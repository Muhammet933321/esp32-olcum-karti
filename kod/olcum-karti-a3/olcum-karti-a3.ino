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
static const uint8_t PIN_HAZIR = 7;         // ADS #1 ALERT/RDY
// B21: pil testi MOSFET kapisi. J5'in eski YEDEK pini (10) buraya gidiyor.
// GPIO6 strapping pini DEGIL; acilista giris kipinde, yani kapi R42 ile
// GND'ye cekili ve MOSFET KAPALI. Failsafe daha ilk milisaniyeden gecerli.
static const uint8_t PIN_PIL_KAPI = 6;
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
static uint32_t rapor_ms = 200;
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


Okuma3 olcum_al() {
  // 1) GERILIM once, AKIM sonra baslatiliyor. Aradaki fark iki I2C
  //    yazmasinin suresi: 400 kHz'te ~95 us. SABIT ve BILINEN.
  ads_tek_atis_baslat(ADS_GERILIM, etkin_mux(), etkin_kanal()->pga);
  uint32_t t_yaz_bas = micros();
  ads_tek_atis_baslat(ADS_AKIM, MUX_01, ayar.i_pga);
  uint32_t t_kayma_us = micros() - t_yaz_bas;   // OLCULUYOR, varsayilmiyor

  // 2) Donusumun bitmesini bekle. ALERT/RDY akim cipinde kurulu; o
  //    bittiyse gerilim de bitmistir (once baslatildi, ayni sure).
  if (!yeni_donusum_bekle(4000)) delayMicroseconds(1300);

  int16_t ham_v = ads_oku(ADS_GERILIM);
  int16_t ham_i = ads_oku(ADS_AKIM);

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
    skop_ofsetle(&m);

    Serial.print(F("S2 "));
    Serial.print(skop_adet);                    Serial.print(' ');
    Serial.print(skop_hz);                      Serial.print(' ');
    Serial.print(skop_volt_adim(), 6);          Serial.print(' ');
    Serial.print(skop_tetik_idx);               Serial.print(' ');
    Serial.print(SKOP_TDIV_US[skop_ayar.tdiv]); Serial.print(' ');
    Serial.print(skop_ayar.kip);                Serial.print(' ');
    Serial.print(skop_tetiklendi ? 1 : 0);      Serial.print(' ');
    /* B19: 9. alan — volt ofseti. Arayuz p.length >= 8 baktigi icin
     * eski surumler bu alani gormezden gelir (geriye uyumlu). */
    Serial.println(skop_volt_ofset(), 6);

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


// Osiloskop komutlari. Asama 2'de `komut_calistir` icinde satir ici
// idi; Asama 3'te fonksiyona cikarildi ki komut isleyici sadeleşsin.
// GOVDE ASAMA 2 ILE AYNI — davranis degismedi.
void skop_komut(const char *s) {
      char alt = s[1];
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
        if (skop_yakala()) {
          Serial.print(F("* skop yakalandi (ikili): "));
          Serial.print(skop_adet);
          Serial.print(F(" ornek @ "));
          Serial.print(skop_hz);
          Serial.println(F(" Hz — /skop.bin"));
        } else {
          Serial.println(F("! tetiklenemedi"));
        }
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
static void hizli_olcekle(uint16_t adet) {
    const float lsb = SKOP_ADC_TAVAN / SKOP_ADC_SAYIM;
    for (uint16_t n = 0; n < adet; n++) {
        hizli_v[n] = VREF_NOMINAL
                     + (hizli_v[n] * lsb - VREF_NOMINAL) * SKOP_ORAN;
        float vc = hizli_i[n] * lsb;
        hizli_i[n] = (vc - VREF_NOMINAL) / HIZLI_KAZANC / ayar.sont_ohm
                     * ayar.i_duzeltme;
    }
}

// `w` komutu — bir pencere yakalayip gucu raporlar.
//
// PROTOKOL:
//   W <P> <S> <PF> <Vrms> <Irms> <Vort> <Iort> <n> <P_hizalamasiz>
//
// Son alan BILEREK var: hizalamanin ne kadar fark ettigini arayuz
// gosterebilsin. Dirençsel yukte ikisi ayni cikar, reaktif yukte
// duzeltmesiz olan belirgin sapar (B8: 1 kHz PF=0.1'de %78).
static void hizli_yolla(void) {
    if (!skop_kulp) { Serial.println(F("! hizli yol: ADC kulpu yok")); return; }

    // Skop yapilandirmasini birak, iki kanalliya gec
    adc_continuous_stop(skop_kulp);
    if (!hizli_kur()) {
        Serial.println(F("! hizli yol: 2 kanalli yapilandirma basarisiz"));
        return;
    }
    if (adc_continuous_start(skop_kulp) != ESP_OK) {
        Serial.println(F("! hizli yol: baslatilamadi"));
        return;
    }

    uint16_t nv = 0, ni = 0;
    bool tamam = hizli_yakala(&nv, &ni);
    adc_continuous_stop(skop_kulp);

    if (!tamam) {
        Serial.print(F("! hizli yol: yeterli ornek yok  V="));
        Serial.print(nv); Serial.print(F(" I=")); Serial.println(ni);
        return;
    }

    uint16_t adet = (nv < ni) ? nv : ni;
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
    Serial.println(g0.p, 5);

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

  uint8_t b[32];
  memset(b, 0, sizeof(b));
  b[0] = 'S'; b[1] = '3'; b[2] = 'B'; b[3] = (uint8_t)SKOP_BIN_SURUM;
  uint16_t adet = skop_adet;
  uint32_t hz = skop_hz;
  float adim = skop_volt_adim();
  float ofset = skop_volt_ofset();
  uint32_t tdiv = SKOP_TDIV_US[skop_ayar.tdiv];
  uint16_t tidx = skop_tetik_idx;
  memcpy(b + 4,  &adet,  2);
  memcpy(b + 8,  &hz,    4);
  memcpy(b + 12, &adim,  4);
  memcpy(b + 16, &ofset, 4);
  memcpy(b + 20, &tdiv,  4);
  memcpy(b + 24, &tidx,  2);
  b[26] = (uint8_t)skop_ayar.kip;
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
  bool giden = false;
  for (int8_t i = 0; i < AKIS_AZAMI; i++) {
    if (!akis[i]) continue;
    if (!akis[i].connected()) { akis[i].stop(); continue; }
    akis[i].print(F("id: "));
    akis[i].print(akis_sira);
    akis[i].print(F("\ndata: "));
    akis[i].print(satir);
    akis[i].print(F("\n\n"));
    giden = true;
  }
  if (!giden) akis_dusen++;
}

// `Serial` aynasinin geri cagrisi — tamamlanan her satir buraya geliyor.
void web_satir_hazir(const char *satir) {
  akis_yolla(satir);
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
static char komut_kuyruk[KOMUT_KUYRUK][48];
static uint8_t komut_bas = 0, komut_adet = 0;

static bool komut_kuyruga(const char *k) {
  if (komut_adet >= KOMUT_KUYRUK) return false;
  uint8_t yer = (uint8_t)((komut_bas + komut_adet) % KOMUT_KUYRUK);
  snprintf(komut_kuyruk[yer], sizeof(komut_kuyruk[0]), "%s", k);
  komut_adet++;
  return true;
}

static void komut_kuyrugu_bosalt() {
  while (komut_adet) {
    char yerel[48];
    snprintf(yerel, sizeof(yerel), "%s", komut_kuyruk[komut_bas]);
    komut_bas = (uint8_t)((komut_bas + 1) % KOMUT_KUYRUK);
    komut_adet--;
    komut_calistir(yerel);
  }
}

// 🔴 `p0` (pil desarjini DURDUR) HER ZAMAN serbest: jetonsuz, parolasiz.
//    Baslatmak yetki ister; durdurmayi hicbir sey geciktiremez. Bu bir
//    kolaylik degil EMNIYET karari — koprude de ayni kural var.
static bool komut_serbest(const char *k) {
  return k[0] == 'p' && k[1] == '0' && k[2] == 0;
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
                  "gecersiz oturum jetonu. `p0` (durdur) her zaman acik.");
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
  Serial.print(F(" i_ofset="));   Serial.println(ayar.i_ofset);

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
}

// Bir ADS1115 cevap vermiyorsa sebep genelde uctan bire indirgenir:
// ADDR bosta, SDA/SCL ters, ya da pull-up yok.
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
  Serial.println(F("  R! fabrika ayarlari (kalibrasyonu SIFIRLAR)"));
  Serial.println(F("  t yakala  ta otomatik  tb<0-11> zaman tabani  t+ t-"));
  Serial.println(F("  tl<0-4095> esik  te<0/1> kenar  th<hist>  tp<%>  tm<kip>  t?"));
}

void komut_calistir(const char *s) {
  switch (s[0]) {
    case '?': ayar_yaz_seri(); break;
    case 'h': case 'Y': yardim(); break;
    case '#': i2c_tara(); break;

    case 'e':
      enerji_pJ = 0;
      Serial.println(F("* enerji sifirlandi"));
      break;

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
      if (s[1] == '1') { pil_baslat(); break; }
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

    case 'w': hizli_yolla(); break;   /* B8 — hizli yol gucu */

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
void setup() {
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
                   "<ornek> <menzil>"));
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
  if (ag_durum.kip != AG_KAPALI && !ag_nvs.getString("web_sifre", "").length()) {
    // Sessiz "guvenlik yok" durumu, guvenlik olmamasindan daha kotudur.
    Serial.println(F("! UYARI: web parolasi YOK — komut ucu yalnizca jeton"
                     " ve Host denetimiyle korunuyor. `Ns<parola>` ile kur."));
  }
}

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

  sunucu.handleClient();
  akis_kalp();               // B22.4: 15 s'de bir, NAT zaman asimi icin
  komut_isle();              // seri porttan gelen komutlar
  komut_kuyrugu_bosalt();    // B22.4: HTTP'den gelenler — TEK yazar

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

  Okuma3 o = olcum_al();
  // Guc ORNEK BASINA carpilir: ort(VxI) != ort(V) x ort(I).
  enerji_biriktir(o.watt);
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
             "D %.4f %.6f %.5f %.4f %.7f %lu %lu %u",
             (double)(v_top / ornek), (double)(i_top / ornek),
             (double)(w_top / ornek),
             (double)enerji_joule3(enerji_pJ),
             (double)enerji_wh3(enerji_pJ),
             (unsigned long)ms, (unsigned long)ornek,
             (unsigned)ayar.menzil);
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
