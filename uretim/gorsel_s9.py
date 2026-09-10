# -*- coding: utf-8 -*-
"""S9 sonuclarindan kanit grafikleri.

    python gorsel_s9.py      (once sim_kart.py kosmus olmali)

Bu grafiklerdeki her nokta GERCEK firmware'in seri portundan cikan sayidir;
hicbiri elle girilmedi. Kaynak: kanit/s9-veri.json
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

BURASI = Path(__file__).parent
VERI = BURASI.parent / "arsiv" / "asama1" / "kanit" / "s9-veri.json"
CIKTI = BURASI.parent / "gorsel"
CIKTI.mkdir(exist_ok=True)

EKSEN = "#8a92a0"
IZGARA = "#8a92a055"
RENK = {"mavi": "#4b7bec", "turuncu": "#f0883e", "yesil": "#2ea36b",
        "kirmizi": "#e5534b", "mor": "#a371f7", "gri": "#8a92a0"}

plt.rcParams.update({
    "figure.facecolor": "none", "axes.facecolor": "none",
    "savefig.facecolor": "none", "savefig.transparent": True,
    "text.color": EKSEN, "axes.labelcolor": EKSEN, "axes.edgecolor": EKSEN,
    "xtick.color": EKSEN, "ytick.color": EKSEN, "grid.color": IZGARA,
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


def g1_dogrusallik(d):
    """Uygulanan gerilim vs firmware'in bildirdigi gerilim, hata LSB cinsinden."""
    o = np.array(d["olcumler"])          # v_uyg, i_uyg, v_ok, i_ok, w_ok
    lsb = d["ozet"]["lsb_v"]
    v_uyg, v_ok = o[:, 0], o[:, 2]
    hata_lsb = (v_ok - v_uyg) / lsb

    f, a = plt.subplots(1, 2, figsize=(7.4, 3.2))
    for x in a:
        x.grid(True, lw=.6, alpha=.6)
        for k in ("top", "right"):
            x.spines[k].set_visible(False)

    a[0].plot([0, 26], [0, 26], lw=1, color=RENK["gri"], ls="--",
              label="ideal (y = x)")
    a[0].plot(v_uyg, v_ok, "o", ms=7, color=RENK["mavi"], label="firmware ciktisi")
    a[0].set_xlabel("uygulanan gerilim (V)")
    a[0].set_ylabel("kartin bildirdigi (V)")
    a[0].set_title("Dogrusallik")
    a[0].legend(frameon=False, fontsize=8, loc="upper left")

    a[1].axhspan(-1, 1, color=RENK["yesil"], alpha=.13)
    a[1].axhline(0, lw=.8, color=RENK["gri"])
    a[1].plot(v_uyg, hata_lsb, "o-", ms=6, lw=1.2, color=RENK["turuncu"])
    a[1].set_ylim(-1.6, 1.6)
    a[1].set_xlabel("uygulanan gerilim (V)")
    a[1].set_ylabel("hata (ADC adimi)")
    a[1].set_title(f"Hata — 1 adim = {lsb*1000:.1f} mV")
    a[1].text(0.5, 0.93, "yesil serit: ±1 adim (kuantalama tabani)",
              transform=a[1].transAxes, ha="center", fontsize=8, color=EKSEN)
    kaydet(f, "s9a-dogrusallik.svg")


def g2_osiloskop(d):
    """Firmware'in 't' komutuyla yakaladigi 1000 ornek."""
    o = d["osilo"]
    ham = np.array(o["ornekler"])
    volt = ham * o["volt_adim"]
    t_ms = np.arange(len(ham)) / o["hz"] * 1000

    f, a = yeni(7.4, 3.2)
    beklenen = o["dc"] + o["ac_genlik"] * np.sin(2 * np.pi * o["ac_hz"] * t_ms / 1000)
    a.plot(t_ms, beklenen, lw=2.4, color=RENK["gri"], alpha=.45,
           label=f"uygulanan  {o['ac_hz']:.0f} Hz, {o['ac_genlik']:.0f} V tepe")
    a.plot(t_ms, volt, lw=1.0, color=RENK["mor"],
           label=f"karttan gelen {len(ham)} ornek")
    a.set_xlabel("zaman (ms)")
    a.set_ylabel("gerilim (V)")
    a.set_title(f"Osiloskop kipi — {o['hz']:,} ornek/sn, 8 bit"
                .replace(",", " "))
    a.legend(frameon=False, fontsize=8, loc="upper right")
    kaydet(f, "s9b-osiloskop.svg")


def g3_kalibrasyon(d):
    """Yanlis referansla olusan sistematik hatayi 'kv' nasil siliyor."""
    k = d["kalibrasyon"]
    f, a = yeni(5.4, 3.2)
    etiket = ["kalibrasyon\noncesi", "kalibrasyon\nsonrasi"]
    hata = [(k["once"] - k["uygulanan"]) * 1000,
            (k["sonra"] - k["uygulanan"]) * 1000]
    renkler = [RENK["kirmizi"], RENK["yesil"]]
    cubuk = a.bar(etiket, hata, width=.5, color=renkler, alpha=.85)
    a.axhline(0, lw=.9, color=EKSEN)
    lsb = d["ozet"]["lsb_v"] * 1000
    a.axhspan(-lsb, lsb, color=RENK["gri"], alpha=.15)
    for c, h in zip(cubuk, hata):
        a.text(c.get_x() + c.get_width() / 2, h + (2 if h >= 0 else -6),
               f"{h:+.1f} mV", ha="center", fontsize=9, color=EKSEN)
    a.set_ylabel("12.00 V'ta hata (mV)")
    a.set_title(f"'kv' kalibrasyonu — referans {k['aref_gercek']} V,"
                f" firmware {k['aref_sanilan']} V saniyor")
    a.text(0.5, 0.06, f"gri serit = ±1 ADC adimi ({lsb:.1f} mV)",
           transform=a.transAxes, ha="center", fontsize=8, color=EKSEN)
    kaydet(f, "s9c-kalibrasyon.svg")


def main() -> int:
    if not VERI.exists():
        print(f"once sim_kart.py kosmali — {VERI} yok")
        return 1
    d = json.loads(VERI.read_text(encoding="utf-8"))
    print("S9 kanit grafikleri -> ../gorsel/")
    g1_dogrusallik(d)
    g2_osiloskop(d)
    g3_kalibrasyon(d)
    print("bitti")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
