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

import http.server
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


def _tur(basliklar: dict) -> str:
    """Content-Type (http.server `Content-type` yaziyor — buyuk/kucuk harf serbest)."""
    return next((v for k, v in basliklar.items() if k.lower() == "content-type"), "")


def ortak_sina(taban: str, kim: str) -> None:
    """3A (P4): panel `import ... from '/ortak/x.js'` diyor. Kart LittleFS'ten,
    kopru ve `arayuz3/sunucu.py` `ortak/src/`ten AYNI dosyayi vermeli.

    🔴 `app.js` artik ES MODULU: tarayici modul betigini YALNIZCA JavaScript
       MIME turuyle calistirir. `mimetypes` Windows'ta kayit defterinden
       `.js` -> `text/plain` okuyabiliyor — o makinede panel HIC acilmazdi.
    ⚠ `/ortak/` bir DUSME degil (K4): arayuz3'te olmayan bir dosya baska
      dizinden VERILMEMELI. `/disari.js` ortak/src'te var, arayuz3'te yok -> 404.
    """
    ortak = KOK / "ortak" / "src"
    kod, govde, _ = istek_bas(taban + "/ortak/ozet.js")
    ok(f"{kim}: /ortak/ozet.js = ortak/src/ozet.js (bayt-bayt, kopya yok)",
       kod == 200 and govde == (ortak / "ozet.js").read_bytes(), f"HTTP {kod}")
    turler = {}
    for yol in ("/app.js", "/ekran/tema.js", "/ortak/ozet.js"):
        k2, _, b2 = istek_bas(taban + yol)
        turler[yol] = (k2, _tur(b2))
    ok(f"{kim}: [!] .js JavaScript MIME turuyle (ES modulu bunu ister)",
       all(k == 200 and t.split(";")[0].strip() in ("text/javascript", "application/javascript")
           for k, t in turler.values()),
       " ".join(f"{y}={k}:{t}" for y, (k, t) in turler.items()))
    red = {yol: istek(taban + yol)[0]
           for yol in ("/ortak/yok.js", "/ortak/../../arayuz3/app.js", "/ortak/ozet.txt",
                       "/disari.js")}
    ok(f"{kim}: /ortak/ DUSME DEGIL — yalniz ortak/src/<ad>.js; arayuz3'te olmayan 404",
       all(k == 404 for k in red.values()),
       " ".join(f"{y}={k}" for y, k in red.items()))


