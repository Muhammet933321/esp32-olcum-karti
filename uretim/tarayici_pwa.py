# -*- coding: utf-8 -*-
"""T4F — PWA KABUGU GERCEK TARAYICIDA (PC17): service worker, cevrimdisi sayfa, manifest.

    python tarayici_pwa.py          # 0 = yesil, 1 = kirmizi

🔴 NEDEN BU BETIK VAR: B7 sw.js'i node'da sahte `caches`/`fetch` ile sinar — gercek
   tarayicinin service worker kaydi, kapsami, kontrolu, Cache Storage'a GERCEKTE ne
   yazdigi, kopru kapaninca gezinmenin ne gosterdigi ve manifestin Edge'in gozunde
   kurulabilir olup olmadigi ancak tarayicida olculur. T4A'nin duzeni: GERCEK kopru
   (`kopru.sunucu_kur`, yalniz 127.0.0.1) + GERCEK panel, koken `olcum.localhost`.

Olculenler:
  * panel kendi service worker'ini kaydeder, yeniden yuklemede sayfayi DENETLER
  * denetim altindaki yeniden yuklemede kabuk dosyalari yine AGDAN istenir (ag once)
  * Edge'in manifest ayristiricisi hatasiz, kurulabilirlik hatasi yok; ikonlar gercek olcude
  * Cache Storage: tek `olcum-kabuk-<SURUM>`, icinde API yolu / sorgulu adres YOK
  * kopru kapaninca gezinme "Kopru calismiyor" sayfasini verir; kopru donunce sayfa
    kendiliginden panele doner
  * KART kokeni benzetimi (`http://olcum.local`, Edge'de ad 127.0.0.1'e esleniyor —
    guvenli baglam DEGIL) ve gelistirme sunucusu (`localhost`): kayit YOK

⚠ Kart: `KayitKart` (sahte satir akisi) — donanim gerekmez.
⚠ Edge: `tarayici.Tarayici` (profil ve surec sizintisi korumali); sonda bu profilin
  msedge sureci kalmadigi OLCULUR.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                       # noqa: E402
import kopru as kopru_mod                                  # noqa: E402
import pc_ayar                                             # noqa: E402
import gecici                                              # noqa: E402
from tarayici import Tarayici                              # noqa: E402

UYG = "document.querySelector('#uyg') && document.querySelector('#uyg')._vnode.component.proxy"
KART_AD = "olcum.local"                                    # kartin mDNS adi (benzetim)
# PC17'nin "ASLA onbelleklenmez" listesi + koprunun diger uclari
YASAK = ("/akis", "/komut", "/arsiv", "/kayit", "/skop", "/pil", "/kal", "/eslestir",
         "/cihaz", "/saat", "/bildirim", "/kunye.json", "/durum", "/devral", "/sw.js")
gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))


def bekle_js(t, ifade: str, sure: float = 10.0):
    son = time.monotonic() + sure
    deger = None
    while time.monotonic() < son:
        try:
            deger = t.js(ifade)
        except RuntimeError:
            deger = None
        if deger:
            return deger
        t.bekle(0.25)
    return deger


def sizan_edge(profil: str) -> int:
    """Bu profilin komut satirinda gectigi msedge sureci sayisi (Windows)."""
    if sys.platform != "win32":
        return 0
    ad = Path(profil).name
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "@(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                        f"Where-Object {{ $_.CommandLine -like '*{ad}*' }}).Count"],
                       capture_output=True, text=True, timeout=60)
    try:
        return int(r.stdout.strip() or "0")
    except ValueError:
        return -1


def yenile(t) -> None:
    """GERCEK yeniden yukleme. `t.git(ayni adres)` yalniz hash farkliysa belge-ici gezinme
    olur (sayfa yuklenmez); `ignoreCache` service worker'i ATLATIR — ikisi de olcumu bozar."""
    t.cagir("Page.reload", {"ignoreCache": False})
    t.bekle(0.5)


def kopru_kur(k, port: int, gorulen: list):
    sunucu = kopru_mod.sunucu_kur(k, port=port)            # GERCEK baglama: yalniz 127.0.0.1
    taban = sunucu.RequestHandlerClass

    class Kayitli(taban):
        def do_GET(self):
            gorulen.append(self.path.split("?")[0])
            return super().do_GET()

    sunucu.RequestHandlerClass = Kayitli
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return sunucu


