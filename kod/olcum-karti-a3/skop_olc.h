#ifndef SKOP_OLC_H
#define SKOP_OLC_H
/*
 * Osiloskop olcum matematigi — ASAMA 2 ve ASAMA 3 ORTAK.
 *
 * !! BU DOSYA ELLE DUZENLENMEZ. olcum2.h icindeki ayni blogun birebir
 *    kopyasidir ve uretim/skop_olc_uret.py tarafindan uretilir.
 *    uretim/test_skop_ayni.py iki metni karakter karakter karsilastirir;
 *    ayrisirlarsa zincir KALIR.
 *
 * Degisiklik yapacaksan: once olcum2.h icinde yap, sonra
 *     python uretim/skop_olc_uret.py
 */
#include <stdint.h>
#include <math.h>       /* sqrtf */

/* ═══════════════════════════════════════════════════════════════════════
   OSİLOSKOP ÖLÇÜMLERİ

   Gerçek osiloskopların ekranın altında gösterdiği otomatik ölçümler.
   Burada, `olcum2.h`'nin geri kalanı gibi PLATFORM BAĞIMSIZ yazıldı
   (int/double yok) — böylece AVR emülatöründe bit-birebir koşturulabiliyor
   ve doğrulama zincirine girebiliyor.

   Hepsi tek geçişte değil, birkaç kısa geçişte hesaplanıyor; 4000 örnek
   için 240 MHz'de toplam birkaç yüz mikrosaniye.
   ═══════════════════════════════════════════════════════════════════════ */

typedef struct {
    float vmax;        /* tepe (V, prob ucunda)            */
    float vmin;        /* dip                              */
    float vpp;         /* tepeden tepeye                   */
    float vort;        /* ortalama (DC bileşen)            */
    float vrms;        /* toplam RMS (DC dahil)            */
    float vac;         /* AC RMS (ortalama çıkarılmış)     */
    float frekans;     /* Hz — 0 ise ölçülemedi            */
    float periyot;     /* s                                */
    float duty;        /* % — orta seviyenin üstünde geçen */
    float t_yuksel;    /* s, %10→%90                       */
    float t_dus;       /* s, %90→%10                       */
    uint16_t cevrim;   /* ölçüme giren tam çevrim sayısı   */
} SkopOlcum;

/* İki örnek arasında `esik`in geçildiği kesirli konumu döndürür.
 * Doğrusal ara değerleme: kenar iki örnek arasına düşerse periyot
 * ölçümü örnek çözünürlüğüne hapsolmaz. Bu, frekans doğruluğunu
 * tipik olarak 10–50 kat iyileştiriyor. */
static float skop_kesisim(float onceki, float simdi, float esik)
{
    float fark = simdi - onceki;
    if (fark > -1e-9f && fark < 1e-9f) return 0.0f;
    return (esik - onceki) / fark;
}

