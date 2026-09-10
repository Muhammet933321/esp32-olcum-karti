# -*- coding: utf-8 -*-
"""A6 — Osiloskop olcum matematiginin AVR emulatorunde dogrulanmasi.

    python test_skop_olcum.py

`skop_olc()` fonksiyonu `kod/olcum-karti-a2/olcum2.h` icinde ve PLATFORM
BAGIMSIZ yazildi. Burada GERCEK KOD, avr-gcc ile derlenip 39/39 bit-birebir
dogrulanmis AVR emulatorunde (test_avr.py) kosturuluyor.

Beklenen degerler bir YENIDEN-UYGULAMADAN gelmiyor: sentetik dalgalarin
frekansi, genligi ve duty'si ANALITIK OLARAK biliniyor.

    kare   periyot 80 ornek @ 10 kSa/s -> 125.00 Hz, %50 duty
    ucgen  periyot 100 ornek           -> 100.00 Hz, %50 duty
    sinus  periyot 64 ornek            -> 156.25 Hz, %50 duty
    duz    olcum yapilamaz             -> hepsi 0
    %25    periyot 80, 20 ornek ustte  -> 125.00 Hz, %25 duty
"""
from __future__ import annotations

import math
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr import mega328                          # noqa: E402
from avr.cekirdek import Cekirdek                # noqa: E402
from avr.elf import flash_goruntusu          # noqa: E402
import gecici                                   # noqa: E402

BURASI = Path(__file__).parent
KOK = BURASI.parent
AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"  {ek}" if ek else ""))


def yakin(ad: str, olculen: float, beklenen: float, tol: float,
          birim: str = "") -> None:
    fark = abs(olculen - beklenen)
    ok(ad, fark <= tol,
       f"{olculen:.6g}{birim} ~ {beklenen:.6g}{birim} (fark {fark:.3g})")


def cozf(h: str) -> float:
    """32 bitlik hex bit desenini float'a cevirir."""
    return struct.unpack(">f", bytes.fromhex(h))[0]


def kostur() -> dict:
    """ornek_skop.c'yi derler, emulatorde kosturur, satirlari cozer."""
    gec_dizin = gecici.dizin("skopolc_")
    elf = gec_dizin / "ornek_skop.elf"
    d = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os",
         "-std=gnu11", "-Wall", "-Wextra",
         f"-I{KOK / 'arsiv' / 'asama2' / 'olcum-karti-a2'}",
         "-o", str(elf), str(BURASI / "avr" / "ornek_skop.c"), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if d.returncode != 0:
        print(d.stderr)
        raise SystemExit("avr-gcc derleyemedi")

    uyari = [x for x in d.stderr.splitlines() if "warning:" in x]
    ok("olcum2.h skop katmani AVR'de uyarisiz derlendi", not uyari,
       f"{len(uyari)} uyari")
    if uyari:
        for u in uyari[:5]:
            print("       " + u)

    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    kart.cevrim_kadar_kos(120_000_000)
    metin = kart.tx.decode("ascii", "replace")
    ok("Program tamamlandi (BITTI)", "BITTI" in metin,
       f"{kart.cpu.cevrim:,} cevrim".replace(",", " "))

    sonuc = {}
    for sat in metin.splitlines():
        p = sat.split()
        if len(p) >= 2 and p[0] == "VA":
            sonuc["VA"] = cozf(p[1])
        elif len(p) >= 24 and p[0] in ("KARE", "UCGN", "SINS", "DUZ", "D25"):
            d2 = {}
            i = 1
            while i + 1 < len(p):
                anahtar, deger = p[i], p[i + 1]
                d2[anahtar] = (int(deger) if anahtar in ("cv", "n")
                               else cozf(deger))
                i += 2
            sonuc[p[0]] = d2
    return sonuc


