/*
 * Ölçüm Kartı — Aşama 1  (Arduino Uno / Nano, ATmega328P)
 *
 * Voltmetre · Ampermetre · Wattmetre · Enerji sayacı · Basit osiloskop
 *
 * Donanım (hepsi envanterden):
 *   AREF   <- TL431 (IC002) + 1K (R029) bias + 220R (R006) seri + 100nF (C008)
 *   A0     <- 100K (R025) / 10K (R032) bölücü, 1nF (C049), 2x 1N4148 (D003) kelepçe
 *   A1     <- LM358 (IC003) çıkışı, kazanç 1 + 47K (R040) / 6.8K (R018)
 *   şönt   <- 1 / 10 / 30 adet 10R (R001) paralel
 *
 * Seri port: 115200 baud. Komutlar için 'y' (yardım) yaz.
 *
 * TEHLİKE: analogReference(EXTERNAL) ilk analogRead()'den ÖNCE çağrılmalı.
 *          Aksi halde dahili referans harici referansla kısa devre olur ve
 *          mikrodenetleyici yanabilir. setup() bunu ilk iş olarak yapıyor.
 */

#include <EEPROM.h>
#include "tipler.h"

// ------------------------------------------------------------------ pinler
const uint8_t PIN_GERILIM = A0;
const uint8_t PIN_AKIM    = A1;

// ------------------------------------------------------- devre sabitleri
// Simülasyonla doğrulanmış değerler (uretim/sim_*.py)
const float AREF_V      = 2.470f;   // ÖLÇÜLDÜ 2026-09-07 (multimetre, AREF-GND)
const float BOLME_ORANI = 11.0f;    // (100K + 10K) / 10K
const float KAZANC      = 7.9118f;  // 1 + 47K/6.8K

// Şönt kademeleri — kartta hangisi takılıysa onu seç
const float SONT_1X10R  = 10.0f;        // 0 – 31 mA
const float SONT_10X10R = 1.0f;         // 0 – 313 mA
const float SONT_30X10R = 10.0f / 30;   // 0 – 940 mA

// --------------------------------------------------------------- ayarlar
const uint16_t IMZA = 0xC0FE;
const int EEPROM_ADRES = 0;

Ayar ayar;   // tanımı tipler.h içinde

uint16_t rapor_ms = 200;   // rapor aralığı (ms), 'h' komutuyla değişir

// Ham ADC -> mühendislik birimi çarpanları (ayar değişince yeniden hesaplanır)
float v_adim;   // volt / adım
float i_adim;   // amper / adım

void carpanlari_hesapla() {
  const float lsb = AREF_V / 1024.0f;
  v_adim = lsb * BOLME_ORANI * ayar.v_duzeltme;
  i_adim = lsb / KAZANC / ayar.sont_ohm * ayar.i_duzeltme;
}

void varsayilan_ayar() {
  ayar.imza       = IMZA;
  ayar.sont_ohm   = SONT_1X10R;
  ayar.v_duzeltme = 1.0f;
  ayar.i_duzeltme = 1.0f;
  ayar.i_ofset    = 0;
}

void ayar_yukle() {
  EEPROM.get(EEPROM_ADRES, ayar);
  if (ayar.imza != IMZA) varsayilan_ayar();
  carpanlari_hesapla();
}

void ayar_kaydet() {
  ayar.imza = IMZA;
  EEPROM.put(EEPROM_ADRES, ayar);
  carpanlari_hesapla();
}

// ---------------------------------------------------------------- enerji
/*
 * Enerji birikimi TAM SAYI ile tutulur.
 *
 * ATmega328P'de `double` diye ayrı bir tip yoktur, `float`a takma addır:
 * 24 bit mantis ≈ 7 anlamlı basamak. Enerjiyi float'ta biriktirirsen toplam
 * büyüdükçe küçük eklemeler sessizce yutulur ve sayaç yavaşlar.
 *
 * Birim seçimi: µW × µs = pJ — çarpma tam sayı, kayıp yok.
 * uint64 tavanı 1.8e19 pJ = 5.1 kWh. 25 W'lık bu kart için 200 saatten fazla
 * kesintisiz tam güç demek; pratikte ulaşılmaz.
 */
