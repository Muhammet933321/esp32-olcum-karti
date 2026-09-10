# -*- coding: utf-8 -*-
"""S5 — Semanin netlist'ini tasarlanan devreye karsi dogrular.

NEDEN GEREKLI: ERC bir diyodun TERS baglandigini yakalayamaz — iki ucu da
bagli oldugu icin sema "temiz" gorunur. Nitekim bu projede ERC 0 ihlal
verirken her iki koruma diyotu da ters bagliydi; hata ancak netlist'teki
pin islevleri (K / A) okununca ortaya cikti.

Bu betik netlist'i ayristirip her netin hangi pinleri icerdigini, yonlu
parcalarda hangi ucun nereye bagli oldugunu beklenene karsi olcer.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import spice

BURASI = Path(__file__).parent
SEMA = BURASI.parent / "arsiv" / "asama1" / "sema" / "olcum-karti.kicad_sch"
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

# ---------------------------------------------------------------------------
# Tasarlanan devre. Her net -> o nete bagli olmasi gereken pinler.
# Yonlu parcalarda pin islevi de yazili: "D1.1(K)" gibi.
# Simetrik parcalarda (direnc, kondansator) yalnizca parca adi onemli oldugu
# icin pin numarasi "*" olabilir.
BEKLENEN = {
    "+5V": {"R1.1", "D1.1(K)", "U2.8(V+)", "J3.5"},
    "Net-(U1-K)": {"R1.2", "R2.*", "U1.1(REF)", "U1.3(K)"},
    "/AREF": {"R2.*", "C1.1", "J3.3"},
    "/V_GIRIS": {"J1.1", "R3.1"},
    "/A0": {"R3.2", "R4.1", "C2.1", "D1.2(A)", "D2.1(K)", "J3.1"},
    "/YUK_EKSI": {"J2.1", "RS.1", "U2.3(+)"},
    "Net-(U2A--)": {"U2.2(-)", "R5.*", "R6.1"},
    "/A1": {"U2.1", "R5.*", "J3.2"},
    "Net-(U2B--)": {"U2.6(-)", "U2.7"},
    "GND": {"C1.2", "C2.2", "D2.2(A)", "R4.2", "R6.2", "RS.2",
            "U1.2(A)", "U2.4(V-)", "U2.5(+)", "J1.2", "J2.2", "J3.4"},
}

# Devrenin dogru calismasi icin sart olan, ERC'nin goremedigi kurallar.
KRITIK = [
    ("D1 ust kelepce: KATOT +5V'ta", "+5V", "D1.1(K)"),
    ("D1 ust kelepce: ANOT olcum dugumunde", "/A0", "D1.2(A)"),
    ("D2 alt kelepce: KATOT olcum dugumunde", "/A0", "D2.1(K)"),
    ("D2 alt kelepce: ANOT GND'de", "GND", "D2.2(A)"),
    ("TL431: ANOT GND'de", "GND", "U1.2(A)"),
    ("TL431: REF katoda bagli (2 uclu sont kipi)", "Net-(U1-K)", "U1.1(REF)"),
    ("LM358: + girisi sont ustunde", "/YUK_EKSI", "U2.3(+)"),
    ("LM358: - girisi geri besleme dugumunde", "Net-(U2A--)", "U2.2(-)"),
    ("LM358: cikis A1'e gidiyor", "/A1", "U2.1"),
    ("LM358: besleme +5V / GND", "+5V", "U2.8(V+)"),
]


# ---------------------------------------------------------------- ayristirma
def netlist_uret() -> Path:
    hedef = BURASI / "netlist.net"
    sonuc = subprocess.run(
        [KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr",
         "--output", str(hedef), str(SEMA)],
        capture_output=True, text=True, timeout=120)
    if not hedef.exists():
        raise RuntimeError(f"netlist uretilemedi:\n{sonuc.stdout}\n{sonuc.stderr}")
    return hedef


def netleri_oku(dosya: Path) -> dict[str, set[str]]:
    metin = dosya.read_text(encoding="utf-8")
    kisim = metin[metin.index("\t(nets"):]
    netler: dict[str, set[str]] = {}
    # Her (net ...) blogunu parantez sayarak ayikla — regex lookahead son neti kacirir
    i = 0
    while True:
        bas = kisim.find("(net\n", i)
        if bas < 0:
            bas = kisim.find("(net ", i)
        if bas < 0:
            break
        derinlik, j = 0, bas
        while j < len(kisim):
            if kisim[j] == "(":
                derinlik += 1
            elif kisim[j] == ")":
                derinlik -= 1
                if derinlik == 0:
                    break
            j += 1
        blok = kisim[bas:j + 1]
        i = j + 1
        ad_m = re.search(r'\(name "([^"]*)"\)', blok)
        if not ad_m:
            continue
        pinler = set()
        for d in re.finditer(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)'
                             r'(?:\s*\(pinfunction "([^"]*)"\))?', blok):
            ref, no, islev = d.groups()
            if islev and not islev.startswith("Pin_"):
                # "K_1" -> "K",  "V+_8" -> "V+"
                kisa = islev.rsplit("_", 1)[0] if "_" in islev else islev
                pinler.add(f"{ref}.{no}({kisa})")
            else:
                pinler.add(f"{ref}.{no}")
        netler[ad_m.group(1)] = pinler
    return netler


def _esdeger(pin: str) -> str:
    """Simetrik parcalarin pin numarasini yok sayan anahtar."""
    m = re.match(r"([A-Za-z]+\d*)\.(\S+)", pin)
    return f"{m.group(1)}.*" if m else pin


def karsilastir(beklenen: set[str], olculen: set[str]) -> tuple[bool, str]:
    b_joker = {p for p in beklenen if p.endswith(".*")}
    b_kesin = beklenen - b_joker
    kalan = set(olculen)

    eksik = []
    for p in b_kesin:
        if p in kalan:
            kalan.discard(p)
        else:
            eksik.append(p)
    for p in b_joker:
        eslesen = [q for q in kalan if _esdeger(q) == p]
        if eslesen:
            kalan.discard(eslesen[0])
        else:
            eksik.append(p)

    if eksik or kalan:
        return False, (("eksik: " + ", ".join(sorted(eksik)) if eksik else "")
                       + ("  fazla: " + ", ".join(sorted(kalan)) if kalan else ""))
    return True, f"{len(olculen)} pin"


def kosu(rapor: spice.Rapor) -> None:
    rapor.bilgi("S5 — Sema netlist'i tasarlanan devreye uyuyor mu")
    rapor.bilgi("")

    netler = netleri_oku(netlist_uret())

    rapor.kosul("Net sayisi beklendigi gibi",
                len(netler) == len(BEKLENEN),
                f"{len(netler)} net (beklenen {len(BEKLENEN)})")
    rapor.bilgi("")

    for ad, beklenen in BEKLENEN.items():
        if ad not in netler:
            rapor.kosul(f"net {ad}", False, "netlist'te YOK")
            continue
        tamam, aciklama = karsilastir(beklenen, netler[ad])
        rapor.kosul(f"net {ad}", tamam, aciklama)

    fazla = set(netler) - set(BEKLENEN)
    if fazla:
        rapor.kosul("Beklenmeyen net yok", False, f"fazla: {sorted(fazla)}")

    rapor.bilgi("")
    rapor.bilgi("  ERC'nin GOREMEDIGI kritik kurallar (yon/polarite):")
    for aciklama, net, pin in KRITIK:
        rapor.kosul(f"  {aciklama}", pin in netler.get(net, set()),
                    f"{pin} -> {net}")


if __name__ == "__main__":
    r = spice.Rapor()
    kosu(r)
    print()
    raise SystemExit(0 if r.yazdir() else 1)
