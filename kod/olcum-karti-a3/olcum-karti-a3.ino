/*
 * Olcum Karti — Asama 3  (ESP32-S3 + 2x ADS1115, CIFT YONLU on uc)
 *
 * ASAMA 2'DEN FARKLAR:
 *   * Gerilim CIFT YONLU: bolucularin alt ucu GND'ye degil tamponlu
 *     Vref'e gidiyor, ADS diferansiyel okuyor -> isaretli sonuc.
 *   * IKI gerilim kanali: NORMAL +-32.4 V (AIN0-AIN1) ve
 *     YUKSEK +-613.7 V (AIN2-AIN3), ikisi de ADS #2'de.
 *   * Akim CIFT YONLU: Asama 2'nin `if (amper < 0) amper = 0;` kirpmasi
 *     kaldirildi. Guc elektroniginde bobin akimi ters doner.
 *   * Enerji ISARETLI (int64): sarj/desarj cevriminde net sifir verir.
 *   * Kalibrasyon AYRISIK: ofset HAM KOD olarak saklaniyor, kazanctan
 *     bagimsiz. Asama 3 taslaginda volt olarak saklaniyordu ve iki
 *     kalibrasyon birbirini bozuyordu (B4 yakaladi).
 *   * PGA oto-kademesi YOK: ADS'in giris empedansi PGA ile degistigi
 *     icin tamponsuz bolucude kademe sinirinda %0.67 puan kazanc
 *     sicramasi oluyordu (DEVIR 4.14). Tampon eklendi ama kademe yine
 *     de sabit tutuluyor — menzil zaten iki kanala bolunmus durumda.
 *
 * PINLER
 *   GPIO8  SDA        GPIO9  SCL
 *   GPIO4  ADC1_CH3   <- osiloskop, ayri bolucu + Sallen-Key
 *   GPIO7  ADS #1 ALERT/RDY (donusum hazir)
 *
 * ADRESLER
 *   0x48  ADS #1  AIN0-AIN1 diferansiyel  -> AKIM (sont, Kelvin)
 *   0x49  ADS #2  AIN0-AIN1               -> GERILIM normal
 *                 AIN2-AIN3               -> GERILIM yuksek
 *
 * !!! KART IZOLE DEGIL. 615 V kanali sebeke referansli bir devreye
 *     BAGLANMAZ — USB uzerinden bilgisayara sebeke tasir.
 *
 * Tum sabitler uretim/tasarim3_sabit.py ile ayni; test_olcum3.py bunu
 * her kosuda siniyor.
 *
 * ─────────────────────────────────────────────────────────────────────
 * OSILOSKOP BOLUMU HAKKINDA — DURUST NOT
 *
 * Asagidaki osiloskop SURUCUSU (DMA kurulumu, tetikleme, yakalama,
 * `skop_yolla`, `skop_komut`) Asama 2'nin .ino dosyasindan KOPYALANDI.
 * Davranis degismedi; A5 orada dogrulanmis durumda.
 *
 * Osiloskop MATEMATIGI (SkopOlcum / skop_olc) ayri: `skop_olc.h`
 * olcum2.h'den URETILIYOR ve `uretim/test_skop_ayni.py` iki kopyanin
 * birebir ayni oldugunu her kosuda siniyor.
 *
 * SURUCU icin boyle bir denetim YOK. Yani A2'nin surucusu degisirse
 * buradaki kopya sessizce eskir. Bilerek kabul edildi cunku:
 *   * Asama 3 donanimi Asama 2'nin yerini aliyor; A2 artik regresyon
 *     temeli olarak tutuluyor, gelistirilmiyor.
 *   * Surucu zaten Asama 3'te degisecek (PSRAM'li derin bellek, ikili
 *     aktarim — DEVIR 4.11).
 * Surucu degistirilecegi gun bu not silinmeli.
 *
 * BU DOSYA ARTIK KAYNAKTIR. Ilk surumu parcalardan birlestirilerek
 * uretildi, ama o gecici bir onyukleme adimiydi — bundan sonra dogrudan
 * burasi duzenlenir.
 * ─────────────────────────────────────────────────────────────────────
 */
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <LittleFS.h>   // B22.5 — arayuz goruntusu

#include "esp_adc/adc_continuous.h"

#include "olcum3.h"
#include "skop_olc.h"   // SkopOlcum, skop_olc (olcum2.h kopyasi)
#include "tipler3.h"
#include "pil_test.h"
#include "web_satir.h"  // B22.4 — satir bolucu (AVR'de sinaniyor)
#include "web_akis.h"   // B22.4 — Serial aynasi
/* 🔴 B34 — ESP32 ADC'si DOGRUSAL DEGIL ve bu OLCULDU (2026-09-12).
   PWM+RC ile uretilen bilinen DC'ye karsi ham kod supuruldu: en kucuk
   kareler dogrusundan sapma %5..%85 araliginda ±76 kod (±61 mV), %85
   ustunde +290 koda kadar cikiyor. Skopun gerilim ekseni bugun TAM
   DOGRUSAL varsayiyor (`SKOP_ADIM` sabit carpan).
   Espressif her yongaya eFuse'ta bir egri kalibrasyonu yaziyor; bu
   basligi kullanip `c<ham>` komutuyla ham kodun kalibre karsiligini
   sorabiliyoruz. Boylece "egri ADC'nin mi, kaynagin mi" sorusu
   KAYNAK DEGISTIRMEDEN yanitlanabiliyor. */
#include "driver/gpio.h"        // B37 — bos pin sinamasi (dahili cekme)
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "ag.h"         // B22.4 — WiFi durum makinesi

// 🔴 B22.4 — `Serial` AYNASI. BUTUN #include'lardan SONRA gelmeli.
//
// Nesne olusturulurken `Serial` HALA gercek HardwareSerial'i gostermeli,
// bu yuzden tanim makrodan ONCE. Makrodan sonra `.ino`'daki 245 `Serial.`
// cagrisinin HEPSI aynaya gidiyor ve cagri yerlerinin hicbiri degismiyor.
//
// Cozdugu kusur: SSE yalnizca `D` satirini tasiyordu; `S2`/`M`/ham skop/
// `E`/`T`/`W`/`B` ve butun `*`/`!` yanitlari WiFi'de GORUNMUYORDU.
static WebAkis CIKIS(Serial);
// ⚠ `#undef` SART: ESP32 cekirdeginde `Serial` ZATEN bir makro
//    (HardwareSerial.h, USB CDC yapilandirmasina gore `Serial0` vb.).
//    Dogrudan yeniden tanimlamak "warning: Serial redefined" veriyor ve
//    bu projede derleme uyarilarina SIFIR tolerans var — `--warnings all`
//    ile derlenip `test_firmware3.py` uyarisizligi IDDIA ediyor.
//    Yukaridaki satirda `Serial` hala GERCEK nesneyi gosteriyor.
#undef Serial
#define Serial CIKIS

// ───────────────────────────────────────────────── pinler ve adresler
static const uint8_t PIN_SDA = 8;
static const uint8_t PIN_SCL = 9;
static const uint8_t PIN_SKOP = 4;          // ADC1_CH3
static const uint8_t PIN_HIZLI_I = 5;       // ADC1_CH4 — hizli akim kanali
static const uint8_t PIN_HAZIR = 7;         // ADS #1 ALERT/RDY
// B21: pil testi MOSFET kapisi. J5'in eski YEDEK pini (10) buraya gidiyor.
// GPIO6 strapping pini DEGIL; acilista giris kipinde, yani kapi R42 ile
// GND'ye cekili ve MOSFET KAPALI. Failsafe daha ilk milisaniyeden gecerli.
static const uint8_t PIN_PIL_KAPI = 6;
/* 🔴 B30 — KALIBRASYON CIKISI (CAL). Her gercek osiloskopta var (Rigol'un
   1 kHz kare dalgasi, prob dengeleme cikisi). Burada iki ise yariyor:
     1. LEHIMSIZ DOGRULAMA: skop zinciri (12 bit DMA ADC + tetik + zaman
        tabani + olcum matematigi) bugune kadar hic BILINEN bir sinyalle
        sinanmadi — yalnizca benzetimde. Tek atlama teliyle sinanir.
     2. Prob/giris dengeleme: on uc kurulunca RC dengesi buradan bakilir.
   GPIO10: strapping DEGIL, oktal PSRAM'in (GPIO35-37) ve USB'nin
   (GPIO19/20) disinda, semada da bos. Acilista KAPALI — bir sinyal
   kaynagi kendiliginden surmemeli. */
static const uint8_t PIN_CAL = 10;
static uint32_t cal_hz = 0;          // 0 = kapali
/* 🔴 B33 — COZUNURLUK DONANIMA SORULUYOR, VARSAYILMIYOR.
   `ledcAttach(pin, 50000, 10)` bu kartta BASARISIZ oluyor ("requested
   frequency 50000 and duty resolution 10 can not be achieved"), ama
   dusuk frekansta baglanip sonra `ledcChangeFrequency(50000)` cagirinca
   50000 DONUYORDU — yani API iki yoldan iki farkli cevap veriyor ve
   biri yaniltici. Cozum: en yuksek cozunurlukten baslayip TUTANI bul,
   hangisinin tuttugunu da bildir. Gorev orani o cozunurluge gore
   olceklenecek — sabit 1023 varsaymak sessizce yanlis duty verirdi. */
static uint8_t cal_cozunurluk = 0;   // bit; 0 = bagli degil
static const uint8_t ADS_AKIM = 0x48;       // ADDR -> GND
static const uint8_t ADS_GERILIM = 0x49;    // ADDR -> VDD

// 🔴 B22.4: WIFI_AD / WIFI_SIFRE SABITLERI KALDIRILDI.
// Ikisi de bos dizeydi, yani `WiFi.begin()` HIC cagrilmiyordu: kartin
// WiFi'si bugune kadar hic acilmadi. Artik `ag.h` yonetiyor ve kimlik
// bilgileri NVS'te (`olcumag` ad alani) duruyor — kaynak koda parola
// yazmak, ikilide duz metin sir birakmak demekti (zincir bunu denetliyor).

// ───────────────────────────────────────────────── ADS1115 sürücüsü
static const uint8_t ADS_DONUSUM = 0x00;
static const uint8_t ADS_AYAR    = 0x01;
static const uint8_t ADS_ALT     = 0x02;   // Lo_thresh
static const uint8_t ADS_UST     = 0x03;   // Hi_thresh

static const uint16_t ADS_SUREKLI  = 0x0000;   // MODE = 0, sürekli
static const uint16_t ADS_TEK      = 0x0100;   // MODE = 1, tek atış
static const uint16_t ADS_BASLAT   = 0x8000;   // OS = 1
static const uint16_t ADS_860SPS   = 0x00E0;   // DR = 111

// 🔴 B20 (2026-09-10) — COMP_QUE, ALERT/RDY'yi KAPATIYORDU.
//
// Eskiden burada tek bir sabit vardi: ADS_KOMP_KAPALI = 0x0003, yani
// COMP_QUE = 11b. TI SBAS444E 7.3.8 bunu acikca yasakliyor:
//     "Set the COMP_QUE[1:0] bits to any 2-bit value other than 11b
//      to keep the ALERT/RDY pin enabled"
// ve yazmac tablosu 11b icin: "Disable comparator and set ALERT/RDY
// pin to high-impedance (default)".
//
// setup() Hi_thresh = 0x8000 / Lo_thresh = 0x0000 yazip pini DONUSUM
// HAZIR cikisi yapiyordu — ama HER ayar yazmasi COMP_QUE = 11b ile
// pini yeniden yuksek empedansa aliyordu. Sonuc: pin INPUT_PULLUP ile
// hep HIGH okunuyor, yeni_donusum_bekle HER cagrida 4000 us zaman
// asimina dusuyordu. Olculdu (uretim/sim3_bant.py): dongu periyodu
// 11.0 ms, yani 91 SPS — firmware'in her yerde yazdigi 860 SPS'in
// ONDA BIRI. B17'nin butun frekans butcesi bu hiza dayaniyordu.
//
// COMP_QUE = 00b: komparator etkin, BIR donusumden sonra assert.
// Esik yazmaclari zaten RDY kipine ayarli oldugu icin komparator
// islevi devreye girmiyor; tek etkisi pinin ETKIN kalmasi.
static const uint16_t ADS_KOMP_TEK    = 0x0000;   // COMP_QUE = 00b, RDY ETKIN
static const uint16_t ADS_KOMP_KAPALI = 0x0003;   // COMP_QUE = 11b, pin YUKSEK-Z

// MUX secimleri — HEPSI DIFERANSIYEL (tekli yok, cift yonluluk buna bagli)
static const uint16_t MUX_01 = 0x0000;     // AIN0 - AIN1
static const uint16_t MUX_23 = 0x3000;     // AIN2 - AIN3

