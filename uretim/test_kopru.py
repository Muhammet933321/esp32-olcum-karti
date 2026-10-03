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
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gercek_dizin_koru                                   # noqa: E402
_KORUMA = gercek_dizin_koru.koru()   # LOCALAPPDATA gecici dizine — gercek PC dizinine asla yazilmaz
os.environ["OLCUM_TOAST_YOK"] = "1"  # 4E: pc.calistir GERCEK bildirim cikisiyla kosuyor — toast/kayit defteri YOK
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
    kod_x, _ = istek(lt + "/skop.bin", basliklar={"X-Olcum": "1", "X-Jeton": kim["jeton"] if kim else "x"})
    # 4A inceleme: surucunun `tB`si yolda iken (skop_kurulu) yerel ag yakalamayi KAPAMAZ
    k3.skop_hazirla()
    kod_k, _ = _guvenli_istek(lt + "/skop.bin", zaman_asimi=3)
    k3.skop_kurulu = False
    ok("[!] PC2: yerel ag istemcisi /skop.bin ile karta YAKALAMA YAPTIRAMIYOR (`t` gitmez; X-Olcum'la "
       "da), surucunun bekleyen yakalamasini da KAPAMIYOR",
       (kod, kod_x, kod_k) == (403, 403, 403) and k3.kart.yazilanlar[once_t:] == [],
       f"HTTP {kod}/{kod_x}/bekleyen {kod_k} · {k3.kart.yazilanlar[once_t:]}")
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
        return _Sahte([D9])

    # 4A inceleme: otomatik secimde kart KIMLIGI dogrulaniyor — sahte kart gercek
    # bicimde `D` satiri basiyor; aday listesi kayit defterinden degil, sabit.
    D9 = "D 9.0000 0.100000 0.90000 0.0000 0.0000000 1000 100 0 0"
    bildirim: list[str] = []
    oto = kart_baglanti.OtoSeriKart(None, aralik=0.0, kurucu=kurucu, adaylar=lambda: ["COM250"])
    oto.bildir = bildirim.append
    oto.ac()
    bos_okuma = [oto.satir_oku(0.01) for _ in range(5)]
    ok("[!] PC4: kart takili DEGILKEN acilis cokmuyor; 'bulunamadi' BIR KEZ soyleniyor (spam yok)",
       bos_okuma == [None] * 5 and len(bildirim) == 1 and "bulunamadi" in bildirim[0],
       str(bildirim))
    durum["var"] = True
    gelen = [oto.satir_oku(0.01) for _ in range(3)]
    ok("Kart takilinca kendiliginden baglaniyor ve satir akiyor",
       D9 in gelen and any("baglandi" in b for b in bildirim), f"{gelen} · {bildirim[-1:]}")
    oto._kart.kopuk = True
    k_once = durum["kurulan"]
    [oto.satir_oku(0.01) for _ in range(3)]
    ok("Kart kopunca soyleniyor ve YENIDEN aciliyor",
       any("koptu" in b for b in bildirim) and durum["kurulan"] > k_once, str(bildirim))
    hata = ""
    oto2 = kart_baglanti.OtoSeriKart(None, aralik=60.0, adaylar=lambda: ["COM250"],
                                     kurucu=lambda p: (_ for _ in ()).throw(
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


def _bos_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _guvenli_istek(url, veri=None, basliklar=None, yontem=None, zaman_asimi=5):
    """`istek` + baglanti hatasi (isleyici coktu) -> (None, hata)."""
    try:
        return istek(url, veri, basliklar, yontem, zaman_asimi)
    except Exception as e:                              # noqa: BLE001
        return None, str(e).encode("utf-8", "replace")


def pc_4a_inceleme_sina(gec_dizin: Path) -> None:
    """4A inceleme bulgulari (2026-10-03) — her biri once KIRMIZI goruldu.

    CSRF (baska kokenden <img> GET'i karta `t` yollatiyor, suruculugu kapiyordu),
    `gun` yol gecisi / UNC, port acilisindaki yarim satirin suzgeci atlamasi,
    yabanci CH34x aygitinin portunu ele gecirme, suzgecin yanlis pozitifleri,
    kucuk harfli `--port`, vekil, olu tekrarin cekirdek yakmasi, yaz/kapat
    yarisi, konsolda gorunmeyen port hatasi, kopruyu durdurma yolu.
    """
    import os
    import pc as pc_mod                                     # noqa: E402
    import pc_ayar                                          # noqa: E402

    SKOP = (["S2 64 10000 0.028787 12 5000 0 1 63.530093",
             "M f=156.250 T=0.006400000 Vpp=24.0000 n=10"]
            + [" ".join(str((i * 37) % 4096) for i in range(j, j + 16)) for j in range(0, 64, 16)]
            + ["E"])

    # ── 1. CSRF: baska kokenden GET yan etkisiz ──────────────────────
    print("\n--- 4A inceleme 1. Capraz koken (CSRF) ---")
    kc = kart_baglanti.KayitKart([], yanitlar={"t": SKOP, "p0": ["* durdu"]})
    kc.ac()
    k = kopru_mod.Kopru(kc, gec_dizin / "arsiv_csrf")
    threading.Thread(target=k.dongu, daemon=True).start()
    s = _kos(k)
    p = s.server_address[1]
    tb = f"http://127.0.0.1:{p}"
    yabanci = {
        "same-site (baska port)": {"Sec-Fetch-Site": "same-site"},
        "cross-site": {"Sec-Fetch-Site": "cross-site"},
        "Origin baska port": {"Origin": "http://127.0.0.1:1"},
        "Origin baska ad": {"Origin": "http://stok"},
    }
    sonuc = {}
    for ad, b in yabanci.items():
        kod_s, _ = _guvenli_istek(tb + "/skop.bin", basliklar={**b, "X-Olcum": "1"}, zaman_asimi=8)
        kod_a, _ = _guvenli_istek(tb + "/akis", basliklar=b)
        sonuc[ad] = (kod_s, kod_a)
    ok("[!] CSRF: baska kokenden (Sec-Fetch-Site same-site/cross-site, yabanci Origin) /skop.bin "
       "ve /akis 403 — karta HICBIR SEY gitmedi, surucu/jeton verilmedi",
       all(v == (403, 403) for v in sonuc.values()) and kc.yazilanlar == []
       and k.surucu is None and not k.jetonlar,
       f"{sonuc} · karta={kc.yazilanlar} surucu={k.surucu} jeton={len(k.jetonlar)}")
    kod, _ = _guvenli_istek(tb + "/skop.bin", zaman_asimi=8)
    ok("[!] /skop.bin X-Olcum'suz (img/curl) kendi `t`sini YOLLAMIYOR: 403, karta bir sey gitmez",
       kod == 403 and kc.yazilanlar == [], f"HTTP {kod} · {kc.yazilanlar}")
    ayni = {"Sec-Fetch-Site": "same-origin", "Origin": f"http://olcum.localhost:{p}",
            "Host": f"olcum.localhost:{p}"}
    # 4I: ilk sekme ACIK kalir — kapansaydi rol (dogru olarak) ikinciye gecerdi
    acik_ilk = _AcikAkis(tb, ayni)
    kim = acik_ilk.kimlik()
    kim_none = kimlik_oku(tb + "/akis", basliklar={"Sec-Fetch-Site": "none"})
    ok("Ayni koken (same-origin, Origin = Host) ve adres cubugu (none) /akis aliyor; ilki surucu",
       bool(kim and kim.get("surucu")) and kim_none is not None and kim_none.get("surucu") is False,
       f"{kim} · {kim_none}")
    jet = kim["jeton"] if kim else ""
    kod1, govde1 = _guvenli_istek(tb + "/skop.bin", basliklar={**ayni, "X-Olcum": "1", "X-Jeton": jet},
                                  zaman_asimi=8)
    kod2, _ = _guvenli_istek(tb + "/skop.bin", basliklar={"X-Olcum": "1", "X-Jeton": "baskasi"},
                             zaman_asimi=8)
    ok("[!] /skop.bin kendi `t`si /komut'un kapisindan: X-Olcum + SURUCU jetonu 200, yabanci jeton 403",
       kod1 == 200 and (govde1 or b"")[:3] == b"S3B" and kod2 == 403 and kc.yazilanlar == ["t"],
       f"surucu={kod1} yabanci={kod2} · karta={kc.yazilanlar}")
    once = list(kc.yazilanlar)
    kod_x, _ = _guvenli_istek(tb + "/komut", b"GF!", {"X-Olcum": "1", "X-Jeton": jet,
                                                       "Sec-Fetch-Site": "cross-site"}, "POST")
    kod_p0, _ = _guvenli_istek(tb + "/komut", b"p0", {"X-Olcum": "1", "Sec-Fetch-Site": "cross-site",
                                                       "Origin": "http://stok"}, "POST")
    kod_dv, _ = _guvenli_istek(tb + "/devral", b"", {"X-Olcum": "1", "X-Jeton": jet,
                                                      "Origin": "http://stok"}, "POST")
    ok("[!] /komut: baska kokenden komut 403 (surucu jetonu olsa da), `p0` (DURDUR) yine GECIYOR; "
       "/devral 403",
       kod_x == 403 and kod_p0 == 204 and kod_dv == 403 and kc.yazilanlar[len(once):] == ["p0"],
       f"GF!={kod_x} p0={kod_p0} devral={kod_dv} · karta={kc.yazilanlar[len(once):]}")
    acik_ilk.kapat()

    # ── 2. gun yol gecisi ────────────────────────────────────────────
    print("\n--- 4A inceleme 2. `gun` parametresi (yol gecisi, UNC) ---")
    import urllib.parse
    dis = gec_dizin / "disarida" / "gizli.satir"
    dis.parent.mkdir(parents=True, exist_ok=True)
    dis.write_text("".join(f"{i}\t{x}\n" for i, x in enumerate(SKOP, 1)), encoding="utf-8")
    (k.arsiv.dizin / "gizli.satir").write_text(dis.read_text(encoding="utf-8"), encoding="utf-8")
    kotu = [str(dis.with_suffix("")).replace("\\", "/"), str(dis.with_suffix("")),
            "//saldirgan.example/pay/x", "\\\\saldirgan.example\\pay\\x", "../disarida/gizli",
            "..\\..\\x", "C:x", "gizli", "2026-1-01", "2026-10-03/../../x", "２０２６-10-03"]
    kodlar = {}
    for g in kotu:
        q = urllib.parse.quote(g, safe="")
        kodlar[g[-14:]] = (_guvenli_istek(tb + f"/skop/liste?gun={q}")[0],
                           _guvenli_istek(tb + f"/skop/al?gun={q}&ms=1")[0])
    ok("[!] /skop/liste ve /skop/al: gun yalniz YYYY-AA-GG — mutlak, UNC (// ve \\\\), '..', surucu, "
       "arsivdeki tarih-disi ad 400",
       all(v == (400, 400) for v in kodlar.values()), str(kodlar))
    kod_iyi, govde_iyi = _guvenli_istek(tb + "/skop/liste?gun=2000-01-01")
    ok("Gecerli bicimdeki gun 200 (kayit yoksa bos liste); tarih-disi .satir gun listesine girmiyor",
       kod_iyi == 200 and json.loads(govde_iyi).get("kayitlar") == []
       and "gizli" not in json.loads(govde_iyi).get("gunler", []),
       f"HTTP {kod_iyi} {govde_iyi[:120]!r}")
    from arsiv import Arsiv as _Arsiv
    a = _Arsiv(gec_dizin / "arsiv_gun")
    (a.dizin / "gizli.satir").write_text(dis.read_text(encoding="utf-8"), encoding="utf-8")
    redler = {}
    for g in ("gizli", str(dis.with_suffix("")), "//saldirgan.example/pay/x", "../x", "C:x"):
        try:
            list(a.skop_ozet(g))
            list(a.ham_satirlar(g))
            redler[g[-12:]] = "KABUL"
        except ValueError:
            redler[g[-12:]] = "ret"
    ok("[!] Arsiv katmani da (derinlemesine savunma): tarih bicimi disindaki gun ValueError — "
       "arsivdeki 'gizli.satir' bile okunmaz",
       all(v == "ret" for v in redler.values()), str(redler))
    k.calisiyor = False
    s.shutdown()
    s.server_close()
    time.sleep(0.6)
    k.durdur()

    # ── 3. port acilisindaki yarim satir ─────────────────────────────
    print("\n--- 4A inceleme 3. Acilista / yeniden baglanmada yarim satir ---")
    sk = kart_baglanti.SeriKart("COM250")
    parcalar = [b"q9wRt2z-Parola\r\nD 1.0 0.1 0.1 0 0 1 1 0 0\r\n"]
    sk._ham_oku = lambda: parcalar.pop(0) if parcalar else b""
    sk._baglanti_basladi()
    ilk = [sk.satir_oku(0.05), sk.satir_oku(0.05)]
    parcalar.append(b"XyZ-kuyruk\r\nK 1 2 3\r\n")
    sk._baglanti_basladi()                 # yeniden baglanma: yine yarim satirdan
    ikinci = [sk.satir_oku(0.05)]
    ok("[!] SeriKart: her acilista ILK (yarim) satir ATILIYOR — parola kuyrugu satir sanilmiyor",
       ilk == ["D 1.0 0.1 0.1 0 0 1 1 0 0", None] and ikinci == ["K 1 2 3"], f"{ilk} {ikinci}")

    class _Kopabilir(kart_baglanti.KayitKart):
        kopuk = False

        def satir_oku(self, zaman_asimi=0.5):
            s_ = super().satir_oku(zaman_asimi)
            if s_ is None and self.kopacak:
                self.kopuk = True
            return s_

    kartlar = []

    def yeni_kart(satirlar, kopacak):
        c = _Kopabilir(satirlar)
        c.kopacak = kopacak
        kartlar.append(c)
        return c

    sira = [lambda: yeni_kart(["Gizli-Parca-1", "D 2.0", "D 3.0", "   AP parolasi (yalniz USB): "], True),
            lambda: yeni_kart(["Gizli-Kuyruk-2", "D 4.0", "D 5.0", "D 6.0"], False)]
    oto = kart_baglanti.OtoSeriKart(None, aralik=0.0, adaylar=lambda: ["COM250"], dogrula=False,
                                    kurucu=lambda port: sira.pop(0)() if sira else (_ for _ in ()).throw(
                                        RuntimeError("yok")))
    k3 = kopru_mod.Kopru(oto, gec_dizin / "arsiv_yarim")
    yayilan: list[str] = []
    k3.yayinla = yayilan.append
    oto.bildir = yayilan.append
    threading.Thread(target=k3.dongu, daemon=True).start()
    son = time.monotonic() + 4
    while "D 6.0" not in yayilan and time.monotonic() < son:
        time.sleep(0.02)
    k3.calisiyor = False
    time.sleep(0.6)
    k3.arsiv.kapat()
    arsiv3 = list(k3.arsiv.ham_satirlar())
    sizan = [x for x in yayilan + arsiv3 if "Gizli" in x]
    ok("[!] Kopru: (yeniden) baglanti suzgec penceresini ACIYOR ve kisaltmiyor — ilk parca da, "
       "baglanti koptuktan sonra isaretin kuyrugu da akisa/arsive GECMIYOR",
       not sizan and "D 3.0" in yayilan and "D 6.0" in yayilan and len(kartlar) == 2,
       f"sizan={sizan} · {[x for x in yayilan if not x.startswith('*') and not x.startswith('!')]}")
    k3.durdur()

    # ── 4. yabanci CH34x aygiti ──────────────────────────────────────
    print("\n--- 4A inceleme 4. Port yalniz KART dogrulaninca tutuluyor ---")
    ad = kart_baglanti.kart_adaylari({"COM3": "1A86:7523", "COM9": "1A86:55D3", "COM4": "303A:1001",
                                      "COM5": "10C4:EA60"})
    sec_ = kart_baglanti.kart_portu_sec({"COM3": "1A86:7523", "COM9": "1A86:55D3"})
    ok("[!] PC3: kartin tam VID:PID'i (CH343 1A86:55D3) ONCE; iki kopru cipi varken kart PID'i secilir",
       ad[0] == "COM9" and set(ad) == {"COM3", "COM9", "COM5"} and sec_ == "COM9", f"{ad} · {sec_}")

    class _Aygit(kart_baglanti.KayitKart):
        """Port arkasindaki aygit: `?`a yanit `soru` ile; acik/kapali izlenir."""

        def __init__(self, satirlar, soru=None):
            super().__init__(satirlar, yanitlar={"?": soru} if soru else {})
            self.acik = True

        def kapat(self):
            self.acik = False

        def yaz(self, metin):
            if metin == "?" and "?" not in self.yanitlar:
                self.yazilanlar.append(metin)     # yabanci aygit `?`a yanit vermez
                return
            super().yaz(metin)

    D = "D 12.3456 0.891234 10.99881 1234.5678 0.3429355 3600000 133 0 0"
    durumlar = {
        "kart D satiri": _Aygit(["W (12) boot", D]),
        "kart sessiz ama ? yanitli": _Aygit([], soru=["A menzil=NORMAL oto=1 n_kazanc=1.0"]),
        "Arduino Hello": _Aygit(["Hello", "Hello", "D 9.0"]),
        "sessiz aygit": _Aygit([]),
    }
    kimlik = {}
    for ad_, c in durumlar.items():
        t0 = time.monotonic()
        tamam, gorulen = kart_baglanti.kart_kimligi(c, pasif_sn=0.3, soru_sn=0.3)
        kimlik[ad_] = (tamam, c.yazilanlar, round(time.monotonic() - t0, 1))
    ok("[!] PC3: kart kimligi yalniz kartin satiriyla (D / K / `?` yaniti A); Arduino/sessiz aygit DEGIL; "
       "aygita `?` DISINDA hicbir sey yazilmaz (asla N?)",
       [v[0] for v in kimlik.values()] == [True, True, False, False]
       and kimlik["kart D satiri"][1] == []
       and all(set(v[1]) <= {"?"} for v in kimlik.values()), str(kimlik))
    aygitlar = {"COM3": _Aygit(["Hello"] * 3), "COM9": _Aygit([D, D])}
    acilan: list[str] = []

    def kurucu(port):
        acilan.append(port)
        c = aygitlar[port]
        c.acik = True
        c.ac()
        return c

    bild: list[str] = []
    oto4 = kart_baglanti.OtoSeriKart(None, aralik=0.0, kurucu=kurucu, adaylar=lambda: ["COM3", "COM9"],
                                     pasif_sn=0.2, soru_sn=0.2)
    oto4.bildir = bild.append
    oto4.ac()
    ok("[!] PC3: yabanci aygit (COM3) acildi, kart DEGIL -> BIRAKILDI (port kapatildi); kart (COM9) tutuldu",
       aygitlar["COM3"].acik is False and oto4.ad.startswith("kayit") and acilan == ["COM3", "COM9"]
       and any("baglandi" in b for b in bild), f"acilan={acilan} COM3.acik={aygitlar['COM3'].acik} {bild}")
    gelen4 = [oto4.satir_oku(0.05) for _ in range(3)]
    ok("Dogrulamada okunan kart satirlari akistan KAYBOLMUYOR (sirayla geri veriliyor)",
       gelen4[:2] == [D, D], str(gelen4))
    yalniz = {"COM3": _Aygit(["Hello"] * 3)}
    acilan2: list[str] = []
    bild2: list[str] = []

    def kurucu2(port):
        acilan2.append(port)
        yalniz[port].acik = True
        yalniz[port].ac()
        return yalniz[port]

    oto5 = kart_baglanti.OtoSeriKart(None, aralik=0.0, kurucu=kurucu2, adaylar=lambda: ["COM3"],
                                     pasif_sn=0.2, soru_sn=0.2)
    oto5.bildir = bild2.append
    for _ in range(4):
        oto5.satir_oku(0.01)
    ok("[!] PC3: yalniz yabanci aygit varken port TUTULMUYOR ve her 3 s'de yeniden ACILMIYOR "
       "(reddedilen port aygit takili kaldikca denenmez); mesaj sebebi soyluyor",
       oto5._kart is None and yalniz["COM3"].acik is False and acilan2 == ["COM3"]
       and any("olcum karti" in b for b in bild2), f"acilan={acilan2} {bild2[-1:]}")

    # ── 5. suzgecin yanlis pozitifleri ───────────────────────────────
    print("\n--- 4A inceleme 5. Suzgec: yanlis pozitif yok, gizli yine duser ---")
    gs = kopru_mod.GizliSuzgec()
    girdi = ["* faz kalibrasyonu (us): NORMAL 0.00  YUKSEK 1.50", "D 1", "D 2",
             "* AP parolasi kaydedildi", "  (bir sonraki acilista gecerli)", "D 3",
             "* web parolasi: KURULU", "D 4"]
    gecen = [x for x in girdi if gs.gecir(x)]
    ok("Suzgec yanlis pozitifsiz: 'YUKSEK 1.50' ve '* AP parolasi kaydedildi' ve ardindaki olcum "
       "satirlari GECIYOR", gecen == girdi, str(gecen))
    gs = kopru_mod.GizliSuzgec()
    gizli = ["EK 7", "a1b2c3d4e5f60718", "293a4b5c6d7e8f90", "D 1",
             "x AP parolasi", "Pw-Sinama-77", "D 2",
             "   AP parolasi (yal", "niz USB): Pw-Sinama-78", "D 3",
             "AP parolas", "Pw-Sinama-79", "D 4"]
    gecen = [x for x in gizli if gs.gecir(x)]
    ok("[!] Daraltilan isaretler gizliyi yine yakaliyor: satir sonunda biten `EK 7`, bolunmus "
       "'AP parolasi' / 'AP parolasi (yal' / 'AP parolas' — degerler GECMEZ",
       not any("Sinama" in x or "a1b2" in x or "293a" in x for x in gecen), str(gecen))

    # ── 6. kucuk harfli --port ───────────────────────────────────────
    eski = kart_baglanti.portlar_vid
    try:
        kart_baglanti.portlar_vid = lambda: {"COM251": "303A:1001"}
        try:
            kart_baglanti.SeriKart("com251").ac()
            m = "acildi?!"
        except RuntimeError as e:
            m = str(e)
    finally:
        kart_baglanti.portlar_vid = eski
    ok("[!] PC3: `--port com251` (kucuk harf) da 303A reddine takiliyor", "303A" in m, m[:90])

    # ── 7. vekil ─────────────────────────────────────────────────────
    print("\n--- 4A inceleme 7. Vekil (HTTP_PROXY) 127.0.0.1'i saptirmiyor ---")

    class _KopruKarti(kart_baglanti.KayitKart):
        ad = "seri:COM250@115200"

    k7 = kopru_mod.Kopru(_KopruKarti([]), gec_dizin / "arsiv_vekil")
    s7 = _kos(k7)
    p7 = s7.server_address[1]
    eski_env = {a_: os.environ.get(a_) for a_ in ("HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy")}
    try:
        for a_ in ("NO_PROXY", "no_proxy"):
            os.environ.pop(a_, None)
        os.environ["HTTP_PROXY"] = os.environ["http_proxy"] = f"http://127.0.0.1:{_bos_port()}"
        urllib.request._opener = None           # ortam vekili yeniden okunsun
        calisiyor = pc_mod.zaten_calisiyor(p7)
        tutuyor = kart_baglanti._kopru_portu_tutuyor("COM250", (p7,))
        m5 = kart_baglanti.acma_hatasi("COM250", 5, kopru_portlari=(p7,))
    finally:
        for a_, d_ in eski_env.items():
            if d_ is None:
                os.environ.pop(a_, None)
            else:
                os.environ[a_] = d_
        urllib.request._opener = None
    ok("[!] HTTP_PROXY tanimliyken de zaten_calisiyor ve 'kopru bu portu kullaniyor' yoklamasi "
       "kopruyu goruyor (vekilsiz)", calisiyor and tutuyor, f"zaten={calisiyor} tutuyor={tutuyor}")
    s7.shutdown()
    s7.server_close()
    k7.durdur()

    # ── 8. olu tekrar bitince bekleme ────────────────────────────────
    kk = kart_baglanti.KayitKart(["D 1"], yanitlar={"?": ["A menzil=NORMAL"]})
    kk.ac()
    kk.satir_oku(0.01)
    n, t0 = 0, time.monotonic()
    while time.monotonic() - t0 < 0.5:
        kk.satir_oku(0.1)
        n += 1
    yanit = {}

    def _bekleyen_okur():
        t1 = time.monotonic()
        yanit["s"] = kk.satir_oku(2.0)
        yanit["t"] = time.monotonic() - t1

    th = threading.Thread(target=_bekleyen_okur)
    th.start()
    time.sleep(0.15)
    kk.yaz("?")
    th.join(3)
    ok("[!] Olu tekrar bitince satir_oku BEKLIYOR (cekirdek yakmiyor), komut yaniti beklemeyi hemen kesiyor",
       n <= 8 and yanit.get("s") == "A menzil=NORMAL" and yanit.get("t", 9) < 0.5,
       f"0.5 s'de {n} cagri · yanit {yanit}")

    # ── 9. yaz / kapat yarisi ────────────────────────────────────────
    olay: list[str] = []

    class _Yavas(kart_baglanti.KayitKart):
        def yaz(self, metin):
            olay.append("yaz-bas")
            time.sleep(0.3)
            olay.append("yaz-son")

        def kapat(self):
            olay.append("kapat")

    oto9 = kart_baglanti.OtoSeriKart("COM250", aralik=0.0, kurucu=lambda p_: _Yavas([]))
    oto9.ac()
    tw = threading.Thread(target=lambda: oto9.yaz("p1"))
    tw.start()
    time.sleep(0.08)
    oto9.kapat()
    tw.join(2)
    hata9 = ""
    try:
        oto9.yaz("p1")
    except Exception as e:                              # noqa: BLE001
        hata9 = f"{type(e).__name__}: {e}"
    ok("[!] OtoSeriKart: kapat, suren yazmayi BEKLIYOR (kapanmis taniticiya yazilmaz); sonra acik hata",
       olay == ["yaz-bas", "yaz-son", "kapat"] and hata9.startswith("RuntimeError") and "bagli degil" in hata9,
       f"{olay} · {hata9[:60]}")

    # ── 10/11. konsol + durdurma yolu ────────────────────────────────
    print("\n--- 4A inceleme 10. Konsolda port hatasi + kopruyu durdurma ---")
    hp = _bos_port()
    yazilan: list[str] = []
    rc = {}

    def _calistir():
        rc["rc"] = pc_mod.calistir(["--port", "COM250", "--http-port", str(hp), "--tarayici-acma"],
                                   tarayici_ac=lambda u: None, yazdir=yazilan.append)

    tc = threading.Thread(target=_calistir, daemon=True)
    tc.start()
    son = time.monotonic() + 8
    while not any("COM250" in y and "bulunamadi" in y for y in yazilan) and time.monotonic() < son:
        time.sleep(0.05)
    ok("[!] Elle --port hatasi (COM250 yok) KONSOLA da yaziliyor (yalniz /akis'e degil)",
       any("COM250" in y and "bulunamadi" in y for y in yazilan), str(yazilan[-2:]))
    durdu, mesaj = pc_mod.durdur(hp)
    tc.join(6)
    ok("[!] `pc.py --durdur` kopruyu KENDI ucundan durduruyor (pythonw.exe oldurmek gerekmiyor)",
       durdu and not tc.is_alive() and rc.get("rc") == 0 and not pc_mod.zaten_calisiyor(hp),
       f"{durdu} {mesaj} rc={rc}")
    k8 = kopru_mod.Kopru(_KopruKarti([]), gec_dizin / "arsiv_kapat")
    s8 = _kos(k8, _LanIsleyici)
    lp = s8.server_address[1]
    kod_lan, _ = _guvenli_istek(f"http://127.0.0.1:{lp}/kapat", b"", {"X-Olcum": "1"}, "POST")
    s8.shutdown()
    s8.server_close()
    s9 = _kos(k8)
    p9 = s9.server_address[1]
    kod_xo, _ = _guvenli_istek(f"http://127.0.0.1:{p9}/kapat", b"", {}, "POST")
    kod_cr, _ = _guvenli_istek(f"http://127.0.0.1:{p9}/kapat", b"", {"X-Olcum": "1",
                                                                     "Sec-Fetch-Site": "same-site"}, "POST")
    hala = pc_mod.zaten_calisiyor(p9)
    s9.shutdown()
    s9.server_close()
    k8.durdur()
    ok("[!] /kapat yalniz bu bilgisayardan, X-Olcum ile, ayni kokenden: yerel ag 403, basliksiz 400, "
       "capraz 403 (kopru ayakta kaliyor)",
       kod_lan == 403 and kod_xo == 400 and kod_cr == 403 and hala, f"lan={kod_lan} xolcum={kod_xo} "
       f"capraz={kod_cr} ayakta={hala}")
    ps1 = (KOK / "kopru" / "otomatik-baslat.ps1").read_text(encoding="utf-8")
    bat = KOK / "kopru" / "Kopruyu Durdur.bat"
    ok("Mesgul port mesaji ve kisayol araci pythonw.exe oldurtmuyor (stok-takip de pythonw); "
       "durdurma yolunu soyluyor",
       "kopru bu portu kullaniyor" in m5 and "pythonw" not in m5 and "--durdur" in m5
       and "Gorev Yoneticisi >" not in ps1 and "Kopruyu Durdur" in ps1
       and bat.is_file() and "--durdur" in bat.read_text(encoding="utf-8"),
       m5[:110])

    # ── 12. belge ────────────────────────────────────────────────────
    bs = (BURASI / "belge_sayfa.py").read_text(encoding="utf-8")
    bg = (BURASI / "belge_grafik.py").read_text(encoding="utf-8")
    bu = (BURASI / "belge-uret.py").read_text(encoding="utf-8")
    ok("Belge (ag kipleri) yeni kokeni anlatiyor: adres pc_ayar'dan, yedek porta dusme YOK, yalniz bu "
       "bilgisayar, telefon --lan ile SALT OKUMA",
       "kopru_yedek" not in bs + bg + bu and "pc_ayar" in bu and "kopru_adres" in bs
       and "--lan" in bs and "salt okuma" in bs.lower() and "127.0.0.1" in bs,
       "belge_sayfa/belge_grafik/belge-uret")


class _SahteYukari:
    """4B: SecmeliKart'in USB / WiFi kolu icin sahte yukari-akis (OtoSeriKart / WifiKart yuzeyi)."""

    def __init__(self, ad: str, bagli: bool = False):
        self._ad, self.bagli = ad, bagli
        self.host = "olcum.local"
        self.bildir = None
        self.durum_satiri = None
        self.baglanti_no = 0
        self.satirlar: list[str] = []
        self.yazilan: list[str] = []
        self.acildi = self.kapandi = 0
        self.yaz_hata = None

    @property
    def ad(self) -> str:
        return self._ad

    def ac(self):
        self.acildi += 1

    def kapat(self):
        self.kapandi += 1

    def satir_oku(self, zaman_asimi=0.5):
        if self.satirlar and (self.bagli or self._ad.startswith("wifi")):
            return self.satirlar.pop(0)
        time.sleep(min(zaman_asimi, 0.01))
        return None

    def yaz(self, metin):
        if self.yaz_hata:
            raise RuntimeError(self.yaz_hata)
        if self._ad.startswith("seri") and not self.bagli:
            raise RuntimeError("kart bagli degil")
        self.yazilan.append(metin)


def _sec_oku(k, n, sure=3.0):
    son, al = time.monotonic() + sure, []
    while len(al) < n and time.monotonic() < son:
        x = k.satir_oku(0.05)
        if x is not None:
            al.append(x)
    return al


def pc_4b_sina(gec_dizin: Path) -> None:
    """4B (PC6): USB ONCE, yoksa kartla WiFi'den eslesmis cihaz olarak — SecmeliKart + pc.py.

    WifiKart'in kendisi (imzali /akis, kimlik, /saat) B72.W'de sahte karta karsi sinaniyor.
    """
    print("\n--- 4B. Yukari-akis secimi: USB once, yoksa WiFi (eslesmis cihaz) ---")
    import kart_wifi as KW
    import pc
    usb, wifi = _SahteYukari("seri:COM9@115200", bagli=True), _SahteYukari("wifi:olcum.local (cihaz 2)")
    usb.satirlar = ["D 1.0", "D 2.0"]
    wifi.satirlar = ["D 9.0"]
    k = KW.SecmeliKart(usb, wifi)
    durum = []
    k.bildir = durum.append
    al = _sec_oku(k, 2)
    ok("4B: USB'de dogrulanmis kart varken canli akis USB'den; WiFi HIC acilmaz",
       al == ["D 1.0", "D 2.0"] and wifi.acildi == 0 and k.etkin == "usb" and k.ad.startswith("seri:"),
       f"{al} wifi.ac={wifi.acildi}")
    usb.bagli = False
    no0 = k.baglanti_no
    al = _sec_oku(k, 1)
    ok("4B: USB'den kart gidince yukari-akis WiFi'ye GECER (WiFi acilir, satirlar ondan) ve gecis "
       "`* kopru:` durum satiriyla SOYLENIR; baglanti numarasi artar (suzgec penceresi acilir)",
       al == ["D 9.0"] and wifi.acildi == 1 and k.etkin == "wifi" and k.baglanti_no > no0
       and any(x.startswith("* kopru:") and "WiFi" in x for x in durum) and k.ad.startswith("wifi:"),
       f"{al} {durum[-1:]}")
    k.yaz("A?")
    ok("4B: WiFi seciliyken komut WiFi koluna gider (USB'ye degil)",
       wifi.yazilan == ["A?"] and usb.yazilan == [], f"{wifi.yazilan} {usb.yazilan}")
    wifi.durum_satiri = "! kopru: WiFi (olcum.local) — kart erisilemiyor"
    usb.durum_satiri = "! kopru: kart bulunamadi — USB"
    ok("4B: WiFi seciliyken sonradan baglanan tarayiciya WiFi'nin durum satiri gosterilir",
       k.durum_satiri == wifi.durum_satiri, str(k.durum_satiri))
    wifi.durum_satiri = None
    usb.bagli = True
    usb.satirlar = ["D 3.0"]
    wifi.satirlar = ["D 8.0"]
    al = _sec_oku(k, 1)
    ok("4B: kart USB'ye geri takilinca USB'ye DONER, WiFi baglantisi KAPATILIR (ayni satirlar iki "
       "kez arsive dusmesin) ve soylenir",
       al == ["D 3.0"] and wifi.kapandi >= 1 and k.etkin == "usb"
       and any("USB" in x and "kapatildi" in x for x in durum), f"{al} {durum[-1:]}")
    k.yaz("A?")
    ok("4B: USB seciliyken komut USB'den", usb.yazilan == ["A?"], str(usb.yazilan))
    # p0: hicbir secimde takilmaz
    usb.bagli = False
    k._sec("wifi")
    wifi.yaz_hata = "ag yok"
    usb.bagli = True
    k.yaz("p0")
    p0_usb = usb.yazilan[-1:] == ["p0"]
    usb.bagli = False
    wifi.yaz_hata = None
    k.yaz("p0")
    p0_wifi = wifi.yazilan[-1:] == ["p0"]
    wifi.yaz_hata = "ag yok"
    try:
        k.yaz("p0")
        iki_red = "gecti"
    except RuntimeError as e:
        iki_red = str(e)
    wifi.yaz_hata = None
    ok("4B: p0 (DURDUR) yukari-akis seciminde TAKILMAZ: bir yol olmazsa oteki denenir; ikisi de "
       "olmazsa acik hata", p0_usb and p0_wifi and "p0" in iki_red and "ag yok" in iki_red,
       f"usb={p0_usb} wifi={p0_wifi} {iki_red!r}")

    # Kopru + SecmeliKart: WiFi'den gelen satirlar tarayiciya USB'dekiyle AYNI bicimde; durum arsive girmez
    usb2, wifi2 = _SahteYukari("seri:COM9@115200"), _SahteYukari("wifi:olcum.local (cihaz 2)")
    wifi2.satirlar = list(ORNEK)
    k2 = KW.SecmeliKart(usb2, wifi2)
    kop = kopru_mod.Kopru(k2, gec_dizin / "arsiv_4b")
    s = _kos(kop)
    taban = f"http://127.0.0.1:{s.server_address[1]}"
    sonuc = {}
    # beklenen: 1 gecis durum satiri + ORNEK[2:] (baglanti acilinca suzgec penceresi ilk 2 satiri atar)
    t = threading.Thread(target=lambda: sonuc.update(v=akis_oku(taban + "/akis", len(ORNEK) - 1)),
                         daemon=True)
    t.start()
    _son = time.monotonic() + 5
    while not kop.aboneler and time.monotonic() < _son:
        time.sleep(0.01)
    threading.Thread(target=kop.dongu, daemon=True).start()
    t.join(10)
    kop.calisiyor = False
    time.sleep(0.3)
    s.shutdown()
    kop.arsiv.kapat()
    gelen = sonuc.get("v", ([], None))[0]
    olcum = [x for x in gelen if not x.startswith(("* kopru", "! kopru"))]
    ars = list(kop.arsiv.ham_satirlar())
    # baglanti numarasi artti -> suzgec penceresi ilk 2 satiri atar (USB ile ayni kural)
    ok("4B: WiFi yukari-akisindan gelen satirlar tarayiciya USB'dekiyle AYNI bicimde (bayt-seffaf "
       "`data:`) gider; gecis durum satiri akista, arsivde YOK",
       olcum == ORNEK[2:] and any(x.startswith("* kopru:") for x in gelen)
       and ars == ORNEK[2:] and not any("kopru" in x for x in ars),
       f"olcum={olcum} ars={ars[:3]}")

    # pc.py: yukari-akis kurulumu
    eski = os.environ.pop("OLCUM_KART_HOST", None)
    try:
        a1 = pc.yukari_akis_kur([])
        a2 = pc.yukari_akis_kur(["--kart-host", "192.168.4.1", "--cihaz", "x.json", "--port", "com7"])
        a3 = pc.yukari_akis_kur(["--wifi-yok"])
        a5 = pc.yukari_akis_kur(["--usb-yok", "--kart-host", "192.168.4.1"])
        try:
            pc.yukari_akis_kur(["--usb-yok", "--wifi-yok"])
            ikisi = "kabul"
        except RuntimeError:
            ikisi = "ret"
        os.environ["OLCUM_KART_HOST"] = "10.0.0.9"
        a4 = pc.yukari_akis_kur([])
    finally:
        if eski is None:
            os.environ.pop("OLCUM_KART_HOST", None)
        else:
            os.environ["OLCUM_KART_HOST"] = eski
    ok("4B: pc.py yukari-akisi USB (OtoSeriKart) + WiFi (WifiKart, olcum.local) kurar; --kart-host / "
       "OLCUM_KART_HOST adresi, --cihaz dosyayi verir; --wifi-yok yalniz USB (4A davranisi)",
       isinstance(a1, KW.SecmeliKart) and isinstance(a1.usb, kart_baglanti.OtoSeriKart)
       and isinstance(a1.wifi, KW.WifiKart) and a1.wifi.host == "olcum.local"
       and a2.wifi.host == "192.168.4.1" and a2.wifi.cihaz_dosyasi == Path("x.json")
       and a2.usb.elle_port == "COM7"
       and isinstance(a3, kart_baglanti.OtoSeriKart) and a4.wifi.host == "10.0.0.9",
       f"{type(a1).__name__} {getattr(getattr(a1, 'wifi', None), 'host', None)} {type(a3).__name__}")
    ok("4B: pc.py --usb-yok YALNIZ WiFi kurar (COM portu hic acilmaz — kart USB'den beslenirken WiFi "
       "yolu sinanir, tezgah araclari portu kullanabilir); --usb-yok ile --wifi-yok birlikte REDDEDILIR",
       isinstance(a5, KW.WifiKart) and a5.host == "192.168.4.1" and ikisi == "ret",
       f"{type(a5).__name__} {ikisi}")


def pc_4c_sina(gec_dizin: Path) -> None:
    """4C (PC5/PC9/PC12): arka plan esitlemesinin pc.py baglantisi, /esitleme/durum, .satir gocu.

    Esitleme dongusunun kendisi (sahte karta karsi, imzali) B72.A'da sinaniyor."""
    print("\n--- 4C. Arka plan disk arsivi: pc.py baglantisi, /esitleme/durum, .satir gocu ---")
    import arka_esitle as AE
    import kart_wifi as KW
    import pc
    import pc_ayar

    def _durum_al(url):
        kod, govde = _guvenli_istek(url)
        return kod, govde.decode("utf-8", "replace")
    ayar = pc_ayar.veri_dizini() / pc_ayar.AYAR
    if ayar.exists():
        ayar.unlink()
    usb, wifi = _SahteYukari("seri:COM9@115200"), KW.WifiKart("127.0.0.1:9")
    sec = KW.SecmeliKart(usb, wifi)
    kop = kopru_mod.Kopru(sec, gec_dizin / "arsiv_4c")
    sus: list[str] = []
    e1 = pc.esitleme_kur([], sec, kop, yazdir=sus.append)
    usb.baglanti_no = 7
    sec._sec("usb")
    ok("4C (PC5/PC9): varsayilan esitleme kartin WiFi kolunu kullanir, ONAY verir, 120 s araliklidir, "
       "arsiv %LOCALAPPDATA%\\olcum-karti\\arsiv (OLCUM_PC_DIZIN ile), kopruye bagli; tetik yukari-akisin "
       "baglanti numarasi, USB etkinligi SecmeliKart'tan",
       e1 is not None and e1.wifi is wifi and e1.onay is True and e1.aralik == AE.ARALIK_SN == 120.0
       and e1.arsiv_kok == pc_ayar.veri_dizini() / "arsiv" and kop.esitleme is e1
       and e1._tetik() == sec.baglanti_no and e1._usb_etkin() is True and e1._is is None,
       f"onay={getattr(e1, 'onay', None)} aralik={getattr(e1, 'aralik', None)}")
    e2 = pc.esitleme_kur(["--onaysiz"], sec, kop, yazdir=sus.append)
    sus.clear()
    e3 = pc.esitleme_kur(["--esitleme-aralik", "5"], sec, kop, yazdir=sus.append)
    e3b = pc.esitleme_kur(["--esitleme-aralik", "300"], sec, kop, yazdir=sus.append)
    ok("4C (PC9): --onaysiz onayi KAPATIR; --esitleme-aralik verilir ama en az 30 s (daha kisasi "
       "soylenerek 30'a cekilir — kart dovulmez)",
       e2.onay is False and e3.aralik == AE.ARALIK_EN_AZ == 30.0 and e3b.aralik == 300.0
       and any("cok kisa" in x for x in sus), f"{e2.onay} {e3.aralik} {e3b.aralik} {sus[-1:]}")
    ayar.parent.mkdir(parents=True, exist_ok=True)
    ayar.write_text('{"esitleme_onay": false, "esitleme_aralik_s": 240}', encoding="utf-8")
    e4 = pc.esitleme_kur([], sec, kop, yazdir=sus.append)
    sus.clear()
    ayar.write_text("{bozuk", encoding="utf-8")
    e5 = pc.esitleme_kur([], sec, kop, yazdir=sus.append)
    ayar.write_text('{"esitleme_onay": "hayir"}', encoding="utf-8")
    e5b = pc.esitleme_kur([], sec, kop, yazdir=sus.append)
    ayar.write_text('{"esitleme_onay": true}', encoding="utf-8")
    e5c = pc.esitleme_kur(["--onaysiz"], sec, kop, yazdir=sus.append)
    ayar.unlink()
    ok("4C (PC9): ayar.json `esitleme_onay: false` / `esitleme_aralik_s` uygulanir; dosya bozuk ya da "
       "deger true/false degilse GUVENLI tarafa (ONAYSIZ) dusulur ve soylenir; --onaysiz ayari ezer",
       e4.onay is False and e4.aralik == 240.0 and e5.onay is False and e5b.onay is False
       and e5c.onay is False and any("okunamadi" in x and "ONAYSIZ" in x for x in sus),
       f"{e4.onay}/{e4.aralik} {e5.onay} {e5b.onay} {sus[:1]}")
    sus.clear()
    kop_y = kopru_mod.Kopru(usb, gec_dizin / "arsiv_4c_y")
    e6 = pc.esitleme_kur(["--esitleme-yok"], sec, kop, yazdir=sus.append)
    e7 = pc.esitleme_kur([], usb, kop_y, yazdir=sus.append)
    e8 = pc.esitleme_kur([], wifi, kopru_mod.Kopru(wifi, gec_dizin / "arsiv_4c_w"), yazdir=sus.append)
    ok("4C (PC6): --esitleme-yok ve WiFi'siz yukari-akis (--wifi-yok: kayit verisinin seri yolu yok, "
       "4C-2 ertelendi) esitleme KURMAZ ve sebebini soyler; yalniz WiFi (--usb-yok) kurar",
       e6 is None and e7 is None and kop_y.esitleme is None and "4C-2" in (kop_y.esitleme_neden or "")
       and e8 is not None and e8.wifi is wifi and any("KAPALI" in x for x in sus),
       f"{e6} {e7} {kop_y.esitleme_neden!r}")

    # /esitleme/durum: yalniz bu bilgisayar, JSON, mutlak yol yok
    kop.esitleme = e1
    s1 = _kos(kop)
    t1 = f"http://127.0.0.1:{s1.server_address[1]}"
    kod_d, govde_d = _durum_al(t1 + "/esitleme/durum")
    s1.shutdown()
    s1.server_close()
    s2 = _kos(kop, _LanIsleyici)
    kod_lan, _ = _durum_al(f"http://127.0.0.1:{s2.server_address[1]}/esitleme/durum")
    s2.shutdown()
    s2.server_close()
    s3 = _kos(kop_y)
    kod_y, govde_y = _durum_al(f"http://127.0.0.1:{s3.server_address[1]}/esitleme/durum")
    s3.shutdown()
    s3.server_close()
    try:
        dj, dy = json.loads(govde_d), json.loads(govde_y)
    except ValueError:
        dj, dy = {}, {}
    ok("4C: GET /esitleme/durum yalniz BU BILGISAYARDAN (yerel ag 403) — etkin / onay / aralik / son "
       "sonuc JSON'u; esitleme yoksa etkin:false + sebep; yanitta mutlak yol yok",
       kod_d == 200 and dj.get("etkin") is True and dj.get("onay") is True and dj.get("sonuc") == "bekliyor"
       and dj.get("aralik_s") == 120.0 and kod_lan == 403 and kod_y == 200 and dy.get("etkin") is False
       and "4C-2" in dy.get("neden", "") and str(gec_dizin) not in govde_d + govde_y
       and str(pc_ayar.veri_dizini()) not in govde_d,
       f"{kod_d} {govde_d[:80]} lan={kod_lan} yok={govde_y[:60]}")

    # .satir gocu: BIR KEZ, KOPYA, yalniz yeni dizin bossa
    eski, yeni = gec_dizin / "agac_arsiv", gec_dizin / "satir_yeni"
    eski.mkdir()
    (eski / "2026-09-11.satir").write_text("1000\tD 1.0\n", encoding="utf-8")
    (eski / "2026-09-12.satir").write_text("2000\tD 2.0\n", encoding="utf-8")
    (eski / "not.txt").write_text("x", encoding="utf-8")
    g1 = pc.satir_goc(eski, yeni)
    g2 = pc.satir_goc(eski, yeni)
    (eski / "2026-10-01.satir").write_text("3000\tD 3.0\n", encoding="utf-8")
    g3 = pc.satir_goc(eski, yeni)
    bos_eski = gec_dizin / "agac_bos"
    g4 = pc.satir_goc(bos_eski, gec_dizin / "satir_yeni2")
    ok("4C (PC12): eski .satir arsivi (calisan agacin kopru/arsiv) yeni dizin BOSSA bir kez KOPYALANIR "
       "(tasinmaz, silinmez); sonra bir daha dokunulmaz; .satir disi dosya gitmez; varsayilan yer "
       "%LOCALAPPDATA%\\olcum-karti\\satir",
       g1 == ["2026-09-11.satir", "2026-09-12.satir"] and g2 == [] and g3 == [] and g4 == []
       and all((eski / a).exists() for a in g1)
       and all((yeni / a).read_bytes() == (eski / a).read_bytes() for a in g1)
       and not (yeni / "not.txt").exists() and not (yeni / "2026-10-01.satir").exists()
       and pc_ayar.satir_dizini() == pc_ayar.veri_dizini() / "satir"
       and pc.ESKI_SATIR_DIZINI == KOK / "kopru" / "arsiv",
       f"{g1} {g2} {g3}")

    # pc.calistir: .satir gunlugu yeni yerde, esitleme baslar ve /esitleme/durum'dan gorunur
    hp = _bos_port()
    yazilan: list[str] = []
    sonuc = {}
    th = threading.Thread(target=lambda: sonuc.update(rc=pc.calistir(
        ["--usb-yok", "--http-port", str(hp), "--tarayici-acma"], tarayici_ac=lambda u: None,
        yazdir=yazilan.append)), daemon=True)
    th.start()
    son = time.monotonic() + 8
    while not pc.zaten_calisiyor(hp) and time.monotonic() < son:
        time.sleep(0.05)
    kod_c, govde_c = _durum_al(f"http://127.0.0.1:{hp}/esitleme/durum")
    son = time.monotonic() + 6
    while '"son_deneme": null' in govde_c and time.monotonic() < son:
        time.sleep(0.1)
        kod_c, govde_c = _durum_al(f"http://127.0.0.1:{hp}/esitleme/durum")
    durdu, _ = pc.durdur(hp)
    th.join(8)
    try:
        dc = json.loads(govde_c)
    except ValueError:
        dc = {}
    ok("4C: pc.py (--usb-yok) esitlemeyi KURAR ve BASLATIR (ilk tur hemen; kart yoksa hata sayilir), "
       "durdurulunca iplik biter; .satir gunlugu %LOCALAPPDATA%\\olcum-karti\\satir, kayit arsivi "
       "...\\arsiv konsolda soylenir",
       kod_c == 200 and dc.get("etkin") is True and dc.get("son_deneme") and dc.get("sonuc") == "hata"
       and durdu and not th.is_alive() and sonuc.get("rc") == 0
       and any("Satir gunlugu" in x and str(pc_ayar.satir_dizini()) in x for x in yazilan)
       and any("Kayit arsivi" in x and str(pc_ayar.arsiv_dizini()) in x and "ONAY" in x for x in yazilan),
       f"{kod_c} {govde_c[:90]} rc={sonuc.get('rc')}")


def _akis_baytlari(oturum_say: int, sira0: int = 0) -> bytes:
    """4D: gercek kayit bicimiyle (kopru/kayit_bicim.py paketleyicileri) bir akisin baytlari:
    her oturum BASLA + 4 NOKTA kaydi (24 nokta) + BITIR."""
    import struct
    import kayit_bicim as KB
    f = lambda x: struct.unpack("<f", struct.pack("<f", x))[0]          # noqa: E731
    kn = lambda n: KB.Kanal(f(n), f(4.096), f(1.0), 12, 0.0)             # noqa: E731
    kal = KB.Kalibrasyon(kn(21.0), kn(201.0), 5, f(0.256), f(0.1), f(1.0), 0.0, (0.0, 0.0))
    sira, cikti = sira0, []

    def ekle(tur, ot, yuk):
        nonlocal sira
        sira += 1
        cikti.append(KB.kayit_paketle(tur, sira, ot, yuk))
        return sira
    for k in range(oturum_say):
        ot = ekle(KB.T_BASLA, sira + 1, KB.basla_paketle(
            KB.Basla(1, 1, 200, 1790000000 + k * 3600, 1000, 1, "A3-4D", kal, kal_no=1)))
        for j in range(0, 24, 6):
            ns = [KB.Nokta(200 * (j + i + 1), 40, 0, f(12.0 + i), 1000, 1100, f(0.5), 10, 20, f(6.0),
                           f(5.9), f(6.1)) for i in range(6)]
            ekle(KB.T_NOKTA, ot, struct.pack("<I", j) + b"".join(KB.nokta_paketle(p) for p in ns))
        ekle(KB.T_BITIR, ot, struct.pack("<IB3x", 24, 1))
    return b"".join(cikti)


def _arsiv_yaz(kok: Path, kart: str, akis: int, veri: bytes, kuyruk: bytes = b"", kal: bool = True) -> Path:
    """Esitleyicinin yazdigi dizin bicimi: kayitlar.kyt (+ kalici onekin otesinde `kuyruk`),
    durum.json (bayt = kalici onek), kalibrasyon.json."""
    import struct
    d = kok / kart / f"akis-{akis}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "kayitlar.kyt").write_bytes(veri + kuyruk)
    son = max(struct.unpack_from("<I", veri, a + 4)[0] for a in _kayit_baslari(veri)) if veri else 0
    (d / "durum.json").write_text(json.dumps({"son_sira": son, "bayt": len(veri), "onaylanan": 0,
                                              "kimlik": akis}), encoding="utf-8")
    if kal:
        (d / "kalibrasyon.json").write_text(json.dumps(
            {"adet": 1, "etkin": 1, "azami": 40, "kayitlar": [{"no": 1, "unix": 1790000000, "not": "pc"}]},
            indent=1), encoding="utf-8")
    return d


def _kayit_baslari(veri: bytes) -> list[int]:
    import kayit_bicim as KB
    a, cikti = 0, []
    while a + 16 <= len(veri):
        cikti.append(a)
        a += KB.toplam_bayt(int.from_bytes(veri[a + 2:a + 4], "little"))
    return cikti


def _dokum(kok: Path) -> dict:
    return {str(p.relative_to(kok)): (p.stat().st_size, p.stat().st_mtime_ns, p.read_bytes())
            for p in sorted(kok.rglob("*")) if p.is_file()}


def pc_4d_sina(gec_dizin: Path) -> None:
    """4D (PC10/PC11): koprunun PC arsivini SALT OKUMA sunan uclari (/arsiv/liste, /arsiv/veri,
    /arsiv/kal) ve kartin /pil, /kal/liste, /kunye.json uclarinin IMZALI vekili.

    Kart: B72'nin sahte karti (test_kayit_esp._SahteKart — imza dogrulayicisi BAGIMSIZ, imza.py'yi
    kullanmaz). Arsiv: gercek kayit bicimi, gecici OLCUM_PC_DIZIN altinda."""
    print("\n--- 4D. Panel PC'de: PC arsivi (salt okuma) + kart uclarinin imzali vekili ---")
    import struct
    import imza as IM
    import kart_wifi as KW
    import kayit_bicim as KB
    import pc_ayar
    import vekil as VK
    ortam = {a: os.environ.get(a) for a in ("OLCUM_PC_DIZIN", "OLCUM_CIHAZ_DIZIN")}
    import test_kayit_esp as T                       # B72 sahte karti (ice aktarma ortami yeniden yonlendirir)
    for a, v in ortam.items():
        if v is not None:
            os.environ[a] = v

    kok = pc_ayar.arsiv_dizini()
    KART = "0a1b2c3d4e5f6a7b"          # harfli: buyuk harf denemesi gercekten farkli olsun
    v1 = _akis_baytlari(3, 100)
    v2 = _akis_baytlari(1, 0)
    kuyruk = KB.kayit_paketle(KB.T_NOKTA, 999, 7, b"\x00" * 40)[:30]      # cokme kuyrugu (kalici degil)
    d2 = _arsiv_yaz(kok, KART, 77, v2, kal=False)
    os.utime(d2 / "kayitlar.kyt", (time.time() - 3600, time.time() - 3600))
    d1 = _arsiv_yaz(kok, KART, 3995957410, v1, kuyruk)
    disari = gec_dizin / "arsiv_disi"
    _arsiv_yaz(disari, "aaaaaaaaaaaaaaaa", 5, _akis_baytlari(1, 0))
    baglanti = None
    if sys.platform == "win32":
        import _winapi
        try:
            _winapi.CreateJunction(str(disari / "aaaaaaaaaaaaaaaa"), str(kok / "aaaaaaaaaaaaaaaa"))
            baglanti = "junction"
        except OSError:
            baglanti = None
    if baglanti is None:
        try:
            (kok / "aaaaaaaaaaaaaaaa").symlink_to(disari / "aaaaaaaaaaaaaaaa", target_is_directory=True)
            baglanti = "symlink"
        except OSError:
            baglanti = None
    once = _dokum(kok)

    kart = T._SahteKart([])
    kart_sun, kart_taban = T._sunucu(kart)
    cdiz = gec_dizin / "cihaz_4d"
    IM.esles(kart_taban, "kopru-4d", kart.parola, dizin=cdiz)
    kart.imza_zorunlu = True
    kart.kal_liste = {"adet": 2, "etkin": 2, "azami": 40, "kayitlar": [{"no": 1}, {"no": 2}]}
    PIL = b"durum=CALISIYOR\nsira=9\nkalan=0\n--\n1000,12.0,0.5\n"
    KUNYE = b'{"surum":"0123456789ab","dosya":30,"icerik_bayt":400000}'
    kart.ek_get = {"/pil": (200, "text/plain; charset=utf-8", PIL),
                   "/kunye.json": (200, "application/json", KUNYE)}
    usb = _SahteYukari("seri:COM9@115200")
    wifi = KW.WifiKart(kart_taban, dizin=cdiz)
    sec = KW.SecmeliKart(usb, wifi)
    kop = kopru_mod.Kopru(sec, gec_dizin / "satir_4d")
    s = _kos(kop)
    taban = f"http://127.0.0.1:{s.server_address[1]}"
    s_lan = _kos(kop, _LanIsleyici)
    taban_lan = f"http://127.0.0.1:{s_lan.server_address[1]}"
    govdeler: list[bytes] = []

    def al(url, basliklar=None, yontem=None, veri=None):
        kod, g, b = None, b"", {}
        try:
            kod, g, b = istek_bas(url, veri, basliklar, yontem, 15)
        except Exception as e:                              # noqa: BLE001
            g = str(e).encode("utf-8", "replace")
        govdeler.append(g)
        return kod, g, {k.lower(): v for k, v in b.items()}

    try:
        # ── PC10: liste ──────────────────────────────────────────────
        kod, g, _ = al(taban + "/arsiv/liste")
        try:
            liste = json.loads(g)["arsivler"]
        except (ValueError, KeyError, TypeError):
            liste = []
        py1 = KB.oturumlari_kur(KB.akis_onek(v1)[0])
        a1 = liste[0] if liste else {}
        ok("4D (PC10): GET /arsiv/liste kart/akis basina arsivleri EN YENI ONCE verir: boy = durum.json'un "
           "KALICI oneki (dosyanin cokme kuyrugu degil), durum, kalibrasyon kopyasi var mi, oturum listesi "
           "(Python kayit_bicim'in kendi cozumuyle ayni), goreli ad; arsiv kokunun DISINA giden bag LISTELENMEZ",
           kod == 200 and [(a["kart"], a["akis"]) for a in liste] == [(KART, 3995957410), (KART, 77)]
           and a1.get("bayt") == len(v1) and a1.get("dosya_bayt") == len(v1) + len(kuyruk)
           and a1.get("durum", {}).get("kimlik") == 3995957410 and a1.get("kal") is True
           and liste[1].get("kal") is False and a1.get("oturum") == len(py1) == 3
           and [o["id"] for o in a1.get("oturumlar", [])] == sorted(py1)
           and all(o["nokta"] == 24 and o["bitti"] and o["tur"] == 1 for o in a1["oturumlar"])
           and a1.get("ad") == f"arsiv/{KART}/akis-3995957410",
           f"{kod} {[(a.get('kart'), a.get('akis'), a.get('bayt')) for a in liste]} bag={baglanti}")

        # ── PC10: bayt araliklari ─────────────────────────────────────
        q = f"kart={KART}&akis=3995957410"
        parcalar, ofset, boylar = [], 0, set()
        for _ in range(20):
            kod_v, g_v, b_v = al(f"{taban}/arsiv/veri?{q}&ofset={ofset}&bayt=1000")
            if kod_v != 200:
                break
            boylar.add(b_v.get("x-arsiv-boy"))
            parcalar.append(g_v)
            ofset += len(g_v)
            if not g_v or ofset >= len(v1):
                break
        kod_son, g_son, _ = al(f"{taban}/arsiv/veri?{q}&ofset={len(v1)}&bayt=1000")
        kod_ust, _, _ = al(f"{taban}/arsiv/veri?{q}&ofset={len(v1) + 1}&bayt=10")
        kod_kal, g_kal, _ = al(f"{taban}/arsiv/kal?{q}")
        kod_kal2, _, _ = al(f"{taban}/arsiv/kal?kart={KART}&akis=77")
        ok("4D (PC10): GET /arsiv/veri parca parca okunan baytlar kayitlar.kyt'nin KALICI onekiyle BAYT BAYT "
           "ayni (X-Arsiv-Boy = durum.json bayt; cokme kuyrugu verilmez, ofset = boy bos 200, otesi 400); "
           "/arsiv/kal kalibrasyon.json'u AYNEN verir, kopyasi yoksa 404",
           b"".join(parcalar) == v1 and boylar == {str(len(v1))} and kod_son == 200 and g_son == b""
           and kod_ust == 400 and kod_kal == 200 and g_kal == (d1 / "kalibrasyon.json").read_bytes()
           and kod_kal2 == 404,
           f"{len(b''.join(parcalar))}/{len(v1)} boy={boylar} son={kod_son} ust={kod_ust} kal={kod_kal}/{kod_kal2}")

        # ── PC10: kati parametre + yol icerme ─────────────────────────
        kotu = {
            "kart buyuk harf": f"/arsiv/veri?kart={KART.upper()}&akis=77&ofset=0&bayt=10",
            "kart 15": f"/arsiv/veri?kart={KART[:15]}&akis=77&ofset=0&bayt=10",
            "kart ..": "/arsiv/veri?kart=..&akis=77&ofset=0&bayt=10",
            "kart %2e%2e": "/arsiv/veri?kart=%2e%2e%2f%2e%2e&akis=77&ofset=0&bayt=10",
            "kart UNC": "/arsiv/veri?kart=%5C%5Csaldirgan%5Cpay&akis=77&ofset=0&bayt=10",
            "kart mutlak": "/arsiv/veri?kart=C%3A%2FWindows&akis=77&ofset=0&bayt=10",
            "akis 007": f"/arsiv/veri?kart={KART}&akis=077&ofset=0&bayt=10",
            "akis eksi": f"/arsiv/veri?kart={KART}&akis=-1&ofset=0&bayt=10",
            "akis bos": f"/arsiv/veri?kart={KART}&akis=&ofset=0&bayt=10",
            "ofset harf": f"/arsiv/veri?kart={KART}&akis=77&ofset=1e3&bayt=10",
            "bayt 0": f"/arsiv/veri?kart={KART}&akis=77&ofset=0&bayt=0",
            "bayt dev": f"/arsiv/veri?kart={KART}&akis=77&ofset=0&bayt={VK.VERI_AZAMI + 1}",
            "bayt cok dev": f"/arsiv/veri?kart={KART}&akis=77&ofset=0&bayt=99999999999999999999",
            "bilinmeyen": f"/arsiv/veri?kart={KART}&akis=77&ofset=0&bayt=10&dosya=durum.json",
            "tekrar": f"/arsiv/veri?kart={KART}&akis=77&akis=78&ofset=0&bayt=10",
            "eksik": f"/arsiv/veri?kart={KART}&akis=77&bayt=10",
            "liste parametre": "/arsiv/liste?kok=C%3A%2F",
        }
        if baglanti:
            kotu["arsiv disina bag"] = "/arsiv/veri?kart=aaaaaaaaaaaaaaaa&akis=5&ofset=0&bayt=10"
        kodlar = {ad: al(taban + y)[0] for ad, y in kotu.items()}
        kod_yok, _, _ = al(f"{taban}/arsiv/veri?kart={KART}&akis=78&ofset=0&bayt=10")
        ok("4D (PC10): /arsiv/* parametreleri KATI — kart 16 kucuk onaltilik, akis/ofset/bayt bastaki "
           f"sifirsiz ondalik, bayt <= {VK.VERI_AZAMI}; yol gecisi / UNC / mutlak yol / bilinmeyen / tekrar / "
           f"eksik parametre 400; arsiv kokunun disina giden bag ({baglanti or 'kurulamadi'}) 400; olmayan akis 404",
           all(k == 400 for k in kodlar.values()) and kod_yok == 404,
           " ".join(f"{a}={k}" for a, k in kodlar.items() if k != 400) + f" yok={kod_yok}")

        # ── kapilar: yerel ag, capraz koken ──────────────────────────
        k_lan = [al(taban_lan + y)[0] for y in ("/arsiv/liste", f"/arsiv/veri?{q}&ofset=0&bayt=10",
                                                 f"/arsiv/kal?{q}", "/pil", "/kal/liste", "/kunye.json")]
        k_capraz = [al(taban + "/arsiv/liste", {"Sec-Fetch-Site": "cross-site"})[0],
                    al(taban + "/arsiv/liste", {"Sec-Fetch-Site": "same-site"})[0],
                    al(f"{taban}/arsiv/veri?{q}&ofset=0&bayt=10",
                       {"Origin": "http://kotu.example", "Host": s.server_address[0] + ":" + str(s.server_address[1])})[0],
                    al(taban + "/kal/liste", {"Sec-Fetch-Site": "cross-site"})[0]]
        k_ayni = al(taban + "/arsiv/liste", {"Sec-Fetch-Site": "same-origin"})[0]
        ok("4D (PC10/PC11): /arsiv/* ve vekil uclari YALNIZ bu bilgisayardan (yerel ag 403) ve YALNIZ ayni "
           "kokenden (baska site / baska port `<img>`/fetch'i 403 — 4A CSRF kapisi); panelin kendisi 200",
           k_lan == [403] * 6 and k_capraz == [403] * 4 and k_ayni == 200, f"lan={k_lan} capraz={k_capraz} ayni={k_ayni}")

        # ── yazma yok ────────────────────────────────────────────────
        k_yaz = [al(f"{taban}/arsiv/veri?{q}&ofset=0&bayt=10", yontem=y, veri=b"x")[0]
                 for y in ("POST", "PUT", "DELETE")]
        k_yaz.append(al(taban + "/arsiv/liste", yontem="POST", veri=b"{}")[0])
        k_yaz.append(al(taban + "/pil", yontem="POST", veri=b"p1")[0])
        sonra = _dokum(kok)
        ok("4D (PC10): arsiv ve vekil yollari YAZMA kabul etmez (POST/PUT/DELETE 2xx degil; vekil POST'u karta "
           "gitmez) ve butun istekler bittiginde arsiv dizini BAYT BAYT ve mtime'iyla ayni — tek yazar Python",
           all(k is not None and not 200 <= k < 300 for k in k_yaz) and sonra == once
           and not any(y.startswith("POST /pil") for y in kart.istekler),
           f"{k_yaz} degisen={sorted(set(sonra) ^ set(once))[:3]}")

        # ── /durum ───────────────────────────────────────────────────
        dj = json.loads(al(taban + "/durum")[1] or b"{}")
        dl = json.loads(al(taban_lan + "/durum")[1] or b"{}")
        kop_usb = kopru_mod.Kopru(kart_baglanti.KayitKart([]), gec_dizin / "satir_4d_u")
        s_u = _kos(kop_usb)
        du = json.loads(al(f"http://127.0.0.1:{s_u.server_address[1]}/durum")[1] or b"{}")
        ok("4D: /durum bu istemcinin PC arsivini okuyup okuyamayacagini (`pc_arsiv`) ve kartin uclarinin "
           "WiFi vekilinden gelip gelemeyecegini (`vekil`) soyler — yerel agdan ikisi de false, WiFi'siz "
           "yukari-akista vekil false (panel bundan karar verir)",
           dj.get("pc_arsiv") is True and dj.get("vekil") is True and dl.get("pc_arsiv") is False
           and dl.get("vekil") is False and du.get("pc_arsiv") is True and du.get("vekil") is False
           and "kart" in dj and "skop_arsiv" in dj, f"{dj} {dl} {du}")

        # ── PC11: imzali vekil ───────────────────────────────────────
        kart.istekler.clear()
        i401 = kart.ret_401
        kod_p, g_p, b_p = al(taban + "/pil?sira=9", {"X-Cihaz": "7", "X-Sayac": "1", "X-Imza": "00" * 32})
        kod_k, g_k, b_k = al(taban + "/kal/liste")
        kod_n, g_n, b_n = al(taban + "/kunye.json")
        giden = list(kart.istekler)
        cihaz_n = str(IM.Cihaz.yukle(next(cdiz.glob("*.json"))).n)
        imzali = [x for x in giden if x.startswith(("GET /pil", "GET /kal/liste", "GET /kunye.json"))]
        ok("4D (PC11): /pil?sira, /kal/liste, /kunye.json karta kopru cihaziyla IMZALI gider (kartin bagimsiz "
           "dogrulayicisi kabul eder, imza zorunluyken); panelin yolladigi imza basliklari TASINMAZ; kartin "
           "yaniti AYNEN doner (X-Kopru-Vekil: kart)",
           (kod_p, kod_k, kod_n) == (200, 200, 200) and g_p == PIL and g_n == KUNYE
           and json.loads(g_k) == kart.kal_liste and kart.ret_401 == i401 and len(imzali) == 3
           and all(f"'x-cihaz': '{cihaz_n}'" in x.lower() and "'x-imza'" in x.lower() for x in imzali)
           and any(x.startswith("GET /pil?sira=9 ") for x in imzali)
           and {b_p.get("x-kopru-vekil"), b_k.get("x-kopru-vekil"), b_n.get("x-kopru-vekil")} == {"kart"},
           f"{kod_p} {kod_k} {kod_n} 401={kart.ret_401 - i401} giden={[x[:40] for x in giden]}")
        k_izin = [al(taban + y)[0] for y in ("/pil?sira=09", "/pil?sira=1&_c=1&_s=2&_i=ab", "/pil?x=1",
                                             "/kal/liste?sira=1", "/kunye.json?a=b")]
        k_yok = [al(taban + y)[0] for y in ("/eslestir/bilgi", "/kayit/liste", "/komut")]
        ok("4D (PC11): vekil BEYAZ LISTE — yalniz /pil (sira), /kal/liste, /kunye.json; izinsiz parametre ve "
           "`_c _s _i` 400; /eslestir/* ve /kayit/* VEKILDE DEGIL (kopru 404 = panelin imzasiz yolu, EU9)",
           k_izin == [400] * 5 and all(k == 404 for k in k_yok[:2]) and k_yok[2] != 200,
           f"izin={k_izin} yok={k_yok}")

        # ayni Cihaz nesnesi + sayac kilidi (esitleme / akis ile): donuk saatte bile tekrar sayac yok
        asil_time = IM.time
        IM.time = T._DonukSaat(time.time())
        try:
            i401 = kart.ret_401
            cihaz, _, _ = wifi.dogrula()
            sonuc_s = []
            for _ in range(4):
                sonuc_s.append(al(taban + "/kunye.json")[0])
                with wifi.imzali_ac(cihaz, "GET", "/kal/liste", []) as y:   # arka plan esitlemesinin yolu
                    y.read()
        finally:
            IM.time = asil_time
        ok("4D (PC11 + 4C-2): vekil canli akis / esitlemeyle AYNI Cihaz nesnesini ve sayac kilidini kullanir — "
           "ayni milisaniyede (donuk saat) art arda vekil + esitleme istekleri: kart hicbirini 401 ile reddetmez",
           sonuc_s == [200] * 4 and kart.ret_401 == i401, f"{sonuc_s} 401={kart.ret_401 - i401}")

        # p0: vekilden gecmez, yavas bir vekil istegi (sayac kilidi tutulurken) onu BEKLETMEZ
        kart.ek_bekle["/pil"] = 1.5
        kart.imza_zorunlu = False      # gercek kart p0'i imza zorunluyken de serbest birakir (komut_serbest)
        kart.komut_imzali.clear()
        sonuc_p = {}
        t_v = threading.Thread(target=lambda: sonuc_p.update(v=al(taban + "/pil?sira=1")[0]), daemon=True)
        t_v.start()
        time.sleep(0.3)
        t0 = time.monotonic()
        kod_p0 = al(taban + "/komut", {"X-Olcum": "1"}, "POST", b"p0")[0]
        sure_p0 = time.monotonic() - t0
        t_v.join(10)
        kart.ek_bekle.clear()
        ok("4D (O7): p0 (DURDUR) vekilden GECMEZ — kopru /komut'tan karta IMZASIZ gider ve sayac kilidini "
           "tutan YAVAS bir vekil istegi (kart 1.5 s'de yanitliyor) suruyorken bile beklemeden ulasir",
           kod_p0 == 204 and ("p0", False) in kart.komut_imzali and sure_p0 < 0.8 and sonuc_p.get("v") == 200,
           f"p0={kod_p0} {sure_p0:.2f} s {kart.komut_imzali[-2:]} vekil={sonuc_p.get('v')}")

        # hatalar: acik JSON, mutlak yol yok
        kart.ek_get.pop("/kunye.json")
        kod_404, g_404, b_404 = al(taban + "/kunye.json")
        kart.cihazlar.clear()                                       # kart cihazi unuttu -> 401
        VK._durum(kop, "_kart_vekili", VK.KartVekili).unut()
        kod_401, g_401, b_401 = al(taban + "/kal/liste")
        bos = gec_dizin / "cihaz_4d_bos"
        wifi_bos = KW.WifiKart(kart_taban, dizin=bos)
        kop_bos = kopru_mod.Kopru(KW.SecmeliKart(_SahteYukari("seri:COM9@115200"), wifi_bos), gec_dizin / "s4b")
        s_b = _kos(kop_bos)
        kod_es, g_es, _ = al(f"http://127.0.0.1:{s_b.server_address[1]}/pil")
        kop_x = kopru_mod.Kopru(KW.WifiKart("127.0.0.1:9", dizin=cdiz), gec_dizin / "s4x")
        s_x = _kos(kop_x)
        kod_er, g_er, _ = al(f"http://127.0.0.1:{s_x.server_address[1]}/kunye.json")
        kod_wy, g_wy, _ = al(f"http://127.0.0.1:{s_u.server_address[1]}/kal/liste")

        def neden(g):
            try:
                return json.loads(g).get("vekil")
            except (ValueError, AttributeError):
                return None
        ok("4D (PC11): vekil hatasi ACIK JSON — kartin 404'u aynen gecer; kart imzayi reddederse (cihaz "
           "silinmis) 502 `imza` (panel 401'i 'bu tarayici eslesmemis' sanmasin); bu PC karta eslesmemisse "
           "`dogrulanamadi`, kart erisilemezse `dogrulanamadi`, WiFi yukari-akisi yoksa `wifi_yok`",
           kod_404 == 404 and b_404.get("x-kopru-vekil") == "kart" and kod_401 == 502 and neden(g_401) == "imza"
           and b_401.get("x-kopru-vekil") == "hata" and kod_es == 502 and neden(g_es) == "dogrulanamadi"
           and "ESLESMEMIS" in g_es.decode("utf-8", "replace") and kod_er == 502
           and neden(g_er) == "dogrulanamadi" and kod_wy == 502 and neden(g_wy) == "wifi_yok",
           f"404={kod_404} 401={kod_401}/{neden(g_401)} es={kod_es}/{neden(g_es)} er={kod_er}/{neden(g_er)} "
           f"wy={kod_wy}/{neden(g_wy)}")
        for x in (s_b, s_x):
            x.shutdown()
            x.server_close()
        hepsi = b"\n".join(govdeler).decode("utf-8", "replace")
        yollar = {str(gec_dizin), str(kok), str(cdiz), str(bos), str(Path.home()), str(pc_ayar.veri_dizini())}
        sizan = [y for y in yollar | {json.dumps(x)[1:-1] for x in yollar} if y and y in hepsi]
        import re
        # mutlak Windows kullanici yolu (ham ya da JSON kacisli) ve UNC — desen olarak (gizlilik_dogrula temiz kalsin)
        sizan += [m.group(0) for m in re.finditer(r"[A-Za-z]:(?:\\{1,2}|/)Users|\\{2,}[A-Za-z]", hepsi)]
        ok("4D: /arsiv/* ve vekil yanitlarinin HICBIRINDE mutlak kullanici yolu yok (eslesmemis kartin "
           "mesajindaki cihaz dizini dahil — `vekil.yolsuz`)", not sizan and len(govdeler) > 40, f"{sizan[:3]}")
        s_u.shutdown()
        s_u.server_close()
    finally:
        for x in (s, s_lan):
            x.shutdown()
            x.server_close()
        kart_sun.shutdown()
        kart_sun.server_close()


class _Cikis4E:
    """4E: bildirim cikisi yerine kayit (GERCEK toast YOK)."""
    yol = "sahte"

    def __init__(self):
        self.cagri: list[tuple] = []

    def goster(self, etiket, baslik, metin, sessiz=False):
        self.cagri.append((etiket, metin, sessiz))

    def kapat(self):
        pass


def pc_4e_sina(gec_dizin: Path) -> None:
    """4E (PC13–PC16): bildirim ipliginin pc.py baglantisi, yerel `G` satiri dinleme, /bildirim/durum.

    MQTT ipligi, karar katmani ve Windows bildirim betigi B72.Q16'da (test_bildirim.py) sinaniyor."""
    print("\n--- 4E. MQTT bildirimleri: pc.py baglantisi, yerel satir, /bildirim/durum ---")
    import kart_wifi as KW
    import pc
    import pc_ayar
    import pc_bildirim as PB

    def _durum_al(url):
        kod, govde = _guvenli_istek(url)
        return kod, govde.decode("utf-8", "replace")
    usb, wifi = _SahteYukari("seri:COM9@115200"), KW.WifiKart("127.0.0.1:9")
    sec = KW.SecmeliKart(usb, wifi)
    kop = kopru_mod.Kopru(sec, gec_dizin / "arsiv_4e")
    sus: list[str] = []
    yok = pc.bildirim_kur(["--bildirim-yok"], sec, kop, yazdir=sus.append)
    neden_yok = getattr(kop, "bildirim_neden", None)
    b1 = pc.bildirim_kur([], sec, kop, yazdir=sus.append)
    kop_u = kopru_mod.Kopru(usb, gec_dizin / "arsiv_4e_u")
    b2 = pc.bildirim_kur([], usb, kop_u, yazdir=sus.append, cikis=_Cikis4E())
    ok("4E: pc.bildirim_kur — --bildirim-yok kurmaz (sebep); varsayilan kartin WiFi kolunu kullanir, cikis "
       "Windows bildirimi (sinamada OLCUM_TOAST_YOK: alt surec yok), veri dizini %LOCALAPPDATA%\\olcum-karti; "
       "WiFi'siz (--wifi-yok) yukari-akista da kurulur (onbellekle calisir)",
       yok is None and neden_yok == "--bildirim-yok" and b1 is not None and b1.wifi is wifi
       and kop.bildirim is b1 and b1.mantik.cikis.yol == ("windows" if sys.platform == "win32" else "yok")
       and getattr(b1.mantik.cikis, "sinama", True) and b1.dizin == pc_ayar.veri_dizini() / "bildirim"
       and b2 is not None and b2.wifi is None and any("KAPALI (--bildirim-yok)" in x for x in sus),
       f"{yok} {neden_yok} {b1 and b1.wifi}")

    # yerel satirlar: kartin satir_oku'su sarilir — Kopru.dongu degismeden G gecisi bildirime
    kart = kart_baglanti.KayitKart([_g4e(2, 7), "D 1.0 0.5", _g4e(1, 7)], gecikme=0.0)
    kart.ac()
    kop_k = kopru_mod.Kopru(kart, gec_dizin / "arsiv_4e_k")
    cikis = _Cikis4E()
    pc.bildirim_kur([], kart, kop_k, yazdir=sus.append, cikis=cikis)
    okunan = [kart.satir_oku(1.0) for _ in range(3)]
    ok("4E (PC16): kartin yukari-akis satirlari (Kopru.dongu'nun okudugu) bildirim katmanina da gider — "
       "`G` kayit -> degil gecisi YEREL 'kayit bitti' bildirimi; satirlar akisa AYNEN devam eder",
       okunan == [_g4e(2, 7), "D 1.0 0.5", _g4e(1, 7)]
       and [c[0] for c in cikis.cagri] == ["os-7"] and "Kayıt bitti (oturum 7)" in cikis.cagri[0][1],
       f"{okunan} {cikis.cagri}")
    kart.kapat()

    # /bildirim/durum: yalniz bu bilgisayar, JSON, sir yok
    b1._b = {"uri": "mqtts://gizli-araci.example:8883", "kullanici": "cihaz-sinama-b22", "parola": "sinama-pw-b22",
             "onek": "ab" * 16, "anahtar": bytes(range(32))}
    b1._d["mesaj"] = "! bildirim: gizli-araci.example cihaz-sinama-b22 sinama-pw-b22"
    s1 = _kos(kop)
    kod_d, govde_d = _durum_al(f"http://127.0.0.1:{s1.server_address[1]}/bildirim/durum")
    s1.shutdown()
    s1.server_close()
    s2 = _kos(kop, _LanIsleyici)
    kod_lan, _ = _durum_al(f"http://127.0.0.1:{s2.server_address[1]}/bildirim/durum")
    s2.shutdown()
    s2.server_close()
    kop_y = kopru_mod.Kopru(usb, gec_dizin / "arsiv_4e_y")
    pc.bildirim_kur(["--bildirim-yok"], usb, kop_y, yazdir=sus.append)
    s3 = _kos(kop_y)
    kod_y, govde_y = _durum_al(f"http://127.0.0.1:{s3.server_address[1]}/bildirim/durum")
    s3.shutdown()
    s3.server_close()
    try:
        dj, dy = json.loads(govde_d), json.loads(govde_y)
    except ValueError:
        dj, dy = {}, {}
    sirlar = ["gizli-araci", "cihaz-sinama-b22", "sinama-pw-b22", "ab" * 16, bytes(range(32)).hex()]
    ok("4E: GET /bildirim/durum yalniz BU BILGISAYARDAN (yerel ag 403) — etkin / abone / kart cevrimici / "
       "son olay / ac-kapa ayarlari; kurulmadiysa etkin:false + sebep; araci adresi, kullanici, parola, "
       "konu oneki, anahtar ve mutlak yol YOK",
       kod_d == 200 and dj.get("etkin") is True and dj.get("abone") is False and "kart_cevrimici" in dj
       and set(dj.get("ayar", {})) == set(PB.SINIFLAR) and kod_lan == 403 and kod_y == 200
       and dy.get("etkin") is False and dy.get("neden") == "--bildirim-yok"
       and not [s for s in sirlar if s in govde_d] and str(pc_ayar.veri_dizini()) not in govde_d,
       f"{kod_d} {govde_d[:120]} lan={kod_lan} yok={govde_y[:60]}")

    # pc.calistir: bildirim ipligi kurulur, baslar, /bildirim/durum'dan gorunur, durdurulunca biter
    hp = _bos_port()
    yazilan: list[str] = []
    sonuc = {}
    th = threading.Thread(target=lambda: sonuc.update(rc=pc.calistir(
        ["--usb-yok", "--esitleme-yok", "--http-port", str(hp), "--tarayici-acma"],
        tarayici_ac=lambda u: None, yazdir=yazilan.append)), daemon=True)
    th.start()
    son = time.monotonic() + 8
    while not pc.zaten_calisiyor(hp) and time.monotonic() < son:
        time.sleep(0.05)
    kod_c, govde_c = _durum_al(f"http://127.0.0.1:{hp}/bildirim/durum")
    son = time.monotonic() + 6
    while "dogrulanamadi" not in govde_c and time.monotonic() < son:
        time.sleep(0.1)
        kod_c, govde_c = _durum_al(f"http://127.0.0.1:{hp}/bildirim/durum")
    durdu, _ = pc.durdur(hp)
    th.join(8)
    ok("4E: pc.py bildirim ipligini KURAR ve BASLATIR (kart yoksa 'dogrulanamadi' soylenir), konsolda "
       "'Bildirimler' satiri; durdurulunca surec kapanir",
       kod_c == 200 and '"etkin": true' in govde_c and "dogrulanamadi" in govde_c and durdu
       and not th.is_alive() and sonuc.get("rc") == 0 and any("Bildirimler" in x and "MQTT" in x for x in yazilan),
       f"{kod_c} {govde_c[:100]} rc={sonuc.get('rc')}")


def pc_4h_sina(gec_dizin: Path) -> None:
    """4H: panelin bildirim bolumu icin YAZMA ucu (`POST /bildirim/ayar`), yerel ag reddinin isareti
    (`X-Kopru-Ret: lan`) ve koprunun sundugu kabugun surumu (`/durum` `kabuk`).

    Kararlar tasarim/2026-10-03-alt-proje-4-pc.md "4H uygulama kararlari"."""
    print("\n--- 4H. Bildirim ayari yazma ucu, yerel ag reddi isareti, kabuk surumu ---")
    import pc
    import pc_ayar
    import pc_bildirim as PB

    ayar = pc_ayar.veri_dizini() / pc_ayar.AYAR
    ayar.parent.mkdir(parents=True, exist_ok=True)
    kart = kart_baglanti.KayitKart([], gecikme=0.0)
    kart.ac()
    kop = kopru_mod.Kopru(kart, gec_dizin / "arsiv_4h")
    pc.bildirim_kur(["--bildirim-yok"], kop.kart, kop, yazdir=lambda *_: None)
    s = _kos(kop)
    s_lan = _kos(kop, _LanIsleyici)
    taban = f"http://127.0.0.1:{s.server_address[1]}"
    taban_lan = f"http://127.0.0.1:{s_lan.server_address[1]}"
    JSON_B = {"X-Olcum": "1", "Content-Type": "application/json"}

    def post(govde, basliklar=JSON_B, t=taban):
        veri = govde if isinstance(govde, bytes) else json.dumps(govde).encode("utf-8")
        kod, g, b = _guvenli_istek_bas(t + "/bildirim/ayar", veri, basliklar, "POST")
        return kod, g.decode("utf-8", "replace"), b

    def yolsuz(metin: str) -> bool:
        """Mutlak veri dizini ne duz ne JSON-kacisli (ters bolu iki katli) bicimde gecmez."""
        d = str(pc_ayar.veri_dizini())
        return d not in metin and json.dumps(d)[1:-1] not in metin

    def lan_isareti(b: dict) -> str | None:
        return next((v for k, v in b.items() if k.lower() == "x-kopru-ret"), None)

    try:
        # ── kapilar: yazmadan ONCE reddedilir, dosya hic olusmaz ──────────────
        ayar.unlink(missing_ok=True)
        k_baslik, _, _ = post({"bildirim": {"kopuk": False}}, {"Content-Type": "application/json"})
        k_lan, g_lan, b_lan = post({"bildirim": {"kopuk": False}}, t=taban_lan)
        k_x, _, _ = post({"bildirim": {"kopuk": False}}, {**JSON_B, "Origin": "http://evil.example"})
        k_sfs, _, _ = post({"bildirim": {"kopuk": False}}, {**JSON_B, "Sec-Fetch-Site": "cross-site"})
        k_tur, _, _ = post({"bildirim": {"kopuk": False}}, {"X-Olcum": "1", "Content-Type": "text/plain"})
        k_host, _, _ = post({"bildirim": {"kopuk": False}}, {**JSON_B, "Host": "evil.example"})
        ok("[!] 4H: POST /bildirim/ayar KAPILARI — X-Olcum yoksa 400, yerel ag 403 (+ X-Kopru-Ret: lan), baska "
           "koken (Origin / Sec-Fetch-Site) 403, govde JSON degilse 415, taninmayan Host 403; hicbirinde "
           "ayar.json YAZILMAZ",
           k_baslik == 400 and k_lan == 403 and lan_isareti(b_lan) == "lan" and k_x == 403 and k_sfs == 403
           and k_tur == 415 and k_host == 403 and not ayar.exists(),
           f"baslik={k_baslik} lan={k_lan}/{lan_isareti(b_lan)} origin={k_x} sfs={k_sfs} tur={k_tur} host={k_host}")

        # ── kati dogrulama: her biri 400, dosya degismez ──────────────────────
        once = {"esitleme_onay": False, "esitleme_aralik_s": 300, "bildirim": {"bitti": False},
                "kullanicinin_notu": "elle yazdim"}
        ayar.write_text(json.dumps(once, ensure_ascii=False, indent=2), encoding="utf-8")
        ham_once = ayar.read_bytes()
        kotu = {
            "bilinmeyen alan": {"bildirim": {"kopuk": False}, "parola": "sinama-pw-4h"},
            "araci adresi": {"uri": "mqtts://sinama.example:8883"},
            "bilinmeyen sinif": {"bildirim": {"parola": False}},
            "bool olmayan (1)": {"bildirim": {"kopuk": 1}},
            "bool olmayan ('false')": {"bildirim": {"kopuk": "false"}},
            "bool olmayan (null)": {"bildirim": {"kopuk": None}},
            "bildirim nesne degil": {"bildirim": ["kopuk"]},
            "gecersiz dil": {"dil": "de"},
            "dil metin degil": {"dil": 1},
            "bos degisiklik": {},
            "bos bildirim": {"bildirim": {}},
            "dizi govde": [{"bildirim": {"kopuk": False}}],
            "JSON degil": b"kopuk=0",
            "tekrarlanan anahtar": b'{"bildirim": {"kopuk": false, "kopuk": true}}',
            "tekrarlanan ust anahtar": b'{"dil": "en", "dil": "tr"}',
            "NaN": b'{"bildirim": {"kopuk": NaN}}',
            "tam buyuk ama gecerli": b'{"bildirim": {"kopuk": false}' + b" " * 600 + b"}",
        }
        sonuc = {ad: post(g)[0] for ad, g in kotu.items()}
        ok("[!] 4H: KATI dogrulama — bilinmeyen alan (parola, uri), bilinmeyen sinif, true/false olmayan deger "
           "(1, 'false', null), nesne olmayan bildirim, gecersiz dil, bos degisiklik, dizi govde, JSON olmayan "
           "govde, tekrarlanan anahtar, NaN, 512 B'den buyuk govde -> 400; ayar.json BAYT BAYT ayni",
           all(k == 400 for k in sonuc.values()) and ayar.read_bytes() == ham_once,
           " ".join(f"{a}={k}" for a, k in sonuc.items() if k != 400) or "hepsi 400")

        # ── birlestirme: oteki anahtarlar korunur ─────────────────────────────
        k1, g1, _ = post({"bildirim": {"kopuk": False, "deneme": True}})
        k2, g2, _ = post({"dil": "en"})
        sonra = json.loads(ayar.read_text(encoding="utf-8"))
        try:
            y1, y2 = json.loads(g1), json.loads(g2)
        except ValueError:
            y1, y2 = {}, {}
        kd, gd = _guvenli_istek(taban + "/bildirim/durum")
        try:
            dd = json.loads(gd)
        except ValueError:
            dd = {}
        ok("[!] 4H: yazma ayar.json'a BIRLESTIRIR — esitleme_onay / esitleme_aralik_s / kullanicinin anahtari ve "
           "onceki bildirim.bitti AYNEN kalir; yanit ve GET /bildirim/durum (bildirim ipligi kurulmamisken de) "
           "yeni ac/kapa ve dili gosterir",
           k1 == 200 and k2 == 200 and sonra.get("esitleme_onay") is False and sonra.get("esitleme_aralik_s") == 300
           and sonra.get("kullanicinin_notu") == "elle yazdim"
           and sonra.get("bildirim") == {"bitti": False, "kopuk": False, "deneme": True}
           and sonra.get("bildirim_dil") == "en"
           and y1.get("ayar", {}).get("kopuk") is False and y1.get("ayar", {}).get("bitti") is False
           and y2.get("dil") == "en" and set(y2.get("ayar", {})) == set(PB.SINIFLAR)
           and kd == 200 and dd.get("etkin") is False and dd.get("dil") == "en"
           and dd.get("ayar", {}).get("kopuk") is False and dd.get("ayar", {}).get("esik") is True,
           f"{k1} {k2} {sonra} durum={gd[:120]}")
        ok("[!] 4H: SIR YOK — yazmalardan sonra ayar.json'da yalniz onceki anahtarlar + bildirim / bildirim_dil; "
           "bildirim altinda yalniz bilinen siniflar ve true/false; reddedilen parola / araci adresi dosyada yok, "
           "yanitlarda mutlak yol yok",
           set(sonra) == set(once) | {"bildirim_dil"} and set(sonra["bildirim"]) <= set(PB.SINIFLAR)
           and all(isinstance(v, bool) for v in sonra["bildirim"].values())
           and "sinama-pw-4h" not in ayar.read_text(encoding="utf-8") and "sinama.example" not in ayar.read_text(encoding="utf-8")
           and yolsuz(g1 + g2), str(sorted(sonra)))

        # ── bozuk dosyanin uzerine yazilmaz ───────────────────────────────────
        ayar.write_bytes(b'{"esitleme_onay": false, "bildirim": ')
        bozuk = ayar.read_bytes()
        kb, gb, _ = post({"bildirim": {"kopuk": True}})
        ok("[!] 4H: ayar.json okunamiyorsa 409 ve dosya BAYT BAYT ayni (kullanicinin elle yazdigi ayar ezilmez); "
           "mesajda mutlak yol yok",
           kb == 409 and ayar.read_bytes() == bozuk and yolsuz(gb), f"{kb} {gb[:80]}")
        ayar.unlink()

        # ── yerel ag reddi isaretli; oteki retler isaretsiz; p0 serbest ───────
        lan = {}
        for ad, yol, yontem, veri, bas in (
                ("komut", "/komut", "POST", b"?", {"X-Olcum": "1"}),
                ("devral", "/devral", "POST", b"", {"X-Olcum": "1", "X-Jeton": "x"}),
                ("kapat", "/kapat", "POST", b"", {"X-Olcum": "1"}),
                ("esitleme", "/esitleme/durum", None, None, {}),
                ("bildirim", "/bildirim/durum", None, None, {}),
                ("arsiv", "/arsiv/liste", None, None, {}),
                ("skop", "/skop.bin", None, None, {"X-Olcum": "1"})):
            r = _guvenli_istek_bas(taban_lan + yol, veri, bas, yontem)
            lan[ad] = (r[0], lan_isareti(r[2]))
        p0 = _guvenli_istek_bas(taban_lan + "/komut", b"p0", {"X-Olcum": "1"}, "POST")
        csrf = _guvenli_istek_bas(taban + "/komut", b"?", {"X-Olcum": "1", "Origin": "http://evil.example"}, "POST")
        kop.surucu = "baskasi"
        surucu_degil = _guvenli_istek_bas(taban + "/komut", b"?", {"X-Olcum": "1", "X-Jeton": "x"}, "POST")
        kop.surucu = None
        ok("[!] 4H: yerel ag istemcisinin 403'leri ISARETLI (X-Kopru-Ret: lan — panel cevrilmis 'salt okuma' "
           "uyarisi gosterir): komut, devral, kapat, esitleme/durum, bildirim/durum, arsiv, skop.bin; p0 yine "
           "serbest; baska sebepli 403 (capraz koken, surucu degil) ISARETSIZ",
           all(v == (403, "lan") for v in lan.values()) and p0[0] == 204
           and csrf[0] == 403 and lan_isareti(csrf[2]) is None
           and surucu_degil[0] == 403 and lan_isareti(surucu_degil[2]) is None,
           f"{lan} p0={p0[0]} csrf={csrf[0]}/{lan_isareti(csrf[2])} surucu={surucu_degil[0]}/{lan_isareti(surucu_degil[2])}")

        # ── kabuk surumu ──────────────────────────────────────────────────────
        import re as _re
        sw = (KOK / "arayuz3" / "sw.js").read_text(encoding="utf-8")
        m = _re.search(r"^const SURUM = '([0-9a-f]{12})';$", sw, _re.M)
        kdu, gdu = _guvenli_istek(taban + "/durum")
        try:
            du = json.loads(gdu)
        except ValueError:
            du = {}
        ok("[!] 4H: /durum `kabuk` = koprunun sundugu panel kabugunun surumu (sw.js SURUM, arayuz-uret.py yazar)",
           kdu == 200 and m is not None and du.get("kabuk") == m.group(1), f"{du.get('kabuk')} / {m and m.group(1)}")
    finally:
        for x in (s, s_lan):
            x.shutdown()
            x.server_close()
        ayar.unlink(missing_ok=True)


def _guvenli_istek_bas(url, veri=None, basliklar=None, yontem=None, zaman_asimi=5):
    """`istek_bas` + baglanti hatasi -> (None, hata, {})."""
    try:
        return istek_bas(url, veri, basliklar, yontem, zaman_asimi)
    except Exception as e:                              # noqa: BLE001
        return None, str(e).encode("utf-8", "replace"), {}


class _AcikAkis:
    """4I: ACIK kalan `/akis` — yasayan bir sekme. Ham soketle (baglantiyi ne zaman
    kapattigimizi biz bilelim: urllib yaniti soketi kendi tutuyor). `kimlikler` her
    `event: kimlik` olayini varis anıyla toplar; `kapat()` sekmenin kapanmasi/yenilenmesi."""

    def __init__(self, taban: str, basliklar: dict | None = None):
        import socket
        import urllib.parse
        u = urllib.parse.urlsplit(taban)
        self.s = socket.create_connection((u.hostname, u.port), timeout=10)
        bas = {"Host": f"{u.hostname}:{u.port}", **(basliklar or {})}
        self.s.sendall(("GET /akis HTTP/1.1\r\n" + "".join(f"{a}: {d}\r\n" for a, d in bas.items())
                        + "\r\n").encode("utf-8"))
        self.dosya = self.s.makefile("rb")
        self.kod = int(self.dosya.readline().split()[1])
        self.kimlikler: list[tuple[float, dict]] = []
        self.kapali = False
        threading.Thread(target=self._oku, daemon=True).start()

    def _oku(self):
        sonraki = False
        try:
            while True:
                ham = self.dosya.readline()
                if not ham:
                    break
                sat = ham.decode("utf-8", "replace").rstrip("\r\n")
                if sat.startswith("event: kimlik"):
                    sonraki = True
                elif sat.startswith("data: ") and sonraki:
                    self.kimlikler.append((time.monotonic(), json.loads(sat[6:])))
                    sonraki = False
        except Exception:                                   # noqa: BLE001
            pass

    def kimlik(self, n: int = 1, sure: float = 3.0) -> dict | None:
        """n. kimlik olayini bekle (1 = ilk)."""
        son = time.monotonic() + sure
        while len(self.kimlikler) < n and time.monotonic() < son:
            time.sleep(0.01)
        return self.kimlikler[n - 1][1] if len(self.kimlikler) >= n else None

    @property
    def jeton(self) -> str:
        k = self.kimlik()
        return k["jeton"] if k else ""

    def kapat(self):
        import socket
        if self.kapali:
            return
        self.kapali = True
        try:
            self.s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.dosya.close()
        self.s.close()


def pc_4i_sina(gec_dizin: Path) -> None:
    """4I — surucu sekmesi yenilenince / kapaninca rol BIRAKILIR (spec "4I uygulama kararlari").

    🔴 4H'de bulundu: kopru, yenilenen ya da kapanan sekmenin surucu jetonunu tutmaya devam
       ediyordu. EventSource baslik gonderemedigi icin yenilenen sekme YENI jeton aliyor ->
       yalniz izleyici; acilis komutlari (`?`, `CT`, `G?`) ve kullanicinin her islemi 403
       "surucu degil", ta ki elle devralana dek. PC uygulamasinda her yenilemede.
    """
    print("\n--- 4I. Surucunun akisi kapaninca rol birakilir ---")
    kart = kart_baglanti.KayitKart([], yanitlar={"p0": ["* durdu"]})   # BOSTA: akisa satir gelmiyor
    kart.ac()
    k = kopru_mod.Kopru(kart, gec_dizin / "arsiv_4i")
    s = _kos(k)
    s_lan = _kos(k, _LanIsleyici)
    tb = f"http://127.0.0.1:{s.server_address[1]}"
    lb = f"http://127.0.0.1:{s_lan.server_address[1]}"
    kom = {"X-Olcum": "1"}

    def komut(metin, jeton, taban=tb):
        return istek(taban + "/komut", metin.encode(), {**kom, "X-Jeton": jeton}, "POST")[0]

    acik: list[_AcikAkis] = []

    def ac(taban=tb, basliklar=None):
        a = _AcikAkis(taban, basliklar)
        acik.append(a)
        return a

    try:
        # ── 1. yenileme: eski surucu kapanir, HEMEN yeni akis gelir ──────
        a = ac()
        ka = a.kimlik()
        a.kapat()
        b = ac()                     # bekleme YOK — tarayicida yenileme boyle
        kb = b.kimlik()
        once = len(kart.yazilanlar)
        kodlar = {m: komut(m, b.jeton) for m in ("?", "CT", "G?")}
        ok("[!] 4I: surucu sekme YENILENINCE yeni sekme ilk `kimlik`te SURUCU, acilis komutlari "
           "(`?` `CT` `G?`) 204 ve karta ulasiyor",
           bool(ka and ka["surucu"]) and bool(kb and kb["surucu"]) and k.surucu == b.jeton
           and all(c == 204 for c in kodlar.values()) and kart.yazilanlar[once:] == ["?", "CT", "G?"],
           f"eski={ka} yeni={kb} · {kodlar} · karta={kart.yazilanlar[once:]}")
        ok("4I: kapanan sekmenin eski jetonu artik surucu degil (komutu 403)",
           komut("?", ka["jeton"] if ka else "x") == 403, f"surucu={k.surucu == (ka or {}).get('jeton')}")

        # ── 1b. IKINCI sekme aciktayken yenileme: rol arka sekmeye KACMAZ ───
        # 🔴 4I incelemesinde bulundu: eski akisin isleyicisi kapanisi <= 0.5 s'de fark edip
        #    rolu HEMEN yasayan tek yerel akisa (arka sekme) veriyordu; yenilenen sekmenin
        #    yeni /akis'i hep ondan SONRA geliyor -> surucu yasiyor, "calma yok" -> yenilenen
        #    sekme izleyici, acilis komutlari 403. Gecikmeler 0…1.5 s hepsinde. Yeniden
        #    yuklenme penceresi (AKIS_DEVIR_BEKLE_S) icinde gelen yeni yerel akis rolu alir.
        sonuc_1b = []
        for gec in (0.0, 0.8, 1.5):
            v = ac()
            kv = v.kimlik()
            b.kapat()
            time.sleep(gec)              # eski isleyici kapanisi coktan fark etti (<= 0.5 s)
            b = ac()
            kb = b.kimlik()
            kod_b = komut("?", b.jeton)
            kod_v = komut("CT", v.jeton)
            sonuc_1b.append((gec, bool(kv) and not kv["surucu"], bool(kb and kb["surucu"]), kod_b,
                             kod_v, len(v.kimlikler)))
            v.kapat()
        time.sleep(kopru_mod.AKIS_DEVIR_BEKLE_S + 0.6)   # pencere zamanlayicisi da rolu kacirmasin
        ok("[!] 4I: IKINCI yerel sekme aciktayken surucu YENILENINCE (yeni akis eski isleyici "
           "fark ettikten 0 / 0.8 / 1.5 s sonra) yenilenen sekme SURUCU, `?` 204; arka sekme rol "
           "olayi almaz, komutu 403",
           all(x[1:] == (True, True, 204, 403, 1) for x in sonuc_1b) and k.surucu == b.jeton
           and komut("?", b.jeton) == 204,
           f"(gec, v izleyici, yeni surucu, ?, v CT, v olay) = {sonuc_1b}")

        # ── 2. kapanan surucu: rol <= 2 s'de EN YENI yasayan yerel izleyiciye ─
        c = ac()
        d = ac()
        kc, kd = c.kimlik(), d.kimlik()
        t0 = time.monotonic()
        b.kapat()
        devir_ust = kopru_mod.AKIS_DEVIR_BEKLE_S + 1.5   # pencere + 0.5 s yoklama + pay
        kd2 = d.kimlik(2, sure=devir_ust + 2.0)
        dt = (d.kimlikler[1][0] - t0) if len(d.kimlikler) >= 2 else None
        ok("[!] 4I: surucunun akisi kapaninca rol, yeniden yuklenme penceresi dolunca "
           f"(<= {devir_ust:.1f} s) EN YENI yasayan yerel izleyiciye gecer, "
           "o sekme yeniden yuklenmeden `kimlik` olayi (surucu: true, kendi jetonu) alir",
           bool(kc and kd) and not kc["surucu"] and not kd["surucu"] and bool(kd2 and kd2["surucu"])
           and kd2["jeton"] == d.jeton and dt is not None and dt <= devir_ust and k.surucu == d.jeton,
           f"dt={dt if dt is None else round(dt, 3)} s · yeni={kd2}")
        time.sleep(0.3)
        ok("4I: devir yalniz yeni surucuye — daha eski izleyici (c) rol olayi almadi, komutu 403; "
           "yeni surucunun komutu 204",
           len(c.kimlikler) == 1 and komut("?", c.jeton) == 403 and komut("?", d.jeton) == 204,
           f"c olaylari={len(c.kimlikler)}")

        # ── 3. iki YASAYAN sekme: sessiz calma yok; /devral acik yol ───────
        kodlar_c = []
        for _ in range(4):
            kodlar_c.append(komut("CT", c.jeton))
            time.sleep(0.3)
        e = ac()
        ke = e.kimlik()
        ok("[!] 4I: iki sekme de ACIKKEN surucu degismez — izleyicinin komutlari 403 kalir, yeni "
           "acilan sekme izleyici (rol calinmaz)",
           all(x == 403 for x in kodlar_c) and k.surucu == d.jeton and bool(ke) and not ke["surucu"],
           f"izleyici={kodlar_c} · yeni={ke}")
        kod_dv, _ = istek(tb + "/devral", b"", {**kom, "X-Jeton": c.jeton}, "POST")
        ok("4I: acik devralma (/devral) aynen calisiyor: izleyici devralir, eski surucu 403",
           kod_dv == 204 and komut("?", c.jeton) == 204 and komut("?", d.jeton) == 403,
           f"devral={kod_dv}")

        # ── 4. LAN: yerel ag izleyicisi ASLA surucu olmaz; p0 her zaman ────
        for x in (d, e):
            x.kapat()
        lan = ac(lb)
        kl = lan.kimlik()
        c.kapat()                        # yasayan tek yerel sekme (surucu) kapandi
        time.sleep(0.8)                  # isleyici fark etti; yeniden yuklenme penceresi acik
        lan2 = ac(lb)                    # pencere icinde YENI kaydolan LAN akisi da aday degil
        kl2 = lan2.kimlik()
        time.sleep(kopru_mod.AKIS_DEVIR_BEKLE_S + 1.0)   # pencere zamanlayicisi da LAN'a vermesin
        kod_l = komut("?", lan.jeton, lb)
        kod_p0 = komut("p0", "", lb)
        kod_p0b = komut("p0", "")
        ok("[!] 4I: surucu kapaninca yerel AG izleyicisi rolu ALMAZ — ne acik olan, ne pencere icinde "
           "yeni kaydolan, ne pencere dolunca (olay yok, komutu 403); `p0` (DURDUR) LAN'dan da bu "
           "bilgisayardan da jetonsuz 204",
           bool(kl) and not kl["surucu"] and len(lan.kimlikler) == 1 and k.surucu != lan.jeton
           and bool(kl2) and not kl2["surucu"] and len(lan2.kimlikler) == 1 and k.surucu != lan2.jeton
           and kod_l == 403 and kod_p0 == 204 and kod_p0b == 204,
           f"lan olaylari={len(lan.kimlikler)}/{len(lan2.kimlikler)} yeni={kl2} ?={kod_l} "
           f"p0={kod_p0}/{kod_p0b}")

        # ── 5. CSRF: baska kokenden /akis rolu ve jetonu ALAMAZ ───────────
        jetonlar = len(k.jetonlar)
        kod_x = _AcikAkis(tb, {"Sec-Fetch-Site": "cross-site"})
        acik.append(kod_x)
        kod_o = _AcikAkis(tb, {"Origin": "http://stok"})
        acik.append(kod_o)
        time.sleep(0.3)
        f = ac()
        kf = f.kimlik()
        ok("[!] 4I: rol bostayken baska kokenden /akis 403, jeton yok; ardindan ayni kokenden acilan "
           "sekme SURUCU",
           kod_x.kod == 403 and kod_o.kod == 403 and not kod_x.kimlikler and not kod_o.kimlikler
           and len(k.jetonlar) == jetonlar + 1 and bool(kf and kf["surucu"]) and k.surucu == f.jeton,
           f"capraz={kod_x.kod}/{kod_o.kod} jeton +{len(k.jetonlar) - jetonlar} yeni={kf}")
    finally:
        for x in acik:
            x.kapat()
        for sv in (s, s_lan):
            sv.shutdown()
            sv.server_close()

    # ── 6. komut aninda yoklama (isleyici kopuslugu henuz fark etmeden) ──
    import socket
    import queue as _q
    k2 = kopru_mod.Kopru(kart_baglanti.KayitKart([]), gec_dizin / "arsiv_4i_2")
    j1 = k2.jeton_ver()
    j2 = k2.jeton_ver()
    s1, s1_karsi = socket.socketpair()
    s2, s2_karsi = socket.socketpair()
    q2 = _q.Queue()
    k2.akis_kaydet(j1, s1, _q.Queue(), True)
    k2.akis_kaydet(j2, s2, q2, True)
    once = (k2.komut_izinli("?", j2)[0], k2.surucu == j1)
    s1_karsi.close()                 # surucunun sekmesi kapandi; isleyicisi henuz bilmiyor
    t_k = time.monotonic()
    izin = k2.komut_izinli("?", j2)[0]
    dt_k = time.monotonic() - t_k
    olay = q2.get_nowait() if not q2.empty() else None
    yabanci = k2.komut_izinli("?", "baskasi")[0]
    pencere = kopru_mod.AKIS_DEVIR_BEKLE_S
    ok("[!] 4I: surucunun soketi kapaliysa izleyicinin KOMUTU (isleyici kopusu henuz fark etmeden) "
       "yeniden yuklenme penceresinin sonunu bekleyip rolu devralir ve 204 alir (403 degil); ona "
       "`kimlik` gider; bilinmeyen jeton yine 403",
       once == (False, True) and izin and k2.surucu == j2 and isinstance(olay, tuple)
       and pencere - 0.2 <= dt_k <= pencere + 1.0
       and olay[0] == "kimlik" and json.loads(olay[1]) == {"jeton": j2, "surucu": True} and not yabanci,
       f"once={once} izin={izin} bekleme={dt_k:.2f} s olay={olay} yabanci={yabanci}")

    # ── 6b. pencere icinde yenilenen sekme gelirse bekleyen izleyici komutu 403 ──
    s3, s3_karsi = socket.socketpair()
    q3 = _q.Queue()
    j3 = k2.jeton_ver()
    s4, s4_karsi = socket.socketpair()
    j4 = k2.jeton_ver()
    k2.akis_kaydet(j4, s4, _q.Queue(), True)              # acik izleyici sekme (surucu j2 yasarken)
    s2_karsi.close()                 # surucu (j2) kapandi; pencere basliyor
    sonuc6b: dict = {}
    th6 = threading.Thread(target=lambda: sonuc6b.update(izin=k2.komut_izinli("CT", j4)[0]),
                           daemon=True)
    th6.start()
    time.sleep(0.4)
    k2.akis_kaydet(j3, s3, q3, True)                      # yenilenen sekme pencere icinde geldi
    th6.join(pencere + 2.0)
    ok("[!] 4I: pencere icinde yenilenen sekme gelirse rol ONUN; pencereyi bekleyen acik izleyicinin "
       "komutu 403 (rol arka sekmeye kacmaz)",
       k2.surucu == j3 and sonuc6b.get("izin") is False and not th6.is_alive(),
       f"surucu=j3:{k2.surucu == j3} j4:{k2.surucu == j4} izin={sonuc6b}")
    for x in (s1, s2, s3, s3_karsi, s4, s4_karsi):
        x.close()


def _g4e(durum: int, oturum: int) -> str:
    return f"G {durum} {oturum} 100 101 50 120 10 0 900 25000 3 400 0"


def pc_4g_sina() -> None:
    """4G (gercek kart kabulu): `uretim/tezgah_pc.py`'nin SAF yardimcilari cevrimdisi.

    Kabulun kendisi gercek kartta (tezgah); burada olcum ARACININ yalan soylemedigi sinaniyor:
    kayitci TCP rolesi iki yonu de kaydediyor mu, sir arayici onaltilik/base64 bicimini buluyor mu,
    `Authorization:` sayaci harf duyarsiz mi, akis karsilastirici tek bayt farkini yakaliyor mu."""
    print("\n--- 4G. Kabul araci (tezgah_pc.py): kayitci, sir arama, akis karsilastirma ---")
    import base64
    import secrets as _s
    import tezgah_pc as T
    import kayit_bicim as KB
    sir = _s.token_bytes(32)
    kullanici = "araci-kullanicisi-" + _s.token_hex(4)
    gorulen_host: list = []

    class _H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            gorulen_host.append(self.headers.get("Host"))
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            g = b"zarf " + sir.hex().upper().encode() + b" " + base64.urlsafe_b64encode(sir).rstrip(b"=")
            self.send_response(200)
            self.send_header("Content-Length", str(len(g)))
            self.end_headers()
            self.wfile.write(g)

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    v = T.KayitciVekil("127.0.0.1", srv.server_address[1], host_yaz="olcum.local").baslat()
    ist = urllib.request.Request(f"http://127.0.0.1:{v.port}/komut?x=1", data=kullanici.encode(), method="POST",
                                 headers={"authorization": "Basic eHk6eg==", "X-Olcum": "1"})
    try:
        govde = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(ist, timeout=5).read()
    except OSError as e:
        govde = repr(e).encode()
    time.sleep(0.3)
    akislar = list(v.akislar().values())
    istekler = v.istekler()
    v.durdur()
    srv.shutdown()
    bulunan = T.kayitta_ara(akislar, {"sir": sir, "kullanici": kullanici, "yok": _s.token_bytes(16)})
    ok("4G: kayitci TCP rolesi baytlari aynen iletir ve IKI YONU de kaydeder (istek satiri + yanit kodu); "
       "yalniz `Host:` karta kendi adiyla gider (kart baska Host'u 403 'Host reddedildi' ile reddediyor)",
       govde.startswith(b"zarf ") and [(x["yontem"], x["yol"], x["durum"]) for x in istekler]
       == [("POST", "/komut?x=1", 200)] and gorulen_host == ["olcum.local"]
       and b"Host: olcum.local\r\n" in b"".join(akislar), f"{istekler} {govde[:12]!r} host={gorulen_host}")
    ok("4G: sir arayici kayitta BUYUK onaltilik ve dolgusuz URL-guvenli base64 bicimini (yanittan), duz "
       "metni (istek govdesinden) bulur; olmayan sir 0",
       bulunan["sir"]["ham"] >= 2 and bulunan["kullanici"]["sinirli"] == 1 and bulunan["yok"]["ham"] == 0,
       str(bulunan))
    ok("4G: `Authorization:` sayaci harf duyarsiz (kucuk harfli baslik da sayilir), govdedeki sozcuk degil",
       T.yetki_basligi(akislar) == 1 and T.yetki_basligi([b"x authorization: y"]) == 0
       and T.yetki_basligi([b"GET / HTTP/1.1\r\nProxy-Authorization: Basic x\r\n"]) == 1,
       str(T.yetki_basligi(akislar)))
    ok("4G: sinirli sayim daha uzun sozcugun parcasini ayirir ('olcum-kart' 'olcum-karti' icinde)",
       T.kayitta_ara([b"olcum-karti olcum-kart."], {"k": "olcum-kart"})["k"] == {"ham": 2, "sinirli": 1})
    k = [KB.kayit_paketle(3, i, 7, bytes([i]) * 8) for i in range(1, 11)]
    tam = b"".join(k)
    farkli = b"".join(k[:5] + [KB.kayit_paketle(3, 6, 7, bytes([99]) * 8)] + k[6:])
    a = T.akis_karsilastir(tam, tam)
    b = T.akis_karsilastir(b"".join(k[:8]), b"".join(k[2:]))       # arsivde eski onek, taze sonek
    c = T.akis_karsilastir(tam, farkli)
    d = T.akis_karsilastir(b"".join(k[:4] + k[5:]), tam)              # arsivde bir sira EKSIK
    ok("4G: akis karsilastirici — ayni akis ayni; arsivin eski oneki / tazenin yeni soneki ortak araligi "
       "bozmaz (sayilir); TEK kayitta farkli bayt (gecerli CRC) ve arsivde eksik sira AYNI DEGIL",
       a["ayni"] and a["tam_ayni"] and b["ayni"] and not b["tam_ayni"] and b["yalniz_pc"] == 2
       and b["yalniz_taze"] == 2 and b["ortak"] == 6 and not c["ayni"] and c["ortak"] == 10
       and not d["ayni"], f"{a['ayni']} {b} {c['ayni']} {d['ayni']}")
    # gercek_dizin_koru (4G + 4H birlesik kural): geri alma YALNIZ cihaz/'da beliren dosyada; baska yerde
    # silme yok; gercek kopru aciksa cihaz/ disindaki ve cihaz/'da VAROLAN dosyadaki degisiklik onun (yesil),
    # cihaz/'da YENI dosya her zaman kirmizi.
    import tempfile as _tf
    sonuc = {}
    for ad, acik in (("acik", True), ("kapali", False)):
        with _tf.TemporaryDirectory() as kd:
            kok = Path(kd)
            (kok / "cihaz").mkdir()
            varolan = kok / "cihaz" / "kart.json"
            varolan.write_bytes(b"sayac=1")
            # 1) cihaz/ disinda beliren arsiv + cihaz/'da varolan dosyanin sayaci ilerler (kopru isi)
            koruma = {"kok": kok, "once": gercek_dizin_koru._dokum(kok)}
            arsiv = kok / "akis-1" / "kayitlar.kyt"
            arsiv.parent.mkdir()
            arsiv.write_bytes(b"x")
            varolan.write_bytes(b"sayac=22")
            notlar = []
            gercek_dizin_koru.denetle(koruma, lambda a, k, e="": notlar.append((k, e)), kopru_acik=lambda a=acik: a)
            # 2) cihaz/'da YENI dosya (sahte kartin cihaz dosyasi)
            koruma = {"kok": kok, "once": gercek_dizin_koru._dokum(kok)}
            sahte = kok / "cihaz" / "sahte.json"
            sahte.write_bytes(b"y")
            notlar2 = []
            gercek_dizin_koru.denetle(koruma, lambda a, k, e="": notlar2.append((k, e)), kopru_acik=lambda a=acik: a)
            sonuc[ad] = (arsiv.exists(), varolan.exists(), notlar[0][0], sahte.exists(), notlar2[0][0])
    ok("4G/4H: gercek_dizin_koru — cihaz/ disinda HIC silmez (calisan koprunun yeni arsivi olabilir); kopru "
       "ACIKKEN cihaz/ disi + varolan cihaz dosyasinin degismesi yesil, kapaliyken kirmizi; cihaz/'da beliren "
       "YENI dosya her durumda kirmizi ve geri alinir",
       sonuc == {"acik": (True, True, True, False, False), "kapali": (True, True, False, False, False)},
       str(sonuc))


def main() -> int:
    print("=" * 78)
    print("  B22.3  PC KOPRUSU  (role · arsiv · surucu hakemi)")
    print("=" * 78)

    import tempfile
    gec_dizin = gecici.dizin("kopru_")
    # 4B: pc.calistir artik USB yoksa kartla WiFi'den konusuyor — testler GERCEK karta
    # (olcum.local) ve kullanicinin cihaz dizinine ASLA gitmesin: kapali yerel port + gecici dizin
    os.environ["OLCUM_KART_HOST"] = "127.0.0.1:9"
    os.environ["OLCUM_CIHAZ_DIZIN"] = str(gec_dizin / "cihaz")

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

    # 4A inceleme: kopru kendi `t`sini yalniz /komut'un kapisindan yollar
    kod, govde, bas = istek_bas(taban + "/skop.bin", basliklar={"X-Olcum": "1", "X-Jeton": surucu_jetonu}, zaman_asimi=25)
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
    kod, govde = istek(taban + "/skop.bin", basliklar={"X-Olcum": "1", "X-Jeton": surucu_jetonu})
    gecen = time.monotonic() - t0
    ok("[!] Tetiklenemeyince HEMEN 503 (20 s beklemiyor)",
       kod == 503 and gecen < 5.0, f"HTTP {kod}, {gecen:.2f} s")
    ok("503 sebebi soyleniyor", b"tetikle" in govde,
       govde[:60].decode("utf-8", "replace"))

    # Kirpik blok CIZILMIYOR: eksik dalga "olculmus" gibi gorunmemeli.
    kart.yanitlar["t"] = ["S2 64 10000 0.028787 12 5000 0 1 0.0",
                          "1 2 3 4 5 6 7 8", "E"]
    kod, govde = istek(taban + "/skop.bin", basliklar={"X-Olcum": "1", "X-Jeton": surucu_jetonu})
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
    pc_4a_inceleme_sina(gec_dizin)
    pc_4b_sina(gec_dizin)
    pc_4c_sina(gec_dizin)
    pc_4d_sina(gec_dizin)
    pc_4e_sina(gec_dizin)
    pc_4g_sina()
    pc_4h_sina(gec_dizin)
    pc_4i_sina(gec_dizin)

    k.calisiyor = False
    time.sleep(0.25)
    sunucu.shutdown()
    k.durdur()
    gercek_dizin_koru.denetle(_KORUMA, ok)
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
         "baslar. `Otomatik Baslatmayi Kapat.bat` kisayolu siler (kurulum kullanicinin). "
         "⚠ Kurulum YALNIZ ana calisma agacindan (projeler/olcum-karti), gecici dal "
         "agacindan degil (betik worktree'yi reddeder). Durdurma: `kopru/Kopruyu Durdur.bat`"),
        ("4A: USB kablosu cek / tak",
         "Kopru acikken kabloyu cek: akista BIR KEZ '! kopru: kart baglantisi koptu'; "
         "tak: '* kopru: kart baglandi' ve D satirlari geri gelir. ReadFile'in kopmada "
         "FALSE dondugu gercek CH343'te SINANMADI (OtoSeriKart sahte kartla sinaniyor)"),
        ("4B: kopru kartla WiFi'den ESLESMIS CIHAZ olarak (firmware A3-4B)",
         "Once bir kez `python kopru/imza.py esles --host olcum.local --ad <bu-PC>` (WEB parolasi). "
         "USB kablosu takili DEGILKEN `kopru/PC Baslat.bat` (ya da `python kopru/pc.py --usb-yok`: "
         "COM portu acilmaz): akista '* kopru: ... yukari-akis WiFi' + "
         "'* kopru: WiFi baglandi', D satirlari; komut (ör. `?`) imzali gider, `p0` imzasiz. Kablo "
         "takilinca USB'ye doner ('WiFi baglantisi kapatildi'), cekilince WiFi'ye (KALAN: kablo cek/tak elle). "
         "Kopru + karta dogrudan 3 tarayici = 4 yuva, hicbiri reddedilmez; 5. istemci `event: dolu` — 4G'de "
         "koşuldu (`tezgah_pc.py --o5`: kopru 1 yuva, kullanicinin Chrome'u 1, dogrudan 2, sonraki dolu)"),
        ("4G: GERCEK KART KABULU — `python uretim/tezgah_pc.py --o3` ve `--o5`",
         "2026-10-03 A3-4B: Ö3 11/11 (kopru 202 s kapali, bosluk 59 kayit 4.5 s'de, arsiv bagimsiz indirmeyle "
         "bayt bayt ayni 1 311 112 B), Ö5 + izleyici + p0 14/14 (kopru<->kart kaydinda K / araci bilgisi / "
         "Authorization 0; 6 sekme 1 yuvada; p0 5/5 204 <= 246 ms). Kopru, firmware ya da kart_wifi degisince "
         "TEKRAR kosun. ⚠ Ö3 kullanicinin GERCEK arsivine yazar ve karta ONAY yollar; Ö5 web parolasini "
         "yalniz OLCUM_PAROLA verilirse arar. Kopru KAPALIYKEN baslatin (betik acik kopruyu reddeder)"),
        ("4C: arka plan esitlemesi gercek kartta (ONAYLI ilk kosu bekliyor)",
         "2026-10-03 A3-4B, `pc.py --usb-yok --onaysiz` (gecici OLCUM_PC_DIZIN): 2234 kayit / 1 268 956 B / "
         "son sira 61276 / 44 oturum, kartin /kayit/listesiyle ayni, 29.6 s; canli akis hizi bosta ile ayni "
         "(spec 4C tablosu). ONAYLI kosu 4G'de yapildi (Go gitti, kart dogruladi, PC arsivi kartin akisiyla "
         "bayt bayt ayni). KALAN: PC'deki kayitlar.kyt == kartin FLAS bolumu (tezgah_kayit.py --esit, COM6 + "
         "kopru kapali); USB takiliyken (SecmeliKart USB) "
         "esitlemenin WiFi'den surdugu; kart kapatilip acilinca yeniden baglanma tetigiyle <= 10 s'de tur"),
        ("4E: PC'de Windows bildirimi + Ö4 PC karsiligi (PC18: hedef 10 s, kabul 15 s) — GERCEK aracida",
         "Kopru ana agactan acikken (`kopru/PC Baslat.bat`; kart eslesmis, kartta MQTT ayarli) karta kayit "
         "baslat (`Gb1000`), kartin FISINI CEK (USB + pil kapali): saniye olcerle 'Ölçüm kartı — Karttan haber "
         "yok' bildirimine kadar gecen sure <= 10 s hedef, <= 15 s kabul (10 tekrar; aracinin ilani ~7.5 s + "
         "PC). Karti geri tak: AYNI bildirim 'Kart yeniden bağlandı — kayıt sürüyor' olmali (Bildirim "
         "merkezinde tek kart). Ev interneti: modemin WAN kablosunu cek (kart ve PC ayni agda): 'Ev interneti "
         "koptu — kart çalışıyor'. `Qt` (USB) -> 'Deneme bildirimi'. ⚠ 'Rahatsız Etmeyin' aciksa acilir "
         "pencere CIKMAZ (Bildirim merkezine duser): Ayarlar > Sistem > Bildirimler > Öncelikli bildirimler'e "
         "'Ölçüm kartı' eklenebilir. Araci parolalari yalniz kullanicida — olcumu kullanici yapar"),
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
