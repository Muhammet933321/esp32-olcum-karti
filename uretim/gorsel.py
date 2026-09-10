# -*- coding: utf-8 -*-
"""Simulasyon sonuclarindan SVG grafik uretir.

    python gorsel.py

Ciktilar `../gorsel/` altina yazilir. Saydam zemin ve orta tonlu eksenler
kullaniliyor — hem acik hem koyu temada okunuyor.
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import spice
import sim_bolucu
import sim_akim

BURASI = Path(__file__).parent
GECICI = BURASI / "_gecici"
CIKTI = BURASI.parent / "gorsel"
CIKTI.mkdir(exist_ok=True)

EKSEN = "#8a92a0"      # her iki temada okunan orta ton
IZGARA = "#8a92a055"
RENK = {
    "mavi": "#4b7bec", "turuncu": "#f0883e", "yesil": "#2ea36b",
    "kirmizi": "#e5534b", "mor": "#a371f7", "gri": "#8a92a0",
}

plt.rcParams.update({
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
    "savefig.transparent": True,
    "text.color": EKSEN,
    "axes.labelcolor": EKSEN,
    "axes.edgecolor": EKSEN,
    "xtick.color": EKSEN,
    "ytick.color": EKSEN,
    "grid.color": IZGARA,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.titleweight": "600",
    "figure.dpi": 110,
})


def yeni(en=6.4, boy=3.4):
    f, a = plt.subplots(figsize=(en, boy))
    a.grid(True, lw=.6, alpha=.6)
    for k in ("top", "right"):
        a.spines[k].set_visible(False)
    return f, a


def kaydet(f, ad):
    f.tight_layout(pad=0.6)
    yol = CIKTI / ad
    f.savefig(yol, format="svg", transparent=True, bbox_inches="tight")
    plt.close(f)
    print(f"  {ad}  ({yol.stat().st_size // 1024} KB)")


# ═══════════════════════════════════════════════ S1 — AREF seri direnci
def g_referans():
    dirençler = [100, 220, 470, 1000, 2200, 4700]
    aref, dusum = [], []
    for r in dirençler:
        _, d = spice.kos(sim_bolucu.__dict__.get("_x") or
                         _s1_netlist(r), GECICI / f"g1_{r}")
        v = spice.degerler(d / "op.txt")[0]
        aref.append(v[2])
        dusum.append((2.495 - v[2]) * 1e3)

    f, a = yeni()
    a.semilogx(dirençler, aref, "o-", color=RENK["mavi"], lw=2, ms=6)
    a.axhline(2.495, ls="--", lw=1, color=RENK["gri"])
    a.annotate("TL431 = 2.495 V", (7000, 2.505), color=RENK["gri"],
               fontsize=8, ha="right")

    for r, v, dd in zip(dirençler, aref, dusum):
        if r in (220, 4700):
            renk = RENK["yesil"] if r == 220 else RENK["kirmizi"]
            secim = "  ← seçilen" if r == 220 else "  ← reddedilen"
            a.plot(r, v, "o", ms=11, mfc="none", mec=renk, mew=2)
            a.annotate(f"{r} Ω{secim}\n{v:.3f} V   (−{dd:.0f} mV)",
                       (r, v), textcoords="offset points",
                       xytext=(14, -4 if r == 220 else 12),
                       va="top" if r == 220 else "bottom",
                       ha="left" if r == 220 else "right",
                       color=renk, fontsize=8.5, weight="600")

    a.set_xlabel("AREF seri direnci (Ω, log)")
    a.set_ylabel("AREF gerilimi (V)")
    a.set_title("S1 · AREF'in iç yükü (~32 kΩ, 77 µA) referansı aşağı çekiyor",
                pad=12)
    a.set_ylim(2.10, 2.56)
    a.set_xlim(80, 9000)
    kaydet(f, "s1-aref.svg")


def _s1_netlist(rs):
    return f"""* TL431 + AREF yuku
