# -*- coding: utf-8 -*-
"""OZEL LOCALAPPDATA — mutasyon iscileri VE dogrulama zinciri icin (HIZ, 2026-10-03).

Neden: `gercek_dizin_koru` testleri (B22a test_kopru, B72 test_kayit_esp,
test_bildirim) GERCEK `%LOCALAPPDATA%\\olcum-karti`'nin dokumunu once/sonra
karsilastiriyor ve test sirasinda BELIREN dosyalari SILIYOR ("geri al").
Olculdu (2026-10-03 14:11): zincir koşarken gercek kopru (4E bildirimleri)
`bildirim/son.json` ve `bildirim/<kart>.okb` yazdi — B72 KIRMIZI oldu VE test
bu iki dosyayi kullanicinin gercek dizininden SILDI. Ayni pencerede yeni bir
arsiv akis dizini acilsaydi kartin onaylanmis kayitlari da silinirdi.

Cozum: adimlar ve mutasyon iscileri `LOCALAPPDATA`'yi OZEL bir dizinde gorur.
Orada gercek LOCALAPPDATA'nin HER ust dizini JUNCTION ile baglidir — `olcum-karti`
(izole edilen tek sey) ve `Temp` (bos, ozel) HARIC. Gercek `olcum-karti` ortam
degiskeniyle HIC gorunmez.

🔴 NEDEN HEPSI, YALNIZ Arduino15 DEGIL (2026-10-03 olculdu): ilk surum yalniz
   Arduino15 + arduino bagliyordu. B73'un `python` diye (tam yolsuz) actigi alt
   surec WindowsApps takma adindan gecti; Python kurulum yoneticisi calisma
   zamanini %LOCALAPPDATA%\\Python'da aradi, BULAMADI ve ozel dizine 153 MB'lik
   YENI bir Python 3.14 INDIRIP KURDU — zincir sessizce baska bir Python yamasiyla
   kosuyordu. Araclarin LOCALAPPDATA'da ne aradigini tek tek bilemeyiz; kural:
   her seyi bagla, yalniz korunani ayir.

🔴 Silme `guvenli_sil` ile: junction BAGLANTI olarak kaldirilir, hedefe asla
   inilmez (kullanicinin ESP32 cekirdegi silinmesin). test_zincir_hiz A4 sinar.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

# Junction ile BAGLANMAYANLAR (gerisi baglanir). Kendisi zaten baglanti olan girdiler
# (ornegin "Application Data" -> LOCALAPPDATA'nin kendisi) da atlanir.
YEREL_HARIC = ("olcum-karti", "Temp")


def baglanti_mi(p) -> bool:
    try:
        return os.path.islink(p) or os.path.isjunction(p)
    except OSError:
        return False


def guvenli_sil(kok: Path) -> bool:
    """Dizini sil — ama icindeki JUNCTION/symlink'lerin HEDEFINE asla dokunmadan.

    🔴 Ozel LOCALAPPDATA'da `Arduino15` gercek ESP32 cekirdegine junction. Bir
    silme rutini junction'i izlerse kullanicinin araclarini siler. Once butun
    baglantilar BAGLANTI olarak kaldirilir (os.rmdir junction'i, os.unlink
    symlink'i), kalan yoksa agac silinir. Kaldirilamayan baglanti varsa agac
    SILINMEZ (False) — birakmak zararsiz, yanlis silmek degil."""
    kok = Path(kok)
    if not kok.exists() and not baglanti_mi(kok):
        return True
    if baglanti_mi(kok):
        try:
            os.rmdir(kok) if os.path.isdir(kok) else os.unlink(kok)
        except OSError:
            return False
        return True
    yigin = [kok]
    while yigin:
        d = yigin.pop()
        try:
            girdiler = list(os.scandir(d))
        except OSError:
            continue
        for g in girdiler:
            if baglanti_mi(g.path):
                try:
                    os.rmdir(g.path) if os.path.isdir(g.path) else os.unlink(g.path)
                except OSError:
                    pass
                if baglanti_mi(g.path) or os.path.lexists(g.path):
                    return False
            elif g.is_dir(follow_symlinks=False):
                yigin.append(Path(g.path))
    shutil.rmtree(kok, ignore_errors=True)
    return not kok.exists()


def baglanti_kur(link: Path, hedef: Path) -> bool:
    if not hedef.is_dir():
        return False
    try:
        import _winapi
        _winapi.CreateJunction(str(hedef), str(link))
    except (ImportError, OSError):
        try:
            os.symlink(hedef, link, target_is_directory=True)
        except OSError:
            return False
    return baglanti_mi(link)


def yerel_kur(yerel: Path, gercek: str | None) -> Path:
    """`yerel`i olustur; gercek LOCALAPPDATA'nin ust dizinlerini (YEREL_HARIC disinda)
    junction'la bagla."""
    yerel = Path(yerel)
    yerel.mkdir(parents=True, exist_ok=True)
    (yerel / "Temp").mkdir(exist_ok=True)
    if gercek and os.path.isdir(gercek):
        for g in sorted(os.scandir(gercek), key=lambda x: x.name):
            ad = g.name
            if ad in YEREL_HARIC or baglanti_mi(g.path) or not g.is_dir(follow_symlinks=False):
                continue
            if baglanti_mi(yerel / ad) or (yerel / ad).exists():
                continue
            if not baglanti_kur(yerel / ad, Path(gercek) / ad):
                raise RuntimeError(f"junction kurulamadi: {yerel / ad}")
    return yerel


def bayatlari_sil(ust: Path, onek: str, yas_sn: float = 6 * 3600) -> int:
    """Oldurulmus bir kosudan kalan `<onek>*` dizinlerini (yas_sn'den eski) guvenle sil."""
    n = 0
    for d in Path(ust).glob(onek + "*"):
        try:
            if d.is_dir() and time.time() - d.stat().st_mtime > yas_sn and guvenli_sil(d):
                n += 1
        except OSError:
            pass
    return n
