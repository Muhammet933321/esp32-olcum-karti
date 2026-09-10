# -*- coding: utf-8 -*-
"""A1 — Asama 2 tasarimi: ESP32-S3 + ADS1115.

Bu betik TASARIM BELGESIDIR ve ayni zamanda BIR TESTTIR. Her sayi burada
hesaplanir; hicbiri elle yazilmaz. Tasarim kurallari `kural()` ile
sinanir, ihlal varsa cikis kodu 1 olur.

Kaynaklar:
  ADS1115  — TI SBAS444 veri sayfasi
  ESP32-S3 — Espressif veri sayfasi + ESP-IDF ADC belgeleri
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hedef2                                       # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════ sabitler (veri sayfasi)
VDD = 3.3                 # ADS1115 ve ESP32-S3 ortak besleme
ADS_GIRIS_TAVAN = VDD     # veri sayfasi: analog giris GND-0.3 .. VDD+0.3
ADS_SAYIM = 32768         # 16 bit isaretli, tek yon
ADS_OFSET_LSB = 3         # veri sayfasi: ofset hatasi +-3 LSB
ADS_KAZANC_HATA = 0.0015  # veri sayfasi: kazanc hatasi +-%0.15 (maks)
ADS_SPS = 860             # en yuksek veri hizi

PGA = {4.096: 125e-6, 2.048: 62.5e-6, 1.024: 31.25e-6,
       0.512: 15.625e-6, 0.256: 7.8125e-6}

ESP_ADC_BIT = 12
ESP_ADC_SPS = 83333       # ESP-IDF: SOC_ADC_SAMPLE_FREQ_THRES_HIGH
ESP_ADC_TAVAN = 3.1       # 12 dB zayiflatmada kullanilabilir ust sinir
ESP_PIN_MUTLAK = 3.6      # GPIO mutlak azami

# --- bolucu (Asama 1'den aynen, stokta var ve SPICE ile dogrulanmis)
R_UST, R_ALT = 100e3, 6.8e3
ORAN = (R_UST + R_ALT) / R_ALT
THEVENIN = R_UST * R_ALT / (R_UST + R_ALT)
C_SUZGEC = 1e-9

# --- TL431 kelepce rayi (Asama 1'de referanstı, simdi koruma)
TL431_V = 2.495
DIYOT_VF = 0.7            # 1N4148, ~1 mA'de

# --- sontler (stok + siparis)
SONTLAR = [
    ("uA",  10.0,   0.25, "10R  x1        (stokta 30 adet)"),
    ("mA",   1.0,   0.25, "1R   1/4W      (siparis 50 adet)"),
    ("A",    0.1,   5.00, "0R1  5W tas    (siparis 3 adet)"),
    ("10A",  0.015, 2.00, "15mR Type-C    (siparis 3 adet)"),
]

LEHIM_DIRENC = 1e-3       # tek lehim noktasi, tipik
TERMO_EMK = 3e-6          # bakir-alasim birlesimi, en kotu (V)

gecti = kaldi = 0


def baslik(s):
    print()
    print("=" * 78)
    print(f"  {s}")
    print("=" * 78)


def kural(ad, tamam, ek=""):
    global gecti, kaldi
    if tamam:
        gecti += 1
    else:
        kaldi += 1
    print(f"  {'[OK]' if tamam else '[!!]'} {ad}" + (f"   {ek}" if ek else ""))


def bilgi(s=""):
    print(s)


# ═══════════════════════════════════════════════════════════ 1. BESLEME
baslik("1. BESLEME VE MANTIK SEVIYELERI")
bilgi(f"  ESP32-S3 kart uzerinde 3.3 V uretiyor; ADS1115 de 3.3 V'ta calisiyor.")
bilgi()
vih_ads = 0.7 * VDD
bilgi(f"  ADS1115 VIH = 0.7 x VDD = {vih_ads:.2f} V,  ESP32 cikis yuksek = 3.3 V")
kural("I2C seviyeleri uyumlu (ayni 3.3 V)", 3.3 >= vih_ads,
      f"3.30 V >= {vih_ads:.2f} V")
bilgi()
bilgi("  NEDEN 5 V DEGIL: ADS1115'i 5 V'ta besleseydik VIH = 3.50 V olurdu;")
bilgi("  ESP32'nin 3.3 V'luk yuksek seviyesi bunu KARSILAMAZDI. Seviye")
bilgi("  cevirici gerekirdi. 3.3 V'ta besleyerek o parcayi tamamen siliyoruz.")
bilgi()
bilgi(f"  BEDELI: analog giris {ADS_GIRIS_TAVAN} V ile sinirli. PGA +-4.096 V")
bilgi(f"  secilse bile aralaigin sadece %{ADS_GIRIS_TAVAN/4.096*100:.0f}'i")
bilgi(f"  ({round(ADS_GIRIS_TAVAN/4.096*ADS_SAYIM):,} sayim) kullanilabiliyor.".replace(",", " "))


# ═══════════════════════════════════════════════════ 2. GERILIM KANALI
baslik("2. GERILIM KANALI  (ADS #2, AIN0 tekli)")
bilgi(f"  Bolucu {R_UST/1e3:.0f}K / {R_ALT/1e3:.1f}K  ->  oran {ORAN:.3f}")
bilgi("  (A2 SPICE taramasi bu orani secti — gerekce asagida)")
bilgi(f"  Thevenin direnci {THEVENIN/1e3:.2f} kohm, dugum kondansatoru "
      f"{C_SUZGEC*1e9:.0f} nF")
fc = 1 / (2 * 3.141592653589793 * THEVENIN * C_SUZGEC)
bilgi(f"  Kesim frekansi {fc/1e3:.1f} kHz")
bilgi()

# kelepce: dugum TL431 rayina 1N4148 ile baglanir
kelepce_v = TL431_V + DIYOT_VF
giris_kelepce = kelepce_v * ORAN
bilgi(f"  KELEPCE: dugum -> 1N4148 -> TL431 rayi ({TL431_V} V)")
bilgi(f"  Dugum en fazla {kelepce_v:.3f} V'a cikabilir "
      f"(girise vurulursa {giris_kelepce:.1f} V)")
kural("Kelepce ADS1115 mutlak azamisinin altinda",
      kelepce_v < VDD + 0.3, f"{kelepce_v:.3f} V < {VDD+0.3:.1f} V")
bilgi()
bilgi("  NEDEN TL431, neden 3.3 V rayina degil:")
bilgi(f"    3.3 V rayina 1N4148 ile kelepcelenseydi dugum "
      f"{3.3+DIYOT_VF:.1f} V'a cikardi.")
bilgi(f"    ADS1115 mutlak azamisi {VDD+0.3:.1f} V — {3.3+DIYOT_VF-(VDD+0.3):.1f} V")
bilgi("    asardi. TL431 rayi 0.8 V daha alcak oldugu icin pay birakiyor.")
bilgi()

# --- PGA merdiveni: giris tavanini asmayan en kucuk kademe secilir
bilgi("  PGA merdiveni (yazilimdan secilir, donanim degismez):")
bilgi()
bilgi(f"    {'PGA':>10} {'tam olcek':>11} {'adim':>10} {'12 V hatasi':>13}")
bilgi("    " + "-" * 48)
v_kademe = []
for pga, lsb in PGA.items():
    tavan = min(pga, ADS_GIRIS_TAVAN)
    tam = tavan * ORAN
    adim = lsb * ORAN
    ofset = ADS_OFSET_LSB * adim
    hata12 = (ofset + adim / 2) / 12 * 100 if tam >= 12 else float("nan")
    v_kademe.append((pga, tam, adim, ofset))
    h = f"%{hata12:.3f}" if tam >= 12 else "  —"
    bilgi(f"    +-{pga:6.3f} {tam:9.2f} V {adim*1e6:8.1f} uV {h:>13}")

# SECILEN CALISMA KADEMESI: PGA +-2.048 V
# Sebep (A2): dugum 2.048 V'da kalinca TL431 kelepcesi tum menzil
# boyunca ters kutuplu olur, sizinti sifirlanir.
SECILEN_PGA = 2.048
v_tam = next(t for p_, t, a_, o_ in v_kademe if p_ == SECILEN_PGA)
v_adim = next(a_ for p_, t, a_, o_ in v_kademe if p_ == SECILEN_PGA)
bilgi()
kural("Gerilim tam olcegi Asama 1'i (27.14 V) asiyor", v_tam > 27.14,
      f"{v_tam:.2f} V")
kural("Gerilim adimi Asama 1'den (26.53 mV) ince", v_adim * 1000 < 26.53,
      f"{v_adim*1000:.3f} mV")
kural("Kelepce olcum araligini kisitlamiyor", giris_kelepce > v_tam * 0.85,
      f"kelepce {giris_kelepce:.1f} V vs tam olcek {v_tam:.1f} V")


# ═══════════════════════════════════════════════════════ 3. AKIM KANALI
baslik("3. AKIM KANALI  (ADS #1, AIN0-AIN1 DIFERANSIYEL, alcak taraf)")
pga_i = 0.256
lsb_i = PGA[pga_i]
bilgi(f"  PGA +-{pga_i} V sabit, adim {lsb_i*1e6:.4f} uV")
bilgi(f"  Diferansiyel giris: sontun iki ucu dogrudan okunuyor, "
      f"ortak uc sorunu yok.")
bilgi()
bilgi(f"  {'kademe':>7} {'sont':>9} {'tam olcek':>11} {'adim':>10} "
      f"{'FS gerilim':>11} {'FS guc':>9} {'lehim hatasi':>13}")
bilgi("  " + "-" * 76)
kademeler = []
for ad, r, w, not_ in SONTLAR:
    i_aralik = pga_i / r
    i_guc = (w / r) ** 0.5
    i_fs = min(i_aralik, i_guc)
    adim_i = lsb_i / r
    lehim = LEHIM_DIRENC / r * 100
    kademeler.append((ad, r, i_fs, adim_i, lehim, not_))
    bilgi(f"  {ad:>7} {r:9.4f} {i_fs:9.3f} A {adim_i*1e6:8.2f} uA "
          f"{i_fs*r*1000:9.1f} mV {i_fs**2*r:7.2f} W  %{lehim:10.2f}")

bilgi()
kural("En hassas kademe Asama 1'den (30.5 uA) ince",
      kademeler[0][3] * 1e6 < 30.5, f"{kademeler[0][3]*1e6:.2f} uA")
kural("En yuksek kademe Asama 1'i (31 mA) asiyor",
      kademeler[-1][2] > 0.031, f"{kademeler[-1][2]:.2f} A")

bilgi()
bilgi("  KUSUR ve DOGRU GEREKCE:")
bilgi("  Lehim direnci SABIT oldugu icin statik hatasi kalibrasyonla silinir.")
bilgi("  Kelvin'in asil gerekcesi bu degil, su iki sey:")
bilgi()
TCR_BAKIR = 3900e-6       # bakir sicaklik katsayisi, 1/C
RTH_EKLEM = 100.0         # kucuk lehim ekleminin isil direnci, C/W (temkinli)
TCR_ALASIM = 75e-6        # Type-C / Manganin alasimi, 1/C
RTH_SONT = 20.0           # C/W

bilgi(f"  (a) YUKE BAGLI SURUKLENME — eklem akimla isinir, direnci degisir:")
bilgi(f"      {'akim':>6} {'eklem P':>9} {'dT':>7} {'dR':>9} "
      f"{'15 mohm''da hata':>16}")
bilgi("      " + "-" * 52)
surukleme = {}
for akim in (1, 2, 5, 10):
    p = akim * akim * LEHIM_DIRENC
    dt = p * RTH_EKLEM
    dr = LEHIM_DIRENC * TCR_BAKIR * dt
    surukleme[akim] = dr / 0.015 * 100
    bilgi(f"      {akim:5.0f} A {p*1000:7.1f} mW {dt:6.1f} C {dr*1e6:7.1f} uohm "
          f"{dr/0.015*100:15.3f}%")
bilgi()
bilgi(f"  (b) 10 A KALIBRASYON KAYNAGI GEREKTIRMEZ — Kelvin olmadan kademeyi")
bilgi(f"      kullanmak icin elinde 10 A veren ve olcen bir referans olmali.")
bilgi(f"      Kelvin ile sontun kendi %1 toleransi yeterli, kalibrasyon sart degil.")
bilgi()
bilgi(f"  Kelvin'in COZMEDIGI: sontun kendi isinmasi (alasim TCR {TCR_ALASIM*1e6:.0f} ppm/C)")
for akim in (1, 5, 10):
    p = akim * akim * 0.015
    dt = p * RTH_SONT
    bilgi(f"      {akim:4.0f} A: {p:5.2f} W -> dT {dt:5.1f} C -> "
          f"%{TCR_ALASIM*dt*100:.3f} degisim  (kacinilmaz)")
kelvin_gerekli = [k for k in kademeler if k[4] > 1.0]
kural("Kelvin gerektiren kademeler tespit edildi ve semada ayri izle cizilecek",
      len(kelvin_gerekli) > 0, f"{len(kelvin_gerekli)} kademe")
kural("Kelvinsiz yuke bagli suruklenme 10 A'de %0.1'i asiyor",
      surukleme[10] > 0.1, f"%{surukleme[10]:.3f} — kalibrasyon bunu silemez")

bilgi()
bilgi("  Termo-emk (bakir/alasim birlesimi, en kotu 3 uV):")
for ad, r, i_fs, adim_i, lehim, not_ in kademeler:
    esdeger = TERMO_EMK / r
    bilgi(f"    {ad:>5}: {esdeger*1e6:8.1f} uA esdeger  "
          f"(tam olcegin %{esdeger/i_fs*100:.4f}'i)")


# ═══════════════════════════════ 4. AKIM SUZGECI (diferansiyel RC)
baslik("4. AKIM GIRISI ORTUSME SUZGECI")
R_SUZ = 100.0             # her bacakta, stokta 30 adet var
C_DIF = 100e-9
fc_dif = 1 / (2 * 3.141592653589793 * 2 * R_SUZ * C_DIF)
# ADS1115 diferansiyel giris direnci PGA +-0.256 V'ta ~710 kohm
Z_ADS = 710e3
kazanc_hatasi = 2 * R_SUZ / Z_ADS * 100
bilgi(f"  Her bacakta {R_SUZ:.0f} ohm, aralarinda {C_DIF*1e9:.0f} nF")
bilgi(f"  Diferansiyel kesim {fc_dif/1e3:.2f} kHz")
bilgi(f"  ADS1115 giris direnci (PGA +-0.256 V) ~{Z_ADS/1e3:.0f} kohm")
kural("Seri direncin yarattigi kazanc hatasi < %0.1",
      kazanc_hatasi < 0.1, f"%{kazanc_hatasi:.4f}")
kural("Kesim frekansi anahtarlama gurultusunun (100 kHz) altinda",
      fc_dif < 100e3, f"{fc_dif/1e3:.1f} kHz")


# ═══════════════════════════════════════════════════ 5. OSILOSKOP KANALI
baslik("5. OSILOSKOP KANALI  (ESP32-S3 ADC1_CH3 / GPIO4)")
skop_tam = ESP_ADC_TAVAN * ORAN
skop_adim = ESP_ADC_TAVAN / (2 ** ESP_ADC_BIT) * ORAN
bilgi(f"  AYRI giris, ayri bolucu — voltmetreyle ayni dugum DEGIL.")
bilgi(f"  Bolucu yine {ORAN:.0f}:1, ESP32 ADC ust siniri {ESP_ADC_TAVAN} V")
bilgi(f"  Tam olcek {skop_tam:.1f} V, adim {skop_adim*1000:.1f} mV "
      f"({ESP_ADC_BIT} bit)")
bilgi(f"  Ornekleme {ESP_ADC_SPS:,} Sa/s".replace(",", " "))
nyquist = ESP_ADC_SPS / 2
bilgi(f"  Nyquist {nyquist/1e3:.1f} kHz, ortusme suzgeci kesimi {fc/1e3:.1f} kHz")
bilgi()
kural("Kelepce ESP32 GPIO mutlak azamisinin altinda",
      kelepce_v < ESP_PIN_MUTLAK, f"{kelepce_v:.3f} V < {ESP_PIN_MUTLAK} V")
kural("Ornekleme Asama 1'i (76 923 Sa/s) asiyor", ESP_ADC_SPS > 76923,
      f"{ESP_ADC_SPS:,} Sa/s".replace(",", " "))
kural("Cozunurluk Asama 1'i (8 bit) asiyor", ESP_ADC_BIT > 8,
      f"{ESP_ADC_BIT} bit")
kural("Ortusme suzgeci Nyquist'in altinda", fc < nyquist,
      f"{fc/1e3:.1f} kHz < {nyquist/1e3:.1f} kHz")
bilgi()
bilgi("  UYARI: ESP32-S3 ADC'si dogrusal DEGILDIR. Bu kanal dalga SEKLI icin;")
bilgi("  sayisal deger her zaman ADS1115'ten okunmali.")


# ═══════════════════════════════════════════ 6. ORNEKLEME VE GURULTU
baslik("6. ORNEKLEME VE GURULTU TABANI")
PENCERE = 0.200
bilgi(f"  Iki ayri ADS1115 kullaniliyor: biri akim, biri gerilim.")
bilgi(f"  Ikisi de SUREKLI kipte {ADS_SPS} SPS -> kanal basina {ADS_SPS} ornek/s")
bilgi(f"  V ve I ES ZAMANLI orneklendigi icin P = V x I carpimi dogru.")
bilgi()
bilgi(f"  (Tek ADS1115 ile kanal degistirseydik {ADS_SPS//2} cift/s olurdu ve")
bilgi(f"   V ile I arasinda {1000/ADS_SPS:.2f} ms gecikme kalirdi.)")
bilgi()
n = ADS_SPS * PENCERE
bastirma = n ** 0.5
bilgi(f"  {PENCERE*1000:.0f} ms pencere = {n:.0f} ornek -> sqrt(N) = {bastirma:.1f}x")
bilgi(f"  {PENCERE*1000:.0f} ms tam 10 sebeke cevrimi (50 Hz) -> ugultu sifirlanir")
bilgi()
for ad, r, i_fs, adim_i, lehim, not_ in kademeler:
    bilgi(f"    {ad:>5} kademesi gurultu tabani: "
          f"{adim_i*1e6/bastirma:8.4f} uA")
uno_taban = 30.49 / (344 ** 0.5)
yeni_taban = kademeler[0][3] * 1e6 / bastirma
bilgi()
kural("Gurultu tabani Asama 1'den (1.644 uA) iyi", yeni_taban < 1.644,
      f"{yeni_taban:.4f} uA ({uno_taban/yeni_taban:.0f} kat)")
kural("DC ornekleme Asama 1'in yarisina dustu (bilinen odun)",
      ADS_SPS < 1720, f"{ADS_SPS} < 1720 ornek/s — gurultu tabani yine de iyi")


# ═══════════════════════════════════════════════════════ 7. HATA BUTCESI
baslik("7. HATA BUTCESI  (kalibrasyon SONRASI, 25 C)")
bilgi("  Kalibrasyonla silinenler: ADS kazanc hatasi (%0.15), direnc")
bilgi("  toleransi (%1), sont toleransi. Geriye kalanlar:")
bilgi()


def butce(ad, birim, adim, ofset_lsb, olcum, ek=()):
    kuantalama = adim / 2
    ofset = ofset_lsb * adim
    kalemler = [("kuantalama +-0.5 LSB", kuantalama), ("ADS ofseti +-3 LSB", ofset)]
    kalemler += list(ek)
    toplam = sum(v for _, v in kalemler)
    bilgi(f"  {ad}  ({olcum}{birim} olcerken)")
    for k, v in kalemler:
        bilgi(f"      {k:<34} {v*1e6:10.2f} u{birim}  %{v/olcum*100:7.4f}")
    bilgi(f"      {'TOPLAM (en kotu hal)':<34} {toplam*1e6:10.2f} u{birim}  "
          f"%{toplam/olcum*100:7.4f}")
    bilgi()
    return toplam / olcum


h_v = butce(f"GERILIM (PGA +-{SECILEN_PGA}, SECILEN)", "V", v_adim,
            ADS_OFSET_LSB, 12.0)
h_v2 = butce("GERILIM (PGA +-0.512, kucuk gerilim)", "V",
             v_kademe[3][2], ADS_OFSET_LSB, 3.3)
h_i = butce("AKIM (1 ohm sont)", "A", kademeler[1][3], ADS_OFSET_LSB, 0.100,
            ek=[("termo-emk", TERMO_EMK / 1.0),
                ("lehim direnci (1 mohm)", 0.100 * LEHIM_DIRENC / 1.0)])
h_i2 = butce("AKIM (15 mohm, KELVINSIZ, KALIBRESIZ)", "A",
             kademeler[3][3], ADS_OFSET_LSB, 10.0,
             ek=[("termo-emk", TERMO_EMK / 0.015),
                 ("lehim direnci — statik", 10.0 * LEHIM_DIRENC / 0.015)])
h_i2b = butce("AKIM (15 mohm, KELVINSIZ ama 10 A'de KALIBRE)", "A",
              kademeler[3][3], ADS_OFSET_LSB, 10.0,
              ek=[("termo-emk", TERMO_EMK / 0.015),
                  ("eklem yuke bagli suruklenme", 10.0 * surukleme[10] / 100),
                  ("sont oz-isinmasi", 10.0 * TCR_ALASIM * 10.0**2 * 0.015 * RTH_SONT)])
h_i3 = butce("AKIM (15 mohm, KELVIN ile, kalibrasyonsuz)", "A",
             kademeler[3][3], ADS_OFSET_LSB, 10.0,
             ek=[("termo-emk", TERMO_EMK / 0.015),
                 ("sont toleransi %1 (etiket degeri)", 10.0 * 0.01),
                 ("sont oz-isinmasi", 10.0 * TCR_ALASIM * 10.0**2 * 0.015 * RTH_SONT)])

kural("12 V olcumunde hata < %0.1", h_v * 100 < 0.1, f"%{h_v*100:.4f}")
kural("100 mA olcumunde hata < %0.2", h_i * 100 < 0.2, f"%{h_i*100:.4f}")
kural("15 mohm KELVINSIZ+KALIBRESIZ kabul edilemez (kusur dogrulandi)",
      h_i2 * 100 > 1.0, f"%{h_i2*100:.2f}")
kural("Kalibrasyon statik kismi siliyor ama tamamini degil",
      0.1 < h_i2b * 100 < 1.0, f"%{h_i2b*100:.3f} — yuke bagli kalan")
kural("KELVIN ile kalibrasyonsuz bile %1.5'in altinda",
      h_i3 * 100 < 1.5, f"%{h_i3*100:.3f} (sontun kendi %1 toleransi baskin)")


# ═══════════════════════════════════════════════════════ 8. BAGLANTI PLANI
baslik("8. I2C VE PIN PLANI")
bilgi("  ADS1115 adresleri (ADDR pini):")
for ad, adres, gorev in (("ADS #1", "0x48  ADDR->GND", "AKIM   AIN0-AIN1 diferansiyel"),
                         ("ADS #2", "0x49  ADDR->VDD", "GERILIM AIN0 tekli"),
                         ("ADS #3", "0x4A  ADDR->SDA", "yedek / 2. kanal (verim)")):
    bilgi(f"    {ad}  {adres:<16} {gorev}")
bilgi()
bilgi("  ESP32-S3 pinleri:")
for pin, gorev in (("GPIO8",  "I2C SDA  (4.7K pull-up -> 3.3 V)"),
                   ("GPIO9",  "I2C SCL  (4.7K pull-up -> 3.3 V)"),
                   ("GPIO4",  "ADC1_CH3 — osiloskop girisi"),
                   ("GPIO5",  "ADC1_CH4 — osiloskop 2. kanal (yedek)"),
                   ("GPIO7",  "ADS #1 ALERT/RDY (donusum hazir kesmesi)")):
    bilgi(f"    {pin:<8} {gorev}")
bilgi()
bilgi("  KACINILAN PINLER (N16R8 varyantinda kullanilamaz):")
bilgi("    GPIO0, GPIO3, GPIO45, GPIO46 — strapping")
bilgi("    GPIO19, GPIO20              — yerel USB D-/D+")
bilgi("    GPIO26..GPIO32              — SPI flash")
bilgi("    GPIO33..GPIO37              — oktal PSRAM (R8 varyanti)")
kural("Secilen ADC pinleri ADC1'de (WiFi ile cakismaz)",
      all(1 <= p <= 10 for p in (4, 5)), "GPIO4, GPIO5 -> ADC1_CH3, CH4")
kural("Secilen pinlerin hicbiri yasakli listede degil",
      not ({8, 9, 4, 5, 7} & {0, 3, 45, 46, 19, 20} | ({8, 9, 4, 5, 7} & set(range(26, 38)))),
      "cakisma yok")


# ═══════════════════════════════════════════════════════ 9. ON PANEL
baslik("9. ON PANEL — 5 UC CIFTI")
bilgi(f"  {'uc':<12} {'baglanti':<14} {'menzil':<22} {'konnektor'}")
bilgi("  " + "-" * 74)
for uc, bag, menzil, kon in (
        ("V",     "yuke PARALEL", f"0 - {v_tam:.1f} V", "muz jak kirmizi+siyah"),
        ("uA/mA", "yuke SERI",    f"0 - {kademeler[1][2]*1000:.0f} mA", "muz jak sari+siyah"),
        ("A",     "yuke SERI",    f"0 - {kademeler[2][2]:.2f} A", "muz jak mavi+siyah"),
        ("10A",   "yuke SERI",    f"0 - {kademeler[3][2]:.1f} A", "vidali klemens"),
        ("SCOPE", "gezici prob",  f"0 - {skop_tam:.1f} V", "muz jak yesil+siyah")):
    bilgi(f"  {uc:<12} {bag:<14} {menzil:<22} {kon}")
bilgi()
bilgi("  Akim kademeleri AYRI UC — anahtarla secilmez.")
bilgi(f"  Sebep: 20 mohm'luk bir anahtar kontagi 15 mohm sontun "
      f"{0.020/0.015:.1f} katidir.")
bilgi("  Gerilim kademesi ise yazilimdan (PGA), orada anahtar yok.")


# ═══════════════════════════════════════ 8b. I2C PULL-UP (DEVIR 4.7)
baslik("8b. I2C PULL-UP — R8/R9 DEGERI")
bilgi("  Her ADS1115 modulunde kart ustu 10K pull-up var; modulleri veri")
bilgi("  yoluna ekledikce paralel direnc DUSER (yukselme hizlanir).")
bilgi("  Fast-mode (400 kHz) siniri: t_r <= 300 ns,  t_r = 0.8473 x R x C")
bilgi()
I2C_C = 150e-12           # delikli plaket + kisa tel, temkinli
I2C_K = 0.8473            # 0.3->0.7 VDD RC yukselmesi: ln(7/3)
I2C_TR_SINIR = 300e-9     # NXP UM10204 Fast-mode
I2C_SINK_SINIR = 3e-3     # ADS1115/ESP32 VOL akimi
MODUL_PULLUP = 10e3


def _par(*r):
    return 1.0 / sum(1.0 / x for x in r)


def _tr(r):
    return I2C_K * r * I2C_C


r_azami = I2C_TR_SINIR / (I2C_K * I2C_C)
bilgi(f"  300 ns'e izin veren azami toplam pull-up: {r_azami:.0f} ohm")
bilgi()
bilgi(f"    {'modul':>6} {'R8/R9':>7} {'toplam':>9} {'t_r':>9} {'sink':>8}  sonuc")
bilgi("    " + "-" * 52)
secim = {}
for n_modul in (2, 3):
    taban = _par(*([MODUL_PULLUP] * n_modul))
    for rp in (None, 4.7e3, 2.7e3):
        toplam = taban if rp is None else _par(taban, rp)
        t = _tr(toplam)
        sink = VDD / toplam
        secim[(n_modul, rp)] = (toplam, t, sink)
        etiket = "yok" if rp is None else f"{rp/1e3:.1f}K"
        sonuc = "gecer" if t <= I2C_TR_SINIR and sink <= I2C_SINK_SINIR else "KALIR"
        bilgi(f"    {n_modul:>6} {etiket:>7} {toplam:8.0f}o {t*1e9:8.1f}n "
              f"{sink*1e3:7.2f}m  {sonuc}")
bilgi()
bilgi("  KUSUR (DEVIR 4.7 / kurulum2.html): belge 'R8/R9 = 4.7K tak, 308 ns,")
bilgi("  gecer' diyordu. 308 ns kendi verdigi 300 ns sinirinin USTUNDE — iki")
bilgi("  modullu yapilandirmada KALIYOR. 2.7K (stokta 10 adet) her iki modul")
bilgi("  sayisinda da geciyor, secilen bu.")
kural("2 modul + 4.7K Fast-mode'da KALIYOR (belgedeki iddia yanlisti)",
      secim[(2, 4.7e3)][1] > I2C_TR_SINIR,
      f"{secim[(2, 4.7e3)][1]*1e9:.1f} ns > 300 ns")
kural("2 modul + 2.7K geciyor", secim[(2, 2.7e3)][1] <= I2C_TR_SINIR,
      f"{secim[(2, 2.7e3)][1]*1e9:.1f} ns")
kural("3 modul + 2.7K geciyor", secim[(3, 2.7e3)][1] <= I2C_TR_SINIR,
      f"{secim[(3, 2.7e3)][1]*1e9:.1f} ns")
kural("2.7K'da sink akimi 3 mA sinirinin altinda (her iki durumda)",
      max(secim[(2, 2.7e3)][2], secim[(3, 2.7e3)][2]) <= I2C_SINK_SINIR,
      f"en kotu {max(secim[(2, 2.7e3)][2], secim[(3, 2.7e3)][2])*1e3:.2f} mA")
bilgi()
bilgi("  100 kHz'e DUSMEK BEDAVA DEGIL — DEVIR 4.7 'ornekleme hizini")
bilgi("  etkilemez' diyor, veri yolu doluluguna bakilinca oyle degil:")
bilgi()
# ads_oku(): [S adr+W ptr P] + [S adr+R hi lo P] ~ 49 bit suresi
I2C_BIT = 49
okuma_hz = ADS_SPS * 2        # iki ADS, her biri 860 SPS
for hiz in (400e3, 100e3):
    sure = I2C_BIT / hiz
    doluluk = okuma_hz * sure
    bilgi(f"    {hiz/1e3:.0f} kHz: okuma basina {sure*1e6:6.1f} us x "
          f"{okuma_hz} okuma/s = %{doluluk*100:.0f} veri yolu dolulugu")
kural("400 kHz'te veri yolu dolulugu %50'nin altinda",
      okuma_hz * I2C_BIT / 400e3 < 0.5,
      f"%{okuma_hz * I2C_BIT / 400e3 * 100:.0f}")
kural("100 kHz yedek yolu BEDAVA DEGIL — doluluk %80'i asiyor",
      okuma_hz * I2C_BIT / 100e3 > 0.8,
      f"%{okuma_hz * I2C_BIT / 100e3 * 100:.0f} — son care, ilk secenek degil")
bilgi()
bilgi("  IYILESTIRME (uygulanmadi): ADS1115 yazmac isaretcisini KORUR.")
bilgi("  Ilk okumadan sonra isaretci yazmayi atlayip dogrudan 2 bayt")
bilgi(f"  istenirse islem {I2C_BIT} bit yerine ~29 bit olur (-%41).")


# ═══════════════════════════════════════════ 9. DERLEME HEDEFI (DEVIR 4.9)
baslik("9. DERLEME HEDEFI — PSRAM")
bilgi("  KUSUR: FQBN duz 'esp32:esp32:esp32s3' idi. Kartin PSRAM varsayilani")
bilgi("  'disabled' oldugu icin ps_malloc() SESSIZCE NULL doner ve derin skop")
bilgi("  bellegi hic ayrilamaz — hata mesaji da olmaz.")
bilgi()
sec = hedef2.secenek_sozlugu()
bilgi(f"  FQBN: {hedef2.FQBN}")
bilgi()
for anahtar, deger in sec.items():
    bilgi(f"    {anahtar:<16} {deger}")
bilgi()
kural("PSRAM acik (N16R8 = 8 MB oktal)", sec.get("PSRAM") == "opi",
      f"PSRAM={sec.get('PSRAM')}")
kural("Flash boyutu N16R8'in gercek boyutu", sec.get("FlashSize") == "16M",
      f"FlashSize={sec.get('FlashSize')} (varsayilan 4M yanlisti)")
kural("Uygulama bolumu 473 KB'lik firmware icin genis",
      sec.get("PartitionScheme") == "huge_app", "huge_app = 3 MB")
bilgi()
bilgi("  BU KURAL NEYI KANITLAMAZ: kartta gercekten PSRAM oldugunu. Derleme")
bilgi("  secenegi yalnizca surucuyu derler. Kanit, firmware'in acilista")
bilgi("  yazdigi 'PSRAM: 8192 KB' satiridir — tezgahta ONA bak.")


# ═══════════════════════════════════════════════════════════════ OZET
baslik("OZET")
print(f"  {gecti}/{gecti + kaldi} tasarim kurali gecti")
print()
print("  BULUNAN KUSURLAR ve COZUMLERI:")
print("   1. ADS1115 girisi VDD ile sinirli -> tam olcek 45 V degil, "
      f"{v_tam:.1f} V.")
print("      Cozum: kabul edildi; yine de Asama 1'in 27.1 V'undan genis.")
print("   2. 3.3 V rayina kelepce ADS/ESP mutlak azamisini asiyor.")
print("      Cozum: TL431 rayina (2.495 V) kelepce -> dugum en fazla "
      f"{kelepce_v:.2f} V.")
print("   3. 15 mohm ve altinda lehim direnci baskin hata "
      f"(%{kademeler[3][4]:.1f}).")
print("      Cozum: Kelvin (4 telli) baglanti — semada ayri algilama izi.")
print("   4. DC ornekleme 1720 -> 860 ornek/s dustu.")
print("      Cozum gerekmez: gurultu tabani yine de "
      f"{uno_taban/yeni_taban:.0f} kat iyi.")
print("   5. ESP32-S3 ADC'si dogrusal degil.")
print("      Cozum: yalnizca dalga sekli icin; sayisal deger ADS1115'ten.")
raise SystemExit(0 if kaldi == 0 else 1)
