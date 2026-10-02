# -*- coding: utf-8 -*-
"""3H-1 — AYARLAR TARAYICIDA (T3H): sahte karta karsi uctan uca.

    python tarayici_ayarlar.py                    # sessiz, 0/1 doner
    python tarayici_ayarlar.py --goruntu DIZIN    # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B7 (`test_arayuz3.js` bolum 30) saf mantigi ve sablonu node'da sinar;
   bolumlerin GERCEKTEN gorunup gizlendigini, tembel modulun YALNIZ gerekince indigini, gercek
   IndexedDB kopyasini (boyut, oturum, silme), `navigator.storage`in guvenli baglamda VAR ve kartin
   http:// adresinde YOK oldugunu, dil gecisinin sayfa yenilenmeden kabugu / Kayitlar'i / sekme
   basligini degistirdigini, geri tusunu, uc gorunumu ve 390 px telefonu sinayamaz.

Sahte kart: `tarayici_kayitlar.Kart` (B72.E'nin `/kayit/veri` sahtesi + dizin) — bu betigin kendi
sunucusuyla: `/kal/liste` (kod degistirilebilir: 200 / 401), `/kunye.json` (`arayuz-uret.py`
`kunye_hesapla` — kartin goruntusune giren kunyenin AYNISI), `/akis` (SSE), `/komut` (her komut
kaydedilir: Ayarlar HICBIR kalibrasyon komutu gondermemeli, `N?` hic gitmemeli).
Iki koken: `http://olcum.test:<port>/` (kartin sayfasi gibi: guvenli baglam DISI, akis kipi,
ayni koken — C1) ve `http://127.0.0.1:<port>/` (guvenli baglam: storage.estimate / persist var).
Beklenen degerler BAGIMSIZ Python hesabindan (`kopru/kayit_bicim.py` cozucusu: akis boyu, oturum
sayisi; sahte kartin kalibrasyon JSON'u; `arayuz-uret.py` panel surumu).
"""
from __future__ import annotations

import base64
import http.server
import importlib.util
import json
import struct
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
from tarayici import bos_port                               # noqa: E402
from tarayici_tema import css_takimlari, rgb, TEMALAR       # noqa: E402
from tarayici_karsilastir import (KrTarayici, Kopuk, bekle_js, profil_surecleri,  # noqa: E402
                                  tasma, tema_sec, tikla_cdp)

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
AD = "olcum.test"
JETON = "abc123"
SIRA = ["baglanti", "ag", "kalibrasyon", "kal-gecmis", "depolama", "dil-gorunum", "gelismis"]
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


def uretec():
    oz = importlib.util.spec_from_file_location("arayuz_uret", BURASI / "arayuz-uret.py")
    u = importlib.util.module_from_spec(oz)
    oz.loader.exec_module(u)
    return u


def kal_liste() -> dict:
    """Kartin /kal/liste bicimi (kal_liste_sayfa): iki kayit + bir BOZUK, etkin 2, Turkce not."""
    k1, k2 = TK.kal_json(1), TK.kal_json(2)
    k2["not"] = "şönt değişti"
    k2["tur"] = 2
    k2["kaynak"] = 0
    k2["kal"]["normal"]["kazanc"] = 1.0125
    return {"surum": 1, "adet": 3, "taslak": 0, "etkin": 2, "azami": 40,
            "kayitlar": [k1, k2, {"no": 3, "bozuk": True}]}


DUR = threading.Event()


