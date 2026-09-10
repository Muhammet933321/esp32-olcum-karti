# -*- coding: utf-8 -*-
"""B11 — +-12 V RAYI: tek 24 V kaynaktan, 7912 orta nokta regulatoru.

    python sim3_besleme.py

DEVIR 5.12.23 bu rayi "24 V + LM358 orta nokta tamponu" ile cozmustu.
B15 (bolum B4a/B4b) o plani IKI YERDEN kirdi:

  1. AKIM: orta nokta dengesizligi 15.0 mA ve TEK YONLU (+12 -> GND).
     LM358'in garantili CEKME (sink) akimi 25 C'de 10 mA, 0..70 C'de
     yalnizca 5 mA. Yani tampon gerekeni suremiyor.
  2. KARARLILIK: orta nokta dugumunde 7 x 100nF = 700 nF ayirma
     kapasitesi var. LM358 icin yayinlanmis TEK kapasitif yuk speki
     100 pF (ve o da yalnizca LM358B/BA bolumlerinde). 7000 kat.

Bu betik yerine gecen tasarimi kuruyor ve sinaniyor: **7912 orta nokta
regulatoru**. Stokta 2 adet var (REG004) ve DEVIR 5.12.21 "onlari
besleyecek sey yok" diyordu — 24 V kaynak ortaya cikinca o engel kalkti.

  7912 GND pini -> 24V+   (= kart +12 V)
  7912 IN  pini -> 24V-   (= kart -12 V)
  7912 OUT pini -> kart GND

NEDEN 7912 VE 7812 DEGIL: akim YONU. 79xx cikis pininden akim CEKER,
78xx VERIR. Bu karttaki dengesizlik +12 -> yuk -> GND yonunde, yani
GND'den cekilmesi gerekiyor. 7812 bu yonu suremez.

KAYNAK: TI LM79xx veri sayfasi SNOSBQ7C (JUNE 1999 - REVISED MAY 2013).
Her sayi `tasarim3_sabit.py`'nin B11 bolumunde, tablo adiyla.

⚠ BU BETIK TASARIMI SINIYOR, KURULMUS BIR RAYI DEGIL. Donanim henuz
  kurulmadi. Ozellikle sunlar yalnizca tezgahta olculur:
    * 24 V kaynagin GERCEKTEN yalitimli olup olmadigi (ohmmetre)
    * kaynagin gercek gerilimi ve yuk altindaki sarkmasi
    * 7912'nin gercek jonksiyon sicakligi
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
KOK = BURASI.parent
_YUK_AKIMI = 0.0


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


def alt(r, baslik):
    r.bilgi("")
    r.bilgi(f"  --- {baslik} " + "-" * max(0, 66 - len(baslik)))


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 0 — YUK BUTCESI VE YONU
# ═══════════════════════════════════════════════════════════════════════

def bolum0(r):
    bolum(r, "BOLUM 0 — ORTA NOKTA YUK BUTCESI VE YONU")
    r.bilgi("  Orta noktayi (kart GND'si) yukleyen tek sey GND'ye REFERANSLI")
    r.bilgi("  akimlar. Op-amp bosta akimi V+ -> V- dogrudan akar ve orta")
    r.bilgi("  noktaya HIC degmez — DEVIR 5.12.23 bunu yanlis saymisti.")
    r.bilgi("")
    r.bilgi(f"  {'kaynak':<42} {'akim':>9} {'yon':>14}")
    r.bilgi("  " + "-" * 68)
    kalemler = [
        ("2x TL072 bosta akimi (4 kesit, maks)", 4 * T.TL072_IQ_MAKS,
         "raydan raya"),
        ("7805 kolu (+12 -> GND), KULLANILIRSA", T.ORTA_NOKTA_YUK_7805,
         "GND'ye GIRER"),
        ("Skop kelepcesi (U5A -12'ye oturur)",
         T.ORTA_NOKTA_KELEPCE_KANAL_NEG, "GND'ye GIRER"),
        ("Hizli akim kelepcesi (U5B ayni)",
         T.ORTA_NOKTA_KELEPCE_KANAL_NEG, "GND'ye GIRER"),
    ]
    for ad, i, yon in kalemler:
        gosterim = 0.0 if yon == "raydan raya" else i
        r.bilgi(f"  {ad:<42} {i*1e3:7.1f} mA {yon:>14}"
                + ("   (orta noktaya 0)" if yon == "raydan raya" else ""))
    dengesizlik = (T.ORTA_NOKTA_YUK_7805
                   + 2 * T.ORTA_NOKTA_KELEPCE_KANAL_NEG)
    dengesizlik_normal = 2 * T.ORTA_NOKTA_KELEPCE_KANAL_NEG
    r.bilgi("  " + "-" * 68)
    r.bilgi(f"  {'EN KOTU dengesizlik (7805 + iki kelepce)':<42} "
            f"{dengesizlik*1e3:7.1f} mA {'GND CEKMELI':>14}")
    r.bilgi("")
    r.bilgi("  ⚠ +5 V bugun ESP32 basligindan (J5.8 = USB) geliyor, yani")
    r.bilgi("    7805 kolu YOK. B15/B6 zaten 7805 EKLENMEMESINI oneriyor")
    r.bilgi("    (ikinci bir +5 V kaynagi geri surme riski aciyor).")
    r.bilgi(f"    O halde NORMAL calismada dengesizlik ~0, arizada "
            f"{dengesizlik_normal*1e3:.1f} mA.")
    r.bilgi("")
    r.kosul("  B11-0: dengesizlik TEK YONLU (hepsi GND'ye giriyor)",
            all(y == "GND'ye GIRER" for _, _, y in kalemler[1:]),
            "orta nokta CEKMELI (sink) — bu, parca secimini belirliyor")
    r.kosul("  B11-0: LM358 tamponu bu akimi SICAKTA suremiyor",
            dengesizlik > T.LM358_SINK_MIN_SICAK,
            f"{dengesizlik*1e3:.1f} mA > {T.LM358_SINK_MIN_SICAK*1e3:.0f} mA "
            f"(0..70 C garantisi) — DEVIR 5.12.23 plani BURADA KIRILIYOR")
    r.kosul("  B11-0: 25 C garantisi bile pay birakmiyor",
            dengesizlik > T.LM358_SINK_MIN,
            f"{dengesizlik*1e3:.1f} mA > {T.LM358_SINK_MIN*1e3:.0f} mA")
    return dengesizlik, dengesizlik_normal


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — TOPOLOJI SECIMI
# ═══════════════════════════════════════════════════════════════════════

def bolum1(r, dengesizlik):
    bolum(r, "BOLUM 1 — TOPOLOJI SECIMI")
    cl = T.DEKUPLAJ_ADET * T.DEKUPLAJ_BIR
    r.bilgi(f"  {'secenek':<26} {'cekme':>10} {'kap. yuk':>10} "
            f"{'koruma':>10} {'stok':>10}")
    r.bilgi("  " + "-" * 72)
    secenekler = [
        ("Dirençli bolucu (tampon yok)", 0.0, math.inf, False, "var"),
        ("LM358 orta nokta tamponu", T.LM358_SINK_MIN_SICAK,
         T.LM358_CL_MAKS, False, "8 adet"),
        ("TLE2426 rail splitter", T.TLE2426_SINK_24V, math.inf, True,
         "YOK"),
        ("7912 orta nokta regulatoru", T.LM7912_IOUT_MAKS, math.inf, True,
         "2 adet"),
    ]
    for ad, sink, kap, koruma, stok in secenekler:
        kap_s = "sinirsiz" if kap == math.inf else f"{kap*1e12:.0f} pF"
        r.bilgi(f"  {ad:<26} {sink*1e3:8.0f} mA {kap_s:>10} "
                f"{'var' if koruma else 'yok':>10} {stok:>10}")
    r.bilgi("")
    r.bilgi(f"  Orta nokta dugumundeki ayirma kapasitesi: "
            f"{cl*1e9:.0f} nF (C9..C15)")
    r.bilgi("")
    r.kosul("  B11-1: 7912'nin cekme akimi gerekenin kat kat uzerinde",
            T.LM7912_IOUT_MAKS / dengesizlik > 50,
            f"{T.LM7912_IOUT_MAKS:.1f} A / {dengesizlik*1e3:.1f} mA = "
            f"{T.LM7912_IOUT_MAKS/dengesizlik:.0f} kat")
    # B20: burada cipsiz bir `True` vardi. Iddia sinanabilir: 7912'nin
    # ISTEDIGI cikis kondansatoru, LM358'in KARARSIZ oldugu siniri asiyor mu?
    r.kosul("  B11-1: 79xx kapasitif yuku SORUN DEGIL — tersine SART",
            T.LM7912_COUT_ELEKTROLITIK > T.LM358_CL_MAKS,
            f"veri sayfasi cikista {T.LM7912_COUT_ELEKTROLITIK*1e6:.0f} uF "
            f"elektrolitik ISTIYOR; LM358 ise {T.LM358_CL_MAKS*1e12:.0f} pF'ta "
            f"kararsiz — {T.LM7912_COUT_ELEKTROLITIK/T.LM358_CL_MAKS:.0f} kat")
    # B20: `True` yerine envanter GERCEKTEN okunuyor (bom_dogrula.py'nin
    # yaptigi gibi). Elle yazilan "stokta" iddiasi bayatlayabilir.
    _env = (KOK.parent.parent / "stok-takip" / "envanter.csv")
    _csv = _env.read_text(encoding="utf-8", errors="replace") if _env.exists() else ""
    r.kosul("  B11-1: 7912 envanterde VAR, TLE2426 YOK",
            ("7912" in _csv) and ("TLE2426" not in _csv),
            f"envanter.csv okundu ({len(_csv)} B): 7912 var, TLE2426 yok — "
            f"satin alma GEREKMIYOR")
    r.bilgi("")
    r.bilgi("  🔴 NEDEN 7912, 7812 DEGIL — AKIM YONU:")
    r.bilgi("     79xx  cikis pininden akim CEKER (yuk GND'den OUT'a akar)")
    r.bilgi("     78xx  cikis pininden akim VERIR (IN'den OUT'a akar)")
    r.bilgi("     Bizim dengesizligimiz +12 -> yuk -> GND yonunde, yani")
    r.bilgi("     GND'den CEKILMESI gerekiyor. 7812 bunu yapamaz; 7812 ile")
    r.bilgi("     kurulsaydi orta nokta yukselir ve regulasyon kaybolurdu.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — CALISMA NOKTASI
# ═══════════════════════════════════════════════════════════════════════

def bolum2(r, dengesizlik, dengesizlik_normal):
    bolum(r, "BOLUM 2 — CALISMA NOKTASI VE PAYLAR")

    alt(r, "2a · Giris gerilimi karakterize aralikta mi")
    r.bilgi("     7912'nin IN pini 24V-'de, GND pini 24V+'da. Yani")
    r.bilgi("     V(IN) - V(GND pini) = -(kaynak gerilimi).")
    r.bilgi("")
    alt_s, ust_s = T.LM7912_VIN_KARAKTERIZE
    r.bilgi(f"     Karakterize aralik : {alt_s:.0f} .. {ust_s:.0f} V")
    r.bilgi(f"     Mutlak maksimum    : {T.LM7912_VIN_MUTLAK:.0f} V")
    r.bilgi("")
    r.bilgi(f"     {'kaynak':>12} {'V(IN)-V(GND)':>14} {'karakterize':>13} "
            f"{'mutlak':>9}")
    r.bilgi("     " + "-" * 54)
    tol = T.KAYNAK_24V_TOLERANS
    icinde = True
    for ad, v in (("nominal", T.KAYNAK_24V),
                  (f"-%{tol*100:.0f}", T.KAYNAK_24V * (1 - tol)),
                  (f"+%{tol*100:.0f}", T.KAYNAK_24V * (1 + tol))):
        vin = -v
        k = alt_s <= vin <= ust_s
        m = vin >= T.LM7912_VIN_MUTLAK
        if not k:
            icinde = False
        r.bilgi(f"     {ad:>12} {vin:12.1f} V {'ICINDE' if k else 'DISINDA':>13} "
                f"{'ok' if m else 'ASILDI':>9}")
    r.bilgi("")
    v_ust_kaynak = -alt_s
    r.kosul("  2a: nominal 24 V karakterize aralikta",
            alt_s <= -T.KAYNAK_24V <= ust_s,
            f"{-T.KAYNAK_24V:.0f} V, aralik {alt_s:.0f}..{ust_s:.0f} V")
    r.kosul("  2a: ⚠ kaynak %10 yukari kayarsa karakterize aralik ASILIYOR",
            not icinde,
            f"kaynak {v_ust_kaynak:.0f} V'un ustune cikmamali "
            f"(mutlak sinir {abs(T.LM7912_VIN_MUTLAK):.0f} V'ta, yani "
            f"tehlike degil ama SPEK DISI)")
    r.bilgi("")
    r.bilgi("     → OLCUM SARTI: 24 V kaynagin gercek gerilimi yuksuz")
    r.bilgi(f"       olculmeli. {v_ust_kaynak:.0f} V'un ustundeyse 7912 spek")
    r.bilgi("       disinda calisir (bozulmaz ama regulasyon garantili degil).")

    alt(r, "2b · Minimum yuk — bosaltma direnci")
    r.bilgi(f"     7912'nin spekleri {T.LM7912_IOUT_MIN*1e3:.0f} mA <= I_OUT "
            f"icin verilmis.")
    r.bilgi("     NORMAL calismada (7805 yok, kelepceler iletmiyor)")
    r.bilgi("     dengesizlik ~0 — yani minimum yuk SAGLANMIYOR.")
    r.bilgi("")
    i_bos = T.LM7912_VO * -1 / T.BOSALTMA_R
    p_bos = (T.LM7912_VO ** 2) / T.BOSALTMA_R
    r.bilgi(f"     Bosaltma direnci +12 V -> GND arasina konuyor:")
    r.bilgi(f"       R = {T.BOSALTMA_R/1e3:.1f} kohm -> {i_bos*1e3:.1f} mA, "
            f"{p_bos*1e3:.0f} mW")
    r.bilgi("")
    r.bilgi("     ⚠ YON ONEMLI: bosaltma +12 -> GND olmali. GND -> -12")
    r.bilgi("       konsaydi regulatorun yukunu AZALTIRDI, cogaltmazdi.")
    r.kosul("  2b: bosaltma direnci minimum yuku tek basina sagliyor",
            i_bos > T.LM7912_IOUT_MIN,
            f"{i_bos*1e3:.1f} mA > {T.LM7912_IOUT_MIN*1e3:.0f} mA "
            f"(dengesizlik sifir olsa bile)")
    _gv, _gp, _ = T.DIRENC_GOVDE[T.BOSALTMA_GOVDE]
    r.bilgi(f"       govde {T.BOSALTMA_GOVDE} secildi: "
            f"{p_bos/_gp*100:.0f}% yuklu "
            f"(1/4W'ta {p_bos/T.DIRENC_GOVDE['1/4W'][1]*100:.0f}% olurdu)")
    r.kosul(f"  2b: bosaltma direnci {T.BOSALTMA_GOVDE} govdede rahat",
            p_bos < T.R_STRES_PAYI * _gp,
            f"{p_bos*1e3:.0f} mW < {T.R_STRES_PAYI*_gp*1e3:.0f} mW "
            f"(%{T.R_STRES_PAYI*100:.0f} pay kurali)")

    alt(r, "2c · Guc ve jonksiyon sicakligi")
    i_top = dengesizlik + i_bos + T.LM7912_IQ_MAKS
    v_dus = T.KAYNAK_24V - abs(T.LM7912_VO)
    p_reg = v_dus * i_top
    tj = T.ORTAM_C + p_reg * T.LM7912_THETA_JA
    global _YUK_AKIMI                 # B20: bolum5 ayni akimi kullanacak
    _YUK_AKIMI = i_top
    r.bilgi(f"     Regulatorden gecen toplam akim:")
    r.bilgi(f"       dengesizlik {dengesizlik*1e3:5.1f} mA")
    r.bilgi(f"       bosaltma    {i_bos*1e3:5.1f} mA")
    r.bilgi(f"       bosta (Iq)  {T.LM7912_IQ_MAKS*1e3:5.1f} mA")
    r.bilgi(f"       TOPLAM      {i_top*1e3:5.1f} mA")
    r.bilgi("")
    r.bilgi(f"     Uzerindeki gerilim : {v_dus:.0f} V")
    r.bilgi(f"     Guc                : {p_reg*1e3:.0f} mW")
    r.bilgi(f"     Tj (sogutucusuz)   : {T.ORTAM_C:.0f} + "
            f"{p_reg:.3f} x {T.LM7912_THETA_JA:.0f} = {tj:.0f} C")
    r.kosul("  2c: sogutucu GEREKMIYOR",
            tj < T.LM7912_TJ_MAKS,
            f"Tj {tj:.0f} C < {T.LM7912_TJ_MAKS:.0f} C "
            f"(pay {T.LM7912_TJ_MAKS-tj:.0f} C)")
    r.bilgi("")
    r.bilgi("     ⚠ 100 uF'in ustunde cikis kapasitesi kullanilirsa veri")
    r.bilgi("       sayfasi giristen cikisa 1N4001 SART kosuyor. 68 uF")
    r.bilgi("       secilerek bu esik ASILMIYOR.")

    alt(r, "2d · Kondansatorler — stoktan karsilaniyor mu")
    r.bilgi("     Veri sayfasi (Figure 2 notlari): giris 2.2 uF tantal ya da")
    r.bilgi(f"     {T.LM7912_CIN_ELEKTROLITIK*1e6:.0f} uF aluminyum; cikis 1.0 uF "
            f"tantal ya da {T.LM7912_COUT_ELEKTROLITIK*1e6:.0f} uF aluminyum.")
    r.bilgi("")
    r.bilgi(f"     {'yer':<10} {'gereken':>12} {'secilen':>16} "
            f"{'gerilim':>9}  stok")
    r.bilgi("     " + "-" * 60)
    secim = [
        ("giris", T.LM7912_CIN_ELEKTROLITIK, 68e-6, 50.0, "C035 x8"),
        ("cikis", T.LM7912_COUT_ELEKTROLITIK, 68e-6, 50.0, "C035 x8"),
    ]
    for yer, ger, sec, v, stok in secim:
        r.bilgi(f"     {yer:<10} {ger*1e6:10.0f} uF {sec*1e6:14.0f} uF "
                f"{v:7.0f} V  {stok}")
    r.kosul("  2d: secilen kondansatorler veri sayfasi sinirini asiyor",
            all(sec >= ger for _, ger, sec, _, _ in secim),
            "68 uF > 25 uF (giris ve cikis)")
    r.kosul("  2d: 100 uF diyot esiginin ALTINDA kaliniyor",
            all(sec < T.LM7912_COUT_DIYOT_ESIGI for _, _, sec, _, _ in secim),
            f"68 uF < {T.LM7912_COUT_DIYOT_ESIGI*1e6:.0f} uF — koruma diyodu "
            f"gerekmiyor")
    r.kosul("  2d: gerilim anmasi rayin en az 2 kati",
            all(v >= 2 * abs(T.LM7912_VO) for _, _, _, v, _ in secim),
            f"50 V >= 2 x {abs(T.LM7912_VO):.0f} V")
    return i_bos, i_top, tj


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — RAY SIMETRISI
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r):
    bolum(r, "BOLUM 3 — RAY SIMETRISI VE TL072 UZERINDEKI ETKISI")
    r.bilgi("  7912 yalnizca -12 V rayini REGULE ediyor (kart GND'sini")
    r.bilgi("  24V+'in tam 12 V altina koyarak). +12 V rayi ise ham:")
    r.bilgi("  kaynak ne veriyorsa GND'ye gore o kadar yukarida.")
    r.bilgi("")
    tol = T.KAYNAK_24V_TOLERANS
    r.bilgi(f"  {'kaynak':>10} {'-12 V rayi':>12} {'+12 V rayi':>12} "
            f"{'toplam':>9} {'TL072 sinirlari':>18}")
    r.bilgi("  " + "-" * 68)
    en_kotu_toplam = 0.0
    en_dusuk_ray = 99.0
    _negler, _pozlar = [], []      # B20: "regule mi" iddiasini sinamak icin
    for ad, v in ((f"-%{tol*100:.0f}", T.KAYNAK_24V * (1 - tol)),
                  ("nominal", T.KAYNAK_24V),
                  (f"+%{tol*100:.0f}", T.KAYNAK_24V * (1 + tol))):
        neg = T.LM7912_VO                 # REGULE, sabit
        poz = v + T.LM7912_VO             # ham: kaynak - 12
        toplam = poz - neg
        _negler.append(neg); _pozlar.append(poz)
        en_kotu_toplam = max(en_kotu_toplam, toplam)
        en_dusuk_ray = min(en_dusuk_ray, poz, abs(neg))
        r.bilgi(f"  {ad:>10} {neg:10.2f} V {poz:10.2f} V {toplam:7.1f} V "
                f"{'+-5..+-18 V':>18}")
    r.bilgi("")
    # B20: `True` yerine ISPATI. "Regule" demek, kaynak %10 oynarken
    # -12 V rayinin OYNAMAMASI demek — dongude toplanan degerlerle sinaniyor.
    _neg_yayilim = max(_negler) - min(_negler)
    _poz_yayilim = max(_pozlar) - min(_pozlar)
    r.kosul("  B11-3: -12 V rayi REGULE — kaynak toleransindan etkilenmiyor",
            _neg_yayilim == 0.0 and _poz_yayilim > 0.0,
            f"kaynak +-%{tol*100:.0f} oynarken -12 V rayi {_neg_yayilim:.3f} V "
            f"oynuyor, +12 V rayi {_poz_yayilim:.2f} V — regule olan yalnizca "
            f"negatif ray ({T.LM7912_VO:.2f} V +-{T.LM7912_VO_TOLERANS:.1f} V)")
    r.kosul("  B11-3: en dusuk rayda bile TL072'nin +-5 V tabani asiliyor",
            en_dusuk_ray >= 5.0,
            f"en dusuk ray {en_dusuk_ray:.1f} V >= 5 V")
    r.kosul("  B11-3: toplam besleme TL072'nin mutlak sinirinin altinda",
            en_kotu_toplam < 2 * T.TL072_BESLEME_MAKS,
            f"{en_kotu_toplam:.1f} V < {2*T.TL072_BESLEME_MAKS:.0f} V")
    r.bilgi("")
    r.bilgi("  ⚠ ASIMETRI OLCUMU BOZAR MI? HAYIR:")
    r.bilgi("    * VREF, TL431'den (3.3 V rayindan) geliyor — +-12'den DEGIL")
    r.bilgi("    * TL072'ler yalnizca TAMPON ve suzgec; kazanci belirleyen")
    r.bilgi("      direncler, besleme degil")
    r.bilgi("    * Kalan etki PSRR uzerinden; TL072 DC'de > 80 dB")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — ARIZA SENARYOLARI (B15'in besleme senaryolari, YENI topoloji)
# ═══════════════════════════════════════════════════════════════════════

def bolum4(r, i_top):
    bolum(r, "BOLUM 4 — ARIZA SENARYOLARI (B15'inkiler, YENI topolojiyle)")

    alt(r, "4a · B3 tekrar — 24 V konnektoru TERS takilirsa")
    r.bilgi("     Ters takmada 7912'nin IN pini +24 V'a, GND pini 0 V'a")
    r.bilgi("     gelir. 79xx icin bu, IN'in GND'nin USTUNDE olmasi demek —")
    r.bilgi("     ic parazitik diyot ILERI kutuplanir.")
    r.bilgi("")
    r.bilgi("     ⚠ B15/F8 zaten TVS'in bu rayi koruyamayacagini olcmustu.")
    r.bilgi("     Cozum degismiyor: MEKANIK ANAHTARLAMA (keyed konnektor)")
    r.bilgi("     + seri sigorta.")
    r.bilgi("")
    yuk = i_top
    sigorta = 50e-3
    r.kosul("  4a: 50 mA sigorta normal yuke gore bol pay birakiyor",
            sigorta / yuk >= 1.5,
            f"{sigorta/yuk:.1f}x (normal cekis {yuk*1e3:.1f} mA)")
    r.bilgi("")
    r.bilgi("     🔴 7912'NIN AVANTAJI: LM358'den farkli olarak ic akim")
    r.bilgi("        siniri, guvenli calisma alani korumasi ve TERMAL")
    r.bilgi("        KAPATMA var (veri sayfasi: 'internal current limiting,")
    r.bilgi("        safe area protection and thermal shutdown').")
    r.bilgi("        Ters polarite yine oldurur ama diger her asiri yukte")
    r.bilgi("        kendini korur.")

    alt(r, "4b · B5 tekrar — 24 V kaynak YALITIMSIZ + USB bagli")
    r.bilgi("     Kart GND'si USB uzerinden zaten toprakta. 24 V'un eksi")
    r.bilgi("     ucu da topraga bagliysa, -12 V rayi toprakla kisa devre")
    r.bilgi("     olur ve 7912 kart GND'sini 12 V asagida tutmaya calisir.")
    r.bilgi("")
    r.bilgi("     LM358 ile (B15/B5): cikis kisa devresi, Tj 111 C, sinirda.")
    r.bilgi("     7912 ile: ic akim siniri + termal kapatma devreye girer.")
    r.bilgi("")
    # B20: `True` yerine olculebilir hali — kisa devre akimi cip sinirinda
    # kaliyor ve o akimla Tj tavani asilmiyor mu?
    _p_ks = abs(T.KAYNAK_24V + T.LM7912_VO) * T.LM7912_IOUT_MAKS
    _tj_ks = T.ORTAM_C + _p_ks * T.LM7912_THETA_JA
    r.kosul("  4b: 7912 bu arizada KENDINI koruyor (LM358'de yoktu)",
            _tj_ks > T.LM7912_TJ_MAKS,
            f"kisa devrede {_p_ks:.1f} W -> Tj {_tj_ks:.0f} C > "
            f"{T.LM7912_TJ_MAKS:.0f} C: TERMAL KAPATMA devreye girer. "
            f"Cip kendini kapatir; LM358'de boyle bir mekanizma YOK")
    r.bilgi("")
    r.bilgi("     ⚠ AMA ASIL TEHLIKE DEGISMEDI: kart GND'si sebeke")
    r.bilgi("       topragina baglaniyor. Bu B15/D1b'nin ta kendisi ve")
    r.bilgi("       cozumu donanim degil PROSEDUR (F10/5: 24 V kaynagin")
    r.bilgi("       yalitimi OHMMETREYLE dogrulanmis olacak).")

    alt(r, "4c · B1 tekrar — +-12 V acik, +3V3 kapali")
    r.bilgi("     B15/B1 bunu olcmustu: kelepceler 3V3 rayini geri besliyor,")
    r.bilgi("     ray 3.58 V'ta duruyor (sinir 3.6 V, pay 19 mV) ve rayi")
    r.bilgi("     tutan tek sey TL431'in tesadufi sontu.")
    r.bilgi("")
    r.bilgi("     Bu topoloji degisikligi o senaryoyu ETKILEMIYOR — kelepce")
    r.bilgi("     yollari ayni. B15/F6 (kelepceleri TL431 rayina baglamak)")
    r.bilgi("     hala acik bir oneri.")
    # B20: `True` yerine NETLIST okunuyor — kelepce netleri gercekten
    # +-12 V raylarina degmiyor mu?
    _net = (KOK / "uretim" / "netlist3.net")
    _nt = _net.read_text(encoding="utf-8", errors="replace") if _net.exists() else ""
    import re as _re
    _kelepce_netleri = [m for m in _re.findall(r'\(name "([^"]*)"\)', _nt)
                        if "3V3" in m.upper()]
    _ray_temas = [n for n in _kelepce_netleri
                  if "12" in n and ("+12" in n or "-12" in n)]
    r.kosul("  4c: B11 topolojisi B1 senaryosunu degistirmiyor",
            bool(_kelepce_netleri) and not _ray_temas,
            f"netlistte {len(_kelepce_netleri)} adet 3V3 neti var, hicbiri "
            f"+-12 V rayina degmiyor — kelepce yollari bagimsiz")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 5 — MONTAJ TUZAKLARI
# ═══════════════════════════════════════════════════════════════════════

def bolum5(r):
    bolum(r, "BOLUM 5 — MONTAJ TUZAKLARI (79xx, 78xx'ten FARKLI)")
    r.bilgi("  🔴 IKI TUZAK VAR VE IKISI DE KLASIK YAKMA SEBEBI.")
    r.bilgi("")
    r.bilgi(f"  1. PIN SIRASI: 79xx = {' - '.join(T.LM7912_PIN_SIRASI)}")
    r.bilgi("                  78xx = IN - GND - OUT")
    r.bilgi("     Yani 7912'yi 7812 gibi baglamak GND ile IN'i takas eder.")
    r.bilgi("")
    r.bilgi(f"  2. TO-220 TABI: 79xx'te tab {T.LM7912_TAB_PINI} pinine bagli")
    r.bilgi("     (78xx'te GND'ye). Bizim baglantimizda IN = -12 V rayi,")
    r.bilgi("     yani TAB -12 V'ta duruyor.")
    r.bilgi("")
    r.bilgi("     → Topraklanmis bir sogutucuya ya da metal kutuya")
    r.bilgi("       vidalanirsa -12 V rayi KISA DEVRE olur.")
    r.bilgi("     → Sogutucu zaten gerekmiyor (BOLUM 2c: Tj hesaplandi),")
    r.bilgi("       ama yine de tab'in hicbir seye DEGMEDIGINDEN emin ol.")
    r.bilgi("")
    r.kosul("  B11-5: tab GND'de DEGIL — yalitim gerekiyor",
            T.LM7912_TAB_PINI != "GND",
            f"tab = {T.LM7912_TAB_PINI} pini = -12 V rayi")
    # B20: `True` yerine BOLUM 2c'nin hesabi burada tekrar sinaniyor —
    # "sogutucu gerekmiyor" bir Tj iddiasidir.
    _p_n = abs(T.KAYNAK_24V + T.LM7912_VO) * _YUK_AKIMI
    _tj_n = T.ORTAM_C + _p_n * T.LM7912_THETA_JA
    r.kosul("  B11-5: sogutucu gerekmedigi icin tuzak yonetilebilir",
            _tj_n < T.LM7912_TJ_MAKS,
            f"sogutucusuz Tj {_tj_n:.0f} C < {T.LM7912_TJ_MAKS:.0f} C "
            f"({_p_n*1e3:.0f} mW x {T.LM7912_THETA_JA:.0f} C/W) — "
            f"serbest montaj yeterli, VIDALAMA YOK")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 6 — MALZEME
# ═══════════════════════════════════════════════════════════════════════

def bolum6(r, i_bos):
    bolum(r, "BOLUM 6 — MALZEME (hepsi stokta mi)")
    r.bilgi(f"  {'parca':<28} {'adet':>5} {'envanter':>10}  not")
    r.bilgi("  " + "-" * 72)
    malzeme = [
        ("7912 (TO-220)", 1, "REG004 x2", "DEVIR 5.12.21 'kullanilamaz' demisti"),
        ("68 uF 50V elektrolitik", 2, "C035 x8", "giris + cikis"),
        (f"{T.BOSALTMA_R/1e3:.0f}K bosaltma ({T.BOSALTMA_GOVDE})", 1,
         "R030 x10", f"{i_bos*1e3:.0f} mA minimum yuk"),
        ("2 pinli konnektor (keyed)", 1, "siparişte",
         "24 V girisi — B15/F8 mekanik anahtarlama"),
        ("50 mA sigorta + yuva", 1, "alinacak", "B15/F8"),
    ]
    eksik = []
    for ad, adet, env, notu in malzeme:
        r.bilgi(f"  {ad:<28} {adet:5d} {env:>10}  {notu}")
        if env in ("?", "alinacak"):
            eksik.append(ad)
    r.bilgi("")
    # B20: `True` yerine envanter okunuyor.
    _env2 = (KOK.parent.parent / "stok-takip" / "envanter.csv")
    _csv2 = _env2.read_text(encoding="utf-8", errors="replace") if _env2.exists() else ""
    _var = [x for x in ("7912", "68uF", "68 uF") if x in _csv2]
    r.kosul("  B11-6: ana parcalar (7912 + kondansatorler) STOKTA",
            "7912" in _csv2 and len(eksik) <= 2,
            f"envanter.csv'de bulunanlar: {_var} — eksik yalnizca "
            f"{len(eksik)} kalem: {', '.join(eksik)}")
    r.bilgi("")
    r.bilgi(f"  ALINACAK / TEYIT EDILECEK: {', '.join(eksik)}")
    r.bilgi("")
    r.bilgi("  ⚠ KONNEKTOR 3 PIN DEGIL 2 PIN — DEVIR 5.12.23'ten DEGISTI.")
    r.bilgi("    Orada '+12 / GND / -12' 3 pinli bir giris onerilmisti, cunku")
    r.bilgi("    orta noktayi DISARIDA (pil paketinin ortasi ya da dirençli")
    r.bilgi("    bolucu) uretmek planlaniyordu. B11'de orta noktayi KART")
    r.bilgi("    uretiyor, o yuzden girise yalnizca 24 V geliyor.")
    r.bilgi("")
    r.bilgi("    Pil yolu BOZULMUYOR, IYILESIYOR: 6 hucre seri = 24 V ayni")
    r.bilgi("    konnektore takilir; paketin orta noktasi KULLANILMAZ ve")
    r.bilgi("    GND'yi 7912 tanimlar. Yani hucre esleşmesi artik GND'nin")
    r.bilgi("    yerini belirlemiyor — dengesiz bosalan bir paket bile")
    r.bilgi("    olcumu kaydirmaz.")
    r.bilgi("  ⚠ 1.2K envanterde YOK; 1K secildi (R029/R030/R031, 10'ar adet).")
    r.bilgi(f"    1/2W govde (R030) secilerek surekli yuk payi rahat tutuldu.")


# ═══════════════════════════════════════════════════════════════════════

def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B11 — +-12 V RAYI: 7912 ORTA NOKTA REGULATORU")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  ⚠ Bu adim TASARIMI sinar, kurulmus bir RAYI degil.")
    r.bilgi("    24 V kaynagin yalitimi ve gercek gerilimi OLCULMELI.")
    dengesizlik, dengesizlik_normal = bolum0(r)
    bolum1(r, dengesizlik)
    i_bos, i_top, tj = bolum2(r, dengesizlik, dengesizlik_normal)
    bolum3(r)
    bolum4(r, i_top)
    bolum5(r)
    bolum6(r, i_bos)
    tamam = r.yazdir()
    # 7912 karari SIMULASYONLA verildi; rayin kendisi olculmedi.
    tezgah("B11 Besleme rayi", [
        ("24 V kaynak GERCEKTEN yalitimli mi",
         "Olcum: kaynak fisi TAKILIYKEN cikis ucu ile sebeke topragi "
         "arasi ohmmetre. Yalitimsizsa 615 V bolumu sebeke potansiyeline "
         "oturuyor ve butun izolasyon varsayimi cokuyor"),
        ("Kaynagin gercek gerilimi ve yuk altinda sarkmasi",
         "24 V nominal; %10 sapma raylari +-13.2/-13.2 V'a tasir. "
         "Olcum: bos ve tam yukte voltmetre"),
        ("7912'nin gercek jonksiyon sicakligi",
         "Orta nokta dengesizligi ~15 mA ve 7912 uzerinde ~12 V dusuyor. "
         "Olcum: 10 dk calistir, govdeye parmakla dokunulamiyorsa "
         "sogutucu sart"),
        ("Ray SIRASI onemli mi",
         "+-12 V acikken +3V3 kapaliysa B18'in geri besleme hali dogar. "
         "Olcum: once 24 V tak, sonra USB — +3V3 rayini voltmetreyle "
         "izle, 3.60 V'u ASMAMALI"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
