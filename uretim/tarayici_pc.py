# -*- coding: utf-8 -*-
"""T4A — PC KOPRUSU GERCEK TARAYICIDA: koken olcum.localhost (PC1).

    python tarayici_pc.py          # 0 = yesil, 1 = kirmizi

🔴 NEDEN BU BETIK VAR: PC1 kararinin dayanagi bir OLCUM — `*.localhost`
   Edge'de donguye cozuluyor mu, guvenli baglam mi, service worker kayit
   olabiliyor mu. Kaynak metni ya da kopru birim testi (B22a) bunu
   kanitlayamaz; tarayici davranisi. Ilk olcum 2026-10-03 (Edge 154):
   uc soru da EVET. Bu betik o olcumu her kosuda tekrarlar ve ustune
   GERCEK kopruyu (kopru.sunucu_kur, yalniz 127.0.0.1) + GERCEK paneli koyar:
   panel o kokende kendiliginden `akis` tasiyicisiyla baglanmali (Web Serial
   degil), komutu kopru uzerinden karta yollamali.

⚠ Kart: `KayitKart` (sahte satir akisi) — donanim gerekmez.
⚠ Edge: `tarayici.Tarayici` (profil ve surec sizintisi korumali).
"""
from __future__ import annotations

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

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
gecti = kaldi = 0

SW = (b"self.addEventListener('install', e => self.skipWaiting());\n"
      b"self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));\n")


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


def main() -> int:
    print("=" * 78)
    print("  T4A  PC KOPRUSU — olcum.localhost kokeni GERCEK TARAYICIDA")
    print("=" * 78)
    satirlar = [f"D {12 + i * 0.01:.4f} 0.100000 1.20000 0.0000 0.0000000 {1000 + i * 100} 172 0 0"
                for i in range(400)]
    kart = kart_baglanti.KayitKart(satirlar, yanitlar={"?": ["A menzil=NORMAL oto=1"]},
                                   gecikme=0.03)
    kart.ac()
    k = kopru_mod.Kopru(kart, gecici.dizin("kopru_t4a_") / "arsiv")
    sunucu = kopru_mod.sunucu_kur(k, port=0)        # GERCEK baglama: yalniz 127.0.0.1
    gorulen: list[tuple[str, str, str]] = []
    taban_sinif = sunucu.RequestHandlerClass

    class Kayitli(taban_sinif):
        """GERCEK isleyici + gelen istegin (istemci, Host) kaydi + deneme SW'si."""

        def do_GET(self):
            gorulen.append((self.client_address[0], self.headers.get("Host", ""),
                            self.path.split("?")[0]))
            if self.path.startswith("/_sw_deneme/sw.js"):
                if not self._kapi():
                    return
                return self._yanit(200, SW, "text/javascript")
            return super().do_GET()

    sunucu.RequestHandlerClass = Kayitli
    port = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    threading.Thread(target=k.dongu, daemon=True).start()
    adres = f"http://{pc_ayar.AD}:{port}"
    print(f"     kopru: {sunucu.server_address} · panel: {adres}\n")
    ok("Kopru yalniz 127.0.0.1'e bagli (gercek sunucu_kur)", sunucu.server_address[0] == "127.0.0.1",
       str(sunucu.server_address))
    try:
        with Tarayici(auth_iptal=False) as t:
            t.git(adres + "/#/canli")
            bekle_js(t, f"{UYG}.bagli && {UYG}.gecmis.length > 10", 15)

            ok("[!] PC1: olcum.localhost istegi 127.0.0.1'deki kopruye ULASTI (hosts yok, OS cozmuyor)",
               any(ip == "127.0.0.1" and h == f"{pc_ayar.AD}:{port}" and y == "/"
                   for ip, h, y in gorulen),
               str(gorulen[:2]))
            ok("Sayfa olcum.localhost kokeninde", t.js("location.hostname") == pc_ayar.AD,
               str(t.js("location.origin")))
            ok("[!] PC1: olcum.localhost GUVENLI BAGLAM (isSecureContext)",
               t.js("window.isSecureContext") is True, str(t.js("window.isSecureContext")))
            sw = t.js("navigator.serviceWorker.register('/_sw_deneme/sw.js', {scope: '/_sw_deneme/'})"
                      ".then(r => (r.installing || r.waiting || r.active) ? 'kayitli' : 'bos')"
                      ".catch(e => 'HATA ' + e)")
            ok("[!] PC1: service worker KAYIT OLABILIYOR (4F PWA kabugunun on kosulu)",
               sw == "kayitli", str(sw))
            ok("[!] Panel bu kokende tasiyiciyi kendiliginden `akis` secti (Web Serial degil)",
               t.js(f"{UYG}.tasiyiciAdi") == "akis", str(t.js(f"{UYG}.tasiyiciAdi")))
            ok("[!] Panel 'Baglan'a basilmadan kopruye BAGLANDI ve satir aliyor",
               t.js(f"{UYG}.bagli") is True and (t.js(f"{UYG}.gecmis.length") or 0) > 10,
               f"bagli={t.js(UYG + '.bagli')} gecmis={t.js(UYG + '.gecmis.length')}")
            ok("Komut yolu: panelin `?`u kopru uzerinden KARTA ulasti",
               "?" in kart.yazilanlar, " ".join(kart.yazilanlar[:6]))
            hatalar = [h for h in t.hatalar() if "favicon" not in h.lower()]
            ok("Konsol hatasi yok", not hatalar, " | ".join(hatalar[:3]) or "temiz")
    finally:
        k.calisiyor = False
        sunucu.shutdown()
        sunucu.server_close()
        k.durdur()

    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
