# -*- coding: utf-8 -*-
"""Asama 3 on uc sabitleri — TEK KAYNAK.

`tasarim3.py` (B1, hesap) ve `sim3_giris.py` (B2, ngspice) ayni sayilardan
beslenir. Projenin kurali: bir sabit iki yerde yazilirsa sessizce ayrisir.
Asama 2'de FQBN'in basina bu gelmisti (DEVIR 4.9).
"""
from __future__ import annotations

import math

# ═════════════════════════════════════ ADS1115 — TI SBAS444B
VDD = 3.3
ADS_SAYIM = 32768
ADS_SPS = 860
# ADS1115 IC OSILATOR TOLERANSI — TI veri sayfasi (SBAS444).
# 860 SPS nominal, gercekte 774..946 SPS. B17'nin ana bulgusunun
# kaynagi bu: iki ADS surekli kipte kosarsa aralarindaki ornekleme
# kaymasi SABIT DEGIL, surukleniyor.
ADS_OSILATOR_TOL = 0.10

# I2C — ayar yazmasi: adres+W (9 bit) + yazmac (9) + iki veri baytI (18)
# + baslat/bitir. Kayma hesabinda kullaniliyor (B17 bolum 1).
I2C_HIZ = 400e3
I2C_YAZMA_BIT = 38
ADS_CALISMA_ALT = 0.0             # s.3 "Analog input voltage MIN: GND"
ADS_CALISMA_UST = VDD             # s.3 "MAX: VDD"
ADS_MUTLAK_ALT = -0.3             # s.12 ESD diyodu bu altta iletir
ADS_MUTLAK_UST = VDD + 0.3
ADS_GIRIS_AKIM_MAKS = 10e-3
ADS_OFSET_LSB = 3
ADS_PGA_UYUM = 0.001              # kademeler arasi kazanc uyumu %0.1 maks

# PGA -> (LSB volt, Z_diferansiyel, Z_ortak-mod)   s.13 Tablo 2 + s.3
PGA_TABLO = {
    6.144: (187.5e-6, 22.0e6, 10e6),
    4.096: (125.0e-6, 15.0e6,  6e6),
    2.048: (62.50e-6,  4.9e6,  6e6),
    1.024: (31.25e-6,  2.4e6,  3e6),
    0.512: (15.625e-6, 710e3, 100e6),
    0.256: (7.8125e-6, 710e3, 100e6),
}

# s.8 Sekil 14/15'ten okunan RMS gurultu (VDD 3.3 V, 860 SPS)
ADS_GURULTU = {2.048: 26.5e-6, 1.024: 13.5e-6, 0.512: 8.5e-6, 0.256: 8.5e-6}

# ═════════════════════════════════════ pasifler
R_1_4W_AZAMI_V = 200.0            # Yageo MFR: 1/4W azami CALISMA gerilimi
R_STRES_PAYI = 0.60
TL431_V = 2.495

# Vref — TL431 rayindan 10K/22K (ikisi de stokta), tamponlanmis
VREF_RA, VREF_RB = 10e3, 22e3
VREF = TL431_V * VREF_RB / (VREF_RA + VREF_RB)

# GPIO kelepce seri direnci (R26 skop, R33 hizli akim yolu).
# B18/F12 (2026-09-09): 2.7K -> 10K. Bu direnc ariza aninda olu +3V3
# rayina GERI BESLENEN akimi belirliyor (B15/B1). 2.7K'da ray 3.582 V'a
# cikiyordu, ESP32 besleme pini siniri 3.60 V — pay 18 mV.
# 10K menzili SINIRLAMIYOR (kelepce tavani hala ADC'nin 3.1 V'unun
# ustunde) ve ADC tarafindaki uc bedeli de olculu: sizinti ofseti
# 0.5 mV (<1 LSB), oturma 330 ns (ornek araliginin 1/73'u), gurultu
# 1.8 uV. Olcumler: sim3_kelepce.py bolum 2 ve 4.
R_SERI_ESKI = 2.7e3                       # B18 oncesi deger
R_SERI = 10.0e3

# ═════════════════════ B15 DUZELTMESI — ADS giris seri direnci
#
# Tampon cikislari ve VREF, ADS1115'in analog pinlerine BUGUNE KADAR
# DOGRUDAN bagliydi (netlist: /V_TAMPON = U3.6, U3.7, U7.4). Bu yuzden
# tampon doydugu her an ADS'in mutlak maksimumu (VDD+0.3 = 3.6 V)
# asiliyordu — bir ARIZA degil, her menzil disi okumada.
#
# LM358'in cikis tavani icin veri sayfasi yalnizca ALT sinir veriyor
# (TI SLOS068AB 5.7, duz LM358: raydan dusum EN FAZLA 1.5 V, yani
# V_OH >= 3.5 V). UST sinir baglanmamis — en kotu halde cikis rayda.
#
# 1K seri direnc TI'in tasarim hedefine (SLVAEX7A 2.1: ESD diyot akimi
# <= 1 mA) uyuyor ve PGA SABIT (+-1.024) oldugu icin kazanc hatasi da
# sabit: 1k / 2.4 Mohm = %0.042, kalibrasyonla siliniyor.
ADS_SERI_R = 1.0e3

# ADS yolu ortusme suzgeci (Nyquist 430 Hz)
#
# HER IKI gerilim kanalinda da var: NORMAL'de R7, HV'de R17 — ikisi de 22K.
#   NORMAL: Thevenin 6.60 kohm, tek basina fc 241 Hz -> yeterince asagi degil.
#   HV    : Thevenin 8.19 kohm, tek basina fc 194 Hz -> 860 Hz'te -13.1 dB,
#           20 dB kuralini GECMEZ.
# ⚠ 2026-09-09 (B16): buradaki eski not "RC_R yalnizca NORMAL kanal" diyor,
#   "HV Thevenin 21.96 kohm, oraya seri direnc EKLENMIYOR" diye devam
#   ediyordu. O not 2.2M'lik ESKI HV bolucusune aitti; 6x820K/8.2K'ya
#   gecilince Thevenin 8.19 kohm'a dustu ve R17 semaya EKLENDI
#   (sema3-uret.py BLOK 3). tasarim3.py ve sim3_giris.py zaten RC_R'yi
#   HER IKI kanala uyguluyordu — yani not koda gore GERIDE kalmisti.
#
# 🔴 SONUC (B16'nin bulgusu): iki gerilim kanalinin zaman sabiti ESIT DEGIL.
#   NORMAL 6.596k + 22k = 28.596 kohm -> 2.860 ms -> 55.66 Hz
#   HV     8.186k + 22k = 30.186 kohm -> 3.019 ms -> 52.73 Hz
#   Aradaki fark %5.6. Tek bir C18 ikisine birden TAM eslesemez;
#   sim3_ortusme.py bolum 2 bunu iki menzil icin ayri ayri olcuyor.
RC_R = 22e3          # R7 (NORMAL) ve R17 (HV) — ikisi de
RC_C = 100e-9        # C2 (NORMAL) ve C3 (HV) — ikisi de

# ESP yolu Sallen-Key (Nyquist 20.83 kHz)
SK_R = 6.8e3
SK_C1 = 2e-9                      # 2 x 1nF paralel
SK_C2 = 1e-9
SK_F0 = 1 / (2 * math.pi * SK_R * math.sqrt(SK_C1 * SK_C2))
SK_Q = 0.5 * math.sqrt(SK_C1 / SK_C2)

