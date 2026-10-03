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
import re
import sys
import threading
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

# EscapeCommFunction — otomatik reset dizisi icin.
SETRTS, CLRRTS, SETDTR, CLRDTR = 3, 4, 5, 6


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
    k.EscapeCommFunction.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.EscapeCommFunction.restype = wintypes.BOOL
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


# ── 4A (PC3): portu VID'den sec ──────────────────────────────────────
# Kartin IKI Type-C soketi var. "COM" yazan soketteki USB-UART kopru cipi
# dogru olan: firmware `Serial`i UART0'da tutuyor. Yerel USB soketi de port
# acar (VID 303A) ama HICBIR satir gelmez — eskiden "son port" seciliyordu ve
# yanlis sokette kopru sessizce bos akis yayinliyordu.
KOPRU_VID = {"1A86": "WCH CH34x", "10C4": "Silicon Labs CP210x", "0403": "FTDI"}
YEREL_USB_VID = "303A"
# 4A inceleme: kartin KENDI kopru cipi (CH343) — birden cok CH34x/CP210x varken
# once bu denenir. Kullanicinin Arduino Nano klonlari CH340 = 1A86:7523.
KART_USB = {"1A86:55D3": "WCH CH343 (olcum karti)"}


def _vid(deger: str | None) -> str | None:
    """'1A86:55D3' / '1A86' -> '1A86'; belirsiz ('1A86/303A') ya da yok -> None."""
    if not deger or "/" in deger:
        return None
    return deger.split(":", 1)[0]


def portlar_vid() -> dict[str, str | None]:
    """TAKILI COM portlari -> USB "VID:PID" (PID okunamazsa yalniz VID; 4 onaltilik,
    buyuk harf) ya da None.

    Kayit defterinden: `Enum\\USB\\VID_xxxx&PID_yyyy\\<ornek>\\Device
    Parameters\\PortName` (FTDI: `Enum\\FTDIBUS\\VID_xxxx+...`). Enum takili
    OLMAYAN eski aygitlari da tutar (bu makinede COM3/COM5 eski CH340'lar,
    2026-10-03) — o yuzden `SERIALCOMM` (yalniz takili portlar) ile kesisiyor.
    Ayni COM adina iki farkli VID dusuyorsa "1A86/303A" gibi BELIRSIZ dondurur;
    secici onu kopru cipi saymaz.
    """
    takili = portlari_listele()
    if sys.platform != "win32" or not takili:
        return {p: None for p in takili}
    import winreg
    vidler: dict[str, set[str]] = {}

    def alt_anahtarlar(a):
        i = 0
        while True:
            try:
                yield winreg.EnumKey(a, i)
            except OSError:
                return
            i += 1

    for kok in (r"SYSTEM\CurrentControlSet\Enum\USB",
                r"SYSTEM\CurrentControlSet\Enum\FTDIBUS"):
        try:
            a = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, kok)
        except OSError:
            continue
        with a:
            for aygit in list(alt_anahtarlar(a)):
                m = re.search(r"VID_([0-9A-Fa-f]{4})(?:[&+]PID_([0-9A-Fa-f]{4}))?", aygit)
                if not m:
                    continue
                kimlik = m.group(1).upper() + (":" + m.group(2).upper() if m.group(2) else "")
                try:
                    b = winreg.OpenKey(a, aygit)
                except OSError:
                    continue
                with b:
                    for ornek in list(alt_anahtarlar(b)):
                        try:
                            with winreg.OpenKey(b, ornek + r"\Device Parameters") as c:
                                ad, _ = winreg.QueryValueEx(c, "PortName")
                        except OSError:
                            continue
                        vidler.setdefault(str(ad).upper(), set()).add(kimlik)
    return {p: ("/".join(sorted(vidler[p.upper()])) if p.upper() in vidler else None)
            for p in takili}


def kart_adaylari(portlar: dict[str, str | None]) -> list[str]:
    """Kopru cipli portlar, kartin kendi VID:PID'i (KART_USB) ONCE. 303A / belirsiz / bilinmeyen YOK."""
    adaylar = [p for p, v in portlar.items() if _vid(v) in KOPRU_VID]
    return sorted(adaylar, key=lambda p: (portlar[p] not in KART_USB, p))


