# -*- coding: utf-8 -*-
"""Panelin ikonlarini ve `manifest.json`'u URETIR — elle cizilmis ikili dosya YOK.

    python ikon-uret.py

iPhone'da "Ana Ekrana Ekle" yapilinca `apple-touch-icon` PNG'si
kullaniliyor; olmazsa iOS sayfanin ekran goruntusunu kirpiyor ve sonuc
okunaksiz oluyor. Android ve masaustu PWA kurulumu manifest ikonlarini
kullaniyor.

NEDEN URETILIYOR: bu projede "hicbir sayi elle yazilmiyor" kurali var
(`belge-uret.py`). Ayni mantik ikili varliklar icin de gecerli — depoda
kaynagi olmayan bir PNG, degistirilemeyen bir esere donusur. Burasi
yalnizca standart kutuphaneyle (zlib + struct) PNG yaziyor.

Cizim: koyu zemin + gerilim/akim renklerinde iki sinus. Renkler
`style.css`'in KOYU blogundaki `--zemin-2` / `--volt` / `--amper`
belirteclerinden OKUNUYOR, elle yazilmiyor — arayuzun rengi degisirse ikon
da degisiyor (index.html'in `theme-color`'i da ayni `--zemin-2`).

4F (PC17) — PWA KABUGU IKONLARI:
  * 180 (apple-touch-icon), 192 ve 512 "any"; 192 ve 512 "maskable".
  * Hepsi AYNI cizimden, kenar yumusatmali (piksel merkezinin egriye
    uzakligi -> kaplama). Eski 180'lik ikon basamakliydi; buyuk olcude
    (512) basamak gozle gorunurdu.
  * MASKABLE: isletim sistemi ikonu daire/damla/kare maskesiyle kirpiyor;
    guvenli bolge merkezdeki capi %80 daire (W3C manifest). Cizim merkeze
    gore kucultuluyor; olcek ELLE degil, cizimin merkeze en uzak noktasindan
    HESAPLANIYOR (`MASKE_GUVENLI` yaricapina sigacak kadar). Zemin tam tasma.
  * manifest: `id`, `scope`, `start_url` = "/" (kart ve PC koprusu paneli
    kokten sunuyor). Ikon listesi buradan; `arayuz-uret.py` kart
    goruntusune manifestteki HER ikonu aliyor (kartin manifesti 404'lu ikon
    gostermesin).
"""
from __future__ import annotations

import json
import math
import re
import struct
import zlib
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"

# (dosya, olcu, amac). Ilk satir apple-touch-icon (index.html bagliyor).
IKONLAR = (
    ("ikon-180.png", 180, "any"),
    ("ikon-192.png", 192, "any"),
    ("ikon-512.png", 512, "any"),
    ("ikon-maskable-192.png", 192, "maskable"),
    ("ikon-maskable-512.png", 512, "maskable"),
)
# W3C "maskable icon": guvenli bolge yaricapi olcunun %40'i. Bir pay birakiliyor
# (cizgi kalinligi + kenar yumusatma yaricapin icinde kalsin).
MASKE_GUVENLI = 0.40
MASKE_PAY = 0.02


def css_renk(ad: str, varsayilan: str) -> tuple[int, int, int]:
    """style.css'in KOYU blogundan (`:root[data-tema="koyu"]`) rengi okur.

    Ikon telefon ana ekraninda / gorev cubugunda duruyor; koyu zemin hem
    daha okunakli hem de acik/koyu tema secimine bagli degil.
    """
    try:
        css = (ARAYUZ / "style.css").read_text(encoding="utf-8", errors="replace")
    except OSError:
        css = ""
    m = re.search(r':root\[data-tema="koyu"\]\s*\{(.*?)\n\}', css, re.S)
    kaynak = m.group(1) if m else css
    m = re.search(rf"--{ad}:\s*(#[0-9a-fA-F]{{6}})", kaynak)
    h = (m.group(1) if m else varsayilan).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def png_yaz(yol: Path, boyut: int, satirlar: list[bytearray]) -> int:
    """Ham RGB satirlarindan PNG uretir (filtre 0, tek IDAT).

    Renk sayisi <= 256 ise PALETLI (renk tipi 3, piksel basina 1 bayt): kenar
    yumusatma kaplamasi `KAPLAMA_ADIM` duzeyine yuvarlandigi icin renkler sinirli.
    Kart goruntusunde (LittleFS) PNG gzip'lenmiyor — her bayt butceye sayiliyor;
    RGB'ye gore ~3 kat kucuk. Filtre 0: denendi, 1/2/4 bu cizimde %35-50 BUYUK."""
    renkler = sorted({bytes(s[i:i + 3]) for s in satirlar for i in range(0, len(s), 3)})
    paletli = len(renkler) <= 256
    if paletli:
        no = {r: i for i, r in enumerate(renkler)}
        ham = b"".join(b"\x00" + bytes(no[bytes(s[i:i + 3])] for i in range(0, len(s), 3))
                       for s in satirlar)
    else:
        ham = b"".join(b"\x00" + bytes(s) for s in satirlar)

    def parca(tip: bytes, veri: bytes) -> bytes:
        return (struct.pack(">I", len(veri)) + tip + veri
                + struct.pack(">I", zlib.crc32(tip + veri) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", boyut, boyut, 8, 3 if paletli else 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", ihdr)
           + (parca(b"PLTE", b"".join(renkler)) if paletli else b"")
           + parca(b"IDAT", zlib.compress(ham, 9)) + parca(b"IEND", b""))
    yol.write_bytes(png)
    return len(png)


