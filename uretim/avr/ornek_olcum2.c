/*
 * Asama 2 donusum katinin AVR uzerinde kosturulmasi.
 *
 * NEDEN AVR: ESP32-S3'u komut komut calistiran bir emulatorumuz yok, ama
 * AVR'yi calistiran ve 39/39 bit birebir dogrulanmis bir emulatorumuz var
 * (test_avr.py). olcum2.h hicbir platform cagrisi icermedigi ve her yerde
 * acik genislikli tip + float kullandigi icin iki mimaride de AYNI
 * IEEE-754 sonucu verir. Burada kosturulan kod, ESP32'de kosacak kodun
 * ta kendisidir.
 *
 * vektor.h Python tarafindan uretilir: ngspice'in verdigi dugum
 * gerilimlerinden veri sayfasi denklemiyle cikarilan ADS1115 ham kodlari.
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#include "olcum2.h"
#include "vektor.h"      /* VEKTOR[] ve VEKTOR_ADET — Python uretir */

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

static void hex8(uint8_t v)
{
    const char *h = "0123456789abcdef";
    yaz(h[v >> 4]);
    yaz(h[v & 15]);
}

static void hexf(float f)
{
    uint8_t b[4];
    memcpy(b, &f, 4);
    for (int8_t i = 3; i >= 0; i--) hex8(b[i]);
}

static void hex64(uint64_t v)
{
    for (int8_t i = 7; i >= 0; i--) hex8((uint8_t)(v >> (i * 8)));
}

static void ondalik(float v, uint8_t basamak)
{
    char t[20];
    dtostrf(v, 1, basamak, t);
    /* dtostrf basa bosluk koyabilir; atla */
    char *p = t;
    while (*p == ' ') p++;
    metin(p);
}

int main(void)
{
    uart_baslat();

    Ayar2 ayar;
    varsayilan_ayar2(&ayar);

    /* --- 1. HAM DONUSUMLER: her vektorun bit deseni basilir.
     *     Python tarafi ayni hesabi numpy.float32 ile yapip
     *     BIT BIREBIR karsilastirir. */
    uint64_t enerji = 0;
    uint32_t ornek = 0;
    float v_top = 0.0f, i_top = 0.0f, w_top = 0.0f;

    for (uint16_t k = 0; k < VEKTOR_ADET; k++) {
        ayar.sont_ohm = VEKTOR[k].sont;
        ayar.v_pga = VEKTOR[k].v_pga;
        ayar.i_pga = VEKTOR[k].i_pga;
        ayar.i_ofset = VEKTOR[k].i_ofset;

        Okuma2 o = olc2(VEKTOR[k].ham_v, VEKTOR[k].ham_i, &ayar);

        metin("V ");   hexf(o.volt);   yaz(' ');
        metin("I ");   hexf(o.amper);  yaz(' ');
        metin("W ");   hexf(o.watt);   yaz('\n');

        enerji = enerji_ekle(enerji, o.watt, VEKTOR[k].dt_us);
        v_top += o.volt;
        i_top += o.amper;
        w_top += o.watt;
        ornek++;
    }

    /* --- 2. ENERJI: tam sayi birikim */
    metin("E ");  hex64(enerji);  yaz(' ');
    metin("J ");  hexf(enerji_joule(enerji));  yaz(' ');
    metin("H ");  hexf(enerji_wh(enerji));     yaz('\n');

    /* --- 3. PGA otomatik kademe secimi */
    {
        static const float DUGUM[] = {2.00f, 1.00f, 0.40f, 0.20f, 0.05f};
        metin("P");
        for (uint8_t k = 0; k < 5; k++) { yaz(' '); hexf(pga_sec(DUGUM[k])); }
        yaz('\n');
    }

    /* --- 4. TAM OLCEK ve ADIM: kademe basina, girise vurulmus */
    {
        static const float KADEME[] = {PGA_2048, PGA_1024, PGA_0512, PGA_0256};
        metin("F");
        for (uint8_t k = 0; k < 4; k++) { yaz(' '); hexf(tam_olcek_volt(KADEME[k])); }
        yaz('\n');
        metin("A");
        for (uint8_t k = 0; k < 4; k++) { yaz(' '); hexf(adim_volt(KADEME[k])); }
        yaz('\n');
    }

    /* --- 5. SABIT CALISMA NOKTASI -> protokol satirlari
     *
     * Yukaridaki tarama 3.3..30 V arasi gezdigi icin ort(VxI) ile
     * ort(V)xort(I) BILEREK farkli cikar — zaten bu yuzden gucu ornek
     * basina carpiyoruz. Arayuz testi icin sabit bir nokta gerekiyor:
     * asagida ayni kod SABIT_V / SABIT_I ile tekrar kosuyor.
     *
     * Iki satir basiliyor cunku arayuz ornekleme hizini iki raporun
     * zaman damgasi FARKINDAN cikariyor; tek satirla hesaplayamaz.
     */
    {
        Ayar2 s;
        varsayilan_ayar2(&s);
        s.sont_ohm = SABIT_SONT;
        s.v_pga = SABIT_V_PGA;
        s.i_pga = SABIT_I_PGA;

        uint64_t e2 = 0;
        for (uint8_t tur = 0; tur < 2; tur++) {
            float vt = 0, it = 0, wt = 0;
            uint16_t n = 0;
            for (uint16_t k = 0; k < 172; k++) {   /* 200 ms @ 860 SPS */
                Okuma2 o = olc2(SABIT_HAM_V, SABIT_HAM_I, &s);
                e2 = enerji_ekle(e2, o.watt, 1163u);
                vt += o.volt; it += o.amper; wt += o.watt; n++;
            }
            metin("D ");
            ondalik(vt / (float)n, 4);  yaz(' ');
            ondalik(it / (float)n, 6);  yaz(' ');
            ondalik(wt / (float)n, 6);  yaz(' ');
            ondalik(enerji_joule(e2), 4);  yaz(' ');
            ondalik(enerji_wh(e2), 7);     yaz(' ');
            {
                char t[12];
                ultoa(200u * (uint16_t)(tur + 1), t, 10);
                metin(t);  yaz(' ');
                ultoa(n, t, 10);
                metin(t);
            }
            yaz('\n');
        }
    }

    /* olcum2.h'nin OSILOSKOP tarafi bu kosumda kullanilmiyor (onun
     * kendi kosumu var: ornek_skop.c). static fonksiyon "tanimli ama
     * kullanilmamis" uyarisi uretmesin diye bir kez cagriliyor;
     * boylece "0 uyari" kosulu anlamli kaliyor. */
    {
        static uint16_t iki[4] = {100u, 3000u, 100u, 3000u};
        SkopOlcum sm;
        skop_olc(iki, 4u, SKOP_VOLT_ADIM, 1000.0f, &sm);
        metin("S ");  hexf(sm.vpp);  yaz(' ');  hexf(sm.vort);  yaz('\n');
    }

    metin("BITTI\n");
    for (;;) {}
}
