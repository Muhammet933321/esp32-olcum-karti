/*
 * Ölçüm Kartı — Aşama 2  (ESP32-S3 N16R8 + 2× ADS1115)
 *
 * Voltmetre · Ampermetre · Wattmetre · Enerji sayacı · Osiloskop
 *
 * Donanım (uretim/sema2-uret.py, ERC 0 ihlal, netlist 33/33):
 *   ADS #1 0x48  AIN0-AIN1 diferansiyel  <- şönt (Kelvin), PGA ±0.256 V
 *   ADS #2 0x49  AIN0 tekli              <- 100K/6.8K bölücü, PGA ±2.048 V
 *   GPIO4 ADC1_CH3                       <- osiloskop, ayrı bölücü
 *   GPIO8/9                              <- I2C SDA/SCL, 4.7K pull-up
 *   TL431 2.495 V                        <- koruma kelepçe rayı
 *
 * Arayüz: WiFi + HTTP. Ölçüm akışı Server-Sent Events ile gider —
 * ek kütüphane gerektirmez, tarayıcı EventSource ile doğrudan okur.
 * Satır biçimi Aşama 1 ile AYNI, böylece arayuz/app.js değişmiyor:
 *   D <volt> <amper> <watt> <joule> <wh> <ms> <örnek>
 */

#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>

#include "esp_adc/adc_continuous.h"

#include "olcum2.h"

// ───────────────────────────────────────────────── pinler ve adresler
static const uint8_t PIN_SDA = 8;
static const uint8_t PIN_SCL = 9;
static const uint8_t PIN_SKOP = 4;          // ADC1_CH3
static const uint8_t PIN_HAZIR = 7;         // ADS #1 ALERT/RDY
static const uint8_t ADS_AKIM = 0x48;       // ADDR -> GND
static const uint8_t ADS_GERILIM = 0x49;    // ADDR -> VDD

static const char *WIFI_AD = "";            // kurulumda doldurulacak
static const char *WIFI_SIFRE = "";

// ───────────────────────────────────────────────── ADS1115 sürücüsü
//
// Kütüphane kullanmıyoruz: yazması 40 satır, ve her bitin ne olduğunu
// bilmek doğrulama için şart. Yazmaç haritası veri sayfası Tablo 8.
static const uint8_t ADS_DONUSUM = 0x00;
static const uint8_t ADS_AYAR    = 0x01;
static const uint8_t ADS_ALT     = 0x02;   // Lo_thresh
static const uint8_t ADS_UST     = 0x03;   // Hi_thresh

// Ayar yazmacı bitleri
static const uint16_t ADS_SUREKLI  = 0x0000;   // MODE = 0, sürekli
static const uint16_t ADS_860SPS   = 0x00E0;   // DR = 111
static const uint16_t ADS_KOMP_KAPALI = 0x0003;

static uint16_t pga_bitleri(float pga) {
  if (pga >= PGA_6144) return 0x0000;
  if (pga >= PGA_4096) return 0x0200;
  if (pga >= PGA_2048) return 0x0400;
  if (pga >= PGA_1024) return 0x0600;
  if (pga >= PGA_0512) return 0x0800;
  return 0x0A00;                              // ±0.256 V
}

static void ads_yaz(uint8_t adres, uint8_t yazmac, uint16_t deger) {
  Wire.beginTransmission(adres);
  Wire.write(yazmac);
  Wire.write((uint8_t)(deger >> 8));
  Wire.write((uint8_t)(deger & 0xFF));
  Wire.endTransmission();
}

static int16_t ads_oku(uint8_t adres) {
  Wire.beginTransmission(adres);
  Wire.write(ADS_DONUSUM);
  Wire.endTransmission();
  Wire.requestFrom(adres, (uint8_t)2);
  if (Wire.available() < 2) return 0;
  uint16_t h = Wire.read();
  uint16_t l = Wire.read();
  return (int16_t)((h << 8) | l);
}

// mux: 0x0000 = AIN0-AIN1 diferansiyel, 0x4000 = AIN0 tekli
static void ads_kur(uint8_t adres, uint16_t mux, float pga) {
  uint16_t ayar = 0x8000            // OS: tek atış başlat (sürekli kipte yok sayılır)
                | mux
                | pga_bitleri(pga)
                | ADS_SUREKLI
                | ADS_860SPS
                | ADS_KOMP_KAPALI;
  ads_yaz(adres, ADS_AYAR, ayar);
}

// ───────────────────────────────────────────────── durum
Ayar2 ayar;
Preferences kalici;
WebServer sunucu(80);

uint64_t enerji_pJ = 0;
uint32_t son_us = 0;
uint32_t rapor_ms = 200;
uint32_t son_rapor = 0;

uint32_t ornek = 0;
float v_top = 0, i_top = 0, w_top = 0;
char son_satir[128] = "";

// ───────────────────────────────────────────────── ayar saklama
void ayar_yukle() {
  kalici.begin("olcum2", false);
  size_t n = kalici.getBytesLength("ayar");
  if (n == sizeof(Ayar2)) {
    kalici.getBytes("ayar", &ayar, sizeof(Ayar2));
  }
  if (ayar.imza != 0xC0FE) varsayilan_ayar2(&ayar);
}

