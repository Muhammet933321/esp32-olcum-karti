# -*- coding: utf-8 -*-
"""Kutu / panel kurulumunun TEK KARAR YERI (B50).

`yerlesim3_veri.py` plakete ne gelecegini soyluyor; burasi PLAKETE
GIRMEYEN her seyi soyluyor: kutunun kendisi (kullanici DIL CUBUGUNDAN
yapiyor), panel delikleri, sont ve yuk yolu, Q1, kablolarin hangi alt
adimda baglandigi.

Kural (yerlesim planiyla ayni): sayilar burada, metin ve cizim
uretecte, denetim `kutu.py`'de. Kart disi kablolarin KENDISI burada
tekrar YAZILMAZ — `yerlesim3_veri.KABLOLAR` tek kaynak; burada yalnizca
"hangi kablo hangi alt adimda" eslemesi var.

EKSENLER (mm) — tek tanim, her yerde ayni:
  x = soldan saga (kutunun ONUNDEN bakinca), y = 0 ARKA duvarin ic yuzu,
  y = ic_boy ON duvarin ic yuzu (jaklar), z = tabandan yukari.
  2B kusbakisi bunu oldugu gibi cizer (on duvar altta). 3B sahne sag-el
  sistemi icin y'yi cevirir — o cevirme yalnizca kutu.sahne()'de.
  Panel x'leri de AYNI eksende (ic sol koseden, onden bakinca) — arka
  panel dahil. Kullanici arkaya gecince kendi solundan olcer: arka panelin
  CIZIMI ve DELIK TABLOSU uretecte aynalanir (kutu.arka_ayna), veri degil.

Kutu ilkeleri (B50f, kullanici 2026-09-20):
  * Kutuya giren hicbir parca YAPISTIRILMAZ — vida ve kablo bagi; kutunun
    kendi parcalari (cubuk, ayak, altlik) yapistirilir.
  * Tek kat 2 mm tahta esner ve jak somunu tutmaz: duvarlar iki kat
    (disi yatay siralar, ici dikey cubuklar), dort ic kosede direk.
  * Kapak dort M3 civatayla YAN duvarlardan kapak raylarina baglanir —
    tahtaya dis acilmaz, somunla tutulur; ayaklarda gomme somun.
"""
from __future__ import annotations

# ── malzeme: dil basacagi ──────────────────────────────────────────────
# Kullanici olctu (2026-09-20): 150 x 18 x 2, uclar 10 mm yuvarlak.
# duz bolum = uzunluk - 2*uc_egim; derz = iki cubuk arasindaki silikon.
CUBUK = {"uzunluk": 150.0, "genislik": 18.0, "kalinlik": 2.0, "uc_egim": 10.0,
         "derz": 0.5, "ad": "dil basacağı (tahta çubuk)"}

# ── kutu ───────────────────────────────────────────────────────────────
KUTU = {
    "ic_en": 214.0,             # net ic (ic katin icinden icine)
    "ic_boy": 154.0,            # dis derinlik 162 = 9 taban sirasi x 18
    "duvar_sira": 4,            # dis kat: 4 x 18 = 72 mm
    "duvar_kat": 2,             # dis yatay + ic dikey
    "direk_kat": 3,             # kose diregi 3 cubuk = 6 mm
    "kapak_civata": "M3x12",    # yan duvardan kapak rayina, somunlu
    "kapak_civata_y": (45.0, 117.0),   # her yan duvarda iki civata (y) — yan ic kat cubugu ortasi
    "kapak_civata_z": 63.0,     # 4. siranin ortasi
    "kenar_payi": 10.0,         # panel deligi ile kose arasi en az
    "parca_payi": 6.0,          # ic parcalar arasi en az bosluk
    "elde_cubuk": 50,           # kullanicida su an olan (yaklasik)
    "yapistirici": "sıcak silikon (tabanca) — tahtada hızlı tutar; "
                   "istersen ahşap tutkalı daha sağlam ama beklemek gerekir",
}

# ── kutunun icindeki parcalar (taban yerlesimi) ────────────────────────
# x, y: sol-ARKA kosesi (y=0 arka duvar).  en/boy: taban izi.  yuk: en
# yuksek nokta.  tasiyici: kutunun parcasi olan altlik/ayak (kesim
# listesine girer).  nasil: sokulebilir tutturma (denetim olcuyor).
IC_PARCA = [
    {"ref": "A", "ad": "Ana kart (45×45 delikli plaket)", "x": 13.0, "y": 12.0,
     "en": 114.3, "boy": 114.3, "yuk": 24.0, "sutun_yonu": "arka", "bos_yuk": 2.0,
     "tasiyici": {"tip": "ayak", "adet": 4, "kat": 4, "adim": "6.1"},
     "nasil": "Dört köşede ahşap ayak bloğu (gömme M3 somunlu); plaket M3x10 vidayla "
              "ayaklara. YAPIŞTIRILMAZ — vidayı sök, kart çıkar. Telli kenarı "
              "(A–C sütunları) ÖN panele baksın."},
    {"ref": "ESP32", "ad": "ESP32-S3 devkit", "x": 139.0, "y": 2.0,
     "en": 26.0, "boy": 63.0, "yuk": 14.0, "soket_x_ofset": 13.0, "soket_z": 7.0,
     "tasiyici": {"tip": "altlik", "adet": 2, "uzunluk": 63.0, "adim": "6.3"},
     "nasil": "Pinler yukarı, USB soketi ARKA duvara 2 mm; iki çubuk altlığa kablo "
              "bağıyla (altlıkta iki delik). Kablo bağını kes, çıkar."},
    {"ref": "RS", "ad": "15 mΩ şönt (R044)", "x": 176.0, "y": 2.0,
     "en": 12.0, "boy": 30.0, "yuk": 10.0,
     "stok": ("15mR Type-C Şönt Direnç", "Direnç"),
     "tasiyici": {"tip": "altlik", "adet": 1, "uzunluk": 30.0, "adim": "6.6"},
     "nasil": "Tek çubuk altlığa kablo bağıyla; bacakları serbest, hava alsın. "
              "Kelvin/yıldız demeti tezgahta lehimlenir, karta KONNEKTÖRLE gelir. "
              "Sökülebilir."},
    {"ref": "B", "ad": "HV zinciri kartı (5×5 cm)", "x": 140.0, "y": 72.0,
     "en": 45.7, "boy": 45.7, "yuk": 16.0,
     "tasiyici": {"tip": "ayak", "adet": 2, "kat": 4, "adim": "6.1"},
     "nasil": "İki ahşap ayak (gömme somunlu) + M3 vida; HV jakının yakınında, "
              "HV kablosu ≤ 6 cm. Sökülebilir."},
    {"ref": "Q1", "ad": "IRFZ44N + soğutucu", "x": 196.0, "y": 44.0,
     "en": 15.0, "boy": 40.0, "yuk": 42.0,
     "stok": ("IRFZ44N", "MOSFET"),
     "tasiyici": {"tip": "kosebent", "adet": 3, "uzunluk": 40.0, "adim": "6.6"},
     "nasil": "Soğutucu DİK (kanatlar y yönünde), ahşap köşebende M3 vida + somun. "
              "MOSFET'in tabı soğutucudan yalıtılmış. Kapı teli konnektörle. Sökülebilir."},
]

# ── kutunun kendi ek bloklari ──────────────────────────────────────────
# Kutu parcasi (yapistirilir); kat = ust uste cubuk sayisi, adim = ne zaman.
KUTU_EK_PARCA = [
    {"ref": "HV ankraj bloğu", "x": 150.0, "y": 122.0, "en": 18.0, "boy": 6.0, "yuk": 18.0,
     "kat": 3, "adim": "9.3",
     "nasil": "Üç çubuk parçası üst üste, kart B'nin önünde tabana dik yapıştırılır; HV "
              "kablosu buna kablo bağıyla tutulur — çekilince D8 lehimi değil bağ direnir."},
    {"ref": "24 V klemens çubuğu", "x": 40.0, "y": 2.0, "en": 30.0, "boy": 2.0, "yuk": 18.0,
     "kat": 1, "adim": "10.1",
     "nasil": "Arka duvara paralel, XT30 kuyruğunun yanında dik duran tek çubuk; 2'li vidalı "
              "klemens (CON007) yüzüne vidalanır/yapıştırılır."},
]

