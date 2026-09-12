# -*- coding: utf-8 -*-
"""B35 — SKOP ARSIVI TARAYICIDA GERCEKTEN GORUNUYOR MU.

    python tarayici_skop_arsiv.py            # sessiz, 0/1 doner
    python tarayici_skop_arsiv.py --goruntu  # ekran goruntusu de al

🔴 NEDEN BU BETIK VAR: `test_arayuz3.js` bolum 16 KAYNAK METNINDE arama
   yapiyor — `v-if="skopArsivVar"` yaziyor mu, `skopIkiliCoz` cagriliyor
   mu. Bu, sayfanin TARAYICIDA acildigini kanitlamiyor. B22.0'da zincir
   15/15 yesilken arayuz tarayicida HIC acilmiyordu; bu projede o ders
   pahaliya ogrenildi.

   Burada gercek bir tarayici (CDP), gercek Vue, gercek DOM var. Sahte
   bir kopru sunucusu `/durum`, `/skop/liste` ve `/skop/al` ucunu
   karsiliyor — yani arayuz KOPRUYE bagliymis gibi davraniyor.

⚠ Sahte kopru KARTI taklit etmiyor, KOPRUYU taklit ediyor: govdeler
  `kopru/arsiv.py`'nin GERCEK paketleyicisinden (`skop_ikili`) geliyor,
  elle yazilmiyor. Elle yazilsaydi bicim ayrisir ve bu test yanlis bir
  bicimi dogrulardi.
"""
from __future__ import annotations

import json
import math
import sys
import threading
import http.server
import socketserver
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from arsiv import skop_ikili                               # noqa: E402
from tarayici import Tarayici                              # noqa: E402

gecti = kaldi = 0

# 🔴 Vue ornegine erisim. `app.js` `.mount('#uyg')` sonucunu HICBIR
#    yere koymuyor (global bir kanca eklemek yalnizca test icin uretim
#    koduna dokunmak olurdu). Vue 3 kabin uzerine `__vue_app__` koyuyor;
#    ic API, ama Vue yukseltmesinde SESSIZCE degil GURULTUYLE kirilir —
#    `js()` istisnayi yukseltiyor.
# ⚠ `__vue_app__._instance` bu surumde NULL (uretim yapisi); calisan yol
#   kabin uzerindeki `_vnode.component`. Ikisi de ic API — kirilirsa
#   `js()` istisna atar, yani SESSIZ kalmaz.
UYG = "document.querySelector('#uyg')._vnode.component.proxy"


def u(ifade: str) -> str:
    """`u('skopArsivVar')` -> uygulamanin o alanini okuyan JS ifadesi."""
    return f"(() => {{ const g = {UYG}; return g.{ifade}; }})()"



def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))


# Iki kayit: biri tetiklenmis ve tam, biri tetiklenmemis ve KIRPIK —
# arayuzun ikisini de AYIRT EDEREK gostermesi gerekiyor.
def _dalga(n, donem):
    return [int(2048 + 1500 * math.sin(2 * math.pi * i / donem)) for i in range(n)]


KAYITLAR = {
    (("2026-09-12", 1200)): {
        "gun": "2026-09-12", "ms": 1200, "adet_bildirilen": 400,
        "hz": 20000, "adim": 0.028787, "ofset": 63.530093,
        "tetik_idx": 100, "tdiv_us": 5000, "kip": 0, "tetiklendi": True,
        "ornek": _dalga(400, 80), "olcum": "M f=250.000 Vpp=24.0000 n=5",
        "tam": True, "atlanan": 0,
    },
    (("2026-09-12", 9400)): {
        "gun": "2026-09-12", "ms": 9400, "adet_bildirilen": 400,
        "hz": 20000, "adim": 0.028787, "ofset": 63.530093,
        "tetik_idx": 0, "tdiv_us": 5000, "kip": 0, "tetiklendi": False,
        "ornek": _dalga(137, 40), "olcum": "", "tam": False, "atlanan": 3,
    },
}


