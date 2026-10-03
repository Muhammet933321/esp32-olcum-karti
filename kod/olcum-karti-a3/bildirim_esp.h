#ifndef BILDIRIM_ESP_H
#define BILDIRIM_ESP_H
/*
 * 1E — MQTT BILDIRIMLERININ KARTA BAGLANMASI.
 * Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K1-K12).
 *
 * Olay uretimi, esik, kuyruk, zarf bicimi platformsuz bildirim.h'de (AVR'de
 * sinaniyor, B71.N); MQTT paketleri platformsuz mqtt_paket.h'de (B71.M). Bu
 * dosya YALNIZ ESP32 yapistiricisi: NVS (`mqtt` ad alani), esp-tls baglantisi,
 * libsodium ChaCha20-Poly1305, cekirdek 0'a SABITLI bildirim gorevi.
 *
 * Neden esp-mqtt degil: 3.3.11'deki esp-mqtt gorevi cekirdege sabitlenmiyor
 * (CONFIG_MQTT_TASK_CORE_SELECTION_ENABLED yok, oncelik en az 1) — TLS el
 * sikismasi (P-256 yazilimda, yuzlerce ms) cekirdek 1'e kayip olcumu bloklardi.
 *
 * 🔴 BURADA `Serial` YOK (kayit_esp.h gibi): `#define Serial CIKIS`'ten ONCE
 *    dahil ediliyor; Q komutlarinin butun basmasi .ino'da, cekirdek 1'de.
 * 🔴 Sirlar (aracı parolalari, bildirim anahtari) hicbir satira basilmaz:
 *    Serial aynasi her satiri /akis SSE'sine tasir.
 *
 * CEKIRDEKLER:
 *   cekirdek 1 (loop)  bildirim_pil_bitti (pil_durdur), Q komutlari (NVS yazar,
 *                      bld_istek_* bayraklarini kaldirir)
 *   cekirdek 0 (bld)   bildirim_gorevi: anlik goruntu -> bld_adim, baglanti,
 *                      yayin. Bildirim yapisina YALNIZ bu gorev dokunur.
 *   cekirdek 0 (ag)    /bildirim/bilgi: bildirim_bilgi_zarf (NVS okur)
 */
#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <string.h>
#include <sys/socket.h>
#include "esp_tls.h"
#include "esp_crt_bundle.h"
#include "esp_random.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <sodium.h>
#include "ag.h"
#include "kayit_esp.h"            /* kayit_durum_al, kayit_bitir_iz_al, kayit__unix */
#include "mqtt_paket.h"

#define BLD_KUYRUK 16u            /* K7: internet yokken RAM'de bekleyen olay */
#define BLD_MESAJ  192u
#include "bildirim.h"

#define BLD_NVS          "mqtt"
#define BLD_KEEPALIVE_S  5u       /* K8: araci 1.5 x = 7.5 s'de vasiyeti yayinlar */
#define BLD_PING_MS      4000UL   /* keepalive'dan once bir sey gonder */
#define BLD_PINGRESP_MS  5000UL   /* yanit gelmezse baglanti olu */
#define BLD_PUBACK_MS    10000UL  /* olay onaysizsa baglanti olu (yeniden gonderilir; n ayiklar) */
#define BLD_CONNACK_MS   10000UL
#define BLD_TLS_MS       10000
#define BLD_DENEME_EN_AZ 2000UL   /* yeniden baglanma: 2, 4, 8 ... 60 s */
#define BLD_DENEME_EN_COK 60000UL
#define BLD_PAKET        640u     /* CONNECT (iki 95'lik alan + vasiyet) sigar */
#define BLD_ZARF         (4u + 12u + BLD_MESAJ + 16u)

#define BLD_URI_AZAMI    127u
#define BLD_KUL_AZAMI    63u
#define BLD_PAR_AZAMI    95u

/* durum (Q? satiri) */
#define BLDD_KAPALI     0u        /* Q0 */
#define BLDD_AYAR_EKSIK 1u        /* uri / kart kullanicisi / parolasi / anahtar yok */
#define BLDD_AG_YOK     2u        /* STA degil (AP kipinde MQTT yok, K8) ya da WiFi kopuk */
#define BLDD_BAGLANIYOR 3u
#define BLDD_BAGLI      4u
#define BLDD_BEKLIYOR   5u        /* hata sonrasi geri cekilme */

