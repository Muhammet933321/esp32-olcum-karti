#ifndef KAYIT_OTURUM_H
#define KAYIT_OTURUM_H
/*
 * B71 — OTURUM YAZICI: noktalari tamponlar, oturum kayitlarini gunluge
 * yazar (kartta cekirdek 0'daki kayit gorevi; 1A-2).
 *
 * Kurallar (tasarim §5):
 *   * Oturum kimligi = BASLA kaydinin sirasi.
 *   * Noktalar RAM'de en fazla KAYIT_TAMPON_NOKTA ya da KAYIT_BOSALT_MS
 *     bekler: elektrik kesilirse kayip bununla sinirli (hedef <= ~5 s).
 *   * Aktif oturumun her YENI sektoru TEKRAR kaydiyla baslar: temizlik
 *     BASLA'yi silse de her sektor kendi oturumunu anlatir; yeniden
 *     baslamada kalibrasyon kopyasi hep bulunur.
 *   * Her sektorde BITIR icin KY_BITIR_PAY bayt AYRILIR: bellek onaysiz
 *     veriyle dolunca BITIR(DOLU) yine yazilir, kayit sessizce durmaz.
 */
#include "kayit_gunluk.h"

#ifndef KAYIT_AZAMI_YUK
#define KAYIT_AZAMI_YUK 1012u      /* 4 + 28 nokta */
#endif
#define KAYIT_TAMPON_NOKTA ((KAYIT_AZAMI_YUK - 4u) / KAYIT_NOKTA_BAYT)
#ifndef KAYIT_BOSALT_MS
#define KAYIT_BOSALT_MS 5000UL
#endif
#define KY_BITIR_PAY (KAYIT_BASLIK_BAYT + KAYIT_BITIR_BAYT)

/* Sektor en az TEKRAR (116) + tam NOKTA kaydi + BITIR payi almali; yoksa
   ky_bosalt hic ilerleyemezdi. Derleme aninda denetim. */
typedef char kayit__sektor_yeter[
    (KAYIT_SEKTOR >= (uint32_t)(KAYIT_BASLIK_BAYT + KAYIT_BASLA_BAYT + 2u
                                + KAYIT_BASLIK_BAYT + KAYIT_AZAMI_YUK
                                + KY_BITIR_PAY)) ? 1 : -1];

typedef struct {
    KayitGunluk *g;
    uint32_t     oturum;          /* 0 = kayit yok */
    KayitBasla   basla;           /* TEKRAR icin */
    uint32_t     nokta_sira;      /* oturumdaki sonraki noktanin sirasi */
    uint8_t      yuk[KAYIT_AZAMI_YUK];   /* [0..3] ilk_nokta, sonra noktalar */
    uint16_t     yuk_nokta;
    uint32_t     yuk_ilk_ms;
    uint32_t     dusen;           /* dolulukta atilan nokta */
    int          son_hata;
} KayitYazici;

static inline void ky_kur(KayitYazici *y, KayitGunluk *g)
{
    memset(y, 0, sizeof(*y));
    y->g = g;
}

static inline int ky__yeni_sektor(KayitYazici *y)
{
    uint8_t p[KAYIT_BASLA_BAYT];
    int32_t s;
    int r = kg_ilerle(y->g);
    if (r) return r;
    if (!y->oturum) return KG_TAMAM;
    kayit_basla_paketle(&y->basla, p);
    s = kg_ekle(y->g, KAYIT_T_TEKRAR, y->oturum, p, KAYIT_BASLA_BAYT);
    return s < 0 ? (int)s : KG_TAMAM;
}

/* `toplam` baytlik kayit + BITIR payi bu sektore sigmiyorsa yeni sektor. */
static inline int ky__yer(KayitYazici *y, uint32_t toplam)
{
    if (y->g->bas_ofset + toplam + KY_BITIR_PAY <= KAYIT_SEKTOR) return KG_TAMAM;
    return ky__yeni_sektor(y);
}

static inline int ky__kayit(KayitYazici *y, uint8_t tur, const uint8_t *yuk,
                            uint16_t n)
{
    int32_t s;
    int r = ky__yer(y, kayit_toplam_bayt(n));
    if (r) return r;
    s = kg_ekle(y->g, tur, y->oturum, yuk, n);
    return s < 0 ? (int)s : KG_TAMAM;
}

/* Yer kalmadi: BITIR(DOLU)'yu AYRILMIS paya yaz, oturumu kapat. */
static inline int ky__dolu(KayitYazici *y, int r)
{
    if (r == KG_DOLU && y->oturum) {
        uint8_t p[KAYIT_BITIR_BAYT];
        KayitBitir b;
        b.nokta_adedi = y->nokta_sira;
        b.sebep = KB_SEBEP_DOLU;
        kayit_bitir_paketle(&b, p);
        (void)kg_ekle(y->g, KAYIT_T_BITIR, y->oturum, p, KAYIT_BITIR_BAYT);
        y->dusen += y->yuk_nokta;
        y->yuk_nokta = 0u;
        y->oturum = 0u;
    }
    y->son_hata = r;
    return r;
}

