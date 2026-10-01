/* bildirim.h — 1E MQTT bildirimleri: OLAY URETICISI + DURUM + ZARF (platformsuz).
 *
 * Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K4-K8, "Zarf bicimi").
 * Cekirdek 0'daki yapistirici her turda kayit/pil/acilis ANLIK GORUNTUSUNU
 * (BildirimGoruntu) doldurup `bld_adim`a verir; uretilen olaylar RAM kuyruguna
 * girer, bagliysa yapistirici `bld_kuyruk_bas` -> yayin -> `bld_kuyruk_at` ile
 * bosaltir (ikisinin ARASINDA bld_adim cagrilmaz: dolu kuyrukta en eski duser).
 * MQTT istemcisi, NVS, saat ve kriptografi CAGIRANIN isi; burada platform yok,
 * malloc yok, float yok (mAh/Wh tamsayi milli birim).
 *
 * Olaylar (K7), duz metin: {"n":<no>,"a":<acilis>,"t":<unix|0>,"o":"<ad>",...}
 *   basladi     devam (0 yok, 1 DEVAM aldi, 2 kapandi), oturum
 *   kayit_bitti sebep (KB_SEBEP_*), oturum, nokta
 *   dolu        —
 *   pil_bitti   durum, mah_milli, wh_milli, sure_ms
 *   esik        deger (esitlenmemis binde), esik
 *   deneme      — (Qt; a ve t cagirandan)
 * Kurallar:
 *  - `n` acilis basina 1'den artar; dusen olayin numarasi da harcanir (alici
 *    bosluktan kaybi gorur);
 *  - kuyruk BLD_KUYRUK olay; doluyken EN ESKI duser, `dusen` sayar (K7);
 *  - `basladi` tarama BITINCE (kayit != KDR_TARIYOR) bir kez ve HER ZAMAN ILK olay
 *    (`devam` ancak tarama bitince bilinir). Son gorulen sayaclar (bitir/pil) 0'dan
 *    baslar: acilis taramasinda kapanan oturum/pil testi `basladi`dan HEMEN SONRA
 *    kayit_bitti/pil_bitti olur; `basladi`dan once sayac olayi uretilmez (bekler).
 *    Her ARTIS bir olay (son olayin bilgisiyle); azalma olay degil, yalniz tasinir;
 *  - `deneme` (Qt): bld_deneme ile, ayni kuyruk ve numara yolundan;
 *  - `dolu` yalniz DOLU'ya GECISTE (acilis TARIYOR'dan sayilir);
 *  - `esik` kuruluyken esitlenmemis >= esik olunca bir kez; yeniden kurulma
 *    ancak esitlenmemis + BLD_ESIK_GERI < esik (ya da 0) olunca. Tarama
 *    surerken esik karari YOK (degerler henuz bilinmiyor);
 *  - durum (retained, K6): ilk kez, (kayit, oturum, tur) degisince, doluluk ya
 *    da esitlenmemis BLD_DURUM_FARK binde oynayinca, BLD_DURUM_MS'de bir.
 * Zarf (K5): "OKB1" | nonce 12 | sifreli metin | etiket 16; AAD = konu adi
 * (NUL'suz). AEAD (ChaCha20-Poly1305 IETF) ve rastgele `BildirimKripto`dan.
 * AVR'de sinaniyor: test_kayit.py B71.Q (SENARYO_BILDIRIM, sahte AEAD). */
#ifndef BILDIRIM_H
#define BILDIRIM_H

#include <limits.h>
#include <stdint.h>
#include <string.h>
#include "kayit_yonet.h"          /* KDR_* */

#ifndef BLD_KUYRUK
#define BLD_KUYRUK 16u            /* K7; AVR sinamasi kucuk verir */
#endif
#ifndef BLD_MESAJ
#define BLD_MESAJ 192u            /* olay basina bayt (NUL dahil) */
#endif
/* En uzun olay (NUL dahil): pil_bitti, butun sayilar en buyuk —
   {"n":10,"a":10,"t":10,"o":"pil_bitti" = 61; ,"durum":3 = 12; ,"mah_milli":10 = 23;
   ,"wh_milli":10 = 22; ,"sure_ms":10 = 21; } = 1; NUL = 1 -> 141. Alan eklersen BUNU
   guncelle: AVR sinamasi BLD_MESAJ'i tam bu degerle derler, en buyuk olay sigmazsa kirmizi. */
