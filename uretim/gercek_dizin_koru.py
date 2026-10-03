# -*- coding: utf-8 -*-
"""Testler kullanicinin GERCEK PC uygulamasi dizinine (%LOCALAPPDATA%\\olcum-karti) yazmasin.

4B gercek kart sinamasinda bulundu (2026-10-03): kullanicinin cihaz dizininde sahte test kartinin
("0011223344556677", ad "kopru-3") cihaz dosyasi vardi. Test dizini yalniz OLCUM_CIHAZ_DIZIN ile
yonlendiriyordu; o yolu atlatan bir mutasyon (ya da kod kusuru) varsayilana, yani GERCEK
%LOCALAPPDATA%'ya dusuyordu.

Iki katman:
  1. OLCUM_PC_DIZIN VE OLCUM_CIHAZ_DIZIN ikisi de gecici dizinlere — biri atlatilsa obur yonlendirme
     yine gecici dizine dusurur. (LOCALAPPDATA'nin kendisi DEGISTIRILMEZ: Arduino cekirdegi
     `%LOCALAPPDATA%\\Arduino15`'te, arayuz-uret.py ve B72.P1 onu oradan okuyor.)
  2. Test sonunda gercek dizinin dokumu OLCULUR (iddia). Degistiyse iddia KIRMIZI ve test sirasinda
     beliren dosyalar geri alinir (yalniz testin baslangicinda OLMAYANLAR silinir).

    import gercek_dizin_koru
    _KORUMA = gercek_dizin_koru.koru()          # ice aktarma aninda
    ...
    gercek_dizin_koru.denetle(_KORUMA, ok)      # ozetten once
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

AD = "olcum-karti"


def _dokum(kok: Path) -> dict:
    if not kok or not kok.is_dir():
        return {}
    d = {}
    for p in sorted(kok.rglob("*")):
        try:
            st = p.stat()
        except OSError:
            continue
        d[str(p.relative_to(kok))] = (p.is_dir(), st.st_size, st.st_mtime_ns)
    return d


def koru() -> dict:
    """Gercek dizinin dokumunu al; PC uygulamasinin iki dizin yonlendirmesini gecici dizinlere cevir."""
    yerel = os.environ.get("LOCALAPPDATA")
    kok = Path(yerel) / AD if yerel else None
    once = _dokum(kok)
    gecici = Path(tempfile.mkdtemp(prefix="olcum-test-pc-"))
    os.environ["OLCUM_PC_DIZIN"] = str(gecici / "pc")
    os.environ["OLCUM_CIHAZ_DIZIN"] = str(gecici / "cihaz")
    return {"kok": kok, "once": once, "gecici": gecici}


def denetle(koruma: dict, ok) -> None:
    kok = koruma["kok"]
    sonra = _dokum(kok)
    once = koruma["once"]
    yeni = sorted(set(sonra) - set(once))
    degisen = sorted(k for k in set(sonra) & set(once) if sonra[k] != once[k] and not sonra[k][0])
    silinen = sorted(set(once) - set(sonra))
    # Geri al: yalniz test sirasinda BELIREN dosya/dizinler (derinden sigaya); onceden olana dokunma.
    for ad in sorted(yeni, key=lambda s: -s.count(os.sep)):
        p = kok / ad
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()
        except OSError:
            pass
    ok("[!] Test kullanicinin GERCEK %LOCALAPPDATA%\\olcum-karti dizinine dokunmadi "
       "(sahte kartin cihaz dosyasi gercek dizine dusmesin; belirenler geri alindi)",
       not yeni and not degisen and not silinen,
       f"yeni={yeni[:3]} degisen={degisen[:3]} silinen={silinen[:3]}")
