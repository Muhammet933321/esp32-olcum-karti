# -*- coding: utf-8 -*-
"""Sema ureteclerinin ORTAK yardimcilari (Asama 1 ve Asama 2).

sema-uret.py icinden cikarildi ki iki uretec de ayni kodu kullansin.
`PROJE` modul duzeyinde: KiCad'in `instances` blogu proje adini istiyor,
hangi sema uretiliyorsa uretec bu degeri ayarlar.
"""
from __future__ import annotations

import math
import uuid

from kutuphane import pinler

KOK = str(uuid.uuid4())
PROJE = "olcum-karti-a2"
PROJE2 = "olcum-karti-a2"

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
