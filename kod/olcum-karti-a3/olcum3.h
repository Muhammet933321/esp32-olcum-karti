#ifndef OLCUM3_H
#define OLCUM3_H
/*
 * Asama 3 olcum matematigi — CIFT YONLU (+-) on uc.
 *
 * PLATFORM BAGIMSIZ. `int` ve `double` YASAK; her yerde acik genislikli
 * tip ve `float`. Boylece ayni kaynak hem gercek ESP32-S3 derleyicisiyle
 * derleniyor, hem de bit-birebir dogrulanmis AVR emulatorunde kosuyor.
 * (Asama 2'de olcum2.h ayni disiplinle yazilmisti; A4/A6 bunu kullaniyor.)
 *
 * 🔴 KURAL BIR ARA CIGNENMISTI — B25'te (2026-09-11) geri getirildi.
 * enerji_joule3 · enerji_wh3 · yuk_mAh3 · yuk_coulomb3 fonksiyonlari
 * `(float)((double)<int64> / <sabit>)` yaziyordu. Asama 1'den devralinan
 * bir aliskanlikti; kaynakta savunan tek satir yoktu.
 *
 * NEDEN ONEMLIYDI: avr-gcc `double`u 32 bit yapiyor (takma ad),
 * Xtensa'da 64 bit. Yani B4/B5'in EMULATORDE kosturdugu aritmetik,
 * kartta kosacak olandan FARKLIYDI — degerlerin bir kisminda son bit
 * ayriliyordu. Adimin (ve kullanici belgesinin) "sinanan sey kartta
 * calisacak kodun TA KENDISI" iddiasi bu dort fonksiyon icin DOGRU
 * DEGILDI. Fark kucuktu ama iddia yanlisti.
 *
 * OLCULDU, sonra duzeltildi: iki yolun farki en kotu durumda 1 ULP
 * (bagil 6.8e-8; float32 eps 6.0e-8). ADS1115'in tek adimi 3.1e-5,
 * yani fark olcum gurultusunun 450 kati altinda. Saf float'a gecmenin
 * bedeli int64 uclarinda ~0.5 ULP dogruluk; karsiliginda iki mimaride
 * BIT BIREBIR ayni sonuc. Bu takas dogru: emulatorun temsil gucu,
 * olculemeyecek bir 0.5 ULP'den kiymetli.
 *
 * `test_olcum3.py` B4.6 artik dosyada HIC `(double)` olmadigini
 * sinıyor ve bedeli kayit altinda tutuyor. `mutasyon.py`de karsiligi
 * var: cast geri konursa zincir kirmizi.
 *
 * NEDEN AYRI DOSYA: olcum2.h Asama 2 zincirinde (A4, A5, A6) kullaniliyor
 * ve o zincir gecmeye devam etmeli. Asama 3 farkli bir ON UC'tur; ayni
 * dosyayi degistirmek dogrulanmis Asama 2'yi bozardi.
 *
 * TASARIM KAYNAGI: uretim/tasarim3.py + uretim/tasarim3_sabit.py
 * Buradaki her sabit orada bir `kural()` ile sinaniyor.
 */
#include <stdint.h>
#include <math.h>      /* sqrtf — hizli yol RMS hesabi */

/* ─────────────────────────────────── ADS1115 (TI SBAS444B) */
#define ADS_SAYIM      32768.0f      /* 16 bit isaretli */
#define PGA_2048       2.048f
#define PGA_1024       1.024f        /* iki gerilim kanalinin calisma kademesi */
#define PGA_0512       0.512f
#define PGA_0256       0.256f        /* akim kanalinin sabit kademesi */

