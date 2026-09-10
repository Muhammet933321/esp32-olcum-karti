# -*- coding: utf-8 -*-
"""Dogrulama sayfasini uretir: SVG'leri ve ekran goruntusunu HTML'e gomer.

    python sayfa-uret.py   ->  ../dogrulama-sayfasi.html
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

KOK = Path(__file__).parent.parent
GORSEL = KOK / "gorsel"
SABLON = Path(__file__).parent / "sayfa-sablon.html"
HEDEF = KOK / "dogrulama-sayfasi.html"


def svg(ad: str, sinif: str = "") -> str:
    """SVG dosyasini satir ici gomulebilir hale getirir."""
    s = (GORSEL / ad).read_text(encoding="utf-8")
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s, flags=re.S)
    # sabit boyutlari kaldir, viewBox olceklesin
    s = re.sub(r'\swidth="[\d.]+m?m?"', "", s, count=1)
    s = re.sub(r'\sheight="[\d.]+m?m?"', "", s, count=1)
    s = s.replace("<svg", f'<svg class="{sinif}" preserveAspectRatio="xMidYMid meet"', 1)
    return s.strip()


def png(yol: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(yol.read_bytes()).decode()


def main() -> None:
    html = SABLON.read_text(encoding="utf-8")

    yerine = {
        "{{SEMA}}": svg("sema.svg", "sema"),
        "{{S1}}": svg("s1-aref.svg", "grafik"),
        "{{S2A}}": svg("s2a-bolucu.svg", "grafik"),
        "{{S2B}}": svg("s2b-kelepce.svg", "grafik"),
        "{{S2C}}": svg("s2c-suzgec.svg", "grafik"),
        "{{S3A}}": svg("s3a-sont.svg", "grafik"),
        "{{S3B}}": svg("s3b-bant.svg", "grafik"),
        "{{S4}}": svg("s4-enerji.svg", "grafik"),
        "{{ARAYUZ}}": png(KOK / "arayuz-onizleme.png"),
    }
    for anahtar, deger in yerine.items():
        if anahtar not in html:
            raise SystemExit(f"sablonda {anahtar} yok")
        html = html.replace(anahtar, deger)

    HEDEF.write_text(html, encoding="utf-8")
    print(f"yazildi: {HEDEF}  ({HEDEF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
