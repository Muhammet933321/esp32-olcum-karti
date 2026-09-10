# -*- coding: utf-8 -*-
"""Olcum Karti — Asama 1 semasini uretir.

Dort blok:
  1. TL431 gerilim referansi -> AREF
  2. Gerilim bolucu + koruma kelepceleri -> A0
  3. Sont + LM358 akim yukselteci -> A1
  4. Besleme ve bayraklar

Tum degerler uretim/sim_*.py ile dogrulanmis olanlardir.
"""
from __future__ import annotations

import math
import uuid
from pathlib import Path

from kutuphane import pinler, sembol_cek

BURASI = Path(__file__).parent
KOK = str(uuid.uuid4())
PROJE = "olcum-karti"


def u() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------- pin konumlari
_PIN_ONBELLEK: dict[tuple[str, str], list[tuple]] = {}


def pin_konum(kutuphane: str, ad: str, numara: str,
              x: float, y: float, aci: int = 0) -> tuple[float, float]:
    """Sembol (x, y, aci) konumundayken verilen pinin sema koordinati.

    Yerel (px, py) once `aci` kadar saat yonunun tersine dondurulur, sonra
    sema Y ekseni ters oldugu icin Y isareti cevrilir:

        x_sema = x + px*cos(aci) - py*sin(aci)
        y_sema = y - (px*sin(aci) + py*cos(aci))

    DIKKAT: 90 derecede isaret hatasi yapmak diyot gibi yonlu parcalari ters
    baglar ve ERC bunu YAKALAMAZ (iki pin de bagli gorunur). Dogrulama
    netlist uzerinden yapilmali — bkz. netlist_dogrula.py.
    """
    anahtar = (kutuphane, ad)
    if anahtar not in _PIN_ONBELLEK:
        _PIN_ONBELLEK[anahtar] = pinler(kutuphane, ad)
    for _birim, no, _isim, px, py, _pa, _tip in _PIN_ONBELLEK[anahtar]:
        if no == numara:
            r = math.radians(aci)
            c, s = round(math.cos(r), 9), round(math.sin(r), 9)
            return (round(x + px * c - py * s, 4),
                    round(y - (px * s + py * c), 4))
    raise KeyError(f"{kutuphane}:{ad} pin {numara} yok")


# --------------------------------------------------------------- parcalar
# Tel kalinligi ACIK yazilmali.
# `(width 0)` "proje varsayilanini kullan" demektir; bu betigin urettigi
# minimal .kicad_pro'da o varsayilan bulunmadigi icin teller SIFIR kalinlikta
# cizilir — sema ERC'den temiz gecer, netlist dogrudur, ama PDF/SVG ciktisinda
# hicbir baglanti gorunmez. KiCad'in kendi varsayilani 0.1524 mm.
TEL_KALINLIK = 0.1524


def tel(x1, y1, x2, y2) -> str:
    return ("\t(wire\n\t\t(pts\n\t\t\t(xy " + f"{x1} {y1}) (xy {x2} {y2}" + ")\n\t\t)\n"
            f"\t\t(stroke (width {TEL_KALINLIK}) (type default))\n"
            f'\t\t(uuid "{u()}")\n\t)\n')


def yol(*noktalar) -> str:
    """Ard arda noktalari birlestiren tel dizisi."""
    return "".join(tel(*noktalar[i], *noktalar[i + 1])
                   for i in range(len(noktalar) - 1))


def dugum(x, y) -> str:
    return f'\t(junction (at {x} {y}) (diameter 0.9144) (color 0 0 0 0) (uuid "{u()}"))\n'


def etiket(ad, x, y, aci=0) -> str:
    return (f'\t(label "{ad}"\n\t\t(at {x} {y} {aci})\n'
            '\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'\t\t(uuid "{u()}")\n\t)\n')


def yazi(metin, x, y, boyut=2.0) -> str:
    return (f'\t(text "{metin}"\n\t\t(at {x} {y} 0)\n'
            f'\t\t(effects (font (size {boyut} {boyut})) (justify left bottom))\n'
            f'\t\t(uuid "{u()}")\n\t)\n')