void ayar_kaydet() {
  ayar.imza = 0xC0FE;
  kalici.putBytes("ayar", &ayar, sizeof(Ayar2));
}

// ───────────────────────────────────────────────── ölçüm
// Yeni bir donusumun bitmesini bekler. Zaman asimi varsa yine de okur
// (ALERT pini baglanmamis olabilir) ama o zaman sayim guvenilmez.
bool yeni_donusum_bekle(uint32_t azami_us) {
  uint32_t t0 = micros();
  while (digitalRead(PIN_HAZIR) == HIGH) {
    if (micros() - t0 > azami_us) return false;
  }
  while (digitalRead(PIN_HAZIR) == LOW) {
    if (micros() - t0 > azami_us) return false;
  }
  return true;
}

Okuma2 olcum_al() {
  // Iki AYRI ADS1115 oldugu icin V ve I ES ZAMANLI ornekleniyor.
  // Tek cip ile kanal degistirseydik aralarinda 1.16 ms gecikme kalirdi
  // ve degisen yukte P = V x I carpimi yanlis olurdu.
  int16_t ham_i = ads_oku(ADS_AKIM);
  int16_t ham_v = ads_oku(ADS_GERILIM);
  kademe_gozet(ham_v);
  return olc2(ham_v, ham_i, &ayar);
}

// Gerilim kanalı OTOMATİK KADEME: ölçülen düğüm gerilimine göre en dar
// PGA'yı seçer. ±2.048 V'ta adım 982 µV, ±0.256 V'ta 123 µV — küçük
// gerilimlerde 8 kat çözünürlük kazandırır. Donanım değişmiyor, yalnız
// ADS1115'in ayar yazmacı yeniden yazılıyor.
void kademe_gozet(int16_t ham_v) {
  float dugum = ads_volt(ham_v, ayar.v_pga);
  float yeni = pga_sec(dugum);
  if (yeni != ayar.v_pga) {
    ayar.v_pga = yeni;
    ads_kur(ADS_GERILIM, 0x4000, yeni);
    // Kademe değişiminden sonraki ilk dönüşüm eski kademeye ait olabilir;
    // bir dönüşüm süresi (1/860 s) bekleyip atıyoruz.
    delayMicroseconds(1200);
    ads_oku(ADS_GERILIM);
  }
}

// ───────────────────────────────────────────────── osiloskop
//
// ESP32-S3'un ADC'si DMA ile 83 333 örnek/s'e kadar sürekli çalışıyor
// (SOC_ADC_SAMPLE_FREQ_THRES_HIGH). Arduino'nun analogContinuousRead()
// sarmalayıcısı conversions_per_pin kadar örneğin ORTALAMASINI döndürür —
// dalga şekli vermez, yani osiloskop için kullanılamaz. Bu yüzden doğrudan
// IDF'in sürekli sürücüsünü kullanıyoruz ve DMA tamponunu ham okuyoruz.
//
// ZAMAN TABANI: örnekleme hızı 611 Hz .. 83 333 Sa/s arasında AYARLANABİLİR
// (SOC_ADC_SAMPLE_FREQ_THRES_LOW/HIGH). Sabit 83 333 Sa/s'te pencere hep
// 12 ms kalıyordu ve 50 Hz'in bir tam çevrimi (20 ms) ekrana SIĞMIYORDU.
// Artık gerçek osiloskoplardaki gibi saniye/bölme seçiliyor.
static const uint32_t SKOP_HZ_AZAMI   = 83333;  // SOC_ADC_SAMPLE_FREQ_THRES_HIGH
static const uint32_t SKOP_HZ_ASGARI  = 611;    // SOC_ADC_SAMPLE_FREQ_THRES_LOW
static const uint16_t SKOP_AZAMI_ADET = 4000;   // 2 x 8 kB SRAM
// SKOP_TAVAN artik olcum2.h icinde: SKOP_ADC_TAVAN / SKOP_VOLT_ADIM
static const uint8_t  SKOP_KANAL      = 3;      // GPIO4 = ADC1_CH3
static const uint8_t  SKOP_BOLME      = 10;     // ekranda yatay bölme sayısı

// Zaman tabanı merdiveni — 1-2-5 dizisi, gerçek osiloskoplardaki gibi.
// Hedef 100 örnek/bölme. Hız tavana dayanınca örnek sayısı düşer (hızlı
// uçta), tabana dayanınca artar (yavaş uçta).
static const uint32_t SKOP_TDIV_US[] = {
    100, 200, 500, 1000, 2000, 5000,
    10000, 20000, 50000, 100000, 200000, 500000
};
static const uint8_t SKOP_TDIV_SAYI =
    sizeof(SKOP_TDIV_US) / sizeof(SKOP_TDIV_US[0]);

// Tetikleme kipleri
static const uint8_t SKOP_KIP_OTO    = 0;  // tetik yoksa yine de göster
static const uint8_t SKOP_KIP_NORMAL = 1;  // tetik yoksa gösterme
static const uint8_t SKOP_KIP_TEK    = 2;  // tek atış