# ESP32-S3 ADC
ESP_TOPLAM_SPS = 83333
ESP_KANAL_SAYISI = 2
ESP_KANAL_SPS = ESP_TOPLAM_SPS / ESP_KANAL_SAYISI
ESP_NYQUIST = ESP_KANAL_SPS / 2

# Lagrange yarim-ornek hizalayici
LAGRANGE = [-1 / 16, 9 / 16, 9 / 16, -1 / 16]

# ═════════════════════════════════════ op-amp adaylari
#
# LM358'in cikis tavani asagidaki B15 bolumunde de kullanildigi icin
# BURADA tanimlaniyor (OPAMPLAR tablosu ona bagli).
#
# 🔴 VERI SAYFASI BU SAYIYI TEK YONLU BAGLIYOR — bu, B15'in en ince
#    bulgusu. TI SLOS068AB 5.7 (DUZ LM358/LM358A tablosu — 5.5 ve 5.6
#    LM358B/LM358BA icindir): "Voltage output swing from rail,
#    positive rail", kosul V_S = 5 V, R_L >= 2 kohm, T_A = 25 C:
#    yalnizca bir MAKSIMUM verilmis (1.5 V). MIN ve TYP YOK.
#    ⚠ Bir ara kullanilan "1.35 tipik / 1.42 maks" degerleri DUZ LM358'e
#      AIT DEGIL — onlar SLOS068AB 5.5'in basligindaki LM358B/LM358BA
#      tablosundan. Kullanicinin stokundaki parca duz LM358.
#
#    Bunun anlami: cikis rayin EN AZ 1.5 V altina inebilir diye
#    GARANTI var (V_OH >= 3.5 V), ama rayin NE KADAR YAKININA
#    cikabilecegine dair HICBIR GARANTI YOK. ADS'in gordugu gerilim
#    icin belirleyici olan tam da bu ust sinir.
#
#    Ustelik ADS'in giris empedansi ~2.4 Mohm, yani tampon veri
#    sayfasinin test kosulundan (2 kohm) 1200 kat daha HAFIF yuklu —
#    yuk azaldikca cikis raya YAKLASIR. Yani en kotu hal ray'in kendisi.
#
#    B15 bu yuzden korumayi V_OH = BESLEME RAYI varsayimiyla boyutluyor.
LM358_VOH_DUSUM = 1.5                     # GARANTILI en buyuk dusum
                                          # (V_OH >= 3.5 V @ 5 V, R_L>=2k)
LM358_VOH_DUSUM_MAKUL = 0.9               # hafif yukte gozlenen tipik
                                          # davranis (spek DEGIL, muhendislik
                                          # kestirimi — cikis kati Darlington
                                          # PNP oldugu icin raya bu kadar
                                          # yaklasabiliyor)
LM358_VOH_DUSUM_EN_KOTU = 0.0             # UST sinir spek DISI -> en kotu
                                          # halde cikis rayin kendisinde
#
# KULLANICI KISITI (2026-09-08): "yuzey montajda zorlaniyorum" ->
# yalnizca DELIKLI (THT) govdeler degerlendirilir.
#   ad,  Vos maks, drift V/C, Ib, GBW, besleme, cikis tavani, govde, stok
OPAMPLAR = [
    ("TL072",    10.0e-3, 18e-6, 200e-12, 3.0e6, "+-12 V",
     10.0,  "DIP-8",  "yolda 4"),
    # ⚠ B15 DUZELTMESI: cikis tavani 4.3 V DEGIL. TI SLOS068AB 5.7,
    #   duz LM358, V_S = 5 V / R_L >= 2 kohm / 25 C: raydan dusum EN FAZLA
    #   1.5 V -> tavan EN AZ 3.50 V. UST sinir veri sayfasinda YOK.
    #   4.3 V hicbir veri sayfasi satirina dayanmiyordu.
    ("LM358",     7.0e-3,  7e-6,  45e-9,  1.0e6, "+5 V",
     5.0 - LM358_VOH_DUSUM,   "DIP-8",  "STOKTA 8"),
    ("MCP6002",   4.5e-3,  2e-6,   1e-12, 1.0e6, "3.3 V RRIO",
     3.3,   "DIP-8",  "alinacak"),
    ("MCP6004",   4.5e-3,  2e-6,   1e-12, 1.0e6, "3.3 V RRIO",
     3.3,   "DIP-14", "alinacak"),
]

# Kelepce diyotlari — hepsi DELIKLI govde secenegiyle
#   ad, Vf@10mA, kacak@2V/25C, govde, stok
DIYOTLAR = [
    ("1N4148", 0.75, 5e-9,    "DO-35 eksenel", "stokta 8"),
    ("SR5100", 0.55, 50e-6,   "DO-201 eksenel", "stokta 10"),
    ("BAT85",  0.40, 0.2e-6,  "DO-34 eksenel", "alinacak"),
    ("1N5711", 0.41, 0.2e-6,  "DO-35 eksenel", "alinacak"),
]
# BAT85 kaynak: Nexperia veri sayfasi, Tablo 7 + Sekil 2
#   Vf 400 mV maks @ 10 mA · IR 2 uA maks @ 25 V · Sekil 2: ~2 V'ta 25 C'de
#   tipik ~200 nA · Cd 10 pF maks @ 1 V (Sekil 3: yuksek VR'de ~3 pF)
#   Govde: DO-34 "hermetically sealed glass package; axial leaded"


def par(*r):
    return 1.0 / sum(1.0 / x for x in r)


def _kanal(kod, ad, rust_adet, rust_bir, ralt, pga):
    rust = rust_adet * rust_bir
    N = (rust + ralt) / ralt
    lsb, zdiff, zcm = PGA_TABLO[pga]
    return {
        "kod": kod, "ad": ad,
        "rust_adet": rust_adet, "rust_bir": rust_bir,
        "rust": rust, "ralt": ralt, "pga": pga,
        "N": N, "lsb": lsb, "zdiff": zdiff, "zcm": zcm,
        # ⚠ MENZIL SIMETRIK DEGIL: fark = (Vin-Vref)/N oldugu icin ADS'in
        # +-pga penceresi girise Vref kadar YUKARI kaymis bir aralik verir.
        # AVR testi (B4) bunu yakaladi: NORMAL kanal 2x100K/6.8K ile
        # -29.43 V'ta kirpiyordu ama tasarim "+-31.14 V" diyordu.
        "fs": pga * N,                       # tek yonun genligi (ham)
        "fs_ust": pga * N + VREF,            # gercek ust sinir
        "fs_alt": -pga * N + VREF,           # gercek alt sinir
        "fs_sim": pga * N - VREF,            # GARANTI simetrik menzil
        "adim": lsb * N,
        "thev": par(rust, ralt),
        "giris_z": rust + ralt,
        "r_gerilim": pga * N * (rust_bir / (rust + ralt)),
        "r_guc": (pga * N * (rust_bir / (rust + ralt))) ** 2 / rust_bir,
        "cm_alt": VREF - pga,
        "cm_ust": VREF + pga,
    }


