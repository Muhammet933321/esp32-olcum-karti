# Tezgahta olculecekler — URETILMIS liste

Bu dosya `dogrula3.py` tarafindan uretiliyor. **Elle duzenleme.**
Her kalem, onu dogrulayamayan adimin yaninda yaziyor;
yeni bir kalem eklemek icin o adimin `tezgah(...)` cagrisina ekle.

## Ilk gun

Bu 10 kalem `[!]` ile isaretli: kart calisir calismaz, digerlerinden ONCE.

> Asagidaki sira ZINCIR sirasi, oncelik sirasi DEGIL — kalemler arasinda elle bir siralama tutulsaydi yine bayatlardi. Hepsi ilk gun yapilacak; hangisinin once oldugu kalemin kendi kabul olcutunde yaziyor (orn. *bedava test*, *kart calisir calismaz*).

| # | Adim | Olcum |
|---|---|---|
| 1 | B18 GPIO kelepceleri | +3V3 rayinin GERI BESLENMESI |
| 2 | B17 ADS es zamanliligi ve faz | Faz kalibrasyonunun TASINABILIRLIGI |
| 3 | B20 Ornekleme hizi ve bant | `D` satirindaki ORNEK SAYISI — ilk, en ucuz ve en onemli test |
| 4 | B20 Ornekleme hizi ve bant | ALERT/RDY gercekten DARBE mi, MANDAL mi |
| 5 | B20 Ornekleme hizi ve bant | `K` satiri — loop_azami_us |
| 6 | B21 Pil kapasite testi | FAILSAFE — kart calisirken RESET at |
| 7 | B21 Pil kapasite testi | BAYPAS denetimi — yuku bilerek J3'e bagla |
| 8 | B25 Kart bringup kosucusu | Kosucunun kendisi gercek kartta calisiyor mu |
| 9 | B7 Arayuz | Arayuz tarayicida GERCEKTEN dogru gorunuyor mu |
| 10 | B9 Malzeme listesi | Direnc adetleri SAYIM degil goz karari |


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
| 23 | Skop girisi VREF'i ne kadar kaydiriyor (capraz konusma) | Skop akimi artik GND'ye degil VREF'e gidiyor ve VREF BUTUN kanallarin referansi. Olcum: skop girisine 40 V ver, GERILIM kanalinin okumasi degisiyor mu bak — degisiyorsa VREF tamponu yetersiz |
| 24 | Gercek menzil -63.5 .. +46.8 V mi | R23 2.7K'ya dusuruldu. Olcum: her iki uctan da sinira yakin DC ver, kirpma noktalarini oku |
| 25 | Cozunurluk kaybi kabul edilebilir mi | Adim 28.8 mV (tek yonluyken 11.9 mV idi; ikisi de NOMINAL tam olcekten). Olcum: kucuk genlikli (1 V tepe) bir dalga sekli cizdir, basamaklanma goze batiyorsa karar yeniden gorusulecek |

## B17 ADS es zamanliligi ve faz

| # | Olcum | Kabul olcutu |
|---|---|---|
| 26 | [!] Faz kalibrasyonunun TASINABILIRLIGI | Direncli yukte USB'den `F` ile kalibre et, sonra AYNI yuke WiFi ile bak. PF farki > %0.5 ise B22.1'in us duzeltmesi eksik ve faz hala periyoda bagli demektir |
| 27 | Kondansator tolerans harfi (J=%5, K=%10) | Gucun gecerlilik bandini bu belirliyor. Kutudaki harfi oku; K ise en kotu tau eslesmezligi 292.8 us |
| 28 | Sontun guc degeri | +-11.5 A rakami 2 W CIKARIMINDAN geliyor. Uzerindeki degeri oku; dusukse akim tavani duser |
| 29 | Direncli yukte PF gercekten 1'e yakin mi | `w` komutu. PF < 0.99 ise suzgec eslesmezligi kalibre edilmemis demektir — once `F` ile duzelt |

## B20 Ornekleme hizi ve bant

