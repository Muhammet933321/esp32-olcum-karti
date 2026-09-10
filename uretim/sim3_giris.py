# -*- coding: utf-8 -*-
"""B2 — Asama 3 on ucu: CIFT YONLU bolucu, kelepce ve suzgecler (ngspice).

Cevaplanan sorular:
  1. Vref'e referansli bolucu NEGATIF girise gercekten dogrusal mi?
     (Asama 2'nin A2 adimi `dc Vin 0 300` idi — negatif taraf HIC
      simule edilmemisti. DEVIR 4.13 bu yuzden gozden kacmis.)
  2. +-615 V boyunca ADS dugumu calisma penceresinde kaliyor mu?
  3. Asiri gerilimde ne oluyor — 3.3 V'luk tampon gercekten koruyor mu?
  4. Kelepce: 1N4148 ariza akiminin ne kadarini ic ESD diyoduna birakiyor,
     BAT54 ne kadar? (tasarim3.py'nin ustel kestirimi SPICE ile sinaniyor)
  5. ADS yolu RC suzgeci: kesim ve 860 Hz'teki (ilk katlanma) zayiflama
  6. ESP yolu Sallen-Key: f0, Q, Nyquist / fs / 100 kHz zayiflamasi
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
import tasarim3_sabit as T                              # noqa: E402
from tezgah import tezgah                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent

# ── diyot modelleri
D_1N4148 = (".model D1N4148 D(IS=4.352E-9 N=1.906 BV=110 IBV=1E-4 RS=0.6458 "
            "CJO=7.048E-13 VJ=0.869 M=0.03 FC=0.5 TT=3.48E-9)")
# BAT85 — DELIKLI (DO-34 eksenel cam) kucuk sinyal Schottky.
# Kullanici SMD yapamadigi icin BAT54 (SOT-23) yerine bu secildi.
# Nexperia veri sayfasi Tablo 7: Vf 400 mV maks @ 10 mA, IR 2 uA maks @ 25 V,
# Cd 10 pF maks @ 1 V.  1N5711 (DO-35) de esdeger bir alternatif.
D_BAT85 = (".model DBAT85 D(IS=2.6E-7 N=1.06 RS=0.42 CJO=1.0E-11 M=0.333 "
           "VJ=0.4 BV=30 IBV=1E-5 EG=0.69 XTI=2)")
# ADS1115'in ICINDEKI ESD diyodu — genel silisyum
D_ESD = (".model DESD D(IS=1.0E-14 N=1.0 RS=10 CJO=2.0E-12 BV=20 IBV=1E-5)")

IDEAL_OPAMP = """* ideal birim kazanc tampon: kazanc 1e6, tek kutup 10 Hz
.subckt OPAMP arti eksi cikis
Rin arti eksi 1T
Egain ic 0 arti eksi 1E6
Rp ic cikis 159.15k
Cp cikis 0 100n
.ends
"""


def netlist_bolucu(rust, ralt, vref, vmin, vmax, adim):
    """Vref'e referansli bolucu — NEGATIFTEN POZITIFE tarama."""
    return f"""* cift yonlu bolucu — Vref referansli
Vin giris 0 DC 0
Vref vref 0 DC {vref}
Rust giris dugum {rust}
Ralt dugum vref {ralt}
.control
dc Vin {vmin} {vmax} {adim}
wrdata dc.txt v(dugum)
.endc
.end
"""


def netlist_kelepce(harici_model, harici_ad, rseri):
    """TL072 cikisi arizada raya oturuyor; ic ESD diyoduna ne kadar akim kaciyor?

    dugum = ADS pini. Harici kelepce seri direncin ARDINDA (pinde).
    """
    return f"""* kelepce karsilastirmasi — ic ESD diyoduna kacan akim
{harici_model}
{D_ESD}
Vsurucu surucu 0 DC 0
V33 v33 0 DC 3.3
Rs surucu pin {rseri}
* ADS'in ic ESD diyotlari
Desd_alt 0 pin DESD
Desd_ust pin v33 DESD
* harici kelepce
Dext_alt 0 pin {harici_ad}
Dext_ust pin v33 {harici_ad}
.control
dc Vsurucu -12 12 0.05
wrdata dc.txt v(pin) i(Vsurucu) i(V33)
.endc
.end
"""