uint64_t enerji_pJ = 0;
uint32_t son_us    = 0;

float enerji_wh() {
  /*
   * 1 Wh = 3600 J = 3.6e15 pJ.
   *
   * Burada bir kere 3.6e18 yazılıydı — o 1 kWh'in pJ karşılığı. Wh alanı
   * tam 1000 kat küçük çıkıyordu. Joule alanı doğru olduğu için gözden
   * kaçıyordu: iki alan birbiriyle karşılaştırılana kadar sessizce yanlıştı.
   * S9 uçtan uca testi (wh × 3600 == joule) yakaladı.
   */
  return (float)((double)enerji_pJ / 3.6e15);
}

float enerji_joule() {
  return (float)((double)enerji_pJ / 1.0e12);
}

// ------------------------------------------------------------ okuma katı
// Gerilim ve akımı ard arda okuyup gücü ÖRNEK BAŞINA çarpar.
// Önce çarpıp sonra ortalamak şart: ort(V×I) ≠ ort(V) × ort(I).
/*
 * KANAL GECISI: her kanal IKI KEZ okunur, ilki atilir.
 *
 * DIKKAT — burada once yanlis bir gerekce yazmistim: "9 kohm kaynak
 * empedansinda ornekle-tut kondansatoru tek okumada bosalamaz". Veri sayfasi
 * (Atmel-42735B, Sekil 28-8) bunu DESTEKLEMIYOR:
 *
 *   "The ADC is optimized for analog signals with an output impedance of
 *    approximately 10 kohm or less. If such a source is used, the sampling
 *    time will be negligible."
 *
 * Bolucu dugumu 100K||10K = 9.09 kohm, yani sinirin icinde. C_S/H = 14 pF ile
 * zaman sabiti 127 ns; en dar ornekleme penceresi bile (serbest calismada
 * 2 ADC saati = 2 us) 15 zaman sabiti eder. Sizma ihmal edilebilir —
 * simulasyon da bunu dogruluyor.
 *
 * Atma okumasinin GERCEK gerekcesi veri sayfasinin kendi tavsiyesi
 * (Bolum 28.5.1): kanal secimi degistikten sonra ilk sonuc guvenilir degil.
 * Ayrica tezgahta gorulen kanal karismasinin asil sebebi HAVADA DURAN A0
 * ucuydu; A1'i topraklamak duzeltmemisti.
 *
 * Bedeli ornekleme hizinin yariya inmesi: ~1720 ornek/sn, 50 ms pencerede
 * 86 ornek, √86 ≈ 9x gurultu bastirma. Dogruluk hizdan onemli.
 */
Okuma olc() {
  analogRead(PIN_GERILIM);                    // oturma okumasi, atilir
  int ham_v = analogRead(PIN_GERILIM);
  analogRead(PIN_AKIM);                       // oturma okumasi, atilir
  int ham_i = analogRead(PIN_AKIM);

  Okuma o;
  o.volt  = ham_v * v_adim;
  o.amper = (ham_i - ayar.i_ofset) * i_adim;
  if (o.amper < 0) o.amper = 0;        // tek yönlü ölçüm
  o.watt  = o.volt * o.amper;
  return o;
}

void enerji_biriktir(float watt) {
  uint32_t simdi = micros();
  uint32_t dt_us = simdi - son_us;     // taşma sarmalı doğru çalışır
  son_us = simdi;

  if (dt_us > 1000000UL) return;       // ilk tur veya uzun duraklama: sayma

  uint32_t guc_uW = (watt > 0) ? (uint32_t)(watt * 1e6f) : 0;
  enerji_pJ += (uint64_t)guc_uW * dt_us;
}

