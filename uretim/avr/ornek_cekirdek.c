/*
 * Cekirdek dogrulama programi — SIMULATORU sinar, firmware'i degil.
 *
 * Her satir: <etiket> <onaltilik sonuc>
 * Beklenen degerler Python tarafinda IEEE-754 ile bagimsiz hesaplanip
 * BIT BIREBIR karsilastirilir. Yazilim float kutuphanesi (avr-libc) komut
 * kumesinin buyuk bolumunu zorlar: kaydirma, dondurme, elde ile toplama,
 * carpma, isaretli karsilastirma, cok sozcuklu dallanma.
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

static void uart_baslat(void)
{
    UBRR0H = 0;
    UBRR0L = 16;
    UCSR0A = (1 << U2X0);
    UCSR0B = (1 << TXEN0);
    UCSR0C = (3 << UCSZ00);
}

static void yaz(char c)
{
    while (!(UCSR0A & (1 << UDRE0))) {}
    UDR0 = c;
}

static void metin(const char *s)
{
    while (*s) yaz(*s++);
}

static void hex8(uint8_t v)
{
    const char *h = "0123456789abcdef";
    yaz(h[v >> 4]);
    yaz(h[v & 15]);
}

static void hex16(uint16_t v) { hex8(v >> 8); hex8(v & 0xFF); }
static void hex32(uint32_t v) { hex16(v >> 16); hex16(v & 0xFFFF); }

static void hex64(uint64_t v)
{
    for (int8_t i = 7; i >= 0; i--) hex8((uint8_t)(v >> (i * 8)));
}

static void hexf(float f)
{
    uint32_t b;
    memcpy(&b, &f, 4);
    hex32(b);
}

static void satir(const char *ad) { metin(ad); yaz(' '); }
static void bitir(void) { yaz('\n'); }

/* derleyici sabit katlamasin diye degiskenler volatile */
volatile uint8_t  u8a = 200, u8b = 100;
volatile int8_t   i8a = -128, i8b = 3;
volatile uint16_t u16a = 50000, u16b = 40000;
volatile int16_t  i16a = -30000, i16b = 12345;
volatile uint32_t u32a = 3000000000UL, u32b = 1500000000UL;
volatile int32_t  i32a = -2000000000L, i32b = 7;
volatile uint64_t u64a = 1234567890123456789ULL;
volatile float    fa = 3.14159265f, fb = -2.718281828f, fc = 1e-7f;
volatile float    fd = 12345.678f;

int main(void)
{
    uart_baslat();

    /* --- tam sayi aritmetigi: tasma, isaret, bolme, mod */
    satir("u8add");   hex8((uint8_t)(u8a + u8b));                bitir();
    satir("u8sub");   hex8((uint8_t)(u8b - u8a));                bitir();
    satir("u8mul");   hex16((uint16_t)u8a * (uint16_t)u8b);      bitir();
    satir("i8neg");   hex8((uint8_t)(-i8a));                     bitir();
    satir("i8div");   hex8((uint8_t)(i8a / i8b));                bitir();
    satir("i8mod");   hex8((uint8_t)(i8a % i8b));                bitir();
    satir("u16add");  hex16((uint16_t)(u16a + u16b));            bitir();
    satir("u16mul");  hex32((uint32_t)u16a * (uint32_t)u16b);    bitir();
    satir("i16mul");  hex32((uint32_t)((int32_t)i16a * i16b));   bitir();
    satir("i16shr");  hex16((uint16_t)(i16a >> 3));              bitir();
    satir("u32add");  hex32(u32a + u32b);                        bitir();
    satir("u32mul");  hex32(u32a * u32b);                        bitir();
    satir("u32div");  hex32(u32a / 7u);                          bitir();
    satir("i32div");  hex32((uint32_t)(i32a / i32b));            bitir();
    satir("i32mod");  hex32((uint32_t)(i32a % i32b));            bitir();
    satir("u32shl");  hex32(u32b << 3);                          bitir();

    /* --- 64 bit: enerji sayacinin tam olarak yaptigi is */
    satir("u64mul");  hex64((uint64_t)u32a * (uint64_t)u32b);    bitir();
    satir("u64add");  hex64(u64a + (uint64_t)u32a * 220ULL);     bitir();
    satir("u64div");  hex64(u64a / 1000000ULL);                  bitir();

    /* --- IEEE-754 tek duyarlik (yazilim kutuphanesi) */
    satir("fadd");    hexf(fa + fb);                             bitir();
    satir("fsub");    hexf(fa - fb);                             bitir();
    satir("fmul");    hexf(fa * fb);                             bitir();
    satir("fdiv");    hexf(fa / fb);                             bitir();
    satir("fdivs");   hexf(fc / 3.0f);                           bitir();
    satir("fsqrt");   hexf(sqrtf(fd));                           bitir();
    satir("fi2f");    hexf((float)u32a);                         bitir();
    satir("ff2i");    hex32((uint32_t)fd);                       bitir();
    satir("fneg");    hexf(-fa * fc);                            bitir();
    satir("fcmp");    hex8(fa > fb ? 1 : 0);                     bitir();

    /* --- karti ilgilendiren gercek zincir: ADC adimi -> volt -> watt */
    {
        volatile float lsb = 2.470f / 1024.0f;
        volatile float v_adim = lsb * 11.0f;
        volatile float i_adim = lsb / 7.9118f / 10.0f;
        volatile int ham_v = 512, ham_i = 300;
        float volt = ham_v * v_adim;
        float amper = ham_i * i_adim;
        float watt = volt * amper;
        satir("v_adim"); hexf(v_adim);                           bitir();
        satir("i_adim"); hexf(i_adim);                           bitir();
        satir("volt");   hexf(volt);                             bitir();
        satir("amper");  hexf(amper);                            bitir();
        satir("watt");   hexf(watt);                             bitir();
        satir("guc_uW"); hex32((uint32_t)(watt * 1e6f));         bitir();
    }

    /* --- metin donusumleri: komut ayristirma ve rapor bicimi */
    {
        char t[16];
        volatile float d = atof("12.345");
        satir("atof");  hexf(d);                                 bitir();
        satir("atol");  hex32((uint32_t)atol("500"));            bitir();
        dtostrf(3.14159f, 8, 4, t);
        satir("dtostrf"); metin(t);                              bitir();
        ltoa(-123456L, t, 10);
        satir("ltoa");  metin(t);                                bitir();
    }

    metin("BITTI\n");
    for (;;) {}
}
