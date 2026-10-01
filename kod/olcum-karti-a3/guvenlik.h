/* guvenlik.h — 1D cihaz eslestirmesi + imzali istekler: MANTIK (platformsuz).
 *
 * Tasarim: tasarim/2026-10-01-1d-eslestirme.md (K4-K11, K17).
 *   P      = PBKDF2-HMAC-SHA256(parola, tuz, tur, 32)
 *   kanit  = HMAC(P, "OK1-istemci\n" kimlik "\n" nk "\n" nc "\n" ad)   (hex alanlar)
 *   kart   = HMAC(P, "OK1-kart\n"    kimlik "\n" nk "\n" nc "\n" n)
 *   K      = HMAC(P, "OK1-anahtar\n" kimlik "\n" nk "\n" nc "\n" n)
 *   imza   = HMAC(K, "OK1\n" yontem "\n" yol ["?" a=d&..] "\n" acilis "\n" sayac "\n" sha256(govde))
 * Sorgu ad/degerleri YUZDE KODLU (RFC 3986 ayrilmamis aynen) — kopru/imza.py ile ayni.
 *
 * Kriptografi `GuvKripto`dan (kartta mbedTLS, AVR testinde sha256_sinama.h),
 * kalicilik `GuvNvs`ten (ADA gore blob). `K` RAM'de TUTULMAZ: dogrulamada NVS'ten
 * okunur. RAM'de cihaz basina yalniz tekrar penceresi.
 * Karsilastirmalar sabit zamanli (guv__esit); dogrulamada ONCE HMAC, SONRA pencere
 * (sahte imzali buyuk sayac pencereyi ilerletemez).
 * Son inceleme (1D) duzeltmeleri:
 *  - kriptografi HATASI karar degildir: HMAC/SHA hata dondururse imza REDDEDILIR
 *    (yigindaki eski MAC'e guvenilmez), eslestirme GUV_E_KRIPTO;
 *  - PBKDF2 cekirdekte (guv_pbkdf2), GUV_NEFES_ARALIK turda bir `nefes` (kartta
 *    zamanlayiciya pay; bekci/WDT); P YALNIZ guv_p_hesapla ile hesaplanir — kartta
 *    cekirdek 1, web yolunda HIC PBKDF2 yok;
 *  - (kart tezgahi) PBKDF2 ipad/opad SHA durumunu kopyalar (`sha_kopya`): 85 -> 30 us/tur;
 *  - ayar kaydi VAR ama okunamiyorsa (boy/surum) fail-CLOSED: imza zorunlu.
 * AVR'de sinaniyor: test_kayit.py B71.U (SENARYO_GUV). */
#ifndef GUVENLIK_H
#define GUVENLIK_H

#include <stdint.h>
#include <string.h>

#define GUV_CIHAZ_AZAMI   8u
#define GUV_AD_AZAMI      24u
#define GUV_PAROLA_EN_AZ  12u     /* K3, kullanici onayi 2026-10-01 (kartta 20 000 tur) */
#define GUV_ESLES_SURE_MS 60000UL
#define GUV_PENCERE       64u
#define GUV_BEKLE_AZAMI_K 8u          /* 2^8 s ~ 4 dk */
#define GUV_SON_YAZ_S     3600UL      /* "son gorulme" NVS'e saatte en fazla bir kez */
#define GUV_AYAR_SURUM    1u
/* Varsayilan tur kartta < 1 s (spec K4). Kart tezgahi 2026-10-01: ESP32-S3'te en hizli
   PBKDF2 (ipad/opad kopyasi) 30.5 us/tur, firmware icinde ~38 us/tur — 25 000 tur 956 ms
   (yuzde 4 pay, WiFi yukunde asar); 20 000 ~ 0.77 s. */
#ifndef GUV_TUR_VARSAYILAN
#define GUV_TUR_VARSAYILAN 20000UL
#endif
#define GUV_TUR_EN_AZ     10000UL     /* istemci de bunun altini REDDEDER (sahte kart) */
#define GUV_TUR_EN_COK    200000UL
#ifndef GUV_NEFES_ARALIK
#define GUV_NEFES_ARALIK  1000UL
#endif
/* Islev niteligi: kartta `static inline`. AVR sinamasi (2 KB RAM) `noinline`
   verir; yoksa derleyici her seyi tek cerceveye gomup yigini tasirir. */
