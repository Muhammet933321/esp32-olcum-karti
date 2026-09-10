# -*- coding: utf-8 -*-
"""S1 — TL431 gerilim referansi ve AREF yuku.

Sorun: ATmega328P'nin AREF pini bosta degildir; ADC etkinken ic merdiven
direnci uzerinden yaklasik 32 kohm'luk bir yuk gorunur (2.495 V'ta ~78 uA).
AREF'e seri konan koruma direnci bu akimi tasidigi icin uzerinde gerilim
dusurur ve referansi kaydirir.

Bu simulasyon seri direncin ne kadar kaydirdigini olcer ve dogru degeri secer.
"""
from __future__ import annotations

from pathlib import Path

import spice

AREF_YUKU = 32e3        # ATmega328P AREF ic merdiven direnci (tipik)
TL431_V = 2.495         # TL431 referans gerilimi


def netlist(seri_direnc: float, aref_yuku: float) -> str:
    return f"""* TL431 referans + AREF yuku
V5 v5 0 DC 5.0
Rbias v5 katot 1k
* TL431 davranissal model: 2.495 V'u tutmak icin gereken akimi ceker
BTL431 katot 0 I = max(0, (V(katot)-{TL431_V})/0.2)
* seri koruma direnci ve AREF pini
Rs katot aref {seri_direnc}
Caref aref 0 100n
* ATmega AREF ic yuku
Rload aref 0 {aref_yuku}
.control
op
wrdata op.txt v(katot) v(aref) i(V5)
.endc
.end
"""


def kosu(rapor: spice.Rapor) -> None:
    rapor.bilgi("S1 — TL431 referansi ve AREF seri direnci")
    rapor.bilgi("")

    # --- TL431 kendisi dogru gerilimi tutuyor mu, akimi yeterli mi
    _, dizin = spice.kos(netlist(470, AREF_YUKU), Path("_s1_470"))
    (_, v_katot, v_aref, i_v5) = spice.degerler(dizin / "op.txt")[0]

    rapor.esit("TL431 katot gerilimi", v_katot, TL431_V, 0.001, " V")

    # TL431'in kendi calisma akimi: bias akimi eksi AREF'e giden
    i_bias = (5.0 - v_katot) / 1e3
    i_aref = v_aref / AREF_YUKU
    i_tl431 = i_bias - i_aref
    rapor.kosul("TL431 calisma akimi >= 1 mA",
                i_tl431 >= 1e-3,
                f"{i_tl431 * 1e3:.2f} mA  (bias {i_bias * 1e3:.2f} mA, "
                f"AREF {i_aref * 1e6:.0f} uA)")

    rapor.bilgi("")
    rapor.bilgi("  Seri direncin AREF'te yarattigi kayma:")

    # --- seri direnc taramasi
    #
    # Iki olcut var:
    #   dusum      — AREF'i ne kadar kaydiriyor. Sabit oldugu icin kalibrasyon
    #                yutar, ama menzilden yiyor.
    #   surunme    — AREF ic direnci SICAKLIKLA degistiginde referans ne kadar
    #                oynuyor. Asil onemli olan bu; kalibrasyon bunu yutamaz.
    #                Ic direnc sicaklikla ~+-%5 oynuyor kabul edildi.
    #   ariza akimi— firmware yanlislikla dahili referansi secerse akan akim.
    kayma = {}
    rapor.bilgi("    Rs      AREF      dusum     surunme   ariza akimi")
    rapor.bilgi("    " + "-" * 52)
    for r in (100, 220, 470, 1000, 4700):
        vlar = []
        for yuk in (AREF_YUKU * 0.95, AREF_YUKU, AREF_YUKU * 1.05):
            _, d = spice.kos(netlist(r, yuk), Path(f"_s1_r{r}_{int(yuk)}"))
            vlar.append(spice.degerler(d / "op.txt")[0][2])
        va = vlar[1]
        dusum_mv = (TL431_V - va) * 1e3
        surunme = (max(vlar) - min(vlar)) / va * 100
        ariza_ma = (5.0 - TL431_V) / r * 1e3
        kayma[r] = (va, dusum_mv, surunme, ariza_ma)
        rapor.bilgi(f"    {r:>5}  {va:.4f} V  {dusum_mv:6.1f} mV  "
                    f"%{surunme:.3f}    {ariza_ma:5.1f} mA")

    rapor.bilgi("")

    # --- kararlar
    rapor.kosul("4.7K seri direnc REDDEDILDI",
                kayma[4700][1] > 100,
                f"AREF'i {kayma[4700][1]:.0f} mV dusuruyor — menzilin %13'u gider")

    SECILEN = 220
    va, dusum, surunme, ariza = kayma[SECILEN]
    rapor.esit(f"SECILEN Rs={SECILEN} ohm -> AREF", va, 2.478, 0.005, " V")
    rapor.kosul(f"  dusum < %1 (kalibrasyon yutar)",
                dusum / (TL431_V * 1e3) * 100 < 1.0,
                f"{dusum:.1f} mV = %{dusum / (TL431_V * 1e3) * 100:.2f}")
    rapor.kosul(f"  sicaklik surunmesi < %0.1",
                surunme < 0.1, f"%{surunme:.3f}")
    rapor.kosul(f"  ariza akimi < 20 mA (cip guvende)",
                ariza < 20, f"{ariza:.1f} mA")


if __name__ == "__main__":
    r = spice.Rapor()
    kosu(r)
    print()
    raise SystemExit(0 if r.yazdir() else 1)