struct SkopAyar {
    uint8_t  tdiv;        // SKOP_TDIV_US indeksi
    uint16_t esik;        // tetik seviyesi, ADC kodu 0..4095
    uint8_t  kenar;       // 0 = yükselen, 1 = düşen
    uint16_t histerezis;  // ADC kodu — sahte tetiklemeyi önler
    uint8_t  on_yuzde;    // ön-tetik yüzdesi 0..90
    uint8_t  kip;         // SKOP_KIP_*
};

static SkopAyar skop_ayar = { 5, 2048, 0, 40, 25, SKOP_KIP_OTO };

static adc_continuous_handle_t skop_kulp = NULL;
static uint16_t skop_veri[SKOP_AZAMI_ADET];
static uint16_t skop_gecici[SKOP_AZAMI_ADET];
static uint16_t skop_adet = 0;        // son yakalamadaki örnek sayısı
static uint16_t skop_tetik_idx = 0;   // tetik örneğinin dizideki yeri
static uint32_t skop_hz = 0;          // son yakalamanın gerçek hızı
static bool     skop_tetiklendi = false;

// Prob ucundaki volt/adım. Skop bölücüsü (R6/R7) ölçüm bölücüsüyle aynı
// oranda: 100K/6.8K. 3.10 V / 4095 x 15.706 = 11.89 mV -> tam ölçek 48.7 V.
static float skop_volt_adim() { return SKOP_VOLT_ADIM; }

// Seçili zaman tabanı için örnekleme hızını ve örnek sayısını çözer.
// Pencere = SKOP_BOLME x tdiv.
static void skop_taban_coz(uint8_t tdiv_idx, uint32_t *hz, uint16_t *adet)
{
    float pencere_s = (float)SKOP_TDIV_US[tdiv_idx] * (float)SKOP_BOLME * 1e-6f;
    float istenen = (float)(SKOP_BOLME * 100u) / pencere_s;

    if (istenen > (float)SKOP_HZ_AZAMI)  istenen = (float)SKOP_HZ_AZAMI;
    if (istenen < (float)SKOP_HZ_ASGARI) istenen = (float)SKOP_HZ_ASGARI;
    *hz = (uint32_t)(istenen + 0.5f);

    float n = pencere_s * (float)(*hz);
    if (n > (float)SKOP_AZAMI_ADET) n = (float)SKOP_AZAMI_ADET;
    if (n < 100.0f) n = 100.0f;
    *adet = (uint16_t)(n + 0.5f);
}

void skop_kur() {
    adc_continuous_handle_cfg_t k = {};
    k.max_store_buf_size = 8192;
    k.conv_frame_size    = 1024;            // 4 bayt/dönüşüm -> 256 örnek
    if (adc_continuous_new_handle(&k, &skop_kulp) != ESP_OK) skop_kulp = NULL;
}

// Örnekleme hızını değiştirir. ADC durmuş olmalı.
static bool skop_hiz_ayarla(uint32_t hz) {
    if (!skop_kulp) return false;
    adc_digi_pattern_config_t d = {};
    d.atten     = ADC_ATTEN_DB_12;
    d.channel   = SKOP_KANAL;
    d.unit      = ADC_UNIT_1;
    d.bit_width = ADC_BITWIDTH_12;

    adc_continuous_config_t c = {};
    c.pattern_num    = 1;
    c.adc_pattern    = &d;
    c.sample_freq_hz = hz;
    c.conv_mode      = ADC_CONV_SINGLE_UNIT_1;
    c.format         = ADC_DIGI_OUTPUT_FORMAT_TYPE2;
    return adc_continuous_config(skop_kulp, &c) == ESP_OK;
}

