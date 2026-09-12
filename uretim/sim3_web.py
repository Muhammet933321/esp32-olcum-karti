# -*- coding: utf-8 -*-
"""B22.4 — KARTIN WEB KATMANI (Serial aynasi · SSE · komut ucu · guvenlik).

    python sim3_web.py

B22.4 oncesi kartin web tarafi UC yerden kirikti:

  1. [!] WiFi HIC ACILMIYORDU. `WIFI_AD` bos bir sabitti, yani
     `WiFi.begin()` bir kez bile cagrilmadi. AP kipi dosyada hic yoktu.
  2. [!] SSE YALNIZCA `D` SATIRINI TASIYORDU. `akis_yolla` tek bir yerden,
     `loop()`'un rapor blogundan cagriliyordu. `S2`/`M`/ham skop/`E`/`T`/
     `W`/`B` ve butun `*`/`!` yanitlari yalnizca `Serial.print`'teydi:
     WiFi ile baglanan arayuz SALT-OKUNUR ve SESSIZ olurdu.
  3. [!] KOMUT UCU YOKTU. `komut_calistir`'a HTTP'den giden yol yoktu.

Bu betik duzeltmelerin GERCEKTEN uygulandigini FIRMWARE KAYNAGINDAN
dogruluyor. Metin tabanli iddialar YORUMLARI CIKARARAK bakiyor — bir
iddianin kendi aciklama yorumuyla karsilanmasi, iddia olmadigi anlamina
gelir (bu ders B22.0-B22.2'de bes kez cikti).

⚠ Bu adim TASARIMI ve FIRMWARE'i sinar, kurulmus bir KARTI degil.
  Gercek WiFi baglantisi, mDNS'in telefonda cozulmesi, CSRF savunmasinin
  gercek tarayicilardaki davranisi ve `esp_wifi_start` <-> ADC DMA
  carpismasi TEZGAHTA olculmeli.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
from tezgah import tezgah                               # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"

INO = (KOD / "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
AG_H = (KOD / "ag.h").read_text(encoding="utf-8", errors="replace")
AKIS_H = (KOD / "web_akis.h").read_text(encoding="utf-8", errors="replace")
SATIR_H = (KOD / "web_satir.h").read_text(encoding="utf-8", errors="replace")


def kod(metin: str) -> str:
    """C/C++ yorumlarini cikarir — iddialar KODA baksin, prozaya degil."""
    return re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", metin, flags=re.S))


INO_KOD = kod(INO)
AG_KOD = kod(AG_H)


def govde(kaynak: str, imza: str) -> str:
    """Bir fonksiyonun govdesini susluler sayarak cikarir."""
    i = kaynak.find(imza)
    if i < 0:
        return ""
    j = kaynak.find("{", i)
    if j < 0:
        return ""
    d = 0
    for k in range(j, len(kaynak)):
        if kaynak[k] == "{":
            d += 1
        elif kaynak[k] == "}":
            d -= 1
            if d == 0:
                return kaynak[j:k + 1]
    return ""


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


# ═══════════════════════════════════════════════════════════════════════
def bolum1(r):
    bolum(r, "BOLUM 1 — `Serial` AYNASI (SSE artik HER satiri tasiyor)")
    r.bilgi("  Once SSE yalnizca `D` tasiyordu: `akis_yolla` TEK yerden,")
    r.bilgi("  loop()'un rapor blogundan cagriliyordu. Skop yakalamasi")
    r.bilgi("  yapan bir WiFi kullanicisi HICBIR SEY goremezdi.")
    r.bilgi("")

    r.kosul("  1a: `Serial` aynasi kurulu",
            "#define Serial CIKIS" in INO,
            "245 cagri yeri degismeden aynaya gidiyor")
    r.kosul("  1a: makrodan ONCE `#undef` var",
            re.search(r"#undef\s+Serial\s*\n\s*#define\s+Serial\s+CIKIS", INO)
            is not None,
            "cekirdekte `Serial` ZATEN makro — undef'siz 'redefined' uyarisi "
            "veriyor ve bu projede uyariya sifir tolerans var")

    # [!] `#define Serial` butun include'lardan SONRA gelmeli.
    i_tanim = INO.find("#define Serial CIKIS")
    son_include = max(m.start() for m in re.finditer(r"^#include", INO, re.M))
    r.kosul("  1a: `#define Serial` butun #include'lardan SONRA",
            i_tanim > son_include,
            "once gelirse kutuphane basliklarindaki Serial de yeniden adlanir")

    # Nesne olusturulurken `Serial` HALA gercek nesne olmali.
    i_nesne = INO.find("WebAkis CIKIS(Serial)")
    r.kosul("  1a: CIKIS nesnesi makrodan ONCE olusturuluyor",
            0 <= i_nesne < i_tanim,
            "sonra olsaydi kendi kendini sarardi")

    # [!] OZYINELEME: akis_yolla icinde Serial KULLANILAMAZ.
    g_yolla = kod(govde(INO, "static void akis_yolla(const char *satir)"))
    r.kosul("  1b: `akis_yolla` icinde Serial KULLANILMIYOR",
            bool(g_yolla) and "Serial" not in g_yolla,
            "ayna bu fonksiyonu cagiriyor — Serial kullansa SONSUZ OZYINELEME")

    r.kosul("  1b: satir bolucu ayri ve saf C (AVR'de sinaniyor)",
            "satir_ekle" in SATIR_H and "#include <Arduino.h>" not in SATIR_H,
            "sinir kosullari donanimsiz sinanabiliyor (test_olcum3.py)")
    # ⚠ Adin gecmesi yetmiyor — yapi alani ve yorum da adi tasiyor.
    #   ARTIRMA sinaniyor (mutasyon `s->kirpilan++` yerine `(void)0`
    #   koyunca iddia yesil kalmisti). Davranissal karsiligi AVR'de:
    #   test_olcum3.py "Kirpilan bayt SAYILIYOR" -> 77 bayt.
    r.kosul("  1b: kirpilan bayt GERCEKTEN artiriliyor",
            "s->kirpilan++" in kod(SATIR_H),
            "sessiz kirpma yasak")
    r.kosul("  1b: ayna kirpilan sayacini disari veriyor",
            "kirpilan()" in kod(AKIS_H))

    # 🔴 B26 — AYNA + ACIK CAGRI = HER SATIR IKI KEZ.
    #    B20 `loop()`in rapor blogunda `akis_yolla(son_satir)` cagiriyordu;
    #    o sirada SSE'yi besleyen tek yol buydu. B22.4 `Serial` aynasini
    #    getirince tamamlanan her satir zaten `web_satir_hazir()` ->
    #    `akis_yolla()` yolundan gitmeye basladi, ama eski cagri kaldirilmadi.
    #    Tezgahta olculdu: 8 sn'de 80 `D` olayi / 40 benzersiz satir,
    #    tekrar dagilimi {2: 40}. Kart 5/s rapor ederken yayin 10/s idi.
    #    Bir mekanizma daha genelini getirdiginde eskisi KALDIRILMALI.
    #    ⚠ `(?<!void )` SART: yoksa fonksiyonun KENDI TANIMI da cagri
    #      sayiliyor ve iddia dogru kodda bile kirmizi yaniyor.
    _cagri = [m.start()
              for m in re.finditer(r"(?<!void )\bakis_yolla\s*\(", INO_KOD)]
    _g_hazir = kod(govde(INO, "void web_satir_hazir"))
    r.kosul("  1b: `akis_yolla` YALNIZCA ayna geri cagrisindan cagriliyor",
            len(_cagri) == 1 and "akis_yolla(" in _g_hazir,
            f"{len(_cagri)} cagri yeri — birden fazlaysa ayna ile birlikte "
            f"calisip satiri COGALTIR")


def bolum2(r):
    bolum(r, "BOLUM 2 — SSE: cok istemci, kalp atisi, yer imi")
    r.bilgi("  Once TEK global `akis_istemci` vardi; ikinci `GET /akis`")
    r.bilgi("  birincisini SESSIZCE uzerine yaziyor ve soketi kapatiyordu.")
    r.bilgi("")

    azami = re.search(r"#define AKIS_AZAMI (\d+)", INO)
    n = int(azami.group(1)) if azami else 0
    r.kosul("  2a: birden fazla SSE istemcisi destekleniyor", n >= 2,
            f"AKIS_AZAMI = {n}")
    r.kosul("  2a: yuva bulunamazsa SEBEBI soyleniyor",
            "event: dolu" in INO,
            "sessizce kapatmak yerine")
    r.kosul("  2b: kalp atisi var (NAT/vekil zaman asimi)",
            "akis_kalp" in INO_KOD and ": kalp" in INO,
            "15 s")
    r.kosul("  2b: kalp atisi loop()'tan cagriliyor",
            "akis_kalp()" in kod(govde(INO, "void loop()")),
            "cagrilmayan bir kalp atisi yoktur")
    r.kosul("  2c: `id:` yer imi gonderiliyor",
            "id: " in INO and "akis_sira" in INO_KOD,
            "yeniden baglanmada nerede kalindigi bilinsin")
    r.kosul("  2c: `retry:` gonderiliyor", "retry: 3000" in INO)
    r.kosul("  2d: kopru kayitliysa ikinci istemci REDDEDILIYOR",
            "event: kopru" in INO and "kopru_canli()" in INO_KOD,
            "kart TEK surucuye hizmet ediyor — sessiz kapanma yok")
    r.kosul("  2d: kopru kaydi RAM'de, NVS'te DEGIL",
            "kopru_adres" in INO_KOD
            and not re.search(r'put\w+\(\s*"kopru', INO_KOD),
            "koprunun adresi gecici bir gercek, kalibrasyon gibi kalici degil")


def bolum3(r):
    bolum(r, "BOLUM 3 — KOMUT UCU ve CSRF YUZEYI")
    r.bilgi("  Kart bir MOSFET suruyor: `p1` pil desarjini BASLATIYOR.")
    r.bilgi("  GET tabanli bir uc olsaydi <img src=...> ile uzaktan")
    r.bilgi("  tetiklenebilirdi. Ayrica ciplak `g` kanali tuglaliyordu")
    r.bilgi("  (B22.1'de kapatildi) — o da bir <img> ile gonderilebilirdi.")
    r.bilgi("")

    r.kosul("  3a: `/komut` ucu var", '"/komut"' in INO_KOD)
    r.kosul("  3a: YONTEM acikca POST",
            'sunucu.on("/komut", HTTP_POST' in INO_KOD,
            "HTTP_ANY olsaydi GET /komut?k=p1 calisirdi")
    r.kosul("  3a: hicbir uc HTTP_ANY ile kayitli degil",
            "HTTP_ANY" not in INO_KOD)
    # ⚠ GOVDE ICINDE aranmali: once dosya genelinde araniyordu ve
    #   `kopru_sayfa` da ayni denetimi yaptigi icin "komut ucundan
    #   kaldir" mutasyonu KACTI.
    g_kom0 = kod(govde(INO, "void komut_sayfa()"))
    r.kosul("  3b: ozel baslik KOMUT UCUNDA zorunlu",
            'header("X-Olcum")' in g_kom0,
            "<img>/<form> ozel baslik EKLEYEMEZ")
    r.kosul("  3b: ozel baslik KOPRU UCUNDA da zorunlu",
            'header("X-Olcum")' in kod(govde(INO, "void kopru_sayfa()")))

    # [!] collectHeaders cagrilmazsa header() HER ZAMAN bos doner ve butun
    #    CSRF savunmasi SESSIZCE devre disi kalir.
    # 🔴 Once yalnizca `"collectHeaders" in INO_KOD` bakiyordu ve iddia
    #    GEVSEKTI: `sunucu.collectHeadersX(...)` de geciyordu (B23.3
    #    mutasyon kosucusuyla olculdu — kacti). Artik cagrinin KENDISI
    #    ve toplanacak dizinin ona verildigi aranıyor.
    r.kosul("  3b: `collectHeaders` cagriliyor",
            "sunucu.collectHeaders(toplanacak" in INO_KOD.replace(" ", ""),
            "cagrilmazsa header() hep bos doner ve savunma sessizce oler")
    toplanan = re.search(r"const char \*toplanacak\[\] = \{([^}]*)\}", INO_KOD)
    metin = toplanan.group(1) if toplanan else ""
    r.kosul("  3b: X-Olcum ve X-Jeton toplananlar arasinda",
            "X-Olcum" in metin and "X-Jeton" in metin, metin.strip())

    r.kosul("  3c: oturum jetonu uretiliyor",
            "jeton_uret" in INO_KOD and "esp_random" in INO_KOD)
    r.kosul("  3c: jeton denetleniyor",
            'header("X-Jeton")' in INO_KOD and "oturum_jetonu" in INO_KOD)
    r.kosul("  3d: Host beyaz listesi var (DNS rebinding)",
            "hostHeader" in INO_KOD and "host_gecerli" in INO_KOD,
            "olmadan jeton ve ozel baslik savunmalari da coker")
    r.kosul("  3d: Host denetimi komut ucunda UYGULANIYOR",
            "host_gecerli()" in kod(govde(INO, "void komut_sayfa()")))

    # [!] EMNIYET: p0 her zaman serbest.
    g_ser = kod(govde(INO, "static bool komut_serbest(const char *k)"))
    r.kosul("  3e: [!] `p0` (DURDUR) jetonsuz/parolasiz gecebiliyor",
            "'p'" in g_ser and "'0'" in g_ser,
            "baslatmak yetki ister; durdurmayi hicbir sey geciktiremez")
    g_kom = kod(govde(INO, "void komut_sayfa()"))
    r.kosul("  3e: serbest komut jeton denetimini ATLIYOR",
            "komut_serbest" in g_kom and "!komut_serbest" in g_kom)
    # B27 A2: `?` (ayar dokumu) da serbest — sayfa acilinca K5 esitlemesi
    # parola sorusu acmadan calissin. Ama YALNIZCA tam `?`: `N` (parolalari
    # basar) ve baska hicbir harf serbest OLMAMALI.
    r.kosul("  3e: `?` (ayar dokumu, salt okunur) serbest",
            "'?'" in g_ser and "k[1] == 0" in g_ser,
            "tam eslesme sart: `?x` gecmemeli")
    r.kosul("  3e: [!] `N` (parolalari basar) serbest DEGIL",
            "'N'" not in g_ser and "'p'" in g_ser and g_ser.count("return true") == 2,
            "serbest liste tam olarak iki komut: p0 ve ?")

    r.kosul("  3f: komutlar KUYRUGA giriyor, dogrudan calismiyor",
            "komut_kuyruga" in g_kom and "komut_calistir" not in g_kom,
            "HTTP isleyicisi uzun komut beklemiyor; tek yazar disiplini")
    r.kosul("  3f: kuyrugu loop() bosaltiyor",
            "komut_kuyrugu_bosalt()" in kod(govde(INO, "void loop()")))


def bolum4(r):
    bolum(r, "BOLUM 4 — CORS: `enableCORS(true)` KULLANILMAMALI")
    r.bilgi("  WebServer::enableCORS(true) uc basligi da `*` yapiyor")
    r.bilgi("  (WebServer.cpp:663-667): Allow-Origin, Allow-Methods,")
    r.bilgi("  Allow-Headers. Boylece HERHANGI bir sayfa yaniti OKUYABILIR")
    r.bilgi("  ve oturum jetonu sizar — jeton savunmasinin tamami coker.")
    r.bilgi("")
    r.kosul("  4a: `enableCORS` kullanilmiyor",
            "enableCORS" not in INO_KOD,
            "yerine kayitli kopru kokenine ELLE izin veriliyor")
    r.kosul("  4a: ACAO yalnizca kayitli kopruye veriliyor",
            "Access-Control-Allow-Origin" in INO
            and "kopru_adres" in kod(govde(INO, "void onuc_sayfa()")),
            "acik uclu `*` yok")
    # `ACAO: null` da yasak — sandbox'li iframe'ler de `null` kokenli.
    r.kosul("  4b: `Access-Control-Allow-Origin: null` verilmiyor",
            'Allow-Origin"), F("null")' not in INO
            and '"null"' not in kod(govde(INO, "void onuc_sayfa()")),
            "sandbox'li iframe'ler de null kokenli — acik kapi olurdu")


def bolum5(r):
    bolum(r, "BOLUM 5 — AG: STA -> AP dususu, NVS ayriligi, sir sizintisi")
    r.bilgi("  B22.4 oncesi `WIFI_AD` bos bir sabitti: WiFi HIC acilmadi.")
    r.bilgi("")
    r.kosul("  5a: eski sabitler kaldirildi",
            "WIFI_AD" not in INO_KOD and "WIFI_SIFRE" not in INO_KOD)
    r.kosul("  5a: STA denenip AP'ye DUSULUYOR",
            "WIFI_STA" in AG_KOD and "softAP" in AG_KOD,
            "AP kipi olmadan 'bilgisayar yoksa' senaryosu ag altyapisina "
            "bagimli kalirdi")
    r.kosul("  5a: mDNS kuruluyor", "MDNS.begin" in AG_KOD)
    # 🔴 Ad BOSALIRSA `http://<ad>.local` cozulmez ve BELGELER/6-ag.html
    #    bos adres yazar — B23.3 mutasyonu bunu KACIRDI, iddia yoktu.
    _mdns = re.search(r'#define AG_MDNS\s+"([^"]*)"', AG_KOD)
    # 🔴 Afis satirlarinin KAPANDIGI denetimi. "Ag: ..." blogunun sonunda
    #    println YOKTU ve cikti `http://192.168.4.1Arayuz: ...` seklinde
    #    yapisiyordu — adresi kopyalayan kullanici BOZUK adres aliyordu.
    #    B25 bringup kosucusu hazirlanirken bulundu (2026-09-11).
    #    ⚠ Kapsam: `setup()` govdesinin ICINDE, "Ag: " ile "Arayuz: "
    #    arasindaki parcaya bakiyoruz — tum dosyada aramak komsu
    #    fonksiyonlarin println'lerini kabul ederdi.
    _kur = govde(INO, "void setup()")
    _i = _kur.find('F("Ag: ")')
    _j = _kur.find('F("Arayuz: ")', _i + 1)
    _ara = _kur[_i:_j] if 0 <= _i < _j else ""
    r.kosul("  5a: `Ag:` satiri `Arayuz:`den ONCE KAPANIYOR",
            "Serial.println();" in _ara.replace(" ", "").replace(
                "Serial.println()", "Serial.println();").replace(";;", ";"),
            "kapanmazsa IP adresi bir sonraki etikete yapisir ve "
            "kullanici bozuk adres kopyalar")

    r.kosul("  5a: mDNS adi BOS DEGIL", bool(_mdns and _mdns.group(1)),
            f"http://{_mdns.group(1) if _mdns else '?'}.local")
    r.kosul("  5a: MDNS.begin adi sabitten aliyor",
            "MDNS.begin(AG_MDNS)" in AG_KOD.replace(" ", ""),
            "elle yazilirsa sabitle sessizce ayrisir")

    # [!] `Ns` (web parolasi) ANINDA gecerli — web_yetkili() her istekte
    #     NVS'ten okuyor. `N` komutunun ortak kuyrugu ise "bir sonraki
    #     acilista gecerli" diyor. Ns o kuyruga DUSERSE, korumayi KALDIRAN
    #     kullaniciya korumanin surdugu soylenmis olur. Yani mesajin
    #     dogrulugu bir EMNIYET ozelligi.
    #     ⚠ Kapsam: yorumlar ciplak metinde de gecebilir, o yuzden
    #     yalnizca KOD uzerinde ve `alt == 's'` dalinin ICINDE ariyoruz.
    #     🔴 Ilk yazimda dilim `alt == 's'`den ortak kuyruga kadardi ve
    #     SONRAKI dallarin `break`lerini de iceriyordu — mutasyon (Ns'in
    #     kendi break'ini sil) KACTI. Dilim artik yalnizca o dalin govdesi:
    #     `alt == 's'`den bir SONRAKI `else`e kadar.
    _ns = INO_KOD.find("alt == 's'")
    _son = INO_KOD.find("else", _ns + 1) if _ns >= 0 else -1
    _dal = INO_KOD[_ns:_son] if 0 <= _ns < _son else ""
    r.kosul("  5b: `Ns` dali ortak 'sonraki acilis' kuyruguna DUSMUYOR",
            "break" in _dal,
            "Ns ANINDA gecerli; kuyruga duserse parolayi KALDIRAN "
            "kullaniciya korumanin surdugu soylenir")
    r.kosul("  5b: parola KALDIRILDI mesaji korumasizligi SOYLUYOR",
            "korumasiz" in _dal,
            "sessiz 'kaldirildi' yeterli degil — komut ucu o an aciliyor")

    # [!] NVS AYRILIGI: Ayar3 buyurse imza bumplanir ve KALIBRASYON GIDER.
    r.kosul("  5b: ag ayarlari AYRI NVS ad alaninda",
            'AG_ALAN "olcumag"' in AG_H and '"olcum3"' not in AG_KOD,
            "Ayar3 buyurse sizeof denetimi bozulur, imza bumplanir ve "
            "KALIBRASYON SIFIRLANIR — bir WiFi parolasi buna mal olamaz")
    r.kosul("  5b: `Ayar3` yapisina ag alani EKLENMEDI",
            "wifi" not in (KOD / "tipler3.h").read_text(
                encoding="utf-8", errors="replace").lower())

    # [!] SIR SIZINTISI: parola kaynak kodda olmamali (ikilide duz metin).
    # ⚠ Desen ONCE `wifi_`/`ap_` oneki istiyordu; `String sifre = "..."`
    #   bicimindeki mutasyon KACTI. Artik adin ICINDE sifre/parola/pass
    #   gecen HER degiskene atanan uzun dize yakalaniyor.
    sabit = re.search(r'\w*(sifre|parola|pass\w*)\s*=\s*"[^"]{4,}"',
                      INO_KOD + AG_KOD, re.I)
    r.kosul("  5c: kaynakta sabit parola YOK", sabit is None,
            sabit.group(0)[:48] if sabit else "kimlik bilgileri NVS'ten")
    r.kosul("  5c: kimlik bilgileri NVS'ten okunuyor",
            'getString("wifi_ad"' in AG_KOD and 'getString("wifi_sifre"' in AG_KOD)
    # ⚠ Adin GECMESI yetmiyor: cagri yeri kalip TANIM yeniden adlansa
    #   iddia yine yesil yanardi (mutasyon KACTI). Govde sinaniyor.
    g_par = kod(govde(AG_H, "static void ag_rastgele_parola"))
    r.kosul("  5c: AP parolasi RASTGELE uretiliyor, MAC'ten TURETILMIYOR",
            bool(g_par) and "esp_random" in g_par
            and "macAddress" not in g_par,
            "SSID zaten MAC son ekini yayinliyor — MAC turevi parola "
            "HICBIR SEY korumaz")
    r.kosul("  5c: WPA2 asgari uzunlugu denetleniyor",
            "< 8" in AG_KOD or "strlen(deg) < 8" in INO_KOD)

    # 🔴 B26 (2026-09-11) — GERCEK KARTTA bulundu, tasarim zinciri
    #    18/18 yesilken GORUNMUYORDU. `ag_baslat()` `ag_ap_ssid()`'yi
    #    `WiFi.mode()`'dan ONCE cagiriyor; kayitli ev agi yokken WiFi
    #    surucusu o ana kadar hic baslamamis oluyor ve
    #    `WiFi.macAddress()` tampona DOKUNMUYOR (ESP_ERR_WIFI_NOT_INIT).
    #    Sonuc: SSID'e ILKLENMEMIS YIGIN BELLEGI giriyordu. Kartin
    #    gercek MAC'i ...:96:9c iken ad `OLCUM-KARTI-ABAB`
    #    cikti (AB AB = dolgu bayti deseni). Deger acilislar arasinda
    #    SABIT kaldigi icin kusur "rastgele ad" gibi de gorunmuyordu.
    g_ssid = kod(govde(AG_H, "static String ag_ap_ssid"))
    r.kosul("  5c: AP SSID'i eFuse MAC'inden (esp_read_mac) turetiliyor",
            bool(g_ssid) and "esp_read_mac" in g_ssid
            and "WiFi.macAddress" not in g_ssid,
            "esp_read_mac eFuse'tan okur, WiFi surucusunun baslatilmis "
            "olmasini gerektirmez; WiFi.macAddress() gerektirir")
    # Kartta sinanan iddianin BAGIMSIZ olcutu: afis, softAP ayaga
    # kalktiktan SONRA okunan GERCEK MAC'i da basmali. Ayni kaynaktan
    # okusaydi tezgah denetimi totoloji olur, eski kusuru kacirirdi.
    # ⚠ Ilk yazimda kosul `"MAC=" in INO` idi ve MUTASYON KACTI: afis
    #   satiri silinse bile `N` komut ciktisindaki kopya iddiayi yesil
    #   tutuyordu. Kosucu AFISI okuyor, `N`'i degil — kapsam setup()'a
    #   daraltildi. (mutasyon.py bunu ilk turda yakaladi.)
    g_setup = govde(INO, "void setup()")
    r.kosul("  5c: ACILIS AFISI gercek MAC'i da ilan ediyor",
            "MAC=" in g_setup and "ag_durum.mac" in kod(g_setup),
            "tezgah_kart.py SSID sonekini AFISTEKI MAC ile "
            "karsilastiriyor; `N` ciktisindaki kopya yetmez")

    r.kosul("  5d: web parolasi YOKSA acilista UYARILIYOR",
            "web parolasi YOK" in INO,
            "sessiz 'guvenlik yok', guvenlik olmamasindan kotudur")
    r.kosul("  5d: ag durumu acilista BASILIYOR",
            "ag_kip_adi" in kod(govde(INO, "void setup()")),
            "DEVIR 4.9 kurali: durum sessiz kalamaz")

    r.kosul("  5e: `N` komut ailesi arayuzden erisilebilir olmali",
            "case 'N'" in INO_KOD,
            "ters yon denetimini test_arayuz3.js yapiyor")


def bolum6(r):
    bolum(r, "BOLUM 6 — ARAYUZ KARTTAN SERVIS EDILIYOR (B22.5)")
    r.bilgi("  Kart artik arayuzu KENDISI sunuyor: 'bilgisayar yoksa'")
    r.bilgi("  senaryosu tamamlaniyor. LittleFS bolumu 0xE0000 = 917 504 B")
    r.bilgi("  ve bugune kadar TAMAMEN BOS duruyordu.")
    r.bilgi("")

    g_setup = kod(govde(INO, "void setup()"))
    r.kosul("  6a: LittleFS baglaniyor", "LittleFS.begin(" in g_setup)
    r.kosul("  6a: OTOMATIK BICIMLENDIRME yok",
            "LittleFS.begin(false)" in g_setup,
            "basarisiz bir yazma 'bos dosya sistemi'ne donusup sebebi "
            "gizlerdi; bos bolum bir HATA degil, kok_sayfa bunu SOYLUYOR")

    i_vendor = g_setup.find('serveStatic("/vendor/"')
    i_kok = g_setup.find('serveStatic("/",')
    r.kosul("  6b: `/vendor/` statik servisi kayitli", i_vendor >= 0)
    r.kosul("  6b: `/vendor/` daha OZEL oldugu icin ONCE kayitli",
            0 <= i_vendor < i_kok,
            "sonra kayitli olsaydi `/` onu golgelerdi")
    r.kosul("  6b: vendor `immutable` (Vue bir kez iniyor)",
            "immutable" in g_setup,
            "58 KB'lik indirme telefonda her acilista tekrarlanmasin")
    # [!] index.html immutable OLMAMALI: yoksa arayuz guncellemesi
    #    tarayiciya HIC ulasmaz.
    kok_bolum = g_setup[i_kok:i_kok + 160] if i_kok >= 0 else ""
    r.kosul("  6b: kok servisi `no-cache` (arayuz guncellemesi gorulsun)",
            "no-cache" in kok_bolum,
            "immutable olsaydi guncelleme tarayiciya hic ulasmazdi")

    # [!] `index.htm` TUZAGI
    g_kok = kod(govde(INO, "void kok_sayfa()"))
    r.kosul("  6c: ACIK kok isleyicisi var (index.htm tuzagi)",
            "index.html.gz" in g_kok and "streamFile" in g_kok,
            "serveStatic dizin istegini `index.htm` ile karsiliyor "
            "(RequestHandlersImpl.h:198), `index.html` DEGIL")
    r.kosul("  6c: goruntu yoksa NE YAPILACAGI yaziliyor",
            "arayuz-yaz.py" in g_kok,
            "bos sayfa birakmak kullaniciyi 'calismiyor' sanisina iter")

    r.kosul("  6d: `enableETag` KULLANILMIYOR",
            "enableETag" not in INO_KOD,
            "calcETag dosyanin TAMAMINI okuyup ozet cikariyor — gondermek "
            "kadar bloklar; `immutable` ayni isi sifir maliyetle yapiyor")

    # ── Toplu uclar: bitisik tampon ve blokaj ────────────────────────
    n = re.search(r"#define PIL_YANIT_NOKTA (\d+)u", INO)
    nokta = int(n.group(1)) if n else 0
    r.kosul("  6e: PIL_YANIT_NOKTA dusuruldu", 0 < nokta <= 200,
            f"{nokta} nokta ~ {nokta * 25} B  (600 iken ~15 KB idi)")
    g_pil = kod(govde(INO, "void pil_sayfa()"))
    r.kosul("  6e: pil ucu PARCALI gonderiyor",
            "sendContent" in g_pil and "CONTENT_LENGTH_UNKNOWN" in g_pil,
            "bitisik 20 KB'lik String, parcalanmis yiginda BASARISIZ olup "
            "sessizce kesik govde uretebiliyordu")
    r.kosul("  6e: pil ucu bitisik buyuk tampon ISTEMIYOR",
            "n * 34" not in g_pil and "n*34" not in g_pil)

    # ── Ikili skop ───────────────────────────────────────────────────
    g_bin = kod(govde(INO, "void skop_bin_sayfa()"))
    r.kosul("  6f: `/skop.bin` ucu kayitli", '"/skop.bin"' in INO_KOD)
    r.kosul("  6f: ikili baslik imzali", "'S'" in g_bin and "'3'" in g_bin
            and "'B'" in g_bin, "kismi yanit sessizce cizilmesin")
    r.kosul("  6f: ikili dokum de PARCALI", "sendContent" in g_bin)
    r.kosul("  6f: Host denetimi ikili ucta da var", "host_gecerli()" in g_bin)
    # [!] Tuketicisi olmayan bir uc yarim istir (B17'nin f/F kusuru).
    g_skop = kod(govde(INO, "void skop_komut(const char *s)"))
    r.kosul("  6g: `tB` — ASCII DOKMEDEN yakalama komutu var",
            "'B'" in g_skop and "skop_yakala()" in g_skop,
            "yoksa WiFi'de ayni veri IKI KEZ tasinirdi (ASCII + ikili)")
    r.kosul("  6g: `tB` onayi `!` ile BASLAMIYOR",
            "* skop yakalandi (ikili)" in INO,
            "arayuz `!` gorunce skop beklemesini IPTAL ediyor")

    # ── Goruntu varlik listesi ───────────────────────────────────────
    uret = (BURASI / "arayuz-uret.py").read_text(encoding="utf-8",
                                                 errors="replace")
    m = re.search(r"VARLIKLAR = \[(.*?)\]", uret, re.S)
    varliklar = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
    html = (KOK / "arayuz3" / "index.html").read_text(encoding="utf-8",
                                                      errors="replace")
    # ⚠ `(?:^|\s)` sart: `:href="kopruAdresi"` bir Vue BAGLAMASI, dosya
    #   yolu degil. Onsuz `:href` de esleserek "goruntude yok" diyordu.
    #   (Ayni kusur test_arayuz3.js'te de cikmisti — iki yerde ayni
    #   deseni yazmanin bedeli.)
    istenen = {u for u in re.findall(r'(?:^|\s)(?:href|src)="([^"]+)"',
                                     html, re.M)
               if not re.match(r"^(https?:|data:|#|mailto:)", u)}
    istenen.add("index.html")
    eksik = istenen - varliklar
    r.kosul("  6h: index.html'in istedigi HER varlik goruntude",
            not eksik, " ".join(sorted(eksik)) or f"{len(varliklar)} varlik",
            )
    r.kosul("  6h: `sahte-kart.js` goruntuye GIRMIYOR",
            "sahte-kart.js" not in varliklar,
            "15 936 B, yalnizca ?demo icin — dinamik iniyor")

    # ── Telefonda uygulama gibi ──────────────────────────────────────
    # ⚠ HTML YORUMLARI CIKARILIYOR. Ilk yazimda `apple-mobile-web-app-
    #   capable` dizesi etiketin USTUNDEKI aciklama yorumunda da geciyordu
    #   ve "etiketi kaldir" mutasyonu KACTI. Bu sinif kusurun bu oturumda
    #   ALTINCI ortaya cikisi (CSS sinifi, NVS imzasi, faz_kal alani,
    #   .uyari govdesi, komut toplayici, simdi de HTML yorumu).
    html_kod = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    r.kosul("  6i: iOS tam ekran etiketi var",
            "apple-mobile-web-app-capable" in html_kod,
            "duz HTTP'de calisiyor; Android'de gercek PWA HTTPS ister")
    r.kosul("  6i: ikon ve manifest bagli",
            "apple-touch-icon" in html_kod and 'rel="manifest"' in html_kod)
    r.kosul("  6i: ikon URETILIYOR, depoda elle konmus ikili degil",
            (BURASI / "ikon-uret.py").exists()
            and (KOK / "arayuz3" / "ikon-180.png").exists())

    # ── Goruntunun bayatligi ─────────────────────────────────────────
    r.kosul("  6j: uretec ve yazici var",
            (BURASI / "arayuz-uret.py").exists()
            and (BURASI / "arayuz-yaz.py").exists())
    kunye = BURASI / "_fs.json"
    if not kunye.exists():
        # Iddia SESSIZCE kaybolmasin: yoklugu ACIKCA raporlaniyor.
        r.bilgi("     _fs.json yok — goruntu henuz uretilmedi "
                "(python arayuz-uret.py). Bayatlik denetimi ATLANDI.")
        r.kosul("  6j: goruntu yoksa bu ACIKCA soyleniyor", True,
                "sessiz atlama degil")
    else:
        import hashlib, json as _json
        k = _json.loads(kunye.read_text(encoding="utf-8"))
        bayat = [ad for ad, ozet in k["kaynak"].items()
                 if not (KOK / "arayuz3" / ad).exists()
                 or hashlib.sha256((KOK / "arayuz3" / ad).read_bytes()
                                   ).hexdigest() != ozet]
        r.kosul("  6j: LittleFS goruntusu GUNCEL", not bayat,
                " ".join(bayat) or f"{len(k['kaynak'])} varlik, "
                f"{k['icerik_bayt']} B, bolumun %"
                f"{100.0 * k['icerik_bayt'] / k['bolum_boyut']:.1f}'i")
        r.kosul("  6j: goruntu bolume SIGIYOR",
                k["icerik_bayt"] < k["bolum_boyut"])


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B22.4 — KARTIN WEB KATMANI")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI ve FIRMWARE'i sinar, kurulmus bir KARTI degil.")
    bolum1(r)
    bolum2(r)
    bolum3(r)
    bolum4(r)
    bolum5(r)
    bolum6(r)
    tamam = r.yazdir()
    # Bu adim FIRMWARE KAYNAGINI siniyor; asagidakilerin hicbiri kaynaktan
    # gorulemez. Once yalnizca docstring'de gomuluyduler — ekrana hic
    # cikmiyorlardi (B23.1'in duzelttigi kusur).
    tezgah("B22b Kart web katmani", [
        ("Kart gercekten WiFi'ya baglaniyor mu (STA -> AP dusmesi)",
         "Acilista `Ag: STA (ev agi)` ya da `Ag: AP (kendi agi)` yazmali. "
         "10 s'de STA olmazsa AP'ye dusmeli; AP parolasi seri konsola basilir"),
        ("mDNS telefonda cozuluyor mu",
         "http://olcum.local acilmali. Android'de Chrome `.local`'i "
         "guvenilir cozmuyor (12+ ve degisken) — cozulmezse AP'nin SABIT "
         "192.168.4.1'i kullanilacak, bu bir kusur DEGIL"),
        ("CSRF savunmasi gercek tarayicida",
         "Baska bir makinede `<img src=http://<kart-ip>/komut?k=p>` iceren "
         "sayfa ac. Istek karta ULASMAMALI. Ulasiyorsa POST+X-Olcum "
         "savunmasi calismiyor demektir"),
        ("collectHeaders gercekten toplaniyor mu",
         "`curl -X POST --data-binary '?' http://<ip>/komut` (basliksiz) "
         "-> HTTP 400. 204 donerse baslik denetimi SESSIZCE olmus demektir"),
        ("esp_wifi_start() <-> adc_continuous_start() carpismasi",
         "Skop yakalarken WiFi'yi kopar/bagla (DEVIR 7.1 (1), esp-idf#12749). "
         "Beklenen kusur: `! tetiklenemedi` ya da sifir dolu DMA tamponu. "
         "Bugunku baslatma sirasi TESADUFEN guvenli"),
        ("SSE loop()'u ne kadar blokluyor",
         "Iki sekmede /akis acikken `D` satirindaki ornek sayisi ve "
         "`K` satirindaki loop_azami_us. `K` > 20 000 us ise cift cekirdek "
         "karari TETIKLENIR (5.12.34)"),
        ("LittleFS gercekten baglaniyor mu",
         "Acilista `Arayuz: LittleFS'te` yazmali. `begin(false)` — otomatik "
         "bicimlendirme YOK, yani bos bolum sessiz kalmaz"),
        ("serveStatic ve index.htm tuzagi",
         "`http://<ip>/` tam arayuzu vermeli (acik kok isleyicisi). "
         "`/vendor/vue.global.prod.js` ikinci yuklemede 304/onbellekten "
         "gelmeli — `immutable` calisiyor mu"),
        ("Telefondan ilk yukleme suresi",
         "93 753 B gzip. 3 s'yi gecerse panel cikarma adimi acilir "
         "(5.12.38). Ikinci acilista statik trafik 0 B olmali"),
        ("arayuz-yaz.py ile karta yazma",
         "esptool yolu ve 0x310000 ofseti HIC denenmedi. "
         "`python arayuz-uret.py && python arayuz-yaz.py`"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