/* son hata */
#define BLDH_YOK      0
#define BLDH_URI     -1           /* uri cozulemedi */
#define BLDH_BELLEK  -2
#define BLDH_TLS     -3           /* TCP/TLS kurulamadi (ad, sertifika, ag) */
#define BLDH_YAZ     -4
#define BLDH_CONNACK -5           /* sure doldu */
#define BLDH_KOPTU   -6           /* araci kapatti / okuma hatasi */
#define BLDH_PING    -7           /* PINGRESP gelmedi */
#define BLDH_PUBACK  -8
#define BLDH_PAKET   -9           /* paket kurulamadi (alan uzun) */
#define BLDH_BOZUK   -10          /* gelen akis MQTT degil */
#define BLDH_RED     -100         /* -100 - CONNACK kodu (5 = yetkisiz, 4 = kullanici/parola) */

typedef struct {
    uint8_t  durum;
    int32_t  son_hata;
    uint32_t baglanti, yayin, olay, dusen, kuyruk;
    uint32_t bagli_ms;            /* son baglanma ani (millis) */
    uint32_t el_sikisma_ms;       /* son TLS + CONNACK suresi */
} BildirimDurum;

static BildirimDurum bld_durum = {};
static portMUX_TYPE bld_mux = portMUX_INITIALIZER_UNLOCKED;
static volatile uint8_t bld_istek_yeniden = 1;   /* ayar degisti: oku + yeniden baglan */
/* Qt: cekirdek 1 `istek`i, gorev `islenen`i artirir — her sayacin TEK yazari var. Bayrak
   arka arkaya iki Qt'yi tek olaya birlestiriyordu (kart tezgahi 2026-10-01, D1). */
static volatile uint8_t bld_deneme_istek = 0, bld_deneme_islenen = 0;
static volatile uint8_t bld_sodium = 0;          /* sodium_init basarili */
static TaskHandle_t bld_gorev_kolu = nullptr;
static char bld_kimlik[17] = "";                 /* istemci kimligi: "ok-" + kart kimligi */

/* ─────────────────────────────── pil testi bitti (cekirdek 1, pil_durdur) */
typedef struct {
    uint32_t say;
    uint8_t  durum;
    uint32_t mah_milli, wh_milli, sure_ms;
} BildirimPilIz;
static BildirimPilIz bld_pil_iz = {};

static void bildirim_pil_bitti(uint8_t durum, float mah, float wh, uint32_t sure_ms)
{
    const uint32_t m = (mah > 0.0f) ? (uint32_t)lroundf(mah * 1000.0f) : 0u;
    const uint32_t w = (wh > 0.0f) ? (uint32_t)lroundf(wh * 1000.0f) : 0u;
    portENTER_CRITICAL(&bld_mux);
    bld_pil_iz.say++;
    bld_pil_iz.durum = durum;
    bld_pil_iz.mah_milli = m;
    bld_pil_iz.wh_milli = w;
    bld_pil_iz.sure_ms = sure_ms;
    portEXIT_CRITICAL(&bld_mux);
}

static BildirimDurum bildirim_durum_al(void)
{
    BildirimDurum t;
    portENTER_CRITICAL(&bld_mux);
    t = bld_durum;
    portEXIT_CRITICAL(&bld_mux);
    return t;
}

static void bld__durum_yaz(uint8_t d, int32_t h)
{
    portENTER_CRITICAL(&bld_mux);
    bld_durum.durum = d;
    if (h) bld_durum.son_hata = h;
    portEXIT_CRITICAL(&bld_mux);
}

/* ─────────────────────────────── kriptografi (libsodium) */
static int bld__aead(const uint8_t anahtar[32], const uint8_t nonce[12], const uint8_t *aad,
                     uint16_t aad_n, const uint8_t *duz, uint16_t duz_n, uint8_t *cikti)
{
    unsigned long long n = 0;
    if (!bld_sodium) return -1;
    return crypto_aead_chacha20poly1305_ietf_encrypt(cikti, &n, duz, duz_n, aad, aad_n, nullptr,
                                                     nonce, anahtar) == 0 ? 0 : -1;
}

static void bld__rastgele(uint8_t *h, uint16_t n)
{
    esp_fill_random(h, n);
}

static const BildirimKripto bld_kripto = { bld__rastgele, bld__aead };

