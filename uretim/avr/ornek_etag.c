/*
 * W6 — web_etag.h'nin AVR uzerinde kosturulmasi (sim3_web.py 6q).
 *
 * Kartin ETag/304 karari `etag_bul` + `etag_eslesir`'den ibaret; ikisi de
 * platformsuz. Burada kosan kod kartta kosanin TA KENDISI (ayni baslik).
 *
 * Girdiler `etag_vektor.h`'de: sim3_web.py onu her kosuda URETIYOR —
 * kunye satirlari `arayuz-uret.py`'nin `etag_kunyesi()`'nden (gercek
 * goruntunun ozetleriyle), beklenenler Python tarafinda. Yani uretecin
 * yazdigi bicimi C ayristiricisi okuyor: iki dil, tek bicim.
 *
 * Cikti:  B <i> <1|0> <etag|->      etag_bul(KUNYE, BUL_YOL[i])
 *         E <i> <1|0>               etag_eslesir(ESL_INM[i], ESL_ETAG[i])
 *         N <bul_null> <esl_null>   NULL girdiler (0 beklenir)
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>

#include "web_etag.h"
#include "etag_vektor.h"

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

static void sayi(uint8_t v)
{
    if (v >= 100) yaz((char)('0' + v / 100));
    if (v >= 10) yaz((char)('0' + (v / 10) % 10));
    yaz((char)('0' + v % 10));
}

int main(void)
{
    uart_baslat();
    char e[WEB_ETAG_BOY];

    for (uint8_t i = 0; i < BUL_ADET; i++) {
        memset(e, 0, sizeof(e));
        uint8_t r = etag_bul(KUNYE, BUL_YOL[i], e);
        metin("B "); sayi(i); metin(r ? " 1 " : " 0 ");
        metin(r ? e : "-");
        metin("\r\n");
    }
    for (uint8_t i = 0; i < ESL_ADET; i++) {
        uint8_t r = etag_eslesir(ESL_INM[i], ESL_ETAG[i]);
        metin("E "); sayi(i); metin(r ? " 1\r\n" : " 0\r\n");
    }
    metin("N ");
    sayi(etag_bul((const char *)0, "/app.js", e) + etag_bul(KUNYE, (const char *)0, e));
    metin(" ");
    sayi(etag_eslesir((const char *)0, "\"0123456789abcdef\"")
         + etag_eslesir("*", (const char *)0));
    metin("\r\n");
    metin("BITTI\r\n");
    for (;;) {}
}