KANALLAR = [
    # NORMAL: 220K tek direnc (ilk surumde 2x100K idi -> N=30.41, simetrik
    # menzil yalnizca +-29.43 V cikiyordu; B4 yakaladi).
    _kanal("normal", "NORMAL   +-32 V",  1, 220e3,  6.8e3, 1.024),
    # 2026-09-09: tedarikcinin METAL FILM hatti 1K..820K arasi — MOhm
    # degeri HIC YOK. (Bir ara "2.2M var" denmisti; o karbon film.
    # Karbon film bu bolucude %4.10 hata yapar, bolum 11'de olculuyor.)
    # 6x820K / 8.2K, N'yi TAM 601.0'da tutuyor: 6*820k/8.2k = 600.
    # Menzil, adim ve firmware sabiti (ORAN_YUKSEK) hic degismiyor.
    # Bu ayni zamanda 1M'den de IYI: Thevenin 9.98k -> 8.19k dustu.
    _kanal("hv",     "YUKSEK  +-613 V",  6, 820e3, 8.2e3, 1.024),
]

# Asama 2'nin (tamponsuz, tek yonlu) bolucusu — kiyas icin
A2_THEVENIN = 6.37e3
A2_PGA_ARALIK = (2.048, 1.024, 0.512, 0.256)


# ═══════════════════════════════════════════════════════════════════════════
#  B15 — ARIZA VE ZORLAMA SIMULASYONU icin MUTLAK SINIRLAR
# ═══════════════════════════════════════════════════════════════════════════
#
# Buradaki her sayi bir veri sayfasindan geliyor ve KAYNAGI yazili.
# `sim3_ariza.py` (B15) yalnizca bu tablodan besleniyor — hicbir sinir
# betigin icine elle yazilmiyor.
#
# ⚠ CALISMA sinirlarindan farkli. Calisma sinirinin asilmasi olcumu
#   BOZAR; mutlak sinirin asilmasi parcayi OLDURUR. B15 ikisini ayri
#   raporluyor.

# ── ADS1115 · TI SBAS444E (guncel revizyon), "Absolute Maximum Ratings"
ADS_MUTLAK_GIRIS_ALT = -0.3               # GND - 0.3 V
ADS_MUTLAK_GIRIS_UST = VDD + 0.3          # VDD + 0.3 V = 3.6 V
# ADS_GIRIS_AKIM_MAKS yukarida (10 mA) — "Input current, continuous".
# ⚠ Eski SBAS444B (2009) ayrica "100 mA momentary" satiri tasiyordu;
#   TI bunu SBAS444D'de (Ocak 2018) KALDIRDI. Adafruit'in sitesinde hala
#   eski kopya duruyor — hobi dunyasinda dolasan 100 mA rakami GERI
#   CEKILMIS bir spektir, ona guvenilmez.
# TI'in kendi TASARIM HEDEFI mutlak sinirdan cok daha siki:
ADS_TASARIM_AKIM_HEDEFI = 1e-3            # SLVAEX7A 2.1: "keep under 1 mA"
ADS_TASARIM_AKIM_TAVANI = 2e-3            # SBAA227 3.1: abs max'in %20'si
ADS_ESD_VF = 0.5                          # TI'in verdigi tek sayi (~500 mV)

# ── ESP32-S3 · Espressif ESP32-S3 Datasheet + resmi FAQ
#    ⚠ Veri sayfasinin mutlak maksimum tablosunda GPIO icin gerilim ya da
#      akim siniri YOK. Tablodaki 0.3..3.6 V satiri GUC pinlerine ait.
#      Tek resmi acik ifade FAQ'ta: "The voltage tolerance of GPIO is 3.6 V."
ESP_MUTLAK_PIN_ALT = -0.3                 # DC karakteristik V_IL min
ESP_MUTLAK_PIN_UST = 3.6                  # Espressif FAQ: GPIO tolerance
ESP_LATCHUP_AKIM = 200e-3                 # JESD78 akim tetikleme (veri sayfasi)
ESP_LATCHUP_GERILIM = 5.4                 # JESD78 = 1.5 x VDDmax (3.6 V)
ESP_ENJEKSIYON_HEDEFI = 5e-3              # Espressif I_INJ YAYINLAMIYOR.
                                          # ST'nin STM32 icin verdigi
                                          # +-5 mA vekil olarak kullaniliyor.
ESP_BOSTA_AKIM = 40e-3                    # 3V3 rayindan bosta cektigi
                                          # (Wi-Fi kapali). Raya ENJEKTE
                                          # edilen akim bunun altindaysa ray
                                          # YUKSELMEZ — akim yalnizca
                                          # regulatorun akimini oteler.
ESP_ADC_ETKIN_UST = 2.9                   # ATTEN_DB_12'de etkin aralik
                                          # (nominal 3.1 V; ustu "undefined")

# ── LM358 · TI SLOS068AB / onsemi LM358 "Maximum Ratings"
#    KRITIK: giris sinirlari V+ ya gore DEGIL, V- ye gore mutlak.
#    PNP giris kati sayesinde giris beslemenin USTUNE cikabiliyor.
#    TI ve onsemi bu noktada AYNI degerleri veriyor.
LM358_BESLEME_MAKS = 32.0
LM358_GIRIS_MUTLAK_ALT = -0.3             # V- ye gore
LM358_GIRIS_MUTLAK_UST = 32.0             # V- ye gore, BESLEMEDEN BAGIMSIZ
LM358_GIRIS_AKIM_GUVENLI = 1e-3           # V- altina inildiginde parazitik
                                          # jonksiyona akan akim icin
                                          # yaygin uygulama siniri
# ⚠ V_OH DUSUMU TEK YONLU BAGLI: SLOS068AB 5.7 (duz LM358):
#   1.35 V tipik, 1.42 V maksimum. Yani V+ = 5.00 V'ta cikis tavani
#   3.65 V (tipik) — ADS'in mutlak ustu 3.60 V. TAMPON DOYDUGU HER AN
#   ADS SPEK DISINDA. Bu bir ARIZA degil, NORMAL menzil disi davranis.
# LM358_VOH_DUSUM / _EN_KOTU yukarida, OPAMPLAR'dan once tanimli.
LM358_VOL = 0.02
LM358_ISC = 40e-3                         # cikis kisa devre akimi (tipik)
LM358_ISC_MAKS = 60e-3                    # maksimum
# 🔴 BU BIR VERI SAYFASI DEGERI DEGIL, ACIK BIR VARSAYIM.
# LM358'in giris jonksiyonunun TERS KIRILMA gerilimi hicbir veri
# sayfasinda verilmiyor. B15 bunu bir tarama parametresi olarak
# kullaniyor: C1 senaryosu (alt bacak acik) tek bir sayi yerine
# BU DEGER TARANARAK raporlaniyor, cunku sonucu belirleyen tek sey o.
# EN KOTU HAL kirilmanin HIC olmamasidir (dugum girise oturur).
LM358_GIRIS_KIRILMA_VARSAYIMI = 60.0      # V, model parametresi (BV)
LM358_KIRILMA_TARAMA = (30.0, 40.0, 60.0, 100.0, 200.0, 1000.0)

LM358_ROUT_DOYMUS = 100.0                 # doymus cikis empedansi; veri
                                          # sayfasindan turetildi: V+ = 30 V'ta
                                          # V_OH 10k'da 27 V, 2k'da 26 V ->
                                          # 1 V / 10.3 mA = 97 ohm
