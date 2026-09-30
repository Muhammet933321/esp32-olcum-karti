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
#include "kayit_halka.h"       /* 1C-2: KayitOrnek */

#ifndef KAYIT_AZAMI_YUK
#define KAYIT_AZAMI_YUK 1012u      /* 4 + 28 nokta */
#endif
#define KAYIT_TAMPON_NOKTA ((KAYIT_AZAMI_YUK - 4u) / KAYIT_NOKTA_BAYT)
#ifndef KAYIT_BOSALT_MS
#define KAYIT_BOSALT_MS 5000UL
#endif
#define KY_BITIR_PAY (KAYIT_BASLIK_BAYT + KAYIT_BITIR_BAYT)
/* 1C-2 ayrintili kip: ornekler ayni `yuk` tamponunda (RAM eklemez) */
#define KAYIT_AYRINTI_TAMPON ((KAYIT_AZAMI_YUK - KAYIT_AYRINTI_BAS) / KAYIT_AYRINTI_ORNEK)
#define KAYIT_AYRINTI_EN_AZ  8u    /* sektor sonuna bundan az ornek sigarsa yeni sektor */
typedef char kayit__ayrinti_tampon_yeter[
    (KAYIT_AYRINTI_TAMPON >= KAYIT_AYRINTI_EN_AZ) ? 1 : -1];

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
    uint32_t     dusen;           /* dolulukta atilan nokta / ornek */
    int          son_hata;
    /* 1C-2 ayrintili kip (hiz_ms 0): yuk[16..] ornekler, yuk[0..15] kayit basi */
    uint8_t      ayrinti;         /* etkin oturum her ornegi kaydediyor */
    uint16_t     a_adet;          /* tampondaki ornek */
    uint32_t     a_ilk_ms, a_ilk_us;   /* tampondaki ilk ornegin zamani */
    uint32_t     a_q;             /* son ornegin 4 us nicemi (a_ilk_us'e gore) */
    uint8_t      a_bayrak;        /* SONRAKI AYRINTI kaydinin KA_* bayragi */
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
        y->dusen += y->yuk_nokta + y->a_adet;
        y->yuk_nokta = 0u;
        y->a_adet = 0u;
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

/* ─────────────────────────────── 1C-2: AYRINTILI KIP (her ornek)
 * Ornekler `yuk[16 + 6k]`de paketli birikir; kayit basi yazarken doldurulur.
 * Zaman 4 us nicemli ve tampondaki ILK ornege gore (a_q), yani her ornegin
 * kurulan zamani gercekten <= 2 us sapar ve BIRIKMEZ. Sektore sigmayan kayit
 * BOLUNUR (sektor sonu bosa gitmez); kalanin t0'i nicem izgarasinda kalir. */
static inline int ky_ayrinti_bosalt(KayitYazici *y)
{
    KayitGunluk *g = y->g;
    const uint32_t sil_bas = g->silinen_sektor;
    while (y->oturum && y->a_adet) {
        uint32_t kalan = KAYIT_SEKTOR - g->bas_ofset;
        uint32_t sabit = KAYIT_BASLIK_BAYT + KAYIT_AYRINTI_BAS + KY_BITIR_PAY;
        uint32_t n = 0u, j, top;
        uint8_t *p;
        int32_t s;
        if (kalan >= sabit + KAYIT_AYRINTI_ORNEK) n = (kalan - sabit) / KAYIT_AYRINTI_ORNEK;
        if (n > y->a_adet) n = y->a_adet;
        if (n < y->a_adet && n < KAYIT_AYRINTI_EN_AZ) n = 0u;
        if (!n) {
            int r = ky__yeni_sektor(y);
            if (r) return ky__dolu(y, r);
            continue;
        }
        kayit_ayrinti_bas_paketle(y->yuk, y->nokta_sira, y->a_ilk_ms, y->a_ilk_us,
                                  (uint16_t)n, y->a_bayrak);
        s = kg_ekle(g, KAYIT_T_AYRINTI, y->oturum, y->yuk,
                    (uint16_t)(KAYIT_AYRINTI_BAS + n * KAYIT_AYRINTI_ORNEK));
        if (s < 0) return ky__dolu(y, (int)s);
        y->nokta_sira += n;
        y->a_bayrak = 0u;
        if (n < y->a_adet) {                   /* BOLUNDU: kalan basa */
            p = y->yuk + KAYIT_AYRINTI_BAS;
            for (top = 0u, j = 1u; j <= n; j++)
                top += (uint32_t)(kayit_o16(p + j * KAYIT_AYRINTI_ORNEK + 4u) >> 4);
            y->a_ilk_us += 4u * top;
            y->a_ilk_ms += (4u * top + 500u) / 1000u;
            y->a_q -= top;                     /* kalan yazilamazsa (hata) tamponda kalir */
            memmove(p, p + n * KAYIT_AYRINTI_ORNEK,
                    (size_t)(y->a_adet - n) * KAYIT_AYRINTI_ORNEK);
            kayit_y16(p + 4, (uint16_t)(kayit_o16(p + 4) & 0x0Fu));   /* ilk: dt4 0 */
            y->a_adet = (uint16_t)(y->a_adet - n);
        } else {
            y->a_adet = 0u;
        }
    }
    /* bu bosaltmada DOLU sektor silindiyse (~25 ms iki cekirdek durdu) o
       sirada ornek gelmedi: SONRAKI kaydin basi bunu soylesin */
    if (g->silinen_sektor != sil_bas) y->a_bayrak = (uint8_t)(y->a_bayrak | KA_SILME);
    return KG_TAMAM;
}