def netlist_esd_akimi(harici_model, harici_ad, rseri, vsurucu):
    """Tek noktada ic ESD diyodunun akimini olcer (ayri ampermetre ile)."""
    return f"""* tek nokta: ic ESD diyodunun akimi
{harici_model}
{D_ESD}
Vsurucu surucu 0 DC {vsurucu}
V33 v33 0 DC 3.3
Rs surucu pin {rseri}
Vam_esd 0 esd_a DC 0
Desd_alt esd_a pin DESD
Desd_ust pin v33 DESD
Vam_ext 0 ext_a DC 0
Dext_alt ext_a pin {harici_ad}
Dext_ust pin v33 {harici_ad}
.control
op
print i(Vam_esd) i(Vam_ext) v(pin)
.endc
.end
"""


def netlist_rc(rtop, c):
    return f"""* ADS yolu RC ortusme suzgeci
Vin giris 0 DC 0 AC 1
R1 giris cikis {rtop}
C1 cikis 0 {c}
.control
ac dec 80 1 100k
wrdata ac.txt vdb(cikis)
.endc
.end
"""


def netlist_sallen_key(r, c1, c2):
    return f"""* Sallen-Key birim kazanc, esit R
{IDEAL_OPAMP}
Vin giris 0 DC 0 AC 1
R1 giris a {r}
R2 a b {r}
C2 b 0 {c2}
C1 a cikis {c1}
XU1 b cikis cikis OPAMP
.control
ac dec 100 10 1meg
wrdata ac.txt vdb(cikis) vp(cikis)
.endc
.end
"""


def kesim_hz(veri, plato_db=0.0):
    """Ilk -3 dB noktasi. veri satirlari (f, dB, ...) olabilir."""
    for satir in veri:
        if satir[1] <= plato_db - 3.0:
            return satir[0]
    return float("inf")


def db_at(veri, hedef):
    return min(veri, key=lambda s: abs(s[0] - hedef))[1]


