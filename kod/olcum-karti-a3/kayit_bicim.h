#ifndef KAYIT_BICIM_H
#define KAYIT_BICIM_H
/*
 * B71 — KAYIT BICIMI, surum 1.
 *
 * Kartin flasa yazdigi ve telefon/PC'nin AYNEN sakladigi baytlarin TEK
 * tanimi. Platform bagimsiz: firmware (ESP32) ve AVR emulator testi
 * (uretim/test_kayit.py) ayni dosyayi derler. Python karsiligi
 * kopru/kayit_bicim.py; iki taraf ortak test vektorleriyle sinaniyor.
 * Tasarim: tasarim/2026-09-29-yazilim-sistemi.md §5.
 *
 * KAYIT = 16 bayt baslik + yuk + 0..3 bayt SIFIR dolgu (4'un katina):
 *    0  u8   imza 0xA5  (silinmis flas 0xFF: bos yer boyle taninir)
 *    1  u8   tur        KAYIT_T_*. BILINMEYEN tur de GECERLI (CRC karar
 *                       verir): 1C yeni turler ekleyecek, eski cozucu
 *                       onlari tasiyip atlamali, kaydi bozuk saymamali.
 *    2  u16  yuk_bayt
 *    4  u32  sira       kartin BUTUN kayitlari icin artan sira (>= 1),
 *                       asla tekrar verilmez
 *    8  u32  oturum     oturum kimligi = oturumun BASLA kaydinin sirasi;
 *                       0 = oturuma bagli degil
 *   12  u32  crc        CRC-32 (zlib.crc32 ile ayni): bayt 0..11 + yuk.
 *                       Dolgu CRC'ye GIRMEZ.
 *
 * NOKTA (36 bayt): kart_ms u32 · n u16 · bayrak u8 · 0 u8 ·
 *   V: ort f32 (HAM KOD) · min i16 · maks i16 (HAM KOD)
 *   A: ort f32 (HAM KOD) · min i16 · maks i16 (HAM KOD)
 *   W: ort f32 · min f32 · maks f32 (WATT — kayit anindaki kalibrasyonla)
 *
 * 🔴 ELLE PAKETLEME. Butun sayilar kucuk uclu, bayt bayt yaziliyor;
 *    memcpy(struct) YOK. AVR ile Xtensa'nin hizalama ve dolgu kurallari
 *    ayni olmak zorunda degil — struct kopyalamak iki mimaride farkli
 *    bayt dizisi uretebilirdi.
 * 🔴 Butun fonksiyonlar `static inline`: harness her fonksiyonu
 *    kullanmiyor; duz `static` -Wunused-function uyarisi verirdi ve
 *    zincir uyarisiz derleme istiyor.
 */
#include <stdint.h>
#include <string.h>

#define KAYIT_SURUM        2u   /* 1B: BASLA'da kal_no (surum 1 = 98 B, okunur) */
#define KAYIT_IMZA         0xA5u
#define KAYIT_BASLIK_BAYT  16u
#define KAYIT_NOKTA_BAYT   36u
#define KAYIT_BASLA_BAYT   102u
#define KAYIT_BASLA_V1_BAYT 98u  /* surum 1 (1A-2): kal_no yok */
#define KAYIT_KAL_BAYT     62u   /* kalibrasyon kopyasi (BASLA 36..97, kalgec) */
#define KAYIT_DEVAM_BAYT   16u
#define KAYIT_BITIR_BAYT   8u
#define KAYIT_SAAT_BAYT    12u

/* kayit turleri */
#define KAYIT_T_BASLA   1u   /* oturum basladi; kalibrasyon kopyasi burada */
#define KAYIT_T_NOKTA   2u   /* u32 ilk_nokta + N x 36 bayt nokta */
#define KAYIT_T_DEVAM   3u   /* kart yeniden basladi, oturum SURUYOR */
#define KAYIT_T_BITIR   4u   /* oturum bitti */
#define KAYIT_T_SAAT    5u   /* kart ms <-> unix eslemesi */
#define KAYIT_T_TEKRAR  6u   /* BASLA'nin sektor basi kopyasi (ayni yuk) */
#define KAYIT_T_OLAY    7u   /* 1C-1: oturum olayi (pil ayari, DCIR, pil sonucu) */
#define KAYIT_T_NOT     8u   /* 1C-1: oturuma ad/etiket/not (baslikta oturum 0) */
#define KAYIT_T_AYRINTI 9u   /* 1C-2: ayrintili kip — her ornek (hiz_ms 0) */
#define KAYIT_T_SKOP   10u   /* 1C-3: osiloskop yakalamasi, parca parca (0. parca META) */
#define KAYIT_T_AZAMI  10u   /* bilinen en buyuk tur (gecerlilik siniri DEGIL) */

/* nokta bayraklari */
#define KN_YUKSEK      0x01u  /* nokta YUKSEK gerilim menzilinde */
#define KN_V_HATA      0x02u  /* en az bir ornekte gerilim ADS'i okunamadi */
#define KN_I_HATA      0x04u  /* en az bir ornekte akim ADS'i okunamadi */
#define KN_V_DOYDU     0x08u  /* en az bir gerilim ornegi doydu */
#define KN_DURAKLAMA   0x10u  /* bu noktadan once/icinde olcum durdu */
#define KN_KAYIP_ONCE  0x20u  /* bundan ONCEKI noktalar kuyrukta dustu */
#define KN_DCIR        0x40u  /* 1C-1: en az bir ornek DCIR darbesinde (yuk KAPALI) */

