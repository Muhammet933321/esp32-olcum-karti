"""Panelin "ⓘ Bağlantı" penceresi — ön panel resmi + kısa talimat, VERİDEN.

    python baglanti.py            ortak/src/baglanti_veri.js'i yazar
    python baglanti.py --denetle  yazmaz: denetler + dosya GÜNCEL mi (zincir B73 bunu koşar)

Kullanıcı (2026-10-06): "hangi ölçümde hangi problar nereye takılmalı emin olamıyorum ...
sadece öğrenmek istediğim zaman için bir info yeri olsun". Kaynaklar TEK:
  * jakların yeri / rengi / etiketi  kutu_veri.PANEL_ON (kutu belgesi ve 3B ile aynı veri)
  * renklerin kendisi                kutu.JAK_RENK
  * menzil sayıları                  kutu.menziller() (tasarım sabitleri)
  * ölçüm başına kablolar + metin    kutu_veri.BAGLANTI_REHBER
Uzun kablo çizilmez (jakların üstünden geçip karışıyordu): kullanılan jak parlak + ①②③
rozeti, aşağıdaki çizimde aynı renk + aynı numara hedef ucunda.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
HEDEF = KOK / "ortak" / "src" / "baglanti_veri.js"
sys.path.insert(0, str(BURASI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import kutu  # noqa: E402
import kutu_veri as K  # noqa: E402

S = 2.0                      # px / mm
KENAR = 10.0
PANEL_EN = K.KUTU["ic_en"]   # ön panelin iç genişliği (mm) — jak x'leri buna göre
PANEL_YUK = kutu.olcu()["ic_yuk"]
G = KENAR * 2 + PANEL_EN * S
UST_Y = KENAR + 18           # jakların z ekseni başlangıcı (çerçeve 18 px yukarıdan: üst sıra etiketi)
ALT_Y = UST_Y + PANEL_YUK * S + 30    # devre çiziminin üst sınırı
YUK = ALT_Y + 205

YAZI = {
    "devre": ("ölçülen devre", "circuit under test"),
    "kaynak": ("Kaynak", "Source"), "kaynak_alt": ("pil / güç kaynağı", "battery / power supply"),
    "yuk": ("Yük", "Load"), "yuk_alt": ("ölçtüğün şey", "what you measure"),
    "arti_hat": ("+ tel olduğu gibi kalır — kutuya girmez", "+ wire stays as is — not into the box"),
    "sont": ("kutunun içinden (şönt)", "through the box (shunt)"),
    "kesik": ("− tel kesilir, iki ucu kutuya", "− wire is cut, both ends into the box"),
    "pil": ("Pil", "Battery"), "direnc": ("yük direnci", "load resistor"),
    "pil_arti": ("pilin + ucu: iki tel", "battery +: two wires"),
    "sinyal_k": ("Sinyal kaynağı", "Signal source"), "sinyal": ("sinyal", "signal"), "toprak": ("toprak", "ground"),
    "paralel": ("paralel — hiçbir tel kesilmez", "in parallel — no wire is cut"),
    "ic": ("CAL ↔ SKOP kısa kablo — dışarıda bir şey yok", "CAL ↔ SKOP short cable — nothing external"),
    "pencere": ("Nereye ne takılır", "What plugs where"),
    "kapat": ("Kapat", "Close"), "uyari": ("Dikkat", "Caution"),
    "panel": ("Kutunun ön paneli", "Front panel of the box"),
}
# Çizim türü -> kabloların bağlanabileceği uçlar (denetim BG2; yerleri hedef_svg'de).
UCLAR = {
    "devre": {"devre+", "devre-"},
    "akim": {"yuk-", "kaynak-"},
    "guc": {"yuk+", "yuk-", "kaynak-"},
    "pil": {"direnc", "pil-", "pil+"},
    "sinyal": {"toprak", "sinyal"},
    "ic": {"ic"},
}
EKRANLAR = ("canli", "pil", "skop")
IZINLI_ETIKET = {"b", "code"}


def _x(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _yazi(x, y, t, boy=12, renk="var(--yazi)", hiza="middle", kalin=False, ek="") -> str:
    k = ' font-weight="600"' if kalin else ""
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="{boy}" fill="{renk}" text-anchor="{hiza}"{k}{ek}>'
            f'{_x(t)}</text>')


def _rozet(x, y, n) -> str:
    return (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="var(--vurgu)"/>'
            + _yazi(x, y + 4, str(n), 11, "var(--vurgu-yazi)", kalin=True))


def jak_yeri(q: dict) -> tuple[float, float]:
    return KENAR + q["x"] * S, UST_Y + (PANEL_YUK - q["z"]) * S


def panel_svg(kullanilan: dict[str, int], ic_kablo: bool) -> str:
    """Ön panel: bütün öğeler gerçek yerinde; kullanılanlar parlak + numaralı."""
    o = [f'<rect x="{KENAR:.0f}" y="{UST_Y - 18:.0f}" width="{PANEL_EN * S:.0f}" height="{PANEL_YUK * S + 18:.0f}" '
         f'rx="10" fill="var(--zemin)" stroke="var(--kenar-koyu)" stroke-width="2"/>']
    for q in K.PANEL_ON:
        x, y = jak_yeri(q)
        no = kullanilan.get(q["ref"])
        sol = "" if no else ' opacity="0.3"'
        renk = kutu.JAK_RENK[q["renk"]]
        if q["ref"] == "SWP1":
            govde = (f'<rect x="{x - 9:.0f}" y="{y - 14:.0f}" width="18" height="28" rx="4" fill="{renk}" '
                     f'stroke="var(--kenar-koyu)"/><rect x="{x - 3:.0f}" y="{y - 12:.0f}" width="6" height="12" '
                     f'rx="2" fill="var(--yazi)"/>')
        elif q["ref"].startswith("LED"):
            govde = f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="{renk}"/>'
        else:
            r = q["metal_mm"] / 2 * S
            govde = (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{renk}" stroke="var(--kenar-koyu)" '
                     f'stroke-width="2"/><circle cx="{x:.0f}" cy="{y:.0f}" r="{r * 0.35:.0f}" fill="#111"/>')
        if no:
            govde = (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{q["metal_mm"] / 2 * S + 5:.0f}" fill="none" '
                     f'stroke="var(--vurgu)" stroke-width="3"/>' + govde)
        etiket = _yazi(x, y - q["metal_mm"] / 2 * S - 5, q["etiket"], 11, "var(--yazi)", kalin=True)
        o.append(f'<g data-jak="{q["ref"]}" data-kul="{1 if no else 0}" data-renk="{renk}"{sol}>{govde}{etiket}</g>')
        if no and not ic_kablo:
            o.append(_rozet(x + 17, y + 15, no))
    if ic_kablo:
        on = {q["ref"]: q for q in K.PANEL_ON}
        (x1, y1), (x2, y2) = jak_yeri(on["CAL"]), jak_yeri(on["J4.1"])
        o.append(f'<path data-kablo="ic" d="M{x1:.0f} {y1 + 14:.0f} C{x1:.0f} {y1 + 40:.0f} {x2:.0f} {y2 + 40:.0f} '
                 f'{x2:.0f} {y2 + 14:.0f}" fill="none" stroke="#2b2b2b" stroke-width="5" stroke-linecap="round"/>')
    return "".join(o)


def hedef_svg(hedef: str, uc_jak: dict[str, tuple[str, int]], d: int) -> str:
    """Panelin altındaki DEVRE ŞEMASI: kutunun jakları renkli + numaralı uç olarak devreye girer.
    Kablolar jak renginde, devrenin kendi telleri soluk; akım yönü oklarla."""
    y0 = ALT_Y + 8
    o = []
    TEL = "var(--soluk)"

    def tel(*n, renk=TEL, k=3.0):
        o.append(f'<path d="M{n[0][0]:.0f} {n[0][1]:.0f} ' + " ".join(f"L{x:.0f} {y:.0f}" for x, y in n[1:])
                 + f'" fill="none" stroke="{renk}" stroke-width="{k}" stroke-linejoin="round" stroke-linecap="round"/>')

    def nokta(x, y):
        o.append(f'<circle data-dugum="1" cx="{x:.0f}" cy="{y:.0f}" r="4.5" fill="var(--yazi)"/>')

    def ok_(x, y, yon):                         # akim yonu: 'sag' | 'sol' | 'asagi' | 'yukari'
        a = {"sag": (6, 0), "sol": (-6, 0), "asagi": (0, 6), "yukari": (0, -6)}[yon]
        b = (-a[1], a[0])
        o.append(f'<path data-ok="1" d="M{x + a[0]:.0f} {y + a[1]:.0f} L{x - a[0] + b[0] * .8:.0f} {y - a[1] + b[1] * .8:.0f} '
                 f'L{x - a[0] - b[0] * .8:.0f} {y - a[1] - b[1] * .8:.0f} Z" fill="var(--amper)"/>')

    def pil_(x, yu, ya, ad, alt=None, sag=True):
        """Dik pil sembolü: üst uç +, alt uç −; uzun levha +."""
        ym = (yu + ya) / 2
        tel((x, yu), (x, ym - 7))
        tel((x, ym + 7), (x, ya))
        o.append(f'<line x1="{x - 16}" y1="{ym - 7:.0f}" x2="{x + 16}" y2="{ym - 7:.0f}" stroke="var(--yazi)" stroke-width="3"/>')
        o.append(f'<line x1="{x - 8}" y1="{ym + 7:.0f}" x2="{x + 8}" y2="{ym + 7:.0f}" stroke="var(--yazi)" stroke-width="5"/>')
        ix, ih = (x - 22, "end") if sag else (x + 22, "start")      # +/− isareti adin KARSI tarafinda
        o.append(_yazi(ix, ym - 10, "+", 14, "var(--yazi)", ih, True))
        o.append(_yazi(ix, ym + 16, "−", 14, "var(--yazi)", ih, True))
        hx, hz = (x + 24, "start") if sag else (x - 30, "end")
        o.append(_yazi(hx, ym + 2, ad, 13, "var(--yazi)", hz, True))
        if alt:
            o.append(_yazi(hx, ym + 17, alt, 10, "var(--soluk)", hz))

    def yuk_(x, yu, ya, ad, alt):
        o.append(f'<rect x="{x - 15}" y="{yu:.0f}" width="30" height="{ya - yu:.0f}" rx="4" fill="var(--kart)" '
                 f'stroke="var(--yazi)" stroke-width="2.5"/>')
        o.append(_yazi(x + 24, (yu + ya) / 2 + 2, ad, 13, "var(--yazi)", "start", True))
        o.append(_yazi(x + 24, (yu + ya) / 2 + 17, alt, 10, "var(--soluk)", "start"))

    def direnc_(x1, x2, y):
        n = 8
        adim = (x1 - x2) / n
        zz = " ".join(f"L{x1 - adim * (i + .5):.0f} {y + (-7 if i % 2 == 0 else 7)}" for i in range(n))
        o.append(f'<path data-direnc="1" d="M{x1} {y} {zz} L{x2} {y}" fill="none" stroke="var(--yazi)" '
                 f'stroke-width="2.5" stroke-linejoin="round"/>')

    uc = {}                                      # uc adi -> (x, y): jak isaretcisinin yeri

    if hedef in ("akim", "guc"):
        yu, ya, yt, yb = y0 + 54, y0 + 106, y0 + 26, y0 + 146
        xy, xk = 70, 380                          # yük solda, kaynak sağda (panelde YÜK 1 solda)
        yuk_(xy, yu, ya, YAZI["yuk"][d], YAZI["yuk_alt"][d])
        pil_(xk, yu, ya, YAZI["kaynak"][d], YAZI["kaynak_alt"][d], sag=False)
        tel((xy, yu), (xy, yt), (xk, yt), (xk, yu))                    # + hattı: doğrudan
        ok_(240, yt, "sol")
        o.append(_yazi(240, yt - 8, YAZI["arti_hat"][d], 10, "var(--soluk)"))
        tel((xy, ya), (xy, yb), (172, yb))                            # yükün − → YÜK 1
        tel((276, yb), (xk, yb), (xk, ya))                            # YÜK 2 → kaynağın −
        o.append(f'<rect data-sont="1" x="160" y="{yb - 9}" width="128" height="22" rx="8" fill="none" '
                 f'stroke="var(--vurgu)" stroke-width="2" stroke-dasharray="5 4"/>')
        tel((172, yb), (276, yb), renk="var(--vurgu)", k=2)
        ok_(120, yb, "sag"); ok_(330, yb, "sag")
        o.append(_yazi(224, yb + 28, YAZI["sont"][d], 10, "var(--vurgu)"))
        o.append(_yazi(224, yb + 41, YAZI["kesik"][d], 10, "var(--soluk)"))
        uc["yuk-"], uc["kaynak-"] = (172, yb), (276, yb)
        if hedef == "guc":
            nokta(xy + 60, yt)
            tel((xy + 60, yt), (xy + 60, y0 + 2))
            uc["yuk+"] = (xy + 60, y0 + 2)
    elif hedef == "pil":
        xp, yu, ya = 330, y0 + 52, y0 + 112
        yj, yb = y0 + 22, y0 + 150
        pil_(xp, yu, ya, YAZI["pil"][d])
        tel((xp, yu), (xp, yj))
        nokta(xp, yj)
        o.append(_yazi(xp + 8, yj + 20, YAZI["pil_arti"][d], 10, "var(--soluk)", "start"))
        tel((xp, yj), (410, yj))                                       # + → V
        tel((xp, yj), (262, yj))                                       # + → direnç
        direnc_(262, 176, yj)
        o.append(_yazi(219, yj + 24, YAZI["direnc"][d], 10, "var(--soluk)"))
        tel((176, yj), (90, yj))                                       # direnç → PİL 1
        ok_(140, yj, "sol")
        tel((xp, ya), (xp, yb), (170, yb))                             # − → PİL 2
        ok_(250, yb, "sag")                                            # PİL 2'den pilin −'sine döner
        uc["pil+"], uc["direnc"], uc["pil-"] = (410, yj), (90, yj), (170, yb)
    elif hedef == "devre":
        yu, ya, yt, yb = y0 + 50, y0 + 110, y0 + 26, y0 + 146
        pil_(60, yu, ya, "", None)
        yuk_(230, yu, ya, YAZI["devre"][d].capitalize(), "")
        tel((60, yu), (60, yt), (230, yt), (230, yu))
        tel((60, ya), (60, yb), (230, yb), (230, ya))
        nokta(230, yt); nokta(230, yb)
        tel((230, yt), (360, yt)); tel((230, yb), (360, yb))
        o.append(_yazi(145, yb + 20, YAZI["paralel"][d], 10, "var(--soluk)"))
        uc["devre+"], uc["devre-"] = (360, yt), (360, yb)
    elif hedef == "sinyal":
        xs, ym = 330, y0 + 82
        yt, yb = y0 + 26, y0 + 146
        o.append(f'<circle cx="{xs}" cy="{ym}" r="24" fill="var(--kart)" stroke="var(--yazi)" stroke-width="2.5"/>'
                 f'<path d="M{xs - 14} {ym} C{xs - 9} {ym - 14} {xs - 3} {ym - 14} {xs} {ym} '
                 f'S{xs + 9} {ym + 14} {xs + 14} {ym}" fill="none" stroke="var(--volt)" stroke-width="2.5"/>')
        o.append(_yazi(xs - 32, ym + 4, YAZI["sinyal_k"][d], 12, "var(--yazi)", "end", True))
        tel((xs, ym - 24), (xs, yt), (400, yt))
        tel((xs, ym + 24), (xs, yb), (224, yb))
        o.append(_yazi(xs + 8, yt - 8, YAZI["sinyal"][d], 10, "var(--soluk)", "start"))
        o.append(_yazi(xs - 8, yb - 8, YAZI["toprak"][d], 10, "var(--soluk)", "end"))
        uc["sinyal"], uc["toprak"] = (400, yt), (224, yb)
    elif hedef == "ic":
        o.append(_yazi(G / 2, y0 + 40, YAZI["ic"][d], 12, "var(--soluk)"))

    for ad, (ref, no) in uc_jak.items():
        if ad not in uc:
            continue
        x, y = uc[ad]
        q = next(p for p in K.PANEL_ON if p["ref"] == ref)
        renk = kutu.JAK_RENK[q["renk"]]
        # jak ucu: renkli fiş + numara + jak adı (paneldeki numarayla aynı)
        o.append(f'<g data-uc="{ad}" data-jak="{ref}" data-renk="{renk}">'
                 f'<circle cx="{x}" cy="{y}" r="8" fill="{renk}" stroke="var(--kenar-koyu)" stroke-width="2"/>'
                 + _rozet(x, y - 19, no)
                 + _yazi(x + 13, y - 15, q["etiket"], 11, "var(--yazi)", "start", True) + "</g>")
    return "".join(o)


def sema(r: dict, d: int) -> str:
    kullanilan, uc_jak = {}, {}
    for ref, uc in r["kablolar"]:
        if ref not in kullanilan:
            kullanilan[ref] = len(kullanilan) + 1
        uc_jak[uc if r["hedef"] != "ic" else f"ic{ref}"] = (ref, kullanilan[ref])
    ic = r["hedef"] == "ic"
    govde = panel_svg(kullanilan, ic) + hedef_svg(r["hedef"], {} if ic else uc_jak, d)
    ad = f'{YAZI["panel"][d]} — {r["baslik"][d]}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {G:.0f} {YUK:.0f}" role="img" '
            f'aria-label="{_x(ad)}" font-family="system-ui, sans-serif" data-sema="{r["kimlik"]}">{govde}</svg>')


def metin(t: str) -> str:
    return t.format(**{k: v for k, v in kutu.menziller().items() if isinstance(v, str)})


def uret() -> dict:
    cikti = {e: [] for e in EKRANLAR}
    for r in K.BAGLANTI_REHBER:
        cikti[r["ekran"]].append({
            "kimlik": r["kimlik"], "menzil": r["menzil"],
            "baslik": {"tr": r["baslik"][0], "en": r["baslik"][1]},
            "svg": {"tr": sema(r, 0), "en": sema(r, 1)},
            "satirlar": {"tr": [metin(s[0]) for s in r["satirlar"]], "en": [metin(s[1]) for s in r["satirlar"]]},
            "uyari": {"tr": metin(r["uyari"][0]), "en": metin(r["uyari"][1])} if r["uyari"] else None,
        })
    return {"ekranlar": cikti, "yazi": {k: {"tr": v[0], "en": v[1]} for k, v in YAZI.items()
                                         if k in ("pencere", "kapat", "uyari")}}


def js(v: dict) -> str:
    return ("/* ÜRETİLİYOR — uretim/baglanti.py (kaynak: uretim/kutu_veri.py BAGLANTI_REHBER + PANEL_ON).\n"
            "   ELLE DÜZENLEME: `python uretim/baglanti.py` ile yeniden üret; zincir (B73) bayatsa kırmızı. */\n"
            "export const BAGLANTI = " + json.dumps(v, ensure_ascii=False, indent=1) + ";\n")


# ── denetim ─────────────────────────────────────────────────────────────────
gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> bool:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))
    return kosul


def denetle(v: dict) -> None:
    on = {q["ref"]: q for q in K.PANEL_ON}
    R = {r["kimlik"]: r for r in K.BAGLANTI_REHBER}
    ok("BG1 her ekranın (Canlı, Pil testi, Osiloskop) en az bir bağlantı resmi var",
       all(v["ekranlar"][e] for e in EKRANLAR), str({e: len(v["ekranlar"][e]) for e in EKRANLAR}))
    yanlis_ref = [(r["kimlik"], ref) for r in K.BAGLANTI_REHBER for ref, _ in r["kablolar"] if ref not in on]
    yanlis_uc = [(r["kimlik"], uc) for r in K.BAGLANTI_REHBER for _, uc in r["kablolar"]
                 if r["hedef"] not in UCLAR or uc not in UCLAR[r["hedef"]]]
    ok("BG2 her kablonun jakı ön panelde (PANEL_ON) ve ucu o çizim türünde VAR", not yanlis_ref and not yanlis_uc,
       f"{yanlis_ref} {yanlis_uc}")
    # resim panel verisiyle aynı: her öğe bir kez, rengi PANEL_ON'daki, kullanılanlar tam olarak kablolar
    sorun = []
    for e in EKRANLAR:
        for k in v["ekranlar"][e]:
            svg = k["svg"]["tr"]
            g = re.findall(r'<g data-jak="([^"]+)" data-kul="(\d)" data-renk="([^"]+)"', svg)
            if sorted(x[0] for x in g) != sorted(on):
                sorun.append(f"{k['kimlik']}: panel öğeleri {sorted(x[0] for x in g)}")
            for ref, kul, renk in g:
                if renk != kutu.JAK_RENK[on[ref]["renk"]]:
                    sorun.append(f"{k['kimlik']}:{ref} renk {renk}")
            kul = {x[0] for x in g if x[1] == "1"}
            if kul != {ref for ref, _ in R[k["kimlik"]]["kablolar"]}:
                sorun.append(f"{k['kimlik']}: parlak {sorted(kul)}")
    ok("BG3 resimdeki her jak panel verisiyle AYNI (hepsi bir kez, renk PANEL_ON'dan); parlak olanlar tam "
       "olarak o ölçümün jakları", not sorun, "; ".join(sorun[:4]))
    uc_sorun = []
    for e in EKRANLAR:
        for k in v["ekranlar"][e]:
            r = R[k["kimlik"]]
            if r["hedef"] == "ic":
                if 'data-kablo="ic"' not in k["svg"]["tr"]:
                    uc_sorun.append(k["kimlik"])
                continue
            uclar = dict(re.findall(r'<g data-uc="([^"]+)" data-jak="([^"]+)"', k["svg"]["tr"]))
            if uclar != {uc: ref for ref, uc in r["kablolar"]}:
                uc_sorun.append(f"{k['kimlik']}: {uclar}")
    ok("BG4 alttaki çizimde her ucun rozeti DOĞRU jakı gösteriyor (CAL testinde panelde CAL–SKOP kablosu)",
       not uc_sorun, "; ".join(uc_sorun[:3]))
    # KULLANIM kurallarıyla çelişme yok (kutu belgesi + kart ile aynı kurallar)
    kab = {r["kimlik"]: {ref: uc for ref, uc in r["kablolar"]} for r in K.BAGLANTI_REHBER}
    ok("BG5 akım/güç: COM'a tel YOK (COM = YÜK 2; takılırsa şönt baypas), yükün − YÜK 1, kaynağın − YÜK 2",
       all("J1.2" not in kab[i] and kab[i].get("J3.1") == "yuk-" and kab[i].get("J3.2") == "kaynak-"
           for i in ("akim", "guc")) and kab["guc"].get("J1.1") == "yuk+", str({i: kab[i] for i in ("akim", "guc")}))
    ok("BG6 pil testi: pil + hiçbir PİL jakına DOĞRUDAN gitmez (PİL 1 = direnç ucu), pil − PİL 2, V pil +; "
       "YÜK ve COM boş",
       kab["pil"].get("J7.1") == "direnc" and kab["pil"].get("J7.2") == "pil-" and kab["pil"].get("J1.1") == "pil+"
       and not ({"J3.1", "J3.2", "J1.2"} & set(kab["pil"])), str(kab["pil"]))
    ok("BG7 yüksek gerilim HV jakından (V'den DEĞİL — 615 V R4'ü yakar) ve kartın HV menzili (1) bu sekmeyi seçer",
       "J2.1" in kab["hv"] and "J1.1" not in kab["hv"] and R["hv"]["menzil"] == 1
       and [r["kimlik"] for r in K.BAGLANTI_REHBER if r["menzil"] == 1] == ["hv"], str(kab["hv"]))
    ok("BG8 osiloskop SKOP + COM; CAL testi CAL ↔ SKOP (CAL HV'ye komşu değil, B59)",
       kab["skop"] == {"J4.1": "sinyal", "J1.2": "toprak"} and set(kab["cal"]) == {"CAL", "J4.1"})
    # metinler: iki dil, yer tutucu kalmamış, yalnız <b> <code>
    m_sorun = []
    for e in EKRANLAR:
        for k in v["ekranlar"][e]:
            parca = [k["baslik"]["tr"], k["baslik"]["en"]] + k["satirlar"]["tr"] + k["satirlar"]["en"]
            if k["uyari"]:
                parca += [k["uyari"]["tr"], k["uyari"]["en"]]
            if len(k["satirlar"]["tr"]) != len(k["satirlar"]["en"]) or not k["satirlar"]["tr"]:
                m_sorun.append(f"{k['kimlik']}: satır sayısı")
            for t in parca:
                if not t.strip() or "{" in t or "}" in t:
                    m_sorun.append(f"{k['kimlik']}: '{t[:40]}'")
                etiketler = set(re.findall(r"</?([a-zA-Z]+)", t))
                if etiketler - IZINLI_ETIKET:
                    m_sorun.append(f"{k['kimlik']}: etiket {etiketler - IZINLI_ETIKET}")
    ok("BG9 her metin TR + EN, dolu, yer tutucusu çözülmüş, yalnız <b>/<code> (v-html güvenli)", not m_sorun,
       "; ".join(m_sorun[:4]))
    mz = kutu.menziller()
    hepsi = json.dumps(v, ensure_ascii=False)
    ok("BG10 menzil sayıları tasarım sabitinden (normal, yüksek, akım, skop) metne girdi",
       all(mz[a] in hepsi for a in ("normal", "yuksek", "akim", "skop")),
       ", ".join(mz[a] for a in ("normal", "yuksek", "akim", "skop")))
    uyari = {r["kimlik"]: (r["uyari"] or ("", ""))[0].lower() for r in K.BAGLANTI_REHBER}
    ok("BG11 tehlikeli ölçümlerde uyarı var: HV (tek el + USB'yi PC'ye takma), akım (COM'a takma), pil (ters "
       "kutup + pil + doğrudan PİL'e gitmez)",
       "tek el" in uyari["hv"] and "usb" in uyari["hv"] and "com" in uyari["akim"]
       and "ters" in uyari["pil"] and "doğrudan" in uyari["pil"])
    ok("BG12 ortak/src/baglanti_veri.js GÜNCEL (kutu_veri'den yeniden üretilenle bayt bayt aynı)",
       HEDEF.exists() and HEDEF.read_text(encoding="utf-8") == js(v),
       "yok" if not HEDEF.exists() else "bayat — python uretim/baglanti.py")


def main(argv: list[str]) -> int:
    v = uret()
    if "--denetle" not in argv:
        HEDEF.write_text(js(v), encoding="utf-8", newline="\n")
        print(f"yazildi: {HEDEF.relative_to(KOK)} ({HEDEF.stat().st_size} B)")
    print("\n── Bağlantı penceresi (ön panel resmi + talimat)")
    denetle(v)
    print(f"\nbaglanti: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