# ── panel ogeleri ──────────────────────────────────────────────────────
# x: ic sol koseden, ONDEN bakinca (arka panel dahil — USB x'i ESP32 soket
# x'iyle dogrudan karsilastirilir); z: tabandan.  Her delik/yuva bir ic-kat
# cubugunun ORTASINA gelir: ic kat listesi bu x'lerden turetilir
# (kutu.py: ic_kat_cubuklari); USB yuvasinin arkasindaki cubuk KISA.  derin_mm: ogenin
# kutu icine uzanan govdesi (cakisma denetimi).  menzil: etiketi uretec
# tasarim sabitinden yazar.
# J3 (YUK) ve J7 (PIL) born jak CIFTI: bariyer klemens panele
# vidalanamiyordu (PCB tipi); buyuk boy jaklar 15 A tasir.
PANEL_ON = [
    {"ref": "J3.1", "ad": "YÜK 1 — devrenin eksisi", "tip": "jak", "x": 33.0, "z": 9.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 22.0, "renk": "siyah",
     "parca": ("4mm Born Jak Şeffaf Siyah (Büyük Boy)", "Konnektör"),
     "etiket": "YÜK 1", "alt_etiket": "devre −", "not": "Akım buradan girer; büyük boy jak."},
    {"ref": "J3.2", "ad": "YÜK 2 — kaynağın eksisi", "tip": "jak", "x": 69.0, "z": 9.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 22.0, "renk": "siyah",
     "parca": ("4mm Born Jak Şeffaf Siyah (Büyük Boy)", "Konnektör"),
     "etiket": "YÜK 2", "alt_etiket": "kaynak −", "not": "Şöntün alt bacağı = kart GND = COM."},
    {"ref": "J7.1", "ad": "PİL 1 — yük direncinin ucu", "tip": "jak", "x": 123.0, "z": 9.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "derin_mm": 20.0, "renk": "mavi",
     "parca": ("4mm Born Jak Şeffaf Mavi (Büyük Boy)", "Konnektör"),
     "etiket": "PİL 1", "alt_etiket": "yük direnci", "not": "Q1'in savağı."},
    {"ref": "J7.2", "ad": "PİL 2 — pilin eksisi", "tip": "jak", "x": 159.0, "z": 9.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "derin_mm": 20.0, "renk": "mavi",
     "parca": ("4mm Born Jak Şeffaf Mavi (Büyük Boy)", "Konnektör"),
     "etiket": "PİL 2", "alt_etiket": "pil −", "not": "YÜK 2 ile aynı düğüm (şönt altı)."},
    {"ref": "J1.1", "ad": "V girişi", "tip": "jak", "x": 87.0, "z": 45.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "derin_mm": 20.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (kırmızı)", "Konnektör"),
     "etiket": "V", "menzil": "normal", "not": "NORMAL gerilim kanalı."},
    {"ref": "J1.2", "ad": "COM (ortak)", "tip": "jak", "x": 123.0, "z": 45.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "derin_mm": 20.0, "renk": "siyah",
     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (siyah)", "Konnektör"),
     "etiket": "COM", "alt_etiket": "= YÜK 2 = PİL 2",
     "not": "TEK COM: V, HV ve SKOP'un ortak ucu; içeride YÜK 2 ve PİL 2 ile aynı düğüm."},
    {"ref": "J4.1", "ad": "Osiloskop girişi", "tip": "jak", "x": 159.0, "z": 45.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "derin_mm": 20.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (kırmızı)", "Konnektör"),
     "etiket": "SKOP", "menzil": "skop", "not": "Dalga şekli kanalı."},
    {"ref": "SW", "ad": "Güç anahtarı (AÇ/KAPA toggle)", "tip": "anahtar", "x": 33.0, "z": 63.0,
     "delik_mm": 6.0, "metal_mm": 12.0, "derin_mm": 15.0, "renk": "gri",
     "parca": ("KTS102 On/Off 3 Ayak Toggle Anahtar", "Anahtar/Buton"),
     "etiket": "AÇ/KAPA", "alt_etiket": "24 V + hattı",
     "not": "KTS102 toggle (orta + bir uç ayak; ON-OFF), 24 V'un ARTI koluna seri, kaynak seçicinin "
            "ARDINDAN (pil kipinde de bu açar/kapar). YÜK 1 jakının üstünde (aynı iç çubuk). Kilit "
            "anahtarı (SW045) kullanılmadı — kullanıcı toggle istedi (2026-09-20)."},
    {"ref": "SWP1", "ad": "Hücre 1 anahtarı (ESP32 pili)", "tip": "anahtar", "x": 69.0, "z": 63.0,
     "delik_mm": 6.0, "metal_mm": 12.0, "derin_mm": 15.0, "renk": "gri",
     "parca": ("KTS102 On/Off 3 Ayak Toggle Anahtar", "Anahtar/Buton"),
     "etiket": "PİL ESP32", "alt_etiket": "hücre 1 → MT1",
     "not": "KTS102 toggle (ikinci adet): hücre 1'i MT1'e bağlar. USB takılıyken KAPALI tut (MT3608 boşta "
            "1–4 mA çeker). YÜK 2 jakının üstünde."},
    {"ref": "SWP2", "ad": "24 V kaynak seçici (PİL / HARİCİ)", "tip": "anahtar", "x": 87.0, "z": 63.0,
     "delik_mm": 6.0, "metal_mm": 12.0, "derin_mm": 15.0, "renk": "gri",
     "parca": ("KTS202 On/Off 6 Ayak Toggle Anahtar", "Anahtar/Buton"),
     "etiket": "PİL / HARİCİ", "alt_etiket": "24 V kaynağı",
     "not": "KTS202 çift kutup (DPDT, ON-ON): iki hattı birden seçer — pil eksisi ile XT30 eksisi hiçbir "
            "konumda birleşmez. Stoktaki 3 konumlu KTS103 tek kutup, seçici olamaz (eksi hattı açıkta "
            "kalır). Ortak uçlar AÇ/KAPA anahtarına, oradan klemense. V jakının üstünde."},
    {"ref": "J2.1", "ad": "YÜKSEK gerilim girişi", "tip": "jak", "x": 187.0, "z": 63.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 22.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Şeffaf Kırmızı (Büyük Boy)", "Konnektör"),
     "etiket": "HV ⚡", "menzil": "yuksek",
     "not": "AYRI sırada ve işaretli; arka ucu makaronla kaplanır. Yerini değiştirme."},
]

PANEL_ARKA = [
    {"ref": "J6", "ad": "24 V girişi — XT30 kuyruğu", "tip": "kuyruk", "x": 45.0, "z": 9.0,
     "delik_mm": 6.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "sari",
     "parca": ("XT30 Lipo Pil Konnektör Takımı", "Konnektör"),
     "etiket": "24 V", "alt_etiket": "XT30 kuyruk",
     "not": "8–10 cm kalın kablo kuyruğu: dışarıda XT30'un PİMLİ (erkek) ucu — kutu "
            "enerjisiz taraf. Kaynak kablosuna KILIFLI (dişi) uç. İçeride düğüm/"
            "kablo bağı gerilim tahliyesi."},
    # B52 pil blogu (2026-09-20, kullanici: iki hucre, sifir alim, arka duvara asili).
    # Kilit anahtari ve toggle'lar ON panelde (4. sira, HV'nin solunda): arka duvarin
    # 3. sirasinda iki sarj yuvasi + kilit anahtari dis kat ek yerine yer birakmiyordu.
    {"ref": "SARJ1", "ad": "Hücre 1 (ESP32) şarj — TP4056 Type-C", "tip": "yuva", "x": 27.0, "z": 45.0,
     "delik_mm": 9.0, "yuva_en_mm": 14.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri",
     "parca": None, "etiket": "ŞARJ 1", "alt_etiket": "ESP32 pili",
     "not": "TP1 rafının Type-C soketi bu yuvadan bakar. Hücre 1'in eksisi = kart GND: PC'ye takılıyken "
            "de güvenli."},
    {"ref": "SARJ2", "ad": "Hücre 2 (24 V) şarj — TP4056 Type-C", "tip": "yuva", "x": 187.0, "z": 45.0,
     "delik_mm": 9.0, "yuva_en_mm": 14.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri",
     "parca": None, "etiket": "ŞARJ 2", "alt_etiket": "⚠ yalnız HARİCİ konumda",
     "not": "TP2 rafı. Hücre 2'nin eksisi pil kipinde kartın −12 rayıdır: kaynak seçici PİL'deyken şarj "
            "kablosu takılıp PC/ortak adaptöre giderse −12 GND'ye kısa olur. Şarj = seçici HARİCİ."},

    {"ref": "USB", "ad": "ESP32 USB yuvası", "tip": "yuva", "x": 152.0, "z": 8.0,
     "delik_mm": 9.0, "yuva_en_mm": 14.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri",
     "parca": None, "etiket": "USB", "alt_etiket": "⚡ HV ölçerken çıkar",
     "not": "14 × 9 mm oval yuva; devkit'in COM yazan Type-C soketi buraya bakar."},
]

# ── duvara asili parcalar: pil blogu (B52) ────────────────────────────
# duvar: "arka" (y=0 yuzu) ya da "ön" (y=ic_boy).  x/z: sol-alt kose (ic
# koordinat, onden bakinca; arka duvar cizimi aynalanir).  derin: kutunun
# icine uzanan derinlik.  Neden burasi: zeminde 77x21 yuvaya yer yok; sol
# duvarda A'nin ustu (32) + pay + yuva (21) kapak rayina (54) sigmiyor;
# arka duvarin ESP32/sont bolgesi (x>127, z>16) ve A'nin ustu (z>38, ince
# parcalar A'nin arka kenari y=12'den once) uyuyor.
DUVAR_PARCA = [
    {"ref": "YUVA1", "ad": "18650 yuvası — hücre 1 (ESP32)", "duvar": "arka", "x": 92.0, "z": 22.0,
     "en": 80.0, "yuk": 21.0, "derin": 21.0, "stok": ("18650 Tekli Pil Yuvası", "Güç Kaynağı/Pil"),
     "nasil": "80 × 21 × 21 (ölçüldü). İki M3 cıvata duvardan (dıştan) geçer, içeride somun; yuva sökülür, "
              "hücre yuvadan çıkar. Hücre başlı (PWR005) — yaylı yuvada başlık temas eder; yalıtım contası "
              "MEK025."},
    {"ref": "YUVA2", "ad": "18650 yuvası — hücre 2 (24 V)", "duvar": "arka", "x": 92.0, "z": 49.0,
     "en": 80.0, "yuk": 21.0, "derin": 21.0, "stok": ("18650 Tekli Pil Yuvası", "Güç Kaynağı/Pil"),
     "nasil": "İki M3 cıvata dıştan, somun içeride; sökülebilir. Kapağa 2 mm kalır (yuva 21 mm "
              "ölçüldü mü — 1.1'de kumpasla)."},
    {"ref": "TP1", "ad": "TP4056 şarj modülü — hücre 1 (raf)", "duvar": "arka", "x": 18.5, "z": 42.0,
     "en": 17.0, "yuk": 5.0, "derin": 25.0, "stok": ("TP4056 Li-ion Şarj Devresi", "Modül"),
     "nasil": "Kart RAF gibi yatay (27 × 17 × 5 ölçüldü, soket kart kenarından 2 mm dışarı): soket "
              "ŞARJ 1 yuvasının içine 2 mm girer, kart kenarı duvara dayanır; iki M2.5/M3 cıvata + duvara "
              "yapıştırılmış 3 katlı çubuk bloğu (somun gömme). Sökülebilir."},
    {"ref": "TP2", "ad": "TP4056 şarj modülü — hücre 2 (raf)", "duvar": "arka", "x": 178.5, "z": 42.0,
     "en": 17.0, "yuk": 5.0, "derin": 25.0, "stok": ("TP4056 Li-ion Şarj Devresi", "Modül"),
     "nasil": "Raf gibi yatay, soketi ŞARJ 2 yuvasına dayalı; çubuk bloğuna cıvata. Sökülebilir."},
    {"ref": "MT1", "ad": "MT3608 — 5.0 V (ESP32)", "duvar": "arka", "x": 42.0, "z": 24.0,
     "en": 36.0, "yuk": 17.0, "derin": 14.0, "stok": ("MT3608 DC-DC Yükseltici", "Modül"),
     "nasil": "Arka duvarın iç yüzüne düz (A'nın boş arka şeridinin üstü); iki M3 cıvata dıştan, somun "
              "içeride (ya da yapışık çubuk bloğu + vida). Trimpot içe bakar, ayar kapak açıkken. Sökülebilir."},
    {"ref": "MT2", "ad": "MT3608 — 24.0 V (analog ray)", "duvar": "arka", "x": 42.0, "z": 47.0,
     "en": 36.0, "yuk": 17.0, "derin": 14.0, "stok": ("MT3608 DC-DC Yükseltici", "Modül"),
     "nasil": "MT1'in üstüne, aynı yöntemle iki M3 cıvata; sökülebilir. Çıkışı kaynak seçiciye (SWP2), "
              "oradan AÇ/KAPA anahtarına."},
]

