# -*- coding: utf-8 -*-
"""3E — OSILOSKOP TARAYICIDA (T3E): sahte karta karsi uctan uca.

    python tarayici_skop.py                    # sessiz, 0/1 doner
    python tarayici_skop.py --goruntu DIZIN    # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B7 (`test_arayuz3.js` bolum 26) saf mantigi ve kaynak metnini
   node'da sinar; gercek Vue'yu, gercek SSE akisini + `/skop.bin` cekisini, tuvallerin
   GERCEKTEN cizildigini, `/komut`a giden METNI, IndexedDB'den acilan kayitli yakalamayi,
   duzenin gercek olculerini (1280 / 390 px) ve uc gorunumu sinayamaz.

Sahte kart (bu dosyada, Python): arayuz3 + `/ortak/` + `/akis` (SSE: `kimlik`, komut
yanitlari) + `/komut` (jeton denetimli; `?` `CT` `G?` `Gt…` `tB` `ta` `w` — FIRMWARE'in
metinleriyle) + `/skop.bin` (S3B) + `/kayit/liste` `/kayit/veri` `/kal/liste`
(tarayici_kayitlar.Kart = B72.E'nin sahtesi).

BEKLENEN DEGERLER SAYFADAN DEGIL:
  * Kartin `M` satiri = KARTIN C KODU (skop_olc, AVR emulatorunde: ortak/test/vektor/
    skop.json) + skop_ofsetle (burada float32, struct ile). Kayitli yakalamada panelin
    tarayicida hesapladigi sayi, kartin printf bicimiyle bu satirin AYNISI olmali (OS4).
  * Egrili kayitli yakalama: GERCEK KARTIN yakalamasi ve `M` satiri (olcum-skop-fikstur.json).
  * Spektrum tepesi: saf Python DFT (numpy YOK) — Hann'li, DC'si cikarilmis dizinin DTFT
    tepesi altin oran aramasiyla; panelin parabol ara degerlemesiyle <= 0.05 kutu.

Sayfa `http://olcum.test:<port>/` (Edge `--host-resolver-rules`): kartin sayfasi gibi
localhost DISI — panel kendiliginden akis kipine gecip baglanir, Kayitlar esitler (C1).
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
from tarayici_tema import KayitliTarayici, bos_port, css_takimlari, rgb, TEMALAR  # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
AD = "olcum.test"
JETON = "jeton3e"
BEKLENEN_404 = ("/durum", "/pil", "/favicon.ico")
VEKTOR = json.loads((KOK / "ortak" / "test" / "vektor" / "skop.json").read_text(encoding="utf-8"))
FIKSTUR = json.loads((BURASI / "olcum-skop-fikstur.json").read_text(encoding="utf-8"))
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


# ── kartin sayilari (olcum3.h sabitleri float32; skop_ofsetle) ──────────────
def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


ORAN = f32(38.03703704)
VREF = f32(1.7153125)
ADIM = f32(f32(f32(3.10) / 4096.0) * ORAN)
OFSET = f32(VREF * f32(ORAN - 1.0))
assert ADIM == VEKTOR["vakalar"][0]["volt_adim"], "SKOP_VOLT_ADIM vektorlerle ayni degil"


def vaka(ad: str) -> dict:
    return next(v for v in VEKTOR["vakalar"] if v["ad"] == ad)


def kart_olcum(v: dict) -> dict:
    """Kartin M satirinin sayilari: C skop_olc (vektor) + skop_ofsetle (float32)."""
    b = dict(v["beklenen"])
    o = OFSET
    b["Vmax"] = f32(b["Vmax"] - o)
    b["Vmin"] = f32(b["Vmin"] - o)
    b["Vort"] = f32(b["Vort"] - o)
    b["Vrms"] = f32(math.sqrt(f32(f32(b["Vac"] * b["Vac"]) + f32(b["Vort"] * b["Vort"]))))
    return b


def m_satiri(o: dict) -> str:
    """olcum-karti-a3.ino skop_m_satiri snprintf bicimi."""
    return ("M f=%.3f T=%.9f Vpp=%.4f Vmax=%.4f Vmin=%.4f Vort=%.4f Vrms=%.4f Vac=%.4f "
            "duty=%.2f tr=%.9f tf=%.9f n=%u" % (o["f"], o["T"], o["Vpp"], o["Vmax"], o["Vmin"], o["Vort"],
                                                 o["Vrms"], o["Vac"], o["duty"], o["tr"], o["tf"], int(o["n"])))


def m_alanlar(s: str) -> dict:
    return dict(a.split("=", 1) for a in s.split()[1:])


# ── saf Python spektrum tepesi (numpy YOK) ───────────────────────────────────
def dtft_genlik(v: list[float], w: list[float], wtop: float, f: float, hz: float) -> float:
    re = im = 0.0
    k = 2 * math.pi * f / hz
    for i, x in enumerate(v):
        a = k * i
        re += w[i] * x * math.cos(a)
        im -= w[i] * x * math.sin(a)
    return 2 * math.hypot(re, im) / wtop


def py_tepe(kodlar: list[int], adim: float, ofset: float, hz: float, f_azami: float) -> tuple[float, float, float]:
    """Hann (periyodik), DC cikarilmis; kaba DFT (nfft = 2^k ile ayni kutular) + altin oran."""
    n = len(kodlar)
    v = [k * adim - ofset for k in kodlar]
    ort = sum(v) / n
    v = [x - ort for x in v]
    w = [0.5 - 0.5 * math.cos(2 * math.pi * i / n) for i in range(n)]
    wtop = sum(w)
    nfft = 1
    while nfft < n:
        nfft *= 2
    df = hz / nfft
    en_k, en_g = 1, -1.0
    for kutu in range(1, int(f_azami / df)):
        g = dtft_genlik(v, w, wtop, kutu * df, hz)
        if g > en_g:
            en_k, en_g = kutu, g
    a, b = (en_k - 1) * df, (en_k + 1) * df
    oran = (math.sqrt(5) - 1) / 2
    c, d = b - oran * (b - a), a + oran * (b - a)
    gc, gd = dtft_genlik(v, w, wtop, c, hz), dtft_genlik(v, w, wtop, d, hz)
    for _ in range(40):
        if gc > gd:
            b, d, gd = d, c, gc
            c = b - oran * (b - a)
            gc = dtft_genlik(v, w, wtop, c, hz)
        else:
            a, c, gc = c, d, gd
            d = a + oran * (b - a)
            gd = dtft_genlik(v, w, wtop, d, hz)
    f = (a + b) / 2
    return f, dtft_genlik(v, w, wtop, f, hz), df


# ── kayitlar: iki osiloskop oturumu (kopru/kayit_bicim.py) ───────────────────
CANLI_A = vaka("sinus_4000")          # 4000 ornek @ 83333 Hz, ~1 kHz
CANLI_B = vaka("kare50_tam_4000")     # 4000 ornek @ 10 kHz, 100 Hz kare (ASCII yolu, "Otomatik")
EGRI = [int(p.split(":")[1]) for p in FIKSTUR["ct"].split() if ":" in p and p.split(":")[0].isdigit()]


def meta(t_ms: int, hz: int, tetik: int) -> dict:
    return {"t_ms": t_ms, "sure_ms": 14, "hz": hz, "tdiv_us": 5000, "adim": ADIM, "ofset": OFSET, "tetik": tetik,
            "esik": 2048, "histerezis": 40, "kip": 1, "tetiklendi": 1, "kenar": 0, "on_yuzde": 25, "onay": 2}


def akis_kur():
    a = TK.Akis(40)
    no = {}
    # A: kart egri KURAMAMIS (kal_tab_var false) — firmware yine de sifir dizi yazar
    no["A"] = a.basla(3, 0, 1790100000, 500000, 4)
    a.ekle(KB.T_OLAY, no["A"], KB.olay_paketle({"tur": KB.KO_SKOP_KAL, "kart_ms": 500001, "mv": [0] * 17}))
    kod = CANLI_A["ham"]
    no["A_sira"] = a.ekle(KB.T_SKOP, no["A"], KB.skop_paketle({"no": 1, "ilk": 0, "toplam": len(kod), "parca": 0,
                                                              "meta": meta(500100, 83333, 1000), "kodlar": kod[:1500]}))
    a.ekle(KB.T_SKOP, no["A"], KB.skop_paketle({"no": 1, "ilk": 1500, "toplam": len(kod), "parca": 1, "kodlar": kod[1500:]}))
    a.not_(no["A"], KB.KNT_AD, 0, "sinüs 1 kHz")
    a.bitir(no["A"], 0, 1)
    # B: GERCEK KARTIN yakalamasi + egrisi (fikstur; kart M satirini egriyle olcmustu)
    no["B"] = a.basla(3, 0, 1790200000, 600000, 4)
    a.ekle(KB.T_OLAY, no["B"], KB.olay_paketle({"tur": KB.KO_SKOP_KAL, "kart_ms": 600001, "mv": EGRI}))
    kf = FIKSTUR["kodlar"]
    no["B_sira"] = a.ekle(KB.T_SKOP, no["B"], KB.skop_paketle({"no": 1, "ilk": 0, "toplam": len(kf), "parca": 0,
                                                              "meta": meta(600200, 83333, 208), "kodlar": kf[:400]}))
    a.ekle(KB.T_SKOP, no["B"], KB.skop_paketle({"no": 1, "ilk": 400, "toplam": len(kf), "parca": 1, "kodlar": kf[400:]}))
    a.bitir(no["B"], 0, 1)
    return a, no


# ── sahte kart ───────────────────────────────────────────────────────────
class Kart(TK.Kart):
    def __init__(self, kayitlar):
        super().__init__(kayitlar)
        self.istemciler: list[queue.Queue] = []
        self.komut_listesi: list[str] = []
        self.gunluk = [0, 0, 0, 0]          # etkin aralik yakalama yazilamayan
        self.pil = False                    # True: Gt pil testi reddi
        self.tetiksiz = False               # True: tB -> "! tetiklenemedi"
        self.bin = b""
        self.m_gonderilen: list[str] = []

    def yay(self, satir: str) -> None:
        with self.kilit:
            for q in self.istemciler:
                q.put(satir)

    def skop_bin(self, v: dict, tetik: int) -> bytes:
        kod = v["ham"]
        b = bytearray(32 + 2 * len(kod))
        b[0:4] = b"S3B\x01"
        struct.pack_into("<H", b, 4, len(kod))
        struct.pack_into("<I", b, 8, int(v["hz"]))
        struct.pack_into("<ff", b, 12, ADIM, OFSET)
        struct.pack_into("<IHBBI", b, 20, 5000, tetik, 1, 1, 7)
        struct.pack_into(f"<{len(kod)}H", b, 32, *kod)
        return bytes(b)

    def komut(self, k: str) -> list[str]:
        self.komut_listesi.append(k)
        if k == "?":
            return ["A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=0 y_kazanc=1.000000 y_sifir=0 "
                    "sont=0.100000 i_duz=1.000000 i_ofset=0 rapor=200"]
        if k == "CT":
            return ["CT 0 kaynak=YOK"]          # canli eksen egrisiz: M = skop_olc + ofset
        if k in ("G", "G?"):
            return ["G 1 0 0 121 0 310 45 0 2900 1300 4 300 0", "GA 480 0 0 0",
                    "GT " + " ".join(map(str, self.gunluk)), "GP 0 0 0 0 0"]
        if k.startswith("Gt"):
            r = k[2:]
            if r == "d":
                if not self.gunluk[0]:
                    return ["! G: osiloskop gunlugu yok"]
                self.gunluk[0] = 0
                return [f"* G osiloskop gunlugu durdu: {self.gunluk[2]} yakalama, {self.gunluk[3]} yazilamayan"]
            if not r.isdigit() or len(r) > 7 or (int(r) != 0 and not 1000 <= int(r) <= 3600000):
                return ["! G: Gt<ms> — 0 (her tetik) ya da 1000..3600000; Gtd durdurur"]
            if self.gunluk[0]:
                return ["! G: osiloskop gunlugu zaten suruyor (Gtd)"]
            if self.pil:
                return ["! G: pil testi suruyor — yakalama ADS'i susturur, kesme denetimi durur"]
            self.gunluk = [1, int(r), 0, 0]
            return ["* G osiloskop gunlugu basladi: " + (f"{r} ms'de bir" if int(r) else "her tetikte") + " — SKOP oturumu"]
        if k == "tB":
            if self.gunluk[0]:
                return ["! skop: osiloskop gunlugu suruyor — elle yakalama yok (once Gtd)"]
            if self.tetiksiz:
                return ["! tetiklenemedi"]
            self.bin = self.skop_bin(CANLI_A, 1000)
            m = m_satiri(kart_olcum(CANLI_A))
            self.m_gonderilen.append(m)
            return [m, f"* skop yakalandi (ikili): {len(CANLI_A['ham'])} ornek @ 83333 Hz — /skop.bin"]
        if k == "ta":
            v = CANLI_B
            m = m_satiri(kart_olcum(v))
            self.m_gonderilen.append(m)
            satirlar = ["T tdiv=5/11 (5000 us/bolme) hz=10000 adet=4000 pencere_ms=400.00 esik=2048 kenar=yukselen "
                        "hist=40 on=25% kip=0 onay=2",
                        "S2 %u %lu %.6f %u %lu %u %u %.6f" % (len(v["ham"]), 10000, ADIM, 1000, 5000, 0, 1, OFSET), m]
            for i in range(0, len(v["ham"]), 16):
                satirlar.append(" ".join(str(x) for x in v["ham"][i:i + 16]))
            return satirlar + ["E"]
        if k == "w":
            return ["W 0.36314 0.36356 0.9988 1.8291 0.19876 -1.8283 -0.19859 297 0.36313 1"]
        if k.startswith("t"):
            return ["T tdiv=5/11 (5000 us/bolme) hz=20000 adet=1000 pencere_ms=50.00 esik=2048 kenar=yukselen "
                    "hist=40 on=25% kip=1 onay=2"]
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
            if yol == "/skop.bin":
                return self._gonder(200, kart.bin, "application/octet-stream") if kart.bin else self._gonder(503, b"yakalama yok")
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
            if self.headers.get("X-Olcum") != "1" or self.headers.get("X-Jeton") != JETON:
                return self._gonder(403, b"gecersiz oturum jetonu")
            for s in kart.komut(govde):        # kart komutu loop()'ta calistirir; cikti SSE'ye
                kart.yay(s)
            self._gonder(200, b"")

    class Sunucu(http.server.ThreadingHTTPServer):
        daemon_threads = True
        block_on_close = False
        allow_reuse_address = False

        def handle_error(self, *a):
            pass

    s = Sunucu(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


# ── tarayici yardimcilari ────────────────────────────────────────────────
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


def komut_bekle(t, kart: Kart, n: int, adet: int, sure: float = 5.0) -> list[str]:
    son = time.monotonic() + sure
    while time.monotonic() < son and len(kart.komut_listesi) < n + adet:
        t.bekle(0.05)
    t.bekle(0.2)
    return kart.komut_listesi[n:]


def tikla_sec(t, secici: str) -> None:
    t.js("document.querySelector(%s).click()" % json.dumps(secici))


def fare(t, tur: str, x: float, y: float, tik: int = 0) -> None:
    t.cagir("Input.dispatchMouseEvent", {"type": tur, "x": x, "y": y,
                                         "button": "left" if tur != "mouseMoved" else "none", "clickCount": tik})


def cift_tikla(t, x: float, y: float) -> None:
    fare(t, "mouseMoved", x, y)
    for tik in (1, 2):
        fare(t, "mousePressed", x, y, tik)
        fare(t, "mouseReleased", x, y, tik)


def tasma(t) -> int:
    return t.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")


PIKSEL_JS = """(() => {
  const c = document.querySelector(%s);
  if (!c || !c.width) return null;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const h = %s; const s = h.map(() => 0);
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 250) continue;
    for (let j = 0; j < h.length; j++) if (Math.abs(d[i] - h[j][0]) <= 6 && Math.abs(d[i + 1] - h[j][1]) <= 6
      && Math.abs(d[i + 2] - h[j][2]) <= 6) s[j]++; }
  return s; })()"""

OLCUM_JS = ("[...document.querySelectorAll('[data-skop-olcum] .skop-olcum-oge')]"
            ".map(e => e.querySelector('.skop-olcum-ad').textContent.trim() + '=' + e.querySelector('.skop-olcum-deger').textContent.trim())")
OLCUM_DURUM_JS = (f"(() => {{ const o = {UYG}.osilo && {UYG}.osilo.olcum; if (!o) return null;"
                  " const r = {}; for (const a of ['f','T','Vpp','Vmax','Vmin','Vort','Vrms','Vac','duty','tr','tf','n']) r[a] = o[a];"
                  " return r; })()")
DUZEN_JS = """(() => { const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
  return {l: b.left, r: b.right, t: b.top, b: b.bottom, w: b.width}; };
  return {dalga: r('canvas.surukle'), denetim: r('.skop-denetim'), spektrum: r('[data-spektrum]')}; })()"""


def tema_sec(t, ad: str, geri: str = "#/skop") -> None:
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


# ── ana akis ─────────────────────────────────────────────────────────────
def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    takim = css_takimlari()
    akis, no = akis_kur()
    kart = Kart(akis.kayitlar)
    s = sunucu_kur(kart)
    taban = f"http://{AD}:{s.server_address[1]}"
    resimler = []
    profil = None
    print("=" * 78)
    print("  3E  OSILOSKOP — TARAYICIDA, SAHTE KARTA KARSI (T3E)")
    print("=" * 78)
    print(f"     sahte kart: {taban}\n")

    def resim(ad: str) -> None:
        if goruntu:
            y = goruntu / f"{ad}.png"
            t.goruntu(str(y))
            resimler.append(y)

    try:
        with KayitliTarayici(auth_iptal=False, port=bos_port(),
                             ek_arg=[f"--host-resolver-rules=MAP {AD} 127.0.0.1"]) as t:
            profil = t.profil
            t.cagir("Log.enable")
            t.tema("dark")

            # ── 1. acilis: Osiloskop, baglanti, modul ─────────────────────
            t.git(taban + "/#/skop")
            bekle_js(t, f"{UYG}.bagli && {UYG}.skopDurum === 'hazir' && {UYG}.kayit.gt", 15)
            ok("[!] Panel #/skop ile acildi, akis kipinde BAGLANDI, osiloskop modulu (ekran/osiloskop.js) indi",
               t.js(f"{UYG}.gorunum") == "skop" and t.js(f"{UYG}.tasiyiciAdi") == "akis" and t.js(f"{UYG}.skopDurum") == "hazir",
               " ".join(kart.komut_listesi))
            t.bekle(1.0)

            # ── 2. duzen (1280): dalga solda >= 2/3, denetimler sagda ─────
            d = t.js(DUZEN_JS)
            pay = d["dalga"]["w"] / (d["dalga"]["w"] + d["denetim"]["w"])
            ok("[!] OS1 (1280 px): denetimler dalganin SAGINDA, dalga >= 2/3 genislik, yatay tasma yok",
               d["denetim"]["l"] >= d["dalga"]["r"] and pay >= 2 / 3 and tasma(t) <= 0,
               f"dalga {d['dalga']['w']:.0f} px · denetim {d['denetim']['w']:.0f} px · %{100 * pay:.0f}")
            kume = t.js("[...document.querySelectorAll('.skop-denetim > fieldset > legend')].map(l => l.textContent.trim())")
            ok("[!] OS1: kumeler sirayla Yakalama · Zaman tabani · Tetik · Yakalama gunlugu · Kalibrasyon cikisi",
               kume == ["Yakalama", "Zaman tabanı", "Tetik", "Yakalama günlüğü", "Kalibrasyon çıkışı"], str(kume))

            # ── 3. canli ikili yakalama (tB + /skop.bin) — OS4 kart M ──────
            n0 = len(kart.komut_listesi)
            tikla_sec(t, "[data-skop=yakala]")
            bekle_js(t, f"{UYG}.osilo && {UYG}.osilo.veri.length === {len(CANLI_A['ham'])} && {UYG}.osilo.olcum", 10)
            ok("[!] Yakala -> `/komut`a 'tB'; M satiri + onay -> /skop.bin cekildi (4000 ornek)",
               kart.komut_listesi[n0:n0 + 1] == ["tB"] and t.js(f"{UYG}.osilo.veri[123]") == CANLI_A["ham"][123],
               " ".join(kart.komut_listesi[n0:]))
            canli_dom = t.js(OLCUM_JS)
            kaynak = t.js("document.querySelector('.skop-olcum-kaynak').textContent.trim()")
            canli_m = t.js(OLCUM_DURUM_JS)
            ok("[!] OS4: canlida olcum kutusu KARTIN M satirindan, kaynak yaziyor",
               kaynak == "Kaynak: kartın ölçüm satırı (M)" and len(canli_dom) >= 9
               and abs(canli_m["f"] - float(m_alanlar(kart.m_gonderilen[-1])["f"])) < 1e-9, f"{kaynak} · {canli_dom[:3]}")
            koyu = takim["koyu"]
            px = t.js(PIKSEL_JS % (json.dumps("canvas.surukle"), json.dumps([list(rgb(koyu["--volt"]))])))
            ok("[!] OS2: dalga tuvali GERCEKTEN cizili (--volt pikselleri)", bool(px) and px[0] > 300, str(px))
            # spektrum: Python bagimsiz DFT
            bekle_js(t, f"{UYG}.spektrumBilgi && {UYG}.spektrumBilgi.var && {UYG}.spektrumBilgi.n === 4000", 8)
            sb = t.js(f"(() => {{ const b = {UYG}.spektrumBilgi; return {{f: b.tepe.f, g: b.tepe.genlik, df: b.df, n: b.n, nfft: b.nfft,"
                      " thd: b.thd, h: b.harmonikler.map(x => x && x.f)}; })()")
            pf, pg, pdf = py_tepe(CANLI_A["ham"], ADIM, OFSET, 83333.0, 5000.0)
            ok("[!] OS3: spektrum tepe frekansi ve genligi BAGIMSIZ Python DFT ile ayni (<= 0.05 kutu, <= %4); 4000 ornegin TAMAMI",
               sb["n"] == 4000 and sb["nfft"] == 4096 and abs(sb["f"] - pf) <= 0.05 * pdf and abs(sb["g"] - pg) <= 0.04 * pg,
               f"panel {sb['f']:.3f} Hz {sb['g']:.4f} V · python {pf:.3f} Hz {pg:.4f} V (kutu {pdf:.2f} Hz)")
            ok("[!] OS3: harmonikler temelin katlarinda (1. = tepe; gurultu tepesi harmonik sayilmiyor) ve THD sayisi var",
               sb["h"][0] == sb["f"] and all(h is None or abs(h - (j + 1) * sb["f"]) <= 1.05 * 83333 / 4000
                                             for j, h in enumerate(sb["h"]))
               and sb["thd"] >= 0, str(sb["h"]))
            pxs = t.js(PIKSEL_JS % (json.dumps("canvas.spektrum-grafik"), json.dumps([list(rgb(koyu["--volt"]))])))
            tepe_yazi = t.js("document.querySelector('[data-spektrum=tepe]').textContent.trim()")
            ok("[!] OS2: spektrum tuvali (grafik.js) GERCEKTEN cizili; tepe frekansi ekranda; x ekseni Hz yazili",
               bool(pxs) and pxs[0] > 40 and tepe_yazi.endswith("kHz")
               and t.js(f"{UYG}._skop.g.sonPlan.komutlar.some(k => k.rol === 'eksen' && /k?Hz$/.test(k.metin))") is True,
               f"{pxs} · {tepe_yazi}")
            ham = t.js(f"{UYG}.spektrumBilgi.tepe.f")
            t.js(f"(() => {{ {UYG}.yatayZoom = 8; {UYG}.yatayKaydir = 0.2; {UYG}.osiloCiz(); {UYG}.spektrumCiz(); }})()")
            t.bekle(0.3)
            ok("[!] OS3: yatay yakinlastirma spektrumu DEGISTIRMIYOR (kaynak ham kodlarin tamami, zoom penceresi degil)",
               t.js(f"{UYG}.spektrumBilgi.tepe.f") == ham and t.js(f"{UYG}.spektrumBilgi.n") == 4000)
            t.js(f"{UYG}.yatarSifirla()")
            t.js("(() => { const s = document.querySelector('[data-spektrum=birim]'); s.value = 'dbv'; s.dispatchEvent(new Event('change')); })()")
            t.bekle(0.4)
            ok("OS3: genlik birimi dBV'ye gecince eksen dBV", t.js(f"{UYG}._skop.g.sonPlan.eksenler.sol.birim") == "dBV")
            t.js("(() => { const s = document.querySelector('[data-spektrum=birim]'); s.value = 'v'; s.dispatchEvent(new Event('change')); })()")
            t.bekle(0.3)
            t.js("document.querySelector('canvas.spektrum-grafik').scrollIntoView({block: 'center'})")
            t.bekle(0.3)
            sr = t.js(f"(() => {{ const c = document.querySelector('canvas.spektrum-grafik'); const b = c.getBoundingClientRect();"
                      f" const a = {UYG}._skop.g.sonPlan.alan; const d = {UYG}._skop.g.durum;"
                      " return {x: b.left + c.clientLeft, y: b.top, ax: a.x, aw: a.w, ay: a.y, ah: a.h, t0: d.t0, t1: d.t1}; })()")
            tx = sr["ax"] + (sb["f"] - sr["t0"]) / (sr["t1"] - sr["t0"]) * sr["aw"]
            cift_tikla(t, sr["x"] + tx, sr["y"] + sr["ay"] + sr["ah"] / 2)
            okuma = bekle_js(t, "(() => { const e = document.querySelector('[data-spektrum=imlec]'); return e && e.textContent.trim(); })()", 5)

            mo = re.match(r"^A: ([\d.]+) (k?)Hz · [\d.]+ V$", okuma or "")
            f_ok = float(mo.group(1)) * (1000 if mo.group(2) else 1) if mo else float("nan")
            px_hz = (sr["t1"] - sr["t0"]) / sr["aw"]
            ok("OS3: spektrumda GERCEK fare cift tiki tiklanan piksele A imleci koyuyor; okuma (Hz + V) altta yaziyor",
               bool(mo) and abs(f_ok - sb["f"]) <= 2 * px_hz + pdf, f"{okuma} (tepe {sb['f']:.1f} Hz, 1 px = {px_hz:.0f} Hz)")
            resim("1-skop-canli-koyu")

            # ── 4. ASCII yolu (Otomatik: ta -> S2 dokumu) ─────────────────
            n1 = len(kart.komut_listesi)
            tikla_sec(t, "[data-skop=otomatik]")
            bekle_js(t, f"{UYG}.osilo && {UYG}.osilo.hz === 10000 && {UYG}.osilo.veri.length === 4000 && !{UYG}.osiloBekliyor", 10)
            mb = t.js(OLCUM_DURUM_JS)
            mk = m_alanlar(kart.m_gonderilen[-1])
            ok("[!] OS7: Otomatik -> 'ta'; ASCII S2 dokumu cizildi, M satiri olcume girdi (B40/B43 yolu korunuyor)",
               kart.komut_listesi[n1:n1 + 1] == ["ta"] and abs(mb["f"] - float(mk["f"])) < 1e-9
               and abs(mb["duty"] - float(mk["duty"])) < 1e-9, f"{mb['f']} / {mk['f']}")

            # ── 5. OS5 gunluk: Gt0 / Gtd / Gt5000, GT durumu, ret ─────────
            n2 = len(kart.komut_listesi)
            tikla_sec(t, "[data-gunluk=kip-tetik]")
            tikla_sec(t, "[data-gunluk=baslat]")
            bekle_js(t, f"{UYG}.skopGunlukAktif", 5)
            k2 = komut_bekle(t, kart, n2, 2)
            durum = t.js("document.querySelector('[data-gunluk=durum]').textContent.trim()")
            kapali = t.js("document.querySelector('[data-skop=yakala]').disabled && document.querySelector('[data-skop=otomatik]').disabled")
            ok("[!] OS5: 'Her tetikte' + Baslat -> `/komut`a 'Gt0' + 'G?'; durum GT satirindan 'Suruyor: her tetikte'; elle yakalama kapali",
               k2[:2] == ["Gt0", "G?"] and durum == "Sürüyor: her tetikte · 0 yakalama" and kapali is True, f"{' '.join(k2)} · {durum}")
            n3 = len(kart.komut_listesi)
            tikla_sec(t, "[data-gunluk=durdur]")
            bekle_js(t, f"!{UYG}.skopGunlukAktif", 5)
            k3 = komut_bekle(t, kart, n3, 2)
            ok("[!] OS5: Durdur -> 'Gtd' + 'G?'; durum 'Gunluk kapali'", k3[:2] == ["Gtd", "G?"]
               and t.js("document.querySelector('[data-gunluk=durum]').textContent.trim()") == "Günlük kapalı", " ".join(k3))
            tikla_sec(t, "[data-gunluk=kip-aralik]")
            bekle_js(t, "!!document.querySelector('[data-gunluk=saniye]')", 3)
            t.js("(() => { const e = document.querySelector('[data-gunluk=saniye]'); e.value = '5'; e.dispatchEvent(new Event('input')); })()")
            t.bekle(0.2)
            n4 = len(kart.komut_listesi)
            tikla_sec(t, "[data-gunluk=baslat]")
            bekle_js(t, f"{UYG}.skopGunlukAktif", 5)
            k4 = komut_bekle(t, kart, n4, 2)
            ok("[!] OS5: 'Her N saniyede' 5 s -> 'Gt5000'; durum 'her 5 s'", k4[:2] == ["Gt5000", "G?"]
               and t.js("document.querySelector('[data-gunluk=durum]').textContent.trim()") == "Sürüyor: her 5 s · 0 yakalama",
               " ".join(k4))
            n5 = len(kart.komut_listesi)
            tikla_sec(t, "[data-gunluk=durdur]")
            bekle_js(t, f"!{UYG}.skopGunlukAktif", 5)
            komut_bekle(t, kart, n5, 2)
            kart.pil = True
            n6 = len(kart.komut_listesi)
            tikla_sec(t, "[data-gunluk=baslat]")
            ret = bekle_js(t, "(() => { const e = document.querySelector('[data-gunluk=uyari]'); return e && e.dataset.tur === 'kart' && e.textContent.trim(); })()", 5)
            komut_bekle(t, kart, n6, 2)
            kart.pil = False
            ok("[!] OS5 (E9): kartin `! G:` reddi gunluk kumesinde OLDUGU GIBI",
               ret == "Kart reddetti: ! G: pil testi suruyor — yakalama ADS'i susturur, kesme denetimi durur", str(ret))
            t.js("(() => { const e = document.querySelector('[data-gunluk=saniye]'); e.value = '0.5'; e.dispatchEvent(new Event('input')); })()")
            t.bekle(0.2)
            n7 = len(kart.komut_listesi)
            tikla_sec(t, "[data-gunluk=baslat]")
            t.bekle(0.6)
            uy = t.js("(() => { const e = document.querySelector('[data-gunluk=uyari]'); return e && e.dataset.tur + '|' + e.textContent.trim(); })()")
            ok("OS5: 0.5 s (kartin siniri disi) GONDERILMIYOR, panel sebebi yaziyor",
               len(kart.komut_listesi) == n7 and uy == "panel|Aralık 1 … 3600 s olmalı (kartın sınırı).", str(uy))
            kart.tetiksiz = True
            tikla_sec(t, "[data-skop=yakala]")
            sret = bekle_js(t, "(() => { const e = document.querySelector('[data-skop-ret]'); return e && e.textContent.trim(); })()", 6)
            kart.tetiksiz = False
            ok("[!] Elle yakalamanin reddi (`! tetiklenemedi`) Yakalama kumesinde oldugu gibi",
               sret == "Kart reddetti: ! tetiklenemedi", str(sret))
            n8 = len(kart.komut_listesi)
            t.js("[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Hızlı ölçüm yap').click()")
            bekle_js(t, f"{UYG}.hizli && {UYG}.hizli.p > 0", 5)
            ok("OS7: hizli olcum (gercek guc / PF) yerinde: 'w' -> W satiri ekranda",
               "w" in kart.komut_listesi[n8:]
               and any("0.3631" in x for x in t.js("[...document.querySelectorAll('.olcumler .olcum.w .deger')].map(e => e.textContent)")))
            # canli A'yi yeniden yakala (kayitliyla karsilastirmak icin DOM)
            tikla_sec(t, "[data-skop=yakala]")
            bekle_js(t, f"{UYG}.osilo && {UYG}.osilo.hz === 83333 && !{UYG}.osiloBekliyor && {UYG}.osilo.olcum", 10)
            canli_dom = t.js(OLCUM_JS)
            resim("2-skop-gunluk")

            # ── 6. Kayitlar: esitle (IndexedDB), B'yi ac, "Osiloskopta ac" ──
            t.js("location.hash = '#/kayitlar'")
            esit = bekle_js(t, "document.querySelectorAll('.kl-satir').length >= 2"
                               " && document.querySelectorAll('.kl-nerede-ikisi').length >= 2", 20)
            ok("OS6 on kosul: Kayitlar iki osiloskop oturumunu esitledi (IndexedDB, 'ikisinde')", bool(esit))
            t.bekle(1.0)
            t.js(f"location.hash = '#/kayit/{no['B']}'")
            bekle_js(t, "!!document.querySelector('a[data-skop-ac]')", 10)
            href = t.js("document.querySelector('a[data-skop-ac]').getAttribute('href')")
            ok("[!] OS6: 3C yakalama tablosunda 'Osiloskopta ac' baglantisi kimlikli adresle",
               href == f"#/skop/kayit/{no['B']}/{no['B_sira']}@{kart.kimlik}", str(href))
            t.js("document.querySelector('a[data-skop-ac]').click()")
            bekle_js(t, f"{UYG}.skopKayitli && {UYG}.osilo && {UYG}.osilo.veri.length === {len(FIKSTUR['kodlar'])}", 10)
            t.bekle(0.6)
            serit = t.js("(() => { const e = document.querySelector('[data-skop-kayitli]'); return e && e.textContent.replace(/\\s+/g, ' ').trim(); })()")
            ok("[!] OS6: kayitli yakalama Osiloskop'ta ARSIV seridiyle ('canli degil'), adres rotada",
               t.js("location.hash") == href and t.js(f"{UYG}.gorunum") == "skop" and bool(serit)
               and f"Kayıt #{no['B']} · yakalama 1" in serit and "canlı değil" in serit, str(serit))
            pb = t.js(OLCUM_DURUM_JS)
            pm = m_alanlar(m_satiri(pb))
            km = m_alanlar(FIKSTUR["m"])
            fark = [a for a in ("f", "T", "Vpp", "Vmax", "Vmin", "Vort", "Vrms", "Vac", "n") if pm[a] != km[a]]
            ok("[!] OS4 GERCEK KART: egrili kayitli yakalamada panelin hesabi (tarayicida) kartin M satiriyla basilan haneye kadar AYNI",
               not fark and t.js("document.querySelector('.skop-olcum-kaynak').dataset.kaynak") == "panel",
               ("farkli: " + " ".join(f"{a} {pm[a]}/{km[a]}" for a in fark)) if fark else m_satiri(pb))
            ok("OS6: kayitli yakalamanin rozeti 'eksen kaydin egrisiyle' (canli CT olmadigi halde)",
               t.js("document.querySelector('.kal-rozet').textContent.trim()") == "eksen kaydın eğrisiyle")
            bekle_js(t, f"{UYG}.spektrumBilgi && {UYG}.spektrumBilgi.n === {len(FIKSTUR['kodlar'])}", 5)
            ok("OS6: spektrum da kayitli yakalamadan (CAL 1 kHz -> tepe ~1 kHz)",
               abs(t.js(f"{UYG}.spektrumBilgi.tepe.f") - 1000) < 15, str(t.js(f"{UYG}.spektrumBilgi.tepe.f")))
            resim("3-skop-kayitli-egrili")

            # A: dogrudan adres (egrisiz) — canli ile AYNI yakalama
            t.js(f"location.hash = '#/skop/kayit/{no['A']}/{no['A_sira']}'")
            bekle_js(t, f"{UYG}.skopKayitli && {UYG}.skopKayitli.oturum === {no['A']} && {UYG}.osilo.veri.length === 4000", 10)
            t.bekle(0.5)
            pa = m_satiri(t.js(OLCUM_DURUM_JS))
            kayitli_dom = t.js(OLCUM_JS)
            ok("[!] OS4: AYNI yakalama — canlida kartin M satiri, kayittan acilinca panelin skopOlcKart'i: printf bicimiyle BIREBIR",
               pa == kart.m_gonderilen[-1], f"panel  {pa}\n      kart   {kart.m_gonderilen[-1]}")
            ok("[!] OS4: ... ve ekrandaki olcum kutusu (biçimli) canlidakiyle AYNI", kayitli_dom == canli_dom,
               f"{kayitli_dom} vs {canli_dom}")
            ok("OS6: egrisiz kayit (kart sifir dizi yazmis) — rozet 'eksen HAM (kayitta egri yok)'",
               t.js("document.querySelector('.kal-rozet').textContent.trim()") == "eksen HAM (kayıtta eğri yok)")
            t.js("history.back()")
            bekle_js(t, f"{UYG}.skopKayitli && {UYG}.skopKayitli.oturum === {no['B']}", 8)
            ok("OS6: geri tusu onceki kayitli yakalamaya donuyor (B)", t.js(f"{UYG}.skopKayitli.oturum") == no["B"])
            n9 = len(kart.komut_listesi)
            tikla_sec(t, "[data-skop=canliya-don]")
            bekle_js(t, f"!{UYG}.skopKayitli && {UYG}.osilo && {UYG}.osilo.hz === 83333 && !{UYG}.osiloBekliyor", 10)
            ok("[!] OS6: 'Canliya don' -> adres #/skop, serit kalkti, yeni canli yakalama (tB)",
               t.js("location.hash") == "#/skop" and "tB" in kart.komut_listesi[n9:]
               and t.js("!document.querySelector('[data-skop-kayitli]')") is True
               and t.js("document.querySelector('.skop-olcum-kaynak').dataset.kaynak") == "kart")

            # ── 7. uc gorunum ─────────────────────────────────────────────
            onceki = "koyu"
            for ad in TEMALAR:
                tema_sec(t, ad)
                tikla_sec(t, "[data-skop=yakala]")
                bekle_js(t, f"!{UYG}.osiloBekliyor", 6)
                t.bekle(0.5)
                hedef = [list(rgb(takim[ad]["--volt"]))] + ([list(rgb(takim[onceki]["--volt"]))] if ad != onceki else [])
                pd_ = t.js(PIKSEL_JS % (json.dumps("canvas.surukle"), json.dumps(hedef)))
                ps_ = t.js(PIKSEL_JS % (json.dumps("canvas.spektrum-grafik"), json.dumps(hedef)))
                ok(f"[!] {ad}: dalga ve spektrum tuvali YENI --volt rengiyle" + (f", eski ({onceki}) yok" if ad != onceki else ""),
                   bool(pd_) and bool(ps_) and pd_[0] > 300 and ps_[0] > 40 and (ad == onceki or (pd_[1] == 0 and ps_[1] == 0)),
                   f"dalga {pd_} spektrum {ps_}")
                resim(f"4-skop-{ad}")
                onceki = ad

            # ── 8. telefon (390 px): denetimler dalganin altinda ──────────
            t.ekran(390, 844)
            t.bekle(0.8)
            tasmalar = {}
            for ad in TEMALAR:
                tema_sec(t, ad)
                tasmalar[ad] = tasma(t)
            d2 = t.js(DUZEN_JS)
            ok("[!] OS1 (390 px): denetimler dalganin ALTINDA, spektrum denetimlerin altinda; uc gorunumde yatay tasma YOK",
               d2["denetim"]["t"] >= d2["dalga"]["b"] and d2["spektrum"]["t"] >= d2["denetim"]["b"]
               and all(v <= 0 for v in tasmalar.values()), f"{d2} {tasmalar}")
            resim("5-skop-telefon")
            t.cagir("Emulation.clearDeviceMetricsOverride")

            # ── 9. konsol ─────────────────────────────────────────────────
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
