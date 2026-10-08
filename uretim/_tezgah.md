# Tezgahta olculecekler — URETILMIS liste

Bu dosya `dogrula3.py` tarafindan uretiliyor. **Elle duzenleme.**
Her kalem, onu dogrulayamayan adimin yaninda yaziyor;
yeni bir kalem eklemek icin o adimin `tezgah(...)` cagrisina ekle.

## Ilk gun

Bu 22 kalem `[!]` ile isaretli: kart calisir calismaz, digerlerinden ONCE.

> Asagidaki sira ZINCIR sirasi, oncelik sirasi DEGIL — kalemler arasinda elle bir siralama tutulsaydi yine bayatlardi. Hepsi ilk gun yapilacak; hangisinin once oldugu kalemin kendi kabul olcutunde yaziyor (orn. *bedava test*, *kart calisir calismaz*).

| # | Adim | Olcum |
|---|---|---|
| 1 | B18 GPIO kelepceleri | +3V3 rayinin GERI BESLENMESI |
| 2 | B19 Skop kanali | ON UC KURULUNCA: hizli yol SIFIR kalibrasyonu |
| 3 | B19 Skop kanali | Skop yakalamasi — `python tezgah_blokaj.py --skop` |
| 4 | B17 ADS es zamanliligi ve faz | Faz kalibrasyonunun TASINABILIRLIGI |
| 5 | B20 Ornekleme hizi ve bant | `D` satirindaki ORNEK SAYISI — ilk, en ucuz ve en onemli test |
| 6 | B20 Ornekleme hizi ve bant | `K` ve `F` satirlari — blokaj artik CIFT CEKIRDEKTEN SONRA |
| 7 | B21 Pil kapasite testi | FAILSAFE — kart calisirken RESET at |
| 8 | B21 Pil kapasite testi | BAYPAS denetimi — yuku bilerek J3'e bagla |
| 9 | B22a PC koprusu | SKOP ARSIVI gercek kartta — `python tezgah_skop_arsiv.py` |
| 10 | B22a PC koprusu | TARAYICIDA — `python tarayici_skop_arsiv.py --goruntu` |
| 11 | B22b Kart web katmani | Coklu ag CA6: kart acikken bagli ag KAYBOLUR (tasarim/2026-10-06-coklu-ag.md) |
| 12 | B25 Kart bringup kosucusu | Kosucunun kendisi gercek kartta calisiyor mu |
| 13 | B72 Kayit firmware + esitleme | ADS takilinca: GERCEK bir kalibrasyon adimi |
| 14 | B72 Kayit firmware + esitleme | Gecmis doluyken tarama suresi |
| 15 | B72 Kayit firmware + esitleme | ADS takilinca: GERCEK pil testi kaydi |
| 16 | B72 Kayit firmware + esitleme | Skop girisine CAL bagliyken osiloskop gunlugu (1C-3) |
| 17 | B72 Kayit firmware + esitleme | ADS takilinca: gercek 500/s ayrintili kayit |
| 18 | B72 E6F dahili yigin duzeltmesi (kartta) | Ag geri donusu: erisim noktasi gidip gelince kart STA'ya kendiliginden doner |
| 19 | B73 ortak/ (JS hesap kodu) | Telefonda PBKDF2 suresi (Capacitor WebView) |
| 20 | B7 Arayuz | Arayuz tarayicida GERCEKTEN dogru gorunuyor mu |
| 21 | B9 Malzeme listesi | Direnc adetleri SAYIM degil goz karari |
| 22 | B48 Yerlesim plani | BJT/TL431/7912 bacak sirasi multimetrenin diyot kademesiyle |


## B1 On uc tasarimi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 1 | TL072'nin gercek ofseti ve suruklenmesi | Girisi kisa devre yapip cikisi olc; veri sayfasi tipik degeri 3 mV, en kotu 6 mV. Hata butcesi bu sayiya dayaniyor |
| 2 | 4.9 M ohm'luk zincirde nem ve kacak akimlari | Nemli gunde ve kuru gunde ayni gerilimi olc. Fark %0.5'i gecerse zincir konformal kaplama ya da daha dusuk direnc ister |
| 3 | Delikli plakette 615 V icin iletken araligi | IPC-2221 kirlenmis yuzey: 615 V icin >= 3 mm. Lehim koprusu olasiligi da gozle denetlensin |
| 4 | ADS giris empedansinin sicaklikla suruklenmesi | Kart isindiginda (30 dk calistir) ayni girisin okumasi kaymamali; kayma PGA'ya bagli giris empedansindan gelir |

## B2 Analog on uc

| # | Olcum | Kabul olcutu |
|---|---|---|
| 5 | Bolucu NEGATIF girise gercekten dogrusal mi | Vref'e referansli bolucu -615 V'ta da dogrusal olmali. Asama 2'de negatif taraf HIC simule edilmemisti (DEVIR 4.13). Olcum: -100 V uygula, ADS dugumunu voltmetreyle oku, hesaplanan degerle karsilastir |
| 6 | BAT85'in GERCEK Vf'i ve ters kacagi | Modeldeki 400 mV @ 10 mA ve 2 uA @ 25 V veri sayfasi MAKSIMUMU, tipik degil. Delikli DO-34 cam govde partiden partiye oynar. Kelepce ariza akiminin ne kadarini aldigi buna bagli |
| 7 | ADS yolu RC kesimi gercekte kacta | Hesap 55.7 Hz. Gercek C2 %10 tolerans + kablo kapasitesi ile kayabilir. Olcum: sinyal jeneratorunden supurme, -3 dB noktasi. Kaymasi B16'nin V/I eslesmesini dogrudan bozar |
| 8 | Sallen-Key f0 ve Q | Hesaplanan f0 ve Q ancak direnc/kondansator toleransi kadar gerceklesir. Q beklenenden yuksek cikarsa gecis bandinda tepe olusur ve skop dalga sekli SISIRILMIS gorunur |

## B15 Ariza ve zorlama

| # | Olcum | Kabul olcutu |
|---|---|---|
| 9 | Bir direnc asiri yukte ACIK mi KISA mi devre kaliyor | Butun ariza matrisi ACIK devre varsayiyor. KISA kalirsa koruma zinciri ters yonde calisir. Olcum: feda edilecek bir 1/4 W direnci bilerek yak, sonra ohmmetreyle bak |
| 10 | Gercek LM358 giris jonksiyonunun kirilma gerilimi | Makromodelde bu yok. Veri sayfasi mutlak maksimumu veriyor ama kirilma noktasini vermiyor. Ariza akimi buna gore akar |
| 11 | Delikli plakette 615 V'ta ark ve yuzey kacagi | Simulasyon yalnizca IDEAL yalitim biliyor. Olcum: HV bolumu besle, karanlikta korona ara, nemli gunde tekrarla. Ark varsa iletken araligi acilacak |
| 12 | Emniyet uyarilari kartin USTUNDE yaziyor mu | Ariza matrisinin yarisi KULLANICI hatasi. J7/J3 baypasi ve 615 V ucu, kartin uzerinde etiketli olmali — belgede olmasi tezgahta ise yaramiyor |

