/* ═══════════════════════════════════════════════════════════════════════
   ag_liste.h — KAYITLI WiFi AGLARI + ADAY SECIMI (platformsuz)  (2026-10-06)

   Kullanici: "Karti birden fazla ag hatirlayacak sekilde yapamaz miyiz? 4-5 belki
   daha fazla" + "ev agina baglandi, hotspotu actim, panelden hotspota gecsin".
   Tasarim: tasarim/2026-10-06-coklu-ag.md (CA1-CA13).

   Burada YALNIZ karar: liste islemleri (ekle/guncelle/sil, sinirlar) ve "hangi aga
   baglanilsin". NVS / WiFi surucusu ag.h'de (yapistirici). Parola bu yapida YOK —
   karar parolaya bakmaz; parola NVS'te kalir, yalniz begin() aninda okunur (CA9).
   AVR'de kosuyor: uretim/avr/ornek_ag_liste.c (sim3_web.py 5n). Yalniz <stdint.h>
   ve <string.h>.

   SECIM (CA3): kayitli VE taramada gorunen aglar; once oncelikliler, her grupta guclu
   RSSI once; ayni adli birden cok erisim noktasi -> en gucluu. DONUS (CA4): bir aday
   baglanamazsa sonraki denemede listede ONDAN SONRAKI aday (dongusel) — yanlis
   parolali oncelikli ag karti sonsuza dek kilitlemez, uc aday da sirayla denenir.
   ═══════════════════════════════════════════════════════════════════════ */
#ifndef AG_LISTE_H
#define AG_LISTE_H
#include <stdint.h>
#include <string.h>

#define AGL_AZAMI 8u                 /* CA1 */
#define AGL_AD    33u                /* 32 bayt SSID + NUL */

typedef struct {
    char    ad[AGL_AD];
    uint8_t dolu;                    /* 1: yuva kullanimda */
    uint8_t oncelik;                 /* 1: gorunuyorsa sinyale bakmadan once */
} AglKayit;

typedef struct {
    char   ad[AGL_AD];
    int8_t rssi;                     /* dBm (negatif; buyuk = guclu) */
} AglGorunen;

/* CA13: ad 1..32 bayt */
static uint8_t agl_ad_gecerli(const char *ad)
{
    const size_t n = ad ? strlen(ad) : 0u;
    return n >= 1u && n <= AGL_AD - 1u;
}

/* CA13: parola bos (acik ag) ya da 8..63 karakter (WPA2) */
static uint8_t agl_parola_gecerli(const char *p)
{
    const size_t n = p ? strlen(p) : 0u;
    return n == 0u || (n >= 8u && n <= 63u);
}

static uint8_t agl_adet(const AglKayit k[AGL_AZAMI])
{
    uint8_t n = 0;
    for (uint8_t i = 0; i < AGL_AZAMI; i++) n = (uint8_t)(n + (k[i].dolu ? 1u : 0u));
    return n;
}

/* adi birebir (buyuk/kucuk harf, bosluk) esleyen dolu yuva; yoksa -1 */
static int8_t agl_bul(const AglKayit k[AGL_AZAMI], const char *ad)
{
    if (!ad) return -1;
    for (uint8_t i = 0; i < AGL_AZAMI; i++)
        if (k[i].dolu && strcmp(k[i].ad, ad) == 0) return (int8_t)i;
    return -1;
}

/* ekleme yeri: ayni adli kayit (guncelleme) ya da ilk bos yuva; dolu + yeni ad -> -1 */
static int8_t agl_yer(const AglKayit k[AGL_AZAMI], const char *ad)
{
    const int8_t v = agl_bul(k, ad);
    if (v >= 0) return v;
    for (uint8_t i = 0; i < AGL_AZAMI; i++)
        if (!k[i].dolu) return (int8_t)i;
    return -1;
}

