# -*- coding: utf-8 -*-
"""B19 — OSILOSKOP KANALI CIFT YONLU (2026-09-09, kullanici karari).

    python sim3_skop.py

SORUN. ESP32'nin ADC'si yalnizca 0..2.9 V okuyor, EKSI goremiyor. Skop
bolucusunun alt ucu GND'de oldugu icin kanal TEK YONLUYDU: 0 .. 45.5 V.
Negatife inen bir dalga sekli goruntulenemiyordu.

COZUM. Gerilim kanallarinin ZATEN kullandigi hilenin aynisi: bolucunun
alt ucunu GND yerine VREF'e (1.7153 V) baglamak. Sifir giris = VREF,
eksi giris asagi, arti giris yukari.

    R23  6.8K -> 2.7K   (oran 15.71 -> 38.04)
    R23'un alt ucu GND -> VREF

    ONCE :  0 .. +45.5 V   TEK YONLU,  adim 11.9 mV
    SONRA: -63.5 .. +46.8 V,           adim 28.8 mV

BEDELI COZUNURLUK — arti taraf HIC daralmiyor, adim iki katina cikiyor.

⚠ YENI AKIM YOLU: skop girisinden gelen akim artik GND'ye degil VREF'e
  gidiyor. VREF butun kanallarin referansi, o yuzden bu betik hem normal
  calismadaki yuku hem ARIZA akimini hem de CAPRAZ KONUSMAYI olcuyor.

⚠ BU BETIK TASARIMI SINIYOR, KURULMUS BIR KARTI DEGIL.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
import tasarim3_sabit as T                              # noqa: E402
from sim3_ariza import AYARLAR, opamp_makro, D_BAT85    # noqa: E402
from tezgah import tezgah                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
N_ESKI = (T.SKOP_RUST + T.SKOP_RALT_ESKI) / T.SKOP_RALT_ESKI


def op(netlist, etiket):
    kayit, _ = spice.kos(netlist, BURASI / f"_b19_{etiket}")
    d = {}
    for satir in kayit.splitlines():
        if "=" not in satir:
            continue
        sol, _, sag = satir.partition("=")
        p = sol.split()
        if p:
            try:
                d[p[-1].lower()] = float(sag.split()[0])
            except (ValueError, IndexError):
                pass
    return d


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


def alt(r, baslik):
    r.bilgi("")
    r.bilgi(f"  --- {baslik} " + "-" * max(0, 64 - len(baslik)))


def skop_net(vin, ralt, alt_ucu, vp=5.0):
    """Skop bolucusu + VREF tamponu (LM358) + Sallen-Key girisi (TL072).

    Iki op-amp da B15'in makromodeliyle: ray doymasi, akim siniri ve
    GIRIS JONKSIYONU dahil. Ideal op-amp bu soruyu cevaplayamaz.
    """
    return f"""* skop kanali
{opamp_makro("LM358", T.LM358_VOH_DUSUM, 0.02, 20e-3)}
{opamp_makro("TL072", 1.5, -10.5, 20e-3)}
{AYARLAR}
Vin giris 0 DC {vin}
V5 v5 0 DC {vp}
V12p v12p 0 DC 12
V12n v12n 0 DC -12
Vtl tlray 0 DC {T.TL431_V}
R2 tlray vtap {T.VREF_RA}
R3 vtap 0 {T.VREF_RB}
XU3A vtap vrefo vrefo v5 0 LM358
Vam_vref vrefo vref DC 0
R20 giris dugum {T.SKOP_RUST}
R23 dugum {alt_ucu} {ralt}
XU5A dugum sk sk v12p v12n TL072
.control
op
print v(dugum) v(vref) i(Vam_vref) v(sk)
.endc
.end
"""


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 0 — MENZIL VE COZUNURLUK
# ═══════════════════════════════════════════════════════════════════════

def bolum0(r):
    bolum(r, "BOLUM 0 — NE KAZANDIK, NE KAYBETTIK")
    r.bilgi(f"  {'':<22} {'oran':>7} {'menzil':>22} {'adim':>9}")
    r.bilgi("  " + "-" * 64)
    # 🔴 B20 (2026-09-10): burada ESP_ADC_ETKIN_UST (2.9 V) vardi ama
    # T.SKOP_ADIM artik SKOP_TAVAN (3.1 V) kullaniyor — yani ESKI ve YENI
    # adim FARKLI sabitlerle hesaplanip karsilastiriliyordu. Duzeltmenin
    # kendisi B20/6c'de: adim bir LSB'dir, "etkin aralik"tan degil NOMINAL
    # TAM OLCEK'ten turer. Menzil satirlari ESP_ADC_ETKIN_UST kullanmaya
    # devam ediyor — orasi girisin kullanilabilir ustu, dogru sabit o.
    adim_eski = T.SKOP_TAVAN / 4096 * N_ESKI
    r.bilgi(f"  {'ONCE (6.8K, GND)':<22} {N_ESKI:7.2f} "
            f"{'0 .. +' + format(T.ESP_ADC_ETKIN_UST*N_ESKI, '.1f') + ' V':>22} "
            f"{adim_eski*1e3:7.1f}mV")
    r.bilgi(f"  {'SONRA (2.7K, VREF)':<22} {T.SKOP_N:7.2f} "
            f"{format(T.SKOP_MENZIL_EKSI, '.1f') + ' .. +' + format(T.SKOP_MENZIL_ARTI, '.1f') + ' V':>22} "
            f"{T.SKOP_ADIM*1e3:7.1f}mV")
    r.kosul("  B19-0: ARTI taraf daralmadi",
            T.SKOP_MENZIL_ARTI >= 0.98 * T.ESP_ADC_ETKIN_UST * N_ESKI,
            f"+{T.SKOP_MENZIL_ARTI:.1f} V vs "
            f"+{T.ESP_ADC_ETKIN_UST*N_ESKI:.1f} V")
    r.kosul("  B19-0: EKSI taraf kazanildi (kanal artik cift yonlu)",
            T.SKOP_MENZIL_EKSI < -50,
            f"{T.SKOP_MENZIL_EKSI:.1f} V — oncesi 0 V idi")
    r.kosul("  B19-0: BEDEL cozunurluk, iki kattan fazla degil",
            T.SKOP_ADIM / adim_eski < 2.5,
            f"{adim_eski*1e3:.1f} -> {T.SKOP_ADIM*1e3:.1f} mV "
            f"({T.SKOP_ADIM/adim_eski:.2f} kat)")
    r.bilgi("")
    r.bilgi("  ⚠ Menzil SIMETRIK DEGIL: VREF (1.7153 V), ADC penceresinin")
    r.bilgi("    (0-2.9 V) ortasinda degil. Eksi taraf daha genis.")
    r.bilgi("    Simetrik kullanilabilir bolum: "
            f"+-{min(abs(T.SKOP_MENZIL_EKSI), T.SKOP_MENZIL_ARTI):.1f} V.")

    alt(r, "0b · Tam menzilde ALT KELEPCE devreye giriyor mu")
    r.bilgi("     Kanal artik eksiye indigi icin alt kelepce (D2) ilk kez")
    r.bilgi("     is goruyor. Tam eksi menzilde dugum nerede?")
    r.bilgi("")
    r.bilgi(f"     {'giris':>9} {'bolucu dugumu':>15} {'yargi':>22}")
    r.bilgi("     " + "-" * 50)
    en_dusuk = 0.0
    for vin in (T.SKOP_MENZIL_EKSI, -80.0, -120.0):
        d = op(skop_net(vin, T.SKOP_RALT, "vref"), "altkelepce")
        v = d["v(dugum)"]
        if vin == T.SKOP_MENZIL_EKSI:
            en_dusuk = v
        r.bilgi(f"     {vin:8.1f}V {v:14.3f}V "
                f"{'kelepce ICINDE' if v > -0.3 else 'kelepce devrede':>22}")
    r.kosul("  0b: tam eksi menzilde dugum kelepce esiginin ICINDE",
            en_dusuk > -0.3,
            f"{en_dusuk:.3f} V > -0.3 V — kelepce menzili KISMIYOR, "
            f"yalnizca asirisinda devreye giriyor")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — YENI AKIM YOLU: VREF'E BINEN YUK
# ═══════════════════════════════════════════════════════════════════════

def bolum1(r):
    bolum(r, "BOLUM 1 — YENI AKIM YOLU: SKOP AKIMI ARTIK VREF'E GIDIYOR")
    r.bilgi("  Alt uc GND'deyken skop akimi topraga gidiyordu. Artik VREF'e")
    r.bilgi("  gidiyor — ve VREF BUTUN kanallarin referansi. Uc soru var:")
    r.bilgi("  (a) tampon bu akimi surebiliyor mu, (b) arizada ne oluyor,")
    r.bilgi("  (c) VREF kayarsa diger kanallara ne kadar bulasir.")
    r.bilgi("")
    r.bilgi(f"  {'giris':>9} {'dugum':>10} {'VREF':>10} {'VREF akimi':>12} "
            f"{'SK cikisi':>11}")
    r.bilgi("  " + "-" * 60)
    en_akim = 0.0
    vref_sapma = 0.0
    for vin in (T.SKOP_MENZIL_ARTI, T.SKOP_MENZIL_EKSI, 0.0):
        d = op(skop_net(vin, T.SKOP_RALT, "vref"), "normal")
        i = d.get("i(vam_vref)", 0.0)
        en_akim = max(en_akim, abs(i))
        vref_sapma = max(vref_sapma, abs(d["v(vref)"] - T.VREF))
        r.bilgi(f"  {vin:8.1f}V {d['v(dugum)']:9.3f}V {d['v(vref)']:9.4f}V "
                f"{i*1e3:10.3f}mA {d['v(sk)']:10.3f}V")
    r.kosul("  B19-1: normal calismada VREF akimi LM358'in cok altinda",
            en_akim < 0.05 * T.LM358_ISC,
            f"en buyuk {en_akim*1e3:.2f} mA vs "
            f"{T.LM358_ISC*1e3:.0f} mA")
    r.kosul("  B19-1: VREF tam menzilde bile kaymiyor",
            vref_sapma < 1e-3,
            f"en buyuk sapma {vref_sapma*1e6:.1f} uV — tamponun geri "
            f"beslemesi akimi yutuyor (VREF'in TAMPONLU olmasinin sebebi bu)")

    alt(r, "1b · ARIZA: skop girisine yuksek gerilim")
    r.bilgi(f"     {'giris':>9} {'ONCE dugum':>12} {'SONRA dugum':>13} "
            f"{'VREF akimi':>12} {'VREF':>9}")
    r.bilgi("     " + "-" * 60)
    ar_akim = 0.0
    ar_sapma = 0.0
    for vin in (T.SEBEKE_TEPE, 615.0, -615.0):
        de = op(skop_net(vin, T.SKOP_RALT_ESKI, "0"), "arz_eski")
        dy = op(skop_net(vin, T.SKOP_RALT, "vref"), "arz_yeni")
        i = dy.get("i(vam_vref)", 0.0)
        ar_akim = max(ar_akim, abs(i))
        ar_sapma = max(ar_sapma, abs(dy["v(vref)"] - T.VREF))
        r.bilgi(f"     {vin:8.0f}V {de['v(dugum)']:11.2f}V "
                f"{dy['v(dugum)']:12.2f}V {i*1e3:10.3f}mA "
                f"{dy['v(vref)']:8.4f}V")
    r.kosul("  1b: ariza akimi LM358'in cikis siniri icinde",
            ar_akim < T.LM358_ISC,
            f"en buyuk {ar_akim*1e3:.2f} mA < "
            f"{T.LM358_ISC*1e3:.0f} mA — tampon dayaniyor")
    r.kosul("  1b: 🔴 ARIZADA BILE VREF kaymiyor",
            ar_sapma < 5e-3,
            f"en buyuk sapma {ar_sapma*1e3:.3f} mV — yani skop girisindeki "
            f"bir ariza DIGER kanallarin okumasini bozmuyor")
    r.bilgi("")
    r.bilgi("     ⚠ Bu, degisikligin en onemli sorusuydu: skop girisine")
    r.bilgi("       gelen bir ariza VREF uzerinden butun kanallara")
    r.bilgi("       bulasabilir miydi? Cevap HAYIR — tamponun geri")
    r.bilgi("       beslemesi akimi yutuyor.")

    alt(r, "1c · IYI YAN ETKI: Sallen-Key girisi daha AZ zorlaniyor")
    r.bilgi("     Oran buyudugu icin ayni ariza gerilimi bolucu dugumunde")
    r.bilgi("     daha kucuk bir gerilime donusuyor.")
    r.bilgi("")
    r.bilgi(f"     {'giris':>9} {'ONCE':>10} {'SONRA':>10} {'kazanc':>10}")
    r.bilgi("     " + "-" * 44)
    en_iyilesme = 1e9
    for vin in (T.SEBEKE_TEPE, 615.0):
        de = op(skop_net(vin, T.SKOP_RALT_ESKI, "0"), "sk_eski")
        dy = op(skop_net(vin, T.SKOP_RALT, "vref"), "sk_yeni")
        k = abs(de["v(dugum)"]) / max(abs(dy["v(dugum)"]), 1e-9)
        en_iyilesme = min(en_iyilesme, k)
        r.bilgi(f"     {vin:8.0f}V {de['v(dugum)']:9.2f}V "
                f"{dy['v(dugum)']:9.2f}V {k:9.2f}x")
    r.kosul("  1c: ariza gerilimi TL072 girisinde en az 2 kat azaliyor",
            en_iyilesme > 2.0,
            f"{en_iyilesme:.2f} kat — B19 bu yonden koruma EKLIYOR")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — DIRENC STRESI
# ═══════════════════════════════════════════════════════════════════════

def bolum2(r):
    bolum(r, "BOLUM 2 — DIRENC STRESI (R20 / R23)")
    fs = max(abs(T.SKOP_MENZIL_EKSI), T.SKOP_MENZIL_ARTI)
    r.bilgi(f"  Tam olcekte (en buyuk mutlak giris {fs:.1f} V):")
    r.bilgi("")
    r.bilgi(f"  {'direnc':>8} {'deger':>8} {'gerilim':>10} {'guc':>10} "
            f"{'govde':>7} {'gerilim %':>10} {'guc %':>8}")
    r.bilgi("  " + "-" * 66)
    i_fs = fs / (T.SKOP_RUST + T.SKOP_RALT)
    en_g = en_p = 0.0
    for ad, deg in (("R20", T.SKOP_RUST), ("R23", T.SKOP_RALT)):
        gov = T.DIRENC_GOVDESI.get(ad, "1/4W")
        vmax, pmax, _ = T.DIRENC_GOVDE[gov]
        v, p = i_fs * deg, i_fs ** 2 * deg
        en_g, en_p = max(en_g, v / vmax), max(en_p, p / pmax)
        r.bilgi(f"  {ad:>8} {deg/1e3:7.1f}k {v:9.2f}V {p*1e3:9.1f}mW "
                f"{gov:>7} {v/vmax*100:9.1f} {p/pmax*100:7.1f}")
    r.kosul("  B19-2: tam olcekte hicbir direnc govdesini zorlamiyor",
            en_g < 0.6 and en_p < 0.5,
            f"en yuksek gerilim %{en_g*100:.0f}, guc %{en_p*100:.0f}")
    r.bilgi("")
    r.bilgi("  ⚠ 615 V ARIZASI: B15/A9 zaten R20'nin GITTIGINI soyluyor")
    r.bilgi("    (film ~504 C). B19 bunu degistirmiyor — R20 ucuz ve")
    r.bilgi("    ariza skop girisine 615 V vermekten geliyor.")
    p615 = (615.0 / (T.SKOP_RUST + T.SKOP_RALT)) ** 2 * T.SKOP_RUST
    p615_eski = (615.0 / (T.SKOP_RUST + T.SKOP_RALT_ESKI)) ** 2 * T.SKOP_RUST
    r.kosul("  B19-2: 615 V arizasinda R20'nin yuku ONEMLI olcude "
            "degismiyor",
            abs(p615 - p615_eski) / p615_eski < 0.1,
            f"{p615_eski:.2f} W -> {p615:.2f} W "
            f"(%{(p615/p615_eski-1)*100:+.1f})")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — SABITLER UC DOSYADA AYNI MI
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r):
    bolum(r, "BOLUM 3 — SABITLER AYRISMIYOR MU (sema / firmware / arayuz)")
    r.bilgi("  Ayni sayi dort yerde duruyor. Biri unutulursa kart yanlis")
    r.bilgi("  olcer ve HICBIR test bunu yakalamaz — o yuzden burada.")
    r.bilgi("")
    fw = (KOK / "kod" / "olcum-karti-a3" / "olcum3.h").read_text(
        encoding="utf-8", errors="replace")
    sahte = (KOK / "arayuz3" / "sahte-kart.js").read_text(
        encoding="utf-8", errors="replace")

    def sayi(metin, desen):
        m = re.search(desen, metin)
        return float(m.group(1)) if m else float("nan")

    fw_oran = sayi(fw, r"#define SKOP_ORAN\s+([\d.]+)f")
    fw_vref = sayi(fw, r"#define VREF_NOMINAL\s+([\d.]+)f")
    ui_oran = sayi(sahte, r"const BOLME_ORANI = ([\d.]+);")
    ui_vref = sayi(sahte, r"const VOLT_OFSET = ([\d.]+) \* \(BOLME_ORANI")

    r.bilgi(f"  {'kaynak':<28} {'oran':>12} {'VREF':>12}")
    r.bilgi("  " + "-" * 56)
    r.bilgi(f"  {'tasarim3_sabit.py':<28} {T.SKOP_N:12.6f} {T.VREF:12.7f}")
    r.bilgi(f"  {'kod/olcum3.h':<28} {fw_oran:12.6f} {fw_vref:12.7f}")
    r.bilgi(f"  {'arayuz3/sahte-kart.js':<28} {ui_oran:12.6f} {ui_vref:12.7f}")
    r.kosul("  B19-3: firmware orani sabitler dosyasiyla ayni",
            abs(fw_oran - T.SKOP_N) < 1e-4,
            f"{fw_oran:.6f} = {T.SKOP_N:.6f}")
    r.kosul("  B19-3: arayuz orani da ayni",
            abs(ui_oran - T.SKOP_N) < 1e-4,
            f"{ui_oran:.6f}")
    r.kosul("  B19-3: VREF uc yerde de ayni",
            abs(fw_vref - T.VREF) < 1e-6 and abs(ui_vref - T.VREF) < 1e-6,
            f"{T.VREF:.7f} V")
    r.bilgi("")
    r.kosul("  B19-3: firmware'de OFSET tanimi var (cift yonlu donusum)",
            "SKOP_VOLT_OFSET" in fw,
            "kod * SKOP_VOLT_ADIM - SKOP_VOLT_OFSET")
    # 🔴 Bu iddia B19'un YAKALADIGI hatayi kalici olarak kapatiyor:
    #    ofset VREF*ORAN degil VREF*(ORAN-1) olmali.
    r.kosul("  B19-3: ofset FORMULU dogru (VREF*(ORAN-1), VREF*ORAN DEGIL)",
            "(SKOP_ORAN - 1.0f)" in fw and "(BOLME_ORANI - 1)" in sahte,
            f"{T.SKOP_VOLT_OFSET:.4f} V — ilk surumde VREF*ORAN yazilmisti "
            f"ve 0 V giris {-T.VREF*T.SKOP_N:.2f} V okuyordu")
    ino = (KOK / "kod" / "olcum-karti-a3" /
           "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
    r.kosul("  B19-3: skop olcumune ofset uygulaniyor",
            ino.count("skop_ofsetle(&m)") == 2,
            f"skop_olc() cagrisinin ikisinde de ({ino.count('skop_ofsetle(&m)')} yer)")
    r.kosul("  B19-3: hizli yol gerilimi de ofsetli",
            "(hizli_v[n] * lsb - VREF_NOMINAL) * SKOP_ORAN" in ino,
            "hizli_olcekle()")
    app = (KOK / "arayuz3" / "app.js").read_text(encoding="utf-8",
                                                 errors="replace")
    r.kosul("  B19-3: arayuz S2'nin 9. alanini (ofset) okuyor",
            "voltOfset" in app and "p.length >= 9" in app,
            "eski kartlarda 0 kabul ediliyor — geriye uyumlu")
    r.kosul("  B19-3: 🔴 skop_olc.h'ye DOKUNULMADI",
            "volt_ofset" not in (KOK / "kod" / "olcum-karti-a3" /
                                 "skop_olc.h").read_text(encoding="utf-8",
                                                         errors="replace"),
            "Asama 2'den uretilen birebir kopya; ofset CAGIRAN tarafta "
            "uygulaniyor, boylece test_skop_ayni.py hala gecerli")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — OFSET MATEMATIGI DOGRU MU
# ═══════════════════════════════════════════════════════════════════════

def bolum4(r):
    bolum(r, "BOLUM 4 — OFSET MATEMATIGI (firmware'in yaptigi duzeltme)")
    r.bilgi("  skop_olc() ofset bilmiyor; sonuclari firmware duzeltiyor.")
    r.bilgi("  Hangi alan duzeltilmeli, hangisi DOKUNULMAMALI?")
    r.bilgi("")
    ofs = T.VREF * T.SKOP_N
    # ornek dalga: VREF etrafinda +-10 V salinim
    n = 512
    ornek = [T.VREF + 10.0 / T.SKOP_N * math.sin(2 * math.pi * i / n)
             for i in range(n)]
    ham = [x * T.SKOP_N for x in ornek]             # ofsetsiz (skop_olc)
    duz = [x - ofs for x in ham]                    # duzeltilmis
    for ad, dizi in (("skop_olc ciktisi", ham), ("duzeltilmis", duz)):
        vmax, vmin = max(dizi), min(dizi)
        vort = sum(dizi) / len(dizi)
        vrms = math.sqrt(sum(x * x for x in dizi) / len(dizi))
        vac = math.sqrt(max(vrms ** 2 - vort ** 2, 0.0))
        r.bilgi(f"  {ad:<20} vmax {vmax:7.2f}  vmin {vmin:7.2f}  "
                f"vpp {vmax-vmin:6.2f}  vort {vort:7.2f}  "
                f"vrms {vrms:6.2f}  vac {vac:5.2f}")
    hv = [max(ham) - min(ham), math.sqrt(
        max(sum(x*x for x in ham)/n - (sum(ham)/n)**2, 0.0))]
    dv = [max(duz) - min(duz), math.sqrt(
        max(sum(x*x for x in duz)/n - (sum(duz)/n)**2, 0.0))]
    r.kosul("  B19-4: vpp ve vac ofsetten ETKILENMIYOR (duzeltilmemeli)",
            abs(hv[0] - dv[0]) < 1e-9 and abs(hv[1] - dv[1]) < 1e-9,
            f"vpp {hv[0]:.4f} = {dv[0]:.4f} · vac {hv[1]:.4f} = {dv[1]:.4f}")
    vort_d = sum(duz) / n
    r.kosul("  B19-4: vort ofset kadar kayiyor (duzeltilmeli)",
            abs((sum(ham) / n - vort_d) - ofs) < 1e-6,
            f"{sum(ham)/n:.3f} - {ofs:.3f} = {vort_d:.3f} V (~0 olmali)")
    vrms_d = math.sqrt(sum(x * x for x in duz) / n)
    vrms_kur = math.sqrt(dv[1] ** 2 + vort_d ** 2)
    r.kosul("  B19-4: vrms, vac ve duzeltilmis vort'tan TAM kurulabiliyor",
            abs(vrms_d - vrms_kur) < 1e-9,
            f"sqrt(vac^2 + vort^2) = {vrms_kur:.6f} = {vrms_d:.6f} — "
            f"firmware'in skop_ofsetle() fonksiyonunun dayanagi bu")
    alt(r, "4b · GIDIS-DONUS: gercek devreden okunan dugum, girisi geri veriyor mu")
    r.bilgi("     Devre ngspice'te kuruldu; dugum gerilimi olculdu; firmware'in")
    r.bilgi("     formulu uygulandi. Sonuc girise esit cikmali.")
    r.bilgi("")
    r.bilgi(f"     {'giris':>9} {'olculen dugum':>15} {'geri cevrilen':>15} "
            f"{'hata':>10}")
    r.bilgi("     " + "-" * 54)
    en_hata = 0.0
    for vin in (0.0, 10.0, T.SKOP_MENZIL_ARTI, -20.0, T.SKOP_MENZIL_EKSI):
        d = op(skop_net(vin, T.SKOP_RALT, "vref"), "gidisdonus")
        geri = d["v(dugum)"] * T.SKOP_N - T.SKOP_VOLT_OFSET
        h = geri - vin
        en_hata = max(en_hata, abs(h))
        r.bilgi(f"     {vin:8.2f}V {d['v(dugum)']:14.4f}V {geri:14.3f}V "
                f"{h*1e3:8.1f}mV")
    r.kosul("  4b: 🔴 gidis-donus hatasi bir ADC adiminin altinda",
            en_hata < T.SKOP_ADIM,
            f"en buyuk {en_hata*1e3:.1f} mV < {T.SKOP_ADIM*1e3:.1f} mV — "
            f"formulun +VREF terimi UNUTULSAYDI bu {T.VREF:.2f} V x "
            f"{T.SKOP_N:.0f} = {T.VREF*T.SKOP_N:.0f} V olurdu")

    r.bilgi("")
    r.bilgi("  ⚠ Frekans, periyot, duty, yukselme/dusme sureleri ZAMAN")
    r.bilgi("    buyuklugu; tetik esikleri de verinin KENDISINDEN")
    r.bilgi("    turetiliyor. Hicbiri ofsetten etkilenmiyor.")


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B19 — OSILOSKOP KANALI CIFT YONLU")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI sinar, kurulmus bir KARTI degil.")
    bolum0(r)
    bolum1(r)
    bolum2(r)
    bolum3(r)
    bolum4(r)
    # Skop bolucusunun VREF'e baglanmasi YENI bir akim yolu acti;
    # capraz konusma yalnizca simulasyonda olculdu.
    tezgah("B19 Skop kanali", [
        ("Skop girisi VREF'i ne kadar kaydiriyor (capraz konusma)",
         "Skop akimi artik GND'ye degil VREF'e gidiyor ve VREF BUTUN "
         "kanallarin referansi. Olcum: skop girisine 40 V ver, "
         "GERILIM kanalinin okumasi degisiyor mu bak — degisiyorsa "
         "VREF tamponu yetersiz"),
        # 🔴 Bu iki kalemin sayilari ELLE yaziliydi ve BAYATLAMISTI:
        #    "-65.2 .. +45.1 V" ve "26.9 mV" deniyordu, gercek deger
        #    -63.5/+46.8 V ve 28.8 mV. Yani URETILEN tezgah listesi,
        #    projenin kendi "elle sayi yazma" kuralini cigniyordu ve
        #    ayni dosyada iki farkli cozunurluk gorunuyordu.
        #    Artik sabitlerden TURETILIYOR.
        (f"Gercek menzil {T.SKOP_MENZIL_EKSI:.1f} .. "
         f"+{T.SKOP_MENZIL_ARTI:.1f} V mi",
         "R23 2.7K'ya dusuruldu. Olcum: her iki uctan da sinira yakin "
         "DC ver, kirpma noktalarini oku"),
        ("Cozunurluk kaybi kabul edilebilir mi",
         f"Adim {T.SKOP_ADIM*1e3:.1f} mV (tek yonluyken 11.9 mV idi; "
         f"ikisi de NOMINAL tam olcekten). "
         "Olcum: kucuk genlikli (1 V tepe) bir dalga sekli cizdir, "
         "basamaklanma goze batiyorsa karar yeniden gorusulecek"),
    ])
    return 0 if r.yazdir() else 1


if __name__ == "__main__":
    raise SystemExit(main())