/* BITIR sebepleri */
#define KB_SEBEP_KULLANICI 1u
#define KB_SEBEP_DOLU      2u
#define KB_SEBEP_HATA      3u
#define KB_SEBEP_PIL       4u   /* pil testi kendi bitti (kesme/emniyet; ayrinti SONUC'ta) */
#define KB_SEBEP_YENIDEN   5u   /* kart yeniden basladi: surdurulmeyen oturum acilista kapandi */
#define KB_SEBEP_OTURUM    6u   /* baska bir oturum basladi */
#define KB_SEBEP_PLAN      7u   /* 1C-4: zamanlanmis kaydin suresi doldu */

#define KAYIT_OTURUM_OLCUM 1u   /* BASLA.oturum_turu: V/A/W olcum kaydi */
#define KAYIT_OTURUM_PIL   2u   /* 1C-1: pil testi (noktalar + OLAY'lar); yeniden baslamada SURMEZ */
#define KAYIT_OTURUM_SKOP  3u   /* 1C-3: osiloskop gunlugu (yalniz SKOP kayitlari); hiz_ms =
                                   aralik (0 = her tetik); yeniden baslamada SURMEZ */
#define KAYIT_KAL_BICIM    1u   /* BASLA.kal_bicim: KayitKalibrasyon v1 */

/* ─────────────────────────────── kucuk uclu elle paketleme */
static inline void kayit_y16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}

static inline void kayit_y32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static inline uint16_t kayit_o16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8));
}

static inline uint32_t kayit_o32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
         | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline void kayit_yf(uint8_t *p, float f)
{
    uint32_t u;
    memcpy(&u, &f, 4);
    kayit_y32(p, u);
}

static inline float kayit_of(const uint8_t *p)
{
    uint32_t u = kayit_o32(p);
    float f;
    memcpy(&f, &u, 4);
    return f;
}

/* Kaydin flasta kapladigi toplam bayt: baslik + yuk, 4'un katina. */
static inline uint32_t kayit_toplam_bayt(uint32_t yuk_bayt)
{
    return (KAYIT_BASLIK_BAYT + yuk_bayt + 3u) & ~(uint32_t)3u;
}

/* ─────────────────────────────── CRC-32 (ISO-HDLC, zlib ile ayni)
 * Yarim bayt (nibble) tablosu: 64 bayt. AVR'de 256'lik tablo 1 KB RAM
 * yerdi; bitsel dongu ise emulatorde 4 kat yavasti. */
static const uint32_t KAYIT_CRC_TABLO[16] = {
    0x00000000u, 0x1DB71064u, 0x3B6E20C8u, 0x26D930ACu,
    0x76DC4190u, 0x6B6B51F4u, 0x4DB26158u, 0x5005713Cu,
    0xEDB88320u, 0xF00F9344u, 0xD6D6A3E8u, 0xCB61B38Cu,
    0x9B64C2B0u, 0x86D3D2D4u, 0xA00AE278u, 0xBDBDF21Cu,
};

/* zlib.crc32(veri, crc) ile ayni: parca parca cagrilabilir. */
static inline uint32_t kayit_crc_ekle(uint32_t crc, const uint8_t *p, uint32_t n)
{
    crc = ~crc;
    while (n--) {
        crc ^= *p++;
        crc = (crc >> 4) ^ KAYIT_CRC_TABLO[crc & 15u];
        crc = (crc >> 4) ^ KAYIT_CRC_TABLO[crc & 15u];
    }
    return ~crc;
}

/* ─────────────────────────────── baslik */
typedef struct {
    uint8_t  tur;
    uint16_t yuk_bayt;
    uint32_t sira;
    uint32_t oturum;
    uint32_t crc;
} KayitBaslik;

/* `b` 16 bayt. CRC baslik (0..11) + yuk uzerinden hesaplanir. */
static inline void kayit_baslik_yaz(uint8_t *b, uint8_t tur, uint32_t sira,
                                    uint32_t oturum, const uint8_t *yuk,
                                    uint16_t yuk_bayt)
{
    uint32_t c;
    b[0] = (uint8_t)KAYIT_IMZA;
    b[1] = tur;
    kayit_y16(b + 2, yuk_bayt);
    kayit_y32(b + 4, sira);
    kayit_y32(b + 8, oturum);
    c = kayit_crc_ekle(0u, b, 12u);
    c = kayit_crc_ekle(c, yuk, yuk_bayt);
    kayit_y32(b + 12, c);
}

/* 1 = gecerli GORUNEN baslik, 0 = bos (16 bayt 0xFF), -1 = cop.
   CRC burada DENETLENMEZ: yuk okunmadan denetlenemez. */