#define BLD_OLAY_AZAMI 141u
#define BLD_ESIK_VARSAYILAN 500u  /* binde */
#define BLD_ESIK_GERI 100u        /* K7: yeniden kurulma icin esigin bu kadar altina */
#define BLD_DURUM_FARK 10u        /* binde */
#define BLD_DURUM_MS 60000UL      /* K6: "son gorulme" */
#define BLD_ZARF_EK 32u           /* "OKB1" 4 + nonce 12 + etiket 16 */
#define BLD_ONEK_UZUN 32u         /* K4: 16 B -> 32 kucuk hex */

#define BLD_E_YER    (-1)         /* cikti tamponu yetmiyor */
#define BLD_E_KRIPTO (-2)         /* AEAD hata dondurdu (ya da islev yok) */
#define BLD_E_ARG    (-3)         /* gecersiz onek/konu */
#define BLD_E_BOS    (-4)         /* kuyruk bos */

/* Islev niteligi: kartta `static inline`. AVR sinamasi (2 KB RAM) `noinline`
   verir; yoksa derleyici her seyi tek cerceveye gomup yigini tasirir. */
#ifndef BLD_ISLEV
#define BLD_ISLEV static inline
#endif

/* derleme ani denetimleri (C ve C++'ta calisir; dosya kapsaminda typedef uyari vermez) */
typedef char bld__mesaj_yeter[(BLD_MESAJ >= BLD_OLAY_AZAMI) ? 1 : -1];
typedef char bld__kuyruk_sinir[(BLD_KUYRUK >= 1u && BLD_KUYRUK <= 255u) ? 1 : -1];

/* Yapistiricinin her turda doldurdugu anlik goruntu. Sayaclar acilista 0'dan
   baslayan, olay oldukca artan RAM sayaclari; bitir_* / pil_* SON olayin bilgisi. */
typedef struct {
    uint32_t acilis;
    uint32_t unix_s;              /* 0 = saat yok */
    uint8_t  kayit;               /* KDR_* */
    uint32_t oturum;              /* etkin oturum (0 = yok) */
    uint8_t  tur;                 /* etkin oturum turu */
    uint16_t doluluk_binde;
    uint16_t esitlenmemis_binde;
    uint32_t bitir_say;
    uint32_t bitir_oturum;
    uint32_t bitir_nokta;
    uint8_t  bitir_sebep;         /* KB_SEBEP_* */
    uint32_t pil_say;
    uint8_t  pil_durum;
    uint32_t pil_mah_milli;
    uint32_t pil_wh_milli;
    uint32_t pil_sure_ms;
    uint8_t  devam;               /* 0 yok, 1 DEVAM aldi, 2 kapandi */
} BildirimGoruntu;

typedef struct {
    char     kuyruk[BLD_KUYRUK][BLD_MESAJ];   /* halka; her olay NUL sonlu JSON */
    uint8_t  bas, adet;
    uint32_t dusen;               /* kuyruk tasmasinda dusen olay sayisi */
    uint32_t no;                  /* SONRAKI olayin numarasi (acilista 1) */
    uint32_t bitir_say, pil_say;  /* son gorulen sayaclar (acilista 0) */
    uint16_t esik;                /* binde */
    uint8_t  esik_kurulu;
    uint8_t  ilk;                 /* basladi henuz uretilmedi */
    uint8_t  son_kayit;           /* dolu gecisi icin onceki KDR_* */
    /* son yayinlanan durum */
    uint8_t  d_var, d_kayit, d_tur;
    uint16_t d_doluluk, d_esit;
    uint32_t d_oturum, d_ms;
} Bildirim;

/* AEAD: cikti = sifreli metin (duz_n) || etiket (16). 0 = tamam. */
typedef struct {
    void (*rastgele)(uint8_t *h, uint16_t n);
    int  (*aead)(const uint8_t anahtar[32], const uint8_t nonce[12], const uint8_t *aad,
                 uint16_t aad_n, const uint8_t *duz, uint16_t duz_n, uint8_t *cikti);
} BildirimKripto;

/* ─────────────────────────────── tasma denetimli JSON yazici */
typedef struct {
    char    *p;
    uint16_t n, azami;
    uint8_t  tasti;
} BldYazi;

BLD_ISLEV void bld__yazi_ac(BldYazi *y, char *p, uint16_t azami)
{
    y->p = p;
    y->n = 0u;
    y->azami = azami;
    y->tasti = (uint8_t)(azami == 0u);
    if (azami) p[0] = 0;
}

/* her zaman NUL'a yer birakir: n < azami */
BLD_ISLEV void bld__kar(BldYazi *y, char c)
{
    if ((uint32_t)y->n + 1u >= y->azami) {
        y->tasti = 1u;
        return;
    }
    y->p[y->n++] = c;
}

