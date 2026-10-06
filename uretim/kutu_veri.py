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
    kendi parcalari (cubuk, ayak, altlik) yapistirilir. ISTISNA (B57b,
    kullanici karari 2026-09-25): YAPISTIRMA_ISTISNA — 18650 yuvalari, gerekceli
    ve sokme yoluyla birlikte.
  * Tek kat 2 mm tahta esner ve jak somunu tutmaz: duvarlar iki kat
    (disi yatay siralar, ici dikey cubuklar), dort ic kosede direk.
  * Kapak dort M3 civatayla YAN duvarlardan kapak raylarina baglanir —
    tahtaya dis acilmaz, somunla tutulur; ayaklarda gomme somun.
  * B58 (kullanici karari 2026-09-25): kutu YALNIZ kendi pilinden calisir —
    dis besleme (XT30) yok. Iki 18650 paralel, tek TP4056, tek Type-C sarj
    girisi; analog 24 V yalitilmis B0505S uzerinden (-12 rayi kart GND'den ayri).
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
    "duvar_sira": 5,            # dis kat: 5 x 18 = 90 mm (B54: 4 sira 72 mm'de ESP32 dupont'lari
                                #  (28 mm) + iki 18650 yuvasi ust uste sigmiyordu)
    "duvar_kat": 2,             # dis yatay + ic dikey
    "direk_kat": 3,             # kose diregi 3 cubuk = 6 mm
    "kart_vida": "M3x10",       # kart -> ayak blogunun gomme somununa (6.1)
    "m3_gecme": 3.2,            # M3 gecme deligi (B57b: eskiden yuva civata kayitlarindan okunuyordu)
    # B55l: kapak rayinin gecme payi NOMINAL SIFIRDI — KR1+KR2'nin dis yuzleri
    # tam 214 = ic en, yani kapak takimi acikligin TA KENDISI kadar genisti ve
    # girmezdi. Cubuk toleransi (+-0.3 mm genislik) ve ahsabin nemle oynamasi
    # ustune binince kesin sikisirdi. Her yanda yarim milimetre iceri aliniyor.
    "kapak_ray_payi": 0.5,      # mm — her rayin dis yuzu duvardan bu kadar iceride
    "kapak_civata": "M3x12",    # yan duvardan kapak rayina, somunlu
    "kapak_civata_y": (45.0, 117.0),   # her yan duvarda iki civata (y) — yan ic kat cubugu ortasi
    "kapak_civata_z": 81.0,     # 5. siranin ortasi (kapak rayi z 72-90)
    # B55g: civatanin yolundaki HER ahsap katmani hangi alt adim deliyor.
    # 13.1 yapilamiyordu: 4.7 yalniz duvari deliyor, civatanin onundeki 2 mm'lik
    # kapak rayini delen adim YOKTU. Denetim bu sozlugu civatanin GEOMETRISIYLE
    # karsilastiriyor — katman eklenirse/cikarsa sozluk de degismek zorunda.
    "kapak_civata_delen": {"duvar": "4.7", "ray": "13.1"},
    "kapak_civata_takan": "14.2",       # civatalarin kalici takildigi alt adim
    "kapak_somun_kat": 4,       # kapak rayindaki gomme somunlu blok (4 blok x bu kadar kat, 13.1)
                                # B55e: 3 -> 4. Cep SOMUN_CEP["kat"]=2 kat oldugu icin 1+2+1.
    "kenar_payi": 10.0,         # panel deligi ile kose arasi en az
    "parca_payi": 6.0,          # ic parcalar arasi en az bosluk
    "elde_cubuk": 50,           # kullanicida su an olan (yaklasik)
    # Yapistirici secimi (B52f, kullanici: elinde japon (CA), sicak silikon, hizli yapistirici var):
    # is turune gore — uretec 'Bu belge ne' altinda tablo yapiyor, denetim adim metinlerinin
    # bu tabloyla celismedigini olcuyor.
    "yapistirici": [
        ("Lamine (üst üste) parçalar: ayak blokları, direkler, köşebent, ankraj, TP4056 rafı blokları",
         "Japon (CA, sıvı)", "Yüze ince çizgi, 30 s bastır; kelepçe gerekmez. Gömme somunun dişine "
         "damlatma — somunu kuru geçir."),
        ("Taban / kapak sıraları (uç uca ve yan yana)",
         "Maskeleme bandı + japon", "Parçaları düz zeminde dizip üstünden maskeleme bandıyla tut, derzlere "
         "ince japon süz (altına kapton/pişirme kâğıdı: masaya yapışır)."),
        ("Raylar (taban altı, kapak altı)", "Sıcak silikon",
         "Ray boyunca sürekli, ince bir çizgi; 10 s içinde bastır. Yerinde oynatma payı veren tek yapıştırıcı."),
        ("Dış kat sıraları (tabana ve birbirine)", "Japon + içeriden sıcak silikon",
         "Uçları ve ortayı japonla tuttur (hizala, 30 s bastır), sonra iç köşeye sıcak silikonla "
         "fileto çek: japon hizayı, silikon dayanımı verir."),
        ("İç kat dikey çubuklar", "Japon (üst-orta-alt üç çizgi)",
         "Sıcak silikon kalınlık yapar (iç kat 2 mm olmalı, delikler hizasız kalır); japon ince "
         "kalır. Çubuğu tek seferde doğru yere koy — kayma payı yok."),
        ("Şönt / ESP32 altlıkları (tabana)", "Sıcak silikon",
         "Kutu parçaları; sökmek gerekirse maket bıçağıyla altından kesilir."),
        # B65: kizak parcalari devkit'e DAYALI yapistiriliyor; silikon kalinlik yapar ve 0.25 mm
        # payi yer, japon ince kalir. Kagit hem payi verir hem japonu devkit'ten uzak tutar.
        ("ESP32 kızağı (yan raylar, omuz takozları — altlığın üstüne)", "Japon (CA, sıvı)",
         "Devkit yerinde ve kenarına bir kat kâğıt sarılıyken parçayı daya, damla japon, 30 s bastır. "
         "Devkit'e japon değdirme; kuruyunca kâğıdı çek."),
        # B57b: kutuya giren parcalar icin TEK istisna (YAPISTIRMA_ISTISNA).
        ("18650 yuvaları, modüller (MT1, MT2, B0505S), 680 µF, KL, sigorta şeritleri (arka duvarın iç yüzü)", "Sıcak silikon",
         "Yuvanın tabanına boydan boya iki şerit, duvara 10 s bastır; iç kat çubuklarının arasına denk "
         "gelen yerde silikonu kalın bırak (2 mm boşluğu doldurur). Japon DEĞİL: bazı yuva plastiklerini "
         "(PP) tutmaz ve ısıda gevrekleşir. Sökmek: ısı tabancası ya da izopropil alkol + maket bıçağı."),
        ("Silikon mastik (tüp, kürlenen)", "KULLANMA",
         "Yapısal değil, 24 saat kürlenir, üstüne hiçbir şey tutmaz. Yalnız ileride su/toz sızdırmazlık "
         "istersen jak somunlarının çevresine."),
        # B55l: satır FAZLA GENİŞTİ ve 6.6 ile çelişiyordu ("köşebendi tabana silikonla").
        # Isı hesabı 6.6'yı haklı çıkarıyor: köşebent–taban derzi soğutucudan 16 mm ahşap
        # ötede (R_th ≈ 444 K/W), Q1'in 1.37 W'ının %5'inden azı oraya ulaşıyor, ΔT < 1 K —
        # sıcak silikonun yumuşama noktasına (~70 °C) hiç yaklaşılmıyor. Yasak yalnız
        # soğutucunun KENDİSİNE DEĞEN yerler için geçerli.
        # B68 (kullanici 2026-09-27: "silikonlasam nasil olur, saglamlik acisindan?"): sontun kendisi
        # icin kural yoktu. Sont 9.5 A'de ~45 K isinir (B53 yuzey modeli), kapali kutuda 70 °C'yi
        # gecer: sicak silikon ~65 °C'de yumusar; ustelik 9.5 A siniri ACIK HAVADA sogumaya gore.
        ("Şöntün kendisi ve Kelvin lehimleri", "Yapıştırıcı yok — makaron + kablo bağı",
         "Şönt 9.5 A'de ~45 °C ısınır, kapalı kutuda 70 °C'yi geçer: sıcak silikon ~65 °C'de yumuşayıp "
         "akar, üstelik şöntün soğumasını keser (9.5 A sınırı açık havada soğumaya göre). 15 mΩ'a geçerken "
         "bu lehimler sökülür. Gerilmeyi kablo bağı alır (7.2: burgulu çift şönt altlığına); istersen "
         "lehimin üstüne makaron — bacağın klemense girecek alt ucu açık kalsın."),
        ("Soğutucunun kendisine değen yerler (Q1'in tabı, kapı teli, mika pul)",
         "Kablo bağı, yapıştırıcı yok",
         "Sıcak silikon soğutucunun yüzeyinde yumuşar; CA ısıda gevrekleşir. "
         "⚠ Köşebendin TABANA yapıştırılması bu yasağın DIŞINDA (6.6): o derz soğutucudan "
         "16 mm ahşap ötede, oraya ulaşan ısı 1 K'den az."),
    ],
}

