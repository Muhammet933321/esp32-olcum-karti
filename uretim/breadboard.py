# -*- coding: utf-8 -*-
"""Breadboard baglanti semasi ciker (SVG).

Her adim icin ayri bir cizim; delik delik nereye ne takilacagini gosterir.
Koordinat sistemi gercek breadboard olculerinde: delik araligi 2.54 mm.
"""
from __future__ import annotations

from pathlib import Path

CIKTI = Path(__file__).parent.parent / "gorsel"
CIKTI.mkdir(exist_ok=True)

ADIM = 26              # delik araligi (piksel)
SOL = 74               # ilk sutunun x'i
UST = 58               # ust rayin y'si
SUTUN = 30             # gosterilen sutun sayisi (yarim boy breadboard)

# satir adlari ve y konumlari
SATIRLAR = {
    "+": UST,
    "-": UST + ADIM,
    "A": UST + ADIM * 4.2,
    "B": UST + ADIM * 5.2,
    "C": UST + ADIM * 6.2,
    "D": UST + ADIM * 7.2,
    "E": UST + ADIM * 8.2,
    "F": UST + ADIM * 10.1,
    "G": UST + ADIM * 11.1,
    "H": UST + ADIM * 12.1,
    "I": UST + ADIM * 13.1,
    "J": UST + ADIM * 14.1,
    "=": UST + ADIM * 16.3,   # alt eksi ray
    "#": UST + ADIM * 17.3,   # alt arti ray
}

RENK = {
    "govde": "#e8e4da", "govde-k": "#cfc9bb",
    "delik": "#a8a294", "kanal": "#dcd7cb",
    "arti": "#d0342c", "eksi": "#2d5aa8",
    "yazi": "#3a3a3a", "soluk": "#7a7a7a",
    "tel-k": "#c8342c", "tel-s": "#1f4e9c", "tel-y": "#1a7f4b",
    "tel-t": "#d98324", "tel-m": "#7b3fa0",
    "direnc": "#c8a56b", "direnc-k": "#8a6e42",
    "ic": "#2b2b2b", "kondansator": "#3f6fb5",
}


def xy(satir: str, sutun: int) -> tuple[float, float]:
    return SOL + (sutun - 1) * ADIM, SATIRLAR[satir]


def cizim(baslik: str, ogeler: list[str], aciklama: list[tuple],
          netler: list[tuple] = (), sol_pay: int = 0) -> str:
    en = SOL + SUTUN * ADIM + 210 + sol_pay
    boy = SATIRLAR["#"] + ADIM * 2 + 34 + len(aciklama) * 21

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-sol_pay} 0 {en} {boy}" '
         f'font-family="IBM Plex Mono, ui-monospace, monospace">']

    # breadboard govdesi
    gy = UST - 22
    gboy = SATIRLAR["#"] + 22 - gy
    p.append(f'<rect x="{SOL-42}" y="{gy}" width="{SUTUN*ADIM+70}" height="{gboy}" '
             f'rx="6" fill="{RENK["govde"]}" stroke="{RENK["govde-k"]}" stroke-width="1.5"/>')
    # orta kanal
    ky = (SATIRLAR["E"] + SATIRLAR["F"]) / 2 - ADIM * .55
    p.append(f'<rect x="{SOL-42}" y="{ky}" width="{SUTUN*ADIM+70}" '
             f'height="{ADIM*1.1}" fill="{RENK["kanal"]}"/>')

    # guc rayi cizgileri
    for satir, renk in (("+", RENK["arti"]), ("-", RENK["eksi"]),
                        ("=", RENK["eksi"]), ("#", RENK["arti"])):
        y = SATIRLAR[satir]
        p.append(f'<line x1="{SOL-30}" y1="{y}" x2="{SOL+(SUTUN-1)*ADIM+22}" y2="{y}" '
                 f'stroke="{renk}" stroke-width="1.6" opacity=".5"/>')
        p.append(f'<text x="{SOL-38}" y="{y+5}" font-size="15" font-weight="600" '
                 f'fill="{renk}" text-anchor="end">{"+" if satir in "+#" else "−"}</text>')

    # net vurgulari — bir sutunun A-E (veya F-J) delikleri elektriksel olarak birdir
    for sutun, renk, ad, *bank in netler:
        alt = bool(bank) and bank[0] == "alt"
        x, _ = xy("A", sutun)
        y1, y2 = (SATIRLAR["F"], SATIRLAR["J"]) if alt else (SATIRLAR["A"], SATIRLAR["E"])
        p.append(f'<rect x="{x-9}" y="{y1-11}" width="18" height="{y2-y1+22}" '
                 f'rx="9" fill="{renk}" opacity=".16"/>')
        if ad:
            ey = y1 - 20 if alt else y2 + 30
            p.append(f'<text x="{x}" y="{ey}" font-size="10.5" font-weight="600" '
                     f'fill="{renk}" text-anchor="middle">{ad}</text>')

    # delikler
    for satir in SATIRLAR:
        for s in range(1, SUTUN + 1):
            x, y = xy(satir, s)
            p.append(f'<rect x="{x-3.6}" y="{y-3.6}" width="7.2" height="7.2" rx="1.4" '
                     f'fill="{RENK["delik"]}" opacity=".5"/>')

    # satir etiketleri
    for satir in "ABCDEFGHIJ":
        y = SATIRLAR[satir]
        p.append(f'<text x="{SOL-20}" y="{y+4.5}" font-size="12" '
                 f'fill="{RENK["soluk"]}" text-anchor="middle">{satir}</text>')
    # sutun numaralari
    for s in range(1, SUTUN + 1, 5):
        x, _ = xy("A", s)
        p.append(f'<text x="{x}" y="{SATIRLAR["#"]+24}" font-size="11" '
                 f'fill="{RENK["soluk"]}" text-anchor="middle">{s}</text>')

    p.extend(ogeler)

    # aciklama listesi
    ay = SATIRLAR["#"] + ADIM * 2 + 6
    for i, (renk, metin) in enumerate(aciklama):
        y = ay + i * 21
        p.append(f'<rect x="{SOL-42}" y="{y-8}" width="13" height="4" rx="2" fill="{renk}"/>')
        p.append(f'<text x="{SOL-22}" y="{y-2}" font-size="13" fill="currentColor">{metin}</text>')

    p.append("</svg>")
    return "\n".join(p)