/* ─────────────────────────────────── bolme oranlari (tasarim3_sabit.py)
 *
 * NORMAL : 1x220K / 6.8K  -> (220000+6800)/6800
 *           (ilk surumde 2x100K idi; menzil Vref kadar YUKARI kaydigi icin
 *            -29.43 V'ta kirpiyordu. 220K ile simetrik +-32.4 V oluyor.)
 * YUKSEK : 6x820K / 8.2K  -> (4920000+8200)/8200
 *
 * 6 direncin sebebi: 1/4W metal filmin azami CALISMA gerilimi 200 V
 * (Yageo MFR). 4 adetle hem tam olcek 410 V'ta kaliyor hem direnc
 * basina 151 V dusuyordu — pay yok.
 *
 * 2026-09-09: tasarim once 6x1M / 10K idi; tedarikcide metal film 1M
 * cikmadi. Alt bacak zincirin YUZDE BIRI oldugu surece oran TAM 601.0
 * kaliyor (6R / (R/100) = 600), yani 820K, 2.2M ve 6.8M'in ucu de ayni
 * menzili ve adimi verirdi. 820K secildi cunku YUZEY KACAGINA en az
 * duyarli olan o: hata ~ Rust / R_kacak, 10 Gohm'luk bir kacakta
 * 820K %0.049, 2.2M %0.132, 6.8M %0.408 yapar. ORAN_YUKSEK DEGISMEDI.
 */
#define ORAN_NORMAL    33.35294118f
#define ORAN_YUKSEK    601.0f

/* B16/B17 — ADS yolunun ortusme suzgeci zaman sabitleri (saniye).
 *   NORMAL : (220k||6.8k + 22k) x 100nF = 28.596k x 100n
 *   YUKSEK : (4.92M||8.2k + 22k) x 100nF = 30.186k x 100n
 *   AKIM   : (R18+R19+R38+R39) x C18 = 2200 x 1.32u
 * Ikisi ESIT DEGIL; olcek duzeltmesi kanal basina yapiliyor. */
#define TAU_NORMAL     0.00285957f
#define TAU_YUKSEK     0.00301857f
#define TAU_AKIM       0.00290400f

/* Vref: TL431 (2.495 V) -> 10K/22K -> 1.7153 V, tamponlanmis.
 *
 * Vref hatasi girise vurulmus SABIT bir ofsettir (N'den bagimsiz), kazanc
 * hatasi degil — turevi tasarim3.py bolum 1'de. Sifir kalibrasyonu siler.
 */
#define VREF_NOMINAL   1.71531250f

/* ─────────────────────────────────── osiloskop kanali (ESP32 dahili ADC)
 *
 * AYRI giris, AYRI bolucu — gerilim kanallariyla ayni dugum DEGIL.
 * Bolucu 100K/6.8K (semada R20/R21), yani Asama 2 ile ayni oran.
 * Bu kanal DALGA SEKLI icin; sayisal deger ADS1115'ten gelir
 * (ESP32-S3 ADC'si dogrusal degildir).
 */
/* B19 (2026-09-09): kanal CIFT YONLU yapildi.
 * Bolucunun ALT UCU artik GND'de degil VREF'te (semada R23 -> VREF),
 * ve R23 6.8K -> 2.7K. Menzil 0..45.5 V yerine -65.2 .. +45.1 V.
 * Bedeli cozunurluk: adim 11.1 -> 26.9 mV.
 *
 * Donusum artik OFSETLI. Bolucunun alt ucu VREF'te oldugu icin
 *     V_dugum = VREF + (V_giris - VREF) * R23/(R20+R23)
 * ters cevirince
 *     V_giris = VREF + (V_dugum - VREF) * SKOP_ORAN
 *             = kod * SKOP_VOLT_ADIM - SKOP_VOLT_OFSET
 * ⚠ Bastaki +VREF UNUTULMAMALI: ofset VREF*ORAN DEGIL, VREF*(ORAN-1).
 *   Unutulursa 0 V giris -VREF*ORAN okur. (B19 bolum 1 bunu yakaladi.)
 */
#define SKOP_ORAN      38.03703704f  /* (100k + 2.7k) / 2.7k */
#define SKOP_ADC_TAVAN 3.10f         /* 12 dB zayiflatmada kullanilabilir ust */
#define SKOP_ADC_SAYIM 4096.0f  /* B20: LSB = tam olcek/4096 */
#define SKOP_VOLT_ADIM (SKOP_ADC_TAVAN / SKOP_ADC_SAYIM * SKOP_ORAN)
#define SKOP_VOLT_OFSET (VREF_NOMINAL * (SKOP_ORAN - 1.0f))

