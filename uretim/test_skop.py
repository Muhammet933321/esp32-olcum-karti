# -*- coding: utf-8 -*-
"""A5 — Osiloskop: protokol koprusu + olu kod denetimi.

    python test_skop.py

Iki ayri sey dogruluyor:

  1. `S <adet> <Hz> <volt/adim>` baslikli akisi arayuzun KENDI ayristiricisi
     okuyabiliyor mu (test_skop_arayuz.js, sabitler .ino kaynagindan).

  2. Tetikleme ve kalibrasyon dallari GERCEKTEN DERLENMIS IKILIDE duruyor mu.
     Asama 1'de `osiloskop_yakala(0, 0)` cagrisi sabitti; derleyici esigin
     hep sifir oldugunu gorup tetikleme arayan ~25 satiri ve "! tetiklenemedi"
     dalini komple attı. Kaynakta duran kod calisacak demek degil — ikiliye
     bakmak sart.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hedef2                                       # noqa: E402
import gecici                                   # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
ARDUINO_CLI = KOK.parents[1] / ".araclar" / "arduino-cli.exe"
ESKIZ = KOK / "arsiv" / "asama2" / "olcum-karti-a2"

# Kaynakta yazili olup ikilide de bulunmasi gereken dizeler.
# Her biri bir CALISMA DALINI temsil ediyor: dize yoksa dal atilmistir.
BEKLENEN_DIZELER = [
    ("! tetiklenemedi", "tetikleme basarisizlik dali"),
    ("ok i_ofset=", "akim sifirlama komutu"),
    ("ok v_duzeltme=", "gerilim kalibrasyon komutu"),
    ("ok i_duzeltme=", "akim kalibrasyon komutu"),
    ("ok sont_ohm=", "sont degeri komutu"),
    ("A sont=", "ayar raporu"),
    ("! bilinmeyen komut", "komut ayristirici varsayilan dali"),
    ("(hicbir cihaz yok)", "I2C tarama dali"),
]

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"  {ek}" if ek else ""))


def main() -> int:
    global kaldi

    print("  --- 1. protokol koprusu (arayuzun kendi ayristiricisi) ---")
    s = subprocess.run(["node", str(BURASI / "test_skop_arayuz.js")],
                       cwd=KOK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    print(s.stdout.rstrip())
    if s.returncode != 0:
        kaldi += 1
        if s.stderr.strip():
            print(s.stderr.rstrip())

    print("\n  --- 2. derlenmis ikilide olu kod denetimi ---")
    gec_dizin = gecici.dizin("skop_")
    try:
        d = subprocess.run(
            [str(ARDUINO_CLI), "compile", "--fqbn", hedef2.FQBN,
             "--warnings", "all", "--output-dir", str(gec_dizin), str(ESKIZ)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=900)
        if d.returncode != 0:
            print(d.stdout[-1500:])
            print(d.stderr[-1500:])
            ok("ESP32-S3 derlemesi", False)
            return 1

        uyarilar = [x for x in d.stderr.splitlines() if "warning:" in x]
        ok("Derleme uyarisiz", not uyarilar, f"{len(uyarilar)} uyari")

        ikili = next(gec_dizin.glob("*.ino.bin"), None)
        if ikili is None:
            ok("Ikili uretildi", False)
            return 1
        ham = ikili.read_bytes()
        print(f"       ikili {ikili.name}  {len(ham):,} bayt")

        for dize, aciklama in BEKLENEN_DIZELER:
            ok(f"Ikilide duruyor: {aciklama}",
               dize.encode("utf-8") in ham, f'"{dize}"')

        # Ters kanit: uydurma bir dize BULUNMAMALI. Aramanin kendisi
        # her seye "var" demiyor, onu gosteriyor.
        ok("Denetim yanlis pozitif vermiyor",
           b"! bu dize kaynakta yok" not in ham)
    finally:
        shutil.rmtree(gec_dizin, ignore_errors=True)

    print(f"\n  {gecti} gecti, {kaldi} kaldi")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
