#ifndef KAYIT_ESP_H
#define KAYIT_ESP_H
/*
 * B72 — KAYIT MOTORUNUN KARTA BAGLANMASI (alt proje 1A-2).
 *
 * Motor kayit_*.h'de (B71; AVR emulatorunde emule NOR + elektrik kesme ile
 * sinaniyor), DURUM MAKINESI kayit_yonet.h'de (platformsuz; AVR'de emule NVS
 * ile acilistan acilisa sinaniyor, B71.V). Bu dosya YALNIZ ESP32
 * yapistiricisi: flas bolumu (esp_partition), NVS (Preferences), cekirdek
 * 0'daki kayit gorevi, kuyruklar, kilit.
 * Tasarim: tasarim/2026-09-29-yazilim-sistemi.md §5.
 * Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md.
 *
 * 🔴 BURADA `Serial` YOK. Bu baslik `#define Serial CIKIS`'ten ONCE dahil
 *    ediliyor; burada basilan satir web aynasini (SSE) atlardi, ustelik
 *    cekirdek 0'dan basmak aynanin satir bolucusunu yarisa sokardi (B28:
 *    tek yazar). Butun basma .ino'da, cekirdek 1'de.
 *
 * CEKIRDEKLER:
 *   cekirdek 1 (loop)   kayit_ornek / kayit_duraklama: noktaci, nokta KUYRUGA
 *                       kayit_onay_iste: onay "son gelen kazanir" (kuyruk DEGIL)
 *   cekirdek 0 (kayit)  kayit_gorevi: kuyruk -> ky_nokta, istekler, kyn_adim, NTP
 *   cekirdek 0 (ag)     /kayit/liste ve /kayit/veri uclari: kg_oku (SURELI kilit)
 * Butun kg_* / ky_* / kyn_* cagrilari `kayit_kilit` ALTINDA.
 */
#include <Arduino.h>
#include <Preferences.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include "esp_partition.h"
#include "esp_heap_caps.h"
#include "esp_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "ag.h"

#define KG__PARCA 256u            /* flasi 256'lik parcalarla oku (AVR testinde 32) */
/* Arka plan temizligi (GF! sonrasi eski sektorler): DOLU sektor silme ~25 ms
   IKI cekirdegi de durdurur (AUTO_SUSPEND kapali, tezgahta olculdu). 500 ms
   aralik: dolu bolumde ~24 dk surer, olcum dongusunun duraklama payi ~%5. */
#define KYN_TEMIZ_MS 500UL
#include "kayit_nokta.h"
#include "kayit_yonet.h"
#include "kalgec.h"               /* 1B: kalibrasyon gecmisi (platformsuz) */
#include "nvs.h"                  /* nvs_get_stats */

#define KAYIT_FW_SURUM    "A3-1C1"    /* 1C-1: OLAY/NOT kayitlari, PIL oturumu */
#define KAYIT_ALT_TUR     0x40      /* partitions.csv: kayit, data, 0x40 */
#define KAYIT_DIZIN_KAP   64u
#define KAYIT_KUYRUK      256u      /* nokta; 50/s'de ~5 s flas beklemesini yutar */
#define KAYIT_VERI_AZAMI  8192u     /* /kayit/veri tek yanit tavani (dahili RAM) */
#define KAYIT_WEB_BEKLE_MS 200u     /* web ucu kilidi en fazla bu kadar bekler, sonra 503 */

/* cekirdek 1 -> 0 istekleri (onay BURADA DEGIL: kayit_onay_istek) */
#define KM_BASLAT  1u
#define KM_DURDUR  2u
#define KM_BICIMLE 3u
#define KM_PIL_BASLAT 4u   /* 1C-1: BASLA (tur PIL) + yukte PIL_AYAR olayi, TEK mesaj */
#define KM_OLAY       5u   /* 1C-1: yukte olay (DCIR) */
#define KM_PIL_BITIR  6u   /* 1C-1: yukte PIL_SONUC + sebep; yalniz etkin oturum PIL ise */
#define KM_NOT        7u   /* 1C-1: yukte NOT kaydi (ad/etiket/not) */

typedef struct {
    uint8_t    tur, sebep;
    uint16_t   n;                                        /* yuk uzunlugu */
    KayitBasla basla;
    uint8_t    yuk[KAYIT_NOT_BAS + KAYIT_NOT_METIN + 1u];  /* olay ya da NOT */
} KayitMesaj;

