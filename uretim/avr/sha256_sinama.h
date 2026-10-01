/* sha256_sinama.h — YALNIZ SINAMA: FIPS 180-4 SHA-256 + RFC 2104 HMAC +
 * PBKDF2-HMAC-SHA256 (tek blok, 32 B).
 *
 * Kartta mbedTLS (donanim SHA) kullanilir; bu dosya guvenlik.h'yi AVR
 * emulatorunde sinamak icin. Dogrulugu RFC 4231 ve RFC 7914 vektorleriyle
 * olculur (test_kayit.py B71.U1/U2) — kendi sonucunu dogrulamaz.
 * Sabitler PROGMEM'de (ATmega328p'nin 2 KB RAM'i). Imzalar GuvKripto ile ayni. */
#ifndef SHA256_SINAMA_H
#define SHA256_SINAMA_H

#include <stdint.h>
#include <string.h>
#include <avr/pgmspace.h>

typedef struct {
    uint32_t h[8];
    uint32_t uz;              /* bayt (sinama iletileri kucuk) */
    uint8_t  tampon[64];
    uint8_t  n;
} SsSha;

typedef struct {
    SsSha   ic;
    uint8_t dis[64];
} SsHmac;

static const uint32_t SS_K[64] PROGMEM = {
    0x428a2f98UL, 0x71374491UL, 0xb5c0fbcfUL, 0xe9b5dba5UL, 0x3956c25bUL, 0x59f111f1UL,
    0x923f82a4UL, 0xab1c5ed5UL, 0xd807aa98UL, 0x12835b01UL, 0x243185beUL, 0x550c7dc3UL,
    0x72be5d74UL, 0x80deb1feUL, 0x9bdc06a7UL, 0xc19bf174UL, 0xe49b69c1UL, 0xefbe4786UL,
    0x0fc19dc6UL, 0x240ca1ccUL, 0x2de92c6fUL, 0x4a7484aaUL, 0x5cb0a9dcUL, 0x76f988daUL,
    0x983e5152UL, 0xa831c66dUL, 0xb00327c8UL, 0xbf597fc7UL, 0xc6e00bf3UL, 0xd5a79147UL,
    0x06ca6351UL, 0x14292967UL, 0x27b70a85UL, 0x2e1b2138UL, 0x4d2c6dfcUL, 0x53380d13UL,
    0x650a7354UL, 0x766a0abbUL, 0x81c2c92eUL, 0x92722c85UL, 0xa2bfe8a1UL, 0xa81a664bUL,
    0xc24b8b70UL, 0xc76c51a3UL, 0xd192e819UL, 0xd6990624UL, 0xf40e3585UL, 0x106aa070UL,
    0x19a4c116UL, 0x1e376c08UL, 0x2748774cUL, 0x34b0bcb5UL, 0x391c0cb3UL, 0x4ed8aa4aUL,
    0x5b9cca4fUL, 0x682e6ff3UL, 0x748f82eeUL, 0x78a5636fUL, 0x84c87814UL, 0x8cc70208UL,
    0x90befffaUL, 0xa4506cebUL, 0xbef9a3f7UL, 0xc67178f2UL
};

#define SS_ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

