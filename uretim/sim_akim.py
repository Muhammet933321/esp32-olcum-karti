# -*- coding: utf-8 -*-
"""S3 — Sont + LM358 akim olcum kati.

LM358 icin davranissal makromodel kullaniliyor:
  acik cevrim kazanc 100 dB, GBW 700 kHz, slew 0.3 V/us,
  tek besleme cikis sinirlari (0.02 V .. Vcc-1.5 V), ayarlanabilir giris ofseti.

Dogrulanan sorular:
  1. Kazanc gercekten 1 + 47K/6.8K = 7.912 mi?
  2. 5 V tek beslemede cikis AREF'e (2.478 V) ulasabiliyor mu?
  3. LM358'in giris ofseti akim okumasini ne kadar bozuyor?
  4. Kapali cevrim bant genisligi ADC'nin 8 kHz'inin ustunde mi?
"""
from __future__ import annotations

from pathlib import Path

import spice

AREF = 2.478
RF, RG = 47e3, 6.8e3
KAZANC = 1 + RF / RG
VCC = 5.0

SONTLAR = {           # etiket -> (ohm, kac adet 10R paralel)
    "1x 10R":  (10.0, 1),
    "10x 10R": (1.0, 10),
    "30x 10R": (10.0 / 30, 30),
}

# LM358 davranissal makromodel.
#
# NOT: ngspice'in B-kaynagindaki `limit()` fonksiyonu beklendigi gibi
# calismiyor (akimi sinirlamak yerine kati doyuma surukluyor), o yuzden
# transkondüktans kati duz bir VCCS (G kaynagi). Slew rate SPICE'ta degil,
# asagida analitik olarak dogrulaniyor.
#
#   acik cevrim kazanc  = gm * Rp = 1e-3 * 1e8 = 1e5  (100 dB)
#   kutup               = 1/(2*pi*Rp*Cp) = 7.0 Hz
#   GBW                 = 1e5 * 7.0 = 700 kHz   (LM358 veri sayfasi)
LM358 = """
.subckt LM358 inp inn out vcc vee vos=2m
Vos nip inp DC {vos}
Ggm 0 n1 nip inn 1e-3
Rp n1 0 1e8
Cp n1 0 227p
Bo nout 0 V = min(max(V(n1), V(vee)+0.02), V(vcc)-1.5)
Ro nout out 50
.ends
"""

SLEW = 0.3e6        # LM358 veri sayfasi: 0.3 V/us


def netlist_dc(sont: float, vos: str, imaks: float) -> str:
    return f"""* sont + LM358 evirmeyen yukseltec, akim taramasi
{LM358}
V5 v5 0 DC {VCC}
Iyuk 0 sontust DC 0
Rsont sontust 0 {sont}
XU1 sontust geri cikis v5 0 LM358 vos={vos}
Rf cikis geri {RF}
Rg geri 0 {RG}
.control
dc Iyuk 0 {imaks} {imaks / 400}
wrdata dc.txt v(sontust) v(cikis)
.endc
.end
"""


def netlist_ac(sont: float) -> str:
    return f"""* kapali cevrim bant genisligi
{LM358}
V5 v5 0 DC {VCC}
Vin sontust 0 DC 0.15 AC 1
XU1 sontust geri cikis v5 0 LM358 vos=0
Rf cikis geri {RF}
Rg geri 0 {RG}
.control
ac dec 40 10 10meg
wrdata ac.txt vdb(cikis)
.endc
.end
"""


def kesim(veri) -> float:
    plato = veri[0][1]
    for f, db in veri:
        if db <= plato - 3.0:
            return f
    return float("inf")