#ifndef GUV_ISLEV
#define GUV_ISLEV static inline
#endif
#ifndef GUV_CTX_BOYU
#define GUV_CTX_BOYU      224u
#endif
#ifndef GUV_SHA_BOYU
#define GUV_SHA_BOYU      GUV_CTX_BOYU  /* yalniz SHA baglami (guv_pbkdf2 yiginda 3 tane) */
#endif

#define GUV_E_YOK    (-1)
#define GUV_E_IMZA   (-2)
#define GUV_E_TEKRAR (-3)
#define GUV_E_CIHAZ  (-4)
#define GUV_E_BEKLE  (-5)
#define GUV_E_DOLU   (-6)
#define GUV_E_PAROLA (-7)
#define GUV_E_KANIT  (-8)
#define GUV_E_AD     (-9)
#define GUV_E_NVS    (-10)
#define GUV_E_KRIPTO (-11)
#define GUV_E_AYAR   (-12)            /* ayar kaydi bozuk: fail-closed (zorunlu 1) */

/* `bas` ve `bit` 0 = tamam. `ekle` hatasi baglamda SAKLANIR, `bit` onu dondurur. */
typedef struct {
    int  (*hmac_bas)(void *ctx, const uint8_t *anahtar, uint16_t n);
    void (*hmac_ekle)(void *ctx, const void *v, uint16_t n);
    int  (*hmac_bit)(void *ctx, uint8_t c[32]);
    int  (*sha_bas)(void *ctx);
    void (*sha_ekle)(void *ctx, const void *v, uint16_t n);
    int  (*sha_bit)(void *ctx, uint8_t c[32]);
    /* hedef (baslatilmamis ya da bitmis) kaynagin SHA durumunu alir; guv_pbkdf2 ipad/opad
       durumunu bir kez kurup her turda kopyalar */
    int  (*sha_kopya)(void *hedef, const void *kaynak);
    void (*rastgele)(uint8_t *h, uint16_t n);
    void (*nefes)(void);                    /* NULL olabilir */
} GuvKripto;

/* oku: 0 tamam, -1 YOK (hic yazilmamis), -2 BOZUK (boy/okuma hatasi). yaz: 0 tamam. */
typedef struct {
    int (*oku)(void *b, const char *ad, void *h, uint16_t n);
    int (*yaz)(void *b, const char *ad, const void *k, uint16_t n);
    void *baglam;
} GuvNvs;

typedef struct {
    uint8_t  surum, zorunlu, misafir, _bos;
    uint32_t tur;
    uint8_t  tuz[16];
    uint8_t  kimlik[8];
} GuvAyar;

typedef struct {
    uint8_t  var;
    char     ad[GUV_AD_AZAMI + 1];
    uint8_t  K[32];
    uint32_t eklenme, son;
} GuvCihaz;

typedef struct {
    uint8_t  var;
    uint64_t son_sayac;
    uint64_t pencere;           /* bit i: (son_sayac - i) goruldu */
    uint32_t son_yazim;
} GuvCanli;

typedef union {
    uint8_t  b[GUV_CTX_BOYU];
    uint64_t _hiza;
    void    *_isaret;
} GuvCtx;

typedef union {
    uint8_t  b[GUV_SHA_BOYU];
    uint64_t _hiza;
    void    *_isaret;
} GuvShaCtx;

typedef struct {
    const GuvKripto *k;
    const GuvNvs    *nvs;
    GuvAyar  ayar;
    uint8_t  ayar_bozuk;        /* fail-closed: kayit var ama okunamadi */
    GuvCanli c[GUV_CIHAZ_AZAMI];
    uint8_t  acilis[16];
    uint8_t  P[32];
    uint8_t  p_var;
    /* bekleyen eslestirme (ayni anda tek) */
    uint8_t  e_var, e_no;
    uint8_t  e_nk[16], e_nc[16];
    char     e_ad[GUV_AD_AZAMI + 1];
    uint32_t e_bas_ms;
    /* deneme siniri */
    uint8_t  d_var, d_k;
    uint32_t d_serbest_ms;
} GuvDurum;

