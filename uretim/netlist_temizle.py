# -*- coding: utf-8 -*-
"""Netlist'ten UCUCU ve KISISEL alanlari temizler — TEK KAYNAK.

🔴 NEDEN AYRI DOSYA (B26, 2026-09-12). `kicad-cli sch export netlist`
iki sey gomuyor:

  * uretim ZAMAN DAMGASI  -> her kosuda degisir, anlamsiz diff uretir
  * semanin MUTLAK YOLU   -> proje kokunun disk yolu; YAYINLANAN depoda
                             kisisel iz (gizlilik_dogrula.py bunu tariyor)

Temizlik `dogrula3.py`nin B3 adiminda VARDI ama ISE YARAMIYORDU, iki
sebepten:

  1. SIRA. B3 temizliyor, ama netlist'i B9'daki `bom_dogrula.py` DAHA
     SONRA yeniden uretiyor ve orada temizlik yoktu. Yani zincirin sonunda
     dosya yine kirli kaliyordu — bagimsiz bir gizlilik denetimi tam bunu
     yakaladi.
  2. KAPSAM. `re.sub(..., count=1)` yalnizca ILK gecisi degistiriyordu.

Artik temizlik burada, uretimi yapan HER yer bunu cagiriyor.
⚠ Yeni bir netlist uretimi eklersen buradan gecir.
"""
from __future__ import annotations

import re
from pathlib import Path

# Semanin depo icindeki GORELI yolu — mutlak yolun yerine bu yaziliyor.
GORELI = {
    "netlist.net": "sema/olcum-karti.kicad_sch",
    "netlist2.net": "sema2/olcum-karti-a2.kicad_sch",
    "netlist3.net": "sema3/olcum-karti-a3.kicad_sch",
}


def temizle(yol: Path) -> bool:
    """Dosyayi yerinde temizler. Degisiklik olduysa True doner."""
    if not yol.exists():
        return False
    eski = yol.read_text(encoding="utf-8", errors="replace")
    yeni = re.sub(r'\(date "[^"]*"\)', '(date "")', eski)
    hedef = GORELI.get(yol.name, "sema3/olcum-karti-a3.kicad_sch")
    yeni = re.sub(r'\(source "[^"]*"\)', f'(source "{hedef}")', yeni)
    if yeni == eski:
        return False
    yol.write_text(yeni, encoding="utf-8")
    return True


if __name__ == "__main__":
    burasi = Path(__file__).parent
    for ad in GORELI:
        if temizle(burasi / ad):
            print(f"  temizlendi: {ad}")