def kosu(r: spice.Rapor) -> None:
    r.bilgi("B2 — Asama 3 on ucu (cift yonlu, kelepce, suzgecler)")
    r.bilgi("")

    # ═══════════════════════════ 1. CIFT YONLU BOLUCU, NEGATIF DAHIL
    r.bilgi("  1. CIFT YONLU BOLUCU — NEGATIFTEN POZITIFE TARAMA")
    r.bilgi("     (Asama 2'de bu hic yapilmamisti: `dc Vin 0 300`)")
    r.bilgi("")
    for k in T.KANALLAR:
        sinir = k["fs"] * 1.15
        _, dizin = spice.kos(
            netlist_bolucu(k["rust"], k["ralt"], T.VREF,
                           -sinir, sinir, sinir / 400),
            BURASI / f"_b2_bol_{k['kod']}")
        veri = spice.degerler(dizin / "dc.txt")

        r.bilgi(f"     {k['ad']}  (N = {k['N']:.2f})")
        # dogrusallik: her noktada beklenen dugum
        en_kotu = 0.0
        for vin, dugum in veri:
            bekle = T.VREF + (vin - T.VREF) / k["N"]
            en_kotu = max(en_kotu, abs(dugum - bekle))
        r.kosul(f"       {k['ad']}: dugum = Vref+(Vin-Vref)/N (negatif dahil)",
                en_kotu < 1e-6, f"en buyuk sapma {en_kotu*1e9:.2f} nV")

        # tam olcekte iki uc
        for isaret, ad in ((-1, "-FS"), (+1, "+FS")):
            vin = isaret * k["fs"]
            olculen = min(veri, key=lambda s: abs(s[0] - vin))[1]
            bekle = T.VREF + (vin - T.VREF) / k["N"]
            r.esit(f"       {k['ad']} {ad} dugumu", olculen, bekle, 0.001, " V")

        # ADS calisma penceresi
        icinde = [d for v, d in veri if abs(v) <= k["fs"]]
        r.kosul(f"       {k['ad']}: +-FS boyunca dugum 0..3.3 V icinde",
                min(icinde) >= 0.0 and max(icinde) <= 3.3,
                f"{min(icinde):.3f} .. {max(icinde):.3f} V")

        # %15 asiri gerilimde ne oluyor
        hepsi = [d for _, d in veri]
        r.kosul(f"       {k['ad']}: %15 asiri gerilimde bile 0..3.3 disina "
                f"cikmiyor mu?",
                min(hepsi) >= 0.0 and max(hepsi) <= 3.3,
                f"{min(hepsi):.3f} .. {max(hepsi):.3f} V  "
                f"({'kaliyor' if min(hepsi) >= 0 and max(hepsi) <= 3.3 else 'ASIYOR — tampon girisi korunmali'})")
        r.bilgi("")

    # ═══════════════════════════ 2. KELEPCE: IC ESD DIYODUNA KACAN AKIM
    r.bilgi("  2. KELEPCE — ic ESD diyoduna kacan ariza akimi")
    r.bilgi("     tasarim3.py bunu ustel kestirimle buluyordu; SPICE'a soralim.")
    r.bilgi("")
    r.bilgi(f"     {'harici kelepce':<16} {'pin':>9} {'ESD akimi':>11} "
            f"{'harici akim':>12} {'ESD payi':>10}")
    r.bilgi("     " + "-" * 62)
    esd_payi = {}
    for ad, model, mad in (("kelepce YOK", D_ESD, None),
                           ("1N4148", D_1N4148, "D1N4148"),
                           ("BAT85", D_BAT85, "DBAT85")):
        if mad is None:
            net = f"""* kelepcesiz — tum ariza akimi ic ESD diyodundan
{D_ESD}
Vsurucu surucu 0 DC -12
V33 v33 0 DC 3.3
Rs surucu pin {T.R_SERI}
Vam_esd 0 esd_a DC 0
Desd_alt esd_a pin DESD
Desd_ust pin v33 DESD
.control
op
print i(Vam_esd) v(pin)
.endc
.end
"""
        else:
            net = netlist_esd_akimi(model, mad, T.R_SERI, -12.0)
        kayit, _ = spice.kos(net, BURASI / f"_b2_kel_{ad.replace(' ', '_')}")
        # ngspice `print` ciktisini ayristir
        def bul(isim):
            # ngspice satirlari "stdout i(vam_esd) = 2.18e-10" seklinde gelir
            for satir in kayit.splitlines():
                if "=" not in satir:
                    continue
                sol, _, sag = satir.partition("=")
                if sol.split() and sol.split()[-1].lower() == isim:
                    try:
                        return float(sag.split()[0])
                    except (ValueError, IndexError):
                        pass
            return None
        i_esd = abs(bul("i(vam_esd)") or 0.0)
        i_ext = abs(bul("i(vam_ext)") or 0.0)
        vpin = bul("v(pin)")
        pay = i_esd / (i_esd + i_ext) if (i_esd + i_ext) else 1.0
        esd_payi[ad] = pay
        r.bilgi(f"     {ad:<16} {vpin:8.3f}V {i_esd*1e3:9.3f}mA "
                f"{i_ext*1e3:10.3f}mA {pay*100:9.2f}%")

    r.bilgi("")
    r.kosul("     1N4148 ariza akiminin buyuk kismini ESD'ye birakiyor",
            esd_payi["1N4148"] > 0.10,
            f"%{esd_payi['1N4148']*100:.1f} — DEVIR 4.13 SPICE ile dogrulandi")
    r.kosul("     BAT85 ESD payini %1'in altina indiriyor",
            esd_payi["BAT85"] < 0.01, f"%{esd_payi['BAT85']*100:.3f}")
    r.kosul("     BAT85, 1N4148'den en az 10 kat iyi",
            esd_payi["1N4148"] / max(esd_payi["BAT85"], 1e-12) > 10,
            f"{esd_payi['1N4148']/max(esd_payi['BAT85'],1e-12):.0f}x")
    r.bilgi("")

    # ═══════════════════════════ 2b. KELEPCESIZ YOLLAR — GERCEKTEN GUVENLI MI
    r.bilgi("  2b. KELEPCESIZ TAMPONLAR — ADS pinine kacan akim")
    r.bilgi("      Kullanici SMD istemiyor; en iyi cozum kelepceyi hic")
    r.bilgi("      gerektirmemek. Tamponun cikis TAVANI ADS'i zorluyor mu?")
    r.bilgi("")
    r.bilgi("      ⚠ B15 (2026-09-09) BU BOLUMU DUZELTTI. Onceki surum burada")
    r.bilgi(f"        {T.R_SERI_ESKI/1e3:.1f}K seri direnc varsayiyordu — ama o")
    r.bilgi("        direnc SKOP ve HIZLI AKIM yollarinin kelepce direnciydi;")
    r.bilgi("        gerilim kanallarinda HIC YOKTU (netlist: /V_TAMPON =")
    r.bilgi("        U3.6, U3.7, U7.4). B15/F1 ile R34/R35/R36 eklendi ve bu")
    r.bilgi(f"        tablo artik GERCEK degeri ({T.ADS_SERI_R/1e3:.0f}K) kullaniyor.")
    r.bilgi("        Ayrica LM358'in tavani 4.3 V degil, veri sayfasindan")
    r.bilgi(f"        turetilen {5.0-T.LM358_VOH_DUSUM:.2f} V (TI SLOS068AB 5.5).")
    r.bilgi("")
    r.bilgi(f"      {'tampon':<22} {'cikis':>7} {'ADS pini':>9} {'ESD akimi':>11}")
    r.bilgi("      " + "-" * 54)
    for ad, vcikis in (("MCP600x (3.3 V RRIO)", 3.30),
                       ("LM358 (+5.00 V) tavan", 5.00 - T.LM358_VOH_DUSUM),
                       ("LM358 (+5.25 V) tavan", 5.25 - T.LM358_VOH_DUSUM),
                       ("TL072 (+-12 V)", 12.00)):
        net = f"""* kelepcesiz tampon arizasi
{D_ESD}
Vsurucu surucu 0 DC {vcikis}
V33 v33 0 DC 3.3
Rs surucu pin {T.R_SERI}
Vam_esd esd_a v33 DC 0
Desd_ust pin esd_a DESD
Desd_alt 0 pin DESD
.control
op
print i(Vam_esd) v(pin)
.endc
.end
"""
        kayit, _ = spice.kos(net, BURASI / f"_b2_kelsiz_{vcikis:.0f}")

        def bul2(isim):
            for satir in kayit.splitlines():
                if "=" not in satir:
                    continue
                sol, _, sag = satir.partition("=")
                if sol.split() and sol.split()[-1].lower() == isim:
                    try:
                        return float(sag.split()[0])
                    except (ValueError, IndexError):
                        pass
            return None
        i_esd = abs(bul2("i(vam_esd)") or 0.0)
        vpin = bul2("v(pin)")
        r.bilgi(f"      {ad:<22} {vcikis:5.2f} V {vpin:7.3f} V {i_esd*1e6:8.1f} uA")
        if ad.startswith("LM358 (+5.25 V)"):
            r.kosul("      LM358 en kotu rayda bile ESD akimi 1 mA'in altinda",
                    i_esd < 1e-3,
                    f"{i_esd*1e6:.0f} uA — kelepce gerekmiyor, ama "
                    f"{T.ADS_SERI_R/1e3:.0f}K SERI DIRENC sart (B15/F1)")
        if ad.startswith("MCP600x"):
            r.kosul("      MCP600x'te ESD akimi pratik olarak sifir",
                    i_esd < 1e-6, f"{i_esd*1e9:.1f} nA")
        if ad.startswith("TL072"):
            # ⚠ B18/F12 (2026-09-09): R_SERI 2.7K -> 10K olunca bu akim
            #   2.2 mA'den 0.80 mA'e dustu, yani 1 mA olcutunun ALTINA.
            #   Iddia AKIM uzerinden kuruluysa artik gecmiyor — ama
            #   kelepce yine de SART: belirleyici olan GERILIM.
            #   Kelepcesiz pin, ESP32'nin kendi ESD diyoduna dayanip
            #   VDD + Vf'e oturuyor; sinir VDD + 0.3 V.
            sinir = 3.3 + T.ESP_GPIO_VDD_PAYI
            r.kosul("      TL072 kelepcesiz KABUL EDILEMEZ (GERILIM olcutu)",
                    vpin > sinir,
                    f"pin {vpin:.3f} V > {sinir:.2f} V (VDD+0.3) — "
                    f"kelepce SART")
            r.kosul("      ...akim olcutu ise B18/F12 sonrasi tek basina "
                    "YETMEZ",
                    i_esd < 1e-3,
                    f"{i_esd*1e3:.2f} mA (10K ile) — 2.7K'da 2.2 mA idi. "
                    f"Akima bakip 'kelepce gereksiz' demek YANLIS olurdu; "
                    f"gerilim olcutu bagimsiz olarak kelepceyi zorunlu "
                    f"kiliyor")
    r.bilgi("")

    # ═══════════════════════════ 3. ADS YOLU RC SUZGECI
    r.bilgi("  3. ADS YOLU — RC ortusme suzgeci (Nyquist 430 Hz)")
    r.bilgi("")
    r.bilgi("     (Her iki kanalda da 22K seri: NORMAL'de R7, YUKSEK'te R17.")
    r.bilgi("      820K zinciri Thevenin'i 8.19k yapiyor; TEK BASINA C3 ile")
    r.bilgi("      fc 194 Hz olur ve 860 Hz'te yalnizca -13 dB verir.)")
    r.bilgi("")
    for k in T.KANALLAR:
        rtop = k["thev"] + T.RC_R
        _, dizin = spice.kos(netlist_rc(rtop, T.RC_C),
                             BURASI / f"_b2_rc_{k['kod']}")
        veri = spice.degerler(dizin / "ac.txt")
        fc = kesim_hz(veri)
        bekle_fc = 1 / (2 * math.pi * rtop * T.RC_C)
        r.esit(f"     {k['ad']} RC kesimi", fc, bekle_fc, 0.03, " Hz")
        r.kosul(f"     {k['ad']}: kesim ADS Nyquist'inin (430 Hz) altinda",
                fc < 430, f"{fc:.1f} Hz")
        r.kosul(f"     {k['ad']}: 860 Hz'te (ilk katlanma) >= 20 dB",
                db_at(veri, 860) <= -20, f"{db_at(veri, 860):.1f} dB")
    r.bilgi("")

    # ═══════════════════════════ 4. ESP YOLU SALLEN-KEY
    r.bilgi("  4. ESP32 HIZLI YOLU — Sallen-Key (Nyquist 20.83 kHz)")
    r.bilgi("     DEVIR 4.8'in cozumu. Bugunku tek kutuplu RC 25 kHz'te,")
    r.bilgi("     yani Nyquist'in USTUNDE — hicbir sey suzmuyor.")
    r.bilgi("")
    _, dizin = spice.kos(netlist_sallen_key(T.SK_R, T.SK_C1, T.SK_C2),
                         BURASI / "_b2_sk")
    veri = spice.degerler(dizin / "ac.txt")
    fc = kesim_hz(veri)
    r.esit("     Sallen-Key -3 dB noktasi", fc, T.SK_F0, 0.05, " Hz")

    # Butterworth: tepe olmamali
    en_yuksek = max(satir[1] for satir in veri)
    r.kosul("     Tepe yok (Butterworth, Q = 0.707)", en_yuksek < 0.1,
            f"en yuksek {en_yuksek:+.3f} dB")

    for f, hedef_db, ad in ((1e3, -0.1, "1 kHz olcum bandi"),
                            (20833, -4.0, "Nyquist"),
                            (41667, -14.0, "fs"),
                            (100e3, -30.0, "100 kHz SMPS")):
        olculen = db_at(veri, f)
        if f <= 1e3:
            r.kosul(f"     {ad}: bozulma yok", olculen > hedef_db,
                    f"{olculen:.3f} dB")
        else:
            r.kosul(f"     {ad}: en az {abs(hedef_db):.0f} dB zayiflama",
                    olculen <= hedef_db, f"{olculen:.2f} dB")

    # 2 kutuplu mu — 1 dekatta 40 dB egim
    d1, d2 = db_at(veri, 100e3), db_at(veri, 1e6)
    egim = d2 - d1
    r.esit("     Yuksek frekans egimi (dekat basina)", egim, -40.0, 0.10, " dB")
    r.bilgi("")
    r.bilgi("     KIYAS — bugunku tek kutuplu RC (6.37k + 1nF, fc 25 kHz):")
    _, dizin = spice.kos(netlist_rc(6.37e3, 1e-9), BURASI / "_b2_eski")
    eski = spice.degerler(dizin / "ac.txt")
    r.bilgi(f"       100 kHz'te eski {db_at(eski, 100e3):6.2f} dB   "
            f"yeni {db_at(veri, 100e3):6.2f} dB   "
            f"kazanc {db_at(eski, 100e3) - db_at(veri, 100e3):.1f} dB")
    r.kosul("     Yeni suzgec 100 kHz'te eskisinden en az 15 dB iyi",
            db_at(eski, 100e3) - db_at(veri, 100e3) >= 15,
            f"{db_at(eski, 100e3) - db_at(veri, 100e3):.1f} dB")