static inline int8_t kayit_baslik_coz(const uint8_t *b, KayitBaslik *h)
{
    uint8_t i, hepsi_ff = 1u;
    for (i = 0; i < KAYIT_BASLIK_BAYT; i++) {
        if (b[i] != 0xFFu) { hepsi_ff = 0u; break; }
    }
    if (hepsi_ff) return 0;
    if (b[0] != KAYIT_IMZA) return -1;
    if (b[1] == 0u || b[1] == 0xFFu) return -1;   /* bilinmeyen tur gecerli; CRC karar verir */
    h->tur = b[1];
    h->yuk_bayt = kayit_o16(b + 2);
    h->sira = kayit_o32(b + 4);
    h->oturum = kayit_o32(b + 8);
    h->crc = kayit_o32(b + 12);
    if (h->sira == 0u || h->sira == 0xFFFFFFFFUL) return -1;
    return 1;
}

/* ─────────────────────────────── nokta */
typedef struct {
    uint32_t kart_ms;      /* noktanin BITTIGI an (millis) */
    uint16_t n;            /* gecerli ornek sayisi */
    uint8_t  bayrak;       /* KN_* */
    float    v_ort_kod;
    int16_t  v_min_kod, v_maks_kod;
    float    i_ort_kod;
    int16_t  i_min_kod, i_maks_kod;
    float    w_ort, w_min, w_maks;
} KayitNokta;

static inline void kayit_nokta_paketle(const KayitNokta *k, uint8_t *p)
{
    kayit_y32(p, k->kart_ms);
    kayit_y16(p + 4, k->n);
    p[6] = k->bayrak;
    p[7] = 0u;
    kayit_yf(p + 8, k->v_ort_kod);
    kayit_y16(p + 12, (uint16_t)k->v_min_kod);
    kayit_y16(p + 14, (uint16_t)k->v_maks_kod);
    kayit_yf(p + 16, k->i_ort_kod);
    kayit_y16(p + 20, (uint16_t)k->i_min_kod);
    kayit_y16(p + 22, (uint16_t)k->i_maks_kod);
    kayit_yf(p + 24, k->w_ort);
    kayit_yf(p + 28, k->w_min);
    kayit_yf(p + 32, k->w_maks);
}

static inline void kayit_nokta_coz(const uint8_t *p, KayitNokta *k)
{
    k->kart_ms = kayit_o32(p);
    k->n = kayit_o16(p + 4);
    k->bayrak = p[6];
    k->v_ort_kod = kayit_of(p + 8);
    k->v_min_kod = (int16_t)kayit_o16(p + 12);
    k->v_maks_kod = (int16_t)kayit_o16(p + 14);
    k->i_ort_kod = kayit_of(p + 16);
    k->i_min_kod = (int16_t)kayit_o16(p + 20);
    k->i_maks_kod = (int16_t)kayit_o16(p + 22);
    k->w_ort = kayit_of(p + 24);
    k->w_min = kayit_of(p + 28);
    k->w_maks = kayit_of(p + 32);
}

/* ─────────────────────────────── BASLA (102 bayt; surum 1 = 98)
 *    0 u8 oturum_turu · 1 u8 kal_bicim · 2 u16 bicim surumu (KAYIT_SURUM) ·
 *    4 u32 hiz_ms ·
 *    8 u32 unix_s (0 = bilinmiyor) · 12 u32 kart_ms · 16 u32 acilis ·
 *   20 char[16] surum · 36 kalibrasyon v1 (62 bayt):
 *   36 kanal normal (n f32, pga f32, kazanc f32, sifir_ham i16, tau f32)
 *   54 kanal yuksek · 72 i_ofset i16 · 74 i_pga · 78 sont_ohm ·
 *   82 i_duzeltme · 86 sebeke_hz · 90 faz_kal_us[0] · 94 faz_kal_us[1]
 *   98 u32 kal_no — kalibrasyon GECMISINDEKI numara (1B; 0 = bilinmiyor:
 *      surum 1 ya da gecmis dolu). Surum 1 (98 B) okunur, kal_no 0.
 * Kalibrasyon kopyasi olc_gerilim3/olc_akim3'un (olcum3.h) girdilerinin
 * TAMAMI: kayit hangi cihaza giderse gitsin kendi ham kodunu volta
 * cevirebilir (tasarim §7). */
typedef struct {
    float   n, pga, kazanc;
    int16_t sifir_ham;
    float   tau;
} KayitKanal;

typedef struct {
    KayitKanal normal, yuksek;
    int16_t    i_ofset;
    float      i_pga, sont_ohm, i_duzeltme, sebeke_hz;
    float      faz_kal_us[2];
} KayitKalibrasyon;

typedef struct {
    uint8_t  oturum_turu, kal_bicim;
    uint16_t bicim_surum;          /* cozulen kayitta: yazildigi bicim (KAYIT_SURUM) */
    uint32_t hiz_ms, unix_s, kart_ms, acilis;
    char     surum[16];
    KayitKalibrasyon kal;
    uint32_t kal_no;               /* 1B: kalibrasyon gecmisindeki numara (0 = bilinmiyor) */
} KayitBasla;