# Ortak-mod GIRIS araligi ust siniri — ureticiler farkli sayi veriyor.
LM358_CM_TAVAN_DUSUM_25C = 1.5            # TI, 25 C
LM358_CM_TAVAN_DUSUM_ONSEMI = 1.7         # onsemi
LM358_CM_TAVAN_DUSUM_TAMSIC = 2.0         # TI, tam sicaklik araligi tavsiyesi
# 🔴 KAPASITIF YUK. ⚠ DUZELTME: "veri sayfasi Application Information
#    bolumu 50 pF veriyor" iddiasi YANLISTI — SLOS068AB'nin uygulama
#    bolumu kapasitif yuk hakkinda hicbir sey demiyor.
#    Belgedeki TEK kapasitif yuk speki elektriksel karakteristik
#    tablolarindaki "C_LOAD Capacitive load drive = 100 pF" ve yalnizca
#    LM358B / LM358BA bolumlerinde (5.5 / 5.6) veriliyor.
#    DUZ LM358 icin YAYINLANMIS bir kapasitif yuk siniri YOK — bu,
#    sayinin buyuklugunden daha kotu bir durum.
LM358_CL_MAKS = 100e-12                   # SLOS068AB 5.5/5.6, LM358B/BA
LM358_CL_OSILASYON_TAHMIN = 1.5e-9        # ~150 ohm Zout_ol ile ilk kutup
LM358_SINK_MIN = 10e-3                    # V_S = 15 V, 25 C
LM358_SINK_MIN_SICAK = 5e-3               # 0..70 C garantili
LM358_SOURCE_MIN = 20e-3
LM358_TJ_MAKS = 125.0
# ⚠ DUZELTME: onceki 120/200 K/W degerleri hicbir veri sayfasinda YOK.
#   TI SLOS068AB 5.4 "Thermal Information": P (PDIP) 8 pin R_thetaJA = 80.9 C/W,
#   D (SOIC) 8 pin R_thetaJA = 124.7 C/W.
LM358_THETA_DIP8 = 80.9                   # C/W, TI SLOS068AB 5.4
LM358_THETA_SOIC8 = 124.7                 # C/W, TI SLOS068AB 5.4
# ⚠ LM2904 "LM358 muadili" diye satiliyor ama TI onu 26 V'a dusuruyor.
#   24 V rayda bu mutlak maksimumun %92'si — yanlis parca alinirsa risk.
LM2904_BESLEME_MAKS_TI = 26.0

# ── TL072 ek sinirlar
TL072_IQ_MAKS = 2.5e-3                    # kesit basina MAKSIMUM (tipik 1.4)
TL072_CM_TAVSIYE_DUSUM = 4.0              # VI >= (V-)+4 V, <= (V+)-4 V
TL072_GIRIS_AKIM_MAKS = 10e-3             # yeni die, raylara kelepceli
TL072_PTOT_ST = 680e-3                    # ST Ptot mutlak maksimum
TL072_ISC_MAKS = 60e-3                    # ST: min 10 / tip 40 / maks 60

# ── TL431 · TI TL431 / onsemi TL431
TL431_VKA_MAKS = 37.0
TL431_IKA_MUTLAK = (-100e-3, 150e-3)
TL431_IKA_TAVSIYE = (1e-3, 100e-3)
TL431_TO92_PD = 0.70
# 🔴 KARARLILIK TUZAGI — TI SLVA482A: katot-anot arasindaki kondansator
#    bu aralikta OSILASYONA yol aciyor. Guvenli: < 1 nF ya da > 22 uF.
TL431_KARARSIZ_C = (10e-9, 2.2e-6)
TL431_GUVENLI_C_ALT = 1e-9
TL431_GUVENLI_C_UST = 22e-6
# Semadaki C1 (TL_RAY <-> GND) B15'ten ONCE 100nF idi — tam kararsiz
# bolgenin ICINDE. B15/F4 ile 1nF yapildi (sema3-uret.py).
C1_ESKI = 100e-9                          # duzeltme oncesi deger
C1_SIMDI = 1e-9                           # envanterde var: C049 1nF x10

# ── Orta nokta (rail splitter) yuk butcesi
# ⚠ DEVIR 5.12.23 "+-12 V rayinda 5.6 mA" diyor ve bunu orta nokta yuku
#   sayiyordu. YANLIS: op-amp bosta akimi V+ -> V- dogrudan akar, orta
#   noktaya HIC degmez. Orta noktayi yukleyen tek sey GND'ye referansli
#   cikis akimlari ve +12'den beslenen GND referansli regulatorler.
ORTA_NOKTA_KELEPCE_KANAL = 3.0e-3         # bir TL072 cikisi +12'ye oturursa
ORTA_NOKTA_KELEPCE_KANAL_NEG = 4.3e-3     # -12'ye oturursa
DEKUPLAJ_ADET = 7                         # C9..C15
DEKUPLAJ_BIR = 100e-9

# ═══════════════════════════════════════════════════════════════════════════
#  B11 — +-12 V RAYI: 7912 ORTA NOKTA REGULATORU
# ═══════════════════════════════════════════════════════════════════════════
#
# TI LM79xx veri sayfasi SNOSBQ7C (JUNE 1999 - REVISED MAY 2013).
# Her sayi orada, ilgili tablo adiyla birlikte.
#
# TOPOLOJI: tek ve YALITILMIS 24 V kaynaktan +-12 V. 7912 orta noktayi
# TANIMLIYOR:
#     7912 GND pini -> 24V+   (= kart +12 V)
#     7912 IN  pini -> 24V-   (= kart -12 V)
#     7912 OUT pini -> kart GND
# Regulator V(OUT) - V(GND pini) = -12 V tutuyor, yani kart GND'si
# 24V+'in TAM 12 V altinda.
#
# NEDEN 7912, 7812 DEGIL: akim yonu. 79xx OUT pininden akim ALIR
# (ceker), 78xx OUT pininden akim VERIR. Bu karttaki orta nokta
# dengesizligi tek yonlu: +12 -> yuk -> GND, yani GND'ye akim GIRIYOR
# ve oradan CEKILMESI gerekiyor. 7812 bu yonu suremez.
LM7912_VO = -12.0
LM7912_VO_TOLERANS = 0.5                  # -11.5 .. -12.5 V @ 25 C
LM7912_VIN_KARAKTERIZE = (-25.0, -15.0)   # elektriksel karakteristik kosulu
LM7912_VIN_MUTLAK = -35.0                 # abs max (Vo = -12/-15 satiri)
LM7912_VIO_DIF_MUTLAK = 30.0              # input-output differential abs max
LM7912_IQ_MAKS = 3e-3                     # 1.5 mA tip / 3 mA maks
LM7912_IOUT_MIN = 5e-3                    # spekler 5 mA <= IOUT icin verilmis
LM7912_IOUT_MAKS = 1.5
LM7912_TJ_MAKS = 125.0
LM7912_THETA_JA = 60.0                    # C/W, TO-220 sogutucusuz
# Kararlilik icin kondansatorler (veri sayfasi Figure 2 notlari):
#   giris  2.2 uF tantal  ya da 25 uF aluminyum elektrolitik
#   cikis  1.0 uF tantal  ya da 25 uF aluminyum elektrolitik
# ⚠ 100 uF'in USTUNDE cikis kapasitesi kullanilirsa giristen cikisa
#   yuksek akimli bir diyot (1N4001) SART — ani giris kisasinda
#   regulatoru korumak icin. 68 uF secilerek bu gereklilik ASILMIYOR.
LM7912_CIN_ELEKTROLITIK = 25e-6
LM7912_COUT_ELEKTROLITIK = 25e-6
LM7912_COUT_DIYOT_ESIGI = 100e-6
# 🔴 MONTAJ TUZAGI: 79xx'te TO-220 TABI GIRIS pinine bagli (78xx'te GND'ye).
#    Bizim baglantimizda IN = -12 V rayi, yani TAB -12 V'ta. Topraklanmis
#    bir sogutucuya vidalanirsa -12 V rayi kisa devre olur.
#    Ayrica pin sirasi 79xx'te GND-IN-OUT, 78xx'te IN-GND-OUT — 7812 gibi
#    baglamak klasik bir yakma sebebi.
LM7912_TAB_PINI = "IN"
LM7912_PIN_SIRASI = ("GND", "IN", "OUT")