/* Qv: RFC 8439 §2.8.2 vektoru (anahtar 80..9f, AAD 50..53 c0..c7). 0 = gecti. */
static int bildirim_oz_sinama(void)
{
    static const char duz[] = "Ladies and Gentlemen of the class of '99: If I could offer you only "
                              "one tip for the future, sunscreen would be it.";
    static const uint8_t nonce[12] = {7, 0, 0, 0, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47};
    static const uint8_t aad[12] = {0x50, 0x51, 0x52, 0x53, 0xc0, 0xc1, 0xc2, 0xc3,
                                    0xc4, 0xc5, 0xc6, 0xc7};
    static const uint8_t ilk[8] = {0xd3, 0x1a, 0x8d, 0x34, 0x64, 0x8e, 0x60, 0xdb};
    static const uint8_t etiket[16] = {0x1a, 0xe1, 0x0b, 0x59, 0x4f, 0x09, 0xe2, 0x6a,
                                       0x7e, 0x90, 0x2e, 0xcb, 0xd0, 0x60, 0x06, 0x91};
    uint8_t k[32], c[sizeof(duz) - 1 + 16], d[sizeof(duz)];
    unsigned long long n = 0;
    const uint16_t m = (uint16_t)(sizeof(duz) - 1);
    for (uint8_t i = 0; i < 32; i++) k[i] = (uint8_t)(0x80 + i);
    if (!bld_sodium) return 1;
    if (bld__aead(k, nonce, aad, sizeof(aad), (const uint8_t *)duz, m, c)) return 2;
    if (memcmp(c, ilk, sizeof(ilk))) return 3;
    if (memcmp(c + m, etiket, 16)) return 4;
    if (crypto_aead_chacha20poly1305_ietf_decrypt(d, &n, nullptr, c, sizeof(c), aad, sizeof(aad),
                                                  nonce, k) || n != m || memcmp(d, duz, m)) return 5;
    c[3] ^= 1u;                                    /* bozuk sifreli metin REDDEDILMELI */
    if (!crypto_aead_chacha20poly1305_ietf_decrypt(d, &n, nullptr, c, sizeof(c), aad, sizeof(aad),
                                                   nonce, k)) return 6;
    return 0;
}

/* ─────────────────────────────── ayar (NVS `mqtt`) */
typedef struct {
    char    uri[BLD_URI_AZAMI + 1];
    char    kk[BLD_KUL_AZAMI + 1], kp[BLD_PAR_AZAMI + 1];   /* kart: yayin */
    char    ck[BLD_KUL_AZAMI + 1], cp[BLD_PAR_AZAMI + 1];   /* cihaz: yalniz abone (K3) */
    uint8_t acik;
    uint8_t onek[16];
    uint8_t anahtar[32];
    uint8_t onek_var, anahtar_var;
    uint16_t esik;                /* W2 (E3): `Qe` binde; 0 / gecersiz = varsayilan */
} BildirimAyar;

static void bld__ayar_oku(BildirimAyar *a)
{
    Preferences p;
    memset(a, 0, sizeof(*a));
    if (!p.begin(BLD_NVS, true)) return;     /* ad alani yok = hic ayarlanmamis */
    p.getString("uri", a->uri, sizeof(a->uri));
    p.getString("kk", a->kk, sizeof(a->kk));
    p.getString("kp", a->kp, sizeof(a->kp));
    p.getString("ck", a->ck, sizeof(a->ck));
    p.getString("cp", a->cp, sizeof(a->cp));
    a->acik = p.getUChar("acik", 0);
    a->esik = p.getUShort("esik", 0);
    a->onek_var = p.getBytes("onek", a->onek, 16) == 16u;
    a->anahtar_var = p.getBytes("anahtar", a->anahtar, 32) == 32u;
    p.end();
}

static void bld__ayar_sil(BildirimAyar *a)
{
    sodium_memzero(a, sizeof(*a));
}

static void bld__onek_hex(const uint8_t o[16], char h[33])
{
    static const char x[] = "0123456789abcdef";
    for (uint8_t i = 0; i < 16; i++) {
        h[2 * i] = x[o[i] >> 4];
        h[2 * i + 1] = x[o[i] & 15u];
    }
    h[32] = 0;
}

/* Q komutlari (cekirdek 1). 0 = yazildi. Metin alanlarinda kontrol karakteri yok. */
static int bildirim_ayar_metin(const char *anahtar, const char *deger, uint8_t azami)
{
    Preferences p;
    for (const char *q = deger; *q; q++)
        if ((uint8_t)*q < 0x20u) return -2;
    if (strlen(deger) > azami) return -3;
    if (!p.begin(BLD_NVS, false)) return -1;
    const size_t n = p.putString(anahtar, deger);
    p.end();
    if (n != strlen(deger) && deger[0]) return -1;
    bld_istek_yeniden = 1;
    return 0;
}

/* W2 (E3): `Qe<binde>` (cekirdek 1, YALNIZ USB). 0 = anahtari sil (varsayilan). Gorev yeni
   esigi BAGLANTIYI KESMEDEN alir (bld_istek_yeniden degil: istek/islenen sayaclari). */
static volatile uint8_t bld_esik_istek = 0, bld_esik_islenen = 0;
static volatile uint16_t bld_esik_etkin = BLD_ESIK_VARSAYILAN;   /* gorev yazar, Q? okur */

