# -*- coding: utf-8 -*-
"""B15 — ARIZA VE ZORLAMA SIMULASYONU (Asama 3 on ucu).

    python sim3_ariza.py

Kullanicinin istegi (DEVIR 5.12.22): *"sistemin bastan sona olasi zorlama ve
kirilma noktalarinin hepsi test ve simule edilsin. Ters akim, ters voltaj,
yuksek voltaj — tum giris ve cikislar icin."*

Bugune kadar B2 yalnizca IKI ariza senaryosu kapsiyordu. B15 senaryo
sayisini 30'un uzerine cikariyor ve her birini SAYISALLASTIRIYOR:
kacan akim, dugum gerilimi, hangi mutlak sinir asiliyor, hangi parca gidiyor.

  BOLUM 0  Mutlak sinirlar — tablo ve kaynaklar
  BOLUM 1  Op-amp makromodeli — kendisi dogrulaniyor
  BOLUM 2  A · Giris terminallerine YANLIS SINYAL
  BOLUM 3  B · Besleme arizalari (24 V + LM358 orta nokta)
  BOLUM 4  C · Bilesen arizasi
  BOLUM 5  D · Kullanici hatasi ve sistem (izolasyon)
  BOLUM 6  OZET — ariza -> olen parca matrisi
  BOLUM 7  ONERILEN DUZELTMELER — her biri olculmus

KABUL OLCUTU (DEVIR 5.12.22):
  Hicbir TEK ariza ESP32'yi ya da PC'yi oldurmemeli. Olecek bir parca
  varsa hangisi oldugu bilinmeli ve UCUZ olmali.

⚠ BU BETIK TASARIMI SINIYOR, KURULMUS BIR KARTI DEGIL. Donanim henuz
  kurulmadi; buradaki her sayi HESAP ve SIMULASYON, tezgah olcumu DEGIL.
  Ozellikle su uc sey yalnizca tezgahta ogrenilir:
    * bir direncin asiri yukte ACIK mi KISA mi devre kaldigi
    * gercek LM358'in giris jonksiyonunun kirilma gerilimi
    * delikli plakette 615 V'ta ark ve yuzey kacagi

YONTEM: mevcut zincirin kalibi — ngspice (B2 kalibi) + kural() iddialari.
Elle yazilmis sonuc sayisi YOK; her sayi ya `tasarim3_sabit.py`'den gelen
bir veri sayfasi siniri, ya da burada hesaplanan/simule edilen bir sonuc.
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
NORMAL = T.KANALLAR[0]
HV = T.KANALLAR[1]


# ═══════════════════════════════════════════════════ SPICE yapi taslari

# ADS1115'in ICINDEKI ESD diyodu.
#
# ⚠ B2'nin modelinden BILEREK FARKLI. B2 genel bir silisyum diyot
#   (IS=1e-14) kullaniyor; o model 1 mA'de Vf = 0.655 V veriyor.
#   TI, ESD diyotlari icin verdigi TEK sayiyi "yaklasik 500 mV" olarak
#   yaziyor (kelepcelenmis pin gerilimi hesabi icin). 500 mV daha DUSUK
#   bir kelepce demek, yani daha COK akim — yani DAHA KOTUMSER.
#   IS bu noktaya oturtuldu: Vf(1 mA) = 26 mV * ln(1e-3/4e-12) = 0.500 V.
D_ESD = ".model DESD D(IS=4.0E-12 N=1.0 RS=10 CJO=2.0E-12 BV=20 IBV=1E-5)"
# BAT85 — B2 ile ayni model (Nexperia veri sayfasindan cikarilmis)
D_BAT85 = (".model DBAT85 D(IS=2.6E-7 N=1.06 RS=0.42 CJO=1.0E-11 M=0.333 "
           "VJ=0.4 BV=30 IBV=1E-5 EG=0.69 XTI=2)")
D_1N4148 = (".model D1N4148 D(IS=4.352E-9 N=1.906 BV=110 IBV=1E-4 RS=0.6458 "
            "CJO=7.048E-13 VJ=0.869 M=0.03 FC=0.5 TT=3.48E-9)")

# Yakinsama ayarlari. 4.9 Mohm'luk zincir + diyot kirilmasi + 600 V:
# varsayilan reltol ile ngspice zaman zaman "timestep too small" veriyor.
AYARLAR = (".options gmin=1e-13 reltol=1e-4 abstol=1e-13 vntol=1e-8 "
           "itl1=500 itl2=200")

# Acik devre = eleman silme DEGIL, 1 Tohm. Elemani silmek dugumu
# tamamen yuzer birakir ve ngspice "no DC path to ground" der.
ACIK = 1e12


def opamp_makro(ad: str, voh_dusum: float, vol: float, isc: float,
                giris_kelepce: str = "alt",
                aol: float = 2e4, rout: float = 100.0,
                bv: float = T.LM358_GIRIS_KIRILMA_VARSAYIMI) -> str:
    """Rayla SINIRLI, akimi SINIRLI, GIRIS JONKSIYONU olan op-amp makromodeli.

    Neden gerekli: B2'nin `IDEAL_OPAMP`'i sinirsiz kazancli bir izleyici;
    ne doyma ne giris jonksiyonu var. Ariza analizinde belirleyici olan
    tam da bunlar — "LM358'in cikisi en fazla kaca cikar" sorusu ADS'in,
    "girisi kac volt altina inebilir" sorusu da LM358'in kaderini
    belirliyor.

    tanh kullaniliyor cunku min()/max() ile kurulan sert kirpma ngspice'ta
    yakinsamiyor (denendi: "Timestep too small; trouble with node").
    tanh turevlenebilir oldugu icin Newton-Raphson rahat ilerliyor.

      cikis araligi : [V(valt)+vol, V(vust)-voh_dusum]
      cikis akimi   : kucuk sinyalde egim 1/rout, asimptotu +-isc

    Rout = 100 ohm KEYFI DEGIL, veri sayfasindan turetildi: LM358'in
    V_OH'u V+ = 30 V'ta R_L = 10 kohm'da 27 V, R_L = 2 kohm'da 26 V.
    Yani 1 V'luk dusum 10.3 mA'lik akim farkina karsilik geliyor ->
    dV/dI = 97 ohm. (Bu, tampon DOYDUGUNDA gecerli cikis empedansi;
    dogrusal bolgede geri besleme onu binlerce kat kucultuyor.)

    Yumusak kirpma ussu p=8 ile: kucuk akimda TAM dogrusal (egim 1/rout),
    buyuk akimda isc asimptotu. Saf tanh kucuk akimda da %30 hata
    yapiyordu.

    giris_kelepce:
      "alt"  LM358 gibi PNP giris kati — YALNIZCA V- ye parazitik
             jonksiyon var. Giris V+'in USTUNE cikabilir (mutlak sinir
             V- ye gore 32 V). B15'in en onemli tek bulgusu bu.
      "iki"  TL072 / CMOS gibi her iki raya kelepceli giris.
    """
    kel = f"Dsub_p valt arti DSUBS\nDsub_n valt eksi DSUBS\n"
    if giris_kelepce == "iki":
        kel += "Dust_p arti vust DSUBS\nDust_n eksi vust DSUBS\n"
    return f""".subckt {ad} arti eksi cikis vust valt