static inline void kayit__kanal_yaz(uint8_t *p, const KayitKanal *k)
{
    kayit_yf(p, k->n);
    kayit_yf(p + 4, k->pga);
    kayit_yf(p + 8, k->kazanc);
    kayit_y16(p + 12, (uint16_t)k->sifir_ham);
    kayit_yf(p + 14, k->tau);
}

static inline void kayit__kanal_oku(const uint8_t *p, KayitKanal *k)
{
    k->n = kayit_of(p);
    k->pga = kayit_of(p + 4);
    k->kazanc = kayit_of(p + 8);
    k->sifir_ham = (int16_t)kayit_o16(p + 12);
    k->tau = kayit_of(p + 14);
}

/* Kalibrasyon kopyasi (62 bayt) — BASLA 36..97 ve kalibrasyon gecmisi
   (kalgec.h) AYNI paketi kullanir. */
static inline void kayit_kal_paketle(const KayitKalibrasyon *k, uint8_t *p)
{
    kayit__kanal_yaz(p, &k->normal);
    kayit__kanal_yaz(p + 18, &k->yuksek);
    kayit_y16(p + 36, (uint16_t)k->i_ofset);
    kayit_yf(p + 38, k->i_pga);
    kayit_yf(p + 42, k->sont_ohm);
    kayit_yf(p + 46, k->i_duzeltme);
    kayit_yf(p + 50, k->sebeke_hz);
    kayit_yf(p + 54, k->faz_kal_us[0]);
    kayit_yf(p + 58, k->faz_kal_us[1]);
}

static inline void kayit_kal_coz(const uint8_t *p, KayitKalibrasyon *k)
{
    kayit__kanal_oku(p, &k->normal);
    kayit__kanal_oku(p + 18, &k->yuksek);
    k->i_ofset = (int16_t)kayit_o16(p + 36);
    k->i_pga = kayit_of(p + 38);
    k->sont_ohm = kayit_of(p + 42);
    k->i_duzeltme = kayit_of(p + 46);
    k->sebeke_hz = kayit_of(p + 50);
    k->faz_kal_us[0] = kayit_of(p + 54);
    k->faz_kal_us[1] = kayit_of(p + 58);
}

static inline void kayit_basla_paketle(const KayitBasla *b, uint8_t *p)
{
    p[0] = b->oturum_turu;
    p[1] = b->kal_bicim;
    kayit_y16(p + 2, (uint16_t)KAYIT_SURUM);   /* kayit hangi bicimde yazildigini soyler */
    kayit_y32(p + 4, b->hiz_ms);
    kayit_y32(p + 8, b->unix_s);
    kayit_y32(p + 12, b->kart_ms);
    kayit_y32(p + 16, b->acilis);
    memcpy(p + 20, b->surum, 16);
    kayit_kal_paketle(&b->kal, p + 36);
    kayit_y32(p + 98, b->kal_no);
}

/* `n`: yuk uzunlugu — 102 (surum 2) ya da 98 (surum 1: kal_no yok -> 0). */
static inline void kayit_basla_coz(const uint8_t *p, uint16_t n, KayitBasla *b)
{
    b->oturum_turu = p[0];
    b->kal_bicim = p[1];
    b->bicim_surum = kayit_o16(p + 2);
    b->hiz_ms = kayit_o32(p + 4);
    b->unix_s = kayit_o32(p + 8);
    b->kart_ms = kayit_o32(p + 12);
    b->acilis = kayit_o32(p + 16);
    memcpy(b->surum, p + 20, 16);
    kayit_kal_coz(p + 36, &b->kal);
    b->kal_no = (n >= KAYIT_BASLA_BAYT) ? kayit_o32(p + 98) : 0u;
}

/* ─────────────────────────────── DEVAM (16) · BITIR (8) · SAAT (12) */
typedef struct { uint32_t acilis, unix_s, kart_ms, nokta_sira; } KayitDevam;
typedef struct { uint32_t nokta_adedi; uint8_t sebep; } KayitBitir;
typedef struct { uint32_t unix_s, kart_ms, acilis; } KayitSaat;

static inline void kayit_devam_paketle(const KayitDevam *d, uint8_t *p)
{
    kayit_y32(p, d->acilis);
    kayit_y32(p + 4, d->unix_s);
    kayit_y32(p + 8, d->kart_ms);
    kayit_y32(p + 12, d->nokta_sira);
}

static inline void kayit_devam_coz(const uint8_t *p, KayitDevam *d)
{
    d->acilis = kayit_o32(p);
    d->unix_s = kayit_o32(p + 4);
    d->kart_ms = kayit_o32(p + 8);
    d->nokta_sira = kayit_o32(p + 12);
}

static inline void kayit_bitir_paketle(const KayitBitir *b, uint8_t *p)
{
    kayit_y32(p, b->nokta_adedi);
    p[4] = b->sebep;
    p[5] = 0u;
    p[6] = 0u;
    p[7] = 0u;
}

static inline void kayit_bitir_coz(const uint8_t *p, KayitBitir *b)
{
    b->nokta_adedi = kayit_o32(p);
    b->sebep = p[4];
}

static inline void kayit_saat_paketle(const KayitSaat *s, uint8_t *p)
{
    kayit_y32(p, s->unix_s);
    kayit_y32(p + 4, s->kart_ms);
    kayit_y32(p + 8, s->acilis);
}