/* Hizli akim yolu fark yukselteci — 47K/10K (tasarim3.py bolum 10).
 * DEVIR 5.1.4 kazanc 27 onermisti; o, hizli yolu ADS'ten 5 kat ONCE
 * kirpiyordu (tam olcek sont gerilimi 51 mV vs ADS'in 256 mV'u). */
#define HIZLI_KAZANC   4.7f

/* Osiloskop OLCUM matematigi (SkopOlcum, skop_olc) ayri dosyada:
 * skop_olc.h — olcum2.h'den URETILEN birebir kopya, ayrisma denetimi
 * uretim/test_skop_ayni.py'de.
 *
 * BURADAN INCLUDE EDILMIYOR, .ino kendisi ediyor. Sebep: olcum3.h'yi
 * AVR emulatorunde kosan test (B4/B5) de derliyor ve orada skop
 * matematigi cagrilmadigi icin "defined but not used" uyarisi cikiyordu.
 * Skop matematigi zaten olcum KATMANINA degil FIRMWARE'e ait. */

/* ─────────────────────────────────── kanal ayari */
typedef struct {
    float   n;          /* bolme orani */
    float   pga;        /* ADS tam olcegi (V) */
    float   kazanc;     /* 1.0 baslangic; kazanc kalibrasyonu gunceller */
    int16_t sifir_ham;  /* giris 0 V iken okunan HAM kod */
    float   tau;        /* B17: ortusme suzgecinin zaman sabiti (s).
                         * NORMAL ve YUKSEK AYNI DEGIL (28.60k vs 30.19k
                         * x 100nF) — B16 bunu olctu. Olcek duzeltmesi
                         * kanal basina yapilmali. */
} Kanal3;

/* NEDEN `sifir_ham`, `ofset_volt` DEGIL:
 *
 * Ilk surumde ofset volt olarak saklaniyordu ve sifir kalibrasyonu
 * `ofset -= okunan` yapiyordu. Bu ofseti O ANKI kazanca baglar; sonra
 * kazanc kalibrasyonu yapilinca ofset ESKI kazanca gore kalir ve iki
 * kalibrasyon birbirini bozar. AVR testi bunu yakaladi: 12 V'ta kalibre
 * edip -24 V'ta olcunce 175 mV hata kaliyordu.
 *
 * Ham kod olarak saklayinca sifir TANIM GEREGI dogru olur ve kazanctan
 * bagimsizdir; ikisi tam ayrisir. Ayrica sifir noktasinda sinyal TAM 0
 * oldugu icin "sifira yakin girisle kazanc kalibrasyonunu reddet"
 * korumasi da dogru calisir.
 */

typedef struct {
    float    volt;
    float    amper;
    float    watt;
} Okuma3;

/* ─────────────────────────────────── ham kod -> diferansiyel gerilim */
static float ads_volt3(int16_t ham, float pga)
{
    return (float)ham * (pga / ADS_SAYIM);
}

/* ─────────────────────────────────── CIFT YONLU gerilim
 *
 *   fark = (Vin - Vref)/N          <- ADS'in okudugu, ISARETLI
 *   Vin  = fark*N + Vref
 *
 * Kazanc yalnizca fark terimine uygulanir (hata bolucu direnclerinde),
 * ofset ise ayri toplanir. Bu ayrim kalibrasyonu tek anlamli yapiyor.
 */
static float olc_gerilim3(int16_t ham, const Kanal3 *k)
{
    int32_t d = (int32_t)ham - (int32_t)k->sifir_ham;
    if (d > 32767) d = 32767;
    if (d < -32768) d = -32768;
    return ads_volt3((int16_t)d, k->pga) * k->n * k->kazanc;
}

/* Sifir kalibrasyonu: giris 0 V'a baglanmisken cagrilir.
 * Okunan degeri ofsetten dusurur, boylece okuma tam 0 olur. */
