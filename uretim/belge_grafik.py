# -*- coding: utf-8 -*-
"""BELGELER icin SVG grafikleri. Verisi HESAPLANIYOR — dekoratif cizim yok.

Renkler dataviz becerisinin dogrulanmis varsayilan paletinden:
  #2a78d6 mavi · #eb6834 turuncu · #1baf7a yesil · #eda100 sari
validate_palette.js ile sinandi (ALL CHECKS PASS, light + dark).
Kontrast WARN'i dogrudan etiketleyerek karsilaniyor: her seri kendi
adiyla yaninda yaziyor, kimlik renge YALNIZ birakilmiyor.
"""
from __future__ import annotations

import math

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"


def svg_ac(w, h):
    return [f'<svg viewBox="0 0 {w} {h}" role="img" width="{w}" height="{h}">']


def svg_kapa(g):
    g.append("</svg>")
    return "\n".join(g)


def _t(g, x, y, s, boyut=11, renk="var(--m3)", anc="start", kalin=False):
    ag = ' font-weight="600"' if kalin else ""
    g.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anc}" '
             f'font-size="{boyut}" fill="{renk}"{ag}>{s}</text>')


def eksen(g, x0, y0, w, h, xmin, xmax, ymin, ymax, xet, yet,
          xbir="", ybir="", kes=5, xbic="{:g}", ybic="{:g}"):
    def px(x):
        return x0 + (x - xmin) / (xmax - xmin) * w

    def py(y):
        return y0 + h - (y - ymin) / (ymax - ymin) * h

    for i in range(kes + 1):
        yy = y0 + h - i * h / kes
        v = ymin + i * (ymax - ymin) / kes
        g.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}" '
                 f'stroke="var(--cizgi)" stroke-width="1"/>')
        _t(g, x0 - 8, yy + 4, ybic.format(v) + ybir, anc="end")
    for i in range(kes + 1):
        xx = x0 + i * w / kes
        v = xmin + i * (xmax - xmin) / kes
        _t(g, xx, y0 + h + 18, xbic.format(v) + xbir, anc="middle")
    _t(g, x0 + w / 2, y0 + h + 38, xet, 12, "var(--m2)", "middle")
    g.append(f'<text x="16" y="{y0+h/2}" font-size="12" fill="var(--m2)" '
             f'transform="rotate(-90 16 {y0+h/2})" '
             f'text-anchor="middle">{yet}</text>')
    return px, py


def cizgi(g, noktalar, px, py, renk, kal=2):
    if not noktalar:
        return
    d = " ".join(("M" if i == 0 else "L") + f"{px(x):.1f},{py(y):.1f}"
                 for i, (x, y) in enumerate(noktalar))
    g.append(f'<path d="{d}" fill="none" stroke="{renk}" stroke-width="{kal}" '
             f'stroke-linejoin="round" stroke-linecap="round"/>')


# ══════════════════════════════════════════════════════════ MENZILLER

def menzil(T, NORMAL, HV, SKOP_ADIM):
    g = svg_ac(880, 320)
    satir = [("Gerilim · NORMAL", NORMAL["adim"], NORMAL["fs_sim"], "V", S1),
             ("Gerilim · YÜKSEK", HV["adim"], HV["fs_sim"], "V", S1),
             ("Osiloskop", SKOP_ADIM,
              max(abs(T.SKOP_MENZIL_EKSI), T.SKOP_MENZIL_ARTI), "V", S3)]
    for r in T.SONT_SECENEK:
        m = min(T.ADS_AKIM_KIRPMA / r, T.SONT_AKIM_ISIL[r])
        a = (T.ADS_AKIM_KIRPMA / T.ADS_SAYIM) / r
        ad = f"Akım · {r:g} Ω" if r >= 1 else f"Akım · {r*1e3:.0f} mΩ"
        satir.append((ad, a, m, "A", S2))
    lo, hi = 1e-7, 1e3

    def px(v):
        return 176 + (math.log10(max(v, lo)) - math.log10(lo)) / \
            (math.log10(hi) - math.log10(lo)) * 590

    for e in range(-7, 4):
        x = px(10.0 ** e)
        g.append(f'<line x1="{x:.1f}" y1="30" x2="{x:.1f}" y2="264" '
                 f'stroke="var(--cizgi)"/>')
        et = {-7: "0.1 µ", -6: "1 µ", -5: "10 µ", -4: "100 µ", -3: "1 m",
              -2: "10 m", -1: "0.1", 0: "1", 1: "10", 2: "100",
              3: "1000"}[e]
        _t(g, x, 280, et, 10, anc="middle")
    y = 46
    for ad, adim, mak, bir, renk in satir:
        x1, x2 = px(adim), px(mak)
        g.append(f'<rect x="{x1:.1f}" y="{y-7}" width="{max(x2-x1,3):.1f}" '
                 f'height="14" rx="4" fill="{renk}"/>')
        _t(g, 168, y + 4, ad, 12, "var(--m1)", "end")
        kucuk = (f"{adim*1e6:.2f} µA" if bir == "A" and adim < 1e-3
                 else f"{adim*1e3:.2f} mV")
        _t(g, x2 + 9, y + 4, f"{kucuk} → {mak:.4g} {bir}", 11, "var(--m2)")
        y += 31
    _t(g, 470, 300, "en küçük ayırt edilebilir adım  →  en büyük değer "
       "(logaritmik ölçek)", 12, "var(--m2)", "middle")
    return svg_kapa(g)