# ───────────────────────────────────────────────────────── ogeler
def tel(s1, c1, s2, c2, renk, kavis=26, yatay_kaydir=0):
    """Iki delik arasi jumper kablo."""
    x1, y1 = xy(s1, c1)
    x2, y2 = xy(s2, c2)
    mx, my = (x1 + x2) / 2 + yatay_kaydir, (y1 + y2) / 2 - kavis
    return (f'<path d="M{x1},{y1} Q{mx},{my} {x2},{y2}" fill="none" '
            f'stroke="{renk}" stroke-width="3.4" stroke-linecap="round" opacity=".92"/>'
            f'<circle cx="{x1}" cy="{y1}" r="3.4" fill="{renk}"/>'
            f'<circle cx="{x2}" cy="{y2}" r="3.4" fill="{renk}"/>')


def direnc(s1, c1, s2, c2, etiket, kimlik):
    x1, y1 = xy(s1, c1)
    x2, y2 = xy(s2, c2)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    yatay = abs(x2 - x1) > abs(y2 - y1)
    gw, gh = (46, 15) if yatay else (15, 46)
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{RENK["direnc-k"]}" '
            f'stroke-width="2"/>'
            f'<circle cx="{x1}" cy="{y1}" r="3.4" fill="{RENK["direnc-k"]}"/>'
            f'<circle cx="{x2}" cy="{y2}" r="3.4" fill="{RENK["direnc-k"]}"/>'
            f'<rect x="{mx-gw/2}" y="{my-gh/2}" width="{gw}" height="{gh}" rx="4" '
            f'fill="{RENK["direnc"]}" stroke="{RENK["direnc-k"]}" stroke-width="1.2"/>'
            f'<text x="{mx}" y="{my-gh/2-6}" font-size="12.5" font-weight="600" '
            f'fill="currentColor" text-anchor="middle">{etiket}</text>'
            f'<text x="{mx}" y="{my+gh/2+14}" font-size="10.5" '
            f'fill="{RENK["soluk"]}" text-anchor="middle">{kimlik}</text>')


