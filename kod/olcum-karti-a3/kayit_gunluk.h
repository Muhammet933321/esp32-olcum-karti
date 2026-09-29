#ifndef KAYIT_GUNLUK_H
#define KAYIT_GUNLUK_H
/*
 * B71 — KAYIT GUNLUGU: NOR flas uzerinde yalniz-sona-ekleyen halka.
 *
 * Flas KAYIT_SEKTOR baytlik sektorlere bolunur (ESP32: 4096 = silme
 * birimi). Kayitlar bir sektorun basindan itibaren arka arkaya yazilir,
 * sektor sinirini ASLA asmaz. Sektorler halka sirasiyla kullanilir; bir
 * sektor kullanilmadan once HER ZAMAN silinir — kesik bir silmenin
 * coplugu veri sanilmasin diye.
 *
 * AKILLI TEMIZLIK (tasarim §5): en eski sektor ancak icindeki son kaydin
 * sirasi `onay`dan buyuk DEGILSE silinir, yani en az bir cihaz o veriyi
 * kalici diske yazdigini bildirdiyse. Aksi halde KG_DOLU: onaysiz veri
 * ASLA silinmez.
 *
 * KURTARMA (kg_ac): her sektor bastan taranir; CRC'si tutmayan ilk
 * kayitta durulur. Yazilan (en yeni) sektorun geri kalani 0xFF degilse o
 * sektore bir daha yazilmaz: yarim kaydin ardina yazmak yeni kaydi da
 * bozardi.
 *
 * Flas erisimi KayitFlas islev isaretcileriyle: kartta esp_partition_*
 * (1A-2), AVR testinde emule NOR (uretim/avr/nor_flas.py). Butun bellek
 * (sektor tablosu, oturum dizini) CAGIRANDAN gelir; burada malloc yok.
 */
#include "kayit_bicim.h"

#ifndef KAYIT_SEKTOR
#define KAYIT_SEKTOR 4096UL
#endif

#define KG_TAMAM   0
#define KG_DOLU   (-1)   /* onaysiz veri yuzunden yer yok */
#define KG_HATA   (-2)   /* flas islemi basarisiz ya da gecersiz arguman */
#define KG_BUYUK  (-3)   /* kayit bir sektore sigmiyor */
#define KG_YOK    (-4)   /* aktif oturum yok */

#define KD_ACIK   1u
#define KD_BITTI  2u
#define KG_ADRES_YOK 0xFFFFFFFFUL
#define KG__PARCA 32u

typedef struct {
    int (*oku)(void *baglam, uint32_t adres, void *hedef, uint32_t n);
    int (*yaz)(void *baglam, uint32_t adres, const void *kaynak, uint32_t n);
    int (*sil)(void *baglam, uint32_t sektor_adres);
    void *baglam;
} KayitFlas;

typedef struct { uint32_t ilk, son; } KayitSektor;   /* 0,0 = bos */

typedef struct {
    uint32_t id;
    uint32_t hiz_ms, unix_s, kart_ms, acilis;
    uint32_t ilk_sira, son_sira;   /* flasta KALAN kayitlarinin araligi */
    uint32_t nokta_sonraki;        /* oturumun sonraki noktasinin sirasi */
    uint32_t basla_adres;          /* son BASLA/TEKRAR'in adresi; KG_ADRES_YOK */
    uint8_t  tur, durum, basi_silindi;
} KayitOzet;

typedef struct KayitGunluk_ {
    KayitFlas    f;
    uint32_t     sektor_adet;
    KayitSektor *sektor;
    KayitOzet   *dizin;
    uint16_t     dizin_kap, dizin_adet;
    uint32_t     bas, bas_ofset;       /* yazilan sektor ve icindeki yer */
    uint32_t     sonraki_sira, onay;
    uint32_t     bozuk;                /* son kg_ac'ta atilan cop/yarim */
    uint32_t     silinen_sektor;       /* son kg_ac'tan beri temizlik */
    uint8_t      dolu;
} KayitGunluk;

typedef void (*KgBesle)(KayitGunluk *g, const KayitBaslik *h, uint32_t adres);