## B11 Besleme rayi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 13 | 24 V kaynak GERCEKTEN yalitimli mi | Olcum: kaynak fisi TAKILIYKEN cikis ucu ile sebeke topragi arasi ohmmetre. Yalitimsizsa 615 V bolumu sebeke potansiyeline oturuyor ve butun izolasyon varsayimi cokuyor |
| 14 | Kaynagin gercek gerilimi ve yuk altinda sarkmasi | 24 V nominal; %10 sapma raylari +-13.2/-13.2 V'a tasir. Olcum: bos ve tam yukte voltmetre |
| 15 | 7912'nin gercek jonksiyon sicakligi | Orta nokta dengesizligi ~15 mA ve 7912 uzerinde ~12 V dusuyor. Olcum: 10 dk calistir, govdeye parmakla dokunulamiyorsa sogutucu sart |
| 16 | Ray SIRASI onemli mi | +-12 V acikken +3V3 kapaliysa B18'in geri besleme hali dogar. Olcum: once 24 V tak, sonra USB — +3V3 rayini voltmetreyle izle, 3.60 V'u ASMAMALI |

## B16 V/I suzgec eslestirmesi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 17 | Iki kanalin gercek kesim frekanslari eslesiyor mu | Hesap ikisini de ~55.7 Hz'e getiriyor. Olcum: her iki kanala ayni 50 Hz sinusu ver, faz farkini skopla oku. Fark 1 dereceden buyukse C18 ya da R degeri yanlis |
| 18 | C18 gercekten takildi mi ve degeri dogru mu | Ortusme (aliasing) korumasinin TEK parcasi. Yoksa 430 Hz ustundeki her sey katlanip olcume girer ve firmware bunu AYIRT EDEMEZ — geri donusu yok |
| 19 | Reaktif yukte guc okumasi | Direncli yukte hata KENDINI GOTURUYOR, o yuzden direncli yuk bu kalemi DOGRULAMAZ. Olcum: motor ya da trafo gibi PF<1 bir yuk baglayip wattmetre ile karsilastir |

## B18 GPIO kelepceleri

| # | Olcum | Kabul olcutu |
|---|---|---|
| 20 | [!] +3V3 rayinin GERI BESLENMESI | En kritik olcum. USB'yi CIKAR, 24 V kaynagi TAKILI birak, +3V3 rayini voltmetreyle oku. Beklenen ray 1.670 V, ESP32 siniri 3.60 V, yani pay 1930 mV. 3.60 V'a yaklasiyorsa R41 ya da 10K seri dirençlerden biri YOK demektir (B18/F12 oncesi pay 18 mV idi) |
| 21 | Acma SIRASI her iki yonde de guvenli mi | Yukaridaki olcumu iki sirayla da yap: once USB sonra 24 V, sonra tersi. Ikisi de gecmezse talimat degil DEVRE degisecek |
| 22 | R41'in gercek degeri ve isinmasi | Geri besleme akimini sinirlayan parca. Olcum: devreden cikarip ohmmetre, sonra hata halinde 10 dk isinma |

## B19 Skop kanali

| # | Olcum | Kabul olcutu |
|---|---|---|
| 23 | 🔴 ON UC KURULMADAN ONCE: GPIO4-GPIO5 kopru telini ve RC duzenegini (2x10K + 2x100nF, GPIO10'dan) SOK | B38 supurmesi icin GPIO4 ile GPIO5 AYNI satira baglandi. Gercek devrede GPIO4 skop/GERILIM, GPIO5 hizli AKIM kanali: kisa devre kalirsa iki op-amp cikisi birbirine baglanir ve guc/PF olcumu ANLAMSIZ olur (V ve I ayni sinyal -> PF=1.0000, kartta goruldu). RC duzenegi de skop girisini 20K ile yukler |
| 24 | [!] ON UC KURULUNCA: hizli yol SIFIR kalibrasyonu | B39 hizli yolu eFuse tablosuyla olcekliyor (dogrusal model sifir giriste -6.93 V / -397 mA veriyordu). Kalan belirsizlik ~22 mV kesme (eFuse ofseti mi rail mi, multimetresiz ayrilamadi) = girisde ~0.8 V / ~47 mA. Girisleri kisa devre et, `w` Vort/Iort oku: sifirdan sapma bu belirsizligin kendisi. Firmware'de hizli yol icin sifir kalibrasyonu HENUZ YOK |
| 25 | Hizli yol olceklemesi — `python tezgah_adc_supur.py --hizli` | GPIO4+GPIO5 ayni RC dugumundeyken: Vort ve Iort'tan geri cikarilan dugum gerilimi <= 2 mV uyusmali (2026-09-13: 0.39 mV), dugum-gorev egimi ~3296 mV (olculen 3302). Firmware olcekleme degisince tekrar kosun. NOT: `w` olcum dongusunu ~34 ms blokluyor (cekme sinamasi dahil; B37'de 123 ms idi) |
| 26 | GPIO5 dogrusalligi — OLCULDU (2026-09-13, B38) | `python tezgah_adc_supur.py --adim 10 --csv olcum-adc-supurme.csv`. GPIO5 rms 18.2 kod = GPIO4 rms 18.2 kod: egrilik KANALA degil DONUSTURUCUYE ait, B36'nin eFuse duzeltmesi GPIO5'e de gecerli. Kanaldan kanala -0.26 +- 0.75 kod. Tekrar gerekirse: ayni duzenek, analiz kartsiz `--analiz olcum-adc-supurme.csv` |
| 27 | Bos-pin sinamasi GERCEK on ucla — `wB` | B37 esigi %75, bos %100 ve RC duzenegi %41-50 OLCULEREK secildi; gercek on uc (op-amp cikisi ~%0, skop bolucusu ~%10) HESAPLANDI, olculmedi. On uc lehimlenince `wB` kosun: iki kanal da 'surulu' ve %25'in altinda olmali |
| 28 | I2C kenarlarinin skop orneklerine sizmasi — PCB'de yeniden olc (B44) | B44 kuplaj deneyi (2026-09-13): hata YUKLU HATTAN geliyor, pinden degil (I2C'yi GPIO41/42'ye tasimak COZMEDI: 1.26/1000, 8/9'da 2.22); tel yakinligindan da degil (teller ayrilinca 3.24); KENAR HIZINDAN: ayni hatta zayif surus d0 1.26, varsayilan d2 4.80, d3 4.44. Mekanizma: yuklu hattin kenar akimi ESP32'nin kendi rayini sarsiyor. Zayif surus 4x azaltiyor, sifirlamiyor -> yakalamada ADS susturma KALIYOR. PCB'de: SDA/SCL'ye seri direnc (33-100 ohm) + tek pull-up seti (moduldeki cift 10K'lar degil) + zayif surus; sonra `python tezgah_kuplaj.py --asama 3 --karisik --cal-kapali --tekrar 20` ile yeniden olc. K1 K0 duzeyine inerse ADS susturmasi kaldirilabilir (o zaman `tezgah_blokaj --skop` ADS SUSTURULMADAN 0 hata vermeli) |
| 29 | [!] Skop yakalamasi — `python tezgah_blokaj.py --skop` | Bes sey sinaniyor: (1) TEK-ORNEK HATASI <= 1/3721 (CAL KAPALI — B44: PWM kenari da hata sokuyor, 20 kHz ile kosan eski hali 11/3721 verdi) — B40b bunu 3-9/1000'e bozmustu ve zincir yakalayamamisti; (2) komut dongusu <= 20 ms (B40 oncesi 4437 ms); (3) ADS susmasi `ads_duraklama_ms` ile yakalama suresi kadar SAYILIYOR; (4) B42: TETIK ORNEGI on-tetik ayarinin TAM yerinde ve gercek bir esik gecisi (`--tetik`); (5) B43: OLCUM SATIRI dalganin kendi kodlarindan arayuz kuraliyla hesaplananla <= 2 mV, ikili yolda M satiri onaydan once ve /skop.bin'le ayni (`--olcum`, WiFi erisimi gerekli); (6) B47: TETIK ONAYI A/B — tK8,9 igneleriyle onay=1 tetikler (>0), onay=2 tetiklemez (0); gercek sinyalde iki kipte de tetik idx == on (`--onay`). (4)-(6) CAL 1 kHz + RC duzenegi istiyor. 2026-09-13/14: tetik 0/30 -> 30/30, olcum 0/4 -> 4/4, onay 17/20 -> 0/20. Firmware'de skop/ADC/I2C/Serial'e dokunan her degisiklikten sonra tekrar kosun |
| 30 | WiFi'de `tB` uctan uca (web parolasiyla, tarayicidan) | Parola depoda yok, bu yuzden Claude KOMUT ucunu sinayamadi; yaris seri tetik + WiFi `/skop.bin` ile yeniden uretildi: eski arayuzun 400 ms beklemesi tb7'de 503 aldi, onay satiri beklenince 200/1000. Elle: tarayicida karta dogrudan baglan, zaman tabani 200 ms/bol, `Yakala` -> dalga cizilmeli, hata bildirimi CIKMAMALI |
| 31 | Bosta blokaj — `python tezgah_blokaj.py --sifirla --tekrar 4` | Tek 45 s penceresi yaniltir: acilis gecisi ~16 ms, kararli hal ~3 ms. `?` komutunun bedeli 2026-09-13'te 21.9 ms olculdu (TX halkasi ogesi ek yuku); 8 KB tamponla 5.8 ms. Firmware'e cikti ekleyen her degisiklikten sonra tekrar olcun |
| 32 | Skop girisi VREF'i ne kadar kaydiriyor (capraz konusma) | Skop akimi artik GND'ye degil VREF'e gidiyor ve VREF BUTUN kanallarin referansi. Olcum: skop girisine 40 V ver, GERILIM kanalinin okumasi degisiyor mu bak — degisiyorsa VREF tamponu yetersiz |
| 33 | Gercek menzil -63.5 .. +46.8 V mi | R23 2.7K'ya dusuruldu. Olcum: her iki uctan da sinira yakin DC ver, kirpma noktalarini oku |
| 34 | Cozunurluk kaybi kabul edilebilir mi | Adim 28.8 mV (tek yonluyken 11.9 mV idi; ikisi de NOMINAL tam olcekten). Olcum: kucuk genlikli (1 V tepe) bir dalga sekli cizdir, basamaklanma goze batiyorsa karar yeniden gorusulecek |

