# -*- coding: utf-8 -*-
"""Ana ekran ikonunu URETIR — elle cizilmis ikili dosya YOK.

    python ikon-uret.py

iPhone'da "Ana Ekrana Ekle" yapilinca `apple-touch-icon` PNG'si
kullaniliyor; olmazsa iOS sayfanin ekran goruntusunu kirpiyor ve sonuc
okunaksiz oluyor. Android'in manifest ikonlari da ayni dosyayi kullaniyor.

NEDEN URETILIYOR: bu projede "hicbir sayi elle yazilmiyor" kurali var
(`belge-uret.py`). Ayni mantik ikili varliklar icin de gecerli — depoda
kaynagi olmayan bir PNG, degistirilemeyen bir esere donusur. Burasi
yalnizca standart kutuphaneyle (zlib + struct) PNG yaziyor.

Cizim: koyu zemin + gerilim/akim renklerinde iki sinus. Renkler
`style.css`'in `--volt` / `--amper` belirteclerinden OKUNUYOR, elle
yazilmiyor — arayuzun rengi degisirse ikon da degisiyor.
"""
from __future__ import annotations

import math
import re
import struct
import sys
import zlib
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"
BOYUT = 180                      # apple-touch-icon icin onerilen olcu


def css_renk(ad: str, varsayilan: str, koyu: bool = False) -> tuple[int, int, int]:
    """style.css'in belirtecinden rengi okur.

    `koyu=True` ise ONCE `prefers-color-scheme: dark` blogundaki degere
    bakiyor: ikon telefon ana ekraninda duruyor ve orada koyu zemin hem
    daha okunakli hem de acik/koyu tema secimine bagli degil.
    """
    try:
        css = (ARAYUZ / "style.css").read_text(encoding="utf-8", errors="replace")
    except OSError:
        css = ""
    kaynak = css
    if koyu:
        m = re.search(r"prefers-color-scheme:\s*dark[^{]*\{(.*?)\n\s*\}\s*\n",
                      css, re.S)
        if m:
            kaynak = m.group(1)
    m = re.search(rf"--{ad}:\s*(#[0-9a-fA-F]{{6}})", kaynak)
    h = (m.group(1) if m else varsayilan).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def png_yaz(yol: Path, satirlar: list[bytearray]) -> int:
    """Ham RGB satirlarindan PNG uretir (filtre 0, tek IDAT)."""
    ham = b"".join(b"\x00" + bytes(s) for s in satirlar)
    def parca(tip: bytes, veri: bytes) -> bytes:
        return (struct.pack(">I", len(veri)) + tip + veri
                + struct.pack(">I", zlib.crc32(tip + veri) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", BOYUT, BOYUT, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", ihdr)
           + parca(b"IDAT", zlib.compress(ham, 9)) + parca(b"IEND", b""))
    yol.write_bytes(png)
    return len(png)


def main() -> int:
    zemin = css_renk("zemin-2", "#111827", koyu=True)
    volt = css_renk("volt", "#2563eb", koyu=True)
    amper = css_renk("amper", "#f59e0b", koyu=True)

    tuval = [bytearray(zemin * BOYUT) for _ in range(BOYUT)]

    def nokta(x: int, y: int, renk: tuple[int, int, int]) -> None:
        if 0 <= x < BOYUT and 0 <= y < BOYUT:
            tuval[y][x * 3:x * 3 + 3] = bytes(renk)

    # Iki sinus: gerilim (buyuk genlik) ve akim (kaymis, kucuk genlik).
    # Kalinlik 5 px — 180 px'lik ikonda telefonda gorunur kaliyor.
    for x in range(14, BOYUT - 14):
        t = (x - 14) / (BOYUT - 28)
        yv = BOYUT * 0.42 - math.sin(t * 2 * math.pi * 1.5) * BOYUT * 0.20
        ya = BOYUT * 0.66 - math.sin(t * 2 * math.pi * 1.5 - 0.9) * BOYUT * 0.12
        for k in range(-2, 3):
            nokta(x, int(yv) + k, volt)
            nokta(x, int(ya) + k, amper)

    hedef = ARAYUZ / "ikon-180.png"
    n = png_yaz(hedef, tuval)
    print(f"{hedef.name} yazildi: {BOYUT}x{BOYUT}, {n} B")

    # manifest.json AYNI ureteçten — renkleri ikonla ayrisamaz.
    # ⚠ Android'de gercek PWA kurulumu HTTPS ister; kart duz HTTP
    #   konustugu icin kisayol Chrome sekmesinde acilir. iOS'ta ise
    #   `apple-mobile-web-app-capable` duz HTTP'de de tam ekran veriyor.
    #   Manifest yine de duruyor: masaustunde ve ileride bir kopru
    #   HTTPS konusursa ise yariyor.
    zem = "#%02x%02x%02x" % zemin
    man = (
        '{\n'
        '  "name": "Ölçüm Kartı",\n'
        '  "short_name": "Ölçüm",\n'
        '  "start_url": "./",\n'
        '  "display": "standalone",\n'
        '  "orientation": "any",\n'
        f'  "background_color": "{zem}",\n'
        f'  "theme_color": "{zem}",\n'
        '  "icons": [\n'
        f'    {{ "src": "ikon-180.png", "sizes": "{BOYUT}x{BOYUT}",'
        ' "type": "image/png", "purpose": "any" }\n'
        '  ]\n'
        '}\n'
    )
    (ARAYUZ / "manifest.json").write_text(man, encoding="utf-8")
    print(f"manifest.json yazildi: tema {zem}")
    print(f"  zemin #{zemin[0]:02x}{zemin[1]:02x}{zemin[2]:02x} · "
          f"volt #{volt[0]:02x}{volt[1]:02x}{volt[2]:02x} · "
          f"amper #{amper[0]:02x}{amper[1]:02x}{amper[2]:02x}  (style.css'ten)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