BLD_ISLEV void bld__metin(BldYazi *y, const char *s)
{
    while (*s) bld__kar(y, *s++);
}

/* JSON dizesi icerigi: " ve \ kacislanir, denetim karakteri '?' olur */
BLD_ISLEV void bld__kacisli(BldYazi *y, const char *s)
{
    char c;
    while ((c = *s++) != 0) {
        if (c == '"' || c == '\\') {
            bld__kar(y, '\\');
            bld__kar(y, c);
        } else if ((uint8_t)c < 0x20u) {
            bld__kar(y, '?');
        } else {
            bld__kar(y, c);
        }
    }
}

BLD_ISLEV void bld__sayi(BldYazi *y, uint32_t v)
{
    char t[10];
    uint8_t i = 0;
    do {
        t[i++] = (char)('0' + (uint8_t)(v % 10u));
        v /= 10u;
    } while (v);
    while (i) bld__kar(y, t[--i]);
}

/* ,"ad":v */
BLD_ISLEV void bld__alan(BldYazi *y, const char *ad, uint32_t v)
{
    bld__metin(y, ",\"");
    bld__metin(y, ad);
    bld__metin(y, "\":");
    bld__sayi(y, v);
}

/* uzunluk ya da BLD_E_YER (o zaman cikti bos dize) */
BLD_ISLEV int bld__bitir(BldYazi *y)
{
    if (!y->azami) return BLD_E_YER;
    if (y->tasti) {
        y->p[0] = 0;
        return BLD_E_YER;
    }
    y->p[y->n] = 0;
    return (int)y->n;
}

BLD_ISLEV uint16_t bld__fark(uint16_t a, uint16_t b)
{
    return (uint16_t)(a > b ? a - b : b - a);
}

/* ─────────────────────────────── olay kuyrugu */
BLD_ISLEV void bld_kur(Bildirim *b, uint16_t esik_binde)
{
    memset(b, 0, sizeof(*b));
    b->no = 1u;
    if (!esik_binde) esik_binde = BLD_ESIK_VARSAYILAN;
    if (esik_binde > 1000u) esik_binde = 1000u;
    b->esik = esik_binde;
    b->esik_kurulu = 1u;
    b->ilk = 1u;
    b->son_kayit = KDR_TARIYOR;
}

BLD_ISLEV uint8_t bld_kuyruk_adet(const Bildirim *b)
{
    return b->adet;
}

/* En eski olayi `cikti`ya kopyalar (silmez). Uzunluk, BLD_E_BOS ya da BLD_E_YER. */
BLD_ISLEV int bld_kuyruk_bas(const Bildirim *b, char *cikti, uint16_t azami)
{
    const char *s;
    size_t n;
    if (!b->adet) return BLD_E_BOS;
    s = b->kuyruk[b->bas];
    n = strlen(s);
    if (n + 1u > azami) return BLD_E_YER;
    memcpy(cikti, s, n + 1u);
    return (int)n;
}

/* Basarili yayindan sonra en eski olayi at. */
BLD_ISLEV void bld_kuyruk_at(Bildirim *b)
{
    if (!b->adet) return;
    b->bas = (uint8_t)((b->bas + 1u) % BLD_KUYRUK);
    b->adet--;
}

/* Kuyrukta yer ac (doluysa EN ESKI duser) ve olayin ortak basini yaz. */
BLD_ISLEV void bld__olay_ac(Bildirim *b, BldYazi *y, uint32_t acilis, uint32_t unix_s,
                            const char *ad)
{
    uint8_t i;
    if (b->adet >= BLD_KUYRUK) {
        b->bas = (uint8_t)((b->bas + 1u) % BLD_KUYRUK);
        b->adet--;
        b->dusen++;
    }
    i = (uint8_t)((b->bas + b->adet) % BLD_KUYRUK);
    bld__yazi_ac(y, b->kuyruk[i], BLD_MESAJ);
    bld__metin(y, "{\"n\":");
    bld__sayi(y, b->no);
    bld__alan(y, "a", acilis);
    bld__alan(y, "t", unix_s);
    bld__metin(y, ",\"o\":\"");
    bld__metin(y, ad);
    bld__kar(y, '"');
}

/* Olay kuyruga ancak TAM sigdiysa girer (BLD_OLAY_AZAMI'ye gore sigmamasi olanaksiz;
   olursa yarim JSON yayinlanmaz, dusen sayilir). Numara her durumda harcanir. */
