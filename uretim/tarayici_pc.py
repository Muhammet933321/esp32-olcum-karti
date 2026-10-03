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

import http.server
import socketserver
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

# 4A inceleme (CSRF): BASKA bir 127.0.0.1 portundan (stok-takip, bir gelistirme
# sunucusu...) sunulan sayfa. <img> ozel baslik ekleyemez ama GET kopruye ULASIR;
# eskiden /skop.bin karta `t` yollatiyor, /akis suruculugu ilk gelene veriyordu.
SALDIRI = """<!doctype html><html><body>
<img src="http://127.0.0.1:{p}/akis"><img src="http://127.0.0.1:{p}/skop.bin">
<img src="http://olcum.localhost:{p}/akis"><img src="http://olcum.localhost:{p}/skop.bin">
<img src="http://127.0.0.1:{p}/skop/liste?gun=//saldirgan.example/pay/x">
<script>
window.sonuc = [];
const not_ = (ad) => (r) => window.sonuc.push(ad + ' ' + (r.type || r.status));
fetch("http://127.0.0.1:{p}/skop.bin", {{mode: "no-cors"}}).then(not_("skop")).catch(e => window.sonuc.push("skop HATA"));
fetch("http://127.0.0.1:{p}/komut", {{method: "POST", headers: {{"X-Olcum": "1"}}, body: "GF!"}})
  .then(not_("komut")).catch(e => window.sonuc.push("komut HATA"));
fetch("http://127.0.0.1:{p}/komut", {{method: "POST", mode: "no-cors", body: "p1"}})
  .then(not_("komut2")).catch(e => window.sonuc.push("komut2 HATA"));
</script></body></html>"""


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
    komutlar: list[tuple[str, int]] = []         # 4I: (komut, HTTP kodu) — /komut yanitlari
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

        def _yanit(self, kod, govde=b"", tip="text/plain"):
            if self.path.split("?")[0] == "/komut":
                komutlar.append((getattr(self, "_govde_metin", ""), kod))
            return super()._yanit(kod, govde, tip)

    sunucu.RequestHandlerClass = Kayitli
    port = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    threading.Thread(target=k.dongu, daemon=True).start()
    adres = f"http://{pc_ayar.AD}:{port}"
    print(f"     kopru: {sunucu.server_address} · panel: {adres}\n")
    ok("Kopru yalniz 127.0.0.1'e bagli (gercek sunucu_kur)", sunucu.server_address[0] == "127.0.0.1",
       str(sunucu.server_address))
    sayfa = SALDIRI.format(p=port).encode("utf-8")

    class Saldiri(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(sayfa)))
            self.end_headers()
            self.wfile.write(sayfa)

        def log_message(self, *a):
            pass

    saldiri = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Saldiri)
    saldiri.daemon_threads = True
    threading.Thread(target=saldiri.serve_forever, daemon=True).start()
    try:
        with Tarayici(auth_iptal=False) as t:
            # ── 4A inceleme: once saldiri sayfasi (kopru Windows acilisinda
            #    arka planda, panel henuz acilmamis — surucu yok) ──────────
            t.git(f"http://127.0.0.1:{saldiri.server_address[1]}/")
            bekle_js(t, "window.sonuc && window.sonuc.length >= 3", 8)
            t.bekle(1.5)
            ulasan = sorted({y for ip, h, y in gorulen if y in ("/akis", "/skop.bin", "/skop/liste")})
            ok("[!] CSRF: baska 127.0.0.1 portundaki sayfanin <img>/fetch istekleri kopruye ULASTI "
               "(sinama bos degil) ama karta HICBIR SEY gitmedi (`t`, GF!, p1 yok)",
               ulasan == ["/akis", "/skop.bin", "/skop/liste"] and kart.yazilanlar == [],
               f"ulasan={ulasan} karta={kart.yazilanlar} sayfa={t.js('JSON.stringify(window.sonuc)')}")
            ok("[!] CSRF: saldiri sayfasi SURUCULUGU kapmadi, jeton almadi",
               k.surucu is None and not k.jetonlar, f"surucu={k.surucu} jeton={len(k.jetonlar)}")
            gorulen.clear()

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
            ok("[!] Saldiridan sonra acilan GERCEK panel surucu (rol calinmadi)",
               t.js(f"{UYG}.surucuyum") is True and k.surucu is not None,
               f"surucuyum={t.js(UYG + '.surucuyum')} jeton={len(k.jetonlar)}")
            hatalar = [h for h in t.hatalar() if "favicon" not in h.lower()]
            ok("Konsol hatasi yok", not hatalar, " | ".join(hatalar[:3]) or "temiz")

            # ── 4I: surucu sekme YENILENINCE rol yeni sekmeye gecer ──────
            # 🔴 4H'de bulundu: kopru eski sekmenin jetonunu tutuyordu; yenilenen sekme
            #    izleyici kaliyor, acilis komutlari (`?`, `CT`, `G?`) 403 aliyordu.
            eski = k.surucu
            komutlar.clear()
            t.cagir("Page.reload", {"ignoreCache": False})
            t.bekle(1.0)
            bekle_js(t, f"{UYG}.bagli && {UYG}.gecmis.length > 10", 15)
            bekle_js(t, f"{UYG}.surucuyum === true", 3)
            t.bekle(1.5)                 # acilis komutlarinin yanitlari
            red = [(m, c) for m, c in komutlar if c != 204]
            ok("[!] 4I: panel YENILENINCE yeni sekme SURUCU (elle devralmadan), acilis komutlari "
               "403 almadi",
               t.js(f"{UYG}.surucuyum") is True and k.surucu not in (None, eski)
               and any(m == "?" and c == 204 for m, c in komutlar) and not red,
               f"surucuyum={t.js(UYG + '.surucuyum')} degisti={k.surucu != eski} "
               f"komutlar={komutlar[:8]} red={red[:4]}")
            ok("4I: yenilemeden sonra panelde 'Komut gönderilemedi' hatasi yok",
               "403" not in str(t.js(f"{UYG}.hata") or ""), str(t.js(f"{UYG}.hata")))

            # ── 4I: ACIK izleyici panel, surucu sekme kapaninca yeniden yuklenmeden surucu ─
            # Ikinci "sekme" ham soketle (bu bilgisayardan) acilip /devral ile surucu olur;
            # panel izleyiciye duser. O sekme kapaninca kopru rolu panele verir ve `kimlik`
            # olayini AKAN baglantiya yollar — panel bunu yeniden yuklenmeden islemeli.
            import json as _json
            import socket as _socket
            import urllib.request as _ur
            ikinci = _socket.create_connection(("127.0.0.1", port), timeout=10)
            ikinci.sendall(f"GET /akis HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\r\n".encode())
            dosya = ikinci.makefile("rb")
            jeton2, sonraki = None, False
            son = time.monotonic() + 5
            while jeton2 is None and time.monotonic() < son:
                sat = dosya.readline().decode("utf-8", "replace").rstrip("\r\n")
                if sat.startswith("event: kimlik"):
                    sonraki = True
                elif sat.startswith("data: ") and sonraki:
                    jeton2 = _json.loads(sat[6:])["jeton"]
            r = _ur.Request(f"http://127.0.0.1:{port}/devral", data=b"", method="POST",
                            headers={"X-Olcum": "1", "X-Jeton": jeton2 or ""})
            with _ur.urlopen(r, timeout=5) as y:
                kod_dv = y.status
            t.js(f"{UYG}.surucuyum = false")          # panel izleyici (devral'i bilmiyordu)
            ikinci.shutdown(_socket.SHUT_RDWR)
            dosya.close()
            ikinci.close()
            t0 = time.monotonic()
            gecti_mi = bekle_js(t, f"{UYG}.surucuyum === true", 4)
            dt = time.monotonic() - t0
            ok("[!] 4I: ACIK izleyici panel, surucu sekme kapaninca YENIDEN YUKLENMEDEN surucu olur "
               "(`kimlik` olayi akan baglantidan; <= 2 s)",
               kod_dv == 204 and gecti_mi is True and dt <= 2.0
               and k.surucu == t.js(f"{UYG}.jeton"),
               f"devral={kod_dv} dt={dt:.2f} s surucuyum={t.js(UYG + '.surucuyum')}")
            print(f"     profil: {t.profil}")
    finally:
        saldiri.shutdown()
        saldiri.server_close()
        k.calisiyor = False
        sunucu.shutdown()
        sunucu.server_close()
        k.durdur()

    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
