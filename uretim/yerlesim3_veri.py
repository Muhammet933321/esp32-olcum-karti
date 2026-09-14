# -*- coding: utf-8 -*-
"""Delikli plaket yerlesimi — VERI (tek kaynak).

Denetim ve cizim `yerlesim3.py`'de. Burada yalnizca KARAR var: hangi parca
hangi kartta, hangi delikte, hangi yonde; kart disi neler; kablolar.

── KOORDINAT ─────────────────────────────────────────────────────────
Delik birimi. (0, 0) PARCA YUZUNDEN bakista sol ust. x saga, y asagi.
Belgede sutun harfle (A, B, ... AA), satir sayiyla (1, 2, ...): (2, 3) = C4.
Lehim yuzu cizimi AYNALI — plaketi cevirince ayni harf ayni delige gelir.

── KART MIMARISI (neden uc parca) ────────────────────────────────────
  A  Ana analog kart  — butun dusuk gerilim devresi, iki ADS, J5.
  B  HV zinciri       — R10..R15 (6 x 820K) AYRI kucuk plakette. Kurulum
     kilavuzu zinciri "muz jakin ustunde havada" kurmayi oneriyor; ayri
     plaket ayni amaci mekanik olarak saglam yapiyor ve 615 V'luk bakiri
     ana kartin HICBIR yerine yaklastirmiyor. B'den A'ya giden tek sinyal
     zincirin alt dugumu (~1.7 V, R15.2).
  GUC YOLU (kart disi, kutuda) — sont RS, J3, J7, Q1. 15 mOhm'da +-11.5 A,
     Q1 sogutucusuz 6.55 A'e kadar: delikli plaketin ince bakiri ve pedleri
     bunu tasimaz. Plakete yalniz Kelvin uclari (S+, S-), TEK yildiz toprak
     teli ve Q1'in kapi teli gelir.
  PANEL (kart disi) — J1, J2, J4 born jaklar (BOM boyle), J6 24 V girisi.
"""
from __future__ import annotations

import tasarim3_sabit as T

# ── plaketler ──────────────────────────────────────────────────────────
# Delik sayilari kullanici tarafindan SAYILDI (2026-09-14): 13x23 = 45x90,
# 10x10 = 32x32 (ana kart SIGMIYOR), 5x5 = 18x18.
KARTLAR = {
    "A": {"ad": "Ana analog kart", "plaket": "13x23 cm (SRF023) plaketten kesilmis 38x38 delik",
          "sutun": 38, "satir": 38},
    "B": {"ad": "HV zinciri", "plaket": "5x5 cm (SRF020)",
          "sutun": 18, "satir": 18},
}
VIDA_KOSE = 2              # her kosede 2x2 delik vida icin bos
VIDA_YARICAP_MM = 3.0      # M3 vida basi + pul (kacak yolu hesabinda iletken)

# ── kacak yolu ─────────────────────────────────────────────────────────
# Ped capi, Tablo F.4 ve esik TEK KAYNAKTAN (tasarim3_sabit) — B15/D2, F9,
# kurulum kilavuzu ve bu plan ayni sayiyi kullanir.
PAD_ETKIN_MM = T.DELIKLI_PAD_ETKIN_MM
KACAK_ESIK_V = T.IEC60664_ESIK_V
IEC_F4 = T.IEC60664_F4_PD2_MG3
# HV zinciri dugumleri, girisden alta (k = 0..6). Takviyeli kural: k<6 ile
# zincir DISI her sey arasi (kurulum kilavuzu F9).
ZINCIR = ["/HV_GIRIS", "Net-(R10-Pad2)", "Net-(R11-Pad2)", "Net-(R12-Pad2)",
          "Net-(R13-Pad2)", "Net-(R14-Pad2)", "Net-(R15-Pad2)"]

