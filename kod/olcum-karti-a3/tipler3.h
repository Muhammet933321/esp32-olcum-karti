#ifndef TIPLER3_H
#define TIPLER3_H
/*
 * Asama 3 firmware'inin struct'lari.
 *
 * NEDEN AYRI DOSYA — ARDUINO TUZAGI:
 * Arduino, .ino dosyasinin basina otomatik fonksiyon prototipleri ekler.
 * `void varsayilan_ayar3(Ayar3 *a)` gibi kendi struct'ini kullanan bir
 * fonksiyonun prototipi, struct tanimindan ONCE yerlesir ve derleyici
 *     error: variable or field 'varsayilan_ayar3' declared void
 *     error: 'Ayar3' was not declared in this scope
 * verir. Ayni tuzaga Asama 1'de de dusulmustu (README "Yakalanan alti
 * hata", #5) ve cozumu ayni: tipleri .ino disina, bir baslik dosyasina al.
 * Baslik dosyalari prototiplerden ONCE include edildigi icin sorun kalkiyor.
 */
#include <stdint.h>
#include "olcum3.h"

/* Kalici ayar. `imza` surum damgasi: yapisi degisince eski NVS kaydi
 * sessizce yanlis okunmasin diye Asama 2'nin 0xC0FE'sinden farkli.
 * B17'de yapi buyudugu icin 0xC0F3 -> 0xC0F4.
 *
 * 🔴 B20 (2026-09-10): imza TEK YERDE tanimli olmali. B17 bu dosyada
 * 0xC0F4'e gecmisti ama .ino'daki ayar_yukle/ayar_kaydet elle 0xC0F3
 * yaziyordu — yani NVS'e hep ESKI imza gidiyor, damga hicbir sey
 * korumuyordu. Ayrisan iki kopya yerine tek sabit:  */
/* B21'de yapi yine buyudu (pil testi ayarlari) -> 0xC0F4 -> 0xC0F5.
 * ⚠ Bu, karta daha once kaydedilmis KALIBRASYONU sifirlar. Donanim
 *   henuz kurulmadigi icin bedeli yok; kurulduktan SONRA yapilsaydi
 *   kalibrasyonun tekrarlanmasi gerekirdi. */
/* 🔴 B22.1 (2026-09-10): 0xC0F5 -> 0xC0F6. faz_kal ORNEK cinsindenken
 * MIKROSANIYE'ye cevrildi. YAPI BOYUTU DEGISMEDI (float[2] yine float[2]) —
 * yani `n == sizeof(Ayar3)` denetimi bu degisikligi GOREMEZ ve imza TEK
 * korumadir. Eski bir NVS kaydi yeni anlamla okunsaydi 0.02 "ornek"
 * degeri 0.02 us sanilirdi: duzeltme 75 kat kucululurdu, sessizce.
 * Donanim henuz kurulmadigi icin kalibrasyon sifirlanmasinin bedeli yok;
 * kurulduktan SONRA yapilsaydi yeniden kalibrasyon gerekirdi. */
#define AYAR3_IMZA 0xC0F6u
struct Ayar3 {
    uint16_t imza;
    Kanal3   normal;        /* +-32.4 V kanali  (ADS #2 AIN0-AIN1) */
    Kanal3   yuksek;        /* +-613.7 V kanali (ADS #2 AIN2-AIN3) */
    float    sont_ohm;
    float    i_pga;
    float    i_duzeltme;
    int16_t  i_ofset;
    uint8_t  menzil;        /* 0 = NORMAL, 1 = YUKSEK */
    uint8_t  oto_menzil;    /* 1 ise yazilim kanallar arasi gecis yapar */

    /* ── B17 ────────────────────────────────────────────────────────
     * sebeke_hz: OLCEK DUZELTMESI icin gereken frekans. ADS yolu
     *   (860 SPS, 55 Hz suzgec) frekans OLCEMEZ, o yuzden AYAR.
     *   0 = DC, duzeltme yok. 50 / 60 = sebeke.
     *   ⚠ Yanlis ayar ONGORULEBILIR bir hata yapar: 60 Hz sebekede
     *     50 Hz ayari ~%30. sim3_senkron.py bolum 2 tabloyu veriyor.
     * faz_kal_us: MENZIL BASINA faz kalibrasyonu, MIKROSANIYE cinsinden
     *   SABIT gecikme. Direncli bir yukle olculur (referans cihaz
     *   gerekmez): direncli yukte gercek faz farki sifir olmali, okunan
     *   fark dogrudan suzgec eslesmezligidir. [0] = NORMAL, [1] = YUKSEK.
     *
     *   🔴 B22.1 — NEDEN US, NEDEN ORNEK DEGIL: duzeltilen sey iki RC'nin
     *   arctan farkidir, yani SABIT bir zaman. Ornek cinsinden saklanirsa
     *   uygulanan zaman `faz_kal * ornek_periyot_us` olur ve dongu
     *   periyoduyla olceklenir — oysa periyot degiskendir (web istegi,
     *   menzil gecisi 1518 us, B22.1 oncesi enableDelay kusuru). 1503 us'te
     *   kalibre edilen kart 2000 us'te 1.744 derece artik hata yapiyordu;
     *   B17'nin kabul olcutu <=1 derece. Simdi bolmenin ICINDE:
     *       d = (t_kayma_us + faz_kal_us) / ornek_periyot_us            */
    float    sebeke_hz;
    float    faz_kal_us[2];

    /* -- B21 (pil kapasite testi) ------------------------------------
     * pil_kesme_v : desarj bu gerilime inince MOSFET KAPANIR. Li-ion
     *   icin 3.0 V, kursun asit icin 10.5 V tipik. Kullanici giriyor.
     * pil_kayit_hz: egri kayit hizi (0.2 / 1 / 5). Olcum hizi DEGIL —
     *   olcum 665 Sa/s, bu yalnizca KAC ORNEGIN bir noktada toplandigi.
     * pil_azami_s : azami test suresi (emniyet zaman asimi). 0 = kapali
     *   DEGIL, en az bir sinir olmali; varsayilan 24 saat. */
    float    pil_kesme_v;
    float    pil_kayit_hz;
    uint32_t pil_azami_s;
};

static void varsayilan_ayar3(Ayar3 *a)
{
    a->imza = AYAR3_IMZA;   /* B17: yapi degisti · B20: tek kaynak */
    varsayilan_kanal3(&a->normal, &a->yuksek);
    a->sont_ohm = 0.1f;
    a->i_pga = PGA_0256;
    a->i_duzeltme = 1.0f;
    a->i_ofset = 0;
    a->menzil = 0;
    a->oto_menzil = 1;
    a->sebeke_hz = 50.0f;   /* B17 — Turkiye sebekesi; 0 = DC */
    a->faz_kal_us[0] = 0.0f;
    a->faz_kal_us[1] = 0.0f;
    a->pil_kesme_v = 3.0f;      /* B21: Li-ion 1S varsayilani */
    a->pil_kayit_hz = 1.0f;
    a->pil_azami_s = 24UL * 3600UL;
}

#endif /* TIPLER3_H */