static inline void kayit_saat_coz(const uint8_t *p, KayitSaat *s)
{
    s->unix_s = kayit_o32(p);
    s->kart_ms = kayit_o32(p + 4);
    s->acilis = kayit_o32(p + 8);
}

/* ─────────────────────────────── METIN (1B'nin not temizleyicisi, genel)
 * `s`'deki UTF-8 karakterinin bayt sayisi; gecersizse 0. RFC 3629 tablosu:
 * asiri uzun kodlama, vekil (D800-DFFF) ve 10FFFF ustu GECERSIZ (Python'un
 * cozucusu da reddeder). NUL'dan otesini okumaz: her devam bayti okunmadan
 * once oncekinin NUL olmadigi dogrulanmis. */
static inline uint8_t kayit__utf8(const uint8_t *s)
{
    uint8_t c = s[0], uz, i, alt = 0x80u, ust = 0xBFu;
    if (c < 0x80u) return 1u;
    if (c >= 0xC2u && c <= 0xDFu) {
        uz = 2u;
    } else if (c >= 0xE0u && c <= 0xEFu) {
        uz = 3u;
        if (c == 0xE0u) alt = 0xA0u;
        else if (c == 0xEDu) ust = 0x9Fu;
    } else if (c >= 0xF0u && c <= 0xF4u) {
        uz = 4u;
        if (c == 0xF0u) alt = 0x90u;
        else if (c == 0xF4u) ust = 0x8Fu;
    } else {
        return 0u;
    }
    if (s[1] < alt || s[1] > ust) return 0u;
    for (i = 2u; i < uz; i++)
        if ((s[i] & 0xC0u) != 0x80u) return 0u;
    return uz;
}

/* Metni kopyala: gecersiz UTF-8 bayti (orn. cp1254 terminalden 'ş' = FE),
   kontrol karakterleri, `"` ve `\` atilir — JSON'a kacissiz ve PC'de hep
   cozulur. `d`'de `azami` bayt var: en fazla azami-1 bayt metin, sigmayan
   karakterde (karakter SINIRINDA) kesilir; geri kalani sifir. Donus: uzunluk. */
static inline uint8_t kayit_metin_kopyala(char *d, const char *s, uint8_t azami)
{
    const uint8_t *p = (const uint8_t *)s;
    uint8_t n = 0u, uz, c;
    if (p) {
        while ((c = *p) != 0u) {
            uz = kayit__utf8(p);
            if (!uz || (uz == 1u && (c < 0x20u || c == 0x7Fu || c == (uint8_t)'"'
                                     || c == (uint8_t)'\\'))) {
                p++;
                continue;
            }
            if ((uint16_t)(n + uz) > (uint16_t)(azami - 1u)) break;
            memcpy(d + n, p, uz);
            n = (uint8_t)(n + uz);
            p += uz;
        }
    }
    memset(d + n, 0, (size_t)(azami - n));
    return n;
}

/* ─────────────────────────────── OLAY (1C-1)
 *    0 u8 olay_tur · 1 u8 0 · 2 u16 0 · 4 u32 kart_ms · 8.. ture ozel
 *    KO_PIL_AYAR  (32 B) 8 f32 kesme_v · 12 f32 ocv · 16 u32 azami_s ·
 *                 20 u32 dcir_aralik_ms · 24 u32 dcir_ms · 28 f32 kayit_hz
 *    KO_DCIR      (44 B) 8 u32 no · 12 f32 v_once · 16 f32 i_once · 20 f32 v_ani ·
 *                 24 f32 v_oturmus · 28 f32 r_ani · 32 f32 r_oturmus ·
 *                 36 f32 mah · 40 f32 wh   (mah/wh: o ana kadarki)
 *    KO_PIL_SONUC (36 B) 8 u8 durum · 9 u8 hata · 10 u16 0 · 12 f32 mah ·
 *                 16 f32 wh · 20 f32 ocv · 24 f32 v_son · 28 u32 sure_ms ·
 *                 32 u32 dcir_sayisi
 * Volt/amper KALIBRE (kartin o anki hesabi); ham kod noktalarda. */
#define KO_PIL_AYAR  1u
#define KO_DCIR      2u
#define KO_PIL_SONUC 3u
#define KO_PLAN      5u   /* 1C-4: 8 u32 bas_unix · 12 u32 sure_s · 16 u32 hiz_ms · 20 u32 plan_no */
#define KO_SKOP_KAL  4u   /* 1C-3: 8 i16 mv[17] — skop ADC'nin eFuse egrisi (kal_mv_tab) */
#define KAYIT_OLAY_AYAR_BAYT  32u
#define KAYIT_OLAY_DCIR_BAYT  44u
#define KAYIT_OLAY_SONUC_BAYT 36u
#define KAYIT_OLAY_SKOP_KAL_BAYT 42u
#define KAYIT_OLAY_PLAN_BAYT  24u
#define KAYIT_SKOP_KAL_N      17u
#define KAYIT_OLAY_AZAMI      44u

typedef struct {
    float    kesme_v, ocv;
    uint32_t azami_s, dcir_aralik_ms, dcir_ms;
    float    kayit_hz;
} KayitPilAyar;