# 24 V kaynak — kullanicinin elindeki, yalitimi OLCULMELI (B15/B5)
KAYNAK_24V = 24.0
KAYNAK_24V_TOLERANS = 0.10                # tipik anahtarlamali adaptor +-%10

# Orta noktaya minimum yuku garantileyen bosaltma direnci (+12 -> GND).
# 7912'nin spekleri 5 mA'in ustunde gecerli; normal calismada dengesizlik
# neredeyse SIFIR olabiliyor (+5 V USB'den gelirse 7805 kolu yok).
# 1.2K envanterde YOK; 1K var (R029 1/4W, R030 1/2W, R031 1W — 10'ar adet).
# 1K -> 12 mA, 144 mW. 1/4W govdede %58 olurdu; R030 (1/2W) secilerek
# %29'a iniyor. Bosaltma direnci SUREKLI yuklu, o yuzden pay onemli.
BOSALTMA_R = 1.0e3
BOSALTMA_GOVDE = "1/2W"

# ── TLE2426 — amaca yonelik "The Rail Splitter" (TO-92 govde, delikli uyumlu)
TLE2426_VIN_MAKS = 40.0
TLE2426_IOUT_MUTLAK = 80e-3
TLE2426_SINK_24V = 31e-3
TLE2426_SOURCE_24V = 70e-3
TLE2426_IQ = 195e-6

# ── TL072 · TI TL072 (SLOS080) "Absolute Maximum Ratings"
TL072_BESLEME_MAKS = 18.0                 # +-18 V
TL072_GIRIS_MUTLAK = 15.0                 # +-15 V (besleme +-15 V iken)
TL072_CIKIS_TAVAN = 10.5                  # +-12 V beslemede tipik doyma

# ── BAT85 · Nexperia BAT85 / Vishay BAT85S (degerler ayni)
BAT85_IF_SUREKLI = 200e-3
BAT85_IF_TEKRARLI = 300e-3                # I_FRM, tp < 1 s
BAT85_IF_TEPE = 5.0                       # I_FSM, tp <= 10 ms
BAT85_VR = 30.0
# V_F MAKSIMUM tablosu (T_amb 25 C) — kelepce seviyesini bu belirliyor.
# SPICE modeli TIPIK degerleri veriyor; en kotu durum bu tablodan okunur.
BAT85_VF_MAKS = {0.1e-3: 0.240, 1e-3: 0.320, 10e-3: 0.400,
                 30e-3: 0.500, 100e-3: 0.800}



def bat85_vf_maks(akim: float) -> float:
    """BAT85 V_F MAKSIMUM tablosundan log-ara deger (T_amb 25 C).

    Kelepce seviyesini SPICE'in TIPIK modeli degil bu belirler —
    yukaridaki kural bunu soyluyor ve B18 bolum 4f bunu kullaniyor.
    """
    n = sorted(BAT85_VF_MAKS)
    if akim <= n[0]:
        return BAT85_VF_MAKS[n[0]]
    if akim >= n[-1]:
        return BAT85_VF_MAKS[n[-1]]
    for a, b in zip(n, n[1:]):
        if a <= akim <= b:
            f = (math.log(akim) - math.log(a)) / (math.log(b) - math.log(a))
            return BAT85_VF_MAKS[a] + f * (BAT85_VF_MAKS[b] - BAT85_VF_MAKS[a])
    return BAT85_VF_MAKS[n[-1]]


BAT85_IR_MAKS = 2e-6                      # V_R = 25 V, 25 C
BAT85_IR_TIPIK_3V = 0.1e-6                # V_R ~3 V, 25 C (Vishay egrisi)
BAT85_IR_TIPIK_3V_60C = 1e-6              # ayni nokta, 60 C

# ── 1N4148 · Vishay/onsemi
D1N4148_IF_SUREKLI = 200e-3

# ── Direnc govdeleri: (azami CALISMA gerilimi, nominal guc, Rth K/W)
#    ⚠ DUZELTME (B15 arastirmasi): tasarim3.py'nin "1/4W -> 200 V" sayisi
#      MINYATUR govdeye (Yageo MFR25S, 0204, 3.4 mm) ait. NORMAL 1/4W
#      govde (0207, 6.3 mm) Yageo/KOA'da 250 V, Vishay'de 350 V.
#      Turkiye'de "metal film 1/4W" diye satilanlarin cogu minyatur
#      govde oldugu icin 200 V yine de DOGRU CALISMA VARSAYIMI —
#      ama gerekcesi "1/4W boyle" degil, "alinan parca minyatur".
#      B15 en kotu durumu (200 V) kullaniyor.
#    Rth: Vishay VR25 140 K/W, PR01 135 K/W (0207 govde).
DIRENC_GOVDE = {
    "1/4W": (200.0, 0.25, 140.0),
    "1/2W": (250.0, 0.50, 120.0),
    "1W":   (350.0, 1.00, 135.0),   # Vishay PR01 (0207 govde) — notta adi gecen tek 1W parcasi
    "2W":   (500.0, 2.00,  70.0),
}
DIRENC_ASIRI_YUK_CARPANI = 2.0            # kisa sureli (5 s) overload gerilimi
DIRENC_FILM_TMAKS = 155.0                 # izin verilen film sicakligi
DIRENC_YALITIM_SUREKLI = 75.0             # govde<->cevre SUREKLI yalitim
                                          # (Vishay MRS25). 500 V rakami
                                          # 1 DAKIKALIK testtir.
# IEC 60115-1 4.13 kisa sureli asiri yuk testi 2.5 x RCWV / 5 s = 6.25 x
# nominal GUC. Yani 6.4x guc, standardin nitelendirme testinin tam sinirinda.
DIRENC_KALIFIKASYON_GUC_CARPANI = 6.25
# Amaca yonelik ERIYEN direncler bile acilmak icin 16-24x nominal guc
# istiyor (TT FM1/4, FR25). Siradan metal film 6.4x'te ACILMAZ —
# ~250 C'de suresiz oturur. "Sigorta gibi acilir" varsayimi YANLIS.
DIRENC_ERIME_GUC_CARPANI = 16.0

