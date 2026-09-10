/*
 * Ölçüm Kartı — Aşama 2 dönüşüm katı (TAŞINABİLİR)
 *
 * NEDEN AYRI DOSYA VE NEDEN ARDUINO'YA BAĞIMSIZ:
 * Bu başlıktaki aritmetik, hem ESP32-S3'te (hedef) hem de AVR'de
 * (doğrulama) derlenebilsin diye hiçbir platform çağrısı içermez.
 * ESP32-S3'ü komut komut çalıştıran bir emülatörümüz yok; ama AVR'yi
 * çalıştıran ve 39/39 bit-birebir doğrulanmış bir emülatörümüz var
 * (uretim/test_avr.py). Aynı kaynağı AVR'de koşturup sonucu bağımsız
 * hesapla karşılaştırınca, aritmetiğin doğruluğu kanıtlanmış oluyor.
 *
 * Bunun geçerli olması için iki kural:
 *   1. `int` KULLANILMAZ — AVR'de 16 bit, ESP32'de 32 bit. Her yerde
 *      int16_t / int32_t / uint32_t / uint64_t yazılı.
 *   2. `double` KULLANILMAZ — AVR'de float'a takma addır. Her yerde float.
 * Böylece iki mimaride de IEEE-754 tek duyarlık, bit birebir aynı sonuç.
 */

#ifndef OLCUM2_H
#define OLCUM2_H

#include <stdint.h>
#include <math.h>       /* sqrtf — osiloskop RMS ölçümü */

/* ───────────────────────────────────────────── ADS1115 sabitleri */
/* Veri sayfası: 16 bit işaretli, tam ölçek ±PGA, yani ±32768 sayım. */
#define ADS_SAYIM 32768.0f

/* PGA kademeleri (V). Yazılımdan seçilir, donanım değişmez. */
#define PGA_6144 6.144f
#define PGA_4096 4.096f
#define PGA_2048 2.048f          /* gerilim kanalının çalışma kademesi */
#define PGA_1024 1.024f
#define PGA_0512 0.512f
#define PGA_0256 0.256f          /* akım kanalının sabit kademesi */

/* ───────────────────────────────────────────── kart sabitleri */
/* Bölücü 100K/6.8K. Oran uretim/tasarim2.py ve sim2_giris.py'de seçildi:
 * 11:1 seçilseydi TL431 kelepçesi 29.7 V'ta sızıp ölçümü bozardı. */
#define BOLME_ORANI 15.70588235f   /* (100k + 6.8k) / 6.8k */

/* ───────────────────────────────────────────── osiloskop kanalı
 * Skop bölücüsü (R6/R7) ölçüm bölücüsüyle AYNI oranda: 100K/6.8K.
 * ESP32-S3'ün ADC'si 12 bit ve 12 dB zayıflatmada kullanılır tavanı
 * ~3.10 V (uretim/tasarim2.py: ESP_ADC_TAVAN).
 *   3.10 / 4095 x 15.70588 = 11.89 mV/adım -> tam ölçek 48.7 V
 * Bu sabit hem firmware'de hem doğrulama koşumunda buradan okunuyor;
 * iki yerde ayrı yaşayıp sessizce ayrışmasın diye. */
#define SKOP_ADC_TAVAN 3.10f
#define SKOP_ADC_SAYIM 4095.0f
#define SKOP_VOLT_ADIM (SKOP_ADC_TAVAN / SKOP_ADC_SAYIM * BOLME_ORANI)

/* Ayarlar — EEPROM/NVS'te saklanır */
typedef struct {
    uint16_t imza;
    float    sont_ohm;      /* takılı şöntün değeri */
    float    v_duzeltme;    /* gerilim kalibrasyon çarpanı */
    float    i_duzeltme;    /* akım kalibrasyon çarpanı */
    int16_t  i_ofset;       /* akım kanalı ham sıfır noktası */
    float    v_pga;         /* gerilim kanalı PGA tam ölçeği */
    float    i_pga;         /* akım kanalı PGA tam ölçeği */
} Ayar2;

typedef struct {
    float volt;
    float amper;
    float watt;
} Okuma2;

/* ─────────────────────────────────── ham kod -> gerilim (veri sayfası) */
static float ads_volt(int16_t ham, float pga)
{
    return (float)ham * (pga / ADS_SAYIM);
}

