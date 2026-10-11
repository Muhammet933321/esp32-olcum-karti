/*
 * SZ — osiloskop KULLANICI SIFIRI cekirdeginin (skop_sifir.h) kosturulmasi.
 *
 * AYNI kaynak iki yerde derlenir:
 *   - avr-gcc (atmega328p) -> bit birebir dogrulanmis AVR emulatoru (uretim/avr). Girdi programi
 *     Python'un RAM'e yazdigi bayt dizisi (PROGRAM_ADRES, en cok 0xC000'e dek), cikti UART.
 *   - host gcc (-DHOST) -> girdi stdin, cikti stdout.
 * uretim/test_skop_sifir.py iki ciktinin BIT BIT ayni oldugunu ve beklenenleri sinar;
 * uretim/ortak_vektor_skop_sifir.py JS capraz vektorlerini (M komutu) bundan uretir.
 *
 * Program (kucuk-sonlu): komut bayti + alanlar
 *   'B'                         skop_sifir_bas
 *   'E' u16 adet, adet x u16    skop_sifir_ekle          -> "E <0|1>"
 *   'K' f32 mv oran fab kod_v   skop_sifir_karar         -> "K <sebep> <ort> <sac> <kay> <sifir> <yak> <n>"
 *   'O' f32 fab kul             skop_sifir_ofset         -> "O <ofset>"
 *   'V' f32 mv oran fab         skop_sifir_volt          -> "V <volt>"
 *   'G' f32 kul                 skop_sifir_gecerli       -> "G <0|1>"
 *   'F' f32 vmax vmin vort vrms vac ofset  skop_sifir_ofsetle -> "F <vmax> <vmin> <vort> <vrms>"
 *   'S' u8 sebep                skop_sifir_sebep         -> "S <metin>"
 *   'M' u16 adet, f32 adim hz fab kul, adet x u16  skop_olc + skop_sifir_ofsetle(ofset(fab, kul))
 *                                                        -> "M <ofset> <11 alan> <n>"
 *   'Q'                                                   -> "BITTI"
 * Kayan nokta degerleri big-endian hex (bit deseni).
 */
#include <stdint.h>
#include <string.h>
#include <math.h>

#include "skop_olc.h"
#include "skop_sifir.h"

#ifdef HOST
#include <stdio.h>
static void yaz(char c) { putchar(c); }
static uint8_t oku8(void) { int c = getchar(); return (uint8_t)(c < 0 ? 'Q' : c); }
#else
#include <avr/io.h>
#define PROGRAM_ADRES 0x0A00u
static const uint8_t *p_isaret = (const uint8_t *)PROGRAM_ADRES;
static void yaz(char c) { while (!(UCSR0A & (1 << UDRE0))) {} UDR0 = c; }
static uint8_t oku8(void) { return *p_isaret++; }
#endif

static void metin(const char *s) { while (*s) yaz(*s++); }

static uint16_t oku16(void)
{
    uint16_t a = oku8();
    return (uint16_t)(a | ((uint16_t)oku8() << 8));
}

static float okuf(void)
{
    uint8_t b[4];
    float f;
    uint8_t i;
    for (i = 0; i < 4u; i++) b[i] = oku8();
    memcpy(&f, b, 4);
    return f;
}

static void hexf(float f)
{
    const char *h = "0123456789abcdef";
    uint8_t b[4];
    int8_t i;
    memcpy(b, &f, 4);
    yaz(' ');
    for (i = 3; i >= 0; i--) { yaz(h[b[i] >> 4]); yaz(h[b[i] & 15]); }
}

static void sayi(uint32_t v)
{
    char t[12];
    uint8_t n = 0;
    yaz(' ');
    do { t[n++] = (char)('0' + v % 10u); v /= 10u; } while (v);
    while (n) yaz(t[--n]);
}

#define TAMPON 1024u
#ifdef HOST
static uint16_t tampon[TAMPON];
#else
/* 328'in 2 KB'lik ic RAM'ine sigmaz: emulatorun genisletilmis RAM'inde sabit adres
   (derleyici dokunmaz; yigin RAMEND 0x8FF'te, program 0x0A00..0xBFFF) */
#define tampon ((uint16_t *)0xC000u)
#endif

int main(void)
{
    SkopSifir s;
#ifndef HOST
    UBRR0H = 0;
    UBRR0L = 16;
    UCSR0A = (1 << U2X0);
    UCSR0B = (1 << TXEN0);
    UCSR0C = (3 << UCSZ00);
#endif
    skop_sifir_bas(&s);
    for (;;) {
        const uint8_t k = oku8();
        if (k == 'B') {
            skop_sifir_bas(&s);
        } else if (k == 'E') {
            uint16_t adet = oku16(), i;
            for (i = 0; i < adet; i++) {
                uint16_t v = oku16();
                if (i < TAMPON) tampon[i] = v;
            }
            metin("E");
            sayi(skop_sifir_ekle(&s, tampon, adet > TAMPON ? (uint16_t)TAMPON : adet));
            yaz('\n');
        } else if (k == 'K') {
            SkopSifirSonuc r;
            const float mv = okuf(), oran = okuf(), fab = okuf(), kv = okuf();
            const uint8_t e = skop_sifir_karar(&s, mv, oran, fab, kv, &r);
            metin("K");
            sayi(e);
            hexf(r.ort_kod); hexf(r.sacilma_v); hexf(r.kayma_v); hexf(r.sifir_v);
            sayi(s.yakalama);
            sayi(s.n);
            yaz('\n');
        } else if (k == 'O') {
            const float fab = okuf(), kul = okuf();
            metin("O"); hexf(skop_sifir_ofset(fab, kul)); yaz('\n');
        } else if (k == 'V') {
            const float mv = okuf(), oran = okuf(), fab = okuf();
            metin("V"); hexf(skop_sifir_volt(mv, oran, fab)); yaz('\n');
        } else if (k == 'G') {
            const float kul = okuf();
            metin("G"); sayi(skop_sifir_gecerli(kul)); yaz('\n');
        } else if (k == 'F') {
            float mx = okuf(), mn = okuf(), av = okuf(), rm = okuf();
            const float ac = okuf(), of = okuf();
            skop_sifir_ofsetle(&mx, &mn, &av, &rm, ac, of);
            metin("F"); hexf(mx); hexf(mn); hexf(av); hexf(rm); yaz('\n');
        } else if (k == 'S') {
            metin("S ");
            metin(skop_sifir_sebep(oku8()));
            yaz('\n');
        } else if (k == 'M') {
            SkopOlcum m;
            uint16_t adet = oku16(), i;
            const float adim = okuf(), hz = okuf(), fab = okuf(), kul = okuf();
            const float of = skop_sifir_ofset(fab, kul);
            for (i = 0; i < adet; i++) {
                uint16_t v = oku16();
                if (i < TAMPON) tampon[i] = v;
            }
            skop_olc(tampon, adet > TAMPON ? (uint16_t)TAMPON : adet, adim, hz, &m);
            skop_sifir_ofsetle(&m.vmax, &m.vmin, &m.vort, &m.vrms, m.vac, of);
            metin("M");
            hexf(of);
            hexf(m.frekans); hexf(m.periyot); hexf(m.vpp); hexf(m.vmax); hexf(m.vmin);
            hexf(m.vort); hexf(m.vrms); hexf(m.vac); hexf(m.duty); hexf(m.t_yuksel); hexf(m.t_dus);
            sayi(m.cevrim);
            yaz('\n');
        } else {
            metin("BITTI\n");
#ifdef HOST
            return 0;
#else
            for (;;) {}
#endif
        }
    }
}