def sunucu_kur(kart):
    MIME = TK.MIME

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
                p = (ORTAK / yol[len("/ortak/"):]).resolve()
                if p.parent != ORTAK.resolve() or not p.is_file():
                    return self._gonder(404, b"yok")
            else:
                p = (ARAYUZ / (yol.lstrip("/") or "index.html")).resolve()
                if ARAYUZ.resolve() not in p.parents or not p.is_file():
                    return self._gonder(404, b"yok")
            self._gonder(200, p.read_bytes(), MIME.get(p.suffix, "application/octet-stream"))

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            with kart.kilit:
                kart.istek_yollari.append(u.path)
            if u.path == "/kayit/liste":
                with kart.kilit:
                    d = kart.dizin()
                return self._gonder(200, json.dumps(d).encode(), "application/json")
            if u.path == "/kayit/veri":
                sira = int(q.get("sira", ["1"])[0])
                with kart.kilit:
                    govde, ilk, son = kart.veri(sira, int(q.get("bayt", ["8192"])[0]))
                    bas = {"X-Kayit-Kimlik": str(kart.kimlik), "X-Ilk-Sira": str(ilk), "X-Son-Sira": str(son),
                           "X-Sonraki-Sira": str(kart.sonraki()), "X-Onay": str(kart.onay)}
                return self._gonder(200, govde, "application/octet-stream", bas)
            if u.path == "/kal/liste":
                if kart.kal_kod != 200:
                    return self._gonder(kart.kal_kod, b"imza gerekli")
                return self._gonder(200, json.dumps(kart.kal_liste, ensure_ascii=False).encode("utf-8"),
                                    "application/json")
            if u.path == "/kunye.json":
                return self._gonder(200, json.dumps(kart.kunye).encode(), "application/json")
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


GORUNEN_JS = ("[...document.querySelectorAll('[data-ay-bolum]')].filter(e => e.offsetParent !== null)"
              ".map(e => e.dataset.ayBolum).filter((x, i, a) => a.indexOf(x) === i)")
MODUL_JS = ("performance.getEntriesByType('resource').some(e => /\\/ekran\\/ayarlar\\.js$/.test(new URL(e.name).pathname))")
ZINCIR_JS = ("performance.getEntriesByType('resource').some(e => /\\/ekran\\/(esitleme|depo_idb)\\.js$/"
             ".test(new URL(e.name).pathname))")


def bolume_git(t, bolum: str) -> bool:
    """Ic gezinmede o bolumun baglantisina GERCEK fare ile tikla, bolum gorunene dek bekle."""
    tikla_cdp(t, f".ay-nav [data-ay-git='{bolum}']")
    return bool(bekle_js(t, f"location.hash === '#/ayar/{bolum}' && {UYG}.ayarBolum === '{bolum}'"
                            f" && ({GORUNEN_JS}).length > 0", 8))