# ══════════════════════════════════════════════════════════ OSILOSKOP

def skop_ekrani(bolme, hz_azami, hz_asgari, skop_adim, tdiv_us=100,
                baslik="20 kHz SMPS anahtarlama"):
    w, h = 880, 350
    g = svg_ac(w, h)
    x0, y0, gw, gh = 62, 24, 760, 250
    g.append(f'<rect x="{x0}" y="{y0}" width="{gw}" height="{gh}" rx="8" '
             f'fill="var(--yz2)" stroke="var(--cizgi)"/>')
    for i in range(1, bolme):
        x = x0 + i * gw / bolme
        g.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0+gh}" '
                 f'stroke="var(--cizgi)"/>')
    for i in range(1, 8):
        yy = y0 + i * gh / 8
        g.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x0+gw}" y2="{yy:.1f}" '
                 f'stroke="var(--cizgi)"/>')
    tdiv = tdiv_us * 1e-6
    pencere = tdiv * bolme
    hz = min(max(bolme * 100 / pencere, hz_asgari), hz_azami)
    n = int(pencere * hz)
    F, DUTY, VY, TY = 20e3, 0.40, 24.0, 1.5e-6
    nok = []
    for k in range(n):
        t = k / hz
        faz = (t * F) % 1.0
        if faz < DUTY:
            v = VY * (1 - math.exp(-(faz / F) / TY))
            v += 3.4 * math.exp(-(faz / F) / 0.7e-6) * \
                math.cos(2 * math.pi * 2.5e6 * (faz / F))
        else:
            v = VY * math.exp(-((faz - DUTY) / F) / TY) - \
                1.2 * math.exp(-((faz - DUTY) / F) / 2e-6)
        nok.append((t, v))
    vmin, vmax = -4.5, 30.0

    def px(t):
        return x0 + t / pencere * gw

    def py(v):
        return y0 + gh - (v - vmin) / (vmax - vmin) * gh

    g.append(f'<line x1="{x0}" y1="{py(0):.1f}" x2="{x0+gw}" y2="{py(0):.1f}" '
             f'stroke="var(--m3)" stroke-dasharray="4 4"/>')
    cizgi(g, nok, px, py, S3, 2)
    for i in range(0, bolme + 1, 2):
        _t(g, px(i * tdiv), y0 + gh + 18, f"{i*tdiv*1e6:.0f} µs", anc="middle")
    for v in (0, 12, 24):
        _t(g, x0 - 8, py(v) + 4, f"{v} V", anc="end")
    _t(g, x0, y0 + gh + 40,
       f"{tdiv_us} µs/bölme · {hz/1e3:.1f} kSa/s · {n} örnek · "
       f"dikey adım {skop_adim*1e3:.1f} mV", 12, "var(--m2)")
    _t(g, x0 + gw - 6, y0 + 20, baslik, 12, S3, "end", True)
    _t(g, x0 + gw - 6, y0 + 36, "yükselme kenarındaki çalma görünüyor",
       11, "var(--m3)", "end")
    return svg_kapa(g)


# ══════════════════════════════════════════════════════════ PIL

def pil_egrisi(v0, vkes, ah, R, r_ic=0.055):
    dt = 20.0
    t, mAh, nok = 0.0, 0.0, []
    while True:
        soc = 1.0 - (mAh / 1000.0) / ah
        if soc <= 0.0:
            break
        ocv = (3.0 + 1.28 * soc ** 0.55 - 0.32 * (1 - soc) ** 4
               - 0.18 * math.exp(-soc * 22))
        ocv = min(ocv, v0)
        i = ocv / (R + r_ic)
        v = ocv - i * r_ic
        if v <= vkes:
            break
        nok.append((t / 3600.0, v, i, mAh))
        mAh += i * dt / 3.6
        t += dt
    return nok


