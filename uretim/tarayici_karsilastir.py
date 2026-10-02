# -*- coding: utf-8 -*-
"""3G — KARSILASTIRMA TARAYICIDA (T3G): sahte karta karsi uctan uca.

    python tarayici_karsilastir.py                    # sessiz, 0/1 doner
    python tarayici_karsilastir.py --goruntu DIZIN    # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B7 (`test_arayuz3.js` bolum 29) saf mantigi node'da sinar; gercek
   IndexedDB'den gelen kopyayi, Kayitlar listesindeki secimden adrese giden yolu, tuvalin her
   kayit icin GERCEKTEN cizildigini, kip degisince eksenin degistigini, gercek fare olaylariyla
   iki imleci, indirilen CSV baytlarini, geri tusunu, uc gorunumu ve telefon genisligini
   sinayamaz.

Sahte kart: `tarayici_kayitlar.Kart` (B72.E'nin `/kayit/veri` sahtesi + dizin + `/akis` +
`/komut`). Sayfa `http://olcum.test:<port>/` (Edge `--host-resolver-rules`): kartin sayfasi gibi
localhost DISI — panel akis kipine gecer, Kayitlar ayni kokenden kendiliginden esitler (C1).

Oturumlar (`kopru/kayit_bicim.py` paketleyicileri): A olcum (saatli, 200 ms), B pil (kesintisiz),
C pil (BOSLUKLU — mAh ekseninde disarida), E olcum SAATSIZ + saatsiz DEVAM (K1 "tahmini";
saat ekseninde disarida), D osiloskop gunlugu (secilemez). Esitlemeden sonra kartta beliren K
(yalniz kartta: secilemez, KR5). Beklenen degerler BAGIMSIZ Python hesabindan
(`ortak_vektor_disari.nokta_satirlari` + bu dosyadaki K1 / yamuk / en yakin ornek / CSV) —
sayfanin kendi hesabiyla karsilastirilsaydi test kendini dogrulardi.
"""
from __future__ import annotations

import base64
import json
import math
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kayit_bicim as KB                                    # noqa: E402
import ortak_vektor_disari as OV                            # noqa: E402
import tarayici_kayitlar as TK                              # noqa: E402
from tarayici import Tarayici, bos_port                     # noqa: E402
from tarayici_tema import css_takimlari, rgb, TEMALAR       # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
AD = "olcum.test"
BEKLENEN_404 = ("/durum", "/pil", "/favicon.ico")
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


# ── oturumlar ────────────────────────────────────────────────────────────
def akis_kur() -> tuple[TK.Akis, dict]:
    a = TK.Akis(10)
    no = {}
    # A: olcum 200 ms, saatli, 60 s
    no["A"] = a.basla(1, 200, 1790000000, 5000, 3)
    a.noktalar(no["A"], 0, [TK.nokta(5000 + 200 * (k + 1), 12000 + 2500 * math.sin(k / 23.0) + 7 * (k % 5),
                                     2000 + 600 * math.cos(k / 31.0), 0.4 + 0.1 * math.sin(k / 17.0)) for k in range(300)])
    a.not_(no["A"], KB.KNT_AD, 0, "Akü şarj")
    a.bitir(no["A"], 300, 1)
    # B: pil 1000 ms, kesintisiz, 50 s
    no["B"] = a.basla(2, 1000, 1790001000, 90000, 3)
    a.noktalar(no["B"], 0, [TK.nokta(90000 + 1000 * (k + 1), 1900 - 6 * k + 3 * (k % 3), 1200 - 4 * k, 0.9 - 0.004 * k)
                            for k in range(50)])
    a.not_(no["B"], KB.KNT_AD, 0, "Li-ion #2")
    a.bitir(no["B"], 50, 4)
    # C: pil 1000 ms, 22. noktadan sonra 3 s BOSLUK (> 2.5 x 1000) — mAh ekseninde disarida
    no["C"] = a.basla(2, 1000, 1790002000, 150000, 3)
    ms_c = [150000 + 1000 * (k + 1) + (2000 if k >= 22 else 0) for k in range(45)]
    a.noktalar(no["C"], 0, [TK.nokta(ms, 1800 - 5 * k, 900 + 2 * (k % 7), 0.8 - 0.003 * k) for k, ms in enumerate(ms_c)])
    a.bitir(no["C"], 45, 4)
    # E: olcum SAATSIZ + saatsiz DEVAM (ikinci parcanin yeri K1 "tahmini")
    no["E"] = a.basla(1, 1000, 0, 7000, 5)
    a.noktalar(no["E"], 0, [TK.nokta(7000 + 1000 * (k + 1), 5500 + 40 * (k % 6), 300 + 10 * (k % 4), 0.27) for k in range(20)])
    a.ekle(KB.T_DEVAM, no["E"], struct.pack("<IIII", 6, 0, 2000, 20))
    a.noktalar(no["E"], 20, [TK.nokta(2000 + 1000 * (k + 1), 6200 - 30 * (k % 5), 350, 0.3) for k in range(15)])
    a.bitir(no["E"], 35, 1)
    # D: osiloskop gunlugu (zaman grafigi yok -> secilemez)
    no["D"] = a.basla(3, 1000, 1790003000, 300000, 3)
    meta = {"t_ms": 300100, "sure_ms": 13, "hz": 10000, "tdiv_us": 1000, "adim": 0.03, "ofset": 1.5,
            "tetik": 32, "esik": 2048, "histerezis": 8, "kip": 0, "tetiklendi": 1, "kenar": 0, "on_yuzde": 25, "onay": 2}
    a.ekle(KB.T_SKOP, no["D"], KB.skop_paketle({"no": 1, "ilk": 0, "toplam": 64, "parca": 0, "meta": meta,
                                                 "kodlar": [2048 + 20 * k for k in range(64)]}))
    a.bitir(no["D"], 0, 1)
    return a, no


