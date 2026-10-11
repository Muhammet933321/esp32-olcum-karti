#ifndef SKOP_SIFIR_H
#define SKOP_SIFIR_H
/*
 * SZ (2026-10-11, A3-SK3) — OSILOSKOP KANALININ KULLANICI SIFIRI (`tz` / `tz0` / `tz?`).
 * PLATFORM BAGIMSIZ: karar ve hesap burada, .ino yalniz yapistirir (yakalama, NVS, cikti).
 * uretim/test_skop_sifir.py bu dosyayi avr-gcc ile derleyip AVR emulatorunde VE host gcc ile
 * kosturur (iki cikti bit bit ayni olmali); ortak/test/vektor/skop_sifir.json'u
 * uretim/ortak_vektor_skop_sifir.py uretir, ortak/src/skop.js onu Object.is ile tutturur.
 *
 * NEDEN (kartta olculdu, tasarim/1-acik-isler.md SK-8): SKOP-COM kisa devreyken ortalama USB
 * takiliyken ~0.3 V, USB'siz (pilden) ~2.6 V. Sebep bulunmadi. Fabrika sifiri sabit
 * (SKOP_VOLT_OFSET); kullanici kisa devre edip `tz` der, kart o anki ortalamayi sifir sayar.
 *
 * NE YAPAR:
 *   - skop_sifir_ekle: her yakalamanin ham kodlarini AKAN TOPLAMA katar (tampon yok): kod
 *     toplami (u32), kare toplami (u64), yakalama ortalamalarinin en kucugu / en buyugu.
 *   - skop_sifir_karar: yeterli yakalama, saçılma, yakalamalar arasi kayma ve fabrika degerinden
 *     sapma sinirlarini denetler; gecerse "kullanici sifiri" (V, giris-referansli) = ortalama
 *     kodun pin mV'u (.ino eFuse egrisinden, `kal_mv`) fabrika donusumuyle volta tasinmis hali:
 *         sifir = mv / 1000 * oran - fabrika_ofset
 *     Yani giris 0 V iken fabrika donusumunun gosterecegi deger. Uygulanan toplam ofset
 *     fabrika + sifir (skop_sifir_ofset); 0 V girisi artik 0 V cizer.
 *   - skop_sifir_ofsetle: .ino `skop_ofsetle`nin (B19) aritmetigi, ofset parametre.
 *
 * Kayan nokta: hepsi float, her islem ayri yuvarlanir (fp-contract=off — skop_olc.h 1F S2
 * gerekcesi: xtensa a*b+c'yi kaynastirir, AVR ve JS ile ayrisirdi).
 */
#include <stdint.h>
#include <math.h>

#pragma GCC push_options
#pragma GCC optimize ("fp-contract=off")

/* Yakalama plani (.ino uygular; gerekce DEVIR 5.12.123):
 *   10 yakalama x 1000 ornek (10 ms/bol: 100 ms pencere = 5 x 50 Hz = 6 x 60 Hz; suzgecli plan
 *   10 081 Sa/s -> 99.2 ms), aralarinda 200 ms bekleme: ~2.9 s'ye yayilmis 10 000 ornek. */
#define SKOP_SIFIR_YAKALAMA   10u
#define SKOP_SIFIR_ARA_MS     200u
#define SKOP_SIFIR_DENEME     (SKOP_SIFIR_YAKALAMA + 4u)   /* /skop.bin kilidi vb. icin pay */
/* Ret esikleri (V, giris-referansli; gerekce DEVIR 5.12.123):
 *   SINIR   : olculen sifir fabrika degerinden bu kadar saparsa giris kisa devre degil.
 *   SACILMA : butun orneklerin standart sapmasi. Kisa devrede tek ornek sicramalari tepe-tepe
 *             2-4 V (std <= ~0.7 V, suzgecliyken cok daha az); 1.2 V ustu = sinyal var.
 *   KAYMA   : yakalama ortalamalarinin en buyugu - en kucugu. Kisa devrede olculen 0.14 V;
 *             0.6 V ustu = giris degisiyor / bagli bir kaynak var. */
#define SKOP_SIFIR_SINIR_V    6.0f
#define SKOP_SIFIR_SACILMA_V  1.2f
#define SKOP_SIFIR_KAYMA_V    0.6f

enum {
    SKOP_SIFIR_TAMAM = 0,
    SKOP_SIFIR_E_AZ,        /* yeterli yakalama yok */
    SKOP_SIFIR_E_SINIR,     /* fabrika degerinden +-6 V'tan fazla (ya da sayi degil) */
    SKOP_SIFIR_E_SACILMA,   /* ornek saçılması buyuk */
    SKOP_SIFIR_E_KAYMA,     /* yakalamalar arasi ortalama kayiyor */
    SKOP_SIFIR_E_SAYI
};

typedef struct {
    uint32_t n;          /* toplam ornek (<= 65535: top u32'ye sigar) */
    uint32_t top;        /* sum kod */
    uint64_t kare;       /* sum kod^2 */
    float    ort_az;     /* yakalama ortalamalarinin en kucugu (kod) */
    float    ort_cok;    /* en buyugu */
    uint8_t  yakalama;   /* eklenen yakalama */
} SkopSifir;

typedef struct {
    float ort_kod;       /* butun orneklerin ortalamasi (kod) */
    float sacilma_v;     /* ornek std'si (V) */
    float kayma_v;       /* yakalama ortalamalari farki (V) */
    float sifir_v;       /* kullanici sifiri (V) — yalniz TAMAM'da anlamli */
} SkopSifirSonuc;

static void skop_sifir_bas(SkopSifir *s)
{
    s->n = 0u;
    s->top = 0u;
    s->kare = 0u;
    s->ort_az = 0.0f;
    s->ort_cok = 0.0f;
    s->yakalama = 0u;
}

