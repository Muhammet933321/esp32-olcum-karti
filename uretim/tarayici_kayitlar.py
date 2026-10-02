# -*- coding: utf-8 -*-
"""3C — KAYITLAR TARAYICIDA (T3C): sahte karta karsi uctan uca.

    python tarayici_kayitlar.py                    # sessiz, 0/1 doner
    python tarayici_kayitlar.py --goruntu DIZIN    # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B7 (`test_arayuz3.js` bolum 24) saf mantigi node'da
   sinar; IndexedDB'yi, gercek fare olaylarini, indirmeyi, Vue'nun calisma
   anini, uc gorunumu ve telefon genisligini SINAYAMAZ. Burada gercek
   headless Edge (CDP), gercek Vue, gercek modul yukleyicisi ve PYTHON
   SAHTE KART var: arayuz3 + `/ortak/` + `/kayit/liste` + `/kayit/veri`
   (`test_kayit_esp._SahteKart` — B72.E'nin sahtesi) + `/kal/liste` +
   `/komut` (gelen `Go` onaylari sayilir) + `/akis` (SSE, jeton).

Sayfa `http://olcum.test:<port>/` adresinden acilir (Edge
`--host-resolver-rules` ile 127.0.0.1): kartin sayfasi gibi localhost DISI
ve GUVENLI BAGLAM DISI (Web Locks yok, kart CORS'u yok) — panel kendiliginden
akis kipine gecip karta baglanir, Kayitlar ayni kokenden esitler (C1).

Oturumlar `kopru/kayit_bicim.py` paketleyicileriyle: ad/etiket/notlu olcum
(sicrama, bos nokta, YUKSEK, DURAKLAMA), pil (OLAY: ayar/DCIR/sonuc),
ayrintili, osiloskop (tam + eksik yakalama), saatsiz (unix 0), sonra karttan
silinen bir oturum. Beklenen degerler BAGIMSIZ Python hesabindan
(`ortak_vektor_disari.py` islevleri: nokta_satirlari, sayi_yaz, olcekli,
iso) — sayfanin kendi hesabiyla karsilastirilsaydi test kendini dogrulardi.
"""
from __future__ import annotations

import bisect
import hashlib
import http.server
import json
import math
import shutil
import struct
import sys
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"
ORTAK = KOK / "ortak" / "src"
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kayit_bicim as KB                                    # noqa: E402
import ortak_vektor_disari as OV                            # noqa: E402
import test_kayit_esp as T                                  # noqa: E402
from tarayici_tema import KayitliTarayici, bos_port, css_takimlari, rgb, TEMALAR  # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
AD = "olcum.test"
JETON = "abc123"
gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> bool:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))
    return kosul


# ── oturumlar (kopru/kayit_bicim.py paketleyicileri) ─────────────────────
def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def kanal(n: float) -> KB.Kanal:
    return KB.Kanal(f32(n), f32(4.096), f32(1.0), 12, 0.0)


KAL = KB.Kalibrasyon(kanal(21.0), kanal(201.0), 5, f32(0.256), f32(0.1), f32(1.0), 0.0, (0.0, 0.0))


def kal_json(no: int) -> dict:
    k = KAL
    kn = lambda c: {"n": c.n, "pga": c.pga, "kazanc": c.kazanc, "sifir_ham": c.sifir_ham, "tau": c.tau}  # noqa: E731
    return {"no": no, "unix": 1789000000 + no, "acilis": no, "tur": 1, "kaynak": 2, "not": "sahte",
            "kal": {"normal": kn(k.normal), "yuksek": kn(k.yuksek), "i_ofset": k.i_ofset, "i_pga": k.i_pga,
                    "sont_ohm": k.sont_ohm, "i_duzeltme": k.i_duzeltme, "sebeke_hz": k.sebeke_hz,
                    "faz0": 0.0, "faz1": 0.0}}


class Akis:
    def __init__(self, sira0: int = 0):
        self.sira = sira0
        self.kayitlar: list[bytes] = []

    def ekle(self, tur: int, oturum: int, yuk: bytes) -> int:
        self.sira += 1
        self.kayitlar.append(KB.kayit_paketle(tur, self.sira, oturum, yuk))
        return self.sira

    def basla(self, tur, hiz, unix, kart, acilis) -> int:
        return self.ekle(KB.T_BASLA, self.sira + 1, KB.basla_paketle(
            KB.Basla(tur, 1, hiz, unix, kart, acilis, "A3-3C", KAL, kal_no=2)))

    def noktalar(self, ot: int, ilk: int, ns: list) -> None:
        for j in range(0, len(ns), 6):
            self.ekle(KB.T_NOKTA, ot, struct.pack("<I", ilk + j) + b"".join(KB.nokta_paketle(p) for p in ns[j:j + 6]))

    def not_(self, ot: int, alan: int, ms: int, metin: str) -> None:
        self.ekle(KB.T_NOT, 0, KB.not_paketle(ot, alan, ms, 0, metin.encode("utf-8")))

    def bitir(self, ot: int, n: int, sebep: int) -> None:
        self.ekle(KB.T_BITIR, ot, struct.pack("<IB3x", n, sebep))


def nokta(ms: int, v: float, i: float, w: float, bayrak: int = 0, sic: int = 0, n: int = 40) -> KB.Nokta:
    if n == 0:
        return KB.Nokta(ms, 0, KB.KN_V_HATA | KB.KN_I_HATA, 0.0, 0, 0, 0.0, 0, 0, 0.0, 0.0, 0.0)
    vi = int(round(v))
    ii = int(round(i))
    return KB.Nokta(ms, n, bayrak, f32(v), vi - 40, min(32767, vi + 60 + sic), f32(i), ii - 5, ii + 7,
                    f32(w), f32(w - 0.3), f32(w + 0.4))


