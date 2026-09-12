"""tarayici.py — headless Edge'i CDP ile suren KUCUK arac (yalnizca stdlib).

NEDEN VAR (B27 A2, 2026-09-12): `msedge --headless --screenshot` tek URL
acip resim cekiyor; tiklayamiyor, JS calistiramiyor, Basic Auth
sorusuna cevap veremiyor. Kartin sayfasi acilir acilmaz `?` gonderiyor,
sunucu 401 donuyor, headless tarayici o istegi SONSUZA KADAR askida
tutuyor ve `--timeout` ile alinan goruntude sayfa "bagli ama veri yok"
gorunuyor. Yani sayfa degil, olcum araci bozuktu. Bu arac auth isteklerini
CDP'den yakalayip IPTAL ediyor (kart 401 doner, arayuz "komut
gonderilemedi (401)" der — GERCEK davranis), sonra sayfada JS
degerlendirip ekran goruntusu alabiliyor.

Kullanim:
    from tarayici import Tarayici
    with Tarayici() as t:
        t.git("http://olcum.local/#/olcum")
        t.bekle(4)
        n = t.js("document.querySelectorAll('.olcum').length")
        t.goruntu("cikti.png")

Komut satiri:
    python tarayici.py URL CIKTI.png [bekle_sn] [js-ifadesi]

WebSocket istemcisi RFC 6455'in istemci tarafinin ASGARI alt kumesi:
metin cerceveleri, maskeleme, 3 uzunluk bicimi, parcalanma YOK (CDP tek
parca yollar), ping'e pong. Baska bir sey gerekmiyor.
"""
from __future__ import annotations

import base64
import json
import os
import select
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

EDGE_ADAYLAR = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def _edge_yolu() -> str:
    for y in EDGE_ADAYLAR:
        if os.path.exists(y):
            return y
    raise SystemExit("Edge/Chrome bulunamadi: " + ", ".join(EDGE_ADAYLAR))


class _WS:
    """Asgari WebSocket istemcisi (ws:// yalnizca)."""

    def __init__(self, url: str):
        assert url.startswith("ws://")
        kalan = url[5:]
        hostport, _, yol = kalan.partition("/")
        host, _, port = hostport.partition(":")
        self.s = socket.create_connection((host, int(port or 80)), timeout=30)
        anahtar = base64.b64encode(os.urandom(16)).decode()
        istek = (f"GET /{yol} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
                 f"Connection: Upgrade\r\nSec-WebSocket-Key: {anahtar}\r\n"
                 f"Sec-WebSocket-Version: 13\r\n\r\n")
        self.s.sendall(istek.encode())
        baslik = b""
        while b"\r\n\r\n" not in baslik:
            parca = self.s.recv(4096)
            if not parca:
                raise ConnectionError("WebSocket el sikisma kesildi")
            baslik += parca
        if b" 101 " not in baslik.split(b"\r\n", 1)[0]:
            raise ConnectionError("WebSocket reddedildi: " + baslik[:120].decode(errors="replace"))
        self._kalan = baslik.split(b"\r\n\r\n", 1)[1]

    def _oku(self, n: int) -> bytes:
        while len(self._kalan) < n:
            parca = self.s.recv(65536)
            if not parca:
                raise ConnectionError("WebSocket kapandi")
            self._kalan += parca
        veri, self._kalan = self._kalan[:n], self._kalan[n:]
        return veri

    def gonder(self, metin: str) -> None:
        govde = metin.encode()
        maske = os.urandom(4)
        n = len(govde)
        if n < 126:
            bas = bytes([0x81, 0x80 | n])
        elif n < 65536:
            bas = bytes([0x81, 0x80 | 126]) + struct.pack(">H", n)
        else:
            bas = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", n)
        maskeli = bytes(b ^ maske[i % 4] for i, b in enumerate(govde))
        self.s.sendall(bas + maske + maskeli)

    def al(self) -> str:
        while True:
            b0, b1 = self._oku(2)
            op = b0 & 0x0F
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._oku(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._oku(8))[0]
            if b1 & 0x80:            # sunucu maskelemez; yine de tolere et
                maske = self._oku(4)
                govde = bytes(b ^ maske[i % 4] for i, b in enumerate(self._oku(n)))
            else:
                govde = self._oku(n)
            if op == 0x9:            # ping -> pong
                self.s.sendall(bytes([0x8A, 0x80 | len(govde)]) + b"\0\0\0\0"
                               + bytes(b ^ 0 for b in govde))
                continue
            if op == 0x8:
                raise ConnectionError("WebSocket kapatildi")
            if op in (0x1, 0x0):
                return govde.decode()

    def kapat(self) -> None:
        try:
            self.s.close()
        except OSError:
            pass