// ------------------------------------------------------- osiloskop kipi
/*
 * Serbest çalışan ADC, prescaler 16 -> 1 MHz ADC saati -> 76.9 kSa/s.
 * ADLAR ile sola hizalanıp yalnız ADCH okunur: 8 bit, tampon iki kat uzun.
 */
const uint16_t TAMPON = 1000;          // 1000 örnek = 13 ms pencere
uint8_t tampon[TAMPON];

void adc_hizli_baslat(uint8_t kanal) {
  ADMUX  = (0 << REFS1) | (0 << REFS0)   // harici AREF
         | (1 << ADLAR)                  // sola hizala (8 bit ADCH'de)
         | (kanal & 0x0F);
  ADCSRB = 0;                            // serbest çalışma
  ADCSRA = (1 << ADEN) | (1 << ADSC) | (1 << ADATE)
         | (1 << ADIF) | (1 << ADPS2);   // prescaler 16
}

void adc_normale_don() {
  ADCSRA = (1 << ADEN) | (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);
  ADMUX  = (0 << REFS1) | (0 << REFS0);
}

// Yükselen kenarda tetikler, sonra tamponu doldurur.
// esik: 8 bit ham değer. 0 verilirse tetikleme beklemez.
bool osiloskop_yakala(uint8_t kanal, uint8_t esik) {
  adc_hizli_baslat(kanal);

  // ilk dönüşümü at (kanal değişimi sonrası ADC oturması)
  for (uint8_t i = 0; i < 4; i++) {
    while (!(ADCSRA & (1 << ADIF))) {}
    ADCSRA |= (1 << ADIF);
  }

  bool tetiklendi = (esik == 0);
  if (!tetiklendi) {
    // önce eşiğin altına in, sonra yukarı kesişimi bekle
    uint32_t bekleme = 200000UL;
    bool altta = false;
    while (bekleme--) {
      while (!(ADCSRA & (1 << ADIF))) {}
      uint8_t v = ADCH;
      ADCSRA |= (1 << ADIF);
      if (!altta) { if (v < esik) altta = true; }
      else if (v >= esik) { tetiklendi = true; break; }
    }
  }

  if (tetiklendi) {
    for (uint16_t i = 0; i < TAMPON; i++) {
      while (!(ADCSRA & (1 << ADIF))) {}
      tampon[i] = ADCH;
      ADCSRA |= (1 << ADIF);
    }
  }

  adc_normale_don();
  return tetiklendi;
}

// ------------------------------------------------------------- komutlar
void yardim() {
  Serial.println(F("--- Olcum Karti — komutlar ---"));
  Serial.println(F("  o : olcum (surekli akis) ac/kapa"));
  Serial.println(F("  s : akim kanalini SIFIRLA (yuku kes, sonra bas)"));
  Serial.println(F("  e : enerji sayacini sifirla"));
  Serial.println(F("  kv<volt>  : gerilim kalibrasyonu, orn. kv12.34"));
  Serial.println(F("  ka<amper> : akim kalibrasyonu,    orn. ka0.250"));
  Serial.println(F("  r<ohm>    : takili sont degeri,   orn. r1.0"));
  Serial.println(F("  d : mevcut ayarlari goster"));
  Serial.println(F("  h<ms>     : rapor araligi (20-5000), orn. h500"));
  Serial.println(F("  t[esik]   : osiloskop yakala (A0), orn. t128"));
  Serial.println(F("  y : bu yardim"));
  Serial.println(F("Cikis bicimi: D <volt> <amper> <watt> <joule> <wh> <ms> <ornek>"));
  Serial.println(F("Osiloskop   : S <adet> <Hz> <volt/adim> + ham 8-bit degerler"));
}

void ayarlari_goster() {
  Serial.println(F("--- ayarlar ---"));
  Serial.print(F("  sont      : ")); Serial.print(ayar.sont_ohm, 4); Serial.println(F(" ohm"));
  Serial.print(F("  v duzeltme: ")); Serial.println(ayar.v_duzeltme, 5);
  Serial.print(F("  i duzeltme: ")); Serial.println(ayar.i_duzeltme, 5);
  Serial.print(F("  i ofset   : ")); Serial.println(ayar.i_ofset);
  Serial.print(F("  rapor     : ")); Serial.print(rapor_ms); Serial.println(F(" ms"));
  Serial.print(F("  tam olcek : ")); Serial.print(1023 * v_adim, 2);
  Serial.print(F(" V / ")); Serial.print(1023 * i_adim * 1000, 1); Serial.println(F(" mA"));
}