def main() -> int:
    r = spice.Rapor()
    kosu(r)
    tamam = r.yazdir()
    import shutil
    for d in BURASI.glob("_b2_*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    # Bu bolumun her sayisi ngspice MODELINDEN geliyor; modeli
    # yalanlayacak tek sey gercek parcadir.
    tezgah("B2 Analog on uc", [
        ("Bolucu NEGATIF girise gercekten dogrusal mi",
         "Vref'e referansli bolucu -615 V'ta da dogrusal olmali. "
         "Asama 2'de negatif taraf HIC simule edilmemisti (DEVIR 4.13). "
         "Olcum: -100 V uygula, ADS dugumunu voltmetreyle oku, "
         "hesaplanan degerle karsilastir"),
        ("BAT85'in GERCEK Vf'i ve ters kacagi",
         "Modeldeki 400 mV @ 10 mA ve 2 uA @ 25 V veri sayfasi MAKSIMUMU, "
         "tipik degil. Delikli DO-34 cam govde partiden partiye oynar. "
         "Kelepce ariza akiminin ne kadarini aldigi buna bagli"),
        ("ADS yolu RC kesimi gercekte kacta",
         "Hesap 55.7 Hz. Gercek C2 %10 tolerans + kablo kapasitesi ile "
         "kayabilir. Olcum: sinyal jeneratorunden supurme, -3 dB noktasi. "
         "Kaymasi B16'nin V/I eslesmesini dogrudan bozar"),
        ("Sallen-Key f0 ve Q",
         "Hesaplanan f0 ve Q ancak direnc/kondansator toleransi kadar "
         "gerceklesir. Q beklenenden yuksek cikarsa gecis bandinda "
         "tepe olusur ve skop dalga sekli SISIRILMIS gorunur"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