def kart_portu_sec(portlar: dict[str, str | None]) -> str:
    """Kopru cipli TEK portu dondur; yoksa / birden fazlaysa ACIK hata.

    303A (yerel USB) ASLA secilmez; VID'i bilinmeyen port da secilmez. Birden
    cok kopru cipi varken kartin kendi VID:PID'i (KART_USB) tek ise o secilir.
    """
    def liste():
        return ", ".join(f"{p} ({v or 'VID ?'})" for p, v in sorted(portlar.items())) or "(yok)"

    adaylar = kart_adaylari(portlar)
    if len(adaylar) == 1:
        return adaylar[0]
    if len(adaylar) > 1:
        tam = [p for p in adaylar if portlar[p] in KART_USB]
        if len(tam) == 1:
            return tam[0]
        raise RuntimeError(f"birden fazla kopru cipli port var: {liste()} — "
                           f"--port COMx ile secin")
    if any(_vid(v) == YEREL_USB_VID for v in portlar.values()):
        raise RuntimeError(
            f"kart YANLIS sokete takili: yalniz yerel USB portu var ({liste()}). "
            f"VID 303A = ESP32'nin kendi USB'si, firmware orada SESSIZ. Kabloyu "
            f"kartin 'COM' yazan soketine takin (kopru cipi: 1A86 / 10C4 / 0403)")
    if not portlar:
        raise RuntimeError("COM portu bulunamadi — kart takili mi, surucu kurulu mu? "
                           "(Aygit Yoneticisi -> Baglanti noktalari)")
    raise RuntimeError(f"kopru cipli COM portu bulunamadi: {liste()} — kart 'COM' "
                       f"soketinden takili mi? Gerekirse --port COMx")


def kart_portu_bul() -> str:
    return kart_portu_sec(portlar_vid())


def _otomatik_adaylar() -> list[str]:
    """OtoSeriKart icin denenecek portlar (tercih sirasiyla); hic yoksa ACIK hata."""
    portlar = portlar_vid()
    adaylar = kart_adaylari(portlar)
    if not adaylar:
        kart_portu_sec(portlar)          # hic aday yok: sebebi soyleyen RuntimeError
    return adaylar


# ── 4A inceleme: portu TUTMADAN once kartin kimligi ──────────────────
# Eskiden VID'i uyan ILK aygit (Arduino Nano klonu, USB-TTL) arka planda acilip
# tutuluyordu: Arduino IDE "Access denied" aliyor, Nano'nun ciktisi kart verisi
# diye arsivleniyor, sonra takilan gercek kart hic secilmiyordu. Kart kendiliginden
# `D` satiri basar (rapor araligi en cok 5 s); basmazsa SERBEST `?` komutunun
# yaniti `A menzil=...` (salt okunur, sir icermez — firmware komut_serbest).
# 🔴 `N?` ASLA: o parolalari basar.
_SAYI = r"-?(?:[0-9]+(?:\.[0-9]+)?|nan|inf)"
KIMLIK_DESEN = re.compile(
    rf"D {_SAYI}(?: {_SAYI}){{4}}(?: [0-9]+){{3,4}}|K [0-9]+ [0-9]+ [0-9]+|A menzil=(?:NORMAL|YUKSEK) .*")
KIMLIK_TAMPON = 64


def kart_kimligi(kart, pasif_sn: float = 2.0, soru_sn: float = 2.0) -> tuple[bool, list[str]]:
    """Port arkasindaki aygit olcum karti mi? (tamam, okunan satirlar).

    Once DINLER (`D`/`K` satiri); gelmezse yalniz `?` yollar ve `A menzil=` bekler.
    Okunan satirlar geri verilir: dogrulama sirasinda gelen olcum kaybolmasin.
    """
    gorulen: list[str] = []

    def dinle(sure: float) -> bool:
        son = time.monotonic() + sure
        while time.monotonic() < son:
            satir = kart.satir_oku(min(0.25, max(0.01, son - time.monotonic())))
            if getattr(kart, "kopuk", False):
                return False
            if satir is None:
                continue
            gorulen.append(satir)
            del gorulen[:-KIMLIK_TAMPON]
            if KIMLIK_DESEN.fullmatch(satir.strip()):
                return True
        return False

    if dinle(pasif_sn):
        return True, gorulen
    try:
        kart.yaz("?")
    except Exception:                                       # noqa: BLE001
        return False, gorulen
    return dinle(soru_sn), gorulen


