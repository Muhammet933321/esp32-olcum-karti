/*
 * PT (2026-10-07) — PIL TESTI DURUM MAKINESI (pil_test.h pil_adim) AVR'de.
 * sim3_pil.py bolum 7 derler (avr-g++ -Wall -Wextra), kosturur, satirlari okur.
 * Beklenen degerler ANALITIK (sim3_pil.py'de); burada yalniz kartin kodu kosar.
 *
 * Zaman yalniz harness ile ilerler (deterministik): baslama 1000 ms, adim
 * `adim_ms` (dt_us = adim_ms x 1000). Kesme 3.000 V, azami sure 0 (S5 haric),
 * halka araligi 1000 ms.
 *
 * PILA_BITTI / PILA_SURE'de durum .ino'daki gibi degisir (durdur), yani
 * eylem bir kez sayilmali.
 *
 * Cikti (sayilar ondalik; gerilim/direnc x10000, i32):
 *   S1 <bitti_say> <dip_say> <ilk_dip_ms> <durum> <ema_x1e4> <v_min_x1e4>
 *        gurultulu V, ortalama 3.10 (kesmenin 0.10 ustu), dipler 2.85 (0.15 alti), 20 s yuk
 *   S2 <bitti_ms> <basamak_ms> <ema_x1e4> <durum> <v_son_x1e4>
 *        ortalama 10 s sonra 3.10 -> 2.95 (ayni gurultu)
 *   S3a <ms> <ocv> <durum>                 OCV evresinde ornek (her 1000 ms'de bir)
 *   S3 <yuk_ac_ms> <yuk_ac_say> <yuk_pC_ac> <halka_adet_ac> <bitti_ms> <bitti_say>
 *        <ocv_evresi_bitti_ms>              OCV'de V 2.0 (kesmenin ALTI) ve I 0.8 A; yukte V 2.9
 *   S3b <once> <sonra> <evre>          p0 OCV evresinde: once 1, sonra 0 (evre hala OCV=1)
 *   S4 <acik> <dcir_bas_say> <dcir_bitti_say> <ilk_bas_ms> <dcir_n> <r_ani_x1e4>
 *        <r_otr_x1e4> <bitti_say> <ema_x1e4> <v_ani_x1e4>
 *   S5 <sure_ms> <sure_say>                 azami 7 s: (ms - bas) / 1000 > 7
 *   S6 <hz> <nokta_ms> <halka_ms>           pil_nokta_ms / pil_halka_ms (hz x100)
 *   S7 <i> <sonuc> <hz>                     pil_pr_ayir vektorleri
 *   S8 <i> <sonuc>                          pil_pd_ayir vektorleri
 *   S9 <hz> <izinli>                        pil_hz_izinli 0..60
 *   BITTI
 */
#include <avr/io.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

#include "pil_test.h"

/* ── UART ──────────────────────────────────────────────────────────── */
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
static void isayi(int32_t v)
{
    if (v < 0) { yaz('-'); sayi((uint32_t)(-v)); } else sayi((uint32_t)v);
}
static void ara() { yaz(' '); }
static int32_t x1e4(float v) { return (int32_t)lroundf(v * 10000.0f); }

/* ── ortak ─────────────────────────────────────────────────────────── */
#define BAS_MS 1000UL
static PilNokta halka_t[16];
static PilHalka halka;
static PilTest p;
static PilParam a;

static void kur(uint8_t dcir_acik, uint32_t azami_s)
{
    halka.nokta = halka_t;
    halka.kapasite = 16u;
    pil_halka_sifirla(&halka);
    a.kesme_v = 3.0f;
    a.azami_s = azami_s;
    a.halka_ms = 1000u;
    pil_baslat_kur(&p, BAS_MS, 4.1f, dcir_acik);
}

/* .ino pil_durdur'un durum kismi (yuk kesme, kayit, bildirim .ino'da) */
static void durdur(uint8_t d)
{
    p.durum = d;
    p.dcir_icinde = 0u;
}

/* gurultu: periyot 4, ortalama 0, en dip -0.25 */
static float gurultu(uint32_t k)
{
    static const float d[4] = {0.10f, -0.25f, 0.10f, 0.05f};
    return d[k & 3u];
}

