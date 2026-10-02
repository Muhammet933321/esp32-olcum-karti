# -*- coding: utf-8 -*-
"""3F — PIL TESTI TARAYICIDA (T3F): sahte karta karsi uctan uca.

    python tarayici_pil.py                    # sessiz, 0/1 doner
    python tarayici_pil.py --goruntu DIZIN    # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B7 (`test_arayuz3.js` bolum 27) saf mantigi ve kaynak metnini
   node'da sinar; gercek Vue'yu, gercek SSE akisini, `/pil` yoklamasinin GERCEK istek
   sayisini (sekme gizliyken / test bitince DURUYOR mu), IndexedDB'den geri gelen egriyi,
   tuvalin gercekten cizildigini, `/komut`a giden METNI, esitlenen PIL oturumunu, uc
   gorunumu ve telefon genisligini sinayamaz.

Sahte kart (bu dosyada, Python): arayuz3 + `/ortak/` + `/akis` (SSE: `kimlik`, komut
ciktilari — gercek kart gibi `/komut` 204 doner, cikti YALNIZ akistan) + `/komut`
(jetonlu; `?` `CT` `G?` `P` `P<v>` `p` `p0` `p1` `Ga…` — FIRMWARE'in metinleriyle) +
`/pil?sira=` (firmware `pil_sayfa` bicimi: en cok 150 nokta, `kalan=`; HER istek sayilir)
+ `/kayit/liste` `/kayit/veri` `/kal/liste` (tarayici_kayitlar.Kart = B72.E'nin sahtesi,
icinde testin PIL oturumu: PIL_AYAR, noktalar, 4 DCIR olayi, PIL_SONUC, BITIR sebep 4).

Pil testi OYNATILIR: OCV -> desarj (noktalar test adim adim acar) -> DCIR anlari (kartin
kurali: n x 300 200 ms) -> kesme (BITTI satiri + G) -> sonuc. Beklenen degerler SAYFADAN
DEGIL: mAh / Wh / DCIR sahte kartin kendi sayilari, mAh ekseni sonu bagimsiz Python yamuk
integrali (sayfanin aldigi metin degerlerinden).

Sayfa `http://olcum.test:<port>/` (Edge `--host-resolver-rules`): kartin sayfasi gibi
localhost DISI — panel kendiliginden akis kipine gecip baglanir, kayit ayni kokenden
esitlenir (C1).
"""
from __future__ import annotations

import http.server
import json
import math
import queue
import re
import struct
import subprocess
import sys
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
import tarayici_kayitlar as TK                              # noqa: E402
from tarayici import Tarayici, bos_port                     # noqa: E402
from tarayici_tema import css_takimlari, rgb, TEMALAR       # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
AD = "olcum.test"
JETON = "jeton3f"
BEKLENEN_404 = ("/durum", "/favicon.ico")
KIMLIK = 21                      # kartin kayit akisi kimligi (oturum numarasindan FARKLI)
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


# ── pil testi senaryosu (deterministik; kartin kurallari) ──────────────────
KESME = 3.2
OCV = 4.10
DCIR_ARALIK, DCIR_DARBE = 300000, 200          # pil_test.h


def gerilim(k: int) -> float:
    return OCV - 0.0007 * k


def senaryo() -> dict:
    """Noktalar (ms, V, A), kartin sayaclari (her noktada), DCIR'ler. Kesme: ilk V <= KESME."""
    noktalar, sayac, dcir = [], [], []
    mah = wh = 0.0
    k = 0
    while True:
        ms = 1000 * (k + 1)
        v = gerilim(k)
        i = v / (4.0 + 0.0004 * k)          # yuk direnci isinip artiyor: I egrisi V'den ayrisir
        mah += i * 1000 / 3600
        wh += v * i / 3600
        noktalar.append((ms, v, i))
        sayac.append((mah, wh))
        n = len(dcir) + 1
        if ms >= n * (DCIR_ARALIK + DCIR_DARBE):
            dcir.append({"no": n, "nokta": k, "t_ms": n * (DCIR_ARALIK + DCIR_DARBE), "r_ani": 0.040 + 0.002 * n,
                         "r_otr": 0.055 + 0.002 * n, "mah": mah, "wh": wh, "v_once": v, "i_once": i})
        if v <= KESME:
            break
        k += 1
    return {"noktalar": noktalar, "sayac": sayac, "dcir": dcir}


SEN = senaryo()
SON = len(SEN["noktalar"])            # kesme noktasi dahil


def kayit_akisi():
    """Kartin kayit akisi: testin PIL oturumu (numarasi G satirinda da bu)."""
    a = TK.Akis(6)
    ot = a.basla(2, 1000, 1790300000, 100000, 3)
    a.ekle(KB.T_OLAY, ot, KB.olay_paketle({"tur": KB.KO_PIL_AYAR, "kart_ms": 100001, "kesme_v": KESME, "ocv": OCV,
                                            "azami_s": 86400, "dcir_aralik_ms": DCIR_ARALIK, "dcir_ms": DCIR_DARBE,
                                            "kayit_hz": 1.0}))
    ns = []
    for ms, v, i in SEN["noktalar"]:
        ns.append(TK.nokta(100000 + ms, v / 0.002625 + 12, i / 7.8125e-5 + 5, v * i))
    sinir = [0] + [d["nokta"] + 1 for d in SEN["dcir"]] + [len(ns)]
    for j in range(len(sinir) - 1):
        a.noktalar(ot, sinir[j], ns[sinir[j]:sinir[j + 1]])
        if j < len(SEN["dcir"]):
            d = SEN["dcir"][j]
            a.ekle(KB.T_OLAY, ot, KB.olay_paketle({"tur": KB.KO_DCIR, "kart_ms": 100000 + d["t_ms"], "no": d["no"],
                                                    "v_once": d["v_once"], "i_once": d["i_once"], "v_ani": d["v_once"] - 0.05,
                                                    "v_oturmus": d["v_once"] - 0.07, "r_ani": d["r_ani"],
                                                    "r_oturmus": d["r_otr"], "mah": d["mah"], "wh": d["wh"]}))
    ms, v, _i = SEN["noktalar"][-1]
    mah, wh = SEN["sayac"][-1]
    a.ekle(KB.T_OLAY, ot, KB.olay_paketle({"tur": KB.KO_PIL_SONUC, "kart_ms": 100000 + ms + 1, "durum": 2, "hata": 0,
                                            "mah": mah, "wh": wh, "ocv": OCV, "v_son": v, "sure_ms": ms,
                                            "dcir_sayisi": len(SEN["dcir"])}))
    a.bitir(ot, len(ns), 4)
    return a, ot