/* ─────────────────────────────────── gerilim kanalı (ADS #2, tekli) */
static float olc_gerilim(int16_t ham, const Ayar2 *a)
{
    return ads_volt(ham, a->v_pga) * BOLME_ORANI * a->v_duzeltme;
}

/* ─────────────────────────────────── akım kanalı (ADS #1, diferansiyel) */
static float olc_akim(int16_t ham, const Ayar2 *a)
{
    /* Ofset HAM KOD olarak çıkarılır, gerilime çevrilmeden önce:
     * böylece PGA değişse bile ofset aynı ölçekte kalır. */
    int32_t duzeltilmis = (int32_t)ham - (int32_t)a->i_ofset;
    float v = ads_volt((int16_t)duzeltilmis, a->i_pga);
    return v / a->sont_ohm * a->i_duzeltme;
}

/* ─────────────────────────────────── tek ölçüm anı */
static Okuma2 olc2(int16_t ham_v, int16_t ham_i, const Ayar2 *a)
{
    Okuma2 o;
    o.volt = olc_gerilim(ham_v, a);
    o.amper = olc_akim(ham_i, a);
    if (o.amper < 0.0f) o.amper = 0.0f;   /* tek yönlü ölçüm */
    /* Güç ÖRNEK BAŞINA çarpılır. ort(V×I) ≠ ort(V)×ort(I). */
    o.watt = o.volt * o.amper;
    return o;
}

/* ─────────────────────────────────── enerji: TAM SAYI birikim
 *
 * float32'de biriktirilse mantis 24 bit olduğu için toplam büyüdükçe
 * küçük eklemeler yutulur (Aşama 1'de S4 bunu ölçtü: 0.1 W'ta 440 s'de
 * %2.5 kayıp, 512 J'de sayaç tamamen durur).
 *
 * µW × µs = pJ — çarpma tam sayı, kayıp yok.
 * uint64 tavanı 1.8e19 pJ = 5.1 kWh.
 */
static uint64_t enerji_ekle(uint64_t pJ, float watt, uint32_t dt_us)
{
    uint32_t guc_uW = (watt > 0.0f) ? (uint32_t)(watt * 1e6f) : 0u;
    return pJ + (uint64_t)guc_uW * (uint64_t)dt_us;
}

static float enerji_joule(uint64_t pJ)
{
    return (float)((double)pJ / 1.0e12);
}

static float enerji_wh(uint64_t pJ)
{
    /* 1 Wh = 3600 J = 3.6e15 pJ.  (3.6e18 pJ = 1 kWh — Aşama 1'de
     * buraya 3.6e18 yazılmıştı, Wh alanı tam 1000 kat küçük çıkıyordu.) */
    return (float)((double)pJ / 3.6e15);
}

/* ─────────────────────────────────── PGA otomatik kademe seçimi
 *
 * Ölçülen değere göre en dar kademeyi seçer. Kademe daraldıkça adım
 * incelir: ±2.048 V'ta 982 µV, ±0.256 V'ta 123 µV.
 *
 * %90 eşiği histerezis içindir: tam sınırda kademe gidip gelmesin.
 */
static float pga_sec(float dugum_volt)
{
    float m = dugum_volt < 0.0f ? -dugum_volt : dugum_volt;
    if (m > 0.90f * PGA_1024) return PGA_2048;
    if (m > 0.90f * PGA_0512) return PGA_1024;
    if (m > 0.90f * PGA_0256) return PGA_0512;
    return PGA_0256;
}

/* Kademenin girişe vurulmuş tam ölçeği (V) */
static float tam_olcek_volt(float pga)
{
    return pga * BOLME_ORANI;
}

/* Kademenin girişe vurulmuş adımı (V) */
static float adim_volt(float pga)
{
    return (pga / ADS_SAYIM) * BOLME_ORANI;
}

static void varsayilan_ayar2(Ayar2 *a)
{
    a->imza = 0xC0FEu;
    a->sont_ohm = 1.0f;          /* mA kademesi: 1 Ω */
    a->v_duzeltme = 1.0f;
    a->i_duzeltme = 1.0f;
    a->i_ofset = 0;
    a->v_pga = PGA_2048;
    a->i_pga = PGA_0256;
}

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

#endif /* OLCUM2_H */
