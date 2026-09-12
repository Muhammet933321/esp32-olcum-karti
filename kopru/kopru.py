# -*- coding: utf-8 -*-
"""PC KOPRUSU — kart ile tarayicilar arasinda role, arsiv ve surucu hakemi.

    python kopru/kopru.py                 # portu otomatik bul, karti otomatik sec
    python kopru/kopru.py --port COM7
    python kopru/kopru.py --kayit arsiv/2026-09-10.satir    # olu tekrar

🔴 KOPRUNUN ASIL DEGERI GUZEL ARAYUZ DEGIL, ROLE OLMASI.

Karta baglanan HER tarayici olcumu dogrudan bozuyor: her HTTP istegi
`loop()`'u bloklyor (`/pil` tipik 25-200 ms) ve blokaj 1 s'yi gecerse
`enerji_biriktir` o araligi TAMAMEN ATIYOR. Ustelik kartin SSE'si tek
istemcilik. Kopru N tarayiciyi 1'e indiriyor: kart tek bir istemciye
hizmet ediyor, tarayici trafigini PC emiyor.

USB yukari-akis TERCIH EDILENDIR — o kipte kartin WiFi'si hic acilmaz,
yani `loop()`'ta TCP yoktur ve olcum dogrulugu en yuksektir.

── ROLE BAYT-SEFFAF ──────────────────────────────────────────────────
Karttan gelen satir aynen `data: <satir>` olarak yayiliyor. Firmware,
`sahte-kart.js` ve kopru AYNI baytlari konusuyor; arayuzun tek
ayristiricisi bu yuzden yetiyor. `test_kopru.py` bunu bayt-bayt siniyor.

── KOMUT UCU: /komut ─────────────────────────────────────────────────
⚠ Plan `/k` diyordu; `/komut` secildi. Kartin B22.4'te acacagi uc de
  `/komut` olacak, yani istemci KOPRUYE mi KARTA mi bagli oldugunu
  bilmek zorunda kalmiyor. Ayni yol, ayni yontem, ayni basliklar.

── SURUCU HAKEMI ─────────────────────────────────────────────────────
N izleyici, BIR surucu. Jeton kimdeyse kalibrasyon/menzil/pil onda.
🔴 TEK ISTISNA: `p0` (pil desarjini DURDUR) her zaman, jetonsuz,
   kimliksiz gecer. Baslatmak yetki ister; durdurmayi hicbir sey
   geciktiremez.

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import http.server
import json
import queue
import secrets
import socket
import socketserver
import sys
import threading
import time
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"

sys.path.insert(0, str(BURASI))
from arsiv import Arsiv, SkopCozucu, skop_ikili           # noqa: E402
import kart_baglanti                                      # noqa: E402

# stok-takip 127.0.0.1:80'i tutuyor (ayarlar.PORT = 80, Windows acilisinda
# arka planda basliyor). LAN arayuzundeki 80 bos; oradan da olmazsa 8770.
PORT = 80
YEDEK_PORT = 8770

# Her taşımada, jetonsuz, kimliksiz gecen komutlar.
SERBEST_KOMUTLAR = {"p0"}

# Karta yakalama YAPTIRAN komutlar (tam eslesme).
#
# 🔴 `tb0`/`tl500` gibi AYAR komutlari bu kumede DEGIL — onlar yakalama
#    uretmiyor, yalnizca `T ...` ayar satiri basiyor. Onek eslemesi
#    yapilsaydi her ayar degisikligi bosuna bir yakalama beklerdi.
#
# ⚠ `tB` -> `t` CEVRILIYOR. Arayuz ikili tasiyicida `tB` yolluyor; `tB`
#   dokumu seri porta HIC basmiyor, gövdeyi kartin kendi HTTP ucuna
#   birakiyor. Kopru ise karta USB'den bagli — kartin WiFi'si kapali bile
#   olabilir. Cevirmeseydik kopru kendi `t`sini yollamak zorunda kalir ve
#   kart IKI KEZ yakalardi (biri bosa, ustelik ikisi farkli dalga).
SKOP_KOMUTLARI = {"t", "tB", "ta"}

# Canli yakalamanin tavani. Kartin kendi yakalama zaman asimi
# `pencere_ms * 1.2 + 300`; ustune ASCII dokumun seri porttan gecisi
# geliyor: 4000 ornek ~20 250 B, 115 200 baud'da ~1.8 s. 20 s arayuzun
# `osiloBekliyor` tavaniyla AYNI — arayuz vazgectikten sonra donen bir
# yanit kullaniciya hicbir sey soylemezdi.
SKOP_BEKLE_SN = 20.0


def lan_ip() -> str:
    """Disari bakan arayuzun IP'si. Paket gondermeden ogreniyor."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Kopru:
    """Yukari-akis ile aboneler arasindaki durum. HTTP'den bagimsiz."""

    def __init__(self, kart, arsiv_dizini: Path):
        self.kart = kart
        self.arsiv = Arsiv(arsiv_dizini)
        self.aboneler: list[queue.Queue] = []
        self.kilit = threading.Lock()
        self.jetonlar: dict[str, float] = {}
        self.surucu: str | None = None
        self.calisiyor = False
        self.son_satir = ""
        self.satir_adedi = 0
        self.arsiv_hatasi: str | None = None
        # ── skop yakalama (B35) ──────────────────────────────────────
        # 🔴 KOPRU KIPINDE SKOP HIC CALISMIYORDU. Arayuz `TasiyiciAkis`
        #    icin `skop: 'ikili'` ilan ediyor ve `/skop.bin` cekiyor;
        #    sayfa kopruden geldiginde o istek KOPRUYE gidiyor, kopru de
        #    `arayuz3/`yi servis ettigi icin 404 donuyordu. Yani tam da
        #    kullanicinin "sekilleri gormek + kayit almak" istedigi kipte
        #    osiloskop olu bir dugmeydi.
        #    Cozum: kopru `t` (ASCII dokum) gonderip blogu seri akistan
        #    toplar ve KARTIN BICIMINDE ikili dondurur. Firmware
        #    degismiyor, role bayt-seffaf kaliyor, ve dokum `Serial`den
        #    gectigi icin AYNI ANDA arsive de duser — kayit ozelligi
        #    bunun yan urunu.
        self.skop_cozucu = SkopCozucu()
        self.skop_son: dict | None = None
        self.skop_hata: str | None = None
        self.skop_olay = threading.Event()
        self.skop_kilit = threading.Lock()      # tek anda tek yakalama
        self.skop_kurulu = False    # arayuz komutu yolladi, cevap bekleniyor
        self.skop_adedi = 0

    # ── abonelik ─────────────────────────────────────────────────────
    def abone_ol(self) -> queue.Queue:
        k = queue.Queue(maxsize=2000)
        with self.kilit:
            self.aboneler.append(k)
        return k

    def abonelikten_cik(self, k: queue.Queue) -> None:
        with self.kilit:
            if k in self.aboneler:
                self.aboneler.remove(k)

    def yayinla(self, satir: str) -> None:
        with self.kilit:
            hedefler = list(self.aboneler)
        for k in hedefler:
            try:
                k.put_nowait(satir)
            except queue.Full:
                # 🔴 YAVAS ISTEMCI OTEKILERI YAVASLATAMAZ. Kuyruk dolarsa
                #    o istemcinin satiri DUSER; blokla beklemek koprunun
                #    tamamini o istemcinin hizina indirirdi — kartin
                #    `loop()`'unu bloklamamak icin kuruldugumuz seyin
                #    aynisini PC'de tekrarlamak olurdu.
                pass

    # ── jeton / surucu ───────────────────────────────────────────────
    def jeton_ver(self) -> str:
        j = secrets.token_urlsafe(12)
        with self.kilit:
            self.jetonlar[j] = time.time()
            if self.surucu is None:
                self.surucu = j          # ilk baglanan surucu olur
        return j

    def surucu_mu(self, jeton: str | None) -> bool:
        return bool(jeton) and jeton == self.surucu

    def devral(self, jeton: str) -> bool:
        with self.kilit:
            if jeton not in self.jetonlar:
                return False
            self.surucu = jeton
        return True

    def komut_izinli(self, komut: str, jeton: str | None) -> tuple[bool, str]:
        if komut in SERBEST_KOMUTLAR:
            return True, ""
        if self.surucu is None:
            return True, ""
        if self.surucu_mu(jeton):
            return True, ""
        return False, ("bu oturum SURUCU degil — komut reddedildi. "
                       "`p0` (durdur) her zaman acik.")

    # ── yukari-akis dongusu ──────────────────────────────────────────
    def dongu(self) -> None:
        self.calisiyor = True
        while self.calisiyor:
            try:
                satir = self.kart.satir_oku(0.5)
            except Exception as e:                      # noqa: BLE001
                self.yayinla(f"! kopru: kart okunamadi — {e}")
                time.sleep(1.0)
                continue
            if satir is None:
                continue
            self.son_satir = satir
            self.satir_adedi += 1
            # 🔴 ARSIV HATASI ROLEYI OLDUREMEZ. Onceden `yaz()` bir kez
            #    atinca bu iplik olup gidiyordu: kopru ayakta gorunur,
            #    ama ne arsiv ne SSE calisirdi ve HICBIR YERDE yazmazdi.
            #    Rolenin kendisi kritik islev; arsiv onemli ama ikincil.
            #    Sebep bir kez akisa basiliyor — sessiz kalmiyor.
            try:
                ms = self.arsiv.yaz(satir)
            except Exception as e:                        # noqa: BLE001
                ms = 0
                if not self.arsiv_hatasi:
                    self.arsiv_hatasi = str(e)
                    self.yayinla(f"! kopru: arsive yazilamiyor — {e}")
            self.skop_besle(satir, ms)
            self.yayinla(satir)

    def skop_besle(self, satir: str, ms: int = 0) -> None:
        """Yukari-akis satirini skop cozucusune ver.

        ⚠ ARSIVDEN SONRA, YAYINDAN ONCE cagriliyor ve satiri
          DEGISTIRMIYOR — role bayt-seffafligi bozulmuyor.
        """
        # Kart tetikleyemediyse bekleyeni hemen serbest birak; 20 s
        # bosuna beklemek kullaniciya "sanki calisiyor" hissi verirdi.
        if satir.startswith("! tetiklenemedi"):
            self.skop_hata = "kart tetikleyemedi"
            self.skop_olay.set()
            return
        blok = self.skop_cozucu.besle(satir, ms)
        if blok is not None:
            blok["gun"] = time.strftime("%Y-%m-%d")
            self.skop_son = blok
            self.skop_adedi += 1
            self.skop_olay.set()

    def skop_hazirla(self) -> None:
        """Yakalama komutu karta RELAY EDILMEDEN once cagriliyor.

        Arayuz once `/komut` ile `tB` yolluyor, 400 ms sonra `/skop.bin`
        cekiyor. Kopru komutu tanidiginda "bu yakalamanin cevabini
        bekliyorum" diye isaretleniyor; `/skop.bin` o zaman KENDI `t`sini
        yollamiyor, gelmekte olani bekliyor. Isaretlenmeseydi kart iki kez
        yakalar, arayuze DONEN dalga kullanicinin tetikledigi dalga
        OLMAZDI.
        """
        self.skop_olay.clear()
        self.skop_hata = None
        self.skop_son = None
        self.skop_cozucu.sifirla()
        self.skop_kurulu = True

    def skop_yakala(self, bekle: float = SKOP_BEKLE_SN) -> tuple[dict | None, str]:
        """Yakalamayi getir. (blok, hata) donduruyor.

        Arayuz komutu zaten yolladiysa (`skop_kurulu`) YALNIZCA bekliyor;
        yollamadiysa (curl, betik) kendisi `t` tetikliyor. Iki yolda da
        dokum `Serial`den gectigi icin yakalama ARSIVE de dusuyor —
        "geriye donuk kayit" ozelligi bunun yan urunu.
        """
        with self.skop_kilit:
            kendi_tetikledi = not self.skop_kurulu
            if kendi_tetikledi:
                self.skop_hazirla()
                try:
                    self.kart.yaz("t")
                except Exception as e:                    # noqa: BLE001
                    self.skop_kurulu = False
                    return None, f"karta yazilamadi: {e}"
            self.skop_kurulu = False
            if not self.skop_olay.wait(bekle):
                return None, f"kart {bekle:.0f} s icinde yakalama dondurmedi"
            if self.skop_hata:
                return None, self.skop_hata
            blok = self.skop_son
            if blok is None:
                return None, "blok toplanamadi"
            # Kirpik blok CIZILMIYOR: eksik dalga "olculmus" gibi
            # gorunurdu ve tekrar denemek ucuz.
            if not blok["tam"]:
                return None, (f"blok kirpik ({len(blok['ornek'])}/"
                              f"{blok['adet_bildirilen']} ornek)")
            return blok, ""

    def durdur(self) -> None:
        self.calisiyor = False
        self.arsiv.kapat()