def parca(lib_id, x, y, ref, deger, aci=0, birim=1, ayak="",
          gizle_deger=False, kaydir=(3.2, 0.0)) -> str:
    dx, dy = kaydir
    dy_ref, dy_val = dy - 3.0, dy + 3.0
    return (
        '\t(symbol\n'
        f'\t\t(lib_id "{lib_id}")\n'
        f'\t\t(at {x} {y} {aci})\n'
        f'\t\t(unit {birim})\n'
        '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
        f'\t\t(uuid "{u()}")\n'
        f'\t\t(property "Reference" "{ref}"\n'
        f'\t\t\t(at {round(x + dx, 4)} {round(y + dy_ref, 4)} 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27)) (justify left))\n\t\t)\n'
        f'\t\t(property "Value" "{deger}"\n'
        f'\t\t\t(at {round(x + dx, 4)} {round(y + dy_val, 4)} 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27)) (justify left)'
        + (' (hide yes)' if gizle_deger else '') + ')\n\t\t)\n'
        f'\t\t(property "Footprint" "{ayak}"\n'
        f'\t\t\t(at {x} {y} 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n'
        '\t\t(instances\n'
        f'\t\t\t(project "{PROJE}"\n'
        f'\t\t\t\t(path "/{KOK}"\n'
        f'\t\t\t\t\t(reference "{ref}") (unit {birim})\n'
        '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')


# =========================================================== YERLESIM
R = ("Device", "R")
C = ("Device", "C")
D = ("Diode", "1N4148")
TL = ("Reference_Voltage", "TL431LP")
OP = ("Amplifier_Operational", "LM358")
KLEMENS = ("Connector", "Screw_Terminal_01x02")
BASLIK = ("Connector_Generic", "Conn_01x05")

govde: list[str] = []
g = govde.append


def koy(kut_ad, x, y, ref, deger, aci=0, birim=1, ayak="", kaydir=(3.2, 0.0)):
    kut, ad = kut_ad
    g(parca(f"{kut}:{ad}", x, y, ref, deger, aci, birim, ayak, False, kaydir))
    return lambda no: pin_konum(kut, ad, no, x, y, aci)


def guc(sembol, x, y, ref, aci=0):
    g(parca(f"power:{sembol}", x, y, ref, sembol, aci, 1, "", gizle_deger=True))
    return pin_konum("power", sembol, "1", x, y, aci)


# ---------------------------------------------- BLOK 1: TL431 referansi
g(yazi("BLOK 1  —  TL431 gerilim referansi  ->  AREF", 25.4, 25.4))

p5 = guc("+5V", 50.8, 38.1, "#PWR01")
r1 = koy(R, 50.8, 48.26, "R1", "1K", ayak="")          # R029
tl = koy(TL, 50.8, 66.04, "U1", "TL431LP", aci=0)
r2 = koy(R, 71.12, 58.42, "R2", "220R", aci=90)        # R006
c1 = koy(C, 83.82, 66.04, "C1", "100nF")               # C008
gnd1 = guc("GND", 40.64, 66.04, "#PWR02")
gnd2 = guc("GND", 83.82, 76.2, "#PWR03")

# +5V -> R1 -> KATOT
g(yol(p5, r1("1")))
g(yol(r1("2"), (50.8, 58.42), tl("3")))     # R1 alt -> K  (K sagda: x+2.54)
# TL431 A -> GND
g(yol(tl("2"), gnd1))
# REF -> K  (REF ustte)
g(yol(tl("1"), (48.26, 62.23), (48.26, 58.42), (50.8, 58.42)))
g(dugum(50.8, 58.42))
# KATOT -> R2 -> AREF
g(yol((50.8, 58.42), r2("2")))
g(yol(r2("1"), (83.82, 58.42), c1("1")))
g(dugum(83.82, 58.42))
g(yol(c1("2"), gnd2))
g(yol((83.82, 58.42), (91.44, 58.42)))
g(etiket("AREF", 91.44, 58.42))

# ------------------------------------- BLOK 2: gerilim bolucu + kelepce
g(yazi("BLOK 2  —  Gerilim bolucu 1:11 + koruma kelepceleri  ->  A0", 127.0, 25.4))

vin = (139.7, 38.1)
j1 = koy(KLEMENS, 114.3, 33.02, "J1", "V girisi", aci=180)
gndj1 = guc("GND", 127.0, 30.48, "#PWR15", aci=180)
g(yol(j1("1"), (139.7, 33.02), vin))
g(yol(j1("2"), gndj1))
r3 = koy(R, 139.7, 48.26, "R3", "100K")                # R025
r4 = koy(R, 139.7, 78.74, "R4", "10K")                 # R032
c2 = koy(C, 154.94, 71.12, "C2", "1nF")                # C049
d1 = koy(D, 152.4, 55.88, "D1", "1N4148", aci=90)      # ust kelepce
d2 = koy(D, 127.0, 74.93, "D2", "1N4148", aci=90)      # alt kelepce
p5b = guc("+5V", 152.4, 43.18, "#PWR04")
gnd3 = guc("GND", 139.7, 88.9, "#PWR05")
gnd4 = guc("GND", 154.94, 81.28, "#PWR06")
gnd5 = guc("GND", 127.0, 83.82, "#PWR07")

