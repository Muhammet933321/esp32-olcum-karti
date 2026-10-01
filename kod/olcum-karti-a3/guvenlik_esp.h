/* guvenlik_esp.h — 1D eslestirme + imza: ESP32 YAPISTIRICISI.
 *
 * mbedTLS kriptografisi (donanim SHA, PBKDF2), Preferences NVS (`guv`: ayar,
 * `cihaz`: c1..c8), kilit (web cekirdek 0 + seri cekirdek 1), SNTP saat
 * kaynagi. Mantik guvenlik.h'de (platformsuz, B71.U). Web kapisi, uclar ve
 * seri `E` komutlari .ino'da (sunucu ve Serial aynasi orada).
 * ⚠ Serial KULLANMAZ: cekirdek 0'dan cagrilir ve Serial aynasi makrodan
 *   ONCE dahil edilir (B72.F87). Yanlis eslestirmeler `guv_ret_sayac` ile
 *   cekirdek 1'e bildirilir, o basar.
 * Tasarim: tasarim/2026-10-01-1d-eslestirme.md. */
#ifndef GUVENLIK_ESP_H
#define GUVENLIK_ESP_H

#include <Arduino.h>
#include <Preferences.h>
#include <mbedtls/md.h>
#include <mbedtls/pkcs5.h>
#include <esp_random.h>
#include <esp_sntp.h>
#include <sys/time.h>
#include "guvenlik.h"

/* web ucu siniflari (spec K11) */
#define GUV_ACIK   0u      /* /, /eslestir/..., CORS on ucu */
#define GUV_IZLEME 1u      /* /akis, /pil — zorunlulukta misafir izlemeyle acilabilir */
#define GUV_OKUMA  2u      /* /kayit/..., /kal/liste, /skop.bin */
#define GUV_KOMUT  3u      /* /komut, /kopru — imzasizsa isleyici karar verir */
#define GUV_CIHAZ  4u      /* /cihaz/..., /saat — HER ZAMAN imza */

typedef struct {
    mbedtls_md_context_t md;
} GuvMbedCtx;
static_assert(sizeof(GuvMbedCtx) <= GUV_CTX_BOYU, "mbedTLS baglami GUV_CTX_BOYU'na sigmali");

static void gm__kur(void *ctx, int hmac)
{
    GuvMbedCtx *c = (GuvMbedCtx *)ctx;
    mbedtls_md_init(&c->md);
    (void)mbedtls_md_setup(&c->md, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), hmac);
}

static void gm_hmac_bas(void *ctx, const uint8_t *k, uint16_t n)
{
    gm__kur(ctx, 1);
    (void)mbedtls_md_hmac_starts(&((GuvMbedCtx *)ctx)->md, k, n);
}

static void gm_hmac_ekle(void *ctx, const void *v, uint16_t n)
{
    (void)mbedtls_md_hmac_update(&((GuvMbedCtx *)ctx)->md, (const unsigned char *)v, n);
}

static void gm_hmac_bit(void *ctx, uint8_t c[32])
{
    GuvMbedCtx *m = (GuvMbedCtx *)ctx;
    (void)mbedtls_md_hmac_finish(&m->md, c);
    mbedtls_md_free(&m->md);
}

static void gm_sha_bas(void *ctx)
{
    gm__kur(ctx, 0);
    (void)mbedtls_md_starts(&((GuvMbedCtx *)ctx)->md);
}

static void gm_sha_ekle(void *ctx, const void *v, uint16_t n)
{
    (void)mbedtls_md_update(&((GuvMbedCtx *)ctx)->md, (const unsigned char *)v, n);
}

static void gm_sha_bit(void *ctx, uint8_t c[32])
{
    GuvMbedCtx *m = (GuvMbedCtx *)ctx;
    (void)mbedtls_md_finish(&m->md, c);
    mbedtls_md_free(&m->md);
}

static int gm_pbkdf2(const char *parola, const uint8_t *tuz, uint16_t tn, uint32_t tur,
                     uint8_t c[32])
{
    return mbedtls_pkcs5_pbkdf2_hmac_ext(MBEDTLS_MD_SHA256, (const unsigned char *)parola,
                                         strlen(parola), tuz, tn, tur, 32, c) ? -1 : 0;
}