# ── fiziksel bacak sirasi ──────────────────────────────────────────────
# On yuz (yazili yuz) SIZE donuk, bacaklar asagi, SOLDAN SAGA.
# ⚠ Yerlesim bu tabloya dayaniyor. Lehimlemeden once multimetrenin diyot
#   kademesiyle dogrula: BJT'de baz iki eklemin ortak ucudur.
BACAK = {
    "TL431": ("REF", "A", "K"),        # TO-92, TI "LP" kilifi
    # Gövdede "2N2222 -331": yaygin TO-92 surumu E-B-C. Semadaki sembol
    # BC547'den (C-B-E) — pin NUMARASIYLA lehimlenirse C ile E yer
    # degistirir ve transistor ters yonde, cok dusuk kazancla YARI calisir.
    "2N2222-331": ("E", "B", "C"),
    "BC557": ("C", "B", "E"),
    "L7912": ("GND", "VI", "VO"),      # 79xx: GND-VI-VO (78xx'ten FARKLI)
}
# ADS1115 modulu baslik sirasi (modulun ustunde yazar — dogrula)
ADS_MODUL = ("VDD", "GND", "SCL", "SDA", "ADDR", "ALERT/RDY",
             "AIN0", "AIN1", "AIN2", "AIN3")

# ── kurulum adimlari ───────────────────────────────────────────────────
# Kilavuzun sirasi + kilavuzda OLMAYAN iki blok (besleme, pil testi).
ADIM_ADLARI = [
    "Besleme: 24 V girisi, sigorta, 7912, ±12 V rayi",
    "Vref: TL431 + U3A tamponu, J5 basligi (+3V3, +5V)",
    "ESP32 + I²C: iki ADS modulu, pull-up'lar",
    "Akim kanali: Kelvin uclari, 100R/1K, ortusme suzgeci",
    "NORMAL gerilim kanali (±32 V)",
    "YUKSEK gerilim kanali: B karti + U4",
    "Osiloskop kanali + Sallen-Key (U5A)",
    "Hizli akim yolu: fark yukselteci U8 + U5B",
    "Pil testi: kapi surucusu Q2/Q3",
]