static void kalibre_sifir(int16_t ham, Kanal3 *k)
{
    k->sifir_ham = ham;
}

/* Kazanc kalibrasyonu: giriste BILINEN `gercek` volt varken cagrilir.
 * Yalnizca sinyal terimini olcekler; ofsete dokunmaz. */
static void kalibre_kazanc(int16_t ham, float gercek, Kanal3 *k)
{
    float s = olc_gerilim3(ham, k);
    /* s sifira cok yakinsa oran anlamsiz olur — kalibrasyonu REDDET.
     * (Tam olcegin %5'i esik; altinda gurultu orani bozar.) */
    float esik = 0.05f * k->pga * k->n;
    if (s > esik || s < -esik) {
        /* 🔴 B22.1 — IKINCI SAVUNMA HATTI. `gercek` sifir (ya da sacma)
           gelirse kazanc sifira/asiri degere gider ve NVS'e yazilir;
           kazanc 0 olunca olc_gerilim3 hep 0 doner, yani |s| > esik
           sarti bir daha ASLA saglanmaz ve kanal KALICI olarak olur.
           Fabrika kazanci 1.0; bolucu direnc toleransi +-%1 oldugu icin
           mesru kalibrasyon 0.9-1.1 araligindadir. 0.2-5 kat siniri
           fazlasiyla genis ama tuglalanmayi imkansiz kiliyor. */
        float yeni = k->kazanc * (gercek / s);
        if (yeni > 0.2f && yeni < 5.0f) k->kazanc = yeni;
    }
}

/* Kademenin girise vurulmus tam olcegi.
 *
 * ⚠ MENZIL SIMETRIK DEGIL. fark = (Vin - Vref)/N oldugu icin ADS'in
 * +-pga penceresi girise su araligi karsilik getirir:
 *      Vin_ust = +pga*N + Vref
 *      Vin_alt = -pga*N + Vref
 * Yani menzil Vref kadar YUKARI kaymistir. GARANTI SIMETRIK aralik
 * +-(pga*N - Vref)'tir ve tasarim bunu esas almalidir.
 *
 * Bu, AVR testinin yakaladigi gercek bir tasarim hatasiydi: NORMAL kanal
 * 2x100K/6.8K ile -29.43 V'ta kirpiyor, +32.86 V'a cikiyordu. Bolucu
 * 220K/6.8K'ya cekilerek simetrik +-32.4 V saglandi.
 */
/* Ham yarim-genlik (Vref kaymasi haric) — digerleri bunu kullanir. */
static float tam_olcek3(const Kanal3 *k)
{
    return k->pga * k->n * k->kazanc;
}

static float tam_olcek_ust(const Kanal3 *k)
{
    return tam_olcek3(k) + VREF_NOMINAL;
}
static float tam_olcek_alt(const Kanal3 *k)
{
    return -tam_olcek3(k) + VREF_NOMINAL;
}
/* Guvenle kullanilabilecek SIMETRIK menzil */
static float tam_olcek_simetrik(const Kanal3 *k)
{
    return tam_olcek3(k) - VREF_NOMINAL;
}
static float adim3(const Kanal3 *k)
{
    return (k->pga / ADS_SAYIM) * k->n * k->kazanc;
}

/* ─────────────────────────────────── CIFT YONLU akim
 *
 * Asama 2'de burada su vardi:
 *     if (o.amper < 0.0f) o.amper = 0.0f;   // tek yonlu olcum
 * Donanim (ADS #1 AIN0-AIN1 diferansiyel) zaten ISARETLI okuyor;
 * kirpma tamamen yazilimdaydi. Kaldirildi.
 *
 * Guc elektroniginde bobin akimi ters doner; tek yonlu olcum SMPS'te
 * yanlis cevaptir.
 */
