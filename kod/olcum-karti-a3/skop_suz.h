#ifndef SKOP_SUZ_H
#define SKOP_SUZ_H
/*
 * SK1 (2026-10-10) — OSILOSKOP ON SUZGECI: iki kat medyan-3 + kutu ortalamasi.
 * PLATFORM BAGIMSIZ, yalniz tamsayi. uretim/test_skop_suz.py bu dosyayi avr-gcc ile derleyip
 * AVR emulatorunde kosturur; ESP32'de kosan kod budur.
 *
 * NEDEN (kartta olculdu, 12 yakalamanin ham kodlari, 50 kSa/s):
 *   - Izdeki sivri darbeler HEP tek ornek genisliginde (nadiren 2), 64-138 kod = 1.8-4 V.
 *     Giris RC'si 6.4 kohm x 1 nF (25 kHz): gercek sinyal tek ornekte (12-24 us) bu kadar
 *     sicrayamaz; darbe girisin degil DONUSUM ANININ urunu (B41: I2C kenarlari; kutuda baska
 *     kaynaklar da var). Medyan-3 hepsini sildi (12 yakalamada 0 kaldi), std 13 -> 7 kod.
 *   - Tek bir darbe Vmax'i sisirince skop_olc'un %50 / %10-%90 esikleri kayiyordu: Arduino'nun
 *     1000 Hz / 5 V karesinde frekans 20 yakalamanin yalniz 11'inde %1 icindeydi, Vpp 9.2 V
 *     (gercek 5 V), yukselme 373 us (gercek < 20 us).
 *   - Yavas zaman tabaninda ADC de yavas ornekliyordu: her nokta TEK ham okuma.
 *
 * NE YAPAR: ADC her zaman ust hiza yakin kosar (skop_suz_plan: hz_adc ~ k x hz_cikis).
 * Her ham ornek once art arda IKI KEZ uc ornegin ortancasina (medyan) girer — tek ornek darbe ve
 * kisa igne patlamalari silinir, basamak ve iki ornekli darbe AYNEN gecer (iki ornek gecikir). Sonra k ortanca
 * toplanip yuvarlanarak TEK cikis ornegi olur (k = 1'de yalniz medyan). Halka tampon ve
 * tetik mantigi CIKIS orneklerini gorur; onlara dokunulmaz.
 *
 * NE YAPMAZ: iki ornekten genis hicbir seyi silmez; ust hizda (k = 1) gurultuyu azaltmaz.
 */
#include <stdint.h>

typedef struct {
    uint16_t x1, x2;   /* 1. kat: son iki HAM ornek (x1 en yeni) */
    uint16_t y1, y2;   /* 2. kat: 1. katin son iki ciktisi */
    uint8_t  gecmis;   /* 0..4: iki katin penceresi dolana kadar sayar */
    uint16_t say;      /* kutuda biriken ortanca sayisi */
    uint16_t k;        /* kac ortanca bir cikis ornegi eder (>= 1) */
    uint32_t top;      /* kutudaki ortancalarin toplami: <= 65535 x 65535 < 2^32 */
} SkopSuz;

/* HIZ PLANI. ESP32-S3'un surekli ADC'si ornekleme hizini TAMSAYI aralikla kurar:
 * hiz = saat / N (saat = 2.5 MHz: APB 80 MHz / 16 / 2; surucu N = saat / istenen, asagi yuvarlar).
 * "Cikis hizinin k kati" diye rastgele bir hiz istenirse gercek hiz %3'e kadar sapar ve zaman
 * ekseni (frekans olcumu) o kadar kayar. Bu yuzden plan N'yi kendisi secer ve GERCEK cikis
 * hizini dondurur; yakalama basligina o yazilir.
 *   T = saat / hz_nominal (yuvarlanmis)   bir cikis ornegine dusen saat adimi
 *   k = T / N_ASGARI (>= 1)               ADC ust hizi asmadan en buyuk seyreltme
 *   N = T / k (yuvarlanmis, >= N_ASGARI)  ADC araligi: N_ASGARI .. 2 N_ASGARI - 1
 *   hz_adc = saat / N,  hz_gercek = saat / (N k)  — nominalden en cok 1 / (2 N_ASGARI) sapar. */
