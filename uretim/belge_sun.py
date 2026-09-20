# -*- coding: utf-8 -*-
"""BELGELER/ klasorunu ag uzerinden sunar — tezgahta telefondan okumak icin.

Kullanici (2026-09-20): "kutuyu hazirlarken 3B'ye bakamiyorum." Belgeler
PC'de `file://` olarak duruyordu; tezgahta elde telefon oluyor. Bu betik
ayni Wi-Fi'daki telefondan acilacak bir adres veriyor.

    python belge_sun.py              # http://<pc-ip>:8099/8-kutu.html
    python belge_sun.py --port 9000
    python belge_sun.py --ac         # PC'de tarayiciyi da acar

Yalniz standart kutuphane (projenin kurali). Sunucu SALT OKUNUR ve
yalnizca BELGELER/ altini veriyor.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import socketserver
import webbrowser
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
BELGELER = KOK / "BELGELER"
VARSAYILAN_PORT = 8099


def yerel_adresler() -> list[str]:
    """Bu makinenin LAN adres(ler)i — telefondan yazilacak olan."""
    adresler = []
    try:                                    # disari cikan arayuzun adresi
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            adresler.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for bilgi in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = bilgi[4][0]
            if not ip.startswith("127.") and ip not in adresler:
                adresler.append(ip)
    except OSError:
        pass
    return adresler or ["127.0.0.1"]


class Susturulmus(http.server.SimpleHTTPRequestHandler):
    def log_message(self, bicim, *arg):     # her istek icin satir basmasin
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=VARSAYILAN_PORT)
    ap.add_argument("--ac", action="store_true", help="PC'de tarayiciyi ac")
    a = ap.parse_args()
    if not BELGELER.exists():
        print(f"! {BELGELER} yok")
        return 1
    islem = functools.partial(Susturulmus, directory=str(BELGELER))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", a.port), islem) as sunucu:
        print("  BELGELER sunuluyor — Ctrl-C ile durdur\n")
        for ip in yerel_adresler():
            print(f"    http://{ip}:{a.port}/8-kutu.html      (kutu kılavuzu)")
            print(f"    http://{ip}:{a.port}/7-yerlesim.html  (kart yerleşimi)")
            print(f"    http://{ip}:{a.port}/                 (hepsi)")
        print("\n  Telefon aynı Wi-Fi'da olmalı. Güvenlik duvarı sorarsa izin ver.")
        if a.ac:
            webbrowser.open(f"http://127.0.0.1:{a.port}/8-kutu.html")
        try:
            sunucu.serve_forever()
        except KeyboardInterrupt:
            print("\n  durduruldu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
