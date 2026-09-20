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
# `kaynak`: plaketin kesilmeden onceki delik sayisi (sutun, satir) — kesim
# talimati bundan TURETILIYOR (hangi kenar kesilecek).
# A 2026-09-15'te 38x38 -> 45x45 (kullanici): plaketin kisa kenari zaten 45
# delik, tek kesim yetiyor; uc kenar fabrika kenari. Plan sol ust (A1)
# koseye bagli kaldigi icin delik adlari DEGISMEDI, fazlasi sagda ve altta
# bos. Denetim 38/40/45'te ayni (47/47, A'da en dar pay +4.78 mm).
# `cizgi`: plaketin uzerindeki boydan boya cizgilerin araligi (kullanicinin
# 13x23 plaketinde her 5 delikte bir; 2026-09-15). Cizim ayni yere ciziyor;
# B plaketinde cizgi olup olmadigi ve nereden basladigi DOGRULANMADI.
KARTLAR = {
    "A": {"ad": "Ana analog kart", "plaket": "13x23 cm (SRF023) plaketten kesilmis 45x45 delik",
          "sutun": 45, "satir": 45, "kaynak": (45, 90), "cizgi": 5},
    "B": {"ad": "HV zinciri", "plaket": "5x5 cm (SRF020)",
          "sutun": 18, "satir": 18, "kaynak": (18, 18), "cizgi": 5},
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

# Alt adim (LEGO) SINIRLARI — denetimin olcutu. Uretici (`yerlesim3_adim`)
# kendi grup buyukluklerini ayri tutuyor; biri kayarsa denetim kirmizi.
ALT_ADIM_SINIR = {"parca": 4, "iz": 6, "tel": 4, "kablo": 4}

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
# Kart disi parcalar icin belgeye giren aciklama — kullanici 3.7'de "buraya
# ne gelecek, parca var mi" diye sordu (2026-09-17): kablo alt adiminda
# plakete parca takilmadigi belgede yazmiyordu.
KART_DISI_NOTU = {
    "RS": "15 mΩ Type-C şönt (R044): U biçimli kalın tel, iki bacak, bacaklarda sıkıştırma "
          "izi. Kutuda durur, plakete GİRMEZ. Kelvin telleri bacaklara, sıkıştırma izinin "
          "ÜST tarafına (gövdeye yakın) lehimlenir; 'RS.2' saydığın bacağa S−, yıldız GND "
          "ve J3.2 gider — tutarlı ol.",
    "J3": "YÜK born jak çifti (büyük boy, siyah ×2, panel): J3.1 → yük eksisi, J3.2 → kaynak "
          "eksisi. Jakların iç ucundan şönt bacaklarına kısa kalın kablo + halka pabuç; akım "
          "J3.1 → şönt → J3.2 yolunu izler. (Bariyer klemens panele vidalanamıyordu — PCB tipi.)",
    "J6": "24 V girişi: XT30 (CON058). Kart tarafı ERKEK uç (pimli), güç kaynağı "
          "tarafı DİŞİ uç — gerilim taşıyan taraf kapalı soketli olsun. Kablo yalıtımlı, "
          "kırmızı = +, siyah = −.",
    "J1": "V girişi born jak çifti (panel): kırmızı = V girişi, siyah = COM (kart GND).",
    "J2": "HV girişi born jakı (panel): AYRI ve işaretli; COM, J1'in COM'uyla ortak.",
    "J4": "Skop girişi born jakı (panel); COM ortak.",
    "J7": "PİL born jak çifti (büyük boy, mavi ×2, panel): J7.1 → yük direnci, J7.2 → pil "
          "eksisi; J3'ten AYRI — karıştırılırsa kesme çalışmaz.",
    "Q1": "IRFZ44N (Q006), kutuda: kaynağı şönt üst bacağına, savağı J7.1'e, kapısı "
          "karta tek telle (T_KAPI). Soğutucusuz 6.55 A'e kadar.",
}

# (uc1, uc2, tur, adim, not)
#   uc: "A:<TEL>" / "B:<TEL>" (lehim noktasi) · "X:<REF.PIN>" (kart disi pin)
#   tur: yuk (yuk akimi) · kelvin · yildiz · sinyal · hv · besleme · panel
KABLOLAR = [
    ("X:J6.1", "A:T_24P", "besleme", 0,
     "24 V arti — XT30 (kodlu: ters takilamaz; acma-kapama anahtari DEGIL)"),
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
    # 2026-09-17 (4.7): kullanici sordu "bu ikisini de burayim mi?". J1 +-32 V,
    # kanal girisi yuksek empedansli (R4+R6 = 227K) -> ikisini burmak dongu
    # alanini kucultur, zarari yok. Kelvin cifti gibi ZORUNLU degil.
    ("X:J1.1", "A:T_VGIR", "sinyal", 4, "V girisi (KIRMIZI uc). COM teliyle burulabilir"),
    ("X:J1.2", "A:T_COM", "sinyal", 4, "COM jak -> kart GND (SIYAH uc)"),
    # 2026-09-20 (B50g): J2.2 ve J4.2 netlistte ayri pin ama panelde TEK COM
    # jaki var — fiziksel kablo yok. 'sanal' turu: kutu plani bunlari kablo
    # listesine koymaz (kullanici var olmayan tellere ne yapacagini soruyordu).
    ("X:J2.2", "X:J1.2", "sanal", 5, "HV COM = ortak COM jaki (ayni fiziksel jak, tel yok)"),
    ("X:J4.2", "X:J1.2", "sanal", 6, "skop COM = ortak COM jaki (ayni fiziksel jak, tel yok)"),
    ("X:J2.1", "B:T_HV", "hv", 5, "HV jak -> B karti. 600 V silikon test kablosu"),
    ("B:T_N6", "A:T_HVALT", "sinyal", 5,
     "zincir alt dugumu (~1.7 V, Thevenin 8.2K). KISA tut (<10 cm), HV "
     "kablosundan ve 24 V hattindan uzak; B kartini A'nin yanina monte et"),
    ("X:J4.1", "A:T_SKOP", "sinyal", 6, "skop girisi"),
]

# ── direnc TURU ve GUCU ─────────────────────────────────────────────────
# Kullanici sordu (2026-09-15): "hangi direnc metal film, kac watt?"
# GUC ayak izinden gelir: R4/R1D = 1/4 W, R5 = 1/2 W. tasarim3 §12: en
# yuksek yuk 1/4 W'in %15'i (R20), en yuksek gerilim 200 V'un %51'i
# (820K, 102 V) -> tek govde 1/4 W her yerde yeter; R40 144 mW -> 1/2 W.
# TUR (tasarim3 §11): bolme ORANINI KURAN direncler metal film %1 olmak
# ZORUNDA — karbon filmin gerilim katsayisi ve 1000 saatlik %1-3
# suruklenmesi kalibrasyonla silinmez. Denetim (bolum 10) bu kumeyi
# NETLIST TOPOLOJISINDEN yeniden kurup buradaki listeyle karsilastirir:
# giris agina/zincire dokunan direnc (bolucu ust), VREF ile bolucu
# dugumu arasindaki direnc (alt bacak), iki girisinde de >=2 direnc
# olan op-amp'in direncleri (fark yukselteci).
DIRENC_TURU = {
    "zorunlu": {"R4", "R6", "R10", "R11", "R12", "R13", "R14", "R15", "R16",
                "R20", "R23", "R27", "R28", "R29", "R30"},
    # oran kurmuyor ama kararliligi olcume giriyor — stokta metal film
    # zaten var (R059/R060/R062), kullan; karbon da CALISIR
    "onerilir": {"R2", "R3", "R7", "R17", "R21", "R22", "R31", "R32"},
}
DIRENC_TURU_AD = {
    "zorunlu": "metal film %1 ZORUNLU",
    "onerilir": "metal film önerilir (standart da çalışır)",
    "serbest": "standart (karbon) olur",
}
# Her direncin gorevi — belge icin. Denetim: her R eksiksiz.
DIRENC_GOREV = {
    "R1": "TL431 ön gerilim direnci", "R2": "Vref bölücü üst — sıfır noktasının kararlılığı",
    "R3": "Vref bölücü alt — sıfır noktasının kararlılığı",
    "R4": "NORMAL kanal bölücü üst (oran)", "R6": "NORMAL kanal bölücü alt (oran)",
    "R7": "NORMAL kanal RC süzgeci — HV kanalıyla (R17) eşleşmeli",
    **{f"R1{i}": "HV zinciri (oran) — 615 V'u 6'ya bölüyor" for i in range(0, 6)},
    "R16": "HV bölücü alt bacak (oran)",
    "R17": "HV kanal RC süzgeci — NORMAL kanalla (R7) eşleşmeli",
    "R18": "şönt S+ Kelvin ucu RC direnci", "R19": "şönt S− Kelvin ucu RC direnci",
    "R20": "skop bölücü üst (oran)", "R21": "Sallen-Key süzgeç (f0/Q)",
    "R22": "Sallen-Key süzgeç (f0/Q)", "R23": "skop bölücü alt (oran)",
    "R24": "I²C SCL pull-up", "R25": "I²C SDA pull-up",
    "R26": "skop kelepçe seri direnci (ESP32 girişi koruma)",
    "R27": "fark yükselteci giriş (oran: kazanç)", "R28": "fark yükselteci geri besleme (oran: kazanç)",
    "R29": "fark yükselteci giriş (oran: kazanç)", "R30": "fark yükselteci geri besleme (oran: kazanç)",
    "R31": "Sallen-Key süzgeç (f0/Q)", "R32": "Sallen-Key süzgeç (f0/Q)",
    "R33": "hızlı akım kelepçe seri direnci (ESP32 girişi koruma)",
    "R34": "ADS giriş koruma seri direnci (V)", "R35": "ADS giriş koruma seri direnci (HV)",
    "R36": "ADS giriş koruma seri direnci (VREF)",
    "R38": "ADS giriş koruma seri direnci (şönt +)", "R39": "ADS giriş koruma seri direnci (şönt −)",
    "R40": "7912 asgari yükü (12 mA, 144 mW → 1/2 W)", "R41": "+3V3 boşaltma direnci",
    "R42": "Q1 kapı pull-down (failsafe)", "R43": "kapı sürücü Q2→Q3 baz direnci",
    "R44": "kapı sürücü Q2 baz direnci (ESP32'den)", "R45": "Q1 kapı seri direnci",
}

# ── kondansator TIPI ─────────────────────────────────────────────────
# Kullanici sordu (2026-09-16, adim 1.3): "multilayer mi, mercimek mi?
# Elektrolitikse belirt." Stokta iki seramik var: DISK (mercimek —
# yassi turuncu disk, C049 1nF) ve MULTILAYER (yumru bicimli acik sari,
# C051/C008 100nF, C052 220nF). Ayrim gorevden geliyor (B16 bolum 4:
# suzgec kondansatorlerinde TOLERANS baskin artik, ayirmada tip fark
# etmez). Denetim: her C tek tipte; tip ayak iziyle tutarli (CE ->
# elektrolitik, C6 -> film, C1/C2/C1x2 -> seramik); kanal RC suzgec
# kondansatorleri (op-amp giris agi + VREF) AYNI tip ve multilayer.
KOND_TIPI = {
    "seramik disk (mercimek)": {"C1", "C4", "C5", "C6", "C7", "C8"},
    "multilayer seramik": {"C2", "C3", "C9", "C10", "C11", "C12", "C13", "C14",
                           "C15", "C19", "C20"},
    "film (polyester)": {"C18"},
    "elektrolitik (KUTUPLU)": {"C16", "C17"},
}
# tip -> ayak izleri (denetim) ve envanter etiket anahtari (belge, stok)
KOND_TIPI_AYAK = {
    "seramik disk (mercimek)": {"C1", "C2", "C1x2"},
    "multilayer seramik": {"C1", "C2", "C1x2"},
    "film (polyester)": {"C6"},
    "elektrolitik (KUTUPLU)": {"CE"},
}
KOND_TIPI_ETIKET = {
    "seramik disk (mercimek)": "mercimek",
    "multilayer seramik": "multilayer",
    "film (polyester)": "polyester",
    "elektrolitik (KUTUPLU)": "elektrolitik",
}
KOND_GOREV = {
    "C1": "TL431 kararlılık kondansatörü (B15: 100nF osilasyon yapıyordu → 1nF); tip fark etmez",
    "C2": "NORMAL kanal RC süzgeci — C3 ile AYNI tip; toleransı V/I eşleşmesine giriyor (B16)",
    "C3": "HV kanal RC süzgeci — C2 ile AYNI tip; toleransı V/I eşleşmesine giriyor (B16)",
    "C4": "şönt Kelvin hattı RC süzgeci; tip fark etmez",
    "C5": "Sallen-Key süzgeç (2×1nF paralel); C0G olsa daha iyi, stokta yok — disk olur",
    "C6": "Sallen-Key süzgeç; disk olur",
    "C7": "Sallen-Key süzgeç (2×1nF paralel); disk olur",
    "C8": "Sallen-Key süzgeç; disk olur",
    "C9": "U3 (+5V) ayırma — pine yakın", "C10": "U4 (+5V) ayırma — pine yakın",
    "C11": "U5 (+12V) ayırma", "C12": "U5 (−12V) ayırma",
    "C13": "U8 (+12V) ayırma", "C14": "U8 (−12V) ayırma",
    "C15": "ADS rayı (+3V3) ayırma",
    "C16": "7912 giriş kondansatörü — + ucu +12V, − ucu −12V (uzun bacak +)",
    "C17": "7912 çıkış kondansatörü — + ucu +12V, − ucu GND (uzun bacak +)",
    "C18": "akım kanalı örtüşme süzgeci (B16), 1 µF film 15 mm bacak — C023 (CBB22 105J400V, polipropilen ±%5; ölçüldü 15 mm, 4 adet) ya da C022 (damla, ±%10, 1 adet); C021 22.5 mm sığmaz",
    "C19": "akım kanalı örtüşme süzgeci (B16) — C18/C20 ile paralel, toplam 1.32 µF",
    "C20": "akım kanalı örtüşme süzgeci (B16) — ADS pinine en yakın olan",
}

# ── belgede parca satirina eklenen aciklama ────────────────────────────
# Kullanici sordu (2026-09-15): "F1 50mA diyor — sigorta mi yuvasi mi?",
# "R40 metal film mi olmali?". Semanin deger alani bunu soylemiyor.
PARCA_NOTU = {
    "F1": "Plakete lehimlenen: 5×20 sigorta YUVASI (2 klips, FUS009). 50mA, içine takılan "
          "cam sigortanın değeri — 50 mA geldi (FUS010, 2026-09-17); yuvada geçici 400 mA "
          "(FUS001) duruyorsa onunla DEĞİŞTİR.",
    "R40": "7912'nin asgari yükü: 12 V / 1K = 12 mA, 144 mW → 1/2 W (R030). Değer kritik "
           "değil; metal film GEREKMEZ.",
    # Kullanici sordu (2026-09-16): "TL431LP diyor, elimdeki TL431A — ayni mi?"
    "U1": "Şemadaki 'LP' kılıf kodu (TO-92), parça adı değil. Stoktaki parça: gövdede "
          "'WS TL431A 819SB' = Wing Shing, A sınıfı (±%1; sıfır kalibrasyonu zaten siliyor). "
          "Wing Shing veri sayfası (datasheet/TL431A_WingShing_TO-92.pdf): TO-92 ön yüzden "
          "R-A-K — TI ile AYNI, plan doğru. Yine de lehimlemeden önce 5 V→1K→K, REF=K "
          "bağla, K'da 2.5 V okunmalı.",
}

# ── kart disi tel lehim noktalarinin belgede gorunen adi ───────────────
TEL_ETIKET = {
    "T_HV": "HV jak", "T_N6": "→ A:HV alt",
    "T_VGIR": "V girişi (J1)", "T_COM": "COM jak", "T_HVALT": "HV alt (B'den)",
    "T_SKOP": "Skop jak (J4)", "T_SP": "S+ (şönt üst)", "T_SN": "S− (şönt alt)",
    "T_YILDIZ": "GND yıldız (şönt alt BACAĞI, S− ile aynı nokta)", "T_KAPI": "Q1 kapı",
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
