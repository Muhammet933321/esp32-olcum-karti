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
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"

sys.path.insert(0, str(BURASI))
from arsiv import Arsiv                                   # noqa: E402
import kart_baglanti                                      # noqa: E402

# stok-takip 127.0.0.1:80'i tutuyor (ayarlar.PORT = 80, Windows acilisinda
# arka planda basliyor). LAN arayuzundeki 80 bos; oradan da olmazsa 8770.
PORT = 80
YEDEK_PORT = 8770

# Her taşımada, jetonsuz, kimliksiz gecen komutlar.
SERBEST_KOMUTLAR = {"p0"}


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
            self.arsiv.yaz(satir)
            self.yayinla(satir)

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
    def do_GET(self):
        if self.path.split("?")[0] == "/akis":
            return self._akis()
        if self.path.split("?")[0] == "/durum":
            return self._durum()
        return super().do_GET()

    def _durum(self):
        k = self.kopru
        d = {
            "kart": k.kart.ad,
            "satir": k.satir_adedi,
            "abone": len(k.aboneler),
            "arsiv_satir": k.arsiv.satir_adedi,
            "surucu_var": k.surucu is not None,
        }
        self._yanit(200, json.dumps(d).encode("utf-8"), "application/json")

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