// Halka tamponlu yakalama — ÖN-TETİK bedavaya geliyor.
//
// ADC sürekli koşar ve örnekler halkaya yazılır. Tetik aranırken halka
// dolmaya devam ettiği için, tetik bulunduğunda elimizde ZATEN tetik
// ÖNCESİNE ait örnekler var. Gerçek osiloskopların ön-tetik penceresi
// tam olarak böyle çalışıyor.
//
// Histerezis: yükselen kenarda önce sinyalin (esik - histerezis) altına
// inmesi ŞART. Bu olmadan gürültülü bir eşikte yüzlerce sahte tetik alınır
// ve bir MOSFET anahtarlama çalması aynı çevrimde defalarca tetikler.
static bool skop_yakala()
{
    uint32_t hz;
    uint16_t n;
    skop_taban_coz(skop_ayar.tdiv, &hz, &n);

    if (!skop_kulp) return false;
    if (!skop_hiz_ayarla(hz)) return false;
    if (adc_continuous_start(skop_kulp) != ESP_OK) return false;

    uint16_t on = (uint16_t)((uint32_t)n * skop_ayar.on_yuzde / 100u);
    if (on + 2u > n) on = (uint16_t)(n - 2u);
    uint16_t sonra = (uint16_t)(n - on);

    uint16_t w = 0, dolu = 0, kalan = 0, tetik_w = 0, onceki = 0;
    bool bulundu = false, hazir = false, ilk = true;

    // Zaman aşımı: pencerenin dört katı, en az 300 ms, en çok 4 s.
    float pencere_ms = 1000.0f * (float)n / (float)hz;
    uint32_t azami_ms = (uint32_t)(pencere_ms * 4.0f) + 300u;
    if (azami_ms > 4000u) azami_ms = 4000u;
    uint32_t t0 = millis();

    uint8_t cerceve[1024];
    while (millis() - t0 < azami_ms) {
        uint32_t okunan = 0;
        if (adc_continuous_read(skop_kulp, cerceve, sizeof(cerceve),
                                &okunan, 100) != ESP_OK) continue;

        for (uint32_t b = 0;
             b + SOC_ADC_DIGI_RESULT_BYTES <= okunan;
             b += SOC_ADC_DIGI_RESULT_BYTES) {
            adc_digi_output_data_t *o = (adc_digi_output_data_t *)&cerceve[b];
            if (o->type2.channel != SKOP_KANAL) continue;
            uint16_t v = o->type2.data;

            skop_veri[w] = v;
            w = (uint16_t)((w + 1u) % n);
            if (dolu < n) dolu++;

            if (!bulundu) {
                if (dolu >= on) {        // yeterli geçmiş biriktikten sonra
                    if (skop_ayar.kenar == 0u) {              // yükselen
                        if (!hazir) {
                            if ((uint32_t)v + skop_ayar.histerezis <
                                (uint32_t)skop_ayar.esik) hazir = true;
                        } else if (!ilk && onceki < skop_ayar.esik &&
                                   v >= skop_ayar.esik) {
                            bulundu = true;
                        }
                    } else {                                  // düşen
                        if (!hazir) {
                            if ((uint32_t)v >
                                (uint32_t)skop_ayar.esik + skop_ayar.histerezis)
                                hazir = true;
                        } else if (!ilk && onceki > skop_ayar.esik &&
                                   v <= skop_ayar.esik) {
                            bulundu = true;
                        }
                    }
                }
                onceki = v;
                ilk = false;
                if (bulundu) {
                    tetik_w = (uint16_t)((w + n - 1u) % n);
                    kalan = sonra;
                }
            } else if (kalan > 0u) {
                kalan--;
            }
        }
        if (bulundu && kalan == 0u) break;
    }
    adc_continuous_stop(skop_kulp);

    if (!bulundu) {
        // OTO kipinde tetik bulunamazsa serbest koşu olarak göster.
        // NORMAL ve TEK kipinde göstermek YALAN olur — başarısız dön.
        if (skop_ayar.kip != SKOP_KIP_OTO) return false;
        if (dolu < 2u) return false;
    } else if (kalan > 0u) {
        return false;                    // zaman aşımı, pencere dolmadı
    }

    // Halkayı düz diziye aç: en eskiden en yeniye.
    uint16_t bas = (dolu < n) ? 0u : w;
    for (uint16_t i = 0; i < dolu; i++)
        skop_gecici[i] = skop_veri[(uint16_t)((bas + i) % n)];
    for (uint16_t i = 0; i < dolu; i++) skop_veri[i] = skop_gecici[i];

    skop_adet = dolu;
    skop_hz = hz;
    skop_tetiklendi = bulundu;
    skop_tetik_idx = bulundu ? (uint16_t)((tetik_w + n - bas) % n) : 0u;
    if (skop_tetik_idx >= dolu) skop_tetik_idx = 0u;
    return true;
}

// OTOMATİK KURULUM ("auto-set") — gerçek osiloskoplardaki AUTO tuşu.
//
// Sinyali hiç bilmeden doğru zaman tabanını ve tetik seviyesini bulur:
//   1. Kademeleri hızlıdan yavaşa tarayarak frekansı yakala
//   2. Ekranda ~4 çevrim görünecek zaman tabanını seç
//   3. Tetiği dalganın ORTASINA, histerezisi genliğin %10'una koy
static bool skop_otomatik()
{
    uint8_t  eski_kip  = skop_ayar.kip;
    uint8_t  eski_tdiv = skop_ayar.tdiv;
    uint16_t eski_esik = skop_ayar.esik;
    uint16_t eski_hist = skop_ayar.histerezis;

    skop_ayar.kip = SKOP_KIP_OTO;
    skop_ayar.esik = 0u;                 // tetiklemesiz: serbest yakala
    skop_ayar.histerezis = 0u;

    float    bulunan_f = 0.0f;
    uint16_t orta = 2048u, genlik = 0u;

    for (uint8_t i = 0; i < SKOP_TDIV_SAYI; i++) {
        skop_ayar.tdiv = i;
        if (!skop_yakala()) continue;

        SkopOlcum m;
        skop_olc(skop_veri, skop_adet, skop_volt_adim(), (float)skop_hz, &m);
        if (m.frekans > 0.0f && m.cevrim >= 2u) {
            float va = skop_volt_adim();
            bulunan_f = m.frekans;
            orta   = (uint16_t)(((m.vmax + m.vmin) * 0.5f) / va);
            genlik = (uint16_t)(m.vpp / va);
            break;
        }
    }

    if (bulunan_f <= 0.0f) {             // periyodik sinyal yok
        skop_ayar.kip  = eski_kip;
        skop_ayar.tdiv = eski_tdiv;
        skop_ayar.esik = eski_esik;
        skop_ayar.histerezis = eski_hist;
        return false;
    }

    // Ekranda ~4 çevrim olacak s/bölme: pencere = 4/f, tdiv = pencere/bölme
    float hedef_us = (4.0f / bulunan_f) / (float)SKOP_BOLME * 1e6f;
    uint8_t en_iyi = 0;
    for (uint8_t i = 0; i < SKOP_TDIV_SAYI; i++)
        if ((float)SKOP_TDIV_US[i] <= hedef_us) en_iyi = i;

    skop_ayar.tdiv = en_iyi;
    skop_ayar.esik = orta;
    skop_ayar.histerezis = (genlik / 10u) > 4u ? (uint16_t)(genlik / 10u) : 4u;
    skop_ayar.kip = eski_kip;
    return true;
}