NV = (139.7, 66.04)                                     # bolucu dugumu
g(yol(vin, r3("1")))
g(etiket("V_GIRIS", *vin))
g(yol(r3("2"), NV))
g(yol(NV, r4("1")))
g(yol(r4("2"), gnd3))
# dugum -> C2
g(yol(NV, (154.94, 66.04), c2("1")))
g(yol(c2("2"), gnd4))
# ust kelepce: anot dugumde, katot +5V'ta  (aci 90 -> K yukarida, A asagida)
g(yol(NV, (152.4, 66.04), d1("2")))
g(yol(d1("1"), p5b))
# alt kelepce: anot GND'de (asagida), katot dugumde (yukarida)
g(yol(NV, (127.0, 66.04), d2("1")))
g(yol(d2("2"), gnd5))
# A0 cikisi: NV yatay telini saga uzat
g(yol((154.94, 66.04), (170.18, 66.04)))
g(etiket("A0", 170.18, 66.04))
g(dugum(154.94, 66.04))
g(dugum(152.4, 66.04))
g(dugum(127.0, 66.04))

# ------------------------------------- BLOK 3: sont + LM358 akim kati
g(yazi("BLOK 3  —  Sont + LM358 yukselteci (x7.912)  ->  A1", 25.4, 106.68))

j2 = koy(KLEMENS, 17.78, 118.11, "J2", "Yuk donusu", aci=180)
gndj2 = guc("GND", 30.48, 115.57, "#PWR16", aci=180)
g(yol(j2("2"), gndj2))
rs = koy(R, 40.64, 127.0, "RS", "10R / 1R / 0.33R")    # R001 x1/x10/x30
gnd6 = guc("GND", 40.64, 137.16, "#PWR08")
SONT = (40.64, 120.65)
g(yol(j2("1"), (33.02, 118.11), (40.64, 118.11), SONT))
g(etiket("YUK_EKSI", 33.02, 118.11))
g(yol(SONT, rs("1")))
g(yol(rs("2"), gnd6))

op1 = koy(OP, 76.2, 127.0, "U2", "LM358", birim=1)
# + giris (pin 3) <- sont ustu
g(yol(SONT, (40.64, 124.46), op1("3")))
g(dugum(40.64, 120.65))
# geri besleme: cikis -> R5 -> geri dugumu -> R6 -> GND
r5 = koy(R, 76.2, 111.76, "R5", "47K", aci=90, kaydir=(-2.0, 6.0))          # R040
r6 = koy(R, 60.96, 139.7, "R6", "6.8K")                 # R018
gnd7 = guc("GND", 60.96, 149.86, "#PWR09")
GERI = (60.96, 129.54)
g(yol(op1("2"), GERI))
g(yol(GERI, r6("1")))
g(yol(r6("2"), gnd7))
g(yol(GERI, (60.96, 111.76), r5("2")))
g(dugum(60.96, 129.54))
CIKIS = (83.82, 127.0)
g(yol(op1("1"), CIKIS))
g(yol(CIKIS, (83.82, 111.76), r5("1")))
g(dugum(83.82, 127.0))
g(yol(CIKIS, (99.06, 127.0)))
g(etiket("A1", 99.06, 127.0))

# ------------------------------------------ BLOK 4: LM358 beslemesi
g(yazi("BLOK 4  —  Besleme ve baglanti", 152.4, 106.68))
op3 = koy(OP, 142.24, 127.0, "U2", "LM358", birim=3)
p5c = guc("+5V", 139.7, 114.3, "#PWR10")
gnd8 = guc("GND", 139.7, 139.7, "#PWR11")
g(yol(op3("8"), p5c))
g(yol(op3("4"), gnd8))

# kullanilmayan ikinci op-amp: gerilim izleyici olarak baglanir (bosta birakilmaz)
g(yazi("kullanilmayan kat — gerilim izleyici", 187.96, 137.16, 1.4))
op2 = koy(OP, 200.66, 147.32, "U2", "LM358", birim=2)
gnd10 = guc("GND", 185.42, 157.48, "#PWR14")
g(yol(op2("5"), (185.42, 144.78), gnd10))
g(yol(op2("7"), (210.82, 147.32), (210.82, 160.02), (193.04, 160.02),
      (193.04, 149.86)))