typedef struct {
    uint8_t  durum;
    uint32_t oturum, nokta_sira, sonraki_sira, onay, kimlik;
    uint16_t doluluk_binde, onaysiz_binde;
    uint32_t dusen, bozuk, silinen, sil_adet, temiz_kalan;
    uint32_t yaz_azami_us, sil_azami_us, tarama_ms;
    uint32_t acilis, hiz_ms, nesil;
    int32_t  son_hata;
} KayitDurum;

/* olcum_al'in son HAM ornegi — ikisi de cekirdek 1: olcum_al yazar, loop okur */
typedef struct {
    int16_t ham_v, ham_i;
    uint8_t hata, v_doydu, menzil;
} KayitHam;
static KayitHam kayit_ham;

static const esp_partition_t *kayit_bolum = nullptr;
static KayitSektor *kayit_sektor = nullptr;
static KayitOzet   *kayit_dizin = nullptr;
static uint8_t     *kayit_veri_tampon = nullptr;
static KayitGunluk  kayit_g;
static KayitYazici  kayit_y;
static KayitYonetici kayit_m;
static SemaphoreHandle_t kayit_kilit = nullptr;
static QueueHandle_t kayit_nokta_q = nullptr;
static QueueHandle_t kayit_mesaj_q = nullptr;
static TaskHandle_t  kayit_gorev_kolu = nullptr;
static Preferences   kayit_nvs;
static KayitDurum    kayit_durum = {};
static portMUX_TYPE  kayit_mux = portMUX_INITIALIZER_UNLOCKED;

static volatile uint32_t kayit_kuyruk_dusen = 0;   /* cekirdek 1 yazar */
static volatile uint32_t kayit_mesaj_dusen = 0;    /* 1C-1: istek kuyrugunda dusen (cekirdek 1) */
static volatile uint32_t kayit_onay_istek = 0;     /* cekirdek 1 yazar: SON gelen kazanir */
static volatile uint32_t kayit_yaz_azami_us = 0;
static volatile uint32_t kayit_sil_azami_us = 0;
static volatile uint32_t kayit_sil_adet = 0;

static uint32_t kayit_tarama_ms = 0;
static uint8_t  kayit_nvs_acik = 0;
static uint8_t  kayit_saat_ntp = 0, kayit_saat_gecerli = 0;

/* ─────────────────────────────── flas: esp_partition */
static const uint8_t *kayit_esle_ptr = nullptr;       /* bolum bellege esli (mmap) */
static esp_partition_mmap_handle_t kayit_esle_kolu;

/* 🔴 Tezgah 2026-09-30 (dolu bolum): acilis taramasi 11.4 MB'in her kaydinin
   CRC'sini okuyor ve cekirdek 0'i saniyelerce birakmiyordu -> Task WDT (IDLE0)
   karti 5 s'de SIFIRLIYORDU; her acilis ayni taramaya girdigi icin SONSUZ
   yeniden baslama: bolum dolunca kayitlara hic ulasilamiyordu. Kayit gorevi
   uzun islerde 50 ms'de bir tick birakir (kilit tutulurken de guvenli: web
   uclari sureli bekler). */
static void kayit__nefes(void)
{
    static uint32_t son = 0;
    if (xTaskGetCurrentTaskHandle() != kayit_gorev_kolu) return;
    if (millis() - son >= 50u) {
        vTaskDelay(1);
        son = millis();
    }
}

/* Okuma bellege esli bolumden (onbellek uzerinden): esp_partition_read her
   cagrida onbellegi KAPATIP iki cekirdegi de durduruyordu (256 B'lik ~46 000
   okuma). Yazma/silme sonrasi IDF esli araligin onbellegini tazeliyor. */
static int kayit_f_oku(void *b, uint32_t a, void *h, uint32_t n)
{
    (void)b;
    kayit__nefes();
    if (kayit_esle_ptr) {
        memcpy(h, kayit_esle_ptr + a, n);
        return 0;
    }
    return esp_partition_read(kayit_bolum, a, h, n) == ESP_OK ? 0 : -1;
}