class SahteKopru(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ARAYUZ), **k)

    def log_message(self, *a):
        pass

    def _gonder(self, kod, govde, tip):
        self.send_response(kod)
        self.send_header("Content-Type", tip)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        yol = self.path.split("?")[0]
        if yol == "/durum":
            return self._gonder(200, json.dumps({
                "kart": "sahte", "satir": 10, "abone": 1,
                "arsiv_satir": 10, "surucu_var": True,
                "skop_arsiv": True, "skop_adedi": len(KAYITLAR),
            }).encode(), "application/json")
        if yol == "/skop/liste":
            kyt = [{"gun": b["gun"], "ms": b["ms"], "adet": len(b["ornek"]),
                    "adet_bildirilen": b["adet_bildirilen"], "hz": b["hz"],
                    "tdiv_us": b["tdiv_us"], "tetiklendi": b["tetiklendi"],
                    "tam": b["tam"], "olcum": b["olcum"]}
                   for b in KAYITLAR.values()]
            kyt.reverse()
            return self._gonder(200, json.dumps(
                {"gunler": ["2026-09-12"], "gun": "2026-09-12",
                 "kayitlar": kyt}).encode(), "application/json")
        if yol == "/skop/al":
            import urllib.parse
            s = urllib.parse.parse_qs(self.path.split("?", 1)[-1])
            anahtar = (s.get("gun", [""])[0], int(s.get("ms", ["0"])[0]))
            b = KAYITLAR.get(anahtar)
            if not b:
                return self._gonder(404, b"yok", "text/plain")
            return self._gonder(200, skop_ikili(b), "application/octet-stream")
        if yol == "/akis":
            # Arayuz `kimlik` olayini bekliyor; gelmezse 3 s tavanla devam
            # ediyor. Kisa bir akis acip kimligi yolluyoruz.
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            try:
                self.wfile.write(b"retry: 3000\n\n")
                self.wfile.write(b'event: kimlik\ndata: {"jeton":"x","surucu":true}\n\n')
                self.wfile.flush()
                import time
                time.sleep(30)
            except OSError:
                pass
            return
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        self._gonder(204, b"", "text/plain")


