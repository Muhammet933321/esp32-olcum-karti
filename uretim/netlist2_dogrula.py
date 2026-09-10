# -*- coding: utf-8 -*-
"""A3 — Asama 2 semasinin netlist'ini tasarima karsi dogrular.

NEDEN GEREKLI: ERC bir diyodun TERS baglandigini yakalayamaz — iki ucu da
bagli oldugu icin sema temiz gorunur. Asama 1'de tam olarak bu oldu: ERC
0 ihlal verirken iki koruma diyodu da tersti.

Burada ayrica ADS1115 ADRES pinleri dogrulaniyor: U2 -> GND (0x48),
U3 -> +3V3 (0x49). Ters olsa iki cip ayni adresi paylasir ve I2C coker.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from netlist_dogrula import netleri_oku                 # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
SEMA = BURASI.parent / "arsiv" / "asama2" / "sema2" / "olcum-karti-a2.kicad_sch"
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

BEKLENEN = {
    "+3V3": {"J4.1", "R1.1", "R8.1", "R9.1", "U2.8(VDD)", "U3.1(ADDR)",
             "U3.8(VDD)"},
    "/TL_RAY": {"C1.1", "D1.1(K)", "D3.1(K)", "R1.2", "U1.1(REF)", "U1.3(K)"},
    "/V_GIRIS": {"J1.1", "R2.1"},
    "/V_DUGUM": {"C2.1", "D1.2(A)", "D2.1(K)", "R2.2", "R3.1", "U3.4(AIN0)"},
    "/YUK_EKSI": {"J2.1", "R4.2", "RS.1"},
    "/I_ARTI": {"C3.1", "R4.1", "U2.4(AIN0)"},
    "/I_EKSI": {"C3.2", "R5.1", "U2.5(AIN1)"},
    "/SKOP_GIRIS": {"J3.1", "R6.1"},
    "/SKOP": {"C4.1", "D3.2(A)", "D4.1(K)", "J4.5", "R6.2", "R7.1"},
    "/SDA": {"J4.3", "R8.2", "U2.9(SDA)", "U3.9(SDA)"},
    "/SCL": {"J4.4", "R9.2", "U2.10(SCL)", "U3.10(SCL)"},
    "/ALERT": {"J4.6", "U2.2(ALERT/RDY)"},
    "GND": {"C1.2", "C2.2", "C4.2", "D2.2(A)", "D4.2(A)", "J1.2", "J2.2",
            "J3.2", "J4.2", "R3.2", "R5.2", "R7.2", "RS.2", "U1.2(A)",
            "U2.1(ADDR)", "U2.3(GND)", "U2.6(AIN2)", "U2.7(AIN3)",
            "U3.3(GND)", "U3.5(AIN1)", "U3.6(AIN2)", "U3.7(AIN3)"},
}

# ERC'nin GOREMEDIGI kurallar — yon, polarite, adres
KRITIK = [
    ("D1 gerilim kelepcesi: KATOT TL rayinda",   "/TL_RAY",  "D1.1(K)"),
    ("D1 gerilim kelepcesi: ANOT olcum dugumunde", "/V_DUGUM", "D1.2(A)"),
    ("D2 alt kelepce: KATOT olcum dugumunde",    "/V_DUGUM", "D2.1(K)"),
    ("D2 alt kelepce: ANOT GND'de",              "GND",      "D2.2(A)"),
    ("D3 skop kelepcesi: KATOT TL rayinda",      "/TL_RAY",  "D3.1(K)"),
    ("D3 skop kelepcesi: ANOT skop dugumunde",   "/SKOP",    "D3.2(A)"),
    ("D4 skop alt kelepce: KATOT skop dugumunde", "/SKOP",   "D4.1(K)"),
    ("D4 skop alt kelepce: ANOT GND'de",         "GND",      "D4.2(A)"),
    ("TL431: ANOT GND'de",                       "GND",      "U1.2(A)"),
    ("TL431: REF katoda bagli (2 uclu sont kipi)", "/TL_RAY", "U1.1(REF)"),
    ("ADS #1 (akim) adresi 0x48: ADDR -> GND",   "GND",      "U2.1(ADDR)"),
    ("ADS #2 (gerilim) adresi 0x49: ADDR -> +3V3", "+3V3",   "U3.1(ADDR)"),
    ("ADS #1 AIN0 sontun ARTI ucunda",           "/I_ARTI",  "U2.4(AIN0)"),
    ("ADS #1 AIN1 sontun EKSI ucunda",           "/I_EKSI",  "U2.5(AIN1)"),
    ("ADS #2 AIN0 gerilim bolucusunde",          "/V_DUGUM", "U3.4(AIN0)"),
    ("Osiloskop ESP32 GPIO4'e gidiyor (ADS'e DEGIL)", "/SKOP", "J4.5"),
    ("Kullanilmayan ADS girisleri GND'de (acikta degil)", "GND", "U2.6(AIN2)"),
    ("Kullanilmayan ADS girisleri GND'de (acikta degil)", "GND", "U3.7(AIN3)"),
    ("ADS #1 beslemesi +3V3 (5 V DEGIL — I2C seviyesi icin)", "+3V3", "U2.8(VDD)"),
]


def main() -> int:
    hedef = BURASI / "netlist2.net"
    s = subprocess.run(
        [KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr",
         "--output", str(hedef), str(SEMA)],
        capture_output=True, text=True, timeout=120)
    if not hedef.exists():
        print("netlist uretilemedi:\n" + s.stdout + s.stderr)
        return 1

    netler = netleri_oku(hedef)
    gecti = kaldi = 0

    print("A3 — Asama 2 netlist'i tasarima uyuyor mu")
    print()
    for ad, beklenen in BEKLENEN.items():
        alinan = netler.get(ad, set())
        tamam = alinan == beklenen
        if tamam:
            gecti += 1
        else:
            kaldi += 1
        print(f"  {'[OK]' if tamam else '[!!]'} net {ad:<14} {len(beklenen)} pin")
        if not tamam:
            print(f"        eksik : {sorted(beklenen - alinan)}")
            print(f"        fazla : {sorted(alinan - beklenen)}")

    print()
    print("  ERC'nin GOREMEDIGI kurallar (yon / polarite / adres):")
    for ad, net, pin in KRITIK:
        tamam = pin in netler.get(net, set())
        if tamam:
            gecti += 1
        else:
            kaldi += 1
        print(f"  {'[OK]' if tamam else '[!!]'}   {ad:<48} {pin} -> {net}")

    # bagli olmayan uclar: yalnizca U3'un ALERT'i olmali (bilerek)
    bos = [a for a in netler if a.startswith("unconnected-")]
    tamam = bos == ["unconnected-(U3-ALERT{slash}RDY-Pad2)"]
    gecti += tamam
    kaldi += not tamam
    print(f"  {'[OK]' if tamam else '[!!]'}   {'Yalniz U3.ALERT bilerek bos':<48} {bos}")

    print()
    print(f"  {gecti}/{gecti + kaldi} dogrulama gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
