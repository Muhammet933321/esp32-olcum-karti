# -*- coding: utf-8 -*-
"""Asama 2 (ESP32-S3 + ADS1115) — tum dogrulama zinciri.

    python dogrula2.py

  A1  Tasarim ve hata butcesi              (hesap + kural)
  A2  Analog giris korumasi ve suzgecler   (ngspice)
  A3  Sema: ERC + netlist                  (kicad-cli)
  A4  Uctan uca: ngspice -> ADS modeli -> GERCEK donusum kodu (AVR
      emulatorunde) -> protokol -> GERCEK arayuz; ayrica ayni kaynak
      gercek ESP32-S3 derleyicisiyle derleniyor
  A5  Osiloskop protokolu -> GERCEK arayuz ayristiricisi; zaman tabani
      merdiveninin firmware ve arayuzde ayni oldugu; tetikleme ve
      kalibrasyon dallarinin derlenmis ikilide durdugu denetimi
  A6  Osiloskop olcum matematigi (frekans, Vpp, RMS, duty, yukselme):
      GERCEK kod AVR emulatorunde, analitik olarak bilinen dalgalara karsi

Cikis kodu 0 ise her sey gecti.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SEMA2 = BURASI.parent / "arsiv" / "asama2" / "sema2" / "olcum-karti-a2.kicad_sch"

ADIMLAR = [
    ("A1  Tasarim ve hata butcesi", "tasarim2.py"),
    ("A2  Analog giris korumasi",   "sim2_giris.py"),
]


def kos(betik: str) -> tuple[bool, str, float]:
    t0 = time.time()
    s = subprocess.run([sys.executable, betik], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    return s.returncode == 0, s.stdout, time.time() - t0


def main() -> int:
    print("=" * 78)
    print("  OLCUM KARTI — ASAMA 2 DOGRULAMA ZINCIRI  (ESP32-S3 + ADS1115)")
    print("=" * 78)
    sonuclar = []

    for baslik, betik in ADIMLAR:
        print(f"\n{'-' * 78}\n  {baslik}\n{'-' * 78}")
        tamam, cikti, sure = kos(betik)
        print(cikti.rstrip())
        sonuclar.append((baslik, tamam, sure))

    # --- A3: sema uret + ERC + netlist
    print(f"\n{'-' * 78}\n  A3  Sema: uretim + ERC + netlist\n{'-' * 78}")
    t0 = time.time()
    u = subprocess.run([sys.executable, "sema2-uret.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300)
    print(u.stdout.rstrip())
    erc = subprocess.run(
        [KICAD_CLI, "sch", "erc", "--output", "erc2.rpt",
         "--severity-error", "--severity-warning", str(SEMA2)],
        cwd=BURASI, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300)
    ihlal = [s for s in erc.stdout.splitlines() if "violation" in s.lower()]
    erc_temiz = "Found 0 violations" in erc.stdout
    print(f"  ERC: {ihlal[0].strip() if ihlal else '?'}")
    n = subprocess.run([sys.executable, "netlist2_dogrula.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300)
    print(n.stdout.rstrip())
    sonuclar.append(("A3  Sema (ERC + netlist)",
                     erc_temiz and n.returncode == 0, time.time() - t0))

    # --- A4: uctan uca
    print(f"\n{'-' * 78}\n  A4  Uctan uca\n{'-' * 78}")
    tamam, cikti, sure = kos("sim2_kart.py")
    print(cikti.rstrip())
    sonuclar.append(("A4  Uctan uca (+ ESP32-S3 derleme)", tamam, sure))

    # --- A5: osiloskop protokolu ve olu kod denetimi
    print(f"\n{'-' * 78}\n  A5  Osiloskop\n{'-' * 78}")
    tamam, cikti, sure = kos("test_skop.py")
    print(cikti.rstrip())
    sonuclar.append(("A5  Osiloskop (protokol + ikili)", tamam, sure))

    # --- A6: osiloskop olcum matematigi, AVR emulatorunde
    print(f"\n{'-' * 78}\n  A6  Osiloskop olcum matematigi\n{'-' * 78}")
    tamam, cikti, sure = kos("test_skop_olcum.py")
    print(cikti.rstrip())
    sonuclar.append(("A6  Skop olcumleri (AVR emulatoru)", tamam, sure))

    print("\n" + "=" * 78)
    print("  OZET")
    print("=" * 78)
    for baslik, tamam, sure in sonuclar:
        print(f"  {'GECTI ' if tamam else 'KALDI '} {baslik:<40} {sure:6.1f} s")

    import shutil
    for d in BURASI.glob("_a[0-9]*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)

    kalan = [b for b, t, _ in sonuclar if not t]
    print()
    if kalan:
        print(f"  {len(kalan)} adim BASARISIZ: {', '.join(kalan)}")
        return 1
    print("  Asama 2 tasarimi dogrulandi — kurulmaya hazir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
