# -*- coding: utf-8 -*-
"""BELGELER/7-yerlesim.html — delikli plaket yerlesim plani (kullanici icin).

`yerlesim3.py` denetimi GECTIKTEN sonra cagirir; kendi basina calismaz.
Sayilarin hepsi `yerlesim3_veri.py`, `yerlesim3_teller.json` ve
`netlist3.net`'ten — elle yazilmis delik adi yok.

Sayfa LEGO kilavuzu gibi: her buyuk adim (0..8) `yerlesim3_adim`'in
urettigi kucuk alt adimlara bolunmus. Ustte sabit bir cizim alani o alt
adima yakinlasir: o adimin parcalari koyu, oncekiler soluk, sonrakiler
gorunmez. Parca takarken parca yuzu, iz/tel cekerken lehim yuzu.

Stil `belge-uret.py`'deki STIL'den METIN olarak okunuyor (modulu calistirmadan);
ikinci bir CSS kopyasi tutulmuyor.
"""
from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

import belge_menu as MN
import yerlesim3 as Y
import yerlesim3_veri as V

BURASI = Path(__file__).parent
P = 17          # bir delik adimi (px)
K = 30          # cizim kenar payi (etiketler)

AG_RENK = {
    "GND": "#3b3b38", "+3V3": "#d97a00", "+5V": "#d62828",
    "+12V": "#9c1c1c", "Net-(J6-Pin_1)": "#9c1c1c", "-12V": "#1f5fbf",
    "/VREF": "#15935e",
}
PALET = ["#2a78d6", "#e0662f", "#0f9e8c", "#8a55c8", "#b5651d", "#5f8f1f",
         "#d6336c", "#4b6cb7", "#a0522d", "#2e8b57"]
# Belgede agin okunur adi (netlistin otomatik adlari yerine)
AG_AD = {"Net-(J6-Pin_1)": "24V+ (sigorta öncesi)", "GND@kelvin": "S− Kelvin (GND'ye değmez)"}
RAYLAR = {"+12V", "-12V", "+5V", "+3V3", "/VREF", "Net-(J6-Pin_1)"}


def renk(ag: str) -> str:
    ag = ag.split("@")[0]
    if ag in AG_RENK:
        return AG_RENK[ag]
    if ag in V.ZINCIR:
        # zincir dugumleri: 617 V koyu bordo -> alt dugum acik pembe
        k = V.ZINCIR.index(ag) / (len(V.ZINCIR) - 1)
        r_, g_, b_ = (int(120 + 100 * k), int(0 + 90 * k), int(60 + 100 * k))
        return f"#{r_:02x}{g_:02x}{b_:02x}"
    return PALET[sum(ord(c) for c in ag) % len(PALET)]


BACAK_AD = {"B": "baz", "C": "kollektör", "E": "emiter", "G": "kapı", "PadG": "kapı"}


def kisa_ag(ag: str) -> str:
    """Netlistin otomatik adini okunur yapar: Net-(U3A-+) -> 'U3A + girişi'."""
    if ag in AG_AD:
        return AG_AD[ag]
    ag = ag.split("@")[0]
    if ag in AG_AD:
        return AG_AD[ag]
    if ag in V.ZINCIR:
        k = V.ZINCIR.index(ag)
        son = len(V.ZINCIR) - 1
        return ("HV girişi" if k == 0 else
                "HV alt düğüm (~1.7 V)" if k == son else f"HV düğüm {k}")
    m = re.fullmatch(r"Net-\((U\d+[A-Z])-([+-])\)", ag)
    if m:
        return f"{m.group(1)} {'+' if m.group(2) == '+' else '−'} girişi"
    m = re.fullmatch(r"Net-\(([A-Z]+\d+)-(B|C|E|G|PadG)\)", ag)
    if m:
        return f"{m.group(1)} {BACAK_AD[m.group(2)]}"
    m = re.fullmatch(r"Net-\(([A-Z]+\d+)-Pad(\d+)\)", ag)
    if m:
        return f"{m.group(1)} pin {m.group(2)}"
    m = re.fullmatch(r"Net-\((.+)\)", ag)
    return m.group(1) if m else ag.lstrip("/")


def stil() -> str:
    kaynak = (BURASI / "belge-uret.py").read_text(encoding="utf-8")
    return re.search(r'STIL = """(.*?)"""', kaynak, re.S).group(1)


def e(s) -> str:
    return html.escape(str(s))


# ═══════════════════════════════════════════════════════════════════════
#  SVG
# ═══════════════════════════════════════════════════════════════════════

GOVDE_RENK = {
    "R4": ("#e9d7b0", "#8a6e42"), "R5": ("#e9d7b0", "#8a6e42"),
    "R1D": ("#e9d7b0", "#8a6e42"), "C1": ("#8fb3e0", "#3d6aa8"),
    "C2": ("#8fb3e0", "#3d6aa8"), "C1x2": ("#8fb3e0", "#3d6aa8"),
    "C6": ("#c9a227", "#7a6112"), "CE": ("#34507d", "#1c2e4a"),
    "D3": ("#e9a178", "#8a4b2a"), "DIP8": ("#2b2b2b", "#000"),
    "TO92": ("#262626", "#000"), "TO220": ("#4a4a4a", "#111"),
    "SIG": ("#c8c8c8", "#6b6b6b"), "HDR10": ("#262626", "#000"),
    "ADS": ("#1d4fa0", "#0d2a5a"), "TEL": ("none", "none"),
}
KOYU = {"DIP8", "TO92", "TO220", "HDR10", "ADS", "CE"}