# Kutuya giren, kartla ilgisi olmayan parcalarin kurallari (KART_DISI_NOTU'nun kutu esi)
KUTU_NOTU = {
    "YUVA1": "18650 yuvası; hücre 1'in EKSİSİ = kart GND (ESP32 ile ortak). Şarj her zaman güvenli.",
    "YUVA2": "18650 yuvası; hücre 2'nin EKSİSİ pil kipinde −12 rayı. Hücre 2 hiçbir yerde kart GND'ye "
             "değmez — kablo listesi ve denetim bunu ölçüyor.",
    "TP1": "TP4056 korumalı (DW01+FS8205): B± hücreye, OUT± yüke. Rprog 1.5–1.6 kΩ (~0.5 C). Yük "
           "altında şarj etme: SWP1 KAPALI.",
    "TP2": "Aynı; şarj yalnız SWP2 HARİCİ konumdayken.",
    "MT1": "MT3608 yüksüz 5.0 V'a ayarlanır (fabrika ayarı 28 V'a kadar çıkabilir — önce ayar, sonra ESP32). "
           "Çıkış ESP32'nin 5V (VIN) pinine; devkit USB'yle diyot-OR yapar.",
    "MT2": "MT3608 yüksüz 24.0 V'a ayarlanır. 24 V yükü 19–25 mA → hücreden ~150–200 mA. Anahtarlama "
           "dalgalanması −12 rayında skopla ölçülecek (5.12.23 bu yolu gürültülü diye reddetmişti).",
    "SWP1": "KTS102 toggle: hücre 1 → MT1.",
    "SWP2": "KTS202 DPDT kaynak seçici: PİL (MT2 çıkışı) / HARİCİ (XT30). Ortak uçlar → AÇ/KAPA anahtarı → "
            "klemens. Şarj kuralı: hücre 2 şarjdayken HARİCİ.",
}

# Pil blogu kablolari — kart kablolari degil (yerlesim3_veri.KABLOLAR'a girmez):
# (nereden, nereye, tur, not).  Dugum adlari: H1±/H2± hucre uclari, TPn.B±/OUT±,
# MTn.IN±/OUT±, SWP1.1/2, SWP2.P1/P2 (ortak), .A1/.A2 (PIL), .B1/.B2 (HARICI),
# SW.1/2 AC/KAPA toggle, KL.+/- klemens, J6.1/J6.2 XT30 kuyruk, ESP32.5V / ESP32.GND.
# Denetim bu listeden graf kuruyor: PIL konumunda H2- yalniz -12 rayina, asla
# kart GND'ye; H1- kart GND'ye; HARICI konumda H2- hicbir kart dugumune bagli
# degil (sarj guvenli).
PIL_KABLOLAR = [
    ("H1+", "TP1.B+", "pil", "hücre 1 artı — yuva ucundan, kırmızı"),
    ("H1-", "TP1.B-", "pil", "hücre 1 eksi — siyah"),
    ("TP1.OUT+", "SWP1.1", "pil", "korumalı çıkış (B+ değil!)"),
    ("SWP1.2", "MT1.IN+", "pil", "anahtar hücre tarafında: kapalıyken MT1 hiç çekmez"),
    ("TP1.OUT-", "MT1.IN-", "pil", "eksi doğrudan"),
    ("MT1.OUT+", "ESP32.5V", "sinyal", "5.0 V → devkit 5V/VIN pini (J5 kablosuna eklenmez, ayrı dişi jumper)"),
    ("MT1.OUT-", "ESP32.GND", "sinyal", "= kart GND (ESP32 üzerinden). Hücre 1 eksisi bu düğümde."),
    ("H2+", "TP2.B+", "pil", "hücre 2 artı"),
    ("H2-", "TP2.B-", "pil", "hücre 2 eksi"),
    ("TP2.OUT+", "MT2.IN+", "pil", "korumalı çıkış"),
    ("TP2.OUT-", "MT2.IN-", "pil", ""),
    ("MT2.OUT+", "SWP2.A1", "pil", "24.0 V → seçicinin PİL ucu (kutup 1)"),
    ("MT2.OUT-", "SWP2.A2", "pil", "24 V eksisi → seçicinin PİL ucu (kutup 2) — bu uç −12 rayı olur"),
    ("J6.1", "SWP2.B1", "besleme", "XT30 kuyruk kırmızı → seçicinin HARİCİ ucu (kutup 1)"),
    ("J6.2", "SWP2.B2", "besleme", "XT30 kuyruk siyah → seçicinin HARİCİ ucu (kutup 2)"),
    ("SWP2.P1", "SW.1", "besleme", "seçici ortak (kutup 1) → AÇ/KAPA anahtarı"),
    ("SW.2", "KL.+", "besleme", "AÇ/KAPA anahtarı → klemens + (kart C34)"),
    ("SWP2.P2", "KL.-", "besleme", "seçici ortak (kutup 2) → klemens − (kart C36 = −12 rayı)"),
]
# Asama (kutu.py pil_asama): ucu H1/TP1/MT1/SWP1/ESP32 olan kablolar 2. asama
# (ESP32 hucresi, istege bagli), digerleri 1. asama (24 V hucresi).
# Modullerin ic baglantilari (grafta kisa devre sayilir): korumali TP4056'da
# OUT- ile B- koruma FET'i uzerinden ayni dugum; MT3608'de IN- = OUT-.
PIL_IC_BAG = [("TP1.B-", "TP1.OUT-"), ("TP2.B-", "TP2.OUT-"), ("MT1.IN-", "MT1.OUT-"),
              ("MT2.IN-", "MT2.OUT-"), ("KL.-", "-12"), ("ESP32.GND", "KART_GND")]
PIL_SECICI = {"PİL": [("SWP2.P1", "SWP2.A1"), ("SWP2.P2", "SWP2.A2")],
              "HARİCİ": [("SWP2.P1", "SWP2.B1"), ("SWP2.P2", "SWP2.B2")]}