def _kopru_portu_tutuyor(port: str, kopru_portlari) -> bool:
    """Bu bilgisayarda calisan PC koprusu `port`u mu tutuyor? (`/durum`'a sor)."""
    import json
    import pc_ayar
    for hp in kopru_portlari:
        try:
            # 4A inceleme: VEKILSIZ — HTTP_PROXY / sistem vekili 127.0.0.1'i saptirmasin
            with pc_ayar.yerel_istek(hp, "/durum") as y:
                d = json.load(y)
        except Exception:                                   # noqa: BLE001
            continue
        if isinstance(d, dict) and str(d.get("kart", "")).upper().startswith(
                f"SERI:{port.upper()}@"):
            return True
    return False


def acma_hatasi(port: str, hata: int, kopru_portlari=None) -> str:
    """CreateFileW hata kodunu kullaniciya ACIK bir cumleye cevir.

    Iki hata birbirine karistirilmamali: 2 = port YOK (kart takili degil ya
    da surucu kurulmadi), 5 = port MESGUL (baska bir program tutuyor).
    4A (PC3): mesgulse ve tutan PC koprusuyse bunu ADIYLA soyle — kopru
    arka planda (Baslangic kisayolu) calisiyorsa tezgah araci sessizce
    "acilamadi" demesin.
    """
    if hata == 5:
        if kopru_portlari is None:
            import pc_ayar
            kopru_portlari = (pc_ayar.PORT,)
        if _kopru_portu_tutuyor(port, kopru_portlari):
            # 4A inceleme: "pythonw.exe'yi oldur" DEMIYORUZ — stok-takip'in arka plan
            # sunucusu da ayni yoldan pythonw; yanlisi oldurulurdu.
            return (f"{port}: PC kopru bu portu kullaniyor — kapatin: kopru\\Kopruyu Durdur.bat "
                    f"(ya da `python kopru/pc.py --durdur`; on plandaysa penceresinde Ctrl+C), "
                    f"sonra yeniden deneyin (WinError 5)")
        return (f"{port}: port mesgul — baska bir program tutuyor (PC koprusu, Arduino "
                f"seri monitoru, baska bir tezgah araci?) (WinError 5)")
    neden = {2: "boyle bir port yok — kart takili mi, surucu kurulu mu?"}.get(hata, "acilamadi")
    return f"{port}: {neden} (WinError {hata})"