# ── sahte kart ───────────────────────────────────────────────────────────
class Kart(TK.Kart):
    def __init__(self, kayitlar, oturum: int):
        super().__init__(kayitlar)
        self.kimlik = KIMLIK
        self.istemciler: list[queue.Queue] = []
        self.komut_listesi: list[str] = []
        self.pil_istek: list[tuple[float, int]] = []     # (zaman, istenen sira)
        self.oturum = oturum
        self.sonraki_oturum = oturum
        self.durum = "BEKLEMEDE"
        self.hata = "-"
        self.kesme = 3.0
        self.acik = 0                  # kartin "uretmis" oldugu nokta sayisi
        self.ret = None                # p1'in reddi (satir)
        self.kesme_bozuk = False       # PU4: BASLADI satiri istenenden farkli kesme soyler
        self.g = [1, 0, 0]             # durum oturum nokta

    def yay(self, satir: str) -> None:
        with self.kilit:
            for q in self.istemciler:
                q.put(satir)

    def g_satiri(self) -> str:
        d, o, n = self.g
        return f"G {d} {o} {n} 30 0 120 45 0 2900 1300 4 300 0"

    def sayac(self) -> tuple[float, float]:
        return SEN["sayac"][self.acik - 1] if self.acik else (0.0, 0.0)

    def dcir_n(self) -> int:
        return sum(1 for d in SEN["dcir"] if d["nokta"] < self.acik) if self.durum != "BEKLEMEDE" else 0

    def pil_govde(self, sira: int) -> str:
        n = self.acik
        bas = min(max(0, sira), n)
        adet = min(150, n - bas)
        mah, wh = self.sayac()
        dn = self.dcir_n()
        son = SEN["dcir"][dn - 1] if dn else None
        vson = SEN["noktalar"][n - 1][1] if n else 0.0
        satir = [f"durum={self.durum}", f"hata={self.hata}", f"mah={mah:.4f}", f"wh={wh:.6f}",
                 f"ocv={OCV if self.durum != 'BEKLEMEDE' else 0:.4f}", f"vson={vson:.4f}", f"kesme={self.kesme:.3f}",
                 f"dcir_ani={son['r_ani'] if son else 0:.5f}", f"dcir_otr={son['r_otr'] if son else 0:.5f}",
                 f"dcir_n={dn}", f"sira={n}", f"ilk_sira={bas}", f"kalan={n - bas - adet}",
                 f"coulomb={mah * 3.6:.3f}", "--"]
        for ms, v, i in SEN["noktalar"][bas:bas + adet]:
            satir.append(f"{ms},{v:.4f},{i:.6f}")
        return chr(10).join(satir) + chr(10)

    def ilerle(self, adet: int) -> None:
        """Kart `adet` nokta daha uretir; kesmeye ulasirsa BITTI + G (firmware satirlari)."""
        if self.durum != "CALISIYOR":
            return
        self.acik = min(SON, self.acik + adet)
        self.g[2] = self.acik
        if self.acik >= SON:
            self.durum = "BITTI"
            mah, wh = self.sayac()
            self.yay(f"* pil testi BITTI — {mah:.2f} mAh, {wh:.4f} Wh")
            self.g = [1, 0, 0]
            self.yay(self.g_satiri())

    def komut(self, k: str) -> list[str]:
        self.komut_listesi.append(k)
        if k == "?":
            return ["A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=0 y_kazanc=1.000000 y_sifir=0 "
                    "sont=0.100000 i_duz=1.000000 i_ofset=0 rapor=200"]
        if k == "CT":
            return ["CT 0 kaynak=YOK"]
        if k in ("G", "G?"):
            return [self.g_satiri(), "GA 480 0 0 0", "GT 0 0 0 0", "GP 0 0 0 0 0"]
        if k == "P":
            return [f"* pil kesme gerilimi {self.kesme:.3f} V · kayit 1.00 Hz · azami sure 24 saat"]
        if k.startswith("P"):
            try:
                v = float(k[1:])
            except ValueError:
                v = float("nan")
            if not (v >= 0.5) or not (v <= 38.5):
                return ["! P: 0.5 ile 38.5 V arasi olmali (ust sinir MOSFET Vdss'inden)"]
            self.kesme = v
            return [f"* pil kesme gerilimi {v:.3f} V"]
        if k == "p1":
            if self.durum == "CALISIYOR":
                return ["! pil testi zaten suruyor — yeniden baslatmak icin once p0"]
            if self.ret:
                self.durum, self.hata = "HATA", self.ret.split(": ", 1)[1]
                return [self.ret]
            self.durum, self.hata, self.acik = "CALISIYOR", "-", 0
            self.oturum = self.sonraki_oturum
            self.sonraki_oturum += 1
            self.g = [2, self.oturum, 0]
            kesme = 3.0 if self.kesme_bozuk else self.kesme
            return [f"* pil testi BASLADI — OCV {OCV:.4f} V, kesme {kesme:.3f} V",
                    "* pil testi kaydi istendi (oturum turu PIL; olcum kaydi aciksa kapanir) — sonuc G satirinda",
                    self.g_satiri()]
        if k == "p0":
            if self.durum == "CALISIYOR":
                self.durum = "DURDURULDU"
                self.g = [1, 0, 0]
                return ["* pil testi DURDURULDU, yuk kesildi", self.g_satiri()]
            return ["* pil testi zaten calismiyor; yuk kapali"]
        if k == "p":
            mah, wh = self.sayac()
            return [f"B {self.durum} {mah:.3f} {wh:.5f} {OCV:.4f} 0.0000 {self.kesme:.3f} 0 0 0 0 {self.acik} {self.hata}"]
        if k.startswith("Ga"):
            return ["* G not kuyrukta (verilmemis oturuma yazilmaz; sonuc esitlenen dosyada)"]
        return ["* tamam"]


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

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            yol = u.path
            if yol == "/akis":
                kuyruk: queue.Queue = queue.Queue()
                with kart.kilit:
                    kart.istemciler.append(kuyruk)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(f'retry: 1000\n\nevent: kimlik\ndata: {{"jeton":"{JETON}","surucu":true}}\n\n'.encode())
                    self.wfile.flush()
                    while not DUR.is_set():
                        try:
                            s = kuyruk.get(timeout=1.0)
                            self.wfile.write(("data: " + s + "\n\n").encode("utf-8"))
                        except queue.Empty:
                            self.wfile.write(b": nabiz\n\n")
                        self.wfile.flush()
                except OSError:
                    pass
                finally:
                    with kart.kilit:
                        if kuyruk in kart.istemciler:
                            kart.istemciler.remove(kuyruk)
                self.close_connection = True
                return
            if yol == "/pil":
                with kart.kilit:
                    sira = int(q.get("sira", ["0"])[0])
                    kart.pil_istek.append((time.monotonic(), sira))
                    govde = kart.pil_govde(sira).encode()
                return self._gonder(200, govde)
            if yol == "/kayit/liste":
                with kart.kilit:
                    d = kart.dizin()
                return self._gonder(200, json.dumps(d).encode(), "application/json")
            if yol == "/kayit/veri":
                with kart.kilit:
                    govde, ilk, son = kart.veri(int(q.get("sira", ["1"])[0]), int(q.get("bayt", ["8192"])[0]))
                    bas = {"X-Kayit-Kimlik": str(kart.kimlik), "X-Ilk-Sira": str(ilk), "X-Son-Sira": str(son),
                           "X-Sonraki-Sira": str(kart.sonraki()), "X-Onay": str(kart.onay)}
                return self._gonder(200, govde, "application/octet-stream", bas)
            if yol == "/kal/liste":
                return self._gonder(200, json.dumps(kart.kal_liste, ensure_ascii=False).encode("utf-8"), "application/json")
            if yol in BEKLENEN_404:
                return self._gonder(404, b"yok")
            if yol.startswith("/ortak/"):
                p = (ORTAK / yol[len("/ortak/"):]).resolve()
                if p.parent != ORTAK.resolve() or not p.is_file():
                    return self._gonder(404, b"yok")
            else:
                p = (ARAYUZ / (yol.lstrip("/") or "index.html")).resolve()
                if ARAYUZ.resolve() not in p.parents or not p.is_file():
                    return self._gonder(404, b"yok")
            self._gonder(200, p.read_bytes(), MIME.get(p.suffix, "application/octet-stream"))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            govde = self.rfile.read(n).decode("utf-8", "replace").strip()
            if urllib.parse.urlparse(self.path).path != "/komut":
                return self._gonder(404, b"yok")
            if self.headers.get("X-Olcum") != "1":
                return self._gonder(400, b"X-Olcum basligi gerekli")
            if govde != "p0" and self.headers.get("X-Jeton") != JETON:     # p0 HER ZAMAN serbest (firmware)
                return self._gonder(403, b"gecersiz oturum jetonu")
            with kart.kilit:
                cikti = kart.komut(govde)
            for s in cikti:          # gercek kart: 204, cikti YALNIZ akistan (Serial aynasi)
                kart.yay(s)
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

    class Sunucu(http.server.ThreadingHTTPServer):
        daemon_threads = True
        block_on_close = False
        allow_reuse_address = False

        def handle_error(self, *a):
            pass

    s = Sunucu(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


# ── tarayici ─────────────────────────────────────────────────────────────
class PilTarayici(Tarayici):
    """tarayici.Tarayici + `Log` alani (modul / varlik yukleme hatalari)."""

    def _olay(self, m: dict) -> None:
        if m.get("method") == "Log.entryAdded":
            e = m.get("params", {}).get("entry", {})
            if e.get("level") == "error":
                self.olaylar.append({"tur": "log", "url": e.get("url", ""),
                                     "metin": f"{e.get('source')}: {e.get('text')} {e.get('url', '')}"})
            return
        super()._olay(m)

    def hatalar_tum(self) -> list[str]:
        h = [o["metin"] for o in self.olaylar if o["tur"] == "hata" or o.get("seviye") == "error"]
        for o in self.olaylar:
            if o["tur"] == "log":
                yol = re.sub(r"^https?://[^/]+", "", o["url"]).split("?")[0]
                if yol not in BEKLENEN_404:
                    h.append(o["metin"])
        return [x for x in h if "favicon" not in x.lower()]


class Kopuk(Exception):
    """Ust uste bekleme zaman asimi: kalan evreler anlamsiz — erken, SAYILARAK bitis."""


ZAMAN_ASIMI = [0]


def bekle_js(t, ifade: str, sure: float = 10.0):
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
        t.bekle(0.15)
    ZAMAN_ASIMI[0] += 1
    if ZAMAN_ASIMI[0] >= 3:
        raise Kopuk(ifade[:80])
    return deger


def komut_bekle(t, kart: Kart, n: int, adet: int, sure: float = 6.0) -> list[str]:
    son = time.monotonic() + sure
    while time.monotonic() < son and len(kart.komut_listesi) < n + adet:
        t.bekle(0.05)
    t.bekle(0.3)
    return kart.komut_listesi[n:]


def deger_yaz(t, secici: str, deger: str) -> None:
    t.js("(() => { const e = document.querySelector(%s); e.value = %s; e.dispatchEvent(new Event('input')); })()"
         % (json.dumps(secici), json.dumps(deger)))


def tikla(t, secici: str) -> None:
    t.js("document.querySelector(%s).click()" % json.dumps(secici))


def tasma(t) -> int:
    return t.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def istek_say(kart: Kart) -> int:
    with kart.kilit:
        return len(kart.pil_istek)


def okumalar(t) -> dict:
    return t.js("Object.fromEntries([...document.querySelectorAll('[data-pil-okuma]')].map(e => [e.dataset.pilOkuma,"
                " {d: e.querySelector('.deger').textContent.trim(), k: e.querySelector('[data-pil=kaynak]').textContent.trim()}]))")


def dcir_tablo(t) -> list:
    return t.js("[...document.querySelectorAll('.pil-dcir-tablo tbody tr')].map(r => [...r.children].map(c => c.textContent.trim()))")


def gorunurluk(t, gizli: bool) -> None:
    if gizli:
        t.js("(() => { Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'hidden'});"
             " document.dispatchEvent(new Event('visibilitychange')); })()")
    else:
        t.js("(() => { delete document.visibilityState; document.dispatchEvent(new Event('visibilitychange')); })()")


PIKSEL_JS = """(() => {
  const c = document.querySelector(%s);
  if (!c || !c.width) return null;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const h = %s; const s = h.map(() => 0);
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 250) continue;
    for (let j = 0; j < h.length; j++) if (Math.abs(d[i] - h[j][0]) <= 6 && Math.abs(d[i + 1] - h[j][1]) <= 6
      && Math.abs(d[i + 2] - h[j][2]) <= 6) s[j]++; }
  return s; })()"""


def tema_sec(t, ad: str, geri: str = "#/pil") -> None:
    yazi = ["Koyu", "Açık", "Ön panel"][TEMALAR.index(ad)]
    t.js("location.hash = '#/ayar/dil-gorunum'")   # 3H: tema dugmeleri 'Dil ve gorunum' bolumunde
    t.bekle(0.3)
    t.js("[...document.querySelectorAll('button')].find(x => x.textContent.trim() === %s).click()" % json.dumps(yazi))
    bekle_js(t, f"document.documentElement.dataset.tema === {json.dumps(ad)}", 5)
    t.js(f"location.hash = {json.dumps(geri)}")
    t.bekle(0.8)


def profil_surecleri(profil: str) -> list[int]:
    ad = Path(profil).name
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                            f"Where-Object {{ $_.CommandLine -like '*{ad}*' }} | ForEach-Object {{ $_.ProcessId }}"],
                           capture_output=True, text=True, timeout=60)
    except Exception:
        return [-1]
    return [int(x) for x in r.stdout.split() if x.strip().isdigit()]