static inline int kg_kur(KayitGunluk *g, const KayitFlas *f, uint32_t sektor_adet,
                         KayitSektor *sektor, KayitOzet *dizin, uint16_t dizin_kap)
{
    memset(g, 0, sizeof(*g));
    if (sektor_adet < 2u) return KG_HATA;
    g->f = *f;
    g->sektor_adet = sektor_adet;
    g->sektor = sektor;
    g->dizin = dizin;
    g->dizin_kap = dizin_kap;
    g->sonraki_sira = 1u;
    g->bas = sektor_adet - 1u;
    g->bas_ofset = KAYIT_SEKTOR;
    memset(sektor, 0, (size_t)sektor_adet * sizeof(KayitSektor));
    return KG_TAMAM;
}

/* `adres`teki kaydi dogrula. 1 gecerli, 0 bos, -1 cop/yarim. */
static inline int8_t kg__kayit_dogrula(KayitGunluk *g, uint32_t adres,
                                       uint32_t sektor_sonu, KayitBaslik *h)
{
    uint8_t b[KAYIT_BASLIK_BAYT], parca[KG__PARCA];
    uint32_t c, kalan, a;
    int8_t d;
    if (adres + KAYIT_BASLIK_BAYT > sektor_sonu) return 0;
    if (g->f.oku(g->f.baglam, adres, b, KAYIT_BASLIK_BAYT)) return -1;
    d = kayit_baslik_coz(b, h);
    if (d <= 0) return d;
    if (adres + kayit_toplam_bayt(h->yuk_bayt) > sektor_sonu) return -1;
    c = kayit_crc_ekle(0u, b, 12u);
    a = adres + KAYIT_BASLIK_BAYT;
    kalan = h->yuk_bayt;
    while (kalan) {
        uint32_t n = kalan < KG__PARCA ? kalan : KG__PARCA;
        if (g->f.oku(g->f.baglam, a, parca, n)) return -1;
        c = kayit_crc_ekle(c, parca, n);
        a += n;
        kalan -= n;
    }
    return (c == h->crc) ? 1 : -1;
}

static inline uint8_t kg__ff_mi(KayitGunluk *g, uint32_t a, uint32_t son)
{
    uint8_t parca[KG__PARCA];
    while (a < son) {
        uint32_t n = son - a;
        uint8_t i;
        if (n > KG__PARCA) n = KG__PARCA;
        if (g->f.oku(g->f.baglam, a, parca, n)) return 0u;
        for (i = 0; i < (uint8_t)n; i++) {
            if (parca[i] != 0xFFu) return 0u;
        }
        a += n;
    }
    return 1u;
}

/* ─────────────────────────────── oturum dizini */
static inline KayitOzet *kg__ozet(KayitGunluk *g, uint32_t id)
{
    uint16_t i;
    KayitOzet *o;
    for (i = 0; i < g->dizin_adet; i++) {
        if (g->dizin[i].id == id) return &g->dizin[i];
    }
    if (!g->dizin_kap) return 0;
    if (g->dizin_adet == g->dizin_kap) {        /* en eskiyi dusur */
        memmove(&g->dizin[0], &g->dizin[1],
                (size_t)(g->dizin_kap - 1u) * sizeof(KayitOzet));
        g->dizin_adet--;
    }
    o = &g->dizin[g->dizin_adet++];
    memset(o, 0, sizeof(*o));
    o->id = id;
    o->basla_adres = KG_ADRES_YOK;
    o->basi_silindi = 1u;
    o->durum = KD_ACIK;
    return o;
}

/* `y`: yukun ilk `n` bayti (en fazla 20). */
static inline void kg__dizin_isle(KayitGunluk *g, const KayitBaslik *h,
                                  uint32_t adres, const uint8_t *y, uint16_t n)
{
    KayitOzet *o;
    if (!h->oturum) return;
    o = kg__ozet(g, h->oturum);
    if (!o) return;
    if (!o->ilk_sira) o->ilk_sira = h->sira;
    o->son_sira = h->sira;
    switch (h->tur) {
    case KAYIT_T_BASLA:
    case KAYIT_T_TEKRAR:
        if (n >= 20u) {
            o->tur = y[0];
            o->hiz_ms = kayit_o32(y + 4);
            o->unix_s = kayit_o32(y + 8);
            o->kart_ms = kayit_o32(y + 12);
            o->acilis = kayit_o32(y + 16);
        }
        o->basla_adres = adres;
        if (h->tur == KAYIT_T_BASLA) {
            o->basi_silindi = 0u;
            o->nokta_sonraki = 0u;
        }
        break;
    case KAYIT_T_NOKTA:
        if (n >= 4u && h->yuk_bayt >= 4u)
            o->nokta_sonraki = kayit_o32(y)
                             + (uint32_t)(h->yuk_bayt - 4u) / KAYIT_NOKTA_BAYT;
        break;
    case KAYIT_T_DEVAM:
        if (n >= 16u) o->nokta_sonraki = kayit_o32(y + 12);
        o->durum = KD_ACIK;
        break;
    case KAYIT_T_BITIR:
        o->durum = KD_BITTI;
        break;
    default:
        break;
    }
}

