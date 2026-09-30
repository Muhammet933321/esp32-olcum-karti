#ifndef KAYIT_HALKA_H
#define KAYIT_HALKA_H
/*
 * 1C-2 — ORNEK HALKASI: cekirdek 1 (loop, olcum_al) -> cekirdek 0 (kayit
 * gorevi), ayrintili kipte her ornek. Kilitsiz TEK uretici / TEK tuketici,
 * platformsuz: AVR emulatorunde sinaniyor (uretim/test_kayit.py B71.H).
 *
 *   * `yaz`'i yalniz uretici, `oku`'yu yalniz tuketici yazar; serbest akan 32
 *     bit sayaclar, fark = doluluk (sarmada da dogru). Kapasite 2'nin kuvveti.
 *   * Dolu halkada ornek DUSER, sayilir (`dusen`) ve bir SONRAKI itilen ornege
 *     KO_KAYIP_ONCE konur: yazici yeni kayit acar, kaydi KA_KAYIP_ONCE ile
 *     isaretler. Sessiz birlesme yok (spec O1).
 *   * FreeRTOS kuyrugu ornek basina kilit + kopya demekti; 500/s'de gereksiz.
 */
#include <stdint.h>

#ifndef KAYIT_BARIYER
#define KAYIT_BARIYER() __sync_synchronize()   /* ESP32: memw */
#endif

#define KO_KAYIP_ONCE 0x10u    /* yalniz bellekte: bundan ONCE ornek dustu */

typedef struct {
    uint32_t us, ms;           /* micros() ve millis() — ayni zamanlayici */
    int16_t  v, i;             /* ham ADS kodlari */
    uint8_t  bayrak;           /* KAO_* (alt 4 bit) + KO_KAYIP_ONCE */
} KayitOrnek;

typedef struct {
    KayitOrnek *tampon;
    uint32_t    kapasite;      /* 2'nin kuvveti */
    volatile uint32_t yaz, oku, dusen;
    volatile uint8_t  kayip;
} KayitHalka;

static inline void kh_kur(KayitHalka *h, KayitOrnek *t, uint32_t kapasite)
{
    h->tampon = t;
    h->kapasite = kapasite;
    h->yaz = 0u;
    h->oku = 0u;
    h->dusen = 0u;
    h->kayip = 0u;
}

static inline uint32_t kh_adet(const KayitHalka *h)
{
    return h->yaz - h->oku;
}

/* Uretici. Donus: 1 itildi, 0 halka dolu (ornek DUSTU, sayildi). */
static inline uint8_t kh_it(KayitHalka *h, const KayitOrnek *o)
{
    uint32_t y = h->yaz;
    KayitOrnek *e;
    if (!h->tampon || y - h->oku >= h->kapasite) {
        h->dusen = h->dusen + 1u;
        h->kayip = 1u;
        return 0u;
    }
    e = &h->tampon[y & (h->kapasite - 1u)];
    *e = *o;
    if (h->kayip) {
        e->bayrak = (uint8_t)(e->bayrak | KO_KAYIP_ONCE);
        h->kayip = 0u;
    }
    KAYIT_BARIYER();           /* ornek YAZILDI, sonra sayac */
    h->yaz = y + 1u;
    return 1u;
}

/* Tuketici. Donus: 1 alindi, 0 bos. */
static inline uint8_t kh_al(KayitHalka *h, KayitOrnek *o)
{
    uint32_t r = h->oku;
    if (r == h->yaz) return 0u;
    KAYIT_BARIYER();           /* sayaci gordukten sonra ornegi oku */
    *o = h->tampon[r & (h->kapasite - 1u)];
    KAYIT_BARIYER();
    h->oku = r + 1u;
    return 1u;
}

#endif /* KAYIT_HALKA_H */