class Isleyici(http.server.SimpleHTTPRequestHandler):
    kopru: Kopru = None                                  # sinif duzeyinde

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ARAYUZ), **k)

    def log_message(self, bicim, *args):
        if "--ayrintili" in sys.argv:
            super().log_message(bicim, *args)

    # ── yardimcilar ──────────────────────────────────────────────────
    def _jeton(self) -> str | None:
        return self.headers.get("X-Jeton")

    def _yanit(self, kod: int, govde: bytes = b"", tip="text/plain"):
        self.send_response(kod)
        self.send_header("Content-Type", tip + "; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if govde:
            self.wfile.write(govde)

    # ── GET ──────────────────────────────────────────────────────────
    def _sorgu(self) -> dict:
        parca = self.path.split("?", 1)
        if len(parca) < 2:
            return {}
        return {a: d[0] for a, d in urllib.parse.parse_qs(parca[1]).items()}

    def do_GET(self):
        yol = self.path.split("?")[0]
        if yol == "/akis":
            return self._akis()
        if yol == "/durum":
            return self._durum()
        if yol == "/skop.bin":
            return self._skop_canli()
        if yol == "/skop/liste":
            return self._skop_liste()
        if yol == "/skop/al":
            return self._skop_al()
        return super().do_GET()

    def _durum(self):
        k = self.kopru
        d = {
            "kart": k.kart.ad,
            "satir": k.satir_adedi,
            "abone": len(k.aboneler),
            "arsiv_satir": k.arsiv.satir_adedi,
            "surucu_var": k.surucu is not None,
            # Arayuz KOPRUDE mi KARTTA mi oldugunu bundan anliyor: kart
            # `/durum` ucunu HIC acmiyor, yani bu alanin varligi zaten
            # koprunun imzasi. Ayri bir "kopru misin" ucu acmak ikinci
            # bir gercek kaynagi olurdu.
            "skop_arsiv": True,
            "skop_adedi": k.skop_adedi,
        }
        self._yanit(200, json.dumps(d).encode("utf-8"), "application/json")

    # ── skop (B35) ───────────────────────────────────────────────────
    def _skop_canli(self):
        """Kartin `/skop.bin` ucunun kopru karsiligi — AYNI BICIM.

        Arayuz hangi tasiyicida oldugunu bilmek zorunda kalmasin diye
        yol da, bicim de, imza da kartinkiyle ayni. `/komut` ucunde
        alinan kararin aynisi (bkz. dosya basligi).
        """
        k = self.kopru
        blok, hata = k.skop_yakala()
        if blok is None:
            return self._yanit(503, hata.encode("utf-8"))
        govde = skop_ikili(blok)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        # Yakalamanin arsivdeki kimligi — arayuz "bu kayit listede hangisi"
        # sorusunu ek istek atmadan yanitlayabilsin.
        self.send_header("X-Skop-Gun", str(blok.get("gun", "")))
        self.send_header("X-Skop-Ms", str(blok.get("ms", 0)))
        self.end_headers()
        self.wfile.write(govde)

    def _skop_liste(self):
        k = self.kopru
        s = self._sorgu()
        gunler = k.arsiv.gunler()
        gun = s.get("gun") or (gunler[-1] if gunler else None)
        # Gunluge yazilani okuyacagiz; henuz diske inmemis satirlar
        # listede gorunmezdi ("az once cektim, listede yok").
        k.arsiv.flush()
        kayitlar = k.arsiv.skop_ozet(gun) if gun else []
        kayitlar.reverse()                       # en yenisi basta
        d = {"gunler": gunler, "gun": gun, "kayitlar": kayitlar}
        self._yanit(200, json.dumps(d).encode("utf-8"), "application/json")

    def _skop_al(self):
        k = self.kopru
        s = self._sorgu()
        gun, ms = s.get("gun"), s.get("ms")
        if not gun or ms is None or not ms.lstrip("-").isdigit():
            return self._yanit(400, "gun ve ms gerekli".encode("utf-8"))
        k.arsiv.flush()
        blok = k.arsiv.skop_bul(gun, int(ms))
        if blok is None:
            return self._yanit(404, "yakalama bulunamadi".encode("utf-8"))
        govde = skop_ikili(blok)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _akis(self):
        k = self.kopru
        jeton = self._jeton() or k.jeton_ver()
        kuyruk = k.abone_ol()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            # Once kimlik: istemci jetonu saklayip komutlarda gonderiyor.
            self.wfile.write(b"retry: 3000\n\n")
            self._olay("kimlik", json.dumps(
                {"jeton": jeton, "surucu": k.surucu_mu(jeton)}))
            while True:
                try:
                    satir = kuyruk.get(timeout=15.0)
                except queue.Empty:
                    # Kalp atisi: NAT ve ara vekiller sessiz baglantiyi
                    # dusuruyor. Yorum satiri istemciye gorunmuyor.
                    self.wfile.write(b": kalp\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(b"data: " + satir.encode("utf-8") + b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            k.abonelikten_cik(kuyruk)

    def _olay(self, ad: str, veri: str):
        self.wfile.write(f"event: {ad}\ndata: {veri}\n\n".encode("utf-8"))
        self.wfile.flush()

    # ── POST ─────────────────────────────────────────────────────────
    def do_POST(self):
        yol = self.path.split("?")[0]
        if yol == "/komut":
            return self._komut()
        if yol == "/devral":
            return self._devral()
        self._yanit(404, b"bilinmeyen uc")

    def _govde(self) -> str:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n).decode("utf-8", "replace").strip()

    def _komut(self):
        k = self.kopru
        # 🔴 Ozel baslik SART. Capraz kokende preflight'a zorluyor ve
        #    <img>/<form> ozel baslik EKLEYEMEZ — yani bir web sayfasi
        #    kullaniciya fark ettirmeden komut gonderemiyor.
        if self.headers.get("X-Olcum") != "1":
            return self._yanit(400, "X-Olcum basligi gerekli".encode("utf-8"))
        metin = self._govde()
        if not metin:
            return self._yanit(400, b"bos komut")
        izin, neden = k.komut_izinli(metin, self._jeton())
        if not izin:
            return self._yanit(403, neden.encode("utf-8"))
        # Yakalama komutuysa: cozucuyu hazirla ve `tB`yi `t`ye cevir
        # (gerekcesi SKOP_KOMUTLARI'nin yaninda).
        if metin in SKOP_KOMUTLARI:
            k.skop_hazirla()
            if metin == "tB":
                metin = "t"
        try:
            k.kart.yaz(metin)
        except Exception as e:                            # noqa: BLE001
            return self._yanit(502, f"karta yazilamadi: {e}".encode("utf-8"))
        # Yanit GOVDESI BOS: kartin cevabi zaten SSE'den geliyor. Govdede
        # de dondurmek ayni satirin arayuzde IKI KEZ islenmesi olurdu.
        self._yanit(204)

    def _devral(self):
        k = self.kopru
        if self.headers.get("X-Olcum") != "1":
            return self._yanit(400, "X-Olcum basligi gerekli".encode("utf-8"))
        jeton = self._jeton()
        if not jeton or not k.devral(jeton):
            return self._yanit(403, "bilinmeyen oturum".encode("utf-8"))
        k.yayinla("* kopru: surucu degisti")
        self._yanit(204)


class Sunucu(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    # 🔴 ISTEMCININ BAGLANTIYI KOPARMASI HATA DEGIL, NORMAL. SSE acik bir
    #    sekme kapaninca / sayfa yenilenince soket koparilir ve
    #    `handle_one_request` keep-alive okumasinda patlar. Varsayilan
    #    `handle_error` bunun icin konsola 25 satirlik yigin izi basiyordu:
    #    kullanici her sekme yenilemesinde "bir sey bozuldu" sanirdi ve
    #    GERCEK bir iz bu gurultunun icinde kaybolurdu.
    #    ⚠ YALNIZCA kopma ailesi susturuluyor; baska her istisna aynen
    #      basiliyor — "hatalari gizle" degil, "hata olmayani hata diye
    #      gostermeyi birak".
    SESSIZ = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError,
              TimeoutError)

    def handle_error(self, istek, istemci_adresi):
        if isinstance(sys.exc_info()[1], self.SESSIZ):
            return
        super().handle_error(istek, istemci_adresi)
    # Windows'ta allow_reuse_address BASKA bir surecin aktif tuttugu portu
    # ele gecirmeye izin verir; yedek porta dusme hic tetiklenmez.
    # (stok-takip'in konsol.py'sinde de ayni not var.)
    if sys.platform == "win32":
        allow_reuse_address = False


def sunucu_kur(kopru: Kopru):
    Isleyici.kopru = kopru
    ip = lan_ip()
    for adres, port in (("0.0.0.0", PORT), (ip, PORT), ("0.0.0.0", YEDEK_PORT)):
        try:
            return Sunucu((adres, port), Isleyici), adres, port, ip
        except OSError:
            continue
    raise SystemExit(f"{PORT} ve {YEDEK_PORT} mesgul.")


def main() -> int:
    arg = sys.argv[1:]

    def secenek(ad, varsayilan=None):
        return arg[arg.index(ad) + 1] if ad in arg else varsayilan

    kayit = secenek("--kayit")
    if kayit:
        satirlar = [s.split("\t", 1)[-1].rstrip("\n")
                    for s in Path(kayit).read_text(encoding="utf-8").splitlines()]
        kart = kart_baglanti.KayitKart(satirlar, gecikme=0.2)
    else:
        kart = kart_baglanti.SeriKart(secenek("--port"))

    try:
        kart.ac()
    except RuntimeError as e:
        print(f"Karta baglanilamadi: {e}")
        print("Portlar:", ", ".join(kart_baglanti.portlari_listele()) or "(yok)")
        return 1

    kopru = Kopru(kart, KOK / "kopru" / "arsiv")
    threading.Thread(target=kopru.dongu, daemon=True).start()

    sunucu, adres, port, ip = sunucu_kur(kopru)
    ek = "" if port == 80 else f":{port}"
    print(f"Kopru acildi — kart: {kart.ad}")
    # 🔴 HER IKI SATIRDA DA LAN IP'si — `127.0.0.1` YAZILMIYOR.
    #    Windows'ta 0.0.0.0:80 baglamasi, 127.0.0.1:80 BASKA bir surec
    #    tarafindan tutuluyorken de BASARILI olabiliyor (SO_EXCLUSIVEADDRUSE
    #    kullanilmamissa). O durumda hangi sunucunun cevap verecegi HEDEF
    #    ADRESE bagli: 127.0.0.1 daha ozel baglamaya, yani stok-takip'e
    #    gider; kopruye yalnizca LAN IP'sinden ulasilir. "127.0.0.1" yazmak
    #    kullaniciyi yanlis sunucuya yollardi — bu makinede tam olarak oyle
    #    oldu ve stok arayuzu acildi.
    print(f"  Bu bilgisayardan : http://{ip}{ek}")
    print(f"  Telefondan       : http://{ip}{ek}"
          f"   (yonlendiricide DHCP rezervasyonu yapin, adres degismesin)")
    print(f"  Arsiv            : {kopru.arsiv.dizin}")
    print("Kapatmak icin Ctrl+C")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nkapatiliyor…")
    finally:
        kopru.durdur()
        kart.kapat()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