# ── yerlesim ───────────────────────────────────────────────────────────
# ref: (kart, ayak[:kod], x, y, aci, adim[, TEL icin ag])
YER = {
    # ═══ KART B — HV zinciri (3 sira, yilan) ═══
    # Siralar arasi 3 ve 5 adim: 1-2 arasi en kotu 411 V TEMEL (4.1 mm),
    # 2-3 arasi N2 ile alt dugum 411 V TAKVIYELI (8.2 mm). 4 adimda pay
    # 0.39 mm idi — lehim tepecigi biraz buyuse yetmezdi; 5 adimda 2.9 mm.
    "T_HV":  ("B", "TEL", 3, 7, 180, 5, "/HV_GIRIS"),
    "R10":   ("B", "R4", 4, 7, 0, 5),
    "R11":   ("B", "R4", 9, 7, 0, 5),
    "R12":   ("B", "R4", 13, 10, 180, 5),
    "R13":   ("B", "R4", 8, 10, 180, 5),
    "R14":   ("B", "R4", 4, 15, 0, 5),
    "R15":   ("B", "R4", 9, 15, 0, 5),
    "T_N6":  ("B", "TEL", 14, 15, 0, 5, "Net-(R15-Pad2)"),

    # ═══ KART A ═══
    # sag kenar: ADS modulleri, J5 (ESP32 kablosu sagdan cikar), kiskaclar
    "U7":    ("A", "ADS", 27, 2, 0, 2),
    "U6":    ("A", "ADS", 27, 14, 0, 2),
    "J5":    ("A", "HDR10", 35, 14, 90, 1),
    "C15":   ("A", "C1", 26, 14, 180, 2),
    "R24":   ("A", "R1D", 25, 16, 0, 2),
    "R25":   ("A", "R1D", 25, 17, 0, 2),
    "R41":   ("A", "R4", 29, 25, 0, 1),
    "D1":    ("A", "D3", 36, 14, 90, 6),
    "D2":    ("A", "D3", 36, 18, 90, 6),
    "D3":    ("A", "D3", 37, 15, 90, 7),
    "D4":    ("A", "D3", 37, 19, 90, 7),

    # kart disi teller
    "T_VGIR":   ("A", "TEL", 2, 3, 180, 4, "/V_GIRIS"),
    "T_COM":    ("A", "TEL", 2, 5, 180, 4, "GND"),
    "T_HVALT":  ("A", "TEL", 2, 10, 180, 5, "Net-(R15-Pad2)"),
    "T_SKOP":   ("A", "TEL", 1, 15, 180, 6, "/SKOP_GIRIS"),
    "T_SP":     ("A", "TEL", 2, 24, 180, 3, "/YUK_EKSI"),
    "T_SN":     ("A", "TEL", 2, 26, 180, 3, "GND@kelvin"),
    "T_YILDIZ": ("A", "TEL", 2, 28, 180, 3, "GND"),
    "T_KAPI":   ("A", "TEL", 25, 35, 90, 8, "Net-(Q1-PadG)"),
    "T_24P":    ("A", "TEL", 2, 33, 180, 0, "Net-(J6-Pin_1)"),
    "T_24N":    ("A", "TEL", 2, 35, 180, 0, "-12V"),

    # adim 1 — Vref
    "U3":    ("A", "DIP8", 17, 7, 180, 1),
    "C9":    ("A", "C1", 13, 7, 180, 1),
    "R3":    ("A", "R4", 18, 4, 0, 1),
    "R2":    ("A", "R4", 22, 5, 180, 1),
    "U1":    ("A", "TO92:TL431", 23, 6, 0, 1),
    "C1":    ("A", "C1", 23, 4, 0, 1),
    "R1":    ("A", "R4", 25, 1, 90, 1),

    # adim 4 — normal kanal
    "R4":    ("A", "R4", 3, 3, 0, 4),
    "R7":    ("A", "R4", 8, 3, 0, 4),
    "R6":    ("A", "R4", 7, 4, 90, 4),
    "C2":    ("A", "C1", 13, 4, 180, 4),
    "R34":   ("A", "R4", 22, 8, 0, 4),
    "R36":   ("A", "R4", 22, 12, 0, 4),

    # adim 5 — yuksek gerilim
    "R16":   ("A", "R4", 3, 10, 0, 5),
    "R17":   ("A", "R4", 13, 13, 0, 5),
    "U4":    ("A", "DIP8", 18, 11, 0, 5),
    "C3":    ("A", "C1", 17, 14, 90, 5),
    "C10":   ("A", "C1", 22, 11, 0, 5),
    "R35":   ("A", "R4", 22, 10, 0, 5),

    # adim 6 — skop (U5A)
    "R20":   ("A", "R4", 2, 15, 0, 6),
    "R23":   ("A", "R1D", 6, 14, 270, 6),
    "R22":   ("A", "R4", 7, 15, 0, 6),
    "C5":    ("A", "C1x2", 12, 15, 0, 6),
    "U5":    ("A", "DIP8", 13, 17, 0, 6),
    "R21":   ("A", "R1D", 12, 18, 90, 6),
    "C6":    ("A", "C1", 11, 19, 180, 6),
    "C12":   ("A", "C1", 12, 20, 180, 6),
    "C11":   ("A", "C1", 17, 17, 0, 6),
    "R26":   ("A", "R1D", 14, 16, 0, 6),

    # adim 3 — akim kanali
    "R18":   ("A", "R4", 3, 24, 0, 3),
    "R19":   ("A", "R4", 3, 26, 0, 3),
    "C4":    ("A", "C1", 8, 24, 90, 3),
    "R38":   ("A", "R1D", 26, 18, 90, 3),
    "R39":   ("A", "R1D", 26, 23, 270, 3),
    "C20":   ("A", "C1", 26, 20, 90, 3),
    "C19":   ("A", "C2", 24, 20, 90, 3),
    "C18":   ("A", "C6", 22, 19, 90, 3),

    # adim 7 — hizli akim yolu (U8 + U5B)
    "U8":    ("A", "DIP8", 12, 27, 0, 7),
    "R30":   ("A", "R1D", 11, 28, 270, 7),
    "R27":   ("A", "R4", 7, 29, 0, 7),
    "R29":   ("A", "R4", 6, 28, 0, 7),
    "R28":   ("A", "R4", 7, 30, 0, 7),
    "C14":   ("A", "C1", 12, 31, 90, 7),
    "C13":   ("A", "C1", 15, 26, 270, 7),
    "R31":   ("A", "R4", 12, 26, 270, 7),
    "R32":   ("A", "R4", 13, 22, 0, 7),
    "C8":    ("A", "C1", 17, 20, 90, 7),
    "C7":    ("A", "C1x2", 13, 23, 0, 7),
    "R33":   ("A", "R4", 17, 18, 0, 7),

    # adim 0 — besleme
    "F1":    ("A", "SIG", 4, 34, 0, 0),
    "U9":    ("A", "TO220:L7912", 18, 35, 180, 0),
    "C16":   ("A", "CE", 18, 32, 180, 0),
    "C17":   ("A", "CE", 21, 34, 90, 0),
    "R40":   ("A", "R5", 19, 30, 0, 0),

    # adim 8 — pil testi kapi surucusu
    "Q3":    ("A", "TO92:BC557", 25, 29, 0, 8),
    "Q2":    ("A", "TO92:2N2222-331", 29, 29, 0, 8),
    "R45":   ("A", "R4", 25, 30, 90, 8),
    "R42":   ("A", "R4", 26, 34, 0, 8),
    "R43":   ("A", "R4", 31, 31, 180, 8),
    "R44":   ("A", "R4", 35, 28, 180, 8),
}