def akis_kur() -> tuple[Akis, dict]:
    a = Akis(10)
    no = {}
    # F: en eski oturum — ilk esitlemeden sonra KARTTAN SILINIR (akilli temizlik)
    no["F"] = a.basla(1, 1000, 1789990000, 1000, 2)
    a.noktalar(no["F"], 0, [nokta(1000 + 1000 * (k + 1), 9000 + k, 500, 2.0) for k in range(20)])
    a.not_(no["F"], KB.KNT_AD, 0, "silinecek oturum")
    a.bitir(no["F"], 20, 1)
    # A: olcum 200 ms, ad + etiket + iki not; sicrama yalniz MAKS'ta (Ö1), bos nokta, YUKSEK, DURAKLAMA
    no["A"] = a.basla(1, 200, 1790000000, 5000, 3)
    ns = []
    for k in range(300):
        v = 12000 + 2500 * math.sin(k / 23.0) + 7 * (k % 5)
        i = 2000 + 600 * math.cos(k / 31.0)
        w = v * i * 1e-6
        if k == 40:
            ns.append(nokta(5000 + 200 * (k + 1), 0, 0, 0, n=0))
            continue
        if k == 60:                       # YUKSEK menzil: kod yuksek kanalin bolucusune gore (gerilim surekli)
            v = (v - 12) * 21.0 / 201.0 + 12
        ns.append(nokta(5000 + 200 * (k + 1), v, i, w,
                        bayrak=KB.KN_YUKSEK if k == 60 else KB.KN_DURAKLAMA if k == 61 else 0,
                        sic=4000 if k == 150 else 0))
    a.noktalar(no["A"], 0, ns)
    a.not_(no["A"], KB.KNT_AD, 0, "Akü şarj — deneme")
    a.not_(no["A"], KB.KNT_ETIKET, 0, "akü, şarj, 12V")
    a.not_(no["A"], KB.KNT_NOT, 0, "genel not")
    a.not_(no["A"], KB.KNT_NOT, 5000 + 200 * 101, "dalgalanma başladı")
    a.bitir(no["A"], 300, 1)
    # B: pil testi 500 ms, OLAY ayar / DCIR / sonuc
    no["B"] = a.basla(2, 500, 1790001000, 90000, 3)
    a.ekle(KB.T_OLAY, no["B"], KB.olay_paketle({"tur": KB.KO_PIL_AYAR, "kart_ms": 90001, "kesme_v": 3.0,
                                                 "ocv": 4.1, "azami_s": 36000, "dcir_aralik_ms": 3000,
                                                 "dcir_ms": 200, "kayit_hz": 2.0}))
    pn = [nokta(90000 + 500 * (k + 1), 1900 - 4 * k, 1000, 1.9 - 0.004 * k) for k in range(120)]
    a.noktalar(no["B"], 0, pn[:60])
    a.ekle(KB.T_OLAY, no["B"], KB.olay_paketle({"tur": KB.KO_DCIR, "kart_ms": 120100, "no": 1, "v_once": 3.9,
                                                 "i_once": 1.0, "v_ani": 3.8, "v_oturmus": 3.75, "r_ani": 0.1,
                                                 "r_oturmus": 0.15, "mah": 8.3, "wh": 0.03}))
    a.noktalar(no["B"], 60, pn[60:])
    a.ekle(KB.T_OLAY, no["B"], KB.olay_paketle({"tur": KB.KO_PIL_SONUC, "kart_ms": 150100, "durum": 2,
                                                 "hata": 0, "mah": 16.6, "wh": 0.061, "ocv": 4.1, "v_son": 3.0,
                                                 "sure_ms": 60000, "dcir_sayisi": 1}))
    a.not_(no["B"], KB.KNT_AD, 0, "Li-ion 18650 #2")
    a.bitir(no["B"], 120, 4)
    # C: ayrintili (hiz 0)
    no["C"] = a.basla(1, 0, 1790002000, 200000, 3)
    s = 0
    for j, (ms, us, b) in enumerate([(200003, 200003417, 0), (200103, 200103120, KB.KA_SILME),
                                     (200203, 200203999, KB.KA_KAYIP_ONCE)]):
        orn = [(1000 + 13 * k + j, 200 + k, 0 if k == 0 else 500, KB.KAO_V_HATA if k == 7 else 0) for k in range(40)]
        a.ekle(KB.T_AYRINTI, no["C"], KB.ayrinti_paketle({"ilk": s, "t0_ms": ms, "t0_us": us, "ornekler": orn, "bayrak": b}))
        s += 40
    a.bitir(no["C"], s, 1)
    # D: osiloskop gunlugu: bir tam (iki parca) + bir eksik yakalama
    no["D"] = a.basla(3, 1000, 1790003000, 300000, 3)
    meta = {"t_ms": 300100, "sure_ms": 13, "hz": 10000, "tdiv_us": 1000, "adim": 0.03, "ofset": 1.5,
            "tetik": 32, "esik": 2048, "histerezis": 8, "kip": 0, "tetiklendi": 1, "kenar": 0, "on_yuzde": 25, "onay": 2}
    a.ekle(KB.T_SKOP, no["D"], KB.skop_paketle({"no": 1, "ilk": 0, "toplam": 128, "parca": 0, "meta": meta,
                                                 "kodlar": [2048 + 20 * k for k in range(64)]}))
    a.ekle(KB.T_SKOP, no["D"], KB.skop_paketle({"no": 1, "ilk": 64, "toplam": 128, "parca": 1,
                                                 "kodlar": [3328 - 20 * k for k in range(64)]}))
    a.ekle(KB.T_SKOP, no["D"], KB.skop_paketle({"no": 2, "ilk": 0, "toplam": 128, "parca": 0,
                                                 "meta": {**meta, "t_ms": 301100}, "kodlar": [100] * 64}))
    a.bitir(no["D"], 0, 1)
    # E: saatsiz (unix 0)
    no["E"] = a.basla(1, 1000, 0, 7000, 5)
    a.noktalar(no["E"], 0, [nokta(7000 + 1000 * (k + 1), 3000 + 3 * k, 300, 0.27) for k in range(50)])
    a.bitir(no["E"], 50, 1)
    return a, no


def g_ekle(a: Akis, no: dict) -> None:
    """Ilk esitlemeden SONRA kartta beliren oturum."""
    no["G"] = a.basla(1, 1000, 1790005000, 400000, 3)
    a.noktalar(no["G"], 0, [nokta(400000 + 1000 * (k + 1), 5000 + k, 700, 0.5) for k in range(30)])
    a.not_(no["G"], KB.KNT_AD, 0, "yeni kayıt G")
    a.bitir(no["G"], 30, 1)


def yeni_kart_akisi() -> tuple[Akis, int]:
    """Kart bicimlendi: YENI kimlik, sira bastan."""
    a = Akis(0)
    h = a.basla(1, 1000, 1790009000, 1000, 1)
    a.noktalar(h, 0, [nokta(1000 + 1000 * (k + 1), 6000 + k, 100, 0.1) for k in range(20)])
    a.not_(h, KB.KNT_AD, 0, "yeni kart H")
    a.bitir(h, 20, 1)
    return a, h


# ── sahte kart ───────────────────────────────────────────────────────────
class Kart(T._SahteKart):
    """`/kayit/veri` B72.E'nin sahtesi (kg_oku anlami); ustune dizin, kalibrasyon,
    komut ve akis uclari."""

    def __init__(self, kayitlar):
        super().__init__(kayitlar)
        self.veri_istekleri: list[int] = []
        self.tum_komutlar: list[str] = []
        self.liste_kod = 200
        self.imza_zorunlu = False
        self.aktif = 0
        self.kal_liste = {"surum": 1, "adet": 2, "taslak": 0, "etkin": 2, "azami": 40,
                          "kayitlar": [kal_json(1), kal_json(2)]}
        self.kilit = threading.Lock()
        # Gercek kartta (2026-10-02) tarayici esitlemesi bir /kayit/veri baglantisinda
        # ERR_CONNECTION_TIMED_OUT aldi (ESP32'nin soket havuzu; ham Python cekimi hatasiz).
        # kopar = N: sonraki N /kayit/veri istegi YANITSIZ bekletilir (panelin 10 s istek zaman
        # asimini asar) ve koparilir. Hemen kapatmak YETMEZ: Chrome yeniden kullanilan baglanti
        # yanitsiz kapaninca GET'i kendiliginden bir kez tekrarliyor — zaman asimini tekrarlamiyor.
        self.kopar = 0
        self.koparilan = 0

    def dizin(self) -> dict:
        oz: dict[int, dict] = {}
        for ham in self.kayitlar:
            _imza, tur, n, sira, oturum = struct.unpack_from("<BBHII", ham, 0)
            y = ham[16:16 + n]
            if not oturum:
                continue
            o = oz.setdefault(oturum, {"id": oturum, "tur": 0, "hiz_ms": 0, "unix_s": 0, "kart_ms": 0,
                                       "acilis": 0, "ilk": 0, "son": 0, "nokta": 0, "durum": 1,
                                       "basi_silindi": 1})
            if not o["ilk"]:
                o["ilk"] = sira
            o["son"] = sira
            if tur in (KB.T_BASLA, KB.T_TEKRAR) and n >= 20:
                o["tur"] = y[0]
                o["hiz_ms"], o["unix_s"], o["kart_ms"], o["acilis"] = struct.unpack_from("<IIII", y, 4)
                if tur == KB.T_BASLA:
                    o["basi_silindi"] = 0
                    o["nokta"] = 0
            elif tur == KB.T_NOKTA and n >= 4:
                o["nokta"] = struct.unpack_from("<I", y)[0] + (n - 4) // KB.NOKTA_BAYT
            elif tur == KB.T_AYRINTI and n >= 14:
                o["nokta"] = struct.unpack_from("<I", y)[0] + struct.unpack_from("<H", y, 12)[0]
            elif tur == KB.T_DEVAM and n >= 16:
                o["nokta"] = struct.unpack_from("<I", y, 12)[0]
                o["durum"] = 1
            elif tur == KB.T_BITIR:
                o["durum"] = 2
        return {"surum": 2, "durum": 2 if self.aktif else 1, "sektor": 2912, "sektor_bayt": 4096,
                "sonraki": self.sonraki(), "onay": self.onay, "doluluk_binde": 123, "onaysiz_binde": 45,
                "aktif": self.aktif, "acilis": 3, "unix": 1790009999, "kimlik": self.kimlik, "temiz_kalan": 0,
                "oturumlar": list(oz.values())}


MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".png": "image/png", ".json": "application/json"}
DUR = threading.Event()


