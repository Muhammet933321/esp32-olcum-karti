# -*- coding: utf-8 -*-
"""MUTASYON KOSUCUSU — "yesil test bir sey kanitlamaz"i olculebilir kilar.

    python mutasyon.py                 butun mutasyonlar
    python mutasyon.py --adim B22b     yalnizca o adimin mutasyonlari
    python mutasyon.py --liste         ne kosacagini yazar, kosmaz

Bu projenin altin kurali: bir iddia, onu YALANLAYAN bir degisiklikle
kirmiziya donmuyorsa BOSTUR. Simdiye kadar her mutasyon ELLE yapildi ve
sonucu DEVIR'e ELLE yazildi — yani tekrarlanabilir DEGILDI ve bir sure
sonra hangi mutasyonun hala tuttugu bilinmiyordu.

── IKI TASARIM KARARI ───────────────────────────────────────────────

🔴 YERINDE MUTASYON YOK. Proje bir git deposu DEGIL. "Boz, kostur, geri
al" deseninde bir Ctrl-C kaynagi bozuk birakir ve GERI DONUS YOLU YOKTUR.
Her mutasyon bir KOPYA uzerinde kosuyor; asil agac hic dokunulmuyor.

🔴 KOPYA `%TEMP%`'E DEGIL KARDES DIZINE. Uc betik agactan cikip
`Elekronic/` duzeyine bakiyor:

    test_firmware3.py   .araclar/arduino-cli.exe   (KOK.parents[1])
    bom_dogrula.py      stok-takip/envanter.csv
    sim3_ortusme.py     stok-takip/envanter.csv

`projeler/_mutasyon-<pid>/` kullanilirsa `KOK.parents[1]` yine
`Elekronic`'e cozulur ve ucu de calisir. `%TEMP%`'te hicbiri calismaz.

⚠ `_fs.json` ve `_fs.bin` KOPYALANIYOR — yoksa `sim3_web.py`'nin kosullu
  dali degisir ve iddia sayisi oynar, mutasyon sonucu yaniltir.

⚠ `--adim` HEDEFLEMESI SART: tam zincir ~6 dk; 20 mutasyonluk bir tur
  hedefsiz iki saat surer.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sayim                                            # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent

# Kopyalanmayacaklar: yeniden uretilebilir ya da agir.
#
# 🔴 `arsiv/` ONCE DISLANMISTI ve taban kosusu kopyada KIRMIZI dondu:
#    `kurulum3-uret.py:326` CSS'ini `arsiv/asama2/kurulum2.html`'den
#    okuyor — yani GUNCEL kurulum kilavuzu bir ARSIV dosyasina bagimli.
#    Derleme ciktilari temizlendikten sonra `arsiv/` zaten 6 MB / 52
#    dosya; dislamaya degmiyor. Ders: "eski asamalar" diye isaretlenmis
#    bir dizin, guncel uretecin bagimliligi olabilir.
ATLA = {"BELGELER", "__pycache__", ".git", "build"}
ATLA_DOSYA = {"DEVIR.md"}


# ── Mutasyon tanimlari ────────────────────────────────────────────────
# (adim, betik, dosya, eski, yeni, ne_kanitliyor)
#
# `betik` mutasyondan SONRA kosturulan sey. Beklenen sonuc: KIRMIZI
# (sifirdan farkli cikis) ya da IDDIA SAYISI degisimi.
# Tam zinciri kosturan mutasyonlar (~6 dk): yalnizca --adim ile.
AGIR = {"B3", "B23"}

MUTASYONLAR = [
    # ── B50 · kutu / panel plani (kutu.py) — B50g'de yeniden yazildi
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"tip": "jak", "x": 187.0, "z": 63.0',
     '"tip": "jak", "x": 170.0, "z": 63.0',
     "HV jaki komsusuna yaklasirsa kacak yolu (IEC takviyeli 12.6 mm) iddiasi "
     "kirmiziya donmeli"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"kablo": [11, 12],', '"kablo": [11],',
     "COM kablosu alt adimdan dusunce 'kart disi kablolarin hepsi bir alt adimda' "
     "iddiasi kirmizi olmali — eksik kalan kablo sessizce kaybolmasin"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"monte": ["RS", "Q1"],',
     '"monte": ["RS"],',
     "Q1 hic monte edilmezse hem parca iddiasi hem KAPI 8 / kablo sirasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"ic_boy": 154.0,', '"ic_boy": 120.0,',
     "kutu kisalirsa kart A on jak govdeleriyle cakisir ve dis derinlik tam sira "
     "olmaz: cakisma / sira iddialari kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"duvar_kat": 2,', '"duvar_kat": 1,',
     "duvar tek kata inerse 'duvar iki kat' iddiasi kirmizi — 2 mm tek kat esner, "
     "somun tutmaz"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"direk_kat": 3,', '"direk_kat": 2,',
     "kose diregi 4 mm'ye inerse M3 civatayi tasiyamaz: et kalinligi iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '("s0.015"', '("s0.15"',
     "kalibrasyon komutundaki sont degeri tasarim sabitinden kayarsa iddia kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"uc_egim": 10.0', '"uc_egim": 0.0',
     "cubugun yuvarlak uclari unutulursa (duz bolum = tam boy) kesim iddiasi "
     "kirmizi olmali — parcalar yuvarlak bolgeye tasar"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"nasil": "Tek çubuk altlığa kablo bağıyla; bacakları serbest, hava alsın. "',
     '"nasil": "Tabana sıcak silikonla yapıştırılır; bacakları serbest, hava alsın. "',
     "bir ic parca YAPISTIRILARAK tutturulursa sokulebilirlik iddiasi kirmizi "
     "olmali (kullanici ileride baska kaba gececek)"),
    # B50g — yeni iddialar
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"tip": "yuva", "x": 152.0, "z": 8.0', '"tip": "yuva", "x": 152.0, "z": 30.0',
     "USB yuvasi ESP32 soket yuksekliginden kayarsa (eski kusur: z=45) hizalama "
     "iddiasi kirmizi — fis sokete girmez"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"ref": "ESP32", "ad": "ESP32-S3 devkit", "x": 139.0,',
     '"ref": "ESP32", "ad": "ESP32-S3 devkit", "x": 120.0,',
     "ESP32 kayarsa USB yuvasi soketle hizasiz kalir ve A'nin ayagiyla cakisir: "
     "iki iddia da kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"kapak_civata_y": (45.0, 117.0),', '"kapak_civata_y": (10.0, 117.0),',
     "kapak civatasi direge/rayin disina kayarsa ray ve ic kat cubugu iddialari kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"tip": "jak", "x": 69.0, "z": 9.0', '"tip": "jak", "x": 45.0, "z": 9.0',
     "iki jak yaklasirsa (36 -> 12 mm) fis araligi ve ic kat cubuklari ust uste "
     "binme iddialari kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"renk": "kirmizi",\n     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (kırmızı)", "Konnektör"),\n     "etiket": "V"',
     '"renk": "siyah",\n     "parca": ("4mm Born Jak Banana Dişi Soket Vidalı (kırmızı)", "Konnektör"),\n     "etiket": "V"',
     "V jakinin rengi stok kaydiyla celisirse (siyah jak, kirmizi kayit) renk iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/yerlesim3_veri.py",
     '"T_SP":     ("A", "TEL", 2, 24, 180, 3, "/YUK_EKSI"),',
     '"T_SP":     ("A", "TEL", 2, 23, 180, 3, "/YUK_EKSI"),',
     "S+ teli yerlesimde bir satir kayarsa (C25 -> C24) kutu metnindeki delik adi eskir: "
     "'metni kart deligini adiyla veriyor' iddiasi kirmizi — kullanici yanlis delige takardi"),
    ("B50", "kutu.py", "uretim/yerlesim3_veri.py",
     '("X:J2.2", "X:J1.2", "sanal", 5,', '("X:J2.2", "X:J1.2", "sinyal", 5,',
     "sanal COM baglantisi gercek kablo sanilirsa 'kart disi kablolarin hepsi bir alt "
     "adimda' kirmizi — kullanici olmayan tel arardi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     "<b>COM'a krokodil TAKMA</b> — COM zaten YÜK 2'dir.",
     "<b>COM'a krokodil TAK</b> — COM zaten YÜK 2'dir.",
     "kullanim metni COM baypas uyarisini kaybederse iddia kirmizi (sont baypas, yanlis akim)"),
    ("B50", "kutu.py", "uretim/tasarim3_sabit.py",
     '"T 50 mA":  (21.29, 27e-3, "T"),', '"T 50 mA":  (21.29, 2.7e-3, "T"),',
     "T sigortanin erime I2t'si 10 kat dusuk olsaydi darbe payi 3x'in altina iner: iddia kirmizi "
     "(veri sayfasi sayisi degisirse karar yeniden verilir)"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     "F tipi → <b>T (gecikmeli) 50 mA cam</b> al", "F tipi → <b>50 mA cam</b> al",
     "10.1 metni 'gecikmeli' demeyi birakirsa kullanici yine F alir: iddia kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '{"ad": "50 mA T (gecikmeli) 5×20 cam sigorta, markalı", "stok": None,',
     '{"ad": "50 mA T (gecikmeli) 5×20 cam sigorta, markalı", "stok": ("50mA 5x20mm Cam Sigorta", "Sigorta"),',
     "T sigorta stoktaki F ile eslestirilirse 'alinacak' listesinden duser: iddia kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"not": "Bir tanesini ölç: gerçek 50 mA telin soğuk direnci', '"not": "Yenisini al. Bir tanesini ölç: gerçek 50 mA telin soğuk direnci',
     "stokta olan kalemin notuna 'al' girerse iddia kirmizi (B39 tuzagi: regex'te gercek 0x08 vardi, "
     "iddia oluydu — bu mutasyon onu kanitliyor)"),
    # B52 pil blogu — toprak tuzagi ve yerlesim
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '("MT1.OUT-", "ESP32.GND", "sinyal",', '("MT2.OUT-", "ESP32.GND", "sinyal",',
     "hucre 2'nin eksisi (=-12 rayi) ESP32 GND'ye baglanirsa -12 GND'ye kisa olur: graf iddiasi kirmizi "
     "(kart GND = 24V- + 12 V; sessiz ariza)"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     'PIL_SECICI = {"PİL": [("SWP2.P1", "SWP2.A1"), ("SWP2.P2", "SWP2.A2")],',
     'PIL_SECICI = {"PİL": [("SWP2.P1", "SWP2.A1"), ("SWP2.P2", "SWP2.A2"), ("SWP2.P2", "SWP2.B2")],',
     "secici tek kutuplu olsaydi (eksiler ortak) PIL konumunda XT30 eksisi -12'ye baglanir: iddia kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '"duvar": "arka", "x": 92.0, "z": 22.0,', '"duvar": "arka", "x": 92.0, "z": 12.0,',
     "yuva ESP32'nin ustune 6 mm'den yakin inerse 3B pay iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     "PC'deyken seçici PİL'e ALINMAZ (hücre 2 eksisi = −12 rayı).", "PC'deyken seçici PİL'e alınabilir (hücre 2 eksisi = −12 rayı).",
     "kullanim tablosu sarj kuralini kaybederse iddia kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '("TP1.OUT+", "SWP1.1", "pil", "korumalı çıkış (B+ değil!)"),', '("TP1.B+", "SWP1.1", "pil", "korumalı çıkış (B+ değil!)"),',
     "yuk TP4056'nin B+ ucundan alinirsa koruma devre disi kalir: SWP1 zinciri iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu.py",
     'ekle(k1, "Taban rayı — kısa parça", D * TABAN_EK[0], 2, "2.2")', 'ekle(k1, "Taban rayı — kısa parça", D * TABAN_EK[0], 2, "2.9")',
     "kesim listesindeki bir parca olmayan bir alt adima baglanirsa 'bir alt adimda kullaniliyor' kirmizi — "
     "kullanici o parcayi hicbir adimda gormezdi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py",
     '("0.9", "İlk elektrik', '("0.99", "İlk elektrik',
     "on kosul yerlesim planinda olmayan bir alt adima isaret ederse iddia kirmizi "
     "(HTML'den degil yerlesim3_adim'dan olculur — kopyada BELGELER yok)"),
    # ── B22b · kart web katmani
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "sunucu.enableDelay(false);", "/* sunucu.enableDelay(false); */",
     "WebServer'in kendi delay(1)'i periyodu tik sinirina kilitliyor "
     "(665 -> 500 SPS). B22.1'in en pahali bulgusu"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "sunucu.collectHeaders(", "sunucu.collectHeadersX(",
     "collectHeaders cagrilmazsa CSRF/Host savunmasi SESSIZCE oluyor: "
     "basliklar hic okunmuyor, denetim hep geciyor"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/ag.h",
     '#define AG_MDNS "olcum"', '#define AG_MDNS ""',
     "mDNS adi bosalirsa http://olcum.local cozulmez"),
    # 🔴 B39 — SIR SIZINTISI DENETIMI ILK YAYINDAN BERI KORDU. Desenin
    #    basindaki `\b` bir heredoc yamasinda GERCEK backspace (0x08)
    #    olarak yazilmisti; regex hicbir kaynakla eslesemiyordu ve 5c her
    #    zaman yesildi. Depo herkese acik, kural "parola depoda olmaz".
    #    Bu mutasyon o denetimin ISIRDIGINI kanitliyor. (Kacak olmamis:
    #    bugunku agac ve kod/ git gecmisi dogru desenle 0 esleşme.)
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/ag.h",
     '#define AG_MDNS "olcum"',
     # ⚠ Dize `sifre` ile ` =` ARASINDAN bolunuyor: baska yerden bolunse
     #   bu satirin METNI de desene uyuyor ve bu dosya depoda "gomulu
     #   parola" gibi gorunuyordu (metin tabanli denetimin kendi test
     #   verisini yakalamasi — bu projede altinci kez).
     '#define AG_MDNS "olcum"\nstatic const char *wifi_sifre' + ' = "gizli1234";',
     "firmware'e GOMULU parola girerse (ikilide duz metin, depo acik) "
     "5c KIRMIZI donmeli — ilk yayindan beri donmuyordu"),
    # ── B26 · ayna + acik cagri = her satir IKI KEZ (kartta olculdu)
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    Serial.println(son_satir);",
     "    Serial.println(son_satir);\n    akis_yolla(son_satir);",
     "ESKI KUSURU geri koyar: ayna zaten yolluyorken acik cagri da "
     "eklenince her `D` satiri SSE'ye iki kez dusuyor. Kartta olculdu: "
     "8 sn'de 80 olay / 40 benzersiz, dagilim {2: 40}"),

    # ── B26 · AP SSID gercekten MAC'ten mi geliyor (GERCEK KARTTA bulundu)
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/ag.h",
     "esp_read_mac(m, ESP_MAC_WIFI_SOFTAP);", "WiFi.macAddress(m);",
     "TAM ESKI KUSURU geri koyar: ag_baslat() bu fonksiyonu "
     "WiFi.mode()'dan ONCE cagirdigi icin surucu baslamamis olur, "
     "WiFi.macAddress() tampona dokunmaz ve SSID'e ilklenmemis yigin "
     "bellegi girer (kartta gorulen: OLCUM-KARTI-ABAB)"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     'Serial.print(F("  MAC=")); Serial.print(ag_durum.mac);', "",
     "afisten GERCEK MAC kalkarsa tezgah kosucusunun SSID denetimi "
     "karsilastiracak bagimsiz olcutu kaybeder"),

    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "korumasiz", "parola yok",
     "web parolasi KALDIRILDI mesaji, komut ucunun O AN korumasiz "
     "kaldigini soylemeli — sessiz bir 'kaldirildi' yetmez"),

    # ── B26 · gizlilik: depo herkese acik, kisisel iz KIRMIZI olmali
    #    (dosya: README.md — takip ediliyor, metin, kopyada da var)
    #    ⚠ Ornek dizgeler PARCALI kuruluyor: literal olarak yazilsalardi
    #      tarayici BU DOSYAYI yakalar ve taban kosu kirmizi olurdu —
    #      metin tabanli iddianin kendi test verisini yakalamasi, bu
    #      projede besinci kez. chr(92) = ters bolu, chr(64) = @.
    ("B26", "gizlilik_dogrula.py", "README.md",
     "# ", "# C:" + chr(92) + "Users" + chr(92) + "birisi" + chr(92) + "x ",
     "kullanici klasoru yolu takip edilen bir dosyaya girerse tarama "
     "KIRMIZI donmeli; donmezse denetim kordur (B26'da 59 iz yesil "
     "zincirin altinda duruyordu)"),
    ("B26", "gizlilik_dogrula.py", "README.md",
     "# ", "# birisi" + chr(64) + "ornek.com ",
     "e-posta adresi takip edilen dosyaya girerse tarama kirmizi donmeli"),
    # B39 — kacis dizisi GERCEK karaktere donerse (heredoc tuzagi) tarama
    # kirmizi donmeli. chr(8) ile kuruluyor: literal yazilsaydi bu dosyanin
    # KENDISI taramaya takilirdi.
    ("B26", "gizlilik_dogrula.py", "README.md",
     "# ", "# x" + chr(8) + "y ",
     "backspace iceren bir satir, bir regex'in sessizce kor oldugu demek "
     "(sim3_web.py'nin parola denetimi ilk yayindan beri boyleydi)"),

    # ── B22a · PC koprusu
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     'SERBEST_KOMUTLAR = {"p0"}', "SERBEST_KOMUTLAR = set()",
     "p0 (pil desarjini DURDUR) her zaman parolasiz gecmeli — "
     "emniyet ozelligi, kolaylik degil"),
    ("B22a", "test_kopru.py", "kopru/arsiv.py",
     "def ham_satirlar", "def ham_satirlar_",
     "role BAYT-SEFFAF olmali; arsivin ham okuma yolu kaybolursa "
     "girdi/cikti karsilastirmasi yapilamaz"),

    # ── B35 · skop kopru kipinde + geriye donuk kayit
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     'if yol == "/skop.bin":\n            return self._skop_canli()', "",
     "ESKI CANLI KUSURU geri koyar: kopru kipinde `/skop.bin` yoktu, "
     "arayuz 404 aliyordu — osiloskop tam da PC'ye bagliyken olu bir "
     "dugmeydi"),
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     'self.kart.yaz("t")', 'self.kart.yaz("tB")',
     "`tB` dokumu seri porta HIC basmaz (kartin kendi HTTP ucuna "
     "birakir); kopru USB'den bagli oldugu icin ne yakalama gelir ne de "
     "arsive bir sey duser — 'kayit aliyorum' sanip hicbir sey kaydetmek"),
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     'if not blok["tam"]:', "if False:",
     "kirpik blok cizilirse eksik dalga 'olculmus' gibi gorunur; "
     "tekrar denemek ucuzken yanlis sekil gostermek pahali"),
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     'if satir.startswith("! tetiklenemedi"):', "if False:",
     "tetiklenemeyen yakalamada arayuz 20 s bosuna bekler; kullanici "
     "kartin calistigini sanir"),
    ("B22a", "test_kopru.py", "kopru/arsiv.py",
     # ⚠ Baglamla daraltildi: `self._gun = None` __init__'te de var; kosucu
     #   HER esleşmeyi degistirdigi icin ikisi de siliniyor ve test yanlis
     #   sebeple (hic tanimlanmamis nitelik) kirmiziya donuyordu. Hedef
     #   yalnizca kapat()'taki satir.
     "        #    aciliyor, yeniden acmak hicbir sey kaybettirmiyor.\n        self._gun = None\n",
     "        #    aciliyor, yeniden acmak hicbir sey kaybettirmiyor.\n",
     "ESKI CANLI KUSURU geri koyar: kapatilmis arsive yazma "
     "AttributeError atip YUKARI-AKIS IPLIGINI olduruyordu — kopru "
     "ayakta gorunur, arsiv de SSE de olu, hicbir yerde yazmaz"),
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     "            except Exception as e:                        # noqa: BLE001\n"
     "                ms = 0\n",
     "            except ZeroDivisionError as e:\n                ms = 0\n",
     "arsiv hatasi yine roleyi oldurur; role kritik islev, arsiv ikincil"),
    ("B22a", "test_kopru.py", "kopru/arsiv.py",
     "        yer = self.baslik[\"adet_bildirilen\"] - len(self.ornek)",
     "        yer = 1 << 30",
     "bozuk bir `S2` uzun sayi akisina denk gelirse ornek listesi "
     "sinirsiz buyur; bildirilen adet tavan olmali"),
    ("B22a", "test_kopru.py", "kopru/arsiv.py",
     "            self.atlanan += 1", "            pass",
     "blok icinde gelen `D` satiri sessizce yutulursa eksik bir dalga "
     "'tam' gorunur"),
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     '            if metin == "tB":\n                metin = "t"',
     "            pass",
     "`tB` karta oldugu gibi giderse dokum seri porta HIC basilmaz: "
     "kopru USB'den bagliyken ne yakalama gelir ne arsive bir sey duser"),
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     "        if metin in SKOP_KOMUTLARI:\n            k.skop_hazirla()",
     "        if False:\n            k.skop_hazirla()",
     "kopru arayuzun yakalama komutunu tanimazsa `/skop.bin` KENDI `t`sini "
     "yollar: kart IKI KEZ yakalar ve arayuze donen dalga kullanicinin "
     "tetikledigi dalga olmaz"),
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     "        if metin in SKOP_KOMUTLARI:",
     '        if metin.startswith("t"):',
     "onek eslemesi `tb0`/`tl500` gibi AYAR komutlarini da yakalama "
     "sanar; her ayar degisikligi bosuna yakalama bekler"),

    # ── B20 · ornekleme hizi
    ("B20", "sim3_bant.py", "uretim/tasarim3_sabit.py",
     "ADS_SPS = 860", "ADS_SPS = 250",
     "ornekleme hizi butun zamanlama butcesinin tabani"),
    # ── B27/K1 · yanit vermeyen ADC sessiz kalmasin (kartta gorüldu)
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    ads_hata |= bit;", "    /* ads_hata |= bit; */",
     "ESKI KUSURU geri koyar: okuma basarisizken hata biti kurulmaz, "
     "`durum` hep 0, arayuz sahte 1.716 V'u olcum sanir"),
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  if (!ads_hata) enerji_biriktir(o.watt);",
     "  enerji_biriktir(o.watt);",
     "enerji kapisi kalkarsa yanit vermeyen cipin copu Wh sayacina girer "
     "(kartta 3 dk'da 0.03 J bos giristen)"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "this.adsDurum = p.length >= 10 ? parseInt(p[9], 10) : 0;",
     "this.adsDurum = 0;",
     "arayuz `durum` alanini okumazsa 'veri yok' hic gorunmez"),
    # ── B27/K3 · bos giris W basmasin
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "            return;   /* K3: W BASILMAZ */",
     "            /* return; */   /* K3: W BASILMAZ */",
     "return kalkarsa uyari basilir AMA W de basilir; bos giristen 223 W "
     "yine ekrana gider"),
    # ── B27/K2 · guc yonu olu bandi
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "Math.abs(this.watt) < 1e-3", "Math.abs(this.watt) < 0",
     "olu bant kalkarsa gurultu duzeyindeki -10 uW 'kaynak' etiketi uretir"),

    # ── B27 A1 · gorunumler (hash yonlendirme)
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     "<main class=\"gorunum\" v-show=\"gorunum === 'skop'\">",
     "<main class=\"gorunum\" v-if=\"gorunum === 'skop'\">",
     "v-if tuvali YOK EDER: skop sekmesine donunce yakalama kaybolur, "
     "grafik ilk D satirina kadar bos"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      this.$nextTick(() => { this.grafikCiz(); this.osiloCiz(); });\n    },\n    /* B22.2",
     "      this.$nextTick(() => { this.grafikCiz(); });\n    },\n    /* B22.2",
     "skop yeniden cizilmezse gizliyken 0 genislik okuyan tuval 300px "
     "varsayilanda, sola yapisik kalir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "return GORUNUMLER.some((g) => g.id === h) ? h : GORUNUM_VARSAYILAN;",
     "return h || GORUNUM_VARSAYILAN;",
     "bilinmeyen hash (#/yok) bes gorunumun HICBIRINI acmaz — bos sayfa"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "window.addEventListener('hashchange', () => { this.gorunum = hashtenGorunum(); });",
     "",
     "hashchange dinlenmezse geri tusu adresi degistirir ama gorunum "
     "degismez — adres ile ekran ayrisir"),

    # ── B27 A2 · rapor araligi + grafik bosluklari
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "          v: this.voltGecersiz  ? NaN : this.volt,",
     "          v: this.volt,",
     "grafik K1 sizintisi geri gelir: kartlar 'veri yok' derken cizgi "
     "sahte 1.72 V'u cizer"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "          if (Number.isNaN(deger)) { kopuk = true; continue; }",
     "          if (Number.isNaN(deger)) { continue; }",
     "bosluk yerine NaN'in iki yani BIRLESTIRILIR — yanit vermeyen "
     "pencere yokmus gibi cizilir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "          if (this.kartRapor !== this.raporMs && this.surucuyum) {",
     "          if (this.kartRapor !== this.raporMs) {",
     "izleyici de r<ms> yollar: sunucu reddeder ama her baglanti bir "
     "hata satiri uretir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (grafikBekliyor) return;",
     "      if (false) return;",
     "cizim birlestirme kalkar: 20 satir/s'de saniyede 20 tam cizim"),

    # ── B35 · skop arsivi (geriye donuk kayit)
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        if (this.skopIkiliCoz(await y.arrayBuffer())) {",
     "        if (await this.skopArsivCozKopya(y)) {",
     "arsiv kaydi AYRI bir cozucuden gecerse eski kayit canlidan BASKA "
     "cizilir — endian/olcek/ofset ayrisir ve hata SESSIZ olur"),
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     '<section class="kart" v-if="skopArsivVar">',
     '<section class="kart">',
     "kart dogrudan bagliyken (kayit YOK) bolum yine cizilir: OLU DUGME, "
     "DEVIR 4.15'in tam kendisi"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      this.skopAcikKayit = null;     // canli yakalama: artik arsiv kaydi degil",
     "",
     "canli dalga 'ARSIV' seridiyle gosterilir; kullanici neye baktigini "
     "bilemez"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "          if (this.surekli) this.surekliDegis();",
     "",
     "surekli kip acikken arsiv kaydi acilinca bir sonraki tur kaydin "
     "ustune canli dalgayi cizer"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (this.skopArsivVar && !this.surekli) this.skopKayitlariYukle(this.skopGun);",
     "      if (this.skopArsivVar) this.skopKayitlariYukle(this.skopGun);",
     "surekli kipte her yakalamada liste cekilir: kopru bosuna mesgul"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (this.skopArsivVar) {\n        this.gonder('t');\n      } else if",
     "      if (false) {\n        this.gonder('t');\n      } else if",
     "koprude de `tB` + `/skop.bin` kullanilir: dokum zaten seri porttan "
     "geldigi halde ayni dalga IKINCI KEZ tasinir ve IKI KEZ cizilir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (!this.skopArsivtenAciliyor) this.skopListeTazeleGerekirse();",
     "",
     "koprudeki ASCII yakalamalari kayit listesine HIC dusmez: "
     "kullanici 'Yakala'ya basar, kayit diske yazilir ama listede gorunmez"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (this.osiloBekliyor) {\n        bekleme = 150;",
     "      if (false) {\n        bekleme = 150;",
     "ESKI HALI: surekli kip onceki yakalamayi beklemeden her 500 ms'de "
     "bir yenisini ister. Koprude dokum seri porttan geciyor (4000 ornek "
     "~1.8 s), yani kuyruk birikir, bloklar birbirini keser ve arsiv "
     "kirpik kayitlarla dolar"),
    # ── B36 · skop gerilim ekseni kalibrasyonu
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (k) return this.kalMv(kod) / 1000 * k.oran - of;", "",
     "kalibrasyon tablosu gelse bile KULLANILMIYOR: eksen eski sabit "
     "carpanla ciziliyor, girisde 9 V'a varan sapma geri geliyor"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      return this.kodVolt(this.skopEsik);",
     "      return this.skopEsik * (3.10 / 4096 * 38.03703704) - 63.53009;",
     "tetik seviyesi IKINCI bir ceviri yolundan geciyor: izgara "
     "kalibre, tetik cizgisi ham — ekranda iki farkli eksen"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        ust + boy * (1 - (this.kodVolt(v) - vmin) / (vmax - vmin));",
     "        ust + boy * (1 - (v * this.osilo.voltAdim - vmin) / (vmax - vmin));",
     "iz ham cevirimle cizilirken dikey olcek kalibre kaliyor: etiketler "
     "bir seyi, dalga baska seyi gosterir ve hata SESSIZ"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        this.skopKal = (kal.oran > 0 && kal.kod.length >= 2",
     "        this.skopKal = (true || kal.oran > 0 && kal.kod.length >= 2",
     "bozuk/yarim tablo kabul edilir ve duzeltme yapiyormus gibi gorunup "
     "ekseni bozar"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "                        && sayiTamam) ? kal : null;",
     "                        ) ? kal : null;",
     "`256:abc` gibi bozuk bir cift NaN uretiyor; uzunluk ve `oran` "
     "denetimlerinden GECIYOR, sonra her gerilim NaN oluyor ve dalga "
     "ekrandan SESSIZCE kayboluyor — 'kalibre' rozeti yanarken"),
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     '<span v-if="skopKal" class="kal-rozet"',
     '<span v-if="false" class="kal-rozet"',
     "eksenin kalibre olup olmadigi EKRANDA yazmaz: duzeltmesiz eksen "
     "'olculmus' gorunur ve sayilar sessizce yanlis okunur"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        try { await this.gonder('CT'); } catch (e3) { /* tablosuz devam */ }",
     "",
     "kalibrasyon tablosu HIC istenmez: eksen her zaman duzeltmesiz kalir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        return vs[n - 1] + (kod - ks[n - 1]) * e;",
     "        return vs[n - 1];",
     "tablo disi kod KIRPILIR: doyuma giren sinyal DUZ bir cizgi gibi "
     "gorunur ve kirpildigi anlasilmaz"),

    # ── B40 · arayuz: dokum olcumle ic ice, ikili cekis satir tetikli
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        if (/^\\d+(\\s+\\d+)*$/.test(satir.trim())) {",
     "        if (true) {",
     "araya giren D satiri dalgaya COP ornek olarak girer (parseInt('1.7156')=1) "
     "ve olcum gostergesine ulasmaz"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        this.skopIkiliBekle = true;\n        this.gonder('tB');",
     "        this.gonder('tB');\n        setTimeout(() => this.skopIkiliAl(), 400);",
     "ESKI HALI: sabit 400 ms sonra cekis — yakalama uzunsa /skop.bin 503"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        this.skopIkiliBekle = false;\n        this.skopIkiliAl();",
     "        this.skopIkiliAl();",
     "bayrak silinmez: sonraki her onay satiri govdeyi IKINCI kez ceker"),

    # ── B39 · heredoc `\b` backspace'e donmustu: bu iki iddianin yarisi
    #    ilk yazildiklari gunden beri KORDU. Artik canli; isirdiklarini
    #    kanitlayan mutasyonlar:
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     '<span v-if="!k.tam" class="kayit-etiket dikkat">',
     '<span v-if="!k.tam" class="kayit-etiket uyari">',
     "rozete emniyet-uyarisi KUTU stili bulasir (B35'te tarayicida "
     "gorulmustu); iddianin bu yarisi backspace yuzunden kordu"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      const { veri, hz, adet } = this.osilo;",
     "      const { veri, hz, adet } = this.osilo;  // veri[i] * voltAdim",
     "cizimde ikinci bir ham ceviri izi; iddianin bu yarisi backspace "
     "yuzunden kordu"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "          kal: p.length >= 11 ? p[10] === '1' : null,",
     "          kal: p.length >= 11 ? p[10] === '1' : true,",
     "eski firmware'in 10 alanli `W` satiri 'kalibre' sanilir"),

    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        this.kopruYokla();", "        await this.kopruYokla();",
     "arsiv yoklamasi baglanmayi BLOKLAR: yoklama takilirsa olcum de "
     "baslamaz — ek ozellik kritik yolu tutamaz"),
    ("B7", "test_arayuz3.js", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        if (v < RAPOR_MS_EN_AZ)  v = RAPOR_MS_EN_AZ;",
     "        /* alt sinir yok */",
     "`r1` kabul edilir: olcum dongusu satir basmaktan olcum alamaz"),
    ("B7", "test_arayuz3.js", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    akis[i].write((const uint8_t *)olay, (size_t)n);",
     "    akis[i].print(olay);",
     "SSE olayi yine tek parca ama print() — write() iddiasi bunu "
     "ayirt etmeli (print sonunda ek kopya, ayni sey degil)"),
    ("B7", "test_arayuz3.js", "arayuz3/sahte-kart.js",
     "        raporMs = Math.max(RAPOR_EN_AZ, Math.min(RAPOR_EN_COK, v));",
     "        raporMs = v;",
     "demo kipi firmware'den farkli davranir: r5 -> 5 ms"),

    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (/(^|[?&])demo(=|&|$)/.test(k.search)) return false;",
     "",
     "?demo'da da baglanmaya kalkar: sahte kart yerine gercek /akis aranir, "
     "demo 'Baglanamadi' ile acilir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      return this.tasiyiciAdi === 'akis' && !this.bagli;",
     "      return !this.bagli;",
     "USB kipinde de otomatik baglanir: Web Serial izin penceresi kullanici "
     "istemeden acilir"),

    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      uyg.akis.addEventListener('kimlik', bitir, { once: true });",
     "      bitir();",
     "ac() kimlik gelmeden doner: `?` bos jetonla gider, kart 403 der, "
     "K5 esitlemesi WiFi'de hic calismaz (kartta CDP ile olculdu)"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      uyg.akis.addEventListener('error', bitir, { once: true });",
     "",
     "akis hatasinda ac() askida kalir: baglan() hic donmez"),

    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  if (k[0] == '?' && k[1] == 0) return true;",
     "  if (k[0] == '?') return true;",
     "`?x` de serbest olur — tam eslesme iddiasi bunu yakalamali"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  if (k[0] == '?' && k[1] == 0) return true;\n  return false;",
     "  if (k[0] == '?' && k[1] == 0) return true;\n  if (k[0] == 'N') return true;\n  return false;",
     "`N` serbest olursa AP ve web parolasi jetonsuz okunur"),

    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      const sont = this.kartSont !== null ? this.kartSont : parseFloat(this.sontSecim);",
     "      const sont = parseFloat(this.sontSecim);",
     "menu 1 ohm derken kart 0.1 ohm calisiyorsa adim 10 kat KUCUK yazilir — "
     "gurultu gercek akim sanilir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "const ADS_PGA_V = 0.256;",
     "const ADS_PGA_V = 2.048;",
     "arayuzun kademesi firmware'inkinden (PGA_0256) ayrisir: menzil 8 kat yanlis"),

    # ── B27 A2 · tasarim sistemi
    ("B7", "test_arayuz3.js", "arayuz3/style.css",
     "    --amper:       #b0590a;",
     "    --amper:       #1f5ed0;",
     "acik temada akim ile gerilim AYNI renk olur; grafikte iki kanal "
     "ayirt edilemez"),
    ("B7", "test_arayuz3.js", "arayuz3/style.css",
     "    --cok-soluk:   #75828f;",
     "",
     "belirtec yalnizca koyu temada kalir; acik temada var() sessizce "
     "gecersize duser ve o renk hic uygulanmaz"),
    ("B7", "test_arayuz3.js", "arayuz3/style.css",
     "@media (prefers-reduced-motion: reduce) {",
     "@media (min-width: 1px) and (prefers-reduced-motion: xyz) {",
     "hareketi azalt tercihi karsiliksiz kalir"),
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     '        <option value="demo">Demo — sahte kart</option>\n',
     "",
     "?demo ile tasiyici 'demo' olur ama menude karsiligi yoktur: "
     "secici BOS gorunur"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "  destekli() { return true; },",
     "  destekli() { return typeof SahteKart !== 'undefined'; },",
     "menuden demo secen kullanici OLU DUGME gorur (betik daha inmedi)"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (this.demoKurulu) return;",
     "      if (false) return;",
     "sahte-kart.js iki kez iner: 'SahteKart has already been declared'"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (this.bagli && acik && acik !== v && TASIYICILAR[acik]) {",
     "      if (this.bagli && TASIYICILAR[eski]) {",
     "watch, demo'nun az once actigi baglantiyi 'eski tasiyici' sanip "
     "kapatir; demo akisi ilk 300 noktadan sonra susar"),
    # ── B27 A3 · telefon + acil durdurma
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     "  <div v-if=\"pilDurum === 'CALISIYOR'\" class=\"acil\">",
     '  <div v-if="false" class="acil">',
     "desarj surerken acil serit HIC gorunmez: durdurmak icin once dogru "
     "sekmeyi bulmak gerekir"),
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     '    <button class="acil-dur" @click="pilDurdurKomut">DURDUR</button>',
     '    <button class="acil-dur" :disabled="!surucuyum" @click="pilDurdurKomut">DURDUR</button>',
     "izleyici oturumda durdurma kilitlenir — oysa `p0` bilerek jetonsuz"),
    ("B7", "test_arayuz3.js", "arayuz3/style.css",
     "  .olcum.w { grid-column: 1 / -1; }",
     "",
     "telefonda guc karti yarim sutunda kalir: 32 px'lik sayi kutuya "
     "sigmaz, tasar"),
    ("B7", "test_arayuz3.js", "arayuz3/style.css",
     "  .ust .alt { display: none; }        /* alt başlık telefonda yer kaplıyor */",
     "",
     "telefonda ust serit bir satir daha buyur, olcumler ilk ekrandan duser"),

    # ── B27 A4 · butce ve dayaniklilik
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     "<script src=\"app.js\" onerror=\"arayuzHata('app.js')\"></script>",
     '<script src="app.js"></script>',
     "app.js gelmezse sayfa sessizce bos kalir; kullanici neden "
     "acilmadigini ogrenemez"),
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     '<div id="acilmadi" hidden class="hata" style="margin:20px">',
     '<div id="acilmadi" class="hata" style="margin:20px">',
     "hata kutusu HER acilista gorunur — saglikli sayfada bile"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      return (this.pilDurum === 'CALISIYOR' || this.gorunum === 'pil') ? 2000 : 10000;",
     "      return 2000;",
     "bosta da 2 s'de bir yoklanir: kartta bosuna ~15 ms/2 s olcum kaybi"),

    # ── B28 · cift cekirdek (kartta OLCULDU: 186 ms -> 3.8 ms)
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  komut_isle();              // seri porttan gelen komutlar",
     "  sunucu.handleClient();\n  komut_isle();              // seri porttan gelen komutlar",
     "handleClient loop()'a geri gelirse sayfa sunmak olcumu yine "
     "blokluyor — bu asamanin butun sebebi"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "                            &ag_gorev_kolu, 0);",
     "                            &ag_gorev_kolu, 1);",
     "gorev olcum cekirdegine (1) kurulursa ayirma gorunuste var ama "
     "gercekte yok: ayni cekirdek, ayni blokaj"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    vTaskDelay(1);             // 1 tik = 1 ms; IDLE0 ac kalmasin",
     "    /* vTaskDelay(1); */",
     "tik birakmayan gorev IDLE0'i ac birakir; gorev bekci kopegi karti "
     "yeniden baslatir"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     # ⚠ Desen kaynakla AYNI olmali: `akis_tasma++` -> `akis_tasma =
     #   akis_tasma + 1` olunca bu mutasyon "UYGULANAMADI" diye dusmus
     #   ve kimse fark etmemisti — uygulanamayan mutasyon, iddiayi
     #   SINAMAYAN mutasyondur. Kosucu bunu ayri raporluyor, iyi ki.
     "  if (xQueueSend(akis_kuyrugu_q, &ak, 0) != pdTRUE) akis_tasma = akis_tasma + 1;",
     "  akis_yolla(satir);",
     "olcum cekirdegi sokete yazmaya geri doner: hem akis[] dizisinde "
     "ikinci yazar hem de kaldirilan blokaj geri gelir"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    if (skop_kilidi && xSemaphoreTake(skop_kilidi, 0) != pdTRUE) {",
     "    if (skop_kilidi && xSemaphoreTake(skop_kilidi, portMAX_DELAY) != pdTRUE) {",
     "olcum tarafi HTTP dokumunu beklerse cift cekirdegin anlami kalmaz"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     '    snprintf(isaret, sizeof(isaret), "! akis: %lu satir dustu (kuyruk doldu)",',
     '    snprintf(isaret, sizeof(isaret), "",',
     "dusen satir sessiz kalir: eksik bir skop dokumu TAM sanilir"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  Serial.setTxBufferSize(8192);\n  Serial.begin(115200);",
     "  Serial.begin(115200);\n  Serial.setTxBufferSize(8192);",
     "begin()'den SONRA cagrilan setTxBufferSize ise yaramaz; `?` "
     "ciktisi yine 27 ms bloklar"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  Serial.setTxBufferSize(8192);", "  Serial.setTxBufferSize(2048);",
     "ESKI DEGERI geri koyar: halka ogesi ek yuku yuzunden `?` 2048'de "
     "doluyor, 19.4 ms blokluyor ve bringup 20 ms esigini asiyor "
     "(kartta olculdu, 2026-09-13)"),

    # ── B29 · cevrim faz olcumu (iki ADS takilinca kartta olculdu)
    ("B25", "test_tezgah_kart.py", "uretim/tasarim3_sabit.py",
     "I2C_ISLEM_EK_US = 69.0", "I2C_ISLEM_EK_US = 0.0",
     "I2C islem yuku modelden cikarsa beklenti 104 -> 133'e ziplar ve "
     "saglikli kart 'ornek sayisi bantta degil' diye kirmizi yanar"),
    ("B25", "test_tezgah_kart.py", "uretim/tezgah_kart.py",
     "           80.0 <= kayma <= 400.0,",
     "           0.0 <= kayma <= 100000.0,",
     "kayma bandi genisleyince iki baslatma arasina is girmesi (faz "
     "hatasi) gorunmez olur — B17'nin en pahali kusuru"),
    ("B25", "test_tezgah_kart.py", "uretim/tezgah_kart.py",
     '    tik = [ad for ad in ("yaz_us", "bek_us", "oku_us")',
     '    tik = [ad for ad in ()',
     "tik kilidi denetimi bosalir: B22.1'in enableDelay kusuru geri "
     "gelse ornek sayisi bandin ICINDE kalacagi icin hic yakalanmaz"),

    # ── B30 · ALERT teli teshisi + CAL cikisi (kartta yasandi)
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    rdy_zaman_asimi++;", "    /* rdy_zaman_asimi++; */",
     "tel dustugunde kart 3 kat yavaslar ve HICBIR SEY soylemez — "
     "2026-09-12'de tam olarak bu yasandi"),
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    case '#': i2c_tara(); alert_probu(); break;",
     "    case '#': i2c_tara(); break;",
     "donanim akil sagligi komutu I2C adreslerini gosterip ALERT telini "
     "atlar: kusurun yarisi gorunur, yarisi kacar"),
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    iki = (alert_dener(ADS_GERILIM, etkin_kanal()->pga, &sure2) == ALERT_VAR);",
     "    iki = false;",
     "prob yalnizca #1'i dener: tel YANLIS MODULDE ise 'tel yok' ile "
     "ayni cikti gelir ve kullanici bosuna arar"),
    # ── B46 · prob hat zaten dusukken VAR demesin
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    if (!yukseldi) { if (p == HIGH) yukseldi = true; continue; }\n", "",
     "ESKI KUSURU geri koyar: hat zaten dusukken ilk turda 'VAR' — modul "
     "I2C'de yokken 'RDY calisiyor' basiyordu (2026-09-13)"),
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  if (Wire.endTransmission() != 0) return ALERT_ACK_YOK;",
     "  Wire.endTransmission();",
     "ACK'lamayan modulde RDY sinamasi yapilir ve sonuc anlamsizdir"),
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "      Serial.print(F(\" istenen=\"));      Serial.print(istek);",
     "",
     "CAL ciktisi yalnizca istenen frekansi basar; skop olcumu kendi "
     "varsayimiyla dogrulanir (LEDC 7000 -> 6998 kirpiyor)"),

    # ── B31 · skop zaman tabani (CAL cikisiyla kartta olculdu)
    # ── B47 · tetik onayi (gurultu reddi), ayarlanabilir
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "                        tetik_w = (uint16_t)((w + n - 2u) % n);\n"
     "                        kalan = (uint16_t)(sonra - 2u);",
     "                        tetik_w = (uint16_t)((w + n - 1u) % n);\n"
     "                        kalan = (uint16_t)(sonra - 1u);",
     "onay ornegi tetik sayilir: on-tetik konumu 1 kayar (B42 bozulur)"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "                    if (cift) {\n                        bekleyen = true;",
     "                    if (false) {\n                        bekleyen = true;",
     "ESKI KUSURU geri koyar: onay=2 secilse de tek ornekte tetikler, igne sahte tetik"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    if (on + 3u > n) on = (uint16_t)(n - 3u);",
     "    if (on + 2u > n) on = (uint16_t)(n - 2u);",
     "on=%90 ve kisa halkada onay ornegi sigmaz, kalan tasar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "static SkopAyar skop_ayar = { 5, 2048, 0, 40, 25, SKOP_KIP_OTO, 2 };",
     "static SkopAyar skop_ayar = { 5, 2048, 0, 40, 25, SKOP_KIP_OTO, 1 };",
     "varsayilan tek ornek: kullanici dokunmadan sahte tetik riski"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        const on2 = sayi(a.onay);  if (on2 === 1 || on2 === 2) this.skopOnay = on2;\n", "",
     "arayuz kartin bildirdigi onayi okumaz: menu yalan soyler"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        const on2 = sayi(a.onay);  if (on2 === 1 || on2 === 2) this.skopOnay = on2;",
     "        const on2 = sayi(a.onay);  this.skopOnay = on2 === null ? 2 : on2;",
     "eski firmware'de (onay yok) menu 2 gosterir ama kart tek ornekte tetikler"),
    ("B7", "test_arayuz3.js", "arayuz3/index.html",
     "@change=\"skopKomut('tn' + skopOnay)\"", "@change=\"skopKomut('tm' + skopOnay)\"",
     "menu yanlis komut gonderir: onay yerine KIP degisir"),
    ("B7", "test_arayuz3.js", "arayuz3/sahte-kart.js",
     "        if (v !== 1 && v !== 2) return ['! onay 1=tek ornek 2=iki ornek (gurultu reddi)'];\n", "",
     "sahte kart gecersiz onayi kabul eder — firmware'den ayrisir"),

    # ── B45 · tarayici gezisinde bulunanlar (zaman grafigi, birimler, konsol, arsiv)
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        if (d[al] < 0) negatif = true;\n", "",
     "ESKI KUSURU geri koyar: negatif deger tuvalin disina cizilir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        const yOl = (deger) => negatif ? ust + boy * (1 - deger / enb) / 2\n"
     "                                      : ust + boy * (1 - deger / enb);",
     "        const yOl = (deger) => ust + boy * (1 - deger / enb);",
     "eslem sifiri hep alta koyar: negatif yari kaybolur"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      const tabanda = enb < taban;", "      const tabanda = false;",
     "ESKI KUSURU geri koyar: 0.05 LSB gurultu ekrani doldurur"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      const v = 20 * vLsb, i = 20 * iLsb;", "      const v = 0, i = 0;",
     "taban sifir: gurultu yine tam ekran"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      const V = (x) => (isFinite(x) ? x.toFixed(3) : '—') + ' V';",
     "      const V = (x) => muh(x, 'V', 3);",
     "ESKI KUSURU geri koyar: 'Vmax 348.200 mV' yaninda 'Vmin -4.092 V'"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "           (tarayıcıda görüldü). */\n        this.kaydet(satir);\n",
     "           (tarayıcıda görüldü). */\n",
     "ESKI KUSURU geri koyar: `A` satiri konsola dusmez, 'Ayarlari goster' bos"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      o.Vmax = this.kodVolt(hmax);", "      if (!('Vmax' in o)) o.Vmax = this.kodVolt(hmax);",
     "eski kaydin dogrusal-model Vmax'i eksenle 7 V celisir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "          this.osilo.olcum = this.skopArsivOlcum(kyt.olcum, this.osilo.veri);\n", "",
     "ESKI KUSURU geri koyar: arsiv kaydinda olcum satiri yok"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (o.f > 0 && Number.isFinite(o.duty)) l.push({ ad: 'Duty'",
     "      if (o.f > 0) l.push({ ad: 'Duty'",
     "kisa M satirinda undefined.toFixed: skop gorunumu komple kaybolur"),

    # ── B44 · kuplaj deneyi komutu (`tK`) guvenli
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  return p == 1 || p == 2 || p == PIN_SDA",
     "  return p == 1 || p == 6 || p == PIN_SDA",
     "EMNIYET: PIL KAPISI MOSFET'i (GPIO6) tiklatilabilir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "(p >= 39 && p <= 42);", "(p >= 33 && p <= 42);",
     "oktal PSRAM pinleri (33-37) tiklatilabilir — kart coker"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  if (i2c && kuplaj_hazir) Wire.begin(PIN_SDA, PIN_SCL, 400000);\n", "",
     "deneyden sonra I2C geri kurulmaz: ADS'ler kalici okunamaz"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    if (kuplaj_aktif) kuplaj_patlat();       /* B44 deneyi — yalnizca `tK` */\n", "",
     "tiklatma yakalama sirasinda yapilmaz: deney bos sonuc verir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "      gpio_set_drive_capability((gpio_num_t)p, GPIO_DRIVE_CAP_DEFAULT);\n", "",
     "zayif surus deneyden sonra I2C pinlerinde kalir"),

    # ── B43 · olcum satiri eksenle ayni kalibrasyonda, WiFi'de de var
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        if (sonuc == SKOP_SONUC_OK) {\n            SkopOlcum &m = skop_dokum_m;",
     "        if (sonuc == SKOP_SONUC_OK && is != SKOP_IS_IKILI) {\n            SkopOlcum &m = skop_dokum_m;",
     "ESKI KUSURU geri koyar: WiFi (ikili) yakalamalarinda olcum yapilmaz"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "            skop_olc_kalibre(&m);",
     "            skop_olc(skop_veri, skop_adet, skop_volt_adim(), (float)skop_hz, &m);",
     "ESKI KUSURU geri koyar: olcum satiri dogrusal modelden, eksenden 7 V sapar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    m->vmax = kal_mv((float)hmax) * mv_v;",
     "    m->vmax = (float)hmax * skop_volt_adim();",
     "Vmax dogrusal: tepe degeri izgarayla celisir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    double top = 0.0, kare = 0.0;", "    float top = 0.0f, kare = 0.0f;",
     "float32 toplam: ~65 V ortalamanin yaninda gurultu Vac'i yuvarlamada kaybolur"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    skop_olc(skop_gecici, n, skop_volt_adim(), (float)skop_hz, m);",
     "    skop_olc(skop_veri, n, skop_volt_adim(), (float)skop_hz, m);",
     "zaman esikleri ham kodda: duty/tr/tf eksenin orta seviyesinde olcülmez"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        if (mn > 0) Serial.write((const uint8_t *)mb, (size_t)mn);\n", "",
     "ikili yolda M satiri basilmaz: WiFi'de olcum yine yok"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        olcum: this.skopArsivtenAciliyor ? null : this.skopIkiliOlcum,",
     "        olcum: null,",
     "ESKI KUSURU geri koyar: ikili cozucu olcumu atar, WiFi'de satir cikmaz"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        olcum: this.skopArsivtenAciliyor ? null : this.skopIkiliOlcum,",
     "        olcum: this.skopIkiliOlcum,",
     "arsivden acilan kayda bekleyen (baska dalganin) olcumu yapisir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      this.skopIkiliOlcum = null;\n      /* DataView", "      /* DataView",
     "olcum tek kullanimlik degil: sonraki kayda eski olcum yapisir"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "      if (this.skopIkiliBekle && satir[0] === 'M' && satir[1] === ' ') {",
     "      if (false) {",
     "onaydan once gelen M satiri tutulmaz"),
    ("B7", "test_arayuz3.js", "arayuz3/app.js",
     "        this.osiloBekliyor = false; this.skopIkiliBekle = false; this.skopIkiliOlcum = null;",
     "        this.osiloBekliyor = false; this.skopIkiliBekle = false;",
     "`!` ile iptal edilen yakalamanin olcumu sonraki kayda yapisir"),

    # ── B42 · tetik ornegi on-tetik ayarinin yerinde
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "            if (bulundu && kalan == 0u) break;\n"
     "            adc_digi_output_data_t *o = (adc_digi_output_data_t *)&cerceve[b];",
     "            adc_digi_output_data_t *o = (adc_digi_output_data_t *)&cerceve[b];",
     "ESKI KUSURU geri koyar: cerceve kuyrugu on-tetik gecmisini ve tetik "
     "orneginin kendisini ezer"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "            if (bulundu && kalan == 0u) break;\n"
     "            adc_digi_output_data_t *o = (adc_digi_output_data_t *)&cerceve[b];\n"
     "            if (o->type2.channel != SKOP_KANAL) continue;\n"
     "            uint16_t v = o->type2.data;\n"
     "\n"
     "            skop_veri[w] = v;\n",
     "            adc_digi_output_data_t *o = (adc_digi_output_data_t *)&cerceve[b];\n"
     "            if (o->type2.channel != SKOP_KANAL) continue;\n"
     "            uint16_t v = o->type2.data;\n"
     "\n"
     "            skop_veri[w] = v;\n"
     "            if (bulundu && kalan == 0u) break;\n",
     "bekci YAZMADAN SONRA: sayac bittikten sonra bir ornek daha halkaya "
     "girer, tetik bir kayar (varlik degil SIRA sinaniyor mu)"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "                } else if (dolu > on) {", "                } else if (dolu >= on) {",
     "tetikten once on-1 ornek: halka bir eksik dolar, tetik on-1'e duser"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "kalan = (uint16_t)(sonra - 1u);", "kalan = sonra;",
     "tetikten sonra bir fazla ornek: tetik on-1'e kayar"),

    # ── B41 · yakalama surerken ADS susuyor (I2C kenarlari ADC'ye hata sokuyor)
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  if (skop_is != SKOP_IS_YOK) {\n    if (!ads_duraklama_bas_ms)",
     "  if (false) {\n    if (!ads_duraklama_bas_ms)",
     "ESKI KUSURU geri koyar (B40b): ADS yakalamayla eszamanli calisir, I2C "
     "kenarlari skop orneklerine igne ve sahte tetik sokar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    ads_duraklama_top_ms += millis() - ads_duraklama_bas_ms;", "",
     "ADS susmasi sayilmaz: enerji/pil araligi sessizce kayar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    if (pil_testi_suruyor()) {", "    if (false) {",
     "EMNIYET: pil testi surerken yakalama ADS'yi susturur, kesme denetimi durur"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        if (skop_is != SKOP_IS_YOK) {\n          Serial.println(F(\"! pil: skop",
     "        if (false) {\n          Serial.println(F(\"! pil: skop",
     "yakalama surerken pil testi baslar ve ilk araligi ADS'siz gecirir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        if (pil.durum == PIL_CALISIYOR) {\n          pil_durdur(PIL_DURDURULDU, PILH_YOK);",
     "        if (skop_is != SKOP_IS_YOK) break;\n        if (pil.durum == PIL_CALISIYOR) {\n          pil_durdur(PIL_DURDURULDU, PILH_YOK);",
     "EMNIYET: p0 (DURDUR) skop yakalamasi bitene kadar gecikir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    if (skop_ayar.kip == SKOP_KIP_OTO) azami_ms = taban_ms;", "",
     "OTO kipte tetik yokken 4 s beklenir (200 ms/bol'de 4.08 s)"),

    # ── B40 · skop olcum cekirdegini bloklamiyor
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        if (skop_ayar.kip != SKOP_KIP_OTO) { skop_kilidi_birak(); return SKOP_SONUC_TETIK_YOK; }",
     "        if (skop_ayar.kip != SKOP_KIP_OTO) { return SKOP_SONUC_TETIK_YOK; }",
     "ESKI KUSURU geri koyar: Normal kipte tetiklenmeyince kilit birakilmaz, "
     "skop yeniden baslatmaya kadar olu (kartta goruldu)"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    if (!skop_hiz_ayarla(hz)) { skop_kilidi_birak(); return SKOP_SONUC_HATA; }",
     "    if (!skop_hiz_ayarla(hz)) { skop_kilidi_birak(); return SKOP_SONUC_HATA; }\n"
     "    Serial.println(F(\"skop basladi\"));",
     "yakalama (cekirdek 0) yazdirirsa WebAkis satir birlestirmesi iki "
     "cekirdekten beslenir ve D/skop satirlari karakter duzeyinde karisir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  skop_sonuc_isle();         // B40b: yakalama gorevinin sonucu",
     "",
     "sonuc hic islenmez: `t` sessizce hicbir sey dondurmez, skop_is hep dolu kalir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        if (Serial.availableForWrite() < n + SKOP_DOKUM_PAY) return;  /* sonraki tura */",
     "",
     "dokum TX payini gozetmez: halka dolunca D satirlari ve dokumun kendisi "
     "yine olcum dongusunu bloklar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "      if (alt != '?' && skop_is != SKOP_IS_YOK) {",
     "      if (false) {",
     "is surerken `tb`/`tl`/`ta` skop_ayar'i degistirir; gorev yari eski yari "
     "yeni ayarla yakalar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "  uint32_t tdiv = SKOP_TDIV_US[skop_son_tdiv];     /* B40b: yakalamanin ayari */",
     "  uint32_t tdiv = SKOP_TDIV_US[skop_ayar.tdiv];",
     "/skop.bin yakalamadan sonra degisen zaman tabaniyla etiketlenir"),

    # ── B39 · hizli yol kalibre + cekme sinamasi bedeli
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        float vd = kal_tab_var ? kal_mv(hizli_v[n]) / 1000.0f : hizli_v[n] * lsb;",
     "        float vd = hizli_v[n] * lsb;",
     "gerilim kanali ESKI dogrusal modele doner: sifir giriste -6.93 V "
     "ofset, P ve PF yanlis"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "        Serial.print(':');  Serial.print(kal_mv_tab[k]);",
     "        Serial.print(':');  { int mv_ = -1; adc_cali_raw_to_voltage("
     "skop_cali, kal_dugum_kod(k), &mv_); Serial.print(mv_); }",
     "`CT` eFuse'u yeniden sorgular: arayuzun tablosu ile kartin olcekledigi "
     "tablo IKI AYRI temsil olur"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    Serial.println(kal_tab_var ? 1 : 0);", "    Serial.println(1);",
     "`W` her zaman 'kalibre' der — tablo kurulamasa bile"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "#define CEKME_BEKLE_MS 8u", "#define CEKME_BEKLE_MS 3u",
     "3 ms'de kaynaksiz 100 nF dugum %56 kayar ve 'surulu' sayilir (olculdu)"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "                if (nv < CEKME_ORNEK) { vt += s->type2.data; nv++; }",
     "                if (nv < CEKME_ORNEK) { hizli_v[nv] = s->type2.data; "
     "vt += s->type2.data; nv++; }",
     "cekme okuyucusu asil yakalamanin dizisine yazar: sinama sonradan "
     "yapildigi icin olculen dalga CEKILMIS dugumun degerleriyle bozulur"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     '        Serial.println(F("! hizli yol: baslatilamadi"));\n        return;\n    }\n\n    uint16_t nv = 0, ni = 0;',
     '        Serial.println(F("! hizli yol: baslatilamadi"));\n        return;\n    }\n'
     '    { float a_ = 0, b_ = 0; hizli_cekme_kaymasi(&a_, &b_, CEKME_BEKLE_MS); }\n'
     '\n    uint16_t nv = 0, ni = 0;',
     "cekme sinamasi asil yakalamadan ONCE: dugumde kalan cekme yuku "
     "olcume girer"),

    # ── B38 · GPIO5 karakterizasyonu — kayitli olcum zincirde
    ("B19", "sim3_skop.py", "uretim/tezgah_adc_supur.py",
     '        ok("[!] GPIO5\'in egriligi GPIO4\'unkiyle ayni (rms +-%15)",\n'
     '           abs(r5 - r4) <= 0.15 * r4,',
     '        ok("[!] GPIO5\'in egriligi GPIO4\'unkiyle ayni (rms +-%15)",\n'
     '           abs(r5 - r4) <= 0.15 * r4 - 100,',
     "GPIO5'in egriligi GPIO4'unkinden farkli cikarsa B36'nin eFuse "
     "duzeltmesi hizli AKIM kanalina TASINAMAZ; iddia bunu yakalamali"),
    ("B19", "sim3_skop.py", "uretim/tezgah_adc_supur.py",
     "           abs(eg) < 0.005,", "           abs(eg) < 0.0005,",
     "okuma yollari arasi kazanc esigi olculen %0.141'in ALTINA inerse "
     "iddia kirmiziya donmeli — esik olcumu gercekten sinıyor mu"),
    ("B19", "sim3_skop.py", "uretim/olcum-adc-supurme.csv",
     "gorev_promil,", "gorev_promilX,",
     "kayitli olcum okunamaz hale gelirse zincir SESSIZCE gecmemeli"),

    # ── B37 · bos pin kapisi (cekme sinamasi)
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "                return;   /* B37: W BASILMAZ */",
     "                /* return; */",
     "ESKI KUSURU geri koyar: bos giriste `w` yine 7.68 W / PF 0.98 basar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "#define BOS_PIN_ESIK_KOD (SKOP_ADC_SAYIM * 0.75f)",
     "#define BOS_PIN_ESIK_KOD (SKOP_ADC_SAYIM * 0.5f)",
     "esik %50: surulu RC duzenegi (%90 gorevde 2054 kod) BOS sayilir; "
     "surulu bir giris reddedilir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    adc_durdur();\n    gpio_set_pull_mode((gpio_num_t)PIN_SKOP,    kip);",
     "    gpio_set_pull_mode((gpio_num_t)PIN_SKOP,    kip);",
     "DMA halkasi sifirlanmaz: cekme degismeden onceki bayat ornekler "
     "okunur, surulu pinin kaymasi isaret degistirir (kartta olculdu)"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "static bool skop_calisiyor = false;", "static bool skop_calisiyor_ = false;",
     "surucu durumu izlenmez; her `w`de uc satir 'already stopped' gurultusu"),

    # ── B36 · kalibrasyon tablosu + hizli kanal ham kodu
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     'Serial.print(F(" oran="));    Serial.print(SKOP_ORAN, 6);', "",
     "tablo `oran`siz gider; arayuz cevrim carpanini kendi sabitinden "
     "turetmek zorunda kalir ve VREF bir gun kalibre edilince eksen "
     "SESSIZCE kayar"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     'Serial.println(F("CT 0 kaynak=YOK"));', "Serial.println(F(\"CT 0\"));",
     "kalibrasyon yokken sebep soylenmez; arayuz duzeltmesiz cizer ve "
     "kullanici ekseni 'kalibre' sanir"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "static void hizli_ham_yolla", "static void hizli_ham_yolla_",
     "GPIO5'in ham kodunu disari veren TEK yol kaybolur; hizli AKIM "
     "kanali olculemez ve guc faktorunun baska kaynagi yok"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    /* `hizli_olcekle` CAGRILMIYOR",
     "    hizli_olcekle(nv);  /* `hizli_olcekle` CAGRILMIYOR",
     "`wR` ham kod yerine OLCEKLENMIS deger basar: dogrusallik supurmesi "
     "kendi duzeltmesini olcmus olur, yani hicbir sey olcmez"),

    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    uint32_t taban_ms = (uint32_t)(pencere_ms * 1.2f) + 300u;\n"
     "    if (azami_ms < taban_ms) azami_ms = taban_ms;",
     "",
     "4 s tavani geri gelir: en yavas kademe (5 s pencere) ASLA "
     "tamamlanmaz, OTO kipi kisa kaydi SESSIZCE dondurur ve secilen "
     "zaman tabani yalan olur (kartta 3055 beklenirken 2304 geldi)"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    100, 200, 500, 1000, 2000, 5000,",
     "    100, 200, 500, 1000, 2000, 4000,",
     "tablo degisince model de degismeli — iddia firmware'in KENDI "
     "tablosundan turetiliyor, elle yazilmiyor"),

    # ── B34 · ADC kalibrasyonu (kartta olculdu)
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    c.atten    = ADC_ATTEN_DB_12;", "    c.atten    = ADC_ATTEN_DB_6;",
     "kalibrasyon atteni surekli kipinkinden farkli olursa AYNI ham kod "
     "baska bir gerilime cevrilir ve hata SESSIZ olur"),
    ("B19", "sim3_skop.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "    skop_cali_var = (adc_cali_create_scheme_curve_fitting(&c, &skop_cali) == ESP_OK);",
     "    skop_cali_var = false;",
     "kalibrasyon hic kurulmazsa `c` komutu ham kodu sabitle carpip "
     "'olculmus' gibi gosterir — olculen 4 kat iyilesme kaybolur"),

    # ── B26 · RDY kenar yonu (GERCEK KARTTA olculdu)
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "while (digitalRead(PIN_HAZIR) == LOW) {        /* yeni donusum basladi mi */",
     "while (digitalRead(PIN_HAZIR) == HIGH) {       /* yeni donusum basladi mi */",
     "ESKI KUSURU geri koyar: once dusmeyi bekleyince ikinci dongu "
     "(kalkmayi bekleyen) HIC bitmez, her tur 4000 us zaman asimina "
     "duser. Kartta olculdu: 6.17 ms/tur, 162 ornek/s — hedefin 1/4'u"),

    # ── B4/B5 · platform bagimsizligi (B25'te bulunan kapsam bosluğu:
    #    mutasyon tablosunda olcum3.h'ye ait TEK kayit yoktu)
    ("B4", "test_olcum3.py", "kod/olcum-karti-a3/olcum3.h",
     "return (float)pJ / 1.0e12f;", "return (float)((double)pJ / 1.0e12);",
     "olcum3.h'de `double` YASAK: AVR'de 32 bit, Xtensa'da 64 bit. "
     "Geri konursa emulator ile kart ayni aritmetigi kosturmaz ve "
     "adimin 'kodun ta kendisi' iddiasi YANLIS olur"),

    # ── B17 · es zamanlilik
    ("B17", "sim3_senkron.py", "kod/olcum-karti-a3/tipler3.h",
     "float    faz_kal_us[2];", "float    faz_kal[2];",
     "faz kalibrasyonu ORNEK degil MIKROSANIYE cinsinden olmali "
     "(B22.1'in K2 duzeltmesi)"),

    # ── B21 · pil testi
    ("B21", "sim3_pil.py", "kod/olcum-karti-a3/pil_test.h",
     "#define PIL_AZAMI_V", "#define PIL_AZAMI_V_",
     "pil gerilim tavani yoksa sinir disi pil kabul edilir"),

    # ── B3 · sema YENIDEN URETILEBILIR mi (B25'te bulundu)
    ("B3s", "netlist3_dogrula.py", "uretim/sema_uret_ortak.py",
     'return str(uuid.uuid5(_AD_ALANI, f"olcum-karti/{_SAYAC}"))',
     "return str(uuid.uuid4())",
     "sema UUID'leri belirlenimli olmali; uuid4 geri gelirse .kicad_sch "
     "ve netlist HER kosuda degisir, 858 satirlik anlamsiz diff verir "
     "ve gercek bir tasarim degisikligini bogar"),

    # ── B3 · sema (B23.3'te bulunan delik)
    ("B3", "dogrula3.py", "uretim/sema3-uret.py",
     'print(f"yazildi: {hedef}")', "raise SystemExit(1)",
     "sema uretimi cokerse ERC ve netlist BAYAT dosyalari okur; "
     "dogrula3.py bunu B23.3'e kadar goremiyordu"),

    # ── B23.1 · tezgah toplayicisinin kendisi
    ("B23", "dogrula3.py", "uretim/netlist3_dogrula.py",
     'tezgah("B3 Sema"', 'if False: tezgah("B3 Sema"',
     "bir adim tezgah kalemi basmayi birakirsa toplayici KIRMIZI "
     "donmeli — adim kendi basina yesil kalsa bile"),

    # ── B48 · delikli plaket yerlesimi (bakir ↔ netlist, geometriden)
    # Denetim tel etiketlerini DEGIL geometriyi okuyor; bu mutasyonlar
    # VERIYI bozuyor ve geometrik denetimin isirdigini olcuyor. Bacak
    # sirasi tablosunun (BACAK) fiziksel dogrulugu ise burada SINANAMAZ —
    # o, tezgah kalemi (multimetre).
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     '"C15":   ("A", "C1", 26, 14, 180, 2),', '"C15":   ("A", "C1", 26, 14, 0, 2),',
     "parca 180 derece ters takilirsa (+3V3 ve GND bacaklari yer degisir) "
     "bakir netlistle ayrisir: kisa devre ya da baska bacakla ayni delik"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     '"R41":   ("A", "R4", 29, 25, 0, 1),', '"R41":   ("A", "R4", 29, 25, 0, 0),',
     "parca kendi aglarinin izlerinden ONCEKI adimda takilirsa o adimda "
     "kart ACIK kalir — 'her kurulum adiminda tam bagli' iddiasi"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     'KELVIN = [("R18.1", "T_SP.1"), ("R19.1", "T_SN.1")]',
     'KELVIN = [("R18.1", "T_SN.1"), ("R19.1", "T_SP.1")]',
     "Kelvin uclari capraz baglanirsa (S+ alt, S- ust) sont algilamasi ters "
     "isaretli ve GND'ye kisa olur"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     '("X:RS.2", "A:T_YILDIZ", "yildiz", 3,', '("X:RS.2", "A:T_YILDIZ", "kelvin", 3,',
     "kart topragi guc yoluna 'yildiz' diye isaretli TEK kablodan gitmeli; "
     "ikinci bir toprak yolu sont dususunu olcume sokar"),
    ("B48", "yerlesim3.py", "uretim/tasarim3_sabit.py",
     "DELIKLI_PAD_ETKIN_MM = 1.54", "DELIKLI_PAD_ETKIN_MM = 4.0",
     "ped capi buyudukce bakirdan bakira aralik kuculur; HV kartinda "
     "411 V'luk cift 4.11 mm'nin altina dusunce kacak yolu KIRMIZI olmali"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_teller.json",
     '{"tur": "iz", "adim": 5, "ag": "Net-(R11-Pad2)", "yol": [[13, 10], [13, 9], [13, 8], [13, 7]]}',
     '{"tur": "iz", "adim": 5, "ag": "Net-(R11-Pad2)", "yol": [[13, 10], [13, 9], [13, 8]]}',
     "HV zincirinde bir iz bir delik kisa kalirsa R11-R12 dugumu ACIK: "
     "etiket hala dogru, geometri yalan soylemiyor"),
    # ── B48b · alt adimlar (LEGO sirasi) — her mutasyon bolum 9'daki BIR
    #    iddiayi yalanliyor. Uretici bozuluyor; denetimin olcutu (yukseklik_mm,
    #    yonlu, delik sahipligi, V.ALT_ADIM_SINIR) ureticiden bagimsiz.
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     "        for i in range(0, len(tp), GRUP_PARCA):",
     "        for i in range(0, len(tp) - 1, GRUP_PARCA):",
     "9a: tek parcali turler (U9, J5, R30...) hicbir alt adima girmezse "
     "kullanici o parcayi hic takmaz — 'her parca TAM BIR alt adimda'"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     "GRUP_PARCA = 4", "GRUP_PARCA = 9",
     "9b: uretici 6 direnci tek alt adima yigarsa 'her sey bir adimda "
     "olmasin' ilkesi bozulur — sinir V.ALT_ADIM_SINIR'dan, ureticiden degil"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     'KART_TURLERI = ("parca", "iz", "tel")', 'KART_TURLERI = ("iz", "parca", "tel")',
     "9c: izler parcalardan once cekilirse lehim henuz takilmamis parcanin "
     "deligini doldurur ve bacak girmez"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     'SIRA = ["D3", "R4", "R5",', 'SIRA = ["D3", "CE", "R4", "R5",',
     "9d: elektrolitik dirençten once takilirsa alcak parcanin bacaklarina "
     "erisim kapanir — yukseklik ayak izinin yukseklik_mm'sinden"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     "    return not (_yonlu(a[0]) or _yonlu(b[0])) and len(a) + len(b) <= GRUP_PARCA",
     "    return len(a) + len(b) <= GRUP_PARCA",
     "9e: kutuplu parca (C16/C17) baska turle ayni alt adima karisirsa "
     "yon uyarisi kaybolur — ters takma riski"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     "ped = [p.ref for p in pedler if p.ref in uclar and p.ref not in atanan]",
     "ped = [p.ref for p in pedler if p.ref not in uclar and p.ref not in atanan]",
     "9f: kablo, ucundaki lehim noktasi yokken baglanmaya kalkilirsa "
     "(ped sonraki alt adimda) sira fiziksel olarak imkansiz"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     'SON_TURLER = ("kablo", "kontrol")', 'SON_TURLER = ("kontrol", "kablo")',
     "9g: KAPI kontrolunden SONRA kablo takiliyorsa kapi yarim karti olcer "
     "— 'her adim KAPI ile biter'"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_adim.py",
     "                if j5:", "                if False:",
     "9h: 'ESP32'yi J5'e bagla' alt adimi yoksa kullanici Adim 1 KAPI'sinda "
     "beslemesiz karti olcer (B48b'ye kadar boyleydi)"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     '"R20", "R23", "R27", "R28", "R29", "R30"},', '"R23", "R27", "R28", "R29", "R30"},',
     "10: skop bolucusunun ust direnci (R20) 'metal film zorunlu' listesinden "
     "duserse belge onu karbon diye gosterir — topolojiden turetilen kume yakalar"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     '"onerilir": {"R2", "R3",', '"onerilir": {"R4", "R2", "R3",',
     "10: bir direnc iki turde birden olursa belge celisir — 'her direnc TEK turde'"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     '"multilayer seramik": {"C2", "C3", "C9",', '"multilayer seramik": {"C3", "C9",',
     "10b: C2 tipsiz kalirsa belge onu gostermez; ayrica C2/C3 RC suzgec cifti "
     "artik ayni tipte degil — 'her kondansator TEK tipte' + 'RC cifti ayni tip'"),
    ("B48", "yerlesim3.py", "uretim/yerlesim3_veri.py",
     '"seramik disk (mercimek)": {"C1", "C4",', '"seramik disk (mercimek)": {"C1", "C2", "C4",',
     "10b: C2 hem disk hem multilayer yazilirsa kullanici disk takabilir — "
     "V/I eslesmesi toleransa bagli (B16)"),
]


def kopyala(hedef: Path) -> Path:
    def gormezden(dizin, adlar):
        return [a for a in adlar
                if a in ATLA or a in ATLA_DOSYA
                or a.endswith((".pyc", ".elf", ".rpt"))]
    # 🔴 B26: hedef VARSA once sil. Dizin adi PID'den turuyor ve Windows
    #   PID'leri geri donusturuyor; olduruLen ya da coken bir onceki kosunun
    #   kalintisi ayni adi alinca `copytree` FileExistsError ile cokuyordu.
    #   Bir oturumda IKI KEZ tetiklendi. Kalinti bizim yazdigimiz gecici bir
    #   kopya, silmek guvenli.
    # ⚠ B30: `ignore_errors=True` SESSIZCE basarisiz olabiliyor — Windows'ta
    #   Defender/dizinleyici kalintiyi kilitlediginde dizin DURUYOR ve bir
    #   sonraki `copytree` FileExistsError ile cokuyor (bu oturumda oldu).
    #   Once birkac kez dene; yine silinemezse BENZERSIZ ada kac. Kalinti
    #   bizim gecici kopyamiz, birakmak zararsiz — kosuyu bolmek degil.
    for _ in range(5):
        if not hedef.exists():
            break
        shutil.rmtree(hedef, ignore_errors=True)
        if hedef.exists():
            time.sleep(0.3)
    if hedef.exists():
        n = 1
        while (KOK.parent / f"{hedef.name}-{n}").exists():
            n += 1
        hedef = KOK.parent / f"{hedef.name}-{n}"
    shutil.copytree(KOK, hedef, ignore=gormezden)
    return hedef


def kosut(kopya: Path, betik: str) -> tuple[int, str]:
    # B27: `.js` betikleri (test_arayuz3.js — B7, 132 iddia) node ile.
    # Onceden yalnizca Python kosuyordu, yani arayuz iddialarinin HICBIRI
    # mutasyonla sinanmiyordu — "olmayan iddia gorunmezdir" sinifinin
    # koca bir dosyalik ornegi.
    calistirici = ["node"] if betik.endswith(".js") else [sys.executable]
    r = subprocess.run(calistirici + [betik], cwd=kopya / "uretim",
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    return r.returncode, r.stdout + r.stderr


def uygula(kopya: Path, dosya: str, eski: str, yeni: str) -> bool:
    p = kopya / dosya
    if not p.exists():
        return False
    s = p.read_text(encoding="utf-8", errors="replace")
    if eski not in s:
        return False
    # ⚠ WINDOWS: yeni kopyalanan agaci Defender/arama dizinleyicisi
    #   tararken dosya KISA SURELI kilitli kalabiliyor ve yazma
    #   PermissionError atiyor. Kosu tam ortasinda cokuyordu (B28'de iki
    #   kez). Kusur mutasyonda degil ortamda; birkac kez denemek yeter.
    for deneme in range(5):
        try:
            p.write_text(s.replace(eski, yeni), encoding="utf-8")
            break
        except PermissionError:
            if deneme == 4:
                raise
            time.sleep(0.3)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adim", help="yalnizca bu adimin mutasyonlari")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()

    if a.adim:
        secili = [m for m in MUTASYONLAR if m[0].lower() == a.adim.lower()]
    else:
        secili = [m for m in MUTASYONLAR if m[0] not in AGIR]
    if not a.adim and any(m[0] in AGIR for m in MUTASYONLAR):
        print(f"  (atlandi: {', '.join(sorted(AGIR))} — tam zincir "
              f"kosturuyor, --adim ile calistirin)")
    if not secili:
        adlar = sorted({m[0] for m in MUTASYONLAR})
        print(f"  '{a.adim}' icin mutasyon yok. Var olanlar: "
              f"{', '.join(adlar)}")
        return 1

    print("=" * 78)
    print(f"  MUTASYON KOSUCUSU — {len(secili)} mutasyon")
    print("=" * 78)
    if a.liste:
        for adim, betik, dosya, eski, _y, neden in secili:
            print(f"  {adim:5} {betik:22} {dosya}")
            print(f"        {eski}  ->  bozuluyor")
            print(f"        {neden}")
        return 0

    kopya = KOK.parent / f"_mutasyon-{os.getpid()}"
    kacan, uygulanamayan = [], []
    try:
        print(f"  kopya: {kopya}")
        t0 = time.time()
        kopya = kopyala(kopya)
        print(f"  kopyalandi ({time.time() - t0:.1f} s)")

        # Once TEMIZ taban: mutasyonsuz kosu gercekten yesil mi?
        taban = {}
        for betik in sorted({m[1] for m in secili}):
            rc, cikti = kosut(kopya, betik)
            taban[betik] = (rc, sayim.sayimlar(cikti))
            print(f"  taban {betik:24} rc={rc} {taban[betik][1]}")
            if rc != 0:
                print(f"  KIRMIZI: {betik} mutasyonsuz da KALIYOR — "
                      f"once onu duzelt. Kopyadaki cikti:")
                # Yalnizca ozet satiri basmak yetmiyordu: taban kirmizi
                # olunca NEDENI gorunmuyordu ve tanilamak icin kopyayi
                # elle kurmak gerekti.
                ilginc = [x for x in cikti.splitlines()
                          if ("KALDI" in x and "[OK]" not in x)
                          or "KIRMIZI" in x or "Traceback" in x
                          or x.strip().startswith("[!!]")]
                for x in ilginc[-25:]:
                    print("      " + x.rstrip()[:110])
                if not ilginc:
                    for x in cikti.rstrip().splitlines()[-15:]:
                        print("      " + x.rstrip()[:110])
                return 1

        for i, (adim, betik, dosya, eski, yeni, neden) in enumerate(secili, 1):
            shutil.rmtree(kopya, ignore_errors=True)
            kopya = kopyala(kopya)
            print()
            print(f"  [{i}/{len(secili)}] {adim} · {dosya}")
            print(f"        {eski}  ->  {yeni}")
            if not uygula(kopya, dosya, eski, yeni):
                print(f"        ATLANDI: desen bulunamadi (kod degisti mi?)")
                uygulanamayan.append((adim, dosya, eski))
                continue
            rc, cikti = kosut(kopya, betik)
            simdi = sayim.sayimlar(cikti)
            yakalandi = rc != 0 or simdi != taban[betik][1]
            print(f"        rc={rc} sayim={simdi} "
                  f"-> {'YAKALANDI' if yakalandi else 'KACTI'}")
            if not yakalandi:
                print(f"        !! {neden}")
                kacan.append((adim, dosya, eski, neden))
    finally:
        shutil.rmtree(kopya, ignore_errors=True)

    print()
    print("=" * 78)
    if uygulanamayan:
        print(f"  {len(uygulanamayan)} mutasyon UYGULANAMADI (desen yok):")
        for adim, dosya, eski in uygulanamayan:
            print(f"    * {adim} {dosya}: {eski}")
    if kacan:
        print(f"  {len(kacan)} MUTASYON KACTI — o iddialar bos:")
        for adim, dosya, eski, neden in kacan:
            print(f"    * {adim} {dosya}: {eski}")
            print(f"      {neden}")
        return 1
    if uygulanamayan:
        return 1
    print(f"  {len(secili)} mutasyonun hepsi YAKALANDI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
