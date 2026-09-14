# -*- coding: utf-8 -*-
"""BELGELER/ gezinme seridi — TEK KAYNAK.

NEDEN AYRI DOSYA: serit iki ayri uretecte yasiyordu. `belge-uret.py`
yedi sayfayi kendi `MENU`'sunden uretiyor, `kurulum3-uret.py` ise
`4-kurulum.html`'i BAGIMSIZ bir belge olarak uretiyor ve serit HIC
yoktu. Sonuc: menuden kurulum sayfasina girildiginde geri donus yolu
yoktu, ve B23.2'de eklenen "Baglanma" sekmesi orada gorunmedi.

Bu, projenin defalarca yandigi AYRISMA SINIFI: ayni seyin iki temsili.
Yeni sayfa eklerken YALNIZCA buraya satir eklenecek.

⚠ `4-kurulum.html`'i bu paket URETMIYOR — `kurulum3-uret.py` uretiyor.
  `7-yerlesim.html`'i de `yerlesim3.py` uretiyor (denetim gecerse).
  Menude durmasi onu buranin sorumluluguna sokmuyor; yalnizca seridi
  paylasiyorlar.
"""
from __future__ import annotations

MENU = [("index.html", "Başla"),
        ("1-ne-yapabilir.html", "Ne yapabilir"),
        ("2-olcumler.html", "Ölçümler"),
        ("3-pil-testi.html", "Pil testi"),
        ("6-ag.html", "Bağlanma"),
        ("2-malzemeler.html", "Malzemeler"),
        ("4-kurulum.html", "Kurulum"),
        ("7-yerlesim.html", "Yerleşim"),
        ("5-muhendislik.html", "Mühendislik")]

# Bagimsiz belgeler icin (kendi CSS'i olan sayfalar) satir ici bicim.
_BAG = ("color:inherit;text-decoration:none;padding:5px 11px;"
        "border:1px solid currentColor;border-radius:99px;opacity:.65")
_BU = ("text-decoration:none;padding:5px 11px;border-radius:99px;"
       "border:1px solid currentColor;font-weight:600")


def serit(dosya: str, gomulu: bool = False) -> str:
    """Gezinme seridi. `gomulu`: kendi CSS'i olmayan bagimsiz sayfa."""
    if gomulu:
        ic = "".join(
            f'<a href="{d}" style="{_BU if d == dosya else _BAG}">{a}</a>'
            for d, a in MENU)
        return ('<nav style="display:flex;gap:8px;flex-wrap:wrap;'
                f'margin:0 0 22px;font-size:14px">{ic}</nav>')
    ic = "".join(
        f'<a href="{d}"{" class=\'bu\'" if d == dosya else ""}>{a}</a>'
        for d, a in MENU)
    return f'<nav class="ust">{ic}</nav>'
