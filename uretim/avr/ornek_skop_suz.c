/*
 * Osiloskop ON SUZGECININ (skop_suz.h: medyan-3 + kutu ortalamasi) AVR uzerinde kosturulmasi.
 *
 * NEDEN AVR: ornek_skop.c ile ayni — ESP32'de kosacak fonksiyonun TA KENDISI, bit birebir
 * dogrulanmis emulatorde. skop_suz.h yalniz tamsayi kullanir, platform cagrisi yoktur.
 *
 * Girdiler burada URETILIR, Python tarafi AYNI kuralla yeniden uretip beklenen ciktiyi
 * analitik olarak (ve bagimsiz bir basvuru uygulamasiyla) hesaplar.
 */
#include <avr/io.h>
#include <stdint.h>
#include <stdlib.h>

#include "skop_suz.h"

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

static void metin(const char *s) { while (*s) yaz(*s++); }

static void hex16(uint16_t v)
{
    const char *h = "0123456789abcdef";
    yaz(h[(v >> 12) & 15]);
    yaz(h[(v >> 8) & 15]);
    yaz(h[(v >> 4) & 15]);
    yaz(h[v & 15]);
}

static void sayi(uint32_t v)
{
    char t[12];
    ultoa(v, t, 10);
    metin(t);
}

/* Girdi kurallari — test_skop_suz.py'deki `girdi()` ile BIREBIR ayni. */
static uint32_t lcg = 12345u;
static uint16_t girdi(uint8_t durum, uint16_t i)
{
    switch (durum) {
    case 0:  /* IGNE: taban 1000; tek +igne (10), bir atlayarak iki +igne (20, 22), tek -igne (37),
                yan yana zit iki igne (45 +, 46 -), IKI ornekli DARBE (60, 61 — gercek sinyal olabilir) */
        if (i == 10u || i == 20u || i == 22u || i == 45u) return 3000u;
        if (i == 37u || i == 46u) return 0u;
        if (i == 60u || i == 61u) return 3000u;
        return 1000u;
    case 1:  /* BASAMAK: 500 -> 3500, 30. ornekte */
        return (i < 30u) ? 500u : 3500u;
    case 2:  /* ORT4: rampa */
        return (uint16_t)(100u + 3u * i);
    case 3:  /* DC */
        return 2047u;
    case 4:  /* YUVARLA: 1000 / 1001 almasik */
        return (uint16_t)(1000u + (i & 1u));
    default: /* GURULTU: 2000 +- 64 (LCG) + her 97 ornekte bir tek ornek igne */
        lcg = lcg * 1103515245u + 12345u;
        {
            uint16_t v = (uint16_t)(2000u + ((lcg >> 16) & 127u) - 64u);
            if (i % 97u == 50u) v = (uint16_t)(v + 1500u);
            return v;
        }
    }
}

static void kos(const char *ad, uint8_t durum, uint16_t k, uint16_t adet)
{
    SkopSuz s;
    uint16_t i, c, cikan = 0;
    skop_suz_kur(&s, k);
    metin(ad);
    for (i = 0; i < adet; i++) {
        if (skop_suz_besle(&s, girdi(durum, i), &c)) {
            yaz(' ');
            hex16(c);
            cikan++;
        }
    }
    metin(" n ");
    sayi(cikan);
    yaz('\n');
}

int main(void)
{
    static const uint32_t hizlar[] = { 611u, 1000u, 2000u, 5000u, 10000u, 20000u, 26316u, 50000u, 83333u, 100000u, 0u };
    uint8_t j;
    uart_baslat();

    for (j = 0; j < sizeof(hizlar) / sizeof(hizlar[0]); j++) {
        const SkopSuzPlan p = skop_suz_plan(hizlar[j], 2500000u, 30u);
        metin("PLAN ");
        sayi(hizlar[j]);   yaz(' ');
        sayi(p.k);         yaz(' ');
        sayi(p.n);         yaz(' ');
        sayi(p.hz_adc);    yaz(' ');
        sayi(p.hz_gercek);
        yaz('\n');
    }
    kos("IGNE", 0, 1u, 80u);
    kos("BASAMAK", 1, 1u, 60u);
    kos("ORT4", 2, 4u, 42u);
    kos("DC", 3, 7u, 72u);
    kos("YUVARLA", 4, 2u, 42u);
    kos("GURULTU", 5, 16u, 962u);
    kos("SIFIRK", 3, 0u, 12u);      /* k = 0 verilirse 1 sayilir (0'a bolme yok) */

    metin("BITTI\n");
    for (;;) {}
}
