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

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import http.server
import socket
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

BURASI = Path(__file__).resolve().parent
PORT = 8772
YEDEK_PORT = 8773


class Sunucu(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(BURASI), **k)

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