# Arduino baglanti basligi
g(yazi("Arduino", 187.96, 83.82, 1.6))
j3 = koy(BASLIK, 190.5, 96.52, "J3", "Arduino", aci=180)
for no, ad, y in (("1", "A0", 101.6), ("2", "A1", 99.06), ("3", "AREF", 96.52)):
    g(yol(j3(no), (205.74, y)))
    g(etiket(ad, 205.74, y))
g(yol(j3("4"), (205.74, 93.98)))
guc("GND", 205.74, 93.98, "#PWR17")
g(yol(j3("5"), (205.74, 91.44)))
guc("+5V", 205.74, 91.44, "#PWR18")

# guc bayraklari — ERC "surulmeyen guc pini" uyarisini susturur
pf1 = guc("PWR_FLAG", 172.72, 114.3, "#FLG01")
p5d = guc("+5V", 172.72, 111.76, "#PWR12")
g(yol(pf1, p5d))
pf2 = guc("PWR_FLAG", 172.72, 137.16, "#FLG02")
gnd9 = guc("GND", 172.72, 139.7, "#PWR13")
g(yol(pf2, gnd9))

# ------------------------------------------------------ aciklama notlari
g(yazi("Tum degerler uretim/sim_*.py ile dogrulandi.  AREF = 2.478 V, "
       "tam olcek 27.2 V / 31-940 mA", 25.4, 165.1, 1.6))
g(yazi("UYARI: firmware'de analogReference(EXTERNAL) ilk analogRead'den "
       "ONCE cagrilmali — yoksa cip yanar.", 25.4, 170.18, 1.6))
g(yazi("R2 = 220R secildi: AREF ic yuku (~32k) uzerinden dusum 17 mV. "
       "4.7K olsaydi 320 mV duserdi.", 25.4, 175.26, 1.6))
g(yazi("C2 = 1nF secildi: kesim 17.8 kHz. 100nF olsaydi 178 Hz olur, "
       "osiloskop kipi olurdu.", 25.4, 180.34, 1.6))

# ======================================================= dosyayi yaz
kullanilan = [R, C, D, TL, OP, KLEMENS, BASLIK,
              ("power", "GND"), ("power", "+5V"), ("power", "PWR_FLAG")]
semboller = "".join(sembol_cek(k, a) + "\n" for k, a in kullanilan)

sema = ('(kicad_sch\n\t(version 20250114)\n\t(generator "claude")\n'
        '\t(generator_version "9.0")\n'
        f'\t(uuid "{KOK}")\n\t(paper "A3")\n'
        '\t(title_block\n'
        '\t\t(title "Olcum Karti — Asama 1 (Arduino)")\n'
        '\t\t(company "Elektronik Calisma Alani")\n'
        '\t\t(rev "1")\n'
        '\t\t(comment 1 "Voltmetre 0-27.2 V · Ampermetre 31-940 mA · '
        'Wattmetre · Osiloskop ~8 kHz")\n'
        '\t\t(comment 2 "Tum degerler uretim/sim_*.py ve netlist_dogrula.py '
        'ile dogrulandi")\n'
        '\t)\n'
        f'\t(lib_symbols\n{semboller}\t)\n'
        + "".join(govde)
        + '\t(sheet_instances\n\t\t(path "/" (page "1"))\n\t)\n)\n')

hedef = BURASI.parent / "arsiv" / "asama1" / "sema" / f"{PROJE}.kicad_sch"
hedef.parent.mkdir(parents=True, exist_ok=True)
hedef.write_text(sema, encoding="utf-8")

proje = ('{\n  "board": {},\n  "boards": [],\n  "cvpcb": {"equivalence_files": []},\n'
         '  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},\n'
         '  "meta": {"filename": "' + PROJE + '.kicad_pro", "version": 3},\n'
         '  "net_settings": {"classes": [{"name": "Default"}]},\n'
         '  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},\n'
         '  "sheets": [["' + KOK + '", "Root"]],\n  "text_variables": {}\n}\n')
(hedef.parent / f"{PROJE}.kicad_pro").write_text(proje, encoding="utf-8")

print(f"yazildi: {hedef}")
print(f"  {len(govde)} ogesi, {len(kullanilan)} sembol tanimi")
