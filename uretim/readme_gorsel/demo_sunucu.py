"""arayuz3/sunucu.py'nin cok is parcacikli kopyasi — yalniz README ekran goruntuleri icin.

Asil sunucu tek is parcacikli: Chromium'un acik tuttugu bos baglantilar onu kilitliyor,
cek.js'in paralel isleri zaman asimina dusuyordu. Kullanim: py demo_sunucu.py  (port 8772)
"""
import os
import socketserver
import sys
from pathlib import Path

ARAYUZ = Path(__file__).resolve().parents[2] / "arayuz3"
os.chdir(ARAYUZ)
sys.path.insert(0, str(ARAYUZ))
sys.argv.append("--sessiz")
import sunucu  # noqa: E402


class CokluSunucu(socketserver.ThreadingMixIn, sunucu.TCPSunucu):
    daemon_threads = True


with CokluSunucu(("127.0.0.1", 8772), sunucu.Sunucu) as s:
    print("demo panel: http://localhost:8772/?demo", flush=True)
    s.serve_forever()
