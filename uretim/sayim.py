# -*- coding: utf-8 -*-
"""Adim ozet satirlarindan iddia sayisini cikarir — ORTAK ayristirici.

    from sayim import sayimlar
    sayimlar(cikti)   ->  [(gecen, toplam), ...]

Zincirdeki 18 ozet satiri DORT ayri bicimde yaziliyor (olculdu):

    89/89 tasarim kurali gecti          girintisiz, "tasarim kurali"
      150/150 dogrulama gecti           girintili, "dogrulama"
    B4/B5/B8/B17: 101/101 kosul gecti   adim oneki + "kosul"
    3/3 kural gecti, 2 uyari            kuyrukta uyari sayisi

Ayni desen HEM sayim kilidi HEM mutasyon kosucusu tarafindan
kullaniliyor; iki kopya tutulsa biri otekinden sessizce ayrisirdi.

🔴 SAYIM TABANLI DENETIMIN KOR NOKTASI. DEVIR'in kendi uyarisi: bir
iddia dusup baskasi eklenince TOPLAM SABIT KALIR ve mutasyon kacar
(B22.2'de tam olarak bu oldu). Bu yuzden `beklenen_sayim.json` kilidi
sapmayi IKI YONDE de kirmizi yapiyor — azalma kadar artis da.
"""
from __future__ import annotations

import re

# Girinti serbest · istege bagli "<adim>:" oneki · dort ad · istege bagli
# ", N uyari" kuyrugu.
DESEN = re.compile(
    r"^[ \t]*(?:[\w/]+:[ \t]*)?(\d+)/(\d+)[ \t]+"
    r"(?:tasarim kurali|dogrulama|kosul|kural)[ \t]+gecti",
    re.M)


def sayimlar(metin: str) -> list[tuple[int, int]]:
    """Metindeki her ozet satiri icin (gecen, toplam)."""
    return [(int(a), int(b)) for a, b in DESEN.findall(metin)]


def toplam(metin: str) -> int:
    """Metindeki butun ozet satirlarindaki GECEN iddia sayisi."""
    return sum(a for a, _b in sayimlar(metin))