class Sunucu(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False

    def handle_error(self, *a):
        pass


def main() -> int:
    sunucu = Sunucu(("127.0.0.1", 0), SahteKopru)
    port = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    taban = f"http://127.0.0.1:{port}"

    print("=" * 78)
    print("  B35  SKOP ARSIVI — TARAYICIDA")
    print("=" * 78)
    print(f"     sahte kopru: {taban}\n")

    goruntu = "--goruntu" in sys.argv
    try:
        with Tarayici(auth_iptal=False) as t:
            t.git(taban + "/#/skop")
            t.bekle(3.0)

            # Kopru kipine gec: arayuz `akis` tasiyicisini secmeli ve
            # baglanmali. Sayfa kopruden geldigi icin kendiliginden
            # oluyor (kopruyuAlgila), ama garantiye aliyoruz.
            t.js(f"{UYG}.tasiyiciAdi = 'akis'")
            t.bekle(0.5)
            t.js(f"{UYG}.baglan()")
            t.bekle(2.5)

            hatalar = [h for h in t.hatalar() if "favicon" not in h.lower()]
            ok("[!] Sayfa konsol hatasi OLMADAN aciliyor", not hatalar,
               " | ".join(hatalar[:3]) or "temiz")
            ok("Ham `{{ }}` ekranda kalmiyor (Vue basladi)",
               t.js("document.body.innerText.indexOf('{{') < 0") is True)

            ok("[!] Kopru algilandi (skopArsivVar)",
               t.js(u("skopArsivVar")) is True,
               str(t.js(u("skopArsivVar"))))
            ok("[!] Kayit listesi DOLDU",
               t.js(u("skopKayitlar.length")) == 2,
               str(t.js(u("skopKayitlar.length"))))

            # 🔴 ASIL IDDIA: bolum GERCEKTEN DOM'da ve GORUNUR.
            gorunur = t.js(
                "(() => { const e = [...document.querySelectorAll('h2')]"
                ".find(h => h.textContent.includes('Kayıtlar'));"
                " if (!e) return 'baslik yok';"
                " const s = e.closest('section');"
                " return s.getBoundingClientRect().height > 0 ? 'gorunur'"
                " : 'yuksekligi sifir'; })()")
            ok("[!] Kayitlar bolumu DOM'da ve gorunur", gorunur == "gorunur",
               str(gorunur))
            ok("Listede 2 kayit dugmesi ciziliyor",
               t.js("document.querySelectorAll('.kayit').length") == 2,
               str(t.js("document.querySelectorAll('.kayit').length")))
            # Kirpik kayit SESSIZ kalmamali.
            #
            # ⚠ TUZAK (burada gercekten yasandi): ilk yazdigim iddia
            #   `document.body.innerText.includes('kırpık')` idi ve
            #   BASARISIZ oldu — ama urun dogruydu. `.kayit-etiket`
            #   `text-transform: uppercase` tasiyor ve Chrome'un
            #   `innerText`'i donusumu UYGULUYOR: DOM'da "kırpık" yazan
            #   metin "KIRPIK" olarak geri geliyor (Turkcede i -> I).
            #   `textContent` donusumu uygulamaz. Yani gorunuse gore
            #   basarisiz olan sey olcumun kendisiydi.
            #
            # Bulunamazsa etiketler yaziliyor — "false" tek basina
            # nedenini soylemiyor.
            etiketler = t.js(
                "[...document.querySelectorAll('.kayit-etiket')]"
                ".map(e => e.textContent.trim())")
            ok("[!] KIRPIK kayit isaretlenmis",
               any("rp" in (e or "") for e in (etiketler or [])),
               " · ".join(etiketler or []) or "hic etiket yok")

            if goruntu:
                # Bolumu GORUNUR ALANA getir: ekran goruntusu yalnizca
                # viewport'u aliyor ve kanit olarak konulan ilk goruntude
                # Kayitlar bolumu katlamanin altinda kalmisti.
                t.js("[...document.querySelectorAll('h2')]"
                     ".find(h => h.textContent.includes('Kay'))"
                     ".scrollIntoView({block: 'center'})")
                t.bekle(0.6)
                t.goruntu(str(BURASI / "_skop-arsiv-liste.png"))

            # ── Bir kaydi AC ve tuvalde ciziliyor mu bak ──────────────
            t.js("document.querySelectorAll('.kayit')[1].click()")
            t.bekle(2.0)

            ok("[!] Arsiv kaydi COZULDU ve cizildi",
               t.js(u("osilo ? g.osilo.veri.length : -1")) == 400,
               str(t.js(u("osilo ? g.osilo.veri.length : -1"))))
            ok("Cozulen veri SAHTE KOPRUNUN yolladigi dalga",
               t.js(u("osilo.veri[20]")) == KAYITLAR[("2026-09-12", 1200)]["ornek"][20],
               f"arayuz {t.js(u("osilo.veri[20]"))} · "
               f"kaynak {KAYITLAR[('2026-09-12', 1200)]['ornek'][20]}")
            ok("Baslik alanlari da dogru cozuldu",
               t.js(u("osilo.hz")) == 20000
               and t.js(u("osilo.tetikIdx")) == 100
               and t.js(u("osilo.tetiklendi")) is True)

            ok("[!] Tuvalde ARSIV seridi belirdi (canli sanilmasin)",
               t.js("!!document.querySelector('.arsiv-serit')") is True
               and t.js("document.body.innerText.includes('canlı değil')") is True)
            ok("Acik kayit listede isaretli",
               t.js("document.querySelectorAll('.kayit.acik').length") == 1,
               str(t.js("document.querySelectorAll('.kayit.acik').length")))
            ok("Tuval GERCEKTEN cizilmis (bos piksel degil)",
               t.js("(() => { const c = " + UYG + ".$refs.osiloTuval;"
                    " const d = c.getContext('2d').getImageData("
                    "0, 0, c.width, c.height).data;"
                    " let n = 0; for (let i = 3; i < d.length; i += 4)"
                    " if (d[i] > 0) n++; return n; })()") > 1000,
               "saydam olmayan piksel sayisi")

            if goruntu:
                t.goruntu(str(BURASI / "_skop-arsiv-kayit.png"))

            hatalar = [h for h in t.hatalar() if "favicon" not in h.lower()]
            ok("Kayit acarken de konsol hatasi yok", not hatalar,
               " | ".join(hatalar[:3]) or "temiz")
    finally:
        sunucu.shutdown()

    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