V5 v5 0 DC 5.0
Rbias v5 katot 1k
BTL431 katot 0 I = max(0, (V(katot)-2.495)/0.2)
Rs katot aref {rs}
Caref aref 0 100n
Rload aref 0 32e3
.control
op
wrdata op.txt v(katot) v(aref)
.endc
.end
"""


# ═══════════════════════════════════ S2a — bölücü doğrusallığı
def g_bolucu():
    _, d = spice.kos(sim_bolucu.netlist_dc(30, "1n"), GECICI / "g2_dc")
    veri = spice.degerler(d / "dc.txt")
    vin = np.array([s[0] for s in veri])
    vd = np.array([s[1] for s in veri])

    f, a = yeni()
    a.plot(vin, vd, color=RENK["mavi"], lw=2.2, label="düğüm gerilimi (A0)")
    a.plot(vin, vin / 11, ls="--", lw=1.2, color=RENK["gri"], label="ideal 1:11")
    a.axhline(2.478, ls=":", lw=1.2, color=RENK["turuncu"])
    a.annotate("AREF = 2.478 V  →  tam ölçek 27.26 V",
               (1, 2.52), color=RENK["turuncu"], fontsize=8.5)
    a.set_xlabel("giriş gerilimi (V)")
    a.set_ylabel("bölücü düğümü (V)")
    a.set_title("S2a · Gerilim bölücü — doğrusallık sapması %0.006")
    a.legend(frameon=False, fontsize=8.5, loc="lower right")
    kaydet(f, "s2a-bolucu.svg")


# ═══════════════════════════════════ S2b — arıza kelepçesi
def g_kelepce():
    _, d = spice.kos(sim_bolucu.netlist_dc(400, "1n"), GECICI / "g2_ariza")
    veri = spice.degerler(d / "dc.txt")
    vin = np.array([s[0] for s in veri])
    vd = np.array([s[1] for s in veri])
    iin = np.array([abs(s[2]) for s in veri]) * 1e3

    f, a = yeni()
    a.plot(vin, vd, color=RENK["mavi"], lw=2.2)
    a.axhline(5.0, ls="--", lw=1, color=RENK["gri"])
    a.annotate("+5 V rayı", (5, 5.12), color=RENK["gri"], fontsize=8.5)
    a.set_xlabel("giriş gerilimi (V)")
    a.set_ylabel("düğüm gerilimi (V)", color=RENK["mavi"])
    a.tick_params(axis="y", colors=RENK["mavi"])
    a.set_ylim(0, 7)

    b = a.twinx()
    b.plot(vin, iin, color=RENK["kirmizi"], lw=1.6, ls="-")
    b.set_ylabel("kelepçe akımı (mA)", color=RENK["kirmizi"])
    b.tick_params(axis="y", colors=RENK["kirmizi"])
    b.spines["top"].set_visible(False)
    b.spines["left"].set_visible(False)
    b.set_ylim(0, 8)

    for x in (230, 400):
        i = int(np.argmin(abs(vin - x)))
        a.plot(x, vd[i], "o", color=RENK["mavi"], ms=6)
        a.annotate(f"{x} V →  {vd[i]:.2f} V,  {iin[i]:.1f} mA",
                   (x, vd[i]), textcoords="offset points", xytext=(-8, 14),
                   ha="right", color=EKSEN, fontsize=8.5, weight="600")

    a.set_title("S2b · Arıza dayanımı — 400 V girişte bile düğüm 5.7 V'ta kelepçeleniyor")
    kaydet(f, "s2b-kelepce.svg")


# ═══════════════════════════════════ S2c — örtüşme süzgeci
def g_suzgec():
    f, a = yeni()
    for etiket, deger, renk, kalin in (
            ("100 nF  →  178 Hz  ✗", "100n", RENK["kirmizi"], 1.6),
            ("10 nF  →  1.8 kHz", "10n", RENK["gri"], 1.4),
            ("1 nF  →  17.8 kHz  ✓", "1n", RENK["yesil"], 2.4)):
        _, d = spice.kos(sim_bolucu.netlist_ac(deger), GECICI / f"g2_ac{deger}")
        veri = spice.degerler(d / "ac.txt")
        fr = np.array([s[0] for s in veri])
        db = np.array([s[1] for s in veri])
        a.semilogx(fr, db - db[0], color=renk, lw=kalin, label=etiket)

    a.axvline(8000, ls="--", lw=1.2, color=RENK["turuncu"])
    a.annotate("ADC sınırı\n8 kHz", (8600, -26), color=RENK["turuncu"],
               fontsize=8.5, weight="600")
    a.axhline(-3, ls=":", lw=1, color=RENK["gri"])
    a.set_xlabel("frekans (Hz)")
    a.set_ylabel("kazanç (dB, normalize)")
    a.set_ylim(-40, 3)
    a.set_title("S2c · Düğüm kondansatörü — 100nF osiloskop kipini öldürürdü")
    a.legend(frameon=False, fontsize=8.5, loc="lower left")
    kaydet(f, "s2c-suzgec.svg")


# ═══════════════════════════════════ S3a — şönt kademeleri
def g_sont():
    f, a = yeni()
    for etiket, (sont, _adet), renk in zip(
            ("1× 10R  →  0–31 mA", "10× 10R = 1R  →  0–313 mA",
             "30× 10R = 0.33R  →  0–939 mA"),
            sim_akim.SONTLAR.values(),
            (RENK["mavi"], RENK["turuncu"], RENK["yesil"])):
        imaks = 2.478 / sim_akim.KAZANC / sont
        _, d = spice.kos(sim_akim.netlist_dc(sont, "0", imaks), GECICI / f"g3_{sont:.3f}")
        veri = spice.degerler(d / "dc.txt")
        ii = np.array([s[0] for s in veri]) * 1e3
        vo = np.array([s[2] for s in veri])
        a.plot(ii, vo, color=renk, lw=2.2, label=etiket)

    a.axhline(2.478, ls="--", lw=1.2, color=RENK["gri"])
    a.annotate("AREF = 2.478 V  (ADC tavanı)", (12, 2.52),
               color=RENK["gri"], fontsize=8.5)
    a.set_xscale("log")
    a.set_xlabel("akım (mA, log)")
    a.set_ylabel("LM358 çıkışı → A1 (V)")
    a.set_ylim(0, 2.75)
    a.set_title("S3a · Üç kademe, aynı çıkış aralığı — kazanç 7.911")
    a.legend(frameon=False, fontsize=8.5, loc="upper left")
    kaydet(f, "s3a-sont.svg")


# ═══════════════════════════════════ S3b — LM358 bant genişliği
def g_bant():
    _, d = spice.kos(sim_akim.netlist_ac(10.0), GECICI / "g3_ac")
    veri = spice.degerler(d / "ac.txt")
    fr = np.array([s[0] for s in veri])
    db = np.array([s[1] for s in veri])

    f, a = yeni()
    a.semilogx(fr, db, color=RENK["mavi"], lw=2.2)
    a.axhline(db[0], ls="--", lw=1, color=RENK["gri"])
    a.axhline(db[0] - 3, ls=":", lw=1.2, color=RENK["gri"])
    a.annotate(f"kazanç 7.911  ({db[0]:.1f} dB)", (12, db[0] + .7),
               color=RENK["gri"], fontsize=8.5)

    a.axvline(8000, ls="--", lw=1.4, color=RENK["turuncu"])
    a.annotate("ADC sınırı\n8 kHz", (4200, 4), color=RENK["turuncu"],
               fontsize=8.5, weight="600", ha="right")
    a.axvline(89100, ls="--", lw=1.4, color=RENK["yesil"])
    a.annotate("LM358 −3 dB\n89.1 kHz", (100000, 10), color=RENK["yesil"],
               fontsize=8.5, weight="600")

    a.set_xlabel("frekans (Hz)")
    a.set_ylabel("kazanç (dB)")
    a.set_ylim(0, 20)
    a.set_title("S3b · Darboğaz LM358 değil, ADC — op-amp 11 kat daha hızlı")
    kaydet(f, "s3b-bant.svg")


# ═══════════════════════════════════ S4 — enerji sayacı kayması
def g_enerji():
    f32 = np.float32
    dt_us, watt = 220, 0.1
    n = 2_000_000
    artis = f32(f32(watt) * f32(dt_us * 1e-6))

    adim = n // 400
    t, gercek, kayan, tam = [], [], [], []
    e_f = f32(0.0)
    e_pj = 0
    for i in range(n):
        e_f = f32(e_f + artis)
        e_pj += int(f32(watt) * f32(1e6)) * dt_us
        # ilk saniyeyi atla: gercek deger sifira yakinken bagil hata patlar
        if i % adim == 0 and i * dt_us / 1e6 >= 5.0:
            t.append(i * dt_us / 1e6)
            gercek.append(watt * i * dt_us / 1e6)
            kayan.append(float(e_f))
            tam.append(e_pj / 1e12)

    t = np.array(t)
    gercek = np.array(gercek)
    hata_f = (np.array(kayan) - gercek) / gercek * 100
    hata_t = (np.array(tam) - gercek) / gercek * 100

    f, a = yeni()
    a.plot(t, hata_f, color=RENK["kirmizi"], lw=2.2, label="float32 (yanlış yol)")
    a.plot(t, hata_t, color=RENK["yesil"], lw=2.4, label="uint64 pikojoule (firmware)")
    a.axhline(0, lw=1, color=RENK["gri"])
    a.set_xlabel("geçen süre (saniye, 0.1 W yükte)")
    a.set_ylabel("enerji sayacındaki hata (%)")
    a.set_title("S4 · float32 sayacı sürükleniyor, tam sayı hiç kaymıyor")
    a.legend(frameon=False, fontsize=8.5, loc="upper left")
    a.annotate(f"{hata_f[-1]:.2f}%", (t[-1], hata_f[-1]),
               textcoords="offset points", xytext=(-6, 6), ha="right",
               color=RENK["kirmizi"], fontsize=9, weight="700")
    a.annotate("0.000000%", (t[-1], 0), textcoords="offset points",
               xytext=(-6, -16), ha="right",
               color=RENK["yesil"], fontsize=9, weight="700")
    kaydet(f, "s4-enerji.svg")


if __name__ == "__main__":
    import shutil
    print("Grafikler uretiliyor -> ../gorsel/")
    g_referans()
    g_bolucu()
    g_kelepce()
    g_suzgec()
    g_sont()
    g_bant()
    g_enerji()
    shutil.rmtree(GECICI, ignore_errors=True)
    print("bitti")
