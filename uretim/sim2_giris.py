# -*- coding: utf-8 -*-
"""A2 — Asama 2 analog giris korumasi ve suzgecleri (ngspice).

Cevaplanan sorular:
  1. Kelepceyi nereye baglamali? Dort secenek taraniyor:
       A) kelepce YOK  — 100K seri direnc akimi sinirlar, ADS'in kendi ESD
                         diyodu 3.3 V'a kelepceler
       B) 3.3 V rayina — dugum 4.0 V'a cikar, ADS mutlak azamisi 3.6 V
       C) TL431 rayina (2.495 V), bolucu 11:1 — dugum 3.2 V'da kalir ama
                         diyot tam olcege yaklasirken SIZINTI yapip bolucuyu yukler
       D) TL431 rayina, bolucu 15.71:1 + PGA +-2.048 V — dugum 2.048 V'da
                         kaldigi icin diyot hep ters kutuplu, sizinti sifir
     Hangisi? Bunu iddia ile degil, tarama ile sececegiz.

  2. Kelepce sizintisi olcum araligini nerede bozuyor?
  3. Ariza akimi ADS1115'in +-10 mA mutlak azamisinin altinda mi?
  4. Akim girisindeki diferansiyel RC suzgeci ne kadar hata katiyor?
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
R_UST, R_ALT = 100e3, 10e3          # Asama 1 bolucusu, oran 11
R_ALT_D = 6.8e3                     # secenek D: oran 15.71
ORAN = (R_UST + R_ALT) / R_ALT
ORAN_D = (R_UST + R_ALT_D) / R_ALT_D
C_SUZ = "1n"
VDD = 3.3
TL431_V = 2.495
ADS_MUTLAK = VDD + 0.3        # 3.6 V
ADS_AKIM_MUTLAK = 10e-3       # veri sayfasi: surekli giris akimi +-10 mA

D1N4148 = (".model D1N4148 D(IS=4.352E-9 N=1.906 BV=110 IBV=1E-4 RS=0.6458 "
           "CJO=7.048E-13 VJ=0.869 M=0.03 FC=0.5 TT=3.48E-9)")

# ADS1115'in kendi ESD diyodu — hangi secenekte olursa olsun devrede
ESD = "Desd dugum v33 D1N4148"


def netlist(secenek: str, vmaks: float) -> str:
    """DC tarama; secenek A / B / C / D."""
    ralt = R_ALT_D if secenek == "D" else R_ALT
    TL431_KELEPCE = ("Rbias v33 tlray 220\n"
                     "BTL431 tlray 0 I = max(0, (V(tlray)-2.495)/0.2)\n"
                     "Ctl tlray 0 100n\n"
                     "Dklm dugum tlray D1N4148")
    kelepce = {
        "A": "* harici kelepce yok",
        "B": "Dklm dugum v33 D1N4148",
        "C": TL431_KELEPCE,
        "D": TL431_KELEPCE,
    }[secenek]
    return f"""* Asama 2 gerilim girisi — secenek {secenek}
{D1N4148}
V33 v33 0 DC {VDD}
Vin giris 0 DC 0
Rust giris dugum {R_UST}
Ralt dugum 0 {ralt}
Cf dugum 0 {C_SUZ}
{ESD}
{kelepce}
.control
dc Vin 0 {vmaks} {vmaks/2000}
wrdata dc.txt v(dugum) i(Vin) i(V33)
.endc
.end
"""


def netlist_ac(ralt: float) -> str:
    return f"""* bolucunun frekans tepkisi (ortusme suzgeci)
Vin giris 0 DC 0 AC 1
Rust giris dugum {R_UST}
Ralt dugum 0 {ralt}
Cf dugum 0 {C_SUZ}
.control
ac dec 60 10 1meg
wrdata ac.txt vdb(dugum)
.endc
.end
"""


def netlist_akim_suzgec(rs: float, cd: str) -> str:
    """Sont -> diferansiyel RC -> ADS1115 (giris direnci 710 kohm)."""
    return f"""* akim girisi diferansiyel RC suzgeci