typedef struct {
    uint32_t no;
    float    v_once, i_once, v_ani, v_oturmus, r_ani, r_oturmus, mah, wh;
} KayitDcir;

typedef struct {
    uint8_t  durum, hata;
    float    mah, wh, ocv, v_son;
    uint32_t sure_ms, dcir_sayisi;
} KayitPilSonuc;

static inline void kayit__olay_bas(uint8_t *p, uint8_t tur, uint32_t kart_ms)
{
    p[0] = tur;
    p[1] = 0u;
    p[2] = 0u;
    p[3] = 0u;
    kayit_y32(p + 4, kart_ms);
}

static inline uint16_t kayit_olay_ayar_paketle(uint32_t kart_ms, const KayitPilAyar *a,
                                               uint8_t *p)
{
    kayit__olay_bas(p, (uint8_t)KO_PIL_AYAR, kart_ms);
    kayit_yf(p + 8, a->kesme_v);
    kayit_yf(p + 12, a->ocv);
    kayit_y32(p + 16, a->azami_s);
    kayit_y32(p + 20, a->dcir_aralik_ms);
    kayit_y32(p + 24, a->dcir_ms);
    kayit_yf(p + 28, a->kayit_hz);
    return (uint16_t)KAYIT_OLAY_AYAR_BAYT;
}

static inline uint16_t kayit_olay_dcir_paketle(uint32_t kart_ms, const KayitDcir *d,
                                               uint8_t *p)
{
    kayit__olay_bas(p, (uint8_t)KO_DCIR, kart_ms);
    kayit_y32(p + 8, d->no);
    kayit_yf(p + 12, d->v_once);
    kayit_yf(p + 16, d->i_once);
    kayit_yf(p + 20, d->v_ani);
    kayit_yf(p + 24, d->v_oturmus);
    kayit_yf(p + 28, d->r_ani);
    kayit_yf(p + 32, d->r_oturmus);
    kayit_yf(p + 36, d->mah);
    kayit_yf(p + 40, d->wh);
    return (uint16_t)KAYIT_OLAY_DCIR_BAYT;
}

typedef struct {
    uint32_t bas_unix, sure_s, hiz_ms, plan_no;
} KayitPlanOlay;

static inline uint16_t kayit_olay_plan_paketle(uint32_t kart_ms, const KayitPlanOlay *o,
                                               uint8_t *p)
{
    kayit__olay_bas(p, (uint8_t)KO_PLAN, kart_ms);
    kayit_y32(p + 8, o->bas_unix);
    kayit_y32(p + 12, o->sure_s);
    kayit_y32(p + 16, o->hiz_ms);
    kayit_y32(p + 20, o->plan_no);
    return (uint16_t)KAYIT_OLAY_PLAN_BAYT;
}

/* Y2: PLAN olayinin plan numarasi (kayit_olay_plan_paketle'nin tersi, tek alan) */
static inline uint32_t kayit_olay_plan_no(const uint8_t *p)
{
    return kayit_o32(p + 20);
}

static inline uint16_t kayit_olay_skop_kal_paketle(uint32_t kart_ms, const int16_t *mv,
                                                   uint8_t *p)
{
    uint32_t j;
    kayit__olay_bas(p, (uint8_t)KO_SKOP_KAL, kart_ms);
    for (j = 0u; j < KAYIT_SKOP_KAL_N; j++) kayit_y16(p + 8u + 2u * j, (uint16_t)mv[j]);
    return (uint16_t)KAYIT_OLAY_SKOP_KAL_BAYT;
}

static inline uint16_t kayit_olay_sonuc_paketle(uint32_t kart_ms, const KayitPilSonuc *s,
                                                uint8_t *p)
{
    kayit__olay_bas(p, (uint8_t)KO_PIL_SONUC, kart_ms);
    p[8] = s->durum;
    p[9] = s->hata;
    p[10] = 0u;
    p[11] = 0u;
    kayit_yf(p + 12, s->mah);
    kayit_yf(p + 16, s->wh);
    kayit_yf(p + 20, s->ocv);
    kayit_yf(p + 24, s->v_son);
    kayit_y32(p + 28, s->sure_ms);
    kayit_y32(p + 32, s->dcir_sayisi);
    return (uint16_t)KAYIT_OLAY_SONUC_BAYT;
}

/* ─────────────────────────────── NOT (1C-1): oturuma ad / etiket / not
 *    0 u32 hedef_oturum · 4 u8 alan (KNT_*) · 5 u8 0 · 6 u16 0 ·
 *    8 u32 nokta_ms (not: grafikteki kart_ms; 0 = oturumun geneli) ·
 *   12 u32 degistirir (0 = yeni; > 0 = ASIL notun (ilk yazilan NOT kaydinin)
 *                      sirasi: onun yerine gecer, metin bossa onu SILER) ·
 *   16 metin (UTF-8, <= 120 B, NUL'suz)
 * Baslikta oturum 0: baska oturum surerken de yazilir. Kart YORUMLAMAZ; son
 * hali PC kurar (kopru/kayit_bicim.py _not_uygula, ortak/ ayni kurali tasir):
 *   ad/etiket: en son kayit gecerli · not: `degistirir` ASIL sirayi gosterir
 *   (duzeltilmis bir not yine asil sirasiyla hedeflenir); duzeltmede nokta_ms 0
 *   = notun grafik yeri KORUNUR; bilinmeyen/silinmis sira YOK SAYILIR (hayalet
 *   not uretmez). */
