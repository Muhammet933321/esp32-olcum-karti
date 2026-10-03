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


def kopru_calisiyor(port: int = 8770) -> bool:
    """Bu bilgisayarda GERCEK PC koprusu (pc.py) acik mi? (`/durum` imzasi: `kart` + `skop_arsiv`)"""
    import json
    import urllib.request
    try:
        acici = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with acici.open(f"http://127.0.0.1:{port}/durum", timeout=1.5) as y:
            d = json.load(y)
        return isinstance(d, dict) and "kart" in d and "skop_arsiv" in d
    except Exception:                                   # noqa: BLE001
        return False


def denetle(koruma: dict, ok, kopru_acik=kopru_calisiyor) -> None:
    """4G (gercek kart kabulunde bulundu): kullanicinin koprusu (Baslangic kisayolu, varsayilan
    ONAYLI esitleme) acikken o da bu dizine YAZAR — yeni `akis-<n>` arsivi, gunun `.satir`'i,
    bildirim onbellegi. Geri alma onlari da SILERDI (onayli kayit kartta da temizlenebilir: veri
    kaybi). Kopru aciksa geri alma YAPILMAZ; iddia yine kirmizi ve sebebi soyler."""
    kok = koruma["kok"]
    sonra = _dokum(kok)
    once = koruma["once"]
    yeni = sorted(set(sonra) - set(once))
    degisen = sorted(k for k in set(sonra) & set(once) if sonra[k] != once[k] and not sonra[k][0])
    silinen = sorted(set(once) - set(sonra))
    # Geri al: yalniz test sirasinda BELIREN dosya/dizinler (derinden sigaya); onceden olana dokunma.
    kopru = bool(yeni or degisen or silinen) and kopru_acik()
    for ad in ([] if kopru else sorted(yeni, key=lambda s: -s.count(os.sep))):
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
       f"yeni={yeni[:3]} degisen={degisen[:3]} silinen={silinen[:3]}"
       + (" — GERCEK kopru acik: degisiklik onun olabilir, geri alma YAPILMADI; zinciri kopru kapaliyken "
          "kosun (`python kopru/pc.py --durdur`)" if kopru else ""))