def gelistirme_sunucusu_sina() -> None:
    """`arayuz3/sunucu.py`nin isleyicisi gecici portta — ayni `/ortak/` kurali."""
    import importlib.util
    import socketserver
    oz = importlib.util.spec_from_file_location("arayuz_sunucu", KOK / "arayuz3" / "sunucu.py")
    gs = importlib.util.module_from_spec(oz)
    oz.loader.exec_module(gs)

    class Sessiz(gs.Sunucu):
        def log_message(self, *a):
            pass

    class Tcp(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = False

    s = Tcp(("127.0.0.1", 0), Sessiz)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        ortak_sina(f"http://127.0.0.1:{s.server_address[1]}", "sunucu.py")
    finally:
        s.shutdown()
        s.server_close()


def kimlik_oku(url, basliklar=None, zaman_asimi=5.0):
    """`/akis`in ilk `kimlik` olayini oku ve baglantiyi kapat."""
    r = urllib.request.Request(url)
    for a, d in (basliklar or {}).items():
        r.add_header(a, d)
    son = time.monotonic() + zaman_asimi
    with urllib.request.urlopen(r, timeout=zaman_asimi) as y:
        sonraki = False
        while time.monotonic() < son:
            sat = y.readline().decode("utf-8", "replace").rstrip("\r\n")
            if sat.startswith("event: kimlik"):
                sonraki = True
            elif sat.startswith("data: ") and sonraki:
                return json.loads(sat[6:])
    return None


# 4A (PC2): "yerel agdaki telefon" taklidi. YALNIZ istemci adresi degisiyor —
# karar mantigi (hangi uc, hangi komut) gercek `Isleyici`de kaliyor. Adres
# RFC 5737 belgeleme blogundan: kullanicinin agina ait hicbir adres depoda yok.
LAN_ISTEMCI = "198.51.100.23"


class _LanIsleyici(kopru_mod.Isleyici):
    def _istemci_ip(self) -> str:
        return LAN_ISTEMCI


def _kos(kopru, taban_sinif=kopru_mod.Isleyici):
    """Gecici sunucu; isleyici OZEL alt sinif (ana testin `Isleyici.kopru`su ezilmesin)."""
    isleyici = type("TestIsleyici", (taban_sinif,), {"kopru": kopru})
    s = kopru_mod.Sunucu(("127.0.0.1", 0), isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def pc_4a_sina(gec_dizin: Path, taban: str) -> None:
    """4A — PC uygulamasinin ana sureci: koken, yerel ag, port, tek kopya.

    Kararlar tasarim/2026-10-03-alt-proje-4-pc.md PC1-PC4 + "4A uygulama
    kararlari". 🔴 Acik kapatiliyor: kopru eskiden 0.0.0.0'a baglaniyordu ve
    yerel agdaki ILK istemci surucu olup USB'den `Ns`/`GF!`/`p1`/`R!`
    gonderebiliyordu — kart USB'de kimlik sormadigi icin 1D tamamen atlaniyordu.
    """
    import os
    import socket
    import pc as pc_mod                                     # noqa: E402
    import pc_ayar                                          # noqa: E402

    print("\n--- 4A. PC1 koken + PC2 yerel ag salt okuma ---")
    ok("PC1: koken http://olcum.localhost:8770 (tek yer: pc_ayar)",
       pc_ayar.PORT == 8770 and pc_ayar.adres() == "http://olcum.localhost:8770",
       pc_ayar.adres())
    k3 = kopru_mod.Kopru(kart_baglanti.KayitKart([], yanitlar={"p0": ["* durdu"]}),
                         gec_dizin / "arsiv_4a")
    s_yerel = kopru_mod.sunucu_kur(k3, port=0)
    ok("[!] PC2: kopru VARSAYILAN olarak yalniz 127.0.0.1'e baglaniyor (0.0.0.0 degil)",
       s_yerel.server_address[0] == "127.0.0.1", str(s_yerel.server_address))
    s_yerel.server_close()
    s_lan = kopru_mod.sunucu_kur(k3, lan=True, port=0)
    ok("PC2: --lan butun arayuzlere baglaniyor",
       s_lan.server_address[0] == "0.0.0.0", str(s_lan.server_address))
    s_lan.server_close()
    ok("Windows: allow_reuse_address KAPALI (baska surecin portunu ele gecirmez)",
       sys.platform != "win32" or kopru_mod.Sunucu.allow_reuse_address is False,
       str(kopru_mod.Sunucu.allow_reuse_address))
    # 🔴 Olculdu (2026-10-03): Windows'ta 127.0.0.1:P baskasindayken 0.0.0.0:P
    #    baglamasi SO_EXCLUSIVEADDRUSE OLMADAN basarili oluyor; dongu trafigi
    #    yine oteki surece gider ve kopru "acildi" der.
    tutan = socket.socket()
    tutan.bind(("127.0.0.1", 0))
    tutan.listen()
    tutulan = tutan.getsockname()[1]
    try:
        s2 = kopru_mod.sunucu_kur(k3, lan=True, port=tutulan)
        s2.server_close()
        cakisti = True
    except OSError:
        cakisti = False
    tutan.close()
    ok("[!] --lan: 127.0.0.1:P baskasindayken 0.0.0.0:P baglanamiyor (SO_EXCLUSIVEADDRUSE)",
       not cakisti, "ikinci baglama reddedildi" if not cakisti else "IKI SUNUCU AYNI PORTTA")

    dongu = {ip: kopru_mod.dongu_mu(ip) for ip in
             ("127.0.0.1", "127.8.9.10", "::1", "::ffff:127.0.0.1",
              LAN_ISTEMCI, "192.168.4.2", "::ffff:192.168.4.2", "fe80::1", "", "bozuk")}
    ok("dongu_mu: yalniz 127/8, ::1 ve IPv4-esli 127 dongu sayilir; bozuk/bos adres DEGIL",
       [ip for ip, d in dongu.items() if d] == ["127.0.0.1", "127.8.9.10", "::1", "::ffff:127.0.0.1"],
       str(dongu))

    # ── yerel ag istemcisi: GORUR, yalniz p0 gonderir ─────────────────
    s_l = _kos(k3, _LanIsleyici)
    lt = f"http://127.0.0.1:{s_l.server_address[1]}"
    gorur = {y: istek(lt + y)[0] for y in ("/", "/app.js", "/durum", "/skop/liste",
                                             "/ortak/ozet.js")}
    ok("PC2: yerel ag istemcisi GOREBILIYOR (statik dosyalar + okuma uclari 200)",
       all(c == 200 for c in gorur.values()), str(gorur))
    kim = kimlik_oku(lt + "/akis")
    ok("[!] PC2: yerel ag istemcisi /akis aliyor ama ASLA surucu olmuyor (surucu yokken bile)",
       kim is not None and kim.get("surucu") is False and k3.surucu is None,
       f"{kim} · k.surucu={k3.surucu}")
    once = len(k3.kart.yazilanlar)
    kod, _ = istek(lt + "/komut", b"p0", {"X-Olcum": "1"}, "POST")
    ok("[!] PC2/O7: yerel ag istemcisinin `p0`u (DURDUR) jetonsuz GECIYOR",
       kod == 204 and k3.kart.yazilanlar[once:] == ["p0"], f"HTTP {kod} · {k3.kart.yazilanlar[once:]}")
    redler = {}
    for komut in ("Nsyeni-parola", "GF!", "p1", "R!", "?", "Na ev", "t", "Ep telefon", "Qp x",
                  "p0\nNs", "p00"):
        kod, govde = istek(lt + "/komut", komut.encode(), {"X-Olcum": "1", "X-Jeton": kim["jeton"]
                                                            if kim else "x"}, "POST")
        redler[komut] = (kod, govde.decode("utf-8", "replace"))
    ok("[!] PC2: yerel ag istemcisinin p0 DISINDAKI her komutu 403 (Ns, GF!, p1, R!, ?, Na, t, E, Q, gomulu p0)",
       all(k_ == 403 for k_, _ in redler.values()),
       " ".join(f"{c!r}={k_}" for c, (k_, _) in redler.items()))
    ok("PC2: ret sebebi Turkce ve acik (salt okuma + p0 + bu bilgisayardan adres)",
       all("salt okuma" in g and "p0" in g for c, (_, g) in redler.items()
           if c in ("Nsyeni-parola", "GF!", "p1", "R!")),
       redler["GF!"][1][:90])
    ok("PC2: reddedilen hicbir komut karta ULASMADI",
       k3.kart.yazilanlar[once:] == ["p0"], str(k3.kart.yazilanlar[once:]))
    kod, _ = istek(lt + "/devral", b"", {"X-Olcum": "1", "X-Jeton": kim["jeton"] if kim else "x"},
                   "POST")
    ok("PC2: yerel ag istemcisi surucu DEVRALAMIYOR", kod == 403 and k3.surucu is None, f"HTTP {kod}")
    once_t = len(k3.kart.yazilanlar)
    kod, _ = istek(lt + "/skop.bin")
    ok("[!] PC2: yerel ag istemcisi /skop.bin ile karta YAKALAMA YAPTIRAMIYOR (`t` gitmez)",
       kod == 403 and k3.kart.yazilanlar[once_t:] == [], f"HTTP {kod} · {k3.kart.yazilanlar[once_t:]}")
    s_l.shutdown()
    s_l.server_close()

    # ── dongu istemcisi: bugunku davranis aynen ──────────────────────
    s_d = _kos(k3)
    dt = f"http://127.0.0.1:{s_d.server_address[1]}"
    kim_d = kimlik_oku(dt + "/akis")
    once = len(k3.kart.yazilanlar)
    kod1, _ = istek(dt + "/komut", b"p1", {"X-Olcum": "1", "X-Jeton": kim_d["jeton"] if kim_d else ""},
                    "POST")
    kod2, _ = istek(dt + "/komut", b"p1", {"X-Olcum": "1", "X-Jeton": "baskasi"}, "POST")
    kod3, _ = istek(dt + "/komut", b"p0", {"X-Olcum": "1", "X-Jeton": "baskasi"}, "POST")
    kod4, _ = istek(dt + "/komut", b"Ep x", {"X-Olcum": "1", "X-Jeton": kim_d["jeton"] if kim_d else ""},
                    "POST")
    ok("Dongu istemcisi DEGISMEDI: ilk baglanan surucu, surucunun p1'i gecer, yabancinin p1'i 403, "
       "p0 herkese acik, E surucuye de kapali",
       bool(kim_d and kim_d["surucu"]) and (kod1, kod2, kod3, kod4) == (204, 403, 204, 403)
       and k3.kart.yazilanlar[once:] == ["p1", "p0"],
       f"{(kod1, kod2, kod3, kod4)} · {k3.kart.yazilanlar[once:]}")
    s_d.shutdown()
    s_d.server_close()

    # ── Host basligi: DNS yeniden baglama ────────────────────────────
    # Dongu baglamasi tek basina yetmez: kotu bir site kendi adini 127.0.0.1'e
    # cozdurup (DNS rebinding) AYNI KOKEN sayilir, X-Olcum basligini on-ucus
    # olmadan ekleyebilir ve USB'den komut gonderirdi.
    print("\n--- 4A. Host basligi (DNS yeniden baglama) ---")
    port = taban.rsplit(":", 1)[1]
    host = {}
    for h in ("olcum.localhost:" + port, "localhost:" + port, "127.0.0.1:" + port,
              "[::1]:" + port, "198.51.100.23:" + port, "kotu.example:" + port,
              "olcum.local", "olcum.localhost.kotu.example:" + port):
        host[h] = istek(taban + "/durum", basliklar={"Host": h})[0]
    ok("[!] Host yalniz localhost / *.localhost / IP: tanimadik ad 403 (kotu.example, olcum.local, "
       "*.localhost.kotu.example)",
       [h for h, c in host.items() if c == 200] == list(host)[:5]
       and all(c == 403 for h, c in list(host.items())[5:]), str(host))
    kod, _ = istek(taban + "/komut", b"p0", {"X-Olcum": "1", "Host": "kotu.example:" + port}, "POST")
    kod_iyi, _ = istek(taban + "/komut", b"p0", {"X-Olcum": "1", "Host": "olcum.localhost:" + port},
                       "POST")
    ok("Yabanci Host'tan komut karta gitmiyor; panelin kendi kokeninden p0 geciyor",
       kod == 403 and kod_iyi == 204, f"kotu={kod} olcum.localhost={kod_iyi}")

    # ── gizli satir suzgeci (D5 #12) ─────────────────────────────────
    print("\n--- 4A. EK / parola satiri suzgeci (onekli, bolunmus) ---")
    K1 = "0123456789abcdef" * 4          # deneme anahtarlari — gercek degil
    K2 = "fedcba9876543210" * 4
    # Her katman AYRI sinaniyor (biri kalkinca oteki ortmesin — mutasyon 4A):
    #   isaret (onekli EK) · pencere (24'ten kisa parca) · USB isareti · uzun hex.
    girdi = [
        "D 1.0",
        "W (1234) wifi: bekle EK 3 " + K1,          # TAM ve onekli: yalniz bu satir duser
        "* E: USB'den cihaz 3 eklendi",              # gecer (tam EK'de pencere yok)
        "D 2.0",
        "W (1300) wifi: x EK 4 I (1301) araya girdi",  # onekli VE eksik: anahtar alt satirlarda
        K2[:20],                                     # 20 hex (< 24): YALNIZ pencere yakalar
        K2[20:40],
        "D 3.0",
        "   AP parolasi (yalniz USB): ",             # parola alt satira dustu
        "OrnekParola-12",
        "* web parolasi: KURULU",
        "D 4.0",
        "E zorunlu=0 misafir=1 tur=20000 kimlik=0a1b2c3d4e5f6789 saat=1 cihaz=1",
        "K 1735689600123456789 1503 0",
        "x " + K1[10:40],                            # pencere disinda 30 hex: YALNIZ hex kurali
        K2[40:],                                     # 24 hex: YALNIZ hex kurali
        "D 5.0",
    ]
    beklenen = ["D 1.0", girdi[2], "D 2.0", "D 3.0", "D 4.0", girdi[12], girdi[13], "D 5.0"]
    kart4 = kart_baglanti.KayitKart(list(girdi))
    kart4.ac()
    k4 = kopru_mod.Kopru(kart4, gec_dizin / "arsiv_4a_ek")
    yayilan: list[str] = []
    k4.yayinla = yayilan.append
    threading.Thread(target=k4.dongu, daemon=True).start()
    son = time.monotonic() + 4.0
    while len(yayilan) < len(beklenen) and time.monotonic() < son:
        time.sleep(0.02)
    time.sleep(0.3)
    k4.calisiyor = False
    time.sleep(0.6)
    k4.arsiv.kapat()
    arsiv4 = list(k4.arsiv.ham_satirlar())
    parcalar = [x[i:i + 12] for x in (K1, K2) for i in range(0, 64, 4)] + ["OrnekParola", "EK "]
    sizan = sorted({p for p in parcalar for s in yayilan + arsiv4 if p in s})
    ok("[!] D5 #12: onekli/bolunmus EK anahtari ve USB'ye ozel parola YAYINLANMIYOR, ARSIVLENMIYOR",
       not sizan, f"sizan: {sizan}" if sizan else "hicbir 12'lik parca yok")
    ok("Suzgec olcumu yemiyor: pencere disindaki satirlar (16 hex kimlik, uzun ondalik) GECIYOR",
       yayilan == beklenen, str(yayilan))
    k4.durdur()

    # ── PC3: port VID'den ────────────────────────────────────────────
    print("\n--- 4A. PC3 COM portu VID'den ---")

    def sec(portlar):
        try:
            return kart_baglanti.kart_portu_sec(portlar), ""
        except RuntimeError as e:
            return None, str(e)

    p, _ = sec({"COM3": "303A", "COM6": "1A86"})
    ok("[!] PC3: kopru cipli port (1A86) seciliyor, yerel USB (303A) secilmiyor", p == "COM6", str(p))
    p_, n_ = sec({"COM3": "303A"})
    ok("[!] PC3: yalniz 303A varsa SECILMIYOR; mesaj yanlis soketi soyluyor",
       p_ is None and "303A" in n_ and "COM" in n_ and "soket" in n_, n_[:110])
    p_, n_ = sec({"COM6": "1A86", "COM9": "10C4"})
    ok("PC3: iki kopru cipli port -> secmiyor, ikisini de sayip --port istiyor",
       p_ is None and "COM6" in n_ and "COM9" in n_ and "--port" in n_, n_[:110])
    p_, n_ = sec({})
    ok("PC3: port yoksa acik mesaj", p_ is None and "bulunamadi" in n_, n_[:80])
    p, _ = sec({"COM4": None, "COM7": "0403", "COM8": "1A86/303A"})
    ok("PC3: VID'i bilinmeyen / belirsiz port secilmiyor (FTDI 0403 seciliyor)", p == "COM7", str(p))
    eski = kart_baglanti.portlar_vid
    try:
        # 303A bilerek SON sirada: eski kural "son port"tu
        kart_baglanti.portlar_vid = lambda: {"COM250": "1A86", "COM251": "303A"}
        try:
            kart_baglanti.SeriKart(None).ac()
            m = "acildi?!"
        except RuntimeError as e:
            m = str(e)
        ok("PC3: SeriKart(port yok) VID secimini kullaniyor (COM250'yi deniyor, sondaki 303A'yi degil)",
           "COM250" in m and "COM251" not in m, m[:100])
        try:
            kart_baglanti.SeriKart("COM251").ac()
            m = "acildi?!"
        except RuntimeError as e:
            m = str(e)
        ok("PC3: elle verilen 303A port da REDDEDILIYOR (sessiz soket)", "303A" in m, m[:100])
    finally:
        kart_baglanti.portlar_vid = eski

    # Mesgul port: kopru o portu tutuyorsa mesaj BUNU soyler.
    class _KopruKarti(kart_baglanti.KayitKart):
        ad = "seri:COM250@115200"

    k5 = kopru_mod.Kopru(_KopruKarti([]), gec_dizin / "arsiv_4a_mesgul")
    s_m = _kos(k5)
    mp = s_m.server_address[1]
    m_kopru = kart_baglanti.acma_hatasi("COM250", 5, kopru_portlari=(mp,))
    m_baska = kart_baglanti.acma_hatasi("COM251", 5, kopru_portlari=(mp,))
    m_yok = kart_baglanti.acma_hatasi("COM250", 2, kopru_portlari=(mp,))
    s_m.shutdown()
    s_m.server_close()
    ok("[!] PC3: port mesgul VE kopru tutuyor -> 'kopru bu portu kullaniyor — kapat'",
       "kopru bu portu kullaniyor" in m_kopru and "kapat" in m_kopru, m_kopru[:110])
    ok("PC3: baska program tutuyorsa kopruyu SUCLAMIYOR (ama olasiligi soyluyor)",
       "kopru bu portu kullaniyor" not in m_baska and "mesgul" in m_baska, m_baska[:110])
    ok("PC3: WinError 2 'port yok' olarak kaliyor", "port yok" in m_yok, m_yok[:80])

    # ── PC4: tek kopya, sessiz kip, hata izi ─────────────────────────
    print("\n--- 4A. PC4 tek ana surec ---")
    k6 = kopru_mod.Kopru(kart_baglanti.KayitKart([]), gec_dizin / "arsiv_4a_tek")
    s_t = _kos(k6)
    tp = s_t.server_address[1]
    class _SessizHttp(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):          # "kopru degil" sunucusu: 404 gunlugu gurultu
            pass

    baska = _kos(None, _SessizHttp)
    bp = baska.server_address[1]
    bos = socket.socket()
    bos.bind(("127.0.0.1", 0))
    yp = bos.getsockname()[1]
    bos.close()
    ok("zaten_calisiyor: kopru varsa True, baska HTTP sunucusu / bos port False",
       pc_mod.zaten_calisiyor(tp) and not pc_mod.zaten_calisiyor(bp)
       and not pc_mod.zaten_calisiyor(yp), f"kopru={tp} baska={bp} bos={yp}")
    acilan: list[str] = []
    t0 = time.monotonic()
    rc = pc_mod.calistir(["--http-port", str(tp)], tarayici_ac=acilan.append)
    ok("[!] PC4: kopru calisirken ikinci kopya BASLAMIYOR, yalniz tarayiciyi aciyor",
       rc == 0 and acilan == [pc_ayar.adres(tp) + "/"] and time.monotonic() - t0 < 5,
       f"rc={rc} acilan={acilan}")
    acilan.clear()
    rc = pc_mod.calistir(["--http-port", str(tp), "--sessiz"], tarayici_ac=acilan.append)
    ok("PC4: --sessiz ikinci kopya tarayici da acmadan cikiyor", rc == 0 and acilan == [],
       f"rc={rc} acilan={acilan}")
    rc = pc_mod.calistir(["--http-port", str(tp), "--kayit", "yok.satir"], tarayici_ac=acilan.append)
    ok("PC4: olu tekrar canli kopruyle carpisinca tarayici ACMIYOR, hata veriyor (baska port onerir)",
       rc != 0 and acilan == [], f"rc={rc}")
    hata_dizini = gec_dizin / "pc_dizin"
    eski_env = os.environ.get("OLCUM_PC_DIZIN")
    os.environ["OLCUM_PC_DIZIN"] = str(hata_dizini)
    try:
        rc = pc_mod.main(["--sessiz", "--http-port", str(bp), "--kayit", "yok.satir"])
    finally:
        if eski_env is None:
            os.environ.pop("OLCUM_PC_DIZIN", None)
        else:
            os.environ["OLCUM_PC_DIZIN"] = eski_env
    iz = hata_dizini / "arkaplan-hata.txt"
    ok("[!] PC4: --sessiz cokuste iz OLCUM_PC_DIZIN/arkaplan-hata.txt'e yaziliyor",
       rc == 1 and iz.is_file() and str(bp) in iz.read_text(encoding="utf-8"),
       f"rc={rc} {iz.name if iz.is_file() else 'iz YOK'}")
    s_t.shutdown()
    s_t.server_close()
    baska.shutdown()
    baska.server_close()

    os.environ.pop("OLCUM_PC_DIZIN", None)
    vd = pc_ayar.veri_dizini()
    if eski_env is not None:
        os.environ["OLCUM_PC_DIZIN"] = eski_env
    yerel = os.environ.get("LOCALAPPDATA", "")
    ok("PC5: veri dizini kullanici basina, depo DISINDA (%LOCALAPPDATA%\\olcum-karti)",
       vd.name == "olcum-karti" and (not yerel or str(vd).startswith(yerel))
       and KOK.resolve() not in vd.resolve().parents, str(vd.name))

    # ── kart takili degilken de acilir, kopunca yeniden baglanir ─────
    print("\n--- 4A. Kart yokken acilis + kopunca yeniden baglanma ---")
    durum = {"var": False, "kurulan": 0}

    class _Sahte(kart_baglanti.KayitKart):
        kopuk = False

    def kurucu(port):
        durum["kurulan"] += 1
        if not durum["var"]:
            raise RuntimeError("COM portu bulunamadi — kart takili mi?")
        return _Sahte(["D 9.0"])

    bildirim: list[str] = []
    oto = kart_baglanti.OtoSeriKart(None, aralik=0.0, kurucu=kurucu)
    oto.bildir = bildirim.append
    oto.ac()
    bos_okuma = [oto.satir_oku(0.01) for _ in range(5)]
    ok("[!] PC4: kart takili DEGILKEN acilis cokmuyor; 'bulunamadi' BIR KEZ soyleniyor (spam yok)",
       bos_okuma == [None] * 5 and len(bildirim) == 1 and "bulunamadi" in bildirim[0],
       str(bildirim))
    durum["var"] = True
    gelen = [oto.satir_oku(0.01) for _ in range(3)]
    ok("Kart takilinca kendiliginden baglaniyor ve satir akiyor",
       "D 9.0" in gelen and any("baglandi" in b for b in bildirim), f"{gelen} · {bildirim[-1:]}")
    oto._kart.kopuk = True
    k_once = durum["kurulan"]
    [oto.satir_oku(0.01) for _ in range(3)]
    ok("Kart kopunca soyleniyor ve YENIDEN aciliyor",
       any("koptu" in b for b in bildirim) and durum["kurulan"] > k_once, str(bildirim))
    hata = ""
    oto2 = kart_baglanti.OtoSeriKart(None, aralik=60.0, kurucu=lambda p: (_ for _ in ()).throw(
        RuntimeError("COM portu bulunamadi")))
    oto2.ac()
    try:
        oto2.yaz("?")
    except Exception as e:                              # noqa: BLE001
        hata = str(e)
    ok("Kart yokken komut ACIK hatayla reddediliyor (sessizce kaybolmuyor)",
       "bagli degil" in hata, hata[:80])
    # Durum satiri BIR KEZ yayinlaniyor; o an abonesi olmayan (acilistan sonra
    # gelen tarayici) onu ancak /akis'e baglaninca alabilir.
    k7 = kopru_mod.Kopru(oto2, gec_dizin / "arsiv_4a_oto")
    s_o = _kos(k7)
    gelen7, _ = akis_oku(f"http://127.0.0.1:{s_o.server_address[1]}/akis", 1, zaman_asimi=4.0)
    s_o.shutdown()
    s_o.server_close()
    ok("[!] Kart yokken SONRADAN baglanan tarayici da 'kart bulunamadi'yi goruyor",
       len(gelen7) == 1 and "bulunamadi" in gelen7[0], str(gelen7))
    ok("Durum satiri kart baglaninca temizleniyor (eski hata yeni gelene gosterilmez)",
       oto.durum_satiri is None, str(oto.durum_satiri))


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
    # 3A (P4): `/ortak/` — kopru ve gelistirme sunucusu AYNI kurali uyguluyor.
    ortak_sina(taban, "kopru")
    gelistirme_sunucusu_sina()

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

    # ── 1D: E komutlari yalniz USB; EK satiri (cihaz anahtari) ASLA yayinlanmaz ──
    # Kopru kartin USB satirlarini agdaki istemcilere tasiyor: kart `Ep` ile
    # anahtari YALNIZ seri porta basar (ham UART), ama kopru o portu okuyorsa
    # anahtari aga cikarirdi. Ikinci savunma katmani burada.
    print("\n--- 1D. Kopru: E komutu reddi, EK satiri suzgeci ---")
    izin, neden = k.komut_izinli("Ep telefon", None)
    ok("E komutu (USB eslestirme / zorunluluk) koprude REDDEDILIR, surucu yokken bile",
       not izin and "USB" in neden, neden)
    kart2 = kart_baglanti.KayitKart(["D 1.0", "EK 3 " + "ab" * 32, "E 12.5 enerji", "D 2.0"])
    kart2.ac()
    k2 = kopru_mod.Kopru(kart2, gec_dizin / "arsiv2")
    # ⚠ k2 TAZE (surucu YOK): k'de surucu kayitli oldugu icin anonim her komut zaten
    #   reddediliyordu ve bu iddia bos kaliyordu (ilk yazilisi oyleydi)
    izin2 = [k2.komut_izinli(x, None)[0] for x in ("?\nEz0", "x\rEx!", "p0\nEp evil", "?\x00Ez1")]
    ok("Satir sonu / kontrol karakteri gomulu komut REDDEDILIR (kart seriyi \\r\\n'de boler: "
       "'?\\nEz0' E suzgecini atlatirdi); surucusuz koprude duz p0 ve ? serbest kalir",
       k2.surucu is None and not any(izin2) and k2.komut_izinli("p0", None)[0]
       and k2.komut_izinli("?", None)[0], str(izin2))
    izin_e, neden_e = k2.komut_izinli("Ep telefon", None)
    ok("E komutu surucusuz (anonim kabul eden) koprude de REDDEDILIR",
       not izin_e and "USB" in neden_e, neden_e)
    # 1E (K9): Q komutlari MQTT araci parolalarini tasir — yalniz USB
    izin_q = [k2.komut_izinli(x, None) for x in ("Q?", "Qpgizli", "Q1")]
    ok("1E: Q komutu (MQTT bildirim ayari) surucusuz koprude de REDDEDILIR",
       not any(i for i, _ in izin_q) and all("USB" in n for _, n in izin_q), str(izin_q))
    yayilan = []
    k2.yayinla = yayilan.append
    threading.Thread(target=k2.dongu, daemon=True).start()
    son = time.monotonic() + 3.0
    while len(yayilan) < 3 and time.monotonic() < son:
        time.sleep(0.02)
    time.sleep(0.3)
    k2.calisiyor = False
    time.sleep(0.6)
    k2.arsiv.kapat()
    arsiv2 = list(k2.arsiv.ham_satirlar())
    ok("EK satiri (cihaz anahtari) YAYINLANMAZ ve ARSIVLENMEZ; 'E ' onekli baska satir tasinir",
       yayilan == ["D 1.0", "E 12.5 enerji", "D 2.0"] and not any("EK " in s for s in arsiv2),
       f"{yayilan} | arsiv {arsiv2}")
    k2.durdur()

    pc_4a_sina(gec_dizin, taban)

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
        ("4A: panel http://olcum.localhost:8770 (stok-takip ile carpisma yok)",
         "`kopru/PC Baslat.bat` -> tarayici olcum.localhost:8770'i acmali, panel "
         "kendiliginden baglanmali (stok-takip 127.0.0.1:80; farkli port, farkli ad). "
         "2026-10-03 COM6'da kosuldu: VID secimi COM6 (1A86), akista D satirlari, Host "
         "denetimi, mesgul port mesaji 'PC kopru bu portu kullaniyor', ikinci kopya acilmadi"),
        ("4A: telefon `--lan` ile SALT OKUMA",
         "`python kopru/pc.py --lan` -> telefondan http://<PC-IP>:8770 canli olcumu "
         "gostermeli; `p0` (DURDUR) gecmeli, baska her komut 403 'yerel agdan salt "
         "okuma'. Komut icin telefon karta DOGRUDAN baglanir (olcum.local). Iki "
         "tarayici ayni anda izlerken YALNIZCA bu bilgisayardaki surucu olmali"),
        ("4A: Baslangic kisayolu",
         "`kopru/Otomatik Baslat Kur.bat` -> oturumu kapat/ac -> pythonw arka planda, "
         "olcum.localhost:8770 acilir; kart takili degilken de acilir, takilinca akis "
         "baslar. `Otomatik Baslatmayi Kapat.bat` kisayolu siler (kurulum kullanicinin)"),
        ("4A: USB kablosu cek / tak",
         "Kopru acikken kabloyu cek: akista BIR KEZ '! kopru: kart baglantisi koptu'; "
         "tak: '* kopru: kart baglandi' ve D satirlari geri gelir. ReadFile'in kopmada "
         "FALSE dondugu gercek CH343'te SINANMADI (OtoSeriKart sahte kartla sinaniyor)"),
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
