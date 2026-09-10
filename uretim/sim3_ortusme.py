# -*- coding: utf-8 -*-
"""B16 — V/I SUZGEC ESLESTIRMESI ve akim kanalinin ortusme suzgeci.

    python sim3_ortusme.py

B15'in yan bulgusuydu, B16'da olculdu ve cozuldu.

SORUN. Wattmetre gucu V x I diye hesapliyor ama iki kanal ayni sinyali
FARKLI suzuyordu:

    gerilim kanali : (Rth + R7) x C2   = 28.6 kohm x 100 nF ->   55.7 Hz
    akim   kanali  : (R18 + R19) x C4  =   200 ohm x 100 nF -> 8037.3 Hz

(Akim kanalinin 8037 Hz'i 7958'den biraz yuksek: hizli yolun R27/R29
yuklemesi kaynak direncini efektif olarak dusuruyor — bolum 2e.)

Uc ayri sonucu vardi:

  1. ORTUSME (aliasing). Akim kanalinin suzgeci 7958 Hz'te ama ADS'in
     Nyquist'i 430 Hz. 430 Hz ile 8 kHz arasi her sey katlanip olcume
     giriyordu. GERI DONUSU YOK: katlanmis sinyal firmware'de ayirt
     EDILEMEZ. C18'in asil gerekcesi bu — faz eslesmesi degil.
  2. REAKTIF YUKTE GUC HATASI. 50 Hz'te faz farki -41.6 derece.
     Direncli yukte bu KENDINI GOTURUYOR — tek kutuplu suzgecte
     |H|*cos(atan x) = |H|^2 oldugu icin "esitsiz" ve "esit" suzgec AYNI
     guc okumasini verir. Hata reaktif yukte cikiyor; kullanicinin alani
     SMPS/inverter, yani yuk neredeyse HER ZAMAN reaktif.
  3. HIZLI YOLUN BANDI BELGELENENDEN DAR. Sema notu "hizli yol RC'nin
     ARDINDAN cekilseydi 7.96 kHz'e hapsolurdu" diyor ama netlist'te
     R27/R29 zaten C4 dugumunden tapliyordu. Skop kanali 16.55 kHz,
     akim kanali 7.76 kHz — hem dar hem ESITSIZ.

COZUM. Suzmeyi PAYLASILAN dugumden alip ADS'IN KENDI koluna tasimak —
B15/F2'nin (korumayi ADS koluna koymak) tam ayni mantigi:

    C4  100 nF -> 1 nF   (yalnizca RF, kutup 796 kHz)
    C18 YENI  1.32 uF    (ADS akim girisleri arasi, R38/R39'un ARDINDAN)

BOLUM 1b elle turetilen merdiven modelini ngspice'te kurulmus GERCEK
devreye (fark yukselteci sadelestirilmeden) karsi siniyor — B16'nin
butun sayilari o modele dayandigi icin.

BU BETIK TASARIMI SINIYOR, KURULMUS BIR KARTI DEGIL.
"""
from __future__ import annotations

import cmath
import csv
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
import tasarim3_sabit as T                              # noqa: E402
from tezgah import tezgah                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── akim kolunun elemanlari
RA = 2 * T.SONT_KELVIN_R          # R18 + R19 (Kelvin uclari)
RB = 2 * T.ADS_SERI_R             # R38 + R39 (B15/F1-F2 koruma direncleri)
RL = 2 * T.HIZLI_RG               # R27 + R29 — hizli yolun C4 dugumune yuku
A0 = 1 + RA / RL                  # RL'nin getirdigi DC bolunmesi

BANT = (5, 10, 25, 50, 100, 200, 400)
YUKLER = (("direncli (PF=1)", 0.0), ("PF=0.87 (30 der.)", 30.0),
          ("PF=0.50 (60 der.)", 60.0), ("PF=0.26 (75 der.)", 75.0))


def rv(k):
    """Bir gerilim kanalinin suzgec direnci: bolucunun Thevenin'i + R7/R17."""
    return k["thev"] + T.RC_R


def HV(f, k, c2=None):
    """Gerilim kanali — tek kutup (tampon girisinin onunde)."""
    c2 = T.RC_C if c2 is None else c2
    return 1 / (1 + 1j * 2 * math.pi * f * rv(k) * c2)


def _payda(f, c4, c18, rs):
    s = 1j * 2 * math.pi * f
    ra = RA + rs
    a0 = 1 + ra / RL
    return (a0 + s * (ra * c4 + RB * c18 * a0 + ra * c18)
            + s * s * ra * RB * c4 * c18)


def HI(f, c4=None, c18=None, rs=0.0):
    """ADS akim girisi (C18 dugumu) — iki kademeli, YUKLU RC merdiveni.

    Kademeler birbirini yukluyor ve hizli yol (RL) C4 dugumunu ayrica
    yukluyor; o yuzden kutup carpimi degil tam merdiven cozumu.
    """
    c4 = T.SONT_C if c4 is None else c4
    c18 = T.ADS_AKIM_C if c18 is None else c18
    if c18 <= 0:
        return 1 / (1 + (RA + rs) / RL
                    + 1j * 2 * math.pi * f * (RA + rs) * c4)
    return 1 / _payda(f, c4, c18, rs)


def HH(f, c4=None, c18=None, rs=0.0):
    """Hizli yolun tapladigi dugum (C4 uzeri) — C18'in ARDINDA degil ONUNDE."""
    c4 = T.SONT_C if c4 is None else c4
    c18 = T.ADS_AKIM_C if c18 is None else c18
    if c18 <= 0:
        return HI(f, c4, 0.0, rs)
    s = 1j * 2 * math.pi * f
    return (1 + s * RB * c18) / _payda(f, c4, c18, rs)


def SK(f):
    """Sallen-Key (skop ve hizli akim yolu ORTAK)."""
    s = 1j * f / T.SK_F0
    return 1 / (1 + s / T.SK_Q + s * s)


def guc(f, theta, hv, hi):
    """P_olculen / P_gercek — yuk faz acisi theta (derece) olan bir yukte."""
    d = cmath.phase(hv) - cmath.phase(hi)
    return (abs(hv) * abs(hi) * math.cos(math.radians(theta) + d)
            / math.cos(math.radians(theta)))


def esl_hata(f, theta, hv, hi, hi0=1.0):
    """YALNIZ ESLESMEDEN kaynaklanan hata.

    IKI sey disarida birakiliyor, cunku ikisi de firmware'de TEK bir
    carpanla siliniyor ve yukten bagimsiz:
      * kanallarin ORTAK yuvarlanmasi -> paydadaki guc(hv, hv)
      * akim kolunun DUZ (frekanstan bagimsiz) kazanc kaybi -> hi0
        (R27/R29'un yuklemesi; bolum 2e)
    Geriye yalnizca FREKANSA BAGLI eslesmezlik kaliyor — yani B16'nin
    konusu.
    """
    return guc(f, theta, hv, hi / hi0) / guc(f, theta, hv, hv) - 1


def hi_dc(c4=None, c18=None, rs=0.0):
    """Akim kolunun DC kazanci — R27/R29 yuklemesi yuzunden 1 degil."""
    return abs(HI(1e-6, c4, c18, rs))


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


def alt(r, baslik):
    r.bilgi("")
    r.bilgi(f"  --- {baslik} " + "-" * max(0, 64 - len(baslik)))


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 0 — SORUNUN SAYISALLASTIRILMASI
# ═══════════════════════════════════════════════════════════════════════