class SeriKart:
    """USB seri yukari-akisi (K3a).

    Bu kip TERCIH EDILENDIR: kartin WiFi'si kapali kalabilir, `loop()`'ta
    hic TCP yoktur, ikili derin aktarim (DEVIR 4.11) yalnizca burada
    mumkundur ve kalibrasyon yetkisi zaten fiziksel erisim gerektirir.
    """

    def __init__(self, port: str | None = None, baud: int = 115200):
        # 4A inceleme: `--port com7` -> COM7 (SERIALCOMM adlari buyuk harf; kucuk
        # harf 303A reddini sessizce atlatiyordu)
        self.port = port.strip().upper() if port else None
        self.baud = baud
        self._h = None
        self._tampon = b""
        # 4A: ReadFile/WriteFile BASARISIZ oldu (kablo cekildi, surucu gitti).
        # Eskiden bos okuma sayilip sessizce sonsuza dek None donuyordu.
        self.kopuk = False
        self._hizali = True
        # 4A inceleme: CloseHandle ile ReadFile/WriteFile ayni anda olmasin
        # (kapanan tanitici numarasini Windows hemen baska nesneye verebilir)
        self._kilit = threading.Lock()

    def _baglanti_basladi(self) -> None:
        """Her acilista: tampon bos, ILK satir atilacak.

        🔴 4A inceleme: port satirin ORTASINDA acilabilir. Kart AP parolasini
           "  AP parolasi (yalniz USB): " + parola + "\\r\\n" diye UC parcada basiyor;
           port aradan acilirsa ilk okunan "satir" isaretsiz parolanin kendisiydi
           ve suzgecten gecip akisa / arsive gidiyordu. Ilk `\\n`e kadar gelen her
           sey atilir (en kotu ihtimalle tam bir olcum satiri kaybolur).
        """
        self._tampon = b""
        self._hizali = False
        self.kopuk = False

    @property
    def ad(self) -> str:
        return f"seri:{self.port or '(otomatik)'}@{self.baud}"

    def ac(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("SeriKart yalnizca Windows'ta calisir")
        if not self.port:
            # 4A (PC3): eskiden `portlari_listele()[-1]` — yerel USB soketi
            # (303A) son siradaysa SESSIZ porta baglaniyordu.
            self.port = kart_portu_bul()
        elif _vid(portlar_vid().get(self.port)) == YEREL_USB_VID:
            raise RuntimeError(f"{self.port}: VID 303A = ESP32'nin yerel USB soketi; "
                               f"firmware orada SESSIZ. 'COM' yazan sokete takin")

        k32 = _kernel32()
        self._k32 = k32
        # COM10 ve ustu icin `\\.\` oneki SART; COM9'a kadar da zararsiz.
        yol = r"\\.\{}".format(self.port)
        h = k32.CreateFileW(yol, GENERIC_READ | GENERIC_WRITE, 0, None,
                            OPEN_EXISTING, 0, None)
        if not h or h == INVALID_HANDLE_VALUE:
            # Kullaniciya yanlis sebep soylemek en can sikici hata ayiklama
            # turudur — ayrim `acma_hatasi`nda (2 yok / 5 mesgul / kopru).
            raise RuntimeError(acma_hatasi(self.port, ctypes.get_last_error()))
        self._h = h
        self._baglanti_basladi()

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
        with self._kilit:
            if self._h:
                if not getattr(self, "_k32", None):
                    self._k32 = _kernel32()
                self._k32.CloseHandle(self._h)
            self._h = None

    def _ham_oku(self) -> bytes:
        tampon = ctypes.create_string_buffer(4096)
        okunan = wintypes.DWORD(0)
        with self._kilit:
            if not self._h:
                self.kopuk = True
                return b""
            if not self._k32.ReadFile(self._h, tampon, 4096,
                                      ctypes.byref(okunan), None):
                self.kopuk = True
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
                if not self._hizali:
                    self._hizali = True          # acilistaki yarim satir: AT
                    continue
                return satir.decode("utf-8", "replace").rstrip("\r")
            if time.monotonic() >= son:
                return None
            parca = self._ham_oku()
            if parca:
                self._tampon += parca
            elif self.kopuk:
                return None
            else:
                time.sleep(0.002)

    def sifirla(self, bekle: float = 0.35) -> bool:
        """Karti DONANIMDAN sifirlamayi dener. Basardiysa True.

        NEDEN VAR: kart acilis afisinde PSRAM boyutunu, pil tamponunu ve
        LittleFS durumunu YALNIZCA BIR KEZ basiyor. `ac()` DTR/RTS'i
        DISABLE kuruyor (bilerek: acilista kazara reset atmasin), o
        yuzden baglandigimizda afis coktan gecmis oluyor.

        Klasik oto-reset devresi: DTR -> EN, RTS -> IO0.
            RTS=1, DTR=0  ->  IO0 asagi, EN yukari
            DTR=1         ->  EN asagi  (reset)
            DTR=0, RTS=0  ->  birak     (normal acilis)

        ⚠ Yerel USB CDC'li kartlarda (ESP32-S3'un kendi USB'si) bu
          dizinin HICBIR ETKISI YOK — orada DTR/RTS gercek bir pine
          bagli degil. Zararsiz; True donmesi "sinyaller gonderildi"
          demek, "kart gercekten sifirlandi" demek DEGIL. Cagiran taraf
          afisi GORDU MU diye bakmali.
        """
        if not self._h:
            return False
        k = self._k32
        for islev in (SETRTS, CLRDTR):
            k.EscapeCommFunction(self._h, islev)
        time.sleep(0.05)
        k.EscapeCommFunction(self._h, SETDTR)      # EN asagi — reset
        time.sleep(0.05)
        k.EscapeCommFunction(self._h, CLRDTR)      # EN birak
        k.EscapeCommFunction(self._h, CLRRTS)
        time.sleep(bekle)                          # acilis
        return True

    def yaz(self, metin: str) -> None:
        veri = (metin + "\n").encode("utf-8")
        yazilan = wintypes.DWORD(0)
        with self._kilit:
            if not self._h:
                raise RuntimeError(f"{self.port}: port kapali")
            if not self._k32.WriteFile(self._h, veri, len(veri),
                                       ctypes.byref(yazilan), None):
                self.kopuk = True


def _seri_kur(port: str | None):
    k = SeriKart(port)
    k.ac()
    return k


class OtoSeriKart:
    """4A (PC4): kart TAKILI OLMASA DA acilan, kopunca yeniden baglanan yuzey.

    Windows acilisinda arka planda baslayan kopru kart takili degilken
    olmemeli (yoksa kisayol ise yaramaz) ve kablo cekilip takilinca kendiliginden
    toparlanmali. `SeriKart` ile AYNI yuzey; durum degisiklikleri `bildir`
    (kopru: yayina, arsive DEGIL) ile BIR KEZ soyleniyor — her denemede
    tekrarlasa akis her 3 s'de bir ayni hatayla dolardi.
    """

    # 4A inceleme: kart olmadigi anlasilan port, aygit takili kaldikca bu sure
    # yeniden ACILMAZ (her 3 s'de Arduino'nun portunu kapmasin; cikarilinca unutulur)
    RET_SN = 120.0

    def __init__(self, port: str | None = None, aralik: float = 3.0, kurucu=None,
                 adaylar=None, dogrula: bool | None = None,
                 pasif_sn: float = 2.0, soru_sn: float = 2.0):
        self.elle_port = port.strip().upper() if port else None
        self.aralik = aralik
        self.kurucu = kurucu or _seri_kur
        self.adaylar = adaylar or _otomatik_adaylar
        # Elle verilen port kullanicinin karari; otomatik secimde kimlik SART
        self.dogrula = (self.elle_port is None) if dogrula is None else dogrula
        self.pasif_sn = pasif_sn
        self.soru_sn = soru_sn
        self.bildir = None
        self._kart = None
        self._son_deneme = -1e9
        self._son_neden = None
        self._reddedilen: dict[str, float] = {}
        self._bekleyen: list[str] = []
        self._kilit = threading.Lock()
        # Her basarili (yeniden) baglantida artar — kopru suzgec penceresini acar
        self.baglanti_no = 0
        # Kart YOKKEN son durum satiri: sonradan baglanan tarayici da gorsun
        # (BIR KEZ yayinlanan satir o an abonesi olmayana hic ulasmazdi —
        # acilista kart yoksa panel "bos ama bagli" kalirdi). Bagliyken None.
        self.durum_satiri: str | None = None

    @property
    def ad(self) -> str:
        if self._kart is not None:
            return self._kart.ad
        return f"seri:{self.elle_port or '(otomatik)'} (bekleniyor)"

    @property
    def bagli(self) -> bool:
        """4B: USB'de (otomatik secimde DOGRULANMIS) kart bagli mi — SecmeliKart USB'yi
        WiFi'ye bunun icin yegler."""
        return self._kart is not None

    def _soyle(self, metin: str) -> None:
        self.durum_satiri = None if metin.startswith("* ") else metin
        if self.bildir:
            self.bildir(metin)

    def _neden(self, metin: str) -> None:
        if metin != self._son_neden:
            self._son_neden = metin
            self._soyle(f"! kopru: kart bulunamadi — {metin} (bekleniyor)")

    def _dene(self) -> None:
        if time.monotonic() - self._son_deneme < self.aralik:
            return
        self._son_deneme = time.monotonic()
        if self.elle_port:
            portlar = [self.elle_port]
        else:
            try:
                portlar = list(self.adaylar())
            except RuntimeError as e:
                self._neden(str(e))
                return
            simdi = time.monotonic()
            self._reddedilen = {p: t for p, t in self._reddedilen.items()
                                if p in portlar and t > simdi}
            if not [p for p in portlar if p not in self._reddedilen]:
                self._neden(f"{', '.join(portlar)}: olcum karti degil (kartin satiri gelmedi) — "
                            f"baska bir aygit (Arduino, USB-TTL) olabilir; kart takiliysa "
                            f"`--port COMx` ile verin")
                return
            portlar = [p for p in portlar if p not in self._reddedilen]
        hata = "kart bulunamadi"
        for port in portlar:
            try:
                kart = self.kurucu(port)
            except RuntimeError as e:
                hata = str(e)
                continue
            if self.dogrula:
                tamam, gorulen = kart_kimligi(kart, self.pasif_sn, self.soru_sn)
                if not tamam:
                    kart.kapat()                # yabanci aygitin portu TUTULMAZ
                    self._reddedilen[port] = time.monotonic() + self.RET_SN
                    hata = (f"{port}: olcum karti degil ({self.pasif_sn + self.soru_sn:.0f} s'de "
                            f"kartin satiri ya da `?` yaniti gelmedi) — port birakildi")
                    continue
                self._bekleyen = gorulen
            with self._kilit:
                self._kart = kart
            self.baglanti_no += 1
            self._son_neden = None
            self._soyle(f"* kopru: kart baglandi — {kart.ad}")
            return
        self._neden(hata)

    def ac(self) -> None:
        """Hata ATMAZ: kart yoksa `satir_oku` aramaya devam eder."""
        self._dene()

    def kapat(self) -> None:
        # 4A inceleme: yaz() ile ayni kilit — suren bir yazma bitmeden kapatilmaz,
        # kapandiktan sonra yazma AttributeError degil acik hata alir
        with self._kilit:
            kart, self._kart = self._kart, None
            if kart is not None:
                kart.kapat()

    def satir_oku(self, zaman_asimi: float = 0.5) -> str | None:
        if self._kart is None:
            self._dene()
            if self._kart is None:
                time.sleep(min(zaman_asimi, 0.2))
                return None
        if self._bekleyen:
            return self._bekleyen.pop(0)
        kart = self._kart
        if kart is None:
            return None
        satir = kart.satir_oku(zaman_asimi)
        if getattr(kart, "kopuk", False):
            ad = kart.ad
            self.kapat()
            self._son_deneme = time.monotonic()
            self._soyle(f"! kopru: kart baglantisi koptu ({ad}) — yeniden araniyor")
        return satir

    def yaz(self, metin: str) -> None:
        with self._kilit:
            if self._kart is None:
                raise RuntimeError("kart bagli degil — USB kablosu 'COM' soketinde mi?")
            self._kart.yaz(metin)


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
        self._yeni = threading.Event()

    @property
    def ad(self) -> str:
        return f"kayit:{len(self._satirlar)} satir"

    def ac(self) -> None:
        self._i = 0

    def sifirla(self, bekle: float = 0.0) -> bool:
        """`SeriKart.sifirla()` ile AYNI YUZEY — kaydi bastan oynatir.

        Bringup kosucusu iki kart tipini ayirt etmek zorunda kalmasin
        diye var; yoksa kosucunun icinde `isinstance` dali dogar ve
        kayitli kosu gercek kosudan AYRISIR.
        """
        self._i = 0
        return True

    def kapat(self) -> None:
        pass

    def satir_oku(self, zaman_asimi: float = 0.5) -> str | None:
        if self._i >= len(self._satirlar):
            # 4A inceleme: kayit bitince BEKLE — olu tekrarda kopru dongusu bos
            # donup bir cekirdegi %100 yakiyordu (SeriKart da zaman asimina uyar).
            # Komut yaniti gelince (yaz) bekleme hemen kesilir.
            self._yeni.wait(zaman_asimi)
            self._yeni.clear()
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
        self._yeni.set()
