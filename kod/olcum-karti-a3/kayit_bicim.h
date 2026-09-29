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
 *    1  u8   tur        KAYIT_T_*
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

#define KAYIT_SURUM        1u
#define KAYIT_IMZA         0xA5u
#define KAYIT_BASLIK_BAYT  16u
#define KAYIT_NOKTA_BAYT   36u
#define KAYIT_BASLA_BAYT   98u
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
#define KAYIT_T_AZAMI   6u

/* nokta bayraklari */
#define KN_YUKSEK      0x01u  /* nokta YUKSEK gerilim menzilinde */
#define KN_V_HATA      0x02u  /* en az bir ornekte gerilim ADS'i okunamadi */
#define KN_I_HATA      0x04u  /* en az bir ornekte akim ADS'i okunamadi */
#define KN_V_DOYDU     0x08u  /* en az bir gerilim ornegi doydu */
#define KN_DURAKLAMA   0x10u  /* bu noktadan once/icinde olcum durdu */
#define KN_KAYIP_ONCE  0x20u  /* bundan ONCEKI noktalar kuyrukta dustu */

/* BITIR sebepleri */
#define KB_SEBEP_KULLANICI 1u
#define KB_SEBEP_DOLU      2u
#define KB_SEBEP_HATA      3u

#define KAYIT_OTURUM_OLCUM 1u   /* BASLA.oturum_turu: V/A/W olcum kaydi */
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
    if (b[1] < 1u || b[1] > KAYIT_T_AZAMI) return -1;
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

/* ─────────────────────────────── BASLA (98 bayt)
 *    0 u8 oturum_turu · 1 u8 kal_bicim · 2 u16 0 · 4 u32 hiz_ms ·
 *    8 u32 unix_s (0 = bilinmiyor) · 12 u32 kart_ms · 16 u32 acilis ·
 *   20 char[16] surum · 36 kalibrasyon v1 (62 bayt):
 *   36 kanal normal (n f32, pga f32, kazanc f32, sifir_ham i16, tau f32)
 *   54 kanal yuksek · 72 i_ofset i16 · 74 i_pga · 78 sont_ohm ·
 *   82 i_duzeltme · 86 sebeke_hz · 90 faz_kal_us[0] · 94 faz_kal_us[1]
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
    uint32_t hiz_ms, unix_s, kart_ms, acilis;
    char     surum[16];
    KayitKalibrasyon kal;
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

static inline void kayit_basla_paketle(const KayitBasla *b, uint8_t *p)
{
    p[0] = b->oturum_turu;
    p[1] = b->kal_bicim;
    p[2] = 0u;
    p[3] = 0u;
    kayit_y32(p + 4, b->hiz_ms);
    kayit_y32(p + 8, b->unix_s);
    kayit_y32(p + 12, b->kart_ms);
    kayit_y32(p + 16, b->acilis);
    memcpy(p + 20, b->surum, 16);
    kayit__kanal_yaz(p + 36, &b->kal.normal);
    kayit__kanal_yaz(p + 54, &b->kal.yuksek);
    kayit_y16(p + 72, (uint16_t)b->kal.i_ofset);
    kayit_yf(p + 74, b->kal.i_pga);
    kayit_yf(p + 78, b->kal.sont_ohm);
    kayit_yf(p + 82, b->kal.i_duzeltme);
    kayit_yf(p + 86, b->kal.sebeke_hz);
    kayit_yf(p + 90, b->kal.faz_kal_us[0]);
    kayit_yf(p + 94, b->kal.faz_kal_us[1]);
}

static inline void kayit_basla_coz(const uint8_t *p, KayitBasla *b)
{
    b->oturum_turu = p[0];
    b->kal_bicim = p[1];
    b->hiz_ms = kayit_o32(p + 4);
    b->unix_s = kayit_o32(p + 8);
    b->kart_ms = kayit_o32(p + 12);
    b->acilis = kayit_o32(p + 16);
    memcpy(b->surum, p + 20, 16);
    kayit__kanal_oku(p + 36, &b->kal.normal);
    kayit__kanal_oku(p + 54, &b->kal.yuksek);
    b->kal.i_ofset = (int16_t)kayit_o16(p + 72);
    b->kal.i_pga = kayit_of(p + 74);
    b->kal.sont_ohm = kayit_of(p + 78);
    b->kal.i_duzeltme = kayit_of(p + 82);
    b->kal.sebeke_hz = kayit_of(p + 86);
    b->kal.faz_kal_us[0] = kayit_of(p + 90);
    b->kal.faz_kal_us[1] = kayit_of(p + 94);
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

#endif /* KAYIT_BICIM_H */