# ── cizim (birim karede: 0..1) ────────────────────────────────────────
# 180'lik ilk ikonun oranlari: kenar payi 14/180, gerilim 0.42 +- 0.20,
# akim 0.66 +- 0.12 (0.9 rad kaymis), 1.5 periyot, cizgi 5/180.
KENAR = 14 / 180
KALINLIK = 5 / 180
# Kenar yumusatma kaplamasi bu kadar duzeye yuvarlanir (paletli PNG icin renk siniri).
KAPLAMA_ADIM = 24


def egriler() -> list[list[tuple[float, float]]]:
    """Iki sinusun birim karedeki noktalari (gerilim, akim)."""
    n = 2000
    v, a = [], []
    for i in range(n + 1):
        t = i / n
        x = KENAR + t * (1 - 2 * KENAR)
        v.append((x, 0.42 - math.sin(t * 2 * math.pi * 1.5) * 0.20))
        a.append((x, 0.66 - math.sin(t * 2 * math.pi * 1.5 - 0.9) * 0.12))
    return [v, a]


def maske_olcegi() -> float:
    """Maskable cizimin kucultme olcegi: cizimin (cizgi dahil) merkeze en uzak
    noktasi guvenli dairenin icinde kalsin. Elle sayi degil — cizim degisirse
    olcek de degisir."""
    uzak = max(math.hypot(x - 0.5, y - 0.5) for e in egriler() for x, y in e)
    return (MASKE_GUVENLI - MASKE_PAY) / (uzak + KALINLIK / 2)


def ciz(boyut: int, maskable: bool, zemin, renkler) -> list[bytearray]:
    olcek = maske_olcegi() if maskable else 1.0
    tuval = [bytearray(zemin * boyut) for _ in range(boyut)]
    r = max(1.0, KALINLIK * olcek * boyut / 2)      # piksel cinsinden yari kalinlik
    for egri, renk in zip(egriler(), renkler):
        # piksel koordinatina (merkeze gore olcekli)
        p = [((0.5 + (x - 0.5) * olcek) * boyut, (0.5 + (y - 0.5) * olcek) * boyut) for x, y in egri]
        xs = [q[0] for q in p]
        x0, x1 = min(xs), max(xs)
        adim = (x1 - x0) / (len(p) - 1)
        for px in range(max(0, int(x0 - r - 1)), min(boyut, int(x1 + r + 2))):
            cx = px + 0.5
            i0 = max(0, int((cx - r - 1 - x0) / adim))
            i1 = min(len(p) - 2, int((cx + r + 1 - x0) / adim) + 1)
            if i1 < i0:
                continue
            ys = [p[i][1] for i in range(i0, i1 + 2)]
            for py in range(max(0, int(min(ys) - r - 1)), min(boyut, int(max(ys) + r + 2))):
                cy = py + 0.5
                d = 1e9
                for i in range(i0, i1 + 1):
                    ax, ay = p[i]
                    bx, by = p[i + 1]
                    dx, dy = bx - ax, by - ay
                    u = ((cx - ax) * dx + (cy - ay) * dy) / (dx * dx + dy * dy)
                    u = 0.0 if u < 0 else (1.0 if u > 1 else u)
                    e = math.hypot(cx - ax - u * dx, cy - ay - u * dy)
                    if e < d:
                        d = e
                kap = r + 0.5 - d
                if kap <= 0:
                    continue
                kap = round(min(1.0, kap) * KAPLAMA_ADIM) / KAPLAMA_ADIM
                if kap <= 0:
                    continue
                s = tuval[py]
                for k in range(3):
                    s[px * 3 + k] = round(s[px * 3 + k] * (1 - kap) + renk[k] * kap)
    return tuval


def manifest_metni(zemin_hex: str) -> str:
    man = {
        "id": "/",
        "name": "Ölçüm Kartı",
        "short_name": "Ölçüm",
        "description": "ESP32 ölçüm kartının paneli: gerilim, akım, güç, osiloskop, pil testi, kayıtlar",
        "lang": "tr",
        "dir": "ltr",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": zemin_hex,
        "theme_color": zemin_hex,
        "icons": [{"src": ad, "sizes": f"{n}x{n}", "type": "image/png", "purpose": amac}
                  for ad, n, amac in IKONLAR],
    }
    return json.dumps(man, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    zemin = css_renk("zemin-2", "#101821")
    volt = css_renk("volt", "#6ea8fe")
    amper = css_renk("amper", "#f2a33c")
    for ad, n, amac in IKONLAR:
        bayt = png_yaz(ARAYUZ / ad, n, ciz(n, amac == "maskable", zemin, (volt, amper)))
        print(f"{ad} yazildi: {n}x{n} {amac}, {bayt} B")
    print(f"  maskable olcegi {maske_olcegi():.3f} (guvenli daire %{200 * MASKE_GUVENLI:.0f})")

    # manifest.json AYNI ureteçten — renkleri ve ikon listesi ikonlarla ayrisamaz.
    zem = "#%02x%02x%02x" % zemin
    (ARAYUZ / "manifest.json").write_text(manifest_metni(zem), encoding="utf-8", newline="\n")
    print(f"manifest.json yazildi: tema {zem}")
    print(f"  zemin {zem} - volt #{volt[0]:02x}{volt[1]:02x}{volt[2]:02x} - "
          f"amper #{amper[0]:02x}{amper[1]:02x}{amper[2]:02x}  (style.css koyu blogundan)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
