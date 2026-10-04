/*
 * AGD — ag_karar.h'nin AVR uzerinde kosturulmasi (sim3_web.py 5m).
 *
 * Kartin "ev agi yoksa AP + yeniden dene, donunce AP'yi kapat" karari
 * `agk_kur` + `agk_adim`'dan ibaret; ikisi de platformsuz. Burada kosan kod
 * kartta kosanin TA KENDISI (ayni baslik). Sureler (AG_STA_BEKLE_MS ...)
 * derleyiciye -D ile `ag.h`'den okunarak veriliyor — tek kaynak.
 *
 * Senaryolar `ag_vektor.h`'de (sim3_web.py uretir): her biri 100 ms adimla
 * `son` ms'ye dek kosar. bagli = iki pencereden birinde; iliskili = bagli
 * ya da ayri "yalniz iliski" penceresinde (DHCP bekleniyor).
 * kimlik: 1 = ev agi kayitli, 0 = kayitli degil, 2 = agk_kur HIC cagrilmadi
 * (sifir ilklenmis durum: WiFi N0).
 *
 * Cikti:  A <i> <ms> <eylem>       eylem != AGE_YOK olan her adim (ms: goreli)
 *         S <i> <evre> <etkin>     senaryo sonu
 */
#include <avr/io.h>
#include <stdint.h>

#include "ag_karar.h"
#include "ag_vektor.h"

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

static void sayi(uint32_t v)
{
    char b[11];
    uint8_t n = 0;
    do { b[n++] = (char)('0' + (uint8_t)(v % 10u)); v /= 10u; } while (v);
    while (n) yaz(b[--n]);
}

static uint8_t icinde(uint32_t t, uint32_t bas, uint32_t bit) { return t >= bas && t < bit; }

int main(void)
{
    uart_baslat();
    for (uint8_t i = 0; i < SEN_ADET; i++) {
        const Senaryo *s = &SEN[i];
        AgKarar k = {0, AGK_YOK};
        if (s->kimlik != 2u) agk_kur(&k, s->kimlik, s->t0);
        for (uint32_t r = 0; r <= s->son; r += 100u) {
            const uint8_t bagli = icinde(r, s->b1, s->b1s) || icinde(r, s->b2, s->b2s);
            const uint8_t ilis = bagli || icinde(r, s->il, s->ils);
            const uint8_t e = agk_adim(&k, s->t0 + r, bagli, ilis);
            if (e != AGE_YOK) {
                metin("A "); sayi(i); metin(" "); sayi(r); metin(" "); sayi(e); metin("\r\n");
            }
        }
        metin("S "); sayi(i); metin(" "); sayi(k.evre); metin(" "); sayi(agk_etkin(&k)); metin("\r\n");
    }
    metin("BITTI\r\n");
    for (;;) {}
}