__attribute__((noinline)) static void ss__blok(SsSha *s, const uint8_t *b)
{
    uint32_t w[16], a, bb, c, d, e, f, g, h, t1, t2, wi;
    uint8_t i;
    for (i = 0; i < 16; i++)
        w[i] = ((uint32_t)b[4 * i] << 24) | ((uint32_t)b[4 * i + 1] << 16)
             | ((uint32_t)b[4 * i + 2] << 8) | (uint32_t)b[4 * i + 3];
    a = s->h[0]; bb = s->h[1]; c = s->h[2]; d = s->h[3];
    e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (i = 0; i < 64; i++) {
        if (i < 16) {
            wi = w[i];
        } else {
            uint32_t w15 = w[(i - 15) & 15], w2 = w[(i - 2) & 15];
            uint32_t s0 = SS_ROTR(w15, 7) ^ SS_ROTR(w15, 18) ^ (w15 >> 3);
            uint32_t s1 = SS_ROTR(w2, 17) ^ SS_ROTR(w2, 19) ^ (w2 >> 10);
            wi = w[i & 15] = w[i & 15] + s0 + w[(i - 7) & 15] + s1;   /* w[i&15] = w[i-16] */
        }
        t1 = h + (SS_ROTR(e, 6) ^ SS_ROTR(e, 11) ^ SS_ROTR(e, 25)) + ((e & f) ^ (~e & g))
           + pgm_read_dword(&SS_K[i]) + wi;
        t2 = (SS_ROTR(a, 2) ^ SS_ROTR(a, 13) ^ SS_ROTR(a, 22)) + ((a & bb) ^ (a & c) ^ (bb & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = bb; bb = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += bb; s->h[2] += c; s->h[3] += d;
    s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}

__attribute__((noinline)) static int ss_sha_bas(void *ctx)
{
    static const uint32_t ilk[8] PROGMEM = {
        0x6a09e667UL, 0xbb67ae85UL, 0x3c6ef372UL, 0xa54ff53aUL,
        0x510e527fUL, 0x9b05688cUL, 0x1f83d9abUL, 0x5be0cd19UL };
    SsSha *s = (SsSha *)ctx;
    uint8_t i;
    for (i = 0; i < 8; i++) s->h[i] = pgm_read_dword(&ilk[i]);
    s->uz = 0;
    s->n = 0;
    return 0;
}

__attribute__((noinline)) static void ss_sha_ekle(void *ctx, const void *v, uint16_t n)
{
    SsSha *s = (SsSha *)ctx;
    const uint8_t *p = (const uint8_t *)v;
    while (n--) {
        s->tampon[s->n++] = *p++;
        s->uz++;
        if (s->n == 64u) { ss__blok(s, s->tampon); s->n = 0; }
    }
}

__attribute__((noinline)) static int ss_sha_bit(void *ctx, uint8_t c[32])
{
    SsSha *s = (SsSha *)ctx;
    uint32_t bit = s->uz << 3;
    uint8_t i;
    s->tampon[s->n++] = 0x80u;
    if (s->n > 56u) {
        while (s->n < 64u) s->tampon[s->n++] = 0;
        ss__blok(s, s->tampon);
        s->n = 0;
    }
    while (s->n < 56u) s->tampon[s->n++] = 0;
    s->tampon[56] = 0; s->tampon[57] = 0; s->tampon[58] = 0;
    s->tampon[59] = (uint8_t)(s->uz >> 29);
    s->tampon[60] = (uint8_t)(bit >> 24); s->tampon[61] = (uint8_t)(bit >> 16);
    s->tampon[62] = (uint8_t)(bit >> 8);  s->tampon[63] = (uint8_t)bit;
    ss__blok(s, s->tampon);
    for (i = 0; i < 8; i++) {
        c[4 * i] = (uint8_t)(s->h[i] >> 24); c[4 * i + 1] = (uint8_t)(s->h[i] >> 16);
        c[4 * i + 2] = (uint8_t)(s->h[i] >> 8); c[4 * i + 3] = (uint8_t)s->h[i];
    }
    return 0;
}

/* guv_pbkdf2'nin ipad/opad durum kopyasi: hedef kaynagin durumunu alir (yigin yok, duz kopya) */
__attribute__((noinline)) static int ss_sha_kopya(void *hedef, const void *kaynak)
{
    memcpy(hedef, kaynak, sizeof(SsSha));
    return 0;
}

__attribute__((noinline)) static int ss_hmac_bas(void *ctx, const uint8_t *anahtar, uint16_t n)
{
    SsHmac *m = (SsHmac *)ctx;
    uint8_t k0[64], i;
    memset(k0, 0, sizeof(k0));
    if (n > 64u) {
        ss_sha_bas(&m->ic);
        ss_sha_ekle(&m->ic, anahtar, n);
        ss_sha_bit(&m->ic, k0);
    } else {
        memcpy(k0, anahtar, n);
    }
    for (i = 0; i < 64u; i++) {
        m->dis[i] = (uint8_t)(k0[i] ^ 0x5cu);
        k0[i] ^= 0x36u;
    }
    ss_sha_bas(&m->ic);
    ss_sha_ekle(&m->ic, k0, 64);
    memset(k0, 0, sizeof(k0));
    return 0;
}

__attribute__((noinline)) static void ss_hmac_ekle(void *ctx, const void *v, uint16_t n)
{
    ss_sha_ekle(&((SsHmac *)ctx)->ic, v, n);
}

__attribute__((noinline)) static int ss_hmac_bit(void *ctx, uint8_t c[32])
{
    SsHmac *m = (SsHmac *)ctx;
    uint8_t ic[32];
    ss_sha_bit(&m->ic, ic);
    ss_sha_bas(&m->ic);
    ss_sha_ekle(&m->ic, m->dis, 64);
    ss_sha_ekle(&m->ic, ic, 32);
    return ss_sha_bit(&m->ic, c);
}

/* PBKDF2-HMAC-SHA256, tek blok (dkLen 32). 0 = tamam. */
__attribute__((noinline)) static int ss_pbkdf2(const char *parola, const uint8_t *tuz, uint16_t tn, uint32_t tur,
                     uint8_t c[32])
{
    static const uint8_t bir[4] = {0, 0, 0, 1};
    SsHmac m;
    uint8_t u[32];
    uint16_t pn = (uint16_t)strlen(parola);
    uint32_t t;
    uint8_t i;
    ss_hmac_bas(&m, (const uint8_t *)parola, pn);
    ss_hmac_ekle(&m, tuz, tn);
    ss_hmac_ekle(&m, bir, 4);
    ss_hmac_bit(&m, u);
    memcpy(c, u, 32);
    for (t = 1; t < tur; t++) {
        ss_hmac_bas(&m, (const uint8_t *)parola, pn);
        ss_hmac_ekle(&m, u, 32);
        ss_hmac_bit(&m, u);
        for (i = 0; i < 32u; i++) c[i] ^= u[i];
    }
    return 0;
}

#endif /* SHA256_SINAMA_H */