#define KNT_AD     1u
#define KNT_ETIKET 2u
#define KNT_NOT    3u
#define KAYIT_NOT_BAS   16u
#define KAYIT_NOT_METIN 120u

/* `p` en az KAYIT_NOT_BAS + KAYIT_NOT_METIN + 1 bayt. Donus: yuk uzunlugu. */
static inline uint16_t kayit_not_paketle(uint32_t hedef, uint8_t alan, uint32_t nokta_ms,
                                         uint32_t degistirir, const char *metin, uint8_t *p)
{
    uint8_t n;
    kayit_y32(p, hedef);
    p[4] = alan;
    p[5] = 0u;
    p[6] = 0u;
    p[7] = 0u;
    kayit_y32(p + 8, nokta_ms);
    kayit_y32(p + 12, degistirir);
    n = kayit_metin_kopyala((char *)(p + KAYIT_NOT_BAS), metin,
                            (uint8_t)(KAYIT_NOT_METIN + 1u));
    return (uint16_t)(KAYIT_NOT_BAS + n);
}

/* ─────────────────────────────── NOT KOMUTU (1C-1 son inceleme)
 * Kartin seri/web komutu Ga/Ge/Gn/Gx — platformsuz ki bozuk argumanlar AVR'de
 * sinansin (B71.B21). Sayilar YALNIZ rakam: isaret, bosluk, bos sayi, 32 bit
 * tasmasi ve 0 oturum/sira REDDEDILIR (strtoul hepsini sessizce kabul edip
 * kayit yazdiriyordu). Bozuk argumanda kayit YAZILMAZ.
 *   Ga<oturum>[ <ad>]                         ad (bos: adi siler)
 *   Ge<oturum>[ <etiket, ...>]                etiketler (bos: siler)
 *   Gn<oturum>[@<kart_ms>] <not>              yeni not, metin ZORUNLU
 *   Gx<oturum>:<sira>[@<kart_ms>][ <metin>]   ASIL <sira>'daki notu degistir
 *                                             (@ yoksa grafik yeri korunur);
 *                                             metin bossa SIL */
#define KNK_TAMAM  0u
#define KNK_OTURUM 1u   /* oturum numarasi yok / 0 / rakam disi / tasma */
#define KNK_SIRA   2u   /* Gx: ':' + sira yok / 0 / rakam disi */
#define KNK_ZAMAN  3u   /* '@' sonrasi rakam yok */
#define KNK_METIN  4u   /* numaradan sonra bosluk yok ya da Gn metni bos */
#define KNK_ALT    5u   /* a/e/n/x degil */

typedef struct {
    uint8_t     alan;
    uint32_t    hedef, nokta_ms, degistirir;
    const char *metin;
} KayitNotKomut;

/* Yalniz rakam; en az bir rakam, 32 bit tasmasi yok. Basarida *p ilerler. */
static inline uint8_t kayit__rakam(const char **p, uint32_t *v)
{
    const char *s = *p;
    uint32_t x = 0u, d;
    uint8_t n = 0u;
    while (*s >= '0' && *s <= '9') {
        d = (uint32_t)(*s - '0');
        if (x > (0xFFFFFFFFUL - d) / 10u) return 0u;
        x = x * 10u + d;
        s++;
        n++;
    }
    if (!n) return 0u;
    *p = s;
    *v = x;
    return 1u;
}

static inline uint8_t kayit_not_ayir(const char *s, KayitNotKomut *k)
{
    const char *p;
    char a;
    memset(k, 0, sizeof(*k));
    if (s[0] != 'G') return KNK_ALT;
    a = s[1];
    if (a == 'a') k->alan = KNT_AD;
    else if (a == 'e') k->alan = KNT_ETIKET;
    else if (a == 'n' || a == 'x') k->alan = KNT_NOT;
    else return KNK_ALT;
    p = s + 2;
    if (!kayit__rakam(&p, &k->hedef) || !k->hedef) return KNK_OTURUM;
    if (a == 'x') {
        if (*p != ':') return KNK_SIRA;
        p++;
        if (!kayit__rakam(&p, &k->degistirir) || !k->degistirir) return KNK_SIRA;
    }
    if ((a == 'n' || a == 'x') && *p == '@') {
        p++;
        if (!kayit__rakam(&p, &k->nokta_ms)) return KNK_ZAMAN;
    }
    if (*p == ' ') p++;
    else if (*p) return KNK_METIN;
    if (a == 'n' && !*p) return KNK_METIN;
    k->metin = p;
    return KNK_TAMAM;
}