typedef struct {
    GuvCtx  ctx;
    uint8_t n, ilk_arg;
} GuvImza;

/* ── yardimcilar ──────────────────────────────────────────────────────── */
GUV_ISLEV void guv__hex(const uint8_t *v, uint8_t n, char *h)
{
    static const char x[] = "0123456789abcdef";
    uint8_t i;
    for (i = 0; i < n; i++) {
        h[2 * i] = x[v[i] >> 4];
        h[2 * i + 1] = x[v[i] & 15u];
    }
    h[2 * n] = 0;
}

/* sabit zamanli: erken cikis yok */
GUV_ISLEV uint8_t guv__esit(const uint8_t *a, const uint8_t *b, uint8_t n)
{
    uint8_t f = 0, i;
    for (i = 0; i < n; i++) f |= (uint8_t)(a[i] ^ b[i]);
    return (uint8_t)(f == 0u);
}

GUV_ISLEV int guv__hexten(const char *h, uint8_t *v, uint8_t n)
{
    uint8_t i, j, d;
    for (i = 0; i < n; i++) {
        uint8_t b = 0;
        for (j = 0; j < 2u; j++) {
            char c = h[2 * i + j];
            if (c >= '0' && c <= '9') d = (uint8_t)(c - '0');
            else if (c >= 'a' && c <= 'f') d = (uint8_t)(c - 'a' + 10);
            else if (c >= 'A' && c <= 'F') d = (uint8_t)(c - 'A' + 10);
            else return -1;
            b = (uint8_t)((b << 4) | d);
        }
        v[i] = b;
    }
    return h[2 * n] ? -1 : 0;
}

GUV_ISLEV void guv__dec(uint64_t v, char *t)
{
    char r[21];
    uint8_t n = 0;
    do {
        r[n++] = (char)('0' + (uint8_t)(v % 10u));
        v /= 10u;
    } while (v);
    while (n) *t++ = r[--n];
    *t = 0;
}

GUV_ISLEV void guv__cihaz_adi(uint8_t n, char ad[4])
{
    ad[0] = 'c';
    ad[1] = (char)('0' + n);
    ad[2] = 0;
}

/* 1-24 bayt, kontrol karakteri yok (kanit metninde ayirici '\n') */
GUV_ISLEV uint8_t guv__ad_gecerli(const char *ad)
{
    uint16_t n = 0;
    if (!ad) return 0;
    while (ad[n]) {
        uint8_t c = (uint8_t)ad[n];
        if (c < 0x20u || c == 0x7Fu) return 0;
        if (++n > GUV_AD_AZAMI) return 0;
    }
    return (uint8_t)(n > 0u);
}

GUV_ISLEV uint8_t guv__parola_uygun(const char *p)
{
    return (uint8_t)(p && strlen(p) >= GUV_PAROLA_EN_AZ);
}

GUV_ISLEV void guv__ekle(const GuvDurum *g, void *ctx, const char *s)
{
    g->k->hmac_ekle(ctx, s, (uint16_t)strlen(s));
}

/* PBKDF2-HMAC-SHA256, tek blok (32 B). Tablo HMAC'i; GUV_NEFES_ARALIK turda bir
   `nefes` (kartta zamanlayiciya pay). 0 tamam, GUV_E_KRIPTO hata. */