static int kayit_f_yaz(void *b, uint32_t a, const void *k, uint32_t n)
{
    uint32_t t = micros();
    esp_err_t e;
    (void)b;
    kayit__nefes();
    e = esp_partition_write(kayit_bolum, a, k, n);
    t = micros() - t;
    if (t > kayit_yaz_azami_us) kayit_yaz_azami_us = t;
    return e == ESP_OK ? 0 : -1;
}

static int kayit_f_sil(void *b, uint32_t a)
{
    uint32_t t = micros();
    esp_err_t e;
    (void)b;
    kayit__nefes();
    e = esp_partition_erase_range(kayit_bolum, a, KAYIT_SEKTOR);
    t = micros() - t;
    if (t > kayit_sil_azami_us) kayit_sil_azami_us = t;
    kayit_sil_adet = kayit_sil_adet + 1u;
    return e == ESP_OK ? 0 : -1;
}

/* ─────────────────────────────── NVS: Preferences (kayit_yonet.h tablosu) */
static uint32_t kayit_nvs_oku(void *b, const char *ad, uint32_t varsayilan)
{
    (void)b;
    return kayit_nvs_acik ? kayit_nvs.getUInt(ad, varsayilan) : varsayilan;
}

static int kayit_nvs_yaz(void *b, const char *ad, uint32_t deger)
{
    (void)b;
    if (!kayit_nvs_acik) return -1;
    return kayit_nvs.putUInt(ad, deger) == sizeof(uint32_t) ? 0 : -1;
}

/* ─────────────────────────────── zaman */
static uint32_t kayit__unix(void)
{
    time_t t = time(nullptr);
    return (t > (time_t)1700000000) ? (uint32_t)t : 0u;   /* 0 = bilinmiyor */
}

/* ─────────────────────────────── durum (cekirdek 0 yazar, herkes okur) */
static KayitDurum kayit_durum_al(void)
{
    KayitDurum t;
    portENTER_CRITICAL(&kayit_mux);
    t = kayit_durum;
    portEXIT_CRITICAL(&kayit_mux);
    return t;
}

/* KILIT ALTINDA cagrilir */
static void kayit__durum_guncelle(void)
{
    KayitDurum t;
    memset(&t, 0, sizeof(t));
    t.durum = kyn_durum(&kayit_m);
    t.oturum = kyn_oturum(&kayit_m);
    t.nokta_sira = kayit_y.nokta_sira + kayit_y.yuk_nokta;
    t.sonraki_sira = kayit_g.sonraki_sira;
    t.onay = kayit_g.onay;
    t.kimlik = kayit_m.kimlik;
    if (kayit_m.hazir) {
        t.doluluk_binde = kg_binde(&kayit_g, kg_kullanilan(&kayit_g));
        t.onaysiz_binde = kg_binde(&kayit_g, kg_onaysiz(&kayit_g));
        t.temiz_kalan = kayit_g.sektor_adet - kayit_m.temiz_s;
    }
    t.dusen = kayit_y.dusen + kayit_kuyruk_dusen;
    t.bozuk = kayit_g.bozuk;
    t.silinen = kayit_g.silinen_sektor;
    t.sil_adet = kayit_sil_adet;
    t.yaz_azami_us = kayit_yaz_azami_us;
    t.sil_azami_us = kayit_sil_azami_us;
    t.tarama_ms = kayit_tarama_ms;
    t.acilis = kayit_m.acilis;
    t.hiz_ms = kayit_y.oturum ? kayit_y.basla.hiz_ms : 0u;
    t.son_hata = kayit_m.son_hata;
    portENTER_CRITICAL(&kayit_mux);
    t.nesil = kayit_durum.nesil
            + ((t.durum != kayit_durum.durum || t.oturum != kayit_durum.oturum) ? 1u : 0u);
    kayit_durum = t;
    portEXIT_CRITICAL(&kayit_mux);
}