static int bildirim_esik_yaz(uint16_t binde)
{
    Preferences p;
    int r = 0;
    if (!p.begin(BLD_NVS, false)) return -1;
    if (binde) r = p.putUShort("esik", binde) == 2u ? 0 : -1;
    else if (p.isKey("esik") && !p.remove("esik")) r = -1;
    p.end();
    bld_esik_istek = (uint8_t)(bld_esik_istek + 1u);   /* yalniz cekirdek 1 yazar */
    return r;
}

static uint16_t bld__esik_oku(void)
{
    Preferences p;
    uint16_t e = 0;
    if (p.begin(BLD_NVS, true)) {
        e = p.getUShort("esik", 0);
        p.end();
    }
    return e;
}

static int bildirim_ayar_acik(uint8_t acik)
{
    Preferences p;
    if (!p.begin(BLD_NVS, false)) return -1;
    const size_t n = p.putUChar("acik", acik ? 1u : 0u);
    p.end();
    bld_istek_yeniden = 1;
    return n == 1u ? 0 : -1;
}

/* Onek + bildirim anahtari: yoksa (ya da yeni = 1) uret. RF ACIK olmali (cagiran
   denetler — Ep gibi). 1: uretildi, 0: zaten vardi, < 0: NVS hatasi. */
static int bildirim_sir_uret(uint8_t yeni)
{
    Preferences p;
    uint8_t o[16], k[32];
    int r = 0;
    if (!p.begin(BLD_NVS, false)) return -1;
    if (yeni || p.getBytes("onek", o, 16) != 16u) {
        esp_fill_random(o, 16);
        if (p.putBytes("onek", o, 16) != 16u) r = -1; else r = 1;
    }
    if (r >= 0 && (yeni || p.getBytes("anahtar", k, 32) != 32u)) {
        esp_fill_random(k, 32);
        if (p.putBytes("anahtar", k, 32) != 32u) r = -1; else r = 1;
    }
    p.end();
    sodium_memzero(k, sizeof(k));
    bld_istek_yeniden = 1;
    return r;
}

/* Q? icin SIRSIZ ozet: kullanici adlari, uri, onekin ilk 8 hanesi; parolalar var/yok. */
typedef struct {
    char    uri[BLD_URI_AZAMI + 1];
    char    kk[BLD_KUL_AZAMI + 1], ck[BLD_KUL_AZAMI + 1];
    uint8_t kp_var, cp_var, acik, onek_var, anahtar_var;
    char    onek8[9];
} BildirimOzet;

static void bildirim_ozet(BildirimOzet *z)
{
    BildirimAyar *a = (BildirimAyar *)malloc(sizeof(BildirimAyar));
    memset(z, 0, sizeof(*z));
    if (!a) return;
    bld__ayar_oku(a);
    memcpy(z->uri, a->uri, sizeof(z->uri));
    memcpy(z->kk, a->kk, sizeof(z->kk));
    memcpy(z->ck, a->ck, sizeof(z->ck));
    z->kp_var = a->kp[0] != 0;
    z->cp_var = a->cp[0] != 0;
    z->acik = a->acik;
    z->onek_var = a->onek_var;
    z->anahtar_var = a->anahtar_var;
    if (a->onek_var) {
        char h[33];
        bld__onek_hex(a->onek, h);
        memcpy(z->onek8, h, 8);
    }
    bld__ayar_sil(a);
    free(a);
}

/* ─────────────────────────────── /bildirim/bilgi (cekirdek 0, ag) — K10
   Yanit = "OKB1" | nonce | ChaCha20-Poly1305(K_cihaz, JSON) | etiket,
   AAD = "OK1-bildirim\n<kimlik>\n<n>". Donus: uzunluk, -1 ayar eksik, -2 kripto. */
static int bildirim_bilgi_zarf(uint8_t n, const uint8_t K[32], const char *kimlik,
                               uint8_t *cikti, uint16_t azami)
{
    BildirimAyar *a = (BildirimAyar *)malloc(sizeof(BildirimAyar));
    char aad[48], onek[33], anahtar[65];
    int r = -1;
    if (!a) return -2;
    bld__ayar_oku(a);
    if (a->uri[0] && a->ck[0] && a->cp[0] && a->onek_var && a->anahtar_var) {
        bld__onek_hex(a->onek, onek);
        for (uint8_t i = 0; i < 2; i++) bld__onek_hex(a->anahtar + 16 * i, anahtar + 32 * i);
        /* uri/kullanici/parola kontrol karaktersiz (Q komutu denetledi); " ve \ kacirilir */
        String js = "{\"u\":\"";
        auto kac = [&js](const char *s) {
            for (; *s; s++) { if (*s == '"' || *s == '\\') js += '\\'; js += *s; }
        };
        kac(a->uri);
        js += "\",\"k\":\""; kac(a->ck);
        js += "\",\"p\":\""; kac(a->cp);
        js += "\",\"o\":\""; js += onek;
        js += "\",\"a\":\""; js += anahtar;
        js += "\"}";
        const uint16_t m = (uint16_t)js.length();
        snprintf(aad, sizeof(aad), "OK1-bildirim\n%s\n%u", kimlik, (unsigned)n);
        if (4u + 12u + m + 16u > azami) r = -2;
        else {
            memcpy(cikti, "OKB1", 4);
            esp_fill_random(cikti + 4, 12);
            r = bld__aead(K, cikti + 4, (const uint8_t *)aad, (uint16_t)strlen(aad),
                          (const uint8_t *)js.c_str(), m, cikti + 16) ? -2 : (int)(16u + m + 16u);
        }
        for (unsigned i = 0; i < js.length(); i++) js.setCharAt(i, 0);
        sodium_memzero(anahtar, sizeof(anahtar));
    }
    bld__ayar_sil(a);
    free(a);
    return r;
}

