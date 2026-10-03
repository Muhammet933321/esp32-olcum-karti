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


CIHAZ = "cihaz"


def gercek_kopru_calisiyor() -> bool:
    """Bu makinede GERCEK bir PC koprusu (127.0.0.1:8770) yanit veriyor mu. O zaman arsiv/, satir/,
    bildirim/ dizinlerindeki degisiklikler koprunun MESRU isidir (4H'de bulundu: geri alma, calisan bir
    koprunun bildirim onbellegini silmisti)."""
    import urllib.request
    try:
        acici = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        r = urllib.request.Request("http://127.0.0.1:8770/durum", headers={"Host": "olcum.localhost:8770"})
        with acici.open(r, timeout=1.0) as y:
            return y.status == 200
    except Exception:
        return False


def denetle(koruma: dict, ok) -> None:
    kok = koruma["kok"]
    sonra = _dokum(kok)
    once = koruma["once"]
    yeni = sorted(set(sonra) - set(once))
    degisen = sorted(k for k in set(sonra) & set(once) if sonra[k] != once[k] and not sonra[k][0])
    silinen = sorted(set(once) - set(sonra))
    cihazda = lambda a: a == CIHAZ or a.startswith(CIHAZ + os.sep)  # noqa: E731
    # Geri al: YALNIZ cihaz/ altinda, test sirasinda BELIREN dosyalar (sahte kartin cihaz dosyasi buraya
    # dusmustu; gercek kopru cihaz/'a hic yazmaz). arsiv/ satir/ bildirim/ ASLA silinmez — orada calisan
    # gercek bir kopru mesru dosya yaratir (4H: bildirim onbellegi silinmisti).
    for ad in sorted((a for a in yeni if cihazda(a)), key=lambda s: -s.count(os.sep)):
        p = kok / ad
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()
        except OSError:
            pass
    kopru = gercek_kopru_calisiyor()
    kirli_cihaz = [a for a in yeni + degisen + silinen if cihazda(a)]
    kirli_diger = [a for a in yeni + degisen + silinen if not cihazda(a)]
    ok("[!] Test kullanicinin GERCEK %LOCALAPPDATA%\\olcum-karti dizinine dokunmadi "
       "(cihaz/'da beliren sahte cihaz dosyasi geri alindi; arsiv/satir/bildirim asla silinmez, gercek "
       "kopru calisirken oradaki degisiklik koprunundur)",
       not kirli_cihaz and (kopru or not kirli_diger),
       f"cihaz={kirli_cihaz[:3]} diger={kirli_diger[:3]} gercek_kopru={kopru}")