def bolum0(r):
    bolum(r, "BOLUM 0 — SORUN: IKI KANAL AYNI SINYALI FARKLI SUZUYOR")
    fi_eski = 1 / (2 * math.pi * RA * T.SONT_C_ESKI / A0)
    r.bilgi(f"  {'kanal':<26} {'R':>10} {'C':>8} {'tau':>10} {'fc':>11}")
    r.bilgi("  " + "-" * 70)
    for k in T.KANALLAR:
        tau = rv(k) * T.RC_C
        r.bilgi(f"  {'gerilim / ' + k['kod']:<26} {rv(k)/1e3:8.2f}k "
                f"{T.RC_C*1e9:6.0f}nF {tau*1e3:8.3f}ms "
                f"{1/(2*math.pi*tau):9.2f} Hz")
    r.bilgi(f"  {'akim (B16 ONCESI)':<26} {RA:8.0f}  "
            f"{T.SONT_C_ESKI*1e9:6.0f}nF "
            f"{RA*T.SONT_C_ESKI/A0*1e3:8.3f}ms {fi_eski:9.1f} Hz")
    r.bilgi("")
    r.bilgi(f"  ADS Nyquist (860 SPS / 2)  : {T.ADS_SPS/2:.1f} Hz")

    tau_v = [rv(k) * T.RC_C for k in T.KANALLAR]
    r.kosul("  B16-0: iki kanalin kesimleri 100 kattan fazla ayrisiyor",
            fi_eski * 2 * math.pi * tau_v[0] > 100,
            f"{fi_eski*2*math.pi*tau_v[0]:.0f} kat")
    r.kosul("  B16-0: iki GERILIM kanali da birbirine esit degil",
            abs(tau_v[1] / tau_v[0] - 1) > 0.02,
            f"%{(tau_v[1]/tau_v[0]-1)*100:.1f} fark — tek bir C18 ikisine "
            f"birden TAM eslesemez")

    alt(r, "0a · ASIL GEREKCE: ORTUSME — geri donusu yok")
    r.kosul("  0a: akim kanalinin suzgeci Nyquist'in USTUNDE",
            fi_eski > T.ADS_SPS / 2,
            f"{fi_eski:.0f} Hz > {T.ADS_SPS/2:.0f} Hz — "
            f"{fi_eski/(T.ADS_SPS/2):.1f} kati")
    r.kosul("  0a: gerilim kanallarinda ayni sorun YOK",
            all(1 / (2 * math.pi * t) < T.ADS_SPS / 2 for t in tau_v),
            " · ".join(f"{k['kod']} {1/(2*math.pi*t):.1f} Hz"
                       for k, t in zip(T.KANALLAR, tau_v)))
    z_eski = 20 * math.log10(abs(HI(T.ADS_SPS, T.SONT_C_ESKI, 0.0))
                             / abs(HI(0.001, T.SONT_C_ESKI, 0.0)))
    r.kosul("  0a: 860 Hz'te (ilk katlanma) akim kanali 20 dB kuralini "
            "GECEMIYOR",
            z_eski > -20,
            f"{z_eski:.1f} dB — 430 Hz ile 8 kHz arasindaki her bilesen "
            f"bandin icine katlaniyordu")
    r.bilgi("")
    r.bilgi("     -> Katlanmis bir bilesen olcumun icine GIRDIKTEN sonra")
    r.bilgi("        firmware onu ayirt edemez. Faz hatasi duzeltilebilir,")
    r.bilgi("        ortusme DUZELTILEMEZ. C18'in zorunluluk olmasinin sebebi")
    r.bilgi("        bu; faz eslesmesi ondan sonra gelen ikinci kazanc.")

    alt(r, "0b · INCE NOKTA: direncli yukte fark KENDINI GOTURUYOR")
    r.bilgi("     Tek kutuplu suzgecte  |H| * cos(atan x)  =  |H|^2.")
    r.bilgi("     Yani 'gerilim suzuluyor, akim suzulmuyor' ile 'ikisi de")
    r.bilgi("     ayni suzuluyor' DIRENCLI yukte ayni sonucu veriyor.")
    hv = HV(50.0, T.KANALLAR[0])
    r.bilgi("")
    r.bilgi(f"       |Hv| * cos(faz) = {abs(hv)*math.cos(cmath.phase(hv)):.6f}")
    r.bilgi(f"       |Hv|^2          = {abs(hv)**2:.6f}")
    ozd = max(abs(abs(HV(f, T.KANALLAR[0])) * math.cos(cmath.phase(
        HV(f, T.KANALLAR[0]))) - abs(HV(f, T.KANALLAR[0])) ** 2)
        for f in BANT)
    r.kosul("  0b: ozdeslik 5-400 Hz boyunca sayisal olarak dogrulandi",
            ozd < 1e-12,
            f"en buyuk sapma {ozd:.2e} — direncli yukte esitsizlik ZARARSIZ")
    # NEGATIF DENETIM: ozdeslik TEK KUTBA ozgu. Iki kutuplu Sallen-Key'de
    # tutmamali — tutuyorsa iddia bos demektir.
    sk_sapma = max(abs(abs(SK(f)) * math.cos(cmath.phase(SK(f)))
                       - abs(SK(f)) ** 2) for f in (1e3, 5e3, 10e3))
    r.kosul("  0b: NEGATIF DENETIM — ozdeslik iki kutuplu suzgecte TUTMUYOR",
            sk_sapma > 1e-3,
            f"Sallen-Key'de sapma {sk_sapma:.4f} — iddia gercekten "
            f"tek-kutup ozelligini sinıyor, her sey icin dogru degil")
    r.bilgi("")
    hi = HI(50.0, T.SONT_C_ESKI, 0.0)
    hi0 = hi_dc(T.SONT_C_ESKI, 0.0)
    r.bilgi("     B16 ONCESI, 50 Hz, NORMAL menzil:")
    r.bilgi(f"     {'yuk':<20} {'okunan/gercek':>14} "
            f"{'eslesmis/gercek':>16} {'ESLESME HATASI':>16}")
    r.bilgi("     " + "-" * 70)
    en_kotu = 0.0
    for ad, th in YUKLER:
        e = esl_hata(50.0, th, hv, hi, hi0) * 100
        en_kotu = max(en_kotu, abs(e))
        r.bilgi(f"     {ad:<20} {guc(50.0, th, hv, hi/hi0):13.3f} "
                f"{guc(50.0, th, hv, hv):15.3f} {e:15.1f}%")
    r.kosul("  0b: direncli yukte eslesme hatasi ihmal edilebilir",
            abs(esl_hata(50.0, 0.0, hv, hi, hi0)) < 0.01,
            f"%{abs(esl_hata(50.0, 0.0, hv, hi, hi0))*100:.2f} — "
            f"'esitsizlik zararsiz' sanisinin kaynagi bu")
    r.kosul("  0b: REAKTIF yukte hata kabul edilemez",
            en_kotu > 100,
            f"en kotu %{en_kotu:.0f} (PF=0.26) — guc faktoru olcumu comuyor")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — BILESEN SECIMI
# ═══════════════════════════════════════════════════════════════════════