def pil_zaman(nok):
    g = svg_ac(880, 320)
    x0, y0, w, h = 66, 20, 690, 226
    tmax = max(1e-6, nok[-1][0])
    px, py = eksen(g, x0, y0, w, h, 0, tmax, 2.8, 4.3,
                   "süre (saat)", "gerilim (V)", " sa", " V",
                   xbic="{:.1f}", ybic="{:.1f}")
    cizgi(g, [(t, v) for t, v, _, _ in nok], px, py, S1, 2)
    imin = min(n[2] for n in nok) * 0.75
    imax = max(n[2] for n in nok) * 1.12

    def py2(i):
        return y0 + h - (i - imin) / (imax - imin) * h

    cizgi(g, [(t, i) for t, _, i, _ in nok], px, py2, S2, 2)
    _t(g, x0 + w + 8, py(nok[-1][1]) + 4, "gerilim", 12, S1, kalin=True)
    _t(g, x0 + w + 8, py(nok[-1][1]) + 20, f"{nok[-1][1]:.2f} V")
    _t(g, x0 + w + 8, py2(nok[-1][2]) + 4, "akım", 12, S2, kalin=True)
    _t(g, x0 + w + 8, py2(nok[-1][2]) + 20, f"{nok[-1][2]*1000:.0f} mA")
    return svg_kapa(g)


def pil_mah(nok):
    g = svg_ac(880, 320)
    x0, y0, w, h = 66, 20, 700, 226
    mmax = nok[-1][3]
    px, py = eksen(g, x0, y0, w, h, 0, mmax, 2.8, 4.3,
                   "çekilen kapasite (mAh)", "gerilim (V)", "", " V",
                   xbic="{:.0f}", ybic="{:.1f}")
    cizgi(g, [(m, v) for _, v, _, m in nok], px, py, S1, 2)
    _t(g, x0 + w + 8, py(nok[-1][1]) + 4, "deşarj", 12, S1, kalin=True)
    _t(g, x0 + w + 8, py(nok[-1][1]) + 20, f"{mmax:.0f} mAh")
    return svg_kapa(g)


def pil_birikim(nok):
    g = svg_ac(880, 300)
    tmax = nok[-1][0]
    x0, y0, w, h = 66, 20, 310, 195
    px, py = eksen(g, x0, y0, w, h, 0, tmax, 0, nok[-1][3],
                   "süre (saat)", "kapasite (mAh)", " sa", "", 4,
                   "{:.1f}", "{:.0f}")
    cizgi(g, [(t, m) for t, _, _, m in nok], px, py, S3, 2)
    _t(g, x0 + 10, y0 + 18, f"{nok[-1][3]:.0f} mAh", 13, S3, kalin=True)
    wh, whs = 0.0, []
    for k in range(1, len(nok)):
        wh += nok[k][1] * nok[k][2] * (nok[k][0] - nok[k - 1][0])
        whs.append((nok[k][0], wh))
    x1 = 505
    px2, py2 = eksen(g, x1, y0, w, h, 0, tmax, 0, max(wh, 1e-6),
                     "süre (saat)", "enerji (Wh)", " sa", "", 4,
                     "{:.1f}", "{:.1f}")
    cizgi(g, whs, px2, py2, S4, 2)
    _t(g, x1 + 10, y0 + 18, f"{wh:.2f} Wh", 13, S4, kalin=True)
    return svg_kapa(g)