static void skop_olc(const uint16_t *ham, uint16_t adet, float volt_adim,
                     float ornekleme_hz, SkopOlcum *o)
{
    uint16_t i;
    uint16_t hmin, hmax;
    float toplam, kare_toplam, v;
    float orta, hist, ust, alt;
    float ilk_kesim, son_kesim;
    uint16_t kesim_sayisi;
    uint8_t hazir;
    float onceki;

    o->vmax = o->vmin = o->vpp = o->vort = 0.0f;
    o->vrms = o->vac = o->frekans = o->periyot = 0.0f;
    o->duty = o->t_yuksel = o->t_dus = 0.0f;
    o->cevrim = 0;
    if (adet == 0u || ornekleme_hz <= 0.0f) return;

    /* --- 1. geçiş: uçlar, ortalama, RMS ------------------------------- */
    hmin = hmax = ham[0];
    toplam = 0.0f;
    kare_toplam = 0.0f;
    for (i = 0u; i < adet; i++) {
        uint16_t h = ham[i];
        if (h < hmin) hmin = h;
        if (h > hmax) hmax = h;
        v = (float)h * volt_adim;
        toplam += v;
        kare_toplam += v * v;
    }
    o->vmax = (float)hmax * volt_adim;
    o->vmin = (float)hmin * volt_adim;
    o->vpp  = o->vmax - o->vmin;
    o->vort = toplam / (float)adet;
    o->vrms = sqrtf(kare_toplam / (float)adet);

    /* AC RMS = √(kare_ort − ort²).  Kayan nokta yuvarlaması yüzünden
     * sabit bir sinyalde bu ifade eksiye düşebilir; kırpıyoruz. */
    v = kare_toplam / (float)adet - o->vort * o->vort;
    o->vac = (v > 0.0f) ? sqrtf(v) : 0.0f;

    /* --- 2. geçiş: periyot, yükselen kenar kesişimleriyle -------------
     * Orta seviyede histerezisli kenar arıyoruz. Histerezis olmadan
     * gürültülü bir sinyalde her örnekte sahte kesişim sayardık. */
    orta = ((float)hmin + (float)hmax) * 0.5f;
    hist = ((float)hmax - (float)hmin) * 0.125f;   /* %12.5 */
    if (hist < 1.0f) return;                       /* düz çizgi: ölçüm yok */

    ilk_kesim = son_kesim = 0.0f;
    kesim_sayisi = 0u;
    hazir = 0u;
    onceki = (float)ham[0];
    for (i = 1u; i < adet; i++) {
        float s = (float)ham[i];
        if (!hazir) {
            if (s < orta - hist) hazir = 1u;
        } else if (s >= orta) {
            float k = (float)(i - 1u) + skop_kesisim(onceki, s, orta);
            if (kesim_sayisi == 0u) ilk_kesim = k;
            son_kesim = k;
            kesim_sayisi++;
            hazir = 0u;
        }
        onceki = s;
    }

    if (kesim_sayisi >= 2u) {
        float ornek_periyot = (son_kesim - ilk_kesim) /
                              (float)(kesim_sayisi - 1u);
        if (ornek_periyot > 0.0f) {
            o->cevrim  = (uint16_t)(kesim_sayisi - 1u);
            o->periyot = ornek_periyot / ornekleme_hz;
            o->frekans = ornekleme_hz / ornek_periyot;

            /* Duty: yalnız TAM çevrimler üzerinde say — yarım çevrim
             * sayılırsa duty sistematik olarak kayar. */
            {
                uint16_t bas = (uint16_t)ilk_kesim;
                uint16_t son = (uint16_t)son_kesim;
                uint16_t ust_sayi = 0u, top = 0u;
                for (i = bas; i <= son && i < adet; i++) {
                    if ((float)ham[i] >= orta) ust_sayi++;
                    top++;
                }
                if (top > 0u)
                    o->duty = 100.0f * (float)ust_sayi / (float)top;
            }
        }
    }

    /* --- 3. geçiş: yükselme / düşme süresi (%10 → %90) ---------------- */
    alt = (float)hmin + ((float)hmax - (float)hmin) * 0.1f;
    ust = (float)hmin + ((float)hmax - (float)hmin) * 0.9f;
    {
        float t10 = -1.0f, t90 = -1.0f;
        onceki = (float)ham[0];
        for (i = 1u; i < adet; i++) {
            float s = (float)ham[i];
            if (t10 < 0.0f && onceki < alt && s >= alt)
                t10 = (float)(i - 1u) + skop_kesisim(onceki, s, alt);
            if (t10 >= 0.0f && t90 < 0.0f && onceki < ust && s >= ust)
                t90 = (float)(i - 1u) + skop_kesisim(onceki, s, ust);
            onceki = s;
        }
        if (t10 >= 0.0f && t90 > t10)
            o->t_yuksel = (t90 - t10) / ornekleme_hz;
    }
    {
        float t90 = -1.0f, t10 = -1.0f;
        onceki = (float)ham[0];
        for (i = 1u; i < adet; i++) {
            float s = (float)ham[i];
            if (t90 < 0.0f && onceki > ust && s <= ust)
                t90 = (float)(i - 1u) + skop_kesisim(onceki, s, ust);
            if (t90 >= 0.0f && t10 < 0.0f && onceki > alt && s <= alt)
                t10 = (float)(i - 1u) + skop_kesisim(onceki, s, alt);
            onceki = s;
        }
        if (t90 >= 0.0f && t10 > t90)
            o->t_dus = (t10 - t90) / ornekleme_hz;
    }
}

#endif /* SKOP_OLC_H */