| # | Olcum | Kabul olcutu |
|---|---|---|
| 30 | [!] `D` satirindaki ORNEK SAYISI — ilk, en ucuz ve en onemli test | 200 ms'de 133 +-3 beklenir. ~100 cikarsa B22.1'in enableDelay(false)'u ISE YARAMAMIS; ~19 cikarsa B20'nin kendi duzeltmeleri cokmus. IKI AYRI kusur, ikisi de bu tek sayidan gorulur — o yuzden once bu olculur |
| 31 | `Wire` gercekten 400 kHz mi | Skopla SCL periyodunu olc. 100 kHz'e duserse V/I kaymasi DORT KAT buyur ve butun faz butcesi gecersizlesir |
| 32 | [!] ALERT/RDY gercekten DARBE mi, MANDAL mi | Skopla bak. Tek atista mandal olabilir — veri sayfasi kendisiyle CELISIYOR (5.12.30). Mandalsa `yeni_donusum_bekle` mantigi degismeli; bugunku kod darbe varsayiyor |
| 33 | /HAZIR hattinda harici pull-up gerekiyor mu | Bugun ESP32'nin dahili ~45 kOhm'una guveniliyor; en kotu yukselme 11.1 us. Skopta yavas gorunuyorsa stoktaki 10K eklensin |
| 34 | `t_kayma_us` gercekten ~95 us mi | `?` ciktisinda gorunuyor. I2C yazma suresi hesabina dayaniyor (B17); sapma faz duzeltmesini kaydirir |
| 35 | [!] `K` satiri — loop_azami_us | `K <kayip_ms> <loop_azami_us> <uzun_tur>`. **20 000 us'yi gecerse CIFT CEKIRDEK karari tetiklenir** (5.12.34). Bu, o kararin TEK olcutu. Ayrica kayip_ms > 0 ise enerji sayaci aralik atlamis demektir |

## B21 Pil kapasite testi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 36 | [!] FAILSAFE — kart calisirken RESET at | Yuk KESILMELI. Kapi R42 ile GND'ye cekili, ESP32 olurse MOSFET kapanmali. B21'in EN ONEMLI tezgah testi; gecmezse pil testi hic kullanilmamali |
| 37 | [!] BAYPAS denetimi — yuku bilerek J3'e bagla | Test REDDEDILMELI. J3 dogrudan sonte gidiyor; oraya baglanirsa MOSFET baypas olur ve kesme CALISMAZ. Sessiz hatayi yakalayan tek sey bu |
| 38 | Kesme gecikmesi | `p1` kosarken bir istemciyi askiya al ve kesme gerilimine in. Fazla desarj < 0.5 mAh olmali — yani kesme loop() blokajina BAGLI OLMAMALI |
| 39 | MOSFET'in uzerindeki logo | Veri sayfasi ikincil kaynak (INCHANGE). Farkli bir uretici cikarsa Vdss ve Rds(on) yeniden denetlenmeli |
| 40 | Kapi gerilimi — yuk acikken Vgs | ~11.8 V beklenir. Dususe Rds(on) buyur, MOSFET isinir |
| 41 | Tas direncin gercek degeri ve isinmasi | 4.7-7.5 ohm / 10 W. Elle olc; 30 dk desarjda sicakligina bak |
| 42 | Sarj yonunde test | Sayac ISARETLI ama sarj kaynagi yok — mAh geri saymali. Kaynak bulununca denenecek |

## B22a PC koprusu

| # | Olcum | Kabul olcutu |
|---|---|---|
| 43 | SeriKart gercek baud'da calisiyor mu | `python kopru/kopru.py --port COMx` -> `D` satirlari akmali. Bozuk karakter gelirse DCB alan duzeni ya da baud yanlis |
| 44 | DTR/RTS kart RESET atmiyor mu | Kopru acilinca kart yeniden BASLAMAMALI (acilis banneri gorunmemeli). Iki hat da bilerek DISABLE; reset atiyorsa devre otomatik-reset'e bagli ve pil testi kopru acilisinda OLUR |
| 45 | Windows 0.0.0.0:80 / stok-takip cakismasi | stok-takip 127.0.0.1:80'i tutuyor. Kopru `http://<LAN-IP>` yazmali; `127.0.0.1` yazarsa kullaniciyi STOK arayuzune yollar (bu makinede gercekten oldu, 5.12.36) |
| 46 | Telefon koprude uctan uca | Telefondan http://<PC-IP> -> tam arayuz, canli olcum. Iki tarayici ayni anda izlerken YALNIZCA biri surucu olmali |
| 47 | p0 (DURDUR) izleyiciden de geciyor mu | Surucu OLMAYAN sekmeden pil testini durdur. Gecmeli — bu bir kolaylik degil EMNIYET karari |

