# -*- coding: utf-8 -*-
"""S2 — Gerilim bolucu, koruma kelepceleri ve ortusme (anti-alias) suzgeci.

Uc soru:
  1. Bolucu 0-30 V arasi dogrusal mi, oran gercekten 1:11 mi?
  2. Girise kazara 100 V (hatta 400 V) gelirse Arduino sag kaliyor mu?
  3. Dugumdeki kondansator osiloskop kipini oldurmuyor mu?

3. soru kritik: bolucu dugumunde gorulen Thevenin direnci 100K||10K = 9.09K.
Oraya 100nF koyarsan kesim frekansi 175 Hz olur — 8 kHz'lik osiloskop kipi
tamamen olur. Dogru deger cok daha kucuk.
"""
from __future__ import annotations

import math
from pathlib import Path

import spice

AREF = 2.478          # S1'den: TL431 + 220 ohm seri
UST = 100e3           # R025
ALT = 10e3            # R032
ORAN = (UST + ALT) / ALT

D1N4148 = (".model D1N4148 D(IS=4.352E-9 N=1.906 BV=110 IBV=1E-4 RS=0.6458 "
           "CJO=7.048E-13 VJ=0.869 M=0.03 FC=0.5 TT=3.48E-9)")


def netlist_dc(vmaks: float, kapasite: str) -> str:
    return f"""* gerilim bolucu + kelepceler, DC tarama
{D1N4148}
V5 v5 0 DC 5.0
Vin giris 0 DC 0
Rust giris dugum {UST}
Ralt dugum 0 {ALT}
Cf dugum 0 {kapasite}
Dust dugum v5 D1N4148
Dalt 0 dugum D1N4148
.control
dc Vin 0 {vmaks} {vmaks / 400}
wrdata dc.txt v(dugum) i(Vin) i(V5)
.endc
.end
"""


def netlist_ac(kapasite: str) -> str:
    return f"""* bolucunun frekans tepkisi
Vin giris 0 DC 0 AC 1
Rust giris dugum {UST}
Ralt dugum 0 {ALT}
Cf dugum 0 {kapasite}
.control
ac dec 40 1 1meg
wrdata ac.txt vdb(dugum)
.endc
.end
"""


def kesim_frekansi(veri) -> float:
    """-3 dB noktasini bulur (alcak frekans platosuna gore)."""
    plato = veri[0][1]
    for f, db in veri:
        if db <= plato - 3.0:
            return f
    return float("inf")


def kosu(rapor: spice.Rapor) -> None:
    rapor.bilgi("S2 — Gerilim bolucu, kelepceler ve ortusme suzgeci")
    rapor.bilgi("")

    # ---------------------------------------------------- 1. dogrusallik
    _, d = spice.kos(netlist_dc(30, "1n"), Path("_s2_dc30"))
    veri = spice.degerler(d / "dc.txt")

    calisma = [(vin, vd) for vin, vd, *_ in veri if vd < 2.0]   # kelepce oncesi
    en_kotu = 0.0
    for vin, vd in calisma:
        if vin < 1.0:
            continue
        beklenen = vin / ORAN
        en_kotu = max(en_kotu, abs(vd - beklenen) / beklenen)

    rapor.esit("Bolme orani (20 V girise karsilik)",
               next(vin / vd for vin, vd in calisma if abs(vin - 20) < 0.1),
               ORAN, 0.001)
    rapor.kosul("Dogrusallik sapmasi < %0.1",
                en_kotu < 0.001, f"en kotu %{en_kotu * 100:.4f}")

    tam_olcek = AREF * ORAN
    rapor.bilgi(f"    Tam olcek : {tam_olcek:.2f} V")
    rapor.bilgi(f"    Cozunurluk: {tam_olcek / 1024 * 1e3:.1f} mV / adim")
    rapor.bilgi("")

    # ---------------------------------------------------- 2. ariza koruma
    rapor.bilgi("  Ariza dayanimi — girise yanlislikla yuksek gerilim gelirse:")
    _, d = spice.kos(netlist_dc(400, "1n"), Path("_s2_ariza"))
    veri = spice.degerler(d / "dc.txt")

    for hedef in (30, 100, 230, 400):
        vin, vd, i_in, i_v5 = min(veri, key=lambda s: abs(s[0] - hedef))
        rapor.bilgi(f"    {vin:6.1f} V girisde -> dugum {vd:.3f} V, "
                    f"kelepce akimi {abs(i_in) * 1e3:6.2f} mA")

    en_yuksek = max(vd for _, vd, *_ in veri)
    en_buyuk_akim = max(abs(i) for *_, i, _ in veri)

    rapor.kosul("400 V'ta dugum 6 V'un altinda kaliyor",
                en_yuksek < 6.0, f"en yuksek {en_yuksek:.3f} V")
    rapor.kosul("Kelepce akimi 1N4148 sinirinin (200 mA) cok altinda",
                en_buyuk_akim < 0.02,
                f"en buyuk {en_buyuk_akim * 1e3:.2f} mA")
    rapor.kosul("5 V rayina basilan akim Arduino tuketiminin altinda",
                en_buyuk_akim < 0.02,
                f"{en_buyuk_akim * 1e3:.2f} mA << ~30 mA — ray yukselmez")
    rapor.bilgi("")

    # ------------------------------------------- 3. ortusme suzgeci (BUG)
    rapor.bilgi("  Dugum kondansatorunun osiloskop kipine etkisi:")
    thevenin = UST * ALT / (UST + ALT)
    rapor.bilgi(f"    Dugumde gorulen Thevenin direnci: {thevenin / 1e3:.2f} kohm")

    kesimler = {}
    for etiket, deger in (("100nF", "100n"), ("10nF", "10n"), ("1nF", "1n")):
        _, d = spice.kos(netlist_ac(deger), Path(f"_s2_ac_{etiket}"))
        fc = kesim_frekansi(spice.degerler(d / "ac.txt"))
        kesimler[etiket] = fc
        teorik = 1 / (2 * math.pi * thevenin * float(deger.rstrip("n")) * 1e-9)
        rapor.bilgi(f"    C = {etiket:>6} -> kesim {fc:>9.0f} Hz "
                    f"(teorik {teorik:.0f} Hz)")

    rapor.bilgi("")
    rapor.kosul("100nF REDDEDILDI — osiloskop kipini oldururdu",
                kesimler["100nF"] < 1000,
                f"kesim {kesimler['100nF']:.0f} Hz, 8 kHz bandin cok altinda")
    rapor.kosul("SECILEN 1nF — 8 kHz bandi geciriyor",
                kesimler["1nF"] > 12000,
                f"kesim {kesimler['1nF']:.0f} Hz > 8 kHz")
    rapor.kosul("SECILEN 1nF — ortusmeyi hala bastiriyor",
                kesimler["1nF"] < 40000,
                f"kesim {kesimler['1nF']:.0f} Hz < 38 kHz (Nyquist)")


if __name__ == "__main__":
    r = spice.Rapor()
    kosu(r)
    print()
    raise SystemExit(0 if r.yazdir() else 1)