# ── kart disi ──────────────────────────────────────────────────────────
# ref: (grup, adim)   grup: "panel" | "guc"
KART_DISI = {
    "J6": ("panel", 0),
    "J1": ("panel", 4),
    "J2": ("panel", 5),
    "J4": ("panel", 6),
    "J3": ("guc", 3),
    "RS": ("guc", 3),
    "J7": ("guc", 8),
    "Q1": ("guc", 8),
}

# (uc1, uc2, tur, adim, not)
#   uc: "A:<TEL>" / "B:<TEL>" (lehim noktasi) · "X:<REF.PIN>" (kart disi pin)
#   tur: yuk (yuk akimi) · kelvin · yildiz · sinyal · hv · besleme · panel
KABLOLAR = [
    ("X:J6.1", "A:T_24P", "besleme", 0, "24 V arti — XT30 (anahtarli)"),
    ("X:J6.2", "A:T_24N", "besleme", 0, "24 V eksi = -12 V rayi"),
    # guc yolu
    ("X:J3.1", "X:RS.1", "yuk", 3, "yuk donusu -> sont ust bacagi"),
    ("X:RS.2", "X:J3.2", "yuk", 3, "sont alt bacagi -> kaynak eksisi"),
    ("X:RS.1", "A:T_SP", "kelvin", 3,
     "S+ : sont BACAGINA, sikistirma izinin ustunden — klemensten degil"),
    ("X:RS.2", "A:T_SN", "kelvin", 3, "S- : ayni sekilde; S+ ile BURULU cift"),
    ("X:RS.2", "A:T_YILDIZ", "yildiz", 3,
     "kart topraginin guc yoluna TEK baglantisi — S- ile AYNI noktaya, sont "
     "bacagina (klemens vidasina DEGIL: vida-bacak temas direnci COM'u S-'den "
     "I x R kadar kaydirir)"),
    ("X:Q1.S", "X:RS.1", "yuk", 8, "Q1 kaynagi -> sont ust bacagi"),
    ("X:J7.1", "X:Q1.D", "yuk", 8, "pil testi yuku -> Q1 savagi"),
    ("X:J7.2", "X:RS.2", "yuk", 8, "pil eksisi -> sont alt bacagi"),
    ("X:Q1.G", "A:T_KAPI", "sinyal", 8, "kapi teli"),
    # panel
    ("X:J1.1", "A:T_VGIR", "sinyal", 4, "V girisi"),
    ("X:J1.2", "A:T_COM", "sinyal", 4, "COM jak -> kart GND"),
    ("X:J2.2", "X:J1.2", "panel", 5, "HV COM = ortak COM jaki"),
    ("X:J4.2", "X:J1.2", "panel", 6, "skop COM = ortak COM jaki"),
    ("X:J2.1", "B:T_HV", "hv", 5, "HV jak -> B karti. 600 V silikon test kablosu"),
    ("B:T_N6", "A:T_HVALT", "sinyal", 5,
     "zincir alt dugumu (~1.7 V, Thevenin 8.2K). KISA tut (<10 cm), HV "
     "kablosundan ve 24 V hattindan uzak; B kartini A'nin yanina monte et"),
    ("X:J4.1", "A:T_SKOP", "sinyal", 6, "skop girisi"),
]