// Protokol — yeni `S2` başlığı zaman tabanını, tetik konumunu ve
// otomatik ölçümleri taşıyor:
//
//   S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
//   M f=<Hz> T=<s> Vpp=<V> Vmax=<V> Vmin=<V> Vort=<V> Vrms=<V> Vac=<V>
//     duty=<%> tr=<s> tf=<s> n=<çevrim>
//   <ham ADC kodları, 16'şar satır>
//   E
void skop_yolla()
{
    if (!skop_yakala()) {
        Serial.println(F("! tetiklenemedi"));
        return;
    }

    SkopOlcum m;
    skop_olc(skop_veri, skop_adet, skop_volt_adim(), (float)skop_hz, &m);

    Serial.print(F("S2 "));
    Serial.print(skop_adet);                    Serial.print(' ');
    Serial.print(skop_hz);                      Serial.print(' ');
    Serial.print(skop_volt_adim(), 6);          Serial.print(' ');
    Serial.print(skop_tetik_idx);               Serial.print(' ');
    Serial.print(SKOP_TDIV_US[skop_ayar.tdiv]); Serial.print(' ');
    Serial.print(skop_ayar.kip);                Serial.print(' ');
    Serial.println(skop_tetiklendi ? 1 : 0);

    Serial.print(F("M f="));   Serial.print(m.frekans, 3);
    Serial.print(F(" T="));    Serial.print(m.periyot, 9);
    Serial.print(F(" Vpp="));  Serial.print(m.vpp, 4);
    Serial.print(F(" Vmax=")); Serial.print(m.vmax, 4);
    Serial.print(F(" Vmin=")); Serial.print(m.vmin, 4);
    Serial.print(F(" Vort=")); Serial.print(m.vort, 4);
    Serial.print(F(" Vrms=")); Serial.print(m.vrms, 4);
    Serial.print(F(" Vac="));  Serial.print(m.vac, 4);
    Serial.print(F(" duty=")); Serial.print(m.duty, 2);
    Serial.print(F(" tr="));   Serial.print(m.t_yuksel, 9);
    Serial.print(F(" tf="));   Serial.print(m.t_dus, 9);
    Serial.print(F(" n="));    Serial.println(m.cevrim);

    for (uint16_t i = 0; i < skop_adet; i++) {
        Serial.print(skop_veri[i]);
        if (i % 16 == 15) Serial.println();
        else Serial.print(' ');
    }
    if (skop_adet % 16) Serial.println();
    Serial.println(F("E"));
}

void skop_ayar_yaz()
{
    uint32_t hz; uint16_t n;
    skop_taban_coz(skop_ayar.tdiv, &hz, &n);
    Serial.print(F("T tdiv="));  Serial.print(skop_ayar.tdiv);
    Serial.print('/');           Serial.print(SKOP_TDIV_SAYI - 1);
    Serial.print(F(" ("));       Serial.print(SKOP_TDIV_US[skop_ayar.tdiv]);
    Serial.print(F(" us/bolme) hz="));  Serial.print(hz);
    Serial.print(F(" adet="));   Serial.print(n);
    Serial.print(F(" pencere_ms="));
    Serial.print(1000.0f * (float)n / (float)hz, 2);
    Serial.print(F(" esik="));   Serial.print(skop_ayar.esik);
    Serial.print(F(" kenar="));
    Serial.print(skop_ayar.kenar ? F("dusen") : F("yukselen"));
    Serial.print(F(" hist="));   Serial.print(skop_ayar.histerezis);
    Serial.print(F(" on="));     Serial.print(skop_ayar.on_yuzde);
    Serial.print(F("% kip="));   Serial.println(skop_ayar.kip);
}

void enerji_biriktir(float watt) {
  uint32_t simdi = micros();
  uint32_t dt = simdi - son_us;      // taşma sarmalı doğru çalışır
  son_us = simdi;
  if (dt > 1000000UL) return;        // ilk tur veya uzun duraklama
  enerji_pJ = enerji_ekle(enerji_pJ, watt, dt);
}

