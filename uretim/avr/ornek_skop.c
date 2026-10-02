/*
 * Osiloskop OLCUM matematiginin AVR uzerinde kosturulmasi.
 *
 * NEDEN AVR: ESP32-S3'u komut komut calistiran bir emulatorumuz yok, ama
 * AVR'yi calistiran ve 39/39 bit birebir dogrulanmis bir emulatorumuz var
 * (test_avr.py). olcum2.h hicbir platform cagrisi icermedigi ve her yerde
 * acik genislikli tip + float kullandigi icin iki mimaride de AYNI
 * IEEE-754 sonucu verir. Burada kosturulan skop_olc(), ESP32'de kosacak
 * fonksiyonun ta kendisidir.
 *
 * NEDEN SENTETIK DALGA: burada ngspice'e gerek yok. Uc dalganin frekansi,
 * genligi ve duty'si ANALITIK OLARAK BILINIYOR; test bunlara karsi
 * dogruluyor. Yani beklenen degerler bir yeniden-uygulamadan degil,
 * matematigin kendisinden geliyor.
 *
 *   kare     : periyot 80 ornek, 5 tam cevrim, %50 duty
 *   ucgen    : periyot 100 ornek, 4 tam cevrim, %50 duty
 *   sinus    : periyot 64 ornek, 6 tam cevrim, %50 duty
 *
 * Ornekleme hizi 10 000 Sa/s kabul ediliyor, yani:
 *   kare  -> 125.00 Hz     ucgen -> 100.00 Hz     sinus -> 156.25 Hz
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#include "olcum2.h"

#define ADET 400u
#define FS   10000.0f

static uint16_t tampon[ADET];

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

/* Bir SkopOlcum yapisini tek satirda basar. Python tarafi bit desenini
 * cozup analitik beklenen degerle karsilastirir. */
static void olcum_yaz(const char *ad, const SkopOlcum *o, uint16_t n)
{
    metin(ad);            yaz(' ');
    metin("f ");   hexf(o->frekans);   yaz(' ');
    metin("T ");   hexf(o->periyot);   yaz(' ');
    metin("pp ");  hexf(o->vpp);       yaz(' ');
    metin("mx ");  hexf(o->vmax);      yaz(' ');
    metin("mn ");  hexf(o->vmin);      yaz(' ');
    metin("av ");  hexf(o->vort);      yaz(' ');
    metin("rm ");  hexf(o->vrms);      yaz(' ');
    metin("ac ");  hexf(o->vac);       yaz(' ');
    metin("du ");  hexf(o->duty);      yaz(' ');
    metin("tr ");  hexf(o->t_yuksel);  yaz(' ');
    metin("tf ");  hexf(o->t_dus);     yaz(' ');
    {
        char t[8];
        metin("cv ");  utoa(o->cevrim, t, 10);  metin(t);  yaz(' ');
        metin("n ");   utoa(n, t, 10);          metin(t);
    }
    yaz('\n');
}

