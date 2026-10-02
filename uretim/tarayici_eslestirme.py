# -*- coding: utf-8 -*-
"""3H-2 — ESLESTIRME TARAYICIDA (T3H2): sahte karta karsi uctan uca.

    python tarayici_eslestirme.py                 # sessiz, 0/1 doner
    python tarayici_eslestirme.py --goruntu DIZIN # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B7 (`test_arayuz3.js` bolum 31) istemciyi node'da imza.js ile sinar —
   yani imzayi KENDI kodumuzla. Burada sahte kart imzayi BAGIMSIZ basvuruyla (`kopru/imza.py`,
   kartin C koduyla vektorlerde bayt bayt ayni) dogrular ve kartin kurallarini uygular:
   64'luk kayan pencerede tekrar reddi, yeniden baslamada yeni `X-Acilis`, silinmis cihaza ayni
   acilisla 401, `p0` imzasiz serbest, Basic-Auth (eslesmemis yol: jeton + parola). Gercek
   tarayicida olculenler: IndexedDB'deki anahtar (kartin turettigiyle AYNI K), parolanin hicbir
   depoda olmamasi, tarayicinin ONBELLEKTEKI Basic-Auth'unun eslesince hicbir API istegine
   gitmemesi (credentials:'omit' — EventSource bunu yapamazdi), SSE'nin her yeniden baglanmada
   YENI imzali URL ve artan bekleme kullanmasi, iki sekme (ayni kokenli iframe) ayni anda
   komut yollarken sayac carpismasi olmamasi, "kart tanimiyor" uyarisi ve imzasiz yola dusus.

Sahte kart: `/eslestir/bilgi|baslat|kanit`, `/cihaz/liste|sil`, `/saat`, `/komut`, `/akis` (SSE),
`/kayit/liste|veri` (tarayici_kayitlar.Kart), `/kal/liste`, `/kunye.json`, `/pil`, `/skop.bin`.
⚠ WEB_PAROLA SAHTE kartin sinama parolasidir (gercek kartin parolasi DEGIL, o depoda yok).
⚠ `N?` hic gonderilmemeli (AP parolasini basar) — iddia.
"""
from __future__ import annotations

import base64
import hmac
import http.client
import http.server
import re
import json
import math
import secrets
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

import imza as I                                            # noqa: E402  (bagimsiz basvuru)
import tarayici_ayarlar as TA                               # noqa: E402
import tarayici_kayitlar as TK                              # noqa: E402
from tarayici import bos_port                               # noqa: E402
from tarayici_karsilastir import (KrTarayici, Kopuk, bekle_js, profil_surecleri,  # noqa: E402
                                  tasma, tema_sec, tikla_cdp)
from tarayici_tema import TEMALAR                           # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
IFR = "document.querySelector('#ikinci').contentDocument.querySelector('#uyg')._vnode.component.proxy"
AD = "olcum.test"
JETON = "abc123"
KULLANICI = "olcum"
WEB_PAROLA = "sinama-parolasi-12"          # SAHTE kartin parolasi (sinama)
YANLIS = "yanlis-parola-0000"
API = ("/komut", "/kayit/", "/kal/liste", "/pil", "/skop.bin", "/kunye.json", "/akis", "/cihaz/", "/saat", "/durum")
DUR = threading.Event()
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


# ── sahte kart ─────────────────────────────────────────────────────────────
class SahteKart:
    """Kartin 1D davranisi (olcum-karti-a3.ino guv_kapi + eslestir/cihaz/saat uclari)."""

    def __init__(self) -> None:
        akis, _no = TK.akis_kur()
        self.kayit = TK.Kart(list(akis.kayitlar))
        self.k = threading.RLock()
        self.kimlik = secrets.token_hex(8)
        self.acilis = secrets.token_hex(16)
        self.tuz = secrets.token_bytes(16)
        self.tur = 10000
        self.P = I.pbkdf2(WEB_PAROLA, self.tuz, self.tur)
        self.zorunlu = self.misafir = self.saat = 0
        self.saat_unix = None
        self.cihazlar: dict[int, dict] = {}
        self.pencere: dict[int, dict] = {}
        self.bekleyen = None
        self.yanlis_k = 0
        self.serbest = 0.0
        self.istekler: list[dict] = []
        self.komutlar: list[dict] = []
        self.akis_nesil = 0
        self.akis_red = 0
        self.tekrar_zorla = 0
        self.sil_kopar = False
        self.kunye = TA.uretec().kunye_hesapla()
        self.kal = {"surum": 1, "adet": 1, "taslak": 0, "etkin": 1, "azami": 40, "kayitlar": [TK.kal_json(1)]}

    def yeniden_basla(self) -> None:
        with self.k:
            self.acilis = secrets.token_hex(16)
            self.pencere.clear()
            self.bekleyen = None
            self.yanlis_k = 0
            self.serbest = 0.0
            self.akis_nesil += 1

    def imza(self, yontem: str, yol: str, args: list, govde: bytes, h, q) -> tuple[int | None, int | None, tuple | None]:
        """(n, sayac, None) gecerli | (n, sayac, (kod, metin)) ret. Kanonik: kopru/imza.py."""
        baslik = h.get("X-Imza") is not None
        cs = h.get("X-Cihaz") if baslik else q.get("_c")
        ss = h.get("X-Sayac") if baslik else q.get("_s")
        im = h.get("X-Imza") if baslik else q.get("_i")
        if yontem == "POST" and "x-www-form-urlencoded" in (h.get("Content-Type") or ""):
            return None, None, (400, "imzali istek form kodlamali olamaz (text/plain gonder)")
        try:
            n, sayac = int(cs or "0"), int(ss or "0")
        except ValueError:
            return None, None, (401, "imza gecersiz")
        with self.k:
            c = self.cihazlar.get(n)
            if not c:
                return n, sayac, (401, "imza: cihaz kayitli degil")
            arg = [(a, d) for a, d in args if a not in ("_c", "_s", "_i", "plain")]
            beklenen = I.imzala(c["K"], yontem, yol, arg, self.acilis, sayac, govde)
            if not hmac.compare_digest(beklenen, im or ""):
                return n, sayac, (401, "imza gecersiz (acilis degistiyse /eslestir/bilgi)")
            p = self.pencere.setdefault(n, {"en": 0, "gorulen": set()})
            if sayac in p["gorulen"] or sayac <= p["en"] - 64:
                return n, sayac, (401, "imza: sayac tekrar ya da cok eski")
            p["gorulen"].add(sayac)
            p["en"] = max(p["en"], sayac)
            p["gorulen"] = {x for x in p["gorulen"] if x > p["en"] - 64}
            if self.tekrar_zorla:                  # baska sekme bu sayaci az once kullandi (carpisma taklidi)
                self.tekrar_zorla -= 1
                return n, sayac, (401, "imza: sayac tekrar ya da cok eski")
            c["son"] = int(time.time())
        return n, sayac, None