# ── kutunun icindeki parcalar (taban yerlesimi) ────────────────────────
# x, y: sol-ARKA kosesi (y=0 arka duvar).  en/boy: taban izi.  yuk: en
# yuksek nokta.  tasiyici: kutunun parcasi olan altlik/ayak (kesim
# listesine girer).  nasil: sokulebilir tutturma (denetim olcuyor).
IC_PARCA = [
    # B55j ÖLÇÜLDÜ (2026-09-23): plaket 130×120 kesilmişti (plan 114.3 varsayıyordu);
    # kullanıcı fazlalığı kesip 115×115'e indirecek. Yükseklik de ölçüldü: alttaki
    # atlama telleri + üstteki parçalarla TOPLAM ~35 mm (plan 24 varsayıyordu).
    # Arka boş şerit (bos_yuk) alçak kalıyor — duvara asılı parçalar oraya sarkıyor.
    {"ref": "A", "ad": "Ana kart (45×45 delikli plaket, 115×115 kesilmiş)", "x": 13.0, "y": 12.0,
     "en": 115.0, "boy": 115.0, "yuk": 35.0, "olculdu": True, "sutun_yonu": "arka", "bos_yuk": 2.0,
     # B64 (kullanici 2026-09-27, 6.2: "kablo olan taraflar ne yone bakmali?"): yon HIC veride
     # yoktu, yalniz 6.1'de parantez icinde "telli kenar one". 270 = kart B ile ayni donus:
     # A-C sutunlari ONE, A1 on-solda. sutun_yonu 'arka' ile ayni sey — denetim ikisini ve
     # tellerin gercekten on kenarda kaldigini kart_nokta() ile olcuyor.
     "yon": 270,
     # B55j (kullanıcı kararı): kartın altındaki atlama telleri yüzünden kart
     # en az 16–17 mm yerden yüksek olmalı (tezgahta uzun M3 vidayla yapıyor).
     # Ahşap blok 4 kat (8 mm) → 9 kat (18 mm); gömme somun yine 2.–3. katta,
     # yani M3×10 vida yetmeye devam ediyor, alttaki katlar sadece yükseltiyor.
     "tasiyici": {"tip": "ayak", "adet": 4, "kat": 9, "adim": "6.1"},
     "nasil": "Dört köşede ahşap ayak bloğu (gömme M3 somunlu); plaket M3x10 vidayla "
              "ayaklara. YAPIŞTIRILMAZ — vidayı sök, kart çıkar. Telli kenarı "
              "(A–C sütunları) ÖN panele baksın."},
    {"ref": "ESP32", "ad": "ESP32-S3 devkit", "x": 139.0, "y": 2.0,
     # B55j OLCULDU (2026-09-23): genislik 27.5 (varsayim 26), boy 63 anten dahil
     # (varsayim 63 ✔), bacaklarla yukseklik ~14 — model 28 disi dupont govdesini
     # de sayiyor (14 + 14), yani tutarli.
     "en": 27.5, "boy": 63.0, "yuk": 28.0, "olculdu": True, "soket_x_ofset": 13.0, "soket_z": 7.0,
     # yuk 28: pin (9) + disi dupont govdesi (14) + tel bukumu (B54; eskiden 14 = ciplak pin ucu)
     "tasiyici": {"tip": "altlik", "adet": 2, "uzunluk": 63.0, "bolum": 2, "kanal": 9.0, "adim": "6.3",
                  # B65 (kullanici 2026-09-27: "ESP'nin bacaklarina dikkat et, USB takilirken geriye
                  # gitmemesi icin arkasinda bir yer olmali; arkasinda ~18-19 mm genis, ortalanmis anten
                  # cikintisi var"): altligin USTUNE kizak. Yan raylar = enine kesilmis serit (18 x
                  # ray_yuk x 2) uzun kenari ustunde DIK; on takozlar = ayni seritten ikiye bolunmus iki
                  # parca, anten cikintisinin IKI YANINDA kartin omuzlarina dayanir (antene degmez).
                  # Arka taraf = arka duvar (USB ucu 2 mm). Raylar kanal hizasinda BOSLUKLU: bag oradan.
                  "kizak": {"ray_yuk": 5.0,        # serit genisligi = rayin yuksekligi (altlik ustunden)
                            "ray_pay": 0.25,       # ray ile kart kenari arasi (her yan)
                            "takoz_boy": 9.0,      # iki takoz = tek 18 mm serit (fire yok)
                            "anten_en": 19.0,      # kullanici: "yaklasik 18-19 mm", ortalanmis
                            "anten_pay": 1.5,      # takoz ile anten cikintisi arasi (her yan)
                            # anten cikintisinin kart kenarindan tasmasi OLCULMEDI: takozlar yerinde
                            # omuza dayanarak yapistiriliyor, sayi yalniz modelin konumu. Aralik
                            # denetimde kart B'nin ayagina karsi uc uca sinaniyor.
                            "anten_cikinti": 5.0, "anten_cikinti_aralik": (3.0, 8.0)}},
     # B55l: iki altlik arasi 8 mm bosluk — kablo bagi (SRF012, 3.6 mm) oradan
     # gecip devkit'in ustunden donuyor. Once bitisikti ve bag GECEMIYORDU.
     # B55l: altlik ORTADAN BOLUNDU. Onceki hali iki bitisik tam boy cubuktu ve
     # kablo bagi ALTINDAN GECEMIYORDU (2 mm cubuga yandan delik acilamaz).
     "nasil": "Pinler yukarı, USB soketi ARKA duvara 2 mm. Altlık <b>dört parça</b>: iki sıra, "
              "her sıra ortadan bölük — aradaki <b>{kanal:.0f} mm kanal</b> kablo bağının geçtiği "
              "yer. Altlığın üstünde <b>kızak</b>: iki yanda dik raylar, anten ucunda anten çıkıntısının "
              "iki yanında omuz takozları (USB takılırken devkit öne kaçmaz), arkası duvar. Bağ kanaldan "
              "geçer, iki yandaki BOŞ pinlerin tepesinden devkit'in üstünden dolanır. Bağı kes, devkit çıkar."},
    {"ref": "RS", "ad": "5 mΩ Ø1.6 şönt (R042, 9.5 A) — 15 mΩ yedek", "x": 196.0, "y": 96.0,
     "en": 12.0, "boy": 30.0, "yuk": 14.0,
     # B54: Q1'in onunde, YUK jaklarinin (x 123/159, on duvar) 40-60 mm arkasinda. Eskiden arka-sag
     # kosedeydi (y 2): yuk kablosu 190-250 mm, 9.5 A'de ~30 mV dusum V okumasina giriyordu.
     "stok": ("5mR Type-C Şönt Direnç 9.5A", "Direnç"),
     # B55l: sont altligi da TEK PARCA tabana yapisikti ve kablo bagi altindan
     # gecemiyordu — ESP32 altligindaki kusurun birebir aynisi. Ortadan bolundu.
     "tasiyici": {"tip": "altlik", "adet": 1, "uzunluk": 30.0, "bolum": 2, "kanal": 9.0, "adim": "6.6"},
     "nasil": "Bacakları (veri sayfası: 10 mm aralık — önce bükmeden dene) <b>XP128 10 mm klemense</b> "
              "(CON064) vidalanır — klemens tek çubuk altlığa yapışık; kalın yük kabloları XP128'e girmez, "
              "yanındaki bariyer klemenste (HB950) birleşir, XP128'in her kutbuna tek köprü. Manganin U havada, altlığa değmez. Kelvin/yıldız telleri bacağa lehim (vidaya değil), "
              "demet karta KONNEKTÖRLE gelir. Vidayı gevşet, şönt çıkar: 15 mΩ (R044) ile değiştirilebilir "
              "(<code>s0.015</code>, <code>Z</code>) — ⚠ ama Kelvin/yıldız telleri bacağa LEHİMLİ (6.4): takas için üç teli "
              "söküp yeni şöntün bacaklarına, yıldızı S− ile aynı noktaya lehimlemek gerekir. Kalibrasyon için takas "
              "ZORUNLU DEĞİL, 12.2'ye bak."},
    # B55g (kullanici karari 2026-09-23): kartin YONU artik veri. Kare bir
    # plaket dort turlu takilabiliyordu ve 617 V'luk dugum (T_HV, sutun 3
    # satir 7) kartin BIR kenarinda toplanmis durumda — yani yon, kutudaki
    # en yuksek gerilimin nereye bakacagini belirliyor. Ayaklar 6.1'de tabana
    # YAPISTIRILDIGI icin bu secim geri donulemez, ama hicbir yerde yaziliyordu.
    # 270 derece dort yonelim icinde ikisini birden kazaniyor: HV dugumunun en
    # yakin iletkene mesafesi en buyuk (30.2 mm; digerleri 16.0-21.6) VE HV
    # kablosu en kisa (73.8 mm; digerleri 88-101). Denetim ikisini de olcuyor
    # ve secilen yonun her iki olcutte de en iyi oldugunu sinar — olcutler
    # ileride ayrisirsa kirmiziya doner ve karar yeniden sorulur.
    {"ref": "B", "ad": "HV zinciri kartı (5×5 cm)", "x": 140.0, "y": 72.0,
     # B55j ÖLÇÜLDÜ (2026-09-23): plaket kenarlar dahil TAM 50×50 (fabrika 5×5 cm,
     # kesilmiyor). Model 45.7 diyordu — o DELİK ALANI (18×2.54), gövde değil.
     # x/y delik ızgarasının çıpası olarak kaldı; gövde `tasma` kadar dışarı taşıyor.
     "en": 45.7, "boy": 45.7, "tasma": 2.15, "olculdu": True, "yuk": 16.0, "yon": 270,
     "tasiyici": {"tip": "ayak", "adet": 2, "kat": 4, "adim": "6.1"},
     "nasil": "İki ahşap ayak (gömme somunlu) + M3 vida. <b>YÖN ÖNEMLİ:</b> {yon_b} kutunun "
              "o köşesine baksın. Bu yönde 617 V'luk düğüm kutudaki her iletkenden en uzak ve "
              "HV kablosu ({hv_kablo}) en kısa. Sökülebilir."},
    {"ref": "Q1", "ad": "IRFZ44N + soğutucu", "x": 196.0, "y": 44.0,
     "en": 15.0, "boy": 40.0, "yuk": 42.0,
     "stok": ("IRFZ44N", "MOSFET"),
     # B55m: sogutucu hicbir yerde tanimli degildi — malzeme listesinde satiri,
     # stok kaydi ve olcusu yoktu. Elde MEK002 "Sogutucu Blok (muhtelif
     # boyutlarda)" var ama olculeri KAYITTA YOK; plan 15 x 40 x 42 VARSAYIYOR.
     "sogutucu_stok": ("Soğutucu Blok", "Mekanik"), "sogutucu_olcu_varsayim": True,
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
    # B58: "24 V klemens cubugu" (tabanda, arka duvara paralel) KALKTI. TP4056
    # rafi SARJ yuvasinin arkasina (x 53.5) gelince alt sirada TP1 + F1P + cubuk
    # + ESP32 sigmiyordu (68.5 mm'ye 73 mm is). Klemens artik duvar parcasi (KL).
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
    {"ref": "J3.1", "ad": "YÜK 1 — devrenin eksisi", "tip": "jak", "x": 143.0, "z": 9.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "yesil",
     "parca": ("4mm Born Jak Şeffaf Yeşil (Büyük Boy)", "Konnektör"),
     "etiket": "YÜK 1", "alt_etiket": "yükün −",
     "not": "Akım buradan girer: ölçülen yükün EKSİ ucu. Yükün + ucu kutuya gelmez, doğrudan kaynağın +'sına.",
     "neden": "Yük akımının GİRDİĞİ uç (11.5 A'e kadar): büyük boy jak 15 A taşır, küçük vidalı jak taşımaz. YEŞİL (B60): bütün jaklar tek model (büyük şeffaf) ve stoktaki siyahlar COM ile CAL'e gitti; YÜK çifti tek renk kalsın diye yeşil ×2. Kart akımı hep devrenin eksi/dönüş tarafından ölçer. Bariyer klemens (CON012) PCB tipiydi, panele vidalanamadı."},
    {"ref": "J3.2", "ad": "YÜK 2 — kaynağın eksisi", "tip": "jak", "x": 179.0, "z": 9.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "yesil",
     "parca": ("4mm Born Jak Şeffaf Yeşil (Büyük Boy)", "Konnektör"),
     "etiket": "YÜK 2", "alt_etiket": "kaynağın −", "not": "Kaynağın EKSİ ucu. Şöntün alt bacağı = kart GND = COM.",
     "neden": "Yük akımının ÇIKTIĞI uç; şöntün alt bacağı = kart GND = COM. İki jak olması şart: akım şöntten SERİ geçmeli."},
    {"ref": "J7.1", "ad": "PİL 1 — yük direncinin ucu", "tip": "jak", "x": 35.0, "z": 9.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "mavi",
     "parca": ("4mm Born Jak Şeffaf Mavi (Büyük Boy)", "Konnektör"),
     "etiket": "PİL 1", "alt_etiket": "direnç ← pil +",
     "not": "Q1'in savağı. Pilin + ucu buraya DİRENÇ ÜSTÜNDEN gelir (pil + → direnç → PİL 1); ayrıca pil + → V.",
     "neden": "Pil deşarj yolu (Q1 savağı, 6.5 A'e kadar): büyük boy jak. MAVİ, YÜK'ten ayırt edilsin diye — karıştırılırsa pil kesmesi çalışmaz."},
    {"ref": "J7.2", "ad": "PİL 2 — pilin eksisi", "tip": "jak", "x": 71.0, "z": 9.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "mavi",
     "parca": ("4mm Born Jak Şeffaf Mavi (Büyük Boy)", "Konnektör"),
     "etiket": "PİL 2", "alt_etiket": "pil −", "not": "Pilin EKSİ ucu. YÜK 2 ile aynı düğüm (şönt altı).",
     "neden": "Pil eksisi = şönt altı = COM ile aynı düğüm; mavi çiftin ikinci ucu."},
    {"ref": "J1.1", "ad": "V girişi", "tip": "jak", "x": 143.0, "z": 45.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Şeffaf Kırmızı (Büyük Boy)", "Konnektör"),
     "etiket": "V", "menzil": "normal", "not": "NORMAL gerilim kanalı.",
     "neden": "Gerilim girişi: yüksek empedans (227 kΩ, akım yok) — akım için değil GÖRÜNÜŞ için büyük: B60'tan beri panelde tek jak modeli var. KIRMIZI = ölçüm artısı."},
    {"ref": "J1.2", "ad": "COM (ortak)", "tip": "jak", "x": 107.0, "z": 45.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "siyah",
     "parca": ("4mm Born Jak Şeffaf Siyah (Büyük Boy)", "Konnektör"),
     "etiket": "COM", "alt_etiket": "= YÜK 2 = PİL 2",
     "not": "TEK COM: V, HV ve SKOP'un ortak ucu; içeride YÜK 2 ve PİL 2 ile aynı düğüm.",
     "neden": "TEK COM: V, HV ve SKOP'un ortak eksisi; içeride YÜK 2 / PİL 2 ile aynı düğüm. Tek jak olması bilerek — ikinci bir COM olsaydı şönt baypas edilebilirdi."},
    {"ref": "J4.1", "ad": "Osiloskop girişi", "tip": "jak", "x": 179.0, "z": 81.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Şeffaf Kırmızı (Büyük Boy)", "Konnektör"),
     "etiket": "SKOP", "menzil": "skop", "not": "Dalga şekli kanalı.",
     "neden": "Osiloskop girişi: 103 kΩ, akım yok → kırmızı; B60'tan beri öbür jaklarla aynı model (büyük şeffaf)."},
    # B58 (kullanici karari 2026-09-25): kaynak secici (SWP2, KTS202) KALKTI — dis
    # besleme yok. B58e (kullanici karari): ANALOG anahtari da KALKTI — kutunun TEK
    # anahtari PIL. B59 (kullanici karari 2026-09-26): sol ustte, GUC lambasinin yaninda;
    # panelde buyuk "AC / KAPA" yazar, altinda kucuk "PIL" — metinler onu "PIL anahtari" diye
    # aniyor (35 yer), iki ad ayni anahtari gostersin.
    {"ref": "SWP1", "ad": "PİL anahtarı (kutunun tek AÇ/KAPA'sı)", "tip": "anahtar", "x": 35.0, "z": 81.0,
     "delik_mm": 6.0, "metal_mm": 12.0, "derin_mm": 15.0, "renk": "gri",
     "parca": ("KTS102 On/Off 3 Ayak Toggle Anahtar", "Anahtar/Buton"),
     "etiket": "AÇ / KAPA", "alt_etiket": "PİL",
     "not": "KTS102: paket (TP4056 OUT+) → MT1. Açınca ESP32 ve ölçüm tarafı (±12 V) birlikte açılır; "
            "kapalıyken kutu tamamen enerjisiz ve MT1 hiç çekmez. Şarj ederken KAPALI; USB'yi PC'ye "
            "takarken AÇIK (yükü pil taşır). Sol üstte, GÜÇ lambasının yanında: kutuyu açan el ilk oraya gider. "
            "Panelde büyük \"AÇ / KAPA\", altında küçük \"PİL\" yazar — metinlerdeki PİL anahtarı bu.",
     "neden": "Kutunun tek anahtarı: paketi 5 V yükselticiye bağlar. Paket tarafında olmalı — MT3608 "
              "boşta 1–4 mA çekip paketi haftalarda bitirir. KTS102 tek kutup yeter: eksi hat ortak, "
              "kesilmesi gerekmiyor."},
    {"ref": "CAL", "ad": "CAL kare dalga çıkışı (ESP32 GPIO10, seri dirençli)", "tip": "jak", "x": 143.0, "z": 81.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "siyah",
     "parca": ("4mm Born Jak Şeffaf Siyah (Büyük Boy)", "Konnektör"),
     "etiket": "CAL", "alt_etiket": "→ SKOP'a kısa kablo",
     "not": "Kartın test sinyali (X<hz> ile açılır) kapak KAPALIYKEN de dışarıdan alınsın diye: skop kapısı "
            "(12.5) ve kapalı-kutu testi (14.3) CAL → SKOP kısa patch kablosuyla yapılır. GPIO10 J5'te "
            "yok; devkit'ten tek dişi jumper + {cal_r} seri. ⚠ Bu direnç panelin TEK korumasız GPIO "
            "ucunu koruyor: komşuları {cal_komsu} ({cal_pay:.0f} mm), yanlış deliğe giren bir kablo en fazla "
            "{cal_tehdit:.0f} V getirir ve hem GPIO10'u hem +3V3 rayındaki İKİ ADS1115'i vurabilir — "
            "{cal_r} bunu sınırlıyor. HV'nin komşusu DEĞİL (bilerek).",
     "neden": "B60 (kullanıcı kararı, alım yok): CAL SİYAH büyük jak — stokta her renkten 2 var, sarı HV'ye "
              "ayrıldı. COM ile karışabilir ama ZARARSIZ: CAL'e takılan COM kablosu ölçümü çalıştırmaz, "
              "{cal_r} bir şeyi yakmaz. "
              "B59'da sağ üste, SKOP'un yanına ve V'nin üstüne çıktı: CAL → SKOP patch kablosu kısa. "
              "Kullanıcının görselinde HV'nin tam üstündeydi — bir HV ucu (614 V) yanlışlıkla CAL'e girse "
              "{cal_r}'dan ~28 mA akar, GPIO'yu ve iki ADS'yi öldürür; SKOP ile yer değiştirdi. Komşuları "
              "{cal_komsu}, en yakını {cal_pay:.0f} mm."},
    {"ref": "LED1", "ad": "GÜÇ lambası — analog raylar ayakta", "tip": "led", "x": 71.0, "z": 81.0,
     "delik_mm": 5.0, "metal_mm": 5.0, "derin_mm": 12.0, "renk": "yesil",
     "parca": ("5mm LED Yeşil (şeffaf)", "LED"),
     "etiket": "GÜÇ", "alt_etiket": "±12 V var",
     "bagli": ("KL.+", "KART_GND"),     # ARTI ucu +12 rayi (klemens +), donusu kart GND
     "not": "PASİF: ESP32'ye bağlı DEĞİL, firmware gerektirmez. +12 rayı ile kart GND arasında "
            "10 kΩ seri direnç (R060) + 5 mm yeşil LED (LED003) — PİL anahtarının ve F0'ın ardında olduğu için "
            "yalnız kart gerçekten enerjiliyken yanar. ESP32 ölü olsa da yanar; F1 atmışsa sönük kalır.",
     "neden": "Kartın enerjili olup olmadığının TEK görsel cevabı. +12 rayında olmak zorunda: akım GND'ye "
              "GİRER, yani 7912'nin çekmek üzere tasarlandığı yön. GND ile −12 arasına konsaydı "
              "regülatörden akım VERMESİ istenirdi, 79xx veremez. ESP32'nin sürdüğü bir gösterge, ESP32 "
              "USB'deyken analog kapalıysa 'hazır' diye yalan söylerdi — bu yüzden pasif."},
    {"ref": "J2.1", "ad": "YÜKSEK gerilim girişi", "tip": "jak", "x": 179.0, "z": 45.0,
     "delik_mm": 8.0, "metal_mm": 14.0, "derin_mm": 15.0, "renk": "sari",
     "parca": ("4mm Born Jak Şeffaf Sarı (Büyük Boy)", "Konnektör"),
     "etiket": "HV ⚡", "menzil": "yuksek",
     "not": "Sağ kenarda, orta sırada: COM · V · HV — ölçüm probu COM'un yanından alınır. İşaretli; "
            "arka ucu makaronla kaplanır. Komşusunda CAL yok (bilerek).",
     "neden": "614 V'a kadar giriş: büyük boy jakın gövdesi/yalıtımı daha uzun, sağ kenarda ve öbür metalden ≥ 12.6 mm kaçak yolu (IEC 60664 takviyeli). Kutudaki TEK SARI jak (B60): bütün jaklar aynı model olunca 'tek büyük kırmızı' ipucu kalktı, renk onun yerini aldı. Yanlışlıkla V'ye takılan 615 V R4'ü zamanla yakar (B15/A1) — HV'nin rengini başka hiçbir jak kullanmaz (denetimli). İç ucu makaronla."},
]

PANEL_ARKA = [
    # B58 (kullanici karari 2026-09-25): TEK sarj girisi. Iki hucre PARALEL, tek
    # TP4056; XT30 kuyrugu (dis besleme) ve ikinci sarj yuvasi KALKTI. Yuva USB
    # yuvasinin tam aynasinda (x 214-152 = 62, ayni z): arka yuz simetrik kalir.
    {"ref": "SARJ", "ad": "Şarj girişi — TP4056 Type-C (iki hücre birlikte)", "tip": "yuva", "x": 62.0, "z": 8.0,
     "delik_mm": 9.0, "yuva_en_mm": 14.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri",
     "parca": None, "etiket": "ŞARJ", "alt_etiket": "PİL kapalıyken",
     "not": "TP1 rafının Type-C soketi bu yuvadan bakar; iki hücre paralel, tek kabloyla birlikte dolar. "
            "Paketin eksisi kart GND: şarj kablosu COM'u (ölçülen devrenin referansı) şarj cihazının "
            "toprağına bağlar — şarj ederken ölçüm yapma, HV'de asla. USB yuvasının aynası.",
     "neden": "Tek şarj girişi (B58): analog 24 V artık yalıtılmış B0505S'ten geldiği için paketin eksisi "
              "−12 rayına değmiyor, tek USB toprağı hiçbir şeyi kısa etmiyor. Eskiden iki hücre ayrı "
              "topraklıydı ve iki Type-C gerekiyordu."},

    # B57b: YUVA1/YUVA2'nin dort M3 civata deligi (C1a, C1b, C2a, C2b) kalkti —
    # yuvalar artik yapistiriliyor (YAPISTIRMA_ISTISNA). Arka yuzun simetri
    # istisnalari yalniz bunlardi, arka yuz simdi TAMAMEN simetrik.
    # ── havalandirma (B55e, kullanici karari 2026-09-23: secenek A) ──────
    # Iki 18650 kapali ahsap kutuda SARJ oluyordu ve tek delik yoktu. Bir hucre
    # termal kacaga girerse 1-3 L gaz saliyor; serbest ic hacim ~2.5 L -> ~+1 bar
    # -> kapaga ~3.3 kN. Olasilik dusuk, sonuc yuksek; onlem bedava (havya + Ø5).
    # Konumlar iki kosula gore secildi: (1) ust delikler 18650 yuvalarinin ORTTUGU
    # x 92-172 seridinin disinda (yuva duvara yapisik, deligi kapatirdi),
    # (2) hepsi ic kat cubugunun ortasina denk geliyor (ek yerine degil).
    # Gaz yukari cikar: 5. sirada iki cikis, 1. sirada iki giris (capraz akis).
    # B56 (2026-09-24): konumlar SIMETRIK cifte cevrildi. Eski dagilim
    # (63,81) (81,63) (81,27) (117,9) dort ayri x ve dort ayri z kullaniyordu —
    # kullanici arka yuzu "asimetrik ve hos degil" buldu. Yeni kural: iki ayna
    # cifti, (x, ic_en - x). Simetrik cift olabilecek x'ler kisitli: yuvalarin
    # orttugu 92-172 seridinin DISINDA hem x hem 214-x kalmali, yani x <= 42
    # (aynasi >= 172) ya da x >= 172. Ustte F2/TP2/F0B, altta F1P/F2/USB/J6
    # bloklari kalani eliyor; kalan cift program aramasiyla bulundu.
    {"ref": "HV1", "ad": "Havalandırma — üst sol (çıkış)", "tip": "havalandirma", "x": 12.5, "z": 81.0,
     "delik_mm": 5.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri", "parca": None,
     "etiket": "≋", "alt_etiket": "havalandırma",
     "not": "Üst sıranın sol ucunda; HV2'nin aynası. Hiçbir parça kapatmıyor (YUVA2 x 92'den başlar, B0505S z 57'de biter).",
     "neden": "Li-ion termal kaçağında gaz basınç yapmadan çıksın diye; kapak 4 cıvatayla sıkılı ve kutu 2.5 L. Üst sıra: gaz yukarı çıkar. {konum}."},
    {"ref": "HV2", "ad": "Havalandırma — üst sağ (çıkış)", "tip": "havalandirma", "x": 201.5, "z": 81.0,
     "delik_mm": 5.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri", "parca": None,
     "etiket": "≋", "alt_etiket": "havalandırma",
     "not": "Üst sıranın sağ ucunda, HV1 ile tam simetrik; F2 (z 0–10) çok altta kalıyor.",
     "neden": "İkinci çıkış: tek delik tıkanırsa (toz, kablo) basınç yolu kapanmasın. HV1'in karşı ucunda — aynı engel ikisini birden kapatamaz. {konum}."},
    {"ref": "HV3", "ad": "Havalandırma — alt sol (giriş)", "tip": "havalandirma", "x": 80.0, "z": 27.0,
     "delik_mm": 5.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri", "parca": None,
     "etiket": "≋", "alt_etiket": "havalandırma",
     "not": "Alt yarıda, ŞARJ yuvasının (x 62) sağında ve F1P'nin (z 0–10) üstünde; HV4'ün aynası.",
     "neden": "Alt giriş: gaz tahliyesinde üst deliklerin hava alabilmesi için karşı açıklık şart, yoksa basınç yolu tek delikte tıkanır. ⚠ ISIL gerekçe DEĞİL — baca akışı hesaplandı, ΔT 10 K'de 0.19 L/dk = 36 mW, duvarların attığı ısının %1'i. {konum}."},
    {"ref": "HV4", "ad": "Havalandırma — alt sağ (giriş)", "tip": "havalandirma", "x": 134.0, "z": 27.0,
     "delik_mm": 5.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri", "parca": None,
     "etiket": "≋", "alt_etiket": "havalandırma",
     "not": "En alt sırada, USB yuvasının (x 145–159) sağında; F2 x 177'den başlıyor. HV3'ün aynası.",
     "neden": "İkinci giriş, ilkinin karşı ucunda: tek delik tıkanırsa (toz, kablo) alt açıklık kalsın. Dört delik iki ayna çifti oluşturuyor, akış çaprazlama. {konum}."},

    {"ref": "USB", "ad": "ESP32 USB yuvası", "tip": "yuva", "x": 152.0, "z": 8.0,
     "delik_mm": 9.0, "yuva_en_mm": 14.0, "metal_mm": 0.0, "derin_mm": 0.0, "renk": "gri",
     "parca": None, "etiket": "USB", "alt_etiket": "⚡ HV ölçerken çıkar",
     "not": "14 × 9 mm oval yuva; devkit'in COM yazan Type-C soketi buraya bakar.",
     "neden": "Kendi parçası yok: ESP32 devkit'in COM yazan Type-C soketi duvarın 2 mm içinde; fiş bu yuvadan geçer. Oval 14 × 9: Type-C fişin plastik gövdesi ~12 × 6.5."},
]

# ── duvara asili parcalar: pil blogu (B52) ────────────────────────────
# duvar: "arka" (y=0 yuzu) ya da "ön" (y=ic_boy).  x/z: sol-alt kose (ic
# koordinat, onden bakinca; arka duvar cizimi aynalanir).  derin: kutunun
# icine uzanan derinlik.  Neden burasi: zeminde 77x21 yuvaya yer yok; sol
# duvarda A'nin ustu (32) + pay + yuva (21) kapak rayina (54) sigmiyor;
# arka duvarin ESP32/sont bolgesi (x>127, z>16) ve A'nin ustu (z>38, ince
# parcalar A'nin arka kenari y=12'den once) uyuyor.
DUVAR_PARCA = [
    {"ref": "YUVA1", "ad": "18650 yuvası — hücre 1 (paket, paralel)", "duvar": "arka", "x": 92.0, "z": 36.0,
     "en": 80.0, "yuk": 21.0, "derin": 21.0, "stok": ("18650 Tekli Pil Yuvası", "Güç Kaynağı/Pil"),
     "nasil": "80 × 21 × 21 (ölçüldü). Arka duvarın iç yüzüne SICAK SİLİKONLA yapıştırılır (kullanıcı "
              "kararı 2026-09-25, cıvata yok): yuvanın tabanına boydan boya iki şerit, duvara 10 s bastır. "
              "Sökülebilir: ısı tabancasıyla ısıt ya da derze izopropil alkol damlat, maket bıçağıyla kaldır. "
              "Hücre yuvadan çıkar. Hücre başlı (PWR005) — yaylı yuvada başlık temas eder; yalıtım contası "
              "MEK025."},
    {"ref": "YUVA2", "ad": "18650 yuvası — hücre 2 (paket, paralel)", "duvar": "arka", "x": 92.0, "z": 63.0,
     "en": 80.0, "yuk": 21.0, "derin": 21.0, "stok": ("18650 Tekli Pil Yuvası", "Güç Kaynağı/Pil"),
     "nasil": "YUVA1 ile aynı: arka duvarın iç yüzüne SICAK SİLİKONLA yapıştırılır, cıvata yok. "
              "Sökülebilir: ısı tabancası ya da izopropil alkol, maket bıçağıyla kaldır. Yuva 21 mm "
              "(ölçüldü); üstünde kapağa pay kalır, 10.2 kontrol eder."},
    # B58: tek TP4056 (iki hucre paralel). Raf arka duvarin EN ALT sirasinda,
    # soketi SARJ yuvasina (USB'nin aynasi, z 8) bakiyor: 2 katli blok (z 0-4) +
    # modul (z 4-9); soket merkezi yuvanin icinde.
    {"ref": "TP1", "ad": "TP4056 şarj modülü — paket (raf)", "duvar": "arka", "x": 53.5, "z": 4.0,
     "en": 17.0, "yuk": 5.0, "derin": 25.0, "stok": ("TP4056 Li-ion Şarj Devresi", "Modül"),
     # B58d: modul kart A'nin arka BOS seridinin (y 12-29.8) ALTINDA, kart tabanina 9 mm.
     # Kart takilinca ne yerine indirilebiliyor ne uc pedlerine havya giriyor -> 6.0'da,
     # kart A'dan ONCE, kablolari tezgahta lehimlenmis olarak takiliyor.
     "nasil": "Kart RAF gibi yatay (27 × 17 × 5 ölçüldü, soket kart kenarından 2 mm dışarı): soket "
              "ŞARJ yuvasına girer. Kart A'nın arka boş şeridinin ALTINDA kalır — bu yüzden kart A'dan "
              "önce (6.0), kabloları tezgahta lehimlenmiş olarak takılır. Kanallı 4 parçalı çubuk rafının "
              "üstüne oturur, uzak kenarı dayanağa yaslanır; tek kablo bağı kanaldan geçip modülün "
              "ortasını sarar. Modülde montaj deliği yok, vida yok. Sökülebilir: kart A'yı 4 vidasından "
              "kaldır, bağı kes."},
    # B58e: x 42 -> 43, F0 sol uca (x 12) sigsin diye (direge ve MT1'e 6'sar mm).
    {"ref": "MT1", "ad": "MT3608 — 5.0 V (ESP32)", "duvar": "arka", "x": 43.0, "z": 24.0,
     "en": 36.0, "yuk": 17.0, "derin": 14.0, "stok": ("MT3608 DC-DC Yükseltici", "Modül"),
     "nasil": "Arka duvarın iç yüzüne düz (A'nın boş arka şeridinin üstü), sıcak silikonla — PCB'nin arkasından, çipin ve bobinin üstüne değil. OUT pedleri SOLA (F0 ve B0505S). Trimpot içe bakar, ayar kapak açıkken. Derze izopropil alkol damlatıp plastik kartla kaldırarak sökülür."},
    # B55m: hucre kolu sigortalarinin (B55k'da eklendi) kutuda YERI YOKTU —
    # kablo listesinde, PIL_IC_BAG'da ve iki adim metninde vardilar ama hicbir
    # geometrik listede degillerdi: konum, cakisma, kutle, kesim hepsi gormuyordu.
    # PCB klipsli 5x20 yuva ~25 x 10 x 10 mm; her biri kendi TP4056 rafinin altina.
    {"ref": "F1P", "ad": "Hücre 1 sigorta yuvası (5×20 PCB klipsli)", "duvar": "arka",
     "x": 77.0, "z": 0.0, "en": 25.0, "yuk": 10.0, "derin": 10.0,
     "stok": ("5x20mm PCB Klipsli Sigorta Yuvası", "Sigorta"),
     "nasil": "Arka duvarın en alt sırasına, TP4056 rafının sağına (konum listesinde): iki klips + en fazla 25 mm'lik plaket şeridi, arkasından sıcak silikonla. Sigorta içe çekilerek değişir. İzopropil alkolle sökülür."},
    {"ref": "F2", "ad": "Hücre 2 sigorta yuvası (5×20 PCB klipsli)", "duvar": "arka",
     "x": 177.0, "z": 0.0, "en": 25.0, "yuk": 10.0, "derin": 10.0,
     "stok": ("5x20mm PCB Klipsli Sigorta Yuvası", "Sigorta"),
     "nasil": "Arka duvarın SAĞ ALT köşesine, en alt sıraya, aynı yöntemle (klips şeridi, sıcak silikon). Çıkışı arka duvar boyunca F1P'nin çıkış klipsine (= TP4056 B+). İzopropil alkolle sökülür."},
    {"ref": "MT2", "ad": "MT3608 — 24.0 V (analog ray)", "duvar": "arka", "x": 43.0, "z": 47.0,
     "en": 36.0, "yuk": 17.0, "derin": 14.0, "stok": ("MT3608 DC-DC Yükseltici", "Modül"),
     "nasil": "MT1'in üstüne, aynı yöntemle (sıcak silikon, PCB'nin arkasından); IN pedleri SOLA (B0505S ve 680 µF). Girişi B0505S'in yalıtılmış 5 V'u, çıkışı 24 V iç klemensine. İzopropil alkolle sökülür."},
    # B58 (kullanici karari 2026-09-25): analog 24 V'un YALITIM parcasi. Paketin
    # eksisi kart GND, kartin -12 rayi bu modulun OBUR tarafinda; ikisini ayiran
    # TEK parca bu. B58b: kullanicinin aldigi Hi-Link B0505S-2WR3, govde 19.5 x 7 x
    # 10 mm (1 W surumu 11.6 mm idi); bacaklara tel lehimlenip makaronla kaplanir. 2026-09-28
    # GELDI (MOD013): 'alinacak' anahtari kalkti, envanter sorgusu tasiyor (kutu.py B0505S iddiasi).
    # B58f: YALNIZ 2 W. 1 W duragan yuke (%73) yetiyordu ama ACILISTA yetmiyor: akim sinirli
    # modul MT2'nin girisini UVLO'ya (~2 V) ceker, aktarilan guc ~ I_sinir x 2 V kalir; kart
    # 24 V'ta 0.73 W istiyor -> sinir >= 0.35 A (1 W'ta anmanin 1.8 kati). sim3_kutu_besleme.py.
    {"ref": "IZ", "ad": "B0505S yalıtılmış DC-DC (5 V → 5 V, 2 W)", "duvar": "arka",
     "x": 14.0, "z": 47.0, "en": 20.0, "yuk": 10.0, "derin": 7.0,
     "stok": ("B0505S-2WR3", "Modül"),
     "nasil": "MT2'nin soluna, bacaklar aşağı; dört bacağına ince tel lehimli ve makaronlu. Gövdesinden sıcak silikonla duvara; izopropil alkolle sökülür. Giriş (1 +Vin, 2 −Vin) ve çıkış (4 −Vout, 6 +Vout) tarafı hiçbir telle birleşmez."},
    # B58f (benzetim): MT2'nin girisine TOPLU KONDANSATOR. MT3608'in yumusak baslamasi
    # veri sayfasinda tanimsiz; 'referans rampasi' ise MT2 acilista girisini UVLO'ya cekip
    # rampayi sifirliyor ve her dongu yalniz modulun 22 uF'sinin enerjisini tasiyor -> kart
    # ~15 V'ta TAKILIYOR (2 W'ta bile). 470 uF her modelde yetiyor (ESR 2x ile de), 220 yetmiyor.
    # Stokta 680 uF 16 V (C042). Bacaklar MT2'nin giris uclarina (B0505S'in 6/4 bacak tellerinin
    # geldigi yer) lehimlenir; govde MT2'nin ustune yatik, kablo bagiyla.
    {"ref": "CB", "ad": "MT2 giriş kondansatörü 680 µF 16 V (elektrolitik)", "duvar": "arka",
     "x": 45.0, "z": 70.0, "en": 22.0, "yuk": 10.0, "derin": 10.0,
     "stok": ('680µF 16V', "Kondansatör"),
     "nasil": "MT2'nin üstüne, yatık (gövde x yönünde), gövdesinden sıcak silikonla. Bacakları MT2'nin giriş pedlerine lehimli — ⚠ Elektrolitik: <b>şeritli bacak EKSİ</b> (MT2 IN−), uzun bacak artı (MT2 IN+). İzopropil alkol ve iki bacağın lehimi sökülerek sökülür."},
    # B58e (kullanici karari 2026-09-25): F0 panelden KUTU ICINE. Yalniz ic arizada atar
    # (B0505S, MT2, kart); panelde "F0 1A" yazisi olcum akiminin (YUK jaklari, 9.5 A'e kadar,
    # bilerek sigortasiz) korundugunu dusunduruyordu ve Ø12 delik panelin en zayif yeriydi.
    # MT1 (5 V cikisi) ile B0505S arasinda, ikisine de bitisik.
    {"ref": "F0", "ad": "Analog sigortası F0 (5×20 PCB klipsli, 1 A F)", "duvar": "arka",
     "x": 12.0, "z": 26.0, "en": 25.0, "yuk": 10.0, "derin": 10.0,
     "stok": ("5x20mm PCB Klipsli Sigorta Yuvası", "Sigorta"),
     "nasil": "Arka duvarın sol ucuna, MT1'in soluna ve B0505S'in altına (konum listesinde): iki klips + en fazla 25 mm'lik plaket şeridi (FUS009 tek gövde değil), şeridin arkasından sıcak silikonla. İçine 1 A hızlı cam sigorta (FUS003) — 10.5'e kadar TAKMA. Sigorta içe doğru çekilerek çıkar. İzopropil alkolle sökülür."},
    # B58: 24 V ic klemensi duvarda, B0505S'in USTUNDE — MT2'nin cikisina bitisik
    # (kisa 24 V kablosu), kart A'nin ustunden 10 mm yukarida.
    {"ref": "KL", "ad": "24 V iç klemens (2'li, 5 mm)", "duvar": "arka",
     "x": 20.0, "z": 63.0, "en": 16.0, "yuk": 10.0, "derin": 10.0,
     "stok": ("2 Pin Klemens 5.00mm", "Konnektör"),
     "nasil": "B0505S'in üstüne, tabanından sıcak silikonla (PCB klemensinde montaj deliği yok). Vidalar içe: 10.4'te MT2'nin çıkışı ve kartın 24 V telleri buraya vidalanır. Hangi vidanın + olduğunu kalemle yaz. İzopropil alkolle sökülür."},
]

# Duvara asili modullerin AHSAP tutuculari — kesim listesine ve kutle modeline
# buradan girer. Eskiden `kutu.py` icinde `ref.startswith("TP")` diye sabit
# kodluydu: MT3608'lerin iki yanak cubugu hicbir listede yoktu, kullanici onlari
# kesmeden 14.2'ye geliyordu (B55c). None = ahsap tutucu yok (dogrudan civatali).
DUVAR_TUTUCU = {
    "YUVA1": None,        # B57b: tutucu blok YOK — duvara yapistirilir (YAPISTIRMA_ISTISNA)
    "YUVA2": None,        # B57b: ayni
    # B58d: raf 2 kat (z 0-4). Alt kat IKI parca, aralarinda kablo bagi KANALI (ESP32 altligi
    # ile ayni yontem; eski "blokta iki delik, kisa kenarlarin disina" tarifi yapilamiyordu —
    # kisa kenarlardan biri DUVARA dayali). Dayanak: fisi takarken modulu iceri iten kuvvete
    # karsi, modulun uzak kenarinin arkasinda uzun kenari ustunde dik duran parca (z 4-9).
    # Rafin ucu y 27: kart A'nin dolu bolgesi (atlama telleri) y 29.8'den basliyor.
    "TP1": {"ad": "raf", "kanal": 9.0,
            "parcalar": [("alt kat, kanal için iki parça", 9.0, 2), ("üst kat", 27.0, 1),
                         ("dayanak, uzun kenarı üstünde dik", 5.0, 1)]},
    "MT1": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
    "MT2": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
    "F1P": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
    "F2": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
    "IZ": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
    "CB": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
    "KL": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
    "F0": None,           # B73: sicak silikon (YAPISTIRMA_ISTISNA), tutucu yok
}

# Kutuya giren, kartla ilgisi olmayan parcalarin kurallari (KART_DISI_NOTU'nun kutu esi)
KUTU_NOTU = {
    "YUVA1": "18650 yuvası; iki hücre PARALEL (B58): eksiler TP4056'nın B−'sinde birleşir = kart GND "
             "(ESP32 ile ortak). Arka duvara sıcak silikonla yapıştırılır — kutu kuralının tek istisnası "
             "(cıvata deliği yok).",
    "YUVA2": "18650 yuvası, hücre 1'e PARALEL; artısı kendi sigortasından (F2). İlk takışta iki hücrenin "
             "gerilimi ±0.1 V içinde olmalı (10.3).",
    "KL": "24 V iç klemens (CON007, 2'li 5 mm): MT2'nin 24 V çıkışı ve kartın C34 (+) / C36 (−) telleri "
          "buraya; kart lehim sökmeden çıkar. Klemens − = kartın −12 rayı: kart GND'ye hiçbir yoldan DEĞMEZ.",
    "F0": "Kutu içinde, PCB klipsli 5×20 yuva (FUS009) + 1 A hızlı (FUS003): 5 V barası → F0 → B0505S "
          "girişi. Yalnız iç arızada atar (B0505S, MT2, kart); panelde değil, çünkü ölçüm akımının "
          "(YÜK jakları, bilerek sigortasız) korunduğunu düşündürüyordu. Kartın F1'i 24 V tarafında.",
    "CAL": "CAL jakı: devkit GPIO10 → {cal_r} ({cal_stok}) → jak. Skop kapısı ve kapalı kutu "
           "testinde CAL → SKOP kısa kablo.",
    "TP1": "TP4056 korumalı (DW01+FS8205): B± pakete (iki hücre paralel), OUT± yüke. Rprog fabrika "
           "1.2 kΩ (1 A, hücre başına ~0.5 A). Yük altında şarj etme: PİL KAPALI.",
    "MT1": "MT3608 yüksüz 5.0 V'a ayarlanır (fabrika ayarı 28 V'a kadar çıkabilir — önce ayar, sonra ESP32). "
           "Çıkış 5 V barası: ESP32'nin 5V (VIN) pini ve F0 (ölçüm tarafı); devkit USB'yle diyot-OR yapar.",
    "MT2": "MT3608 yüksüz 24.0 V'a ayarlanır; girişi B0505S'in yalıtılmış 5 V'u. 24 V yükü 19–25 mA. "
           "Anahtarlama dalgalanması −12 rayında skopla ölçülecek (10.5).",
    "IZ": "B0505S-2WR3 (5 V → 5 V yalıtılmış, 2 W): kutunun İKİ TOPRAĞINI ayıran tek parça. Giriş (bacak 1 "
          "+Vin, 2 −Vin) paket/ESP32 tarafı = kart GND; çıkış (6 +Vout, 4 −Vout) MT2'ye — bacak 4 kartın −12 "
          "rayı olur (gövdede ad yazmaz, numaralar 10.1'de). İki tarafı "
          "birleştiren tek bir tel −12'yi GND'ye kısa eder. Yük {iz_yuk_w:.2f} W (%{iz_yuk:.0f}). 1 W sürümü "
          "sürekli yüke yeter ama açılışta kartı 24 V'a çıkaramayabilir (B58f benzetimi).",
    "CB": "MT2'nin giriş kondansatörü (680 µF 16 V, C042): açılışta MT2'nin çektiği tepe akımı verir; "
          "yoksa MT2 girişini B0505S'ten çökertip yeniden başlar ve kart 24 V'a çıkamayabilir (B58f). "
          "B0505S'in çıkış tarafında = −12 rayı tarafı: kart GND'ye DEĞMEZ.",
    "LED1": "GÜÇ lambası: +12 rayı (klemens +, KL.+) → 10 kΩ (R060) → LED anodu; katot kart GND'ye. PASİF — ESP32'ye bağlanmaz. Akım ~1 mA ve GND'ye GİRER (7912 çeker). LED'i −12 rayına BAĞLAMA: regülatör o yönde akım veremez. Direnci LED'in bacağına lehimle, makaronla kapat; karta dokunma.",
    "SWP1": "PİL — KTS102: paket (TP1 OUT+) → MT1. Kutunun TEK anahtarı (B58e): ESP32 ve ölçüm tarafı "
            "birlikte açılır. Şarj ederken KAPALI; USB'yi PC'ye takarken AÇIK.",
    "F1P": "Hücre 1 sigortası: PCB klipsli 5×20 yuva (FUS009) + {pil_sigorta} (FUS004), hücrenin ARTI ucunda. "
           "TP4056'nın koruması hücre ucundaki kısayı kesemez (FET B−/OUT− arasında); o yolu yalnız bu korur.",
    "F2": "Hücre 2 sigortası: F1P'nin aynısı. Paralelde her hücrenin AYRI sigortası şart — biri içeriden kısa "
          "devre olursa öbürü onu sigortasız doldurmaya çalışır.",
}

# Pil blogu ve analog besleme kablolari (B58) — kart kablolari degil
# (yerlesim3_veri.KABLOLAR'a girmez): (nereden, nereye, tur, not).
# Dugum adlari: H1±/H2± hucre uclari, F1P/F2 hucre sigortalari, TP1.B±/OUT±,
# SWP1.1/2 PIL anahtari (kutunun TEK anahtari, B58e), MT1/MT2.IN±/OUT±, F0.1/2 (kutu ici),
# IZ.IN±/OUT± (B0505S bacak 1/2 · 6/4), KL.± klemens, A.C34/C36 kart,
# ESP32.5V / ESP32.GND.
# Denetim bu listeden graf kuruyor: paketin eksisi = kart GND; -12 rayi kart
# GND'den AYRI bilesende. B0505S'in ICI grafta kenar DEGIL (yalitim) — iki
# topragi birlestiren tek bir kablo eklenirse denetim kirmizi.
PIL_KABLOLAR = [
    # B55k/B55g: her hucrenin ARTI ucu once KENDI sigortasina. TP4056'nin koruma
    # FET'i B-/OUT- arasinda; hucre ucundaki kisayi DW01A kesemez (42 A'lik yol).
    ("H1+", "F1P.1", "pil", "hücre 1 artı → kendi sigortası (yuva ucundan, kırmızı)"),
    ("F1P.2", "TP1.B+", "pil", "sigorta → TP4056 B+"),
    ("H2+", "F2.1", "pil", "hücre 2 artı → kendi sigortası (paralelde her hücrenin ayrı sigortası şart)"),
    ("F2.2", "F1P.2", "pil", "sigorta → F1P'nin çıkış klipsi = TP4056 B+ düğümü (iki hücre burada paralel)"),
    ("H1-", "TP1.B-", "pil", "hücre 1 eksi — siyah"),
    ("H2-", "TP1.B-", "pil", "hücre 2 eksi — siyah (paralel)"),
    ("TP1.OUT+", "SWP1.1", "pil", "korumalı çıkış (B+ değil!) → PİL anahtarı"),
    ("SWP1.2", "MT1.IN+", "pil", "anahtar paket tarafında: kapalıyken MT1 hiç çekmez"),
    ("TP1.OUT-", "MT1.IN-", "pil", "eksi doğrudan"),
    ("MT1.OUT+", "ESP32.5V", "sinyal", "5.0 V → devkit 5V/VIN pini (J5 kablosunun 5V teliyle çatal)"),
    ("MT1.OUT-", "ESP32.GND", "sinyal", "= kart GND (ESP32 üzerinden). Paket eksisi bu düğümde."),
    ("MT1.OUT+", "F0.1", "besleme", "5 V barası → F0 (kutu içi sigorta, 1 A)"),
    ("F0.2", "IZ.IN+", "besleme", "F0 → B0505S Vin"),
    ("MT1.OUT-", "IZ.IN-", "besleme", "B0505S GND — kart GND tarafı"),
    ("IZ.OUT+", "MT2.IN+", "besleme", "yalıtılmış 5 V (+Vo) → MT2"),
    ("IZ.OUT-", "MT2.IN-", "besleme", "yalıtılmış 0V → MT2 eksisi — bu uç −12 rayı olur, kart GND'ye DEĞMEZ"),
    # B58f: acilista MT2'nin tepe akimini veren toplu kondansator (aksi halde kart takilir)
    ("CB.+", "MT2.IN+", "besleme", "680 µF artısı (uzun bacak) → MT2 IN+ (B0505S +Vo ile aynı nokta)"),
    ("CB.-", "MT2.IN-", "besleme", "680 µF eksisi (şeritli bacak) → MT2 IN− — −12 rayı tarafı"),
    ("MT2.OUT+", "KL.+", "besleme", "24.0 V → klemens +"),
    ("MT2.OUT-", "KL.-", "besleme", "24 V eksisi → klemens −"),
    ("KL.+", "A.C34", "besleme", "klemens → kart 24 V + (T_24P)"),
    ("KL.-", "A.C36", "besleme", "klemens → kart 24 V − (T_24N = −12 rayı)"),
]
# Asama (kutu.py pil_asama): ucu SW/F0/IZ/MT2/KL/kart olan kablolar "analog"
# (10.4), digerleri "paket" (10.3).
# Modullerin ic baglantilari (grafta kisa devre sayilir): korumali TP4056'da
# OUT- ile B- koruma FET'i uzerinden ayni dugum; MT3608'de IN- = OUT-.
# ⚠ B0505S'te IN ile OUT arasinda baglanti YOK — yalitim; buraya eklenmez.
PIL_IC_BAG = [("TP1.B-", "TP1.OUT-"), ("MT1.IN-", "MT1.OUT-"), ("MT2.IN-", "MT2.OUT-"),
              # ("ESP32.GND", "KART_GND") J5 TAKILI varsayar (11.1); 10.3'te paket–GND bağı fiziksel
              # olarak YOK (B73 §4.4) — grafın "en kötü hal, her yol bağlı" ilkesi.
              ("KL.-", "-12"), ("ESP32.GND", "KART_GND"),
              ("F0.1", "F0.2"), ("F2.1", "F2.2"), ("F1P.1", "F1P.2")]   # sigortalar (takili)
# Anahtarlar: grafta varsayilan KAPALI (en kotu hal — her yol bagli). Denetim
# tek tek acip kestikleri yolu da olcuyor.
PIL_ANAHTAR = {"SWP1": ("SWP1.1", "SWP1.2")}     # B58e: ANALOG anahtari (SW) kalkti

# ── B73 · kablo guzergahi (8-kutu.html'de cizim + 3B) ──────────────────────
# Uc ofsetleri parcanin KENDI kosesine gore (dx, dy, dz) mm; duvar parcasinda dy = on yuz.
# OLCULMEDI — modul fotografi / veri sayfasindan TAHMIN (±3 mm): cizim yon ve sira
# gosterir, milimetrik lehim yeri degil. Kart notu bunu soyler.
KABLO_UCLARI = {
    "MT1": {"OUT+": (2.0, 14.0, 12.0), "OUT-": (2.0, 14.0, 5.0), "IN+": (34.0, 14.0, 12.0), "IN-": (34.0, 14.0, 5.0)},
    "MT2": {"IN+": (2.0, 14.0, 12.0), "IN-": (2.0, 14.0, 5.0), "OUT+": (34.0, 14.0, 12.0), "OUT-": (34.0, 14.0, 5.0)},
    # B0505S (Hi-Link veri sayfasi): 1 +Vin, 2 -Vin, 4 -Vout, 6 +Vout; bacaklar asagi
    "IZ": {"IN+": (3.0, 7.0, 0.0), "IN-": (5.5, 7.0, 0.0), "OUT-": (10.6, 7.0, 0.0), "OUT+": (15.7, 7.0, 0.0)},
    "KL": {"+": (4.0, 10.0, 5.0), "-": (12.0, 10.0, 5.0)},
    "F0": {"1": (3.0, 10.0, 5.0), "2": (22.0, 10.0, 5.0)},
    "F1P": {"1": (3.0, 10.0, 5.0), "2": (22.0, 10.0, 5.0)},
    "F2": {"1": (3.0, 10.0, 5.0), "2": (22.0, 10.0, 5.0)},
    "CB": {"+": (2.0, 10.0, 2.0), "-": (2.0, 10.0, 8.0)},
    # yuvanin kendi telleri yaysiz (+) uctan cikar; YUVA1'in + ucu SOLDA, YUVA2'ninki SAGDA (spec §4.2)
    "YUVA1": {"+": (0.0, 10.0, 14.0), "-": (0.0, 10.0, 7.0)},
    # 2026-10-02 fotograf: 2. yuvanin siyah teli YAYLI (sol) uctan cikiyor, kirmizi sagdan
    "YUVA2": {"+": (80.0, 10.0, 14.0), "-": (0.0, 10.0, 7.0)},
    # TP1'in 6.0'da lehimlenen telleri duvar ile kart A arasindaki araliktan yukari cikar: uc = tel ucu
    "TP1": {"OUT+": (2.5, 6.0, 18.0), "B+": (6.5, 6.0, 18.0), "B-": (10.5, 6.0, 18.0), "OUT-": (14.5, 6.0, 18.0)},
    # ESP32 devkit (kizakta, USB arka duvara): pin tepeleri govdenin ustu (dz = yuk).
    # B73 gozden gecirme: GPIO10 5V ile AYNI baslikta (J1), USB ucundan 21 = 5V, 16 = GPIO10 ->
    # 5 adim x 2.54 = 12.7 mm onde (ESP32_J1 ile capraz denetlenir; eskiden 34, ~11 mm hatali).
    "ESP32": {"5V": (2.0, 10.0, 28.0), "GND": (25.5, 10.0, 28.0), "GPIO10": (2.0, 22.7, 28.0), "J5": (13.75, 40.0, 28.0)},
}
# ESP32-S3-DevKitC-1 (ve ayni dizilimli N16R8 kopyalari) J1 basligi, 1. pin anten ucunda,
# 22. pin USB ucunda. Kaynak: Espressif kullanici kilavuzu, "J1" tablosu.
ESP32_J1 = ["3V3", "3V3", "RST", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO15", "GPIO16", "GPIO17",
            "GPIO18", "GPIO8", "GPIO3", "GPIO46", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14",
            "5V", "GND"]
PIN_ADIM = 2.54
KABLO_UC_SAPMA = {"TP1": 15.0}        # mm — TP1 ucu govde degil, araliktan cikan TEL UCU
KABLO_UC_TAKMA = {"H1+": "YUVA1.+", "H1-": "YUVA1.-", "H2+": "YUVA2.+", "H2-": "YUVA2.-"}
# Panel ogesinin ic ucu (dx, dz): y = panel govdesinin ice uzanan ucu (panel_hacim)
PANEL_UCLARI = {"SWP1": {"1": (0.0, 0.0), "2": (0.0, -4.7)}, "LED1": {"A": (1.3, 0.0), "K": (-1.3, 0.0)},
                "J1.2": {"L": (0.0, 0.0)}, "CAL": {"L": (0.0, 0.0)}}
UC_AD = {
    "H1+": "1. yuvanın kırmızı teli", "H1-": "1. yuvanın siyah teli",
    "H2+": "2. yuvanın kırmızı teli", "H2-": "2. yuvanın siyah teli",
    "F1P.1": "F1P klips 1", "F1P.2": "F1P klips 2 (çıkış)", "F2.1": "F2 klips 1", "F2.2": "F2 klips 2 (çıkış)",
    "F0.1": "F0 klips 1", "F0.2": "F0 klips 2",
    "TP1.B+": "TP4056 B+ teli", "TP1.B-": "TP4056 B− teli", "TP1.OUT+": "TP4056 OUT+ teli", "TP1.OUT-": "TP4056 OUT− teli",
    "SWP1.1": "PİL anahtarı orta bacak", "SWP1.2": "PİL anahtarı dış bacak (AÇ'ta ortayla öten)",
    "MT1.IN+": "MT1 IN+", "MT1.IN-": "MT1 IN−", "MT1.OUT+": "MT1 OUT+", "MT1.OUT-": "MT1 OUT−",
    "MT2.IN+": "MT2 IN+", "MT2.IN-": "MT2 IN− (−12 tarafı)", "MT2.OUT+": "MT2 OUT+", "MT2.OUT-": "MT2 OUT−",
    "IZ.IN+": "B0505S 1 (+Vin)", "IZ.IN-": "B0505S 2 (−Vin)", "IZ.OUT-": "B0505S 4 (−Vout)", "IZ.OUT+": "B0505S 6 (+Vout)",
    "CB.+": "680 µF uzun bacak", "CB.-": "680 µF şeritli bacak",
    "KL.+": "KL + vidası", "KL.-": "KL − vidası",
    "A.C34": "kart A C34 teli (24 V +)", "A.C36": "kart A C36 teli (−12)", "A.J5": "kart A J5 başlığı",
    "ESP32.5V": "ESP32 5V pini", "ESP32.GND": "ESP32 GND pini (ikinci)", "ESP32.GPIO10": "ESP32 GPIO10",
    "ESP32.J5": "ESP32 pinleri (J5 kablosu)",
    "LED1.A": "GÜÇ LED'i uzun bacak (10 kΩ ile)", "LED1.K": "GÜÇ LED'i kısa bacak",
    "J1.2.L": "COM jakının lehim kulağı", "CAL.L": "CAL jakının lehim kulağı",
}
# PIL_KABLOLAR disinda cizilen kablolar. Graf (union-find) bunlari GORMEZ: LED + direnc
# iletken degil, J5/CAL sinyal. Adim numarasi yerlerini belirler.
KABLO_EK = [
    {"a": "KL.+", "b": "LED1.A", "adim": "10.4", "not": "10 kΩ (R060) LED'in uzun bacağına lehimli, makaronlu"},
    {"a": "LED1.K", "b": "J1.2.L", "adim": "10.4",
     "not": "katot → COM jakının lehim kulağı = kart GND (J5'ten önce de lamba yanar)"},
    {"a": "ESP32.J5", "b": "A.J5", "adim": "11.1", "not": "10 telli kablo; tel eşlemesi Yerleşim 1.12"},
    {"a": "ESP32.GPIO10", "b": "CAL.L", "adim": "11.1", "not": "22 kΩ seri direnç jakın iç ucunda, makaronlu"},
]
# Guzergah istisnalari: ara noktalar (x, y, z) mm + kullaniciya soylenen yol.
# Kayitsiz kablo varsayilan yolu izler: one cik, dik, yatay, gir (arka bolgede).
KABLO_YOL = {
    ("H1+", "F1P.1"): {"ara": [(88, 7, 50), (88, 7, 13), (80, 13, 13)],
                       "soz": "yuvanın sol ucundan duvar dibine iner, F1P'nin üstünden girer"},
    ("H2+", "F2.1"): {"ara": [(176, 7, 77), (176, 7, 13), (180, 13, 13)],
                      "soz": "2. yuvanın sağ ucundan sağ alt köşeye iner"},
    ("F2.2", "F1P.2"): {"ara": [(199, 13, 13), (199, 7, 33), (104, 7, 33), (104, 7, 13)],
                        "soz": "ESP32'nin üstünden, 1. yuvanın altından (yerden 33 mm) arka duvar boyunca sola"},
    ("F1P.2", "TP1.B+"): {"ara": [(99, 13, 13), (84, 7, 13), (84, 7, 22), (60, 7, 22)],
                          "soz": "duvar ile kart A arasındaki aralıktan TP4056'nın teline"},
    ("H1-", "TP1.B-"): {"ara": [(88, 7, 43), (88, 7, 22), (64, 7, 22)],
                        "soz": "yuvanın sol ucundan aralığa iner, TP4056'nın teline"},
    ("H2-", "TP1.B-"): {"ara": [(88, 7, 70), (88, 7, 22), (64, 7, 22)],
                        "soz": "2. yuvanın sol (yaylı) ucundan aralığa iner, TP4056'nın teline"},
    ("TP1.OUT+", "SWP1.1"): {"ara": [(56, 7, 22), (84, 7, 22), (84, 7, 80), (84, 130, 80), (35, 130, 81)],
                             "soz": "aralıktan yukarı, kapağın altından öne, PİL anahtarına"},
    ("SWP1.2", "MT1.IN+"): {"ara": [(35, 130, 80), (84, 130, 80), (84, 18, 80), (84, 18, 36)],
                            "soz": "PİL anahtarından kapağın altından arkaya, MT1'in sağ ucuna"},
    ("KL.+", "A.C34"): {"ara": [(24, 30, 60), (98, 120, 60)],
                        "soz": "klemensten kart A'nın üstünden öne, kartın ön kenarındaki tele"},
    ("KL.-", "A.C36"): {"ara": [(32, 30, 62), (103, 120, 62)],
                        "soz": "klemensten kart A'nın üstünden öne, kartın ön kenarındaki tele"},
    ("KL.+", "LED1.A"): {"ara": [(24, 30, 70), (24, 130, 70), (72, 130, 81)],
                         "soz": "klemensten kart A'nın üstünden öne, GÜÇ lambasına"},
    ("ESP32.GPIO10", "CAL.L"): {"ara": [(141, 40, 78), (141, 130, 78), (143, 130, 81)],
                                "soz": "ESP32'den yukarı, kart B'nin üstünden (HV'ye ≥ 13 mm) öne, CAL jakına"},
    ("ESP32.J5", "A.J5"): {"ara": [(153, 45, 58), (50, 45, 58)],
                           "soz": "ESP32'den yukarı, kart A'nın üstünden J5 başlığına"},
}
KABLO_PAY = 1.15                     # kesim = guzergah x pay + 2 x soyma, yukari 1 cm
KABLO_SOYMA = 6.0                    # mm — her uc: soyulup terminale sarilan / pede yatirilan kisim
KABLO_SERIT = 2.0                    # mm — ucu ortak olmayan kablolar ayni cizgiye binmesin diye kaydirma adimi (ic bakista 6 px)
# B73 gozden gecirme: bazi uclar YENI kablo degil, parcanin KENDI teli. Kesim boyu o telin
# gereken boyu olarak yazilir; bilinen boyu yetmezse "ek" denir. TP1: 6.0'da pedlere ~20 cm
# lehimlendi (6.0 metni); kivrim = pedden araliga donus. Yuva tellerinin boyu olculmedi.
KENDI_TEL = {"TP1": {"ad": "TP4056'nın kendi teli", "boy_mm": 200.0, "kivrim_mm": 5.0},
             "YUVA1": {"ad": "yuvanın kendi teli", "boy_mm": None, "kivrim_mm": 0.0},
             "YUVA2": {"ad": "yuvanın kendi teli", "boy_mm": None, "kivrim_mm": 0.0}}
KABLO_KESIT = {"sinyal": "ince tel (jumper)", "bacak": "kondansatörün kendi bacağı"}   # gerisi 0.5 mm²
KABLO_ROL_AD = {"arti": "artı (5 V / 24 V)", "gnd": "paket / kart GND", "eksi12": "−12 tarafı (B0505S çıkışı)",
                "hucre": "hücre → sigorta → TP4056", "sinyal": "sinyal (J5, CAL)", "bacak": "kondansatör bacağı"}

# ── kutle ve denge (B55) ───────────────────────────────────────────────
# Kullanicinin sorusu: "bir taraf asiri agir, obur taraf bos kalmasin".
# Agirlik merkezi kutu.agirlik_merkezi() ile HESAPLANIR; burada yalnizca
# kutleler var. Her satir: (gram, goreli belirsizlik, kaynak).
#
# Kaynak sutunu ciddiye alinir: hicbiri daha TARTILMADI. Denetim bu yuzden
# agirlik merkezini belirsizligin KOTU halinde de olcuyor (her kalemi
# merkezden uzaga iten uc secim) — sonuc yalnizca nominal sayilarla
# saglikliysa iddia kirmizi olur. Kullanici bir kalemi tartarsa sayiyi ve
# belirsizligi guncelle, kaynaga "olculdu" yaz.
# ── gomme M3 somun ve cebi (B55e) ──────────────────────────────────────
# Kusur: cep Ø6 ve 2 mm idi. DIN 934 M3 somun 2.4 mm kalin ve KOSEDEN KOSEYE
# 6.35 mm — yani Ø6 delige zaten girmiyor, 2 mm cebe 0.4 mm tasiyor ve
# YUVARLAK cep donmeyi engellemiyor. Elle tork 0.5 N·m -> cep yuzeyinde
# ~8 MPa, husun lif dikine ezilme dayanimi 5-7 MPa: birkac sikmada cep
# yuvarlanir. Kapak somunu donerse KAPAK BIR DAHA ACILMAZ (somun iceride,
# tutulamaz — blogun var olma sebebi zaten bu).
# Kullanici karari (2026-09-23): "somunlarin sokulebilir olmasi onemli degil,
# yalnizca degerli parcalar sokulebilir olsun" -> donmeyi YAPISTIRICI
# engelliyor, cep yalnizca somunu yerinde tutuyor.
M3_SOMUN = {"kalinlik": 2.4, "anahtar": 5.5, "kose": 6.35}   # DIN 934

# B66 (kullanici 2026-09-27, 6.4: "o klemens kac amper kaldiriyor, baktin mi?"): baktirilmamisti.
# Olculen yuk yolu sirayla: YUK jaki -> kalin kablo -> HB950 bariyer -> kopru -> XP128 -> sont.
# KULLANIM "13 A birkac dakika" diyordu; XP128 10 A — zincirin en zayif halkasi klemensti.
# Deger stok kaydindan (CON064 notu "300V 10A, 22-12 AWG"); HB950 kaydinda deger YOK -> 7.1
# parcanin ustundeki baskiya baktiriyor.
KLEMENS_ANMA_A = {"XP128": 10.0}
KLEMENS_ADIM_MM = {"XP128": 10.0}        # iki kutup arasi

# B67 (kullanici 2026-09-27 veri sayfalarini gonderdi): takili sont R042 = YSR serisi. Kaynak:
# pdf.direnc.net/upload/5mr-type-c-sont-direnc-9-5a-datasheet.pdf (1.8 "External" tablosu).
# R043 (akimi yazmayan 5 mOhm) veri sayfasi genel katalog (Royalohm CSR): alasim degere gore
# CuNi ya da MnCu, ±400 ppm/°C'ye kadar — takilmaz.
SONT_VERI = {"R042": {"malzeme": "manganin", "cap_mm": 1.6, "W_mm": 10.0, "W_tol_mm": 0.5,
                      "anma_A": 10.0, "tolerans": 0.05, "bacak_mm": 3.5,
                      "lehim": "350 °C / 3.5 s"}}

# B55n: 14.2/15.2 "blokta iki delik" diyordu ama CAPI hicbir yerde yoktu ve
# kullanici artik soru soramiyor. Stoktaki tek bag SRF012 3.6x150: serit 3.6
# mm genis, ~1.5 mm kalin -> kosegen 3.9; Ø4.5 seridi gecirir, bag KAFASI
# gecmek zorunda degil (kafa disarida kalir).
KABLO_BAGI = {"stok": ("Kablo Bağı", "Sarf Malzeme"), "genislik": 3.6,
              "delik": 4.5, "aralik": 12.0}   # aralik: ayni parcada iki delik arasi en az
# ── yalitkan kaplama: nerelere, ne zaman (B55h, kullanici karari 2026-09-23) ──
# Kullanici: "elimde tirnak cilasi var, yuksek voltaj gecen yerleri onunla 4-5
# kat kaplamayi dusunuyorum." Tirnak cilasi = nitroselüloz lak; hobi
# konformal kaplamasi olarak gecerli. ASIL KAZANC EMNIYET DEGIL DOGRULUK:
# HV bolucusu 4.92 MOhm / 8.2 kOhm oldugu icin plaket yuzeyindeki kacak
# bolucuye PARALEL giriyor ve orani kaydiriyor (kutu.py bolum 6 olcuyor):
#   1 GOhm  -> %0.5 hata      100 MOhm -> %4.7 hata      50 MOhm -> %8.9
# Tozlu/nemli FR4 yuzeyi 1e8-1e9 Ohm mertebesinde, yani kaplama kalibrasyonu
# koruyor. ⚠ Kaplama YUZEY kacagini keser, HAVA arasindan atlamayi KESMEZ —
# mesafe yerine gecmez (kutuda mesafeler 16-30 mm, zaten fazlasiyla yeterli).
KAPLAMA = [
    {"ref": "B", "kapsam": "kart", "nerede": "Kart B'nin İKİ YÜZÜ de — zincirin tamamı bu kartta",
     "ne_zaman": "6.3'ten ÖNCE (kart kutuya girmeden, elde kolay)",
     "neden": "6 × 820K seri zincir 617 → 103 V basamaklarıyla bu kartta; komşu pedler arası "
              "kaçak hem emniyet hem ORAN hatası. Lehim yüzü öncelikli: kaçak yolu orada.",
     "onkosul": "Kartın süreklilik/direnç ölçümleri geçmiş olmalı; kaplanmış pede prob değmez."},
    {"ref": "B", "kapsam": "nokta", "nerede": "T_HV ve T_N6 tellerinin lehim noktaları + telin ilk 10 mm'si",
     "ne_zaman": "teller LEHİMLENDİKTEN sonra (kartı takmadan önce pigtail olarak lehimle)",
     "neden": "Zincirin en yüksek (617 V) ve en düşük ucu. Lehim tepeciği kaplanmazsa kaçak "
              "yolunun en dar yeri açıkta kalır.",
     "onkosul": "Önce lehimle, sonra kapla — tersi olursa cilayı kazımak gerekir."},
]
# Kaplanmayacak yerler (gerekce ile) — 'kapla' kadar onemli:
KAPLAMA_HARIC = [
    ("Kart A", "En yüksek düğümü 63.5 V (skop girişi) ve en yüksek empedansı 227 kΩ: "
               "100 MΩ'luk yüzey kaçağı %0.2 hata verir, bütçede kaybolur. Gerekmiyor."),
    ("Q1 soğutucusu ve regülatörlerin çevresi",
     "Nitroselüloz ısıda sararıp çatlar, üstelik ısı yolunu da bozar. Zaten orada yüksek "
     "gerilim yok: Q1 pil testinde ≤ 38 V, regülatörler ±12 V."),
    ("Panel jaklarının lehim kulakları (CAL, PİL, YÜK, HV)",
     "Tel oynayınca cila çatlar. Orada makaron ya da izole bant doğru çözüm — "
     "Kulaklar arası artık geniş (B56/B58e), yine de tel oynar."),
    ("Ölçüm noktaları ve test pedleri", "Kaplanmış pede prob değmez; kapı ölçümleri önce."),
]

# ── bilinen dar acikliklar (B55g) ──────────────────────────────────────
# Denetim bugune kadar hicbir yerde ACIKLIK olcmuyordu: yalnizca CAKISMA
# (cakisma3) bakiliyordu ve `parca_payi` = 6 mm kurali sadece IC_PARCA
# ciftlerine + duvar parcalarina uygulaniyordu. Tasiyici bloklar, kutu ek
# parcalari, sabitler (kose diregi / kapak rayi) ve panel govdeleri kapsam
# DISINDAYDI; asagidaki cift listesi tam o bosluktan cikti (19 cift).
# KURAL: 6 mm'nin altina inen her cift burada GEREKCESIYLE yazili olmali.
# Yeni bir dar cift cikarsa ya da buradaki bir cift artik dar degilse denetim
# kirmiziya doner — yani liste hem tavan hem taban.
# B56 (2026-09-24): ON PANEL yeniden dizilince BES kayit listeden dustu —
# "A (dolu)|F0" 3.00, "A-ayak4|F0" 3.59, "F0|J3.1" 4.95, "CAL|J7.1" ve
# "CAL|J7.2" 5.66 mm. Hicbiri "cozuldu" diye silinmedi: F0 kart A'nin x
# menzilinin (13-128) DISINA, x 161'e gitti ve CAL panelin ortasina alindi,
# yani cakisan geometri artik yok. Panel tarafinda 6 mm'nin altinda kalan
# hicbir cift kalmadi; listedeki her sey kutu ICI (kart/ayak/modul).
DAR_ACIKLIK = {
    "B-ayak1|ESP32":
        "0.54 mm — devkit'in gövdesi kart B'nin ahşap ayağına değebilir; yalıtkan, yerinde "
        "ayarlanır. Anten bu uçta ama ✅ KAPANDI (kullanıcı kararı 2026-09-23): dahili anten "
        "kartın kendi kalınlığında küçük bir çıkıntı, yanındaki ahşap blok sorun değil. "
        "Ahşap 2.4 GHz'de düşük kayıplı ve kutunun tamamı zaten ahşap.",
    "B|HV ankraj bloğu":
        "2.15 mm — kart B ölçülünce 50×50 çıktı (model 45.7 delik alanıydı), ankraja 4.30'dan "
        "2.15'e indi. Ankraj bilerek kartın önünde: HV kablosu çekilince D8 lehimi değil kablo "
        "bağı direniyor. Ahşap, iletken değil.",
    "B|Q1-köşebent":
        "2.15 mm — aynı sebep (kart B 50 mm). Q1'in ahşap köşebendi; soğutucunun KENDİSİ daha "
        "uzakta. Ahşap-plaket boşluğu, elektriksel risk yok.",
    "B-ayak2|RS": "3.82 mm — şöntün gövdesi kart B'nin ahşap ayağına yaklaşıyor. Manganin U "
                  "havada, altlığa değmiyor; ayak yalıtkan, sorun yok.",
    "A-ayak4|B": "4.09 mm — kart A'nın ön-sağ ayağı ile kart B'nin gövdesi. İkisi de sabit ve "
                 "ayak 6.1'de karttan işaretlenerek konuyor, yani yerinde ayarlanabilir.",
    "B|ESP32":
        "4.85 mm — kart B 50 mm ölçülünce ortaya çıktı (model 45.7 ile 7.0 görünüyordu). "
        "Elektriksel olarak sorun değil: 617 V'luk düğüm kartın KARŞI kenarında (yön 270°) ve "
        "en yakın iletkene mesafesi 30 mm. Buradaki 4.85 mm plaket kenarı ↔ devkit gövdesi.",
    "A-ayak2|ESP32": "5.24 mm — kart A'nın ahşap ayağı devkit gövdesine yaklaşıyor; yalıtkan, "
                     "yerinde ayarlanır.",
    "A (boş kenar)|MT1":
        "4.00 mm — kart A 18 mm'lik ayağa çıkınca ortaya çıktı (kullanıcı kararı: altındaki "
        "atlama telleri için 16–17 mm gerekiyor). Kartın ARKA BOŞ ŞERİDİ artık z 18–20'de, "
        "MT3608 ise z 24–41: düşeyde 4 mm kalıyor. Şerit boş plaket, MT modülü de yalıtkan "
        "gövdeli — değmezler, sadece pay daraldı. Gerekirse MT1 bir sıra yukarı alınır.",
}
DAR_ACIKLIK_GEREKCE_EN_AZ = 40   # karakter — 'tamam' demek gerekce degil

# ── panel simetrisi (B56, kullanici istegi 2026-09-24) ──────────────────
# ⚠ B59 (kullanici 2026-09-26): "simetrik konusunda yanlis anlastik — on yuzun TOPLU ve
# DUZENLI gozukmesini istiyorum, simetrik degil." Simetri kurali artik YALNIZ ARKA panelde.
# On panelin kurali kutu.py'de: 18 mm izgara + islev iddialari (COM olcum jaklarinin
# yaninda, CAL HV'nin komsusu degil, CAL SKOP'a komsu).
# Kullanici: "on ve arka yuzun cok daha duzgun gozukmesini istiyorum, su anda
# cok asimetrik ve hos degil."  KURAL: her panel ogesinin x'i, panelin
# ortasina (ic_en/2) gore bir AYNA esine sahip olmali; tam ortadaki oge kendi
# esidir.  Esi olamayan oge burada GEREKCESIYLE yazili olmali — ve artik
# simetrik olan bir ref burada kalirsa denetim kirmiziya doner (liste hem
# tavan hem taban, DAR_ACIKLIK ile ayni disiplin).
# B57b: tek istisnalar 18650 yuvasinin dort civata deligiydi; yuvalar yapistirilinca
# delikler kalkti, liste BOS — arka yuz de tamamen simetrik. Yeni bir essiz delik
# eklenirse denetim kirmiziya doner ve buraya gerekcesiyle yazilmasi gerekir.
PANEL_SIMETRI_HARIC: dict[str, str] = {
}
# ── yapistirma istisnasi (B57b, kullanici karari 2026-09-25) ──────────────
# Kutu ilkesi "kutuya giren hicbir parca yapistirilmaz" (B50f: ileride baska / 3D
# baski kaba gecis). Kullanici 18650 yuvalarinin M3 civata yerine yapistirilmasina
# karar verdi. Istisna burada GEREKCESI ve SOKME YOLUYLA yazili. Denetim: listede
# olmayan bir kutu ici parcanin yapistirilmasi hala KIRMIZI; listede olup artik
# yapistirilmayan (eskimis) kayit da.
# Neden sicak silikon, japon degil: japon bazi yuva plastiklerini (PP) tutmaz ve
# isida gevreklesir; sicak silikon hem ahsabi hem plastigi tutar, sokulebilir, ve
# yumusama noktasi (~65 °C) Li-ion desarj tavaninin (60 °C) ustunde.
YAPISTIRMA_ISTISNA = {
    "YUVA1": {"yapistirici": "sıcak silikon",
              "sokme": "ısı tabancasıyla ısıt ya da derze izopropil alkol damlat, maket bıçağıyla kaldır",
              "neden": "Kullanıcı kararı (2026-09-25): M3 cıvata yerine yapıştırma. Arka duvardan iki delik "
                       "ve iki somun eksilir; arka yüzün tek simetri istisnası bu delikleriydi."},
    "YUVA2": {"yapistirici": "sıcak silikon",
              "sokme": "ısı tabancasıyla ısıt ya da derze izopropil alkol damlat, maket bıçağıyla kaldır",
              "neden": "Kullanıcı kararı (2026-09-25): YUVA1 ile aynı gerekçe — iki delik ve iki somun eksilir."},
}
_MODUL_SILIKON = {"yapistirici": "sıcak silikon",
                  "sokme": "derze izopropil alkol damlat, plastik kartla kaldır",
                  "neden": "Kullanıcı kararı (2026-09-30): 'B0505S, MT1 ve MT2'yi sıcak silikonla yapıştırabilirim, "
                           "elimde izopropil alkol var, sökmesi kolay'; küçük parçalar için 2026-09-27: 'küçük parçaları "
                           "yapıştırabiliriz, değerli şeyler yapıştırılmasın'. Kablo bağı tutucuları ve çubukları kalktı."}
for _r in ("MT1", "MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"):
    YAPISTIRMA_ISTISNA[_r] = dict(_MODUL_SILIKON)
PANEL_SIMETRI_TOLERANS = 0.6     # mm — ayna esi bu kadar kayabilir (yalniz arka panel, B59)
# B59: on panelin "duzenli" tanimi — her oge bu izgaranin bir dugumunde (x ic koordinat).
ON_IZGARA_X = tuple(35.0 + 36.0 * k for k in range(5))      # 35 71 107 143 179 (jak araligi 36)
ON_IZGARA_Z = (9.0, 45.0, 81.0)                            # 1., 3., 5. cubuk sirasinin ortasi
CAL_KOMSU_R = 40.0      # mm — bu yaricapta merkezi olan jaklar CAL'in "komsusu" (yanlis delik riski)

SOMUN_CEP = {
    "cap": 6.5,      # > kose (6.35): somun zorlanmadan duser
    "kat": 2,        # 2 x 2 mm = 4 mm > kalinlik (2.4): tam gomulur, lamine duz kalir
    "yapistirici": "japon, somunun DIŞ yüzüne — dişine değil",
    "son_kat_delik": 3.2,   # vida ucu dayanmasin (M3x10 ayakta 1.5 mm, M3x12 kapakta 1.1 mm daliyordu)
}

CUBUK_YOGUNLUK = 0.65e-3     # g/mm^3 — hus/kavak dil basacagi; 150x18x2 -> 3.5 g

KUTLE = {
    # kartlar ve guc parcalari (IC_PARCA ref'leri)
    "A":     (90.0, 0.40, "tahmin: 114×114 delikli plaket (1.6 mm ≈ 39 g) + ~120 parça, soket, klemens"),
    "ESP32": (9.0, 0.20, "katalog: ESP32-S3 DevKitC-1 ≈ 9 g"),
    "B":     (14.0, 0.40, "tahmin: 50×50 plaket (≈ 7 g) + HV bölücü zinciri"),
    "RS":    (4.0, 0.40, "tahmin: manganin U şönt + XP128 klemens"),
    "Q1":    (32.0, 0.40, "tahmin: IRFZ44N 2.3 g + TO-220 soğutucu (15×40×42 alüminyum)"),
    # duvara asili pil blogu (DUVAR_PARCA ref'leri)
    "YUVA1": (12.0, 0.25, "tahmin: 18650 tekli plastik yuva, yaylı"),
    "YUVA2": (12.0, 0.25, "tahmin: 18650 tekli plastik yuva, yaylı"),
    "TP1":   (3.0, 0.30, "tahmin: TP4056 Type-C modülü"),
    "MT1":   (4.0, 0.30, "tahmin: MT3608 yükseltici modülü"),
    "MT2":   (4.0, 0.30, "tahmin: MT3608 yükseltici modülü"),
    "F1P":   (6.0, 0.30, "tahmin: 5x20 PCB klipsli sigorta yuvası + cam sigorta"),
    "F2":    (6.0, 0.30, "tahmin: 5x20 PCB klipsli sigorta yuvası + cam sigorta"),
    "IZ":    (4.0, 0.40, "tahmin: B0505S-2WR3 SIP (~3 g) + dört kısa kablo ve makaron"),
    "CB":    (3.0, 0.40, "tahmin: 680 µF 16 V radyal elektrolitik (~2.5 g) + bacaklar"),
    "KL":    (4.0, 0.40, "tahmin: 2'li 5 mm vidalı klemens + kablo uçları"),
    "HÜCRE": (45.0, 0.10, "katalog: 18650 1500 mAh ≈ 45 g (yuvaya takılınca eklenir)"),
    # panel ogeleri — tur bazinda (her ref icin ayri satir gerekmiyor)
    "jak_büyük": (9.0, 0.35, "tahmin: 4 mm born jak büyük boy, pirinç gövde + somun"),
    "jak_küçük": (6.0, 0.35, "tahmin: 4 mm vidalı banana soket"),
    "anahtar":   (8.0, 0.35, "tahmin: KTS102 toggle + somun"),
    "F0":        (6.0, 0.30, "tahmin: 5x20 PCB klipsli sigorta yuvası + cam sigorta (B58e: kutu içi)"),
    "LED1":      (2.0, 0.40, "tahmin: 5 mm LED + seri direnç + makaron + kısa tel"),
    # dagilmis kutle
    "KABLO": (25.0, 0.50, "tahmin: kutu içi kablo demeti + kablo bağları + makaron"),
}

# Denge olcutleri. "Bir taraf asiri agir mi" sorusunun FIZIKSEL karsiligi
# soldan/sagdan bakinca su: kutu iki taban rayinin uzerinde duruyor, her
# ray toplam agirligin ne kadarini tasiyor (ray_pay). Derinlik yonunde
# raylar bastan basa uzandigi icin ayni sorun yok; orada olcut AM'nin orta
# bolgede kalmasi. devrilme_aci: AM'den destek kenarina olan yatay
# uzakligin AM yuksekligine gore acisi — kutu bu aciya kadar egilse
# devrilmez (dort yonde de, belirsizligin KOTU halinde hesaplanir).
DENGE = {
    "ray_pay": 0.35,         # her taban rayi toplamin en az %35'ini tasisin (nominal)
    "kotu_ray_pay": 0.25,    # belirsizligin en kotu halinde
    "y_orta": 0.30,          # AM, yari derinligin en fazla %30'u kadar kayar
    "kotu_y_orta": 0.50,
    "devrilme_aci": 25.0,    # derece — kotu halde de
    "am_yukseklik": 0.50,    # AM, dis yuksekligin en fazla yarisinda (nominal)
    # Kotu halde 0.55: AM yuksekligi BAGIMSIZ bir fiziksel sinir degil, devrilmenin
    # ikincil gostergesi — asil olcut kotu halde olculen devrilme acisi (>= 25 derece,
    # bugun 45-56). Nominal 0.50 ile kotu hal 0.55 arasindaki fark bilerek: kutlelerin
    # hepsi ayni anda AM'yi yukari itecek uca giderse 0.509 cikiyor (B55d ile olculdu).
    "kotu_am_yukseklik": 0.55,
}

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
                 # B55n: "olc ve tutmuyorsa soyle" kullaniciyi bana yolluyordu.
                 # Kural artik metinde: delik her zaman OLCULEN disten turetiliyor.
                 "Kumpasla doğrula: born jak gövde dişi (≈ 8 mm; B60'tan beri panelde TEK model, büyük "
                 "şeffaf); jakların duvarın içine uzanan boyu (2026-09-21): 15 mm. "
                 "USB-C fiş gövdesi (≈ 12 × 6.5), toggle dişi (6). "
                 "<b>Tutmuyorsa delik tablosunu değil ölçtüğün sayıyı kullan:</b> "
                 "delik = ölçülen diş + 0.5 mm, en yakın matkap ucuna yuvarla, deneyerek büyüt. "
                 "Tablodaki çaplar nominal; asıl ölçüt parçanın somuna kadar geçmesi.",
                 # B55l: bu madde "olc ve soyle" istiyordu ve verdigi referans sayilar
                 # (114.3, 26x63) B55j'de olculup degismisti. Artik bilgi satiri.
                 "<b>Kart ölçüleri ÖLÇÜLDÜ</b> (2026-09-23), yeniden ölçmene gerek yok: kart A "
                 "{kart_a_en:.0f} × {kart_a_boy:.0f} (Adım 1.3'te bu ölçüye kesiliyor), kart B fabrika "
                 "50 × 50 (kesilmiyor), devkit 27.5 × 63. Plan bu sayılarla üretildi. "
                 # B64b: "kisa kaldiysa ek yap, GND ile bur" diyordu — yerlesim "<10 cm" kestirdigi
                 # icin tel KESIN kisa kaliyordu; GND ile burma da eski karara (B'de GND yok) aykiri.
                 "Tek bakılacak şey: <b>B:O16 → A:C11 sarı telin boyu</b>. Kutuda (kart B 270°) iki "
                 "lehim noktası düz çizgide {hvalt_duz:.0f} mm, kenarlardan ~{hvalt_yol:.0f} mm: tel "
                 "<b>{hvalt_kes:.0f} mm</b> olmalı. Yerleşimde daha kısa kestiysen: ucuna aynı kalınlıkta tel "
                 "ekle, lehimle, makaronla kapla (~1.7 V, tehlikesiz) — GND ile burma, B'de GND yok.",
                 # B55n: burasi "bana soyle, yeniden uretirim" diyordu; kullanici
                 # artik soru sormadan bitirecek, o yuzden yolu kendisi kosuyor.
                 "<b>Bir sayı tutmazsa ne yapacaksın:</b> ±2 mm'ye kadar hiçbir şey — "
                 "Adım 4.4 zaten \"ölç, kalanı kes\" diyor ve iç kat / direk / ray boyları oradan "
                 "gerçek ölçüne göre çıkıyor. Daha büyüğü için sayıyı tek yerden değiştir: "
                 "<code>uretim/kutu_veri.py</code> içindeki ilgili alanı düzelt, "
                 "<code>python kutu.py</code> koş — kesim listesi, delik tabloları, çizimler ve 3B "
                 "sahne yeniden üretilir; tutarsız bir şey kaldıysa denetim kırmızı verir."],
         "kontrol": ["Çubuklar düz mü, çatlak var mı? Eğri olanları kapak için ayır.",
                     # B55n: "soyle" yerine yapilacak is — kesim zaten 1.3'te.
                     "A'nın dış ölçüsü {kart_a_en:.0f} × {kart_a_boy:.0f}'den büyük mü? (13 cm'lik kenar "
                     "kesilmediyse 130 çıkar.) Büyükse <b>Adım 1.3'te kes</b> — plan bu ölçüyle üretildi, "
                     "büyük kalırsa ön jak gövdelerine 5 mm'den az pay kalıyor."]},
        {"no": "1.2", "baslik": "Kesim listesi — önce taban ve dış kat", "tur": "kesim",
         # B55l: bu listenin KENDISI elde olandan cok cubuk istiyordu ve belge
         # bunu soylemiyordu; uyari listenin altinda ve plan GENELI icindi.
         # Kullanici kesmeye baslayip yarida kalirdi.
         "yap": ["🛑 <b>Önce çubuk say.</b> Bu listenin kendisi <b>{kesim1_cubuk} çubuk</b> "
                 "istiyor, elinde ~{elde} var → <b>en az {kesim1_eksik} çubuk daha al</b> "
                 "(fire payıyla ~{kesim1_eksik} + 15). Planın tamamı {cubuk} çubuk; hepsini "
                 "şimdi almak zorunda değilsin ama bu adımı bitirmeye yetecek kadarı şart, "
                 "yoksa kesim yarıda kalır.",
                 "Çubuğun <b>iki ucu yuvarlak</b>: düz birleşme isteyen her parça ortadaki "
                 "<b>düz bölümden</b> ({duz:.0f} mm) kesilir. İç kat ve direk parçaları <b>{dikey_kaynak}</b>: "
                 "{h:.0f} mm boyunda, <b>yuvarlak uç aşağı</b> (tabanda gizli kalır). Duvar {sira} sıra = "
                 "{h:.0f} mm; çubuğu ortadan bölmek bu boyu VERMEZ ({yarim:.0f} mm kalır), o yüzden her dikey "
                 "parça için bir tam çubuk açılır ve artan düz kısım öbür parçalara gider.",
                 "<b>Ölç-kes-ölç:</b> şimdi yalnız <b>taban, raylar ve dış kat</b> "
                 "parçalarını kes. İç kat, direkler, kapak ve altlıklar duvar bitince "
                 "gerçek ölçüye göre kesilecek (4.4).",
                 "Maket bıçağı ya da ince testere; kesmeden önce kurşun kalemle işaretle. "
                 "Parçaları gruplara ayır."],
         "kontrol": ["Her gruptaki parça sayısı listedekiyle aynı mı?",
                     "Aynı gruptaki parçaların boyu eşit mi (üst üste koy, uçlar hizalı)?"]},
        # B55l: kart A 130x120 kesilmisti; 115x115'e indirme karari B55j'de
        # alindi ama YALNIZ veriye/DEVIR'e yazildi — kullanicinin okudugu hicbir
        # adimda yoktu. Kesilmeden 6.1 fiziken yapilamiyor (kart x 143'e uzanip
        # ESP32'ye giriyor). Tarama bunu "durdurur" diye isaretledi.
        {"no": "1.3", "baslik": "Kart A'yı {kart_a_en:.0f} × {kart_a_boy:.0f} mm'ye getir", "tur": "kesim",
         "yap": ["Elindeki plaket <b>130 × 120 mm</b> kesilmişti; plan <b>{kart_a_en:.0f} × "
                 "{kart_a_boy:.0f}</b> istiyor. Fazlalık <b>sağda ~15 mm, önde ~5 mm</b> "
                 "(A1 köşesi sol-arkada kalıyor, lehimli bölgeye dokunmuyorsun).",
                 "<b>Neden şart:</b> kesmezsen kart sağda x 143'e uzanır ve ESP32'nin (x 139) "
                 "üstüne biner. Kutuya sığmaz.",
                 "<b>Nasıl:</b> kesilecek çizgiyi iki yüzden de maket bıçağıyla <b>delik sırasının "
                 "ortasından</b> derin çiz (5–6 geçiş), sonra masa kenarında kısa kenardan başlayarak "
                 "kır. Zımparayla düzelt. Cam elyafı tozu için maske/ıslak bez.",
                 "Kesmeden önce kesim çizgisinin lehimli bir ize ya da parçaya denk gelmediğini "
                 "gözle kontrol et — yerleşim planı kenarda 2×2 delik boş bırakmıştı."],
         "kontrol": ["Kart {kart_a_en:.0f} × {kart_a_boy:.0f} mm (±1).",
                     "Kesilen kenarda kalkmış bakır ya da kopmuş iz yok (ışığa tut).",
                     # B56: F0 kartin sagina gecti; on kenarin karsisi artik bos.
                     "Kart, planın sol-arka köşesine (x 13, y 12) konunca ön duvara "
                     "<b>{a_on_pay:.0f} mm</b> kalıyor — bu boşluk ön panel jaklarının 15 mm'lik "
                     "gövdeleri ve kablo kıvrımı için."]},
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
                 # B55n: konum metinde hic yoktu ("uclardan iceride"); kutu bu iki rayin
                 # uzerinde duruyor ve devrilme hesabi TABAN_RAY_X'e bagli -> sayi metne girdi.
                 "<b>Ray merkezleri: sol kenardan {ray1_x:.0f} mm ve {ray2_x:.0f} mm</b> "
                 "(dış en {dis_en:.0f} mm'nin ¼'ü ve ¾'ü). Kutu fiilen bu iki rayın üstünde duruyor: "
                 "devrilme ve yük payı hesabı bu konumu varsayıyor, ±5 mm'den fazla kaydırma.",
                 "Sıcak silikonu ray boyunca sürekli çek, nokta nokta değil; 10 s içinde bastır. Sıralar "
                 "arası derzleri isteğe bağlı ince japonla süz (maskeleme bandı üstten tutar)."],
         "kontrol": ["Taban tek parça gibi kalkıyor mu? Ortadan tutup kaldır.",
                     "Taban düz mü, beşik gibi kamburlaşmamış mı?"]},
    ]},
    {"no": 3, "baslik": "Dış kat parçalarını del (düz zeminde)", "alt": [
        {"no": "3.1", "baslik": "Ön duvar parçalarını del", "tur": "delik_parca", "panel": "ön",
         "yap": ["Delikler duvar dikilmeden, parça <b>düz zeminde</b> delinir: 18 mm'lik "
                 "çubukta Ø8 delik 5 mm et bırakır, yerinde delmek çatlatır.",
                 "Aşağıdaki tabloda her delik hangi sıranın hangi parçasına geliyor; <b>ölçüler deliğin "
                 "MERKEZİ</b>: parçanın <b>sol ucundan</b> x, çubuğun <b>alt kenarından</b> z. Çap "
                 "sütunu Ø yazıyorsa <b>yuvarlak</b> delik, \"14 × 9 oval\" yazıyorsa dikdörtgen yuva.",
                 "Matkap yoksa: \"Delikleri nasıl açarım\" bölümü (sayfanın başında) — havya ucuyla "
                 "kılavuz, bıçak/zımparayla büyütme. Parçanın altına fire çubuk koy.",
                 "Delinen parçayı sıra ve konumuyla etiketle (örn. \"ön 3 sol\")."],
         "kontrol": ["Jakı deliğe sok: gövde geçiyor, somun yüzeye oturuyor.",
                     "Delik çevresinde çatlak yok."]},
        {"no": "3.2", "baslik": "Arka duvar parçalarını del", "tur": "delik_parca", "panel": "arka",
         "yap": ["Aynı yöntem; ölçüler yine deliğin MERKEZİ, ama <b>arkadan bakınca soldan</b> "
                 "(parçalar da o çerçevede adlandı: \"sol (arkadan)\").",
                 "USB ve ŞARJ yuvaları oval (14 × 9): merkezin 2.5 mm sağına ve soluna iki Ø9 daire, arası "
                 "maket bıçağıyla.",
                 # B63 (kullanici 2026-09-27): iki oval TIPATIP AYNI ve birbirinin aynasi; etiketler
                 # 14.1'e kadar yapismiyor, cizim de arkadan bakana gore. Kullanici TP4056'yi USB
                 # ovaline takti (on bakista sagdaki) -> ESP32 kart A'nin altina dusuyordu.
                 "<b>Deler delmez iki ovalin İÇ yüzüne kurşun kalemle adını yaz: ŞARJ / USB.</b> İkisi "
                 "tıpatıp aynı ve etiketler 14.1'e kadar yapıştırılmıyor; bu çizim arkadan bakana göre "
                 "ters. Kutu kurulunca <b>önden (jak tarafından) bakınca ŞARJ {sarj_taraf}, USB {usb_taraf}</b>."],
         # B63: "Anahtarin somunu" B58e'den kalmisti — arka duvarda anahtar yok (hepsi onde).
         "kontrol": ["USB-C fişi iki yuvadan da rahat geçiyor.",
                     "İki ovalin iç yüzünde ŞARJ / USB yazıyor."]},
    ]},
    {"no": 4, "baslik": "Duvarlar", "alt": [
        {"no": "4.1", "baslik": "1. sıra — ön ve arka", "tur": "duvar", "sira": 1,
         "yap": ["Ön ve arka duvarın ilk sırasını tabanın kenarına, <b>dik</b> yapıştır. "
                 "Geniş yüz dışa, delikli parçalar tablodaki yerde.",
                 "Her sıra iki parça; ek yeri tabloda yazan x'te. <b>Arka duvar parçaları \"arkadan bakınca\" "
                 "adlandı:</b> önde durup yerleştiriyorsan \"sol (arkadan)\" parça senin SAĞINA gelir — "
                 "şaşırmamak için arka sırayı kutunun arkasına geçip diz."],
         "kontrol": ["Gönye ya da kitap kenarıyla bak: duvar tabana dik mi?"]},
        {"no": "4.2", "baslik": "1. sıra — yanlar", "tur": "duvar", "sira": 1,
         "yap": ["Yan duvarların ilk sırasını ön ve arka duvarın <b>arasına</b> sıkıştır.",
                 "Parçayı uçlarından ve ortadan japonla tuttur (hizala, 30 s bastır); sonra iç köşeye sıcak "
                 "silikonla fileto çek."],
         "kontrol": ["Dört köşe de kapalı mı?"]},
        {"no": "4.3", "baslik": "2. sıradan en üste", "tur": "duvar", "sira": 5,
         "yap": ["Üstteki sıraları aynı şekilde ekle; ek yerleri tabloda — sıradan sıraya "
                 "kayıyor, üst üste gelmiyor.",
                 "Kalan bütün sıraları ekle — duvar toplam {sira} sıra ({h:.0f} mm). Delikli parçalar tablodaki "
                 "konumda: aynı x'teki delikler alt alta hizalanmalı."],
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
                 "Japonu üst-orta-alt üç ince çizgi sür, tek seferde doğru yere koy, 30 s bastır. Sıcak "
                 "silikon KULLANMA: kalınlık yapar, iç kat 2 mm kalmalı."],
         "kontrol": ["Duvara parmakla bastır: artık esnememeli.",
                     "Deliklerin arkasında çubuk ortası var, ek yeri yok."]},
        {"no": "4.7", "baslik": "Kapak cıvata deliklerini aç (kutu boşken)", "tur": "taban", "kapak": True,
         "yap": ["Her yan duvarda iki nokta işaretle (aşağıdaki tablo: y arka dış köşeden, z tabandan), "
                 "<b>Ø3.2 del</b> — delik dış kat (2 mm) + iç kat (2 mm) boyunca geçer.",
                 "<b>Neden şimdi:</b> kutu şu an boş. Adım 6'dan sonra içeride lehimlenmiş kart A var ve "
                 "havyayla delerken çıkan yanık talaşı doğrudan onun üstüne döküleceği için burada "
                 "deliniyor. Kapağa henüz gerek yok: konumlar tablodan.",
                 "Somun blokları kapak yapılınca (13.1) <b>cıvatanın üstüne merkezlenerek</b> "
                 "yapıştırılacak — kendi kendine hizalanır."],
         "kontrol": ["Dört delikten M3 cıvata sürtünerek geçiyor.",
                     "Delikler yan duvarın iç kat çubuğunun ortasına denk geldi (ek yerine değil)."]},
        {"no": "4.6", "baslik": "Köşe direkleri", "tur": "direk", "sira": 4,
         "yap": ["Her köşe için {direk_kat} parçayı üst üste japonla yapıştırıp "
                 "<b>{direk_t:.0f} × {direk_g:.0f} × {h:.0f} mm</b> direk yap (4 adet), "
                 "yuvarlak uçlar aşağı.",
                 "Dört iç köşeye, iki duvara da yaslanacak şekilde yapıştır; üstü duvarla "
                 "hizalı."],
         "kontrol": ["Kutuyu köşelerinden tutup bur: köşeler oynamamalı.",
                     "Dört direğin üstü aynı seviyede."]},
    ]},
    {"no": 5, "baslik": "Panel parçalarını tak", "alt": [
        {"no": "5.1", "baslik": "İç katı deliklerden geçerek del", "tur": "delik", "panel": "ön",
         "yap": ["Dış kattaki her delik kılavuz: havya ucunu / matkabı ondan geçir, iç kat çubuğunu "
                 "<b>dıştan içe</b> del, aynı çapa büyüt. İçeriden çıkarken kıymık verirse fire çubukla "
                 "destekle.",
                 "Arka duvar için de aynı. <b>USB ve ŞARJ yuvalarında delme yok:</b> arkalarındaki iç kat "
                 "çubukları kısa, yuvanın üstünden başlıyor (4.5 tablosu)."],
         "kontrol": ["Her delik iki kattan düz geçiyor; jak gövdesi rahat giriyor."]},
        {"no": "5.2", "baslik": "Born jakları tak (8 adet)", "tur": "delik", "panel": "ön",
         "monte": ["J1", "J2", "J3", "J4", "J7"],
         "vurgu": ["J3.1", "J3.2", "J7.1", "J7.2", "J1.1", "J1.2", "J4.1", "J2.1"],
         "yap": ["Sekiz jakı deliklere tak, somunları içeriden sık. Hepsi AYNI model (büyük şeffaf, B60). "
                 "Renkler: <b>YÜK</b> yeşil ×2, <b>PİL</b> mavi ×2, <b>V/SKOP</b> kırmızı, <b>COM</b> siyah, "
                 "<b>HV sarı</b> — kutudaki tek sarı jak, yerini karıştırma.",
                 "HV jakının içerideki ucuna somunu sıktıktan sonra <b>makaron geçir ama DARALTMA</b> — "
                 "HV teli 9.3'te bağlanacak (aşağıdaki ① ya da ② yöntemi); makaronu o zaman bağlantının "
                 "üstüne çekip daraltacaksın.",
                 # B62 (kullanici 2026-09-27 "kablolari nasil baglayacagim, pabuc lazim mi"):
                 # eski tarif "kalayli kanca somunun altina" idi. Kalay basinc altinda
                 # zamanla akar (soguk akma), somun gevser; 9.5 A'lik yolda gevsek
                 # baglanti isinir. Jakin arkasi metal saplama + somun; paket icerigi
                 # urun sayfasinda yazmiyor -> uc durumun ucu de yazildi.
                 "<b>Jaka kablo nasıl bağlanır</b> (jakın arkasındaki metal saplamaya; bütün jaklarda "
                 "aynı). Jakı panele tutan somunu kablo için kullanma — o somunu her sıktığında jak da "
                 "döner. ① Pakette <b>lehim kulağı</b> (delikli, kulakçıklı ince pul) varsa: somun → "
                 "kulak → ikinci somun; kabloyu kulağa lehimle, makaron geçir — en iyisi. ② Kulak yoksa: "
                 "kabloyu ~18 mm soy, telleri sıkıca bük ve <b>kalaylama</b>; yuvarlak uçlu kargaburunla "
                 "halka yap, iki somunun arasına saplamanın çevresine <b>saat yönünde</b> sar (somunu "
                 "sıktıkça halka kapanır), dış somunu sıkıca sık. Taşan tek tel kalmasın; somunun dışında "
                 "kalan çıplak kısmı makaronla kapat. ③ Saplamada <b>tek somun</b> varsa o somun jakı "
                 "tutuyor: <b>ikinci somun</b> gerekir — saplama M3 ise stoktaki M3 somun (MEK034), "
                 "değilse hırdavattan saplamaya uyan somun. <b>Neden kalaysız:</b> kalay basınç altında "
                 "zamanla akar, somun gevşer; 9.5 A'lik yolda gevşek bağlantı ısınır. Halka pabuç stokta "
                 "yok ve gerekmez; almak istersen yalıtımsız pabucun borusunu sık ve lehimle (lehim boruda "
                 "kalır, somunun altına girmez). Ertesi gün somunları bir kez daha sık.",
                 # B55l: kalin yuk kablolari 7.1'de baglaniyordu, yani kart A takiliyken
                 # ve on panelle kartin arasinda 12 mm'lik kor bir yarikta. Kutu SU AN bos;
                 # pigtail'i burada lehimlemek o isi tamamen ortadan kaldiriyor.
                 "<b>Kalın uçları ŞİMDİ hazırla (kutu boşken):</b> dört büyük jakın iç ucuna "
                 "<b>≥1.5 mm² pigtail</b> bağla (yukarıdaki yöntem; kalınlığı soyup ölçerek anla: "
                 "çıplak iletken tek damarda ≥ 1.4 mm, çok damarlı demette ~1.6 mm) ve <b>ucunu etiketle</b>. Boylar "
                 "(kart A'nın çevresinden dolaşarak ölçüldü, 3–4 cm pay dahil):<br>"
                 "• <b>YÜK 1</b> → 8.1'de bariyerin 1. kutbuna — <b>20 cm</b><br>"
                 "• <b>YÜK 2</b> → 8.1'de bariyerin 2. kutbuna — <b>20 cm</b><br>"
                 "• <b>PİL 1</b> → 8.1'de Q1'in savağına — <b>30 cm</b> (en uzun yol)<br>"
                 "• <b>PİL 2</b> → 8.1'de bariyerin 2. kutbuna — <b>25 cm</b><br>"
                 "<b>Neden şimdi:</b> 8.1'de kart A takılı olacak ve bu jakların arkasında yalnız "
                 "<b>12 mm</b> kör boşluk kalıyor; havya oraya girmiyor. Pigtail'leri kutunun "
                 "ortasına doğru kıvır, 8.1'de yalnız uçlarını vidalayacaksın.",
                 # B55n: liste ELLE yazilmisti (panel verisinden kayabiliyordu);
                 # artik bu adimin kendi 'monte' listesinden uretiliyor.
                 "Bu adımda taktığın jakların etiketlerini hemen yapıştır — {bu_etiketler}; "
                 "kalan etiketler 14.1'de."],
         "kontrol": ["Jakların içerideki uçları birbirine değmiyor.",
                     "Somunlar sıkı; jak elle dönmüyor."]},
        {"no": "5.3", "baslik": "PİL anahtarı, CAL jakı ve GÜÇ lambası", "tur": "delik", "panel": "ön",
         "monte": ["SWP1", "CAL", "LED1"], "vurgu": ["SWP1", "CAL", "LED1"],
         # B56: panel yeniden dizildi — sira ve mesafe sayilari artik uretiliyor.
         # B58e: ANALOG anahtari kalkti, F0 kutu icine (10.2); panel uc sira.
         "yap": ["Bu adımda takılanlar: {bu_etiketler}. Hepsi <b>ÖN</b> duvara; somunlar dıştan sıkılır. "
                 "<b>PİL</b> anahtarı (KTS102, 3 ayak) kutunun tek AÇ/KAPA'sı — ayakları yere doğru baksın "
                 "(kablolar aşağı iner).",
                 "<b>Konumlar aşağıdaki çizimden ve delik tablosundan okunur</b>, metinden değil. Dizilimin "
                 "mantığı (B59): <b>sol üst</b> AÇ/KAPA + GÜÇ lambası, <b>orta sıra</b> COM · V · HV (ölçüm "
                 "probu COM'un yanından), <b>sağ üst</b> CAL · SKOP (patch kablo kısa), <b>alt sıra</b> PİL "
                 "çifti solda, YÜK çifti sağda. Hepsi 18 mm ızgarada ve 1., 3., 5. çubuk sıralarının ortasında.",
                 "⚠ <b>CAL jakının iç ucuna (lehim kulağı ya da saplama) makaron geçir.</b> Panelde en yakın komşusuna "
                 "<b>{cal_pay:.0f} mm</b> var; komşuları {cal_komsu} ve onlarda {cal_tehdit:.0f} V'a kadar "
                 "gerilim bulunabiliyor, panelin arkası da kalabalık. Makaron yoksa izole bant sar.",
                 # B55n: LED1 'monte' listesindeydi ama takilisi hicbir adimda
                 # anlatilmiyordu — kullanici deligi acar, LED'i eline alir, kalir.
                 "<b>GÜÇ lambası (LED1):</b> 5 mm yeşil LED'i ön duvarın üst sırasındaki Ø5 deliğe "
                 "<b>dışarıdan içeri</b> it (sıkı geçer; gevşekse deliğin içine bir damla sıcak silikon). "
                 "⚠ <b>Bacak yönünü şimdi işaretle:</b> <b>uzun bacak = artı (anot)</b>, gövdenin yanındaki "
                 "düzlük kısa bacağın (katot) tarafıdır. LED takılınca hangisinin uzun olduğu artık "
                 "görünmüyor — kısa bacağı kıvır ya da üstüne makaron geçir. Kablolaması 10.4'te: "
                 "uzun bacak 10 kΩ üzerinden +12 rayına, kısa bacak kart GND'ye.",
                 "Arka duvara bu adımda takılan bir şey yok: ŞARJ ve USB yuvaları boş kalır (Type-C fişleri "
                 "doğrudan modüllerin soketine girer), havalandırma delikleri açık."],
         "kontrol": ["Anahtar iki konumda net oturuyor.",
                     "CAL jakı elle dönmüyor; LED dışarıdan bakınca delikte oturuyor."]},
    ]},
    {"no": 6, "baslik": "Kartları ve güç parçalarını hazırla", "alt": [
        # B58d: TP4056 (TP1) kart A'nin arka bos seridinin ALTINA giriyor. 10.2'de takiliyordu —
        # kart A 6.2'de takildigi icin 27 mm'lik modul duvar-kart araligindan indirilip altina
        # yatirilamiyordu (donerken kart kenarina carpar) ve uc pedlerine havya girmiyordu.
        {"no": "6.0", "baslik": "Şarj modülünü (TP1) kart A'dan ÖNCE tak", "tur": "duvar_parca",
         "monte": ["TP1"], "vurgu": ["TP1"],
         "yap": ["<b>Neden şimdi:</b> TP4056 kart A'nın arka boş şeridinin <b>altına</b> giriyor (kart "
                 "tabanına {tp1_bosluk:.0f} mm kalıyor). Kart takılınca 27 mm'lik modül duvarla kart arasındaki "
                 "{tp1_aralik:.0f} mm'lik aralıktan indirilip yatırılamaz, uçtaki pedlerine de havya girmez.",
                 "<b>Önce tezgahta lehimle:</b> modülün <b>B+, B−, OUT+, OUT−</b> pedlerine ~20 cm 0.5 mm² "
                 "kablo (artılar kırmızı, eksiler siyah), uçlarını etiketle: B+ / B− / OUT+ / OUT−. IN+/IN− "
                 "boş kalır (şarj Type-C'den gelir). Uçlar 10.3'te sigortalara ve PİL anahtarına bağlanacak.",
                 "<b>Raf — dört çubuk parçası</b> (hepsi 18 mm genişlik, enine kesim): alt kat iki "
                 "{tp1_alt:.0f} mm, üst kat bir {tp1_ust:.0f} mm, dayanak bir {tp1_day:.0f} mm. Alt kattaki iki "
                 "parçayı aralarında <b>{tp1_kanal:.0f} mm kanal</b> kalacak şekilde koy, üst katı ikisinin "
                 "üstüne japonla yapıştır. Dayanağı üst katın duvardan uzak ucuna, <b>uzun kenarı üstünde "
                 "dik</b> yapıştır (modül bu kenara yaslanacak).",
                 "<b>Hangi oval:</b> önden (jak tarafından) bakınca <b>{sarj_taraf}</b> olan — 3.2'de iç yüzüne "
                 "ŞARJ yazdın; öbürü (USB) ESP32'nin. Karıştırırsan ESP32 kart A'nın altına düşer ve kart oturmaz.",
                 "Rafı ŞARJ yuvasının tam önüne, tabana <b>sıcak silikonla</b> yapıştır: üst katın ucu duvara "
                 "değsin, yuva rafın ortasına gelsin (konum tabloda). Yuvanın arkasında iç kat çubuğu kısa, "
                 "raf o 2 mm'lik girintiye de girebilir — sorun değil.",
                 "<b>Modülü (TP1) kablo bağıyla tuttur:</b> kanaldan bir kablo bağı geçir; modülü rafa koy, Type-C "
                 "soketi yuvaya girsin, uzak kenarı dayanağa yaslansın (fişi takarken itme kuvvetini dayanak "
                 "alır, bağ değil). Bağı modülün <b>ortasından</b> (soketten ~13 mm), entegrenin üstünden "
                 "geçirip sık — LED'leri ve uçtaki pedleri kapatmasın. Modülde montaj deliği yok — "
                 "<b>vida/cıvata YOK</b>.",
                 "Dört kablonun uçlarını duvarla kart A arasındaki aralıktan yukarı al, duvara maskeleme "
                 "bandıyla geçici tuttur — kart A takılırken ezilmesinler."],
         "kontrol": ["Type-C fişi dışarıdan ŞARJ yuvasına tam giriyor; fişi iterken modül geri kaçmıyor.",
                     "Modül rafta oynamıyor; kablolar etiketli ve kart A'nın ayak yerlerini kapatmıyor."]},
        {"no": "6.1", "baslik": "Ayakları kartla hizala, gömme somun", "tur": "montaj",
         "vurgu": ["A", "B"],
         "yap": ["Yerleşim planı her kartın köşesinde <b>2×2 delik</b> boş bıraktı: bu dört "
                 "deliğin ortasına Ø3.2 del (A'da dört köşe, B'de çapraz iki köşe).",
                 "Kartın yeri tabloda (telli kenar öne). Ayak bloğu kartın kenarından ~6 mm taşar, normal.",
                 "Ayak bloğu: <b>{ayak_kat_a} parça çubuk üst üste = {ayak_yuk_a:.0f} mm</b> (kartın altındaki "
                 "atlama telleri için bu yükseklik ÖLÇÜLDÜ). <b>1. kat Ø3.2</b> (vida girer), "
                 "<b>2. ve 3. kat Ø{cep_cap:.1f} = somun cebi</b> (4 mm derin: M3 somun 2.4 mm, tam gömülür "
                 "ve lamine düz kalır), <b>{cep_alt_kat}. kat Ø{son_delik:.1f}</b> — vidanın ucu oraya çıkar, "
                 "altındaki katlar delinmez, sadece yükseltir; tahtaya "
                 "dayanmaz. Cep çapı neden Ø{cep_cap:.1f}: M3 somun köşeden köşeye {somun_kose:.2f} mm, daha darına girmez.",
                 "<b>Somunu cebe koyarken dış yüzüne bir damla japon</b> ({cep_yapistirici}) — cep yuvarlak "
                 "olduğu için dönmeyi tek başına engellemez; dönen somun vidayı ne sıkar ne söker. "
                 "Somun kutuda kalıcıdır, sorun değil: sökülmesi gereken şey kart, somun değil.",
                 # B55n: "katlari lamine et" diyordu ama dort katin deliklerinin nasil
                 # ust uste tutturulacagini soylemiyordu. Elle isaretlenen 4 delik
                 # tutmaz (0.5 mm sapma vidayi somuna sokmaz) ve cep lamine olduktan
                 # SONRA acilamaz (icte kaliyor) — sira tersine cevrilemez, yazildi.
                 "<b>Delikler nasıl üst üste gelir (sıra önemli):</b> "
                 "① Üstteki <b>{cep_alt_kat} katı</b> üst üste koy, mandalla/bantla sık, hepsini birden "
                 "<b>tek seferde Ø3.2</b> del — dört delik böyle eş eksenli çıkar, elle işaretleme yok. "
                 "② Yandan kurşun kalemle bir <b>hizalama çizgisi</b> çek (katlar geri aynı sırayla ve aynı "
                 "yöne gelsin). ③ Katları ayır; 2. ve 3. katın deliğini Ø{cep_cap:.1f}'e büyüt (Ø3.2 kılavuz "
                 "matkabı ortalar), {cep_alt_kat}. katı Ø{son_delik:.1f}'e getir. "
                 "④ Önce {cep_alt_kat}. + 3. + 2. katı japonla yapıştır — cep şimdi üstü açık bir kuyu. "
                 "⑤ Somunu kuyuya bırak (Ø{cep_cap:.1f} kuyuda {somun_kose:.2f} mm somun kendiliğinden ortalanır), "
                 "dış yüzüne damla japon, üstüne 1. katı çizgiye göre koy ve bastır. "
                 "⑥ <b>Japon kurumadan M3 vidayı sok-çıkar:</b> girmiyorsa katlar kaymıştır, hemen düzelt. "
                 "⑦ Kalan alt katları (yükseltici, deliksiz) bu başlığın altına yapıştır.",
                 # B62: eski yol "karti koy, deliklerden kalemle isaretle, blogu isarete
                 # yapistir" idi. Isaret 0.5-1 mm kayarsa M3 vida (Ø3.2 delikte 0.2 mm
                 # bosluk) somuna GIRMEZ ve blok silikonla yapismis olur. Blok karta
                 # vidaliyken yapistirilinca hizayi vidanin kendisi verir.
                 "<b>Tabana yapıştırma — blok karta vidalıyken:</b> blokları M3 vidalarla <b>karta "
                 "vidala</b>, kartı bloklarıyla birlikte tablodaki yere koy, blokların kartın dışına taşan "
                 "kenarlarına sıcak silikonla fileto çek; silikon soğuyunca vidaları sök, kartı kaldır. "
                 "Hizayı vida verir: kalemle işaretleyip tek tek yapıştırırsan 0.5–1 mm kayma vidayı "
                 "somuna sokmaz. <b>Kart B için iki blok aynı yöntemle ama {ayak_kat_b} kat "
                 "({ayak_yuk_b:.0f} mm)</b> — B'nin altında tel yok, alçak kalıyor."],
         "kontrol": ["Kartı koy, M3 vida dört delikten de somuna giriyor.",
                     "Kart sallanmıyor, altı hiçbir yere değmiyor."]},
        {"no": "6.2", "baslik": "Ana kartı vidala", "tur": "montaj", "vurgu": ["A"],
         "yap": ["<b>YÖN ÖNEMLİ — kare kart dört türlü oturur, ayaklar simetrik olduğu için yanlış yön de "
                 "vidalanır:</b> tellerin sıra hâlinde çıktığı uzun kenar (<b>A–C sütunları</b>: V, COM, SKOP, "
                 "HV alt, Kelvin/yıldız ve 24 V telleri) <b>ön panele, jaklara</b> baksın — kartın "
                 "<b>{yon_a}</b> kutunun o köşesine gelir. Bu yönde J5 başlığı (ESP32 kablosu) kartın arka "
                 "yarısında kalır.",
                 "Kartın arka şeridinin altında TP4056 var: dört kablosu ayak ya da kart altında ezilmesin.",
                 "Kart A'yı ayaklara oturt, dört M3x10 vidayla tuttur (pul ile). "
                 "<b>Yapıştırma.</b>",
                 "Vidayı fazla sıkma; plaket çatlar."],
         "kontrol": ["Kart tek parça çıkıyor (dene: vidaları sök, tak)."]},
        {"no": "6.3", "baslik": "ESP32, kart B ve altlıklar", "tur": "montaj",
         "vurgu": ["B", "ESP32"],
         # B62: "altlikta iki delik" B55l'den kalmisti — altlik o gun ortadan bolundu,
         # bag artik aradaki KANALDAN geciyor (2 mm cubuga yandan delik acilamaz).
         # B65 (kullanici 2026-09-27): "ESP'nin bacaklarina dikkat et, USB takilirken geriye gitmemesi
         # icin arkasinda bir yer olmali, anten cikintisi ~18-19 mm". Eskiden yalniz altlik + "bagi
         # devkit'in ustunden dolandir" vardi: bag 3.6 mm, pin arasi ~1.9 mm — pinlerin ARASINDAN
         # gecemez, dupont ucuna basabilirdi; USB takilirken devkit'i tutan hicbir sey yoktu.
         "yap": ["<b>ESP32 — kızakta; önce hizala, sonra yapıştır.</b> Devkit pinleri yukarı, soketli ucu arka "
                 "duvara ~2 mm. <b>Hangi oval:</b> önden (jak tarafından) bakınca <b>{usb_taraf}</b> olan — iç "
                 "yüzünde USB yazıyor; öbüründe 6.0'da taktığın şarj modülü var. Dışarıdan bir Type-C kabloyu o "
                 "ovalden devkit'in <b>COM yazan</b> soketine tak ve <b>takılı bırak</b>: devkit'in yerini kablo "
                 "belirler, aşağıdaki parçaları ona dayayarak yapıştırırsın. Fiş girmiyorsa devkit'i fiş girene "
                 "kadar yana kaydır — önden bakınca sağa <b>{esp_sag_pay:.0f} mm</b>, sola yalnız "
                 "<b>{esp_sol_pay:.0f} mm</b> yer var (solda kart A'nın arka-sağ ayağı); daha fazlası gerekirse "
                 "devkit'i yerinde bırak, ovali COM soketine doğru eğeyle genişlet.",
                 "<b>Altlık</b> dört parça: iki sıra, her sıra ortadan bölük, aradaki <b>9 mm kanal</b> kablo "
                 "bağının geçtiği yer. <b>Kanal, iki yanındaki pinlerde dupont ucu OLMAYAN bir hizaya gelmeli</b>: "
                 "bağ {bag_genislik:.1f} mm, pinlerin arası ~1.9 mm — bağ pinlerin arasından geçemez, BOŞ pinlerin "
                 "tepesinden geçer. Kullanılacak pinler: {esp_dolu_pin}. Devkit'in üstündeki pin yazılarına bak, "
                 "iki yanda da boş 3–4 pinlik hizayı bul; kanal orada değilse parça boylarını kaydır (arka + 9 + ön "
                 "= 63 mm). Altlığı tabloda yazan yere tabana sıcak silikonla yapıştır (±2 mm tolerans; rayların "
                 "altında yer kalsın).",
                 "<b>Kızak</b> — hepsi japonla altlığın üstüne, devkit yerinde ve kablo COM'da takılıyken (devkit'in "
                 "kenarına bir kat kâğıt sar: hem {esp_ray_pay:.2f} mm pay verir hem japonu devkit'ten uzak tutar): "
                 "① <b>Yan raylar</b> — {esp_ray_yuk:.0f} mm'lik enine şeritler, uzun kenarı üstünde dik; iki "
                 "uzun kenara ikişer tane, <b>kanal hizasında ray yok</b> (bağ oradan çıkar). "
                 "② <b>Omuz takozları</b> — bir şeridi ikiye böl ({esp_takoz_boy:.0f} + {esp_takoz_boy:.0f} mm); "
                 "anten ucunda, <b>anten çıkıntısının iki yanında</b> kartın omuzlarına daya. Aralarında en az "
                 "<b>{esp_anten_bosluk:.0f} mm</b> boşluk kalsın: çıkıntı ~{esp_anten_en:.0f} mm ve ortada — "
                 "takozlar ANTENE DEĞMEZ, USB takılırken itme kuvvetini kartın omuzları taşır. Arka tarafı arka "
                 "duvar tutar (çekerken devkit en çok 2 mm geri gider).",
                 "Japon kuruyunca kabloyu çıkar, <b>kablo bağını</b> kanaldan geçir: devkit'in altından, iki "
                 "yandaki boş pinlerin tepesinden, üstte kilitle. Devkit oynamayacak kadar sık, kartı eğmeden; bağ "
                 "dupont ucuna, USB soketlerine ve BOOT/RESET düğmelerine basmasın. <b>Sökmek:</b> bağı kes, telleri "
                 "çek, devkit yukarı çıkar — kızak yerinde kalır, geri takınca devkit kendi yerine oturur.",
                 # B55g: kart B kare ve DORT TURLU takilabiliyor; yonu hicbir
                 # yerde yaziliyordu ve ayaklar 6.1'de yapistirildigi icin secim
                 # geri donulemez. Cumle veriden uretiliyor (yon_b).
                 # B55h: kaplama kart kutuya girmeden yapilir; hatirlatma burada.
                 "<b>Kart B'yi takmadan önce kapla.</b> Zincirin tamamı (617 → 103 V) bu kartta: "
                 "iki yüzü de 4–5 ince kat tırnak cilası/konformal lak. T_HV ve T_N6 tellerini "
                 "ÖNCE lehimle, sonra lehim noktalarını da kapla. Ayrıntı ve kaplanmayacak yerler: "
                 "\"Yalıtkan kaplama\" bölümü.",
                 "Kart B'yi ayaklarına vidala. <b>YÖN ÖNEMLİ — dört türlü takılabilir:</b> "
                 "kartın <b>{yon_b}</b> kutunun o köşesine baksın. Bu yönde 617 V'luk giriş "
                 "düğümü kutudaki her iletkenden en uzakta kalıyor <i>ve</i> HV kablosu en "
                 "kısa ({hv_kablo}) oluyor; yanlış yön ikisini birden kötüleştirir."],
         "kontrol": ["USB-C fişi yuvadan girip sokete oturuyor.",
                     "Kart B ile kart A arasındaki tel gergin değil."]},
        {"no": "6.4", "baslik": "Şönt demetini tezgahta lehimle", "tur": "montaj", "vurgu": ["RS"],
         # B67 (kullanici 2026-09-27 iki veri sayfasi gonderdi: "elimde 2 sont var, hangisi?"): R042
         # "9.5 A" = YSR serisi, MANGANIN Ø1.6, 5 mOhm ±%5, 10 A, bacak araligi W = 10 ± 0.5 mm, basik
         # yerin altinda bacak A = 3.5 mm, olcum noktasi (test point) basik yerde. R043 (akimi yazmayan
         # 5 mOhm) genel katalog: alasim "degere gore CuNi ya da MnCu", ±400 ppm/°C'ye kadar. Eski
         # metin "iki bakir bacak, manganin-bakir eki, 11 mm, bogun ALTINA bakira" diyordu — R042'de
         # bakir bacak yok (tek parca manganin tel) ve basigin altinda Kelvin'e yer yok (3.5 mm klemense).
         "yap": ["Kutuya <b>5 mΩ 9.5 A şönt (R042)</b> takılır. Veri sayfası (YSR serisi): tek parça "
                 "<b>manganin</b> tel Ø1.6 mm, 5 mΩ ±%5, <b>10 A</b>, bacaklar arası 10 ± 0.5 mm, bacaklardaki "
                 "<b>basık yerin</b> (boncuk) altında bacak yalnız 3.5 mm. Aynı kutudaki öbür 5 mΩ'u (R043, akımı "
                 "yazmayan) <b>KULLANMA</b>: veri sayfası genel katalog, alaşımı belirsiz (bakır-nikel olabilir, "
                 "±400 ppm/°C) — 9.5 A'de şönt ~40 °C ısınır, okuma bakır-nikelde ~%1.6, manganinde ~%0.1 kayar. "
                 "15 mΩ (R044) 3.4 A'de kalıyor ama 3 kat ince okur — mA işleri için yedek; klemens vidasıyla "
                 "değişir. Kalın yük kabloları bacağa LEHİMLENMEZ: bacaklar XP128 10 mm klemensin (CON064) iki "
                 "kutbuna — aralık zaten 10 mm, <b>önce bükmeden dene</b>, girmezse hafif bük; kalın kablolar "
                 "XP128'e de girmez, <b>bariyer klemenste</b> (HB950) birleşir ve XP128'in her kutbuna tek köprü "
                 "gider (7.1, 8.1). Şöntün hangi bacağı RS.1 (YÜK 1 tarafı) hangisi RS.2 (YÜK 2) — işaretle.",
                 "<b>Kelvin telleri</b> = akım taşımayan iki ince ölçüm teli: şöntün gerilimini, klemens "
                 "temasının direnci (birkaç mΩ — şöntün kendisi kadar) karışmadan okur. Onları bacaklardaki "
                 "<b>basık yerin kendisine</b> lehimle: veri sayfası ölçüm noktasını orada gösteriyor, basığın "
                 "altındaki 3.5 mm'lik bacak klemense girecek — onu çıplak bırak, vidaya lehim/temas YOK. Lehim "
                 "yeri 1 mm kayarsa şöntün görünen değeri ~%4 değişir; 12.2'deki kalibrasyon bunu düzeltir. "
                 "<b>Lehim:</b> havya ≤ 350 °C, her lehimde ≤ 3–4 s (veri sayfası 350 °C / 3.5 s'yi sınıyor); "
                 "önce teli kalayla, flux kullan. <b>Lehimlere sıcak silikon SÜRME</b> — şönt tam akımda ~45 °C "
                 "ısınır, silikon yumuşar ve şöntün soğumasını keser; gerilmeyi 7.2'deki kablo bağı alır, "
                 "istersen lehimin üstüne makaron. Kelvin çifti S+ (RS.1) ve S− (RS.2) burgulu, yıldız GND RS.2'ye "
                 "S− ile <b>aynı noktaya</b>. Teller ~20 cm (kutuda şöntten kart A'nın ön kenarına ~12 cm). Üç "
                 "telin ucuna 3'lü <b>dişi header</b> (CON018'den kes).",
                 "Kart A'daki T_SP / T_SN / T_YILDIZ tellerinin uçlarına <b>erkek pin</b>: "
                 "demet konnektörle takılır, kart sökülebilir kalır."],
         "kontrol": ["S+ ↔ RS.1 bacağı, S− ↔ RS.2 bacağı: bip ötmeli.",
                     "Yıldız ↔ S−: ötmeli (aynı nokta).",
                     "RS.1 ↔ RS.2: 0.0–0.5 Ω (şönt + prob)."]},
        {"no": "6.5", "baslik": "Q1 demeti ve soğutucu", "tur": "montaj", "vurgu": ["Q1"],
         "yap": ["Q1'i soğutucuya <b>yalıtarak</b> vidala: mika/silikon izolatör + burç + "
                 "termal macun. Kapı bacağına 1 pinli dişi header, makaronla.",
                 "Soğutucuyu üç parça çubuktan köşebende M3 vida + somunla tuttur.",
                 # B55n (kullanici karari 2026-09-24): mika yalittigi icin sogutucu
                 # kapali kutunun icinde YUZEN bir metal plakaydi. Dogrudan GND'ye
                 # baglamak mika delinirse PIL 1'i (38.5 V'a kadar, o yolda BIZIM
                 # koydugumuz sigorta yok) GND'ye kisa ederdi; 1 M ile baglamak
                 # statigi akitir ve ariza halinde 38 uA'den fazla akitmaz.
                 # B58: asagida "(klemensin siyah ucu ya da A:T_YILDIZ)" yaziyordu —
                 # klemensin siyah ucu C36 = -12 RAYI, kart GND degil (B50'den beri).
                 "<b>Soğutucuyu {sogutucu_r} ile kart GND'ye bağla</b> ({sogutucu_stok}): direncin bir ucunu "
                 "soğutucunun vida somununun altına, diğer ucunu kart GND'ye (A:T_YILDIZ ya da şöntün "
                 "RS.2 bacağı; ⚠ 24 V klemensinin siyah ucu DEĞİL — o −12 rayı). Neden dirençle: mika soğutucuyu yalıttığı için soğutucu kapalı kutuda "
                 "<b>yüzen</b> bir metal plaka kalıyor; direnç statik birikimini akıtıp potansiyelini "
                 "tanımlıyor. Neden doğrudan tel DEĞİL: mika bir gün delinirse soğutucu Q1'in savağına, "
                 "yani <b>PİL 1</b>'e (pil testinde {pil_azami}) bağlanır — düz tel bunu GND'ye kısa "
                 "devre ederdi ve o yolda bizim koyduğumuz bir sigorta yok. {sogutucu_r} ile en kötü "
                 "hâlde {sogutucu_akim:.0f} µA akar."],
         "kontrol": ["Q1 tabı ↔ soğutucu: ötmemeli.",
                     "Kapı ↔ kaynak: ötmemeli.",
                     "Soğutucu ↔ kart GND: ötmemeli ama direnç kademesinde ≈ {sogutucu_r} okumalı "
                     "(0 Ω okursan mika delinmiş ya da vida tabı sıyırmış)."]},
        {"no": "6.6", "baslik": "Şönt ve Q1'i kutuya al", "tur": "montaj", "vurgu": ["RS", "Q1"],
         "monte": ["RS", "Q1"],
         "yap": ["Şönt altlığını (iki parça, aradaki <b>9 mm kanal</b> kablo bağının geçtiği yer) ve Q1 "
                 "köşebendini plandaki yere yapıştır; şöntü kanaldan geçen kablo bağıyla, köşebendi tabana "
                 "silikonla (kutu parçası).",
                 "Parçaların hiçbirini doğrudan tabana yapıştırma."],
         "kontrol": ["Şönt bacakları serbest, hava alıyor.",
                     "Q1 soğutucusu hiçbir parçaya 6 mm'den yakın değil."]},
    ]},
    {"no": 7, "baslik": "Güç yolu — YÜK jakları, şönt, Kelvin", "alt": [
        {"no": "7.1", "baslik": "Yük yolunu bağla", "tur": "kablo", "kablo": [2, 3],
         "vurgu": ["RS", "J3.1", "J3.2"],
         # B55n: eskiden "sont bacagiyla ayni vida" diyordu — XP128'in tek kafesine
         # Ø2 manganin + damarli kablo birlikte giremez. Guc dugumu bariyere tasindi
         # (8.1 gerekcesi); XP128'de yalnizca sont bacagi + tek kopru kaliyor.
         "yap": ["<b>Güç düğümü bariyer klemensi</b> (HB950, CON011) şönt bloğunun yanına: "
                 "XP128'in her kutbundan bariyerin ilgili kutbuna <b>kısa kalın köprü</b> çek. "
                 "XP128'de şönt bacağı + o tek köprüden başka bir şey olmayacak.",
                 "YÜK 1 jakının <b>kalın kablosu</b> (≥1.5 mm², 5.2'de takıldı) → <b>bariyer kutup 1</b> "
                 "(= RS.1 düğümü); <b>bariyer kutup 2</b> (= RS.2 düğümü) → YÜK 2 jakının kalın kablosu. "
                 "Bariyer tarafında: teli "
                 "~10 mm soy, sıkıca bük, <b>kalaylama</b>, vidanın (varsa pulunun) altına saat yönünde yatır ve "
                 "sık — kalaylı uç vida altında zamanla gevşer (gerekçe 5.2). ⚠ <b>Halka pabuç stokta YOK</b> "
                 "ve gerekmez; almak istersen 5.2'deki gibi borusu lehimli pabuç.",
                 "Kısa tut: ölçülen bütün akım bu yoldan geçecek (sürekli ≤ 9.5 A, 5 mΩ şöntün ısıl "
                 "sınırı; 15 mΩ takılıysa 3.4 A). Şöntü tutan XP128 klemensi 10 A: kısa süreli de olsa geçme.",
                 # B66: HB950'nin akim degeri kayitta ve urun sayfasinda yok.
                 "<b>HB950'nin üstündeki baskıya bak</b> (ör. \"300V 15A\"): en az 10 A olmalı. Daha düşük yazıyorsa "
                 "o sayıyı kutunun akım sınırı say ve panelde YÜK etiketinin altına yaz."],
         "kontrol": ["YÜK 1 ↔ YÜK 2: 0.0–0.5 Ω (şönt 5 mΩ + prob).",
                     "YÜK 1 ↔ V, SKOP, HV jakları: OL (sonsuz)."]},
        {"no": "7.2", "baslik": "Kelvin ve yıldız konnektörünü tak", "tur": "kablo",
         "kablo": [4, 5, 6], "vurgu": ["RS"],
         "yap": ["6.4'te hazırladığın 3'lü demeti kartın T_SP / T_SN / T_YILDIZ pinlerine "
                 "tak — sıraya dikkat: S+ → T_SP (C25), S− → T_SN (C27), yıldız → "
                 "T_YILDIZ (C29).",
                 "Burgulu çifti kablo bağıyla şönt altlığına tuttur."],
         "kontrol": ["Kart C25 ↔ YÜK 1 jakı: ötmeli. Kart C27 ↔ YÜK 2: ötmeli.",
                     "Kart C29 ↔ <b>şöntün RS.2 bacağı</b>: ötmeli (yıldız oraya lehimli). "
                     "⚠ COM <b>jakıyla</b> ölçme — COM'un teli 9.1'de bağlanıyor, şu an takılı "
                     "değil ve OL okursun; sağlam lehimi sökmeye kalkma.",
                     "YÜK 1 ↔ COM: <b>öter</b> (arada yalnız 5 mΩ şönt var) — ohm kademesinde ≤ 0.5 Ω oku; "
                     "asıl kontrol yukarıdaki C25/C27 ayrımı."]},
    ]},
    {"no": 8, "baslik": "Pil testi yolu — Q1 ve PİL jakları", "alt": [
        {"no": "8.1", "baslik": "Q1'i yük yoluna bağla", "tur": "kablo", "kablo": [7, 8, 9],
         "vurgu": ["Q1", "J7.1", "J7.2", "RS"],
         # B55n: "Q1 kaynagi -> RS.1" + "YUK 1 -> RS.1" demek XP128'in TEK kutbuna
         # sont bacagi dahil UC iletken sokmak demekti. Ø2 manganin cubuk kafes
         # basincini tek basina alir, yanindaki damarli kablo gevser ve 10 A'lik
         # yolda gevsek klemens isinir. Dugum bariyer klemense ayrildi; olcum
         # etkilenmiyor cunku Kelvin uclari sontun BACAGINDA, dugumde degil.
         "yap": ["<b>Güç düğümü bariyerde, XP128'de değil.</b> Şönt bloğunun yanına <b>HB950 2 pin "
                 "bariyer klemensi</b> (CON011) yapıştır/vidala. Her XP128 kutbunda yalnız "
                 "<b>şönt bacağı + tek köprü kablosu</b> kalsın; kalın kabloların hepsi bariyerde birleşsin. "
                 "Gerekçe: XP128'in kafesine Ø1.6 mm manganin çubukla damarlı kablo birlikte girerse "
                 "basıncı çubuk alır, kablo gevşer — 10 A'lik yolda gevşek klemens ısınır. "
                 "Ölçüme etkisi yok: Kelvin uçları şöntün <b>bacağında</b>, bu düğümde değil; "
                 "düğümdeki temas direnci akımı değiştirmez, ölçülen gerilime girmez.",
                 "Bariyer <b>kutup 1</b> (= RS.1 düğümü): YÜK 1 jakı · Q1'in <b>kaynağı</b> · "
                 "XP128 kutup 1'e giden köprü.",
                 "Bariyer <b>kutup 2</b> (= RS.2 düğümü): YÜK 2 jakı · PİL 2 jakı · "
                 "XP128 kutup 2'ye giden köprü.",
                 "PİL 1 jakı → Q1'in <b>savağı</b> (bariyere uğramaz, tek kablo).",
                 "Hepsi kalın kablo; jak tarafları 5.2'de bağlandı. Bariyer tarafında burulmuş, "
                 "<b>kalaysız</b> uçlar vidanın (varsa pulunun) altına — bir kutba iki-üç uç sığar, hepsini aynı "
                 "yöne (saat yönü) yatır. Kalaylı uç vida altında zamanla gevşer (5.2). Halka pabuç stokta "
                 "yok ve gerekmez.",
                 "<b>Şönt değiştirirken</b> (5 mΩ ↔ 15 mΩ) yalnız XP128'in iki vidası gevşer — "
                 "kalın kablolar ve Kelvin lehimleri yerinde kalır."],
         "kontrol": ["PİL 2 ↔ YÜK 2: ötmeli (ikisi de RS.2).",
                     "PİL 1 ↔ YÜK 1: <b>kırmızı prob PİL 1'de</b> ölç — ötmemeli. (Ters "
                     "probda MOSFET'in gövde diyotu öter, o normal.) Kapı teli henüz takılı değil: "
                     "ölçerken Q1'in kapısını kaynağına ince telle kısa devre et (yüzen kapı MOSFET'i "
                     "yarı açabilir, yanlış 'öter' verir)."]},
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
                 "Jak tarafı 5.2'deki yöntemle: lehim kulağı varsa lehim, yoksa <b>kalaysız</b> halka iki "
                 "somunun arasında; çıplak uç kalmasın. Bu teller akım taşımaz ama gevşek bağlantı "
                 "okumayı oynatır. (Halka pabuç stokta yok, gerekmez.)"],
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
                 # B55n: "600 V altiysa soyle" kullaniciyi bana yolluyordu. Artik karar
                 # metinde: baski >= tam skala ise gec, degilse ne yapilacagi yazili.
                 "HV jakı → kart B D8: <b>silikon prob kablosu</b> (KBL004). Kısa yoldan, diğer "
                 "tellere paralel gitmesin.",
                 "<b>Kablonun gerilim sınıfı — kararı burada ver, sorma:</b> kılıfın üstündeki "
                 "baskıyı oku ({hv_fs:.0f} V tam skala). "
                 "① <b>{hv_fs:.0f} V ve üstü yazıyorsa</b> (ör. 1 kV / 20 kV silikon prob kablosu): "
                 "doğrudan kullan. "
                 "② <b>Daha düşük yazıyorsa ya da hiç baskı yoksa:</b> kabloyu <b>boydan boya makaronla</b> "
                 "kapla (ikinci yalıtım; makaron uçlardan 10 mm taşsın) <b>ve</b> panelde HV etiketinin "
                 "altına okuduğun değeri yaz — o değerin üstünde ölçüm yapma. "
                 "Baskısız kablonun kılıfı tek başına {hv_fs:.0f} V sayılmaz; kaplarsan ikinci katman "
                 "riski taşır, kutunun kendisi zaten yalıtkan. "
                 "③ Her iki halde de kablo <b>tek parça</b> olsun: ek yeri / lüstür klemens yok.",
                 "Ankraj: üç çubuk parçasını üst üste yapıştırıp kart B'nin önüne, tabana dik "
                 "yapıştır (plandaki yer); HV kablosunu buna kablo bağıyla tut — çekilince "
                 "D8 lehimi değil bağ direnir.",
                 "HV'nin dönüşü de COM jakıdır; ayrı tel yok."],
         "kontrol": ["HV jakı ↔ kart B'nin R10 bacağı: ötmeli. (D8'in kendisi 6.3'te cilayla kaplandı — "
                 "kaplı lehime prob değmez, kazıma; komşu çıplak bacaktan ölç.)",
                     "HV jakı ↔ R8 (VREF): tabloda yazan direnç (≈ 4.9 MΩ).",
                     "Kabloyu elle çek: kart B ve D8 lehimi oynamıyor."]},
    ]},
    # B58 (kullanici karari 2026-09-25): dis besleme (XT30, PIL/HARICI secici,
    # F0B giris sigortasi) KALKTI; kutu yalniz kendi pilinden calisiyor. Iki
    # hucre PARALEL (tek TP4056, tek Type-C); analog 24 V yalitilmis B0505S
    # uzerinden. Paketin eksisi = kart GND; -12 rayi B0505S'in OBUR tarafinda.
    # Kalibrasyon (Adim 12) artik bu paketle calisan kutuda yapildigi icin pil
    # blogu buraya, testlerin ONUNE alindi (eskiden Adim 14-15'teydi).
    {"no": 10, "baslik": "Besleme — pil paketi ve analog besleme", "alt": [
        {"no": "10.1", "baslik": "MT1'i 5.0 V'a, MT2'yi 24.0 V'a yüksüz ayarla", "tur": "montaj",
         "vurgu": ["MT1", "MT2"],
         "yap": ["İki MT3608'i tezgahta, <b>yük takmadan</b> ayarla: çıkışı multimetreyle izle, trimpotu "
                 "saat yönü tersine çevir. Fabrika ayarı 28 V'a kadar çıkabilir: <b>ayarlanmamış modülü "
                 "ESP32'ye ya da karta bağlama</b> (28 V ESP32'yi öldürür).",
                 "<b>MT1 → 5.0 V</b>: girişe bir 18650 (3.0–4.2 V). <b>MT2 → 24.0 V</b>: girişe 5 V ver — "
                 "kutuda onu B0505S'in yalıtılmış 5 V'u besleyecek; tezgahta bir USB şarj adaptörü ya da "
                 "az önce ayarladığın MT1'in çıkışı yeter.",
                 "İkisini etiketle: MT1 (5 V), MT2 (24 V).",
                 # B58b: surumler arasinda bacak sirasi FARKLI. B73: Hi-Link govdesinde AD YOK (yalniz
                 # 1. bacak noktasi) -> veri sayfasindan sira; Mornsun'da giris ters.
                 "<b>B0505S'i de tezgahta dene</b> (duvara gitmeden). <b>Gövdede bacak adı yazmaz</b>: yazılı yüz "
                 "sana dönük, bacaklar aşağıdayken noktanın altındaki en soldaki bacak 1. Hi-Link veri sayfası: "
                 "<b>1 = +Vin, 2 = −Vin, 4 = −Vout, 6 = +Vout</b> (3 ve 5 yok) — <b>yan yana duran iki bacak "
                 "GİRİŞ</b>, aralıklı ikisi ÇIKIŞ. ⚠ Mornsun B0505S'te 1 = GND, 2 = Vin: başka markanın şemasına "
                 "bakma; girişi ters beslemek modülü bozar (−0.7 V sınırı). Bacaklara krokodil takma (1–2 arası "
                 "2.5 mm): önce dört bacağa ince tel lehimle (havya ≤ 300 °C, gövdeden ≥ 1.5 mm), makaronla kapla "
                 "— 10.2'de modül zaten böyle takılıyor. Gövdede <b>2WR3</b> yazmalı (1 W sürümü açılışta "
                 "yetmez, B58f). Girişine 5 V (USB şarj adaptörü ya da ayarlı MT1), çıkışında 5–7 V oku "
                 "(yüksüzken regülesiz modül biraz yüksek okur; kutuda MT2 onu yükler). Veri sayfası uzun süre "
                 "yüksüz çalıştırmayı önermiyor: oku ve kapat."],
         "kontrol": ["MT1 çıkışı 4.95–5.05 V (giriş 3.0–4.2 V'ta).",
                     "MT2 çıkışı 23.8–24.2 V (giriş 4.5–5.5 V'ta).",
                     "B0505S: çıkış (6 ↔ 4) 5–7 V (yüksüz); enerjisizken bacak 2 (−Vin) ↔ bacak 4 (−Vout) ötmüyor."]},
        {"no": "10.2", "baslik": "Yuvaları, MT1/MT2'yi, B0505S'i ve hücre sigortalarını tak",
         "tur": "duvar_parca",
         "monte": ["YUVA1", "YUVA2", "MT1", "MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"],
         "vurgu": ["YUVA1", "YUVA2", "MT1", "MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"],
         # B57b (kullanici karari 2026-09-25): yuvalar civata yerine sicak silikon.
         # B73: modüller ve küçük parçalar sıcak silikonla (kullanıcı 2026-09-30); sigorta yuvası
         # iki ayrı klips (FUS009) -> plaket şeridi; MT1/MT2 kabloları tezgahta önceden.
         "yap": ["Arka duvar (içeriden): iki 18650 yuvası üst üste — YUVA1 alt, YUVA2 üst (konum tabloda). "
                 "<b>Sıcak silikonla yapıştır — cıvata yok</b> (kullanıcı kararı): önce yerini kurşun kalemle "
                 "işaretle (sıcak silikonda kaydırma payı birkaç saniye), yuvanın tabanına boydan boya iki "
                 "şerit çek, duvara 10 s bastır. İç kat çubuklarının arasına denk gelen yerde silikonu kalın "
                 "bırak — 2 mm boşluğu doldurur. <b>Yön:</b> YUVA1'in kırmızı telinin çıktığı ucu SOLA (F1P'ye), "
                 "YUVA2'ninki SAĞA (F2'ye). Hücreleri henüz TAKMA (10.5). YUVA2'nin üstü kapağa 6 mm.",
                 "Şarj modülü (TP1) 6.0'da, kart A'dan önce takıldı; burada ona dokunma.",
                 "<b>Tezgahta önce:</b> MT1 ve MT2'ye kablolarını lehimle (TP1 gibi; kutuda pedlere havya rahat "
                 "girmez): teli kartın parça yüzünden sok, alttan lehimle, taşan ucu kes — modülün arkası duvara "
                 "düz otursun. Uçları etiketle. Hangi pede ne geldiği ve kesim boyları 10.3 / 10.4'ün kablo "
                 "tablosunda ve çiziminde (numaralı). MT2'nin IN− ucuna '−12 tarafı' yaz.",
                 "<b>Sigorta yuvası = iki ayrı klips</b> (FUS009), tek gövde değil: iki klipsi kart A'dan artan "
                 "plaketten kestiğin en fazla <b>25 mm</b>'lik bir şeride lehimle — önce sigortayı iki klipse "
                 "tak, bacakları şeride geçir, lehimle; sigorta aralığı kendiliğinden doğru olur. Her klipsin "
                 "iki bacağını altta birleştir; teli klipsin yanındaki boş delikten ön yüzden sok, arkada klips "
                 "bacağına lehimle. Üç şerit: F0, F1P, F2. (Kapaklı KF-03 denendi: 27 × 14 mm ölçüsüyle "
                 "yerleşime sığmıyor — F1P kart A'nın altına giriyor, kapaklar üst üste geliyor.)",
                 "<b>Tutturma — sıcak silikon</b> (kullanıcı kararı 2026-09-30): MT1, MT2, B0505S, 680 µF, KL ve "
                 "üç sigorta şeridi duvara sıcak silikonla; sökmek için izopropil alkol damlat, plastik kartla "
                 "kaldır. Silikon PCB'nin ARKASINA ya da kenarına — çipin ve bobinin üstüne değil (ısınan "
                 "yerler). MT1/MT2'nin trimpotu içe ve erişilebilir kalsın. Kartlar, ESP32, şönt ve Q1 "
                 "yapıştırılmaz.",
                 "MT1 ve MT2 arka duvarın solunda, üst üste (x 43–79; MT1 z 24, MT2 z 47). MT1'in OUT pedleri "
                 "SOLA (F0 ve B0505S), MT2'nin IN pedleri SOLA (B0505S ve 680 µF).",
                 "<b>B0505S (IZ)</b> MT2'nin soluna, bacaklar aşağı, gövdesinden yapıştır. ⚠ Bu modül kutunun <b>iki toprağını ayıran "
                 "TEK parça</b>: giriş tarafı (1 +Vin, 2 −Vin) ile çıkış tarafı (4 −Vout, 6 +Vout) hiçbir telle "
                 "birleşmesin.",
                 "<b>MT2'nin giriş kondansatörü (CB, 680 µF 16 V, C042)</b> MT2'nin üstüne, yatık. Bacaklarını "
                 "MT2'nin giriş pedlerine lehimle: uzun bacak IN+, ⚠ <b>şeritli bacak EKSİ → IN−</b>.",
                 "<b>24 V iç klemensi (KL, CON007)</b> B0505S'in üstüne; vidalar içe. Hangi vidanın + olduğunu "
                 "kalemle yaz: 10.4'te MT2'nin çıkışı ve kartın 24 V telleri aynı kutupla buraya vidalanacak.",
                 "<b>Analog sigortası F0</b> B0505S'in altına, MT1'in soluna (konum tabloda); içine 1 A hızlı cam "
                 "sigorta (FUS003) — şimdilik <b>TAKMA</b>, 10.5'te ilk enerji sırası için çıkarılmış duracak.",
                 "Hücre sigortaları <b>F1P ve F2</b> en alt sırada (konum tabloda); içlerine <b>{pil_sigorta}</b> "
                 "cam sigorta (FUS004). Anma neden bu kadar yüksek: sigorta hücrenin artısında, yani şarj akımı "
                 "da buradan geçiyor ({sarj_akimi}; tek hücre takılıysa tamamı) — daha küçüğü ilk şarjda atar."],
         "kontrol": ["Yuvalar yerinden oynamıyor (silikon soğuduktan sonra elle it).",
                     "Kapak kapanıyor: YUVA2'nin üstü kapağa değmiyor.",
                     "Silikon soğuyunca modülleri elle it; oynamamalı.",
                     "B0505S'in giriş (1, 2) ve çıkış (4, 6) telleri arasında bip: ötmemeli."]},
        {"no": "10.3", "baslik": "Pil paketini kablola (iki hücre paralel)", "tur": "pil_kablo",
         "asama": "paket",
         "vurgu": ["YUVA1", "YUVA2", "TP1", "F1P", "F2", "MT1", "SWP1", "ESP32"],
         "yap": ["TP1'in 6.0'da lehimlediğin dört ucu (B+, B−, OUT+, OUT−) duvarla kart A arasındaki "
                 "aralıktan geliyor; bandı sök, uçları aşağıdaki tabloya göre bağla.",
                 "Aşağıdaki tabloya göre; hücreler <b>TAKILI DEĞİLKEN</b>. İki hücre <b>paralel</b>: her "
                 "hücrenin artısı <b>KENDİ sigortasından</b> (F1P, F2) geçip TP4056'nın <b>B+</b>'sında "
                 "birleşir, eksileri <b>B−</b>'de. <b>H1+ / H2+ doğrudan B+'ya GİTMEZ.</b> Neden: TP4056'nın "
                 "koruma FET'i (FS8205) B− ile OUT− arasında; hücre uçlarındaki ya da hücre kablolarındaki bir "
                 "kısa devre o FET'in DIŞINDA kalır, DW01A bunu <b>kesemez</b>. Paralelde bir de şu var: "
                 "hücrelerden biri içeriden kısa devre olursa öbürü onu sigortasız doldurmaya çalışır.",
                 "Hücre telleri <b>yuvanın kendi telleri</b>: kırmızı (+, yaysız uç) doğrudan sigorta klipsine, "
                 "siyah TP4056 B−'ye. F2'nin çıkışı arka duvar boyunca <b>F1P'nin çıkış klipsine</b> gelir; "
                 "TP4056 B+'ya oradan tek tel gider (iki hücre burada paralel). Yuva teli tablodaki boydan "
                 "kısa gelirse ek yap (lehim + makaron).",
                 "TP4056'da paket <b>B±</b>'ye, yük <b>OUT±</b>'ye. En büyük akım şarjda {sarj_akimi} (iki "
                 "hücreye yarı yarıya); 0.5 mm² bunu rahat taşır, kalın kablo gerekmez.",
                 "<b>PİL anahtarı (SWP1)</b> paket tarafında: TP1.OUT+ → PİL → MT1 girişi. Kapalıyken MT1 "
                 "hiç çekmez; kutunun tek anahtarı bu. KTS102'nin <b>orta</b> bacağı TP4056 OUT+'ya; öbür tel, "
                 "anahtar AÇ konumundayken orta bacakla <b>öten</b> dış bacağa (multimetreyle bul).",
                 "MT1'in 5 V çıkışı ESP32'ye: devkit'te tek 5V pini var ve 11.1'de J5 kablosunun 5V teli de "
                 "oraya takılacak — <b>çatal</b> yap: dişi header'dan (CON018) tek pinlik bir parça kes, MT1'in "
                 "5 V telini ve J5 kablosunun 5V telini İKİSİNİ BİRDEN onun kuyruğuna lehimle, makaronla kapla; "
                 "bu tek dişi uç devkit'in 5V pinine geçer (erkek pine erkek header takılmaz). GND için devkit'in "
                 "ikinci GND pini.",
                 "⚠ <b>İlk takışta iki hücre aynı gerilimde olmalı (±0.1 V)</b>: farklıysa yüksek olan alçak "
                 "olanı büyük akımla doldurur. Takmadan önce ikisini ayrı ayrı ölç; fark büyükse önce "
                 "<b>yalnız birini</b> tak ve 10.6'daki gibi tam doldur (4.2 V), çıkar, ötekini tak ve "
                 "doldur, sonra ikisini birlikte tak."],
         # B73 §4.4: eski "TP1.B− ↔ kart GND öter" J5'ten (11.1) önce fiziksel olarak imkânsızdı.
         "kontrol": ["1. ve 2. yuvanın siyah teli ↔ TP4056 B−: ötmeli. F1P'nin ve F2'nin çıkış klipsi ↔ "
                     "TP4056 B+: ötmeli.",
                     "Paket eksisi kart GND'ye J5 kablosuyla bağlanır — o kontrol 11.1'de (şimdi ötmemesi "
                     "NORMAL: FS8205'in gövde diyotları hücresizken B− ile OUT−'yu da ayrı tutar).",
                     "PİL kapalı: TP1.OUT+ ↔ MT1.IN+ ötmemeli; açık: ötmeli.",
                     "F1P çıkarılınca H1+ ↔ TP1.B+ kesik; F2 çıkarılınca H2+ ↔ TP1.B+ kesik (her sigorta "
                     "gerçekten kendi hücresinin yolunda)."]},
        {"no": "10.4", "baslik": "Analog beslemeyi kablola: 5 V → F0 → B0505S → MT2 → klemens → kart",
         "tur": "pil_kablo", "asama": "analog", "kablo": [0, 1],
         "vurgu": ["F0", "IZ", "MT2", "KL", "A"], "monte": ["J6"],
         "yap": ["Kartın 24 V girişinin telleri (<b>J6</b>: C34 kırmızı, C36 siyah) klemense <b>vidalanır</b> — "
                 "kart lehim sökmeden çıkar. Tellerin ucunda tezgahtan kalan <b>XT30 erkek</b> varsa kes: dış "
                 "besleme yok, XT30 kullanılmıyor.",
                 "Aşağıdaki tabloya göre: 5 V barası (MT1 çıkışı) → <b>F0</b> ({f0_sigorta}, kutu içi, "
                 "10.2) → B0505S bacak 1 (+Vin); bacak 2 (−Vin) → 5 V barasının eksisi. "
                 "B0505S bacak 6 (+Vout) → MT2 IN+, bacak 4 (−Vout) → MT2 IN−; MT2 çıkışı → klemens (+ → C34, − → C36).",
                 "<b>CB (680 µF)</b> MT2'nin giriş uçlarına, B0505S'in telleriyle aynı noktaya: uzun bacak "
                 "→ IN+, şeritli bacak → IN−. Neden: açılışta MT2 kartın 136 µF'sini doldururken B0505S'in "
                 "veremeyeceği tepe akımı çekiyor; kondansatör yoksa MT2 girişini çökertip baştan başlıyor ve "
                 "kart 24 V'a çıkamayabilir (B58f benzetimi).",
                 "<b>Kural (denetimli):</b> B0505S'in çıkış tarafı (MT2 girişi, klemens −, kartın −12 rayı) "
                 "kart GND'ye hiçbir yoldan <b>DEĞMEZ</b>. Kutunun iki toprağını ayıran tek parça B0505S: iki "
                 "tarafı birleştiren tek bir tel −12'yi GND'ye kısa eder.",
                 "Neden F0 5 V tarafında: analog zincirindeki bir arıza (B0505S, MT2, kart) paketi ve 5 V "
                 "barasını çekemesin. 24 V tarafını ayrıca korumaya gerek yok — kartın kendi F1'i orada, "
                 "B0505S'in gücü de 1–2 W ile sınırlı ve kısa devrede kendini keser.",
                 "Sigorta: kartta F1. Açılışta kartın 136 µF'si dolar; B58'den beri anahtar 5 V tarafında ve "
                 "24 V B0505S + MT2 üzerinden yükseliyor, yani darbe sert bir 24 V kaynağındakinden yumuşak — "
                 "ama hesap en kötü hâli (sert kaynak) varsayıyor: gerçek bir 50 mA <b>hızlı</b> (F) sigortayı "
                 "bu darbe <b>atar</b> (darbe I²t erime değerinin 3–5 katı — Littelfuse 217/218 veri "
                 "sayfaları, denetim hesaplıyor). "
                 # B55n (kullanici 2026-09-24): "su anda 50 mA takili ancak hic
                 # atmadi; T alimini sonraki plan olarak aklimizda tutalim."
                 # B52'nin OLCUMU (0.4 ohm) bunun 400 mA sinifi oldugunu soyluyordu;
                 # olcumu silmiyoruz ama karar kullanicinin: simdilik takili kalsin.
                 "<b>Karar (2026-09-24): takılı sigorta kalıyor, T sonraki plana.</b> Şu an yuvada "
                 "'50 mA' duruyor ve 20+ açmada <b>hiç atmadı</b> — bu tek başına iyi haber ama "
                 "<i>hangi</i> sigorta olduğunu söylemiyor: gerçek bir 50 mA F bu darbede atardı. "
                 "B52'de ölçülen <b>{r400:.1f} Ω</b>, 50 mA olamaz (50 mA'lık tel {r50f:.0f}–{r50t:.0f} Ω okur) — {r400:.1f} Ω "
                 "<b>400 mA</b> sınıfıdır. İkisi birlikte tek bir şey söylüyor: yuvadaki etikete "
                 "bakma, <b>ohmmetreye bak</b>. Merak edersen sigortayı çıkar, soğukken direncini "
                 "ölç: <b>{r50f:.0f}–{r50t:.0f} Ω</b> → gerçekten 50 mA (o zaman T tipidir, çünkü atmadı); "
                 "<b>{r400:.1f} Ω</b> civarı → 400 mA sınıfı (FUS001). Her iki hâlde de <b>kısa devre koruması var</b> ve "
                 "kutu kurulumu beklemiyor. İleride <b>T (gecikmeli) 50 mA cam</b> (Littelfuse "
                 "218.050 / ESKA / Schurter, pay ≥ 10×) alınırsa takılır ve 20 kez aç-kapa denenir: "
                 "her açılışta +12/−12 gelmeli. Stoktaki FUS010 F tipi, 315 mA F de darbeye pay "
                 "vermiyor — ikisi de değiştirmeye değmez. TL072 kısmi arızasını hiçbir sigorta açmaz.",
                 # B73 §4.3: katodun "kart GND" noktasi muglakti; MT1 eksisi J5'ten (11.1) once kart
                 # GND'ye bagli DEGIL -> 10.5'te lamba yanmazdi. COM jakinin kulagi = C6 = kart GND.
                 "<b>GÜÇ lambası:</b> 10 kΩ direnci (R060) LED'in <b>uzun bacağına</b> lehimle, makaronla "
                 "kapat; direncin öbür ucu <b>klemensin ARTI</b> ucuna (KL.+ = +12 rayı). LED'in kısa bacağı "
                 "(katot) <b>COM jakının lehim kulağına</b> (= kart GND; tablodaki kablo {led_k_no}, {led_k_kesim} cm). ⚠ MT1'in eksisine "
                 "bağlama: o nokta kart GND'ye ancak 11.1'deki J5 ile bağlanır, 10.5'te lamba yanmaz. ⚠ "
                 "Klemensin EKSİ ucuna da bağlama: −12 rayıdır, 7912 o yönde akım veremez, ray kayar."],
         "kontrol": ["B0505S bacak 2 (−Vin) ↔ bacak 4 (−Vout): <b>ötmemeli</b> (yalıtım sağlam).",
                     "Klemens − (C36) ↔ kart GND (C29): ötmemeli.",
                     # B58: XT30 KODLUYDU (ters takilamaz); vidali klemens degil. Ters 24 V iki
                     # TL072'yi oldurur ve TVS bunu koruyamaz (B15/F8) — enerjiden ONCE olc.
                     "<b>Kutup (enerjiden ÖNCE):</b> klemens + ↔ MT2 OUT+ ve kartın C34'ü ötmeli; klemens − ↔ "
                     "MT2 OUT− ve C36 ötmeli. Ters olursa ilk enerjide iki TL072 ölür (XT30 kodluydu, "
                     "klemens değil).",
                     "F0 takılıyken 5 V barası ↔ B0505S Vin bağlı; F0 çıkarılınca kesik (sigorta gerçekten "
                     "yolda).",
                     "<b>CB kutbu (enerjiden ÖNCE):</b> kondansatörün şeritli bacağı ↔ MT2 IN− ötmeli; ters "
                     "takılan elektrolitik ilk enerjide ısınır ve patlar."]},
        {"no": "10.5", "baslik": "Kutuda ilk enerji — pilden", "tur": "kontrol",
         "yap": ["Soketlerdeki entegreler takılı değil (11.1'de takılacak), J5 kablosu takılı değil, PİL "
                 "KAPALI, USB takılı değil, <b>F0 yuvasında sigorta YOK</b> (ölçüm tarafı önce kapalı kalsın).",
                 "Hücreleri tak (kutuplara dikkat; ±0.1 V kuralı 10.3'te). <b>PİL AÇ</b>: 5 V barasında "
                 "4.95–5.05 V, ESP32 açılır. Klon devkit'te VBUS diyotu olmayabilir: USB soketinin VBUS ucunda "
                 "<b>0 V</b> oku. 5 V okursan MT1 USB'ye geri besliyor → ESP32'ye giden 5 V telinin arasına "
                 "stoktaki Schottky <b>SR5100</b> (D004; çizgili uç ESP32'ye) koy, makaronla kapla ve MT1'i "
                 "<b>5.3 V</b>'a çıkar (diyotta ~0.4 V düşer).",
                 "PİL'i kapat, <b>F0'ı tak</b> (1 A), PİL'i yeniden aç: klemenste 24.0 V, kartta +12 V / −12 V "
                 "(V35 / R33, GND: V36); GÜÇ lambası yanar.",
                 # B58f: B0505S'in asiri yuk davranisi veri sayfasinda yok; benzetim dort modeli
                 # tariyor. Dolu pilde hepsi aciliyor; yarim pilde guclu modelde DW01A kesebilir,
                 # 3 ohm seri direnc onu cozer ama hiccup tipli modulde 24 V'u engeller.
                 "<b>Kutu açılmazsa</b> (PİL açınca ESP32 hiç açılmıyor ya da bir an yanıp sönüyor, GÜÇ lambası "
                 "yanmıyor): paketin koruması (DW01A) açılış akımında kesmiş. PİL'i kapat, 2 saniye bekle, "
                 "yeniden aç. Sürerse pili 10.6'daki gibi <b>doldur</b> ve dene — benzetimde dolu pilde B0505S'in "
                 "dört davranış modelinin hepsi açılıyor. Dolu pilde de açılmıyorsa: PİL'i kapat, B0505S'in +Vo teli "
                 "ile MT2'nin IN+ ucu arasına <b>3 × 1 Ω 1 W</b> direnci (R052) seri lehimle, makaronla kapla, "
                 "dene. Yine olmuyorsa TP4056 modülünü stoktaki yedekle değiştir (MOD002, 6.0'daki gibi). "
                 "<b>24 V gelmiyorsa</b> (ESP32 açık ama klemenste 24 V yok ya da GÜÇ lambası yanıp sönüyor): "
                 "seri direnç takılıysa <b>çıkar</b> — bu B0505S aşırı yükte kapanıp yeniden deneyen türden, "
                 "direnç ona fazla gelir; takılı değilse CB'nin iki bacağının MT2 girişine lehimli olduğuna ve "
                 "kutbuna bak.",
                 "Skopla −12 rayına bak (MT3608 + B0505S dalgalanması): 50 mV üstü görürsen MT2 çıkışına "
                 "68 µF 50 V (C035) + 100 nF (C008) ekle (5.12.23'ün gürültü endişesi burada ölçülür). "
                 "⚠ Stoktaki 100 µF'lerin çoğu 16 V — 24 V rayına TAKMA, patlar.",
                 "🛑 <b>Ölçtükten sonra PİL'i KAPAT.</b> Sıradaki adım (11.1) soketlere entegre, ADS "
                 "modülü ve 10 telli J5 kablosu takıyor — bunlar <b>enerjili karta takılmaz</b>: yanlış oturan "
                 "bir entegre ya da ters takılan bir modül anında ölür."],
         "kontrol": ["+12 V: +11.5 … +12.5 V. −12 V: −11 … −13 V.",
                     "−12 rayı ↔ kart GND arasında gerilim <b>≈ −12 V</b> (0 V okursan B0505S'in iki tarafı bir "
                     "yerde birleşmiş — hemen kapat).",
                     "10 dk sonra MT1, B0505S, MT2 ve 7912 ılık, sıcak değil."]},
        {"no": "10.6", "baslik": "Şarj kuralı ve etiket", "tur": "kontrol",
         "yap": ["Şarj: <b>PİL anahtarını KAPAT</b>, sonra ŞARJ yuvasına <b>tek Type-C</b> tak — iki hücre "
                 "birlikte dolar ({sarj_akimi}, hücre başına yarısı). PİL açıkken şarj etme: TP4056 yük "
                 "altında şarjı bitiremez.",
                 "⚠ Şarj sırasında kutunun toprağı (COM) şarj cihazının toprağına bağlanır: <b>şarj ederken "
                 "ölçüm yapma</b>, HV'de asla.",
                 "Etiket (arka panele, ŞARJ yuvasının yanına): \"ŞARJ: PİL kapalı · şarjda ölçüm yok\"."],
         "kontrol": ["TP4056'nın LED'i şarjda kırmızı, bitince mavi (kapak açıkken kart A'nın arka "
                     "kenarından bakınca). Kapak kapalıyken ışık yuvanın kenarından ancak loş sızar — "
                     "göremiyorsan ≈ {sarj_suresi} bekle.",
                     "USB'yi çıkar, PİL AÇ: ESP32 açılıyor, WiFi paneli geliyor, GÜÇ lambası yanıyor — "
                     "kutu tamamen kablosuz."]},
    ]},
    {"no": 11, "baslik": "ESP32 ve ilk iki kapı", "alt": [
        {"no": "11.1", "baslik": "J5 kablosu ve entegreler", "tur": "montaj",
         "vurgu": ["ESP32", "A"],
         "yap": ["PİL KAPALI (10.5'te kapattın). Soketlere entegreleri tak: U3, U4 (LM358), "
                 "U5, U8 (TL072). Çentik yönü.",
                 "ADS modüllerini yuvalarına tak.",
                 "J5 başlığına 10 telli kabloyu tak (eşleme Yerleşim 1.12). "
                 "<b>3V3 ile 5V'u karıştırma.</b>",
                 "CAL jakı: devkit GPIO10 pinine tek dişi jumper, ucuna {cal_r} ({cal_stok}) seri, jakın iç ucuna "
                 "lehim; jumper'ı SCL (GPIO9) pininin yanından dikkatle ayır.",
                 "USB'yi devkit'in COM yazan soketine, arka yuvadan tak."],
         "kontrol": ["Entegre çentikleri doğru yönde.", "10 tel doğru pinde.",
                     # B73 §4.4: paket eksisi ile kart GND arasindaki TEK bag J5 (ESP32 GND uzerinden)
                     "J5 takılınca, hücreler takılı değilken: TP4056 OUT− ↔ kart GND (C29): ötmeli (paket "
                     "eksisi = kart GND; bağ ESP32'nin GND'si ve J5 üzerinden)."]},
        {"no": "11.2", "baslik": "Vref ve I²C kapıları", "tur": "kapi", "kapi": [1, 2],
         # B55n: bu adimin metni YALNIZ WiFi ayariydi; basligindaki iki kapinin
         # olcutu (nereden, ne kadar, tutmazsa ne) hicbir yerde yoktu. Kullanici
         # artik soru soramiyor -> sayilar tasarim3_sabit'ten uretiliyor.
         "yap": ["<b>Enerji:</b> PİL AÇ. Seri konsol için USB'yi PC'ye takabilirsin — PİL açıkken yükü pil "
                 "taşır (MT1'in 5.0 V'u USB'nin ~4.7 V'unu bastırır). <b>PİL kapalıyken USB takma:</b> ölçüm "
                 "tarafı da PC'den beslenmeye çalışır (~0.35 A, USB 2.0 portunun sınırına yakın).",
                 "<b>Kapı 1 — Vref.</b> Multimetre kart GND'ye referanslı: "
                 "① <b>TL431 katodu</b> = {tl431:.3f} V (±%2 → {tl431_alt:.3f}–{tl431_ust:.3f} V). "
                 "② <b>U3'ün 1. bacağı (delik A:R8)</b> = {vref:.4f} V (±10 mV). "
                 "③ Aynı ölçümü bölücüler bağlıyken tekrarla — <b>kaymıyorsa tampon çalışıyor.</b> "
                 "<i>Tutmazsa:</i> ① yanlışsa TL431 yönü / 220R besleme; ① doğru ② yanlışsa U3 "
                 "soketi, çentiği ya da U3'ün +5 V beslemesi (3.3 V'ta çıkış yeterince yükselmez).",
                 "<b>Kapı 2 — I²C.</b> Seri konsolda <code>#</code>: <b>0x48 ve 0x49 ikisi de</b> "
                 "listede görünmeli. <i>Tutmazsa:</i> SDA/SCL ters, ADDR ucu boşta (0x48 = GND, "
                 "0x49 = +3V3) ya da pull-up yok. <b>Bir adres eksikken kalibrasyona geçme</b> — "
                 "eksik olan kanal sessizce sıfır okur.",
                 "İki kapı da geçmeden Adım 12'ye başlama.",
                 "WiFi ayarları seri konsoldan: <code>Ns&lt;web parolası&gt;</code>, "
                 "<code>Na&lt;ssid&gt;</code>, <code>Np&lt;parola&gt;</code>; durum <code>N?</code>."]},
    ]},
    {"no": 12, "baslik": "Kalibrasyon ve kalan kapılar", "alt": [
        {"no": "12.1", "baslik": "Kalibrasyon", "tur": "kalibrasyon"},
        {"no": "12.2", "baslik": "Kapı 3 — akım (iki aşamalı)", "tur": "kapi", "kapi": [3],
         "yap": ["<b>Kural:</b> test kaynağı kutudan <b>bağımsız</b> olmalı. Kutunun kendi pil paketi OLAMAZ: "
                 "paketin eksisi kart GND'dir, ondan YÜK'e akım çekersen dönüş akımı kart GND telinden (J5 "
                 "kablosu) geçer — ölçüm bozulur, ince tel ısınır. Test kaynağı: <b>tezgah beslemesi</b> "
                 "(WCT-200-24 + MOD011 buck, <b>{test_v:.1f} V</b>'a ayarlı) → <b>3.3 Ω 11 W (R049)</b> ≈ "
                 "{test_i:.1f} A. WCT artık kutuya bağlı değil (B58): yalıtılmış bir test kaynağı.",
                 "Firmware kazanç kalibrasyonunu tam skalanın %5'inin (1638 kod) altında reddeder: 5 mΩ ile "
                 "bu 2.6 A demek, 1.1 A yetmez. Kazanç düzeltmesi (<code>i</code>) şöntten bağımsızdır → "
                 "<b>önce 15 mΩ (R044) tak</b>, <code>s0.015</code>, <code>Z</code> yüksüzken; buck + 3.3 Ω "
                 "YÜK 1–2'den seri, multimetre 10 A kademesi seriye, <code>i&lt;ölçülen&gt;</code>.",
                 "Sonra <b>5 mΩ'u tak</b>, <code>s0.005</code>, <code>Z</code>; aynı ~1.1 A'i ölç: multimetreyle "
                 "±%2 tutmalı. ≥2.6 A için: buck 3.9 V + üç 3.3 Ω paralel "
                 "(1.1 Ω, ≈3.5 A, 30 s; MOD011 10 A'lik) ile <code>i</code>. Kabloları ters çevir: işaret "
                 "değişmeli.",
                 # B67: iki asamali yolda 5 mOhm'un GERCEK degeri hic duzeltilmiyordu. Veri sayfasi ±%5, Kelvin
                 # lehiminin yeri mm basina ~%4 (Ø1.6 manganin 0.22 mOhm/mm) — ±%2 kapisi tutmayabilir ve metin
                 # tutmazsa ne yapilacagini soylemiyordu.
                 "<i>±%2 tutmazsa:</i> şöntün görünen değeri 5 mΩ değil (veri sayfası ±%5, Kelvin lehiminin yeri "
                 "mm başına ~%4 oynatır). Kart <b>X</b> A, multimetre <b>Y</b> A okuyorsa <code>s</code> değerini "
                 "0.005 × X ÷ Y yap (ör. X 1.15, Y 1.10 → <code>s0.00523</code>), <code>Z</code>, yeniden ölç. "
                 "Ya da ≥2.6 A yoluyla 5 mΩ takılıyken doğrudan <code>i</code> ver: o zaman şöntün gerçek değeri "
                 "kazanca girer, <code>s</code>'ye dokunma."]},
        {"no": "12.3", "baslik": "Kapı 4 — NORMAL gerilim", "tur": "kapi", "kapi": [4],
         "yap": ["<code>n</code>; <b>V jakını kısa bir kabloyla COM'a bağla</b> (gerçek 0 V) ve <code>z</code>, "
                 "sonra kabloyu çıkar. ⚠ Boştaki V jakında <code>z</code> verme: giriş havada kalır ve okuma "
                 "Vref civarına (~1.5 V) oturur; sıfır o noktaya kurulursa bütün okumalar o kadar kayar "
                 "(2026-10-04 kartta: boşta 1.456 V, kısa devrede −0.23 V). Bilinen gerilimi (tezgah beslemesi 5–12 V — kutunun "
                 "kendi pili DEĞİL, 12.2 kuralı) V–COM'a ver, multimetreyle kıyasla, "
                 "<code>g&lt;ölçülen&gt;</code>; ters bağla: işaret değişmeli."]},
        {"no": "12.4", "baslik": "Kapı 5 — YÜKSEK gerilim", "tur": "kapi", "kapi": [5],
         "yap": ["<code>y</code>; önce <b>HV jakını kısa bir kabloyla COM'a bağla</b>, <code>z</code>, kabloyu "
                 "çıkar (12.3'teki gibi; boştayken sıfırlama yapma). Sonra 12 V (tezgah beslemesi), sonra 24 V (WCT'nin kendi çıkışı). Kutu "
                 "B58'den beri yalnız kendi pilinden çalışıyor: WCT kutuya bağlı değil, burada serbestçe "
                 "test kaynağı olur. (Eski düzende WCT kutuyu beslerdi ve eksisi −12 rayıydı — o kural kalktı.)",
                 "Kazanç kalibrasyonu ≥31 V ister: iki <b>yalıtılmış</b> kaynağı seri bağla (varsa) ya da HV "
                 "kazancını fabrika 1.0'da bırak (bölücü %1 metal film, hata ≤ %1). <b>Tek el kuralı.</b>"]},
        {"no": "12.5", "baslik": "Kapı 6 — osiloskop", "tur": "kapi", "kapi": [6],
         "yap": ["Sinyal kaynağı: kartın CAL çıkışı — seri konsolda <code>X&lt;hz&gt;</code> "
                 "ile aç, <code>x</code> ile kapat; panelde <b>CAL jakı → SKOP jakı</b> kısa kablo (COM zaten "
                 "ortak). <code>t</code> komutlarıyla yakala; kare dalga ve frekans görünmeli. Genlik 3.3 V DEĞİL "
                 "≈2.7 V görünür: CAL'in 22 kΩ seri direnci ile skop girişinin ~103 kΩ'u (R20 100 kΩ + R23 2.7 kΩ) "
                 "bölücü kurar, 103/125 ≈ %82 (eski '1 kΩ seri, ≤ %1' notu B55g'de 22 kΩ'a geçilince eskidi)."]},
        {"no": "12.6", "baslik": "Kapı 7 — hızlı akım yolu", "tur": "kapi", "kapi": [7],
         "yap": ["Dirençsel yük (tezgah beslemesi + 3.3 Ω, 12.2 kuralı) YÜK'ten; <code>w</code> → PF ≈ 1."]},
        {"no": "12.7", "baslik": "Kapı 8 — pil testi", "tur": "kapi", "kapi": [8],
         "yap": ["Failsafe: PİL kapalıyken ve RESET'te Q1 kapısı 0 V (PİL 1 ↔ PİL 2 ötmemeli).",
                 "Pil yerine <b>tezgah beslemesi</b> (buck 4.0 V; kutudaki hücreler paketin parçası, "
                 "çıkarma) + 3.3 Ω 11 W, PİL 1 – PİL 2 ve V jakıyla (KULLANIM: pil kapasitesi): "
                 "<code>P3.5</code>, <code>p1</code> → ≈1.2 A akmalı. Buck'ı yavaşça 3.4 V'a indir: "
                 "kart testi <b>kesmeli</b> (akım 0, Q1 kapısı 0 V). Kesme eşiğini böyle gerçek "
                 "bir pilden daha kesin sınarsın."]},
    ]},
    {"no": 13, "baslik": "Kapak — yap, del, dene (henüz kapatma)", "alt": [
        {"no": "13.1", "baslik": "Kapağı yap", "tur": "taban", "kapak": True,
         "yap": ["Kapak sıralarını taban gibi diz (ek yerleri kaydırmalı), altına iki rayı "
                 "direklerin arasına yapıştır. Raylar 18 mm yüzü dik (aşağı sarkar). "
                 "⚠ <b>Rayları yan duvara YASLAMA — her birini {ray_payi:.1f} mm içeri al</b> "
                 "(toplam {ray_payi_toplam:.1f} mm geçme payı). Yaslarsan kapak takımı açıklığın "
                 "tam kendisi kadar olur ve girmez; çubuk toleransı ve ahşabın nemle oynaması "
                 "bu payı yiyor. Kapağı ters çevirip düz zeminde dizerken araya bir kartvizit "
                 "koyarsan pay kendiliğinden çıkar.",
                 # B55g: bu adim FIZIKSEL OLARAK YAPILAMIYORDU. 4.7 yalniz DUVARI deliyor;
                 # civatanin yolunda 2 mm'lik kapak rayi duruyor ve onu delen adim yoktu.
                 # Cozum DELME'nin kendi yontemi ("Ic kat (5.1)"): dis delik kilavuz olur.
                 "<b>Rayları del:</b> kapağı yerine koy, yan duvardaki dört Ø{m3_cap:.1f} deliğin "
                 "arkasında 2 mm'lik kapak rayı var ve orada delik yok. Havya ucunu <b>dıştaki "
                 "delikten geçirip rayı da del</b> — delik kılavuz olduğu için eş eksenli çıkar, "
                 "işaretleme yok (5.1'deki iç kat yöntemi). Kapağı kaldırmadan yap.",
                 # B55n: blok RAYIN IC YUZUNE yapisiyor, yani kutunun icine. Kapak
                 # takiliyken oraya el girmiyor (kutunun tek acikligi kapagin kendisi).
                 # Cozum: blok kapak TEZGAHTAYKEN, yalnizca raya takilan civatayla
                 # merkezlenerek yapistirilir — duvara hic gerek yok, hizalama yine
                 # civatadan geliyor.
                 "<b>Somunlu blokları KAPAK TEZGAHTAYKEN yapıştır — kutunun içinde değil.</b> "
                 "Rayları deldikten sonra <b>kapağı kaldır</b> ve ters çevirip masaya koy (raylar yukarı). "
                 "Her ray deliğine <b>dıştan</b> (rayın duvara bakan yüzünden) bir {kapak_civata} cıvata sok; "
                 "ucuna <b>gömme somunlu {kapak_somun_kat} katlı bloğu</b> (1. kat Ø3.2 · 2.–3. kat "
                 "Ø{cep_cap:.1f} somun cebi · {kapak_somun_kat}. kat Ø{son_delik:.1f}) — somunun dış yüzüne "
                 "bir damla japon ({cep_yapistirici}), 6.1'deki ayak bloğunun aynısı — vidala. "
                 "Blok şimdi cıvatanın üstünde <b>kendi kendine merkezlenmiş</b> durumda: temas yüzüne japon "
                 "sür, rayın iç yüzüne bastır. Kuruyunca cıvatayı sök. İki bağımsız ölçüm tutturmaya "
                 "çalışmazsın; kapak kapalıyken içeride somun tutulamadığı için bu blok şart (B54).",
                 "Kapağı yapıştırma."],
         "kontrol": ["Kapak oturuyor, raylar yan duvarlara sürtmeden giriyor."]},
        {"no": "13.2", "baslik": "Kapağı dene — sonra ÇIKAR", "tur": "taban", "kapak": True,
         "yap": ["Bloklar kuruyunca dört <b>{kapak_civata}</b> cıvatayı pul ile sık: bir kez tam sık, "
                 "tak-çıkarı dene. Tahtada diş yok, içeriye el girmez. (Delikler 4.7'de açıldı.)",
                 "<b>Sonra cıvataları sök ve kapağı KALDIR — kapak Adım 14'e kadar açık kalır.</b> "
                 "Son toplama (14.1) kutunun içinde kablo bağı atıyor: kapak takılıyken yapılamaz.",
                 "Kapak bu adımda <b>bitmiş ve denenmiş</b> oluyor; kutunun üstünde durmuyor. Kapatma Adım 14'te."],
         "kontrol": ["Cıvatalar takılıyken kapak elle çekince kalkmıyor.",
                     "Cıvatalar söküldü, <b>kapak kutunun üstünden alındı</b> — kutu yine açık.",
                     "Dört delik de rayın somun bloğuna denk geliyor (cıvata boşta dönmüyor)."]},
    ]},
    # Kutunun KAPANDIGI adim — kutu icine giren her is (montaj, kablo, duvar
    # parcasi) bundan ONCE biter; kutu.py bunu adim adim olcuyor (B55: eskiden
    # kapak 13'te kapaniyor, 14-15 pil blogu kapali kutunun icine giriyordu).
    # B58: pil blogu Adim 10'a tasindi, eski 14-15 kalkti -> kapanis 16'dan 14'e.
    {"no": 14, "baslik": "Kapat ve son kontrol", "alt": [
        {"no": "14.1", "baslik": "Etiketle ve topla", "tur": "kontrol",
         # B55n: etiket listesi ELLE yazilmisti ve panel verisinden kaymisti — CAL,
         # F0, GUC, SARJ 1/2 ve uc toggle listede hic yoktu. Artik PANEL_ON /
         # PANEL_ARKA'dan uretiliyor; denetim her etiketin metne girdigini olcuyor.
         "yap": ["<b>Panelin bütün etiketlerini yaz/yapıştır</b> — eksiksiz liste: {panel_etiketleri}",
                 "Arka panele ŞARJ yuvasının yanına şarj kuralı etiketi (10.6). "
                 "USB yuvasının yanına: ⚠ HV varken USB'yi çıkar.",
                 "Kabloları kablo bağıyla topla; HV kablosu tek başına ve diğerlerinden "
                 "≥ 20 mm.",
                 "<b>Kutu prensibi:</b> değerli parçalar (kartlar, ESP32, şönt, Q1) yapıştırılmaz; "
                 "18650 yuvaları, modüller (MT1, MT2, B0505S), 680 µF, KL ve sigorta şeritleri sıcak "
                 "silikonla tutuyor. Başka kaba geçerken vidaları ve kablo bağlarını sök, konnektörleri "
                 "ayır; silikonlu parçaları izopropil alkol damlatıp plastik kartla kaldır."],
         "kontrol": ["Kutuyu salla: içeride oynayan bir şey yok.",
                     "Kapak henüz açık: içeride unutulan alet, tel kırpıntısı, vida yok."]},
        {"no": "14.2", "baslik": "Kapağı tak ve cıvatala", "tur": "taban", "kapak": True, "kapanis": True,
         # B55g: "13.2'de acilan" eskimisti — delikler B55d'de 4.7'ye tasindi
         # (13.1 rayi deliyor). Ustteki 13.1/13.2 metinleri dogruydu, bu kalmisti.
         "yap": ["Kapağı (13.1'de yapıldı) yerine koy; 4.7'de açılan dört delikten "
                 "<b>{kapak_civata}</b> cıvatayı pulla dıştan tak, raydaki gömme somuna sık.",
                 "<b>Kutu burada kapanıyor:</b> bundan sonra kutunun içine giren iş yok. İçeride bir "
                 "şey değiştirmek gerekirse dört cıvata sökülür, kapak kalkar — kartlar ve pil bloğu "
                 "vida/kablo bağıyla tutulduğu için hiçbir şey kırılmaz.",
                 "Hücreler yerinde mi, son kez bak (10.5'te takılmıştı): yuvalar kapak altında kalıyor, "
                 "hücre değiştirmek için kapağı açman gerekir. Şarj için gerekmez — ŞARJ yuvası dışarıda."],
         "kontrol": ["Kapak dört cıvatayla sıkı; elle çekince kalkmıyor.",
                     "Kapak ile en yüksek parça (18650 yuvası / Q1 soğutucusu) arasında boşluk var, "
                     "kapak hiçbir şeye bastırmıyor."]},
        {"no": "14.3", "baslik": "Kapalı kutuda uçtan uca", "tur": "kapi", "kapi": [4, 3],
         # B55l: bu adim "18650 + 3.3 ohm" istiyordu ama stokta TAM 2 hucre var ve
         # ikisi de kutuya kilitleniyor. B58: kutu artik yalniz kendi pilinden
         # calisiyor ve WCT kutuya bagli degil -> test kaynagi tezgah beslemesi.
         "yap": ["Kapak kapalı, her şey panelden. Kutu <b>kendi pilinden</b>: PİL AÇ, USB takılı "
                 "DEĞİL — okumaları WiFi panelinden al. Test kaynağı <b>tezgah beslemesi</b> (buck "
                 "{test_v:.1f} V, 12.2 kuralı) → 3.3 Ω / 11 W → <b>YÜK 1 – YÜK 2</b>; V jakını buck'ın "
                 "artısına bağla. Kartın V ve I okuması multimetreyle <b>±%1 / ±%2</b> içinde olmalı.",
                 "CAL → SKOP kısa kabloyla: panelde kare dalga görünüyor.",
                 "5 dk sonra kutunun hiçbir yüzü elde ısı hissettirmiyor.",
                 "<b>Pil kapasite testini gerçek bir pille sınamak istersen</b> (isteğe bağlı): kutudaki iki "
                 "18650 paketin parçası, onları çıkarma — üçüncü bir hücre al."],
         "kontrol": ["V okuması multimetreyle ±%1 içinde.",
                     "I okuması multimetreyle ±%2 içinde.",
                     "SKOP'ta CAL'in kare dalgası görünüyor."]},
    ]},
]