# ── kart disi tel lehim noktalarinin belgede gorunen adi ───────────────
TEL_ETIKET = {
    "T_HV": "HV jak", "T_N6": "→ A:HV alt",
    "T_VGIR": "V girişi (J1)", "T_COM": "COM jak", "T_HVALT": "HV alt (B'den)",
    "T_SKOP": "Skop jak (J4)", "T_SP": "S+ (şönt üst)", "T_SN": "S− (şönt alt)",
    "T_YILDIZ": "GND yıldız (şönt alt klemens)", "T_KAPI": "Q1 kapı",
    "T_24P": "24 V +", "T_24N": "24 V −",
}

# ── yol uretici ipuclari (DENETIM bunlari kullanmaz) ───────────────────
# Kelvin S- kartta GND bakirina DEGMEMELI: yol uretici onu ayri ag sayar.
KELVIN_AYRI = {"R19.1": "GND@kelvin", "T_SN.1": "GND@kelvin"}
GUC_AGLARI = {"GND", "+3V3", "+5V", "+12V", "-12V", "/VREF"}

# ── denetim kurallari ──────────────────────────────────────────────────
# Kelvin: bu pin kartta YALNIZ bu lehim noktasiyla bagli olmali
KELVIN = [("R18.1", "T_SP.1"), ("R19.1", "T_SN.1")]
YILDIZ_ORNEK_PIN = "U6.3"          # kart toprak adasini tanimlayan pin

# (kondansator pini, entegre pini, en cok delik, neden)
YAKINLIK = [
    ("C9.1", "U3.8", 3, "U3 +5V ayirma"),
    ("C10.1", "U4.8", 3, "U4 +5V ayirma"),
    ("C11.1", "U5.8", 3, "U5 +12V ayirma"),
    ("C12.1", "U5.4", 3, "U5 -12V ayirma"),
    ("C13.1", "U8.8", 3, "U8 +12V ayirma"),
    ("C14.1", "U8.4", 3, "U8 -12V ayirma"),
    ("C15.1", "U6.8", 3, "ADS rayi ayirma"),
    ("C20.1", "U6.4", 4, "B16 ortusme suzgeci ADS pinine yakin"),
    ("C20.2", "U6.5", 4, "B16 ortusme suzgeci ADS pinine yakin"),
    ("C19.1", "U6.4", 6, "B16 ortusme suzgeci"),
    ("C19.2", "U6.5", 6, "B16 ortusme suzgeci"),
    ("C18.1", "U6.4", 10, "B16 ortusme suzgeci (film, 15 mm)"),
    ("C18.2", "U6.5", 10, "B16 ortusme suzgeci (film, 15 mm)"),
    ("C17.1", "U9.1", 6, "7912 cikis kondansatoru"),
    ("C16.2", "U9.2", 6, "7912 giris kondansatoru"),
]