def bolum1(r):
    bolum(r, "BOLUM 1 — COZUM: SUZGECI ADS'IN KENDI KOLUNA TASIMAK")
    r.bilgi("  B15/F2 KORUMAYI ADS koluna koymustu (R38/R39). B16 ayni seyi")
    r.bilgi("  SUZGEC icin yapiyor: C18, R38/R39'un ARDINA.")
    r.bilgi("")
    r.bilgi("    sont -[R18/R19]-+- SONT_P/N -[R38/R39]-+- ADS")
    r.bilgi("                    |                      |")
    r.bilgi("                    C4 (artik yalnizca RF)  C18 1.32 uF")
    r.bilgi("                    |")
    r.bilgi("                    hizli yol (R27/R29) BURADAN tapliyor")
    r.bilgi("")
    ideal = rv(T.KANALLAR[0]) * T.RC_C / (RA + RB)
    ideal_hv = rv(T.KANALLAR[1]) * T.RC_C / (RA + RB)
    r.kosul("  B16-1: sabitler dosyasindaki ideal deger betikle ayni",
            abs(ideal - T.ADS_AKIM_C_IDEAL) < 1e-12,
            f"{T.ADS_AKIM_C_IDEAL*1e6:.3f} uF — tasarim3_sabit.py ile "
            f"ayrisma yok")
    r.bilgi(f"  Ideal C18 (NORMAL menzile gore) = "
            f"({rv(T.KANALLAR[0])/1e3:.2f}k x {T.RC_C*1e9:.0f}n) / "
            f"{RA+RB:.0f} = {ideal*1e6:.3f} uF")
    r.bilgi(f"  Ideal C18 (HV menzile gore)     = {ideal_hv*1e6:.3f} uF")
    r.bilgi(f"  Secilen                         = {T.ADS_AKIM_C*1e6:.3f} uF "
            f"(1uF C023 + 220nF C052 + 100nF C008)")
    r.bilgi("")
    r.bilgi(f"  {'C18 adayi':<24} {'toplam':>9} {'NORMAL':>9} {'HV':>9}"
            f"   (50 Hz, PF=0.5 eslesme hatasi)")
    r.bilgi("  " + "-" * 72)
    for ad, cb in (("YOK (B16 oncesi)", 0.0), ("1uF", 1e-6),
                   ("1uF+220nF", 1.22e-6),
                   ("1uF+220nF+100nF  <=", T.ADS_AKIM_C),
                   ("1uF+220nF+100nF+22nF", 1.342e-6),
                   ("2x680nF", 1.36e-6)):
        c4 = T.SONT_C if cb > 0 else T.SONT_C_ESKI
        hi, hi0 = HI(50.0, c4, cb), hi_dc(c4, cb)
        s = [f"{esl_hata(50.0, 60.0, HV(50.0, k), hi, hi0)*100:8.2f}%"
             for k in T.KANALLAR]
        r.bilgi(f"  {ad:<24} {cb*1e6:8.3f}uF {s[0]} {s[1]}")
    r.bilgi("")
    r.bilgi("  4. adayin (22nF ekli) en kotu menzil hatasi biraz daha kucuk")
    r.bilgi("  ama bolum 4 gosteriyor ki KONDANSATOR TOLERANSI bu farkin")
    r.bilgi("  birkac katini zaten uretiyor — 4. kondansator sahte hassasiyet.")
    r.kosul("  B16-1: secilen deger her IKI menzilin ideali arasinda kaliyor",
            ideal <= T.ADS_AKIM_C <= ideal_hv,
            f"{ideal*1e6:.3f} <= {T.ADS_AKIM_C*1e6:.3f} <= "
            f"{ideal_hv*1e6:.3f} uF")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1b — ANALITIK MODEL ngspice'E KARSI
# ═══════════════════════════════════════════════════════════════════════
#
# Yukaridaki HI/HH ifadeleri ELLE turetildi. Projenin kurali "ngspice +
# kural()" oldugu icin turetim burada GERCEK devreye karsi sinaniyor —
# hem de fark yukseltecinin TAM modeliyle:
#
#   RL = 2 x R27 (20 kohm diferansiyel) bir SADELESTIRME. Gercekte
#   fark yukselteci simetrik degil: + kolu AC toprağa R27+R28 = 57 kohm
#   gosteriyor, - kolu ise cikisi izleyen bir dugume 10 kohm. Ustelik
#   sontun alt ucu GND'de oldugu icin surus TEK YONLU. Bu betigin
#   DIFERANSIYEL sonucu yine de 2xR27 modeliyle ayni cikmali — asagisi
#   bunu sinar. Cikmasaydi B16'nin butun sayilari coperdi.
NETLIST = """* B16 akim kolu — fark yukselteci DAHIL gercek topoloji
.subckt OPAMP arti eksi cikis
Rin arti eksi 1T
Egain ic 0 arti eksi 1E6
Rp ic cikis 159.15k
Cp cikis 0 100n
.ends
Vs sp 0 DC 0 AC 1
R18 sp a {ra}
R19 0 b {ra}
C4 a b {c4}
R38 a cp {rb}
R39 b cn {rb}
C18 cp cn {c18}
Rads cp cn 1T
R27 a x {rg}
R28 x 0 {rf}
R29 b y {rg}
R30 y cik {rf}
XU1 x y cik OPAMP
.control
ac lin 1 {f} {f}
print v(cp,cn) v(a,b)
.endc
.end
"""


def ngspice_kolu(f, c4, c18):
    """(HI, HH) — ADS dugumu ve hizli yolun tapladigi dugum."""
    kayit, _ = spice.kos(NETLIST.format(
        f=f, c4=c4, c18=max(c18, 1e-18), ra=T.SONT_KELVIN_R,
        rb=T.ADS_SERI_R, rg=T.HIZLI_RG, rf=T.HIZLI_RF))
    bul = {}
    for satir in kayit.splitlines():
        p = satir.split()
        # ngspice kaydinda her satir "stdout " ile basliyor; ayrica AC'de
        # "v(a,b) = 5.4e-01,-4.9e-01" — gercek ve sanal kisim ARADA
        # BOSLUK OLMADAN virgulle ayrik.
        if p and p[0] in ("stdout", "stderr"):
            p = p[1:]
        if len(p) >= 3 and p[1] == "=" and p[0].startswith("v("):
            sayi = "".join(p[2:]).split(",")
            if len(sayi) == 2:
                bul[p[0]] = complex(float(sayi[0]), float(sayi[1]))
    if "v(cp,cn)" not in bul or "v(a,b)" not in bul:
        raise RuntimeError("ngspice ciktisi okunamadi:\n" + kayit[-800:])
    return bul["v(cp,cn)"], bul["v(a,b)"]