static float olc_akim3(int16_t ham, int16_t ofset_ham, float pga,
                       float sont_ohm, float duzeltme)
{
    int32_t d = (int32_t)ham - (int32_t)ofset_ham;
    /* int16 tasmasini onle: ADS zaten +-32768 veriyor, fark 2 kat olabilir */
    if (d > 32767) d = 32767;
    if (d < -32768) d = -32768;
    return ads_volt3((int16_t)d, pga) / sont_ohm * duzeltme;
}

/* ─────────────────────────────────── ISARETLI enerji birikimi
 *
 * Asama 2'de uint64 idi ve negatif gucu 0 sayiyordu. Cift yonlu olcumde
 * bu YANLIS: sarj/desarj cevriminde sayac yalnizca yukari sayar ve net
 * enerji hep sifirdan buyuk cikar.
 *
 * int64 pJ:  tavan 9.22e18 pJ = 9.22e6 J = 2562 Wh (uint64'te 5124 Wh idi;
 * isaret biti icin yarisi gitti — 25 W'ta 102 saat, hala fazlasiyla yeter).
 *
 * guc_uW int64 OLMALI: 615 V x 11.5 A = 7072 W = 7.07e9 uW, int32'nin
 * 2.147e9 tavanini asar. Asama 2'de uint32 idi cunku tavan 25 W'ti.
 */
static int64_t enerji_ekle3(int64_t pJ, float watt, uint32_t dt_us)
{
    int64_t guc_uW = (int64_t)(watt * 1e6f);
    return pJ + guc_uW * (int64_t)dt_us;
}

static float enerji_joule3(int64_t pJ)
{
    return (float)pJ / 1.0e12f;
}

/* ─────────────────────────────────── B21: ISARETLI YUK (mAh) BIRIKIMI
 *
 * Enerjinin (pJ) birebir kardesi, ama YUK biriktiriyor. Pil kapasitesi
 * mAh cinsinden konusuluyor; enerji Wh veriyor, ikisi FARKLI seyler ve
 * ikisi de gerekli (mAh pili, Wh isi anlatir).
 *
 *   uA x us = 1e-6 A x 1e-6 s = 1e-12 A.s = 1 pC
 *   1 mAh   = 1e-3 A x 3600 s = 3.6 C     = 3.6e12 pC
 *   int64 tavani = 9.223e18 pC = 2 562 048 mAh = 2562 Ah
 *
 * ISARETLI olmasi bilerek: pil SARJ edilirse sayac GERI sayar. Asama
 * 2'nin enerji sayaci uint64'tu ve negatifi 0 sayiyordu; cift yonlu
 * olcumde bu YANLIS (bkz. enerji_ekle3'un ustundeki not).
 */
static int64_t yuk_ekle3(int64_t pC, float amper, uint32_t dt_us)
{
    int64_t i_uA = (int64_t)(amper * 1e6f);
    return pC + i_uA * (int64_t)dt_us;
}

static float yuk_mAh3(int64_t pC)
{
    return (float)pC / 3.6e12f;
}

static float yuk_coulomb3(int64_t pC)
{
    return (float)pC / 1.0e12f;
}

static float enerji_wh3(int64_t pJ)
{
    /* 1 Wh = 3600 J = 3.6e15 pJ.  (3.6e18 = 1 kWh — Asama 1'de buraya
     * 3.6e18 yazilmisti, Wh alani tam 1000 kat kucuk cikiyordu.) */
    return (float)pJ / 3.6e15f;
}