/* ─────────────────────────────── istekler (KILIT ALTINDA) */
static void kayit__mesaj(const KayitMesaj *m)
{
    uint32_t simdi = millis();
    switch (m->tur) {
    case KM_BASLAT: {
        KayitBasla b = m->basla;
        if (!b.unix_s) b.unix_s = kayit__unix();
        (void)kyn_baslat(&kayit_m, &b, simdi, kayit__unix());
        break;
    }
    case KM_DURDUR:
        (void)kyn_durdur(&kayit_m);
        break;
    case KM_BICIMLE:
        (void)kyn_bicimle(&kayit_m, simdi);
        break;
    case KM_PIL_BASLAT: {      /* 1C-1: surmekte olan oturum "baska oturum" ile kapanir */
        KayitBasla b = m->basla;
        if (!b.unix_s) b.unix_s = kayit__unix();
        if (kyn_baslat(&kayit_m, &b, simdi, kayit__unix()) > 0)
            (void)kyn_olay(&kayit_m, m->yuk, m->n);
        break;
    }
    case KM_OLAY:
        (void)kyn_olay(&kayit_m, m->yuk, m->n);
        break;
    case KM_PIL_BITIR:
        (void)kyn_pil_bitir(&kayit_m, m->yuk, m->n, m->sebep);
        break;
    case KM_NOT:
        (void)kyn_not(&kayit_m, m->yuk, m->n);
        break;
    default:
        break;
    }
    /* noktaci HEMEN dursun/baslasin: sonraki mesaj/tur beklenmez */
    kayit__durum_guncelle();
}

/* ─────────────────────────────── NTP (gorevde) */
static void kayit__saat(void)
{
    if (!kayit_saat_ntp && ag_durum.kip == AG_STA) {
        configTime(0, 0, "pool.ntp.org", "time.google.com");
        kayit_saat_ntp = 1u;
    }
    if (!kayit_saat_gecerli && kayit__unix()) {
        kayit_saat_gecerli = 1u;
        if (kayit_y.oturum) {
            KayitSaat z;
            z.unix_s = kayit__unix();
            z.kart_ms = millis();
            z.acilis = kayit_m.acilis;
            (void)ky_saat(&kayit_y, &z);
        }
    }
}

/* ─────────────────────────────── gorev (cekirdek 0) */
static void kayit_gorevi(void *)
{
    static const KayitFlas f = { kayit_f_oku, kayit_f_yaz, kayit_f_sil, nullptr };
    static const KayitNvs nvs = { kayit_nvs_oku, kayit_nvs_yaz, nullptr };
    KayitNokta p;
    KayitMesaj m;
    uint32_t t0;
    xSemaphoreTake(kayit_kilit, portMAX_DELAY);
    kayit_nvs_acik = kayit_nvs.begin("kayit", false) ? 1u : 0u;
    kg_kur(&kayit_g, &f, kayit_bolum->size / KAYIT_SEKTOR,
           kayit_sektor, kayit_dizin, (uint16_t)KAYIT_DIZIN_KAP);
    ky_kur(&kayit_y, &kayit_g);
    kyn_kur(&kayit_m, &kayit_g, &kayit_y, &nvs);
    t0 = millis();
    (void)kyn_ac(&kayit_m, millis(), kayit__unix(), esp_random());
    kayit_tarama_ms = millis() - t0;
    if (!kayit_nvs_acik && !kayit_m.son_hata) kayit_m.son_hata = KG_HATA;   /* NVS yok: gorunsun */
    kayit__durum_guncelle();
    xSemaphoreGive(kayit_kilit);
    for (;;) {
        bool var = xQueueReceive(kayit_nokta_q, &p, pdMS_TO_TICKS(100)) == pdTRUE;
        xSemaphoreTake(kayit_kilit, portMAX_DELAY);
        if (kayit_m.hazir) {
            while (var) {
                int r = ky_nokta(&kayit_y, &p, millis());
                if (r && r != KG_YOK) kayit_m.son_hata = r;
                var = xQueueReceive(kayit_nokta_q, &p, 0) == pdTRUE;
            }
            while (xQueueReceive(kayit_mesaj_q, &m, 0) == pdTRUE) kayit__mesaj(&m);
            kyn_adim(&kayit_m, kayit_onay_istek, millis(), kayit__unix());
            kayit__saat();
        }
        kayit__durum_guncelle();
        xSemaphoreGive(kayit_kilit);
    }
}