def to92(satir, sutun, pinler, etiket, kimlik):
    """TO-92 govde: uc bacak ardisik sutunlarda."""
    x, y = xy(satir, sutun)
    x2 = x + ADIM * 2
    mx = (x + x2) / 2
    ty = y - 30
    ogeler = [f'<path d="M{x-11},{ty+16} a15,15 0 0 1 {ADIM*2+22},0 L{x2+11},{ty+16} '
              f'L{x-11},{ty+16} Z" fill="{RENK["ic"]}"/>',
              f'<rect x="{x-11}" y="{ty+6}" width="{ADIM*2+22}" height="12" '
              f'fill="{RENK["ic"]}"/>']
    for i in range(3):
        px = x + i * ADIM
        ogeler.append(f'<line x1="{px}" y1="{ty+18}" x2="{px}" y2="{y}" '
                      f'stroke="{RENK["ic"]}" stroke-width="2.4"/>')
        ogeler.append(f'<circle cx="{px}" cy="{y}" r="3.6" fill="{RENK["ic"]}"/>')
        ogeler.append(f'<text x="{px}" y="{y+17}" font-size="11.5" font-weight="600" '
                      f'fill="currentColor" text-anchor="middle">{pinler[i]}</text>')
    ogeler.append(f'<text x="{mx}" y="{ty-2}" font-size="12.5" font-weight="600" '
                  f'fill="currentColor" text-anchor="middle">{etiket}</text>')
    ogeler.append(f'<text x="{mx+58}" y="{ty+14}" font-size="10.5" '
                  f'fill="{RENK["soluk"]}">{kimlik}</text>')
    return "".join(ogeler)


def diyot(s1, c1, s2, c2, etiket, kimlik, katot_ilk=True):
    """1N4148 — bant (katot) katot_ilk ise ilk uca yakin."""
    x1, y1 = xy(s1, c1); x2, y2 = xy(s2, c2)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    import math
    aci = math.degrees(math.atan2(y2 - y1, x2 - x1))
    bant = -7 if katot_ilk else 7
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{RENK["ic"]}" '
            f'stroke-width="2"/>'
            f'<circle cx="{x1}" cy="{y1}" r="3.4" fill="{RENK["ic"]}"/>'
            f'<circle cx="{x2}" cy="{y2}" r="3.4" fill="{RENK["ic"]}"/>'
            f'<g transform="translate({mx},{my}) rotate({aci})">'
            f'<rect x="-17" y="-6" width="34" height="12" rx="2.5" fill="#d9d2c4" '
            f'stroke="{RENK["ic"]}" stroke-width="1"/>'
            f'<rect x="{bant-2}" y="-6" width="4.5" height="12" fill="{RENK["ic"]}"/>'
            f'</g>'
            f'<text x="{mx}" y="{my-16}" font-size="12" font-weight="600" '
            f'fill="currentColor" text-anchor="middle">{etiket}</text>'
            f'<text x="{mx}" y="{my+24}" font-size="10.5" '
            f'fill="{RENK["soluk"]}" text-anchor="middle">{kimlik}</text>')


def dip(sutun, pin_adlari, etiket, kimlik):
    """DIP-8: pin 1-4 F satirinda, 5-8 E satirinda (kanali atlar)."""
    x1, _ = xy("F", sutun)
    x2, _ = xy("F", sutun + 3)
    ya, yb = SATIRLAR["E"], SATIRLAR["F"]
    o = [f'<rect x="{x1-13}" y="{ya-9}" width="{x2-x1+26}" height="{yb-ya+18}" '
         f'rx="3" fill="#23262b" stroke="#0f1114"/>',
         f'<path d="M{x1-13},{(ya+yb)/2-9} a9,9 0 0 0 0,18" fill="none" '
         f'stroke="#6b7280" stroke-width="1.6"/>']
    for i in range(4):                       # alt sira: pin 1-4
        px, _ = xy("F", sutun + i)
        o.append(f'<circle cx="{px}" cy="{yb}" r="3.6" fill="#c9ccd1"/>')
        o.append(f'<text x="{px}" y="{yb+17}" font-size="10.5" font-weight="600" '
                 f'fill="currentColor" text-anchor="middle">{pin_adlari[i]}</text>')
    for i in range(4):                       # ust sira: pin 8-5
        px, _ = xy("E", sutun + i)
        o.append(f'<circle cx="{px}" cy="{ya}" r="3.6" fill="#c9ccd1"/>')
        o.append(f'<text x="{px}" y="{ya-11}" font-size="10.5" font-weight="600" '
                 f'fill="currentColor" text-anchor="middle">{pin_adlari[7-i]}</text>')
    o.append(f'<text x="{(x1+x2)/2}" y="{(ya+yb)/2+4}" font-size="12" '
             f'font-weight="600" fill="#e6e9ee" text-anchor="middle">{etiket}</text>')
    o.append(f'<text x="{x2+20}" y="{(ya+yb)/2+4}" font-size="10.5" '
             f'fill="{RENK["soluk"]}">{kimlik}</text>')
    return "".join(o)