// ───────────────────────────────────────────────── HTTP
void kok_sayfa() {
  sunucu.send(200, "text/html",
              "<!doctype html><meta charset=utf-8>"
              "<title>Olcum Karti</title>"
              "<p>Akis: <a href=/akis>/akis</a> (text/event-stream)");
}

void akis_sayfa() {
  // Server-Sent Events: tarayıcı EventSource ile okur, ek kütüphane yok
  WiFiClient istemci = sunucu.client();
  istemci.print("HTTP/1.1 200 OK\r\n"
                "Content-Type: text/event-stream\r\n"
                "Cache-Control: no-cache\r\n"
                "Connection: keep-alive\r\n\r\n");
  uint32_t gonderilen = 0;
  while (istemci.connected() && gonderilen < 100000) {
    if (!yeni_donusum_bekle(3000)) continue;   // yalniz BENZERSIZ ornek say
    Okuma2 o = olcum_al();
    enerji_biriktir(o.watt);
    v_top += o.volt; i_top += o.amper; w_top += o.watt; ornek++;

    if (millis() - son_rapor >= rapor_ms) {
      son_rapor = millis();
      uint32_t n = ornek ? ornek : 1;
      snprintf(son_satir, sizeof(son_satir),
               "D %.3f %.5f %.5f %.4f %.7f %lu %lu",
               (double)(v_top / n), (double)(i_top / n), (double)(w_top / n),
               (double)enerji_joule(enerji_pJ), (double)enerji_wh(enerji_pJ),
               (unsigned long)son_rapor, (unsigned long)n);
      istemci.print("data: ");
      istemci.print(son_satir);
      istemci.print("\n\n");
      v_top = i_top = w_top = 0; ornek = 0; gonderilen++;
    }
  }
}

// ───────────────────────────────────────────────── kalibrasyon ve komutlar
//
// Kart kalibrasyonsuz kullanılamaz: şöntün gerçek değeri etiketinden %1
// sapar, bölücü dirençleri %5'lik karbondur ve ADS'in akım kanalının
// sıfır noktası birkaç LSB kayıktır. Bu komutlar ayarları NVS'e yazar,
// yani güç kesildiğinde kaybolmaz.
//
//   ?          ayarları yaz
//   t<esik>    osiloskop yakala (esik = ADC kodu 0..4095, 0 = tetiklemesiz)
//   z          akım sıfırı — YÜK BAĞLI DEĞİLKEN çalıştır
//   v<gercek>  gerilim kalibresi — multimetrenin okuduğu değeri yaz
//   i<gercek>  akım kalibresi   — multimetrenin okuduğu değeri yaz
//   s<ohm>     takılı şöntün değeri (örn. s0.1)

static int32_t ham_ortalama(uint8_t adres, uint8_t kez) {
  int32_t t = 0;
  for (uint8_t i = 0; i < kez; i++) {
    yeni_donusum_bekle(3000);
    t += ads_oku(adres);
  }
  return t / (int32_t)kez;
}

void ayar_yaz_seri() {
  Serial.print(F("A sont="));    Serial.print(ayar.sont_ohm, 6);
  Serial.print(F(" v_duz="));    Serial.print(ayar.v_duzeltme, 6);
  Serial.print(F(" i_duz="));    Serial.print(ayar.i_duzeltme, 6);
  Serial.print(F(" i_ofset="));  Serial.print(ayar.i_ofset);
  Serial.print(F(" v_pga="));    Serial.print(ayar.v_pga, 3);
  Serial.print(F(" i_pga="));    Serial.println(ayar.i_pga, 3);
}

// Breadboard'da bir ADS1115 cevap vermiyorsa sebebi genelde uctan bire
// indirgenir: ADDR pini bosta kalmis, SDA/SCL ters, ya da pull-up yok.
// Tarama bunu saniyede ayirt ettiriyor — 0x48 ve 0x49 gorunmuyorsa
// sorun kabloda, kalibrasyonda degil.
void i2c_tara() {
  uint8_t bulunan = 0;
  Serial.print(F("I2C:"));
  for (uint8_t a = 0x08; a < 0x78; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.print(F(" 0x"));
      Serial.print(a, HEX);
      bulunan++;
    }
  }
  if (!bulunan) Serial.print(F(" (hicbir cihaz yok)"));
  Serial.println();
  Serial.print(F("  beklenen: 0x48 (akim)  0x49 (gerilim) — bulunan "));
  Serial.println(bulunan);
}