# ── Semadaki her direncin GERCEKTEN hangi govdede olacagi.
#    envanter.csv'den: 220K -> R037 "1W", 820K -> R038 "2W",
#    10K -> R032 "1/2W" / R033 "1W". Digerleri dokme, 1/4W varsayiliyor.
#    ⚠ tasarim3.py bolum 12 hepsini 1/4W sayiyor; ariza analizinde bu
#    fark 6 kat guc payi demek, o yuzden burada ayri tutuluyor.
DIRENC_GOVDESI = {
    "R1": "1/4W", "R2": "1/2W", "R3": "1/4W",
    "R4": "1W",                                  # 220K envanterde 1W
    "R6": "1/4W", "R7": "1/4W",
    "R10": "2W", "R11": "2W", "R12": "2W", "R13": "2W",
    "R14": "2W", "R15": "2W",                    # 820K envanterde 2W
    "R16": "1/4W", "R17": "1/4W",
    "R18": "1/4W", "R19": "1/4W",
    "R20": "1/4W", "R21": "1/4W", "R22": "1/4W", "R23": "1/4W",
    "R24": "1/4W", "R25": "1/4W", "R26": "1/4W",
    "R27": "1/2W", "R29": "1/2W",                # 10K envanterde 1/2W
    "R28": "1/4W", "R30": "1/4W",
    "R31": "1/4W", "R32": "1/4W", "R33": "1/4W",
    # B15/F1-F2 ile eklenen ADS giris koruma direncleri.
    # Envanterde 1K uc govdede var: R029 1/4W, R030 1/2W, R031 1W (10'ar).
    # R38/R39 ariza aninda GUC harciyor (A7: 32 V ciplak beslemede 0.64 W),
    # o yuzden onlar 1/2W secilmeli — B15 bolum 0 bunu sinar.
    "R34": "1/4W", "R35": "1/4W", "R36": "1/4W",
    "R38": "1/2W", "R39": "1/2W",
    # B11: 7912'nin minimum yukunu garantileyen bosaltma direnci.
    # SUREKLI 144 mW harciyor, o yuzden 1/2W (envanterde R030 x10).
    "R40": "1/2W",
    # B18/F12: +3V3 bosaltma direnci. Surekli 10.9 mW — 1/4W bol bol yeter.
    "R41": "1/4W",
    # ── B21 (pil testi kapi surucusu). Hepsi cok dusuk guclu:
    #   R42 (10K kapi->GND) : kapi 12 V'ta iken 12^2/10k = 14.4 mW
    #   R43 (10K PNP taban)  : ~1.1 mA x 10k = 12 mW, yalnizca yuk ACIKKEN
    #   R44 (4.7K NPN taban) : (3.3-0.7)^2/4.7k = 1.4 mW
    #   R45 (220R kapi seri) : yalnizca anahtarlama aninda, ~2 us
    # Dordu de 1/4W'ta rahat; envanterde 10K R032 (1/2W) x10 ve
    # R033 (1W) x10, 4.7K x15, 220R x10 var.
    "R42": "1/4W", "R43": "1/4W", "R44": "1/4W", "R45": "1/4W",
}

# ═════════════════════ B18 — GPIO KELEPCELERI VE +3V3 GERI BESLEMESI
#
# B15/B1: +-12 V acikken +3V3 kapaliysa (USB cikarilmis, 24 V takili)
# BAT85 kelepceleri olu 3V3 rayini geri besliyor. B18 bunu olcup cozuyor.
R1_TL431 = 220.0                          # R1 — TL431'in +3V3'ten on gerilimi
TL431_BIAS_AKIM = (3.3 - TL431_V) / R1_TL431

# B18/F12 — secilen cozum
KELEPCE_R_SERI_YENI = 10.0e3              # R26/R33 (eskiden R_SERI 2.7K)
BOSALTMA_R_3V3 = 1.0e3                    # R41 YENI: +3V3 -> GND

# ADS akim kanali PGA +-0.256'da kirpiyor; hizli yolun tam olcegi 294.6 mV.
# Hizli yolun kirpma noktasi bunun ALTINA duserse tepe yakalama islevi
# yavas yoldan once doyar — F6'nin reddedilme sebebi bu.
ADS_AKIM_KIRPMA = 0.256

# Kelepce TL431 rayina baglansaydi kullanilabilir tavan. Diyot 'Vf'ten
# cok once yumusak iletime girdigi icin bu deger ray + 0.4 V DEGIL;
# sim3_kelepce.py bolum 2 supurmeyle olcuyor ve bu sabite karsi siniyor.
KELEPCE_TL_TAVAN = 2.510

# ── ESP32-S3 ADC giris tarafi (seri direnci buyutmenin bedeli burada)
# GPIO yuksek seviye giris siniri VDD + 0.3 V (veri sayfasi, Absolute
# Maximum Ratings) — BESLEME pininin sabit 3.6 V'luk siniriyla KARISTIRMA.
ESP_GPIO_VDD_PAYI = 0.3
ESP_PIN_SIZINTI = 50e-9                   # veri sayfasi: pin kacagi maks
ESP_SH_C = 1.0e-12                        # SAR tutma kondansatoru ~1 pF
                                          # (Espressif ESP-FAQ, ADC bolumu)
# Kelepce dugumundeki toplam kapasite: 2 x BAT85 (Cd 10 pF maks @ 1 V,
# Nexperia Tablo 7) + ESP32 pini (~3 pF) + delikli plaket kacagi (~10 pF).
# KOTUMSER taraf secildi: buyuk kapasite = yavas oturma = zor sinav.
KELEPCE_DUGUM_C = 33e-12

# ── Skop kanali bolucusu (BLOK 5): R20 100K / R23 2.7K
#
# B19 (2026-09-09, kullanici karari): kanal CIFT YONLU yapildi.
#   ONCE : R23 6.8K, alt uc GND'de -> 0 .. 45.5 V TEK YONLU
#   SIMDI: R23 2.7K, alt uc VREF'te -> -65.2 .. +45.1 V
# Alt ucun VREF'e baglanmasi, gerilim kanallarinin zaten kullandigi
# cozumun aynisi. Bedeli COZUNURLUK: adim 11.1 -> 26.9 mV.
SKOP_RUST = 100e3
SKOP_RALT_ESKI = 6.8e3                    # B19 oncesi
SKOP_RALT = 2.7e3
SKOP_N = (SKOP_RUST + SKOP_RALT) / SKOP_RALT
SKOP_ALT_UC_VREF = True                   # B19: alt uc GND'de DEGIL
SKOP_TAVAN = 3.1                          # ESP32 ADC'nin nominal ustu
                                          # (kelepce/pay hesaplari icin;
                                          #  MENZIL icin ESP_ADC_ETKIN_UST)

# B19 menzilleri.
#
# 🔴 DONUSUM: bolucunun ALT UCU VREF'te oldugu icin dugum
#       V_dugum = VREF + (V_giris - VREF) * R23/(R20+R23)
#    yani ters cevirince
#       V_giris = VREF + (V_dugum - VREF) * N
#              = V_dugum * N  -  VREF * (N - 1)
#    ⚠ Bastaki +VREF UNUTULMAMALI. Unutulursa 0 V giris -VREF*N okur
#    (B19 bolum 1'deki "0 V" satiri bu hatayi yakaladi).
SKOP_VOLT_OFSET = VREF * (SKOP_N - 1.0)   # V_giris = V_dugum*N - bu
SKOP_MENZIL_EKSI = 0.0 * SKOP_N - SKOP_VOLT_OFSET
SKOP_MENZIL_ARTI = ESP_ADC_ETKIN_UST * SKOP_N - SKOP_VOLT_OFSET