/* ─────────────────────────────── baglanti (YALNIZ bildirim gorevi) */
typedef struct {
    esp_tls_t  *tls;
    uint8_t     sifreli;          /* mqtts */
    MqpOkuyucu  ok;
    uint16_t    pid;              /* sonraki paket kimligi */
    uint16_t    ucusta;           /* onay bekleyen olayin pid'i (0 = yok) */
    uint32_t    ucus_ms, gonder_ms, ping_ms;
    uint8_t     ping_bekle;
    char        konu_durum[48], konu_olay[48];
} BldBag;

static BildirimAyar bld_ayar;               /* gorevin kopyasi */
static Bildirim     bld;                    /* olay ureticisi (gorev disinda dokunulmaz) */
static BldBag       bld_bag = {};
static uint8_t      bld_paket[BLD_PAKET];
static uint8_t      bld_zarf_t[BLD_ZARF];
static char         bld_json[BLD_MESAJ];

static int bld__yaz(BldBag *b, const uint8_t *v, size_t n);
static int bld__zarfla(const char *konu, const char *json);

/* nazik: DISCONNECT'ten ONCE durum konusuna c:0 (retained) — araci nazik kopuista
   vasiyeti YAYINLAMAZ; Q0 / ayar degisimi "cevrimici" durumu birakmasin. */
static void bld__kapat(BldBag *b, uint8_t nazik)
{
    if (b->tls) {
        if (nazik) {
            bld_vasiyet_json(kayit_durum_al().acilis, bld_json, sizeof(bld_json));
            const int z = bld__zarfla(b->konu_durum, bld_json);
            if (z > 0) {
                const int32_t n = mqp_yayin(b->konu_durum, bld_zarf_t, (uint16_t)z, 0, 1, 0,
                                            bld_paket, sizeof(bld_paket));
                if (n > 0) (void)bld__yaz(b, bld_paket, (size_t)n);
            }
            const int32_t n = mqp_kopar(bld_paket, sizeof(bld_paket));
            if (n > 0) (void)esp_tls_conn_write(b->tls, bld_paket, (size_t)n);
        }
        esp_tls_conn_destroy(b->tls);
    }
    b->tls = nullptr;
    b->ucusta = 0;
    b->ping_bekle = 0;
}

static int bld__yaz(BldBag *b, const uint8_t *v, size_t n)
{
    size_t o = 0;
    const uint32_t son = millis() + 5000UL;
    while (o < n) {
        const ssize_t k = esp_tls_conn_write(b->tls, v + o, n - o);
        if (k > 0) { o += (size_t)k; continue; }
        if ((k == ESP_TLS_ERR_SSL_WANT_READ || k == ESP_TLS_ERR_SSL_WANT_WRITE)
            && (int32_t)(millis() - son) < 0) { vTaskDelay(1); continue; }
        return BLDH_YAZ;
    }
    b->gonder_ms = millis();
    return 0;
}

/* En fazla `bekle_ms` bekler; > 0 okunan, 0 veri yok, < 0 baglanti olu. */
static int bld__oku(BldBag *b, uint32_t bekle_ms, uint8_t *t, size_t n)
{
    int fd = -1;
    if (!(b->sifreli && esp_tls_get_bytes_avail(b->tls) > 0)) {
        if (esp_tls_get_conn_sockfd(b->tls, &fd) != ESP_OK || fd < 0) return BLDH_KOPTU;
        fd_set r;
        FD_ZERO(&r);
        FD_SET(fd, &r);
        struct timeval tv = { (time_t)(bekle_ms / 1000u), (suseconds_t)((bekle_ms % 1000u) * 1000u) };
        const int s = select(fd + 1, &r, nullptr, nullptr, &tv);
        if (s < 0) return BLDH_KOPTU;
        if (s == 0) return 0;
    }
    const ssize_t k = esp_tls_conn_read(b->tls, t, n);
    if (k == ESP_TLS_ERR_SSL_WANT_READ || k == ESP_TLS_ERR_SSL_WANT_WRITE) return 0;
    return k > 0 ? (int)k : BLDH_KOPTU;
}

