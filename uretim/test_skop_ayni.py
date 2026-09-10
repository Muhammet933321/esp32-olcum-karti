# -*- coding: utf-8 -*-
"""Osiloskop olcum matematiginin IKI KOPYASI ayni mi?

    python test_skop_ayni.py

`SkopOlcum` / `skop_kesisim` / `skop_olc` hem Asama 2'nin `olcum2.h`
dosyasinda hem Asama 3'un `skop_olc.h` dosyasinda duruyor. Kopya olmasinin
sebebi skop_olc_uret.py'nin basinda yaziyor.

Kopya olmak KENDI BASINA tehlikeli degil; SESSIZCE AYRISMAK tehlikeli.
Bu test onu imkansiz kiliyor: iki metni karakter karakter karsilastirir.

Asama 2'nin A6 adimi skop matematigini GERCEK KODDA dogruluyor. Bu test
Asama 3'un kopyasinin o dogrulanmis metinle ayni oldugunu gosterdigi icin,
A6'nin kanidi Asama 3 icin de gecerli oluyor — ayri bir A6 kosmaya gerek yok.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from skop_olc_uret import KAYNAK, HEDEF, blok_cikar   # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


def main() -> int:
    print("=" * 78)
    print("  Osiloskop olcum matematigi — iki kopya ayrismis mi?")
    print("=" * 78)
    print()

    if not HEDEF.exists():
        print(f"  {HEDEF} yok — once `python skop_olc_uret.py` kos.")
        return 1

    kaynak_blok = blok_cikar(KAYNAK.read_text(encoding="utf-8")).rstrip()
    kopya_metin = HEDEF.read_text(encoding="utf-8")

    # kopyadan baslik ve kapanis cikarilinca geriye blok kalmali
    bas_isaret = "#include <math.h>"
    i = kopya_metin.index(bas_isaret)
    i = kopya_metin.index("\n", i) + 1
    j = kopya_metin.rindex("#endif /* SKOP_OLC_H */")
    kopya_blok = kopya_metin[i:j].strip("\n")

    ok("Asama 3 kopyasi bulundu", True, f"{HEDEF.name}, {len(kopya_metin)} bayt")
    ok("olcum2.h'den blok cikarilabildi", bool(kaynak_blok),
       f"{len(kaynak_blok.splitlines())} satir")

    ayni = kaynak_blok == kopya_blok
    ok("IKI KOPYA BIREBIR AYNI", ayni,
       f"{len(kaynak_blok)} bayt" if ayni else "AYRISMISLAR")

    if not ayni:
        import difflib
        fark = list(difflib.unified_diff(
            kaynak_blok.splitlines(), kopya_blok.splitlines(),
            fromfile="olcum2.h (KAYNAK)", tofile="skop_olc.h (kopya)",
            lineterm="", n=1))
        print()
        print("  ILK FARKLAR:")
        for s in fark[:25]:
            print("    " + s)
        print()
        print("  DUZELTME: degisikligi olcum2.h'de yap, sonra")
        print("            python skop_olc_uret.py")

    # kritik simgeler gercekten kopyada mi
    for simge in ("SkopOlcum", "skop_kesisim", "skop_olc"):
        ok(f"`{simge}` kopyada var", simge in kopya_blok)

    # Asama 3'un kopyasi Asama 2'nin sabitlerine BAGLI OLMAMALI
    # (BOLME_ORANI olcum2.h'ye ozgu; skop_olc.h onu gormemeli)
    ok("Kopya Asama 2'ye ozgu sabitlere bagli degil",
       "BOLME_ORANI" not in kopya_blok,
       "skop_olc.h tek basina derlenebilir olmali")

    print()
    print(f"  {gecti}/{gecti + kaldi} dogrulama gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