/* Bir yakalama ekler. Bos ya da toplami 65535 ornegi asacak yakalama EKLENMEZ (0 doner). */
static uint8_t skop_sifir_ekle(SkopSifir *s, const uint16_t *v, uint16_t adet)
{
    uint32_t t = 0u, i;
    uint64_t k = 0u;
    float o;
    if (adet == 0u || s->n + adet > 65535u || s->yakalama == 255u) return 0u;
    for (i = 0u; i < adet; i++) {
        t += v[i];
        k += (uint64_t)v[i] * v[i];
    }
    o = (float)t / (float)adet;
    if (s->yakalama == 0u || o < s->ort_az) s->ort_az = o;
    if (s->yakalama == 0u || o > s->ort_cok) s->ort_cok = o;
    s->n += adet;
    s->top += t;
    s->kare += k;
    s->yakalama++;
    return 1u;
}

/* u64 -> float, iki parca (her platformda AYNI yuvarlama; dogruluk degil belirlenimcilik) */
static float skop_sifir__u64f(uint64_t x)
{
    return (float)(uint32_t)(x >> 32) * 4294967296.0f + (float)(uint32_t)x;
}

static float skop_sifir_ort_kod(const SkopSifir *s)
{
    return s->n ? (float)s->top / (float)s->n : 0.0f;
}

/* Ornek standart sapmasi (kod): n * sum x^2 - (sum x)^2 tamsayida TAM, sonra float. */
static float skop_sifir_sacilma_kod(const SkopSifir *s)
{
    uint64_t a, b;
    float nf;
    if (s->n < 2u) return 0.0f;
    a = (uint64_t)s->n * s->kare;
    b = (uint64_t)s->top * s->top;
    if (a <= b) return 0.0f;
    nf = (float)s->n;
    return sqrtf(skop_sifir__u64f(a - b) / nf / nf);
}

/* Giris 0 V iken fabrika donusumunun gosterdigi deger (V). */
static float skop_sifir_volt(float pin_mv, float oran, float fabrika_ofset)
{
    return pin_mv / 1000.0f * oran - fabrika_ofset;
}

/* Uygulanan toplam ofset. kul = 0 iken fabrika degerinin KENDISI (bit bit). */
static float skop_sifir_ofset(float fabrika_ofset, float kul)
{
    return fabrika_ofset + kul;
}

/* NVS'ten okunan deger kullanilabilir mi (bozuk / eski kayit: fabrika). */
static uint8_t skop_sifir_gecerli(float kul)
{
    return (uint8_t)(isfinite(kul) && fabsf(kul) <= SKOP_SIFIR_SINIR_V);
}

/* Karar. pin_mv = ort_kod'un pin mV'u (cagiran eFuse egrisinden cevirir: s'den ort_kod alip).
   kod_v = bir kodun giris-referansli volt karsiligi (saçılma ve kayma esigi icin, nominal yeter).
   Ret sebebi doner; TAMAM'da r->sifir_v yazilir, yoksa 0. */
static uint8_t skop_sifir_karar(const SkopSifir *s, float pin_mv, float oran, float fabrika_ofset,
                                float kod_v, SkopSifirSonuc *r)
{
    float v;
    r->ort_kod = skop_sifir_ort_kod(s);
    r->sacilma_v = skop_sifir_sacilma_kod(s) * kod_v;
    r->kayma_v = (s->ort_cok - s->ort_az) * kod_v;
    r->sifir_v = 0.0f;
    if (s->yakalama < SKOP_SIFIR_YAKALAMA) return SKOP_SIFIR_E_AZ;
    v = skop_sifir_volt(pin_mv, oran, fabrika_ofset);
    if (!skop_sifir_gecerli(v)) return SKOP_SIFIR_E_SINIR;
    if (!(r->sacilma_v <= SKOP_SIFIR_SACILMA_V)) return SKOP_SIFIR_E_SACILMA;
    if (!(r->kayma_v <= SKOP_SIFIR_KAYMA_V)) return SKOP_SIFIR_E_KAYMA;
    r->sifir_v = v;
    return SKOP_SIFIR_TAMAM;
}

/* Ret sebebinin metni (kartin `! tz:` satiri; ASCII). */
static const char *skop_sifir_sebep(uint8_t e)
{
    switch (e) {
    case SKOP_SIFIR_TAMAM:     return "tamam";
    case SKOP_SIFIR_E_AZ:      return "yeterli yakalama alinamadi";
    case SKOP_SIFIR_E_SINIR:   return "olculen sifir fabrika degerinden 6 V'tan fazla sapiyor — giris COM'a kisa devre degil";
    case SKOP_SIFIR_E_SACILMA: return "ornek sacilmasi buyuk — giris COM'a kisa devre degil (sinyal var)";
    case SKOP_SIFIR_E_KAYMA:   return "yakalamalar arasi ortalama kayiyor — giris COM'a kisa devre degil";
    default:                   return "bilinmeyen";
    }
}

/* .ino `skop_ofsetle` (B19): MUTLAK alanlardan ofset dusulur, Vrms = sqrt(Vac^2 + Vort^2).
   Fark / zaman alanlari (Vpp, Vac, f, T, duty, tr, tf, n) ofsetten bagimsiz. */
static void skop_sifir_ofsetle(float *vmax, float *vmin, float *vort, float *vrms, float vac, float ofset)
{
    *vmax -= ofset;
    *vmin -= ofset;
    *vort -= ofset;
    *vrms = sqrtf(vac * vac + *vort * *vort);
}

#pragma GCC pop_options

#endif /* SKOP_SIFIR_H */