static void gm_rastgele(uint8_t *h, uint16_t n)
{
    esp_fill_random(h, n);
}

static const GuvKripto guv_kripto = { gm_hmac_bas, gm_hmac_ekle, gm_hmac_bit, gm_sha_bas,
                                      gm_sha_ekle, gm_sha_bit, gm_pbkdf2, gm_rastgele };

/* ── NVS: `guv` ad alani (ayar), `cihaz` ad alani (c1..c8) ── */
static Preferences guv_nvs_ayar;
static Preferences guv_nvs_cihaz;
static uint8_t guv_nvs_acik = 0;

static Preferences &gn__ad_alani(const char *ad)
{
    return strcmp(ad, "ayar") ? guv_nvs_cihaz : guv_nvs_ayar;
}

static int gn_oku(void *b, const char *ad, void *h, uint16_t n)
{
    (void)b;
    if (!guv_nvs_acik) return -1;
    Preferences &p = gn__ad_alani(ad);
    if (p.getBytesLength(ad) != n) return -1;
    return p.getBytes(ad, h, n) == n ? 0 : -1;
}

static int gn_yaz(void *b, const char *ad, const void *k, uint16_t n)
{
    (void)b;
    if (!guv_nvs_acik) return -1;
    return gn__ad_alani(ad).putBytes(ad, k, n) == n ? 0 : -1;
}

static const GuvNvs guv_nvs_tablo = { gn_oku, gn_yaz, nullptr };

/* ── durum ── */
static GuvDurum guv;
static SemaphoreHandle_t guv_mux = nullptr;
static uint8_t guv_hazir = 0;                   /* guv_ac basarili (NVS acik) */
static volatile uint8_t guv_saat_ntp = 0;       /* SNTP en az bir kez esitledi */
static volatile uint8_t guv_saat_kaynak = 0;    /* 0 yok, 1 ntp, 2 cihaz (/saat) */
static volatile uint32_t guv_ret_sayac = 0;     /* yanlis kanit (cekirdek 0 artirir, 1 basar) */
static uint8_t guv_imzali = 0;                  /* cekirdek 0: son istek imzali ve gecerli (cihaz no) */

static inline void guv_kilit(void)
{
    if (guv_mux) xSemaphoreTake(guv_mux, portMAX_DELAY);
}

static inline void guv_birak(void)
{
    if (guv_mux) xSemaphoreGive(guv_mux);
}

static void guv__sntp_cb(struct timeval *tv)
{
    (void)tv;
    guv_saat_ntp = 1u;
    guv_saat_kaynak = 1u;
}

/* setup: NVS hazir olduktan, web sunucusu baslamadan once */
static void guv_esp_ac(void)
{
    guv_mux = xSemaphoreCreateMutex();
    guv_nvs_acik = (guv_nvs_ayar.begin("guv", false) && guv_nvs_cihaz.begin("cihaz", false))
                   ? 1u : 0u;
    guv_hazir = (guv_nvs_acik && guv_ac(&guv, &guv_kripto, &guv_nvs_tablo) == 0) ? 1u : 0u;
    sntp_set_time_sync_notification_cb(guv__sntp_cb);
}

static uint8_t guv_cihaz_adet(void)
{
    uint8_t i, n = 0;
    for (i = 1; i <= GUV_CIHAZ_AZAMI; i++) n = (uint8_t)(n + guv_cihaz_var(&guv, i));
    return n;
}

/* govde ozeti (kilit gerekmez: durum kullanmaz) */
static void guv_esp_sha(const char *v, size_t n, uint8_t c[32])
{
    GuvCtx ctx;
    gm_sha_bas(ctx.b);
    while (n) {
        uint16_t p = (uint16_t)(n > 4096u ? 4096u : n);
        gm_sha_ekle(ctx.b, v, p);
        v += p;
        n -= p;
    }
    gm_sha_bit(ctx.b, c);
}

#endif /* GUVENLIK_ESP_H */
