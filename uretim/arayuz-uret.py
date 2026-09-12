# -*- coding: utf-8 -*-
"""B22.5 — arayuzu LittleFS goruntusune paketler.

    python arayuz-uret.py

`arayuz3/` -> gzip -> `uretim/_fs/` -> mklittlefs -> `uretim/_fs.bin`

⚠ HICBIR ADRES ELLE YAZILMIYOR. Bolum ofseti ve boyutu, derlemede
  kullanilan `huge_app.csv`'den OKUNUYOR. Elle yazilsaydi bolum semasi
  degistiginde goruntu yanlis adrese yazilir ve kart sessizce bos bir
  dosya sistemi gorurdu.

⚠ SIKISTIRMA CALISMA ANINDA DEGIL BURADA. `serveStatic` bir dosyayi
  bulamayinca `<yol>.gz` ariyor ve bulursa `Content-Encoding: gzip`
  basligini KENDISI koyuyor (RequestHandlersImpl.h:209-215). Yani kartta
  hicbir sikistirma kodu kosmuyor.

⚠ `sahte-kart.js` GORUNTUYE GIRMIYOR (15 936 B, yalnizca `?demo` icin).
  Karttan `?demo` acilirsa `betikYukle` sebebini soyleyip duruyor —
  sessizce bos ekran degil.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"
SAHNE = BURASI / "_fs"
GORUNTU = BURASI / "_fs.bin"
KUNYE = BURASI / "_fs.json"

# LittleFS blok/sayfa olculeri — ESP32 flash icin sabit.
BLOK, SAYFA = 4096, 256

# Goruntuye giren varliklar. `index.html`'in referanslariyla AYNI olmali;
# `sim3_web.py` bunu denetliyor (bir varlik unutulursa kart onu 404
# verir ve arayuz sessizce bozulur — B22.0'da tam bu olmustu).
VARLIKLAR = [
    "index.html",
    "app.js",
    "style.css",
    "vendor/vue.global.prod.js",
    "manifest.json",
    "ikon-180.png",
]

# Zaten sikistirilmis olanlar tekrar gzip'lenmiyor — PNG buyurdu.
GZIPLENMEYEN = {".png", ".jpg", ".gz", ".woff2"}


def araclar() -> tuple[Path, Path, Path]:
    """mklittlefs, esptool ve huge_app.csv — makineye ozgu, ARANIYOR."""
    kok = os.environ.get("LOCALAPPDATA")
    if not kok:
        raise SystemExit("LOCALAPPDATA yok — Windows disi ortam")
    taban = Path(kok) / "Arduino15" / "packages" / "esp32"
    mk = next(iter(sorted((taban / "tools" / "mklittlefs").glob("*/mklittlefs.exe"),
                          reverse=True)), None)
    esp = next(iter(sorted((taban / "tools" / "esptool_py").glob("*/esptool.exe"),
                           reverse=True)), None)
    csv = next(iter(sorted((taban / "hardware" / "esp32").glob(
        "*/tools/partitions/huge_app.csv"), reverse=True)), None)
    for ad, y in (("mklittlefs", mk), ("esptool", esp), ("huge_app.csv", csv)):
        if y is None:
            raise SystemExit(f"{ad} bulunamadi — ESP32 cekirdegi kurulu mu?")
    return mk, esp, csv


def bolum(csv: Path) -> tuple[int, int]:
    """huge_app.csv'den spiffs bolumunun (ofset, boyut) degerleri."""
    for sat in csv.read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in sat.split(",")]
        if len(p) >= 5 and p[0] == "spiffs":
            return int(p[3], 0), int(p[4], 0)
    raise SystemExit("huge_app.csv icinde spiffs bolumu yok")


def kaynak_ozeti() -> dict:
    """Her varligin KAYNAK sha256'si — goruntunun bayatligini yakalar."""
    o = {}
    for ad in VARLIKLAR:
        y = ARAYUZ / ad
        if not y.exists():
            raise SystemExit(f"varlik yok: {ad}  (once ikon-uret.py kostur)")
        o[ad] = hashlib.sha256(y.read_bytes()).hexdigest()
    return o


def main() -> int:
    mk, esp, csv = araclar()
    ofset, boyut = bolum(csv)
    ozet = kaynak_ozeti()

    shutil.rmtree(SAHNE, ignore_errors=True)
    SAHNE.mkdir(parents=True)
    toplam = 0
    print(f"  {'varlik':<30} {'ham':>9} {'goruntude':>10}")
    print("  " + "-" * 52)
    for ad in VARLIKLAR:
        kaynak = ARAYUZ / ad
        ham = kaynak.read_bytes()
        if kaynak.suffix.lower() in GZIPLENMEYEN:
            hedef = SAHNE / ad
            veri = ham
        else:
            hedef = SAHNE / (ad + ".gz")
            # mtime=0: ayni girdi ayni cikti versin (yeniden uretilebilir).
            veri = gzip.compress(ham, 9, mtime=0)
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(veri)
        toplam += len(veri)
        print(f"  {ad:<30} {len(ham):>9} {len(veri):>10}")
    print("  " + "-" * 52)
    print(f"  {'TOPLAM':<30} {'':>9} {toplam:>10} B")

    d = subprocess.run([str(mk), "-c", str(SAHNE), "-b", str(BLOK),
                        "-p", str(SAYFA), "-s", str(boyut), str(GORUNTU)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if d.returncode != 0:
        print(d.stdout[-2000:])
        print(d.stderr[-2000:])
        raise SystemExit("mklittlefs basarisiz")

    n = GORUNTU.stat().st_size
    if n > boyut:
        raise SystemExit(f"goruntu {n} B, bolum {boyut} B — SIGMIYOR")

    KUNYE.write_text(json.dumps({
        "kaynak": ozet,
        "ofset": hex(ofset),
        "bolum_boyut": boyut,
        "icerik_bayt": toplam,
        "goruntu_bayt": n,
        "blok": BLOK, "sayfa": SAYFA,
    }, indent=2), encoding="utf-8")

    # Sahne dizini yalnizca mklittlefs icin gerekliydi — birakmak
    # goruntuyle ayrisabilecek ikinci bir kopya olurdu.
    shutil.rmtree(SAHNE, ignore_errors=True)

    print()
    print(f"  goruntu : {GORUNTU.name}  {n} B  (bolum {boyut} B, "
          f"%{100.0 * toplam / boyut:.1f} dolu)")
    print(f"  ofset   : {hex(ofset)}   (huge_app.csv'den OKUNDU)")
    print(f"  kunye   : {KUNYE.name}")
    print()
    print("  Karta yazmak icin:  python arayuz-yaz.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
