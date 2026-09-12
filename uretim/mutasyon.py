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

    # ── B22a · PC koprusu
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     'SERBEST_KOMUTLAR = {"p0"}', "SERBEST_KOMUTLAR = set()",
     "p0 (pil desarjini DURDUR) her zaman parolasiz gecmeli — "
     "emniyet ozelligi, kolaylik degil"),
    ("B22a", "test_kopru.py", "kopru/arsiv.py",
     "def ham_satirlar", "def ham_satirlar_",
     "role BAYT-SEFFAF olmali; arsivin ham okuma yolu kaybolursa "
     "girdi/cikti karsilastirmasi yapilamaz"),

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
     "  if (xQueueSend(akis_kuyrugu_q, &ak, 0) != pdTRUE) akis_tasma++;",
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
     "  Serial.setTxBufferSize(2048);\n  Serial.begin(115200);",
     "  Serial.begin(115200);\n  Serial.setTxBufferSize(2048);",
     "begin()'den SONRA cagrilan setTxBufferSize ise yaramaz; `?` "
     "ciktisi yine 27 ms bloklar"),

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
     "    iki = alert_dener(ADS_GERILIM, etkin_kanal()->pga, &sure2);",
     "    iki = false;",
     "prob yalnizca #1'i dener: tel YANLIS MODULDE ise 'tel yok' ile "
     "ayni cikti gelir ve kullanici bosuna arar"),
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "      Serial.print(F(\" istenen=\"));      Serial.print(istek);",
     "",
     "CAL ciktisi yalnizca istenen frekansi basar; skop olcumu kendi "
     "varsayimiyla dogrulanir (LEDC 7000 -> 6998 kirpiyor)"),

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
