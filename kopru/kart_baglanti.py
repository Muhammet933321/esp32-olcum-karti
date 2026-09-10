# -*- coding: utf-8 -*-
"""Koprunun YUKARI-AKISI — karta nasil baglanildigi.

Iki uygulama, tek yuzey:

    SeriKart   USB seri port (K3a) — Win32 API, ctypes ile
    KayitKart  kaydedilmis satir gunlugu (testler ve olu tekrar)

Yuzey:
    ac()               baglantiyi kur
    kapat()            kapat
    satir_oku(sn)      bir satir dondur ya da None (zaman asimi)
    yaz(metin)         komut gonder ('\\n' burada ekleniyor)
    ad                 kullaniciya gosterilecek kimlik

NEDEN PYSERIAL DEGIL: bu proje "pip install gerektiren her bagimlilik
ileride 'calismiyor' riski demek" kuralini benimsedi ve butun Python
tarafi (arayuz3/sunucu.py, uretim/ zinciri, stok-takip) yalnizca standart
kutuphane kullaniyor. pyserial bu makinede kurulu ama bir Python yeniden
kurulumunda kaybolabilir; koprunun o gun calismamasi kabul edilemez.
Win32 seri API'si ctypes ile stdlib'den erisilebilir.

⚠ WINDOWS'A OZGU. Baska bir platform gerekirse `SeriKart` yerine yeni bir
  sinif yazilir; koprunun geri kalani degismez.

⚠ TEZGAHTA DOGRULANACAK: `SeriKart` gercek donanim olmadan uctan uca
  denenemiyor (kart henuz kurulmadi). Burada sinanan seyler: port
  bulunamayinca duzgun hata, DCB alan duzeni, satir tamponlama mantigi.
  Gercek baud/DTR davranisi TEZGAH LISTESINDE.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

# ── Win32 sabitleri ───────────────────────────────────────────────────
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

NOPARITY = 0
ONESTOPBIT = 0
# 🔴 DTR/RTS SURUCUSU KAPALI. ESP32 gelistirme kartlarinda bu iki hat
#    otomatik-reset devresine bagli: acilista degisirlerse kart RESET
#    ATAR. Reset atmasi bazen istenir (temiz acilis) ama SESSIZCE olmasi
#    istenmez — pil testi kosarken kopru acmak testi oldururdu.
#    B21'in failsafe'i MOSFET'i kapatir, yani veri kaybi olur, tehlike
#    olmaz; yine de bilincli olmali.
DTR_CONTROL_DISABLE = 0
RTS_CONTROL_DISABLE = 0


class DCB(ctypes.Structure):
    """Win32 DCB. Alan SIRASI ve bit alanlari ONEMLI — yanlis duzen
    SetCommState'i sessizce yanlis yapilandirir."""
    _fields_ = [
        ("DCBlength", wintypes.DWORD),
        ("BaudRate", wintypes.DWORD),
        ("fBinary", wintypes.DWORD, 1),
        ("fParity", wintypes.DWORD, 1),
        ("fOutxCtsFlow", wintypes.DWORD, 1),
        ("fOutxDsrFlow", wintypes.DWORD, 1),
        ("fDtrControl", wintypes.DWORD, 2),
        ("fDsrSensitivity", wintypes.DWORD, 1),
        ("fTXContinueOnXoff", wintypes.DWORD, 1),
        ("fOutX", wintypes.DWORD, 1),
        ("fInX", wintypes.DWORD, 1),
        ("fErrorChar", wintypes.DWORD, 1),
        ("fNull", wintypes.DWORD, 1),
        ("fRtsControl", wintypes.DWORD, 2),
        ("fAbortOnError", wintypes.DWORD, 1),
        ("fDummy2", wintypes.DWORD, 17),
        ("wReserved", wintypes.WORD),
        ("XonLim", wintypes.WORD),
        ("XoffLim", wintypes.WORD),
        ("ByteSize", wintypes.BYTE),
        ("Parity", wintypes.BYTE),
        ("StopBits", wintypes.BYTE),
        ("XonChar", ctypes.c_char),
        ("XoffChar", ctypes.c_char),
        ("ErrorChar", ctypes.c_char),
        ("EofChar", ctypes.c_char),
        ("EvtChar", ctypes.c_char),
        ("wReserved1", wintypes.WORD),
    ]


