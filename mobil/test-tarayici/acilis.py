"""acilis.py — 5P P1: telefon paketinin (mobil/dist) BASLIKSIZ Edge'de sıkı CSP ile açılışı.

NEDEN: Vue'nun runtime sürümünde derlenmemiş bir şablon üretim kipinde SESSİZCE boş çizilir; CSP bir
satır içi betiği ya da `new Function`'ı yalnız konsola yazarak engeller. Birim testleri
(test/panel_paket.test.js) dönüşümü sınar; bu test GERÇEK tarayıcıda paketin açıldığını ölçer:

  1. Paket geçici dizine derlenir (`vite build`; `--dist` ile var olan kullanılır).
  2. Küçük statik sunucu index.html'deki CSP'nin AYNISINI başlık olarak da gönderir.
  3. Edge (uretim/tarayici.py — sızıntısız kapanış, geçici profil, senkron kapalı) telefon ekranıyla açar:
     #uyg boyandı (v-cloak düştü), 7 görünüm (#/canli … #/konsol) + Ayarlar'ın bölümleri + Bağlantı
     penceresi açılır ve içerik çizer.
  4. DOM şablonu tuzağı KESİN denetimi: tarayıcının ayrıştırdığı #uyg innerHTML'i (PC'de Vue'nun derlediği)
     ile ham metin (telefon paketinin derlediği) AYNI render kodunu üretmeli (test-tarayici/sablon_karsilastir.mjs).
  KIRMIZI: CSP ihlali, yakalanmamış istisna, console.error / Vue uyarısı, paketin kendi dosyasında 404.
  Ortam (P3) yoksa panel ortamsız açılır ve taşıyıcıları dener — o istekler BİLGİ olarak yazılır.

Kullanım:  python mobil/test-tarayici/acilis.py [--dist DİZİN] [--goruntu DİZİN]
Çıkış kodu: 0 = GEÇTİ, 1 = KALDI.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BURASI = Path(__file__).resolve().parent
MOBIL = BURASI.parent
KOK = MOBIL.parent
sys.path.insert(0, str(KOK / "uretim"))
from tarayici import Tarayici  # noqa: E402

GORUNUMLER = ["canli", "skop", "pil", "kayitlar", "karsilastir", "ayar", "konsol"]
# app.js AYAR_BOLUMLERI (ortamsız liste). Telefon kipinde (__olcumOrtam var) liste panelin KENDİSİNDEN okunur
# (`[data-ay-git]`): "Bu telefon" eklenir, Bağlantı / Eşleştirme / Depolama yoktur (spec K13/K14).
AYAR_BOLUMLERI = ["baglanti", "ag", "eslestirme", "kalibrasyon", "kal-gecmis", "depolama", "dil-gorunum", "gelismis"]
# Tembel ekran bileşenlerinin kök sınıfı (ekran/*.js SABLON) — derlenmiş render'ları gerçekten çizdi mi.
GORUNUM_KOKU = {"kayitlar": ".kl", "karsilastir": ".kr"}


def derle(hedef: Path) -> None:
    komut = f'npx vite build --outDir "{hedef}" --emptyOutDir --logLevel warn'
    r = subprocess.run(komut, cwd=MOBIL, shell=True, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, env={**os.environ, "NODE_ENV": "production"})
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("vite build BASARISIZ")


def sunucu_kur(dizin: Path, csp: str):
    istekler: list[tuple[str, int]] = []

    class Isleyici(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript",
                          ".mjs": "text/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8"}

        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(dizin), **k)

        def end_headers(self):
            self.send_header("Content-Security-Policy", csp)
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_request(self, code="-", size="-"):
            try:
                istekler.append((self.path, int(code)))
            except (TypeError, ValueError):
                istekler.append((self.path, 0))

        def log_message(self, *a):
            pass

    s = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, istekler


class Izleyici(Tarayici):
    """Tarayici + Log alani (CSP ihlali, ağ hatası konsol satırları)."""

    def _olay(self, m: dict) -> None:
        if m.get("method") == "Log.entryAdded":
            e = m["params"]["entry"]
            self.olaylar.append({"tur": "log", "kaynak": e.get("source"), "seviye": e.get("level"),
                                 "metin": e.get("text", ""), "url": e.get("url", "")})
            return
        super()._olay(m)


CSP_KAYDI = """
window.__cspIhlal = [];
document.addEventListener('securitypolicyviolation', function (e) {
  window.__cspIhlal.push(e.violatedDirective + ' ' + e.blockedURI + ' ' + (e.sourceFile || '') + ':' + e.lineNumber);
});
"""

GORUNUR = "const gorunur = (e) => !!e && e.getClientRects().length > 0;"


def ifade(govde: str) -> str:
    """Runtime.evaluate kuresel kapsamda kosar: const'lar kalici olur. Her ifade kendi islevinde."""
    return "(() => {" + GORUNUR + govde + "})()"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", help="var olan paket dizini (verilmezse geçici dizine derlenir)")
    ap.add_argument("--goruntu", help="her görünümün ekran görüntüsü bu dizine")
    a = ap.parse_args()

    gecici = None
    if a.dist:
        dist = Path(a.dist).resolve()
    else:
        gecici = Path(tempfile.mkdtemp(prefix="olcum-mobil-dist-"))
        print("derleniyor ->", gecici)
        derle(gecici)
        dist = gecici
    html = (dist / "index.html").read_text(encoding="utf-8")
    m = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
    if not m:
        print("KALDI: dist/index.html'de CSP yok")
        return 1
    csp = m.group(1)
    paket_dosyalari = {"/" + p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file()}

    sonuc: list[tuple[bool, str, str]] = []

    def iddia(ad: str, kosul: bool, ayrinti: str = "") -> None:
        sonuc.append((bool(kosul), ad, ayrinti))
        print(("  ok  " if kosul else "  XX  ") + ad + (f"  [{ayrinti}]" if ayrinti else ""))

    sunucu, istekler = sunucu_kur(dist, csp)
    taban = f"http://127.0.0.1:{sunucu.server_address[1]}/"
    try:
        with Izleyici(auth_iptal=False) as t:
            t.cagir("Log.enable")
            t.cagir("Page.addScriptToEvaluateOnNewDocument", {"source": CSP_KAYDI})
            t.ekran(390, 844)                                   # telefon (çekmece düzeni)
            t.git(taban + "#/canli")
            for _ in range(60):
                t.bekle(0.25)
                if t.js("!!document.getElementById('uyg') && !document.getElementById('uyg').hasAttribute('v-cloak')"):
                    break
            iddia("#uyg boyandı (v-cloak düştü, Vue mount etti)",
                  t.js("!document.getElementById('uyg').hasAttribute('v-cloak') && document.querySelectorAll('#uyg .kabuk').length === 1"))
            iddia("Vue npm runtime: globalThis.Vue var, derleyici YOK",
                  t.js("typeof Vue === 'object' && typeof Vue.createApp === 'function'"
                       " && (typeof Vue.compile !== 'function' || Vue.compile('<p>x</p>') === undefined)"))
            iddia("#acilmadi kutusu gizli", t.js("document.getElementById('acilmadi').hidden === true"))
            iddia("tema ön boyaması uygulandı (data-tema)",
                  t.js("['koyu','acik','onpanel'].includes(document.documentElement.getAttribute('data-tema'))"))

            # DOM şablonu tuzağı: tarayıcı ayrıştırması == ham metin (render kodu bayt bayt)
            ham = (KOK / "arayuz3" / "index.html").read_text(encoding="utf-8")
            ic = t.js("new DOMParser().parseFromString(" + json.dumps(ham) + ", 'text/html').getElementById('uyg').innerHTML")
            with tempfile.NamedTemporaryFile("wb", suffix=".html", delete=False) as f:
                f.write(ic.encode("utf-8"))
                ic_yol = f.name
            try:
                r = subprocess.run(["node", str(BURASI / "sablon_karsilastir.mjs"), ic_yol], cwd=MOBIL,
                                   capture_output=True, text=True, encoding="utf-8", timeout=120)
            finally:
                os.unlink(ic_yol)
            try:
                k = json.loads(r.stdout.strip().splitlines()[-1])
            except Exception:
                k = {"ayni": False, "hata": (r.stderr or r.stdout)[-500:]}
            iddia("tarayıcının ayrıştırdığı #uyg (PC) ile ham metin (telefon) AYNI render kodu", k.get("ayni") is True,
                  json.dumps(k, ensure_ascii=False)[:600])

            # Görünümler
            for g in GORUNUMLER:
                t.js(f"location.hash = '#/{g}'")
                t.bekle(1.2)
                d = t.js(ifade(f"""
                  const ana = [...document.querySelectorAll('#uyg main.gorunum')].filter(gorunur);
                  const kok = {json.dumps(GORUNUM_KOKU.get(g, ''))};
                  return ({{ gorunen: ana.length, metin: ana.length ? ana[0].innerText.trim().length : 0,
                     oge: ana.length ? ana[0].querySelectorAll('*').length : 0,
                     kok: kok ? gorunur(ana[0] && ana[0].querySelector(kok)) : true,
                     etkin: (document.querySelector('.gorunum-sekme.etkin') || {{}}).getAttribute
                            ? document.querySelector('.gorunum-sekme.etkin').getAttribute('href') : null }});"""))
                iddia(f"#/{g}: tek görünüm görünür, içerik çizildi"
                      + (f" ({GORUNUM_KOKU[g]} bileşeni)" if g in GORUNUM_KOKU else ""),
                      d["gorunen"] == 1 and d["metin"] > 10 and d["oge"] > 5 and d["kok"], json.dumps(d))
                if a.goruntu:
                    Path(a.goruntu).mkdir(parents=True, exist_ok=True)
                    t.goruntu(str(Path(a.goruntu) / f"acilis-{g}.png"))

            # Ayarlar bölümleri (tembel modüller dahil: kal-gecmis/depolama/gelismis -> ayarlar.js, eslestirme,
            # telefon -> ortamın "Bu telefon" bileşeni). Liste panelin menüsünden.
            telefon = bool(t.js("!!globalThis.__olcumOrtam"))
            bolumler = t.js("[...document.querySelectorAll('[data-ay-git]')].map((a) => a.getAttribute('data-ay-git'))") or []
            print(f"  ..  kip: {'TELEFON (ortam kurulu)' if telefon else 'ortamsız'}; Ayarlar bölümleri: {bolumler}")
            if telefon:
                iddia("telefon kipi: Ayarlar 'telefon' ile başlar, Bağlantı/Eşleştirme/Depolama yok",
                      bolumler[:1] == ["telefon"] and not {"baglanti", "eslestirme", "depolama"} & set(bolumler),
                      json.dumps(bolumler))
            else:
                iddia("ortamsız: Ayarlar bölümleri app.js AYAR_BOLUMLERI ile aynı", bolumler == AYAR_BOLUMLERI, json.dumps(bolumler))
            for b in bolumler:
                t.js(f"location.hash = '#/ayar/{b}'")
                t.bekle(1.5 if b == "telefon" else 1.0)
                d = t.js(ifade(f"""
                  const ic = [...document.querySelectorAll('#uyg .ay-icerik')].filter(gorunur);
                  const s = [...document.querySelectorAll('[data-ay-bolum="{b}"]')];
                  const etkin = document.querySelector('[data-ay-git="{b}"].etkin');
                  return ({{ etkin: !!etkin, icerik: ic.length ? ic[0].innerText.trim().length : 0,
                     isaretli: s.length, gorunur: s.filter(gorunur).length,
                     metin: s.filter(gorunur).map((x) => x.innerText.trim().length).reduce((a, b) => a + b, 0) }});"""))
                # `data-ay-bolum` işaretli bölüm görünür ve dolu olmalı; işaretsiz bölüm (ortamın bileşeni)
                # için içerik alanı dolu olmalı.
                ok = d["etkin"] and (d["gorunur"] >= 1 and d["metin"] > 5 if d["isaretli"] else d["icerik"] > 20)
                iddia(f"#/ayar/{b}: bölüm görünür ve çizildi", ok, json.dumps(d))
                if a.goruntu and b == "telefon":
                    t.goruntu(str(Path(a.goruntu) / "acilis-ayar-telefon.png"))

            # Bağlantı penceresi (ekran/baglanti.js — teleport'lu tembel bileşen)
            t.js("location.hash = '#/canli'")
            t.bekle(0.8)
            t.js(ifade("[...document.querySelectorAll('#uyg main.gorunum button')].filter(gorunur)"
                 ".find((b) => b.textContent.includes('ⓘ')).click();"))
            t.bekle(1.5)
            d = t.js(ifade("return ({ n: [...document.querySelectorAll('.baglanti-bilgi')].filter(gorunur).length,"
                     " metin: (document.querySelector('.baglanti-bilgi') || {innerText: ''}).innerText.trim().length });"))
            iddia("Bağlantı penceresi (ⓘ) açıldı ve çizildi", d["n"] == 1 and d["metin"] > 10, json.dumps(d))
            if a.goruntu:
                t.goruntu(str(Path(a.goruntu) / "acilis-baglanti.png"))
            t.js("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))")
            t.bekle(0.5)

            # Hatalar
            csp_ihlal = t.js("window.__cspIhlal") or []
            # `webrtc` yonergesini Chromium tanimiyor (konsola "Unrecognized ... 'webrtc'" yazar); CSP'de bilerek
            # duruyor (test/gizlilik.test.js; WebRTC'yi asil src/cekirdek/rtc_kapat.js kapatir) -> BILGI, ihlal degil.
            log_csp = [o["metin"] for o in t.olaylar if o["tur"] == "log"
                       and ("Content Security Policy" in o["metin"] or "Content-Security-Policy" in o["metin"]
                            or o.get("kaynak") == "security")]
            tanimsiz = [x for x in log_csp if "Unrecognized Content-Security-Policy directive 'webrtc'" in x]
            log_csp = [x for x in log_csp if x not in tanimsiz]
            iddia("CSP ihlali YOK (securitypolicyviolation olayi + konsol)", not csp_ihlal and not log_csp,
                  "; ".join(csp_ihlal + log_csp)[:600])
            if tanimsiz:
                print(f"  ..  BİLGİ: tarayıcı 'webrtc' CSP yönergesini tanımıyor ({len(tanimsiz)} satır; bilinen, rtc_kapat.js kapatır)")
            istisna = [o["metin"] for o in t.olaylar if o["tur"] == "hata"]
            iddia("yakalanmamış istisna YOK", not istisna, " | ".join(istisna)[:600])
            konsol_hata = [o["metin"] for o in t.olaylar if o["tur"] == "console" and o.get("seviye") in ("error", "assert")]
            iddia("console.error YOK", not konsol_hata, " | ".join(konsol_hata)[:600])
            vue = [o["metin"] for o in t.olaylar if "[Vue warn]" in o.get("metin", "")
                   or "runtime compilation" in o.get("metin", "").lower()]
            iddia("Vue uyarısı / runtime derleme uyarısı YOK", not vue, " | ".join(vue)[:600])
            kirik = [f"{p} {c}" for p, c in istekler if p.split("?")[0] in paket_dosyalari and c >= 400]
            eksik = [f"{p} {c}" for p, c in istekler if c == 404 and re.search(r"\.(js|css|mjs)(\?|$)", p)]
            iddia("paketin kendi dosyaları hatasız indi (404 yok)", not kirik and not eksik, " ".join(kirik + eksik))
            yabanci = sorted({p for p, c in istekler if p.split("?")[0] not in paket_dosyalari and p not in ("/", "/index.html")})
            print(f"  ..  BİLGİ: paket dışı istekler (ortamsızken panelin taşıyıcı denemeleri): {yabanci[:12]}"
                  + (f" (+{len(yabanci) - 12})" if len(yabanci) > 12 else ""))
            ag_log = [o["metin"][:120] for o in t.olaylar if o["tur"] == "log" and o.get("kaynak") == "network"]
            if ag_log:
                print(f"  ..  BİLGİ: ağ günlüğü {len(ag_log)} satır, ilki: {ag_log[0]}")
    finally:
        sunucu.shutdown()
        if gecici:
            shutil.rmtree(gecici, ignore_errors=True)

    kalan = [s for s in sonuc if not s[0]]
    print()
    print(f"{'GECTI' if not kalan else 'KALDI'}: {len(sonuc) - len(kalan)}/{len(sonuc)} iddia")
    return 0 if not kalan else 1


if __name__ == "__main__":
    sys.exit(main())
