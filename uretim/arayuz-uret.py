# -*- coding: utf-8 -*-
"""B22.5 — arayuzu LittleFS goruntusune paketler.

    python arayuz-uret.py

`arayuz3/` -> gzip -> `uretim/_fs/` -> mklittlefs -> `uretim/_fs.bin`

⚠ HICBIR ADRES ELLE YAZILMIYOR. Bolum ofseti ve boyutu, derlemede
  cizim klasorundeki `kod/olcum-karti-a3/partitions.csv`'den OKUNUYOR
  (B72; derleme de onu kullaniyor). Elle yazilsaydi bolum semasi
  degistiginde goruntu yanlis adrese yazilir ve kart sessizce bos bir
  dosya sistemi gorurdu.

⚠ SIKISTIRMA CALISMA ANINDA DEGIL BURADA. `serveStatic` bir dosyayi
  bulamayinca `<yol>.gz` ariyor ve bulursa `Content-Encoding: gzip`
  basligini KENDISI koyuyor (RequestHandlersImpl.h:209-215). Yani kartta
  hicbir sikistirma kodu kosmuyor.

⚠ `sahte-kart.js` GORUNTUYE GIRMIYOR (15 936 B, yalnizca `?demo` icin).
  Karttan `?demo` acilirsa `betikYukle` sebebini soyleyip duruyor —
  sessizce bos ekran degil.

3A (P4) — ES MODULLERI DE GORUNTUDE:
  * `arayuz3/ekran/*.js`  -> `/ekran/*.js`   (yeni ekranlar; `app.js` import ediyor)
  * `ortak/src/*.js`      -> `/ortak/*.js`   (alt proje 2'nin paylasilan hesabi)
  Ikisi de DIZINDEN okunuyor, elle liste degil: yeni bir ekran ya da ortak
  modul eklenince goruntu onu kendiliginden alir; unutulan bir dosya kartta
  404 olur ve modul grafigi HIC yuklenmez (`onerror` -> "acilmadi" kutusu).
  `VARLIKLAR` sayfanin <script>/<link> ile ISTEDIGI dosyalar olarak kaldi.
  Kunye (`_fs.json`) goruntu yolunu anahtar tutuyor; kaynagi `kaynak_yolu()`
  cozuyor — `arayuz-yaz.py` ve `sim3_web.py` bayatlik denetiminde AYNI
  fonksiyonu kullaniyor (iki kopya kural ayrisirdi).
  Butce (P5): icerik (gzip) <= 600 KB, `ortak/` dahil — `sim3_web.py` 6m.

3H-1 (AY6) — PANEL SURUMU: goruntuye URETILMIS bir `kunye.json` da giriyor
  (`panel_kunyesi`: kaynak ozetlerinin sha256'si, ilk 12 onaltilik + dosya
  sayisi + icerik bayti). Kaynagi YOK (kunyenin `kaynak`inda degil, bayatlik
  denetimi onu aramaz); `bayt`ta ve `icerik_bayt`ta sayiliyor. Panel Ayarlar ->
  Gelismis'te `/kunye.json`dan okuyor; `arayuz3/sunucu.py` ayni islevle
  (`kunye_hesapla`) kaynaktan uretip sunuyor. B7 surumu `_fs.json`dan node'da
  yeniden hesaplayip `panel_surum` ile karsilastiriyor (iki dil, tek kural).
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
ORTAK = KOK / "ortak" / "src"
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

# 3A: dizinden okunan ES modulleri (goruntu oneki, kaynak dizini).
EKRAN_ONEK = "ekran/"
ORTAK_ONEK = "ortak/"


def goruntu_listesi() -> list[str]:
    """Goruntuye giren HER dosyanin goruntudeki yolu (`/` sonrasi)."""
    ekran = sorted(EKRAN_ONEK + p.name for p in (ARAYUZ / "ekran").glob("*.js"))
    ortak = sorted(ORTAK_ONEK + p.name for p in ORTAK.glob("*.js"))
    return list(VARLIKLAR) + ekran + ortak


def kaynak_yolu(ad: str) -> Path:
    """Goruntu yolundan kaynak dosyaya: `ortak/x.js` -> `ortak/src/x.js`,
    gerisi `arayuz3/` altinda. Sunucularin `/ortak/` esleme kuraliyla AYNI."""
    if ad.startswith(ORTAK_ONEK):
        return ORTAK / ad[len(ORTAK_ONEK):]
    return ARAYUZ / ad


def sikistir(ad: str) -> tuple[bytes, bool]:
    """Varligin goruntudeki baytlari ve gzip'li mi (ayni girdi ayni cikti: mtime=0)."""
    ham = kaynak_yolu(ad).read_bytes()
    if kaynak_yolu(ad).suffix.lower() in GZIPLENMEYEN:
        return ham, False
    return gzip.compress(ham, 9, mtime=0), True


def panel_surumu(ozet: dict) -> str:
    """Kaynak ozetlerinden panel surumu: sha256("<ad>:<sha256>\\n" ad sirasinda), ilk 12."""
    satirlar = "".join(f"{ad}:{ozet[ad]}\n" for ad in sorted(ozet))
    return hashlib.sha256(satirlar.encode("utf-8")).hexdigest()[:12]