GUV_ISLEV int guv_pbkdf2(const GuvKripto *k, const char *parola, const uint8_t *tuz,
                         uint16_t tn, uint32_t tur, uint8_t c[32])
{
    /* HMAC'in ipad/opad durumu BIR KEZ kurulur, her turda KOPYALANIR: tur basina 2 SHA
       sikistirmasi. Kart tezgahi 2026-10-01: her turda HMAC kurulumu (+ bellek ayirma)
       85 us/tur, 50 000 tur 4.76 s; kopya ile 30.5 us/tur (B71.U19, B72.F99). */
    static const uint8_t bir[4] = {0u, 0u, 0u, 1u};
    GuvShaCtx ic, dis, is;
    uint8_t ped[64], u[32], i;
    const uint8_t *a = (const uint8_t *)parola;
    uint16_t pn = (uint16_t)strlen(parola);
    uint32_t t;
    int r = 0;
    if (!tur) return GUV_E_KRIPTO;
    if (pn > 64u) {                               /* RFC 2104: uzun anahtar once ozetlenir */
        if (k->sha_bas(is.b)) return GUV_E_KRIPTO;
        k->sha_ekle(is.b, parola, pn);
        if (k->sha_bit(is.b, u)) return GUV_E_KRIPTO;
        a = u;
        pn = 32u;
    }
    memset(ped, 0x36, sizeof(ped));
    for (i = 0; i < pn; i++) ped[i] ^= a[i];
    if (k->sha_bas(ic.b)) {
        r = GUV_E_KRIPTO;
    } else {
        k->sha_ekle(ic.b, ped, 64);
        for (i = 0; i < 64u; i++) ped[i] ^= (uint8_t)(0x36u ^ 0x5cu);
        if (k->sha_bas(dis.b)) {
            (void)k->sha_bit(ic.b, u);
            r = GUV_E_KRIPTO;
        }
    }
    if (r) {
        memset(ped, 0, sizeof(ped));
        memset(u, 0, sizeof(u));
        return r;
    }
    k->sha_ekle(dis.b, ped, 64);
    memset(ped, 0, sizeof(ped));
    for (t = 0; t < tur; t++) {
        if (k->sha_kopya(is.b, ic.b)) { r = GUV_E_KRIPTO; break; }
        if (t == 0) {
            k->sha_ekle(is.b, tuz, tn);
            k->sha_ekle(is.b, bir, 4);
        } else {
            k->sha_ekle(is.b, u, 32);
        }
        if (k->sha_bit(is.b, u) || k->sha_kopya(is.b, dis.b)) { r = GUV_E_KRIPTO; break; }
        k->sha_ekle(is.b, u, 32);
        if (k->sha_bit(is.b, u)) { r = GUV_E_KRIPTO; break; }
        if (t == 0) memcpy(c, u, 32);
        else for (i = 0; i < 32u; i++) c[i] ^= u[i];
        if (k->nefes && (t % GUV_NEFES_ARALIK) == 0u) k->nefes();
    }
    (void)k->sha_bit(ic.b, u);                    /* ipad/opad durumlari serbest */
    (void)k->sha_bit(dis.b, u);
    memset(u, 0, sizeof(u));
    if (r) memset(c, 0, 32);
    return r;
}

/* HMAC(P, etiket \n kimlik \n nk \n nc \n son); 0 tamam, GUV_E_KRIPTO hata */
GUV_ISLEV int guv__es_hmac(const GuvDurum *g, const char *etiket, const uint8_t nk[16],
                           const uint8_t nc[16], const char *son, uint8_t c[32])
{
    GuvCtx ctx;
    char h[33];
    if (g->k->hmac_bas(ctx.b, g->P, 32)) return GUV_E_KRIPTO;
    guv__ekle(g, ctx.b, etiket);
    guv__ekle(g, ctx.b, "\n");
    guv__hex(g->ayar.kimlik, 8, h);
    guv__ekle(g, ctx.b, h);
    guv__ekle(g, ctx.b, "\n");
    guv__hex(nk, 16, h);
    guv__ekle(g, ctx.b, h);
    guv__ekle(g, ctx.b, "\n");
    guv__hex(nc, 16, h);
    guv__ekle(g, ctx.b, h);
    guv__ekle(g, ctx.b, "\n");
    guv__ekle(g, ctx.b, son);
    return g->k->hmac_bit(ctx.b, c) ? GUV_E_KRIPTO : 0;
}

GUV_ISLEV void guv__ayar_uret(GuvDurum *g)
{
    memset(&g->ayar, 0, sizeof(g->ayar));
    g->ayar.surum = GUV_AYAR_SURUM;
    g->ayar.tur = GUV_TUR_VARSAYILAN;
    g->k->rastgele(g->ayar.tuz, 16);
    g->k->rastgele(g->ayar.kimlik, 8);
}

GUV_ISLEV int guv__ayar_yaz(GuvDurum *g)
{
    return g->nvs->yaz(g->nvs->baglam, "ayar", &g->ayar, (uint16_t)sizeof(g->ayar))
           ? GUV_E_NVS : 0;
}