# ── bagimsiz Python basvurusu ────────────────────────────────────────────
class Seri:
    """Bir kaydin x/y dizileri + okuma icin i, w, acilis (BAGIMSIZ: nokta_satirlari + K1)."""

    def __init__(self, o: KB.Oturum, kanal: str = "v"):
        r = OV.nokta_satirlari(o)
        self.r = r
        self.bosluk = o.basla.hiz_ms * 2.5
        self.acilis = [x["acilis"] for x in r]
        # K1: acilis 0 baslangica gore; bilinmeyen ofsetli parca oncekinin ARDINA (3 x bosluk)
        self.t = []
        once_son = None
        ofset = {}
        for s in sorted(set(self.acilis)):
            rel = [x["rel"] for x in r if x["acilis"] == s]
            g = [x["gecen"] for x in r if x["acilis"] == s]
            if g[0] is not None and (once_son is None or g[0] >= once_son):
                ofset[s] = g[0] - rel[0]
            else:
                ofset[s] = (0 if once_son is None else once_son + 3 * self.bosluk) - min(rel)
            once_son = ofset[s] + max(rel)
        self.t = [ofset[x["acilis"]] + x["rel"] for x in r]
        self.unix = [x["unix"] for x in r]
        self.v = [x["v"][0] for x in r]
        self.i = [x["a"][0] for x in r]
        self.w = [x["w"][0] for x in r]

    def y(self, kanal: str) -> list:
        return {"V": self.v, "I": self.i, "W": self.w}[kanal]

    def mah_x(self) -> list | None:
        """PU9: yamuk, ayni islem sirasi: top += (i0 + i1) / 2 * dt / 3600; bosluk / eksi -> None."""
        x, top = [], 0.0
        for k in range(len(self.t)):
            if math.isnan(self.i[k]) or self.i[k] < 0:
                return None
            if k:
                dt = self.t[k] - self.t[k - 1]
                if dt > self.bosluk:
                    return None
                top += (self.i[k - 1] + self.i[k]) / 2 * dt / 3600
            x.append(top)
        return x


def okuma_py(s: Seri, x: list, kanal: str, ta: float, tb: float, enerji: bool) -> dict:
    """Kayit basina okuma: aralik disi imlec -> None; en yakin NaN'siz ornek; ort; K3 yamuk (acilis basina)."""
    y = s.y(kanal)
    nan = math.isnan
    ic = lambda q: q is not None and x[0] <= q <= x[-1]  # noqa: E731

    def yakin(q):
        en = None
        for k in range(len(x)):
            if nan(y[k]):
                continue
            if en is None or abs(x[k] - q) < abs(x[en] - q):
                en = k
        return y[en]

    sonuc = {"a": None, "b": None, "fark": None, "ort": None, "mah": None, "wh": None}
    if ic(ta):
        sonuc["a"] = yakin(ta)
    if ic(tb):
        sonuc["b"] = yakin(tb)
    if not (ic(ta) and ic(tb)):
        return sonuc
    sonuc["fark"] = sonuc["b"] - sonuc["a"]
    aralik = [k for k in range(len(x)) if ta <= x[k] <= tb]
    deg = [y[k] for k in aralik if not nan(y[k])]
    sonuc["ort"] = math.fsum(deg) / len(deg)
    if enerji:
        mah, wh = [], []
        for gecerli, deger, liste in ((lambda k: not nan(s.v[k]) and not nan(s.i[k]), lambda k: s.i[k], mah),
                                      (lambda k: not nan(s.w[k]), lambda k: s.w[k], wh)):
            onceki = None
            for k in aralik:
                if not gecerli(k):
                    continue
                if onceki is not None and s.acilis[k] == s.acilis[onceki] and x[k] - x[onceki] <= s.bosluk:
                    liste.append((deger(onceki) + deger(k)) * (x[k] - x[onceki]) / 2)
                onceki = k
        sonuc["mah"] = math.fsum(mah) / 3600.0
        sonuc["wh"] = math.fsum(wh) / 3_600_000.0
    return sonuc