/* ─────────────────────────────── AYRINTI (1C-2): her ornek
 *    0 u32 ilk_ornek (oturumdaki sirasi) · 4 u32 t0_ms · 8 u32 t0_us (micros,
 *    alt 32 bit) · 12 u16 adet · 14 u8 bayrak (KA_*) · 15 u8 0 ·
 *   16 + 6k: i16 v_kod · i16 i_kod · u16 (dt4 << 4 | KAO_*)
 * dt4: onceki ornekten bu yana 4 us birimi, 12 bit (<= 16.38 ms; ilk ornekte 0).
 * Daha buyuk bosluk YENI kayit acar: bosluk t0'dan okunur, gizlenmez. Ornegin
 * zamani t0_us + 4 x (dt4 toplami); t0_ms micros sarmasini (71.6 dk) cozer. */
#define KAYIT_AYRINTI_BAS      16u
#define KAYIT_AYRINTI_ORNEK    6u
#define KAYIT_AYRINTI_DT_AZAMI 4095u
#define KA_KAYIP_ONCE 0x01u   /* onceki kayittan beri ornek DUSTU (halka tasti) */
#define KA_SILME      0x02u   /* bu kaydin ILK ornegi, kafanin kirli sektor silmesinden
                                 (~25 ms, iki cekirdek durur) SONRA uretildi: ilk ornegin
                                 onundeki bosluk o silmedir */
#define KAO_YUKSEK    0x1u    /* ornek: yuksek gerilim menzili */
#define KAO_V_HATA    0x2u
#define KAO_I_HATA    0x4u
#define KAO_V_DOYDU   0x8u

static inline void kayit_ayrinti_bas_paketle(uint8_t *p, uint32_t ilk, uint32_t t0_ms,
                                             uint32_t t0_us, uint16_t adet, uint8_t bayrak)
{
    kayit_y32(p, ilk);
    kayit_y32(p + 4, t0_ms);
    kayit_y32(p + 8, t0_us);
    kayit_y16(p + 12, adet);
    p[14] = bayrak;
    p[15] = 0u;
}

static inline void kayit_ayrinti_ornek_paketle(uint8_t *p, int16_t v, int16_t i, uint16_t dt4,
                                               uint8_t bayrak)
{
    kayit_y16(p, (uint16_t)v);
    kayit_y16(p + 2, (uint16_t)i);
    kayit_y16(p + 4, (uint16_t)((uint16_t)(dt4 << 4) | (uint16_t)(bayrak & 0x0Fu)));
}

/* ─────────────────────────────── SKOP (1C-3): osiloskop yakalamasi
 * Bir yakalama (<= 4000 ham kod, u16) PARCA PARCA yazilir; kayit siniri
 * 4096 B ve yazicinin tamponu 1012 B. Her parca:
 *    0 u32 no (oturumdaki yakalama sirasi, 1'den) · 4 u16 ilk (parcanin ilk
 *    orneginin indeksi) · 6 u16 adet · 8 u16 toplam · 10 u8 parca · 11 u8 0
 *    12 [yalniz 0. parca] META 36 B:
 *       u32 t_ms (istek ani, kart_ms — ADS burada susar) · u32 sure_ms (istekten
 *       sonuca) · u32 hz · u32 tdiv_us · f32 adim · f32 ofset · u16 tetik ·
 *       u16 esik · u16 histerezis · u8 kip · tetiklendi · kenar · on_yuzde · onay · 0
 *       (histerezis u16: SkopAyar'da u16 — kirpilmasin)
 *    + u16 kod x adet
 * `adim`/`ofset` `/skop.bin` ile ayni (nominal); egri OLAY KO_SKOP_KAL'da. PC
 * eksik parcayi doldurmaz: yakalama "tam" degil (kopru/kayit_bicim.py). */
#define KAYIT_SKOP_PARCA_BAS 12u
#define KAYIT_SKOP_META      36u
#define KAYIT_SKOP_AZAMI     4000u

typedef struct {
    uint32_t t_ms, sure_ms, hz, tdiv_us;
    float    adim, ofset;
    uint16_t tetik, esik, histerezis;
    uint8_t  kip, tetiklendi, kenar, on_yuzde, onay;
} KayitSkopMeta;

static inline void kayit_skop_parca_paketle(uint8_t *p, uint32_t no, uint16_t ilk, uint16_t adet,
                                            uint16_t toplam, uint8_t parca)
{
    kayit_y32(p, no);
    kayit_y16(p + 4, ilk);
    kayit_y16(p + 6, adet);
    kayit_y16(p + 8, toplam);
    p[10] = parca;
    p[11] = 0u;
}

static inline void kayit_skop_meta_paketle(uint8_t *p, const KayitSkopMeta *m)
{
    kayit_y32(p, m->t_ms);
    kayit_y32(p + 4, m->sure_ms);
    kayit_y32(p + 8, m->hz);
    kayit_y32(p + 12, m->tdiv_us);
    kayit_yf(p + 16, m->adim);
    kayit_yf(p + 20, m->ofset);
    kayit_y16(p + 24, m->tetik);
    kayit_y16(p + 26, m->esik);
    kayit_y16(p + 28, m->histerezis);
    p[30] = m->kip;
    p[31] = m->tetiklendi;
    p[32] = m->kenar;
    p[33] = m->on_yuzde;
    p[34] = m->onay;
    p[35] = 0u;
}

#endif /* KAYIT_BICIM_H */