class Tarayici:
    def __init__(self, genislik=1280, yukseklik=1000, port=9333, auth_iptal=True):
        """auth_iptal: Basic Auth sorusunu CDP'den iptal et (kart icin sart).

        ⚠ Bunun BEDELI var: `Fetch.enable` HER istegi duraklatiyor ve
        surdurme isi bizim olay dongumuzde. Uzun oturumlarda (10+ gezinme)
        `Page.captureScreenshot` yanit vermez oldu — parolasiz bir sunucuda
        (yerel gelistirme, ?demo) `auth_iptal=False` ver, yakalama hic
        kurulmasin.
        """
        self.port = port
        self.profil = tempfile.mkdtemp(prefix="olcum-edge-")
        self.surec = subprocess.Popen(
            [_edge_yolu(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--no-first-run", "--no-default-browser-check",
             f"--window-size={genislik},{yukseklik}",
             f"--remote-debugging-port={port}",
             f"--user-data-dir={self.profil}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._id = 0
        self.olaylar: list[dict] = []
        hedef = None
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as y:
                    hedefler = json.load(y)
                hedef = next((h for h in hedefler if h.get("type") == "page"), None)
                if hedef:
                    break
            except Exception:
                pass
            time.sleep(0.25)
        if not hedef:
            self.kapat()
            raise RuntimeError("Edge CDP hedefi acilmadi")
        self.ws = _WS(hedef["webSocketDebuggerUrl"])
        self.cagir("Page.enable")
        self.cagir("Runtime.enable")
        if auth_iptal:
            # Basic Auth sorusunu askida birakma: iptal et, sayfa 401'i gorsun
            self.cagir("Fetch.enable", {"handleAuthRequests": True, "patterns": [{"urlPattern": "*"}]})

    # ── CDP ────────────────────────────────────────────────────────
    def cagir(self, yontem: str, params: dict | None = None) -> dict:
        self._id += 1
        kimlik = self._id
        self.ws.gonder(json.dumps({"id": kimlik, "method": yontem, "params": params or {}}))
        while True:
            m = json.loads(self.ws.al())
            if m.get("id") == kimlik:
                if "error" in m:
                    raise RuntimeError(f"{yontem}: {m['error']}")
                return m.get("result", {})
            self._olay(m)

    def _olay(self, m: dict) -> None:
        yontem = m.get("method", "")
        p = m.get("params", {})
        if yontem == "Fetch.authRequired":
            self.ws.gonder(json.dumps({"id": 0, "method": "Fetch.continueWithAuth",
                                       "params": {"requestId": p["requestId"],
                                                  "authChallengeResponse": {"response": "CancelAuth"}}}))
        elif yontem == "Fetch.requestPaused":
            self.ws.gonder(json.dumps({"id": 0, "method": "Fetch.continueRequest",
                                       "params": {"requestId": p["requestId"]}}))
        elif yontem == "Runtime.consoleAPICalled":
            self.olaylar.append({"tur": "console", "seviye": p.get("type"),
                                 "metin": " ".join(str(a.get("value", a.get("description", "")))
                                                    for a in p.get("args", []))})
        elif yontem == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails", {})
            self.olaylar.append({"tur": "hata", "metin": d.get("text", "") + " " +
                                 str(d.get("exception", {}).get("description", ""))})

    def bekle(self, sn: float) -> None:
        """Olaylari islemeye devam ederek `sn` saniye bekle.

        🔴 Once soket zaman asimi 0.25 s'ye cekilip `al()` cagriliyordu.
        Zaman asimi CERCEVE ORTASINDA dusunce `al()` zaten okudugu 2
        baslik baytini kaybediyor ve akis KAYIYOR — sonraki her CDP
        yaniti coz​ulemez oluyordu (acik tema render'i boyle dustu).
        Artik once `select` ile VERI VAR MI diye bakiliyor; `al()` hep
        tam cerceve okuyor.
        """
        son = time.monotonic() + sn
        while True:
            kalan = son - time.monotonic()
            if kalan <= 0:
                return
            hazir, _, _ = select.select([self.ws.s], [], [], min(0.25, kalan))
            if hazir:
                self._olay(json.loads(self.ws.al()))

    # ── sayfa ───────────────────────────────────────────────────────
    def tema(self, ad: str) -> None:
        """`dark` / `light` / `` (sistem) — prefers-color-scheme'i taklit et.

        B27 A2: acik tema yalnizca belirtec degerlerini degistiriyor;
        "bir temada guzel, otekinde okunaksiz" halini GORMEDEN iddia
        edemeyiz. Bu, iki temayi da headless'ta render etmenin yolu.
        """
        ozellikler = [{"name": "prefers-color-scheme", "value": ad}] if ad else []
        self.cagir("Emulation.setEmulatedMedia", {"features": ozellikler})

    def ekran(self, genislik: int, yukseklik: int, dpr: float = 2.0,
              mobil: bool = True) -> None:
        """Gercek bir telefon ekrani taklidi (CDP device metrics).

        🔴 `--window-size=390,844` YETMIYOR: Windows'ta pencere ~500 px'in
        altina inmiyor, yani "390 px testi" aslinda 496 px'te kosuyordu ve
        telefon kirilimi HIC sinanmamis oluyordu. Bu cagri viewport'u
        dogrudan ayarliyor.
        """
        self.cagir("Emulation.setDeviceMetricsOverride", {
            "width": genislik, "height": yukseklik,
            "deviceScaleFactor": dpr, "mobile": mobil,
        })

    def git(self, url: str) -> None:
        self.cagir("Page.navigate", {"url": url})
        self.bekle(0.5)

    def js(self, ifade: str):
        r = self.cagir("Runtime.evaluate", {"expression": ifade, "returnByValue": True,
                                            "awaitPromise": True})
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise RuntimeError("JS hatasi: " + str(d.get("text")) + " "
                               + str(d.get("exception", {}).get("description", ""))[:300])
        return r.get("result", {}).get("value")

    def goruntu(self, yol: str) -> None:
        r = self.cagir("Page.captureScreenshot", {"format": "png"})
        with open(yol, "wb") as f:
            f.write(base64.b64decode(r["data"]))

    def hatalar(self) -> list[str]:
        return [o["metin"] for o in self.olaylar
                if o["tur"] == "hata" or o.get("seviye") == "error"]

    def kapat(self) -> None:
        try:
            self.ws.kapat()
        except Exception:
            pass
        try:
            self.surec.kill()
            self.surec.wait(timeout=5)
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kapat()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    url, cikti = sys.argv[1], sys.argv[2]
    bekle = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    ifade = sys.argv[4] if len(sys.argv) > 4 else ""
    with Tarayici() as t:
        t.git(url)
        t.bekle(bekle)
        if ifade:
            print(json.dumps(t.js(ifade), ensure_ascii=False))
        t.goruntu(cikti)
        for h in t.hatalar():
            print("! " + h)
        print("goruntu:", cikti)
