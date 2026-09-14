# -*- coding: utf-8 -*-
"""BELGELER/7-yerlesim.html — delikli plaket yerlesim plani (kullanici icin).

`yerlesim3.py` denetimi GECTIKTEN sonra cagirir; kendi basina calismaz.
Sayilarin hepsi `yerlesim3_veri.py`, `yerlesim3_teller.json` ve
`netlist3.net`'ten — elle yazilmis delik adi yok.

Stil `belge-uret.py`'deki STIL'den METIN olarak okunuyor (modulu calistirmadan);
ikinci bir CSS kopyasi tutulmuyor.
"""
from __future__ import annotations

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


def kisa_ag(ag: str) -> str:
    ag = ag.split("@")[0]
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


def _yon(aci, dx, dy):
    return Y.dondur(dx, dy, aci)


def kart_svg(kart: str, yuz: str, nl, parcalar, teller, kok_ag) -> str:
    kb = V.KARTLAR[kart]
    W, H = kb["sutun"], kb["satir"]
    alt = yuz == "alt"

    def X(x):
        return K + ((W - 1 - x) if alt else x) * P + P / 2

    def Yp(y):
        return K + y * P + P / 2

    gen, yuk = 2 * K + W * P, 2 * K + H * P
    o = [f'<svg viewBox="0 0 {gen} {yuk}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="ui-monospace,Consolas,monospace" role="img" '
         f'aria-label="Kart {kart} {"lehim" if alt else "parca"} yuzu">']
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
    # eksen etiketleri
    for x in range(W):
        for yy in (K - 12, K + H * P + 20):
            o.append(f'<text x="{X(x)}" y="{yy}" font-size="8" text-anchor="middle" '
                     f'fill="currentColor" opacity=".7">{Y.sutun_adi(x)}</text>')
    for y in range(H):
        for xx, an in ((K - 9, "end"), (K + W * P + 9, "start")):
            o.append(f'<text x="{xx}" y="{Yp(y) + 3}" font-size="8" text-anchor="{an}" '
                     f'fill="currentColor" opacity=".7">{y + 1}</text>')

    if alt:
        # parca izleri (soluk) — lehim yuzunde yon bulmak icin
        for p in parcalar.values():
            if p.kart != kart or p.ayak == "TEL":
                continue
            x0, y0, x1, y1 = p.govde()
            a, b = sorted((X(x0), X(x1)))
            o.append(f'<g data-adim="{p.adim}"><rect x="{a:.1f}" y="{Yp(y0):.1f}" '
                     f'width="{b - a:.1f}" height="{Yp(y1) - Yp(y0):.1f}" fill="none" '
                     f'stroke="#5b4630" stroke-width=".8" stroke-dasharray="3 2" opacity=".55"/>'
                     f'<text x="{(a + b) / 2:.1f}" y="{(Yp(y0) + Yp(y1)) / 2 + 3:.1f}" '
                     f'font-size="7" text-anchor="middle" fill="#3a2a1a" opacity=".8">{e(p.ref)}</text></g>')
        for t in teller.get(kart, []):
            c = renk(t["ag"])
            ad = kisa_ag(t["ag"])
            if t["tur"] == "iz":
                nokta = " ".join(f"{X(h[0]):.1f},{Yp(h[1]):.1f}" for h in t["yol"])
                o.append(f'<polyline data-adim="{t["adim"]}" points="{nokta}" fill="none" '
                         f'stroke="{c}" stroke-width="{P * 0.36:.1f}" stroke-linecap="round" '
                         f'stroke-linejoin="round"><title>{e(ad)} · lehim izi · adim {t["adim"]}'
                         f'</title></polyline>')
            else:
                (ax, ay), (bx, by) = t["uclar"]
                x1_, y1_, x2_, y2_ = X(ax), Yp(ay), X(bx), Yp(by)
                mx, my = (x1_ + x2_) / 2, (y1_ + y2_) / 2
                dx, dy = x2_ - x1_, y2_ - y1_
                L = max(1.0, (dx * dx + dy * dy) ** 0.5)
                bx_, by_ = mx - dy / L * min(22, L * 0.25), my + dx / L * min(22, L * 0.25)
                o.append(f'<g data-adim="{t["adim"]}"><path d="M{x1_:.1f},{y1_:.1f} Q{bx_:.1f},{by_:.1f} '
                         f'{x2_:.1f},{y2_:.1f}" fill="none" stroke="{c}" stroke-width="2.6" '
                         f'stroke-dasharray="6 3"><title>{e(ad)} · YALITIMLI TEL · '
                         f'{Y.delik_adi(ax, ay)} → {Y.delik_adi(bx, by)} · adim {t["adim"]}</title></path>'
                         f'<circle cx="{x1_:.1f}" cy="{y1_:.1f}" r="3" fill="{c}"/>'
                         f'<circle cx="{x2_:.1f}" cy="{y2_:.1f}" r="3" fill="{c}"/></g>')

    # parcalar (ust yuzde govde, iki yuzde de bacak)
    for p in sorted(parcalar.values(), key=lambda q: q.ayak == "ADS"):
        if p.kart != kart:
            continue
        g = [f'<g data-adim="{p.adim}">']
        deger = nl.deger.get(p.ref, "")
        if not alt and p.ayak != "TEL":
            x0, y0, x1, y1 = p.govde()
            dolgu, cizgi = GOVDE_RENK[p.ayak]
            saydam = ' fill-opacity=".82"' if p.ayak == "ADS" else ""
            g.append(f'<rect x="{X(x0):.1f}" y="{Yp(y0):.1f}" width="{(x1 - x0) * P:.1f}" '
                     f'height="{(y1 - y0) * P:.1f}" rx="{3 if p.ayak not in ("R4", "R5") else 6}" '
                     f'fill="{dolgu}"{saydam} stroke="{cizgi}" stroke-width="1">'
                     f'<title>{e(p.ref)} · {e(deger)} · adim {p.adim}</title></rect>')
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
                     f'stroke="#555" stroke-width="1.2"><title>gerginlik deligi — telin '
                     f'yalitimi buradan gecer, lehimlenmez</title></circle>')
        g.append("</g>")
        o += g
    # kart disi tel etiketleri EN USTTE — govdelerin altinda kalmasin
    for p in parcalar.values():
        if p.kart != kart or p.ayak != "TEL":
            continue
        (d,) = p.delikler(nl)[f"{p.ref}.1"]
        etiket = V.TEL_ETIKET.get(p.ref, p.ref)
        yon = -1 if (X(d[0]) > K + W * P / 2) else 1
        o.append(f'<text data-adim="{p.adim}" x="{X(d[0]) + yon * 9:.1f}" y="{Yp(d[1]) - 7:.1f}" '
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
                   f'stroke="#f5c518" stroke-width="2.5"><title>duz (yazili) yuz</title></line>')
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
                   f'stroke="#222" stroke-width="3"><title>katot bandi</title></line>')
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
        pid = anah[k]
        if p.ayak in ("TO92", "TO220"):
            et = V.BACAK[p.kod]["LMR".index(k)]
        elif p.ayak == "ADS":
            et = V.ADS_MODUL[int(k[1:]) - 1].replace("ALERT/RDY", "ALRT").replace("AIN", "A")
        elif p.ayak in ("R4", "R5", "R1D", "C1", "C2", "C6", "C1x2", "SIG"):
            et = k
        elif p.ayak == "CE":
            et = "+" if k == "1" else "−"
        elif p.ayak == "D3":
            et = "K" if k == "1" else "A"
        else:
            et = k
        yer = "/".join(Y.delik_adi(*p._yer(dx, dy)) for dx, dy in konum)
        parcalar_.append(f"<b>{e(et)}</b> {yer}")
    notlar = []
    if p.ayak == "TO92":
        notlar.append(f"düz yüz {_yon_adi(p.aci, 0, 1)}")
    elif p.ayak == "TO220":
        notlar.append(f"yazılı yüz {_yon_adi(p.aci, 0, 1)}, tab arkada")
        if p.kod == "L7912":
            notlar.append("<b>tab −12 V'ta: soğutucuya vidalama</b>")
    elif p.ayak == "DIP8":
        notlar.append(f"çentik {_yon_adi(p.aci, 0, -1)} · soketli")
    elif p.ayak == "CE":
        notlar.append("uzun bacak +")
    elif p.ayak == "D3":
        notlar.append("bant = K")
    elif p.ayak == "R1D":
        notlar.append("dik montaj, gövde 1'in üstünde")
    elif p.ayak == "SIG":
        notlar.append("klipsleri sigortayla birlikte oturt, bacak deliklerini kontrol et")
    elif p.ayak == "ADS":
        notlar.append("dişi başlıkta; modül sağa uzanır")
    elif p.ayak == "C1x2":
        notlar.append("iki ayrı 1nF, yan yana")
    return (f"<tr><td>{p.kart}</td><td><b>{e(p.ref)}</b></td><td>{e(nl.deger.get(p.ref, ''))}</td>"
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


def yaz(nl, parcalar, teller, bilgi, hedef: Path) -> None:
    # delik -> ag (denetimin kurdugu gercek baglantidan)
    kok_ag = bilgi["delik_agi"]
    son = max(p.adim for p in parcalar.values())
    toplam_iz = sum(1 for l in teller.values() for t in l if t["tur"] == "iz")
    toplam_tel = sum(1 for l in teller.values() for t in l if t["tur"] == "tel")
    kb_a, kb_b = V.KARTLAR["A"], V.KARTLAR["B"]

    g = []
    g.append(f"""
<div class="kpi">
  <div><span>Ana kart (A)</span><b>{kb_a['sutun']}×{kb_a['satir']}</b></div>
  <div><span>HV kartı (B)</span><b>{kb_b['sutun']}×{kb_b['satir']}</b></div>
  <div><span>Lehim izi</span><b>{toplam_iz}</b></div>
  <div><span>Yalıtımlı tel</span><b>{toplam_tel}</b></div>
  <div><span>Denetim</span><b>{bilgi['gecti']}/{bilgi['toplam']}</b></div>
</div>

<p>Plaketler <b>her delikte ayrı pedli</b>. Ana kart (A), 13×23 cm plaketten
(45×90 delik) <b>{kb_a['sutun']}×{kb_a['satir']} delik</b> kesilerek yapılıyor;
HV zinciri (B) ayrı bir 5×5 cm plakette ({kb_b['sutun']}×{kb_b['satir']}). Şönt,
J3, J7 ve Q1 <b>plakette değil</b>: 11.5 A'e varan yük akımını plaket bakırı
taşımaz. Onlar kutuda, bariyer klemenslerde duruyor; plakete yalnızca Kelvin
uçları, tek yıldız toprak teli ve kapı teli geliyor.</p>

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
eklemin ortak ucudur.</td></tr>
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
<tr><td><b>Kart A'yı kesmek</b></td><td>39. sıra deliklerin üzerinden kes; köşelere M3
delik aç (her köşede 2×2 delik boş bırakıldı).</td></tr>
<tr><td><b>Dik dirençler</b></td><td>Sıkışık yerlerde dik montaj (R1D). Gövde, tabloda
"1" yazan deliğin üstünde durur.</td></tr>
</table>
""")

    # adim secici + cizimler
    dugmeler = ['<button data-k="-1" class="sec">Hepsi</button>']
    for k, ad in enumerate(V.ADIM_ADLARI):
        dugmeler.append(f'<button data-k="{k}" title="{e(ad)}">{k}</button>')
    g.append(f"""
<h2>Çizimler</h2>
<p class="kucuk">Bir adım seç: o adımın parçaları ve telleri koyu, önceki adımlar
yarı saydam, sonrakiler silik görünür. İmleci bir bacağın ya da telin
üstünde tut: ağ adı ve delik yazar.</p>
<div class="adimsec">{''.join(dugmeler)}</div>
<p class="kucuk" id="adimad"></p>
""")
    for kart in ("A", "B"):
        kb = V.KARTLAR[kart]
        g.append(f"<h3>Kart {kart} — {e(kb['ad'])} · parça yüzü</h3>")
        g.append(f'<figure class="cizim">{kart_svg(kart, "ust", nl, parcalar, teller, kok_ag)}</figure>')
        g.append(f"<h3>Kart {kart} — lehim yüzü (aynalı)</h3>")
        g.append(f'<figure class="cizim">{kart_svg(kart, "alt", nl, parcalar, teller, kok_ag)}</figure>')

    # adim adim tablolar
    g.append("<h2>Adım adım</h2>")
    g.append("<p>Her adımın sonunda kılavuzdaki <b>KAPI</b> ölçümünü yap; geçmeden "
             "sonrakine geçme. Denetim, her adımın sonunda yarım kurulmuş kartın o "
             "adıma kadarki parçaları <b>tam ve kısasız</b> bağladığını ayrıca "
             "sınıyor.</p>")
    for k in range(son + 1):
        g.append(f'<h3 id="adim{k}">Adım {k} — {e(V.ADIM_ADLARI[k])}</h3>')
        ps = [p for p in parcalar.values() if p.adim == k]
        ps.sort(key=lambda p: (p.kart, p.ayak == "TEL",
                               re.sub(r"\d+", lambda m: m.group(0).zfill(3), p.ref)))
        gercek = [p for p in ps if p.ayak != "TEL"]
        pedler = [p for p in ps if p.ayak == "TEL"]
        if gercek:
            g.append("<table><tr><th>Kart</th><th>Parça</th><th>Değer</th>"
                     "<th>Bacak → delik</th><th>Yön</th></tr>")
            g += [parca_satiri(p, nl) for p in gercek]
            g.append("</table>")
        if pedler:
            g.append("<p class='kucuk'><b>Kart dışı tel lehim noktaları:</b> " + " · ".join(
                f"{e(V.TEL_ETIKET.get(p.ref, p.ref))} = {p.kart}:"
                f"{Y.delik_adi(*p.delikler(nl)[p.ref + '.1'][0])}" for p in pedler) + "</p>")
        izler = [(kart, t) for kart, l in teller.items() for t in l
                 if t["adim"] == k and t["tur"] == "iz"]
        teller_k = [(kart, t) for kart, l in teller.items() for t in l
                    if t["adim"] == k and t["tur"] == "tel"]
        if izler:
            g.append("<details><summary>Lehim izleri "
                     f"({len(izler)})</summary><table><tr><th>Kart</th><th>Ağ</th>"
                     "<th>Yol (köşeler)</th><th class='s'>Delik</th></tr>")
            for kart, t in sorted(izler, key=lambda x: (x[0], kisa_ag(x[1]["ag"]))):
                g.append(f"<tr><td>{kart}</td><td><span style='color:{renk(t['ag'])}'>●</span> "
                         f"{e(kisa_ag(t['ag']))}</td><td>{yol_ozeti(t['yol'])}</td>"
                         f"<td class='s'>{len(t['yol']) - 1}</td></tr>")
            g.append("</table></details>")
        if teller_k:
            g.append("<table><tr><th>Yalıtımlı tel</th><th>Uç 1</th><th>Uç 2</th>"
                     "<th class='s'>Delik</th></tr>")
            for kart, t in sorted(teller_k, key=lambda x: kisa_ag(x[1]["ag"])):
                (ax, ay), (bx, by) = t["uclar"]
                g.append(f"<tr><td><span style='color:{renk(t['ag'])}'>●</span> "
                         f"{e(kisa_ag(t['ag']))}</td><td>{kart}:{Y.delik_adi(ax, ay)}</td>"
                         f"<td>{kart}:{Y.delik_adi(bx, by)}</td>"
                         f"<td class='s'>{abs(ax - bx) + abs(ay - by)}</td></tr>")
            g.append("</table>")
        kab = [c for c in V.KABLOLAR if c[3] == k]
        if kab:
            g.append("<table><tr><th>Kart dışı kablo</th><th>→</th><th>Tür</th><th>Not</th></tr>")
            for u1, u2, tur, _a, not_ in kab:
                g.append(f"<tr><td>{e(_uc_adi(u1))}</td><td>{e(_uc_adi(u2))}</td>"
                         f"<td>{'<b>YÜK AKIMI</b>' if tur == 'yuk' else e(tur)}</td>"
                         f"<td class='kucuk'>{e(not_)}</td></tr>")
            g.append("</table>")
        g.append(f"<div class='ok'><b>KAPI:</b> {KAPI.get(k, '')}</div>")

    g.append("""
<h2>Bu plan neyi garanti ediyor, neyi etmiyor</h2>
<p>Denetim (<code>uretim/yerlesim3.py</code>) bakır bağlantıyı <b>geometriden</b>
yeniden kurup şemanın netlistiyle birebir karşılaştırıyor: açık devre yok, kısa
devre yok, her kurulum adımında da. Gövdeler çakışmıyor, bacaklar başka gövdenin
altına düşmüyor; Kelvin uçları kartta yalnız, toprak güç yoluna tek noktadan
bağlı; 50 V üstü her bakır çifti IEC 60664-1 Tablo F.4 aralığını sağlıyor;
ayırma kondansatörleri pinlerine yakın.</p>
<div class="uy"><b>Garanti etmediği:</b> parça ölçüleri tahmin — sigorta klipsinin
bacak aralığı, 68 µF'ın çapı (8 mm varsayıldı), film C18'in bacak aralığı
(15 mm). Tezgâhta parçayı plakete oturtup delikleri kontrol et; uymayan olursa
söyle, plan yeniden üretilsin. Bakırın <b>kalitesi</b> (soğuk lehim, köprü)
ancak multimetreyle sınanır.</div>
""")

    js = """
<script>
(function(){
 const ad = %s;
 const bs = document.querySelectorAll('.adimsec button');
 function sec(k){
   document.querySelectorAll('[data-adim]').forEach(function(el){
     const a = +el.dataset.adim;
     el.style.opacity = (k < 0 || a === k) ? 1 : (a < k ? .3 : .06);
   });
   bs.forEach(function(b){ b.classList.toggle('sec', +b.dataset.k === k); });
   document.getElementById('adimad').textContent = k < 0 ? '' : ('Adım ' + k + ' — ' + ad[k]);
 }
 bs.forEach(function(b){ b.addEventListener('click', function(){ sec(+b.dataset.k); }); });
})();
</script>""" % json.dumps(list(V.ADIM_ADLARI), ensure_ascii=False)

    ek_stil = """
.adimsec{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.adimsec button{font:inherit;font-size:14px;padding:4px 12px;border-radius:99px;
  border:1px solid var(--cizgi);background:var(--yz2);color:var(--m1);cursor:pointer}
.adimsec button.sec{background:var(--m1);color:var(--yz);border-color:var(--m1)}
figure.cizim{overflow-x:auto;margin:10px 0 26px}
figure.cizim svg{min-width:640px;color:var(--m2)}
details{margin:8px 0}
summary{cursor:pointer;color:var(--m2);font-size:15px}
td{vertical-align:top}
"""
    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yerleşim planı — Ölçüm Kartı</title><style>{stil()}{ek_stil}</style></head><body>
<div class="kutu">{MN.serit('7-yerlesim.html')}
<h1>Yerleşim planı</h1>
<p class="alt">Delikli plakette hangi parça hangi deliğe, hangi tel nereden nereye —
kurulum kılavuzunun adımlarıyla aynı sırada.</p>
{''.join(g)}
<p class="kucuk" style="margin-top:60px;border-top:1px solid var(--cizgi);padding-top:14px">
Bu sayfa <code>uretim/yerlesim3.py</code> tarafından, denetim geçtikten sonra üretildi.
Delik adları <code>yerlesim3_veri.py</code> ve <code>yerlesim3_teller.json</code>'dan
geliyor, elle yazılmıyor.</p>
</div>{js}</body></html>"""
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(sayfa, encoding="utf-8")


def _uc_adi(uc: str) -> str:
    yer, ad = uc.split(":", 1)
    if yer == "X":
        return ad
    return f"{yer}:{V.TEL_ETIKET.get(ad, ad)}"