## B22b Kart web katmani

| # | Olcum | Kabul olcutu |
|---|---|---|
| 48 | Kart gercekten WiFi'ya baglaniyor mu (STA -> AP dusmesi) | Acilista `Ag: STA (ev agi)` ya da `Ag: AP (kendi agi)` yazmali. 10 s'de STA olmazsa AP'ye dusmeli; AP parolasi seri konsola basilir |
| 49 | mDNS telefonda cozuluyor mu | http://olcum.local acilmali. Android'de Chrome `.local`'i guvenilir cozmuyor (12+ ve degisken) — cozulmezse AP'nin SABIT 192.168.4.1'i kullanilacak, bu bir kusur DEGIL |
| 50 | CSRF savunmasi gercek tarayicida | Baska bir makinede `<img src=http://<kart-ip>/komut?k=p>` iceren sayfa ac. Istek karta ULASMAMALI. Ulasiyorsa POST+X-Olcum savunmasi calismiyor demektir |
| 51 | collectHeaders gercekten toplaniyor mu | `curl -X POST --data-binary '?' http://<ip>/komut` (basliksiz) -> HTTP 400. 204 donerse baslik denetimi SESSIZCE olmus demektir |
| 52 | esp_wifi_start() <-> adc_continuous_start() carpismasi | Skop yakalarken WiFi'yi kopar/bagla (DEVIR 7.1 (1), esp-idf#12749). Beklenen kusur: `! tetiklenemedi` ya da sifir dolu DMA tamponu. Bugunku baslatma sirasi TESADUFEN guvenli |
| 53 | SSE loop()'u ne kadar blokluyor | Iki sekmede /akis acikken `D` satirindaki ornek sayisi ve `K` satirindaki loop_azami_us. `K` > 20 000 us ise cift cekirdek karari TETIKLENIR (5.12.34) |
| 54 | LittleFS gercekten baglaniyor mu | Acilista `Arayuz: LittleFS'te` yazmali. `begin(false)` — otomatik bicimlendirme YOK, yani bos bolum sessiz kalmaz |
| 55 | serveStatic ve index.htm tuzagi | `http://<ip>/` tam arayuzu vermeli (acik kok isleyicisi). `/vendor/vue.global.prod.js` ikinci yuklemede 304/onbellekten gelmeli — `immutable` calisiyor mu |
| 56 | Telefondan ilk yukleme suresi | 93 753 B gzip. 3 s'yi gecerse panel cikarma adimi acilir (5.12.38). Ikinci acilista statik trafik 0 B olmali |
| 57 | arayuz-yaz.py ile karta yazma | esptool yolu ve 0x310000 ofseti HIC denenmedi. `python arayuz-uret.py && python arayuz-yaz.py` |

## B25 Kart bringup kosucusu

| # | Olcum | Kabul olcutu |
|---|---|---|
| 58 | [!] Kosucunun kendisi gercek kartta calisiyor mu | Bu adim kosucuyu KAYITLI bir kart uzerinde siniyor. Gercek seri port, gercek zamanlama ve gercek USB CDC davranisi yalnizca kart takilinca gorulur: `python tezgah_kart.py --sifirla` |
| 59 | Acilis afisi yakalanabiliyor mu | DTR/RTS ile reset YALNIZCA UART kopruli kartlarda calisiyor. Yerel USB CDC'de EN dugmesine elle basmak gerekir — afis alinamazsa PSRAM/LittleFS denetimleri ATLANIR, kirmizi olmaz |
| 60 | Denetimler yeterli mi | Kosucu 30 denetim yapiyor; `_tezgah.md` bundan COK DAHA fazla kalem sayiyor (toplam dosyanin sonunda). Fark, multimetre isteyen kalemler. Kart calisir calismaz ikisini birlikte kullan |

## B3 Sema