def panel_kunyesi(ozet: dict, icerik_bayt: int) -> dict:
    """Goruntuye giren `kunye.json` (AY6). `icerik_bayt` kunyenin KENDISI haric."""
    return {"bicim": 1, "surum": panel_surumu(ozet), "dosya": len(ozet), "icerik_bayt": icerik_bayt}


def kunye_hesapla() -> dict:
    """Kaynaktan, goruntu uretmeden: `arayuz3/sunucu.py` `/kunye.json` icin."""
    return panel_kunyesi(kaynak_ozeti(), sum(len(sikistir(ad)[0]) for ad in goruntu_listesi()))


def araclar() -> tuple[Path, Path, Path]:
    """mklittlefs ve esptool makineye ozgu, ARANIYOR. Bolum tablosu TEK
    kaynaktan: cizim klasorundeki partitions.csv (B72; cekirdegin
    huge_app.csv'sini gecersiz kilan dosya)."""
    kok = os.environ.get("LOCALAPPDATA")
    if not kok:
        raise SystemExit("LOCALAPPDATA yok — Windows disi ortam")
    taban = Path(kok) / "Arduino15" / "packages" / "esp32"
    mk = next(iter(sorted((taban / "tools" / "mklittlefs").glob("*/mklittlefs.exe"),
                          reverse=True)), None)
    esp = next(iter(sorted((taban / "tools" / "esptool_py").glob("*/esptool.exe"),
                           reverse=True)), None)
    csv = KOK / "kod" / "olcum-karti-a3" / "partitions.csv"
    for ad, y in (("mklittlefs", mk), ("esptool", esp), ("partitions.csv", csv)):
        if y is None or not Path(y).exists():
            raise SystemExit(f"{ad} bulunamadi — ESP32 cekirdegi kurulu mu?")
    return mk, esp, csv


def bolum(csv: Path) -> tuple[int, int]:
    """partitions.csv'den spiffs bolumunun (ofset, boyut) degerleri."""
    for sat in csv.read_text(encoding="utf-8").splitlines():
        sat = sat.split("#", 1)[0]
        p = [x.strip() for x in sat.split(",")]
        if len(p) >= 5 and p[0] == "spiffs":
            return int(p[3], 0), int(p[4], 0)
    raise SystemExit("partitions.csv icinde spiffs bolumu yok")


def kaynak_ozeti() -> dict:
    """Her varligin KAYNAK sha256'si — goruntunun bayatligini yakalar."""
    o = {}
    for ad in goruntu_listesi():
        y = kaynak_yolu(ad)
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
    gz = []                  # goruntude `.gz` olarak duranlar (kunyede)
    # 3D: dosya basina goruntudeki bayt — B7 acilis kumesinin (index + varliklar +
    # app.js'in statik ice aktarma agaci) butcesini bundan topluyor.
    bayt = {}
    print(f"  {'varlik':<30} {'ham':>9} {'goruntude':>10}")
    print("  " + "-" * 52)
    for ad in goruntu_listesi():
        ham = kaynak_yolu(ad).read_bytes()
        # mtime=0: ayni girdi ayni cikti versin (yeniden uretilebilir).
        veri, sikisik = sikistir(ad)
        hedef = SAHNE / (ad + ".gz" if sikisik else ad)
        if sikisik:
            gz.append(ad)
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(veri)
        toplam += len(veri)
        bayt[ad] = len(veri)
        print(f"  {ad:<30} {len(ham):>9} {len(veri):>10}")
    # 3H-1 (AY6): uretilmis kunye — kaynagi yok, butceye sayiliyor
    kunye = panel_kunyesi(ozet, toplam)
    ham = json.dumps(kunye, separators=(",", ":")).encode("utf-8")
    veri = gzip.compress(ham, 9, mtime=0)
    (SAHNE / "kunye.json.gz").write_bytes(veri)
    gz.append("kunye.json")
    toplam += len(veri)
    bayt["kunye.json"] = len(veri)
    print(f"  {'kunye.json (uretilmis)':<30} {len(ham):>9} {len(veri):>10}")
    print("  " + "-" * 52)
    print(f"  {'TOPLAM':<30} {'':>9} {toplam:>10} B   "
          f"(P5 butcesi 600 KB'in %{100.0 * toplam / (600 * 1024):.0f}'i)")

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
        "panel_surum": kunye["surum"],
        "gz": gz,
        "ofset": hex(ofset),
        "bolum_boyut": boyut,
        "icerik_bayt": toplam,
        "bayt": bayt,
        "goruntu_bayt": n,
        "blok": BLOK, "sayfa": SAYFA,
    }, indent=2), encoding="utf-8")

    # Sahne dizini yalnizca mklittlefs icin gerekliydi — birakmak
    # goruntuyle ayrisabilecek ikinci bir kopya olurdu.
    shutil.rmtree(SAHNE, ignore_errors=True)

    print()
    print(f"  goruntu : {GORUNTU.name}  {n} B  (bolum {boyut} B, "
          f"%{100.0 * toplam / boyut:.1f} dolu)")
    print(f"  ofset   : {hex(ofset)}   (partitions.csv'den OKUNDU)")
    print(f"  kunye   : {KUNYE.name}")
    print()
    print("  Karta yazmak icin:  python arayuz-yaz.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