/* OCV evresini 4.1 V ile gecir; donus: yukun acildigi ms */
static uint32_t ocv_gec(uint32_t adim_ms)
{
    uint32_t ms = BAS_MS, n;
    for (n = 0; n < 20000u; n++) {        /* sinirli: OCV evresi hic yoksa da ilerler */
        ms += adim_ms;
        if (pil_adim(&p, &halka, &a, ms, 4.1f, 0.0f, 0.0f, adim_ms * 1000UL) & PILA_YUK_AC)
            return ms;
    }
    return ms;
}

static void s1(void)
{
    uint32_t ms, son, k = 0, bitti = 0, dip = 0, ilk_dip = 0;
    float vmin = 99.0f;
    kur(0u, 0u);
    ms = ocv_gec(10u);
    son = ms + 20000UL;
    while (ms < son) {
        ms += 10u;
        const float v = 3.10f + gurultu(k++);
        if (v < vmin) vmin = v;
        if (pil_kesmeli_mi(v, a.kesme_v)) { dip++; if (!ilk_dip) ilk_dip = ms; }
        if (pil_adim(&p, &halka, &a, ms, v, 0.8f, v * 0.8f, 10000UL) & PILA_BITTI) {
            bitti++;
            durdur(PIL_BITTI);
        }
    }
    metin("S1 "); sayi(bitti); ara(); sayi(dip); ara(); sayi(ilk_dip); ara(); sayi(p.durum);
    ara(); isayi(x1e4(p.v_ema)); ara(); isayi(x1e4(vmin)); yaz('\n');
}

static void s2(void)
{
    uint32_t ms, basamak, son, k = 0, bitti_ms = 0;
    float v = 0.0f;
    kur(0u, 0u);
    ms = ocv_gec(10u);
    basamak = ms + 10000UL;
    son = ms + 30000UL;
    while (ms < son) {
        ms += 10u;
        v = (ms <= basamak ? 3.10f : 2.95f) + gurultu(k++);
        if (pil_adim(&p, &halka, &a, ms, v, 0.8f, v * 0.8f, 10000UL) & PILA_BITTI) {
            bitti_ms = ms;
            durdur(PIL_BITTI);
            break;
        }
    }
    metin("S2 "); sayi(bitti_ms); ara(); sayi(basamak); ara(); isayi(x1e4(p.v_ema));
    ara(); sayi(p.durum); ara(); isayi(x1e4(p.v_son)); yaz('\n');
}

static void s3(void)
{
    uint32_t ms = BAS_MS, yuk_ac = 0, yuk_say = 0, bitti = 0, bitti_say = 0, ocv_son = 0;
    int32_t pc_ac = -1;
    uint32_t halka_ac = 0;
    kur(0u, 0u);
    while (ms < BAS_MS + 10000UL) {
        ms += 10u;
        const uint8_t ocv = pil_ocv_evresinde(&p);
        const float v = ocv ? 2.0f : 2.9f;      /* OCV'de kesmenin ALTI: yine de kesmez */
        const float i = ocv ? 0.8f : 1.0f;      /* OCV'de akim olsa da mAh BIRIKMEZ */
        if (ocv) ocv_son = ms;
        if (ocv && (ms % 1000u) == 0u) {
            metin("S3a "); sayi(ms); ara(); sayi(ocv); ara(); sayi(p.durum); yaz('\n');
        }
        const uint8_t e = pil_adim(&p, &halka, &a, ms, v, i, v * i, 10000UL);
        if (e & PILA_YUK_AC) {
            yuk_say++;
            if (!yuk_ac) { yuk_ac = ms; pc_ac = (int32_t)p.yuk_pC; halka_ac = halka.adet; }
        }
        if (e & PILA_BITTI) { bitti_say++; if (!bitti) bitti = ms; durdur(PIL_BITTI); }
    }
    metin("S3 "); sayi(yuk_ac); ara(); sayi(yuk_say); ara(); isayi(pc_ac); ara(); sayi(halka_ac);
    ara(); sayi(bitti); ara(); sayi(bitti_say); ara(); sayi(ocv_son); yaz('\n');
}

/* p0 OCV evresinde: durum DURDURULDU, evre OCV kalir — KN_OCV / evre=ocv SONA ERMELI */
static void s3b(void)
{
    uint32_t ms = BAS_MS;
    uint8_t once;
    kur(0u, 0u);
    while (ms < BAS_MS + 1000UL) {
        ms += 10u;
        (void)pil_adim(&p, &halka, &a, ms, 4.1f, 0.0f, 0.0f, 10000UL);
    }
    once = pil_ocv_evresinde(&p);
    durdur(PIL_DURDURULDU);
    metin("S3b "); sayi(once); ara(); sayi(pil_ocv_evresinde(&p)); ara(); sayi(p.evre);
    yaz('\n');
}