/* ─────────────────────────────── kurulum (setup, cekirdek 1) */
static bool kayit_kur(void)
{
    uint32_t adet;
    kayit_bolum = esp_partition_find_first(ESP_PARTITION_TYPE_DATA,
                                           (esp_partition_subtype_t)KAYIT_ALT_TUR, "kayit");
    if (!kayit_bolum) return false;
    adet = kayit_bolum->size / KAYIT_SEKTOR;
    {
        const void *p = nullptr;
        if (esp_partition_mmap(kayit_bolum, 0, kayit_bolum->size, ESP_PARTITION_MMAP_DATA,
                               &p, &kayit_esle_kolu) == ESP_OK)
            kayit_esle_ptr = (const uint8_t *)p;       /* olmazsa esp_partition_read */
    }
    kayit_sektor = (KayitSektor *)heap_caps_malloc(adet * sizeof(KayitSektor), MALLOC_CAP_SPIRAM);
    kayit_dizin = (KayitOzet *)heap_caps_malloc(KAYIT_DIZIN_KAP * sizeof(KayitOzet),
                                                 MALLOC_CAP_SPIRAM);
    kayit_veri_tampon = (uint8_t *)heap_caps_malloc(KAYIT_VERI_AZAMI,
                                                     MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    kayit_kilit = xSemaphoreCreateMutex();
    kayit_nokta_q = xQueueCreate(KAYIT_KUYRUK, sizeof(KayitNokta));
    kayit_mesaj_q = xQueueCreate(4, sizeof(KayitMesaj));
    if (!kayit_sektor || !kayit_dizin || !kayit_veri_tampon || !kayit_kilit
        || !kayit_nokta_q || !kayit_mesaj_q) {
        kayit_bolum = nullptr;
        return false;
    }
    xTaskCreatePinnedToCore(kayit_gorevi, "kayit", 8192, nullptr, 1, &kayit_gorev_kolu, 0);
    return true;
}

/* Web ucu icin: kilidi SURELI al (dolu bolumde arka plan temizligi ya da
   uzun acilis taramasi web sunucusunu — p0 dahil — dondurmasin). */
static bool kayit_kilit_al_web(void)
{
    return kayit_kilit && xSemaphoreTake(kayit_kilit, pdMS_TO_TICKS(KAYIT_WEB_BEKLE_MS)) == pdTRUE;
}

/* ─────────────────────────────── onay (cekirdek 1) */
static void kayit_onay_iste(uint32_t sira)
{
    kayit_onay_istek = sira;         /* son gelen kazanir; gorev bir sonraki turda uygular */
}

/* ─────────────────────────────── istek kuyrugu (cekirdek 1)
   Beklemeden gonderir: p0 yolu (pil_durdur) kuyruga TAKILMAZ. `kayit__kuyruga`
   saymaz (yeniden deneme icin); `kayit_mesaj_gonder` dusen istegi sayar.
   Uyari basmak cagiranin isi: bu dosya Serial kullanmaz (B72.F1). */
static bool kayit__kuyruga(const KayitMesaj *m)
{
    return kayit_mesaj_q && xQueueSend(kayit_mesaj_q, m, 0) == pdTRUE;
}

/* 1C-1 son inceleme 1: kuyruga giremeyen pil bitir mesaji BEKLER ve SIRA
   ONUNDUR. Sonraki hicbir istek (p1'in PIL_BASLAT'i, Gb, olay, not) onu
   gecemez: gecseydi bir sonraki testin oturumu, oncekinin SONUC'uyla
   kapanirdi. */
static uint8_t    kayit_bekleyen = 0;
static KayitMesaj kayit_bekleyen_m;

/* Bekleyen yoksa ya da simdi gittiyse true. loop her turda cagirir. */
static bool kayit__bekleyeni_gonder(void)
{
    if (!kayit_bekleyen) return true;
    if (!kayit__kuyruga(&kayit_bekleyen_m)) return false;
    kayit_bekleyen = 0u;
    return true;
}

/* Siradan istek: bekleyen once; o gidemezse bu istek REDDEDILIR (sayilir). */
static bool kayit_mesaj_gonder(const KayitMesaj *m)
{
    if (kayit__bekleyeni_gonder() && kayit__kuyruga(m)) return true;
    kayit_mesaj_dusen = kayit_mesaj_dusen + 1u;
    return false;
}

/* DUSMEYECEK istek (pil bitir): gidemezse bekler. Bekleyen varken ikincisi
   gelirse ESKISI korunur: o kaydedilen testindir; sonraki test, bekleyen varken
   kayit alamadigi (PIL_BASLAT reddedildi) icin bitisi de yazilmaz. */
static void kayit_mesaj_birak(const KayitMesaj *m)
{
    if (!kayit__bekleyeni_gonder()) return;
    if (kayit__kuyruga(m)) return;
    kayit_bekleyen_m = *m;
    kayit_bekleyen = 1u;
}

/* ─────────────────────────────── noktaci (cekirdek 1) */
static KayitNoktaci kayit_kn;
static uint32_t kayit_kn_nesil = 0xFFFFFFFFu;
static uint8_t  kayit_kn_aktif = 0;

static void kayit__gonder(const KayitNokta *c)
{
    if (!kayit_nokta_q || xQueueSend(kayit_nokta_q, c, 0) != pdTRUE) {
        kn_kayip(&kayit_kn);                           /* sonraki nokta isaretli */
        kayit_kuyruk_dusen = kayit_kuyruk_dusen + 1u;
    }
}

static void kayit__nesil(uint32_t simdi, uint8_t menzil)
{
    KayitDurum d = kayit_durum_al();
    if (d.nesil == kayit_kn_nesil) return;
    kayit_kn_nesil = d.nesil;
    kayit_kn_aktif = (d.durum == KDR_KAYIT && d.hiz_ms) ? 1u : 0u;
    if (kayit_kn_aktif) kn_baslat(&kayit_kn, d.hiz_ms, simdi, menzil);
}

/* Her ornekte (loop, olcum_al'dan sonra). `ek`: ornege ait bayrak (KN_DCIR). */
static void kayit_ornek(float watt, uint32_t simdi, uint8_t ek)
{
    KayitNokta c;
    uint8_t hata = kayit_ham.hata;
    kayit__nesil(simdi, kayit_ham.menzil);
    if (!kayit_kn_aktif) return;
    if (!isfinite(watt)) hata |= (uint8_t)(KN_HATA_V | KN_HATA_I);   /* NaN int64'e cevrilemez */
    if (kn_ornek(&kayit_kn, simdi, kayit_ham.menzil, kayit_ham.ham_v, kayit_ham.ham_i,
                 watt, hata, kayit_ham.v_doydu, ek, &c))
        kayit__gonder(&c);
}

/* Skop ADS'i sustururken (loop'un erken donusu). */
static void kayit_duraklama(uint32_t simdi)
{
    KayitNokta c;
    kayit__nesil(simdi, kayit_ham.menzil);
    if (kayit_kn_aktif && kn_zaman(&kayit_kn, simdi, &c)) kayit__gonder(&c);
}

/* ─────────────────────────────── 1B: kalibrasyon gecmisi (cekirdek 1)
   Durum makinesi kalgec.h'de (B71.C'de sinaniyor). Burada NVS: ad alani
   `kalgec`, `adet` + `k1…k40`. Yazan yalniz cekirdek 1 (komut + kayit
   baslangici); /kal/liste kendi salt-okunur ornegini acar. */
static Preferences kalgec_nvs;
static KalGecmis   kalgec;
static uint8_t     kalgec_acik = 0;

static int kalgec_nvs_oku(void *b, const char *ad, void *h, uint32_t n)
{
    (void)b;
    if (!kalgec_acik || !kalgec_nvs.isKey(ad) || kalgec_nvs.getBytesLength(ad) != n) return -1;
    return kalgec_nvs.getBytes(ad, h, n) == n ? 0 : -1;
}

static int kalgec_nvs_yaz(void *b, const char *ad, const void *k, uint32_t n)
{
    (void)b;
    if (!kalgec_acik) return -1;
    return kalgec_nvs.putBytes(ad, k, n) == n ? 0 : -1;
}

/* NVS'te veri icin KALAN giris: available_entries GC'ye ayrilan sayfayi
   saymaz (free_entries sayar). 116 B'lik kayit 6 giris tutar. */
static uint32_t kalgec_nvs_bos(void *b)
{
    nvs_stats_t s;
    (void)b;
    return nvs_get_stats(NULL, &s) == ESP_OK ? (uint32_t)s.available_entries : 0u;
}

static int kalgec_kur(const KayitKalibrasyon *simdiki, uint32_t unix_s)
{
    static const KalNvs t = { kalgec_nvs_oku, kalgec_nvs_yaz, kalgec_nvs_bos, nullptr };
    kalgec_acik = kalgec_nvs.begin("kalgec", false) ? 1u : 0u;
    return kgc_ac(&kalgec, &t, simdiki, unix_s, 0u);
}

#endif /* KAYIT_ESP_H */