def csv_py(girdiler: list, kip: str, kanal: str, dil: str) -> bytes:
    """KR7 birlesik CSV'nin bagimsiz karsiligi. girdiler [(no, x, y, ayrinti)]."""
    ayrac, ondalik = (";", ",") if dil == "tr" else (",", ".")
    onek = "kayit" if dil == "tr" else "rec"
    xad = {"baslangic": "gecen_ms" if dil == "tr" else "elapsed_ms", "saat": "unix_s",
           "mah": "yuk_mAh" if dil == "tr" else "charge_mAh"}[kip]
    kad = {"V": ("v_ort_V", "v_avg_V"), "I": ("i_ort_A", "i_avg_A"), "W": ("w_ort_W", "p_avg_W")}[kanal][0 if dil == "tr" else 1]
    say = lambda v, b: OV.sayi_yaz(v, b).replace(".", ondalik)  # noqa: E731
    xyaz = {"baslangic": lambda v: say(v, 3), "saat": lambda v: say(v / 1000, 3), "mah": lambda v: say(v, 6)}[kip]
    bas = []
    for no, _x, _y in girdiler:
        bas += [f"{onek}{no}_{xad}", f"{onek}{no}_{kad}"]
    satir = ["﻿" + ayrac.join(bas) + "\r\n"]
    for j in range(max(len(g[1]) for g in girdiler)):
        h = []
        for _no, x, y in girdiler:
            h += [xyaz(x[j]), say(y[j], 6)] if j < len(x) else ["", ""]
        satir.append(ayrac.join(h) + "\r\n")
    return "".join(satir).encode("utf-8")


def renk_kar(a: str, b: str | None, oran: float) -> tuple:
    """ekran/karsilastir.js renkKar'in bagimsiz karsiligi (Math.round = floor(x + 0.5))."""
    x = rgb(a)
    if not b or not oran:
        return x
    y = rgb(b)
    return tuple(math.floor(x[i] * (1 - oran) + y[i] * oran + 0.5) for i in range(3))


TARIF = [("volt", None, 0), ("amper", None, 0), ("watt", None, 0),
         ("volt", "yazi", 0.5), ("amper", "yazi", 0.35), ("vurgu", "kart", 0.35)]


def kr_renk(takim: dict, k: int) -> tuple:
    b, kutup, oran = TARIF[k]
    return renk_kar(takim["--" + b], takim["--" + kutup] if kutup else None, oran)


# ── tarayici ─────────────────────────────────────────────────────────────
class KrTarayici(Tarayici):
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


def bekle_js(t, ifade: str, sure: float = 12.0):
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


PIKSEL_JS = """(() => {
  const c = document.querySelector('canvas.kr-grafik');
  if (!c || !c.width) return null;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const h = %s; const s = h.map(() => 0);
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 250) continue;
    for (let j = 0; j < h.length; j++) if (Math.abs(d[i] - h[j][0]) <= 6 && Math.abs(d[i + 1] - h[j][1]) <= 6
      && Math.abs(d[i + 2] - h[j][2]) <= 6) s[j]++; }
  return s; })()"""

LEJANT_JS = ("[...document.querySelectorAll('[data-kr-lejant]')].map(l => ({k: l.dataset.krLejant, d: l.dataset.durum,"
             " m: l.textContent.replace(/\\s+/g, ' ').trim()}))")


def tasma(t) -> int:
    return t.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def merkez(t, secici: str) -> dict | None:
    return t.js("(() => { const e = document.querySelector(%s); if (!e) return null; e.scrollIntoView({block: 'center'});"
                " const b = e.getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; })()"
                % json.dumps(secici))


def tikla_cdp(t, secici: str) -> bool:
    m = merkez(t, secici)
    if not m:
        return False
    t.bekle(0.15)
    m = merkez(t, secici)
    TK.fare(t, "mouseMoved", m["x"], m["y"])
    TK.fare(t, "mousePressed", m["x"], m["y"], 1)
    TK.fare(t, "mouseReleased", m["x"], m["y"], 1)
    return True


def sec_degistir(t, secici: str, deger: str) -> None:
    t.js("(() => { const s = document.querySelector(%s); s.value = %s; s.dispatchEvent(new Event('change')); })()"
         % (json.dumps(secici), json.dumps(deger)))


def tema_sec(t, ad: str, geri: str) -> None:
    yazi = ["Koyu", "Açık", "Ön panel"][TEMALAR.index(ad)]
    t.js("[...document.querySelectorAll('button')].find(x => x.textContent.trim() === %s).click()" % json.dumps(yazi))
    bekle_js(t, f"document.documentElement.dataset.tema === {json.dumps(ad)}", 5)
    if t.js("location.hash") != geri:
        t.js(f"location.hash = {json.dumps(geri)}")
    t.bekle(0.6)


def pencere(t) -> dict:
    p = t.js("(document.querySelector('.kr .kg-tuval') || {dataset: {}}).dataset.pencere")
    return json.loads(p) if p else {}


def okuma(t) -> dict:
    o = t.js("(document.querySelector('.kr-okuma') || {dataset: {}}).dataset.okuma")
    return json.loads(o) if o else {}


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