# 🔴 B20 (2026-09-10) — ADIM ile MENZIL ayni sabiti kullaniyordu, oysa
# ikisi FARKLI seyler ve bu, firmware ile bu dosyayi %6.92 ayirmisti:
#   * SKOP_MENZIL_* : girisin KULLANILABILIR ustu -> ESP_ADC_ETKIN_UST
#     (2.9 V; ustunde ESP32 ADC'si dogrusalligini kaybediyor)
#   * SKOP_ADIM     : bir ADC kodunun kac volt ettigi, yani LSB ->
#     kod 4095'in karsilik geldigi NOMINAL TAM OLCEK / 4096
# Adim "etkin ust"e bolununce ne firmware'in yaptigi sey cikiyor ne de
# gercek LSB. Firmware (olcum3.h), arayuz3/app.js ve sahte-kart.js ucu de
# 3.1'i kullaniyordu; ayrisan bu dosyaydi. B19'un "sabit ayrismasi
# denetimi" yalnizca SKOP_ORAN ve VREF'e bakip ADIM'i atlamisti.
#
# ⚠ 3.1 V bir VERI SAYFASI NOMINALI. ESP32 ADC'sinin gercek tam olcegi
#   yongadan yongaya degisiyor ve dogrusal degil — bu sabit TEZGAHTA
#   kalibre edilmeli. sim3_bant.py bolum 6c dort kopyanin AYNI kalmasini
#   sinar, DOGRU olmasini degil.
SKOP_ADIM = SKOP_TAVAN / 4096 * SKOP_N

# ── Sont kanali (BLOK 4)
SONT_KELVIN_R = 100.0                     # R18 / R19

# ═════════════════════ B16 — V/I SUZGEC ESLESTIRMESI
#
# SORUN: wattmetre gucu V x I diye hesapliyor, ama iki kanal ayni sinyali
# FARKLI suzuyordu:
#     gerilim kanali : (Rth + R7) x C2  = 28.6 kohm x 100 nF ->    55.7 Hz
#     akim   kanali  : (R18+R19) x C4   =   200 ohm x 100 nF ->  7957.7 Hz
# 50 Hz'te aradaki faz farki -41.6 derece.
#
# ⚠ INCE NOKTA: DIRENCLI yukte bu fark KENDINI GOTURUYOR, cunku tek
#   kutuplu suzgecte |H|*cos(atan x) = |H|^2 — yani "esitsiz" ve "esit"
#   suzgec ayni guc okumasini veriyor. Hata REAKTIF yukte cikiyor:
#   PF=0.5'te %90, PF=0.26'da %222. Kullanicinin alani SMPS/inverter,
#   yani yuk neredeyse her zaman reaktif.
#
# COZUM: suzmeyi PAYLASILAN dugumden alip ADS'IN KENDI koluna tasimak.
#   C4  100 nF -> 1 nF    (yalnizca RF; kutup 796 kHz'e cikiyor)
#   C18 YENI: ADS akim girisleri arasina, R38/R39'un ARDINDAN
# Boylece:
#   * ADS kolu 59 Hz'te suzuluyor -> gerilim kanaliyla ESLESIYOR
#     (50 Hz'te faz farki 0.44 derece) ve 430 Hz Nyquist'i korunuyor
#   * hizli yol C4'ten KURTULUYOR -> 7.59 kHz yerine 16.53 kHz,
#     yani belgelenen Sallen-Key bandina kavusuyor ve skop kanaliyla
#     esleseiyor (5 kHz'te faz farki 32 derece yerine 0.36 derece)
SONT_C_ESKI = 100e-9                      # B16 oncesi deger
SONT_C = 1e-9                             # C4 — artik yalnizca RF
# C18: stoktan 1uF (C023) + 220nF (C052) + 100nF (C008) paralel.
# Ideal deger (rv*C2/R_eff) 1.300 uF; bu kombinasyon 1.320 uF.
ADS_AKIM_C = 1.0e-6 + 220e-9 + 100e-9
# Ideal deger, iki kanalin zaman sabitini ESITLEYEN degerdir:
#     (Rth + RC_R) * RC_C  =  (R18+R19+R38+R39) * C18
_RV_B16 = (KANALLAR[0]["rust"] * KANALLAR[0]["ralt"]
           / (KANALLAR[0]["rust"] + KANALLAR[0]["ralt"])) + RC_R
_RI_B16 = 2 * SONT_KELVIN_R + 2 * ADS_SERI_R
ADS_AKIM_C_IDEAL = _RV_B16 * RC_C / _RI_B16
SONT_SECENEK = (10.0, 1.0, 0.1, 0.015)    # takilabilen sont degerleri

# 🔴 B20 (2026-09-10) — SONTUN ISIL SINIRI, ADC'NIN DEGIL.
# "±11.5 A" rakami UC dosyada elle yaziliydi (arayuz3/index.html,
# kurulum3-uret.py x2) ve BU DOSYADA YOKTU. Ustelik ADC'nin verdigi
# menzille CELISIYOR: 0.256 V / 0.015 ohm = 17.07 A. 11.5 nereden?
#     I = sqrt(P / R) = sqrt(2 / 0.015) = 11.547 A
# yani 2 W'lik bir sonttan. Sinir ISIL; ADS degil sont belirliyor.
# Menzil = min(ADC siniri, isil sinir).
#
# ⚠ 2 W bir CIKARIM: 11.547 rakamindan geri turetildi (DEVIR 2.3).
#   Sont HENUZ GELMEDI. Parca elde olunca uzerindeki/veri sayfasindaki
#   guc degeri okunup BURASI duzeltilmeli — tezgah listesinde var.
SONT_GUC_W = 2.0                          # cikarim, parca gelince teyit et
SONT_AKIM_ISIL = {r: math.sqrt(SONT_GUC_W / r) for r in SONT_SECENEK}

# ── Hizli akim yolu (BLOK 8)
HIZLI_RG = 10e3                           # R27 / R29
HIZLI_RF = 47e3                           # R28 / R30
HIZLI_G = HIZLI_RF / HIZLI_RG

# ── Sebeke ve izolasyon (D bolumu)
SEBEKE_RMS = 230.0
SEBEKE_TEPE = SEBEKE_RMS * math.sqrt(2)
SEBEKE_HZ = 50.0
SEBEKE_KAYNAK_Z = 0.4                     # tipik ev tesisati kaynak empedansi
RCD_ESIK = 30e-3                          # kacak akim rolesi
RCD_ACMA_S = 0.04                         # 5 x I_dn'de IEC 61008 siniri

# USB kablosu toprak iletkeni — Onderdonk erime akimi hesabi icin
USB_AWG = {"28AWG": 159.8, "26AWG": 254.0, "24AWG": 404.0}   # dairesel mil
USB_OHM_M = {"28AWG": 0.21306, "26AWG": 0.13400, "24AWG": 0.08427}  # 20 C
BAKIR_ERIME_C = 1083.0
ORTAM_C = 40.0                            # kablo ici, kilifin altinda
# Ariza dongusunun toplam direnci: Ze (sebeke kaynak) + USB GND teli +
# PCB izleri + kontaklar. Arastirma 0.3-1.2 ohm araligi veriyor.
ARIZA_DONGU_R = (0.3, 1.2)
MCB_B16_ANI = (48.0, 80.0)                # B egrisi 16 A: 3-5 x In, <= 0.1 s
# 🔴 USB portunda koruma YALNIZCA VBUS hattinda (TPS2041, I_LIM 0.9 A).
#    GND hattinda HICBIR KORUMA YOK.
USB_VBUS_ILIM = 0.9
USB_GND_KORUMA = 0.0

# Tektronix'in PILLE BESLENEN (gercekten yuzen) osiloskoplar icin bile
# koydugu sert sinir. "Karti pille yuzdurelim" plani bu sayiyla sinanmali.
YUZEN_ALET_TOPRAGA_SINIR_RMS = 30.0
YUZEN_ALET_TOPRAGA_SINIR_TEPE = 42.0