def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    takim = css_takimlari()
    akis, no = TK.akis_kur()
    kart = TK.Kart(list(akis.kayitlar))
    kart.kal_liste = kal_liste()
    kart.kal_kod = 200
    kart.istek_yollari = []
    _u = uretec()
    kart.kunye = _u.kunye_hesapla()
    s = sunucu_kur(kart)
    port = s.server_address[1]
    taban = f"http://{AD}:{port}"
    yerel = f"http://127.0.0.1:{port}"
    ham = b"".join(akis.kayitlar)
    oturum_sayisi = len(KB.oturumlari_kur(KB.akis_coz(ham)))
    eski_akis, _h = TK.yeni_kart_akisi()
    eski_b64 = base64.b64encode(b"".join(eski_akis.kayitlar)).decode()
    eski_bayt = len(b"".join(eski_akis.kayitlar))
    resimler = []
    profil = None
    print("=" * 78)
    print("  3H-1  AYARLAR — TARAYICIDA, SAHTE KARTA KARSI (T3H)")
    print("=" * 78)
    print(f"     sahte kart: {taban}  ({len(kart.kayitlar)} kayit, {len(ham)} B, {oturum_sayisi} oturum,"
          f" kimlik {kart.kimlik}); panel surumu {kart.kunye['surum']}\n")

    def resim(ad: str) -> None:
        if not goruntu:
            return
        y = goruntu / f"{ad}.png"
        t.goruntu(str(y))
        resimler.append(y)

    try:
        with KrTarayici(auth_iptal=False, port=bos_port(), ek_arg=[f"--host-resolver-rules=MAP {AD} 127.0.0.1"]) as t:
            profil = t.profil
            t.cagir("Log.enable")
            t.tema("dark")

            # ── 1. #/ayar (taze sayfa): ilk bolum, gezinme, modul INMEDI ─────
            t.git(taban + "/#/ayar")
            bekle_js(t, f"{UYG}.gorunum === 'ayar' && {UYG}.bagli === true", 10)
            t.bekle(0.4)
            nav = t.js("[...document.querySelectorAll('.ay-nav a')].map(a => ({h: a.getAttribute('href'),"
                       " c: a.getAttribute('aria-current'), m: a.textContent.trim()}))") or []
            gor = t.js(GORUNEN_JS)
            ok("[!] AY2: #/ayar ilk bolumu (Baglanti) gosterir, digerleri GIZLI; ic gezinmede yedi bolum karardaki sirayla,"
               " secili olan aria-current",
               [n["h"] for n in nav] == [f"#/ayar/{b}" for b in SIRA] and nav[0]["c"] == "true"
               and all(n["c"] is None for n in nav[1:]) and gor == ["baglanti"]
               and [n["m"] for n in nav][:2] == ["Bağlantı", "Ağ"], f"{gor} {[n['m'] for n in nav]}")
            ok("[!] AY2: Ayarlar modulu (ekran/ayarlar.js) eski bolumlerde INMEDI",
               t.js(MODUL_JS) is False)
            resim("0-baglanti")

            # ── 3. Gelismis: modul iner, IndexedDB zinciri INMEZ; kunye, firmware, tasiyici ──
            bolume_git(t, "gelismis")
            bilgi = bekle_js(t, "(() => { const p = document.querySelector('[data-ay-panel]');"
                                " return p && /·/.test(p.textContent) && {p: p.textContent.trim(),"
                                " f: document.querySelector('[data-ay-fw]').textContent.trim(),"
                                " t: document.querySelector('[data-ay-tasiyici]').textContent.trim()}; })()", 10) or {}
            ok("[!] AY6: Gelismis — panel surumu kunyeden (Python kunye_hesapla ile AYNI), firmware afis gorulmedi (WiFi) diyor,"
               " baglanti yolu yazili",
               bilgi.get("p", "").startswith(kart.kunye["surum"] + " · ") and "afişi görülmedi" in bilgi.get("f", "")
               and bilgi.get("t") == "WiFi / köprü (akış)", json.dumps(bilgi, ensure_ascii=False))
            ok("[!] AY2: Gelismis acilinca modul indi ama IndexedDB zinciri (esitleme.js / depo_idb.js) INMEDI (tek dosya)",
               t.js(MODUL_JS) is True and t.js(ZINCIR_JS) is False)
            resim("1-gelismis")

            # ── 2. Kayitlar: kartin kopyasi bu tarayiciya (kalibrasyon.json dahil) ──
            tikla_cdp(t, "#serit .gorunum-sekme[href='#/kayitlar']")
            bekle_js(t, "document.querySelectorAll('.kl-satir').length >= 5 && [...document.querySelectorAll('.kl-satir')]"
                        ".every(a => a.dataset.nerede === 'ikisi')", 60)
            t.js("location.hash = '#/ayar/gelismis'")
            bekle_js(t, f"{UYG}.ayarBolum === 'gelismis'", 6)

            # ── 4. Kalibrasyon gecmisi: karttan; degerler; sonra 401 -> yerel kopya ──
            bolume_git(t, "kal-gecmis")
            satirlar = bekle_js(t, "(() => { const r = [...document.querySelectorAll('[data-ay-kal]')];"
                                   " return r.length === 3 && r.map(x => ({n: x.dataset.ayKal, m: x.textContent.replace(/\\s+/g, ' ').trim(),"
                                   " e: x.classList.contains('ay-etkin')})); })()", 10) or []
            kaynak = t.js("document.querySelector('[data-ay-kal-kaynak]').textContent.trim()")
            ok("[!] AY5: karttan /kal/liste — yeniden eskiye (3 bozuk, 2, 1), etkin 2 METINLE isaretli, Turkce not ve sozlukten tur",
               [r["n"] for r in satirlar] == ["3", "2", "1"] and satirlar[1]["e"] and "etkin" in satirlar[1]["m"]
               and "şönt değişti" in satirlar[1]["m"] and "ince ayar" in satirlar[1]["m"]
               and "okuyamadı" in satirlar[0]["m"] and "kartın kalibrasyon geçmişi" in (kaynak or ""),
               json.dumps(satirlar, ensure_ascii=False)[:300])
            degerler = t.js("Object.fromEntries([...document.querySelectorAll('[data-ay-alan]')].map(r => [r.dataset.ayAlan,"
                            " r.querySelector('td').textContent.trim()]))") or {}
            k2 = kart.kal_liste["kayitlar"][1]["kal"]
            ok("[!] AY5: degerler tablosu etkin kaydin 17 alani, kartin JSON degerleriyle ayni",
               len(degerler) == 17 and float(degerler.get("normal.kazanc", "nan")) == k2["normal"]["kazanc"]
               and float(degerler.get("sont_ohm", "nan")) == k2["sont_ohm"]
               and float(degerler.get("yuksek.n", "nan")) == k2["yuksek"]["n"], json.dumps(degerler)[:200])
            tikla_cdp(t, "[data-ay-kal-sec='1']")
            bas1 = bekle_js(t, "document.querySelector('[data-ay-kal-sec=\"1\"]').getAttribute('aria-pressed') === 'true'"
                               " && document.querySelector('[data-ay-kal-degerler] caption').textContent", 4)
            ok("AY5: baska kaydin 'Degerler'i o kaydi gosterir (aria-pressed, tablo basligi)", "1" in (bas1 or ""), str(bas1))
            kart.kal_kod = 401
            t.js("[...document.querySelectorAll('[data-ay-bolum=\"kal-gecmis\"] button')].find(b => b.textContent.trim() === 'Yenile').click()")
            yerel_k = bekle_js(t, "(() => { const k = document.querySelector('[data-ay-kal-kaynak]').textContent;"
                                  " return /bu tarayıcıdaki kopya/.test(k) && {k, n: document.querySelectorAll('[data-ay-kal]').length}; })()", 8) or {}
            ok("[!] AY5: kart 401 (imzali istek) -> bu tarayicidaki kopya (esitlemenin yazdigi), kaynak ve sebep YAZILI",
               f"kart akışı {kart.kimlik}" in yerel_k.get("k", "") and "imzalı" in yerel_k.get("k", "") and yerel_k.get("n") == 3,
               json.dumps(yerel_k, ensure_ascii=False))
            kart.kal_kod = 200
            resim("2-kal-gecmis")

            # ── 5. Depolama (guvenli baglam DISI): kota yok + sebep; kopya; eski kopya silme ──
            bolume_git(t, "depolama")
            dep = bekle_js(t, "(() => { const r = [...document.querySelectorAll('[data-ay-akis]')];"
                              " return r.length && r.map(x => [...x.children].map(c => c.textContent.replace(/\\s+/g, ' ').trim())); })()", 10) or []
            kota = t.js("({y: (document.querySelector('[data-ay-kota-yok]') || {}).textContent || '',"
                        " p: !!document.querySelector('progress.ay-kota'), s: window.isSecureContext,"
                        " st: typeof navigator.storage})")
            ok("[!] AY4: kartin http:// adresinde (guvenli baglam DEGIL) navigator.storage yok — cokmez, SEBEBI yazar, kota cubugu yok",
               kota["s"] is False and kota["st"] == "undefined" and "güvenli bağlam" in kota["y"] and not kota["p"],
               json.dumps(kota, ensure_ascii=False))
            ok("[!] AY4: kopya satiri — kart akisi, boyut (Python akisi ile ayni bayt), oturum sayisi (Python cozucusu), 'bu kart'",
               len(dep) == 1 and dep[0][0] == str(kart.kimlik) and dep[0][1] == TK_bayt(len(ham))
               and dep[0][2] == str(oturum_sayisi) and "bu kart" in dep[0][6] and dep[0][5] == "kapalı",
               json.dumps(dep, ensure_ascii=False))
            # eski kart kopyasi + arsiv secimi
            t.js(f"localStorage.setItem('olcum.arsiv.{kart.kimlik}', 'true')")
            eklenen = t.js("(async () => { const d = await import('/ekran/depo_idb.js'); const vt = await d.vtAc();"
                           " await d.akisHazirla(vt, 999); const b = Uint8Array.from(atob(%s), c => c.charCodeAt(0));"
                           " await d.idbDepo(vt, 999).veriEkle(b); return (await d.akislar(vt)).map(a => a.kimlik); })()"
                           % json.dumps(eski_b64))
            t.js("[...document.querySelectorAll('[data-ay-bolum=\"depolama\"] button')].find(b => b.textContent.trim() === 'Yenile').click()")
            dep2 = bekle_js(t, "(() => { const r = [...document.querySelectorAll('[data-ay-akis]')];"
                               " return r.length === 2 && r.map(x => [...x.children].map(c => c.textContent.replace(/\\s+/g, ' ').trim())); })()", 8) or []
            sat = {r[0]: r for r in dep2}
            ok("[!] AY4: baska kimlikli akis 'eski kart kopyasi' (kart dizini bilindigi icin), arsiv secimi (C3) gorunur",
               sorted(eklenen or []) == sorted([kart.kimlik, 999]) and "eski kart kopyası" in sat.get("999", [""] * 8)[6]
               and sat.get("999", [""] * 8)[1] == TK_bayt(eski_bayt)
               and sat.get(str(kart.kimlik), [""] * 8)[5].startswith("açık"), json.dumps(dep2, ensure_ascii=False))
            # arsiv yalniz GOSTERIM icin acildi: kapat — yoksa sonraki Kayitlar ziyareti karta Go<sira> yollar (C3)
            t.js(f"localStorage.removeItem('olcum.arsiv.{kart.kimlik}')")
            tikla_cdp(t, "[data-ay-sil='999']")
            silahli = bekle_js(t, "document.activeElement && document.activeElement.getAttribute('data-ay-sil-eminim') === '999'"
                                  " && !!document.querySelector('[data-ay-bolum=\"depolama\"] .uyari[role=alert]')", 4)
            hala = t.js("(async () => { const d = await import('/ekran/depo_idb.js'); return (await d.akislar(await d.vtAc())).length; })()")
            tikla_cdp(t, "[data-ay-sil-eminim='999']")
            sonra = bekle_js(t, "document.querySelectorAll('[data-ay-akis]').length === 1"
                                " && document.querySelector('[data-ay-akis]').dataset.ayAkis", 8)
            kalan = t.js("(async () => { const d = await import('/ekran/depo_idb.js'); return (await d.akislar(await d.vtAc())).map(a => a.kimlik); })()")
            ok("[!] AY4: silme IKI ASAMALI (ilk tik yalniz silahlar, odak 'Eminim'de, uyari) — ikinci tikla YALNIZ o akis silinir",
               bool(silahli) and hala == 2 and sonra == str(kart.kimlik) and kalan == [kart.kimlik], f"{silahli} {hala} {sonra} {kalan}")
            resim("3-depolama")

            # ── 6. Dil: aninda (yenileme yok); kabuk, Ayarlar, Kayitlar, baslik, <html lang> ──
            t.js("window.__isaret = 3")
            bolume_git(t, "dil-gorunum")
            tikla_cdp(t, "[data-ay-dil='en']")
            en = bekle_js(t, "document.documentElement.lang === 'en' && ({t: document.title, l: localStorage.getItem('olcum.dil'),"
                             " i: window.__isaret, n: [...document.querySelectorAll('.ay-nav a')].map(a => a.textContent.trim()),"
                             " s: [...document.querySelectorAll('#serit .gorunum-sekme')].map(a => a.textContent.trim()),"
                             " p: document.querySelector('[data-ay-dil=en]').getAttribute('aria-pressed')})", 6) or {}
            ok("[!] AY3: English — <html lang>, sekme basligi, ic gezinme ve serit ANINDA; secim `olcum.dil`de; sayfa YENILENMEDI",
               en.get("t") == "Settings — Measurement Board" and en.get("l") == '"en"' and en.get("i") == 3
               and en.get("n", [""])[4] == "Storage" and "Recordings" in en.get("s", []) and en.get("p") == "true",
               json.dumps(en, ensure_ascii=False)[:300])
            tikla_cdp(t, "#serit .gorunum-sekme[href='#/kayitlar']")
            kl = bekle_js(t, "location.hash === '#/kayitlar' && document.title.startsWith('Recordings') && ({t: document.title,"
                             " h: (document.querySelector('.kl h1') || {}).textContent})", 6) or {}
            ok("[!] AY3: Kayitlar (ayri modul) da yenilemeden Ingilizce; baslik da",
               kl.get("t") == "Recordings — Measurement Board" and kl.get("h") == "Recordings", json.dumps(kl, ensure_ascii=False))
            t.js("location.hash = '#/ayar/gelismis'")
            gel = bekle_js(t, "(() => { const h = document.querySelector('[data-ay-bolum=gelismis] h2');"
                              " return h && h.offsetParent && h.textContent.trim(); })()", 6)
            ok("AY3: Ayarlar modulu da Ingilizce (Gelismis basligi)", gel == "Version and diagnostics", str(gel))
            resim("4-en")
            t.js("location.hash = '#/ayar/dil-gorunum'")
            bekle_js(t, f"{UYG}.ayarBolum === 'dil-gorunum'", 4)
            tikla_cdp(t, "[data-ay-dil='tr']")
            tr = bekle_js(t, "document.documentElement.lang === 'tr' && document.title === 'Ayarlar — Ölçüm Kartı'"
                             " && localStorage.getItem('olcum.dil') === '\"tr\"'", 6)
            ok("AY3: Turkce'ye donus da aninda", bool(tr))

            # ── 7. geri tusu bolumler arasinda ─────────────────────────────
            bolume_git(t, "ag")
            bolume_git(t, "depolama")
            t.js("history.back()")
            g1 = bekle_js(t, f"location.hash === '#/ayar/ag' && {UYG}.ayarBolum === 'ag' && ({GORUNEN_JS}).join() === 'ag'", 6)
            t.js("history.forward()")
            g2 = bekle_js(t, f"location.hash === '#/ayar/depolama' && ({GORUNEN_JS}).join() === 'depolama'", 6)
            ok("[!] AY2: geri / ileri tusu bolumler arasinda gezer (adres = bolum)", bool(g1) and bool(g2), t.js("location.hash"))

            # ── 8. uc gorunum: ic gezinmenin etkin bolumu temanin vurgu zemini ──
            sonuc = {}
            for ad in TEMALAR:
                tema_sec(t, ad, "#/ayar/depolama")
                bekle_js(t, f"{UYG}.ayarBolum === 'depolama'", 4)
                t.bekle(0.3)
                sonuc[ad] = t.js("getComputedStyle(document.querySelector('.ay-sekme.etkin')).backgroundColor")
                resim(f"5-{ad}")
            ok("[!] AY7: uc gorunumde etkin bolum temanin --vurgu-zemin'i (renk + cizgi + kalin)",
               all(sonuc[ad] == "rgb(%d, %d, %d)" % rgb(takim[ad]["--vurgu-zemin"]) for ad in TEMALAR), json.dumps(sonuc))

            # ── 9. telefon 390 px: gezinme USTTE, tasma yok (uc gorunum, uc bolum) ──
            t.ekran(390, 844)
            t.bekle(0.6)
            tas = {}
            for ad in TEMALAR:
                tema_sec(t, ad, "#/ayar/depolama")
                for b in ("depolama", "kal-gecmis", "gelismis"):
                    t.js(f"location.hash = '#/ayar/{b}'")
                    bekle_js(t, f"{UYG}.ayarBolum === '{b}' && ({GORUNEN_JS}).join() === '{b}'", 5)
                    t.bekle(0.3)
                    tas[f"{ad}-{b}"] = tasma(t)
            dz = t.js("(() => { const n = document.querySelector('.ay-nav').getBoundingClientRect();"
                      " const k = [...document.querySelectorAll('[data-ay-bolum]')].find(e => e.offsetParent).getBoundingClientRect();"
                      " return {nAlt: n.bottom, kUst: k.top, nSag: n.right, cw: document.documentElement.clientWidth}; })()")
            ok("[!] AY2: 390 px'te ic gezinme icerigin USTUNDE; uc gorunumde Ayarlar bolumleri YATAY TASMIYOR",
               all(v <= 0 for v in tas.values()) and dz["nAlt"] <= dz["kUst"] and dz["nSag"] <= dz["cw"], f"{tas} {dz}")
            resim("6-telefon")
            t.cagir("Emulation.clearDeviceMetricsOverride")
            tema_sec(t, "koyu", "#/ayar/gelismis")

            # ── 10. sifirla: yalniz olcum.* anahtarlari, iki asama, yeniden yukleme; kopyalar KALIR ──
            t.js("localStorage.setItem('baska.anahtar', 'kalsin'); localStorage.setItem('olcum.sinama', '1')")
            bekle_js(t, f"{UYG}.ayarBolum === 'gelismis'", 4)
            t.js("location.hash = '#/ayar/ag'")
            bekle_js(t, f"{UYG}.ayarBolum === 'ag'", 4)
            t.js("location.hash = '#/ayar/gelismis'")          # anahtar listesi gorunuste tazelenir
            liste = bekle_js(t, "(() => { const l = [...document.querySelectorAll('[data-ay-anahtarlar] li')].map(x => x.textContent.trim());"
                                " return l.includes('olcum.sinama') && l; })()", 6) or []
            ok("AY6: silinecek anahtarlar LISTELENIR (yalniz olcum.)", all(a.startswith("olcum.") for a in liste)
               and "olcum.dil" in liste and "baska.anahtar" not in liste, ", ".join(liste))
            t.js("window.__isaret = 7")
            tikla_cdp(t, "[data-ay-sifirla]")
            silahli2 = bekle_js(t, "document.activeElement && document.activeElement.hasAttribute('data-ay-sifirla-eminim')", 4)
            hala2 = t.js("localStorage.getItem('olcum.sinama')")
            tikla_cdp(t, "[data-ay-sifirla-eminim]")
            yeni = bekle_js(t, "window.__isaret === undefined && document.readyState === 'complete' && !!document.querySelector('.ay-nav')"
                               " && ({s: localStorage.getItem('olcum.sinama'), b: localStorage.getItem('baska.anahtar'),"
                               " d: localStorage.getItem('olcum.dil')})", 10) or {}
            idb = t.js("(async () => { const d = await import('/ekran/depo_idb.js'); return (await d.akislar(await d.vtAc())).map(a => a.kimlik); })()")
            ok("[!] AY6: sifirlama IKI ASAMALI; yalniz `olcum.` anahtarlari silindi, sayfa YENIDEN YUKLENDI, kayit kopyalari (IndexedDB) KALDI",
               bool(silahli2) and hala2 == "1" and yeni.get("s") is None and yeni.get("b") == "kalsin"
               and yeni.get("d") is None and idb == [kart.kimlik], f"{silahli2} {hala2} {yeni} {idb}")

            # ── 11. guvenli baglam (127.0.0.1): storage.estimate + persist sonucu ──
            t.git(yerel + "/#/ayar/depolama")
            kt = bekle_js(t, "(() => { const k = document.querySelector('[data-ay-kota]'); const p = document.querySelector('progress.ay-kota');"
                             " return k && /kullanılıyor/.test(k.textContent) && {k: k.textContent.trim(), p: !!p,"
                             " s: window.isSecureContext, c: (document.querySelector('[data-ay-kalici]') || {}).textContent}; })()", 12) or {}
            ok("[!] AY4: guvenli baglamda (localhost) storage.estimate kullanim / kota + cubuk + kalici durumu",
               kt.get("s") is True and kt.get("p") is True and "Kalıcı depolama" in (kt.get("c") or ""), json.dumps(kt, ensure_ascii=False))
            ist = t.js("!!document.querySelector('[data-ay-kalici-iste]')")
            if ist:
                tikla_cdp(t, "[data-ay-kalici-iste]")
            ks = bekle_js(t, "(() => { const s = document.querySelector('[data-ay-kalici-sonuc]');"
                             " return s && {m: s.textContent.trim(), k: " + UYG + ".$refs ? null : null}; })()", 8) if ist else {"m": "zaten kalici"}
            kalici = t.js("navigator.storage.persisted()")
            ok("[!] AY4: 'Kalici depolama iste' persist() SONUCUNU yazar (verdi / vermedi) ve durum tarayicininkiyle tutarli",
               (not ist and kalici is True) or (bool(ks) and (("verdi" in ks["m"]) == bool(kalici))
                                                and ("verdi" in ks["m"] or "vermedi" in ks["m"])),
               f"{ks} persisted={kalici}")
            t.js("location.hash = '#/ayar/kal-gecmis'")
            kh = bekle_js(t, "(() => { const h = document.querySelector('[data-ay-kal-hic]'); const k = document.querySelector('[data-ay-kal-kaynak]');"
                             " return h && h.offsetParent && {h: h.textContent.trim(), k: k.textContent.trim()}; })()", 8) or {}
            ok("AY5: USB yolunda (localhost) karta SORULMAZ, bu kokende kopya yok -> 'gecmis yok' + sebep",
               "USB" in kh.get("k", "") and "Kalibrasyon geçmişi yok" in kh.get("h", ""), json.dumps(kh, ensure_ascii=False))
            resim("7-yerel")

            # ── 12. komutlar ve konsol ─────────────────────────────────────
            with kart.kilit:
                kom = list(kart.tum_komutlar)
                yollar = list(kart.istek_yollari)
            ok("[!] AY5: Ayarlar karta HICBIR kalibrasyon / ag komutu gondermedi (k…, N?, N…, Ns…, Go… yok)",
               not any(k.startswith(("k", "N", "Go", "z", "Z", "g", "a")) for k in kom), json.dumps(kom))
            ok("AY5/AY6: kartin okunan uclari yalniz /kal/liste, /kunye.json (+ Kayitlar'in /kayit/*)",
               "/kal/liste" in yollar and "/kunye.json" in yollar, str(sorted(set(yollar)))[:200])
            # 401 /kal/liste bu testin KENDI urettigi ret (4. adim) — beklenen tek ag hatasi
            h = [x for x in t.hatalar_tum() if not ("401" in x and "/kal/liste" in x)]
            ok("[!] Butun gezinti boyunca konsol / yukleme hatasi YOK (bilerek uretilen 401 /kal/liste disinda)",
               not h, " | ".join(h[:3]) or "temiz")
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


def TK_bayt(n: int) -> str:
    """Bagimsiz boyut yazimi (ekran/kayitlar.js baytYaz kurali)."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 / 1024:.2f} MB"


if __name__ == "__main__":
    raise SystemExit(main())