static void s4(uint8_t acik)
{
    uint32_t ms, son, bas_say = 0, bitti_say = 0, ilk_bas = 0, kes = 0;
    uint8_t darbe = 0;
    kur(acik, 0u);
    ms = ocv_gec(100u);
    son = ms + 650000UL;
    while (ms < son) {
        ms += 100u;
        const float v = darbe ? 4.0f : 3.6f;    /* darbede yuk kapali: OCV'ye siçrar */
        const float i = darbe ? 0.0f : 1.0f;
        const uint8_t e = pil_adim(&p, &halka, &a, ms, v, i, v * i, 100000UL);
        if (e & PILA_DCIR_BAS) { bas_say++; darbe = 1u; if (!ilk_bas) ilk_bas = ms; }
        if (e & PILA_DCIR_BITTI) { bitti_say++; darbe = 0u; }
        if (e & PILA_BITTI) { kes++; durdur(PIL_BITTI); }
    }
    metin("S4 "); sayi(acik); ara(); sayi(bas_say); ara(); sayi(bitti_say); ara();
    sayi(ilk_bas ? ilk_bas - p.yuk_bas_ms : 0u); ara(); sayi(p.dcir_sayisi); ara();
    isayi(x1e4(p.dcir_ani)); ara(); isayi(x1e4(p.dcir_oturmus)); ara(); sayi(kes); ara();
    isayi(x1e4(p.v_ema)); ara(); isayi(x1e4(p.dcir_v_ani)); yaz('\n');
}

static void s5(void)
{
    uint32_t ms = BAS_MS, sure = 0, say = 0;
    kur(0u, 7u);
    while (ms < BAS_MS + 12000UL) {
        ms += 100u;
        if (pil_adim(&p, &halka, &a, ms, 3.6f, 1.0f, 3.6f, 100000UL) & PILA_SURE) {
            say++;
            if (!sure) sure = ms - BAS_MS;
            durdur(PIL_HATA);
        }
    }
    metin("S5 "); sayi(sure); ara(); sayi(say); yaz('\n');
}

static void s6(void)
{
    static const float hz[] = {0.0f, 1.0f, 5.0f, 20.0f, 50.0f, 0.2f, 0.001f, 1000.0f, -1.0f};
    uint8_t j;
    for (j = 0; j < (uint8_t)(sizeof(hz) / sizeof(hz[0])); j++) {
        metin("S6 "); isayi(x1e4(hz[j]) / 100); ara(); sayi(pil_nokta_ms(hz[j])); ara();
        sayi(pil_halka_ms(hz[j])); yaz('\n');
    }
    metin("S6n "); sayi(pil_nokta_ms(NAN)); ara(); sayi(pil_halka_ms(NAN)); yaz('\n');
}

static void s7(void)
{
    static const char *const v[] = {"0", "1", "5", "20", "50", "2", "10", "100", "", "-1",
                                    " 5", "5x", "05", "00", "0050", "4294967297", "20 "};
    uint8_t j;
    for (j = 0; j < (uint8_t)(sizeof(v) / sizeof(v[0])); j++) {
        uint32_t hz = 999u;
        const uint8_t r = pil_pr_ayir(v[j], &hz);
        metin("S7 "); sayi(j); ara(); sayi(r); ara(); sayi(hz); yaz('\n');
    }
}

static void s8(void)
{
    static const char *const v[] = {"0", "1", "", "2", "01", "1 ", "a"};
    uint8_t j;
    for (j = 0; j < (uint8_t)(sizeof(v) / sizeof(v[0])); j++) {
        metin("S8 "); sayi(j); ara(); sayi(pil_pd_ayir(v[j])); yaz('\n');
    }
}

static void s9(void)
{
    uint32_t h;
    metin("S9");
    for (h = 0; h <= 60u; h++) if (pil_hz_izinli(h)) { ara(); sayi(h); }
    yaz('\n');
}

int main(void)
{
    uart_baslat();
    s1();
    s2();
    s3();
    s3b();
    s4(0u);
    s4(1u);
    s5();
    s6();
    s7();
    s8();
    s9();
    metin("BITTI\n");
    for (;;) {}
}