# ── adimlar ve alt adimlar ─────────────────────────────────────────────
# tur: cizim/gorunum secer.  kablo: yerlesim3_veri.KABLOLAR indeksleri.
# monte: kutuya giren kart disi parca.  vurgu: 3B/2B'de parlayacak ref'ler.
# kapi: enerjili test numarasi (metin yerlesim3_belge.KAPI'dan).
ADIMLAR = [
    {"no": 1, "baslik": "Ölçü ve kesim", "alt": [
        {"no": "1.1", "baslik": "Çubuğunu ve parçaları ölç", "tur": "kesim",
         "yap": ["Bir çubuğu cetvelle ölç: <b>{u:.0f} × {g:.0f} × {k:.0f} mm</b>, uçlarda "
                 "<b>{ue:.0f} mm</b> yuvarlak bölüm (2026-09-20'de doğrulandı); ortada "
                 "<b>{duz:.0f} mm düz</b> bölüm kalıyor.",
                 "Kumpasla ölç ve tutmuyorsa söyle: born jak gövde dişi (küçük ≈ 6, büyük "
                 "≈ 8 mm), USB-C fiş gövdesi (≈ 12 × 6.5), anahtar dişi (12).",
                 "Tutmayan bir sayı varsa bana söyle — kesim listesi, delik tabloları ve "
                 "çizimler bu sayılardan üretiliyor, yeniden üretirim."],
         "kontrol": ["Çubuklar düz mü, çatlak var mı? Eğri olanları kapak için ayır."]},
        {"no": "1.2", "baslik": "Kesim listesi — önce taban ve dış kat", "tur": "kesim",
         "yap": ["Çubuğun <b>iki ucu yuvarlak</b>: düz birleşme isteyen her parça ortadaki "
                 "<b>düz bölümden</b> ({duz:.0f} mm) kesilir. İç kat ve direk parçaları "
                 "<b>yarım çubuktan</b>: çubuğu ortadan ikiye kes, düz uçtan 3 mm al → "
                 "{h:.0f} mm, <b>yuvarlak uç aşağı</b> (tabanda gizli kalır).",
                 "<b>Ölç-kes-ölç:</b> şimdi yalnız <b>taban, raylar ve dış kat</b> "
                 "parçalarını kes. İç kat, direkler, kapak ve altlıklar duvar bitince "
                 "gerçek ölçüye göre kesilecek (4.4).",
                 "Maket bıçağı ya da ince testere; kesmeden önce kurşun kalemle işaretle. "
                 "Parçaları gruplara ayır."],
         "kontrol": ["Her gruptaki parça sayısı listedekiyle aynı mı?",
                     "Aynı gruptaki parçaların boyu eşit mi (üst üste koy, uçlar hizalı)?"]},
    ]},
    {"no": 2, "baslik": "Taban", "alt": [
        {"no": "2.1", "baslik": "Taban sıralarını diz", "tur": "taban",
         "yap": ["Taban parçalarını düz bir zeminde <b>sıra sıra</b> diz: her sıra iki "
                 "parça uç uca, ek yeri sırada bir sağa bir sola (kaydırmalı).",
                 "Sıralar yan yana, boşluksuz. Henüz yapıştırma yok."],
         "kontrol": ["Dizilen tabanın eni ve boyu tabloyla uyuyor mu?"]},
        {"no": "2.2", "baslik": "Alttan raylarla bağla", "tur": "taban",
         "yap": ["Rayları tabanın <b>altına</b>, sıralara dik (derinlik yönünde), "
                 "uçlardan içeride yapıştır. Ray bütün sıraları birbirine bağlar.",
                 "Silikonu ray boyunca sürekli çek, nokta nokta değil."],
         "kontrol": ["Taban tek parça gibi kalkıyor mu? Ortadan tutup kaldır.",
                     "Taban düz mü, beşik gibi kamburlaşmamış mı?"]},
    ]},
    {"no": 3, "baslik": "Dış kat parçalarını del (düz zeminde)", "alt": [
        {"no": "3.1", "baslik": "Ön duvar parçalarını del", "tur": "delik_parca", "panel": "ön",
         "yap": ["Delikler duvar dikilmeden, parça <b>düz zeminde</b> delinir: 18 mm'lik "
                 "çubukta Ø8 delik 5 mm et bırakır, yerinde delmek çatlatır.",
                 "Aşağıdaki tabloda her delik hangi sıranın hangi parçasına, parçanın "
                 "<b>sol ucundan</b> kaç mm'ye ve çubuğun <b>alt kenarından</b> kaç mm'ye "
                 "geliyor. Parçanın altına fire çubuk koy, önce 2 mm kılavuz aç, sonra büyüt.",
                 "Delinen parçayı sıra ve konumuyla etiketle (örn. \"ön 3 sol\")."],
         "kontrol": ["Jakı deliğe sok: gövde geçiyor, somun yüzeye oturuyor.",
                     "Delik çevresinde çatlak yok."]},
        {"no": "3.2", "baslik": "Arka duvar parçalarını del", "tur": "delik_parca", "panel": "arka",
         "yap": ["Aynı yöntem. Tablodaki ölçüler <b>dışarıdan bakınca soldan</b>.",
                 "USB yuvası oval: iki Ø9 delik açıp arasını maket bıçağıyla al."],
         "kontrol": ["Anahtarın somunu oturuyor.", "USB-C fişi yuvadan rahat geçiyor."]},
    ]},
    {"no": 4, "baslik": "Duvarlar", "alt": [
        {"no": "4.1", "baslik": "1. sıra — ön ve arka", "tur": "duvar", "sira": 1,
         "yap": ["Ön ve arka duvarın ilk sırasını tabanın kenarına, <b>dik</b> yapıştır. "
                 "Geniş yüz dışa, delikli parçalar tablodaki yerde.",
                 "Her sıra iki parça; ek yeri tabloda yazan x'te."],
         "kontrol": ["Gönye ya da kitap kenarıyla bak: duvar tabana dik mi?"]},
        {"no": "4.2", "baslik": "1. sıra — yanlar", "tur": "duvar", "sira": 1,
         "yap": ["Yan duvarların ilk sırasını ön ve arka duvarın <b>arasına</b> sıkıştır.",
                 "Köşeleri içeriden bir damla silikonla güçlendir."],
         "kontrol": ["Dört köşe de kapalı mı?"]},
        {"no": "4.3", "baslik": "2., 3. ve 4. sıralar", "tur": "duvar", "sira": 4,
         "yap": ["Üstteki sıraları aynı şekilde ekle; ek yerleri tabloda — sıradan sıraya "
                 "kayıyor, üst üste gelmiyor.",
                 "Delikli parçalar (3. ve 4. sıra) tablodaki konumda: delikler alt alta "
                 "hizalanmalı."],
         "kontrol": ["Duvar yüksekliği her köşede aynı mı?",
                     "Kutuyu ters çevir, sallanıyor mu?"]},
        {"no": "4.4", "baslik": "Ölç, kalanı kes", "tur": "kesim",
         "yap": ["Şimdi gerçek ölçüleri al: duvar yüksekliği (derz dahil), iç en, iç boy.",
                 "İç kat çubuklarını, direk parçalarını ve kapak raylarını <b>ölçtüğün</b> "
                 "yüksekliğe/uzunluğa kes (tablo nominal; 1–2 mm sapma normal)."],
         "kontrol": ["Bir iç kat çubuğunu deneme yerleştir: üstü dış katla hizalı mı?"]},
        {"no": "4.5", "baslik": "İç kat — dikey çubuklar", "tur": "duvar_ic", "sira": 4,
         "yap": ["Dört duvarın <b>iç yüzüne</b> dikey çubukları yapıştır (kontrplak gibi "
                 "çapraz kat). <b>Yuvarlak uç aşağı.</b>",
                 "Konum önemli: her yuvarlak deliğin tam arkasına bir çubuk <b>ortalanır</b> "
                 "(tablo). Aradaki dar boşluklar boş kalabilir, dış kat kapatıyor.",
                 "Silikonu üst-orta-alt üç noktaya sür; bastırınca yayılır."],
         "kontrol": ["Duvara parmakla bastır: artık esnememeli.",
                     "Deliklerin arkasında çubuk ortası var, ek yeri yok."]},
        {"no": "4.6", "baslik": "Köşe direkleri", "tur": "direk", "sira": 4,
         "yap": ["Her köşe için {direk_kat} parçayı üst üste yapıştırıp "
                 "<b>{direk_t:.0f} × {direk_g:.0f} × {h:.0f} mm</b> direk yap (4 adet), "
                 "yuvarlak uçlar aşağı.",
                 "Dört iç köşeye, iki duvara da yaslanacak şekilde yapıştır; üstü duvarla "
                 "hizalı."],
         "kontrol": ["Kutuyu köşelerinden tutup bur: köşeler oynamamalı.",
                     "Dört direğin üstü aynı seviyede."]},
    ]},
    {"no": 5, "baslik": "Panel parçalarını tak", "alt": [
        {"no": "5.1", "baslik": "İç katı deliklerden geçerek del", "tur": "delik", "panel": "ön",
         "yap": ["Dış kattaki her delikten matkabı geçir, iç kat çubuğunu <b>dıştan içe</b> del "
                 "(aynı çap). İçeriden çıkarken kıymık verirse fire çubukla destekle.",
                 "Arka duvar için de aynı. <b>USB yuvasında delme yok:</b> arkasındaki iç kat "
                 "çubuğu kısa, yuvanın üstünden başlıyor (4.5 tablosu)."],
         "kontrol": ["Her delik iki kattan düz geçiyor; jak gövdesi rahat giriyor."]},
        {"no": "5.2", "baslik": "Born jakları tak (8 adet)", "tur": "delik", "panel": "ön",
         "monte": ["J1", "J2", "J3", "J4", "J7"],
         "vurgu": ["J3.1", "J3.2", "J7.1", "J7.2", "J1.1", "J1.2", "J4.1", "J2.1"],
         "yap": ["Sekiz jakı deliklere tak, somunları içeriden sık. Renkler: <b>YÜK</b> siyah "
                 "büyük ×2, <b>PİL</b> mavi ×2, <b>V/SKOP/HV</b> kırmızı, <b>COM</b> siyah.",
                 "HV jakının içerideki ucuna somunu sıktıktan sonra <b>makaron</b> geçir.",
                 "Etiketleri hemen yapıştır: YÜK 1/2, PİL 1/2, V, COM, SKOP, HV ⚡."],
         "kontrol": ["Jakların içerideki uçları birbirine değmiyor.",
                     "Somunlar sıkı; jak elle dönmüyor."]},
        {"no": "5.3", "baslik": "XT30 kuyruğu ve AÇ/KAPA anahtarı", "tur": "delik", "panel": "arka",
         "monte": ["J6", "SW"], "vurgu": ["J6", "SW"],
         "yap": ["AÇ/KAPA toggle'ını (KTS102) somunuyla ÖN duvara (4. sıra, YÜK 1'in üstü) tak.",
                 "XT30 kuyruğu: 8–10 cm kalın kabloya XT30'un <b>pimli (erkek)</b> ucunu "
                 "lehimle — kutu tarafı enerjisiz, pimler açıkta olabilir. Kabloyu Ø6 "
                 "delikten geçir, içeride düğüm at ya da kablo bağıyla durdur "
                 "(itme ve çekmeye karşı).",
                 "Kaynak kablosuna <b>kılıflı (dişi)</b> ucu tak: enerjili taraf kapalı."],
         "kontrol": ["Fişi tak-çıkar: kablo içeri kaçmıyor, dışarı çekilmiyor.",
                     "Anahtar iki konumda da net oturuyor."]},
    ]},
    {"no": 6, "baslik": "Kartları ve güç parçalarını hazırla", "alt": [
        {"no": "6.1", "baslik": "Ayakları kartla hizala, gömme somun", "tur": "montaj",
         "vurgu": ["A", "B"],
         "yap": ["Yerleşim planı her kartın köşesinde <b>2×2 delik</b> boş bıraktı: bu dört "
                 "deliğin ortasına Ø3.2 del (A'da dört köşe, B'de çapraz iki köşe).",
                 "Kart A'yı tabana plandaki yere koy (telli kenar öne), vida deliklerinden "
                 "kurşun kalemle tabanı işaretle; kartı kaldır. Ayak bloğu kartın kenarından "
                 "~6 mm taşar, normal.",
                 "Ayak bloğu: 4 parça çubuk üst üste. 1. ve 2. kata Ø3.2 delik, 3. kata "
                 "<b>Ø6 delik + M3 somun gömülü</b>, 4. kat deliksiz. Somun 2. ve 4. kat "
                 "arasında hapis kalır — tahtaya diş açılmaz.",
                 "Blokları işaretler merkezde kalacak şekilde tabana yapıştır. Kart B için "
                 "iki blok aynı yöntemle."],
         "kontrol": ["Kartı koy, M3 vida dört delikten de somuna giriyor.",
                     "Kart sallanmıyor, altı hiçbir yere değmiyor."]},
        {"no": "6.2", "baslik": "Ana kartı vidala", "tur": "montaj", "vurgu": ["A"],
         "yap": ["Kart A'yı ayaklara oturt, dört M3x10 vidayla tuttur (pul ile). "
                 "<b>Yapıştırma.</b>",
                 "Vidayı fazla sıkma; plaket çatlar."],
         "kontrol": ["Kart tek parça çıkıyor (dene: vidaları sök, tak)."]},
        {"no": "6.3", "baslik": "ESP32, kart B ve altlıklar", "tur": "montaj",
         "vurgu": ["B", "ESP32"],
         "yap": ["ESP32 için iki çubuk altlık yapıştır (pinler yukarı bakacak, USB soketi "
                 "arka duvardaki yuvaya 2 mm); altlıkta iki delik, devkit kablo bağıyla.",
                 "Kart B'yi ayaklarına vidala; HV jakına yakın, kablo kısa."],
         "kontrol": ["USB-C fişi yuvadan girip sokete oturuyor.",
                     "Kart B ile kart A arasındaki tel gergin değil."]},
        {"no": "6.4", "baslik": "Şönt demetini tezgahta lehimle", "tur": "montaj", "vurgu": ["RS"],
         "yap": ["Şönt kutuya girmeden ÖNCE: iki bacağına kalın yük kabloları için "
                 "<b>halka pabuç/lehim kulağı</b> ve Kelvin tellerini lehimle. Şöntün "
                 "hangi bacağı RS.1 (YÜK 1 tarafı) hangisi RS.2 (YÜK 2) — işaretle.",
                 "Kelvin çifti S+ (RS.1) ve S− (RS.2) burgulu, yıldız GND RS.2'ye S− ile "
                 "<b>aynı noktaya</b>. Üç telin ucuna 3'lü <b>dişi header</b> (CON018'den kes).",
                 "Kart A'daki T_SP / T_SN / T_YILDIZ tellerinin uçlarına <b>erkek pin</b>: "
                 "demet konnektörle takılır, kart sökülebilir kalır."],
         "kontrol": ["S+ ↔ RS.1 bacağı, S− ↔ RS.2 bacağı: bip ötmeli.",
                     "Yıldız ↔ S−: ötmeli (aynı nokta).",
                     "RS.1 ↔ RS.2: 0.0–0.5 Ω (şönt + prob)."]},
        {"no": "6.5", "baslik": "Q1 demeti ve soğutucu", "tur": "montaj", "vurgu": ["Q1"],
         "yap": ["Q1'i soğutucuya <b>yalıtarak</b> vidala: mika/silikon izolatör + burç + "
                 "termal macun. Kapı bacağına 1 pinli dişi header, makaronla.",
                 "Soğutucuyu üç parça çubuktan köşebende M3 vida + somunla tuttur."],
         "kontrol": ["Q1 tabı ↔ soğutucu: ötmemeli.",
                     "Kapı ↔ kaynak: ötmemeli."]},
        {"no": "6.6", "baslik": "Şönt ve Q1'i kutuya al", "tur": "montaj", "vurgu": ["RS", "Q1"],
         "monte": ["RS", "Q1"],
         "yap": ["Şönt altlığını ve Q1 köşebendini plandaki yere yapıştır; şöntü kablo "
                 "bağıyla, köşebendi tabana silikonla (kutu parçası).",
                 "Parçaların hiçbirini doğrudan tabana yapıştırma."],
         "kontrol": ["Şönt bacakları serbest, hava alıyor.",
                     "Q1 soğutucusu hiçbir parçaya 6 mm'den yakın değil."]},
    ]},
    {"no": 7, "baslik": "Güç yolu — YÜK jakları, şönt, Kelvin", "alt": [
        {"no": "7.1", "baslik": "Yük yolunu bağla", "tur": "kablo", "kablo": [2, 3],
         "vurgu": ["RS", "J3.1", "J3.2"],
         "yap": ["YÜK 1 jakının içerideki ucu → şöntün RS.1 bacağı; şöntün RS.2 bacağı → "
                 "YÜK 2. <b>Kalın kablo (≥1.5 mm²)</b>, halka pabuçla jak somununun altına.",
                 "Kısa tut: ölçülen bütün akım bu yoldan geçecek."],
         "kontrol": ["YÜK 1 ↔ YÜK 2: 0.0–0.5 Ω (şönt 15 mΩ + prob).",
                     "YÜK 1 ↔ V, SKOP, HV jakları: OL (sonsuz)."]},
        {"no": "7.2", "baslik": "Kelvin ve yıldız konnektörünü tak", "tur": "kablo",
         "kablo": [4, 5, 6], "vurgu": ["RS"],
         "yap": ["6.4'te hazırladığın 3'lü demeti kartın T_SP / T_SN / T_YILDIZ pinlerine "
                 "tak — sıraya dikkat: S+ → T_SP (C25), S− → T_SN (C27), yıldız → "
                 "T_YILDIZ (C29).",
                 "Burgulu çifti kablo bağıyla şönt altlığına tuttur."],
         "kontrol": ["Kart C25 ↔ YÜK 1 jakı: ötmeli. Kart C27 ↔ YÜK 2: ötmeli.",
                     "Kart C29 ↔ COM jakı: ötmeli (yıldız = kart GND).",
                     "YÜK 1 ↔ COM: <b>ötmemeli</b> (şönt ile ayrılır; 15 mΩ ötmeyi tetiklemez)."]},
    ]},
    {"no": 8, "baslik": "Pil testi yolu — Q1 ve PİL jakları", "alt": [
        {"no": "8.1", "baslik": "Q1'i yük yoluna bağla", "tur": "kablo", "kablo": [7, 8, 9],
         "vurgu": ["Q1", "J7.1", "J7.2", "RS"],
         "yap": ["Q1'in <b>kaynağı</b> → şöntün RS.1 bacağı (YÜK 1 ile aynı nokta).",
                 "PİL 1 jakı → Q1'in <b>savağı</b>. PİL 2 jakı → şöntün RS.2 bacağı.",
                 "Üçü de kalın kablo, halka pabuç."],
         "kontrol": ["PİL 2 ↔ YÜK 2: ötmeli (ikisi de RS.2).",
                     "PİL 1 ↔ YÜK 1: <b>kırmızı prob PİL 1'de</b> ölç — ötmemeli. (Ters "
                     "probda MOSFET'in gövde diyotu öter, o normal.)"]},
        {"no": "8.2", "baslik": "Kapı telini tak", "tur": "kablo", "kablo": [10], "vurgu": ["Q1"],
         "yap": ["Kartın T_KAPI telinin (Z36) ucuna erkek pin; Q1 demetinin dişi ucunu tak.",
                 "Teli Q1 bacağından ~15 mm sonra köşebende <b>kablo bağıyla</b> tut — "
                 "soğutucunun yanında silikon yok (yumuşar)."],
         "kontrol": ["Q1 kapısı ↔ kaynağı: ötmemeli.",
                     "Kapı teli soğutucuya değmiyor."]},
    ]},
    {"no": 9, "baslik": "Ölçüm girişleri", "alt": [
        {"no": "9.1", "baslik": "V ve COM jakları", "tur": "kablo", "kablo": [11, 12],
         "vurgu": ["J1.1", "J1.2"],
         "yap": ["Kartın V girişi teli (C4) → <b>V jakı</b>; COM teli (C6) → <b>COM jakı</b>. "
                 "Halka pabuç ya da jakın vidalı ucuna sar; çıplak uç kalmasın."],
         "kontrol": ["V jakı ↔ kart C4: ötmeli. COM jakı ↔ kart C6: ötmeli.",
                     "V jakı ↔ kart R8 (VREF): tabloda yazan direnç."]},
        {"no": "9.2", "baslik": "SKOP jakı", "tur": "kablo", "kablo": [17], "vurgu": ["J4.1"],
         "yap": ["Skop teli (B16) → <b>SKOP jakı</b>.",
                 "Skopun dönüşü COM jakıdır; <b>ayrı tel yok</b> (netlistteki J4.2 aynı "
                 "fiziksel jak)."],
         "kontrol": ["SKOP jakı ↔ kart B16: ötmeli.",
                     "SKOP jakı ↔ R8 (VREF): tabloda yazan direnç."]},
        {"no": "9.3", "baslik": "HV jakı ve kablo ankrajı", "tur": "kablo", "kablo": [15],
         "vurgu": ["J2.1", "B"],
         "yap": ["<b>Ön koşul:</b> Yerleşim 5.12'nin B tarafı bitmiş olmalı (B:D8'e HV "
                 "lehimi, B:O16 → A:C11 sarı tel).",
                 "HV jakı → kart B D8: <b>silikon prob kablosu</b> (KBL004; üstündeki gerilim "
                 "baskısını oku, 600 V altıysa söyle). Kısa yoldan, diğer tellere paralel "
                 "gitmesin.",
                 "Ankraj: üç çubuk parçasını üst üste yapıştırıp kart B'nin önüne, tabana dik "
                 "yapıştır (plandaki yer); HV kablosunu buna kablo bağıyla tut — çekilince "
                 "D8 lehimi değil bağ direnir.",
                 "HV'nin dönüşü de COM jakıdır; ayrı tel yok."],
         "kontrol": ["HV jakı ↔ kart B D8: ötmeli.",
                     "HV jakı ↔ R8 (VREF): tabloda yazan direnç (≈ 4.9 MΩ).",
                     "Kabloyu elle çek: kart B ve D8 lehimi oynamıyor."]},
    ]},
    {"no": 10, "baslik": "Besleme", "alt": [
        {"no": "10.1", "baslik": "XT30 kuyruğu → anahtar → iç klemens → kart", "tur": "kablo",
         "kablo": [0, 1], "vurgu": ["J6", "SW"],
         "yap": ["İçeride küçük bir <b>2'li vidalı klemens</b> (CON007): XT30 kuyruğunun yanında, "
                 "arka duvara paralel dik duran tek çubuğa (plandaki yer) vidala/yapıştır; "
                 "kartın 24 V telleri (C34 kırmızı, C36 siyah) buraya vidalanır — kart "
                 "lehim sökmeden çıkar.",
                 "Kuyruğun kırmızı ve siyah telleri <b>kaynak seçicinin (SWP2) HARİCİ uçlarına</b>; "
                 "seçicinin ortak uçları: kutup 1 → <b>AÇ/KAPA anahtarı</b> → klemensin kırmızı vidası, "
                 "kutup 2 → doğrudan klemensin siyah vidası. Seçici HARİCİ'de, PİL uçları şimdilik boş "
                 "(Adım 14).",
                 "Sigorta: kartta F1. Anahtar her açmada dolu 24 V'u 136 µF'ye bir anda uygular; "
                 "gerçek bir 50 mA <b>hızlı</b> (F) sigortayı bu darbe <b>atar</b> (darbe I²t erime "
                 "değerinin 3–5 katı — Littelfuse 217/218 veri sayfaları, denetim hesaplıyor). "
                 "Yuvada ölçtüğün 0.4 Ω, 50 mA olamaz (50 mA'lık tel 15–21 Ω okur): 0.4 Ω = "
                 "<b>400 mA</b> sınıfı, yani geçici taktığın FUS001 hâlâ yuvada. Stoktaki FUS010 "
                 "F tipi → <b>T (gecikmeli) 50 mA cam</b> al (Littelfuse 218.050 ya da ESKA/Schurter "
                 "eşdeğeri, pay ≥ 10×); gelene kadar <b>yuvadaki 400 mA (FUS001) kalsın</b> — kısa "
                 "devrede açar; stoktaki 315 mA F de darbeye pay vermiyor, değiştirmeye değmez. TL072 "
                 "kısmi arızasını hiçbir sigorta açmaz. T takılınca 20 kez aç-kapa: her açılışta "
                 "+12/−12 gelmeli."],
         "kontrol": ["Anahtar KAPALI: kuyruk ↔ kart C34 süreklilik yok; AÇIK: var.",
                     "Kuyruk siyah ↔ kart C36: ötmeli."]},
        {"no": "10.2", "baslik": "Kutuda ilk enerji + toprak kontrolü", "tur": "kontrol",
         "yap": ["Soketlerdeki entegreleri çıkar, ESP32'yi ayır, anahtar KAPALI.",
                 "Ohmmetre: kaynağın (WCT-200-24) <b>V− çıkışı ↔ fişin toprak ucu</b>: "
                 "sonsuz olmalı. Değilse kaynak topraklı demektir; kart COM'u toprağa "
                 "bağlanır (yalıtımlı kaynak ya da yalıtımlı adaptör gerekir).",
                 "Kaynağı XT30'a tak, anahtarı AÇ; kartta +12 V / −12 V'u ölç "
                 "(V35 / R33, GND: V36)."],
         "kontrol": ["+12 V: +11.5 … +12.5 V. −12 V: −11 … −13 V.",
                     "Hiçbir şey ısınmıyor."]},
    ]},
    {"no": 11, "baslik": "ESP32 ve ilk iki kapı", "alt": [
        {"no": "11.1", "baslik": "J5 kablosu ve entegreler", "tur": "montaj",
         "vurgu": ["ESP32", "A"],
         "yap": ["Soketlere entegreleri tak: U3, U4 (LM358), U5, U8 (TL072). Çentik yönü.",
                 "ADS modüllerini yuvalarına tak.",
                 "J5 başlığına 10 telli kabloyu tak (eşleme Yerleşim 1.12). "
                 "<b>3V3 ile 5V'u karıştırma.</b>",
                 "USB'yi devkit'in COM yazan soketine, arka yuvadan tak."],
         "kontrol": ["Entegre çentikleri doğru yönde.", "10 tel doğru pinde."]},
        {"no": "11.2", "baslik": "Vref ve I²C kapıları", "tur": "kapi", "kapi": [1, 2],
         "yap": ["WiFi ayarları seri konsoldan: <code>Ns&lt;web parolası&gt;</code>, "
                 "<code>Na&lt;ssid&gt;</code>, <code>Np&lt;parola&gt;</code>; durum <code>N?</code>."]},
    ]},
    {"no": 12, "baslik": "Kalibrasyon ve kalan kapılar", "alt": [
        {"no": "12.1", "baslik": "Kalibrasyon", "tur": "kalibrasyon"},
        {"no": "12.2", "baslik": "Kapı 3 — akım", "tur": "kapi", "kapi": [3],
         "yap": ["Kaynak: 12 V + 10 Ω/20 W taş direnç (≈1.2 A) YÜK 1–2'den seri; "
                 "multimetre 10 A kademesi seriye. <code>Z</code> yüksüzken, sonra "
                 "<code>i&lt;ölçülen&gt;</code>. Kabloları ters çevir: işaret değişmeli."]},
        {"no": "12.3", "baslik": "Kapı 4 — NORMAL gerilim", "tur": "kapi", "kapi": [4],
         "yap": ["<code>n</code>; V boşta <code>z</code>; 12 V'u V–COM'a ver, multimetreyle "
                 "kıyasla, <code>g&lt;ölçülen&gt;</code>; ters bağla: işaret değişmeli."]},
        {"no": "12.4", "baslik": "Kapı 5 — YÜKSEK gerilim", "tur": "kapi", "kapi": [5],
         "yap": ["<code>y</code>; önce 12 V, sonra 24 V. Kazanç kalibrasyonu ≥31 V ister: "
                 "iki kaynağı seri bağla ya da HV kazancını fabrika 1.0'da bırak (bölücü "
                 "%1 metal film, hata ≤ %1). <b>Tek el kuralı.</b>"]},
        {"no": "12.5", "baslik": "Kapı 6 — osiloskop", "tur": "kapi", "kapi": [6],
         "yap": ["Sinyal kaynağı: kartın CAL çıkışı — seri konsolda <code>X&lt;hz&gt;</code> "
                 "ile aç, <code>x</code> ile kapat; GPIO'dan SKOP–COM'a krokodille bağla. "
                 "<code>t</code> komutlarıyla yakala; kare dalga ve frekans görünmeli."]},
        {"no": "12.6", "baslik": "Kapı 7 — hızlı akım yolu", "tur": "kapi", "kapi": [7],
         "yap": ["Dirençsel yük (12 V + 10 Ω) YÜK'ten; <code>w</code> → PF ≈ 1."]},
        {"no": "12.7", "baslik": "Kapı 8 — pil testi", "tur": "kapi", "kapi": [8],
         "yap": ["Failsafe: kart kapalıyken ve RESET'te Q1 kapısı 0 V (PİL 1 ↔ PİL 2 "
                 "ötmemeli). Sonra 18650 + 3.3 Ω 11 W: <code>P2.8</code>, <code>p1</code>."]},
    ]},
    {"no": 13, "baslik": "Kapak ve son kontrol", "alt": [
        {"no": "13.1", "baslik": "Kapağı yap", "tur": "taban", "kapak": True,
         "yap": ["Kapak sıralarını taban gibi diz (ek yerleri kaydırmalı), altına iki rayı "
                 "<b>yan duvarların iç yüzüne yaslanacak</b> şekilde, direklerin arasına "
                 "yapıştır. Raylar 18 mm yüzü dik (aşağı sarkar).",
                 "Kapağı yapıştırma."],
         "kontrol": ["Kapak oturuyor, raylar yan duvarlara sürtmeden giriyor."]},
        {"no": "13.2", "baslik": "Kapağı yan duvarlardan cıvatala", "tur": "taban", "kapak": True,
         "yap": ["Kapak yerindeyken her yan duvarda iki nokta işaretle (tablo: y ve z), "
                 "Ø3.2 del — delik duvar (4 mm) + ray (2 mm) boyunca geçer.",
                 "Dört <b>{kapak_civata}</b> cıvata dıştan, pul + somun içeriden rayın "
                 "arkasına. Tak-çıkar: somunu gevşet, kapak kalkar. Tahtada diş yok."],
         "kontrol": ["Kapak elle çekince kalkmıyor; cıvatalar sökülünce tek parça çıkıyor."]},
        {"no": "13.3", "baslik": "Etiketle ve topla", "tur": "kontrol",
         "yap": ["Etiketler: YÜK 1/2, PİL 1/2, V, COM, SKOP, HV ⚡, 24 V, USB (⚡ HV varken "
                 "çıkar).",
                 "Kabloları kablo bağıyla topla; HV kablosu tek başına ve diğerlerinden "
                 "≥ 20 mm.",
                 "<b>Kutu prensibi:</b> kutunun kendi parçaları yapıştırılır; içine giren "
                 "hiçbir parça yapıştırılmaz. Başka kaba geçerken vidaları ve kablo "
                 "bağlarını sök, konnektörleri ayır."],
         "kontrol": ["Kutuyu salla: içeride oynayan bir şey yok."]},
        {"no": "13.4", "baslik": "Kapalı kutuda uçtan uca", "tur": "kapi", "kapi": [4, 3],
         "yap": ["Kapak kapalı, panelden: 12 V + 10 Ω yük YÜK'ten, V–COM 12 V'ta. Kartın "
                 "V ve I okuması multimetreyle ±%1 / ±%2 içinde; osiloskopta CAL kare "
                 "dalgası; 5 dk sonra kutu içinde ısınan yok."]},
    ]},
    {"no": 14, "baslik": "Pil bloğu I — 24 V hücresi (kart pilden çalışır; tek hücre + tek modül)", "alt": [
        {"no": "14.1", "baslik": "MT2'yi yüksüz 24.0 V'a ayarla", "tur": "montaj", "vurgu": ["MT2"],
         "yap": ["MT3608'i tezgahta, <b>yük takmadan</b> ayarla: girişe 3.7–4.2 V (hücre ya da tezgah "
                 "kaynağı), çıkışı multimetreyle izle, trimpotu saat yönü tersine çevirerek <b>24.0 V</b>. "
                 "Fabrika ayarı 28 V'a kadar çıkabilir: ayarlanmamış modülü karta bağlama.",
                 "Modülü etiketle: MT2 (24 V)."],
         "kontrol": ["MT2 çıkışı 23.8–24.2 V (giriş 3.7 V'ta da).",
                     "Girişi 3.0 V'a düşür: çıkış hâlâ ayarında (boost payı var)."]},
        {"no": "14.2", "baslik": "Yuva 2, TP2 rafı, MT2 ve seçiciyi tak", "tur": "duvar_parca",
         "monte": ["YUVA2", "TP2", "MT2", "SWP2"], "vurgu": ["YUVA2", "TP2", "MT2", "SWP2"],
         "yap": ["Arka duvar (içeriden): 18650 yuvası YUVA2 üst sıraya (konum tabloda; alttaki YUVA1 yeri "
                 "hücre 1 için boş kalır); iki M3 cıvata dıştan, somun içeriden. Üstü kapağa 2 mm.",
                 "TP4056 (TP2) <b>raf</b> gibi yatay, arka duvarın sağ ucunda: Type-C soketi ŞARJ 2 "
                 "yuvasına dayanır; kartı 3 katlı bir çubuk bloğuna (duvara yapışık, somun gömme) vidala.",
                 "MT2 arka duvarın solunda üst konuma (x 42–78, z 47); cıvata dıştan somun içeriden, trimpot "
                 "içe baksın.",
                 "Kaynak seçici SWP2 (KTS202, DPDT) ÖN duvarın 4. sırasında V jakının üstüne, somun dıştan "
                 "(AÇ/KAPA ve SWP1 toggle'larıyla aynı sıra).",
                 "Cıvata deliklerini iç kat çubuğunun olduğu yerden geçir (4.5 tablosu; şarj yuvasının altı "
                 "tek kat). Denk gelmiyorsa o noktaya içeriden 18 mm'lik çubuk parçası yapıştırıp öyle del."],
         "kontrol": ["Hücreyi tak-çıkar: yuva yerinden oynamıyor.",
                     "Kapak kapanıyor: YUVA2'nin üstü kapağa değmiyor.",
                     "Type-C fişi ŞARJ 2 yuvasından TP2'ye rahat giriyor."]},
        {"no": "14.3", "baslik": "24 V hücresini kablola", "tur": "pil_kablo", "asama": 1,
         "vurgu": ["YUVA2", "TP2", "MT2", "SWP2", "J6", "SW"],
         "yap": ["Aşağıdaki tabloya göre; hücre TAKILI DEĞİLKEN. TP4056'da hücre <b>B±</b>'ye, yük "
                 "<b>OUT±</b>'ye (koruma FET'i OUT− kolunda). Kalın kablo gerekmez (≤ 0.5 A); 0.5 mm² yeter.",
                 "<b>Kural (denetimli):</b> hücre 2'nin eksisi yalnız TP2/MT2/seçiciye gider — kart GND'ye, "
                 "ESP32'ye ASLA değmez (pil kipinde bu uç kartın −12 rayıdır).",
                 "10.1'de takılan XT30 kuyruğu seçicinin HARİCİ uçlarına, MT2 çıkışı PİL uçlarına; ortak uçlar "
                 "AÇ/KAPA anahtarına ve klemense."],
         "kontrol": ["Hücre takılı değilken: <b>H2− (TP2.B−) ↔ kart GND (C29): ÖTMEMELİ</b> — seçici "
                     "her iki konumda da.",
                     "Seçici HARİCİ: XT30 kırmızı ↔ AÇ/KAPA anahtarı girişi ötmeli; MT2.OUT+ ↔ klemens +: ötmemeli.",
                     "Seçici PİL: MT2.OUT+ ↔ AÇ/KAPA anahtarı girişi ötmeli; XT30 kırmızı ↔ klemens +: ötmemeli."]},
        {"no": "14.4", "baslik": "Pil kipinde ilk enerji", "tur": "kontrol",
         "yap": ["Hücreyi tak (kutuplara dikkat). SWP2 → <b>PİL</b>, AÇ/KAPA anahtarı AÇ: klemenste 24.0 V, "
                 "kartta +12 / −12 (V35 / R33, GND V36). ESP32 bu aşamada USB'den (PC ya da güç bankası).",
                 "Skopla −12 rayına bak (MT3608 dalgalanması, ~1 MHz): 50 mV üstü görürsen MT2 çıkışına "
                 "100 µF + 100 nF ekle (5.12.23'ün gürültü endişesi burada ölçülür)."],
         "kontrol": ["+12: +11.5…+12.5 V · −12: −11…−13 V (pilde de).",
                     "Hücre 2 eksisi ↔ kart GND arasında gerilim: <b>≈ −12 V</b> (yani ayrı düğüm — 0 V "
                     "okursan kısa var, hemen kapat).",
                     "10 dk sonra MT2 ve 7912 ılık, sıcak değil."]},
        {"no": "14.5", "baslik": "Şarj kuralı ve etiket", "tur": "kontrol",
         "yap": ["Şarj: <b>SWP2 → HARİCİ</b>, sonra Type-C tak (TP4056 yük altında şarjı bitiremez). ŞARJ 2'nin "
                 "kablosu ile ESP32'nin USB'si <b>aynı PC'ye/adaptöre takılıyken seçici PİL'e alınmaz</b> — "
                 "hücre 2 eksisi −12 rayıdır, ortak toprak −12'yi GND'ye kısa eder (parça ölmez, ölçüm "
                 "sessizce bozulur).",
                 "Etiket (arka panele): \"ŞARJ: seçici HARİCİ\". HV ölçümü pil kipinde de USB'siz: kutu "
                 "tamamen yüzer, en güvenli hal."],
         "kontrol": ["TP4056 LED'i şarjda kırmızı, bitince mavi (yuvadan görünüyor).",
                     "Pil kipinde 1 saat ölçüm: kalibrasyon değerleri harici kaynakla aynı (±%0.5)."]},
    ]},
    {"no": 15, "baslik": "Pil bloğu II — ESP32 hücresi (isteğe bağlı: kutu tamamen kablosuz)", "alt": [
        {"no": "15.1", "baslik": "MT1'i yüksüz 5.0 V'a ayarla", "tur": "montaj", "vurgu": ["MT1"],
         "yap": ["İkinci MT3608'i aynı yöntemle <b>5.0 V</b>'a ayarla; etiketle: MT1 (5 V). Ayarlanmamış "
                 "modülü ESP32'ye bağlama (28 V ESP32'yi öldürür)."],
         "kontrol": ["MT1 çıkışı 4.95–5.05 V (giriş 3.0–4.2 V'ta)."]},
        {"no": "15.2", "baslik": "Yuva 1, TP1 rafı, MT1 ve SWP1'i tak", "tur": "duvar_parca",
         "monte": ["YUVA1", "TP1", "MT1", "SWP1"], "vurgu": ["YUVA1", "TP1", "MT1", "SWP1"],
         "yap": ["Arka duvar: YUVA1 alt sıraya (ESP32'nin 6 mm üstü), TP1 rafı sol uca (ŞARJ 1 yuvası), MT1 "
                 "MT2'nin altına (x 42–78, z 24) — hepsi cıvata dıştan somun içeriden.",
                 "SWP1 toggle ÖN duvarın 4. sırasında YÜK 2 jakının üstüne."],
         "kontrol": ["Hücreyi tak-çıkar: yuva yerinden oynamıyor.", "Type-C fişi ŞARJ 1'den TP1'e giriyor."]},
        {"no": "15.3", "baslik": "ESP32 hücresini kablola", "tur": "pil_kablo", "asama": 2,
         "vurgu": ["YUVA1", "TP1", "MT1", "SWP1"],
         "yap": ["Tabloya göre; hücre takılı değilken. Hücre 1'in eksisi ESP32 GND = kart GND'ye gider (hücre "
                 "2'den farklı: bu hücre kartla ortak topraklı, şarjı her zaman güvenli).",
                 "MT1 çıkışını ESP32'nin 5V/VIN ve GND pinlerine ayrı iki dişi jumper ile tak (J5 "
                 "kablosunun 5V teline paralel olur; devkit USB ile diyot-OR yapar).",
                 "SWP1 hücre tarafında: kapalıyken MT1 hiç çekmez. USB takılıyken SWP1 KAPALI."],
         "kontrol": ["H1− (TP1.B−) ↔ kart GND (C29): ötmeli.",
                     "H1− ↔ H2− (TP2.B−): <b>ötmemeli</b> (iki hücrenin eksisi ayrı).",
                     "SWP1 kapalı: TP1.OUT+ ↔ MT1.IN+ ötmemeli; açık: ötmeli."]},
        {"no": "15.4", "baslik": "Tamamen kablosuz test", "tur": "kontrol",
         "yap": ["USB çıkar, SWP1 AÇ: ESP32 açılıyor, WiFi paneli geliyor. SWP2 PİL + AÇ/KAPA AÇ: ölçüm "
                 "pilden. Şarj için iki kural: SWP2 HARİCİ ve SWP1 KAPALI iken Type-C tak.",
                 "Etiketi güncelle: \"ŞARJ: seçici HARİCİ + PİL ESP32 kapalı\"."],
         "kontrol": ["ESP32 pilden 30 dk çalışıyor, MT1 ılık.",
                     "Hücre 1 eksisi ↔ kart GND: 0 V (aynı düğüm); hücre 2 eksisi ↔ kart GND: ≈ −12 V."]},
    ]},
]

