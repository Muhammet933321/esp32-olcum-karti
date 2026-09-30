#ifndef KALGEC_H
#define KALGEC_H
/*
 * 1B — KALIBRASYON GECMISI (tasarim §7), platformsuz.
 *
 * Her kalibrasyon ayri, kalici, numarali bir kayit: numara · tarih · acilis ·
 * tur ("donanim degisti" / "ince ayar") · kaynak · not · degerlerin tam
 * kopyasi. Oturum basligi (BASLA surum 2) numarayi tasir.
 *
 * TASLAK modeli (kullanici karari, 2026-09-30): kalibrasyon komutlari yalniz
 * Ayar3'u degistirir; degerler son kayittan FARKLIYSA ortada taslak var.
 * `kgc_kaydet` taslagi not + turle kayda cevirir; unutulursa kayit baslarken
 * `kgc_oturum_no` OTOMATIK kaydeder — hicbir oturum numarasiz kalmaz.
 * Not ve tur sonradan duzeltilir; DEGERLER degismez.
 *
 * Saklama NVS (kullanici karari): `adet` + `k1`…`k40`. 40: yedekteki NVS
 * olculdu (179 dolu giris; 116 B'lik blob 6 giris tutar). Dolunca ACIK hata,
 * sessiz silme yok. Yazim sirasi: once `k<no>`, sonra `adet` — arada
 * elektrik giderse `adet` eski kalir, yetim blob sonraki kaydetmede ezilir;
 * numara oturuma ancak ikisi de yazildiktan sonra verilir.
 *
 * Paket (116 B): 0 u32 no · 4 u32 unix_s · 8 u32 acilis · 12 u8 tur ·
 * 13 u8 kaynak · 14 u16 bicim (1) · 16 not[32] (UTF-8, NUL'lu) ·
 * 48 kalibrasyon[62] (BASLA ile ayni) · 110 u16 0 · 112 CRC-32 (0..111)
 * Sinama: uretim/test_kayit.py B71.C (AVR emulatoru + emule NVS).
 */
#include "kayit_bicim.h"

#define KALGEC_SURUM   1u
#define KALGEC_AZAMI   40u
#define KALGEC_NOT     32u         /* 31 bayt + NUL */
#define KALGEC_BAYT    116u
#ifndef KALGEC_NVS_PAY
#define KALGEC_NVS_PAY 24u         /* kaydetmeden once NVS'te en az bu kadar bos giris */
#endif

#define KGT_BELIRSIZ 0u            /* tur */
#define KGT_DONANIM  1u
#define KGT_INCE     2u
#define KGK_ELLE     0u            /* kaynak */
#define KGK_OTOMATIK 1u
#define KGK_ILK      2u

#define KGC_TAMAM     0
#define KGC_YOK      (-1)          /* boyle kayit yok / taslak yok */
#define KGC_HATA     (-2)          /* NVS okuma/yazma */
#define KGC_DOLU     (-3)          /* KALGEC_AZAMI doldu */
#define KGC_NVS_DOLU (-4)          /* NVS'te yer yok */
#define KGC_BOZUK    (-5)          /* CRC tutmadi */

typedef struct {
    uint32_t no, unix_s, acilis;
    uint8_t  tur, kaynak;
    char     not_[KALGEC_NOT];
    KayitKalibrasyon kal;
} KalKayit;

typedef struct {
    int      (*oku)(void *baglam, const char *ad, void *hedef, uint32_t n);   /* 0 = tamam */
    int      (*yaz)(void *baglam, const char *ad, const void *kaynak, uint32_t n);
    uint32_t (*bos)(void *baglam);          /* NVS'te bos giris */
    void *baglam;
} KalNvs;

typedef struct {
    KalNvs   nvs;
    uint32_t adet;
    uint8_t  son_var;
    KalKayit son;
    int      son_hata;
} KalGecmis;

/* Notu kopyala: kontrol karakterleri, `"` ve `\` atilir (JSON'a kacissiz
   girer); en fazla 31 bayt, UTF-8 karakter SINIRINDA kesilir. */
