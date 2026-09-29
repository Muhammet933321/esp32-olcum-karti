# -*- coding: utf-8 -*-
"""B71 — KAYIT MOTORU: bicim · noktaci · gunluk · yazici · elektrik kesme.

    python test_kayit.py                  # zincir adimi
    python test_kayit.py --kesinti 1000   # uzun elektrik kesme denemesi

Gercek C kodu (kod/olcum-karti-a3/kayit_*.h) avr-gcc ile derlenip AVR
emulatorunde, EMULE NOR FLASIN (avr/nor_flas.py) ustunde kosuyor. Python
cozucu (kopru/kayit_bicim.py) ayni baytlari BAGIMSIZ olarak cozuyor; iki
taraf ayni sonucu vermezse kirmizi.
Tasarim: tasarim/2026-09-29-yazilim-sistemi.md §5
Plan:    tasarim/2026-09-29-plan-1a1-kayit-motoru.md

Beklenen degerler analitik ya da elle hesaplanmis; C kodunun Python'da
yeniden yazilmis bir kopyasindan GELMIYOR. Tek istisna `f32`: sonucu degil
float32 YUVARLAMASINI taklit ediyor.
"""
from __future__ import annotations

import argparse
import random
import struct
import subprocess
import sys
import zlib
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr.nor_flas import NorFlas, A0, A1, A2, VERI, KOMUT, SIL   # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


# ── B71.N · emule NOR flas ─────────────────────────────────────────────
class _Cpu:
    def __init__(self):
        self.cevrim = 0
        self.gc_oku = {}
        self.gc_yaz = {}


class _Kart:
    def __init__(self):
        self.cpu = _Cpu()


def bolum_nor() -> None:
    print("\n── B71.N  emule NOR flas")
    k = _Kart()
    f = NorFlas(1024, sektor=512, sil_cevrim=100)
    f.tak(k)
    y, o = k.cpu.gc_yaz, k.cpu.gc_oku

    def adres(a: int) -> None:
        y[A0](a & 0xFF)
        y[A1]((a >> 8) & 0xFF)
        y[A2]((a >> 16) & 0xFF)

    ok("B71.N1 yeni flas tamamen 0xFF", f.bellek == b"\xff" * 1024)
    adres(0x10)
    y[VERI](0x0F)
    adres(0x10)
    y[VERI](0xF0)
    ok("B71.N2 yazma yalniz 1->0 yapar (0x0F sonra 0xF0 = 0x00)",
       f.bellek[0x10] == 0x00, f"bayt={f.bellek[0x10]:#04x}")
    adres(0x10)
    v = o[VERI]()
    ok("B71.N3 okuma bayti verir ve adresi ilerletir", v == 0 and f.adres == 0x11)
    f.bellek[0x200:0x400] = b"\x00" * 512
    adres(0x200)
    y[KOMUT](SIL)
    ok("B71.N4 silme ZAMAN alir: hemen sonra mesgul", o[KOMUT]() == 1)
    k.cpu.cevrim += 100
    ok("B71.N5 sil_cevrim sonra sektor 0xFF ve mesgul degil",
       o[KOMUT]() == 0 and f.bellek[0x200:0x400] == b"\xff" * 512)
    f.bellek[0:512] = b"\x00" * 512
    adres(0)
    y[KOMUT](SIL)
    f.kes(random.Random(1))
    yari = bytes(f.bellek[0:512])
    ok("B71.N6 kesilen silme sektoru YARIM birakir (ne hepsi 0xFF ne hepsi eski)",
       yari != b"\xff" * 512 and yari != b"\x00" * 512 and f.kesilen_silme == 1,
       f"0xFF={yari.count(0xFF)} 0x00={yari.count(0)}")
    try:
        f.tak(k)
        adres(1024)
        o[VERI]()
        ok("B71.N7 alan disi okuma sessiz gecmez", False)
    except IndexError:
        ok("B71.N7 alan disi okuma sessiz gecmez", True)


BOLUMLER = [bolum_nor]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kesinti", type=int, default=120,
                    help="elektrik kesme denemesi sayisi")
    arg = ap.parse_args()
    for b in BOLUMLER:
        if b.__name__ == "bolum_kesinti":
            b(arg.kesinti)
        else:
            b()
    print(f"\nB71: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
