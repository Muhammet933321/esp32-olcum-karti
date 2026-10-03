# -*- coding: utf-8 -*-
"""4E (PC13) — Windows bildirimi: WinRT toast, `powershell.exe` alt sureciyle (yalniz stdlib).

    s = WindowsBildirim(veri_dizini)
    s.goster("baglanti", "Ölçüm kartı", "Karttan haber yok …")          # yeni / ayni etiketle YERINDE gunceller
    s.goster("baglanti", "Ölçüm kartı", "Kart yeniden bağlandı …", sessiz=True)   # acilir pencere yok
    s.kapat()

Deneme (2026-10-03, bu PC, Windows 11 26200, PowerShell 5.1; spec "4E uygulama kararlari"):
  * `Windows.UI.Notifications.ToastNotificationManager` PS 5.1'de `ContentType = WindowsRuntime`
    ile yukleniyor; `CreateToastNotifier(AUMID).Show()` ~0.2-0.8 s (alt surec dahil).
  * Ayni `Tag` + `Group` ile ikinci `Show` ESKISININ YERINI ALIYOR (Bildirim merkezinde
    `History.GetHistory` 1 kayit; ekranda tek kart, yeni metin).
  * Kaynak adi: AUMID `HKCU\\Software\\Classes\\AppUserModelId\\OlcumKarti.Kopru` altina
    `DisplayName` = "Ölçüm kartı" + `IconUri` (panel ikonu) yazilinca Bildirim merkezinde
    "Ölçüm kartı" + ikon; kisayol / paket GEREKMIYOR. Kayit yoksa PowerShell'in AUMID'i
    kullanilsaydi kaynak "Windows PowerShell" gorunurdu.
  * Tarayici / panel KAPALIYKEN de cikiyor (alt surec tarayicidan bagimsiz).
  * "Rahatsiz Etmeyin" acikken acilir pencere (banner) GOSTERILMIYOR, bildirim yine Bildirim
    merkezine dusuyor — kullanicinin Windows ayari; oncelikli uygulamalar listesine "Ölçüm kartı"
    eklenirse geçer (tezgah/kullanici kalemi).

Metin XML'e kacirilarak, XML de base64 ile betige girer: bildirim metni PowerShell komutu olarak
YORUMLANAMAZ. Etiket/grup yalniz [a-z0-9-] (en cok 16). Alt surec `CREATE_NO_WINDOW` ile (pythonw
arka planinda konsol penceresi yanip sonmesin). Gosterim AYRI bir iplikte kuyruktan: MQTT ipligi
PowerShell'i beklemez.
"""
from __future__ import annotations

import base64
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from xml.sax.saxutils import escape