/* ─────────────────────────────────── V-I KAYMA HIZALAYICI
 *
 * ESP32-S3'te tek SAR var ve pattern sirali kosuyor: V,I,V,I...
 * Ornekler arasi 1/83333 = 12.000 us, kanal periyodu 24.000 us
 * -> kayma TAM YARIM ORNEK.
 *
 * Duzeltilmezse reaktif yukte hata BIRINCI derecedendir:
 *   1 kHz, PF=0.5 -> %-13.3   (dirençsel yukte yalnizca %-0.28)
 *
 * 4 katsayili Lagrange kesirli gecikme (d = 1/2):
 *   h = [-1/16, 9/16, 9/16, -1/16]
 * Simetrik -> dogrusal faz -> FAZ HATASI TAM SIFIR. Geriye yalnizca
 * genlik sarkmasi kalir: 1 kHz'te 0.0001 dB, 5 kHz'te 0.063 dB.
 *
 * DIKKAT: suzgec Nyquist'te sifira gider (kesirli gecikme suzgeclerinin
 * dogasi).
 *
 * 🔴 B20 (2026-09-10) — IKI AYRI BANT, TEK CUMLEYE KARISMISTI. Eskiden
 * burada yalnizca "Guvenilir wattmetre bandi ~5 kHz" yaziyordu:
 *   * HIZLI YOL  (guc_olc, hizala_yarim, 41.7 kSa/s kanal basina):
 *     ~5 kHz DOGRU. Orada |H_L| = 0.9928 (-0.063 dB), Sallen-Key de
 *     20.8 kHz'te -5.45 dB veriyor.
 *   * ADS YOLU   (hizala_kesirli, ~671 Sa/s): AYNI suzgec orada
 *     100 Hz'te %0.78, 200 Hz'te %8.3 sarkiyor. Bandi ~100 Hz.
 * Ve ADS yolunun GERCEK siniri sarkma bile degil FAZ KALIBRASYONU:
 * `F` sabit bir ZAMAN gecikmesi saklar, duzelttigi sey ise iki RC'nin
 * arctan farkidir — ikisi yalnizca kalibrasyon frekansinda ortusur.
 * Gecerlilik bandi 40-70 Hz. Olcum: uretim/sim3_bant.py bolum 2-3.
 */
#define HIZA_K0  (-0.0625f)      /* -1/16 */
#define HIZA_K1  ( 0.5625f)      /*  9/16 */

/* B8'den beri GERCEKTEN CAGRILIYOR: `guc_olc()` hizli yolun akim
 * ornegini yarim ornek geri kaydirmak icin bunu kullaniyor.
 * (B4-B7 arasinda henuz cagrilmiyordu ve `unused` isaretliydi.) */
static float hizala_yarim(float x_m2, float x_m1, float x_0, float x_p1)
{
    return HIZA_K0 * x_m2 + HIZA_K1 * x_m1 + HIZA_K1 * x_0 + HIZA_K0 * x_p1;
}

/* ─────────────────────────────────── B17: GENEL KESIRLI GECIKME
 *
 * `hizala_yarim` d = 1/2'ye sabitlenmis. B17'de ADS yolunda BASKA bir
 * kesirli gecikme gerekiyor:
 *   * iki cipe tek atis baslatma komutu ARDI ARDINA yaziliyor; aradaki
 *     I2C suresi (~95 us) bilinen ve SABIT bir kayma birakiyor
 *   * uzerine menzil basina FAZ KALIBRASYONU ekleniyor
 * Ikisinin toplami ornek periyoduna bolununce istenen `d` cikiyor.
 *
 * 4 katsayili Lagrange (dugumler n = -1, 0, 1, 2):
 *     h[k] = PROD_{j != k} (d - j) / (k - j)
 * d = 0.5 konursa TAM OLARAK [-1/16, 9/16, 9/16, -1/16] cikiyor, yani
 * `hizala_yarim`in ozel hali. Test bunu siniyor (B17/LK).
 *
 * ⚠ `hizala_yarim` KALDIRILMADI: hizli yol onu kullanmaya devam ediyor
 *   ve B5'in kaniti dogrudan ona ait.
 */
static void lagrange4(float d, float *h)
{
    /* n = -1, 0, 1, 2 — acik yazildi; dongu + dizinin AVR'de maliyeti
     * bu dort satirdan yuksek ve okunurlugu dusuk. */
    h[0] = (d - 0.0f) * (d - 1.0f) * (d - 2.0f) / (-6.0f);
    h[1] = (d + 1.0f) * (d - 1.0f) * (d - 2.0f) / (2.0f);
    h[2] = (d + 1.0f) * (d - 0.0f) * (d - 2.0f) / (-2.0f);
    h[3] = (d + 1.0f) * (d - 0.0f) * (d - 1.0f) / (6.0f);
}

