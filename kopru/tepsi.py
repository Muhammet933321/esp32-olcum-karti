# -*- coding: utf-8 -*-
"""Windows bildirim alani (sistem tepsisi) simgesi — PC uygulamasi konsolsuz calisirken.

Kullanici (2026-10-06): "CMD acik kaliyor ve gozukuyor ... onu kapattigimda baglanti kapaniyor.
Bunu arka planda yapamaz miyiz? Kapatmak istedigimde de [gizli simgeler] yerinden kapatilabilir olsun."

    simge ustune gelince   durum ipucu ("Olcum Karti — WiFi'den bagli" ...)
    cift tik               paneli ac
    sag tik                menu: Paneli ac · Kapat

YALNIZ standart kutuphane (ctypes, Win32 Shell_NotifyIconW): pystray/pywin32 kurulumu yok —
projenin bagimlilik kurali. Ayri iplikte kendi pencere + ileti dongusu; kopru (HTTP sunucusu)
ana iplikte. Windows disinda `Tepsi.baslat()` hicbir sey yapmaz (False doner).

⚠ Explorer yeniden baslarsa (gorev cubugu cokup gelir) simge kaybolur: "TaskbarCreated"
  yayini dinlenip simge YENIDEN eklenir.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Callable

IKON = Path(__file__).resolve().parent / "olcum-karti.ico"
IPUCU_AZAMI = 127                       # szTip[128] (NUL dahil)

KOMUT_PANEL = 1001
KOMUT_KAPAT = 1002

MENU = {"tr": (("Paneli aç", KOMUT_PANEL), None, ("Kapat", KOMUT_KAPAT)),
        "en": (("Open panel", KOMUT_PANEL), None, ("Quit", KOMUT_KAPAT))}


def ipucu_metni(etkin: str | None, bagli: bool) -> str:
    """Simgenin ipucu: hangi yoldan bagli (USB / WiFi) ya da kart araniyor."""
    if bagli and etkin == "usb":
        d = "USB'den bağlı"
    elif bagli and etkin == "wifi":
        d = "Wi-Fi'den bağlı"
    else:
        d = "kart aranıyor"
    return f"Ölçüm Kartı — {d}"[:IPUCU_AZAMI]


def kart_durumu(kart) -> tuple[str | None, bool]:
    """Kopru kartindan (SecmeliKart / WifiKart / OtoSeriKart / KayitKart) (etkin yol, bagli mi)."""
    etkin = getattr(kart, "etkin", None)
    if etkin is None:                                   # tek yollu kart
        ad = str(getattr(kart, "ad", "") or "")
        etkin = "wifi" if ad.startswith("wifi") else "usb"
        return etkin, bool(getattr(kart, "bagli", False))
    alt = getattr(kart, etkin, None) if etkin in ("usb", "wifi") else None
    return etkin, bool(getattr(alt, "bagli", False))


class Tepsi:
    """Bildirim alani simgesi. Geri cagirmalar SIMGE IPLIGINDE cagrilir — uzun is yapmasinlar."""

    def __init__(self, ipucu_al: Callable[[], str], paneli_ac: Callable[[], None],
                 kapat: Callable[[], None], ikon: Path | None = IKON, dil: str = "tr",
                 tazele_ms: int = 2000):
        self.ipucu_al, self.paneli_ac, self.kapat = ipucu_al, paneli_ac, kapat
        self.ikon, self.dil, self.tazele_ms = ikon, dil, tazele_ms
        self.eklendi = False                # simge su an bildirim alaninda mi
        self.hwnd = None
        self.son_ipucu = ""
        self.hata: str | None = None
        self._gorev_cubugu = None           # CreateWindowExW sirasinda gelen iletiler bunu okur
        self._hazir = threading.Event()
        self._iplik: threading.Thread | None = None

    # ── genel ────────────────────────────────────────────────────────
    def baslat(self, bekle: float = 5.0) -> bool:
        if sys.platform != "win32":
            return False
        self._iplik = threading.Thread(target=self._dongu, name="tepsi", daemon=True)
        self._iplik.start()
        self._hazir.wait(bekle)
        return self.eklendi

    def durdur(self, bekle: float = 5.0) -> None:
        if self.hwnd and sys.platform == "win32":
            self._w.user32.PostMessageW(self.hwnd, self._w.WM_CLOSE, 0, 0)
        if self._iplik is not None:
            self._iplik.join(bekle)

    def komut(self, kimlik: int) -> None:
        """Menu secimi (testler de dogrudan cagirir)."""
        if kimlik == KOMUT_PANEL:
            self.paneli_ac()
        elif kimlik == KOMUT_KAPAT:
            self.kapat()

    # ── Win32 ────────────────────────────────────────────────────────
    def _dongu(self) -> None:
        try:
            self._w = _Win32()
            self._kur()
            msg = self._w.MSG()
            while self._w.user32.GetMessageW(self._w.byref(msg), None, 0, 0) > 0:
                self._w.user32.TranslateMessage(self._w.byref(msg))
                self._w.user32.DispatchMessageW(self._w.byref(msg))
        except Exception as e:                                  # noqa: BLE001 — kopru olmesin
            self.hata = f"{type(e).__name__}: {e}"
        finally:
            self.eklendi = False
            self._hazir.set()

    def _kur(self) -> None:
        w = self._w
        self._proc = w.WNDPROC(self._ileti)            # referans TUTULMALI (yoksa cop toplanir)
        sinif = "OlcumKartiTepsi"
        wc = w.WNDCLASSEXW()
        wc.cbSize = w.ctypes.sizeof(wc)
        wc.lpfnWndProc = self._proc
        wc.hInstance = w.kernel32.GetModuleHandleW(None)
        wc.lpszClassName = sinif
        w.user32.RegisterClassExW(w.byref(wc))         # ikinci kez (testte) zaten kayitli: sorun degil
        self.hwnd = w.user32.CreateWindowExW(0, sinif, "Olcum Karti", 0, 0, 0, 0, 0, None, None,
                                             wc.hInstance, None)
        if not self.hwnd:
            raise OSError("CreateWindowExW basarisiz")
        self._gorev_cubugu = w.user32.RegisterWindowMessageW("TaskbarCreated")
        self._hicon = None
        if self.ikon and Path(self.ikon).exists():
            self._hicon = w.user32.LoadImageW(None, str(self.ikon), w.IMAGE_ICON, 0, 0,
                                              w.LR_LOADFROMFILE | w.LR_DEFAULTSIZE)
        if not self._hicon:
            self._hicon = w.user32.LoadIconW(None, w.IDI_APPLICATION)
        self._simge(w.NIM_ADD)
        w.user32.SetTimer(self.hwnd, 1, self.tazele_ms, None)
        self._hazir.set()

    def _nid(self, ipucu: str):
        w = self._w
        n = w.NOTIFYICONDATAW()
        n.cbSize = w.ctypes.sizeof(n)
        n.hWnd = self.hwnd
        n.uID = 1
        n.uFlags = w.NIF_MESSAGE | w.NIF_ICON | w.NIF_TIP
        n.uCallbackMessage = w.WM_SIMGE
        n.hIcon = self._hicon
        n.szTip = ipucu[:IPUCU_AZAMI]
        return n

    def _simge(self, islem: int) -> None:
        w = self._w
        if islem == w.NIM_DELETE:
            n = w.NOTIFYICONDATAW()
            n.cbSize = w.ctypes.sizeof(n)
            n.hWnd, n.uID = self.hwnd, 1
            w.shell32.Shell_NotifyIconW(islem, w.byref(n))
            self.eklendi = False
            return
        try:
            ipucu = self.ipucu_al()
        except Exception:                                       # noqa: BLE001
            ipucu = "Ölçüm Kartı"
        if islem == w.NIM_MODIFY and ipucu == self.son_ipucu:
            return
        ok = bool(w.shell32.Shell_NotifyIconW(islem, w.byref(self._nid(ipucu))))
        if islem == w.NIM_ADD:
            self.eklendi = ok
        if ok:
            self.son_ipucu = ipucu

    def _menu(self) -> None:
        w = self._w
        m = w.user32.CreatePopupMenu()
        for oge in MENU.get(self.dil, MENU["tr"]):
            if oge is None:
                w.user32.AppendMenuW(m, w.MF_SEPARATOR, 0, None)
            else:
                w.user32.AppendMenuW(m, w.MF_STRING, oge[1], oge[0])
        w.user32.SetMenuDefaultItem(m, KOMUT_PANEL, 0)
        nokta = w.POINT()
        w.user32.GetCursorPos(w.byref(nokta))
        w.user32.SetForegroundWindow(self.hwnd)         # yoksa menu disina tiklayinca kapanmaz
        secim = w.user32.TrackPopupMenu(m, w.TPM_RETURNCMD | w.TPM_RIGHTBUTTON | w.TPM_NONOTIFY,
                                        nokta.x, nokta.y, 0, self.hwnd, None)
        w.user32.PostMessageW(self.hwnd, w.WM_NULL, 0, 0)
        w.user32.DestroyMenu(m)
        if secim:
            self.komut(secim)

    def _ileti(self, hwnd, ileti, wparam, lparam):
        w = self._w
        try:
            if ileti == w.WM_SIMGE:
                olay = lparam & 0xFFFF
                if olay == w.WM_LBUTTONDBLCLK:
                    self.komut(KOMUT_PANEL)
                elif olay in (w.WM_RBUTTONUP, w.WM_CONTEXTMENU):
                    self._menu()
                return 0
            if ileti == w.WM_TIMER:
                self._simge(w.NIM_MODIFY)
                return 0
            if ileti == self._gorev_cubugu:              # explorer yeniden basladi: simge geri
                self.son_ipucu = ""
                self._simge(w.NIM_ADD)
                return 0
            if ileti == w.WM_CLOSE:
                w.user32.KillTimer(hwnd, 1)
                self._simge(w.NIM_DELETE)
                w.user32.DestroyWindow(hwnd)
                return 0
            if ileti == w.WM_DESTROY:
                w.user32.PostQuitMessage(0)
                return 0
        except Exception as e:                                  # noqa: BLE001
            self.hata = f"{type(e).__name__}: {e}"
        return w.user32.DefWindowProcW(hwnd, ileti, wparam, lparam)


class _Win32:
    """ctypes tanimlari (64 bit: WPARAM/LPARAM/HANDLE isaretci boyu — argtypes SART)."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes as wt
        self.ctypes, self.byref = ctypes, ctypes.byref
        LRESULT = ctypes.c_ssize_t
        self.WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", self.WNDPROC),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON), ("hCursor", wt.HANDLE),
                        ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                        ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]

        class GUID(ctypes.Structure):
            _fields_ = [("a", wt.DWORD), ("b", wt.WORD), ("c", wt.WORD), ("d", ctypes.c_ubyte * 8)]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT),
                        ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON), ("szTip", wt.WCHAR * 128),
                        ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD), ("szInfo", wt.WCHAR * 256),
                        ("uVersion", wt.UINT), ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
                        ("guidItem", GUID), ("hBalloonIcon", wt.HICON)]

        self.WNDCLASSEXW, self.NOTIFYICONDATAW = WNDCLASSEXW, NOTIFYICONDATAW
        self.MSG, self.POINT = wt.MSG, wt.POINT
        u, s, k = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("shell32"), ctypes.WinDLL("kernel32")
        self.user32, self.shell32, self.kernel32 = u, s, k
        P = ctypes.c_void_p
        imza = {
            (u, "RegisterClassExW"): ([P], wt.ATOM),
            (u, "CreateWindowExW"): ([wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, P], wt.HWND),
            (u, "DefWindowProcW"): ([wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM], LRESULT),
            (u, "GetMessageW"): ([P, wt.HWND, wt.UINT, wt.UINT], wt.BOOL),
            (u, "TranslateMessage"): ([P], wt.BOOL),
            (u, "DispatchMessageW"): ([P], LRESULT),
            (u, "PostMessageW"): ([wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM], wt.BOOL),
            (u, "PostQuitMessage"): ([ctypes.c_int], None),
            (u, "DestroyWindow"): ([wt.HWND], wt.BOOL),
            (u, "RegisterWindowMessageW"): ([wt.LPCWSTR], wt.UINT),
            (u, "LoadImageW"): ([wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT], wt.HANDLE),
            (u, "LoadIconW"): ([wt.HINSTANCE, P], wt.HICON),
            (u, "SetTimer"): ([wt.HWND, ctypes.c_size_t, wt.UINT, P], ctypes.c_size_t),
            (u, "KillTimer"): ([wt.HWND, ctypes.c_size_t], wt.BOOL),
            (u, "CreatePopupMenu"): ([], wt.HMENU),
            (u, "AppendMenuW"): ([wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR], wt.BOOL),
            (u, "SetMenuDefaultItem"): ([wt.HMENU, wt.UINT, wt.UINT], wt.BOOL),
            (u, "TrackPopupMenu"): ([wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, P],
                                    ctypes.c_int),
            (u, "DestroyMenu"): ([wt.HMENU], wt.BOOL),
            (u, "GetCursorPos"): ([P], wt.BOOL),
            (u, "SetForegroundWindow"): ([wt.HWND], wt.BOOL),
            (s, "Shell_NotifyIconW"): ([wt.DWORD, P], wt.BOOL),
            (k, "GetModuleHandleW"): ([wt.LPCWSTR], wt.HMODULE),
        }
        for (dll, ad), (arg, don) in imza.items():
            f = getattr(dll, ad)
            f.argtypes, f.restype = arg, don
        self.WM_NULL, self.WM_CLOSE, self.WM_DESTROY, self.WM_TIMER = 0x0000, 0x0010, 0x0002, 0x0113
        self.WM_CONTEXTMENU, self.WM_RBUTTONUP, self.WM_LBUTTONDBLCLK = 0x007B, 0x0205, 0x0203
        self.WM_SIMGE = 0x8000 + 1                       # WM_APP + 1
        self.NIM_ADD, self.NIM_MODIFY, self.NIM_DELETE = 0, 1, 2
        self.NIF_MESSAGE, self.NIF_ICON, self.NIF_TIP = 1, 2, 4
        self.IMAGE_ICON, self.LR_LOADFROMFILE, self.LR_DEFAULTSIZE = 1, 0x10, 0x40
        self.IDI_APPLICATION = ctypes.c_void_p(32512)
        self.MF_STRING, self.MF_SEPARATOR = 0x0, 0x800
        self.TPM_RETURNCMD, self.TPM_RIGHTBUTTON, self.TPM_NONOTIFY = 0x100, 0x2, 0x80