void akim_sifirla() {
  Serial.println(F("Yuku kes... 2 sn"));
  delay(2000);
  long toplam = 0;
  for (int i = 0; i < 64; i++) { analogRead(PIN_AKIM);
                                toplam += analogRead(PIN_AKIM); delay(2); }
  ayar.i_ofset = (int16_t)(toplam / 64);
  ayar_kaydet();
  Serial.print(F("Ofset = ")); Serial.print(ayar.i_ofset);
  Serial.print(F(" adim = ")); Serial.print(ayar.i_ofset * i_adim * 1000, 3);
  Serial.println(F(" mA (LM358 giris ofseti)"));
}

void kalibre_gerilim(float gercek) {
  long toplam = 0;
  for (int i = 0; i < 64; i++) { analogRead(PIN_GERILIM);
                                toplam += analogRead(PIN_GERILIM); delay(2); }
  float ham = (toplam / 64.0f) * (AREF_V / 1024.0f) * BOLME_ORANI;
  if (ham < 0.1f) { Serial.println(F("HATA: giris cok dusuk")); return; }
  ayar.v_duzeltme = gercek / ham;
  ayar_kaydet();
  Serial.print(F("v_duzeltme = ")); Serial.println(ayar.v_duzeltme, 5);
}

void kalibre_akim(float gercek) {
  long toplam = 0;
  for (int i = 0; i < 64; i++) { analogRead(PIN_AKIM);
                                toplam += analogRead(PIN_AKIM); delay(2); }
  float ham = ((toplam / 64.0f) - ayar.i_ofset)
            * (AREF_V / 1024.0f) / KAZANC / ayar.sont_ohm;
  if (ham < 1e-4f) { Serial.println(F("HATA: akim cok dusuk")); return; }
  ayar.i_duzeltme = gercek / ham;
  ayar_kaydet();
  Serial.print(F("i_duzeltme = ")); Serial.println(ayar.i_duzeltme, 5);
}

// ------------------------------------------------------------------ ana
bool akis = true;
uint32_t son_rapor = 0;

void setup() {
  // *** ILK IS: harici referansi sec. Bunu analogRead'den once yapmak sart. ***
  analogReference(EXTERNAL);

  Serial.begin(115200);
  ayar_yukle();
  son_us = micros();

  Serial.println();
  Serial.println(F("Olcum Karti — Asama 1 (Arduino)"));
  ayarlari_goster();
  yardim();
}

/*
 * Komut okuma — String DEGIL sabit tampon.
 *
 * AVR'de String yigindan (heap) yer alir; 2 KB SRAM'de yigin ile yigit (stack)
 * birbirine girip sessiz cokmelere yol acar. Sabit tampon bu riski kaldirir.
 */
char komut[16];
uint8_t komut_uzunluk = 0;

void komut_isle() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (komut_uzunluk == 0) continue;
      komut[komut_uzunluk] = '\0';
      komut_calistir();
      komut_uzunluk = 0;
    } else if (komut_uzunluk < sizeof(komut) - 1) {
      komut[komut_uzunluk++] = c;
    }
  }
}