static inline void kg__besle(KayitGunluk *g, const KayitBaslik *h, uint32_t adres)
{
    uint8_t y[20];
    uint16_t n = (uint16_t)(h->yuk_bayt < 20u ? h->yuk_bayt : 20u);
    if (n && g->f.oku(g->f.baglam, adres + KAYIT_BASLIK_BAYT, y, n)) return;
    kg__dizin_isle(g, h, adres, y, n);
}

/* Sektoru bastan tara. Donus: son gecerli kaydin bittigi ofset.
   *temiz = 1: o ofsetten sektor sonuna kadar her bayt 0xFF. */
static inline uint32_t kg__sektor_tara(KayitGunluk *g, uint32_t s, KgBesle besle,
                                       uint8_t *temiz)
{
    uint32_t bas = s * KAYIT_SEKTOR, son = bas + KAYIT_SEKTOR, a = bas;
    KayitBaslik h;
    int8_t d;
    g->sektor[s].ilk = 0u;
    g->sektor[s].son = 0u;
    for (;;) {
        d = kg__kayit_dogrula(g, a, son, &h);
        if (d == 1 && g->sektor[s].son && h.sira <= g->sektor[s].son) d = -1;
        if (d != 1) break;
        if (!g->sektor[s].ilk) g->sektor[s].ilk = h.sira;
        g->sektor[s].son = h.sira;
        if (besle) besle(g, &h, a);
        a += kayit_toplam_bayt(h.yuk_bayt);
    }
    if (d < 0) {
        g->bozuk++;
        *temiz = 0u;
    } else {
        *temiz = kg__ff_mi(g, a, son);
    }
    return a - bas;
}

/* KURTARMA. `sira_taban`: bu siranin altinda numara verilmez (bicimleme
   sonrasi NVS'ten gelir; 1A-2). */
static inline int kg_ac(KayitGunluk *g, uint32_t sira_taban)
{
    uint32_t s, i, en_ilk = 0u, en_son = 0u, bas = 0u, ofset;
    uint8_t temiz, bos = 1u;
    KayitBaslik h;
    g->dizin_adet = 0u;
    g->onay = 0u;
    g->bozuk = 0u;
    g->silinen_sektor = 0u;
    g->dolu = 0u;
    /* 1. gecis: en yeni sektor = ilk kaydinin sirasi en buyuk olan */
    for (s = 0; s < g->sektor_adet; s++) {
        if (kg__kayit_dogrula(g, s * KAYIT_SEKTOR, (s + 1u) * KAYIT_SEKTOR, &h) == 1
            && h.sira > en_ilk) {
            en_ilk = h.sira;
            bas = s;
            bos = 0u;
        }
    }
    /* 2. gecis: halka sirasiyla; bas'tan SONRAKI sektor en eskidir */
    g->bas = bas;
    g->bas_ofset = KAYIT_SEKTOR;
    for (i = 1; i <= g->sektor_adet; i++) {
        s = (bas + i) % g->sektor_adet;
        ofset = kg__sektor_tara(g, s, kg__besle, &temiz);
        if (g->sektor[s].son > en_son) en_son = g->sektor[s].son;
        if (s == bas && temiz) g->bas_ofset = ofset;
    }
    if (bos) { g->bas = g->sektor_adet - 1u; g->bas_ofset = KAYIT_SEKTOR; }
    g->sonraki_sira = en_son + 1u;
    if (g->sonraki_sira < sira_taban) g->sonraki_sira = sira_taban;
    return KG_TAMAM;
}