class COMMTIMEOUTS(ctypes.Structure):
    _fields_ = [
        ("ReadIntervalTimeout", wintypes.DWORD),
        ("ReadTotalTimeoutMultiplier", wintypes.DWORD),
        ("ReadTotalTimeoutConstant", wintypes.DWORD),
        ("WriteTotalTimeoutMultiplier", wintypes.DWORD),
        ("WriteTotalTimeoutConstant", wintypes.DWORD),
    ]


def _kernel32():
    """kernel32'yi TIPLERI TANIMLANMIS olarak dondur.

    🔴 argtypes/restype vermek ZORUNLU. Verilmezse ctypes donus tipini
    `c_int` (32 bit) sayar ve x64'te 64 bitlik TANITICIYI KIRPAR:
    CreateFileW basarisiz oldugunda dondurdugu -1, kirpilmis haliyle
    INVALID_HANDLE_VALUE ile karsilastirilamaz hale gelir ve kod
    GECERSIZ BIR TANITICIYLA DEVAM EDER. Ilk yazimda tam bu oldu; hata
    "COM99 acilamadi" yerine bir sonraki adimda "GetCommState basarisiz"
    olarak, yani YANLIS YERDE gorundu. Isaretci argumanlar da ayni
    sebeple kirpilir.
    """
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                              wintypes.HANDLE]
    k.CreateFileW.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    k.GetCommState.argtypes = [wintypes.HANDLE, ctypes.POINTER(DCB)]
    k.GetCommState.restype = wintypes.BOOL
    k.SetCommState.argtypes = [wintypes.HANDLE, ctypes.POINTER(DCB)]
    k.SetCommState.restype = wintypes.BOOL
    k.SetCommTimeouts.argtypes = [wintypes.HANDLE, ctypes.POINTER(COMMTIMEOUTS)]
    k.SetCommTimeouts.restype = wintypes.BOOL
    k.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                           ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    k.ReadFile.restype = wintypes.BOOL
    k.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                            ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    k.WriteFile.restype = wintypes.BOOL
    return k


def portlari_listele() -> list[str]:
    """Kayitli COM portlari. `winreg` de standart kutuphanede."""
    if sys.platform != "win32":
        return []
    import winreg
    try:
        anahtar = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DEVICEMAP\SERIALCOMM")
    except OSError:
        return []
    bulunan = []
    try:
        i = 0
        while True:
            try:
                _, deger, _ = winreg.EnumValue(anahtar, i)
            except OSError:
                break
            bulunan.append(str(deger))
            i += 1
    finally:
        anahtar.Close()
    return sorted(bulunan)