/* Bir ornek (kayit gorevi, halkadan). Zaman farki 16.38 ms'yi asarsa, halka
   tasmissa (KO_KAYIP_ONCE) ya da tampon doluysa once bosaltir: bosluk yeni
   kaydin t0'indan gorunur, sessiz birlesme yok. */
static inline int ky_ayrinti_ornek(KayitYazici *y, const KayitOrnek *o, uint32_t simdi_ms)
{
    uint32_t q = 0u, dt4 = 0u;
    int r;
    if (!y->oturum || !y->ayrinti) return KG_YOK;
    if (y->a_adet) {
        q = (uint32_t)(o->us - y->a_ilk_us + 2u) / 4u;
        dt4 = q - y->a_q;
        if ((o->bayrak & KO_KAYIP_ONCE) || dt4 > KAYIT_AYRINTI_DT_AZAMI
            || y->a_adet >= KAYIT_AYRINTI_TAMPON) {
            r = ky_ayrinti_bosalt(y);
            if (r) return r;
            if (!y->oturum) return KG_YOK;
        }
    }
    if (o->bayrak & KO_KAYIP_ONCE) y->a_bayrak = (uint8_t)(y->a_bayrak | KA_KAYIP_ONCE);
    if (!y->a_adet) {
        y->a_ilk_ms = o->ms;
        y->a_ilk_us = o->us;
        y->a_q = 0u;
        y->yuk_ilk_ms = simdi_ms;
        dt4 = 0u;
    } else {
        y->a_q = q;
    }
    kayit_ayrinti_ornek_paketle(y->yuk + KAYIT_AYRINTI_BAS
                                + (uint32_t)y->a_adet * KAYIT_AYRINTI_ORNEK,
                                o->v, o->i, (uint16_t)dt4, (uint8_t)(o->bayrak & 0x0Fu));
    y->a_adet++;
    return KG_TAMAM;
}

static inline int ky_nokta(KayitYazici *y, const KayitNokta *p, uint32_t simdi_ms)
{
    if (!y->oturum || y->ayrinti) return KG_YOK;
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
    if (y->oturum && y->a_adet
        && (uint32_t)(simdi_ms - y->yuk_ilk_ms) >= KAYIT_BOSALT_MS)
        return ky_ayrinti_bosalt(y);
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
    if (!r) r = ky_ayrinti_bosalt(y);
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
    if (y->oturum) {           /* 1C-1: surmekte olan "baska oturum basladi" ile kapanir */
        r = ky_bitir(y, KB_SEBEP_OTURUM);
        if (r && r != KG_DOLU) return r;
    }
    y->basla = *b;
    y->nokta_sira = 0u;
    y->yuk_nokta = 0u;
    y->son_hata = 0;
    y->ayrinti = (uint8_t)(b->hiz_ms == 0u);   /* 1C-2: hiz 0 = her ornek */
    y->a_adet = 0u;
    y->a_bayrak = 0u;
    kayit_basla_paketle(b, p);
    r = ky__yer(y, kayit_toplam_bayt(KAYIT_BASLA_BAYT));   /* oturum 0: TEKRAR yok */
    if (r) { y->son_hata = r; return r; }
    y->oturum = y->g->sonraki_sira;
    s = kg_ekle(y->g, KAYIT_T_BASLA, y->oturum, p, KAYIT_BASLA_BAYT);
    if (s < 0) { y->oturum = 0u; y->son_hata = (int)s; }
    return s;
}

/* 1C-1: oturum OLAYI (pil ayari, DCIR, pil sonucu). Once tamponda bekleyen
   noktalar yazilir: kayit sirasi zaman sirasiyla ayni kalir. */
static inline int ky_olay(KayitYazici *y, const uint8_t *yuk, uint16_t n)
{
    int r;
    if (!y->oturum) return KG_YOK;
    r = ky_bosalt(y);
    if (r) return r;           /* DOLU ise ky__dolu BITIR'i zaten yazdi */
    r = ky__kayit(y, KAYIT_T_OLAY, yuk, n);
    return r ? ky__dolu(y, r) : KG_TAMAM;
}

/* Kart yeniden basladi: acik OLCUM oturumunu surdur. Pil testi (ve olcum
   disi her tur) ICIN CAGRILMAZ — emniyet: yuk kapali kalir; yonetici o
   oturumu "yeniden basladi" ile kapatir (1C-1, kyn__devam_dene). */
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
    y->ayrinti = (uint8_t)(b->hiz_ms == 0u);   /* ayrintili oturum ayrintili SURER */
    y->a_adet = 0u;
    y->a_bayrak = 0u;
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