def kondansator(s1, c1, s2, c2, etiket, kimlik):
    x1, y1 = xy(s1, c1)
    x2, y2 = xy(s2, c2)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{RENK["ic"]}" '
            f'stroke-width="2"/>'
            f'<circle cx="{x1}" cy="{y1}" r="3.4" fill="{RENK["ic"]}"/>'
            f'<circle cx="{x2}" cy="{y2}" r="3.4" fill="{RENK["ic"]}"/>'
            f'<ellipse cx="{mx}" cy="{my}" rx="12" ry="14" fill="{RENK["kondansator"]}"/>'
            f'<text x="{mx+18}" y="{my-2}" font-size="12.5" font-weight="600" '
            f'fill="currentColor">{etiket}</text>'
            f'<text x="{mx+18}" y="{my+12}" font-size="10.5" '
            f'fill="{RENK["soluk"]}">{kimlik}</text>')


def uno_pin(satir, sutun, ad, renk, onek="UNO ", yon="sag"):
    """Tahtadan disari cikan kablo ucu. yon='sol' girisler icin."""
    x, y = xy(satir, sutun)
    if yon == "sag":
        ux = SOL + SUTUN * ADIM + 40
        kutu_x, hiza = ux, ux + 56
    else:
        ux = SOL - 118
        kutu_x, hiza = ux - 112, ux - 56
    return (f'<path d="M{x},{y} C{(x+ux)/2},{y} {(x+ux)/2},{y} {ux},{y}" fill="none" '
            f'stroke="{renk}" stroke-width="3.4" stroke-linecap="round"/>'
            f'<circle cx="{x}" cy="{y}" r="3.4" fill="{renk}"/>'
            f'<rect x="{kutu_x}" y="{y-11}" width="112" height="22" rx="4" fill="{renk}"/>'
            f'<text x="{hiza}" y="{y+5}" font-size="12.5" font-weight="600" '
            f'fill="#fff" text-anchor="middle">{onek}{ad}</text>')


# ═══════════════════════════════════ ADIM 2: TL431 referansi
def adim2() -> str:
    o = []
    # + ray -> C2  (kisa besleme kablosu)
    o.append(tel("+", 2, "C", 2, RENK["tel-k"], 16))
    # R1 1K yatay: C2 -> C6   (sutun 6 = dugum K)
    o.append(direnc("C", 2, "C", 6, "1 kΩ", "R029"))
    # TL431: K=6, A=7, REF=8  — A satirinda, govde ust seritte
    o.append(to92("A", 6, ("dış", "ANOT", "dış"), "TL431", "IC002"))
    # anot -> eksi ray, govdenin sagindan dolasarak
    o.append(tel("C", 7, "-", 14, RENK["tel-s"], 34))
    # REF -> K kisa kopru
    o.append(tel("E", 8, "E", 6, RENK["tel-y"], 20))
    # R2 220R yatay: D6 -> D12  (sutun 12 = dugum AREF)
    o.append(direnc("D", 6, "D", 12, "220 Ω", "R006"))
    # C1 100nF: A12 -> eksi ray
    o.append(kondansator("A", 12, "-", 12, "100 nF", "C008"))
    # Uno baglantilari
    o.append(uno_pin("+", 18, "5V", RENK["tel-k"]))
    o.append(uno_pin("-", 19, "GND", RENK["tel-s"]))
    o.append(uno_pin("E", 12, "AREF", RENK["tel-t"]))

    aciklama = [
        (RENK["tel-k"], "kırmızı — Uno 5V → + ray;  + ray → C2 (kısa kablo)"),
        (RENK["tel-s"], "mavi — Uno GND → − ray;  TL431 ORTA bacak C7 → − ray"),
        (RENK["tel-y"], "yeşil — dış bacak E8 → dış bacak E6   (ikisi de düğüm K)"),
        (RENK["tel-t"], "turuncu — AREF düğümü (E12) → Uno AREF pini"),
    ]
    netler = [
        (2, RENK["tel-k"], "+5V"),
        (6, "#7b3fa0", "K"),
        (7, RENK["tel-s"], "ANOT"),
        (8, "#7b3fa0", "K"),
        (12, RENK["tel-t"], "AREF"),
    ]
    return cizim("Adım 2 — TL431 referansı", o, aciklama, netler)


