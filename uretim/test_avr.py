# -*- coding: utf-8 -*-
"""S8 — AVR simulatorunun KENDISINI dogrular.

Bir simulator, dogrulanmadan hicbir sey kanitlamaz. Burada sonucu bagimsiz
olarak bilinen bir AVR programi gercek avr-gcc ile derlenip simulatorde
kosturuluyor; her sayi Python tarafinda IEEE-754 ile ayrica hesaplanip
BIT BIREBIR karsilastiriliyor.

Yazilim float kutuphanesi (avr-libc) bilerek zorlaniyor: tek bir toplama bile
onlarca kaydirma, dondurme, elde-ile-toplama ve isaretli dallanma calistirir.
Bunlar tutuyorsa cekirdegin bayrak mantigi da tutuyor demektir.
"""
from __future__ import annotations

import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from avr import elf, mega328                      # noqa: E402
from avr.cekirdek import Cekirdek                 # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"

f32 = np.float32


def b(x) -> str:
    """float32 -> onaltilik bit dizisi (C tarafiyla ayni gosterim)."""
    return f"{struct.unpack('<I', struct.pack('<f', f32(x)))[0]:08x}"


def bol(a: int, n: int) -> int:
    """C'nin tam sayi bolmesi: sifira dogru kirpar (Python asagi yuvarlar)."""
    q = abs(a) // abs(n)
    return q if (a >= 0) == (n >= 0) else -q


def mod(a: int, n: int) -> int:
    return a - n * bol(a, n)


def derle(kaynak: Path, hedef: Path) -> None:
    s = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os",
         "-std=gnu99", "-o", str(hedef), str(kaynak), "-lm"],
        capture_output=True, text=True, timeout=300)
    if s.returncode != 0:
        raise SystemExit("avr-gcc derleyemedi:\n" + s.stderr)


def main() -> int:
    print("S8 — AVR simulatorunun dogrulanmasi")
    print()

    if not AVR_GCC.exists():
        print(f"  avr-gcc bulunamadi: {AVR_GCC}")
        return 1

    with tempfile.TemporaryDirectory() as d:
        cikti = Path(d) / "ornek.elf"
        derle(BURASI / "avr" / "ornek_cekirdek.c", cikti)
        flash, giris = elf.flash_goruntusu(cikti)
        boy = sum(1 for x in flash if x)
        print(f"  derlendi: {cikti.name}, flash'a yuklenen ~{boy} bayt, "
              f"giris noktasi sozcuk {giris // 2:#x}")

        kart = mega328.Kart(flash, Cekirdek)
        # program sonsuz donguye girer; sabit bir cevrim butcesi ver
        kart.cevrim_kadar_kos(120_000_000)

    ciktilar = {}
    for satir in kart.satirlar():
        p = satir.split(None, 1)
        if len(p) == 2:
            ciktilar[p[0]] = p[1].strip()

    if "BITTI" not in kart.tx.decode("ascii", "replace"):
        print("  [!!] program bitmedi — cikti:")
        print("      " + kart.tx.decode("ascii", "replace")[-300:].replace("\n", "\n      "))
        return 1

    # ---------------------------------------------------- beklenen degerler
    u8a, u8b = 200, 100
    i8a, i8b = -128, 3
    u16a, u16b = 50000, 40000
    i16a, i16b = -30000, 12345
    u32a, u32b = 3000000000, 1500000000
    i32a, i32b = -2000000000, 7
    u64a = 1234567890123456789
    fa, fb, fc, fd = f32(3.14159265), f32(-2.718281828), f32(1e-7), f32(12345.678)

    lsb = f32(f32(2.470) / f32(1024.0))
    v_adim = f32(lsb * f32(11.0))
    i_adim = f32(f32(lsb / f32(7.9118)) / f32(10.0))
    volt = f32(f32(512) * v_adim)
    amper = f32(f32(300) * i_adim)
    watt = f32(volt * amper)

    beklenen = {
        "u8add":  f"{(u8a + u8b) & 0xFF:02x}",
        "u8sub":  f"{(u8b - u8a) & 0xFF:02x}",
        "u8mul":  f"{u8a * u8b & 0xFFFF:04x}",
        "i8neg":  f"{(-i8a) & 0xFF:02x}",
        "i8div":  f"{bol(i8a, i8b) & 0xFF:02x}",
        "i8mod":  f"{mod(i8a, i8b) & 0xFF:02x}",
        "u16add": f"{(u16a + u16b) & 0xFFFF:04x}",
        "u16mul": f"{u16a * u16b & 0xFFFFFFFF:08x}",
        "i16mul": f"{(i16a * i16b) & 0xFFFFFFFF:08x}",
        "i16shr": f"{(i16a >> 3) & 0xFFFF:04x}",
        "u32add": f"{(u32a + u32b) & 0xFFFFFFFF:08x}",
        "u32mul": f"{(u32a * u32b) & 0xFFFFFFFF:08x}",
        "u32div": f"{u32a // 7:08x}",
        "i32div": f"{bol(i32a, i32b) & 0xFFFFFFFF:08x}",
        "i32mod": f"{mod(i32a, i32b) & 0xFFFFFFFF:08x}",
        "u32shl": f"{(u32b << 3) & 0xFFFFFFFF:08x}",
        "u64mul": f"{(u32a * u32b) & 0xFFFFFFFFFFFFFFFF:016x}",
        "u64add": f"{(u64a + u32a * 220) & 0xFFFFFFFFFFFFFFFF:016x}",
        "u64div": f"{u64a // 1000000:016x}",
        "fadd":   b(fa + fb),
        "fsub":   b(fa - fb),
        "fmul":   b(fa * fb),
        "fdiv":   b(fa / fb),
        "fdivs":  b(fc / f32(3.0)),
        "fsqrt":  b(np.sqrt(fd)),
        "fi2f":   b(f32(u32a)),
        "ff2i":   f"{int(fd):08x}",
        "fneg":   b(f32(-fa) * fc),
        "fcmp":   "01",
        "v_adim": b(v_adim),
        "i_adim": b(i_adim),
        "volt":   b(volt),
        "amper":  b(amper),
        "watt":   b(watt),
        "guc_uW": f"{int(f32(watt * f32(1e6))):08x}",
        "atof":   b(12.345),
        "atol":   f"{500:08x}",
        "dtostrf": "3.1416",
        "ltoa":   "-123456",
    }

    gecti = kaldi = 0
    print()
    print(f"  {'alan':<9} {'AVR simulatoru':>18}  {'bagimsiz hesap':>18}   sonuc")
    print("  " + "-" * 68)
    for ad, bek in beklenen.items():
        alinan = ciktilar.get(ad, "<yok>")
        if ad == "dtostrf":
            tamam = alinan.strip() == bek
        else:
            tamam = alinan == bek
        if tamam:
            gecti += 1
        else:
            kaldi += 1
        print(f"  {ad:<9} {alinan:>18}  {bek:>18}   {'OK' if tamam else 'FARK'}")

    print()
    print(f"  {gecti}/{gecti + kaldi} deger bit birebir tuttu")
    print(f"  simulatorde islenen cevrim: {kart.cpu.cevrim:,} "
          f"({kart.cpu.cevrim / mega328.F_CPU * 1000:.1f} ms gercek zaman)")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
