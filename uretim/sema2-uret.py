# -*- coding: utf-8 -*-
"""Olcum Karti — Asama 2 semasini uretir (ESP32-S3 + ADS1115).

Alti blok:
  1. TL431 kelepce rayi (2.495 V)      — Asama 1'de referanstı, simdi KORUMA
  2. Gerilim girisi  -> ADS #2 AIN0    — bolucu 15.71:1 + kelepce
  3. Akim girisi     -> ADS #1 AIN0/1  — sont, KELVIN, diferansiyel RC
  4. Osiloskop girisi-> ESP32 GPIO4    — ayri bolucu + kelepce
  5. ADS1115 x2 + I2C
  6. ESP32-S3 baglantisi

Tum degerler uretim/tasarim2.py ve uretim/sim2_giris.py ile dogrulandi.
Bolucu orani 15.71 (100K/6.8K) A2 taramasinin SECIMIDIR — 11:1 secilseydi
TL431 kelepcesi 29.7 V'ta sizip olcumu bozardi.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from kutuphane import sembol_cek
from sema_uret_ortak import (KOK, PROJE2, dugum, etiket, parca, pin_konum,
                             yazi, yol)

BURASI = Path(__file__).parent

# ------------------------------------------------------------- semboller
R = ("Device", "R")
C = ("Device", "C")
D = ("Device", "D")
TL = ("Reference_Voltage", "TL431LP")
ADS = ("Analog_ADC", "ADS1115IDGS")
KLEMENS = ("Connector", "Screw_Terminal_01x02")
BASLIK6 = ("Connector_Generic", "Conn_01x06")

govde: list[str] = []
g = govde.append


def koy(kut_ad, x, y, ref, deger, aci=0, birim=1, ayak="", kaydir=(3.2, 0.0)):
    kut, ad = kut_ad
    g(parca(f"{kut}:{ad}", x, y, ref, deger, aci, birim, ayak, False, kaydir))
    return lambda no: pin_konum(kut, ad, no, x, y, aci)


_pwr_sayac = [0]


def guc(sembol, x, y, ref=None, aci=0):
    """Guc sembolu koyar. Referans OTOMATIK sirali (#PWR001, #PWR002, ...).

    Elle "#PWR_U2A" gibi harf ekli referans vermek KiCad'in annotation
    denetimini bozuyor ve netlist BOS cikiyor — ERC bunu yakalamiyor.
    """
    _pwr_sayac[0] += 1
    otomatik = f"#PWR{_pwr_sayac[0]:03d}"
    g(parca(f"power:{sembol}", x, y, otomatik, sembol, aci, 1, "",
            gizle_deger=True))
    return pin_konum("power", sembol, "1", x, y, aci)


# ═════════════════════════════ BLOK 1 — TL431 KELEPCE RAYI
g(yazi("BLOK 1  —  TL431 kelepce rayi 2.495 V  (referans DEGIL, KORUMA)",
       25.4, 25.4))

p33a = guc("+3V3", 45.72, 38.1, "#PWR01")
r1 = koy(R, 45.72, 48.26, "R1", "220R")
tl = koy(TL, 45.72, 66.04, "U1", "TL431LP")
c1 = koy(C, 66.04, 66.04, "C1", "100nF")
gnd1 = guc("GND", 35.56, 66.04, "#PWR02")
gnd2 = guc("GND", 66.04, 76.2, "#PWR03")

g(yol(p33a, r1("1")))
g(yol(r1("2"), (45.72, 58.42), tl("3")))          # K
g(yol(tl("2"), gnd1))                              # A -> GND
g(yol(tl("1"), (43.18, 62.23), (43.18, 58.42), (45.72, 58.42)))   # REF -> K
g(dugum(45.72, 58.42))
g(yol((45.72, 58.42), (66.04, 58.42), c1("1")))
g(dugum(66.04, 58.42))
g(yol(c1("2"), gnd2))
g(yol((66.04, 58.42), (81.28, 58.42)))
g(etiket("TL_RAY", 81.28, 58.42))
g(yazi("TL431 calisma akimi = (3.3-2.495)/220 = 3.66 mA  (veri sayfasi min 1 mA)",
       25.4, 88.9, 1.6))

# ═════════════════════════════ BLOK 2 — GERILIM GIRISI
g(yazi("BLOK 2  —  Gerilim girisi, bolucu 15.71:1  ->  ADS #2 AIN0",
       127.0, 25.4))

j1 = koy(KLEMENS, 114.3, 33.02, "J1", "V girisi", aci=180)
gndj1 = guc("GND", 127.0, 30.48, "#PWR04", aci=180)
VIN = (139.7, 38.1)
g(yol(j1("1"), (139.7, 33.02), VIN))
g(yol(j1("2"), gndj1))
g(etiket("V_GIRIS", *VIN))

r2 = koy(R, 139.7, 48.26, "R2", "100K")
r3 = koy(R, 139.7, 78.74, "R3", "6.8K")
c2 = koy(C, 160.02, 71.12, "C2", "1nF")
d1 = koy(D, 154.94, 55.88, "D1", "1N4148", aci=90)     # dugum -> TL_RAY
d2 = koy(D, 127.0, 74.93, "D2", "1N4148", aci=90)      # GND -> dugum
gnd3 = guc("GND", 139.7, 88.9, "#PWR05")
gnd4 = guc("GND", 160.02, 81.28, "#PWR06")
gnd5 = guc("GND", 127.0, 83.82, "#PWR07")

NV = (139.7, 66.04)
g(yol(VIN, r2("1")))
g(yol(r2("2"), NV))
g(yol(NV, r3("1")))
g(yol(r3("2"), gnd3))
g(yol(NV, (160.02, 66.04), c2("1")))
g(yol(c2("2"), gnd4))
# ust kelepce: ANOT dugumde (asagi), KATOT TL_RAY'da (yukari)
g(yol(NV, (154.94, 66.04), d1("2")))
g(yol(d1("1"), (154.94, 50.8)))
g(etiket("TL_RAY", 154.94, 50.8))
# alt kelepce: ANOT GND'de, KATOT dugumde
g(yol(NV, (127.0, 66.04), d2("1")))
g(yol(d2("2"), gnd5))
g(yol((160.02, 66.04), (177.8, 66.04)))
g(etiket("V_DUGUM", 177.8, 66.04))
g(dugum(160.02, 66.04))
g(dugum(154.94, 66.04))
g(dugum(127.0, 66.04))
g(yazi("Tam olcek 32.2 V @ PGA +-2.048 V, adim 982 uV. Dugum en fazla 2.048 V —",
       127.0, 96.52, 1.6))
g(yazi("kelepce 2.495 V'ta oldugu icin diyot TUM MENZILDE ters kutuplu, sizinti yok.",
       127.0, 101.6, 1.6))

# ═════════════════════════════ BLOK 3 — AKIM GIRISI (KELVIN)
g(yazi("BLOK 3  —  Sont + KELVIN algilama + diferansiyel RC  ->  ADS #1 AIN0/AIN1",
       25.4, 116.84))

j2 = koy(KLEMENS, 17.78, 128.27, "J2", "Yuk donusu", aci=180)
gndj2 = guc("GND", 30.48, 125.73, "#PWR08", aci=180)
g(yol(j2("2"), gndj2))
rs = koy(R, 48.26, 137.16, "RS", "10R/1R/0R1/15mR")
gnd6 = guc("GND", 48.26, 147.32, "#PWR09")
SONT_UST = (48.26, 130.81)
g(yol(j2("1"), (33.02, 128.27), (48.26, 128.27), SONT_UST))
g(etiket("YUK_EKSI", 33.02, 128.27))
g(yol(SONT_UST, rs("1")))
g(yol(rs("2"), gnd6))

# --- KELVIN algilama uclari: AYRI teller, akim yolundan bagimsiz
r4 = koy(R, 71.12, 130.81, "R4", "100R", aci=90)
r5 = koy(R, 71.12, 147.32, "R5", "100R", aci=90)
c3 = koy(C, 88.9, 139.7, "C3", "100nF")
IP = (86.36, 130.81)
IN = (86.36, 147.32)
g(yol(SONT_UST, (60.96, 130.81), r4("2")))
g(dugum(48.26, 130.81))
g(yol(r4("1"), IP))
g(yol((48.26, 147.32), (60.96, 147.32), r5("2")))
g(yol((48.26, 144.78), (48.26, 147.32)))
g(dugum(48.26, 144.78))
g(yol(r5("1"), IN))
g(yol(IP, (88.9, 130.81), c3("1")))
g(yol(c3("2"), (88.9, 147.32), IN))
g(dugum(88.9, 130.81))
g(dugum(88.9, 147.32))
g(yol((88.9, 130.81), (109.22, 130.81)))
g(yol((88.9, 147.32), (109.22, 147.32)))
g(etiket("I_ARTI", 109.22, 130.81))
g(etiket("I_EKSI", 109.22, 147.32))

g(yazi("*** KELVIN — MONTAJ KURALI ***", 25.4, 158.75, 1.8))
g(yazi("R4/R5 algilama uclari sontun GOVDESINE ayri lehimlenecek, akim izine DEGIL.",
       25.4, 163.83, 1.6))
g(yazi("15 mohm kademesinde tek lehim noktasi (1 mohm) %6.7 hata demektir;",
       25.4, 168.91, 1.6))
g(yazi("statik kismi kalibrasyonla silinir ama 10 A'de yuke bagli %0.26 kalir.",
       25.4, 173.99, 1.6))

# ═════════════════════════════ BLOK 4 — OSILOSKOP GIRISI
g(yazi("BLOK 4  —  Osiloskop girisi (AYRI kanal)  ->  ESP32 GPIO4 / ADC1_CH3",
       190.5, 116.84))

j3 = koy(KLEMENS, 177.8, 124.46, "J3", "Skop probu", aci=180)
gndj3 = guc("GND", 190.5, 121.92, "#PWR10", aci=180)
SIN = (203.2, 129.54)
g(yol(j3("1"), (203.2, 124.46), SIN))
g(yol(j3("2"), gndj3))
g(etiket("SKOP_GIRIS", *SIN))

r6 = koy(R, 203.2, 139.7, "R6", "100K")
r7 = koy(R, 203.2, 170.18, "R7", "6.8K")
c4 = koy(C, 223.52, 162.56, "C4", "1nF")
d3 = koy(D, 218.44, 147.32, "D3", "1N4148", aci=90)
d4 = koy(D, 190.5, 166.37, "D4", "1N4148", aci=90)
gnd7 = guc("GND", 203.2, 180.34, "#PWR11")
gnd8 = guc("GND", 223.52, 172.72, "#PWR12")
gnd9 = guc("GND", 190.5, 175.26, "#PWR13")

NS = (203.2, 157.48)
g(yol(SIN, r6("1")))
g(yol(r6("2"), NS))
g(yol(NS, r7("1")))
g(yol(r7("2"), gnd7))
g(yol(NS, (223.52, 157.48), c4("1")))
g(yol(c4("2"), gnd8))
g(yol(NS, (218.44, 157.48), d3("2")))
g(yol(d3("1"), (218.44, 142.24)))
g(etiket("TL_RAY", 218.44, 142.24))
g(yol(NS, (190.5, 157.48), d4("1")))
g(yol(d4("2"), gnd9))
g(yol((223.52, 157.48), (243.84, 157.48)))
g(etiket("SKOP", 243.84, 157.48))
g(dugum(223.52, 157.48))
g(dugum(218.44, 157.48))
g(dugum(190.5, 157.48))

# ═════════════════════════════ BLOK 5 — ADS1115 x2 + I2C
g(yazi("BLOK 5  —  ADS1115 x2  (ikisi de SUREKLI kipte, es zamanli V ve I)",
       279.4, 25.4))

u2 = koy(ADS, 314.96, 53.34, "U2", "ADS1115", kaydir=(-6.0, -16.0))
u3 = koy(ADS, 314.96, 96.52, "U3", "ADS1115", kaydir=(-6.0, -16.0))

for u, ref, adr_hedef, ain0, ain1, notu in (
        (u2, "U2", "GND", "I_ARTI", "I_EKSI", "AKIM  0x48"),
        (u3, "U3", "3V3", "V_DUGUM", None, "GERILIM 0x49")):
    # besleme
    p = guc("+3V3", u("8")[0], u("8")[1] - 7.62, f"#PWR_{ref}A")
    g(yol(u("8"), p))
    gg = guc("GND", u("3")[0], u("3")[1] + 7.62, f"#PWR_{ref}B")
    g(yol(u("3"), gg))
    # ADDR
    if adr_hedef == "GND":
        ga = guc("GND", u("1")[0] + 12.7, u("1")[1], f"#PWR_{ref}C", aci=270)
        g(yol(u("1"), ga))
    else:
        pa = guc("+3V3", u("1")[0] + 12.7, u("1")[1], f"#PWR_{ref}C", aci=90)
        g(yol(u("1"), pa))
    # I2C
    g(yol(u("9"), (u("9")[0] + 20.32, u("9")[1])))
    g(etiket("SDA", u("9")[0] + 20.32, u("9")[1]))
    g(yol(u("10"), (u("10")[0] + 20.32, u("10")[1])))
    g(etiket("SCL", u("10")[0] + 20.32, u("10")[1]))
    # analog girisler
    g(yol(u("4"), (u("4")[0] - 20.32, u("4")[1])))
    g(etiket(ain0, u("4")[0] - 20.32, u("4")[1]))
    if ain1:
        g(yol(u("5"), (u("5")[0] - 20.32, u("5")[1])))
        g(etiket(ain1, u("5")[0] - 20.32, u("5")[1]))
    # KULLANILMAYAN analog girisler GND'ye baglanir — acikta birakilmaz.
    # Acik giris komsu kanaldan yuk tasir (Asama 1'de tezgahta yasandi).
    bos = ["5", "6", "7"] if not ain1 else ["6", "7"]
    for i, no in enumerate(bos):
        pb = u(no)
        g(yol(pb, (pb[0] - 7.62, pb[1])))
        gb = guc("GND", pb[0] - 7.62, pb[1] + 5.08, f"#PWR_{ref}D{i}")
        g(yol((pb[0] - 7.62, pb[1]), gb))
    g(yazi(notu, u("4")[0] - 20.32, u("4")[1] - 7.62, 1.6))

# ALERT/RDY yalnizca U2'den; U3'unki bilerek kullanilmiyor
g(yol(u2("2"), (u2("2")[0] + 20.32, u2("2")[1])))
g(etiket("ALERT", u2("2")[0] + 20.32, u2("2")[1]))
def baglanti_yok(x, y):
    """KiCad no_connect ogesi — ucun BILEREK bos oldugunu ERC'ye soyler."""
    ic = '(no_connect (at ' + f'{x} {y}' + ') ' + f'(uuid "{uuid.uuid4()}")' + ')'
    return chr(9) + ic + chr(10)

g(baglanti_yok(*u3("2")))

# I2C pull-up'lar
r8 = koy(R, 289.56, 33.02, "R8", "4.7K (DNP*)", aci=90)
r9 = koy(R, 302.26, 33.02, "R9", "4.7K (DNP*)", aci=90)
p33b = guc("+3V3", 289.56, 22.86, "#PWR14")
p33c = guc("+3V3", 302.26, 22.86, "#PWR15")
g(yol(r8("1"), p33b))
g(yol(r9("1"), p33c))
g(yol(r8("2"), (289.56, 43.18)))
g(etiket("SDA", 289.56, 43.18))
g(yol(r9("2"), (302.26, 43.18)))
g(etiket("SCL", 302.26, 43.18))

# ═════════════════════════════ BLOK 6 — ESP32-S3
g(yazi("BLOK 6  —  ESP32-S3 DevKit baglantisi (yalniz kullanilan pinler)",
       279.4, 116.84))

j4 = koy(BASLIK6, 320.04, 149.86, "J4", "ESP32-S3 DevKit", aci=180)
J4_PIN = [("1", "+3V3", None), ("2", "GND", None), ("3", "SDA", "GPIO8"),
          ("4", "SCL", "GPIO9"), ("5", "SKOP", "GPIO4"),
          ("6", "ALERT", "GPIO7")]
for no, ag, gpio in J4_PIN:
    p = j4(no)
    hedef = (p[0] - 20.32, p[1])
    g(yol(p, hedef))
    if ag == "+3V3":
        g(parca("power:+3V3", hedef[0] - 2.54, hedef[1], "#PWR16", "+3V3",
                270, 1, "", gizle_deger=True))
        g(yol(hedef, pin_konum("power", "+3V3", "1",
                               hedef[0] - 2.54, hedef[1], 270)))
    elif ag == "GND":
        g(parca("power:GND", hedef[0] - 2.54, hedef[1], "#PWR17", "GND",
                90, 1, "", gizle_deger=True))
        g(yol(hedef, pin_konum("power", "GND", "1",
                               hedef[0] - 2.54, hedef[1], 90)))
    else:
        g(etiket(ag, hedef[0] - 12.7, hedef[1]))
        g(yol(hedef, (hedef[0] - 12.7, hedef[1])))
    if gpio:
        g(yazi(gpio, p[0] + 3.0, p[1] + 1.0, 1.4))

# ------------------------------------------- guc bayraklari (ERC icin)
# PWR_FLAG olmadan ERC "besleme pini surulmuyor" der: semada gucu URETEN
# bir parca yok, guc disaridan (ESP32 kartindan) geliyor.
fl1 = koy(("power", "PWR_FLAG"), 25.4, 210.82, "#FLG001", "PWR_FLAG")
p33f = guc("+3V3", 25.4, 220.98, "#PWR20", aci=180)
g(yol(fl1("1"), p33f))
fl2 = koy(("power", "PWR_FLAG"), 45.72, 210.82, "#FLG002", "PWR_FLAG")
gndf = guc("GND", 45.72, 220.98, "#PWR21", aci=180)
g(yol(fl2("1"), gndf))

# ------------------------------------------- SAHA NOTLARI (arastirma)
g(yazi("*** MONTAJ — SIMULASYONUN GOREMEDIGI UC KURAL ***", 190.5, 190.5, 1.9))
g(yazi("1) YILDIZ TOPRAK: sontun GND ucu tek toprak noktasidir. ADS'lerin GND'si,",
       190.5, 196.85, 1.6))
g(yazi("   bolucunun alt ucu ve ESP32 GND'si oraya AYRI tellerle gider — yuk akiminin",
       190.5, 201.93, 1.6))
g(yazi("   gectigi iz uzerinden DEGIL. 10 A x 10 mohm iz = 100 mV hata (12 V'ta %0.8).",
       190.5, 207.01, 1.6))
g(yazi("2) R8/R9 (*DNP): hazir ADS1115 modullerinde kart uzerinde 10K pull-up VAR.",
       190.5, 213.36, 1.6))
g(yazi("   Uc modul + 4.7K = 1.95 kohm; 2 kohm sinirinin altina duser. Modul", 190.5, 218.44, 1.6))
g(yazi("   kullaniliyorsa R8/R9 TAKILMAZ. Ciplak cip lehimleniyorsa takilir.",
       190.5, 223.52, 1.6))
g(yazi("3) SKOP girisi: ESP32-S3 ADC'si gurultuye duyarli ve dogrusal degil.",
       190.5, 229.87, 1.6))
g(yazi("   Temiz dalga sekli isteniyorsa NS dugumu ile GPIO4 arasina TL072 gerilim",
       190.5, 234.95, 1.6))
g(yazi("   izleyici koy (+-12 V raydan). Tamponsuz da calisir, sadece gurultulu.",
       190.5, 240.03, 1.6))

# ------------------------------------------------------------ notlar
g(yazi("Asama 2 — tum degerler uretim/tasarim2.py (24/24) ve "
       "uretim/sim2_giris.py (11/11) ile dogrulandi.", 25.4, 190.5, 1.7))
g(yazi("Bolucu 15.71:1 SECIMDIR: 11:1 olsaydi TL431 kelepcesi 29.7 V'ta "
       "sizip menzili keserdi (A2, secenek C).", 25.4, 195.58, 1.7))
g(yazi("ADS1115 3.3 V'ta besleniyor — 5 V'ta VIH 3.5 V olur ve ESP32'nin "
       "3.3 V'luk cikisi yetmezdi.", 25.4, 200.66, 1.7))

# ═══════════════════════════════════════════════════ dosyayi yaz
kullanilan = [R, C, D, TL, ADS, KLEMENS, BASLIK6,
              ("power", "GND"), ("power", "+3V3"), ("power", "PWR_FLAG")]
semboller = "".join(sembol_cek(k, a) + "\n" for k, a in kullanilan)

sema = ('(kicad_sch\n\t(version 20250114)\n\t(generator "claude")\n'
        '\t(generator_version "9.0")\n'
        f'\t(uuid "{KOK}")\n\t(paper "A3")\n'
        '\t(title_block\n'
        '\t\t(title "Olcum Karti — Asama 2 (ESP32-S3 + ADS1115)")\n'
        '\t\t(company "Elektronik Calisma Alani")\n'
        '\t\t(rev "2")\n'
        '\t\t(comment 1 "Voltmetre 0-32.2 V / 982 uV · Ampermetre 0.78 uA - '
        '11.5 A · Osiloskop 83 kSa/s 12 bit")\n'
        '\t\t(comment 2 "tasarim2.py + sim2_giris.py + netlist2_dogrula.py '
        'ile dogrulandi")\n'
        '\t)\n'
        f'\t(lib_symbols\n{semboller}\t)\n'
        + "".join(govde)
        + '\t(sheet_instances\n\t\t(path "/" (page "1"))\n\t)\n)\n')

hedef = BURASI.parent / "arsiv" / "asama2" / "sema2" / f"{PROJE2}.kicad_sch"
hedef.parent.mkdir(parents=True, exist_ok=True)
hedef.write_text(sema, encoding="utf-8")

proje = ('{\n  "board": {},\n  "boards": [],\n  "cvpcb": {"equivalence_files": []},\n'
         '  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},\n'
         '  "meta": {"filename": "' + PROJE2 + '.kicad_pro", "version": 3},\n'
         '  "net_settings": {"classes": [{"name": "Default"}]},\n'
         '  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},\n'
         '  "sheets": [["' + KOK + '", "Root"]],\n  "text_variables": {}\n}\n')
(hedef.parent / f"{PROJE2}.kicad_pro").write_text(proje, encoding="utf-8")

print(f"yazildi: {hedef}")
print(f"  {len(govde)} ogesi, {len(kullanilan)} sembol tanimi")