void komut_calistir() {
  char c = komut[0];
  if (c == 'o') { akis = !akis; }
  else if (c == 's') { akim_sifirla(); }
  else if (c == 'e') { enerji_pJ = 0; Serial.println(F("Enerji sifirlandi")); }
  else if (c == 'd') { ayarlari_goster(); }
  else if (c == 'y') { yardim(); }
  else if (c == 'r') {
    float r = atof(komut + 1);
    if (r > 0) {
      ayar.sont_ohm = r;
      ayar_kaydet();
      Serial.print(F("Sont = ")); Serial.println(r, 4);
    }
  }
  else if (c == 'h') {
    long ms = atol(komut + 1);
    if (ms >= 20 && ms <= 5000) {
      rapor_ms = (uint16_t)ms;
      Serial.print(F("Rapor araligi = ")); Serial.print(rapor_ms);
      Serial.println(F(" ms"));
    } else {
      Serial.println(F("! 20-5000 ms arasi olmali"));
    }
  }
  else if (c == 'k' && komut_uzunluk > 2) {
    float d = atof(komut + 2);
    if (komut[1] == 'v') kalibre_gerilim(d);
    else if (komut[1] == 'a') kalibre_akim(d);
  }
  else if (c == 't') {
    /*
     * Eşik komuttan geliyor: 't' tetiklemesiz, 't128' yükselen kenarda.
     *
     * Önceden çağrı `osiloskop_yakala(0, 0)` diye SABİTTİ. Derleyici
     * `esik == 0` olduğunu görüp tetikleme arayan ~25 satırı ve
     * "! tetiklenemedi" dalını komple attı: yazılmış ama hiç çalışmayan
     * kod. S9 ikilideki metinleri arayınca ortaya çıktı.
     */
    uint8_t esik = (uint8_t)atoi(komut + 1);
    if (osiloskop_yakala(0, esik)) {
      // Başlık:  S <örnek sayısı> <örnekleme Hz> <volt / adım>
      // Ardından ham 8-bit değerler. 8 bit -> 10 bit ölçek için ×4.
      Serial.print(F("S "));
      Serial.print(TAMPON);            Serial.print(' ');
      Serial.print(76923UL);           Serial.print(' ');
      Serial.println(4 * v_adim, 6);
      for (uint16_t i = 0; i < TAMPON; i++) {
        Serial.print(tampon[i]);
        Serial.print(i % 32 == 31 ? '\n' : ' ');
      }
      Serial.println();
    } else {
      Serial.println(F("! tetiklenemedi"));
    }
  }
  else {
    Serial.println(F("? bilinmeyen komut — 'y' yardim"));
  }
}

/*
 * Rapor arası ORTALAMA.
 *
 * Döngü ~4500 tur/sn dönüyor; rapor 5 Hz. Aradaki ~900 örneği atmak yerine
 * hepsinin ortalamasını alıyoruz. Beyaz gürültü √900 = 30 kat bastırılıyor.
 *
 * Pencere uzunluğunun ayrı bir faydası var: 200 ms tam 10 şebeke çevrimi
 * (50 Hz) ve tam 12 çevrim (60 Hz). Tam katı olduğu için şebeke uğultusu
 * ortalamada sıfırlanıyor — havada duran ölçüm kablosunun topladığı 50 Hz
 * bu sayede kayboluyor.
 */
uint32_t ornek = 0;
float v_top = 0, i_top = 0, w_top = 0;

void loop() {
  if (Serial.available()) komut_isle();

  Okuma o = olc();
  enerji_biriktir(o.watt);

  v_top += o.volt;
  i_top += o.amper;
  w_top += o.watt;
  ornek++;

  if (akis && millis() - son_rapor >= rapor_ms) {
    son_rapor = millis();
    uint32_t n = ornek ? ornek : 1;
    // Makine biçimi — arayüz bunu ayrıştırıyor. Alan sırası:
    //   D <volt> <amper> <watt> <joule> <wh> <ms> <örnek>
    Serial.print(F("D "));
    Serial.print(v_top / n, 4);      Serial.print(' ');
    Serial.print(i_top / n, 6);      Serial.print(' ');
    Serial.print(w_top / n, 6);      Serial.print(' ');
    Serial.print(enerji_joule(), 4); Serial.print(' ');
    Serial.print(enerji_wh(), 7);    Serial.print(' ');
    Serial.print(son_rapor);         Serial.print(' ');
    Serial.println(n);
    v_top = i_top = w_top = 0;
    ornek = 0;
  }
}