def sunucu_kur(kart: Kart):
    class Isleyici(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _gonder(self, kod: int, govde: bytes, tur: str = "text/plain; charset=utf-8", ek: dict | None = None):
            self.send_response(kod)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            for a, d in (ek or {}).items():
                self.send_header(a, d)
            self.end_headers()
            self.wfile.write(govde)

        def _dosya(self, yol: str):
            if yol.startswith("/ortak/"):
                ad = yol[len("/ortak/"):]
                p = (ORTAK / ad).resolve()
                if p.parent != ORTAK.resolve() or not p.is_file():
                    return self._gonder(404, b"yok")
            else:
                p = (ARAYUZ / (yol.lstrip("/") or "index.html")).resolve()
                if ARAYUZ.resolve() not in p.parents or not p.is_file():
                    return self._gonder(404, b"yok")
            self._gonder(200, p.read_bytes(), MIME.get(p.suffix, "application/octet-stream"))

        def _imza_reddi(self) -> bool:
            if kart.imza_zorunlu:
                self._gonder(401, "imza gerekli (zorunluluk yalniz USB'den Ez0 ile kapanir)".encode())
                return True
            return False

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/kayit/liste":
                if self._imza_reddi():
                    return
                if kart.liste_kod != 200:
                    return self._gonder(kart.liste_kod, b"kayit mesgul, tekrar dene")
                with kart.kilit:
                    d = kart.dizin()
                return self._gonder(200, json.dumps(d).encode(), "application/json")
            if u.path == "/kayit/veri":
                if self._imza_reddi():
                    return
                sira = int(q.get("sira", ["1"])[0])
                with kart.kilit:
                    kopar = kart.kopar > 0
                    if kopar:
                        kart.kopar -= 1
                        kart.koparilan += 1
                if kopar:
                    DUR.wait(12.0)                   # > panelin istek zaman asimi (10 s)
                    self.close_connection = True
                    try:
                        self.connection.shutdown(2)
                    except OSError:
                        pass
                    return
                with kart.kilit:
                    kart.veri_istekleri.append(sira)
                    govde, ilk, son = kart.veri(sira, int(q.get("bayt", ["8192"])[0]))
                    bas = {"X-Kayit-Kimlik": str(kart.kimlik), "X-Ilk-Sira": str(ilk), "X-Son-Sira": str(son),
                           "X-Sonraki-Sira": str(kart.sonraki()), "X-Onay": str(kart.onay)}
                return self._gonder(200, govde, "application/octet-stream", bas)
            if u.path == "/kal/liste":
                if self._imza_reddi():
                    return
                return self._gonder(200, json.dumps(kart.kal_liste, ensure_ascii=False).encode("utf-8"),
                                    "application/json")
            if u.path == "/akis":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(f'retry: 3000\n\nevent: kimlik\ndata: {{"jeton":"{JETON}","surucu":true}}\n\n'
                                     .encode())
                    self.wfile.flush()
                    while not DUR.is_set():
                        DUR.wait(1.0)
                        self.wfile.write(b": nabiz\n\n")
                        self.wfile.flush()
                except OSError:
                    pass
                self.close_connection = True
                return
            if u.path in ("/durum", "/pil", "/favicon.ico"):
                return self._gonder(404, b"yok")
            return self._dosya(u.path)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            govde = self.rfile.read(n).decode("utf-8", "replace")
            if urllib.parse.urlparse(self.path).path != "/komut":
                return self._gonder(404, b"yok")
            if self.headers.get("X-Olcum") != "1" or self.headers.get("X-Jeton") != JETON:
                return self._gonder(403, b"gecersiz oturum jetonu")
            with kart.kilit:
                kart.tum_komutlar.append(govde)
                cevap = ""
                if govde.startswith("Go"):
                    kart.komutlar.append(govde)
                    kart.onayla(int(govde[2:]))
                    cevap = f"* G onay istegi {int(govde[2:])}\n"
            self._gonder(200, cevap.encode())

    class Sunucu(http.server.ThreadingHTTPServer):
        daemon_threads = True
        block_on_close = False
        allow_reuse_address = False

        def handle_error(self, *a):
            pass

    s = Sunucu(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


# ── bagimsiz Python basvurusu (ortak_vektor_disari islevleri) ────────────
KOLON = {
    "tr": ["sira", "acilis", "devam", "kart_ms", "gecen_ms", "unix_s", "zaman_utc", "n", "v_ort_V", "v_min_V",
           "v_maks_V", "i_ort_A", "i_min_A", "i_maks_A", "w_ort_W", "w_min_W", "w_maks_W", "bayrak",
           "bayraklar", "not"],
    "en": ["seq", "boot", "resumed", "board_ms", "elapsed_ms", "unix_s", "time_utc", "n", "v_avg_V", "v_min_V",
           "v_max_V", "i_avg_A", "i_min_A", "i_max_A", "p_avg_W", "p_min_W", "p_max_W", "flags",
           "flag_names", "note"],
}
BAYRAK = {"tr": [(0x01, "YUKSEK"), (0x02, "V_HATA"), (0x04, "I_HATA"), (0x08, "V_DOYDU"), (0x10, "DURAKLAMA"),
                 (0x20, "KAYIP_ONCE"), (0x40, "DCIR")],
          "en": [(0x01, "HIGH_RANGE"), (0x02, "V_ERROR"), (0x04, "I_ERROR"), (0x08, "V_SATURATED"),
                 (0x10, "PAUSE"), (0x20, "LOSS_BEFORE"), (0x40, "DCIR")]}


def metin_hucre(s: str, ayrac: str) -> str:
    if s and s[0] in "=+-@\t\r":
        s = "'" + s
    if ayrac in s or '"' in s or "\r" in s or "\n" in s:
        s = '"' + s.replace('"', '""') + '"'
    return s


def nokta_csv_py(o: KB.Oturum, dil: str) -> bytes:
    """oturumCsv'nin (Excel-TR / EN) bagimsiz Python karsiligi — DEVAM'siz oturum."""
    ayrac, ondalik = (";", ",") if dil == "tr" else (",", ".")
    satirlar = OV.nokta_satirlari(o)
    notlar: dict[int, list[str]] = {}
    for _s, n in sorted(o.notlar.items()):
        if not n["nokta_ms"]:
            notlar.setdefault(0, []).append(n["metin"])
            continue
        rel = OV.i32(n["nokta_ms"] - o.basla.kart_ms)
        k = next((j for j, r in enumerate(satirlar) if r["rel"] >= rel), len(satirlar) - 1)
        notlar.setdefault(k, []).append(n["metin"])
    say = lambda x: OV.sayi_yaz(x, 6).replace(".", ondalik)  # noqa: E731
    cikti = ["\ufeff" + ayrac.join(KOLON[dil]) + "\r\n"]
    for k, r in enumerate(satirlar):
        devam = "1" if r["acilis"] > 0 and (k == 0 or satirlar[k - 1]["acilis"] != r["acilis"]) else "0"
        adlar = "|".join(a for b, a in BAYRAK[dil] if r["bayrak"] & b)
        h = [str(r["sira"]), str(r["acilis"]), devam, str(r["kart"]),
             "" if r["gecen"] is None else str(r["gecen"]),
             "" if r["unix"] is None else OV.olcekli(r["unix"], 3).replace(".", ondalik),
             "" if r["unix"] is None else metin_hucre(OV.iso(r["unix"]), ayrac), str(r["n"])]
        h += [say(x) for x in r["v"] + r["a"] + r["w"]]
        h += [str(r["bayrak"]), metin_hucre(adlar, ayrac), metin_hucre("\n".join(notlar.get(k, [])), ayrac)]
        cikti.append(ayrac.join(h) + "\r\n")
    return "".join(cikti).encode("utf-8")


def ham_py(kayitlar: list[bytes], ot: int) -> bytes:
    """Oturumun kayitlari + hedefi o olan NOT'lar, sira ile (kartin baytlari aynen)."""
    secilen = []
    for ham in kayitlar:
        _i, tur, n, sira, oturum = struct.unpack_from("<BBHII", ham, 0)
        if oturum == ot or (tur == KB.T_NOT and oturum == 0 and struct.unpack_from("<I", ham, 16)[0] == ot):
            secilen.append((sira, ham))
    return b"".join(h for _s, h in sorted(secilen))


def okuma_py(o: KB.Oturum, ta: float, tb: float) -> dict:
    """Imlec okumasi, BAGIMSIZ: en yakin NaN'siz ornek, aralik ort/min/maks, yamuk mAh/Wh."""
    r = OV.nokta_satirlari(o)
    bosluk = o.basla.hiz_ms * 2.5
    t = [x["gecen"] for x in r]
    nan = math.isnan

    def yakin(y, x):
        i = bisect.bisect_left(t, x)
        sag = i
        while sag < len(t) and nan(y[sag]):
            sag += 1
        sol = i - 1
        while sol >= 0 and nan(y[sol]):
            sol -= 1
        if sol >= 0 and sag < len(t):
            return y[sol] if x - t[sol] <= t[sag] - x else y[sag]
        return y[sol] if sol >= 0 else y[sag]

    ic = [k for k in range(len(t)) if ta <= t[k] <= tb]

    def integral(deger, gecerli):
        top, onceki = [], None
        for k in ic:
            if not gecerli(k):
                continue
            if onceki is not None and t[k] - t[onceki] <= bosluk:
                top.append((deger(onceki) + deger(k)) * (t[k] - t[onceki]) / 2)
            onceki = k
        return math.fsum(top)

    v = [x["v"][0] for x in r]
    i_ = [x["a"][0] for x in r]
    w = [x["w"][0] for x in r]
    vg = [k for k in ic if not nan(v[k])]
    return {
        "va": yakin(v, ta), "vb": yakin(v, tb), "ia": yakin(i_, ta), "ib": yakin(i_, tb),
        "vort": math.fsum(v[k] for k in vg) / len(vg),
        "vmin": min(r[k]["v"][1] for k in ic if not nan(r[k]["v"][1])),
        "vmaks": max(r[k]["v"][2] for k in ic if not nan(r[k]["v"][2])),
        "mah": integral(lambda k: i_[k], lambda k: not nan(v[k]) and not nan(i_[k])) / 3600.0,
        "wh": integral(lambda k: w[k], lambda k: not nan(w[k])) / 3_600_000.0,
    }


def yakin_mi(a, b, tol=1e-9) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b))