static inline int ky_bosalt(KayitYazici *y)
{
    KayitGunluk *g = y->g;
    while (y->oturum && y->yuk_nokta) {
        uint32_t kalan = KAYIT_SEKTOR - g->bas_ofset;
        uint32_t sabit = KAYIT_BASLIK_BAYT + 4u + KY_BITIR_PAY;
        uint32_t n = 0u;
        int32_t s;
        if (kalan >= sabit + KAYIT_NOKTA_BAYT) n = (kalan - sabit) / KAYIT_NOKTA_BAYT;
        if (n > y->yuk_nokta) n = y->yuk_nokta;
        if (!n) {
            int r = ky__yeni_sektor(y);
            if (r) return ky__dolu(y, r);
            continue;
        }
        kayit_y32(y->yuk, y->nokta_sira);
        s = kg_ekle(g, KAYIT_T_NOKTA, y->oturum, y->yuk,
                    (uint16_t)(4u + n * KAYIT_NOKTA_BAYT));
        if (s < 0) return ky__dolu(y, (int)s);
        y->nokta_sira += n;
        y->yuk_nokta = (uint16_t)(y->yuk_nokta - n);
        if (y->yuk_nokta)
            memmove(y->yuk + 4, y->yuk + 4 + n * KAYIT_NOKTA_BAYT,
                    (size_t)y->yuk_nokta * KAYIT_NOKTA_BAYT);
    }
    return KG_TAMAM;
}

static inline int ky_nokta(KayitYazici *y, const KayitNokta *p, uint32_t simdi_ms)
{
    if (!y->oturum) return KG_YOK;
    if (y->yuk_nokta >= KAYIT_TAMPON_NOKTA) {
        int r = ky_bosalt(y);
        if (r) return r;
    }
    kayit_nokta_paketle(p, y->yuk + 4 + (uint32_t)y->yuk_nokta * KAYIT_NOKTA_BAYT);
    if (!y->yuk_nokta) y->yuk_ilk_ms = simdi_ms;
    y->yuk_nokta++;
    if (y->yuk_nokta >= KAYIT_TAMPON_NOKTA) return ky_bosalt(y);
    return KG_TAMAM;
}

static inline int ky_zaman(KayitYazici *y, uint32_t simdi_ms)
{
    if (y->oturum && y->yuk_nokta
        && (uint32_t)(simdi_ms - y->yuk_ilk_ms) >= KAYIT_BOSALT_MS)
        return ky_bosalt(y);
    return KG_TAMAM;
}

static inline int ky_bitir(KayitYazici *y, uint8_t sebep)
{
    uint8_t p[KAYIT_BITIR_BAYT];
    KayitBitir b;
    int32_t s;
    int r;
    if (!y->oturum) return KG_YOK;
    r = ky_bosalt(y);
    if (r) return r;           /* DOLU ise ky__dolu BITIR'i zaten yazdi */
    b.nokta_adedi = y->nokta_sira;
    b.sebep = sebep;
    kayit_bitir_paketle(&b, p);
    s = kg_ekle(y->g, KAYIT_T_BITIR, y->oturum, p, KAYIT_BITIR_BAYT);
    y->oturum = 0u;
    return s < 0 ? (int)s : KG_TAMAM;
}

/* Donus: oturum kimligi (> 0) ya da KG_*. */
static inline int32_t ky_baslat(KayitYazici *y, const KayitBasla *b)
{
    uint8_t p[KAYIT_BASLA_BAYT];
    int32_t s;
    int r;
    if (y->oturum) {
        r = ky_bitir(y, KB_SEBEP_KULLANICI);
        if (r && r != KG_DOLU) return r;
    }
    y->basla = *b;
    y->nokta_sira = 0u;
    y->yuk_nokta = 0u;
    y->son_hata = 0;
    kayit_basla_paketle(b, p);
    r = ky__yer(y, kayit_toplam_bayt(KAYIT_BASLA_BAYT));   /* oturum 0: TEKRAR yok */
    if (r) { y->son_hata = r; return r; }
    y->oturum = y->g->sonraki_sira;
    s = kg_ekle(y->g, KAYIT_T_BASLA, y->oturum, p, KAYIT_BASLA_BAYT);
    if (s < 0) { y->oturum = 0u; y->son_hata = (int)s; }
    return s;
}

/* Kart yeniden basladi: acik oturumu surdur (pil testi ICIN CAGRILMAZ —
   emniyet: yuk kapali kalir; 1C). */
static inline int ky_devam(KayitYazici *y, uint32_t oturum, const KayitBasla *b,
                           uint32_t nokta_sira, const KayitDevam *d)
{
    uint8_t p[KAYIT_DEVAM_BAYT];
    KayitDevam dd = *d;
    int r;
    y->oturum = oturum;
    y->basla = *b;
    y->nokta_sira = nokta_sira;
    y->yuk_nokta = 0u;
    y->son_hata = 0;
    dd.nokta_sira = nokta_sira;
    kayit_devam_paketle(&dd, p);
    r = ky__kayit(y, KAYIT_T_DEVAM, p, KAYIT_DEVAM_BAYT);
    return r ? ky__dolu(y, r) : KG_TAMAM;
}

static inline int ky_saat(KayitYazici *y, const KayitSaat *z)
{
    uint8_t p[KAYIT_SAAT_BAYT];
    int r;
    kayit_saat_paketle(z, p);
    r = ky__kayit(y, KAYIT_T_SAAT, p, KAYIT_SAAT_BAYT);
    return r ? ky__dolu(y, r) : KG_TAMAM;
}

#endif /* KAYIT_OTURUM_H */