static int bld__zarfla(const char *konu, const char *json)
{
    return bld_zarf(&bld_kripto, bld_ayar.anahtar, konu, json, bld_zarf_t, sizeof(bld_zarf_t));
}

static int bld__baglan(BldBag *b, uint32_t acilis)
{
    char ad[64], onek[33];
    uint16_t port = 0;
    uint8_t tls = 0;
    const uint32_t t0 = millis();
    if (mqp_uri_coz(bld_ayar.uri, ad, sizeof(ad), &port, &tls)) return BLDH_URI;
    bld__onek_hex(bld_ayar.onek, onek);
    bld_konu(onek, "durum", b->konu_durum, sizeof(b->konu_durum));
    bld_konu(onek, "olay", b->konu_olay, sizeof(b->konu_olay));

    esp_tls_cfg_t cfg = {};
    cfg.timeout_ms = BLD_TLS_MS;
    if (tls) cfg.crt_bundle_attach = esp_crt_bundle_attach;
    else cfg.is_plain_tcp = true;
    b->tls = esp_tls_init();
    if (!b->tls) return BLDH_BELLEK;
    b->sifreli = tls;
    if (esp_tls_conn_new_sync(ad, (int)strlen(ad), port, &cfg, b->tls) != 1) {
        bld__kapat(b, 0);
        return BLDH_TLS;
    }
    /* vasiyet: her baglanista YENI nonce ile sifrelenir (K6) */
    bld_vasiyet_json(acilis, bld_json, sizeof(bld_json));
    const int z = bld__zarfla(b->konu_durum, bld_json);
    if (z < 0) { bld__kapat(b, 0); return BLDH_PAKET; }
    char istemci[24];
    snprintf(istemci, sizeof(istemci), "ok-%s", bld_kimlik);
    MqpBaglan m = {};
    m.istemci = istemci;
    m.kullanici = bld_ayar.kk;
    m.parola = bld_ayar.kp[0] ? bld_ayar.kp : nullptr;
    m.vasiyet_konu = b->konu_durum;
    m.vasiyet = bld_zarf_t;
    m.vasiyet_n = (uint16_t)z;
    m.vasiyet_qos = 1;
    m.vasiyet_tut = 1;
    m.keepalive = BLD_KEEPALIVE_S;
    m.temiz = 1;
    const int32_t n = mqp_baglan(&m, bld_paket, sizeof(bld_paket));
    if (n < 0) { bld__kapat(b, 0); return BLDH_PAKET; }
    int r = bld__yaz(b, bld_paket, (size_t)n);
    sodium_memzero(bld_paket, (size_t)n);          /* parola paketin icindeydi */
    if (r) { bld__kapat(b, 0); return r; }
    mqp_oku_kur(&b->ok);
    const uint32_t son = millis() + BLD_CONNACK_MS;
    uint8_t t[16];
    while ((int32_t)(millis() - son) < 0) {
        const int k = bld__oku(b, 100, t, sizeof(t));
        if (k < 0) { bld__kapat(b, 0); return BLDH_KOPTU; }
        uint16_t i = 0;
        while (i < (uint16_t)k) {
            uint16_t u = 0;
            const int p = mqp_oku(&b->ok, t + i, (uint16_t)(k - i), &u);
            i = (uint16_t)(i + u);
            if (p < 0) { bld__kapat(b, 0); return BLDH_BOZUK; }
            if (p == 1) {
                const int rc = mqp_connack(&b->ok);
                if (rc < 0) { bld__kapat(b, 0); return BLDH_BOZUK; }
                if (rc) { bld__kapat(b, 0); return BLDH_RED - rc; }
                b->ping_ms = 0;
                b->ping_bekle = 0;
                b->ucusta = 0;
                portENTER_CRITICAL(&bld_mux);
                bld_durum.el_sikisma_ms = millis() - t0;
                bld_durum.bagli_ms = millis();
                bld_durum.baglanti++;
                portEXIT_CRITICAL(&bld_mux);
                return 0;
            }
        }
    }
    bld__kapat(b, 0);
    return BLDH_CONNACK;
}