def sunucu_kur(kart: SahteKart):
    MIME = TK.MIME
    beklenen_auth = "Basic " + base64.b64encode(f"{KULLANICI}:{WEB_PAROLA}".encode()).decode()

    class Isleyici(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _gonder(self, kod: int, govde: bytes = b"", tur: str = "text/plain; charset=utf-8", ek: dict | None = None):
            self.send_response(kod)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            for a, d in (ek or {}).items():
                self.send_header(a, d)
            self.end_headers()
            if govde:
                self.wfile.write(govde)
            self._k["kod"] = kod

        def _red(self, kod: int, metin: str) -> None:
            self._gonder(kod, metin.encode(), ek={"X-Acilis": kart.acilis} if kod == 401 else None)

        def _dosya(self, yol: str):
            if yol.startswith("/ortak/"):
                p = (ORTAK / yol[len("/ortak/"):]).resolve()
                if p.parent != ORTAK.resolve() or not p.is_file():
                    return self._gonder(404, b"yok")
            else:
                p = (ARAYUZ / (yol.lstrip("/") or "index.html")).resolve()
                if ARAYUZ.resolve() not in p.parents or not p.is_file():
                    return self._gonder(404, b"yok")
            self._gonder(200, p.read_bytes(), MIME.get(p.suffix, "application/octet-stream"))

        # 1D guv_kapi: imza VARSA dogrulama (basarisiz -> 401, imzasiz dala dusmez)
        def _kapi(self, sinif: str) -> bool:
            k = self._k
            imzali = self.headers.get("X-Imza") is not None or "_i" in k["q"]
            if imzali:
                n, sayac, ret = kart.imza(k["yontem"], k["yol"], k["args"], k["govde"], self.headers, k["q"])
                k.update(imza=True, n=n, sayac=sayac, gecerli=ret is None, acilis=kart.acilis)
                if ret:
                    self._red(*ret)
                    return False
                return True
            if sinif == "acik":
                return True
            if sinif == "cihaz":
                self._red(401, "imza gerekli")
                return False
            if not kart.zorunlu or sinif == "komut" or (sinif == "izleme" and kart.misafir):
                return True
            self._red(401, "imza gerekli (zorunluluk yalniz USB'den Ez0 ile kapanir)")
            return False

        def _hazirla(self, yontem: str) -> None:
            u = urllib.parse.urlparse(self.path)
            n = int(self.headers.get("Content-Length", "0") or 0)
            govde = self.rfile.read(n) if n else b""
            args = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
            self._k = {"t": time.monotonic(), "yontem": yontem, "yol": u.path, "url": self.path, "args": args,
                       "q": dict(args), "govde": govde, "auth": self.headers.get("Authorization"),
                       "jeton": self.headers.get("X-Jeton"), "imza": self.headers.get("X-Imza") is not None or "_i" in dict(args),
                       "n": None, "sayac": None,
                       "gecerli": None, "kod": None, "acilis": kart.acilis,
                       "kred": self.headers.get("Authorization") is not None}
            if u.path.startswith(API) or u.path.startswith("/eslestir/"):
                with kart.k:
                    kart.istekler.append(self._k)

        def do_GET(self):
            self._hazirla("GET")
            yol = self._k["yol"]
            if yol == "/eslestir/bilgi":
                b = {"surum": "OK1", "kimlik": kart.kimlik, "acilis": kart.acilis, "tuz": kart.tuz.hex(), "tur": kart.tur,
                     "zorunlu": kart.zorunlu, "misafir": kart.misafir, "saat": kart.saat, "cihaz_azami": 8}
                return self._gonder(200, json.dumps(b).encode(), "application/json")
            if yol == "/akis":
                return self._akis()
            if yol in ("/kayit/liste", "/kayit/veri", "/kal/liste", "/skop.bin"):
                if not self._kapi("okuma"):
                    return
                if yol == "/kal/liste":
                    return self._gonder(200, json.dumps(kart.kal).encode(), "application/json")
                if yol == "/skop.bin":
                    return self._gonder(503, b"yakalama yok (sinama)")
                with kart.kayit.kilit:
                    if yol == "/kayit/liste":
                        return self._gonder(200, json.dumps(kart.kayit.dizin()).encode(), "application/json")
                    q = self._k["q"]
                    g, ilk, son = kart.kayit.veri(int(q.get("sira", "1")), int(q.get("bayt", "8192")))
                    bas = {"X-Kayit-Kimlik": str(kart.kayit.kimlik), "X-Ilk-Sira": str(ilk), "X-Son-Sira": str(son),
                           "X-Sonraki-Sira": str(kart.kayit.sonraki()), "X-Onay": str(kart.kayit.onay)}
                return self._gonder(200, g, "application/octet-stream", bas)
            if yol == "/kunye.json":
                # kartta LittleFS serveStatic: guv_kapi YOK (imza basliklari yok sayilir). Burada imza tasiyorsa
                # yalniz KAYIT icin dogrulanir (iddia: eslesmisken bu istek de gecerli imzali), reddedilmez.
                if self._k["imza"]:
                    _n, _s, ret = kart.imza("GET", yol, self._k["args"], b"", self.headers, self._k["q"])
                    self._k.update(n=_n, sayac=_s, gecerli=ret is None)
                return self._gonder(200, json.dumps(kart.kunye).encode(), "application/json")
            if yol == "/pil":
                if not self._kapi("izleme"):
                    return
                g = ("durum=BEKLEMEDE\nhata=-\nmah=0.0000\nwh=0.000000\nocv=0.0000\nvson=0.0000\nkesme=3.000\n"
                     "dcir_ani=0.00000\ndcir_otr=0.00000\ndcir_n=0\nsira=0\nilk_sira=0\nkalan=0\ncoulomb=0.000\n--\n")
                return self._gonder(200, g.encode())
            if yol == "/cihaz/liste":
                if not self._kapi("cihaz"):
                    return
                with kart.k:
                    l = [{"n": n, "ad": c["ad"], "eklenme": c["eklenme"], "son": c["son"]} for n, c in sorted(kart.cihazlar.items())]
                return self._gonder(200, json.dumps({"cihazlar": l}).encode(), "application/json")
            if yol in ("/durum", "/favicon.ico"):
                return self._gonder(404, b"yok")
            return self._dosya(yol)

        def _akis(self):
            if not self._kapi("izleme"):
                return
            with kart.k:
                if kart.akis_red > 0:
                    kart.akis_red -= 1
                    return self._gonder(503, b"akis dolu (sinama)")
                nesil = kart.akis_nesil
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self._k["kod"] = 200
            self.close_connection = True
            try:
                self.wfile.write(f'retry: 3000\n\nevent: kimlik\ndata: {{"jeton":"{JETON}","surucu":true}}\n\n'.encode())
                self.wfile.flush()
                while not DUR.is_set() and kart.akis_nesil == nesil:
                    DUR.wait(0.25)
                    self.wfile.write(b": nabiz\n\n")
                    self.wfile.flush()
            except OSError:
                pass

        def do_POST(self):
            self._hazirla("POST")
            k = self._k
            yol, q = k["yol"], k["q"]
            if yol.startswith("/eslestir/") and self.headers.get("X-Olcum") != "1":
                return self._gonder(400, b"X-Olcum basligi gerekli")
            if yol == "/eslestir/baslat":
                with kart.k:
                    if time.monotonic() < kart.serbest:
                        kalan = max(1, math.ceil(kart.serbest - time.monotonic()))
                        return self._gonder(429, "cok fazla yanlis deneme — Retry-After kadar bekle".encode(),
                                            ek={"Retry-After": str(kalan)})
                    nk = secrets.token_bytes(16)
                    kart.bekleyen = {"eno": secrets.randbelow(250) + 1, "ad": q.get("ad", ""), "nc": bytes.fromhex(q.get("nc", "")),
                                     "nk": nk, "t": time.monotonic()}
                    return self._gonder(200, json.dumps({"eno": kart.bekleyen["eno"], "nk": nk.hex()}).encode(), "application/json")
            if yol == "/eslestir/kanit":
                with kart.k:
                    b = kart.bekleyen
                    if not b or str(b["eno"]) != q.get("eno") or time.monotonic() - b["t"] > 60:
                        return self._gonder(410, "bekleyen eslestirme yok ya da 60 s gecti — bastan basla".encode())
                    kart.bekleyen = None
                    if I.kanit_istemci(kart.P, kart.kimlik, b["nk"], b["nc"], b["ad"]).hex() != q.get("kanit"):
                        kart.yanlis_k += 1
                        kart.serbest = time.monotonic() + 2 ** kart.yanlis_k
                        return self._gonder(403, b"kanit yanlis (parola?)")
                    bos = [n for n in range(1, 9) if n not in kart.cihazlar]
                    if not bos:
                        return self._gonder(409, b"cihaz listesi dolu (8)")
                    n = bos[0]
                    kart.cihazlar[n] = {"K": I.cihaz_anahtari(kart.P, kart.kimlik, b["nk"], b["nc"], n), "ad": b["ad"],
                                        "eklenme": int(time.time()), "son": 0}
                    kart.pencere.pop(n, None)
                    kart.yanlis_k = 0
                    kk = I.kanit_kart(kart.P, kart.kimlik, b["nk"], b["nc"], n).hex()
                    return self._gonder(200, json.dumps({"n": n, "kart_kanit": kk}).encode(), "application/json")
            if yol == "/cihaz/sil":
                if kart.sil_kopar:                 # karta ulasilamiyor: yanit YOK, baglanti kapanir
                    self.close_connection = True
                    return
                if not self._kapi("cihaz"):
                    return
                with kart.k:
                    n = int(q.get("n", "0") or 0)
                    if n not in kart.cihazlar:
                        return self._gonder(404, b"silinemedi")
                    del kart.cihazlar[n]
                return self._gonder(204)
            if yol == "/saat":
                if not self._kapi("cihaz"):
                    return
                if self.headers.get("X-Olcum") != "1":
                    return self._gonder(400, b"X-Olcum basligi gerekli")
                if kart.saat == 1:
                    return self._gonder(409, "kartin NTP saati var — cihaz saati kullanilmaz".encode())
                u = int(q.get("unix", "0") or 0)
                if u < 1700000000:
                    return self._gonder(400, b"unix >= 1700000000 olmali")
                kart.saat, kart.saat_unix = 2, u
                return self._gonder(204)
            if yol == "/komut":
                if not self._kapi("komut"):
                    return
                if self.headers.get("X-Olcum") != "1":
                    return self._gonder(400, b"X-Olcum basligi gerekli")
                m = k["govde"].decode("utf-8", "replace").strip()
                if not k["imza"] and m not in ("p0", "?"):
                    if self.headers.get("X-Jeton") != JETON:
                        return self._gonder(403, b"gecersiz oturum jetonu")
                    if self.headers.get("Authorization") != beklenen_auth:
                        return self._gonder(401, b"yetki gerekli", ek={"WWW-Authenticate": 'Basic realm="olcum"'})
                with kart.k:
                    kart.komutlar.append({"m": m, "imza": k["imza"], "t": time.monotonic()})
                return self._gonder(204)
            return self._gonder(404, b"yok")

    class Sunucu(http.server.ThreadingHTTPServer):
        daemon_threads = True
        block_on_close = False
        allow_reuse_address = False

        def handle_error(self, *a):
            pass

    s = Sunucu(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


class AuthTarayici(KrTarayici):
    """Kartin Basic-Auth sorusuna SAHTE kartin parolasiyla cevap verir (tarayici onbellege alir):
    eslesmeden ONCEKI bugunku yol ve eslestikten sonra onbellegin istege gitmedigi boyle olculur."""

    def _olay(self, m: dict) -> None:
        if m.get("method") == "Fetch.authRequired":
            self.auth_sayisi = getattr(self, "auth_sayisi", 0) + 1
            self.ws.gonder(json.dumps({"id": 0, "method": "Fetch.continueWithAuth", "params": {
                "requestId": m["params"]["requestId"],
                "authChallengeResponse": {"response": "ProvideCredentials", "username": KULLANICI, "password": WEB_PAROLA}}}))
            return
        super()._olay(m)


IDB_KAYIT_JS = """(async () => {
  if (!(await indexedDB.databases()).some(d => d.name === 'olcum-cihaz')) return null;
  const vt = await new Promise((c, r) => { const q = indexedDB.open('olcum-cihaz'); q.onsuccess = () => c(q.result); q.onerror = () => r(q.error); });
  if (!vt.objectStoreNames.contains('cihaz')) { vt.close(); return []; }
  const l = await new Promise(c => { const q = vt.transaction('cihaz').objectStore('cihaz').getAll(); q.onsuccess = () => c(q.result); });
  vt.close();
  return l.map(x => ({ ...x, K: x.K instanceof Uint8Array ? Array.from(x.K, b => b.toString(16).padStart(2, '0')).join('') : String(x.K) }));
})()"""

YABANCI_YAZ_JS = """(async () => {
  const vt = await new Promise((c, r) => { const q = indexedDB.open('olcum-cihaz'); q.onsuccess = () => c(q.result); q.onerror = () => r(q.error); });
  await new Promise((c, r) => { const t = vt.transaction('cihaz', 'readwrite');
    t.objectStore('cihaz').put({ kimlik: 'fedcba9876543210', n: 1, K: new Uint8Array(32).fill(7), ad: 'eski kart', sayac: 0,
      acilis: 'c'.repeat(32), eklenme: 1 });
    t.oncomplete = c; t.onerror = () => r(t.error); });
  vt.close();
  return true;
})()"""

PAROLA_TARA_JS = """(async (p) => {
  const bul = []; const enc = new TextEncoder().encode(p);
  const icerir = (u) => { dis: for (let i = 0; i + enc.length <= u.length; i++) { for (let j = 0; j < enc.length; j++) if (u[i + j] !== enc[j]) continue dis; return true; } return false; };
  const tara = (v, yol, d = 0) => { if (v == null || d > 8) return;
    if (typeof v === 'string') { if (v.includes(p)) bul.push(yol); return; }
    if (v instanceof ArrayBuffer) v = new Uint8Array(v);
    if (ArrayBuffer.isView(v)) { if (icerir(new Uint8Array(v.buffer, v.byteOffset, v.byteLength))) bul.push(yol); return; }
    if (typeof v === 'object') for (const [k, x] of Object.entries(v)) { if (String(k).includes(p)) bul.push(yol + '#'); tara(x, yol + '.' + k, d + 1); } };
  for (const [ad, s] of [['local', localStorage], ['session', sessionStorage]])
    for (let i = 0; i < s.length; i++) { const k = s.key(i); tara(k + '=' + s.getItem(k), ad + ':' + k); }
  const dbs = await indexedDB.databases(); let depo = 0, kayit = 0;
  for (const d of dbs) {
    const vt = await new Promise((c, r) => { const q = indexedDB.open(d.name); q.onsuccess = () => c(q.result); q.onerror = () => r(q.error); });
    for (const ad of vt.objectStoreNames) { depo++;
      const l = await new Promise(c => { const q = vt.transaction(ad).objectStore(ad).getAll(); q.onsuccess = () => c(q.result); });
      kayit += l.length; l.forEach((v, i) => tara(v, d.name + '/' + ad + '/' + i)); }
    vt.close(); }
  const alan = document.querySelector('#es-parola');
  return { bul, dbs: dbs.map(d => d.name).sort(), depo, kayit, alan: alan ? alan.value : null,
           dom: document.documentElement.outerHTML.includes(p) };
})(%s)"""


def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    kart = SahteKart()
    s = sunucu_kur(kart)
    port = s.server_address[1]
    taban = f"http://{AD}:{port}"
    profil = None
    print("=" * 78)
    print("  3H-2  ESLESTIRME — TARAYICIDA, SAHTE KARTA KARSI (T3H2)")
    print("=" * 78)
    print(f"     sahte kart: {taban}  (kimlik {kart.kimlik}, PBKDF2 {kart.tur} tur, imza dogrulamasi kopru/imza.py)\n")

    def istekler(f=lambda r: True) -> list[dict]:
        with kart.k:
            return [r for r in kart.istekler if f(r)]

    def api_mi(r) -> bool:
        return r["yol"].startswith(API)

    def sira() -> int:
        with kart.k:
            return len(kart.istekler)

    def komut_bekle(m: str, bas: int, sure: float = 8.0, imza: bool | None = None) -> dict | None:
        son = time.monotonic() + sure
        while time.monotonic() < son:
            with kart.k:
                for r in kart.istekler[bas:]:
                    if r["yol"] == "/komut" and r["govde"] == m.encode() and r["kod"] in (204, 200) and (imza is None or r["imza"] == imza):
                        return r
            t.bekle(0.15)
        return None

    def esles_formu(parola: str) -> None:
        t.js("(() => { const p = document.querySelector('#es-parola'); p.value = %s; })()" % json.dumps(parola))
        tikla_cdp(t, "[data-es-eslestir]")

    def ret_bekle(onceki: str = "") -> str:
        return bekle_js(t, "(() => { const r = document.querySelector('[data-es-ret]'); return r && r.textContent.trim() !== %s"
                           " && document.querySelector('[data-es-eslestir]').getAttribute('aria-busy') === 'false' && r.textContent.trim(); })()"
                        % json.dumps(onceki), 10) or ""

    def resim(ad: str) -> None:
        if goruntu:
            t.goruntu(str(goruntu / f"{ad}.png"))

    def durum() -> str:
        return t.js("(document.querySelector('[data-es-durum]') || {}).textContent || ''") or ""

    try:
        with AuthTarayici(port=bos_port(), ek_arg=[f"--host-resolver-rules=MAP {AD} 127.0.0.1"]) as t:
            profil = t.profil
            t.cagir("Log.enable")

            # ── 1. ESLESMEMIS: bugunku yol AYNEN, modul INMEZ, cihaz veritabani YARATILMAZ ──────────
            t.git(taban + "/#/canli")
            bekle_js(t, f"{UYG}.bagli === true", 12)
            bas = 0
            komut_bekle("CT", bas, 10)
            komut_bekle("G?", bas, 6)
            t.bekle(0.5)
            once = istekler()
            akis0 = [r for r in once if r["yol"] == "/akis"]
            kom0 = [r for r in once if r["yol"] == "/komut"]
            ct = next((r for r in kom0 if r["govde"] == b"CT" and r["kod"] == 204), None)
            yuklenen = t.js("performance.getEntriesByType('resource').map(e => new URL(e.name).pathname)"
                            ".filter(p => /eslesme|imza|kripto/.test(p))")
            dbs = t.js("indexedDB.databases().then(l => l.map(d => d.name))")
            ok("[!] ES4: eslesmemisken BUGUNKU yol aynen — /akis imzasiz (EventSource), komutlar X-Jeton + tarayicinin Basic-Auth'u"
               " (kart sordu, tarayici cevapladi); /eslestir/* hic sorulmadi; eslesme.js / imza.js / kripto.js INMEDI;"
               " 'olcum-cihaz' veritabani YARATILMADI",
               bool(akis0) and all("_i" not in r["q"] for r in akis0) and ct is not None and ct["jeton"] == JETON and ct["kred"]
               and not any(r["imza"] for r in once) and not any(r["yol"].startswith("/eslestir/") for r in once)
               and yuklenen == [] and "olcum-cihaz" not in (dbs or []) and getattr(t, "auth_sayisi", 0) >= 1,
               f"akis {len(akis0)} · komut {[r['govde'].decode() for r in kom0]} · auth {getattr(t, 'auth_sayisi', 0)} · {yuklenen} · {dbs}")

            # ── 2. Eslestirme bolumu: modul iner, kartin bilgisi; eslesmemis ───────────────────
            t.js("location.hash = '#/ayar/eslestirme'")
            d0 = bekle_js(t, "(() => { const d = document.querySelector('[data-es-durum]'); return d && d.offsetParent && /eşleşmemiş/.test(d.textContent)"
                             " && document.querySelector('[data-es-bilgi]') && document.querySelector('[data-es-bilgi]').textContent; })()", 12) or ""
            ok("[!] ES1/ES9: Eslestirme bolumu — 'eslesmemis' durumu, kartin kimligi, imza zorunlulugu / misafir izleme (kapali) ve saat kaynagi"
               " kartin /eslestir/bilgi'sinden; zorunluluk/misafir icin girdi YOK (yalniz USB)",
               kart.kimlik in d0 and "kapalı" in d0 and "yok (NTP de" in d0
               and t.js("document.querySelectorAll('[data-ay-bolum=eslestirme] input').length") == 2
               and "Ez1" in (t.js("document.querySelector('[data-es-guv]').textContent") or "")
               and "USB" in (t.js("document.querySelector('[data-es-bildirim]').textContent") or ""), d0[:160])

            resim("1-eslesmemis")

            # ── 3. ES3: kisa parola aga cikmaz; yanlis parola; deneme siniri (429 + Retry-After) ─────
            b3 = sira()
            esles_formu("kisa-parola")
            r1 = ret_bekle()
            ag1 = [r for r in istekler()[b3:] if r["yol"].startswith("/eslestir/")]
            esles_formu(YANLIS)
            r2 = ret_bekle(r1)
            esles_formu(WEB_PAROLA)
            r3 = ret_bekle(r2)
            ok("[!] ES3: kisa parola AGA CIKMADAN reddedildi (kartin 12 alt siniri); yanlis parolada KARTIN sebebi; hemen yeniden denemede"
               " deneme siniri 429 + bekleme saniyesi; her gonderide parola alani BOSALTILDI",
               "en az 12" in r1 and not ag1 and "parola yanlış" in r2 and "kanit yanlis" in r2
               and re.search(r"\d+ s bekleyip yeniden deneyin", r3) is not None
               and t.js("document.querySelector('#es-parola').value") == "", f"{r1[:50]} | {r2[:60]} | {r3[:60]}")
            t.bekle(max(0.0, kart.serbest - time.monotonic()) + 0.3)

            # ── 4. dogru parola: eslesti; K kartinkiyle AYNI; parola hicbir yerde yok ──────────────
            b4 = sira()
            esles_formu(WEB_PAROLA)
            d4 = bekle_js(t, "(() => { const d = document.querySelector('[data-es-durum]'); return d && /Eşleşmiş: cihaz 1/.test(d.textContent)"
                             " && document.querySelectorAll('[data-es-cihaz]').length === 1 && d.textContent; })()", 15) or ""
            kayit = t.js(IDB_KAYIT_JS) or []
            with kart.k:
                kartK = kart.cihazlar.get(1, {}).get("K", b"").hex()
            ok("[!] ES2/ES3: dogru parolayla eslesti (cihaz 1); IndexedDB 'olcum-cihaz' deposunda kimlige gore kayit — K kartin"
               " (kopru/imza.py) turettigi anahtarla BAYT BAYT ayni; acilis kartinki",
               bool(d4) and len(kayit) == 1 and kayit[0]["kimlik"] == kart.kimlik and kayit[0]["n"] == 1
               and kayit[0]["K"] == kartK and len(kartK) == 64 and kayit[0]["acilis"] == kart.acilis,
               f"{d4[:60]} · {len(kayit)} kayit")
            odak4 = bekle_js(t, "!!document.activeElement && document.activeElement.hasAttribute('data-es-durum')", 3)
            resim("2-eslesmis")
            es_ist = [r for r in istekler()[b3:] if r["yol"].startswith("/eslestir/")]
            tum = json.dumps([[r["url"], r["govde"].decode("utf-8", "replace")] for r in istekler()], ensure_ascii=False)
            ok("[!] ES3: parola HICBIR istekte yok (URL, govde); eslestirme istekleri tarayicinin onbellekteki Basic-Auth'unu TASIMADI",
               WEB_PAROLA not in tum and YANLIS not in tum and bool(es_ist) and not any(r["kred"] for r in es_ist),
               f"{len(es_ist)} eslestirme istegi")
            tara = t.js(PAROLA_TARA_JS % json.dumps(WEB_PAROLA)) or {}
            ok("[!] ES3: eslesince parola localStorage / sessionStorage / BUTUN IndexedDB depolarinda ve sayfada (DOM) YOK; form kalkti",
               tara.get("bul") == [] and "olcum-cihaz" in tara.get("dbs", []) and tara.get("depo", 0) >= 1 and tara.get("alan") in (None, "")
               and tara.get("dom") is False, json.dumps(tara, ensure_ascii=False)[:200])

            # ── 5. eslesmis: akis imzali yeniden acildi; HER API istegi imzali, Basic-Auth YOK ─────
            son = time.monotonic() + 10
            akis_imzali = None
            while time.monotonic() < son and not akis_imzali:
                akis_imzali = next((r for r in istekler()[b4:] if r["yol"] == "/akis" and r["imza"] and r["gecerli"]), None)
                t.bekle(0.2)
            ilk_imzali_t = min((r["t"] for r in istekler()[b4:] if r["imza"]), default=time.monotonic())
            b5 = sira()
            t.js(f"{UYG}.gonder('G?')")
            g5 = komut_bekle("G?", b5, 6, imza=True)
            t.js(f"{UYG}.pilYokla()")
            t.js(f"{UYG}.skopIkiliAl()")
            t.js("location.hash = '#/kayitlar'")
            bekle_js(t, "document.querySelectorAll('.kl-satir').length >= 3 && [...document.querySelectorAll('.kl-satir')]"
                        ".every(a => a.dataset.nerede === 'ikisi')", 60)
            t.js("location.hash = '#/ayar/kal-gecmis'")
            bekle_js(t, "document.querySelectorAll('[data-ay-kal]').length >= 1", 10)
            t.js("location.hash = '#/ayar/gelismis'")
            bekle_js(t, "/·/.test((document.querySelector('[data-ay-panel]') || {}).textContent || '')", 10)
            t.bekle(0.5)
            # P0-S/EU28: p0 ve /durum (kopru yoklamasi) KASITLI imzasiz — ama Authorization denetiminden ISTISNA DEGILLER
            sonra = [r for r in istekler()[b4:] if api_mi(r)]
            yollar = sorted({r["yol"] for r in sonra})
            imzasiz = [r["url"] for r in sonra if not r["imza"] and r["yol"] != "/durum" and not (r["yol"] == "/komut" and r["govde"] == b"p0")]
            gecersiz = [r["url"] for r in sonra if r["imza"] and not r["gecerli"] and r["kod"] != 401]
            kredili = [r["url"] for r in sonra if r["kred"]]
            ok("[!] ES4/ES6: eslesince akis IMZALI URL ile yeniden acildi (kart imza.py ile dogruladi) ve komut imzali gitti",
               bool(akis_imzali) and g5 is not None and g5["jeton"] is None, f"akis {bool(akis_imzali)} · G? {g5 is not None}")
            ok("[!] ES4: eslesmisken /komut /kayit/* /kal/liste /pil /skop.bin /kunye.json /akis /cihaz/* — HEPSI imzali ve gecerli;"
               " hicbirinde (p0 ve /durum dahil) Authorization (tarayicinin onbellekteki Basic-Auth'u) YOK",
               all(y in yollar for y in ("/akis", "/komut", "/kayit/liste", "/kayit/veri", "/kal/liste", "/pil", "/skop.bin", "/kunye.json", "/cihaz/liste"))
               and not imzasiz and not gecersiz and not kredili, f"{yollar} · imzasiz {imzasiz[:3]} · kredili {kredili[:3]}")

            # ── 6. EMNIYET-P0: eslesmisken de p0 imzasiz, tek istek ───────────────────────────
            b6 = sira()
            t6 = time.monotonic()
            t.js(f"{UYG}.pilDurdurKomut()")
            p0 = komut_bekle("p0", b6, 5)
            p0lar = [r for r in istekler()[b6:] if r["yol"] == "/komut"]
            ok("[!] EMNIYET-P0: eslesmisken p0 IMZASIZ, TEK istekle ve <= 5 s icinde gitti (kart K11 geregi kabul etti);"
               " tarayicinin onbellekteki Basic-Auth'unu TASIMADI (P0-S credentials 'omit')",
               p0 is not None and not p0["imza"] and not p0["kred"] and len(p0lar) == 1,
               f"{[(r['govde'], r['imza'], r['kred'], r['kod']) for r in p0lar]} · {round((p0['t'] - t6) if p0 else -1, 3)} s")

            # ── 7. kart kurallari (bagimsiz): tekrar reddi, bozuk govde reddi; panel sayaci tekrar etmedi ─
            ornek = next(r for r in istekler()[b5:] if r["yol"] == "/komut" and r["imza"] and r["gecerli"])
            import http.client
            def yeniden_yolla(govde: bytes) -> int:
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                c.request("POST", ornek["url"], body=govde, headers={
                    "Host": f"{AD}:{port}", "X-Olcum": "1", "Content-Type": "text/plain",
                    "X-Cihaz": str(ornek["n"]), "X-Sayac": str(ornek["sayac"]), "X-Imza": ornek_imza})
                y = c.getresponse()
                y.read()
                c.close()
                return y.status
            with kart.k:
                ornek_imza = I.imzala(kart.cihazlar[1]["K"], "POST", "/komut", [], ornek["acilis"], ornek["sayac"], ornek["govde"])
            tekrar = yeniden_yolla(ornek["govde"])
            bozuk = yeniden_yolla(b"G!")
            kabul = [(r["n"], r["acilis"], r["sayac"]) for r in istekler() if r["imza"] and r["gecerli"]]
            ok("[!] ES10: sahte kart tekrar oynatilan imzali istegi (ayni sayac) ve govdesi degistirilmisi REDDEDIYOR (401);"
               " panelin kabul edilen sayaclari hic tekrar etmedi",
               tekrar == 401 and bozuk == 401 and len(kabul) == len(set(kabul)) and len(kabul) >= 8, f"{tekrar} {bozuk} · {len(kabul)} kabul")

            # ── 8. ES5: carpisma (baska sekme ayni sayaci kullandi) -> yeni sayacla tek yeniden deneme ─
            b8 = sira()
            with kart.k:
                kart.tekrar_zorla = 1
            t.js(f"{UYG}.gonder('G?')")
            g8 = komut_bekle("G?", b8, 6, imza=True)
            k8 = [r for r in istekler()[b8:] if r["yol"] == "/komut"]
            ok("[!] ES5: ayni acilisla tek 401 (sayac carpismasi) -> panel YENI sayacla bir kez yeniden denedi, kabul edildi; uyari YOK",
               g8 is not None and len(k8) == 2 and k8[0]["kod"] == 401 and k8[1]["sayac"] > k8[0]["sayac"]
               and not t.js("!!document.querySelector('[data-es-uyari]')"), str([(r['kod'], r['sayac']) for r in k8]))

            # ── 9. iki sekme (ayni kokenli iframe) ayni anda komut: carpisma YOK (sayac depoda atomik) ─
            t.js("(() => { const f = document.createElement('iframe'); f.id = 'ikinci'; f.style.cssText = 'width:900px;height:600px';"
                 " f.src = location.origin + '/#/ayar/baglanti'; document.body.appendChild(f); })()")
            bekle_js(t, f"(() => {{ try {{ return {IFR}.bagli === true; }} catch (e) {{ return false; }} }})()", 15)
            son = time.monotonic() + 12              # ikinci sekmenin acilis komutlari (?, CT, G?) bitsin
            while time.monotonic() < son:
                t.bekle(1.2)
                with kart.k:
                    sonk = max((r["t"] for r in kart.istekler if r["yol"] == "/komut"), default=0)
                if time.monotonic() - sonk > 1.0:
                    break
            b9 = sira()
            t.js(f"Promise.all(Array.from({{length: 8}}, () => [{UYG}.gonder('G?'), {IFR}.gonder('G?')]).flat())")
            son = time.monotonic() + 10
            while time.monotonic() < son and len([r for r in istekler()[b9:] if r["yol"] == "/komut" and r["kod"] == 204]) < 16:
                t.bekle(0.2)
            k9 = [r for r in istekler()[b9:] if r["yol"] == "/komut" and r["govde"] == b"G?"]
            kabul9 = [r["sayac"] for r in k9 if r["kod"] == 204]
            kayit9 = t.js(IDB_KAYIT_JS) or [{}]
            ok("[!] ES5: iki sekme ayni anda 16 imzali komut — 16'si de ILK denemede kabul (401 YOK), sayaclar ayri; depodaki sayac en buyugu",
               len(kabul9) == 16 and all(r["imza"] for r in k9) and not [r for r in k9 if r["kod"] == 401]
               and len(set(kabul9)) == 16 and kayit9[0].get("sayac", 0) >= max(kabul9 or [0]),
               f"{len(k9)} istek · 401 {len([r for r in k9 if r['kod'] == 401])} · {kayit9[0].get('sayac')} >= {max(kabul9 or [0])}")
            t.js("document.querySelector('#ikinci').remove()")

            # ── 10. ES6: akis koptugunda YENI imzali URL + artan bekleme ───────────────────────
            b10 = sira()
            with kart.k:
                kart.akis_red = 2
                kart.akis_nesil += 1                # canli akislari kapat
            son = time.monotonic() + 16
            while time.monotonic() < son and not [r for r in istekler()[b10:] if r["yol"] == "/akis" and r["kod"] == 200]:
                t.bekle(0.2)
            a10 = [r for r in istekler()[b10:] if r["yol"] == "/akis"]
            ar = [a10[i + 1]["t"] - a10[i]["t"] for i in range(len(a10) - 1)]
            ok("[!] ES6: akis koptu -> her yeniden baglanma YENI imzali URL (farkli _s ve _i, hepsi gecerli) ve bekleme ARTIYOR (~1, ~2, ~4 s)",
               len(a10) == 3 and len({r["url"] for r in a10}) == 3 and all(r["imza"] and r["gecerli"] for r in a10)
               and a10[-1]["kod"] == 200 and len(ar) == 2 and 1.5 <= ar[0] <= 3.5 and 3.2 <= ar[1] <= 6.5,
               f"{[r['kod'] for r in a10]} · araliklar {[round(x, 2) for x in ar]}")

            # ── 11. kart yeniden basladi: yeni acilis -> akis + komut yeni acilisla, uyari YOK ────────
            b11 = sira()
            kart.yeniden_basla()
            son = time.monotonic() + 12
            while time.monotonic() < son and not [r for r in istekler()[b11:] if r["yol"] == "/akis" and r["kod"] == 200]:
                t.bekle(0.2)
            t.js(f"{UYG}.gonder('G?')")
            g11 = komut_bekle("G?", b11, 6, imza=True)
            a11 = [r for r in istekler()[b11:] if r["yol"] in ("/akis", "/komut")]
            ok("[!] ES4/ES6: kart yeniden basladi (yeni X-Acilis) -> akis ve komut YENI acilisla imzali kabul; cihaz isaretlenmedi, uyari yok",
               g11 is not None and g11["acilis"] == kart.acilis and any(r["yol"] == "/akis" and r["kod"] == 200 for r in a11)
               and not t.js("!!document.querySelector('[data-es-uyari]')") and not (t.js(IDB_KAYIT_JS) or [{}])[0].get("tanimiyor"),
               str([(r['yol'], r['kod']) for r in a11]))

            # ── 12. cihaz listesi: baska cihazi kaldirma IKI ASAMALI ──────────────────────────
            with kart.k:
                kart.cihazlar[2] = {"K": secrets.token_bytes(32), "ad": "PC kopru", "eklenme": int(time.time()) - 86400, "son": 0}
            t.js("location.hash = '#/ayar/eslestirme'")
            bekle_js(t, "document.querySelector('[data-es-durum]') && document.querySelector('[data-es-durum]').offsetParent", 6)
            t.js("[...document.querySelectorAll('[data-ay-bolum=eslestirme] button')].find(b => b.textContent.trim() === 'Yenile').click()")
            satir = bekle_js(t, "document.querySelectorAll('[data-es-cihaz]').length === 2 && [...document.querySelectorAll('[data-es-cihaz]')]"
                                ".map(r => r.textContent.replace(/\\s+/g, ' ').trim())", 8) or []
            b12 = sira()
            tikla_cdp(t, "[data-es-kaldir='2']")
            silahli = bekle_js(t, "document.activeElement && document.activeElement.getAttribute('data-es-kaldir-eminim') === '2'", 4)
            hic = [r for r in istekler()[b12:] if r["yol"] == "/cihaz/sil"]
            tikla_cdp(t, "[data-es-kaldir-eminim='2']")
            kalan = bekle_js(t, "document.querySelectorAll('[data-es-cihaz]').length === 1 && document.querySelector('[data-es-cihaz]').dataset.esCihaz", 8)
            sil = [r for r in istekler()[b12:] if r["yol"] == "/cihaz/sil"]
            ok("[!] ES7: cihaz listesi (bu tarayici METINLE isaretli); baska cihazi kaldirma IKI ASAMALI — ilk tik karta gitmez (odak 'Eminim'de),"
               " ikinci tik imzali POST /cihaz/sil?n=2; liste tazelendi",
               len(satir) == 2 and "bu tarayıcı" in satir[0] and bool(silahli) and not hic and len(sil) == 1 and sil[0]["q"].get("n") == "2"
               and sil[0]["imza"] and sil[0]["gecerli"] and kalan == "1" and 2 not in kart.cihazlar, f"{satir} · {kalan}")

            # ── 13. ES8: saat yalniz NTP yokken, dugmeyle ─────────────────────────────────────
            gorunur = t.js("!!document.querySelector('[data-es-saat-ayarla]')")
            b13 = sira()
            tikla_cdp(t, "[data-es-saat-ayarla]")
            saat = bekle_js(t, "/eşleşmiş bir cihazdan/.test((document.querySelector('[data-es-saat]') || {}).textContent || '')", 6)
            st = [r for r in istekler()[b13:] if r["yol"] == "/saat"]
            with kart.k:
                kart.saat = 1
            t.js("[...document.querySelectorAll('[data-ay-bolum=eslestirme] button')].find(b => b.textContent.trim() === 'Yenile').click()")
            ntp = bekle_js(t, "!document.querySelector('[data-es-saat-ayarla]') && !!document.querySelector('[data-es-ntp]')", 6)
            ok("[!] ES8: kartin NTP saati yokken dugme var; tiklayinca imzali POST /saat?unix=<simdi>, kart 'cihazdan' der; NTP gelince dugme KALKAR",
               gorunur is True and bool(saat) and len(st) == 1 and st[0]["imza"] and st[0]["gecerli"]
               and abs((kart.saat_unix or 0) - time.time()) < 10 and bool(ntp), f"{st[0]['q'] if st else None}")
            with kart.k:
                kart.saat = 0

            # ── 13b. WIG: 390 px telefonda uc gorunumde Eslestirme bolumu yatay TASMIYOR ───────────
            t.ekran(390, 844)
            tas = {}
            for ad in TEMALAR:
                tema_sec(t, ad, "#/ayar/eslestirme")
                bekle_js(t, "document.querySelectorAll('[data-es-cihaz]').length === 1", 6)
                t.bekle(0.3)
                tas[ad] = tasma(t)
                resim(f"3-telefon-{ad}")
            ust = t.js("(() => { const f = document.querySelector('[data-es-durum]').getBoundingClientRect();"
                       " return f.right <= document.documentElement.clientWidth; })()")
            t.cagir("Emulation.clearDeviceMetricsOverride")
            tema_sec(t, "koyu", "#/ayar/eslestirme")
            ok("[!] WIG: 390 px telefonda uc gorunumde Eslestirme bolumu (durum, liste, saat, aciklamalar) yatay TASMIYOR",
               all(v <= 0 for v in tas.values()) and ust is True, json.dumps(tas))

            # ── 14. AU10: tarayici ayarlarini sifirla eslestirmeye DOKUNMAZ ve bunu soyler ───────────
            t.js("location.hash = '#/ayar/gelismis'")
            aciklama = bekle_js(t, "(() => { const p = [...document.querySelectorAll('[data-ay-bolum=gelismis] .ipucu')].map(x => x.textContent).join(' ');"
                                   " return /eşleştirmesi/.test(p) && p; })()", 6) or ""
            tikla_cdp(t, "[data-ay-sifirla]")
            bekle_js(t, "document.activeElement && document.activeElement.hasAttribute('data-ay-sifirla-eminim')", 4)
            b14 = sira()
            tikla_cdp(t, "[data-ay-sifirla-eminim]")
            bekle_js(t, f"document.readyState === 'complete' && (() => {{ try {{ return {UYG}.bagli === true; }} catch (e) {{ return false; }} }})()", 15)
            son = time.monotonic() + 10
            akis14 = None
            while time.monotonic() < son and not akis14:
                akis14 = next((r for r in istekler()[b14:] if r["yol"] == "/akis" and r["imza"] and r["gecerli"]), None)
                t.bekle(0.2)
            kayit14 = t.js(IDB_KAYIT_JS) or []
            ok("[!] AU10/ES2: 'tarayici ayarlarini sifirla' eslestirmeye dokunmadigini SOYLER; sifirlayip yeniden yukleyince cihaz kaydi duruyor ve akis yine imzali",
               "eşleştirmesi" in aciklama and len(kayit14) == 1 and kayit14[0]["n"] == 1 and akis14 is not None, aciklama[:80])

            # ── 15. kart cihazi sildi (USB Ex1): "kart tanimiyor" uyarisi + imzasiz yol; p0 hep serbest ─
            with kart.k:
                del kart.cihazlar[1]
            b15 = sira()
            t.js(f"{UYG}.gonder('G?')")
            uyari = bekle_js(t, "(() => { const u = document.querySelector('[data-es-uyari]'); return u && u.textContent.replace(/\\s+/g, ' ').trim(); })()", 10) or ""
            g15 = komut_bekle("G?", b15, 8, imza=False)
            k15 = [(r["imza"], r["kod"]) for r in istekler()[b15:] if r["yol"] == "/komut"]
            kayit15 = (t.js(IDB_KAYIT_JS) or [{}])[0]
            ok("[!] ES4: kart cihazi silince ayni acilisla iki 401 -> 'kart tanimiyor' her gorunumde SOYLENDI (cihaz 1, Eslestirme baglantisi),"
               " kayit isaretli, komut IMZASIZ yoldan (jeton + Basic-Auth) gitti — sessizce degil",
               "tanımıyor" in uyari and "1" in uyari and g15 is not None and g15["kred"] and kayit15.get("tanimiyor") is True
               and k15[:2] == [(True, 401), (True, 401)], f"{uyari[:80]} · {k15}")
            b15b = sira()
            t.js(f"{UYG}.pilDurdurKomut()")
            p015 = komut_bekle("p0", b15b, 5)
            ok("[!] EMNIYET-P0: kart tanimazken de p0 tek imzasiz istekle hemen gitti; tarayici parolayi onbellege almisken bile Authorization YOK",
               p015 is not None and not p015["imza"] and not p015["kred"] and len([r for r in istekler()[b15b:] if r["yol"] == "/komut"]) == 1)

            # ── 16. unut: tanimiyorken karta sormadan; sonra yeniden eslesip unut (kart siler); ulasilamazken ─
            t.js("location.hash = '#/ayar/eslestirme'")
            bekle_js(t, "/TANIMIYOR/.test((document.querySelector('[data-es-durum]') || {}).textContent || '')", 8)
            b16 = sira()
            tikla_cdp(t, "[data-es-unut]")
            bekle_js(t, "document.activeElement && document.activeElement.hasAttribute('data-es-unut-eminim')", 4)
            tikla_cdp(t, "[data-es-unut-eminim]")
            u1 = bekle_js(t, "(document.querySelector('[data-es-sonuc]') || {}).textContent", 6) or ""
            bekle_js(t, "!document.querySelector('[data-es-uyari]')", 4)
            sorulan = [r for r in istekler()[b16:] if r["yol"] == "/cihaz/sil"]
            esles_formu(WEB_PAROLA)
            bekle_js(t, "/Eşleşmiş: cihaz 1/.test((document.querySelector('[data-es-durum]') || {}).textContent || '')", 15)
            b16b = sira()
            tikla_cdp(t, "[data-es-unut]")
            bekle_js(t, "document.activeElement && document.activeElement.hasAttribute('data-es-unut-eminim')", 4)
            tikla_cdp(t, "[data-es-unut-eminim]")
            u2 = bekle_js(t, "/kart da sildi/.test((document.querySelector('[data-es-sonuc]') || {}).textContent || '')"
                             " && document.querySelector('[data-es-sonuc]').textContent", 8) or ""
            sil2 = [r for r in istekler()[b16b:] if r["yol"] == "/cihaz/sil"]
            odak16 = bekle_js(t, "document.activeElement && document.activeElement.id === 'es-ad' && 'es-ad'", 3)
            esles_formu(WEB_PAROLA)
            bekle_js(t, "/Eşleşmiş: cihaz 1/.test((document.querySelector('[data-es-durum]') || {}).textContent || '')", 15)
            kart.sil_kopar = True
            tikla_cdp(t, "[data-es-unut]")
            bekle_js(t, "document.activeElement && document.activeElement.hasAttribute('data-es-unut-eminim')", 4)
            tikla_cdp(t, "[data-es-unut-eminim]")
            u3 = bekle_js(t, "/ULAŞILAMADI/.test((document.querySelector('[data-es-sonuc]') || {}).textContent || '')"
                             " && document.querySelector('[data-es-sonuc]').textContent", 8) or ""
            kart.sil_kopar = False
            kayit16 = t.js(IDB_KAYIT_JS) or []
            ok("[!] ES7: unut — kart zaten tanimiyorken karta sormadan yerelden siler (uyari kalkar); eslesmisken ONCE kartta imzali"
               " POST /cihaz/sil?n=<kendi> sonra yerel; karta ulasilamazsa yerel yine silinir ve 'kartta hala kayitli, USB Ex1' der",
               "tanımıyordu" in u1 and not sorulan and "kart da sildi" in u2 and len(sil2) == 1 and sil2[0]["imza"] and sil2[0]["gecerli"]
               and sil2[0]["q"].get("n") == "1" and "Ex1" in u3 and kayit16 == [] and 1 in kart.cihazlar,
               f"{u1[:50]} | {u2[:40]} | {u3[:60]}")

            # ── 17. unuttuktan sonra bugunku yol geri ─────────────────────────────────────────
            b17 = sira()
            t.js(f"{UYG}.gonder('G?')")
            g17 = komut_bekle("G?", b17, 8, imza=False)
            ok("[!] ES4: unutulunca istekler yine BUGUNKU yoldan (imzasiz, jeton + Basic-Auth); uyari yok",
               g17 is not None and g17["kred"] and g17["jeton"] == JETON and not t.js("!!document.querySelector('[data-es-uyari]')"))

            # ── 17b. EU26: baska kart kimligine ait kayit listelenir ve IKI ASAMADA yalniz bu tarayicidan silinir ─────
            t.js(YABANCI_YAZ_JS)
            t.js("location.hash = '#/ayar/eslestirme'")
            bekle_js(t, "document.querySelector('[data-es-durum]') && document.querySelector('[data-es-durum]').offsetParent", 6)
            t.js("[...document.querySelectorAll('[data-ay-bolum=eslestirme] button')].find(b => b.textContent.trim() === 'Yenile').click()")
            yb = bekle_js(t, "(() => { const r = document.querySelector('[data-es-yabanci-kayit=\"fedcba9876543210\"]');"
                             " return r && r.textContent.replace(/\\s+/g, ' ').trim(); })()", 8) or ""
            b17 = sira()
            tikla_cdp(t, "[data-es-yabanci-sil='fedcba9876543210']")
            silahli17 = bekle_js(t, "document.activeElement && document.activeElement.getAttribute('data-es-yabanci-eminim') === 'fedcba9876543210'", 4)
            tikla_cdp(t, "[data-es-yabanci-eminim='fedcba9876543210']")
            gitti = bekle_js(t, "!document.querySelector('[data-es-yabanci]')", 6)
            kalan17 = [k for k in (t.js(IDB_KAYIT_JS) or []) if k.get("kimlik") == "fedcba9876543210"]
            ok("[!] EU26: baska kart kimligine ait kayit Eslestirme'de listelendi (kimlik + ad); silme IKI ASAMALI (odak 'Eminim'de),"
               " yalniz bu tarayicidan silindi (karta istek YOK), bolum kalkti",
               "fedcba9876543210" in yb and "eski kart" in yb and bool(silahli17) and bool(gitti) and not kalan17
               and not [r for r in istekler()[b17:] if r["yol"].startswith("/cihaz/")], yb[:80])
            ok("[!] EU27/WIG: gercek tarayicida odak kaybolmuyor — eslesince durum satirinda, unutunca cihaz adi alaninda",
               odak4 is True and odak16 == "es-ad", f"{odak4} · {odak16}")

            # ── 18. guvenlik + temizlik ───────────────────────────────────────────────────────
            tara2 = t.js(PAROLA_TARA_JS % json.dumps(WEB_PAROLA)) or {}
            ok("[!] ES3: uc eslestirme + unut sonrasi da parola HICBIR depoda yok (kayit kopyalari 'olcum-kayit' dahil butun IndexedDB), alan bos",
               tara2.get("bul") == [] and "olcum-kayit" in tara2.get("dbs", []) and tara2.get("kayit", 0) >= 3 and tara2.get("alan") == ""
               and tara2.get("dom") is False, json.dumps(tara2, ensure_ascii=False)[:200])
            with kart.k:
                govdeler = [r["govde"] for r in kart.istekler if r["yol"] == "/komut"]
            durumlar = istekler(lambda r: r["yol"] == "/durum")
            ok("[!] P0-S/EU28: /durum (kopru yoklamasi) eslesmeden once de sonra da tarayicinin onbellekteki Basic-Auth'unu TASIMADI",
               len(durumlar) >= 2 and len([r for r in durumlar if r["t"] >= ilk_imzali_t]) >= 1 and not [r for r in durumlar if r["kred"]],
               f"{len(durumlar)} /durum · kredili {len([r for r in durumlar if r['kred']])}")
            ok("[!] N? (AP parolasini basar) HIC gonderilmedi; Eslestirme karta hicbir E / Q komutu yollamadi",
               b"N?" not in govdeler and not any(g[:1] in (b"E", b"Q") for g in govdeler), f"{len(govdeler)} komut")
            beklenen = ("401", "403", "429", "503")
            h = [x for x in t.hatalar_tum() if not any(k in x for k in beklenen)
                 and not ("ERR_EMPTY_RESPONSE" in x and "/cihaz/sil" in x)]
            ok("[!] Butun gezinti boyunca konsol / yukleme hatasi YOK (bilerek uretilen 401/403/429/503 ve ulasilamayan /cihaz/sil disinda)",
               not h, " | ".join(h[:3]) or "temiz")
    except Kopuk as hata:
        ok("[!] Sayfa beklenen akista kaldi (ust uste 3 bekleme zaman asimi yok)", False,
           f"son beklenen: {hata} — kalan olcumler ATLANDI")
    finally:
        DUR.set()
        s.shutdown()
        s.server_close()

    if profil and sys.platform == "win32":
        kalan_s = profil_surecleri(profil)
        ok("[!] Basliksiz Edge SIZMADI (bu testin profiliyle calisan msedge sureci kalmadi)", not kalan_s, str(kalan_s))
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0



if __name__ == "__main__":
    raise SystemExit(main())