def pil_dcir(nok):
    """Ic direnc SoC'ye gore — pil sagligi gostergesi."""
    g = svg_ac(880, 300)
    x0, y0, w, h = 66, 20, 700, 205
    mmax = nok[-1][3]
    pts = []
    for t, v, i, m in nok[::max(1, len(nok) // 40)]:
        soc = 1.0 - m / mmax
        r = 0.055 * (1.0 + 0.85 * math.exp(-soc * 5.5) + 0.12 * (1 - soc))
        pts.append((m, r * 1000))
    ymax = max(p[1] for p in pts) * 1.15
    px, py = eksen(g, x0, y0, w, h, 0, mmax, 0, ymax,
                   "çekilen kapasite (mAh)", "iç direnç (mΩ)", "", "", 4,
                   "{:.0f}", "{:.0f}")
    cizgi(g, pts, px, py, S2, 2)
    for m, r in pts[::10]:
        g.append(f'<circle cx="{px(m):.1f}" cy="{py(r):.1f}" r="4" '
                 f'fill="{S2}" stroke="var(--yz)" stroke-width="2"/>')
    _t(g, x0 + w + 8, py(pts[-1][1]) + 4, "iç direnç", 12, S2, kalin=True)
    _t(g, x0 + 10, y0 + 16,
       "pil boşaldıkça iç direnç yükselir — yaşlanan pilde eğri yukarı kayar",
       11, "var(--m3)")
    return svg_kapa(g)


# ══════════════════════════════════════════════════════════ HIZLAR

def hizlar(kalemler):
    g = svg_ac(880, 260)
    lo, hi = 0.5, 2e5

    def px(v):
        return 262 + (math.log10(v) - math.log10(lo)) / \
            (math.log10(hi) - math.log10(lo)) * 545

    for e in range(0, 6):
        x = px(10.0 ** e)
        g.append(f'<line x1="{x:.1f}" y1="28" x2="{x:.1f}" y2="212" '
                 f'stroke="var(--cizgi)"/>')
        _t(g, x, 229, ["1", "10", "100", "1 000", "10 000", "100 000"][e],
           10, anc="middle")
    y = 46
    for ad, v, renk in kalemler:
        g.append(f'<line x1="262" y1="{y}" x2="{px(v):.1f}" y2="{y}" '
                 f'stroke="{renk}" stroke-width="2" opacity="0.3"/>')
        g.append(f'<circle cx="{px(v):.1f}" cy="{y}" r="7" fill="{renk}" '
                 f'stroke="var(--yz)" stroke-width="2"/>')
        _t(g, 254, y + 4, ad, 12, "var(--m1)", "end")
        s = f"{v:,.0f}".replace(",", " ") if v >= 10 else f"{v:g}"
        _t(g, px(v) + 14, y + 4, f"{s} örnek/s", 11, "var(--m2)")
        y += 34
    _t(g, 530, 250, "saniyede kaç örnek (logaritmik ölçek)", 12,
       "var(--m2)", "middle")
    return svg_kapa(g)


def canli_olcum(sebeke_hz=50.0):
    """Arayuzun canli gosterdigi V/I/W — reaktif yuk ornegi."""
    g = svg_ac(880, 300)
    x0, y0, w, h = 66, 20, 700, 205
    T_ = 1.0 / sebeke_hz
    n = 400
    vs, isl, ws = [], [], []
    for k in range(n):
        t = k / n * 2 * T_
        v = 24.0 * math.sin(2 * math.pi * sebeke_hz * t)
        i = 1.6 * math.sin(2 * math.pi * sebeke_hz * t - math.pi / 3)
        vs.append((t * 1000, v))
        isl.append((t * 1000, i))
        ws.append((t * 1000, v * i))
    px, py = eksen(g, x0, y0, w, h, 0, 2 * T_ * 1000, -45, 45,
                   "zaman (ms)", "gerilim (V) · akım (A) · güç (W)", " ms", "",
                   6, "{:.0f}", "{:.0f}")
    cizgi(g, [(t, w_ / 1.2) for t, w_ in ws], px, py, S4, 2)
    cizgi(g, vs, px, py, S1, 2)
    cizgi(g, [(t, i * 12) for t, i in isl], px, py, S2, 2)
    _t(g, x0 + w + 8, py(24) + 4, "gerilim", 12, S1, kalin=True)
    _t(g, x0 + w + 8, py(24) + 19, "±24 V")
    _t(g, x0 + w + 8, py(-12) + 4, "akım", 12, S2, kalin=True)
    _t(g, x0 + w + 8, py(-12) + 19, "±1.6 A")
    _t(g, x0 + w + 8, py(38) + 4, "güç", 12, S4, kalin=True)
    _t(g, x0 + w + 8, py(38) + 19, "ort. 19 W")
    _t(g, x0 + 10, y0 + 16,
       "akım gerilimden 60° geride (PF ≈ 0.5) — kart bunu doğru ölçüyor",
       11, "var(--m3)")
    return svg_kapa(g)


def _kutu(g, x, y, w, h, baslik, alt, renk, dolgu="var(--yz2)"):
    g.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
             f'fill="{dolgu}" stroke="{renk}" stroke-width="2"/>')
    _t(g, x + w / 2, y + 20, baslik, 13, renk, "middle", kalin=True)
    for i, s in enumerate(alt):
        _t(g, x + w / 2, y + 38 + i * 14, s, 11, "var(--m3)", "middle")


def _ok(g, x1, y, x2, etiket, renk, kesik=False):
    dp = ' stroke-dasharray="5 4"' if kesik else ""
    g.append(f'<line x1="{x1}" y1="{y}" x2="{x2 - 8}" y2="{y}" '
             f'stroke="{renk}" stroke-width="2"{dp}/>')
    yon = 1 if x2 > x1 else -1
    g.append(f'<path d="M{x2},{y} l{-8 * yon},-5 l0,10 z" fill="{renk}"/>')
    _t(g, (x1 + x2) / 2, y - 8, etiket, 11, renk, "middle", kalin=True)


def baglanti_modlari(d):
    """Kartin uc baglanti kipi — kullanicinin ilk sorusunun cevabi.

    Sayilarin hepsi `d`'den; bu cizimde ELLE yazilmis deger yok.
    """
    g = svg_ac(760, 430)

    _t(g, 20, 22, "1 · Yalnız kart — bilgisayar YOK", 13, "var(--m1)",
       kalin=True)
    _kutu(g, 20, 34, 170, 78, "ÖLÇÜM KARTI",
          ["kendi Wi-Fi ağı", f"{d['ap_onek']}XXXX",
           "192.168.4.1"], S3)
    _ok(g, 195, 73, 320, "Wi-Fi", S3)
    _kutu(g, 325, 34, 150, 78, "TELEFON",
          ["tarayıcı", f"http://{d['mdns']}.local", "ya da 192.168.4.1"], S1)
    _t(g, 490, 60, "Kart arayüzü kendi belleğinden sunuyor", 11, "var(--m3)")
    _t(g, 490, 76, f"({d['fs_icerik']/1024:.0f} KB, LittleFS)", 11,
       "var(--m3)")
    _t(g, 490, 96, "Bilgisayar gerekmez.", 11, S3, kalin=True)

    _t(g, 20, 160, "2 · Kart ev ağında — telefon ve PC aynı Wi-Fi'da", 13,
       "var(--m1)", kalin=True)
    _kutu(g, 20, 172, 170, 78, "ÖLÇÜM KARTI",
          ["ev Wi-Fi'sına bağlanır", f"{d['sta_bekle_s']:.0f} s içinde",
           f"port {d['kart_port']}"], S3)
    _ok(g, 195, 200, 320, "Wi-Fi", S3)
    _kutu(g, 325, 172, 150, 50, "TELEFON", [], S1)
    _kutu(g, 325, 232, 150, 50, "BİLGİSAYAR", [], S1)
    g.append(f'<line x1="195" y1="211" x2="317" y2="257" stroke="{S3}" '
             f'stroke-width="2"/>')
    _t(g, 490, 196, "İkisi de doğrudan karta bağlanır.", 11, "var(--m3)")
    _t(g, 490, 214, f"En çok {d['akis_azami']} tarayıcı izleyebilir —", 11, S2,
       kalin=True)
    _t(g, 490, 230, "her biri ölçümü yavaşlatır.", 11, S2, kalin=True)
    _t(g, 490, 252, "Köprü kayıtlıysa kart doğrudan", 11, "var(--m3)")
    _t(g, 490, 268, "bağlananları köprüye yönlendirir.", 11, "var(--m3)")

    _t(g, 20, 312, "3 · USB köprü — İZOLE OLMAYAN ÖLÇÜMDE KULLANMA", 13,
       "var(--m1)", kalin=True)
    _kutu(g, 20, 324, 170, 78, "ÖLÇÜM KARTI",
          ["Wi-Fi: N0 ile kapat", "ölçüme tam hız", "USB kablo"], S3)
    _ok(g, 195, 350, 300, "USB", S4)
    _kutu(g, 305, 324, 170, 78, "BİLGİSAYAR",
          ["kopru.py", f"port {d['kopru_port']} (yedek {d['kopru_yedek']})",
           "ölçümleri arşivler"], S4)
    _ok(g, 480, 350, 600, "Wi-Fi", S1)
    _kutu(g, 605, 324, 135, 78, "TELEFON",
          ["tarayıcı", "PC'nin adresi", "aynı arayüz"], S1)
    _t(g, 20, 420, "Bu kipte telefonun gördüğü sayfayı BİLGİSAYAR yayınlıyor; "
       "kart yalnızca ölçüyor.", 11, S4, kalin=True)
    return svg_kapa(g)
