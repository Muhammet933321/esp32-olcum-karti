# -*- coding: utf-8 -*-
"""B45 — GERCEK KARTTAN skop fiksturu: `CT` tablosu + bir `t` dokumu (S2, M, kodlar).

    python fikstur_skop_al.py            # -> olcum-skop-fikstur.json

test_arayuz3.js bunu okuyup arayuzun ARSIV icin yeniden hesapladigi
gerilimleri (kodVolt ile) kartin `M` satiriyla karsilastiriyor. Fikstur
GERCEK karttan: kartin C kodu ile arayuzun JS'i ayni kodlardan ayni volta
varmali. Sentetik bir tablo iki tarafin ayni formulu paylastigini
sinardi, kartin gercekten ne yazdigini degil.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

KOK = Path(__file__).parent.parent
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                       # noqa: E402
from arsiv import SkopCozucu                               # noqa: E402

YOL = Path(__file__).parent / "olcum-skop-fikstur.json"


def main() -> int:
    k = kart_baglanti.SeriKart(sys.argv[1] if len(sys.argv) > 1 else None)
    k.ac()
    time.sleep(1.0)

    def komut(kom, sn=0.3):
        k.yaz(kom)
        time.sleep(sn)

    k.yaz("CT")
    ct = None
    son = time.monotonic() + 4
    while time.monotonic() < son and ct is None:
        s = k.satir_oku(0.2)
        if s and s.startswith("CT "):
            ct = s
    if not ct or ct.startswith("CT 0"):
        print("CT tablosu yok")
        k.kapat()
        return 1

    komut("X1000", 0.5)
    komut("x500", 1.0)
    for c in ("tm0", "tp25", "te0", "th14", "tl1916", "tb3"):
        komut(c)
    c = SkopCozucu()
    k.yaz("t")
    blok = None
    s2 = None
    son = time.monotonic() + 15
    while time.monotonic() < son and blok is None:
        s = k.satir_oku(0.1)
        if not s:
            continue
        if s.startswith("S2 "):
            s2 = s
        blok = c.besle(s)
    for c_ in ("tl2048", "th40", "tb5"):
        komut(c_)
    komut("X0", 0.5)
    k.kapat()
    if blok is None or not blok["tam"] or not blok["olcum"]:
        print("yakalama gelmedi / eksik / M satiri yok")
        return 1

    veri = {
        "aciklama": "B45 — gercek karttan (CAL 1 kHz, 1 ms/bol). Arayuz arsiv "
                    "olcumu bu kodlardan kartin M satirina varmali.",
        "ct": ct, "s2": s2, "m": blok["olcum"], "kodlar": blok["ornek"],
    }
    YOL.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"yazildi: {YOL.name} · {len(blok['ornek'])} kod · {blok['olcum'][:60]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