GUV_ISLEV int guv__bos_numara(const GuvDurum *g)
{
    uint8_t i;
    for (i = 0; i < GUV_CIHAZ_AZAMI; i++)
        if (!g->c[i].var) return (int)(i + 1u);
    return GUV_E_DOLU;
}

GUV_ISLEV int guv__cihaz_yaz(GuvDurum *g, uint8_t n, const GuvCihaz *c)
{
    char ad[4];
    guv__cihaz_adi(n, ad);
    return g->nvs->yaz(g->nvs->baglam, ad, c, (uint16_t)sizeof(*c)) ? GUV_E_NVS : 0;
}

GUV_ISLEV int guv__ekle_cihaz(GuvDurum *g, uint8_t n, const char *ad, const uint8_t K[32],
                              uint32_t unix)
{
    GuvCihaz c;
    int r;
    memset(&c, 0, sizeof(c));
    c.var = 1u;
    strncpy(c.ad, ad, GUV_AD_AZAMI);
    memcpy(c.K, K, 32);
    c.eklenme = unix;
    c.son = unix;
    r = guv__cihaz_yaz(g, n, &c);
    memset(&c, 0, sizeof(c));
    if (r) return r;
    memset(&g->c[n - 1u], 0, sizeof(g->c[0]));
    g->c[n - 1u].var = 1u;
    g->c[n - 1u].son_yazim = unix;
    return 0;
}

/* ── genel arayuz ─────────────────────────────────────────────────────── */
/* 0 tamam; GUV_E_AYAR: ayar kaydi VAR ama okunamadi — durum KULLANILABILIR, imza
   ZORUNLU (fail-closed), kimlik/tuz bilinmiyor (eslestirme yok) ve diske YAZILMAZ;
   guv_ayar_yaz yeniden uretip yazar. GUV_E_NVS: ilk ayar yazilamadi. */
GUV_ISLEV int guv_ac(GuvDurum *g, const GuvKripto *k, const GuvNvs *nvs)
{
    GuvCihaz c;
    char ad[4];
    uint8_t i;
    int r, sonuc = 0;
    memset(g, 0, sizeof(*g));
    g->k = k;
    g->nvs = nvs;
    r = nvs->oku(nvs->baglam, "ayar", &g->ayar, (uint16_t)sizeof(g->ayar));
    if (r == -1) {                                       /* hic yazilmamis */
        guv__ayar_uret(g);
        if (guv__ayar_yaz(g)) sonuc = GUV_E_NVS;
    } else if (r || g->ayar.surum != GUV_AYAR_SURUM) {   /* bozuk: fail-CLOSED */
        memset(&g->ayar, 0, sizeof(g->ayar));
        g->ayar.zorunlu = 1u;
        g->ayar.tur = GUV_TUR_VARSAYILAN;
        g->ayar_bozuk = 1u;
        sonuc = GUV_E_AYAR;
    }
    for (i = 1; i <= GUV_CIHAZ_AZAMI; i++) {
        guv__cihaz_adi(i, ad);
        if (!nvs->oku(nvs->baglam, ad, &c, (uint16_t)sizeof(c)) && c.var) {
            g->c[i - 1u].var = 1u;
            g->c[i - 1u].son_yazim = c.son;
        }
    }
    memset(&c, 0, sizeof(c));
    k->rastgele(g->acilis, 16);
    return sonuc;
}

GUV_ISLEV void guv_parola_degisti(GuvDurum *g)
{
    g->p_var = 0;
    memset(g->P, 0, sizeof(g->P));
}

/* P'yi hesapla (kartta CEKIRDEK 1; web yolunda PBKDF2 YOK). Parola uygun degilse P
   silinir ve eslestirme PAROLA reddi verir. */
GUV_ISLEV int guv_p_hesapla(GuvDurum *g, const char *parola)
{
    guv_parola_degisti(g);
    if (g->ayar_bozuk) return GUV_E_AYAR;
    if (!guv__parola_uygun(parola)) return GUV_E_PAROLA;
    if (guv_pbkdf2(g->k, parola, g->ayar.tuz, 16, g->ayar.tur, g->P)) {
        memset(g->P, 0, sizeof(g->P));
        return GUV_E_KRIPTO;
    }
    g->p_var = 1u;
    return 0;
}