static uint16_t pga_bitleri(float pga) {
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

/* 🔴 B27/K1 (2026-09-12, GERCEK KARTTA gorüldu) — YANIT VERMEYEN ADC
   SESSIZCE 0 DONUYORDU. Kalibrasyon o sifira uygulaniyor ve ekranda
   kendinden emin bir "1.716 V" cikiyordu:

       V = (0 - n_sifir) * adim = (0 - (-1646)) * 1.0423 mV = 1.7156 V

   Yani gosterilen sayi ters cevrilmis sifir-ofset sabitiydi, olcum degil.
   Cip takili degilken de, cip BOZULDUGUNDA da, kablo CIKTIGINDA da AYNI
   sahte sayi. Arayuz "veri yok" ile "veri sifir"i ayirt edemiyordu.

   Artik her okuma kendi cipinin hata bitini kuruyor/temizliyor; `D`
   satirina `durum` alani eklendi (bit0 = GERILIM okunamadi, bit1 = AKIM
   okunamadi), enerji hatali ornekle BIRIKTIRILMIYOR. */
static uint8_t ads_hata = 0;            /* son turun okuma hatalari */
static uint8_t ads_hata_pencere = 0;    /* rapor penceresinde BIRIKEN */
#define ADS_HATA_V 0x01
#define ADS_HATA_I 0x02

static int16_t ads_oku(uint8_t adres) {
  const uint8_t bit = (adres == ADS_GERILIM) ? ADS_HATA_V : ADS_HATA_I;
  Wire.beginTransmission(adres);
  Wire.write(ADS_DONUSUM);
  Wire.endTransmission();
  Wire.requestFrom(adres, (uint8_t)2);
  if (Wire.available() < 2) {
    ads_hata |= bit;
    ads_hata_pencere |= bit;
    return 0;
  }
  ads_hata &= ~bit;
  uint16_t h = Wire.read();
  uint16_t l = Wire.read();
  return (int16_t)((h << 8) | l);
}

// B20: `komp` alani ADS_KOMP_TEK (RDY etkin) ya da ADS_KOMP_KAPALI.
// ALERT/RDY yalnizca AKIM cipinde (U6) telli; GERILIM cipinin (U7)
// ALERT ucu netliste bilerek bostur (netlist3_dogrula.py: unconnected-
// (U7-ALERT{slash}RDY-Pad2)). O yuzden RDY'yi yalnizca gereken cipe
// aciyoruz — bos bir cikisi surmenin anlami yok.
static void ads_kur(uint8_t adres, uint16_t mux, float pga, bool surekli) {
  uint16_t a = ADS_BASLAT
             | mux
             | pga_bitleri(pga)
             | (surekli ? ADS_SUREKLI : ADS_TEK)
             | ADS_860SPS
             | (adres == ADS_AKIM ? ADS_KOMP_TEK : ADS_KOMP_KAPALI);
  ads_yaz(adres, ADS_AYAR, a);
}

// ───────────────────────────────────────────────── durum
// `Ayar3` ve `varsayilan_ayar3` tipler3.h icinde — Arduino'nun otomatik
// prototipleri struct tanimindan once yerlestigi icin (bkz. tipler3.h).
static Ayar3 ayar;
static Preferences kalici;
static WebServer sunucu(80);

// B22.5 — arayuz goruntusu LittleFS'te mi? Acilista bir kez ogreniliyor.
// `kok_sayfa` bundan SONRA tanimli oldugu icin bildirim burada olmali.
static bool fs_hazir = false;

// SSE satir sayaci. `skop.bin` basligi da kullaniyor (dokumun akista
// nereye denk geldigini soyluyor), o yuzden bildirimi burada.
static uint32_t akis_sira = 0;

// ───────────────────────────────────────────────── B21 pil testi
static PilTest  pil;
static PilHalka pil_halka;
// Ic RAM tamponu. PSRAM bulunursa setup() 24 saate buyutuyor.
//
// ⚠ NEDEN 2 SAAT DEGIL 1.5 SAAT: 2 saatlik tampon (7200 nokta = 86 KB)
//   RAM kullanimini %42'ye cikariyor ve projenin kendi "RAM < %40"
//   kuralini ASIYOR (test_firmware3.py bunu YAKALADI). 5400 nokta =
//   64.8 KB ile toplam %35'te kaliyor ve WiFi yigini + skop tamponu
//   icin pay kaliyor. Sinir donanimdan geliyor, tercihten degil.
#define PIL_IC_KAPASITE 5400u
// 🔴 B22.1: Eskiden STATIK diziydi (`static PilNokta pil_ic_tampon[...]`).
// PSRAM bulununca halka PSRAM'e tasiniyor ama statik dizi serbest
// BIRAKILAMIYOR: 5400 x 12 = 64 800 B ic RAM (toplam RAM'in %20'si,
// bos yigin payinin ~%31'i) OLU kaliyordu. Artik yigindan aliniyor ve
// yalnizca gercekten kullanilacaksa ayriliyor. Ayirma setup()'ta,
// PSRAM durumu bilindikten SONRA tek yerde yapiliyor.
static PilNokta *pil_ic_tampon = nullptr;

static int64_t  enerji_pJ = 0;
static uint32_t son_us = 0;
/* B27 A2 — RAPOR ARALIGI kullanici tarafindan secilebilir (`r<ms>`).
   ADC ~465 ornek/s aliyor; D satiri bu araligin ORTALAMASI. Sinirlar:
   EN_AZ 20 ms = 50 satir/s. Her satir, bagli SSE istemcisi basina bir
   TCP yazma demek ve bu yazma OLCUM DONGUSUNUN ICINDE kosuyor (web
   sunucusu loop()'ta, cift cekirdek henuz yok). 20 ms altinda dongu
   satir basmaktan olcum alamaz hale gelir. EN_COK 5000 ms: daha
   seyrek rapor icin bir gerekce yok, arayuz "koptu" sanir.
   NVS'e YAZILMIYOR — oturumluk tercih; arayuz baglaninca kendi
   tercihini yolluyor (K5 deseni: kart soyler, arayuz uyar). */
#define RAPOR_MS_EN_AZ   20
#define RAPOR_MS_EN_COK  5000
#define RAPOR_MS_VARSAYILAN 200
static uint32_t rapor_ms = RAPOR_MS_VARSAYILAN;
static uint32_t son_rapor = 0;

/* ── B22.1: BLOKAJ GORUNURLUGU ─────────────────────────────────────
 * Web sunucusu olcum dongusunun ICINDE kostugu icin her HTTP istegi
 * loop()'u blokluyor. Blokaj 1 s'yi gecerse enerji_biriktir o araligi
 * TAMAMEN ATIYOR ve bu SESSIZDI — B20 bunu 1 dk @ 25 W = 0.42 Wh (%100)
 * olarak olcmustu ama kart calisirken gorunur bir izi yoktu.
 * Bu uc sayac `K` satiriyla disari veriliyor. Cift cekirdek kararinin
 * esigi de bunlar: loop_azami_us > 20 000 ise gorev ayrimi yapilir. */
static uint32_t loop_azami_us = 0;     /* gorulmus en uzun dongu turu */
static uint32_t loop_uzun_adet = 0;    /* > 20 ms suren tur sayisi */
static uint32_t enerji_kayip_ms = 0;   /* dt > 1 s yuzunden ATLANAN sure */
static uint8_t  k_degisti = 0;

static uint32_t ornek = 0;
static float v_top = 0, i_top = 0, w_top = 0;
static char son_satir[160] = "";

static Kanal3 *etkin_kanal() {
  return ayar.menzil ? &ayar.yuksek : &ayar.normal;
}

static uint16_t etkin_mux() {
  return ayar.menzil ? MUX_23 : MUX_01;
}

// ───────────────────────────────────────────────── ayar saklama
void ayar_yukle() {
  kalici.begin("olcum3", false);
  size_t n = kalici.getBytesLength("ayar");
  if (n == sizeof(Ayar3)) {
    kalici.getBytes("ayar", &ayar, sizeof(Ayar3));
  }
  // B20: imza tipler3.h'deki AYAR3_IMZA'dan geliyor. Eskiden burada ve
  // ayar_kaydet'te elle 0xC0F3 yaziliydi, oysa varsayilan_ayar3 0xC0F4
  // koyuyordu — B17 imzayi yarim degistirmis, surum damgasi olmustu.
  if (ayar.imza != AYAR3_IMZA) varsayilan_ayar3(&ayar);
}

void ayar_kaydet() {
  ayar.imza = AYAR3_IMZA;
  kalici.putBytes("ayar", &ayar, sizeof(Ayar3));
}

// ───────────────────────────────────────────────── ölçüm
// Yeni bir donusumun bitmesini bekler. Zaman asimi varsa yine de okur
// (ALERT pini baglanmamis olabilir) ama o zaman sayim guvenilmez.
/* 🔴 B26 (2026-09-11, GERCEK KARTTA OLCULDU) — KENAR YONU TERSTI.
 *
 * Eskiden once DUSMEYI, sonra KALKMAYI bekliyordu:
 *     while (... == HIGH) {}   // dus
 *     while (... == LOW)  {}   // kalk   <- BU HIC GELMEZ
 *
 * ADS1115'in ALERT/RDY pini bu yapilandirmada (Hi=0x8000, Lo=0x0000,
 * COMP_QUE=00) donusum bitince LOW'a cekiyor ve OYLE KALIYOR. Pini
 * geri kaldiran sey YENI DONUSUMU BASLATAN AYAR YAZMASI — donusum
 * yazmacini okumak DEGIL. Tezgahta olculdu:
 *
 *     RDY dustu: EVET @1228 us   |  kalkti: HAYIR
 *     okuma oncesi: LOW  |  okuma sonrasi: LOW      <- okuma kaldirmiyor
 *
 * Yani ikinci dongu her cagrida 4000 us zaman asimina dusuyor, sonra
 * cagiran taraf 1300 us daha bekliyordu. Olculen tur suresi 6.17 ms,
 * yani 162 ornek/s — firmware'in her yerde yazdigi 665'in DORTTE BIRI.
 *
 * ⚠ B20 bu pinin B I R kusurunu duzeltmisti (COMP_QUE=11b pini yuksek
 * empedansta birakiyordu, 91 SPS). O duzeltme DOGRUYDU ama YETMIYORDU:
 * kenar yonu hatasi altinda duruyordu ve donanim olmadigi icin kimse
 * 665'i gercekten olcmemisti. "Yesil test bir sey kanitlamaz"in bir
 * baska bicimi: duzeltilmis bir kusurun ARKASINDA ikinci bir kusur.
 *
 * DOGRU SIRA: once pinin KALKTIGINI dogrula (ayar yazmasi yeni donusumu
 * baslatti), sonra DUSMESINI bekle (donusum bitti). Ters sira teorik bir
 * yarisa da aciktir: ayar yazmasi bitmeden pin hala LOW iken bakilirsa
 * ONCEKI donusum okunur ve "kac ornek" sayisi yine yalan olur.
 *
 * Tezgahta olculen (tek ADS, 300 tur): 1614 us/tur, 620 ornek/s,
 * her iki dongude de SIFIR zaman asimi.
 */
bool yeni_donusum_bekle(uint32_t azami_us) {
  uint32_t t0 = micros();
  while (digitalRead(PIN_HAZIR) == LOW) {        /* yeni donusum basladi mi */
    if (micros() - t0 > azami_us) return false;
  }
  while (digitalRead(PIN_HAZIR) == HIGH) {       /* donusum bitti mi */
    if (micros() - t0 > azami_us) return false;
  }
  return true;
}

// ── B20: hizalama tamponlari BURADA tanimli, menzil_uygula onlara
//    dokundugu icin. (Onceki surumde olcum_al'in hemen ustundeydiler.)
//
// Hizalama tamponlari — en eski [0], en yeni [3].
static float hv_tampon[4] = {0, 0, 0, 0};
static float hi_tampon[4] = {0, 0, 0, 0};
static uint8_t tampon_dolu = 0;

// B20: her gerilim gozunun DOYUP doymadigi. bit0 = en yeni ([3]),
// bit3 = en eski ([0]). Menzil degisince tamponda KALACAK olanlar
// [1..3], yani bit 0..2 -> maske 0x07.
static uint8_t hv_doydu = 0;

static void tampona_it(float *t, float x) {
  t[0] = t[1]; t[1] = t[2]; t[2] = t[3]; t[3] = x;
}

// Bu ham kod tam olcege DAYANDI mi?
// Iki kelepce var ve UST tarafta yazilim kelepcesi ONCE giriyor:
// olc_gerilim3, d = ham - sifir_ham hesapliyor ve sifir_ham NEGATIF
// oldugu icin d, ADS doymadan once int16'yi tasiriyor (NORMAL kanalda
// ham > 31121'de, yani girisde 34.15 V'ta; ADS ise 35.87 V'ta doyuyor).
// Ikisini de doygunluk sayiyoruz — ikisinde de okunan deger YANLIS.
static bool gerilim_doydu(int16_t ham, const Kanal3 *k) {
  int32_t d = (int32_t)ham - (int32_t)k->sifir_ham;
  return ham == 32767 || ham == -32768 || d > 32767 || d < -32768;
}

// Gerilim kanali degisince ADS'in MUX'unu yeniden yaz ve bir donusum al.
//
// 🔴 B20 (2026-09-10). Bu fonksiyonun eski yorumu soyleydi:
//     "ILK donusumu AT. Kademe/kanal degisiminden sonraki ilk donusum
//      ESKI ayara ait olabilir."
// GEREKCE YANLIS, KOD DOGRU — ikisini karistirmayalim:
//   * Gerekce SUREKLI kip varsayimindan kalma. TI SBAS444E 7.4.2.2
//     "when writing new configuration settings, the currently ongoing
//     conversion completes with the previous configuration settings"
//     derken SUREKLI kipi anlatiyor. 7.4.2.1'e gore TEK ATIS kipinde
//     donusum, OS = 1 yazildigi ANDAKI yapilandirmayla basliyor;
//     ESKI ayarli bir ornek OLUSMUYOR.
//   * Ama okuma yine de SART, baska bir sebeple: ads_kur'un kendisi
//     ADS_BASLAT (OS = 1) yaziyor, yani BIR DONUSUM BASLATIYOR. Ayni
//     bolum "writing a 1b to the OS bit while a conversion is ongoing
//     has no effect" diyor — o donusum BOSALTILMAZSA olcum_al'in bir
//     sonraki ads_tek_atis_baslat'i YOK SAYILIR ve gerilim ornegi,
//     akim ornegiyle arasindaki 95 us'lik BILINEN kaymayi kaybedip
//     bir donusum periyoduna (1.16 ms, 50 Hz'te 21 dereceye) kadar
//     one kayar. B17'nin sildigi hata geri gelir.
// Yani delayMicroseconds(1300) + ads_oku ikilisi KALMALI.
//
// Okuma artik ATILMIYOR: hizalama tamponunu TAZELEMEK icin kullaniliyor.
// Menzil degistiginde hv_tampon'un uc gozu hala ESKI kanalin olcumunu
// tasiyor ve hizalayici onlari 3 olcum (3.49 ms) boyunca cikisa
// katmaya devam ediyor. Eski kanal DOYMUSSA — ki otomatik menzil zaten
// bunun icin tetikleniyor — o uc ornek tam olcekte takili kalir.
// Olculdu (uretim/sim3_menzil.py): 20 V -> 200 V basamaginda gecis
// basina enerji sayaci %1.90, 20 V -> 500 V'ta %2.13 kaybediyordu;
// tazeleme bu hatayi TAM sifire indiriyor.
//
// NEDEN DOLDURMA, `tampon_dolu = 0` DEGIL: tampon_dolu sifirlanirsa
// olcum_al 3 tur boyunca yedek yola dusup HAM ornek dondurur; cikisin
// temsil ettigi an 2 ornek ILERI sicrar, sonra geri doner ve dalga
// seklinin bir parcasi iki kez sayilir. Olculen enerji hatasi
// doldurmaya gore daha buyuk (en kotu %3.57 / ortalama %0.95 —
// doldurmada %2.44 / %0.69).
//
// NEDEN KOSULLU: eski ornekler DOYMAMISSA onlar zaten dogru
// olcumlerdir; tamponu bosuna tazelemek gerilim ile akimin hizasini
// bir ornek bozar (V, tazeleme aninda; I hala hi_tampon[1] aninda).
// Kosullu tazeleme butun senaryolarda en dusuk hatayi verdi:
// en kotu %1.30 / ortalama %0.25.
static void menzil_uygula() {
  ads_kur(ADS_GERILIM, etkin_mux(), etkin_kanal()->pga, false);
  delayMicroseconds(1300);          // 1/860 s + pay
  int16_t ham = ads_oku(ADS_GERILIM);
  if (tampon_dolu >= 4u && (hv_doydu & 0x07u)) {
    float v = olc_gerilim3(ham, etkin_kanal());
    hv_tampon[0] = hv_tampon[1] = hv_tampon[2] = hv_tampon[3] = v;
    hv_doydu = gerilim_doydu(ham, etkin_kanal()) ? 0x0Fu : 0u;
  }
}

// OTOMATIK MENZIL — iki KANAL arasinda gecis (PGA kademesi DEGIL).
//
// PGA oto-kademesi bilerek yapilmiyor: ADS1115'in giris empedansi PGA ile
// degisiyor (4.9 M -> 710 k) ve bu, kalibrasyonun silemeyecegi bir kazanc
// sicramasi yaratiyor (DEVIR 4.14). Kanal degistirmek ayni sorunu
// yaratmaz cunku her kanalin KENDI kalibrasyonu var.
//
// 🔴 B20 (2026-09-10) — HISTEREZIS AC'DE CALISMIYORDU.
//
// Eski yorum "Aradaki bosluk gidip gelmeyi (chatter) onluyor" diyordu.
// DC'de onluyor, AC'de ONLEMIYOR: esikler ANLIK |v|'ye uygulaniyordu ve
// bir sinusun genligi her yarim cevrimde asagi esigin altina inip tepede
// yukari esigi asiyor. Tepesi 29.2 V'i gecen HER AC sinyalde bu bir
// dongu. Olculdu (uretim/sim3_bant.py bolum 5, 50 Hz sinus):
//     tepe 30 V -> 199 gecis/s · tepe 50 V -> 201 gecis/s
//     50 V tepede orneklerin %31.3'u NORMAL kanalda DOYUYOR,
//     Vrms %12.2 dusuk okunuyor,
//     her gecis menzil_uygula'nin 1518 us'sini odedigi icin ornekleme
//     hizinin %30'u menzil degisimine gidiyor.
// Yani AC'de otomatik menzil kullanilamaz durumdaydi.
//
// COZUM — iki asimetrik karar:
//   YUKARI : ANLIK |v| ile. Hizli olmali, yoksa kanal doyar.
//   ASAGI  : bir sebeke cevrimlik pencerede TUTULAN TEPE ile. Bir
//            sinusun tepesi cevrim boyunca sabittir; anlik degeri degil
//            tepeyi olcunce "asagi in" karari AC'de artik tetiklenmiyor.
// Ustune bir SUSTURMA: gecisten sonra en az bir sebeke cevrimi boyunca
// yeni gecis yok (menzil_uygula'nin 1518 us'sini pesi sira odememek icin).
//
// Bedeli: gercek bir DC dususunde NORMAL'e donus artik anlik degil, en
// cok iki pencere (50 Hz'te 40 ms) sonra. Kabul edilebilir — yukari yon,
// yani doymayi onleyen yon, hala anlik.

// Bir sebeke cevriminde tutulan tepe. Iki pencereli: simdiki pencere
// dolarken oncekinin tepesi de gecerli sayiliyor, boylece pencere
// sinirinda tepe SIFIRLANMIYOR.
static float    tepe_simdi = 0.0f;
static float    tepe_onceki = 0.0f;
static uint32_t tepe_pencere_us = 0;
static uint32_t menzil_kilit_us = 0;

// Sebeke periyodu (us). sebeke_hz = 0 (DC) ise 20 ms varsayiliyor —
// DC'de tepe zaten anlik degere esit oldugu icin secim onemsiz.
static float sebeke_periyot_us() {
  return (ayar.sebeke_hz > 0.0f) ? (1.0e6f / ayar.sebeke_hz) : 20000.0f;
}

static float tepe_guncelle(float m, uint32_t simdi) {
  if (m > tepe_simdi) tepe_simdi = m;
  if ((uint32_t)(simdi - tepe_pencere_us) >= (uint32_t)sebeke_periyot_us()) {
    tepe_onceki = tepe_simdi;
    tepe_simdi = 0.0f;
    tepe_pencere_us = simdi;
  }
  return tepe_onceki > tepe_simdi ? tepe_onceki : tepe_simdi;
}

static void menzil_gozet(float volt) {
  if (!ayar.oto_menzil) return;
  float m = volt < 0.0f ? -volt : volt;
  uint32_t simdi = micros();
  float tepe = tepe_guncelle(m, simdi);
  float normal_fs = tam_olcek_simetrik(&ayar.normal);

  // Susturma: gecisten sonra bir sebeke cevrimi boyunca karar yok.
  if ((float)(uint32_t)(simdi - menzil_kilit_us) < sebeke_periyot_us()) return;

  if (ayar.menzil == 0 && m > 0.90f * normal_fs) {
    ayar.menzil = 1;                 // YUKARI: anlik — doymayi onler
    menzil_uygula();
    menzil_kilit_us = simdi;
  } else if (ayar.menzil == 1 && tepe < 0.70f * normal_fs) {
    ayar.menzil = 0;                 // ASAGI: pencere TEPESI ile
    menzil_uygula();
    menzil_kilit_us = simdi;
  }
}

// ═══════════════════════════════════════════════ B17 — ES ZAMANLI OKUMA
//
// 🔴 B17'NIN BULDUGU KUSUR. Onceki surum sunu yaziyordu:
//     "Iki AYRI ADS1115 oldugu icin V ve I yaklasik es zamanli
//      ornekleniyor."
// Ikinci yarisi dogruydu (tek cip ile kanal degistirmek 1.16 ms
// birakirdi) ama BIRINCISI DEGILDI. Iki cip de SUREKLI kipteydi ve her
// biri KENDI ic osilatoruyla kosuyordu; dongu yalnizca AKIM cipinin
// ALERT'ini bekliyordu. Gerilim ornegi 0 ile bir cevrim arasinda ESKI
// oluyordu — ve ADS1115'in osilator toleransi ±%10 oldugu icin bu
// gecikme SURUKLENIYORDU.
//
// 50 Hz'te karsiligi 0..23 DERECE, gezinen. PF=0.5'te guc %76'ya varan
// olcude dusuk okunabiliyordu (ortalama %37). Bu, B16'nin duzelttigi
// her seyden buyuktu. Olcumler: uretim/sim3_senkron.py.
//
// COZUM: SUREKLI kip birakildi. Her olcumde iki cipe de TEK ATIS
// baslatma komutu ARDI ARDINA yaziliyor. Kalan kayma artik osilator
// farki degil, iki I2C yazmasi arasindaki SABIT sure (~95 us) — ve o
// BILINEN oldugu icin kesirli gecikmeyle SILINEBILIYOR.
//
// GERILIM ONCE baslatiliyor, yani gerilim ornegi t_yaz kadar ERKEN.
// Hizalayici gerilimi t_yaz kadar ILERI tasiyor.
static void ads_tek_atis_baslat(uint8_t adres, uint16_t mux, float pga) {
  // ADS_BASLAT (OS = 1) tek atis kipinde donusumu BASLATIR.
  // B20: RDY yalnizca AKIM cipinde telli — bkz. ads_kur.
  uint16_t a = ADS_BASLAT | mux | pga_bitleri(pga)
             | ADS_TEK | ADS_860SPS
             | (adres == ADS_AKIM ? ADS_KOMP_TEK : ADS_KOMP_KAPALI);
  ads_yaz(adres, ADS_AYAR, a);
}

// Ornek periyodunu OLCUYORUZ, varsaymiyoruz: dongu web sunucusu ve
// komut isleme de yaptigi icin gercek periyot 1/860 s'ten uzun ve
// degisken. Kesirli gecikme d = t_kayma / T_gercek.
static uint32_t son_ornek_us = 0;
static float ornek_periyot_us = 1000000.0f / 860.0f;

// Hizalama tamponlari (hv_tampon / hi_tampon / tampon_dolu / hv_doydu)
// ve tampona_it, menzil_uygula'nin ustunde tanimli — B20'den beri
// menzil_uygula onlara dokunuyor.


/* 🔴 B29 — CEVRIM SURESI NEREYE GIDIYOR: OLCULUYOR, TAHMIN EDILMIYOR.
   Iki ADS takilinca koşucu "ornek 96, beklenen 133" dedi. Tasarim
   butcesi (sim3_bant) 1.49 ms/cevrim diyor, gercek 2.0 ms. Farki
   tahmin etmek yerine cevrimin ucu de ayri sayiliyor:
     t_yaz  iki tek-atis yazmasi
     t_bek  RDY bekleme (donusum suresi)
     t_oku  iki okuma
   `?` ciktisindaki `T` satiri bu uc sayiyi (son 256 cevrimin ortalamasi)
   basar. Sayaclar `K` ile sifirlanir. */
static uint32_t faz_yaz_top = 0, faz_bek_top = 0, faz_oku_top = 0;
/* B17'nin dersi: iki cip ARASINDAKI baslatma kaymasi, gucun dogrulugunu
   dogrudan belirliyor (P = V x I; kayma faz hatasi demek). Kod bunu
   zaten olcup Lagrange hizalayicisina veriyor — ama SAYI hic disari
   basilmiyordu. Artik `T` satirinda: kayma_us ve ornek periyoduna orani. */
static uint32_t faz_kayma_top = 0;
static uint32_t faz_adet = 0;
/* 🔴 B30 — RDY ZAMAN ASIMI SAYACI. ALERT teli dususe, `yeni_donusum_bekle`
   HER cevrimde 4000 us zaman asimina dusup 1300 us daha bekliyor: cevrim
   2.05 ms -> 6.17 ms, ornekleme 487 -> 162/s. Kart calismaya DEVAM ediyor,
   sayilar dogru, yalnizca 3 KAT YAVAS — yani sessiz. B20'de bu kusur
   aylarca farkedilmedi. Artik sayiliyor ve `F` satirinda gorunuyor. */
static uint32_t rdy_zaman_asimi = 0;

Okuma3 olcum_al() {
  uint32_t t0 = micros();
  // 1) GERILIM once, AKIM sonra baslatiliyor. Aradaki fark bir I2C
  //    yazmasinin suresi.
  //    🔴 B29: burada "400 kHz'te ~95 us" yaziyordu — BIT SURESI. Iki
  //    cip de takilinca kartta OLCULDU: 152 us. Fark `Wire`in islem
  //    basina sabit maliyeti (bkz. tasarim3_sabit.I2C_ISLEM_EK_US).
  //    Kod zaten VARSAYMIYOR, OLCUYOR — o yuzden guc dogru kaldi. Ama
  //    duzeltme olmasaydi 50 Hz / PF=0.5 yukte hata %8.35 olurdu
  //    (95 us varsayilsaydi bile artik %2.5 kalirdi).
  ads_tek_atis_baslat(ADS_GERILIM, etkin_mux(), etkin_kanal()->pga);
  uint32_t t_yaz_bas = micros();
  ads_tek_atis_baslat(ADS_AKIM, MUX_01, ayar.i_pga);
  uint32_t t_kayma_us = micros() - t_yaz_bas;   // OLCULUYOR, varsayilmiyor
  faz_kayma_top += t_kayma_us;                 /* B29: `T` satirinda */
  uint32_t t1 = micros();

  // 2) Donusumun bitmesini bekle. ALERT/RDY akim cipinde kurulu; o
  //    bittiyse gerilim de bitmistir (once baslatildi, ayni sure).
  if (!yeni_donusum_bekle(4000)) {
    delayMicroseconds(1300);
    rdy_zaman_asimi++;
  }
  uint32_t t2 = micros();

  int16_t ham_v = ads_oku(ADS_GERILIM);
  int16_t ham_i = ads_oku(ADS_AKIM);
  uint32_t t3 = micros();

  if (faz_adet >= 256u) {      /* kayan pencere: son 256 cevrim */
    faz_yaz_top = faz_bek_top = faz_oku_top = faz_kayma_top = 0; faz_adet = 0;
  }
  faz_yaz_top += t1 - t0;
  faz_bek_top += t2 - t1;
  faz_oku_top += t3 - t2;
  faz_adet++;

  Okuma3 ham = olc3(ham_v, ham_i, etkin_kanal(),
                    ayar.i_ofset, ayar.i_pga, ayar.sont_ohm,
                    ayar.i_duzeltme);

  // 3) Gercek ornek periyodunu olc (dongu sabit hizli DEGIL).
  uint32_t simdi = micros();
  if (son_ornek_us) {
    float dt = (float)(simdi - son_ornek_us);
    if (dt > 200.0f && dt < 20000.0f) {
      // Yumusatma: tek bir uzun dongu (web istegi) d'yi sicratmasin.
      ornek_periyot_us += 0.05f * (dt - ornek_periyot_us);
    }
  }
  son_ornek_us = simdi;

  // 4) HIZALAMA. Gerilim t_kayma kadar ERKEN ornekleniyor; kesirli
  //    gecikme onu ileri tasiyor. Uzerine menzil basina faz
  //    kalibrasyonu ekleniyor (B17 — direncli yukle olculur).
  tampona_it(hv_tampon, ham.volt);
  tampona_it(hi_tampon, ham.amper);
  // B20: doygunluk bayraklarini tamponla AYNI adimda kaydir.
  hv_doydu = (uint8_t)((hv_doydu << 1) & 0x0Fu);
  if (gerilim_doydu(ham_v, etkin_kanal())) hv_doydu |= 1u;
  if (tampon_dolu < 4u) tampon_dolu++;

  Okuma3 o = ham;
  if (tampon_dolu >= 4u) {
    /* 🔴 B22.1 — K2. Eskiden faz_kal ORNEK cinsindendi ve d'ye DOGRUDAN
        ekleniyordu:
            d = t_kayma_us / ornek_periyot_us + faz_kal[m]
        Uygulanan ZAMAN duzeltmesi boylece faz_kal * ornek_periyot_us
        oluyordu — yani DONGU PERIYODUYLA OLCEKLENIYORDU. Oysa duzeltilen
        sey iki RC'nin arctan farki: SABIT bir zaman. Periyot degisince
        (web istegi, menzil gecisi, enableDelay kusuru) duzeltme kayiyordu.
        50 Hz'te 1503 us'te kalibre edilen kart 2000 us'te 1.744 derece
        artik hata yapiyordu — B17'nin kendi <=1 derece olcutunun 1.74 kati.
        Artik us cinsinden saklaniyor ve BOLMENIN ICINE giriyor: */
    float d = ((float)t_kayma_us + ayar.faz_kal_us[ayar.menzil ? 1 : 0])
              / ornek_periyot_us;
    // Lagrange 4 katsayili; d'yi makul araliga kirp.
    if (d < -1.0f) d = -1.0f;
    if (d > 2.0f) d = 2.0f;
    o.volt = hizala_kesirli(d, hv_tampon[0], hv_tampon[1],
                            hv_tampon[2], hv_tampon[3]);
    // Hizalayicinin cikisi hi_tampon[1] aninda, o yuzden akim ORADAN
    // aliniyor (ham).
    // B20 notu — ASIMETRIK SARKMA: gerilim hizalayicidan geciyor, akim
    // gecmiyor. Yani genlik sarkmasi guce |H_L|^1 olarak biniyor,
    // |H_L|^2 olarak degil — iki kanal da suzulseydi hata IKI KATI
    // olurdu. 50 Hz'te -0.0113%. Ortalama V etkilenmiyor: Lagrange'in
    // DC kazanci her d icin tam 1.
    o.amper = hi_tampon[1];
    o.watt = o.volt * o.amper;
  }

  // 5) OLCEK DUZELTMESI (B16'nin 3. kalemi). Iki kanal da tek kutuplu
  //    RC'den geciyor; 50 Hz'te guc |H_v| * |H_i| = 0.55 kati okunuyor.
  //    B16 iki kanali ESITLEDIGI icin bu artik YUKTEN BAGIMSIZ ve
  //    frekans bilinirse TAM silinebiliyor.
  //    ⚠ Yalnizca GUCE uygulaniyor: ortalama V ve I, AC'de zaten ~0;
  //      DC'de (sebeke_hz = 0) duzeltme carpani 1.
  if (ayar.sebeke_hz > 0.0f) {
    o.watt *= suzgec_ters_kazanc(ayar.sebeke_hz, etkin_kanal()->tau)
            * suzgec_ters_kazanc(ayar.sebeke_hz, TAU_AKIM);
  }

  // 🔴 B20: menzil_gozet'e HAM olcum veriliyor, hizalanmis olan degil.
  // Hizalayicinin cikisi hv_tampon[1] anina ait, yani 2 ornek ESKI; menzil
  // karari o kadar gecikiyor ve esik asildiktan sonra giris kanali 2 ornek
  // daha zorlanmaya devam ediyordu. Yukari esik ile NORMAL kanalin doyumu
  // arasinda yalnizca 3.24 V pay var — 1395 V/s'ten hizli her sinyalde bu
  // pay 2 ornekte yeniyor ve tampona DOYMUS ornek giriyordu.
  // ham.volt zaten ayni turda hesaplaniyor; ek maliyet YOK.
  menzil_gozet(ham.volt);
  return o;
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

/* 🔴 B37 — SURUCU DURUMU IZLENIYOR. `adc_continuous_stop` zaten durmus
   surucuye cagrilinca IDF konsola `E (..) adc_continuous: The driver is
   already stopped` basiyor — hata degil, ama ERROR seviyesinde ve her
   `w`/`wB`de uc satir. Gercek bir iz bu gurultunun icinde kaybolurdu;
   kullanici da her olcumde "bir sey bozuldu" sanirdi. Once `w`de bir
   satirdi (eskiden beri vardi), bos-pin sinamasi bunu uce cikarinca
   duzeltmeye degdi. Sarmalayicilar yalnizca DURUM DEGISIYORSA IDF'i
   cagiriyor; `adc_continuous_start`in donus degeri aynen geciyor. */
static bool skop_calisiyor = false;

static esp_err_t adc_baslat(void) {
    if (skop_calisiyor) return ESP_OK;
    esp_err_t r = adc_continuous_start(skop_kulp);
    if (r == ESP_OK) skop_calisiyor = true;
    return r;
}

static void adc_durdur(void) {
    if (!skop_calisiyor) return;
    adc_continuous_stop(skop_kulp);
    skop_calisiyor = false;
}
static uint16_t skop_veri[SKOP_AZAMI_ADET];
static uint16_t skop_gecici[SKOP_AZAMI_ADET];
static uint16_t skop_adet = 0;        // son yakalamadaki örnek sayısı
static uint16_t skop_tetik_idx = 0;   // tetik örneğinin dizideki yeri
static uint32_t skop_hz = 0;          // son yakalamanın gerçek hızı
static bool     skop_tetiklendi = false;

// Prob ucundaki volt/adım. Skop bölücüsü (R6/R7) ölçüm bölücüsüyle aynı
// oranda: 100K/6.8K. 3.10 V / 4095 x 15.706 = 11.89 mV -> tam ölçek 48.7 V.
static float skop_volt_adim() { return SKOP_VOLT_ADIM; }
static float skop_volt_ofset() { return SKOP_VOLT_OFSET; }

/* B19: skop_olc() ham kodu `kod * volt_adim` diye ceviriyor ve OFSET
 * bilmiyor. O dosya Asama 2'den URETILEN birebir kopya (test_skop_ayni.py
 * karakter karakter karsilastiriyor), o yuzden DOKUNULMUYOR — ofset
 * BURADA, sonuca uygulaniyor.
 *
 * Hangi alan etkilenir: MUTLAK olanlar (vmax, vmin, vort) ve vrms.
 * Etkilenmeyenler: vpp, vac, frekans, periyot, duty, yukselme/dusme,
 * cevrim — hepsi FARK ya da ZAMAN buyuklugu.
 * vrms yeniden kuruluyor: vrms^2 = vac^2 + vort^2 ozdesligi ofsetten
 * bagimsiz oldugu icin duzeltilmis vort ile tekrar hesaplanabiliyor. */
static void skop_ofsetle(SkopOlcum *m) {
    const float o = SKOP_VOLT_OFSET;
    m->vmax -= o;
    m->vmin -= o;
    m->vort -= o;
    m->vrms = sqrtf(m->vac * m->vac + m->vort * m->vort);
}

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

static adc_cali_handle_t skop_cali = NULL;
static bool skop_cali_var = false;

/* Egri kalibrasyonu S3'te desteklenen tek sema. Yoksa SESSIZ KALMIYORUZ:
   `c` komutu bunu soyluyor, cunku kalibrasyonsuz bir mV degeri "olculmus"
   gibi gorunup aslinda ham kodun sabitle carpimi olurdu. */
/* 🔴 B39 — TEK KALIBRASYON TABLOSU. Acilista eFuse egrisinden 17 nokta
   (0, 256, ..., 3840, 4095) cikariliyor. `CT` komutu BU diziyi basiyor,
   arayuz skop eksenini BU diziyle cizıyor, hizli yol (P/PF/Vrms/Irms)
   BU diziyle olcekliyor. Uc tuketici, TEK temsil: hizli yol tam eFuse
   egrisini (`adc_cali_raw_to_voltage`) cagirsaydi, ayni ham kod arayuzde
   bir gerilime, kartta baska bir gerilime cevrilirdi.
   Aradegerleme hatasi KARTTA OLCULDU (2026-09-13, orta noktalarda tam
   egriyle kiyas): kod 0..3000 araliginda +-1 mV, doyum yakininda (3968)
   -4.3 mV. Hizli yol VREF (kod ~2000) cevresinde calisiyor. */
#define KAL_N 17u
static int16_t kal_mv_tab[KAL_N];
static bool kal_tab_var = false;

static inline uint16_t kal_dugum_kod(uint8_t k) {
    return (k == KAL_N - 1u) ? 4095u : (uint16_t)(k * 256u);
}

/* Ham kod -> pin mV, tablo aradegerlemesi. Arayuzun `kalMv`i ile AYNI
   kural: tablo disi kod KIRPILMIYOR, uctaki egimle UZATILIYOR (kirpilsaydi
   doyuma giren sinyal duz bir cizgi gibi gorunur, kirpildigi anlasilmazdi). */
static float kal_mv(float kod) {
    uint8_t i;
    if (kod <= 256.0f)        i = 0;
    else if (kod >= 3840.0f)  i = (uint8_t)(KAL_N - 2u);
    else                      i = (uint8_t)(kod / 256.0f);
    float k0 = (float)kal_dugum_kod(i), k1 = (float)kal_dugum_kod((uint8_t)(i + 1u));
    float v0 = (float)kal_mv_tab[i],   v1 = (float)kal_mv_tab[i + 1u];
    return v0 + (v1 - v0) * (kod - k0) / (k1 - k0);
}

static void skop_cali_kur() {
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    adc_cali_curve_fitting_config_t c = {};
    c.unit_id  = ADC_UNIT_1;
    c.chan     = (adc_channel_t)SKOP_KANAL;
    c.atten    = ADC_ATTEN_DB_12;
    c.bitwidth = ADC_BITWIDTH_12;
    skop_cali_var = (adc_cali_create_scheme_curve_fitting(&c, &skop_cali) == ESP_OK);
#else
    skop_cali_var = false;
#endif
    kal_tab_var = false;
    if (skop_cali_var) {
        bool tamam = true;
        for (uint8_t k = 0; k < KAL_N; k++) {
            int mv = -1;
            if (adc_cali_raw_to_voltage(skop_cali, kal_dugum_kod(k), &mv) != ESP_OK
                || mv < 0) { tamam = false; break; }
            kal_mv_tab[k] = (int16_t)mv;
        }
        kal_tab_var = tamam;
    }
}

void skop_kur() {
    skop_cali_kur();
    adc_continuous_handle_cfg_t k = {};
    k.max_store_buf_size = 8192;
    k.conv_frame_size    = 1024;            // 4 bayt/dönüşüm -> 256 örnek
    if (adc_continuous_new_handle(&k, &skop_kulp) != ESP_OK) skop_kulp = NULL;
}

// Örnekleme hızını değiştirir. ADC durmuş olmalı.
static bool skop_hiz_ayarla(uint32_t hz) {
    if (!skop_kulp) return false;
    adc_durdur();               /* config CALISAN surucuye uygulanamaz */
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
/* B28: skop tamponu TEK yerde yeniden yaziliyor (yakalama) ve TEK
   yerde okunuyor (/skop.bin, cekirdek 0). Ikisi ayni anda olursa
   indirilen dalga YARI ESKI YARI YENI olur — sessiz ve inandirici bir
   yanlis. Kilit bunu kesiyor; OLCUM TARAFI ASLA BEKLEMIYOR (timeout 0),
   dokum suruyorsa yakalama reddedilip kullaniciya soyleniyor. */
static SemaphoreHandle_t skop_kilidi = nullptr;
static inline void skop_kilidi_birak() {
    if (skop_kilidi) xSemaphoreGive(skop_kilidi);
}

/* 🔴 B40 — SKOP DOKUMU OLCUM DONGUSUNU BLOKLUYORDU.
   Kartta olculdu (2026-09-13), `t` sirasinda olcum dongusunun en uzun
   turu:  tb3 667 ms · tb5 897 ms · tb7 1524 ms · tb9 4437 ms; tb7 ve
   ustunde `enerji_biriktir` o araligi TAMAMEN atiyordu. Blokajin cogu
   pencere degil, ASCII dokumun seri porta basilmasiydi: 833 ornek
   ~4.2 KB, 115 200 baud'da ~365 ms, ustune her `print` ayri bir TX
   halka ogesi (B37: ~12 B ek yuk) oldugu icin halka hemen doluyor.
   PC koprusu (B35) tam bu yolu kullaniyor; "Surekli" kipte olcum
   neredeyse hic calismazdi.

   Simdi dokum bir DURUM MAKINESI: yakalama bitince baslatiliyor, her
   `loop()` turunda TX halkasinda yer oldugu kadar satir basiliyor.
   Her satir TEK `write` — hem halka ogesi ek yukunu satir basina bire
   indiriyor hem de satirin yarisinda baska bir satir araya giremiyor.
   Aradaki `D` satirlari dokumun ICINE dusebilir: kopru cozucusu
   (SkopCozucu) bunlari atlayip SAYIYOR, arayuz ayristiricisi B40'ta
   buna gore duzeltildi.

   ⚠ Dokum surerken skop_veri OKUNUYOR — yeni bir yakalama onu yarida
     degistirirse basilan dalga yari eski yari yeni olur. Yakalama bu
     yuzden dokum bitene kadar REDDEDILIYOR ve bu kez mesaj DOGRU. */
static struct {
    bool     aktif;
    uint8_t  asama;        /* 0 S2 · 1 M · 2 ornekler · 3 E */
    uint16_t i;            /* siradaki ornek */
} skop_dokum = { false, 0, 0 };
static SkopOlcum skop_dokum_m;
/* Duzenli ciktiya (D, K, komut yanitlari) birakilan TX payi. Dokum bu
   kadarini hic doldurmuyor; dolduraydi `D` satirinin kendisi bloklardi. */
#define SKOP_DOKUM_PAY 1536
#define SKOP_DOKUM_TUR_SATIR 6u   /* bir loop turunda en fazla */

/* 🔴 B40b — YAKALAMA OLCUM CEKIRDEGINDEN CIKTI.
   Dokum turlara bolununce (B40a) kalan blokaj yakalamanin KENDISIYDI:
   pencere + tetik beklemesi. OTO kipte tetik gelmezse zaman asimi
   (`pencere x 4 + 300 ms`, en cok 4 s) bekleniyor — kartta olculdu:
   tb3 344 ms, tb5 515 ms, tb7 1131 ms, tb9 4048 ms. `ta` (otomatik
   kurulum) esigi 0'a cekip 12 zaman tabanini sirayla yakaliyor;
   periyodik sinyal yoksa ONLARCA saniye.

   Yakalama artik ayri bir gorevde — CEKIRDEK 1, OLCUMDEN YUKSEK ONCELIK.

   🔴 B41 — ESZAMANLI I2C TRAFIGI ADC VERISINE TEK-ORNEK HATA SOKUYOR.
      Kullanicinin ekraninda 200 ms/bol yakalamada uc dik igne ve o
      ignelerden birine dusen SAHTE TETIK vardi. Kartta olculdu
      (2026-09-13), CAL %50 = 20K + 100 nF ile surulu dugum (1.6 ms'de
      600 kod atlayamaz), tek-ornek hatasi (> 60 kod) / 1000 ornek:
          yakalama olcum dongusunu blokluyor (B40a)       tb3 0     tb10 0
          ayri gorev, ADS ESZAMANLI calisiyor (B40b)      tb3 3.9   tb10 2.1
          ayri gorev CEKIRDEK 1'de, ADS eszamanli          tb3 5.7   tb10 2.9
          ayri gorev, yakalamada ADS SUSUYOR               tb3 0     tb10 0
          yakalamada YALNIZ I2C okuma (donusum/RDY yok)    tb3 5.1   tb10 3.3
          yakalamada I2C YOK, CPU mesgul                   tb3 0     tb10 0
          I2C surucusu KAPALI, SDA/SCL elle tiklatiliyor   tb3 2.4   tb10 1.2
      Ilk tanim ("cekirdek 0 / WiFi") YANLISTI. Sebep ELEKTRIKSEL: I2C
      kenarlari — surucu kapaliyken bile — skop donusumune hata sokuyor.
      B40a'da yakalama donguyu bloklarken bu yalitim KAZARA saglaniyordu;
      B40b onu bozdu. Zincir ve bringup yesildi: hicbir iddia ORNEK
      BUTUNLUGUNE bakmiyordu.
      🔶 B44 DUZELTMESI (kuplaj deneyi, `tK` + tezgah_kuplaj.py): yukaridaki
      tablo SIRALI kosuldu ve CAL PWM'inin ara sira gelen hata patlamalariyla
      karisabiliyordu. Icice, CAL kapali, >30 kod, 16 660 ornek/durum:
          GPIO8/9 teller BAGLI 2.22 · teller SOKUK 0 · bos GPIO2 0.06 ·
          bos GPIO40 0.18 · AYNI teller GPIO41/42'de (ADC'siz) 1.26 /1000
      Hatayi pinin ADC1'de olmasi degil YUKLU HAT uretiyor; I2C'yi ADC1
      disina TASIMAK COZMUYOR (olculdu, geri alindi). Aday: kablo demeti
      icinde I2C tellerinden GPIO4 teline sizma.
      Bugunku cozum: yakalama surerken ADS SUSUYOR (loop()'ta bekci),
      susma suresi `ads_duraklama_ms` olarak SAYILIYOR, >1 s araliklar
      enerji sayacinda eskisi gibi `enerji_kayip_ms`e yaziliyor.
      Gorev yine de ayri: komutlar (ozellikle `p0` pil DURDUR) uzun bir
      yakalama sirasinda da ANINDA isleniyor.

   KURAL: bu gorev HIC
   YAZDIRMIYOR. `Serial`in satir birlestirmesi (WebAkis) tek yazarli;
   iki cekirdekten yazilirsa satirlar KARAKTER duzeyinde karisir ve
   hem D hem skop satirlari bozulur. Gorev sonucu bir kuyruga birakiyor,
   butun cikti cekirdek 1'den basiliyor.

   SAHIPLIK: `skop_is` YALNIZCA cekirdek 1'de yaziliyor (ise baslarken
   kurulur, sonuc alininca silinir). Is surerken ADC'ye dokunan `w*`
   komutlari ve `skop_ayar`i degistiren ayar komutlari REDDEDILIYOR —
   gorev ikisini de kullaniyor. */
enum : uint8_t { SKOP_IS_YOK = 0, SKOP_IS_DOKUM, SKOP_IS_IKILI, SKOP_IS_OTOMATIK };
enum : uint8_t { SKOP_SONUC_OK = 0, SKOP_SONUC_TETIK_YOK, SKOP_SONUC_KILIT,
                 SKOP_SONUC_HATA, SKOP_SONUC_OTO_YOK };
static volatile uint8_t skop_is = SKOP_IS_YOK;
static TaskHandle_t  skop_gorev_kolu = nullptr;
static QueueHandle_t skop_sonuc_q = nullptr;
/* Yakalamanin YAPILDIGI ayarlar. Dokum ve /skop.bin basliginda bunlar
   kullaniliyor: yakalamadan sonra `tb` degistirilirse eski kayit YENI
   zaman tabaniyla etiketlenmesin (onceden boyle oluyordu). */
static uint8_t skop_son_tdiv = 5, skop_son_kip = 0;
/* B41: yakalama surerken ADS'nin sustugu toplam sure (C satirinda). */
static uint32_t ads_duraklama_top_ms = 0;
static uint32_t ads_duraklama_bas_ms = 0;
static bool pil_testi_suruyor();   /* tanimi pil durumundan sonra */

/* 🔶 B44 — KUPLAJ DENEYI (`tK[<pin>[,<pin>]]`). Soru: B41'deki tek-ornek
   hatalari PINDEN mi (GPIO8/9 ADC1 pedi) yoksa HATTAN mi (modullere giden
   teller, pull-up akimi) geliyor? Cevap I2C'yi baska pine TASIMANIN ise
   yarayip yaramayacagini soyluyor. Komut normal bir skop yakalamasi
   yapiyor (ADS B41'deki gibi susuyor) ve yakalama BOYUNCA secilen pinleri
   I2C benzeri kenar patlamalariyla tiklatiyor; bos liste = kontrol.
   ⚠ IZIN LISTESI DISINDA HICBIR PINE DOKUNULMAZ — ozellikle GPIO6 PIL
     KAPISI (MOSFET). Bkz. `kuplaj_pin_serbest`. */
static uint8_t  kuplaj_pin[2] = { 0xFFu, 0xFFu };
static bool     kuplaj_aktif = false;
static bool     kuplaj_hazir = false;
static uint32_t kuplaj_patlama = 0;

/* B40b/B41: `skop_gorevi` (cekirdek 1, oncelik 2) cagiriyor. YAZDIRMAZ — sonucu
   dondurur, metni cekirdek 1 basar. Dokum/is cakismasini cagiran taraf
   (`skop_is_ver`) onceden eliyor. */
static uint8_t skop_yakala()
{
    uint32_t hz;
    uint16_t n;
    skop_taban_coz(skop_ayar.tdiv, &hz, &n);

    if (!skop_kulp) return SKOP_SONUC_HATA;
    if (skop_kilidi && xSemaphoreTake(skop_kilidi, 0) != pdTRUE)
        return SKOP_SONUC_KILIT;          /* /skop.bin okunuyor */
    if (!skop_hiz_ayarla(hz)) { skop_kilidi_birak(); return SKOP_SONUC_HATA; }
    if (adc_baslat() != ESP_OK) { skop_kilidi_birak(); return SKOP_SONUC_HATA; }

    uint16_t on = (uint16_t)((uint32_t)n * skop_ayar.on_yuzde / 100u);
    if (on + 2u > n) on = (uint16_t)(n - 2u);
    uint16_t sonra = (uint16_t)(n - on);

    uint16_t w = 0, dolu = 0, kalan = 0, tetik_w = 0, onceki = 0;
    bool bulundu = false, hazir = false, ilk = true;

    /* Zaman aşımı: pencerenin dört katı (tetik beklemesi için pay),
       en az 300 ms, en çok 4 s.

       🔴 B31 — ÜST SINIR PENCEREDEN KÜÇÜK OLAMAZ. 4 s'lik tavan en yavaş
       zaman tabanında (500 ms/böl → 5 s pencere) yakalamayı ASLA
       tamamlatmıyordu: OTO kipi kısa kaydı sessizce döndürüyor, kullanıcı
       "500 ms/böl × 10 böl" seçip 3.77 s'lik bir kayıt alıyordu. Kartta
       ölçüldü: 3055 örnek beklenirken 2304 geldi. Çizim doğruydu (S2
       satırı gerçek adet/hızı bildiriyor), YALAN OLAN ETİKETTİ.
       Tavan artık pencerenin kendisinden küçük olamıyor. Bedeli açık:
       yakalama süresince ölçüm döngüsü duruyor ve bu boşluk zaten
       `enerji_kayip_ms` olarak sayılıyor. */
    float pencere_ms = 1000.0f * (float)n / (float)hz;
    uint32_t azami_ms = (uint32_t)(pencere_ms * 4.0f) + 300u;
    if (azami_ms > 4000u) azami_ms = 4000u;
    uint32_t taban_ms = (uint32_t)(pencere_ms * 1.2f) + 300u;
    if (azami_ms < taban_ms) azami_ms = taban_ms;
    /* B41 — OTO KIPTE TETIK YOKSA TABAN KADAR BEKLE. Kullanici 200 ms/bol'de
       yakalamanin uzun surdugunu soyledi: tetik yokken 4 s bekleniyordu
       (pencere 2 s). OTO'da tetik beklemek anlamsiz — serbest kosu zaten
       gelecek; taban (1.2 x pencere + 300 ms) pencerenin TAMAMINI hala
       garanti ediyor (B31). NORMAL ve TEK kip tetigi beklemeye devam. */
    if (skop_ayar.kip == SKOP_KIP_OTO) azami_ms = taban_ms;
    uint32_t t0 = millis();

    uint8_t cerceve[1024];
    while (millis() - t0 < azami_ms) {
        uint32_t okunan = 0;
        if (adc_continuous_read(skop_kulp, cerceve, sizeof(cerceve),
                                &okunan, 100) != ESP_OK) continue;

        for (uint32_t b = 0;
             b + SOC_ADC_DIGI_RESULT_BYTES <= okunan;
             b += SOC_ADC_DIGI_RESULT_BYTES) {
            /* 🔴 B42 — ÇERÇEVE KUYRUĞU GEÇMİŞİ EZİYORDU. `break` aşağıda
               yalnızca ÇERÇEVE bitince çalışıyor; tetikten sonraki sayaç
               bitse de aynı çerçevenin geri kalanı (256 örneğe kadar)
               halkaya yazılmaya devam ediyordu. Kartta ölçüldü
               (2026-09-13, ön-tetik %25): 5 ms/böl'de beklenen 250 yerine
               3..249; 1 ms/böl'de (833 örnek, %10 → 83) 737..801 ve 6
               yakalamanın 5'inde tetik örneğinin KENDİSİ ezilmişti — işaret
               eşiği geçmeyen bir örneği gösteriyor, Sürekli kipte iz
               kilitlenmiyordu. Zincir yeşildi: hiçbir iddia tetiğin YERİNE
               bakmıyordu. */
            if (bulundu && kalan == 0u) break;
            adc_digi_output_data_t *o = (adc_digi_output_data_t *)&cerceve[b];
            if (o->type2.channel != SKOP_KANAL) continue;
            uint16_t v = o->type2.data;

            skop_veri[w] = v;
            w = (uint16_t)((w + 1u) % n);
            if (dolu < n) dolu++;

            if (!bulundu) {
                /* `dolu` bu örneği de sayıyor: `>` tetikten ÖNCE tam `on`
                   örnek demek (`>=` ile halka bir eksik dolup tetik on-1'e
                   düşerdi). */
                if (dolu > on) {         // yeterli geçmiş biriktikten sonra
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
                    /* Tetik örneği yazıldı; ARKASINDAN sonra-1 örnek daha:
                       on + 1 + (sonra-1) = n → halka tam dolu ve tetik
                       dizide TAM `on` indeksinde. (`sonra >= 2`: yukarıda
                       on + 2 <= n kırpılıyor.) */
                    kalan = (uint16_t)(sonra - 1u);
                }
            } else if (kalan > 0u) {
                kalan--;
            }
        }
        if (bulundu && kalan == 0u) break;
    }
    adc_durdur();

    if (!bulundu) {
        // OTO kipinde tetik bulunamazsa serbest koşu olarak göster.
        // NORMAL ve TEK kipinde göstermek YALAN olur — başarısız dön.
        /* 🔴 B40 — KİLİT SIZINTISI. Bu iki dal `skop_kilidi`ni BIRAKMADAN
           dönüyordu. Kartta ölçüldü (2026-09-13): Normal kipte bir kez
           tetiklenmeyen yakalamadan sonra OTO kipe dönülse bile her `t`
           "! skop: dokum suruyor" diyor ve skop YENİDEN BAŞLATMAYA KADAR
           ölü kalıyordu; WiFi'de `/skop.bin` sonsuza dek 503 dönerdi.
           Arayüzdeki "Normal" ve "Tek atış" seçeneklerinin ikisi de bunu
           tetikliyordu. */
        if (skop_ayar.kip != SKOP_KIP_OTO) { skop_kilidi_birak(); return SKOP_SONUC_TETIK_YOK; }
        if (dolu < 2u)                     { skop_kilidi_birak(); return SKOP_SONUC_TETIK_YOK; }
    } else if (kalan > 0u) {
        skop_kilidi_birak();
        return SKOP_SONUC_TETIK_YOK;     // zaman aşımı, pencere dolmadı
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
    skop_son_tdiv = skop_ayar.tdiv;
    skop_son_kip = skop_ayar.kip;
    skop_kilidi_birak();
    return SKOP_SONUC_OK;
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
        if (skop_yakala() != SKOP_SONUC_OK) continue;

        SkopOlcum m;
        skop_olc(skop_veri, skop_adet, skop_volt_adim(), (float)skop_hz, &m);
        skop_ofsetle(&m);
        if (m.frekans > 0.0f && m.cevrim >= 2u) {
            float va = skop_volt_adim();
            bulunan_f = m.frekans;
            /* KOD cinsinden orta nokta: volt -> kod cevirisinde ofset
             * GERI eklenmeli, yoksa tetik esigi kayar. */
            orta   = (uint16_t)(((m.vmax + m.vmin) * 0.5f
                                 + skop_volt_ofset()) / va);
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

/* 🔴 B43 — SKOP OLCUMLERI EKSENLE AYNI KALIBRASYONDAN.
   Panelden ve tezgahta olculdu (2026-09-13, CAL 1 kHz, AYNI kodlar):
       M satiri (kod * volt_adim)   Vmax -6.30  Vmin -10.65  Vpp 4.35 V
       arayuz ekseni (eFuse, B36)   Vmax +0.70  Vmin  -4.12  Vpp 4.82 V
   B36 ekseni kalibre etti; ekranin altindaki olcum satiri ise hala
   dogrusal modelden geliyordu — izgara bir sey, sayilar baska sey
   (100 Hz'de 9 V). Cozum B39'un TEK TABLOSU (`kal_mv_tab`), dorduncu
   tuketici olarak:
     * VOLT buyuklukleri tablodan, arayuzun `kodVolt`u ile AYNI kural.
       Toplamlar DOUBLE: ofsetsiz deger ~65 V; float32 kare toplaminda
       4000 ornekte Vac'in karesi (gurultude ~0.003 V^2) yuvarlamada
       kaybolurdu.
     * ZAMAN buyuklukleri (f, T, duty, tr, tf, n) `skop_olc`'tan, ama
       tablodan DOGRUSALLASTIRILMIS kodlarla: esikler eksenin gosterdigi
       orta seviyede.
   `skop_olc.h`e DOKUNULMUYOR (Asama 2'den uretilen birebir kopya). Donus
   degerleri `skop_olc` gibi OFSETSIZ; ofseti cagiran `skop_ofsetle` uygular.
   Tablo yoksa eski yol (dogrusal) — arayuz de o durumda ekseni dogrusal
   ciziyor (`CT 0`), yani ikisi yine ayni. */
static void skop_olc_kalibre(SkopOlcum *m)
{
    const uint16_t n = skop_adet;
    if (!kal_tab_var || n == 0u) {
        skop_olc(skop_veri, n, skop_volt_adim(), (float)skop_hz, m);
        return;
    }
    const float mv_kod = SKOP_ADC_SAYIM / (SKOP_ADC_TAVAN * 1000.0f);  /* pin mV -> dogrusal kod */
    const float mv_v   = SKOP_ORAN / 1000.0f;                          /* pin mV -> V, ofsetsiz */
    uint16_t hmin = skop_veri[0], hmax = skop_veri[0];
    double top = 0.0, kare = 0.0;
    for (uint16_t i = 0; i < n; i++) {
        uint16_t h = skop_veri[i];
        float mv = kal_mv((float)h);
        float d = mv * mv_kod + 0.5f;
        skop_gecici[i] = (d <= 0.0f) ? 0u : ((d >= 65535.0f) ? 65535u : (uint16_t)d);
        double v = (double)mv * (double)mv_v;
        top += v;
        kare += v * v;
        if (h < hmin) hmin = h;
        if (h > hmax) hmax = h;
    }
    skop_olc(skop_gecici, n, skop_volt_adim(), (float)skop_hz, m);   /* zaman buyuklukleri */
    double ort = top / (double)n;
    double ac = kare / (double)n - ort * ort;
    m->vmax = kal_mv((float)hmax) * mv_v;
    m->vmin = kal_mv((float)hmin) * mv_v;
    m->vpp  = m->vmax - m->vmin;
    m->vort = (float)ort;
    m->vac  = (ac > 0.0) ? (float)sqrt(ac) : 0.0f;
    m->vrms = (float)sqrt(kare / (double)n);
}

// Protokol — yeni `S2` başlığı zaman tabanını, tetik konumunu ve
// otomatik ölçümleri taşıyor:
//
//   S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
//   M f=<Hz> T=<s> Vpp=<V> Vmax=<V> Vmin=<V> Vort=<V> Vrms=<V> Vac=<V>
//     duty=<%> tr=<s> tf=<s> n=<çevrim>
//   <ham ADC kodları, 16'şar satır>
//   E
/* ── Cekirdek 0: yakalama gorevi ─────────────────────────────────────
   Bildirim bekler, `skop_is`e gore yakalar, sonucu kuyruga birakir.
   ⚠ YAZDIRMAZ (bkz. SKOP_IS tanimlari). Olcumler (`skop_olc`) burada
     hesaplaniyor: skop_veri artik degismeyecek ve float isi olcum
     cekirdeginden de cikmis oluyor. */
static void skop_gorevi(void *)
{
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        uint8_t is = skop_is;
        uint8_t sonuc = SKOP_SONUC_HATA;
        if (is == SKOP_IS_OTOMATIK) {
            sonuc = skop_otomatik() ? skop_yakala() : (uint8_t)SKOP_SONUC_OTO_YOK;
        } else if (is == SKOP_IS_DOKUM || is == SKOP_IS_IKILI) {
            sonuc = skop_yakala();
        }
        /* 🔴 B43: ikili yolda da olculuyor — eskiden `is != SKOP_IS_IKILI`
           vardi ve WiFi'deki (tB + /skop.bin) HICBIR yakalamada olcum
           satiri (frekans, Vpp, duty…) gosterilemiyordu. */
        if (sonuc == SKOP_SONUC_OK) {
            SkopOlcum &m = skop_dokum_m;
            skop_olc_kalibre(&m);
            skop_ofsetle(&m);
        }
        xQueueSend(skop_sonuc_q, &sonuc, portMAX_DELAY);
    }
}

/* ── Cekirdek 1: is ver ──────────────────────────────────────────────
   Cakisan her durumu SEBEBIYLE reddeder. */
static bool skop_is_ver(uint8_t is)
{
    if (!skop_gorev_kolu || !skop_sonuc_q) {
        Serial.println(F("! skop: yakalama gorevi yok"));
        return false;
    }
    if (skop_is != SKOP_IS_YOK) {
        Serial.println(F("! skop: yakalama suruyor — tekrar dene"));
        return false;
    }
    if (skop_dokum.aktif) {
        Serial.println(F("! skop: dokum suruyor, yakalama atlandi — tekrar dene"));
        return false;
    }
    /* 🔴 B41 — EMNIYET: yakalama ADS'yi susturuyor; pil testi surerken
       bu KESME GERILIMI denetiminin durmasi demek (ve `pil_isle` 1 s'den
       uzun araligi atliyor). Pil testi bitmeden skop yakalanmaz. */
    if (pil_testi_suruyor()) {
        Serial.println(F("! skop: pil testi suruyor — yakalama ADS'yi susturur, kesme denetimi durur"));
        return false;
    }
    skop_is = is;
    xTaskNotifyGive(skop_gorev_kolu);
    return true;
}

void skop_yolla()
{
    skop_is_ver(SKOP_IS_DOKUM);
}

/* `M` satiri TEK yerde bicimleniyor: ASCII dokumu ve ikili onay AYNI
   metni basiyor (iki bicimleyici ayrisirsa arayuz iki yolda farkli
   ayristirirdi). */
static int skop_m_satiri(char *b, size_t boy)
{
    const SkopOlcum &m = skop_dokum_m;
    return snprintf(b, boy,
                    "M f=%.3f T=%.9f Vpp=%.4f Vmax=%.4f Vmin=%.4f Vort=%.4f "
                    "Vrms=%.4f Vac=%.4f duty=%.2f tr=%.9f tf=%.9f n=%u\r\n",
                    (double)m.frekans, (double)m.periyot, (double)m.vpp,
                    (double)m.vmax, (double)m.vmin, (double)m.vort,
                    (double)m.vrms, (double)m.vac, (double)m.duty,
                    (double)m.t_yuksel, (double)m.t_dus, (unsigned)m.cevrim);
}

/* ── Cekirdek 1: sonucu isle (her loop turunda) ──────────────────────
   Eskiden ayni yerde senkron basilan metinler BURADA basiliyor; satir
   bicimleri degismedi. */
static void skop_sonuc_isle()
{
    uint8_t sonuc;
    if (!skop_sonuc_q || xQueueReceive(skop_sonuc_q, &sonuc, 0) != pdTRUE) return;
    uint8_t is = skop_is;
    skop_is = SKOP_IS_YOK;

    if (is == SKOP_IS_OTOMATIK) {
        if (sonuc == SKOP_SONUC_OTO_YOK) {
            Serial.println(F("! otomatik kurulum: periyodik sinyal yok"));
            return;
        }
        skop_ayar_yaz();
    }
    if (sonuc == SKOP_SONUC_KILIT) {
        Serial.println(F("! skop: /skop.bin okunuyor, yakalama atlandi — tekrar dene"));
        return;
    }
    if (sonuc != SKOP_SONUC_OK) {
        Serial.println(F("! tetiklenemedi"));
        return;
    }
    if (is == SKOP_IS_IKILI) {
        /* 🔴 B43 — OLCUM SATIRI ONAYDAN ONCE. `/skop.bin` basliginda yer
           yok (32 bayt dolu); arayuz onay satirini gorunce govdeyi cekiyor
           ve hemen onceki `M`yi o yakalamaya bagliyor. Sira bu fonksiyonda
           sabit, kilit de govde okunurken yeni yakalamayi engelliyor. */
        char mb[256];
        int mn = skop_m_satiri(mb, sizeof(mb));
        if (mn > 0) Serial.write((const uint8_t *)mb, (size_t)mn);
        Serial.print(F("* skop yakalandi (ikili): "));
        Serial.print(skop_adet);
        Serial.print(F(" ornek @ "));
        Serial.print(skop_hz);
        Serial.println(F(" Hz — /skop.bin"));
        return;
    }
    skop_dokum.aktif = true;
    skop_dokum.asama = 0;
    skop_dokum.i = 0;
}

/* Bir loop turunda TX halkasinda yer oldugu kadar dokum satiri basar.
   Bitince `skop_dokum.aktif = false`. Satir bicimi ESKI dokumle AYNI:
     S2 <adet> <Hz> <volt/adim> <tetik_idx> <tdiv_us> <kip> <tetiklendi> <ofset>
     M f=.. T=.. Vpp=.. Vmax=.. Vmin=.. Vort=.. Vrms=.. Vac=.. duty=.. tr=.. tf=.. n=..
     <ham ADC kodlari, 16'sar>
     E */
static void skop_dokum_ilerle()
{
    if (!skop_dokum.aktif) return;
    char b[256];
    for (uint8_t tur = 0; tur < SKOP_DOKUM_TUR_SATIR; tur++) {
        int n = 0;
        uint8_t sonraki = skop_dokum.asama;
        uint16_t sonraki_i = skop_dokum.i;
        if (skop_dokum.asama == 0) {
            n = snprintf(b, sizeof(b), "S2 %u %lu %.6f %u %lu %u %u %.6f\r\n",
                         (unsigned)skop_adet, (unsigned long)skop_hz,
                         (double)skop_volt_adim(), (unsigned)skop_tetik_idx,
                         (unsigned long)SKOP_TDIV_US[skop_son_tdiv],
                         (unsigned)skop_son_kip, skop_tetiklendi ? 1u : 0u,
                         (double)skop_volt_ofset());
            sonraki = 1;
        } else if (skop_dokum.asama == 1) {
            n = skop_m_satiri(b, sizeof(b));
            sonraki = (skop_adet > 0u) ? 2 : 3;
        } else if (skop_dokum.asama == 2) {
            uint16_t son = (uint16_t)(skop_dokum.i + 16u);
            if (son > skop_adet) son = skop_adet;
            for (uint16_t k = skop_dokum.i; k < son; k++) {
                n += snprintf(b + n, sizeof(b) - (size_t)n, (k + 1u < son) ? "%u " : "%u",
                              (unsigned)skop_veri[k]);
            }
            n += snprintf(b + n, sizeof(b) - (size_t)n, "\r\n");
            sonraki_i = son;
            sonraki = (son >= skop_adet) ? 3 : 2;
        } else {
            n = snprintf(b, sizeof(b), "E\r\n");
            sonraki = 4;
        }
        if (n <= 0) { skop_dokum.aktif = false; return; }
        if (Serial.availableForWrite() < n + SKOP_DOKUM_PAY) return;  /* sonraki tura */
        Serial.write((const uint8_t *)b, (size_t)n);                  /* TEK write */
        skop_dokum.asama = sonraki;
        skop_dokum.i = sonraki_i;
        if (sonraki == 4) { skop_dokum.aktif = false; return; }
    }
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


/* B44 — kuplaj deneyinde tiklatilabilecek pinler. Yalnizca I2C hatlari
   ve bu kartta BOS olan pinler. DISARIDA (bilerek): 4/5 skop ve hizli
   kanal, 6 PIL KAPISI, 7 RDY, 10 CAL, 0/3/45/46 acilis baglama pinleri,
   19/20 USB, 26-37 flas + oktal PSRAM, 43/44 UART0 (seri konsol). */
static bool kuplaj_pin_serbest(int p) {
  return p == 1 || p == 2 || p == PIN_SDA || p == PIN_SCL || (p >= 39 && p <= 42);
}

/* Yakalama surerken loop()'tan cagriliyor (ADS susuyor, I2C serbest).
   Kenarlar bus'a ZARARSIZ: pinler SIRAYLA tiklatiliyor — SDA inip
   kalkarken SCL bosta (yalnizca baslat/dur kosulu, saat yok), SCL darbe
   yaparken SDA bosta (saat var, baslat yok). Ayni surus her durumda:
   acik-drenaj + dahili pull-up; tek degisken pinin YERI ve YUKU. */
static void kuplaj_patlat() {
  if (!kuplaj_hazir) {
    if (kuplaj_pin[0] == PIN_SDA || kuplaj_pin[0] == PIN_SCL
        || kuplaj_pin[1] == PIN_SDA || kuplaj_pin[1] == PIN_SCL) Wire.end();
    for (uint8_t k = 0; k < 2u; k++)
      if (kuplaj_pin[k] != 0xFFu) {
        pinMode(kuplaj_pin[k], OUTPUT_OPEN_DRAIN | PULLUP);
        digitalWrite(kuplaj_pin[k], HIGH);
      }
    kuplaj_hazir = true;
  }
  for (uint8_t k = 0; k < 2u; k++) {
    uint8_t p = kuplaj_pin[k];
    if (p == 0xFFu) continue;
    for (uint8_t i = 0; i < 18u; i++) {        /* ~iki I2C baytinin kenari */
      digitalWrite(p, LOW);  delayMicroseconds(1);
      digitalWrite(p, HIGH); delayMicroseconds(1);
    }
  }
  kuplaj_patlama++;
  delay(1);                                    /* ADS okuma temposu (~1 ms) */
}

static void kuplaj_bitir() {
  bool i2c = false;
  for (uint8_t k = 0; k < 2u; k++) {
    uint8_t p = kuplaj_pin[k];
    if (p == 0xFFu) continue;
    if (p == PIN_SDA || p == PIN_SCL) i2c = true;
    else pinMode(p, INPUT);
  }
  if (i2c && kuplaj_hazir) Wire.begin(PIN_SDA, PIN_SCL, 400000);
  Serial.print(F("* kuplaj: pinler="));
  if (kuplaj_pin[0] == 0xFFu) Serial.print(F("yok"));
  else {
    Serial.print(kuplaj_pin[0]);
    if (kuplaj_pin[1] != 0xFFu) { Serial.print(','); Serial.print(kuplaj_pin[1]); }
  }
  Serial.print(F(" patlama="));
  Serial.println(kuplaj_patlama);
  kuplaj_aktif = false;
  kuplaj_hazir = false;
}

// Osiloskop komutlari. Asama 2'de `komut_calistir` icinde satir ici
// idi; Asama 3'te fonksiyona cikarildi ki komut isleyici sadeleşsin.
// GOVDE ASAMA 2 ILE AYNI — davranis degismedi.
void skop_komut(const char *s) {
      char alt = s[1];
      /* B40b: yakalama gorevi `skop_ayar`i kullaniyor; is surerken
         ayari degistiren her alt komut REDDEDILIYOR (`t?` yalnizca okur). */
      if (alt != '?' && skop_is != SKOP_IS_YOK) {
        Serial.println(F("! skop: yakalama suruyor — tekrar dene"));
        return;
      }
      if (alt == 0 || (alt >= '0' && alt <= '9')) {
        if (alt) skop_ayar.esik = (uint16_t)atoi(s + 1);
        skop_yolla();
      } else if (alt == 'B') {
        /* 🔴 B22.5 — YAKALA ama ASCII DOKME.
           `t` yakalayip 20 250 B'lik ASCII dokumu basiyor. `Serial`
           aynasi yuzunden bu dokum SSE'ye de gidiyor; WiFi'de hem
           ASCII hem `/skop.bin` cekmek ayni veriyi IKI KEZ tasimak
           olurdu. `tB` yalnizca yakaliyor ve tek satirlik onay
           basiyor — arayuz sonra `/skop.bin`'i cekiyor.
           ⚠ Onay satiri `!` ile BASLAMIYOR: arayuz `!` gorunce skop
             beklemesini iptal ediyor (app.js). */
        /* B40b: yakalama ayri gorevde; onay satiri sonuc gelince
           `skop_sonuc_isle()`den basiliyor. */
        skop_is_ver(SKOP_IS_IKILI);
      } else if (alt == 'K') {                    /* B44 kuplaj deneyi */
        uint8_t p[2] = { 0xFFu, 0xFFu };
        uint8_t adet = 0;
        const char *q = s + 2;
        while (*q) {
          int v = atoi(q);
          if (adet >= 2u || !kuplaj_pin_serbest(v)) {
            Serial.print(F("! kuplaj: pin "));
            Serial.print(v);
            Serial.println(F(" izinli degil (en cok 2 pin: 1 2 SDA SCL 39 40 41 42)"));
            return;
          }
          p[adet++] = (uint8_t)v;
          while (*q && *q != ',') q++;
          if (*q == ',') q++;
        }
        kuplaj_pin[0] = p[0];
        kuplaj_pin[1] = p[1];
        kuplaj_patlama = 0;
        kuplaj_hazir = false;
        kuplaj_aktif = true;
        if (!skop_is_ver(SKOP_IS_DOKUM)) kuplaj_aktif = false;
      } else if (alt == '?') {
        skop_ayar_yaz();
      } else if (alt == 'a') {                    /* otomatik kurulum */
        /* B40b: tamami ayri gorevde (12 zaman tabanini tarayabilir,
           periyodik sinyal yoksa onlarca saniye). T satiri ve dokum
           sonuc gelince cekirdek 1'den. */
        skop_is_ver(SKOP_IS_OTOMATIK);
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
}

// ───────────────────────────────────────────────── HIZLI YOL (B8)
//
// ESP32-S3'un dahili ADC'sini IKI kanalli surekli kipte kullanip gercek
// gucu hesaplar. Osiloskop kanalindan (GPIO4, gerilim) ve hizli akim
// kanalindan (GPIO5, fark yukselteci cikisi) es zamanli olmayan ama
// SABIT KAYMALI ornekler gelir.
//
// KAYMA: `sample_freq_hz` TOPLAM donusum hizidir. pattern_num = 2 ile
// akis V,I,V,I... gider; V ile I arasi tam 1/83333 = 12.000 us, kanal
// periyodu 24 us -> kayma TAM YARIM ORNEK. Bu bir sans: dogrusal fazli
// bir FIR ile TAM olarak duzeltilebiliyor (olcum3.h: hizala_yarim).
//
// KANAL SIRASI INDEKS PARITESINDEN CIKARILMAZ. Her zaman `type2.channel`
// alanindan demux edilir — DMA bir cerceve dusurursa parite kayar ve
// V ile I yer degistirir. `skop_yakala()` da bunu boyle yapiyor.

static const uint8_t HIZLI_KANAL_V = SKOP_KANAL;   // GPIO4, ADC1_CH3
static const uint8_t HIZLI_KANAL_I = 4;            // GPIO5, ADC1_CH4

// Pencere: guc_olc kenarlardan 3 ornek dusuruyor.
// 300 ornek @ 41 666.5 Sa/s = 7.2 ms. 50 Hz'te bu yalnizca 0.36 cevrim —
// pencere yanliligi buyuk olur. Bu yuzden COK PENCERE toplaniyor.
#define HIZLI_ADET 300u
static float hizli_v[HIZLI_ADET];
static float hizli_i[HIZLI_ADET];

static bool hizli_kur(void) {
    if (!skop_kulp) return false;
    adc_durdur();               /* config CALISAN surucuye uygulanamaz */
    static adc_digi_pattern_config_t d[2];
    d[0] = (adc_digi_pattern_config_t){};
    d[0].atten = ADC_ATTEN_DB_12;
    d[0].channel = HIZLI_KANAL_V;
    d[0].unit = ADC_UNIT_1;
    d[0].bit_width = ADC_BITWIDTH_12;
    d[1] = d[0];
    d[1].channel = HIZLI_KANAL_I;

    adc_continuous_config_t c = {};
    c.pattern_num = 2;
    c.adc_pattern = d;
    c.sample_freq_hz = SKOP_HZ_AZAMI;      // TOPLAM; kanal basina yarisi
    c.conv_mode = ADC_CONV_SINGLE_UNIT_1;
    c.format = ADC_DIGI_OUTPUT_FORMAT_TYPE2;
    return adc_continuous_config(skop_kulp, &c) == ESP_OK;
}

// Bir pencere yakalar. Basarisizsa false.
static bool hizli_yakala(uint16_t *alinan_v, uint16_t *alinan_i) {
    uint16_t nv = 0, ni = 0;
    static uint8_t ham[1024];
    uint32_t okundu = 0;
    uint32_t basla = millis();

    while ((nv < HIZLI_ADET || ni < HIZLI_ADET) && millis() - basla < 200u) {
        if (adc_continuous_read(skop_kulp, ham, sizeof(ham), &okundu, 100)
            != ESP_OK) continue;
        for (uint32_t o = 0; o + SOC_ADC_DIGI_RESULT_BYTES <= okundu;
             o += SOC_ADC_DIGI_RESULT_BYTES) {
            adc_digi_output_data_t *s = (adc_digi_output_data_t *)&ham[o];
            uint16_t kod = s->type2.data;
            // KANAL ALANINDAN demux — indeks paritesinden DEGIL
            if (s->type2.channel == HIZLI_KANAL_V) {
                if (nv < HIZLI_ADET) hizli_v[nv++] = (float)kod;
            } else if (s->type2.channel == HIZLI_KANAL_I) {
                if (ni < HIZLI_ADET) hizli_i[ni++] = (float)kod;
            }
        }
    }
    *alinan_v = nv;
    *alinan_i = ni;
    return nv >= 8u && ni >= 8u;
}

// Ham ADC kodlarini VOLT ve AMPER'e cevirir.
//
// Gerilim: skop bolucusu (SKOP_ORAN), B19'dan beri VREF referansli
//          (bolucunun alt ucu VREF'te) -> v = (Vadc - VREF) * ORAN
// Akim   : fark yukselteci G = HIZLI_KAZANC, cikis VREF'e merkezli.
//          i = (Vcikis - VREF) / G / sont
/* 🔴 B39 — DOGRUSAL ADC MODELI HIZLI YOLDA BUYUK HATA VERIYORDU.
   `guc_olc` ORTALAMAYI CIKARMIYOR: P = ort(v*i), Vrms = sqrt(ort(v^2)).
   Yani ADC modelinin orta olcekteki OFSET hatasi dogrudan guce giriyor.
   Tasarim degerleriyle, kartin eFuse tablosundan hesap (2026-09-13):
       sifir giris (dugum 1670 mV):  dogrusal model  -6.93 V   kalibre  0.00 V
       sifir akim  (dugum 1715 mV):  dogrusal model  -397 mA   kalibre  0 mA
       10 Vrms / 100 mA direncsel:   P 3.56 W, PF 0.77         P 1.00 W, PF 1.00
   eFuse olcegi fizikle sinandi: PWM ortalamasi (gorev x rail) karsisinda
   egim 3296 mV (%0.1), artik rms 4.6 mV; dogrusal model egimi %8.8 dusuk.
   GPIO5'in egriligi GPIO4'unkiyle AYNI olculdu (B38) — ayni tablo iki
   kanala da uygulanabiliyor.
   ⚠ Kalan belirsizlik ~22 mV kesme (eFuse ofseti mi rail mi, multimetresiz
     ayrilamiyor): girisde ~0.8 V / ~47 mA. On uc kurulunca SIFIR
     kalibrasyonu yine gerekecek — bu duzeltme onun yerini tutmuyor.
   Tablo yoksa ESKI dogrusal yol; `W` satirinin son alani bunu soyluyor. */
static void hizli_olcekle(uint16_t adet) {
    const float lsb = SKOP_ADC_TAVAN / SKOP_ADC_SAYIM;
    const float vref = VREF_NOMINAL;
    for (uint16_t n = 0; n < adet; n++) {
        float vd = kal_tab_var ? kal_mv(hizli_v[n]) / 1000.0f : hizli_v[n] * lsb;
        float vc = kal_tab_var ? kal_mv(hizli_i[n]) / 1000.0f : hizli_i[n] * lsb;
        hizli_v[n] = vref + (vd - vref) * SKOP_ORAN;
        hizli_i[n] = (vc - vref) / HIZLI_KAZANC / ayar.sont_ohm
                     * ayar.i_duzeltme;
    }
}

/* 🔴 B37 — BOS PIN SINAMASI (`wB`): "giris RAYDA" korumasinin DELIGI.
   B27/K3 bos girisin 223 W basmasini "ortalama bir raya yapisik mi"
   diye yakaliyordu. B36'da gorüldu: bostaki GPIO5'in ortalamasi
   tesadufen ORTA olcekte (787) kaliyor, koruma deliniyor ve `w`
   7.68 W / PF 0.98 basiyor — hicbir sinyali temsil etmeyen ama
   kendinden emin bir sayi.

   Sinyal istatistigine dayanan bir esik (yayilim, ardisik fark)
   uydurmak yerine DETERMINISTIK bir yontem: dahili pull-down ile oku,
   pull-up ile oku. Bos (yuksek empedansli) pin cekmeyi izler ve iki
   okuma arasinda tam olcege yakin kayar; dusuk empedansli bir kaynak
   (op-amp cikisi ~0 ohm, skop bolucusu ~2.6K, RC duzenegi 10K) 45K'lik
   dahili cekmeye direnir ve kayma kucuk kalir:
   KARTTA OLCULDU (2026-09-13, DMA sifirlamasindan sonra, +-2 kod):
       BOS pin (GPIO5; CAL kapaliyken GPIO4)        %100  (4095 kod)
       RC duzenegi (Thevenin 20K = iki kademe seri)  %41-50 (1666-2054)
   Hesap (olculen kaymadan geri cikarilan dahili cekme ~25K, 45K DEGIL):
       skop bolucusu (100K/2.7K -> VREF, ~2.6K)      ~%10
       op-amp cikisi (hizli akim kanali, ~0 ohm)     ~%0
   Esik %75: surulu tarafa da bos tarafa da 25 puan pay. Ilk yazim %50
   idi ve RC duzenegi %90 gorevde 2054 kodla esigi ASIYORDU — surulu
   pin "bos" sayilirdi. Iki taraf olculmeseydi bu gorulmezdi.

   ⚠ Cekme degistirilince RC duzenegi (100 nF) yavas oturur: tau = 45K x
     100nF = 4.5 ms, 30 ms bekleniyor. Islem sonunda cekme KAPATILIYOR
     ve skop yapilandirmasi geri kuruluyor. */
/* 🔴 B39 — `w` OLCUM DONGUSUNU 123 ms BLOKLUYORDU (kartta olculdu).
   B37'nin cekme sinamasi 3 x 30 ms bekleme + iki TAM (300 ornek)
   yakalama ekliyordu ve B37'de bu bedel OLCULMEDI. Duzeltme:
     * bekleme OLCULEN oturma suresine indirildi (`wB<ms>` ile olculur)
     * sinama 64 ornek/kanal ile yapiliyor (esik %75'e karsi fazlasiyla)
     * okuyucu YIKICI DEGIL: hizli_v/hizli_i dizilerine yazmiyor, yani
       sinama ASIL yakalamadan SONRA yapilabiliyor ve serbest birakma
       beklemesine gerek kalmiyor.
   CEKME_BEKLE_MS asagida, olcumle birlikte. */
#define CEKME_ORNEK 64u

static bool hizli_kanal_oku_ort(float *v_ort, float *i_ort) {
    static uint8_t ham[512];
    uint32_t okundu = 0, basla = millis();
    uint16_t nv = 0, ni = 0;
    float vt = 0, it = 0;
    while ((nv < CEKME_ORNEK || ni < CEKME_ORNEK) && millis() - basla < 100u) {
        if (adc_continuous_read(skop_kulp, ham, sizeof(ham), &okundu, 20)
            != ESP_OK) continue;
        for (uint32_t o = 0; o + SOC_ADC_DIGI_RESULT_BYTES <= okundu;
             o += SOC_ADC_DIGI_RESULT_BYTES) {
            adc_digi_output_data_t *s = (adc_digi_output_data_t *)&ham[o];
            if (s->type2.channel == HIZLI_KANAL_V) {
                if (nv < CEKME_ORNEK) { vt += s->type2.data; nv++; }
            } else if (s->type2.channel == HIZLI_KANAL_I) {
                if (ni < CEKME_ORNEK) { it += s->type2.data; ni++; }
            }
        }
    }
    if (nv < 8u || ni < 8u) return false;
    *v_ort = vt / nv; *i_ort = it / ni;
    return true;
}

/* Belirli bir cekme kipinde iki kanalin ortalamasini olcer.

   🔴 HER OLCUM ONCESI SURUCU DURDURULUP YENIDEN BASLATILIYOR. Ilk
      yazimda cekme degistirilip 30 ms beklenip dogrudan okunuyordu ve
      GPIO4'un kaymasi -1557..+2728 kod arasinda, ISARET DEGISTIREREK
      geliyordu (beklenen: hep ~+740). Sebep: surekli ADC'nin DMA
      halkasi cekme DEGISMEDEN ONCEKI ornekleri tutuyor; `hizli_yakala`
      once o bayat veriyi okuyor. GPIO5 (bos) yine de yakalaniyordu
      cunku kayma o kadar buyuk ki bayat veri bile onu gizleyemiyor —
      yani kusur yalnizca "surulu" tarafta gorunuyordu. Iki tarafi da
      olcmeseydik bu gorulmezdi. `adc_continuous_start` DMA'yi sifirlar. */
static bool hizli_cekmeli_oku(gpio_pull_mode_t kip, uint16_t bekle_ms,
                              float *v_ort, float *i_ort) {
    adc_durdur();
    gpio_set_pull_mode((gpio_num_t)PIN_SKOP,    kip);
    gpio_set_pull_mode((gpio_num_t)PIN_HIZLI_I, kip);
    delay(bekle_ms);                            /* oturma — CEKME_BEKLE_MS */
    if (adc_baslat() != ESP_OK) return false;
    bool tamam = hizli_kanal_oku_ort(v_ort, i_ort);
    adc_durdur();
    return tamam;
}

/* Iki kanalin cekme kaymasini olcer (kod cinsinden, pull-up - pull-down).
   Basarisizsa false. Cagiran taraf ADC'yi cift kanalli KURMUS olmali
   (baslatmis olmasi gerekmiyor; burada baslatilip durduruluyor). */
static bool hizli_cekme_kaymasi(float *v_kayma, float *i_kayma,
                                uint16_t bekle_ms) {
    float vd = 0, id = 0, vu = 0, iu = 0;
    bool a = hizli_cekmeli_oku(GPIO_PULLDOWN_ONLY, bekle_ms, &vd, &id);
    bool b = hizli_cekmeli_oku(GPIO_PULLUP_ONLY,   bekle_ms, &vu, &iu);
    /* Serbest birakma BEKLEMESIZ: sinama artik asil yakalamadan SONRA ve
       bir sonraki okuma seri porttan gelecek bir komutla, onlarca ms
       sonra. */
    gpio_set_pull_mode((gpio_num_t)PIN_SKOP,    GPIO_FLOATING);
    gpio_set_pull_mode((gpio_num_t)PIN_HIZLI_I, GPIO_FLOATING);
    if (!a || !b) return false;
    *v_kayma = vu - vd; *i_kayma = iu - id;
    return true;
}

#define BOS_PIN_ESIK_KOD (SKOP_ADC_SAYIM * 0.75f)  /* %75 tam olcek — gerekce yukarida */
/* B39 — bekleme OLCULDU (2026-09-13, `wB<ms>`, 3'er tekrar, +-1 puan):
       bekle   surulu (RC 20K kaynak)   kaynaksiz 100 nF (CAL kapali)
         3 ms        %60                    %56   <- YANLIS: surulu sayilir
         5 ms        %63                    %77   <- esige 2 puan
         8 ms        %63                    %94
        12 ms        %63                   %100
   8 ms: iki tarafta da >= 12 puan pay. Kaynaksiz 100 nF yalnizca bu
   tezgahta var ve EN ZOR "bos" durumu; ciplak baglantisiz bir pin pF'lik
   kapasitesiyle mikrosaniyede oturur. 30 ms (B37) gereksiz uzundu. */
#define CEKME_BEKLE_MS 8u

static void hizli_bos_yolla(uint16_t bekle_ms) {
    if (!skop_kulp) { Serial.println(F("! bos sinama: ADC kulpu yok")); return; }
    adc_durdur();
    if (!hizli_kur()) {
        Serial.println(F("! bos sinama: 2 kanalli yapilandirma basarisiz"));
        skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
        return;
    }
    float vk = 0, ik = 0;
    bool tamam = hizli_cekme_kaymasi(&vk, &ik, bekle_ms);
    if (!tamam) {
        Serial.println(F("! bos sinama: ornek alinamadi"));
    } else {
        Serial.print(F("WB v_kayma="));  Serial.print(vk, 1);
        Serial.print(F(" v_yuzde="));    Serial.print(100.0f * vk / SKOP_ADC_SAYIM, 0);
        Serial.print(F(" v_bos="));      Serial.print(vk > BOS_PIN_ESIK_KOD ? 1 : 0);
        Serial.print(F(" i_kayma="));    Serial.print(ik, 1);
        Serial.print(F(" i_yuzde="));    Serial.print(100.0f * ik / SKOP_ADC_SAYIM, 0);
        Serial.print(F(" i_bos="));      Serial.print(ik > BOS_PIN_ESIK_KOD ? 1 : 0);
        Serial.print(F(" esik="));       Serial.print(BOS_PIN_ESIK_KOD, 0);
        Serial.print(F(" bekle_ms="));   Serial.println(bekle_ms);
    }
    skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
}

/* 🔴 B36 — HIZLI KANALLARIN HAM KODU (`wR`).
   Neden gerekiyor: B34'te ADC dogrusalsizligi OLCULDU ama yalnizca
   GPIO4'te, cunku ham kodu disari veren TEK yol skop yakalamasi ve
   skop yalnizca SKOP_KANAL'i okuyor. GPIO5 (hizli AKIM kanali, ADC1_CH4)
   bugune kadar HIC karakterize edilmedi — ve guc faktorunun BASKA
   KAYNAGI YOK (ADS yolu 487 SPS ile PF veremez).

   ⚠ `w`nin "giris RAYDA" korumasi burada BILEREK YOK. O koruma bos
     girisin 223 W basmasini engelliyor (B27/K3) ve dogru; ama
     dogrusallik supurmesi tam da rayin yakinini olcmek zorunda.
     Bu komut WATT BASMIYOR, yalnizca HAM KOD basiyor — yani "olculmus
     guc" gibi gorunen bir sey uretmiyor.

   Ayrica GPIO4'u de basiyor: B34'un skop yoluyla yaptigi supurme ile
   BAGIMSIZ bir yoldan karsilastirilabilsin. Ayni pin, iki farkli okuma
   zinciri; ayrisirlarsa biri yanlistir. */
static void hizli_ham_yolla(void) {
    if (!skop_kulp) { Serial.println(F("! hizli ham: ADC kulpu yok")); return; }
    adc_durdur();
    if (!hizli_kur()) {
        Serial.println(F("! hizli ham: 2 kanalli yapilandirma basarisiz"));
        skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
        return;
    }
    if (adc_baslat() != ESP_OK) {
        Serial.println(F("! hizli ham: baslatilamadi"));
        skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
        return;
    }
    uint16_t nv = 0, ni = 0;
    bool tamam = hizli_yakala(&nv, &ni);
    adc_durdur();
    if (!tamam) {
        Serial.print(F("! hizli ham: yeterli ornek yok  V="));
        Serial.print(nv); Serial.print(F(" I=")); Serial.println(ni);
        skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
        return;
    }
    /* `hizli_olcekle` CAGRILMIYOR — diziler ham kod olarak kaliyor. */
    float v_top = 0, i_top = 0;
    uint16_t v_min = 0xFFFF, v_max = 0, i_min = 0xFFFF, i_max = 0;
    for (uint16_t n = 0; n < nv; n++) {
        uint16_t k = (uint16_t)hizli_v[n];
        v_top += hizli_v[n];
        if (k < v_min) v_min = k;
        if (k > v_max) v_max = k;
    }
    for (uint16_t n = 0; n < ni; n++) {
        uint16_t k = (uint16_t)hizli_i[n];
        i_top += hizli_i[n];
        if (k < i_min) i_min = k;
        if (k > i_max) i_max = k;
    }
    Serial.print(F("WR v_ort="));  Serial.print(v_top / nv, 3);
    Serial.print(F(" v_min="));    Serial.print(v_min);
    Serial.print(F(" v_max="));    Serial.print(v_max);
    Serial.print(F(" v_n="));      Serial.print(nv);
    Serial.print(F(" i_ort="));    Serial.print(i_top / ni, 3);
    Serial.print(F(" i_min="));    Serial.print(i_min);
    Serial.print(F(" i_max="));    Serial.print(i_max);
    Serial.print(F(" i_n="));      Serial.println(ni);
    skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
}

// `w` komutu — bir pencere yakalayip gucu raporlar.
//
// PROTOKOL:
//   W <P> <S> <PF> <Vrms> <Irms> <Vort> <Iort> <n> <P_hizalamasiz> <kal>
//
// B39: 11. alan `kal` = 1 ise olcekleme eFuse tablosuyla, 0 ise ESKI
// dogrusal modelle yapildi (girisde 7 V'a varan ofset). Susmuyoruz:
// kalibresiz bir PF "olculmus" gibi gorunmemeli. Eski arayuz 10 alana
// bakiyor, 11. alan onu bozmuyor.
//
// Son alan BILEREK var: hizalamanin ne kadar fark ettigini arayuz
// gosterebilsin. Dirençsel yukte ikisi ayni cikar, reaktif yukte
// duzeltmesiz olan belirgin sapar (B8: 1 kHz PF=0.1'de %78).
static void hizli_yolla(void) {
    if (!skop_kulp) { Serial.println(F("! hizli yol: ADC kulpu yok")); return; }

    // Skop yapilandirmasini birak, iki kanalliya gec
    adc_durdur();
    if (!hizli_kur()) {
        Serial.println(F("! hizli yol: 2 kanalli yapilandirma basarisiz"));
        return;
    }
    if (adc_baslat() != ESP_OK) {
        Serial.println(F("! hizli yol: baslatilamadi"));
        return;
    }

    uint16_t nv = 0, ni = 0;
    bool tamam = hizli_yakala(&nv, &ni);
    adc_durdur();

    /* 🔴 B37 — BOS PIN KAPISI. K3'un "ortalama rayda mi" korumasi
       bostaki GPIO5'in ortalamasi orta olcekte kalinca deliniyordu ve
       `w` 7.68 W / PF 0.98 basiyordu. Cekme sinamasi deterministik:
       bos pin cekmeyi izler. Bos girisle GUC BASILMAZ, sebep yazilir.
       B39: sinama ASIL yakalamadan SONRA — okuyucu yikici degil, cekmenin
       dugumde biraktigi yuk olcumu etkilemiyor, serbest birakma beklemesi
       gerekmiyor. */
    if (tamam) {
        float vk = 0, ik = 0;
        if (hizli_cekme_kaymasi(&vk, &ik, CEKME_BEKLE_MS)) {
            bool v_bos = vk > BOS_PIN_ESIK_KOD, i_bos = ik > BOS_PIN_ESIK_KOD;
            if (v_bos || i_bos) {
                Serial.print(F("! hizli yol: giris BOSTA — cekme sinamasi:"));
                Serial.print(F(" GPIO4 %")); Serial.print(100.0f * vk / SKOP_ADC_SAYIM, 0);
                Serial.print(v_bos ? F(" BOS") : F(" surulu"));
                Serial.print(F(" · GPIO5 %")); Serial.print(100.0f * ik / SKOP_ADC_SAYIM, 0);
                Serial.print(i_bos ? F(" BOS") : F(" surulu"));
                Serial.println(F("  (on uc bagli degil)"));
                skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
                return;   /* B37: W BASILMAZ */
            }
        }
    }

    if (!tamam) {
        Serial.print(F("! hizli yol: yeterli ornek yok  V="));
        Serial.print(nv); Serial.print(F(" I=")); Serial.println(ni);
        return;
    }

    uint16_t adet = (nv < ni) ? nv : ni;

    /* 🔴 B27/K3 (2026-09-12, GERCEK KARTTA gorüldu) — BOS GIRIS 223 W
       BASIYORDU. GPIO4 ve akim kanali hicbir seye bagli degilken ham ADC
       raya yapisik (~0) okunuyor; olcekleme onu -63.5 V'a, akim kanalini
       3.5 A'e cevirip P = 223.5667 W diye DORT ondalikla basiyordu. Sayi
       hicbir sinyali temsil etmiyordu ama kendinden emin duruyordu.

       OLCUT: ham kodlarin ORTALAMASI bir raya yapisik (<%2 ya da >%98).
       On uc alt ucu VREF'e cektigi icin gecerli bir sinyalin DC'si ORTA
       olcekte durur — tam olcekli AC bile ortalamada oradadir. Ortalama
       raydaysa ya on uc bagli degil (bos giris) ya da sinyal kirpilmis;
       iki durumda da olcum gecersiz ve W BASILMIYOR.

       ⚠ Ilk yazim "VE yayilim < 41 LSB" da istiyordu ve kartta KACIRDI:
       bostaki pin GURULTULUDUR (ham ort 14 LSB ama yayilim >41), sart
       tutmadi ve 218 W yine basildi. Yayilim, rayda olmanin kaniti
       degil; ortalama yeter. */
    {
        float v_min = 1e9f, v_max = -1e9f, v_top = 0, i_min = 1e9f, i_max = -1e9f, i_top = 0;
        for (uint16_t n = 0; n < adet; n++) {
            if (hizli_v[n] < v_min) v_min = hizli_v[n];
            if (hizli_v[n] > v_max) v_max = hizli_v[n];
            v_top += hizli_v[n];
            if (hizli_i[n] < i_min) i_min = hizli_i[n];
            if (hizli_i[n] > i_max) i_max = hizli_i[n];
            i_top += hizli_i[n];
        }
        const float alt = SKOP_ADC_SAYIM * 0.02f, ust = SKOP_ADC_SAYIM * 0.98f;
        float v_ort = v_top / adet, i_ort = i_top / adet;
        bool v_rayda = (v_ort < alt || v_ort > ust);
        bool i_rayda = (i_ort < alt || i_ort > ust);
        (void)v_min; (void)v_max; (void)i_min; (void)i_max;
        if (v_rayda || i_rayda) {
            Serial.print(F("! hizli yol: giris RAYDA — sinyal yok"));
            if (v_rayda) { Serial.print(F("  V ham ort=")); Serial.print(v_ort, 0); }
            if (i_rayda) { Serial.print(F("  I ham ort=")); Serial.print(i_ort, 0); }
            Serial.println(F("  (bos giris ya da on uc bagli degil)"));
            return;   /* K3: W BASILMAZ */
        }
    }

    hizli_olcekle(adet);

    GucOlcum g, g0;
    guc_olc(hizli_v, hizli_i, adet, 1u, &g);    // hizalamali
    guc_olc(hizli_v, hizli_i, adet, 0u, &g0);   // hizalamasiz (kiyas)

    Serial.print(F("W "));
    Serial.print(g.p, 5);      Serial.print(' ');
    Serial.print(g.s, 5);      Serial.print(' ');
    Serial.print(g.pf, 4);     Serial.print(' ');
    Serial.print(g.v_rms, 4);  Serial.print(' ');
    Serial.print(g.i_rms, 5);  Serial.print(' ');
    Serial.print(g.v_ort, 4);  Serial.print(' ');
    Serial.print(g.i_ort, 5);  Serial.print(' ');
    Serial.print(g.n);         Serial.print(' ');
    Serial.print(g0.p, 5);     Serial.print(' ');
    Serial.println(kal_tab_var ? 1 : 0);

    // PENCERE YANLILIGI — susmak yerine soyle.
    // 300 ornek @ 41.7 kSa/s = 7.2 ms. 50 Hz'te 0.36 cevrim eder ve
    // yanlilik buyuk olur (B8 olctu: 2.75 cevrimde %2.6).
    float pencere_s = (float)adet / (float)(SKOP_HZ_AZAMI / 2u);
    Serial.print(F("  pencere ")); Serial.print(pencere_s * 1e3f, 2);
    Serial.print(F(" ms — 50 Hz'te "));
    Serial.print(50.0f * pencere_s, 2);
    Serial.println(F(" cevrim (1 cevrimin altinda yanlilik BUYUK)"));

    // Skop yapilandirmasini geri kur
    skop_hiz_ayarla(skop_hz ? skop_hz : SKOP_HZ_AZAMI);
}

// ───────────────────────────────────────────────── enerji
//
// Asama 2'nin `enerji_biriktir`inin ISARETLI karsiligi. Oradaki iki
// koruma aynen korundu:
//   * dt tasma sarmali ile dogru hesaplaniyor (uint32 cikarma)
//   * cok uzun aralik (ilk tur, duraklama, seri komut) ATLANIYOR —
//     yoksa tek bir 10 saniyelik bosluk sayaca sahte enerji yazar
void enerji_biriktir(float watt) {
  uint32_t simdi = micros();
  uint32_t dt = simdi - son_us;      // taşma sarmalı doğru çalışır
  son_us = simdi;
  if (dt > 1000000UL) {
    // 🔴 B22.1: bu aralik ATLANIYOR ve eskiden SESSIZDI. Atmak dogru
    // (tek watt ornegini 10 saniyeye yaymak sahte enerji yazar), ama
    // KAC saniye kaybedildigi kullaniciya soylenmeli — yoksa sayac
    // "biraz dusuk" okur ve kimse sebebini bilmez.
    enerji_kayip_ms += dt / 1000UL;
    k_degisti = 1;
    return;
  }
  enerji_pJ = enerji_ekle3(enerji_pJ, watt, dt);
}

// ───────────────────────────────────────────────── B21 PIL TESTI
//
// 🔴 KAPI YONU: Q1'in kapisi R42 ile GND'ye CEKILI. Buradaki her
//    "kapat" cagrisi yalnizca YARDIMCI — asil emniyet donanimda.
//    ESP32 olurse/reset atarsa kapi kendiliginden 0 V'a iner.
static void pil_yuk(bool ac) {
  digitalWrite(PIN_PIL_KAPI, ac ? HIGH : LOW);
}

static const char *pil_hata_metni(uint8_t h) {
  switch (h) {
    case PILH_GERILIM_DUSUK:  return "gerilim zaten kesmenin altinda";
    case PILH_GERILIM_YUKSEK: return "gerilim 38.5 V ustunde (MOSFET Vdss)";
    case PILH_TERS:           return "TERS POLARITE";
    case PILH_BAYPAS:         return "MOSFET kapali ama AKIM VAR — yuk J3'e "
                                     "baglanmis olmali, J7'ye tak";
    case PILH_SURE:           return "azami sure asildi";
    case PILH_AKIM_YOK:       return "yuk baglanmadi (akim akmadi)";
    default:                  return "-";
  }
}

static const char *pil_durum_metni(uint8_t d) {
  switch (d) {
    case PIL_CALISIYOR:   return "CALISIYOR";
    case PIL_BITTI:       return "BITTI";
    case PIL_DURDURULDU:  return "DURDURULDU";
    case PIL_HATA:        return "HATA";
    default:              return "BEKLEMEDE";
  }
}

static void pil_durdur(uint8_t yeni_durum, uint8_t hata) {
  pil_yuk(false);
  pil.durum = yeni_durum;
  pil.hata = hata;
  pil.bitis_ms = millis();
  pil.dcir_icinde = 0;
}

// Testi baslat. Once MOSFET'i KAPALI tutup olcuyoruz: bu hem OCV'yi
// veriyor hem de BAYPAS denetimini yapiyor.
static void pil_baslat() {
  pil_yuk(false);
  delay(50);                       // olcumun oturmasi icin
  Okuma3 o = olcum_al();
  uint8_t h = pil_baslatilabilir(o.volt, o.amper, ayar.pil_kesme_v);
  if (h != PILH_YOK) {
    pil_sifirla(&pil);
    pil.durum = PIL_HATA;
    pil.hata = h;
    Serial.print(F("! pil testi REDDEDILDI: "));
    Serial.println(pil_hata_metni(h));
    return;
  }
  pil_sifirla(&pil);
  pil_halka_sifirla(&pil_halka);
  pil.v_bas = o.volt;              // OCV (yuk yokken)
  pil.durum = PIL_CALISIYOR;
  pil.baslama_ms = millis();
  pil.son_kayit_ms = pil.baslama_ms;
  pil.son_dcir_ms = pil.baslama_ms;
  pil_yuk(true);
  Serial.print(F("* pil testi BASLADI — OCV "));
  Serial.print(o.volt, 4);
  Serial.print(F(" V, kesme "));
  Serial.print(ayar.pil_kesme_v, 3);
  Serial.println(F(" V"));
}

// Her olcumden sonra cagriliyor. Durum makinesi + kayit + DCIR.
static void pil_isle(const Okuma3 &o, uint32_t dt_us) {
  if (pil.durum != PIL_CALISIYOR) return;
  uint32_t ms = millis();

  // --- emniyet: azami sure
  if (ayar.pil_azami_s && (ms - pil.baslama_ms) / 1000UL > ayar.pil_azami_s) {
    pil_durdur(PIL_HATA, PILH_SURE);
    Serial.println(F("! pil testi: azami sure asildi, yuk kesildi"));
    return;
  }

  // --- DCIR darbesi icindeysek
  if (pil.dcir_icinde) {
    if (ms - pil.dcir_bas_ms == 0) return;      // ilk tur, henuz olcum yok
    if (pil.dcir_sayisi == 0 || pil.dcir_ani == 0.0f) {
      // darbeden SONRAKI ILK ornek — "ani" deger
      pil.dcir_ani = pil_dcir(pil.dcir_v_once, o.volt, pil.dcir_i_once);
    }
    if (ms - pil.dcir_bas_ms >= (uint32_t)(PIL_DCIR_MS)) {
      pil.dcir_oturmus = pil_dcir(pil.dcir_v_once, o.volt, pil.dcir_i_once);
      pil.dcir_sayisi++;
      pil.dcir_icinde = 0;
      pil.son_dcir_ms = ms;
      pil_yuk(true);
    }
    return;                                      // darbe boyunca BIRIKTIRME
  }

  // --- normal birikim
  pil.yuk_pC = yuk_ekle3(pil.yuk_pC, o.amper, dt_us);
  pil.enerji_pJ = enerji_ekle3(pil.enerji_pJ, o.watt, dt_us);
  pil.v_son = o.volt;

  // --- egri kaydi
  uint32_t kayit_ms = (uint32_t)(1000.0f / (ayar.pil_kayit_hz > 0.01f
                                            ? ayar.pil_kayit_hz : 1.0f));
  if (ms - pil.son_kayit_ms >= kayit_ms) {
    pil_halka_ekle(&pil_halka, ms - pil.baslama_ms, o.volt, o.amper);
    pil.son_kayit_ms = ms;
  }

  // --- KESME
  if (pil_kesmeli_mi(o.volt, ayar.pil_kesme_v)) {
    pil_durdur(PIL_BITTI, PILH_YOK);
    Serial.print(F("* pil testi BITTI — "));
    Serial.print(yuk_mAh3(pil.yuk_pC), 2);
    Serial.print(F(" mAh, "));
    Serial.print(enerji_wh3(pil.enerji_pJ), 4);
    Serial.println(F(" Wh"));
    return;
  }

  // --- DCIR darbesi zamani mi
  if (ms - pil.son_dcir_ms >= (uint32_t)(PIL_DCIR_ARALIK_MS)) {
    pil.dcir_v_once = o.volt;
    pil.dcir_i_once = o.amper;
    pil.dcir_ani = 0.0f;
    pil.dcir_icinde = 1;
    pil.dcir_bas_ms = ms;
    pil_yuk(false);
  }
}

// ───────────────────────────────────────────────── HTTP
// B22.5'te burasi LittleFS'ten gercek arayuzu servis edecek. Su an ne
// yapilacagini YAZIYOR — bos bir sayfa birakmak, kullaniciyi "calismiyor"
// sanisina iter.
void kok_sayfa() {
  // 🔴 `index.htm` TUZAGI: `serveStatic` dizin istegini
  //    `requestUri + "index.htm"` ile karsiliyor
  //    (RequestHandlersImpl.h:198) — `index.html` DEGIL. Dosyayi
  //    `index.htm` diye adlandirmak yerine ACIK bir kok isleyicisi
  //    konuyor: dosya adi alisildik kaliyor ve tuzak koda YAZILI oluyor.
  if (fs_hazir) {
    File f = LittleFS.open("/index.html.gz", "r");
    if (f && f.size()) {
      // `streamFile` .gz uzantisini gorup Content-Encoding'i KENDISI
      // koyuyor. ⚠ index.html `immutable` OLMAMALI: yoksa arayuz
      // guncellemesi tarayiciya HIC ulasmaz.
      sunucu.sendHeader(F("Cache-Control"), F("no-cache"));
      sunucu.streamFile(f, "text/html");
      f.close();
      return;
    }
  }
  String g = F("Olcum Karti — Asama 3\n\n");
  g += F("Arayuz karta YUKLENMEMIS (LittleFS bos ya da acilmadi).\n");
  g += F("Yuklemek icin:\n");
  g += F("  python uretim/arayuz-uret.py\n");
  g += F("  python uretim/arayuz-yaz.py\n\n");
  g += F("Arayuzu bilgisayardan da calistirabilirsiniz:\n");
  g += F("  python arayuz3/sunucu.py     (USB)\n");
  g += F("  python kopru/kopru.py        (kopru — telefon icin)\n\n");
  g += F("Uclar:\n");
  g += F("  GET  /akis    SSE olcum akisi (tum protokol satirlari)\n");
  g += F("  GET  /pil     pil testi durumu + egri\n");
  g += F("  POST /komut   komut (X-Olcum: 1 basligi ve jeton gerekli)\n");
  g += F("  POST /kopru   PC koprusu kaydi\n\n");
  g += F("Ag: ");
  g += ag_kip_adi(ag_durum.kip);
  g += F("  SSID=");   g += ag_durum.ssid;
  g += F("  IP=");     g += ag_durum.ip;
  g += F("\nmDNS: ");
  g += ag_durum.mdns ? F("http://" AG_MDNS ".local") : F("YOK");
  g += F("\n");
  sunucu.send(200, "text/plain", g);
}

// 🔴 B20 (2026-09-10) — BU ISLEV loop()'U SONSUZA KADAR KILITLIYORDU.
//
// Eski govde soyleydi:
//     while (c.connected()) { ...; delay(20); sunucu.handleClient(); }
// akis_sayfa, loop() icindeki sunucu.handleClient()'tan cagriliyor.
// Dongu istemci bagli kaldigi surece geri donmedigi icin loop() da geri
// donmuyordu: olcum_al() kosmuyor, enerji_biriktir() kosmuyor, ornek
// sayaci artmiyordu. Daha kotusu son_satir[] YALNIZCA loop() tarafindan
// yaziliyor — yani akis ilk (bayat) satiri gonderip SONSUZA KADAR
// susuyordu. Islev kendi amacini bile yerine getirmiyordu. Ayrica
// icerideki sunucu.handleClient() ayni sayfayi IC ICE cagirabiliyordu.
//
// Etkisi olculdu (uretim/sim3_bant.py): istemci bagliyken etkin
// ornekleme 0 SPS. Blokaj bitince enerji_biriktir'in dt > 1 s korumasi
// devreye girip o araligi ATLIYOR, yani blokaj boyunca harcanan TUM
// enerji sayaca hic girmiyor (1 dk @ 25 W -> 0.42 Wh kayip, %100).
//
// COZUM: durum makinesi. Islev yalnizca basliklari yazip HEMEN doner;
// istemci global `akis_istemci`de saklanir ve loop() her D satirini
// urettiginde ona yazilir. HTTP isleyicisi icinde while dongusu YOK.
// ───────────────────────────────────────────────── B21 pil testi ucu
//
// GET /pil?sira=N  ->  durum + N'den sonraki egri noktalari (CSV govde)
//
// Tarayici IndexedDB'de biriktiriyor ve yeniden baglaninca "bende
// N'e kadar var" diyor. Kart son 1.5 saati tutuyor; daha eskisi
// istenirse BOSLUK vardir ve yanit bunu ACIKCA soyluyor
// (ilk_sira > istenen). Arayuz o bosluğu grafikte ISARETLIYOR —
// sessizce interpolasyon YAPILMIYOR.
//
// ⚠ Isleyici BLOKLAMIYOR: tek seferde en cok PIL_YANIT_NOKTA nokta
//   gonderip donuyor. B20'de akis_sayfa()'nin loop()'u sonsuza kadar
//   kilitledigi gorulmustu; ayni hataya dusmuyoruz.
// 🔴 B22.5: 600 -> 150. Iki sebep:
//
// (1) BLOKAJ. 600 nokta ~15 KB gövde demek ve lwIP'in TCP_SND_BUF'u
//     ~5744 B: uc TCP penceresi, her biri ACK bekliyor. Isleyici
//     `loop()`'un icinde kostugu icin bu sure boyunca ORNEKLEME DURUYOR.
//     150 nokta ~3.8 KB — en kotu blokaj DORT KAT azaliyor.
//     Kayip yok: kayit 1 Hz, yoklama 2 s, yani kararli durumda zaten
//     ~2 nokta geliyor. 600 yalnizca yeniden baglanma dolgusunda
//     gerekiyordu ve istemci `kalan=` alanini gorup dongude cekiyor.
//
// (2) BITISIK BELLEK. Eski kod `g.reserve(64 + n*34)` ile TEK PARCA
//     20 464 B istiyordu. Saatlerce calismis, parcalanmis bir yiginda
//     bu ayirma BASARISIZ olabilir ve `String::concat` false doner —
//     ama `operator+=` bunu YUTUYOR. Sonuc: kesik govde + TUTARLI
//     Content-Length, yani tarayici hicbir hata gormeden eksik veri
//     aliyor. Artik parcali gonderiliyor, bitisik tampon gerekmiyor.
#define PIL_YANIT_NOKTA 150u
#define PIL_PARCA_BAYT 1024u

void pil_sayfa() {
  uint32_t istenen = 0;
  if (sunucu.hasArg("sira")) istenen = (uint32_t)sunucu.arg("sira").toInt();

  uint32_t ilk_yer = 0;
  uint32_t ilk_sira = 0;
  uint32_t kalan = pil_halka_bul(&pil_halka, istenen, &ilk_yer, &ilk_sira);
  uint32_t n = kalan > PIL_YANIT_NOKTA ? PIL_YANIT_NOKTA : kalan;

  // Parcali gonderim: uzunluk BILINMIYOR olarak isaretlenip govde
  // parca parca yollaniyor (chunked). Bitisik 20 KB'lik tampon YOK.
  sunucu.setContentLength(CONTENT_LENGTH_UNKNOWN);
  sunucu.send(200, "text/plain", "");

  String g;
  g.reserve(PIL_PARCA_BAYT + 128u);
  // 1. satir: durum
  g += F("durum=");     g += pil_durum_metni(pil.durum);
  g += F("\nhata=");    g += pil_hata_metni(pil.hata);
  g += F("\nmah=");     g += String(yuk_mAh3(pil.yuk_pC), 4);
  g += F("\nwh=");      g += String(enerji_wh3(pil.enerji_pJ), 6);
  g += F("\nocv=");     g += String(pil.v_bas, 4);
  g += F("\nvson=");    g += String(pil.v_son, 4);
  g += F("\nkesme=");   g += String(ayar.pil_kesme_v, 3);
  g += F("\ndcir_ani="); g += String(pil.dcir_ani, 5);
  g += F("\ndcir_otr="); g += String(pil.dcir_oturmus, 5);
  g += F("\ndcir_n=");  g += String(pil.dcir_sayisi);
  g += F("\nsira=");    g += String(pil_halka.sira);
  g += F("\nilk_sira="); g += String(ilk_sira);   // > istenen ise BOSLUK var
  g += F("\nkalan=");   g += String(kalan - n);
  g += F("\ncoulomb="); g += String(yuk_coulomb3(pil.yuk_pC), 3);
  g += F("\n--\n");
  // sonra: ms,V,I  (her satir bir nokta) — ~1 KB'lik parcalar halinde
  for (uint32_t k = 0; k < n; k++) {
    const PilNokta &q = pil_halka.nokta[(ilk_yer + k) % pil_halka.kapasite];
    g += String(q.ms);   g += ',';
    g += String(q.v, 4); g += ',';
    g += String(q.i, 6); g += '\n';
    if (g.length() >= PIL_PARCA_BAYT) {
      sunucu.sendContent(g);
      g = "";
    }
  }
  if (g.length()) sunucu.sendContent(g);
  sunucu.sendContent("");          // chunked akisin sonu
}

// ═══════════════════════════════════════ B22.5 — IKILI SKOP DOKUMU ═══
//
// 🔴 NEDEN AYRI UC: ASCII dokumu en kotu halde 4000 ornek x 5.06 B =
//    20 250 B. Bu, gercek zamanli kanalda (SSE) yolculuk EDEMEZ:
//    SSE metin tasiyicidir, ikiliyi base64'e sarmak %33 sisirir ve
//    dokum sirasinda `D` akisi durur.
//
//    Kural: BIR kanal kalp atisi icindir (D, 5 Hz, ~63 B), IKINCI kanal
//    toplu aktarim icindir (istek/yanit, ikili). Ikisi karismaz.
//
//    Ikili bicimde ayni veri 32 + 4000x2 = 8032 B — ASCII'nin %40'i.
//
// ⚠ HAM ADC KODU gonderiliyor, volt DEGIL — bugunku ASCII dokumu de
//   oyle yapiyor (`skop_yolla` ham sayi basiyor, olcek basliktan
//   geliyor). Davranis DEGISMIYOR, yalnizca kodlama degisiyor. B19'un
//   9. alani (volt ofseti) baslikta yerini koruyor.
#define SKOP_BIN_SURUM 1u

void skop_bin_sayfa() {
  if (!host_gecerli()) { sunucu.send(403, "text/plain", "Host reddedildi"); return; }
  /* B28: yakalama surerken dokum almak yari eski yari yeni dalga verir.
     Okuyucu BEKLER (200 ms) — yakalama kisa; olmazsa 503, arayuz tekrar
     dener. Bekleyen taraf HEP cekirdek 0: olcum asla beklemiyor. */
  if (skop_kilidi && xSemaphoreTake(skop_kilidi, pdMS_TO_TICKS(200)) != pdTRUE) {
    sunucu.send(503, "text/plain", "yakalama suruyor, tekrar dene");
    return;
  }

  uint8_t b[32];
  memset(b, 0, sizeof(b));
  b[0] = 'S'; b[1] = '3'; b[2] = 'B'; b[3] = (uint8_t)SKOP_BIN_SURUM;
  uint16_t adet = skop_adet;
  uint32_t hz = skop_hz;
  float adim = skop_volt_adim();
  float ofset = skop_volt_ofset();
  uint32_t tdiv = SKOP_TDIV_US[skop_son_tdiv];     /* B40b: yakalamanin ayari */
  uint16_t tidx = skop_tetik_idx;
  memcpy(b + 4,  &adet,  2);
  memcpy(b + 8,  &hz,    4);
  memcpy(b + 12, &adim,  4);
  memcpy(b + 16, &ofset, 4);
  memcpy(b + 20, &tdiv,  4);
  memcpy(b + 24, &tidx,  2);
  b[26] = (uint8_t)skop_son_kip;
  b[27] = skop_tetiklendi ? 1u : 0u;
  uint32_t sira = akis_sira;
  memcpy(b + 28, &sira, 4);

  sunucu.setContentLength((size_t)32 + (size_t)adet * 2u);
  sunucu.send(200, "application/octet-stream", "");
  sunucu.sendContent((const char *)b, 32);
  // Parcali: bitisik bir 8 KB tampon istemiyoruz (pil ucundaki ile
  // ayni gerekce). skop_veri zaten bellekte, dogrudan dilimleniyor.
  const uint16_t PARCA = 512u;          // ornek, yani 1024 bayt
  for (uint16_t i = 0; i < adet; i += PARCA) {
    uint16_t n2 = (uint16_t)((adet - i) < PARCA ? (adet - i) : PARCA);
    sunucu.sendContent((const char *)(skop_veri + i), (size_t)n2 * 2u);
  }
  skop_kilidi_birak();
}

// ═════════════════════════════════════════════════ B22.4 — SSE ═══════
//
// 🔴 ONCEKI HALI TEK ISTEMCILIKTI. Global tek bir `akis_istemci` vardi;
//    ikinci bir `GET /akis` onu SESSIZCE uzerine yaziyor, birincinin
//    soketi referans sayaci sifirlaninca kapaniyordu. Iki sekme acan
//    kullanici birinin neden durdugunu goremezdi.
//
// Simdi AKIS_AZAMI yuva var. Ayrica:
//   * `id:` alani = monotonik satir sirasi (yeniden baglanmada yer imi)
//   * `retry: 3000` — tarayici ne kadar sonra denesin
//   * 15 s'de bir `: kalp` yorum satiri (NAT / ara vekil zaman asimi)
//   * kopru kayitliysa ikinci istemci REDDEDILIYOR ve NEREYE gidecegi
//     soyleniyor — sessiz kapanma yok
#define AKIS_AZAMI 4
static WiFiClient akis[AKIS_AZAMI];
static uint32_t akis_dusen = 0;       // yuva bulunamayip ATILAN satir
static uint32_t akis_son_kalp = 0;

// Kopru kaydi (B22.6). RAM'de — NVS'e yazilmiyor: koprunun adresi
// gecici bir gercek, kalibrasyon gibi kalici bir ayar degil.
static char kopru_adres[40] = "";
static uint32_t kopru_son_ms = 0;
#define KOPRU_OMUR_MS 20000u

static bool kopru_canli() {
  return kopru_adres[0] && (millis() - kopru_son_ms) < KOPRU_OMUR_MS;
}

// Oturum jetonu — acilista uretiliyor. Ayni kokenden servis edilen sayfa
// bunu `event: kimlik` ile aliyor; capraz kokenli bir sayfa `/akis`'i
// OKUYAMADIGI icin (ACAO verilmiyor) jetonu ogrenemiyor.
static char oturum_jetonu[17] = "";


static void jeton_uret() {
  static const char ABC[] = "abcdefghjkmnpqrstuvwxyz23456789";
  for (uint8_t i = 0; i < 16; i++) oturum_jetonu[i] = ABC[esp_random() % (sizeof(ABC) - 1)];
  oturum_jetonu[16] = 0;
}

void akis_sayfa() {
  WiFiClient c = sunucu.client();
  c.println(F("HTTP/1.1 200 OK"));
  c.println(F("Content-Type: text/event-stream"));
  c.println(F("Cache-Control: no-cache"));
  c.println(F("Connection: keep-alive"));
  // ⚠ enableCORS(true) KULLANILMIYOR: o, Allow-Origin/Methods/Headers'in
  //   UCUNU DE `*` yapiyor (WebServer.cpp:663-667) ve boylece HERHANGI
  //   bir sayfa yaniti OKUYABILIR — oturum jetonu sizardi. Yalnizca
  //   kayitli kopru kokenine izin veriliyor.
  if (kopru_adres[0]) {
    c.print(F("Access-Control-Allow-Origin: "));
    c.println(kopru_adres);
  }
  c.println();

  if (kopru_canli()) {
    // Kart TEK surucuye hizmet ediyor. Reddediyoruz ama NEDEN ve NEREYE
    // gidilecegini soyluyoruz.
    c.print(F("event: kopru\ndata: "));
    c.print(kopru_adres);
    c.print(F("\n\n"));
    c.stop();
    return;
  }

  int8_t yuva = -1;
  for (int8_t i = 0; i < AKIS_AZAMI; i++) {
    if (!akis[i] || !akis[i].connected()) { yuva = i; break; }
  }
  if (yuva < 0) {
    c.print(F("event: dolu\ndata: "));
    c.print(AKIS_AZAMI);
    c.print(F("\n\n"));
    c.stop();
    return;
  }
  akis[yuva] = c;
  akis[yuva].print(F("retry: 3000\n\n"));
  akis[yuva].print(F("event: kimlik\ndata: {\"jeton\":\""));
  akis[yuva].print(oturum_jetonu);
  akis[yuva].print(F("\",\"surucu\":true}\n\n"));
}

// loop() her satir uretiminde cagirir (Serial aynasi uzerinden).
static void akis_yolla(const char *satir) {
  // ⚠ BURADA `Serial` KULLANILAMAZ: ayna bu fonksiyonu cagiriyor, yani
  //   sonsuz ozyineleme olurdu. Zincir bunu denetliyor.
  akis_sira++;
  /* B27 A2: olay TEK tamponda kuruluyor ve TEK write() ile gidiyor.
     Onceden istemci basina DORT ayri print() vardi — her biri lwIP'de
     ayri bir gonderim, hepsi olcum dongusunun icinde. Rapor araligi
     20 ms'ye inince (50 satir/s) bu fark dogrudan olcum kaybina donuyor.
     Tampon: "id: " + 10 hane + "\ndata: " + satir + "\n\n". */
  char olay[WEB_SATIR_AZAMI + 32];
  int n = snprintf(olay, sizeof(olay), "id: %lu\ndata: %s\n\n",
                   (unsigned long)akis_sira, satir);
  if (n < 0 || n >= (int)sizeof(olay)) n = (int)sizeof(olay) - 1;
  bool giden = false;
  for (int8_t i = 0; i < AKIS_AZAMI; i++) {
    if (!akis[i]) continue;
    if (!akis[i].connected()) { akis[i].stop(); continue; }
    akis[i].write((const uint8_t *)olay, (size_t)n);
    giden = true;
  }
  if (!giden) akis_dusen++;
}

/* 🔴 B28 — SOKETE YAZMA ARTIK YALNIZCA CEKIRDEK 0'DA.
   `web_satir_hazir` OLCUM cekirdeginde (1) cagriliyor: satirlari basan
   `Serial.println` orada. Soketlere oradan yazmak iki sorun dogururdu:
     * `akis[]` dizisini ag gorevi (yeni istemci kabulu, kalp atisi) ile
       AYNI ANDA elleyen ikinci bir yazar,
     * ve daha kotusu, TCP yazmasinin olcum dongusunu bloklamasi —
       yani bu asamanin cozmeye calistigi seyin ta kendisi.
   Satir bir kuyruga birakiliyor, ag gorevi bosaltiyor. Kuyruk dolarsa
   satir DUSER ve sayilir: olcumu yavaslatmaktansa telemetri satirini
   kaybetmek yeglenir (D satiri zaten bir sonrakinde tazeleniyor). */
typedef struct { char m[WEB_SATIR_AZAMI]; } AkisKalem;
static QueueHandle_t akis_kuyrugu_q = nullptr;
/* Ag gorevinin kolu ve tur sayaci BURADA tanimli: `?` ciktisi (bolum
   ayar_yaz_seri) bunlari okuyor ve o fonksiyon gorev tanimindan ONCE
   geliyor — .ino tek ceviri birimi oldugundan sira onemli. */
static TaskHandle_t ag_gorev_kolu = nullptr;
static volatile uint32_t ag_tur = 0;
static volatile uint32_t akis_tasma = 0;      // kuyruk dolu -> dusen satir

void web_satir_hazir(const char *satir) {
  if (!akis_kuyrugu_q) return;                // ag kurulmadan once (afis)
  AkisKalem ak;
  snprintf(ak.m, sizeof(ak.m), "%s", satir);
  /* `volatile` uzerinde `++` C++20'de kullanimdan kalkti (-Wvolatile).
     Acik oku-yaz ayni sey ama uyarisiz. Yaris yok: bu sayaci YALNIZCA
     olcum cekirdegi yaziyor, otekiler okuyor (tek yazar disiplini). */
  if (xQueueSend(akis_kuyrugu_q, &ak, 0) != pdTRUE) akis_tasma = akis_tasma + 1;
}

/* 🔴 DUSEN SATIR SESSIZ KALMAZ. Kuyruk yalnizca ag gorevi uzun bir
   istekte (ornegin 58 KB'lik vue.js) mesgulken doluyor; olculdu: skop
   ASCII dokumu (63 satirlik patlama) + es zamanli sayfa yuklemesinde
   32 satir dustu. Dinleyen taraf bunu BILMELI, yoksa eksik bir dokumu
   tam sanar. Yer acilir acilmaz tek bir isaret satiri gonderiliyor. */
static uint32_t akis_bildirilen_tasma = 0;

static void akis_kuyrugunu_bosalt() {
  AkisKalem ak;
  while (xQueueReceive(akis_kuyrugu_q, &ak, 0) == pdTRUE) akis_yolla(ak.m);
  uint32_t t = akis_tasma;
  if (t != akis_bildirilen_tasma) {
    char isaret[64];
    snprintf(isaret, sizeof(isaret), "! akis: %lu satir dustu (kuyruk doldu)",
             (unsigned long)(t - akis_bildirilen_tasma));
    akis_bildirilen_tasma = t;
    akis_yolla(isaret);
  }
}

// NAT ve ara vekiller sessiz baglantiyi dusuruyor. Yorum satiri istemciye
// gorunmuyor ama soketi canli tutuyor.
static void akis_kalp() {
  uint32_t ms = millis();
  if (ms - akis_son_kalp < 15000u) return;
  akis_son_kalp = ms;
  for (int8_t i = 0; i < AKIS_AZAMI; i++) {
    if (akis[i] && akis[i].connected()) akis[i].print(F(": kalp\n\n"));
  }
}

// ═════════════════════════════════════════════ B22.4 — KOMUT UCU ═════
void komut_calistir(const char *s);   // asagida tanimli (imza birebir)

// Komutlar DOGRUDAN calistirilmiyor, kuyruga giriyor ve `loop()`
// bosaltiyor. Uc sebep:
//   1. HTTP yaniti hizli donuyor (isleyici uzun bir komutu beklemiyor)
//   2. I2C / NVS / ADC yapilandirmasi TEK yerden yurutuluyor
//   3. Cift cekirdege gecilirse (B22.5 sonrasi karar) tek yazar
//      disiplini zaten kurulmus oluyor
#define KOMUT_KUYRUK 4
/* 🔴 B28 — CEKIRDEKLER ARASI KUYRUK. Eskiden `komut_adet++` / `--`
   ile elle halka tamponu vardi; TEK cekirdekte dogruydu. Artik uretici
   AG GOREVI (cekirdek 0, HTTP), tuketici OLCUM DONGUSU (cekirdek 1):
   iki cekirdekten okunup yazilan bir sayac YARIS demektir (kayip komut
   ya da ayni komutun iki kez calismasi). FreeRTOS kuyrugu bunu kendi
   kritik bolgesiyle cozuyor; `false` donusu (kuyruk dolu -> HTTP 503)
   ve 48 baytlik kalem sinirlari AYNI kaldi. */
typedef struct { char m[48]; } KomutKalem;
static QueueHandle_t komut_kuyrugu_q = nullptr;

static bool komut_kuyruga(const char *k) {
  if (!komut_kuyrugu_q) return false;
  KomutKalem kk;
  snprintf(kk.m, sizeof(kk.m), "%s", k);
  /* Bekleme YOK: dolu kuyrukta HTTP isteyicisini bloklamak, olcum
     dongusunu de yavaslatan bir geri basinc olurdu. */
  return xQueueSend(komut_kuyrugu_q, &kk, 0) == pdTRUE;
}

static void komut_kuyrugu_bosalt() {
  if (!komut_kuyrugu_q) return;
  KomutKalem kk;
  while (xQueueReceive(komut_kuyrugu_q, &kk, 0) == pdTRUE) {
    komut_calistir(kk.m);
  }
}

// 🔴 `p0` (pil desarjini DURDUR) HER ZAMAN serbest: jetonsuz, parolasiz.
//    Baslatmak yetki ister; durdurmayi hicbir sey geciktiremez. Bu bir
//    kolaylik degil EMNIYET karari — koprude de ayni kural var.
/* Serbest komutlar — jeton da parola da ISTEMEYEN ikisi:
     p0  durdur. Emniyet; hicbir sey geciktiremez.
     ?   ayar dokumu (B27 A2). Salt okunur, sir icermez (menzil, kazanc,
         sont, rapor araligi). Sayfa acilinca K5 esitlemesi icin
         gonderiliyor; izleyiciyi daha ilk saniyede parola sorusu
         karsilamasin. `N?` SERBEST DEGIL — o parolalari basar.
   Tam eslesme: `?x` ya da `p0!` gecmez. */
static bool komut_serbest(const char *k) {
  if (k[0] == 'p' && k[1] == '0' && k[2] == 0) return true;
  if (k[0] == '?' && k[1] == 0) return true;
  return false;
}

// Host beyaz listesi. DNS rebinding'i kiriyor: saldirganin alan adi kisa
// TTL ile 192.168.x.x'e donse bile `Host:` basligi bizim adlarimizdan
// biri OLMAZ. Bu olmadan jeton ve ozel baslik savunmalari da coker.
static bool host_gecerli() {
  String h = sunucu.hostHeader();
  int k = h.indexOf(':');
  if (k >= 0) h = h.substring(0, k);
  return h == String(ag_durum.ip)
      || h.equalsIgnoreCase(F(AG_MDNS ".local"))
      || h.equalsIgnoreCase(F(AG_MDNS));
}

// Parola KURULMAMISSA yetkilendirme kapali — ama acilista bu yuksek
// sesle soyleniyor. Sessiz "guvenlik yok" durumu birakmak, guvenlik
// olmamasindan daha kotudur.
static bool web_yetkili() {
  String s = ag_nvs.getString("web_sifre", "");
  if (!s.length()) return true;
  return sunucu.authenticate("olcum", s.c_str());
}

void komut_sayfa() {
  if (!host_gecerli()) {
    sunucu.send(403, "text/plain", "Host reddedildi (DNS rebinding korumasi)");
    return;
  }
  // Ozel baslik SART: capraz kokende preflight'a zorluyor ve
  // <img>/<form> ozel baslik EKLEYEMEZ.
  if (sunucu.header("X-Olcum") != "1") {
    sunucu.send(400, "text/plain", "X-Olcum basligi gerekli");
    return;
  }
  String k = sunucu.arg("plain");
  k.trim();
  if (!k.length()) { sunucu.send(400, "text/plain", "bos komut"); return; }

  if (!komut_serbest(k.c_str())) {
    if (sunucu.header("X-Jeton") != String(oturum_jetonu)) {
      sunucu.send(403, "text/plain",
                  "gecersiz oturum jetonu. `p0` (durdur) ve `?` serbest.");
      return;
    }
    if (!web_yetkili()) {
      sunucu.requestAuthentication();
      return;
    }
  }
  if (!komut_kuyruga(k.c_str())) {
    sunucu.send(503, "text/plain", "komut kuyrugu dolu");
    return;
  }
  // Govde BOS: kartin cevabi SSE'den geliyor. Koprude de boyle — ayni
  // istemci kodu ikisini de isliyor cunku bos govde satir uretmiyor.
  sunucu.send(204, "text/plain", "");
}

// Kopru kendini kaydediyor ve kalp atisiyla canli tutuyor. Kayitliyken
// ikinci bir /akis REDDEDILIYOR: kart TEK surucuye hizmet ediyor.
void kopru_sayfa() {
  if (!host_gecerli()) { sunucu.send(403, "text/plain", "Host reddedildi"); return; }
  if (sunucu.header("X-Olcum") != "1") {
    sunucu.send(400, "text/plain", "X-Olcum basligi gerekli");
    return;
  }
  String a = sunucu.arg("plain");
  a.trim();
  if (a.length() >= (int)sizeof(kopru_adres)) {
    sunucu.send(400, "text/plain", "adres cok uzun");
    return;
  }
  snprintf(kopru_adres, sizeof(kopru_adres), "%s", a.c_str());
  kopru_son_ms = millis();
  sunucu.send(204, "text/plain", "");
}

// OPTIONS: capraz koken izni YALNIZCA kayitli kopruye. Kayit yoksa
// hicbir kokene izin verilmiyor ve preflight basarisiz oluyor — yani
// tarayici istegi HIC gondermiyor.
void onuc_sayfa() {
  if (kopru_adres[0]) {
    sunucu.sendHeader(F("Access-Control-Allow-Origin"), kopru_adres);
    sunucu.sendHeader(F("Access-Control-Allow-Methods"), F("POST"));
    sunucu.sendHeader(F("Access-Control-Allow-Headers"), F("X-Olcum, X-Jeton, Content-Type"));
  }
  sunucu.send(204, "text/plain", "");
}

// ───────────────────────────────────────────────── kalibrasyon ve komutlar
//
// PROTOKOL — arayuz bunu ayristirir. Asama 2'de arayuz ile firmware
// komutlari AYRISMISTI (DEVIR 4.1: app.js `kv12.34` gonderiyor, firmware
// `v12.34` bekliyordu). Bu yuzden komut harfleri burada TEK KAYNAK ve
// `?` ciktisi hepsini listeliyor.
//
// CIKTI:
//   D <volt> <amper> <watt> <joule> <wh> <ms> <ornek> <menzil>
//   S2 ... (osiloskop, Asama 2 ile ayni)
//
// KOMUTLAR:
//   ?          ayarlari yaz
//   #          I2C taramasi
//   z          gerilim SIFIR kalibrasyonu (giris 0 V'a bagliyken)
//   g<volt>    gerilim KAZANC kalibrasyonu (giriste bilinen gerilim)
//   n / y      menzili elle NORMAL / YUKSEK yap (oto kapanir)
//   a<0|1>     otomatik menzil kapali / acik
//   Z          akim sifiri (yuk bagli DEGILken)
//   i<amper>   akim kazanc kalibrasyonu
//   s<ohm>     takili sont degeri
//   e          enerji sayacini sifirla
//   t...       osiloskop (Asama 2 ile ayni)

// 🔴 B20 (2026-09-10) — BU ISLEV ORTALAMA ALMIYORDU.
//
// Eski govde her turda yeni_donusum_bekle + ads_oku yapiyordu ama
// TEK ATIS kipinde hicbir donusum BASLATMIYORDU. Tek atista cip
// donusum bitince kapanir; yeni bir OS = 1 yazilmadikca yazmac
// DEGISMEZ. Yani 16-32 okuma AYNI bayat degeri okuyup "ortalamasini"
// aliyordu: gurultu azaltma TAM SIFIR. Ustune her tur zaman asimina
// dusup komut basina 48-96 ms olu zaman harciyordu.
//
// Dort kalibrasyon komutu da (z, g, Z, i) bunu kullaniyor — yani
// sifir ve kazanc kalibrasyonlari tek bir gurultulu ornekle
// yapiliyordu. Duzeltme: her turda donusumu KENDIMIZ baslatiyoruz.
static int16_t ortalama_oku(uint8_t adres, uint8_t kez) {
  int32_t t = 0;
  uint16_t mux = (adres == ADS_GERILIM) ? etkin_mux() : MUX_01;
  float   pga = (adres == ADS_GERILIM) ? etkin_kanal()->pga : ayar.i_pga;
  for (uint8_t i = 0; i < kez; i++) {
    ads_tek_atis_baslat(adres, mux, pga);
    // RDY yalnizca AKIM cipinde telli; GERILIM cipinde bekleyecek
    // pin yok, donusum suresi kadar bekliyoruz (1/860 s + pay).
    if (adres == ADS_AKIM) {
      if (!yeni_donusum_bekle(3000)) delayMicroseconds(1300);
    } else {
      delayMicroseconds(1300);
    }
    t += ads_oku(adres);
  }
  return (int16_t)(t / (int32_t)kez);
}

void ayar_yaz_seri() {
  Serial.print(F("A menzil="));   Serial.print(ayar.menzil ? F("YUKSEK") : F("NORMAL"));
  Serial.print(F(" oto="));       Serial.print(ayar.oto_menzil);
  Serial.print(F(" n_kazanc="));  Serial.print(ayar.normal.kazanc, 6);
  Serial.print(F(" n_sifir="));   Serial.print(ayar.normal.sifir_ham);
  Serial.print(F(" y_kazanc="));  Serial.print(ayar.yuksek.kazanc, 6);
  Serial.print(F(" y_sifir="));   Serial.print(ayar.yuksek.sifir_ham);
  Serial.print(F(" sont="));      Serial.print(ayar.sont_ohm, 6);
  Serial.print(F(" i_duz="));     Serial.print(ayar.i_duzeltme, 6);
  Serial.print(F(" i_ofset="));   Serial.print(ayar.i_ofset);
  Serial.print(F(" rapor="));     Serial.println(rapor_ms);   /* B27 A2 */

  Serial.print(F("R normal=+-")); Serial.print(tam_olcek_simetrik(&ayar.normal), 2);
  Serial.print(F(" V/"));         Serial.print(adim3(&ayar.normal) * 1e3f, 4);
  Serial.print(F(" mV  yuksek=+-"));
  Serial.print(tam_olcek_simetrik(&ayar.yuksek), 1);
  Serial.print(F(" V/"));         Serial.print(adim3(&ayar.yuksek) * 1e3f, 3);
  Serial.println(F(" mV"));
  // Menzil ASIMETRIK — kullanici bunu bilmeli (B4 bu hatayi yakaladi)
  Serial.print(F("L normal "));   Serial.print(tam_olcek_alt(&ayar.normal), 2);
  Serial.print(F(" .. "));        Serial.print(tam_olcek_ust(&ayar.normal), 2);
  Serial.print(F(" V  yuksek "));  Serial.print(tam_olcek_alt(&ayar.yuksek), 1);
  Serial.print(F(" .. "));        Serial.print(tam_olcek_ust(&ayar.yuksek), 1);
  Serial.println(F(" V"));
  // B22.1: blokaj sayaclari `?` ciktisinda da gorunsun — kullanici
  // `K` satirini kacirmis olabilir. Ayni bicim, tek temsil.
  Serial.print(F("K "));   Serial.print(enerji_kayip_ms);
  Serial.print(' ');       Serial.print(loop_azami_us);
  Serial.print(' ');       Serial.println(loop_uzun_adet);
  Serial.println(F("  (K = atlanan enerji ms · en uzun dongu us · >20ms tur)"));
  /* B28: cift cekirdek telemetrisi. Yigin dip degeri OLCULEN sayi —
     8 KB tahmin degil, kalan pay gorunur. `dusen` sifirdan buyukse
     akis kuyrugu tasmis demektir (satir kaybi). */
  Serial.print(F("C olcum_cekirdek="));  Serial.print(xPortGetCoreID());
  Serial.print(F(" ag_gorev="));
  Serial.print(ag_gorev_kolu ? F("var") : F("yok"));
  Serial.print(F(" ag_tur="));           Serial.print(ag_tur);
  Serial.print(F(" ag_yigin_dip="));
  Serial.print(ag_gorev_kolu ? (unsigned)uxTaskGetStackHighWaterMark(ag_gorev_kolu) : 0u);
  Serial.print(F(" ads_duraklama_ms="));  Serial.print(ads_duraklama_top_ms);
  Serial.print(F(" skop_yigin_dip="));
  Serial.print(skop_gorev_kolu ? (unsigned)uxTaskGetStackHighWaterMark(skop_gorev_kolu) : 0u);
  Serial.print(F(" adc_cali="));         Serial.print(skop_cali_var ? F("egri")
                                                                     : F("YOK"));
  Serial.print(F(" cal_hz="));           Serial.print(cal_hz);
  Serial.print(F(" akis_dusen="));       Serial.print(akis_tasma);
  /* B28: kuyruklar ve gorev yigini CALISMA ANINDA ayriliyor (~19 KB);
     zincirin B6 adimi yalnizca BAG ANI DRAM'ini olcuyor. Gercek pay
     burada gorunur. */
  Serial.print(F(" bos_dram="));
  Serial.println((unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
  /* B29: cevrim suresinin dagilimi — hangi faz yiyor. */
  if (faz_adet) {
    /* ⚠ Onek `F`: `T ` ZATEN osiloskop ayar satirinin onegi
       (`T tdiv=... hz=...`) ve tezgah kosucusu onu TELEMETRI sayip
       suzuyor. Ayni onegi ikinci bir anlamla kullanmak, bu projenin
       defalarca cezalandirdigi sey. */
    Serial.print(F("F yaz_us="));  Serial.print(faz_yaz_top / faz_adet);
    Serial.print(F(" bek_us="));   Serial.print(faz_bek_top / faz_adet);
    Serial.print(F(" oku_us="));   Serial.print(faz_oku_top / faz_adet);
    Serial.print(F(" toplam_us="));
    Serial.print((faz_yaz_top + faz_bek_top + faz_oku_top) / faz_adet);
    Serial.print(F(" kayma_us=")); Serial.print(faz_kayma_top / faz_adet);
    Serial.print(F(" kayma_ornek="));
    Serial.print((float)faz_kayma_top / faz_adet
                 / ((float)(faz_yaz_top + faz_bek_top + faz_oku_top) / faz_adet), 4);
    Serial.print(F(" rdy_asim="));  Serial.print(rdy_zaman_asimi);
    Serial.print(F(" cevrim="));   Serial.println(faz_adet);
  }
}

// Bir ADS1115 cevap vermiyorsa sebep genelde uctan bire indirgenir:
// ADDR bosta, SDA/SCL ters, ya da pull-up yok.
/* 🔴 B30 — ALERT/RDY TELI GERCEKTEN BAGLI MI: PINI OLCUYORUZ.
   `#` donanim akil saglig i komutu; I2C adreslerini gosteriyordu ama
   ALERT telini HIC sinamiyordu. Oysa o tel dususe kart sessizce 3 kat
   yavasliyor (B20'nin 91 SPS kusuru ayni aileden).
   Yontem: 0x48'e tek atis baslat, pini 3 ms boyunca yokla.
     * baslangicta LOW kalirsa  -> pin GND'ye kisali ya da hep asserted
     * hic LOW'a inmezse        -> tel TAKILI DEGIL ya da +3V3'e bagli
     * inerse                   -> gecen sure gercek donusum suresidir */
/* Tek cip icin: RDY'yi ZORLA ac, donusum baslat, pini yokla. */
static bool alert_dener(uint8_t adres, float pga, uint32_t *sure_us) {
  ads_yaz(adres, ADS_UST, 0x8000);       /* RDY kipi icin esikler */
  ads_yaz(adres, ADS_ALT, 0x0000);
  ads_yaz(adres, ADS_AYAR, ADS_BASLAT | MUX_01 | pga_bitleri(pga)
                           | ADS_TEK | ADS_860SPS | ADS_KOMP_TEK);
  uint32_t t0 = micros();
  while (micros() - t0 < 3000u) {
    if (digitalRead(PIN_HAZIR) == LOW) { *sure_us = micros() - t0; return true; }
  }
  (void)ads_oku(adres);
  return false;
}

static void alert_probu() {
  int bas = digitalRead(PIN_HAZIR);
  uint32_t sure = 0;
  bool bir = alert_dener(ADS_AKIM, ayar.i_pga, &sure);
  (void)ads_oku(ADS_AKIM);

  /* 🔴 TEL HANGI MODULDE: iki modul BIRBIRINE BENZIYOR ve `ADDR` ile
     `ALRT` YAN YANA pinler. Tel #2'ye takildiysa GPIO7, COMP_QUE=11b ile
     yuksek-Z birakilmis bir cikisi goruyor: hep YUKSEK, yani "tel yok"
     ile AYNI belirti. Ayirt etmek icin #2'nin RDY'sini GECICI acip
     yokluyoruz — kullaniciya "ara bul" dedirtmek yerine SOYLUYORUZ. */
  bool iki = false;
  uint32_t sure2 = 0;
  if (!bir) {
    iki = alert_dener(ADS_GERILIM, etkin_kanal()->pga, &sure2);
    (void)ads_oku(ADS_GERILIM);
    /* #2'yi ESKI HALINE dondur: ALERT ucu bilerek yuksek-Z. */
    ads_yaz(ADS_GERILIM, ADS_AYAR, ADS_BASLAT | etkin_mux()
                                   | pga_bitleri(etkin_kanal()->pga)
                                   | ADS_TEK | ADS_860SPS | ADS_KOMP_KAPALI);
  }

  Serial.print(F("! alert: pin=GPIO"));  Serial.print(PIN_HAZIR);
  Serial.print(F(" baslangic="));        Serial.print(bas ? F("YUKSEK") : F("DUSUK"));
  if (bir) {
    Serial.print(F(" 0x48=VAR sure="));  Serial.print(sure);
    Serial.println(F(" us  (RDY calisiyor — dogru modul)"));
  } else if (iki) {
    Serial.print(F(" 0x48=YOK  0x49=VAR sure=")); Serial.print(sure2);
    Serial.println(F(" us  -> ALERT teli YANLIS MODULDE:"
                     " #2'den (0x49) cikarip #1'e (0x48) tak"));
  } else {
    Serial.println(F(" 0x48=YOK  0x49=YOK"
                     "  -> ALERT teli hicbir modulde degil:"
                     " #1'in (0x48) ALRT pini ile GPIO7 arasina tak"));
  }
}

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

void yardim() {
  Serial.println(F("Komutlar:"));
  Serial.println(F("  ?  ayarlar   #  I2C tara   e  enerji sifirla"));
  Serial.println(F("  z  gerilim sifiri (giris 0 V)   g<volt> gerilim kazanci"));
  Serial.println(F("  n / y  menzil NORMAL / YUKSEK   a<0|1> otomatik menzil"));
  Serial.println(F("  Z  akim sifiri (yuk YOK)        i<amper> akim kazanci"));
  Serial.println(F("  s<ohm> sont degeri   w  hizli yol gucu (P/PF)"));
  Serial.println(F("  f<Hz> sebeke frekansi (0=DC, olcek duzeltmesi)"));
  Serial.println(F("  F<us> faz kalibrasyonu us (direncli yukle), F goster"));
  Serial.println(F("  P<volt> pil kesme   p1/p0 pil testi baslat/durdur   p durum"));
  Serial.println(F("  K blokaj sayaclarini sifirla (eski degeri basar)"));
  Serial.println(F("  r<ms> rapor araligi 20..5000 ms (D satiri sikligi), r goster"));
  Serial.println(F("  X<hz> kalibrasyon cikisi (GPIO10, %50 kare), X0 kapatir"));
  Serial.println(F("  x<promil> CAL gorev orani 0..1000 (PWM+RC = DC kaynagi)"));
  Serial.println(F("  c<ham> ham ADC kodunun fabrika kalibrasyonlu mV karsiligi"));
  Serial.println(F("  CT kalibrasyon tablosu (17 nokta) — arayuz skop eksenini duzeltir"));
  Serial.println(F("  wR hizli kanallarin HAM kodu (GPIO4 + GPIO5 dogrusallik supurmesi)"));
  Serial.println(F("  wB hizli kanallar BOSTA mi (dahili cekme sinamasi)"));
  Serial.println(F("  R! fabrika ayarlari (kalibrasyonu SIFIRLAR)"));
  Serial.println(F("  t yakala  ta otomatik  tb<0-11> zaman tabani  t+ t-"));
  Serial.println(F("  tl<0-4095> esik  te<0/1> kenar  th<hist>  tp<%>  tm<kip>  t?"));
}

void komut_calistir(const char *s) {
  switch (s[0]) {
    case '?': ayar_yaz_seri(); break;
    case 'h': case 'Y': yardim(); break;
    case '#': i2c_tara(); alert_probu(); break;

    case 'e':
      enerji_pJ = 0;
      Serial.println(F("* enerji sifirlandi"));
      break;

    /* B30 — kalibrasyon cikisi: `X<hz>` kare dalga, `X0` kapatir.
       ⚠ BASILAN FREKANS, ISTENEN DEGIL GERCEKLESEN olmali: LEDC 80 MHz
         APB'yi tam sayi bolerek uretiyor, yani 7 kHz isteyip 6993 Hz
         alabilirsin. Skopun olcumunu ISTENEN degerle karsilastirmak
         kendini kandirmak olurdu. */
    case 'X': {
      long istek = (s[1]) ? atol(s + 1) : 0;
      if (istek < 0) istek = 0;
      if (istek > 200000L) istek = 200000L;
      if (istek == 0) {
        if (cal_cozunurluk) { ledcDetach(PIN_CAL); pinMode(PIN_CAL, INPUT); }
        cal_hz = 0; cal_cozunurluk = 0;
        Serial.println(F("X cal=kapali"));
        break;
      }
      if (cal_cozunurluk) { ledcDetach(PIN_CAL); cal_cozunurluk = 0; }
      uint8_t coz = 0;
      for (uint8_t b = 12; b >= 6; b--) {
        if (ledcAttach(PIN_CAL, (uint32_t)istek, b)) { coz = b; break; }
      }
      if (!coz) {
        Serial.print(F("! X: "));  Serial.print(istek);
        Serial.println(F(" Hz LEDC ile uretilemiyor (hicbir cozunurlukte)"));
        cal_hz = 0;
        break;
      }
      cal_cozunurluk = coz;
      uint32_t gercek = ledcChangeFrequency(PIN_CAL, (uint32_t)istek, coz);
      if (!gercek) gercek = (uint32_t)istek;
      ledcWrite(PIN_CAL, (uint32_t)1 << (coz - 1));   /* %50 */
      cal_hz = gercek;
      Serial.print(F("X cal_hz="));      Serial.print(cal_hz);
      Serial.print(F(" istenen="));      Serial.print(istek);
      Serial.print(F(" cozunurluk="));   Serial.print(coz);
      Serial.print(F(" bit gorev=%50 pin=GPIO")); Serial.print(PIN_CAL);
      Serial.println(F("  (skop girisi GPIO4'e tek tel)"));
      break;
    }

    /* B34 — ham ADC kodunun FABRIKA KALIBRASYONUNA gore mV karsiligi.
       `c<ham>` -> `c ham=2048 mv=1571 kaynak=egri`. Olculmus bir supurmeyi
       KAYNAGI DEGISTIRMEDEN kalibrasyondan gecirmeye yariyor: egri ADC'nin
       mi yoksa PWM+RC kaynaginin mi, ayrimi boyle yapiliyor. */
    /* 🔴 B36 — KALIBRASYON TABLOSU (`cT`).
       Skopun gerilim ekseni bugun ham kodu SABIT bir carpanla ceviriyor;
       B34 o varsayimin ±76 kod (girisde ±2.2 V) hata verdigini OLCTU.
       Egri tek bir carpanla ifade edilemez, o yuzden arayuze BILGI olarak
       gonderiliyor ve duzeltme CIZIM ANINDA yapiliyor.

       ⚠ TABLO KARTTAN GELIYOR, KODA GOMULU DEGIL. Her yonganin eFuse
         egrisi KENDISINE ait; benim tek bir kartta olctugum egriyi koda
         gommek baska bir karta YANLIS duzeltme uygulamak olurdu.
         B34'un 101 noktali olcumu bu tablonun KAYNAGI degil, DENETIMI.

       ⚠ Kayitlar HAM kod tutuyor (B35), yani bu duzeltme eski
         yakalamalara da uygulanabiliyor — kalibrasyon degisirse kayitlar
         yeniden yorumlanir, yeniden olcmek gerekmez.

       Cikti tek satir:
         `CT <n> oran=<f> ofset=<f> tavan_mv=<f> <kod0>:<mv0> ...`

       ⚠ `oran` ve `ofset` BILEREK BURADA. Arayuz duzeltilmis gerilimi
         `V = (mv/1000)*oran - ofset` ile buluyor. Bunlari gondermeyip
         arayuzun `voltAdim`/`voltOfset`ten turetmesini isteseydik,
         turetme VREF'in nominal degerine gomulu bir varsayima dayanirdi
         ve VREF bir gun kalibre edilince SESSIZCE kayardi.

       `tavan_mv` kartin KENDI dogrusal varsayimi (SKOP_ADC_TAVAN).
       Tablonun son noktasiyla karsilastirilinca kazanc hatasi gorunur
       olur — B34 bunu olctu: varsayilan 3100, olculen 3160 (%1.9).

       Kalibrasyon yoksa `CT 0 kaynak=YOK` — SESSIZ kalmiyor, cunku
       duzeltmesiz cizim "kalibre" sanilirdi. */
    case 'C': {
      if (s[1] != 'T') { Serial.println(F("! bilinmeyen komut — `h` yardim")); break; }
      if (!kal_tab_var) {
        Serial.println(F("CT 0 kaynak=YOK"));
        break;
      }
      const uint8_t N = (uint8_t)KAL_N;  // 0, 256, ..., 4096-1
      Serial.print(F("CT ")); Serial.print(N);
      Serial.print(F(" oran="));    Serial.print(SKOP_ORAN, 6);
      Serial.print(F(" ofset="));   Serial.print(SKOP_VOLT_OFSET, 6);
      Serial.print(F(" tavan_mv="));Serial.print(SKOP_ADC_TAVAN * 1000.0f, 1);
      /* B39: hizli yolun kullandigi DIZININ KENDISI basiliyor — eFuse
         burada yeniden sorgulanmiyor; sorgulansaydi arayuzun gordugu
         tablo ile kartin olcekledigi tablo iki ayri temsil olurdu. */
      for (uint8_t k = 0; k < N; k++) {
        Serial.print(' '); Serial.print(kal_dugum_kod(k));
        Serial.print(':');  Serial.print(kal_mv_tab[k]);
      }
      Serial.println();
      break;
    }

    case 'c': {
      long ham = atol(s + 1);
      if (ham < 0) ham = 0;
      if (ham > 4095) ham = 4095;
      int mv = -1;
      if (skop_cali_var) adc_cali_raw_to_voltage(skop_cali, (int)ham, &mv);
      Serial.print(F("c ham="));   Serial.print(ham);
      Serial.print(F(" mv="));     Serial.print(mv);
      Serial.print(F(" kaynak=")); Serial.println(skop_cali_var ? F("egri")
                                                                : F("YOK"));
      break;
    }

    /* 🔴 B33 — CAL GOREV ORANI (binde). `X<hz>` kare dalgayi kurar,
       `x<promil>` gorev oranini degistirir: 0..1000 = %0..%100.
       NEDEN: PWM + RC = programlanabilir DC kaynagi. ESP32'nin ADC'si
       dogrusal DEGIL (Espressif'in kendi belgeleri soyluyor) ve skopun
       gerilim ekseni bugun TAM DOGRUSAL varsayiyor. Gorev oranini
       supurup okunan kodu olcmek, o egriyi cikarmanin lehimsiz yolu.
       Referans: gorev orani TAM BILINIYOR (10 bit LEDC, tamsayi), yani
       olcum kendi varsayimina degil BAGIMSIZ bir sayiya dayaniyor. */
    case 'x': {
      if (!cal_hz) { Serial.println(F("! x: once `X<hz>` ile cikisi ac")); break; }
      long p = atol(s + 1);
      if (p < 0) p = 0;
      if (p > 1000) p = 1000;
      /* Gorev orani GERCEK cozunurluge gore olcekleniyor: 1023 sabiti
         8 bitlik bir kanalda %400 gorev demek olurdu. */
      uint32_t azami = ((uint32_t)1 << cal_cozunurluk) - 1u;
      uint32_t d = (uint32_t)(((uint64_t)p * azami + 500u) / 1000u);
      ledcWrite(PIN_CAL, d);
      Serial.print(F("x gorev_promil="));  Serial.print(p);
      Serial.print(F(" ham_duty="));       Serial.print(d);
      Serial.print('/');                   Serial.print(azami);
      Serial.print(F(" ("));                Serial.print(cal_cozunurluk);
      Serial.print(F(" bit) cal_hz="));     Serial.println(cal_hz);
      break;
    }

    /* B27 A2 — rapor araligi. Sinir DISI deger reddedilmiyor, KIRPILIYOR
       ve kirpilmis deger basiliyor: kullanici `r5` yazip 20 ms aldigini
       gormeli, sessiz bir "olmadi" degil. Bos `r` yalnizca gosterir. */
    case 'r': {
      if (s[1]) {
        long v = atol(s + 1);
        if (v < RAPOR_MS_EN_AZ)  v = RAPOR_MS_EN_AZ;
        if (v > RAPOR_MS_EN_COK) v = RAPOR_MS_EN_COK;
        rapor_ms = (uint32_t)v;
      }
      Serial.print(F("* rapor araligi "));
      Serial.print(rapor_ms);
      Serial.println(F(" ms"));
      break;
    }

    /* 🔴 B26 — BLOKAJ SAYAÇLARINI SIFIRLA.

       NEDEN VAR: `loop_azami_us` acilistan beri sifirlanmayan KOSAN
       MAKSIMUM ve isinma payi yok (olcum ikinci loop() turunda basliyor).
       Yani setup() sonrasi WiFi/mDNS ayaga kalkarken olusan TEK SEFERLIK
       bir sicrama degeri KALICI olarak cakiliyordu.

       Bu onemli, cunku DEVIR 5.12.34 cift cekirdek kararini TAM OLARAK
       bu sayiya bagliyor (esik 20 000 us). Gercek kartta olculen:
       taze acilista 18 203 us (esigin ALTINDA, 0 uzun tur), birkac
       dakika sonra seyrek bir ~30 ms olayla 30 397 us (esigin USTUNDE).
       Yani ayni kart, NE ZAMAN BAKTIGINA gore iki farkli cevap veriyordu
       ve aylardir acik duran mimari karar buna dayandirilacakti.

       Sifirlayip BELIRLI bir sure olcmek, kararı tekrarlanabilir kiliyor.
       Eski degerler SILINMEDEN ONCE BASILIYOR — bu projede bir sayinin
       sessizce kaybolmasi kabul edilmiyor. */
    case 'K':
      Serial.print(F("* blokaj sayaclari sifirlandi — onceki: atlanan "));
      Serial.print(enerji_kayip_ms);
      Serial.print(F(" ms, en uzun dongu "));
      Serial.print(loop_azami_us);
      Serial.print(F(" us, >20ms tur "));
      Serial.println(loop_uzun_adet);
      loop_azami_us = 0;
      loop_uzun_adet = 0;
      enerji_kayip_ms = 0;
      k_degisti = 1;
      break;

    // --- gerilim SIFIR kalibrasyonu
    case 'z': {
      int16_t ham = ortalama_oku(ADS_GERILIM, 16);
      kalibre_sifir(ham, etkin_kanal());
      ayar_kaydet();
      Serial.print(F("* gerilim sifiri ("));
      Serial.print(ayar.menzil ? F("YUKSEK") : F("NORMAL"));
      Serial.print(F(") ham="));
      Serial.println(ham);
      break;
    }

    // --- gerilim KAZANC kalibrasyonu
    case 'g': {
      /* 🔴 B22.1 — K3. Eskiden `atof(s + 1)` idi ve `atof("")` = 0.0
         donuyordu. Ciplak `g` gonderilince kalibre_kazanc(ham, 0.0f, k)
         cagriliyor, `kazanc *= 0/s` ile kazanc SIFIRLANIYOR ve
         ayar_kaydet() bunu NVS'e yaziyordu. Ret denetimi de tetiklenmiyor
         (sonra=0, once=5 -> esit degil). Kurtarma IMKANSIZDI. Web komut
         ucu acilinca bu UZAKTAN tetiklenebilir hale gelecekti. */
      char *son;
      float gercek = strtof(s + 1, &son);
      if (son == s + 1) {
        Serial.println(F("! g: gerilim degeri gerekli, orn. `g12.34`"));
        break;
      }
      if (!(fabsf(gercek) > 1e-6f)) {   // !( > ) NaN'i da reddeder
        Serial.println(F("! g: sifir gecerli bir kalibrasyon degeri degil"));
        break;
      }
      int16_t ham = ortalama_oku(ADS_GERILIM, 16);
      float once = olc_gerilim3(ham, etkin_kanal());
      kalibre_kazanc(ham, gercek, etkin_kanal());
      float sonra = olc_gerilim3(ham, etkin_kanal());
      if (sonra == once && gercek != once) {
        // kalibre_kazanc esigi asilmadigi icin REDDETTI
        Serial.println(F("! kazanc kalibrasyonu reddedildi — giris tam "
                         "olcegin %5'inden kucuk"));
      } else {
        ayar_kaydet();
        Serial.print(F("* gerilim kazanci "));
        Serial.print(etkin_kanal()->kazanc, 6);
        Serial.print(F("  ")); Serial.print(once, 4);
        Serial.print(F(" -> ")); Serial.println(sonra, 4);
      }
      break;
    }

    case 'n': case 'y':
      ayar.menzil = (s[0] == 'y') ? 1 : 0;
      ayar.oto_menzil = 0;
      menzil_uygula();
      ayar_kaydet();
      Serial.print(F("* menzil "));
      Serial.print(ayar.menzil ? F("YUKSEK") : F("NORMAL"));
      Serial.println(F(" (otomatik kapatildi)"));
      break;

    case 'a':
      ayar.oto_menzil = (s[1] == '1');
      ayar_kaydet();
      Serial.print(F("* otomatik menzil "));
      Serial.println(ayar.oto_menzil ? F("acik") : F("kapali"));
      break;

    // --- akim sifiri
    case 'Z': {
      ayar.i_ofset = ortalama_oku(ADS_AKIM, 32);
      ayar_kaydet();
      Serial.print(F("* akim sifiri ham="));
      Serial.println(ayar.i_ofset);
      break;
    }

    case 'i': {
      /* 🔴 B22.1 — K3, `g` ile ayni kusur: ciplak `i` -> atof("") = 0 ->
         `i_duzeltme *= 0/olculen` -> 0 -> NVS. Sonra olc_akim3 hep 0
         dondugu icin |olculen| > esik bir daha saglanmaz. */
      char *son;
      float gercek = strtof(s + 1, &son);
      if (son == s + 1) {
        Serial.println(F("! i: akim degeri gerekli, orn. `i1.5`"));
        break;
      }
      if (!(fabsf(gercek) > 1e-9f)) {
        Serial.println(F("! i: sifir gecerli bir kalibrasyon degeri degil"));
        break;
      }
      int16_t ham = ortalama_oku(ADS_AKIM, 16);
      float olculen = olc_akim3(ham, ayar.i_ofset, ayar.i_pga,
                                ayar.sont_ohm, ayar.i_duzeltme);
      float esik = 0.05f * ayar.i_pga / ayar.sont_ohm;
      if (olculen > esik || olculen < -esik) {
        // B22.1: kazanc kelepcesi (olcum3.h'deki ile ayni gerekce).
        float yeni_duz = ayar.i_duzeltme * (gercek / olculen);
        if (!(yeni_duz > 0.2f) || !(yeni_duz < 5.0f)) {
          Serial.println(F("! i: sonuc duzeltme 0.2-5 kat disinda, REDDEDILDI"));
          break;
        }
        ayar.i_duzeltme = yeni_duz;
        ayar_kaydet();
        Serial.print(F("* akim duzeltmesi "));
        Serial.println(ayar.i_duzeltme, 6);
      } else {
        Serial.println(F("! akim kalibrasyonu reddedildi — akim cok kucuk"));
      }
      break;
    }

    case 's': {
      float r = atof(s + 1);
      if (r > 1e-4f) {
        ayar.sont_ohm = r;
        ayar_kaydet();
        Serial.print(F("* sont "));
        Serial.print(ayar.sont_ohm, 6);
        Serial.print(F(" ohm, menzil +-"));
        Serial.print(ayar.i_pga / ayar.sont_ohm, 4);
        Serial.println(F(" A"));
      } else {
        Serial.println(F("! sont degeri gecersiz"));
      }
      break;
    }

    /* ── B17: SEBEKE FREKANSI (olcek duzeltmesi icin) ─────────────────
     * ADS yolu 860 SPS ve 55 Hz suzgecle frekans OLCEMEZ. Duzeltme
     * icin frekans AYARLANIYOR. 0 = DC (duzeltme yok). */
    case 'f': {
      /* 🔴 B22.1: ciplak `f` eskiden atof("") = 0 ile SESSIZCE DC kipine
         geciriyor ve NVS'e yaziyordu. Bir yazim hatasi olcek duzeltmesini
         kapatiyordu ve kullanici bunu ancak gucu %82 yanlis okuyunca
         anlardi. Artik `F` ve `P` gibi DEGERI GOSTERIYOR. */
      if (s[1] == 0) {
        Serial.print(F("* sebeke frekansi "));
        if (ayar.sebeke_hz <= 0.0f) Serial.println(F("DC (olcek duzeltmesi KAPALI)"));
        else { Serial.print(ayar.sebeke_hz, 2); Serial.println(F(" Hz")); }
        break;
      }
      char *fson;
      float f = strtof(s + 1, &fson);
      if (fson == s + 1) {
        Serial.println(F("! f: frekans gerekli, orn. `f50` ya da `f0` (DC)"));
        break;
      }
      // 🔴 B20: ust sinir 400 -> 100 Hz. Sinir OLCUMLE secildi
      // (uretim/sim3_bant.py bolum 2-3); bagliyici kisit BEKLENEN
      // yer degil:
      //
      //   * Lagrange hizalayicinin genlik sarkmasi 100 Hz'te yalnizca
      //     %0.78 (671 SPS'te) — burasi sorun DEGIL.
      //   * ASIL KISIT FAZ KALIBRASYONU. `F` komutu SABIT bir ZAMAN
      //     gecikmesi sakliyor; duzelttigi sey ise iki RC'nin arctan
      //     farki. Ikisi yalnizca kalibrasyon frekansinda ortusur.
      //     50 Hz'te kalibre edilmis kartta KALAN faz hatasi
      //     (kondansator toleransi ±%10, en kotu hal):
      //         60 Hz  -> -1.21°   PF=0.5'te guc hatasi   %3.7
      //        100 Hz  -> -7.04°                          %20.5
      //        200 Hz  -> -21.39°                         %56.3
      //        400 Hz  -> (eski sinir) tamamen gecersiz
      //     Yani kart 50/60 Hz BANDINDA kalibre ve gecerli; ustunde
      //     kalibrasyon ise YARAMIYOR, hatta zarar veriyor.
      //   * Olcek carpani da 100 Hz'te 4.5x, 400 Hz'te 56x olup
      //     tau hatasina asiri duyarli hale geliyordu.
      //
      // ⚠ Sinir NEDEN olculen ornek_periyot_us'a BAGLANMADI: o deger
      //   bir EMA; ayni `f50` komutu dongu yukune gore bazen kabul
      //   bazen ret edilirdi. Sabit ve ONGORULEBILIR sinir daha iyi.
      //   Gercek hiz dusukse uyariyi `D` satirindaki ornek sayisi verir.
      if (!(f >= 0.0f) || f > 100.0f) {     // !(>=) NaN'i da yakalar
        Serial.println(F("! f: 0 (DC) ile 100 Hz arasi olmali. ADS yolu bir"
                         " SEBEKE wattmetresidir; faz kalibrasyonu yalnizca"
                         " kalibrasyon frekansinin yakininda gecerli."));
        break;
      }
      if (f > 0.0f && (f < 40.0f || f > 70.0f)) {
        Serial.println(F("* uyari: 40-70 Hz disinda faz kalibrasyonu (F)"
                         " gecerliligini yitirir — bkz. DEVIR 5.12.30"));
      }
      ayar.sebeke_hz = f;
      ayar_kaydet();
      Serial.print(F("* sebeke frekansi "));
      if (f <= 0.0f) {
        Serial.println(F("DC — olcek duzeltmesi KAPALI"));
      } else {
        Serial.print(f, 2); Serial.print(F(" Hz  ->  guc carpani "));
        Serial.println((double)(suzgec_ters_kazanc(f, etkin_kanal()->tau)
                                * suzgec_ters_kazanc(f, TAU_AKIM)), 4);
      }
      break;
    }

    /* ── B17: FAZ KALIBRASYONU ────────────────────────────────────────
     * `F<sayi>`  : etkin menzilin faz duzeltmesini MIKROSANIYE yaz
     * `F`        : mevcut degerleri goster
     * ⚠ NASIL OLCULUR: DIRENCLI bir yuk bagla (rezistans, ampul).
     *   Dirençli yukte gercek faz farki SIFIR olmali. Okunan PF 1'den
     *   kucukse aradaki fark suzgec eslesmezligidir; F ile kucuk
     *   adimlarla duzelt (PF en buyuk olacak sekilde). Referans cihaz
     *   GEREKMIYOR. */
    case 'F': {
      if (s[1] == 0) {
        Serial.print(F("* faz kalibrasyonu (us): NORMAL "));
        Serial.print(ayar.faz_kal_us[0], 2);
        Serial.print(F("  YUKSEK "));
        Serial.println(ayar.faz_kal_us[1], 2);
        break;
      }
      float d = atof(s + 1);
      // B20: !(>=) ve !(<=) NaN'i da reddediyor. Eskiden `Fnan`
      // faz_kal'i NaN yapip NVS'e yaziyordu; NaN bir kez girince
      // hizalayici NaN uretiyor, o.watt NaN oluyor ve enerji sayaci
      // (int64_t)(NaN * 1e6f) ile tanimsiz degere gidiyordu.
      // B22.1: sinir artik MIKROSANIYE. +-2000 us, nominal periyotta
      // (1502.8 us) yaklasik +-1.3 ornek — Lagrange'in d kelepcesi
      // (-1..+2) zaten ustune biniyor. Fiziksel eslesmezlik en kotu
      // halde ~293 us oldugu icin bu sinir fazlasiyla genis.
      if (!(d >= -2000.0f) || !(d <= 2000.0f)) {
        Serial.println(F("! F: -2000 ile +2000 us arasi olmali"));
        break;
      }
      ayar.faz_kal_us[ayar.menzil ? 1 : 0] = d;
      ayar_kaydet();
      Serial.print(F("* "));
      Serial.print(ayar.menzil ? F("YUKSEK") : F("NORMAL"));
      Serial.print(F(" faz kalibrasyonu "));
      Serial.print(d, 2);
      Serial.print(F(" us  ("));
      // Derece artik ornek_periyot_us'a BAGLI DEGIL — duzeltmenin
      // kendisi gibi. Eskiden buraya periyot carpani giriyordu.
      Serial.print((double)(360.0f * (ayar.sebeke_hz > 0 ? ayar.sebeke_hz
                                                         : 50.0f)
                            * d * 1e-6f), 3);
      Serial.println(F(" derece)"));
      break;
    }

    /* ── B21: PIL KAPASITE TESTI ──────────────────────────────────────
     * P<volt> : kesme gerilimini ayarla (NVS'e yazilir)
     * P       : ayari goster
     * p1 / p0 : testi baslat / durdur
     * p       : durum + sonuc raporu
     * ⚠ Yuk J7'ye baglanir. J3'e baglanirsa MOSFET BAYPAS olur ve kesme
     *   CALISMAZ — p1 bunu denetleyip testi REDDEDER. */
    case 'P': {
      if (s[1] == 0) {
        Serial.print(F("* pil kesme gerilimi "));
        Serial.print(ayar.pil_kesme_v, 3);
        Serial.print(F(" V · kayit "));
        Serial.print(ayar.pil_kayit_hz, 2);
        Serial.print(F(" Hz · azami sure "));
        Serial.print(ayar.pil_azami_s / 3600UL);
        Serial.println(F(" saat"));
        break;
      }
      float v = atof(s + 1);
      /* !(>=) NaN'i da reddeder — B20'de f/F komutlarinda ayni koruma. */
      if (!(v >= 0.5f) || !(v <= PIL_AZAMI_V)) {
        Serial.print(F("! P: 0.5 ile "));
        Serial.print(PIL_AZAMI_V, 1);
        Serial.println(F(" V arasi olmali (ust sinir MOSFET Vdss'inden)"));
        break;
      }
      ayar.pil_kesme_v = v;
      ayar_kaydet();
      Serial.print(F("* pil kesme gerilimi "));
      Serial.print(v, 3);
      Serial.println(F(" V"));
      break;
    }

    case 'p': {
      if (s[1] == '1') {
        /* B41: yakalama surerken ADS susuyor — pil testi baslayamaz.
           `p0` (DURDUR) bu kontrolden GECMIYOR, her zaman serbest. */
        if (skop_is != SKOP_IS_YOK) {
          Serial.println(F("! pil: skop yakalamasi suruyor (ADS susuyor) — tekrar dene"));
          break;
        }
        pil_baslat();
        break;
      }
      if (s[1] == '0') {
        if (pil.durum == PIL_CALISIYOR) {
          pil_durdur(PIL_DURDURULDU, PILH_YOK);
          Serial.println(F("* pil testi DURDURULDU, yuk kesildi"));
        } else {
          pil_yuk(false);
          Serial.println(F("* pil testi zaten calismiyor; yuk kapali"));
        }
        break;
      }
      /* durum raporu */
      Serial.print(F("B "));
      Serial.print(pil_durum_metni(pil.durum));
      Serial.print(' ');
      Serial.print(yuk_mAh3(pil.yuk_pC), 3);       /* mAh */
      Serial.print(' ');
      Serial.print(enerji_wh3(pil.enerji_pJ), 5);  /* Wh */
      Serial.print(' ');
      Serial.print(pil.v_bas, 4);                  /* OCV */
      Serial.print(' ');
      Serial.print(pil.v_son, 4);
      Serial.print(' ');
      Serial.print(ayar.pil_kesme_v, 3);
      Serial.print(' ');
      Serial.print((pil.durum == PIL_CALISIYOR
                    ? (millis() - pil.baslama_ms)
                    : (pil.bitis_ms - pil.baslama_ms)) / 1000UL);
      Serial.print(' ');
      Serial.print(pil.dcir_ani, 5);
      Serial.print(' ');
      Serial.print(pil.dcir_oturmus, 5);
      Serial.print(' ');
      Serial.print(pil.dcir_sayisi);
      Serial.print(' ');
      Serial.print(pil_halka.sira);                /* uretilen nokta sayisi */
      Serial.print(' ');
      Serial.println(pil_hata_metni(pil.hata));
      break;
    }

    case 't': skop_komut(s); break;

    /* B8 — hizli yol gucu. `wR` HAM KOD basiyor (B36, dogrusallik
       supurmesi icin); duz `w` eskisi gibi guc raporluyor. */
    case 'w':
      /* B40b: yakalama gorevi surekli ADC'yi kullaniyor. */
      if (skop_is != SKOP_IS_YOK) {
        Serial.println(F("! skop: yakalama suruyor — hizli yol ADC'yi kullanamaz, tekrar dene"));
        break;
      }
      if      (s[1] == 'R') hizli_ham_yolla();
      else if (s[1] == 'B')                         /* B37 — bos pin sinamasi */
        hizli_bos_yolla(s[2] ? (uint16_t)atoi(s + 2) : (uint16_t)CEKME_BEKLE_MS);
      else                  hizli_yolla();
      break;

    /* ── B22.4: AG AYARLARI ────────────────────────────────────────
     *   N?          durumu goster (AP parolasi dahil)
     *   Na<ssid>    ev agi adi        Np<parola>  ev agi parolasi
     *   NA<parola>  AP parolasi (>=8) Ns<parola>  web parolasi
     *   N1 / N0     agi ac / kapat
     *
     * ⚠ Hepsi NVS'te AYRI ad alaninda ("olcumag"). `Ayar3` BUYUMUYOR,
     *   yani AYAR3_IMZA bumplanmiyor, yani KALIBRASYON SIFIRLANMIYOR.
     *   Bir WiFi parolasi degisikligi yeniden kalibrasyona mal olamaz.
     * ⚠ Degisiklikler bir sonraki ACILISTA gecerli — WiFi'yi kosarken
     *   yeniden baslatmak ADC DMA ile carpisiyor (DEVIR 7.1 ①).
     */
    case 'N': {
      char alt = s[1];
      const char *deg = s + 2;
      if (alt == 0 || alt == '?') {
        Serial.print(F("* ag: "));       Serial.print(ag_kip_adi(ag_durum.kip));
        Serial.print(F("  SSID="));      Serial.print(ag_durum.ssid);
        Serial.print(F("  MAC="));       Serial.print(ag_durum.mac);
        Serial.print(F("  IP="));        Serial.print(ag_durum.ip);
        Serial.print(F("  mDNS="));
        Serial.println(ag_durum.mdns ? F(AG_MDNS ".local") : F("yok"));
        Serial.print(F("* ev agi: "));
        Serial.print(ag_nvs.getString("wifi_ad", "(kurulmadi)"));
        Serial.print(F("   AP parolasi: "));
        Serial.println(ag_nvs.getString("ap_sifre", ""));
        Serial.print(F("* web parolasi: "));
        Serial.println(ag_nvs.getString("web_sifre", "").length()
                       ? F("KURULU") : F("YOK — komut ucu parolasiz"));
        break;
      }
      if (alt == 'a') { ag_nvs.putString("wifi_ad", deg);
                        Serial.print(F("* ev agi adi: ")); Serial.println(deg); }
      else if (alt == 'p') { ag_nvs.putString("wifi_sifre", deg);
                        Serial.println(F("* ev agi parolasi kaydedildi")); }
      else if (alt == 'A') {
        if (strlen(deg) < 8) { Serial.println(F("! NA: WPA2 en az 8 karakter ister")); break; }
        ag_nvs.putString("ap_sifre", deg);
        Serial.println(F("* AP parolasi kaydedildi"));
      }
      /* 🔴 Web parolasi ANINDA gecerli: web_yetkili() her istekte NVS'ten
         okuyor. Eskiden buradaki tek ortak satir "bir sonraki acilista
         gecerli" diyordu ve `Ns` (bos) ile korumayi KALDIRAN kullaniciya
         korumanin surdugunu dusundurtuyordu. Mesaj artik alt komuta gore. */
      else if (alt == 's') { ag_nvs.putString("web_sifre", deg);
                        Serial.println(strlen(deg)
                            ? F("* web parolasi kuruldu — HEMEN gecerli")
                            : F("! web parolasi KALDIRILDI — komut ucu SU AN"
                                " korumasiz")); break; }
      else if (alt == '1' || alt == '0') {
        ag_nvs.putUChar("acik", alt == '1');
        Serial.println(alt == '1' ? F("* ag ACIK") : F("* ag KAPALI"));
      }
      else { Serial.println(F("! N: N? Na<ssid> Np<parola> NA<ap> Ns<web> N1 N0")); break; }
      Serial.println(F("  (bir sonraki acilista gecerli)"));
      break;
    }

    /* ── B22.1: FABRIKA SIFIRLAMA ──────────────────────────────────
     * Bozulmus bir NVS kaydindan kurtulmanin BASKA YOLU YOKTU. Ciplak
     * `g`/`i` kazanci sifira cekip NVS'e yaziyordu ve kazanc 0 olunca
     * kalibrasyon esigi bir daha saglanmadigi icin kanal KALICI olarak
     * oluyordu. Artik o kusur kapali, ama kurtarma yolu yine de olmali:
     * imza degisimi disinda NVS'i temizlemenin yolu yok.
     * Onay eki `!` kazara tetiklenmeyi engelliyor. */
    case 'R': {
      if (s[1] != '!') {
        Serial.println(F("! R: onay gerekli — `R!` yaz. TUM kalibrasyonu ve"
                         " ayarlari fabrika degerlerine dondurur."));
        break;
      }
      varsayilan_ayar3(&ayar);
      menzil_uygula();
      ayar_kaydet();
      Serial.println(F("* FABRIKA AYARLARI yuklendi — KALIBRASYON SIFIRLANDI"));
      ayar_yaz_seri();
      break;
    }

    default:
      Serial.println(F("! bilinmeyen komut — `h` yardim"));
  }
}

void komut_isle() {
  static char tampon[48];
  static uint8_t n = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (n) {
        tampon[n] = 0;
        komut_calistir(tampon);
        n = 0;
      }
    } else if (n < sizeof(tampon) - 1) {
      tampon[n++] = c;
    }
  }
}

// ───────────────────────────────────────────────── setup / loop
/* ═══════════════════════════════════════════════════════════════════
   B28 — CIFT CEKIRDEK

   NEDEN: kartta olculdu (B27 A4). Her HTTP istegi olcum dongusunu
   BOYUTUYLA ORANTILI blokluyordu — `app.js` 186 ms, `vue` 155 ms; bir
   sayfa acilisi ~0.4 s olcum kaybi. Esik 20 ms. Ustune istemci yokken
   bile ~50-60 s'de bir 22.5 ms'lik bir olay vardi (300 s'de 5 tur).

   BOLUM:
     cekirdek 1  Arduino `loop()`  — ADS okuma, enerji, pil testi, D
                 satiri, seri komutlar, komut kuyrugunu bosaltma, skop
     cekirdek 0  `ag_gorevi()`     — WebServer, SSE yazimi, kalp atisi

   Cekirdek 0'i secmemizin sebebi: WiFi/lwIP gorevleri zaten orada.
   Ag isini oraya koymak TCP'yi kendi cekirdeginde tutuyor.

   ARALARINDA YALNIZCA KUYRUK VAR — paylasilan degisken yok:
     komut_kuyrugu_q   cekirdek 0 -> 1  (HTTP komutu)
     akis_kuyrugu_q    cekirdek 1 -> 0  (SSE satiri)
     skop_kilidi       tek tampon; OLCUM TARAFI ASLA BEKLEMEZ (timeout 0)

   Kalibrasyon (`ayar`), enerji sayaclari ve pil durumu YALNIZCA
   cekirdek 1'de yaziliyor (komutlar orada calisiyor). Pil halkasi
   ekle-yalniz: `/pil` okuyucusu yazilmis noktalara bakiyor, yazar
   eskilere dokunmuyor.

   ⚠ `vTaskDelay(1)` SART: ag gorevi bosta donerken tik birakmazsa ayni
     cekirdekteki bos gorev (IDLE0) ac kalir ve gorev bekci kopegi
     karti yeniden baslatir. */
static void ag_gorevi(void *) {
  for (;;) {
    sunucu.handleClient();
    akis_kuyrugunu_bosalt();   // olcum cekirdeginin biraktigi satirlar
    akis_kalp();               // 15 s'de bir, NAT zaman asimi icin
    ag_tur = ag_tur + 1;      // bkz. akis_tasma: tek yazar, -Wvolatile
    vTaskDelay(1);             // 1 tik = 1 ms; IDLE0 ac kalmasin
  }
}

void setup() {
  /* B28: TX tamponu buyutuldu. 115200 baud'da `?` ciktisi (9 satir,
     ~700 bayt) varsayilan tamponu doldurup `Serial.print`i BLOKLUYORDU:
     olculdu, tek bir loop() turu 27 ms. Cift cekirdekten sonra geriye
     kalan TEK >20 ms kaynagi buydu. 2 KB tampon tam ciktiyi yutuyor,
     gonderme arka planda suruyor. Serial.begin'den ONCE cagrilmali. */
  /* 🔴 B37 — 2048 -> 8192. Kartta olculdu (2026-09-13): `?` komutu
     19.4 ms blokluyordu ve olcum 1000 baytlik TEK bir write'in 229 us
     surdugunu, yani tamponun CALISTIGINI gosteriyordu. Sebep IDF'nin
     TX halkasinin turu: RINGBUF_TYPE_NOSPLIT — HER write cagrisi ayri
     bir oge, ~8 B baslik + 4 B hizalama. `Print::print(float)` rakam
     rakam yaziyor (her rakam ayri write), yani her rakam ~12 B tampon
     yeri. `?`nin 548 baytlik ciktisi ~15 float iceriyor -> ~1.4 KB
     tampon; 200'luk parcalarla olculdu: 1600 baytta doluyor, sonra her
     200 bayt 11-22 ms (hat hizi). 8 KB ile `?` sigiyor. Ayni sorun `M`
     (12 float), `F`, `W`, `S2` satirlarinda da var. Yapisal cozum
     (satiri tek write'a birlestirmek) WebAkis'te; bu, o gelene kadar
     olcumu koruyan ucuz onlem. */
  Serial.setTxBufferSize(8192);
  Serial.begin(115200);
  ayar_yukle();

  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  // B17: iki cip de TEK ATIS kipinde. SUREKLI kip birakildi cunku iki
  // ayri osilator birbirinden surukleniyordu (bkz. olcum_al ustundeki
  // aciklama). Donusumleri olcum_al ARDI ARDINA baslatiyor.
  ads_kur(ADS_AKIM, MUX_01, ayar.i_pga, false);
  menzil_uygula();

  // ALERT/RDY pinini DONUSUM HAZIR cikisi yap.
  // Veri sayfasi 7.3.8: Hi_thresh MSB=1, Lo_thresh MSB=0 yazilinca pin
  // her donusum sonunda ~8 us darbe veriyor. Beklemeden okursak AYNI
  // donusumu birkac kez okur ve "kac ornek" sayisi YALAN olur.
  ads_yaz(ADS_AKIM, ADS_UST, 0x8000);
  ads_yaz(ADS_AKIM, ADS_ALT, 0x0000);
  pinMode(PIN_HAZIR, INPUT_PULLUP);

  // B21: kapiyi ONCE LOW yap, SONRA cikis yap — sira onemli, tersi
  // olsaydi pin bir an belirsiz surulurdu.
  digitalWrite(PIN_PIL_KAPI, LOW);
  pinMode(PIN_PIL_KAPI, OUTPUT);
  digitalWrite(PIN_PIL_KAPI, LOW);
  pil_sifirla(&pil);
  // Halka tamponu burada DEGIL, PSRAM durumu ogrenildikten sonra
  // ayriliyor (asagida). pil_halka statik oldugu icin nokta=nullptr,
  // kapasite=0; pil_halka_ekle bu durumu zaten koruyor.

  skop_kur();

  // ── B22.4: AG ─────────────────────────────────────────────────────
  ag_yukle();
  jeton_uret();
  if (ag_nvs.getUChar("acik", 1)) {
    // STA dene -> olmazsa KENDI AGINI kur. "Bilgisayar yoksa" senaryosu
    // var olan bir altyapiya bagimli olamaz.
    ag_baslat();
  }

  // Ozel basliklar VARSAYILAN OLARAK TOPLANMIYOR — istenmezse
  // sunucu.header("X-Olcum") her zaman bos doner ve butun CSRF
  // savunmasi SESSIZCE devre disi kalirdi.
  const char *toplanacak[] = {"X-Olcum", "X-Jeton", "Origin"};
  sunucu.collectHeaders(toplanacak, 3);

  /* B28: kuyruklar SUNUCUDAN ONCE kurulmali — ilk istek gorev
     baslamadan once gelebilir ve `komut_kuyruga` null kuyrukta 503
     donerdi. Boyutlar: komut 8 kalem (KOMUT_KUYRUK ile ayni),
     akis 48 satir: D satiri 5/s ama skop ASCII dokumu TEK SEFERDE ~63
     satir basiyor; 24'te olculen tasma buydu. 48 x 224 B ≈ 10.7 KB. */
  komut_kuyrugu_q = xQueueCreate(KOMUT_KUYRUK, sizeof(KomutKalem));
  akis_kuyrugu_q = xQueueCreate(48, sizeof(AkisKalem));
  skop_kilidi = xSemaphoreCreateMutex();
  /* B40b: yakalama gorevi. WiFi kapali olsa da kuruluyor — skop USB'de de
     calisiyor. Yigin: yakalama dongusundeki 1 KB cerceve + skop_olc;
     olculen dip deger `?` -> C satirinda `skop_yigin_dip`. */
  skop_sonuc_q = xQueueCreate(2, sizeof(uint8_t));
  /* 🔴 B41: CEKIRDEK 1, ONCELIK 2 — cekirdek 0'da ADC verisine tek-ornek
     hata giriyordu (kartta A/B ile olculdu, gerekce SKOP_IS tanimlarinda). */
  xTaskCreatePinnedToCore(skop_gorevi, "skop", 6144, nullptr, 2,
                          &skop_gorev_kolu, 1);

  sunucu.on("/", kok_sayfa);
  sunucu.on("/akis", akis_sayfa);
  sunucu.on("/pil", pil_sayfa);   // B21
  sunucu.on("/skop.bin", skop_bin_sayfa);   // B22.5 — ikili dokum
  // ⚠ YONTEM ACIKCA yaziliyor: HTTP_ANY olsaydi `GET /komut?k=p1` de
  //   calisirdi ve <img> etiketiyle uzaktan pil desarji baslatilabilirdi.
  sunucu.on("/komut", HTTP_POST, komut_sayfa);
  sunucu.on("/komut", HTTP_OPTIONS, onuc_sayfa);
  sunucu.on("/kopru", HTTP_POST, kopru_sayfa);
  sunucu.on("/kopru", HTTP_OPTIONS, onuc_sayfa);

  // ── B22.5: ARAYUZ LittleFS'TEN ────────────────────────────────────
  // `false` = bicimlendirme YAPMA. Bos bolum bir hata degil; goruntu
  // yazilmamis demek ve `kok_sayfa` bunu SOYLUYOR. Otomatik bicimlendirme
  // basarisiz bir yazmayi "bos dosya sistemi"ne cevirip sebebi gizlerdi.
  fs_hazir = LittleFS.begin(false);
  if (fs_hazir) {
    // ⚠ SIRA ONEMLI: `/vendor/` daha OZEL, ONCE kayitli olmali.
    //   Vue surumlenmis bir varlik (vue.global.prod.js), yani `immutable`
    //   guvenli: 58 KB bir kez iniyor ve tarayici bir daha SORMUYOR.
    //   Telefonda "her acilista 58 KB" ile "bir kez" arasindaki fark bu.
    sunucu.serveStatic("/vendor/", LittleFS, "/vendor/",
                       "max-age=31536000, immutable");
    // Geri kalani `no-cache`: arayuz guncellemesi hemen gorulsun.
    sunucu.serveStatic("/", LittleFS, "/", "no-cache");
  }
  // ⚠ `enableETag` KULLANILMIYOR: `calcETag` dosyanin TAMAMINI okuyup
  //   ozet cikariyor, yani gondermek kadar bloklar ve `loop()` durur.
  //   `immutable` ayni isi SIFIR maliyetle yapiyor.
  // 🔴 B22.1 — K1. WebServer::handleClient() istemci YOKKEN her turda
  // `delay(1)` cagiriyor (WebServer.cpp:422-425, _nullDelay varsayilan
  // true). CONFIG_FREERTOS_HZ = 1000 oldugu icin bu vTaskDelay(1 tik):
  // dongu bir sonraki tik sinirina kadar blokeleniyor. Govde 1502.8 us
  // oldugundan periyot 2000 us'e KILITLENIYOR -> 665 SPS yerine 500 SPS.
  //
  // Bu, B20'nin sildigi `delay(2)` kusurunun KUTUPHANE surumu. sim3_bant
  // goremiyordu cunku yalnizca .ino'nun loop() govdesinde regex ariyor.
  // Sunucu WiFi kapaliyken bile dinleme soketi kurdugu icin (begin()
  // kosulsuz) kusur BUGUN de gecerliydi.
  sunucu.enableDelay(false);
  sunucu.begin();

  son_us = micros();
  Serial.println();
  Serial.println(F("Olcum Karti — Asama 3 (CIFT YONLU on uc)"));
  ayar_yaz_seri();

  // PSRAM DURUMU — sessiz kalmasi yasak (DEVIR 4.9).
  // Derlemenin PSRAM'li olmasi kartta PSRAM BULUNDUGUNU kanitlamaz.
  Serial.print(F("PSRAM: "));
  if (psramFound()) {
    Serial.print(ESP.getPsramSize() / 1024);
    Serial.println(F(" KB"));
    // B21: PSRAM VARSA egri tamponunu 24 saate cikar.
    const uint32_t buyuk = 24UL * 3600UL;    // 1 Hz'te 24 saat
    PilNokta *pn = (PilNokta *)ps_malloc((size_t)buyuk * sizeof(PilNokta));
    if (pn) { pil_halka.nokta = pn; pil_halka.kapasite = buyuk; }
    else Serial.println(F("  ! PSRAM ayrilamadi"));
  } else {
    Serial.println(F("YOK — derin skop bellegi kullanilamaz "
                     "(hedef2.py: PSRAM=opi mi?)"));
  }
  // PSRAM yoksa ya da ayrilamadiysa ic RAM'den al. B22.1'den once bu
  // tampon STATIKTI ve PSRAM varken bosa gidiyordu.
  if (!pil_halka.nokta) {
    pil_ic_tampon = (PilNokta *)malloc((size_t)PIL_IC_KAPASITE * sizeof(PilNokta));
    pil_halka.nokta = pil_ic_tampon;
    pil_halka.kapasite = pil_ic_tampon ? PIL_IC_KAPASITE : 0;
  }
  pil_halka_sifirla(&pil_halka);

  // 🔴 SURE ELLE YAZILMIYOR, kapasiteden TURETILIYOR. Eskiden burada
  // "(2 saat)" yaziyordu ama PIL_IC_KAPASITE 5400 = 1.5 saatti; acilis
  // satiri kullaniciya YANLIS bilgi veriyordu (pil_test.h:59 da "2 saat"
  // diyor). Sayi degisince metin kendiliginden dogru kalsin.
  Serial.print(F("  pil egri tamponu: "));
  if (pil_halka.kapasite) {
    const float hz = ayar.pil_kayit_hz > 0.01f ? ayar.pil_kayit_hz : 1.0f;
    Serial.print(pil_halka.kapasite);
    Serial.print(F(" nokta = "));
    Serial.print((float)pil_halka.kapasite / hz / 3600.0f, 2);
    Serial.print(F(" saat @ "));
    Serial.print(hz, 2);
    Serial.print(F(" Hz, "));
    Serial.print((uint32_t)((size_t)pil_halka.kapasite * sizeof(PilNokta) / 1024u));
    Serial.print(F(" KB "));
    Serial.println(pil_halka.nokta == pil_ic_tampon ? F("(ic RAM)") : F("(PSRAM)"));
  } else {
    Serial.println(F("AYRILAMADI — mAh/Wh sayaclari calisir, EGRI KAYDI YOK"));
  }

  Serial.println(F("Cikis: D <volt> <amper> <watt> <joule> <wh> <ms> "
                   "<ornek> <menzil> <durum>"));
  Serial.println(F("`h` yardim"));
  if (!skop_kulp) Serial.println(F("! osiloskop suruculu kurulamadi"));
  // ── B22.4: AG DURUMU — sessiz kalmasi YASAK ──────────────────────
  Serial.print(F("Ag: "));
  Serial.print(ag_kip_adi(ag_durum.kip));
  if (ag_durum.kip != AG_KAPALI) {
    Serial.print(F("  SSID=")); Serial.print(ag_durum.ssid);
    /* B26: GERCEK MAC. Ad bundan turetiliyor; ikisi ayrisirsa SSID
       yanlis uretilmis demektir (bkz. ag.h'deki B26 notu). */
    Serial.print(F("  MAC=")); Serial.print(ag_durum.mac);
    Serial.print(F("  http://")); Serial.print(ag_durum.ip);
    if (ag_durum.mdns) Serial.print(F("  http://" AG_MDNS ".local"));
  }
  /* 🔴 Buradaki println EKSIKTI: "Ag:" satiri kapanmadigi icin cikti
     `...http://192.168.4.1Arayuz: YOK...` seklinde yapisiyordu. Adresi
     seri konsoldan kopyalayan kullanici BOZUK bir adres aliyordu ve
     acilis afisi ayristirilamaz haldeydi. B25 bringup kosucusu
     hazirlanirken bulundu (2026-09-11); sim3_web.py artik afisin her
     satirinin KAPANDIGINI ayrica sinıyor. */
  Serial.println();
  Serial.print(F("Arayuz: "));
  Serial.println(fs_hazir ? F("LittleFS'te (karttan servis ediliyor)")
                          : F("YOK — uretim/arayuz-yaz.py ile yukleyin"));
  Serial.println();
  if (ag_durum.kip == AG_AP) {
    // AP parolasi RASTGELE uretildi ve NVS'te; kullanici bir kez buradan
    // okuyup telefonuna yaziyor. MAC'ten turetseydik hicbir sey korumazdi
    // (SSID zaten MAC son ekini yayinliyor).
    Serial.print(F("  AP parolasi: "));
    Serial.println(ag_nvs.getString("ap_sifre", ""));
  }
  /* B28: ag gorevi EN SONDA baslatiliyor — sunucu, kuyruklar ve afis
     hazir olduktan sonra. Onceden baslatilsaydi ilk istek yarim kurulmus
     bir sunucuya duserdi. Yigin 8 KB: WebServer + LittleFS akisi
     (olculen dip deger `?` ciktisinda). */
  if (ag_durum.kip != AG_KAPALI) {
    xTaskCreatePinnedToCore(ag_gorevi, "ag", 8192, nullptr, 1,
                            &ag_gorev_kolu, 0);
    Serial.print(F("Cekirdek: olcum="));
    Serial.print(xPortGetCoreID());
    Serial.println(F("  ag=0 (WebServer + SSE ayri gorevde)"));
  }

  if (ag_durum.kip != AG_KAPALI && !ag_nvs.getString("web_sifre", "").length()) {
    // Sessiz "guvenlik yok" durumu, guvenlik olmamasindan daha kotudur.
    Serial.println(F("! UYARI: web parolasi YOK — komut ucu yalnizca jeton"
                     " ve Host denetimiyle korunuyor. `Ns<parola>` ile kur."));
  }
}

static bool pil_testi_suruyor() { return pil.durum == PIL_CALISIYOR; }

void loop() {
  // B22.1: tur suresini OLC. Blokaj iddiasi olculmeden dogrulanamaz.
  {
    static uint32_t tur_son_us = 0;
    uint32_t simdi = micros();
    if (tur_son_us) {
      uint32_t tur = simdi - tur_son_us;
      if (tur > loop_azami_us) { loop_azami_us = tur; k_degisti = 1; }
      if (tur > 20000UL) { loop_uzun_adet++; k_degisti = 1; }
    }
    tur_son_us = simdi;
  }

  /* 🔴 B28: `sunucu.handleClient()` ve `akis_kalp()` BURADAN CIKTI —
     ikisi de artik cekirdek 0'daki `ag_gorevi()` icinde. Sayfa sunmak
     bu donguyu bloklamiyor. Komutlar yine BURADA calisiyor: tek yazar
     disiplini korunuyor (kalibrasyon, NVS, skop hep cekirdek 1'de). */
  komut_isle();              // seri porttan gelen komutlar
  komut_kuyrugu_bosalt();    // HTTP'den gelenler — TEK yazar, cekirdek 1
  skop_sonuc_isle();         // B40b: yakalama gorevinin sonucu
  skop_dokum_ilerle();       // B40: skop dokumu, TX'te yer oldugu kadar

  // 🔴 B20 (2026-09-10) — BURADA OLU BIR BEKLEME VARDI:
  //     if (!yeni_donusum_bekle(4000)) delay(2);
  // Bu, SUREKLI kipten kalmaydi: orada donusumler kendiliginden akiyordu
  // ve bu bekleme dongunun HIZ AYARLAYICISIYDI. B17 TEK ATIS kipine
  // gecince donusumu olcum_al'in KENDISI baslatiyor, dolayisiyla buraya
  // gelindiginde UCUSTA DONUSUM YOK: bir onceki olcum_al iki yazmaci da
  // okumustu ve tek atis kipi donusum bitince kapaniyor. Yani bu bekleme
  // ALERT KUSURSUZ CALISSA BILE her turda 4000 us zaman asimina dusuyor,
  // ustune delay(2) ekleniyordu.
  //
  // Olculdu (uretim/sim3_bant.py): bu blok tek basina dongu periyodunu
  // 5.72 ms'ten 11.0 ms'e cikariyordu. COMP_QUE duzeltmesiyle birlikte
  // periyot 1.49 ms'e (671 SPS) iniyor.
  //
  // ⚠ delay(2) bu dongudeki TEK vTaskDelay idi. Silinince loop() hic
  //   yield etmez ve ayni cekirdekteki dusuk oncelikli gorevler ac kalir.
  //   Bu yuzden yerine yield() konuyor — o, gorev degistirmeyi birakir
  //   ama bir tik beklemez.
  yield();

  /* 🔴 B41 — YAKALAMA SURERKEN ADS SUSUYOR. Yuklu I2C hattinin kenarlari
     skop donusumune tek-ornek hata sokuyor; pini tasimak cozmuyor (B44)
     (gerekce ve olcum: SKOP_IS tanimlarinin yaninda). Susma sayiliyor;
     enerji araligi >1 s ise `enerji_biriktir` eskisi gibi kayip yaziyor. */
  if (skop_is != SKOP_IS_YOK) {
    if (!ads_duraklama_bas_ms) ads_duraklama_bas_ms = millis() | 1u;
    if (kuplaj_aktif) kuplaj_patlat();       /* B44 deneyi — yalnizca `tK` */
    return;
  }
  if (kuplaj_aktif) kuplaj_bitir();          /* Wire, ADS okunmadan ONCE geri */
  if (ads_duraklama_bas_ms) {
    ads_duraklama_top_ms += millis() - ads_duraklama_bas_ms;
    ads_duraklama_bas_ms = 0;
  }

  Okuma3 o = olcum_al();
  // Guc ORNEK BASINA carpilir: ort(VxI) != ort(V) x ort(I).
  // B27/K1: iki ciften biri okunamadiysa watt COP — enerjiye katma.
  // (Ornek yine sayiliyor ve D basiliyor; arayuz `durum` alanindan
  // hangi kanalin gecersiz oldugunu ogreniyor. D'yi kesmek karti olu
  // gosterirdi, o daha kotu.)
  if (!ads_hata) enerji_biriktir(o.watt);
  // B21: pil testi kendi sayaclarini AYRI tutuyor (genel enerji sayaci
  // sifirlanabiliyor; test sayaci teste ait olmali).
  {
    static uint32_t pil_son_us = 0;
    uint32_t simdi_us = micros();
    uint32_t dt = simdi_us - pil_son_us;
    pil_son_us = simdi_us;
    if (dt < 1000000UL) pil_isle(o, dt);
  }

  v_top += o.volt;
  i_top += o.amper;
  w_top += o.watt;
  ornek++;

  uint32_t ms = millis();
  if (ms - son_rapor >= rapor_ms && ornek) {
    snprintf(son_satir, sizeof(son_satir),
             "D %.4f %.6f %.5f %.4f %.7f %lu %lu %u %u",
             (double)(v_top / ornek), (double)(i_top / ornek),
             (double)(w_top / ornek),
             (double)enerji_joule3(enerji_pJ),
             (double)enerji_wh3(enerji_pJ),
             (unsigned long)ms, (unsigned long)ornek,
             (unsigned)ayar.menzil,
             /* B27/K1: pencere boyunca BIRIKEN ADC hatasi. bit0 = GERILIM
                (0x49) okunamadi, bit1 = AKIM (0x48) okunamadi. 0 = ikisi
                de yanit verdi. Arayuz bununla "veri yok"u "veri sifir"dan
                ayiriyor. Tek ornek bile hataliysa pencere isaretli. */
             (unsigned)ads_hata_pencere);
    ads_hata_pencere = 0;
    /* 🔴 B26: BURADAKI `akis_yolla(son_satir)` KALDIRILDI — SATIR IKI KEZ
       GIDIYORDU. B20 bu cagriyi ekledigi sirada SSE'yi besleyen TEK yol
       buydu. B22.4 `Serial` aynasini (WebAkis) getirdi: tamamlanan HER
       satir `web_satir_hazir()` -> `akis_yolla()` yolundan zaten gidiyor.
       Eski cagri kaldirilmadi ve her `D` satiri akisa IKI KEZ dustu.

       Tezgahta olculdu (2026-09-12): 8 sn'de 80 `D` olayi, 40 benzersiz
       satir, tekrar dagilimi {2: 40} — istisnasiz hepsi cift. Kartin
       rapor hizi 5/s iken yayin 10/s idi. Bedeli: iki kat WiFi trafigi,
       grafikte ust uste binen noktalar, CSV'de cift satir.

       ⚠ Bir mekanizma daha genelini getirdiginde ESKISINI KALDIR;
       ikisi birlikte calisirsa sonuc sessizce iki katina cikar. */
    Serial.println(son_satir);
    /* B22.1: `K` YALNIZ degisince basiliyor — surekli akista gurultu
       yapmasin. ⚠ `D` satirina ALAN EKLENMEDI: 9 alan arayuzde,
       sahte-kart.js'te ve testte sabit; alan eklemek ucunu ayni anda
       degistirmeyi gerektirir (B17'nin f/F kusurunun aynisi). Yeni
       onek geriye donuk uyumlu: bilmeyen istemci gunluge dusurur. */
    if (k_degisti) {
      char ksat[72];
      snprintf(ksat, sizeof(ksat), "K %lu %lu %lu",
               (unsigned long)enerji_kayip_ms,
               (unsigned long)loop_azami_us,
               (unsigned long)loop_uzun_adet);
      Serial.println(ksat);   /* ayna SSE'ye kendisi yolluyor — B26 */
      k_degisti = 0;
    }
    v_top = i_top = w_top = 0;
    ornek = 0;
    son_rapor = ms;
  }
}