void komut_calistir(const char *s) {
  switch (s[0]) {
    case '?':
      ayar_yaz_seri();
      break;

    case '#':
      i2c_tara();
      break;

    /* Osiloskop. `t` tek başına yakalar; `t<sayı>` eşiği de ayarlar
     * (Aşama 1 uyumluluğu). İkinci karakter harfse ayar komutudur. */
    case 't': {
      char alt = s[1];
      if (alt == 0 || (alt >= '0' && alt <= '9')) {
        if (alt) skop_ayar.esik = (uint16_t)atoi(s + 1);
        skop_yolla();
      } else if (alt == '?') {
        skop_ayar_yaz();
      } else if (alt == 'a') {                    /* otomatik kurulum */
        if (skop_otomatik()) {
          skop_ayar_yaz();
          skop_yolla();
        } else {
          Serial.println(F("! otomatik kurulum: periyodik sinyal yok"));
        }
      } else if (alt == 'b') {                    /* zaman tabanı */
        int v = atoi(s + 2);
        if (v >= 0 && v < SKOP_TDIV_SAYI) {
          skop_ayar.tdiv = (uint8_t)v;
          skop_ayar_yaz();
        } else {
          Serial.print(F("! tdiv 0.."));
          Serial.println(SKOP_TDIV_SAYI - 1);
        }
      } else if (alt == '+') {                    /* bir kademe yavaşlat */
        if (skop_ayar.tdiv + 1 < SKOP_TDIV_SAYI) skop_ayar.tdiv++;
        skop_ayar_yaz();
      } else if (alt == '-') {                    /* bir kademe hızlandır */
        if (skop_ayar.tdiv > 0) skop_ayar.tdiv--;
        skop_ayar_yaz();
      } else if (alt == 'l') {                    /* tetik seviyesi */
        int v = atoi(s + 2);
        if (v >= 0 && v <= 4095) { skop_ayar.esik = (uint16_t)v; skop_ayar_yaz(); }
        else Serial.println(F("! esik 0..4095"));
      } else if (alt == 'e') {                    /* kenar */
        skop_ayar.kenar = (atoi(s + 2) != 0) ? 1u : 0u;
        skop_ayar_yaz();
      } else if (alt == 'h') {                    /* histerezis */
        int v = atoi(s + 2);
        if (v >= 0 && v <= 2000) { skop_ayar.histerezis = (uint16_t)v; skop_ayar_yaz(); }
        else Serial.println(F("! histerezis 0..2000"));
      } else if (alt == 'p') {                    /* ön-tetik yüzdesi */
        int v = atoi(s + 2);
        if (v >= 0 && v <= 90) { skop_ayar.on_yuzde = (uint8_t)v; skop_ayar_yaz(); }
        else Serial.println(F("! on-tetik 0..90"));
      } else if (alt == 'm') {                    /* kip */
        int v = atoi(s + 2);
        if (v >= 0 && v <= 2) { skop_ayar.kip = (uint8_t)v; skop_ayar_yaz(); }
        else Serial.println(F("! kip 0=oto 1=normal 2=tek"));
      } else {
        Serial.println(F("! skop: t ta tb tl te th tp tm t? t+ t-"));
      }
      break;
    }

    case 'z': {
      ayar.i_ofset = (int16_t)ham_ortalama(ADS_AKIM, 32);
      ayar_kaydet();
      Serial.print(F("ok i_ofset="));
      Serial.println(ayar.i_ofset);
      break;
    }

    case 'v': {
      float gercek = atof(s + 1);
      float olculen = olc_gerilim((int16_t)ham_ortalama(ADS_GERILIM, 32), &ayar);
      if (gercek > 0.0f && olculen > 0.0f) {
        ayar.v_duzeltme *= gercek / olculen;
        ayar_kaydet();
        Serial.print(F("ok v_duzeltme="));
        Serial.print(ayar.v_duzeltme, 6);
        Serial.print(F("  (olculen "));
        Serial.print(olculen, 4);
        Serial.println(F(" V)"));
      } else {
        Serial.println(F("! gecersiz: gerilim uygula ve gercek degeri yaz"));
      }
      break;
    }

    case 'i': {
      float gercek = atof(s + 1);
      float olculen = olc_akim((int16_t)ham_ortalama(ADS_AKIM, 32), &ayar);
      if (gercek > 0.0f && olculen > 0.0f) {
        ayar.i_duzeltme *= gercek / olculen;
        ayar_kaydet();
        Serial.print(F("ok i_duzeltme="));
        Serial.print(ayar.i_duzeltme, 6);
        Serial.print(F("  (olculen "));
        Serial.print(olculen, 5);
        Serial.println(F(" A)"));
      } else {
        Serial.println(F("! gecersiz: akim akitip gercek degeri yaz"));
      }
      break;
    }

    case 's': {
      float r = atof(s + 1);
      if (r > 0.0f) {
        ayar.sont_ohm = r;
        ayar_kaydet();
        Serial.print(F("ok sont_ohm="));
        Serial.println(ayar.sont_ohm, 6);
      } else {
        Serial.println(F("! gecersiz sont degeri"));
      }
      break;
    }

    default:
      Serial.println(F("! bilinmeyen komut — ? yazin"));
  }
}

