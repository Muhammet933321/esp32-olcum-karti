# -*- coding: utf-8 -*-
"""3D — CANLI + KABUK + KAYIT DENETIMI TARAYICIDA (T3D): sahte karta karsi uctan uca.

    python tarayici_canli.py                    # sessiz, 0/1 doner
    python tarayici_canli.py --goruntu DIZIN    # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B7 (`test_arayuz3.js` bolum 25) saf mantigi ve kaynak
   metnini node'da sinar; gercek Vue'yu, gercek SSE akisini, cekmecenin gercek
   odak davranisini, tuvalin GERCEKTEN cizildigini, `/komut`a giden METNI ve
   kartin `! G:` reddinin EKRANA dustugunu sinayamaz.

Sahte kart (bu dosyada, Python): arayuz3 + `/ortak/` + `/akis` (SSE: `kimlik`,
200 ms'de bir `D`, kayitta saniyede bir `G`, komut yanitlari) + `/komut`
(jeton denetimli; `G`/`?`/`CT` komutlarini kartin METINLERIYLE yanitlar, gelen
her komutu sayar). D satirlari belirlenimci; okuma kartlarinin "10 s min … maks"
beklenen degeri panelden DEGIL buradaki gonderim kaydindan hesaplanir (sayfanin
kendi hesabiyla karsilastirilsaydi test kendini dogrulardi).

Sayfa `http://olcum.test:<port>/` (Edge `--host-resolver-rules`): kartin sayfasi
gibi localhost DISI — panel kendiliginden akis kipine gecip baglanir.
"""
from __future__ import annotations

import http.server
import json
import queue
import shutil
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
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tarayici_tema import KayitliTarayici, bos_port, css_takimlari, rgb, TEMALAR  # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
AD = "olcum.test"
JETON = "jeton3d"
BEKLENEN_404 = ("/durum", "/pil", "/favicon.ico")
HIZLAR = (0, 20, 100, 200, 1000, 10000, 60000)
AFIS = "Olcum Karti — Asama 3 (CIFT YONLU on uc)"
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


# ── sahte kart ───────────────────────────────────────────────────────────
class Kart:
    """D akisi + kayit motoru (firmware'in G satiri bicimi ve ret metinleri)."""

    def __init__(self):
        self.kilit = threading.Lock()
        self.istemciler: list[queue.Queue] = []
        self.komutlar: list[str] = []
        self.gonderilen: list[tuple] = []        # (ms, v, i, w, wh)
        self.k = 0
        self.ms0 = 1000
        self.wh = 0.0
        self.duraklat = False
        self.pil = False                          # True: Gb/Gd pil testi reddi
        self.dusen = 0
        self.durum, self.oturum, self.nokta, self.sonraki = 1, 0, 0, 121
        self.onaysiz = 45
        self.hiz = 200
        self.son_g = 0.0
        self.plan = [0, 0, 0, 0, 0]

    # SSE yayini
    def yay(self, satir: str) -> None:
        with self.kilit:
            for q in self.istemciler:
                q.put(satir)

    def g_satiri(self) -> str:
        return (f"G {self.durum} {self.oturum} {self.nokta} {self.sonraki} 0 310 {self.onaysiz} {self.dusen}"
                " 2900 1300 4 300 0")

    def d_uret(self) -> None:
        """200 ms'de bir D; kayitta saniyede bir G."""
        while not DUR.is_set():
            time.sleep(0.2)
            if self.duraklat:
                continue
            k = self.k
            self.k += 1
            ms = self.ms0 + 200 * k
            v = round(12 + 0.01 * (k % 13), 4)
            i = round(0.1 + 0.001 * (k % 7), 6)
            w = round(v * i, 5)
            self.wh += w * 0.2 / 3600
            self.gonderilen.append((ms, v, i, w, round(self.wh, 7)))
            self.yay(f"D {v:.4f} {i:.6f} {w:.5f} {self.wh * 3600:.4f} {self.wh:.7f} {ms} 172 0 0")
            if self.durum == 2 and time.monotonic() - self.son_g >= 1.0:
                self.son_g = time.monotonic()
                self.nokta += max(1, 1000 // self.hiz) if self.hiz else 500
                self.yay(self.g_satiri())

    def yeniden_baslat(self) -> None:
        """Kart yeniden basladi: afis + millis sifirdan (kayit DEVAM ile surer)."""
        self.yay(AFIS)
        self.ms0 = 500 - 200 * self.k

    def komut(self, k: str) -> list[str]:
        self.komutlar.append(k)
        if k == "?":
            return ["A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=0 y_kazanc=1.000000 y_sifir=0 "
                    "sont=0.100000 i_duz=1.000000 i_ofset=0 rapor=200"]
        if k == "CT":
            return ["CT 0 kaynak=YOK"]
        if not k.startswith("G"):
            return ["* tamam"]
        alt = k[1:2]
        if alt in ("", "?"):
            return [self.g_satiri(), "GA 480 0 0 0", "GT 0 0 0 0", "GP " + " ".join(map(str, self.plan))]
        if alt == "b":
            if self.pil:
                return ["! G: pil testi suruyor — kaydi zaten acik; durdurmak icin p0"]
            h = k[2:]
            if not h.isdigit() or int(h) not in HIZLAR:
                return ["! G: hiz 0 (her ornek) / 20/100/200/1000/10000/60000 ms olmali"]
            self.durum, self.oturum, self.nokta, self.hiz = 2, self.sonraki, 0, int(h)
            self.sonraki += 1
            self.son_g = time.monotonic()
            return ["* G istek kuyrukta — sonuc G satirinda", self.g_satiri()]
        if alt == "d":
            if self.pil:
                return ["! G: pil testi suruyor — testi p0 ile durdur (kayit onunla kapanir)"]
            self.durum, self.oturum = 1, 0
            return ["* G istek kuyrukta — sonuc G satirinda", self.g_satiri()]
        if alt == "n":
            return ["* G not kuyrukta (verilmemis oturuma yazilmaz; sonuc esitlenen dosyada)"]
        if alt == "p":
            r = k[2:]
            if r == "-":
                self.plan = [0, 0, 0, 0, 0]
                return ["* G plan iptal"]
            p = r.split(",")
            if len(p) != 3 or not all(x.isdigit() for x in p):
                return ["! G: Gp<unix>,<sure_s>,<hiz_ms> ya da Gp+<saniye>,<sure_s>,<hiz_ms>; Gp- iptal"]
            self.plan = [1, int(p[0]), int(p[1]), int(p[2]), 0]
            return [f"* G plan kuruldu: {p[0]} (+0 s), {p[1]} s, {p[2]} ms — GP durum"]
        return ["! G: alt komut b<ms> d ? o<sira> F!  a<id> e<id> n<id> x<id>:<sira>  t<ms> td  p<plan>"]


MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".png": "image/png", ".json": "application/json"}
DUR = threading.Event()


