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


def istek(url, veri=None, basliklar=None, yontem=None, zaman_asimi=5):
    kod, govde, _ = istek_bas(url, veri, basliklar, yontem, zaman_asimi)
    return kod, govde


def istek_bas(url, veri=None, basliklar=None, yontem=None, zaman_asimi=5):
    """`istek` + YANIT BASLIKLARI. Skop ucu yakalamanin arsiv kimligini
    (`X-Skop-Gun`/`X-Skop-Ms`) baslikta donduruyor; kimligin govdeyle
    tutarli oldugunu sinamak icin basliklara erisim gerekiyor."""
    r = urllib.request.Request(url, data=veri, method=yontem)
    for k, v in (basliklar or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=zaman_asimi) as y:
            return y.status, y.read(), dict(y.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


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

    # ── 7. SKOP: KOPRU KIPINDE YAKALAMA VE GERIYE DONUK KAYIT ────────
    #
    # 🔴 BU BOLUM BIR CANLI KUSURDAN DOGDU (B35). Arayuz `TasiyiciAkis`
    #    icin `skop: 'ikili'` ilan edip `/skop.bin` cekiyor; sayfa
    #    kopruden geldiginde o istek kopruye gidiyordu ve kopruda boyle
    #    bir uc YOKTU — `SimpleHTTPRequestHandler` `arayuz3/`de dosya
    #    arayip 404 donuyordu. Yani osiloskop, kullanicinin "sekilleri
    #    gormek + kayit almak" istedigi TAM O KIPTE olu bir dugmeydi.
    #    Zincir 18/18 yesilken. (Bu projede kacinci oldugunu sayiyoruz.)
    print("\n--- 7. Skop: kopru kipinde yakalama + arsiv ---")
    from arsiv import SkopCozucu, skop_ikili           # noqa: E402
    import struct

    # Kartin `t` yanitinin GERCEK bicimi: S2 basligi, M olcumu, 16'sar
    # ham kod, `E`. Ucgen dalga — cizim dogruysa gozle de ayirt edilir.
    ORNEKLER = [(i * 37) % 4096 for i in range(64)]
    SKOP_YANIT = (
        ["S2 64 10000 0.028787 12 5000 0 1 63.530093",
         "M f=156.250 T=0.006400000 Vpp=24.0000 n=10"]
        + [" ".join(str(x) for x in ORNEKLER[i:i + 16])
           for i in range(0, len(ORNEKLER), 16)]
        + ["E"])
    kart.yanitlar["t"] = SKOP_YANIT

    kod, govde, bas = istek_bas(taban + "/skop.bin", zaman_asimi=25)
    canli_govde = govde
    ok("[!] KOPRUDE /skop.bin ucu VAR (404 degil)", kod == 200, f"HTTP {kod}")
    ok("Govde kartin imzasini tasiyor (tek ikili cozucu)",
       govde[:3] == b"S3B", repr(govde[:4]))
    if kod == 200 and len(govde) >= 32:
        adet = struct.unpack_from("<H", govde, 4)[0]
        hz = struct.unpack_from("<I", govde, 8)[0]
        adim = struct.unpack_from("<f", govde, 12)[0]
        ofset = struct.unpack_from("<f", govde, 16)[0]
        tdiv = struct.unpack_from("<I", govde, 20)[0]
        tidx = struct.unpack_from("<H", govde, 24)[0]
        gelen = list(struct.unpack_from(f"<{adet}H", govde, 32))
        ok("Baslik alanlari `S2` satiriyla AYNI",
           (adet, hz, tdiv, tidx) == (64, 10000, 5000, 12)
           and abs(adim - 0.028787) < 1e-6 and abs(ofset - 63.530093) < 1e-4,
           f"adet={adet} hz={hz} tdiv={tdiv} tetik={tidx} "
           f"adim={adim:.6f} ofset={ofset:.4f}")
        ok("[!] Ornekler BIREBIR geri geliyor (ham kod, donusum YOK)",
           gelen == ORNEKLER,
           f"{len(gelen)}/{len(ORNEKLER)} ornek")
        ok("Govde uzunlugu 32 + 2*adet", len(govde) == 32 + 2 * adet,
           f"{len(govde)} B")
    else:
        ok("Baslik alanlari `S2` satiriyla AYNI", False, "govde yok")
        ok("[!] Ornekler BIREBIR geri geliyor (ham kod, donusum YOK)", False,
           "govde yok")
        ok("Govde uzunlugu 32 + 2*adet", False, "govde yok")

    ok("Kopru karta `t` yolladi (`tB` DEGIL — `tB` seri porta hic dokmez)",
       "t" in kart.yazilanlar and "tB" not in kart.yazilanlar,
       " ".join(kart.yazilanlar))

    # 🔴 GERIYE DONUK KAYIT — asil istenen sey. Dokum `Serial`den gectigi
    #    icin ARSIVE de dustu; ayrica bir dosyaya yazilmiyor.
    time.sleep(0.3)
    k.arsiv.flush()
    bloklar = list(k.arsiv.skop_bloklari())
    ok("[!] Yakalama ARSIVE dustu (ayri dosya YOK, gunlukten turetiliyor)",
       len(bloklar) >= 1, f"{len(bloklar)} blok")
    if bloklar:
        b = bloklar[-1]
        ok("Arsivden okunan ornekler de BIREBIR", b["ornek"] == ORNEKLER,
           f"{len(b['ornek'])} ornek, tam={b['tam']}")
        # 🔴 Canli yanitin bildirdigi kimlik ile arsivdeki kayit AYNI
        #    olmali; ayrisirsa "az once cektigim yakalama listede yok"
        #    olur ve kullanici kaydin tutuldugundan suphe eder.
        ok("[!] Canli yanitin kimligi arsivdeki kayitla AYNI",
           bas.get("X-Skop-Ms") == str(b["ms"])
           and bas.get("X-Skop-Gun") == b["gun"],
           f"baslik={bas.get('X-Skop-Gun')}/{bas.get('X-Skop-Ms')} · "
           f"arsiv={b['gun']}/{b['ms']}")
    else:
        ok("Arsivden okunan ornekler de BIREBIR", False, "blok yok")
        ok("[!] Canli yanitin kimligi arsivdeki kayitla AYNI", False, "blok yok")

    kod, govde = istek(taban + "/skop/liste")
    liste = json.loads(govde) if kod == 200 else {}
    ok("/skop/liste kayitlari sayiyor",
       kod == 200 and len(liste.get("kayitlar", [])) >= 1,
       f"HTTP {kod} · {len(liste.get('kayitlar', []))} kayit")
    ok("Liste ORNEK DIZISI tasimiyor (4000 ornek = ~20 KB/satir)",
       all("ornek" not in kyt for kyt in liste.get("kayitlar", [])),
       "hafif ozet")

    if liste.get("kayitlar"):
        kyt = liste["kayitlar"][0]
        kod, govde2 = istek(
            taban + f"/skop/al?gun={kyt['gun']}&ms={kyt['ms']}")
        ok("[!] /skop/al ESKI yakalamayi geri veriyor",
           kod == 200 and govde2[:3] == b"S3B", f"HTTP {kod}")
        # Ayni yakalama iki yoldan (canli / arsiv) BAYT-BAYT ayni
        # gelmeli — ayrisirsa arayuz eski kaydi baska cizerdi.
        ok("[!] Arsivden gelen govde CANLI govdeyle BAYT-BAYT ayni",
           govde2 == canli_govde, f"{len(govde2)} B / {len(canli_govde)} B")
    else:
        ok("[!] /skop/al ESKI yakalamayi geri veriyor", False, "liste bos")
        ok("[!] Arsivden gelen govde CANLI govdeyle BAYT-BAYT ayni", False,
           "liste bos")
    kod, _ = istek(taban + "/skop/al?gun=2000-01-01&ms=0")
    ok("Olmayan kayit 404", kod == 404, f"HTTP {kod}")
    kod, _ = istek(taban + "/skop/al")
    ok("Eksik parametre 400", kod == 400, f"HTTP {kod}")

    # 🔴 ARAYUZUN GERCEK AKISI: once `/komut` ile `tB`, 400 ms sonra
    #    `/skop.bin`. Kopru bunu TEK yakalamaya indirmeli.
    #    Indirmeseydi kart iki kez yakalardi ve arayuze donen dalga
    #    kullanicinin tetikledigi dalga OLMAZDI — sessiz, ama yanlis.
    kart.yanitlar["t"] = SKOP_YANIT
    onceki_t = kart.yazilanlar.count("t")
    kod, _ = istek(taban + "/komut", b"tB",
                   {"X-Olcum": "1", "X-Jeton": surucu_jetonu}, "POST")
    ok("Arayuzun `tB` komutu kopruden geciyor", kod == 204, f"HTTP {kod}")
    ok("[!] Kopru `tB`yi `t`ye CEVIRIYOR (yoksa seri porta hic dokulmez)",
       kart.yazilanlar[-1] == "t", f"karta giden: {kart.yazilanlar[-1]!r}")
    time.sleep(0.4)
    kod, govde = istek(taban + "/skop.bin", zaman_asimi=25)
    ok("`tB` sonrasi /skop.bin yakalamayi donduruyor",
       kod == 200 and govde[:3] == b"S3B", f"HTTP {kod}")
    ok("[!] Kart IKI KEZ yakalamiyor (tek `t` gitti)",
       kart.yazilanlar.count("t") == onceki_t + 1,
       f"`t` sayisi {onceki_t} -> {kart.yazilanlar.count('t')}")
    # Ayar komutlari yakalama DEGIL — `tb0` bosuna beklememeli.
    onceki_t = kart.yazilanlar.count("t")
    kart.yanitlar["tb0"] = ["T tdiv=0/11 (5 us/bolme) hz=200000 adet=1000"]
    istek(taban + "/komut", b"tb0",
          {"X-Olcum": "1", "X-Jeton": surucu_jetonu}, "POST")
    time.sleep(0.2)
    ok("Ayar komutu (`tb0`) yakalama olarak SAYILMIYOR",
       kart.yazilanlar[-1] == "tb0"
       and kart.yazilanlar.count("t") == onceki_t,
       f"karta giden: {kart.yazilanlar[-1]!r}")

    # Tetikleyemeyen kart: 20 s beklemek yerine HEMEN sebep donmeli.
    kart.yanitlar["t"] = ["! tetiklenemedi"]
    t0 = time.monotonic()
    kod, govde = istek(taban + "/skop.bin")
    gecen = time.monotonic() - t0
    ok("[!] Tetiklenemeyince HEMEN 503 (20 s beklemiyor)",
       kod == 503 and gecen < 5.0, f"HTTP {kod}, {gecen:.2f} s")
    ok("503 sebebi soyleniyor", b"tetikle" in govde,
       govde[:60].decode("utf-8", "replace"))

    # Kirpik blok CIZILMIYOR: eksik dalga "olculmus" gibi gorunmemeli.
    kart.yanitlar["t"] = ["S2 64 10000 0.028787 12 5000 0 1 0.0",
                          "1 2 3 4 5 6 7 8", "E"]
    kod, govde = istek(taban + "/skop.bin")
    ok("[!] KIRPIK blok reddediliyor (eksik dalga cizilmez)",
       kod == 503 and b"kirpik" in govde,
       f"HTTP {kod} · " + govde[:60].decode("utf-8", "replace"))

    # Cozucu birim sinamasi — arada `D` satiri gecerse blok BOZULMAMALI.
    c = SkopCozucu()
    karisik = ["S2 4 1000 0.01 0 100 0 1 0.0", "M f=1",
               "10 20", "D 1 2 3 4 5 6 7 8 9", "30 40", "E"]
    son = None
    for s in karisik:
        son = c.besle(s, 7) or son
    ok("Cozucu arada gelen `D` satirini ATLIYOR ama SAYIYOR",
       son is not None and son["ornek"] == [10, 20, 30, 40]
       and son["atlanan"] == 1,
       f"ornek={son['ornek'] if son else None} "
       f"atlanan={son['atlanan'] if son else None}")

    # 🔴 BILDIRILEN ADET TAVAN. Bozuk bir `S2` uzun bir sayi akisina denk
    #    gelirse (ornegin baska bir dokumun ortasina dusulurse) ornek
    #    listesi sinirsiz buyurdu — kopru surekli calisan bir surec,
    #    boyle bir buyume belleği yer.
    c2 = SkopCozucu()
    son2 = None
    for s in (["S2 4 1000 0.01 0 100 0 1 0.0"]
              + [" ".join(str(i) for i in range(16))] * 3 + ["E"]):
        son2 = c2.besle(s, 0) or son2
    ok("[!] Cozucu BILDIRILEN ADEDI tavan aliyor (sinirsiz buyume yok)",
       son2 is not None and len(son2["ornek"]) == 4,
       f"{len(son2['ornek']) if son2 else None} ornek (48 geldi, 4 bildirildi)")
    ok("Tasan ornekler SESSIZCE atilmiyor (sayiliyor)",
       son2 is not None and son2["atlanan"] == 44,
       f"atlanan={son2['atlanan'] if son2 else None}")

    # ── 8. ARSIV HATASI ROLEYI OLDUREMEZ ─────────────────────────────
    #
    # 🔴 BU BOLUM DE BIR CANLI KUSURDAN DOGDU. `Arsiv.kapat()` `_gun`u
    #    sifirlamiyordu; kapatilmis arsive gelen ILK satir `yaz()` icinde
    #    AttributeError atiyor, bu da yukari-akis IPLIGINI OLDURUYORDU.
    #    Kopru ayakta gorunmeye devam ediyor, HTTP cevap veriyor, ama ne
    #    arsiv ne SSE calisiyor ve hicbir yerde yazmiyordu.
    #    ⚠ Bu testin KENDISI de o kusurdan etkilenmisti: 2. bolumdeki
    #      `k.arsiv.kapat()` cagrisindan SONRAKI butun bolumler, yukari-
    #      akis ipligi OLMUS bir kopruye karsi kosuyordu ve bunu hicbir
    #      iddia yakalamiyordu (kanit: iplik yasayinca SSE gercekten
    #      yayin yapmaya basladi ve kapanis davranisi degisti).
    print("\n--- 8. Arsiv hatasi roleyi olduremiyor ---")
    k.arsiv.kapat()
    kart.yanitlar["z"] = ["* kapatilmis arsivden sonra gelen satir"]
    onceki = k.satir_adedi
    kart.yaz("z")
    time.sleep(0.4)
    ok("[!] Kapatilmis arsivden SONRA da satir isleniyor",
       k.satir_adedi > onceki, f"{onceki} -> {k.satir_adedi}")
    k.arsiv.flush()          # periyodik flush 2 s'de bir; okumadan once indir
    ok("Kapatilmis arsiv kendini yeniden aciyor (satir KAYBOLMUYOR)",
       any("kapatilmis arsivden sonra" in s
           for s in k.arsiv.ham_satirlar()),
       "gunluk `a` kipinde yeniden aciliyor")

    # Arsiv gercekten yazamaz hale gelirse: role SURUYOR, sebep BIR KEZ
    # akisa dusuyor. (Diski dolduramayiz; `yaz`i bilerek patlatiyoruz.)
    class _BozukArsiv:
        satir_adedi = 0
        t0 = 0.0

        def yaz(self, satir):
            raise OSError("disk dolu (sinama)")

        def kapat(self):
            pass

    gercek_arsiv = k.arsiv
    k.arsiv = _BozukArsiv()
    k.arsiv_hatasi = None
    onceki = k.satir_adedi
    kart.yanitlar["z2"] = ["* arsiv bozukken gelen satir"]
    kart.yaz("z2")
    time.sleep(0.4)
    ok("[!] Arsiv YAZAMAZ hale gelince role DURMUYOR",
       k.satir_adedi > onceki, f"{onceki} -> {k.satir_adedi}")
    ok("Arsiv hatasi SESSIZ kalmiyor (sebep akisa dusuyor)",
       k.arsiv_hatasi is not None and "disk dolu" in k.arsiv_hatasi,
       str(k.arsiv_hatasi))
    k.arsiv = gercek_arsiv

    # ⚠ KAPANIS SIRASI: once yukari-akis, sonra sunucu. Tersi olunca
    #   kapanmakta olan sunucuya SSE yazmasi denk gelip stderr'e teardown
    #   izi dusuyordu — cikis kodunu bozmuyor ama GERCEK bir izi
    #   maskeleyebilir, o yuzden gurultu birakilmiyor.
    k.calisiyor = False
    time.sleep(0.25)
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
        ("[!] SKOP ARSIVI gercek kartta — `python tezgah_skop_arsiv.py`",
         "Bu betikteki skop iddialari `KayitKart` ile kosuyor, yani "
         "kartin `t` yanitini BEN yaziyorum: protokol sinaniyor, KART "
         "sinanmiyor. Gercek kartta 2026-09-12'de kosuldu ve 16/16 "
         "gecti (1000 ornek 1.07 s, arsive dustu, geri okunan kayit "
         "bayt-bayt ayni). Firmware ya da kopru degisince TEKRAR kosun"),
        ("[!] TARAYICIDA — `python tarayici_skop_arsiv.py --goruntu`",
         "Bolum 16'daki iddialar KAYNAK METNINDE arama yapiyor; sayfanin "
         "acildigini kanitlamiyor (B22.0'da zincir 15/15 yesilken arayuz "
         "tarayicida HIC acilmiyordu). Bu betik gercek tarayici + gercek "
         "Vue + sahte kopru ile 14/14 kosuyor ve iki ekran goruntusu "
         "birakiyor. Arayuz ya da kopru ucu degisince TEKRAR kosun"),
        ("Tarayicida: kayit listesi + arsiv seridi (elle)",
         "Kopruye bagli tarayicida Osiloskop gorunumu -> `Yakala` -> "
         "kayit **Kayitlar** bolumunde belirmeli. Bir kaydi acinca tuvalin "
         "ustunde ARSIV seridi cikmali ve `Canliya don` calismali. "
         "Karta DOGRUDAN bagliyken bu bolum HIC gorunmemeli (olu dugme)"),
    ])
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