static inline void kgc_not_kopyala(char *d, const char *s)
{
    uint8_t n = 0u, i, uz, bas;
    uint8_t c;
    if (s) {
        while ((c = (uint8_t)*s++) != 0u && n < KALGEC_NOT - 1u) {
            if (c < 0x20u || c == 0x7Fu || c == (uint8_t)'"' || c == (uint8_t)'\\') continue;
            d[n++] = (char)c;
        }
    }
    i = n;
    while (i && ((uint8_t)d[i - 1u] & 0xC0u) == 0x80u) i--;      /* devam baytlari */
    if (i) {
        bas = (uint8_t)d[i - 1u];
        uz = (bas >= 0xF0u) ? 4u : (bas >= 0xE0u) ? 3u : (bas >= 0xC0u) ? 2u : 1u;
        if ((uint8_t)(n - (i - 1u)) < uz) n = (uint8_t)(i - 1u);     /* yarim karakter */
    } else {
        n = 0u;
    }
    memset(d + n, 0, KALGEC_NOT - n);
}

static inline void kgc_paketle(const KalKayit *e, uint8_t *p)
{
    memset(p, 0, KALGEC_BAYT);
    kayit_y32(p, e->no);
    kayit_y32(p + 4, e->unix_s);
    kayit_y32(p + 8, e->acilis);
    p[12] = e->tur;
    p[13] = e->kaynak;
    kayit_y16(p + 14, (uint16_t)KALGEC_SURUM);
    memcpy(p + 16, e->not_, KALGEC_NOT);
    p[16 + KALGEC_NOT - 1u] = 0u;
    kayit_kal_paketle(&e->kal, p + 48);
    kayit_y32(p + 112, kayit_crc_ekle(0u, p, 112u));
}

static inline int kgc_coz(const uint8_t *p, KalKayit *e)
{
    if (kayit_crc_ekle(0u, p, 112u) != kayit_o32(p + 112)) return KGC_BOZUK;
    e->no = kayit_o32(p);
    e->unix_s = kayit_o32(p + 4);
    e->acilis = kayit_o32(p + 8);
    e->tur = p[12];
    e->kaynak = p[13];
    memcpy(e->not_, p + 16, KALGEC_NOT);
    e->not_[KALGEC_NOT - 1u] = 0;
    kayit_kal_coz(p + 48, &e->kal);
    return KGC_TAMAM;
}

/* "k<no>" (snprintf'siz: AVR'de de ucuz) */
static inline void kgc__ad(char *ad, uint32_t no)
{
    char t[11];
    uint8_t n = 0u, i = 0u;
    do { t[n++] = (char)('0' + no % 10u); no /= 10u; } while (no && n < 10u);
    ad[i++] = 'k';
    while (n) ad[i++] = t[--n];
    ad[i] = 0;
}

static inline int kgc_oku(KalGecmis *m, uint32_t no, KalKayit *e)
{
    uint8_t p[KALGEC_BAYT];
    char ad[13];
    if (!no || no > m->adet) return KGC_YOK;
    kgc__ad(ad, no);
    if (m->nvs.oku(m->nvs.baglam, ad, p, KALGEC_BAYT)) return KGC_HATA;
    return kgc_coz(p, e);
}

static inline int kgc__yaz(KalGecmis *m, const KalKayit *e)
{
    uint8_t p[KALGEC_BAYT];
    char ad[13];
    kgc_paketle(e, p);
    kgc__ad(ad, e->no);
    return m->nvs.yaz(m->nvs.baglam, ad, p, KALGEC_BAYT) ? KGC_HATA : KGC_TAMAM;
}

/* Simdiki degerler son kayittan farkli mi (paket karsilastirmasi). */
static inline int kgc_taslak(const KalGecmis *m, const KayitKalibrasyon *simdiki)
{
    uint8_t a[KAYIT_KAL_BAYT], b[KAYIT_KAL_BAYT];
    if (!m->son_var) return 1;
    kayit_kal_paketle(simdiki, a);
    kayit_kal_paketle(&m->son.kal, b);
    return memcmp(a, b, KAYIT_KAL_BAYT) ? 1 : 0;
}

