# -*- coding: utf-8 -*-
"""Turk elektronik sitelerinde fiyat karsilastirma.

    python fiyat_tara.py "ads1115"  "esp32-s3"  ...

WebFetch bu siteleri alamiyor: direnc.net 403 veriyor, motorobit JS ile
yukluyor. Cozum: kurulu Chrome'u headless kosturup RENDER EDILMIS DOM'u
almak. Gercek tarayici oldugu icin bot engeline de takilmiyor.

NOT: motorobit fiyatlari KDV HARIC, direnc.net KDV DAHIL yayinliyor.
Karsilastirma icin motorobit fiyatlari x1.20 ile duzeltiliyor.
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
KDV = 1.20

SITELER = {
    "motorobit": {
        "arama": "https://www.motorobit.com/arama?q={}",
        "kdv_dahil": False,
    },
    "direnc.net": {
        "arama": "https://www.direnc.net/arama?q={}",
        "kdv_dahil": True,
    },
    # robotistan: arama sonuclari JS ile sonradan cekiliyor, dump-dom yakalayamiyor
}


def dom_cek(url: str, sure_ms: int = 9000) -> str:
    """Chrome'u headless kosturup render edilmis DOM'u dondurur."""
    with tempfile.TemporaryDirectory() as d:
        cikti = Path(d) / "sayfa.html"
        with open(cikti, "w", encoding="utf-8") as f:
            subprocess.run(
                [CHROME, "--headless=new", "--disable-gpu",
                 f"--virtual-time-budget={sure_ms}", "--dump-dom", url],
                stdout=f, stderr=subprocess.DEVNULL, timeout=120)
        return cikti.read_text(encoding="utf-8", errors="replace")


def ayikla_motorobit(s: str) -> list[tuple[str, float]]:
    # <span data-toggle="product-title">AD</span> ... <span data-toggle="price-sell">FIYAT</span>
    bloklar = re.split(r'data-toggle="product-title"', s)[1:]
    cikti = []
    for b in bloklar:
        ad = re.search(r'>([^<]{4,120})</span>', b)
        fi = re.search(r'data-toggle="price-sell"[^>]*>([\d.,]+)</span>', b)
        if ad and fi:
            cikti.append((html.unescape(ad.group(1)).strip(),
                          float(fi.group(1).replace(".", "").replace(",", "."))))
    return cikti


def ayikla_direnc(s: str) -> list[tuple[str, float]]:
    # class="...productDescription">AD</a> ... class="currentPrice">FIYAT TL
    bloklar = re.split(r'class="[^"]*productDescription"', s)[1:]
    cikti = []
    for b in bloklar:
        ad = re.search(r'>([^<]{4,120})</a>', b)
        fi = re.search(r'class="currentPrice"[^>]*>\s*([\d.,]+)\s*TL', b)
        if ad and fi:
            cikti.append((html.unescape(ad.group(1)).strip(),
                          float(fi.group(1).replace(".", "").replace(",", "."))))
    return cikti


def ayikla_genel(s: str) -> list[tuple[str, float]]:
    """Robotistan ve benzerleri icin kaba yakalama."""
    cikti = []
    for m in re.finditer(r'title="([^"]{6,120})"[^>]*>.{0,4000}?([\d]{1,3}(?:\.\d{3})*,\d{2})\s*TL',
                         s, re.S):
        cikti.append((html.unescape(m.group(1)).strip(),
                      float(m.group(2).replace(".", "").replace(",", "."))))
    return cikti


AYIKLAYICI = {"motorobit": ayikla_motorobit,
              "direnc.net": ayikla_direnc,
              "robotistan": ayikla_genel}


def ara(terim: str) -> None:
    print(f"\n{'=' * 74}\n  {terim.upper()}\n{'=' * 74}")
    for site, bilgi in SITELER.items():
        url = bilgi["arama"].format(terim.replace(" ", "+"))
        try:
            dom = dom_cek(url)
            urunler = AYIKLAYICI[site](dom)
        except Exception as e:
            print(f"\n  {site}: alinamadi ({type(e).__name__})")
            continue

        # arama terimindeki kelimeleri iceren urunler
        kelimeler = [k.lower() for k in terim.split() if len(k) > 2]
        eslesen = [(a, f) for a, f in urunler
                   if all(k in a.lower().replace("-", "") for k in
                          [w.replace("-", "") for w in kelimeler])]
        if not eslesen:
            eslesen = urunler[:6]

        print(f"\n  {site}  ({'KDV dahil' if bilgi['kdv_dahil'] else 'KDV HARIC → x1.20'})")
        if not eslesen:
            print("     sonuc yok")
        for ad, f in eslesen[:8]:
            kdvli = f if bilgi["kdv_dahil"] else f * KDV
            ek = "" if bilgi["kdv_dahil"] else f"  ({f:,.2f} + KDV)"
            print(f"     {kdvli:9,.2f} TL   {ad[:62]}{ek}")


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["ads1115"]):
        ara(t)
