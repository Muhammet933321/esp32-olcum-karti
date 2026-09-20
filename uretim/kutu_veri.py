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

Eksenler (mm):
  x = sagA, y = derinlik (on duvardan arkaya), z = yukari (tabandan).
  Taban ic kosesi (0, 0, 0). Panel ogelerinde x ve z kullanilir.
"""
from __future__ import annotations

# ── malzeme: dil basacagi ──────────────────────────────────────────────
# Kullanici olctu (2026-09-20): 150 x 18 x 2 mm. Butun kesim listesi,
# duvar sira sayisi ve cizimler bu uc sayidan turuyor.
# uc_egim: dil basacaginin iki ucundaki YUVARLAK bolum. Duz (dikdortgen)
# bolum = uzunluk - 2 * uc_egim. Duz birlesme isteyen her parca bu duz
# bolumden kesilir; taban/kapak cubuklari kesilmeden kullanilir (yuvarlak
# uclari duvarlarin altinda kalir). Kullanici olcup dogrulayacak (1.1).
CUBUK = {"uzunluk": 150.0, "genislik": 18.0, "kalinlik": 2.0, "uc_egim": 10.0,
         "ad": "dil basacağı (tahta çubuk)"}

# ── kutu ───────────────────────────────────────────────────────────────
# Ic en: kart A (114.3) + sag kolon (kart B / ESP32 / sont) + paylar.
# Ic boy: kart A + on serit (Q1 ve kablo).  Duvar yuksekligi cubuk
# genisliginin katidir — her sira bir cubuk.
KUTU = {
    "ic_en": 190.0,
    "ic_boy": 146.0,
    "duvar_sira": 4,            # 4 x 18 = 72 mm ic yukseklik
    "kenar_payi": 10.0,         # panel deligi ile kose arasi en az
    "parca_payi": 6.0,          # ic parcalar arasi en az bosluk
    "yapistirici": "sıcak silikon (tabanca) — tahtada hızlı tutar; "
                   "istersen ahşap tutkalı daha sağlam ama beklemek gerekir",
}

# ── kutunun icindeki parcalar (taban yerlesimi) ────────────────────────
# x, y: sol-arka kosesi.  en/boy: taban izi.  yuk: en yuksek noktasi.
IC_PARCA = [
    {"ref": "A", "ad": "Ana kart (45×45 delikli plaket)", "x": 8.0, "y": 8.0,
     "en": 114.3, "boy": 114.3, "yuk": 24.0,
     "nasil": "Dört köşeye ahşap ayak bloğu; plaket ayakların üstüne M3 vidayla "
              "tutturulur. YAPIŞTIRILMAZ — vidayı sök, kart çıkar."},
    {"ref": "B", "ad": "HV zinciri kartı (5×5 cm)", "x": 132.0, "y": 8.0,
     "en": 45.7, "boy": 45.7, "yuk": 16.0,
     "nasil": "İki ahşap ayak + M3 vida; HV jakının olduğu tarafa, ana karttan "
              "ayrı dursun. Sökülebilir."},
    {"ref": "ESP32", "ad": "ESP32-S3 devkit", "x": 132.0, "y": 62.0,
     "en": 26.0, "boy": 63.0, "yuk": 14.0,
     "nasil": "İki kablo bağıyla ahşap altlığa bağlanır (altlıkta iki delik). "
              "USB soketi arka duvardaki deliğe baksın. Kablo bağını kes, çıkar."},
    {"ref": "RS", "ad": "15 mΩ şönt (R044)", "x": 164.0, "y": 62.0,
     "en": 12.0, "boy": 30.0, "yuk": 10.0,
     "stok": ("15mR Type-C Şönt Direnç", "Direnç"),
     "nasil": "Ahşap altlığa kablo bağıyla; bacakları serbest kalsın, Kelvin "
              "telleri oraya lehimlenecek. Sökülebilir."},
    {"ref": "Q1", "ad": "IRFZ44N + soğutucu", "x": 8.0, "y": 126.0,
     "en": 40.0, "boy": 15.0, "yuk": 42.0,
     "stok": ("IRFZ44N", "Transistör"),
     "nasil": "Soğutucu DİK duracak (kanatlar yukarı), ahşap bir köşebende M3 "
              "vidayla. MOSFET'in tabı soğutucudan yalıtılmış olmalı. Sökülebilir."},
]

# ── panel ogeleri ──────────────────────────────────────────────────────
# x: sol kenardan, z: tabandan yukari.  Delik bir cubuk sirasinin
# ICINDE kalmali (denetim bunu olcuyor).
PANEL_ON = [
    {"ref": "J3", "ad": "YÜK (akım yolu)", "tip": "klemens", "x": 34.0, "z": 9.0,
     "delik_mm": 3.2, "metal_mm": 26.0, "renk": "gri",
     "parca": ("2 Pin Bariyer Klemens", "Konnektör"),
     "etiket": "YÜK", "alt_etiket": "1: devre −   2: kaynak −",
     "not": "Akım buradan geçer. İki M3 vidayla duvara; vida delikleri Ø3.2."},
    {"ref": "J7", "ad": "PİL (kapasite testi)", "tip": "klemens", "x": 70.0, "z": 9.0,
     "delik_mm": 3.2, "metal_mm": 26.0, "renk": "gri",
     "parca": ("2 Pin Bariyer Klemens", "Konnektör"),
     "etiket": "PİL", "alt_etiket": "1: yük   2: pil −",
     "not": "J3'ten AYRI. Karıştırılırsa kesme çalışmaz."},
    {"ref": "J1.1", "ad": "V girişi", "tip": "jak", "x": 90.0, "z": 45.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (kırmızı)", "Konnektör"),
     "etiket": "V", "alt_etiket": "±32 V", "not": "NORMAL gerilim kanalı."},
    {"ref": "J1.2", "ad": "COM (ortak)", "tip": "jak", "x": 114.0, "z": 45.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "renk": "siyah",
     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (siyah)", "Konnektör"),
     "etiket": "COM", "alt_etiket": "ortak uç",
     "not": "TEK COM: V, HV ve SKOP'un ortak ucu."},
    {"ref": "J4.1", "ad": "Osiloskop girişi", "tip": "jak", "x": 138.0, "z": 45.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (kırmızı)", "Konnektör"),
     "etiket": "SKOP", "alt_etiket": "±63 V", "not": "Dalga şekli kanalı."},
    {"ref": "J2.1", "ad": "YÜKSEK gerilim girişi", "tip": "jak", "x": 166.0, "z": 63.0,
     "delik_mm": 6.5, "metal_mm": 12.0, "renk": "kirmizi",
     "parca": ("4mm Born Jak Şeffaf Kırmızı (Büyük Boy)", "Konnektör"),
     "etiket": "HV ⚡", "alt_etiket": "±614 V",
     "not": "AYRI sırada ve işaretli. Kaçak yolu için diğerlerinden uzak; "
            "yerini değiştirme."},
]

PANEL_ARKA = [
    {"ref": "J6", "ad": "24 V girişi (XT30)", "tip": "konnektor", "x": 40.0, "z": 45.0,
     "delik_mm": 12.0, "metal_mm": 16.0, "renk": "sari",
     "parca": ("XT30 Lipo Pil Konnektör Takımı", "Konnektör"),
     "etiket": "24 V", "alt_etiket": "giriş",
     "not": "Dişi uç dışarıda; kablo içeriden anahtara gider."},
    {"ref": "SW", "ad": "Güç anahtarı", "tip": "anahtar", "x": 95.0, "z": 45.0,
     "delik_mm": 12.0, "metal_mm": 16.0, "renk": "gri",
     "parca": ("12mm Kilit Anahtarı 2 Konum ON-OFF", "Anahtar/Buton"),
     "etiket": "AÇ/KAPA", "alt_etiket": "24 V + hattı",
     "not": "24 V'un ARTI koluna seri. Somunlu, 12 mm delik."},
    {"ref": "USB", "ad": "ESP32 USB deliği", "tip": "delik", "x": 150.0, "z": 45.0,
     "delik_mm": 12.0, "metal_mm": 0.0, "renk": "gri",
     "parca": None, "etiket": "USB", "alt_etiket": "kablo geçişi",
     "not": "Devkit'in COM yazan Type-C soketi buraya baksın."},
]

# ── adimlar ve alt adimlar ─────────────────────────────────────────────
# tur: cizimi secer — kesim · taban · duvar · delik · montaj · kablo ·
#      kontrol · kapi · hazirlik
# kablo: yerlesim3_veri.KABLOLAR indeksleri (tek kaynak orada)
# monte: bu alt adimda kutuya giren kart disi parca
# vurgu: cizimde parlayacak ic parca ya da panel ogesi
ADIMLAR = [
    {"no": 1, "baslik": "Çubuk kutu — ölçü ve kesim", "alt": [
        {"no": "1.1", "baslik": "Çubuğunu doğrula", "tur": "kesim",
         "yap": ["Bir çubuğu cetvelle ölç: <b>{u:.0f} × {g:.0f} × {k:.0f} mm</b> bekliyoruz.",
                 "Uçlardaki <b>yuvarlak bölüm {ue:.0f} mm</b> kabul edildi (2026-09-20'de "
                 "doğrulandı); ortada <b>{duz:.0f} mm düz</b> bölüm kalıyor.",
                 "Tutmuyorsa bana söyle — bütün kesim listesi ve çizimler bu dört "
                 "sayıdan üretiliyor, yeniden üretirim."],
         "kontrol": ["Çubuklar düz mü, çatlak olan var mı? Eğri olanları kapak "
                     "için ayır."]},
        {"no": "1.2", "baslik": "Kesim listesi — hepsini önce kes", "tur": "kesim",
         "yap": ["Çubuğun <b>iki ucu yuvarlak</b>. Düz birleşme isteyen her parça "
                 "ortadaki <b>düz bölümden</b> kesilir: uçlardan {ue:.0f}'ar mm at, "
                 "geriye {duz:.0f} mm düz bölüm kalır.",
                 "<b>Tek istisna taban ve kapak çubukları:</b> onlar kesilmeden, tam "
                 "{u:.0f} mm kullanılıyor — yuvarlak uçları duvarların altında kalıyor.",
                 "Aşağıdaki listeye göre kes. Maket bıçağı ya da ince testere; "
                 "kesmeden önce kurşun kalemle işaretle.",
                 "Kesilen parçaları gruplara ayır (taban / duvar / kapak / ayak). "
                 "Karışırsa sıra bozulur."],
         "kontrol": ["Her gruptaki parça sayısı listedekiyle aynı mı?",
                     "Aynı gruptaki parçaların boyu birbirine eşit mi (üst üste koy, "
                     "uçları hizalı mı)?"]},
    ]},
    {"no": 2, "baslik": "Taban", "alt": [
        {"no": "2.1", "baslik": "Taban çubuklarını diz", "tur": "taban",
         "yap": ["Taban çubuklarını düz bir zemine <b>yan yana</b>, uçları hizalı diz. "
                 "Aralarında boşluk kalmasın.",
                 "Henüz yapıştırma yok — önce dizilişi gör."],
         "kontrol": ["Dizilen tabanın eni ve boyu ölçüyle uyuyor mu?"]},
        {"no": "2.2", "baslik": "Alttan iki rayla bağla", "tur": "taban",
         "yap": ["İki rayı tabanın <b>altına</b>, uçlardan 20 mm içeriden enine yapıştır. "
                 "Ray bütün çubukları birbirine bağlar.",
                 "Silikonu ray boyunca sürekli çek, nokta nokta değil."],
         "kontrol": ["Taban tek parça gibi kalkıyor mu? Ortadan tutup kaldır, çubuklar "
                     "ayrılmamalı.",
                     "Taban düz mü, beşik gibi kamburlaşmamış mı?"]},
    ]},
    {"no": 3, "baslik": "Duvarlar", "alt": [
        {"no": "3.1", "baslik": "1. sıra — ön ve arka", "tur": "duvar", "sira": 1,
         "yap": ["Ön ve arka duvarın ilk sırasını tabanın kenarına, <b>dik</b> olarak "
                 "yapıştır. Çubuğun geniş yüzü dışa baksın.",
                 "Uzun duvar tek çubuktan uzun: bir tam çubuk + kalan parça. Ek yerini "
                 "ortaya değil, <b>bir yana kaydır</b>."],
         "kontrol": ["Gönye ya da kitap kenarıyla bak: duvar tabana dik mi?"]},
        {"no": "3.2", "baslik": "1. sıra — yanlar", "tur": "duvar", "sira": 1,
         "yap": ["Yan duvarların ilk sırasını ön ve arka duvarın <b>arasına</b> sıkıştır. "
                 "Köşede çubuk uçları birbirine dayanır.",
                 "Köşeleri içeriden bir damla silikonla güçlendir."],
         "kontrol": ["Dört köşe de kapalı mı, boşluk kaldı mı?"]},
        {"no": "3.3", "baslik": "2., 3. ve 4. sıralar", "tur": "duvar", "sira": 4,
         "yap": ["Üstteki sıraları aynı şekilde ekle. Her sırada <b>ek yerini kaydır</b> "
                 "— ekler üst üste gelirse duvar o çizgiden ayrılır.",
                 "Sıra sayısı {sira}: iç yükseklik {h:.0f} mm oluyor."],
         "kontrol": ["Duvar yüksekliği her köşede aynı mı?",
                     "Kutuyu ters çevir, sallanıyor mu?"]},
    ]},
    {"no": 4, "baslik": "Panel delikleri", "alt": [
        {"no": "4.1", "baslik": "Ön duvarı işaretle", "tur": "delik", "panel": "ön",
         "yap": ["Ön duvarda delik merkezlerini kurşun kalemle işaretle (ölçüler sol "
                 "kenardan ve tabandan).",
                 "Her delik <b>tek bir çubuk sırasının</b> içinde kalıyor; sıra sınırına "
                 "denk getirme, tahta çatlar."],
         "kontrol": ["İşaretler tabloyla aynı mı? Bir kez daha ölç, sonra del."]},
        {"no": "4.2", "baslik": "Ön duvarı del", "tur": "delik", "panel": "ön",
         "yap": ["Önce ince matkapla (2 mm) kılavuz deliği aç, sonra istenen çapa büyüt. "
                 "Tahta böyle çatlamaz.",
                 "Jak delikleri Ø6.5, klemens vida delikleri Ø3.2.",
                 "Delik kenarlarını zımparayla temizle."],
         "kontrol": ["Jakı deliğe sok: somunu rahat sıkılıyor mu?",
                     "Delik çevresinde çatlak var mı?"]},
        {"no": "4.3", "baslik": "Arka duvarı del", "tur": "delik", "panel": "arka",
         "yap": ["Arka duvarda üç delik var: XT30, anahtar ve USB — üçü de Ø12.",
                 "Ø12'yi tek hamlede açma; 2 mm → 6 mm → 12 mm diye büyüt."],
         "kontrol": ["Anahtarın somunu oturuyor mu?",
                     "USB kablosu delikten rahat geçiyor mu?"]},
    ]},
    {"no": 5, "baslik": "Panel parçalarını tak", "alt": [
        {"no": "5.1", "baslik": "Born jakları tak", "tur": "delik", "panel": "ön",
         "monte": ["J1", "J2", "J4"], "vurgu": ["J1.1", "J1.2", "J4.1", "J2.1"],
         "yap": ["Dört jakı deliklere tak, somunları içeriden sık.",
                 "Renklere dikkat: V ve SKOP ve HV <b>kırmızı</b>, COM <b>siyah</b>.",
                 "HV jakını takınca üstüne ⚡ etiketini yapıştır."],
         "kontrol": ["Jakların arka ucu içeride birbirine değmiyor.",
                     "Somunlar sıkı; jak elle döndürülmüyor."]},
        {"no": "5.2", "baslik": "Klemensleri tak", "tur": "delik", "panel": "ön",
         "monte": ["J3", "J7"], "vurgu": ["J3", "J7"],
         "yap": ["J3 (YÜK) ve J7 (PİL) klemenslerini M3 vidayla ön duvara tuttur.",
                 "İkisini <b>etiketle</b>. Karıştırmak pil testinin kesmesini bozar."],
         "kontrol": ["Vidalar tahtayı çatlatmamış.",
                     "Klemens vidaları rahat dönüyor."]},
        {"no": "5.3", "baslik": "XT30 ve anahtarı tak", "tur": "delik", "panel": "arka",
         "monte": ["J6", "SW"], "vurgu": ["J6", "SW"],
         "yap": ["Anahtarı somunuyla arka duvara tak.",
                 "XT30'un dişi ucunu delikten geçir, içeriden <b>kablo bağıyla</b> "
                 "ahşap bir parçaya çek ya da iki küçük çubuk arasına sıkıştır. "
                 "Yapıştırma; kablo bağı kesilince çıkar."],
         "kontrol": ["Anahtar iki konumda da net oturuyor.",
                     "XT30 çekince oynamıyor."]},
    ]},
    {"no": 6, "baslik": "Kartları ve güç parçalarını yerleştir", "alt": [
        {"no": "6.1", "baslik": "Ayakları yapıştır", "tur": "montaj", "vurgu": ["A"],
         "yap": ["Ana kartın dört köşesinin geleceği yere <b>ayak bloklarını</b> yapıştır: "
                 "her köşeye 3–4 parça çubuk üst üste (~8 mm). Bunlar kutunun kendi "
                 "parçası, yapıştırılabilir.",
                 "Her ayağın ortasına <b>2.5 mm delik</b> aç — kart M3 vidayla buraya "
                 "tutturulacak.",
                 "Amaç iki yönlü: plaketin altındaki lehimler tabana değmesin, kart "
                 "istendiğinde vida sökülerek çıksın."],
         "kontrol": ["Dört ayak da aynı yükseklikte mi? Kartı üstüne koy, sallanmamalı."]},
        {"no": "6.2", "baslik": "Ana kartı yerleştir", "tur": "montaj", "vurgu": ["A"],
         "yap": ["Kart A'yı ayakların üstüne oturt. Kartın ön kenarı jaklara bakacak.",
                 "Dört köşesindeki delikten <b>M3 vidayla</b> ayaklara tuttur. "
                 "<b>Yapıştırma.</b> Vidalar söküldüğünde kart tek parça çıkmalı.",
                 "Vidayı fazla sıkma; tahta ezilir, plaket çatlar."],
         "kontrol": ["Kartın altı hiçbir yere değmiyor.",
                     "Kartın telleri jaklara rahat uzanıyor (zorlanmıyor)."]},
        {"no": "6.3", "baslik": "Kart B ve ESP32", "tur": "montaj",
         "vurgu": ["B", "ESP32"],
         "yap": ["Kart B için iki ayak bloğu yapıştır, kartı M3 vidayla tuttur.",
                 "ESP32 için tabana küçük bir ahşap altlık yapıştır, altlığa iki delik aç; "
                 "devkit'i <b>kablo bağıyla</b> altlığa bağla. Type-C soketi arka duvardaki "
                 "deliğe baksın.",
                 "Hiçbirini yapıştırma — ikisi de sökülebilir kalsın."],
         "kontrol": ["İki kart arasındaki kısa tel gergin değil.",
                     "USB kablosu takılıp çıkabiliyor."]},
        {"no": "6.4", "baslik": "Şönt ve Q1", "tur": "montaj", "vurgu": ["RS", "Q1"],
         "monte": ["RS", "Q1"],
         "yap": ["Şönt için tabana küçük bir ahşap altlık yapıştır, iki delik aç ve "
                 "şöntü <b>kablo bağıyla</b> bağla. Bacakları serbest kalsın.",
                 "Q1'in soğutucusunu ahşap bir köşebende <b>M3 vidayla</b> tuttur; "
                 "köşebendi tabana yapıştır. Soğutucu dik, kanatlar yukarı.",
                 "Q1'in tabı (metal sırtı) soğutucudan <b>yalıtılmış</b> olmalı: "
                 "mika/silikon izolatör + burç + termal macun.",
                 "Parçaların hiçbirini doğrudan tabana yapıştırma."],
         "kontrol": ["Q1'in tabı ile soğutucu arası ohmmetrede <b>ötmemeli</b>.",
                     "Şöntün bacakları serbest; lehim yapacak yer var."]},
    ]},
    {"no": 7, "baslik": "Güç yolu — şönt, J3, Kelvin, yıldız GND", "alt": [
        {"no": "7.1", "baslik": "Yük yolunu bağla", "tur": "kablo", "kablo": [2, 3],
         "vurgu": ["RS", "J3"],
         "yap": ["J3'ün 1. vidası → şöntün bir bacağı, şöntün öbür bacağı → J3'ün 2. vidası.",
                 "<b>Kalın kablo (≥1.5 mm²)</b> ve kısa tut. Ölçülen bütün akım bu yoldan geçecek."],
         "kontrol": ["J3'ün iki vidası arası neredeyse kısa devre: 0.0–0.5 Ω "
                     "(şönt 15 mΩ; prob direnci de içinde).",
                     "Kablo uçları vidanın altında sıkı, tek tel dışarı kaçmamış."]},
        {"no": "7.2", "baslik": "Kelvin uçları ve yıldız GND", "tur": "kablo",
         "kablo": [4, 5, 6], "vurgu": ["RS"],
         "yap": ["Karttan gelen <b>S+</b> ve <b>S−</b> tellerini şöntün <b>bacaklarına</b> "
                 "lehimle — klemens vidasına değil.",
                 "Yıldız GND telini şöntün alt bacağına, <b>S− ile tam aynı noktaya</b> bağla.",
                 "S+ ve S− tellerini birbirine bur."],
         "kontrol": ["S+ ↔ J3.1 ve S− ↔ J3.2: bip ötmeli.",
                     "Yıldız teli ↔ kart GND: bip ötmeli.",
                     "Şönt bacağı ↔ kutudaki başka hiçbir şey: ötmemeli."]},
    ]},
    {"no": 8, "baslik": "Pil testi yolu — Q1 ve J7", "alt": [
        {"no": "8.1", "baslik": "Q1'i yük yoluna bağla", "tur": "kablo",
         "kablo": [7, 8, 9], "vurgu": ["Q1", "J7", "RS"],
         "yap": ["Q1'in <b>kaynağı</b> → şöntün üst bacağı.",
                 "J7'nin 1. vidası → Q1'in <b>savağı</b>.",
                 "J7'nin 2. vidası → şöntün alt bacağı.",
                 "Üçü de kalın kablo."],
         "kontrol": ["J7.2 ↔ J3.2: ötmeli (ikisi de şöntün alt bacağı).",
                     "J7.1 ↔ J3.1: <b>ötmemeli</b> — ötüyorsa klemensler karışmış."]},
        {"no": "8.2", "baslik": "Kapı telini bağla", "tur": "kablo", "kablo": [10],
         "vurgu": ["Q1"],
         "yap": ["Karttaki kapı telini (Z36) Q1'in <b>kapısına</b> lehimle. İnce tel yeter.",
                 "Lehimi yaptıktan sonra teli silikonla sabitle."],
         "kontrol": ["Q1'in kapısı ↔ kaynağı: ötmemeli.",
                     "Kapı teli soğutucuya değmiyor."]},
    ]},
    {"no": 9, "baslik": "Ölçüm girişleri", "alt": [
        {"no": "9.1", "baslik": "V ve COM jakları", "tur": "kablo", "kablo": [11, 12],
         "vurgu": ["J1.1", "J1.2"],
         "yap": ["Karttan gelen V girişi telini (C4) <b>V jakına</b>, COM telini (C6) "
                 "<b>COM jakına</b> lehimle.",
                 "Jakın arkasındaki vidalı ucu kullan; lehim yaptıysan ucu izole et."],
         "kontrol": ["V jakı ↔ kart C4: ötmeli. COM jakı ↔ kart C6: ötmeli."]},
        {"no": "9.2", "baslik": "SKOP jakı ve ortak COM", "tur": "kablo",
         "kablo": [17, 14], "vurgu": ["J4.1", "J1.2"],
         "yap": ["Skop telini (B16) <b>SKOP jakına</b> bağla.",
                 "SKOP'un COM ucu ayrı jak istemiyor: <b>COM jakına</b> kısa bir telle bağla."],
         "kontrol": ["SKOP jakı ↔ kart B16: ötmeli."]},
        {"no": "9.3", "baslik": "HV jakı", "tur": "kablo", "kablo": [15, 13],
         "vurgu": ["J2.1", "J1.2", "B"],
         "yap": ["HV jakını kart B'ye <b>600 V silikon prob kablosuyla</b> bağla (KBL004).",
                 "Bu kabloyu diğerlerinden ayrı, kısa yoldan geçir; 24 V hattına ve "
                 "sinyal tellerine paralel uzatma.",
                 "HV'nin COM ucunu da COM jakına bağla."],
         "kontrol": ["HV jakı ↔ kart B D8: ötmeli.",
                     "Üç COM ucu (V, SKOP, HV) birbirine bağlı.",
                     "Aşağıdaki üç direnç ölçümü jaktan karta bütün yolu doğrular."]},
    ]},
    {"no": 10, "baslik": "Besleme", "alt": [
        {"no": "10.1", "baslik": "XT30 → anahtar → kart", "tur": "kablo", "kablo": [0, 1],
         "vurgu": ["J6", "SW"],
         "yap": ["XT30'un kırmızı ucu → <b>anahtarın</b> bir bacağı; anahtarın öbür bacağı "
                 "→ kartın kırmızı teli (C34).",
                 "XT30'un siyah ucu → doğrudan kartın siyah teli (C36).",
                 "Kaynak tarafındaki kabloyu XT30'un erkek ucuna bağla."],
         "kontrol": ["Anahtar KAPALI iken XT30 ile kart arası süreklilik yok; AÇIK iken var.",
                     "Kaynak <b>kapalıyken</b> XT30'u tak, sonra kaynağı aç."]},
        {"no": "10.2", "baslik": "Kutuda ilk enerji", "tur": "kontrol",
         "yap": ["Soketlerdeki entegreleri çıkar, ESP32'yi ayır.",
                 "24 V ver ve kartta +12 V / −12 V'u tekrar ölç (V35 / R33, GND: V36)."],
         "kontrol": ["+12 V: +11.5 … +12.5 V. −12 V: −11 … −13 V.",
                     "Sigorta üzerindeki düşüm, hiçbir şey ısınmıyor."]},
    ]},
    {"no": 11, "baslik": "ESP32 ve ilk iki kapı", "alt": [
        {"no": "11.1", "baslik": "J5 kablosu ve entegreler", "tur": "montaj",
         "vurgu": ["ESP32", "A"],
         "yap": ["Soketlere entegreleri tak: U3, U4 (LM358), U5, U8 (TL072). Çentik yönü.",
                 "ADS modüllerini yuvalarına tak.",
                 "J5 başlığına 10 telli kabloyu tak — eşleme tablosu Yerleşim belgesi "
                 "alt adım 1.12'de. <b>3V3 ile 5V'u karıştırma.</b>",
                 "USB'yi devkit'in COM yazan soketine tak."],
         "kontrol": ["Entegrelerin çentiği doğru yönde.",
                     "10 telin hepsi J5'te ve ESP32'de doğru pinde."]},
        {"no": "11.2", "baslik": "Vref ve I²C kapıları", "tur": "kapi", "kapi": [1, 2],
         "yap": ["WiFi ayarlarını seri konsoldan gir: <code>Ns&lt;web parolası&gt;</code>, "
                 "<code>Na&lt;ssid&gt;</code>, <code>Np&lt;parola&gt;</code>; durum "
                 "<code>N?</code>."]},
    ]},
    {"no": 12, "baslik": "Kalibrasyon ve kalan kapılar", "alt": [
        {"no": "12.1", "baslik": "Kalibrasyon", "tur": "kalibrasyon"},
        {"no": "12.2", "baslik": "Kapı 3–8", "tur": "kapi", "kapi": [3, 4, 5, 6, 7, 8]},
    ]},
    {"no": 13, "baslik": "Kapak ve etiketler", "alt": [
        {"no": "13.1", "baslik": "Kapağı yap", "tur": "taban", "kapak": True,
         "yap": ["Kapak çubuklarını taban gibi diz, altlarına iki rayı <b>içeri</b> "
                 "kalacak şekilde yapıştır. Raylar kapağı duvarların içine oturtur, "
                 "kapak kaymaz.",
                 "Kapağı yapıştırma — açılıp kapanabilir kalsın.",
                 "<b>Kutu prensibi:</b> kutunun kendi parçaları (çubuklar, ayaklar, "
                 "altlıklar) yapıştırılır; <b>içine giren hiçbir parça</b> yapıştırılmaz. "
                 "İleride başka bir kaba geçerken kartları, şöntü, Q1'i ve jakları "
                 "sökerek alırsın."],
         "kontrol": ["Kapak oturuyor ve kolay kalkıyor mu?",
                     "Kapak kapalıyken hiçbir kablo ezilmiyor."]},
        {"no": "13.2", "baslik": "Etiketle ve topla", "tur": "kontrol",
         "yap": ["Panel etiketlerini yapıştır: V, COM, SKOP, HV ⚡, YÜK, PİL, 24 V.",
                 "Kabloları kablo bağıyla topla; HV kablosunu ayrı tut."],
         "kontrol": ["Kapak kapalıyken kart hâlâ çalışıyor.",
                     "Kutuyu hafifçe salla: içeride oynayan bir şey yok."]},
    ]},
]

# ── kalibrasyon (seri konsol komutlari firmware'den) ───────────────────
KALIBRASYON = [
    ("s0.015", "Şönt değerini gir (15 mΩ)", "Bir kez. Şöntü değiştirirsen tekrar."),
    ("Z", "Akım sıfırı", "Yük bağlı DEĞİLken; J3'e hiçbir şey bağlı olmamalı."),
    ("i&lt;amper&gt;", "Akım kazancı", "Bilinen bir akım geçirirken; multimetrenin okuduğunu yaz."),
    ("n", "NORMAL menzile geç", "±32 V kanalı."),
    ("z", "Gerilim sıfırı", "V jakı boşta iken."),
    ("g&lt;volt&gt;", "Gerilim kazancı", "Bilinen gerilimi verip multimetrenin okuduğunu yaz."),
    ("y", "YÜKSEK menzile geç", "±614 V kanalı; sonra tekrar z / g."),
    ("P&lt;volt&gt;", "Pil kesme gerilimi", "Örnek: 18650 için 2.8 V."),
    ("?", "Bütün ayarları yaz", "Kalibrasyon sonunda oku, bir yere not et."),
]

# ── kullanim: neyi nereden olcerim ─────────────────────────────────────
KULLANIM = [
    ("Gerilim, ≤ 32 V", "V (kırmızı) + COM (siyah)",
     "Krokodil kabloyla devreye <b>paralel</b> bağla. Menzil: <code>n</code>.",
     "1.04 mV adım"),
    ("Gerilim, 32 – 614 V", "HV (kırmızı) + COM (siyah)",
     "Menzil: <code>y</code>. <b>Tek el kuralı</b>, eller uzakta, önce devreyi kapat.",
     "18.8 mV adım"),
    ("Akım, ≤ 11.5 A", "YÜK klemensi (J3)",
     "Devrenin dönüş hattını <b>seri</b> olarak buradan geçir: devrenin eksi ucu 1'e, "
     "kaynağın eksisi 2'ye.", "0.52 mA adım"),
    ("Güç ve enerji (W, Wh)", "V + COM ve YÜK klemensi birlikte",
     "Gerilim ve akım aynı anda bağlıysa kart gücü kendi hesaplar; reaktif yükte de doğru.",
     "işaretli, gerçek güç"),
    ("Osiloskop, ≤ 63 V", "SKOP (kırmızı) + COM",
     "Dalga şeklini görmek için. Zaman tabanı 100 µs – 500 ms/bölme.", "83 kSa/s'e kadar"),
    ("Pil kapasitesi (mAh)", "PİL klemensi (J7) + yük direnci",
     "Pilin artısı yük direncine, direncin öbür ucu J7.1'e, pilin eksisi J7.2'ye. "
     "Kesmeyi <code>P</code> ile gir, <code>p1</code> ile başlat.", "≤ 38 V pil"),
]

# ── alinacaklar (envanterde olmayan / belirsiz) ────────────────────────
ALINACAK = [
    ("Dil basacağı çubuk", "Kesim listesi {cubuk} çubuk istiyor (elde ~50 var). "
                           "Fire payıyla {cubuk_pay} almak iyi olur"),
    ("Yük yolu için kalın kablo (≥1.5 mm²)",
     "KBL003 karışık montaj kablosunda kalın damar varsa oradan; yoksa 1 m kırmızı + 1 m siyah"),
    ("TO-220 yalıtım seti (mika/silikon + burç)",
     "Q1'i soğutucudan yalıtmak için. 'Soğutucu izolatörü' kutusuna bak; yoksa al"),
]