.model DSUBS D(IS=1.0E-14 N=1.0 RS=5 CJO=2.0E-12 BV={bv} IBV=1E-5)
Rin arti eksi 1T
{kel}Bmid mid 0 V = (V(vust)-{voh_dusum} + V(valt)+{vol})/2
Bspn spn 0 V = (V(vust)-{voh_dusum} - V(valt)-{vol})/2
Bic  ic 0 V = V(mid) + V(spn)*tanh( {aol}*(V(arti)-V(eksi))/max(V(spn),1m) )
Rp ic ara 1k
Cp ara 0 1n
Bout 0 cikis I = ((V(ara)-V(cikis))/{rout}) / pow(1 + pow(abs(V(ara)-V(cikis))/{isc * rout}, 8), 0.125)
Rkacak cikis 0 1G
.ends
"""


LM358 = opamp_makro("LM358", T.LM358_VOH_DUSUM, T.LM358_VOL, T.LM358_ISC)
LM358_MAKUL = opamp_makro("LM358M", T.LM358_VOH_DUSUM_MAKUL, T.LM358_VOL,
                          T.LM358_ISC)
LM358_KOTU = opamp_makro("LM358K", T.LM358_VOH_DUSUM_EN_KOTU, T.LM358_VOL,
                         T.LM358_ISC)
TL072 = opamp_makro("TL072", 1.5, 1.5, 40e-3, giris_kelepce="iki")


def op(netlist: str, etiket: str) -> dict:
    """`op` analizi kosar, `print` edilen dugum/akimlari sozluk dondurur."""
    kayit, _ = spice.kos(netlist, BURASI / f"_b15_{etiket}")
    cikti = {}
    for satir in kayit.splitlines():
        if "=" not in satir:
            continue
        sol, _, sag = satir.partition("=")
        parcalar = sol.split()
        if not parcalar:
            continue
        try:
            cikti[parcalar[-1].lower()] = float(sag.split()[0])
        except (ValueError, IndexError):
            pass
    return cikti


def tara(netlist: str, etiket: str, dosya: str = "dc.txt"):
    _, dizin = spice.kos(netlist, BURASI / f"_b15_{etiket}")
    return spice.degerler(dizin / dosya)


# ═══════════════════════════════════════════════════ rapor altyapisi

class Ariza:
    """Bir senaryonun sonucu — OZET matrisi bundan uretiliyor."""

    def __init__(self, kod, ad, olen, esp_guvende, pc_guvende, not_=""):
        self.kod, self.ad = kod, ad
        self.olen = olen                    # "" ise hicbir parca gitmiyor
        self.esp_guvende = esp_guvende
        self.pc_guvende = pc_guvende
        self.not_ = not_


ARIZALAR: list[Ariza] = []

# Bolumler arasinda tasinan OLCULMUS degerler. Betigin kendi kurali:
# "Elle yazilmis sonuc sayisi YOK" — BOLUM 7 bir sayiyi BOLUM 2'den
# aliyorsa onu buradan almali, tekrar yazmamali.
OLCUM: dict[str, float] = {}


def kaydet(kod, ad, olen, esp=True, pc=True, not_=""):
    ARIZALAR.append(Ariza(kod, ad, olen, esp, pc, not_))


# Parca fiyatlari (TL) — "olecek parca ucuz mu" olcutu icin.
# Kaynak: motorobit.com / direnc.net 2026-09 fiyatlari, DEVIR 5.12.15.
FIYAT = {
    "R4 (220K 1W)": 0.60,
    "R18 (100R)": 0.15,
    "RS (sont seti)": 20.0,
    "R20 (100K)": 0.15,
    "C2/C3 (100nF)": 0.50,
    "U3/U4 (LM358, soketli)": 8.0,
    "U5/U8 (TL072, soketli)": 15.0,
    "U6/U7 (ADS1115 modulu)": 45.0,
    "ESP32-S3 N16R8": 350.0,
    "PC anakarti": 4000.0,
}
UCUZ_ESIK = 50.0        # bunun altinda kalan bir parca "ucuz" sayiliyor


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
#  BOLUM 0 — MUTLAK SINIRLAR
# ═══════════════════════════════════════════════════════════════════════

def bolum0(r):
    bolum(r, "BOLUM 0 — MUTLAK SINIRLAR (tasarim3_sabit.py, kaynakli)")
    r.bilgi("  CALISMA siniri asilirsa OLCUM bozulur; MUTLAK sinir asilirsa")
    r.bilgi("  PARCA olur. B15 ikisini ayri raporluyor.")
    r.bilgi("")
    r.bilgi(f"  {'parca':<16} {'buyukluk':<26} {'alt':>10} {'ust':>10}")
    r.bilgi("  " + "-" * 66)
    satirlar = [
        ("ADS1115", "analog giris (mutlak)",
         T.ADS_MUTLAK_GIRIS_ALT, T.ADS_MUTLAK_GIRIS_UST, "V"),
        ("ADS1115", "analog giris (calisma)",
         T.ADS_CALISMA_ALT, T.ADS_CALISMA_UST, "V"),
        ("ADS1115", "giris akimi (surekli)",
         -T.ADS_GIRIS_AKIM_MAKS * 1e3, T.ADS_GIRIS_AKIM_MAKS * 1e3, "mA"),
        ("ESP32-S3", "GPIO / ADC pini (mutlak)",
         T.ESP_MUTLAK_PIN_ALT, T.ESP_MUTLAK_PIN_UST, "V"),
        ("LM358", "giris (V- ye gore, MUTLAK)",
         T.LM358_GIRIS_MUTLAK_ALT, T.LM358_GIRIS_MUTLAK_UST, "V"),
        ("LM358", "besleme", 0.0, T.LM358_BESLEME_MAKS, "V"),
        ("TL072", "giris (besleme +-15 V)",
         -T.TL072_GIRIS_MUTLAK, T.TL072_GIRIS_MUTLAK, "V"),
        ("TL072", "besleme", -T.TL072_BESLEME_MAKS, T.TL072_BESLEME_MAKS, "V"),
        ("BAT85", "surekli ileri akim", 0.0, T.BAT85_IF_SUREKLI * 1e3, "mA"),
    ]
    for parca, ne, a, u, birim in satirlar:
        r.bilgi(f"  {parca:<16} {ne:<26} {a:9.2f}{birim:<2} {u:9.2f}{birim}")
    r.bilgi("")
    r.bilgi("  🔴 LM358'IN GIRIS SINIRI BESLEMEDEN BAGIMSIZ — bu, B15'in")
    r.bilgi("     en onemli tek bulgusu. DEVIR 5.12.22 senaryo 1 'LM358'in")
    r.bilgi(f"     mutlak giris siniri V+ +0.3 = 5.3 V' diyordu. Veri sayfasi")
    r.bilgi(f"     boyle DEMIYOR: sinir V- ye gore {T.LM358_GIRIS_MUTLAK_UST:.0f} V ve besleme")
    r.bilgi("     5 V olsa bile gecerli (PNP giris kati, V+'ya kelepce YOK).")
    r.bilgi("     Bolum 2'de iki varsayim da simule edilip karsilastiriliyor.")
    r.bilgi("")

    # Bu bir kural degil bir denetim: sinirlar birbiriyle tutarli mi
    # ⚠ Bu kural NETLIST'i okumali; sabit tablonun kendi icinde tutarli
    #   olmasi hicbir sey kanitlamaz (tavtoloji). Semaya yeni bir direnc
    #   eklenirse ve govdesi girilmezse B15 sessizce kapsam disi kalir.
    import re as _re
    _net = (BURASI / "netlist3.net")
    if _net.exists():
        _metin = _net.read_text(encoding="utf-8", errors="replace")
        _direncler = {ref for ref, val in _re.findall(
            r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\)', _metin)
            if ref.startswith("R") and not ref.startswith("RS")}
        _eksik = sorted(_direncler - set(T.DIRENC_GOVDESI))
        r.kosul("  Direnc govde tablosu NETLIST'teki her direnci kapsiyor",
                not _eksik,
                f"netlist {len(_direncler)} direnc, tablo "
                f"{len(T.DIRENC_GOVDESI)} kayit"
                + (f" — EKSIK: {', '.join(_eksik)}" if _eksik else ""))
    else:
        r.kosul("  Direnc govde tablosu denetimi", False,
                "netlist3.net yok — once sema3-uret.py kosturulmali")
    r.kosul("  Her govde adi DIRENC_GOVDE tablosunda tanimli",
            all(g in T.DIRENC_GOVDE for g in T.DIRENC_GOVDESI.values()),
            f"{len(set(T.DIRENC_GOVDESI.values()))} farkli govde")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — OP-AMP MAKROMODELI KENDISI DOGRULANIYOR
# ═══════════════════════════════════════════════════════════════════════

def bolum1(r):
    bolum(r, "BOLUM 1 — OP-AMP MAKROMODELININ KENDISI DOGRULANIYOR")
    r.bilgi("  Bu betigin butun sonuclari makromodele dayaniyor. Once")
    r.bilgi("  makromodel dogru mu: (a) izleyici olarak birim kazanc,")
    r.bilgi("  (b) raylarda doyma, (c) cikis akiminin sinirlanmasi.")
    r.bilgi("")

    # (a) + (b): +5 V beslemede izleyici, giris 0..20 V
    net = f"""* LM358 izleyici, +5 V — doyma sinamasi
{LM358}
{AYARLAR}
V5 v5 0 DC 5
Vg giris 0 DC 0
XU giris cik cik v5 0 LM358
Rl cik 0 100k
.control
dc Vg 0 20 0.05
wrdata dc.txt v(cik)
.endc
.end
"""
    veri = tara(net, "mac_doyma")
    dogrusal = [(x, y) for x, y in veri if 0.5 <= x <= 3.0]
    en_kotu = max(abs(y - x) for x, y in dogrusal)
    r.kosul("  (a) dogrusal bolgede birim kazanc", en_kotu < 2e-3,
            f"en buyuk sapma {en_kotu * 1e3:.3f} mV")
    tavan = max(y for _, y in veri)
    r.esit("  (b) cikis tavani = V+ - V_OH dusumu", tavan,
           5.0 - T.LM358_VOH_DUSUM, 0.01, " V")

    # (c) akim siniri: cikisi kisa devre et. +15 V'ta test ediliyor cunku
    #     +5 V'ta doyma gerilimi (3.5 V) zaten 100 ohm'dan yalnizca 35 mA
    #     surebiliyor — akim sinirlayici hic devreye girmiyor.
    for vs, bekle, ad in ((15.0, T.LM358_ISC, "akim siniri devrede"),
                          (5.0, (5.0 - T.LM358_VOH_DUSUM) / 100.0,
                           "cikis empedansi belirleyici")):
        net2 = f"""* LM358 cikisi kisa devre — akim siniri
{LM358}
{AYARLAR}
V5 v5 0 DC {vs}
Vg giris 0 DC {vs}
XU giris ic ic v5 0 LM358
Vam ic 0 DC 0
.control
op
print i(Vam)
.endc
.end
"""
        d = op(net2, f"mac_isc_{vs:.0f}")
        r.esit(f"  (c) V+={vs:.0f} V'ta kisa devre akimi ({ad})",
               abs(d.get("i(vam)", 0.0)), bekle, 0.05, " A")

    # (d) dogrusal bolgede cikis empedansi veri sayfasindan turetilen 100 ohm
    net3 = f"""* yuklu doyma — cikis empedansi
{LM358}
{AYARLAR}
V5 v5 0 DC 30
Vg giris 0 DC 30
XU giris cik cik v5 0 LM358
Rl cik 0 2k
.control
op
print v(cik)
.endc
.end
"""
    d3 = op(net3, "mac_rout")
    vcik = d3.get("v(cik)", 0.0)
    r.kosul("  (d) V+=30 V, R_L=2k'da V_OH veri sayfasi araliginda (>=26 V)",
            vcik >= 26.0, f"{vcik:.2f} V  (TI SLOS068: 26 V min, 27 V tip)")
    r.bilgi("")
    r.bilgi("  Makromodel guvenilir. Bundan sonraki her sonuc buna dayaniyor.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — A · GIRIS TERMINALLERINE YANLIS SINYAL
# ═══════════════════════════════════════════════════════════════════════

def gerilim_kanali_netlist(vin, rust, ralt, rseri, kelepce, ads_seri=0.0,
                           opad="LM358", vplus=5.0):
    """Bir gerilim kanalinin TAM zinciri: bolucu -> RC -> tampon -> ADS.

    kelepce: None | "1N4148"  (tampon girisine, +5 V ve GND'ye)
    ads_seri: tampon cikisi ile ADS pini arasina konacak direnc (bugun 0)
    """
    kel = ""
    if kelepce == "1N4148":
        kel = f"""{D_1N4148}
Dk_ust filt vp D1N4148
Dk_alt 0 filt D1N4148
"""
    rs = f"Rads cik pin {ads_seri}" if ads_seri > 0 else "Rads cik pin 1m"
    # Ampermetreler SERI konmali; asili birakilan bir 0 V kaynagi hep 0 okur.
    #   Vam_giris : filt -> op-amp + girisi  (giris jonksiyonu akimi)
    #   Vam_ust   : ADS'in ust ESD diyodu -> +3V3  (kacan ariza akimi)
    return f"""* gerilim kanali tam zinciri — ariza
{LM358 if opad == 'LM358' else LM358_KOTU}
{D_ESD}
{kel}{AYARLAR}
Vin giris 0 DC {vin}
Vref vref 0 DC {T.VREF}
Vp vp 0 DC {vplus}
V33 v33 0 DC {T.VDD}
Rust giris dugum {rust}
Ralt dugum vref {ralt}
Rf dugum filt {rseri}
Cf filt vref {T.RC_C}
Vam_giris filt opin DC 0
XU opin cik cik vp 0 {opad}
{rs}
Vam_ust esd_a v33 DC 0
Desd_ust pin esd_a DESD
Desd_alt 0 pin DESD
.control
op
print v(dugum) v(filt) v(cik) v(pin) i(Vin) i(Vam_giris) i(Vam_ust)
.endc
.end
"""


def _kanal_arizasi(r, ad, vin, kanal, ads_seri=0.0, opad="LM358"):
    """Tek bir asiri gerilim senaryosunu olcup satir dondurur."""
    d = op(gerilim_kanali_netlist(vin, kanal["rust"], kanal["ralt"],
                                  T.RC_R, None, ads_seri, opad),
           f"kan_{kanal['kod']}_{vin:.0f}_{ads_seri:.0f}_{opad}")
    dugum = d.get("v(dugum)", float("nan"))
    filt = d.get("v(filt)", float("nan"))
    cik = d.get("v(cik)", float("nan"))
    pin = d.get("v(pin)", float("nan"))
    i_giris = abs(d.get("i(vin)", 0.0))
    i_op = abs(d.get("i(vam_giris)", 0.0))
    i_esd = abs(d.get("i(vam_ust)", 0.0))
    p_ust = i_giris ** 2 * kanal["rust_bir"]
    v_ust = i_giris * kanal["rust_bir"]
    return dict(ad=ad, vin=vin, dugum=dugum, filt=filt, cik=cik, pin=pin,
                i_giris=i_giris, i_op=i_op, i_esd=i_esd,
                p_ust=p_ust, v_ust=v_ust)


def bolum2(r):
    bolum(r, "BOLUM 2 — A · GIRIS TERMINALLERINE YANLIS SINYAL")

    # ─────────────────────────────────────────── A1/A2: J1'e 615 V
    alt(r, "A1/A2 · +-32 V terminaline (J1) 615 V DC — en olasi kullanici hatasi")
    r.bilgi("    Yanlis klemens. DEVIR bunu 'en olasi kullanici hatasi' diyor.")
    r.bilgi("")
    r.bilgi(f"    {'giris':>8} {'bolucu':>9} {'LM358 gir':>10} {'tampon':>8} "
            f"{'ADS pini':>9} {'I(R4)':>8} {'P(R4)':>8}")
    r.bilgi("    " + "-" * 68)
    a1 = {}
    for vin in (615.0, -615.0, 325.0, -325.0):
        s = _kanal_arizasi(r, "J1", vin, NORMAL, ads_seri=T.ADS_SERI_R)
        a1[vin] = s
        r.bilgi(f"    {vin:+7.0f}V {s['dugum']:+8.2f}V {s['filt']:+9.2f}V "
                f"{s['cik']:+7.3f}V {s['pin']:+8.3f}V "
                f"{s['i_giris']*1e3:6.3f}mA {s['p_ust']:6.3f}W")

    govde = T.DIRENC_GOVDESI["R4"]
    v_sinir, p_sinir, rth = T.DIRENC_GOVDE[govde]
    s = a1[615.0]
    OLCUM["R4_p_615"] = s["p_ust"]
    OLCUM["R4_v_615"] = s["v_ust"]
    t_film = T.ORTAM_C + s["p_ust"] * rth
    r.bilgi("")
    r.bilgi(f"    R4 govdesi envanterden: {govde} "
            f"({v_sinir:.0f} V calisma, {p_sinir:.2f} W, Rth {rth:.0f} K/W)")
    r.bilgi(f"    615 V'ta R4: {s['v_ust']:.0f} V ({s['v_ust']/v_sinir:.1f}x sinir) "
            f"· {s['p_ust']:.2f} W ({s['p_ust']/p_sinir:.1f}x sinir)")
    r.bilgi(f"    Film sicakligi: {T.ORTAM_C:.0f} + {s['p_ust']:.2f} x {rth:.0f} "
            f"= {t_film:.0f} C   (izin verilen {T.DIRENC_FILM_TMAKS:.0f} C)")
    r.bilgi("")

    r.kosul("    A1: bolucu dugumu DEVIR'in dedigi ~20.1 V'ta",
            abs(s["dugum"] - 20.1) < 0.2, f"{s['dugum']:.2f} V — DEVIR dogru")
    r.kosul("    A1: LM358 girisi mutlak ust sinirin (32 V) ALTINDA",
            s["filt"] < T.LM358_GIRIS_MUTLAK_UST,
            f"{s['filt']:.2f} V < {T.LM358_GIRIS_MUTLAK_UST:.0f} V — LM358 YASAR")
    # ⚠ Iddia EN KOTU tampon modeliyle kurulmali. GARANTI modelde (tavan
    #   3.5 V) ESD diyodu zaten iletmiyor, yani R34 olsa da olmasa da akim
    #   sifir — o iddia R34'e DUYARSIZ olurdu ve hicbir sey sinamazdi.
    _ek = _kanal_arizasi(r, "J1", 615.0, NORMAL, ads_seri=0.0, opad="LM358K")
    _ek34 = _kanal_arizasi(r, "J1", 615.0, NORMAL,
                           ads_seri=T.ADS_SERI_R, opad="LM358K")
    r.bilgi("")
    r.bilgi("    ADS giris akimi (tampon EN KOTU halde, cikis rayda):")
    r.bilgi(f"      R34 YOK    : {_ek['i_esd']*1e3:.3f} mA")
    r.bilgi(f"      R34 (1K)   : {_ek34['i_esd']*1e3:.3f} mA")
    r.kosul("    A1: R34 OLMADAN en kotu halde TI'in tasarim hedefi asiliyor",
            _ek["i_esd"] > T.ADS_TASARIM_AKIM_HEDEFI,
            f"{_ek['i_esd']*1e3:.2f} mA > {T.ADS_TASARIM_AKIM_HEDEFI*1e3:.0f} mA")
    r.kosul("    A1: R34 ile ADS akimi TI'in %20 kuralinin altinda",
            _ek34["i_esd"] < T.ADS_TASARIM_AKIM_TAVANI,
            f"{_ek34['i_esd']*1e3:.3f} mA < "
            f"{T.ADS_TASARIM_AKIM_TAVANI*1e3:.0f} mA "
            f"({_ek['i_esd']/max(_ek34['i_esd'],1e-12):.1f}x iyilesme)")
    r.bilgi("")
    r.bilgi("    🔴 R4 'SIGORTA GIBI ACILIR' VARSAYIMI YANLIS")
    r.bilgi("       Arastirma (Yageo/KOA/Vishay + Horowitz&Hill olcumu):")
    r.bilgi(f"         · IEC 60115-1 4.13 nitelendirme testi 2.5 x RCWV / 5 s")
    r.bilgi(f"           = {T.DIRENC_KALIFIKASYON_GUC_CARPANI:.2f}x nominal GUC. "
            f"Buradaki {s['p_ust']/p_sinir:.1f}x tam o sinirda.")
    r.bilgi(f"         · Amaca yonelik ERIYEN direncler bile acilmak icin "
            f"{T.DIRENC_ERIME_GUC_CARPANI:.0f}x guc istiyor.")
    r.bilgi("         · Film direncler acilmadan ONCE DUSUK DIRENC evresinden")
    r.bilgi("           geciyor (cam dielektrik bozulur -> yerel kisalar).")
    r.bilgi("       Yani R4 ACILMAZ: kizarir, surukler, ve dusuk-direnc")
    r.bilgi("       evresinde bolucu oranini BOZARAK durumu KOTULESTIRIR.")
    r.kosul("    A1: R4 acilma esiginin ALTINDA kaliyor (temiz sigorta DEGIL)",
            s["p_ust"] < T.DIRENC_ERIME_GUC_CARPANI * p_sinir,
            f"{s['p_ust']/p_sinir:.1f}x < {T.DIRENC_ERIME_GUC_CARPANI:.0f}x — "
            f"acilmaz, {t_film:.0f} C'de oturur")
    r.kosul("    A1: R4'un film sicakligi izin verilen sinirin USTUNDE",
            t_film > T.DIRENC_FILM_TMAKS,
            f"{t_film:.0f} C > {T.DIRENC_FILM_TMAKS:.0f} C — yavas bozulma + yanma riski")

    # R4'u BOLMEK: gerilim ve sicakligi ayni anda cozer, N degismez
    r.bilgi("")
    r.bilgi("    COZUM — R4'u SERI PARCALARA BOLMEK (N degismez, firmware aynen kalir):")
    r.bilgi("")
    r.bilgi(f"    {'bolme':>10} {'deger':>9} {'V/parca':>9} {'P/parca':>9} "
            f"{'film C':>8}  yargi")
    r.bilgi("    " + "-" * 60)
    en_iyi = None
    for k in (1, 2, 3):
        rbir = NORMAL["rust"] / k
        vbir = s["v_ust"] / k
        pbir = s["p_ust"] / k
        # bolunmus parcalar NORMAL 1/4W metal film varsayiliyor
        gv, gp, grth = T.DIRENC_GOVDE["1/4W"]
        tf = T.ORTAM_C + pbir * grth
        # ⚠ SUREKLI ariza: gerilim olcutu CALISMA siniri olmali.
        #   DIRENC_ASIRI_YUK_CARPANI (2.0) yalnizca 5 saniyelik test icin.
        ok = tf <= T.DIRENC_FILM_TMAKS and vbir <= gv
        if ok and en_iyi is None:
            en_iyi = (k, rbir, vbir, pbir, tf)
        r.bilgi(f"    {k:>4} x 1/4W {rbir/1e3:8.1f}K {vbir:8.1f}V {pbir:8.3f}W "
                f"{tf:7.0f}C  {'OLUR' if ok else 'olmaz'}")
    r.kosul("    A1: R4'u bolmek 615 V arizasini govde sinirlarina sokuyor",
            en_iyi is not None,
            f"{en_iyi[0]} x {en_iyi[1]/1e3:.0f}K -> {en_iyi[2]:.0f} V, "
            f"{en_iyi[3]:.2f} W, {en_iyi[4]:.0f} C" if en_iyi else "cozum yok")

    sn = a1[-615.0]
    r.bilgi("")
    r.bilgi(f"    TERS GERILIM (-615 V) POZITIFTEN KOTU: bolucu dugumu")
    r.bilgi(f"    {sn['dugum']:+.2f} V'a iniyor. LM358'in mutlak ALT siniri")
    r.bilgi(f"    {T.LM358_GIRIS_MUTLAK_ALT:+.1f} V — yani ust sinir {T.LM358_GIRIS_MUTLAK_UST:.0f} V kadar comert DEGIL.")
    r.bilgi(f"    R7 (22K) akimi sinirliyor: LM358 giris jonksiyonuna")
    r.bilgi(f"    {sn['i_op']*1e6:.0f} uA akiyor.")
    r.kosul("    A2: ters gerilimde LM358 giris akimi guvenli sinirin altinda",
            sn["i_op"] < T.LM358_GIRIS_AKIM_GUVENLI,
            f"{sn['i_op']*1e6:.0f} uA < {T.LM358_GIRIS_AKIM_GUVENLI*1e6:.0f} uA")
    r.kosul("    A2: ADS pini ters gerilimde de mutlak sinirin ustunde",
            sn["pin"] >= T.ADS_MUTLAK_GIRIS_ALT,
            f"{sn['pin']:+.3f} V >= {T.ADS_MUTLAK_GIRIS_ALT:+.1f} V")
    kaydet("A1", "J1 (+-32V) terminaline +615 V DC", "R4 (220K)",
           not_=f"LM358 ve ADS yasiyor; R4 {s['p_ust']:.2f} W ile "
                f"{s['p_ust']/p_sinir:.1f}x asiri yukleniyor, film ~{t_film:.0f} C "
                f"— ACILMIYOR, kizariyor")
    kaydet("A2", "J1 (+-32V) terminaline -615 V DC", "R4 (220K)",
           not_=f"LM358 giris jonksiyonuna {sn['i_op']*1e6:.0f} uA — sinir alti")

    # LM358'in V_OH'u — B15'in EN ONEMLI BULGUSU
    alt(r, "A1b · 🔴 TAMPON DOYDUGU HER AN ADS SPEK DISINDA (ariza degil!)")
    r.bilgi("    🔴 VERI SAYFASI V_OH'u TEK YONLU BAGLIYOR — B15'in en ince")
    r.bilgi("    bulgusu. TI SLOS068AB 5.7 (DUZ LM358 tablosu; 5.5/5.6")
    r.bilgi("    LM358B icindir), 'Voltage output swing from rail,")
    r.bilgi("    positive rail', kosul V_S = 5 V / R_L >= 2k / 25 C:")
    r.bilgi(f"    yalnizca MAKSIMUM verilmis ({T.LM358_VOH_DUSUM:.1f} V). MIN ve TYP YOK.")
    r.bilgi("")
    r.bilgi("    Yani 'cikis rayin en az 1.5 V altina iner' GARANTI edilmis,")
    r.bilgi("    ama 'rayin ne kadar YAKININA cikar' HIC baglanmamis. ADS'in")
    r.bilgi("    gordugu gerilim icin belirleyici olan tam da o ust sinir.")
    r.bilgi("    Ustelik ADS ~2.4 Mohm, yani test kosulundan (2 kohm) 1200 kat")
    r.bilgi("    daha HAFIF yuk — yuk azaldikca cikis raya YAKLASIR.")
    r.bilgi("")
    r.bilgi("    Bu yuzden uc kademe ayri ayri olculuyor:")
    r.bilgi(f"      GARANTI   V_OH = V+ - {T.LM358_VOH_DUSUM:.1f} V  (veri sayfasi maksimum dusum)")
    r.bilgi(f"      MAKUL     V_OH = V+ - {T.LM358_VOH_DUSUM_MAKUL:.1f} V  (hafif yukte tipik davranis)")
    r.bilgi(f"      EN KOTU   V_OH = V+        (spek disi ust sinir)")
    r.bilgi("")
    r.bilgi(f"    {'+5V rayi':>9} {'V_OH dus.':>10} {'ADS pini':>9} "
            f"{'seri R yok':>11} {'seri 1K ile':>12}  yargi")
    r.bilgi("    " + "-" * 70)
    en_kotu_akim = 0.0
    en_kotu_akim_1k = 0.0
    en_kotu_pin = 0.0
    for opad, dusum in (("LM358", T.LM358_VOH_DUSUM),
                        ("LM358M", T.LM358_VOH_DUSUM_MAKUL),
                        ("LM358K", T.LM358_VOH_DUSUM_EN_KOTU)):
        for vp in (4.75, 5.00, 5.25):
            net = f"""* doymus tampon -> ADS pini
{ {'LM358': LM358, 'LM358M': LM358_MAKUL, 'LM358K': LM358_KOTU}[opad] }
{D_ESD}
{AYARLAR}
Vp vp 0 DC {vp}
V33 v33 0 DC {T.VDD}
Vg giris 0 DC 20
XU giris cik cik vp 0 {opad}
Rads cik pin 1m
Vam esd_a v33 DC 0
Desd_ust pin esd_a DESD
Desd_alt 0 pin DESD
.control
op
print v(pin) i(Vam)
.endc
.end
"""
            d0 = op(net, f"voh_{opad}_{vp:.2f}_0")
            net1k = net.replace("Rads cik pin 1m",
                                f"Rads cik pin {T.ADS_SERI_R}")
            d1k = op(net1k, f"voh_{opad}_{vp:.2f}_1k")
            i0 = abs(d0.get("i(vam)", 0.0))
            i1k = abs(d1k.get("i(vam)", 0.0))
            en_kotu_akim = max(en_kotu_akim, i0)
            en_kotu_akim_1k = max(en_kotu_akim_1k, i1k)
            pin = d0.get("v(pin)", 0.0)
            en_kotu_pin = max(en_kotu_pin, pin)
            yargi = ("guvenli" if pin <= T.ADS_MUTLAK_GIRIS_UST
                     else ("mutlak sinir asildi"
                           if i0 < T.ADS_TASARIM_AKIM_HEDEFI
                           else "TI hedefi de asildi"))
            r.bilgi(f"    {vp:8.2f}V {dusum:9.2f}V {pin:8.3f}V "
                    f"{i0*1e3:9.3f}mA {i1k*1e3:10.3f}mA  {yargi}")
    r.bilgi("")
    r.bilgi("    🔴 B2 (sim3_giris.py) bu tabloyu 2.7K SERI DIRENCLE olcup")
    r.bilgi("       'KELEPCE GEREKMIYOR' demisti — ama o 2.7K skop ve hizli")
    r.bilgi("       akim yollarinin kelepce direnciydi; gerilim kanallarinda")
    r.bilgi("       HIC YOKTU: /V_TAMPON = U3.6, U3.7, U7.4 (dogrudan).")
    r.bilgi("       B15/F1 ile R34/R35/R36 eklendi; netlist artik:")
    r.bilgi("       /V_TAMPON = R34.1, U3.6, U3.7  ->  /V_ADS = R34.2, U7.4")
    r.bilgi("")
    r.bilgi("    TI'in TASARIM HEDEFI mutlak sinirdan cok daha siki:")
    r.bilgi(f"      SLVAEX7A 2.1  : ESD diyot akimi <= {T.ADS_TASARIM_AKIM_HEDEFI*1e3:.0f} mA")
    r.bilgi(f"      SBAA227 3.1   : mutlak maksimumun %20'si = "
            f"{T.ADS_TASARIM_AKIM_TAVANI*1e3:.0f} mA")
    r.bilgi(f"      Mutlak sinir  : {T.ADS_GIRIS_AKIM_MAKS*1e3:.0f} mA "
            f"(TAHRIBAT esigi, tasarim hedefi DEGIL)")
    r.bilgi("")
    r.kosul("    A1b: seri direncsiz ADS pini mutlak maksimumu ASIYOR",
            en_kotu_pin > T.ADS_MUTLAK_GIRIS_UST,
            f"en yuksek {en_kotu_pin:.3f} V > {T.ADS_MUTLAK_GIRIS_UST:.2f} V")
    r.kosul("    A1b: 🔴 seri direncsiz EN KOTU halde ADS'in MUTLAK giris "
            "akimi da asiliyor",
            en_kotu_akim > T.ADS_GIRIS_AKIM_MAKS,
            f"{en_kotu_akim*1e3:.1f} mA > {T.ADS_GIRIS_AKIM_MAKS*1e3:.0f} mA "
            f"— tahribat esigi")
    r.kosul(f"    A1b: {T.ADS_SERI_R/1e3:.0f}K seri direnc EN KOTU halde bile "
            f"TI'in %20 kuralini saglıyor",
            en_kotu_akim_1k < T.ADS_TASARIM_AKIM_TAVANI,
            f"{en_kotu_akim*1e3:.1f} mA -> {en_kotu_akim_1k*1e3:.3f} mA "
            f"< {T.ADS_TASARIM_AKIM_TAVANI*1e3:.0f} mA "
            f"({T.ADS_GIRIS_AKIM_MAKS/en_kotu_akim_1k:.1f}x mutlak sinir payi)")
    r.bilgi("")
    r.bilgi("    ⚠ Seri direnc GERILIMI degil AKIMI cozuyor: pin yine 3.8 V'a")
    r.bilgi("      cikiyor ama ESD diyodundan gecen akim zararsiz seviyede.")
    r.bilgi("      Gerilimi de cozmek isteyen tek yol 3.3 V RRIO tampon.")
    r.bilgi("")
    r.bilgi("    ⚠ TI'in 1 NUMARALI onerisi (SLAA593 2): suren op-amp'i ADC ile")
    r.bilgi("      AYNI beslemeden calistir — op-amp raya doyar ve ADC girisi")
    r.bilgi("      ADC'nin besleme araligini HIC asamaz. Bu tasarim tam TERSI:")
    r.bilgi("      LM358 +5 V'ta, ADS 3.3 V'ta. LM358 3.3 V'ta calisamaz")
    r.bilgi(f"      ({T.LM358_VOH_DUSUM:.2f} V dusumle tavani 1.95 V'a duserdi, "
            f"sinyal 2.74 V'a cikiyor)")
    r.bilgi("      — bu yuzden ya SERI DIRENC ya da 3.3 V RRIO op-amp (MCP6002)")
    r.bilgi("      gerekiyor. Ikisi de BOLUM 7'de sayisallastirildi.")

    # ─────────────────────────────────────────── A3: 230 V AC sebeke
    alt(r, "A3 · J1'e 230 V AC SEBEKE (tepe 325 V) — tran")
    r.bilgi("    DC'den farkli: negatif yarim dalga LM358'in girisini")
    r.bilgi("    GND'nin ALTINA suruyor. RC suzgec (R7+C2) genligi biraz")
    r.bilgi("    kirpiyor ama isareti degistirmiyor.")
    r.bilgi("")
    # ⚠ GERCEK tampon bagli olmali. Onceki surumde girise 1 Tohm konmus,
    #   yani LM358'in parazitik jonksiyonu YOKTU ve "girisi -5.6 V goruyor"
    #   deniyordu. Gercekte jonksiyon V- 'nin ~0.6 V altinda kelepceliyor.
    net = f"""* 230 V AC sebeke J1'e — GERCEK tamponla
{LM358}
{AYARLAR}
Vin giris 0 SIN(0 {T.SEBEKE_TEPE} {T.SEBEKE_HZ})
Vref vref 0 DC {T.VREF}
Vp vp 0 DC 5
R4 giris dugum {NORMAL['rust']}
R6 dugum vref {NORMAL['ralt']}
R7 dugum filt {T.RC_R}
C2 filt vref {T.RC_C}
Vam filt opin DC 0
XU opin cik cik vp 0 LM358
.control
tran 20u 80m 0 20u
wrdata tr.txt v(dugum) v(filt) i(Vam)
.endc
.end
"""
    tr = [s for s in tara(net, "ac_sebeke", "tr.txt") if s[0] >= 0.04]
    dug = [s[1] for s in tr]
    filt = [s[2] for s in tr]
    iop = [abs(s[3]) for s in tr]
    r.bilgi(f"    Bolucu dugumu : {min(dug):+8.3f} .. {max(dug):+8.3f} V")
    r.bilgi(f"    LM358 girisi  : {min(filt):+8.3f} .. {max(filt):+8.3f} V")
    r.bilgi(f"    LM358 giris akimi (tepe) : {max(iop)*1e6:.0f} uA")
    r.bilgi("")
    r.bilgi("    Girisin -5.6 V'a inmedigine dikkat: parazitik jonksiyon")
    r.bilgi("    onu ~-0.6 V'ta kelepceliyor ve akimi R7 sinirliyor.")
    r.bilgi("")
    i_neg = max(iop)
    r.kosul("    A3: negatif yarim dalga LM358'in mutlak alt sinirini ASIYOR",
            min(filt) < T.LM358_GIRIS_MUTLAK_ALT,
            f"{min(filt):.3f} V < {T.LM358_GIRIS_MUTLAK_ALT:+.1f} V — SPEC DISI")
    r.kosul("    A3: ama parazitik jonksiyon kelepceliyor, R7 akimi sinirliyor",
            i_neg < T.LM358_GIRIS_AKIM_GUVENLI,
            f"{i_neg*1e6:.0f} uA < {T.LM358_GIRIS_AKIM_GUVENLI*1e6:.0f} uA "
            f"(TI'in kendi kilavuzu)")
    # R4'e dusen RMS gerilim ve guc — sebeke DC 615 V'tan cok daha hafif
    v_r4_rms = T.SEBEKE_RMS * NORMAL["rust"] / NORMAL["giris_z"]
    p_r4_ac = v_r4_rms ** 2 / NORMAL["rust"]
    r.bilgi("")
    r.bilgi(f"    R4 ({govde}): {v_r4_rms:.0f} V RMS / "
            f"{v_r4_rms*math.sqrt(2):.0f} V tepe · {p_r4_ac:.3f} W")
    r.bilgi(f"    Sinirlar: {v_sinir:.0f} V calisma, {p_sinir:.2f} W")
    r.kosul("    A3: 230 V AC'de R4 GUC sinirini ASMIYOR (govde 1W oldugu icin)",
            p_r4_ac < p_sinir,
            f"{p_r4_ac:.3f} W < {p_sinir:.2f} W — 615 V DC'den cok daha hafif")
    r.kosul("    A3: R4'un tepe gerilimi calisma sinirinin altinda",
            v_r4_rms * math.sqrt(2) < v_sinir,
            f"{v_r4_rms*math.sqrt(2):.0f} V < {v_sinir:.0f} V")
    r.bilgi("")
    r.bilgi("    ⚠ Sasirtici sonuc: 230 V AC, 615 V DC'den DAHA ZARARSIZ.")
    r.bilgi("      Tek sorun LM358'in girisinin GND altina inmesi; hicbir")
    r.bilgi("      parca gitmiyor. Bu, R4'un envanterdeki govdesinin 1/4W")
    r.bilgi("      DEGIL 1W olmasi sayesinde (tasarim3.py hepsini 1/4W sayiyor).")
    kaydet("A3", "J1'e 230 V AC sebeke", "",
           not_=f"hicbir parca gitmiyor; LM358 girisi {min(filt):.2f} V'ta "
                f"kelepceleniyor, akim {i_neg*1e6:.0f} uA. R4 "
                f"{p_r4_ac:.2f} W (sinir {p_sinir:.2f} W)")

    # ─────────────────────────────────────────── A4: HV kanalina asiri gerilim
    alt(r, "A4 · 615 V terminaline (J2) 1000 V ve uzeri")
    r.bilgi("    N = 601 oldugu icin HV kanali asiri gerilime NORMAL")
    r.bilgi("    kanaldan cok daha dayanikli — belirleyici olan direnc")
    r.bilgi("    basina dusen gerilim.")
    r.bilgi("")
    hv_govde = T.DIRENC_GOVDESI["R10"]
    hv_vsinir, hv_psinir, hv_rth = T.DIRENC_GOVDE[hv_govde]
    r.bilgi(f"    820K govdesi envanterden: {hv_govde} "
            f"({hv_vsinir:.0f} V calisma, {hv_psinir:.1f} W)")
    r.bilgi("")
    r.bilgi(f"    {'giris':>8} {'bolucu':>8} {'LM358 gir':>10} {'ADS pini':>9} "
            f"{'V/820K':>8} {'P/820K':>8}  yargi")
    r.bilgi("    " + "-" * 68)
    hv_son = {}
    for vin in (613.0, 1000.0, 1500.0, 2000.0, -1000.0):
        s = _kanal_arizasi(r, "J2", vin, HV, ads_seri=T.ADS_SERI_R)
        hv_son[vin] = s
        yargi = "ok" if s["v_ust"] <= hv_vsinir else "GERILIM ASILDI"
        r.bilgi(f"    {vin:+7.0f}V {s['dugum']:+7.3f}V {s['filt']:+9.3f}V "
                f"{s['pin']:+8.3f}V {s['v_ust']:7.1f}V "
                f"{s['p_ust']*1e3:6.1f}mW  {yargi}")
    # direnc gerilim sinirinin asildigi giris
    v_asma = hv_vsinir * HV["N"] * HV["rust"] / (HV["rust_bir"] * HV["N"] - 0)
    v_asma = hv_vsinir / (HV["rust_bir"] / HV["giris_z"])
    r.bilgi("")
    r.bilgi(f"    820K'nin {hv_vsinir:.0f} V calisma siniri {v_asma:.0f} V girise "
            f"kadar asilmiyor.")
    r.kosul("    A4: 1000 V'ta ADS pini mutlak sinirin altinda",
            hv_son[1000.0]["pin"] <= T.ADS_MUTLAK_GIRIS_UST,
            f"{hv_son[1000.0]['pin']:.3f} V (tampon doyuyor, koruyor)")
    r.kosul("    A4: 2000 V'ta bile LM358 girisi 32 V sinirinin altinda",
            hv_son[2000.0]["filt"] < T.LM358_GIRIS_MUTLAK_UST,
            f"{hv_son[2000.0]['filt']:.2f} V")
    # NORMAL kanalda belirleyici olan R4'un GERILIM siniri
    _r4_v, _r4_p, _ = T.DIRENC_GOVDE[T.DIRENC_GOVDESI["R4"]]
    _n_asma = _r4_v / (NORMAL["rust_bir"] / NORMAL["giris_z"])
    r.kosul("    A4: HV kanali NORMAL kanaldan cok daha dayanikli",
            v_asma / _n_asma > 5,
            f"820K zinciri {v_asma:.0f} V'a dayaniyor, R4 ise {_n_asma:.0f} V'a "
            f"— {v_asma/_n_asma:.1f} kat")
    r.kosul("    A4: bunun sebebi bolme oranlarinin farki",
            HV["N"] / NORMAL["N"] > 15,
            f"N: {HV['N']:.0f} / {NORMAL['N']:.2f} = "
            f"{HV['N']/NORMAL['N']:.1f} kat")
    kaydet("A4", "J2 (+-615V) terminaline 1000 V", "",
           not_=f"hicbir sinir asilmiyor; olcum kirpiyor. "
                f"{v_asma:.0f} V'un ustunde 820K gerilim siniri asilir")

    # ─────────────────────────────────────────── A5: skop girisi
    alt(r, "A5 · Skop girisine (J4) menzil disi gerilim")
    r.bilgi(f"    Bolucu {T.SKOP_RUST/1e3:.0f}K / {T.SKOP_RALT/1e3:.1f}K, "
            f"N = {T.SKOP_N:.2f}. Tampon TL072 (+-12 V),")
    r.bilgi(f"    sonra {T.R_SERI/1e3:.1f}K seri + 2x BAT85 -> GPIO4.")
    r.bilgi("")
    r.bilgi(f"    {'giris':>8} {'bolucu':>9} {'TL072 cik':>10} {'GPIO4':>8} "
            f"{'kelepce I':>10} {'P(R20)':>8}")
    r.bilgi("    " + "-" * 66)
    skop_govde = T.DIRENC_GOVDESI["R20"]
    skop_v, skop_p, skop_rth = T.DIRENC_GOVDE[skop_govde]
    en_gpio_ust, en_gpio_alt, en_kel, en_tl = -9e9, 9e9, 0.0, 0.0
    for vin in (50.0, 160.0, 250.0, 400.0, -400.0):
        net = f"""* skop kanali arizasi
{TL072}
{D_BAT85}
{AYARLAR}
Vin giris 0 DC {vin}
V12p v12p 0 DC 12
V12n v12n 0 DC -12
V33 v33 0 DC {T.VDD}
R20 giris dugum {T.SKOP_RUST}
R23 dugum 0 {T.SKOP_RALT}
* Sallen-Key'in SERI direncleri (R22 + R21 = 2 x 6.8K) giris yolunda —
* akim sinirlamasini asil bunlar yapiyor. Onceki surumde atlanmisti.
R22 dugum sk1 {T.SK_R}
Vam_g sk1 skm DC 0
R21 skm opin {T.SK_R}
XU opin cik cik v12p v12n TL072
R26 cik gpio {T.R_SERI}
Vam kel_a v33 DC 0
D1 gpio kel_a DBAT85
Vam2 0 kel_b DC 0
D2 kel_b gpio DBAT85
.control
op
print v(dugum) v(cik) v(gpio) i(Vam) i(Vam2) i(Vin) i(Vam_g)
.endc
.end
"""
        d = op(net, f"skop_{vin:.0f}")
        g = d.get("v(gpio)", 0.0)
        ikel = max(abs(d.get("i(vam)", 0.0)), abs(d.get("i(vam2)", 0.0)))
        i_tl072 = abs(d.get("i(vam_g)", 0.0))
        en_tl = max(en_tl, i_tl072)
        ig = abs(d.get("i(vin)", 0.0))
        p20 = ig ** 2 * T.SKOP_RUST
        en_gpio_ust = max(en_gpio_ust, g)
        en_gpio_alt = min(en_gpio_alt, g)
        en_kel = max(en_kel, ikel)
        r.bilgi(f"    {vin:+7.0f}V {d.get('v(dugum)',0):+8.3f}V "
                f"{d.get('v(cik)',0):+9.3f}V {g:+7.3f}V "
                f"{ikel*1e3:8.3f}mA {p20*1e3:6.1f}mW")
    v_p20 = math.sqrt(skop_p * T.SKOP_RUST) * T.SKOP_N / (T.SKOP_N - 1)
    r.bilgi("")
    r.bilgi(f"    R20 ({skop_govde}) guc sinirini {v_p20:.0f} V girişte asiyor —")
    r.bilgi("    yani skop kanalinin GERCEK siniri bolucunun degil, R20'nin.")
    r.kosul("    A5: BAT85 kelepceleri GPIO'yu mutlak pencerede tutuyor",
            en_gpio_alt >= T.ESP_MUTLAK_PIN_ALT
            and en_gpio_ust <= T.ESP_MUTLAK_PIN_UST,
            f"{en_gpio_alt:+.3f} .. {en_gpio_ust:+.3f} V  (sinir "
            f"{T.ESP_MUTLAK_PIN_ALT:+.1f} .. {T.ESP_MUTLAK_PIN_UST:+.1f})")
    r.kosul("    A5: kelepce akimi BAT85'in surekli siniri altinda",
            en_kel < T.BAT85_IF_SUREKLI,
            f"{en_kel*1e3:.2f} mA < {T.BAT85_IF_SUREKLI*1e3:.0f} mA")
    r.kosul("    A5: TL072 giris kelepce akimini Sallen-Key direncleri "
            "(2x6.8K) sinirliyor",
            en_tl < T.TL072_GIRIS_AKIM_MAKS,
            f"{en_tl*1e3:.2f} mA < {T.TL072_GIRIS_AKIM_MAKS*1e3:.0f} mA — "
            f"akim sinirlamasini R20 degil R22+R21 yapiyor")
    r.kosul("    A5: R20 skop kanalinin gercek sinirini belirliyor",
            v_p20 < 250.0, f"{v_p20:.0f} V — bolucu {T.SKOP_TAVAN*T.SKOP_N:.0f} V "
                           f"'okuyabilir' ama R20 dayanmaz")
    kaydet("A5", "Skop girisine +-400 V", "R20 (100K)",
           not_=f"GPIO {en_gpio_alt:+.2f}..{en_gpio_ust:+.2f} V — BAT85 tutuyor; "
                f"R20 {v_p20:.0f} V ustunde yaniyor")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2b — A · SONT KANALI (bu betikte bulunan EN BUYUK acik)
# ═══════════════════════════════════════════════════════════════════════

def bolum2b(r):
    alt(r, "A6 · SONT: YANLIS SONT SECILMESI (en olasi akim hatasi)")
    r.bilgi(f"    Sont soketli: {', '.join(f'{x:g}R' for x in T.SONT_SECENEK)}.")
    r.bilgi(f"    Kelvin uclari R18/R19 = {T.SONT_KELVIN_R:.0f}R ile ADS #1'e gidiyor.")
    r.bilgi("    Duzeltme ONCESI SONT_P ile ADS pini arasinda HICBIR SEY")
    r.bilgi("    yoktu: /SONT_P = C4.1, R18.2, R27.1, U6.4")
    r.bilgi(f"    B15/F2 ile R38/R39 ({T.ADS_SERI_R/1e3:.0f}K) eklendi; artik")
    r.bilgi("    /SONT_P = C4.1, R18.2, R27.1, R38.1 -> /SONT_P_A = R38.2, U6.4")
    r.bilgi("")
    r_once = T.SONT_KELVIN_R
    r_sonra = T.SONT_KELVIN_R + T.ADS_SERI_R
    v_kel = T.VDD + T.ADS_ESD_VF
    r.bilgi(f"    {'sont':>7} {'ADS mutlak':>11} {'ADS 10 mA (once)':>17} "
            f"{'ADS 10 mA (R38 ile)':>20} {'3V3 (R38 ile)':>14}")
    r.bilgi("    " + "-" * 74)
    esikler = {}
    for rs in T.SONT_SECENEK:
        i_mutlak = T.ADS_MUTLAK_GIRIS_UST / rs
        i_10_once = (T.ADS_GIRIS_AKIM_MAKS * r_once + v_kel) / rs
        i_10ma = (T.ADS_GIRIS_AKIM_MAKS * r_sonra + v_kel) / rs
        i_ray = (T.ESP_BOSTA_AKIM * r_sonra + v_kel) / rs
        esikler[rs] = (i_mutlak, i_10ma, i_ray, i_10_once)
        r.bilgi(f"    {rs:6g}R {i_mutlak:9.3f} A {i_10_once:15.3f} A "
                f"{i_10ma:18.3f} A {i_ray:12.3f} A")
    r.bilgi("")
    r.bilgi("    'ADS mutlak'  : bu yuk akiminda ADS pini 3.6 V'u asiyor")
    r.bilgi("    'ADS 10 mA'   : bu yuk akiminda ADS giris akimi siniri asiliyor")
    r.bilgi("    '3V3 tehlike' : bu yuk akiminda kacak, ESP32'nin kendi bosta")
    r.bilgi(f"                    tuketimini ({T.ESP_BOSTA_AKIM*1e3:.0f} mA) asiyor ve 3V3 rayi")
    r.bilgi("                    YUKSELMEYE basliyor -> ESP32 de tehlikede")
    r.bilgi("")
    i10 = esikler[10.0]
    _yaygin_yuk = 0.5          # "yarim amperlik siradan bir yuk"
    r.kosul(f"    A6: R38 OLMADAN {_yaygin_yuk:.1f} A'lik siradan bir yuk "
            f"ADS'i olduruyordu",
            i10[3] < _yaygin_yuk,
            f"duzeltme oncesi esik {i10[3]:.3f} A < {_yaygin_yuk:.1f} A")
    r.kosul("    A6: R38 ile esik tam olcegin (25.6 mA) 58 kati uzerine cikti",
            i10[1] > 1.0,
            f"{i10[3]:.3f} A -> {i10[1]:.3f} A "
            f"({i10[1]/i10[3]:.1f}x). 10R sontun tam olcegi "
            f"{0.256/10*1e3:.1f} mA, yani pay {i10[1]/(0.256/10):.0f}x")
    r.kosul("    A6: R38 ile 3V3 rayi tehlikesi pratik disina cikti",
            i10[2] ** 2 * 10.0 > 100.0,
            f"{i10[2]:.2f} A — 10R sont uzerinde bu {i10[2]**2*10:.0f} W "
            f"demek, sont zaten cok once yanar")
    kaydet("A6", "Yanlis sont (10R) + asiri yuk", "U6 (ADS1115 #1)",
           not_=f"R38 SONRASI: esik {i10[3]:.2f} A -> {i10[1]:.2f} A. "
                f"10R sontun tam olcegi yalnizca {0.256/10*1e3:.1f} mA "
                f"oldugu icin bu esige ulasmak icin sontu {i10[1]/(0.256/10):.0f} "
                f"kat asirilamak gerekiyor")

    alt(r, "A7 · SONT ACIK DEVRE — DEVIR'in cevapsiz biraktigi senaryo")
    r.bilgi("    Sont soketli/vidali; gevsek baglanti cok olasi.")
    r.bilgi("")
    r.bilgi("    ⚠ YOLU DOGRU KURMAK SART: sont ALCAK tarafta")
    r.bilgi("      (J3.1 = YUK_EKSI = R18.1 = RS.1, RS.2 = GND). Sont acilinca")
    r.bilgi("      yuk akimi ESKI BUYUKLUGUNDE baska yola donmez — sifira")
    r.bilgi("      duser ve YENI bir cevrim olusur:")
    r.bilgi("        V_kaynak -> HARICI YUK -> J3.1 -> R18 -> ADS AIN0")
    r.bilgi("                 -> ic ESD diyodu -> +3V3 -> GND -> J3.2")
    r.bilgi("      Harici yuk direnci bu cevrimde SERIDIR ve formulden")
    r.bilgi("      atilamaz. Asagidaki tablo onu iceriyor.")
    r.bilgi("")
    r.bilgi(f"    {'kaynak':>8} {'yuk akimi':>10} {'R_yuk':>9} "
            f"{'R38 YOK':>13} {'R38 (1K) ile':>12} {'ADS':>7} {'3V3':>9}")
    r.bilgi("    " + "-" * 74)
    r18_v, r18_p, r18_rth = T.DIRENC_GOVDE[T.DIRENC_GOVDESI["R18"]]
    a7 = {}
    durumlar = [(5.0, 0.010), (5.0, 1.0), (5.0, None),
                (12.0, 0.010), (12.0, 1.0), (12.0, None),
                (32.0, 1.0), (32.0, None)]
    for v, iyuk in durumlar:
        ryuk = ACIK if iyuk is None else max(v / iyuk, 1e-3)
        etiket_r = "0 (ciplak)" if iyuk is None else f"{v/iyuk:.1f}R"
        etiket_i = "—" if iyuk is None else f"{iyuk*1e3:.0f} mA"
        satir = {}
        for rads in (0.0, T.ADS_SERI_R):
            net = f"""* sont ACIK — harici yuk cevrimde SERI
{D_ESD}
{AYARLAR}
Vyuk kaynak 0 DC {v}
V33 v33 0 DC {T.VDD}
Ryuk kaynak yuk {1e-3 if iyuk is None else v / iyuk}
Rsont yuk 0 {ACIK}
R18 yuk sp {T.SONT_KELVIN_R}
R38 sp spa {rads if rads > 0 else 1e-3}
Vam esd_a v33 DC 0
Desd_ust spa esd_a DESD
Desd_alt 0 spa DESD
.control
op
print v(spa) i(Vam)
.endc
.end
"""
            d = op(net, f"sont_acik_{v:.0f}_"
                        f"{0 if iyuk is None else iyuk*1000:.0f}_{rads:.0f}")
            satir[rads] = abs(d.get("i(vam)", 0.0))
        a7[(v, iyuk)] = satir[T.ADS_SERI_R]
        a7[(v, iyuk, "ham")] = satir[0.0]
        i = satir[T.ADS_SERI_R]
        p18 = i ** 2 * T.SONT_KELVIN_R
        r.bilgi(f"    {v:7.1f}V {etiket_i:>10} {etiket_r:>9} "
                f"{satir[0.0]*1e3:11.2f}mA {i*1e3:10.2f}mA "
                f"{'OLUR' if i > T.ADS_GIRIS_AKIM_MAKS else 'yasar':>7} "
                f"{'YUKSELIR' if i > T.ESP_BOSTA_AKIM else 'guvende':>9}")
    r.bilgi("")
    r.bilgi("    ⚠ DEVIR 5.12.22 senaryo 5 bu soruyu soruyordu ama")
    r.bilgi("      cevaplamiyordu. CEVAP KOSULLU:")
    r.bilgi("")
    r.kosul("    A7: R38 OLMADAN 1 A'lik yuk ADS'i olduruyordu",
            a7[(12.0, 1.0, "ham")] > T.ADS_GIRIS_AKIM_MAKS,
            f"12 V / 1 A -> {a7[(12.0,1.0,'ham')]*1e3:.1f} mA > "
            f"{T.ADS_GIRIS_AKIM_MAKS*1e3:.0f} mA (duzeltme oncesi)")
    r.kosul("    A7: R38 (1K) ile ayni yukte ADS sinir ALTINA iniyor",
            a7[(12.0, 1.0)] < T.ADS_GIRIS_AKIM_MAKS,
            f"{a7[(12.0,1.0,'ham')]*1e3:.1f} mA -> {a7[(12.0,1.0)]*1e3:.2f} mA "
            f"({a7[(12.0,1.0,'ham')]/a7[(12.0,1.0)]:.1f}x iyilesme)")
    r.kosul("    A7: 32 V CIPLAK besleme hala ADS'i goturuyor — KALAN RISK",
            a7[(32.0, None)] > T.ADS_GIRIS_AKIM_MAKS,
            f"32 V ciplak -> {a7[(32.0,None)]*1e3:.1f} mA "
            f"({a7[(32.0,None)]/T.ADS_GIRIS_AKIM_MAKS:.1f}x sinir) — bu "
            f"senaryo icin sont kolunda SIGORTA gerekiyor")
    r.kosul("    A7: R38 ile 3V3 rayi HICBIR senaryoda yukselmiyor",
            all(a7[k] < T.ESP_BOSTA_AKIM
                for k in a7 if len(k) == 2),
            f"en yuksek {max(a7[k] for k in a7 if len(k)==2)*1e3:.1f} mA < "
            f"{T.ESP_BOSTA_AKIM*1e3:.0f} mA — ESP32 her senaryoda GUVENDE")
    r.bilgi("")
    r.bilgi("    NOT: 80 mA'in uzerinde asil baskin ariza ADS pini DEGIL,")
    r.bilgi("    geri surulen +3V3 rayidir. Yukaridaki tablo rayin 3.3 V'ta")
    r.bilgi("    CIVILI kaldigini varsayiyor; gercekte LDO akim SINK edemez,")
    r.bilgi("    ray yukselir ve ESP32 ile U7 de mutlak sinir disina cikar.")
    r.bilgi("    Yani tablo bu yonde IYIMSER.")
    kaydet("A7", "Sont ACIK DEVRE (32 V ciplak besleme)",
           "U6 (ADS1115 #1)",
           not_=f"R38 SONRASI: 12 V / 1 A yukte {a7[(12.0,1.0)]*1e3:.1f} mA "
                f"(sinir alti, ADS yasiyor). Yalnizca klemense CIPLAK besleme "
                f"baglanirsa ({a7[(32.0,None)]*1e3:.0f} mA) ADS gidiyor; "
                f"ESP32 her halde guvende")

    alt(r, "A8 · Sont TERS AKIM — tasarim geregi, sinir neresi")
    r.bilgi("    Kart cift yonlu tasarlandi; ters akim ARIZA DEGIL. Ama")
    r.bilgi("    sinir hic olculmemisti.")
    r.bilgi("")
    pga_min = 0.256
    r.bilgi(f"    {'sont':>7} {'tam olcek akim':>15} {'ADS pini (-FS)':>16}")
    r.bilgi("    " + "-" * 42)
    for rs in T.SONT_SECENEK:
        i_fs = pga_min / rs
        r.bilgi(f"    {rs:6g}R {i_fs:13.3f} A {-pga_min:14.3f} V")
    r.bilgi("")
    r.bilgi(f"    Ters yonde ADS pini en fazla -{pga_min:.3f} V'a iniyor.")
    r.kosul("    A8: ters akimda ADS pini mutlak alt sinirin ustunde",
            -pga_min > T.ADS_MUTLAK_GIRIS_ALT,
            f"{-pga_min:.3f} V > {T.ADS_MUTLAK_GIRIS_ALT:+.1f} V — "
            f"pay yalnizca {(-pga_min-T.ADS_MUTLAK_GIRIS_ALT)*1e3:.0f} mV")
    r.bilgi("")
    r.bilgi("    ⚠ Bu pay 44 mV. PGA +-0.256'da tam olcekte calisirken")
    r.bilgi("      ADS'in kendi ofseti ve sontun toleransi bu payi yiyebilir.")
    r.bilgi("      Ters yonde tam olcege DAYANMAK dogru degil.")
    kaydet("A8", "Sont ters akim, tam olcek", "",
           not_=f"guvenli ama pay yalnizca "
                f"{(-pga_min-T.ADS_MUTLAK_GIRIS_ALT)*1e3:.0f} mV")



# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2c — A9/B6 · GOREV TANIMININ KALAN IKI SENARYOSU
#  (DEVIR 5.12.22 madde 8 ve madde 13)
# ═══════════════════════════════════════════════════════════════════════

def bolum2c(r):
    alt(r, "A9 · PROB UCU KAYMASI — bir uc komsu terminale degerse")
    r.bilgi("    DEVIR 5.12.22 madde 13. Dort giris terminali yan yana;")
    r.bilgi("    615 V'luk ucun kaymasi en olasi kaza.")
    r.bilgi("")
    r.bilgi(f"    {'615 V nereye degdi':<24} {'bolucu N':>9} {'dugum':>9} "
            f"{'seri R':>8} {'P(ust R)':>10}  sonuc")
    r.bilgi("    " + "-" * 74)
    kaymalar = [
        ("J1 (+-32 V girisi)", NORMAL["N"], NORMAL["rust"], "R4",
         T.DIRENC_GOVDESI["R4"]),
        ("J4 (skop girisi)", T.SKOP_N, T.SKOP_RUST, "R20",
         T.DIRENC_GOVDESI["R20"]),
    ]
    a9 = {}
    for ad, n, rust, ref, govde in kaymalar:
        dugum = 615.0 / n
        i = (615.0 - dugum) / rust
        p = i * i * rust
        gv, gp, grth = T.DIRENC_GOVDE[govde]
        t = T.ORTAM_C + p * grth
        a9[ref] = (p, gp, t, dugum)
        r.bilgi(f"    {ad:<24} {n:8.2f} {dugum:8.2f}V {ref:>8} "
                f"{p:8.2f} W  {p/gp:.0f}x govde, {t:.0f} C")
    r.bilgi("")
    r.bilgi("    J1'e kayma = A1 senaryosunun ta kendisi (zaten olculdu).")
    r.bilgi("    J4'e kayma DAHA KOTU: skop bolucusu yalnizca N = 15.7,")
    r.bilgi("    yani ayni gerilim 38 kat daha az bolunuyor.")
    r.bilgi("")
    p20, gp20, t20, d20 = a9["R20"]
    r.kosul("    A9: 615 V skop girisine degerse R20 aniden 14x asiri yukleniyor",
            p20 / gp20 > 10, f"{p20:.2f} W / {gp20:.2f} W = {p20/gp20:.0f}x, "
                             f"film ~{t20:.0f} C — R20 GIDER")
    # TL072 girisi: R20/R23 dugumu, sonra R22+R21 seri
    i_tl = (d20 - T.TL072_CIKIS_TAVAN) / (T.SK_R * 2)
    r.kosul("    A9: TL072 giris akimi mutlak sinirin altinda kaliyor",
            abs(i_tl) < T.TL072_GIRIS_AKIM_MAKS,
            f"{abs(i_tl)*1e3:.2f} mA < {T.TL072_GIRIS_AKIM_MAKS*1e3:.0f} mA — "
            f"Sallen-Key'in 2x{T.SK_R/1e3:.1f}K'si akimi sinirliyor")
    r.bilgi("")
    r.bilgi("    ⚠ TL072'nin girisi bu senaryoda +38 V goruyor; mutlak")
    r.bilgi(f"      sinir +-{T.TL072_GIRIS_MUTLAK:.0f} V. Kelepce diyotlari (yeni die)")
    r.bilgi("      akimi tasiyor ve sinirda kaliyor, ama ESKI die'da")
    r.bilgi("      kelepce YOK — o durumda TL072 de gider.")
    r.bilgi("")
    r.bilgi("    ✅ COZUM ucuz ve tamamen mekanik: 615 V terminali DIGER")
    r.bilgi("       UCTA, aralarinda en az bir bos yuva, AYRI renk ve")
    r.bilgi("       etiketli olsun. Semada zaten 'AYRI ve isaretli olmali'")
    r.bilgi("       notu var — B15 bunu sayiyla gerekcelendiriyor.")
    kaydet("A9", "615 V ucu SKOP girisine kayiyor", "R20 (100K)",
           not_=f"{p20:.1f} W ({p20/gp20:.0f}x govde). J1'e kayma = A1. "
                f"TL072 giris akimi {abs(i_tl)*1e3:.1f} mA ile sinirli")

    alt(r, "B6 · USB TAKILIYKEN harici besleme de bagli")
    r.bilgi("    DEVIR 5.12.22 madde 8. Bugunku semada +5 V rayi J5.8'den,")
    r.bilgi("    yani ESP32 kartindan geliyor (netlist: +5V = J5.8, U3.8,")
    r.bilgi("    U4.8, C9.1, C10.1). DEVIR 5.12.23 ise +5 V'u 24 V'tan")
    r.bilgi("    besleyen bir 7805 onermisti. IKISI BIRDEN olursa:")
    r.bilgi("")
    r.bilgi("      USB VBUS (4.75..5.25 V)  --+")
    r.bilgi("                                 +-- ayni +5V rayi")
    r.bilgi("      7805 cikisi (4.8..5.2 V) --+")
    r.bilgi("")
    r.bilgi("    Iki kaynak paralel: YUKSEK olan digerini geri suruyor.")
    r.bilgi("")
    fark = 5.25 - 4.80
    r.kosul("    B6: iki kaynak arasindaki en kotu fark kucuk",
            fark < 1.0, f"{fark:.2f} V (USB 5.25 maks, 7805 4.80 min)")
    r.bilgi("")
    r.bilgi("    🔴 ASIL TEHLIKE BU DEGIL — 7805'IN TERS SURULMESI:")
    r.bilgi("    24 V kesilip USB takili kalirsa 7805'in CIKISI girisinden")
    r.bilgi("    yuksek olur. 78xx serisinde bu klasik bir olum sebebidir:")
    r.bilgi("    pass transistorunun taban-kolektor jonksiyonu ters yonde")
    r.bilgi("    iletir ve cikis kondansatorunun enerjisi cipin icinden akar.")
    r.bilgi("")
    r.bilgi("    ✅ COZUM (standart uygulama): 7805'in CIKISINDAN GIRISINE")
    r.bilgi("       ters bir diyot (1N4148 ya da 1N4007). Envanterde 1N4148")
    r.bilgi("       8 adet var. Maliyet ~0.2 TL.")
    r.bilgi("")
    r.bilgi("    ✅ DAHA IYISI: +5 V'u TEK kaynaktan al. Bugunku sema zaten")
    r.bilgi("       oyle (J5.8 = ESP32 karti). 7805'i eklemek yeni bir ariza")
    r.bilgi("       modu aciyor ve B1'deki guc sirasi sorununu da")
    r.bilgi("       kotulestiriyor (+5 V var, +3V3 yok hali mumkun hale gelir).")
    # NETLIST'ten okunan gercek denetim: +5V agina bagli KAYNAK pini
    # (konnektor/regulator) sayisi 1 olmali. Ikinci bir kaynak eklenirse
    # bu kural kirmiziya doner.
    import re as _re
    _m = (BURASI / "netlist3.net").read_text(encoding="utf-8", errors="replace")
    _i = _m.find('(name "+5V")')
    _blok = _m[_i:_m.find("(net", _i + 10)] if _i > 0 else ""
    _pinler = _re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', _blok)
    _kaynak = [f"{a}.{b}" for a, b in _pinler
               if a.startswith("J") or a.startswith("U1")]
    r.kosul("    B6: +5V rayinda TEK kaynak var (netlist'ten okundu)",
            len(_kaynak) == 1,
            f"{', '.join(_kaynak) or 'yok'} — ikinci bir kaynak (7805) "
            f"eklenirse bu kural kirmiziya doner")
    kaydet("B6", "USB + harici besleme birlikte", "",
           not_="bugunku semada iki kaynak YOK, sorun da yok. 7805 eklenirse "
                "cikis->giris ters diyodu SART")

    alt(r, "B7 · Yuk terminaline (J3) gerilim baglanmasi")
    r.bilgi("    J3 'yuk donusu' terminali; kullanici oraya yanlislikla")
    r.bilgi("    besleme baglarsa A7'nin (sont acik) en kotu haliyle ayni")
    r.bilgi("    devreyi kuruyor — cunku sont 15 mR ise neredeyse kisa devre,")
    r.bilgi("    10R ise seri direnc gorevi goruyor.")
    r.bilgi("")
    r.bilgi(f"    {'sont':>7} {'32 V baglanirsa':>17} {'P(sont)':>10}  sonuc")
    r.bilgi("    " + "-" * 50)
    for rs in T.SONT_SECENEK:
        i = 32.0 / rs
        p = i * i * rs
        r.bilgi(f"    {rs:6g}R {i:15.1f} A {p:8.0f} W  "
                f"{'sont YANAR' if p > 5 else 'sinirda'}")
    _rs_min = min(T.SONT_SECENEK)
    _v = NORMAL["fs_sim"]
    _p = _v ** 2 / _rs_min
    r.kosul(f"    B7: en dusuk sont ({_rs_min*1e3:.0f} mR) tam olcek gerilimde "
            f"aninda yaniyor",
            _p > 100 * T.DIRENC_GOVDE["2W"][1],
            f"{_p:.0f} W ({_v:.1f} V) — {_v/_rs_min:.0f} A ceker; "
            f"sinirlayan tek sey kaynagin kendisi")
    r.bilgi("")
    r.bilgi("    ✅ COZUM: J3 devreye SERI baglanan bir terminal; uzerine")
    r.bilgi("       'YUK DONUSU — BESLEME BAGLAMA' etiketi. Ayrica sont")
    r.bilgi("       kolunda bir sigorta (yuk akimina gore secilir) bu")
    r.bilgi("       senaryonun tamamini kapatir.")
    # ESP32 acisindan bu senaryonun en kotu hali A7'nin "32 V ciplak"
    # satiriyla AYNI devre: sont acilinca YUK_EKSI kaynak gerilimine
    # cikiyor ve R18+R38 uzerinden ADS'e biniyor. A7 orada 25 mA olctu —
    # ADS'in 10 mA sinirinin ustunde ama ESP32'nin bosta akiminin (40 mA)
    # altinda, yani 3V3 rayi YUKSELMIYOR. ESP32 guvende.
    kaydet("B7b", "Yuk terminaline (J3) besleme baglanmasi",
           "RS (sont) + R18",
           not_="dusuk degerli sontta sinirlayan tek sey kaynagin kendisi; "
                "sont kolunda SIGORTA sart. ADS icin en kotu hal A7'nin "
                "'32 V ciplak' satiriyla ayni — ESP32 guvende")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2d — ARIZA DEGIL, CALISMA SINIRI
#  "Sistem gercekten calisiyor mu" sorusunun ariza disi yarisi
# ═══════════════════════════════════════════════════════════════════════

def bolum2d(r):
    bolum(r, "BOLUM 2d — ARIZA DEGIL, CALISMA SINIRI (tamponun CM tavani)")
    r.bilgi("  B15'in ariza taramasi sirasinda cikan ama ariza OLMAYAN bir")
    r.bilgi("  bulgu: iki gerilim kanali da TAM OLCEKTE, LM358'in garantili")
    r.bilgi("  ortak-mod (CM) giris araliginin SINIRINDA calisiyor.")
    r.bilgi("")
    r.bilgi("  LM358'in CM tavani ureticiye ve sicakliga gore degisiyor:")
    r.bilgi(f"    TI, 25 C          : V+ - {T.LM358_CM_TAVAN_DUSUM_25C:.1f} V")
    r.bilgi(f"    onsemi            : V+ - {T.LM358_CM_TAVAN_DUSUM_ONSEMI:.1f} V")
    r.bilgi(f"    TI, tam sicaklik  : V+ - {T.LM358_CM_TAVAN_DUSUM_TAMSIC:.1f} V  <- tasarim icin bu")
    r.bilgi("")
    r.bilgi("  ⚠ Bu asilirsa parca OLMEZ ama veri sayfasi cikisin TANIMSIZ")
    r.bilgi("    oldugunu soyluyor — okuma sessizce yanlis olabilir.")
    r.bilgi("")
    r.bilgi(f"  {'kanal':<16} {'+5V rayi':>9} {'CM tavani':>10} "
            f"{'FS dugumu':>10} {'pay':>9} {'FS carpani':>11}")
    r.bilgi("  " + "-" * 70)
    en_dar = None
    for k in T.KANALLAR:
        # tam olcekte (simetrik menzilin ust ucunda) dugum gerilimi
        fs_dugum = T.VREF + k["fs_sim"] / k["N"]
        for vp in (5.00, 4.75):
            tavan = vp - T.LM358_CM_TAVAN_DUSUM_TAMSIC
            pay = tavan - fs_dugum
            # tavanin asildigi GIRIS gerilimi
            v_asma = T.VREF + (tavan - T.VREF) * k["N"]
            carpan = v_asma / k["fs_sim"]
            if en_dar is None or pay < en_dar[0]:
                en_dar = (pay, k["ad"], vp, v_asma, carpan)
            r.bilgi(f"  {k['ad']:<16} {vp:8.2f}V {tavan:9.3f}V "
                    f"{fs_dugum:9.3f}V {pay*1e3:8.0f}mV {carpan:10.2f}x")
    r.bilgi("")
    r.bilgi(f"  EN DAR HAL: {en_dar[1]} kanali, +5 V rayi {en_dar[2]:.2f} V ->")
    r.bilgi(f"  pay yalnizca {en_dar[0]*1e3:.0f} mV. CM tavani giriste "
            f"{en_dar[3]:.0f} V'ta,")
    r.bilgi(f"  yani tam olcegin yalnizca {en_dar[4]:.2f} katinda asiliyor.")
    r.bilgi("")
    r.kosul("  2d: her iki kanal da TIPIK (25 C) CM tavaninin altinda",
            all(T.VREF + k["fs_sim"] / k["N"]
                < 5.00 - T.LM358_CM_TAVAN_DUSUM_25C for k in T.KANALLAR),
            "25 C ve 5.00 V rayda sorun yok")
    r.kosul("  2d: 🔴 tam sicaklik + dusuk USB rayinda pay 50 mV'un ALTINA "
            "iniyor",
            en_dar[0] < 0.050,
            f"{en_dar[1]}, {en_dar[2]:.2f} V ray -> {en_dar[0]*1e3:.0f} mV pay")
    r.kosul("  2d: CM tavani tam olcegin 1.5 katindan ONCE asiliyor",
            en_dar[4] < 1.5,
            f"{en_dar[4]:.2f}x — yani %{(en_dar[4]-1)*100:.0f} asiri gerilimde "
            f"tampon garantili aralik disina cikiyor")
    r.bilgi("")
    _carpan = {}
    for k in T.KANALLAR:
        _tavan = 5.00 - T.LM358_CM_TAVAN_DUSUM_TAMSIC
        _carpan[k["kod"]] = (T.VREF + (_tavan - T.VREF) * k["N"]) / k["fs_sim"]
    r.bilgi("  ⚠ SASIRTICI: 'dusuk gerilim' kanali, 'yuksek gerilim'")
    r.bilgi("    kanalindan RELATIF olarak daha GUVENLI. Herkes 615 V")
    r.bilgi("    bacagina odaklaniyor ama 5.00 V rayda CM tavani:")
    r.bilgi(f"      NORMAL kanal : tam olcegin {_carpan['normal']:.2f} kati")
    r.bilgi(f"      HV kanal     : tam olcegin {_carpan['hv']:.2f} kati  <- daha dar")
    r.kosul("  2d: HV kanalinin CM payi NORMAL kanaldan dar",
            _carpan["hv"] < _carpan["normal"],
            f"{_carpan['hv']:.2f}x < {_carpan['normal']:.2f}x")
    r.bilgi("")
    r.bilgi("  COZUMLER (hicbiri B15 kapsaminda uygulanmadi):")
    r.bilgi("    1. +5 V rayini USB yerine REGULE bir kaynaktan al — 5.00 V")
    r.bilgi("       garanti edilirse pay 261 mV'a cikiyor.")
    r.bilgi("    2. Tamponlari MCP6002 (3.3 V RRIO) yap: CM araligi raydan")
    r.bilgi("       raya, yani sorun tamamen kalkiyor. Ustelik TI'in 1 numarali")
    r.bilgi("       ADC koruma onerisini de saglar (op-amp = ADC beslemesi) ve")
    r.bilgi("       BOLUM 7/F1'deki seri direnc gereksinimini de kaldirir.")
    r.bilgi("    3. Tamponlari +12 V'tan besle: CM tavani 10 V'a cikar, ama")
    r.bilgi("       o zaman doymus cikis 10.65 V olur ve ADS'i korumak icin")
    r.bilgi("       seri direnc 1K yerine ~7K gerekir.")
    r.bilgi("")
    r.bilgi("  🌟 2. secenek (MCP6002) UC sorunu birden cozuyor. Kullaniciya")
    r.bilgi("     sorulmali: 2 adet MCP6002-I/P (DIP-8) alinacak mi?")

    alt(r, "2d-b · Skop kanalinin NEGATIF kapsamı YOK")
    r.bilgi("      Skop bolucusu (R20/R23) GND referansli — gerilim")
    r.bilgi("      kanallarindaki gibi VREF ofseti YOK (netlist: R23.2 -> GND).")
    r.bilgi("      ESP32'nin ADC'si de tek yonlu.")
    r.bilgi("")
    r.bilgi("      Sonuc: negatif girislerin TAMAMI D2 tarafindan kirpiliyor")
    r.bilgi(f"      ve GPIO4 {-0.3:.1f} V civarinda tutuluyor. Skop kanali")
    r.bilgi(f"      0 .. {T.ESP_ADC_ETKIN_UST*T.SKOP_N:.1f} V arasi TEK YONLU bir kanal.")
    # 🔴 B20 (2026-09-10): burada `True` ile "skop kanali CIFT YONLU DEGIL"
    # yaziyordu. B19 (2026-09-09) tam da bunu DEGISTIRDI — bolucunun alt ucu
    # GND yerine VREF'e baglandi. Yani iddia B19'dan beri YANLISTI ve sart
    # `True` oldugu icin zincir bunu hic gormedi. Artik SEMADAN sinaniyor.
    r.kosul("      2d-b: skop kanali CIFT YONLU (B19'dan beri)",
            T.SKOP_ALT_UC_VREF and T.SKOP_MENZIL_EKSI < -50.0,
            f"{T.SKOP_MENZIL_EKSI:.1f} .. +{T.SKOP_MENZIL_ARTI:.1f} V — "
            f"bolucunun alt ucu VREF'te; eksi taraf artik olculebiliyor")
    r.bilgi("")
    r.bilgi("      ⚠ Kart 'cift yonlu on uc' diye tasarlandi ama bu YALNIZCA")
    r.bilgi("        ADS kanallari icin gecerli. Skop (GPIO4) ve hizli akim")
    r.bilgi("        (GPIO5) yollarindan hizli akim VREF ofsetli — o cift")
    r.bilgi("        yonlu; skop DEGIL. SMPS anahtarlama dugumu genelde")
    r.bilgi("        pozitif oldugu icin pratikte sorun cikmayabilir, ama")
    r.bilgi("        bobin akimi ters donen bir olcumde skop kanali KOR.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2e — A10/B2b · DENETIMIN BULDUGU IKI EKSIK SENARYO
# ═══════════════════════════════════════════════════════════════════════

def bolum2e(r):
    alt(r, "A10 · 🔴 ENDUKTIF YUK KESILMESI (flyback) — sont kolunun")
    r.bilgi("       en olasi zorlanmasi")
    r.bilgi("")
    r.bilgi("      Sont YUKUN DONUS kolunda (netlist: /YUK_EKSI = J3.1 =")
    r.bilgi("      R18.1 = RS.1, RS.2 = GND) — yani kart yuk akiminin")
    r.bilgi("      TAMAMINI tasiyor. Kullanicinin alani SMPS/inverter, yani")
    r.bilgi("      yuk neredeyse HER ZAMAN endüktif. Simdiye kadarki butun")
    r.bilgi("      sont senaryolari dirençli/DC kaynak varsayiyordu.")
    r.bilgi("")
    r.bilgi("      IKI AYRI OLAY VAR — karistirilmamali:")
    r.bilgi("")

    # ── (a) parazitik endüktans x di/dt — HER anahtarlamada olan
    r.bilgi("      (a) HER ANAHTARLAMADA: kablo/sont parazitik endüktansi")
    r.bilgi("          uzerinde L·di/dt. Bu bir ariza degil, NORMAL calisma.")
    r.bilgi("")
    L_PARAZIT = 100e-9          # ~10 cm kablo + sont bacaklari, tipik
    r.bilgi(f"      {'di/dt':>10} {'L·di/dt':>10} {'SONT_P tepe':>12} "
            f"{'ADS akimi':>11}  yargi")
    r.bilgi("      " + "-" * 58)
    a10 = {}
    for didt in (0.1e6, 1e6, 10e6):
        vspike = L_PARAZIT * didt
        net = f"""* parazitik L uzerinde di/dt — SONT_P'ye binen ani gerilim
{D_ESD}
{AYARLAR}
Vs kaynak 0 PWL(0 0 1u 0 1.01u {-vspike} 3u {-vspike} 3.01u 0 20u 0)
Lp kaynak yuk {L_PARAZIT}
Rsont yuk 0 {min(T.SONT_SECENEK)}
R18 yuk sp {T.SONT_KELVIN_R}
R38 sp spa {T.ADS_SERI_R}
C4 sp sn {T.SONT_C}
R19 0 sn {T.SONT_KELVIN_R}
R39 sn sna {T.ADS_SERI_R}
C18 spa sna {T.ADS_AKIM_C}
Rsna sna 0 1G
V33 v33 0 DC {T.VDD}
Vam 0 esd_a DC 0
Desd_alt esd_a spa DESD
Desd_ust spa v33 DESD
.control
tran 10n 20u 0 10n
wrdata tr.txt v(spa) i(Vam)
.endc
.end
"""
        tr = tara(net, f"a10_didt_{didt/1e6:.0f}", "tr.txt")
        vmin = min(x[1] for x in tr)
        imax = max(abs(x[2]) for x in tr)
        a10[didt] = (vspike, vmin, imax)
        yargi = ("guvenli" if vmin >= T.ADS_MUTLAK_GIRIS_ALT
                 else ("sinir asimi" if imax < T.ADS_TASARIM_AKIM_HEDEFI
                       else "AKIM da asiliyor"))
        r.bilgi(f"      {didt/1e6:8.1f} A/us {vspike:8.2f} V {vmin:10.3f} V "
                f"{imax*1e3:9.3f} mA  {yargi}")
    r.bilgi("")
    r.bilgi(f"      (L = {L_PARAZIT*1e9:.0f} nH varsayimi: ~10 cm kablo + sont")
    r.bilgi("       bacaklari. Kablo uzarsa dogrusal olarak buyur.)")
    _en = a10[10e6]
    r.kosul("      A10a: 10 A/us'te bile SONT_P mutlak sinirin ICINDE kaliyor",
            _en[1] >= T.ADS_MUTLAK_GIRIS_ALT,
            f"{_en[1]:.3f} V >= {T.ADS_MUTLAK_GIRIS_ALT:+.1f} V — C18 ve "
            f"R18+R38 tepeyi yutuyor; L·di/dt {_en[0]:.1f} V olmasina ragmen")
    r.kosul("      A10a: kelepce akimi TI'in tasarim hedefinin altinda",
            _en[2] < T.ADS_TASARIM_AKIM_HEDEFI,
            f"{_en[2]*1e3:.3f} mA < {T.ADS_TASARIM_AKIM_HEDEFI*1e3:.0f} mA")
    r.bilgi("")
    r.bilgi("      → IYI HABER: normal anahtarlama zararsiz. Sasirtici olan,")
    r.bilgi(f"        L·di/dt'nin {_en[0]:.1f} V olmasina ragmen ADS pininin")
    r.bilgi(f"        yalnizca {_en[1]:.2f} V'a inmesi.")
    r.bilgi(f"        B16'dan sonra tepeyi yutan sey C4 degil (artik "
            f"{T.SONT_C*1e9:.0f} nF),")
    r.bilgi(f"        C18 ({T.ADS_AKIM_C*1e6:.2f} uF) ve R18+R38 ({T.SONT_KELVIN_R+T.ADS_SERI_R:.0f} ohm).")
    r.bilgi("        Yine de KABLO KISA olmali; 1 m'lik bir yuk kablosu")
    r.bilgi("        (~1 uH) ayni di/dt'de 10 kat buyuk tepe verir.")

    # ── (b) yukun CANLIYKEN sokulmesi — asil ariza
    r.bilgi("")
    r.bilgi("      (b) ARIZA: endüktif yuk AKIM AKARKEN sokuluyor.")
    r.bilgi("          Bobin akimi devam etmek istiyor; onune cikan tek yol")
    r.bilgi("          R18 + R38 uzerinden ADS'in ESD diyodu.")
    r.bilgi("")
    r.bilgi(f"      {'bobin akimi':>12} {'sokulme yeri':>16} "
            f"{'ADS akimi':>11}  yargi")
    r.bilgi("      " + "-" * 52)
    rtop = T.SONT_KELVIN_R + T.ADS_SERI_R
    for iyuk in (0.1, 1.0, 5.0):
        # Bobin akimi sabit akim kaynagi gibi davranir; kart yolu 1100 R.
        # Akim ya kart yolundan akar ya da sokulen kontakta ARK olusur.
        i_kart = min(iyuk, (T.VDD + T.ADS_ESD_VF) / 1.0)   # ust sinir yok
        # gercek sinir: ADS diyodu iletince gerilim kelepceleniyor,
        # bobin geri kalan akimi ARK olarak bosaltiyor
        r.bilgi(f"      {iyuk:10.1f} A {'J3 klemensi':>16} "
                f"{'ARK':>9}   kart yolu 1100 R, bobin {iyuk:.1f} A istiyor")
    r.bilgi("")
    r.bilgi("      🔴 KRITIK GERCEK: bobin, kartin 1100 ohm'luk yolundan")
    r.bilgi("         gecebilecek akimdan (birkac mA) KAT KAT fazlasini")
    r.bilgi("         istiyor. Yani akim karttan AKMAZ — sokulen kontakta")
    r.bilgi("         ARK olusur ve gerilim ark gerilimine (~15-20 V)")
    r.bilgi("         kelepcelenir. Kart bu gerilimi gorur:")
    v_ark = 20.0
    i_ark = (v_ark - T.ADS_ESD_VF) / rtop
    r.bilgi(f"           ark gerilimi ~{v_ark:.0f} V -> ADS akimi "
            f"{i_ark*1e3:.1f} mA")
    _i_ark_ham = (v_ark - T.ADS_ESD_VF) / T.SONT_KELVIN_R
    _v_esik = T.ADS_GIRIS_AKIM_MAKS * rtop + T.ADS_ESD_VF
    r.kosul("      A10b: R38 ark akimini 10 kattan fazla azaltiyor",
            _i_ark_ham / i_ark > 10,
            f"{_i_ark_ham*1e3:.0f} mA -> {i_ark*1e3:.1f} mA "
            f"({_i_ark_ham/i_ark:.1f}x)")
    r.kosul("      A10b: 🔴 AMA ARK GERILIMINDE ADS SINIRI YINE DE ASILIYOR",
            i_ark > T.ADS_GIRIS_AKIM_MAKS,
            f"{i_ark*1e3:.1f} mA > {T.ADS_GIRIS_AKIM_MAKS*1e3:.0f} mA — "
            f"sinir {_v_esik:.1f} V'luk bir arkta asiliyor, hava arki ise "
            f"en az ~15 V")
    r.bilgi("")
    r.bilgi("      → B15'in KAPATAMADIGI tek bilesen senaryosu bu. R38 riski")
    r.bilgi("        10 kattan fazla azaltiyor ama ELEMIYOR. Cozum donanimda")
    r.bilgi("        degil KULLANIMDA: endüktif yuke serbest gecis diyodu.")
    r.bilgi("")
    r.bilgi("      ✅ ONERI: endüktif yuk olcerken yukun uzerine SERBEST")
    r.bilgi("         GECIS (freewheel) diyodu konmali — bu zaten guc")
    r.bilgi("         elektroniginin standart kurali, ama olcum karti")
    r.bilgi("         kullanilirken UNUTULMASI cok kolay. Kutu etiketine")
    r.bilgi("         yazilmali.")
    kaydet("A10", "Endüktif yuk akim akarken sokuluyor",
           "U6 (ADS1115 #1)",
           not_=f"bobin kartin {rtop:.0f} ohm'luk yolundan gecemez; ark "
                f"kontakta olusur. ~{v_ark:.0f} V arkta ADS akimi "
                f"{i_ark*1e3:.1f} mA (R38 olmasa {_i_ark_ham*1e3:.0f} mA) — "
                f"{T.ADS_GIRIS_AKIM_MAKS*1e3:.0f} mA sinirinin USTUNDE. "
                f"FREEWHEEL DIYODU sart")

    # ── B2b: USB TAKILI ama +-12 V YOK — her programlamada olan hal
    alt(r, "B2b · USB TAKILI, +-12 V YOK — HER PROGRAMLAMADA olan hal")
    r.bilgi("      Denetim bunu yakaladi: B2 'tersi' halini kapsamiyordu.")
    r.bilgi("      Oysa kart her programlanisinda tam bu durumda:")
    r.bilgi("      USB takili (+5 V ve +3V3 var, VREF calisiyor) ama 24 V")
    r.bilgi("      kaynak kapali (+-12 V yok).")
    r.bilgi("")
    r.bilgi("      TL072'ler (U5, U8) BESLEMESIZ ama girislerinde sinyal var:")
    r.bilgi("        U8A: R27/R29 (10K) uzerinden VREF'e bakiyor")
    r.bilgi("        U5A: skop bolucusu uzerinden J4'e bakiyor")
    r.bilgi("")
    i_u8 = (T.VREF - 0.5) / T.HIZLI_RG
    r.bilgi(f"      U8A giris kelepce akimi: (VREF - 0.5)/10K = "
            f"{i_u8*1e3:.3f} mA")
    r.kosul("      B2b: U8A kelepce akimi TL072'nin mutlak sinirinin altinda",
            i_u8 < T.TL072_GIRIS_AKIM_MAKS,
            f"{i_u8*1e3:.3f} mA < {T.TL072_GIRIS_AKIM_MAKS*1e3:.0f} mA "
            f"(%{i_u8/T.TL072_GIRIS_AKIM_MAKS*100:.1f})")
    r.bilgi("")
    r.bilgi("      Skop girisinde sinyal varken (J4'e bagli devre canli):")
    r.bilgi(f"      {'J4 girisi':>10} {'bolucu dugumu':>15} "
            f"{'U5A kelepce akimi':>18}  yargi")
    r.bilgi("      " + "-" * 54)
    z_sk = T.SK_R * 2 + (T.SKOP_RUST * T.SKOP_RALT
                         / (T.SKOP_RUST + T.SKOP_RALT))
    en_u5 = 0.0
    for vj4 in (12.0, 48.0, 160.0):
        dug = vj4 / T.SKOP_N
        i_u5 = max(0.0, (dug - 0.5) / z_sk)
        en_u5 = max(en_u5, i_u5)
        r.bilgi(f"      {vj4:8.0f} V {dug:13.2f} V {i_u5*1e3:15.3f} mA  "
                f"{'ok' if i_u5 < T.TL072_GIRIS_AKIM_MAKS else 'ASIYOR'}")
    r.kosul("      B2b: skop girisi canliyken de TL072 kelepce akimi guvenli",
            en_u5 < T.TL072_GIRIS_AKIM_MAKS,
            f"en fazla {en_u5*1e3:.3f} mA < "
            f"{T.TL072_GIRIS_AKIM_MAKS*1e3:.0f} mA — Sallen-Key'in "
            f"2x{T.SK_R/1e3:.1f}K'si sinirliyor")
    r.bilgi("")
    r.bilgi("      ⚠ TI'in kurali: beslemesiz bir op-amp'in girisine sinyal")
    r.bilgi("        uygulanabilir, AMA akim 10 mA ile sinirlanmak KAYDIYLA.")
    r.bilgi("        Burada iki yolda da sinir bol bol saglaniyor.")
    r.bilgi("      ⚠ ESKI die TL072'de (giris kelepcesi YOK) bu sinir hic")
    r.bilgi("        yoktu; TI 'giris gerilimi beslemenin buyuklugunu asmasin'")
    r.bilgi("        diyordu. Alinacak TL072CP'nin hangi die oldugu")
    r.bilgi("        BILINMIYOR — ama akim her iki halde de guvenli.")
    kaydet("B2b", "USB takili, +-12 V yok (her programlamada)", "",
           not_=f"TL072 girisleri beslemesizken kelepce akimi en fazla "
                f"{max(i_u8, en_u5)*1e3:.2f} mA — TI'in 10 mA sinirinin cok "
                f"altinda. Bu hal HER programlamada yasaniyor ve zararsiz")

# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — B · BESLEME ARIZALARI (24 V + LM358 orta nokta)
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r):
    bolum(r, "BOLUM 3 — B · BESLEME ARIZALARI  (24 V + LM358 orta nokta)")
    r.bilgi("  DEVIR 5.12.23 +-12 V rayini '24 V + LM358 orta nokta tamponu'")
    r.bilgi("  ile cozdu. Senaryolar bu topolojiye gore kuruldu.")

    # ── B4a: orta nokta yuk butcesi — DEVIR'in sayisi YANLIS
    alt(r, "B4a · Orta nokta YUK BUTCESI — DEVIR'in 5.6 mA'i yanlis sayilmis")
    r.bilgi("      DEVIR 5.12.23: '+-12 V rayi 5.6 mA, 2x TL072' ve bunu orta")
    r.bilgi("      nokta yuku sayiyor. Op-amp BOSTA AKIMI V+ -> V- DOGRUDAN")
    r.bilgi("      akar; orta noktaya HIC degmez. Orta noktayi yukleyen:")
    r.bilgi("        (a) GND'ye referansli cikis akimlari (kelepce yollari)")
    r.bilgi("        (b) +12'den beslenip GND'ye donen regulatorler")
    r.bilgi("")
    tl072_bosta = 4 * T.TL072_IQ_MAKS
    r.bilgi(f"      2x TL072 bosta akimi (4 kesit x {T.TL072_IQ_MAKS*1e3:.1f} mA "
            f"maks) = {tl072_bosta*1e3:.1f} mA")
    r.bilgi("        -> orta noktaya katkisi 0.0 mA  (raydan raya akiyor)")
    r.bilgi("")
    r.bilgi(f"      {'kaynak':<38} {'orta nokta akimi':>18}")
    r.bilgi("      " + "-" * 57)
    kaynaklar = [
        ("2x TL072 bosta akimi (raydan raya)", 0.0),
        ("Skop kelepcesi (U5A cikisi -12'ye oturur)",
         T.ORTA_NOKTA_KELEPCE_KANAL_NEG),
        ("Hizli akim kelepcesi (U5B ayni)",
         T.ORTA_NOKTA_KELEPCE_KANAL_NEG),
        ("7805 -> analog +5 V (bosta + 1.4 mA yuk)", T.ORTA_NOKTA_YUK_7805),
    ]
    toplam_normal = T.ORTA_NOKTA_YUK_7805
    toplam_ariza = sum(x for _, x in kaynaklar)
    for ad, i in kaynaklar:
        r.bilgi(f"      {ad:<38} {i*1e3:15.2f} mA")
    r.bilgi("      " + "-" * 57)
    r.bilgi(f"      {'NORMAL calismada toplam':<38} {toplam_normal*1e3:15.2f} mA")
    r.bilgi(f"      {'Kelepce arizasinda toplam':<38} {toplam_ariza*1e3:15.2f} mA")
    r.bilgi(f"      {'ESP32 dusurucusu +12den beslenirse':<38} "
            f"{T.ORTA_NOKTA_YUK_ESP*1e3:15.2f} mA")
    r.bilgi("")
    r.bilgi("      LM358'in orta nokta olarak surebilecegi akim (veri sayfasi):")
    r.bilgi(f"        kaynak (source) : en az {T.LM358_SOURCE_MIN*1e3:.0f} mA")
    r.bilgi(f"        cekme  (sink)   : en az {T.LM358_SINK_MIN*1e3:.0f} mA "
            f"(0..70 C'de yalnizca {T.LM358_SINK_MIN_SICAK*1e3:.0f} mA)")
    r.bilgi("")
    # DEVIR 5.6 mA diyordu; gercek orta nokta yuku 7805 kolu.
    # Fark, TL072'nin bosta akiminin ORTA NOKTAYA katkisinin sifir olmasi.
    _devir = 5.6e-3
    r.kosul("      B4a: DEVIR'in '5.6 mA orta nokta yuku' sayisi YANLIS",
            abs(toplam_normal - _devir) / _devir > 0.10,
            f"DEVIR {_devir*1e3:.1f} mA dedi, gercek {toplam_normal*1e3:.1f} mA "
            f"(%{abs(toplam_normal-_devir)/_devir*100:.0f} fark). TL072'nin "
            f"{tl072_bosta*1e3:.0f} mA'i raydan raya akiyor, orta noktaya 0")
    r.kosul("      B4a: 🔴 NORMAL calismada bile SICAK cekme garantisi asiliyor",
            toplam_normal > T.LM358_SINK_MIN_SICAK,
            f"{toplam_normal*1e3:.1f} mA > {T.LM358_SINK_MIN_SICAK*1e3:.0f} mA "
            f"(0..70 C garantisi) — 25 C'de "
            f"{T.LM358_SINK_MIN*1e3:.0f} mA ile calisir, isininca degil")
    r.kosul("      B4a: 25 C garantisi ise NORMAL yuku karsiliyor",
            toplam_normal < T.LM358_SINK_MIN,
            f"{toplam_normal*1e3:.1f} mA < {T.LM358_SINK_MIN*1e3:.0f} mA — "
            f"pay yalnizca {T.LM358_SINK_MIN/toplam_normal:.1f}x")
    r.kosul("      B4a: 🔴 ESP32 dusurucusu +12'den beslenirse LM358 YETMEZ",
            T.ORTA_NOKTA_YUK_ESP > T.LM358_SINK_MIN,
            f"{T.ORTA_NOKTA_YUK_ESP*1e3:.0f} mA > {T.LM358_SINK_MIN*1e3:.0f} mA "
            f"({T.ORTA_NOKTA_YUK_ESP/T.LM358_SINK_MIN:.0f} kat) — ESP32 USB'den "
            f"beslenmeli ya da TLE2426 kullanilmali")
    r.kosul("      B4a: kelepce arizasinda sicak garanti sinirinin ustunde",
            toplam_ariza > T.LM358_SINK_MIN_SICAK,
            f"{toplam_ariza*1e3:.1f} mA > {T.LM358_SINK_MIN_SICAK*1e3:.0f} mA — "
            f"pay yok")

    # ── B4b: KAPASITIF YUK — kararlilik
    alt(r, "B4b · 🔴 Orta nokta tamponu KAPASITIF YUKTE KARARSIZ")
    r.bilgi("      LM358 veri sayfasi Application Information: EN KOTU baglanti")
    r.bilgi("      olan evirmeyen BIRIM KAZANC icin kapasitif yuk siniri")
    r.bilgi(f"      yalnizca {T.LM358_CL_MAKS*1e12:.0f} pF. Orta nokta tamponu "
            f"TAM O BAGLANTI.")
    r.bilgi("")
    cl = T.DEKUPLAJ_ADET * T.DEKUPLAJ_BIR
    r.bilgi(f"      Semadaki ayirma kondansatorleri C9..C15: "
            f"{T.DEKUPLAJ_ADET} x {T.DEKUPLAJ_BIR*1e9:.0f} nF = {cl*1e9:.0f} nF")
    r.bilgi("      Hepsi rayla GND arasinda; GND = tamponun CIKISI.")
    r.bilgi("")
    r.kosul("      B4b: kapasitif yuk veri sayfasi sinirinin cok uzerinde",
            cl > T.LM358_CL_MAKS,
            f"{cl*1e9:.0f} nF / {T.LM358_CL_MAKS*1e12:.0f} pF = "
            f"{cl/T.LM358_CL_MAKS:.0f} kat")
    r.kosul("      B4b: tahmini osilasyon esiginin de uzerinde",
            cl > T.LM358_CL_OSILASYON_TAHMIN,
            f"{cl*1e9:.0f} nF > {T.LM358_CL_OSILASYON_TAHMIN*1e9:.1f} nF")
    r.bilgi("")
    r.bilgi("      COZUM (BOLUM 7): 10 R yalitim direnci ya da TLE2426.")

    # ── B3: ters polarite
    alt(r, "B3 · +-12 V konnektoru TERS takilirsa")
    r.bilgi("      LM358 veri sayfasi bunu ACIKCA olumcul sayiyor ve")
    r.bilgi("      mekanizmayi adlandiriyor: ters besleme bir IC diyodu ILERI")
    r.bilgi("      kutuplar -> 'unlimited current surge' -> 'fusing of")
    r.bilgi("      internal conductors'.")
    r.bilgi("")
    _asim = T.RAY_24V / abs(T.LM358_GIRIS_MUTLAK_ALT)
    r.bilgi(f"      Ters takmada gorulen -{T.RAY_24V:.0f} V  ·  mutlak alt sinir "
            f"{T.LM358_GIRIS_MUTLAK_ALT:+.1f} V")
    r.kosul("      B3: ters polarite mutlak alt siniri kat kat asiyor — "
            "parcalar OLUR",
            _asim > 50, f"{_asim:.0f} kat "
                        f"(-{T.RAY_24V:.0f} V vs {T.LM358_GIRIS_MUTLAK_ALT:+.1f} V)")
    r.bilgi("")
    r.bilgi("      ⚠ TVS ILE KORUNAMAZ: 24 V rayi tutan hicbir standart SMBJ")
    r.bilgi("        parcasi LM358'in 32 V mutlak maksimumunun ALTINDA")
    r.bilgi("        kelepceleyemiyor (SMBJ24A: 38.9 V @ 15.4 A -> 6.9 V YUKARIDA).")
    r.bilgi("      ✅ DOGRU COZUM: MEKANIK ANAHTARLAMA (keyed konnektor).")
    r.bilgi("         Sifir gerilim dusumu, sifir maliyet, sifir yeni ariza modu.")
    r.bilgi(f"      ✅ Ikinci hat: 50 mA sigorta (+-12 V yuku "
            f"{tl072_bosta*1e3:.0f} mA maks -> "
            f"{50e-3/tl072_bosta:.0f}x pay)")
    kaydet("B3", "+-12 V konnektoru ters takilmasi", "U5 + U8 (2x TL072)",
           not_="veri sayfasi 'fusing of internal conductors' diyor; "
                "TVS ile korunamaz, MEKANIK ANAHTARLAMA sart")

    # ── B5: 24 V kaynak yalitimsiz
    alt(r, "B5 · 24 V kaynak YALITIMSIZ -> orta nokta topraga kisa")
    r.bilgi("      24 V kaynagin eksi ucu sebeke topragina bagliysa ve kart da")
    r.bilgi("      USB ile PC'ye bagliysa, kart GND'si (= orta nokta) toprakla")
    r.bilgi("      KISA DEVRE olur. Tampon 12 V'luk farki surmeye calisir.")
    r.bilgi("")
    for ad, isc, theta in (("tipik / DIP-8", T.LM358_ISC, T.LM358_THETA_DIP8),
                           ("maksimum / DIP-8", T.LM358_ISC_MAKS,
                            T.LM358_THETA_DIP8),
                           ("maksimum / SOIC-8", T.LM358_ISC_MAKS,
                            T.LM358_THETA_SOIC8)):
        p = 12.0 * isc
        tj = 25.0 + p * theta
        r.bilgi(f"      I_SC {ad:<18} {isc*1e3:5.1f} mA -> P {p*1e3:5.0f} mW "
                f"-> Tj {tj:5.0f} C  "
                f"{'YASAR' if tj < T.LM358_TJ_MAKS else 'OLUR'}")
    p_dip = 12.0 * T.LM358_ISC_MAKS
    tj_dip = 25.0 + p_dip * T.LM358_THETA_DIP8
    tj_soic = 25.0 + p_dip * T.LM358_THETA_SOIC8
    r.bilgi("")
    r.kosul("      B5: DIP-8 govde bu kisa devreden SAG CIKIYOR",
            tj_dip < T.LM358_TJ_MAKS,
            f"Tj {tj_dip:.0f} C < {T.LM358_TJ_MAKS:.0f} C — delikli plaket "
            f"(DIP) burada SMD'den DAHA saglam")
    r.kosul("      B5: SOIC govde de sag cikiyor ama payi cok daha dar",
            tj_soic < T.LM358_TJ_MAKS
            and (T.LM358_TJ_MAKS - tj_soic) < (T.LM358_TJ_MAKS - tj_dip) / 2,
            f"SOIC Tj {tj_soic:.0f} C (pay {T.LM358_TJ_MAKS-tj_soic:.0f} C) vs "
            f"DIP {tj_dip:.0f} C (pay {T.LM358_TJ_MAKS-tj_dip:.0f} C)")
    r.bilgi("")
    r.bilgi("      ⚠ Bir onceki surum burada 'SOIC OLURDU' diyordu; o yargi")
    r.bilgi("        kaynaksiz termal direnclere (120/200 K/W) dayaniyordu.")
    r.bilgi(f"        Gercek degerler SLOS068AB 5.4'ten: PDIP "
            f"{T.LM358_THETA_DIP8:.1f} C/W, SOIC {T.LM358_THETA_SOIC8:.1f} C/W.")
    r.bilgi("        Ikisi de sag cikiyor — DIP'in payi iki katindan fazla.")
    r.bilgi("")
    r.bilgi("      🔴 ASIL TEHLIKE AKIM DEGIL, REFERANS: kart GND'si artik")
    r.bilgi("         sebeke topragina baglandi. 615 V bolucusunun donusu de")
    r.bilgi("         oraya gidiyor — bu, D1 senaryosunun ta kendisi.")
    r.bilgi("")
    r.bilgi("      ✅ OLCUM: 24 V kaynagin eksi ucu ile sebeke topragi arasina")
    r.bilgi("         ohmmetre. Birkac ohm okuyorsa kaynak YALITIMSIZ.")
    # PC RISKI YOK: kart GND'si USB uzerinden ZATEN toprakta. 24 V'un
    # yalitimsiz olmasi yeni bir toprak baglantisi EKLEMIYOR, yalnizca
    # orta nokta tamponunu kisa devre ediyor. USB GND'sinden gecen akim
    # tamponun kendi kisa devre akimi kadar (40-60 mA) — PC icin zararsiz.
    kaydet("B5", "24 V kaynak yalitimsiz + USB bagli",
           "" if tj_dip < T.LM358_TJ_MAKS
           else "U3 orta nokta tamponu (soketli LM358)",
           not_=f"DIP-8'de Tj {tj_dip:.0f} C, SOIC'te {tj_soic:.0f} C — "
                f"ikisi de {T.LM358_TJ_MAKS:.0f} C sinirinin altinda, parca "
                f"YASIYOR. PC'ye akan "
                f"{T.LM358_ISC_MAKS*1e3:.0f} mA zararsiz; asil sonuc raylarin "
                f"+24/0 V'a kaymasi ve olcumun bozulmasi")

    # ── B1: guc sirasi — +-12 V var, +3V3 yok
    alt(r, "B1 · 🔴 +-12 V VAR, +3V3 YOK — kelepceler 3V3 rayini GERI BESLIYOR")
    r.bilgi("      En olasi hali: USB cikarilmis (ESP32 ve ADS beslemesiz) ama")
    r.bilgi("      24 V kaynak takili. Bu, 'izolasyon icin USB'yi cikar'")
    r.bilgi("      talimatinin DOGRUDAN sonucu — NADIR degil, TAVSIYE EDILEN")
    r.bilgi("      kullanim.")
    r.bilgi("")
    net = f"""* 3V3 yok, TL072 cikislari raya oturmus -> BAT85'ler 3V3'u besliyor
{D_BAT85}
{AYARLAR}
Vs1 cik1 0 DC {T.TL072_CIKIS_TAVAN}
Vs2 cik2 0 DC {T.TL072_CIKIS_TAVAN}
R26 cik1 gpio1 {T.R_SERI}
R33 cik2 gpio2 {T.R_SERI}
Vam1 kel1 ray DC 0
D1 gpio1 kel1 DBAT85
Vam2 kel2 ray DC 0
D3 gpio2 kel2 DBAT85
* B18/F12: R41 bosaltma direnci — kelepce akimina KALICI yol.
Rbos ray 0 {T.BOSALTMA_R_3V3}
* R1 + TL431 kolu. TL431 TEK YONLU (yalnizca sink) — B18 bolum 0b:
* ideal gerilim kaynagi modeli onu akim VERIR gosteriyordu.
R1 ray tlk1 {T.R1_TL431}
R2 tlk1 vtap {T.VREF_RA}
R3 vtap 0 {T.VREF_RB}
Btl tlk1 0 I = 0.5*((V(tlk1)-{T.TL431_V})+sqrt((V(tlk1)-{T.TL431_V})*(V(tlk1)-{T.TL431_V})+1e-8))/0.2
.control
op
print v(ray) v(gpio1) i(Vam1) i(Vam2)
.endc
.end
"""
    d = op(net, "b1_geri")
    ray = d.get("v(ray)", 0.0)
    # B18 oncesi hali: 2.7K seri direnc, bosaltma direnci YOK
    net_eski = (net.replace(f"R26 cik1 gpio1 {T.R_SERI}",
                            f"R26 cik1 gpio1 {T.R_SERI_ESKI}")
                   .replace(f"R33 cik2 gpio2 {T.R_SERI}",
                            f"R33 cik2 gpio2 {T.R_SERI_ESKI}")
                   .replace(f"Rbos ray 0 {T.BOSALTMA_R_3V3}",
                            f"Rbos ray 0 {ACIK}"))
    ray_eski = op(net_eski, "b1_geri_eski").get("v(ray)", 0.0)
    igeri = abs(d.get("i(vam1)", 0.0)) + abs(d.get("i(vam2)", 0.0))
    r.bilgi(f"      Iki TL072 cikisi da +{T.TL072_CIKIS_TAVAN:.1f} V'a oturdugunda:")
    r.bilgi(f"        3V3 rayina enjekte edilen akim : {igeri*1e3:.2f} mA")
    r.bilgi(f"        3V3 rayinin oturdugu gerilim   : {ray:.3f} V")
    r.bilgi(f"        ESP32 mutlak pin siniri        : {T.ESP_MUTLAK_PIN_UST:.2f} V")
    r.bilgi("")
    r.bilgi(f"      B18/F12 ONCESI ayni senaryo: ray {ray_eski:.3f} V, "
            f"pay {(T.ESP_MUTLAK_PIN_UST-ray_eski)*1e3:.0f} mV")
    r.bilgi("      (2.7K seri direnc + bosaltma direnci yok. O halde rayi")
    r.bilgi("       tutan TEK sey R1 + TL431 koluydu — yani ariza aninda")
    r.bilgi("       TL431 istemeden 3V3 rayinin asiri gerilim sontu oluyordu.)")
    r.kosul("      B1: B18/F12 ONCESI pay kabul edilemezdi",
            (T.ESP_MUTLAK_PIN_UST - ray_eski) < 0.05,
            f"{(T.ESP_MUTLAK_PIN_UST-ray_eski)*1e3:.0f} mV — kusur gercekti")
    r.kosul("      B1: B18/F12 SONRASI ray ESP32 sinirinin cok altinda",
            ray <= T.ESP_MUTLAK_PIN_UST - 1.0,
            f"{ray:.3f} V, pay {(T.ESP_MUTLAK_PIN_UST-ray)*1e3:.0f} mV "
            f"({(T.ESP_MUTLAK_PIN_UST-ray)/(T.ESP_MUTLAK_PIN_UST-ray_eski):.0f} "
            f"kat iyilesme)")
    r.kosul("      B1: enjeksiyon akimi ESP32 latch-up esiginin cok altinda",
            igeri < T.ESP_LATCHUP_AKIM,
            f"{igeri*1e3:.2f} mA << {T.ESP_LATCHUP_AKIM*1e3:.0f} mA (JESD78)")
    r.bilgi("")
    r.bilgi("      🔴 B18 ONCESI KURTULUS TESADUFIYDI: TL431 bu tasarimda")
    r.bilgi("         referans olmak icin var; 3V3 rayinin asiri gerilim")
    r.bilgi("         sontu olmasi PLANLANMIS bir islev DEGIL.")
    _btl = ("Btl tlk1 0 I = 0.5*((V(tlk1)-{v})+sqrt((V(tlk1)-{v})*"
            "(V(tlk1)-{v})+1e-8))/0.2").format(v=T.TL431_V)
    net2 = net.replace(_btl, f"Rtl tlk1 0 {ACIK}")
    ray2 = op(net2, "b1_geri_tl431yok").get("v(ray)", 0.0)
    ray2e = op(net_eski.replace(_btl, f"Rtl tlk1 0 {ACIK}"),
               "b1_eski_tl431yok").get("v(ray)", 0.0)
    r.bilgi(f"         TL431 acik devre olsaydi B18 oncesi ray "
            f"{ray2e:.2f} V'a tirmaniyordu ({ray2e/T.ESP_MUTLAK_PIN_UST:.1f}x "
            f"sinir) — ESP32 olurdu.")
    r.kosul("      B1: B18 oncesi TL431 acik devre ESP32'yi OLDURURDU",
            ray2e > T.ESP_MUTLAK_PIN_UST,
            f"{ray2e:.2f} V > {T.ESP_MUTLAK_PIN_UST:.2f} V")
    r.kosul("      B1: R41 ile kurtulus TL431'e BAGLI DEGIL",
            abs(ray2 - ray) < 1e-3,
            f"TL431 var {ray:.3f} V · yok {ray2:.3f} V — bosaltma direnci "
            f"rayi 2.495 V'un altinda tuttugu icin TL431 hic iletmiyor")
    r.bilgi("")
    r.bilgi("      ✅ COZUM UYGULANDI (B18/F12): kelepceler +3V3'te KALDI,")
    r.bilgi("         onun yerine R26/R33 2.7K -> 10K ve R41 (1K) eklendi.")
    r.bilgi("         B15'in onerdigi F6 (kelepceleri TL431 rayina tasimak)")
    r.bilgi("         DEGERLENDIRILDI VE REDDEDILDI: hizli akim yolunun tam")
    r.bilgi("         olcegini 294.6 -> 169 mV'a dusuruyordu (ADS'in kendi")
    r.bilgi("         256 mV kirpmasinin ALTINA) ve TL431 kalintisini")
    r.bilgi("         kapatmiyordu. Olcumler: sim3_kelepce.py (B18).")
    kaydet("B1", "+-12 V acik, +3V3 kapali (USB cikarilmis)", "",
           not_=f"B18/F12 sonrasi 3V3 rayi {ray:.2f} V (sinir "
                f"{T.ESP_MUTLAK_PIN_UST:.1f} V, pay "
                f"{(T.ESP_MUTLAK_PIN_UST-ray)*1e3:.0f} mV) ve TL431'den "
                f"BAGIMSIZ. Oncesi {ray_eski:.2f} V / "
                f"{(T.ESP_MUTLAK_PIN_UST-ray_eski)*1e3:.0f} mV idi")

    # ── B2: +5 V yok, +-12 V var
    alt(r, "B2 · +5 V yok, +-12 V var")
    r.bilgi("      VREF, +5 V'tan beslenen U3A'dan geliyor. +5 V yoksa VREF")
    r.bilgi("      yuzer. TL072'nin (U8A) girisleri R27/R29 (10K) uzerinden")
    r.bilgi("      VREF'e bakiyor; kelepce diyotlari akimi sinirliyor.")
    r.bilgi("")
    i_kel = (T.VREF - 0.5) / T.HIZLI_RG
    r.kosul("      B2: TL072 giris kelepce akimi mutlak sinirin cok altinda",
            i_kel < T.TL072_GIRIS_AKIM_MAKS,
            f"{i_kel*1e3:.3f} mA << {T.TL072_GIRIS_AKIM_MAKS*1e3:.0f} mA "
            f"(%{i_kel/T.TL072_GIRIS_AKIM_MAKS*100:.1f})")
    r.bilgi("")
    r.bilgi("      Pratikte +5 V ve +3V3 birlikte gidiyor (ikisi de ESP32")
    r.bilgi("      kartindan), yani bu senaryo B1'in icinde eriyor.")
    kaydet("B2", "+5 V yok, +-12 V var", "",
           not_=f"TL072 giris kelepce akimi {i_kel*1e3:.2f} mA — zararsiz")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — C · BILESEN ARIZASI
# ═══════════════════════════════════════════════════════════════════════

def bolum4(r):
    bolum(r, "BOLUM 4 — C · BILESEN ARIZASI")

    # ── C1: alt bacak acik devre
    alt(r, "C1 · 🔴 Bolucunun ALT BACAGI acik devre (R16 8.2K / R6 6.8K)")
    r.bilgi("      DEVIR 5.12.22 senaryo 9: 'ilk hesap 123 uA'e sinirliyor,")
    r.bilgi("      yani MUHTEMELEN HAYATTA KALINIR — ama dogrulanmali.'")
    r.bilgi("      DOGRULANDI VE DEVIR YANILIYOR.")
    r.bilgi("")
    r.bilgi(f"      {'kanal':<12} {'giris':>8} {'alt bacak':>11} "
            f"{'dugum':>10} {'LM358 girisi':>13}")
    r.bilgi("      " + "-" * 58)
    c1 = {}
    for kanal, vin in ((HV, 615.0), (NORMAL, 615.0), (NORMAL, 32.0)):
        for ralt, ad in ((kanal["ralt"], "saglam"), (ACIK, "ACIK")):
            net = f"""* alt bacak {ad}
{LM358}
{AYARLAR}
Vin giris 0 DC {vin}
Vref vref 0 DC {T.VREF}
Vp vp 0 DC 5
Rust giris dugum {kanal['rust']}
Ralt dugum vref {ralt}
Rf dugum filt {T.RC_R}
Cf filt vref {T.RC_C}
Rkacak filt vref 1T
XU filt cik cik vp 0 LM358
.control
op
print v(dugum) v(filt)
.endc
.end
"""
            d = op(net, f"c1_{kanal['kod']}_{vin:.0f}_{ad}")
            c1[(kanal["kod"], vin, ad)] = d.get("v(filt)", 0.0)
            r.bilgi(f"      {kanal['kod']:<12} {vin:7.0f}V {ad:>10} "
                    f"{d.get('v(dugum)', 0):9.2f}V {d.get('v(filt)', 0):12.2f}V")
    r.bilgi("")
    hv_acik = c1[("hv", 615.0, "ACIK")]
    r.bilgi("      🔴 R16 ACIK -> LM358'in girisini asagi cekecek HICBIR SEY")
    r.bilgi("         kalmiyor. DEVIR'in '123 uA' hesabi, girisin ~5 V'ta")
    r.bilgi("         KELEPCELENDIGINI varsayiyordu; LM358'in V+'ya kelepcesi")
    r.bilgi("         YOK (TI acikca yaziyor).")
    r.bilgi("")
    r.bilgi("      ⚠ GIRISIN NEREDE DURACAGINI BELIRLEYEN TEK SEY, jonksiyonun")
    r.bilgi("        TERS KIRILMA gerilimidir — ve o deger HICBIR VERI")
    r.bilgi("        SAYFASINDA YOK. Bu yuzden burada TEK SAYI degil TARAMA")
    r.bilgi("        raporlaniyor; sonuc varsayimdan bagimsiz olarak ayni.")
    r.bilgi("")
    r.bilgi(f"      {'varsayilan kirilma':>19} {'LM358 girisi':>14} "
            f"{'zincir akimi':>14} {'jonksiyon gucu':>15}")
    r.bilgi("      " + "-" * 66)
    tarama = {}
    for bv in T.LM358_KIRILMA_TARAMA:
        _mak = opamp_makro("LM358V", T.LM358_VOH_DUSUM, T.LM358_VOL,
                           T.LM358_ISC, bv=bv)
        net = f"""* C1 taramasi — jonksiyon kirilmasi varsayimi
{_mak}
{AYARLAR}
Vin giris 0 DC 615
Vref vref 0 DC {T.VREF}
Vp vp 0 DC 5
Rust giris dugum {HV['rust']}
Ralt dugum vref {ACIK}
Rf dugum filt {T.RC_R}
Cf filt vref {T.RC_C}
Rkacak filt vref 1T
XU filt cik cik vp 0 LM358V
.control
op
print v(dugum) v(filt) i(Vin)
.endc
.end
"""
        d = op(net, f"c1_bv_{bv:.0f}")
        vf = d.get("v(filt)", 0.0)
        ii = abs(d.get("i(vin)", 0.0))       # SIMULASYONDAN, elle degil
        tarama[bv] = (vf, ii)
        r.bilgi(f"      {bv:16.0f} V {vf:12.2f} V {ii*1e6:11.1f} uA "
                f"{vf*ii*1e3:13.2f} mW")
    r.bilgi("")
    _en_dusuk = min(tarama)
    _en_yuksek = max(tarama)
    r.bilgi(f"      EN KOTU HAL kirilmanin HIC olmamasi: dugum girise oturuyor")
    r.bilgi(f"      ({tarama[_en_yuksek][0]:.0f} V). Yani tek sayilik bir rapor")
    r.bilgi("      KOTUMSER degil IYIMSER olurdu.")
    r.bilgi("")
    # ⚠ Akim SIMULASYONDAN aliniyor; elle yeniden hesaplanmiyor.
    i_zincir = max(v[1] for v in tarama.values())
    r.bilgi(f"      Akim her varsayimda kucuk: zincir onu en fazla "
            f"{i_zincir*1e6:.0f} uA'e")
    r.bilgi("      sinirliyor (DEVIR bu kismi DOGRU bilmis).")
    r.bilgi("      Ama belirleyici olan AKIM degil GERILIM:")
    r.bilgi("")
    # Tek istisna: jonksiyon 32 V'un ALTINDA kirilirsa parca kendi kendini
    # spek icinde kelepceler. Ama hicbir veri sayfasi bunu VAAT ETMIYOR —
    # ve o durumda bile jonksiyon surekli ters kirilmada calisiyor.
    _asanlar = [bv for bv, v in tarama.items()
                if v[0] > T.LM358_GIRIS_MUTLAK_UST]
    _en_kotu_v = tarama[max(tarama)][0]
    r.kosul("      C1: EN KOTU HALDE (kirilma yok) giris TUM giris gerilimini "
            "goruyor",
            _en_kotu_v > 0.95 * 615.0,
            f"{_en_kotu_v:.0f} V — mutlak sinirin "
            f"{_en_kotu_v/T.LM358_GIRIS_MUTLAK_UST:.0f} kati")
    r.kosul("      C1: makul her kirilma varsayiminda (>=40 V) sinir asiliyor",
            all(tarama[bv][0] > T.LM358_GIRIS_MUTLAK_UST
                for bv in tarama if bv >= 40.0),
            f"{len(_asanlar)}/{len(tarama)} varsayim sinirin ustunde — "
            f"DEVIR'in 'hayatta kalinir' tahmini DOGRULANMADI")
    r.bilgi("")
    r.bilgi("      ⚠ TEK ISTISNA: jonksiyon 32 V'un ALTINDA kirilirsa parca")
    r.bilgi("        kendini spek icinde kelepceler (tabloda 30 V satiri).")
    r.bilgi("        Ama hicbir veri sayfasi bunu VAAT ETMIYOR ve o halde de")
    r.bilgi("        jonksiyon SUREKLI ters kirilmada calisiyor. Yani")
    r.bilgi("        'sanslıysak sorun yok' — tasarim bunun uzerine kurulamaz.")
    r.kosul("      C1: akim ise her varsayimda kucuk (DEVIR bu kismi dogru)",
            i_zincir < 200e-6, f"en fazla {i_zincir*1e6:.0f} uA")
    r.bilgi("")
    r.bilgi("      NE OLUR: LM358'in giris jonksiyonu ters kirilmaya (avalanche)")
    r.bilgi(f"      girer. Guc en fazla "
            f"{max(v[0]*v[1] for v in tarama.values())*1e3:.1f} mW mertebesinde,")
    r.bilgi("      yani ANINDA yanmaz — ama surekli spek disi calisir ve")
    r.bilgi("      sessizce suruklenir. Bu, en kotu ariza tipi: OLMUYOR ama")
    r.bilgi("      YANLIS OLCUYOR.")
    r.bilgi("")
    r.bilgi("      ⚠ C3 (100nF) de bu dugumde: uzerinde")
    r.bilgi(f"        {hv_acik - T.VREF:.0f} V var. Envanterdeki 100nF'lerin cogu")
    r.bilgi("        50V/63V — onlar once delinir (ve delinince dugumu VREF'e")
    r.bilgi("        kisa devre edip sistemi KURTARIR). 630V'luk parca")
    r.bilgi("        kullanilirsa bu kurtarma da olmaz.")
    r.bilgi("")
    r.bilgi("      ✅ COZUM: LM358 girisine kelepce. 1N4148 (silisyum) secilmeli,")
    r.bilgi("         Schottky DEGIL: dugum yuksek empedansli (22K) ve Schottky")
    r.bilgi("         kacagi olcumu bozar. Bolum 7'de sayisallastirildi.")
    kaydet("C1", "HV bolucunun alt bacagi (R16) acik devre",
           "U3/U4 (LM358, soketli) — yavas",
           not_=f"LM358 girisi {hv_acik:.0f} V (sinir 32 V); akim yalnizca "
                f"{i_zincir*1e6:.0f} uA, yani anlik olum yok ama surekli "
                f"spek disi. DEVIR 'hayatta kalinir' diyordu — dogrulanmadi")

    # ── C2: zincirdeki bir 820K acik
    alt(r, "C2 · Zincirdeki bir 820K acik devre")
    net = f"""* bir 820K acik
{LM358}
{AYARLAR}
Vin giris 0 DC 615
Vref vref 0 DC {T.VREF}
Vp vp 0 DC 5
R1 giris a {5*820e3}
Racik a dugum {ACIK}
R16 dugum vref {HV['ralt']}
Rf dugum filt {T.RC_R}
Cf filt vref {T.RC_C}
Rkacak filt vref 1T
XU filt cik cik vp 0 LM358
.control
op
print v(dugum) v(filt) v(cik)
.endc
.end
"""
    d = op(net, "c2_820k")
    r.bilgi(f"      Dugum {d.get('v(dugum)', 0):.4f} V, VREF {T.VREF:.4f} V")
    r.kosul("      C2: dugum VREF'e oturuyor — GUVENLI, okuma sifir",
            abs(d.get("v(dugum)", 0) - T.VREF) < 1e-3,
            f"sapma {abs(d.get('v(dugum)', 0) - T.VREF)*1e6:.1f} uV")
    r.bilgi("")
    r.bilgi("      ⚠ AMA: acik kalan direncin iki ucu arasinda tum 613 V var.")
    r.bilgi("        Arastirma: 615 V bir 6.3 mm direnc govdesi uzerinden ARK")
    r.bilgi("        ATLAYAMAZ (hava ~3 kV/mm, ~19 kV gerekirdi). Yani acik")
    r.bilgi("        kalan direnc yeniden iletmez — ariza KARARLI ve GUVENLI.")
    _ark = T.HAVA_KIRILMA_V_MM * T.DIRENC_GOVDE_BOY_MM
    _uygulanan = HV["fs_sim"]
    r.kosul("      C2: acik kalan direncin govdesi uzerinden ARK ATLAMAZ",
            _uygulanan < _ark,
            f"{_uygulanan:.0f} V << {_ark:.0f} V "
            f"({T.DIRENC_GOVDE_BOY_MM:.1f} mm govde x "
            f"{T.HAVA_KIRILMA_V_MM/1000:.0f} kV/mm) — ariza KARARLI")
    kaydet("C2", "Zincirdeki bir 820K acik devre", "",
           not_="dugum VREF'e oturuyor, okuma sifir — guvenli ariza")

    # ── C3: TL431 arizasi
    alt(r, "C3 · TL431 (U1) arizasi — HER IKI kanali birden kaydiriyor")
    r.bilgi("      VREF her iki gerilim kanalinin da alt ucu. VREF hatasi")
    r.bilgi("      girise indirgenmis SABIT OFSET olarak gorunur (N'den")
    r.bilgi("      bagimsiz) — kazanc hatasi degil.")
    r.bilgi("")
    r.bilgi(f"      {'ariza':<20} {'TL_RAY':>9} {'VREF':>9} {'kayma':>10} "
            f"{'NORMAL FS hata':>15}")
    r.bilgi("      " + "-" * 66)
    r_vref = T.VREF_RA + T.VREF_RB
    for ad, tl_ray in (("saglam", T.TL431_V),
                       ("ACIK DEVRE", T.VDD * r_vref / (r_vref + 220.0)),
                       ("KISA DEVRE", 0.0)):
        vref_y = tl_ray * T.VREF_RB / r_vref
        kayma = vref_y - T.VREF
        hata_fs = abs(kayma) / NORMAL["fs_sim"] * 100
        r.bilgi(f"      {ad:<20} {tl_ray:8.4f}V {vref_y:8.4f}V "
                f"{kayma:+9.4f}V {hata_fs:13.2f}%")
    tl_acik = T.VDD * r_vref / (r_vref + 220.0)
    vref_acik = tl_acik * T.VREF_RB / r_vref
    r.bilgi("")
    r.kosul("      C3: TL431 acik devre parcayi oldurmuyor ama SESSIZCE "
            "yanlis okutuyor",
            abs(vref_acik - T.VREF) > 0.5,
            f"VREF {T.VREF:.4f} -> {vref_acik:.4f} V "
            f"({vref_acik-T.VREF:+.3f} V girise indirgenmis ofset)")
    # ⚠ KISA DEVRE senaryosu TAM ZINCIRLE kurulmali. Bolucu dugumu ADS'e
    #   DEGIL, R7 (22K) uzerinden LM358'in GIRISINE gidiyor; ADS pinini
    #   suren sey tamponun CIKISI. Tampon tek besleme (+5 V / GND) ile
    #   calistigi icin cikisi GND altina INEMEZ -> ADS pini V_OL'da kalir.
    #   Zorlanan parca ADS degil, LM358'in giris jonksiyonu.
    d = op(gerilim_kanali_netlist(-32.0, NORMAL["rust"], NORMAL["ralt"],
                                  T.RC_R, None, T.ADS_SERI_R, "LM358")            .replace(f"Vref vref 0 DC {T.VREF}", "Vref vref 0 DC 0"),
           "c3_kisa_tam")
    dug_kisa = d.get("v(dugum)", 0.0)
    op_kisa = d.get("v(filt)", 0.0)
    pin_kisa = d.get("v(pin)", 0.0)
    i_op_kisa = abs(d.get("i(vam_giris)", 0.0))
    r.bilgi(f"      KISA DEVRE + girise -32 V (TAM zincir):")
    r.bilgi(f"        bolucu dugumu   {dug_kisa:+.4f} V")
    r.bilgi(f"        LM358 girisi    {op_kisa:+.4f} V   "
            f"(mutlak alt sinir {T.LM358_GIRIS_MUTLAK_ALT:+.1f} V)")
    r.bilgi(f"        ADS pini        {pin_kisa:+.4f} V   "
            f"(mutlak alt sinir {T.ADS_MUTLAK_GIRIS_ALT:+.1f} V)")
    r.bilgi(f"        LM358 giris akimi {i_op_kisa*1e6:.1f} uA")
    r.kosul("      C3: kisa devrede ZORLANAN parca ADS degil LM358'in girisi",
            pin_kisa >= T.ADS_MUTLAK_GIRIS_ALT
            and op_kisa < T.LM358_GIRIS_MUTLAK_ALT,
            f"ADS pini {pin_kisa:+.3f} V (guvenli, tampon GND altina inemez); "
            f"LM358 girisi {op_kisa:+.3f} V (spek disi)")
    r.kosul("      C3: LM358 giris akimi guvenli sinirin altinda",
            i_op_kisa < T.LM358_GIRIS_AKIM_GUVENLI,
            f"{i_op_kisa*1e6:.0f} uA < "
            f"{T.LM358_GIRIS_AKIM_GUVENLI*1e6:.0f} uA — R7 sinirliyor")
    r.bilgi("")
    i_r1 = (T.VDD - 0.0) / 220.0
    r.kosul("      C3: TL431 kisa devrede R1 (220R) yanmiyor",
            i_r1 ** 2 * 220.0 < T.DIRENC_GOVDE["1/4W"][1],
            f"{i_r1**2*220.0*1e3:.1f} mW < 250 mW")
    kaydet("C3", "TL431 (U1) acik devre", "",
           not_=f"parca olmuyor ama HER IKI kanal {vref_acik-T.VREF:+.3f} V "
                f"kayiyor — SESSIZ ariza, en tehlikeli tip")
    kaydet("C3b", "TL431 (U1) kisa devre", "",
           not_=f"VREF 0 olunca cift yonlu olcum comuyor; LM358 girisi "
                f"{op_kisa:+.2f} V (spek disi) ama akim {i_op_kisa*1e6:.0f} uA. "
                f"ADS pini {pin_kisa:+.2f} V — tampon GND altina inemedigi "
                f"icin ADS GUVENDE. Parca olmuyor, olcum oluyor")

    # ── C4: TL431 kararlilik tuzagi — semadaki C1
    alt(r, "C4 · ✅ C1 TL431'i osile ettiriyordu — B15/F4 ile KAPATILDI")
    r.bilgi("      TI SLVA482A: TL431'in katot-anot arasindaki kondansator")
    r.bilgi(f"      {T.TL431_KARARSIZ_C[0]*1e9:.0f} nF .. "
            f"{T.TL431_KARARSIZ_C[1]*1e6:.1f} uF araliginda OSILASYONA yol aciyor.")
    r.bilgi(f"      Guvenli degerler: < {T.TL431_GUVENLI_C_ALT*1e9:.0f} nF "
            f"ya da > {T.TL431_GUVENLI_C_UST*1e6:.0f} uF.")
    r.bilgi("")
    r.bilgi(f"      B15 ONCESI: C1 = {T.C1_ESKI*1e9:.0f} nF, TL_RAY ile GND arasinda")
    r.bilgi("      (netlist: /TL_RAY = C1.1, R1.2, R2.1, U1.1, U1.3 · GND = C1.2)")
    r.bilgi("      — yani TAM olarak katot-anot arasinda.")
    r.bilgi("")
    kararsiz = T.TL431_KARARSIZ_C[0] <= T.C1_ESKI <= T.TL431_KARARSIZ_C[1]
    r.kosul("      C4: eski deger kararsiz bolgenin TAM ICINDEYDI",
            kararsiz,
            f"{T.C1_ESKI*1e9:.0f} nF, aralik "
            f"{T.TL431_KARARSIZ_C[0]*1e9:.0f} nF .. "
            f"{T.TL431_KARARSIZ_C[1]*1e6:.1f} uF")
    r.kosul("      C4: ✅ semadaki GUNCEL deger guvenli bolgede",
            T.C1_SIMDI <= T.TL431_GUVENLI_C_ALT,
            f"{T.C1_SIMDI*1e9:.0f} nF <= {T.TL431_GUVENLI_C_ALT*1e9:.0f} nF "
            f"(envanter C049: 1nF 50V x10)")
    r.bilgi("")
    r.bilgi("      TL431 veri sayfasi zaten kondansator GEREKTIRMEDIGINI")
    r.bilgi("      soyluyor: 'internally compensated to be stable without an")
    r.bilgi("      output capacitor'. C1 refleksle konmus ve tam yanlis")
    r.bilgi("      araliga dusmus.")
    kaydet("C4", "C1 TL431 osilasyonu (B15/F4 ile KAPATILDI)", "",
           not_=f"eski 100nF kararsiz bolgedeydi; sema artik "
                f"{T.C1_SIMDI*1e9:.0f} nF — kusur kapali")

    # ── C5: Vref tamponu (U3A) arizasi
    alt(r, "C5 · Vref tamponu (U3A) arizasi — cikis raya oturursa")
    r.bilgi("      VREF, B15 oncesi ADS'in AIN1/AIN3 pinlerine DOGRUDAN")
    r.bilgi("      gidiyordu. Artik R36 (1K) araya girdi:")
    r.bilgi("      /VREF = ... R36.1 ...  ->  /VREF_ADS = R36.2, U7.5, U7.7")
    r.bilgi("      U3A cikisi raya oturursa iki ADS pini birden zorlaniyor.")
    r.bilgi("")
    r.bilgi("      ⚠ 'Raya oturuyor' senaryosu GERCEKTEN rayla olculmeli:")
    r.bilgi(f"        garantili tavanda ({5.0-T.LM358_VOH_DUSUM:.2f} V) ESD diyodu")
    r.bilgi("        zaten iletmiyor, yani seri direnc SONUCU DEGISTIRMEZ.")
    r.bilgi("        Belirleyici olan en kotu hal: cikis rayin kendisinde.")
    r.bilgi("")
    c5 = {}
    for ad, vcik in (("V_OH garantili", 5.0 - T.LM358_VOH_DUSUM),
                     ("EN KOTU: ray 5.00 V", 5.00),
                     ("EN KOTU: ray 5.25 V", 5.25),
                     ("V_OL'a oturur", T.LM358_VOL)):
        for var_r, rseri, rad in ((False, 1e-3, "seri R yok"),
                                   (True, T.ADS_SERI_R,
                                   f"{T.ADS_SERI_R/1e3:.0f}K seri")):
            net = f"""* Vref tamponu arizasi -> ADS pinleri
{D_ESD}
{AYARLAR}
Vs cik 0 DC {vcik}
V33 v33 0 DC {T.VDD}
Rs cik pin {rseri}
Vam esd_a v33 DC 0
Desd_ust pin esd_a DESD
Desd_alt 0 pin DESD
.control
op
print v(pin) i(Vam)
.endc
.end
"""
            d = op(net, f"c5_{vcik:.2f}_{rseri:.0f}")
            i = abs(d.get("i(vam)", 0.0))
            r.bilgi(f"      {ad:<16} {rad:<14} pin {d.get('v(pin)', 0):6.3f} V  "
                    f"ESD akimi {i*1e6:8.1f} uA")
            c5[(ad, var_r)] = i
    r.bilgi("")
    _ek_ad = "EN KOTU: ray 5.25 V"
    r.kosul("      C5: R36 OLMADAN en kotu halde ADS akimi hedefi asiyor",
            c5[(_ek_ad, False)] > T.ADS_TASARIM_AKIM_HEDEFI,
            f"{c5[(_ek_ad, False)]*1e3:.2f} mA > "
            f"{T.ADS_TASARIM_AKIM_HEDEFI*1e3:.0f} mA")
    r.kosul("      C5: R36 (1K) ile ADS akimi %20 kuralinin altinda",
            c5[(_ek_ad, True)] < T.ADS_TASARIM_AKIM_TAVANI,
            f"{c5[(_ek_ad, False)]*1e3:.2f} -> {c5[(_ek_ad, True)]*1e3:.3f} mA "
            f"({c5[(_ek_ad, False)]/max(c5[(_ek_ad, True)],1e-12):.1f}x)")
    kaydet("C5", "Vref tamponu (U3A) cikisi raya oturuyor",
           "U3 (LM358, soketli)",
           not_=f"R36 sayesinde ADS akimi {c5[(_ek_ad, True)]*1e3:.2f} mA'de "
                f"kaliyor (R36 olmadan {c5[(_ek_ad, False)]*1e3:.1f} mA); "
                f"olcum tamamen bozulur ama donanim yasar")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 5 — D · KULLANICI HATASI VE SISTEM (IZOLASYON)
# ═══════════════════════════════════════════════════════════════════════

def onderdonk(cmil, saniye, tm=None, ta=None):
    """Onderdonk: bir bakir iletkenin `saniye` icinde eridigi akim (A)."""
    tm = tm if tm is not None else T.BAKIR_ERIME_C
    ta = ta if ta is not None else T.ORTAM_C
    return cmil * math.sqrt(math.log10((tm - ta) / (234.0 + ta) + 1.0)
                            / (33.0 * saniye))


def erime_suresi(cmil, akim, tm=None, ta=None):
    """Verilen akimda erime suresi (s) — Onderdonk'un tersi."""
    tm = tm if tm is not None else T.BAKIR_ERIME_C
    ta = ta if ta is not None else T.ORTAM_C
    return (cmil / akim) ** 2 * math.log10(
        (tm - ta) / (234.0 + ta) + 1.0) / 33.0


def bolum5(r):
    bolum(r, "BOLUM 5 — D · KULLANICI HATASI VE SISTEM (IZOLASYON)")
    r.bilgi("  DEVIR 5.12.22 senaryo 12: 'Kart izole DEGIL — bu bilinen bir")
    r.bilgi("  uyari ama SAYISALLASTIRILMADI.' Burada sayisallastiriliyor.")

    # ── D1a: bolucu yolu — zararsiz
    alt(r, "D1a · J2 ucu sebekeye, kart GND'si TOPRAKTA (bolucu yolu)")
    r.bilgi("      Akim 4.93 Mohm'luk zincirle sinirli. USB GND -> PC sasi ->")
    r.bilgi("      koruyucu toprak yolundan akiyor.")
    r.bilgi("")
    z = HV["giris_z"]
    for ad, v in (("230 V AC (rms)", T.SEBEKE_RMS),
                  ("230 V AC (tepe)", T.SEBEKE_TEPE),
                  ("615 V DC", 615.0)):
        i = v / z
        r.bilgi(f"      {ad:<18} -> {i*1e6:7.2f} uA")
    i_615 = 615.0 / z
    r.kosul("      D1a: bolucu yolundaki akim RCD esiginin cok altinda",
            i_615 < T.RCD_ESIK / 100,
            f"{i_615*1e6:.1f} uA << {T.RCD_ESIK*1e3:.0f} mA — RCD acmaz, "
            f"kimse fark etmez")
    r.kosul("      D1a: dokunma akimi sinirlarinin da altinda",
            i_615 < 0.25e-3,
            f"{i_615*1e6:.1f} uA < 250 uA (IEC 62368-1 Sinif II siniri)")
    r.bilgi("")
    r.bilgi("      ✅ Bu yon GUVENLI. Bolucu isini yapiyor.")
    kaydet("D1a", "J2 ucu sebekeye, kart GND'si toprakta", "",
           not_=f"yalnizca {i_615*1e6:.0f} uA akiyor — elektriksel olarak "
                f"zararsiz")

    # ── D1b: kart GND'si canliya — OLUMCUL
    alt(r, "D1b · 🔴 Kart GND'si CANLI bir dugume baglanirsa (USB takili)")
    r.bilgi("      Trafosuz bir SMPS'in DC bara EKSI ucu, kopru diyot")
    r.bilgi("      uzerinden sebeke topragina gore 0 .. -325 V arasinda")
    r.bilgi("      geziniyor. Schuko fisi POLARIZE DEGIL — hangi bacagin faz")
    r.bilgi("      oldugu standartca tanimsiz, yani %50 ihtimalle en kotu hal.")
    r.bilgi("")
    r.bilgi("      Kart GND'si oraya baglanirsa USB kablosunun GND teli")
    r.bilgi("      sebeke ile toprak arasinda DOGRUDAN KISA DEVRE olur.")
    r.bilgi("")
    r.bilgi(f"      {'dongu direnci':>14} {'ariza akimi (rms)':>19} {'tepe':>10}")
    r.bilgi("      " + "-" * 46)
    akimlar = []
    for rd in T.ARIZA_DONGU_R:
        i = T.SEBEKE_RMS / rd
        akimlar.append(i)
        r.bilgi(f"      {rd:13.1f} R {i:17.0f} A {i*math.sqrt(2):9.0f} A")
    i_tipik = T.SEBEKE_RMS / 0.7
    r.bilgi(f"      {'tipik (0.7 R)':>14} {i_tipik:17.0f} A "
            f"{i_tipik*math.sqrt(2):9.0f} A")
    r.bilgi("")
    r.bilgi("      USB kablosunun GND teli ne kadar dayanir (Onderdonk):")
    r.bilgi("")
    r.bilgi(f"      {'iletken':>10} {'cmil':>7} {'erime suresi':>14} "
            f"{'1 s erime akimi':>17}")
    r.bilgi("      " + "-" * 52)
    for ad, cmil in sorted(T.USB_AWG.items()):
        ts = erime_suresi(cmil, i_tipik)
        r.bilgi(f"      {ad:>10} {cmil:7.1f} {ts*1e3:11.1f} ms "
                f"{onderdonk(cmil, 1.0):15.1f} A")
    t28 = erime_suresi(T.USB_AWG["28AWG"], i_tipik)
    t24 = erime_suresi(T.USB_AWG["24AWG"], i_tipik)
    r.bilgi("")
    r.bilgi("      Koruma cihazlari ne zaman devreye giriyor:")
    r.bilgi(f"        30 mA RCD  : 5xIdn'de en gec {T.RCD_ACMA_S*1e3:.0f} ms "
            f"(IEC 61008)")
    r.bilgi(f"        B16 MCB    : {T.MCB_B16_ANI[0]:.0f}-{T.MCB_B16_ANI[1]:.0f} A "
            f"bandinda, <= 100 ms")
    r.bilgi(f"        USB portu  : VBUS'ta {T.USB_VBUS_ILIM:.1f} A sinir, "
            f"GND'de KORUMA YOK")
    r.bilgi("")
    r.kosul("      D1b: ariza akimi USB GND telini RCD'den ONCE eritiyor",
            t28 < T.RCD_ACMA_S,
            f"28AWG {t28*1e3:.1f} ms < RCD {T.RCD_ACMA_S*1e3:.0f} ms — "
            f"kablo SIGORTA gorevi goruyor")
    r.kosul("      D1b: kalin kabloda bile RCD'den once eriyor",
            t24 < T.RCD_ACMA_S,
            f"24AWG {t24*1e3:.1f} ms < {T.RCD_ACMA_S*1e3:.0f} ms")
    r.kosul("      D1b: ariza akimi USB kontak anmasini kat kat asiyor",
            i_tipik / T.USB_KONTAK_ANMA_A > 100,
            f"{i_tipik:.0f} A / {T.USB_KONTAK_ANMA_A:.1f} A = "
            f"{i_tipik/T.USB_KONTAK_ANMA_A:.0f} kat — ve anakart korumasi "
            f"YALNIZCA VBUS'ta ({T.USB_VBUS_ILIM:.1f} A), GND'de YOK")
    r.bilgi("")
    r.bilgi("      SONUC — kim neyi koruyor:")
    r.bilgi("        RCD    -> INSANI korur (40 ms icinde acar)")
    r.bilgi("        Kablo  -> kendini feda eder (4-30 ms'te erir)")
    r.bilgi("        PC     -> KORUYAN YOK. Anakartin USB GND izi kablodan")
    r.bilgi("                  once buharlasir (20 mil / 1 oz iz ~0.24 ms).")
    kaydet("D1b", "🔴 Kart GND'si canli dugume + USB takili",
           "USB kablosu + PC anakarti", esp=False, pc=False,
           not_=f"~{i_tipik:.0f} A ariza akimi; USB GND teli {t28*1e3:.0f}-"
                f"{t24*1e3:.0f} ms'te eriyor. RCD insani kurtarir, PC'yi DEGIL")

    # ── D2: pille yuzdurme gercekten cozuyor mu
    alt(r, "D2 · 'Karti pille yuzdurelim' plani — gercekten yeterli mi")
    r.bilgi("      DEVIR 5.12.23 pil + Wi-Fi ile kartin YUZECEGINI, boylece")
    r.bilgi("      D1b'nin kapanacagini soyluyor. Elektriksel olarak DOGRU.")
    r.bilgi("      Ama Tektronix, PILLE BESLENEN gercek bir osiloskop icin")
    r.bilgi("      bile sert bir sinir koyuyor:")
    r.bilgi("")
    r.bilgi(f"        toprağa gore en fazla {T.YUZEN_ALET_TOPRAGA_SINIR_RMS:.0f} V rms "
            f"({T.YUZEN_ALET_TOPRAGA_SINIR_TEPE:.0f} V tepe)")
    r.bilgi("        'accessible parts of the instrument such as chassis,")
    r.bilgi("         cabinet, and connectors assume the potential of the")
    r.bilgi("         reference lead'")
    r.bilgi("")
    r.kosul("      D2: 615 V, yuzen alet siniri icin bile KAT KAT fazla",
            615.0 > T.YUZEN_ALET_TOPRAGA_SINIR_TEPE,
            f"615 V / {T.YUZEN_ALET_TOPRAGA_SINIR_TEPE:.0f} V = "
            f"{615.0/T.YUZEN_ALET_TOPRAGA_SINIR_TEPE:.1f} kat")
    r.bilgi("")
    r.bilgi("      YANI: yuzdurmek PC'yi kurtarir, KULLANICIYI kurtarmaz.")
    r.bilgi("      Kartin KENDISI 615 V'a cikar. Sart olan:")
    r.bilgi(f"        · yalitimli kutu, disarida iletken HIC yok")
    r.bilgi(f"        · IEC 60664-1 kacak yolu: temel {T.IEC60664_CREEPAGE_TEMEL:.1f} mm, "
            f"takviyeli {T.IEC60664_CREEPAGE_TAKVIYELI:.1f} mm")
    r.bilgi(f"        · IPC-2221B hava araligi 615 V icin "
            f"{T.IPC2221_KACAK_615V:.2f} mm")
    r.bilgi("")
    # B48: kacak yolu BAKIRDAN BAKIRA — merkez araligindan ped capi dusuluyor.
    # Onceki hesap ceil(12.6 / 2.54) = 5 delik diyordu; 5 delik bakirdan
    # bakira 11.16 mm eder, 12.6'yi saglamaz.
    n_delik_temel = math.ceil((T.IEC60664_CREEPAGE_TEMEL + T.DELIKLI_PAD_ETKIN_MM)
                              / T.DELIKLI_ADIM)
    n_delik_takv = math.ceil((T.IEC60664_CREEPAGE_TAKVIYELI + T.DELIKLI_PAD_ETKIN_MM)
                             / T.DELIKLI_ADIM)
    r.bilgi(f"      Delikli plakette ({T.DELIKLI_ADIM:.2f} mm adim, ped "
            f"{T.DELIKLI_PAD_ETKIN_MM:.2f} mm) bu ne demek:")
    r.bilgi(f"        temel yalitim    : {n_delik_temel} delik atla "
            f"({n_delik_temel*T.DELIKLI_ADIM - T.DELIKLI_PAD_ETKIN_MM:.2f} mm bakirdan bakira)")
    r.bilgi(f"        takviyeli yalitim: {n_delik_takv} delik atla "
            f"({n_delik_takv*T.DELIKLI_ADIM - T.DELIKLI_PAD_ETKIN_MM:.2f} mm bakirdan bakira)")
    r.kosul("      D2: semadaki 'delik atlayarak' notu SAYIYA baglandi",
            n_delik_takv >= 4,
            f"kullanici ile HV arasinda {n_delik_takv} delik "
            f"({n_delik_takv*T.DELIKLI_ADIM - T.DELIKLI_PAD_ETKIN_MM:.2f} mm bakirdan bakira)")
    r.bilgi("")
    r.bilgi("      ⚠ Direnc govdesinin CEVRESINE karsi SUREKLI yalitimi")
    r.bilgi(f"        yalnizca {T.DIRENC_YALITIM_SUREKLI:.0f} V (Vishay MRS25). 500 V rakami")
    r.bilgi("        1 DAKIKALIK testtir. 615 V zincirinin tepesi bu sayinin")
    r.bilgi(f"        {615.0/T.DIRENC_YALITIM_SUREKLI:.0f} katinda — direncler komsu izlere ve")
    r.bilgi("        toprak duzlemine YAKIN KONMAMALI.")
    kaydet("D2", "Pille yuzdurup 615 V olcmek", "",
           pc=True,
           not_=f"PC kurtulur; KULLANICI kurtulmaz — kart 615 V'a cikar. "
                f"Yalitimli kutu + {n_delik_takv} delik aralik SART")

    # ── D3: dolu kondansator desarji
    alt(r, "D3 · Dolu bir kondansatore prob degdirmek (400 V / 470 uF)")
    r.bilgi("      SMPS olcerken en sik karsilasilan enerji kaynagi.")
    r.bilgi("")
    c_yuk, v_yuk = 470e-6, 400.0
    enerji = 0.5 * c_yuk * v_yuk ** 2
    tau = HV["giris_z"] * c_yuk
    i_ilk = v_yuk / HV["giris_z"]
    r.bilgi(f"      Depolanan enerji : {enerji:.1f} J")
    r.bilgi(f"      Ilk akim (HV)    : {i_ilk*1e6:.1f} uA")
    r.bilgi(f"      Zaman sabiti     : {tau:.1f} s  (4.93 Mohm x 470 uF)")
    r.bilgi("")
    r.kosul("      D3: HV kanalinda desarj akimi zararsiz",
            i_ilk < 1e-3, f"{i_ilk*1e6:.1f} uA — bolucu isini yapiyor")
    r.bilgi("")
    r.bilgi("      🔴 AMA SKOP GIRISI (J4) BASKA HIKAYE: orada bolucu")
    r.bilgi(f"      yalnizca {T.SKOP_RUST/1e3:.0f}K, yani ilk akim "
            f"{v_yuk/T.SKOP_RUST*1e3:.1f} mA ve R20'de")
    r.bilgi(f"      {v_yuk**2/T.SKOP_RUST:.1f} W. R20 ({T.DIRENC_GOVDESI['R20']}) bunu "
            f"{v_yuk**2/T.SKOP_RUST/T.DIRENC_GOVDE[T.DIRENC_GOVDESI['R20']][1]:.0f} kat asiyor.")
    p_skop = v_yuk ** 2 / T.SKOP_RUST
    r.kosul("      D3: skop girisine 400 V degerse R20 aniden asiri yukleniyor",
            p_skop > T.DIRENC_GOVDE[T.DIRENC_GOVDESI["R20"]][1],
            f"{p_skop:.1f} W > {T.DIRENC_GOVDE[T.DIRENC_GOVDESI['R20']][1]:.2f} W "
            f"— ama enerji {0.5*c_yuk*v_yuk**2:.0f} J ve tau "
            f"{T.SKOP_RUST*c_yuk:.1f} s, yani SUREKLI yuk gibi davraniyor")
    kaydet("D3", "Skop girisine dolu 400 V kondansator", "R20 (100K)",
           not_=f"{p_skop:.1f} W, {T.SKOP_RUST*c_yuk:.0f} s boyunca — R20 yanar; "
                f"HV kanalinda ayni olay zararsiz ({i_ilk*1e6:.0f} uA)")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 6 — OZET: ARIZA -> OLEN PARCA MATRISI
# ═══════════════════════════════════════════════════════════════════════

def bolum6(r):
    bolum(r, "BOLUM 6 — OZET: hangi arizada hangi parca gidiyor")
    r.bilgi("  KABUL OLCUTU (DEVIR 5.12.22): hicbir TEK ariza ESP32'yi ya da")
    r.bilgi("  PC'yi oldurmemeli; olecek parca bilinmeli ve UCUZ olmali.")
    r.bilgi("")
    r.bilgi(f"  {'kod':<5} {'senaryo':<40} {'olen parca':<26} "
            f"{'ESP':>4} {'PC':>4}")
    r.bilgi("  " + "-" * 84)
    for a in ARIZALAR:
        r.bilgi(f"  {a.kod:<5} {a.ad[:40]:<40} {(a.olen or '—')[:26]:<26} "
                f"{'ok' if a.esp_guvende else 'RISK':>4} "
                f"{'ok' if a.pc_guvende else 'RISK':>4}")
    r.bilgi("")
    r.bilgi("  Ayrinti / not:")
    for a in ARIZALAR:
        if a.not_:
            r.bilgi(f"    {a.kod:<5} {a.not_}")
    r.bilgi("")

    # ── olen parcalarin fiyati
    # D1b bir BILESEN arizasi degil, bir KULLANIM hatasi (kart izole degil).
    # "Olecek parca ucuz olsun" olcutu bilesen arizalari icin anlamli;
    # D1b ayrica raporlaniyor.
    bilesen = [a for a in ARIZALAR if a.olen and a.kod != "D1b"]
    olenler = sorted({a.olen for a in bilesen})
    r.bilgi("  OLEN PARCALARIN FIYATI (bilesen arizalari; D1b ayrica):")
    r.bilgi("")
    en_pahali = 0.0
    en_pahali_ad = ""
    for o in olenler:
        # ⚠ Bir senaryoda BIRDEN COK parca olebiliyor ("U6 ... + R18").
        #   Ilk eslesmeyi almak 45 TL'lik ADS'i 0.15 TL'lik R18 ile
        #   fiyatlandiriyordu — EN PAHALI eslesme alinmali.
        adaylar = [v for k, v in FIYAT.items()
                   if k.split()[0] in o or o.split()[0] in k]
        fiyat = max(adaylar) if adaylar else None
        etiket = f"{fiyat:.2f} TL" if fiyat is not None else "?"
        if fiyat is not None and fiyat > en_pahali:
            en_pahali, en_pahali_ad = fiyat, o
        r.bilgi(f"    {o:<34} {etiket:>10}")
    r.bilgi("")
    r.kosul("  OZET: bilesen arizalarinda olen en pahali parca UCUZ",
            en_pahali <= UCUZ_ESIK,
            f"en pahali {en_pahali_ad} = {en_pahali:.0f} TL "
            f"<= {UCUZ_ESIK:.0f} TL")
    r.bilgi("")
    r.bilgi(f"  🔴 TEK ISTISNA — D1b (kart GND'si canliya + USB takili):")
    r.bilgi(f"     USB kablosu + PC anakarti "
            f"(~{FIYAT['PC anakarti']:.0f} TL). Bu bir BILESEN arizasi")
    r.bilgi("     degil; 'kart izole degil' kisitinin dogrudan sonucu.")
    r.bilgi("     Donanimla degil PROSEDURLE cozuluyor (F10).")
    r.bilgi("")

    # ── kabul olcutu
    esp_riskli = [a for a in ARIZALAR if not a.esp_guvende]
    pc_riskli = [a for a in ARIZALAR if not a.pc_guvende]
    r.bilgi("  KABUL OLCUTU DENETIMI — BUGUNKU SEMA:")
    r.bilgi(f"    ESP32'yi riske atan senaryolar : "
            f"{', '.join(a.kod for a in esp_riskli) if esp_riskli else 'YOK'}")
    r.bilgi(f"    PC'yi riske atan senaryolar    : "
            f"{', '.join(a.kod for a in pc_riskli) if pc_riskli else 'YOK'}")
    r.bilgi("")
    # D1b bir BILESEN arizasi degil, bir KULLANIM kisiti — ayri tutuluyor
    esp_bilesen = [a for a in esp_riskli if a.kod != "D1b"]
    pc_bilesen = [a for a in pc_riskli if a.kod != "D1b"]
    # ⚠ Bos listede all() tavtolojik olur — dogrudan BOSLUGU siniyoruz.
    r.kosul("  OZET: 🎯 KABUL OLCUTU — hicbir BILESEN arizasi ESP32'yi "
            "riske atmiyor",
            len(esp_bilesen) == 0,
            f"{len(ARIZALAR)} senaryodan {len(esp_bilesen)} tanesi ESP32'yi "
            f"tehdit ediyor"
            + (f" ({', '.join(a.kod for a in esp_bilesen)})"
               if esp_bilesen else " — B15/F1 ve F2 duzeltmeleriyle kapandi"))
    r.kosul("  OZET: PC riski YALNIZCA izolasyon kaynakli (bilesen arizasi degil)",
            not pc_bilesen,
            "tek senaryo D1b — 'kart izole degil' kisitindan geliyor, "
            "cozumu prosedurel (F10) + pil")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 7 — ONERILEN DUZELTMELER (her biri olculmus)
# ═══════════════════════════════════════════════════════════════════════

def bolum7(r):
    bolum(r, "BOLUM 7 — ONERILEN DUZELTMELER (her biri sayiyla gerekcelendirildi)")

    # ── F1: ADS gerilim girislerine seri direnc
    alt(r, "F1 · ✅ UYGULANDI — ADS gerilim girislerine 1K seri (R34/R35/R36)")
    r.bilgi("      SORUN (A1b): tampon doydugu her an ADS'in mutlak maksimumu")
    r.bilgi("      asiliyor; ariza degil, NORMAL menzil disi davranis.")
    r.bilgi("")
    zd = T.PGA_TABLO[NORMAL["pga"]][1]
    # ⚠ ADS'in Z_diff'i AIN_P ile AIN_N ARASINDAKI empedans (SBAS444 Tablo 2).
    #   Her diferansiyel cift IKI seri direnc goruyor: AIN0-AIN1 = R34 + R36,
    #   AIN2-AIN3 = R35 + R36. Yani hesaba giren direnc 1K degil 2K.
    r_diff = 2 * T.ADS_SERI_R
    hata = r_diff / zd * 100
    r.bilgi(f"      Kazanc bedeli: gerilim kanallarinda PGA SABIT "
            f"(+-{NORMAL['pga']:.3f} V).")
    r.bilgi(f"      ⚠ Diferansiyel cift IKI direnc goruyor (AIN_P'de R34/R35,")
    r.bilgi(f"        AIN_N'de R36) -> hesaba giren {r_diff/1e3:.0f}K, "
            f"{T.ADS_SERI_R/1e3:.0f}K degil.")
    r.bilgi(f"      Z_diff = {zd/1e6:.1f} Mohm -> hata "
            f"%{hata:.3f}, SABIT — kalibrasyon siliyor.")
    r.bilgi("      Kademe SICRAMASI YOK (DEVIR 4.14'un sorunu burada yok,")
    r.bilgi("      cunku gerilim kanallarinda PGA sabit).")
    r.kosul("      F1: kazanc bedeli ADS'in kendi kademe uyumundan kucuk",
            hata / 100 < T.ADS_PGA_UYUM,
            f"%{hata:.3f} < %{T.ADS_PGA_UYUM*100:.1f} (ADS'in kendi spek'i)")
    r.bilgi("")
    r.bilgi("      UC direnc: R34 (U3B->AIN0), R35 (U4A->AIN2),")
    r.bilgi("                 R36 (VREF->AIN1 VE AIN3).")
    r.bilgi("      R36 iki pini birden besliyor; ADS tek MUX'lu ve ciftleri")
    r.bilgi("      SIRAYLA donusturdugu icin her cift kendi olcumu sirasinda")
    r.bilgi("      1K/1K simetrik goruyor — capraz etkilesim yok.")
    r.bilgi("      Sont kolundakilerle birlikte toplam 5 adet 1K "
            "(envanterde 30 var).")

    # ── F2: sont kanali — EN KRITIK duzeltme
    alt(r, "F2 · ✅ UYGULANDI — ADS AKIM girislerine 1K seri (R38/R39)")
    r.bilgi("      SORUN (A6/A7): SONT_P ile ADS pini arasinda hicbir sey yok.")
    r.bilgi("      10R sont takiliyken 0.5 A yuk, ya da sont acik devre")
    r.bilgi("      kalirsa 5 V'luk bir yuk bile ADS'i olduruyor — ve kacak")
    r.bilgi("      3V3 rayina binerek ESP32'yi de tehdit ediyor.")
    r.bilgi("")
    r.bilgi("      NEDEN KELEPCE DIYODU DEGIL: SONT_P normal calismada")
    r.bilgi(f"      +-{0.256:.3f} V'a kadar saliniyor. BAT85 o gerilimde zaten")
    r.bilgi("      iletir (Schottky), silisyum diyot da 0.78 uA gecirir ->")
    r.bilgi("      100R uzerinde 78 uV hata. Sinyalin kendisi diyot esiginde")
    r.bilgi("      oldugu icin KELEPCE BU KANALDA KULLANILAMAZ.")
    r.bilgi("")
    r.bilgi(f"      {'seri R':>8} {'ADS mutlak':>12} {'ADS 10 mA':>11} "
            f"{'3V3 tehlike':>13} {'PGA sicramasi':>15}")
    r.bilgi("      " + "-" * 64)
    zd_ust = T.PGA_TABLO[2.048][1]
    zd_alt = T.PGA_TABLO[0.256][1]
    secim = None
    for rs in (0.0, 1e3, 2.7e3, 10e3):
        rtop = T.SONT_KELVIN_R + rs           # TEK bacak, ariza akimi icin
        # kazanc icin DIFERANSIYEL: iki bacak (R18+R38 ve R19+R39)
        r_diff = 2 * (T.SONT_KELVIN_R + rs)
        v_mutlak = T.ADS_MUTLAK_GIRIS_UST
        v_10ma = T.ADS_GIRIS_AKIM_MAKS * rtop + T.VDD + T.ADS_ESD_VF
        v_ray = T.ESP_BOSTA_AKIM * rtop + T.VDD + T.ADS_ESD_VF
        sicrama = (r_diff / zd_alt - r_diff / zd_ust) * 100
        if secim is None and rs > 0 and sicrama / 100 < 3 * T.ADS_PGA_UYUM:
            secim = (rs, v_10ma, v_ray, sicrama)
        r.bilgi(f"      {rs/1e3:6.1f}K {v_mutlak:10.2f}V {v_10ma:9.1f}V "
                f"{v_ray:11.1f}V {sicrama:13.3f} puan")
    r.bilgi("")
    r.bilgi("      'ADS 10 mA'   : bu SONT_P gerilimine kadar ADS giris akimi guvenli")
    r.bilgi("      '3V3 tehlike' : bunun ustunde kacak ESP32'nin bosta akimini asar")
    r.bilgi("      'PGA sicramasi': PGA +-2.048 ile +-0.256 arasinda kazanc farki,")
    r.bilgi("                       DIFERANSIYEL direncle (iki bacak: R18+R38")
    r.bilgi("                       ve R19+R39). Kiyas noktalari:")
    r.bilgi(f"                         ADS'in kendi kademe uyumu : "
            f"{T.ADS_PGA_UYUM*100:.1f} puan")
    r.bilgi("                         DEVIR 4.14'te REDDEDILEN   : 0.67 puan")
    r.bilgi("")
    r.kosul("      F2: 1K'nin PGA sicramasi, 4.14'te reddedilen degerin "
            "yarisindan az",
            secim is not None and secim[3] < 0.67 / 2,
            f"{secim[0]/1e3:.0f}K -> {secim[3]:.3f} puan "
            f"(4.14 = 0.67 puan)" if secim else "secim yok")
    r.bilgi("")
    r.bilgi("      ⚠ AMA ADS'in kendi spek'inden (0.1 puan) BUYUK. Akim kanali")
    r.bilgi("        PGA'yi oto-kademeledigi icin bu sicrama GERCEK.")
    r.bilgi("      → GEREKSINIM: akim kanali PGA KADEMESI BASINA kalibre")
    r.bilgi("        edilmeli. Bu zaten ADS'in kendi %0.1 spek'i yuzunden")
    r.bilgi("        gerekiyordu; R38/R39 onu 0.1'den "
            f"{secim[3]:.2f} puana cikariyor.")
    r.bilgi("        Kaynak empedansi SABIT ve BILINEN oldugu icin duzeltme")
    r.bilgi("        firmware'de tam olarak yapilabilir (4.14'ten farki bu:")
    r.bilgi("        orada hata TAMPONSUZ bolucunun degisken empedansindandi).")
    if secim:
        _taban = T.ADS_GIRIS_AKIM_MAKS * T.SONT_KELVIN_R + T.VDD + T.ADS_ESD_VF
        r.kosul("      F2: 1K ile ADS'in guvenli oldugu sont gerilimi 3 kat artiyor",
                secim[1] / _taban > 2.5,
                f"{_taban:.1f} V -> {secim[1]:.1f} V "
                f"({secim[1]/_taban:.1f}x)")
        r.kosul("      F2: 1K ile ESP32 47 V'luk bir sont arizasina kadar guvende",
                secim[2] > 40.0, f"3V3 rayi {secim[2]:.0f} V'a kadar yukselmiyor")
    r.bilgi("")
    r.bilgi("      KALAN RISK: 15 V ustu bir sont arizasinda ADS #1 yine gider")
    r.bilgi("      — ama ESP32 47 V'a kadar guvende. Kabul olcutu saglaniyor:")
    r.bilgi(f"      olen parca ADS1115 modulu ({FIYAT['U6/U7 (ADS1115 modulu)']:.0f} TL, soketli, 3 adet var).")

    # ── F3: R4'u bolmek
    alt(r, "F3 · R4 (220K) — SERI BOLME ya da GERILIM ANMASI YUKSEK parca")
    _gov4 = T.DIRENC_GOVDESI["R4"]
    _v4, _p4, _rth4 = T.DIRENC_GOVDE[_gov4]
    r.bilgi(f"      SORUN (A1): 615 V yanlis klemense baglanirsa R4 "
            f"{OLCUM['R4_v_615']:.0f} V ve")
    r.bilgi(f"      {OLCUM['R4_p_615']:.2f} W goruyor; film sicakligi "
            f"{T.ORTAM_C + OLCUM['R4_p_615']*_rth4:.0f} C "
            f"(izin verilen {T.DIRENC_FILM_TMAKS:.0f} C).")
    r.bilgi(f"      Govde ({_gov4}) sinirlari: {_v4:.0f} V calisma, {_p4:.2f} W.")
    r.bilgi(f"      Guc asimi {OLCUM['R4_p_615']/_p4:.1f}x — acilma esiginin "
            f"({T.DIRENC_ERIME_GUC_CARPANI:.0f}x) cok altinda, yani ACILMIYOR.")
    r.bilgi("")
    r.bilgi("      IKI YOL VAR (ikisi de N'yi ve firmware'i degistirmiyor):")
    r.bilgi("")
    r.bilgi("      YOL 1 — SERI BOLME, siradan 1/4W metal film:")
    _p_tam = OLCUM["R4_p_615"]            # BOLUM 2'de ngspice ile olculdu
    _rth14 = T.DIRENC_GOVDE["1/4W"][2]
    _t_tam = T.ORTAM_C + _p_tam * T.DIRENC_GOVDE[T.DIRENC_GOVDESI["R4"]][2]
    _en_az = None
    for k in (2, 3, 4):
        _t = T.ORTAM_C + (_p_tam / k) * _rth14
        if _t <= T.DIRENC_FILM_TMAKS and _en_az is None:
            _en_az = (k, _t)
    r.kosul("      F3: bolme, film sicakligini sinirin altina indiriyor",
            _en_az is not None,
            f"{_en_az[0]} parcaya bolununce {_en_az[1]:.0f} C "
            f"<= {T.DIRENC_FILM_TMAKS:.0f} C (bolunmemis halde "
            f"{_t_tam:.0f} C)" if _en_az else "cozum yok")
    r.bilgi("")
    r.bilgi("      ⚠ Gerilim tarafinda 2.0 carpani (DIRENC_ASIRI_YUK_CARPANI)")
    r.bilgi("        KISA SURELI (5 s) overload icindir. A1 SUREKLI bir")
    r.bilgi("        kosul, o yuzden burada gerilim olcutu olarak CALISMA")
    r.bilgi("        siniri kullanilmali:")
    _v_bir = OLCUM["R4_v_615"]
    for k in (2, 3, 4):
        _v = _v_bir / k
        _ok = _v <= T.DIRENC_GOVDE["1/4W"][0]
        r.bilgi(f"        {k} x 1/4W -> {_v:.0f} V/parca "
                f"(calisma siniri {T.DIRENC_GOVDE['1/4W'][0]:.0f} V) "
                f"{'OLUR' if _ok else 'olmaz'}")
    r.bilgi("")
    r.bilgi("      → 3 parca gerekiyor. Ama 73.3K standart bir deger DEGIL;")
    r.bilgi("        E96'da 73.2K var, 3 x 73.2K = 219.6K (%0.18 sapma,")
    r.bilgi("        kalibrasyonla siliniyor).")
    r.bilgi("")
    r.bilgi("      YOL 2 — 2 x 110K ama GERILIM ANMASI YUKSEK govde:")
    r.bilgi("        Vishay MRS25 ayni 0207 govdede 350 V veriyor")
    r.bilgi("        (Yageo minyaturu 200 V). 2 x 110K ile parca basina")
    _v2 = OLCUM["R4_v_615"] / 2
    _p2 = OLCUM["R4_p_615"] / 2
    _t2 = T.ORTAM_C + _p2 * T.DIRENC_GOVDE["1/4W"][2]
    r.bilgi(f"        {_v2:.0f} V (350 V sinirinin altinda) ve {_p2:.2f} W,")
    r.bilgi(f"        film {_t2:.0f} C. 110K E24 degeri, toplam TAM 220K.")
    r.kosul("      F3-YOL2: 350 V anmali govdeyle 2 parca YETIYOR",
            _v2 <= 350.0 and _t2 <= T.DIRENC_FILM_TMAKS,
            f"{_v2:.0f} V <= 350 V ve film {_t2:.0f} C <= "
            f"{T.DIRENC_FILM_TMAKS:.0f} C — N tam korunuyor")

    # ── F4: C1
    alt(r, "F4 · ✅ UYGULANDI — C1 100nF -> 1nF  [TL431 kararliligi]")
    r.bilgi("      SORUN (C4): 100nF, TI'in belgeledigi kararsiz bolgenin")
    r.bilgi("      (10 nF .. 2.2 uF) tam icinde. TL431 kondansator zaten")
    r.bilgi("      GEREKTIRMIYOR.")
    r.bilgi("      Envanterde hazir: C049 '1nF 50V seramik' x10.")
    r.kosul("      F4: sema guncellendi, 1nF guvenli bolgede",
            T.C1_SIMDI <= T.TL431_GUVENLI_C_ALT,
            f"{T.C1_SIMDI*1e9:.0f} nF <= {T.TL431_GUVENLI_C_ALT*1e9:.0f} nF")

    # ── F5: LM358 girislerine kelepce
    alt(r, "F5 · LM358 tampon girislerine 1N4148 kelepce (D5..D8)")
    r.bilgi("      SORUN (C1): alt bacak acik kalirsa LM358'in girisi 60 V'a")
    r.bilgi("      cikiyor (mutlak sinir 32 V).")
    r.bilgi("")
    r.bilgi("      ⚠ BU BEDAVA DEGIL — kelepce dugumu yuksek empedansli ve")
    r.bilgi("      diyot KACAGI dogrudan olcume biniyor. Iki yerlestirme var:")
    r.bilgi("")
    # 25 C -> 60 C: silisyum ters doyma akimi ~8-10 C'de iki katina cikar
    KAT_60C = 2 ** ((60 - 25) / 9.0)
    kacak_bat = T.BAT85_IR_TIPIK_3V_60C
    kacak_1n = 5e-9 * KAT_60C
    z_opamp = T.RC_R + NORMAL["thev"]          # tampon girisinde
    z_dugum = NORMAL["thev"]                   # bolucu dugumunde
    r.bilgi(f"      {'diyot':<10} {'60 C kacak':>11} {'yerlesim':<18} "
            f"{'Z':>8} {'dugum hatasi':>13} {'girise vurulmus':>16}")
    r.bilgi("      " + "-" * 80)
    secenekler = []
    for dad, ik in (("BAT85", kacak_bat), ("1N4148", kacak_1n)):
        for yad, z in (("tampon girisinde", z_opamp),
                       ("bolucu dugumunde", z_dugum)):
            dv = ik * z
            giris = dv * NORMAL["N"]
            fs_yuzde = giris / NORMAL["fs_sim"] * 100
            secenekler.append((dad, yad, dv, giris, fs_yuzde))
            r.bilgi(f"      {dad:<10} {ik*1e9:8.0f} nA {yad:<18} "
                    f"{z/1e3:6.1f}K {dv*1e3:10.3f} mV "
                    f"{giris*1e3:10.1f} mV ({fs_yuzde:.3f}%)")
    r.bilgi("")
    en_iyi = min(secenekler, key=lambda s: s[4])
    en_kotu = max(secenekler, key=lambda s: s[4])
    r.kosul("      F5: BAT85 bu dugumde KULLANILAMAZ (kacagi cok buyuk)",
            en_kotu[0] == "BAT85" and en_kotu[4] > 0.5,
            f"tampon girisinde %{en_kotu[4]:.2f} FS hata")
    r.kosul("      F5: en iyi yerlesim 1N4148 + BOLUCU DUGUMU",
            en_iyi[0] == "1N4148" and en_iyi[1].startswith("bolucu"),
            f"%{en_iyi[4]:.3f} FS — tampon girisine konsaydi "
            f"{[s for s in secenekler if s[0]=='1N4148' and s[1].startswith('tampon')][0][4]/en_iyi[4]:.1f} kat kotu")
    r.bilgi("")
    r.bilgi(f"      TAKAS: %{en_iyi[4]:.3f} FS hata, kartin +-%0.1 hedefinin")
    r.bilgi(f"      {en_iyi[4]/0.1*100:.0f}%'i. Buyuk kismi SABIT ofset (kalibre edilir);")
    r.bilgi("      kalan sicaklik surüklenmesidir.")
    r.bilgi("")
    r.bilgi("      KARAR KULLANICININ: C1 senaryosu (alt bacak acik) bir LEHIM")
    r.bilgi("      arizasi. Delikli plakete SAGLAM lehimlenmis tek bir direnc")
    r.bilgi("      icin dusuk olasilikli. Alternatif (bedava): firmware'de")
    r.bilgi("      makullük denetimi — giris yokken okuma tam olcege")
    r.bilgi("      dayaniyorsa 'bolucu alt bacagi kopmus olabilir' uyarisi.")
    r.bilgi(f"      Envanterde 1N4148 var: 8 adet (4 gerekiyor).")

    # ── F6: kelepce referansi
    alt(r, "F6 · ❌ DEGERLENDIRILDI VE REDDEDILDI — yerine B18/F12")
    r.bilgi("      ONERI: GPIO kelepcelerinin ust ucunu +3V3 yerine TL431")
    r.bilgi("      rayina (2.495 V) baglamak. Kullanici 2026-09-09'da bunu")
    r.bilgi("      ONAYLADI; B18 (sim3_kelepce.py) uygulamadan once olctu ve")
    r.bilgi("      IKI SEY buldu — o yuzden UYGULANMADI.")
    bat_vf = T.BAT85_VF_MAKS[10e-3]
    kel_ust = T.TL431_V + bat_vf
    r.kosul("      F6: onerinin ASIL iddiasi dogruydu",
            kel_ust < T.ESP_MUTLAK_PIN_UST,
            f"kelepce {kel_ust:.3f} V < {T.ESP_MUTLAK_PIN_UST:.2f} V")
    r.bilgi("")
    r.bilgi("      🔴 1. BELGELENMEMIS BEDEL. B15 yalnizca skop menzilinden")
    r.bilgi(f"         soz ediyordu ({T.SKOP_TAVAN*T.SKOP_N:.0f} V -> "
            f"{T.KELEPCE_TL_TAVAN*T.SKOP_N:.0f} V). Ama ayni kelepce HIZLI")
    r.bilgi("         AKIM yolunda da var:")
    hizli_eski = (T.SKOP_TAVAN - T.VREF) / T.HIZLI_G
    hizli_yeni = (T.KELEPCE_TL_TAVAN - T.VREF) / T.HIZLI_G
    r.bilgi(f"           hizli yol tam olcek {hizli_eski*1e3:.1f} mV -> "
            f"{hizli_yeni*1e3:.1f} mV (%{(1-hizli_yeni/hizli_eski)*100:.0f} kayip)")
    r.kosul("      F6: hizli yol ADS'in KENDI kirpmasindan once doyardi",
            hizli_yeni < T.ADS_AKIM_KIRPMA,
            f"{hizli_yeni*1e3:.1f} mV < {T.ADS_AKIM_KIRPMA*1e3:.0f} mV — "
            f"tepe yakalamak icin var olan yol, yavas yoldan once kirpar")
    r.bilgi("")
    r.bilgi("      🔴 2. ASIL KALINTIYI KAPATMIYOR. TL431 acik devre olursa")
    r.bilgi("         ray yine 9.9 V'a tirmaniyor — F6'yla da, F6'siz da.")
    r.bilgi("")
    r.bilgi("      ✅ YERINE UYGULANAN (B18/F12): iki stok direnci.")
    r.bilgi(f"           R26/R33  {T.R_SERI_ESKI/1e3:.1f}K -> "
            f"{T.R_SERI/1e3:.0f}K")
    r.bilgi(f"           R41      YENI {T.BOSALTMA_R_3V3/1e3:.0f}K "
            f"(+3V3 -> GND bosaltma)")
    r.bilgi("         Pay 18 -> 1930 mV, TL431'den BAGIMSIZ, skop ve hizli")
    r.bilgi("         akim menzilleri HIC degismiyor. Olcumler: B18.")

    # ── F7: orta nokta tamponu
    alt(r, "F7 · Orta nokta tamponu — kapasitif yuk ve akim")
    r.bilgi("      SORUN (B4a/B4b): LM358'in kapasitif yuk siniri 50 pF;")
    r.bilgi(f"      ayirma kondansatorleri {T.DEKUPLAJ_ADET*T.DEKUPLAJ_BIR*1e9:.0f} nF. "
            f"Ayrica cekme akimi")
    r.bilgi(f"      sicakta yalnizca {T.LM358_SINK_MIN_SICAK*1e3:.0f} mA garanti.")
    r.bilgi("")
    r.bilgi("      SECENEK 1 — 10 R yalitim direnci (0 TL, elde):")
    r.bilgi("        tampon cikisi -[10R]- GND dugumu, geri besleme")
    r.bilgi("        direncin ARDINDAN. Kapasitif yuku op-amp'ten ayirir.")
    r.bilgi(f"        Bedeli: {T.ORTA_NOKTA_YUK_7805*1e3:.1f} mA x 10 R = "
            f"{T.ORTA_NOKTA_YUK_7805*10*1e3:.1f} mV GND kaymasi.")
    r.bilgi("")
    r.bilgi(f"      SECENEK 2 — TLE2426 (TO-92, delikli uyumlu):")
    r.bilgi(f"        {T.TLE2426_VIN_MAKS:.0f} V giris, {T.TLE2426_SINK_24V*1e3:.0f} mA cekme / "
            f"{T.TLE2426_SOURCE_24V*1e3:.0f} mA kaynak,")
    r.bilgi(f"        {T.TLE2426_IQ*1e6:.0f} uA bosta, kapasitif yuk haritasi YAYINLANMIS.")
    r.kosul("      F7: TLE2426 kelepce arizasindaki yuku rahat karsiliyor",
            T.TLE2426_SINK_24V > 2 * T.ORTA_NOKTA_KELEPCE_KANAL_NEG * 2,
            f"{T.TLE2426_SINK_24V*1e3:.0f} mA vs "
            f"{4*T.ORTA_NOKTA_KELEPCE_KANAL_NEG*1e3:.1f} mA")
    r.bilgi("")
    r.bilgi("      🔴 HER IKI SECENEKTE DE GECERLI KURAL: ESP32'nin dusurucu")
    r.bilgi(f"      regulatoru +12 V'tan BESLENMEZ. {T.ORTA_NOKTA_YUK_ESP*1e3:.0f} mA'lik donus")
    r.bilgi("      akimi hicbir orta nokta tamponunun karsilayamayacagi kadar")
    r.bilgi("      buyuk. ESP32 USB'den ya da AYRI bir kaynaktan beslenmeli.")

    # ── F8: ters polarite
    alt(r, "F8 · +-12 V girisi: mekanik anahtarlama + 50 mA sigorta")
    r.bilgi("      SORUN (B3): ters takma iki TL072'yi de oldurur ve TVS ile")
    r.bilgi("      korunamaz (SMBJ24A 38.9 V'ta kelepceliyor, LM358 siniri 32 V).")
    r.bilgi("")
    yuk = 4 * T.TL072_IQ_MAKS
    r.kosul("      F8: 50 mA sigorta yuke gore bol pay birakiyor",
            50e-3 / yuk >= 4, f"{50e-3/yuk:.0f}x  (+-12 V yuku {yuk*1e3:.0f} mA maks)")
    r.bilgi("      Mekanik anahtarlama: sifir gerilim dusumu, sifir maliyet,")
    r.bilgi("      sifir yeni ariza modu. Seri Schottky ise 30 V'luk BAT85 ile")
    r.bilgi("      yapilamaz (40 V gerekiyor) ve ray gerilimini dusurur.")

    # ── F9: yerlesim
    alt(r, "F9 · Delikli plaket yerlesimi — 615 V icin SAYI")
    n = math.ceil((T.IEC60664_CREEPAGE_TAKVIYELI + T.DELIKLI_PAD_ETKIN_MM)
                  / T.DELIKLI_ADIM)
    r.bilgi(f"      Sema bugun 'delik atlayarak' diyor ama SAYI vermiyor.")
    r.bilgi(f"      IEC 60664-1 takviyeli kacak yolu {T.IEC60664_CREEPAGE_TAKVIYELI:.1f} mm")
    r.bilgi(f"      -> {T.DELIKLI_ADIM:.2f} mm adimda, ped {T.DELIKLI_PAD_ETKIN_MM:.2f} mm "
            f"dusulunce {n} delik = {n*T.DELIKLI_ADIM - T.DELIKLI_PAD_ETKIN_MM:.2f} mm "
            f"bakirdan bakira (B48: merkezden merkeze sayilan 5 delik yetmiyordu).")
    r.bilgi(f"      IPC-2221B hava araligi (615 V, kaplamasiz) "
            f"{T.IPC2221_KACAK_615V:.2f} mm -> "
            f"{math.ceil(T.IPC2221_KACAK_615V/T.DELIKLI_ADIM)} delik.")
    r.bilgi("")
    r.bilgi(f"      Ayrica: direnc govdesinin CEVREYE karsi SUREKLI yalitimi")
    r.bilgi(f"      yalnizca {T.DIRENC_YALITIM_SUREKLI:.0f} V. 615 V zincirinin tepesi bunun")
    r.bilgi(f"      {615.0/T.DIRENC_YALITIM_SUREKLI:.0f} katinda -> HV zinciri toprak duzleminden ve")
    r.bilgi("      komsu izlerden UZAK, tercihen havada askida kurulmali.")
    r.kosul("      F9: 615 V icin gereken aralik sayiya baglandi",
            n >= 4 and n * T.DELIKLI_ADIM - T.DELIKLI_PAD_ETKIN_MM >= T.IEC60664_CREEPAGE_TAKVIYELI,
            f"{n} delik ({n*T.DELIKLI_ADIM - T.DELIKLI_PAD_ETKIN_MM:.2f} mm bakirdan bakira) "
            f"— takviyeli yalitim")

    # ── F10: prosedur
    alt(r, "F10 · Prosedur — donanimla cozulemeyen tek sey")
    r.bilgi("      D1b (kart GND'si canliya + USB takili) bir BILESEN arizasi")
    r.bilgi("      degil, bir KULLANIM hatasi. Hicbir ucuz donanim onlemi")
    r.bilgi(f"      ~{T.SEBEKE_RMS/0.7:.0f} A'lik bir ariza akimini durduramaz.")
    r.bilgi("")
    r.bilgi("      KURALLAR (kutunun uzerine yazilmali):")
    r.bilgi("        1. HV bagliyken USB TAKILI OLMAYACAK.")
    r.bilgi("        2. Once GND klemensi, sonra HV ucu baglanir; sokerken ters.")
    r.bilgi("        3. GND klemensi HER ZAMAN devrenin en dusuk potansiyeline.")
    r.bilgi("        4. Programlama/hata ayiklama YALNIZCA HV sokulmusken.")
    r.bilgi("        5. 24 V kaynagin yalitimi ohmmetreyle DOGRULANMIS olacak.")
    r.bilgi("        6. ENDÜKTIF yuk olculurken yukun uzerinde SERBEST GECIS")
    r.bilgi("           (freewheel) diyodu olacak — A10'un kapatamadigi tek")
    r.bilgi("           bilesen senaryosu bu.")
    r.bilgi("        7. Yuk kablosu KISA olacak (parazitik endüktans dogrudan")
    r.bilgi("           L·di/dt tepesine ceviriyor — A10a).")
    r.bilgi("        8. ACMA SIRASI: once USB, sonra 24 V. Kapatirken once")
    r.bilgi("           24 V. (B1: donanimda B18/F12 ile cozuldu, bu kural")
    r.bilgi("           IKINCI savunma — bedava.)")
    r.bilgi("")
    r.bilgi("      Kalici cozum: 4 hucre daha 18650 + Wi-Fi (DEVIR 5.12.23).")
    r.bilgi(f"      O zaman bile kullanici icin sinir gecerli: yuzen bir alette")
    r.bilgi(f"      toprağa gore {T.YUZEN_ALET_TOPRAGA_SINIR_RMS:.0f} V rms (Tektronix) — 615 V")
    r.bilgi("      YALITIMLI KUTU olmadan ASLA.")


    # ═══════════════════════════════════════════════════════════════
    #  BOLUM 7 SONU — DURUM TABLOSU (semadan DOGRULANIYOR)
    # ═══════════════════════════════════════════════════════════════
    bolum(r, "BOLUM 7 SONU — HANGI ONERI UYGULANDI, HANGISI ACIK")
    r.bilgi("  'Uygulandi' iddiasi SEMADAN dogrulaniyor: netlist3.net'te")
    r.bilgi("  o parca gercekten var mi diye bakiliyor. Boylece bu tablo")
    r.bilgi("  semayla sessizce ayrisamaz.")
    r.bilgi("")
    import re as _re2
    _n = (BURASI / "netlist3.net")
    _var = set()
    _deger = {}
    if _n.exists():
        _t = _n.read_text(encoding="utf-8", errors="replace")
        for _ref, _val in _re2.findall(
                r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\)', _t):
            _var.add(_ref)
            _deger[_ref] = _val

    ONERILER = [
        ("F1", "ADS gerilim girislerine 1K seri (R34/R35/R36)",
         ["R34", "R35", "R36"], None),
        ("F2", "ADS akim girislerine 1K seri (R38/R39)",
         ["R38", "R39"], None),
        ("F3", "R4 bolme ya da yuksek gerilim anmali govde",
         [], "ACIK — satin alma karari kullanicinin"),
        ("F4", "C1 100nF -> 1nF (TL431 kararliligi)",
         [], "C1" if _deger.get("C1") == "1nF" else None),
        ("F5", "LM358 giris kelepceleri (1N4148)",
         [], "ACIK — takas olculdu, karar kullanicinin"),
        ("F6", "Kelepce ust ucu TL431 rayina",
         [], "ACIK — skop menzilini dusuruyor, karar kullanicinin"),
        ("F7", "Orta nokta tamponu (10R yalitim / TLE2426)",
         [], "ACIK — B11 isi, ray henuz kurulmadi"),
        ("F8", "+-12 V girisi mekanik anahtarlama + sigorta",
         [], "ACIK — B11 isi"),
        ("F9", f"Delikli plaket 615 V araligi ({n} delik)",
         [], "yerlesim3.py planda sayisal olarak siniyor (B48)"),
        ("F10", "Prosedur — 7 kural (kutu etiketi)",
         [], "ACIK — kutu yapilinca yazilacak"),
    ]
    r.bilgi(f"  {'kod':<5} {'oneri':<48} {'durum':<12} parcalar")
    r.bilgi("  " + "-" * 88)
    uygulanan = []
    for kod, ad, refler, notu in ONERILER:
        if refler:
            tamam = all(x in _var for x in refler)
            durum = "UYGULANDI" if tamam else "EKSIK"
            ek = ", ".join(f"{x}={_deger.get(x,'?')}" for x in refler)
            if tamam:
                uygulanan.append(kod)
        elif notu == "C1":
            durum, ek = "UYGULANDI", f"C1={_deger.get('C1')}"
            uygulanan.append(kod)
        else:
            durum, ek = "ACIK", notu or ""
        r.bilgi(f"  {kod:<5} {ad:<48} {durum:<12} {ek}")
    r.bilgi("")
    r.kosul("  DURUM: semada uygulanmis olmasi gereken uc oneri GERCEKTEN var",
            set(uygulanan) == {"F1", "F2", "F4"},
            f"uygulanan: {', '.join(sorted(uygulanan))} — netlist'ten "
            f"dogrulandi")
    r.bilgi("")
    r.bilgi("  ACIK OLANLAR NEDEN ACIK:")
    r.bilgi("    F3/F5/F6 — TAKAS iceriyor, sayisi olculdu, karar KULLANICININ")
    r.bilgi("    F7/F8    — +-12 V rayi (B11) henuz kurulmadi")
    r.bilgi("    F9/F10   — montaj ve prosedur; donanim kurulunca")
    r.bilgi("")
    r.bilgi("  🔴 B15 KAPSAMI DISINDA KALAN, KAPATILMAMIS IKI IS:")
    r.bilgi("    A10  endüktif yuk — freewheel diyodu (prosedur, F10/6)")
    r.bilgi("    B16  akim kanali ortusme suzgeci + hizli yol bant genisligi")
    r.bilgi("         (DEVIR 5.12.24 sonu — YENI IS KALEMI)")


# ═══════════════════════════════════════════════════════════════════════

def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B15 — ARIZA VE ZORLAMA SIMULASYONU")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  ⚠ Bu adim TASARIMI sinar, kurulmus bir KARTI degil. Buradaki")
    r.bilgi("    her sayi HESAP ve SIMULASYON — tezgah olcumu DEGIL.")
    bolum0(r)
    bolum1(r)
    bolum2(r)
    bolum2b(r)
    bolum2c(r)
    bolum2d(r)
    bolum2e(r)
    bolum3(r)
    bolum4(r)
    bolum5(r)
    bolum6(r)
    bolum7(r)
    tamam = r.yazdir()
    import shutil
    for d in BURASI.glob("_b15_*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    # Ariza senaryolarinin uc tanesi SIMULE EDILEMEZ — malzemenin
    # kendisi karar veriyor.
    tezgah("B15 Ariza ve zorlama", [
        ("Bir direnc asiri yukte ACIK mi KISA mi devre kaliyor",
         "Butun ariza matrisi ACIK devre varsayiyor. KISA kalirsa "
         "koruma zinciri ters yonde calisir. Olcum: feda edilecek bir "
         "1/4 W direnci bilerek yak, sonra ohmmetreyle bak"),
        ("Gercek LM358 giris jonksiyonunun kirilma gerilimi",
         "Makromodelde bu yok. Veri sayfasi mutlak maksimumu veriyor ama "
         "kirilma noktasini vermiyor. Ariza akimi buna gore akar"),
        ("Delikli plakette 615 V'ta ark ve yuzey kacagi",
         "Simulasyon yalnizca IDEAL yalitim biliyor. Olcum: HV bolumu "
         "besle, karanlikta korona ara, nemli gunde tekrarla. "
         "Ark varsa iletken araligi acilacak"),
        ("Emniyet uyarilari kartin USTUNDE yaziyor mu",
         "Ariza matrisinin yarisi KULLANICI hatasi. J7/J3 baypasi ve "
         "615 V ucu, kartin uzerinde etiketli olmali — belgede olmasi "
         "tezgahta ise yaramiyor"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