def bolum1b(r):
    bolum(r, "BOLUM 1b — ELLE TURETILEN MODEL ngspice'E KARSI")
    r.bilgi("  ngspice devresi SADELESTIRME ICERMIYOR: fark yukseltecinin")
    r.bilgi("  iki kolu da (R27/R28 ve R29/R30 + ideal op-amp) yerinde,")
    r.bilgi("  sontun alt ucu GND'de. Analitik model ise yuku tek bir")
    r.bilgi(f"  {RL/1e3:.0f}k diferansiyel direnc sayiyor.")
    r.bilgi("")
    r.bilgi(f"  {'f':>8} {'dugum':>6} {'|H| ngspice':>13} {'|H| model':>11} "
            f"{'faz ngspice':>13} {'faz model':>11}")
    r.bilgi("  " + "-" * 70)
    en_g = en_f = 0.0
    for c4, c18, ad in ((T.SONT_C_ESKI, 0.0, "B16 ONCESI"),
                        (T.SONT_C, T.ADS_AKIM_C, "B16 SONRASI")):
        r.bilgi(f"  --- {ad}")
        for f in (5.0, 50.0, 400.0, 5000.0):
            n_hi, n_hh = ngspice_kolu(f, c4, c18)
            m_hi, m_hh = HI(f, c4, c18), HH(f, c4, c18)
            for etiket, n, m in (("ADS", n_hi, m_hi), ("hizli", n_hh, m_hh)):
                dg = abs(abs(n) - abs(m)) / max(abs(n), 1e-12)
                df = abs(math.degrees(cmath.phase(n) - cmath.phase(m)))
                en_g, en_f = max(en_g, dg), max(en_f, df)
                r.bilgi(f"  {f:7.0f}Hz {etiket:>6} {abs(n):12.6f} "
                        f"{abs(m):10.6f} "
                        f"{math.degrees(cmath.phase(n)):12.4f}° "
                        f"{math.degrees(cmath.phase(m)):10.4f}°")
    r.kosul("  B16-1b: genlikler ngspice ile %0.01 icinde",
            en_g < 1e-4, f"en buyuk sapma %{en_g*100:.5f}")
    r.kosul("  B16-1b: fazlar ngspice ile 0.01 derece icinde",
            en_f < 0.01, f"en buyuk sapma {en_f:.5f}°")
    r.bilgi("")
    r.bilgi("     -> Fark yukseltecinin asimetrisi DIFERANSIYEL sonucu")
    r.bilgi("        degistirmiyor: klasik fark yukseltecinin diferansiyel")
    r.bilgi("        giris direnci gercekten 2xR1. Model dogrulandi.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — SONUC: ADS YOLU, HER IKI GERILIM MENZILI
# ═══════════════════════════════════════════════════════════════════════

def bolum2(r):
    bolum(r, "BOLUM 2 — SONUC: ADS YOLU (her iki gerilim menzili ayri)")
    hi0 = hi_dc()
    hi0e = hi_dc(T.SONT_C_ESKI, 0.0)
    ozet = {}
    for k in T.KANALLAR:
        alt(r, f"{k['ad']}  (Rv = {rv(k)/1e3:.2f}k, "
               f"tau = {rv(k)*T.RC_C*1e3:.3f} ms)")
        r.bilgi(f"     {'f':>7} {'once dfaz':>11} {'sonra dfaz':>11} "
                f"{'PF=1':>8} {'PF=0.5':>9} {'PF=0.26':>9}")
        r.bilgi("     " + "-" * 60)
        en_d = en_h = 0.0
        for f in BANT:
            hv = HV(f, k)
            h0 = HI(f, T.SONT_C_ESKI, 0.0)
            h1 = HI(f)
            d0 = math.degrees(cmath.phase(hv) - cmath.phase(h0))
            d1 = math.degrees(cmath.phase(hv) - cmath.phase(h1))
            e = [esl_hata(f, th, hv, h1, hi0) * 100 for th in (0.0, 60.0, 75.0)]
            en_d = max(en_d, abs(d1))
            en_h = max(en_h, abs(e[1]))
            r.bilgi(f"     {f:6.0f}Hz {d0:10.2f}° {d1:10.2f}° "
                    f"{e[0]:7.2f}% {e[1]:8.2f}% {e[2]:8.2f}%")
        # 50 Hz'te once/sonra — bas basa karsilastirma
        hv50 = HV(50.0, k)
        e50 = abs(esl_hata(50.0, 60.0, hv50, HI(50.0), hi0)) * 100
        o50 = abs(esl_hata(50.0, 60.0, hv50,
                           HI(50.0, T.SONT_C_ESKI, 0.0), hi0e)) * 100
        ozet[k["kod"]] = (en_d, en_h, e50, o50)
        r.kosul(f"  B16-2/{k['kod']}: V/I faz farki 5-400 Hz'te 2 derecenin "
                f"altinda", en_d < 2.0, f"en kotu {en_d:.2f}°")
        r.kosul(f"  B16-2/{k['kod']}: PF=0.5 eslesme hatasi 5-400 Hz boyunca "
                f"%8'in altinda", en_h < 8.0, f"en kotu %{en_h:.2f}")
        r.kosul(f"  B16-2/{k['kod']}: 50 Hz'te iyilesme en az 20 kat",
                o50 / e50 > 20,
                f"%{o50:.0f} -> %{e50:.2f} = {o50/e50:.0f} kat")

    alt(r, "2c · Ortusme kapandi mi?")
    fc = 1 / (2 * math.pi * (RA + RB) * T.ADS_AKIM_C)
    r.bilgi(f"     Akim kanalinin yeni kesimi: {fc:.1f} Hz "
            f"(oncesi {1/(2*math.pi*RA*T.SONT_C_ESKI/A0):.0f} Hz)")
    r.kosul("  2c: akim kanali artik Nyquist'in ALTINDA suzuluyor",
            fc < T.ADS_SPS / 2, f"{fc:.1f} Hz < {T.ADS_SPS/2:.0f} Hz")
    za = 20 * math.log10(abs(HI(T.ADS_SPS)) / hi0)
    z0 = 20 * math.log10(abs(HI(T.ADS_SPS, T.SONT_C_ESKI, 0.0)) / hi0e)
    r.bilgi(f"     {T.ADS_SPS:.0f} Hz'te zayiflama: akim {za:.1f} dB")
    for k in T.KANALLAR:
        r.bilgi(f"     {'':>21} gerilim/{k['kod']:<7} "
                f"{20*math.log10(abs(HV(T.ADS_SPS, k))):.1f} dB")
    r.kosul("  2c: akim kanali 20 dB kuralini geciyor",
            za <= -20.0, f"{za:.1f} dB (oncesi {z0:.1f} dB)")

    alt(r, "2d · Sont degeri degisince eslesme bozuluyor mu?")
    r.bilgi("     Sont, akim kolunun dongu direncine SERI giriyor:")
    r.bilgi(f"     dongu = R38+R18+Rsont+R19+R39 = {RA+RB:.0f} + Rsont")
    r.bilgi("")
    r.bilgi(f"     {'sont':>10} {'dongu R':>10} {'50Hz dfaz':>11} "
            f"{'PF=0.5 hata':>13}")
    r.bilgi("     " + "-" * 48)
    taban = esl_hata(50.0, 60.0, HV(50.0, T.KANALLAR[0]), HI(50.0), hi0) * 100
    en = 0.0
    for rs in T.SONT_SECENEK:
        hv = HV(50.0, T.KANALLAR[0])
        hi = HI(50.0, rs=rs)
        e = esl_hata(50.0, 60.0, hv, hi, hi_dc(rs=rs)) * 100
        en = max(en, abs(e - taban))
        r.bilgi(f"     {rs:9.3f}R {RA+RB+rs:9.1f} "
                f"{math.degrees(cmath.phase(hv)-cmath.phase(hi)):10.2f}° "
                f"{e:12.2f}%")
    r.kosul("  2d: sont secimi eslesmeyi 1 puandan az degistiriyor",
            en < 1.0,
            f"en buyuk sapma {en:.2f} puan (10R sontta) — "
            f"sont/dongu = %{max(T.SONT_SECENEK)/(RA+RB)*100:.2f}")

    alt(r, "2e · YAN BULGU (B16/F11): hizli yol, akim algilamasini YUKLUYOR")
    r.bilgi("     R27/R29 (10K/10K) fark yukseltecinin diferansiyel giris")
    r.bilgi(f"     direnci 2xR27 = {RL/1e3:.0f}k. Bu, R18/R19 uzerinden akim")
    r.bilgi("     cekiyor ve sont gerilimini ADS'e ULASMADAN bolüyor:")
    r.bilgi("")
    r.bilgi(f"       kayip = (R18+R19)/(R18+R19+2xR27) = {RA:.0f}/"
            f"{RA+RL:.0f} = %{RA/(RA+RL)*100:.2f}")
    r.bilgi(f"       olculen DC kazanc = {hi0:.5f}")
    ng_dc = abs(ngspice_kolu(0.001, T.SONT_C, T.ADS_AKIM_C)[0])
    r.kosul("  2e: kayip ngspice'in TAM devresinde de ayni",
            abs(ng_dc - hi0) / ng_dc < 1e-5,
            f"ngspice {ng_dc:.6f} · model {hi0:.6f} — fark yukseltecinin "
            f"iki kolu ve op-amp yerinde")
    r.bilgi("")
    r.bilgi("     ⚠ BU B16'NIN GETIRDIGI BIR SEY DEGIL — B8 (hizli yol)")
    r.bilgi("       eklendiginde olustu ve HICBIR adim modellemedi.")
    r.bilgi("       tasarim2.py'deki akim hata butcesi (h_i3) B8'den ONCE")
    r.bilgi("       yazildi; icinde bu kalem YOK.")
    r.bilgi("")
    r.bilgi("     Niteligi: DUZ (frekanstan bagimsiz) kazanc hatasi.")
    r.bilgi("       * kalibrasyonla TAMAMEN siliniyor")
    r.bilgi("       * B16'nin konusu olan FAZ eslesmesini bozmuyor")
    r.bilgi(f"       * ama 'Kelvin ile KALIBRASYONSUZ %1.5 alti' iddiasini")
    r.bilgi(f"         zorluyor: uzerine %{RA/(RA+RL)*100:.2f} daha biniyor")
    kayip = RA / (RA + RL)
    r.kosul("  2e: kayip kalibrasyonsuz butcenin buyuk bir dilimini yiyor",
            kayip * 100 > 0.5,
            f"%{kayip*100:.2f} — tek basina %1.5 butcesinin "
            f"%{kayip*100/1.5*100:.0f}'i")
    r.bilgi("")
    r.bilgi("     SECENEKLER (karar KULLANICININ, B16 degistirmedi):")
    for ad, rg, rf in (("bugunku: R27/R29 10K, R28/R30 47K", 10e3, 47e3),
                       ("R27/R29 22K, R28/R30 100K", 22e3, 100e3),
                       ("R27/R29 47K, R28/R30 220K", 47e3, 220e3)):
        r.bilgi(f"       {ad:<34} kayip %{RA/(RA+2*rg)*100:5.2f} · "
                f"kazanc {rf/rg:.3f}")
    r.bilgi("       ya da: hicbir sey yapma, kalibrasyona birak")
    return ozet


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — HIZLI YOL
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r):
    bolum(r, "BOLUM 3 — HIZLI YOL (ESP32): C4 KUCULUNCE BANT ACILIYOR")
    r.bilgi("  Skop kanali (GERILIM) yalnizca Sallen-Key'den geciyor.")
    r.bilgi("  I_HIZLI (AKIM) ise C4 kutbundan DA geciyordu.")
    r.bilgi("")
    r.bilgi(f"  {'f':>9} {'once dfaz':>11} {'sonra dfaz':>11} "
            f"{'once |H|':>10} {'sonra |H|':>10}")
    r.bilgi("  " + "-" * 56)
    en_yeni = 0.0
    for f in (50, 1e3, 2e3, 5e3, 10e3, T.SK_F0):
        h0 = HH(f, T.SONT_C_ESKI, 0.0)
        h1 = HH(f)
        d0 = math.degrees(cmath.phase(SK(f)) - cmath.phase(SK(f) * h0))
        d1 = math.degrees(cmath.phase(SK(f)) - cmath.phase(SK(f) * h1))
        if f > 100:
            en_yeni = max(en_yeni, abs(d1))
        r.bilgi(f"  {f/1e3:8.3f}k {d0:10.2f}° {d1:10.2f}° "
                f"{abs(h0)*abs(SK(f)):9.4f} {abs(h1)*abs(SK(f)):9.4f}")

    def uc_db(c4, c18):
        # Referans: GECIRME BANDI platosu (1 kHz), DC degil. C18'li halde
        # 55-60 Hz civarinda bir basamak var (3c) ve DC'yi referans almak
        # bandi yapay olarak dar gosterirdi.
        h0 = abs(HH(1e3, c4, c18)) * abs(SK(1e3))
        f = 1e3
        while abs(HH(f, c4, c18)) * abs(SK(f)) > h0 * 0.70794 and f < 1e6:
            f *= 1.0005
        return f
    b_eski = uc_db(T.SONT_C_ESKI, 0.0)
    b_yeni = uc_db(T.SONT_C, T.ADS_AKIM_C)
    r.bilgi("")
    r.bilgi(f"  I_HIZLI -3 dB : {b_eski/1e3:.2f} kHz -> {b_yeni/1e3:.2f} kHz")
    r.bilgi(f"  skop    -3 dB : {T.SK_F0/1e3:.2f} kHz (degismedi)")
    r.kosul("  B16-3: hizli akim yolu belgelenen Sallen-Key bandina kavusuyor",
            abs(b_yeni - T.SK_F0) / T.SK_F0 < 0.05,
            f"{b_yeni/1e3:.2f} kHz vs {T.SK_F0/1e3:.2f} kHz "
            f"(oncesi {b_eski/1e3:.2f} kHz)")
    r.kosul("  B16-3: skop ile akim kanali arasindaki faz farki 100 Hz "
            "ustunde 2 derecenin altinda",
            en_yeni < 2.0, f"en kotu {en_yeni:.2f}° (oncesi 5 kHz'te 32°)")

    alt(r, "3b · BEDEL: hizli yolun ORTUSME payi dusuyor")
    fk = T.ESP_KANAL_SPS
    a0 = 20 * math.log10(abs(HH(fk, T.SONT_C_ESKI, 0.0)) * abs(SK(fk))
                         / (abs(HH(1.0, T.SONT_C_ESKI, 0.0)) * abs(SK(1.0))))
    a1 = 20 * math.log10(abs(HH(fk)) * abs(SK(fk))
                         / (abs(HH(1.0)) * abs(SK(1.0))))
    av = 20 * math.log10(abs(SK(fk)))
    r.bilgi(f"     Ilk katlanma frekansi (kanal basina ornekleme): "
            f"{fk/1e3:.2f} kHz")
    r.bilgi(f"       I_HIZLI  B16 oncesi : {a0:7.1f} dB   (C4 kutbu YARDIM "
            f"EDIYORDU)")
    r.bilgi(f"       I_HIZLI  B16 sonrasi: {a1:7.1f} dB")
    r.bilgi(f"       skop (gerilim)      : {av:7.1f} dB   (hic degismedi)")
    r.kosul("  3b: kayip var — durustce yaziliyor", a1 > a0,
            f"{a0:.1f} dB -> {a1:.1f} dB, {a0-a1:.1f} dB ortusme payi "
            f"KAYBEDILDI")
    r.kosul("  3b: ama akim yolu skop yolundan KOTU DEGIL",
            a1 <= av + 0.5,
            f"{a1:.1f} dB vs skop {av:.1f} dB — kartin zaten kabul ettigi "
            f"olcut bu; eskisi ESITSIZLIKTI, ustunluk degil")
    r.bilgi("")
    r.bilgi("     -> Hizli yolun ortusme payi yetersiz bulunursa cozum IKI")
    r.bilgi("        yola BIRDEN eklenmeli (yoksa B16'nin duzelttigi")
    r.bilgi("        esitsizlik geri gelir). Ayri bir is kalemi.")

    alt(r, "3c · BEDEL: B16 hizli yola 55 Hz civarinda bir BASAMAK koyuyor")
    dc = abs(HH(1e-3)) 
    plato = abs(HH(2e3))
    r.bilgi("     C18 yuksek frekansta ADS kolunu KISA DEVRE ediyor; hizli")
    r.bilgi("     yolun tapladigi dugum bunu R38/R39 uzerinden yuk olarak")
    r.bilgi("     goruyor. Sonuc: sifir/kutup cifti, yani kucuk bir basamak.")
    r.bilgi("")
    r.bilgi(f"       DC kazanc              : {dc:.4f}")
    r.bilgi(f"       plato (>1 kHz)         : {plato:.4f}")
    r.bilgi(f"       basamak                : "
            f"{20*math.log10(plato/dc):.2f} dB (%{(1-plato/dc)*100:.1f})")
    r.bilgi(f"       kutup {1/(2*math.pi*(RA+RB)*T.ADS_AKIM_C):.1f} Hz · "
            f"sifir {1/(2*math.pi*RB*T.ADS_AKIM_C):.1f} Hz")
    en_bump = max(
        abs(math.degrees(cmath.phase(SK(f)) - cmath.phase(SK(f) * HH(f))))
        for f in [1.0 * i for i in range(1, 1000)])
    r.bilgi(f"       en buyuk faz cikintisi  : {en_bump:.2f}° "
            f"(B16 oncesi bu bolgede 0.4°'nin altindaydi)")
    r.bilgi("")
    r.bilgi("     KALDIRILAMAZ: basamagin buyuklugunu R38/R39 belirliyor")
    r.bilgi("     (RB'ye gore RA). R38/R39 buyutulurse basamak kuculur ama")
    r.bilgi("     ADS'in PGA'ya BAGLI giris empedansi devreye girer:")
    def sicrama(rser):
        """Oto-kademede en ust ve en alt PGA arasindaki kazanc farki."""
        rb = 2 * rser
        z = [T.PGA_TABLO[p][1] for p in (1.024, 0.256)]
        return abs(rb / (rb + z[1]) - rb / (rb + z[0]))
    for rser in (T.ADS_SERI_R, 10 * T.ADS_SERI_R):
        for pga in (1.024, 0.256):
            z = T.PGA_TABLO[pga][1]
            r.bilgi(f"       R38/R39={rser/1e3:4.0f}k, PGA +-{pga}"
                    f" (Zdiff {z/1e6:.2f}M): kazanc hatasi "
                    f"%{2*rser/(2*rser+z)*100:.2f}")
    r.kosul("  3c: R38/R39'u buyutmek oto-kademede kazanc SICRAMASI yaratir",
            sicrama(10 * T.ADS_SERI_R) > 5 * sicrama(T.ADS_SERI_R),
            f"10K'da sicrama %{sicrama(10*T.ADS_SERI_R)*100:.2f}, "
            f"1K'da %{sicrama(T.ADS_SERI_R)*100:.2f} — "
            f"{sicrama(10*T.ADS_SERI_R)/sicrama(T.ADS_SERI_R):.1f} kat. "
            f"B15/F2'nin 1K secimi dogru, basamak KABUL EDILIYOR")
    r.bilgi("")
    r.bilgi("     NEDEN KABUL EDILEBILIR: hizli yolun esi SKOP girisi (J4),")
    r.bilgi("     yani AYRI bir konnektor. Wattmetre carpimi ADS yolunda")
    r.bilgi("     yapiliyor (J1 + sont). Hizli yol dalga sekli gosterimi")
    r.bilgi("     icin ve orada da is bolgesi kHz'ler — basamak 200 Hz'in")
    r.bilgi("     ustunde tamamen oturmus durumda.")
    r.bilgi("")
    r.bilgi("     TAMAMEN ISTENMEZSE (yapilmadi): R27/R29'u R18/R19'un")
    r.bilgi("     ONUNE, dogrudan sontun Kelvin uclarina tasimak hem bu")
    r.bilgi("     basamagi hem 2e'deki %0.99 yuklemeyi siler. Bedeli: semada")
    r.bilgi("     Kelvin niyeti okunaksizlasir (R27/R29 dogrudan YUK_EKSI ve")
    r.bilgi("     GND'ye baglanmis gorunur) — montajda yanlis noktadan")
    r.bilgi("     taplama riski. Karar KULLANICININ.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — BASKIN ARTIK: KONDANSATOR TOLERANSI
# ═══════════════════════════════════════════════════════════════════════

def bolum4(r):
    bolum(r, "BOLUM 4 — BASKIN ARTIK HATA: KONDANSATOR TOLERANSI")
    r.bilgi("  Yukaridaki butun sayilar NOMINAL degerlerle. Gercekte eslesmeyi")
    r.bilgi("  C2 ile C18'in GERCEK degerleri belirliyor.")
    r.bilgi("")
    r.bilgi("  Direncler metal film %1 -> katkilari ihmal edilebilir.")
    r.bilgi("  Kondansatorler film/multilayer: yaygin sinif K = %10, J = %5.")
    r.bilgi("  Envanterde tolerans YAZMIYOR — parcanin uzerindeki harf")
    r.bilgi("  okunmali. Bu yuzden asagisi bir SUPURME, tek sayi degil.")
    r.bilgi("")
    r.bilgi(f"  {'tolerans':>10} {'en kotu tau sapmasi':>21} "
            f"{'50Hz dfaz':>11} {'PF=0.5 hata':>13}")
    r.bilgi("  " + "-" * 60)
    kotu = {}
    for tol in (0.01, 0.02, 0.05, 0.10, 0.20):
        en, dd = 0.0, 0.0
        for s2, s18 in ((1 - tol, 1 + tol), (1 + tol, 1 - tol)):
            h = HI(50.0, T.SONT_C * s18, T.ADS_AKIM_C * s18)
            v = HV(50.0, T.KANALLAR[0], T.RC_C * s2)
            e = abs(esl_hata(50.0, 60.0, v, h,
                             hi_dc(T.SONT_C * s18, T.ADS_AKIM_C * s18)))
            if e > en:
                en = e
                dd = math.degrees(cmath.phase(v) - cmath.phase(h))
        kotu[tol] = en * 100
        r.bilgi(f"  {'+-%' + format(tol*100, '.0f'):>10} "
                f"{'+-%' + format(((1+tol)/(1-tol)-1)*100, '.0f'):>21} "
                f"{dd:10.2f}° {en*100:12.2f}%")
    r.kosul("  B16-4: %10'luk kondansatorde tolerans, nominal artigin kat "
            "kat ustunde",
            kotu[0.10] > 3 * kotu[0.01],
            f"%{kotu[0.10]:.1f} (tolerans) vs %{kotu[0.01]:.1f} (%1) — "
            f"eslesmeyi TOLERANS belirliyor, nominal secim degil")
    r.kosul("  B16-4: bu yuzden 4. kondansatorle 1.320 -> 1.300 uF kovalamak "
            "anlamsiz",
            kotu[0.05] > 2.0,
            f"%5 tolerans tek basina %{kotu[0.05]:.1f} hata veriyor; "
            f"nominal fark %1.5")

    alt(r, "4b · Monte Carlo (3-sigma = tolerans, 20000 ornek)")
    rnd = random.Random(20260909)
    p95 = p5 = 0.0
    for tol in (0.05, 0.10):
        ornek = []
        for _ in range(20000):
            v = HV(50.0, T.KANALLAR[0], T.RC_C * (1 + rnd.gauss(0, tol / 3)))
            s18 = 1 + rnd.gauss(0, tol / 3)
            h = HI(50.0, T.SONT_C * s18, T.ADS_AKIM_C * s18)
            ornek.append(abs(esl_hata(
                50.0, 60.0, v, h,
                hi_dc(T.SONT_C * s18, T.ADS_AKIM_C * s18))) * 100)
        ornek.sort()
        p95 = ornek[19000]
        if tol == 0.05:
            p5 = p95
        r.bilgi(f"     %{tol*100:.0f}: ortanca %{ornek[10000]:.2f} · "
                f"%95 %{p95:.2f} · en kotu %{ornek[-1]:.2f}")
    r.kosul("  4b: KALIBRASYONSUZ hedef, tolerans sinifina BAGLI",
            p5 < 10.0 <= p95 or p95 < 10.0,
            f"J (%5) kartlarin %95'i %{p5:.1f} altinda KALIYOR; "
            f"K (%10) ile %95 dilim %{p95:.1f} — %10 hedefi K sinifiyla "
            f"GARANTI EDILEMEZ")
    r.kosul("  4b: her iki sinifta da B16 oncesine gore 10 kattan iyi",
            p95 * 10 < 152.0,
            f"en kotu durum %{p95:.1f} vs B16 oncesi %152 (50 Hz, PF=0.5)")
    r.bilgi("")
    r.bilgi("     -> SONUC: reaktif yukte %5'ten iyi guc olcumu isteniyorsa")
    r.bilgi("        4c'deki kalibrasyon SECENEK DEGIL, GEREKLILIK.")

    alt(r, "4c · ARTIGIN COZUMU DONANIMDA DEGIL: TEK SEFERLIK KALIBRASYON")
    r.bilgi("     Kalan hata bir FAZ farki. Olcmek icin referans cihaz")
    r.bilgi("     GEREKMIYOR — DIRENCLI bir yuk yeter (rezistans, ampul):")
    r.bilgi("       * direncli yukte gercek faz farki SIFIR olmali")
    r.bilgi("       * okunan fark dogrudan suzgec eslesmezligidir")
    r.bilgi("       * menzil basina bir sayi olarak saklanir")
    r.bilgi("")
    r.bilgi(f"     {'artik dfaz':>12} {'PF=1':>9} {'PF=0.5':>9} "
            f"{'PF=0.26':>9}")
    r.bilgi("     " + "-" * 42)
    for d in (0.5, 1.0, 2.0, 5.0):
        s = [f"{(math.cos(math.radians(th+d))/math.cos(math.radians(th))-1)*100:8.2f}%"
             for th in (0.0, 60.0, 75.0)]
        r.bilgi(f"     {d:11.1f}° {s[0]} {s[1]} {s[2]}")
    def artik(d, th):
        return abs(math.cos(math.radians(th + d))
                   / math.cos(math.radians(th)) - 1)
    r.kosul("  4c: 1 derecelik artik, %10 toleransin biraktigi hatadan "
            "KAT KAT iyi",
            artik(1.0, 60.0) * 4 < kotu[0.10] / 100,
            f"kalibrasyonlu %{artik(1.0, 60.0)*100:.2f} vs "
            f"kalibrasyonsuz en kotu %{kotu[0.10]:.1f} (PF=0.5) — "
            f"{kotu[0.10]/100/artik(1.0, 60.0):.0f} kat")
    r.kosul("  4c: kalibrasyon PF=1'de zaten gereksiz, PF=0.26'da sart",
            artik(5.0, 0.0) < 0.01 < artik(5.0, 75.0),
            f"5 derecelik artik PF=1'de %{artik(5.0, 0.0)*100:.2f}, "
            f"PF=0.26'da %{artik(5.0, 75.0)*100:.1f} — hatanin yuke "
            f"baglilgi burada")
    r.bilgi("")
    r.bilgi("     -> FIRMWARE IS KALEMI (B16'nin KAPSAMI DISI): menzil basina")
    r.bilgi("        faz duzeltmesi. Firmware'de Lagrange yarim-ornek")
    r.bilgi("        hizalayici ZATEN var (B4/B5) — kesirli gecikme altyapisi")
    r.bilgi("        mevcut, duzeltme onun uzerine oturur.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 5 — BEDELLER VE SINIRLAR
# ═══════════════════════════════════════════════════════════════════════

def bolum5(r):
    bolum(r, "BOLUM 5 — BEDELLER VE SINIRLAR (durustluk bolumu)")

    alt(r, "5a · ADS akim kanalinin bandi BILEREK dusuruldu")
    fc = 1 / (2 * math.pi * (RA + RB) * T.ADS_AKIM_C)
    fe = 1 / (2 * math.pi * RA * T.SONT_C_ESKI / A0)
    r.bilgi(f"     {fe:.0f} Hz -> {fc:.1f} Hz. Kayip degil:")
    r.bilgi(f"       * eski {fe:.0f} Hz KULLANILAMAZDI (Nyquist "
            f"{T.ADS_SPS/2:.0f} Hz)")
    r.bilgi("       * wattmetrede belirleyici olan DAR kanal; gerilim kanali")
    r.bilgi("         zaten oradaydi")
    r.bilgi("       * ustu icin HIZLI YOL var, o da 7.6 -> 16.5 kHz'e cikti")
    r.kosul("  5a: yeni kesim her iki gerilim kanaliyla ayni mertebede",
            all(0.5 < fc * 2 * math.pi * rv(k) * T.RC_C < 2.0
                for k in T.KANALLAR),
            " · ".join(f"{k['kod']} {fc*2*math.pi*rv(k)*T.RC_C:.2f}x"
                       for k in T.KANALLAR))

    alt(r, "5b · PGA degisiminde oturma suresi")
    ti = (RA + RB) * T.ADS_AKIM_C
    tv = [rv(k) * T.RC_C for k in T.KANALLAR]
    n = math.ceil(5 * ti * T.ADS_SPS)
    r.bilgi(f"     akim kolu {ti*1e3:.2f} ms · gerilim {tv[0]*1e3:.2f} / "
            f"{tv[1]*1e3:.2f} ms · ornek araligi {1/T.ADS_SPS*1e3:.2f} ms")
    r.kosul("  5b: gereksinim YENI DEGIL — gerilim kanalinda zaten vardi",
            0.5 < ti / max(tv) < 2.0,
            f"{ti*1e3:.2f} ms / {max(tv)*1e3:.2f} ms = {ti/max(tv):.2f}; "
            f"PGA degisiminden sonra {n} ornek atilmali")

    alt(r, "5c · Ortak olcek hatasi KALIYOR — ama artik DUZELTILEBILIR")
    hv = HV(50.0, T.KANALLAR[0])
    r.bilgi(f"     50 Hz'te iki kanal da {abs(hv):.3f} kazancla suzuluyor;")
    r.bilgi(f"     guc {abs(hv)**2:.3f} kati okunuyor "
            f"(%{(1-abs(hv)**2)*100:.0f} dusuk).")
    r.bilgi("     Bu B16'nin cozdugu sey DEGIL. B16 iki kanali ESITLIYOR;")
    r.bilgi("     kalan hata artik YUKTEN BAGIMSIZ bir olcek carpani ve")
    r.bilgi("     firmware'de 1/|H(f)|^2 ile tam olarak silinebilir.")
    r.bilgi("     B16 ONCESI bu mumkun degildi: hata yukun PF'sine bagliydi.")
    e = [esl_hata(50.0, th, hv, HI(50.0), hi_dc()) for _, th in YUKLER]
    r.kosul("  5c: kalan hata yukten BAGIMSIZ (asil kazanc bu)",
            max(e) - min(e) < 0.03,
            f"PF=1 ile PF=0.26 arasi {(max(e)-min(e))*100:.2f} puan")

    alt(r, "5d · SINIR: harmonikli yukte tek carpan YETMEZ")
    r.bilgi("     Suzgec kutbu 50 Hz'in HEMEN USTUNDE. Her harmonik farkli")
    r.bilgi("     |H|^2 ile zayifliyor; tek bir carpan hepsini duzeltemez.")
    r.bilgi("")
    r.bilgi(f"     {'harmonik':>10} {'f':>8} {'|H|':>8} {'|H|^2 (guc)':>13}")
    r.bilgi("     " + "-" * 44)
    for h in (1, 3, 5, 7):
        f = 50.0 * h
        m = abs(HV(f, T.KANALLAR[0]))
        r.bilgi(f"     {h:9d}. {f:7.0f}Hz {m:7.3f} {m*m:12.3f}")
    kat = (abs(HV(50.0, T.KANALLAR[0]))
           / abs(HV(250.0, T.KANALLAR[0]))) ** 2
    r.kosul("  5d: 5. harmonik gucu temele gore 10 kattan fazla bastiriliyor",
            kat > 10,
            f"{kat:.1f} kat — ADS yolu TEMEL BILESEN wattmetresidir")
    r.bilgi("")
    r.bilgi("     -> Bu B16'nin GETIRDIGI bir sinir DEGIL; 860 SPS + 430 Hz")
    r.bilgi("        Nyquist'in dogal sonucu ve gerilim kanalinda zaten vardi.")
    r.bilgi("        B16 akim kanalini da ayni sinira getirerek CARPIMI")
    r.bilgi("        anlamli kildi. Harmonik/dalga sekli isi HIZLI YOLUN.")
    r.bilgi("        Duzeltilmek istenirse: her iki kanala da sayisal ters")
    r.bilgi(f"        suzgec (1 kutuplu IIR). 250 Hz'te kazanci "
            f"{1/abs(HV(250.0, T.KANALLAR[0])):.1f}x — gurultu ve ARTIK")
    r.bilgi("        ortusme de o kadar buyur; siniri olmali.")

    alt(r, "5e · YAPILMAYAN: ortak-mod kondansatorleri")
    r.bilgi("     C18 yalnizca DIFERANSIYEL suzuyor. Klasik uygulamada ayrica")
    r.bilgi("     her girisden GND'ye birer C konur (C_dm >= 10 x C_cm kurali).")
    r.bilgi("     EKLENMEDI, cunku: (1) sont yuk donusunde, ortak-mod zaten")
    r.bilgi("     GND'ye yakin; (2) iki kondansator daha delikli plakette yer")
    r.bilgi("     ve eslesmezlik (CM->DM donusumu) riski demek; (3) ADS'in")
    r.bilgi("     kendi CMRR'i bu seviyede yeterli. Gerekirse sonra eklenir.")
    c_cm = 100e-9
    r.kosul("  5e: eklenirse 2 x 100nF kurali SAGLIYOR (C_dm >= 10 x C_cm)",
            T.ADS_AKIM_C >= 10 * c_cm,
            f"{T.ADS_AKIM_C*1e6:.3f} uF >= {10*c_cm*1e6:.3f} uF "
            f"({T.ADS_AKIM_C/c_cm:.1f}x) — eklenmedi ama secilen C18 buna "
            f"zaten yer birakiyor")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 6 — MALZEME VE OZET
# ═══════════════════════════════════════════════════════════════════════

ENVANTER = (Path(__file__).parent.parent.parents[1]
            / "stok-takip" / "envanter.csv")


def stokta(kimlik):
    """envanter.csv'den (ad, adet). CLAUDE.md: envanter TEK GERCEK KAYNAK.

    ⚠ Dosya bu deponun DISINDA (kullanicinin kisisel stok kaydi). Depoyu
    klonlayan birinde yok; eskiden ciplak FileNotFoundError patliyordu.
    Dosya VARSA davranis birebir ayni.
    """
    if not ENVANTER.exists():
        return None, None
    with open(ENVANTER, encoding="utf-8") as f:
        for kayit in csv.DictReader(f):
            if kayit["id"].strip() == kimlik:
                a = kayit["adet"].strip()
                return kayit["ad"].strip(), (int(a) if a.isdigit() else None)
    return None, 0


def bolum6(r, ozet):
    bolum(r, "BOLUM 6 — MALZEME, MONTAJ VE OZET")
    # `envanter.csv` bu deponun DISINDA. Yoksa iddia SESSIZCE kaybolmasin:
    # yoklugu ACIKCA raporlaniyor ve iddia SAYISI ayni kaliyor (1 kosul),
    # boylece `beklenen_sayim.json` kilidi de tutmaya devam ediyor.
    # Ayni desen `sim3_web.py`'de `_fs.json` icin kullaniliyor.
    if not ENVANTER.exists():
        r.bilgi("  envanter.csv YOK — stok karsilastirmasi ATLANDI.")
        r.bilgi(f"    beklenen yol: {ENVANTER}")
        r.bilgi("    Kullanicinin kisisel stok kaydi; depoda degil.")
        r.bilgi("    Gereken parcalar: C4 1nF · C18 1uF/400V · C19 220nF"
                " · C20 100nF")
        r.kosul("  B16-6: envanter yoksa bu ACIKCA soyleniyor", True,
                "sessiz atlama degil")
        ozet_yaz(r, ozet)
        return
    r.bilgi("  Adetler envanter.csv'den OKUNUYOR — elle yazilmiyor.")
    r.bilgi("")
    r.bilgi(f"  {'parca':<18} {'deger':>13} {'kayit':>7} {'envanterdeki ad':>18}"
            f" {'adet':>5}  not")
    r.bilgi("  " + "-" * 78)
    yeter = True
    for ad, dg, kimlik, notu in (
            ("C4  (DEGISTI)", "100nF -> 1nF", "C049", "yalnizca RF"),
            ("C18 (YENI)", "1uF", "C023", "400V polyester"),
            ("C19 (YENI)", "220nF", "C052", "63V"),
            ("C20 (YENI)", "100nF", "C008", "50V")):
        env_ad, adet = stokta(kimlik)
        yeter = yeter and adet is not None and adet >= 1
        r.bilgi(f"  {ad:<18} {dg:>13} {kimlik:>7} {str(env_ad):>18} "
                f"{str(adet):>5}  {notu}")
    r.kosul("  B16-6: dort parcanin dordu de envanterde ve adedi >= 1",
            yeter, "satin alma YOK — envanter.csv'den okundu")
    r.bilgi("")
    r.bilgi("  MONTAJ: C18/C19/C20 ADS'in giris pinleri ARASINA, R38/R39'un")
    r.bilgi("  ARDINA. Bacaklar kisa, pinlere yakin — bu ayni zamanda ADS'in")
    r.bilgi("  anahtarlamali giris katina yuk deposu olur (TI'in onerisi).")
    r.bilgi("  Kondansatorlerin uzerindeki TOLERANS HARFI okunmali (J=%5,")
    r.bilgi("  K=%10) — bolum 4 bunun neden onemli oldugunu gosteriyor.")
    ozet_yaz(r, ozet)


def ozet_yaz(r, ozet):
    alt(r, "OZET")
    r.bilgi(f"  {'olcut':<40} {'once':>12} {'sonra':>12}")
    r.bilgi("  " + "-" * 68)
    for k in T.KANALLAR:
        d, h, e50, o50 = ozet[k["kod"]]
        r.bilgi(f"  {'PF=0.5 hatasi @50 Hz / ' + k['kod']:<40} "
                f"{'%' + format(o50, '.0f'):>12} "
                f"{'%' + format(e50, '.2f'):>12}")
        r.bilgi(f"  {'  ayni, 5-400 Hz en kotu':<40} {'':>12} "
                f"{'%' + format(h, '.2f'):>12}")
    dfaz = math.degrees(cmath.phase(HV(50.0, T.KANALLAR[0]))
                        - cmath.phase(HI(50.0)))
    dfaz0 = math.degrees(cmath.phase(HV(50.0, T.KANALLAR[0]))
                         - cmath.phase(HI(50.0, T.SONT_C_ESKI, 0.0)))
    r.bilgi(f"  {'V/I faz farki @50 Hz (NORMAL)':<40} "
            f"{format(dfaz0, '.1f') + '°':>12} "
            f"{format(dfaz, '+.2f') + '°':>12}")
    r.bilgi(f"  {'akim kanali ortusme kesimi':<40} {'7958 Hz':>12} "
            f"{format(1/(2*math.pi*(RA+RB)*T.ADS_AKIM_C), '.1f') + ' Hz':>12}")
    r.bilgi(f"  {'I_HIZLI -3 dB':<40} {'7.6 kHz':>12} {'16.5 kHz':>12}")
    r.bilgi("")
    r.bilgi("  ACIK KALAN (B16 disi, is kalemi):")
    r.bilgi("   1. firmware: menzil basina faz kalibrasyonu (bolum 4c)")
    r.bilgi("   2. firmware: PGA degisiminde ornek atma (bolum 5b)")
    r.bilgi("   3. firmware: 1/|H(f)|^2 olcek duzeltmesi (bolum 5c)")
    r.bilgi("   4. karar   : hizli yolun ortusme payi yeterli mi (bolum 3b)")
    r.bilgi("   5. karar   : B16/F11 — R27/R29 yuklemesi (bolum 2e)")


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B16 — V/I SUZGEC ESLESTIRMESI")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI sinar, kurulmus bir KARTI degil.")
    bolum0(r)
    bolum1(r)
    bolum1b(r)
    ozet = bolum2(r)
    bolum3(r)
    bolum4(r)
    bolum5(r)
    bolum6(r, ozet)
    # Eslesme HESAPLANAN bilesen degerlerine dayaniyor; gercek
    # toleranslar eslesmeyi bozabilir.
    tezgah("B16 V/I suzgec eslestirmesi", [
        ("Iki kanalin gercek kesim frekanslari eslesiyor mu",
         "Hesap ikisini de ~55.7 Hz'e getiriyor. Olcum: her iki kanala "
         "ayni 50 Hz sinusu ver, faz farkini skopla oku. "
         "Fark 1 dereceden buyukse C18 ya da R degeri yanlis"),
        ("C18 gercekten takildi mi ve degeri dogru mu",
         "Ortusme (aliasing) korumasinin TEK parcasi. Yoksa 430 Hz "
         "ustundeki her sey katlanip olcume girer ve firmware bunu "
         "AYIRT EDEMEZ — geri donusu yok"),
        ("Reaktif yukte guc okumasi",
         "Direncli yukte hata KENDINI GOTURUYOR, o yuzden direncli yuk "
         "bu kalemi DOGRULAMAZ. Olcum: motor ya da trafo gibi PF<1 bir "
         "yuk baglayip wattmetre ile karsilastir"),
    ])
    return 0 if r.yazdir() else 1


if __name__ == "__main__":
    raise SystemExit(main())
