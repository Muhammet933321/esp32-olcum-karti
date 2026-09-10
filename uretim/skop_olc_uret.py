# -*- coding: utf-8 -*-
"""`kod/olcum-karti-a3/skop_olc.h` dosyasini olcum2.h'den URETIR.

    python skop_olc_uret.py

NEDEN: osiloskop olcum matematigi (SkopOlcum + skop_kesisim + skop_olc)
Asama 2 ve Asama 3 tarafindan ORTAK kullaniliyor. Asama 2'nin zinciri
(A4/A5/A6) olcum2.h'ye bagli ve dogrulanmis durumda; Arduino eskiz
dizinleri de ayri oldugu icin tek bir ortak baslik dosyasini iki
eskizden gormek kolay degil.

Cozum: KOPYA + AYRISMA DENETIMI. Bu betik kopyayi uretir,
`test_skop_ayni.py` iki metnin birebir ayni oldugunu sinar. Biri
elle degistirilirse zincir KALIR.

Kaynak olcum2.h'dir. Degisiklik once ORADA yapilir, sonra bu betik kosar.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOD = BURASI.parent / "kod"
KAYNAK = BURASI.parent / "arsiv" / "asama2" / "olcum-karti-a2" / "olcum2.h"
HEDEF = KOD / "olcum-karti-a3" / "skop_olc.h"

BASLIK = '''#ifndef SKOP_OLC_H
#define SKOP_OLC_H
/*
 * Osiloskop olcum matematigi — ASAMA 2 ve ASAMA 3 ORTAK.
 *
 * !! BU DOSYA ELLE DUZENLENMEZ. olcum2.h icindeki ayni blogun birebir
 *    kopyasidir ve uretim/skop_olc_uret.py tarafindan uretilir.
 *    uretim/test_skop_ayni.py iki metni karakter karakter karsilastirir;
 *    ayrisirlarsa zincir KALIR.
 *
 * Degisiklik yapacaksan: once olcum2.h icinde yap, sonra
 *     python uretim/skop_olc_uret.py
 */
#include <stdint.h>
#include <math.h>       /* sqrtf */

'''

SON = "\n#endif /* SKOP_OLC_H */\n"


def blok_cikar(metin: str) -> str:
    """olcum2.h'den osiloskop olcum blogunu ayikla.

    Sinirlar: "OSILOSKOP OLCUMLERI" basligini tasiyan yorum blogunun
    basindan, dosyanin sonundaki #endif'ten hemen oncesine kadar.
    """
    satirlar = metin.splitlines(keepends=True)
    bas = None
    for i, s in enumerate(satirlar):
        if "OSILOSKOP" in s.upper().replace("İ", "I").replace("Ö", "O") \
                or "ÖLÇÜMLER" in s:
            if "═" in satirlar[i - 1]:
                bas = i - 1
                break
    if bas is None:
        raise SystemExit("olcum2.h icinde osiloskop olcum blogu bulunamadi")
    son = next(i for i, s in enumerate(satirlar) if s.startswith("#endif"))
    return "".join(satirlar[bas:son])


def main() -> int:
    blok = blok_cikar(KAYNAK.read_text(encoding="utf-8"))
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_text(BASLIK + blok.rstrip() + "\n" + SON, encoding="utf-8")
    print(f"yazildi: {HEDEF}")
    print(f"  kaynak {KAYNAK.name}, blok {len(blok.splitlines())} satir, "
          f"toplam {HEDEF.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