/* yuvayi doldur (oncelik korunur: guncellemede kullanicinin tercihi silinmesin) */
static int8_t agl_ekle(AglKayit k[AGL_AZAMI], const char *ad)
{
    if (!agl_ad_gecerli(ad)) return -1;
    const int8_t i = agl_yer(k, ad);
    if (i < 0) return -1;
    if (!k[i].dolu) {
        memset(&k[i], 0, sizeof(k[i]));
        strncpy(k[i].ad, ad, AGL_AD - 1u);
        k[i].dolu = 1u;
    }
    return i;
}

static uint8_t agl_sil(AglKayit k[AGL_AZAMI], int8_t i)
{
    if (i < 0 || (uint8_t)i >= AGL_AZAMI || !k[i].dolu) return 0;
    memset(&k[i], 0, sizeof(k[i]));
    return 1;
}

/* taramada bu adin en guclu RSSI'si; gorunmuyorsa 0 doner ve *rssi'ye dokunmaz */
static uint8_t agl_gorunur(const AglGorunen g[], uint8_t gn, const char *ad, int8_t *rssi)
{
    uint8_t var = 0;
    int8_t en = -128;
    for (uint8_t j = 0; j < gn; j++)
        if (strcmp(g[j].ad, ad) == 0 && (!var || g[j].rssi > en)) { en = g[j].rssi; var = 1; }
    if (var && rssi) *rssi = en;
    return var;
}

/* CA3: adaylar (kayit indeksleri) sirali; donus aday sayisi */
static uint8_t agl_adaylar(const AglKayit k[AGL_AZAMI], const AglGorunen g[], uint8_t gn,
                           uint8_t cikti[AGL_AZAMI])
{
    int8_t r[AGL_AZAMI];
    uint8_t n = 0;
    for (uint8_t i = 0; i < AGL_AZAMI; i++) {
        int8_t x;
        if (k[i].dolu && agl_gorunur(g, gn, k[i].ad, &x)) { cikti[n] = i; r[n] = x; n++; }
    }
    /* kararli ekleme siralamasi: oncelik azalan, sonra RSSI azalan, esitlikte yuva sirasi */
    for (uint8_t a = 1; a < n; a++) {
        const uint8_t ci = cikti[a];
        const int8_t cr = r[a];
        int8_t b = (int8_t)a - 1;
        while (b >= 0 && (k[cikti[b]].oncelik < k[ci].oncelik
                          || (k[cikti[b]].oncelik == k[ci].oncelik && r[b] < cr))) {
            cikti[b + 1] = cikti[b];
            r[b + 1] = r[b];
            b--;
        }
        cikti[b + 1] = ci;
        r[b + 1] = cr;
    }
    return n;
}

/* CA4: denenecek kayit. `son_basarisiz` (onceki denemede baglanamayan, yoksa -1) aday
   listesindeyse ONDAN SONRAKI (dongusel); degilse ilk aday. Aday yoksa -1. */
static int8_t agl_sec(const AglKayit k[AGL_AZAMI], const AglGorunen g[], uint8_t gn, int8_t son_basarisiz)
{
    uint8_t c[AGL_AZAMI];
    const uint8_t n = agl_adaylar(k, g, gn, c);
    if (!n) return -1;
    for (uint8_t p = 0; p < n; p++)
        if ((int8_t)c[p] == son_basarisiz) return (int8_t)c[(uint8_t)(p + 1u) % n];
    return (int8_t)c[0];
}

/* Taramasiz ilk tahmin (setup: radyo ACILIRKEN tarama yok — 1E-2): en son baglanilan
   kayit; yoksa ilk oncelikli; yoksa ilk dolu; liste bossa -1. */
static int8_t agl_ilk(const AglKayit k[AGL_AZAMI], int8_t son_iyi)
{
    if (son_iyi >= 0 && (uint8_t)son_iyi < AGL_AZAMI && k[son_iyi].dolu) return son_iyi;
    for (uint8_t i = 0; i < AGL_AZAMI; i++)
        if (k[i].dolu && k[i].oncelik) return (int8_t)i;
    for (uint8_t i = 0; i < AGL_AZAMI; i++)
        if (k[i].dolu) return (int8_t)i;
    return -1;
}

#endif /* AG_LISTE_H */