def kart_svg(kart: str, yuz: str, nl, parcalar, teller, kok_ag, ss) -> str:
    """ss: alt adim sirasi — {"parca": {ref: i}, "iz"/"tel": {(kart, j): i}}.
    Her ogede data-s (alt adim) ve data-a (buyuk adim) var; JS bunlarla boyar."""
    kb = V.KARTLAR[kart]
    W, H = kb["sutun"], kb["satir"]
    alt = yuz == "alt"

    def X(x):
        return K + ((W - 1 - x) if alt else x) * P + P / 2

    def Yp(y):
        return K + y * P + P / 2

    def ds(tur, anahtar, adim):
        return f'data-s="{ss[tur][anahtar]}" data-a="{adim}"'

    gen, yuk = 2 * K + W * P, 2 * K + H * P
    o = [f'<svg viewBox="0 0 {gen} {yuk}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="ui-monospace,Consolas,monospace" role="img" '
         f'data-w="{W}" data-h="{H}" data-p="{P}" data-k="{K}" data-alt="{int(alt)}" '
         f'aria-label="Kart {kart} {"lehim" if alt else "parça"} yüzü">']
    pid = f"d{kart}{yuz}"
    o.append(f'<defs><pattern id="{pid}" x="{K}" y="{K}" width="{P}" height="{P}" '
             f'patternUnits="userSpaceOnUse">'
             f'<circle cx="{P/2}" cy="{P/2}" r="{P*0.3:.1f}" fill="{"#c98a4b" if alt else "#c4a27a"}"/>'
             f'<circle cx="{P/2}" cy="{P/2}" r="{P*0.11:.1f}" fill="#3a2a1a"/></pattern></defs>')
    o.append(f'<rect x="{K - 6}" y="{K - 6}" width="{W * P + 12}" height="{H * P + 12}" '
             f'rx="6" fill="{"#c7a06a" if alt else "#dcc195"}"/>')
    o.append(f'<rect x="{K}" y="{K}" width="{W * P}" height="{H * P}" fill="url(#{pid})"/>')
    for cx, cy in Y.vida_merkezleri(kart):
        o.append(f'<circle cx="{X(cx)}" cy="{Yp(cy)}" r="{P * 0.95:.1f}" fill="#8a8a85" '
                 f'stroke="#555" stroke-width="1"><title>vida (M3)</title></circle>')
    # eksen etiketleri (yakinlasinca JS gorunen kenara kendi etiketlerini koyar)
    o.append('<g class="eksen">')
    for x in range(W):
        for yy in (K - 12, K + H * P + 20):
            o.append(f'<text x="{X(x)}" y="{yy}" font-size="8" text-anchor="middle" '
                     f'fill="#6b665c">{Y.sutun_adi(x)}</text>')
    for y in range(H):
        for xx, an in ((K - 9, "end"), (K + W * P + 9, "start")):
            o.append(f'<text x="{xx}" y="{Yp(y) + 3}" font-size="8" text-anchor="{an}" '
                     f'fill="#6b665c">{y + 1}</text>')
    o.append('</g>')

    if alt:
        # parca izleri (soluk) — lehim yuzunde yon bulmak icin
        for p in parcalar.values():
            if p.kart != kart or p.ayak == "TEL":
                continue
            x0, y0, x1, y1 = p.govde()
            a, b = sorted((X(x0), X(x1)))
            o.append(f'<g {ds("parca", p.ref, p.adim)}><rect x="{a:.1f}" y="{Yp(y0):.1f}" '
                     f'width="{b - a:.1f}" height="{Yp(y1) - Yp(y0):.1f}" fill="none" '
                     f'stroke="#5b4630" stroke-width=".8" stroke-dasharray="3 2" opacity=".55"/>'
                     f'<text x="{(a + b) / 2:.1f}" y="{(Yp(y0) + Yp(y1)) / 2 + 3:.1f}" '
                     f'font-size="7" text-anchor="middle" fill="#3a2a1a" opacity=".8">{e(p.ref)}</text></g>')
        for j, t in enumerate(teller.get(kart, [])):
            c = renk(t["ag"])
            ad = kisa_ag(t["ag"])
            if t["tur"] == "iz":
                nokta = " ".join(f"{X(h[0]):.1f},{Yp(h[1]):.1f}" for h in t["yol"])
                o.append(f'<polyline {ds("iz", (kart, j), t["adim"])} points="{nokta}" fill="none" '
                         f'stroke="{c}" stroke-width="{P * 0.36:.1f}" stroke-linecap="round" '
                         f'stroke-linejoin="round"><title>{e(ad)} · lehim izi · '
                         f'{Y.delik_adi(*t["yol"][0])} → {Y.delik_adi(*t["yol"][-1])}'
                         f'</title></polyline>')
            else:
                (ax, ay), (bx, by) = t["uclar"]
                x1_, y1_, x2_, y2_ = X(ax), Yp(ay), X(bx), Yp(by)
                mx, my = (x1_ + x2_) / 2, (y1_ + y2_) / 2
                dx, dy = x2_ - x1_, y2_ - y1_
                L = max(1.0, (dx * dx + dy * dy) ** 0.5)
                bx_, by_ = mx - dy / L * min(22, L * 0.25), my + dx / L * min(22, L * 0.25)
                o.append(f'<g {ds("tel", (kart, j), t["adim"])}><path d="M{x1_:.1f},{y1_:.1f} '
                         f'Q{bx_:.1f},{by_:.1f} {x2_:.1f},{y2_:.1f}" fill="none" stroke="{c}" '
                         f'stroke-width="2.6" stroke-dasharray="6 3"><title>{e(ad)} · YALITIMLI TEL · '
                         f'{Y.delik_adi(ax, ay)} → {Y.delik_adi(bx, by)}</title></path>'
                         f'<circle cx="{x1_:.1f}" cy="{y1_:.1f}" r="3" fill="{c}"/>'
                         f'<circle cx="{x2_:.1f}" cy="{y2_:.1f}" r="3" fill="{c}"/></g>')

    # parcalar (ust yuzde govde, iki yuzde de bacak)
    for p in sorted(parcalar.values(), key=lambda q: q.ayak == "ADS"):
        if p.kart != kart:
            continue
        g = [f'<g {ds("parca", p.ref, p.adim)} data-r="{e(p.ref)}">']
        deger = nl.deger.get(p.ref, "")
        if not alt and p.ayak != "TEL":
            x0, y0, x1, y1 = p.govde()
            dolgu, cizgi = GOVDE_RENK[p.ayak]
            saydam = ' fill-opacity=".82"' if p.ayak == "ADS" else ""
            g.append(f'<rect x="{X(x0):.1f}" y="{Yp(y0):.1f}" width="{(x1 - x0) * P:.1f}" '
                     f'height="{(y1 - y0) * P:.1f}" rx="{3 if p.ayak not in ("R4", "R5") else 6}" '
                     f'fill="{dolgu}"{saydam} stroke="{cizgi}" stroke-width="1">'
                     f'<title>{e(p.ref)} · {e(deger)}</title></rect>')
            g += _isaretler(p, X, Yp)
            yazi_renk = "#fff" if p.ayak in KOYU else "#2a1f12"
            cx, cy = (X(x0) + X(x1)) / 2, (Yp(y0) + Yp(y1)) / 2
            dikey = (y1 - y0) > (x1 - x0) * 1.6 and p.ayak not in ("ADS", "DIP8")
            if p.ayak == "CE":
                (ux, uy) = p._yer(0.5, 1.0)          # etiket alt yarida, + ustte
                cx, cy = X(ux), Yp(uy)
            if p.ayak in ("TO92", "TO220"):
                # bacaklar govdenin ortasindan gecer — etiket bacak sirasinin
                # OBUR yanina (govdenin genis tarafina), pedlerin ustune degil
                (ux, uy) = p._yer(1, -0.5 if p.ayak == "TO92" else -0.9)
                cx, cy = X(ux), Yp(uy)
                dikey = p.aci in (90, 270)
            don = f' transform="rotate(-90 {cx:.1f} {cy:.1f})"' if dikey else ""
            g.append(f'<text x="{cx:.1f}" y="{cy + 3:.1f}" font-size="{9 if p.ayak in KOYU else 7.5}" '
                     f'text-anchor="middle" fill="{yazi_renk}" font-weight="600"{don}>{e(p.ref)}</text>')
        for pid_, dl in p.delikler(nl).items():
            for d in dl:
                ag = kok_ag.get((kart, d), "")
                g.append(f'<circle cx="{X(d[0]):.1f}" cy="{Yp(d[1]):.1f}" r="{P * 0.27:.1f}" '
                         f'fill="{renk(ag) if ag else "#999"}" stroke="#fff" stroke-width="1">'
                         f'<title>{e(pid_)} · {e(kisa_ag(ag))} · {Y.delik_adi(*d)}</title></circle>')
        for d in p.bos_delikler():
            g.append(f'<circle cx="{X(d[0]):.1f}" cy="{Yp(d[1]):.1f}" r="{P * 0.2:.1f}" fill="none" '
                     f'stroke="#555" stroke-width="1.2"><title>gerginlik deliği — telin '
                     f'yalıtımı buradan geçer, lehimlenmez</title></circle>')
        g.append("</g>")
        o += g
    # kart disi tel etiketleri EN USTTE — govdelerin altinda kalmasin
    for p in parcalar.values():
        if p.kart != kart or p.ayak != "TEL":
            continue
        (d,) = p.delikler(nl)[f"{p.ref}.1"]
        etiket = V.TEL_ETIKET.get(p.ref, p.ref)
        yon = -1 if (X(d[0]) > K + W * P / 2) else 1
        o.append(f'<text {ds("parca", p.ref, p.adim)} x="{X(d[0]) + yon * 9:.1f}" y="{Yp(d[1]) - 7:.1f}" '
                 f'font-size="8.5" text-anchor="{"start" if yon > 0 else "end"}" fill="#1a1410" '
                 f'font-weight="700" paint-order="stroke" stroke="#e9dcc2" stroke-width="3" '
                 f'stroke-linejoin="round">{e(etiket)}</text>')
    o.append("</svg>")
    return "".join(o)


def _isaretler(p, X, Yp) -> list[str]:
    """Yon isaretleri: DIP centigi, TO-92 duz yuz, TO-220 tabi, + ve katot."""
    out = []

    def nokta(dx, dy):
        rx, ry = Y.dondur(dx, dy, p.aci)
        return X(p.x + rx), Yp(p.y + ry)

    if p.ayak == "DIP8":
        cx, cy = nokta(1.5, -0.47)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#dcc195"/>')
        px, py = nokta(0, 0)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{P * 0.42:.1f}" fill="none" '
                   f'stroke="#f5c518" stroke-width="1.5"/>')
    elif p.ayak == "TO92":
        a = nokta(-0.45, 0.8)
        b = nokta(2.45, 0.8)
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                   f'stroke="#f5c518" stroke-width="2.5"><title>düz (yazılı) yüz</title></line>')
    elif p.ayak == "TO220":
        a = nokta(-1.0, -1.4)
        b = nokta(3.0, -1.4)
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                   f'stroke="#bbb" stroke-width="4"><title>metal tab (arka)</title></line>')
    elif p.ayak == "CE":
        cx, cy = nokta(0, -1.0)
        out.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" font-size="11" text-anchor="middle" '
                   f'fill="#fff" font-weight="700">+</text>')
    elif p.ayak == "D3":
        a = nokta(1.05, -0.4)
        b = nokta(1.05, 0.4)
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                   f'stroke="#222" stroke-width="3"><title>katot bandı</title></line>')
    elif p.ayak in ("HDR10", "ADS"):
        px, py = nokta(0, 0)
        out.append(f'<rect x="{px - 5:.1f}" y="{py - 5:.1f}" width="10" height="10" fill="none" '
                   f'stroke="#f5c518" stroke-width="1.5"/>')
    return out


# ═══════════════════════════════════════════════════════════════════════
#  TABLOLAR
# ═══════════════════════════════════════════════════════════════════════

YON_AD = {(0, 1): "aşağı (satır no. artan)", (0, -1): "yukarı", (1, 0): "sağa",
          (-1, 0): "sola"}


def _yon_adi(aci, dx, dy):
    rx, ry = Y.dondur(dx, dy, aci)
    return YON_AD[(int(round(rx)), int(round(ry)))]