# ── on kosullar: yerlesim planinda bitmis olmasi gerekenler ────────────
# (alt adim no, ne) — kutu.py 7-yerlesim.html'de o anchor'in varligini olcer.
ON_KOSUL = [
    ("0.9", "İlk elektrik: +12 / −12 V ölçüldü, sigorta düşümü kontrol edildi"),
    ("1.12", "J5 başlığına 10 telli ESP32 kablosu hazır (eşleme orada)"),
    ("5.12", "B tarafı: B:D8'e HV teli lehimli, B:O16 → A:C11 sarı tel bağlı"),
    ("8.6", "Kapı sürücüsü (Q2/Q3) lehimli, T_KAPI teli (Z36) çıkmış"),
]

# ── kalibrasyon (seri konsol komutlari firmware'den) ───────────────────
# 'en az' esikleri kutu.py firmware/tasarim sabitlerinden hesaplar.
KALIBRASYON = [
    ("s0.015", "Şönt değerini gir (15 mΩ)", "Bir kez. Şöntü değiştirirsen tekrar."),
    ("Z", "Akım sıfırı", "YÜK'e hiçbir şey bağlı değilken."),
    ("i&lt;amper&gt;", "Akım kazancı", "Bilinen akım geçirirken; multimetrenin okuduğunu yaz."),
    ("n", "NORMAL menzile geç", "V kanalı ±32 V."),
    ("z", "Gerilim sıfırı", "V jakı boşta iken."),
    ("g&lt;volt&gt;", "Gerilim kazancı", "Bilinen gerilimi verip multimetrenin okuduğunu yaz."),
    ("y", "YÜKSEK menzile geç", "HV kanalı; sonra tekrar z / g (eşik yüksek, aşağıya bak)."),
    ("P&lt;volt&gt;", "Pil kesme gerilimi", "Örnek: 18650 için 2.8 V."),
    ("?", "Bütün ayarları yaz", "Kalibrasyon sonunda oku, bir yere not et."),
]