## B17 ADS es zamanliligi ve faz

| # | Olcum | Kabul olcutu |
|---|---|---|
| 35 | [!] Faz kalibrasyonunun TASINABILIRLIGI | Direncli yukte USB'den `F` ile kalibre et, sonra AYNI yuke WiFi ile bak. PF farki > %0.5 ise B22.1'in us duzeltmesi eksik ve faz hala periyoda bagli demektir |
| 36 | Kondansator tolerans harfi (J=%5, K=%10) | Gucun gecerlilik bandini bu belirliyor. Kutudaki harfi oku; K ise en kotu tau eslesmezligi 292.8 us |
| 37 | Sontun guc degeri | +-11.5 A rakami 2 W CIKARIMINDAN geliyor. Uzerindeki degeri oku; dusukse akim tavani duser |
| 38 | Direncli yukte PF gercekten 1'e yakin mi | `w` komutu. PF < 0.99 ise suzgec eslesmezligi kalibre edilmemis demektir — once `F` ile duzelt |

## B20 Ornekleme hizi ve bant

| # | Olcum | Kabul olcutu |
|---|---|---|
| 39 | [!] `D` satirindaki ORNEK SAYISI — ilk, en ucuz ve en onemli test | 200 ms'de 104 +-10 beklenir (model 1917 us/cevrim). KARTTA OLCULDU 2026-09-12: 95-96. ~32 cikarsa ALERT teli dusmustur (`#` komutu soyler), ~19 cikarsa B20'nin kendi duzeltmeleri cokmus demektir |
| 40 | `Wire` gercekten 400 kHz mi | Skopla SCL periyodunu olc. Dolayli kanit VAR: cevrim fazlari (`F` satiri) bit sureleriyle tutarli ve islem basina ek yuk 69 us olculdu. 100 kHz'e duserse V/I kaymasi DORT KAT buyur ve faz butcesi gecersizlesir |
| 41 | ALERT/RDY DARBE mi MANDAL mi — CEVAPLANDI (B26), dogrulamasi kaldi | Tezgahta olculdu: pin donusum bitince LOW'a cekip OYLE KALIYOR (mandal); geri kaldiran sey YENI donusumu baslatan ayar yazmasi, donusum yazmacini okumak DEGIL. `yeni_donusum_bekle` bu siraya gore yazildi. Skopla teyit etmek yine de iyi olur |
| 42 | /HAZIR hattinda harici pull-up gerekiyor mu | Dahili ~45 kOhm ile 400 kHz'te CALISIYOR (kartta: RDY dususu 1229 us'te gorunuyor, rdy_asim=0). En kotu yukselme hesabi 11.1 us. Skopta kenar yavas gorunuyorsa stoktaki 10K eklensin |
| 43 | `t_kayma_us` — OLCULDU, model duzeltildi (B29) | Kartta 152 us (kod yorumu '~95 us' diyordu — bit suresi; fark `Wire`in islem basina sabit maliyeti). Kod zaten VARSAYMIYOR, OLCUYOR ve Lagrange'a veriyor. Duzeltme olmasaydi 50 Hz / PF=0.5 yukte hata %8.35 olurdu |
| 44 | [!] `K` ve `F` satirlari — blokaj artik CIFT CEKIRDEKTEN SONRA | Cift cekirdek B28'de YAPILDI (5.12.44): olcum cekirdek 1'de, web cekirdek 0'da. Kartta olculdu: sayfa yuklenirken loop_azami 186 ms -> 3.8 ms, bosta 3.0 ms. Yeni olcut: `K`'nin ikinci alani birkac ms'i asiyorsa ya da `F` satirindaki `rdy_asim` sifirdan buyukse bir sey bozulmus demektir |