def kosu(rapor: spice.Rapor) -> None:
    rapor.bilgi("S3 — Sont + LM358 akim olcum kati")
    rapor.bilgi("")
    rapor.bilgi(f"    Tasarim kazanci = 1 + {RF/1e3:.0f}K/{RG/1e3:.1f}K "
                f"= {KAZANC:.4f}")
    rapor.bilgi(f"    Maks sont gerilimi = {AREF:.3f} / {KAZANC:.3f} "
                f"= {AREF / KAZANC * 1e3:.1f} mV")
    rapor.bilgi("")

    # ------------------------------------------------ 1. kazanc dogrulama
    sont, _ = SONTLAR["1x 10R"]
    imaks = AREF / KAZANC / sont
    _, d = spice.kos(netlist_dc(sont, "0", imaks), Path("_s3_kazanc"))
    veri = spice.degerler(d / "dc.txt")

    orta = veri[len(veri) // 2]
    olculen_kazanc = orta[2] / orta[1]
    rapor.esit("Kapali cevrim kazanc", olculen_kazanc, KAZANC, 0.002)

    en_yuksek_cikis = max(v for *_, v in veri)
    rapor.kosul("Cikis AREF'e (2.478 V) ulasabiliyor",
                en_yuksek_cikis >= AREF * 0.999,
                f"en yuksek cikis {en_yuksek_cikis:.3f} V "
                f"(LM358 5 V'ta ~3.5 V'a kadar cikar)")
    rapor.bilgi("")

    # ------------------------------------------------ 2. akim kademeleri
    rapor.bilgi("  Akim kademeleri (30 adet R001 10R'den):")
    rapor.bilgi("    kademe      sont      tam olcek   cozunurluk   direnc basi isi")
    rapor.bilgi("    " + "-" * 62)
    for etiket, (sont, adet) in SONTLAR.items():
        fs = AREF / KAZANC / sont
        coz = fs / 1024
        # her direncin ustundeki gerilim ayni: sont gerilimi
        p_direnc = (AREF / KAZANC) ** 2 / (sont * adet) if adet else 0
        rapor.bilgi(f"    {etiket:<10} {sont:>7.3f} ohm  {fs*1e3:>8.1f} mA  "
                    f"{coz*1e6:>8.0f} uA   {p_direnc*1e3:>6.1f} mW")

    p_hepsi = [(AREF / KAZANC) ** 2 / (s * a) for s, a in SONTLAR.values()]
    rapor.kosul("Her kademede direnc basina isi ayni ve < 15 mW",
                max(p_hepsi) < 0.015 and (max(p_hepsi) - min(p_hepsi)) < 1e-6,
                f"{p_hepsi[0]*1e3:.1f} mW — 1/4W direncin %{p_hepsi[0]/0.25*100:.0f}'i")
    rapor.bilgi("")

    # ------------------------------------------------ 3. ofset duyarliligi
    rapor.bilgi("  LM358 giris ofsetinin akim okumasina etkisi:")
    rapor.bilgi("    ofset     cikis kaymasi   10R'de hata   tam olcegin %'si")
    rapor.bilgi("    " + "-" * 58)
    for vos_mv in (2, 7):
        sont, _ = SONTLAR["1x 10R"]
        imaks = AREF / KAZANC / sont
        _, d = spice.kos(netlist_dc(sont, f"{vos_mv}m", imaks),
                         Path(f"_s3_vos{vos_mv}"))
        v0 = spice.degerler(d / "dc.txt")[0][2]      # sifir akimda cikis
        hata_ma = v0 / KAZANC / sont * 1e3
        yuzde = hata_ma / (imaks * 1e3) * 100
        rapor.bilgi(f"    {vos_mv:>2} mV      {v0*1e3:>8.1f} mV     "
                    f"{hata_ma:>7.3f} mA    %{yuzde:.2f}")
        if vos_mv == 7:
            rapor.kosul("En kotu ofset tam olcegin %3'unden az",
                        yuzde < 3.0,
                        f"%{yuzde:.2f} — yazilimda sifirlanacak, kalanı surunme")
    rapor.bilgi("")

    # ------------------------------------------------ 4. bant genisligi
    sont, _ = SONTLAR["1x 10R"]
    _, d = spice.kos(netlist_ac(sont), Path("_s3_ac"))
    fc = kesim(spice.degerler(d / "ac.txt"))
    rapor.esit("Kucuk sinyal bandi (SPICE, = GBW/kazanc)",
               fc, 700e3 / KAZANC, 0.05, " Hz")
    rapor.kosul("  ADC sinirinin (8 kHz) uzerinde",
                fc > 8000,
                f"{fc/1e3:.1f} kHz — darbogaz LM358 degil, ADC")

    # Slew rate SPICE'ta modellenmedi; analitik dogrulama:
    # tam olcek cikis 0..AREF, yani tepe genlik AREF/2 etrafinda salinim.
    tepe = AREF / 2
    fpbw = SLEW / (2 * 3.141592653589793 * tepe)
    rapor.bilgi("")
    rapor.bilgi(f"  Slew siniri (analitik): {SLEW/1e6:.1f} V/us, "
                f"tam olcek tepe genlik {tepe:.3f} V")
    rapor.kosul("Tam guc bandi da 8 kHz'in uzerinde",
                fpbw > 8000,
                f"{fpbw/1e3:.1f} kHz — buyuk sinyalde de LM358 yetiyor")


if __name__ == "__main__":
    r = spice.Rapor()
    kosu(r)
    print()
    raise SystemExit(0 if r.yazdir() else 1)