# ── kullanim: neyi nereden olcerim ─────────────────────────────────────
# Menzil sayilari uretecte tasarim sabitinden yazilir ({normal}, {yuksek},
# {skop}, {akim}, {pil_akim}).
KULLANIM = [
    ("Gerilim, ≤ {normal}", "V (kırmızı) + COM (siyah)",
     "Krokodil kabloyla devreye <b>paralel</b>. Menzil: <code>n</code>.", "1.04 mV adım"),
    ("Gerilim, {yuksek}", "HV (kırmızı) + COM (siyah)",
     "Menzil: <code>y</code>. <b>Tek el kuralı.</b> USB'yi PC'ye TAKMA — WiFi paneli kullan "
     "(COM = kart GND = USB toprağı). Ölçülen devre toprağa bağlıysa (şebekeli kaynak, "
     "PC'li devre) HV'yi KULLANMA: bu kart yüzen (pil / DC-DC) devreler için.",
     "18.8 mV adım"),
    ("Akım, ≤ {akim}", "YÜK 1 – YÜK 2",
     "Devrenin dönüş hattını kes: devreden gelen uç <b>YÜK 1</b>, kaynağa giden uç "
     "<b>YÜK 2</b>. Aynı anda gerilim için yalnız <b>V jakını</b> devrenin artısına bağla; "
     "<b>COM'a krokodil TAKMA</b> — COM zaten YÜK 2'dir. COM'u devrenin eksisine (YÜK 1 "
     "tarafı) takarsan şönt baypas olur: okuma düşer, ince kablo ısınır.", "0.52 mA adım"),
    ("Güç ve enerji (W, Wh)", "V + COM ve YÜK birlikte",
     "Gerilim ve akım aynı anda bağlıysa kart gücü kendi hesaplar; reaktif yükte de doğru.",
     "işaretli, gerçek güç"),
    ("Osiloskop, {skop}", "SKOP (kırmızı) + COM",
     "Dalga şeklini görmek için. Zaman tabanı 100 µs – 500 ms/bölme. Asimetrik menzil: "
     "eksi tarafı daha geniş.", "83 kSa/s'e kadar"),
    ("Pil kipi (kutunun kendi pili)", "SWP2 → PİL, AÇ/KAPA AÇ; SWP1 → ESP32",
     "Kutu tamamen yüzer: HV ölçümü için en güvenli hal. Süre ≈ analog 6–9 sa, ESP32 ~3 sa (1500 mAh). "
     "<b>Şarj:</b> SWP2 HARİCİ + SWP1 KAPALI iken Type-C tak; ŞARJ 2 kablosu ile ESP32 USB'si aynı "
     "PC'deyken seçici PİL'e ALINMAZ (hücre 2 eksisi = −12 rayı).", "2 × 18650"),
    ("Pil kapasitesi (mAh)", "PİL 1 – PİL 2 + yük direnci + V jakı",
     "<b>Zorunlu:</b> V jakı → pil + (COM zaten pil −, ayrıca tel takma). Pil + → yük "
     "direnci → <b>PİL 1</b>; pil − → <b>PİL 2</b>. <b>YÜK boş kalsın.</b> Pil ≤ 31 V ise "
     "<code>n</code>, üstü <code>y</code>. Direnç seçimi: akım = pil V ÷ R, sınır "
     "{pil_akim} A — 3.7 V 18650 için 3.3 Ω 11 W (1.1 A, dirençte 4 W). "
     "<code>P&lt;kesme&gt;</code>, <code>p1</code>.", "≤ 38 V pil"),
]