def adim3() -> str:
    o = []
    # rayları alta köprüle — tahta içinde, boş sütunlarda
    o.append(tel("+", 18, "#", 18, RENK["tel-k"], 0))
    o.append(tel("-", 19, "=", 19, RENK["tel-s"], 0))
    # ölçülecek gerilimin (+) ucu
    o.append(uno_pin("F", 2, "ÖLÇÜLECEK +", "#7b3fa0", onek="", yon="sol"))
    # R025 100K yatay: G2 -> G7
    o.append(direnc("G", 2, "G", 7, "100 kΩ", "R025"))
    # düğüm -> Uno A0
    o.append(uno_pin("F", 7, "A0", RENK["tel-t"]))
    # R032 10K: I7 -> alt eksi ray
    o.append(direnc("I", 7, "=", 7, "10 kΩ", "R032"))
    # C049 1nF: J7 -> alt eksi ray (sagdan)
    o.append(kondansator("J", 7, "=", 9, "1 nF", "C049"))
    # düğümü sağa uzat
    o.append(tel("H", 7, "H", 11, RENK["tel-y"], 15))
    # D2 alt kelepçe: katot J11 (düğüm) -> anot alt eksi ray
    o.append(diyot("J", 11, "=", 11, "D2", "D003", katot_ilk=True))
    # D1 üst kelepçe: anot G11 (düğüm) -> katot alt artı ray
    o.append(diyot("G", 11, "#", 14, "D1", "D003", katot_ilk=False))

    aciklama = [
        ("#7b3fa0", "mor — ölçülecek gerilimin (+) ucu → F2   (− ucu − raya)"),
        (RENK["tel-t"], "turuncu — bölücü düğümü (F7) → Uno A0"),
        (RENK["tel-y"], "yeşil — düğümü sağa uzatan köprü (H7 → H11)"),
        (RENK["tel-k"], "kırmızı — üst + ray → alt + ray   (sütun 18)"),
        (RENK["tel-s"], "mavi — üst − ray → alt − ray   (sütun 19)"),
    ]
    netler = [(2, "#7b3fa0", "GİRİŞ", "alt"),
              (7, RENK["tel-t"], "A0 düğümü", "alt"),
              (11, RENK["tel-t"], "aynı düğüm", "alt")]
    return cizim("Adım 3 — gerilim bölücü", o, aciklama, netler, sol_pay=250)


def adim4() -> str:
    o = []
    # LM358 — sutun 18..21, kanali atliyor
    o.append(dip(18, ("ÇIK", "−", "+", "GND", "+B", "−B", "ÇB", "V+"),
                 "LM358", "IC003"))
    # besleme
    o.append(tel("D", 18, "+", 18, RENK["tel-k"], 0))          # pin8 -> + ray
    o.append(tel("G", 21, "=", 21, RENK["tel-s"], 0))          # pin4 -> alt - ray
    o.append(kondansator("+", 24, "-", 24, "100 nF", "C008"))  # besleme bypass
    # cikisi sola uzat, geri besleme
    o.append(tel("G", 18, "G", 15, RENK["tel-y"], 14))
    o.append(direnc("H", 15, "H", 19, "47 kΩ", "R040"))
    o.append(direnc("I", 19, "=", 19, "6.8 kΩ", "R018"))
    # sont ve yuk donusu
    o.append(direnc("I", 26, "=", 26, "10 Ω", "R001"))
    o.append(uno_pin("F", 26, "YÜK −", "#7b3fa0"))
    o.append(tel("G", 26, "G", 20, RENK["tel-y"], 20))         # sont ustu -> pin3
    # cikis -> A1
    o.append(uno_pin("J", 15, "A1", RENK["tel-t"]))
    # kullanilmayan ikinci kat
    o.append(tel("C", 21, "-", 22, RENK["tel-s"], 12))         # +B -> GND
    o.append(tel("C", 20, "C", 19, RENK["tel-y"], 14))         # -B -> cikisB

    aciklama = [
        (RENK["tel-k"], "kırmızı — pin 8 (V+) → üst + ray"),
        (RENK["tel-s"], "mavi — pin 4 (GND) → alt − ray;  pin 5 (+B) → üst − ray"),
        (RENK["tel-y"], "yeşil — çıkışı sola uzat (G18→G15);  şönt üstü → pin 3;"
                        "  pin 6 → pin 7"),
        (RENK["tel-t"], "turuncu — LM358 çıkışı (J15) → Uno A1"),
        ("#7b3fa0", "mor — ölçülecek yükün (−) ucu → F26"),
    ]
    netler = [(15, RENK["tel-t"], "", "alt"), (18, RENK["tel-t"], "", "alt"),
              (19, "#7b3fa0", "", "alt"),
              (20, RENK["tel-y"], "", "alt"), (26, RENK["tel-y"], "", "alt")]
    return cizim("Adım 4 — şönt + LM358", o, aciklama, netler)


if __name__ == "__main__":
    (CIKTI / "breadboard-adim2.svg").write_text(adim2(), encoding="utf-8")
    (CIKTI / "breadboard-adim3.svg").write_text(adim3(), encoding="utf-8")
    (CIKTI / "breadboard-adim4.svg").write_text(adim4(), encoding="utf-8")
    print("yazildi: adim2 + adim3 + adim4")