// Satır sonu için CR (13) ve LF (10) sayısal olarak yazılı: kaynak dosyada
// kaçış dizisi bulundurmamak, bu projeyi üreten betiklerin geçmişte
// ters bölüyü yiyip dosyayı bozmasından sonra alınmış bir önlem.
void komut_isle() {
  static char tampon[24];
  static uint8_t uz = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == 10 || c == 13) {
      tampon[uz] = 0;
      if (uz) komut_calistir(tampon);
      uz = 0;
    } else if (uz < sizeof(tampon) - 1) {
      tampon[uz++] = c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  ayar_yukle();

  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  ads_kur(ADS_AKIM, 0x0000, ayar.i_pga);      // AIN0-AIN1 diferansiyel
  ads_kur(ADS_GERILIM, 0x4000, ayar.v_pga);   // AIN0 tekli

  // ALERT/RDY pinini DONUSUM HAZIR cikisi yap.
  //
  // NEDEN: 400 kHz I2C'de saniyede ~3000 cift okuyabiliyoruz ama ADC
  // saniyede 860 donusum yapiyor. Beklemeden okursak AYNI donusumu
  // 3-4 kez okuruz. Ortalama bozulmaz ama "kac ornek" sayisi YALAN olur:
  // 600 okumanin sqrt'i 24x bastirma gibi gorunur, gercekte 172 benzersiz
  // ornek var ve bastirma 13x'tir. Arayuz de bu yanlis sayiyi gosterir.
  //
  // Veri sayfasi 7.3.8: Hi_thresh MSB=1, Lo_thresh MSB=0 yazilinca pin
  // her donusum sonunda ~8 us darbe veriyor.
  ads_yaz(ADS_AKIM, ADS_UST, 0x8000);
  ads_yaz(ADS_AKIM, ADS_ALT, 0x0000);
  pinMode(PIN_HAZIR, INPUT_PULLUP);

  // Oneshot (analogRead) ile sürekli sürücü ADC1'i paylaşamaz;
  // osiloskop DMA kullandığı için oneshot ayarı hiç kurulmuyor.
  skop_kur();

  if (WIFI_AD[0]) {
    WiFi.begin(WIFI_AD, WIFI_SIFRE);
    for (uint8_t i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  }
  sunucu.on("/", kok_sayfa);
  sunucu.on("/akis", akis_sayfa);
  sunucu.begin();

  son_us = micros();
  Serial.println();
  Serial.println(F("Olcum Karti — Asama 2 (ESP32-S3 + ADS1115)"));
  Serial.print(F("  tam olcek "));
  Serial.print(tam_olcek_volt(ayar.v_pga), 2);
  Serial.print(F(" V, adim "));
  Serial.print(adim_volt(ayar.v_pga) * 1e6f, 1);
  Serial.println(F(" uV"));
  // PSRAM DURUMU — sessiz kalmasi yasak (DEVIR 4.9).
  //
  // FQBN'de PSRAM=opi yoksa ps_malloc() NULL doner ve derin skop bellegi
  // HIC ayrilmaz; uzerine hata mesaji da olmadigi icin sebebi gorunmez.
  // Derlemenin PSRAM'li olmasi kartta PSRAM BULUNDUGUNU kanitlamaz —
  // kanit bu satirdir. "yok" goruyorsan uretim/hedef2.py'ye bak.
  Serial.print(F("PSRAM: "));
  if (psramFound()) {
    Serial.print(ESP.getPsramSize() / 1024);
    Serial.println(F(" KB"));
  } else {
    Serial.println(F("YOK — derin skop bellegi kullanilamaz "
                     "(hedef2.py: PSRAM=opi mi?)"));
  }
  Serial.println(F("Cikis bicimi: D <volt> <amper> <watt> <joule> <wh> <ms> <ornek>"));
  Serial.println(F("Komutlar: ?  #  z  v<gercek>  i<gercek>  s<ohm>"));
  Serial.println(F("Skop: t yakala · ta otomatik · tb<0-11> zaman tabani · t+ t-"));
  Serial.println(F("      tl<0-4095> esik · te<0/1> kenar · th<hist> · tp<%> · tm<kip> · t?"));
  if (!skop_kulp) Serial.println(F("! osiloskop suruculu kurulamadi"));
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(F("  http://")); Serial.println(WiFi.localIP());
  }
}

void loop() {
  sunucu.handleClient();
  komut_isle();

  // WiFi bağlı değilken de seri porttan aynı biçimi yayınla
  if (!yeni_donusum_bekle(3000)) return;      // yalniz BENZERSIZ ornek say
  Okuma2 o = olcum_al();
  enerji_biriktir(o.watt);
  v_top += o.volt; i_top += o.amper; w_top += o.watt; ornek++;

  if (millis() - son_rapor >= rapor_ms) {
    son_rapor = millis();
    uint32_t n = ornek ? ornek : 1;
    snprintf(son_satir, sizeof(son_satir),
             "D %.3f %.5f %.5f %.4f %.7f %lu %lu",
             (double)(v_top / n), (double)(i_top / n), (double)(w_top / n),
             (double)enerji_joule(enerji_pJ), (double)enerji_wh(enerji_pJ),
             (unsigned long)son_rapor, (unsigned long)n);
    Serial.println(son_satir);
    v_top = i_top = w_top = 0;
    ornek = 0;
  }
}