def yakin_mi(a, b, tol=1e-9) -> bool:
    if b is None or (isinstance(b, float) and math.isnan(b)):
        return a is None
    return a is not None and abs(a - b) <= tol * max(1.0, abs(b))


# ── ana akis ─────────────────────────────────────────────────────────────
def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    takim = css_takimlari()
    akis, no = akis_kur()
    kart = TK.Kart(list(akis.kayitlar))
    s = TK.sunucu_kur(kart)
    taban = f"http://{AD}:{s.server_address[1]}"
    indirme = Path(tempfile.mkdtemp(prefix="olcum-indir-"))
    resimler = []
    profil = None
    ot = KB.oturumlari_kur(KB.akis_coz(b"".join(akis.kayitlar)))
    S = {ad: Seri(ot[no[ad]]) for ad in ("A", "B", "C", "E")}
    print("=" * 78)
    print("  3G  KARSILASTIRMA — TARAYICIDA, SAHTE KARTA KARSI (T3G)")
    print("=" * 78)
    print(f"     sahte kart: {taban}  ({len(kart.kayitlar)} kayit, kimlik {kart.kimlik}), oturumlar {no}\n")

    def resim(ad: str) -> None:
        if not goruntu:
            return
        y = goruntu / f"{ad}.png"
        m = t.cagir("Page.getLayoutMetrics")["cssContentSize"]
        r = t.cagir("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                               "clip": {"x": 0, "y": 0, "width": m["width"],
                                                        "height": min(m["height"], 5000), "scale": 1}})
        y.write_bytes(base64.b64decode(r["data"]))
        resimler.append(y)

    try:
        with KrTarayici(auth_iptal=False, port=bos_port(), ek_arg=[f"--host-resolver-rules=MAP {AD} 127.0.0.1"]) as t:
            profil = t.profil
            t.cagir("Log.enable")
            t.tema("dark")
            try:
                t.cagir("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(indirme),
                                                        "eventsEnabled": False})
            except RuntimeError:
                t.cagir("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(indirme)})

            # ── 1. Kayitlar: otomatik esitleme, secim kutulari ───────────────
            t.git(taban + "/#/kayitlar")
            bekle_js(t, "document.querySelectorAll('.kl-satir').length >= 5 && [...document.querySelectorAll('.kl-satir')]"
                        ".every(a => a.dataset.nerede === 'ikisi')", 60)
            k = kart.kimlik
            kutu = lambda ad: f"[data-kl-sec='{k}:{no[ad]}']"  # noqa: E731
            durum = t.js("Object.fromEntries([...document.querySelectorAll('[data-kl-sec]')].map(i => [i.dataset.klSec,"
                         " {d: i.disabled, e: i.getAttribute('aria-label'), t: i.closest('label').title}]))") or {}
            dsk = durum.get(f"{k}:{no['D']}", {})
            ok("[!] KR1: Kayitlar satirlarinda secim kutusu; osiloskop gunlugunun kutusu KAPALI ve sebebi etiketinde",
               len(durum) == 5 and dsk.get("d") is True and "osiloskop" in (dsk.get("e") or "")
               and "osiloskop" in (dsk.get("t") or "") and not any(v["d"] for kk, v in durum.items() if kk != f"{k}:{no['D']}"),
               json.dumps(dsk, ensure_ascii=False))
            # KR5: esitlemeden sonra kartta beliren oturum yalniz kartta -> secilemez
            yeni = TK.Akis(max(struct.unpack_from("<I", h, 4)[0] for h in akis.kayitlar))
            no["K"] = yeni.basla(1, 1000, 1790006000, 500000, 3)
            yeni.noktalar(no["K"], 0, [TK.nokta(500000 + 1000 * (j + 1), 4000, 500, 0.3) for j in range(10)])
            yeni.bitir(no["K"], 10, 1)
            with kart.kilit:
                kart.kayitlar = list(kart.kayitlar) + yeni.kayitlar
            # eslesme (Yenile) — esitleme kendiliginden DEGIL: yalniz liste tazelenir
            t.js("[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Yenile').click()")
            kk = bekle_js(t, f"(() => {{ const i = document.querySelector(\"[data-kl-sec='{k}:{no['K']}']\");"
                             " return i && {d: i.disabled, e: i.getAttribute('aria-label'),"
                             " n: i.closest('.kl-satir-sarmal').querySelector('.kl-satir').dataset.nerede}; })()", 10) or {}
            ok("[!] KR5: yalniz kartta olan (esitlenmemis) oturumun kutusu KAPALI, etiketi 'önce eşitleyin' diyor",
               kk.get("n") == "kart" and kk.get("d") is True and "önce eşitleyin" in (kk.get("e") or ""),
               json.dumps(kk, ensure_ascii=False))
            # KR6: secim yokken serideki Karsilastirma bos durumu gosterir ve Kayitlar'a yonlendirir
            tikla_cdp(t, "#serit .gorunum-sekme[href='#/karsilastir']")
            bos = bekle_js(t, "location.hash === '#/karsilastir' && !!document.querySelector('[data-kr=bos]')"
                              " && getComputedStyle(document.querySelector('[data-kr=bos]')).display !== 'none'"
                              " && ({m: document.querySelector('[data-kr=bos]').textContent,"
                              " h: document.querySelector('[data-kr=kayitlara-git]').getAttribute('href')})", 10) or {}
            ok("[!] KR6: seritte Karsilastirma; secim yokken bos durum Kayitlar'a yonlendiriyor (olu ekran yok)",
               "Kayıtlar listesinde" in (bos.get("m") or "") and bos.get("h") == "#/kayitlar",
               json.dumps(bos, ensure_ascii=False))
            resim("0-bos")
            t.js("history.back()")
            bekle_js(t, "location.hash === '#/kayitlar' && document.querySelectorAll('.kl-satir').length >= 6", 8)
            # Kayitlar yeniden gorunur olunca kendiliginden esitler (C1): bitmesini bekle, secim sonra
            bekle_js(t, f"(() => {{ const i = document.querySelector(\"[data-kl-sec='{k}:{no['K']}']\");"
                        " const e = document.querySelector('.kl-esitle');"
                        " return i && !i.disabled && e && !e.disabled; })()", 30)

            # ── 2. secim (gercek fare) -> Karsilastir -> adres ──────────────
            for ad in ("A", "B", "C", "E"):
                tikla_cdp(t, kutu(ad))
                t.bekle(0.15)
            bilgi = t.js("document.querySelector('.kl-secim-bilgi').textContent.trim()")
            href = t.js("(document.querySelector('a[data-kl-karsilastir]') || {}).getAttribute"
                        " && document.querySelector('a[data-kl-karsilastir]').getAttribute('href')")
            beklenen = f"#/karsilastir/{no['A']}@{k},{no['B']}@{k},{no['C']}@{k},{no['E']}@{k}"
            ok("[!] KR1: dort kutu GERCEK fareyle secildi; 'Karşılaştır' baglantisi secim sirasiyla ve kimlikle",
               href == beklenen and bilgi.startswith("4 kayıt seçildi"), f"{href} · {bilgi}")
            resim("1-liste-secim")
            tikla_cdp(t, "a[data-kl-karsilastir]")
            bekle_js(t, f"location.hash === {json.dumps(beklenen)} && {UYG}.gorunum === 'karsilastir'"
                        " && document.querySelectorAll('[data-kr-lejant]').length === 4", 15)
            pen = bekle_js(t, "(() => { const p = document.querySelector('.kr .kg-tuval'); return p && p.dataset.pencere"
                              " && JSON.parse(p.dataset.pencere).veriT1 > 0 && JSON.parse(p.dataset.pencere); })()", 10) or {}
            lj = t.js(LEJANT_JS) or []
            gecmis1 = t.js("history.length")
            ok("[!] KR1: 'Karşılaştır' adresi acti, dort kayit lejantta, hepsi cizili (baslangic)",
               t.js("location.hash") == beklenen
               and [x["d"] for x in lj] == ["ici"] * 4 and "Akü şarj #" in lj[0]["m"] and "Li-ion #2" in lj[1]["m"],
               " | ".join(x["m"] for x in lj))
            ok("[!] KR3: saatsiz yeniden baslamali kayit (E) 'baslangictan beri'de cizili ve 'tahmini' diyor",
               "tahmini" in lj[3]["m"] and "tahmini" not in lj[0]["m"], lj[3]["m"])
            beklenen_t1 = max(S[a].t[-1] for a in S)
            ok("[!] KR3 baslangic: x ekseni her kaydin kendi baslangicindan (K1; BAGIMSIZ hesap) — veri araligi [min ilk, max son]",
               pen.get("kip") == "baslangic" and pen.get("veriT0") == min(S[a].t[0] for a in S) and pen.get("veriT1") == beklenen_t1,
               f"{pen.get('veriT0')}…{pen.get('veriT1')} ~ {beklenen_t1}")
            koyu = takim["koyu"]
            renkler = [list(kr_renk(koyu, j)) for j in range(4)]
            px = None
            t0 = time.monotonic()
            while time.monotonic() - t0 < 8:
                px = t.js(PIKSEL_JS % json.dumps(renkler))
                if px and all(v > 25 for v in px):
                    break
                t.bekle(0.15)
            ok("[!] KR2: tuvalde HER kayit kendi renginde cizili (kr0..kr3 pikselleri, renkler tema belirteclerinden bagimsiz hesap)",
               bool(px) and all(v > 25 for v in px), f"{px} · {renkler}")
            lj_renk = t.js("[...document.querySelectorAll('[data-kr-lejant] line')].map(l => [l.getAttribute('stroke'),"
                           " l.getAttribute('stroke-dasharray')])")
            ok("KR2: lejant ornegi tuvaldeki renk + desenle ayni (4. kayit kesik)",
               [x[0] for x in lj_renk] == ["#%02x%02x%02x" % tuple(c) for c in renkler]
               and [x[1] for x in lj_renk] == [None, None, None, "7 4"], str(lj_renk))
            odak = t.js("document.activeElement && document.activeElement.classList.contains('kg-baslik')")
            ok("WIG: ekran acilinca odak basliga (h1 'Karşılaştırma')", odak is True and
               "Karşılaştırma" in t.js("document.querySelector('.kr h1').textContent"))
            resim("2-baslangic-koyu")

            # ── 3. iki imlec: GERCEK CDP fare, kayit basina okuma ──────────
            t.js("document.querySelector('canvas.kr-grafik').scrollIntoView({block: 'center'})")
            t.bekle(0.3)
            r = t.js("(() => { const c = document.querySelector('canvas.kr-grafik'); const b = c.getBoundingClientRect();"
                     " return {x: b.left, y: b.top, w: b.width, h: b.height, sol: c.clientLeft}; })()")
            p = pencere(t)
            for oran in (0.27, 0.71):
                ox = p["alanX"] + oran * p["alanW"]
                TK.cift_tikla(t, r["x"] + r["sol"] + ox, r["y"] + r["h"] / 2)
                t.bekle(0.3)
            bekle_js(t, "(() => { const o = document.querySelector('.kr-okuma').dataset.okuma; return o && JSON.parse(o).tB !== null; })()", 5)
            ok_ = okuma(t)
            p2 = pencere(t)
            ta, tb = ok_.get("tA"), ok_.get("tB")
            px_t = (p["t1"] - p["t0"]) / p["alanW"]
            hedef = [p["t0"] + 0.27 * (p["t1"] - p["t0"]), p["t0"] + 0.71 * (p["t1"] - p["t0"])]
            ok("[!] KR4: gercek fare (CDP cift tik) iki imleci tiklanan piksele koydu",
               ta is not None and tb is not None and abs(ta - hedef[0]) <= 1.5 * px_t and abs(tb - hedef[1]) <= 1.5 * px_t
               and p2.get("imlecA") == ta and p2.get("imlecB") == tb, f"A {ta} ~ {hedef[0]:.0f}, B {tb} ~ {hedef[1]:.0f}")
            kotu = []
            satirlar = {x["anahtar"]: x for x in ok_.get("kayitlar", [])}
            for ad in ("A", "B", "C", "E"):
                py = okuma_py(S[ad], S[ad].t, "V", ta, tb, True)
                js = satirlar.get(f"{k}:{no[ad]}", {})
                for alan in ("a", "b", "fark", "ort", "mah", "wh"):
                    if not yakin_mi(js.get(alan), py[alan]):
                        kotu.append(f"{ad}.{alan}: {js.get(alan)} != {py[alan]}")
            ok("[!] KR4: okuma KAYIT BASINA — A/B, Δ, ort, mAh, Wh her kayit icin BAGIMSIZ Python hesabiyla ayni (1e-9)",
               not kotu and len(satirlar) == 4 and satirlar[f"{k}:{no['A']}"]["mah"] > 0, "; ".join(kotu[:6]) or
               " · ".join(f"{a}: {satirlar[f'{k}:{no[a]}']['a']:.4f}→{(satirlar[f'{k}:{no[a]}']['b'] or float('nan')):.4f}" for a in "ABCE"))
            e_sat = satirlar.get(f"{k}:{no['E']}", {})
            tablo = t.js("Object.fromEntries([...document.querySelectorAll('[data-kr-okuma]')].map(r => [r.dataset.krOkuma,"
                         " [...r.children].map(c => c.textContent.trim())]))") or {}
            ok("[!] KU4: B imleci E'nin (kisa kayit) DISINDA — E'nin B / Δ / ort / mAh hucreleri '—' ve aciklama gorunur",
               e_sat.get("b") is None and e_sat.get("a") is not None and tablo.get(f"{k}:{no['E']}", [None] * 5)[2] == "—"
               and tablo.get(f"{k}:{no['E']}", [None] * 7)[5] == "—" and t.js("!!document.querySelector('[data-kr=imlec-disarida]')"),
               str(tablo.get(f"{k}:{no['E']}")))
            resim("3-imlec")

            # ── 4. CSV (baslangic, TR) ───────────────────────────────────
            def indir(dil: str, ad: str) -> bytes | None:
                yol = indirme / ad
                if yol.exists():
                    yol.unlink()
                t.js(f"document.querySelector('[data-kr-disari=\"{dil}\"]').click()")
                return TK.indir_bekle(indirme, ad)

            g4 = [(no[a], S[a].t, S[a].v) for a in ("A", "B", "C", "E")]
            tr = indir("tr", "karsilastirma-baslangic-v.csv")
            ref = csv_py(g4, "baslangic", "V", "tr")
            ok("[!] KR7: birlesik CSV (Excel-TR) Python basvurusuyla BAYT BAYT ayni — kayit basina x + V, ara deger yok",
               tr is not None and tr == ref, f"{len(tr or b'')} B ~ {len(ref)} B" + ("" if tr == ref else " FARKLI"))

            # ── 5. saat kipi: eksen degisir, saatsiz kayit disarida ────────
            sec_degistir(t, "[data-kr=kip]", "saat")
            bekle_js(t, "(() => { const p = JSON.parse(document.querySelector('.kr .kg-tuval').dataset.pencere || '{}');"
                        " return p.kip === 'saat' && p.veriT0 > 1e12; })()", 8)
            lj = t.js(LEJANT_JS) or []
            ps = pencere(t)
            u0 = min(S[a].unix[0] for a in ("A", "B", "C"))
            u1 = max(S[a].unix[-1] for a in ("A", "B", "C"))
            ok("[!] KR3 saat: x ekseni unix saati — veri araligi saatli kayitlarin [ilk, son] ani (bagimsiz hesap)",
               ps.get("veriT0") == u0 and ps.get("veriT1") == u1, f"{ps.get('veriT0')}…{ps.get('veriT1')} ~ {u0}…{u1}")
            ok("[!] KR3 saat: saatsiz kayit (E) DISARIDA ve lejantta 'dışarıda — saat yok' diyor; digerleri cizili",
               [x["d"] for x in lj] == ["ici", "ici", "ici", "disari"] and "dışarıda" in lj[3]["m"] and "saat yok" in lj[3]["m"],
               lj[3]["m"] if len(lj) > 3 else str(lj))
            pxs = None
            t0 = time.monotonic()
            while time.monotonic() - t0 < 6:
                pxs = t.js(PIKSEL_JS % json.dumps(renkler))
                if pxs and pxs[0] > 25 and pxs[3] == 0:
                    break
                t.bekle(0.15)
            ok("[!] KR3 saat: tuvalde E'nin rengi YOK, A'ninki var (disarida kalan cizilmiyor)", bool(pxs) and pxs[0] > 25 and pxs[3] == 0,
               str(pxs))
            ok("[!] KU2: kip adreste (?x=saat) ve gecmise girdi EKLEMEDEN (replaceState); okuma sifirlandi",
               t.js("location.hash") == beklenen + "?x=saat" and t.js("history.length") == gecmis1
               and not t.js("document.querySelector('.kr-okuma').dataset.okuma"), t.js("location.hash"))
            etiket = t.js("[...document.querySelectorAll('.kr-okuma, .kr')].length && document.querySelector('canvas.kr-grafik').getAttribute('aria-label')")
            ok("KR8: tuvalin erisilebilir adi kanal + eksen kipini soyluyor", "saat" in (etiket or "") and "Gerilim" in (etiket or ""), etiket)
            g3 = [(no[a], S[a].unix, S[a].v) for a in ("A", "B", "C")]
            en = indir("en", "karsilastirma-saat-v-en.csv")
            ref_en = csv_py(g3, "saat", "V", "en")
            ok("[!] KR7: saat kipinde EN CSV — yalniz cizilen kayitlar, x unix_s; Python basvurusuyla BAYT BAYT ayni",
               en is not None and en == ref_en, f"{len(en or b'')} B ~ {len(ref_en)} B" + ("" if en == ref_en else " FARKLI"))
            resim("4-saat")

            # ── 6. mAh kipi: yalniz kesintisiz pil ───────────────────────
            sec_degistir(t, "[data-kr=kip]", "mah")
            bekle_js(t, "(() => { const p = JSON.parse(document.querySelector('.kr .kg-tuval').dataset.pencere || '{}');"
                        " return p.kip === 'mah'; })()", 8)
            lj = t.js(LEJANT_JS) or []
            pm = pencere(t)
            mx = S["B"].mah_x()
            ok("[!] KR3 mAh: yalniz kesintisiz pil (B) cizili; eksen sonu yamuk integralle AYNI (bagimsiz, 1e-9) ve lejantta yaziyor",
               [x["d"] for x in lj] == ["disari", "ici", "disari", "disari"] and mx is not None
               and yakin_mi(pm.get("veriT1"), mx[-1]) and f"{mx[-1]:.3f} mAh" in lj[1]["m"], f"{pm.get('veriT1')} ~ {mx and mx[-1]} · {lj[1]['m']}")
            ok("[!] KR3 mAh: pil DISI kayitlar ve BOSLUKLU pil (C) disarida, sebebiyle (zaman eksenine DUSMEZ)",
               "pil testi değil" in lj[0]["m"] and "boşluk" in lj[2]["m"] and "pil testi değil" in lj[3]["m"]
               and S["C"].mah_x() is None, " | ".join(x["m"] for x in lj))
            mah_b = indir("tr", "karsilastirma-mah-v.csv")
            ref_m = csv_py([(no["B"], mx, S["B"].v)], "mah", "V", "tr")
            ok("[!] KR7: mAh kipinde CSV — x yuk_mAh (6 ondalik); Python basvurusuyla BAYT BAYT ayni",
               mah_b is not None and mah_b == ref_m, f"{len(mah_b or b'')} B")
            resim("5-mah")

            # ── 7. kanal: akim ───────────────────────────────────────────
            sec_degistir(t, "[data-kr=kip]", "baslangic")
            sec_degistir(t, "[data-kr=kanal]", "I")
            bekle_js(t, f"location.hash === {json.dumps(beklenen + '?k=I')}", 5)
            iI = indir("tr", "karsilastirma-baslangic-i.csv")
            ref_i = csv_py([(no[a], S[a].t, S[a].i) for a in ("A", "B", "C", "E")], "baslangic", "I", "tr")
            ok("[!] KR2: tek birim — kanal Akim secilince grafik ve CSV akim (i_ort_A); adres ?k=I",
               iI is not None and iI == ref_i and "i_ort_A" in (iI or b"").decode("utf-8", "replace").split("\r\n")[0],
               (iI or b"")[:80].decode("utf-8", "replace"))
            sec_degistir(t, "[data-kr=kanal]", "V")
            bekle_js(t, f"location.hash === {json.dumps(beklenen)}", 5)

            # ── 8. geri tusu ─────────────────────────────────────────────
            t.js("history.back()")
            geri = bekle_js(t, f"location.hash === '#/kayitlar' && {UYG}.gorunum === 'kayitlar'", 6)
            t.js("history.forward()")
            ileri = bekle_js(t, f"location.hash === {json.dumps(beklenen)} && {UYG}.gorunum === 'karsilastir'"
                                " && document.querySelectorAll('[data-kr-lejant]').length === 4", 8)
            ok("[!] KR1: geri tusu Karsilastirma'dan Kayitlar'a, ileri tusu ayni secime donuyor (kip degisimleri gecmisi kirletmedi)",
               bool(geri) and bool(ileri), t.js("location.hash"))

            # ── 9. uc gorunum ────────────────────────────────────────────
            onceki = "koyu"
            for ad in TEMALAR:
                tema_sec(t, ad, beklenen)
                bekle_js(t, f"{UYG}.gorunum === 'karsilastir'", 4)
                t.js("document.querySelector('canvas.kr-grafik').scrollIntoView({block: 'center'})")
                t.bekle(0.5)
                hedef_r = [list(kr_renk(takim[ad], j)) for j in range(4)]
                eski = list(kr_renk(takim[onceki], 0))
                pd_ = t.js(PIKSEL_JS % json.dumps(hedef_r + [eski]))
                ok(f"[!] {ad}: karsilastirma tuvali dort kaydi YENI gorunumun renkleriyle cizdi"
                   + (f", eski ({onceki}) kr0 rengi yok" if ad != onceki else ""),
                   bool(pd_) and all(v > 25 for v in pd_[:4]) and (ad == onceki or pd_[4] == 0), str(pd_))
                resim(f"6-{ad}")
                onceki = ad

            # ── 10. telefon (390 px) ────────────────────────────────────
            t.ekran(390, 844)
            t.bekle(0.8)
            tas = {}
            for ad in TEMALAR:
                tema_sec(t, ad, beklenen)
                bekle_js(t, f"{UYG}.gorunum === 'karsilastir'", 4)
                t.bekle(0.4)
                tas[ad + "-kr"] = tasma(t)
                t.js("location.hash = '#/kayitlar'")
                bekle_js(t, "document.querySelectorAll('.kl-satir').length > 0", 5)
                t.bekle(0.3)
                tas[ad + "-kl"] = tasma(t)
                t.js(f"location.hash = {json.dumps(beklenen)}")
                bekle_js(t, f"{UYG}.gorunum === 'karsilastir'", 4)
                t.bekle(0.3)
            ii = t.js("(() => { const cw = document.documentElement.clientWidth; const r = (s) => { const e = document.querySelector(s);"
                      " const b = e.getBoundingClientRect(); return {l: b.left, r: b.right}; };"
                      " return {cw, tuval: r('canvas.kr-grafik'), lejant: r('.kr-lejant'), sec: r('[data-kr=kip]')}; })()")
            ok("[!] KR8: 390 px'te uc gorunumde Karsilastirma ve secimli Kayitlar YATAY TASMIYOR; tuval, lejant, secim ekranin icinde",
               all(v <= 0 for v in tas.values()) and all(0 <= ii[x]["l"] and ii[x]["r"] <= ii["cw"] for x in ("tuval", "lejant", "sec")),
               f"{tas} {ii}")
            resim("7-telefon")
            t.cagir("Emulation.clearDeviceMetricsOverride")
            tema_sec(t, "koyu", beklenen)

            # ── 11. konsol ───────────────────────────────────────────────
            h = t.hatalar_tum()
            ok("[!] Butun gezinti boyunca konsol / yukleme hatasi YOK", not h, " | ".join(h[:3]) or "temiz")
    except Kopuk as h:
        ok("[!] Sayfa beklenen akista kaldi (ust uste 3 bekleme zaman asimi yok)", False,
           f"son beklenen: {h} — kalan olcumler ATLANDI")
    finally:
        TK.DUR.set()
        s.shutdown()
        s.server_close()
        shutil.rmtree(indirme, ignore_errors=True)

    if profil and sys.platform == "win32":
        kalan = profil_surecleri(profil)
        ok("[!] Basliksiz Edge SIZMADI (bu testin profiliyle calisan msedge sureci kalmadi)", not kalan, str(kalan))
    for y in resimler:
        print(f"     goruntu: {y}")
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