def sunucu_kur(kart: Kart):
    class Isleyici(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _gonder(self, kod: int, govde: bytes, tur: str = "text/plain; charset=utf-8"):
            self.send_response(kod)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(govde)

        def do_GET(self):
            yol = urllib.parse.urlparse(self.path).path
            if yol == "/akis":
                q: queue.Queue = queue.Queue()
                with kart.kilit:
                    kart.istemciler.append(q)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(f'retry: 1000\n\nevent: kimlik\ndata: {{"jeton":"{JETON}","surucu":true}}\n\n'
                                     .encode())
                    self.wfile.flush()
                    while not DUR.is_set():
                        try:
                            s = q.get(timeout=1.0)
                            self.wfile.write(("data: " + s + "\n\n").encode("utf-8"))
                        except queue.Empty:
                            self.wfile.write(b": nabiz\n\n")
                        self.wfile.flush()
                except OSError:
                    pass
                finally:
                    with kart.kilit:
                        if q in kart.istemciler:
                            kart.istemciler.remove(q)
                self.close_connection = True
                return
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
            if len(govde.encode("utf-8")) > 175:
                return self._gonder(413, "komut cok uzun (en fazla 175 karakter)".encode())
            satirlar = kart.komut(govde)
            # kart komutu loop()'ta calistirir; ciktisi Serial aynasindan SSE'ye duser
            for s in satirlar:
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


def komut_bekle(t, kart: "Kart", n: int, adet: int, sure: float = 5.0) -> list[str]:
    """Karta `n`. komuttan sonra en az `adet` komut ulasana dek bekle (panel komutu ve
    ardindaki `G?` iki AYRI HTTP istegi — biri gelmeden saymak yaris olurdu)."""
    son = time.monotonic() + sure
    while time.monotonic() < son and len(kart.komutlar) < n + adet:
        t.bekle(0.05)
    t.bekle(0.2)
    return kart.komutlar[n:]


def fare(t, tur: str, x: float, y: float, tik: int = 0) -> None:
    t.cagir("Input.dispatchMouseEvent", {"type": tur, "x": x, "y": y,
                                         "button": "left" if tur != "mouseMoved" else "none", "clickCount": tik})


def tikla(t, x: float, y: float) -> None:
    fare(t, "mouseMoved", x, y)
    fare(t, "mousePressed", x, y, 1)
    fare(t, "mouseReleased", x, y, 1)


def cift_tikla(t, x: float, y: float) -> None:
    fare(t, "mouseMoved", x, y)
    for tik in (1, 2):
        fare(t, "mousePressed", x, y, tik)
        fare(t, "mouseReleased", x, y, tik)


def merkez(t, secici: str) -> dict | None:
    return t.js("(() => { const e = document.querySelector(%s); if (!e) return null; const b = e.getBoundingClientRect();"
                " return {x: b.left + b.width / 2, y: b.top + b.height / 2, w: b.width, h: b.height}; })()"
                % json.dumps(secici))


def tus(t, ad: str, kod: str) -> None:
    for tur in ("rawKeyDown", "keyUp"):
        t.cagir("Input.dispatchKeyEvent", {"type": tur, "key": ad, "code": kod,
                                           "windowsVirtualKeyCode": 27 if ad == "Escape" else 0})


def tasma(t) -> int:
    """Yatay tasma (px) — clientWidth temelli (mobil emulasyonda innerWidth icerige buyuyor)."""
    return t.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def durdur(t) -> None:
    """WIG: Durdur IKI ASAMALI — [data-kd=durdur] silahlar, [data-kd=durdur-eminim] gonderir."""
    t.js("document.querySelector('[data-kd=durdur]').click()")
    bekle_js(t, "!!document.querySelector('[data-kd=durdur-eminim]')", 4)
    t.js("document.querySelector('[data-kd=durdur-eminim]').click()")


def deger_yaz(sec: str, deger: str, olay: str = "input") -> str:
    return ("(() => { const e = document.querySelector(%s); if (!e) return 'yok'; e.value = %s;"
            " e.dispatchEvent(new Event(%s)); return 'ok'; })()" % (json.dumps(sec), json.dumps(deger), json.dumps(olay)))


PIKSEL_JS = """(() => {
  const c = document.querySelector('canvas.canli-grafik');
  if (!c || !c.width) return null;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const h = %s; const s = h.map(() => 0);
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 250) continue;
    for (let j = 0; j < h.length; j++) if (Math.abs(d[i] - h[j][0]) <= 6 && Math.abs(d[i + 1] - h[j][1]) <= 6
      && Math.abs(d[i + 2] - h[j][2]) <= 6) s[j]++; }
  return s; })()"""


def tema_sec(t, ad: str) -> None:
    yazi = ["Koyu", "Açık", "Ön panel"][TEMALAR.index(ad)]
    t.js("location.hash = '#/ayar/dil-gorunum'")   # 3H: tema dugmeleri 'Dil ve gorunum' bolumunde
    t.bekle(0.3)
    t.js("[...document.querySelectorAll('button')].find(x => x.textContent.trim() === %s).click()" % json.dumps(yazi))
    bekle_js(t, f"document.documentElement.dataset.tema === {json.dumps(ad)}", 5)
    t.js("location.hash = '#/canli'")
    t.bekle(0.8)


def on_saniye_py(kart: Kart, son_ms: int) -> dict:
    """Panelden BAGIMSIZ: son 10 s (son noktanin ms'ine gore) min/maks, panelin bicimiyle."""
    pencere = [x for x in kart.gonderilen if son_ms - 10000 <= x[0] <= son_ms]
    v = [x[1] for x in pencere]
    i = [x[2] for x in pencere]
    w = [x[3] for x in pencere]
    son = next(x for x in kart.gonderilen if x[0] == son_ms)

    def birimli(deger, taban, sec):
        # panelin kurali (app.js akimBirim / gucBirim): ANA degerin buyuklugu birimi secer
        a = abs(sec)
        k, b, h = (1, taban, 4) if a >= 1 else (1e3, "m" + taban, 2) if a >= 1e-3 else (1e6, "µ" + taban, 0)
        return f"{deger * k:.{h}f} {b}"
    return {
        "v": f"10 s: {min(v):.3f} V … {max(v):.3f} V",
        "i": f"10 s: {birimli(min(i), 'A', son[2])} … {birimli(max(i), 'A', son[2])}",
        "w": f"10 s: {birimli(min(w), 'W', son[3])} … {birimli(max(w), 'W', son[3])}",
    }


# ── ana akis ─────────────────────────────────────────────────────────────
def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    takim = css_takimlari()
    kart = Kart()
    s = sunucu_kur(kart)
    threading.Thread(target=kart.d_uret, daemon=True).start()
    taban = f"http://{AD}:{s.server_address[1]}"
    resimler = []
    print("=" * 78)
    print("  3D  CANLI + KABUK + KAYIT DENETIMI — TARAYICIDA, SAHTE KARTA KARSI (T3D)")
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
            t.cagir("Log.enable")
            t.tema("dark")

            # ── 1. acilis: kendiliginden baglanti, serit, G? bir kez ───────
            t.git(taban + "/")
            bekle_js(t, f"{UYG}.bagli && {UYG}.gecmis.length > 25 && {UYG}.canliDurum === 'hazir'", 15)
            ok("[!] Panel kartin adresinden acildi, akis kipinde BAGLANDI, Canli varsayilan ekran",
               t.js(f"{UYG}.tasiyiciAdi") == "akis" and t.js(f"{UYG}.bagli") is True
               and t.js(f"{UYG}.gorunum") == "canli" and t.js("!document.querySelector('#uyg').hasAttribute('v-cloak')"))
            ser = t.js("({ad: [...document.querySelectorAll('#serit .gorunum-sekme')].map(a => a.textContent.trim()),"
                       " etkin: (document.querySelector('#serit .gorunum-sekme[aria-current=page]') || {}).textContent,"
                       " rozet: document.querySelector('#serit .rozet').textContent.trim(),"
                       " alt: document.querySelector('#serit .serit-alt-ad').textContent.trim(),"
                       " esit: document.querySelector('#serit .serit-alt').textContent.trim(),"
                       " gorunur: getComputedStyle(document.querySelector('#serit')).visibility,"
                       " ust: getComputedStyle(document.querySelector('.ust')).display})")
            ok("[!] D1/KR6: sol serit — 7 baglanti (3G: Karsilastirma), Canli etkin, 'Cevrimici · WiFi', yer, ust cubuk gizli",
               ser["ad"] == ["Canlı", "Osiloskop", "Pil testi", "Kayıtlar", "Karşılaştırma", "Ayarlar", "Konsol"]
               and (ser["etkin"] or "").strip() == "Canlı" and ser["rozet"] == "Çevrimiçi · WiFi"
               and AD in ser["alt"] and ser["gorunur"] == "visible" and ser["ust"] == "none", json.dumps(ser, ensure_ascii=False))
            ok("[!] D1: alt bilgi = G satirinin `onaysiz`i (sahte kart binde 45 -> %4.5)",
               bekle_js(t, "document.querySelector('#serit .serit-alt').textContent.trim() === 'Eşitlenmemiş: %4.5'", 5) is True,
               t.js("document.querySelector('#serit .serit-alt').textContent.trim()"))
            t.bekle(6.0)
            ok("[!] D5: `G?` baglaninca TAM BIR KEZ; 6 s bosta yeni `G?` yok (yoklama yok)",
               kart.komutlar.count("G?") == 1 and kart.komutlar[:3] == ["?", "CT", "G?"], " ".join(kart.komutlar))

            # ── 2. okuma kartlari (D2) + grafik (D3) ──────────────────────
            kart.duraklat = True
            t.bekle(0.8)
            son_ms = t.js(f"{UYG}.kartMs")
            py = on_saniye_py(kart, son_ms)
            dom = t.js("({v: document.querySelector('.olcum.v .on-saniye').textContent.trim(),"
                       " i: document.querySelector('.olcum.i .on-saniye').textContent.trim(),"
                       " w: document.querySelector('.olcum.w .on-saniye').textContent.trim(),"
                       " e: document.querySelector('.olcum.e .on-saniye').textContent.trim(),"
                       " vd: document.querySelector('.olcum.v .deger').textContent.trim()})")
            son = next(x for x in kart.gonderilen if x[0] == son_ms)
            ok("[!] D2: okuma kartlarinin '10 s: min … maks'i sahte kartin GONDERDIKLERINDEN (Python) hesapla ayni",
               dom["v"] == py["v"] and dom["i"] == py["i"] and dom["w"] == py["w"] and dom["e"].startswith("10 s: ")
               and dom["vd"].startswith(f"{son[1]:.3f}"), json.dumps({"dom": dom, "py": py}, ensure_ascii=False))
            kart.duraklat = False
            koyu = takim["koyu"]
            px = t.js(PIKSEL_JS % json.dumps([list(rgb(koyu["--volt"])), list(rgb(koyu["--amper"]))]))
            ok("[!] D3: canli tuval (grafik.js) GERCEKTEN cizili: --volt ve --amper pikselleri",
               bool(px) and px[0] > 80 and px[1] > 80, str(px))
            lej = t.js("[...document.querySelectorAll('.lejant > span')].map(s => s.textContent.trim())")
            ok("D3: lejant (HTML) V ve I icin 'tepe …'", len(lej or []) == 2 and all("tepe" in x for x in lej), str(lej))
            resim("1-canli-koyu")

            # ── 2b. Y ekseni olcegi (2026-10-06): oto / 0'dan / elle, kanal basina, hatirlanir ──
            EKS = f"(() => {{ const e = {UYG}._canli.g.sonPlan.eksenler; return {{sol: [e.sol.min, e.sol.maks],"\
                  f" sag: e.sag ? [e.sag.min, e.sag.maks] : null}}; }})()"
            oto = t.js(EKS)
            t.js(deger_yaz("select[data-olcek=sol]", "elle", "change"))
            bekle_js(t, "document.querySelectorAll('[data-olcek=sol] ~ input').length === 2", 3)
            t.js("(() => { const k = document.querySelectorAll('[data-olcek=sol] ~ input');"
                 " for (const [el, v] of [[k[0], '0'], [k[1], '10']]) { el.value = v;"
                 " el.dispatchEvent(new Event('input', {bubbles: true})); } })()")
            elle = bekle_js(t, f"(({EKS}).sol + '') === '0,10' && ({EKS})", 3)
            kayit = t.js("localStorage.getItem('olcum.yOlcek')")
            ok("[!] OLCEK: sol eksen 'Elle 0–10' -> eksen TAM [0, 10], sag eksen otomatikte kalir, tercih kaydedildi",
               bool(elle) and elle["sag"] == oto["sag"] and (json.loads(kayit or "{}").get("v") or {}) == {"kip": "elle", "min": 0, "maks": 10},
               json.dumps({"oto": oto, "elle": elle, "kayit": kayit}))
            t.js(deger_yaz("select[data-olcek=sol]", "sifir", "change"))
            sif = bekle_js(t, f"({EKS}).sol[0] === 0 && ({EKS})", 3)
            ok("OLCEK: '0'dan' -> alt sinir 0, ust otomatik (sahte kart ~12 V)",
               bool(sif) and sif["sol"][1] > 12.1 and sif["sol"][1] < 15, json.dumps(sif))
            t.js(deger_yaz("select[data-olcek=sol]", "oto", "change"))
            geri = bekle_js(t, f"({EKS}).sol[0] > 1 && ({EKS})", 3)
            ok("OLCEK: 'Otomatik'e donunce dar otomatik olcek geri gelir",
               bool(geri) and geri["sol"][0] > 11, json.dumps(geri))

            # ── 2c. "ⓘ Baglanti" penceresi (2026-10-06): neyi nereye takacagin — kutunun on paneli ──
            YUKLU = "performance.getEntriesByType('resource').some(e => /baglanti(_veri)?\\.js/.test(e.name))"
            bas = t.js(f"({{acik: !!document.querySelector('.baglanti-bilgi'), yuklu: {YUKLU},"
                       " dugme: (document.querySelector('[data-bilgi=canli]') || {}).textContent,"
                       " exp: (document.querySelector('[data-bilgi=canli]') || {getAttribute: () => null}).getAttribute('aria-expanded')})")
            ok("[!] BAGLANTI: pencere KAPALI baslar, resimler ACILISTA INMEZ (baglanti*.js istenmedi), dugme var",
               bas["acik"] is False and bas["yuklu"] is False and "Bağlantı" in (bas["dugme"] or "")
               and bas["exp"] == "false", json.dumps(bas, ensure_ascii=False))
            BOY = ("(() => { const p = document.querySelector('.bb-pencere'); if (!p) return null;"
                   " const r = p.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })()")
            baslik_h0 = t.js("document.querySelector('main.gorunum:not([style*=\"none\"]) .baslik').getBoundingClientRect().height")
            t.js("document.querySelector('[data-bilgi=canli]').click()")
            ac = bekle_js(t, "(() => { const b = document.querySelector('.baglanti-bilgi[data-baglanti=canli]');"
                             " const s = b && b.querySelector('svg[data-sema]'); return s && {sema: s.dataset.sema,"
                             " sekme: [...b.querySelectorAll('[data-bb-sekme]')].map(x => x.dataset.bbSekme),"
                             " parlak: [...s.querySelectorAll('g[data-kul=\"1\"]')].map(g => g.dataset.jak),"
                             " exp: document.querySelector('[data-bilgi=canli]').getAttribute('aria-expanded'),"
                             " metin: b.querySelector('.bb-metin').textContent}; })()", 6)
            ok("[!] BAGLANTI: dugmeyle acilir — Canli'da 4 sekme (gerilim/HV/akim/guc), varsayilan GERILIM: "
               "panelde V + COM parlak, talimat metni var",
               bool(ac) and ac["sema"] == "gerilim" and ac["sekme"] == ["gerilim", "hv", "akim", "guc"]
               and sorted(ac["parlak"]) == ["J1.1", "J1.2"] and ac["exp"] == "true" and "COM" in ac["metin"],
               json.dumps(ac, ensure_ascii=False)[:300])
            pop = t.js("(() => { const a = document.querySelector('.bb-arka'); const p = document.querySelector('.bb-pencere');"
                       " if (!a || !p) return null; const r = p.getBoundingClientRect(); return {"
                       " sabit: getComputedStyle(a).position, ebeveyn: a.parentElement === document.body,"
                       " rol: p.getAttribute('role'), modal: p.getAttribute('aria-modal'),"
                       " ortaX: Math.abs((r.left + r.right) / 2 - innerWidth / 2) < 2,"
                       " ortaY: Math.abs((r.top + r.bottom) / 2 - innerHeight / 2) < 2,"
                       " kaydirma: document.body.style.overflow,"
                       " odak: document.activeElement && document.activeElement.dataset.bb}; })()")
            baslik_h1 = t.js("document.querySelector('main.gorunum:not([style*=\"none\"]) .baslik').getBoundingClientRect().height")
            ok("[!] BAGLANTI: POPUP — ekranin ortasinda sabit kalici pencere (role=dialog, aria-modal), sayfa duzeni "
               "KAYMAZ (baslik ayni yukseklikte), arka sayfa kaymaz, odak pencerede (kullanici: 'ekstra yer olarak cikiyor')",
               bool(pop) and pop["sabit"] == "fixed" and pop["ebeveyn"] and pop["rol"] == "dialog"
               and pop["modal"] == "true" and pop["ortaX"] and pop["ortaY"] and pop["kaydirma"] == "hidden"
               and pop["odak"] == "kapat" and abs(baslik_h1 - baslik_h0) < 1,
               json.dumps({"pop": pop, "baslik": [baslik_h0, baslik_h1]}))
            boylar = {}
            for sek in ("gerilim", "hv", "akim", "guc"):
                t.js(f"document.querySelector('[data-bb-sekme={sek}]').click()")
                bekle_js(t, f"!!document.querySelector('.baglanti-bilgi svg[data-sema={sek}]')", 3)
                boylar[sek] = t.js(BOY)
            t.js("document.querySelector('[data-bb-sekme=akim]').click()")
            ak = bekle_js(t, "(() => { const s = document.querySelector('.baglanti-bilgi svg[data-sema=akim]');"
                             " return s && {parlak: [...s.querySelectorAll('g[data-kul=\"1\"]')].map(g => g.dataset.jak),"
                             " uyari: (document.querySelector('.baglanti-bilgi .bb-uyari') || {}).textContent || ''}; })()", 3)
            ok("BAGLANTI: Akim sekmesi — YUK 1 + YUK 2 parlak, COM DEGIL; 'COM'a takma' uyarisi gorunur",
               bool(ak) and sorted(ak["parlak"]) == ["J3.1", "J3.2"] and "COM" in ak["uyari"],
               json.dumps(ak, ensure_ascii=False)[:200])
            resim("2c-baglanti-akim")
            t.js("(() => { const a = document.querySelector('.bb-arka'); a.dispatchEvent(new MouseEvent('click', {bubbles: true})); })()")
            arka = bekle_js(t, "!document.querySelector('.baglanti-bilgi') && document.body.style.overflow === ''", 3)
            ok("BAGLANTI: arka plana tiklamak kapatir, sayfa kaydirmasi geri gelir", arka is True,
               str(t.js("document.body.style.overflow")))
            t.js("document.querySelector('[data-bilgi=canli]').click()")
            bekle_js(t, "!!document.querySelector('.baglanti-bilgi svg[data-sema]')", 3)
            t.js("window.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}))")
            kap = bekle_js(t, "!document.querySelector('.baglanti-bilgi') && document.activeElement"
                              " && document.activeElement.dataset.bilgi === 'canli'", 3)
            ok("BAGLANTI: Esc kapatir, odak dugmeye doner", kap is True,
               str(t.js("document.activeElement && document.activeElement.outerHTML.slice(0, 80)")))
            # kart HV menzilindeyse pencere HV sekmesiyle acilir
            t.js(f"{UYG}.menzil = 1; document.querySelector('[data-bilgi=canli]').click()")
            hv = bekle_js(t, "(() => { const s = document.querySelector('.baglanti-bilgi svg[data-sema]');"
                             " return s && s.dataset.sema; })()", 3)
            ok("[!] BAGLANTI: kart HV menzilindeyken (menzil 1) pencere HV sekmesiyle acilir (V'ye yuksek gerilim "
               "verilmesin)", hv == "hv", str(hv))
            t.js("document.querySelector('[data-bb=kapat]').click()")
            ekr = {}
            for ekran, sema, sekme in (("skop", "skop", 2), ("pil", "pil", 0)):
                t.js(f"{UYG}.gorunum = '{ekran}'")
                bekle_js(t, f"!!document.querySelector('[data-bilgi={ekran}]') && "
                            f"document.querySelector('[data-bilgi={ekran}]').offsetParent !== null", 4)
                t.js(f"document.querySelector('[data-bilgi={ekran}]').click()")
                ekr[ekran] = bekle_js(t, f"(() => {{ const b = document.querySelector('.baglanti-bilgi[data-baglanti={ekran}]');"
                                         " const s = b && b.querySelector('svg[data-sema]'); return s && {sema: s.dataset.sema,"
                                         " sekme: b.querySelectorAll('[data-bb-sekme]').length,"
                                         " parlak: [...s.querySelectorAll('g[data-kul=\"1\"]')].map(g => g.dataset.jak).sort()}; })()", 4)
                boylar[ekran] = t.js(BOY)
                if ekran == "pil":
                    resim("2c-baglanti-pil")
                t.js("document.querySelector('[data-bb=kapat]').click()")
            t.js(f"{UYG}.gorunum = 'canli'")
            ok("BAGLANTI: Osiloskop (SKOP + COM, 2 sekme: skop/CAL) ve Pil testi (PIL 1 + PIL 2 + V, sekmesiz) "
               "pencereleri de acilir",
               (ekr.get("skop") or {}).get("sema") == "skop" and ekr["skop"]["sekme"] == 2
               and ekr["skop"]["parlak"] == ["J1.2", "J4.1"]
               and (ekr.get("pil") or {}).get("sema") == "pil" and ekr["pil"]["sekme"] == 0
               and ekr["pil"]["parlak"] == ["J1.1", "J7.1", "J7.2"], json.dumps(ekr))
            ok("[!] BAGLANTI: pencere boyutu STANDART — 4 Canli sekmesi, Osiloskop ve Pil testi BIREBIR ayni "
               "(kullanici: 'kimi cok buyuk kimi kucuk')",
               len(boylar) == 6 and all(boylar.values()) and len({tuple(v) for v in boylar.values()}) == 1,
               json.dumps(boylar))

            # ── 3. kayit denetimi (D4) + aktif kayit (D6) ─────────────────
            n0 = len(kart.komutlar)
            t.js(deger_yaz(".kd-hiz select", "1000", "change"))
            t.bekle(0.2)
            t.js("document.querySelector('[data-kd=baslat]').click()")
            bekle_js(t, f"{UYG}.kayitAktif && document.querySelector('[data-ak=oturum]')", 6)
            k0 = komut_bekle(t, kart, n0, 2)
            ok("[!] D4: Baslat (1 s) -> `/komut`a 'Gb1000', ardindan 'G?'", k0[:2] == ["Gb1000", "G?"], " ".join(k0))
            t.bekle(2.5)
            ak = t.js("(() => { const m = (s) => ((document.querySelector(s) || {}).textContent || '').trim(); return {"
                      " o: m('[data-ak=oturum]'), h: m('[data-ak=hiz]'), k: m('[data-ak=kalan]'), d: m('[data-ak=doluluk]'),"
                      " bas: !!document.querySelector('.kayit-durum'),"
                      " olay: [...document.querySelectorAll('[data-olaylar] .olay')].map(o => o.textContent.trim())}; })()")
            ok("[!] D6: aktif kayit karti — oturum 121, aralik 1 s, doluluk, 'hesaplaniyor'; baslikta 'Kayit suruyor'",
               ak["o"] == "Oturum 121" and ak["h"] == "1 s" and "hesaplanıyor" in (ak["k"] or "")
               and ak["d"].startswith("Kart belleği %31.0 dolu") and ak["bas"], json.dumps(ak, ensure_ascii=False))
            ok("[!] D7: son olaylarda 'Kayit basladi · oturum 121'", any("Kayıt başladı · oturum 121" in o for o in ak["olay"]),
               str(ak["olay"][:3]))
            # not
            t.js("document.querySelector('[data-kd=not]').click()")
            bekle_js(t, "!!document.querySelector('[data-kd=not-metin]')", 4)
            t.js(deger_yaz("[data-kd=not-metin]", "x" * 121))
            t.bekle(0.2)
            n1 = len(kart.komutlar)
            t.js("document.querySelector('[data-kd=not-form] button[type=submit]').click()")
            t.bekle(0.6)
            uy = t.js("(document.querySelector('[data-kd=uyari]') || {}).textContent")
            ok("[!] D4: 121 baytlik not GONDERILMIYOR, sebebi yaziyor (kart fazlasini keserdi)",
               len(kart.komutlar) == n1 and "120 bayt" in (uy or ""), uy or "")
            t.js(deger_yaz("[data-kd=not-metin]", "Oda 24 °C"))
            t.bekle(0.2)
            t.js("document.querySelector('[data-kd=not-form] button[type=submit]').click()")
            komut_bekle(t, kart, n1, 2)
            notlar = [k for k in kart.komutlar[n1:] if k.startswith("Gn")]
            ms_ok = bool(notlar) and notlar[0].startswith("Gn121@") and notlar[0].endswith(" Oda 24 °C") \
                and int(notlar[0][len("Gn121@"):].split(" ")[0]) in {x[0] for x in kart.gonderilen}
            ok("[!] D4: Not -> 'Gn<oturum>@<kart_ms> <metin>' (oturum G satirindan, ms GONDERILMIS bir D'nin ms'i)",
               ms_ok and kart.komutlar[-1] == "G?", " ".join(kart.komutlar[n1:]))
            # WIG: Durdur iki asamali — ilk tik HICBIR komut gondermez, odak onay dugmesine;
            # Vazgec silahi indirir ve odagi Durdur'a geri verir
            nw = len(kart.komutlar)
            t.js("document.querySelector('[data-kd=durdur]').click()")
            silahli = bekle_js(t, "!!document.querySelector('[data-kd=durdur-eminim]') && document.activeElement"
                                  " && document.activeElement.dataset.onay === 'durdur'", 4)
            t.bekle(0.6)
            komut_yok = len(kart.komutlar) == nw
            t.js("document.querySelector('[data-kd=durdur-vazgec]').click()")
            geri = bekle_js(t, "!document.querySelector('[data-kd=durdur-eminim]') && document.activeElement"
                               " && document.activeElement.dataset.kd === 'durdur'", 4)
            t.bekle(0.3)
            ok("[!] WIG: Durdur IKI ASAMALI — ilk tik komut gondermez (odak 'Eminim, durdur'da), Vazgec geri alir (odak Durdur'a)",
               silahli is True and komut_yok and geri is True and len(kart.komutlar) == nw and t.js(f"{UYG}.kayitAktif") is True,
               f"silahli={silahli} komut_yok={komut_yok} geri={geri} komutlar={kart.komutlar[nw:]}")
            # ret (pil testi suruyor)
            kart.pil = True
            nr = len(kart.komutlar)
            durdur(t)
            ret = bekle_js(t, "(() => { const e = document.querySelector('[data-kd=uyari]');"
                              " return e && e.dataset.tur === 'kart' && e.textContent.trim(); })()", 5)
            olay = t.js("[...document.querySelectorAll('[data-olaylar] .olay')].map(o => o.textContent.trim())[0]")
            ok("[!] D4: kartin `! G:` reddi OLDUGU GIBI denetimin yaninda ve son olaylarda",
               ret == "Kart reddetti: ! G: pil testi suruyor — testi p0 ile durdur (kayit onunla kapanir)"
               and "! G: pil testi suruyor" in (olay or "") and t.js(f"{UYG}.kayitAktif") is True, f"{ret} · {olay}")
            komut_bekle(t, kart, nr, 2)
            kart.pil = False
            n2 = len(kart.komutlar)
            durdur(t)
            bekle_js(t, f"!{UYG}.kayitAktif && !!document.querySelector('[data-kd=baslat]')", 5)
            k2 = komut_bekle(t, kart, n2, 2)
            ok("[!] D4: Durdur -> 'Gd' + 'G?'; kart durunca baslat geri geliyor, ret kutusu temizlendi",
               k2[:2] == ["Gd", "G?"] and t.js("!document.querySelector('[data-kd=uyari]')") is True, " ".join(k2))
            # her ornek
            n3 = len(kart.komutlar)
            t.js(deger_yaz(".kd-hiz select", "0", "change"))
            t.bekle(0.2)
            t.js("document.querySelector('[data-kd=baslat]').click()")
            bekle_js(t, f"{UYG}.kayitAktif", 5)
            k3 = komut_bekle(t, kart, n3, 2)
            ok("[!] D4: 'her ornek' -> 'Gb0'", k3[:2] == ["Gb0", "G?"], " ".join(k3))
            n3b = len(kart.komutlar)
            durdur(t)
            bekle_js(t, f"!{UYG}.kayitAktif", 5)
            komut_bekle(t, kart, n3b, 2)
            # zamanla
            plan_bas = time.strftime("%Y-%m-%dT%H:%M", time.localtime(time.time() + 7200))
            beklenen_unix = int(time.mktime(time.strptime(plan_bas, "%Y-%m-%dT%H:%M")))
            t.js("document.querySelector('[data-kd=zamanla]').click()")
            bekle_js(t, "!!document.querySelector('[data-kd=plan-bas]')", 4)
            t.js(deger_yaz("[data-kd=plan-bas]", plan_bas))
            t.js(deger_yaz("[data-kd=plan-sa]", "1"))
            t.js(deger_yaz("[data-kd=plan-dk]", "30"))
            t.js(deger_yaz("[data-kd=plan-hiz]", "1000", "change"))
            t.bekle(0.2)
            n4 = len(kart.komutlar)
            t.js("document.querySelector('[data-kd=plan-form] button[type=submit]').click()")
            pl = bekle_js(t, "(() => { const e = document.querySelector('[data-ak=plan]'); return e && e.textContent.includes('bekliyor')"
                             " && e.textContent.trim(); })()", 5)
            k4 = komut_bekle(t, kart, n4, 2)
            ok("[!] D4: Zamanla -> 'Gp<unix>,5400,1000' (YEREL saatten unix; Python bagimsiz hesapladi) + G?; plan 'bekliyor'",
               k4[:2] == [f"Gp{beklenen_unix},5400,1000", "G?"] and bool(pl), f"{' '.join(k4)} · {pl}")
            n5 = len(kart.komutlar)
            t.js("document.querySelector('[data-kd=zamanla]').click()")
            bekle_js(t, "!!document.querySelector('[data-kd=plan-iptal]')", 4)
            t.js("document.querySelector('[data-kd=plan-iptal]').click()")
            k5 = komut_bekle(t, kart, n5, 2)
            ok("[!] D4: Plani iptal -> 'Gp-' + G?", k5[:2] == ["Gp-", "G?"], " ".join(k5))
            # dusen uyarisi + yeniden baslama
            kart.dusen = 3
            n6 = len(kart.komutlar)
            t.js(deger_yaz(".kd-hiz select", "200", "change"))
            t.bekle(0.2)
            t.js("document.querySelector('[data-kd=baslat]').click()")
            dus = bekle_js(t, "(document.querySelector('[data-ak=dusen]') || {}).textContent", 6)
            ok("[!] D6: kartin `dusen` > 0 -> uyari gorunur", "3 noktayı yazamadı" in (dus or ""), dus or "")
            kart.yeniden_baslat()
            ys = bekle_js(t, "[...document.querySelectorAll('[data-olaylar] .olay')].some(o => o.textContent.includes('Kart yeniden başladı'))"
                             " && document.querySelector('#serit .serit-alt-ad').textContent", 6)
            t.bekle(1.5)
            artan = t.js(f"(() => {{ const g = {UYG}.gecmis; for (let k = 1; k < g.length; k++) if (!(g[k].t > g[k - 1].t)) return false;"
                         " return true; })()")
            surdu = t.js("[...document.querySelectorAll('[data-olaylar] .olay')].some(o => o.textContent.includes('Kayıt sürdü · oturum'))")
            ok("[!] D7/D1: kart yeniden basladi (afis + ms sifirlandi): olay, kayit surdu, seritte afis surumu, zaman AZALMADI",
               "Asama 3" in (ys or "") and artan is True and surdu is True, f"{ys} artan={artan} surdu={surdu}")
            n7 = len(kart.komutlar)
            durdur(t)
            bekle_js(t, f"!{UYG}.kayitAktif", 5)
            komut_bekle(t, kart, n7, 2)
            t.bekle(3.0)                     # bos sure: yeni G? DOGMAMALI
            kart.dusen = 0
            gs = kart.komutlar.count("G?")
            kayit_k = sum(1 for k in kart.komutlar if k.startswith("G") and k != "G?")
            ok("[!] D5: butun oturum boyunca `G?` sayisi = 1 (baglanti) + kayit komutu sayisi (yoklama YOK)",
               gs == 1 + kayit_k, f"G? {gs}, kayit komutu {kayit_k}")
            resim("2-canli-kayit")

            # ── 4. dondur: imlec + yakinlastirma (D3) ─────────────────────
            t.js("document.querySelector('canvas.canli-grafik').scrollIntoView({block: 'center'})")
            t.js("document.querySelector('[data-kd=dondur]').click()")
            bekle_js(t, "(() => { const d = document.querySelector('.canli-tuval').dataset.pencere; return d && JSON.parse(d).donmus; })()", 4)
            p1 = json.loads(t.js("document.querySelector('.canli-tuval').dataset.pencere"))
            t.bekle(1.2)
            p2 = json.loads(t.js("document.querySelector('.canli-tuval').dataset.pencere"))
            ok("[!] D3: Dondur — yeni D satirlari gelirken pencere SABIT, tuval etkilesime acik",
               p1["t1"] == p2["t1"] and t.js("getComputedStyle(document.querySelector('canvas.canli-grafik')).pointerEvents") != "none",
               f"t1 {p1['t1']} -> {p2['t1']}")
            r = t.js("(() => { const c = document.querySelector('canvas.canli-grafik'); const b = c.getBoundingClientRect();"
                     " return {x: b.left + c.clientLeft, y: b.top, h: b.height}; })()")
            yv = r["y"] + r["h"] / 2
            beklenen = []
            for oran in (0.3, 0.7):
                ox = p2["alanX"] + oran * p2["alanW"]
                cift_tikla(t, r["x"] + ox, yv)
                t.bekle(0.3)
                beklenen.append(p2["t0"] + (ox - p2["alanX"]) / p2["alanW"] * (p2["t1"] - p2["t0"]))
            t.bekle(0.4)
            p3 = json.loads(t.js("document.querySelector('.canli-tuval').dataset.pencere"))
            okuma = t.js("[...document.querySelectorAll('.canli-okuma .okuma-oge')].map(o => o.textContent.trim())")
            px_t = (p2["t1"] - p2["t0"]) / p2["alanW"]
            ok("[!] D3: donmusken GERCEK fare cift tiki A ve B imlecini tiklanan piksele koydu; okuma (A/B, dt, enerji) gorunur",
               p3.get("imlecA") is not None and p3.get("imlecB") is not None
               and abs(p3["imlecA"] - beklenen[0]) <= 1.5 * px_t and abs(p3["imlecB"] - beklenen[1]) <= 1.5 * px_t
               and len(okuma or []) >= 6 and any(x.startswith("Enerji") for x in okuma), f"{p3} {okuma}")
            fare(t, "mouseMoved", r["x"] + p2["alanX"] + p2["alanW"] / 2, yv)
            t.cagir("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": r["x"] + p2["alanX"] + p2["alanW"] / 2, "y": yv,
                                                 "deltaX": 0, "deltaY": -400})
            t.bekle(0.5)
            p4 = json.loads(t.js("document.querySelector('.canli-tuval').dataset.pencere"))
            ok("[!] D3: donmusken tekerlek YAKINLASTIRIYOR (pencere daraldi)", (p4["t1"] - p4["t0"]) < 0.8 * (p3["t1"] - p3["t0"]),
               f"{p3['t1'] - p3['t0']:.0f} -> {p4['t1'] - p4['t0']:.0f} ms")
            resim("3-canli-donmus")
            t.js("document.querySelector('[data-kd=dondur]').click()")
            bekle_js(t, "(() => { const d = JSON.parse(document.querySelector('.canli-tuval').dataset.pencere); return !d.donmus; })()", 4)
            t.bekle(1.0)
            p5 = json.loads(t.js("document.querySelector('.canli-tuval').dataset.pencere"))
            ok("D3: Canliya don — pencere yeniden ilerliyor, etkilesim kapali",
               p5["t1"] > p2["t1"] and t.js("getComputedStyle(document.querySelector('canvas.canli-grafik')).pointerEvents") == "none")

            # ── 5. serit gezinmesi + eski adres (D1) ───────────────────────
            t.js("window.scrollTo(0, 0)")
            t.bekle(0.3)
            m = merkez(t, "#serit .gorunum-sekme[href='#/skop']")
            ust = t.js("(() => { const e = document.elementFromPoint(%s, %s); return e && (e.closest('a') || e).outerHTML.slice(0, 80); })()"
                       % (m["x"], m["y"]))
            tikla(t, m["x"], m["y"])
            bekle_js(t, f"location.hash === '#/skop' && {UYG}.gorunum === 'skop'"
                        " && (document.querySelector('#serit [aria-current=page]') || {}).textContent.trim() === 'Osiloskop'", 4)
            ok("[!] D1: seritte 'Osiloskop'a tiklamak #/skop'a gider, aria-current gecer",
               t.js(f"{UYG}.gorunum") == "skop"
               and (t.js("(document.querySelector('#serit [aria-current=page]') || {}).textContent") or "").strip() == "Osiloskop",
               f"hash {t.js('location.hash')} · tiklanan {ust}")
            for href, ad, ifade in (("#/konsol", "konsol", "[...document.querySelectorAll('.gunluk div')].some(d => /^G \\d/.test(d.textContent))"),
                                    ("#/ayar", "ayar", "[...document.querySelectorAll('h2')].some(h => h.textContent === 'Bağlantı' && h.offsetParent)"),
                                    ("#/pil", "pil", "!!document.querySelector('.kpi') && document.querySelector('.kpi').offsetParent !== null")):
                m = merkez(t, f"#serit .gorunum-sekme[href='{href}']")
                tikla(t, m["x"], m["y"])
                bekle_js(t, f"location.hash === '{href}' && {ifade}", 4)
            ok("Mevcut gorunumler yeni kabukta calisiyor: Konsol (G satirlari dahil), Ayarlar (3H: ilk bolum Baglanti), Pil testi",
               t.js("location.hash") == "#/pil" and t.js(f"{UYG}.gorunum") == "pil"
               and t.js("[...document.querySelectorAll('.gunluk div')].some(d => /^G \\d/.test(d.textContent))") is True)
            t.js("location.hash = '#/olcum'")
            bekle_js(t, f"{UYG}.gorunum === 'canli'", 4)
            ok("[!] D1: ESKI adres #/olcum Canli'yi aciyor (bos ekran degil)",
               t.js(f"{UYG}.gorunum") == "canli" and t.js("getComputedStyle(document.querySelector('canvas.canli-grafik')).display") != "none")

            # ── 6. uc gorunum ─────────────────────────────────────────────
            onceki = "koyu"
            for ad in TEMALAR:
                tema_sec(t, ad)
                d = takim[ad]
                hedef = [list(rgb(d["--volt"]))] + ([list(rgb(takim[onceki]["--volt"]))] if ad != onceki else [])
                px = t.js(PIKSEL_JS % json.dumps(hedef))
                zemin = t.js("getComputedStyle(document.querySelector('#serit')).backgroundColor")
                ok(f"[!] {ad}: Canli tuvali YENI --volt rengiyle" + (f", eski ({onceki}) yok" if ad != onceki else "")
                   + "; serit zemini --zemin-2",
                   bool(px) and px[0] > 50 and (ad == onceki or px[1] == 0)
                   and zemin == "rgb({}, {}, {})".format(*rgb(d["--zemin-2"])), f"{px} {zemin}")
                resim(f"4-canli-{ad}")
                onceki = ad

            # ── 7. telefon (390 px): cekmece + tasma ──────────────────────
            t.ekran(390, 844)
            t.bekle(0.8)
            gizli = t.js("({v: getComputedStyle(document.querySelector('#serit')).visibility,"
                         " ust: getComputedStyle(document.querySelector('.ust')).display,"
                         " d: document.querySelector('.menu-dugme').getAttribute('aria-expanded')})")
            m = merkez(t, ".menu-dugme")
            tikla(t, m["x"], m["y"])
            bekle_js(t, "getComputedStyle(document.querySelector('#serit')).visibility === 'visible'", 3)
            t.bekle(0.4)
            acik = t.js("({v: getComputedStyle(document.querySelector('#serit')).visibility,"
                        " d: document.querySelector('.menu-dugme').getAttribute('aria-expanded'),"
                        " odak: document.activeElement && document.activeElement.textContent.trim(),"
                        " sag: document.querySelector('#serit').getBoundingClientRect().right})")
            ok("[!] D1 (390 px): serit KAPALI (visibility hidden), ust cubuk gorunur; ☰ ACAR, odak etkin baglantiya (Canli)",
               gizli["v"] == "hidden" and gizli["ust"] == "flex" and gizli["d"] == "false"
               and acik["v"] == "visible" and acik["d"] == "true" and acik["odak"] == "Canlı" and 0 < acik["sag"] <= 390,
               json.dumps({"gizli": gizli, "acik": acik}, ensure_ascii=False))
            # WIG: cekmece acikken arka plan INERT — son serit baglantisindan Tab perdenin arkasina dusmez
            son = t.js("(() => { const a = [...document.querySelectorAll('#serit .gorunum-sekme')].pop(); a.focus();"
                       " return document.activeElement === a; })()")
            tus(t, "Tab", "Tab")
            t.bekle(0.2)
            inert = t.js("({ic: document.querySelector('.icerik').inert, ust: document.querySelector('.ust .baglanti').inert,"
                         " odakIcerikte: !!document.activeElement.closest('.icerik'),"
                         " kilit: getComputedStyle(document.documentElement).overflow})")
            ok("[!] WIG (390 px): cekmece acikken .icerik ve ust cubuk baglantisi INERT; Tab icerige DUSMEZ; govde kilitli",
               son is True and inert["ic"] is True and inert["ust"] is True and inert["odakIcerikte"] is False
               and inert["kilit"] == "hidden", json.dumps(inert))
            resim("5-telefon-cekmece")
            tus(t, "Escape", "Escape")
            bekle_js(t, "getComputedStyle(document.querySelector('#serit')).visibility === 'hidden'", 3)
            esc = t.js("({v: getComputedStyle(document.querySelector('#serit')).visibility,"
                       " odak: document.activeElement && document.activeElement.classList.contains('menu-dugme'),"
                       " d: document.querySelector('.menu-dugme').getAttribute('aria-expanded'),"
                       " ic: document.querySelector('.icerik').inert})")
            ok("[!] D1 (390 px): Esc cekmeceyi KAPATIR, odak ☰ dugmesine doner (WIG: icerik artik inert DEGIL)",
               esc["v"] == "hidden" and esc["odak"] is True and esc["d"] == "false" and esc["ic"] is False, json.dumps(esc))
            tikla(t, m["x"], m["y"])
            bekle_js(t, "getComputedStyle(document.querySelector('#serit')).visibility === 'visible'", 3)
            t.bekle(0.3)
            mp = merkez(t, "#serit .gorunum-sekme[href='#/pil']")
            tikla(t, mp["x"], mp["y"])
            bekle_js(t, "location.hash === '#/pil' && getComputedStyle(document.querySelector('#serit')).visibility === 'hidden'", 4)
            ok("[!] D1 (390 px): cekmecede secim gezinir VE cekmeceyi kapatir",
               t.js("location.hash") == "#/pil" and t.js("getComputedStyle(document.querySelector('#serit')).visibility") == "hidden"
               and t.js("!document.querySelector('.perde')") is True)
            t.js("location.hash = '#/canli'")
            t.bekle(0.6)
            tasmalar = {}
            for ad in TEMALAR:
                tema_sec(t, ad)
                tasmalar[ad] = tasma(t)
                resim(f"6-telefon-canli-{ad}")
            ok("[!] 390 px telefonda Canli uc gorunumde de YATAY TASMIYOR (clientWidth olcutu)",
               all(v <= 0 for v in tasmalar.values()), str(tasmalar))
            t.cagir("Emulation.clearDeviceMetricsOverride")

            # ── 8. konsol ─────────────────────────────────────────────────
            hatalar = []
            for o in t.olaylar:
                if o["tur"] == "hata" or o.get("seviye") == "error":
                    hatalar.append(o["metin"])
                elif o["tur"] == "log":
                    yol = urllib.parse.urlparse(o.get("url", "")).path
                    if yol not in BEKLENEN_404:
                        hatalar.append(o["metin"])
            ok("[!] Butun gezinti boyunca konsol/yukleme hatasi YOK", not hatalar, " | ".join(hatalar[:3]) or "temiz")
    except Kopuk as h:
        ok("[!] Sayfa beklenen akista kaldi (ust uste 3 bekleme zaman asimi yok)", False,
           f"son beklenen: {h} — kalan olcumler ATLANDI")
    finally:
        DUR.set()
        s.shutdown()
        s.server_close()

    for y in resimler:
        print(f"     goruntu: {y}")
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