GUV_ISLEV int guv_esles_baslat(GuvDurum *g, const char *ad, const uint8_t nc[16],
                               uint32_t simdi_ms, uint8_t *eno, uint8_t nk[16])
{
    int n;
    if (!g->p_var) return GUV_E_PAROLA;
    if (!guv__ad_gecerli(ad)) return GUV_E_AD;
    if (g->d_var && (int32_t)(simdi_ms - g->d_serbest_ms) < 0) return GUV_E_BEKLE;
    n = guv__bos_numara(g);
    if (n < 0) return n;
    g->e_var = 1u;
    g->e_no = (uint8_t)(g->e_no + 1u);
    if (!g->e_no) g->e_no = 1u;
    memcpy(g->e_nc, nc, 16);
    g->k->rastgele(g->e_nk, 16);
    memset(g->e_ad, 0, sizeof(g->e_ad));
    strncpy(g->e_ad, ad, GUV_AD_AZAMI);
    g->e_bas_ms = simdi_ms;
    *eno = g->e_no;
    memcpy(nk, g->e_nk, 16);
    return 0;
}

GUV_ISLEV int guv_esles_kanit(GuvDurum *g, uint8_t eno, const uint8_t kanit[32],
                              uint32_t simdi_ms, uint32_t unix, uint8_t *n_cikis,
                              uint8_t kart_kanit[32])
{
    uint8_t bek[32], K[32];
    char son[4];
    int n, r;
    if (!g->e_var || eno != g->e_no) return GUV_E_YOK;
    if ((uint32_t)(simdi_ms - g->e_bas_ms) > GUV_ESLES_SURE_MS) {
        g->e_var = 0;
        return GUV_E_YOK;
    }
    if (!g->p_var) return GUV_E_PAROLA;
    g->e_var = 0;                                  /* her bekleyen icin TEK deneme */
    if (guv__es_hmac(g, "OK1-istemci", g->e_nk, g->e_nc, g->e_ad, bek)) return GUV_E_KRIPTO;
    if (!guv__esit(bek, kanit, 32)) {
        g->d_var = 1u;
        g->d_serbest_ms = simdi_ms + (1000UL << g->d_k);
        if (g->d_k < GUV_BEKLE_AZAMI_K) g->d_k++;
        return GUV_E_KANIT;
    }
    g->d_var = 0;
    g->d_k = 0;
    n = guv__bos_numara(g);
    if (n < 0) return n;
    son[0] = (char)('0' + n);
    son[1] = 0;
    if (guv__es_hmac(g, "OK1-anahtar", g->e_nk, g->e_nc, son, K)
        || guv__es_hmac(g, "OK1-kart", g->e_nk, g->e_nc, son, kart_kanit)) {
        memset(K, 0, sizeof(K));
        return GUV_E_KRIPTO;
    }
    r = guv__ekle_cihaz(g, (uint8_t)n, g->e_ad, K, unix);
    memset(K, 0, sizeof(K));
    if (r) return r;
    *n_cikis = (uint8_t)n;
    return 0;
}

/* USB (seri) eslestirmesi: parola yok, K rastgele; cagiran K'yi YALNIZ seri porta basar */
GUV_ISLEV int guv_esles_usb(GuvDurum *g, const char *ad, uint32_t unix, uint8_t *n_cikis,
                            uint8_t K[32])
{
    int n, r;
    if (!guv__ad_gecerli(ad)) return GUV_E_AD;
    n = guv__bos_numara(g);
    if (n < 0) return n;
    g->k->rastgele(K, 32);
    r = guv__ekle_cihaz(g, (uint8_t)n, ad, K, unix);
    if (r) return r;
    *n_cikis = (uint8_t)n;
    return 0;
}

/* n = 0: hepsi */
GUV_ISLEV int guv_cihaz_sil(GuvDurum *g, uint8_t n)
{
    GuvCihaz c;
    uint8_t i;
    memset(&c, 0, sizeof(c));
    if (!n) {
        for (i = 1; i <= GUV_CIHAZ_AZAMI; i++) {
            if (!g->c[i - 1u].var) continue;
            if (guv__cihaz_yaz(g, i, &c)) return GUV_E_NVS;
            memset(&g->c[i - 1u], 0, sizeof(g->c[0]));
        }
        return 0;
    }
    if (n > GUV_CIHAZ_AZAMI || !g->c[n - 1u].var) return GUV_E_YOK;
    if (guv__cihaz_yaz(g, n, &c)) return GUV_E_NVS;
    memset(&g->c[n - 1u], 0, sizeof(g->c[0]));
    return 0;
}