| # | Olcum | Kabul olcutu |
|---|---|---|
| 61 | Kurulan kart SEMAYLA ayni mi | Netlist yalnizca semayi dogruluyor; lehimlenen kart baska olabilir. Olcum: her dugumu ohmmetrenin sureklilik kipiyle netliste karsi tek tek gec |
| 62 | Polarite: elektrolitik ve diyot yonleri | ERC yon hatasi YAKALAMAZ. Olcum: montajdan ONCE her kutuplu parcayi gozle dogrula — enerji verdikten sonra elektrolitik geri donusu yok |

## B4/B5 Olcum matematigi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 63 | ESP32'nin gercek ADC gurultusu ve INL'i | Sabit gerilimde 1000 ornek al, standart sapmayi olc. Skop cozunurlugu (28.8 mV) bu gurultunun altinda kalmali |
| 64 | Gercek ADS1115 ofset (+-3 LSB) ve kazanc (%0.15) hatasi | Kalibrasyon SONRASI bilinen iki noktada olc. Kalan hata veri sayfasi sinirlarinin icinde mi |
| 65 | ESP32 ADC'sinin gercek TAM OLCEGI | 3.1 V nominal ama yongaya gore degisiyor; skop volt/adim dogrudan buna bagli |

## B6 Firmware derleme + ikili

| # | Olcum | Kabul olcutu |
|---|---|---|
| 66 | I2C gercekten calisiyor mu | `#` komutu -> `I2C: 0x48 0x49`. Ikisi de gorunmuyorsa adres pinleri ya da cekme direncleri yanlis |
| 67 | Menzil gecisi gercek gerilimde puruzsuz mu | Yavas artan bir gerilimde NORMAL->YUKSEK gecisini izle. Sicrama varsa histerezis yetersiz |
| 68 | PSRAM kartta gercekten var mi | Acilista `PSRAM: 8192 KB` yazmali. `YOK` yazarsa hedef2.py'de PSRAM=opi yerine PSRAM=enabled (quad) denenecek |

## B7 Arayuz

| # | Olcum | Kabul olcutu |
|---|---|---|
| 69 | [!] Arayuz tarayicida GERCEKTEN dogru gorunuyor mu | Bu adim Vue`yu TAKLIT ediyor; sayfa hic render edilmiyor. B22.0`da arayuz zincir 15/15 yesilken tarayicida HIC acilmiyordu. `python arayuz3/sunucu.py` -> konsolda 0 hata, ham {{ }} yok |
| 70 | J7/J3 baypas uyarisi KIRMIZI seritli gorunuyor mu | Emniyet uyarisi govde metninden ayirt edilebilmeli. B22.0 oncesi `.uyari` sinifi hic tanimli degildi ve duz paragraf olarak cikiyordu |
| 71 | Osiloskop iki yoldan da AYNI cizimi veriyor mu | USB`de ASCII, WiFi`de ikili (/skop.bin) yol kullaniliyor. Ayni sinyalde iki kip AYNI dalgayi cizmeli; farkliysa cozuculerden biri yanlis (endian, olcek ya da ofset) |
| 72 | Telefonda Ana Ekrana Ekle | iPhone: adres cubugu OLMADAN, kendi ikonuyla acilmali. Android: kisayol Chrome sekmesinde acilir — bu beklenen davranis, gercek PWA kurulumu HTTPS istiyor |

## B9 Malzeme listesi

| # | Olcum | Kabul olcutu |
|---|---|---|
| 73 | [!] Direnc adetleri SAYIM degil goz karari | envanter.csv'nin direnc adetleri yaklasik (CLAUDE.md). Listede yeter gorunen bir deger tezgahta bitebilir. Olcum: montajdan ONCE kritik degerleri say |
| 74 | Kayitta gorunmeyen parca GERCEKTEN yok mu | Bobin/cekirdek ve modul alanlari KISMEN girildi. 'kayitta yok' = 'elde yok' DEGIL. Olcum: kutuya bak |
| 75 | Parcalarin gercek degerleri etiketiyle ayni mi | Ozellikle HV bolucusundeki 4.9 M ohm zinciri. Olcum: lehimlemeden once her direnci ohmmetreyle gec |

**Toplam 75 kalem, 10 tanesi ilk gun.**