## B21 Pil kapasite testi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 45 | [!] FAILSAFE — kart calisirken RESET at | Yuk KESILMELI. Kapi R42 ile GND'ye cekili, ESP32 olurse MOSFET kapanmali. B21'in EN ONEMLI tezgah testi; gecmezse pil testi hic kullanilmamali |
| 46 | [!] BAYPAS denetimi — yuku bilerek J3'e bagla | Test REDDEDILMELI. J3 dogrudan sonte gidiyor; oraya baglanirsa MOSFET baypas olur ve kesme CALISMAZ. Sessiz hatayi yakalayan tek sey bu |
| 47 | Kesme gecikmesi | `p1` kosarken bir istemciyi askiya al ve kesme gerilimine in. Fazla desarj < 0.5 mAh olmali — yani kesme loop() blokajina BAGLI OLMAMALI |
| 48 | MOSFET'in uzerindeki logo | Veri sayfasi ikincil kaynak (INCHANGE). Farkli bir uretici cikarsa Vdss ve Rds(on) yeniden denetlenmeli |
| 49 | Kapi gerilimi — yuk acikken Vgs | ~11.8 V beklenir. Dususe Rds(on) buyur, MOSFET isinir |
| 50 | Tas direncin gercek degeri ve isinmasi | 4.7-7.5 ohm / 10 W. Elle olc; 30 dk desarjda sicakligina bak |
| 51 | [PT] 18650 + 3.3 ohm, kesme 3.0 V (kullanicinin 2 s'de biten testi) | Once 5 s yuksuz (OCV, /pil evre=ocv), sonra yuk; test SAATLER surmeli, 2 s'de bitmemeli. Bitiste PIL_SONUC v_son ~3.0 V (EMA), anlik dip degil. Pd0'da yuk hic kesilmez; Pr0'da kayitta AYRINTI ornekleri + 1/s nokta |
| 52 | [HT] Hat direnci telafisi — multimetreyle `Ph` | Pil testi surerken (I >= 0.1 A) multimetreyi pilin KENDI kutuplarina tut: R = (V_multimetre - V_kart) / I, `Ph<mohm>`. Sonra /pil vson multimetreyle +-10 mV, v_ham degismemis; Canli D satiri ve akim AYNI kalmali (telafi yalniz pil testinde). Kullanicinin olcumu: kart 3.793 V, multimetre 3.966 V, 1.128 A -> ~153 mOhm |
| 53 | Sarj yonunde test | Sayac ISARETLI ama sarj kaynagi yok — mAh geri saymali. Kaynak bulununca denenecek |

## B58f Kutu besleme zinciri

| # | Olcum | Kabul olcutu |
|---|---|---|
| 54 | PIL acilisinda kutu aciliyor mu (DW01A + B0505S'in gercek asiri yuk davranisi) | Yeni olcum DEGIL — 10.5'in ilk enerjisinde zaten gorulur: ESP32 acilir, GUC lambasi yanar, klemenste 24 V. Acilmazsa 10.5'teki yordam (PIL kapat-ac / doldur / TP4056 yedegi) |

## B22a PC koprusu

| # | Olcum | Kabul olcutu |
|---|---|---|
| 55 | SeriKart gercek baud'da calisiyor mu | `python kopru/kopru.py --port COMx` -> `D` satirlari akmali. Bozuk karakter gelirse DCB alan duzeni ya da baud yanlis |
| 56 | DTR/RTS kart RESET atmiyor mu | Kopru acilinca kart yeniden BASLAMAMALI (acilis banneri gorunmemeli). Iki hat da bilerek DISABLE; reset atiyorsa devre otomatik-reset'e bagli ve pil testi kopru acilisinda OLUR |
| 57 | 4A: panel http://olcum.localhost:8770 (stok-takip ile carpisma yok) | `kopru/PC Baslat.bat` -> tarayici olcum.localhost:8770'i acmali, panel kendiliginden baglanmali (stok-takip 127.0.0.1:80; farkli port, farkli ad). 2026-10-03 COM6'da kosuldu: VID secimi COM6 (1A86), akista D satirlari, Host denetimi, mesgul port mesaji 'PC kopru bu portu kullaniyor', ikinci kopya acilmadi |
| 58 | 4A: telefon `--lan` ile SALT OKUMA | `python kopru/pc.py --lan` -> telefondan http://<PC-IP>:8770 canli olcumu gostermeli; `p0` (DURDUR) gecmeli, baska her komut 403 'yerel agdan salt okuma'. Komut icin telefon karta DOGRUDAN baglanir (olcum.local). Iki tarayici ayni anda izlerken YALNIZCA bu bilgisayardaki surucu olmali |
| 59 | 4A: Baslangic kisayolu | `kopru/Otomatik Baslat Kur.bat` -> oturumu kapat/ac -> pythonw arka planda, olcum.localhost:8770 acilir; kart takili degilken de acilir, takilinca akis baslar. `Otomatik Baslatmayi Kapat.bat` kisayolu siler (kurulum kullanicinin). ⚠ Kurulum YALNIZ ana calisma agacindan (projeler/olcum-karti), gecici dal agacindan degil (betik worktree'yi reddeder). Durdurma: `kopru/Kopruyu Durdur.bat` |
| 60 | 4A: USB kablosu cek / tak | Kopru acikken kabloyu cek: akista BIR KEZ '! kopru: kart baglantisi koptu'; tak: '* kopru: kart baglandi' ve D satirlari geri gelir. ReadFile'in kopmada FALSE dondugu gercek CH343'te SINANMADI (OtoSeriKart sahte kartla sinaniyor) |
| 61 | 4B: kopru kartla WiFi'den ESLESMIS CIHAZ olarak (firmware A3-4B) | Once bir kez `python kopru/imza.py esles --host olcum.local --ad <bu-PC>` (WEB parolasi). USB kablosu takili DEGILKEN `kopru/PC Baslat.bat` (ya da `python kopru/pc.py --usb-yok`: COM portu acilmaz): akista '* kopru: ... yukari-akis WiFi' + '* kopru: WiFi baglandi', D satirlari; komut (ör. `?`) imzali gider, `p0` imzasiz. Kablo takilinca USB'ye doner ('WiFi baglantisi kapatildi'), cekilince WiFi'ye (KALAN: kablo cek/tak elle). Kopru + karta dogrudan 3 tarayici = 4 yuva, hicbiri reddedilmez; 5. istemci `event: dolu` — 4G'de koşuldu (`tezgah_pc.py --o5`: kopru 1 yuva, kullanicinin Chrome'u 1, dogrudan 2, sonraki dolu) |
| 62 | 4G: GERCEK KART KABULU — `python uretim/tezgah_pc.py --o3` ve `--o5` | 2026-10-03 A3-4B: Ö3 11/11 (kopru 202 s kapali, bosluk 59 kayit 4.5 s'de, arsiv bagimsiz indirmeyle bayt bayt ayni 1 311 112 B), Ö5 + izleyici + p0 14/14 (kopru<->kart kaydinda K / araci bilgisi / Authorization 0; 6 sekme 1 yuvada; p0 5/5 204 <= 246 ms). Kopru, firmware ya da kart_wifi degisince TEKRAR kosun. ⚠ Ö3 kullanicinin GERCEK arsivine yazar ve karta ONAY yollar; Ö5 web parolasini yalniz OLCUM_PAROLA verilirse arar. Kopru KAPALIYKEN baslatin (betik acik kopruyu reddeder) |
| 63 | 4C: arka plan esitlemesi gercek kartta (ONAYLI ilk kosu bekliyor) | 2026-10-03 A3-4B, `pc.py --usb-yok --onaysiz` (gecici OLCUM_PC_DIZIN): 2234 kayit / 1 268 956 B / son sira 61276 / 44 oturum, kartin /kayit/listesiyle ayni, 29.6 s; canli akis hizi bosta ile ayni (spec 4C tablosu). ONAYLI kosu 4G'de yapildi (Go gitti, kart dogruladi, PC arsivi kartin akisiyla bayt bayt ayni). KALAN: PC'deki kayitlar.kyt == kartin FLAS bolumu (tezgah_kayit.py --esit, COM6 + kopru kapali); USB takiliyken (SecmeliKart USB) esitlemenin WiFi'den surdugu; kart kapatilip acilinca yeniden baglanma tetigiyle <= 10 s'de tur |
| 64 | 4E: PC'de Windows bildirimi + Ö4 PC karsiligi (PC18: hedef 10 s, kabul 15 s) — GERCEK aracida | Kopru ana agactan acikken (`kopru/PC Baslat.bat`; kart eslesmis, kartta MQTT ayarli) karta kayit baslat (`Gb1000`), kartin FISINI CEK (USB + pil kapali): saniye olcerle 'Ölçüm kartı — Karttan haber yok' bildirimine kadar gecen sure <= 10 s hedef, <= 15 s kabul (10 tekrar; aracinin ilani ~7.5 s + PC). Karti geri tak: AYNI bildirim 'Kart yeniden bağlandı — kayıt sürüyor' olmali (Bildirim merkezinde tek kart). Ev interneti: modemin WAN kablosunu cek (kart ve PC ayni agda): 'Ev interneti koptu — kart çalışıyor'. `Qt` (USB) -> 'Deneme bildirimi'. ⚠ 'Rahatsız Etmeyin' aciksa acilir pencere CIKMAZ (Bildirim merkezine duser): Ayarlar > Sistem > Bildirimler > Öncelikli bildirimler'e 'Ölçüm kartı' eklenebilir. Araci parolalari yalniz kullanicida — olcumu kullanici yapar |
| 65 | p0 (DURDUR) izleyiciden de geciyor mu | Surucu OLMAYAN sekmeden pil testini durdur. Gecmeli — bu bir kolaylik degil EMNIYET karari |
| 66 | [!] SKOP ARSIVI gercek kartta — `python tezgah_skop_arsiv.py` | Bu betikteki skop iddialari `KayitKart` ile kosuyor, yani kartin `t` yanitini BEN yaziyorum: protokol sinaniyor, KART sinanmiyor. Gercek kartta 2026-09-12'de kosuldu ve 16/16 gecti (1000 ornek 1.07 s, arsive dustu, geri okunan kayit bayt-bayt ayni). Firmware ya da kopru degisince TEKRAR kosun |
| 67 | [!] TARAYICIDA — `python tarayici_skop_arsiv.py --goruntu` | Bolum 16'daki iddialar KAYNAK METNINDE arama yapiyor; sayfanin acildigini kanitlamiyor (B22.0'da zincir 15/15 yesilken arayuz tarayicida HIC acilmiyordu). Bu betik gercek tarayici + gercek Vue + sahte kopru ile 14/14 kosuyor ve iki ekran goruntusu birakiyor. Arayuz ya da kopru ucu degisince TEKRAR kosun |
| 68 | Tarayicida: kayit listesi + arsiv seridi (elle) | Kopruye bagli tarayicida Osiloskop gorunumu -> `Yakala` -> kayit **Kayitlar** bolumunde belirmeli. Bir kaydi acinca tuvalin ustunde ARSIV seridi cikmali ve `Canliya don` calismali. Karta DOGRUDAN bagliyken bu bolum HIC gorunmemeli (olu dugme) |

## B22b Kart web katmani

| # | Olcum | Kabul olcutu |
|---|---|---|
| 69 | [!] Coklu ag CA6: kart acikken bagli ag KAYBOLUR (tasarim/2026-10-06-coklu-ag.md) | Kart telefonun hotspotundayken hotspotu KAPAT: ~30 s sonra `Ag: AP (kendi agi)` ve HEMEN tarama; goruyorsa diger kayitli aga (ev agi) `Ag: STA` — kronometreyle kapatmadan STA'ya hedef <= ~60 s (tipik ~40 s; firmware A3-CA3, 2026-10-07; A3-CA2'de ~2:30 olculdu); kendi agi 5 s sonra kalkar. 2026-10-07'de kartta Ng gecisi (7-13 s), geri gecis ve yanlis parolada 20 s'de geri donus OLCULDU; bu yol olculmedi |
| 70 | Coklu ag: iki kayitli ag gorunurken ACILIS secimi | Iki ag da acikken karti sifirla: setup en son baglanilani dener (w_son); baglanirsa kalir. En son baglanilani KAPATIP sifirla: tarama diger agi secmeli (<= ~15 s STA) |
| 71 | Kart gercekten WiFi'ya baglaniyor mu (STA -> AP dusmesi) | Acilista `Ag: STA (ev agi)` ya da `Ag: AP (kendi agi)` yazmali. 10 s'de STA olmazsa AP'ye dusmeli; AP parolasi seri konsola basilir |
| 72 | AGD: acilista ev agi yoksa AP, ev agi gelince KENDILIGINDEN STA (DEVIR 5.12.109) | Kayitli erisim noktasi KAPALIYKEN karti sifirla: ~10 s sonra `Ag: AP (kendi agi) ... (ev agi 30 s'de bir deneniyor)`. Erisim noktasini AC: <= 60 s'de ikinci satir `Ag: STA (ev agi)`; ~5 s sonra kartin AP adi PC'nin ag listesinden kalkar; `Q?` durum=4 (bagli); ev aginda `_http._tcp` + TXT kimlik gorunur. Calisirken kopma (5.12.106: 7-14 s'de kendiliginden donus) DEGISMEMELI; AP'deyken panel 192.168.4.1'de calismali (her 30 s'deki taramada kisa takilma olabilir — olculmedi) |
| 73 | mDNS telefonda cozuluyor mu | http://olcum.local acilmali. Android'de Chrome `.local`'i guvenilir cozmuyor (12+ ve degisken) — cozulmezse AP'nin SABIT 192.168.4.1'i kullanilacak, bu bir kusur DEGIL |
| 74 | CSRF savunmasi gercek tarayicida | Baska bir makinede `<img src=http://<kart-ip>/komut?k=p>` iceren sayfa ac. Istek karta ULASMAMALI. Ulasiyorsa POST+X-Olcum savunmasi calismiyor demektir |
| 75 | collectHeaders gercekten toplaniyor mu | `curl -X POST --data-binary '?' http://<ip>/komut` (basliksiz) -> HTTP 400. 204 donerse baslik denetimi SESSIZCE olmus demektir |
| 76 | esp_wifi_start() <-> adc_continuous_start() carpismasi | Skop yakalarken WiFi'yi kopar/bagla (DEVIR 7.1 (1), esp-idf#12749). Beklenen kusur: `! tetiklenemedi` ya da sifir dolu DMA tamponu. Bugunku baslatma sirasi TESADUFEN guvenli |
| 77 | SSE loop()'u ne kadar blokluyor — CIFT CEKIRDEKTEN SONRA | Iki sekmede /akis acikken `D` satirindaki ornek sayisi ve `K` satirindaki loop_azami_us. B28'den beri SSE yazimi cekirdek 0'da; olculdu: 1 istemciyle bosta 3.0 ms, tam sayfa yuklemesinde 4.1 ms. 20 000 us'yi asmasi artik bir KARAR degil GERILEME isaretidir — ag isi olcum dongusune geri sizmis demektir |
| 78 | LittleFS gercekten baglaniyor mu | Acilista `Arayuz: LittleFS'te` yazmali. `begin(false)` — otomatik bicimlendirme YOK, yani bos bolum sessiz kalmaz |
| 79 | serveStatic ve index.htm tuzagi | `http://<ip>/` tam arayuzu vermeli (acik kok isleyicisi). `/vendor/vue.global.prod.js` ikinci yuklemede 304/onbellekten gelmeli — `immutable` calisiyor mu |
| 80 | W6: ETag + 304 kartta (arayuz-uret.py + arayuz-yaz.py + firmware W6 SONRASI) | `curl -sI http://<ip>/app.js` -> `ETag: "<16 onaltilik>"` + `Cache-Control: no-cache` + `Content-Encoding: gzip`. Ayni ETag ile `curl -s -o NUL -w "%{http_code} %{size_download}" -H "If-None-Match: <etag>" http://<ip>/app.js` -> `304 0`; baska bir etiketle -> `200 <boy>`. `/` (index) de ETag tasimali ve ASLA `immutable` olmamali. Telefonda/Edge'de ikinci acilis: Ag sekmesinde panel dosyalari 304, aktarilan ~0 B (DEVIR 5.12.108'deki tahminle karsilastir). Olcum dongusunde yeni blokaj yok (`K` satiri, KOMUT GONDERMEDEN) |
| 81 | Telefondan ilk yukleme suresi | PC'de OLCULDU (B27 A4): 622 ms, 107 KB, 7 istek; ikinci acilista statik trafik 0 B (onbellek). 3 s'yi gecerse panel cikarma adimi acilir (5.12.38). TELEFONDA ayni olcumu yap — WiFi mesafesi ve telefon CPU'su bu sayiyi buyutur |
| 82 | Sayfa sunmanin OLCUME bedeli — CIFT CEKIRDEKTEN SONRA | B27 A4'te (tek cekirdek) varlik varlik olculmustu: index 33 ms, style 34 ms, vue 155 ms, app.js 186 ms blokaj. B28'den sonra AYNI olcum: tam sayfa yuklemesinde 3.8-4.1 ms, bosta 3.0 ms, 0 uzun tur. ⚠ Bu kalemin onceki hali 'bosta 300 s'de 20 ms'yi asan TUR YOK' diyordu — YANLIS: o olcumde 5 tur vardi (22.5 ms, ~50 s'de bir). Metin olcum bitmeden yazilmisti. Olcum: `K` sifirla, sayfayi ac, KOMUT GONDERMEDEN kartin kendi `K` satirlarini dinle (`?` ciktisi tek basina bir turu ~12 ms bloklar) |
| 83 | arayuz-yaz.py ile karta yazma | esptool yolu ve 0x310000 ofseti HIC denenmedi. `python arayuz-uret.py && python arayuz-yaz.py` |
| 84 | 3A: panel karttan ES MODULU olarak aciliyor mu (STA + AP) | `python arayuz-uret.py && python arayuz-yaz.py` sonrasi http://<ip>/: konsolda 0 hata; Ag sekmesinde /app.js ve /ekran/tema.js `Content-Type: application/javascript` + `Content-Encoding: gzip`; konsolda `await import('/ortak/rapor.js')` hatasiz. Ayarlar > Gorunum uc temayi degistiriyor, sayfa yenilenince secim kaliyor. Olcum dongusunde yeni blokaj yok (`K` satiri, KOMUT GONDERMEDEN) |

## B25 Kart bringup kosucusu

| # | Olcum | Kabul olcutu |
|---|---|---|
| 85 | [!] Kosucunun kendisi gercek kartta calisiyor mu | Bu adim kosucuyu KAYITLI bir kart uzerinde siniyor. Gercek seri port, gercek zamanlama ve gercek USB CDC davranisi yalnizca kart takilinca gorulur: `python tezgah_kart.py --sifirla` |
| 86 | Acilis afisi yakalanabiliyor mu | DTR/RTS ile reset YALNIZCA UART kopruli kartlarda calisiyor. Yerel USB CDC'de EN dugmesine elle basmak gerekir — afis alinamazsa PSRAM/LittleFS denetimleri ATLANIR, kirmizi olmaz |
| 87 | Denetimler yeterli mi | Kosucu 33 denetim yapiyor; `_tezgah.md` bundan COK DAHA fazla kalem sayiyor (toplam dosyanin sonunda). Fark, multimetre isteyen kalemler. Kart calisir calismaz ikisini birlikte kullan |

## B71 Kayit motoru

| # | Olcum | Kabul olcutu |
|---|---|---|
| 88 | Flas yazma/silmenin olcume etkisi (gercek kart, 1A-2) | kayit 50/s ve 5/s surerken K satirinda loop_azami ve uzun tur kayitsiz tabanla ayni sinifta; kuyrukta dusen nokta 0 |
| 89 | Gercek elektrik kesme: fis cekme, PIL anahtari kapali | 20 tekrar: kurtarma hatasiz, oturum DEVAM ile suruyor, kayip en fazla son ~5 s (spec O2) |
| 90 | Emule NOR ariza modeli gercek ESP32 flasini temsil ediyor mu | kartta RTS sifirlamasiyla rastgele 100 kesme: K5-K10'un karsiliklari yesil |
| 91 | Python cozucunun volt/amper cevrimi kartin kendi hesabiyla ayni mi | karttan alinan kayit kayit_bicim.volt()/amper() ile cozulunce ayni anin D satiriyla bagil fark <= 1e-6 |

## B72 Kayit firmware + esitleme

| # | Olcum | Kabul olcutu |
|---|---|---|
| 92 | Flas yazma/silmenin olcume etkisi (spec §11 ilk risk) | tezgah_kayit.py --durma: 50/s ve 5/s'de kuyrukta dusen nokta 0; loop_azami ve sil_azami_us raporlanir |
| 93 | Kayit surerken sifirlama (RTS) -> DEVAM | tezgah_kayit.py --kesinti 20: her sifirlamada durum 2'ye doner, flasta tek oturum, noktalar bosluksuz, sira tekrar yok |
| 94 | Esitlenen dosya == karttaki flas bolumu (bayt bayt) | tezgah_kayit.py --esit: esptool ile okunan bolumdeki her kayit esitlenen dosyadakiyle ayni |
| 95 | DOLU bolumde acilis (bolumu 50/s ONAYSIZ ~1.7 sa doldur) | tezgah_kayit.py --dolu: tarama < 5 s ve Task WDT sifirlamasi YOK (2026-09-30'da sonsuz yeniden baslama bulundu), 11 MB esitlenir, onay dogrulanir, halka doner, dusen 0 |
| 96 | DOLU bolumde GF! | tezgah_kayit.py --bicim: anlik biter, temizlik surerken /kayit/liste her istekte < 1 s (p0 ayni web sunucusunda), temiz_kalan azalir |
| 97 | 1B kalibrasyon gecmisi kartta | tezgah_kayit.py --kal: #1 = Ayar3, not/tur kalici, oturum basliginda kal_no, /kal/liste == kl, etkin, `kk` taslaksiz kayit acmaz, Gb sessiz (kalibrasyon komutu CALISTIRMAZ) |
| 98 | [!] ADS takilinca: GERCEK bir kalibrasyon adimi | g sonrasi `k?` taslak=1; `kk<t><not>` yeni numara; ardindan baslayan kaydin kal_no'su o numara; unutulursa kayit baslarken otomatik ve kart 'otomatik kaydedildi' der. z (sifirlama) sonrasi taslak=0 (sifirlar gecmise girmez); sont degistirip geri alinca eski numara |
| 99 | [!] Gecmis doluyken tarama suresi | 30+ kayitli gecmiste degerler degisince kgc_esle en fazla 39 NVS okumasi: ayar komutu ve Gb'de loop_azami < 20 ms (tahmin ~4-8 ms) |
| 100 | 1C-1 pil oturumu kartta (ADS yok) | tezgah_kayit.py --pil: p1 reddedilir ve oturum acmaz; Ga/Ge/Gn gercek oturuma, PC adi/etiketi/notlari okur, Gx siler; olcum oturumu yeniden baslatmada DEVAM |
| 101 | [!] ADS takilinca: GERCEK pil testi kaydi | p1 -> G satirinda PIL oturumu; 5 dk'da bir DCIR olayi; kesmede PIL_SONUC == `B` raporu (mAh, Wh, sure, dcir sayisi); test ortasinda fis cekilirse acilista oturum BITIR(5), DEVAM yok; olcum kaydi surerken p1 -> olcum BITIR(6) |
| 102 | 1C-2 ayrintili kip kartta (ADS yok) | tezgah_kayit.py --ayrinti: hazir alan bosta buyur; Gb0 60 s: sira kesintisiz, zaman farki dagilimi, kayit ici silme 0, dusen 0; yeniden baslatmada DEVAM |
| 103 | [!] Skop girisine CAL bagliyken osiloskop gunlugu (1C-3) | X1000 + tek tel GPIO10 -> GPIO4 (ya da RC duzenegi): tezgah_kayit.py --skop sinyalli dalda Gt0 her yakalama tetikli ve ~1 kHz; 2026-10-01'de giriste sinyal yoktu (kodlar 0) |
| 104 | [!] ADS takilinca: gercek 500/s ayrintili kayit | Gb0 60 s: ~30 000 ornek, dt ortancasi ~2000 us; PC'de V/I (ve hizalamali W) kartin D satiriyla ayni anda karsilastirilir; hazir alan bitince KA_SILME kayitlari gorulur |
| 105 | 1E bildirimler kartta (PC'de sahte araci, hesap gerekmez) | tezgah_bildirim.py: Qv gecti; CONNECT keepalive 5 + vasiyet QoS 1 retained; durum c:1 cozulur (f A3-1E); Qt olayi `n` artarak; RTS sifirlamasinda vasiyet <= 15 s; araci kesintisinde olay kuyrukta bekler, yeniden baglaninca gider; QY dahili_bos >= 60 KB; /komut Q'yu 403 ile reddeder; Q?/akis hicbir parolayi gostermez |
| 106 | Gercek araci (EMQX Serverless): TLS + O4 (2026-10-02: 16/16 vasiyet 4.0-7.9 s) | Qu mqtts://<adres>.emqxsl.com:8883, Qk/Qp kart, Qc/Qd cihaz, Q1: Q? bagli ve el_sikisma_ms; TLS el sikismasi sirasinda K satirinda loop_azami degismez (K11); fis cekme -> vasiyet <= 15 s (hedef 10), 10 tekrar (O4) |
| 107 | Gercek fis cekme (USB + PIL kapali) | elle 5 kez: kurtarma hatasiz, kayit DEVAM ile surer, kayip en fazla son ~5 s |

## B72 E6F dahili yigin duzeltmesi (kartta)

| # | Olcum | Kabul olcutu |
|---|---|---|
| 108 | E6F acilis satiri (yuklemeden sonra ilk acilis, USB seri izleyici) | 'Bellek (E6F): tls=PSRAM veri=PSRAM akis=PSRAM'. 'dahili' = o tampon PSRAM bulamadi (E6F kazanci o kalemde yok), 'YOK' = hic ayrilamadi (tls: mbedTLS calismaz; veri: kayit KAPALI) |
| 109 | E6F uzun kosu: QH asil DRAM bolgesi (saatler, kopru esitlemesi + MQTT acik) | USB'den Q? + QH: ~250 KB'lik asil DRAM bolgesinin min_free / en buyuk blok. Once (A3-W2, ~9 sa) 11.4 KB / 36.9 KB; E6F ~1 dk'da 95.2 KB / 102 KB. Kabul: saatler sonra min_free oncekinden >= ~40 KB fazla (>= ~51 KB) ve Q? ayirma_hata=0; QY dahili_en_az 2.5 KB'a inmez |
| 110 | E6F QF okuma (QH sonundaki son 4 basarisiz ayirma) | 'QF yok' beklenen. caps=0x0008 gorev=bld (boyut <= 1600) = AES DMA ara tamponu ayrilamadi, MQTT o an koptu ve kendisi yeniden baglanir (E6F'nin bilinen bedeli; dahili DMA'li bellekte 1.6 KB'lik blok kalmamis). caps=0x080C gorev=wifi/tiT = Wi-Fi dinamik tamponu. caps=0x0804 gorev=bld = mbedTLS: E6F'den sonra BEKLENMEZ (PSRAM de dolmus demek); boyut gercek n*boyut (E6K) |
| 111 | [!] Ag geri donusu: erisim noktasi gidip gelince kart STA'ya kendiliginden doner | seri izleyici acik; kartin bagli oldugu erisim noktasini (ev agi ya da telefon hotspot'u) ~1 dk kapat, sonra ac: kullanici hicbir sey yapmadan kart STA'ya doner (Q durumu 'ag yok (STA degil)'den cikar, olcum.local acilir, kopru esitler). A3-CA3'ten beri (2026-10-07) 30 s'den uzun kopmada kart once kendi agini kurar (beklenen) ve kayitli aglari 30 s'de bir dener: erisim noktasi acildiktan sonra <= ~40 s'de STA. AP'de kalirsa ya da 5 dk'da donmezse KUSUR (2026-10-04 sabahi >= 1 dk 'ag yok'ta kaldi, donus olculmedi) |

## B72 CA-4 statik DRAM payi: skop tamponlari PSRAM'de (kartta)

| # | Olcum | Kabul olcutu |
|---|---|---|
| 112 | CA-4 acilis satiri (yuklemeden sonra ilk acilis, USB seri izleyici) | 'Bellek (CA-4): skop=PSRAM'. 'dahili' = PSRAM yok/dolu (16 KB dahili yigindan, statik kazanc acilista geri verildi); 'YOK' = osiloskop KAPALI (her yakalama reddedilir) |
| 113 | CA-4 osiloskop PSRAM tamponuyla (tb ve Gt0, /skop.bin) | tezgah_blokaj.py --skop + panel Osiloskop: yakalama, tetik yeri (idx == on), M satiri ve /skop.bin oncekiyle ayni; skop gorevi yigin dibi (C satiri skop_yigin_dip) degismez; K satiri loop_azami ve D satiri ornekleme hizi (~500/s) oncekiyle ayni |

## B73 ortak/ (JS hesap kodu)

| # | Olcum | Kabul olcutu |
|---|---|---|
| 114 | Kartin GERCEK akisi JS ile de ayni cozuluyor mu | tezgah_kayit.py --esit ile esitlenen kayit.bin'i hem kopru/kayit_bicim.py hem ortak/src/kayit.js ile coz; oturumlar, noktalar, volt/amper bit bit ayni |
| 115 | [!] Telefonda PBKDF2 suresi (Capacitor WebView) | 20 000 tur; spec 'telefonda < 1 s' (yazilim-sistemi §13). Node'daki sure telefonu temsil etmez |

## B3 Sema

| # | Olcum | Kabul olcutu |
|---|---|---|
| 116 | Kurulan kart SEMAYLA ayni mi | Netlist yalnizca semayi dogruluyor; lehimlenen kart baska olabilir. Olcum: her dugumu ohmmetrenin sureklilik kipiyle netliste karsi tek tek gec |
| 117 | Polarite: elektrolitik ve diyot yonleri | ERC yon hatasi YAKALAMAZ. Olcum: montajdan ONCE her kutuplu parcayi gozle dogrula — enerji verdikten sonra elektrolitik geri donusu yok |

## B4/B5 Olcum matematigi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 118 | ESP32'nin gercek ADC gurultusu ve INL'i | Sabit gerilimde 1000 ornek al, standart sapmayi olc. Skop cozunurlugu (28.8 mV) bu gurultunun altinda kalmali |
| 119 | Gercek ADS1115 ofset (+-3 LSB) ve kazanc (%0.15) hatasi | Kalibrasyon SONRASI bilinen iki noktada olc. Kalan hata veri sayfasi sinirlarinin icinde mi |
| 120 | ESP32 ADC'sinin gercek TAM OLCEGI | 3.1 V nominal ama yongaya gore degisiyor; skop volt/adim dogrudan buna bagli |

## B6 Firmware derleme + ikili

| # | Olcum | Kabul olcutu |
|---|---|---|
| 121 | I2C gercekten calisiyor mu | `#` komutu -> `I2C: 0x48 0x49`. Ikisi de gorunmuyorsa adres pinleri ya da cekme direncleri yanlis |
| 122 | Menzil gecisi gercek gerilimde puruzsuz mu | Yavas artan bir gerilimde NORMAL->YUKSEK gecisini izle. Sicrama varsa histerezis yetersiz |
| 123 | PSRAM kartta gercekten var mi | Acilista `PSRAM: 8192 KB` yazmali. `YOK` yazarsa hedef2.py'de PSRAM=opi yerine PSRAM=enabled (quad) denenecek |

## B7 Arayuz

| # | Olcum | Kabul olcutu |
|---|---|---|
| 124 | [!] Arayuz tarayicida GERCEKTEN dogru gorunuyor mu | Bu adim Vue`yu TAKLIT ediyor; sayfa hic render edilmiyor. B22.0`da arayuz zincir 15/15 yesilken tarayicida HIC acilmiyordu. `python arayuz3/sunucu.py` -> konsolda 0 hata, ham {{ }} yok |
| 125 | J7/J3 baypas uyarisi KIRMIZI seritli gorunuyor mu | Emniyet uyarisi govde metninden ayirt edilebilmeli. B22.0 oncesi `.uyari` sinifi hic tanimli degildi ve duz paragraf olarak cikiyordu |
| 126 | Osiloskop iki yoldan da AYNI cizimi veriyor mu | USB`de ASCII, WiFi`de ikili (/skop.bin) yol kullaniliyor. Ayni sinyalde iki kip AYNI dalgayi cizmeli; farkliysa cozuculerden biri yanlis (endian, olcek ya da ofset) |
| 127 | Telefonda Ana Ekrana Ekle | iPhone: adres cubugu OLMADAN, kendi ikonuyla acilmali. Android: kisayol Chrome sekmesinde acilir — bu beklenen davranis, gercek PWA kurulumu HTTPS istiyor |

## B9 Malzeme listesi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 128 | [!] Direnc adetleri SAYIM degil goz karari | envanter.csv'nin direnc adetleri yaklasik (CLAUDE.md). Listede yeter gorunen bir deger tezgahta bitebilir. Olcum: montajdan ONCE kritik degerleri say |
| 129 | Kayitta gorunmeyen parca GERCEKTEN yok mu | Bobin/cekirdek ve modul alanlari KISMEN girildi. 'kayitta yok' = 'elde yok' DEGIL. Olcum: kutuya bak |
| 130 | Parcalarin gercek degerleri etiketiyle ayni mi | Ozellikle HV bolucusundeki 4.9 M ohm zinciri. Olcum: lehimlemeden once her direnci ohmmetreyle gec |

## B48 Yerlesim plani

| # | Olcum | Kabul olcutu |
|---|---|---|
| 131 | [!] BJT/TL431/7912 bacak sirasi multimetrenin diyot kademesiyle | Plan E-B-C (2N2222-331), C-B-E (BC557), REF-A-K (TL431), GND-VI-VO (7912) varsayiyor. Semadaki Q2 sembolu BC547 (C-B-E); yanlis sira transistoru YARI calistirir, sessiz kusur |
| 132 | Plaket ped capi kumpasla | Kacak yolu hesabi lehimli iletken capini 1.54 mm aliyor. Olculen buyukse yerlesim3_veri/tasarim3_sabit guncellenip denetim yeniden kosulacak (HV kartinda pay +1.97 mm) |
| 133 | Sigorta klipsi, 68uF ve C18 bacak araliklari | Ayak izleri tahmin: klips cifti 6 adim, 68uF 1 adim / 8 mm govde, C18 film 6 adim. Parcayi plakete oturt, delikleri say; uymayan varsa plan yeniden uretilecek (--yol-uret) |
| 134 | Her adimin sonunda bakir sureklilik (ohmmetre) | Plan acik/kisa devre olmadigini GEOMETRIDEN kanitliyor; soguk lehim ve lehim koprusunu kanitlayamaz. Her adimda kilavuzun KAPI olcumunden once komsu pedler arasi kisa, ag iclerinde sureklilik |

**Toplam 134 kalem, 22 tanesi ilk gun.**
