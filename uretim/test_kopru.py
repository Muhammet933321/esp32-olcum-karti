# -*- coding: utf-8 -*-
"""B22.3 — PC KOPRUSU (kopru/).

    python test_kopru.py

Koprunun tek isi var: karttan gelen satiri BOZMADAN cogaltmak. Bu betigin
en onemli iddiasi da bu — girdi ile cikti BAYT-BAYT esit mi.

Neden bu kadar onemli: arayuzun TEK ayristiricisi (`satirIsle`) firmware,
`sahte-kart.js` ve kopru icin ayni. Kopru satiri "duzeltmeye" kalksa
(bosluk kirpma, sayi bicimleme, JSON'a cevirme) IKINCI BIR TEMSIL
dogar ve bu projenin uc kez yandigi ayrisma sinifi geri gelir
(DEVIR 4.1, 4.15, B17).

Donanim GEREKMIYOR: yukari-akis olarak `KayitKart` kullaniliyor.
⚠ `SeriKart`'in gercek baud/DTR davranisi burada SINANMIYOR — o tezgah
  listesinde.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                       # noqa: E402
import kopru as kopru_mod                                  # noqa: E402
from arsiv import Arsiv                                    # noqa: E402
from tezgah import tezgah                                  # noqa: E402
import gecici                                   # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))


# Kartin gercekten urettigi bicimlerden ornek — protokolun her onekinden
# en az biri var ki role "yalnizca D satirini tasiyor" olmasin.
ORNEK = [
    "D 12.3456 0.891234 10.99881 1234.5678 0.3429355 3600000 133 0",
    "D -613.7000 -11.500000 -7057.55 -1.0000 -0.0002778 3600200 133 1",
    "K 420 1503 0",
    "* enerji sifirlandi",
    "! kazanc kalibrasyonu reddedildi — giris tam olcegin %5'inden kucuk",
    "A menzil=NORMAL oto=1 n_kazanc=1.000000 sont=0.100000",
    "S2 1000 671 0.028787 500 5000 0 1 63.530093",
    "M f=50.000 T=0.020000000 Vpp=24.0000 n=5",
    "E",
]


def istek(url, veri=None, basliklar=None, yontem=None):
    r = urllib.request.Request(url, data=veri, method=yontem)
    for k, v in (basliklar or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=5) as y:
            return y.status, y.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def akis_oku(url, n_olay, jeton=None, zaman_asimi=8.0):
    """SSE akisindan `n_olay` `data:` satiri topla; kimlik olayini ayir."""
    r = urllib.request.Request(url)
    if jeton:
        r.add_header("X-Jeton", jeton)
    veriler, kimlik = [], None
    son = time.monotonic() + zaman_asimi
    with urllib.request.urlopen(r, timeout=zaman_asimi) as y:
        sonraki_kimlik = False
        while len(veriler) < n_olay and time.monotonic() < son:
            ham = y.readline()
            if not ham:
                break
            sat = ham.decode("utf-8", "replace").rstrip("\r\n")
            if sat.startswith("event: kimlik"):
                sonraki_kimlik = True
            elif sat.startswith("data: "):
                govde = sat[6:]
                if sonraki_kimlik:
                    kimlik = json.loads(govde)
                    sonraki_kimlik = False
                else:
                    veriler.append(govde)
    return veriler, kimlik


def main() -> int:
    print("=" * 78)
    print("  B22.3  PC KOPRUSU  (role · arsiv · surucu hakemi)")
    print("=" * 78)

    import tempfile
    gec_dizin = gecici.dizin("kopru_")

    kart = kart_baglanti.KayitKart(
        list(ORNEK),
        yanitlar={"p0": ["* pil testi DURDURULDU, yuk kesildi"],
                  "?": ["A menzil=NORMAL oto=1"]},
    )
    kart.ac()
    k = kopru_mod.Kopru(kart, gec_dizin / "arsiv")
    kopru_mod.Isleyici.kopru = k

    sunucu = kopru_mod.Sunucu(("127.0.0.1", 0), kopru_mod.Isleyici)
    port = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    taban = f"http://127.0.0.1:{port}"
    print(f"     gecici kopru: {taban}\n")

    # ── 1. ROLE BAYT-SEFFAF MI ───────────────────────────────────────
    print("--- 1. Role: girdi ile cikti BAYT-BAYT esit mi ---")
    # ⚠ SIRA ONEMLI: yukari-akis dongusu ONCE baslatilirsa KayitKart'in
    #   butun satirlari abone YOKKEN tuketilir ve akis bos kalir. SSE
    #   yalnizca ABONE OLDUKTAN SONRA yayilanı tasiyor — gercek kartta da
    #   oyle. Once abone ol, sonra dongu.
    sonuc = {}

    def _oku():
        sonuc["veri"] = akis_oku(taban + "/akis", len(ORNEK))

    okuyucu = threading.Thread(target=_oku, daemon=True)
    okuyucu.start()
    bekleme_sonu = time.monotonic() + 5.0
    while not k.aboneler and time.monotonic() < bekleme_sonu:
        time.sleep(0.01)
    ok("SSE abonesi kaydedildi", bool(k.aboneler), f"{len(k.aboneler)} abone")
    threading.Thread(target=k.dongu, daemon=True).start()
    okuyucu.join(timeout=12)
    alinan, kimlik = sonuc.get("veri", ([], None))
    ok("Akis butun satirlari tasidi",
       len(alinan) == len(ORNEK), f"{len(alinan)}/{len(ORNEK)}")
    farkli = [(a, b) for a, b in zip(ORNEK, alinan) if a != b]
    ok("Her satir BIREBIR ayni (bayt-seffaf role)",
       not farkli,
       "ilk fark: " + repr(farkli[0]) if farkli else f"{len(alinan)} satir")
    # Role yalnizca `D`'yi degil HER oneki tasimali — kartin SSE'si
    # B22.4 oncesi yalnizca `D` tasiyordu ve skop/hizli olcum WiFi'de yoktu.
    onekler = {s.split()[0] for s in alinan}
    ok("Her protokol oneki tasindi",
       {"D", "K", "*", "!", "A", "S2", "M", "E"} <= onekler,
       " ".join(sorted(onekler)))

    # ── 2. ARSIV ─────────────────────────────────────────────────────
    print("\n--- 2. Arsiv: eklemeli ham gunluk ---")
    time.sleep(0.3)
    k.arsiv.kapat()
    arsivli = list(k.arsiv.ham_satirlar())
    ok("Arsiv butun satirlari yazdi",
       len(arsivli) >= len(ORNEK), f"{len(arsivli)} satir")
    ok("Arsivdeki satirlar da BIREBIR ayni",
       arsivli[:len(ORNEK)] == ORNEK,
       "zaman damgasi soyulunca ham satir geri geliyor")
    csv_yolu = gec_dizin / "turetilmis.csv"
    n = k.arsiv.csv_uret(csv_yolu)
    ok("CSV gunlukten URETILIYOR (ayri tutulmuyor)", n == 2, f"{n} D satiri")
    ham_csv = csv_yolu.read_bytes()
    ok("CSV Excel-TR uyumlu (BOM + ';' ayrac + ',' ondalik)",
       ham_csv.startswith(b"\xef\xbb\xbf") and b";" in ham_csv
       and b"12,3456" in ham_csv)

    # ── 3. CSRF / KOMUT UCU ──────────────────────────────────────────
    print("\n--- 3. Komut ucu: CSRF yuzeyi ---")
    kod, _ = istek(taban + "/komut?k=p1")
    ok("GET ile komut CALISMIYOR (img/form saldirisi)", kod == 404, f"HTTP {kod}")
    kod, _ = istek(taban + "/komut", b"?", yontem="POST")
    ok("X-Olcum basligi OLMADAN reddediliyor", kod == 400, f"HTTP {kod}")
    kod, _ = istek(taban + "/komut", b"", {"X-Olcum": "1"}, "POST")
    ok("Bos komut reddediliyor", kod == 400, f"HTTP {kod}")

    # ── 4. SURUCU HAKEMI ─────────────────────────────────────────────
    print("\n--- 4. Surucu hakemi: N izleyici, BIR surucu ---")
    ok("Ilk baglanan SURUCU oluyor", bool(kimlik and kimlik["surucu"]),
       json.dumps(kimlik))
    surucu_jetonu = kimlik["jeton"]

    kod, govde = istek(taban + "/komut", b"p1",
                       {"X-Olcum": "1", "X-Jeton": "baskasi"}, "POST")
    ok("Surucu OLMAYAN oturumun komutu REDDEDILIYOR", kod == 403, f"HTTP {kod}")
    ok("Ret sebebi soyleniyor", b"SURUCU" in govde, govde[:48].decode("utf-8", "replace"))

    # 🔴 EMNIYET IDDIASI: `p0` her zaman gecmeli.
    kod, _ = istek(taban + "/komut", b"p0",
                   {"X-Olcum": "1", "X-Jeton": "baskasi"}, "POST")
    ok("🔴 `p0` (DURDUR) jetonsuz/yetkisiz GECIYOR", kod == 204, f"HTTP {kod}")
    time.sleep(0.2)
    ok("`p0` gercekten karta ULASTI", "p0" in kart.yazilanlar,
       " ".join(kart.yazilanlar))

    kod, _ = istek(taban + "/komut", b"p1",
                   {"X-Olcum": "1", "X-Jeton": surucu_jetonu}, "POST")
    ok("Surucunun komutu GECIYOR", kod == 204, f"HTTP {kod}")

    kod, _ = istek(taban + "/devral", b"", {"X-Olcum": "1", "X-Jeton": "yok"},
                   "POST")
    ok("Bilinmeyen oturum DEVRALAMIYOR", kod == 403, f"HTTP {kod}")

    # ── 5. STATIK ARAYUZ ─────────────────────────────────────────────
    print("\n--- 5. Ayni arayuz dosyalari servis ediliyor ---")
    for yol in ("/", "/app.js", "/style.css", "/vendor/vue.global.prod.js"):
        kod, govde = istek(taban + yol)
        ok(f"servis: {yol}", kod == 200 and len(govde) > 0, f"HTTP {kod}")
    kod, govde = istek(taban + "/app.js")
    ok("Kopru arayuz3/'u KOPYALAMIYOR, aynen servis ediyor",
       govde == (KOK / "arayuz3" / "app.js").read_bytes(),
       "iki kopya olsa ayrisirdi")

    # ── 6. DURUM UCU ─────────────────────────────────────────────────
    print("\n--- 6. Durum ucu ---")
    kod, govde = istek(taban + "/durum")
    d = json.loads(govde)
    ok("/durum JSON donduruyor", kod == 200 and "kart" in d, json.dumps(d))

    sunucu.shutdown()
    k.durdur()
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    # Yukari-akis olarak KayitKart kullanildi; gercek seri port hic
    # acilmadi. Asagidakiler yalnizca tezgahta gorulur.
    tezgah("B22a PC koprusu", [
        ("SeriKart gercek baud'da calisiyor mu",
         "`python kopru/kopru.py --port COMx` -> `D` satirlari akmali. "
         "Bozuk karakter gelirse DCB alan duzeni ya da baud yanlis"),
        ("DTR/RTS kart RESET atmiyor mu",
         "Kopru acilinca kart yeniden BASLAMAMALI (acilis banneri "
         "gorunmemeli). Iki hat da bilerek DISABLE; reset atiyorsa devre "
         "otomatik-reset'e bagli ve pil testi kopru acilisinda OLUR"),
        ("Windows 0.0.0.0:80 / stok-takip cakismasi",
         "stok-takip 127.0.0.1:80'i tutuyor. Kopru `http://<LAN-IP>` "
         "yazmali; `127.0.0.1` yazarsa kullaniciyi STOK arayuzune yollar "
         "(bu makinede gercekten oldu, 5.12.36)"),
        ("Telefon koprude uctan uca",
         "Telefondan http://<PC-IP> -> tam arayuz, canli olcum. Iki "
         "tarayici ayni anda izlerken YALNIZCA biri surucu olmali"),
        ("p0 (DURDUR) izleyiciden de geciyor mu",
         "Surucu OLMAYAN sekmeden pil testini durdur. Gecmeli — bu bir "
         "kolaylik degil EMNIYET karari"),
    ])
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