BLD_ISLEV uint8_t bld__olay_kapat(Bildirim *b, BldYazi *y)
{
    uint8_t girdi = 0u;
    bld__kar(y, '}');
    if (bld__bitir(y) < 0) {
        b->dusen++;
    } else {
        b->adet++;
        girdi = 1u;
    }
    b->no++;
    return girdi;
}

/* Her turda. Donus: kuyruga giren olay sayisi. `simdi_ms` bugun kullanilmiyor
   (imza durum islevleriyle ayni; ileride hiz siniri icin). */
BLD_ISLEV uint8_t bld_adim(Bildirim *b, const BildirimGoruntu *g, uint32_t simdi_ms)
{
    BldYazi y;
    uint8_t n = 0u;
    (void)simdi_ms;
    if (b->ilk) {
        if (g->kayit == KDR_TARIYOR) {      /* devam ancak tarama bitince bilinir */
            b->son_kayit = g->kayit;
            return 0u;                      /* sayac olaylari basladi'yi BEKLER */
        }
        b->ilk = 0u;
        bld__olay_ac(b, &y, g->acilis, g->unix_s, "basladi");
        bld__alan(&y, "devam", g->devam);
        bld__alan(&y, "oturum", g->oturum);
        n = (uint8_t)(n + bld__olay_kapat(b, &y));
    }
    if (g->bitir_say != b->bitir_say) {
        if ((int32_t)(g->bitir_say - b->bitir_say) > 0) {
            bld__olay_ac(b, &y, g->acilis, g->unix_s, "kayit_bitti");
            bld__alan(&y, "sebep", g->bitir_sebep);
            bld__alan(&y, "oturum", g->bitir_oturum);
            bld__alan(&y, "nokta", g->bitir_nokta);
            n = (uint8_t)(n + bld__olay_kapat(b, &y));
        }
        b->bitir_say = g->bitir_say;
    }
    if (g->pil_say != b->pil_say) {
        if ((int32_t)(g->pil_say - b->pil_say) > 0) {
            bld__olay_ac(b, &y, g->acilis, g->unix_s, "pil_bitti");
            bld__alan(&y, "durum", g->pil_durum);
            bld__alan(&y, "mah_milli", g->pil_mah_milli);
            bld__alan(&y, "wh_milli", g->pil_wh_milli);
            bld__alan(&y, "sure_ms", g->pil_sure_ms);
            n = (uint8_t)(n + bld__olay_kapat(b, &y));
        }
        b->pil_say = g->pil_say;
    }
    if (g->kayit == KDR_DOLU && b->son_kayit != KDR_DOLU) {
        bld__olay_ac(b, &y, g->acilis, g->unix_s, "dolu");
        n = (uint8_t)(n + bld__olay_kapat(b, &y));
    }
    b->son_kayit = g->kayit;
    if (g->kayit != KDR_TARIYOR) {          /* tarama surerken esitlenmemis bilinmiyor */
        if (b->esik_kurulu) {
            if (g->esitlenmemis_binde >= b->esik) {
                b->esik_kurulu = 0u;
                bld__olay_ac(b, &y, g->acilis, g->unix_s, "esik");
                bld__alan(&y, "deger", g->esitlenmemis_binde);
                bld__alan(&y, "esik", b->esik);
                n = (uint8_t)(n + bld__olay_kapat(b, &y));
            }
        } else if (!g->esitlenmemis_binde
                   || (uint32_t)g->esitlenmemis_binde + BLD_ESIK_GERI < b->esik) {
            b->esik_kurulu = 1u;
        }
    }
    return n;
}

/* Qt deneme olayi: {"n":..,"a":acilis,"t":unix_s,"o":"deneme"} — ayni kuyruk/numara
   yolu (doluysa en eski duser). */
BLD_ISLEV void bld_deneme(Bildirim *b, uint32_t acilis, uint32_t unix_s)
{
    BldYazi y;
    bld__olay_ac(b, &y, acilis, unix_s, "deneme");
    (void)bld__olay_kapat(b, &y);
}

/* ─────────────────────────────── durum (retained) + vasiyet */
BLD_ISLEV uint8_t bld_durum_gerek(const Bildirim *b, const BildirimGoruntu *g, uint32_t simdi_ms)
{
    if (!b->d_var) return 1u;
    if (g->kayit != b->d_kayit || g->oturum != b->d_oturum || g->tur != b->d_tur) return 1u;
    if (bld__fark(g->doluluk_binde, b->d_doluluk) >= BLD_DURUM_FARK) return 1u;
    if (bld__fark(g->esitlenmemis_binde, b->d_esit) >= BLD_DURUM_FARK) return 1u;
    if ((uint32_t)(simdi_ms - b->d_ms) >= BLD_DURUM_MS) return 1u;
    return 0u;
}