int main(void)
{
    uart_baslat();

    float va = SKOP_VOLT_ADIM;
    SkopOlcum o;
    uint16_t i;

    metin("VA ");  hexf(va);  yaz('\n');

    /* olcum2.h'nin DC olcum tarafi bu kosumda kullanilmiyor; static
     * fonksiyonlar "tanimli ama kullanilmamis" uyarisi uretmesin diye
     * birer kez cagriliyor. Boylece "0 uyari" kosulu anlamli kaliyor. */
    {
        Ayar2 a;
        Okuma2 r;
        varsayilan_ayar2(&a);
        r = olc2(1000, 100, &a);
        metin("DC ");  hexf(enerji_wh(3600000000000000ull));  yaz(' ');
        hexf(enerji_joule(enerji_ekle(0ull, r.watt, 1000u)));  yaz(' ');
        hexf(tam_olcek_volt(PGA_2048));  yaz(' ');
        hexf(adim_volt(PGA_2048));  yaz(' ');
        hexf(pga_sec(1.0f));  yaz(' ');
        hexf(r.volt);  yaz(' ');
        hexf(ads_volt(1000, PGA_2048));  yaz(' ');
        hexf(olc_gerilim(1000, &a));  yaz(' ');
        hexf(olc_akim(100, &a));  yaz('\n');
    }

    /* --- 1. KARE: periyot 80, 5 cevrim, alt 200 / ust 3800 ------------ */
    for (i = 0; i < 400u; i++)
        tampon[i] = ((i % 80u) < 40u) ? 3800u : 200u;
    skop_olc(tampon, 400u, va, FS, &o);
    olcum_yaz("KARE", &o, 400u);

    /* --- 2. UCGEN: periyot 100, 4 cevrim, 200..3800 ------------------- */
    for (i = 0; i < 400u; i++) {
        uint16_t f = i % 100u;
        uint16_t y = (f < 50u) ? f : (100u - f);      /* 0..50..0 */
        tampon[i] = (uint16_t)(200u + (uint32_t)y * 3600u / 50u);
    }
    skop_olc(tampon, 400u, va, FS, &o);
    olcum_yaz("UCGN", &o, 400u);

    /* --- 3. SINUS: periyot 64, 6 cevrim (384 ornek), 2048 +- 1500 ----- */
    for (i = 0; i < 384u; i++) {
        float a = 6.283185307f * (float)i / 64.0f;
        tampon[i] = (uint16_t)(2048.0f + 1500.0f * sinf(a) + 0.5f);
    }
    skop_olc(tampon, 384u, va, FS, &o);
    olcum_yaz("SINS", &o, 384u);

    /* --- 4. DUZ CIZGI: olcum yapilamamali, hepsi sifir kalmali -------- */
    for (i = 0; i < 400u; i++) tampon[i] = 2048u;
    skop_olc(tampon, 400u, va, FS, &o);
    olcum_yaz("DUZ ", &o, 400u);

    /* --- 5. ASIMETRIK KARE: %25 duty, periyot 80 --------------------- */
    for (i = 0; i < 400u; i++)
        tampon[i] = ((i % 80u) < 20u) ? 3800u : 200u;
    skop_olc(tampon, 400u, va, FS, &o);
    olcum_yaz("D25 ", &o, 400u);

    /* --- 6. 1F (S1): YUKSEK DUZ CIZGI 4000 kod -> Vac TAM 0 ---------- */
    for (i = 0; i < 400u; i++) tampon[i] = 4000u;
    skop_olc(tampon, 400u, va, FS, &o);
    olcum_yaz("DZ40", &o, 400u);

    /* 3332 kod: S2 = 400·3332² float32'ye TAM sigmiyor — Vrms'i S2/n'den
     * kuran yol bu va ile Vort'tan 1 ulp ayrilir (3000..4095 arasinda 154
     * deger boyle); ozdeslik yolu (√(ort² + ac²)) TAM Vort. */
    for (i = 0; i < 400u; i++) tampon[i] = 3332u;
    skop_olc(tampon, 400u, va, FS, &o);
    olcum_yaz("DZ33", &o, 400u);

    /* --- 7. 1F (S1): 3000 kod DC + {-3..+3} kod "gurultu" ------------
     * 2997 + (5i mod 7): 57 tam devir (399 ornek), her deger esit sayida.
     * Ortalama TAM 3000, varyans TAM (9+4+1+0+1+4+9)/7 = 4 kod^2
     * -> Vac TAM 2 kod. Eski float32 kare farki bunu kaybediyordu. */
    for (i = 0; i < 399u; i++)
        tampon[i] = (uint16_t)(2997u + (5u * i) % 7u);
    skop_olc(tampon, 399u, va, FS, &o);
    olcum_yaz("GRT ", &o, 399u);

    /* --- 8. 1F (S4): CUCE DARBELER + tam kenarlar ---------------------
     * 200/3800 -> alt (%10) 560, ust (%90) 3440 (float32'de tam).
     *  40-49   yukari cuce: 200..1500..200 (%10'u gecer, %90'a VARMAZ)
     *  80-89   tam yukselen rampa 200+360j: 560 @80, 3440 @88 -> tr 8 ornek
     * 150-159  asagi cuce: 3800..2500..3800 (%90'i gecer, %10'a VARMAZ)
     * 200-209  tam dusen rampa 3800-360j: 3440 @200, 560 @208 -> tf 8 ornek
     * Cuceler orta-hist'e (1550) / ortaya (2000) degmez: kenar sayilmaz. */
    for (i = 0; i < 400u; i++) {
        uint16_t y = 200u;
        if (i >= 40u && i < 45u)       y = (uint16_t)(200u + 260u * (i - 39u));
        else if (i >= 45u && i < 50u)  y = (uint16_t)(1500u - 260u * (i - 44u));
        else if (i >= 80u && i < 90u)  y = (uint16_t)(200u + 360u * (i - 79u));
        else if (i >= 90u && i < 150u) y = 3800u;
        else if (i >= 150u && i < 155u) y = (uint16_t)(3800u - 260u * (i - 149u));
        else if (i >= 155u && i < 160u) y = (uint16_t)(2500u + 260u * (i - 154u));
        else if (i >= 160u && i < 200u) y = 3800u;
        else if (i >= 200u && i < 210u) y = (uint16_t)(3800u - 360u * (i - 199u));
        tampon[i] = y;
    }
    skop_olc(tampon, 400u, va, FS, &o);
    olcum_yaz("CUCE", &o, 400u);

    metin("BITTI\n");
    for (;;) {}
}