/* Yeni kayit. Once k<no>, SONRA adet. Donus: numara (> 0) ya da KGC_*. */
static inline int32_t kgc__ekle(KalGecmis *m, const KayitKalibrasyon *simdiki, uint8_t tur,
                                uint8_t kaynak, const char *not_, uint32_t unix_s,
                                uint32_t acilis)
{
    KalKayit e;
    uint8_t a[4];
    if (m->adet >= KALGEC_AZAMI) { m->son_hata = KGC_DOLU; return KGC_DOLU; }
    if (m->nvs.bos && m->nvs.bos(m->nvs.baglam) < KALGEC_NVS_PAY) {
        m->son_hata = KGC_NVS_DOLU;
        return KGC_NVS_DOLU;
    }
    memset(&e, 0, sizeof(e));
    e.no = m->adet + 1u;
    e.unix_s = unix_s;
    e.acilis = acilis;
    e.tur = tur;
    e.kaynak = kaynak;
    kgc_not_kopyala(e.not_, not_);
    e.kal = *simdiki;
    if (kgc__yaz(m, &e)) { m->son_hata = KGC_HATA; return KGC_HATA; }
    kayit_y32(a, e.no);
    if (m->nvs.yaz(m->nvs.baglam, "adet", a, 4u)) { m->son_hata = KGC_HATA; return KGC_HATA; }
    m->adet = e.no;
    m->son = e;
    m->son_var = 1u;
    m->son_hata = KGC_TAMAM;
    return (int32_t)e.no;
}

/* ACILIS. Gecmis bossa bugunku kalibrasyon #1 olur (kaynak 'ilk'). */
static inline int kgc_ac(KalGecmis *m, const KalNvs *nvs, const KayitKalibrasyon *simdiki,
                         uint32_t unix_s, uint32_t acilis)
{
    uint8_t a[4];
    int r;
    memset(m, 0, sizeof(*m));
    m->nvs = *nvs;
    if (!m->nvs.oku(m->nvs.baglam, "adet", a, 4u)) m->adet = kayit_o32(a);
    if (m->adet > KALGEC_AZAMI) m->adet = KALGEC_AZAMI;
    if (m->adet) {
        r = kgc_oku(m, m->adet, &m->son);
        m->son_var = (r == KGC_TAMAM) ? 1u : 0u;
        m->son_hata = r;
        return r;
    }
    r = (int)kgc__ekle(m, simdiki, KGT_BELIRSIZ, KGK_ILK, "1B oncesi kalibrasyon (Ayar3)",
                       unix_s, acilis);
    return r < 0 ? r : KGC_TAMAM;
}

/* Elle kaydet (`kk`). Taslak yoksa KGC_YOK. */
static inline int32_t kgc_kaydet(KalGecmis *m, const KayitKalibrasyon *simdiki, uint8_t tur,
                                 const char *not_, uint32_t unix_s, uint32_t acilis)
{
    if (!kgc_taslak(m, simdiki)) return KGC_YOK;
    return kgc__ekle(m, simdiki, tur, KGK_ELLE, not_, unix_s, acilis);
}

/* Kayit baslarken: taslak varsa OTOMATIK kaydet; numarayi dondur.
   Kaydedilemezse 0 (oturum yine tam kopyayi tasir; hata son_hata'da). */
static inline uint32_t kgc_oturum_no(KalGecmis *m, const KayitKalibrasyon *simdiki,
                                     uint32_t unix_s, uint32_t acilis)
{
    int32_t r;
    if (!kgc_taslak(m, simdiki)) return m->son.no;
    r = kgc__ekle(m, simdiki, KGT_BELIRSIZ, KGK_OTOMATIK, "otomatik: kayit baslarken",
                  unix_s, acilis);
    return r > 0 ? (uint32_t)r : 0u;
}

/* Not ya da turu duzelt (tur < 0 / not_ NULL: degismez). Degerler DEGISMEZ. */
static inline int kgc_duzenle(KalGecmis *m, uint32_t no, int tur, const char *not_)
{
    KalKayit e;
    int r = kgc_oku(m, no, &e);
    if (r) return r;
    if (tur >= 0) e.tur = (uint8_t)tur;
    if (not_) kgc_not_kopyala(e.not_, not_);
    r = kgc__yaz(m, &e);
    if (!r && m->son_var && m->son.no == no) m->son = e;
    return r;
}

#endif /* KALGEC_H */
