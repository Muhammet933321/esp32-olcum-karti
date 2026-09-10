# -*- coding: utf-8 -*-
"""B18 — GPIO kelepceleri ve B1 arizasi: +3V3 rayinin GERI BESLENMESI.

    python sim3_kelepce.py

KOKEN. B15/B1 sunu buldu: +-12 V acikken +3V3 kapaliysa (USB cikarilmis
ama 24 V kaynak takili) TL072 cikislari raya oturuyor ve BAT85 kelepceleri
olu +3V3 rayini GERI BESLIYOR. Ray 3.582 V'a cikiyor; ESP32'nin BESLEME
pini mutlak maksimumu 3.60 V. Pay 18 mV.

⚠ BU NADIR BIR HAL DEGIL. "Izolasyon icin USB'yi cikar" talimatinin ya da
  sadece ACMA SIRASININ (24 V once takilmis) dogal sonucu.

B15 cozum olarak F6'yi onerdi: kelepcelerin ust ucunu +3V3 yerine TL431
rayina (2.495 V) baglamak. Kullanici 2026-09-09'da F6'yi ONAYLADI.

🔴 BU BETIK F6'YI OLCTU VE IKI SEY BULDU — o yuzden F6 UYGULANMADI:

  1. F6'nin BELGELENMEMIS bir bedeli var. B15 yalnizca skop menzilinden
     (48.7 -> 39.4 V) soz ediyordu. Ama ayni kelepce HIZLI AKIM yolunda
     da var: orada tam olcek 294.6 mV sont gerilimine karsilik geliyor ve
     F6 onu 169 mV'a dusuruyor (%43 kayip). Daha kotusu, bu ADS'in kendi
     kirpma noktasinin (256 mV) ALTINA duser — yani hizli yol, yavas
     yoldan ONCE kirpar. Hizli yolun VAROLUS SEBEBI tepe yakalamak.
  2. F6 asil kalintiyi KAPATMIYOR. TL431 acik devre olursa ray 9.9 V'a
     tirmaniyor ve ESP32 oluyor — F6'yla da, F6'siz da.

BUNUN YERINE (B18/F12): iki stok direnci.
     R26/R33  2.7K -> 10K   (kelepce seri direnci)
     R41      YENI 1K       (+3V3 -> GND bosaltma direnci)
Sonuc: pay 18 mV -> 1930 mV, TL431 VAR ya da YOK fark etmiyor,
skop menzili ve hizli akim menzili HIC DEGISMIYOR.

⚠ BU BETIK TASARIMI SINIYOR, KURULMUS BIR KARTI DEGIL.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
import tasarim3_sabit as T                              # noqa: E402
from sim3_ariza import D_BAT85, D_ESD, AYARLAR, ACIK    # noqa: E402
from tezgah import tezgah                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent

# TL431 TEK YONLU modellenmeli: katot pininden akim CEKER, VERMEZ.
#
# 1. DENEME (B15'in B1 modeli): ideal gerilim kaynagi. Bosaltma direnci
#    eklenince rayi 2.495 V'ta TUTUYORDU — yani TL431 akim VERIYOR;
#    fiziksel olarak imkansiz.
# 2. DENEME: "ideal-e yakin" diyot, .model D(IS=1E-9 N=0.02). 27 C'de
#    dogru, ama 60 C'de TERS YONDE iletti (ray 1.67 V yerine 2.33 V,
#    tlray 2.495 V'ta asili kaldi). Sebep: SPICE'in diyot sicaklik
#    modelinde doyma akimi Eg/(N*Vt) ile olceklenir; N=0.02 o usteli
#    50 katina cikarip IS'i patlatiyor.
#    ⚠ "Model parametresi sonuc degildir" kuralinin canli ornegi.
# 3. KULLANILAN: davranissal tek yonlu sont. Sicaklik artefakti YOK,
#    esik tam TL431_V, egim 1/z_KA:   I = max(0, V - Vref) / z
#    (max yakinsama icin yumusatildi)
TL431_Z_KA = 0.2                          # TI TL431 veri sayfasi, tipik


def tl431_sont(dugum: str = "tlray", z: float = TL431_Z_KA) -> str:
    """Yalnizca SINK eden TL431 sonti."""
    d = f"(V({dugum})-{T.TL431_V})"
    return f"Btl {dugum} 0 I = 0.5*({d}+sqrt({d}*{d}+1e-8))/{z}\n"

SKOP_N = (T.SKOP_RUST + T.SKOP_RALT) / T.SKOP_RALT
BOSALTMA_R = T.BOSALTMA_R_3V3   # B18/F12 — R41 (sabitler dosyasindan)
YENI_R_SERI = T.R_SERI      # B18/F12 sonrasi (10K)
ESKI_R_SERI = T.R_SERI_ESKI # B18 oncesi (2.7K)


def op(netlist: str, etiket: str) -> dict:
    kayit, _ = spice.kos(netlist, BURASI / f"_b18_{etiket}")
    cikti = {}
    for satir in kayit.splitlines():
        if "=" not in satir:
            continue
        sol, _, sag = satir.partition("=")
        p = sol.split()
        if not p:
            continue
        ad = p[-1].lower()
        try:
            cikti[ad] = float(sag.split()[0])
        except (ValueError, IndexError):
            pass
    return cikti


def b1_netlist(rs, ray1, ray2, bosalt, tl431=True,
               vop=None, temp=27, olu_yuk=ACIK):
    """B1: TL072 cikislari raya oturmus, +3V3 OLU."""
    vop = T.TL072_CIKIS_TAVAN if vop is None else vop
    tl = tl431_sont() if tl431 else f"Rtl tlray 0 {ACIK}\n"
    return f"""* B1 — +-12 V var, +3V3 yok
{D_BAT85}
{AYARLAR}
.options temp={temp}
Vs1 cik1 0 DC {vop}
Vs2 cik2 0 DC {vop}
R26 cik1 gpio1 {rs}
R33 cik2 gpio2 {rs}
Vam1 kel1 {ray1} DC 0
D1 gpio1 kel1 DBAT85
Vam2 kel2 {ray2} DC 0
D3 gpio2 kel2 DBAT85
R1 tlray ray {T.R1_TL431}
R2 tlray vtap {T.VREF_RA}
R3 vtap 0 {T.VREF_RB}
Rbos ray 0 {bosalt}
Rolu ray 0 {olu_yuk}
{tl}.control
op
print v(ray) v(tlray) v(gpio1) i(Vam1) i(Vam2)
.endc
.end
"""


def b1(rs, ray1="ray", ray2="ray", bosalt=ACIK, tl431=True, **kw):
    d = op(b1_netlist(rs, ray1, ray2, bosalt, tl431, **kw), "b1")
    d["pay"] = (T.ESP_MUTLAK_PIN_UST - d["v(ray)"]) * 1e3
    d["ienj"] = abs(d.get("i(vam1)", 0.0)) + abs(d.get("i(vam2)", 0.0))
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


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 0 — SORUN VE DOGRU OLCUT
# ═══════════════════════════════════════════════════════════════════════

def bolum0(r):
    bolum(r, "BOLUM 0 — SORUN (B15/B1) VE HANGI SINIRIN GECERLI OLDUGU")
    r.bilgi("  +-12 V acik, +3V3 kapali. TL072 cikislari tavana oturuyor,")
    r.bilgi("  BAT85 kelepceleri olu 3V3 rayini yukari suruyor.")
    r.bilgi("")
    r.bilgi("  🔴 HANGI SINIR? Iki ayri sinir var, karistirilmamali:")
    r.bilgi("     * GPIO pini  : VDD + 0.3 V  — beslemeyi IZLEYEN bir sinir")
    r.bilgi("     * BESLEME pini: 3.60 V mutlak — SABIT")
    r.bilgi("     B1'de zorlanan sey BESLEME rayi, o yuzden gecerli olcut")
    r.bilgi(f"     sabit {T.ESP_MUTLAK_PIN_UST:.2f} V.")
    r.bilgi("     (GPIO icin VDD+0.3: ESP32-S3 veri sayfasi. Besleme pini")
    r.bilgi("      icin 3.60 V: tasarim3_sabit.py:ESP_MUTLAK_PIN_UST, kaynagi")
    r.bilgi("      Espressif FAQ. Iki sinir AYNI sayiya denk geliyor ama AYNI")
    r.bilgi("      sey degil — B1'de gecerli olan BESLEME pini olani.)")
    r.bilgi("")
    alt(r, "0a · 🔴 CERCEVE DUZELTMESI: enjeksiyon GIRIS SEVIYESINE bagli")
    r.bilgi("     B15/B1 iki TL072 cikisini da dogrudan 10.5 V'a (doyma)")
    r.bilgi("     koyuyor ve bunu 'USB'yi cikarmanin dogal sonucu' diye")
    r.bilgi("     sunuyordu. Bu EKSIK: +5 V da J5'ten geliyor, yani USB")
    r.bilgi("     cikinca LM358'ler de oluyor ve VREF ~ 0 oluyor. Op-amp")
    r.bilgi("     cikislari o zaman yalnizca GIRIS SINYALININ belirledigi")
    r.bilgi("     yerde durur. 10.5 V'a oturmasi icin:")
    r.bilgi(f"       skop  : J4'te ~{10.5*SKOP_N:.0f} V "
            f"(belgelenen menzil {T.SKOP_TAVAN*SKOP_N:.1f} V — "
            f"{10.5/T.SKOP_TAVAN:.1f} kati)")
    r.bilgi(f"       hizli : sont farki ~{10.5/T.HIZLI_G*1e3:.0f} mV "
            f"(tam olcek {(T.SKOP_TAVAN-T.VREF)/T.HIZLI_G*1e3:.0f} mV)")
    r.bilgi("")
    r.bilgi(f"     {'op-amp cikisi':>14} {'~J4 girisi':>11} "
            f"{'B18 oncesi pay':>15} {'B18 sonrasi':>13}")
    r.bilgi("     " + "-" * 58)
    for vop in (1.0, 3.1, 5.0, 7.0, 10.5):
        de = b1(ESKI_R_SERI, bosalt=ACIK, vop=vop)
        dy = b1(YENI_R_SERI, bosalt=BOSALTMA_R, vop=vop)
        r.bilgi(f"     {vop:13.1f}V {vop*SKOP_N:10.0f}V "
                f"{de['pay']:14.0f}mV {dy['pay']:12.0f}mV")
    menzil_ici = b1(ESKI_R_SERI, bosalt=ACIK, vop=T.SKOP_TAVAN)
    r.kosul("  0a: MENZIL ICI sinyalde B18 oncesi pay bile genisti",
            menzil_ici["pay"] > 500,
            f"{menzil_ici['pay']:.0f} mV — yani 18 mV rakami tek basina "
            f"'USB'yi cikarma' halinin degil, USTUNE ASIRI MENZILLI bir "
            f"girisin sonucu")
    r.bilgi("")
    r.bilgi("     ⚠ Ama senaryo YINE DE gercek ve TASARLANMIS bir hal:")
    r.bilgi("       kutu kurali zaten 'HV bagliyken USB TAKILI OLMAYACAK'")
    r.bilgi("       diyor ve B15/A9 skop girisine 615 V uyguluyor. Yani")
    r.bilgi("       'yuksek gerilim proplu + USB cikik' TAM OLARAK tavsiye")
    r.bilgi("       edilen kullanim. En kotu hal dogru hal — yalnizca")
    r.bilgi("       GEREKCESI 'acma sirasi' degil, 'asiri menzilli giris'.")

    d = b1(ESKI_R_SERI)
    alt(r, "0b · EN KOTU HAL (iki op-amp da doymus)")
    r.bilgi(f"  B18 ONCESI (R26/R33 = {ESKI_R_SERI/1e3:.1f}K):")
    r.bilgi(f"    enjekte edilen akim  : {d['ienj']*1e3:.2f} mA")
    r.bilgi(f"    3V3 rayi             : {d['v(ray)']:.3f} V")
    r.bilgi(f"    GPIO pini            : {d['v(gpio1)']:.3f} V")
    r.bilgi(f"    PAY                  : {d['pay']:.0f} mV")
    r.kosul("  B18-0: bugunku pay 50 mV'un altinda — kabul edilemez",
            d["pay"] < 50.0,
            f"{d['pay']:.0f} mV — B15/B1'in bulgusuyla birebir ayni "
            f"(bu halde TL431 GERCEKTEN iletiyor, iki model ortusuyor)")
    r.kosul("  B18-0: GPIO pininin KENDISI sorun degil",
            d["v(gpio1)"] - d["v(ray)"] < 0.3,
            f"GPIO - VDD = {(d['v(gpio1)']-d['v(ray)'])*1e3:.0f} mV "
            f"< 300 mV — kelepce rayi IZLIYOR; tehlike besleme rayinda")

    alt(r, "0c · MODEL DUZELTMESI: TL431 akim VEREMEZ")
    r.bilgi("     B15'in B1 modeli TL431'i ideal gerilim kaynagi sayiyordu.")
    r.bilgi("     Ray 2.495 V'un ALTINA dusen her cozumde o model TL431'i")
    r.bilgi("     akim VERIR halde gosteriyor — fiziksel olarak imkansiz.")
    r.bilgi("     B18 tek yonlu (yalnizca sink) model kullaniyor.")
    r.bilgi("")
    # ideal kaynak modeli ile karsilastirma
    idl = f"Rz tlray tlk 0.2\nVtl tlk 0 DC {T.TL431_V}\n"
    net_idl = b1_netlist(YENI_R_SERI, "ray", "ray", BOSALTMA_R).replace(
        tl431_sont(), idl)
    d_idl = op(net_idl, "b1_idealkaynak")
    d_tek = b1(YENI_R_SERI, bosalt=BOSALTMA_R)
    r.bilgi(f"     Ornek (10K + 1K bosaltma):")
    r.bilgi(f"       ideal kaynak modeli : ray {d_idl['v(ray)']:.3f} V")
    r.bilgi(f"       TEK YONLU model     : ray {d_tek['v(ray)']:.3f} V")
    r.kosul("  0c: iki model anlamli olcude ayrisiyor — duzeltme gerekliydi",
            abs(d_idl["v(ray)"] - d_tek["v(ray)"]) > 0.3,
            f"{abs(d_idl['v(ray)']-d_tek['v(ray)'])*1e3:.0f} mV fark; "
            f"ideal model TL431'i akim VERIR gosteriyordu")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — ADAYLARIN KARSILASTIRILMASI
# ═══════════════════════════════════════════════════════════════════════

ADAYLAR = [
    ("bugun (2.7K, kelepce +3V3)",      ESKI_R_SERI,  "ray",   "ray",   ACIK),
    ("F6 tam (kelepceler TL_RAY'e)",    ESKI_R_SERI,  "tlray", "tlray", ACIK),
    ("F6 yalniz SKOP (D1 TL_RAY)",      ESKI_R_SERI,  "tlray", "ray",   ACIK),
    ("R26/R33 -> 10K",                  YENI_R_SERI,  "ray",   "ray",   ACIK),
    ("10K + 2.7K bosaltma",             YENI_R_SERI,  "ray",   "ray",   2.7e3),
    ("10K + 1K bosaltma   <= SECILEN",  YENI_R_SERI,  "ray",   "ray",   1.0e3),
    ("10K + 470R bosaltma",             YENI_R_SERI,  "ray",   "ray",   470.0),
]


def menzil(ray1, ray2, rs):
    """Kelepce rayina VE seri direnne gore menziller.

    Tavan, kelepcenin OLCULEN devreye girme noktasi ile ADC'nin kendi
    3.1 V tavaninin kucugu. Seri direnc de etkiliyor (kacak x R), o
    yuzden rs argumani SART — ilk surumde yoktu ve menzil iddialari
    R'ye hic tepki vermiyordu.
    """
    # ⚠ Tavan olarak ESP_ADC_ETKIN_UST (2.9 V) kullaniliyor, SKOP_TAVAN
    # (3.1 V nominal) DEGIL: Espressif 12 dB zayiflatmada etkin araligi
    # 0-2900 mV veriyor ve ustunu "undefined" sayiyor. B15 de menzil
    # iddialarinda ayni sabiti kullaniyor (sim3_ariza.py, skop bolumu) —
    # ilk surumde B18 3.1 V kullaniyordu ve iki betik ayrisiyordu.
    vray = {"ray": 3.30, "tlray": T.TL431_V}
    ust = {k: min(kelepce_tavani(v, rs), T.ESP_ADC_ETKIN_UST)
           for k, v in vray.items()}
    return ust[ray1] * SKOP_N, (ust[ray2] - T.VREF) / T.HIZLI_G


def bolum1(r):
    bolum(r, "BOLUM 1 — ADAYLAR: PAY, MENZIL VE TL431 BAGIMLILIGI")
    r.bilgi(f"  {'aday':<34} {'TL431 VAR':>12} {'TL431 YOK':>12} "
            f"{'skop':>8} {'hizli I+':>9}")
    r.bilgi("  " + "-" * 80)
    sonuc = {}
    for ad, rs, r1, r2, bos in ADAYLAR:
        d1 = b1(rs, r1, r2, bos, tl431=True)
        d0 = b1(rs, r1, r2, bos, tl431=False)
        sk, so = menzil(r1, r2, rs)
        sonuc[ad] = (d1, d0, sk, so)
        r.bilgi(f"  {ad:<34} {d1['pay']:9.0f}mV {d0['pay']:9.0f}mV "
                f"{sk:7.1f}V {so*1e3:8.1f}mV")
    r.bilgi("")
    r.bilgi(f"  Referans: skop menzili {T.ESP_ADC_ETKIN_UST*SKOP_N:.1f} V · "
            f"hizli akim tam olcek "
            f"{(T.ESP_ADC_ETKIN_UST-T.VREF)/T.HIZLI_G*1e3:.1f} mV")
    r.bilgi(f"  (ADC etkin tavani {T.ESP_ADC_ETKIN_UST:.1f} V — Espressif 12 dB")
    r.bilgi(f"   zayiflatmada 0-2900 mV veriyor, ustu 'undefined'.)")
    r.bilgi(f"  ADS akim kanali zaten {T.ADS_AKIM_KIRPMA*1e3:.0f} mV'ta "
            f"kirpiyor (PGA +-0.256).")

    alt(r, "1a · F6 ONAYLANMISTI — neden UYGULANMADI")
    f6 = sonuc["F6 tam (kelepceler TL_RAY'e)"]
    bug = sonuc["bugun (2.7K, kelepce +3V3)"]
    sec = sonuc["10K + 1K bosaltma   <= SECILEN"]
    r.kosul("  1a: F6 asil sorunu GERCEKTEN cozuyor",
            f6[0]["pay"] > 20 * bug[0]["pay"],
            f"{bug[0]['pay']:.0f} mV -> {f6[0]['pay']:.0f} mV "
            f"({f6[0]['pay']/bug[0]['pay']:.0f} kat)")
    r.kosul("  1a: 🔴 ama F6 HIZLI AKIM menzilini de kesiyor "
            "(B15 bunu yazmamisti)",
            f6[3] < 0.75 * bug[3],
            f"{bug[3]*1e3:.1f} mV -> {f6[3]*1e3:.1f} mV "
            f"(%{(1-f6[3]/bug[3])*100:.0f} kayip)")
    r.kosul("  1a: 🔴 F6 sonrasi hizli yol ADS'ten ONCE kirpiyor",
            f6[3] < T.ADS_AKIM_KIRPMA,
            f"{f6[3]*1e3:.1f} mV < {T.ADS_AKIM_KIRPMA*1e3:.0f} mV — "
            f"tepe yakalamak icin var olan yol, yavas yoldan once doyuyor")
    r.kosul("  1a: 🔴 F6 TL431 acik devre kalintisini KAPATMIYOR",
            f6[1]["pay"] < 0,
            f"TL431 yokken ray {f6[1]['v(ray)']:.2f} V — ESP32 oluyor, "
            f"F6'li da F6'siz da")

    alt(r, "1b · SECILEN: R26/R33 -> 10K + 1K bosaltma (B18/F12)")
    r.kosul("  1b: pay bugunkunun en az 100 katina cikiyor",
            sec[0]["pay"] > 100 * bug[0]["pay"],
            f"{bug[0]['pay']:.0f} mV -> {sec[0]['pay']:.0f} mV "
            f"({sec[0]['pay']/bug[0]['pay']:.0f} kat)")
    r.kosul("  1b: TL431'in VARLIGINDAN BAGIMSIZ",
            abs(sec[0]["pay"] - sec[1]["pay"]) < 1.0,
            f"TL431 var {sec[0]['pay']:.0f} mV · yok {sec[1]['pay']:.0f} mV — "
            f"bosaltma direnci rayi 2.495 V'un altinda tuttugu icin TL431 "
            f"hic iletmiyor, yani kurtulus ona BAGLI DEGIL")
    fark = max(abs(b1(YENI_R_SERI, bosalt=BOSALTMA_R, tl431=True,
                      temp=tc)["v(ray)"]
                   - b1(YENI_R_SERI, bosalt=BOSALTMA_R, tl431=False,
                        temp=tc)["v(ray)"])
               for tc in (0, 27, 60, 85))
    r.kosul("  1b: bagimsizlik 0-85 C BOYUNCA suruyor",
            fark < 1e-3,
            f"en buyuk fark {fark*1e6:.1f} uV — sicaklik taramasi, cunku "
            f"ilk model tam burada kirilmisti (bolum 0b/2. deneme)")
    r.kosul("  1b: skop menzili HIC degismiyor",
            abs(sec[2] - bug[2]) < 0.01,
            f"{sec[2]:.1f} V = {bug[2]:.1f} V")
    r.kosul("  1b: hizli akim menzili HIC degismiyor",
            abs(sec[3] - bug[3]) < 1e-6,
            f"{sec[3]*1e3:.1f} mV = {bug[3]*1e3:.1f} mV")
    r.kosul("  1b: F6'dan her eksende iyi ya da esit",
            (sec[0]["pay"] > f6[0]["pay"] and sec[1]["pay"] > f6[1]["pay"]
             and sec[2] >= f6[2] and sec[3] >= f6[3]),
            "pay, TL431-yok hali, skop menzili ve hizli akim menzili")
    return sonuc


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — KELEPCE DOGRUSALLIGI: MENZIL SAYILARI NEREDEN GELIYOR
# ═══════════════════════════════════════════════════════════════════════

def kelepce_tavani(vray, rs, esik=1e-3):
    """Kelepcenin 1 mV'tan fazla hata yapmaya basladigi cikis gerilimi."""
    net = f"""* kelepce dogrusalligi
{D_BAT85}
{AYARLAR}
Vout cik 0 DC 0
R26 cik gpio {rs}
Vray ray 0 DC {vray}
D1 gpio ray DBAT85
D2 0 gpio DBAT85
.control
dc Vout 1.5 4 0.005
wrdata s.txt v(gpio)
.endc
.end
"""
    _, dz = spice.kos(net, BURASI / "_b18_dogru")
    for vin, vg in spice.degerler(dz / "s.txt"):
        if abs(vg - vin) > esik:
            return vin
    return 4.0