def main() -> int:
    print("=" * 78)
    print("  A6  OSILOSKOP OLCUM MATEMATIGI  (gercek kod, AVR emulatorunde)")
    print("=" * 78)
    print("\n--- 1. Derleme ve kosum -------------------------------------------")
    s = kostur()

    ok("Emulator tum dalgalari isledi",
       all(k in s for k in ("VA", "KARE", "UCGN", "SINS", "DUZ", "D25")),
       f"{len(s) - 1}/5 dalga")
    if len(s) < 6:
        return 1

    # volt/adim: olcum2.h'deki SKOP_VOLT_ADIM
    va = s["VA"]
    print("\n--- 2. Volt/adim ---------------------------------------------------")
    beklenen_va = 3.10 / 4095.0 * 15.70588235
    yakin("SKOP_VOLT_ADIM olcum2.h ile ayni", va, beklenen_va, 1e-9, " V")
    yakin("Tam olcek 48.7 V (tasarim2.py ile ayni)", va * 4095, 48.7, 0.1, " V")

    print("\n--- 3. KARE dalga: 80 ornek periyot, 5 cevrim ----------------------")
    k = s["KARE"]
    yakin("Frekans = 10000/80", k["f"], 125.0, 0.05, " Hz")
    yakin("Periyot = 1/125", k["T"], 1.0 / 125.0, 1e-7, " s")
    yakin("Vpp = 3600 kod", k["pp"], 3600 * va, 1e-4, " V")
    yakin("Vmax = 3800 kod", k["mx"], 3800 * va, 1e-4, " V")
    yakin("Vmin = 200 kod", k["mn"], 200 * va, 1e-4, " V")
    yakin("Vort = 2000 kod (simetrik kare)", k["av"], 2000 * va, 1e-3, " V")
    yakin("Duty = %50", k["du"], 50.0, 1.5, " %")
    # 400 ornekte 5 periyot var ama yukselen kenarlar i = 0, 80, 160, 240, 320'de.
    # i=0'daki kenarin ONCESINDE ornek olmadigi icin algilanamaz -> 4 kesisim,
    # yani 3 tam cevrim. Periyot yine (320-80)/3 = 80 ornek, frekans tam 125 Hz.
    ok("Cevrim 3 (i=0'daki kenar oncesi ornek yok, algilanamaz)",
       k["cv"] == 3, f"{k['cv']}")
    # Kare dalgada RMS: sqrt((3800^2 + 200^2)/2) kod
    rms_kod = math.sqrt((3800 ** 2 + 200 ** 2) / 2)
    yakin("Vrms = kare dalga RMS'i", k["rm"], rms_kod * va, 2e-3, " V")
    # AC RMS = tepe genligi = 1800 kod
    yakin("Vac = 1800 kod (AC bileseni)", k["ac"], 1800 * va, 2e-3, " V")

    print("\n--- 4. UCGEN dalga: 100 ornek periyot, 4 cevrim --------------------")
    u = s["UCGN"]
    yakin("Frekans = 10000/100", u["f"], 100.0, 0.05, " Hz")
    yakin("Vpp = 3600 kod", u["pp"], 3600 * va, 5e-3, " V")
    yakin("Duty = %50", u["du"], 50.0, 2.0, " %")
    # Ucgen AC RMS = genlik/sqrt(3) = 1800/1.732
    yakin("Vac = ucgen RMS'i (genlik/√3)", u["ac"], 1800 / math.sqrt(3) * va,
          0.02, " V")

    print("\n--- 5. SINUS: 64 ornek periyot, 6 cevrim ---------------------------")
    n = s["SINS"]
    yakin("Frekans = 10000/64", n["f"], 156.25, 0.1, " Hz")
    yakin("Vpp = 3000 kod", n["pp"], 3000 * va, 0.02, " V")
    yakin("Vort = 2048 kod (merkez)", n["av"], 2048 * va, 0.02, " V")
    yakin("Duty = %50", n["du"], 50.0, 2.0, " %")
    # Sinus AC RMS = genlik/sqrt(2) = 1500/1.414
    yakin("Vac = sinus RMS'i (genlik/√2)", n["ac"], 1500 / math.sqrt(2) * va,
          0.02, " V")

    print("\n--- 6. DUZ CIZGI: olcum YAPILAMAMALI -------------------------------")
    d = s["DUZ"]
    ok("Frekans 0 (periyodik sinyal yok)", d["f"] == 0.0, f"{d['f']}")
    ok("Cevrim 0", d["cv"] == 0, f"{d['cv']}")
    yakin("Vpp 0", d["pp"], 0.0, 1e-6, " V")
    yakin("Vort = 2048 kod", d["av"], 2048 * va, 1e-3, " V")
    yakin("Vac 0 (AC bileseni yok)", d["ac"], 0.0, 1e-3, " V")

    print("\n--- 7. ASIMETRIK KARE: %25 duty ------------------------------------")
    a = s["D25"]
    yakin("Frekans yine 125 Hz", a["f"], 125.0, 0.05, " Hz")
    yakin("Duty = %25", a["du"], 25.0, 1.5, " %")
    ok("Duty simetrikten AYIRT EDILIYOR", abs(a["du"] - k["du"]) > 15.0,
       f"%{a['du']:.1f} vs %{k['du']:.1f}")

    print("\n" + "=" * 78)
    print(f"  A6: {gecti}/{gecti + kaldi} kosul gecti")
    print("=" * 78)
    if kaldi:
        print(f"\n  {kaldi} KOSUL BASARISIZ")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
