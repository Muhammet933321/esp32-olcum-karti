# Ölçüm Kartı — geliştirici notları

> **English:** [GELISTIRICI.md](GELISTIRICI.md). Bu dosya projenin eski İngilizce tanıtımının (2026-09)
> Türkçesidir; mühendislik ve doğrulama ayrıntıları için duruyor. Kullanıcı tanıtımı:
> [README.md](README.md) (Türkçe) · [README.en.md](README.en.md) (İngilizce).

> **Önce bunu oku — yazıldığından bu yana ne değişti (2026-10).**
> Donanım **kuruldu ve çalışıyor**: analog kart delikli plakette, iki ADS1115 de takılı, kutu
> kuruldu, gerçek 18650 hücrelerle pil testleri koşuldu. Aşağıda 2026-09'daki kurulmamış durumu
> anlatan cümleler güncellendi ya da *(2026-09)* diye işaretlendi. Gerçek kartta ölçülen: yaklaşık
> **500 örnek/s** (tasarım değeri 665 örnek/s değil), akım yük yolu yüzünden sürekli **9.5 A** ile
> sınırlı. O günden bu yana projeye kartın kendi kaydı (flash'ta 11 MB, elektrik kesilmesine dayanıklı),
> bir Windows PC uygulaması (`kopru/pc.py`, arşiv + bildirimler) ve bir Android uygulaması (`mobil/`)
> eklendi. Aşağıdaki bellek ve adım sayıları tarihseldir; güncellerini zincir yazdırır.
> Esas kayıt mühendislik günlüğü [`DEVIR.md`](DEVIR.md)'dir.

Tek kartta **voltmetre, ampermetre, wattmetre, enerji sayacı, osiloskop ve pil
kapasite test cihazı**. ESP32-S3 + iki 16 bit ADC; tamamen web tarayıcısından
kullanılır — bilgisayarsız bir telefondan ya da USB ile bağlı bir PC'den.

> `BELGELER/` altındaki ve `uretim/_tezgah.md`'deki **üretilen** belgeler her
> sayıyı tasarım dosyalarından alır, o yüzden kayamazlar. Bu dosya elle
> yazılıyor.

> **Dil notu.** Proje **Türkçe** kuruldu: kod yorumları, seri konsol,
> mühendislik günlüğü ([`DEVIR.md`](DEVIR.md)) ve tezgah listesi Türkçe. Web
> arayüzünün İngilizce seçeneği var, kullanıcı rehberlerinin İngilizceleri
> [`BELGELER/en/`](BELGELER/en)'de, bu dosyanın İngilizce aslı da
> [GELISTIRICI.md](GELISTIRICI.md).
>
> ℹ️ `BELGELER/*.html` sayfaları **tarayıcıda açılmak için üretilmiş
> belgelerdir** — GitHub onları kaynak olarak gösterir. Depoyu klonla (ya da
> ZIP'ini indir) ve `BELGELER/index.html`'i yerelde aç.

---

## Ne ölçer

| Yetenek | Menzil | Not |
|---|---|---|
| **Gerilim** — normal kanal | ±32.4 V | iki yönlü, içteki VREF'e referanslı |
| **Gerilim** — yüksek kanal | ±613.7 V | 4.9 MΩ bölücü zinciri |
| **Akım** | sürekli ±9.5 A | takılı şönt 5 mΩ; sınırı yük yolu koyuyor. Tasarım dört şönt seçeneğiyle (10 / 1 / 0.1 / 0.015 Ω) ±11.55 A'e kadar izin veriyordu |
| **Güç · enerji** | V × I, işaretli | menzil başına faz kalibrasyonlu gerçek güç |
| **Örnekleme hızı** | ölçülen **~500 örnek/s** | 665 örnek/s tasarım değeriydi (aşağıdaki tabloya bak). İki ADC art arda başlatılıyor; kalan ~95 µs kayma yazılımda gideriliyor |
| **Osiloskop** | −63.5 … +46.8 V | 611 – 83 333 örnek/s, 28.8 mV adım |
| **Pil testi** | ≤ 38.5 V, 6.55 A | mAh **ve** Wh, deşarj eğrisi, DC iç direnç |

Buradaki mühendisliğin çoğunun sebebi wattmetre. Gücü doğru ölçmek, gerilim ve
akım örneklerinin *aynı anı* anlatmasını ve *eşleşmiş süzgeçlerden* geçmesini
gerektirir — ikisinin de önceki revizyonlarda doğru olmadığı ortaya çıktı ve
düzeltilmeleri bu projenin emeğinin büyük bir kısmını yedi.

## Bağlanmanın üç yolu

Kartın ekranı yok. Tarayıcıdan kullanılır ve üç yol var — hepsi aynı arayüzü
gösterir. Tam açıklama, çizimiyle birlikte,
[`BELGELER/6-ag.html`](BELGELER/6-ag.html)'de.

| # | Kip | Adres | Ne zaman |
|---|---|---|---|
| 1 | **Kartın kendi Wi-Fi'si** | `192.168.4.1` | Bilgisayar yok. Kart bütün arayüzü kendi flash'ından sunar |
| 2 | **Kart ev Wi-Fi'sinde** | `http://olcum.local` | Kart kablonun yetişmediği yerde. 10 s içinde bağlanamazsa kip 1'e döner |
| 3 | **USB köprüsü** — *USB güvenliyse tercih edilen* | köprünün yazdırdığı adres | Küçük bir Python programı kartı USB üzerinden aktarır ve arayüzü sunar |

**Köprü neden tercih ediliyor:** karta doğrudan bağlanan her tarayıcı ölçümü
yavaşlatır — kart hem örnekleme döngüsünü hem bir HTTP sunucusunu çalıştırıyor.
Karta doğrudan en çok **4** tarayıcı bakabilir; bir köprü kayıtlıyken kart
doğrudan istemcileri ona yönlendirir, böylece karta yalnız köprü konuşur.
Ölçümler kartın belleğiyle sınırlı kalmaz, PC'de arşivlenir. Kartın Wi-Fi'si bu
kipte kendiliğinden **kapanmaz** — ölçüm döngüsünün rahat bırakılmasını
istiyorsan seri konsoldan `N0` gönder.

> ⚠️ **USB her zaman bir seçenek değil, tek başına Wi-Fi de çözüm değil.**
> Kart **yalıtımlı değil**: USB takılıyken kartın toprağı bilgisayarının
> toprağıdır. Kartı pil + Wi-Fi ile yüzdürmek bilgisayarı kurtarır ama **seni
> kurtarmaz** — kart o zaman şebeke potansiyelinde durur. Şebekeye referanslı
> herhangi bir şeyi ölçmeden önce [Güvenlik](#güvenlik) bölümüne bak.

## Bu depoda ne var

| Yol | Ne |
|---|---|
| [`kod/olcum-karti-a3/`](kod/olcum-karti-a3) | Firmware (Arduino / ESP32-S3). Ölçüm matematiği, osiloskop, pil testi, web katmanı |
| [`sema3/`](sema3) | KiCad şeması — tasarımın esas kaydı |
| [`arayuz3/`](arayuz3) | Web arayüzü (Vue 3, derleme adımı yok, kütüphane depoda) |
| [`kopru/`](kopru) | PC köprüsü — seri↔SSE aktarımı, disk arşivi, sürücü hakemliği. Yalnız Python standart kütüphanesi |
| [`BELGELER/`](BELGELER) | **Kullanıcı belgeleri, üretiliyor** — HTML + PDF. `index.html`'den başla; İngilizce sayfalar [`BELGELER/en/`](BELGELER/en)'de |
| [`uretim/`](uretim) | Doğrulama zinciri, benzetimler, üreteçler ve donanım bringup düzeneği |
| [`uretim/_tezgah.md`](uretim/_tezgah.md) | **Üretiliyor** — tezgah listesi: gerçek donanımda ölçülmesi gereken her şey |
| [`DEVIR.md`](DEVIR.md) | Mühendislik günlüğü. Uzun, kronolojik, Türkçe — her kararın nasıl alındığının kaydı |
| [`arsiv/`](arsiv) | Önceki aşamalar (ATmega328P, sonra ilk ESP32 revizyonu), her birinin kendi zinciriyle |

## Bir tane yapmak

1. **Malzemeler** — [`BELGELER/2-malzemeler.html`](BELGELER/2-malzemeler.html)
   şemadan üretiliyor, o yüzden tasarımdan kayamaz.
2. **Kurulum** — [`BELGELER/4-kurulum.html`](BELGELER/4-kurulum.html): yedi
   adım, her biri devam etmeden önce geçmen gereken bir ölçüm kapısıyla biter.
   ⚠️ **Bu depoda PCB yok** — gerber yok, yerleşim çizimi yok. Kart delikli
   plakete elle kuruluyor ve rehber buna göre yazıldı. Tasarımın esas kaydı
   şema.
3. **Firmware** — kart bir **ESP32-S3 N16R8** olmalı (16 MB flash, 8 MB oktal
   PSRAM). FQBN'in tamamı önemli; varsayılanlar çalışmaz:

   ```bash
   arduino-cli compile --warnings all \
     --fqbn esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=huge_app \
     kod/olcum-karti-a3
   ```

   Arduino IDE'de bu, *ESP32S3 Dev Module* kartı ve **PSRAM: OPI PSRAM**,
   **Flash Size: 16MB**, **Partition Scheme: Huge APP** demek. Varsayılan
   `FlashSize=4M` ile yalnız ilk 4 MB görünür ve `0x310000`'daki LittleFS
   görüntüsü bölüm sınırına denk gelir; `PSRAM=opi` olmadan 8 MB PSRAM hiç
   ayağa kalkmaz. `-Wall -Wextra` ile uyarısız derlenir. Bu dizgenin tek
   kaynağı [`uretim/hedef2.py`](uretim/hedef2.py).
4. **Arayüzü karta yaz** —
   `cd uretim && python arayuz-uret.py && python arayuz-yaz.py` arayüzü bir
   LittleFS görüntüsüne paketler ve `0x310000` adresine yazar.
5. **PC köprüsü (isteğe bağlı)** — `Kopru Baslat.bat`'a çift tıkla.

**Bellek** *(2026-09)*: firmware **1 067 423 B**, yani 3 MB'lık `huge_app`
uygulama bölümünün (16 MB flash'ın değil) %33'ü, artı **71 420 B RAM (%21)**.
Arayüz **93 753 B** — 7 dosya, 6'sı gzip ile önceden sıkıştırılmış (PNG simge
ham duruyor) — 917 504 B'lık bir LittleFS bölümünün içinde.

## Bringup düzeneği

Tasarım hiçbir şey kurulmadan önce doğrulandı; bu yüzden kartın geleceği gün
için çalıştırılabilir bir bringup düzeneği yazıldı. O günden bu yana gerçek
kartta koşuldu (DEVIR.md, B26'dan itibaren) ve multimetre gerektirmeyen her
şeyi otomatik yapıyor:

```bash
cd uretim
python tezgah_kart.py --liste                       # neyi denetlediğini göster
python tezgah_kart.py --sifirla                     # aşama 0: çıplak ESP32
python tezgah_kart.py --sifirla --asama 1           # + ADS1115 modülleri
python tezgah_kart.py --sifirla --http olcum.local  # + web katmanı
```

**27 denetim** (`--liste` güncel kümeyi yazdırır), elindeki donanıma göre
aşamalı: açılış satırı (PSRAM boyutu, LittleFS, ağ kipi), komut yüzeyi, bir
zamanlar bir kanalı tuğlaya çeviren korumalar, I²C taraması, `D` satırının
biçimi, hızı ve **örnek sayısı**; HTTP tarafında da CSRF, belirteç,
`p0`-her-zaman-serbest ve Host izin listesi. Beklenen her dizge firmware
kaynağından okunur, o yüzden kayamaz.

Karttan `loop_azami_us`'u okur ve **20 000 µs** eşiğiyle karşılaştırır — çift
çekirdek kararını veren ölçüm buydu. Gerçek kartta karar çıktı: web ve ağ işleri
artık çekirdek 0'da, örnekleme döngüsü çekirdek 1'i tek başına kullanıyor.

🔴 **Düzenek hiçbir zaman yük sürmez.** Pil deşarjını başlatmak bir test
betiğinin kendi başına yapabileceği bir şey değil; o denetim elle kalıyor.

Düzeneğin kendisi donanımsız test ediliyor: `test_tezgah_kart.py` onu senaryolu
bir taklit karta karşı koşturur — sağlam kartta yeşil, ve **bilerek bozulmuş 15
kartın** her biri *doğru* denetimi kırmızıya çevirmeli. Yanlış bir bringup
testi hiç olmamasından kötüdür: bozuk bir karta sağlam der.

Hâlâ multimetre isteyenler [`uretim/_tezgah.md`](uretim/_tezgah.md)'de —
sayıları ve ilk gün alt kümesi o üretilen dosyanın en üstünde.

## Doğrulama zinciri

Projenin asıl zamanını harcadığı kısım bu. Tasarım gözden geçirmeyle değil,
çalıştırılabilir adımlardan oluşan bir zincirle denetleniyor:

```bash
cd uretim
python dogrula3.py     # güncel aşama (2026-09'da 18 adım, ~6 dk)
python dogrula2.py     # arşivlenmiş aşama 2
python dogrula.py      # arşivlenmiş aşama 1
```

**18 adım** *(2026-09; güncel sayıyı zincir yazdırır)*. Devre davranışı
**ngspice** ile benzetiliyor; firmware'in ölçüm matematiği bit düzeyinde
doğrulanmış bir **AVR emülatörünün** içinde *gerçek derlenmiş kod* olarak
koşuyor; şema netlist'ten düğüm düğüm denetleniyor (ERC yalnız "bağlı" der,
"doğru" demez); firmware gerçek araç zinciriyle derleniyor ve ikili dosyada
ölü dallar aranıyor; arayüzün gönderebildiği her komut, firmware'in gerçekten
uyguladığı `case` etiketleriyle karşılaştırılıyor.

Zincir iki dosya yazarak bitiyor:

- **`uretim/_tezgah.md`** — tezgah listesi (aşağıda).
- **`uretim/beklenen_sayim.json`** — iddia sayısı kilidi. Bir adımın sayısı
  **iki yönden birinde** değişirse zincir kırmızıya döner. Bilerek mi?
  `python dogrula3.py --sayim-kilidi-yaz`.

### Yeşil test hiçbir şey kanıtlamaz

Bu cümle projenin çalışma kuralı ve boşuna konmadı. Dört kez zincir baştan
sona yeşilken gerçek ve pahalı bir şey bozuktu:

| Bulunan | O sırada zincirin dediği |
|---|---|
| Web arayüzü **tarayıcıda hiç açılmadı** — iki dosya 404 veriyordu | 15/15 yeşil, arayüz testleri 82/82 |
| Kart **665 değil 500 örnek/s** ile örnekliyordu — `WebServer` boştayken içeride `delay(1)` çağırıyor ve `CONFIG_FREERTOS_HZ=1000` döngüyü kuantalıyordu | 15/15 yeşil |
| Faz kalibrasyonu sabit bir **süreyi** düzeltirken **örnek** cinsinden saklanıyordu — projenin kendi hata bütçesinin 1.74 katı | 15/15 yeşil |
| Çıplak bir `g` komutu **bir kanalı kalıcı olarak tuğlaya çeviriyordu** (NVS'ye kazanç 0 yazılıyor, kurtarma eşiği sonra sağlanamıyordu) | 15/15 yeşil |

Bu yüzden zincire tek başına güvenilmiyor. İddialar **kaynak bozulup
kırmızıya döndükleri denetlenerek** sınanıyor:

```bash
python mutasyon.py                 # hafif mutasyonlar, ~15 s
python mutasyon.py --adim B22b     # tek bir adımı hedefle
python mutasyon.py --liste         # neyi koşacağını göster
python mutasyon.py --adim B3       # bütün zinciri koşar (~12 dk):
python mutasyon.py --adim B23      # bu ikisi zincirin KENDİ korumalarını sınar
```

Her mutasyon ağacın yerinde değil, bir **kopyasında** koşar. Koşucu, proje
henüz sürüm denetiminde değilken yazıldı; o zaman yarıda kesilen yerinde bir
mutasyonun geri dönüş yolu olmazdı. Kopyalamak bugün de doğru varsayılan, çünkü
bir mutasyon koşusu üzerinde çalıştığın ağaca asla zarar verebilmemeli.
Koşucu yazıldığı gün **üç boş iddia** (biri bir alt dizgeyi eşliyordu, adı
değişen bir çağrı yine geçiyordu; bir sabitin hiç iddiası yoktu) ve yalnız proje
temiz bir ağaçtan koşulunca ortaya çıkan **iki görünmez bağımlılık** buldu.

## Bu depo neyi kanıtlamaz

Zincir hesap ve benzetimdir: tasarımı ve kodu doğrular, kartı değil. Kart o
günden bu yana kuruldu ama zincir onu göremez; bu yüzden
**[`uretim/_tezgah.md`](uretim/_tezgah.md)**'yi üreterek biter. Her kalem onu
*doğrulayamayan* kodun yanına, bir kabul ölçütüyle yazılır; ilk gün için
işaretlenenler en üstte listelenir. Aralarında:

- USB çekiliyken ±12 V besleme açıksa `+3V3` rayının kenetler üzerinden geri
  beslenmesi — beklenen ray **1.670 V**, yani ESP32'nin 3.60 V sınırının
  **1930 mV** altında. (B18 düzeltmesinden önce 18 mV'tu; 3.6 V'a yakın bir şey
  ölçersen bir seri direnç eksik demektir.)
- canlı veri satırındaki örnek sayısı: 200 ms'de gerçekten ~133 mü? (Gerçek
  kartta ~100, yani ~500 örnek/s — yukarıdaki tabloya bak.)
- pil testinin emniyet kesmesi: deşarjın ortasında kartı sıfırla ve yükün
  gerçekten ayrıldığını doğrula
- arayüzün gerçek bir tarayıcıda doğru çizilip çizilmediği

O liste elle tutulmuyor, üretiliyor — tezgah kalemlerini bildirmeyi bırakan
bir adım zinciri kırmızıya çevirir.

## Gereksinimler

| Araç | Kullanan |
|---|---|
| Python 3.14 (yalnız standart kütüphane) | bütün zincir, köprü, bütün üreteçler |
| [KiCad 10](https://www.kicad.org/) | şema, ERC, netlist — ve her benzetim için içindeki **ngspice** |
| `arduino-cli` + ESP32 çekirdeği 3.3.x | firmware derleme adımı |
| `avr-gcc` (Arduino AVR paketinden) | ölçüm matematiğini gerçek kod olarak koşturur |
| Node.js | arayüz / komut tutarlılığı adımı |

İki şey bu deponun **dışında** duruyor ve temiz bir klonda eksik olmaları
bekleniyor — ikisi de çökmeyle değil, açık bir mesajla karşılanıyor:

- `arduino-cli.exe`, proje köküne göre `../../.araclar/arduino-cli.exe`'de
  aranır (deponun dışındaki gizli bir araç klasörü)
- yazarın kişisel parça envanteri (`stok-takip/envanter.csv`); **üç** adım
  tasarımı onunla karşılaştırıyor. B11 ve B16 atladıklarını bildirir ve iddia
  sayılarını korur, yeşil kalırlar; **B9 erken çıkar ve zincir kırmızıya
  döner** — tezgah kalemlerini bildirmeden önce durur ve bu denetim sayım
  kilidinden ayrı olduğu için `--sayim-kilidi-yaz` onu susturmaz. Envanter
  adımının sana söyleyeceği her şey zaten
  [`BELGELER/2-malzemeler.html`](BELGELER/2-malzemeler.html)'de.

Araç yolları şimdilik Windows'a göre sabit yazılı (`C:\Program Files\KiCad\10.0\bin`).

## Güvenlik

### Elektrik — seni öldürebilecek kısım bu

> Bitmiş kutunun kuralı ([README.md](README.md#güvenlik)) daha basit ve daha
> sıkı: **şebekeye (220 V) hiç bağlama** — yalnız pil ve DC-DC ile beslenen
> devreleri ölç. Aşağıdaki inceleme nedenini anlatıyor.

**615 V öldürür ve bu kart yalıtımlı değil.** USB bağlıyken kartın toprağı
bilgisayarının toprağıdır — kartı şebekeye referanslı bir devreye (örneğin
yalıtımsız bir SMPS'in primer tarafına) bağlarsan bilgisayarına şebeke
vermiş olursun.

**Kartı pil + Wi-Fi ile yüzdürmek çözüm değil.** Arıza incelemesi tam bu
durumu ölçtü (senaryo D2): yüzdürmek **PC'yi kurtarır, seni değil** — kartın
kendisi o zaman şebeke potansiyeline çıkar ve *üzerindeki her nokta* tehlikeli
olur. 615 V, yüzen bir ölçü aleti için sınırın **14.6 katı**. Şebekeye
referanslı her ölçüm için erişilebilir metali olmayan **yalıtımlı bir kutu**,
güçlendirilmiş kaçak yolu için delikli plakette **5 atlanmış delik (12.7 mm)**
gerekir ve kart enerjiliyken ona dokunulmaz. Kurulum rehberi bunu herhangi bir
kurulum adımından önce, en başta söylüyor.

Arıza kipi incelemesi ([`uretim/sim3_ariza.py`](uretim/sim3_ariza.py),
111 iddia) **27 kötü kullanım senaryosunu** — ters gerilim, aşırı gerilim,
besleme kaybı, parça arızası, kullanıcı hatası — tek bir kabul ölçütüne göre
sayısallaştırıyor: *hiçbir tekil arıza ESP32'yi ya da PC'yi öldüremez.* O ölçüt
**ekipmanla** ilgili, seninle değil; yukarıdaki cümlenin var olma sebebi
senaryo D2.

### Ağ üzerinden

Ağ üzerinden tehlikeli komutlar (pil deşarjını başlatmak, kalibrasyon yazmak)
her zaman bir oturum belirteci artı özel bir başlık ister; bu, başka bir web
sayfasının kartını sürmesini engeller. **Parola isteğe bağlıdır ve
varsayılanda kurulu değildir** — seri konsoldan `Ns<parola>` ile kurana kadar,
ağında karta ulaşabilen herkes o komutları gönderebilir. Firmware bunu
açılışta yüksek sesle söylüyor.

**Deşarjı durdurmak ikisini de istemez** — belirteç yok, parola yok, her zaman.
Güvenlik kolaylıktan önce gelir.

Yukarıdaki paragraf **kartı** anlatıyor. PC köprüsü aynı kuralı kendi ucunda
uyguluyor, ama orada belirteç her şey gibi ağında düz metin olarak gidiyor —
başka sayfaların kartını sürmesini engeller, ağı dinleyen birini değil.

## Lisans

**MIT** — bkz. [LICENSE](LICENSE). Kullan, değiştir, sat; lisans notunu koru.

`arayuz3/vendor/` içindeki Vue 3.5.13 da MIT; aynı dosyada adı geçiyor.

⚠️ Lisans garantiyi reddediyor ve burada bu her zamankinden önemli: bu,
**elle kurulmuş, yalıtımsız ve 615 V ölçebilen bir alet**. Kendi güvenliğinden
sen sorumlusun.