def bolum2(r):
    bolum(r, "BOLUM 2 — MENZIL SAYILARI NEREDEN GELIYOR (kelepce suprumesi)")
    r.bilgi("  Kullanilabilir tavan, kelepcenin 1 mV'tan fazla hata yapmaya")
    r.bilgi("  basladigi nokta. Diyot 'Vf'ten cok once yumusak iletime")
    r.bilgi("  giriyor, o yuzden tavan raydan 0.4 V yukarida DEGIL.")
    r.bilgi("")
    r.bilgi(f"  {'kelepce rayi':<22} {'R seri':>8} {'tavan':>8} "
            f"{'skop menzili':>14} {'hizli I+':>10}")
    r.bilgi("  " + "-" * 68)
    olculen = {}
    for ad, vray, rs in (("+3V3 (3.30 V)", 3.30, ESKI_R_SERI),
                         ("+3V3 (3.30 V)", 3.30, YENI_R_SERI),
                         ("TL_RAY (2.495 V)", T.TL431_V, ESKI_R_SERI),
                         ("TL_RAY (2.495 V)", T.TL431_V, YENI_R_SERI)):
        tav = kelepce_tavani(vray, rs)
        olculen[(round(vray, 3), rs)] = tav
        # ADC'nin kendi tavani da sinirlayici olabilir
        kul = min(tav, T.SKOP_TAVAN)
        r.bilgi(f"  {ad:<22} {rs/1e3:7.1f}k {tav:7.3f}V "
                f"{kul*SKOP_N:13.1f}V "
                f"{(kul-T.VREF)/T.HIZLI_G*1e3:9.1f}mV")
    r.bilgi("")
    tav33 = olculen[(3.30, ESKI_R_SERI)]
    tavtl = olculen[(round(T.TL431_V, 3), ESKI_R_SERI)]
    r.kosul("  B18-2: +3V3 kelepcesi ADC'nin 3.1 V tavanini SINIRLAMIYOR",
            tav33 > T.SKOP_TAVAN,
            f"kelepce {tav33:.3f} V > ADC tavani {T.SKOP_TAVAN:.2f} V — "
            f"menzili ADC belirliyor, kelepce degil")
    r.kosul("  B18-2: TL_RAY kelepcesi ADC tavanindan ONCE devreye giriyor",
            tavtl < T.SKOP_TAVAN,
            f"{tavtl:.3f} V < {T.SKOP_TAVAN:.2f} V — F6'nin menzil bedeli "
            f"buradan cikiyor")
    r.kosul("  B18-2: sabitler dosyasindaki F6 tavani olculenle uyusuyor",
            abs(tavtl - T.KELEPCE_TL_TAVAN) < 0.02,
            f"olculen {tavtl:.3f} V · sabit {T.KELEPCE_TL_TAVAN:.3f} V")
    r.kosul("  B18-2: seri direnci buyutmek menzili BOZMUYOR",
            olculen[(3.30, YENI_R_SERI)] > T.SKOP_TAVAN,
            f"10K'da tavan {olculen[(3.30, YENI_R_SERI)]:.3f} V, "
            f"hala ADC tavaninin ustunde")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — SECILEN COZUMUN ZORLANMASI
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r):
    bolum(r, "BOLUM 3 — SECILEN COZUM ZORLANIYOR (10K + 1K bosaltma)")
    r.bilgi("  Her satirda TL431 hem VAR hem YOK halinde deneniyor.")
    r.bilgi("")
    r.bilgi(f"  {'kosul':<44} {'TL431 var':>11} {'TL431 yok':>11}")
    r.bilgi("  " + "-" * 70)
    en_kotu = 1e9
    for ad, kw in (
            ("nominal (tavan 10.5 V, 27 C)",          {}),
            ("24 V kaynak %10 yuksek -> tavan 11.6 V", dict(vop=11.6)),
            ("TL072 raya TAM oturuyor (12.0 V)",       dict(vop=12.0)),
            ("60 C ortam",                             dict(temp=60)),
            ("0 C ortam",                              dict(temp=0)),
            ("olu 3V3 rayi 10k yukluyor",              dict(olu_yuk=10e3)),
            ("olu 3V3 rayi 1k yukluyor",               dict(olu_yuk=1e3)),
    ):
        sat = f"  {ad:<44}"
        for tl in (True, False):
            d = b1(YENI_R_SERI, bosalt=BOSALTMA_R, tl431=tl, **kw)
            en_kotu = min(en_kotu, d["pay"])
            sat += f" {d['pay']:8.0f}mV"
        r.bilgi(sat)
    r.kosul("  B18-3: en kotu kosulda bile pay 1 V'un uzerinde",
            en_kotu > 1000.0, f"en kotu {en_kotu:.0f} mV")
    r.bilgi("")
    r.bilgi("  ⚠ 'Olu ray yukluyor' satirlari KOTUMSER tarafta: gercekte")
    r.bilgi("    beslemesiz ESP32 ve ADS modulleri bir miktar yuk olusturur")
    r.bilgi("    ve rayi DAHA ASAGI ceker. Model onlari yuksuz sayiyor.")

    alt(r, "3b · Tek kanal mi, iki kanal mi enjekte ediyor")
    r.bilgi("     TL072'lerden yalnizca biri tavana oturmus olabilir.")
    net_tek = b1_netlist(YENI_R_SERI, "ray", "ray", BOSALTMA_R).replace(
        f"Vs2 cik2 0 DC {T.TL072_CIKIS_TAVAN}", "Vs2 cik2 0 DC 0")
    d_tek = op(net_tek, "b1_tekkanal")
    d_cift = b1(YENI_R_SERI, bosalt=BOSALTMA_R)
    r.bilgi(f"       tek kanal : ray {d_tek['v(ray)']:.3f} V")
    r.bilgi(f"       iki kanal : ray {d_cift['v(ray)']:.3f} V")
    r.kosul("  3b: iki kanal EN KOTU hal — dogru senaryo simule edildi",
            d_cift["v(ray)"] > d_tek["v(ray)"],
            f"{d_cift['v(ray)']:.3f} V > {d_tek['v(ray)']:.3f} V")

    alt(r, "3c · 🔴 R41 TEK BASINA ARIZA NOKTASI MI? — iki korumanin ortusmesi")
    r.bilgi("     Kabul olcutu: HICBIR TEK ariza ESP32'yi oldurmemeli.")
    r.bilgi("     R41 bir tek direnc; acik devre kalirsa ne olur?")
    r.bilgi("")
    r.bilgi(f"     {'durum':<40} {'3V3 rayi':>10} {'pay':>10}")
    r.bilgi("     " + "-" * 62)
    haller = {}
    for ad, bos, tl in (("saglam (R41 var, TL431 var)", BOSALTMA_R, True),
                        ("TEK ARIZA: TL431 acik devre", BOSALTMA_R, False),
                        ("TEK ARIZA: R41 acik devre", ACIK, True),
                        ("CIFT ARIZA: ikisi de acik", ACIK, False)):
        d = b1(YENI_R_SERI, bosalt=bos, tl431=tl)
        haller[ad] = d
        r.bilgi(f"     {ad:<40} {d['v(ray)']:9.3f}V {d['pay']:9.0f}mV")
    r.kosul("  3c: R41 acik devre kalirsa TL431 devrali",
            haller["TEK ARIZA: R41 acik devre"]["pay"] > 500,
            f"{haller['TEK ARIZA: R41 acik devre']['pay']:.0f} mV — "
            f"10K seri direnc sayesinde TL431'in tek basina tuttugu "
            f"seviye de guvenli (2.7K'da bu 18 mV idi)")
    r.kosul("  3c: TL431 acik devre kalirsa R41 devrali",
            haller["TEK ARIZA: TL431 acik devre"]["pay"] > 500,
            f"{haller['TEK ARIZA: TL431 acik devre']['pay']:.0f} mV")
    r.kosul("  3c: KABUL OLCUTU — hicbir TEK ariza ESP32'yi oldurmuyor",
            all(haller[k]["pay"] > 0 for k in haller
                if not k.startswith("CIFT")),
            "iki koruma birbirini ortuyor; yalnizca CIFT arizada "
            f"({haller['CIFT ARIZA: ikisi de acik']['v(ray)']:.1f} V) ray "
            f"asiliyor")
    r.bilgi("")
    alt(r, "3d · TL431 KISA DEVRE olursa (acik devrenin oteki ucu)")
    net_kisa = b1_netlist(YENI_R_SERI, "ray", "ray", BOSALTMA_R).replace(
        tl431_sont(), "Rtl tlray 0 0.2\n")
    dk = op(net_kisa, "b1_kisa")
    r.bilgi(f"     B1'de ray {dk['v(ray)']:.3f} V — ESP32 acisindan ZARARSIZ.")
    r.kosul("  3d: TL431 kisa devre B1'de ESP32'yi tehdit etmiyor",
            (T.ESP_MUTLAK_PIN_UST - dk["v(ray)"]) * 1e3 > 1000,
            f"pay {(T.ESP_MUTLAK_PIN_UST-dk['v(ray)'])*1e3:.0f} mV")
    r.bilgi("")
    r.bilgi("     ⚠ Ama NORMAL beslemede yikici degil SESSIZ: R1 (220R)")
    ik = (3.3 - 0) / T.R1_TL431
    r.bilgi(f"       uzerinde {ik*1e3:.0f} mA / {3.3*ik*1e3:.0f} mW ve VREF")
    r.bilgi("       SIFIRA duser — butun bolucu altlari, iki ADS referans")
    r.bilgi("       pini ve hizli yolun REF ucu referansini kaybeder. Yani")
    r.bilgi("       hicbir sey yanmaz ama HER OLCUM bozulur.")
    r.kosul("  3d: R1 kisa devrede kendi govdesini asmiyor",
            3.3 * ik < 0.25,
            f"{3.3*ik*1e3:.0f} mW < 250 mW (1/4W) — R1 sigorta gibi acilmaz, "
            f"ariza SESSIZ kalir")

    r.bilgi("     ⚠ Bu ORTUSME B18/F12'nin en onemli ozelligi: iki koruma")
    r.bilgi("       BIRBIRINDEN BAGIMSIZ. R26/R33'un 10K'ya cikmasi olmasaydi")
    r.bilgi("       R41 acik devre halinde pay 18 mV'a duserdi — yani iki")
    r.bilgi("       degisiklik AYRI AYRI degil, BIRLIKTE anlamli.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — NORMAL CALISMAYA ETKISI (asil risk burada)
# ═══════════════════════════════════════════════════════════════════════

def dc_hata_supurme(rs, temp, v33=3.30, adim=0.05):
    """GPIO dugumundeki GERCEK DC hatasi — kacak ve yumusak iletim BIRDEN.

    Elle "I_R x R" carpmak yerine devre supuruluyor: iki diyot da yerinde,
    kacaklari kismen birbirini goturuyor ve hata menzil boyunca ISARET
    DEGISTIRIYOR. Tek bir sayi bunu anlatamaz.
    """
    net = f"""* kelepce DC hatasi
{D_BAT85}
{AYARLAR}
.options temp={temp}
Vout cik 0 DC 0
R26 cik gpio {rs}
Vray ray 0 DC {v33}
D1 gpio ray DBAT85
D2 0 gpio DBAT85
.control
dc Vout 0 {T.SKOP_TAVAN} {adim}
wrdata s.txt v(gpio)
.endc
.end
"""
    _, dz = spice.kos(net, BURASI / "_b18_dchata")
    return [(vin, vg - vin) for vin, vg in spice.degerler(dz / "s.txt")]


def kelepce_payi_enkotu(rs, v33=3.30):
    """Asiri menzilde kelepce seviyesi — EN KOTU Vf ile (veri sayfasi)."""
    vf = 0.35
    for _ in range(60):
        i = (T.TL072_CIKIS_TAVAN - v33 - vf) / rs
        vf = T.bat85_vf_maks(i)
    return (v33 + T.ESP_GPIO_VDD_PAYI - (v33 + vf)) * 1e3, i, vf


def bolum4(r):
    bolum(r, "BOLUM 4 — SERI DIRENCI BUYUTMEK NORMAL CALISMAYI BOZUYOR MU")
    r.bilgi("  Seri direnci buyutmek ESP32 ADC'sinin gordugu KAYNAK")
    r.bilgi("  EMPEDANSINI buyutuyor. Bedeller tek tek olculuyor.")
    lsb = T.SKOP_TAVAN / 4096

    alt(r, "4a · DC hatasi — kelepce KACAGI (baskin terim, R ile buyuyor)")
    r.bilgi("     Iki diyot da kacak veriyor: D1 raydan dugume (menzilin")
    r.bilgi("     ALTINDA baskin), D2 dugumden GND'ye (USTUNDE). Hata bu")
    r.bilgi("     yuzden duz bir ofset degil, isaret degistiren bir egrilik.")
    r.bilgi("     Asagisi devrenin SUPURULMESIYLE olculdu, elle carpim degil.")
    r.bilgi("")
    r.bilgi(f"     {'R':>7} {'T':>6} {'en buyuk |hata|':>17} {'LSB':>7} "
            f"{'%FS':>8}")
    r.bilgi("     " + "-" * 50)
    olculen = {}
    for rs in (ESKI_R_SERI, YENI_R_SERI):
        for tc in (25, 60):
            en = max(abs(h) for _, h in dc_hata_supurme(rs, tc))
            olculen[(rs, tc)] = en
            r.bilgi(f"     {rs/1e3:6.1f}k {tc:5d}C {en*1e3:15.2f} mV "
                    f"{en/lsb:6.2f} {en/T.SKOP_TAVAN*100:7.3f}")
    r.kosul("  4a: kacak hatasi R ile ORANTILI BUYUYOR — degisikligin BEDELI",
            olculen[(YENI_R_SERI, 25)] > 2 * olculen[(ESKI_R_SERI, 25)],
            f"25 C: {olculen[(ESKI_R_SERI, 25)]*1e3:.2f} -> "
            f"{olculen[(YENI_R_SERI, 25)]*1e3:.2f} mV · 60 C: "
            f"{olculen[(ESKI_R_SERI, 60)]*1e3:.2f} -> "
            f"{olculen[(YENI_R_SERI, 60)]*1e3:.2f} mV")
    r.bilgi("")
    r.bilgi("     SPICE modelinin ters kacagi SABIT (IS = 0.26 uA). Gercek")
    r.bilgi("     Schottky'de kacak ters gerilimle artar; o yuzden tek modele")
    r.bilgi("     guvenmeyip veri sayfasi degerleriyle TARAMA:")
    r.bilgi("")
    r.bilgi(f"     {'I_R':>9} {'kaynak':<26} {ESKI_R_SERI/1e3:>7.1f}k "
            f"{YENI_R_SERI/1e3:>8.1f}k")
    r.bilgi("     " + "-" * 56)
    for ir, kaynak in ((T.BAT85_IR_TIPIK_3V, "tipik, ~3 V, 25 C"),
                       (T.BAT85_IR_TIPIK_3V_60C, "tipik, ~3 V, 60 C"),
                       (T.BAT85_IR_MAKS, "MAKS, 25 V, 25 C")):
        r.bilgi(f"     {ir*1e6:7.1f}uA {kaynak:<26} "
                f"{ir*ESKI_R_SERI*1e3:6.2f}mV {ir*YENI_R_SERI*1e3:7.2f}mV")
    en_kotu = T.BAT85_IR_MAKS * YENI_R_SERI
    r.kosul("  4a: en kotu kacak bile tam olcegin %1'inin altinda",
            en_kotu < 0.01 * T.SKOP_TAVAN,
            f"{en_kotu*1e3:.1f} mV = %{en_kotu/T.SKOP_TAVAN*100:.2f} "
            f"({en_kotu/lsb:.0f} LSB)")
    r.bilgi("")
    r.bilgi("     -> Bu, SKOP kanalinin DC dogrulugunu etkiliyor. OLCUM")
    r.bilgi("        kanallari (ADS) bu yoldan GECMIYOR. Sicaklikla degistigi")
    r.bilgi("        icin tek seferlik kalibrasyon tam silmez.")

    alt(r, "4b · ORNEKLEME PENCERESI — 🔴 DOGRULANAMAYAN TEK KALEM")
    r.bilgi("     ESP32'nin SAR'i her ornekte ~1 pF'lik tutma kondansatorunu")
    r.bilgi("     dugume baglar. Iki kanal sirayla okundugu icin o kondansator")
    r.bilgi("     ONCEKI KANALIN gerilimiyle geliyor; dugumde bir sicrama")
    r.bilgi("     olusuyor ve ORNEKLEME PENCERESI icinde sonmesi gerekiyor.")
    r.bilgi("")
    cd, ts = T.KELEPCE_DUGUM_C, 1.0 / T.ESP_KANAL_SPS
    sic = T.SKOP_TAVAN * T.ESP_SH_C / (T.ESP_SH_C + cd)
    r.bilgi(f"     dugum kapasitesi (VARSAYIM)  : {cd*1e12:.0f} pF")
    r.bilgi(f"     en kotu sicrama (kanallar arasi tam olcek fark): "
            f"{sic*1e3:.1f} mV")
    r.bilgi("")
    r.bilgi(f"     {'pencere':>10} {ESKI_R_SERI/1e3:>10.1f}k artik "
            f"{YENI_R_SERI/1e3:>9.1f}k artik")
    r.bilgi("     " + "-" * 44)
    for t_acq in (100e-9, 250e-9, 500e-9, 1e-6, 2e-6):
        s = f"     {t_acq*1e9:8.0f}ns"
        for rs in (ESKI_R_SERI, YENI_R_SERI):
            art = sic * math.exp(-t_acq / (rs * (cd + T.ESP_SH_C)))
            s += f" {art*1e3:14.3f}mV"
        r.bilgi(s)
    r.bilgi("")
    r.bilgi("     🔴 ESP32-S3'un ORNEKLEME PENCERESI BELGELENMEMIS. Espressif")
    r.bilgi("        veri sayfasinda ve ESP-IDF kilavuzunda deger yok; arandi,")
    r.bilgi("        bulunamadi. Bu kalem SIMULASYONLA KAPATILAMIYOR —")
    r.bilgi("        durustce ACIK birakiliyor.")
    r.kosul("  4b: ornekler ARASINDA tam oturma her iki degerde de garanti",
            ts / (YENI_R_SERI * cd) > 50,
            f"{ts/(YENI_R_SERI*cd):.0f} zaman sabiti — belirsiz olan yalnizca "
            f"pencere ICINDEKI oturma")
    r.kosul("  4b: risk YENI DEGIL, "
            f"{YENI_R_SERI/ESKI_R_SERI:.1f} kat buyuyor",
            YENI_R_SERI / ESKI_R_SERI < 5,
            f"ayni belirsizlik {ESKI_R_SERI/1e3:.1f}K'da da vardi; oradaki "
            f"artik da ayni pencereye bagliydi")
    r.bilgi("")
    r.bilgi("     TEZGAH TESTI (kart kurulunca): GPIO4'e 0 V, GPIO5'e tam")
    r.bilgi("     olcek ver, sonra ters cevir. Okumalarda kanaldan kanala")
    r.bilgi("     kayma varsa pencere yetmiyordur. Cozum banda dokunmadan:")
    r.bilgi(f"     dugume 100 pF eklemek sicramayi "
            f"{T.SKOP_TAVAN*T.ESP_SH_C/(T.ESP_SH_C+cd+100e-12)*1e3:.0f} mV'a "
            f"indirir")
    r.bilgi(f"     ve kutbu {1/(2*math.pi*YENI_R_SERI*(cd+100e-12))/1e3:.0f} "
            f"kHz'te birakir (Sallen-Key {T.SK_F0/1e3:.1f} kHz).")

    alt(r, "4c · Bant genisligi")
    for rs in (ESKI_R_SERI, YENI_R_SERI):
        r.bilgi(f"     R={rs/1e3:5.1f}k -> kutup "
                f"{1/(2*math.pi*rs*cd)/1e3:8.1f} kHz")
    fc10 = 1 / (2 * math.pi * YENI_R_SERI * cd)
    r.kosul("  4c: kutup Sallen-Key'in en az 10 kati ustunde",
            fc10 > 10 * T.SK_F0,
            f"{fc10/1e3:.0f} kHz vs {T.SK_F0/1e3:.2f} kHz")

    alt(r, "4d · Gurultu — R'ye DEGIL, dugum kapasitesine bagli")
    r.bilgi("     ⚠ R26 Sallen-Key'in ARDINDA; kendi gurultusunu SK SUZMEZ.")
    r.bilgi("     Tek kutup R26*C_dugum -> sonuc kT/C limiti, R'den BAGIMSIZ")
    r.bilgi("     (buyuk R = daha cok gurultu yogunlugu ama daha dar bant).")
    kt_c = math.sqrt(1.380649e-23 * 300 / cd)
    r.bilgi(f"       sqrt(kT/C) = {kt_c*1e6:.1f} uV rms   ({cd*1e12:.0f} pF)")
    r.kosul("  4d: gurultu bir LSB'nin cok altinda",
            kt_c < lsb / 10,
            f"{kt_c*1e6:.1f} uV = LSB'nin 1/{lsb/kt_c:.0f}'i "
            f"(LSB {lsb*1e6:.0f} uV)")

    alt(r, "4e · R41'in surekli maliyeti")
    for v33 in (3.30, 3.465):
        ib = v33 / BOSALTMA_R
        r.bilgi(f"     {v33:.3f} V -> {ib*1e3:.2f} mA, {v33*ib*1e3:.1f} mW")
    ib = 3.465 / BOSALTMA_R
    r.kosul("  4e: kartin 3V3 yukunun kucuk bir dilimi",
            ib < 0.25 * T.ESP_BOSTA_AKIM,
            f"{ib*1e3:.2f} mA / {T.ESP_BOSTA_AKIM*1e3:.0f} mA (ESP32 bosta) "
            f"= %{ib/T.ESP_BOSTA_AKIM*100:.0f} — USB/LDO icin onemsiz, "
            f"PILLE calismada not edilmeli")
    r.kosul("  4e: 1/4W govde icin genis pay",
            3.465 * ib < 0.25 * 0.5,
            f"{3.465*ib*1e3:.1f} mW < 125 mW")

    alt(r, "4f · 🔴 Kelepce seviyesi — VERI SAYFASI EN KOTU Vf ile")
    r.bilgi("     ⚠ Bu bolumun ilk surumu SPICE'in TIPIK Vf'ini kullaniyordu.")
    r.bilgi("       Projenin kendi kurali (tasarim3_sabit.py, BAT85 blogu)")
    r.bilgi("       'en kotu durum V_F MAKS tablosundan okunur' diyor.")
    r.bilgi("       Tabloya gecilince SONUC ISARET DEGISTIRIYOR.")
    r.bilgi("")
    r.bilgi(f"     {'R':>7} {'I':>9} {'Vf maks':>9} {'GPIO':>9} "
            f"{'sinir':>8} {'pay':>8}")
    r.bilgi("     " + "-" * 54)
    paylar = {}
    for rs in (ESKI_R_SERI, YENI_R_SERI):
        pay, i, vf = kelepce_payi_enkotu(rs)
        paylar[rs] = pay
        r.bilgi(f"     {rs/1e3:6.1f}k {i*1e3:8.3f}mA {vf:8.3f}V "
                f"{3.30+vf:8.3f}V {3.30+T.ESP_GPIO_VDD_PAYI:7.3f}V "
                f"{pay:7.0f}mV")
    r.kosul("  4f: 🔴 EN KOTU Vf'te kelepce seviyesi ONCE DE SONRA DA "
            "sinirin USTUNDE",
            paylar[ESKI_R_SERI] < 0 and paylar[YENI_R_SERI] < 0,
            f"{paylar[ESKI_R_SERI]:.0f} mV -> {paylar[YENI_R_SERI]:.0f} mV — "
            f"B18'in GETIRDIGI bir kusur DEGIL, zaten vardi")
    r.kosul("  4f: seri direnci buyutmek asimi buyuk olcude kapatiyor",
            abs(paylar[YENI_R_SERI]) < 0.2 * abs(paylar[ESKI_R_SERI]),
            f"asim {abs(paylar[ESKI_R_SERI]):.0f} -> "
            f"{abs(paylar[YENI_R_SERI]):.0f} mV "
            f"({abs(paylar[ESKI_R_SERI] / paylar[YENI_R_SERI]):.0f} kat)")
    r.bilgi("")
    r.bilgi("     Anlami: skop girisi ASIRI MENZILDEYKEN GPIO, VDD+0.3'u")
    r.bilgi(f"     {abs(paylar[YENI_R_SERI]):.0f} mV asiyor ve ESP32'nin kendi")
    r.bilgi("     ESD diyodu kucuk bir pay ustleniyor. Akim 1 mA'in altinda —")
    r.bilgi("     anlik olum degil, SPEK DISI ZORLAMA. Tam kapatmak icin")
    r.bilgi("     R ~15K gerekirdi, ama o zaman 4a'daki kacak hatasi buyur.")

    alt(r, "4g · R NEDEN 10K — karsit maliyetlerin taramasi")
    r.bilgi(f"     {'R':>7} {'B1 pay':>10} {'B1 pay':>11} {'kelepce':>9} "
            f"{'kacak25':>9} {'kacak60':>9}")
    r.bilgi(f"     {'':>7} {'(R41 var)':>10} {'(R41 ACIK)':>11} "
            f"{'(enkotu)':>9} {'':>9} {'':>9}")
    r.bilgi("     " + "-" * 60)
    tara = {}
    for rs in (2.7e3, 4.7e3, 6.8e3, 10e3, 15e3, 22e3):
        d1 = b1(rs, bosalt=BOSALTMA_R)
        d2 = b1(rs, bosalt=ACIK)
        k25 = max(abs(h) for _, h in dc_hata_supurme(rs, 25, adim=0.1))
        k60 = max(abs(h) for _, h in dc_hata_supurme(rs, 60, adim=0.1))
        tara[rs] = (d1["pay"], d2["pay"], kelepce_payi_enkotu(rs)[0], k25, k60)
        r.bilgi(f"     {rs/1e3:6.1f}k {d1['pay']:9.0f}mV {d2['pay']:10.0f}mV "
                f"{tara[rs][2]:8.0f}mV {k25*1e3:7.2f}mV {k60*1e3:7.2f}mV")
    r.bilgi("")
    r.bilgi("     Ilk uc sutun R ile IYILESIYOR, son iki sutun KOTULESIYOR.")
    r.kosul("  4g: 10K, R41 ACIKKEN bile genis pay veriyor",
            tara[10e3][1] > 700,
            f"{tara[10e3][1]:.0f} mV (4.7K'da {tara[4.7e3][1]:.0f}, "
            f"2.7K'da {tara[2.7e3][1]:.0f} mV)")
    r.kosul("  4g: 10K'nin ustune cikmak kacak hatasini hizla buyutuyor",
            tara[22e3][3] > 2 * tara[10e3][3],
            f"25 C kacagi 10K'da {tara[10e3][3]*1e3:.2f} mV, "
            f"22K'da {tara[22e3][3]*1e3:.2f} mV")
    r.kosul("  4g: secim bir TAKAS — tek yonlu bir iyilestirme DEGIL",
            tara[10e3][0] > tara[2.7e3][0] and tara[10e3][3] > tara[2.7e3][3],
            "B1 payi ve kelepce payi kazaniyor, kacak hatasi kaybediyor")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 5 — B15 SENARYOLARI DEGISIYOR MU
# ═══════════════════════════════════════════════════════════════════════

def bolum5(r):
    bolum(r, "BOLUM 5 — DEGISIKLIK B15 SENARYOLARINI BOZUYOR MU")
    r.bilgi("  R26/R33 buyudu. Bu direncler ariza aninda GPIO'ya kacan")
    r.bilgi("  akimi SINIRLIYOR — buyumesi her arizada iyi yonde olmali.")
    r.bilgi("")
    r.bilgi(f"  {'senaryo':<40} {'2.7K':>12} {'10K':>12}")
    r.bilgi("  " + "-" * 68)
    kotulesen = []
    # ⚠ Ilk surumde ucuncu satir birincinin AYNISIYDI (ayni vsur, ayni
    #   netlist) — iki farkli etiketle tek simulasyon. Kaldirildi.
    for ad, vsur in (("TL072 cikisi +10.5 V'a oturmus", T.TL072_CIKIS_TAVAN),
                     ("TL072 cikisi -10.5 V'a oturmus", -T.TL072_CIKIS_TAVAN),
                     ("besleme %10 yuksek: cikis +11.6 V", 11.6)):
        akim = {}
        for rs in (ESKI_R_SERI, YENI_R_SERI):
            net = f"""* GPIO kelepce akimi
{D_BAT85}
{AYARLAR}
Vs1 cik1 0 DC {vsur}
R26 cik1 gpio1 {rs}
Vray ray 0 DC 3.30
Vam kel ray DC 0
D1 gpio1 kel DBAT85
Vam2 kel2 0 DC 0
D2 kel2 gpio1 DBAT85
.control
op
print i(Vam) i(Vam2) v(gpio1)
.endc
.end
"""
            d = op(net, "b15tekrar")
            akim[rs] = max(abs(d.get("i(vam)", 0)), abs(d.get("i(vam2)", 0)))
        if akim[YENI_R_SERI] > akim[ESKI_R_SERI]:
            kotulesen.append(ad)
        r.bilgi(f"  {ad:<40} {akim[ESKI_R_SERI]*1e3:9.2f}mA "
                f"{akim[YENI_R_SERI]*1e3:9.2f}mA")
    r.kosul("  B18-5: hicbir ariza senaryosunda kelepce akimi ARTMIYOR",
            not kotulesen, "hepsi azaliyor ya da ayni" if not kotulesen
            else f"kotulesen: {kotulesen}")
    r.bilgi("")
    r.bilgi("  ⚠ Diger yon: seri direnc buyudukce kelepce dugumu kaynaktan")
    r.bilgi("    daha iyi AYRILIYOR, yani koruma GUCLENIYOR. Bedeli yalnizca")
    r.bilgi("    bolum 4'te olculen ADC tarafi.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 6 — SAHA KAYITLARI VE VERI SAYFASI ARASTIRMASI
# ═══════════════════════════════════════════════════════════════════════

def akim_paylasimi():
    """B1'de kelepce akimi BAT85 ile ESP32'nin ESD diyodu arasinda nasil
    bolunuyor? TI'in 1 mA olcutu CIPE giren akim icin."""
    net = f"""* akim paylasimi
{D_BAT85}
{D_ESD}
{AYARLAR}
Vs1 cik1 0 DC {T.TL072_CIKIS_TAVAN}
Vs2 cik2 0 DC {T.TL072_CIKIS_TAVAN}
R26 cik1 gpio1 {YENI_R_SERI}
R33 cik2 gpio2 {YENI_R_SERI}
Vb1 kel1 ray DC 0
D1 gpio1 kel1 DBAT85
Vb2 kel2 ray DC 0
D3 gpio2 kel2 DBAT85
Ve1 esd1 ray DC 0
Desp1 gpio1 esd1 DESD
Ve2 esd2 ray DC 0
Desp2 gpio2 esd2 DESD
R1 tlray ray {T.R1_TL431}
R2 tlray vtap {T.VREF_RA}
R3 vtap 0 {T.VREF_RB}
Rbos ray 0 {BOSALTMA_R}
{tl431_sont()}.control
op
print v(ray) i(Vb1) i(Vb2) i(Ve1) i(Ve2)
.endc
.end
"""
    d = op(net, "paylasim")
    return (abs(d["i(vb1)"]) + abs(d["i(vb2)"]),
            abs(d["i(ve1)"]) + abs(d["i(ve2)"]), d["v(ray)"])


def bolum6(r):
    bolum(r, "BOLUM 6 — SAHA KAYITLARI: BU ARIZA TIPI BELGELENMIS MI")
    r.bilgi("  B18'in cozdugu sey uydurulmus bir senaryo degil; ureticilerin")
    r.bilgi("  adlandirdigi bir ariza tipi. Ama SECTIGIMIZ COZUM onlarin")
    r.bilgi("  onerdigi standart cozum DEGIL — ikisi de yazilmali.")

    alt(r, "6a · Ariza tipi: 'back powering' / olu rayin geri beslenmesi")
    r.bilgi("     Microchip, 3V Tips'n Tricks bolum 8, TIP #11:")
    r.bilgi("       'diyot kelepce 3.3 V beslemesine akim ENJEKTE eder...")
    r.bilgi("        HAFIF YUKLU 3.3 V raylarinda bu akim rayi 3.3 V'un")
    r.bilgi("        USTUNE cikarabilir.'")
    r.bilgi("     TIP #17 ayni seyi ANALOG hal icin (op-amp -> kelepce -> ADC)")
    r.bilgi("     tekrarliyor ve seri direnc icin sunu diyor: 'direnc, diyodu")
    r.bilgi("     ve 3.3 V beslemesini KORUYACAK ama analog basarimi")
    r.bilgi("     BOZMAYACAK sekilde secilmeli.' — B18 bolum 4g tam bu takas.")
    r.bilgi("     TIP #10: 'kelepce diyot akimi kucuk (mikroamper) tutulmali;")
    r.bilgi("     buyurse LATCH-UP riski var.'")
    r.bilgi("")
    r.bilgi("     TI SLVAEX7A sekil 2-2'nin basligi zaten 'Input Current Path")
    r.bilgi("     of a Back-Powered Op Amp'. Ayni belge: ESD diyot akimini")
    r.bilgi("     'mumkun oldugunda +-1 mA altinda tut' diyor.")
    r.bilgi("")
    r.bilgi("     ⚠ TI'in 1 mA olcutu CIPIN KENDI ESD yapisina giren akim")
    r.bilgi("       icin. Bizde akim BAT85'ten geciyor; ESP32'nin payini")
    r.bilgi("       olcmek icin cipin ESD diyodu da modele konuldu:")
    bat, esp, vray = akim_paylasimi()
    r.bilgi(f"         BAT85'ten        : {bat*1e3:.3f} mA "
            f"(anma {T.BAT85_IF_SUREKLI*1e3:.0f} mA surekli)")
    r.bilgi(f"         ESP32'nin ESD'si : {esp*1e6:.3f} uA "
            f"(%{esp/(bat+esp)*100:.4f})")
    r.kosul("  6a: cipe giren akim TI'in 1 mA olcutunun cok altinda",
            esp < 1e-3,
            f"{esp*1e6:.3f} uA — Schottky, silisyum ESD diyodundan cok"
            f" daha alcakta iletiyor; B15'in BAT85'i 1N4148'e tercih"
            f" etmesinin sebebi tam bu")
    r.kosul("  6a: BAT85 kendi surekli anmasinin cok altinda",
            bat < 0.05 * T.BAT85_IF_SUREKLI,
            f"{bat*1e3:.2f} mA / {T.BAT85_IF_SUREKLI*1e3:.0f} mA")
    r.kosul("  6a: Microchip'in latch-up esigi de rahat saglaniyor",
            b1(YENI_R_SERI, bosalt=BOSALTMA_R)["ienj"] < T.ESP_LATCHUP_AKIM,
            f"{b1(YENI_R_SERI, bosalt=BOSALTMA_R)['ienj']*1e3:.2f} mA << "
            f"{T.ESP_LATCHUP_AKIM*1e3:.0f} mA (JESD78)")

    alt(r, "6b · 🔴 DURUSTLUK: bosaltma direnci STANDART COZUM DEGIL")
    r.bilgi("     Arastirma, 'olu raya bosaltma direnci' oneren bir uretici")
    r.bilgi("     uygulama notu BULAMADI. Belgelenmis cozumler sunlar:")
    r.bilgi("")
    r.bilgi("       1. Op-amp'i ADC'nin KENDI beslemesinden calistir — sinyal")
    r.bilgi("          fiziksel olarak rayi asamaz (TI SLAA593: 'en basit yol')")
    r.bilgi("       2. Kelepceyi diyot yerine TRANSISTORLE yap, fazlayi")
    r.bilgi("          GND'ye ak_it (Microchip TIP #11)")
    r.bilgi("       3. GND'ye ZENER kelepce — 'beslemenin ozelliklerine")
    r.bilgi("          BAGLI DEGIL' (Microchip TIP #17)")
    r.bilgi("       4. Op-amp'li hassas kelepce — 'besleme hic etkilenmez'")
    r.bilgi("          (Microchip TIP #17)")
    r.bilgi("       5. Seri direnci mikroamper duzeyine gore boyutla")
    r.bilgi("       6. Olu rayi yuzer birakma, GND'ye bagla (TI SLVAEX7A)")
    r.bilgi("       7. Besleme sirasi kurali (ADI): beslemeler sinyallerden")
    r.bilgi("          ONCE ya da AYNI ANDA kurulmali")
    r.bilgi("")
    r.bilgi("     Bizim cozumumuz 5 + (rayi yukleyerek 6'nin yumusak hali).")
    r.bilgi("     Dayanagi EDN/ADI'nin sartI: 'ADC besleme rayi kelepce")
    r.bilgi("     akimini SOGURABILMELI, dusmeden.' Bosaltma direnci bunu")
    r.bilgi("     saglayan en ucuz yol — ama TUREVDIR, alintilanmis degil.")
    r.bilgi("")
    r.bilgi("     1. secenek (op-amp'i 3V3'ten besle) BU KARTTA UYGULANAMAZ:")
    r.bilgi("     TL072 +-12 V'ta cunku skop girisi CIFT YONLU ve Sallen-Key")
    r.bilgi("     +-1.4 V salinmali. 3.3 V tek besleme bunu veremez.")
    r.kosul("  6b: 1. secenek (op-amp'i 3V3'ten besle) bu kartta GECERSIZ",
            (T.SKOP_TAVAN - T.VREF) / T.HIZLI_G > 0 and T.VREF > 1.0,
            f"skop Sallen-Key'i VREF={T.VREF:.3f} V etrafinda +-1.385 V "
            f"salinmali; 3.3 V tek besleme {T.VREF+1.385:.2f} V tepe "
            f"veremez")

    alt(r, "6c · 🔴 YENI BULUNAN YOL: modulun LDO'suna TERS AKIM")
    r.bilgi("     ESP32 modulunun 3V3 pini bir LDO CIKISI. Raya akim basmak")
    r.bilgi("     onu kendi girisinin ustune cikariyor:")
    r.bilgi("       TI SSZT658: 'cikis, girisi + govde diyodu kadar asarsa")
    r.bilgi("        govde diyodu iletir; TERS AKIM isinma, elektromigrasyon")
    r.bilgi("        ya da latch-up ile CIHAZI BOZABILIR.'")
    r.bilgi("       ROHM 66AN115E: 'LDO'lar cikistan girise ters akim akitir;")
    r.bilgi("        IC'nin bozulmamasi icin normalde DISARIDAN ters akim")
    r.bilgi("        koruma diyodu baglanir.'")
    r.bilgi("")
    r.bilgi("     ⚠ Bu, B15'in de B18'in ilk surumunun de GORMEDIGI bir yol:")
    r.bilgi("       zarar yalnizca ESP32'nin cekirdegine degil, MODULUN")
    r.bilgi("       REGULATORUNE de gidebilir. Ustelik LDO'nun govde diyodu")
    r.bilgi("       uzerinden +5 V agina da gecer — ve bu kartin analog +5 V'u")
    r.bilgi("       ayni modulden geliyor (J5 pin 8).")
    r.bilgi("")
    r.bilgi(f"     {'durum':<34} {'3V3 rayi':>10} {'LDO ters gerilimi':>19}")
    r.bilgi("     " + "-" * 66)
    for ad, rs, bos in (("B18 oncesi (2.7K, R41 yok)", ESKI_R_SERI, ACIK),
                        ("B18 sonrasi (10K + R41)", YENI_R_SERI, BOSALTMA_R)):
        v = b1(rs, bosalt=bos)["v(ray)"]
        r.bilgi(f"     {ad:<34} {v:9.3f}V {v:18.3f}V")
    v_once = b1(ESKI_R_SERI, bosalt=ACIK)["v(ray)"]
    v_sonra = b1(YENI_R_SERI, bosalt=BOSALTMA_R)["v(ray)"]
    r.kosul("  6c: B18 LDO'ya binen ters gerilimi de yariya indiriyor",
            v_sonra < 0.6 * v_once,
            f"{v_once:.3f} V -> {v_sonra:.3f} V — bu, aranmamis ama "
            f"kazanilmis bir yan fayda")
    r.bilgi("")
    r.bilgi("     ⚠ ACIK KALAN: LDO'nun govde diyodu 1.67 V'ta bile iletir mi")
    r.bilgi("       (modulun LDO tipi bilinmiyor). Kesin cozum ayni kural:")
    r.bilgi("       ONCE USB, SONRA 24 V.")

    alt(r, "6d · 🔴 ESP32-S3 veri sayfasi PIN SINIRI YAYINLAMIYOR")
    r.bilgi("     Arastirmanin en rahatsiz edici bulgusu: ESP32-S3 veri")
    r.bilgi("     sayfasi Tablo 14 (Absolute Maximum Ratings) yalnizca")
    r.bilgi("     BESLEME pinini (-0.3 .. 3.6 V), toplam IO cikis akimini ve")
    r.bilgi("     saklama sicakligini veriyor. HICBIR pin icin mutlak azami")
    r.bilgi("     GIRIS GERILIMI ve HICBIR pin icin enjeksiyon akimi siniri")
    r.bilgi("     YOK. Elimizdeki tek sinir 'Recommended Operating")
    r.bilgi("     Conditions'taki V_IH maks = VDD + 0.3 V.")
    r.bilgi("")
    r.bilgi("     Karsilastirma: ST, STM32 icin hem VDD=0'da azami pin")
    r.bilgi("     gerilimini hem enjeksiyon akimini yayinliyor ve ADC'si")
    r.bilgi("     ETKIN pinlerde enjeksiyonu ACIKCA YASAKLIYOR ('parazitik")
    r.bilgi("     diyotlar bu akimi tasiyamaz').")
    r.bilgi("")
    r.kosul("  6d: bu yuzden 4f'teki 'sinir asiliyor' ifadesi TAVSIYE EDILEN "
            "KOSUL asimidir, mutlak azami asimi DEGIL",
            T.ESP_GPIO_VDD_PAYI == 0.3,
            "VDD+0.3 bir 'recommended operating condition'; ESP32-S3 icin "
            "yayinlanmis bir mutlak azami giris gerilimi YOK — yani asimin "
            "ne kadar tehlikeli oldugu BELGELENEMIYOR")

    alt(r, "6e · 🔴 ESPRESSIF'IN ONERDIGI ADC KONDANSATORU BU KARTA KONAMAZ")
    r.bilgi("     Espressif donanim kilavuzu: 'ADC kullanirken ESP pinleri ile")
    r.bilgi("     GND arasina 0.1 uF suzgec kondansatoru ekleyin.' Dahasi,")
    r.bilgi("     veri sayfasindaki DNL/INL (+-4 / +-8 LSB) rakamlari")
    r.bilgi("     'pine 100 nF bagli' kosuluyla verilmis.")
    r.bilgi("     TI SPNA061 daha gevsek bir olcut veriyor: yuk paylasimi icin")
    r.bilgi(f"     C_ext >= (2^(N+1)-1) x C_sh = "
            f"{(2**13-1)*T.ESP_SH_C*1e9:.1f} nF.")
    r.bilgi("")
    r.bilgi("     Ama bu kartta HICBIRI KONAMAZ — bant genisligi:")
    r.bilgi(f"     {'C':>9} {ESKI_R_SERI/1e3:>9.1f}k kutup "
            f"{YENI_R_SERI/1e3:>9.1f}k kutup")
    r.bilgi("     " + "-" * 44)
    for c in (8.2e-9, 10e-9, 100e-9):
        r.bilgi(f"     {c*1e9:7.1f}nF "
                f"{1/(2*math.pi*ESKI_R_SERI*c)/1e3:12.2f} kHz "
                f"{1/(2*math.pi*YENI_R_SERI*c)/1e3:12.2f} kHz")
    r.bilgi(f"     Sallen-Key bandi: {T.SK_F0/1e3:.2f} kHz")
    en_gevsek = 1 / (2 * math.pi * ESKI_R_SERI * 8.2e-9)
    r.kosul("  6e: en gevsek oneri bile Sallen-Key bandinin ALTINDA kaliyor",
            en_gevsek < T.SK_F0,
            f"{en_gevsek/1e3:.2f} kHz < {T.SK_F0/1e3:.2f} kHz — yani hizli "
            f"yol, Espressif'in KARAKTERIZE ETTIGI kosulda CALISAMAZ")
    r.bilgi("")
    r.bilgi("     -> Bu, 4b'deki acik kalemin GERCEK sebebi: standart cozum")
    r.bilgi("        (pine kondansator) bu kartin 16.5 kHz'lik hedefiyle")
    r.bilgi("        CELISIYOR. ESP32 ADC'siyle 16.5 kHz istemenin bedeli bu.")
    r.bilgi("        Karar: bant genisligi korunuyor, oturma belirsizligi")
    r.bilgi("        TEZGAHTA olculecek (4b'deki test).")
    r.bilgi("")
    r.bilgi("     ⚠ Ayrica: eger o kondansator ILERIDE eklenirse V ve I")
    r.bilgi("       kanallarina AYNI R ve AYNI C konmali — B16'nin V/I faz")
    r.bilgi("       esitligi aksi halde bozulur. 100 nF + 10K = 159 Hz kutup,")
    r.bilgi("       50 Hz'te 17 derece faz. Bu tuzak B16'nin tekrari olurdu.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 7 — MALZEME VE OZET
# ═══════════════════════════════════════════════════════════════════════

def bolum7(r, sonuc):
    bolum(r, "BOLUM 7 — MALZEME VE OZET")
    r.bilgi(f"  {'parca':<24} {'eski':>8} {'yeni':>8}  envanter")
    r.bilgi("  " + "-" * 62)
    r.bilgi(f"  {'R26 (skop kelepcesi)':<24} {'2.7K':>8} {'10K':>8}  "
            f"R032/R033 (1/2W, 1W) x10")
    r.bilgi(f"  {'R33 (hizli yol kelepcesi)':<24} {'2.7K':>8} {'10K':>8}  "
            f"ayni")
    r.bilgi(f"  {'R41 (YENI, bosaltma)':<24} {'-':>8} {'1K':>8}  "
            f"R029/R030/R031 x10")
    r.bilgi("")
    r.bilgi("  Satin alma YOK. 2.7K'lar bosa cikiyor (baska yerde kullanilir).")

    alt(r, "OZET")
    bug = sonuc["bugun (2.7K, kelepce +3V3)"]
    f6 = sonuc["F6 tam (kelepceler TL_RAY'e)"]
    sec = sonuc["10K + 1K bosaltma   <= SECILEN"]
    r.bilgi(f"  {'olcut':<34} {'bugun':>10} {'F6':>10} {'B18/F12':>10}")
    r.bilgi("  " + "-" * 68)
    r.bilgi(f"  {'B1 payi (TL431 var)':<34} {bug[0]['pay']:9.0f}mV "
            f"{f6[0]['pay']:9.0f}mV {sec[0]['pay']:9.0f}mV")
    r.bilgi(f"  {'B1 payi (TL431 acik devre)':<34} "
            f"{'OLUR':>10} {'OLUR':>10} {sec[1]['pay']:9.0f}mV")
    r.bilgi(f"  {'skop menzili':<34} {bug[2]:9.1f}V {f6[2]:9.1f}V "
            f"{sec[2]:9.1f}V")
    r.bilgi(f"  {'hizli akim tam olcek':<34} {bug[3]*1e3:9.1f}mV "
            f"{f6[3]*1e3:9.1f}mV {sec[3]*1e3:9.1f}mV")
    r.bilgi("")
    r.bilgi("  ACIK KALAN: yok. B18/F12 hem B1'i hem TL431 kalintisini")
    r.bilgi("  kapatiyor ve hicbir menzili kismiyor.")
    r.bilgi("")
    r.bilgi("  YINE DE KUTU KURALINA EKLENMELI (bedava, ikinci savunma):")
    r.bilgi("    'Once USB, sonra 24 V. Kapatirken once 24 V.'")


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B18 — GPIO KELEPCELERI VE +3V3 GERI BESLEMESI")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI sinar, kurulmus bir KARTI degil.")
    bolum0(r)
    sonuc = bolum1(r)
    bolum2(r)
    bolum3(r)
    bolum4(r)
    bolum5(r)
    bolum6(r)
    bolum7(r, sonuc)
    # F6 OLCULDU ve REDDEDILDI; yerine gecen R26/R33 + R41 duzeni
    # yalnizca simulasyonda dogrulandi.
    tezgah("B18 GPIO kelepceleri", [
        ("[!] +3V3 rayinin GERI BESLENMESI",
         "En kritik olcum. USB'yi CIKAR, 24 V kaynagi TAKILI birak, "
         "+3V3 rayini voltmetreyle oku. 3.60 V'u asarsa ESP32 mutlak "
         "maksimumu asilmis demektir — hesap 3.582 V, pay 18 mV"),
        ("Acma SIRASI her iki yonde de guvenli mi",
         "Yukaridaki olcumu iki sirayla da yap: once USB sonra 24 V, "
         "sonra tersi. Ikisi de gecmezse talimat degil DEVRE degisecek"),
        ("R41'in gercek degeri ve isinmasi",
         "Geri besleme akimini sinirlayan parca. Olcum: devreden cikarip "
         "ohmmetre, sonra hata halinde 10 dk isinma"),
    ])
    return 0 if r.yazdir() else 1


if __name__ == "__main__":
    raise SystemExit(main())