def gelistirme_sunucusu():
    """arayuz3/sunucu.py'nin GERCEK isleyicisi, rastgele portta (kart kokeni benzetimi icin)."""
    oz = importlib.util.spec_from_file_location("panel_sunucu", KOK / "arayuz3" / "sunucu.py")
    m = importlib.util.module_from_spec(oz)
    oz.loader.exec_module(m)

    class Sessiz(m.Sunucu):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Sessiz)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def main() -> int:
    print("=" * 78)
    print("  T4F  PWA KABUGU — service worker + cevrimdisi sayfa + manifest (GERCEK Edge)")
    print("=" * 78)
    sw_metin = (KOK / "arayuz3" / "sw.js").read_text(encoding="utf-8")
    m = re.search(r"^const SURUM = '([0-9a-f]{12})';$", sw_metin, re.M)
    surum = m.group(1) if m else "?"
    satirlar = [f"D {12 + i * 0.01:.4f} 0.100000 1.20000 0.0000 0.0000000 {1000 + i * 100} 172 0 0"
                for i in range(4000)]
    kart = kart_baglanti.KayitKart(satirlar, yanitlar={"?": ["A menzil=NORMAL oto=1"]},
                                   gecikme=0.03)
    kart.ac()
    k = kopru_mod.Kopru(kart, gecici.dizin("kopru_t4f_") / "arsiv")
    gorulen: list[str] = []
    sunucu = kopru_kur(k, 0, gorulen)
    port = sunucu.server_address[1]
    threading.Thread(target=k.dongu, daemon=True).start()
    gel = gelistirme_sunucusu()
    gport = gel.server_address[1]
    adres = f"http://{pc_ayar.AD}:{port}"
    print(f"     kopru: {sunucu.server_address} · panel: {adres} · gelistirme: {gport} · SURUM {surum}\n")
    profil = None
    try:
        with Tarayici(auth_iptal=False,
                      ek_arg=[f"--host-resolver-rules=MAP {KART_AD} 127.0.0.1"]) as t:
            profil = t.profil
            # ── 1. kayit + denetim ───────────────────────────────────────
            t.git(adres + "/#/canli")
            bekle_js(t, f"{UYG} && {UYG}.bagli", 15)
            durum = bekle_js(t, f"{UYG}._sw && {UYG}._sw.durum !== 'bekliyor' && {UYG}._sw.durum", 15)
            kapsam = t.js("navigator.serviceWorker.getRegistration('/').then(r => r ? "
                          "[r.scope, (r.active || r.waiting || r.installing).scriptURL] : null)")
            ok("[!] 4F: panel PC koprusunde kendi service worker'ini kaydetti (kapsam /, sw.js)",
               durum == "kayitli" and kapsam and kapsam[0] == adres + "/" and kapsam[1] == adres + "/sw.js",
               f"durum={durum} {kapsam}")
            bekle_js(t, "navigator.serviceWorker.ready.then(r => !!r.active)", 10)
            istek_oncesi = len(gorulen)
            yenile(t)
            bekle_js(t, f"{UYG} && {UYG}.bagli", 15)
            denetci = t.js("navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL")
            ok("[!] 4F: yeniden yuklemede service worker sayfayi DENETLIYOR (controller)",
               denetci == adres + "/sw.js", str(denetci))
            sonra = gorulen[istek_oncesi:]
            agdan = [y for y in ("/app.js", "/style.css", "/vendor/vue.global.prod.js", "/ortak/sozluk.js")
                     if y in sonra]
            ok("[!] 4F: AG ONCE — denetim altindaki yuklemede kabuk dosyalari yine kopruden istendi",
               len(agdan) == 4, " ".join(agdan))

            # ── 2. manifest (Edge'in kendi ayristiricisi) + ikonlar ──────
            try:
                am = t.cagir("Page.getAppManifest")
            except RuntimeError as e:
                am = {"errors": [str(e)]}
            man = {}
            try:
                man = json.loads(am.get("data") or "{}")
            except ValueError:
                pass
            ok("[!] 4F: Edge manifesti hatasiz ayristirdi (id, scope, start_url, 5 ikon)",
               not am.get("errors") and am.get("url") == adres + "/manifest.json"
               and man.get("id") == "/" and man.get("scope") == "/" and man.get("start_url") == "/"
               and len(man.get("icons", [])) >= 5,
               f"hata={am.get('errors')} id={man.get('id')} scope={man.get('scope')}")
            try:
                kh = t.cagir("Page.getInstallabilityErrors").get("installabilityErrors", None)
            except RuntimeError as e:
                kh = [str(e)]
            ok("[!] 4F: Edge'in kurulabilirlik denetimi HATASIZ (manifest + service worker + ikon)",
               kh == [], json.dumps(kh, ensure_ascii=False)[:300])
            olcu = t.js(
                "Promise.all((%s).map(async (i) => { const y = await fetch(i.src); const b = await createImageBitmap(await y.blob());"
                " return [i.src, i.sizes, i.purpose, y.status, b.width + 'x' + b.height]; }))" % json.dumps(man.get("icons", [])))
            yanlis = [o for o in (olcu or []) if o[3] != 200 or o[1] != o[4]]
            ok("4F: her manifest ikonu kopruden 200 ile geliyor ve cozulen olcusu `sizes` ile AYNI",
               bool(olcu) and len(olcu) >= 5 and not yanlis,
               " | ".join(str(o) for o in yanlis) or " ".join(f"{o[0]}={o[4]}" for o in olcu or []))

            # ── 3. Cache Storage: yalniz kabuk, API YOK ─────────────────
            t.js("Promise.all(['/durum', '/skop/liste', '/kunye.json', '/app.js?v=1', '/arsiv/liste']"
                 ".map(u => fetch(u).then(y => y.status).catch(() => 0)))")
            t.bekle(1.0)
            depo = t.js("caches.keys().then(ad => Promise.all(ad.map(a => caches.open(a).then(c => c.keys())"
                        ".then(l => [a, l.map(r => { const u = new URL(r.url); return u.pathname + u.search; })]))))") or []
            adlar = [d[0] for d in depo]
            yollar = [y for d in depo for y in d[1]]
            ok("4F: tek onbellek olcum-kabuk-<SURUM> (sw.js'teki surum)",
               adlar == [f"olcum-kabuk-{surum}"], " ".join(adlar))
            yasak = [y for y in yollar if "?" in y or y in ("/", "/index.html")
                     or any(y == p or y.startswith(p + "/") or y.startswith(p + ".") for p in YASAK)]
            ok("[!] 4F: Cache Storage'da API yolu (/akis /komut /arsiv /kayit /skop* /pil /kal /durum /kunye.json …), "
               "sorgulu adres, gezinme sayfasi YOK",
               bool(yollar) and not yasak, " ".join(yasak) or f"{len(yollar)} giris: " + " ".join(sorted(yollar)))
            gerekli = ["/cevrimdisi.html", "/app.js", "/style.css", "/vendor/vue.global.prod.js",
                       "/ortak/sozluk.js", "/ekran/tema.js"]
            ok("4F: onbellekte cevrimdisi sayfa + kullanilan kabuk dosyalari (yedek icin)",
               all(g in yollar for g in gerekli), " ".join(g for g in gerekli if g not in yollar) or "tamam")

            # ── 4. kopru kapali -> cevrimdisi sayfa; donunce panel ──────
            sunucu.shutdown()
            sunucu.server_close()
            yenile(t)
            cevrim = bekle_js(t, "document.getElementById('cevrimdisi') ? document.title : ''", 10)
            ok("[!] 4F: kopru kapaliyken gezinme 'Kopru calismiyor' sayfasini verir (istenen adres korunur)",
               bool(cevrim) and "Köprü çalışmıyor" in cevrim and t.js("location.hash") == "#/canli",
               f"{cevrim} {t.js('location.href')}")
            dis = t.js("performance.getEntriesByType('resource').map(e => e.name)"
                       ".filter(u => !u.startsWith(location.origin))")
            ok("4F: cevrimdisi sayfa dis kaynak istemiyor", dis == [], str(dis))
            sunucu = kopru_kur(k, port, gorulen)
            geri = bekle_js(t, f"!document.getElementById('cevrimdisi') && {UYG} && {UYG}.bagli", 20)
            ok("[!] 4F: kopru donunce cevrimdisi sayfa kendiliginden panele doner ve baglanir",
               bool(cevrim) and bool(geri), str(t.js("document.title")))

            # ── 5. kart kokeni (guvenli degil) + gelistirme sunucusu: kayit YOK ──
            t.git(f"http://{KART_AD}:{gport}/?demo")
            bekle_js(t, f"{UYG} && {UYG}._sw", 10)
            kart_k = t.js(f"[window.isSecureContext, 'serviceWorker' in navigator, {UYG}._sw]")
            ok("[!] 4F: KART kokeninde (http://olcum.local, guvenli baglam degil) service worker ATLANDI",
               kart_k and kart_k[0] is False and kart_k[1] is False
               and kart_k[2] == {"uygun": False, "durum": "atlandi"}, str(kart_k))
            t.git(f"http://localhost:{gport}/?demo")
            bekle_js(t, f"{UYG} && {UYG}._sw", 10)
            t.bekle(1.5)
            gel_k = t.js(f"navigator.serviceWorker.getRegistrations().then(r => "
                         f"[window.isSecureContext, r.length, {UYG}._sw])")
            ok("4F: gelistirme sunucusunda (localhost, guvenli) da kayit YOK",
               gel_k and gel_k[0] is True and gel_k[1] == 0 and gel_k[2]["uygun"] is False, str(gel_k))

            hatalar = [h for h in t.hatalar() if "favicon" not in h.lower()
                       and "ERR_CONNECTION_REFUSED" not in h and "Failed to fetch" not in h]
            ok("Konsol hatasi yok (kopru kapaliyken beklenen baglanti hatalari haric)",
               not hatalar, " | ".join(hatalar[:3]) or "temiz")
    finally:
        k.calisiyor = False
        for s in (sunucu, gel):
            try:
                s.shutdown()
                s.server_close()
            except Exception:                                  # noqa: BLE001
                pass
        k.durdur()
    if profil:
        n = sizan_edge(profil)
        ok("Edge sizintisi yok (bu profilin msedge sureci kalmadi)", n == 0, f"{n} surec")

    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