typedef struct {
    uint16_t k;          /* seyreltme orani (>= 1) */
    uint16_t n;          /* ADC araligi (saat adimi) */
    uint32_t hz_adc;     /* surucuden istenecek hiz */
    uint32_t hz_gercek;  /* cikis orneklerinin gercek hizi (en yakin Hz) */
} SkopSuzPlan;

static SkopSuzPlan skop_suz_plan(uint32_t hz_nominal, uint32_t saat_hz, uint16_t n_asgari)
{
    SkopSuzPlan p;
    uint32_t t, k, n, payda;
    if (hz_nominal == 0u) hz_nominal = 1u;
    if (n_asgari == 0u) n_asgari = 1u;
    t = (saat_hz + hz_nominal / 2u) / hz_nominal;
    if (t < n_asgari) t = n_asgari;
    k = t / n_asgari;
    if (k > 65535u) k = 65535u;
    n = (t + k / 2u) / k;
    if (n < n_asgari) n = n_asgari;
    if (n > 65535u) n = 65535u;
    payda = n * k;
    p.k = (uint16_t)k;
    p.n = (uint16_t)n;
    p.hz_adc = saat_hz / n;
    p.hz_gercek = (saat_hz + payda / 2u) / payda;
    return p;
}

static void skop_suz_kur(SkopSuz *s, uint16_t k)
{
    s->x1 = s->x2 = 0u;
    s->y1 = s->y2 = 0u;
    s->gecmis = 0u;
    s->say = 0u;
    s->k = (k > 0u) ? k : 1u;
    s->top = 0u;
}

/* Uc sayinin ortancasi: max(min(a,b), min(max(a,b), c)). */
static uint16_t skop_suz_ortanca(uint16_t a, uint16_t b, uint16_t c)
{
    const uint16_t kucuk = (a < b) ? a : b;
    const uint16_t buyuk = (a < b) ? b : a;
    const uint16_t orta  = (buyuk < c) ? buyuk : c;
    return (kucuk > orta) ? kucuk : orta;
}

/* Bir HAM ornek verir. Cikis ornegi hazirsa 1 doner ve *cikis'e yazar; degilse 0.
 * Ilk DORT ham ornek yalniz iki medyan penceresini doldurur (cikis yok).
 *
 * NEDEN IKI KAT: kartta igneler 2-3 orneklik patlamalar halinde geliyor (28/1000 ornek; araliklarin
 * cogu 1 ve 2). Tek kat medyan-3 "igne, normal, igne" dizisinde ortadaki pencereden (igne, normal,
 * igne) IGNEYI cikarir: 1000 Hz karede 2.4/1000 igne kaliyordu. Ikinci kat onu da siler. Gercek
 * sinyalde kayip yok: basamak ve iki ornekli darbe medyan-3'un KOKUDUR (degismeden gecer), ikinci
 * gecis de onlari degistirmez. Medyan-5 ise iki ornekli darbeyi (83 kSa/s'te 20 kHz kare) silerdi. */
static uint8_t skop_suz_besle(SkopSuz *s, uint16_t ham, uint16_t *cikis)
{
    uint16_t m1, m2;
    if (s->gecmis < 2u) {                       /* 1. katin penceresi doluyor */
        s->x2 = s->x1;
        s->x1 = ham;
        s->gecmis++;
        return 0u;
    }
    m1 = skop_suz_ortanca(s->x2, s->x1, ham);
    s->x2 = s->x1;
    s->x1 = ham;
    if (s->gecmis < 4u) {                       /* 2. katin penceresi doluyor */
        s->y2 = s->y1;
        s->y1 = m1;
        s->gecmis++;
        return 0u;
    }
    m2 = skop_suz_ortanca(s->y2, s->y1, m1);
    s->y2 = s->y1;
    s->y1 = m1;
    s->top += m2;
    if (++s->say < s->k) return 0u;
    *cikis = (uint16_t)((s->top + (uint32_t)(s->k / 2u)) / (uint32_t)s->k);   /* yarim YUKARI */
    s->top = 0u;
    s->say = 0u;
    return 1u;
}

#endif /* SKOP_SUZ_H */