/* x_m1 en ESKI, x_p2 en YENI ornek. Sonuc: x_0'dan d ornek SONRAKI deger.
 * d = 0 -> x_0, d = 1 -> x_p1. */
static float hizala_kesirli(float d, float x_m1, float x_0,
                            float x_p1, float x_p2)
{
    float h[4];
    lagrange4(d, h);
    return h[0] * x_m1 + h[1] * x_0 + h[2] * x_p1 + h[3] * x_p2;
}

/* ─────────────────────────────────── B17: SUZGEC OLCEK DUZELTMESI
 *
 * B16: ADS yolunda hem gerilim hem akim tek kutuplu bir RC'den geciyor.
 * 50 Hz'te |H| = 0.744, yani AC guc |H_v| * |H_i| = 0.55 kati okunuyor —
 * %45 DUSUK. B16 iki kanali ESITLEDIGI icin bu artik YUKTEN BAGIMSIZ bir
 * olcek carpani ve frekans bilinirse TAM silinebiliyor.
 *
 *     1/|H(f)| = sqrt(1 + (2*pi*f*tau)^2)
 *
 * f = 0 (DC) -> carpan 1, yani duzeltme YOK. Bu dogru: DC'de suzgec
 * zayiflatmiyor.
 *
 * ⚠ FREKANS OLCULMUYOR, AYARLANIYOR. ADS yolu 860 SPS ve 55 Hz suzgecle
 *   frekans olcemez. Kullanici 50/60/0 seciyor. Yanlis ayar ONGORULEBILIR
 *   bir hata yapar (60 Hz sebekede 50 Hz ayari %30 civari) — sim3_senkron.py
 *   bolum 2 bunu tablo halinde veriyor.
 */
static float suzgec_ters_kazanc(float f_hz, float tau_s)
{
    float w;
    if (f_hz <= 0.0f || tau_s <= 0.0f) return 1.0f;
    w = 6.28318531f * f_hz * tau_s;
    return sqrtf(1.0f + w * w);
}

/* ─────────────────────────────────── HIZLI YOL: GERCEK GUC (B8)
 *
 * ESP32-S3'un dahili ADC'si iki kanali SIRAYLA ornekliyor:
 *     V I V I V I ...
 * Akim ornekleri gerilimden YARIM ORNEK GEC alinmis oluyor. Duzeltilmezse
 * reaktif yukte hata BIRINCI derecedendir (1 kHz, PF=0.1 -> %+78).
 *
 * Burasi hizalayiciyi GERCEKTEN kullanan yer. B5 hizalayiciyi tek basina
 * dogruladi; bu fonksiyon onu tam guc hesabina baglar.
 *
 * NEDEN ORNEK BASINA CARPIM: ort(V x I) != ort(V) x ort(I).
 * Anahtarlamali yukte akim kesiktir; guc, gerilimle akimin
 * KORELASYONUDUR. Once carp, sonra biriktir.
 */
typedef struct {
    float p;        /* gercek guc (W) — ort(v*i), isaretli */
    float s;        /* gorunur guc (VA) = Vrms * Irms */
    float pf;       /* guc faktoru = p/s, isaretli (negatif = geri besleme) */
    float v_rms;
    float i_rms;
    float v_ort;
    float i_ort;
    uint16_t n;     /* hesaba giren ornek sayisi */
} GucOlcum;

/* v[] ve i[] AYNI uzunlukta, i[] yarim ornek GEC ornekleniyor.
 *
 * Hizalayici i[n-2..n+1] istedigi icin kenarlar dusuyor: n = 2 .. adet-2.
 * `hizala` 0 ise duzeltme YAPILMAZ — arayuz ikisini yan yana gosterip
 * farki kanitlayabilsin diye.
 */