# ── delik acma: matkapsiz yontem (B52h, kullanici: "elimde matkap yok") ─
# Dil basacagi 2 mm huş; lif boyuna, kenara yakin delikte yarilir. Butun
# olculer DELIGIN MERKEZI (parcanin sol ucundan x, cubugun alt kenarindan z);
# oval yuvada da merkez, 14 x 9 = genislik x yukseklik.
DELME = [
    ("İşaretle", "Cetvelle parçanın sol ucundan x'i, alt kenarından z'yi ölç, iki çizgi çek; kesişme deliğin "
                 "MERKEZİ. Pergel yoksa çapı/2'yi işaretleyip küçük bir daire çiz (Ø6.5 için 3.25 mm)."),
    ("Kılavuz", "Merkeze biz / kalın iğne / çivi ucuyla hafifçe bastırıp döndürerek 1–2 mm çukur aç. "
                "ÇAKMA yok — çakılan çivi 2 mm çubuğu lif boyunca yarar."),
    ("Delme (havya)", "Havyanın eski konik ucunu (350 °C) merkeze dik bastır; 5–10 s'de 2 mm tahtayı geçer, "
                      "~3 mm yanık delik açar. Altına fire çubuk koy, pencereyi aç (duman). Yarmaz, en güvenli "
                      "matkapsız yol. Yanık kenar jakın flanşı/somunu altında kalır."),
    ("Delme (matkap ucu elle)", "Matkap ucun varsa 3 mm'lik ucu penseyle tutup elle döndürerek de geçer "
                                "(2 mm tahta, ~1 dk). El matkabı / pin vise (100–200 ₺) M3 deliklerini "
                                "dakikaya indirir — Ø6–8 için yine büyütme gerekir."),
    ("Büyütme", "3 mm'lik deliği maket bıçağının ucunu döndürerek ya da kalem/marker üstüne sarılı 120'lik "
                "zımparayla çapa getir: <b>Ø5 için bıçak ucu ya da tornavida sapına sarılı zımpara</b> "
                "(havyanın açtığı ~3 mm'den yalnız 2 mm büyük), Ø6 için kalem, Ø8 için kalın marker. "
                "Sık sık jakla dene: gövde sürtünerek geçmeli, boşluk kalmamalı (somun sıkınca jak "
                "dönmez). <b>Havalandırma delikleri (Ø5) istisna:</b> orada sıkı geçme aranmaz, delik "
                "açık olsun yeter — LED ise sıkı geçmeli, yoksa öne düşer."),
    # B55i: Ø12 (F0 sigorta yuvasi) kutudaki EN BUYUK delikti ve rehberde hic yontem
    # yoktu. B58e: F0 kutu icine alininca en buyuk yuvarlak delik Ø8 — satir artik
    # "en dar et" uyarisi; zincir delme yalniz ileride Ø8'den buyuk delik gerekirse.
    ("En büyük delik (Ø{buyuk_cap:.0f}) — en dar et",
     "Paneldeki en büyük yuvarlak delik Ø{buyuk_cap:.0f}: {cubuk_g:.0f} mm çubukta her yanda "
     "<b>{buyuk_et:.1f} mm</b> et kalır — en kolay çatlayan yer. Büyütmeyi kalın markera sarılı zımparayla "
     "yap, sık sık jakla dene, altına fire çubuk koy. İleride kalem/marker büyütmesinin yetmediği daha "
     "büyük bir delik gerekirse: çemberi çiz, <b>çember ÜSTÜNE</b> havyayla 8–10 küçük delik aç, göbeği "
     "bıçakla it, eğeyle çizgiye getir."),
    ("Oval yuva (14 × 9)", "Merkezden ±2.5 mm'de iki Ø9 daire çiz (merkezler 5 mm aralıklı), ikisini de "
                           "havya + büyütme ile aç, arasını maket bıçağıyla düz kes, köşeleri yuvarla. "
                           "USB-C / Type-C fişin metal gövdesi 8.5 × 2.6, plastik kılıfı ~12 × 6.5: 14 × 9 "
                           "rahat geçirir."),
    # B55g: bu satir "3. katindaki Ø6" diyordu — B55e cebi Ø6.5 / 2.-3. kat yapmisti,
    # metin eski dunyada kalmisti (kutu.py'deki delik tablosunun ikizi). Artik SOMUN_CEP'ten.
    ("M3 delikleri (Ø{m3_cap:.1f})", "Havya ucuyla tek geçiş yeter; cıvata sürtünerek geçmeli. Ayak ve kapak "
                            "bloğunun {cep_katlari}. katındaki Ø{cep_cap:.1f} somun cebi: havya + büyütme, "
                            "somunu deneyerek. <b>Cebin hemen altındaki kat</b> da Ø{m3_cap:.1f} delinir (vidanın "
                            "ucu dayanmasın); daha alttaki katlar delinmez."),
    # B55m: 6.1 delikli plakete Ø3.2 deldiriyor ama rehber bastan sona AHSAP.
    # FR4 cam elyaf: havya ISE YARAMAZ (cam 830 °C'de erir, havya 350; recine
    # karbonlasir ve KARBON ILETKENDIR — kacak yolu bozulur).
    ("Delikli plaket (FR4) — Ø{m3_cap:.1f}",
     "⚠ <b>Havya KULLANMA:</b> cam elyaf erimez, reçine karbonlaşır ve karbon iletkendir. "
     "Kartın köşesindeki 2×2 boş bölgede zaten Ø1 delikler var; <b>ortadaki deliği büyüt</b>: "
     "3 mm matkap ucunu <b>penseyle tutup elle çevir</b> (1.6 mm FR4'te ~30 s) ya da yuvarlak "
     "iğne eğeyle aç. Kartı masaya yatır, altına fire tahta koy, bastırma — plaket çatlar. "
     "<b>Toz cam elyafıdır:</b> ıslak bezle sil, üfleme. Kart A lehimli: delik bölgesinde iz ya "
     "da parça olmadığını önce gözle doğrula (yerleşim planı o 2×2'yi boş bıraktı)."),
    ("İç kat (5.1)", "Dış kattaki delik kılavuz olur: havya ucunu ondan geçirip iç çubuğu del, sonra büyüt. "
                     "Oval yuvaların arkasında iç çubuk kısa, delme yok."),
    ("Kontrol", "Parça düz zeminde: çatlak var mı (ışığa tut)? Jak somunu düz oturuyor mu? Çatlak varsa "
                "japonla doldur, kurumadan bastır; büyükse parçayı yeniden kes (fire var)."),
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
    ("s0.005", "Şönt değerini gir (5 mΩ takılı)", "Bir kez. 15 mΩ'a geçince s0.015 + Z."),
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
    ("Gerilim, {yuksek}", "HV (SARI) + COM (siyah)",
     "Menzil: <code>y</code>. <b>Tek el kuralı.</b> USB'yi PC'ye TAKMA — WiFi paneli kullan "
     "(COM = kart GND = USB toprağı). Ölçülen devre toprağa bağlıysa (şebekeli kaynak, "
     "PC'li devre) HV'yi KULLANMA: bu kart yüzen (pil / DC-DC) devreler için.",
     "18.8 mV adım"),
    ("Akım, ≤ {akim} sürekli", "YÜK 1 – YÜK 2",
     "Akım <b>eksi hattan</b> ölçülür: kaynağın + ucu yükün + ucuna <b>doğrudan</b> gider, kutuya "
     "girmez. Eksi hattı kes: yükün eksisi <b>YÜK 1</b>, kaynağın eksisi "
     "<b>YÜK 2</b>. Aynı anda gerilim için yalnız <b>V jakını</b> devrenin artısına bağla; "
     "<b>COM'a krokodil TAKMA</b> — COM zaten YÜK 2'dir. COM'u devrenin eksisine (YÜK 1 "
     "tarafı) takarsan şönt baypas olur: okuma düşer, ince kablo ısınır. Sınır 5 mΩ şöntün "
     "<b>ısınması</b> (Ø1.6 mm manganin, üretici 10 A; sürekli {akim}) ve şöntü tutan <b>XP128 klemensi "
     "(10 A)</b>: kısa süreli de olsa 10 A'i GEÇME. mA "
     "hassasiyeti gerekirse 15 mΩ (R044) tak, <code>s0.015</code> + <code>Z</code>: {akim_15m} "
     "sürekli, adım {adim_15m_uA} mA.", "{adim_uA} mA adım"),
    ("Güç ve enerji (W, Wh)", "V + COM ve YÜK birlikte",
     "Gerilim ve akım aynı anda bağlıysa kart gücü kendi hesaplar; reaktif yükte de doğru.",
     "işaretli, gerçek güç"),
    ("Osiloskop, {skop}", "SKOP (kırmızı) + COM",
     "Dalga şeklini görmek için. Zaman tabanı 100 µs – 500 ms/bölme. Asimetrik menzil: "
     "eksi tarafı daha geniş.", "83 kSa/s'e kadar"),
    ("Güç — kutunun kendi pili", "PİL AÇ (tek anahtar)",
     "Kutu yalnız kendi pilinden çalışır (B58: dış besleme yok). İki 18650 paralel: süre ≈ {pil_suresi}. "
     "USB'siz kullanımda kutu tamamen yüzer: HV ölçümü için en güvenli hal. <b>Şarj:</b> PİL KAPALI, "
     "ŞARJ yuvasına tek Type-C — iki hücre birlikte dolar (≈ {sarj_suresi}). Şarj ederken ölçüm yapma: "
     "şarj kablosu COM'u şarj cihazının toprağına bağlar. <b>USB'yi PC'ye takarken PİL AÇIK olsun</b>: "
     "yükü pil taşır; kapalıyken ölçüm tarafı da PC'den beslenmeye çalışır (~0.35 A).", "2 × 18650 paralel"),
    ("Pil kapasitesi (mAh)", "PİL 1 – PİL 2 + yük direnci + V jakı",
     "<b>Zorunlu:</b> V jakı → pil + (COM zaten pil −, ayrıca tel takma). Pil + → yük "
     "direnci → <b>PİL 1</b>; pil − → <b>PİL 2</b>. Pilin + ucu hiçbir PİL jakına <b>doğrudan</b> "
     "takılmaz: iki tel çıkar, biri dirence, biri V'ye. <b>YÜK boş kalsın.</b> Pil ≤ 31 V ise "
     "<code>n</code>, üstü <code>y</code>. Direnç seçimi: akım = pil V ÷ R, sınır "
     "{pil_akim} A — 3.7 V 18650 için 3.3 Ω 11 W (1.1 A, dirençte 4 W). "
     "<code>P&lt;kesme&gt;</code>, <code>p1</code>. <b>⚠ Kutupları KARIŞTIRMA:</b> ters bağlarsan akım Q1'in "
     "gövde diyodundan akar ve kart bunu <b>KESEMEZ</b> (MOSFET kapalıyken bile; 3.3 Ω ile ~1.1 A sürekli). "
     "Kart 'ters bağlı / baypas' hatası verirse testi başlatmaz ama akım durmaz — <b>kabloyu hemen çıkar</b>.", "≤ 38 V pil"),
    # B55k: sarj sirasinda isil durum. Kutu kapali ve 18650'nin SARJ tavani 45 °C.
    # Isil model 4-5 tahmin sabitine dayandigi icin SAYI IDDIA EDILMIYOR — kural +
    # tezgahta OLCUM. Baskin belirsizlik ESP32'nin gucu (0.4-1.9 W arasi tahminler).
    # B58f: bos pilde MT1 paketi cokertip cirpiniyor, ESP32 acilmiyor (zararsiz: DW01A keser).
    ("Kutu açılmıyorsa", "PİL anahtarı",
     "PİL açınca kutu açılmıyorsa (ESP32 hiç açılmıyor ya da bir an yanıp sönüyor, GÜÇ lambası yanmıyor): "
     "pil azalmış — PİL'i kapat, pili <b>doldur</b> (ŞARJ, PİL kapalı), sonra yeniden aç. Açılışta kart "
     "136 µF'sini doldururken paketten kısa bir süre 2–3.5 A çekiliyor; boşalmış pil bunu taşıyamaz. "
     "Dolu pilde de oluyorsa 10.5'teki yordam (3 × 1 Ω seri direnç).",
     "dolu pilde açılır"),
    ("Şarj (ısıl kural)", "Kapak kapalı, PİL KAPALI",
     "18650'nin <b>şarj tavanı {sarj_tavani}</b> (deşarjda {desarj_tavani}). Kutu kapalı ve havalandırmanın ısıl "
     "katkısı %1 mertebesinde, yani içeride ne ısınırsa hücreye biner. İki kural: "
     "<b>(1) şarj ederken ölçüm yapma</b> — kart ve ESP32 kapalıyken kutuya giren güç yarıya "
     "iniyor; <b>(2) şarj modülünün kendisi ısınır</b> (TP4056 1 A'de ~1–2 W, arka duvarın dibinde). "
     "Sıcak bir odada (>30 °C) kapağı açık şarj et. "
     # B55n: eskiden "sayiyi bana soyle" diyordu; artik karar esigi burada.
     "⚠ Bu bir HESAP değil kural: kutu içi sıcaklık artışı ölçülmedi. İlk şarjda içeriye bir "
     "termometre koy, 2 saat sonra hücre gövdesine el sür. <b>Karar eşiği:</b> hücre gövdesi "
     "elinde <b>ılıktan sıcağa</b> geçiyorsa (yaklaşık 40 °C üstü, {sarj_tavani} tavanına yakın) "
     "kapağı açık şarj etmeye geç (ya da şarj akımını yarıya indir: Rprog 1.2 kΩ → 2.4 kΩ, 0.5 A); "
     "el sıcaklığında kalıyorsa "
     "kapalı şarj güvenli, bir daha ölçmeye gerek yok.",
     "tavan {sarj_tavani}"),
]

