# -*- coding: utf-8 -*-
"""Asama 3 (cift yonlu on uc, +-615 V) — dogrulama zinciri.

    python dogrula3.py

  B1  On uc tasarimi ve hata butcesi        (hesap + kural)
      Cift yonlu topoloji, iki gerilim kanali, direnc gerilim stresi,
      PGA'ya bagli kazanc hatasi, tampon secimi, kelepce, gurultu
      butcesi (DEVIR 1.3'un acik sorusu), Lagrange hizalayici.
  B2  Analog on uc — NEGATIF DAHIL tarama    (ngspice)
      Asama 2'nin A2 adimi yalnizca `dc Vin 0 300` yapiyordu; negatif
      taraf hic simule edilmemisti. B2 bunu kapatiyor. Ayrica kelepce
      karsilastirmasi ve iki ayri ortusme suzgeci.
  B15 Ariza ve zorlama simulasyonu           (ngspice + kural)
      B2 yalnizca IKI ariza senaryosu kapsiyordu. B15 20'nin uzerinde
      senaryoyu sayisallastiriyor: ters akim, ters gerilim, asiri
      gerilim, sebeke, besleme arizasi, bilesen arizasi, izolasyon.
      Her senaryo icin kacan akim, dugum gerilimi, asilan mutlak sinir
      ve OLEN PARCA. Kabul olcutu: hicbir TEK ariza ESP32'yi ya da
      PC'yi oldurmemeli. Op-amp makromodeli (doyma + akim siniri +
      giris jonksiyonu) BOLUM 1'de kendisi dogrulaniyor.
  B3  Sema: uretim + ERC + netlist polarite  (kicad-cli)
      ERC "bagli mi" der, "dogru mu" demez. Netlist denetimi bolucu
      altlarinin GND'ye DEGIL VREF'e gittigini, diferansiyel ciftleri,
      kelepce polaritesini ve Sallen-Key topolojisini tek tek okur.
  B4/B5  Olcum matematigi                    (avr-gcc + emulator)
      olcum3.h GERCEK KODU, bit-birebir dogrulanmis AVR emulatorunde:
      cift yonlu okuma, kalibrasyon, isaretli enerji ve Lagrange
      hizalayicinin reaktif yukteki etkisi.
  B6  Firmware: derleme + ikilide olu kod    (arduino-cli)
      Gercek ESP32-S3 derleyicisi, 0 uyari, her komut dalinin ikilide
      gercekten durdugu denetimi.
  B11 +-12 V rayi                            (hesap + veri sayfasi)
      Tek 24 V kaynaktan +-12 V. DEVIR 5.12.23'un "LM358 orta nokta
      tamponu" plani B15 tarafindan iki yerden kirilmisti (cekme akimi
      ve kapasitif yuk). Yerine 7912 orta nokta REGULATORU: stokta var,
      cekme akimi 100 kat fazla, kapasitif yuku zaten istiyor, ic akim
      siniri + termal kapatma tasiyor.
  B16 V/I suzgec eslestirmesi                (hesap + kural)
      Wattmetre gucu V x I; iki kanal ayni sinyali FARKLI suzuyordu
      (55.7 Hz'e karsi 7958 Hz). Iki sonucu vardi: akim kanali ADS'in
      430 Hz Nyquist'inin cok ustunde suzuldugu icin ORTUSUYORDU
      (geri donusu yok), ve REAKTIF yukte guc hatasi devasaydi
      (PF=0.5'te %155). Direncli yukte fark kendini goturdugu icin
      gozden kacmisti. Suzgec ADS'in kendi koluna tasindi
      (C4 100nF -> 1nF, yeni C18+C19+C20 = 1.32 uF). Bolum 4
      kondansator TOLERANSININ artik baskin hata oldugunu ve firmware
      faz kalibrasyonunun gereklilik oldugunu sayisallastiriyor.
  B18 GPIO kelepceleri ve +3V3 geri beslemesi (ngspice + kural)
      B15/B1: +-12 V acikken +3V3 kapaliysa (USB cikarilmis ama 24 V
      takili — "izolasyon icin USB'yi cikar" talimatinin ya da sadece
      acma sirasinin dogal sonucu) BAT85 kelepceleri olu 3V3 rayini
      3.582 V'a suruyordu; ESP32 besleme pini siniri 3.60 V, pay 18 mV.
      B15 cozum olarak F6'yi (kelepceler TL431 rayina) onermisti ve
      kullanici onaylamisti. B18 uygulamadan ONCE olctu: F6 hizli akim
      yolunun tam olcegini de %43 kesiyor ve TL431 kalintisini
      kapatmiyor. Yerine iki stok direnci: R26/R33 2.7K -> 10K ve
      R41 (1K) bosaltma. Pay 1930 mV, TL431'den BAGIMSIZ, menzillerde
      hicbir kayip yok. Ayrica seri direncin ADC tarafindaki uc bedeli
      (sizinti, oturma, gurultu) ayri ayri olculuyor.
  B19 Osiloskop kanali CIFT YONLU            (ngspice + kural)
      ESP32'nin ADC'si eksi okumadigi icin skop kanali 0..45.5 V TEK
      YONLUYDU. Bolucunun alt ucu GND yerine VREF'e baglandi (gerilim
      kanallarinin zaten kullandigi cozum) ve R23 6.8K -> 2.7K yapildi:
      -63.5 .. +46.8 V. Bedeli cozunurluk (11.9 -> 28.8 mV, ikisi de
      NOMINAL tam olcekten). Yeni akim
      yolu (skop akimi artik VREF'e gidiyor) normalde ve 615 V arizasinda
      olculuyor: VREF kaymiyor. Ayrica ayni sayinin dort dosyada
      (sabitler, sema, firmware, arayuz) ayrismadigi denetleniyor.
  B17 ADS yolunda ES ZAMANLILIK              (kural + firmware denetimi)
      B16'nin birakti uc firmware kalemi ele alinirken cok daha buyuk
      bir kusur cikti: iki ADS1115 de SUREKLI kipte, her biri KENDI ic
      osilatoruyla kosuyordu ve dongu yalnizca AKIM cipini bekliyordu.
      Gerilim ornegi 0..1.29 ms ESKI oluyordu ve osilator toleransi
      ±%10 oldugu icin bu SURUKLENIYORDU — 50 Hz'te 0..23 derece,
      gezinen. PF=0.5'te guc %76'ya varan olcude dusuk okunuyordu.
      Cozum: TEK ATIS kipi, iki cipe ardi ardina baslatma, kalan sabit
      kaymanin kesirli gecikmeyle silinmesi. Ayrica 1/|H(f)| olcek
      duzeltmesi ve menzil basina faz kalibrasyonu eklendi; B16'nin
      "PGA degisiminde ornek at" kalemi ise GECERSIZ cikti (PGA sabit).
  B20 Ornekleme hizi + bant siniri + menzil   (zamanlama + firmware)
      Kart 860 SPS'te DEGIL 91 SPS'te ornekliyordu: loop() basindaki olu
      bir bekleme her turda 4000 us zaman asimina dusuyor, COMP_QUE = 11b
      ise ALERT/RDY'yi yuksek empedansta tutuyordu. Varsayilan sebeke
      ayari Nyquist'in USTUNDEYDI. `f` ust siniri 400 -> 100 Hz.
      B22.1'de bu bolume KUTUPHANE TARAMASI eklendi: WebServer'in kendi
      `delay(1)`'i (istemci yokken, her turda) periyodu tik sinirina
      kilitliyordu — 665 yerine 500 SPS. `enableDelay(false)` ile kapandi.
  B21 Pil kapasite testi                     (veri sayfasi + isil + firmware)
      Tas direnc yuk + IRFZ44N anahtar. Kapi GND'ye cekili: ESP32 olurse
      MOSFET KAPANIR. Pil siniri 38.5 V, sogutucusuz 6.55 A. mAh + Wh +
      desarj egrisi + DCIR.
  B22a PC koprusu                            (role + arsiv + surucu)
      Karta baglanan HER tarayici olcumu bozuyor (her HTTP istegi loop()'u
      blokluyor) ve kartin SSE'si TEK istemcilik. Kopru N tarayiciyi 1'e
      indiriyor. En onemli iddiasi rolenin BAYT-SEFFAF oldugu: girdi ile
      cikti bayt-bayt karsilastiriliyor. Kopru satiri "duzeltmeye" kalksa
      ikinci bir temsil dogar ve ayrisma sinifi geri gelir.
      Donanim GEREKMIYOR: yukari-akis kaydedilmis bir satir gunlugu.
  B22b Kartin web katmani                    (firmware denetimi)
      Uc kusur kapandi: WiFi HIC acilmamisti (`WIFI_AD` bos sabit) ·
      SSE yalnizca `D` satirini tasiyordu (S2/M/ham skop/E/T/W/B ve tum
      */! yanitlari yalnizca Serial.print'teydi) · komut ucu YOKTU.
      Simdi: STA -> AP dusmesi + mDNS, `Serial` aynasi, cok istemcili SSE,
      POST /komut + CSRF yuzeyi, arayuz LittleFS'ten servis ediliyor.
  B9  Malzeme listesi + tezgah kilavuzu      (envanter + uretec)
      Semadan uretilen malzeme listesi envanter.csv ile karsilastiriliyor;
      tasarim elde olmayan bir parca istiyorsa zincir soyluyor. Kurulum
      kilavuzu da buradan uretiliyor — sayilar elle yazilmiyor.
  B25 Kart bringup kosucusu                 (kayitli kart)
      DONANIM GELDIGINDE `python tezgah_kart.py` gercek karti sinayacak.
      Bu adim o kosucunun KENDISINI siniyor: saglikli bir kart
      benzetiminde her denetim yesil, 13 kasitli bozuk senaryoda DOGRU
      denetim kirmizi olmali. Yanlis bir bringup testi, testsizlikten
      kotudur — gecmeyen bir karta "gecti" der.
  B7  Arayuz + KOMUT DENETIMI                (node)
      Arayuzun gonderebilecegi her komut harfi, firmware'in gercekten
      tanidigi `case` harfleriyle karsilastiriliyor — HEM app.js HEM
      index.html taranarak. Asama 2'de index.html taranmadigi icin uc
      dugme sessizce bozuk kalmisti (DEVIR 4.15).

⚠ YUKARIDAKI SIRA ANLATIM SIRASI, KOSMA SIRASI DEGIL. Gercek sira
  `ADIMLAR` listesi + main() govdesi: once 12 hesap/simulasyon adimi
  (B1 B2 B15 B11 B16 B18 B19 B17 B20 B21 B22a B22b B25), sonra bes agir
  adim (B3 sema, B4/B5 AVR, B6 derleme, B7 arayuz, B9 malzeme). Toplam 18.

Cikis kodu 0 ise her sey gecti.

── ADIMLARIN USTUNDE UC DENETIM (B23) ───────────────────────────────

1. TEZGAH KALEMLERI. Her adim, KENDI dogrulayamadigi seyleri
   `tezgah(...)` ile basiyor; burasi toplayip tek liste basiyor ve
   `_tezgah.md` yaziyor. Bir adim hic kalem basmazsa KIRMIZI —
   taban cizgisi `ADIMLAR`'in kendisi, elle liste degil.

2. IDDIA SAYISI KILIDI. Her adimin iddia sayisi
   `beklenen_sayim.json`'la birebir karsilastiriliyor. Sapma IKI YONDE
   de kirmizi: bir iddia dusse de, eklense de. (Yalnizca azalmaya
   bakmak yetmiyordu — B22.2'de biri dusup biri eklenince toplam sabit
   kalmis ve mutasyon kacmisti.) Bilerekse:
       python dogrula3.py --sayim-kilidi-yaz

3. ADIM SAYISI. `ADIM_SAYISI` README'de ve KULLANICI belgelerinde
   kullaniliyor; gercek adim sayisiyla uyusmazsa kirmizi.

Iddialarin gercekten isirdigini olcmek icin ayri bir kosucu var:
    python mutasyon.py [--adim B22b] [--liste]

NOT: Bu zincir TASARIMI dogrular, kurulmus bir KARTI degil. Asama 3
donanimi henuz kurulmadi.
"""
from __future__ import annotations