# ── malzeme: stoktan cikacaklar / alinacaklar ──────────────────────────
# stok: envanter sorgusu (ad, kategori) — uretec kaydi bulursa "stoktan",
# bulamazsa "alinacak" tablosuna koyar; elle "al" yazilmaz (B50h: TO-220
# izolatoru ve 50 mA sigorta zaten stoktaydi, liste "al" diyordu).
MALZEME = [
    {"ad": "Dil basacağı çubuk", "stok": None,
     "not": "Gereken {cubuk}, elde ~{elde}; en az {eksik} al, fire payıyla {eksik_pay}"},
    {"ad": "Yük yolu için kalın kablo (≥1.5 mm²) + halka pabuç", "stok": None,
     "not": "KBL003 karışık montaj kablosunda kalın damar varsa oradan; pabuç yoksa kalaylı kanca"},
    {"ad": "50 mA 5×20 cam sigorta (hızlı, F — stoktaki)", "stok": ("50mA 5x20mm Cam Sigorta", "Sigorta"),
     "not": "Bir tanesini ölç: gerçek 50 mA telin soğuk direnci 15–21 Ω (Littelfuse 217/218); yuvadaki "
            "0.4 Ω = 400 mA (FUS001). F 50 mA anahtar darbesinde atar → aşağıdaki T tipi gelene kadar "
            "yuvadaki 400 mA kalsın (stoktaki F'lerin hiçbiri darbeye ≥3× pay vermiyor)."},
    {"ad": "50 mA T (gecikmeli) 5×20 cam sigorta, markalı", "stok": None,
     "not": "Littelfuse 218.050 / ESKA 522.5xx / Schurter; cam gövde (seramik 50 mA çok dirençli). "
            "Anahtar açılış darbesine (136 µF) ≥ 10× pay; T 63 mA da olur (daha bol pay)."},
    {"ad": "TO-220 yalıtım (mika/plastik izolatör + burç)", "stok": ("TO-220 Mika İzolatör", "Mekanik"),
     "not": "Q1'i soğutucudan yalıtmak için; plastik delikli/deliksiz izolatörler de var (MEK037–040)"},
    {"ad": "M3×10 / M3×12 vida, somun, pul", "stok": ("M3 Somun", "Mekanik"),
     "not": "Kart ayakları ×6, kapak ×4, Q1 köşebent ×1; gömme somun ×6"},
    {"ad": "2'li vidalı klemens 5 mm (24 V iç bağlantı)", "stok": ("2 Pin Klemens 5.00mm", "Konnektör"),
     "not": "Kartın 24 V telleri buraya; kart lehim sökmeden çıkar"},
    {"ad": "Dişi header (3'lü + 1'li konnektör uçları)", "stok": ("1x40 Dişi Header 180°", "Konnektör"),
     "not": "Şönt demeti ve Q1 kapı teli için kesilir"},
    {"ad": "18650 hücre ×2 (pil bloğu)", "stok": ("18650 Li-ion Şarjlı Pil 3.7V 1500mAh", "Güç Kaynağı/Pil"),
     "not": "Başlı hücre: yaylı yuvada başlık temas eder; MEK025 yalıtım contası tak"},
    {"ad": "18650 tekli yuva ×2", "stok": ("18650 Tekli Pil Yuvası", "Güç Kaynağı/Pil"),
     "not": "PWR004 (motorobit) ya da PWR007 (direnc.net); 1.1'de ölç: 77×21×21 varsayıldı"},
    {"ad": "TP4056 korumalı Type-C ×2", "stok": ("TP4056 Li-ion Şarj Devresi", "Modül"),
     "not": "Rprog 1.2 kΩ fabrika (1 A) → 1.5–1.6 kΩ ile ~0.75 A daha rahat (isteğe bağlı)"},
    {"ad": "MT3608 yükseltici ×2", "stok": ("MT3608 DC-DC Yükseltici", "Modül"),
     "not": "Biri 5.0 V (ESP32), biri 24.0 V (analog); 14.1'de yüksüz ayarlanır"},
    {"ad": "KTS202 DPDT toggle ×1 (kaynak seçici)", "stok": ("KTS202 On/Off 6 Ayak Toggle Anahtar", "Anahtar/Buton"),
     "not": "6 ayak, ON-ON; ohmmetreyle ortak ayakları bul. Toggle kılıfı MEK054 isteğe bağlı"},
    {"ad": "KTS102 toggle ×2 (AÇ/KAPA + hücre 1 anahtarı)", "stok": ("KTS102 On/Off 3 Ayak Toggle Anahtar", "Anahtar/Buton"),
     "not": "3 ayak: orta + bir uç kullanılır (ON-OFF). AÇ/KAPA anahtarı yerine (kullanıcı tercihi)"},
]