class SeriKart:
    """USB seri yukari-akisi (K3a).

    Bu kip TERCIH EDILENDIR: kartin WiFi'si kapali kalabilir, `loop()`'ta
    hic TCP yoktur, ikili derin aktarim (DEVIR 4.11) yalnizca burada
    mumkundur ve kalibrasyon yetkisi zaten fiziksel erisim gerektirir.
    """

    def __init__(self, port: str | None = None, baud: int = 115200):
        self.port = port
        self.baud = baud
        self._h = None
        self._tampon = b""

    @property
    def ad(self) -> str:
        return f"seri:{self.port or '(otomatik)'}@{self.baud}"

    def ac(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("SeriKart yalnizca Windows'ta calisir")
        if not self.port:
            adaylar = portlari_listele()
            if not adaylar:
                raise RuntimeError("COM portu bulunamadi — kart takili mi?")
            self.port = adaylar[-1]

        k32 = _kernel32()
        self._k32 = k32
        # COM10 ve ustu icin `\\.\` oneki SART; COM9'a kadar da zararsiz.
        yol = r"\\.\{}".format(self.port)
        h = k32.CreateFileW(yol, GENERIC_READ | GENERIC_WRITE, 0, None,
                            OPEN_EXISTING, 0, None)
        if not h or h == INVALID_HANDLE_VALUE:
            hata = ctypes.get_last_error()
            # Iki hata birbirine karistirilmamali: 2 = port YOK (kart takili
            # degil ya da surucu kurulmadi), 5 = port MESGUL (baska bir
            # program tutuyor). Kullaniciya yanlis sebep soylemek en can
            # sikici hata ayiklama turudur.
            neden = {
                2: "boyle bir port yok — kart takili mi, surucu kurulu mu?",
                5: "port mesgul — baska bir program tutuyor "
                   "(Arduino seri monitoru acik mi?)",
            }.get(hata, "acilamadi")
            raise RuntimeError(f"{self.port}: {neden} (WinError {hata})")
        self._h = h

        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        if not k32.GetCommState(h, ctypes.byref(dcb)):
            self.kapat()
            raise RuntimeError("GetCommState basarisiz")
        dcb.BaudRate = self.baud
        dcb.ByteSize = 8
        dcb.Parity = NOPARITY
        dcb.StopBits = ONESTOPBIT
        dcb.fBinary = 1
        dcb.fParity = 0
        dcb.fOutxCtsFlow = 0
        dcb.fOutxDsrFlow = 0
        dcb.fDtrControl = DTR_CONTROL_DISABLE
        dcb.fRtsControl = RTS_CONTROL_DISABLE
        dcb.fOutX = 0
        dcb.fInX = 0
        dcb.fAbortOnError = 0
        if not k32.SetCommState(h, ctypes.byref(dcb)):
            self.kapat()
            raise RuntimeError("SetCommState basarisiz — baud kabul edilmedi")

        # Bloklamayan okuma: ne varsa hemen don. Kopru dongusu zaten
        # kendi ritmini tutuyor; burada beklemek gecikme ekler.
        zt = COMMTIMEOUTS(ReadIntervalTimeout=0xFFFFFFFF,
                          ReadTotalTimeoutMultiplier=0,
                          ReadTotalTimeoutConstant=0,
                          WriteTotalTimeoutMultiplier=0,
                          WriteTotalTimeoutConstant=1000)
        k32.SetCommTimeouts(h, ctypes.byref(zt))
        self._k32 = k32

    def kapat(self) -> None:
        if self._h:
            if not getattr(self, "_k32", None):
                self._k32 = _kernel32()
            self._k32.CloseHandle(self._h)
        self._h = None

    def _ham_oku(self) -> bytes:
        tampon = ctypes.create_string_buffer(4096)
        okunan = wintypes.DWORD(0)
        if not self._k32.ReadFile(self._h, tampon, 4096,
                                  ctypes.byref(okunan), None):
            return b""
        return tampon.raw[:okunan.value]

    def satir_oku(self, zaman_asimi: float = 0.5) -> str | None:
        """Bir tam satir dondur. Yoksa zaman asimina kadar bekle."""
        son = time.monotonic() + zaman_asimi
        while True:
            n = self._tampon.find(b"\n")
            if n >= 0:
                satir = self._tampon[:n]
                self._tampon = self._tampon[n + 1:]
                return satir.decode("utf-8", "replace").rstrip("\r")
            if time.monotonic() >= son:
                return None
            parca = self._ham_oku()
            if parca:
                self._tampon += parca
            else:
                time.sleep(0.002)

    def yaz(self, metin: str) -> None:
        veri = (metin + "\n").encode("utf-8")
        yazilan = wintypes.DWORD(0)
        self._k32.WriteFile(self._h, veri, len(veri),
                            ctypes.byref(yazilan), None)


class KayitKart:
    """Kaydedilmis satir gunlugunu kart gibi oynatir.

    Iki isi var:
      1. `test_kopru.py` — donanimsiz uctan uca sinama
      2. olu tekrar: arsivlenmis bir kosuyu arayuzde yeniden izlemek

    Komutlar `yanitlar` sozlugunden karsilaniyor; bilinmeyen komut
    kartin yaptigi gibi `! bilinmeyen komut` donduruyor.
    """

    def __init__(self, satirlar, yanitlar=None, gecikme: float = 0.0):
        self._satirlar = list(satirlar)
        self._i = 0
        self.yanitlar = dict(yanitlar or {})
        self.gecikme = gecikme
        self.yazilanlar: list[str] = []

    @property
    def ad(self) -> str:
        return f"kayit:{len(self._satirlar)} satir"

    def ac(self) -> None:
        self._i = 0

    def kapat(self) -> None:
        pass

    def satir_oku(self, zaman_asimi: float = 0.5) -> str | None:
        if self._i >= len(self._satirlar):
            return None
        if self.gecikme:
            time.sleep(self.gecikme)
        s = self._satirlar[self._i]
        self._i += 1
        return s

    def yaz(self, metin: str) -> None:
        self.yazilanlar.append(metin)
        yanit = self.yanitlar.get(metin)
        if yanit is None:
            yanit = ["! bilinmeyen komut — `h` yardim"]
        # Yanit satirlari akisin ICINE giriyor — gercek kartta da oyle:
        # komut yaniti da `Serial.println` ile ayni tele yaziliyor.
        self._satirlar[self._i:self._i] = list(yanit)
