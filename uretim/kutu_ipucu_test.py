"""kutu_ipucu_test.py — 8-kutu.html'deki parca bilgi kartini GERCEK tarayicida sinar (B57).

Kullanici (2026-09-24): "Elimi mouse ile uzerine getirince veya bir tusa basinca
o parcanin detaylarini gorebilmem lazim — uzunlugu, adi, olculeri."

Denetim (kutu.py) kartlarin VERIDEN dogru uretildigini olcuyor; bu test ise
kullanicinin gercekten GORDUGUNU olcuyor: headless Edge'e CDP'den gercek fare
ve klavye olaylari gonderir, #ipucu'nun gorunup gorunmedigine ve ne yazdigina
bakar. Sayfaya test kancasi EKLENMEDI — her sey disaridan, kara kutu.

    python kutu_ipucu_test.py            # ~40 s: belgeyi GECICI klasore uretir, sinar
    python kutu_ipucu_test.py --goruntu  # ek olarak _ipucu_*.png

Belge her kosuda KAYNAKTAN yeniden uretilir (BELGELER/'e dokunmaz). Boylece
mutasyon kosucusu (adim B57) JS'i ya da kutu.py'yi bozdugunda test, bozulmus
kodun URETTIGI sayfayi sinar — hazir bir HTML'e bakip yesil kalmaz.

Cikis kodu: kalan iddia sayisi (0 = hepsi gecti).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from tarayici import Tarayici

sys.stdout.reconfigure(encoding="utf-8")

GORUNTU = "--goruntu" in sys.argv


def belge_uret() -> Path:
    """Belgeyi GECICI bir klasore kaynaktan uret (denetimsiz; denetim kutu.py'nin isi)."""
    import tempfile
    import kutu
    import yerlesim3 as Y
    nl = Y.Netlist(Y.NETLIST)
    parcalar = Y.parcalari_yukle()
    hedef = Path(tempfile.mkdtemp(prefix="kutu-ipucu-")) / "8-kutu.html"
    kutu.yaz(nl, parcalar, hedef)
    return hedef
gecti = kaldi = 0


def kosul(ad: str, ok: bool, ayrinti: str = "") -> None:
    global gecti, kaldi
    if ok:
        gecti += 1
    else:
        kaldi += 1
    print(f"  [{'OK' if ok else '!!'}] {ad}" + (f"   {ayrinti}" if ayrinti else ""))


def kart(t: Tarayici) -> dict:
    """#ipucu'nun o anki hali: gorunur mu, baslik, satirlar, ipucu satiri."""
    return t.js("""(function(){
      var i = document.getElementById('ipucu');
      var r = [].map.call(i.querySelectorAll('dt'), function(dt){ return [dt.textContent, dt.nextSibling.textContent]; });
      var q = function(s){ var e = i.querySelector(s); return e ? e.textContent : ''; };
      return {gorunur: !i.hidden && i.offsetWidth > 0, baslik: q('.ib'), tur: q('.it'), satir: r,
              durum: q('.id'), ipucu: q('.ik'), k: i.dataset.k || ''};
    })()""")


def fare(t: Tarayici, x: float, y: float, tur: str = "mouseMoved", tus: str = "none") -> None:
    p = {"type": tur, "x": x, "y": y, "button": tus, "clickCount": 1 if tur != "mouseMoved" else 0}
    if tus != "none":
        p["buttons"] = 1 if tur == "mousePressed" else 0
    t.cagir("Input.dispatchMouseEvent", p)


def tikla(t: Tarayici, x: float, y: float) -> None:
    fare(t, x, y)
    fare(t, x, y, "mousePressed", "left")
    fare(t, x, y, "mouseReleased", "left")


def tus(t: Tarayici, ad: str, kod: int, metin: str = "") -> None:
    for tur in ("keyDown", "keyUp"):
        p = {"type": tur, "key": ad, "code": ad if len(ad) > 1 else f"Key{ad.upper()}",
             "windowsVirtualKeyCode": kod, "nativeVirtualKeyCode": kod}
        if metin and tur == "keyDown":
            p["text"] = metin
        t.cagir("Input.dispatchKeyEvent", p)


def adima_git(t: Tarayici, no: str) -> None:
    t.js(f"location.hash = '#a{no}'")
    t.bekle(0.4)


def merkez(t: Tarayici, secici: str) -> dict | None:
    """Gorunur ilk ogenin ILK SEKLININ (rect/circle/polygon) ekrandaki merkezi.

    Grubun kendisi olculmez: panel ciziminde jakin grubu alttaki etiketleri de
    kapsiyor, sinir kutusunun ortasi baska bir parcanin ustune dusuyordu. Kaydirma
    ANINDA yapilir ve bir kare sonra olculur (sayfada yumusak kaydirma var)."""
    var = t.js(f"""(function(){{
      var L = [].filter.call(document.querySelectorAll({json.dumps(secici)}),
                             function(e){{ return e.getClientRects().length
                                           && !e.closest('details:not([open])'); }});
      // ⚠ Chromium kapali <details> icindeki SVG'ye de sinir kutusu donduruyor:
      //   getClientRects() tek basina "gorunur" demek degil (ilk surum yaniliyordu).
      if (!L.length) return null;
      var s = L[0].querySelector('rect,circle,polygon,polyline') || L[0];
      window.__olc = s;
      s.scrollIntoView({{block: 'center', behavior: 'instant'}});
      return L.length;
    }})()""")
    if not var:
        return None
    t.bekle(0.3)
    return t.js("""(function(){ var r = window.__olc.getBoundingClientRect();
      return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()""")


def main() -> int:
    BELGE = belge_uret()
    bilgi = json.loads(__import__("re").search(r"var BILGI = (\{.*?\});\n", BELGE.read_text(encoding="utf-8"), 16)
                       .group(1).replace("<\\/", "</"))
    print("  KUTU BELGESI — parca bilgi karti (gercek tarayici)")
    with Tarayici(genislik=1280, yukseklik=900, auth_iptal=False) as t:
        t.git(BELGE.as_uri())
        t.bekle(1.5)
        kosul("Sayfa JS hatasi olmadan acildi", not t.hatalar(), "; ".join(t.hatalar())[:300])
        kosul("Kart kutusu var ve baslangicta gizli", t.js("!!document.getElementById('ipucu') && document.getElementById('ipucu').hidden"))

        # ── 2B: panel ciziminde bir jakin uzerine gel ───────────────────
        print("\n  2B · panel cizimi (adim 5.2)")
        adima_git(t, "5.2")
        m = merkez(t, '.aa:not([hidden]) [data-bi="j:J3.1"]')
        kosul("5.2'de YUK 1 jaki cizimde gorunuyor", m is not None, str(m))
        if m:
            fare(t, m["x"] - 200, m["y"] - 200)
            t.bekle(0.1)
            fare(t, m["x"], m["y"])
            t.bekle(0.25)
            k = kart(t)
            beklenen = bilgi["j:J3.1"]["t"]
            kosul("Uzerine gelince kart ACILIYOR", k["gorunur"], k["baslik"])
            kosul("Kart dogru parcayi gosteriyor (baslik veriden)", k["baslik"] == beklenen, f"{k['baslik']!r} == {beklenen!r}")
            satir = dict(k["satir"])
            kosul("Kartta delik capi ve stoktaki yeri var", "Ø8" in satir.get("Delik", "") and "Soketler" in satir.get("Stok", ""),
                  f"Delik {satir.get('Delik')} · Stok {satir.get('Stok')}")
            if GORUNTU:
                t.goruntu("_ipucu_2b.png")
            fare(t, 5, 5)
            t.bekle(0.25)
            kosul("Uzerinden cekilince kart KAPANIYOR", not kart(t)["gorunur"])
            tikla(t, m["x"], m["y"])
            t.bekle(0.25)
            k = kart(t)
            kosul("Tiklayinca kart SABITLENIYOR", k["gorunur"] and "sabitlendi" in k["ipucu"], k["ipucu"])
            fare(t, 5, 5)
            t.bekle(0.25)
            kosul("Sabit kart fare uzaklasinca KALIYOR", kart(t)["gorunur"])
            tus(t, "Escape", 27)
            t.bekle(0.2)
            kosul("Esc sabit karti KAPATIYOR", not kart(t)["gorunur"])

        # ── 2B: klavye — Tab ile odak = kart ────────────────────────────
        print("\n  2B · klavye")
        n = t.js("""(function(){
          var L = [].filter.call(document.querySelectorAll('.aa:not([hidden]) svg [data-bi]'),
                                 function(e){ return e.getClientRects().length && e.tabIndex >= 0
                                                     && !e.closest('details:not([open])'); });
          if (L.length < 2) return 0;
          // GERCEK Tab senaryosu: parca GORUNUM DISINDAYKEN odaklanir, tarayici onu
          // gorunume KAYDIRIR. Ilk surumdeki hata tam buydu: kaydirma dinleyicisi
          // karti kapatiyordu. Kaydirma olmadan bu iddia o hatayi goremez.
          // B59b: sayfa sonuna kaydirip ILK parcaya odaklanmak duzene bagliydi — on panel
          // yeniden dizilince cizimin altindaki etiket listesi kisaldi, parca gorunumun ancak
          // 22 px ustunde kaldi ve kaydirma 23 px'te bitti (esik 50). Artik parca hangi taraftaysa
          // oradan UZAKLASILIYOR: ilk ekranin altindaysa sayfa basina, degilse sonuna.
          var ust = L[0].getBoundingClientRect().top + window.pageYOffset;
          if (ust > window.innerHeight + 100) window.scrollTo(0, 0);
          else window.scrollTo(0, document.body.scrollHeight);
          var b = L[0].getBoundingClientRect();
          window.__disarida = b.bottom < 0 || b.top > window.innerHeight;
          window.__once = window.pageYOffset;
          L[0].focus(); return L.length; })()""")
        kosul("Cizimdeki parcalar klavyeyle odaklanabiliyor (tabindex)", (n or 0) >= 2, f"{n} parca")
        t.bekle(0.4)
        kaydi = t.js("window.__disarida && Math.abs(window.pageYOffset - window.__once) > 50")
        kosul("Odak parcayi gorunume KAYDIRDI (senaryo gercekten kaydirma iceriyor)", bool(kaydi),
              str(t.js("({disarida: window.__disarida, once: window.__once, sonra: window.pageYOffset})")))
        k1 = kart(t)
        kosul("Odaklanan parcanin karti acildi (kaydirmadan SONRA da acik)", k1["gorunur"], k1["baslik"])
        tus(t, "Tab", 9)
        t.bekle(0.25)
        k2 = kart(t)
        kosul("Tab sonraki parcaya gecince kart DEGISTI", k2["gorunur"] and k2["k"] != k1["k"], f"{k1['k']} -> {k2['k']}")
        tus(t, "Escape", 27)
        t.bekle(0.2)

        # ── 2B: kesim listesi satiri ────────────────────────────────────
        print("\n  2B · kesim listesi (adim 4.3)")
        adima_git(t, "4.3")
        kapali = merkez(t, '.aa:not([hidden]) [data-bi^="kl:"]')
        kosul("Kesim cizimi kapali bolumdeyken hedef alinmiyor (gorunurluk suzgeci)", kapali is None, str(kapali))
        # kullanicinin yaptigi gibi: "Parcalari cubuk ustunde gor" bolumunu ac
        t.js("""[].forEach.call(document.querySelectorAll('.aa:not([hidden]) details.ayrinti'), function(d){
                  if (d.querySelector('[data-bi^="kl:"]')) d.open = true; })""")
        t.bekle(0.2)
        m = merkez(t, '.aa:not([hidden]) [data-bi^="kl:"]')
        kosul("4.3'te kesim cizimi parcalari kart tasiyor (bolum acilinca)", m is not None)
        if m:
            fare(t, m["x"], m["y"])
            t.bekle(0.25)
            k = kart(t)
            satir = dict(k["satir"])
            kosul("Kesim satirinin kartinda UZUNLUK ve ADET var", k["gorunur"] and satir.get("Uzunluk", "").endswith("mm")
                  and satir.get("Adet", "").startswith("×"), f"{k['baslik']}: {satir.get('Uzunluk')} {satir.get('Adet')}")
            fare(t, 5, 5)
            t.bekle(0.2)

        # ── 3B: WebGL gorunumde isin secimi ─────────────────────────────
        print("\n  3B · WebGL gorunum")
        adima_git(t, "6.2")
        gl = t.js("""(function(){
          var g = document.getElementById('uc-govde');
          if (g.hidden) document.getElementById('uc-katla').click();
          var tv = document.getElementById('uc-tuval'); tv.scrollIntoView({block: 'center', behavior: 'instant'});
          return !!tv.getContext('webgl'); })()""")
        kosul("Tarayicida WebGL var (3B testi anlamli)", bool(gl))
        t.js("document.querySelector('[data-gorus=\"ust\"]').click()")
        t.js("var s = document.getElementById('uc-duvar'); s.value = 'saydam'; s.dispatchEvent(new Event('change'))")
        t.bekle(0.4)
        r = t.js("(function(){ var r = document.getElementById('uc-tuval').getBoundingClientRect();"
                 " return {x: r.left, y: r.top, w: r.width, h: r.height}; })()")
        # Ustten bakista kutunun ortasi (x 107, y 77) kart A'nin taban izinin icinde (x 13-128).
        cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
        fare(t, cx - 300, cy - 300)
        t.bekle(0.1)
        fare(t, cx, cy)
        t.bekle(0.35)
        k = kart(t)
        kosul("3B: parcanin uzerine gelince kart ACILIYOR", k["gorunur"], k["baslik"])
        kosul("3B: ustten ortada KART A secildi (isin en yakin kati govdeyi buluyor)",
              k["k"] == "p:A", f"{k['k']} · {k['baslik']}")
        # B59b: "ortada kart A" tek basina AYIRT EDICI degil — ortanin altinda yalniz taban (once
        # cizilir, uzak) ve A (sonra cizilir, yakin) var; "son cizileni sec" hatasi da A'yi bulur.
        # B59'da panel yeniden dizilince o mutasyon KACTI. Ayirt edici nokta: TP1 (sarj modulu,
        # B58d) kart A'nin arka seridinin ALTINDA ve A'dan SONRA ciziliyor -> dogru secim A,
        # hatali secim TP1. Olcek duzenden bagimsiz: kart A'nin kenarlari fareyle bulunur.
        def a_mi(x, y):
            fare(t, x, y)
            t.bekle(0.12)
            kk = kart(t)
            return kk["gorunur"] and kk["k"] == "p:A"

        def kenar(x0, y0, dx, dy):
            """(x0, y0) A'nin icinde; (dx, dy) yonunde A'dan cikilan mesafe (px), ikiye bolmeyle."""
            ic, dis = 0.0, None
            for n in range(1, 60):
                x, y = x0 + dx * 8 * n, y0 + dy * 8 * n
                if not (r["x"] < x < r["x"] + r["w"] and r["y"] < y < r["y"] + r["h"]):
                    return None
                if not a_mi(x, y):
                    dis = 8.0 * n
                    break
                ic = 8.0 * n
            if dis is None:
                return None
            for _ in range(5):
                orta = (ic + dis) / 2
                if a_mi(x0 + dx * orta, y0 + dy * orta):
                    ic = orta
                else:
                    dis = orta
            return (ic + dis) / 2
        a_x0, a_x1, a_y0, a_y1 = 13.0, 128.0, 27.0, 142.0        # kart A taban izi (sahne mm)
        sol, sag = kenar(cx, cy, -1, 0), kenar(cx, cy, 1, 0)
        kal = None
        if sol and sag:
            xl, sx = cx - sol, (sol + sag) / (a_x1 - a_x0)
            vx = xl + (30.0 - a_x0) * sx                          # x 30: A'nin ustunde baska govde yok
            yu, ya = kenar(vx, cy, 0, -1), kenar(vx, cy, 0, 1)
            if yu and ya:
                sy = (yu + ya) / (a_y1 - a_y0)
                # merkez satiri dunya y ~77: 142'ye (arka) 65 mm, 27'ye 50 mm -> uzak kenar arka
                y142, y27 = (cy - yu, cy + ya) if yu > ya else (cy + ya, cy - yu)
                tp = (xl + (62.0 - a_x0) * sx, y27 + (135.5 - a_y0) * (y142 - y27) / (a_y1 - a_y0))
                kal = (sx, sy, tp)
        kosul("3B: olcek kart A'nin kenarlarindan bulundu (x ve y ayni olcek, %10)",
              kal is not None and abs(kal[0] - kal[1]) / kal[0] < 0.10,
              f"{kal[0]:.2f} / {kal[1]:.2f} px/mm" if kal else "kenar bulunamadi")
        if kal:
            a_mi(*kal[2])
            k = kart(t)
            kosul("3B: TP1'in ustunde (A'dan SONRA cizilen, ALTTA kalan) yine KART A secildi",
                  k["gorunur"] and k["k"] == "p:A", f"{k['k']} · {k['baslik']}")
        fare(t, cx, cy)
        t.bekle(0.3)
        if GORUNTU:
            t.goruntu("_ipucu_3b.png")
        tikla(t, cx, cy)
        t.bekle(0.3)
        k = kart(t)
        kosul("3B: tiklayinca sabitlendi", k["gorunur"] and "sabitlendi" in k["ipucu"], k["ipucu"])
        t.js("document.getElementById('uc-tuval').focus()")
        tus(t, "n", 78, "n")
        t.bekle(0.3)
        k2 = kart(t)
        kosul("3B: N tusu sonraki parcaya geciyor", k2["gorunur"] and k2["k"] != k["k"] and "(N / P)" in k2["durum"],
              f"{k['k']} -> {k2['k']} · {k2['durum']}")
        tus(t, "p", 80, "p")
        t.bekle(0.3)
        k3 = kart(t)
        kosul("3B: P tusu geri donuyor", k3["k"] == k["k"], f"{k2['k']} -> {k3['k']}")
        tus(t, "Escape", 27)
        t.bekle(0.2)
        kosul("3B: Esc karti kapatiyor", not kart(t)["gorunur"])

        # Cubuk parcasi: on gorunumde (4.3) dis kat duvarinin ortasi -> uzunluk
        adima_git(t, "4.3")
        t.js("document.querySelector('[data-gorus=\"on\"]').click()")
        t.js("var s = document.getElementById('uc-duvar'); s.value = 'opak'; s.dispatchEvent(new Event('change'))")
        t.bekle(0.4)
        r = t.js("(function(){ var tv = document.getElementById('uc-tuval'); tv.scrollIntoView({block: 'center', behavior: 'instant'});"
                 " var r = tv.getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; })()")
        t.bekle(0.3)
        r = t.js("(function(){ var r = document.getElementById('uc-tuval').getBoundingClientRect();"
                 " return {x: r.left, y: r.top, w: r.width, h: r.height}; })()")
        cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
        # B58e: once tam ortaya bakiliyordu — COM jaki panelin ortasina gelince (x 107, z 45)
        # isin jaka carpti. Nokta artik panel dizilimine bagli degil: ortadan yukari/asagi
        # taranir, ilk CUBUK karti alinir. "En yakin katman" iddiasinin gucu ayni: bozuk bir
        # secici o noktada da arka duvarin cubugunu dondurur.
        k = {"gorunur": False, "k": "", "satir": [], "baslik": ""}
        for dy in (0, 16, -16, 32, -32, 48, -48, 64, -64):
            fare(t, cx - 300, cy + dy)
            t.bekle(0.1)
            fare(t, cx, cy + dy)
            t.bekle(0.35)
            k = kart(t)
            if k["gorunur"] and k["k"].startswith("c:"):
                break
        satir = dict(k["satir"])
        kosul("3B: ondan duvara gelince CUBUK parcasi, kartta UZUNLUK var",
              k["gorunur"] and k["k"].startswith("c:") and satir.get("Uzunluk", "").endswith("mm"),
              f"{k['baslik']} · {satir.get('Uzunluk')}")
        # Onden bakista ayni noktayi DORT katman kapliyor: dis kat on (en yakin),
        # ic kat on, ic kat arka, dis kat arka. Isin EN YAKINI secmeli. Ustten
        # bakistaki kart A testi bunu ayiramiyor (orada en yakin = en son cizilen).
        kosul("3B: isin EN YAKIN katmani seciyor (on dis kat, arkadaki ic kat degil)",
              k["k"].startswith("c:Dış kat — ön duvar"), k["k"])
        kosul("3B: cubugun kartinda kesim listesindeki satiri yaziyor",
              "Kesim listesi" in satir and "⚠" not in satir.get("Kesim listesi", ""), satir.get("Kesim listesi", ""))
        # ── B73: kablolar — uzerine gel (kart) ve tablo satiri (cizimde secili) ──
        tus(t, "Escape", 27)
        adima_git(t, "10.4")
        m = merkez(t, "svg g.kb:has(circle.kno-r)")     # rozet: L bicimli cizginin kutu ortasi bos olabilir
        kosul("B73: 10.4'te çizimde kablo var", m is not None)
        if m:
            fare(t, m["x"], m["y"])
            t.bekle(0.2)
            kk = kart(t)
            kosul("B73: kablonun üzerine gelince kablo kartı açılıyor",
                  kk["gorunur"] and kk["k"].startswith("t:") and "→" in kk["baslik"]
                  and any(r[0] == "Kesim boyu" for r in kk["satir"]), str(kk)[:160])
            tus(t, "Escape", 27)
        r = merkez(t, "tr.bi-satir")
        kosul("B73: 10.4'te kablo tablosu var", r is not None)
        if r:
            tikla(t, r["x"], r["y"])
            t.bekle(0.3)
            d = t.js("""(function(){ var tr = document.querySelector('tr.bi-satir.secili'); if (!tr) return null;
              var k = tr.getAttribute('data-bi');
              var n = document.querySelectorAll('svg [data-bi="' + CSS.escape(k) + '"].secili').length;
              var i = document.getElementById('ipucu');
              return {k: k, svg: n, kart: !i.hidden && i.dataset.k === k}; })()""")
            kosul("B73: tablo satırına dokununca kart açılıyor ve çizimdeki aynı kablo seçili",
                  bool(d) and d["svg"] >= 1 and d["kart"], str(d))
            tus(t, "Escape", 27)
            n_sec = t.js("document.querySelectorAll('.secili').length")
            kosul("B73: Esc bütün seçimleri temizliyor (satır + çizim)", n_sec == 0, str(n_sec))

        # ── B73 gozden gecirme: satira dokununca kablo GORUNUR olmali (yapiskan baslik ortmesin)
        # ve kart EKRANDA kalmali. Ilk surum kabloyu basligin altina kaydiriyor, karti ekran
        # disindaki satira bagliyordu; yukaridaki iddia yalniz '!hidden'e baktigi icin yesildi.
        def satir_dene(W: int, H: int, hangi: int) -> tuple[str, dict]:
            t.cagir("Emulation.setDeviceMetricsOverride", {"width": W, "height": H, "deviceScaleFactor": 1, "mobile": False})
            t.bekle(0.4)
            adima_git(t, "10.4")
            r = t.js(f"""(function(){{
              var L = [].filter.call(document.querySelectorAll('.aa:not([hidden]) tr.bi-satir'),
                                     function(x){{ return x.getClientRects().length; }});
              var tr = L[{hangi} < 0 ? L.length + {hangi} : {hangi}];
              tr.scrollIntoView({{block: 'center', behavior: 'instant'}});
              var b = tr.getBoundingClientRect();
              return {{x: Math.min(b.left + 20, {W} - 10), y: b.top + b.height / 2, k: tr.getAttribute('data-bi')}}; }})()""")
            t.bekle(0.3)
            tikla(t, r["x"], r["y"])
            t.bekle(0.4)
            d = t.js(f"""(function(){{
              var i = document.getElementById('ipucu'), b = i.getBoundingClientRect();
              var c = [].filter.call(document.querySelectorAll('svg .secili circle.kno-r'),
                                     function(e){{ return e.getClientRects().length && !e.closest('details:not([open])'); }});
              var hit = null;
              if (c.length) {{
                var cb = c[0].getBoundingClientRect(), x = cb.left + cb.width / 2, y = cb.top + cb.height / 2;
                var h = document.elementFromPoint(x, y), g = h && h.closest('[data-bi]');
                hit = {{y: Math.round(y), k: g ? g.getAttribute('data-bi') : (h ? h.tagName + '.' + h.className : null)}};
              }}
              return {{kart: !i.hidden && b.bottom > 0 && b.top < {H} && b.right > 0 && b.left < {W},
                      kart_y: [Math.round(b.top), Math.round(b.bottom)], rozet: hit}}; }})()""")
            tus(t, "Escape", 27)
            t.bekle(0.2)
            return r["k"], d
        for W, H, hangi, ad in ((390, 800, 6, "telefon, 7. satır"), (390, 800, -1, "telefon, son satır"),
                                (1280, 900, -1, "masaüstü, son satır")):
            k_, d = satir_dene(W, H, hangi)
            kosul(f"B73: {ad}: satıra dokununca kart EKRANDA ve çizimdeki kablo GÖRÜNÜR (başlığın altında değil)",
                  d["kart"] and d["rozet"] is not None and d["rozet"]["k"] == k_, f"{d}"[:220])
        t.cagir("Emulation.clearDeviceMetricsOverride", {})
        t.bekle(0.4)
        # Kablo EKRANDA ama yapiskan basligin ALTINDA, satir da gorunur: yalniz "ekran disi mi"
        # bakan bir kontrol bunu kacirir (mutasyon kosucusu yakaladi) — kablo yine kaydirilmali.
        adima_git(t, "10.4")
        kur = t.js("""(function(){
          var L = [].filter.call(document.querySelectorAll('.aa:not([hidden]) tr.bi-satir'),
                                 function(x){ return x.getClientRects().length; });
          var bas = document.querySelector('.gorus').getBoundingClientRect().bottom;
          for (var i = 0; i < L.length; i++) {
            var k = L[i].getAttribute('data-bi');
            var c = [].filter.call(document.querySelectorAll('svg [data-bi=' + JSON.stringify(k) + '] circle.kno-r'),
                                   function(e){ return e.getClientRects().length && !e.closest('details:not([open])'); })[0];
            if (!c) continue;
            var cy = c.getBoundingClientRect().top + scrollY, ry = L[i].getBoundingClientRect().top + scrollY;
            var hedef = cy - bas / 2;                       // rozet basligin ortasina gelsin
            if (ry - hedef + 30 < innerHeight) {
              window.scrollTo({top: hedef, behavior: 'instant'});
              var b = L[i].getBoundingClientRect();
              return {k: k, x: b.left + 20, y: b.top + b.height / 2, bas: Math.round(bas)};
            }
          }
          return null; })()""")
        kosul("B73: kablo başlığın altında + satır görünür düzeni kuruldu", kur is not None, str(kur))
        if kur:
            t.bekle(0.3)
            tikla(t, kur["x"], kur["y"])
            t.bekle(0.4)
            g = t.js("""(function(){
              var c = [].filter.call(document.querySelectorAll('svg .secili circle.kno-r'),
                                     function(e){ return e.getClientRects().length && !e.closest('details:not([open])'); })[0];
              if (!c) return null;
              var b = c.getBoundingClientRect(), h = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
              var gr = h && h.closest('[data-bi]');
              return gr ? gr.getAttribute('data-bi') : (h ? h.className : null); })()""")
            kosul("B73: başlığın altındaki kablo satıra dokununca görünür yere geliyor", g == kur["k"], f"{g}")
            tus(t, "Escape", 27)
            t.bekle(0.2)

        # ── B73 gozden gecirme: 3B'de kablo FAREYLE secilir; N/P bir kabloyu bir kez sayar ──
        import kutu as KU
        adima_git(t, "10.4")
        t.js("""(function(){ var g = document.getElementById('uc-govde');
                 if (g.hidden) document.getElementById('uc-katla').click();
                 document.getElementById('uc-tuval').scrollIntoView({block: 'center', behavior: 'instant'}); })()""")
        t.js("document.querySelector('[data-gorus=\"ust\"]').click()")
        t.js("var s = document.getElementById('uc-duvar'); s.value = 'saydam'; s.dispatchEvent(new Event('change'))")
        t.bekle(0.4)
        beklenen_kablo = len(KU.adim_kablolari("10.3")) + len(KU.adim_kablolari("10.4"))
        ozet3 = t.js("document.getElementById('uc-bilgi').textContent")
        kosul("B73: 3B özeti KABLO sayıyor (blok değil)", f"kablo {beklenen_kablo}" in ozet3,
              f"beklenen 'kablo {beklenen_kablo}' · {ozet3[:120]}")
        t.js("document.getElementById('uc-tuval').focus()")
        goruldu, sira_ = {}, []
        for _ in range(40):
            tus(t, "n", 78, "n")
            t.bekle(0.05)
            kk = kart(t)
            sira_.append(kk["k"])
            if kk["k"].startswith("t:"):
                goruldu[kk["k"]] = goruldu.get(kk["k"], 0) + 1
        bu_adim = {f"t:{k['a']}|{k['b']}" for k in KU.adim_kablolari("10.4")}
        kosul("B73: 3B N/P her kabloyu BİR kez geziyor (blok blok değil) ve bu adımın kablolarının hepsi listede",
              all(v == 1 for v in goruldu.values()) and bu_adim <= set(goruldu),
              f"tekrar: {[k for k, v in goruldu.items() if v > 1][:2]} · eksik {len(bu_adim - set(goruldu))}")
        tus(t, "Escape", 27)
        t.bekle(0.2)

        def blok_noktasi(kk_rect):
            """N ile secilen blogun ekran noktasi, kartin konumundan (ipKonum'un tersi)."""
            L, T_, w, h, W, H = kk_rect
            x = L - 16 if L - 16 + 16 + w <= W - 8 else L + w + 16
            y = T_ - 18 if T_ - 18 + 18 + h <= H - 8 else T_ + h + 12
            return x, y
        # Once N ile kablolarin ekran noktalari toplanir (Esc gezinmeyi basa sarar), sonra her
        # noktanin ustune gelinir: arka bolgede komsu kablo one cikabilir, en az biri KENDISI olmali.
        t.js("document.getElementById('uc-tuval').focus()")
        noktalar = []
        for _ in range(40):
            tus(t, "n", 78, "n")
            t.bekle(0.06)
            kk = kart(t)
            if kk["k"].startswith("t:") and all(kk["k"] != n_[0] for n_ in noktalar):
                rect = t.js("(function(){ var b = document.getElementById('ipucu').getBoundingClientRect();"
                            " return [b.left, b.top, b.width, b.height, innerWidth, innerHeight]; })()")
                noktalar.append((kk["k"], blok_noktasi(rect)))
        tus(t, "Escape", 27)
        secildi = []
        for k_, (x, y) in noktalar:
            fare(t, x - 200, y - 200)
            t.bekle(0.05)
            fare(t, x, y)
            t.bekle(0.3)
            hv = kart(t)
            if hv["gorunur"] and hv["k"] == k_:
                secildi.append(k_)
        kosul("B73: 3B'de kablo FAREYLE seçilebiliyor (üzerine gelince kendi kartı)", bool(secildi),
              f"{len(secildi)}/{len(noktalar)} kablo kendi noktasında")
        fare(t, 5, 5)
        tus(t, "Escape", 27)

        # ── B73: kablolari goster / gizle (kullanici istegi) — 2B + 3B tek ayar, hatirlanir ──
        def kablo_durum():
            return t.js("""(function(){
              var gor = function(s){ return [].filter.call(document.querySelectorAll(s), function(e){
                  return e.getClientRects().length && !e.closest('details:not([open])'); }).length; };
              var c = [].filter.call(document.querySelectorAll('.kb-goster'), function(e){ return e.getClientRects().length; })[0];
              return {cizgi: gor('.aa:not([hidden]) svg .kb'), yazi: gor('.aa:not([hidden]) svg .kb-yazi'),
                      kutu: c ? c.checked : null, uc: document.getElementById('uc-kablo').checked,
                      ozet: document.getElementById('uc-bilgi').textContent}; })()""")
        adima_git(t, "10.4")
        once = kablo_durum()
        t.js("""(function(){ var c = [].filter.call(document.querySelectorAll('.kb-goster'), function(e){ return e.getClientRects().length; })[0];
                 c.scrollIntoView({block: 'center', behavior: 'instant'}); })()""")
        t.bekle(0.2)
        m = t.js("""(function(){ var c = [].filter.call(document.querySelectorAll('.kb-goster'), function(e){ return e.getClientRects().length; })[0];
                 var b = c.getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; })()""")
        tikla(t, m["x"], m["y"])
        t.bekle(0.3)
        gizli = kablo_durum()
        kosul("B73: 'kabloları göster' kapatılınca çizimde kablo, numara ve 'ön →' yazısı kalmıyor; 3B'de de kablo yok",
              once["cizgi"] > 0 and once["yazi"] > 0 and gizli["cizgi"] == 0 and gizli["yazi"] == 0
              and not gizli["uc"] and "kablo" not in gizli["ozet"], f"önce {once['cizgi']}/{once['yazi']} · sonra {gizli}"[:220])
        t.js("location.reload()")
        t.bekle(1.5)
        adima_git(t, "10.4")
        yeni = kablo_durum()
        kosul("B73: gizleme ayarı sayfa yenilenince hatırlanıyor", yeni["cizgi"] == 0 and yeni["kutu"] is False, str(yeni)[:160])
        t.js("var c = document.getElementById('uc-kablo'); c.checked = true; c.dispatchEvent(new Event('change', {bubbles: true}))")
        t.bekle(0.3)
        acik = kablo_durum()
        kosul("B73: 3B'deki 'kablolar' kutusu açınca çizimlerde de geri geliyor (tek ayar)",
              acik["cizgi"] > 0 and acik["kutu"] is True and "kablo" in acik["ozet"], str(acik)[:160])
        kosul("Test boyunca JS hatasi yok", not t.hatalar(), "; ".join(t.hatalar())[:300])

    # ozet satiri sayim.py'nin bicimi: mutasyon kosucusu sayiyi buradan okur
    print(f"\n  OZET\n  {gecti}/{gecti + kaldi} dogrulama gecti")
    return kaldi


if __name__ == "__main__":
    raise SystemExit(main())