GUV_ISLEV int guv_cihaz_oku(const GuvDurum *g, uint8_t n, GuvCihaz *c)
{
    char ad[4];
    if (!n || n > GUV_CIHAZ_AZAMI || !g->c[n - 1u].var) return GUV_E_YOK;
    guv__cihaz_adi(n, ad);
    if (g->nvs->oku(g->nvs->baglam, ad, c, (uint16_t)sizeof(*c))) return GUV_E_NVS;
    return c->var ? 0 : GUV_E_YOK;
}

/* ── imza dogrulama: bas → arg* → bit ─────────────────────────────────── */
/* bas basariliysa (0) cagiran bit'i HER ZAMAN cagirir (baglam serbest kalsin) */
GUV_ISLEV int guv_imza_bas(GuvDurum *g, GuvImza *im, uint8_t n, const char *yontem,
                           const char *yol)
{
    GuvCihaz c;
    int r = guv_cihaz_oku(g, n, &c);
    if (r) return r == GUV_E_YOK ? GUV_E_CIHAZ : r;
    r = g->k->hmac_bas(im->ctx.b, c.K, 32);
    memset(&c, 0, sizeof(c));
    if (r) return GUV_E_IMZA;
    guv__ekle(g, im->ctx.b, "OK1\n");
    guv__ekle(g, im->ctx.b, yontem);
    guv__ekle(g, im->ctx.b, "\n");
    guv__ekle(g, im->ctx.b, yol);
    im->n = n;
    im->ilk_arg = 1u;
    return 0;
}

/* RFC 3986: A-Z a-z 0-9 - . _ ~ aynen, gerisi %XX (buyuk harf) */
GUV_ISLEV void guv__yuzde(const GuvDurum *g, void *ctx, const char *s)
{
    static const char x[] = "0123456789ABCDEF";
    char t[3];
    for (; *s; s++) {
        uint8_t c = (uint8_t)*s;
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')
            || c == '-' || c == '.' || c == '_' || c == '~') {
            g->k->hmac_ekle(ctx, s, 1);
        } else {
            t[0] = '%';
            t[1] = x[c >> 4];
            t[2] = x[c & 15u];
            g->k->hmac_ekle(ctx, t, 3);
        }
    }
}

GUV_ISLEV void guv_imza_arg(GuvDurum *g, GuvImza *im, const char *ad, const char *deger)
{
    guv__ekle(g, im->ctx.b, im->ilk_arg ? "?" : "&");
    im->ilk_arg = 0;
    guv__yuzde(g, im->ctx.b, ad);
    guv__ekle(g, im->ctx.b, "=");
    guv__yuzde(g, im->ctx.b, deger);
}