static int bld__yayinla(BldBag *b, const char *konu, const char *json, uint8_t qos, uint8_t tut,
                        uint16_t pid)
{
    const int z = bld__zarfla(konu, json);
    if (z < 0) return BLDH_PAKET;
    const int32_t n = mqp_yayin(konu, bld_zarf_t, (uint16_t)z, qos, tut, pid, bld_paket,
                                sizeof(bld_paket));
    if (n < 0) return BLDH_PAKET;
    const int r = bld__yaz(b, bld_paket, (size_t)n);
    if (!r) {
        portENTER_CRITICAL(&bld_mux);
        bld_durum.yayin++;
        portEXIT_CRITICAL(&bld_mux);
    }
    return r;
}

/* Gelen paketler: PUBACK (ucustaki olay onaylandi), PINGRESP. */
static int bld__gelen(BldBag *b, uint32_t bekle_ms)
{
    uint8_t t[64];
    const int k = bld__oku(b, bekle_ms, t, sizeof(t));
    if (k <= 0) return k;
    uint16_t i = 0;
    while (i < (uint16_t)k) {
        uint16_t u = 0;
        const int p = mqp_oku(&b->ok, t + i, (uint16_t)(k - i), &u);
        i = (uint16_t)(i + u);
        if (p < 0) return BLDH_BOZUK;
        if (p != 1) continue;
        const uint8_t tip = mqp_tip(&b->ok);
        if (tip == MQP_PINGRESP) b->ping_bekle = 0;
        else if (tip == MQP_PUBACK && b->ucusta && mqp_puback_pid(&b->ok) == (int32_t)b->ucusta) {
            bld_kuyruk_at(&bld);
            b->ucusta = 0;
            portENTER_CRITICAL(&bld_mux);
            bld_durum.olay++;
            portEXIT_CRITICAL(&bld_mux);
        }
    }
    return 0;
}

/* ─────────────────────────────── anlik goruntu */
static uint8_t bld_ilk = 1, bld_devam = 0;

static uint8_t bld__goruntu(BildirimGoruntu *g)
{
    const KayitDurum d = kayit_durum_al();
    const KayitBitirIz bi = kayit_bitir_iz_al();
    BildirimPilIz pi;
    if (!d.tarandi && kayit_bolum && millis() < 120000UL) return 0;   /* tarama bitmeden karar yok */
    if (bld_ilk) {   /* acilis: acik olcum oturumu DEVAM aldi mi, kapandi mi */
        bld_devam = d.oturum ? 1u : (bi.say ? 2u : 0u);
        bld_ilk = 0;
    }
    portENTER_CRITICAL(&bld_mux);
    pi = bld_pil_iz;
    portEXIT_CRITICAL(&bld_mux);
    memset(g, 0, sizeof(*g));
    g->acilis = d.acilis;
    g->unix_s = kayit__unix();
    g->kayit = d.durum;
    g->oturum = d.oturum;
    g->tur = d.tur;
    g->doluluk_binde = d.doluluk_binde;
    g->esitlenmemis_binde = d.onaysiz_binde;
    g->bitir_say = bi.say;
    g->bitir_oturum = bi.oturum;
    g->bitir_nokta = bi.nokta;
    g->bitir_sebep = bi.sebep;
    g->pil_say = pi.say;
    g->pil_durum = pi.durum;
    g->pil_mah_milli = pi.mah_milli;
    g->pil_wh_milli = pi.wh_milli;
    g->pil_sure_ms = pi.sure_ms;
    g->devam = bld_devam;
    return 1;
}

static uint8_t bld__ayar_tam(void)
{
    return bld_ayar.uri[0] && bld_ayar.kk[0] && bld_ayar.kp[0] && bld_ayar.onek_var
           && bld_ayar.anahtar_var;
}