# ── tarayici yardimcilari ────────────────────────────────────────────────
class Kopuk(Exception):
    """Ust uste bekleme zaman asimi: sayfa artik beklenen akista degil — erken, SAYILARAK bitis."""


ZAMAN_ASIMI = [0]


def bekle_js(t, ifade: str, sure: float = 12.0):
    """`ifade` dogru olana dek bekle. Saglikli kosuda hicbir bekleme zaman asimina ugramaz;
    UC zaman asimi ust uste gelirse (bozuk kod, mutasyon) kalan evreler anlamsiz: Kopuk."""
    son = time.monotonic() + sure
    deger = None
    while time.monotonic() < son:
        try:
            deger = t.js(ifade)
        except RuntimeError:
            deger = None
        if deger:
            ZAMAN_ASIMI[0] = 0
            return deger
        t.bekle(0.2)
    ZAMAN_ASIMI[0] += 1
    if ZAMAN_ASIMI[0] >= 3:
        raise Kopuk(ifade[:80])
    return deger


def fare(t, tur: str, x: float, y: float, tik: int = 0) -> None:
    p = {"type": tur, "x": x, "y": y, "button": "left" if tur != "mouseMoved" else "none", "clickCount": tik}
    t.cagir("Input.dispatchMouseEvent", p)


def cift_tikla(t, x: float, y: float) -> None:
    fare(t, "mouseMoved", x, y)
    for tik in (1, 2):
        fare(t, "mousePressed", x, y, tik)
        fare(t, "mouseReleased", x, y, tik)


SATIRLAR_JS = ("[...document.querySelectorAll('.kl-satir')].map(a => ({o: +a.dataset.oturum, k: +a.dataset.kimlik,"
               " n: a.dataset.nerede, m: a.textContent.replace(/\\s+/g, ' ').trim()}))")

IDB_JS = """(async () => {
  const vt = await new Promise((c, r) => { const q = indexedDB.open('olcum-kayit'); q.onsuccess = () => c(q.result); q.onerror = () => r(q.error); });
  const g = (r) => new Promise((c, e) => { r.onsuccess = () => c(r.result); r.onerror = () => e(r.error); });
  const tx = vt.transaction(['akis', 'parca'], 'readonly');
  const akislar = await g(tx.objectStore('akis').getAll());
  const out = {};
  for (const a of akislar) {
    const ps = await g(tx.objectStore('parca').getAll(IDBKeyRange.bound([a.kimlik, 0], [a.kimlik, Number.MAX_SAFE_INTEGER])));
    let hex = '';
    for (const p of ps) for (const b of p.veri) hex += b.toString(16).padStart(2, '0');
    out[a.kimlik] = { bayt: a.bayt, durum: a.durum, parca: ps.length, hex, kal: !!a.kal };
  }
  vt.close();
  return out;
})()"""

DEPO_SOZLESME_JS = """(async () => {
  const D = await import('/ekran/depo_idb.js');
  const vt = await D.vtAc();
  const K = 990001;
  await D.akisSil(vt, K);
  await D.akisHazirla(vt, K);
  const d = D.idbDepo(vt, K);
  const r = {};
  r.durumIlk = await d.durumOku();
  const buyuk = new Uint8Array(150000).map((_, i) => (i * 7) & 255);
  await d.veriEkle(new Uint8Array([1, 2, 3, 4, 5]));
  await d.veriEkle(buyuk);
  r.boy = await d.veriBoyu();
  const tum = await d.veriOku(0);
  r.okuTamam = tum.length === 150005 && tum[0] === 1 && tum[4] === 5 && tum.slice(5).every((x, i) => x === ((i * 7) & 255));
  const orta = await d.veriOku(70000);
  r.ortaTamam = orta.length === 80005 && orta[0] === ((69995 * 7) & 255);
  await d.veriKirp(70000);
  r.kirpBoy = await d.veriBoyu();
  r.kirpTamam = (await d.veriOku(69998)).length === 2;
  await d.veriKirp(70010);
  const uz = await d.veriOku(69999);
  r.uzatSifir = uz.length === 11 && uz.slice(1).every((x) => x === 0);
  await d.durumYaz({ son_sira: 9, bayt: 12, onaylanan: 0, kimlik: K, ek: 'x' });
  r.durum = await d.durumOku();
  await d.kalYaz(new TextEncoder().encode('{"a":1}'));
  r.kal = new TextDecoder().decode(await d.kalOku());
  r.arsiv1 = await d.kalArsivle(new Uint8Array([1]));
  r.arsiv2 = await d.kalArsivle(new Uint8Array([2]));
  const b1 = await d.kilitAl();
  try { await d.kilitAl(); r.kilit = 'ikinci alindi'; } catch (e) { r.kilit = e.name; }
  await b1();
  const b2 = await d.kilitAl(); await b2();
  r.webLocks = !!(navigator.locks);
  r.guvenli = window.isSecureContext;
  await D.akisSil(vt, K);
  r.silindi = !(await D.akislar(vt)).some((a) => a.kimlik === K);
  return r;
})()"""


def piksel_say(t, renkler: list) -> list:
    return t.js("""(() => {
      const c = document.querySelector('canvas.kg-grafik');
      if (!c || !c.width) return null;
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      const h = %s; const s = h.map(() => 0);
      for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 250) continue;
        for (let j = 0; j < h.length; j++) if (Math.abs(d[i] - h[j][0]) <= 6 && Math.abs(d[i + 1] - h[j][1]) <= 6
          && Math.abs(d[i + 2] - h[j][2]) <= 6) s[j]++; }
      return s; })()""" % json.dumps(renkler))


def tema_sec(t, ad: str) -> None:
    yazi = ["Koyu", "Açık", "Ön panel"][TEMALAR.index(ad)]
    t.js("[...document.querySelectorAll('button')].find(x => x.textContent.trim() === %s).click()" % json.dumps(yazi))
    t.bekle(0.6)


def tasma(t) -> int:
    """Yatay tasma (px). 🔴 `innerWidth` KULLANILMAZ: telefon emulasyonunda (mobile) icerik
    tasinca Chrome `innerWidth`i icerik genisligine buyutuyor (390 -> 549 olculdu) ve
    `scrollWidth - innerWidth` 0 kaliyordu — tasma mutasyonu KACTI. `clientWidth` yerlesim
    genisliginde (390) kalir."""
    return t.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def indir_bekle(dizin: Path, ad: str, sure: float = 10.0) -> bytes | None:
    son = time.monotonic() + sure
    p = dizin / ad
    while time.monotonic() < son:
        if p.exists() and not any(dizin.glob("*.crdownload")):
            time.sleep(0.2)
            return p.read_bytes()
        time.sleep(0.2)
    return None