def parca_satiri(p, nl) -> str:
    anah = p.pin_anahtarlari(nl)
    parcalar_ = []
    for k, konum in p.a["pin"].items():
        if p.ayak in ("TO92", "TO220"):
            et = V.BACAK[p.kod]["LMR".index(k)]
        elif p.ayak == "ADS":
            et = V.ADS_MODUL[int(k[1:]) - 1].replace("ALERT/RDY", "ALRT").replace("AIN", "A")
        elif p.ayak == "CE":
            et = "+" if k == "1" else "−"
        elif p.ayak == "D3":
            et = "K" if k == "1" else "A"
        else:
            et = k
        _ = anah[k]
        yer = "/".join(Y.delik_adi(*p._yer(dx, dy)) for dx, dy in konum)
        parcalar_.append(f"<b>{e(et)}</b> {yer}")
    notlar = []
    if p.ayak == "TO92":
        notlar.append(f"düz yüz {_yon_adi(p.aci, 0, 1)}")
    elif p.ayak == "TO220":
        notlar.append(f"yazılı yüz {_yon_adi(p.aci, 0, 1)}, tab arkada")
    elif p.ayak == "DIP8":
        notlar.append(f"çentik {_yon_adi(p.aci, 0, -1)}")
    elif p.ayak == "CE":
        notlar.append("uzun bacak +")
    elif p.ayak == "D3":
        notlar.append("bant = K")
    elif p.ayak == "R1D":
        notlar.append("dik: gövde 1'in üstünde")
    elif p.ayak == "ADS":
        notlar.append("dişi başlık; modül sağa uzanır")
    elif p.ayak == "C1x2":
        notlar.append("iki ayrı 1nF, yan yana")
    if p.ref in V.PARCA_NOTU:
        notlar.append(e(V.PARCA_NOTU[p.ref]))
    return (f"<tr><td><b>{e(p.ref)}</b></td><td>{e(nl.deger.get(p.ref, ''))}</td>"
            f"<td>{' · '.join(parcalar_)}</td><td class='kucuk'>{' · '.join(notlar)}</td></tr>")