import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import json

import gecici
import sayim
from tezgah import ayristir, markdown

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SEMA3 = BURASI.parent / "sema3" / "olcum-karti-a3.kicad_sch"

ADIMLAR = [
    ("B1  On uc tasarimi ve hata butcesi", "tasarim3.py"),
    ("B2  Analog on uc (negatif dahil)",   "sim3_giris.py"),
    ("B15 Ariza ve zorlama simulasyonu",   "sim3_ariza.py"),
    ("B11 +-12 V rayi (7912 orta nokta)",  "sim3_besleme.py"),
    ("B16 V/I suzgec eslestirmesi",         "sim3_ortusme.py"),
    ("B18 GPIO kelepceleri (+3V3 geri besleme)", "sim3_kelepce.py"),
    ("B19 Skop kanali cift yonlu",           "sim3_skop.py"),
    ("B17 ADS es zamanliligi + suzgec duzeltmesi", "sim3_senkron.py"),
    ("B20 Ornekleme hizi + bant siniri + menzil", "sim3_bant.py"),
    ("B21 Pil kapasite testi (anahtar + kapi + tampon)", "sim3_pil.py"),
    # B22.3 — PC koprusu. Donanim GEREKMIYOR: yukari-akis olarak
    # kaydedilmis bir satir gunlugu oynatiliyor. En onemli iddiasi
    # rolenin BAYT-SEFFAF oldugu; kopru satiri "duzeltmeye" kalksa
    # ikinci bir temsil dogar ve ayrisma sinifi geri gelir.
    ("B22a PC koprusu (role + arsiv + surucu hakemi)", "test_kopru.py"),
    # B22.4 — kartin kendi web katmani. Serial aynasi, cok istemcili SSE,
    # komut ucu ve CSRF yuzeyi FIRMWARE KAYNAGINDAN dogrulaniyor.
    ("B22b Kart web katmani (ayna + SSE + komut ucu)", "sim3_web.py"),
    # B25 — DONANIM GELDIGINDE kosulacak bringup kosucusunun KENDISI.
    # Gercek karti dogrulamiyor; kosucunun dogru soruyu sorup dogru
    # cevaba baktigini siniyor (KayitKart uzerinde, 13 bozuk senaryo).
    # Yanlis bir bringup testi testsizlikten kotudur.
    ("B25 Kart bringup kosucusu (kayitli kart)", "test_tezgah_kart.py"),
]