# IEC 60664-1 / IPC-2221B mesafeler (615 V DC, kirlilik derecesi 2, FR4 = IIIa)
IPC2221_KACAK_615V = 3.08                 # mm, kaplamasiz dis katman (B2)
# ⚠ DUZELTME: onceki 4.0/8.0 mm degerleri 400 V BASAMAGINA aitti.
#   IEC 60664-1 kacak yolu tablosu (PD2, malzeme grubu IIIa) basamakli:
#     400 V -> 4.0 mm · 500 V -> 5.0 mm · 630 V -> 6.3 mm
#   615 V calisma gerilimi bir UST basamaga (630 V) yuvarlanir.
IEC60664_CREEPAGE_TEMEL = 6.3             # mm, 630 V basamagi, PD2, grup IIIa
IEC60664_CREEPAGE_TAKVIYELI = 12.6        # mm, temelin 2 kati
DELIKLI_ADIM = 2.54                       # mm
# Hava kirilma dayanimi ve eksenel direnc govde boyu — C2 senaryosunda
# "acik kalan direnc uzerinden ark atlar mi" sorusu icin.
HAVA_KIRILMA_V_MM = 3000.0                # 1 atm, kuru hava
DIRENC_GOVDE_BOY_MM = 6.3                 # Yageo MFR-25 / KOA MF1/4 (0207)
# USB Tip-A yuva kontak akim anmasi (Amphenol MUSB, Molex)
USB_KONTAK_ANMA_A = 1.5

# ── +-12 V rayi: 24 V + LM358 orta nokta tamponu (DEVIR 5.12.23)
RAY_24V = 24.0
ORTA_NOKTA_R = 1e3                        # bolucunun her bacagi (onerilen)
# Orta noktadan GND'ye gercekten akan akim (TL072'lerin bosta akimi
# raydan raya akar, orta noktaya DEGMEZ — DEVIR 5.12.23 bunu yanlis
# saymisti; B15 bolum 3'te olculuyor):
ORTA_NOKTA_YUK_7805 = 6.4e-3              # 7805 bosta + analog +5 V yuku
ORTA_NOKTA_YUK_ESP = 250e-3               # ESP32 dusurucu regulatoru +12'den
                                          # beslenirse Wi-Fi tepesinde


# ═════════════════════════════════════ B21 — PIL KAPASITE TESTI (2026-09-10)
#
# Harici bir TAS DIRENC yuk, karttaki bir MOSFET anahtarla kesiliyor.
# MOSFET yaln\u0131zca AC/KAPA yapiyor — dogrusal kipte KULLANILMIYOR, o yuzden
# gucu tas direnc yiyor ve sogutucu gerekmiyor (sinir asagida hesapli).

# ── IRFZ44N · INCHANGE (isc) IRFZ44N urun sartnamesi, sayfa 1-2
#    https://datasheet.octopart.com/IRFZ44N-Inchange-Semiconductor-datasheet-15981338.pdf
#    ⚠ Ikincil kaynak bir uretici (Turkiye'de satilan IRFZ44N genelde bu).
#      Elde parca olunca uzerindeki logo okunup teyit edilmeli.
IRFZ44N_VDSS = 55.0                       # V, drain-source kirilma
IRFZ44N_VGS_MUTLAK = 20.0                 # V, kapi-kaynak surekli abs max
IRFZ44N_VGS_TH = (2.0, 4.0)               # V, esik (Vds=Vgs, Id=0.25 mA)
IRFZ44N_VGS_SPEK = 10.0                   # V, RDS(on)'un OLCULDUGU kosul
IRFZ44N_RDSON = 0.032                     # ohm MAKS @ Vgs=10 V, Id=25 A
IRFZ44N_ID = 49.0                         # A surekli @ Tc=25 C
IRFZ44N_TJ_MAKS = 175.0                   # C
IRFZ44N_RTH_JA = 62.0                     # C/W, TO-220 SOGUTUCUSUZ
IRFZ44N_RTH_JC = 1.5                      # C/W

# 🔴 3.3 V KAPI YETMEZ. Esik 2..4 V ve RDS(on) 10 V'ta olculmus; ESP32'nin
# 3.3 V'u en kotu halde esigin ALTINDA kalir, iyi halde bile MOSFET'i
# dogrusal bolgede birakip isitir. Kapi +12 V rayindan surulyor
# (B11 o rayi zaten karta koydu).
PIL_KAPI_V = 12.0                         # BC557 doyma dususu ihmal
# Kapi surucusu: GPIO -> 2N2222 -> BC557 -> kapi, kapi 10K ile GND'ye cekili.
# ⚠ CEKME YONU KRITIK: ESP32 reset/cokme/WDT halinde GPIO yuksek empedansa
#   doner, kapi GND'ye iner, MOSFET KAPANIR ve pil bosalmayi DURDURUR.
#   Ters kurulum (yukari cekme) tam tersini yapardi.
PIL_KAPI_CEKME_R = 10e3                   # ohm, kapi -> GND (FAILSAFE)
PIL_KAPI_TABAN_R = 4.7e3                  # ohm, GPIO -> 2N2222 tabani
PIL_KAPI_PNP_R = 10e3                     # ohm, 2N2222 kollektoru -> BC557 tabani

# Sogutucusuz calisma siniri: Tj hedefi ORTAM_C uzerinden, projenin
# 7912'de kullandigi 125 C olcutuyle ayni.
PIL_TJ_HEDEFI = 125.0                     # C, sogutucusuz tavan
PIL_AKIM_SOGUTUCUSUZ = ((PIL_TJ_HEDEFI - ORTAM_C) / IRFZ44N_RTH_JA
                        / IRFZ44N_RDSON) ** 0.5     # A

# ── Kayit ve tampon
PIL_KAYIT_HZ = 1.0                        # varsayilan; 0.2 / 1 / 5 secilebilir
PIL_NOKTA_BAYT = 12                       # uint32 ms + float V + float I
# ⚠ Tampon boyutu FIRMWARE'DEN okunuyor (PIL_IC_KAPASITE), elle YAZILMIYOR —
#   iki kopya ayrisirsa sim3_pil.py'nin RAM iddiasi yalan soylerdi.
import re as _re
from pathlib import Path as _P
PIL_IC_KAPASITE = int(_re.search(
    r"#define PIL_IC_KAPASITE (\d+)u",
    (_P(__file__).parent.parent / "kod" / "olcum-karti-a3"
     / "olcum-karti-a3.ino").read_text(encoding="utf-8")).group(1))
PIL_TAMPON_BAYT = PIL_IC_KAPASITE * PIL_NOKTA_BAYT
PIL_TAMPON_S = PIL_IC_KAPASITE / PIL_KAYIT_HZ
ESP_DRAM_TOPLAM = 327680                  # bayt, arduino-cli'nin bildirdigi
ESP_DRAM_KULLANILAN = 51084               # bayt, B6 derlemesinden (guncellenir)

# ── DCIR (ic direnc) darbesi
PIL_DCIR_ARALIK_S = 300.0                 # 5 dakikada bir
PIL_DCIR_DARBE_S = 0.200                  # yuk KAPALI kalma suresi
# ⚠ 665 Sa/s'te ilk ornek 1.5 ms sonra gelir; gercek OHMIK dusus
#   mikrosaniyelerde olur. Yani olculen sey ohmik + bir miktar
#   polarizasyon. MUTLAK DCIR degil, KARSILASTIRILABILIR bir saglik
#   gostergesi olarak raporlanmali.