# ── ana akis ─────────────────────────────────────────────────────────────
def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    takim = css_takimlari()
    akis, no = akis_kur()
    kart = Kart(list(akis.kayitlar))
    s = sunucu_kur(kart)
    port = s.server_address[1]
    taban = f"http://{AD}:{port}"
    indirme = Path(tempfile.mkdtemp(prefix="olcum-indir-"))
    resimler = []
    print("=" * 78)
    print("  3C  KAYITLAR — TARAYICIDA, SAHTE KARTA KARSI (T3C)")
    print("=" * 78)
    print(f"     sahte kart: {taban}  ({len(kart.kayitlar)} kayit, kimlik {kart.kimlik})\n")

    def resim(ad: str, tam: bool = False) -> None:
        if not goruntu:
            return
        t.js("window.scrollTo(0, 0)")
        t.bekle(0.3)
        y = goruntu / f"{ad}.png"
        if tam:                           # butun sayfa (kayit gorunumunun alt bolumleri)
            m = t.cagir("Page.getLayoutMetrics")["cssContentSize"]
            r = t.cagir("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                                   "clip": {"x": 0, "y": 0, "width": m["width"],
                                                            "height": min(m["height"], 6000), "scale": 1}})
            import base64
            y.write_bytes(base64.b64decode(r["data"]))
        else:
            t.goruntu(str(y))
        resimler.append(y)

    beklenen_hata = []          # [yol, bas, son]: bu evrede (olay indisleri) beklenen ag hatalari
    try:
        with KayitliTarayici(auth_iptal=False, port=bos_port(),
                             ek_arg=[f"--host-resolver-rules=MAP {AD} 127.0.0.1"]) as t:
            t.cagir("Log.enable")
            t.tema("dark")
            try:
                t.cagir("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(indirme),
                                                        "eventsEnabled": False})
            except RuntimeError:
                t.cagir("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(indirme)})

            # ── 1. ilk acilis: otomatik baglanti + otomatik esitleme ──────
            t.git(taban + "/#/kayitlar")
            satir = bekle_js(t, f"document.querySelectorAll('.kl-satir').length >= 6 && {SATIRLAR_JS}"
                                f".every(s => s.n === 'ikisi') && document.querySelectorAll('.kl-satir').length")
            acildi = t.js("!document.querySelector('#uyg').hasAttribute('v-cloak')") is True
            ok("[!] Panel kartin adresinden (localhost DISI, guvenli baglam DISI) acildi, Vue basladi",
               acildi and t.js("window.isSecureContext") is False, t.js("location.origin"))
            ok("[!] Panel kendiliginden akis kipine gecti ve karta BAGLANDI (jeton)",
               t.js(f"{UYG}.tasiyiciAdi") == "akis" and t.js(f"{UYG}.bagli") is True)
            satirlar = t.js(SATIRLAR_JS) or []
            ilk_son = max(struct.unpack_from("<I", h, 4)[0] for h in akis.kayitlar)
            ok("[!] Otomatik esitleme: alti oturum listede, HEPSI 'ikisinde'",
               len(satirlar) == 6 and all(x["n"] == "ikisi" for x in satirlar),
               " ".join(f"{x['o']}:{x['n']}" for x in satirlar))
            veri1 = list(kart.veri_istekleri)
            ok("[!] Ilk esitleme sira 1'den basladi, kartin butun kayitlarini aldi",
               bool(veri1) and veri1[0] == 1 and max(veri1) >= ilk_son, f"istek sira: {veri1[:3]}…{veri1[-2:]}")
            idb = t.js(IDB_JS) or {}
            k7 = idb.get(str(kart.kimlik)) or idb.get(kart.kimlik) or {}
            kart_hex = b"".join(akis.kayitlar).hex()
            ok("[!] IndexedDB'deki akis kartin baytlariyla BAYT BAYT ayni; durum son sira ve kimlik dogru",
               k7.get("hex") == kart_hex and k7.get("bayt") == len(kart_hex) // 2
               and (k7.get("durum") or {}).get("son_sira") == ilk_son
               and (k7.get("durum") or {}).get("kimlik") == kart.kimlik and k7.get("kal") is True,
               f"{k7.get('bayt')} B, {k7.get('parca')} parca, durum {k7.get('durum')}")
            ok("[!] C3 VARSAYILAN: karta HIC onay (Go) gitmedi; kartin onayi 0",
               not any(c.startswith("Go") for c in kart.tum_komutlar) and kart.onay == 0,
               f"komutlar: {kart.tum_komutlar}")
            metinler = {x["o"]: x["m"] for x in satirlar}
            ok("Satirlarda ad, etiketler, saatsiz oturum 'saat yok', tur adlari",
               "Akü şarj — deneme" in metinler.get(no["A"], "") and "12V" in metinler.get(no["A"], "")
               and "saat yok" in metinler.get(no["E"], "") and "Pil testi" in metinler.get(no["B"], "")
               and "Osiloskop" in metinler.get(no["D"], "") and "ayrıntılı" in metinler.get(no["C"], ""),
               metinler.get(no["A"], ""))
            resim("1-liste-koyu")

            # ── 2. arama ve suzgec (gercek input olaylari) ──────────────
            def ara(q: str) -> list:
                t.js("(() => { const i = document.querySelector('.kl-ara'); i.value = %s;"
                     " i.dispatchEvent(new Event('input')); })()" % json.dumps(q))
                t.bekle(0.3)
                return [x["o"] for x in t.js(SATIRLAR_JS)]

            def suz(sira: int, deger: str) -> list:
                t.js("(() => { const s = document.querySelectorAll('.kl-suzgec select')[%d]; s.value = %s;"
                     " s.dispatchEvent(new Event('change')); })()" % (sira, json.dumps(deger)))
                t.bekle(0.3)
                return [x["o"] for x in t.js(SATIRLAR_JS)]

            a1, a2, a3, a4 = ara("AKU"), ara("sarj 12v"), ara("#" + str(no["B"])), ara("dalgalanma")
            ara("")
            s1 = suz(0, "pil")
            s2 = suz(0, "olcum")
            suz(0, "hepsi")
            s3 = suz(1, "kart")
            suz(1, "hepsi")
            ok("[!] Arama Turkce duyarsiz (AKU -> Akü), etiket, not metni, #numara; suzgec tur ve nerede",
               a1 == [no["A"]] and a2 == [no["A"]] and a3 == [no["B"]] and a4 == [no["A"]]
               and s1 == [no["B"]] and no["C"] in s2 and no["B"] not in s2 and s3 == [],
               f"aku={a1} 12v={a2} #B={a3} not={a4} pil={s1} olcum={s2} kart={s3}")

            # ── 3. kart temizledi + yeni oturum: nerede; yenileme IDB'den ─
            def f_mi(h: bytes) -> bool:            # basligin oturumu (ofset 8) ya da NOT hedefi F
                tur, ot = h[1], struct.unpack_from("<I", h, 8)[0]
                return ot == no["F"] or (tur == KB.T_NOT and ot == 0 and struct.unpack_from("<I", h, 16)[0] == no["F"])

            n0 = len(akis.kayitlar)
            g_ekle(akis, no)
            with kart.kilit:
                kart.kayitlar = [h for h in kart.kayitlar if not f_mi(h)] + akis.kayitlar[n0:]
            t.js("[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Yenile').click()")
            bekle_js(t, f"{SATIRLAR_JS}.some(s => s.o === {no['G']})")
            nerede = {x["o"]: x["n"] for x in t.js(SATIRLAR_JS)}
            ok("[!] Kartin dizininden silinen oturum 'yalnız bu tarayıcıda', karttaki yeni oturum 'yalnız kartta'",
               nerede.get(no["F"]) == "tarayici" and nerede.get(no["G"]) == "kart" and nerede.get(no["A"]) == "ikisi",
               str(nerede))
            t.js(f"location.hash = '#/kayit/{no['G']}'")
            uyari = bekle_js(t, "(document.querySelector('[data-kl-acilmadi]') || {}).textContent")
            ok("C5: yalniz kartta olan kayit acilmiyor, 'once esitleyin' diyor", "önce eşitleyin" in (uyari or ""),
               uyari or "")
            t.js("history.back()")
            bekle_js(t, "location.hash === '#/kayitlar' && document.querySelectorAll('.kl-satir').length > 0")

            veri_once = len(kart.veri_istekleri)
            kart.liste_kod = 503
            hata_sinir = len(t.olaylar)
            evre_503 = ["/kayit/liste", hata_sinir, None]
            beklenen_hata.append(evre_503)
            t.cagir("Page.reload", {"ignoreCache": True})          # ayni URL'ye git = belge ici; GERCEK yenileme
            t.bekle(0.5)
            bekle_js(t, "document.querySelectorAll('.kl-satir').length >= 6 && !!document.querySelector('.kl-neden')")
            yeniden = t.js(SATIRLAR_JS) or []
            neden = t.js("(document.querySelector('.kl-neden') || {}).dataset && document.querySelector('.kl-neden').dataset.neden")
            ok("[!] Sayfa yenilenince veri INDEXEDDB'den: kart mesgulken (503) bile 6 oturum, hic /kayit/veri istegi yok",
               len(yeniden) == 6 and len(kart.veri_istekleri) == veri_once and neden == "mesgul"
               and any("Akü şarj" in x["m"] for x in yeniden),
               f"{len(yeniden)} satir, neden={neden}, yeni istek {len(kart.veri_istekleri) - veri_once}")
            kart.liste_kod = 200
            t.js("document.querySelector('.kl-esitle') ? 0 : [...document.querySelectorAll('button')]"
                 ".find(b => b.textContent.trim() === 'Yenile').click()")
            bekle_js(t, "!!document.querySelector('.kl-esitle')")
            kart.kopar = 2                           # ikinci esitlemede iki baglanti yanitsiz kopar
            t.js("document.querySelector('.kl-esitle').click()")
            bekle_js(t, f"{SATIRLAR_JS}.some(s => s.o === {no['G']} && s.n === 'ikisi')", 60.0)
            evre_503[2] = len(t.olaylar)               # 503 evresi burada kapanir
            ikinci = kart.veri_istekleri[veri_once:]
            ok("[!] Ikinci esitleme YALNIZ yeni kayitlari cekti (her istek sira > ilk esitlemenin son sirasi)",
               bool(ikinci) and min(ikinci) == ilk_son + 1 and 1 not in ikinci,
               f"ilk son {ilk_son}, ikinci istekler {ikinci}")
            sonuc = t.js("(document.querySelector('.kl-sonuc') || {}).textContent") or ""
            ok("Esitleme sonucu yaziliyor (yeni kayit sayisi)", "yeni kayıt alındı" in sonuc, sonuc)
            idb2 = t.js(IDB_JS) or {}
            k72 = idb2.get(str(kart.kimlik)) or idb2.get(kart.kimlik) or {}
            ok("[!] Ag kopmasi: iki /kayit/veri istegi 12 s yanitsiz kaldi (zaman asimi), esitleme YENIDEN DENEYEREK "
               "tamamlandi; IndexedDB kartla bayt bayt ayni (gercek kartta 2026-10-02 goruldu)",
               kart.koparilan == 2 and kart.kopar == 0 and "yeni kayıt alındı" in sonuc
               and (k72.get("hex") or "").endswith(b"".join(kart.kayitlar).hex())
               and not (t.js("(document.querySelector('.kl-neden') || {}).textContent") or "").strip(),
               f"koparilan {kart.koparilan}, {k72.get('bayt')} B, kart akisi IDB'nin sonu: "
               f"{(k72.get('hex') or '').endswith(b''.join(kart.kayitlar).hex())}, sonuc {sonuc!r}")

            # ── 4. arsiv secimi: onay panelin komut yolundan ─────────────
            t.js("document.querySelector('.kl-arsiv input').click()")
            son_sira = max(struct.unpack_from("<I", h, 4)[0] for h in kart.kayitlar)
            bekle_js(t, f"(document.querySelector('.kl-sonuc') || {{}}).textContent.includes('doğruladı')")
            ok("[!] C3: 'bu tarayıcı arşivdir' secilince Go<son sira> komut yolundan gitti, kart dogruladi",
               f"Go{son_sira}" in kart.tum_komutlar and kart.onay == son_sira
               and t.js(f"localStorage.getItem('olcum.arsiv.{kart.kimlik}')") == "true",
               f"komutlar {[c for c in kart.tum_komutlar if c.startswith('Go')]}, onay {kart.onay}")

            # ── 5. kimlik degisti: yeni akis, eskisi kalir ────────────────
            go_sayi = sum(1 for c in kart.tum_komutlar if c.startswith("Go"))
            eski_kimlik = kart.kimlik
            yeni, no["H"] = yeni_kart_akisi()
            with kart.kilit:
                kart.kimlik = 9
                kart.kayitlar = list(yeni.kayitlar)
                kart.onay = 0
            t.js("[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Yenile').click()")
            bekle_js(t, "!!document.querySelector('.kl-esitle')")
            t.js("document.querySelector('.kl-esitle').click()")
            bekle_js(t, f"{SATIRLAR_JS}.some(s => s.k === 9 && s.n === 'ikisi')")
            ss = t.js(SATIRLAR_JS) or []
            idb2 = t.js(IDB_JS) or {}
            eski_say = sum(1 for x in ss if x["k"] == eski_kimlik and "eski kart kopyası" in x["m"])
            ok("[!] C2: kimlik degisince YENI akis (9) — eski akis (7) silinmedi, oturumlari 'eski kart kopyası'",
               set(idb2) == {str(eski_kimlik), "9"} and idb2["9"]["hex"] == b"".join(yeni.kayitlar).hex()
               and idb2[str(eski_kimlik)]["hex"].startswith(kart_hex[:200]) and eski_say == 7
               and ss[0]["k"] == 9, f"akislar {sorted(idb2)}, eski satir {eski_say}")
            ok("[!] C3: arsiv secimi KART basina — yeni kimlikte kapali, yeni akis icin onay GITMEDI",
               sum(1 for c in kart.tum_komutlar if c.startswith("Go")) == go_sayi
               and t.js("document.querySelector('.kl-arsiv input').checked") is False)
            ok("Bu tarayicidaki kopyalar bolumu iki akisi gosteriyor (guncel + eski)",
               t.js("document.querySelectorAll('.kl-kopya').length") == 2)

            # ── 6. kayit gorunumu: tuval, gercek fare ile iki imlec ──────
            t.js(f"location.hash = '#/kayit/{no['A']}@{eski_kimlik}'")
            bekle_js(t, "!!document.querySelector('canvas.kg-grafik') && !!document.querySelector('.kg-tuval').dataset.pencere")
            koyu = takim["koyu"]
            t_cizim = time.monotonic()               # sabit uyku YOK: en gec 8 s icinde cizilmeli
            px = None
            while time.monotonic() - t_cizim < 8.0:
                px = piksel_say(t, [list(rgb(koyu["--volt"])), list(rgb(koyu["--amper"]))])
                if px and px[0] > 80 and px[1] > 80:
                    break
                t.bekle(0.1)
            ok("[!] Kayit acilinca tuval GERCEKTEN cizili (--volt ve --amper pikselleri), en gec 8 s",
               bool(px) and px[0] > 80 and px[1] > 80,
               f"volt {px and px[0]} amper {px and px[1]}, {time.monotonic() - t_cizim:.2f} s")
            t.js("document.querySelector('canvas.kg-grafik').scrollIntoView({block: 'center'})")
            t.bekle(0.3)
            r = t.js("(() => { const c = document.querySelector('canvas.kg-grafik'); const b = c.getBoundingClientRect();"
                     " return {x: b.left, y: b.top, w: b.width, h: b.height, sol: c.clientLeft, ust: c.clientTop}; })()")
            p = json.loads(t.js("document.querySelector('.kg-tuval').dataset.pencere"))
            yv = r["y"] + r["h"] / 2
            beklenen = []
            for oran in (0.27, 0.71):
                ox = p["alanX"] + oran * p["alanW"]
                cift_tikla(t, r["x"] + r["sol"] + ox, yv)
                t.bekle(0.3)
                beklenen.append(p["t0"] + (ox - p["alanX"]) / p["alanW"] * (p["t1"] - p["t0"]))
            t.bekle(0.4)
            p2 = json.loads(t.js("document.querySelector('.kg-tuval').dataset.pencere"))
            okj = t.js("document.querySelector('.kg-okuma').dataset.okuma")
            okuma = json.loads(okj) if okj else {}
            px_t = (p["t1"] - p["t0"]) / p["alanW"]
            ok("[!] Gercek fare (CDP cift tik) ile A ve B imlecleri tiklanan piksele kondu",
               p2.get("imlecA") is not None and p2.get("imlecB") is not None
               and abs(p2["imlecA"] - beklenen[0]) <= 1.5 * px_t and abs(p2["imlecB"] - beklenen[1]) <= 1.5 * px_t,
               f"A {p2.get('imlecA')} ~ {beklenen[0]:.1f}, B {p2.get('imlecB')} ~ {beklenen[1]:.1f}")
            ot7 = KB.oturumlari_kur(KB.akis_coz(b"".join(akis.kayitlar[:])))
            oA = ot7[no["A"]]
            if okuma.get("tA") is not None:
                py = okuma_py(oA, okuma["tA"], okuma["tB"])
                v, i_ = okuma.get("v") or {}, okuma.get("i") or {}
                e = okuma.get("enerji") or {}
                esler = [("V(A)", v.get("a"), py["va"]), ("V(B)", v.get("b"), py["vb"]), ("I(A)", i_.get("a"), py["ia"]),
                         ("I(B)", i_.get("b"), py["ib"]), ("ort V", v.get("ort"), py["vort"]),
                         ("min V", v.get("min"), py["vmin"]), ("maks V", v.get("maks"), py["vmaks"]),
                         ("mAh", e.get("mah"), py["mah"]), ("Wh", e.get("wh"), py["wh"]),
                         ("dV", okuma.get("dV"), py["vb"] - py["va"])]
                kotu = [f"{a}: {b} != {c}" for a, b, c in esler if not yakin_mi(b, c)]
                ok("[!] Okuma (V/I degerleri, ort, min/maks, dV, mAh, Wh) BAGIMSIZ Python hesabiyla ayni (1e-9)",
                   not kotu and py["mah"] > 0 and py["wh"] > 0, "; ".join(kotu) or
                   f"V {v.get('a'):.4f}->{v.get('b'):.4f} mAh {e.get('mah'):.6f} Wh {e.get('wh'):.8f}")
            else:
                ok("[!] Okuma (V/I degerleri, ort, min/maks, dV, mAh, Wh) BAGIMSIZ Python hesabiyla ayni (1e-9)", False,
                   "okuma yok")
            resim("2-kayit-koyu", tam=True)

            # not: tikla -> grafik o ana
            t.js("[...document.querySelectorAll('.kg-not')].find(b => b.textContent.includes('dalgalanma')).click()")
            t.bekle(0.5)
            p3 = json.loads(t.js("document.querySelector('.kg-tuval').dataset.pencere"))
            not_x = OV.i32(5000 + 200 * 101 - oA.basla.kart_ms)
            ok("[!] Nota tiklayinca grafik penceresi notun anina ortalandi",
               abs((p3["t0"] + p3["t1"]) / 2 - not_x) < 1.0 and (p3["t1"] - p3["t0"]) < (p["t1"] - p["t0"]),
               f"orta {(p3['t0'] + p3['t1']) / 2:.1f} ~ {not_x}")

            # ── 7. disa aktarma: indirme baytlari Python basvurusuyla ────
            def indir(tur: str, ad: str) -> bytes | None:
                yol = indirme / ad
                if yol.exists():
                    yol.unlink()
                t.js(f"document.querySelector('[data-disari=\"{tur}\"]').click()")
                return indir_bekle(indirme, ad)

            kok = f"kayit-{no['A']}-aku-sarj-deneme"
            tr_b = indir("csv_tr", kok + ".csv")
            en_b = indir("csv_en", kok + "-en.csv")
            ham_b = indir("ham", kok + ".kyt")
            ok("[!] CSV (Excel-TR) indirmesi Python basvurusuyla BAYT BAYT ayni (BOM, ;, ondalik virgul)",
               tr_b is not None and tr_b == nokta_csv_py(oA, "tr"),
               f"{len(tr_b or b'')} B" + ("" if tr_b == nokta_csv_py(oA, "tr") else " FARKLI"))
            ok("[!] CSV (EN) indirmesi Python basvurusuyla BAYT BAYT ayni",
               en_b is not None and en_b == nokta_csv_py(oA, "en"), f"{len(en_b or b'')} B")
            ok("[!] Ham .kyt indirmesi = kartin o oturuma ait baytlari (NOT'lar dahil) aynen",
               ham_b is not None and ham_b == ham_py(akis.kayitlar, no["A"]), f"{len(ham_b or b'')} B")

            # ── 8. rapor: yazdirilabilir gorunum ─────────────────────────
            t.js("document.querySelector('.kg-bag').click()")
            bekle_js(t, "!!document.querySelector('.kg-rapor table')")
            vmaks_py = max(x["v"][2] for x in OV.nokta_satirlari(oA) if not math.isnan(x["v"][2]))
            hucre = t.js("[...document.querySelectorAll('.kg-rapor tbody tr')][0].children[3].textContent")
            ok("[!] Rapor acildi (#/.../rapor); V en yuksek hucresi ham min/maks kodlarindan (Python)",
               t.js("location.hash").endswith("/rapor") and hucre == f"{vmaks_py:.4f}", f"{hucre} ~ {vmaks_py:.4f}")
            # 3D: kabuk sol serit (#serit) + dar ekranin ust cubugu (.ust). Ekranda serit GORUNUR
            # olmali (yoksa "yazdirmada gizli" iddiasi bos kalirdi), yazdirmada hepsi gizli.
            ekranda = t.js("getComputedStyle(document.querySelector('#serit')).display")
            t.cagir("Emulation.setEmulatedMedia", {"media": "print"})
            t.bekle(0.4)
            yazdir = t.js("({ust: getComputedStyle(document.querySelector('.ust')).display,"
                          " serit: getComputedStyle(document.querySelector('#serit')).display,"
                          " nav: getComputedStyle(document.querySelector('.gorunum-nav')).display,"
                          " rapor: getComputedStyle(document.querySelector('.kg-rapor')).display,"
                          " dugme: getComputedStyle(document.querySelector('.kg-ust')).display})")
            resim("3-rapor-yazdir")
            t.cagir("Emulation.setEmulatedMedia", {"media": ""})
            t.tema("dark")
            ok("Yazdirmada kabuk (serit + ust cubuk) ve dugmeler gizli, rapor gorunur",
               ekranda != "none" and yazdir["ust"] == "none" and yazdir["serit"] == "none" and yazdir["nav"] == "none"
               and yazdir["dugme"] == "none" and yazdir["rapor"] != "none", f"ekranda {ekranda} · {yazdir}")
            # K6: tarayicinin yazdirma olaylari (emulasyon bunlari atmaz — olay elle)
            tema_once = t.js("document.documentElement.dataset.tema")
            t.js("window.dispatchEvent(new Event('beforeprint'))")
            t.bekle(0.3)
            tema_baski = t.js("document.documentElement.dataset.tema")
            pxb = piksel_say(t, [list(rgb(takim["acik"]["--volt"])), list(rgb(takim[tema_once]["--volt"]))])
            t.js("window.dispatchEvent(new Event('afterprint'))")
            t.bekle(0.3)
            tema_sonra = t.js("document.documentElement.dataset.tema")
            ok("[!] K6: yazdirma ONCESI rapor Acik gorunume gecer (tuval acik renkle cizili), SONRA eski gorunum doner",
               tema_once == "koyu" and tema_baski == "acik" and bool(pxb) and pxb[0] > 50 and pxb[1] == 0
               and tema_sonra == "koyu" and t.js("localStorage.getItem('olcum.tema')") in (None, '"sistem"'),
               f"{tema_once} -> {tema_baski} -> {tema_sonra}, pikseller {pxb}")
            t.js("history.back()")
            bekle_js(t, f"location.hash === '#/kayit/{no['A']}@{eski_kimlik}' && !!document.querySelector('canvas.kg-grafik')")
            t.js("history.back()")
            geri = bekle_js(t, "location.hash === '#/kayitlar' && document.querySelectorAll('.kl-satir').length > 0")
            ok("[!] Geri tusu: rapor -> kayit -> liste", bool(geri), t.js("location.hash"))

            # ── 8b. pil ozeti ve osiloskop yakalama tablosu ──────────────
            t.js(f"location.hash = '#/kayit/{no['B']}@{eski_kimlik}'")
            pil = bekle_js(t, "(() => { const h = [...document.querySelectorAll('h2')].find(x => x.textContent === 'Pil testi özeti');"
                              " if (!h) return null; const k = h.parentElement;"
                              " return {kpi: k.querySelector('.kg-kpiler').textContent.replace(/\\s+/g, ' '),"
                              " dcir: k.querySelectorAll('tbody tr').length,"
                              " disari: [...document.querySelectorAll('[data-disari]')].map(b => b.dataset.disari).join(',')}; })()")
            ok("[!] Pil oturumu: ozet kutusu (ayar + sonuc: bitti, mAh) ve DCIR tablosu; pil CSV secenekleri",
               bool(pil) and "bitti" in pil["kpi"] and "16.6" in pil["kpi"] and "3.000" in pil["kpi"]
               and pil["dcir"] == 1 and pil["disari"] == "pil_tr,pil_en,ham", str(pil))
            t.js(f"location.hash = '#/kayit/{no['D']}@{eski_kimlik}'")
            tablo = bekle_js(t, "document.querySelectorAll('tr[data-sira]').length && [...document.querySelectorAll('tr[data-sira]')]"
                                ".map(r => ({s: +r.dataset.sira, m: r.textContent.replace(/\\s+/g, ' '),"
                                " csv: !!r.querySelector('[data-disari=\"skop\"]')}))")
            ok("[!] Osiloskop oturumu: yakalama TABLOSU (tam + eksik), CSV yalniz tam yakalamada; grafik yok (3E)",
               bool(tablo) and len(tablo) == 2 and [x["csv"] for x in tablo] == [True, False]
               and "eksik" in tablo[1]["m"] and t.js("!document.querySelector('canvas.kg-grafik')") is True, str(tablo))
            if tablo:
                skop_o = ot7[no["D"]]
                y = skop_o.skoplar[tablo[0]["s"]]
                m_ = y["meta"]
                beklenen_skop = ("\ufeffornek;t_s;kod;v_V\r\n" + "".join(
                    f"{i};{OV.sayi_yaz((i - m_['tetik']) / m_['hz'], 9).replace('.', ',')};{kod};"
                    f"{OV.sayi_yaz(kod * m_['adim'] - m_['ofset'], 6).replace('.', ',')}\r\n"
                    for i, kod in enumerate(y["kodlar"]))).encode("utf-8")
                ad = f"kayit-{no['D']}-yakalama-{y['no']}-{tablo[0]['s']}.csv"
                if (indirme / ad).exists():
                    (indirme / ad).unlink()
                t.js("document.querySelector('tr[data-sira] [data-disari=\"skop\"]').click()")
                skop_b = indir_bekle(indirme, ad)
                ok("[!] Yakalama CSV'si (Excel-TR) Python basvurusuyla BAYT BAYT ayni",
                   skop_b is not None and skop_b == beklenen_skop, f"{ad}: {len(skop_b or b'')} B")
            t.js("location.hash = '#/kayitlar'")
            bekle_js(t, "document.querySelectorAll('.kl-satir').length > 0")

            # ── 9. uc gorunum + telefon genisligi ────────────────────────
            onceki = "koyu"
            for ad in TEMALAR:
                tema_sec(t, ad)
                ok(f"{ad}: liste render (satirlar var), yatay tasma yok",
                   t.js("document.querySelectorAll('.kl-satir').length") >= 8 and tasma(t) <= 0)
                resim(f"4-liste-{ad}")
            t.js(f"location.hash = '#/kayit/{no['A']}@{eski_kimlik}'")
            bekle_js(t, "!!document.querySelector('canvas.kg-grafik') && document.querySelector('canvas.kg-grafik').width > 0")
            t.bekle(0.5)
            for ad in TEMALAR:
                tema_sec(t, ad)
                d = takim[ad]
                px = piksel_say(t, [list(rgb(d["--volt"]))] + ([list(rgb(takim[onceki]["--volt"]))] if ad != onceki else []))
                ok(f"[!] {ad}: kayit tuvali YENI --volt rengiyle yeniden cizildi"
                   + (f", eski ({onceki}) renk yok" if ad != onceki else ""),
                   bool(px) and px[0] > 50 and (ad == onceki or px[1] == 0),
                   f"{px}")
                resim(f"5-kayit-{ad}", tam=True)
                onceki = ad
            t.ekran(390, 844)
            t.bekle(0.8)
            for ad in TEMALAR:
                tema_sec(t, ad)
                t.js(f"location.hash = '#/kayit/{no['A']}@{eski_kimlik}'")
                bekle_js(t, "!!document.querySelector('canvas.kg-grafik')")
                t.bekle(0.4)
                kayit_tasma = tasma(t)
                resim(f"6-telefon-kayit-{ad}", tam=True)
                t.js("location.hash = '#/kayitlar'")
                bekle_js(t, "document.querySelectorAll('.kl-satir').length > 0")
                t.bekle(0.3)
                liste_tasma = tasma(t)
                resim(f"6-telefon-liste-{ad}")
                ok(f"[!] {ad}: 390 px telefonda liste ve kayit gorunumu YATAY TASMIYOR",
                   kayit_tasma <= 0 and liste_tasma <= 0, f"kayit {kayit_tasma} px, liste {liste_tasma} px")
            t.cagir("Emulation.clearDeviceMetricsOverride")
            tema_sec(t, "koyu")

            # ── 10. C1: baska adresteki karta bagli panel esitlemez ──────
            # taban DOLU (ayni kart, acik adres): C1 kurali adrese degil "taban dolu mu"ya bakar; baska
            # bir ad cozulmez ve pil yoklamasi konsola ag hatasi dusururdu.
            t.js(f"{UYG}.kartTaban = location.origin")
            neden = bekle_js(t, "(document.querySelector('.kl-neden') || {dataset: {}}).dataset.neden === 'taban'"
                                " && !document.querySelector('.kl-esitle') && document.querySelector('.kl-neden').textContent")
            ok("[!] C1: kartTaban doluyken esitleme dugmesi YOK, 'kartın adresinden açın' yaziyor",
               bool(neden) and "kartın adresinden açın" in neden, neden or "")
            t.js(f"{UYG}.kartTaban = ''")
            # on kosul donunce ekran kendiliginden esitler: BITMESINI bekle (yoksa sonraki evre ona karisir)
            bekle_js(t, "!!document.querySelector('.kl-esitle') && !document.querySelector('.kl-esitle').disabled")

            # ── 11. 401 imza gerekli ─────────────────────────────────────
            evre_401 = [[y, len(t.olaylar), None] for y in ("/kayit/liste", "/kayit/veri", "/kal/liste")]
            beklenen_hata.extend(evre_401)
            kart.imza_zorunlu = True
            t.js("[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Yenile').click()")
            imza = bekle_js(t, "(document.querySelector('.kl-neden') || {dataset: {}}).dataset.neden === 'imza'"
                               " && document.querySelector('.kl-neden').textContent")
            ok("[!] 401 'imza gerekli': 'Kart imza istiyor — bu tarayıcıyı eşleştirmek Ayarlar'da (3H)', liste yerelden",
               bool(imza) and "Kart imza istiyor — bu tarayıcıyı eşleştirmek Ayarlar'da (3H)" in imza
               and t.js("document.querySelectorAll('.kl-satir').length") >= 8, imza or "")
            kart.imza_zorunlu = False
            for e in evre_401:
                e[2] = len(t.olaylar)

            # ── 12. IndexedDB deposunun sozlesmesi (gercek IDB) ──────────
            r = t.js(DEPO_SOZLESME_JS) or {}
            ok("[!] Gercek IndexedDB deposu: parca parca ekle/oku/kirp/uzat, durum, kalibrasyon, arsiv adi, sekme kilidi",
               r.get("durumIlk") == {"son_sira": 0, "bayt": 0, "onaylanan": 0, "kimlik": 990001}
               and r.get("boy") == 150005 and r.get("okuTamam") and r.get("ortaTamam") and r.get("kirpBoy") == 70000
               and r.get("kirpTamam") and r.get("uzatSifir") and (r.get("durum") or {}).get("ek") == "x"
               and r.get("kal") == '{"a":1}' and r.get("arsiv1") != r.get("arsiv2")
               and r.get("kilit") == "CalismaHatasi" and r.get("silindi") is True
               and r.get("webLocks") is False and r.get("guvenli") is False, json.dumps(r)[:300])

            # ── 12b. C8: Ingilizce (3H secicisi gelene dek localStorage) ──
            t.js("localStorage.setItem('olcum.dil', JSON.stringify('en'))")
            t.cagir("Page.reload", {"ignoreCache": True})
            t.bekle(0.5)
            en = bekle_js(t, "document.querySelectorAll('.kl-satir').length > 0 && !!document.querySelector('.kl-esitle')"
                             " && !document.querySelector('.kl-esitle').disabled && ({h: [...document.querySelectorAll('.kl h2')]"
                             ".map(h => h.textContent).join('|'), d: document.querySelector('.kl-esitle').textContent.trim(),"
                             " r: document.querySelector('.kl-satir .kl-rozet').textContent})")
            ok("C8: dil 'en' iken ekran sozlugun Ingilizcesiyle (Recordings · Sync · in both)",
               bool(en) and "Recordings" in en["h"] and "Copies in this browser" in en["h"] and en["d"] == "Sync"
               and en["r"] == "in both", str(en))
            t.js("localStorage.removeItem('olcum.dil')")

            # ── 13. konsol ───────────────────────────────────────────────
            hatalar = []
            for i, o in enumerate(t.olaylar):
                if o["tur"] == "hata" or o.get("seviye") == "error":
                    hatalar.append(o["metin"])
                elif o["tur"] == "log":
                    yol = urllib.parse.urlparse(o.get("url", "")).path
                    if yol in ("/durum", "/pil", "/favicon.ico"):
                        continue
                    if any(yol == y and bas <= i < (son if son is not None else 10 ** 9) for y, bas, son in beklenen_hata):
                        continue
                    hatalar.append(o["metin"])
            ok("[!] Butun gezinti boyunca konsol/yukleme hatasi YOK (503/401 evreleri haric)", not hatalar,
               " | ".join(hatalar[:3]) or "temiz")
    except Kopuk as h:
        ok("[!] Sayfa beklenen akista kaldi (ust uste 3 bekleme zaman asimi yok)", False,
           f"son beklenen: {h} — kalan olcumler ATLANDI")
    finally:
        DUR.set()
        s.shutdown()
        s.server_close()
        shutil.rmtree(indirme, ignore_errors=True)

    for y in resimler:
        print(f"     goruntu: {y}")
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