GUV_ISLEV int guv_imza_bit(GuvDurum *g, GuvImza *im, uint64_t sayac,
                           const uint8_t govde_ozet[32], const char *imza_hex, uint32_t unix)
{
    GuvCanli *cv;
    uint8_t mac[32], gel[32];
    char t[65];
    guv__ekle(g, im->ctx.b, "\n");
    guv__hex(g->acilis, 16, t);
    guv__ekle(g, im->ctx.b, t);
    guv__ekle(g, im->ctx.b, "\n");
    guv__dec(sayac, t);
    guv__ekle(g, im->ctx.b, t);
    guv__ekle(g, im->ctx.b, "\n");
    guv__hex(govde_ozet, 32, t);
    guv__ekle(g, im->ctx.b, t);
    /* kriptografi hatasi: mac guvenilmez (yigindaki eski deger) — RED */
    if (g->k->hmac_bit(im->ctx.b, mac)) return GUV_E_IMZA;
    if (!imza_hex || guv__hexten(imza_hex, gel, 32)) return GUV_E_IMZA;
    if (!guv__esit(mac, gel, 32)) return GUV_E_IMZA;
    /* ancak imza dogruysa pencere (sahte sayac ilerletemez) */
    cv = &g->c[im->n - 1u];
    if (!sayac) return GUV_E_TEKRAR;
    if (sayac > cv->son_sayac) {
        uint64_t d = sayac - cv->son_sayac;
        cv->pencere = (d >= GUV_PENCERE) ? 1u : ((cv->pencere << d) | 1u);
        cv->son_sayac = sayac;
    } else {
        uint64_t d = cv->son_sayac - sayac;
        uint64_t bit;
        if (d >= GUV_PENCERE) return GUV_E_TEKRAR;
        bit = (uint64_t)1u << d;
        if (cv->pencere & bit) return GUV_E_TEKRAR;
        cv->pencere |= bit;
    }
    if (unix && unix - cv->son_yazim >= GUV_SON_YAZ_S) {
        GuvCihaz c;
        if (!guv_cihaz_oku(g, im->n, &c)) {
            c.son = unix;
            (void)guv__cihaz_yaz(g, im->n, &c);
            memset(&c, 0, sizeof(c));
        }
        cv->son_yazim = unix;
    }
    return 0;
}

/* zorunlu / misafir: -1 = degistirme; tur: 0 = degistirme. Ayar bozuksa once
   kimlik/tuz YENIDEN uretilir (eski kimlik bilinemez). */
GUV_ISLEV int guv_ayar_yaz(GuvDurum *g, int zorunlu, int misafir, uint32_t tur)
{
    if (g->ayar_bozuk) {
        const uint8_t z = g->ayar.zorunlu;
        guv__ayar_uret(g);
        g->ayar.zorunlu = z;
        g->ayar_bozuk = 0;
        guv_parola_degisti(g);
    }
    if (zorunlu >= 0) g->ayar.zorunlu = (uint8_t)(zorunlu ? 1u : 0u);
    if (misafir >= 0) g->ayar.misafir = (uint8_t)(misafir ? 1u : 0u);
    if (tur && tur != g->ayar.tur) {
        g->ayar.tur = tur;
        guv_parola_degisti(g);
    }
    return guv__ayar_yaz(g);
}

GUV_ISLEV void guv_acilis_hex(const GuvDurum *g, char h[33]) { guv__hex(g->acilis, 16, h); }
GUV_ISLEV void guv_kimlik_hex(const GuvDurum *g, char h[17]) { guv__hex(g->ayar.kimlik, 8, h); }
GUV_ISLEV void guv_tuz_hex(const GuvDurum *g, char h[33]) { guv__hex(g->ayar.tuz, 16, h); }
GUV_ISLEV uint8_t guv_cihaz_var(const GuvDurum *g, uint8_t n)
{
    return (uint8_t)(n && n <= GUV_CIHAZ_AZAMI && g->c[n - 1u].var);
}

#ifdef GUV_SINAMA
/* YALNIZ AVR sinamasi: vektorler sabit kimlik/tuz/acilis/bekleyen ister */
GUV_ISLEV void guv__sinama_ayar(GuvDurum *g, const uint8_t kimlik[8], const uint8_t tuz[16],
                                uint32_t tur)
{
    memcpy(g->ayar.kimlik, kimlik, 8);
    memcpy(g->ayar.tuz, tuz, 16);
    g->ayar.tur = tur;
    guv_parola_degisti(g);
    (void)guv__ayar_yaz(g);
}

GUV_ISLEV void guv__sinama_acilis(GuvDurum *g, const uint8_t a[16]) { memcpy(g->acilis, a, 16); }

GUV_ISLEV void guv__sinama_bekleyen(GuvDurum *g, uint8_t eno, const uint8_t nk[16],
                                    const uint8_t nc[16], const char *ad, uint32_t simdi_ms)
{
    g->e_var = 1u;
    g->e_no = eno;
    memcpy(g->e_nk, nk, 16);
    memcpy(g->e_nc, nc, 16);
    memset(g->e_ad, 0, sizeof(g->e_ad));
    strncpy(g->e_ad, ad, GUV_AD_AZAMI);
    g->e_bas_ms = simdi_ms;
}
#endif

#endif /* GUVENLIK_H */