def yol_ozeti(yol) -> str:
    """Yalnizca kose noktalari: A1 → A5 → C5."""
    if len(yol) <= 2:
        return " → ".join(Y.delik_adi(*h) for h in yol)
    k = [yol[0]]
    for a, b, c in zip(yol, yol[1:], yol[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            k.append(b)
    k.append(yol[-1])
    return " → ".join(Y.delik_adi(*h) for h in k)


KAPI = {
    0: "24 V'u <b>akım sınırlı</b> ver (kaynakta CC varsa ~60 mA). ±12 V raylarını "
       "GND'ye göre ölç; 7912 ve C16/C17 ısınmamalı. ADS/op-amp henüz yok.",
    1: "Kılavuz <b>01 Vref</b> kapısı: TL431 katodu ve U3A çıkışı (U3 soketine LM358 tak).",
    2: "Kılavuz <b>02</b>: firmware'de <code>#</code> — 0x48 ve 0x49 ikisi de görünmeli.",
    3: "Kılavuz <b>03 Akım kanalı</b>: <code>Z</code> sıfırı, bilinen akım, ters akım.",
    4: "Kılavuz <b>04 NORMAL</b>: <code>z</code>, <code>g&lt;volt&gt;</code>, ters giriş.",
    5: "Kılavuz <b>05 YÜKSEK</b>: <b>önce 12 V</b>, sonra kademeli. Tek el, eller uzakta.",
    6: "Kılavuz <b>06 Osiloskop</b>: bilinen kare dalga, <code>ta</code>.",
    7: "Kılavuz <b>07 Hızlı akım yolu</b>: dirençsel yükte <code>w</code> → PF ≈ 1.",
    8: "Pil testi: Q1 kapısı kart kapalıyken ve RESET'te <b>kapalı</b> kalmalı "
       "(tezgâh listesindeki failsafe kalemi).",
}


# ═══════════════════════════════════════════════════════════════════════
#  STOK — "bu adim icin gerekenler" (envanter yoksa sutun cikmaz)
# ═══════════════════════════════════════════════════════════════════════

# Semada deger olarak gecmeyen ama takmak icin gereken seyler (ayak izine gore)
AKSESUAR = {
    "DIP8": ("DIP-8 entegre soketi", "8 Pin Entegre Soketi", "Konnektör"),
    "SIG": ("5×20 PCB sigorta klipsi (çift)", "5x20mm PCB Klipsli Sigorta Yuvası", "Sigorta"),
    "HDR10": ("1×40 erkek header — 10 pin kes", "1x40 Erkek Header", "Konnektör"),
    "ADS": ("1×40 dişi header — 10 pin kes", "1x40 Dişi Header", "Konnektör"),
}
# Direnc ayak izinin guc sinifi (envanterde paket alaninda yazar)
GUC_SINIFI = {"R4": "1/4W", "R1D": "1/4W", "R5": "1/2W"}
PLAKET_STOK = {"A": ("13x23 Delikli Plaket", "Sarf Malzeme"),
               "B": ("5x5 Delikli Plaket", "Sarf Malzeme")}
KABLO_STOK = {"hv": ("Silikonlu prob kablosu (HV ucu)", "Silikonlu Prob Kablosu", "Kablo")}


class Stok:
    def __init__(self):
        self.kayit = None
        try:
            import bom_dogrula as B
            self.B = B
            if B.ENVANTER.exists():
                with open(B.ENVANTER, encoding="utf-8") as f:
                    self.kayit = list(csv.DictReader(f))
        except Exception:                                   # noqa: BLE001
            self.kayit = None

    @property
    def var(self) -> bool:
        return self.kayit is not None

    def _yaz(self, bulunan) -> str:
        elde = [r for r in bulunan if (r["adet"] or "").strip() != "0"]
        yeni = [r for r in elde if "sökme" not in r["ad"].lower()] or elde
        if not yeni:
            return "<span class='kotu'>kayıtta yok</span>"
        kutu = sorted({r["konum"] or "yeri kayıtta yok" for r in yeni})
        idler = ", ".join(r["id"] for r in yeni[:3]) + (" …" if len(yeni) > 3 else "")
        return f"{e(idler)} <span class='kucuk'>· {e(' / '.join(kutu))}</span>"

    def ad_ile(self, ad, kat, paket="") -> str:
        _t, bulunan, _s = self.B.stok_bul(self.kayit, ad, kat, paket)
        return self._yaz(bulunan)

    def deger_ile(self, deger: str, guc: str = "") -> str:
        if deger in self.B.ESLEME:
            ad, kat, _not, *paket = self.B.ESLEME[deger]
            if paket:
                return self.ad_ile(ad, kat, paket[0])
            if guc:
                # ayak izi guc sinifini belirliyor (R40 1/2 W); o paketten yoksa hepsi
                _t, bulunan, _s = self.B.stok_bul(self.kayit, ad, kat, guc)
                if [r for r in bulunan if (r["adet"] or "").strip() != "0"]:
                    return self._yaz(bulunan)
            return self.ad_ile(ad, kat)
        if deger in self.B.BILINEN_DIS:
            durum, not_ = self.B.BILINEN_DIS[deger]
            return f"<b>{e(durum)}</b> <span class='kucuk'>— {e(not_)}</span>"
        return "—"


def gerekenler(k: int, nl, parcalar, aa, stok: Stok) -> str:
    satir = []
    ilk_kart = [s.kart for s in aa if s.adim == k and s.tur == "hazirlik"]
    for kart in ilk_kart:
        ad, kat = PLAKET_STOK[kart]
        satir.append((f"Delikli plaket — kart {kart}", "1", V.KARTLAR[kart]["plaket"],
                      stok.ad_ile(ad, kat) if stok.var else ""))
    ps = sorted((p for p in parcalar.values() if p.adim == k and p.ayak != "TEL"),
                key=lambda p: Y_dogal(p.ref))
    degerler: dict[tuple, list] = {}
    for p in ps:
        degerler.setdefault((nl.deger.get(p.ref, "?"), GUC_SINIFI.get(p.ayak, "")), []).append(p.ref)
    for (deg, guc), refs in degerler.items():
        satir.append((f"{deg} {guc}".strip(), str(len(refs)), ", ".join(refs),
                      stok.deger_ile(deg, guc) if stok.var else ""))
    aks: dict[str, list] = {}
    for p in ps:
        if p.ayak in AKSESUAR:
            aks.setdefault(p.ayak, []).append(p.ref)
    for ayak, refs in aks.items():
        ad, env_ad, kat = AKSESUAR[ayak]
        satir.append((ad, str(len(refs)), ", ".join(refs),
                      stok.ad_ile(env_ad, kat) if stok.var else ""))
    for ref, (_g, a) in V.KART_DISI.items():
        if a == k:
            deg = nl.deger.get(ref, "?")
            satir.append((f"{deg} (kart dışı)", "1", ref,
                          stok.deger_ile(deg) if stok.var else ""))
    turler = {c[2] for c in V.KABLOLAR if c[3] == k}
    for tur in sorted(turler & set(KABLO_STOK)):
        ad, env_ad, kat = KABLO_STOK[tur]
        satir.append((ad, "", "kart dışı kablo", stok.ad_ile(env_ad, kat) if stok.var else ""))
    if turler - set(KABLO_STOK) or any(s.adim == k and s.tur == "tel" for s in aa):
        satir.append(("Yalıtımlı montaj kablosu", "", "teller / kart dışı kablolar",
                      stok.ad_ile("Tek ve Çok Damarlı Montaj Kablosu", "Kablo") if stok.var else ""))
    bas = "<tr><th>Ne</th><th class='s'>Adet</th><th>Nereye</th>" + \
          ("<th>Stokta (kayıt · kutu)</th>" if stok.var else "") + "</tr>"
    govde = "".join(
        f"<tr><td><b>{e(a)}</b></td><td class='s'>{e(b)}</td><td class='kucuk'>{e(c)}</td>"
        + (f"<td>{d}</td>" if stok.var else "") + "</tr>" for a, b, c, d in satir)
    return f"<details class='gerek' open><summary>Bu adım için gerekenler</summary><table>{bas}{govde}</table></details>"


def Y_dogal(ref: str) -> str:
    return re.sub(r"\d+", lambda m: m.group(0).zfill(3), ref)


# ═══════════════════════════════════════════════════════════════════════
#  ALT ADIM KARTLARI
# ═══════════════════════════════════════════════════════════════════════

TUR_AD = {
    "R4": ("direnç", "direnç"), "R5": ("direnç (1/2 W)", "direnç (1/2 W)"),
    "R1D": ("dik direnç", "dik direnç"), "D3": ("diyot", "diyot"),
    "DIP8": ("entegre soketi", "entegre soketi"),
    "C1": ("seramik kondansatör", "seramik kondansatör"),
    "C2": ("seramik kondansatör", "seramik kondansatör"),
    "C1x2": ("seramik kondansatör çifti", "seramik kondansatör çifti"),
    "C6": ("film kondansatör", "film kondansatör"),
    "CE": ("elektrolitik kondansatör", "elektrolitik kondansatör"),
    "TO92": ("TO-92 parça", "TO-92 parça"), "TO220": ("regülatör (TO-220)", "regülatör (TO-220)"),
    "SIG": ("sigorta klipsi", "sigorta klipsi"), "HDR10": ("J5 başlığı", "J5 başlığı"),
    "ADS": ("ADS modül başlığı", "ADS modül başlığı"),
}
KART_EKI = {"A": "Kart A'yı", "B": "Kart B'yi"}


def _baslik(s, parcalar, teller) -> str:
    if s.tur == "hazirlik":
        return f"{KART_EKI[s.kart]} hazırla"
    if s.tur == "parca":
        turler = []
        for r in s.parcalar:
            ad = TUR_AD[parcalar[r].ayak][0]
            if ad not in turler:
                turler.append(ad)
        return f"{', '.join(s.parcalar)} — {' + '.join(turler)}"
    if s.tur == "iz":
        aglar = []
        for kart, j in s.izler:
            a = kisa_ag(teller[kart][j]["ag"])
            if a not in aglar:
                aglar.append(a)
        return "Lehim izleri — " + ", ".join(aglar)
    if s.tur == "tel":
        return f"Yalıtımlı teller ({len(s.teller)})"
    if s.tur == "kablo":
        bas = ", ".join(s.kart_disi) if s.kart_disi else ", ".join(
            V.TEL_ETIKET.get(r, r) for r in s.parcalar)
        return f"Kart dışı bağlantılar — {bas}"
    if s.tur == "esp32":
        return f"{', '.join(s.ilgili)} → ESP32-S3 kablosu"
    return "Kontrol ve KAPI"


def _madde(xs) -> str:
    return "<ul class='is'>" + "".join(f"<li>{x}</li>" for x in xs) + "</ul>"


def kesim_talimati(kb) -> str:
    """Plaketin kaynak boyutundan hedef boyuta: hangi sutun/sira kesilecek."""
    ks, kr = kb["kaynak"]
    W, H = kb["sutun"], kb["satir"]
    kes = ([f"{W + 1}. sütun"] if W < ks else []) + ([f"{H + 1}. sıra"] if H < kr else [])
    if not kes:
        return f"Plaketi ({W}×{H} delik) <b>kesmeden</b> kullan."
    return (f"{ks}×{kr} deliklik plaketten <b>{W}×{H} delik</b> kes: {' ve '.join(kes)} "
            "deliklerinin üstünden maket bıçağıyla iki yüzden çiz, kır; kenarı zımparala."
            + (" <b>Tek kesim</b> — üç kenar fabrika kenarı kalır." if len(kes) == 1 else ""))


def alt_adim_html(s, nl, parcalar, teller, aa) -> str:
    kb = V.KARTLAR.get(s.kart or "A")
    ic = []
    if s.tur == "hazirlik" and s.kart == "A":
        ks, kr = kb["kaynak"]
        kesik = " ve ".join((["sağda"] if kb["sutun"] < ks else [])
                            + (["altta"] if kb["satir"] < kr else []))
        ic.append(_madde([
            kesim_talimati(kb),
            f"Köşelere M3 delik aç (her köşede {V.VIDA_KOSE}×{V.VIDA_KOSE} delik boş).",
            f"Ped çapını kumpasla ölç: plan <b>{V.PAD_ETKIN_MM:.2f} mm</b> varsayıyor; "
            "büyük çıkarsa dur, söyle — denetim yeniden koşsun.",
            "Plaketi <b>parça yüzü</b> sana bakacak koy; <b>A1</b> sol üst köşe"
            + (f" (kesilen kenar {kesik} kalsın)" if kesik else "")
            + ". Köşeye kalemle A1 yaz — bundan sonraki her delik adı buna göre.",
        ]))
    elif s.tur == "hazirlik":
        ic.append(_madde([
            kesim_talimati(kb) + " Köşelere M3 delik aç.",
            "Bu kart <b>615 V</b> taşır: parçaları takmadan önce plaketi temizle, "
            "sonunda flux'ı IPA ile sil — lehim kalıntısı kaçak yoludur.",
            "Parça yüzünden bakınca sol üst köşeye kalemle <b>B1</b> yaz.",
        ]))
    elif s.tur == "parca":
        ps = [parcalar[r] for r in s.parcalar]
        m = ["Parçaları tablodaki deliklere <b>parça yüzünden</b> tak. Plaketi çevir, "
             "bacakları lehimle, fazlasını kes (izi bacak artığıyla çekeceksen bir iki "
             "delik boyu bırak)."]
        ayaklar = {p.ayak for p in ps}
        if "CE" in ayaklar:
            m.append("<b>Kutuplu:</b> uzun bacak (+) tabloda <b>+</b> yazan deliğe; gövdedeki "
                     "şerit (−) tarafı.")
        if "D3" in ayaklar:
            m.append("<b>Kutuplu:</b> gövdedeki bant = katot (<b>K</b>) — tabloda K yazan deliğe.")
        for p in ps:
            if p.ayak in ("TO92", "TO220"):
                m.append(f"<b>{e(p.ref)}</b>: önce multimetrenin diyot kademesiyle bacak sırasını "
                         f"doğrula — <b>{'-'.join(V.BACAK[p.kod])}</b> (yazılı yüz sana dönük, "
                         "bacaklar aşağı, soldan sağa).")
                if p.kod == "L7912":
                    m.append("7912'nin <b>tabı −12 V'ta</b>: soğutucuya ya da kutuya vidalama "
                             "(soğutucu gerekmiyor).")
                if p.kod == "2N2222-331":
                    m.append("Şemadaki sembol BC547'den (C-B-E); numarayla lehimlenirse C ile E yer "
                             "değiştirir ve transistör <b>yarı çalışır</b>.")
        if "DIP8" in ayaklar:
            m.append("Soketin çentiği tabloda yazan yöne. Entegreyi lehim bitince, bu adımın "
                     "KAPI ölçümünden önce tak (çentik aynı yöne).")
        if "R1D" in ayaklar:
            m.append("<b>Dik montaj:</b> gövde tabloda <b>1</b> yazan deliğin üstünde durur, "
                     "diğer bacak kıvrılıp 2'ye iner.")
        if "SIG" in ayaklar:
            m.append("Klipsleri <b>sigorta takılıyken</b> oturt (aralık kendiliğinden doğru "
                     "olur), her bacağı kısa lehimle (2–3 sn — cam sigorta ısınmasın). Bacak "
                     "delikleri tabloyla uymazsa dur, söyle.")
        if "HDR10" in ayaklar:
            m.append("1×40 erkek header'dan 10 pin kes; kısa uçlar plakete.")
        if "ADS" in ayaklar:
            m.append("1×40 dişi header'dan 10'luk parçalar kes, plakete lehimle. Pin sırasını "
                     f"modülün üstündeki yazıyla karşılaştır: {e(', '.join(V.ADS_MODUL))}. "
                     "Modülleri KAPI ölçümünden önce tak.")
        if "C1x2" in ayaklar:
            m.append("İki ayrı 1nF yan yana; paralel bağlantıyı lehim izi yapacak.")
        if s.kart == "B":
            m.append("<b>HV zinciri:</b> gövdeler plakete yaslı; bacak artığını lehimin üstünden "
                     "kısa kes — keskin uç ve lehim sivrisi kaçak yolunu kısaltır.")
        ic.append(_madde(m))
        ic.append("<table><tr><th>Parça</th><th>Değer</th><th>Bacak → delik</th><th>Yön</th></tr>"
                  + "".join(parca_satiri(p, nl) for p in ps) + "</table>")
    elif s.tur == "iz":
        ic.append(_madde([
            "Plaketi çevir: <b>lehim yüzü</b> (çizim aynalı — aynı harf aynı deliğin üstünde).",
            "Yol köşe noktalarıyla verildi: <code>A1 → A5 → C5</code> = A1'den A5'e düz, oradan "
            "C5'e. Komşu pedleri lehimle köprüle; uzun yolda bacak artığı ya da kalaylı tel "
            "yatırıp lehimle.",
            "Başka renkteki (başka ağdaki) komşu pede lehim taşırma.",
        ]))
        satir = []
        for kart, j in s.izler:
            t = teller[kart][j]
            satir.append(f"<tr><td><span style='color:{renk(t['ag'])}'>●</span> "
                         f"{e(kisa_ag(t['ag']))}</td><td>{yol_ozeti(t['yol'])}</td>"
                         f"<td class='s'>{len(t['yol']) - 1}</td></tr>")
        ic.append("<table><tr><th>Ağ</th><th>Yol (köşeler)</th><th class='s'>Delik</th></tr>"
                  + "".join(satir) + "</table>")
    elif s.tur == "tel":
        ic.append(_madde([
            "Yalıtımlı tel, <b>lehim yüzünde</b> uçtan uca; uçları oradaki bacağa ya da pede lehimle.",
            "Teli plakete yatır, çıplak ucu kısa tut; başka bir pedin üstünden geçirme.",
        ]))
        satir = []
        for kart, j in s.teller:
            t = teller[kart][j]
            (ax, ay), (bx, by) = t["uclar"]
            satir.append(f"<tr><td><span style='color:{renk(t['ag'])}'>●</span> "
                         f"{e(kisa_ag(t['ag']))}</td><td>{kart}:{Y.delik_adi(ax, ay)}</td>"
                         f"<td>{kart}:{Y.delik_adi(bx, by)}</td>"
                         f"<td class='s'>{abs(ax - bx) + abs(ay - by)}</td></tr>")
        ic.append("<table><tr><th>Ağ</th><th>Uç 1</th><th>Uç 2</th><th class='s'>Delik</th></tr>"
                  + "".join(satir) + "</table>")
    elif s.tur == "kablo":
        m = ["Teli önce yanındaki <b>gerginlik deliğinden</b> (boş halka) geçir, sonra lehim "
             "noktasına lehimle — çekilince lehim kopmasın."]
        if any(V.KABLOLAR[j][2] == "yuk" for j in s.kablolar):
            m.append("<b>YÜK AKIMI</b> taşıyan kablolar plakete girmez: kutuda, klemensler "
                     "arasında; kalın kablo kullan.")
        if any(V.KABLOLAR[j][2] == "hv" for j in s.kablolar):
            m.append("<b>HV kablosu</b>: yalıtımı sağlam, diğer kablolardan ayrı ve uzak geçir.")
        ic.append(_madde(m))
        if s.parcalar:
            ic.append("<table><tr><th>Lehim noktası</th><th>Delik</th></tr>" + "".join(
                f"<tr><td>{e(V.TEL_ETIKET.get(r, r))}</td><td>{parcalar[r].kart}:"
                f"{Y.delik_adi(*parcalar[r].delikler(nl)[r + '.1'][0])}</td></tr>"
                for r in s.parcalar) + "</table>")
        if s.kablolar:
            ic.append("<table><tr><th>Nereden</th><th>Nereye</th><th>Tür</th><th>Not</th></tr>"
                      + "".join(
                          f"<tr><td>{e(_uc_adi(V.KABLOLAR[j][0]))}</td>"
                          f"<td>{e(_uc_adi(V.KABLOLAR[j][1]))}</td>"
                          f"<td>{'<b>YÜK AKIMI</b>' if V.KABLOLAR[j][2] == 'yuk' else e(V.KABLOLAR[j][2])}</td>"
                          f"<td class='kucuk'>{e(V.KABLOLAR[j][4])}</td></tr>" for j in s.kablolar)
                      + "</table>")
    elif s.tur == "esp32":
        ic.append(_madde([
            "<b>ESP32 bu karta lehimlenmez.</b> Kutuda kartın yanında durur; J5 başlığına "
            "10 telli <b>dişi-dişi</b> kabloyla bağlanır. Bu adımın KAPI ölçümü +3V3 ve +5V'u "
            "ESP32'den, bu kablo üzerinden alıyor.",
            "Bağlamadan önce ESP32'nin pinlerinde başka tel kalmasın — tezgâh denemelerinden "
            "kalan GPIO4–GPIO5 kısa devre teli ve RC düzeneği dahil.",
            "Kabloyu tablodaki pin pin eşlemeyle tak; <b>3V3 ile 5V'u karıştırma</b>. "
            "Kabloyu kısa tut: I²C ile iki analog sinyal (skop, hızlı akım) aynı demette gidiyor.",
            "USB kablosunu devkit'in <b>COM yazan</b> Type-C soketine tak (CH343 köprüsü). "
            "Öteki soket de port açar ama firmware orada sessiz kalır.",
        ]))
        ic.append("<table><tr><th class='s'>J5</th><th>Ağ</th><th>ESP32-S3 devkit pini</th></tr>"
                  + "".join(j5_satirlari(nl)) + "</table>")
    else:
        aglar = sorted({teller[kart][j]["ag"] for x in aa if x.adim == s.adim
                        for kart, j in x.izler + x.teller} & RAYLAR, key=kisa_ag)
        m = ["<b>Enerji vermeden</b>, ohmmetreyle: bu adımda çektiğin her izin iki ucu arasında "
             "süreklilik var; komşu pedler arasında kısa yok."]
        if aglar:
            m.append("Bu adımda dokunulan rayların hiçbiri GND'ye kısa değil: "
                     + ", ".join(f"<b>{e(kisa_ag(a))}</b>" for a in aglar) + ".")
        ic.append(_madde(m))
        ic.append(f"<div class='ok'><b>KAPI — geçmeden ilerleme:</b> {KAPI.get(s.adim, '')}</div>")
    return "".join(ic)


# ═══════════════════════════════════════════════════════════════════════
#  GORUS PENCERESI (yakinlastirma kutusu)
# ═══════════════════════════════════════════════════════════════════════

def _kutu(s, nl, parcalar, teller):
    """Alt adimin delik biriminde kapsayan kutusu (x0, y0, x1, y1) ya da None."""
    xs, ys = [], []

    def ekle(x, y):
        xs.append(x)
        ys.append(y)

    if s.tur in ("parca", "kablo", "esp32"):
        for r in s.parcalar + s.ilgili:
            p = parcalar[r]
            if p.ayak != "TEL":
                g = p.govde()
                ekle(g[0], g[1])
                ekle(g[2], g[3])
            for dl in p.delikler(nl).values():
                for d in dl:
                    ekle(*d)
            for d in p.bos_delikler():
                ekle(*d)
    for kart, j in s.izler:
        for h in teller[kart][j]["yol"]:
            ekle(*h)
    for kart, j in s.teller:
        for h in teller[kart][j]["uclar"]:
            ekle(*h)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def gorus(s, nl, parcalar, teller, aa) -> dict:
    kart = s.kart or ("B" if any(r in parcalar and parcalar[r].kart == "B" for r in s.parcalar)
                      else "A")
    if s.tur == "kontrol":
        kartlar = [p.kart for p in parcalar.values() if p.adim == s.adim]
        kart = max(set(kartlar), key=kartlar.count) if kartlar else "A"
    yuz = "alt" if s.tur in ("iz", "tel") else "ust"
    kb = V.KARTLAR[kart]
    W, H = kb["sutun"], kb["satir"]
    gen, yuk = 2 * K + W * P, 2 * K + H * P
    vb = [0, 0, gen, yuk]
    if s.tur == "kontrol":
        kutular = [_kutu(x, nl, parcalar, teller) for x in aa
                   if x.adim == s.adim and x.tur in ("parca", "iz", "tel", "kablo")
                   and (x.kart or "A") == kart]
        kutular = [q for q in kutular if q]
        kutu = (min(q[0] for q in kutular), min(q[1] for q in kutular),
                max(q[2] for q in kutular), max(q[3] for q in kutular)) if kutular else None
    elif s.tur == "hazirlik":
        kutu = None
    else:
        kutu = _kutu(s, nl, parcalar, teller)
    if kutu:
        x0, y0, x1, y1 = kutu
        pay = 3.0
        x0, y0, x1, y1 = x0 - pay, y0 - pay, x1 + pay, y1 + pay
        en_az_w, en_az_h = 18, 12
        if x1 - x0 < en_az_w:
            c = (x0 + x1) / 2
            x0, x1 = c - en_az_w / 2, c + en_az_w / 2
        if y1 - y0 < en_az_h:
            c = (y0 + y1) / 2
            y0, y1 = c - en_az_h / 2, c + en_az_h / 2
        if yuz == "alt":
            x0, x1 = (W - 1 - x1), (W - 1 - x0)
        vb = [K + x0 * P, K + y0 * P, (x1 - x0 + 1) * P, (y1 - y0 + 1) * P]
    return {"kart": kart, "yuz": yuz, "vb": [round(v, 1) for v in vb], "tam": [0, 0, gen, yuk]}


# ═══════════════════════════════════════════════════════════════════════
#  SAYFA
# ═══════════════════════════════════════════════════════════════════════

def yaz(nl, parcalar, teller, bilgi, hedef: Path) -> None:
    kok_ag = bilgi["delik_agi"]
    aa = bilgi["alt_adimlar"]
    son = max(s.adim for s in aa)
    toplam_iz = sum(1 for l in teller.values() for t in l if t["tur"] == "iz")
    toplam_tel = sum(1 for l in teller.values() for t in l if t["tur"] == "tel")
    kb_a, kb_b = V.KARTLAR["A"], V.KARTLAR["B"]
    stok = Stok()

    ss = {"parca": {}, "iz": {}, "tel": {}}
    for s in aa:
        for r in s.parcalar:
            ss["parca"][r] = s.sira
        for x in s.izler:
            ss["iz"][x] = s.sira
        for x in s.teller:
            ss["tel"][x] = s.sira

    g = []
    g.append(f"""
<div class="kpi">
  <div><span>Alt adım</span><b>{len(aa)}</b></div>
  <div><span>Ana kart (A)</span><b>{kb_a['sutun']}×{kb_a['satir']}</b></div>
  <div><span>HV kartı (B)</span><b>{kb_b['sutun']}×{kb_b['satir']}</b></div>
  <div><span>Lehim izi · tel</span><b>{toplam_iz} · {toplam_tel}</b></div>
  <div><span>Denetim</span><b>{bilgi['gecti']}/{bilgi['toplam']}</b></div>
</div>

<p>Kurulum <b>LEGO kılavuzu gibi</b>: {son + 1} büyük adım ({', '.join(str(i) for i in range(son + 1))}),
her biri kendi içinde küçük alt adımlara bölünmüş. Her alt adımda birkaç parça ya da birkaç
lehim izi var; her büyük adım bir <b>KAPI</b> ölçümüyle bitiyor ve o geçmeden sonrakine
geçilmiyor. Sıra: <b>önce alçak parçalar, sonra yüksekler</b>; ters takılabilen parça
(elektrolitik, diyot, soket, transistör, regülatör, başlık) hep kendi alt adımında; lehim izleri
parçalardan, kablolar izlerden sonra.</p>

<p>Plaketler <b>her delikte ayrı pedli</b>. Ana kart (A), 13×23 cm plaketten
({kb_a['kaynak'][0]}×{kb_a['kaynak'][1]} delik) <b>{kb_a['sutun']}×{kb_a['satir']} delik</b> kesilerek yapılıyor;
HV zinciri (B) ayrı bir 5×5 cm plakette ({kb_b['sutun']}×{kb_b['satir']}). Şönt,
J3, J7 ve Q1 <b>plakette değil</b>: 11.5 A'e varan yük akımını plaket bakırı
taşımaz. Onlar kutuda, bariyer klemenslerde duruyor; plakete yalnızca Kelvin
uçları, tek yıldız toprak teli ve kapı teli geliyor. <b>615 V'luk giriş A kartına
hiç girmez</b>: B kartındaki zincirden A'ya yalnızca ~1.7 V'luk alt düğüm gelir.</p>

<div class="uy"><b>Koordinat:</b> sütun harf, satır sayı; <b>A1 parça yüzünden bakınca
sol üst</b>. Lehim yüzü çizimi <b>aynalı</b> — plaketi ters çevirince aynı harf
aynı deliğin üstüne gelir. Yalıtımlı teller lehim yüzünde; uçları oradaki
bacağa ya da pede lehimlenir.</div>

<h2>Önce bunlar</h2>
<table>
<tr><th>Ne</th><th>Neden</th></tr>
<tr><td><b>Bacak sırasını multimetreyle doğrula</b></td>
<td>2N2222-331: <b>{'-'.join(V.BACAK['2N2222-331'])}</b> · BC557: <b>{'-'.join(V.BACAK['BC557'])}</b> ·
TL431: <b>{'-'.join(V.BACAK['TL431'])}</b> · 7912: <b>{'-'.join(V.BACAK['L7912'])}</b>
(yazılı yüz sana dönük, bacaklar aşağı, soldan sağa). Şemadaki Q2 sembolü
BC547'den alınmış (C-B-E); numarayla lehimlenirse C ile E yer değiştirir ve
transistör <b>yarı çalışır</b> — sessiz kusur. Diyot kademesinde baz, iki
eklemin ortak ucudur. Her transistörün kendi alt adımında bu uyarı tekrar ediliyor.</td></tr>
<tr><td><b>ADS modül pin sırası</b></td><td>Plan {', '.join(V.ADS_MODUL)} sırasını varsayıyor.
Modülün üstünde yazanla karşılaştır.</td></tr>
<tr><td><b>Ped çapını kumpasla ölç</b></td><td>Kaçak yolu hesabı lehimli iletken
çapını {V.PAD_ETKIN_MM:.2f} mm alıyor. Ölçtüğün daha büyükse söyle, denetim yeniden
koşsun.</td></tr>
<tr><td><b>HV kartında aralık</b></td><td>615 V takviyeli yalıtım <b>bakırdan bakıra</b>
ölçülür. Eski "5 delik atla" merkezden merkezeydi (12.70 mm); pedlerle bakırdan
bakıra {5 * Y.ADIM_MM - V.PAD_ETKIN_MM:.2f} mm kalıyordu, yetmiyordu. Kılavuz ve
bu plan artık <b>{bilgi['f9_adim']} adım</b> diyor. HV kartında 615 V ucu ile alt
düğüm zaten karşı köşelerde; en dar çift:
{e(bilgi['en_dar'].get('B', ''))}.</td></tr>
</table>
""")
    g.append(j5_tablosu(nl))

    # ── gorus penceresi + alt adim listesi
    S = []
    for s in aa:
        gr = gorus(s, nl, parcalar, teller, aa)
        anahtar = f"{s.no}|{','.join(s.parcalar)}|{len(s.izler)}|{len(s.teller)}|{','.join(map(str, s.kablolar))}"
        S.append({"no": s.no, "a": s.adim, "tur": s.tur, "kart": gr["kart"], "yuz": gr["yuz"],
                  "vb": gr["vb"], "baslik": _baslik(s, parcalar, teller), "anahtar": anahtar,
                  "vurgu": list(s.ilgili)})

    dugmeler = "".join(f'<button data-git="{k}" title="{e(V.ADIM_ADLARI[k])}">{k}</button>'
                       for k in range(son + 1))
    figurler = []
    for kart in V.KARTLAR:
        for yuz in ("ust", "alt"):
            figurler.append(f'<figure class="sahne-fig" data-kart="{kart}" data-yuz="{yuz}"'
                            f'{"" if (kart, yuz) == ("A", "ust") else " hidden"}>'
                            f'{kart_svg(kart, yuz, nl, parcalar, teller, kok_ag, ss)}</figure>')
    g.append(f"""
<h2 id="adimadim">Adım adım</h2>
<p class="kucuk">Üstteki çizim seçili alt adıma yakınlaşır: o adımın parçaları <b>koyu ve
parlak</b>, öncekiler soluk, sonrakiler görünmez. Parça takarken <b>parça yüzü</b>, iz ve tel
çekerken <b>lehim yüzü</b> gösterilir. <b>◀ ▶</b> düğmeleri ya da klavyede ← →; bir kartın
başlığına tıklamak da seçer. İmleci bir bacağın ya da izin üstünde tut: ağ ve delik adı yazar.
"Yaptım" işaretleri bu tarayıcıda saklanır.</p>
<div class="gorus" id="gorus">
  <div class="gorus-ust">
    <button id="geri" aria-label="Önceki alt adım">◀</button>
    <div class="gorus-bilgi"><span class="ano" id="g-no"></span> <span id="g-baslik"></span>
      <span class="rozet" id="g-yuz"></span></div>
    <button id="ileri" aria-label="Sonraki alt adım">▶</button>
  </div>
  <div class="sahne" id="sahne">{''.join(figurler)}</div>
  <div class="gorus-alt">
    <div class="adimsec">{dugmeler}</div>
    <label class="kucuk"><input type="checkbox" id="g-tum"> tüm plan</label>
    <span class="kucuk" id="g-sayac"></span>
  </div>
  <div class="cubuk"><div id="g-cubuk"></div></div>
</div>
""")
    for k in range(son + 1):
        g.append(f'<section class="buyuk" id="adim{k}"><h3>Adım {k} — {e(V.ADIM_ADLARI[k])}</h3>')
        g.append(gerekenler(k, nl, parcalar, aa, stok))
        g.append('<ol class="altlar">')
        for s in (x for x in aa if x.adim == k):
            g.append(f'<li class="aa aa-{s.tur}" data-i="{s.sira}" id="s{s.no}">'
                     f'<div class="aa-bas"><span class="ano">{s.no}</span>'
                     f'<b class="aa-ad">{e(_baslik(s, parcalar, teller))}</b>'
                     f'<label class="yaptim"><input type="checkbox"> yaptım</label></div>'
                     f'<div class="aa-ic">{alt_adim_html(s, nl, parcalar, teller, aa)}</div></li>')
        g.append("</ol></section>")

    g.append("""
<h2>Bu plan neyi garanti ediyor, neyi etmiyor</h2>
<p>Denetim (<code>uretim/yerlesim3.py</code>) bakır bağlantıyı <b>geometriden</b>
yeniden kurup şemanın netlistiyle birebir karşılaştırıyor: açık devre yok, kısa
devre yok, her büyük kurulum adımında da. Gövdeler çakışmıyor, bacaklar başka gövdenin
altına düşmüyor; Kelvin uçları kartta yalnız, toprak güç yoluna tek noktadan
bağlı; 50 V üstü her bakır çifti IEC 60664-1 Tablo F.4 aralığını sağlıyor;
ayırma kondansatörleri pinlerine yakın.</p>
<p>Alt adım sırası da denetleniyor: her parça, iz, tel ve kablo <b>tam bir</b> alt adımda;
hiçbir iz ya da tel, daha sonra takılacak bir parçanın deliğini lehimle doldurmuyor;
aynı adımda alçak parçalar yükseklerden önce; ters takılabilen parçalar kendi alt
adımında; her büyük adım KAPI kontrolüyle bitiyor.</p>
<div class="uy"><b>Garanti etmediği:</b> parça ölçüleri tahmin — sigorta klipsinin
bacak aralığı, 68 µF'ın çapı (8 mm varsayıldı), film C18'in bacak aralığı
(15 mm). Parça yükseklikleri de yaklaşık (yalnız sıralama için). Tezgâhta parçayı
plakete oturtup delikleri kontrol et; uymayan olursa söyle, plan yeniden üretilsin.
Bakırın <b>kalitesi</b> (soğuk lehim, köprü) ancak multimetreyle sınanır.</div>
""")

    js = """
<script>
(function(){
 var S = __ALT_ADIMLAR__;
 var ANAHTAR = 'olcum-karti-yerlesim-yaptim';
 var cur = 0, tum = false;
 var figs = Array.prototype.slice.call(document.querySelectorAll('.sahne-fig'));
 var kartlar = Array.prototype.slice.call(document.querySelectorAll('li.aa'));
 var gorusEl = document.getElementById('gorus');
 var yaptim = {};
 try { yaptim = JSON.parse(localStorage.getItem(ANAHTAR) || '{}') || {}; } catch (e) { yaptim = {}; }
 function kaydet(){ try { localStorage.setItem(ANAHTAR, JSON.stringify(yaptim)); } catch (e) {} }

 function oran(fig){ var r = fig.getBoundingClientRect(); return (r.width > 10 && r.height > 10) ? r.width / r.height : 2; }
 function kutu(vb, tam, r){
   var x = vb[0], y = vb[1], w = vb[2], h = vb[3];
   if (w / h < r) { var nw = h * r; x -= (nw - w) / 2; w = nw; } else { var nh = w / r; y -= (nh - h) / 2; h = nh; }
   if (w >= tam[2]) { x = (tam[2] - w) / 2; } else { x = Math.max(0, Math.min(x, tam[2] - w)); }
   if (h >= tam[3]) { y = (tam[3] - h) / 2; } else { y = Math.max(0, Math.min(y, tam[3] - h)); }
   return [x, y, w, h];
 }
 function eksen(svg, vb, yakin){
   var eski = svg.querySelector('g.eksen-dyn'); if (eski) eski.remove();
   var sabit = svg.querySelector('g.eksen'); if (sabit) sabit.style.display = yakin ? 'none' : '';
   if (!yakin) return;
   var NS = 'http://www.w3.org/2000/svg';
   var W = +svg.dataset.w, H = +svg.dataset.h, P = +svg.dataset.p, K = +svg.dataset.k, alt = svg.dataset.alt === '1';
   var olcek = svg.getBoundingClientRect().width / vb[2];
   var fs = 11 / olcek;
   var gg = document.createElementNS(NS, 'g'); gg.setAttribute('class', 'eksen-dyn');
   function yazi(x, y, t, an){
     var el = document.createElementNS(NS, 'text');
     el.setAttribute('x', x); el.setAttribute('y', y); el.setAttribute('font-size', fs);
     el.setAttribute('text-anchor', an); el.setAttribute('font-weight', '700');
     el.setAttribute('fill', '#2a1f12'); el.setAttribute('paint-order', 'stroke');
     el.setAttribute('stroke', '#f3e6cc'); el.setAttribute('stroke-width', fs * 0.35);
     el.textContent = t; gg.appendChild(el);
   }
   function harf(i){ var s = '', n = i + 1; while (n) { var r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); } return s; }
   var aralik = P * olcek, adimX = Math.max(1, Math.ceil(18 / aralik)), adimY = Math.max(1, Math.ceil(13 / aralik));
   for (var i = 0; i < W; i++) {
     if (i % adimX) continue;
     var cx = K + (alt ? (W - 1 - i) : i) * P + P / 2;
     if (cx > vb[0] + fs && cx < vb[0] + vb[2] - fs) yazi(cx, vb[1] + fs * 1.05, harf(i), 'middle');
   }
   for (var j = 0; j < H; j++) {
     if ((j + 1) % adimY && adimY > 1) continue;
     var cy = K + j * P + P / 2;
     if (cy > vb[1] + fs * 2 && cy < vb[1] + vb[3] - fs * 0.5) yazi(vb[0] + fs * 0.3, cy + fs * 0.35, String(j + 1), 'start');
   }
   svg.appendChild(gg);
 }
 function goster(i, kaydir){
   cur = Math.max(0, Math.min(S.length - 1, i));
   var s = S[cur], fig = null;
   figs.forEach(function(f){ var bu = f.dataset.kart === s.kart && f.dataset.yuz === s.yuz; f.hidden = !bu; if (bu) fig = f; });
   var svg = fig.querySelector('svg');
   svg.querySelectorAll('[data-s]').forEach(function(el){
     var n = +el.dataset.s, a = +el.dataset.a, op, parlak;
     if (tum) { op = n <= cur ? 1 : .12; parlak = n === cur; }
     else if (s.tur === 'kontrol') { parlak = a === s.a && n < cur; op = parlak ? 1 : (n < cur ? .25 : 0); }
     else {
       parlak = n === cur || (s.vurgu.length > 0 && s.vurgu.indexOf(el.dataset.r) >= 0);
       op = parlak ? 1 : (n < cur ? (s.yuz === 'alt' ? .6 : .25) : 0);
     }
     el.style.opacity = op;
     el.style.pointerEvents = op === 0 ? 'none' : '';
     el.classList.toggle('bu', parlak);
   });
   var tam = [0, 0, (+svg.dataset.w) * (+svg.dataset.p) + 2 * (+svg.dataset.k), (+svg.dataset.h) * (+svg.dataset.p) + 2 * (+svg.dataset.k)];
   var hedef = tum ? tam : s.vb;
   var vb = kutu(hedef, tam, oran(fig));
   svg.setAttribute('viewBox', vb.join(' '));
   eksen(svg, vb, vb[2] < tam[2] * 0.92 || vb[3] < tam[3] * 0.92);
   document.getElementById('g-no').textContent = s.no;
   document.getElementById('g-baslik').textContent = s.baslik;
   document.getElementById('g-yuz').textContent = s.kart === 'B' ? ('Kart B · ' + (s.yuz === 'alt' ? 'lehim yüzü' : 'parça yüzü')) : ('Kart A · ' + (s.yuz === 'alt' ? 'lehim yüzü' : 'parça yüzü'));
   var bitti = S.filter(function(x){ return yaptim[x.anahtar]; }).length;
   document.getElementById('g-sayac').textContent = (cur + 1) + ' / ' + S.length + ' · yapılan ' + bitti;
   document.getElementById('g-cubuk').style.width = (100 * bitti / S.length) + '%';
   document.querySelectorAll('.adimsec button').forEach(function(b){ b.classList.toggle('sec', +b.dataset.git === s.a); });
   kartlar.forEach(function(li){ li.classList.toggle('secili', +li.dataset.i === cur); });
   document.documentElement.style.setProperty('--gorus-h', gorusEl.offsetHeight + 'px');
   if (kaydir) { var li = kartlar[cur]; if (li) li.scrollIntoView({block: 'start', behavior: 'smooth'}); }
   try { history.replaceState(null, '', '#s' + s.no); } catch (e) {}
 }
 kartlar.forEach(function(li){
   var s = S[+li.dataset.i], kutucuk = li.querySelector('.yaptim input');
   kutucuk.checked = !!yaptim[s.anahtar];
   li.classList.toggle('bitti', kutucuk.checked);
   kutucuk.addEventListener('change', function(){
     if (kutucuk.checked) yaptim[s.anahtar] = 1; else delete yaptim[s.anahtar];
     li.classList.toggle('bitti', kutucuk.checked); kaydet(); goster(cur, false);
   });
   li.querySelector('.aa-bas').addEventListener('click', function(ev){
     if (ev.target.closest('.yaptim')) return; goster(+li.dataset.i, true);
   });
 });
 document.getElementById('geri').addEventListener('click', function(){ goster(cur - 1, true); });
 document.getElementById('ileri').addEventListener('click', function(){ goster(cur + 1, true); });
 document.getElementById('g-tum').addEventListener('change', function(ev){ tum = ev.target.checked; goster(cur, false); });
 document.querySelectorAll('.adimsec button').forEach(function(b){
   b.addEventListener('click', function(){
     var k = +b.dataset.git; for (var i = 0; i < S.length; i++) { if (S[i].a === k) { goster(i, true); return; } }
   });
 });
 document.addEventListener('keydown', function(ev){
   if (ev.target.closest && ev.target.closest('input,textarea,select')) return;
   if (ev.key === 'ArrowRight') { goster(cur + 1, true); ev.preventDefault(); }
   if (ev.key === 'ArrowLeft') { goster(cur - 1, true); ev.preventDefault(); }
 });
 window.addEventListener('resize', function(){ goster(cur, false); });
 function adresten(){
   var m = /^#s(\\d+\\.\\d+)$/.exec(location.hash);
   if (!m) return -1;
   for (var i = 0; i < S.length; i++) if (S[i].no === m[1]) return i;
   return -1;
 }
 window.addEventListener('hashchange', function(){ var i = adresten(); if (i >= 0 && i !== cur) goster(i, true); });
 var bas = adresten();
 goster(Math.max(0, bas), bas >= 0);
})();
</script>""".replace("__ALT_ADIMLAR__", json.dumps(S, ensure_ascii=False))

    ek_stil = """
.kutu{max-width:1040px}
.adimsec{display:flex;gap:4px;flex-wrap:wrap}
.adimsec button{font:inherit;font-size:13px;padding:2px 10px;border-radius:99px;
  border:1px solid var(--cizgi);background:var(--yz2);color:var(--m1);cursor:pointer}
.adimsec button.sec{background:var(--m1);color:var(--yz);border-color:var(--m1)}
figure{margin:0}
details{margin:8px 0}
summary{cursor:pointer;color:var(--m2);font-size:15px}
td{vertical-align:top}
.kotu{color:var(--kotu);font-weight:600}
.gorus{position:sticky;top:0;z-index:5;background:var(--yz);border:1px solid var(--cizgi);
  border-radius:12px;padding:8px 10px 6px;margin:14px 0 18px;box-shadow:0 6px 18px rgba(0,0,0,.08)}
.gorus-ust{display:flex;align-items:center;gap:8px}
.gorus-ust button{font:inherit;font-size:18px;min-width:44px;min-height:40px;border-radius:10px;
  border:1px solid var(--cizgi);background:var(--yz2);color:var(--m1);cursor:pointer}
.gorus-ust button:hover{border-color:var(--m3)}
.gorus-bilgi{flex:1;min-width:0;font-size:15px;line-height:1.35;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.gorus-bilgi .ano{font-weight:700;font-variant-numeric:tabular-nums;margin-right:4px}
.sahne{height:clamp(220px,44vh,540px);margin:6px 0 4px;border-radius:8px;overflow:hidden;
  background:#d9c7a3}
.sahne-fig{width:100%;height:100%}
.sahne-fig svg{width:100%;height:100%;max-width:none}
.sahne-fig svg [data-s]{transition:opacity .25s}
.sahne-fig svg .bu{filter:drop-shadow(0 0 2.5px #ffd21f) drop-shadow(0 0 1px #ffd21f)}
.gorus-alt{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:space-between}
.cubuk{height:3px;background:var(--cizgi);border-radius:3px;margin-top:6px;overflow:hidden}
.cubuk div{height:100%;background:var(--iyi);width:0;transition:width .3s}
.buyuk h3{scroll-margin-top:calc(var(--gorus-h,0px) + 12px)}
ol.altlar{list-style:none;padding:0;margin:8px 0 0}
li.aa{border:1px solid var(--cizgi);border-radius:10px;margin:10px 0;background:var(--yz);
  scroll-margin-top:calc(var(--gorus-h,0px) + 12px)}
li.aa.secili{border-color:var(--s1);box-shadow:0 0 0 2px color-mix(in srgb,var(--s1) 35%,transparent)}
li.aa.bitti .aa-bas{opacity:.6}
li.aa.bitti .aa-ad{text-decoration:line-through}
.aa-bas{display:flex;align-items:baseline;gap:10px;padding:10px 14px;cursor:pointer}
.aa-bas .ano{font-weight:700;font-variant-numeric:tabular-nums;color:var(--s1);min-width:2.6em}
.aa-ad{flex:1;min-width:0}
.yaptim{font-size:13px;color:var(--m2);white-space:nowrap;cursor:pointer}
.aa-ic{padding:0 14px 8px}
.aa-ic table{font-size:14px;margin:8px 0}
.aa-ic .ok{margin:8px 0}
ul.is{margin:4px 0 6px;padding-left:20px;font-size:15px}
ul.is li{margin:3px 0}
.gerek table{font-size:14px}
.aa-ic, .gerek{overflow-x:auto}
@media (max-width:640px){
  .gorus-bilgi{white-space:normal;font-size:14px}
  .aa-bas{flex-wrap:wrap}
  .sahne{height:clamp(180px,32vh,360px)}
  .adimsec button{padding:1px 8px;font-size:12px}
}
"""
    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yerleşim planı — Ölçüm Kartı</title><style>{stil()}{ek_stil}</style></head><body>
<div class="kutu">{MN.serit('7-yerlesim.html')}
<h1>Yerleşim planı</h1>
<p class="alt">Delikli plakette hangi parça hangi deliğe, hangi tel nereden nereye —
adım adım, LEGO kılavuzu sırasıyla.</p>
{''.join(g)}
<p class="kucuk" style="margin-top:60px;border-top:1px solid var(--cizgi);padding-top:14px">
Bu sayfa <code>uretim/yerlesim3.py</code> tarafından, denetim geçtikten sonra üretildi.
Delik adları <code>yerlesim3_veri.py</code> ve <code>yerlesim3_teller.json</code>'dan,
alt adım sırası <code>yerlesim3_adim.py</code>'den geliyor, elle yazılmıyor.</p>
</div>{js}</body></html>"""
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(sayfa, encoding="utf-8")


# J5 pini -> ESP32 GPIO. Ag adi netlist'ten, GPIO numarasi FIRMWARE'den
# (`PIN_*` sabitleri) — iki kaynak; ikisi de elle yazilmiyor. Ag adi ile
# sabit adi eslesmezse tablo "?" basar, sessizce uydurmaz.
J5_AG_PIN = {"/SDA": "PIN_SDA", "/SCL": "PIN_SCL", "/SKOP": "PIN_SKOP",
             "/I_HIZLI": "PIN_HIZLI_I", "/HAZIR": "PIN_HAZIR",
             "/PIL_KAPI": "PIN_PIL_KAPI"}
J5_GUC = {"+3V3": "3V3", "+5V": "5V (VIN)", "GND": "GND"}


def firmware_pinleri() -> dict[str, int]:
    ino = (BURASI.parent / "kod" / "olcum-karti-a3" / "olcum-karti-a3.ino"
           ).read_text(encoding="utf-8", errors="replace")
    return {ad: int(no) for ad, no in
            re.findall(r"static const uint8_t (PIN_\w+)\s*=\s*(\d+);", ino)}


def j5_tablosu(nl) -> str:
    return ("<h2>J5 → ESP32-S3 kablosu</h2>"
            "<p><b>ESP32 karta lehimlenmez</b>: kutuda kartın yanında durur, J5 başlığına "
            "10 telli dişi-dişi kabloyla bağlanır (Adım 1'de, KAPI'dan önce). J5 pin sırası "
            "şemadan, GPIO numaraları firmware'deki <code>PIN_*</code> sabitlerinden. <b>Devkit'in "
            "5V pini USB'den beslenir</b>; kart USB'siz çalışmaz (analog +5 V buradan). "
            "İki Type-C soketinden <b>COM yazan</b> doğru olan (CH343 köprüsü).</p>"
            "<table><tr><th class='s'>J5</th><th>Ağ</th><th>ESP32-S3 devkit pini</th></tr>"
            + "".join(j5_satirlari(nl)) + "</table>")


def j5_satirlari(nl) -> list[str]:
    pinler = firmware_pinleri()
    satir = []
    for no in range(1, 11):
        ag = nl.pin_agi.get(f"J5.{no}", "?")
        if ag in J5_GUC:
            hedef = J5_GUC[ag]
        elif ag in J5_AG_PIN and J5_AG_PIN[ag] in pinler:
            hedef = f"GPIO{pinler[J5_AG_PIN[ag]]}"
        else:
            hedef = "?"
        satir.append(f"<tr><td class='s'>{no}</td><td>{e(kisa_ag(ag))}</td>"
                     f"<td><b>{e(hedef)}</b></td></tr>")
    return satir


def _uc_adi(uc: str) -> str:
    yer, ad = uc.split(":", 1)
    if yer == "X":
        return ad
    return f"{yer}:{V.TEL_ETIKET.get(ad, ad)}"