AUMID = "OlcumKarti.Kopru"
GRUP = "olcum"
GORUNEN_AD = "Ölçüm kartı"
IKON_KAYNAK = Path(__file__).resolve().parent.parent / "arayuz3" / "ikon-192.png"
IKON_AD = "bildirim-ikon.png"
ETIKET_DESEN = re.compile(r"[a-z0-9-]{1,16}")
CREATE_NO_WINDOW = 0x08000000
POWERSHELL = (Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"))

_ON = ("$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
       "[void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
       "ContentType = WindowsRuntime];"
       "[void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
       "ContentType = WindowsRuntime];")


def toast_xml(baslik: str, metin: str) -> str:
    return ('<toast><visual><binding template="ToastGeneric"><text>' + escape(baslik)
            + "</text><text>" + escape(metin) + "</text></binding></visual></toast>")


def betik(etiket: str, baslik: str, metin: str, sessiz: bool = False, aumid: str = AUMID,
          grup: str = GRUP) -> str:
    """PowerShell betigi. Kullanici metni YALNIZ base64 (UTF-8 XML) olarak girer."""
    if not ETIKET_DESEN.fullmatch(etiket) or not ETIKET_DESEN.fullmatch(grup):
        raise ValueError("etiket/grup yalniz [a-z0-9-], en cok 16 karakter")
    if not re.fullmatch(r"[A-Za-z0-9.]{1,64}", aumid):
        raise ValueError("AUMID bicimsiz")
    b64 = base64.b64encode(toast_xml(baslik, metin).encode("utf-8")).decode("ascii")
    return _ON + (
        "$x=[Windows.Data.Xml.Dom.XmlDocument]::new();"
        f"$x.LoadXml([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}')));"
        "$t=[Windows.UI.Notifications.ToastNotification]::new($x);"
        f"$t.Tag='{etiket}';$t.Group='{grup}';$t.SuppressPopup=${'true' if sessiz else 'false'};"
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{aumid}').Show($t)")


def komut(betik_metni: str) -> list[str]:
    kod = base64.b64encode(betik_metni.encode("utf-16-le")).decode("ascii")
    return [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", kod]


def aumid_kaydet(veri_dizini: Path, ikon_kaynak: Path = IKON_KAYNAK) -> None:
    """Kaynak adi + ikon: HKCU (yonetici gerekmez, geri alinir: anahtari sil). Ikon calisma agacindan
    veri dizinine KOPYALANIR — agac silinse de ikon kalir."""
    import winreg
    ikon = Path(veri_dizini) / IKON_AD
    try:
        Path(veri_dizini).mkdir(parents=True, exist_ok=True)
        if ikon_kaynak.is_file():
            shutil.copy2(ikon_kaynak, ikon)
    except OSError:
        pass
    k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{AUMID}")
    try:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, GORUNEN_AD)
        if ikon.is_file():
            winreg.SetValueEx(k, "IconUri", 0, winreg.REG_SZ, str(ikon))
    finally:
        winreg.CloseKey(k)


class WindowsBildirim:
    """Bildirim cikisi (PcBildirim'in `cikis`'i). `calistir` / `kaydet` sinamada degistirilir."""

    yol = "windows"

    def __init__(self, veri_dizini, calistir=None, kaydet=None, hata=None):
        self.veri_dizini = Path(veri_dizini)
        # Sinama/zincir: OLCUM_TOAST_YOK=1 iken GERCEK bildirim gosterilmez, kayit defterine yazilmaz
        # (test_kopru pc.calistir'i gercek cikisla kosar; uyuyan kullanicinin ekranina toast dusmesin)
        self.sinama = bool(os.environ.get("OLCUM_TOAST_YOK"))
        if self.sinama:
            calistir = calistir or (lambda _b: 0)
            kaydet = kaydet if kaydet is not None else (lambda: None)
        self._calistir = calistir or self._ps_calistir
        self._kaydet = kaydet if kaydet is not None else (lambda: aumid_kaydet(self.veri_dizini))
        self._hata = hata                     # hata(metin): durum satiri (sir yok)
        self._kuyruk: queue.Queue = queue.Queue(maxsize=64)
        self._is: threading.Thread | None = None
        self._kayitli = False
        self.gosterilen = 0
        self.son_hata: str | None = None

    def goster(self, etiket: str, baslik: str, metin: str, sessiz: bool = False) -> None:
        b = betik(etiket, baslik, metin, sessiz)          # bicim hatasi cagirana (programci hatasi)
        try:
            self._kuyruk.put_nowait(b)
        except queue.Full:
            return
        if self._is is None or not self._is.is_alive():
            self._is = threading.Thread(target=self._dongu, name="kopru-toast", daemon=True)
            self._is.start()

    def kapat(self, bekle: float = 3.0) -> None:
        if self._is is not None and self._is.is_alive():
            self._kuyruk.put(None)
            self._is.join(bekle)

    def _ps_calistir(self, betik_metni: str) -> int:
        r = subprocess.run(komut(betik_metni), capture_output=True, timeout=30,
                           creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        return r.returncode

    def _dongu(self) -> None:
        while True:
            b = self._kuyruk.get()           # iplik bosta beklemez-cikmaz: cikis yarisi (kuyrukta kalan) olmasin
            if b is None:
                return
            if not self._kayitli:
                try:
                    self._kaydet()
                except Exception:                       # noqa: BLE001 — ad "PowerShell" kalir, bildirim cikar
                    pass
                self._kayitli = True
            try:
                rc = self._calistir(b)
            except Exception as e:                      # noqa: BLE001
                rc = type(e).__name__
            if rc == 0:
                self.gosterilen += 1
            else:
                metin = f"Windows bildirimi gosterilemedi (powershell: {rc})"
                if metin != self.son_hata and self._hata:
                    self._hata(metin)
                self.son_hata = metin


class YokBildirim:
    """Windows disi: bildirim yalniz durum satiri olarak (kopru akisi)."""

    yol = "yok"

    def __init__(self, yayinla=None):
        self._yayinla = yayinla
        self.gosterilen = 0

    def goster(self, etiket: str, baslik: str, metin: str, sessiz: bool = False) -> None:
        self.gosterilen += 1
        if self._yayinla:
            self._yayinla(f"* bildirim: {metin}")

    def kapat(self) -> None:
        pass
