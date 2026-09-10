# -*- coding: utf-8 -*-
"""Olcum Karti — tum dogrulama zincirini kosturur.

    python dogrula.py

Sirasiyla:
  S1  TL431 referansi ve AREF seri direnci        (ngspice)
  S2  Gerilim bolucu, kelepceler, ortusme suzgeci (ngspice)
  S3  Sont + LM358 akim kati                      (ngspice)
  S4  Firmware aritmetigi                         (numpy float32 / uint64)
  S5  Sema netlist'i tasarima uyuyor mu           (kicad-cli)
  S6  Firmware gercekten derleniyor mu            (arduino-cli)
  S7  Arayuz mantigi (satir ayristirma, birimler) (node)

Cikis kodu 0 ise her sey gecti.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

BURASI = Path(__file__).parent
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
ARDUINO_CLI = BURASI.parents[2] / ".araclar" / "arduino-cli.exe"
SEMA = BURASI.parent / "arsiv" / "asama1" / "sema" / "olcum-karti.kicad_sch"
ESKIZ = BURASI.parent / "arsiv" / "asama1" / "olcum-karti"

# ATmega328P sinirlari
FLASH_UNO, SRAM = 32256, 2048
EN_AZ_BOS_SRAM = 512      # yigit (stack) icin birakilmasi gereken pay

ADIMLAR = [
    ("S1  TL431 referansi",          "sim_referans.py"),
    ("S2  Bolucu + kelepce + suzgec", "sim_bolucu.py"),
    ("S3  Sont + LM358",              "sim_akim.py"),
    ("S4  Firmware aritmetigi",       "test_firmware.py"),
]

# S8 ve S9 uzun surer (S9 gercek firmware'i milyonlarca cevrim kosturur).
# `python dogrula.py --hizli` bunlari atlar.
AGIR_ADIMLAR = [
    ("S8  AVR simulatorunun dogrulanmasi", "test_avr.py"),
    ("S9  Kart uctan uca (+ S10 arayuz)",  "sim_kart.py"),
]


def kos(baslik: str, betik: str) -> tuple[bool, str, float]:
    t0 = time.time()
    s = subprocess.run([sys.executable, betik], cwd=BURASI,
                       capture_output=True, text=True, timeout=900)
    return s.returncode == 0, s.stdout, time.time() - t0


def main() -> int:
    print("=" * 78)
    print("  OLCUM KARTI — DOGRULAMA ZINCIRI")
    print("=" * 78)

    sonuclar = []

    for baslik, betik in ADIMLAR:
        print(f"\n{'-' * 78}\n  {baslik}\n{'-' * 78}")
        tamam, cikti, sure = kos(baslik, betik)
        print(cikti.rstrip())
        sonuclar.append((baslik, tamam, sure))

    # --- sema: once uret, sonra ERC, sonra netlist
    print(f"\n{'-' * 78}\n  S5  Sema: uretim + ERC + netlist\n{'-' * 78}")
    t0 = time.time()
    u = subprocess.run([sys.executable, "sema-uret.py"], cwd=BURASI,
                       capture_output=True, text=True, timeout=300)
    print(u.stdout.rstrip())

    erc = subprocess.run(
        [KICAD_CLI, "sch", "erc", "--output", "erc.rpt",
         "--severity-error", "--severity-warning", str(SEMA)],
        cwd=BURASI, capture_output=True, text=True, timeout=300)
    ihlal = [s for s in erc.stdout.splitlines() if "violation" in s.lower()]
    erc_temiz = "Found 0 violations" in erc.stdout
    print(f"  ERC: {ihlal[0].strip() if ihlal else '?'}")

    n = subprocess.run([sys.executable, "netlist_dogrula.py"], cwd=BURASI,
                       capture_output=True, text=True, timeout=300)
    print(n.stdout.rstrip())
    sonuclar.append(("S5  Sema (ERC + netlist)",
                     erc_temiz and n.returncode == 0, time.time() - t0))

    # --- firmware: gercekten derleniyor mu (uyarilar dahil)
    print(f"\n{'-' * 78}\n  S6  Firmware derleme (arduino-cli)\n{'-' * 78}")
    t0 = time.time()
    derleme_tamam = True
    if not ARDUINO_CLI.exists():
        print(f"  arduino-cli bulunamadi: {ARDUINO_CLI}")
        derleme_tamam = False
    else:
        for fqbn in ("arduino:avr:uno", "arduino:avr:nano"):
            d = subprocess.run(
                [str(ARDUINO_CLI), "compile", "--fqbn", fqbn,
                 "--warnings", "all", str(ESKIZ)],
                capture_output=True, text=True, timeout=600)
            uyari = [s for s in (d.stdout + d.stderr).splitlines()
                     if "warning:" in s or "error:" in s]
            flash = re.search(r"Sketch uses (\d+) bytes", d.stdout)
            ram = re.search(r"Global variables use (\d+) bytes", d.stdout)
            ok = d.returncode == 0 and not uyari
            bos = SRAM - int(ram.group(1)) if ram else 0
            print(f"  {'[OK]' if ok else '[!!]'} {fqbn:<20} "
                  f"flash {flash.group(1) if flash else '?':>5} B   "
                  f"SRAM {ram.group(1) if ram else '?':>4} B   "
                  f"bos {bos:>4} B   uyari {len(uyari)}")
            for satir in uyari[:5]:
                print(f"       {satir.strip()}")
            if not ok or bos < EN_AZ_BOS_SRAM:
                derleme_tamam = False
        print(f"  (yigit icin en az {EN_AZ_BOS_SRAM} B bos SRAM sart)")
    sonuclar.append(("S6  Firmware derleme", derleme_tamam, time.time() - t0))

    # --- arayuz mantigi
    print(f"\n{'-' * 78}\n  S7  Arayuz mantigi (node)\n{'-' * 78}")
    t0 = time.time()
    a = subprocess.run(["node", "test_arayuz.js"], cwd=BURASI,
                       capture_output=True, text=True, timeout=300)
    print(a.stdout.rstrip() or a.stderr.rstrip())
    sonuclar.append(("S7  Arayuz mantigi", a.returncode == 0, time.time() - t0))

    # --- agir adimlar: gercek AVR ikilisi kosturuluyor
    if "--hizli" in sys.argv:
        print(f"\n{'-' * 78}\n  S8/S9 atlandi (--hizli)\n{'-' * 78}")
    else:
        for baslik, betik in AGIR_ADIMLAR:
            print(f"\n{'-' * 78}\n  {baslik}\n{'-' * 78}")
            tamam, cikti, sure = kos(baslik, betik)
            print(cikti.rstrip())
            sonuclar.append((baslik, tamam, sure))

    # --- ozet
    print("\n" + "=" * 78)
    print("  OZET")
    print("=" * 78)
    for baslik, tamam, sure in sonuclar:
        print(f"  {'GECTI ' if tamam else 'KALDI '} {baslik:<34} {sure:5.1f} s")

    # ngspice calisma dizinlerini temizle (her kosuda yeniden uretiliyorlar)
    import shutil
    for d in BURASI.glob("_s[0-9]*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)

    kalan = [b for b, t, _ in sonuclar if not t]
    print()
    if kalan:
        print(f"  {len(kalan)} adim BASARISIZ: {', '.join(kalan)}")
        return 1
    print("  Tum dogrulamalar gecti — kart kurulmaya hazir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