Vsont a 0 DC 0 AC 1
Rsa a p {rs}
Rsb 0 n {rs}
Cd p n {cd}
Rads p n 710k
.control
ac dec 60 1 1meg
wrdata ac.txt vdb(p,n)
.endc
.end
"""


def kesim(veri, plato=None):
    p = plato if plato is not None else veri[0][1]
    for f, db in veri:
        if db <= p - 3.0:
            return f
    return float("inf")


def kosu(r: spice.Rapor) -> None:
    r.bilgi("A2 — Asama 2 analog giris korumasi")
    r.bilgi("")

    # ═══════════════════════════════ 1. UC SECENEGI KARSILASTIR
    r.bilgi("  1. KELEPCE SECENEKLERI — 0..300 V taramasi")
    r.bilgi("")
    r.bilgi("     secenek                 dugum@30V   dugum@230V  ariza akimi"
            "  ADS guvenli")
    r.bilgi("     " + "-" * 72)

    sonuc = {}
    for sec, ad in (("A", "11:1, kelepce yok"),
                    ("B", "11:1, 3.3 V rayina"),
                    ("C", "11:1, TL431 rayina"),
                    ("D", "15.71:1, TL431 rayina")):
        _, dizin = spice.kos(netlist(sec, 300.0), BURASI / f"_a2_{sec}")
        veri = spice.degerler(dizin / "dc.txt")
        # (vin, v(dugum), i(Vin), i(V33))
        def dugumde(vin):
            en_yakin = min(veri, key=lambda s: abs(s[0] - vin))
            return en_yakin
        d30 = dugumde(30.0)
        d230 = dugumde(230.0)
        # ariza akimi: giristen akan (isaret ngspice'ta ters)
        ariza = abs(d230[2])
        guvenli = (d230[1] <= ADS_MUTLAK) or (ariza <= ADS_AKIM_MUTLAK)
        sonuc[sec] = dict(veri=veri, d30=d30, d230=d230, ariza=ariza)
        r.bilgi(f"     {ad:<22} {d30[1]:8.4f} V {d230[1]:9.3f} V "
                f"{ariza*1000:9.3f} mA  {'evet' if guvenli else 'HAYIR':>10}")

    r.bilgi("")
    # --- her secenek icin dogrusallik hatasi
    r.bilgi("  2. DOGRUSALLIK — kelepce sizintisi olcumu ne zaman bozuyor?")
    r.bilgi("     (ideal dugum = Vin / oran; A,B,C icin 11, D icin 15.71)")
    r.bilgi("")
    r.bilgi(f"     {'Vin':>7} " + "".join(f"{'sec ' + s:>14}" for s in "ABCD"))
    r.bilgi("     " + "-" * 50)
    for hedef in (5, 10, 20, 25, 30, 32, 35):
        satir = f"     {hedef:5.0f} V "
        for sec in "ABCD":
            v = min(sonuc[sec]["veri"], key=lambda s: abs(s[0] - hedef))
            ideal = v[0] / (ORAN_D if sec == "D" else ORAN)
            ppm = (v[1] - ideal) / ideal * 1e6
            satir += f"{ppm:11.0f} ppm"
        r.bilgi(satir)

    r.bilgi("")
    # --- karar: %0.1 (1000 ppm) hatayi asmadan hangi gerilime kadar gidilir
    r.bilgi("  3. HER SECENEGIN KULLANILABILIR MENZILI (hata < 1000 ppm = %0.1)")
    r.bilgi("")
    menzil = {}
    for sec in "ABCD":
        en_yuksek = 0.0
        for vin, vd, *_ in sonuc[sec]["veri"]:
            if vin < 1.0:
                continue
            ideal = vin / (ORAN_D if sec == "D" else ORAN)
            if abs(vd - ideal) / ideal * 1e6 <= 1000:
                en_yuksek = vin
            else:
                break
        menzil[sec] = en_yuksek
        r.bilgi(f"     secenek {sec}: {en_yuksek:6.2f} V'a kadar %0.1 icinde")

    r.bilgi("")
    r.kosul("Secenek A ariza akimi ADS mutlak azamisinin altinda",
            sonuc["A"]["ariza"] < ADS_AKIM_MUTLAK,
            f"{sonuc['A']['ariza']*1000:.3f} mA < 10 mA")
    r.kosul("Secenek B dugumu ADS mutlak azamisini ASIYOR (elendi)",
            sonuc["B"]["d230"][1] > ADS_MUTLAK,
            f"{sonuc['B']['d230'][1]:.3f} V > {ADS_MUTLAK} V")
    r.kosul("Secenek C dugumu ADS mutlak azamisinin altinda",
            sonuc["C"]["d230"][1] < ADS_MUTLAK,
            f"{sonuc['C']['d230'][1]:.3f} V < {ADS_MUTLAK} V")
    r.kosul("Secenek C 32 V'u KAPSAMIYOR (red gerekcesi dogrulandi)",
            menzil["C"] < 32.0, f"sadece {menzil['C']:.1f} V — sizinti kesiyor")
    r.kosul("Secenek A menzili C'den genis (sizinti yok)",
            menzil["A"] >= menzil["C"], f"A={menzil['A']:.1f} V, C={menzil['C']:.1f} V")

    r.kosul("SECILEN D: menzil 32 V'u kapsiyor", menzil["D"] >= 32.0,
            f"{menzil['D']:.1f} V")
    r.kosul("SECILEN D: arizada dugum ADS mutlak azamisinin altinda",
            sonuc["D"]["d230"][1] < ADS_MUTLAK,
            f"{sonuc['D']['d230'][1]:.3f} V < {ADS_MUTLAK} V")

    r.bilgi("")
    r.bilgi("  SECIM: D — bolucu 100K/6.8K (oran 15.71) + TL431 rayina kelepce")
    r.bilgi("")
    r.bilgi("    ISPAT — 1N4148 ile hem tam menzil hem guvenli kelepce OLMAZ:")
    r.bilgi("      tam olcekte diyodun kapali kalmasi icin gereken marj  0.22 V")
    r.bilgi("      arizada diyodun ileri dusumu                          0.70 V")
    r.bilgi("      gereken toplam acikli                                 0.92 V")
    r.bilgi("      elde olan (3.6 V mutlak azami - 3.3 V tam olcek)      0.30 V")
    r.bilgi("")
    r.bilgi("    COZUM: tam olcek DUGUM gerilimini dusur. PGA +-2.048 V ile")
    r.bilgi("    dugum 2.048 V'da kaliyor, TL431 rayi 2.495 V — diyot tum")
    r.bilgi("    menzil boyunca TERS KUTUPLU, sizinti sifir. Bolucu 15.71:1")
    r.bilgi("    olunca tam olcek 32.2 V'a cikiyor (Asama 1: 27.1 V).")
    r.bilgi("")
    r.bilgi("    Elenme sebepleri:")
    r.bilgi("      A — dugum gerilimini sinirlamiyor; ADS'in kendi ESD diyoduna")
    r.bilgi("          surekli akim basmak iyi uygulama degil.")
    r.bilgi("      B — dugum 3.6 V mutlak azamisini asiyor.")
    r.bilgi("      C — sizinti menzili 29.7 V'ta kesiyor.")

    # ═══════════════════════════════ 4. ORTUSME SUZGECI
    r.bilgi("")
    r.bilgi("  4. ORTUSME (ANTI-ALIAS) SUZGECI")
    _, dizin = spice.kos(netlist_ac(R_ALT_D), BURASI / "_a2_ac")
    veri = spice.degerler(dizin / "ac.txt")
    fc = kesim(veri)
    th_d = R_UST * R_ALT_D / (R_UST + R_ALT_D)
    fc_bek = 1 / (2 * 3.141592653589793 * th_d * 1e-9)
    r.bilgi(f"     Thevenin {th_d/1e3:.2f} kohm, 1 nF -> beklenen {fc_bek/1e3:.1f} kHz")
    r.esit("Bolucu kesim frekansi", fc, fc_bek, 0.05, " Hz")
    nyq_skop = 83333 / 2
    nyq_ads = 860 / 2
    r.kosul("Osiloskop Nyquist'inin altinda", fc < nyq_skop,
            f"{fc/1e3:.1f} kHz < {nyq_skop/1e3:.1f} kHz")
    r.bilgi(f"     NOT: ADS1115 Nyquist'i {nyq_ads:.0f} Hz; suzgec {fc/1e3:.1f} kHz.")
    r.bilgi("     ADS1115 delta-sigma oldugu icin ic modulatoru cok daha hizli")
    r.bilgi("     ornekliyor, ortusme veri hizinda degil modulator hizinda olur.")
    r.bilgi("     Sebeke uugultusu 200 ms'lik pencerede (10 tam cevrim) sifirlanir.")

    # ═══════════════════════════════ 5. AKIM SUZGECI
    r.bilgi("")
    r.bilgi("  5. AKIM GIRISI DIFERANSIYEL RC SUZGECI")
    for rs, cd, ad in ((100.0, "100n", "100 ohm + 100 nF"),
                       (100.0, "10n", "100 ohm + 10 nF")):
        _, dizin = spice.kos(netlist_akim_suzgec(rs, cd), BURASI / f"_a2_i{cd}")
        veri = spice.degerler(dizin / "ac.txt")
        dc_db = veri[0][1]
        fc_i = kesim(veri)
        kayip = (1 - 10 ** (dc_db / 20)) * 100
        r.bilgi(f"     {ad:<20} kesim {fc_i/1e3:7.2f} kHz, "
                f"DC kazanc kaybi %{kayip:.4f}")
        if cd == "100n":
            r.kosul("  Seri direncin DC kazanc kaybi < %0.05", kayip < 0.05,
                    f"%{kayip:.4f} (710 kohm ADS girisine karsi 200 ohm)")
            r.kosul("  Kesim anahtarlama gurultusunun (100 kHz) altinda",
                    fc_i < 100e3, f"{fc_i/1e3:.2f} kHz")


if __name__ == "__main__":
    import shutil
    r = spice.Rapor()
    try:
        kosu(r)
    finally:
        tamam = r.yazdir()
        for d in BURASI.glob("_a2_*"):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
    raise SystemExit(0 if tamam else 1)
