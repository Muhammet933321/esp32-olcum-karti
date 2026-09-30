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
 * Ayar3'u degistirir; degerlerin gecmiste KARSILIGI yoksa ortada taslak var.
 * `kgc_kaydet` taslagi not + turle kayda cevirir; unutulursa kayit baslarken
 * `kgc_oturum_no` OTOMATIK kaydeder — hicbir oturum numarasiz kalmaz.
 * Not ve tur sonradan duzeltilir; DEGERLER degismez.
 * Karsilik (ayni gun, son inceleme C1 uzerine kullanici karari): SIFIR
 * OFSETLERI karsilastirmaya girmez (panelden sik sifirlanir; oturum basligi
 * gercek sifiri tasir) ve daha once kayitli degerlere donulurse (sont,
 * sebeke A->B->A) o kaydin numarasi kullanilir — 40 kayit ancak 40 gercekten
 * farkli kalibrasyonla dolar; KALGEC_UYARI'dan itibaren kart uyarir.
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
#define KALGEC_UYARI   35u         /* bu kadar kayittan sonra "dolmak uzere" */
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

/* `s`'deki UTF-8 karakterinin bayt sayisi; gecersizse 0. RFC 3629 tablosu:
   asiri uzun kodlama, vekil (D800-DFFF) ve 10FFFF ustu GECERSIZ (Python'un
   cozucusu da reddeder). NUL'dan otesini okumaz: her devam bayti okunmadan
   once oncekinin NUL olmadigi dogrulanmis. */
static inline uint8_t kgc__utf8(const uint8_t *s)
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

/* Notu kopyala: gecersiz UTF-8 bayti (orn. cp1254 terminalden 'ş' = FE),
   kontrol karakterleri, `"` ve `\` atilir — JSON'a kacissiz ve PC'de hep
   cozulur; en fazla 31 bayt, sigmayan karakterde (karakter SINIRINDA) kesilir. */
static inline void kgc_not_kopyala(char *d, const char *s)
{
    const uint8_t *p = (const uint8_t *)s;
    uint8_t n = 0u, uz, c;
    if (p) {
        while ((c = *p) != 0u) {
            uz = kgc__utf8(p);
            if (!uz || (uz == 1u && (c < 0x20u || c == 0x7Fu || c == (uint8_t)'"'
                                     || c == (uint8_t)'\\'))) {
                p++;
                continue;
            }
            if ((uint8_t)(n + uz) > KALGEC_NOT - 1u) break;
            memcpy(d + n, p, uz);
            n = (uint8_t)(n + uz);
            p += uz;
        }
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

/* Karsilastirma paketi: SIFIR OFSETLERI (gerilim iki kanal + akim) haric.
   Kullanici karari (2026-09-30): panelden sik sifirlanir ve her seferinde
   biraz farkli cikar — gecmise girseydi 40 kayit olagan kullanimla dolardi.
   Oturum basligi gercek sifir degerlerini zaten tasiyor (tam kopya). */
static inline void kgc__iz(const KayitKalibrasyon *k, uint8_t *p)
{
    KayitKalibrasyon t = *k;
    t.normal.sifir_ham = 0;
    t.yuksek.sifir_ham = 0;
    t.i_ofset = 0;
    kayit_kal_paketle(&t, p);
}

/* Simdiki degerlere (sifirlar haric) esit EN YENI kayit; yoksa 0 = TASLAK.
   Sont / sebeke A->B->A eski numarayi kullanir: gecmis ancak gercekten
   farkli kalibrasyonlarla dolar. Son kayit bellekte; digerleri icin en
   fazla KALGEC_AZAMI - 1 NVS okumasi (yalniz degerler degisince). */
static inline uint32_t kgc_esle(KalGecmis *m, const KayitKalibrasyon *simdiki)
{
    uint8_t a[KAYIT_KAL_BAYT], b[KAYIT_KAL_BAYT];
    KalKayit e;
    uint32_t no;
    kgc__iz(simdiki, a);
    for (no = m->adet; no; no--) {
        if (m->son_var && m->son.no == no) e.kal = m->son.kal;
        else if (kgc_oku(m, no, &e)) continue;
        kgc__iz(&e.kal, b);
        if (!memcmp(a, b, KAYIT_KAL_BAYT)) return no;
    }
    return 0u;
}

/* Gecmiste karsiligi olmayan degerler var mi. */
static inline int kgc_taslak(KalGecmis *m, const KayitKalibrasyon *simdiki)
{
    return kgc_esle(m, simdiki) ? 0 : 1;
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

/* Elle kaydet (`kk`). Degerler zaten kayitliysa KGC_YOK (numarasi:
   kgc_esle — not/tur o kayitta duzeltilir). */
static inline int32_t kgc_kaydet(KalGecmis *m, const KayitKalibrasyon *simdiki, uint8_t tur,
                                 const char *not_, uint32_t unix_s, uint32_t acilis)
{
    if (kgc_esle(m, simdiki)) return KGC_YOK;
    return kgc__ekle(m, simdiki, tur, KGK_ELLE, not_, unix_s, acilis);
}

/* Kayit baslarken: degerlerin kayitli numarasi; yoksa OTOMATIK kaydet.
   Kaydedilemezse 0 (oturum yine tam kopyayi tasir; hata son_hata'da). */
static inline uint32_t kgc_oturum_no(KalGecmis *m, const KayitKalibrasyon *simdiki,
                                     uint32_t unix_s, uint32_t acilis)
{
    int32_t r;
    uint32_t no = kgc_esle(m, simdiki);
    if (no) return no;
    r = kgc__ekle(m, simdiki, KGT_BELIRSIZ, KGK_OTOMATIK, "otomatik: kayit baslarken",
                  unix_s, acilis);
    return r > 0 ? (uint32_t)r : 0u;
}

/* Dolunca yeni kalibrasyon numara alamaz (silme yok): KALGEC_UYARI'dan
   itibaren kart her kayitta uyarir. */
static inline int kgc_dolmak_uzere(const KalGecmis *m)
{
    return m->adet >= KALGEC_UYARI ? 1 : 0;
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
