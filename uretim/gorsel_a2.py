# -*- coding: utf-8 -*-
"""Asama 2 kanit grafikleri.

    python gorsel_a2.py

Her egri ngspice ciktisidir; hicbiri elle cizilmedi.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import spice                             # noqa: E402
import sim2_giris as a2                  # noqa: E402

BURASI = Path(__file__).parent
CIKTI = BURASI.parent / "gorsel"
CIKTI.mkdir(exist_ok=True)

EKSEN = "#8a92a0"
RENK = {"mavi": "#4b7bec", "turuncu": "#f0883e", "yesil": "#2ea36b",
        "kirmizi": "#e5534b", "mor": "#a371f7", "gri": "#8a92a0"}

plt.rcParams.update({
    "figure.facecolor": "none", "axes.facecolor": "none",
    "savefig.facecolor": "none", "savefig.transparent": True,
    "text.color": EKSEN, "axes.labelcolor": EKSEN, "axes.edgecolor": EKSEN,
    "xtick.color": EKSEN, "ytick.color": EKSEN, "grid.color": "#8a92a055",
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "600",
    "figure.dpi": 110,
})


def yeni(en=6.4, boy=3.4):
    f, a = plt.subplots(figsize=(en, boy))
    a.grid(True, lw=.6, alpha=.6)
    for k in ("top", "right"):
        a.spines[k].set_visible(False)
    return f, a


def kaydet(f, ad):
    f.tight_layout()
    f.savefig(CIKTI / ad, format="svg", transparent=True)
    plt.close(f)
    print(f"  {ad}  ({(CIKTI / ad).stat().st_size // 1024} KB)")


def g1_kelepce():
    """Kelepce secenekleri: dogrusallik hatasi ve ariza gerilimi."""
    veriler = {}
    for sec in "ACD":
        _, d = spice.kos(a2.netlist(sec, 300.0), BURASI / f"_g_{sec}")
        veriler[sec] = spice.degerler(d / "dc.txt")

    f, ax = plt.subplots(1, 2, figsize=(7.6, 3.3))
    for a_ in ax:
        a_.grid(True, lw=.6, alpha=.6)
        for k in ("top", "right"):
            a_.spines[k].set_visible(False)

    etiketler = {"A": ("kelepce yok (11:1)", RENK["gri"], "--"),
                 "C": ("TL431 kelepce, 11:1", RENK["kirmizi"], "-"),
                 "D": ("TL431 kelepce, 15.71:1  SECILEN", RENK["yesil"], "-")}
    for sec, (ad, renk, ls) in etiketler.items():
        v = np.array(veriler[sec])
        oran = a2.ORAN_D if sec == "D" else a2.ORAN
        m = v[:, 0] > 1.0
        ppm = (v[m, 1] - v[m, 0] / oran) / (v[m, 0] / oran) * 1e6
        ax[0].plot(v[m, 0], ppm, color=renk, ls=ls, lw=1.8, label=ad)
        ax[1].plot(v[:, 0], v[:, 1], color=renk, ls=ls, lw=1.8, label=ad)

    ax[0].axhspan(-1000, 1000, color=RENK["yesil"], alpha=.12)
    ax[0].axvline(32.17, color=RENK["mavi"], lw=1, ls=":")
    ax[0].text(32.5, -8000, "tam olcek\n32.2 V", fontsize=8, color=RENK["mavi"])
    ax[0].set_xlim(0, 40)
    ax[0].set_ylim(-20000, 2000)
    ax[0].set_xlabel("uygulanan gerilim (V)")
    ax[0].set_ylabel("dogrusallik hatasi (ppm)")
    ax[0].set_title("Kelepce sizintisi menzili nerede kesiyor\n"
                    "yesil serit: ±1000 ppm (%0.1)", fontsize=9.5)
    ax[0].legend(frameon=False, fontsize=7.5, loc="lower left",
                 bbox_to_anchor=(0.0, 0.02))

    ax[1].axhline(3.6, color=RENK["kirmizi"], lw=1.2, ls="--")
    ax[1].text(150, 3.68, "ADS1115 mutlak azami 3.6 V", fontsize=8,
               color=RENK["kirmizi"])
    ax[1].set_xlabel("uygulanan gerilim (V)  —  ariza bolgesi")
    ax[1].set_ylabel("ADC ucundaki gerilim (V)")
    ax[1].set_title("Arizada ucu ne koruyor")
    ax[1].set_ylim(0, 4.4)
    kaydet(f, "a2a-kelepce.svg")


def g2_menzil():
    """Sont merdiveninin kapsadigi akim araligi ve cozunurlugu."""
    lsb = 7.8125e-6
    sontlar = [("10 Ω", 10.0, 0.25), ("1 Ω", 1.0, 0.25),
               ("0.1 Ω", 0.1, 5.0), ("15 mΩ", 0.015, 2.0)]
    f, a = yeni(6.8, 3.4)
    renkler = [RENK["mavi"], RENK["yesil"], RENK["turuncu"], RENK["mor"]]
    for (ad, r, w), renk in zip(sontlar, renkler):
        fs = min(0.256 / r, (w / r) ** 0.5)
        adim = lsb / r
        a.plot([adim, fs], [r, r], color=renk, lw=6, solid_capstyle="round",
               alpha=.85)
        a.text(fs * 1.25, r, f"  {ad}", va="center", fontsize=9, color=renk)
        a.text(adim * 0.75, r, f"{adim*1e6:.2f} µA  ", va="center",
               ha="right", fontsize=7.5, color=EKSEN)
    # Asama 1 karsilastirmasi
    a.plot([30.49e-6, 0.0312], [30, 30], color=RENK["gri"], lw=6,
           solid_capstyle="round", alpha=.5)
    a.text(0.0312 * 1.25, 30, "  Asama 1 (tek kademe)", va="center",
           fontsize=8.5, color=RENK["gri"])
    a.set_xscale("log")
    a.set_yscale("log")
    a.set_xlim(2e-7, 200)
    a.set_xlabel("akim (A) — cizginin sol ucu ADIM, sag ucu TAM OLCEK")
    a.set_ylabel("sont (Ω)")
    a.set_title("Sont merdiveni: 0.78 µA'dan 11.5 A'e")
    kaydet(f, "a2b-menzil.svg")


def g3_hata():
    """15 mohm kademesinde hata butcesi: Kelvin ne kazandiriyor."""
    durum = ["Kelvinsiz\nkalibresiz", "Kelvinsiz\n10 A'de kalibre",
             "Kelvin ile\nkalibresiz"]
    # tasarim2.py ile ayni kalemler
    kalemler = {
        "ADC (kuantalama + ofset)": [0.0182, 0.0182, 0.0182],
        "termo-emk":                [0.0020, 0.0020, 0.0020],
        "lehim direnci (statik)":   [6.6667, 0.0, 0.0],
        "yuke bagli suruklenme":    [0.0, 0.2600, 0.0],
        "sont oz-isinmasi":         [0.0, 0.2250, 0.2250],
        "sont toleransi %1":        [0.0, 0.0, 1.0000],
    }
    f, a = yeni(6.6, 3.6)
    alt = np.zeros(3)
    renkler = [RENK["mavi"], RENK["gri"], RENK["kirmizi"], RENK["turuncu"],
               RENK["mor"], RENK["yesil"]]
    for (ad, v), renk in zip(kalemler.items(), renkler):
        a.bar(durum, v, bottom=alt, label=ad, color=renk, alpha=.88, width=.55)
        alt += np.array(v)
    for i, t in enumerate(alt):
        a.text(i, t * 1.15, f"%{t:.2f}", ha="center", fontsize=9.5,
               color=EKSEN)
    a.set_yscale("log")
    a.set_ylim(0.01, 20)
    a.set_ylabel("10 A olcumunde hata (%)")
    a.set_title("15 mΩ kademesi — Kelvin baglantinin gercek kazanci")
    a.legend(frameon=False, fontsize=7.5, loc="upper right", ncol=2)
    kaydet(f, "a2c-hata.svg")


if __name__ == "__main__":
    import shutil
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Asama 2 kanit grafikleri -> ../gorsel/")
    g1_kelepce()
    g2_menzil()
    g3_hata()
    for d in BURASI.glob("_g_*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    print("bitti")