BLD_ISLEV void bld_durum_yayinlandi(Bildirim *b, const BildirimGoruntu *g, uint32_t simdi_ms)
{
    b->d_var = 1u;
    b->d_kayit = g->kayit;
    b->d_oturum = g->oturum;
    b->d_tur = g->tur;
    b->d_doluluk = g->doluluk_binde;
    b->d_esit = g->esitlenmemis_binde;
    b->d_ms = simdi_ms;
}

/* {"c":1,"a":..,"t":..,"k":..,"o":..,"y":..,"d":..,"e":..,"f":".."} — uzunluk ya da BLD_E_YER */
BLD_ISLEV int bld_durum_json(const BildirimGoruntu *g, const char *fw, char *cikti, uint16_t azami)
{
    BldYazi y;
    bld__yazi_ac(&y, cikti, azami);
    bld__metin(&y, "{\"c\":1");
    bld__alan(&y, "a", g->acilis);
    bld__alan(&y, "t", g->unix_s);
    bld__alan(&y, "k", g->kayit);
    bld__alan(&y, "o", g->oturum);
    bld__alan(&y, "y", g->tur);
    bld__alan(&y, "d", g->doluluk_binde);
    bld__alan(&y, "e", g->esitlenmemis_binde);
    bld__metin(&y, ",\"f\":\"");
    bld__kacisli(&y, fw ? fw : "");
    bld__metin(&y, "\"}");
    return bld__bitir(&y);
}

/* LWT: {"c":0,"a":..} */
BLD_ISLEV int bld_vasiyet_json(uint32_t acilis, char *cikti, uint16_t azami)
{
    BldYazi y;
    bld__yazi_ac(&y, cikti, azami);
    bld__metin(&y, "{\"c\":0");
    bld__alan(&y, "a", acilis);
    bld__kar(&y, '}');
    return bld__bitir(&y);
}

/* ─────────────────────────────── konu + zarf */
/* "ok/<onek>/<son>". onek tam 32 kucuk hex; son bos degil, '/', '+', '#' icermez.
   Uzunluk, BLD_E_ARG ya da BLD_E_YER. */
BLD_ISLEV int bld_konu(const char onek_hex32[33], const char *son, char *cikti, uint8_t azami)
{
    BldYazi y;
    uint8_t i;
    const char *s;
    for (i = 0; i < BLD_ONEK_UZUN; i++) {
        const char c = onek_hex32[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return BLD_E_ARG;
    }
    if (onek_hex32[BLD_ONEK_UZUN] != 0 || !son || !*son) return BLD_E_ARG;
    for (s = son; *s; s++)
        if (*s == '/' || *s == '+' || *s == '#') return BLD_E_ARG;
    bld__yazi_ac(&y, cikti, azami);
    bld__metin(&y, "ok/");
    bld__metin(&y, onek_hex32);
    bld__kar(&y, '/');
    bld__metin(&y, son);
    return bld__bitir(&y);
}

/* "OKB1" | nonce 12 (rastgele) | AEAD(anahtar, nonce, AAD = konu, json) | etiket 16.
   Uzunluk ya da BLD_E_YER (rastgele HARCANMADAN) / BLD_E_KRIPTO / BLD_E_ARG. */
BLD_ISLEV int bld_zarf(const BildirimKripto *k, const uint8_t anahtar[32], const char *konu,
                       const char *json, uint8_t *cikti, uint16_t azami)
{
    uint32_t n, kn, gerek;          /* 32 bit: AVR'de size_t 16 bit (-Wtype-limits) */
    if (!k || !k->rastgele || !k->aead) return BLD_E_KRIPTO;
    if (!konu || !json) return BLD_E_ARG;
    kn = (uint32_t)strlen(konu);
    if (!kn || kn > 0xFFFFu) return BLD_E_ARG;
    n = (uint32_t)strlen(json);
    if (n > 0xFFFFu) return BLD_E_YER;
    gerek = n + BLD_ZARF_EK;
    if (gerek > azami || gerek > (uint32_t)INT_MAX) return BLD_E_YER;
    memcpy(cikti, "OKB1", 4u);
    k->rastgele(cikti + 4, 12u);
    if (k->aead(anahtar, cikti + 4, (const uint8_t *)konu, (uint16_t)kn,
                (const uint8_t *)json, (uint16_t)n, cikti + 16)) {
        memset(cikti, 0, gerek);            /* yarim zarf yayinlanmasin */
        return BLD_E_KRIPTO;
    }
    return (int)gerek;
}

#endif /* BILDIRIM_H */
