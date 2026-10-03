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
import re
import shutil
import sys
import time
from pathlib import Path

# Junction ile BAGLANMAYANLAR (gerisi baglanir). Kendisi zaten baglanti olan girdi HEDEFINE
# baglanir — hedef kaynak dizinin kendisi/atasi degilse ("Application Data" -> LOCALAPPDATA
# atlanir); bkz. yerel_kur.
YEREL_HARIC = ("olcum-karti", "Temp")
# Ozel dizinin kokune yazilan isaret: `gercek_dizin_koru` bunu gorunce LOCALAPPDATA'nin OZEL
# oldugunu bilir — gercek kopru oraya YAZAMAZ, oradaki her degisiklik testin (birlesme
# HIZ + main 4G/4H, 2026-10-03). Dosya; junction degil, ic ice kurulumda da yeniden yazilir.
OZEL_ISARET = ".olcum-ozel-yerel"


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


def _ata_ya_da_kendisi(ata: str, p: str) -> bool:
    a, q = os.path.normcase(ata.rstrip("\\/")), os.path.normcase(p.rstrip("\\/"))
    return q == a or q.startswith(a + os.sep)


def yerel_kur(yerel: Path, gercek: str | None) -> Path:
    """`yerel`i olustur; gercek LOCALAPPDATA'nin ust dizinlerini (YEREL_HARIC disinda)
    junction'la bagla.

    🔴 IC ICE (HIZ inceleme 2026-10-03): mutasyon iscisinin LOCALAPPDATA'si zaten ozel ve
       icindeki HER girdi junction. B3/B23 mutasyonlari orada dogrula3 kosuyor; dogrula3 kendi
       ozel dizinini o dizinden kuruyordu ve junction girdileri ATLANDIGI icin ic zincir yalniz
       `Temp` goruyordu — Arduino15 yok (B22b 113 -> 112, sayim kilidi kirmizi), Python yok
       (B73'un tam yolsuz `python`'u Python'u YENIDEN INDIRTEBILIRDI). Artik kaynak girdi bir
       baglantiysa HEDEFINE baglanir. Izlenmeyen tek durum: hedef kaynak dizinin KENDISI ya da
       bir ATASI ("Application Data" -> LOCALAPPDATA) — korunan olcum-karti onun icinden
       gorunurdu; ve hedefin adi korunanlardan biriyse."""
    yerel = Path(yerel)
    yerel.mkdir(parents=True, exist_ok=True)
    (yerel / "Temp").mkdir(exist_ok=True)
    (yerel / OZEL_ISARET).write_text("dogrula3 / mutasyon iscisi ozel LOCALAPPDATA\n", encoding="utf-8")
    if gercek and os.path.isdir(gercek):
        kok = os.path.realpath(gercek)
        for g in sorted(os.scandir(gercek), key=lambda x: x.name):
            ad = g.name
            if ad in YEREL_HARIC:
                continue
            if baglanti_mi(g.path):
                try:
                    hedef = os.path.realpath(g.path)
                except (OSError, ValueError):
                    continue
                if (_ata_ya_da_kendisi(hedef, kok) or os.path.basename(hedef) in YEREL_HARIC
                        or not os.path.isdir(hedef)):
                    continue
                kaynak = Path(hedef)
            elif g.is_dir(follow_symlinks=False):
                kaynak = Path(gercek) / ad
            else:
                continue
            if baglanti_mi(yerel / ad) or (yerel / ad).exists():
                continue
            if not baglanti_kur(yerel / ad, kaynak):
                raise RuntimeError(f"junction kurulamadi: {yerel / ad}")
    return yerel


def surec_canli(pid: int) -> bool:
    """pid'li surec yasiyor mu. 🔴 Windows'ta os.kill(pid, 0) SURECI OLDURUR
    (TerminateProcess) — kullanilmaz. Emin olunamazsa True (silmeme yonu)."""
    if pid <= 0:
        return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except OSError:
            return True
        return True
    import ctypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k32.OpenProcess(0x1000, 0, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ctypes.get_last_error() == 5     # erisim reddi = var; 87 (gecersiz) = yok
    try:
        kod = ctypes.c_uint32()
        if not k32.GetExitCodeProcess(h, ctypes.byref(kod)):
            return True
        return kod.value == 259                 # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def sahip_pid(ad: str, onek: str) -> int | None:
    """`<onek>[etiket-]<pid>-<sayi>...` adindan sahibin pid'i (`_zincir-yerel-1234-5`,
    `_mutp2-1234-5`, `_mutp2-1234-5.ozel`, `_mutpA-1234-5-1`)."""
    m = re.match(re.escape(onek) + r"(?:[A-Za-z0-9]*-)?(\d+)-\d+", ad)
    return int(m.group(1)) if m else None


def bayatlari_sil(ust: Path, onek: str, yas_sn: float = 6 * 3600, canli=None) -> int:
    """Oldurulmus bir kosudan kalan `<onek>*` dizinlerini guvenle sil: yas_sn'den eski VE adindaki
    sahip surec artik YOK (ad pid tasimiyorsa yalniz yas). 🔴 Yalniz yasa bakmak yetmez: uzun bir
    mutasyon kosusunun `.ozel` dizininin mtime'i olusturuldugu andan kalir — 6 saat sonra BASKA
    agactan baslayan bir kosucu canli iscinin dizinini silerdi."""
    canli = surec_canli if canli is None else canli
    n = 0
    for d in Path(ust).glob(onek + "*"):
        try:
            if not d.is_dir() or time.time() - d.stat().st_mtime <= yas_sn:
                continue
            pid = sahip_pid(d.name, onek)
            if pid is not None and canli(pid):
                continue
            if guvenli_sil(d):
                n += 1
        except OSError:
            pass
    return n
