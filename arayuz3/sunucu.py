# -*- coding: utf-8 -*-
"""Olcum Karti ASAMA 3 arayuzunu yerel sunucudan servis eder.

    python sunucu.py

NEDEN SUNUCU GEREKLI: Web Serial API guvenli baglam (secure context) ister.
`file://` ile acilan sayfada `navigator.serial` yoktur. `http://localhost`
guvenli sayilir, o yuzden arayuz buradan servis ediliyor.

NEDEN AYRI ARAYUZ: Asama 2'nin arayuzu (../arayuz) o firmware'in
protokoluyle konusuyor ve Asama 2 zinciri (A5) bunu `v12.05` gibi komut
biciminden SINIYOR. Asama 3'un protokolu farkli:
  * D satirinda 8. alan var: <menzil>
  * gerilim kalibrasyonu `v` degil `g`, ayrica `z` (sifir) eklendi
  * `Z` akim sifiri (Asama 2'de `z` idi), `n`/`y`/`a` menzil komutlari
Ayni dosyayi ikisine birden uydurmaya calismak, DEVIR 4.1'deki sessiz
ayrisma hatasinin daveti olurdu.

BUTUN VARLIKLAR BU DIZINDE (B22.0, 2026-09-10). Eskiden `style.css` ve
`vendor/vue.global.prod.js` ../arayuz icinde duruyordu ve burada bulunmayan
dosya oraya dusuruluyordu ("tek kopya kalsin" diye). 5.12.32'de ../arayuz
`arsiv/asama1/arayuz`'a tasindi, bu dosya guncellenmedi ve iki varlik da
404 vermeye basladi: Vue yuklenmiyor -> `app.js` ReferenceError ile oluyor
-> ekranda ham `{{ }}` sablonu kaliyor. Zincir 15/15 yesildi, cunku hicbir
test dosya VARLIGINA bakmiyordu.

Kusuru duzeltmek yerine kusuru ureten mekanizma kaldirildi: dusme yolu yok,
varliklar burada. Asama 1/2 zaten arsivde oldugu icin "tek kopya" gerekcesi
de gecerliligini yitirmisti.

3A (P4) — `/ortak/<ad>.js` -> `ortak/src/<ad>.js`. Bu bir DUSME DEGIL:
YALNIZCA bu onek, YALNIZCA o dizin, YALNIZCA `<ad>.js` bicimi. arayuz3'te
olmayan bir dosya hala 404 (test_kopru.py `/disari.js` ile sinar). Ayni
yolu kart (LittleFS `/ortak/`) ve kopru de sunuyor: panel `import ...
from '/ortak/x.js'` dediginde uc yerde de AYNI dosya gelir.

`.js` MIME turu ELLE: `app.js` artik ES modulu ve tarayici modul betigini
yalnizca JavaScript MIME turuyle calistiriyor. `mimetypes` Windows'ta
kayit defterini okuyor ve orada `.js` -> `text/plain` olabiliyor; o
makinede arayuz HIC acilmazdi.

3H-1 (AY6) — `/kunye.json`: kartin arayuz goruntusune `uretim/arayuz-uret.py`
uretilmis bir kunye koyuyor (panel surumu). Burada AYNI islevle (`kunye_hesapla`)
KAYNAKTAN uretiliyor — gelistirme sunucusu da surum gostersin; uretec yoksa 404.

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
import re
import socket
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

BURASI = Path(__file__).resolve().parent
ORTAK = BURASI.parent / "ortak" / "src"
# 3H-1: goruntu ureteci YALNIZ ice aktariliyor (kunye_hesapla) — ondan dosya SUNULMAZ.
URETEC = BURASI.parent / "uretim" / "arayuz-uret.py"
ORTAK_AD = re.compile(r"[a-z0-9_-]+\.js")
JS_TURU = "text/javascript"
PORT = 8772
YEDEK_PORT = 8773


class Sunucu(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": JS_TURU}

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(BURASI), **k)

    def do_GET(self):
        yol = urllib.parse.urlsplit(self.path).path
        if yol == "/kunye.json":
            return self._kunye()
        if yol.startswith("/ortak/"):
            return self._ortak(yol[len("/ortak/"):])
        return super().do_GET()

    def _kunye(self):
        if not URETEC.is_file():
            return self.send_error(404, "kunye yok (uretec bulunamadi)")
        oz = importlib.util.spec_from_file_location("arayuz_uret", URETEC)
        u = importlib.util.module_from_spec(oz)
        oz.loader.exec_module(u)
        try:
            govde = json.dumps(u.kunye_hesapla(), separators=(",", ":")).encode("utf-8")
        except (OSError, SystemExit) as h:
            return self.send_error(503, f"kunye uretilemedi: {h}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def _ortak(self, ad: str):
        dosya = ORTAK / ad
        if not ORTAK_AD.fullmatch(ad) or not dosya.is_file():
            return self.send_error(404, "ortak modulu yok")
        govde = dosya.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", JS_TURU + "; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def end_headers(self):
        # Gelistirme sirasinda tarayici eski dosyayi tutmasin
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, bicim, *args):
        if "--sessiz" not in sys.argv:
            super().log_message(bicim, *args)


class TCPSunucu(socketserver.TCPServer):
    allow_reuse_address = True
    # Windows'ta allow_reuse_address baska bir surecin aktif tuttugu portu
    # ele gecirmeye izin verir; yedek porta dusme hic tetiklenmez.
    if sys.platform == "win32":
        allow_reuse_address = False


def bos_port() -> int:
    for p in (PORT, YEDEK_PORT):
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
    raise SystemExit(f"{PORT} ve {YEDEK_PORT} mesgul.")


def main() -> None:
    port = bos_port()
    adres = f"http://localhost:{port}/"

    with TCPSunucu(("127.0.0.1", port), Sunucu) as sunucu:
        print(f"Olcum Karti ASAMA 3 arayuzu: {adres}")
        print("Kapatmak icin Ctrl+C")
        if "--sessiz" not in sys.argv:
            threading.Timer(0.4, lambda: webbrowser.open(adres)).start()
        try:
            sunucu.serve_forever()
        except KeyboardInterrupt:
            print("\nkapatildi")


if __name__ == "__main__":
    main()
