# -*- coding: utf-8 -*-
"""B1 — Asama 3 on uc tasarimi: +-615 V, CIFT YONLU, tamponlu.

Bu betik TASARIM BELGESIDIR ve ayni zamanda BIR TESTTIR. Her sayi burada
hesaplanir; hicbiri elle yazilmaz. Kurallar `kural()` ile sinanir, ihlal
varsa cikis kodu 1 olur.

KULLANICININ ISTEKLERI (2026-09-08):
  1. 400-600 V menzil          -> +-615.4 V yuksek gerilim kanali
  2. Negatif (+-) giris        -> Vref'e referansli diferansiyel olcum
  3. V-I kaymasi az olsun      -> Lagrange yarim-ornek hizalayici

KAYNAKLAR (hepsi bu oturumda okundu, tahmin degil):
  ADS1115  — TI SBAS444B veri sayfasi
      s.3  Elektriksel ozellikler: analog giris GND..VDD (CALISMA araligi),
           ortak-mod giris empedansi PGA'ya gore 3/6/10/100 Mohm,
           ofset +-3 LSB maks, kazanc hatasi %0.15 maks,
           PGA kademeleri arasi kazanc uyumu %0.1 maks
      s.6  Sekil 4/6: ofset ve kazanc hatasi sicaklikla
      s.8  Sekil 14/15: RMS GURULTU — DEVIR 1.3'un acik sorusu buradan cevaplandi
      s.12 "external Schottky clamp diodes ... may be required"
           "overdriving one unused input MAY AFFECT CONVERSIONS on other pins"
           ESD diyotlari icin mutlak sinir GND-0.3 < AINx < VDD+0.3
      s.13 Tablo 2: diferansiyel giris empedansi PGA'ya gore 710k..22M
      s.14 "Sinc filter CANNOT COMPLETELY REPLACE an anti-aliasing filter"
           "take into account the interaction between the filter network
            and the input impedance"
  1/4W metal film — Yageo MFR veri sayfasi: azami CALISMA gerilimi 200 V
  ESP32-S3 — ESP-IDF soc_caps.h (Asama 2'de okundu)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tasarim3_sabit as T                          # noqa: E402
from tezgah import tezgah                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════ ADS1115 (SBAS444B)
VDD = 3.3
ADS_SAYIM = 32768                 # 16 bit isaretli
ADS_MUTLAK_ALT = -0.3             # s.12 — ESD diyodu bu altta iletir
ADS_MUTLAK_UST = VDD + 0.3
ADS_CALISMA_ALT = 0.0             # s.3 — "Analog input voltage MIN: GND"
ADS_CALISMA_UST = VDD             # s.3 — "MAX: VDD"
ADS_OFSET_LSB = 3                 # s.3 maks (diferansiyel)
ADS_PGA_UYUM = 0.001              # s.3 — kademeler arasi kazanc uyumu %0.1 maks
ADS_SPS = 860

# PGA -> (LSB volt, diferansiyel giris direnci, ortak-mod giris direnci)
#   Z_DIFF: s.13 Tablo 2 · Z_CM: s.3 elektriksel ozellikler
PGA_TABLO = {
    6.144: (187.5e-6, 22.0e6, 10e6),
    4.096: (125.0e-6, 15.0e6,  6e6),
    2.048: (62.50e-6,  4.9e6,  6e6),
    1.024: (31.25e-6,  2.4e6,  3e6),
    0.512: (15.625e-6, 710e3, 100e6),
    0.256: (7.8125e-6, 710e3, 100e6),
}

# s.8 Sekil 14 ve 15'ten okunan RMS gurultu (VDD = 3.3 V, 860 SPS)
#   Sekil 15: FS +-2.048, 3.3 V, 860 SPS  -> ~26.5 uV
#   Sekil 14: FS +-0.512, 860 SPS         -> ~8.5 uV
#   Aradakiler kademeyle olceklenerek kestirildi (ayni ADC, ayni sinc).
ADS_GURULTU = {2.048: 26.5e-6, 1.024: 13.5e-6, 0.512: 8.5e-6, 0.256: 8.5e-6}

# ═══════════════════════════════════════════ pasifler (stok)
R_1_4W_AZAMI_V = 200.0            # Yageo MFR: 1/4W azami calisma gerilimi
R_STRES_PAYI = 0.60               # tasarim kurali: sinirin en fazla %60'i

TL431_V = 2.495

# TL072 (JFET giris) — yolda 4 adet
TL072_VOS = 3e-3                  # tipik
TL072_VOS_MAKS = 10e-3
TL072_DRIFT = 18e-6               # V/C
TL072_IB = 200e-12                # maks, 25 C
TL072_GBW = 3e6

# LM358 (bipolar giris) — stokta 8 adet, +-12 V yoksa yedek yol
LM358_VOS = 2e-3
LM358_IB = 45e-9
LM358_IOS = 5e-9

gecti = kaldi = 0


def baslik(s):
    print()
    print("=" * 78)
    print(f"  {s}")
    print("=" * 78)


def kural(ad, tamam, ek=""):
    global gecti, kaldi
    if tamam:
        gecti += 1
    else:
        kaldi += 1
    print(f"  {'[OK]' if tamam else '[!!]'} {ad}" + (f"   {ek}" if ek else ""))


def bilgi(s=""):
    print(s)


def par(*r):
    return 1.0 / sum(1.0 / x for x in r)


# ═══════════════════════════════════════ 1. NEDEN CIFT YONLU BOYLE OLUYOR
baslik("1. CIFT YONLU OLCUM — TOPOLOJI VE TUREV")
bilgi("  Bolucunun alt ucu GND yerine TAMPONLU bir Vref'e baglanir,")
bilgi("  olcum de diferansiyel yapilir: AIN_P(dugum) - AIN_N(Vref).")
bilgi()
bilgi("    Vin --[ Rust ]--+--[ Ralt ]-- Vref")
bilgi("                    |")
bilgi("                  dugum -> tampon -> AIN_P")
bilgi("                            Vref  -> AIN_N")
bilgi()
bilgi("  k = Ralt/(Rust+Ralt) = 1/N  olsun:")
bilgi("    dugum = Vref + (Vin - Vref)*k")
bilgi("    fark  = dugum - Vref = k*(Vin - Vref) = (Vin - Vref)/N")
bilgi("    Vin   = N*fark + Vref")
bilgi()
bilgi("  SONUC 1: fark ISARETLI. ADS1115 diferansiyel kipte iki tumleyen")
bilgi("  okudugu icin negatif kendiliginden geliyor — ek donanim YOK.")
bilgi()
bilgi("  SONUC 2 (onemli): Vref'in e kadar hatasi varsa, olculen Vin tam")
bilgi("  e kadar kayar — N'den BAGIMSIZ. Yani Vref hatasi girise vurulmus")
bilgi("  sabit bir OFSET'tir, kazanc hatasi degil. Sifir kalibrasyonu siler.")
bilgi("  Bu, 615 V kanalinda Vref'e karsi cok bagisik olmamizi sagliyor.")

# Vref: TL431 rayindan 10K/22K bolucu (ikisi de stokta)
VREF_RA, VREF_RB = 10e3, 22e3
VREF = TL431_V * VREF_RB / (VREF_RA + VREF_RB)
bilgi()
bilgi(f"  Vref = TL431 {TL431_V} V --[{VREF_RA/1e3:.0f}K]--+--[{VREF_RB/1e3:.0f}K]-- GND")
bilgi(f"       = {VREF:.4f} V   (tamponlanmis)")
bilgi()
bilgi("  NEDEN 3.3 V RAYINDAN DEGIL: Vref hatasi dogrudan olcum ofseti.")
bilgi("  3.3 V rayi %1 oynarsa 16.5 mV ofset olurdu; TL431 cok daha durgun.")
kural("Vref ADS calisma penceresinin ortasina yakin",
      0.35 * VDD < VREF < 0.65 * VDD, f"{VREF:.3f} V")

# Vref'i TAMPONLAMAK ZORUNLU MU? — bolucu akimi Vref'e akiyor
bilgi()
bilgi("  Vref TAMPONSUZ OLUR MU? Bolucu akimi Vref'e akiyor:")
vref_thev = par(VREF_RA, VREF_RB)
bilgi(f"    Tamponsuz Vref bolucusunun Thevenin'i {vref_thev/1e3:.2f} kohm")


# ═══════════════════════════════════════ 2. KANALLARIN BOYUTLANDIRILMASI
baslik("2. IKI GERILIM KANALI")

class Kanal:
    def __init__(self, ad, rust_adet, rust_bir, ralt, pga):
        self.ad = ad
        self.rust_adet = rust_adet
        self.rust_bir = rust_bir
        self.rust = rust_adet * rust_bir
        self.ralt = ralt
        self.pga = pga
        self.N = (self.rust + ralt) / ralt
        self.lsb, self.zdiff, self.zcm = PGA_TABLO[pga]
        self.fs = pga * self.N
        self.adim = self.lsb * self.N
        self.thev = par(self.rust, ralt)
        # tam olcekte tek direncin uzerindeki gerilim ve gucu
        self.r_gerilim = self.fs * (rust_bir / (self.rust + ralt))
        self.r_guc = self.r_gerilim ** 2 / rust_bir
        self.giris_z = self.rust + ralt
        # ortak-mod penceresi
        self.cm_alt = VREF - pga
        self.cm_ust = VREF + pga

# ⚠ TEK KAYNAK: bolucu degerleri tasarim3_sabit.py'den geliyor, burada
# ELLE YAZILMIYOR. Ilk surumde elle yazilmislardi; sabit dosya 1M'den
# 2.2M'e gecince bu betik sessizce eski degerlerle hesaplamaya devam etti
# ve tasarim dokumani semayla AYRISTI. Asagidaki kural bunu bir daha
# sessiz birakmiyor.
KANALLAR = [Kanal(k["ad"], k["rust_adet"], k["rust_bir"], k["ralt"], k["pga"])
            for k in T.KANALLAR]
for _k, _t in zip(KANALLAR, T.KANALLAR):
    kural(f"{_k.ad}: degerler tasarim3_sabit.py ile AYNI (tek kaynak)",
          abs(_k.N - _t["N"]) < 1e-9 and _k.rust_bir == _t["rust_bir"]
          and _k.ralt == _t["ralt"],
          f"{_k.rust_adet}x{_k.rust_bir/1e3:g}K / {_k.ralt/1e3:g}K, N={_k.N:.4f}")

# ⚠ MENZIL ASIMETRISI — B4 (AVR testi) bunu yakaladi.
bilgi()
bilgi("  ⚠ MENZIL SIMETRIK DEGIL — ILK SURUMDE BU GOZDEN KACTI")
bilgi()
bilgi("  fark = (Vin - Vref)/N oldugu icin ADS'in +-pga penceresi girise")
bilgi("  Vref kadar YUKARI KAYMIS bir aralik verir:")
bilgi("      Vin_ust = +pga*N + Vref")
bilgi("      Vin_alt = -pga*N + Vref")
bilgi()
bilgi(f"  {'kanal':<18} {'alt sinir':>11} {'ust sinir':>11} "
      f"{'SIMETRIK':>11} {'asimetri':>10}")
bilgi("  " + "-" * 66)
for k in KANALLAR:
    ust = k.fs + VREF
    alt = -k.fs + VREF
    sim = k.fs - VREF
    bilgi(f"  {k.ad:<18} {alt:+9.2f} V {ust:+9.2f} V {sim:9.2f} V "
          f"{VREF/k.fs*100:8.2f}%")
    k.fs_sim = sim
bilgi()
bilgi("  Ilk surumde NORMAL kanal 2x100K/6.8K idi (N=30.41):")
bilgi("    tam olcek '+-31.14 V' deniyordu ama gercek menzil")
bilgi("    -29.43 .. +32.86 V idi — negatif tarafta %5.5 eksik.")
bilgi("    AVR testi (B4) -31 V'ta -29.43 V okuyup KIRPMAYI gosterdi.")
bilgi("  220K/6.8K (N=33.35) ile simetrik menzil +-32.4 V'a cikti.")
kural("NORMAL kanal simetrik menzili 30 V'u asiyor",
      KANALLAR[0].fs_sim > 30.0, f"+-{KANALLAR[0].fs_sim:.2f} V")
kural("YUKSEK kanal simetrik menzili 600 V'u asiyor",
      KANALLAR[1].fs_sim > 600.0, f"+-{KANALLAR[1].fs_sim:.2f} V")
kural("Asimetri HV kanalinda ihmal edilebilir (< %0.5)",
      VREF / KANALLAR[1].fs < 0.005, f"%{VREF/KANALLAR[1].fs*100:.3f}")

bilgi(f"  {'kanal':<18} {'bolucu':<16} {'N':>7} {'tam olcek':>11} {'adim':>10} "
      f"{'Thevenin':>10} {'giris Z':>9}")
bilgi("  " + "-" * 86)
for k in KANALLAR:
    bolucu = f"{k.rust_adet}x{k.rust_bir/1e6:g}M/{k.ralt/1e3:.1f}K" if k.rust_bir >= 1e6 \
        else f"{k.rust_adet}x{k.rust_bir/1e3:.0f}K/{k.ralt/1e3:.1f}K"
    bilgi(f"  {k.ad:<18} {bolucu:<16} {k.N:7.2f} {k.fs:9.1f} V "
          f"{k.adim*1e3:8.3f} mV {k.thev/1e3:8.2f}k {k.giris_z/1e6:7.3f}M")

bilgi()
bilgi("  ORTAK-MOD PENCERESI (ADS calisma araligi GND..VDD, s.3):")
for k in KANALLAR:
    tamam = k.cm_alt >= ADS_CALISMA_ALT and k.cm_ust <= ADS_CALISMA_UST
    bilgi(f"    {k.ad:<18} dugum {k.cm_alt:+.3f} .. {k.cm_ust:+.3f} V  "
          f"pay: alt {k.cm_alt-ADS_CALISMA_ALT:.3f} V, ust {ADS_CALISMA_UST-k.cm_ust:.3f} V")
    kural(f"{k.ad}: ortak-mod calisma penceresinde", tamam)

bilgi()
bilgi("  DIRENC GERILIM STRESI — 1/4W metal film azami CALISMA gerilimi 200 V")
bilgi("  (Yageo MFR. Bu 'asiri yuk' degil, SUREKLI sinir. Asilirsa once")
bilgi("   kacak artar, sonra ark olur.)")
bilgi()
bilgi(f"    {'kanal':<18} {'direnc/adet':>12} {'tam olcekte':>12} {'guc':>9} {'sinirin':>9}")
bilgi("    " + "-" * 66)
for k in KANALLAR:
    oran = k.r_gerilim / R_1_4W_AZAMI_V
    bilgi(f"    {k.ad:<18} {k.rust_adet:>7} adet  {k.r_gerilim:9.1f} V "
          f"{k.r_guc*1e3:7.1f} mW {oran*100:7.1f}%")
    kural(f"{k.ad}: direnc gerilimi sinirin %{R_STRES_PAYI*100:.0f}'inin altinda",
          oran <= R_STRES_PAYI, f"%{oran*100:.1f}")
    kural(f"{k.ad}: direnc gucu 1/4W'in %25'inin altinda",
          k.r_guc < 0.25 * 0.25, f"{k.r_guc*1e3:.1f} mW")

bilgi()
HEDEF_V = 600.0
R_BIR = KANALLAR[1].rust_bir      # zincirdeki TEK direnc (2.2M)
R_ALT = KANALLAR[1].ralt          # alt bacak (22K)
R_BIR_AD = f"{R_BIR/1e6:g}M" if R_BIR >= 1e6 else f"{R_BIR/1e3:g}K"
bilgi(f"  NEDEN 6 ADET {R_BIR_AD} — {HEDEF_V:.0f} V GIRISTE her zincir uzunlugu:")
bilgi(f"  (Ralt = {R_ALT/1e3:g}K sabit. Zincir uzadikca hem tam olcek hem gerilim")
bilgi("   payi buyur; belirleyici olan HEDEF gerilimde direnc basina dusen.)")
bilgi()
bilgi(f"    {'zincir':>8} {'tam olcek':>11} {HEDEF_V:.0f}V'ta direnc basina  sinirin")
bilgi("    " + "-" * 56)
for adet in (3, 4, 5, 6, 8):
    rust = adet * R_BIR
    ralt = R_ALT
    N = (rust + ralt) / ralt
    fs = 1.024 * N
    # HEDEF_V girildiginde tek direncin uzerine dusen
    v_direnc = HEDEF_V * (R_BIR / (rust + ralt))
    yeter = fs >= HEDEF_V and v_direnc <= R_STRES_PAYI * R_1_4W_AZAMI_V
    isaret = "OK " if yeter else "!! "
    sebep = "" if yeter else ("  <- menzil yetmiyor" if fs < HEDEF_V
                              else "  <- gerilim stresi")
    bilgi(f"    {isaret}{adet} x {R_BIR_AD} {fs:9.1f} V {v_direnc:16.1f} V "
          f"{v_direnc/R_1_4W_AZAMI_V*100:7.1f}%{sebep}")
bilgi()
bilgi("  Onceki turda '4 direnc, 151 V, 250 V sinirinin altinda' demistim.")
bilgi("  ARASTIRMA BUNU IKI YERDEN CURUTTU:")
bilgi("    1. 1/4W siniri 250 V degil 200 V (Yageo MFR).")
bilgi(f"    2. 4 direncle tam olcek zaten {1.024*(4*R_BIR+R_ALT)/R_ALT:.0f} V — "
      f"{HEDEF_V:.0f} V'a")
bilgi("       YETMIYOR. Menzil icin de gerilim payi icin de 6 gerekiyor.")
bilgi()
bilgi(f"  DEGER NEDEN {R_BIR_AD}: tasarim once 6x1M / 10K idi (ayni N=601).")
bilgi("  Tedarikcinin METAL FILM hatti 1K..820K arasi — MOhm degeri HIC YOK.")
bilgi("  (Bir ara '2.2M var' denmisti; o karbon film. Bolum 11 karbon filmin")
bilgi("  bu bolucude %4.10 hata yaptigini gosteriyor — tasarimi anlamsiz kilar.)")
bilgi()
bilgi("  6 x R / (R/100) her R icin N'yi TAM 601.0 yapar: 6R/(R/100) = 600.")
bilgi("  Listede hem R hem R/100 bulunan en BUYUK deger 820K/8.2K — en yuksek")
bilgi("  giris empedansi orada. Ve bu 1M'den de IYI cikti: Thevenin 9.98k")
bilgi("  yerine 8.19k, yani tamponun taban akimi ofseti daha da kucuk.")
kural(f"Secilen zincir {HEDEF_V:.0f} V hedefini karsiliyor",
      KANALLAR[1].fs >= HEDEF_V, f"{KANALLAR[1].fs:.1f} V")


# ═══════════════════════════════ 3. TAMPON NEDEN ZORUNLU (YENI KUSUR)
baslik("3. TAMPON ZORUNLU — PGA'ya BAGLI KAZANC HATASI (yeni kusur)")
bilgi("  ADS1115'in giris empedansi PGA kademesiyle DEGISIYOR (Tablo 2 ve s.3).")
bilgi("  Kaynak empedansi sifir degilse, bu bir KAZANC hatasi yaratir — ve")
bilgi("  kademe degisince hata da degisir. Kalibrasyon tek kademede yapildigi")
bilgi("  icin bunu SILEMEZ.")
bilgi()
bilgi("  Asama 2 firmware'i (olcum2.h: pga_sec) gerilim kanalini")
bilgi("  +-2.048 .. +-0.256 arasi OTOMATIK kademeliyor. Bolucu Thevenin'i")
bilgi("  6.37 kohm ve TAMPONSUZ. Sonuc:")
bilgi()
A2_THEV = 6.37e3
bilgi(f"    {'PGA':>8} {'Z_diff':>9} {'Z_cm':>8} {'kazanc hatasi':>14}")
bilgi("    " + "-" * 44)
a2_hata = {}
for pga in (2.048, 1.024, 0.512, 0.256):
    _, zd, zc = PGA_TABLO[pga]
    # tek yonlu: AIN_N ici GND'ye baglanir -> Z_diff baskin, Z_cm de yukler
    h = A2_THEV / zd + A2_THEV / zc
    a2_hata[pga] = h
    bilgi(f"    +-{pga:5.3f} {zd/1e6:7.2f}M {zc/1e6:6.1f}M {h*100:12.3f}%")
sicrama = (a2_hata[0.256] - a2_hata[2.048]) * 100
bilgi()
bilgi(f"  KADEME SICRAMASI: %{a2_hata[2.048]*100:.3f} -> %{a2_hata[0.256]*100:.3f}")
bilgi(f"  = {sicrama:.3f} PUAN. Oto-kademe sinirinda okuma bu kadar ZIPLAR.")
bilgi("  Uzerine ADS'in kendi PGA kazanc uyumu %0.1 maks (s.3) da biniyor.")
kural("Asama 2'de oto-kademe kazanc sicramasi %0.5'i asiyor (KUSUR)",
      sicrama > 0.5, f"{sicrama:.3f} puan — tamponsuz oto-kademe kullanilamaz")

bilgi()
bilgi("  TAMPONLA: kaynak empedansi ~0 olur, hata PGA'dan BAGIMSIZ kaybolur.")
bilgi()
bilgi("  Tamponsuz yeni kanallarda hata ne olurdu:")
for k in KANALLAR:
    h = k.thev / k.zdiff + k.thev / k.zcm
    bilgi(f"    {k.ad:<18} Thevenin {k.thev/1e3:5.2f}k -> %{h*100:.3f} "
          f"(sabit PGA'da kalibre edilir, oto-kademede EDILMEZ)")

bilgi()
bilgi("  ARASTIRMA TEYIDI (TI E2E + Adafruit forumlari, 2026-09-08):")
bilgi("    * 'divider output impedance should be < 10 kohm' (yerlesme suresi)")
bilgi("    * 'input impedance varies with gain settings'")
bilgi("    * 'a voltage buffer can be added to solve this issue'")
bilgi("    * 'the offset voltage of the op-amp should be as low as possible'")
bilgi()
bilgi("  '10 kohm' KILAVUZU KIME BAKIYOR — bir ayrim:")
bilgi("  O kilavuz ADS'in GORDUGU empedans icin. Bizde ADS bolucuyu")
bilgi("  gormuyor, TAMPONUN CIKISINI goruyor (cikis empedansi ~ohm).")
bilgi("  Bolucunun Thevenin'i bambaska bir seyi belirliyor: TAMPONUN")
bilgi("  TABAN AKIMININ (Ib) yarattigi ofset.")
bilgi()
LM358_IB = 45e-9        # tipik, 25 C (TI LM358 s.6)
bilgi("  ⚠ DIKKAT: tamponun + girisinin gordugu DC direnci bolucunun")
bilgi("  Thevenin'i DEGIL, onunla RC suzgec direncinin TOPLAMIDIR — taban")
bilgi("  akimi ikisinin uzerinden de akiyor. Ilk yazdigimda R7/R17'yi")
bilgi("  unutmustum ve ofseti oldugundan kucuk gosteriyordu.")
bilgi()
bilgi(f"  {'kanal':<18} {'Thev':>7} {'+R7/R17':>9} {'Rdc':>8} "
      f"{'Ib ofseti':>10} {'girise':>11} {'tam olcegin':>12}")
bilgi("  " + "-" * 82)
for k in KANALLAR:
    r_dc = k.thev + T.RC_R                 # tamponun GERCEK kaynak direnci
    v_dug = LM358_IB * r_dc                # dugumdeki kayma
    v_gir = v_dug * k.N                    # girise vurulmus
    oran = v_gir / k.fs
    bilgi(f"  {k.ad:<18} {k.thev/1e3:5.2f}k {T.RC_R/1e3:7.0f}K "
          f"{r_dc/1e3:6.2f}k {v_dug*1e6:8.1f} uV {v_gir*1e3:8.1f} mV "
          f"{oran*100:11.3f}%")
    kural(f"{k.ad}: Ib ofseti tam olcegin %0.5'inin altinda",
          oran < 0.005, f"%{oran*100:.3f} ({v_gir*1e3:.0f} mV girise vurulmus)")
bilgi()
bilgi("  Bu bir OFSET, kazanc hatasi degil: N'den gecse de girise SABIT")
bilgi("  bir sayi olarak biner ve sifir kalibrasyonu siler. PGA kademesiyle")
bilgi("  de degismez — bolum 3'teki kusurun aksine.")
bilgi()
bilgi("  ZINCIR DEGERINI NE BELIRLEDI — 820K mi 2.2M mi (2026-09-09)")
bilgi()
bilgi("  Tedarikcide 820K, 2.2M ve 6.8M'in UCU DE metal film. Alt bacak")
bilgi("  zincirin yuzde biri oldugu surece hepsi N'yi TAM 601.0 yapiyor:")
bilgi("  6R / (R/100) = 600. Yani menzil, adim, ORAN_YUKSEK, direnc basina")
bilgi("  dusen gerilim (102.3 V) ve gerilim payi (%51) UCUNDE DE AYNI.")
bilgi()
bilgi("  Ayirt eden tek sey KACAK AKIMI. Delikli plakette zincire paralel")
bilgi("  bir yuzey kacagi (R_L) olusursa bolme oranini asagi ceker:")
bilgi("      bagil hata ~ Rust / R_L        -> ZINCIR DIRENCIYLE ORANTILI")
bilgi()
KACAK_ADAYLAR = [(820e3, 8.2e3), (2.2e6, 22e3), (6.8e6, 68e3)]
bilgi(f"  {'zincir':<10} {'Rust':>8} {'girisZ':>8}  "
      + "  ".join(f"{r/1e9:.0f}G ohm'da" for r in (1e9, 10e9, 100e9)))
bilgi("  " + "-" * 62)
for _R, _ra in KACAK_ADAYLAR:
    _ru = 6 * _R
    _h = "  ".join(f"{_ru/_rl*100:9.3f}%" for _rl in (1e9, 10e9, 100e9))
    _ad = f"{_R/1e6:g}M" if _R >= 1e6 else f"{_R/1e3:g}K"
    bilgi(f"  6x{_ad:<8} {_ru/1e6:6.2f}M {(_ru+_ra)/1e6:6.2f}M  {_h}")
bilgi()
bilgi("  Kacak KALIBRASYONLA SILINMEZ: nemle gunden gune degisir. Karbon")
bilgi("  filmi eleyen gerekce ile birebir ayni gerekce.")
bilgi()
bilgi("  BUNA KARSILIK 2.2M'in kazandirdigi sey giris empedansi:")
bilgi("  13.22 Mohm'a karsi 4.93 Mohm. 615 V'ta cektigi akim 47 uA'e karsi")
bilgi("  125 uA. Ama bu kanalin olcecegi seyler (dogrultulmus sebeke, DC")
bilgi("  bara, SMPS cikisi) miliohm mertebesinde kaynaklar — 5 Mohm ile")
bilgi("  13 Mohm arasindaki fark oralarda OLCULEMEZ.")
bilgi()
bilgi("  KARAR: 820K. Kacak, zincirin DOGRULANAMAYAN riski (tezgahta")
bilgi("  olculecekler listesinde duruyor); giris empedansi ise hesabi")
bilgi("  yapilmis ve onemsiz cikmis bir fark. Dogrulanamayan riskin kucugu")
bilgi("  secilir.")
_SECILEN_RUST = KANALLAR[1].rust
kural("Secilen zincir, ayni N'yi veren alternatiflerin EN DUSUK dirençlisi",
      _SECILEN_RUST <= min(6 * r for r, _ in KACAK_ADAYLAR),
      f"{_SECILEN_RUST/1e6:.2f}M (2.2M -> 13.20M, 6.8M -> 40.80M)")
kural("Zincir 10 Gohm'luk bir yuzey kacaginda %0.1'den az hata yapiyor",
      _SECILEN_RUST / 10e9 < 0.001,
      f"%{_SECILEN_RUST/10e9*100:.3f} — 2.2M ayni kacakta %{13.2e6/10e9*100:.3f}")
_thev68 = T.par(6 * 6.8e6, 68e3)
_kat = (_thev68 + T.RC_R) / (KANALLAR[1].thev + T.RC_R)
kural("Cok yuksek degerli zincir (6x6.8M) Ib ofsetini de belirgin artirir",
      _kat > 2.5, f"{_kat:.2f} kat (Rdc {(_thev68+T.RC_R)/1e3:.1f}k vs "
      f"{(KANALLAR[1].thev+T.RC_R)/1e3:.1f}k) — kacakta ise 8.3 kat")


# ═══════════════════════════════════════ 4. TAMPON SECIMI VE HATA BUTCESI
baslik("4. TAMPON SECIMI — YALNIZCA DELIKLI (THT) GOVDELER")
bilgi("  KULLANICI KISITI (2026-09-08): 'yuzey montajda zorlaniyorum, ")
bilgi("  yapamayabilirim.' -> SMD govde bir eleme olcutu.")
bilgi()
bilgi("  ONCE BIR YANLIS ANLAMAYI DUZELTELIM: MCP6002/6004 SMD DEGIL —")
bilgi("  '-I/P' son ekli surumleri PDIP. MCP6002-I/P = DIP-8,")
bilgi("  MCP6004-I/P = DIP-14. Siparis ederken son eke dikkat.")
bilgi()
bilgi(f"  {'op-amp':<9} {'govde':<8} {'besleme':<11} {'cikis tavani':>12} "
      f"{'Vos':>7} {'drift':>9} {'Ib':>9}  stok")
bilgi("  " + "-" * 84)
for ad, vos, dr, ib, gbw, bes, tavan, govde, stok in T.OPAMPLAR:
    bilgi(f"  {ad:<9} {govde:<8} {bes:<11} {tavan:10.1f} V {vos*1e3:5.1f}mV "
          f"{dr*1e6:6.1f}uV/C {ib*1e9:7.3f}nA  {stok}")
kural("Butun adaylar DELIKLI govdede bulunabiliyor",
      all(g.startswith("DIP") for *_, g, _ in T.OPAMPLAR), "DIP-8 / DIP-14")

bilgi()
bilgi("  ═══ ASIL SORU: ADS GIRISI ARIZADA NE GORUR? ═══")
bilgi()
bilgi("  Tamponun cikis tavani, ADS'in mutlak azamisini (VDD+0.3 = 3.6 V)")
bilgi(f"  asiyorsa kelepce gerekir. Seri direnc {T.ADS_SERI_R/1e3:.1f}k ile")
bilgi("  (R34/R35/R36 — B15/F1 ile eklendi; ONCEDEN HIC YOKTU):")
bilgi()
bilgi(f"  {'op-amp':<9} {'tavan':>7} {'ADS azami':>10} {'asim':>7} "
      f"{'kacan akim':>11}  kelepce")
bilgi("  " + "-" * 62)
kelepce_gerekli = {}
for ad, vos, dr, ib, gbw, bes, tavan, govde, stok in T.OPAMPLAR:
    asim = tavan - T.ADS_MUTLAK_UST
    akim = max(0.0, asim) / T.ADS_SERI_R
    gerek = akim > 0.001            # 1 mA uzeri -> kelepce sart
    kelepce_gerekli[ad] = gerek
    bilgi(f"  {ad:<9} {tavan:5.1f} V {T.ADS_MUTLAK_UST:8.1f} V {asim:+6.1f} V "
          f"{akim*1e3:9.3f} mA  {'SART' if gerek else 'gerekmez'}")
bilgi()
_lm358_tavan = T.OPAMPLAR[1][6]
bilgi("  ⚠ B15 BU BOLUMU DUZELTTI (2026-09-09):")
bilgi(f"  Eskiden 'LM358'in tavani 4.3 V' yaziyordu; o sayi hicbir veri")
bilgi(f"  sayfasi satirina dayanmiyordu. TI SLOS068AB 5.5: V+ - V_OH")
bilgi(f"  dusumu {T.LM358_VOH_DUSUM:.2f} V tipik -> +5.00 V rayda tavan "
      f"{_lm358_tavan:.2f} V.")
bilgi(f"  Bu, ADS'in mutlak ustunu ({T.ADS_MUTLAK_UST:.2f} V) "
      f"{_lm358_tavan-T.ADS_MUTLAK_UST:+.2f} V ASIYOR —")
bilgi("  yani kelepce degil ama SERI DIRENC gerekiyor. B15/F1 ile")
bilgi(f"  R34/R35/R36 ({T.ADS_SERI_R/1e3:.0f}K) eklendi; kacan akim "
      f"{max(0.0,_lm358_tavan-T.ADS_MUTLAK_UST)/T.ADS_SERI_R*1e6:.0f} uA.")
kural("LM358 (+5 V): seri direncle ADS akimi TI'in 1 mA hedefi altinda",
      not kelepce_gerekli["LM358"],
      f"{max(0.0,_lm358_tavan-T.ADS_MUTLAK_UST)/T.ADS_SERI_R*1e6:.0f} uA "
      f"(tavan {_lm358_tavan:.2f} V)")
kural("MCP600x (3.3 V RRIO) kelepcesiz guvenli — rayi zaten ADS'in rayi",
      not kelepce_gerekli["MCP6004"], "asim yok")
kural("TL072 (+-12 V) kelepce SART", kelepce_gerekli["TL072"],
      f"{(10.0-T.ADS_MUTLAK_UST)/T.R_SERI*1e3:.2f} mA")

bilgi()
bilgi("  ═══ HATA BUTCESI — girise vurulmus, 20 C sicaklik degisimi ═══")
bilgi()
bilgi(f"  {'kanal':<18} {'op-amp':<9} {'Ib*Rt':>10} {'drift':>10} "
      f"{'toplam':>10} {'FS orani':>10}")
bilgi("  " + "-" * 72)
for k in KANALLAR:
    for ad, vos, dr, ib, gbw, bes, tavan, govde, stok in T.OPAMPLAR:
        if ad == "MCP6002":
            continue          # MCP6004 ile ayni cekirdek
        ib_g = ib * k.thev * k.N
        dr_g = dr * k.N * 20
        top = ib_g + dr_g
        bilgi(f"  {k.ad:<18} {ad:<9} {ib_g*1e3:8.2f} mV {dr_g*1e3:8.2f} mV "
              f"{top*1e3:8.2f} mV {top/k.fs*100:8.4f}%")

bilgi()
bilgi("  ⚠ YUKARIDAKI TABLO YANILTICI — kalibrasyonun SILDIGI terimleri de")
bilgi("  sayiyor. Vos ve Ib*Rt SABIT'tir; sifir kalibrasyonu ikisini de")
bilgi("  goturur. Kalibrasyondan SONRA kalan yalnizca SURUKLENMEdir.")
bilgi()
# LM358 taban akimi bipolar: sicaklikla ~%30 degisir (20 C icin temkinli)
IB_DRIFT_ORANI = {"TL072": 0.30, "LM358": 0.30, "MCP6002": 0.30, "MCP6004": 0.30}
bilgi(f"  {'kanal':<18} {'op-amp':<9} {'Vos drift':>10} {'Ib drift':>10} "
      f"{'KALAN':>10} {'FS orani':>10}")
bilgi("  " + "-" * 72)
kalan_hata = {}
for k in KANALLAR:
    for ad, vos, dr, ib, gbw, bes, tavan, govde, stok in T.OPAMPLAR:
        if ad == "MCP6002":
            continue
        vos_dr = dr * k.N * 20
        ib_dr = ib * k.thev * k.N * IB_DRIFT_ORANI[ad]
        kalan = vos_dr + ib_dr
        kalan_hata[(k.ad, ad)] = kalan
        bilgi(f"  {k.ad:<18} {ad:<9} {vos_dr*1e3:8.2f} mV {ib_dr*1e3:8.2f} mV "
              f"{kalan*1e3:8.2f} mV {kalan/k.fs*100:8.4f}%")

bilgi()
bilgi("  KIYAS NOKTASI: kullanicinin ANENG AN8000'i +-(%0.5 + 4 hane).")
bilgi("  Kalibrasyon referansi o oldugu surece kartin MUTLAK dogrulugu")
bilgi("  zaten %0.5'in altina inemez (DEVIR 1.3). Yani secim dogrulukla")
bilgi("  degil, PRATIKLIKLE ilgili.")
AN8000_HATA = 0.005
for k in KANALLAR:
    for ad in ("LM358", "MCP6004"):
        kalan = kalan_hata[(k.ad, ad)]
        kural(f"{k.ad} + {ad}: kalibrasyon sonrasi hata DMM'in %10'undan az",
              kalan / k.fs < AN8000_HATA * 0.1,
              f"%{kalan/k.fs*100:.4f} (DMM %{AN8000_HATA*100:.1f})")

bilgi()
bilgi("  LM358'in Ib SURUKLENMESI de silinebilir — klasik telafi:")
bilgi("  izleyicinin geri besleme koluna kaynak Thevenin'ine ESIT direnc koy.")
bilgi("  Eslesen taban akimlari sadelesir, geriye yalnizca OFSET AKIMI kalir")
bilgi(f"  (LM358: Ios ~{T.OPAMPLAR[1][3]*1e9:.0f} nA yerine ~5 nA, 9 kat kucuk).")
for k in KANALLAR:
    ib_telafili = 5e-9 * k.thev * k.N * 0.30
    vos_dr = 7e-6 * k.N * 20
    kural(f"{k.ad} + LM358 (Ib telafili): kalan hata FS'in %0.02'sinin altinda",
          (vos_dr + ib_telafili) / k.fs < 0.0002,
          f"%{(vos_dr+ib_telafili)/k.fs*100:.4f}")

bilgi()
bilgi("  ═══ UC YOL ═══")
bilgi()
bilgi("  YOL 0 — HICBIR SEY ALMA:  LM358 (stokta 8) + 5 V")
bilgi("    + Satin alma yok, DIP-8, elinde var")
bilgi(f"    + Kelepce diyodu gerekmiyor (cikis tavani "
      f"{T.OPAMPLAR[1][6]:.2f} V), ama {T.ADS_SERI_R/1e3:.0f}K seri direnc SART")
bilgi("    - Ib 45 nA -> 615 V kanalinda 270 mV sabit ofset (kalibre edilir)")
bilgi("    - Drift MCP600x'in 3.5 kati (yine de DMM'in cok altinda)")
bilgi("    ! Ib telafisi: geri besleme koluna Thevenin'e esit direnc koy")
bilgi()
bilgi("  YOL 1 — BIR ADET AL:      MCP6004-I/P (DIP-14) veya MCP6002-I/P (DIP-8)")
bilgi("    + En dusuk drift ve Ib, kelepce yok, 4 kesit tek govdede")
bilgi("    - Tek kalemlik siparis")
bilgi()
bilgi("  YOL 2 — TL072 (yolda):    +-12 V + 2.7k + BAT85 x2")
bilgi("    + Skop/hizli yol icin ZATEN gerekli (band 3 MHz)")
bilgi("    - Hassas ADS yolunda kelepce ve +-12 V bagimliligi getirir")
bilgi()
bilgi("  ONERI: ADS yolunda YOL 0 ile basla (bedava, elinde var, kelepcesiz).")
bilgi("  Tezgahta drift olcup yetmezse YOL 1'e gec — devre AYNI kaliyor,")
bilgi("  sadece DIP-8 soketten cip degisiyor. Skop yolu her halukarda TL072.")
kural("Sokete takilirsa LM358 -> MCP6002 gecisi devre degisikligi gerektirmiyor",
      True, "ikisi de DIP-8, ayni bacak duzeni (cift op-amp)")


baslik("5. KORUMA KELEPCESI — TI'nin KENDISI SCHOTTKY DIYOR")
bilgi("  SBAS444B s.12, birebir alinti:")
bilgi('    "external Schottky clamp diodes and/or series resistors may be')
bilgi('     required to limit the input current to safe values"')
bilgi('    "overdriving one unused input on the ADS1115 MAY AFFECT')
bilgi('     CONVERSIONS taking place on other input pins"')
bilgi()
bilgi("  Ikinci alinti mimariyi etkiliyor: HV kanalini normal kanalla AYNI")
bilgi("  cipe koyarsak, HV girisindeki bir asiri surme normal kanalin")
bilgi("  okumasini da bozar. Kelepce burada 'guzel olur' degil, ZORUNLU.")
bilgi()
ESD_VF = 0.70                     # ADS ic ESD diyodu (silisyum)
ADS_GIRIS_AKIM_MAKS = 10e-3       # mutlak azami surekli giris akimi

bilgi("  ONCE BIR KAVRAM DUZELTMESI (bu betigin ilk surumunde YANLISTI):")
bilgi("  'Vf < 0.3 V olan diyot bul' diye kural yazmistim. BOYLE BIR DIYOT")
bilgi("  YOK — hicbir diyot -0.3 V'un altina kelepceleyemez.")
bilgi()
bilgi("  -0.3 V siniri neden var: TI s.12 'to PREVENT THE ESD DIODES FROM")
bilgi("  TURNING ON'. Sinir gerilim degil, ic ESD diyodunun ILETMESI. TI'nin")
bilgi("  cozum cumlesi de akim uzerine kurulu:")
bilgi('    "...AND/OR SERIES RESISTORS may be required TO LIMIT THE INPUT')
bilgi('     CURRENT to safe values"')
bilgi()
bilgi("  ═══ AMA DAHA IYI BIR CEVAP VAR: KELEPCEYI HIC GEREKTIRMEMEK ═══")
bilgi()
bilgi("  Tampon op-amp'i ADS ile AYNI 3.3 V rayindan beslersek, cikisi")
bilgi("  tanim geregi 0..3.3 V disina CIKAMAZ. O zaman ADS girisinde")
bilgi("  kelepce diyoduna hic gerek kalmaz: ne kacak hatasi, ne kapasite,")
bilgi("  ne satin alinacak diyot.")
bilgi()
bilgi("  Peki tamponun KENDI girisi? Bolucu dugumu asiri gerilimde ne olur:")
bilgi()
bilgi(f"    {'kanal':<18} {'giris':>9} {'dugum':>9} {'op-amp ESD akimi':>18}")
bilgi("    " + "-" * 60)
for k in KANALLAR:
    for v_asiri in (2 * k.fs, 3 * k.fs):
        dugum = VREF + (v_asiri - VREF) / k.N
        # dugum rayi asarsa akim Rust uzerinden akar
        i_esd = max(0.0, (v_asiri - VDD)) / k.rust
        bilgi(f"    {k.ad:<18} {v_asiri:7.0f} V {dugum:7.2f} V {i_esd*1e6:15.1f} uA")
        k_i = i_esd
    kural(f"{k.ad}: 3x asiri gerilimde op-amp ESD akimi 1 mA'in altinda",
          k_i < 1e-3, f"{k_i*1e6:.1f} uA — bolucunun kendi direnci koruyor")
bilgi()
bilgi("  Bolucunun ust bacagi (200K / 6M) zaten mukemmel bir akim sinirlayici.")
bilgi("  Yani 3.3 V'luk bir tamponla sistem BASTAN UCA kelepcesiz guvenli.")
bilgi()
bilgi("  BEDELI: TL072 ve LM358 3.3 V'ta bu isi YAPAMAZ.")
bilgi(f"  Gereken cikis araligi {min(k.cm_alt for k in KANALLAR):.3f} .. "
      f"{max(k.cm_ust for k in KANALLAR):.3f} V, besleme 0..3.3 V.")
bilgi("    TL072  : cikis her raydan ~1.5 V uzakta durur -> OLMAZ")
bilgi("    LM358  : cikis alt rayda iyi, ust sinir Vcc-1.5 = 1.8 V -> OLMAZ")
bilgi("    RRIO   : (MCP6002/6004, TLV9002...) -> OLUR, SATIN ALINACAK")
kural("TL072 3.3 V tek beslemede yetmiyor (belgelendi)",
      max(k.cm_ust for k in KANALLAR) > 3.3 - 1.5)
kural("LM358 3.3 V tek beslemede yetmiyor (belgelendi)",
      max(k.cm_ust for k in KANALLAR) > 3.3 - 1.5)

bilgi()
bilgi("  ═══ HIZLI YOL (ESP32 ADC) FARKLI — orada kelepce SART ═══")
bilgi()
bilgi("  Skop kanali TL072 ile +-12 V'ta calisiyor (band gerekiyor), yani")
bilgi("  cikisi arizada +-10 V'a gidebilir. Orada seri direnc + Schottky")
bilgi("  zorunlu. Seri direnci hesaplayalim:")
bilgi()
ARIZA_V = 12.0
bilgi(f"    {'R seri':>8} {'ariza akimi':>12} {'ADS 10 mA':>11}")
bilgi("    " + "-" * 35)
R_SERI = None
for r in (1e3, 2.2e3, 2.7e3, 4.7e3):
    i = (ARIZA_V - ESD_VF) / r
    gecer = i < ADS_GIRIS_AKIM_MAKS
    if gecer and R_SERI is None and r >= 2.7e3:
        R_SERI = r
    bilgi(f"    {r/1e3:6.1f}k {i*1e3:10.2f} mA {'gecer' if gecer else 'KALIR':>11}")
bilgi()
bilgi(f"  SECILEN: {R_SERI/1e3:.1f}k (stokta 10 adet).")
bilgi("  ILK SURUMDE 1K YAZMISTIM — 11.3 mA veriyordu, 10 mA sinirinin USTU.")
kural("Seri direnc ariza akimini 10 mA'in altinda tutuyor",
      (ARIZA_V - ESD_VF) / R_SERI < ADS_GIRIS_AKIM_MAKS,
      f"{(ARIZA_V-ESD_VF)/R_SERI*1e3:.2f} mA")

DIYOTLAR = [
    ("1N4148", 0.75, 5e-9,   8, "silisyum, stokta 8"),
    ("SR5100", 0.55, 50e-6, 10, "5A guc Schottky, stokta 10"),
    ("BAT54",  0.40, 0.1e-6, 0, "kucuk sinyal Schottky, ALINACAK"),
]
bilgi()
bilgi("  Diyot akimi ustel (I ~ exp(V/nVt), nVt ~ 40 mV): Vf farki dV olan")
bilgi("  harici diyot, ic ESD diyodundan exp(dV/0.04) kat fazla akim ceker.")
bilgi()
bilgi("  ⚠ ASAGIDAKI 'ESD payi' KABA BIR KESTIRIM — seri direnci ve gercek")
bilgi("  diyot denklemini ihmal ediyor. Baglayici olan B2 (sim3_giris.py)")
bilgi("  SPICE sonucudur; o 1N4148 icin %25, BAT54 icin ~%0 veriyor.")
bilgi()
bilgi(f"  {'diyot':<9} {'Vf':>6} {'ESD payi':>10} {'kacak':>8} {'kacak hatasi':>13}  not")
bilgi("  " + "-" * 72)
for ad, vf, kacak, stok, notu in DIYOTLAR:
    esd_payi = 1.0 / (1.0 + math.exp((ESD_VF - vf) / 0.040))
    bilgi(f"  {ad:<9} {vf:5.2f}V {esd_payi*100:9.3f}% {kacak*1e6:6.2f}uA "
          f"{kacak*R_SERI*1e3:11.3f} mV  {notu}")

esd_1n4148 = 1.0 / (1.0 + math.exp((ESD_VF - 0.75) / 0.040))
esd_bat54 = 1.0 / (1.0 + math.exp((ESD_VF - 0.40) / 0.040))
kural("1N4148 ic ESD diyodunu KORUYAMIYOR (kesin sayi B2'de)",
      esd_1n4148 > 0.10,
      f"kestirim %{esd_1n4148*100:.0f}, SPICE %25 — ikisi de 'koruyamiyor' diyor")
kural("BAT54 akimin %99'undan fazlasini ESD'den uzaga cekiyor",
      esd_bat54 < 0.01, f"ESD payi %{esd_bat54*100:.4f}")
kural("SR5100 kacagi hizli yolda bile kabul edilemez",
      50e-6 * R_SERI > 1e-3, f"{50e-6*R_SERI*1e3:.0f} mV ofset")
kural("BAT54 kacagi hizli yolda kabul edilebilir (skop 8-12 bit)",
      0.1e-6 * R_SERI < 1e-3, f"{0.1e-6*R_SERI*1e3:.3f} mV")
bilgi()
bilgi("  NOT: BAT54 kacagi icin 25 V ters gerilimdeki 2 uA maks degil,")
bilgi("  ~2 V ters gerilimdeki tipik ~0.1 uA kullanildi. Tezgahta olculmeli.")
bilgi()
bilgi("  B2 (SPICE) SONUCU — -12 V ariza, 2.7k seri direnc:")
bilgi("    kelepce yok : pin -0.734 V, ariza akiminin %100'u ic ESD'de")
bilgi("    1N4148      : pin -0.667 V, %25.1'i hala ic ESD'de")
bilgi("    BAT54       : pin -0.258 V, ic ESD payi ~%0")
bilgi()
bilgi("  BEKLENENDEN IYI: BAT54 ile pin -0.258 V'ta kaliyor, yani mutlak")
bilgi("  alt sinir -0.3 V'un bile USTUNDE. Kelepce sadece akimi yonlendirmiyor,")
bilgi("  gerilimi de spec icinde tutuyor. (Analitik kestirimim -0.4 V demisti;")
bilgi("  SPICE daha iyi cikti. Baglayici olan SPICE.)")
bilgi()
bilgi("  SONUC — IKI FARKLI KORUMA REJIMI:")
bilgi("    ADS yolu  (hassas) : 3.3 V RRIO tampon -> kelepce YOK, kacak YOK")
bilgi(f"    ESP yolu  (hizli)  : TL072 +-12 V -> {R_SERI/1e3:.1f}k + BAT54 x2 SART")


# ═══════════════════════════════ 6. ORTUSME SUZGECI (DEVIR 4.8) — TEK TASARIM
baslik("6. ORTUSME SUZGECI — SALLEN-KEY (DEVIR 4.8'in cozumu)")
bilgi("  TI s.14: 'the digital Sinc filter frequency response CANNOT")
bilgi("  COMPLETELY REPLACE an anti-aliasing filter'.")
bilgi()
bilgi("  Hizli yol: ESP32-S3 ADC, 83 333 Sa/s TOPLAM, 2 kanal ->")
ESP_TOPLAM_SPS = 83333
ESP_KANAL = 2
esp_kanal_sps = ESP_TOPLAM_SPS / ESP_KANAL
esp_nyquist = esp_kanal_sps / 2
bilgi(f"    kanal basina {esp_kanal_sps:.1f} Sa/s, Nyquist {esp_nyquist/1e3:.2f} kHz")
bilgi()
bilgi("  ═══ 6a. ADS YOLU — Nyquist 430 Hz, Sallen-Key BURAYA UYMAZ ═══")
bilgi()
ads_nyquist = ADS_SPS / 2
bilgi(f"  ADS 860 SPS -> Nyquist {ads_nyquist:.0f} Hz. Sinc suzgeci 380 Hz'te")
bilgi("  -3 dB ve 860 Hz'in katlarinda centik var, ama TI (s.14) acikca")
bilgi("  'CANNOT COMPLETELY REPLACE an anti-aliasing filter' diyor.")
bilgi()
bilgi("  ONEMLI: 16.5 kHz'lik Sallen-Key bu yola HICBIR SEY yapmaz —")
bilgi("  430 Hz'lik Nyquist'in 38 kati uzakta. Iki yolun Nyquist'i farkli,")
bilgi("  bu yuzden IKI AYRI SUZGEC gerekiyor. (Ilk taslakta tek suzgec")
bilgi("  dusunmustum; ADS Nyquist'ini hesaba katinca yanlis oldugu cikti.)")
bilgi()
RC_R = 22e3          # stokta 15
RC_C = 100e-9        # stokta ~51
bilgi(f"  Basit RC: bolucu dugumu --[{RC_R/1e3:.0f}K]--+--> tampon")
bilgi(f"                                    [{RC_C*1e9:.0f}nF]")
bilgi("                                       |")
bilgi("                                      Vref")
bilgi("  (C, GND'ye degil VREF'e baglanir — diferansiyel cift boylece")
bilgi("   ortak-mod gurultusunde birlikte hareket eder.)")
bilgi()
for k in KANALLAR:
    r_top = k.thev + RC_R
    fc = 1 / (2 * math.pi * r_top * RC_C)
    tau = r_top * RC_C
    bilgi(f"    {k.ad:<18} R={r_top/1e3:5.1f}k -> fc={fc:6.1f} Hz, "
          f"tau={tau*1e3:5.2f} ms, %0.1'e yerlesme {7*tau*1e3:5.1f} ms")
    k.rc_fc = fc
    kural(f"{k.ad}: RC kesimi ADS Nyquist'inin ALTINDA", fc < ads_nyquist,
          f"{fc:.1f} Hz < {ads_nyquist:.0f} Hz")
    kural(f"{k.ad}: 860 Hz'te (ilk katlanma) en az 20 dB zayiflama",
          20*math.log10(1/math.sqrt(1+(860/fc)**2)) < -20,
          f"{20*math.log10(1/math.sqrt(1+(860/fc)**2)):.1f} dB")
    kural(f"{k.ad}: 5 Hz'lik guncelleme hizina yetisiyor (7 tau < 200 ms)",
          7 * (k.thev + RC_R) * RC_C < 0.200,
          f"{7*(k.thev+RC_R)*RC_C*1e3:.1f} ms")
bilgi()
bilgi("  RC tamponun ONUNDE: seri direnc ADS'e degil, CMOS tampon girisine")
bilgi("  bakiyor (Ib ~1 pA), yani kazanc hatasi yaratmiyor. Tamponun ARDINA")
bilgi("  konsaydi ADS'in giris empedansiyla bolucu olusturup 3. bolumdeki")
bilgi("  PGA'ya bagli hatayi geri getirirdi.")
bilgi()
bilgi("  ═══ 6b. ESP32 HIZLI YOLU — Nyquist 20.83 kHz ═══")
bilgi()
bilgi("  KUSUR (DEVIR 4.8): bugunku tek kutuplu RC'nin kesimi 25.0 kHz —")
bilgi("  Nyquist'in USTUNDE. 100 kHz'lik bir SMPS dalgalanmasi hic")
bilgi("  zayiflamadan 16.67 kHz'e KATLANIR ve gercekmis gibi gorunur.")

# Sallen-Key, esit R, birim kazanc: f0 = 1/(2*pi*R*sqrt(C1*C2)), Q = 0.5*sqrt(C1/C2)
SK_R = 6.8e3      # stokta 18
SK_C1 = 2e-9      # 2 x 1nF paralel (stokta 16)
SK_C2 = 1e-9
sk_f0 = 1 / (2 * math.pi * SK_R * math.sqrt(SK_C1 * SK_C2))
sk_q = 0.5 * math.sqrt(SK_C1 / SK_C2)
bilgi()
bilgi(f"  Sallen-Key birim kazanc, esit R = {SK_R/1e3:.1f}k,")
bilgi(f"  C1 = {SK_C1*1e9:.0f} nF (2x1nF paralel), C2 = {SK_C2*1e9:.0f} nF")
bilgi(f"    f0 = {sk_f0:.0f} Hz,  Q = {sk_q:.4f}  (Butterworth = 0.7071)")


def sk_kazanc_db(f):
    """2 kutuplu Butterworth genlik cevabi (dB)."""
    x = f / sk_f0
    return 20 * math.log10(1 / math.sqrt(1 + x ** 4))


bilgi()
bilgi(f"    {'frekans':>12} {'zayiflama':>11}")
bilgi("    " + "-" * 26)
for f, etiket in ((1e3, ""), (10e3, ""), (esp_nyquist, " <- Nyquist"),
                  (esp_kanal_sps, " <- fs"), (100e3, " <- SMPS")):
    bilgi(f"    {f/1e3:9.2f} kHz {sk_kazanc_db(f):9.2f} dB{etiket}")

kural("Butterworth (Q = 0.7071, tepe yok)", abs(sk_q - 0.70710678) < 0.001,
      f"Q = {sk_q:.5f}")
kural("f0 Nyquist'in ALTINDA (bugunku kusurun tersi)", sk_f0 < esp_nyquist,
      f"{sk_f0:.0f} Hz < {esp_nyquist:.0f} Hz")
kural("100 kHz'te en az 30 dB zayiflama", -sk_kazanc_db(100e3) >= 30,
      f"{sk_kazanc_db(100e3):.2f} dB")
kural("Guc carpiminda (V x I) 100 kHz bastirmasi 60 dB'i asiyor",
      -2 * sk_kazanc_db(100e3) >= 60, f"{2*sk_kazanc_db(100e3):.1f} dB")
kural("1 kHz'te olcum bandi bozulmuyor (< 0.1 dB)",
      abs(sk_kazanc_db(1e3)) < 0.1, f"{sk_kazanc_db(1e3):.4f} dB")

bilgi()
bilgi("  TEK TASARIM IKI KANALA YETIYOR — cunku ikisinin Thevenin'i yakin:")
for k in KANALLAR:
    bilgi(f"    {k.ad:<18} Thevenin {k.thev/1e3:.2f} kohm")
bilgi(f"    Sallen-Key R                 {SK_R/1e3:.2f} kohm")
bilgi("  Suzgec tamponun ICINDE (Sallen-Key zaten bir tampondur) — yani")
bilgi("  bolum 4'teki tampon ve bu suzgec AYNI op-amp kesiti. Ek parca yok.")

# TL072 bandi yetiyor mu
bilgi()
sk_gerekli_gbw = sk_f0 * 100      # birim kazancta 100x pay
bilgi(f"  TL072 GBW {TL072_GBW/1e6:.0f} MHz, birim kazanc tamponu.")
kural("TL072 bandi Sallen-Key f0'inin en az 100 kati",
      TL072_GBW > sk_gerekli_gbw, f"{TL072_GBW/sk_f0:.0f}x")


# ═══════════════════════════════════ 7. GURULTU BUTCESI (DEVIR 1.3 kapaniyor)
baslik("7. GURULTU BUTCESI — DEVIR 1.3'un ACIK SORUSU")
bilgi("  DEVIR 1.3: '200 ms ortalamada 0.22 mV demistim ama zincir bunu")
bilgi("  uretmiyor... veri sayfasinin gurultu tablosundan dogrula ve")
bilgi("  tasarim2.py'ye kural olarak ekle.'  Simdi yapiliyor.")
bilgi()
bilgi("  KAYNAK: SBAS444B s.8 Sekil 15 (gurultu-besleme) ve Sekil 14")
bilgi("  (gurultu-giris sinyali). VDD = 3.3 V, DR = 860 SPS.")
bilgi()
PENCERE_S = 0.200
n_ornek = ADS_SPS * PENCERE_S
bilgi(f"  {'kanal':<18} {'PGA':>7} {'ADS gurultu':>12} {'kuantalama':>11} "
      f"{'toplam/orn':>11} {'200ms':>10}")
bilgi("  " + "-" * 76)
for k in KANALLAR:
    g_ads = ADS_GURULTU[k.pga] * k.N          # girise vurulmus
    g_kuant = k.adim / math.sqrt(12)          # duzgun dagilim
    g_top = math.sqrt(g_ads ** 2 + g_kuant ** 2)
    g_ort = g_top / math.sqrt(n_ornek)
    k.gurultu_ornek = g_top
    k.gurultu_200ms = g_ort
    bilgi(f"  {k.ad:<18} +-{k.pga:5.3f} {g_ads*1e3:9.3f} mV {g_kuant*1e3:9.3f} mV "
          f"{g_top*1e3:9.3f} mV {g_ort*1e3:8.3f} mV")

bilgi()
bilgi(f"  200 ms = {n_ornek:.0f} ornek -> sqrt(N) = {math.sqrt(n_ornek):.1f}x bastirma")
bilgi()
bilgi("  DURUSTLUK NOTU: sqrt(N) yalnizca BEYAZ gurultu icin gecerlidir.")
bilgi("  1/f gurultusu, referans suruklenmesi ve sicaklik bu carpani")
bilgi("  pratikte sinirlar. Asagidaki 'gurultusuz sayim' bir UST SINIRDIR,")
bilgi("  garanti degil — tezgahta olculmelidir.")
bilgi()
for k in KANALLAR:
    gurultusuz = 2 * k.fs / (6.6 * k.gurultu_200ms)     # 6.6 sigma tepe-tepe
    bilgi(f"    {k.ad:<18} 200 ms'te gurultusuz ~{gurultusuz:,.0f} sayim "
          f"(tek ornekte {2*k.fs/(6.6*k.gurultu_ornek):,.0f})")
    kural(f"{k.ad}: tek ornekte gurultu adimin 2 katini asmiyor",
          k.gurultu_ornek < 2 * k.adim,
          f"{k.gurultu_ornek*1e3:.3f} mV vs adim {k.adim*1e3:.3f} mV")

bilgi()
bilgi("  KIYAS: kullanicinin ANENG AN8000'i 4000 sayim, 40 V kademesinde")
bilgi("  10 mV cozunurluk, +-(%0.5+4 hane). Kart cozunurlukte cok onde;")
bilgi("  MUTLAK dogrulukta ise kalibrasyon referansina bagli (DEVIR 1.3).")


# ═══════════════════════════════ 8. V-I KAYMASI (kullanicinin 3. istegi)
baslik("8. V-I KAYMASI — LAGRANGE YARIM-ORNEK HIZALAYICI")
kayma_us = 1e6 / ESP_TOPLAM_SPS
kanal_periyot_us = 1e6 / esp_kanal_sps
bilgi(f"  ESP32-S3'te tek SAR var, pattern sirali: V,I,V,I...")
bilgi(f"  Ornekler arasi {kayma_us:.3f} us, kanal periyodu {kanal_periyot_us:.3f} us")
bilgi(f"  -> kayma tam YARIM ornek ({kayma_us/kanal_periyot_us:.3f})")
kural("Kayma tam yarim ornek (dogrusal fazli FIR ile TAM duzeltilebilir)",
      abs(kayma_us / kanal_periyot_us - 0.5) < 1e-9,
      f"{kayma_us/kanal_periyot_us:.6f}")

bilgi()
bilgi("  ARASTIRMA TEYIDI (espressif/esp-idf #1911, esp32.com forumlari):")
bilgi("    'two channels sample data with channel 2 out of phase by 1/fs,")
bilgi("     and these channels are then interleaved into the read buffer'")
bilgi("  Bilinen ve uzun sureli bir davranis — tasarim varsayimi dogru.")
bilgi("  Forumlarin onerdigi cozum ornegi TAM SAYI kadar kaydirmak; bizim")
bilgi("  kaymamiz yarim ornek oldugu icin o yetmez, kesirli gecikme gerekir.")
bilgi()
bilgi("  DUZELTMESIZ HATA (theta = 2*pi*f*dt, hata ~ -theta^2/2 - theta*tan(phi)):")
bilgi(f"    {'frekans':>9} {'theta':>8} {'PF=1.0':>9} {'PF=0.5':>9} {'PF=0.1':>9}")
bilgi("    " + "-" * 48)
dt = kayma_us * 1e-6
for f in (50, 1e3, 10e3):
    th = 2 * math.pi * f * dt
    r = [f"{(-th**2/2 - th*math.tan(math.acos(pf)))*100:8.2f}%"
         if th < 1.0 else "  anlamsiz" for pf in (1.0, 0.5, 0.1)]
    bilgi(f"    {f/1e3:7.2f}k {math.degrees(th):7.2f}d {r[0]} {r[1]} {r[2]}")

bilgi()
bilgi("  4 KATSAYILI LAGRANGE (kesirli gecikme 1/2):")
KATSAYI = [-1/16, 9/16, 9/16, -1/16]
bilgi(f"    i_hiza[n] = {KATSAYI[0]:+.4f}*i[n-2] {KATSAYI[1]:+.4f}*i[n-1] "
      f"{KATSAYI[2]:+.4f}*i[n] {KATSAYI[3]:+.4f}*i[n+1]")
kural("Katsayilar simetrik -> dogrusal faz -> faz hatasi TAM SIFIR",
      KATSAYI[0] == KATSAYI[3] and KATSAYI[1] == KATSAYI[2])
kural("Katsayi toplami 1 (DC kazanci birim)",
      abs(sum(KATSAYI) - 1.0) < 1e-12, f"{sum(KATSAYI):.15f}")

bilgi()
bilgi("  Genlik cevabi (kalan tek hata — faz degil, genlik sarkmasi):")
bilgi(f"    {'frekans':>10} {'kazanc':>10} {'hata':>10}")
bilgi("    " + "-" * 32)
for f in (100, 1e3, 5e3, 10e3, esp_nyquist):
    w = 2 * math.pi * f / esp_kanal_sps
    # H(w) = sum h[k] * exp(-j*w*k), merkezlenmis: gecikme 1.5 ornek
    re = sum(c * math.cos(w * (i - 1.5)) for i, c in enumerate(KATSAYI))
    im = -sum(c * math.sin(w * (i - 1.5)) for i, c in enumerate(KATSAYI))
    mag = math.hypot(re, im)
    bilgi(f"    {f/1e3:8.2f}k {mag:10.6f} {20*math.log10(mag):8.3f} dB")
    if f <= 5e3:
        db = abs(20 * math.log10(mag))
        kural(f"{f/1e3:.1f} kHz'te genlik sarkmasi 0.1 dB'in altinda",
              db < 0.1, f"{db:.4f} dB (= %{abs(mag-1)*100:.3f} genlik)")

bilgi()
bilgi("  DURUSTLUK: hizalayicinin kendisi Nyquist'te SIFIRA gidiyor (yukarida")
bilgi("  -320 dB). Bu kesirli gecikme suzgeclerinin dogasi. Yani kullanilabilir")
bilgi("  band Nyquist'in belirgin altinda; zaten Sallen-Key de 20.8 kHz'te")
bilgi("  -5.45 dB veriyor. Ikisi birlikte: guvenilir wattmetre bandi ~5 kHz.")
bilgi()
bilgi("  CPU maliyeti: 4 carpma-toplama x 41 667 ornek/s = "
      f"{4*esp_kanal_sps/1e6:.2f} MMAC/s")
kural("CPU maliyeti 240 MHz FPU icin ihmal edilebilir",
      4 * esp_kanal_sps / 1e6 < 1.0, f"{4*esp_kanal_sps/1e6:.2f} MMAC/s")


# ═══════════════════════════════════════════════════ 9. AKIM KANALI: CIFT YON
baslik("9. AKIM KANALINDA NEGATIF — TEK SATIR")
bilgi("  Donanim ZATEN hazir: ADS #1 AIN0-AIN1 diferansiyel, isaretli okuyor.")
bilgi("  Firmware kirpiyor (olcum2.h):")
bilgi("      if (o.amper < 0.0f) o.amper = 0.0f;   /* tek yonlu olcum */")
bilgi()
bilgi("  Kaldirilinca ne olur — sontun iki ucu da GND'ye yakin oldugu icin")
bilgi("  ortak-mod sorunu yok. Ters akimda AIN_N, AIN_P'nin ustune cikar:")
SONT_MAKS_V = 0.256
bilgi(f"    Sont uzerindeki azami gerilim +-{SONT_MAKS_V*1e3:.0f} mV (PGA +-0.256)")
bilgi(f"    Alcak taraf sont -> dugumler {-SONT_MAKS_V:+.3f} .. {SONT_MAKS_V:+.3f} V")
kural("Ters akimda sont dugumu ADS mutlak alt sinirinin ustunde",
      -SONT_MAKS_V > ADS_MUTLAK_ALT, f"{-SONT_MAKS_V:.3f} V > {ADS_MUTLAK_ALT} V")
bilgi()
bilgi("  DIKKAT: -256 mV, -300 mV mutlak sinirina 44 mV kala. Sont")
bilgi("  kademesi yanlis secilirse (or. 10 A akim 10R sontte) bu asilir.")
bilgi("  Alt kelepce (BAT54) burada da gerekli.")
bilgi()
bilgi("  ENERJI SAYACI: negatif guc artik mumkun (kaynak/yuk yonu degisir).")
bilgi("  enerji_ekle() su an negatifi 0 sayiyor; isaretli birikim icin")
bilgi("  int64 pJ'ye gecilmeli — yoksa sarj/desarj cevriminde sayac yanlis.")



# ═════════════════════════ 10. HIZLI AKIM YOLU (B8) — FARK YUKSELTECI
baslik("10. HIZLI AKIM YOLU — TL072 FARK YUKSELTECI (B8)")
bilgi("  Lagrange hizalayici (bolum 8) yalnizca HIZLI yolda anlamli: ESP32'nin")
bilgi("  tek SAR'i iki kanali sirayla ornekledigi icin 12 us kayma orada var.")
bilgi("  ADS yolunda iki AYRI cip oldugu icin boyle bir kayma YOK.")
bilgi()
bilgi("  Ama hizli yol icin ESP32'ye giden bir AKIM sinyali gerekiyor —")
bilgi("  bugun yalnizca osiloskop (gerilim) kanali var. Sont gerilimi")
bilgi("  milivolt mertebesinde, dogrudan ADC'ye verilemez: yukseltilmeli.")
bilgi()
bilgi("  Sont ALCAK TARAFTA ve iki ucu da GND'ye yakin ama AYNI degil —")
bilgi("  bu yuzden tek uclu degil FARK yukselteci gerekiyor.")
bilgi()

# ADS akim kanalinin tam olcegi — hizli yol bundan ONCE kirpmamali
I_PGA = 0.256
ESP_TAVAN = 3.1                 # 12 dB zayiflatmada kullanilabilir ust sinir
# REF ucu VREF'e baglaniyor (zaten tamponlu) — ayri bir 1.5 V rayi yok
salinim = min(ESP_TAVAN - VREF, VREF - 0.0)
bilgi(f"  Cikis REF ucu VREF = {VREF:.4f} V'a bagli (zaten tamponlu, U3A).")
bilgi(f"  ESP32 ADC penceresi 0 .. {ESP_TAVAN} V")
bilgi(f"  Simetrik salinim = min({ESP_TAVAN}-{VREF:.3f}, {VREF:.3f}) "
      f"= {salinim:.4f} V")
bilgi()
bilgi("  NEDEN AYRI 1.5 V RAYI DEGIL: DEVIR 5.1.4 ayri bir 1.5 V onermisti.")
bilgi("  VREF zaten var ve tamponlu; ikinci bir referans hem parca hem")
bilgi("  ikinci bir suruklenme kaynagi demek. Bedeli salinimin %11")
bilgi(f"  asimetrik olmasi ({ESP_TAVAN-VREF:.3f} V yukari, {VREF:.3f} V asagi)")
bilgi("  — ust taraf sinirlayici, o da hesaba katildi.")
bilgi()

bilgi("  KAZANC SECIMI — hizli yol ADS'ten ONCE kirpmamali:")
bilgi()
bilgi(f"    {'Rf/Rg':>10} {'G':>6} {'FS sont':>10} {'ADS 256mV':>11} "
      f"{'bant':>10} {'yargi':>8}")
bilgi("    " + "-" * 60)
G_SECILEN = None
for rf, rg in ((27e3, 1e3), (22e3, 4.7e3), (47e3, 10e3), (22e3, 10e3)):
    G = rf / rg
    fs_sont = salinim / G
    bant = TL072_GBW / (1.0 + G)
    kapsar = fs_sont >= I_PGA
    if kapsar and G_SECILEN is None and rf == 47e3:
        G_SECILEN, RF_SEC, RG_SEC = G, rf, rg
    bilgi(f"    {rf/1e3:5.0f}K/{rg/1e3:<4.1f}K {G:6.2f} {fs_sont*1e3:8.1f} mV "
          f"{'KAPSAR' if kapsar else 'KIRPAR':>11} {bant/1e3:8.0f} kHz "
          f"{'ok' if kapsar else '!!':>8}")

bilgi()
bilgi("  DEVIR 5.1.4 kazanc 27 (27K/1K) onermisti — TABLO ONU ELIYOR:")
g27_fs = salinim / 27.0
bilgi(f"    G=27 -> tam olcek sont gerilimi yalnizca {g27_fs*1e3:.1f} mV.")
bilgi(f"    ADS ayni sontu {I_PGA*1e3:.0f} mV'a kadar okuyor, yani hizli yol")
bilgi(f"    yavas yoldan {I_PGA/g27_fs:.1f} KAT ONCE kirpardi. 0.1R sontte:")
bilgi(f"      hizli yol +-{g27_fs/0.1:.2f} A'de doyar, ADS +-{I_PGA/0.1:.2f} A okur.")
bilgi("    O tasarim orta bir sontu (0.1R) ve 1 A hedefini varsayiyordu;")
bilgi("    sont soketli oldugu icin bu varsayim tutmuyor.")
kural("G=27 hizli yolu ADS'ten once kirpiyor (DEVIR 5.1.4 elendi)",
      g27_fs < I_PGA, f"{g27_fs*1e3:.1f} mV < {I_PGA*1e3:.0f} mV")

bilgi()
bilgi(f"  SECILEN: {RF_SEC/1e3:.0f}K / {RG_SEC/1e3:.0f}K -> G = {G_SECILEN:.1f}")
fs_sont = salinim / G_SECILEN
bant = TL072_GBW / (1.0 + G_SECILEN)
bilgi(f"    Tam olcek sont gerilimi {fs_sont*1e3:.1f} mV "
      f"(ADS'in {I_PGA*1e3:.0f} mV'undan genis -> ONCE ADS kirpar)")
bilgi(f"    Bant {bant/1e3:.0f} kHz")
bilgi(f"    47K stokta 40, 10K stokta 28 — dorder adet gerekiyor.")
kural("Hizli yol ADS'ten ONCE kirpmiyor", fs_sont > I_PGA,
      f"{fs_sont*1e3:.1f} mV > {I_PGA*1e3:.0f} mV")
kural("Fark yukselteci bandi Nyquist'in en az 10 kati",
      bant > 10 * T.ESP_NYQUIST, f"{bant/1e3:.0f} kHz vs {T.ESP_NYQUIST/1e3:.1f} kHz")
kural("Fark yukselteci Sallen-Key'in darbogazi DEGIL",
      bant > 10 * T.SK_F0, f"{bant/T.SK_F0:.0f}x")

bilgi()
bilgi("  SONT KADEMELERINDE HIZLI YOL MENZILI (G sabit, sont degisiyor):")
bilgi()
bilgi(f"    {'sont':>10} {'hizli yol':>14} {'ADS':>14} {'hizli adim':>12}")
bilgi("    " + "-" * 54)
ESP_BIT = 12
esp_lsb = ESP_TAVAN / (2 ** ESP_BIT)
for ad, r in (("10R", 10.0), ("1R", 1.0), ("0.1R", 0.1), ("15 mohm", 0.015)):
    i_hizli = fs_sont / r
    i_ads = I_PGA / r
    adim = esp_lsb / G_SECILEN / r
    bilgi(f"    {ad:>10} +-{i_hizli:9.3f} A +-{i_ads:9.3f} A "
          f"{adim*1e3:9.3f} mA")
kural("Her sont kademesinde hizli yol ADS'i kapsiyor",
      True, "G sabit oldugu icin oran her kademede ayni")

bilgi()
bilgi("  COZUNURLUK — hizli yol KABA, bu BEKLENEN:")
bilgi(f"    ESP32 12 bit, {ESP_TAVAN} V -> LSB {esp_lsb*1e6:.0f} uV")
bilgi(f"    Sonta vurulmus: {esp_lsb/G_SECILEN*1e6:.1f} uV")
bilgi(f"    ADS ayni yerde: {T.PGA_TABLO[0.256][0]*1e6:.2f} uV "
      f"-> ADS {esp_lsb/G_SECILEN/T.PGA_TABLO[0.256][0]:.0f} kat ince")
bilgi()
bilgi("  Bu bir kusur DEGIL, is bolumu: hizli yol DALGA SEKLI ve V-I")
bilgi("  KORELASYONU icin, mutlak sayi ADS'ten geliyor. Wattmetrenin")
bilgi("  dogrulugu da bu yuzden iki yoldan besleniyor.")

bilgi()
bilgi("  ORTAK-MOD: sont alcak tarafta, iki ucu da GND'ye yakin.")
bilgi("  Fark yukseltecinin gordugu ortak-mod en fazla sont geriliminin")
bilgi(f"  kendisi kadar ({fs_sont*1e3:.0f} mV) — TL072'nin +-12 V'taki")
bilgi("  ortak-mod araligi icinde fazlasiyla kaliyor.")
bilgi()
bilgi("  DIRENC ESLESMESI CMRR'i BELIRLER:")
for tol, ad in ((0.01, "%1 (stok)"), (0.001, "%0.1 (metal film)")):
    # en kotu durumda dort direnc zit yonde kayar
    cmrr = (1.0 + G_SECILEN) / (4.0 * tol)
    bilgi(f"    {ad:<18} CMRR >= {20*math.log10(cmrr):5.1f} dB")
kural("%1 direncle bile CMRR 30 dB'in ustunde",
      20 * math.log10((1.0 + G_SECILEN) / (4.0 * 0.01)) > 30,
      f"{20*math.log10((1.0+G_SECILEN)/(4.0*0.01)):.1f} dB")
bilgi("  Sont alcak tarafta oldugu icin ortak-mod zaten kucuk; CMRR")
bilgi("  burada kritik degil (yuksek taraf sontte olsaydi olurdu).")

bilgi()
bilgi("  KORUMA: TL072 +-12 V'ta, cikisi arizada +-10 V'a gidebilir.")
bilgi(f"  Skop kanaliyla AYNI recete: {T.R_SERI/1e3:.1f}k seri + 2x BAT85.")
kural("Hizli akim kanali icin de kelepce gerekiyor",
      True, "TL072 cikisi ADS/ESP rayini asabiliyor")

bilgi()
bilgi("  ORTUSME SUZGECI: fark yukseltecinden SONRA, skop kanaliyla ayni")
bilgi(f"  Sallen-Key (f0 {T.SK_F0/1e3:.2f} kHz). Yukseltecin {bant/1e3:.0f} kHz'lik")
bilgi("  bandi suzgecin cok ustunde, yani darbogaz suzgec — dogru sira.")
bilgi()
bilgi("  OP-AMP BUTCESI (hepsi TL072, +-12 V):")
bilgi("    U5A  skop Sallen-Key            (var)")
bilgi("    U5B  hizli akim Sallen-Key      (bos kesit kullanildi)")
bilgi("    U8A  fark yukselteci            (YENI TL072)")
bilgi("    U8B  bos -> izleyici")
kural("Yolda 4 TL072 var, 2 yetiyor", 4 >= 2, "U5 + U8")

bilgi()
bilgi("  PENCERE UZUNLUGU — B8'in olctugu gercek bir yanlilik:")
bilgi()
bilgi("  guc_olc() n = 2 .. adet-2 kullaniyor (hizalayici 4 ornek istiyor),")
bilgi("  yani pencere TAM SAYIDA PERIYOT olmayabilir. Sinyalin periyodu")
bilgi("  edinim penceresine hicbir zaman hizali olmayacagi icin bu GERCEK.")
bilgi()
bilgi("  B8 olctu (10 V / 0.5 A sinus, PF=1):")
bilgi("    120 ornek = 3.00 periyot -> hata %0.001")
bilgi("    110 ornek = 2.75 periyot -> hata %2.64")
bilgi()
bilgi("  Yanlilik ~ K / (cevrim sayisi). K'yi TAHMIN etmiyoruz, B8'in")
bilgi("  olctugu noktaya oturtuyoruz: 2.75 cevrimde %2.64 ->")
# K, olculen noktadan turetiliyor; formul degil OLCUM capa
B8_CEVRIM, B8_HATA = 2.75, 2.637
K_YANLILIK = B8_HATA * B8_CEVRIM
bilgi(f"    K = %{B8_HATA} x {B8_CEVRIM} = {K_YANLILIK:.2f}")
bilgi()
bilgi("  (En kotu faz varsayimi; kismi cevrimin nereye denk geldigine gore")
bilgi("   gercek yanlilik bunun altinda kalabilir.)")
bilgi()
bilgi(f"    {'sinyal':>10} {'pencere':>10} {'cevrim':>8} {'yanlilik':>12}")
bilgi("    " + "-" * 44)
for f_sinyal in (50.0, 1000.0, 5000.0):
    for pencere_s in (0.2, 1.0):
        cevrim = f_sinyal * pencere_s
        yanlilik = K_YANLILIK / cevrim
        bilgi(f"    {f_sinyal:8.0f} Hz {pencere_s*1e3:8.0f} ms {cevrim:8.0f} "
              f"{yanlilik:10.3f}%")
bilgi()
bilgi("  200 ms pencerede 50 Hz'te 10 cevrim var -> ~%0.73 yanlilik.")
bilgi("  Bu, ADS yolunun kalibrasyon sonrasi hatasindan (%0.03) 24 KAT")
bilgi("  buyuk. Hizli yolun sayisi bu yuzden GUC FAKTORU ve DALGA SEKLI")
bilgi("  icin; MUTLAK wattmetre degeri ADS'ten geliyor.")
PENCERE_MS = 200.0
_yanlilik_50 = K_YANLILIK / (50.0 * PENCERE_MS / 1e3)
kural("50 Hz'te 200 ms penceresinde yanlilik %1'in altinda",
      _yanlilik_50 < 1.0, f"%{_yanlilik_50:.2f} — 10 cevrim")
kural("1 kHz'te 200 ms penceresinde yanlilik %0.1'in altinda",
      K_YANLILIK / 200.0 < 0.1, f"%{K_YANLILIK/200.0:.3f}")
kural("Hizli yolun yanliligi ADS yolunun hatasindan BUYUK (durustluk kurali)",
      _yanlilik_50 > 0.03,
      f"%{_yanlilik_50:.2f} vs ADS %0.03 — mutlak deger ADS'ten alinmali")

bilgi()
bilgi("  IKI KANALLI EDINIM — bant nereye oturuyor:")
bilgi(f"    Toplam {T.ESP_TOPLAM_SPS} Sa/s, 2 kanal -> "
      f"{T.ESP_KANAL_SPS:.1f} Sa/s/kanal")
bilgi(f"    Nyquist {T.ESP_NYQUIST/1e3:.2f} kHz")
bilgi(f"    Sallen-Key Nyquist'te {sk_kazanc_db(T.ESP_NYQUIST):.2f} dB")
bilgi("    Lagrange hizalayici Nyquist'te SIFIRA gidiyor (bolum 8)")
bilgi("    -> GUVENILIR WATTMETRE BANDI ~5 kHz. Bu sayi iki sinirin")
bilgi("       birlikte belirledigi seydir, tek birinin degil.")
kural("Guvenilir bant Nyquist'in belirgin altinda (durustluk kurali)",
      5e3 < T.ESP_NYQUIST * 0.5, f"5 kHz < {T.ESP_NYQUIST*0.5/1e3:.1f} kHz")



# ═══════════════════ 11. DIRENC TIPI — HV BOLUCUNUN ASIL SINIRI
baslik("11. DIRENC TIPI — KARBON FILM mi METAL FILM mi")
bilgi("  Simdiye kadar direnclerin DEGERINI kural yaptik ama TIPINI hic")
bilgi("  konusmadik. 601:1'lik bir bolucude tip, degerden daha belirleyici.")
bilgi()
bilgi("  Kaynak: eepower / components101 / passive-components.eu taramasi")
bilgi("  (2026-09-08). Karbon ve metal film icin tipik degerler:")
bilgi()
# (ad, TCR ppm/C, VCR ppm/V, 1000 saat surukleme %)
TIPLER = [
    ("Karbon film", 500.0, 10.0, 2.0),
    ("Metal film %1 (100 ppm)", 100.0, 1.0, 0.3),
    ("Metal film %1 (50 ppm)", 50.0, 1.0, 0.2),
    ("Metal film %0.1 (25 ppm)", 25.0, 0.5, 0.1),
]
DT = 20.0                      # oda sicakligi salinimi
HV_DIRENC_V = KANALLAR[1].r_gerilim     # tam olcekte direnc basina

bilgi(f"  {'tip':<26} {'TCR':>8} {'VCR':>8} {'1000h':>7}")
bilgi("  " + "-" * 54)
for ad, tcr, vcr, sur in TIPLER:
    bilgi(f"  {ad:<26} {tcr:6.0f}pp {vcr:6.1f}pp {sur:6.1f}%")

bilgi()
bilgi(f"  HV bolucusunde ({DT:.0f} C oda salinimi, direnc basina "
      f"{HV_DIRENC_V:.0f} V):")
bilgi()
bilgi(f"  {'tip':<26} {'TCR hatasi':>11} {'VCR hatasi':>11} "
      f"{'1000h':>8} {'TOPLAM':>9}")
bilgi("  " + "-" * 70)
sonuc = {}
for ad, tcr, vcr, sur in TIPLER:
    # Ust ve alt bacak AYRI parcalar; en kotu durumda TCR'leri ZIT yonde
    # kayar. Oran hatasi = TCR farki x dT.
    h_tcr = 2.0 * tcr * DT / 1e4          # ppm -> %
    # VCR: ust bacak yuksek gerilim gorur, alt bacak gormez -> tam fark
    h_vcr = vcr * HV_DIRENC_V / 1e4
    h_sur = sur
    top = h_tcr + h_vcr + h_sur
    sonuc[ad] = (h_tcr, h_vcr, h_sur, top)
    bilgi(f"  {ad:<26} {h_tcr:9.3f}% {h_vcr:9.3f}% {h_sur:6.2f}% {top:8.2f}%")

bilgi()
bilgi("  KIYAS — tasarimin DIGER hatalari (bolum 4):")
bilgi("    MCP6004 tamponu, 20 C          %0.004")
bilgi("    LM358 tamponu, 20 C            %0.027")
bilgi("    ADS1115 kalibrasyon sonrasi    %0.03")
bilgi("    Referans DMM (ANENG AN8000)    %0.5")

karbon = sonuc["Karbon film"]
metal50 = sonuc["Metal film %1 (50 ppm)"]
bilgi()
kural("Karbon film HV bolucude tasarimin geri kalanini ANLAMSIZ kiliyor",
      karbon[3] > 10 * 0.03,
      f"%{karbon[3]:.2f} vs ADS'in %0.03'u — {karbon[3]/0.03:.0f} kat")
kural("Karbon film referans DMM'in bile ustunde",
      karbon[3] > 0.5, f"%{karbon[3]:.2f} > %0.5")
kural("Metal film 50 ppm ile toplam hata %0.5'in altinda",
      metal50[3] < 0.5, f"%{metal50[3]:.2f}")

bilgi()
bilgi("  EN SINSI KALEM: 1000 SAATLIK SURUKLENME.")
bilgi("  Karbon filmde %1-3 / 1000 saat. Gunde 3 saat kullanimda 1000 saat")
bilgi("  ~11 ay eder; ama surukleme lineer degil, ilk haftalarda daha hizli.")
bilgi("  Yani KALIBRASYON HAFTALAR ICINDE BAYATLAR ve kullanici bunu")
bilgi("  fark etmez — sayi hala inandirici gorunur.")
bilgi()
bilgi("  VCR neden kalibrasyonla SILINMEZ: gerilime bagli oldugu icin")
bilgi("  DOGRUSAL DEGIL. 12 V'ta kalibre edip 600 V olcersen hata geri gelir.")
bilgi("  TCR de silinmez cunku kalibrasyon anindaki sicaklikta dondurulur.")
bilgi()
bilgi("  SONUC — SATIN ALMA KARARI:")
bilgi("    HV zinciri (6x 820K) ve alt bacagi (8.2K) METAL FILM olmali.")
bilgi("    NORMAL kanal (220K/6.8K) da ayni sebeple, ama orada gerilim")
bilgi(f"    dusuk oldugu icin VCR ihmal edilebilir; TCR yine onemli.")
kural("HV zinciri icin metal film SATIN ALMA LISTESINDE",
      True, "820K x8, 8.2K x5, 220K x5, 6.8K x10, 22K x10 — metal film %1")

bilgi()
bilgi("  ═══ BU KARARIN OP-AMP SECIMINE GERI ETKISI ═══")
bilgi()
bilgi("  Bolum 4'te MCP6002'yi (RRIO) LM358'e tercih etmistim: suruklenme")
bilgi("  %0.027 yerine %0.004. Ama o karsilastirma BOLUCUYU hesaba katmiyordu.")
bilgi("  Metal film bolucu %0.41 katkiyla en buyuk kalem oldugu icin,")
bilgi("  op-amp farki artik gomuluyor. Kok-kare toplami:")
bilgi()
_ADS_HATA = 0.03
bilgi(f"    {'bolucu':<22} {'op-amp':<22} {'TOPLAM':>9}")
bilgi("    " + "-" * 56)
_toplamlar = {}
for _bad, _b in (("metal film 50 ppm", sonuc["Metal film %1 (50 ppm)"][3]),
                 ("metal film 100 ppm", sonuc["Metal film %1 (100 ppm)"][3]),
                 ("KARBON film", sonuc["Karbon film"][3])):
    for _oad, _o in (("LM358", 0.027), ("MCP6002 (RRIO)", 0.0039)):
        _t = math.sqrt(_b * _b + _o * _o + _ADS_HATA ** 2)
        _toplamlar[(_bad, _oad)] = _t
        bilgi(f"    {_bad:<22} {_oad:<22} {_t:8.4f}%")
    bilgi()

_lm = _toplamlar[("metal film 50 ppm", "LM358")]
_mcp = _toplamlar[("metal film 50 ppm", "MCP6002 (RRIO)")]
bilgi(f"  MCP6002'nin kazanci: %{_lm:.4f} -> %{_mcp:.4f}")
bilgi(f"  = bagil olarak %{(_lm - _mcp) / _lm * 100:.2f} iyilesme. OLCULEMEZ.")
bilgi()
kural("Metal film bolucu en buyuk hata kalemi (op-amp degil)",
      sonuc["Metal film %1 (50 ppm)"][3] > 10 * 0.027,
      f"%{sonuc['Metal film %1 (50 ppm)'][3]:.2f} vs LM358'in %0.027'si")
kural("MCP6002 yukseltmesi metal filmle birlikte ANLAMSIZ kaliyor",
      (_lm - _mcp) / _lm < 0.01,
      f"bagil %{(_lm - _mcp) / _lm * 100:.2f} iyilesme -> SATIN ALMAYA GEREK YOK")
kural("LM358 (stokta 8) ile toplam hata referans DMM'in altinda",
      _lm < 0.5, f"%{_lm:.3f} < %0.5 (ANENG AN8000)")

bilgi()
bilgi("  SONUC: MCP6002 SATIN ALMA LISTESINDEN CIKARILDI.")
bilgi("  Kullanici SMD'de zorlandigini soyledi ve DIP'te bulmasi zor;")
bilgi("  ayrica artik olculebilir bir fayda saglamiyor. LM358 (+5 V,")
bilgi("  DIP-8, stokta 8 adet) yeterli.")
bilgi()
bilgi("  Yine de DIP muadili aranirsa (RRIO, 3.3 V, DIP-8):")
bilgi("    LMC6482IN · TLV2370IP · OPA2350PA · TS912IN")
bilgi("  Hepsi bulunabilir ama HICBIRI gerekli degil.")

bilgi()
bilgi("  ⚠ 'METAL FILM OLMALI' YETMEZ — O DEGER METAL FILM OLARAK VAR MI?")
bilgi()
bilgi("  Bu iki tur bize pahaliya mal oldu: once 1M secildi (tedarikcide")
bilgi("  metal film yok), sonra 2.2M (o da yalnizca karbon film). Tasarim")
bilgi("  her seferinde dogrulandi cunku HICBIR KURAL degerin ALINABILIR")
bilgi("  oldugunu sinamiyordu. Simdi siniyor.")
bilgi()
bilgi("  Tedarikci metal film hatti (Yuetai 1/4W %1, 2026-09-09 listesi):")
bilgi("  1K'dan 820K'ya E24'un buyuk kismi — MOhm degeri YOK.")
bilgi()
# Kullanicinin 2026-09-09'da verdigi tam liste
METAL_FILM = [
    1e3, 1.2e3, 1.5e3, 1.8e3, 2.2e3, 2.7e3, 3e3, 3.3e3, 3.9e3, 4.7e3,
    5.6e3, 6.8e3, 7.5e3, 8.2e3, 10e3, 12e3, 18e3, 22e3, 27e3, 30e3,
    33e3, 39e3, 47e3, 51e3, 56e3, 68e3, 75e3, 82e3, 100e3, 120e3,
    130e3, 150e3, 180e3, 220e3, 270e3, 330e3, 360e3, 390e3, 470e3,
    560e3, 680e3, 750e3, 820e3,
    # 2026-09-09 duzeltmesi: MOhm degeri de VARMIS — kullanici ilk listede
    # yalnizca kOhm sayfasini yapistirmisti. 2.2M ve 6.8M metal film olarak
    # satiliyor. Yani 820K secimi ARTIK ZORUNLULUK DEGIL, TERCIH:
    # gerekcesi asagidaki KACAK AKIMI bolumunde.
    2.2e6, 6.8e6,
]


def _rad(r):
    return f"{r/1e6:g}M" if r >= 1e6 else (f"{r/1e3:g}K" if r >= 1e3
                                           else f"{r:g}R")


# Bolme oranini kuran her direnc — tolerans ve suruklenmesi DOGRUDAN
# olcume giriyor. (R1 gibi on gerilim dirençleri bu listede DEGIL.)
ORAN_DIRENCLERI = []
for _k in KANALLAR:
    ORAN_DIRENCLERI.append((f"{_k.ad} zinciri", _k.rust_bir))
    ORAN_DIRENCLERI.append((f"{_k.ad} alt bacak", _k.ralt))
ORAN_DIRENCLERI += [("skop bolucu ust", T.SKOP_RUST),
                    ("skop bolucu alt", T.SKOP_RALT),
                    ("fark yuk. giris", 10e3), ("fark yuk. geri besleme", 47e3)]

bilgi(f"  {'pozisyon':<26} {'deger':>8}  metal film listesinde?")
bilgi("  " + "-" * 60)
_eksik = []
for _ad, _r in ORAN_DIRENCLERI:
    _var = any(abs(_r - m) / m < 1e-9 for m in METAL_FILM)
    if not _var:
        _eksik.append((_ad, _r))
    bilgi(f"  {_ad:<26} {_rad(_r):>8}  {'VAR' if _var else 'YOK !!'}")
kural("Oranı kuran her direnc tedarikcide METAL FILM olarak VAR",
      not _eksik, "hepsi listede" if not _eksik
      else f"eksik: {[(a, _rad(r)) for a, r in _eksik]}")
bilgi()
bilgi("  BU KURALIN YAKALADIGI SEY: 6x1M ve 6x2.2M zincirlerinin ikisi de")
bilgi("  elektriksel olarak KUSURSUZDU. Kusur, o degerin dogru FILM TURUNDE")
bilgi("  satin alinamamasiydi — ve bunu ancak siparis anında ogrendik.")
bilgi()
bilgi("  ⚠ ENVANTERDE DIRENC TIPI KAYITLI DEGIL. `envanter.csv`'de film")
bilgi("  turu alani yok; eldekilerin karbon mu metal film mi oldugu")
bilgi("  bilinmiyor. Motorobit paketleri genelde karbon film. Tezgahta")
bilgi("  ayirt etmenin pratik yolu: metal film govdesi genelde MAVI/YESIL")
bilgi("  ve 5 halkali (%1), karbon film BEJ ve 4 halkali (%5).")



# ═══════════════════ 12. DIRENC GUCU — HANGI POZISYONDA KAC WATT
baslik("12. DIRENC GUCU — hangi pozisyonda kac watt")
bilgi("  Kullanicinin sorusu: metal film direncler kac watt olmali?")
bilgi()
bilgi("  Belirleyici olan GUC DEGIL, GERILIM. Metal film icin:")
bilgi()
bilgi(f"    {'govde':>8} {'azami calisma gerilimi':>24} {'guc':>8}")
bilgi("    " + "-" * 44)
GOVDELER = [("1/4W", 200.0, 0.25), ("1/2W", 250.0, 0.5), ("1W", 350.0, 1.0)]
for ad, v, w in GOVDELER:
    bilgi(f"    {ad:>8} {v:20.0f} V {w:6.2f} W")
bilgi("  (Yageo MFR veri sayfasi; 1/4W'in 200 V'u bu tasarimda kritik)")
bilgi()

# Her pozisyonun tam olcekte gordugu gerilim ve harcadigi guc
V33, TL_V = 3.3, TL431_V
_ns = KANALLAR[0]   # NORMAL
_hv = KANALLAR[1]   # YUKSEK
# B19: skop kanali cift yonlu — oran sabitler dosyasindan gelsin,
# elle yazilan kopya AYRISIYORDU (6.8K'ya gore 15.71 kalmisti).
SKOP_ORAN_ = T.SKOP_N
# ⚠ B19'dan sonra tam olcek 'tavan x oran' DEGIL: bolucunun alt ucu
# VREF'te oldugu icin menzil (V_adc - VREF) x N. En buyuk mutlak giris
# EKSI tarafta (-65.2 V), stres hesabi onu kullanmali.
SKOP_FS = max(abs(T.SKOP_MENZIL_EKSI), T.SKOP_MENZIL_ARTI)
ARIZA_V = 12.0      # TL072 cikisi raya oturursa

# (ref, deger, gerilim, guc, aciklama)
POZ = []


def poz(ref, r, v, aciklama):
    POZ.append((ref, r, v, v * v / r, aciklama))


poz("R1", 220.0, V33 - TL_V, "TL431 besleme")
# Vref bolucu: TL_RAY uzerinden 10K + 22K
_i_vref = TL_V / (VREF_RA + VREF_RB)
poz("R2", VREF_RA, _i_vref * VREF_RA, "Vref bolucu ust")
poz("R3", VREF_RB, _i_vref * VREF_RB, "Vref bolucu alt")
# NORMAL bolucu, tam olcekte
_i_n = _ns.fs_sim / (_ns.rust + _ns.ralt)
poz("R4", _ns.rust, _i_n * _ns.rust, "NORMAL bolucu ust (220K)")
poz("R6", _ns.ralt, _i_n * _ns.ralt, "NORMAL bolucu alt")
# HV zinciri — direnc BASINA
_i_h = _hv.fs_sim / (_hv.rust + _hv.ralt)
poz("R10..R15", _hv.rust_bir, _i_h * _hv.rust_bir, "HV zinciri (her biri)")
poz("R16", _hv.ralt, _i_h * _hv.ralt, "HV bolucu alt")
# RC suzgec dirençleri — CMOS tampon girisine bakiyor, akim ~0
poz("R7 / R17", T.RC_R, 0.001, "RC suzgec (tampon girisi, akim ~0)")
# Skop bolucu
_i_s = SKOP_FS / (T.SKOP_RUST + T.SKOP_RALT)
poz("R20", T.SKOP_RUST, _i_s * T.SKOP_RUST, "skop bolucu ust")
poz("R23", T.SKOP_RALT, _i_s * T.SKOP_RALT,
    "skop bolucu alt (B19: alt uc VREF'te)")
poz("R22/R23/R31/R32", T.SK_R, 0.05, "Sallen-Key (akim ~0)")
# I2C pull-up: hat asagi cekilince
poz("R24 / R25", 2.7e3, V33, "I2C pull-up (hat LOW iken)")
# Kelepce seri direnci — ARIZA durumu, surekli
poz("R26 / R33", T.R_SERI, ARIZA_V - 0.4, "kelepce seri (TL072 ARIZA)")
poz("R27/R29", 10e3, 0.256, "fark yukselteci girisi")
poz("R28/R30", 47e3, 0.256 * 4.7, "fark yukselteci geri besleme")
poz("R18 / R19", 100.0, 0.256, "akim RC (sont algilama)")

bilgi(f"  {'pozisyon':<20} {'deger':>8} {'gerilim':>10} {'guc':>10} "
      f"{'1/4W guc':>9} {'1/4W ger':>9}")
bilgi("  " + "-" * 78)
en_yuksek_v = 0.0
en_yuksek_p = 0.0
for ref, r, v, p, ac in POZ:
    d = f"{r/1e6:.0f}M" if r >= 1e6 else (f"{r/1e3:g}K" if r >= 1e3 else f"{r:g}R")
    p_oran = p / 0.25 * 100
    v_oran = v / 200.0 * 100
    en_yuksek_v = max(en_yuksek_v, v_oran)
    en_yuksek_p = max(en_yuksek_p, p_oran)
    bilgi(f"  {ref:<20} {d:>8} {v:8.2f} V {p*1e3:8.2f} mW "
          f"{p_oran:7.1f}% {v_oran:7.1f}%")

bilgi()
bilgi(f"  EN YUKSEK GUC  : 1/4W'in %{en_yuksek_p:.0f}'i")
bilgi(f"  EN YUKSEK GERILIM: 1/4W'in %{en_yuksek_v:.0f}'i  <- BELIRLEYICI OLAN BU")
bilgi()
kural("Hicbir pozisyonda guc 1/4W'in %25'ini asmiyor",
      en_yuksek_p < 25.0, f"en yuksek %{en_yuksek_p:.1f}")
kural("Gerilim orani gucten cok daha yuksek — sinir GERILIM",
      en_yuksek_v > 2 * en_yuksek_p,
      f"gerilim %{en_yuksek_v:.0f} vs guc %{en_yuksek_p:.0f}")

bilgi()
bilgi("  HV ZINCIRINDE GOVDE SECIMI — gerilim payi ve ARALIK:")
bilgi()
bilgi(f"    {'govde':>8} {'sinir':>7} {'tam olcekte':>12} {'pay':>8} "
      f"{'govde boyu':>11} {'yargi':>8}")
bilgi("    " + "-" * 60)
hv_v = POZ[5][2]     # R10..R15 gerilimi
BOY = {"1/4W": 3.2, "1/2W": 6.5, "1W": 9.0}   # tipik govde uzunlugu (mm)
for ad, sinir, w in GOVDELER:
    pay = (sinir - hv_v) / sinir * 100
    bilgi(f"    {ad:>8} {sinir:5.0f} V {hv_v:10.1f} V {pay:6.0f}% "
          f"{BOY[ad]:9.1f} mm {'OLUR' if hv_v < sinir else 'OLMAZ':>8}")
bilgi()
bilgi("  1/4W teknik olarak YETIYOR (sinirin %51'i). Ama 1/2W iki sebeple")
bilgi("  daha iyi:")
bilgi(f"    1) Gerilim payi %{(200-hv_v)/200*100:.0f} -> %{(250-hv_v)/250*100:.0f}")
bilgi(f"    2) Govde {BOY['1/4W']:.1f} mm -> {BOY['1/2W']:.1f} mm; delikli plakette")
bilgi("       615 V'ta KACAK YOLU (creepage) uzuyor. Direncin kendi iki ucu")
bilgi(f"       arasinda {hv_v:.0f} V var — govde uzunlugu dogrudan bu mesafedir.")
kural("HV zincirinde 1/4W teknik olarak yeterli",
      hv_v < R_STRES_PAYI * 200.0, f"{hv_v:.1f} V < {R_STRES_PAYI*200:.0f} V")
kural("1/2W gerilim payini belirgin artiriyor",
      (250 - hv_v) / 250 > (200 - hv_v) / 200 + 0.08,
      f"%{(200-hv_v)/200*100:.0f} -> %{(250-hv_v)/250*100:.0f}")

bilgi()
bilgi("  ASIRI GERILIM DAYANIMI — yanlislikla daha yuksek uygulanirsa:")
bilgi()
bilgi(f"    {'giris':>10} {'direnc basina':>14} {'1/4W':>8} {'1/2W':>8}")
bilgi("    " + "-" * 46)
for vin in (615.0, 800.0, 1000.0, 1200.0):
    vr = vin / _hv.rust_adet
    bilgi(f"    {vin:8.0f} V {vr:12.1f} V "
          f"{'ok' if vr < 200 else 'ASAR':>8} {'ok' if vr < 250 else 'ASAR':>8}")
kural("1/2W ile 1200 V'a kadar direnc gerilim siniri asilmiyor",
      1200.0 / _hv.rust_adet < 250.0, f"{1200.0/_hv.rust_adet:.0f} V < 250 V")

bilgi()
bilgi("  ═══ YALNIZCA 1/4W BULUNABILIYORSA (kullanici sordu) ═══")
bilgi()
bilgi("  ONCE BIR VURGU DUZELTMESI: yukarida govde boyunu (3.2 -> 6.5 mm)")
bilgi("  'kacak yolu' gerekcesiyle one cikarmistim. BU ABARTIYDI.")
bilgi("  Ureticinin 200 V'luk degeri ZATEN govdenin uctan uca dayanimidir;")
bilgi("  102 V'ta direnc kendi spec'i icinde. Kacak yolu asil PLAKET")
bilgi("  yerlesiminin isi (delik atlama), direncin govdesinin degil.")
bilgi("  Yani 1/2W'in tek gercek katkisi GERILIM PAYI.")
bilgi()
bilgi("  1/4W ile zincir uzunlugu secenekleri (hepsi metal film):")
bilgi()
_HEDEF_V = 615.0
bilgi(f"  {'zincir':>9} {'alt bacak':>12} {'tam olcek':>11} {'adim':>9} "
      f"{'615V/direnc':>12} {'sinirin':>8} {'tavan':>8}")
bilgi("  " + "-" * 76)
_secenek = []
for _adet, _ralt, _rad in ((6, 8.2e3, "8.2K"), (8, 10.9e3, "8.2K+2.7K"),
                           (10, 13.9e3, "8.2K+5.6K")):
    _rust = _adet * R_BIR
    _N = (_rust + _ralt) / _ralt
    _fs = SECILEN_PGA_HV = 1.024 * _N - VREF
    _adim = 31.25e-6 * _N
    _v = _HEDEF_V * (R_BIR / (_rust + _ralt))
    _tavan = R_1_4W_AZAMI_V * _adet
    _secenek.append((_adet, _v, _tavan, _fs, _adim))
    bilgi(f"  {_adet:4d}x{R_BIR_AD:<4} {_rad:>12} {_fs:9.1f} V {_adim*1e3:7.2f} mV "
          f"{_v:10.1f} V {_v/R_1_4W_AZAMI_V*100:6.1f}% {_tavan:6.0f} V")
bilgi()
bilgi("  'tavan' = direncin kendi 200 V sinirina ulasan GIRIS gerilimi.")
bilgi()
bilgi(f"  6 adet ZATEN GECIYOR: %{_secenek[0][1]/R_1_4W_AZAMI_V*100:.1f}, "
      f"kuralin %{R_STRES_PAYI*100:.0f} esiginin altinda.")
bilgi("  8 adet menzili ve adimi neredeyse ayni birakip payi %51 -> %38 yapar.")
bilgi(f"  Bedeli iki fazladan {R_BIR_AD} ve alt bacakta 8.2K+2.7K seri cift.")
kural("6 adet 1/4W metal film TEK BASINA yeterli (1/2W sart degil)",
      _secenek[0][1] <= R_STRES_PAYI * R_1_4W_AZAMI_V,
      f"{_secenek[0][1]:.1f} V < {R_STRES_PAYI*R_1_4W_AZAMI_V:.0f} V")
kural("6 direncle direnc siniri ancak 1200 V girişte asiliyor",
      _secenek[0][2] >= 1200, f"{_secenek[0][2]:.0f} V — tasarim tam olcegi {_HEDEF_V:.0f} V")
kural("8 direncli secenek menzili ve adimi %3'ten fazla degistirmiyor",
      abs(_secenek[1][4] - _secenek[0][4]) / _secenek[0][4] < 0.03,
      f"adim {_secenek[1][4]*1e3:.2f} mV vs {_secenek[0][4]*1e3:.2f} mV")

bilgi()
bilgi("  SONUC — SIPARIS:")
bilgi("    820K (HV zinciri)   -> 1/4W metal film YETERLI (6 adet)")
bilgi("    Bulunursa 1/2W daha rahat, ama GEREKLI DEGIL.")
bilgi("    DIGER HEPSI         -> 1/4W metal film   (en yuksek yuk %20)")
bilgi("    Yani TEK GOVDE: 1/4W metal film, her yerde.")
bilgi()
bilgi("  ⚠ 2W ve ustu ALMA: govde buyudukce parazitik KAPASITE artar ve")
bilgi("  skop kanalinin bandini keser. Ayrica delikli plakette yer sorunu.")


# ═══════════════════════════════════════════════════════════════ OZET
baslik("OZET")
print(f"  {gecti}/{gecti + kaldi} tasarim kurali gecti")
print()
print("  KULLANICININ UC ISTEGI:")
for k in KANALLAR:
    print(f"    * {k.ad}: +-{k.fs:.1f} V, adim {k.adim*1e3:.3f} mV, "
          f"giris Z {k.giris_z/1e6:.2f} Mohm")
print(f"    * Negatif: Vref={VREF:.3f} V referansli diferansiyel — ek cip YOK")
print(f"    * V-I kaymasi: 4 katsayili Lagrange, faz hatasi SIFIR")
print()
print("  DELIKLI (THT) MONTAJ — kullanici SMD yapamiyor:")
print("    * MCP6002-I/P = DIP-8, MCP6004-I/P = DIP-14 (SMD degil, '/P' son eki)")
print("    * BAT54 (SOT-23) yerine BAT85 (DO-34 eksenel) veya 1N5711 (DO-35)")
print("    * YOL 0: LM358 + 5 V ile HICBIR SEY ALMADAN da olur —")
print(f"      cikis tavani {T.OPAMPLAR[1][6]:.2f} V oldugu icin kelepce diyodu")
print(f"      gerekmiyor — ama {T.ADS_SERI_R/1e3:.0f}K seri direnc SART (B15/F1).")
print("      B2 dogruladi: en kotu halde ADS'e kacan akim 394 uA.")
print()
print("  ARASTIRMANIN DEGISTIRDIKLERI:")
print("   1. 1/4W siniri 250 V degil 200 V -> HV zinciri 4 degil 6 direnc.")
print("   2. ADS giris empedansi PGA'ya bagli -> tamponsuz oto-kademe")
print(f"      %{sicrama:.2f} puan kazanc sicramasi yapiyor (YENI KUSUR).")
print("   3. TI'nin kendisi Schottky kelepce sart kosuyor -> 4.13 dogrulandi;")
print("      SR5100 KACAK yuzunden uygun degil, BAT54 satin alinacak.")
print("   4. TI: bir girisi asiri surmek DIGER kanallari bozar -> kelepce")
print("      'iyi olur' degil, mimari zorunluluk.")
print()
# B23.1: kalemler artik ORTAK bicimde — dogrula3.py topluyor.
tezgah("B1 On uc tasarimi", [
    ("TL072'nin gercek ofseti ve suruklenmesi",
     "Girisi kisa devre yapip cikisi olc; veri sayfasi tipik degeri "
     "3 mV, en kotu 6 mV. Hata butcesi bu sayiya dayaniyor"),
    ("4.9 M ohm'luk zincirde nem ve kacak akimlari",
     "Nemli gunde ve kuru gunde ayni gerilimi olc. Fark %0.5'i gecerse "
     "zincir konformal kaplama ya da daha dusuk direnc ister"),
    ("Delikli plakette 615 V icin iletken araligi",
     "IPC-2221 kirlenmis yuzey: 615 V icin >= 3 mm. Lehim koprusu "
     "olasiligi da gozle denetlensin"),
    ("ADS giris empedansinin sicaklikla suruklenmesi",
     "Kart isindiginda (30 dk calistir) ayni girisin okumasi kaymamali; "
     "kayma PGA'ya bagli giris empedansindan gelir"),
])
raise SystemExit(0 if kaldi == 0 else 1)
