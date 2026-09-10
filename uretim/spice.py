# -*- coding: utf-8 -*-
"""ngspice.dll surucusu — KiCad'in tasidigi paylasimli kutuphaneyi ctypes ile surer.

Sistem Python'undan calisir; ngspice ayrica kurulmasina gerek yok.
Her devre ayri bir alt surecte kosar, boylece ngspice'in ic durumu
simulasyonlar arasinda birbirine karismaz.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gecici                                    # noqa: E402

KICAD_BIN = r"C:\Program Files\KiCad\10.0\bin"

# Alt surecte kosan surucu. Devreyi kaynak alir, wrdata ciktilarini birakir.
_SURUCU = r'''
import ctypes, os, sys
from ctypes import c_char_p, c_int, c_void_p, CFUNCTYPE

os.add_dll_directory(r"{bin}")
ng = ctypes.CDLL(r"{bin}\ngspice.dll")

satirlar = []
SendChar = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
Exit = CFUNCTYPE(c_int, c_int, c_int, c_int, c_int, c_void_p)

@SendChar
def yakala(mesaj, kimlik, veri):
    satirlar.append(mesaj.decode("utf-8", "replace"))
    return 0

@Exit
def cikis(durum, acil, kapat, kimlik, veri):
    return 0

ng.ngSpice_Init.argtypes = [SendChar, c_void_p, Exit, c_void_p, c_void_p,
                            c_void_p, c_void_p]
ng.ngSpice_Init(yakala, None, cikis, None, None, None, None)
ng.ngSpice_Command(("source " + sys.argv[1]).encode())

with open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write("\n".join(satirlar))
'''


def kos(netlist: str, calisma_dizini: Path | None = None) -> tuple[str, Path]:
    """Netlist'i kosturur. (ngspice_kayit, calisma_dizini) dondurur.

    Netlist icindeki `wrdata <ad>` ciktilari calisma dizinine yazilir.
    """
    dizin = calisma_dizini or gecici.dizin("spice-")
    dizin.mkdir(parents=True, exist_ok=True)

    (dizin / "devre.cir").write_text(netlist, encoding="utf-8")
    (dizin / "_surucu.py").write_text(
        _SURUCU.format(bin=KICAD_BIN), encoding="utf-8")

    sonuc = subprocess.run(
        [sys.executable, "_surucu.py", "devre.cir", "kayit.txt"],
        cwd=dizin, capture_output=True, text=True, timeout=180)
    if sonuc.returncode != 0:
        raise RuntimeError(f"ngspice surucusu coktu:\n{sonuc.stderr}")

    kayit = (dizin / "kayit.txt").read_text(encoding="utf-8", errors="replace")
    return kayit, dizin


def oku(dosya: Path) -> list[tuple[float, ...]]:
    """ngspice `wrdata` ciktisini okur. Her satir bir kayit."""
    satirlar = []
    for ham in dosya.read_text(encoding="utf-8", errors="replace").splitlines():
        parcalar = ham.split()
        if not parcalar:
            continue
        try:
            satirlar.append(tuple(float(p) for p in parcalar))
        except ValueError:
            continue          # basliksa atla
    return satirlar


def degerler(dosya: Path) -> list[tuple[float, ...]]:
    """`wrdata` her degisken icin (x, y) cifti yazar.

    Bu yardimci x sutunlarini atar; geriye (x, y1, y2, ...) kalir.
    Ornek: `wrdata f.txt v(a) v(b)` -> her satir (x, v(a), v(b)).
    """
    cikti = []
    for satir in oku(dosya):
        cikti.append((satir[0],) + satir[1::2])
    return cikti


# ---------------------------------------------------------------- dogrulama

class Rapor:
    """Basit iddia toplayici — her simulasyon sonucunu beklenene karsi olcer."""

    def __init__(self) -> None:
        self.satirlar: list[tuple[bool, str]] = []

    def esit(self, ad: str, olculen: float, beklenen: float,
             tolerans: float, birim: str = "") -> bool:
        """Bagil tolerans (orn. 0.02 = %2) ile karsilastirir."""
        sapma = abs(olculen - beklenen) / abs(beklenen) if beklenen else abs(olculen)
        gecti = sapma <= tolerans
        self.satirlar.append((gecti, (
            f"{ad:44} olculen {olculen:>12.4g}{birim}  "
            f"beklenen {beklenen:>10.4g}{birim}  sapma %{sapma * 100:5.2f}")))
        return gecti

    def kosul(self, ad: str, dogru_mu: bool, aciklama: str = "") -> bool:
        self.satirlar.append((dogru_mu, f"{ad:44} {aciklama}"))
        return dogru_mu

    def bilgi(self, metin: str) -> None:
        self.satirlar.append((None, metin))

    def yazdir(self) -> bool:
        for gecti, metin in self.satirlar:
            im = "     " if gecti is None else ("[OK] " if gecti else "[!!] ")
            print(im + metin)
        basarisiz = [s for g, s in self.satirlar if g is False]
        print()
        toplam = sum(1 for g, _ in self.satirlar if g is not None)
        print(f"  {toplam - len(basarisiz)}/{toplam} dogrulama gecti")
        return not basarisiz
