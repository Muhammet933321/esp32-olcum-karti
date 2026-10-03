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
  2. Test sonunda gercek dizinin dokumu OLCULUR (iddia). cihaz/'da beliren dosya KIRMIZI ve geri
     alinir (yalniz testin baslangicinda OLMAYANLAR silinir); baska yerde hicbir sey silinmez. Gercek
     kopru calisiyorsa onun degisiklikleri beklenir (ayrinti `denetle`).

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


def kopru_calisiyor(port: int = 8770) -> bool:
    """Bu bilgisayarda GERCEK PC koprusu (pc.py) acik mi? (`/durum` imzasi: `kart` + `skop_arsiv`)"""
    import json
    import urllib.request
    try:
        acici = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        r = urllib.request.Request(f"http://127.0.0.1:{port}/durum", headers={"Host": f"olcum.localhost:{port}"})
        with acici.open(r, timeout=1.5) as y:
            d = json.load(y)
        return isinstance(d, dict) and "kart" in d and "skop_arsiv" in d
    except Exception:                                   # noqa: BLE001
        return False


def denetle(koruma: dict, ok, kopru_acik=kopru_calisiyor) -> None:
    """Gercek dizini test sonundaki dokumle karsilastir; iddia + (yalniz cihaz/'da) geri alma.

    4G + 4H (ikisi de gercek kopru calisirken bulundu): kullanicinin koprusu (Baslangic kisayolu,
    varsayilan ONAYLI esitleme) acikken o da bu dizine YAZAR — yeni `akis-<n>` arsivi, gunun `.satir`'i,
    bildirim onbellegi (4H'de geri alma onu SILMISTI; onayli kayit kartta da temizlenebilir: veri kaybi).
    Kural:
      * Geri alma YALNIZ cihaz/ altinda, test sirasinda BELIREN dosyalarda (sahte kartin cihaz dosyasi
        oraya dusmustu, 4B). Baska hicbir yerde hicbir sey silinmez.
      * cihaz/'da YENI dosya her zaman KIRMIZI (gercek kopru cihaz dosyasi YARATMAZ).
      * Gercek kopru 127.0.0.1:8770'te yanit veriyorsa cihaz/ DISINDAKI degisiklikler ve cihaz/'daki
        VAROLAN dosyalarin degismesi (kopru kendi cihaz dosyasinin sayacini ilerletir) beklenir: yesil.
        Kopru kapaliysa her degisiklik kirmizi."""
    kok = koruma["kok"]
    sonra = _dokum(kok)
    once = koruma["once"]
    yeni = sorted(set(sonra) - set(once))
    degisen = sorted(k for k in set(sonra) & set(once) if sonra[k] != once[k] and not sonra[k][0])
    silinen = sorted(set(once) - set(sonra))
    cihazda = lambda a: a == CIHAZ or a.startswith(CIHAZ + os.sep)  # noqa: E731
    # Geri al: YALNIZ cihaz/ altinda, test sirasinda BELIREN dosya/dizinler (derinden sigaya);
    # onceden olana dokunma. arsiv/ satir/ bildirim/ ASLA silinmez.
    for ad in sorted((a for a in yeni if cihazda(a)), key=lambda s: -s.count(os.sep)):
        p = kok / ad
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()
        except OSError:
            pass
    kopru = bool(yeni or degisen or silinen) and kopru_acik()
    yeni_cihaz = [a for a in yeni if cihazda(a)]
    beklenen = [a for a in degisen + silinen if cihazda(a)] + [a for a in yeni + degisen + silinen if not cihazda(a)]
    ok("[!] Test kullanicinin GERCEK %LOCALAPPDATA%\\olcum-karti dizinine dokunmadi "
       "(cihaz/'da beliren sahte cihaz dosyasi geri alindi; baska yerde silme yok, gercek kopru "
       "calisirken onun degisiklikleri beklenir)",
       not yeni_cihaz and (kopru or not beklenen),
       f"cihaz_yeni={yeni_cihaz[:3]} diger={beklenen[:3]} gercek_kopru={kopru}"
       + (" — GERCEK kopru acik: cihaz/ disindaki ve varolan dosyalardaki degisiklik onun sayildi"
          if kopru and beklenen else "")
       + (" — kopru kapali: zinciri kopru kapaliyken kosuyorsaniz bu degisiklik testin"
          if beklenen and not kopru else ""))