/* ─────────────────────────────── gorev (cekirdek 0) */
static void bildirim_gorevi(void *)
{
    BldBag *b = &bld_bag;
    uint32_t deneme_ms = 0, geri = BLD_DENEME_EN_AZ;
    uint8_t durum_zorla = 0, kuruldu = 0;
    bld_kur(&bld, 500u);
    for (;;) {
        if (bld_istek_yeniden) {
            bld_istek_yeniden = 0;
            if (b->tls) bld__kapat(b, 1);
            bld__ayar_sil(&bld_ayar);
            bld__ayar_oku(&bld_ayar);
            bld_esik_ayarla(&bld, bld_ayar.esik);          /* W2 (E3): NVS'teki kullanici esigi */
            deneme_ms = millis();
            geri = BLD_DENEME_EN_AZ;
        }
        if (bld_esik_islenen != bld_esik_istek) {          /* W2 (E3): Qe — baglanti kesilmez */
            bld_esik_islenen = bld_esik_istek;
            bld_esik_ayarla(&bld, bld__esik_oku());
        }
        bld_esik_etkin = bld.esik;
        if (!bld_ayar.acik) {
            bld__durum_yaz(BLDD_KAPALI, 0);
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }
        /* olaylar acikken uretilir (internet yokken kuyrukta bekler) */
        BildirimGoruntu g;
        memset(&g, 0, sizeof(g));
        const uint8_t gv = bld__goruntu(&g);
        if (gv) {
            kuruldu = 1;
            bld_adim(&bld, &g, millis());
            while (bld_deneme_islenen != bld_deneme_istek) {
                bld_deneme(&bld, g.acilis, g.unix_s);
                bld_deneme_islenen = (uint8_t)(bld_deneme_islenen + 1u);
            }
            portENTER_CRITICAL(&bld_mux);
            bld_durum.kuyruk = bld_kuyruk_adet(&bld);
            bld_durum.dusen = bld.dusen;
            portEXIT_CRITICAL(&bld_mux);
        }
        if (!bld__ayar_tam()) {
            bld__durum_yaz(BLDD_AYAR_EKSIK, 0);
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }
        if (!(ag_durum.kip == AG_STA && WiFi.status() == WL_CONNECTED)) {
            if (b->tls) bld__kapat(b, 0);
            bld__durum_yaz(BLDD_AG_YOK, 0);
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }
        if (!b->tls) {
            if ((int32_t)(millis() - deneme_ms) < 0 || !kuruldu) {
                bld__durum_yaz(BLDD_BEKLIYOR, 0);
                vTaskDelay(pdMS_TO_TICKS(200));
                continue;
            }
            bld__durum_yaz(BLDD_BAGLANIYOR, 0);
            const int r = bld__baglan(b, kayit_durum_al().acilis);
            if (r) {
                bld__durum_yaz(BLDD_BEKLIYOR, r);
                deneme_ms = millis() + geri;
                geri = (geri * 2u > BLD_DENEME_EN_COK) ? BLD_DENEME_EN_COK : geri * 2u;
                continue;
            }
            geri = BLD_DENEME_EN_AZ;
            durum_zorla = 1;                         /* retained vasiyetin ustune yaz */
            bld__durum_yaz(BLDD_BAGLI, 0);
        }
        int r = 0;
        /* durum (retained, QoS 0): baglaninca, degisince, 60 s'de bir */
        if (gv && (durum_zorla || bld_durum_gerek(&bld, &g, millis()))) {
            bld_durum_json(&g, KAYIT_FW_SURUM, bld_json, sizeof(bld_json));
            r = bld__yayinla(b, b->konu_durum, bld_json, 0, 1, 0);
            if (!r) { bld_durum_yayinlandi(&bld, &g, millis()); durum_zorla = 0; }
        }
        /* olay (QoS 1): ayni anda TEK olay ucusta; PUBACK gelince kuyruktan duser */
        if (!r && !b->ucusta && bld_kuyruk_adet(&bld)) {
            if (bld_kuyruk_bas(&bld, bld_json, sizeof(bld_json)) > 0) {
                if (++b->pid == 0) b->pid = 1;
                r = bld__yayinla(b, b->konu_olay, bld_json, 1, 0, b->pid);
                if (!r) { b->ucusta = b->pid; b->ucus_ms = millis(); }
            }
        }
        if (!r && b->ucusta && millis() - b->ucus_ms > BLD_PUBACK_MS) r = BLDH_PUBACK;
        /* canlilik: 4 s'de bir PINGREQ; 5 s'de yanit yoksa baglanti olu */
        if (!r && b->ping_bekle && millis() - b->ping_ms > BLD_PINGRESP_MS) r = BLDH_PING;
        if (!r && !b->ping_bekle && millis() - b->gonder_ms >= BLD_PING_MS) {
            const int32_t n = mqp_ping(bld_paket, sizeof(bld_paket));
            r = bld__yaz(b, bld_paket, (size_t)n);
            if (!r) { b->ping_bekle = 1; b->ping_ms = millis(); }
        }
        if (!r) r = bld__gelen(b, 50);
        if (r) {
            bld__kapat(b, 0);
            bld__durum_yaz(BLDD_BEKLIYOR, r);
            deneme_ms = millis() + geri;
        }
    }
}

/* setup()'tan (WiFi kurulduktan SONRA). kimlik: kartin 16 hanelik kimligi. */
static void bildirim_baslat(const char *kimlik)
{
    if (bld_gorev_kolu) return;
    strncpy(bld_kimlik, kimlik, sizeof(bld_kimlik) - 1);
    bld_sodium = sodium_init() >= 0 ? 1u : 0u;
    /* TLS el sikismasi + mbedTLS: 8 KB yigin; CEKIRDEK 0'a SABIT (olcum cekirdek 1'de) */
    xTaskCreatePinnedToCore(bildirim_gorevi, "bld", 8192, nullptr, 1, &bld_gorev_kolu, 0);
}

#endif /* BILDIRIM_ESP_H */