# ── malzeme: stoktan cikacaklar / alinacaklar ──────────────────────────
# stok: envanter sorgusu (ad, kategori) — uretec kaydi bulursa "stoktan",
# bulamazsa "alinacak" tablosuna koyar; elle "al" yazilmaz (B50h: TO-220
# izolatoru ve 50 mA sigorta zaten stoktaydi, liste "al" diyordu).
MALZEME = [
    {"ad": "Dil basacağı çubuk", "stok": None,
     "not": "Gereken {cubuk}, elde ~{elde}; en az {eksik} al, fire payıyla {eksik_pay}"},
    {"ad": "Yük yolu için kalın kablo (≥1.5 mm²)", "stok": None,
     "not": "KBL003 karışık montaj kablosunda kalın damar varsa oradan (soyup ölç: çıplak iletken tek damarda ≥ 1.4 mm, çok damarlı demette ~1.6 mm). Halka pabuç stokta YOK ve plan onu ŞART KOŞMUYOR: jakta lehim kulağı ya da iki somun arasında kalaysız halka, bariyerde kalaysız burulmuş uç (5.2). Pabuç almak isteğe bağlı: yalıtımsız pabucun borusu sıkılıp lehimlenir."},
    # B55m: 12.x kalibrasyon adimlari olcum kablosu istiyordu ama malzemede yoktu.
    {"ad": "Ölçüm kabloları (banana + krokodil)", "stok": ("Krokodil Kıskaç Büyük Boy", "Konnektör"),
     "not": "Kalibrasyon adımları (12.2–12.7) panel jaklarına kablo istiyor: bir ucu 4 mm banana "
            "erkek (CON005/CON006, 4 adet), öbür ucu krokodil (CON065/066, 10 adet) — ikisi de stokta. CAL → SKOP için kısa bir banana–banana da aynı parçalardan yapılır."},
    {"ad": "50 mA 5×20 cam sigorta (hızlı, F — stoktaki)", "stok": ("50mA 5x20mm Cam Sigorta", "Sigorta"),
     "not": "Bir tanesini ölç: gerçek 50 mA telin soğuk direnci 15–21 Ω (Littelfuse 217/218); yuvadaki "
            "0.4 Ω = 400 mA (FUS001). F 50 mA anahtar darbesinde atar → aşağıdaki T tipi gelene kadar "
            "yuvadaki 400 mA kalsın (stoktaki F'lerin hiçbiri darbeye ≥3× pay vermiyor)."},
    # B55n: kullanici 2026-09-24'te "takili olan hic atmadi, T'yi sonraki plana
    # alalim" dedi. Kalem listede KALIYOR ama ISTEGE BAGLI — kutu kurulumu bunu
    # beklemiyor, bugunku sigorta kisa devre korumasini veriyor.
    {"ad": "50 mA T (gecikmeli) 5×20 cam sigorta, markalı — İSTEĞE BAĞLI, sonraki plan", "stok": None,
     "not": "Littelfuse 218.050 / ESKA 522.5xx / Schurter; cam gövde (seramik 50 mA çok dirençli). "
            "Anahtar açılış darbesine (136 µF) ≥ 10× pay; T 63 mA da olur (daha bol pay). "
            "Kullanıcı kararı 2026-09-24: yuvadaki sigorta hiç atmadı, kurulum bunu beklemiyor."},
    {"ad": "Soğutucu boşaltma direnci: {sogutucu_r}", "stok": ("1M", "Direnç"),
     "not": "Q1'in soğutucusu mikayla yalıtık, yani kutuda yüzen bir metal plaka. {sogutucu_r} ile kart "
            "GND'ye bağlanıyor: statik akıyor ama mika delinirse PİL 1'i GND'ye kısa etmiyor "
            "({sogutucu_akim:.0f} µA). Düz tel BAĞLAMA."},
    # B55g: hucre 2 kolunun sigortasi — ikisi de stokta, alim yok.
    {"ad": "Hücre sigortası ×2 (F1P, F2): {pil_sigorta} 5×20 cam", "stok": ("2A 5x20mm Cam Sigorta", "Sigorta"),
     "not": "Her iki hücrenin ARTI ucuna birer tane. TP4056'nın koruma FET'i (FS8205) B−/OUT− arasında "
            "olduğu için hücre ucu ve H+/H− kablosundaki kısa devreyi DW01A kesemez; o kolu yalnız bu "
            "sigorta korur (kısa devre 42 A). ⚠ Anma neden yüksek: sigorta TP4056'nın BAT ucunda, yani "
            "ŞARJ akımının tamamı ({sarj_akimi}, Rprog fabrika ayarı) buradan geçiyor — daha küçüğü ilk "
            "şarjda atar. Sürekli deşarj {pil_kol_ma} mA; belirleyici olan şarj."},
    {"ad": "Sigorta yuvası ×3: 5×20 PCB klipsli (F1P, F2, F0)", "stok": ("5x20mm PCB Klipsli Sigorta Yuvası", "Sigorta"),
     "not": "Arka duvara, çubuk parçasına kablo bağıyla (F1P TP4056 rafının sağında, F2 sağ alt köşede, "
            "F0 sol uçta MT1'in yanında). Panel deliği YOK — kutu içi, "
            "servis için kapak açılır (hücre değişimi zaten kapak açtırıyor)."},
    # B55m: sogutucu malzeme listesinde HIC YOKTU; olculeri de kayitta yok.
    {"ad": "Q1 soğutucusu (plan 15 × 40 × 42 mm VARSAYIYOR)", "stok": ("Soğutucu Blok", "Mekanik"),
     "not": "Kayıtta ölçü yok (MEK002 'muhtelif boyutlarda'). Plan 15 × 40 × 42 mm varsayıyor ve "
            "Q1 için bu ölçüyle yer ayırdı. Elindeki blok daha büyükse kutuya girer ama "
            "kart B'ye olan açıklığı daralır — o zaman bloğu küçült ya da Q1'i 2–3 mm sağa kaydır. "
            "Daha küçükse sorun yok: Q1 pil testinde 1.4 W harcıyor, bu blok fazlasıyla yeter "
            "(soğutucusuz bile Tj 121 °C, sınır 175)."},
    {"ad": "TO-220 yalıtım (mika/plastik izolatör + burç)", "stok": ("TO-220 Mika İzolatör", "Mekanik"),
     "not": "Q1'i soğutucudan yalıtmak için; plastik delikli/deliksiz izolatörler de var (MEK037–040)"},
    {"ad": "M3×10 / M3×12 vida, somun, pul", "stok": ("M3 Somun", "Mekanik"),
     "not": "Kart ayakları ×6, kapak ×4, Q1 köşebent ×1; gömme somun ×10 (6 ayak + 4 kapak rayı bloğu). "
            "18650 yuvaları artık yapıştırılıyor (B57b), onlara cıvata yok"},
    {"ad": "2'li vidalı klemens 5 mm (24 V iç bağlantı)", "stok": ("2 Pin Klemens 5.00mm", "Konnektör"),
     "not": "Kartın 24 V telleri buraya; kart lehim sökmeden çıkar"},
    {"ad": "Dişi header (3'lü + 1'li konnektör uçları)", "stok": ("1x40 Dişi Header 180°", "Konnektör"),
     "not": "Şönt demeti ve Q1 kapı teli için kesilir"},
    {"ad": "XP128 10 mm klemens (şönt bacakları + yük kabloları)", "stok": ("XP128 2 Pin Terminal Klemens 10mm", "Konnektör"),
     "not": "Şönt bacakları (10–11 mm) kutuplara; altlık çubuğuna yapıştırılır, şönt vidayla değişir"},
    {"ad": "5 mΩ Ø1.6 şönt (takılı) + 15 mΩ Ø1 (yedek, mA işleri)", "stok": ("5mR Type-C Şönt Direnç 9.5A", "Direnç"),
     "not": "5 mΩ: 9.5 A sürekli, 1.56 mA adım. 15 mΩ (R044): 3.4 A, 0.52 mA adım; kalibrasyon 12.2'de ikisi de kullanılır"},
    {"ad": "18650 hücre ×2 (pil paketi, paralel)", "stok": ("18650 Li-ion Şarjlı Pil 3.7V 1500mAh", "Güç Kaynağı/Pil"),
     "not": "Başlı hücre: yaylı yuvada başlık temas eder; MEK025 yalıtım contası tak. PARALEL bağlanır: ilk "
            "takışta iki hücrenin gerilimi ±0.1 V içinde olmalı (10.3)"},
    {"ad": "18650 tekli yuva ×2", "stok": ("18650 Tekli Pil Yuvası", "Güç Kaynağı/Pil"),
     "not": "PWR004 (motorobit) ya da PWR007 (direnc.net); 80×21×21 ÖLÇÜLDÜ (B52d) — PWR009 PCB tipi, duvara cıvatalanmaz"},
    {"ad": "TP4056 korumalı Type-C ×1 (tek şarj girişi)", "stok": ("TP4056 Li-ion Şarj Devresi", "Modül"),
     "not": "İki paralel hücreyi birlikte doldurur. Rprog 1.2 kΩ fabrika (1 A, hücre başına ~0.5 A) → "
            "2.4 kΩ ile 0.5 A, kutu daha az ısınır (isteğe bağlı)"},
    {"ad": "MT3608 yükseltici ×2", "stok": ("MT3608 DC-DC Yükseltici", "Modül"),
     "not": "Biri 5.0 V (5 V barası: ESP32 + analog girişi), biri 24.0 V (analog, girişi B0505S); 10.1'de "
            "yüksüz ayarlanır"},
    {"ad": "5 mm yeşil LED + 10 kΩ direnç (GÜÇ lambası)", "stok": ("5mm LED Yeşil (şeffaf)", "LED"),
     "not": "LED003 ×20, direnç R060 (10K) ×50 — ikisi de stokta. Daha parlak istersen 4.7K (R015): 2.1 mA"},
    {"ad": "KTS102 toggle ×1 (PİL, kutunun tek anahtarı)", "stok": ("KTS102 On/Off 3 Ayak Toggle Anahtar", "Anahtar/Buton"),
     "not": "3 ayak: orta + bir uç kullanılır (ON-OFF). Stokta 2, biri yedek. Ortak (orta) ayağı ohmmetreyle "
            "doğrula, lehimde ayağı uzun ısıtma. B58'den beri KTS202 gerekmiyor"},
    {"ad": "F0 sigortası: 1 A 5×20 cam (hızlı)", "stok": ("1A 5x20mm Cam Sigorta", "Sigorta"),
     "not": "Ölçüm tarafının 5 V girişinde, kutu içinde (B58e). Yalnız iç arızada atar; atarsa kapağı aç, "
            "önce arızayı bul (B0505S, MT2, kart), sonra değiştir"},
    # B58 (kullanici karari 2026-09-25): tek sarj girisi icin YALITIMLI DC-DC.
    {"ad": "B0505S-2WR3 (2 W) yalıtılmış DC-DC, 5 V → 5 V (Hi-Link, motorobit) — 1 W DEĞİL",
     "stok": ("B0505S-2WR3", "Modül"),
     "not": "Kutunun iki toprağını ayıran tek parça (B58): analog 24 V bu modülün yalıtılmış çıkışından. "
            "Sürekli yük {iz_yuk_w:.2f} W = %{iz_yuk:.0f}; üreticinin en az %10 yük şartı en düşük yükte "
            "%{iz_yuk_asgari:.0f}. 1 W sürümünü (B0505S-1WR3) ALMA: sürekli yüke yeter (%73) ama açılışta "
            "yetmez — akım sınırında MT2'nin girişini ~2 V'a çeker, kart 24 V'a çıkamaz (B58f benzetimi, "
            "sim3_kutu_besleme.py). 1500 VDC yalıtımlı, kısa devre korumalı; gövde 19.5 × 7 × 10, duvarda "
            "yeri ayrılı. Bacak sırası ada göre (10.1). 2026-09-28'de geldi (MOD013)"},
    # B58f: MT2 girisine toplu kondansator (benzetim: yoksa kart 24 V'ta takilabilir)
    {"ad": "680 µF 16 V elektrolitik ×1 (MT2 girişi, CB)", "stok": ('680µF 16V', "Kondansatör"),
     "not": "B58f benzetimi: 470 µF her modelde yetiyor, 220 yetmiyor. Stokta 2; 470 µF 10 V (C040) da olur"},
    {"ad": "1 Ω 1 W direnç ×3 — YALNIZ 10.5'teki belirtide (yedek yol)", "stok": ('1R 1W', "Direnç"),
     "not": "B0505S +Vo ile MT2 IN+ arasına seri 3 Ω. Varsayılan olarak TAKILMAZ: kutu dolu pilde açılmıyorsa "
            "takılır (10.5). Stokta 50"},
    # B55n: sont kutbuna UC iletken biniyordu (sont bacagi + iki kalin kablo).
    # XP128'in kafesine Ø2 manganin cubuk + iki damarli kablo birlikte girmez:
    # cubuk basinci alir, damarlar gevser. Guc dugumu bariyere tasindi.
    {"ad": "HB950 2 pin bariyer klemens ×1 (güç düğümü)", "stok": ("HB950 2 Pin Bariyer Klemens", "Konnektör"),
     "not": "YÜK/PİL kalın kabloları burada birleşir, XP128'e tek köprü gider. Bariyerin vidası altına "
            "iki-üç kalaysız burulmuş uç sığar; şönt değiştirirken yalnız XP128'in iki vidası gevşer"},
]
