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

W6 — ETag KUNYESI: goruntuye URETILMIS bir `etag.txt` da giriyor (gzip'siz;
  kart acilista bir kez okuyup bellege aliyor, `web_etag.h`). Satir:
  `<istek yolu> <16 onaltilik>` — ozet GORUNTUDEKI baytlarin (gzip'liyse gzip'li
  hali; mtime=0 oldugu icin ayni kaynak ayni ozet) sha256'sinin ilk 16'si. Kart
  bununla ETag verir ve `If-None-Match`e 304 der; ikinci acilis govde indirmez.
  Kunyede (`_fs.json`) `etag` olarak da duruyor; `sim3_web.py` 6q iki yonlu sinar.

4F (PC17) — PWA KABUGU: manifestteki her ikon goruntuye girer (`manifest_ikonlari`,
  kartin manifesti 404'lu ikon gostermesin). `PC_KABUGU` (sw.js, cevrimdisi.html)
  GIRMEZ: kart guvenli baglam degil, service worker kullanamaz. Uretec her kosuda
  sw.js'in SURUM satirini `kabuk_surumu()` ile yazar (panel degisince service
  worker yeniden kurulsun); `sim3_web.py` 6j satirin bayat olmadigini sinar.
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


# 4F (PC17): YALNIZ PC KABUGUNUN dosyalari — karta GIRMEZ. Kart guvenli baglam
# degil (`http://olcum.local`), tarayici orada service worker'a izin vermiyor;
# sw.js ve cevrimdisi.html kartta olu bayt olurdu. `sim3_web.py` 6j bunlarin
# goruntude OLMADIGINI ve sw.js'in SURUM satirinin guncel oldugunu sinar.
SW = "sw.js"
PC_KABUGU = (SW, "cevrimdisi.html")
SW_SURUM = re.compile(r"^const SURUM = '([0-9a-f]{12})';$", re.M)


def manifest_ikonlari() -> list[str]:
    """`manifest.json`'daki ikon dosyalari (4F). Kartin manifesti de bunlari
    gosteriyor; goruntude olmasalar kart 404 verir ve Android "Ana Ekrana Ekle"
    kisayolu ikonsuz kalir. Elle liste degil: ikon-uret.py manifestle birlikte uretiyor."""
    try:
        man = json.loads((ARAYUZ / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [i["src"] for i in man.get("icons", []) if isinstance(i, dict) and i.get("src")]


def goruntu_listesi() -> list[str]:
    """Goruntuye giren HER dosyanin goruntudeki yolu (`/` sonrasi)."""
    ekran = sorted(EKRAN_ONEK + p.name for p in (ARAYUZ / "ekran").glob("*.js"))
    ortak = sorted(ORTAK_ONEK + p.name for p in ORTAK.glob("*.js"))
    ikon = [a for a in manifest_ikonlari() if a not in VARLIKLAR]
    return list(VARLIKLAR) + ikon + ekran + ortak


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


# W6: kartin acilista okudugu ETag kunyesi (goruntunun kokunde, gzip'SIZ).
ETAG_KUNYE = "etag.txt"


def etag_ozet(veri: bytes) -> str:
    """Goruntudeki baytlarin ETag ozeti: sha256'nin ilk 16 onaltiligi (web_etag.h WEB_ETAG_HEX)."""
    return hashlib.sha256(veri).hexdigest()[:16]


def etag_kunyesi(etag: dict) -> str:
    """`etag.txt` metni: istek yolu sirasinda `/<ad> <ozet>` + LF (web_etag.h `etag_bul`)."""
    return "".join(f"/{ad} {etag[ad]}\n" for ad in sorted(etag))


def kabuk_surumu() -> str:
    """4F: PC kabugunun (service worker onbellegi) surumu — panel surumuyle AYNI
    kural, kapsami panelin kaynaklari + PC kabugunun dosyalari (sw.js'in kendisi
    haric: kendi baytlarini kendisi belirleyemez). cevrimdisi.html degisince de
    service worker yeniden kurulur."""
    ozet = kaynak_ozeti()
    for ad in PC_KABUGU:
        if ad != SW:
            ozet[ad] = hashlib.sha256((ARAYUZ / ad).read_bytes()).hexdigest()
    return panel_surumu(ozet)


def sw_surum_yaz() -> str:
    """sw.js'in `const SURUM = '...';` satirini kabuk surumuyle gunceller."""
    yol = ARAYUZ / SW
    metin = yol.read_text(encoding="utf-8")
    if not SW_SURUM.search(metin):
        raise SystemExit("sw.js'te `const SURUM = '<12 onaltilik>';` satiri yok")
    surum = kabuk_surumu()
    yeni = SW_SURUM.sub(f"const SURUM = '{surum}';", metin, count=1)
    if yeni != metin:
        yol.write_text(yeni, encoding="utf-8", newline="\n")
    return surum


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
    # 4F: PC kabugu karta girmiyor ama surumu panelle birlikte ilerlemeli
    print(f"  sw.js SURUM = {sw_surum_yaz()}  (PC kabugu, karta girmez)")

    shutil.rmtree(SAHNE, ignore_errors=True)
    SAHNE.mkdir(parents=True)
    toplam = 0
    gz = []                  # goruntude `.gz` olarak duranlar (kunyede)
    # 3D: dosya basina goruntudeki bayt — B7 acilis kumesinin (index + varliklar +
    # app.js'in statik ice aktarma agaci) butcesini bundan topluyor.
    bayt = {}
    etag = {}                # W6: istek yolu -> goruntudeki baytlarin ozeti
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
        etag[ad] = etag_ozet(veri)
        print(f"  {ad:<30} {len(ham):>9} {len(veri):>10}")
    # 3H-1 (AY6): uretilmis kunye — kaynagi yok, butceye sayiliyor
    kunye = panel_kunyesi(ozet, toplam)
    ham = json.dumps(kunye, separators=(",", ":")).encode("utf-8")
    veri = gzip.compress(ham, 9, mtime=0)
    (SAHNE / "kunye.json.gz").write_bytes(veri)
    gz.append("kunye.json")
    toplam += len(veri)
    bayt["kunye.json"] = len(veri)
    etag["kunye.json"] = etag_ozet(veri)
    print(f"  {'kunye.json (uretilmis)':<30} {len(ham):>9} {len(veri):>10}")
    # W6: ETag kunyesi — gzip'siz (kart dogrudan okuyor), kendisinin ETag'i yok
    veri = etag_kunyesi(etag).encode("ascii")
    (SAHNE / ETAG_KUNYE).write_bytes(veri)
    toplam += len(veri)
    bayt[ETAG_KUNYE] = len(veri)
    print(f"  {ETAG_KUNYE + ' (uretilmis)':<30} {len(veri):>9} {len(veri):>10}")
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
        "etag": etag,
        "goruntu_bayt": n,
        "blok": BLOK, "sayfa": SAYFA,
    }, indent=2), encoding="utf-8", newline="\n")   # LF: depoda CRLF/LF gurultusu olmasin

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