/* Silinecek sektorun izini dizinden cikar. */
static inline void kg__sektor_dusur(KayitGunluk *g, uint32_t s)
{
    uint32_t son = g->sektor[s].son, a0 = s * KAYIT_SEKTOR;
    uint16_t i, j = 0u;
    for (i = 0; i < g->dizin_adet; i++) {
        KayitOzet *o = &g->dizin[i];
        if (o->son_sira <= son) continue;          /* butunuyle gitti */
        if (o->ilk_sira <= son) {
            o->ilk_sira = son + 1u;
            o->basi_silindi = 1u;
        }
        if (o->basla_adres != KG_ADRES_YOK && o->basla_adres >= a0
            && o->basla_adres < a0 + KAYIT_SEKTOR) o->basla_adres = KG_ADRES_YOK;
        if (j != i) g->dizin[j] = *o;
        j++;
    }
    g->dizin_adet = j;
}

/* Sonraki sektore gec: gerekirse AKILLI TEMIZLIK, her durumda SIL. */
static inline int kg_ilerle(KayitGunluk *g)
{
    uint32_t s = (g->bas + 1u) % g->sektor_adet;
    if (g->sektor[s].ilk) {
        if (g->sektor[s].son > g->onay) { g->dolu = 1u; return KG_DOLU; }
        kg__sektor_dusur(g, s);
        g->silinen_sektor++;
    }
    if (g->f.sil(g->f.baglam, s * KAYIT_SEKTOR)) return KG_HATA;
    g->sektor[s].ilk = 0u;
    g->sektor[s].son = 0u;
    g->bas = s;
    g->bas_ofset = 0u;
    g->dolu = 0u;
    return KG_TAMAM;
}

/* Kayit ekle. Donus: verilen sira (>0) ya da KG_*. */
static inline int32_t kg_ekle(KayitGunluk *g, uint8_t tur, uint32_t oturum,
                              const uint8_t *yuk, uint16_t yuk_bayt)
{
    static const uint8_t sifir[3] = {0u, 0u, 0u};
    uint8_t b[KAYIT_BASLIK_BAYT];
    KayitBaslik h;
    uint32_t toplam = kayit_toplam_bayt(yuk_bayt), adres, dolgu;
    int r;
    if (toplam > KAYIT_SEKTOR) return KG_BUYUK;
    if (g->bas_ofset + toplam > KAYIT_SEKTOR) {
        r = kg_ilerle(g);
        if (r) return r;
    }
    h.tur = tur;
    h.yuk_bayt = yuk_bayt;
    h.sira = g->sonraki_sira;
    h.oturum = oturum;
    kayit_baslik_yaz(b, tur, h.sira, oturum, yuk, yuk_bayt);
    h.crc = kayit_o32(b + 12);
    adres = g->bas * KAYIT_SEKTOR + g->bas_ofset;
    dolgu = toplam - KAYIT_BASLIK_BAYT - yuk_bayt;
    if (g->f.yaz(g->f.baglam, adres, b, KAYIT_BASLIK_BAYT)
        || (yuk_bayt && g->f.yaz(g->f.baglam, adres + KAYIT_BASLIK_BAYT, yuk, yuk_bayt))
        || (dolgu && g->f.yaz(g->f.baglam, adres + KAYIT_BASLIK_BAYT + yuk_bayt,
                              sifir, dolgu))) {
        g->bas_ofset = KAYIT_SEKTOR;   /* sektorun durumu belirsiz: bir daha yazma */
        return KG_HATA;
    }
    if (!g->sektor[g->bas].ilk) g->sektor[g->bas].ilk = h.sira;
    g->sektor[g->bas].son = h.sira;
    g->bas_ofset += toplam;
    g->sonraki_sira = h.sira + 1u;
    kg__dizin_isle(g, &h, adres, yuk, (uint16_t)(yuk_bayt < 20u ? yuk_bayt : 20u));
    return (int32_t)h.sira;
}

/* Bir cihaz `sira`ya kadar KALICI aldigini bildirdi. */
static inline void kg_onayla(KayitGunluk *g, uint32_t sira)
{
    if (g->sonraki_sira && sira >= g->sonraki_sira) sira = g->sonraki_sira - 1u;
    if (sira > g->onay) g->onay = sira;
}

/* Esitleme: `sira` ve sonrasini, flasta nasilsa oyle, `kap` bayta kadar
   kopyala. Kayit asla bolunmez. *ilk > istenen ise arada silinmis veri
   var (bosluk). */
