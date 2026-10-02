# -*- coding: utf-8 -*-
"""3A — GORUNUM TARAYICIDA: uc tema render, modul yukleme, tuval yeniden cizimi.

    python tarayici_tema.py                    # sessiz, 0/1 doner
    python tarayici_tema.py --goruntu DIZIN    # her gorunum icin ekran goruntusu

🔴 NEDEN BU BETIK VAR: `test_arayuz3.js` bolum 23 KAYNAK METNINE ve tema
   modulunun saf fonksiyonlarina bakiyor. Bu, `app.js`in ES MODULU olarak
   tarayicida GERCEKTEN acildigini, tema seciminin GERCEK renkleri
   degistirdigini ve tuvalin YENI renkle cizildigini kanitlamiyor. B22.0'da
   zincir 15/15 yesilken arayuz tarayicida hic acilmiyordu.

Burada gercek tarayici (headless Edge, CDP), gercek Vue, gercek modul
yukleyicisi ve `arayuz3/sunucu.py`nin GERCEK isleyicisi var (gecici portta,
`/ortak/` eslemesi dahil). Veri `?demo`nun sahte kartindan
(`sahte-kart.js`) — firmware'in satirlarinin aynisi.

Beklenen RENKLER `style.css`ten BU BETIKTE okunuyor; sayfanin kendi
hesapladigi degerle karsilastirilsaydi test kendini dogrulardi.

⚠ Demo, gelistirme sunucusunda `/durum` (kopru yoklamasi) ve `/pil`
  isteyip 404 aliyor — 3A oncesinden beri boyle, beklenen. Bu ikisi DISINDA
  her ag hatasi (ozellikle .js/.css) KIRMIZI: modul betigi 404 ya da yanlis
  MIME alirsa hata `Runtime`'a degil `Log`'a dusuyor, o yuzden dinleniyor.
"""
from __future__ import annotations

import importlib.util
import re
import socketserver
import sys
import threading
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"
sys.path.insert(0, str(BURASI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tarayici import Tarayici                              # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
BEKLENEN_404 = ("/durum", "/pil", "/favicon.ico")
TEMALAR = ("koyu", "acik", "onpanel")

gecti = kaldi = 0


class _Acilmadi(Exception):
    """Panel tarayicida baslamadi — erken, SAYILARAK bitis."""


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))


def css_takimlari() -> dict:
    """style.css'ten uc temanin belirtec degerleri (sayfadan BAGIMSIZ)."""
    css = re.sub(r"/\*.*?\*/", "", (ARAYUZ / "style.css").read_text(encoding="utf-8"), flags=re.S)
    takim = {}
    for secici, govde in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for ad in TEMALAR:
            if f':root[data-tema="{ad}"]' in [s.strip() for s in secici.split(",")]:
                takim[ad] = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", govde))
    return takim


def rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.strip().lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def bos_port() -> int:
    """CDP icin bos port. ⚠ SABIT PORT KULLANILMIYOR: `Tarayici.kapat()`
    yalnizca baslatici sureci olduruyor, Edge'in kendisi YASAMAYA devam
    ediyor (bu oturumda 9341'de birikti). Sonraki kosu ayni portta ESKI
    tarayiciya baglanip onceki sayfanin hatalarini kendi hatasi sandi."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class KayitliTarayici(Tarayici):
    """`Log` alanini da dinler: modul/varlik yukleme hatalari oraya dusuyor.
    Kapanista profil dizinine ait BUTUN Edge sureclerini olduruyor."""

    def kapat(self) -> None:
        super().kapat()
        if sys.platform == "win32":
            import subprocess
            ad = Path(self.profil).name
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                            f"Where-Object {{ $_.CommandLine -like '*{ad}*' }} | "
                            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
                            "-ErrorAction SilentlyContinue }"],
                           capture_output=True, timeout=60)
        import shutil
        shutil.rmtree(self.profil, ignore_errors=True)   # gecici profil de kalmasin

    def _olay(self, m: dict) -> None:
        if m.get("method") == "Log.entryAdded":
            e = m.get("params", {}).get("entry", {})
            if e.get("level") == "error":
                self.olaylar.append({"tur": "log", "url": e.get("url", ""),
                                     "metin": f"{e.get('source')}: {e.get('text')} {e.get('url', '')}"})
            return
        super()._olay(m)

    def hatalar_tum(self) -> list[str]:
        h = [o["metin"] for o in self.olaylar
             if o["tur"] == "hata" or o.get("seviye") == "error"]
        for o in self.olaylar:
            if o["tur"] == "log":
                yol = re.sub(r"^https?://[^/]+", "", o["url"]).split("?")[0]
                if yol not in BEKLENEN_404:
                    h.append(o["metin"])
        return [x for x in h if "favicon" not in x.lower()]


def sunucu_kur():
    """`arayuz3/sunucu.py`nin isleyicisi — gercek `/ortak/` ve MIME kurali."""
    oz = importlib.util.spec_from_file_location("arayuz_sunucu", ARAYUZ / "sunucu.py")
    gs = importlib.util.module_from_spec(oz)
    oz.loader.exec_module(gs)

    class Sessiz(gs.Sunucu):
        def log_message(self, *a):
            pass

    class Tcp(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = False

        def handle_error(self, *a):
            pass

    s = Tcp(("127.0.0.1", 0), Sessiz)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


PIKSEL_JS = """(() => {
  const c = %s.$refs.grafik;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const hedef = %s;
  const say = hedef.map(() => 0);
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 250) continue;            // kenar yumusatmasi: yari saydam atla
    for (let j = 0; j < hedef.length; j++) {
      const h = hedef[j];
      if (Math.abs(d[i] - h[0]) <= 6 && Math.abs(d[i + 1] - h[1]) <= 6
          && Math.abs(d[i + 2] - h[2]) <= 6) say[j]++;
    }
  }
  return say;
})()"""


def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    takim = css_takimlari()

    print("=" * 78)
    print("  3A  GORUNUM — TARAYICIDA (Koyu · Acik · On panel)")
    print("=" * 78)
    ok("style.css'te uc tema blogu okundu", set(takim) == set(TEMALAR), " ".join(sorted(takim)))
    if set(takim) != set(TEMALAR):
        print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
        return 1

    s = sunucu_kur()
    taban = f"http://127.0.0.1:{s.server_address[1]}"
    print(f"     gelistirme sunucusu: {taban}\n")
    resimler = []
    try:
        with KayitliTarayici(auth_iptal=False, port=bos_port()) as t:
            t.cagir("Log.enable")
            t.tema("dark")
            t.git(taban + "/?demo#/olcum")
            t.bekle(3.5)

            # ── modul olarak acildi mi ───────────────────────────────
            ok("[!] Sayfa konsol/yukleme hatasi OLMADAN aciliyor",
               not t.hatalar_tum(), " | ".join(t.hatalar_tum()[:3]) or "temiz")
            acildi = t.js("!!document.querySelector('script[type=module][src=\"app.js\"]')"
                          " && !document.querySelector('#uyg').hasAttribute('v-cloak')"
                          " && document.body.innerText.indexOf('{{') < 0") is True
            ok("[!] app.js ES MODULU olarak yuklendi ve Vue basladi", acildi,
               "" if acildi else (t.js("document.getElementById('acilmadi-neden').textContent")
                                  or "acilmadi"))
            if not acildi:
                # Panel yoksa geri kalan her olcum anlamsiz (ve JS hatasiyla
                # cokerdi) — kirmizi SAYILARAK bitir.
                raise _Acilmadi()
            ok("Demo verisi akiyor (modulden sahte-kart.js global'i goruluyor)",
               (t.js(f"{UYG}.gecmis.length") or 0) > 100,
               f"{t.js(f'{UYG}.gecmis.length')} nokta")
            ok("Varsayilan: secim 'sistem', koyu sistemde etkin Koyu",
               t.js("document.documentElement.dataset.temaSecim") == "sistem"
               and t.js("document.documentElement.dataset.tema") == "koyu")
            disa = t.js("import('/ortak/rapor.js').then(m => typeof m.oturumRaporu"
                        " + ':' + Object.keys(m).length)")
            ok("[!] /ortak/ modulu tarayicida import ediliyor (gecisli ./ ice aktarmalarla)",
               isinstance(disa, str) and disa.startswith("function:"), str(disa))

            # ── uc tema: arayuz dugmesiyle sec, rengi ve tuvali olc ──
            t.js(f"{UYG}.kes()")                 # akis dursun: tuval yalniz tema ile degissin
            t.bekle(0.5)
            onceki = None
            for ad in TEMALAR:
                d = takim[ad]
                tik = t.js(
                    "(() => { const b = [...document.querySelectorAll('button')]"
                    f".find(x => x.textContent.trim() === {repr(['Koyu', 'Açık', 'Ön panel'][TEMALAR.index(ad)])});"
                    " if (!b) return 'dugme yok'; b.click(); return 'ok'; })()")
                t.bekle(0.6)
                zemin = t.js("getComputedStyle(document.body).backgroundColor")
                beklenen = "rgb({}, {}, {})".format(*rgb(d["--zemin"]))
                kayit = t.js("localStorage.getItem('olcum.tema')")
                ok(f"[!] {ad}: dugme -> data-tema, govde zemini CSS'teki --zemin, secim saklandi",
                   tik == "ok" and t.js("document.documentElement.dataset.tema") == ad
                   and zemin == beklenen and kayit == f'"{ad}"',
                   f"tik={tik} zemin={zemin} (beklenen {beklenen}) kayit={kayit}")
                hedef = [list(rgb(d["--volt"]))] + ([list(rgb(takim[onceki]["--volt"]))] if onceki else [])
                say = t.js(PIKSEL_JS % (UYG, hedef))
                ok(f"[!] {ad}: grafik YENI --volt rengiyle cizili"
                   + (f", eski ({onceki}) renk YOK" if onceki else ""),
                   say[0] > 30 and (not onceki or say[1] == 0),
                   f"yeni {d['--volt']}: {say[0]} px" + (f" · eski {takim[onceki]['--volt']}: {say[1]} px" if onceki else ""))
                if goruntu:
                    t.js("window.scrollTo(0, 0)")
                    t.bekle(0.3)
                    yol = goruntu / f"tema-{ad}.png"
                    t.goruntu(str(yol))
                    resimler.append(yol)
                onceki = ad

            # ── yeniden yukle: secim kaliyor, ilk boyamada uygulanmis ─
            t.git(taban + "/?demo#/ayar")
            t.bekle(3.0)
            ok("[!] Yeniden yuklemede secim KALIYOR (On panel) ve dugmesi etkin",
               t.js("document.documentElement.dataset.tema") == "onpanel"
               and t.js("(() => { const b = [...document.querySelectorAll('button')]"
                        ".find(x => x.textContent.trim() === 'Ön panel');"
                        " return !!b && b.classList.contains('etkin')"
                        " && b.getAttribute('aria-pressed') === 'true'; })()") is True)

            # ── Sistem: isletim sistemi tercihi CANLI izleniyor ──────
            t.js("[...document.querySelectorAll('button')].find(x => x.textContent.trim() === 'Sistem').click()")
            t.bekle(0.4)
            t.tema("light")
            t.bekle(0.6)
            acik_mi = t.js("document.documentElement.dataset.tema")
            t.tema("dark")
            t.bekle(0.6)
            koyu_mu = t.js("document.documentElement.dataset.tema")
            ok("[!] 'Sistem': isletim sistemi acik -> Acik, koyu -> Koyu (sayfa yenilenmeden)",
               acik_mi == "acik" and koyu_mu == "koyu", f"{acik_mi} -> {koyu_mu}")

            # ── telefon genisligi: secici sigiyor ────────────────────
            t.ekran(390, 844)
            t.bekle(0.8)
            sig = t.js("(() => { const g = [...document.querySelectorAll('.dugme-grup')]"
                       ".find(x => x.getAttribute('aria-label') === 'Görünüm');"
                       " if (!g) return 'yok';"
                       " const r = [...g.children].map(b => b.getBoundingClientRect().right);"
                       " return Math.max(...r) <= innerWidth ? 'sigiyor' : 'tasiyor ' + Math.max(...r); })()")
            ok("Telefonda (390 px) Gorunum dugmeleri ekrana sigiyor", sig == "sigiyor", str(sig))
            if goruntu:
                t.js("[...document.querySelectorAll('h2')].find(h => h.textContent === 'Görünüm')"
                     ".scrollIntoView({block: 'center'})")
                t.bekle(0.4)
                yol = goruntu / "tema-telefon-ayar.png"
                t.goruntu(str(yol))
                resimler.append(yol)

            ok("[!] Butun gezinti boyunca konsol/yukleme hatasi yok",
               not t.hatalar_tum(), " | ".join(t.hatalar_tum()[:3]) or "temiz")
    except _Acilmadi:
        print("     panel acilmadi — kalan olcumler ATLANDI (kirmizi sayildi)")
    finally:
        s.shutdown()
        s.server_close()

    for y in resimler:
        print(f"     goruntu: {y}")
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