static void guc_olc(const float *v, const float *i, uint16_t adet,
                    uint8_t hizala, GucOlcum *o)
{
    o->p = o->s = o->pf = 0.0f;
    o->v_rms = o->i_rms = o->v_ort = o->i_ort = 0.0f;
    o->n = 0;
    if (adet < 8u) return;              /* anlamli bir pencere degil */

    float p_top = 0.0f, vv_top = 0.0f, ii_top = 0.0f;
    float v_top = 0.0f, i_top = 0.0f;
    uint16_t say = 0;

    for (uint16_t n = 2u; n + 1u < adet; n++) {
        float ih = hizala ? hizala_yarim(i[n - 2u], i[n - 1u], i[n], i[n + 1u])
                          : i[n];
        float vn = v[n];
        p_top += vn * ih;
        vv_top += vn * vn;
        /* 🔴 B20 (2026-09-10): burada `ih * ih` vardi, yani gosterilen Irms
         * HIZALAYICININ genlik sarkmasini yiyordu (5 kHz'te %0.72), Vrms ise
         * yemiyordu — asimetrik ve yanlis. Hizalama YALNIZCA guc icin gerekli
         * (P, V ile I'nin korelasyonu); RMS bir tek-kanal buyuklugudur ve HAM
         * ornekten hesaplanmali. Sarkma sinyalin degil suzgecin ozelligi. */
        ii_top += i[n] * i[n];
        v_top += vn;
        i_top += ih;
        say++;
    }
    if (!say) return;

    float k = 1.0f / (float)say;
    o->n = say;
    o->p = p_top * k;
    o->v_ort = v_top * k;
    o->i_ort = i_top * k;
    o->v_rms = sqrtf(vv_top * k);
    o->i_rms = sqrtf(ii_top * k);
    o->s = o->v_rms * o->i_rms;
    /* PF yalnizca gorunur guc anlamliysa tanimli. Sifira bolmeyi
     * onlemek disinda bir sebep de var: cok kucuk sinyalde PF gurultudur. */
    o->pf = (o->s > 1e-9f) ? (o->p / o->s) : 0.0f;
}

/* ─────────────────────────────────── tek olcum ani
 *
 * Guc ORNEK BASINA carpilir: ort(VxI) != ort(V) x ort(I).
 * Anahtarlamali yukte akim kesiktir; guc, gerilimle akimin korelasyonudur.
 */
static Okuma3 olc3(int16_t ham_v, int16_t ham_i, const Kanal3 *kv,
                   int16_t i_ofset, float i_pga, float sont, float i_duz)
{
    Okuma3 o;
    o.volt = olc_gerilim3(ham_v, kv);
    o.amper = olc_akim3(ham_i, i_ofset, i_pga, sont, i_duz);
    o.watt = o.volt * o.amper;      /* isaretli — negatif guc mumkun */
    return o;
}

/* En yakin tam sayiya yuvarlama — kesme DEGIL.
 * Kesme kullanilirsa nominal sifir kodu ile gercek ADC kodu 1 LSB
 * ayrisiyor ve kalibrasyonsuz kartta 0 V girisi 0 okumuyor. */
static int16_t yuvarla16(float v)
{
    return (int16_t)(v + (v >= 0.0f ? 0.5f : -0.5f));
}

/* ─────────────────────────────────── varsayilan kanallar */
static void varsayilan_kanal3(Kanal3 *normal, Kanal3 *yuksek)
{
    /* Nominal sifir kodu: giris 0 V iken fark = -Vref/N */
    normal->n = ORAN_NORMAL;
    normal->pga = PGA_1024;
    normal->kazanc = 1.0f;
    normal->sifir_ham = yuvarla16(-VREF_NOMINAL / ORAN_NORMAL
                                  / (PGA_1024 / ADS_SAYIM));
    normal->tau = TAU_NORMAL;

    yuksek->n = ORAN_YUKSEK;
    yuksek->pga = PGA_1024;
    yuksek->kazanc = 1.0f;
    yuksek->sifir_ham = yuvarla16(-VREF_NOMINAL / ORAN_YUKSEK
                                  / (PGA_1024 / ADS_SAYIM));
    yuksek->tau = TAU_YUKSEK;
}

#endif /* OLCUM3_H */