static inline uint32_t kg_oku(KayitGunluk *g, uint32_t sira, uint8_t *hedef,
                              uint32_t kap, uint32_t *ilk, uint32_t *son)
{
    uint8_t b[KAYIT_BASLIK_BAYT];
    KayitBaslik h;
    uint32_t i, s, a, bitis, t, n = 0u;
    *ilk = 0u;
    *son = 0u;
    if (!sira) sira = 1u;
    for (i = 1; i <= g->sektor_adet; i++) {
        s = (g->bas + i) % g->sektor_adet;
        if (!g->sektor[s].ilk || g->sektor[s].son < sira) continue;
        a = s * KAYIT_SEKTOR;
        bitis = a + ((s == g->bas) ? g->bas_ofset : KAYIT_SEKTOR);
        while (a + KAYIT_BASLIK_BAYT <= bitis) {
            if (g->f.oku(g->f.baglam, a, b, KAYIT_BASLIK_BAYT)) return n;
            if (kayit_baslik_coz(b, &h) != 1) break;
            if (h.sira > g->sektor[s].son) break;
            t = kayit_toplam_bayt(h.yuk_bayt);
            if (a + t > bitis) break;
            if (h.sira >= sira) {
                if (n + t > kap) return n;
                if (g->f.oku(g->f.baglam, a, hedef + n, t)) return n;
                if (!*ilk) *ilk = h.sira;
                *son = h.sira;
                n += t;
            }
            a += t;
        }
    }
    return n;
}

/* Butun kayitlari sil. Sira KORUNUR: numara tekrar verilmez. */
static inline int kg_bicimle(KayitGunluk *g)
{
    uint32_t s;
    for (s = 0; s < g->sektor_adet; s++) {
        if (g->f.sil(g->f.baglam, s * KAYIT_SEKTOR)) return KG_HATA;
        g->sektor[s].ilk = 0u;
        g->sektor[s].son = 0u;
    }
    g->dizin_adet = 0u;
    g->bas = g->sektor_adet - 1u;
    g->bas_ofset = KAYIT_SEKTOR;
    g->onay = g->sonraki_sira - 1u;
    g->dolu = 0u;
    return KG_TAMAM;
}

static inline uint32_t kg_kullanilan(const KayitGunluk *g)
{
    uint32_t s, t = 0u;
    for (s = 0; s < g->sektor_adet; s++) {
        if (g->sektor[s].ilk) t += (s == g->bas) ? g->bas_ofset : KAYIT_SEKTOR;
    }
    return t;
}

/* Muhafazakar: onaysiz kayit iceren sektorun TAMAMI sayilir. */
static inline uint32_t kg_onaysiz(const KayitGunluk *g)
{
    uint32_t s, t = 0u;
    for (s = 0; s < g->sektor_adet; s++) {
        if (g->sektor[s].ilk && g->sektor[s].son > g->onay)
            t += (s == g->bas) ? g->bas_ofset : KAYIT_SEKTOR;
    }
    return t;
}

static inline uint16_t kg_binde(const KayitGunluk *g, uint32_t bayt)
{
    return (uint16_t)((uint64_t)bayt * 1000u
                      / ((uint64_t)g->sektor_adet * KAYIT_SEKTOR));
}

/* Dizindeki `basla_adres`ten oturumun BASLA/TEKRAR bilgisini oku. */
static inline int kg_basla_oku(KayitGunluk *g, uint32_t adres, KayitBasla *b)
{
    uint8_t p[KAYIT_BASLA_BAYT];
    KayitBaslik h;
    uint32_t s;
    if (adres == KG_ADRES_YOK) return KG_HATA;
    s = adres / KAYIT_SEKTOR;
    if (s >= g->sektor_adet) return KG_HATA;
    if (kg__kayit_dogrula(g, adres, (s + 1u) * KAYIT_SEKTOR, &h) != 1) return KG_HATA;
    if ((h.tur != KAYIT_T_BASLA && h.tur != KAYIT_T_TEKRAR)
        || h.yuk_bayt != KAYIT_BASLA_BAYT) return KG_HATA;
    if (g->f.oku(g->f.baglam, adres + KAYIT_BASLIK_BAYT, p, KAYIT_BASLA_BAYT))
        return KG_HATA;
    kayit_basla_coz(p, b);
    return KG_TAMAM;
}

#endif /* KAYIT_GUNLUK_H */
