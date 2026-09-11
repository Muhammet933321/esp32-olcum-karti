# -*- coding: utf-8 -*-
"""Olcum Karti — Asama 3 semasini uretir (CIFT YONLU on uc, +-615 V).

Yedi blok:
  1. TL431 rayi (2.495 V) + Vref bolucu (10K/22K) + Vref TAMPONU
  2. NORMAL gerilim  220K / 6.8K   -> Vref -> RC -> tampon -> ADS #2 AIN0
  3. YUKSEK gerilim  6x820K/8.2K  -> Vref -> RC -> tampon -> ADS #2 AIN2
  4. Akim  sont + KELVIN + diferansiyel RC -> ADS #1 AIN0/AIN1
  5. Osiloskop  bolucu -> TL072 Sallen-Key -> 2.7K + 2x BAT85 -> GPIO4
  6. ADS1115 x2 + I2C (pull-up 2.7K, 4.7K DEGIL)
  7. ESP32-S3 baglantisi
  8. Hizli akim yolu: fark yukselteci -> Sallen-Key -> GPIO5 (B8)

ASAMA 2'DEN FARKLAR — hepsi tasarim3.py'de kural olarak sinaniyor:
  * Bolucunun alt ucu GND'ye DEGIL, tamponlu Vref'e gidiyor -> CIFT YONLU
  * ADS diferansiyel okuyor (AIN0-AIN1, AIN2-AIN3); tekli DEGIL
  * Bolucu TAMPONLU: tamponsuz oto-kademe %0.67 puan kazanc sicramasi
    yapiyordu (DEVIR 4.14)
  * Alt kelepceler 1N4148 DEGIL BAT85: 1N4148 ariza akiminin %25'ini
    ic ESD diyoduna birakiyor (DEVIR 4.13, B2 ile olculdu)
  * Kelepce yalnizca TL072 (+-12 V) skop yolunda; LM358 (+5 V) yolunda
    kelepce degil SERI DIRENC var (R34/R35/R36, B15/F1) — cikis tavani
    icin veri sayfasi yalnizca ALT sinir veriyor (V+ - 1.5 V), ust sinir
    baglanmamis, yani tampon doydugunda ADS'in mutlak maksimumu asilabiliyor
  * I2C pull-up 2.7K: 4.7K iki modulde 308 ns veriyor, sinir 300 ns
  * Skop ortusme suzgeci tek kutuplu RC degil, Sallen-Key 16.55 kHz
    (eski RC 25 kHz'teydi — Nyquist'in USTUNDE, hicbir sey suzmuyordu)

B15 (ariza simulasyonu) ile eklenenler:
  * R34/R35/R36 (1K) — tampon cikislari ve VREF ile ADS pinleri arasinda.
    ONCEDEN HIC YOKTU; tampon doydugu her an ADS spek disi kaliyordu.
  * R38/R39 (1K) — sont kolunda, YALNIZCA ADS dalinda. Hizli yol
    (R27/R29) direncin ONUNDEN tapliyor, bant genisligi etkilenmiyor.
  * C1 100nF -> 1nF — 100nF, TI SLVA482A'nin belgeledigi TL431 osilasyon
    bolgesinin (10 nF .. 2.2 uF) tam icindeydi.

Tum degerler uretim/tasarim3.py (89 kural), uretim/sim3_giris.py
(30 SPICE) ve uretim/sim3_ariza.py (B15, 89 ariza dogrulamasi) ile sinandi.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sema_uret_ortak                                   # noqa: E402
sema_uret_ortak.PROJE = "olcum-karti-a3"                 # parca() bunu kullanir

from kutuphane import sembol_cek                         # noqa: E402
from sema_uret_ortak import (KOK, dugum, etiket, parca,   # noqa: E402
                             pin_konum, u, yazi, yol)
import tasarim3_sabit as T                               # noqa: E402

BURASI = Path(__file__).parent
PROJE3 = "olcum-karti-a3"

# ------------------------------------------------------------- semboller
R = ("Device", "R")
C = ("Device", "C")
D = ("Device", "D")
DSCH = ("Device", "D_Schottky")
TL = ("Reference_Voltage", "TL431LP")
ADS = ("Analog_ADC", "ADS1115IDGS")
OPA = ("Amplifier_Operational", "LM358")
OPT = ("Amplifier_Operational", "TL072")
KLEMENS = ("Connector", "Screw_Terminal_01x02")
# 10 pin: +3V3 GND SDA SCL SKOP HAZIR I_HIZLI +5V GND (+1 yedek)
BASLIK10 = ("Connector_Generic", "Conn_01x10")
# B11 (+-12 V rayi) icin
REG = ("Regulator_Linear", "L7912")
FUSE = ("Device", "Fuse")
CPOL = ("Device", "C_Polarized")
# B21 (pil kapasite testi) icin
NMOS = ("Device", "Q_NMOS")            # deger alani IRFZ44N — jenerik sembol,
                                       # tipki dirençlerde Device:R kullanmak gibi
NPN = ("Transistor_BJT", "BC547")
PNP = ("Transistor_BJT", "BC557")

govde: list[str] = []
g = govde.append


def koy(kut_ad, x, y, ref, deger, aci=0, birim=1, ayak="", kaydir=(3.2, 0.0)):
    kut, ad = kut_ad
    g(parca(f"{kut}:{ad}", x, y, ref, deger, aci, birim, ayak, False, kaydir))
    return lambda no: pin_konum(kut, ad, no, x, y, aci)


_pwr = [0]


def guc(sembol, x, y, aci=0):
    """Guc sembolu. Referans OTOMATIK sirali — elle harf ekli referans
    vermek KiCad'in annotation denetimini bozup netlist'i BOS birakiyor."""
    _pwr[0] += 1
    g(parca(f"power:{sembol}", x, y, f"#PWR{_pwr[0]:03d}", sembol, aci, 1, "",
            gizle_deger=True))
    return pin_konum("power", sembol, "1", x, y, aci)


def baglanti_yok(x, y):
    """KiCad no_connect ogesi — ucun BILEREK bos oldugunu ERC'ye soyler.

    ⚠ UUID ortak yardimcidan (belirlenimli). `uuid.uuid4()` kullanilirsa
    sema her uretimde degisir ve git diff'i anlamsizlasir.
    """
    return f'\t(no_connect (at {x} {y}) (uuid "{u()}"))\n'


def seri_direncler(x, y_bas, adet, ilk_no, deger, aralik=17.78):
    """Dikey seri direnc zinciri. (ust_uc, alt_uc, konumlar) dondurur.

    `ilk_no` ACIK verilir: ilk surumde "R2" onekiyle R21..R26 uretiliyordu
    ve bunlar skop/I2C direncleriyle CAKISIYORDU. KiCad cakisan referansta
    "annotation errors" deyip netlist'i BOS uretiyor — ERC bunu gormuyor.
    """
    konum = []
    for i in range(adet):
        yy = y_bas + i * aralik
        konum.append(koy(R, x, yy, f"R{ilk_no + i}", deger))
    for i in range(adet - 1):
        g(yol(konum[i]("2"), konum[i + 1]("1")))
    return konum[0]("1"), konum[-1]("2"), konum


# ═════════════════════════════ BLOK 1 — TL431 RAYI + VREF TAMPONU
g(yazi("BLOK 1  —  TL431 rayi 2.495 V  +  Vref 1.7153 V (TAMPONLU)", 25.4, 20.32))

p33a = guc("+3V3", 40.64, 30.48)
r1 = koy(R, 40.64, 40.64, "R1", "220R")
tl = koy(TL, 40.64, 58.42, "U1", "TL431LP")
# C1 = 1nF, 100nF DEGIL. B15/C4: TI SLVA482A'ya gore TL431'in katot-anot
# arasindaki kondansator 10 nF .. 2.2 uF araliginda OSILASYONA yol aciyor;
# 100nF tam o araligin icindeydi. Guvenli degerler <1 nF ya da >22 uF.
# TL431 zaten kondansator GEREKTIRMIYOR ("internally compensated to be
# stable without an output capacitor"). Envanterde hazir: C049 1nF x10.
c1 = koy(C, 60.96, 58.42, "C1", "1nF")
gnd1 = guc("GND", 30.48, 58.42)
gnd2 = guc("GND", 60.96, 68.58)

g(yol(p33a, r1("1")))
g(yol(r1("2"), (40.64, 50.8), tl("3")))
g(yol(tl("2"), gnd1))
g(yol(tl("1"), (38.1, 54.61), (38.1, 50.8), (40.64, 50.8)))
g(dugum(40.64, 50.8))
g(yol((40.64, 50.8), (60.96, 50.8), c1("1")))
g(dugum(60.96, 50.8))
g(yol(c1("2"), gnd2))
g(yol((60.96, 50.8), (71.12, 50.8)))
g(etiket("TL_RAY", 71.12, 50.8))

# Vref bolucusu: TL_RAY -> 10K -> tap -> 22K -> GND
g(etiket("TL_RAY", 25.4, 78.74))
r2 = koy(R, 40.64, 88.9, "R2", "10K")
r3 = koy(R, 40.64, 111.76, "R3", "22K")
gnd3 = guc("GND", 40.64, 121.92)
VTAP = (40.64, 99.06)
g(yol((25.4, 78.74), (40.64, 78.74), r2("1")))
g(yol(r2("2"), VTAP))
g(yol(VTAP, r3("1")))
g(yol(r3("2"), gnd3))

# Vref TAMPONU — U3A (LM358). Bolucu akimini SURMEK zorunda.
u3a = koy(OPA, 71.12, 99.06, "U3", "LM358", birim=1)
g(yol(VTAP, u3a("3")))
g(yol(u3a("1"), (81.28, 99.06), (96.52, 99.06)))
g(yol(u3a("2"), (60.96, 96.52), (60.96, 106.68), (81.28, 106.68),
      (81.28, 99.06)))
g(dugum(81.28, 99.06))
g(etiket("VREF", 96.52, 99.06))

# ── B15/F1: VREF'in ADS'e giden KOLU seri direncle ayrildi (R36).
# ADS'in AIN1/AIN3 pinleri VREF'e DOGRUDAN bagliydi. Tampon doydugunda
# (V+ - 1.35 V = 3.65 V @ 5 V ray) ADS'in mutlak maksimumu 3.60 V asiliyordu.
# 1K seri: TI'in tasarim hedefi olan <=1 mA'in cok altina iniyor
# (SLVAEX7A 2.1). PGA SABIT oldugu icin kazanc hatasi da sabit: %0.042.
# Bolucu altlari (R6/R16), C2/C3 ve R28 GERCEK VREF'e bagli kalmali —
# yalnizca ADS kolu direncin ardinda.
g(yol((96.52, 99.06), (109.22, 99.06)))
r36 = koy(R, 113.03, 99.06, "R36", "1K", aci=90)
g(yol(r36("2"), (124.46, 99.06)))
g(etiket("VREF_ADS", 124.46, 99.06))
g(yazi("Vref TAMPONSUZ OLAMAZ: iki bolucunun akimi (~290 uA) 6.9 kohm'luk", 25.4, 132.08, 1.5))
g(yazi("bolucu Thevenin'inden aksa 2 V'a varan kayma yapardi.", 25.4, 137.16, 1.5))
g(yazi("Vref hatasi girise vurulmus SABIT ofsettir (N'den bagimsiz),", 25.4, 142.24, 1.5))
g(yazi("kazanc hatasi degil — sifir kalibrasyonu siler.", 25.4, 147.32, 1.5))

# ═════════════════════════════ BLOK 2 — NORMAL GERILIM (+-31 V)
g(yazi("BLOK 2  —  NORMAL gerilim  +-32.4 V  (220K / 6.8K)  ->  ADS #2 AIN0",
       137.16, 20.32))

j1 = koy(KLEMENS, 137.16, 33.02, "J1", "V girisi +-32V", aci=180)
gndj1 = guc("GND", 149.86, 30.48, aci=180)
NVIN = (162.56, 38.1)
g(yol(j1("1"), (162.56, 33.02), NVIN))
g(yol(j1("2"), gndj1))
g(etiket("V_GIRIS", *NVIN))

# 220K TEK direnc: ilk surumde 2x100K idi (N=30.41). Menzil Vref kadar
# YUKARI kaydigi icin simetrik aralik yalnizca +-29.43 V cikiyordu —
# B4 (AVR testi) -31 V'ta kirpmayi gosterdi. 220K ile +-32.4 V.
r4 = koy(R, 162.56, 63.5, "R4", "220K")
nv_ust, nv_alt = r4("1"), r4("2")
g(yol(NVIN, nv_ust))
NDUG = (162.56, 88.9)
g(yol(nv_alt, NDUG))
r6 = koy(R, 162.56, 99.06, "R6", "6.8K")
g(yol(NDUG, r6("1")))
g(etiket("VREF", 162.56, 111.76))
g(yol(r6("2"), (162.56, 111.76)))

# RC ortusme suzgeci (ADS yolu, Nyquist 430 Hz) — TAMPONUN ONUNDE
r7 = koy(R, 177.8, 88.9, "R7", "22K", aci=90)
c2 = koy(C, 190.5, 99.06, "C2", "100nF")
g(yol(NDUG, r7("1")))
NFILT = (190.5, 88.9)
g(yol(r7("2"), NFILT))
g(yol(NFILT, c2("1")))
g(etiket("VREF", 190.5, 111.76))
g(yol(c2("2"), (190.5, 111.76)))
g(dugum(190.5, 88.9))

# tampon — U3B
u3b = koy(OPA, 213.36, 88.9, "U3", "LM358", birim=2)
g(yol(NFILT, u3b("5")))
g(yol(u3b("7"), (223.52, 88.9), (238.76, 88.9)))
g(yol(u3b("6"), (203.2, 86.36), (203.2, 78.74), (223.52, 78.74),
      (223.52, 88.9)))
g(dugum(223.52, 88.9))
g(etiket("V_TAMPON", 238.76, 88.9))
# ── B15/F1: tampon cikisi ile ADS pini arasina 1K (R34).
# Geri besleme DIRENCTEN ONCE alindigi icin dogruluk etkilenmiyor.
g(yol((238.76, 88.9), (242.57, 88.9)))
r34 = koy(R, 246.38, 88.9, "R34", "1K", aci=90)
g(yol(r34("2"), (254.0, 88.9)))
g(etiket("V_ADS", 254.0, 88.9))
g(yazi("Simetrik menzil +-32.44 V @ PGA +-1.024, adim 1.042 mV.", 137.16, 124.46, 1.5))
g(yazi("Menzil Vref kadar YUKARI kaymistir: -32.44 .. +35.87 V.", 137.16, 119.38, 1.5))
g(yazi("Bolucunun ALT ucu GND'ye degil VREF'e gidiyor: fark = (Vin-Vref)/N,", 137.16, 129.54, 1.5))
g(yazi("ADS diferansiyel okudugu icin ISARETLI -> negatif kendiliginden geliyor.", 137.16, 134.62, 1.5))
g(yazi("TAMPON ZORUNLU: tamponsuz bolucude ADS'in giris empedansi PGA ile", 137.16, 139.7, 1.5))
g(yazi("degistigi icin oto-kademe %0.67 puan kazanc sicramasi yapiyor (4.14).", 137.16, 144.78, 1.5))

# ═════════════════════════════ BLOK 3 — YUKSEK GERILIM (+-615 V)
g(yazi("BLOK 3  —  YUKSEK gerilim  +-613.7 V  (6x820K / 8.2K)  ->  ADS #2 AIN2",
       269.24, 20.32))

j2 = koy(KLEMENS, 269.24, 33.02, "J2", "HV +-615V", aci=180)
gndj2 = guc("GND", 281.94, 30.48, aci=180)
HVIN = (294.64, 38.1)
g(yol(j2("1"), (294.64, 33.02), HVIN))
g(yol(j2("2"), gndj2))
g(etiket("HV_GIRIS", *HVIN))

hv_ust, hv_alt, _ = seri_direncler(294.64, 48.26, 6, 10, "820K", aralik=12.7)
g(yol(HVIN, hv_ust))
HDUG = (294.64, 129.54)
g(yol(hv_alt, HDUG))
r14 = koy(R, 294.64, 139.7, "R16", "8.2K")
g(yol(HDUG, r14("1")))
g(etiket("VREF", 294.64, 152.4))
g(yol(r14("2"), (294.64, 152.4)))

# RC ortusme suzgeci — R17, NORMAL kanaldaki R7'nin karsiligi.
# Bolucunun kendi Thevenin'i 8.19 kohm; TEK BASINA C3 ile fc 194 Hz
# eder ve 860 Hz'te yalnizca -13.1 dB verir — 20 dB kuralini GECMEZ.
# R17 (22K) ile toplam 30.19 kohm, fc 52.7 Hz, 860 Hz'te -24.3 dB.
r17 = koy(R, 322.58, 129.54, "R17", "22K", aci=90)
g(yol(HDUG, r17("1")))
c3 = koy(C, 345.44, 139.7, "C3", "100nF")
HFILT = (345.44, 129.54)
g(yol(r17("2"), HFILT))
g(yol(HFILT, c3("1")))
g(etiket("VREF", 345.44, 152.4))
g(yol(c3("2"), (345.44, 152.4)))
g(dugum(345.44, 129.54))

u4a = koy(OPA, 368.3, 129.54, "U4", "LM358", birim=1)
g(yol(HFILT, u4a("3")))
g(yol(u4a("1"), (378.46, 129.54), (393.7, 129.54)))
g(yol(u4a("2"), (358.14, 127.0), (358.14, 119.38), (378.46, 119.38),
      (378.46, 129.54)))
g(dugum(378.46, 129.54))
g(etiket("HV_TAMPON", 393.7, 129.54))
# ── B15/F1: HV tamponu cikisi ile ADS pini arasina 1K (R35).
g(yol((393.7, 129.54), (393.7, 137.16)))
r35 = koy(R, 393.7, 140.97, "R35", "1K")
g(yol(r35("2"), (393.7, 148.59)))
g(etiket("HV_ADS", 393.7, 148.59))

g(yazi("!!! 615 V OLDURUR. Delikli plakette bu 6 direnc DELIK ATLAYARAK,",
       269.24, 165.1, 1.6))
g(yazi("    aralarinda bosluk birakilarak konmali — 2.54 mm adim YETMEZ.",
       269.24, 170.18, 1.6))
g(yazi("6 adet 820K: 1/4W metal filmin azami CALISMA gerilimi 200 V (Yageo MFR).",
       269.24, 177.8, 1.5))
g(yazi("615 V'ta direnc basina 102 V = sinirin %51'i. Tedarikcinin METAL FILM", 269.24, 182.88, 1.5))
g(yazi("hatti 820K'da bitiyor; 6x820K / 8.2K N'yi TAM 601.0'da tutuyor.", 269.24, 187.96, 1.5))
g(yazi("Giris empedansi 4.93 Mohm (Asama 2'de 106.8 kohm idi).", 269.24, 193.04, 1.5))

# ═════════════════════════════ BLOK 4 — AKIM (KELVIN, CIFT YONLU)
g(yazi("BLOK 4  —  Sont + KELVIN + diferansiyel RC  ->  ADS #1 AIN0/AIN1  (CIFT YONLU)",
       25.4, 165.1))

j3 = koy(KLEMENS, 25.4, 177.8, "J3", "Yuk donusu", aci=180)
gndj3 = guc("GND", 38.1, 175.26, aci=180)
g(yol(j3("2"), gndj3))
rs = koy(R, 55.88, 190.5, "RS", "10R/1R/0R1/15mR")
gnd4 = guc("GND", 55.88, 203.2)
SONT_UST = (55.88, 182.88)
g(yol(j3("1"), (43.18, 177.8), (55.88, 177.8), SONT_UST))
g(etiket("YUK_EKSI", 43.18, 177.8))
g(yol(SONT_UST, rs("1")))
g(yol(rs("2"), gnd4))

# KELVIN: algilama uclari AYRI tellerle, akim yolundan bagimsiz
r16 = koy(R, 78.74, 182.88, "R18", "100R", aci=90)
r17 = koy(R, 78.74, 198.12, "R19", "100R", aci=90)
# B16: 100nF -> 1nF. C4 artik yalnizca RF; asil ortusme suzgeci
# ADS'in KENDI kolunda (C18/C19/C20, R38/R39'un ARDINDA).
c4 = koy(C, 96.52, 190.5, "C4", "1nF", aci=90)
g(yol(SONT_UST, (68.58, 182.88), r16("1")))
g(yol((55.88, 198.12), (68.58, 198.12), r17("1")))
g(dugum(55.88, 198.12))
SP = (91.44, 182.88)
SN = (91.44, 198.12)
g(yol(r16("2"), SP))
g(yol(r17("2"), SN))
g(yol(SP, (96.52, 182.88), c4("1")))
g(yol(c4("2"), (96.52, 198.12), SN))
g(dugum(96.52, 182.88))
g(dugum(96.52, 198.12))
g(yol(SP, (114.3, 182.88)))
g(yol(SN, (114.3, 198.12)))
g(etiket("SONT_P", 114.3, 182.88))
g(etiket("SONT_N", 114.3, 198.12))

# ── B15/F2: ADS'e giden kola 1K seri (R38/R39) — B15'in EN KRITIK duzeltmesi
#
# SONT_P ile ADS #1'in AIN0 pini arasinda HICBIR SEY yoktu. Sonuc (B15/A6-A7):
#   · 10R sont takiliyken 0.49 A'lik bir yuk ADS'in 10 mA giris siniri asar
#   · sont ACIK DEVRE kalirsa 5 V'luk bir yuk bile 10.4 mA akitir
#   · 12 V'ta kacak 74 mA olur; ESP32'nin kendi bosta akimini (40 mA) asinca
#     3V3 rayi YUKSELIR ve ESP32 de tehlikeye girer
# 1K seri direncle esik 4.9 V'tan 14.9 V'a, ESP32 riski 47 V'a cikiyor.
#
# NEDEN KELEPCE DEGIL: SONT_P normal calismada +-256 mV saliniyor —
# yani hem Schottky hem silisyum diyot o gerilimde zaten iletiyor.
# Bu kanalda kelepce KULLANILAMAZ, seri direnc tek secenek.
#
# HIZLI YOL ETKILENMIYOR: R27/R29 hala SONT_P/SONT_N'den, yani direncin
# ONUNDEN tapliyor.
r38 = koy(R, 121.92, 182.88, "R38", "1K", aci=90)
r39 = koy(R, 121.92, 198.12, "R39", "1K", aci=90)
g(yol((114.3, 182.88), r38("1")))
g(yol((114.3, 198.12), r39("1")))
g(yol(r38("2"), (129.54, 182.88)))
g(yol(r39("2"), (129.54, 198.12)))
g(etiket("SONT_P_A", 129.54, 182.88))
g(etiket("SONT_N_A", 129.54, 198.12))
# ── B16: ADS AKIM GIRISLERI ARASINA ORTUSME SUZGECI (C18 + C19 + C20)
#
# NEDEN BURAYA, C4'e DEGIL: C4 dugumunu hizli yol (R27/R29) da tapliyor.
# C4 buyutulurse hizli yolun bandi da kapanir (B16 oncesi tam bu oluyordu:
# I_HIZLI 7.8 kHz'te kaliyordu, skop kanali ise 16.55 kHz). Suzgeci
# R38/R39'un ARDINA koyunca ADS suzuluyor, hizli yol serbest kaliyor.
#
# DEGER: gerilim kanaliyla ZAMAN SABITI ESLESMESI icin
#     C18 = (Rth + R7) x C2 / (R18+R19+R38+R39) = 28.60k x 100n / 2200
#         = 1.300 uF   -> stoktan 1uF + 220nF + 100nF = 1.320 uF (%1.5 uste)
# Eslesmezse wattmetre REAKTIF yukte comuyor: B16 oncesi 50 Hz'te V/I faz
# farki -41.6 derece, PF=0.5'te %155 hata. Sonrasi +0.42 derece, %1.9.
#
# !!! MONTAJ: ADS'in giris pinlerine YAKIN ve KISA bacakli. Ayni zamanda
#     ADS'in anahtarlamali giris kati icin yuk deposu gorevi goruyor.
g(yazi("B16  —  ADS akim girisi ortusme suzgeci:  C18+C19+C20 = 1.32 uF "
       "(gerilim kanaliyla tau eslesmesi)", 25.4, 228.6, 1.6))
g(yol((38.1, 232.41), (96.52, 232.41)))
g(etiket("SONT_P_A", 38.1, 232.41))
g(yol((38.1, 247.65), (96.52, 247.65)))
g(etiket("SONT_N_A", 38.1, 247.65))
for _x, _ref, _deger in ((55.88, "C18", "1uF"), (76.2, "C19", "220nF"),
                         (96.52, "C20", "100nF")):
    _c = koy(C, _x, 240.03, _ref, _deger, aci=90)
    g(yol((_x, 232.41), _c("1")))
    g(yol(_c("2"), (_x, 247.65)))
    if _x != 96.52:
        g(dugum(_x, 232.41))
        g(dugum(_x, 247.65))
g(yazi("Toplam 1.320 uF; ideal 1.300 uF (%1.5 uste).", 106.68, 236.22, 1.4))
g(yazi("Kesim 54.8 Hz — gerilim kanalinin 55.7 Hz'i ile", 106.68, 240.03, 1.4))
g(yazi("eslesiyor ve 430 Hz Nyquist'i koruyor.", 106.68, 243.84, 1.4))
g(yazi("!!! ADS pinlerine YAKIN, KISA bacakli.", 106.68, 247.65, 1.4))

g(yazi("Asama 2'de firmware negatif akimi SIFIRA KIRPIYORDU. Donanim zaten", 25.4, 213.36, 1.5))
g(yazi("diferansiyel ve isaretli; kirpma kaldirildi (olcum3.h). Guc", 25.4, 218.44, 1.5))
g(yazi("elektroniginde bobin akimi ters doner — tek yonlu olcum yanlis cevaptir.", 25.4, 223.52, 1.5))

# ═════════════════════════════ BLOK 5 — OSILOSKOP (SALLEN-KEY + BAT85)
g(yazi("BLOK 5  —  Osiloskop CIFT YONLU: -65..+45 V -> Sallen-Key 16.55 kHz -> BAT85 -> GPIO4",
       137.16, 165.1))

j4 = koy(KLEMENS, 137.16, 177.8, "J4", "Skop girisi", aci=180)
gndj4 = guc("GND", 149.86, 175.26, aci=180)
SKIN = (162.56, 182.88)
g(yol(j4("1"), (162.56, 177.8), SKIN))
g(yol(j4("2"), gndj4))
g(etiket("SKOP_GIRIS", *SKIN))

r18 = koy(R, 162.56, 193.04, "R20", "100K")
# ── B19: SKOP KANALI CIFT YONLU YAPILDI (2026-09-09, kullanici karari)
#
# ONCE: R23 alt ucu GND'de, oran 15.71 -> menzil 0 .. 45.5 V TEK YONLU.
#       ESP32 ADC'si eksi okuyamadigi icin negatife inen dalga sekli
#       goruntulenemiyordu.
# SIMDI: alt uc VREF'te (1.7153 V) — gerilim kanallarinin ZATEN kullandigi
#       cozumun aynisi. Sifir giris = VREF, eksi giris asagi, arti yukari.
#       R23 6.8K -> 2.7K ile oran 38.04:
#            -65.2 V .. +45.1 V   (arti taraf HIC daralmiyor)
#       Bedeli COZUNURLUK: adim 11.9 -> 28.8 mV (ikisi de nominal 3.1 V).
#
# ⚠ YENI AKIM YOLU: skop girisinden gelen akim artik GND'ye degil VREF'e
#   gidiyor. Normalde +-0.65 mA, 615 V arizasinda 6.0 mA. sim3_skop.py
#   (B19) bunu ve VREF'e binen capraz konusmayi olcuyor.
# ⚠ IYI YAN ETKI: 615 V arizasinda Sallen-Key girisi 39.2 V yerine
#   17.8 V goruyor — TL072 daha az zorlaniyor.
r19 = koy(R, 162.56, 215.9, "R23", "2.7K")
SKDUG = (162.56, 203.2)
g(yol(SKIN, r18("1")))
g(yol(r18("2"), SKDUG))
g(yol(SKDUG, r19("1")))
g(yol(r19("2"), (162.56, 226.06)))
g(etiket("VREF", 162.56, 226.06))

# Sallen-Key: R20, R21 esit; C5 = 2nF (2x1nF), C6 = 1nF
r20 = koy(R, 180.34, 203.2, "R22", "6.8K", aci=90)
r21 = koy(R, 198.12, 203.2, "R21", "6.8K", aci=90)
c6 = koy(C, 208.28, 213.36, "C6", "1nF")
gnd6 = guc("GND", 208.28, 226.06)
u5a = koy(OPT, 226.06, 203.2, "U5", "TL072", birim=1)
c5 = koy(C, 190.5, 187.96, "C5", "2nF (2x1nF)", aci=0)

g(yol(SKDUG, r20("1")))
SKA = (190.5, 203.2)
g(yol(r20("2"), SKA))
g(yol(SKA, r21("1")))
SKB = (208.28, 203.2)
g(yol(r21("2"), SKB))
g(yol(SKB, c6("1")))
g(yol(c6("2"), gnd6))
g(dugum(208.28, 203.2))
g(yol(SKB, u5a("3")))
SKC = (236.22, 203.2)
g(yol(u5a("1"), SKC))
g(yol(u5a("2"), (215.9, 200.66), (215.9, 195.58), (236.22, 195.58), SKC))
g(dugum(*SKC))
# C1 geri besleme: a dugumunden cikisa
g(yol(SKA, (190.5, 193.04), c5("1")))
g(yol(c5("2"), (198.12, 187.96), (243.84, 187.96), (243.84, 203.2), SKC))
g(dugum(190.5, 203.2))
g(dugum(236.22, 203.2))

# koruma: 2.7K seri + 2x BAT85
# B18/F12: 2.7K -> 10K. Kelepce seri direnci ariza aninda 3V3 rayina
# GERI BESLENEN akimi belirliyor (B15/B1). 10K ile ray 3.582 V yerine
# 2.83 V'ta kaliyor. Menzili SINIRLAMIYOR: kelepce tavani hala
# ADC'nin 3.1 V'unun ustunde (sim3_kelepce.py bolum 2).
r22 = koy(R, 254.0, 203.2, "R26", "10K", aci=90)
g(yol(SKC, r22("1")))
SKPIN = (269.24, 203.2)
g(yol(r22("2"), SKPIN))
# ust kelepce: ANOT pinde, KATOT +3V3'te
d1 = koy(DSCH, 269.24, 193.04, "D1", "BAT85", aci=90)
p33b = guc("+3V3", 269.24, 182.88)
g(yol(SKPIN, d1("2")))
g(yol(d1("1"), p33b))
# alt kelepce: ANOT GND'de, KATOT pinde
d2 = koy(DSCH, 269.24, 213.36, "D2", "BAT85", aci=90)
gnd7 = guc("GND", 269.24, 223.52)
g(yol(SKPIN, d2("1")))
g(yol(d2("2"), gnd7))
g(dugum(*SKPIN))
g(yol(SKPIN, (284.48, 203.2)))
g(etiket("SKOP", 284.48, 203.2))

g(yazi("BAT85 (DO-34 EKSENEL, delikli) — BAT54 SOT-23 oldugu icin secilmedi.", 137.16, 236.22, 1.5))
g(yazi("1N4148 OLMAZ: B2 olctu, ariza akiminin %25'i ADS'in ic ESD diyoduna", 137.16, 241.3, 1.5))
g(yazi("gidiyor. BAT85 ile pin -0.268 V'ta kaliyor, ESD payi ~%0.", 137.16, 246.38, 1.5))
g(yazi("Seri direnc 2.7K: 1K olsaydi +-12 V arizada 11.3 mA — sinir 10 mA.", 137.16, 251.46, 1.5))
g(yazi("Sallen-Key f0 16.55 kHz, Q 0.707. Eski tek kutuplu RC 25 kHz'teydi —", 137.16, 256.54, 1.5))
g(yazi("Nyquist'in (20.83 kHz) USTUNDE, yani hicbir sey suzmuyordu (4.8).", 137.16, 261.62, 1.5))


# ═════════════════════════════ BLOK 8 — HIZLI AKIM YOLU (B8)
g(yazi("BLOK 8  —  Hizli akim yolu: fark yukselteci -> Sallen-Key -> GPIO5",
       355.6, 20.32))

# Fark yukselteci — U8A (TL072, +-12 V). Kazanc 47K/10K = 4.7
#
# NEDEN 4.7, DEVIR'in onerdigi 27 DEGIL: G=27 ile tam olcek sont gerilimi
# 51 mV'ta kaliyor, oysa ADS ayni sontu 256 mV'a kadar okuyor — hizli yol
# yavas yoldan 5 kat ONCE kirpardi. tasarim3.py bolum 10 bunu eliyor.
g(etiket("SONT_P", 355.6, 40.64))
g(etiket("SONT_N", 355.6, 63.5))
r27 = koy(R, 375.92, 40.64, "R27", "10K", aci=90)
r29 = koy(R, 375.92, 63.5, "R29", "10K", aci=90)
g(yol((355.6, 40.64), r27("1")))
g(yol((355.6, 63.5), r29("1")))

u8a = koy(OPT, 411.48, 52.07, "U8", "TL072", birim=1)
DA_ARTI = (388.62, 40.64)     # + giris (SONT_P kolu)
DA_EKSI = (388.62, 63.5)      # - giris (SONT_N kolu)
g(yol(r27("2"), DA_ARTI))
g(yol(r29("2"), DA_EKSI))
g(yol(DA_ARTI, (401.32, 40.64), (401.32, 49.53), u8a("3")))
g(yol(DA_EKSI, (401.32, 63.5), (401.32, 54.61), u8a("2")))

# + kolu VREF'e (REF ucu) — cift yonluluk buradan geliyor
r28 = koy(R, 388.62, 27.94, "R28", "47K")
g(yol(DA_ARTI, r28("2")))
g(yol(r28("1"), (388.62, 20.32)))
g(etiket("VREF", 388.62, 20.32))
g(dugum(*DA_ARTI))

# - kolu cikisa (geri besleme)
DA_CIK = (426.72, 52.07)
g(yol(u8a("1"), DA_CIK))
r30 = koy(R, 388.62, 76.2, "R30", "47K")
g(yol(DA_EKSI, r30("1")))
g(yol(r30("2"), (388.62, 86.36), (426.72, 86.36), DA_CIK))
g(dugum(*DA_EKSI))
g(dugum(*DA_CIK))

g(yazi("Kazanc 47K/10K = 4.7 · tam olcek sont 294.6 mV (ADS 256 mV'ta once kirpar)",
       355.6, 96.52, 1.5))
g(yazi("REF ucu VREF'te (1.7153 V, tamponlu) — cikis 1.7153 V +- 1.385 V.",
       355.6, 101.6, 1.5))
g(yazi("Bant 526 kHz; darbogaz Sallen-Key (16.55 kHz), yukseltec DEGIL.",
       355.6, 106.68, 1.5))

# Sallen-Key — U5B (Asama 3'e kadar BOSTA duran kesit)
r31 = koy(R, 441.96, 52.07, "R31", "6.8K", aci=90)
r32 = koy(R, 459.74, 52.07, "R32", "6.8K", aci=90)
c8 = koy(C, 469.9, 62.23, "C8", "1nF")
gnd16 = koy_gnd = guc("GND", 469.9, 74.93)
u5b = koy(OPT, 487.68, 52.07, "U5", "TL072", birim=2)
# C7 YATAY (aci=90): geri besleme kondansatoru A dugumu ile cikis
# arasinda; dikey birakilinca teller sembolun uzerinden geciyordu.
# x = 450.85 = 355 x 1.27 -> 1.27 mm sebekesine oturuyor (451.1 OTURMUYOR,
# ERC "endpoint_off_grid" veriyordu).
c7 = koy(C, 450.85, 36.83, "C7", "2nF (2x1nF)", aci=90)

g(yol(DA_CIK, r31("1")))
SK2_A = (450.85, 52.07)
g(yol(r31("2"), SK2_A))
g(yol(SK2_A, r32("1")))
SK2_B = (469.9, 52.07)
g(yol(r32("2"), SK2_B))
g(yol(SK2_B, c8("1")))
g(yol(c8("2"), gnd16))
g(dugum(*SK2_B))
g(yol(SK2_B, u5b("5")))
SK2_C = (497.84, 52.07)
g(yol(u5b("7"), SK2_C))
g(yol(u5b("6"), (477.52, 49.53), (477.52, 44.45), (497.84, 44.45), SK2_C))
g(dugum(*SK2_C))
g(yol(SK2_A, (447.04, 52.07), (447.04, 36.83), c7("1")))
g(yol(c7("2"), (505.46, 36.83), (505.46, 52.07), SK2_C))
g(dugum(*SK2_A))

# koruma: 2.7K + 2x BAT85  (skop kanaliyla AYNI recete)
# B18/F12: 2.7K -> 10K (R26 ile ayni gerekce)
r33 = koy(R, 515.62, 52.07, "R33", "10K", aci=90)
g(yol(SK2_C, r33("1")))
IPIN = (530.86, 52.07)
g(yol(r33("2"), IPIN))
d3 = koy(DSCH, 530.86, 41.91, "D3", "BAT85", aci=90)
p33g = guc("+3V3", 530.86, 31.75)
g(yol(IPIN, d3("2")))
g(yol(d3("1"), p33g))
d4 = koy(DSCH, 530.86, 62.23, "D4", "BAT85", aci=90)
gnd17 = guc("GND", 530.86, 72.39)
g(yol(IPIN, d4("1")))
g(yol(d4("2"), gnd17))
g(dugum(*IPIN))
g(yol(IPIN, (546.1, 52.07)))
g(etiket("I_HIZLI", 546.1, 52.07))

g(yazi("U5B Asama 3'e kadar BOSTA duruyordu; artik hizli akim Sallen-Key'i.",
       355.6, 116.84, 1.5))
g(yazi("Sont KELVIN uclari IKI yere gidiyor: ADS'in RC'sine ve buraya.",
       355.6, 121.92, 1.5))
g(yazi("Hizli yol RC'nin ARDINDAN cekilseydi 7.96 kHz'e hapsolurdu.",
       355.6, 127.0, 1.5))

# ═════════════════════════════ BLOK 6 — ADS1115 x2 + I2C
g(yazi("BLOK 6  —  ADS1115 x2  ·  I2C pull-up 2.7K (4.7K DEGIL)", 25.4, 251.46))

# ADS #1 — akim
a1 = koy(ADS, 60.96, 279.4, "U6", "ADS1115 #1 akim")
# ADS pin y'leri: AIN0 276.86 · AIN1 279.40 · AIN2 281.94 · AIN3 284.48
g(etiket("SONT_P_A", 33.02, 276.86))       # B15/F2: 1K'nin ARDINDAN
g(yol((33.02, 276.86), a1("4")))
g(etiket("SONT_N_A", 33.02, 279.4))        # B15/F2: 1K'nin ARDINDAN
g(yol((33.02, 279.4), a1("5")))
gnd8 = guc("GND", 60.96, 292.1)
g(yol(a1("3"), gnd8))
p33c = guc("+3V3", 60.96, 264.16)
g(yol(a1("8"), p33c))
gnd9 = guc("GND", 81.28, 269.24, aci=180)
g(yol(a1("1"), (76.2, 274.32), (76.2, 269.24), gnd9))   # ADDR->GND = 0x48
# Etiketler pin y'leriyle HIZALI — capraz tel cizersen etiket birden
# fazla tele degip ERC'de "label_multiple_wires" uyarisi cikiyor.
g(yol(a1("9"), (86.36, 281.94)))
g(etiket("SDA", 86.36, 281.94))
g(yol(a1("10"), (86.36, 279.4)))
g(etiket("SCL", 86.36, 279.4))
g(yol(a1("2"), (86.36, 274.32)))
g(etiket("HAZIR", 86.36, 274.32))
# kullanilmayan girisler GND'ye (TI: bos giris DIGER kanallari bozabilir)
gnd10 = guc("GND", 40.64, 289.56)
g(yol(a1("6"), (45.72, 281.94), (45.72, 287.02), (40.64, 287.02), gnd10))
g(yol(a1("7"), (43.18, 284.48), (43.18, 287.02)))
g(dugum(43.18, 287.02))

# ADS #2 — gerilim (iki diferansiyel cift)
a2 = koy(ADS, 152.4, 279.4, "U7", "ADS1115 #2 gerilim")
# B15/F1: dordu de 1K seri direncin ARDINDAN geliyor.
g(etiket("V_ADS", 116.84, 276.86))
g(yol((116.84, 276.86), a2("4")))
g(etiket("VREF_ADS", 116.84, 279.4))
g(yol((116.84, 279.4), a2("5")))
g(etiket("HV_ADS", 116.84, 281.94))
g(yol((116.84, 281.94), a2("6")))
g(etiket("VREF_ADS", 116.84, 284.48))
g(yol((116.84, 284.48), a2("7")))
gnd11 = guc("GND", 152.4, 292.1)
g(yol(a2("3"), gnd11))
p33d = guc("+3V3", 152.4, 264.16)
g(yol(a2("8"), p33d))
g(baglanti_yok(*a2("2")))                             # ALERT kullanilmiyor
g(yol(a2("1"), (167.64, 274.32), (167.64, 266.7)))    # ADDR -> VDD = 0x49
g(etiket("+3V3", 167.64, 266.7))
g(yol(a2("9"), (177.8, 281.94)))
g(etiket("SDA", 177.8, 281.94))
g(yol(a2("10"), (177.8, 279.4)))
g(etiket("SCL", 177.8, 279.4))

# I2C pull-up
r23 = koy(R, 213.36, 269.24, "R25", "2.7K")
r24 = koy(R, 228.6, 269.24, "R24", "2.7K")
p33e = guc("+3V3", 213.36, 259.08)
p33f = guc("+3V3", 228.6, 259.08)
g(yol(p33e, r23("1")))
g(yol(p33f, r24("1")))
g(yol(r23("2"), (213.36, 281.94)))
g(etiket("SDA", 213.36, 281.94))
g(yol(r24("2"), (228.6, 281.94)))
g(etiket("SCL", 228.6, 281.94))
g(yazi("4.7K iki modulde 2.42 kohm -> t_r 308 ns; Fast-mode siniri 300 ns.", 25.4, 302.26, 1.5))
g(yazi("2.7K hem 2 hem 3 modulde geciyor (223 / 190 ns), sink 2.21 mA < 3 mA.", 25.4, 307.34, 1.5))

# ═════════════════════════════ BLOK 7 — ESP32-S3
g(yazi("BLOK 7  —  ESP32-S3 N16R8", 269.24, 251.46))
j5 = koy(BASLIK10, 294.64, 281.94, "J5", "ESP32-S3")
g(yol(j5("1"), (309.88, 271.78)))
g(etiket("+3V3", 309.88, 271.78))
g(yol(j5("2"), (309.88, 274.32)))
g(etiket("GND", 309.88, 274.32))
g(yol(j5("3"), (309.88, 276.86)))
g(etiket("SDA", 309.88, 276.86))
g(yol(j5("4"), (309.88, 279.4)))
g(etiket("SCL", 309.88, 279.4))
g(yol(j5("5"), (309.88, 281.94)))
g(etiket("SKOP", 309.88, 281.94))
g(yol(j5("6"), (309.88, 284.48)))
g(etiket("HAZIR", 309.88, 284.48))
g(yol(j5("7"), (309.88, 287.02)))
g(etiket("I_HIZLI", 309.88, 287.02))
# +5V GERI KONDU: LM358'ler (U3, U4) buna bagli. B8'de GPIO5'i eklerken
# 8 pinlik baslikta +5V'un yerini almisti — netlist denetimi yakaladi.
g(yol(j5("8"), (309.88, 289.56)))
g(etiket("+5V", 309.88, 289.56))
g(yol(j5("9"), (309.88, 292.1)))
g(etiket("GND", 309.88, 292.1))
# B21: J5'in 10. pini artik BOS DEGIL — pil testi MOSFET kapisini suruyor.
g(yol(j5("10"), (309.88, 294.64)))
g(etiket("PIL_KAPI", 309.88, 294.64))
g(yazi("GPIO8 SDA · GPIO9 SCL · GPIO4 SKOP (ADC1_CH3) · GPIO5 I_HIZLI (CH4) · GPIO7 HAZIR", 269.24, 302.26, 1.5))

# ═════════════════════════════ OP-AMP BESLEMELERI
g(yazi("OP-AMP BESLEMELERI", 355.6, 251.46))
# U3, U4 = LM358 @ +5 V (birim 3 = guc)
u3p = koy(OPA, 373.38, 271.78, "U3", "LM358", birim=3)
p5a = guc("+5V", 373.38, 261.62)
gnd12 = guc("GND", 373.38, 281.94)
g(yol(u3p("8"), p5a))
g(yol(u3p("4"), gnd12))
u4p = koy(OPA, 403.86, 271.78, "U4", "LM358", birim=3)
p5b = guc("+5V", 403.86, 261.62)
gnd13 = guc("GND", 403.86, 281.94)
g(yol(u4p("8"), p5b))
g(yol(u4p("4"), gnd13))
# U5 = TL072 @ +-12 V
u5p = koy(OPT, 434.34, 271.78, "U5", "TL072", birim=3)
p12 = guc("+12V", 434.34, 261.62)
m12 = guc("-12V", 434.34, 281.94)
g(yol(u5p("8"), p12))
g(yol(u5p("4"), m12))
u8p = koy(OPT, 464.82, 271.78, "U8", "TL072", birim=3)
p12b = guc("+12V", 464.82, 261.62)
m12b = guc("-12V", 464.82, 281.94)
g(yol(u8p("8"), p12b))
g(yol(u8p("4"), m12b))

# ═════════════════════════════ AYIRMA (DECOUPLING) KONDANSATORLERI
#
# Her op-amp besleme ucuna YEREL 100nF. Ilk surumde HIC YOKTU — netlist
# denetimi "+5V/+12V/-12V raylarinda kondansator YOK" diye gosterdi.
#
# NEDEN ONEMLI: op-amp cikisi kapasitif yuk suruyor (Sallen-Key'in C'leri)
# ve besleme empedansi yuksekse bu salinima donusebilir. Ayrica TL072'nin
# slew hizi 13 V/us; ani akim talebini yerel kondansator karsilamali,
# 20 cm'lik besleme teli degil.
g(yazi("AYIRMA KONDANSATORLERI — her op-amp besleme ucuna yerel 100nF",
       355.6, 175.26, 1.5))
_ayirma = [
    ("C9",  "+5V",  381.0,  190.5),
    ("C10", "+5V",  403.86, 190.5),
    ("C11", "+12V", 426.72, 190.5),
    ("C12", "-12V", 449.58, 190.5),
    ("C13", "+12V", 472.44, 190.5),
    ("C14", "-12V", 495.3,  190.5),
    ("C15", "+3V3", 518.16, 190.5),
]
for _ref, _ray, _x, _y in _ayirma:
    _p = guc(_ray, _x, _y - 12.7)
    _c = koy(C, _x, _y, _ref, "100nF")
    _g = guc("GND", _x, _y + 12.7)
    g(yol(_p, _c("1")))
    g(yol(_c("2"), _g))
g(yazi("C9 U3 · C10 U4 · C11/C12 U5 · C13/C14 U8 · C15 ADS rayi",
       355.6, 210.82, 1.5))

# ── B18/F12: +3V3 BOSALTMA DIRENCI (R41)
#
# NEDEN: B15/B1 — +-12 V acikken +3V3 kapaliysa (USB cikarilmis ama 24 V
# takili; "izolasyon icin USB'yi cikar" talimatinin ya da sadece acma
# sirasinin dogal sonucu) BAT85 kelepceleri olu 3V3 rayini 3.582 V'a
# suruyordu. ESP32'nin BESLEME pini mutlak maksimumu 3.60 V — pay 18 mV.
#
# R41 o akima kalici bir yol veriyor: ray 1.67 V'ta kaliyor, pay 1930 mV.
# 🔴 KRITIK OZELLIGI: rayi 2.495 V'un ALTINDA tuttugu icin TL431 hic
#    iletmiyor — yani kurtulus artik TL431'e BAGLI DEGIL. B15 kurtulusun
#    "tesadufi" oldugunu ve TL431 acik devre olursa rayin 9.9 V'a
#    tirmandigini yazmisti; R41 o kalintiyi da kapatiyor.
# Bedeli: normal calismada 3.3 mA surekli cekis (10.9 mW).
r41 = koy(R, 541.02, 190.5, "R41", "1K")
g(yol(guc("+3V3", 541.02, 177.8), r41("1")))
g(yol(r41("2"), guc("GND", 541.02, 203.2)))
g(yazi("R41 (B18/F12): 3V3 bosaltma. Beslemesiz kartta kelepce akimina yol",
       355.6, 218.44, 1.5))
g(yazi("verir; ray 3.58 V yerine 1.67 V'ta kalir ve TL431'e bagimli olmaz.",
       355.6, 223.52, 1.5))

# KULLANILMAYAN kesitler — bosta birakilmaz, gerilim izleyici yapilir
g(yazi("KULLANILMAYAN KESITLER — izleyici olarak baglandi", 355.6, 300.99, 1.5))
u4b = koy(OPA, 381.0, 314.96, "U4", "LM358", birim=2)
gnd14 = guc("GND", 363.22, 317.5)
g(yol(u4b("5"), gnd14))
g(yol(u4b("7"), (391.16, 314.96)))
g(yol(u4b("6"), (370.84, 312.42), (370.84, 304.8), (391.16, 304.8),
      (391.16, 314.96)))
g(dugum(391.16, 314.96))
# U5B ARTIK BOSTA DEGIL — BLOK 8'de hizli akim Sallen-Key'i oldu.
# Yerine yeni TL072'nin (U8) bos kesiti izleyici baglaniyor.
u8b = koy(OPT, 434.34, 314.96, "U8", "TL072", birim=2)
gnd15 = guc("GND", 416.56, 317.5)
g(yol(u8b("5"), gnd15))
g(yol(u8b("7"), (444.5, 314.96)))
g(yol(u8b("6"), (424.18, 312.42), (424.18, 304.8), (444.5, 304.8),
      (444.5, 314.96)))
g(dugum(444.5, 314.96))

# ═════════════════════════════ BLOK 9 — +-12 V RAYI (B11)
#
# Tek ve YALITILMIS 24 V kaynaktan +-12 V. Orta noktayi 7912 TANIMLIYOR:
#     U9 GND pini -> 24V+  (= kart +12 V)
#     U9 VI  pini -> 24V-  (= kart -12 V)
#     U9 VO  pini -> kart GND
#
# NEDEN 7912 VE LM358 TAMPONU DEGIL (DEVIR 5.12.23'un plani):
#   B15/B4a: orta nokta dengesizligi 15.0 mA ve TEK YONLU (+12 -> GND).
#            LM358'in cekme akimi 0..70 C'de yalnizca 5 mA garanti.
#   B15/B4b: orta nokta dugumunde 700 nF ayirma kapasitesi var; LM358
#            icin yayinlanmis tek kapasitif yuk speki 100 pF.
#   7912: 1.5 A cekme, kapasitif yuku zaten ISTIYOR, ic akim siniri +
#         guvenli calisma alani + termal kapatma. Ve stokta (REG004 x2).
#
# NEDEN 7812 DEGIL: akim YONU. 79xx cikis pininden akim CEKER, 78xx VERIR.
# Dengesizlik +12 -> yuk -> GND yonunde, yani GND'den cekilmesi gerekiyor.
#
# 🔴 MONTAJ: 79xx'te TO-220 TABI **VI** pinine bagli (78xx'te GND'ye).
#    Burada VI = -12 V rayi, yani tab -12 V'ta. Topraklanmis bir sogutucuya
#    vidalanirsa -12 V kisa devre olur. Sogutucu GEREKMIYOR (Tj 62 C).
#    Pin sirasi da 78xx'ten FARKLI: 79xx = GND-VI-VO.
g(yazi("BLOK 9  —  +-12 V RAYI (B11):  24 V  ->  7912 orta nokta regulatoru",
       25.4, 378.46))

j6 = koy(KLEMENS, 25.4, 396.24, "J6", "24V girisi", aci=180)
# J6 pin1 = 24V+, pin2 = 24V-
g(yol(j6("1"), (43.18, 396.24)))
g(yol(j6("2"), (38.1, 393.7), (38.1, 408.94), (43.18, 408.94)))

# Sigorta — B15/F8: +-12 V yuku 30 mA, 50 mA sigorta 1.7x pay birakiyor.
f1 = koy(FUSE, 50.8, 396.24, "F1", "50mA", aci=90)
g(yol((43.18, 396.24), f1("1")))
g(yol(f1("2"), (60.96, 396.24)))
g(etiket("+12V", 60.96, 396.24))
g(etiket("-12V", 43.18, 408.94))

# U9 — 7912. GND pini +12V'ta, VI -12V'ta, VO kart GND'sinde.
u9 = koy(REG, 96.52, 396.24, "U9", "L7912")
g(yol(u9("1"), (96.52, 383.54)))          # GND pini yukari -> +12V
g(etiket("+12V", 96.52, 383.54))
g(yol(u9("2"), (78.74, 396.24)))          # VI  sola     -> -12V
g(etiket("-12V", 78.74, 396.24))
g(yol(u9("3"), (114.3, 396.24)))          # VO  saga     -> GND
gnd_b9 = guc("GND", 114.3, 401.32)
g(yol((114.3, 396.24), gnd_b9))

# Kondansatorler. 79xx'te giris kapasitesi VI ile GND-pini arasina,
# cikis kapasitesi VO ile GND-pini arasina konur. Bizim eslemede
# GND-pini = +12V, yani IKISININ DE ARTI UCU +12V'ta.
# Veri sayfasi: 2.2 uF tantal ya da 25 uF aluminyum (giris),
#               1.0 uF tantal ya da 25 uF aluminyum (cikis).
# 68 uF secildi: sinirin ustunde ama 100 uF'lik koruma diyodu esiginin
# altinda (o esikte veri sayfasi VI->VO arasina 1N4001 SART kosuyor).
c16 = koy(CPOL, 137.16, 396.24, "C16", "68uF 50V")
g(yol(c16("1"), (137.16, 383.54)))
g(etiket("+12V", 137.16, 383.54))
g(yol(c16("2"), (137.16, 408.94)))
g(etiket("-12V", 137.16, 408.94))

c17 = koy(CPOL, 160.02, 396.24, "C17", "68uF 50V")
g(yol(c17("1"), (160.02, 383.54)))
g(etiket("+12V", 160.02, 383.54))
gnd_c17 = guc("GND", 160.02, 405.13)
g(yol(c17("2"), gnd_c17))

# Bosaltma direnci — 7912'nin spekleri 5 mA <= I_OUT icin gecerli.
# NORMAL calismada dengesizlik ~0 oldugu icin minimum yuku BU garantiliyor.
# YON ONEMLI: +12 -> GND. GND -> -12 konsaydi regulatorun yukunu
# AZALTIRDI, cogaltmazdi.
r40 = koy(R, 182.88, 396.24, "R40", "1K")
g(yol(r40("1"), (182.88, 383.54)))
g(etiket("+12V", 182.88, 383.54))
gnd_r40 = guc("GND", 182.88, 405.13)
g(yol(r40("2"), gnd_r40))

g(yazi("7912: GND pini +12V'ta, VI -12V'ta, VO kart GND'sinde. Orta noktayi "
       "TANIMLAYAN parca bu.", 25.4, 416.56, 1.5))
g(yazi("R40 (1K) minimum yuku garantiliyor: 12 mA > 5 mA. Dengesizlik sifir "
       "olsa bile regulasyon suruyor.", 25.4, 421.64, 1.5))
g(yazi("C16/C17 68uF: veri sayfasi 25uF aluminyum istiyor; 100uF'in ALTINDA "
       "kalindi (ustunde VI->VO diyodu sart).", 25.4, 426.72, 1.5))
g(yazi("!!! TO-220 TABI VI (-12 V) PININDE — 78xx'ten FARKLI. Sogutucuya "
       "VIDALAMA. Pin sirasi GND-VI-VO.", 25.4, 431.8, 1.6))
g(yazi("F1 50 mA: normal cekis 30 mA. Ters polarite TVS ile korunamiyor "
       "(B15/F8) -> konnektor MEKANIK ANAHTARLI olmali.", 25.4, 436.88, 1.5))


# ═════════════════════════════ GUC BAYRAKLARI (ERC icin)
def bayrak(sembol, x, y):
    p = guc(sembol, x, y)
    _pwr[0] += 1
    g(parca("power:PWR_FLAG", x, y - 5.08, f"#FLG{_pwr[0]:03d}",
            "PWR_FLAG", 0, 1, "", gizle_deger=True))
    f = pin_konum("power", "PWR_FLAG", "1", x, y - 5.08, 0)
    g(yol(p, f))


bayrak("+3V3", 25.4, 335.28)
bayrak("+5V", 55.88, 335.28)
bayrak("+12V", 86.36, 335.28)
bayrak("-12V", 116.84, 335.28)
# GND'ye PWR_FLAG YOK: B11'den beri bu agi U9 (7912) VO pini
# GERCEKTEN suruyor. Bayrak birakilirsa iki 'power output' ayni
# aga baglanmis olur ve ERC hata verir. Bayragin isi zaten
# 'bu ag suruluyor' demekti — artik gercekten oyle.

# ═════════════════════════════ NOTLAR
g(yazi("Asama 3 — CIFT YONLU on uc. Tum degerler uretim/tasarim3.py (89 kural), "
       "uretim/sim3_giris.py (30 SPICE) ve uretim/sim3_ariza.py (B15, 89 ariza) "
       "ile sinandi.", 25.4, 350.52, 1.7))
g(yazi("B15 KORUMALARI: R34/R35/R36 (1K) tampon cikislari ile ADS pinleri arasinda; "
       "R38/R39 (1K) sont kolunda. Bunlar OLMADAN tampon doydugu her an ADS'in",
       25.4, 360.68, 1.5))
g(yazi("mutlak maksimumu (3.6 V) asiliyordu ve sont arizasi ADS'i olduruyordu. "
       "C1 = 1nF (100nF TL431'i osile ettiriyordu — TI SLVA482A).",
       25.4, 365.76, 1.5))
g(yazi("KART IZOLE DEGIL. 615 V kanali sebeke referansli bir devreye "
       "BAGLANMAZ — USB uzerinden bilgisayara sebeke tasir.", 25.4, 355.6, 1.7))

# ═══════════════════════════════════════════════════ dosyayi yaz
# ═════════════════════════════ BLOK 10 — PIL KAPASITE TESTI (B21)
#
# Harici TAS DIRENC yuk, karttaki bir MOSFET anahtarla kesiliyor.
# MOSFET yalnizca AC/KAPA yapiyor — DOGRUSAL KIP YOK, gucu tas direnc
# yiyor. Sogutucu gerekmiyor (sinir 6.55 A, sim3_pil.py bolum 3).
#
# 🔴 NEDEN AYRI KONNEKTOR (J7), KOPRU DEGIL:
#    J3 "Yuk donusu" DOGRUDAN sonte bagli kaliyor (normal ampermetre
#    kullanimi). MOSFET'i ANA akim yoluna koysaydik, ESP32 her reset
#    attiginda OLCULEN DEVRENIN akimi kesilirdi — bir SMPS'i izlerken
#    kabul edilemez. J7 ile normal kullanim hic etkilenmiyor.
#
# 🔴 NEDEN IKI TRANSISTORLU SURUCU:
#    ESP32 3.3 V veriyor; IRFZ44N'in esigi 2..4 V ve RDS(on) 10 V'ta
#    olculmus (INCHANGE sartnamesi s.2). 3.3 V en kotu halde esigin
#    ALTINDA, iyi halde bile MOSFET'i dogrusal bolgede birakip isitir.
#    Kapi +12 V rayindan surulyor (B11 o rayi zaten koydu).
#
# 🔴 CEKME YONU — BUTUN B21'IN EN ONEMLI KARARI:
#    R42 kapiyi GND'ye cekiyor. ESP32 reset atarsa / cokerse / WDT
#    tetiklenirse GPIO YUKSEK EMPEDANSA doner, kapi 0 V'a iner ve
#    MOSFET KAPANIR -> pil bosalmayi DURDURUR. Ters kurulum (kapiyi
#    +12 V'a cekmek) kart olurken yuku BAGLI birakirdi.
#    Kacak denetimi: Igss 100 nA x 10K = 1 mV, esigin 2000 kati altinda.
#
# R45 (220R) kapi seri direnci: BC557'nin tepe akimini 12/220 = 55 mA'e
# siniryor (BC557 tavani 100 mA). Anahtarlama ~2 us — testte saatte bir
# ve DCIR darbelerinde anahtarlandigi icin onemsiz.
g(yazi("BLOK 10  —  PIL KAPASITE TESTI (B21): tas direnc yuk + MOSFET anahtar",
       210.82, 325.12))

# ⚠ YERLESIM: uc AYRI YATAY SERIT kullaniliyor, cunku ayni y'de iki tel
#   KiCad'de birleşir. Ilk surumde J7 -> drain teli ile kapi surucusu
#   teli ayni y=360.68'de gecti ve /PIL_KAPI neti J7 + Q1.D ile KISA
#   DEVRE oldu (netlist bunu yakaladi, ERC yakalamadi — tipik).
#     serit A (y=332.74) : J7 -> MOSFET drain
#     serit B (y=350..371): kapi surucusu zinciri
#     serit C (y=383.54) : MOSFET source -> YUK_EKSI

# ── Yuk konnektoru (SERIT A)
j7 = koy(KLEMENS, 210.82, 332.74, "J7", "Pil testi yuk donusu", aci=180)
gndj7 = guc("GND", 215.9, 322.58)
g(yol(j7("2"), (215.9, 330.2), (215.9, 322.58), gndj7))

# ── Anahtar MOSFET
q1 = koy(NMOS, 365.76, 350.52, "Q1", "IRFZ44N")
g(yol(j7("1"), (368.3, 332.74), q1("D")))

# ── SERIT C: source -> sontun UST ucu
g(yol(q1("S"), (368.3, 383.54), (345.44, 383.54)))
g(etiket("YUK_EKSI", 345.44, 383.54))

# ── SERIT B: kapi dugumu
KAPI = (350.52, 350.52)
g(yol(q1("G"), KAPI))
r45 = koy(R, 335.28, 355.6, "R45", "220R", aci=90)     # yatay, kapi seri
g(yol(r45("2"), (350.52, 355.6), KAPI))
g(dugum(350.52, 355.6))
r42 = koy(R, 350.52, 365.76, "R42", "10K")             # dikey, kapi -> GND
g(yol((350.52, 355.6), r42("1")))
gnd42 = guc("GND", 350.52, 375.92)
g(yol(r42("2"), gnd42))

# ── PNP ust kol (aci=180: E yukarida, C asagida)
q3 = koy(PNP, 312.42, 350.52, "Q3", "BC557", aci=180)
p12b = guc("+12V", 309.88, 340.36)
g(yol(q3("3"), p12b))                                   # 3 = E -> +12V
g(yol(q3("1"), r45("1")))                               # 1 = C -> R45 (ayni y)

# ── NPN alt kol
r43 = koy(R, 299.72, 365.76, "R43", "10K", aci=90)      # yatay
g(yol(q3("2"), (317.5, 365.76), r43("2")))              # 2 = B
q2 = koy(NPN, 259.08, 370.84, "Q2", "2N2222")
g(yol(r43("1"), q2("1")))                               # 1 = C (ayni y)
gnd2b = guc("GND", 261.62, 383.54)
g(yol(q2("3"), gnd2b))                                  # 3 = E
r44 = koy(R, 241.3, 370.84, "R44", "4.7K", aci=90)      # yatay
g(yol(q2("2"), r44("2")))                               # 2 = B
g(yol(r44("1"), (228.6, 370.84)))
g(etiket("PIL_KAPI", 228.6, 370.84))

g(yazi("Kapi GND'ye CEKILI (R42): ESP32 olurse/reset atarsa MOSFET KAPANIR",
       210.82, 393.7, 1.5))
g(yazi("ve pil bosalmayi durdurur. TERS KURMAYIN (kapiyi +12 V'a cekmeyin).",
       210.82, 398.78, 1.5))
g(yazi("Pil gerilimi <= 38.5 V (IRFZ44N Vdss 55 V, %70 pay) — 48 V paket OLMAZ.",
       210.82, 403.86, 1.5))
g(yazi("Yuk J7'ye baglanir. J3'e baglanirsa MOSFET BAYPAS olur ve KESME",
       210.82, 408.94, 1.5))
g(yazi("CALISMAZ — firmware test basinda bunu denetleyip testi reddediyor.",
       210.82, 414.02, 1.5))

kullanilan = [R, C, D, DSCH, TL, ADS, OPA, OPT, KLEMENS, BASLIK10,
              NMOS, NPN, PNP,
              REG, FUSE, CPOL,
              ("power", "GND"), ("power", "+3V3"), ("power", "+5V"),
              ("power", "+12V"), ("power", "-12V"), ("power", "PWR_FLAG")]
semboller = "".join(sembol_cek(k, a) + "\n" for k, a in kullanilan)

sema = ('(kicad_sch\n\t(version 20250114)\n\t(generator "claude")\n'
        '\t(generator_version "9.0")\n'
        f'\t(uuid "{KOK}")\n\t(paper "A2")\n'
        '\t(title_block\n'
        '\t\t(title "Olcum Karti — Asama 3 (CIFT YONLU on uc, +-615 V)")\n'
        '\t\t(company "Elektronik Calisma Alani")\n'
        '\t\t(rev "3")\n'
        '\t\t(comment 1 "Voltmetre +-31.1 V / 950 uV ve +-615.4 V / 18.8 mV · '
        'Ampermetre CIFT YONLU · Osiloskop Sallen-Key 16.55 kHz")\n'
        '\t\t(comment 2 "tasarim3.py + sim3_giris.py + netlist3_dogrula.py '
        'ile dogrulandi")\n'
        '\t)\n'
        f'\t(lib_symbols\n{semboller}\t)\n'
        + "".join(govde)
        + '\t(sheet_instances\n\t\t(path "/" (page "1"))\n\t)\n)\n')

hedef = BURASI.parent / "sema3" / f"{PROJE3}.kicad_sch"
hedef.parent.mkdir(parents=True, exist_ok=True)
hedef.write_text(sema, encoding="utf-8")

proje = ('{\n  "board": {},\n  "boards": [],\n  "cvpcb": {"equivalence_files": []},\n'
         '  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},\n'
         '  "meta": {"filename": "' + PROJE3 + '.kicad_pro", "version": 3},\n'
         # ⚠ ground_pin_not_ground BILEREK kapatildi: B11'de 7912'nin
         # GND pini kart GND'sine DEGIL +12V rayina bagli — orta nokta
         # regulatoru topolojisinin ta kendisi bu. ERC bunu anlayamaz.
         # Karsiliginda netlist3_dogrula.py U9'un UC pinini de tek tek
         # sinar; denetim zayiflamiyor, YERI degisiyor.
         '  "erc": {"rule_severities": '
         '{"ground_pin_not_ground": "ignore"}},\n'
         '  "net_settings": {"classes": [{"name": "Default"}]},\n'
         '  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},\n'
         '  "sheets": [["' + KOK + '", "Root"]],\n  "text_variables": {}\n}\n')
(hedef.parent / f"{PROJE3}.kicad_pro").write_text(proje, encoding="utf-8")

print(f"yazildi: {hedef}")
print(f"  {len(govde)} ogesi, {len(kullanilan)} sembol tanimi")