# `ADIMLAR`'a girmeyen, main() govdesinde EL ILE kurulan adimlar:
# B3 (sema), B4/B5 (AVR), B6 (derleme), B7 (arayuz), B9 (malzeme).
# Bunlar birden fazla surec calistirdigi icin listeye sigmiyor.
# Sayi elle yaziliyor ama YALNIZ BURADA: tezgah_birlestir() her kosuda
# gercek adim sayisiyla karsilastiriyor, sapma KIRMIZI.
EL_ADIMLARI = 5
ADIM_SAYISI = len(ADIMLAR) + EL_ADIMLARI


def kos(betik: str) -> tuple[bool, str, float]:
    t0 = time.time()
    s = subprocess.run([sys.executable, betik], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    return s.returncode == 0, s.stdout, time.time() - t0


TABAN_YOLU = BURASI / "beklenen_sayim.json"


def sayim_kilidi(sonuclar, yaz: bool = False) -> list[str]:
    """Adim basina iddia sayisi kilidi. Bkz. asagidaki uzun aciklama.

    🔴 B27 A2: KIRIK KOSUDA TABAN YAZILMAZ. B9 cokmusken `--sayim-kilidi-yaz`
    ile kosuldu ve cokmus adimin YARIM sayisi kilide yazildi — sonraki
    temiz kosu "sapma" diye kirmizi olacak, ya da daha kotusu yarim sayi
    beklenti olarak kalacakti. Basarisiz adim varsa yazma istegi
    reddedilir ve nedeni basilir.
    """
    """Her adimin iddia sayisini kilitli tabanla karsilastirir.

    🔴 NEDEN SAPMA IKI YONDE DE KIRMIZI. DEVIR'in kendi uyarisi: bir
    iddia dusup baskasi eklenince TOPLAM SABIT KALIR ve mutasyon kacar
    (B22.2'de oldu). Yalnizca azalmayi denetlemek de yetmiyor: bir
    iddiayi silip iki tane ekleyen bir degisiklik yine gorunmezdi.
    O yuzden HER adim icin sayi listesi BIREBIR eslesmek zorunda.

    Sayi degismesi kotu bir sey demek DEGIL — yeni iddia eklemek iyidir.
    Kilit yalnizca "farkinda misin" diye soruyor:
        python dogrula3.py --sayim-kilidi-yaz
    """
    su_an = {baslik: sayim.sayimlar(cikti)
             for baslik, _t, _s, cikti in sonuclar}
    kirik = [b for b, tamam, _s, _c in sonuclar if not tamam]
    if yaz and kirik:
        print(f"  ⚠ kilit YAZILMADI: kirik kosuda taban yazilmaz ({', '.join(kirik)})")
        yaz = False
    if yaz or not TABAN_YOLU.exists():
        TABAN_YOLU.write_text(json.dumps(
            {b: [list(x) for x in v] for b, v in su_an.items()},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  taban yazildi: {TABAN_YOLU.name} "
              f"({sum(a for v in su_an.values() for a, _ in v)} iddia)")
        return []

    taban = {b: [tuple(x) for x in v] for b, v in
             json.loads(TABAN_YOLU.read_text(encoding="utf-8")).items()}
    hatalar = []
    for baslik, simdi in su_an.items():
        bekl = taban.get(baslik)
        if bekl is None:
            hatalar.append(f"{baslik}: tabanda YOK (yeni adim mi?)")
        elif simdi != bekl:
            hatalar.append(
                f"{baslik}: {bekl} bekleniyordu, {simdi} cikti")
    for baslik in taban:
        if baslik not in su_an:
            hatalar.append(f"{baslik}: tabanda var ama KOSMADI")
    return hatalar


def tezgah_birlestir(sonuclar) -> list[str]:
    """Adim ciktilarindaki tezgah kalemlerini TEK listede toplar.

    NEDEN BURADA: tek tezgah listesi `DEVIR.md`'de ELLE yaziliydi ve
    B20/B21 doneminde DONDU — B22.3/B22.4/B22.5 uculu de *"tezgah
    listesinde"* diyerek ICERMEDIGI kalemlere atif yapiyordu. Yani bu
    projenin defalarca yandigi AYRISMA SINIFININ belge surumu.

    KURAL: HER adim en az bir kalem basmak zorunda. Taban cizgisi elle
    yazilmiyor — `ADIMLAR`'in kendisi taban cizgisi. Bir betikten
    `tezgah(...)` cagrisi silinirse o adim sifira duser ve burasi
    KIRMIZI olur; `ADIMLAR`'a kalemsiz yeni bir adim eklenirse de.

    Donus: kalem basmayan adim basliklari.
    """
    kalemler = []
    sessiz = []
    hatalar = []
    if len(sonuclar) != ADIM_SAYISI:
        # `ADIM_SAYISI` README'de ve KULLANICI belgelerinde kullaniliyor.
        # Yeni bir el adimi eklenip EL_ADIMLARI unutulursa kullaniciya
        # yanlis sayi gider — bu satir onu ayni kosuda yakaliyor.
        hatalar.append(f"ADIM_SAYISI={ADIM_SAYISI} ama {len(sonuclar)} adim "
                       f"kostu — dogrula3.EL_ADIMLARI guncellenecek")
    for baslik, _tamam, _sure, cikti in sonuclar:
        bulunan = ayristir(cikti)
        if bulunan:
            kalemler += bulunan
        else:
            sessiz.append(baslik)

    print()
    print("=" * 78)
    print(f"  TEZGAHTA OLCULECEKLER — {len(kalemler)} kalem, "
          f"{len(sonuclar) - len(sessiz)}/{len(sonuclar)} adimdan toplandi")
    print("=" * 78)
    son = None
    for i, (adim, kalem, kabul) in enumerate(kalemler, 1):
        if adim != son:
            print()
            print(f"  --- {adim}")
            son = adim
        print(f"  {i:2d}. {kalem}")
        for sat in textwrap.wrap(kabul, 68):
            print(f"      {sat}")

    hedef = BURASI / "_tezgah.md"
    hedef.write_text(markdown(kalemler), encoding="utf-8")
    print()
    print(f"  -> {hedef.name} yazildi ({len(kalemler)} kalem)")

    if sessiz:
        print()
        print(f"  KIRMIZI: {len(sessiz)} adim tezgah kalemi BASMADI — "
              f"kendi sinirlarini soylemeyen adim, tezgahta korlestirir:")
        for b in sessiz:
            print(f"    * {b}")
        print("    Duzeltme: o adimin betiginin sonuna tezgah(...) ekle.")
    # 🔴 B26: GIZLILIK — depo herkese acik. Kural yukarida bir YORUM olarak
    #    duruyordu ve yorum kurali korumaz: bagimsiz bir denetim HEAD'de 59
    #    mutlak yol buldu. Artik zincirin bir DEGISMEZI; adim degil, cunku
    #    tek bir adima degil deponun tamamina ait. Temizse tek satir basar.
    g = subprocess.run([sys.executable, "gizlilik_dogrula.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    if g.returncode != 0:
        print()
        print(g.stdout.rstrip())
        hatalar.append("gizlilik_dogrula.py kisisel iz buldu — "
                       "yayinlamadan once temizle")
    else:
        print("  gizlilik: takip edilen dosyalarda kisisel iz yok")

    if hatalar:
        print()
        for h in hatalar:
            print(f"  KIRMIZI: {h}")
    return sessiz + hatalar


def main() -> int:
    print("=" * 78)
    print("  OLCUM KARTI — ASAMA 3 DOGRULAMA ZINCIRI  (cift yonlu, +-615 V)")
    print("=" * 78)
    sonuclar = []

    for baslik, betik in ADIMLAR:
        print(f"\n{'-' * 78}\n  {baslik}\n{'-' * 78}")
        tamam, cikti, sure = kos(betik)
        print(cikti.rstrip())
        sonuclar.append((baslik, tamam, sure, cikti))

    # --- B3: sema uret + ERC + netlist polarite
    print(f"\n{'-' * 78}\n  B3  Sema: uretim + ERC + netlist\n{'-' * 78}")
    t0 = time.time()
    u = subprocess.run([sys.executable, "sema3-uret.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    print(u.stdout.rstrip())
    # 🔴 `u.returncode` DENETLENMIYORDU. Sema uretimi coksede ERC ve
    # netlist denetimi diskteki BAYAT `.kicad_sch` / `.net` dosyalarini
    # okuyup temiz rapor veriyordu — yani B3, uretimi hic calismamis bir
    # semayla YESIL kaliyordu. Zincirin en sessiz deligi.
    if u.returncode != 0:
        print(u.stderr[-1500:])
        print("  KIRMIZI: sema3-uret.py cokti — ERC ve netlist BAYAT "
              "dosyalari okuyacakti.")
    erc = subprocess.run(
        [KICAD_CLI, "sch", "erc", "--output", "erc3.rpt",
         "--severity-error", "--severity-warning", str(SEMA3)],
        cwd=BURASI, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300)
    ihlal = [x for x in erc.stdout.splitlines() if "violation" in x.lower()]
    erc_temiz = "Found 0 violations" in erc.stdout
    print(f"  ERC: {ihlal[0].strip() if ihlal else '?'}")
    # 🔴 NETLIST'I NORMALLESTIR. kicad-cli iki UCUCU sey gomuyor:
    #    uretim ZAMAN DAMGASI ve semanin MUTLAK YOLU. Ikisi de her
    #    kosuda degisiyor/makineye ozgu:
    #      * zaman damgasi -> her commit'te anlamsiz diff
    #      * semanin MUTLAK diskteki yolu -> yayinlanan depoda kisisel iz
    #    Netlist bir yapi urunu ama `belge-uret.py` onu okuyor, o yuzden
    #    depoda duruyor. Normallestirince hem belirlenimli hem temiz.
    #    ⚠ Temizlik ARTIK `netlist_temizle.py`de — TEK KAYNAK. Buradaki
    #      kopya B9'da netlist yeniden uretilince eziliyordu (B26).
    import netlist_temizle
    netlist_temizle.temizle(BURASI / "netlist3.net")

    n = subprocess.run([sys.executable, "netlist3_dogrula.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    print(n.stdout.rstrip())
    # B48: kullanicinin okudugu `BELGELER/sema.pdf` ELLE uretiliyordu ve
    # 9 Eylul'de donmustu — sema 11 Eylul'de degisti (emniyet baglantisi),
    # PDF degismedi. Artik semayla ayni adimda uretiliyor.
    pdf = subprocess.run(
        [KICAD_CLI, "sch", "export", "pdf", "--output",
         str(BURASI.parent / "BELGELER" / "sema.pdf"), str(SEMA3)],
        cwd=BURASI, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300)
    print(f"  sema.pdf: {'yazildi' if pdf.returncode == 0 else 'KIRMIZI — uretilemedi'}")
    sonuclar.append(("B3  Sema (ERC + netlist)",
                     u.returncode == 0 and erc_temiz and n.returncode == 0
                     and pdf.returncode == 0,
                     time.time() - t0, u.stdout + n.stdout))

    # --- B4/B5: firmware matematigi, GERCEK KOD AVR emulatorunde
    print(f"\n{'-' * 78}\n  B4/B5  Olcum matematigi + Lagrange (AVR emulatoru)"
          f"\n{'-' * 78}")
    tamam, cikti, sure = kos("test_olcum3.py")
    print(cikti.rstrip())
    sonuclar.append(("B4/B5  Firmware + Lagrange (AVR)", tamam, sure, cikti))

    # --- B6: firmware derleme + ikilide olu kod
    print(f"\n{'-' * 78}\n  B6  Firmware: derleme + ikilide olu kod\n{'-' * 78}")
    t0 = time.time()
    # once ortak skop matematiginin iki kopyasi ayrismis mi
    a = subprocess.run([sys.executable, "test_skop_ayni.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    print(a.stdout.rstrip())
    tamam, cikti, _ = kos("test_firmware3.py")
    print(cikti.rstrip())
    sonuclar.append(("B6  Firmware derleme + ikili",
                     tamam and a.returncode == 0, time.time() - t0,
                     a.stdout + cikti))

    # --- B7: arayuz + arayuz<->firmware komut denetimi
    print(f"\n{'-' * 78}\n  B7  Arayuz (arayuz3) + komut denetimi\n{'-' * 78}")
    t0 = time.time()
    a = subprocess.run(["node", "test_arayuz3.js"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    print(a.stdout.rstrip())
    if a.returncode != 0 and a.stderr.strip():
        print(a.stderr.rstrip())
    sonuclar.append(("B7  Arayuz + komut denetimi",
                     a.returncode == 0, time.time() - t0, a.stdout))

    # --- B9: malzeme listesi + tezgah kilavuzu
    print(f"\n{'-' * 78}\n  B9  Malzeme listesi + tezgah kilavuzu\n{'-' * 78}")
    t0 = time.time()
    b = subprocess.run([sys.executable, "bom_dogrula.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    print(b.stdout.rstrip())
    k = subprocess.run([sys.executable, "kurulum3-uret.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    print(k.stdout.rstrip())
    # B21: kullanici belgeleri de buradan uretiliyor — tasarim degisince
    # BELGELER/ bayat kalmasin diye zincire bagli.
    bl = subprocess.run([sys.executable, "belge-uret.py"], cwd=BURASI,
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=300)
    print(bl.stdout.rstrip())
    if bl.returncode != 0:
        print(bl.stderr[-1500:])
    # B48: delikli plaket yerlesimi — bakir netlistle birebir mi (her kurulum
    # adiminda), kacak yolu, Kelvin, ayirma. B3'un urettigi netlist3.net'i
    # okur, o yuzden B3'ten SONRA kosmali. Denetim gecerse 7-yerlesim.html.
    y = subprocess.run([sys.executable, "yerlesim3.py"], cwd=BURASI,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    print(y.stdout.rstrip())
    if y.returncode != 0:
        print(y.stderr[-1500:])
    # B50: kart disi kurulum (kutu, panel, sont, Q1, jaklar). yerlesim3'un
    # KABLOLAR'ini ve netlisti okur, o yuzden ondan SONRA. Denetim gecerse
    # 8-kutu.html.
    ku = subprocess.run([sys.executable, "kutu.py"], cwd=BURASI,
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=300)
    print(ku.stdout.rstrip())
    if ku.returncode != 0:
        print(ku.stderr[-1500:])
    sonuclar.append(("B9  Malzeme + kurulum kilavuzu",
                     b.returncode == 0 and k.returncode == 0 and bl.returncode == 0
                     and y.returncode == 0 and ku.returncode == 0,
                     time.time() - t0,
                     b.stdout + k.stdout + bl.stdout + y.stdout + ku.stdout))

    print("\n" + "=" * 78)
    print("  OZET")
    print("=" * 78)
    for baslik, tamam, sure, _ in sonuclar:
        print(f"  {'GECTI ' if tamam else 'KALDI '} {baslik:<40} {sure:6.1f} s")

    # Zincir kendi copunu toplasin — arduino-cli ve ngspice geride
    # onlarca MB birakiyor ve bunlarin hepsi YENIDEN URETILEBILIR.
    import shutil
    # 🔴 `glob` OZYINELEMESIZ ve `if d.is_dir()` DOSYALARI ELIYORDU:
    # `kopru/__pycache__` ile `uretim/avr/__pycache__` hic silinmiyordu,
    # `_a4_*.elf` gibi dosyalar da oyle. `rglob` + dosya dali eklendi.
    # ⚠ `kopru/arsiv/` KAPSAM DISI — orasi kullanicinin olcum gunlugu.
    for kok in (BURASI, BURASI.parent / "kopru"):
        for kalip in ("_b[0-9]*", "_chk*", "_lk*", "__pycache__"):
            for d in kok.rglob(kalip):
                if "arsiv" in d.parts:
                    continue
                if d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)
                else:
                    d.unlink(missing_ok=True)
    for f in BURASI.glob("_a4_*.elf"):
        f.unlink(missing_ok=True)
    # %TEMP% kalintilari: alti betik mkdtemp cagirip silmiyordu, 826
    # dizin birikmisti (B23.3'te olculdu). `gecici.py` yeni kosularda
    # sizmayi durduruyor; burasi ESKI birikimi suepuruyor.
    n_gec = gecici.kalintilari_sil()
    if n_gec:
        print(f"  (temizlendi: %TEMP% altinda {n_gec} artik dizin)")
    for d in (BURASI.parent / "kod" / "olcum-karti-a3" / "build",
              BURASI.parent / "arsiv" / "asama2" / "olcum-karti-a2" / "build",
              BURASI.parent / "arsiv" / "asama1" / "olcum-karti" / "build"):
        shutil.rmtree(d, ignore_errors=True)
    for f in BURASI.glob("erc*.rpt"):
        f.unlink(missing_ok=True)

    kalan = [b for b, t, _, _c in sonuclar if not t]
    sessiz = tezgah_birlestir(sonuclar)
    kilit = sayim_kilidi(sonuclar, yaz="--sayim-kilidi-yaz" in sys.argv)
    if kilit:
        print()
        print("  KIRMIZI: iddia sayisi kilidi tutmadi — bir iddia dustu,")
        print("  eklendi ya da yer degistirdi. Bilerek yaptiysan:")
        print("    python dogrula3.py --sayim-kilidi-yaz")
        for h in kilit:
            print(f"    * {h}")
    print()
    if kalan:
        print(f"  {len(kalan)} adim BASARISIZ: {', '.join(kalan)}")
        return 1
    if sessiz or kilit:
        return 1
    print("  Asama 3 dogrulandi — tasarim, sema ve firmware matematigi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