def mah_yamuk(sayi: int) -> float:
    """Bagimsiz: sayfanin ALDIGI metin degerlerinden (ms tam sayi, A 6 ondalik) yamuk integral."""
    n = [(ms, float(f"{i:.6f}")) for ms, _v, i in SEN["noktalar"][:sayi]]
    return sum((n[k - 1][1] + n[k][1]) / 2 * (n[k][0] - n[k - 1][0]) / 3600 for k in range(1, len(n)))


# ── ana akis ─────────────────────────────────────────────────────────────
def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    takim = css_takimlari()
    akis, ot = kayit_akisi()
    kart = Kart(akis.kayitlar, ot)
    s = sunucu_kur(kart)
    taban = f"http://{AD}:{s.server_address[1]}"
    resimler = []
    profil = None
    print("=" * 78)
    print("  3F  PIL TESTI — TARAYICIDA, SAHTE KARTA KARSI (T3F)")
    print("=" * 78)
    print(f"     sahte kart: {taban} · senaryo {SON} nokta, {len(SEN['dcir'])} DCIR, PIL oturumu #{ot}\n")

    def resim(ad: str) -> None:
        if goruntu:
            y = goruntu / f"{ad}.png"
            t.goruntu(str(y))
            resimler.append(y)

    try:
        with PilTarayici(auth_iptal=False, port=bos_port(),
                         ek_arg=[f"--host-resolver-rules=MAP {AD} 127.0.0.1"]) as t:
            profil = t.profil
            t.cagir("Log.enable")
            t.tema("dark")

            # ── 1. Canli'da acilis: pil durumu BIR KEZ, sonra yoklama YOK ──────
            t.git(taban + "/#/canli")
            bekle_js(t, f"{UYG}.bagli && {UYG}.kayit.g && {UYG}.pilKesmeBilinen", 15)
            t.bekle(4.0)
            n_acilis = istek_say(kart)
            ok("[!] PL4: baglaninca `/pil` BIR KEZ (acil serit icin durum); Canli'da 4 s boyunca yeni istek YOK",
               n_acilis == 1 and t.js(f"{UYG}.pilDurum") == "BEKLEMEDE", f"{n_acilis} istek")

            # ── 2. Pil sekmesi: modul iner; test surmuyor -> istek yok ────────
            t.js("location.hash = '#/pil'")
            bekle_js(t, f"{UYG}.pilModDurum === 'hazir'", 10)
            t.bekle(2.5)
            dur = t.js("(() => { const b = document.querySelector('[data-pil=durdur]'); return b && {d: b.disabled,"
                       " a: b.hasAttribute('disabled'), g: b.offsetParent !== null, m: b.textContent.trim()}; })()")
            ok("[!] PL1: Pil sekmesinde DURDUR GORUNUR ve ETKIN (test surmezken de; :disabled YOK)",
               bool(dur) and dur["d"] is False and dur["a"] is False and dur["g"] is True and dur["m"] == "DURDUR", str(dur))
            ok("[!] PL4: Pil sekmesi acildi, test surmuyor, durum taze -> yeni `/pil` YOK",
               istek_say(kart) == n_acilis, f"{istek_say(kart)} istek")
            ok_ = okumalar(t)
            ok("PL2: okuma kartlari altisi da var; kesme KARTIN ayari (3.00 V, kaynak yazili)",
               list(ok_) == ["v", "i", "mah", "wh", "sure", "kesme"] and ok_["kesme"]["d"] == "3.00V"
               and ok_["kesme"]["k"] == "kartın ayarı", json.dumps(ok_, ensure_ascii=False))

            # ── 3. ret: panelin reddi (kesme 40) ve kartin reddi (REDDEDILDI) ──
            n0 = len(kart.komut_listesi)
            deger_yaz(t, "[data-pil=kesme]", "40")
            tikla(t, "[data-pil=baslat]")
            uy = bekle_js(t, "(() => { const e = document.querySelector('[data-pil=uyari]'); return e && e.dataset.tur + '|' + e.textContent.trim(); })()", 4)
            ok("[!] PL5: kesme 40 V (kartin siniri disi) GONDERILMIYOR; sebep alanin ustunde (panel)",
               len(kart.komut_listesi) == n0 and bool(uy) and uy.startswith("panel|") and "0.5 … 38.5 V" in uy, str(uy))
            kart.ret = "! pil testi REDDEDILDI: gerilim zaten kesmenin altinda"
            deger_yaz(t, "[data-pil=kesme]", "3.0")
            n1 = len(kart.komut_listesi)
            tikla(t, "[data-pil=baslat]")
            k1 = komut_bekle(t, kart, n1, 1)
            ret = bekle_js(t, "(() => { const e = document.querySelector('[data-pil=uyari]'); return e && e.dataset.tur === 'kart' && e.textContent.trim(); })()", 5)
            hata = t.js("(() => { const e = [...document.querySelectorAll('main.gorunum p.hata')].find(x => x.textContent.includes('Pil testi:')); return e && e.textContent.replace(/[ ]+/g, ' ').trim(); })()")
            ok("[!] PL5 (E9): kesme kartinkiyle ayniysa `P` GITMEZ, yalniz `p1`; kartin reddi OLDUGU GIBI, hata sozlukten",
               k1 == ["p1"] and ret == "Kart reddetti: ! pil testi REDDEDILDI: gerilim zaten kesmenin altinda"
               and bool(hata) and "gerilim zaten kesme geriliminin altında" in hata, f"{k1} · {ret} · {hata}")
            kart.ret = None
            kart.durum, kart.hata = "BEKLEMEDE", "-"

            # ── 4. baslat: P<v> + onay -> p1 -> G'de PIL oturumu -> Ga ─────────
            deger_yaz(t, "[data-pil=kesme]", "3,2")
            deger_yaz(t, "[data-pil=ad]", "18650 #3 — deneme")
            n2 = len(kart.komut_listesi)
            tikla(t, "[data-pil=baslat]")
            k2 = komut_bekle(t, kart, n2, 3)
            bekle_js(t, f"{UYG}.pilDurum === 'CALISIYOR' && {UYG}.pilOturum && {UYG}.pilOturum.no === {ot}", 6)
            ok("[!] PL5 + PU4: Baslat -> `P3.2` (virgul ondalik), kartin onayindan SONRA `p1`; PIL oturumu G'den, ad `Ga<oturum>`",
               k2 == ["P3.2", "p1", f"Ga{ot} 18650 #3 — deneme"] and t.js(f"{UYG}.pilOturum.no") == ot
               and t.js("document.querySelector('[data-pil=oturum]').textContent.trim()") == f"Kayıt #{ot}", " | ".join(k2))
            acil = t.js("(() => { const a = document.querySelector('.acil'); return a && a.offsetParent !== null && a.textContent.replace(/[ ]+/g, ' ').trim(); })()")
            ok("[!] Acil serit test basladiginda HER gorunumde (BASLADI satirindan, yoklama beklenmeden)",
               bool(acil) and "Pil testi çalışıyor" in acil and "kesme 3.20 V" in acil, str(acil))

            # ── 5. yoklama: yalniz Pil sekmesi gorunur + test suruyor ─────────
            kart.ilerle(40)
            bekle_js(t, f"{UYG}.pilNokta.length === 40", 6)
            a0 = istek_say(kart)
            t.bekle(6.0)
            a1 = istek_say(kart)
            ok("[!] PL4: test surerken Pil sekmesinde ~2 s'de bir `/pil` (6 s'de 2…4 istek)", 2 <= a1 - a0 <= 4, f"{a1 - a0} istek")
            ok_ = okumalar(t)
            mah, wh = SEN["sayac"][39]
            ok("[!] PU8: mAh / Wh KARTIN sayaci (sahte kartin sayisi), kaynagi yazili; gecen sure kartin son noktasi; V/I canli",
               ok_["mah"]["d"] == f"{mah:.1f}mAh" and ok_["wh"]["d"] == f"{wh:.3f}Wh" and ok_["mah"]["k"] == "kartın sayacı (her örnek)"
               and ok_["sure"]["d"] == "00:00:40" and ok_["sure"]["k"] == "kartın saati (son nokta)"
               and ok_["v"]["k"] == "canlı (kartın D satırı)", json.dumps(ok_, ensure_ascii=False))
            # DCIR 1 gorulur
            kart.ilerle(300)
            bekle_js(t, f"{UYG}.pilNokta.length === 340 && {UYG}.pilDcirListe.length === 1", 8)
            d1 = SEN["dcir"][0]
            tb = dcir_tablo(t)
            ok("[!] PU10: DCIR 1 tabloda — an kartin kuralindan (00:05:00), R ani / oturmus mΩ, mAh yoklama aninda (≈)",
               len(tb) == 1 and tb[0][:4] == ["R1", "00:05:00", f"{d1['r_ani'] * 1000:.1f} mΩ", f"{d1['r_otr'] * 1000:.1f} mΩ"]
               and tb[0][4].startswith("≈ "), str(tb))

            # ── 6. sekme gizli (baska gorunum) ve belge gizli: yoklama DURUR ──
            t.js("location.hash = '#/canli'")
            t.bekle(1.0)
            kart.ilerle(600)            # bu arada DCIR 2 ve 3 olur — panel GORMEZ
            g0 = istek_say(kart)
            t.bekle(5.0)
            g1 = istek_say(kart)
            acil2 = t.js("!!document.querySelector('.acil') && document.querySelector('.acil').offsetParent !== null")
            ok("[!] PL4: Pil sekmesi GIZLIYKEN (Canli) test sursе de `/pil` YOK (5 s); acil serit yine gorunur",
               g1 == g0 and acil2 is True, f"{g1 - g0} istek")
            t.js("location.hash = '#/pil'")
            bekle_js(t, f"{UYG}.pilNokta.length === 940", 8)
            tb = dcir_tablo(t)
            d3 = SEN["dcir"][2]
            ok("[!] PU10: sekme donunce kalan noktalar (150'lik parcalarla, ayni yoklamada) geldi; aradaki DCIR 2 'gorulmedi' (—), DCIR 3 degerli",
               len(tb) == 3 and tb[1][2:] == ["—", "—", "—"] and tb[1][1] == "00:10:00"
               and tb[2][:3] == ["R3", "00:15:00", f"{d3['r_ani'] * 1000:.1f} mΩ"]
               and bool(t.js("!!document.querySelector('[data-pil=dcir-gorulmedi]')")), str(tb))
            gorunurluk(t, True)
            t.bekle(0.5)
            h0 = istek_say(kart)
            t.bekle(5.0)
            h1 = istek_say(kart)
            gorunurluk(t, False)
            t.bekle(3.0)
            h2 = istek_say(kart)
            ok("[!] PL4: belge GIZLI (visibilitychange) iken `/pil` YOK; gorunur olunca yeniden basliyor",
               h1 == h0 and h2 > h1, f"gizli {h1 - h0} · sonra {h2 - h1}")

            # ── 7. egri: pikseller, DCIR isaretleri, mAh ekseni ──────────────
            t.js("document.querySelector('canvas.pil-grafik').scrollIntoView({block: 'center'})")
            t.bekle(0.6)
            koyu = takim["koyu"]
            px = t.js(PIKSEL_JS % (json.dumps("canvas.pil-grafik"),
                                   json.dumps([list(rgb(koyu["--volt"])), list(rgb(koyu["--amper"]))])))
            plan = t.js(f"(() => {{ const p = {UYG}._pilGrafik.g.sonPlan; return {{i: p.komutlar.filter(k => k.rol === 'isaret' && k.tur === 'yazi').map(k => k.metin),"
                        " e: p.komutlar.filter(k => k.rol === 'eksen').map(k => k.metin)}; })()")
            ok("[!] PL3: egri tuvali (grafik.js) GERCEKTEN cizili — V (--volt) ve I (--amper) pikselleri; DCIR anlari R1 R2 R3 isaretli",
               bool(px) and px[0] > 200 and px[1] > 100 and plan["i"] == ["R1", "R2", "R3"], f"{px} · {plan['i']}")
            t.js("(() => { const s = document.querySelector('[data-pil=eksen]'); s.value = 'mah'; s.dispatchEvent(new Event('change')); })()")
            t.bekle(0.6)
            xs = t.js(f"{UYG}.pilBilgi && {UYG}.pilBilgi.xSon")
            beklenen = mah_yamuk(940)
            karsi = t.js("(() => { const e = document.querySelector('[data-pil=mah-karsilastir]'); return e && e.textContent.trim(); })()")
            eksen = t.js(f"{UYG}._pilGrafik.g.sonPlan.komutlar.filter(k => k.rol === 'eksen' && k.y > {UYG}._pilGrafik.g.sonPlan.alan.y + {UYG}._pilGrafik.g.sonPlan.alan.h).map(k => k.metin)")
            kmah = SEN["sayac"][939][0]
            ok("[!] PU9: mAh ekseni TARAYICI hesabi — eksen sonu BAGIMSIZ Python yamuk integraliyle ayni; kartin sayaci yaninda yazili; x yazilari mAh",
               xs is not None and abs(xs - beklenen) < 0.01 and bool(karsi) and f"{xs:.1f}" in karsi and f"{kmah:.1f}" in karsi
               and len(eksen) >= 2 and all(e.endswith("mAh") for e in eksen), f"panel {xs} · python {beklenen:.4f} · {karsi} · {eksen[:3]}")
            t.js("(() => { const s = document.querySelector('[data-pil=eksen]'); s.value = 'zaman'; s.dispatchEvent(new Event('change')); })()")
            t.bekle(0.3)
            resim("1-pil-suruyor-koyu")

            # ── 8. yenileme: egri IndexedDB'den, oturum + DCIR yerelden ──────
            r0 = istek_say(kart)
            t.js(f"{UYG}._yenidenYuklemeIsareti = 1")
            t.cagir("Page.reload")          # ayni adrese Page.navigate YENIDEN YUKLEMEZ (yalniz parca gezinmesi)
            t.bekle(0.5)
            bekle_js(t, f"!{UYG}._yenidenYuklemeIsareti && {UYG}.bagli && {UYG}.pilModDurum === 'hazir'", 15)
            ilk_n = t.js(f"{UYG}.pilNokta.length")
            bekle_js(t, f"{UYG}.pilBilgi && {UYG}.pilBilgi.var && {UYG}.pilDurum === 'CALISIYOR'", 8)
            t.bekle(0.5)
            with kart.kilit:
                ilk_istek = kart.pil_istek[r0][1] if len(kart.pil_istek) > r0 else None
            tb8 = dcir_tablo(t)
            ok("[!] PL4: sayfa yenilenince egri geri geliyor — noktalar IndexedDB'den, `/pil` KALDIGI siradan (940, 0'dan degil); oturum ve DCIR tablosu yerelden (R1 degerli, oturum 'gorulmedi' DEGIL)",
               t.js(f"{UYG}.pilNokta.length") == 940 and ilk_istek == 940 and t.js(f"{UYG}.pilOturum && {UYG}.pilOturum.no") == ot
               and t.js(f"{UYG}.pilOturum.gorulmedi") is False and len(tb8) == 3 and tb8[0][2] != "—" and tb8[0][4].startswith("≈ ")
               and t.js(f"{UYG}.pilKayitOzet") is None and t.js(f"{UYG}.pilBilgi.n") == 940,
               f"ilk {ilk_n} · ilk istek sira={ilk_istek} · {tb8[:1]}")

            # ── 9. kesme BASKA sekmedeyken: yalniz kartin BITTI satiri bildirir (yoklama yok) ──
            t.js("location.hash = '#/canli'")
            t.bekle(1.0)
            b0 = istek_say(kart)
            kart.ilerle(SON)
            bekle_js(t, f"{UYG}.pilDurum === 'BITTI'", 8)
            t.bekle(5.0)
            b1 = istek_say(kart)
            ok("[!] PL4: test Canli'dayken kesmede biter — kartin BITTI satiri durumu 'bitti' yapar, acil serit KALKAR; Pil sekmesi gizli: `/pil` YOK (5 s)",
               b1 == b0 and t.js("!document.querySelector('.acil')") is True and t.js(f"{UYG}.pilBayat") is True, f"{b1 - b0} istek")
            t.js("location.hash = '#/pil'")
            bekle_js(t, f"{UYG}.pilKayitOzet && {UYG}.pilKayitOzet.oturum === {ot}", 15)
            t.bekle(5.0)
            b2 = istek_say(kart)
            dolgu = math.ceil((SON - 940) / 150)      # kalan noktalar 150'lik parcalarla, AYNI tazelemede
            ok("[!] PL4: Pil sekmesi acilinca bitmis testin son hali BIR kez alinir (eksik noktalar `kalan=` ile ayni tazelemede), sonra yoklama YOK (5 s)",
               b2 - b1 == dolgu and t.js(f"{UYG}.pilNokta.length") == SON, f"{b2 - b1} istek (beklenen {dolgu})")
            t.bekle(0.6)
            ok_ = okumalar(t)
            mah, wh = SEN["sayac"][-1]
            href = t.js("(() => { const a = document.querySelector('[data-pil=kayitlarda-ac]'); return a && a.getAttribute('href'); })()")
            ok("[!] PL4/PL6: bitince kaynak KARTIN PIL oturumu (esitlendi): mAh/Wh/sure PIL_SONUC'tan, bitis sebebi BITIR'den; egri kaynagi kayit",
               ok_["mah"]["d"] == f"{mah:.1f}mAh" and ok_["mah"]["k"] == "kayıt (PİL oturumu)"
               and ok_["sure"]["d"] == "00:%02d:%02d" % divmod(SEN["noktalar"][-1][0] // 1000, 60)
               and t.js("document.querySelector('[data-pil=sebep]').textContent.trim()") == "pil testi bitti"
               and t.js("document.querySelector('[data-pil=egri-kaynak]').textContent.trim()") == f"kaynak: kayıt #{ot} (bu tarayıcıdaki eşitlenmiş kopya)",
               json.dumps(ok_, ensure_ascii=False))
            tb = dcir_tablo(t)
            ok("[!] PU10: kayit kaynaginda DCIR tablosu kaydin OLAY'larindan — 4 olcum, mAh KARTIN (≈ yok), 'gorulmedi' yok",
               len(tb) == len(SEN["dcir"]) == 4 and all(not r[4].startswith("≈") and r[2] != "—" for r in tb)
               and tb[1][4] == f"{SEN['dcir'][1]['mah']:.1f}" and t.js("!document.querySelector('[data-pil=dcir-gorulmedi]')") is True, str(tb))
            ok("[!] PL6: 'Kayitlar'da ac' dogru oturuma (#/kayit/<oturum>@<kimlik>)", href == f"#/kayit/{ot}@{KIMLIK}", str(href))
            pxk = t.js(PIKSEL_JS % (json.dumps("canvas.pil-grafik"), json.dumps([list(rgb(koyu["--volt"]))])))
            ok("PL3: kayittan egri cizili (kaydin noktalari)", bool(pxk) and pxk[0] > 200 and t.js(f"{UYG}.pilBilgi.n") == SON, str(pxk))
            resim("2-pil-bitti-kayit")
            tikla(t, "[data-pil=kayitlarda-ac]")
            bekle_js(t, f"{UYG}.gorunum === 'kayitlar' && location.hash === {json.dumps(href)}", 6)
            ok("PL6: baglanti Kayitlar'i o kayitla aciyor", t.js("location.hash") == href and t.js(f"{UYG}.gorunum") == "kayitlar")
            t.js("location.hash = '#/pil'")
            bekle_js(t, f"{UYG}.gorunum === 'pil'", 4)

            # ── 10. uc gorunum (kayittan egri) ────────────────────────────────────────────
            onceki = "koyu"
            for ad in TEMALAR:
                tema_sec(t, ad)
                t.js("document.querySelector('canvas.pil-grafik').scrollIntoView({block: 'center'})")
                t.bekle(0.5)
                hedef = [list(rgb(takim[ad]["--volt"]))] + ([list(rgb(takim[onceki]["--volt"]))] if ad != onceki else [])
                pd_ = t.js(PIKSEL_JS % (json.dumps("canvas.pil-grafik"), json.dumps(hedef)))
                ok(f"[!] {ad}: pil egrisi YENI --volt rengiyle" + (f", eski ({onceki}) yok" if ad != onceki else ""),
                   bool(pd_) and pd_[0] > 200 and (ad == onceki or pd_[1] == 0), str(pd_))
                resim(f"3-pil-{ad}")
                onceki = ad

            # ── 11. telefon (390 px) ──────────────────────────────────────
            t.ekran(390, 844)
            t.bekle(0.8)
            tasmalar = {}
            for ad in TEMALAR:
                tema_sec(t, ad)
                tasmalar[ad] = tasma(t)
            ii = t.js("(() => { const r = (s) => { const e = document.querySelector(s); const b = e.getBoundingClientRect(); return {l: b.left, r: b.right}; };"
                      " return {cw: document.documentElement.clientWidth, tuval: r('canvas.pil-grafik'), tablo: r('[data-pil=dcir]'), dur: r('[data-pil=durdur]')}; })()")
            ok("[!] 390 px: uc gorunumde yatay tasma YOK (scrollWidth = clientWidth); tuval, DCIR karti (TEK sutun, tam genislik), DURDUR ekranin icinde",
               all(v <= 0 for v in tasmalar.values()) and all(0 <= ii[k]["l"] and ii[k]["r"] <= ii["cw"] for k in ("tuval", "tablo", "dur"))
               and ii["tablo"]["r"] - ii["tablo"]["l"] > 0.8 * ii["cw"],
               f"{tasmalar} {ii}")
            resim("4-pil-telefon")
            t.cagir("Emulation.clearDeviceMetricsOverride")

            # ── 12. p0: tek tik; PU4: kart baska kesmeyle baslatirsa panel keser ──
            n3 = len(kart.komut_listesi)
            tikla(t, "[data-pil=durdur]")
            k3 = komut_bekle(t, kart, n3, 1)
            ok("[!] PL1: Pil sekmesindeki DURDUR TEK tikla `/komut`a `p0` (onay yok; test surmezken de)",
               k3 == ["p0"] and t.js(f"{UYG}.onay") is None, str(k3))
            kart.durum = "BEKLEMEDE"
            kart.kesme_bozuk = True
            deger_yaz(t, "[data-pil=kesme]", "3.5")
            n4 = len(kart.komut_listesi)
            tikla(t, "[data-pil=baslat]")
            k4 = komut_bekle(t, kart, n4, 3)
            uy4 = bekle_js(t, "(() => { const e = document.querySelector('[data-pil=uyari]'); return e && e.dataset.tur === 'panel' && e.textContent.trim(); })()", 5)
            ok("[!] PU4: kart testi istenenden FARKLI kesmeyle baslattiysa panel HEMEN `p0` yollar ve soyler",
               k4[:3] == ["P3.5", "p1", "p0"] and bool(uy4) and "3.000 V" in uy4 and "3.500 V" in uy4 and "p0" in uy4, f"{k4} · {uy4}")
            kart.kesme_bozuk = False
            bekle_js(t, f"{UYG}.pilDurum === 'DURDURULDU'", 5)
            deger_yaz(t, "[data-pil=kesme]", "")
            n5 = len(kart.komut_listesi)
            tikla(t, "[data-pil=baslat]")
            bekle_js(t, "!!document.querySelector('.acil')", 5)
            t.js("location.hash = '#/canli'")
            t.bekle(0.5)
            tikla(t, ".acil .acil-dur")
            k5 = komut_bekle(t, kart, n5, 2)
            bekle_js(t, "!document.querySelector('.acil')", 5)
            ok("[!] PL1: kesme bos -> kartin kesmesiyle (P yok) `p1`; acil seritteki DURDUR (baska sekmede) tek tikla `p0`, serit kalkti",
               k5[:2] == ["p1", "p0"] and t.js(f"{UYG}.pilDurum") == "DURDURULDU", str(k5))

            # ── 13. konsol ────────────────────────────────────────────────
            hatalar = t.hatalar_tum()
            ok("[!] Butun gezinti boyunca konsol/yukleme hatasi YOK", not hatalar, " | ".join(hatalar[:3]) or "temiz")
    except Kopuk as h:
        ok("[!] Sayfa beklenen akista kaldi (ust uste 3 bekleme zaman asimi yok)", False,
           f"son beklenen: {h} — kalan olcumler ATLANDI")
    finally:
        DUR.set()
        s.shutdown()
        s.server_close()

    if profil and sys.platform == "win32":
        kalan = profil_surecleri(profil)
        ok("[!] Basliksiz Edge SIZMADI (bu testin profiliyle calisan msedge sureci kalmadi)", not kalan, str(kalan))
    for y in resimler:
        print(f"     goruntu: {y}")
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
