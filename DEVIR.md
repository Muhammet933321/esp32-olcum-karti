# Ölçüm Kartı — Devir Belgesi

> **Tarih:** 12 Eylül 2026 · **Devreden oturum:** Claude Opus 5 · **Durum:** Aşama 3
> tasarımı doğrulandı (**18/18**) · **ESP32-S3 GELDİ, bringup koşuldu (B26)**
> — firmware + arayüz kartta, **bir ADS1115 (`0x48`) breadboard'da**, kart ev
> ağında ve web katmanı doğrulandı. Bringup: **48 geçti / 3 kaldı / 1 atlandı**.
> Analog ön uç hâlâ kurulmadı.
>
> 🔴 **B26'da beş kusur bulundu, hepsi düzeltildi** — ikisi firmware'de, üçü
> belge/test tarafında, artı **beş koşucu kusuru** daha. En ciddi ikisi:
> **AP SSID'i MAC'ten gelmiyordu** (ilklenmemiş bellek) ve **ALERT/RDY kenar
> yönü tersti** — ikincisi örnekleme hızını 665 yerine **162**'de tutuyordu ve
> B20'nin düzeltmesinin *altında* duruyordu.
>
> **Ölçülen örnekleme hızı: 485/s** (tek ADS ile; ikinci ADS takılınca banda
> oturması bekleniyor). Kalan üç kırmızıdan ikisi eksik ADS'ten, biri
> **gerçek**: çift çekirdek kararının sinyali — 30 saniyede bir ~26 ms blokaj.
>
> **Kullanıcının okuyacağı belgeler `BELGELER/` klasöründe** — bu dosya
> mühendislik günlüğü, oraya kullanıcıyı yönlendirme.

---

## ⚠️ YENİ OTURUM — ÖNCE BUNU YAP

Bu belgeyi okuyup projeyi devralıyorsun. Sırayla:

1. **Doğrulama zincirini koştur.** Belgede yazan her şey bu zincire dayanıyor:
   ```
   cd projeler/olcum-karti/uretim
   python dogrula3.py          # AŞAMA 3 — GÜNCEL, B1..B25, 18/18, ~6 dk
   python dogrula2.py          # Aşama 2 — A1..A6, 6/6 geçmeli, ~70 s
   python dogrula.py           # Aşama 1 — S1..S9, 9/9 geçmeli, ~110 s
   ```
   **Aşama 3 güncel olan.** Yeşil değilse **önce onu düzelt**, yeni iş açma.

   > **Adım adım iddia sayıları burada ELLE tutulmuyor** — B23.3'ten beri
   > `uretim/beklenen_sayim.json` tutuyor ve zincir her koşuda birebir
   > karşılaştırıyor. **Sapma her iki yönde de kırmızı:** bir iddia
   > düşerse de, eklenirse de. (B22.2'de bir iddia düşerken başkası
   > eklenmiş, toplam sabit kaldığı için mutasyon kaçmıştı.) Bilerek
   > değiştirdiysen `python dogrula3.py --sayim-kilidi-yaz`.
   >
   > Bu blok daha önce elle yazılıydı ve bir kez **12/12**'de donmuştu.

   ⚠️ Zincir **tasarımı** doğruluyor, kurulmuş bir kartı değil. Donanım
   henüz kurulmadı.

2. **Depo GitHub'da — değişikliği göndermeyi unutma.**

   <https://github.com/Muhammet933321/esp32-olcum-karti> · MIT · public.
   Yerel depo `projeler/olcum-karti/`, remote `origin`.

   ```
   cd projeler/olcum-karti
   git add -A && git commit -m "..."
   git push origin main
   ```

   Kimlik **Git Credential Manager**'da kayıtlı (`Muhammet933321`) —
   şifre sorulmaz, push sessizce geçer. ⚠ **`gh` CLI kurulu ama oturum
   AÇIK DEĞİL** (`gh auth login` etkileşimli, ajan tamamlayamaz). Depo
   oluşturmak/ayar değiştirmek gerekirse kullanıcı tarayıcıdan yapar;
   **push için `gh` gerekmiyor.**

   ⚠ Yayınlamadan önce: `.gitignore` kullanıcının ölçüm günlüğünü
   (`kopru/arsiv/`) ve `fiyat_tara.py`'yi **bilerek** dışarıda tutuyor.
   Kişisel iz taraması bütün metin dosyalarını kapsamalı — B24'te
   `uretim/b15-arastirma.md` üç satırda Windows kullanıcı adı taşıyordu
   ve ilk tarama onu kaçırmıştı.

3. **Dosya düzenini bil** (5.12.32'de sadeleştirildi):

   | Klasör | Ne |
   |---|---|
   | **`BELGELER/`** | **Kullanıcının okuduğu yer** — HTML + PDF. `belge-uret.py` üretiyor, ELLE DÜZENLEME |
   | `kod/olcum-karti-a3/` · `sema3/` · `arayuz3/` | Güncel sürümler |
   | **`kopru/`** | **PC köprüsü** (B22.3) — seri↔SSE rölesi, disk arşivi, sürücü hakemi. `Kopru Baslat.bat` ile çalışıyor |
   | `uretim/` | Doğrulama zinciri + üreteçler |
   | **`uretim/_tezgah.md`** | **ÜRETİLİYOR** — kart kurulunca tezgahta ölçülecekler. Sayı dosyanın sonunda; elle düzenleme, kalemi ilgili adımın `tezgah(...)` çağrısına ekle |
   | `arsiv/asama1/` · `arsiv/asama2/` | Eski aşamalar, kendi zincirleriyle. ⚠ **`arsiv/` tamamen ölü değil:** `kurulum3-uret.py` biçimini `arsiv/asama2/kurulum2.html`'den okuyor (B23.3'te bulundu) |

   Bir sayı değişince `BELGELER/` kendiliğinden güncelleniyor (zincirin
   B9 adımına bağlı). Belgelere elle sayı yazma.

   `uretim/` içindeki B23 araçları:

   | Dosya | Ne |
   |---|---|
   | `tezgah.py` | Tezgah kalemi biçimi + toplayıcı yardımcıları. Konsolun çizemeyeceği karakteri **yazmadan önce** yakalıyor |
   | `mutasyon.py` | Mutasyon koşucusu — kaynağı bir **kopyada** bozup testin kırmızıya döndüğünü ölçüyor |
   | `sayim.py` | Adım özet satırlarının ortak ayrıştırıcısı (dört ayrı biçim) |
   | `gecici.py` | Kendini silen geçici dizin (`atexit`). Altı betik `mkdtemp` çağırıp silmiyordu |
   | `belge_menu.py` | `BELGELER/` gezinme şeridi — **tek kaynak**, iki üreteç paylaşıyor |

4. **Bu projenin altın kuralı: yeşil test bir şey kanıtlamaz.**
   Son üç adımda (B17, B20, B21) her seferinde, zincir yeşilken
   **gerçek ve büyük** kusurlar bulundu:

   * B17: iki ADS senkron değildi — PF=0.5'te güç %76 düşük
   * B20: kart 860 SPS'te değil **91 SPS**'te örnekliyordu; B17'nin
     bütün frekans bütçesi yanlış bir hıza dayanıyordu
   * B21: derleme önbelleği uyarıları **gizliyordu**; `--clean` eklenince
     hemen bir `uint16` taşması ortaya çıktı

   Yani: bir iddiayı görünce **kaynağına git**, mutasyon testi yap
   (sabiti boz, kırmızıya döndüğünü gör), ve "bu kusur neden bugüne
   kadar görülmedi?" diye sor. Ayrıntılı liste hafızada:
   *ölçüm kartı doğrulama disiplini*.

   B23.3'ten beri mutasyon testi **elle değil**:
   ```
   python mutasyon.py                 # hafif olanlar, ~15 s
   python mutasyon.py --adim B3       # tam zincir koşar (~12 dk) —
   python mutasyon.py --adim B23      # bu ikisi zincirin KENDİ korumalarını sınar
   python mutasyon.py --adim B22b     # tek adım
   python mutasyon.py --liste         # ne koşacağını yazar, koşmaz
   ```
   Kaynağı bir **kopyada** bozup testin kırmızıya döndüğünü ölçüyor;
   asıl ağaca dokunmuyor (proje git deposu değil, bir Ctrl-C geri dönüşü
   olmayan bir bozulma bırakırdı). Yeni bir iddia yazdığında
   `MUTASYONLAR` listesine onu yalanlayan değişikliği de ekle —
   **koşucu ilk turunda üç boş iddia buldu.**

5. **Bölüm 4'teki "bilinen kusurlar" listesini doğrula.** Gerçekten var mı? Ben yanılmış
   olabilirim.

6. **İnternetten araştır.** Bölüm 7'de başlıklar var. Benzer sistem kuranlar ne sorun
   yaşamış, buradaki mimari varsayımlar tutuyor mu, gözden kaçan ne var?

7. **Kendi hata avını yap.** Bu belgeye güvenme.

8. **Sonra kullanıcıya ne yapacağını anlat, onay al, öyle başla.**

### ✅ B15 bitti (2026-09-09) — sonuçlar **5.12.24**'te

`uretim/sim3_ariza.py` · 111 doğrulama · 27 senaryo · `dogrula3.py`'de B15.
**DEVİR'in kendi dört sayısı yanlış çıktı** ve şemada **üç kusur düzeltildi**
(R34/R35/R36/R38/R39 seri korumaları + C1 100nF→1nF). Kabul ölçütü sağlandı:
hiçbir bileşen arızası ESP32'yi ya da PC'yi öldürmüyor; ölen en pahalı parça
ADS1115 modülü (~45 TL, soketli). Tek istisna kartın izole olmaması (D1b) —
o donanımla değil prosedürle çözülüyor, **sayısallaştırıldı**.

### ✅ B11 bitti (2026-09-09) — sonuçlar **5.12.25**'te

7912 orta nokta regülatörü (şemada BLOK 9). LM358 tamponu planı iki
yerden kırıldı: çekme akımı (15 mA gerekli, 5 mA garanti) ve kapasitif
yük (700 nF, veri sayfası 100 pF). Yalnızca **50 mA cam sigorta + yuva**
alınacak.

### ✅ B16 bitti (2026-09-09) — sonuçlar **5.12.26**'da

`uretim/sim3_ortusme.py` · 41 doğrulama. İki kanal aynı sinyali farklı
süzüyordu (55.7 Hz'e karşı 8037 Hz): akım kanalı **örtüşüyordu** ve
reaktif yükte güç hatası PF=0.5'te **%155**'ti. Dirençli yükte fark
kendini götürdüğü için gözden kaçmıştı. Süzgeç ADS'in kendi koluna
taşındı (C4 100nF→1nF, yeni C18+C19+C20 = 1.32 µF, hepsi stokta).
Sonra %1.9. **Yeni açık karar: B16/F11** — hızlı yolun fark yükselteci
akım algılamasını %0.99 yüklüyor (B8'den beri var, hiçbir adım
modellememişti).

### ✅ B18 bitti (2026-09-09) — sonuçlar **5.12.27**'de

Kullanıcı B15/F6'yı onaylamıştı; B18 **uygulamadan önce ölçtü ve F6'yı
reddetti**: F6 hızlı akım yolunun tam ölçeğini de %33 kesiyordu
(252 → 169 mV) ve TL431
açık devre kalıntısını kapatmıyordu. Yerine **B18/F12**: R26/R33
2.7K → 10K ve yeni **R41 (1K boşaltma)**. B1 payı 18 mV → **1930 mV**,
**TL431'den bağımsız**, menzillerde hiçbir kayıp yok, satın alma yok.

### ✅ B19 bitti (2026-09-09) — sonuçlar **5.12.28**'de

Kullanıcı osiloskobun **çift yönlü** olmasını istedi. Bölücünün alt ucu
GND yerine VREF'e bağlandı ve R23 6.8K → 2.7K: **0…45.5 V tek yönlü**
yerine **−63.5 … +46.8 V**. Bedeli çözünürlük (**11.9 → 28.8 mV**,
ikisi de nominal tam ölçekten).
B19 kendi yazdığım dönüşüm formülündeki hatayı yakaladı (ofset VREF×N
değil VREF×(N−1); 0 V giriş −65 V okuyordu).

### ✅ B17 bitti (2026-09-09) — sonuçlar **5.12.29**'da

🔴 **Projenin en büyük ölçüm kusuru burada bulundu.** İki ADS1115 de
sürekli kipte, her biri kendi osilatörüyle koşuyordu; döngü yalnızca
akım çipini bekliyordu. Gerilim örneği 0…1.29 ms eski oluyordu ve
osilatör toleransı ±%10 olduğu için **sürükleniyordu** — 50 Hz'te
0…23°, gezinen. PF=0.5'te güç %76'ya varan ölçüde düşük okunuyordu
(ortalama %37). Dirençli yükte hata yalnızca %2.7 olduğu için
**kart "çalışıyor" görünüyordu.**

Çözüm: **tek atış kipi + eş zamanlı başlatma + kesirli gecikme.**
Ayrıca 1/|H(f)| ölçek düzeltmesi (`f<Hz>` komutu) ve menzil başına
faz kalibrasyonu (`F<örnek>`) eklendi. B16'nın "PGA değişiminde örnek
at" kalemi **geçersiz** çıktı — PGA hiç değişmiyor.

### ✅ B20 bitti (2026-09-10) — sonuçlar **5.12.30**'da

🔴 **B17'nin bütün frekans bütçesi yanlış bir hıza dayanıyordu.** Kart
860 SPS'te değil **91 SPS**'te örnekliyordu: (1) `loop()`'un başında
sürekli kipten kalma ölü bir bekleme her turda 4000 µs zaman aşımına
düşüyordu, (2) `COMP_QUE = 11b` ALERT/RDY pinini yüksek empedansta
tutuyordu (TI SBAS444E §7.3.8 bunu açıkça yasaklıyor). Varsayılan
`sebeke_hz = 50` ayarı **Nyquist'in üstündeydi**. Düzeltildi: **671 SPS**.

Ayrıca: `F` faz kalibrasyonu düşük hızda **aktif zararlıydı** (+%15.9,
kalibrasyon yükünün kendisinde) · otomatik menzil **AC'de saniyede 200
kez** geçiş yapıyordu (Vrms %12.2 düşük) · SSE işleyicisi `loop()`'u
**sonsuza kadar kilitliyordu** · `ortalama_oku()` aynı bayat yazmacı
okuyup "ortalama" alıyordu · imza yarım uygulanmıştı · skop adımı dört
dosyada **%6.92 ayrışmıştı** (DEVIR 5.12.28'in "26.9 mV"i yanlış, doğrusu
**28.8 mV**).

**`f` üst sınırı 400 → 100 Hz.** Bağlayıcı kısıt beklenen yerde değil:
Lagrange sarkması değil **faz kalibrasyonu**. Sabit gecikmeyle 50 Hz'te
kalibre edilen kart, ±%10 kondansatör toleransında 200 Hz'te PF=0.5'te
**%56** hata yapıyor. Geçerlilik bandı **40–70 Hz**.

11 ölçüm ajanı + 49 adversaryel çürütme ajanı koşturuldu; **çürütme
katmanı 27 bulguyu reddetti ve bu oturumun kendi iki mekanizma
açıklamasını düzeltti.**

### ✅ B21 bitti (2026-09-10) — sonuçlar **5.12.31**'de

**Yeni yetenek: pil kapasite testi** (ZB2L3 gibi, ama mAh **ve** Wh, 665 Sa/s
ve iç direnç ölçümüyle). Harici **taş direnç** yük, karttaki **IRFZ44N**
anahtarla kesiliyor; kesme gerilimi ayarlanabiliyor, deşarj eğrisi
tarayıcıda **IndexedDB**'de sınırsız birikiyor.

🔴 **Failsafe yönü B21'in en önemli kararı:** kapı GND'ye çekili, yani ESP32
ölürse/reset atarsa MOSFET **kapanıyor** ve pil boşalmayı durduruyor.

🔴 **Yeni sınır: pil gerilimi ≤ 38.5 V** (MOSFET Vdss 55 V, %70 pay). 48 V
paket reddediliyor. Soğutucusuz akım sınırı **6.55 A**.

🔴 **`test_firmware3.py`'ye `--clean` eklendi.** Arduino-cli önbellekten
derlediği için *"Derleme UYARISIZ"* iddiası önbellek durumuna göre
değişiyordu (aynı kod için 3, 2, 0 uyarı). Eklenince **hemen gerçek bir hata
çıktı**: PSRAM tamponu `24u*3600u` = 86400 ama alan `uint16_t` idi →
sessizce **20864**'e düşüyordu (24 saat yerine 5.8 saat).

Bütün parçalar **stokta** — tek eksik **taş direnç** (4.7–7.5 Ω / 10 W).

### ✅ B22 bitti (2026-09-10) — sonuçlar **5.12.32b – 5.12.38**'de

**Yeni yetenek: kart artık kendi web arayüzünü sunuyor.** Üç bağlanma kipi
var ve kullanıcıya görünen anlatımı `BELGELER/6-ag.html`'de:

1. **Kartın kendi Wi-Fi'si** (`OLCUM-KARTI-XXXX`, `192.168.4.1`) —
   bilgisayar gerekmiyor, arayüz kartın LittleFS'inden geliyor
2. **Kart ev ağında** (`http://olcum.local`) — 10 s deneyip AP'ye düşüyor
3. **USB köprü** (`kopru/`, `Kopru Baslat.bat`) — **tercih edilen**;
   bu kipte kartın Wi-Fi'si hiç açılmıyor, sayfayı PC yayınlıyor

Mimarinin **gerekçesi** 5.12.32b'de: `file://` bir `http://` sunucuya
ulaşamıyor, PWA HTTPS istiyor, Chrome LNA public→yerel'i kapatıyor. Bu üçü
birlikte *"sayfa karttan servis edilsin"* kararını zorunlu kıldı.

🔴 **Zincir 15/15 yeşilken DÖRT canlı kusur çıktı** — projenin altın kuralının
en pahalı kanıtı:

| # | Kusur | Nerede |
|---|---|---|
| K4 | Arayüz tarayıcıda **hiç açılmıyordu** (iki varlık 404) | 5.12.33 |
| K1 | Kart 665 değil **500 SPS**'te örnekliyordu — `WebServer`'ın kendi `delay(1)`'i | 5.12.34 |
| K2 | `faz_kal` **örnek** cinsindendi ama sabit bir **zamanı** düzeltiyordu (+1.744°) | 5.12.34 |
| K3 | Çıplak `g`/`i` komutu bir kanalı **kalıcı tuğluyordu** | 5.12.34 |

🔴 **Güvenlik kararı kullanıcınındı:** tehlikeli komutlar **jeton + parola**
istiyor (USB-only değil). **Tek istisna `p0`** (pil deşarjını durdur) —
her zaman parolasız çalışıyor, çünkü emniyet kolaylıktan önce gelir.

### 🔌 B25 — ESP32 için bringup koşucusu HAZIR (2026-09-11) — **5.12.41**

Kart gelmeden hazırlandı. `uretim/tezgah_kart.py` gerçek karta seri + HTTP
üzerinden bağlanıp **27 otomatik denetim** yapıyor; aşamalı (çıplak ESP32 →
+ADS → +analog ön uç). Kullanımı bu bloğun altındaki
**"🔌 ESP32 geldiğinde"** bölümünde.

🔴 **Koşucunun kendisi zincirde sınanıyor** (B25, 15 kasıtlı bozuk senaryo).
Yanlış bir bringup testi testsizlikten kötüdür. Öz-test yazılırken koşucuda
**üç gerçek hata** buldu — biri "aynı kapsam hatası, üçüncü kez".

🔴 **`loop_azami_us` artık bir komut mesafesinde** — aylardır açık duran
çift çekirdek kararını kapatacak tek ölçüm.

### ✅ B24 — GitHub'da yayında (2026-09-11) — sonuçlar **5.12.40**'ta

<https://github.com/Muhammet933321/esp32-olcum-karti> · MIT · 180 dosya.
İngilizce tanıtım `README.md`, Türkçe rehber `README.tr.md`.

🔴 **Yayın öncesi iki bağımsız denetim 129 doğrulanmış bulgu çıkardı** ve
en pahalıları yayınlanmış belgelerdeki **yanlış emniyet bilgisiydi**:
*"pil + Wi-Fi ile yüzdür"* şebeke ölçümünün çözümü diye sunuluyordu, oysa
B15/D2 bunu ölçüp **"PC kurtulur, KULLANICI kurtulmaz"** demişti —
**yalıtımlı kutu şartı hiçbir belgede yoktu.** Ayrıca ağ sayfası parola
korumasının varsayılan olarak **açık** olduğunu ima ediyordu; değil.

### ✅ B23 bitti (2026-09-10) — sonuçlar **5.12.39**'da

Donanım beklerken **elle yazıldığı için ölçümle bağı kopmuş bilgi** kaynağa
bağlandı. Üç şey kalıcı:

* **`uretim/_tezgah.md` ÜRETİLİYOR** (B23'te 72 kalem / 17 adımdı; güncel
  sayı dosyanın kendisinde). Her tezgah
  kalemi, onu **doğrulayamayan kodun yanında** yaşıyor. DEVIR'de artık liste
  yok, yönlendirme var — çünkü buradaki elle yazılmış 8 satırlık tablo
  B20/B21'de donmuştu ve B22'nin üç bölümü **içermediği** kalemlere atıf
  yapıyordu.
* **`uretim/mutasyon.py`** — mutasyon testi artık elle değil. Kurulduğu gün
  **üç boş iddia** ve **iki görünmez bağımlılık** buldu.
* **`uretim/beklenen_sayim.json`** — iddia sayısı kilidi, sapma **iki yönde
  de** kırmızı (1027 iddia).

🔴 Bulunan somut kusurlar: **B3 şema üretimi çökse bile yeşil kalıyordu** ·
belgedeki firmware boyutu **481 935 B**, gerçek **1 067 423 B** (2.2 kat) ·
**826 sızmış geçici dizin** · `collectHeaders` iddiası alt dizgeydi ·
`AG_MDNS` için **hiç iddia yoktu** · güncel kurulum kılavuzunun CSS'i
**`arsiv/`'den** okunuyor · `kurulum3-uret.py` `BELGELER/`'i yaratmadan
yazıyordu.

### 🎯 Şu an sıradaki iş

**Zincir yeşil (18/18). ESP32 geliyor — sıradaki gerçek adım kartı kurmak.**

> ⚠️ **Buraya bir kez "tasarım tarafında yapılacak iş kalmadı" yazıldı
> (B21 sonrası) ve ardından ALTI bölüm boyunca büyük kusurlar bulundu:**
> arayüz tarayıcıda hiç açılmıyordu (B22.0) · kart 665 değil **500 SPS**'te
> örneklıyordu (B22.1/K1) · faz hatası B17'nin kendi ölçütünün **1.74
> katıydı** (K2) · çıplak `g` kanalı **kalıcı olarak öldürüyordu** (K3) ·
> WiFi bir kez bile açılmamıştı ve SSE yalnız `D` satırını taşıyordu
> (B22.4) · komut ucu hiç yoktu.
>
> Bu cümleyi bir daha yazma. Doğrusu: *"bugün bilinen iş kalmadı"* — ve
> bilinmeyeni bulmanın yolu zincire güvenmek değil, **mutasyon testi**.
>
> B23'ten beri bunun bir aracı var: **`python mutasyon.py`**. Kurulduğu
> gün üç boş iddia ve iki görünmez bağımlılık buldu. Yeni bir iddia
> yazdığında `MUTASYONLAR` listesine onu **yalanlayan** değişikliği de
> ekle — yoksa iddianın ısırıp ısırmadığını kimse bilmiyor.

#### 🔴 Kullanıcı kararı bekleyen kalemler

**1. Faz kalibrasyonunu τ eşleşmezliği olarak saklamak** (B20'den, 5.12.30).
Bugün `F` komutu SABİT bir zaman gecikmesi saklıyor; düzelttiği şey ise
iki RC'nin arctan farkı — ikisi yalnızca kalibrasyon frekansı civarında
örtüşüyor. Bu yüzden geçerlilik bandı **40–70 Hz** ve `f` komutu 100 Hz'de
kesiliyor. τ eşleşmezliği olarak saklanırsa bant genişler; maliyeti iki
`atanf()`. **Yapılmadı** çünkü `F`'in anlamını değiştirir ve tezgahta
doğrulanmadan yapılmamalı. Ölçümler 5.12.30'da hazır.
⚠ B22.1 `faz_kal`'ı **örnek → mikrosaniye**'ye çevirdi (periyot bağımlılığı
kalktı) ama τ modeline geçmedi; bu karar hâlâ açık.

**2. Çift çekirdeğe geçilecek mi** (B22.1'den) — ✅ **ÖLÇÜLDÜ, CEVAP EVET
(B26, 2026-09-11).** Eşik `loop_azami_us` **> 20 000 µs** idi.

⚠ Ölçüm yöntemi B26'da **değiştirilmek zorunda kaldı**: eski sayı açılıştan
beri sıfırlanmayan koşan maksimumdu ve ısınmayı içeriyordu — taze açılışta
**18 203 µs** (eşiğin ALTINDA), dakikalar sonra **30 397 µs** (ÜSTÜNDE).
Aynı kart iki farklı cevap veriyordu. Firmware'e `K` komutu eklendi
(sayaçları sıfırlar, eski değerleri basarak) ve koşucu artık sıfırlayıp
**45 sn kararlı hal** ölçüyor.

**Sonuç: sıfırlamadan sonra 45 sn'de yine 30 382 µs.** Olay açılış artığı
değil, kararlı halde ~45 sn'de bir tekrarlıyor → **ölçüm döngüsü çekirdek
1'e taşınacak.** Açılan risk sınıfı (yarış koşulları) 5.12.34'te
adlandırıldı; **iş henüz yapılmadı.**

⚠ `atlanan_ms` **hep 0** — enerji penceresi kaçmıyor, yani aciliyet enerji
sayacında değil, skop/örnekleme sürekliliğinde. Ölçüm ADS'ler bağlı
değilken alındı; 30 ms'lik blokaj I²C'den gelemez (WiFi/mDNS bakımı
muhtemel), ADS eklemek iyileştirmez.

**3. Web parolası politikası** (B22.4'ten). Bugün `Ns<parola>` ile
kuruluyor ama **kurulmazsa yetkilendirme kapalı** — açılışta yüksek sesle
uyarılıyor. Parola zorunlu kılınsın mı, yoksa jeton + `Host` beyaz listesi
yeterli mi? TLS olmadığı için parolanın koruduğu şey *"evdeki başka biri
yanlışlıkla basmasın"*; LAN'daki bir dinleyiciye karşı koruma değil.

### ✅ ESP32 geldi — bu akış 2026-09-11'de koşuldu (B26)

> **Bu bölümün tamamı bir kez koşuldu ve çalıştı.** Sonuçlar ve bulunan üç
> kusur **5.12.42**'de. Aşağısı artık *"ilk gün"* değil, **tekrar yükleme
> yordamı** — firmware değiştiğinde aynı sırayla koşulur.
>
> **Kartın kimliği (esptool ile okundu):** ESP32-S3 QFN56 rev v0.2 ·
> flash 16 MB · PSRAM 8 MB oktal · MAC `…:96:9c` · **COM6**,
> köprü çipi **CH343** (`VID_1A86`/`PID_55D3`).
>
> **Kart iki Type-C soketli, doğru olan COM yazan.** ⚠ *"Bir COM portu
> belirdi"* doğru sokete takıldığının kanıtı DEĞİL: yerel USB soketi de
> port açar (`VID_303A`) ama **sessiz** kalır. Ayırt edici ölçüt **VID**.

**1 · Firmware'i yükle.** Tam FQBN şart — varsayılanlar çalışmaz:

```bash
cd projeler/olcum-karti/uretim
python yukle.py --liste     # ne yapacağını gösterir
python yukle.py             # derle + yükle (portu kendi bulur)
```

⚠️ **Çıplak `arduino-cli` komutu çalışmaz** — ikili PATH'te değil,
`Elekronic/.araclar/arduino-cli.exe` altında. `yukle.py` hem onu buluyor
hem FQBN'i `hedef2.py`'den okuyor, yani ikisi de elle yazılmıyor.

FQBN tuzaklı: `FlashSize=16M` olmadan LittleFS'in `0x310000` ofseti 4 MB
sınırına düşer, `PSRAM=opi` olmadan 8 MB PSRAM hiç açılmaz. Kart
**ESP32-S3 N16R8** olmalı.

**2 · Arayüzü karta yaz.**

```bash
cd uretim
python arayuz-uret.py     # LittleFS görüntüsünü paketle
python arayuz-yaz.py      # 0x310000'e yaz (esptool)
```

⚠️ **İKİ USB SOKETİ VARSA: UART/COM soketine takın, yerel USB'ye değil.**
Firmware `Serial`i UART köprüsünde tutuyor — `hedef2.py` `CDCOnBoot`/
`USBMode` seçeneklerini **bilerek** eklemiyor (yerel CDC tezgah ilk
açılışını bozabilir, bu iş 4.11'de ayrı ele alınacak). Yanlış sokette
hiçbir satır gelmez ve boşuna sürücü aranır. Aynı sebeple `--sifirla`'nın
DTR/RTS reset'i **UART soketinde çalışır**.

**3 · Bringup koşucusunu çalıştır** — elle denenmesi gerekmeyen her şeyi
otomatik sınıyor:

```bash
python tezgah_kart.py --liste            # ne yapacağını göster
python tezgah_kart.py --sifirla          # aşama 0: çıplak ESP32
python tezgah_kart.py --sifirla --asama 1        # ADS'ler bağlıyken
python tezgah_kart.py --sifirla --http olcum.local   # web katmanı da
```

**27 denetim** (güncel sayı: `python tezgah_kart.py --liste`). Açılış afişi
(PSRAM boyutu, LittleFS, ağ kipi), komut
yüzeyi, çıplak `g`/`i` reddi (K3 tuğlalama), `R` onay kapısı, I²C taraması,
`D` satırının biçimi/hızı/**örnek sayısı**, ve web tarafında CSRF · jeton ·
`p0` serbestliği · Host beyaz listesi.

⚠ Açılış afişi yalnızca açılışta basılıyor. `--sifirla` DTR/RTS ile reset
denemesi yapıyor ama **yerel USB CDC'li kartlarda bu çalışmaz** — o zaman
EN düğmesine basıp komutu tekrar çalıştırın. Afiş alınamazsa PSRAM ve
LittleFS denetimleri **atlanır**, kırmızı olmaz.

🔴 **Koşucu hiçbir aşamada yük sürmüyor.** Pil deşarjını başlatan komut
otomatik gönderilmiyor; failsafe ve baypas denetimi elle yapılacak.

**4 · İlk gün ölçümleri** — `uretim/_tezgah.md`'nin başındaki `[!]` işaretli
9 kalem. Bunlar multimetre isteyen, koşucunun yapamadığı şeyler. En kritiği:
**+3V3 rayının geri beslenmesi** (USB'yi çıkar, 24 V takılı bırak, rayı ölç
— beklenen 1.670 V).

**5 · Çift çekirdek kararı.** Koşucu `K` satırından `loop_azami_us` okuyup
**20 000 µs** eşiğiyle karşılaştırıyor. Üstündeyse ölçüm döngüsü çekirdek
1'e taşınacak (5.12.34); altındaysa **yapılmayacak**. Bu tek ölçüm, aylardır
açık duran bir mimari kararı kapatıyor.

#### Sıradaki iş: DONANIMI KUR (B10)

Kartın elektroniği tam. Kurulum kılavuzu `BELGELER/4-kurulum.html`.

✅ **Taş direnç geldi (2026-09-11).** Pil testi yükü 18650 için
4.7–7.5 Ω / 10 W isteniyordu: **2× 3.3 Ω 11 W seri = 6.6 Ω / 22 W**
aralığın tam ortasına düşüyor (stokta 3 adet 3.3R 11W var). 18650'de
3.7 V / 6.6 Ω ≈ 0.56 A, 2.1 W — 22 W'lık kapasitenin çok altında.
Ayrıca 1R ve 0.1R taş dirençler de geldi. 12 V akü için istenen
10–15 Ω / 50 W hâlâ yok.

⚠️ Değerleri **ölçerek doğrula**: ürün sayfası 3.3R diyor ama URL slug'ı
33R diyordu. Zaten `_tezgah.md` "lehimlemeden önce her direnci
ohmmetreyle geç" diyor.

**Kalan satın alma listesi — dört kalem**
(`BELGELER/2-malzemeler.html` güncel listeyi üretiyor; oradaki
"Sipariş edildi" tablosu artık **boş**):
820K ×6, 8.2K ×1, BAT85 ×4, 50 mA sigorta ×1.

⚠️ **Stoktaki 820K yerine geçmez:** R038 ×30 var ama **2W**; HV bölücüsü
(4.9 MΩ zinciri) **metal film %1** istiyor — tolerans ve sıcaklık
katsayısı doğrudan ölçüme giriyor.

Sarf tarafı: **delikli plaket geldi** (6x13 ×3, 10x10 ×2, 5x5 ×2);
izopropil alkol, lehim teli, yedek ESP32-S3 hâlâ listede.

#### Kurulum sonrası ilk ölçülecekler → **`uretim/_tezgah.md`**

> **Bu listenin burada elle yazılmış bir kopyası yoktu — vardı ve dondu.**
> B20/B21 döneminde yazılan 8 satırlık tablo B22'nin 17 ölçümünü hiç
> görmedi; üstelik B22.3/B22.4/B22.5'in üçü de *"tezgah listesinde"*
> diyerek **içermediği** kalemlere atıf yapıyordu. Bu, projenin defalarca
> yandığı **ayrışma sınıfının belge sürümü**.

Artık her tezgah kalemi, onu **doğrulayamayan kodun yanında** yaşıyor
(`tezgah(...)` çağrısı, ilgili adımın betiğinin sonunda). `dogrula3.py`
bunları toplayıp ekrana basıyor ve `uretim/_tezgah.md`'yi üretiyor.

* **Liste:** `uretim/_tezgah.md` — adım adım, kabul ölçütleriyle
* **İlk gün:** aynı dosyanın başındaki tablo; `[!]` işaretli kalemlerden
  **türetiliyor**. Sırası zincir sırası, öncelik sırası değil — kalemler
  arası elle bir sıralama tutulsa yine bayatlardı
* **Yeni kalem eklemek:** o adımın betiğindeki `tezgah(...)` çağrısına
  ekle. Buraya değil.

Bir adım hiç kalem basmazsa `dogrula3.py` **kırmızı** dönüyor — taban
çizgisi `ADIMLAR`'ın kendisi, elle yazılmış bir liste değil.

#### Açık duran iş kalemleri (aceleci değil)

| Kaynak | İş |
|---|---|
| B16 (5.12.26) | **Karar:** hızlı yolun örtüşme payı yeterli mi · **Karar:** B16/F11, R27/R29 yüklemesi (%0.99) |
| B21 (5.12.31) | Sıcaklık ölçümü (envanterde sensör yok) · elektronik yük (sabit akım) · kayıt hızı arayüzden ayarlanamıyor · **şarj yönünde test** (sayaç işaretli ama şarj kaynağı yok) |
| B14 (5.12.20) | Hızlı skop (MHz) — harici ADC, açık ihtimal |
| B12 / B13 | İkili aktarım + USB CDC · sürekli hızlı yol — **donanım çalıştıktan SONRA** |
| **B22.6** (planda) | **Köprünün ağ yukarı-akışı** — kart uzaktayken (615 V ölçüyor, kablo çekilemez) PC ona WiFi ile bağlansın. `kopru/kart_baglanti.py`'ye `AgKart` + `POST /kopru` kaydı. **Ertelendi:** donanımsız uçtan uca doğrulanamıyor |
| **B22.5** (5.12.38) | `?demo` kipi **karttan çalışmıyor** — `sahte-kart.js` görüntüye bilerek konmadı (15 936 B). Geliştirme aracı, kartta anlamsız; ama kullanıcı denerse sebebini görüyor |
| **B22.4** (5.12.37) | Kartın `/skop.bin` ucu var ama **derin bellek (PSRAM) hâlâ kullanılmıyor** — skop 4000 örnekte sabit. B14/B12 ile aynı yere bakıyor |
| **B23.3** (5.12.39) | `mutasyon.py` kapsamı dar: her adımın yalnızca bir-iki iddiası sınanıyor. Yeni iddia yazan her bölüm listeye kendi yalanlamasını eklemeli. ⚠ Sayıyı buraya **yazma** — `python mutasyon.py --liste` söyler (B26'da "10 mutasyon" yazıyordu, gerçek 15'ti) |
| **B26** (5.12.42) | `mutasyon.py` geçici kopyayı `projeler/_mutasyon-<pid>` diye açıyor ve **dizin varsa çöküyor** (`FileExistsError`). Windows PID'leri geri dönüştürdüğü için bir kez tetiklendi. `dirs_exist_ok=True` ya da kopyalamadan önce temizleme gerekiyor |
| **B26** (5.12.42) | `yukle.py` derlerken `--clean` geçmiyor, zincirdeki `test_firmware3.py` geçiyor (B21 dersi: önbellek uyarı gizler). Bugün zararsız çıktı ama ayrışma yüzeyi duruyor — `--temiz` bayrağı eklenebilir |
| **B23.3** (5.12.39) | `kurulum3-uret.py` biçimini **`arsiv/asama2/kurulum2.html`**'den okuyor. Taşınmadı (yeni ayrışma yüzeyi açardı) ama arşiv taşınır/silinirse **buraya bakılacak** — dosya yoksa açık bir hatayla düşüyor |
| **B23.2** (5.12.39) | `index.html`'deki *"hangi belgeye bakmalıyım"* tablosu `MENU`'den **türetilmiyor**, elle yazılıyor. Bir denetim ayrışmayı kırmızı yapıyor ama tablo hâlâ iki temsil |
| **B23.1** (5.12.39) | `_tezgah.md`'nin *"İlk gün"* sıralaması **zincir sırası**, öncelik sırası değil. Öncelik gerekirse `[!]` işaretine bir derece eklenmeli |

### Bu belgeyi yazan oturum kendi iddialarından dördünü düzeltmek zorunda kaldı

| Yanlış dediğim | Doğrusu |
|---|---|
| "Tam ölçek 45 V" | ADS girişi VDD ile sınırlı → **32.2 V** |
| "TL072 ve NE555 stokta yok" | CSV'de yok ama **siparişte var, yolda** |
| "İki ADS modülü var, R8/R9 tak" | **Üç modülü var**; karar modül sayısına bağlı (bkz. 4.7) |
| "Kelvin gerekli çünkü statik lehim direnci %6.7 hata yapıyor" | O kısım **kalibre edilebilir**; gerçek sebep yüke bağlı termal sürüklenme ve 10 A referans gerektirmesi |

**Buradaki hiçbir sayıyı doğrulamadan kabul etme.** Her sayının kaynağı belirtildi; kaynağa git.

---

## 0. Bir bakışta

Ölçüm kartı: **voltmetre · ampermetre · wattmetre · enerji sayacı · osiloskop**. İki aşama
tasarlandı ve uçtan uca doğrulandı; hiçbiri henüz fiziksel olarak kurulmadı.

| Aşama | MCU | ADC | Durum |
|---|---|---|---|
| 1 | Arduino Uno/Nano (ATmega328P) | dahili 10 bit | ✅ 9/9 adım, 159 doğrulama |
| 2 | ESP32-S3 N16R8 | 2× ADS1115 (16 bit) + dahili 12 bit | ✅ 6/6 adım, 173 doğrulama — **parça yolda** |
| 3 | aynı | + 3. ADS1115 | 📋 verim ölçümü için yer ayrılmıştı — **artık aktif hedef** |

**Yön değişti.** Kullanıcının multimetresi var (ANENG AN8000), o yüzden DMM işlevleri
(direnç, kapasite, diyot, süreklilik, AC) **istenmiyor**. Yeni odak: gerilim ve akımı
**olabildiğince yüksek örneklemeyle** ölçmek, **osiloskop / wattmetre / eğri çizici**
konusunda iyi olmak, üstüne dört SMPS-odaklı yetenek eklemek.

Kart **delikli plakete kalıcı** kurulacak (breadboard değil).

---

## 1. Yön değişikliği — önce bunu oku

### 1.1 Neden değişti

Kullanıcı zaten bir multimetre sahibi. Geçen turda "kartın yapamadıkları" diye altı
işlev listelemiştim (AC gerilim/akım, direnç, süreklilik, diyot, kapasite, akımda otomatik
kademe) ve hepsinin eklenebileceğini gösteren ayrıntılı bir analiz yapmıştım.
**Kullanıcı bunları reddetti** — multimetresi zaten yapıyor. Onun yerine multimetrenin
**yapamadığı** şeylerde iyi olmak istiyor.

### 1.2 Referans cihaz: ANENG AN8000

Bu, kalibrasyon tavanını belirlediği için kritik:

| Özellik | Değer |
|---|---|
| Sayım | **4000** |
| DC gerilim 400 mV / 4 V / 40 V | **±(%0.5 + 4 hane)** |
| DC gerilim 400 V / 600 V | ±(%0.8 + 4 hane) |
| Okuma hızı | saniyede 3 |
| Ayrıca yapıyor | AC V/I, direnç, kapasite, diyot, süreklilik, frekans, duty cycle |

*Kaynak: [ANENG AN8000 kullanım kılavuzu](https://manuals.plus/asin/B082HMQNNX) ve
[ürün sayfası](https://www.amazon.com/ANENG-AN8000-Digital-Multimeter-4000/dp/B082HMCHRC).
Yeni oturum bunu teyit etsin.*

**12 V ölçümünde:** 40 V kademesinde çözünürlük 0.01 V → hata = %0.5×12 + 4×0.01 =
60 mV + 40 mV = **±100 mV = ±%0.83**.

### 1.3 Bunun kritik sonucu

Kart AN8000'e karşı kalibre edilirse **mutlak doğruluğu ±%0.8'e çakılır** — oysa kartın
çözünürlüğü bunun çok altında. Yani AN8000'den çok daha iyi **çözünürlük**, ondan
kalibre edilirse çok daha kötü **mutlak doğruluk**.

> ⚠️ **DOĞRULANMAMIŞ SAYI — yeni oturum bunu hesaplasın.** Oturumun erken bir turunda
> "200 ms ortalamada 0.22 mV, 146 000 sayım" demiştim, **ama doğrulama zinciri bu sayıyı
> üretmiyor** ve ben şimdi yeniden türetemedim.
> Zincirin gerçekten söylediği (`kanit/a2-tam-dogrulama.txt:137`): *200 ms pencere =
> 172 örnek → √N = 13.1×*. Gerilim adımı PGA ±2.048'de 981.6 µV. Saf kuantalamayla
> 981.6/13.1 = **74.9 µV** çıkar (≈429 000 sayım), 0.22 mV değil.
> Fark muhtemelen ADS1115'in 860 SPS'teki **gerçek gürültüsünden** geliyor (veri sayfası:
> yüksek veri hızında efektif çözünürlük 16 bitin belirgin altında) — ama bunu
> **veri sayfasının gürültü tablosundan doğrula ve `tasarim2.py`'ye bir `kural()` olarak
> ekle.** Akım kanalları için gürültü tabanı zaten hesaplanıyor (µA kademesi 0.0596 µA);
> gerilim için aynısı yok.

**Kullanıcının laboratuvar erişimi var** ("ulaşabileceğim laboratuvar tipi de var,
kalibrasyon için oraya gidebilirim"). **Kalibrasyon oraya yapılmalı.** Kartın ±%0.1
hedefi ancak böyle anlamlı olur.

> Bu ayrım önemli: **çözünürlük** kartın kendi özelliği, **doğruluk** kalibrasyon
> referansının özelliği. Kart, AN8000 ile kalibre edilse bile ondan çok daha iyi
> *tekrarlanabilirlik* ve *fark ölçümü* verir — sadece mutlak değeri onunkine bağlanır.

> 🌟 **Ama bu tavan ORAN ölçümlerinde büyük ölçüde kalkıyor.** Verim (η) gibi bir
> büyüklükte dört kanalı *aynı* DMM ile *aynı* noktada kalibre edersen, DMM'in kazanç
> hatası oranda birinci mertebede yok olur: AN8000 ile ±0.352 puan, 6.5 haneli masa
> referansıyla ±0.352 puan — **fark yok**. Ayrıntı **5.7 → Verim ölçer** bölümünde.
> Yani laboratuvar erişimi *mutlak* ölçümler (voltmetre/ampermetre) için kıymetli,
> *oransal* ölçümler için neredeyse gereksiz.

### 1.4 Rafa kalkanlar

Aşağıdakiler için geçen turda ayrıntılı analiz yapıldı. **Yeni oturum bunları tekrar
analiz etmesin**; kullanıcı isterse özet burada:

| İşlev | Karar | Analiz özeti (istenirse) |
|---|---|---|
| Direnç | ⏸️ rafta | ESP32 GPIO'nun Hi-Z olabilmesi mux'a gerek bırakmıyor; oransal ölçüm ray ve GPIO empedansını sadeleştiriyor. 0.5 Ω–1 MΩ, ±%0.3. |
| Süreklilik | ⏸️ rafta | Direnç modunun eşiği. Buzzer gerekiyor (kayıtta yok). |
| Diyot | ⏸️ rafta | Aynı devre. 3.3 V rayı beyaz LED'de sınırda. |
| Kapasite | ⏸️ rafta | RC şarj eğrisine üstel fit, 50 pF–20 mF ±%2-5. Dolu kondansatör koruması şart. |
| AC V/I | ⏸️ rafta | Ayrı AC-kuplajlı kanal + 1.65 V bias. **Şebeke için izolasyon zorunlu** — ZMPT101B/ZMCT103C. |
| Akımda oto-kademe | ⚠️ **kısmen devam** | PGA oto-kademesi (16:1, sıfır donanım) hâlâ mantıklı ve **yapılmalı**. Fiziksel şönt anahtarlama rafta. |

---

## 2. Şimdiye kadar yapılanlar — TEKRAR ETME

### 2.1 Doğrulama felsefesi

Kullanıcının ilk isteği **"halisünasyon görmeyeceğin şekilde kanıtla"** idi. Bu yüzden
proje sıradışı bir disiplinle kuruldu:

- **Her iddia çalıştırılabilir bir testten geliyor.** `uretim/` altındaki betikler hem
  tasarım belgesi hem test. `tasarim2.py` docstring'i: *"Bu betik TASARIM BELGESIDIR ve
  ayni zamanda BIR TESTTIR."*
- **Şema elle çizilmiyor**, `sema-uret.py` / `sema2-uret.py` betikleri KiCad dosyasını
  sıfırdan yazıyor. Böylece şema ile tasarım sabitleri ayrışamıyor.
- **Firmware aritmetiği platform bağımsız** (`kod/olcum-karti-a2/olcum2.h` — `int` ve
  `double` yasak, her yerde `int16_t`/`int32_t`/`uint64_t`/`float`). Bu sayede **aynı
  kaynak** hem gerçek ESP32-S3 derleyicisiyle derleniyor, hem de sıfırdan yazılmış bir
  AVR emülatöründe bit-birebir koşturulabiliyor.
- **AVR emülatörü kendisi doğrulanmış**: `test_avr.py` (S8), gerçek `avr-gcc` çıktısına
  karşı 39/39 bit-birebir.
- **Testler kaynaktan sabit okuyor.** Ör. `test_skop_arayuz.js` `SKOP_ADET`, `SKOP_HZ`,
  `SKOP_TAVAN`, `BOLME_ORANI` değerlerini `.ino` ve `.h` dosyalarından regex'le çekiyor —
  firmware'de bir sabit değişirse test peşinden gidiyor, sessizce ayrışamıyorlar.

**Yeni oturum bu disiplini bozmasın.** Bir sayı iddia edilecekse, onu üreten bir test olsun.

### 2.2 Aşama 1 — ATmega328P (tamam)

`uretim/dogrula.py` → **9/9 adım, 159 doğrulama**

| Adım | Ne doğruluyor | Araç |
|---|---|---|
| S1 | TL431 referansı ve AREF yükü | ngspice |
| S2 | Bölücü + koruma kelepçesi + örtüşme süzgeci | ngspice |
| S3 | Şönt + LM358 akım katı | ngspice |
| S4 | Firmware aritmetiği | numpy float32/uint64 |
| S5 | Şema: ERC + netlist (polarite!) | kicad-cli |
| S6 | Firmware derleme, 0 uyarı, SRAM payı | arduino-cli |
| S7 | Arayüz mantığı | node |
| S8 | **AVR emülatörünün kendisi** | avr-gcc karşılaştırması |
| S9 | **Kart uçtan uca** (+S10 arayüz) | tüm zincir, 186 400 010 AVR çevrimi |

Menzil: 0–27.2 V / 26.6 mV adım, 0–939 mA, osiloskop 8 bit ~8 kHz.
Derleme: 8444 B flash, 1261 B SRAM, 787 B boş, 0 uyarı.

### 2.3 Aşama 2 — ESP32-S3 + ADS1115 (tasarım tamam, kurulmadı)

`uretim/dogrula2.py` → **6/6 adım, 173 doğrulama**

| Adım | Ne doğruluyor | Sonuç |
|---|---|---|
| A1 | Tasarım, menzil, hata bütçesi, Kelvin gerekçesi | 24/24 |
| A2 | Giriş koruması — **4 seçenek tarandı, ilk seçim elendi** | 11/11 |
| A3 | Şema: ERC (0 ihlal) + netlist (polarite, ADS adresleri) | 33/33 |
| A4 | Uçtan uca + gerçek ESP32-S3 derlemesi | 18/18 |
| A5 | Osiloskop protokolü → gerçek arayüz; zaman tabanı merdiveni; **ikilide ölü kod denetimi** | 45 |
| A6 | **Osiloskop ölçüm matematiği** — gerçek kod AVR emülatöründe, analitik dalgalara karşı | 32 |

Firmware: **473 817 B flash (%36), 47 000 B RAM (%14), 0 uyarı.**
*(RAM artışı osiloskopun 2 × 4000 örneklik halka tamponundan.)*

**Menzil ve çözünürlük** (`kanit/a2-tam-dogrulama.txt`'ten):

| Kanal | Tam ölçek | Adım |
|---|---|---|
| Gerilim, PGA ±2.048 (çalışma kademesi) | 32.17 V | 981.6 µV |
| Gerilim, PGA ±0.256 (oto-kademe alt ucu) | 4.02 V | 122.7 µV |
| Akım, 10R şönt | 26 mA | 0.78 µA |
| Akım, 1R | 256 mA | 7.81 µA |
| Akım, 0.1R | 2.560 A | 78.12 µA |
| Akım, 15 mΩ | 11.547 A | 520.8 µA |
| Osiloskop (ESP32 ADC) | 48.7 V | 11.9 mV @ 83 333 Sa/s |

### 2.4 Bulunmuş gerçek kusurlar — yeniden keşfetmeye çalışma

Bunlar **bulundu ve düzeltildi**. Listeyi vermemin sebebi, yeni oturumun aynı avı
tekrarlayıp zaman kaybetmemesi.

**Aşama 1'de yakalanan altı hata:**

| # | Hata | Nasıl yakalandı |
|---|---|---|
| 1 | AREF seri direnci referansı %12.8 kaydırıyordu | ngspice (S1) |
| 2 | Bölücü kondansatörü osiloskop kipini öldürüyordu | ngspice (S2) |
| 3 | Her iki koruma diyotu **ters bağlıydı** | netlist (S5) — **ERC göremedi** |
| 4 | Şemada hiçbir tel çizilmiyordu | PDF/SVG çıktısına bakınca |
| 5 | `Okuma` struct'ı prototipten önce tanımlanmıyordu | arduino-cli (S6) |
| 6 | `String` yığın parçalanması riski | arduino-cli (S6) |

**S9 turunda yakalanan dört hata:**

| Kusur | Nerede | Nasıl yakalandı |
|---|---|---|
| `enerji_wh()` 1 Wh'i 3.6e18 pJ sanıyordu (o 1 **kWh**) → Wh alanı 1000× küçük | firmware | S9: `wh × 3600 == joule` |
| Osiloskop tetiklemesi **ölü koddu** — tek çağrı `(0,0)` olduğu için derleyici attı | firmware | `"! tetiklenemedi"` ikilide yok |
| ADC'ye Timer0'ın ön bölücü tablosu verilmişti → 64× hızlı, sahte kanal sızması | emülatör | gerilim hatası 258 mV |
| Serbest çalışmada dönüşüm ideal an yerine *fark edilen* anda başlıyordu | emülatör | artık RMS 78 mV (olması gereken 30.6) |

**Aşama 2'de bulunanlar:**

| Kusur | Çözüm |
|---|---|
| Tam ölçek 45 V değil **32.2 V** — ADS girişi VDD ile sınırlı | kabul edildi |
| TL431 kelepçesi 11:1 bölücüde 29.7 V'ta sızıp menzili kesiyor | bölücü 100K/6.8K + PGA ±2.048 → kelepçe hep ters kutuplu |
| 15 mΩ'da lehim direnci %6.7 (statik) + %0.26 (yüke bağlı) | Kelvin (4 telli) algılama |
| `enerji_wh()` 3.6e18 hatası | 3.6e15; A4 **yanlış sabiti reddediyor** |
| **Osiloskop hiç uygulanmamıştı** — `app.js` paneli var, firmware `S` satırı üretmiyordu | IDF sürekli ADC sürücüsü, 83 333 Sa/s; A5 doğruluyor |
| **Kalibrasyon yolu yoktu** — şönt/kazanç/ofset derleme zamanı sabitti | seri komutlar + NVS |
| Şemadaki R8/R9 "DNP" notu yanlış modül sayısı varsayıyordu | bkz. 4.7 — hâlâ açık |

**Ayrıca:** `analogContinuousRead()` (Arduino sarmalayıcısı) örneklerin **ortalamasını**
döndürüyor, dalga şekli vermiyor — osiloskop için kullanılamaz. Bu yüzden doğrudan
ESP-IDF'in `esp_adc/adc_continuous.h` sürücüsü kullanıldı. Yeni oturum bu tuzağa
düşmesin.

---

## 3. Donanım gerçeği

### 3.1 Elde olanlar

Kaynak: `stok-takip/envanter.csv` (183 kayıt). **`CLAUDE.md` kuralı geçerli:** kısmen
girilmiş kategorilerde (bobin/trafo/çekirdek, sensör/modül/kart/kablo/mekanik/sarf/alet)
"kayıtta yok" ≠ "elinde yok".

| Kategori | Öne çıkanlar |
|---|---|
| Opamp | **LM358 ×8** (tek opamp tipi!) |
| Referans | TL431 ×10 |
| MOSFET | IRFZ44N ×13, IRF3205 ×6, IRFP250N ×3, IRF4905 ×2 (P), IRF830 ×1, IRFZ44N sökme ×3 |
| MOSFET sürücü | IR2110 ×2, IR2104 ×3 |
| Optokuplör | PC817 ×17, 4N35 ×5, PC123 ×1 |
| Regülatör | 7812 ×3, 7912 ×2, 7805 ×3, 7809 ×1, LM317T ×1 |
| PWM denetleyici | TL494 ×7, SG3525 ×5, UC3843 ×1 |
| Transistör | 2N2222 ×12, BC547 ×7, BC557 ×7, TIP41C ×2, 13007 ×4, BU508A, BF869S |
| Diyot | UF4007 ×18, SR5100 ×10, 1N4148 ×8, MBR20100 ×2, MBR2200 ×3, 1N4006 ×5, zenerler |
| Direnç | 10R:30 · 22R:20 · 39R:20 · 47R:20 · 100R:30 · 150R:15 · 220R:10 · 270R:7 · 330R:15 · 390R:10 · 470R:21 · 560R:10 · 1K:36 · 2.7K:10 · 4.7K:15 · 5.6K:10 · 6.8K:18 · 10K:28 · 20K:10 · 22K:15 · 27K:10 · 33K:10 · 47K:40 · 100K:33 · 220K:10 · 820K:30 · 1M:30 · 10M:10 · 12M:25 |
| Kondansatör | 100nF ~51 (çeşitli gerilim), 1nF ~16, elektrolitik ve film çeşitleri |
| Kart | Arduino Uno ×2, Nano ×2 |
| Zamanlayıcı | NE555P ×1 |

⚠️ **Direnç adetleri göz kararı sayım** ve ayrıca kayıt dışı dağınık bir yığın var. Sayı
kritikse kullanıcıya saydır.

**Elektrolitikler — darbe tamponu için kritik.** ≥25 V dayanımlı: 470µF/35V ×6,
470µF/63V ×6, 1000µF/35V ×5, 1000µF/25V ×1 → **~11 600 µF**. Bu, eğri çizici ve doyum
testinin darbe akımını karşılıyor (bkz. 5.4).

**Çekirdekler:** E tipi trafo çekirdeği 80mm ×2, sarı toroid ×4. *Doyum testinin ilk
test nesneleri bunlar olabilir.*

✅ **Soğutucu VAR** — `MEK002`, kullanıcı 2026-09-08'de bildirdi. ⚠️ Ölçüsü ve termal
direnci **bilinmiyor**, öğrenilip CSV güncellenmeli.

❌ **Kayıtta olmayan ve gerçekten olmayan** (Entegre kutusu tam tarandı): analog mux
(CD4051/4066), röle, CMOS girişli opamp, **komparatör**.
❓ **Kayıtta yok ama olabilir** (rastgele girilen kategoriler): buzzer/piezo, 12 V
adaptör, küçük şebeke trafosu.

### 3.2 Yolda olanlar — bu oturumda ilk kez tam görüldü

Kullanıcı iki siparişin tam listesini paylaştı. **Bu, oturum içinde verdiğim iki cevabı
düzeltiyor.**

#### direnc.net · TS07091124463 · 2.670,28 TL · "Ürün Hazırlanıyor" · DHL

**Ölçüm kartı için kritik olanlar:**

| Parça | Adet | Not |
|---|---|---|
| **ESP32 S3 N16R8 WiFi Bluetooth Board** | 1 | Aşama 2'nin işlemcisi |
| **TL072CP DIP-8 OpAmp** | 4 | ⚠️ "stokta yok" demiştim — **yolda**. JFET giriş, GBW 3 MHz, slew 13 V/µs |
| **NE555CN DIP-8** | 10 | ⚠️ aynı düzeltme |
| **L7912CV −12 V 1.5 A TO220** | 3 | 7912 ×2 stokla birlikte **±12 V rayı rahat** |
| 15mR Type-C şönt | 3 | 10 A kademesi |
| 5mR Type-C şönt | 2 | |
| 5mR Type-C şönt 9.5A | 4 | |
| 0.1R 5W taş | 3 | A kademesi |
| 0.10R 11W taş | 2 | |
| 1R 5W taş / 1R 11W taş / 3.3R 11W taş | 2 / 2 / 3 | elektronik yük için de kullanılır |
| 1R 1/4W · 1R 1/2W · 1R 1W · 1R 2W | 50 · 50 · 10 · 10 | mA kademesi |
| 0.1R 1/4W | 50 | |
| **Muz jak** (yeşil/siyah/sarı/kırmızı/mavi) | 2'şer | **ön panelin 5 uç çifti tam karşılanıyor** |
| **4mm born jak şeffaf** (5 renk) | 2'şer | |
| 2'li bariyer klemens | 3 | 10 A klemensi |
| Delikli plaket 6x13 / 10x10 / 5x5 | 3 / 2 / 2 | **kalıcı yapım** |
| Header (2mm dişi, 23mm erkek, 19mm erkek, 1.27mm dişi) | 2/3/3/2 | |
| M3 vida/somun/pul/rondela | çeşitli | |
| Anahtar/buton/dip switch/toggle | çok sayıda | ön panel kademe seçimi |

#### Robotistan · TS07091325822 · 1.545,81 TL · "Kargoya Verildi" · Yurtiçi 170997471077

| Parça | Adet | Not |
|---|---|---|
| **ADS1115 16-Bit 4 Kanal ADC** | **3** | ⚠️ Tasarım **ikisini** kullanıyor; 3.'sü verim ölçer için |
| Mano organizer kutu 10" | 3 | |
| Klemens girişli DC barrel jack | 2 | |
| DC güç jakı 2.1mm erkek vidalı klemens | 2 | |
| 1x40 header (12mm/15mm erkek, dişi) | 1/2/2 | |
| PBS-110 / PBS-11A / PBS-11B butonlar | 4'er, çeşitli renk | |
| Mini USB kablo 30cm | 1 | |
| M3 vidalar | çeşitli | |

> **Görev:** Parçalar gelince `stok-takip/envanter.csv`'ye işle. CSV şu an bu 40+ kalemi
> bilmiyor; işlenmezse yeni oturum "elinde yok" diye yanlış cevap verir. `CLAUDE.md`
> kuralları: yazmadan önce `.yedek/`'e kopya, id'ler kategori önekine göre.

### 3.3 ESP32-S3'ün doğrulanmış yetenekleri

Bunlar bu oturumda **yerel ESP-IDF başlıklarından okundu**, tahmin değil. Kaynak:
`~/AppData/Local/Arduino15/packages/esp32/tools/esp32s3-libs/3.3.11/include/soc/esp32s3/include/soc/soc_caps.h`
ve `clk_tree_defs.h`. Arduino ESP32 core **3.3.11**.

| Yetenek | Değer | Kaynak |
|---|---|---|
| ADC bit | **12 sabit** | `SOC_ADC_DIGI_MIN/MAX_BITWIDTH = 12` |
| ADC sürekli/DMA hız | **611 Hz – 83 333 Sa/s** | `SOC_ADC_SAMPLE_FREQ_THRES_LOW/HIGH` |
| ADC kanal | 10 (ADC1 = GPIO1–10) | `SOC_ADC_MAX_CHANNEL_NUM = 10` |
| ADC pattern tablosu | 12 öğe, 4 bayt/dönüşüm | `SOC_ADC_PATT_LEN_MAX = 24` (iki tablo) |
| **DAC** | ❌ **YOK** | `SOC_DAC_SUPPORTED` **tanımlı değil** (klasik ESP32'de var: 2 kanal × 8 bit) |
| LEDC (PWM) | 4 zamanlayıcı, 8 kanal, **14 bit** azami | `SOC_LEDC_TIMER_BIT_WIDTH = 14` |
| **MCPWM capture** | 1 zamanlayıcı, **3 kanal**, saat **APB 80 MHz → 12.5 ns** | `SOC_MCPWM_CAPTURE_*`, `SOC_MCPWM_CAPTURE_CLKS = {SOC_MOD_CLK_APB}` |
| PCNT | var | `SOC_PCNT_SUPPORTED = 1` |
| GPTimer | 2 grup × 2, **54 bit** sayaç | `SOC_TIMER_GROUP_*` |
| Bellek | 512 KB SRAM + **8 MB oktal PSRAM**, 16 MB flash | N16R8 |

**DAC'ın olmaması, eğri çizici ve elektronik yükün süpürme kaynağını belirliyor:**
LEDC PWM + RC süzgeç zorunlu (ya da harici I2C DAC satın alınmalı).
14 bit @ APB 80 MHz → taşıyıcı 80e6/16384 = **4.88 kHz**; 12 bit → 19.5 kHz; 10 bit → 78 kHz.
Çözünürlük ile süzgeç kolaylığı arasında doğrudan takas var.

**Pin durumu:**

| Pin | Kullanım |
|---|---|
| GPIO8 / GPIO9 | I2C SDA / SCL |
| GPIO4 | ADC1_CH3 — osiloskop girişi |
| GPIO7 | ADS #1 ALERT/RDY |
| GPIO5 | ADC1_CH4 — **boşta**, yedek olarak ayrıldı |
| GPIO1, 2, 6, 10 | **boşta**, ADC1'e uygun |
| ❌ GPIO0/3/45/46 | strapping |
| ❌ GPIO19/20 | yerel USB |
| ❌ GPIO26–32 | SPI flash |
| ❌ GPIO33–37 | oktal PSRAM (R8 varyantı) |

---

## 4. Bilinen kusurlar — YENİ OTURUM BUNLARI DÜZELTSİN

Bunlar bu oturumun envanter taramasında çıktı ve **henüz düzeltilmedi**. Sırayla doğrula
ve düzelt.

> **7 gerçek kusur + 1 yanlış alarm.** 4.5'i bilerek bıraktım: onu da kusur sanmıştım,
> doğrulayınca öyle olmadığı çıktı. Aynısı diğer maddeler için de geçerli olabilir —
> **her birini kaynağa giderek doğrula.**
>
> ### 📌 2026-09-08 durumu — liste kaynağa gidilerek denetlendi
>
> Uyarı haklı çıktı: **iddia edilen 7 kusurun 2'si zaten kapanmıştı** (4.3, 4.4),
> **1'inin önerilen çözümü de yanlıştı** (4.7 — 4.7 kΩ, kendi verdiği 300 ns
> sınırını 308 ns ile aşıyor). Ayrıca **yeni bir kusur bulundu** (4.13).
>
> | Durum | Maddeler |
> |---|---|
> | ✅ Bu oturumda çözüldü | 4.2 · 4.6 · 4.7 · 4.9 |
> | ⚪ Zaten kapanmıştı | 4.3 · 4.4 (+ 4.5 yanlış alarm) |
> | ✅ Daha önce çözülmüş | 4.1 · 4.10 |
> | ⏸️ Ön uç işine bağlandı | **4.8 · 4.13** — bkz. 5.12.4 bağımlılık zinciri |
> | 🟡 Açık, bağımsız | 4.11 (ikili aktarım) — **4.12 B22'de kapandı** |
>
> Zincir: **6/6 adım, 182 doğrulama, 0 hata** (A1 24 → 33 kural).

### 4.1 ✅ `app.js` komut uyuşmazlığı — ÇÖZÜLDÜ (2026-09-08)

`arayuz/app.js` (satır 272-291):

| Arayüzün gönderdiği | Aşama 2 firmware'inin beklediği |
|---|---|
| `sontGonder()` → `'r' + değer` | `s<ohm>` |
| `kalibreV()` → `'kv' + v` | `v<gerçek>` |
| `kalibreA()` → `'ka' + a` | `i<gerçek>` |
| `osiloYakala()` → `'t'` | ✅ `t<esik>` — bu çalışıyor |

**Düzeltildi:** `app.js` artık `s<ohm>`, `v<gerçek>`, `i<gerçek>` gönderiyor.
A5 testi bunu her koşuda sınıyor (`gonderilen[0] === 's10'` vb.), yani bir daha
sessizce ayrışamazlar.

### 4.2 ✅ A5/A6 kanıt dosyasına işlenmemiş — ÇÖZÜLDÜ (2026-09-08)

`kanit/a2-tam-dogrulama.txt` yalnız A1–A4 içeriyor (24+11+33+18 = **86 kontrol**).
A5, kanıt kaydı üretildikten *sonra* eklendi. `kanit2-uret.py` sayıları yalnız bu
dosyadan çektiği için `kanit/kanit2-sayfasi.html` hâlâ 4 adımlık koşuyu gösteriyor.

**Düzeltildi.** Asıl kök `kanit2-uret.py:72`'deki `if len(ADIMLAR) != 4` idi —
A5/A6 zincire eklenince üreteç *hata verip duruyordu*, bu yüzden sayfa 4 adımlık
eski koşuda donmuştu. Artık adım sayısı kayıttan geliyor (`< 4` alt sınırı),
A5/A6 basamakları MERDIVEN'e eklendi, A1'in kural sayısı da elle yazılmak yerine
kayıttan okunuyor. Kanıt sayfası şimdi **6 adım / 182 doğrulama** gösteriyor.

### 4.3 ⚪ README kendisiyle çelişiyor — ZATEN KAPANMIŞ (2026-09-08 doğrulandı)

~~Satır 12 `4/4 adım`, satır 31 `5/5 adım, 116/116` diyordu.~~

**Kaynağa gidildi: kusur yok.** README satır 12 `6/6 adım`, satır 32 `6/6 adım,
173/173` diyordu — tutarlıydı. Bu madde yazıldıktan sonra düzeltilmiş olmalı.
(Bugün 182'ye güncellendi, A1'e 9 yeni kural eklendiği için.)

### 4.4 ✅ Arayüz Aşama 1 değerlerini yazıyor — ZATEN KAPANMIŞ (2026-09-08 doğrulandı)

- ✅ `arayuz/index.html` osiloskop başlığı düzeltildi: artık
  *"12 bit, 611 Sa/s … 83.3 kSa/s, ayarlanabilir zaman tabanı"*.
- ~~`app.js` `demoVeri()`: `hz = 76923`, `voltAdim = 0.10648`~~ — **artık yok.**
  `demoVeri()` yeniden yazılmış, sahte veri `arayuz/sahte-kart.js`'ten geliyor ve
  orada `HZ_AZAMI = 83333`, `BOLME_ORANI = 15.70588235`, `VOLT_ADIM` hesaplanıyor.
  Aşama 1 sabiti kalmamış.

### 4.5 ⚪ `sema_uret_ortak.py` proje adı — YANLIŞ ALARM (kayıt için bırakıldı)

Bu maddeyi önce kusur sandım, sonra doğrulayınca **kusur olmadığı çıktı**. Silmek yerine
bırakıyorum, çünkü bu belgenin nasıl kullanılması gerektiğini gösteriyor: *iddiayı gör,
kaynağa git, doğrula.*

**Şüphe:** `sema_uret_ortak.py:16-17`'de `PROJE` ve `PROJE2` ikisi de `"olcum-karti-a2"`.
Aşama 1 şema üreteci yanlış proje adına yazıyor gibi görünüyor.

**Gerçek:** Kusur yok.
- `sema-uret.py:22` `PROJE`'yi `"olcum-karti"` olarak **ezip geçiyor** — ortak modüldeki
  değer sadece varsayılan. Modülün docstring'i bunu zaten söylüyor: *"hangi sema
  uretiliyorsa uretec bu degeri ayarlar."*
- `sema2-uret.py` `PROJE2`'yi içe aktarıp kullanıyor (satır 22, 365, 371, 375).
- Üretilen dosyalar doğrulandı: `sema/olcum-karti.kicad_sch` → `project "olcum-karti"`,
  `sema2/olcum-karti-a2.kicad_sch` → `project "olcum-karti-a2"`. ✅

Tek küçük kokusu: ortak moduldeki `PROJE` varsayılanı hiçbir zaman o değerle
kullanılmıyor (Aşama 1 eziyor, Aşama 2 `PROJE2` kullanıyor). Zararsız, istenirse
sadeleştirilir.

### 4.6 ✅ README:397 eski kod örneği — ÇÖZÜLDÜ (2026-09-08)

~~Hâlâ `float wh = enerji_pJ / 3.6e18;` gösteriyor.~~ Düzeltildi: örnek artık
`3.6e15` gösteriyor ve altına neden yanlış olduğunu (`3.6e18` = 1 kWh) ve hangi
adımların bunu sınadığını (S9 · A4: `wh × 3600 == joule`) anlatan bir not eklendi.

### 4.7 ✅ R8/R9 I2C pull-up — ÇÖZÜLDÜ (2026-09-08), **ama önerilen değer YANLIŞTI**

Şemadaki not **üç** ADS1115 modülü varsayıyor ve "takma" diyor. Ben `kurulum2.html`'de
"iki modül var, tak" diye **koşulsuz** düzelttim. **Kullanıcının üç modülü var** —
dolayısıyla iki ifade de eksik. Doğrusu **veri yolundaki modül sayısına bağlı**:

Her ADS1115 modülünde kart üstü 10 kΩ pull-up var. Fast-mode (400 kHz) sınırı
t_r ≤ 300 ns, ve t_r ≈ 0.8473 · R · C_veriyolu.

| Veri yolundaki modül | Pull-up (hat başına) | t_r @ 150 pF | Karar |
|---|---|---|---|
| 2 modül | 10K‖10K = **5 kΩ** | 636 ns ❌ | **R8/R9 tak** → 2.42 kΩ, 308 ns ✅ |
| 3 modül | 10K‖10K‖10K = **3.33 kΩ** | 423 ns ⚠️ sınırda | R8/R9 takarsan 1.95 kΩ, 248 ns ✅ ama 3 mA sink sınırına yaklaşır |

**Yedek çıkış yolu:** I2C hızını 100 kHz'e düşür (`Wire.begin(8, 9, 100000)`), t_r sınırı
1000 ns olur, her durum geçer. Örnekleme hızını etkilemez çünkü darboğaz ADS'in 860 SPS'i.

**Görev yapıldı — ve yaparken yukarıdaki tablonun kendisi de yanlış çıktı.**

🔴 **Yeni bulgu 1:** Yukarıda "2 modül + R8/R9 → 2.42 kΩ, 308 ns ✅" yazıyor.
**308 ns, aynı satırda verilen 300 ns sınırının ÜSTÜNDE.** İki modüllü
yapılandırmada 4.7 kΩ Fast-mode'da *kalıyor*. Üç modülde tesadüfen geçiyor
(248 ns), çünkü modül arttıkça paralel direnç düşüyor.

300 ns için izin verilen azami toplam pull-up: **2360 Ω**.

| Modül | R8/R9 | Toplam | t_r | Sink | Sonuç |
|---|---|---|---|---|---|
| 2 | yok | 5000 Ω | 635 ns | 0.66 mA | ❌ |
| 2 | 4.7K | 2423 Ω | **308 ns** | 1.36 mA | ❌ **kalır** |
| 2 | **2.7K** | 1753 Ω | **223 ns** | 1.88 mA | ✅ |
| 3 | yok | 3333 Ω | 424 ns | 0.99 mA | ❌ |
| 3 | 4.7K | 1950 Ω | 248 ns | 1.69 mA | ✅ |
| 3 | **2.7K** | 1492 Ω | **190 ns** | 2.21 mA | ✅ |

**Karar: R8/R9 = 2.7 kΩ** (stokta 10 adet). Hem 2 hem 3 modülde geçiyor, sink
akımı en kötü 2.21 mA ile 3 mA sınırının altında. 3. ADS1115 takıldığında
hiçbir şey değişmiyor.

🔴 **Yeni bulgu 2 — "100 kHz'e düş" yedek yolu bedava değil.** Yukarıda
*"Örnekleme hızını etkilemez çünkü darboğaz ADS'in 860 SPS'i"* yazıyor. Veri
yolu doluluğuna bakılınca öyle değil. `ads_oku()` işlem başına ~49 bit sürüyor
(işaretçi yazma + 2 bayt okuma, iki ayrı işlem), iki ADS 860 SPS'te 1720 okuma/s:

| I2C hızı | Okuma başına | Veri yolu doluluğu |
|---|---|---|
| 400 kHz | 122.5 µs | **%21** ✅ |
| 100 kHz | 490.0 µs | **%84** ⚠️ |

`Wire` blokladığı için bu doğrudan CPU'yu da bloklar. **100 kHz son çare.**

💡 **Uygulanmamış iyileştirme:** ADS1115 yazmaç işaretçisini korur. İlk okumadan
sonra işaretçi yazmayı atlayıp doğrudan 2 bayt istenirse işlem 49 → ~29 bite
iner (−%41), 100 kHz doluluğu %84 → %50'ye düşer.

Hepsi `tasarim2.py` §8b'de **kural olarak** duruyor (6 kural), `kurulum2.html`
tablosu da değiştirildi. Bir daha sessizce kayamaz.

### 4.8 🔴 Örtüşme süzgeci Nyquist'in ÜSTÜNDE — sahte sinyal üretir

> ⏸️ **BİLEREK BEKLETİLDİ (2026-09-08).** Kullanıcı 600 V menzil ve çift yönlü
> (±) giriş istedi. İkisi de **bölücüyü değiştiriyor**, süzgeç de bölücünün
> Thevenin direncine göre tasarlanıyor. Şimdi 100K/6.8K'ya göre Sallen-Key
> hesaplamak, ön uç değişince çöpe gidecek iş demek.
>
> İyi haber: önerilen yeni bölücülerin Thevenin'i bugünküne çok yakın
> (6.58 kΩ ve 6.79 kΩ, bugün 6.37 kΩ) — yani süzgeç tasarımı **iki menzilde de
> aynı** olabilir. Bu, 4.8'i ön uç işiyle birlikte **bir kerede** çözmeyi daha
> da mantıklı yapıyor. Bkz. 4.13 ve 5.12.

**Bu oturumda yeni bulundu.** Aşama 2 tek kanallı skop için tasarlanmıştı ve orada sorun
yoktu; **iki kanallı hızlı ölçüme geçince kusur haline geliyor.**

Gerilim bölücüsünün Thevenin'i 6.37 kΩ, süzgeç kondansatörü 1 nF →
fc = 1/(2π·6370·1e-9) = **24.997 kHz**.

İki kanal sürekli kipte çalışınca kanal başına hız 41 666.7 Sa/s, **Nyquist 20.83 kHz**.
Yani süzgeç Nyquist'in üstünde: 20.83 kHz'te sadece −2.3 dB. **Hiçbir şey süzmüyor.**

**Somut zarar:** 100 kHz'lik bir SMPS dalgalanması hiç zayıflamadan **16.67 kHz'e
katlanır** ve ekranda gerçekmiş gibi görünen sahte bir dalgalanma olarak çıkar. Güç
elektroniğiyle uğraşan biri için en tehlikeli hata tipi: **yanlış ama inandırıcı.**

**Çözüm:** 2 kutuplu Sallen-Key Butterworth, R = 6.8 kΩ (stokta 18), C2 = 1 nF,
C1 = 2 nF (iki 1 nF paralel) → f0 = 16 550 Hz, Q = 0.707. Zayıflama: Nyquist'te
−5.45 dB, fs'te −16.15 dB, **100 kHz'te −31.25 dB** (güç çarpımında −62.5 dB = 1360×).

⚠ Akımdaki 7.96 kHz'lik RC **yerinde kalmalı** — o ADS1115'in girişini koruyor. Hızlı
akım yolu onun arkasından çekilirse 7.96 kHz'e hapsolur. **Şönte iki bağımsız Kelvin
çifti bağla:** biri ADS'in RC'sine, biri doğrudan fark yükseltecine.

> 🔴 **YUKARIDAKİ SON PARAGRAF YANLIŞTI — B16 düzeltti (2026-09-09, 5.12.26).**
> İki hatası vardı:
>
> 1. **"Akımdaki 7.96 kHz'lik RC yerinde kalmalı"** — hayır. O RC, ADS akım
>    kanalının Nyquist'inin (430 Hz) **18.7 katı** üstündeydi; yani akım
>    kanalında **hiç örtüşme süzgeci yoktu** ve 430 Hz–8 kHz arası banda
>    katlanıyordu. "ADS'in girişini koruyor" gerekçesi de ayrı: koruma işini
>    B15/F2'de eklenen R38/R39 (1K) yapıyor, C4 değil.
> 2. **"İki bağımsız Kelvin çifti bağla"** — hiç uygulanmadı; R27/R29
>    netlist'te R18/R19'un **ardından** taplıyordu. B16 sorunu başka türlü
>    çözdü: süzgeci ADS'in **kendi koluna** taşıyarak (C4 100nF→1nF, yeni
>    C18/C19/C20 = 1.32 µF, R38/R39'un ardında). Böylece tek Kelvin çifti
>    yeterli oluyor, hızlı yol serbest kalıyor (7.76 → 16.52 kHz) **ve** ADS
>    kanalı gerilim kanalıyla eşleşiyor.

### 4.9 ✅ Derleme FQBN'inde PSRAM açık değil — ÇÖZÜLDÜ (2026-09-08)

`kod/olcum-karti-a2/build/.../build.options.json` incelendi: FQBN düz
`esp32:esp32:esp32s3`. **`PSRAM=opi` yok.** Bugün sorun değil (8 MB PSRAM kullanılmıyor),
ama derin skop belleği için PSRAM ayrılmaya çalışıldığında
`heap_caps_malloc(..., MALLOC_CAP_SPIRAM)` **sessizce NULL döner** ve skop hiç açılmaz.

**ÇÖZÜLDÜ (2026-09-08).** `board details` ile doğrulandı: kartın PSRAM
varsayılanı gerçekten `disabled`.

FQBN artık **tek kaynakta**: `uretim/hedef2.py`. Daha önce `sim2_kart.py` ve
`test_skop.py` içinde *ayrı ayrı* yazılıydı — birini düzeltip ötekini unutmak
mümkündü. İkisi de şimdi `hedef2.FQBN` kullanıyor.

```
esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=huge_app
```

Derlendi: **479 303 B (%15 / 3 MB), 47 452 B RAM, 0 uyarı.**

⚠️ **`CDCOnBoot=cdc,USBMode=hwcdc` BİLEREK EKLENMEDİ.** Bunlar `Serial`i UART
köprüsünden yerel USB CDC'ye taşır; 4.11 için gerekli ama tezgahtaki ilk açılışı
bozabilir. O iş 4.11 ile birlikte, bilerek yapılmalı.

**`ps_malloc(2MB) != NULL` adımı eklenmedi — çünkü kart olmadan koşamaz.** Yerine
firmware açılışta **kendi durumunu yazıyor**:

```
PSRAM: 8192 KB
PSRAM: YOK — derin skop bellegi kullanilamaz (hedef2.py: PSRAM=opi mi?)
```

Sebebi: derlemenin PSRAM'li olması kartta PSRAM *bulunduğunu* kanıtlamaz. Bazı
"N16R8" etiketli kartlarda quad PSRAM çıkıyor; o durumda `hedef2.py`'de
`PSRAM=opi` yerine `PSRAM=enabled` denenecek. `tasarim2.py` §9 üç kuralla
FQBN'in içeriğini sınıyor, kanıt ise tezgahtaki açılış satırı.

### 4.10 ✅ Osiloskop tetiklemesi — ÇÖZÜLDÜ (2026-09-08)

Histerezis, ön-tetik, kenar seçimi ve tetik kipleri eklendi. Ayrıntı 5.2'de.

### 4.11 🟡 Aktarım darboğazı — derin bellek 115200 baud'da anlamsız

Bugünkü ASCII protokolü ile:

| Kayıt | Biçim | Süre @115200 |
|---|---|---|
| 1 000 örnek (bugün) | ASCII | 0.43 s ✅ |
| 20 000 örnek | ASCII | **8.7 s** ❌ |
| 500 000 örnek | ikili + **yerel USB CDC** | **~1.0 s** ✅ |

8 MB PSRAM'in derin belleği ancak **yerel USB CDC (GPIO19/20) + ikili biçim** ile
anlamlı. UART köprüsünde 115200'de kalırsan PSRAM'in hiçbir işe yaramaz.

### 4.12 ✅ WiFi yolunda arayüz yok — **B22'de KAPANDI** (2026-09-10)

> Aşağıdaki tespit Aşama 2 dönemine ait ve **artık geçerli değil.** B22.2
> taşıyıcı katmanını kurdu (`TasiyiciAkis` = SSE), B22.5 arayüzü kartın
> LittleFS'inden servis etti. Ayrıca metindeki `arayuz/app.js` yolu da
> yanlış — o klasör yok, dosya `arayuz3/app.js`. Ayrıntı **5.12.35** ve
> **5.12.38**'de.

Özgün tespit: *"Firmware `/akis` adresinden SSE yayınlıyor ama arayüz
yalnız Web Serial istemcisi; WiFi ile bağlanınca gösterilecek arayüz yok."*

### 4.13 🔴 Alt koruma kelepçeleri 1N4148 — korudukları çipin sınırını AŞIYOR

**Bu oturumda yeni bulundu (2026-09-08).** Netlist okunarak, simülasyondan değil.

`netlist2_dogrula.py` şunu doğruluyor ve şema gerçekten böyle:

```
D2: KATOT /V_DUGUM,  ANOT GND     -> ADS1115 AIN0'i koruyor
D4: KATOT /SKOP,     ANOT GND     -> ESP32-S3 GPIO4'u koruyor
```

Giriş negatife giderse bu diyotlar düğümü **−0.7 V**'a kelepçeler. Ama:

| Çip | Mutlak alt sınır | 1N4148 kelepçesinin verdiği |
|---|---|---|
| ADS1115 (AIN) | **GND − 0.3 V** | −0.7 V ❌ |
| ESP32-S3 (GPIO) | **GND − 0.3 V** | −0.7 V ❌ |

**Devir belgesi bu tuzağı 5.1.4'te yazıyor** — ama yalnızca *gelecekteki* TL072
çıkışları için: *"Alt kelepçe 1N4148 OLAMAZ: −0.7 V, ESP32'nin −0.3 V mutlak alt
sınırını aşar. Schottky şart."* **Aynı cümle şemada bugün duran D2/D4 için de
geçerli ve fark edilmemiş.**

⚠️ **Bunun ne kadar ciddi olduğu ÖLÇÜLMEDİ.** 100K seri direnç akımı sınırlıyor
(−400 V'ta bile 4 mA, 1N4148'in sınırının altında) ve çipin kendi ESD diyodu da
paralel iletiyor; muhtemelen anında yanmaz. Ama spec dışı ve **A2 taraması bunu
hiç görmedi**: `sim2_giris.py` taraması `dc Vin 0 300` — yani **sıfırdan yukarı**.
Negatif giriş bir kez bile simüle edilmemiş, üstelik tarama netlist'inde D2 hiç
yok. Yeşil A2 adımı negatif taraf hakkında **hiçbir şey söylemiyor.**

**Çözüm:** alt kelepçeler Schottky olacak (SR5100 stokta ×10; geniş bantlı skop
kanalı için kapasitesi düşük BAT54 alınmalı). Ve `sim2_giris.py`'ye **negatif
tarama** eklenecek.

⏸️ 4.8 gibi bu da **ön uç işiyle birlikte** yapılmalı — kullanıcı zaten ± giriş
istedi, o iş bu kelepçeleri baştan doğru kurmayı gerektiriyor.
### 4.14 🔴 PGA oto-kademesi tamponsuz bölücüde KAZANÇ SIÇRAMASI yapıyor

**2026-09-08'de bulundu.** Kaynak: ADS1115 veri sayfası (SBAS444B) s.3 ve
s.13 Tablo 2 — bu oturumda PDF'ten okundu.

ADS1115'in giriş empedansı **PGA kademesiyle değişiyor**:

| PGA | Z_diferansiyel | Z_ortak-mod |
|---|---|---|
| ±2.048 | 4.9 MΩ | 6 MΩ |
| ±1.024 | 2.4 MΩ | 3 MΩ |
| ±0.512 | **710 kΩ** | 100 MΩ |
| ±0.256 | **710 kΩ** | 100 MΩ |

Aşama 2'nin gerilim kanalı **tamponsuz** (Thevenin 6.37 kΩ) ve firmware
[`olcum2.h` `pga_sec()`] onu **±2.048 ↔ ±0.256 arası otomatik kademeliyor.**
Kaynak empedansı sıfır olmadığı için bu bir kazanç hatası yaratıyor:

| PGA | Kazanç hatası |
|---|---|
| ±2.048 | %0.236 |
| ±1.024 | %0.478 |
| ±0.512 | %0.904 |
| ±0.256 | %0.904 |

**Kademe sınırında okuma 0.67 puan zıplıyor.** Kalibrasyon tek kademede
yapıldığı için bunu silemez. Üstüne ADS'in kendi "PGA kademeleri arası kazanç
uyumu %0.1 maks" (s.3) da biniyor.

Araştırma teyidi (TI E2E, Adafruit forumları): *"input impedance varies with
gain settings"*, *"a voltage buffer can be added to solve this issue"*,
*"divider output impedance should be < 10 kΩ"*.

**Çözüm:** bölücüyü tamponla (5.12'de yapıldı) — kaynak empedansı ~0 olunca
hata PGA'dan bağımsız kayboluyor. Tamponlanmayacaksa PGA **sabitlenmeli**.

`tasarim3.py` §3 bunu kural olarak sınıyor.


### 4.15 ✅ Arayüzün ÜÇ düğmesi sessizce çalışmıyordu — ÇÖZÜLDÜ (2026-09-08)

**B7 sırasında bulundu.** 4.1 bu hatayı `app.js` içinde düzeltmişti ama
`index.html`'deki üçünü **atlamıştı** — çünkü testler yalnızca `app.js`'e
bakıyordu.

Aşama 2 firmware'inin tanıdığı komutlar: `# ? i s t v z`

| Düğme | Gönderdiği | Ne oluyordu |
|---|---|---|
| Ayarları göster | `d` | **Böyle bir komut yok** → "bilinmeyen komut" |
| Enerjiyi sıfırla | `e` | **Aşama 2'de enerji sıfırlama HİÇ YOK** |
| Akımı sıfırla | `s` | `s` = şönt komutu; boş değerle "sont degeri gecersiz" |

Üçüncüsü en sinsisi: `s` **geçerli bir komut harfi**, o yüzden harf
düzeyinde bir denetim onu yakalamaz — yanlış olan anlamı.

**Düzeltildi:** `d`→`?`, `s`→`z`, `e` düğmesi kaldırıldı (Aşama 2'de
karşılığı yok), yerine `#` (I²C tara) kondu.

**Tekrarlanamaz hale getirildi:** `uretim/test_arayuz3.js` arayüzün
gönderebileceği her komut harfini firmware'in `case` etiketleriyle
karşılaştırıyor — **hem `app.js` hem `index.html` taranarak**. Aynı
denetim Aşama 2 arayüzüne uygulandığında `d` ve `e`'yi yakalıyor.


---

## 5. Yeni hedef mimari

> **Süreklilik notu:** README satır 13'te zaten
> `| 3 | — | çift kanal (verim ölçümü) | 3. ADS1115 için yer ayrıldı |` yazıyor.
> Kullanıcının seçtiği **verim ölçer, planlanmış Aşama 3'ün ta kendisi**. Yeni yön
> projeyi ıskartaya çıkarmıyor, öngörülen yola giriyor.

### 5.0 Kullanıcının istedikleri, öncelik sırasıyla

**Ana üçlü (açıkça istendi):**
1. **Osiloskop** — hem tek seferlik hem eşdeğer-zaman *(kullanıcı "ikisi de olsun" dedi)*
2. **Wattmetre**
3. **Eğri çizici** (I-V curve tracer)

**Artı: gerilim ve akım kalacak, olabildiğince yüksek örneklemeyle.**

**Kullanıcının seçtiği dört ek yetenek** (hepsini seçti):
4. **SMPS zamanlama analizörü** — 12.5 ns'de frekans/duty/ölü zaman
5. **Verim ölçer (η)** — giriş ve çıkış gücünü eşzamanlı ölçüp verim eğrisi
6. **Elektronik yük** — programlanabilir sabit akım
7. **Bobin/trafo doyum testi** — L ölçümü ve çekirdek doyum noktası

### 5.1 Dört fiziksel duvar — mimarinin tamamı bunların etrafında şekilleniyor

| # | Duvar | Sayı | Sonucu |
|---|---|---|---|
| **D1** | ESP32-S3 ADC hızı **toplam**, kanal başına değil | 83 333 Sa/s toplam | 2 kanal → **41 666.7 Sa/s/kanal**, gerçek zamanlı bant **20.83 kHz**. 100 kHz anahtarlamayı gerçek zamanda göremezsin. |
| **D2** | Tek SAR, sıralı pattern | kanallar arası **12.000 µs sabit kayma** | Eşzamanlı örnekleme **imkânsız**. Yalnız DSP'de düzeltilir. |
| **D3** | ADS1115'in kendi sinc süzgeci | 860 SPS'te −3 dB @ **380 Hz**, çentik 860 Hz | 3 ADS'i interleave etmek **bant genişliği yaratmaz** (bkz. 5.1.3) |
| **D4** | ESP32-S3 ADC analog giriş bandı / S/H açıklık süresi | **Espressif yayınlamıyor** | ETS'in gerçek tavanı burası. **Ölçmeden sayı vaat edilemez.** |

#### 5.1.1 Kanal kayması (D2) ve düzeltilmesi — kritik

`sample_freq_hz` **toplam** dönüşüm hızıdır. `pattern_num = 2` ile akış `V,I,V,I…`
şeklinde gider; V ile I arasında tam **1/83 333 = 12.000 µs** vardır. Kanal periyodu
24 µs olduğuna göre **kayma tam yarım örnek** — ve bu bir şans, çünkü doğrusal fazlı bir
FIR ile **tam olarak** düzeltilebilir.

**Düzeltmezsen ne olur** (θ = 2πfΔt, hata ≈ −θ²/2 − θ·tan φ):

| f | θ | PF=1.0 | PF=0.5 | PF=0.1 |
|---|---|---|---|---|
| 50 Hz | 0.22° | −0.001% | **−0.65%** | **−3.75%** |
| 1 kHz | 4.32° | −0.28% | **−13.3%** | −75% |
| 10 kHz | 43.2° | **−27.1%** | anlamsız | anlamsız |

⚠️ **Dirençsel yükte hata ikinci derece (küçük), reaktif yükte birinci derece (büyük).**
Düzeltmesiz wattmetre yalnız ~1 kHz'e kadar ve yalnız yüksek güç faktöründe doğrudur.

**Çözüm — 4 katsayılı Lagrange yarım-örnek hizalayıcı:**
```
i_hiza[n] = −1/16·i[n−2] + 9/16·i[n−1] + 9/16·i[n] − 1/16·i[n+1]
```
Örnekler 24n−36, −12, +12, +36 µs → tam simetrik → **faz hatası sıfır**. Geriye yalnız
genlik sarkması kalır (1 kHz'te −0.000 dB, 5 kHz'te −0.063 dB). CPU maliyeti
0.33 MMAC/s — 240 MHz FPU'da hiçbir şey.

⚠️ **Üç uygulama tuzağı:** (1) kanal sırasını indeks paritesinden **çıkarma**, her zaman
`o->type2.channel` alanından demux et — mevcut `skop_yakala()` bunu zaten doğru yapıyor,
o alışkanlığı koru. (2) `conv_frame_size`, `4 × pattern_num`'un katı olmalı. (3)
`sample_freq_hz` sınırları **toplama** uygulanır.

#### 5.1.2 Hibrit mimari — doğru formülasyonu

Fikir sağlam ama "kazanç+ofset düzelt" hali eksik. **Doğrusu: DC'yi ADS'ten, AC'yi
ESP'den al.**

```
v(t) = V̄_ADS  +  ( v̂_ESP(t) − ort(v̂_ESP) )
```

Bu neden daha güçlü: ESP'nin doğrusalsızlığı (INL) küçük bir AC salınım aralığında
neredeyse doğrusaldır, yani INL'in büyük kısmı **DC teriminin içine düşer ve ADS onu
siler**. Basit kazanç+ofset düzeltmesi INL'e karşı çalışmaz, bu çalışır.

Kazanç/ofset kestirimi için unutmalı özyinelemeli en küçük kareler (τ = 60 s, 4 Hz
kadans). Ofset hızlı kayar (tek noktadan gözlemlenebilir), kazanç yavaş kayar (uyarım
ister) — bu yüzden kazanç yalnız pencere varyansı bir eşiği geçince güncellenir.

**Nerede kırılır — dürüst liste:**

| Kırılma | Çözüm |
|---|---|
| **Farklı düğüm** — ADS ve ESP ayrı bölücülere bakarsa "aynı ortalama" varsayımı yalan | **Zorunlu: aynı düğüm.** Bugünkü ayrı skop bölücüsü ölçüm kanalı olamaz |
| **INL** — 2 parametreli uydurma kod-bağımlı hatayı silmez (kalan ±5–15 LSB) | DC'yi ADS'ten al; hızlı kanalın **mutlak** değerine asla güvenme |
| **Kazanç gözlemlenemez** — sinyal hep 12 V'ta durursa `a` gürültüden uydurulur | Varyans eşiği + kurulumda iki noktalı elle kalibrasyon. **Sürekli disiplinleme sıfırdan mutlak doğruluk YARATMAZ**, yalnız sürüklenmeyi takip eder |
| **Pencere içinde durağan değil** (yük basamağı) | Varyans eşiğini aşan pencereyi at |
| **PGA kademe değişimi** pencere ortasında | Disiplinleme penceresinde PGA'yı dondur |
| **Kırpma** | Tepe dedektörü; kırpma varsa disiplinlemeyi durdur ve arayüze bildir |

#### 5.1.3 3 ADS1115'i interleave etmek — HAYIR

Faz bilinebilir (her ALERT'i ayrı GPIO'ya alıp damgalarsan), ama **bant genişliği
kazanmazsın**. ADS1115'in her örneği 1.16 ms'lik bir **boxcar ortalamasıdır**:

| f | Tek ADS sinc cevabı |
|---|---|
| 200 Hz | −0.79 dB |
| **380 Hz** | **−2.99 dB** |
| 860 Hz | çentik (−∞) |

Her alt-ADC sinyali **almadan önce** 380 Hz'te 3 dB kesmiş oluyor. Üçünü birleştirmek
kaybedilmiş bilgiyi geri getirmez — interleave **örnek yoğunluğunu** artırır, bant
genişliğini değil. Üstelik çipler arası kazanç (±%0.15) ve ofset (±3 LSB) uyumsuzluğu
klasik **interleave sahte tonları** üretir. Maliyeti de yüksek: 2580 okuma/s × ~150 µs
I2C = saniyenin **%39'u** bloklayan I2C içinde.

**3. ADS'in doğru kullanımı hız değil, EŞZAMANLILIK:** çıkış şöntü + çıkış bölücü →
verim ölçümü. Ayrıca boş kanallar sağlık izlemeye ayrılabilir (TL431 rayı kaydı mı,
±12 V sağlam mı).

#### 5.1.4 Hızlı akım yolu — TL072 fark yükselteci

**Kazanç 27 (27K/1K)** seçildi. Neden:

| Rf/Rg | G | 1 A'de çıkış | Tam ölçek | Bant (3 MHz/(1+G)) | Yargı |
|---|---|---|---|---|---|
| 22K/1K | 22 | 2.20 V | 1.364 A | 130 kHz | |
| **27K/1K** | **27** | **2.70 V** | **1.111 A** | **107 kHz** | ✅ **seçilen** |
| 33K/1K | 33 | 3.30 V | 0.909 A | 88 kHz | ❌ 3.1 V penceresini aşar |

27K (stokta 10) ve 1K (stokta 36) var; **30K stokta yok**, o yüzden "temiz" 30 seçilmedi.
107 kHz bant, 20.83 kHz Nyquist'in çok üstünde → örtüşme süzgeci yükselteçten **sonra**
gelmeli, yükselteç darboğaz değil.

**Çift yönlü ölçüm:** fark yükseltecinin REF ucunu GND yerine **+1.5 V**'a bağla (TL431
rayından bölünmüş, ikinci TL072 kesitiyle **tamponlanmış** — REF düşük empedanslı
sürülmezse CMRR ölür). Çıkış 1.5 V ± 1.5 V → **±0.55 A çift yönlü**. Güç elektroniğinde
bobin akımı ters döner; tek yönlü ölçüm SMPS'te yanlış cevaptır.

🔴 **Her op-amp çıkışı ile her GPIO arasına koruma ZORUNLU.** TL072 ±12 V'ta besleniyor;
arıza anında çıkışı ±10 V'a gider ve 3.3 V'luk bir ADC pinini **anında öldürür**.
1 kΩ seri + üstte 1N4148→TL431 rayı (2.495 V) + altta **Schottky**→GND.

⚠️ **Alt kelepçe 1N4148 OLAMAZ:** −0.7 V, ESP32'nin −0.3 V mutlak alt sınırını aşar.
Schottky şart (SR5100 stokta; geniş bantlı skop kanalı için BAT54 al — SR5100'ün
kapasitesi büyük).

### 5.2 Osiloskop — ✅ TEMEL KISMI YAPILDI (2026-09-08)

> Bu bölüm başta tasarım önerisiydi. **Zaman tabanı, tetikleme ve otomatik
> ölçümler uygulandı ve doğrulandı.** Eşdeğer-zaman örnekleme (ETS) hâlâ
> tasarım aşamasında — o kısım aşağıda ayrı işaretli.

#### Neyin çözüldüğü

Eski hali sabit **1000 örnek @ 83 333 Sa/s = 12 ms pencere** idi. Bir 50 Hz
çevrimi 20 ms sürdüğü için **tam çevrim ekrana sığmıyordu.**

Artık gerçek osiloskoplardaki gibi **saniye/bölme** seçiliyor. 12 kademeli
1-2-5 merdiveni, hedef 100 örnek/bölme:

| s/bölme | Örnekleme | Örnek | Pencere | Not |
|---|---|---|---|---|
| 100 µs | 83 333 Sa/s | 100 | 1 ms | en hızlı — hız tavana dayanıyor |
| 1 ms | 83 333 | 833 | 10 ms | |
| 2 ms | 50 000 | 1000 | 20 ms | **50 Hz'in tam bir çevrimi** |
| 10 ms | 10 000 | 1000 | 100 ms | 50 Hz'in 5 çevrimi |
| 100 ms | 1 000 | 1000 | 1 s | |
| 500 ms | 611 | 3055 | 5 s | en yavaş — hız tabana dayanıyor |

Doğrulama zinciri (A5) **50 Hz için en az bir tam çevrimin sığdığı kademe
olduğunu** her koşuda sınıyor — bu kusur bir daha geri gelemez.

#### Eklenen osiloskop özellikleri

| Özellik | Nasıl |
|---|---|
| **Ayarlanabilir zaman tabanı** | 12 kademe, `tb<0-11>` · arayüzde ◀ ▶ düğmeleri |
| **Otomatik kurulum (AUTO)** | `ta` — kademeleri tarar, frekansı bulur, ekranda ~4 çevrim olacak tabanı ve tetiği kendisi ayarlar |
| **Tetik seviyesi** | `tl<0-4095>` · arayüzde kaydırma çubuğu |
| **Tetik kenarı** | `te0` yükselen / `te1` düşen |
| **Histerezis** | `th<kod>` — gürültülü eşikte sahte tetiklemeyi önler |
| **Ön-tetik** | `tp<0-90>` — tetik ANINDAN ÖNCESİNİ gösterir (halka tampon) |
| **Tetik kipleri** | `tm0` oto · `tm1` normal · `tm2` tek atış |
| **Otomatik ölçümler** | frekans, periyot, Vpp, Vmax, Vmin, Vort, Vrms, **Vac (RMS)**, duty, yükselme/düşme süresi, çevrim sayısı |

**Ön-tetik neden bedava geliyor:** ADC sürekli koşuyor ve örnekler halka
tampona yazılıyor. Tetik aranırken halka dolmaya devam ettiği için, tetik
bulunduğunda elimizde **zaten tetik öncesine ait örnekler var**. Gerçek
osiloskopların ön-tetik penceresi tam olarak böyle çalışır.

#### Ölçüm matematiği nerede ve nasıl doğrulandı

`skop_olc()` fonksiyonu **`olcum2.h` içinde ve platform bağımsız** — projenin
kuralı gereği. Bu sayede A6 adımında **gerçek kod**, avr-gcc ile derlenip
39/39 bit-birebir doğrulanmış AVR emülatöründe koşturuluyor.

Beklenen değerler bir yeniden-uygulamadan değil, **analitik olarak bilinen
dalgalardan** geliyor:

| Dalga | Beklenen | Ölçülen |
|---|---|---|
| Kare, 80 örnek periyot @ 10 kSa/s | 125.000 Hz | 125.000 Hz ✅ |
| Üçgen, 100 örnek | 100.000 Hz | 100.000 Hz ✅ |
| Sinüs, 64 örnek | 156.250 Hz | 156.250 Hz ✅ |
| Sinüs AC RMS | genlik/√2 | fark 0.0004 V ✅ |
| Üçgen AC RMS | genlik/√3 | fark 0.005 V ✅ |
| %25 duty kare | %25 | %24.90 ✅ |
| Düz çizgi | ölçüm yok | frekans 0, çevrim 0 ✅ |

**32/32 koşul geçti.** Frekans doğruluğu için kenar geçişleri **doğrusal ara
değerlemeyle** bulunuyor; bu, periyot ölçümünü örnek çözünürlüğüne hapsolmaktan
kurtarıyor (tipik 10–50 kat iyileşme).

#### Protokol

```
S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
M f=<Hz> T=<s> Vpp=<V> Vmax=<V> Vmin=<V> Vort=<V> Vrms=<V> Vac=<V>
  duty=<%> tr=<s> tf=<s> n=<çevrim>
<ham 12-bit ADC kodları, 16'şar satır>
E
```

Arayüz `t=0`'ı **tetik anına** koyuyor, öncesi negatif zaman olarak görünüyor.
Dikey ölçek min–max'a göre otomatik — sabit bir DC seviyesine binmiş küçük bir
dalgalanma böyle görünür hale geliyor.

#### ⚠️ Hâlâ geçerli sınırlar

- **Menzil 0 – 48.7 V, TEK YÖNLÜ.** Sinyal sıfırın altına inerse alt yarısı
  kırpılır. Sinyal üretecinde **DC offset** kullanılmalı.
- Tek kanal gerçek zamanlı **Nyquist 41.7 kHz**; giriş süzgeci 25 kHz'te
  kesiyor. Üstündeki bileşenler sahte, yavaş sinyal olarak görünür.
- **Şebekeye bağlanamaz** — kart izole değil (bkz. 6.1).
- Aktarım hâlâ ASCII ve 115200 baud: 3055 örneklik en yavaş kademe ~1.3 s
  sürüyor. Derin bellek için ikili + yerel USB gerekiyor (bkz. 4.11).

#### 🔵 HENÜZ YAPILMADI: eşdeğer-zaman örnekleme (ETS)

Kullanıcı "ikisi de olsun" dedi; tek seferlik kip yapıldı, **ETS yapılmadı.**
Tasarımı aşağıda duruyor, uygulanmayı bekliyor.


### 5.2b ETS tasarimi (uygulanmadi) — asagidaki bolum tasarim notudur

Kullanıcı **her iki kipi de** istedi:

| Kip | Nasıl | Ne için |
|---|---|---|
| **Tek seferlik** | Gerçek zamanlı 83 333 Sa/s (tek kanal), ön-tetik halka tamponu, PSRAM'de derin bellek | Kalkış anı, arıza, aşırı akım — **bir kez olan** olaylar |
| **Eşdeğer-zaman (ETS)** | Tetiklemeyi 12.5 ns adımlarla kaydırıp dalgayı çok çevrimde biriktirmek | SMPS anahtarlama dalgaları — **tekrarlayan** sinyaller |

#### Süzgeç çelişkisi ve çözümü

Gerçek zamanlı kip örtüşme süzgecine **muhtaç**, ETS ondan **kurtulmalı**. Anahtar veya
röle yerine **iki ADC pini** kullan — sıfır parça, sıfır kontak direnci:

- **GPIO4 (CH3)** = skop **ham** (süzgeçsiz, geniş bant, ETS için)
- **GPIO7 (CH6)** = skop **süzülmüş** (SK 16.55 kHz, tek-seferlik için)

Aynı TL072 tamponunu iki yola çatallayarak. Firmware kipe göre pattern'i değiştirir.

> **GPIO7'yi kurtarmak için ADS ALERT/RDY'yi GPIO21'e taşı.** ALERT sayısal bir sinyal,
> ADC pinine ihtiyacı yok.

#### 🌟 ETS'in kolay ve KESİN yolu: koherent örnekleme

"12.5 ns gecikme üret ve ADC'yi yeniden başlat" **çalışmaz** —
`adc_continuous_start()` gecikmesi onlarca µs ve titreşimli. Doğru numara gecikme
eklemek değil, **frekans seçmek**:

ETS kipinde örnekleme hızını **80 000 Sa/s** iste → APB bölücüsü tam **1000 tik**.
Uyarım periyodunu **P tik** seç ve **P'yi 1000 = 2³·5³ ile aralarında asal** yap:

| P (tik) | f | Eşdeğer adım | Faz sayısı | Bir tam kayıt |
|---|---|---|---|---|
| **799** | **100.125 kHz** | **12.5 ns** | 799 | **9.99 ms** |
| 1599 | 50.031 kHz | 12.5 ns | 1599 | 19.99 ms |
| 3199 | 25.008 kHz | 12.5 ns | 3199 | 39.99 ms |

**Eşdeğer örnekleme hızı 80 MSa/s. Tetikleme yok, capture yok, titreşim yok** (her şey
aynı XTAL'den). 1 s'de 100 geçiş → √100 = **10× gürültü bastırma**; ESP32 ADC'nin bol
gürültüsü doğal dither görevi görüp 12 bit ham izi **~15 bit efektif** yapar.
*Gürültülü ADC bir anda iyi bir ADC oluyor.*

⚠️ `sample_freq_hz`'in **gerçekleşen** değerini varsayma, **ölç**: GPTimer ile 10 s
boyunca dönüşüm say → ppm doğrulukla gerçek hızı bul. ETS'in tüm doğruluğu bu tek sayıya
dayanıyor.

#### Dış SMPS için: analog dalgayı değil, PWM'in KENDİSİNİ tetikle

**Kilit içgörü:** SMPS ölçerken her zaman elinde bir saat sinyali var — SG3525'in çıkışı,
TL494'ün OUT'u, IR2110'un girişi. Onu GPIO'ya alıp MCPWM capture ile damgala.

| Tetik kaynağı | Titreşim (σ) | Jitter tavanı | Yargı |
|---|---|---|---|
| Kart uyarımı (koherent) | ~ps | >100 MHz | ✅ en iyi |
| **Sayısal senk → GPIO → MCPWM capture** | **~3.6 ns** | **36.8 MHz** | ✅ **SMPS için doğru cevap** |
| Harici komparatör (TL072/LM358) | yüzlerce ns | ~1 MHz | ❌ yetersiz |
| **Yazılımla ADC örnekleri üzerinde (bugünkü kod)** | **12 µs** | **0.13 MHz** | ❌ **ETS için işe yaramaz** |

#### 🧱 ETS'in DÜRÜST bant genişliği tavanı

| Katman | Sınır |
|---|---|
| Bölücü, 1 nF kalırsa | **25 kHz** → ETS ölür |
| Bölücü **kompanze edilirse** (Cp·100K = Cs·6.8K) | düz, çok MHz |
| TL072 tampon, 3 V p-p'de slew tavanı | 1.38 MHz |
| 1 kΩ + kelepçe kapasitesi | 14.5 MHz |
| **ESP32-S3 ADC track/hold + giriş bandı** | 🧱 **Espressif YAYINLAMIYOR** — tahmin 0.3–1 MHz |
| Zamanlama titreşimi 12.5 ns | 10.6 MHz |

**Dürüst ifade — kullanıcıya böyle söyle:** *"Eşdeğer örnekleme hızı 80 MSa/s. Analog
bant genişliği ölçülene kadar 500 kHz'in altında varsayılmalıdır; 0.3–1 MHz
beklenmektedir. MHz vaat edilmemektedir."*

**🌟 Kartın kendini ölçmesi — bunu firmware'e koy.** MCPWM'in kendi kare dalgasının
kenarı <2 ns'dir. ETS ile o kenarı yeniden kur, %10–90 yükselme süresini ölç,
BG ≈ 0.35/t_r. Sonucu NVS'e yaz ve **her ETS başlığında yayınla**. Kart kendi bant
genişliğini ilan eder, tasarımcı değil — bu, projenin "hiçbir ölçüm değeri elle yazılmaz"
kültürünün doğal devamı.

#### ETS ne zaman ÇALIŞIR, ne zaman YALAN söyler

| Durum | ETS | Neden |
|---|---|---|
| Kart uyarımlı devre | ✅ kusursuz | koherent, titreşimsiz |
| Kararlı SG3525/TL494, sabit yük | ✅ iyi | periyot titreşimi 10–100 ns, analog duvarın üstünde |
| **UC3843 (akım kipi)** | ⚠️ kısmen | tepe-akım sonlandırması OFF süresini titretir. **Yükselen kenardan (saat) tetikle**; düşen kenar bulanık çıkar — bu gerçektir, kusur değil |
| Hafif yükte darbe atlama / burst | ❌ **çöp** | dalga tekrarlayan değil |
| Yayılı spektrum saat | ❌ | periyot dağılımı geniş |
| Yumuşak başlatma, yük basamağı | ❌ | tanım gereği tek-seferlik |
| **Arıza, açılış darbesi, MOSFET patlaması** | ❌ **asla** | ETS "nadir olay" aramak için kullanılamaz |

**🌟 Firmware'e reddetme mantığı koy.** MCPWM capture zaten her tetiğin zaman damgasını
veriyor. Periyot σ'sını hesapla: σ > 1 bin (12.5 ns) → uyar; histogram çok tepeli →
**reddet**, *"darbe atlama algılandı, tek-seferlik kullanın"* de. σ'yı her ETS başlığında
yayınla.

**Altın kural:** *ETS "kararlı bir çevrim neye benziyor" sorusunu cevaplar. Tek-seferlik
"ne oldu" sorusunu cevaplar. İkisini karıştırma.*

#### Tek-seferlik kip: bellek ve tetik

**DMA'yı DURDURMA.** ADC sürekli koşar, tetik akış üzerinde yazılımla aranır; tetik
bulununca halkadaki yazma imleci dondurulur → **ön-tetik bedava gelir**.

İki katmanlı tampon: ADC →DMA→ dahili SRAM halkası (32 KB) → toplama görevi →
PSRAM halkası (2 MB = kanal başına 12.6 s @ 41.67 kSa/s). Akış 333 KB/s; PSRAM oktal
yazma bandının ~1/150'si, darboğaz yok.

Tetik motoru: `seviye + kenar + histerezis + tutma(holdoff) + ön_tetik_oranı`.
Varsayılan kayıt 20 000 örnek/kanal (480 ms), azami 500 000 (12 s).

⚠️ Bkz. **4.9** (FQBN'de PSRAM açık değil) ve **4.11** (aktarım darboğazı) — ikisi de bu
kipin önkoşulu.

### 5.3 Wattmetre

Bugün güç zaten doğru hesaplanıyor: **örnek başına V×I çarpımının ortalaması**
(ort(V)×ort(I) değil — bu ikisi değişken yükte farklıdır ve A4 bunu gösteriyor).

Hızlı kanalla kazanılacak olan: **anahtarlamalı yükte gerçek ortalama güç**. Bir SMPS'in
girişindeki akım darbeli; 860 SPS ile bunun ortalaması yanlış çıkar, 83 kSa/s ile doğruya
yaklaşır.

Kayma düzeltmesi **zorunlu** — sayılar 5.1.1'de. İki ADS1115'in ayrı çipler olması bu
yüzden bilinçli bir tasarım kararıydı (A4'te "V ve I EŞ ZAMANLI örnekleniyor" notu);
hızlı kanalda aynı lüks yok, DSP ile telafi edilecek.

**Yayınlanacak yeni büyüklükler** (`D2` satırı): Vrms, Irms, P = Σ(v·i_hiza)/N, S, PF,
Q, Vdc, Idc, tepe faktörü (kırpma teşhisi için). Enerji uint64 pJ olarak korunuyor.

#### 🌟 Faz kalibrasyonu — sinyal üreteci gerektirmeyen yöntem

Kayma FIR'ı düzeltilse bile iki artık kalır: fark yükseltecinin 107 kHz kutbu (1 kHz'te
0.54° → PF 0.5'te **%1.6 hata**) ve iki SK süzgecin %5 uyumsuzluğu (0.25° → %0.76).
Bunlar **ölçülüp silinmeli**:

1. MCPWM (GPIO13) → kapı direnci → güç MOSFET'i → **saf dirençsel yük** (taş dirençler yolda)
2. Dirençsel yükte v ile i **tanım gereği aynı fazdadır** → ölçülen her faz farkı
   **aletin kendi hatasıdır**
3. Kare dalganın harmonikleri bandı doldurur → **tek ölçümde tüm bant**
4. Firmware çapraz-korelasyonla Δτ'yi bulur, NVS'e yazar, kesirli-gecikme FIR'ına uygular

Yeni komut `f`. Kart dışında **hiçbir alet gerektirmiyor** — envanterde olmayan tek şey
(sinyal üreteci) yerine olan şeyi (MOSFET + direnç + MCPWM) kullanıyor.

#### ⚠️ Anahtarlama düğümünde ölçülen güç ANLAMSIZDIR

41.67 kSa/s ile 100 kHz'e erişemezsin ve örtüşme süzgeci onu −31 dB kesiyor. **Ama bu
bir kayıp değil:** SMPS'in giriş DC barasında (giriş kondansatörünün arkasında) ölçtüğünde
anahtarlama bileşeninin net ortalama güce katkısı ihmal edilebilir. Örnek: 12 V üzerinde
50 mV dalgacık × 1 A p-p → en fazla ~12 mW, 12 W'ta **%0.1**.

Aşama 1'deki "DC bara tarafında ölç" kuralı doğruydu; hızlı kanalla artık bunun **neden**
doğru olduğunu sayıyla söyleyebiliyorsun.

### 5.4 Besleme — sanıldığından çok küçük bir iş

> ⚠️ **Bu bölüm 2026-09-08'de DÜZELTİLDİ.** Önce "hurda ATX zorunlu, yoksa Rds(on)
> ölçümü ölür" yazmıştım. **Yanlıştı.** Rakamlara bakınca ihtiyaç çok daha küçük.

**"15 V" bir hedef değil, sadece 7812/7912'nin giriş şartı** (dropout ~2.5 V → çıkışta
12 V için girişte ≥14.5 V). **12 V'u doğrudan bir kaynaktan alırsan regülatöre hiç gerek
kalmaz ve 15 V sorunu tamamen ortadan kalkar.**

#### İki ayrı ihtiyaç var — karıştırma

**A) ±12 V analog ray — çok küçük**

| Tüketici | Adet | Ray başına |
|---|---|---|
| TL072 (2.8 mA/paket tipik, 5 mA azami) | 4 | 11 mA tipik / 20 mA azami |
| LM319 (~4.3 mA) | 2 | ~9 mA |
| **Toplam** | | **~20 mA tipik, 50 mA tasarım hedefi** |

**B) +12 V güç rayı — tepe yüksek, ORTALAMA DÜŞÜK**

> 🔴 **Düzeltme: elektronik yük bu raya ihtiyaç duymuyor.** Yükün harcadığı güç, test
> edilen cihazdan gelir — bizim beslememizden değil.

| Kullanım | Tepe | Darbe | Görev | **Ortalama** |
|---|---|---|---|---|
| Rds(on) ölçümü | 5 A | 1 ms | %2 | 100 mA |
| Doyum testi | 10–15 A | 100 µs–1 ms | %1 | ~100 mA |

**Tepe akımı kondansatör bankası karşılar; besleme sadece ortalamayı verir.**
Stokta ≥25 V dayanımlı elektrolitik: 470µF/35V ×6 + 470µF/63V ×6 + 1000µF/35V ×5 +
1000µF/25V ×1 = **~11 600 µF**.

- Rds(on): 5 A × 1 ms = 5 mC → 10 000 µF'ta düşüm **0.5 V** ✅
- Doyum: 10 A × 100 µs = 1 mC → düşüm **0.1 V** ✅

**Sonuç: 12 V @ 1–2 A + kondansatör bankası yeter.** 15 A'lik kaynak gerekmiyor.

#### Nasıl elde edilir — kolaydan zora

| # | Yol | Not |
|---|---|---|
| **1** ⭐ | **İki izole 12 V adaptör, seri** | Birinin (−)'sini diğerinin (+)'sına bağla, o düğüm GND. Doğrudan ±12 V. **Regülatör yok, trafo yok, 15 V yok.** Duvar adaptörleri izoledir |
| **2** ⭐ | **Tek 12 V adaptör + NE555 şarj pompası** | +12 adaptörden, −12 NE555'ten (yolda ×10). ~50 kHz astable + SR5100 Schottky pompası (stokta ×10) → 50 mA'de ~−10.5 V |
| 3 | 15-0-15 trafo + köprü + 7812/7912 | 15 V'un asıl geçtiği yer. E tipi çekirdek ×2 stokta, sarılabilir — ama sıradan bir besleme için emek |
| 4 | Hurda ATX | Tek kutuda +12/−12/+5/+3.3. **Kolaylık, zorunluluk değil** |

> 🌟 **−12 V olması şart değil.** TL072'nin giriş ortak-mod aralığı negatif raydan ~4 V
> yukarıda başlar; sinyaller 0 V civarında olduğu için **−10 V fazlasıyla yeterli**.
> Asimetrik ray (+12/−10) sorun değil. Bu, 2. yolu tamamen geçerli kılıyor.

⚠️ ATX kullanılırsa −12 V rayı gürültülüdür. Opamp beslemesi için sorun değil (TL072
PSRR ~100 dB + yerel 100 nF/10 µF bypass), ama **analog referans olarak asla
kullanılmamalı** — referans zinciri 3.3 V / TL431 tarafında kalıyor.

### 5.5 🌟 En önemli mimari karar: beş yetenek üç yapı taşı paylaşıyor

| Yapı taşı | Kim kullanıyor |
|---|---|
| **A. PWM→RC analog referans** (LEDC + 2 kutuplu RC) | Elektronik yük, eğri çizici (2 eksen), doyum testi eşiği |
| **B. Opamp + MOSFET + şönt lineer çevrim** | Elektronik yük, eğri çizici, doyum akım sınırı |
| **C. MCPWM capture zaman tabanı** | SMPS zamanlama, doyum testi |
| **D. ±12 V ray** | A, B ve komparatörler |

> **Eğri çizici (transfer kipi) ile elektronik yük FİZİKSEL OLARAK AYNI DEVREDİR.**
> Fark tek satır firmware: yükte MOSFET sabit ve DUT dışarıda; eğri çizicide DUT'un
> kendisi o MOSFET'in yerine takılıyor. **Birlikte kurmak ~%70 iş tasarrufu.**

### 5.6 Eğri çizici

**İki kip, iki maliyet sınıfı:**

**Mod-T (transfer/eşik) — ucuz, en yüksek getiri.** DUT'u lineer çevrimin MOSFET yuvasına
tak; opamp DUT'un kendi kapısını sürüp akımı sabitler, firmware akımı süpürüp Vgs okur.

| Ölçüm | Şönt | Gerçekçi doğruluk |
|---|---|---|
| **Vgs(th)** (Id = 250 µA'e servo) | **1 kΩ** | ±20 mV |
| Id–Vgs transfer eğrisi, gfs | 1R / 0.1R | ±%0.3 akım, ±5 mV Vgs |
| **Rds(on)** (Vgs=10 V, Id=5 A, Kelvin) | 0.1R / 15mR | **±%0.5** |
| BJT hFE | 1R | ±%2 |
| Diyot/LED Vf–If | 1k → 0.1R | ±2 mV |
| **Sökme parça ayıklama** | 1k / 1R | *mutlak değil, sağlam parçayla FARK* |

> 🌟 **Neden 1 kΩ şönt şart:** Vgs(th) tanım gereği 250 µA'de ölçülür. 1R şöntte bu
> **250 µV** eder — TL072'nin ofsetinin (10 mV) kırkta biri, ölçülemez. 1 kΩ'da 250 mV
> olur. Stokta 1K ×36 var.

**Mod-O (Id–Vds eğri ailesi) — pahalı, SONA bırak.** Programlanabilir ray gerekiyor
(2. opamp + IRF4905 yüksek taraf geçiş elemanı + ATX). Mod-T zaten sayısal cevapları
veriyor; Mod-O güzel grafik veriyor.

#### 🔴 ADS1115 darbeli süpürmede KULLANILAMAZ

ADS1115 delta-sigma'dır, **dönüşüm penceresi boyunca ORTALAMA alır**. 1 ms'lik darbeye
1.16 ms'lik dönüşümle bakarsan darbenin kapalı kısmını da ortalamaya katar → sistematik
düşük okur.

**Doğru iş bölümü:** darbe = ESP32 ADC (12 µs, 64 ortalama = 0.77 ms, ~%1);
DC noktaları = ADS1115 (%0.05). Isınmanın sorun olduğu yerler zaten %1'in yettiği
yerler; Vgs(th) ve Rds(on) DC ölçülebilir ve orada %0.05 alınır.

**Darbe parametresi: tp = 1 ms, T = 50 ms (%2 görev).** Tek darbede ΔTj < 2 °C, ortalama
1.2 W (soğutucusuz taşınır), 0.77 ms'lik ölçüm 1 ms'e sığar. 500 noktalık aile **25 s**.
DAC oturması (1.93 ms) soğuma süresinin arkasına gizlenir, bedava.

#### 🔴 Kelvin, Rds(on) için ZORUNLU

| Parça | Rds(on) | Soket+tel (30 mΩ) hatası | **Kelvin (0.5 mΩ)** |
|---|---|---|---|
| IRF3205 | 8.0 mΩ | **%375** | %6.2 |
| IRFZ44N | 17.5 mΩ | %171 | %2.9 |
| IRFP250N | 75.0 mΩ | %40 | %0.7 |

**Kelvin'siz IRF3205'in Rds(on)'unu ölçersen gerçek değerin 4.75 katını okursun.** Bu
ölçüm değil, gürültü. DUT soketinden **dört ayrı tel** (2 kalın güç, 2 ince algılama,
bacağın dibine) → ADS U3 AIN2-AIN3 diferansiyel, PGA ±0.256 V.

⚠️ **Sıcaklık:** Vgs(th)'nin tempco'su ~−5 mV/°C. Elinle parçaya dokunursan eşik 15 mV
kayar. Darbeli süpürme bunu çözmez — parça ortam sıcaklığında olmalı, iki ölçüm arasında
30 s beklenmeli.

**LEDC bölüşümü:** T0 = 12 bit @ 19.53 kHz (2× 1k+1µF RC → ripple 279 µV = 0.35 LSB,
oturma 19.3 ms) — yük akım referansı, eğri çizici Vgs ekseni, doyum eşiği.
T1 = 10 bit @ 78 kHz (2× 1k+100nF → 1.93 ms oturma) — hızlı Vds ekseni.
**14 bit kullanma:** 4.88 kHz taşıyıcıda 0.5 LSB ripple için τ = 1.68 s → 500 nokta
97 saniye. Ölü. Çözünürlük eksiği ADS1115'in dış cevrimiyle kapatılır — **iç analog
çevrim kararlılık için, dış sayısal çevrim doğruluk için.**

### 5.7 Dört ek yetenek

#### SMPS zamanlama analizörü — en ucuz, ~5 TL

**Optokuplör ölü (doğrulandı):** PC817'nin tr/tf'i tipik yükte 10–20 µs ve CTR %50–600
arası değiştiği için gecikme **mikrosaniyeler mertebesinde oynar**. Ölçülecek ölü zaman
100 ns – 2 µs → *aletin belirsizliği ölçtüğü şeyden 5–10 kat büyük.*

**Kazanan: rezistif bölücü + TL431 rayına kelepçe.** Gecikme sadece RC (3.7–13.6 ns) ve
kanallar aynıysa ortak mod olduğu için **ölü zaman farkında yok oluyor**.
3.3 V rayına kelepçe olmaz (3.3+0.7 = 4.0 V > 3.6 V mutlak azami); TL431 rayında düğüm
en fazla **3.195 V** — VIH'in 0.72 V üstünde, mutlak azaminin 0.4 V altında. **Bu ray
kartta zaten var.**

Menzil jumper'ı: R1 = 1k/2.7k (5 V mantık) · R2 = 1k/330R (12–15 V kapı) ·
R3 = 10k/1k (yüksek taraf). Hepsi stokta.

> 🌟 **En yüksek getirili firmware özelliği: de-skew kalibrasyonu.** Aynı sinyali üç
> kanala birden ver, artık farkı ölç, NVS'e kaydet, her ölçümde çıkar. Bu tek adım
> bölücü RC farkını, GPIO eşik dağılımını, direnç toleransını ve iz gecikmesini
> **hepsini birden** siler.

**Gerçekçi doğruluk:** frekans ±20 ppm (kristal sınırlı), duty ±0.02 %-puan (hızlı
kenar), **ölü zaman ±15 ns (1σ)** — 200 ns'lik bir ölü zamanı %7.5 ile ölçmek demek,
SMPS ayarı için fazlasıyla yeterli. Azami ~500 kHz (ISR sınırı), patlama kipinde 1 MHz.

**Yüksek taraf:** kapı sinyali yüzen referansta. **En iyi cevap: kontrolcü çıkışlarını
ölç** (SG3525 pin 11/14, TL494 OUT, IR2110 HIN/LIN) — bunlar toprak referanslı ve ölü
zamanın kaynağı zaten kontrolcü. Gerçek izolasyon şartsa 6N137 (50 ns, ~10 TL).

⚠️ 1N4148 stokta 8 adet; 6'sı bu işe gidiyor, Aşama 2 zaten 2 kullanıyor. **Yeni al.**

#### Elektronik yük

**MOSFET: IRFP250N** (IRFZ44N değil) — TO-247 daha büyük soğutucuya oturur, 200 V marjı
doyum testinde de işe yarar, büyük çip lineer bölgede termal kararsızlığa dayanıklı.

**Opamp: TL072, LM358 DEĞİL.** Sırasıyla: (1) LM358'in çıkışı **B sınıfı ve crossover
distorsiyonlu** — kapalı çevrimde sıfır geçişinde kazanç çöküşü → limit-cycle salınımı.
*Elektronik yükün ötmesinin en yaygın sebebi budur.* (2) Aşağı doğru zayıf çeker
(~20 µA) → kapı yavaş kapanır. (3) Slew 0.3 vs **13 V/µs** (43×). (4) Bias 45 nA vs
30 pA — 1 kΩ şöntte 45 µV hata.

**Kararlılık — somut değerler:** `Rin = 10 kΩ, Cf = 10 nF, Rg = 100 Ω, Cgs_ext = 10 nF`
→ faz payı her akımda ve her şönt kademesinde **>80°**. (Cf = 1 nF yaparsan 33°,
100 pF yaparsan 3.7° — öter.) Ek olarak: drain snubber 10R+100nF, kapı pull-down 10k,
yerel bypass, şönt→opamp ve şönt→GND **ayrı, kısa, bükülü** teller.

**Soğutucu ZORUNLU — ✅ kullanıcıda var (`MEK002`), ama ölçüsü teyit edilmeli:**

| Soğutucu | İzin verilen P | 12 V'ta Id |
|---|---|---|
| **yok** | **2.4 W** | 0.20 A |
| 5 °C/W | 15.4 W | 1.29 A |
| **2 °C/W** | **30.2 W** | **2.51 A** |

"12 V × 2 A = 24 W" için **≤2.5 °C/W** şart (~100×60×30 mm kanat veya 60×60 + fan).

> ⚠️ **MOSFET'leri lineer bölgede PARALEL BAĞLAMA.** Vgs(th) tempco'su negatif → sıcak
> olan daha çok çeker, daha çok ısınır. **Termal kaçak, kaçınılmaz.** Doğrusu: her
> MOSFET'e kendi opampı ve kendi şöntü. TL072 ×4 = 8 kanal var, ikinci kanal bedava.

> 🔴 **Donanım watchdog ŞART.** MCU çökerse PWM registeri son değerinde donar → referans
> tam kalır → yük 30 W'ta sonsuza kadar çeker. Şarj pompası + 470k boşaltma + 2N2222
> kapıyı kaynağa kısa devre eder, 0.5 s'de keser. **Tüm parçalar stokta.**
> Ayrıca: NTC (yazılım foldback) + KSD9700 70 °C termal anahtar (donanım kesici).

**Otomatikleşen ölçümler:** yük regülasyonu eğrisi (10 s), verim süpürmesi (25 s), pil
kapasitesi (±%0.3), kaynak iç direnci (2 s), kondansatör ESR (100 ms), SMPS geçici
yanıtı (20 ms pencere), aşırı akım koruma testi (30 s).

#### Bobin/trafo doyum testi

**Sadece ADC ile: L ≥ ~600 µH @ 12 V.** Yani şebeke bobinleri ve büyük trafo primerleri.
**Tipik SMPS bobinleri (10–500 µH) kapsam DIŞI.** ("Daha düşük gerilim" çare değil —
DCR devreye girip rampayı eksponansiyele çeviriyor: 100 µH/100 mΩ'da 2 V'ta eğrilik %11.5.)

> 🌟 **Doğru yöntem: komparatör + MCPWM capture.** Genlik problemini zaman problemine
> çevirip zamanı 12.5 ns'de ölç. Eşiği LEDC DAC ile süpür, LM319 tetiklenince capture
> zaman damgası al. **L(I) = V·Δt/ΔI** — ardışık eşikler arası farkta komparatörün sabit
> gecikmesi **tamamen yok olur**, sadece jitter kalır.
> Üç capture kanalı = tek atışta üç eşik → atıştan atışa sapma da yok olur.

| Sürüş | L | **L hatası** |
|---|---|---|
| 12 V | 10 µH | %3.39 |
| **12 V** | **100 µH** | **%0.34** |
| 12 V | 500 µH | %0.068 |

**Kapsanan menzil: 5 µH – 100 mH, 0.1–15 A** — SMPS bobinlerinin tamamı içeride.

🔴 **LM319N ×2 alınmalı (~15 TL) — envanterde komparatör yok.** TL072 açık çevrim
~2000 ns gecikme/500 ns jitter verir → 100 µH'de %13 hata, işe yaramaz.
**Bu tek parça, doyum testini "yapılamaz"dan "±%0.3"e taşıyor.**

⚠️ **Darbe anahtarı IRFP250N (200 V) olmalı, IRFZ44N (55 V) DEĞİL.** UF4007 + 3.3R 11W
kelepçesiyle 10 A'de Vds tepe **45.7 V**'a çıkıyor; kablo endüktansı üstüne binerse
IRFZ44N avalanche'a girer.
⚠️ **IR2110/IR2104 3.3 V mantıkla doğrudan sürülemez** (VIH = 9.5 V @ Vcc=15 V) —
2N2222 açık kollektör evirici + 1k pull-up → +12 V gerekiyor.

#### Verim ölçer

**Kanal dağılımı — kaymayı YAVAŞ değişkene koy.** ADS1115'te tek ADC + mux var; 4 kanal
için biri mutlaka çoklanacak. SMPS baralarında **gerilim yavaş ve düzgün, akım hızlı ve
tırtıklıdır**:

| | U1 (0x48) | U2 (0x49) | U3 (0x4A) |
|---|---|---|---|
| ✅ **Seçilen** | **Ii diff, sürekli** | **Vi + Vo çoklanmış** (2.33 ms kayma) | **Io diff, sürekli** |

**Hata bütçesi.** %90 verimi ±1 puan mutlak ile ölçmek = bağıl %1.111 → kanal başına
%0.278 (en kötü hal) veya %0.556 (RSS). Mevcut donanımın kanal başına gerçekçi hatası:
δV = %0.251, δI = %0.115 → **η hatası ±0.352 puan (RSS)**. **±1 puan hedefi
karşılanıyor** — ama üç şartla:

| # | Şart | Yapılmazsa |
|---|---|---|
| 1 | Dört kanal **aynı referansla, aynı noktada** kalibre | ±0.97 puan |
| 2 | Örtüşme süzgeçleri düzeltilecek (aşağıda) | aliasing %1'e kadar kayma → geçersiz |
| 3 | Bölücülerde **metal film %1, ≤100 ppm/°C** | karbon filmin 250 ppm/°C'si bütçenin %90'ını yer |

> ### 🌟🌟 EN ÖNEMLİ İÇGÖRÜ — AN8000 sorununu büyük ölçüde çözüyor
>
> η = (Vo/Vi)·(Io/Ii). Vi ve Vo'yu **aynı DMM ile, aynı gerilimde** kalibre edersen,
> DMM'in kazanç hatası her ikisine de aynı çarpanla girer ve **oranda birinci mertebede
> yok olur.**
>
> | Kalibrasyon referansı | Kanalları AYRI kalibre | **AYNI referans, AYNI nokta** |
> |---|---|---|
> | **Hobi DMM %0.5 (AN8000)** | ±**0.966** puan | ±**0.352** puan |
> | 6.5 hane %0.05 | ±0.363 puan | ±0.352 puan |
>
> **Bir %0.5'lik hobi multimetresi, 6.5 haneli masa referansıyla neredeyse eşdeğer hale
> geliyor.** Bölüm 1.3'teki "AN8000 tavanı" endişesi verim ölçümü için büyük ölçüde
> geçersiz — çünkü orada mutlak değil **oran** ölçüyorsun.
>
> **Uygulama:** (1) Vi ve Vo'yu aynı DMM ile aynı gerilimde (ör. ikisi de 12.00 V).
> (2) Akımlar için **iki şöntü SERİ bağla, tek akım geçir, ikisini birden okut** —
> kaynağın mutlak değerini bilmene bile gerek yok, sadece oranı eşitliyorsun.
> (3) Kalibrasyonu ölçümle aynı sıcaklıkta, aynı gün yap.

**🔴 Yeni bulunan kusur — voltmetre bölücüsündeki 1 nF:** ADS1115'in modülatörü ~250 kHz'te
koşar; 100 kHz ripple **katlanarak DC'ye biner** ve ortalamayı kaydırır. Mevcut 1 nF
(fc 25 kHz) 100 kHz'te sadece −12.3 dB. **1 nF → 100 nF yap** (fc 250 Hz, −52 dB).
Osiloskop AYRI bölücüden beslendiği için etkilenmez → **hiçbir şeyi bozmayan bedava
40 dB iyileşme.** Akım kanallarında da 100 nF → 1 µF, iki kademe.

**Doğrulama testi:** girişi ve çıkışı **kısa devre et** → η = %100 okumalı. Sonra araya
bilinen bir direnç koy → η hesaplanabilir. Bu iki test sistematik hataları yakalar.

🔴 **Offline (şebeke referanslı) SMPS verim ölçümü bu kartın KAPSAMI DIŞINDA.** Toprakları
bağlarsan izolasyon bariyerini kısa devre edersin; bağlamazsan ADS'nin ortak mod sınırını
(±0.3 V) aşarsın ve çip anında ölür. Yapılabilmesi için tam izole bir ölçüm adası gerekir
(ayrı ESP32 + izole DC/DC + opto UART) — **ayrı proje.**

### 5.8 Satın alma listesi

> ⚠️ **Bu liste 2026-09-08'de küçüldü.** ATX ve soğutucu "zorunlu"dan çıktı — bkz. 5.4
> (besleme sanıldığından küçük) ve aşağıdaki soğutucu notu.

**Zorunlu (~40 TL):**

| Parça | Adet | Ne için |
|---|---|---|
| **LM319N** (çift komparatör, 80 ns) | 2 | Doyum testi. **Envanterde komparatör yok.** Bu tek parça doyum testini "yapılamaz"dan ±%0.3'e taşıyor |
| **10 kΩ NTC B3950** | 2 | Elektronik yük aşırı sıcaklık koruması (yazılım foldback) |
| **KSD9700 70 °C NC** | 1 | Donanım ısı kesici — firmware'den bağımsız |
| **Metal film %1 ≤100 ppm/°C** (100K, 10K, 6.8K, 1K) | 10'ar | Verim bölücüleri. Karbon filmin 250 ppm/°C'si bütçenin %90'ını yer |
| **1N4148** | 20 | Elektronik yük kelepçeleri + watchdog (stokta 8). **Ölçüm kartı bunu kullanmıyor** — orada BAT85 |
| Mika yalıtkan + montaj seti | 5 | MOSFET–soğutucu |

**Duruma bağlı:**

| Parça | Ne zaman gerekir |
|---|---|
| ~~12 V adaptör ×2~~ | ✅ **ÇÖZÜLDÜ, 5.12.23**: 12 V adaptör yok; 6× 18650 (iki 3'lü paket sırt sırta) ±9…±12.6 V veriyor, yükseltici gerekmiyor. Yedek yol: 24 V kaynak + LM358 orta nokta tamponu |
| **Soğutucu ≤2 °C/W** | ✅ **Kullanıcıda VAR** (2026-09-08 bildirdi, `MEK002`). ⚠️ **Ölçüsü/termal direnci BİLİNMİYOR** — 2 °C/W eşiği elektronik yükte 2.4 W ile 30 W arasındaki farkı belirliyor. **Yeni oturum bunu teyit etsin ve CSV'yi güncellesin** |
| Hurda ATX | Kolaylık isteniyorsa. **Zorunlu değil** |

**❌ ALMAYA GEREK OLMAYANLAR** (yaygın yanılgılar):

| Parça | Neden gereksiz |
|---|---|
| Harici I2C DAC (MCP4725) | LEDC 12 bit + 2 kutuplu RC + ADS dış cevrimi **daha iyi** sonuç veriyor |
| Hızlı ADC modülü | Doyum testinin ADC problemi komparatör+capture ile tamamen çözülüyor |
| Yeni optokuplör | Zamanlama işi için hiçbiri kullanılamaz (hız) |
| Mantık seviyesi MOSFET | ±12 V rayı sorunu çözüyor; lineer bölgede Vgs zaten 5 V |

### 5.9 Önerilen pin planı (Aşama 3)

| Pin | Kanal | Görev | Ön uç |
|---|---|---|---|
| GPIO4 | ADC1_CH3 | **Skop — ham** | kompanze bölücü → TL072 tampon, **süzgeç yok** |
| GPIO5 | ADC1_CH4 | **Ölçüm V (hızlı)** | *ADS ile AYNI* bölücü → tampon → SK 16.55 kHz |
| GPIO6 | ADC1_CH5 | **Ölçüm I (hızlı)** | ayrı Kelvin çifti → fark yük. G=27 → SK 16.55 kHz |
| GPIO7 | ADC1_CH6 | **Skop — süzülmüş** | aynı tampon → SK 16.55 kHz |
| GPIO10 | ADC1_CH9 | **Akım — ham** | fark yük. çıkışı doğrudan (bobin akımı ETS) |
| GPIO1/2 | CH0/CH1 | boş | 2. gerilim düğümü (verim) |
| GPIO8/9 | — | I2C SDA/SCL | mevcut |
| GPIO12 | — | **MCPWM capture girişi** | SMPS gate sürücüden sayısal senk |
| GPIO13 | — | **MCPWM üreteç çıkışı** | uyarım / prob-komp / faz kalibrasyonu |
| GPIO14 | — | LEDC PWM → RC | tetik seviyesi "DAC"ı |
| GPIO21 | — | ADS ALERT/RDY | **GPIO7'den taşındı** |
| GPIO19/20 | — | **yerel USB CDC** | derin kayıt aktarımı (bkz. 4.11) |

**TL072 kesit dağılımı (4 çip = 8 kesit, tam oturuyor):** U1a akım fark yükselteci ·
U1b akım SK · U2a gerilim tamponu · U2b gerilim SK · U3a skop tamponu · U3b skop SK ·
U4a fark yük. REF tamponu (+1.5 V) · U4b yedek.

> ### 🔴 ÇÖZÜLMEMİŞ: pin planı çakışması
>
> Bu belge iki ayrı tasarım çalışmasından derlendi ve **ikisinin pin planı çakışıyor.**
> Gizlemek yerine işaretliyorum — yeni oturumun ilk işlerinden biri bunu çözmek olmalı.
>
> | Pin | Toplama mimarisi istiyor | Enstrüman yetenekleri istiyor |
> |---|---|---|
> | GPIO5 | Ölçüm V (hızlı ADC) | Doyum rampası (hızlı ADC) |
> | GPIO6 | Ölçüm I (hızlı ADC) | Eğri çizici Vds (hızlı ADC) |
> | GPIO7 | Skop süzülmüş (ADC) | ADS ALERT (mevcut yerinde kalsın diyor) |
> | GPIO10 | Akım ham (ADC) | yedek |
> | GPIO11–18, 21, 38 | — | MCPWM capture/fault/üreteç, 4× LEDC, watchdog |
>
> **ADC1'de yalnız 10 kanal var (GPIO1–10)** ve iki tasarım toplamda bundan fazlasını
> istiyor. Çakışma gerçek, uydurma değil.
>
> **Çözüm yönü:** yetenekler aynı anda çalışmıyor. Kip bazlı pin paylaşımı (ölçüm kipinde
> V/I, eğri çizici kipinde DUT, doyum kipinde rampa) ADC pinlerini üçe bölmek yerine
> yeniden kullanmayı sağlar. Ama bu, **analog çoklayıcı** gerektirebilir — envanterde
> CD4051/4066 **yok** (Entegre kutusu tam tarandı). Alternatif: ayrı ön uçları ayrı
> pinlere bağlayıp kullanılmayanı yüksek empedansta bırakmak.
>
> ⚠️ **Ayrıca doğrulanmalı:** GPIO11–18, 21, 38 pinlerinin senin geliştirme kartında
> **gerçekten pin başlığına çıkarıldığı**. Bazı ESP32-S3 kartları çıkarmaz. Yedek:
> GPIO39–42 (JTAG) ve GPIO43/44 (UART0; yerel USB kullanılıyorsa boşta).
> **GPIO11–14 = ADC2, WiFi ile çakışır — bu pinleri yalnız SAYISAL olarak kullan.**

**Yeni alınacak (birkaç lira):** 1 nF C0G şerit (SK süzgeçler için pay), BAT54 ×6
(geniş bantlı alt kelepçe), 5–30 pF trimer ×2 + 470 pF C0G ×2 (bölücü kompanzasyonu).
27K, 1K, 6.8K, 10 k trimpot, SR5100 **stokta var**; TL072, ±12 V regülatörleri, şöntler
**yolda**.

### 5.10 Önerilen uygulama sırası

Yapı taşları paylaşıldığı için sıra önemli:

Her adımın bir **kapısı** var — geçmeden sonrakine geçme. Bu, projenin mevcut
doğrulama kültürünün devamı.

| # | İş | Kapı (geçme koşulu) |
|---|---|---|
| **3.0** | **Sıfır donanım — ÖNCE ÖLÇ.** Yeni `A6` adımı: 2 kanallı pattern'i kur, `type2.channel` demux'unu 60 s kanıtla, **gerçek dönüşüm hızını GPTimer ile ölç**, ESP ADC gürültü tabanını 6.37 kΩ ve düşük empedanslı kaynakla ölç, FQBN'e `PSRAM=opi` ekle | Hız ölçüldü, çerçeve düşmesi 0, `ps_malloc(2MB) != NULL` |
| 3.1 | **±12 V rayı + TL072 ön ucu** (donanım). Sıra: regülatör+dekuplaj → V tamponu+SK → skop tamponu+SK → REF tamponu → fark yükselteci+SK. **Her op-amp çıkışında 1 kΩ + üst 1N4148 + alt Schottky, istisnasız.** ALERT'i GPIO21'e taşı | Her kesitin DC kazancı DMM ile; sonra kartın kendi kare dalgasıyla basamak cevabı |
| 3.2 | **Hızlı wattmetre + hibrit disiplinleme.** 2 kanallı edinim, kayma FIR'ı, RLS disiplinleme, `D2` satırı, `f` faz kalibrasyonu | MCPWM+MOSFET ile dirençsel yükü %D görev çevrimiyle kes → beklenen güç analitik biliniyor → ölçülenle karşılaştır. **`ort(V)×ort(I)`'nin aynı testte kaç kat yanıldığını da yazdır** |
| 3.3 | **Tek-seferlik osiloskop.** PSRAM halkası, tetik motoru (histerezis + tutma + ön-tetik), `S2` protokolü ikili, yerel USB CDC | 500 000 örnek < 1.5 s'de aktarılıyor; ön-tetik gerçekten tetiğin öncesini gösteriyor |
| 3.4 | **ETS — uyarım kilitli (kolay kip).** MCPWM asal periyot (P=799), koherent faz binleme | **Kart kendi kare dalgasının kenarını ETS ile kurup kendi bant genişliğini ölçüp yayınlıyor** |
| 3.5 | **ETS — harici sayısal tetik (SMPS kipi).** MCPWM capture, periyot titreşimi ölçümü ve reddetme mantığı | Bilerek titretilmiş uyarımda kart ETS'i **reddediyor** — dürüstlük mekanizması çalışıyor |
| 3.6 | **SMPS zamanlama analizörü** | 3.5'in capture altyapısı hazır olduğu için buraya taşındı |
| 3.7 | **Verim ölçer** | 3. ADS1115; 3.2'nin kalibrasyonuna dayanıyor |
| 3.8 | **Elektronik yük** | PWM→RC→opamp→MOSFET; 3.7 ile birleşince verim süpürmesi otomatikleşir |
| 3.9 | **Eğri çizici** | 3.8'in yapı taşının aynısı, farklı süpürme mantığı |
| 3.10 | **Bobin/trafo doyum** | 3.6'nın capture altyapısı + 3.8'in güç katı |

> **Kurulum sırası not:** 3.1'den önce kartın Aşama 2 haliyle delikli plakete kurulup
> kalibre edilmesi gerekiyor (`kurulum2.html`, plakete göre güncellenmeli).

#### İkinci iz — enstrüman yetenekleri (yukarıdakine paralel yürüyebilir)

Bu iz, toplama zincirinden **büyük ölçüde bağımsız** ve farklı bir bağımlılık ağacı var.
Yapı taşı haritası:

```
              ┌─ SMPS zamanlama
   MCPWM ─────┤
   capture    └─ Doyum testi ────┐
                                 │
   ±12 V ──┬─ Lineer çevrim ─────┼─ Eğri çizici Mod-T
           │   (TL072+MOSFET+    │
           │    şönt)            ├─ Elektronik yük ── Verim ölçer
           │                     │
           └─ Mod-O geçiş elemanı
   PWM DAC ──┬─ yük/eğri çizici (akım referansı)
   (LEDC)    ├─ doyum (komparatör eşiği)
             └─ Mod-O (Vds ekseni)
```

| # | Adım | Bağımlılık | Süre | Kapı |
|---|---|---|---|---|
| **E0** | **±12 V rayı** — 5.4'teki dört yoldan biri + yerel bypass + kondansatör bankası | — | 1 akşam | +12/−10..−12 V, ripple <50 mV; 5 A'lik 1 ms darbede bara düşümü <0.5 V |
| **E1** | **SMPS zamanlama analizörü** — 3 bölücü + kelepçe + capture ISR + **de-skew** | **yok** (saf sayısal) | 2 akşam | NE555 ile bilinen frekans ±20 ppm; aynı sinyal 3 kanala → de-skew sonrası fark <15 ns |
| E2 | **PWM→RC DAC bloğu** (T0 12b/19.5k + T1 10b/78k) | E0 | 1 akşam | Ripple <300 µV, oturma <20 ms, ADS ile lineerlik %0.1 |
| **E3** | 🔑 **Lineer çevrim** (TL072 + IRFP250N + soketli şönt + snubber + watchdog + NTC) | E0, E2 | 3 akşam | **Salınım yok** — skopla kapı ve drain'e bak, her kademede 1 mA–3 A. Adım tepkisi aşımsız |
| E4 | **Eğri çizici Mod-T** — DUT soketi + Kelvin uçları + dış cevrim | E3 | 2 akşam | Yeni IRFZ44N'in Vgs(th)'si 2–4 V; Rds(on) 17.5 mΩ ±%5; **sökme parçalar ayırt ediliyor** |
| E5 | **Elektronik yük tam** — soğutucu, OTP, kademe süpürmesi, mAh | E3 | 2 akşam | 30 dk 12 V @ 2 A: soğutucu <80 °C, akım kayması <%0.5 |
| E6 | **Doyum testi** — LM319 ×3 + 2N2222→IR2110 + 3.3R kelepçe | E1, E2, E3 | 3 akşam | Bilinen bobin LCR değerine ±%2; doyum dizi görünür |
| E7 | **Verim ölçer** — 3. ADS + süzgeç düzeltmeleri + ortak-referans kalibrasyonu | E0, E5 | 2 akşam | **Kısa devre testi η = %100 ±0.4 puan** |
| E8 | **Eğri çizici Mod-O** | E4, E6 | 3 akşam | Id–Vds ailesi veri sayfası eğrileriyle örtüşüyor |

> 🌟 **E1 en başta** çünkü hiçbir şeye bağımlı değil — ±12 V bile gerektirmiyor. Bir
> akşamda çalışan bir alet çıkıyor ve MCPWM capture altyapısını E6 için hazırlıyor.
> **Kullanıcı hızlı bir kazanım isterse buradan başla.**
>
> 🔑 **E3 pivot.** Yükün, eğri çizicinin ve doyum testinin akım sınırının hepsi bu tek
> devre. **Kararlılığı tezgahta çözmeden ileri gitme** — E4, E5, E6 hep buna yaslanıyor.

### 5.11 Yapılamayanlar — açık liste

| İstenen | Neden yapılamıyor | Ne gerekir |
|---|---|---|
| **Offline (şebeke referanslı) SMPS verim ölçümü** | Toprakları bağlamak izolasyonu kısa devre eder; bağlamamak ADS'nin CM sınırını aşar | Tam izole ölçüm adası — ayrı proje |
| **12 V / 20 V zener dizini** | +12 V ray 12 V zeneri kırmaz; geçiş elemanı headroom'uyla ancak ~10.5 V | 30–50 V ek ray |
| **10 µH altı endüktans** | 24 V'ta 5 µH → rampa 1 µs, LM319 jitter'i %13.6 hata | TLV3501 (4.5 ns) |
| **Lineer bölgede MOSFET paralelleme** | Vgs(th) negatif tempco → termal kaçak. **Fizik yasağı** | Her MOSFET'e ayrı opamp + ayrı şönt |
| **Sadece ADC ile 10–500 µH doyum** | 12 µs/örnek, 12 V'ta örnek başına 1.44 A | Komparatör + capture (çözüm var) |
| **Kelvin'siz Rds(on)** | Soket+tel direnci ölçülen değerin 1.7–3.75 katı | Kelvin, tartışmasız |
| **Optokuplörle ölü zaman** | PC817/4N35 gecikme *değişimi* ölçülen büyüklükten büyük | 6N137 veya toprak referanslı kontrolcü çıkışı |
| **Sürekli 24 W yük, soğutucusuz** | Soğutucusuz izin verilen güç 2.4 W | ≤2 °C/W soğutucu |
| **100 kHz anahtarlamayı gerçek zamanda görmek** | 2 kanalda Nyquist 20.83 kHz | ETS (tekrarlayan sinyalde) |
| **Tek seferlik olayı ETS ile yakalamak** | Yöntemin doğası | Gerçek zamanlı kip, 20.83 kHz sınırıyla |

### 5.12 🎯 Ön uç yeniden tasarımı — TASARLANDI ve DOĞRULANDI (2026-09-08)

Kullanıcının üç isteği. **Tasarım bitti, simüle edildi, zincire girdi.**
Donanım kurulmadı; firmware ve şema henüz yazılmadı.

```
cd projeler/olcum-karti/uretim && python dogrula3.py     # B1 + B2, ~1 s
```

**B1 44/44 kural · B2 27/27 SPICE doğrulaması · toplam 71, 0 hata.**

| İstek | Sonuç |
|---|---|
| 400–600 V | **±615.4 V**, adım 18.78 mV, giriş Z **4.93 MΩ** |
| Negatif (±) | Vref referanslı diferansiyel — **ek çip yok** |
| V–I kayması az | 4 katsayılı Lagrange, **faz hatası tam sıfır** |

#### 5.12.1 Çift yönlülük — türev

Bölücünün alt ucu GND yerine **tamponlu bir Vref**'e bağlanır, ölçüm
diferansiyel yapılır. `k = 1/N` olsun:

```
düğüm = Vref + (Vin − Vref)·k
fark  = düğüm − Vref = (Vin − Vref)/N        ← İŞARETLİ
Vin   = N·fark + Vref
```

🌟 **Vref hatası ε kadarsa, ölçülen Vin tam ε kadar kayar — N'den bağımsız.**
Yani Vref hatası girişe vurulmuş sabit bir *ofset*, kazanç hatası değil. Sıfır
kalibrasyonu siler. 615 V kanalında bu bizi Vref'e karşı çok bağışık yapıyor.

`Vref = TL431 (2.495 V) → 10K/22K → 1.7153 V`, tamponlanmış. (3.3 V rayından
değil: ray %1 oynasa 16.5 mV ofset olurdu, TL431 çok daha durgun.)

#### 5.12.2 İki gerilim kanalı

| | NORMAL | YÜKSEK |
|---|---|---|
| Bölücü | 2× 100K / 6.8K | **6× 820K / 8.2K** |
| N | 30.41 | 601.00 |
| PGA | ±1.024 | ±1.024 |
| Tam ölçek | **±31.1 V** | **±615.4 V** |
| Adım | 0.950 mV | 18.781 mV |
| Thevenin | 6.58 kΩ | 9.98 kΩ |
| Giriş Z | 0.21 MΩ | **4.93 MΩ** |
| Direnç başına (FS) | 15.1 V (%7.5) | 102.4 V (%51) |

> ⚠️ **5.12.18 bu değeri değiştirdi:** zincir artık 6× **820K** / 8.2K.
> Bölme oranı (N = 601.0), menzil ve adım aynı; aşağıdaki gerekçe geçerli.

**Neden 6 direnç, 4 değil:** araştırma 1/4W metal film azami *çalışma* geriliminin
**200 V** olduğunu gösterdi (Yageo MFR) — geçen turda 250 V varsaymıştım.
4× 1M ile tam ölçek zaten 410 V, 600 V'a yetmiyor.

İki bölücünün Thevenin'i birbirine yakın; ortak-mod penceresi ikisinde de
**0.691 .. 2.739 V** (ADS çalışma aralığı 0..3.3 V). SPICE ±%15 aşırı
gerilimde bile pencerede kaldığını doğruladı.

#### 5.12.3 🔴 Tampon ZORUNLU — 4.14'ün sonucu

Tamponsuz bırakılırsa PGA'ya bağlı kazanç sıçraması oluyor (bkz. 4.14).
Tamponla kaynak empedansı ~0 → hata PGA'dan bağımsız kayboluyor.

**Op-amp seçimi — ADS yolu için MCP6004 sınıfı RRIO (SATIN ALINACAK):**

| op-amp | Vos maks | drift | Ib | Besleme | 615 V kanalında 20 °C hata |
|---|---|---|---|---|---|
| TL072 | 10 mV | 18 µV/°C | 200 pA | ±12 V | %0.0354 |
| LM358 | 7 mV | 7 µV/°C | 45 nA | +5 V | %0.0575 |
| **MCP6004** | 4.5 mV | **2 µV/°C** | **1 pA** | **3.3 V RRIO** | **%0.0039** |

🌟 **RRIO'nun asıl kazancı doğruluk değil, KELEPÇEYİ GEREKSİZ KILMASI.**
Tampon ADS ile aynı 3.3 V rayından beslenirse çıkışı tanım gereği 0–3.3 V
dışına çıkamaz → ADS girişinde kelepçe diyoduna gerek yok → kaçak hatası yok,
kapasite yok, alınacak diyot yok.

Tamponun *kendi* girişi ise bölücünün üst bacağıyla (200K / 6M) korunuyor:
3× aşırı gerilimde bile op-amp ESD akımı **µA mertebesinde**.

TL072 ve LM358 3.3 V'ta bu işi yapamaz (çıkışları raylara yaklaşamaz) —
ikisi de kural olarak eleniyor.

#### 5.12.4 Kelepçe — kavram düzeltmesi + SPICE

Önce bir kavram hatasını düzelttim: **"Vf < 0.3 V olan diyot bul" diye bir
kural yazmıştım. Öyle bir diyot yok.** −0.3 V sınırının amacı TI'nin kendi
ifadesiyle *"to prevent the ESD diodes from turning on"* — yani sınır gerilim
değil, **iç ESD diyodunun iletmesi**. TI'nin çözüm cümlesi de akım üzerine
kurulu: *"...and/or series resistors ... to limit the input current"*.

SPICE (B2), −12 V arıza + 2.7 kΩ seri direnç:

| Harici kelepçe | pin | ESD akımı | ESD payı |
|---|---|---|---|
| yok | −0.734 V | 4.173 mA | %100 |
| **1N4148** | −0.667 V | 1.055 mA | **%25.1** |
| **BAT54** | **−0.258 V** | ~0 | **~%0** |

**4.13 sayısal olarak doğrulandı:** 1N4148 arıza akımının dörtte birini hâlâ
iç ESD diyoduna bırakıyor. BAT54 ile pin −0.258 V'ta kalıyor — **mutlak alt
sınır −0.3 V'un bile üstünde.** (Analitik kestirimim −0.4 V demişti; SPICE
daha iyi çıktı, bağlayıcı olan SPICE.)

⚠️ **Seri direnç 1 kΩ değil 2.7 kΩ.** İlk taslakta 1 kΩ yazmıştım: ±12 V
arızada **11.3 mA** veriyor, ADS'in 10 mA sınırının üstünde. 2.7 kΩ → 4.19 mA.

⚠️ **SR5100 uygun değil** — Vf'i yetersiz *ve* kaçağı (~50 µA) 2.7 kΩ üzerinde
**135 mV** ofset yapıyor. Hassas düğümde kabul edilemez.

**İki farklı koruma rejimi:**
- **ADS yolu (hassas):** 3.3 V RRIO tampon → kelepçe YOK, kaçak YOK
- **ESP yolu (hızlı/skop):** TL072 ±12 V → 2.7 kΩ + 2× BAT54 ŞART

#### 5.12.5 İki ayrı örtüşme süzgeci — 4.8'in çözümü

İlk taslakta tek süzgeç düşünmüştüm; **yanlış.** İki yolun Nyquist'i farklı:

| Yol | Nyquist | Süzgeç | Sonuç |
|---|---|---|---|
| **ADS** (860 SPS) | 430 Hz | 22K + 100nF → **50–56 Hz** | 860 Hz'te **−24 dB** |
| **ESP** (41.7 kSa/s/kanal) | 20.83 kHz | Sallen-Key 6.8K, 2nF/1nF → **16.55 kHz** | 100 kHz'te **−31.3 dB** |

16.5 kHz'lik Sallen-Key, ADS yoluna hiçbir şey yapmaz (430 Hz'in 38 katı uzakta).

SPICE doğrulaması (B2): Sallen-Key f0 = 16.6 kHz, **tepe yok** (Q=0.707),
eğim −40.8 dB/dekat (2 kutup teyit), Nyquist'te −5.50 dB, 100 kHz'te
−31.28 dB — **bugünkü tek kutuplu RC'den 19 dB iyi.**

Sallen-Key zaten bir tampondur → 5.12.3'teki tampon ve bu süzgeç **aynı
op-amp kesiti**, ek parça yok.

ADS yolunda RC **tamponun ÖNÜNDE**: seri direnç ADS'e değil CMOS tampon
girişine bakıyor (Ib ~1 pA), kazanç hatası yaratmıyor. Ardına konsaydı 4.14'ü
geri getirirdi.

#### 5.12.6 Gürültü bütçesi — DEVIR 1.3'ün açık sorusu KAPANDI

Veri sayfası s.8 Şekil 14/15'ten okundu (VDD 3.3 V, 860 SPS):
**±2.048'de ~26.5 µV RMS, ±0.512'de ~8.5 µV RMS.**

| Kanal | ADS gürültü | Kuantalama | Toplam/örnek | 200 ms |
|---|---|---|---|---|
| ±31 V | 0.411 mV | 0.274 mV | 0.494 mV | 0.038 mV |
| ±615 V | 8.113 mV | 5.422 mV | 9.758 mV | 0.744 mV |

⚠️ √N yalnızca beyaz gürültü için geçerli; 1/f ve referans sürüklenmesi bunu
sınırlar. "200 ms'te ~250 000 sayım" bir **üst sınırdır**, garanti değil.

#### 5.12.7 V–I kayması

Araştırma tasarım varsayımını **bağımsız doğruladı** (espressif/esp-idf #1911):
*"two channels sample data with channel 2 out of phase by 1/fs"* — bilinen,
uzun süreli bir davranış. Forumların önerdiği çözüm tam sayı kaydırma; bizim
kayma **tam yarım örnek** olduğu için o yetmez, kesirli gecikme gerekiyor.

`i_hiza[n] = −1/16·i[n−2] + 9/16·i[n−1] + 9/16·i[n] − 1/16·i[n+1]`

Simetrik → doğrusal faz → **faz hatası tam sıfır**. Kalan tek hata genlik
sarkması: 1 kHz'te 0.0001 dB, 5 kHz'te 0.063 dB. CPU 0.17 MMAC/s.

⚠️ **Dürüstlük:** hizalayıcı Nyquist'te sıfıra gidiyor (kesirli gecikme
süzgeçlerinin doğası). Sallen-Key de 20.8 kHz'te −5.45 dB veriyor.
**Güvenilir wattmetre bandı ~5 kHz.**

#### 5.12.8 Akım kanalında negatif

Donanım zaten hazır (ADS #1 AIN0-AIN1 diferansiyel, işaretli okuyor).
`olcum2.h`'deki `if (o.amper < 0.0f) o.amper = 0.0f;` satırı kaldırılacak.
Şönt uçları ±256 mV'ta, −300 mV mutlak sınırına 44 mV kala — alt kelepçe
burada da gerekli.

⚠️ **Enerji sayacı işaretli olmalı.** `enerji_ekle()` şu an negatifi 0 sayıyor;
şarj/deşarj çevriminde sayaç yanlış olur. `uint64` → `int64` pJ.

#### 5.12.9 Montaj kısıtı: DELİKLİ (THT) — ve satın alma

⚠️ **Kullanıcı 2026-09-08'de bildirdi: "yüzey montajda zorlanıyorum, yapamayabilirim."**
SMD gövde artık bir eleme ölçütü. İki yanlış anlama düzeltildi:

| Sanılan | Gerçek |
|---|---|
| MCP6004 SMD | **MCP6004-I/P = DIP-14**, MCP6002-I/P = DIP-8. `/P` son eki PDIP demek |
| BAT54 tek seçenek | **BAT85 = DO-34 eksenel cam**, 1N5711 = DO-35. İkisi de delikli |

**BAT85** (Nexperia veri sayfası, Tablo 7): Vf 400 mV maks @ 10 mA · IR **2 µA
maks @ 25 V** (Şekil 2: ~2 V'ta 25 °C'de tipik ~200 nA) · Cd 10 pF maks.
SPICE'ta BAT54 ile aynı sonucu veriyor: pin −0.268 V, ESD payı ~%0.

##### 🌟 Aslında hiçbir şey almadan da olur — YOL 0

Tamponun **çıkış tavanı** ADS'in mutlak azamisini (3.6 V) zorlamıyorsa kelepçe
diyoduna hiç gerek yok. B2 bunu simüle etti (2.7 kΩ seri direnç ile):

| Tampon | Çıkış | ADS pini | ESD akımı | Kelepçe |
|---|---|---|---|---|
| MCP600x (3.3 V RRIO) | 3.30 V | 3.300 V | **0 nA** | gerekmez |
| **LM358 (+5 V) tavan** | 4.30 V | 3.907 V | **146 µA** | **gerekmez** |
| LM358 (+5 V) en kötü | 5.00 V | 3.935 V | **394 µA** | gerekmez |
| TL072 (±12 V) | 12.0 V | 4.013 V | **2.96 mA** | **ŞART** |

**LM358'in kötü çıkış salınımı burada bir güvenlik özelliğine dönüşüyor:**
+5 V'ta beslendiğinde çıkışı ~4.3 V'un üzerine çıkamıyor, ADS'i zorlayamıyor.
En kötü halde bile 394 µA — 10 mA sınırının 25'te biri.

⚠️ Dürüstlük: o arızada pin 3.9 V'a çıkıyor, yani 3.6 V *gerilim* sınırının
üstüne. Mutlak azami tablosunu belirleyen **akım** ve o çok güvenli; ayrıca bu
ancak giriş menzil dışına çıkarsa oluyor, normal çalışmada çıkış 0.69–2.74 V.

##### Kalibrasyon sonrası hata — seçim doğrulukla ilgili değil

Vos ve Ib·Rt **sabittir**, sıfır kalibrasyonu ikisini de siler. Kalan sadece
sürüklenme:

| Kanal | op-amp | Vos drift | Ib drift | KALAN | FS oranı |
|---|---|---|---|---|---|
| ±31 V | LM358 | 4.26 mV | 2.70 mV | 6.96 mV | **%0.022** |
| ±31 V | MCP6004 | 1.22 mV | ~0 | 1.22 mV | %0.0039 |
| ±615 V | LM358 | 84.1 mV | 81.0 mV | 165 mV | **%0.027** |
| ±615 V | MCP6004 | 24.0 mV | ~0 | 24.0 mV | %0.0039 |

Referans DMM (AN8000) zaten ±%0.5. **LM358'in %0.027'si onun 18'de biri** —
yani seçim doğrulukla değil, pratiklikle ilgili.

LM358'de Ib sürüklenmesi de silinebilir: izleyicinin geri besleme koluna
kaynak Thevenin'ine eşit direnç konursa eşleşen taban akımları sadeleşir,
geriye offset akımı kalır → %0.015.

##### Üç yol

| Yol | Ne | Artı | Eksi |
|---|---|---|---|
| **0** | **LM358 (stokta 8) + 5 V** | Satın alma **yok**, DIP-8, kelepçe **yok** | Ib 45 nA, drift 3.5× |
| 1 | MCP6002-I/P / MCP6004-I/P | En düşük drift, kelepçe yok | Tek kalemlik sipariş |
| 2 | TL072 (yolda) + ±12 V | Skop yolu için zaten gerekli | ADS yolunda kelepçe + ±12 V bağımlılığı |

**Öneri: ADS yolunda YOL 0 ile başla.** Elinde var, bedava, kelepçesiz. DIP-8
sokete tak; tezgahta sürüklenmeyi ölçüp yetmezse MCP6002-I/P'ye geçmek
**devre değişikliği gerektirmiyor** — aynı bacak düzeni, sadece çip değişir.

**Skop/hızlı yol her hâlükârda TL072 + 2.7 kΩ + 2× BAT85** (band 3 MHz
gerekiyor, ±12 V'ta çalışıyor, kelepçe şart).

| Parça | Adet | Zorunlu mu |
|---|---|---|
| BAT85 (veya 1N5711) | 6 | ✅ evet — ama yalnız skop yolu için |
| MCP6002-I/P / MCP6004-I/P | 1–2 | ❌ hayır — LM358 yeterli |
| 1M 1/4W | 12 | ❌ hayır — stokta 30 var |

#### 5.12.10 B3–B5 UYGULANDI (2026-09-08) — ve üç gerçek hata daha buldu

```
cd projeler/olcum-karti/uretim && python dogrula3.py
```

| Adım | Ne | Sonuç |
|---|---|---|
| B1 | Ön uç tasarımı ve hata bütçesi | 53 kural |
| B2 | Analog ön uç, **negatif dahil** (ngspice) | 30 doğrulama |
| B3 | Şema + ERC + **netlist polarite** | ERC **0 ihlal**, 54 doğrulama |
| B4/B5 | Ölçüm matematiği + Lagrange (**AVR emülatörü**) | 48 koşul |

**Dosyalar:** `kod/olcum-karti-a3/olcum3.h` · `uretim/sema3-uret.py` ·
`uretim/netlist3_dogrula.py` · `uretim/test_olcum3.py` ·
`uretim/avr/ornek_olcum3.c` · `sema3/olcum-karti-a3.kicad_sch`

##### 🔴 B4 gerçek bir tasarım hatası yakaladı: MENZİL SİMETRİK DEĞİL

`fark = (Vin − Vref)/N` olduğu için ADS'in ±PGA penceresi girişe **Vref
kadar yukarı kaymış** bir aralık verir:

```
Vin_üst = +pga·N + Vref
Vin_alt = −pga·N + Vref
```

İlk tasarım "tam ölçek = pga·N" diyordu ve bu **yanlıştı**. NORMAL kanal
2×100K/6.8K (N=30.41) ile gerçekte **−29.43 .. +32.86 V** idi; AVR testi
−31 V'ta **−29.43 V** okuyup kırpmayı gösterdi.

**Düzeltme:** bölücü **220K / 6.8K** (N=33.35, tek direnç). Garanti
simetrik menzil **±32.44 V**, adım 1.042 mV. HV kanalında asimetri
zaten %0.28 (613.71 / 617.14 V) — ihmal edilebilir.

##### 🔴 B4 ikinci hata: kalibrasyonlar birbirini bozuyordu

Ofset **volt** olarak saklanıyordu ve sıfır kalibrasyonu `ofset −= okunan`
yapıyordu. Bu ofseti *o anki kazanca* bağlar; sonra kazanç kalibrasyonu
yapılınca ofset eski kazanca göre kalır. Test yakaladı: 12 V'ta kalibre
edip **−24 V'ta 175 mV hata**. Ayrıca "sıfıra yakın girişte kazanç
kalibrasyonunu reddet" koruması da hiç tetiklenmiyordu.

**Düzeltme:** ofset artık **ham kod** olarak saklanıyor (`sifir_ham`).
Sıfır tanım gereği doğru ve kazançtan bağımsız; ikisi tam ayrışıyor.

##### 🔴 B3 üçüncü hata: çakışan referanslar netlist'i BOŞALTIYORDU

Direnç zinciri üreteci `"R2"` önekiyle R21…R26 üretiyordu ve bunlar
skop/I2C dirençleriyle çakışıyordu. KiCad çakışan referansta *"annotation
errors"* deyip netlist'i boş üretiyor — **ERC bunu görmüyor.** Üreteç artık
açık başlangıç numarası alıyor.

##### 🌟 B5: Lagrange hizalayıcı — gerçek kodda ölçüldü

Gerçek `olcum3.h` kodu, avr-gcc ile derlenip bit-birebir doğrulanmış AVR
emülatöründe koşturuldu. Tam sayıda periyot kullanıldı, beklenen değer
analitik olarak `0.5·cos(φ)`:

| Frekans | PF | Düzeltmesiz | **Hizalı** | İyileşme |
|---|---|---|---|---|
| 52 Hz | 0.1 | +3.91% | **+0.000%** | — |
| 1.04 kHz | 0.5 | +13.28% | **−0.001%** | 9 853× |
| 1.04 kHz | 0.1 | **+77.76%** | **−0.001%** | **111 965×** |
| 5.21 kHz | 0.5 | +58.67% | −0.847% | 69× |
| 5.21 kHz | 0.1 | **+373.15%** | −0.854% | 437× |

Tasarımın öngördüğü şey gerçek kodda doğrulandı. 5 kHz'teki %0.85, hem
hizalayıcının genlik sarkması hem Sallen-Key'in −0.14 dB'i — **güvenilir
wattmetre bandı ~5 kHz** ifadesi bu ölçümden geliyor.

##### Ayrıca doğrulanan (B4)

- İşaretli enerji: 1000×(+2 W) sonra 1000×(−2 W) → **net tam 0 J**
  (Aşama 2'de 40 J olurdu, çünkü negatifi 0 sayıyordu)
- int64 taşma: 7000 W × 1 s = 7000 J ✓ (Aşama 2'nin uint32'si 2.147e9 µW'ta taşardı)
- Akım kırpması gerçekten kalktı: −2.34 A okunuyor, simetrik
- `olc3()` birleşik yol: 12 V × −1.5 A = **−18 W** (negatif güç temsil edilebiliyor)

##### Şema — B3

7 blok, 88 parça, A2 kağıt. ERC **0 ihlal**. Netlist denetimi ERC'nin
göremediklerini okuyor: bölücü altlarının GND'ye **değil** VREF'e gittiği,
iki diferansiyel çift, kelepçe polaritesi, TL431 yönü, ADS adresleri
(0x48/0x49), Sallen-Key topolojisi (C1 çıkışa, C2 GND'ye), boş op-amp
kesitlerinin izleyici bağlanması.

#### 5.12.11 B6 UYGULANDI (2026-09-08) — firmware çalışır durumda

```
cd projeler/olcum-karti/uretim && python dogrula3.py     # ~2.5 dk
```

| Adım | Ne | Sonuç |
|---|---|---|
| B1 | Ön uç tasarımı ve hata bütçesi | 53 kural |
| B2 | Analog ön uç, **negatif dahil** (ngspice) | 30 doğrulama |
| B3 | Şema + ERC + netlist polarite | ERC **0 ihlal**, 54 doğrulama |
| B4/B5 | Ölçüm matematiği + Lagrange (**AVR emülatörü**) | 48 koşul |
| **B6** | **Firmware: derleme + ikilide ölü kod** | **37 koşul** (+7 ayrışma) |

**Firmware:** `kod/olcum-karti-a3/olcum-karti-a3.ino` (957 satır) +
`olcum3.h` + `tipler3.h` + `skop_olc.h`
→ **480 439 B flash (%15 / 3 MB), 47 532 B RAM (%14), 0 uyarı.**

##### Seri protokol — arayüzün dayanacağı sözleşme

```
D <volt> <amper> <watt> <joule> <wh> <ms> <örnek> <menzil>
S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
```

`<menzil>`: 0 = NORMAL (±32.4 V), 1 = YÜKSEK (±613.7 V). **Aşama 2'de
olmayan alan** — arayüz hangi kanalın etkin olduğunu bilmeli.

| Komut | İş |
|---|---|
| `z` / `g<volt>` | gerilim sıfır / kazanç kalibrasyonu (**etkin kanala**) |
| `n` / `y` | menzili elle NORMAL / YÜKSEK yap (oto kapanır) |
| `a<0\|1>` | otomatik menzil |
| `Z` / `i<amper>` | akım sıfırı / kazanç |
| `s<ohm>` | şönt değeri · `e` enerji sıfırla · `?` ayarlar · `#` I2C tara |
| `t…` | osiloskop (Aşama 2 ile aynı) |

⚠️ Aşama 2'de arayüz ile firmware komutları **ayrışmıştı** (4.1: `app.js`
`kv12.34` gönderiyor, firmware `v12.34` bekliyordu). B6 artık ikilide her
komut dalının varlığını sınıyor, ve `?` çıktısı komutları listeliyor.

##### Otomatik menzil — PGA değil KANAL değiştiriyor

PGA oto-kademesi **bilerek yapılmadı**: ADS'in giriş empedansı PGA ile
değiştiği için kademe sınırında %0.67 puan kazanç sıçraması oluyor
(4.14). Kanal değiştirmek aynı sorunu yaratmıyor çünkü **her kanalın
kendi kalibrasyonu var**. Histerezis: NORMAL FS'in %90'ında yukarı,
%70'ine düşünce aşağı.

##### B6'nın yakaladıkları

🔴 **Arduino otomatik prototip tuzağı — Aşama 1'in #5 hatası tekrarlandı.**
`varsayilan_ayar3(Ayar3 *a)`'nın prototipi struct tanımından **önce**
yerleşiyor:
```
error: variable or field 'varsayilan_ayar3' declared void
error: 'Ayar3' was not declared in this scope
```
Çözüm de aynı: tipler `tipler3.h`'ye taşındı (Aşama 1'de `tipler.h` idi).

🔴 **Kopyalanan dilim fazla şey almış.** Osiloskop bölümünü A2'den
alırken sınırı "// ── HTTP" başlığına koymuştum; araya `enerji_biriktir`
de girdi ve o Aşama 2'nin **uint64** `enerji_ekle`sini çağırıyordu.
İşaretli sürümü yeniden yazıldı — A2'nin iki koruması (taşma sarmalı,
>1 s aralığı atlama) korunarak.

##### Osiloskop matematiği — ayrışma koruması

`SkopOlcum` / `skop_kesisim` / `skop_olc` hem `olcum2.h`'de hem
`skop_olc.h`'de duruyor. Kopya olmak tehlikeli değil, **sessizce
ayrışmak** tehlikeli:

- `uretim/skop_olc_uret.py` kopyayı **olcum2.h'den üretir**
- `uretim/test_skop_ayni.py` iki metni **karakter karakter** karşılaştırır

Böylece A6'nın (gerçek kodda doğrulanmış) kanıtı Aşama 3 için de geçerli.

⚠️ **Osiloskop SÜRÜCÜSÜ için böyle bir denetim YOK** — 339 satır A2'den
kopyalandı ve A2 değişirse sessizce eskir. Bilerek kabul edildi (A2 artık
regresyon temeli; sürücü zaten PSRAM'li derin bellek için değişecek),
`.ino` başlığında açıkça yazıyor.

#### 5.12.12 B7 UYGULANDI (2026-09-08) — arayüz çift yönlü

**Dizin:** `arayuz3/` — `index.html` · `app.js` · `sahte-kart.js` ·
`ek.css` · `sunucu.py`

```
cd projeler/olcum-karti/arayuz3 && python sunucu.py     # :8772
```

##### Neden ayrı dizin

Aşama 2'nin arayüzü o firmware'in protokolüyle konuşuyor ve **A5 bunu
komut biçiminden sınıyor** (`gonderilen[1] === 'v12.05'`). Aynı dosyayı
iki protokole birden uydurmaya çalışmak, 4.1'deki sessiz ayrışmanın
daveti olurdu.

**Ortak dosyalar kopyalanmadı:** `vendor/vue.global.prod.js` (154 KB) ve
`style.css` `../arayuz`'da duruyor; `arayuz3/sunucu.py` bulunmayan dosyayı
oraya düşürüyor (`translate_path`). Tek kopya kalıyor.

##### Ne değişti

| | Aşama 2 | Aşama 3 |
|---|---|---|
| D satırı | 8 alan | **9 alan** — `<menzil>` eklendi |
| Gerilim kalibresi | `v<volt>` | **`g<volt>`** |
| Gerilim sıfırı | yok | **`z`** |
| Akım sıfırı | `z` | **`Z`** ⚠️ harf anlamı değişti |
| Menzil | yok | `n` / `y` / `a<0\|1>` |
| Kalibrasyon işareti | `> 0` şartı | **negatif de kabul** |
| Güç yönü | gösterilemezdi | **"yük çekiyor" / "kaynak — geri besleme"** |

Menzil rozeti gerilim ölçümünün yanında duruyor; çözünürlük iki kanalda
18 kat farklı olduğu için hangisinin okunduğu görünür olmalı.

##### 🌟 B7'nin asıl işi: arayüz ↔ firmware komut denetimi

`test_arayuz3.js` arayüzün gönderebileceği **her** komut harfini,
`.ino`'dan okunan `case` etiketleriyle karşılaştırıyor — hem `app.js`
hem `index.html`. Bu, 4.1 ve 4.15'in tekrarlanmasını imkânsız kılıyor.

Demo kart (`sahte-kart.js`) da gerçek firmware gibi davranıyor:
bilinmeyen komutu reddediyor, sıfıra yakın kazanç kalibrasyonunu
reddediyor. Yani demo kipinde görünen davranış gerçek kartınkiyle aynı.

**B7: 54/54.**

#### 5.12.13 B8 UYGULANDI (2026-09-08) — hızlı yol devrede

Lagrange hizalayıcı artık **gerçekten çağrılıyor**. B4–B7 boyunca kodda
duruyordu ama kullanılmıyordu (`__attribute__((unused))` ile işaretliydi);
B8 onu tam güç hesabına bağladı.

##### 🔴 DEVIR 5.1.4'ün kazanç önerisi elendi

DEVIR fark yükselteci için **kazanç 27** (27K/1K) öneriyordu. `tasarim3.py`
§10 bunu kuralla eledi:

| Rf/Rg | G | Tam ölçek şönt | ADS 256 mV | Bant |
|---|---|---|---|---|
| 27K/1K | 27 | **51.3 mV** | ❌ **KIRPAR** | 107 kHz |
| **47K/10K** | **4.7** | **294.6 mV** | ✅ kapsar | 526 kHz |

G=27 ile hızlı yol yavaş yoldan **5 kat önce** doyuyordu: 0.1R şöntte hızlı
yol ±0.51 A'de kırparken ADS ±2.56 A okuyor. O tasarım 0.1R şöntü ve 1 A
hedefini varsayıyordu; **şönt soketli olduğu için bu varsayım tutmuyor.**

Ayrıca REF ucu ayrı bir 1.5 V rayına değil, **zaten tamponlu VREF'e**
bağlandı — ikinci bir referans hem parça hem ikinci bir sürüklenme kaynağı.

##### 🌟 B8'in ölçtüğü gerçek güç — hizalayıcının etkisi

`guc_olc()` gerçek kodu AVR emülatöründe, analitik sinüslere karşı:

| PF | Beklenen P | **Hizalı** | Hizalamasız |
|---|---|---|---|
| 1.0 | 2.50000 | 2.49996 (**−0.001%**) | 2.49229 (−0.308%) |
| 0.5 | 1.25000 | 1.24998 (**−0.001%**) | 1.41602 (**+13.28%**) |
| 0.1 | 0.25000 | 0.25000 (**−0.001%**) | 0.44439 (**+77.76%**) |

Ayrıca doğrulandı: Vrms/Irms/S tam, DC yükte PF=1, **ters akımda P=−3 W ve
PF=−1** (geri besleme işaretleniyor), 8 örnekten kısa pencerede ölçüm
yapılmıyor.

##### 🔴 B8 kendi testimde bir hata buldu — ve o hata GERÇEK

İlk koşuda üç durumun da **+%2.48** sapması vardı. PF=1'de de görüldüğü
için faz değil: **pencere** sorunu. Hizalayıcı kenarlardan 3 örnek
düşürünce 120 örnekten 117 kalıyor — o da **2.925 periyot**, tam sayı değil.

Test düzeltildi (N=123 → kullanılan 120 = tam 3 periyot) ve hata
%0.001'e indi. **Ama bu gerçek kartta da olacak:** edinim penceresi
sinyalin periyoduna hizalı olmayacak. Yanlılık ölçüldü ve kural yapıldı:

```
2.75 periyot -> %2.64        K = 2.64 x 2.75 = 7.25
yanlilik ~ K / cevrim sayisi
```

| Sinyal | 200 ms pencere | Yanlılık |
|---|---|---|
| 50 Hz | 10 çevrim | **%0.73** |
| 1 kHz | 200 çevrim | %0.04 |

**%0.73, ADS yolunun kalibrasyon sonrası hatasından (%0.03) 24 kat büyük.**
Bu yüzden hızlı yolun sayısı **güç faktörü ve dalga şekli** için; mutlak
watt değeri ADS'ten geliyor. Firmware pencere uzunluğunu ve 50 Hz'teki
çevrim sayısını her ölçümde **yazdırıyor** — susmak yerine söylüyor.

##### Donanım — BLOK 8

```
SONT_P --[10K]--+-- U8A(+)        U8A: TL072 fark yukselteci, G = 4.7
                +--[47K]-- VREF   (REF ucu VREF'te -> cift yonlu)
SONT_N --[10K]--+-- U8A(-)
                +--[47K]-- cikis
cikis -> U5B Sallen-Key 16.55 kHz -> 2.7K -> 2x BAT85 -> GPIO5
```

- **U5B artık boşta değil** — Aşama 3'e kadar izleyici bağlıydı, şimdi
  hızlı akım Sallen-Key'i. Boş kesit yeni TL072'nin (U8B) kesiti oldu.
- Şönt Kelvin uçları **iki yere** gidiyor: ADS'in RC'sine ve fark
  yükseltecine. Hızlı yol RC'nin ardından çekilseydi 7.96 kHz'e hapsolurdu.
- **Netlist denetimi bir hatamı yakaladı:** GPIO5'i eklerken 8 pinlik
  başlıkta `+5V`'un yerini almıştım — LM358'lerin beslemesi kayboluyordu.
  Başlık 10 pine çıkarıldı.

##### Firmware ve arayüz

`w` komutu bir pencere yakalayıp `W` satırı üretiyor:

```
W <P> <S> <PF> <Vrms> <Irms> <Vort> <Iort> <n> <P_hizalamasiz>
```

Son alan **bilerek** var: arayüz hizalamanın ne kadar düzelttiğini
gösteriyor ("hizalama −13.40% düzeltti" / "fark yok (dirençsel)").

⚠️ Kanal sırası **indeks paritesinden çıkarılmıyor**, her zaman
`type2.channel` alanından demux ediliyor — DMA bir çerçeve düşürürse
parite kayar ve V ile I yer değiştirir.

Firmware: **481 935 B flash (%15), 50 972 B RAM (%15), 0 uyarı.**

#### 5.12.14 B9 UYGULANDI (2026-09-08) — malzeme denetimi + tezgah kılavuzu

**B9 olarak ne yapıldığı önemli:** sırada B9 (ikili aktarım) ve B12
(sürekli hızlı yol) vardı; ikisi de seçilmedi. Gerekçe:

- **İkili aktarım / yerel USB CDC**, `Serial`'in nasıl çalıştığını
  değiştiriyor. Kartla konuşulacak **tek kanal** o. Donanım elde yokken
  değiştirmek, yanlışsa kullanıcıyı kartla hiç konuşamaz halde bırakır.
- **Sürekli hızlı yol**, osiloskopla **aynı ADC tutamağını** paylaşıyor;
  sürekli çalışırsa skop çalışamaz. Ayrıca `D` satırı zaten 5 Hz'te
  sürekli güç veriyor; hızlı yolun katkısı PF ve reaktif yük doğruluğu.

Asıl eksik başkaydı: **Aşama 3'ün tezgah kurulum kılavuzu yoktu.**
Aşama 1'in `kurulum.html`'i, Aşama 2'nin `kurulum2.html`'i vardı;
kullanıcı Aşama 3'ü kuracak ve elinde adım adım bir şey yoktu.

##### Malzeme listesi envanterle denetleniyor — `bom_dogrula.py`

Liste **şemadan** üretiliyor (netlist3.net), elle yazılmıyor. Şema
değişince liste peşinden gidiyor.

**55 bileşen, 25 farklı değer.** Sonuç:

| Durum | Parçalar |
|---|---|
| Stokta yeterli | 1M ×6, 6.8K ×6, 100nF ×4, 10K ×4, 2.7K ×4, 22K ×3, 100R ×2, 1nF ×6, 47K ×2, LM358 ×2, 100K, 220K, 220R, TL431 |
| Yolda | TL072 ×2, ADS1115 ×2, ESP32-S3, şönt seti, jaklar |
| **Satın alınacak** | **BAT85 ×4** (tek kalem) |

⚠️ **Uyarı: 10K'nın 1/4W'ı tükenmiş** (R019: 0 adet). R032 (1/2W ×10) ve
R033 (1W ×10) var; tasarımdaki dört 10K de düşük güçte, sorun yok.

CLAUDE.md kuralı korunuyor: direnç adetleri göz kararı sayım ve kayıt dışı
bir yığın var, o yüzden "yetersiz" = **"saydır"** demek, "kesin yok" değil.

##### Tezgah kılavuzu — `kurulum3.html` (üretiliyor)

`kurulum3-uret.py` sayfayı `tasarim3_sabit.py`'den üretiyor. Aşama 2'nin
`kurulum2.html`'i **elle yazılmıştı** ve içindeki 4.7K pull-up önerisi
tasarımla ayrışmıştı (4.7); aynı hatayı tekrarlamamak için bu üretiliyor.

Yedi adım, her birinde geçilmeden ilerlenmeyen bir **ölçüm kapısı**:

| # | Adım | Kapı |
|---|---|---|
| 01 | Vref rayı | TL431 2.495 V, Vref 1.7153 V — **yük altında da** aynı |
| 02 | ESP32 + I²C | `#` → 0x48 **ve** 0x49 görünmeli |
| 03 | Akım + Kelvin | `Z` sıfırla, akımı **ters çevir** → negatif okumalı |
| 04 | NORMAL ±32 V | `z` sonra `g`; girişi ters çevir, simetrik olmalı |
| 05 | **YÜKSEK ±613 V** | 🔴 **önce 12 V**, sonra 100 V, kademeli |
| 06 | Osiloskop | `ta` → frekans/duty doğru; düz çizgide ölçüm **yapılamamalı** |
| 07 | Hızlı yol | Dirençsel yükte PF≈1 ve "fark yok"; reaktif yükte düzeltme görünmeli |

Ayrıca 8 satırlık sorun giderme tablosu (I²C görünmüyor, negatif 0 okunuyor,
PSRAM yok, menzil gidip geliyor…).

#### 5.12.15 🛒 SATIN ALMA LİSTESİ — Aşama 3 (2026-09-08)

Kullanıcı "BAT85 dışında ne lazım olabilir" diye sordu. Geniş bakıldığında
**BAT85 tek başına yetmiyor** — iki gerçek eksik daha çıktı.

##### 🔴 A. ZORUNLU — bunlar olmadan kart ya kurulamaz ya anlamsız ölçer

| Parça | Adet | Neden |
|---|---|---|
| **BAT85** (veya 1N5711 / BAT43) | 6 | Kelepçe. 1N4148 arıza akımının %25'ini ADS'in iç ESD diyoduna bırakıyor (B2 ölçtü) |
| **Metal film %1, ≤100 ppm/°C direnç** | aşağıda | HV bölücünün **asıl sınırı** — bkz. B1 §11 |
| **DIP-8 IC soketi** | 6 | Şemada 4 DIP-8 gövde (LM358 ×2, TL072 ×2) + 2 yedek. Tedarikçide "8 pin dip soket" / "entegre soketi" adıyla, **direnç kategorisinde değil**. Envanterde soket kaydı YOK. Zorunlu değil |

**Metal film direnç seti** (karbon film **olmaz**, gerekçe aşağıda):

| Değer | Adet | Nerede |
|---|---|---|
| ~~1M **1/4W**~~ → **820K 1/4W** (+ **8.2K ×5**) | 8 | HV zinciri (6) + yedek. ⚠️ **5.12.18'de değişti** — tedarikçinin metal film hattı 820K'da bitiyor. N = 601 aynı kaldı |
| 10K | 10 | HV alt bacak, Vref, fark yükselteci |
| 220K | 5 | NORMAL üst bacak |
| 6.8K | 10 | NORMAL alt + Sallen-Key (4) |
| 22K | 5 | Vref alt + RC süzgeç (2) |
| 47K | 10 | Fark yükselteci (2) |
| 2.7K | 10 | I²C pull-up (2) + kelepçe seri (2) |
| 100K · 100R · 220R | 5'er | Skop bölücü, akım RC, TL431 |

##### Neden metal film — B1 §11'in hesabı

601:1'lik bir bölücüde direncin **tipi**, değerinden daha belirleyici.
20 °C oda salınımı ve direnç başına 102 V ile:

| Tip | TCR hatası | VCR hatası | 1000 h sürüklenme | **TOPLAM** |
|---|---|---|---|---|
| **Karbon film** | %2.00 | %0.10 | %2.00 | **%4.10** |
| Metal film %1 (100 ppm) | %0.40 | %0.01 | %0.30 | %0.71 |
| Metal film %1 (50 ppm) | %0.20 | %0.01 | %0.20 | **%0.41** |

Kıyas: ADS kalibrasyon sonrası **%0.03**, MCP6004 tamponu **%0.004**,
referans DMM **%0.5**.

**Karbon film, tasarımın geri kalanını anlamsız kılıyor** — 137 kat kötü,
referans multimetrenin bile üstünde.

İki kalem kalibrasyonla **silinemez**:
- **VCR** gerilime bağlı, yani doğrusal değil. 12 V'ta kalibre edip 600 V
  ölçersen hata geri gelir.
- **1000 saatlik sürüklenme** karbon filmde %1–3. Günde 3 saat kullanımda
  ~11 ay, ama sürüklenme ilk haftalarda daha hızlı. Yani **kalibrasyon
  haftalar içinde bayatlar ve sayı hâlâ inandırıcı görünür.**

⚠️ `envanter.csv`'de **film türü alanı yok**; eldekilerin karbon mu metal
film mi olduğu bilinmiyor. Tezgahta ayırt etme: metal film genelde
mavi/yeşil gövde ve 5 halka (%1); karbon film bej ve 4 halka (%5).

##### Kaç watt? — belirleyici olan güç değil, GERİLİM

Kullanıcı sordu (2026-09-08). B1 §12 her pozisyonu tek tek hesapladı:

| | En yüksek |
|---|---|
| **Güç** | 1/4W'ın **%20**'si (R26/R33, kelepçe seri direnci, TL072 arıza anında 50 mW) |
| **Gerilim** | 1/4W'ın **%51**'i (HV zinciri, direnç başına 102 V) |

**Güç hiçbir yerde sorun değil.** Metal filmde asıl sınır azami *çalışma
gerilimi*: 1/4W = 200 V, 1/2W = 250 V, 1W = 350 V.

| Pozisyon | Gerilim | Güç | Gövde |
|---|---|---|---|
| **1M ×6 (HV zinciri)** | **102 V** | 10 mW | **1/2W** önerilir |
| 100K (skop üst) | 45.6 V | 21 mW | 1/4W |
| 220K (NORMAL üst) | 31.5 V | 4.5 mW | 1/4W |
| 2.7K (kelepçe seri) | 11.6 V | **50 mW** | 1/4W |
| Diğer hepsi | < 3.3 V | < 5 mW | 1/4W |

**HV zincirinde neden 1/2W:** 1/4W teknik olarak yetiyor (sınırın %51'i),
ama 1/2W iki şey kazandırıyor:

1. Gerilim payı %49 → **%59**; yanlışlıkla 1200 V uygulanırsa 1/4W aşar, 1/2W aşmaz
2. **Gövde 3.2 mm → 6.5 mm.** Delikli plakette 615 V'ta kaçak yolu
   (creepage) uzuyor — direncin kendi iki ucu arasında 102 V var ve
   **gövde uzunluğu doğrudan o mesafedir**

⚠️ **2W ve üstü ALMA:** gövde büyüdükçe parazitik kapasite artıyor ve skop
kanalının bandını kesiyor; ayrıca delikli plakette yer sorunu.

**Sipariş:** 1M → **1/2W**, diğer hepsi → **1/4W**. Tek gövde istenirse
hepsi 1/2W de olur; fark küçük, sadece yer kaplar.

##### Yalnızca 1/4W bulunabiliyorsa — sorun yok (2026-09-08)

Kullanıcı sordu. **Cevap: 1/4W yeterli, 6 dirençle tasarım olduğu gibi kurulur.**

> ⚠️ Bu bölümdeki tablolar 1M üzerinden yazıldı; 5.12.18'de değer 820K
> oldu ve alt bacak 10K → 8.2K. **Sayılar aynı kaldı** (N, menzil, adım,
> direnç başına gerilim) — yalnızca değer etiketleri değişti.

⚠️ **Bir vurgu düzeltmesi:** yukarıda 1/2W'ı gövde boyu (3.2 → 6.5 mm) ve
"kaçak yolu" gerekçesiyle öne çıkarmıştım. **Bu abartıydı.** Üreticinin
200 V'luk değeri zaten gövdenin uçtan uca dayanımıdır; 102 V'ta direnç
kendi spec'i içinde. Kaçak yolu asıl **plaket yerleşiminin** işi (delik
atlama), direncin gövdesinin değil. 1/2W'ın tek gerçek katkısı gerilim payı.

| Zincir | Alt bacak | Tam ölçek | Adım | 615 V'ta/direnç | Sınırın | Tavan |
|---|---|---|---|---|---|---|
| **6× 1M** | 10K | 613.7 V | 18.78 mV | **102.3 V** | **%51** | 1200 V |
| 8× 1M | 10K+3.3K | 615.2 V | 18.83 mV | 76.7 V | %38 | 1600 V |
| 10× 1M | 10K+6.8K | 608.8 V | 18.63 mV | 61.4 V | %31 | 2000 V |

*Tavan = direncin kendi 200 V sınırına ulaşan giriş gerilimi.*

**6× 1M zaten geçiyor** (%51, kuralın %60 eşiğinin altında) ve direnç
sınırı ancak **1200 V** girişte aşılıyor — tasarımın tam ölçeği 615 V.

8× 1M seçeneği **aynı menzili ve aynı adımı** veriyor, sadece payı
%51 → %38 çıkarıyor. Bedeli iki fazladan 1M ve alt bacakta 10K+3.3K seri
çift. İstenirse, ama gerekli değil.

**Sipariş tek gövdeye indi: her yerde 1/4W metal film.**

##### 🟡 B. ÖNERİLEN — ucuz, işi belirgin iyileştiriyor

| Parça | Adet | Neden |
|---|---|---|
| ~~MCP6002-I/P~~ | ~~4~~ | ❌ **LİSTEDEN ÇIKARILDI** — bkz. aşağıdaki not |
| **Yedek ESP32-S3** | 1 | 615 V ile çalışılacak ve elde **tek** kart var. Ölürse proje durur |
| Tek damarlı montaj teli (0.5 mm, 3-4 renk) | — | Nokta-nokta + Kelvin uçları |
| **Silikon test kablosu / HV prob** | 1 çift | 600 V için jumper kablo **kullanılmaz** |

##### ❌ MCP6002 listeden ÇIKARILDI (2026-09-08)

Kullanıcı sordu: "MCP6002'nin muadili yok mu, aldığım yerlerde sadece SMD var."

Soru hesabı yeniden yaptırdı ve **cevap şu: artık gerek yok.** Bölüm 4'te
MCP6002'yi LM358'e tercih etmiştim (sürüklenme %0.004 vs %0.027) — ama o
karşılaştırma **bölücüyü hesaba katmıyordu.** Metal film kararından sonra
bölücü %0.41 ile en büyük kalem oldu ve op-amp farkı gömüldü:

| Bölücü | Op-amp | **Toplam (kök-kare)** |
|---|---|---|
| Metal film 50 ppm | **LM358** | **%0.4122** |
| Metal film 50 ppm | MCP6002 | %0.4114 |
| Karbon film | LM358 | %4.1026 |
| Karbon film | MCP6002 | %4.1025 |

MCP6002'nin kazancı: **bağıl %0.21 iyileşme.** Ölçülemez.

Dikkat çekici olan alt iki satır: **karbon filmle op-amp seçimi hiçbir şey
değiştirmiyor** (%4.1026 vs %4.1025). Yani doğru sıra: önce dirençleri
düzelt, op-amp zaten sorun değil.

**LM358 (stokta 8, DIP-8, +5 V) yeterli** — toplam %0.412, referans
multimetrenin %0.5'inin altında.

DIP muadili yine de aranırsa (RRIO, 3.3 V, DIP-8): `LMC6482IN`,
`TLV2370IP`, `OPA2350PA`, `TS912IN`. Hepsi var ama **hiçbiri gerekli değil.**

##### 🟢 C. YOL HARİTASI — sonra lazım, şimdi alınırsa ikinci kargo yok

DEVIR 5.8'den, hâlâ geçerli:

| Parça | Adet | Ne için |
|---|---|---|
| **LM319N** | 2 | Doyum testi. **Envanterde komparatör YOK** |
| 10K NTC B3950 | 2 | Elektronik yük termal koruma |
| KSD9700 70 °C NC | 1 | Donanım ısı kesici |
| **1N4148** | 20 | ⚠️ **Ölçüm kartında KULLANILMIYOR** — oradaki kelepçelerin hepsi BAT85 (4.13/5.12.4). Bu kalem *elektronik yük* projesinin donanım watchdog'u ve kelepçeleri için; o devre henüz tasarlanmadı, 20 sayısı hesap değil tahmin. Stokta 8 var |
| Mika yalıtkan + montaj seti | 5 | MOSFET–soğutucu |
| 🔭 **ALINX AN108** (AD9280 32 Msps ADC + AD9708 DAC) | 1 | **Hızlı skop (B14) + sinyal üreteci.** ~22–49 USD. **Önce 5.12.20'deki bedava adım 1 denenecek**, ondan önce alınmaz. AD9226 modülü de olur ama AN108 8 bit + BNC + DAC ile daha uygun |

##### ✅ ALMAYA GEREK OLMAYANLAR

| Parça | Neden |
|---|---|
| **±12 V için ek parça** | 7812 ×3, 7912 ×2, 7805 ×3 stokta. NE555 (yolda ×10) + SR5100 (stokta ×10) şarj pompası da yeterli — ±12 V rayı yalnızca ~6 mA çekiyor (4 TL072 kesiti) |
| Ayırma kondansatörü | 100nF stokta 51 adet; 7 tane gerekiyor |
| Muz jak / klemens | Siparişte 10 muz + 10 born jak var, 4 giriş çifti için fazlasıyla yeter |
| Soğutucu | `MEK002` var — ama **ölçüsü hâlâ bilinmiyor** (açık soru #2) |
| **ESP32-CAM / OV2640 kamera kartı** | ⚠️ Kullanıcı "LCD_CAM" adından dolayı bunun gerektiğini sandı. **Gerekmiyor:** LCD_CAM, S3 çipinin **içindeki** paralel veri bloğu — ayrı bir kart değil, kamerayla ilgisi yok |
| **Çıplak AD9226 yongası** | LQFP-48, yani **SMD**. Çakır Elektronik satıyor ama alma — modül al, o lehimli geliyor |

##### ✅ O günün açık sorusu kapandı

**"Kaç adet 12 V adaptörün var?"** — 2026-09-09'da cevaplandı: hiç yok.
Çözüm 24 V kaynak + LM358 orta nokta tamponu; ayrıntı **5.12.23**'te.
İkisi seri bağlanınca ±12 V'u regülatörsüz veriyor; bir tanesi varsa
−12 V'u NE555 pompasıyla üretmek gerekiyor. İkisi de yoksa **bir adet
12 V adaptör** listeye eklenmeli.

#### 5.12.16 🔴 Ayırma kondansatörleri EKSİKTİ — düzeltildi (2026-09-08)

Bu soruyu incelerken çıktı: şemada **hiçbir besleme rayında ayırma
kondansatörü yoktu.** Dört op-amp (U3, U4 +5 V'ta; U5, U8 ±12 V'ta),
sıfır yerel bypass.

Netlist denetimi gösterdi:
```
+5V    3 uc, kondansator: YOK
+12V   2 uc, kondansator: YOK
-12V   2 uc, kondansator: YOK
```

**Neden önemli:** op-amp çıkışı kapasitif yük sürüyor (Sallen-Key'in
C'leri) ve besleme empedansı yüksekse bu salınıma dönüşebilir. TL072'nin
slew hızı 13 V/µs; ani akım talebini yerel kondansatör karşılamalı,
20 cm'lik besleme teli değil.

**Düzeltildi:** C9–C15, 7 adet 100nF (U3, U4, U5 ±, U8 ±, ADS rayı).
Hepsi stoktan. Netlist denetimine altı kural eklendi — bir daha
eksik kalamaz.

#### 5.12.18 🔧 HV bölücü 1M → 820K — karar kaçak akımına dayandı (2026-09-09)

Üç turda oturdu:

1. *"Ellerinde 1 M yokmuş"* → 6× 2.2M / 22K seçildi, zincir yeşile döndü.
2. Kullanıcı metal film listesinin **kΩ sayfasını** yapıştırdı; hat 820K'da
   bitiyor görünüyordu. "MΩ'lar karbon film olmalı" diye 6× 820K / 8.2K'ya
   geçildi — **bu gerekçe yanlıştı.**
3. Kullanıcı düzeltti: **2.2M ve 6.8M da metal film.** Yani seçim zorunluluk
   değil, tercih. Yeniden, doğru gerekçeyle karara bağlandı.

**Anahtar gözlem:** alt bacak zincirin yüzde biri olduğu sürece
`6R / (R/100) = 600`, yani **hangi R olursa olsun N = 601.0 tam.** 820K, 2.2M
ve 6.8M üçü de aynı menzili, aynı adımı, aynı direnç gerilimini (102.3 V, %51)
ve aynı `ORAN_YUKSEK = 601.0f`'i verir.

**Ayıran tek şey yüzey kaçağı.** Delikli plakette zincire paralel oluşan bir
kaçak yolu bölme oranını aşağı çeker ve hata **doğrudan zincir direnciyle
orantılıdır** (`bağıl hata ≈ Rust / R_kaçak`):

| zincir | Rust | giriş Z | 1 GΩ kaçakta | 10 GΩ | 100 GΩ |
|---|---|---|---|---|---|
| **6× 820K** | **4.92 MΩ** | 4.93 MΩ | %0.492 | **%0.049** | %0.005 |
| 6× 2.2M | 13.20 MΩ | 13.22 MΩ | %1.320 | %0.132 | %0.013 |
| 6× 6.8M | 40.80 MΩ | 40.87 MΩ | %4.080 | %0.408 | %0.041 |

Kaçak **kalibrasyonla silinmez** — nemle günden güne değişir. Karbon filmi
eleyen gerekçenin birebir aynısı.

**2.2M'in karşı kozu giriş empedansı** (13.22 MΩ ↔ 4.93 MΩ; 615 V'ta 47 µA ↔
125 µA). Ama bu kanalın ölçeceği şeyler — doğrultulmuş şebeke, DC bara, SMPS
çıkışı — miliohm mertebesinde kaynaklar; orada fark ölçülemez.

**Karar: 820K.** Kaçak, zincirin *doğrulanamayan* riski (tezgahta ölçülecekler
listesinde duruyor); giriş empedansı ise hesabı yapılmış ve önemsiz çıkmış bir
fark. Doğrulanamayan riskin küçüğü seçilir. Kılavuza ayrıca "lehimden sonra
izopropil alkolle temizle" maddesi eklendi — bu bölücüde temizlik bir doğruluk
parametresi.

| | 1M (ilk) | 2.2M (ara) | **820K (nihai)** |
|---|---|---|---|
| Alt bacak | 10K | 22K | **8.2K** |
| N · menzil · adım | 601.0 · ±613.7 V · 18.78 mV | *aynı* | *aynı* |
| Direnç başına @615 V | 102.3 V (%51) | 102.3 V | 102.3 V |
| Thévenin | 9.98 kΩ | 21.96 kΩ | **8.19 kΩ** |
| Rust (kaçak duyarlılığı) | 6.00 MΩ | 13.20 MΩ | **4.92 MΩ** |
| Metal film alınabilir mi | ❌ | ✅ | ✅ |

`ORAN_YUKSEK = 601.0f` dört turda da **hiç değişmedi**. R17 (22K) 2.2M turunda
kaldırılmıştı, 820K ile geri kondu: Thévenin 8.19 kΩ tek başına C3 ile 194 Hz
kesim ve 860 Hz'te −13.1 dB veriyor, 20 dB kuralını geçmiyor. R17 ile toplam
30.19 kΩ, fc 52.7 Hz, −24.3 dB.

**Bu iş dört gerçek kusur ortaya çıkardı:**

1. **`tasarim3.py` tek kaynağa bağlı değildi.** Bölücü değerleri orada *elle*
   yazılmıştı; `tasarim3_sabit.py` değişince tasarım dökümanı sessizce eski
   değerlerle hesaplamaya devam etti ve şemayla ayrıştı. Artık `KANALLAR`
   sabit dosyadan türetiliyor, iki kaynağın eşitliği de bir kural.
2. **"Thévenin < 10 kΩ" kuralı yanlış şeye bakıyordu.** O TI kılavuzu ADS'in
   *gördüğü* empedans için; bizde ADS tamponun çıkışını görüyor. Bölücü
   Thévenin'inin belirlediği şey tamponun **taban akımı ofseti**.
3. **Taban akımı hesabının kendisi de yanlıştı.** İlk yazılışında R7/R17
   unutulmuştu: tamponun + girişi bölücü Thévenin'ini *ve* seri süzgeç
   direncini görür. Düzeltilince NORMAL %0.029 → **%0.126**, YÜKSEK %0.036 →
   **%0.133** çıktı. İkisi de %0.5 bütçesinin altında ve zaten sıfır
   kalibrasyonunun sildiği bir ofset — ama rakam yanlıştı.
4. **RC örtüşme süzgeçlerinin topolojisi netlist'te hiç denetlenmiyordu.**
   R17 bir tur kaldırılıp geri kondu, netlist denetimi **iki durumda da
   75/75 geçti**. Artık 10 kural var: seri direnç bölücü düğümünde, öbür ucu
   tamponun *önünde*, kondansatör GND'ye değil VREF'e. Netlist 75 → **85**.

**Yeni tasarım kuralı — "metal film olsun" yetmiyor.** Bölüm 11'e tedarikçinin
metal film listesi girildi; oranı kuran her direnç (iki bölücü + skop bölücüsü
+ fark yükselteci) o listede gerçekten var mı diye sınanıyor. Tasarım kuralı
81 → **89**.

**Sipariş — metal film %1, hepsi 1/4W:**
`820K ×8` · `8.2K ×5` · `10K ×10` · `22K ×10` · `220K ×5` · `6.8K ×10` ·
`47K ×10` · `2.7K ×10` · `100K ×5`
(220R ve 100R metal film listesinde yok — onlar oranı kurmuyor, stoktaki
karbon film yeterli.)

Zincir: **7/7** · 89 tasarım kuralı · 30 SPICE · ERC 0 · 85 netlist ·
70 AVR · 70 arayüz. Aşama 1 (9/9) ve Aşama 2 (6/6) regresyon temiz.

---

#### 5.12.19 🔬 "ESP32-S3 en iyisi mi?" — MCU araştırması (2026-09-09)

Kullanıcı skop tarafında daha iyi sonuç istedi, MCU'yu tamamen değiştirmeye
açık olduğunu söyledi. Araştırıldı; **sonuç: S3'te kalınıyor.**

**1. Bugünkü sınır MCU değil, ön uç.** Sallen-Key f0 = 16.55 kHz:

| frekans | zayıflama |
|---|---|
| 5 kHz | −0.04 dB |
| 10 kHz | −0.54 dB |
| 16.55 kHz | −3.01 dB |
| 41.67 kHz (Nyquist @83.3 ksps) | −16.15 dB |

Ayrıca en hızlı zaman tabanı (100 µs/div × 100 örnek/div) **1 Msps** ister,
eldeki 83.3 ksps ile bölme başına 8 örnek düşer. Yani MCU'yu değiştirmek
tek başına hiçbir şey kazandırmaz — süzgeç de zaman tabanı da yeniden
tasarlanmalı.

**2. 🔴 ESP ailesinde daha hızlısı YOK — Espressif'in kendi blogu yanıltıcı.**
[developer.espressif.com/blog/2025/08/adc-performance](https://developer.espressif.com/blog/2025/08/adc-performance/)
tablosu ESP32-C5 için **2000 ksps** diyor. Ama kurulu çekirdekteki
(`esp32:esp32` 3.3.11) `soc_caps.h`, yani sürücünün **fiilen dayattığı**
sınır:

| SoC | `SAMPLE_FREQ_THRES_HIGH` | blog: DNL / INL | blog: menzil |
|---|---|---|---|
| ESP32-S3 | **83 333** | ±4 / ±8 | 0–2900 mV |
| ESP32-C5 | **83 333** | ±5 / ±5 | 0–3300 mV |
| ESP32-C6 | **83 333** | +12/−8 / ±10 | 0–3300 mV |
| ESP32-P4 | **83 333** | +3/−1 / +3/−5 | 0–3300 mV |
| ESP32 (klasik) | **2 000 000** | ±7 / ±12 | 150–2450 mV |

Yani sürekli-ADC yolunda **83.3 ksps ailenin ortak tavanı**; 2 Msps'i yalnızca
klasik ESP32 veriyor ve o da ailenin **en kötü doğrusallığı** ve kırpılmış
giriş menziliyle. Blog ile `soc_caps.h` çelişiyor — çelişki çözülmedi, ama
karar bugün **çalıştırılabilir** olana göre verildi.

**3. S3 aslında ailenin iyi tarafında.** INL ±8 / DNL ±4 ile C3, C6, H2 ve
klasik ESP32'nin önünde; yalnızca P4 daha iyi ve o da aynı 83.3 ksps'te.

**4. Gerçek hedef ne olurdu:** envanter SMPS ağırlıklı (SG3525, TL494,
UC3843, IR2110) — bunlar 20–100 kHz'te anahtarlıyor. Dalga *şeklini* görmek
için 5–10 katı, yani **500 kHz–1 MHz bant** ve **≥2–4 Msps** gerekir.
Bugünkünün 25–50 katı; bu bir MCU değişimi değil, ayrı bir alet.

| Yol | ADC | Gerçekçi bant | Bedel |
|---|---|---|---|
| **S3, bugünkü hâli** | 83.3 ksps dahili | ~10 kHz | 0 |
| S3 + süzgeç 30 kHz'e | 83.3 ksps | ~20 kHz | 4 parça |
| Başka ESP (C5/C6/P4) | 83.3 ksps | ~10 kHz | **kazanç yok** |
| ESP32 klasik | 2 Msps, INL ±12 | ~200 kHz, gürültülü | firmware + kalite kaybı |
| STM32G4 | 4 Msps, 5 ADC, donanım oversampling → 16 bit | ~500 kHz | firmware baştan, Wi-Fi yok |
| S3 + AD9226 modülü (LCD_CAM) | 65 Msps 12 bit | MHz | ayrı proje |

**5. Geçiş sigortası zaten elimizde.** Matematik katmanı platformdan bağımsız
(`olcum3.h` 377 + `skop_olc.h` 178 = 555 satır) ve **AVR emülatöründe**
doğrulanıyor. İleride STM32'ye geçilirse yeniden yazılacak olan yalnızca
ADC/NVS/seri tutkalı — zor kısım taşınabilir durumda. Bu, B4/B5'in
başlangıçtaki gerekçesinin beklenmedik bir getirisi.

**Karar:** S3'te kal, yedek S3 alımı geçerli. Skop yükseltmesi ayrı bir
kalem olarak yol haritasına yazıldı — ve o iş MCU ile değil, **ön uç +
harici ADC** ile çözülür.

---

#### 5.12.20 🔭 Hızlı skop yolu — AD9226 modülü + ESP32-S3 LCD_CAM (araştırma, 2026-09-09)

5.12.19'da "skop MCU ile değil ön uç + harici ADC ile çözülür" denmişti.
Kullanıcı bu yolun ayrıntısını, fiyatını ve **SMD lehimlemeden** yapılabilir
olup olmadığını sordu. Araştırıldı.

**🟢 SMD sorunu tamamen çözülüyor.** AD9226 hazır modül olarak satılıyor;
yonga (LQFP-48) fabrikada lehimli geliyor, sana kalan yalnızca **2.54 mm
header**. Modülün üzerinde ayrıca:

| Modülün verdiği | Değer | Neden önemli |
|---|---|---|
| Giriş zayıflatıcı + ofset devresi | −5…+5 V (10 Vpp) → 1–3 V | **Hızlı op-amp gerekmiyor** — TL072 zaten 3 MHz'de yetersiz kalırdı |
| Dijital çıkış seviyesi | **3.3 V** | ESP32-S3'e doğrudan, seviye çevirici yok |
| Besleme | tek 5 V | kartta zaten var |
| Analog bant | −3 dB @ 350 MHz | ADC'nin kendisi darboğaz değil |
| Bağlantı | 2.54 mm dişi header | delikli plakete uyar |

**Tasarım taslağı — 8 bit yeter, çünkü gerçek osiloskoplar 8 bit.**
AD9226'nın üst 8 biti (D11…D4) alınır; ESP32-S3'ün CAM arayüzü 8 bit kipinde
çalışır. Pin: 8 veri + PCLK + 1 senkron ≈ **10 GPIO**.

| PCLK | Msps | 4096 örneklik pencere | Nyquist | delikli plakette gerçekçi |
|---|---|---|---|---|
| 10 MHz | 10 | 409.6 µs | 5 MHz | ~1 MHz |
| 20 MHz | 20 | 204.8 µs | 10 MHz | ~2 MHz |
| **40 MHz** (S3 tavanı) | 40 | 102.4 µs | 20 MHz | ~4 MHz |

Bugünkü ~10 kHz'e göre **100–400 kat**. 4096 örnek = 4 kB, S3'ün 512 kB
dahili SRAM'ine rahat sığıyor — **PSRAM gerekmiyor**, dolayısıyla forumlarda
şikâyet edilen PSRAM/DMA bant darboğazı bu işte hiç doğmuyor.

**🔴 Asıl risk lehim değil, FIRMWARE.** LCD_CAM'i kamerasız, jenerik paralel
yakalayıcı olarak kullanmanın Arduino düzeyinde örneği yok; ESP-IDF register
seviyesinde çalışmak ya da `esp32-camera`'yı kırpmak gerekiyor.
**Çalışan emsal KLASİK ESP32'de var, S3'te değil:**
[EUA/ESP32_LogicAnalyzer](https://github.com/EUA/ESP32_LogicAnalyzer) ve
[lmcapacho/ESP32_LogicAnalyzer](https://github.com/lmcapacho/ESP32_LogicAnalyzer)
— klasik ESP32'nin I2S paralel giriş kipiyle **20 MHz, 8/16 bit, 128k örnek**.
Yani firmware riskini düşürmek istersen klasik ESP32 + AD9226, S3 + LCD_CAM'den
**daha az riskli** — açık kaynak başlangıç noktası hazır.

**Diğer riskler:** (1) 40 MHz'te 8 paralel hat delikli plakette çapraz karışma
ve toprak sıçraması yapar — 10 Msps'te başlamak akıllıca, o bile 1000 kat.
(2) Bugünkü halka tamponlu ön-tetik, DMA blok yakalamada döngüsel GDMA
tanımlayıcı listesi ister. (3) ±613 V girişi bu modüle bağlamak için MHz'de
**kompanzasyonlu** bölücü (trimmer kondansatörlü) gerekir — projede yeni konu.

**Fiyat ve tedarik:** modül AliExpress/Amazon'da **~18–25 USD**. Türkiye'de
modül listesi bulunamadı; Çakır Elektronik **çıplak yongayı** satıyor ama o
LQFP-48, yani **SMD — alma**. `AD9226ARSRL` bazı dağıtıcılarda "obsolete";
modüller mevcut stok/klonlarla üretiliyor. Yani **yonga değil modül al**.

##### Tedarik denendi — AD9226 gönderilemiyor, ama muadili DAHA İYİ

Kullanıcı 2026-09-09'da sipariş etmeyi denedi. AliExpress **765,37 TL**
(araştırmadaki 18–25 USD bandının tam ortası, fiyat normal) ama:
*"Bu ürün adresinize gönderilemiyor."* — **satıcıya özel** bir kısıt, ürüne
değil (stokta 99737 adet görünüyordu). Başka satıcılar var:
`aliexpress.com/item/1005005576645194` · `.../1005007430909352`.

**🟢 Muadil: ALINX AN108 — bu proje için AD9226'dan daha uygun.**

| | AD9226 modülü | **ALINX AN108** |
|---|---|---|
| ADC | AD9226, 12 bit, 65 Msps | AD9280, **8 bit**, 32 Msps |
| Giriş konnektörü | SMA | **2× BNC** |
| Giriş menzili | ±5 V | ±5 V |
| Bağlantı | header | 34 pin, 2.54 mm |
| Bonus | — | **AD9708 DAC, 8 bit, 125 Msps** |
| Fiyat | ~20 USD | 22 USD (ALINX resmi) · 40–49 USD (AliExpress/eBay) |

Üç sebeple daha iyi:
1. **8 bit zaten hedefti.** AD9226'nın 4 bitini atacaktık (gerçek osiloskoplar
   8 bit, S3'ün CAM'i 8 bit kipinde). AN108 doğrudan 8 bit veriyor.
2. **32 Msps kayıp değil.** S3'ün PCLK tavanı zaten 40 MHz; 65 Msps'i hiçbir
   zaman kullanamayacaktık.
3. **Üstündeki DAC bir sinyal üreteci.** Şu an ölçüm kartını test etmek için
   elde NE555'ten başka bilinen kaynak yok. Temiz sinüs/kare üretip **kartın
   kendisini doğrulamak** için kullanılabilir — zincirin "tezgahta ölçülmeli"
   maddelerinden birkaçı bununla kapanır. BNC olması da SMA adaptörü derdini
   kaldırıyor.

Yedekler: **TLC5510** modülü (8 bit, 20 Msps, tek 5 V, basit) ·
**AD9248** modülü (çift kanal 12 bit 65 Msps — V ve I aynı anda, ama pin iki katı).

##### Karar ve kademeli plan

**Aşama 4 kalemi, şimdi değil.** Mevcut kartın değeri ±613 V çift yönlü
V/I/W ölçümünde ve o tezgahta doğrulanmadı. Bu iş mevcut kartın büyüklüğünde
ayrı bir proje; karıştırılmamalı. Kullanıcı 2026-09-09'da "şimdilik almıyorum
ama ileride alabilirim, ihtimali aklımızda tutalım" dedi.

Sırası geldiğinde **alışverişle başlanmayacak**:

| # | Adım | Bedel | Karar noktası |
|---|---|---|---|
| 1 | Elde bir ESP32 ile hazır açık kaynak I2S paralel yakalama kodunu dene ([EUA](https://github.com/EUA/ESP32_LogicAnalyzer) / [lmcapacho](https://github.com/lmcapacho/ESP32_LogicAnalyzer)) | **0 TL** | Yürümezse burada dur |
| 2 | Yürürse **AN108** al (ADC + sinyal üreteci bir arada) | ~22–49 USD | — |
| 3 | 10 Msps'te başla, sonra yukarı çık | — | Delikli plakette 40 MHz riskli; 10 Msps bile bugünün 1000 katı |
| 4 | Kompanzasyonlu bölücü (trimmer kondansatörlü) tasarla | — | MHz'de zorunlu, projede yeni konu |

---

#### 5.12.21 🛒 Sipariş listesi denetimi (2026-09-09)

Kullanıcının direnc.net sepeti şema BOM'una karşı denetlendi.

**✅ Kartın elektroniği tam.** Şemanın istediği her direnç 50'şer adet
sipariş edilmiş (820K, 8.2K, 22K, 10K, 6.8K, 220K, 100K, 47K, 2.7K, 220R,
100R — 1K fazladan, sorun değil). BAT85 ×20 (4 gerekiyor), TL072CP ×3
(2 gerekiyor), LM358P ×10 (2 gerekiyor), 8 pin soket ×10 (6 gerekiyor),
1×40 dişi header ×2 (J5 için), silikonlu prob kablosu (HV için —
kırmızı ×2, siyah ×2). LM319N ×3 de yol haritası kalemi olarak alınmış.

**Stoktan karşılananlar (siparişe gerek yok):** 100nF ×11 gerekiyor,
stokta 41 · 1nF ×6 gerekiyor, stokta 11 · TL431 ×1, stokta 10.

**Yolda olduğu varsayılanlar — TEYİT EDİLMELİ:** ADS1115 ×2 · ESP32-S3 ×1 ·
muz jak / bariyer klemens (4 giriş çifti) · şönt seti (0.1R taş, 15mR).

##### 🔴 Listede EKSİK olanlar

| # | Eksik | Neden kritik |
|---|---|---|
| 1 | **Delikli plaket (pertinaks)** | Kart bunun üzerine kurulacak. Envanterde kaydı yok — ama "Mekanik/Sarf" rastgele girilmiş kategoriler, **kayıtta yok = elinde yok demek değil**. Bakılmalı. 615 V için geniş, kaliteli bir plaket gerekiyor |
| 2 | **±12 V rayının ham kaynağı** | 7812 ×3, 7912 ×2 stokta **ama onları besleyecek şey yok**. Simetrik ±12 V için ya çift sargılı trafo, ya iki ayrı 12 V adaptör, ya NE555 şarj pompası. **Dört TL072 kesiti (skop Sallen-Key + hızlı yol) tamamen buna bağlı** — B11 |
| 3 | **Yedek ESP32-S3** | 5.12.15'te önerilmişti. 615 V ile çalışılacak, elde tek kart var |
| 4 | İzopropil alkol | 5.12.18'de kılavuza eklendi: 820K zincirinin etrafındaki lehim kalıntısı **kaçak yolu** demek. Bu bölücüde temizlik bir doğruluk parametresi |
| 5 | Lehim teli / pasta | Envanterde kayıt yok |

**✅ Cevaplandı, 5.12.23:** 12 V adaptör yok; 24 V kaynak + LM358 orta nokta
tamponu ile çözüldü, ek alım gerekmiyor. Bu satırdaki "±12 V ham kaynağı"
eksiği **kapandı** — geriye delikli plaket, yedek ESP32-S3, izopropil alkol
ve lehim teli kalıyor.

**Listedeki fazlalıklar** (ULN2003, 74HC595, CD4027, LM339N, BD139, USB
konnektörler, tunik konnektörler, geniş soket yelpazesi) bu kartla ilgili
değil ama zararsız — başka projelere gider.

---

#### 5.12.22 ✅ B15 — ARIZA VE ZORLAMA SİMÜLASYONU — **TAMAMLANDI (2026-09-09)**

> **Sonuç özeti aşağıda 5.12.24'te.** Bu bölüm görev tanımı olarak
> bırakıldı; her maddenin cevabı 5.12.24'te kodlarıyla duruyor.
> Çıktı: `uretim/sim3_ariza.py` — 89 doğrulama, 25 senaryo,
> `dogrula3.py`'de **B15** adımı.

Kullanıcının isteği: *"sistemin baştan sona olası zorlama ve kırılma
noktalarının hepsi test ve simüle edilsin. Ters akım, ters voltaj, yüksek
voltaj — tüm giriş ve çıkışlar için."*

**Bugün ne var:** B2 yalnızca **iki** arıza senaryosunu kapsıyor —
(a) op-amp çıkışı arızada raya oturursa ADS pinine kaçan akım (kelepçe
karşılaştırması), (b) girişte %15 aşırı gerilim. Gerisi **hiç
incelenmedi**.

**B15'in kapsaması gerekenler:**

**A. Giriş terminalleri — yanlış sinyal**
1. 🔴 **±32 V terminaline 615 V** (en olası kullanıcı hatası: yanlış klemens).
   Bölücü düğümü Vref + 615/33.35 ≈ **20.1 V** olur; LM358'in mutlak giriş
   sınırı V+ +0.3 = 5.3 V. R7 (22K) üzerinden kaçak ≈ (20.1−5.3)/22k =
   **0.67 mA**. LM358'in giriş kelepçe akımı sınırıyla karşılaştırılmalı.
2. 🔴 **±32 V terminaline 230 V AC şebeke** — aynı yol, tepe 325 V.
3. **613 V terminaline 1000 V+** — direnç başına 167 V, 200 V sınırının
   altında ama pay %16'ya iner; ayrıca bölücü düğümü ne olur?
4. **Skop girişine menzil dışı** — kelepçe var, B2 kısmen ölçtü; tamamlanmalı.
5. **Şönt terminaline ters akım ve aşırı akım** — çift yönlü tasarlandı ama
   sınır ölçülmedi. Şönt açık devre kalırsa ne olur?

**B. Besleme arızaları** — ±12 V artık **24 V + LM358 orta nokta tamponu**
ile üretiliyor (5.12.23); senaryolar bu topolojiye göre kurulmalı, ileride
6× 18650 paketi de aynı konnektöre takılacağı için o yol da değerlendirilsin.
6. **+5 V yok, ±12 V var** (ve tersi) — beslemesiz op-amp girişine sinyal
   sürmek "phantom powering" ve latch-up riski.
7. **Ters polarite besleme** — 3 pinli konnektör ters takılırsa (+12 ↔ −12).
8. USB'den beslenirken harici besleme de bağlı.
8b. 🔴 **Orta nokta tamponu (LM358) arızası** — GND referansı kaybolur, iki
   ray birden kayar. Tamponsuz dirençli bölücü ne kadar dayanır?
8c. 🔴 **24 V kaynak yalıtımlı değilse** −12 V rayı şebeke toprağına kısa
   devre olur. Bu senaryo sayısallaştırılmalı.

**C. Bileşen arızası**
9. 🔴 **Alt bacak (R16, 8.2K) açık devre** — bölücü düğümü girişe bağlı
   kalır. İlk hesap: 4.92M zinciri akımı (615−5)/4.94M ≈ **123 µA**'e
   sınırlıyor, yani muhtemelen **hayatta kalınır** — ama doğrulanmalı.
10. Zincirdeki bir 820K açık devre → düğüm Vref'e gider (güvenli, teyit).
11. Vref tamponu arızası → iki kanal birden kayar.

**D. Kullanıcı hatası ve sistem**
12. 🔴 **Kart izole DEĞİL** — 615 V şebeke referanslı bir devreye bağlanırsa
    gerilim USB üzerinden PC'ye gider. Bu bilinen bir uyarı ama
    **sayısallaştırılmadı**.
13. Prob ucu kayması, sıcak takma.

**Kabul ölçütü:** Hiçbir TEK arıza ESP32'yi ya da PC'yi öldürmemeli.
Ölecek bir parça varsa **hangisi olduğu bilinmeli ve ucuz olmalı**
(tercihen soketli LM358). Her senaryo için: kaçan akım, düğüm gerilimi,
hangi mutlak sınır aşılıyor, hangi parça gidiyor.

**Yöntem:** Mevcut zincirin kuralları — ngspice (B2 kalıbı) + `kural()`
iddiaları. Her sonuç çalıştırılabilir bir testle desteklenmeli; elle
yazılmış sayı olmayacak. Çıktı `uretim/sim3_ariza.py` (yeni B15 adımı)
ve `dogrula3.py`'ye eklenmeli.

---

#### 5.12.23 🔋 ±12 V rayı ÇÖZÜLDÜ — 6× 18650, yükselticiye gerek yok (2026-09-09)

**Açık soru #1 kapandı.** Kullanıcı: *"12 volt adaptörüm yok; 24 V güç
kaynağım ve voltaj düşürücü regülatörüm var. 18650 + yükseltici ile
besleyebilir miyim?"*

**Cevap: 18650 ile evet — ama YÜKSELTİCİ GEREKMİYOR.** İki adet 3'lü paket
sırt sırta, orta nokta = GND:

| 3 hücre durumu | Ray | TL072 sınırı ±5…±18 V |
|---|---|---|
| dolu (4.2 V) | **±12.60 V** | ✅ |
| nominal (3.7 V) | **±11.10 V** | ✅ |
| boş (3.0 V) | **±9.00 V** | ✅ |

Tam şarjdan tam boşalmaya kadar TL072 aralığın içinde. Yükseltici,
inverter, şarj pompası — hiçbiri gerekmiyor. **Envanterde tam da gereken
tutucu var: `PWR003` 3'lü pil yuvası ×2.**

##### Akım bütçesi — yük çok küçük

| Ray | Yük | Ne |
|---|---|---|
| ±12 V | **5.6 mA** | 2× TL072 (4 kesit) |
| +5 V analog | **1.4 mA** | 2× LM358 |
| +3.3 V | **4.0 mA** | TL431 rayı 3.7 + 2× ADS 0.3 |
| **Analog toplam** | **11.0 mA** | ESP32 hariç |
| ESP32-S3 | 40 mA (boş) … 250 mA (Wi-Fi tepe) | |

2500 mAh hücreyle: yalnızca analog **~357 saat**; ESP32 de pilden beslenirse
**~17 saat**.

##### 🔴 Bunun asıl kazancı: KART İZOLE OLABİLİR

Projenin en büyük tehlikesi bugüne kadar şuydu: *kart izole değil, 615 V
şebeke referanslı bir devreye bağlanırsa gerilim USB üzerinden PC'ye gider.*
USB ile beslendiği sürece kart toprağı = PC toprağı = şebeke toprağı.

**Pil + Wi-Fi ile kart tamamen yüzer.** Firmware Wi-Fi'yi zaten destekliyor
(`WIFI_AD`/`WIFI_SIFRE` boş, web sunucusu kurulu). O zaman:

| | USB beslemeli (bugün) | Pil + Wi-Fi |
|---|---|---|
| Kart toprağı | PC toprağı = şebeke toprağı | **yüzer** |
| 615 V şebeke referanslı devreye bağlanırsa | ⚠️ **kısa devre — PC ve kullanıcı tehlikede** | akım akmaz |
| Kalan risk | — | **kartın kendisi 615 V'a çıkar — yalıtımlı kutu ŞART** |

Bu galvanik izolasyon *değil* (izolasyon yükselteci yok); **tüm aleti
yüzdürmek** — el tipi multimetrelerin yaptığı şeyin aynısı. Meşru ve
etkili, ama şartı var: ölçüm sırasında **USB takılı olmayacak** ve kart
yalıtımlı bir kutuda, açıkta iletken kalmayacak. Programlama/hata ayıklama
USB ile, ama yalnızca HV bağlı DEĞİLKEN.

##### İki besleme yolu — kart ikisini de kabul etsin

| | **A. 6× 18650 (önerilen)** | **B. 24 V kaynak + orta nokta bölücü** |
|---|---|---|
| ±12 V nasıl | iki 3'lü paket sırt sırta | 24 V'u ikiye böl, orta nokta = GND |
| Ek parça | yok (yuvalar elde) | **LM358 orta nokta tamponu** (stokta 8 var; LM358 azami besleme 32 V — 24 V'ta çalışır, 7 mA dengesizliği rahat sürer) |
| Anahtarlama gürültüsü | **sıfır** | kaynağın SMPS gürültüsü raya biner |
| İzolasyon | **yüzer** | kaynak yalıtımlıysa yüzer, değilse hayır |
| Kullanım | HV ölçümü, saha | tezgahta geliştirme |

**Karar: kartta 3 pinli bir besleme girişi olsun (+12 / GND / −12)** —
siparişte 3 pin tunik konnektör zaten var. Hangi kaynağın takıldığı kartı
ilgilendirmesin.

**ESP32'nin 5 V'u:** +12 raydan. İki ayrı yol tavsiye ediliyor —
analog +5 V (LM358, 1.4 mA) için **7805** (stokta 6 adet, ısınmaz, temiz);
ESP32'nin 150 mA'i için kullanıcının **düşürücü regülatör modülü** (7805 ile
7 V × 150 mA = 1 W olurdu, soğutucu gerekirdi). Anahtarlamalı modülün
gürültüsü analog rayı kirletmesin diye ayrı tutuluyor; toprak yıldız
noktası paketlerin orta noktası olmalı.

##### 🔴 Hücre sayısı: 2 var, 6 gerekiyor → BİRİNCİ YOL 24 V OLDU

Kullanıcı 2026-09-09'da cevapladı: **elinde 2 adet 18650 var.** İki hücre
ortadan bölününce ±3.7…±4.2 V eder — TL072'nin ±5 V tabanının **altında**,
olmaz. Dolayısıyla sıralama değişti:

| Yol | Ne gerekiyor | Gürültü | İzolasyon | Karar |
|---|---|---|---|---|
| **24 V + LM358 orta nokta tamponu** | **hiçbir şey — hepsi elde** | kaynağın SMPS'i | kaynak yalıtımlıysa | ✅ **ŞİMDİ BUNU KUR** |
| 6× 18650 (iki 3'lü paket) | **4 hücre daha al** | **sıfır** | **yüzer** | İzolasyon istendiğinde |
| 2× 18650 + yükseltici → 24 V → bölücü | yükseltici modülü | **iki kat anahtarlama** (boost + bölücü) | yüzer | ❌ en kötüsü |

Son satır kullanıcının ilk sorduğu şeydi ve teknik olarak mümkün — ama bir
**ölçüm aleti** için en kötü seçenek: anahtarlamalı yükselticinin gürültüsü
doğrudan ±12 V rayına biner, TL072'nin PSRR'si 100 kHz'te DC'dekinin çok
altındadır ve **Sallen-Key bu gürültüyü süzemez** (gürültü süzgeçten SONRA,
op-amp'in beslemesinden giriyor). 24 V kaynak varken buna gerek yok.

**Uygulama sırası:** B11'i 24 V + LM358 tamponu ile kur, kart 3 pinli besleme
girişi (+12 / GND / −12) taşısın. Pil yolu sonradan aynı konnektöre takılır —
kartta hiçbir değişiklik gerekmez. 4 hücre alındığında izolasyon seçeneği
açılır.
- Seri bağlı hücreler **eşleşmiş** olmalı; korumalı (protected) hücre tercih
  edilir ya da hücreler tek tek şarj edilmeli. 11 mA'de dengesizlik önemsiz
  ama ESP32 de pilden beslenirse saatler içinde bir hücre aşırı boşalabilir.
  Eldeki 2 hücre 6'lı pakete katılacaksa **aynı marka/kapasite/yaşta 4 hücre
  daha** alınmalı — karışık hücre seri bağlantıda en zayıfını öldürür.
- 24 V kaynağın **yalıtımlı (floating)** olup olmadığı ölçülmeli: negatif
  ucu ile şebeke toprağı arasına ohmmetre. Toprağa bağlıysa orta nokta
  bölücü şemasında −12 V rayı toprağa kısa devre olur.

**B11 (±12 V rayı) artık tanımlı bir iş** — açık soru değil.

---

#### 5.12.24 ✅ B15 SONUÇLARI — arıza simülasyonu (2026-09-09)

`uretim/sim3_ariza.py` · **111 doğrulama · 27 senaryo · ~4 s** ·
`dogrula3.py` → **B15** adımı. Zincir B11 ile birlikte **9/9**.

> ⚠ **Bu bir HESAP, tezgah ölçümü değil.** Donanım kurulmadı. B15 tasarımı
> zorluyor, kurulmuş bir kartı değil. Şu üçü yalnızca tezgahta öğrenilir:
> bir direncin aşırı yükte açık mı kısa mı devre kaldığı, gerçek LM358
> giriş jonksiyonunun kırılma gerilimi, delikli plakette 615 V'ta yüzey
> kaçağı.

##### 🔴 DEVİR'in kendi sayılarından DÖRDÜ yanlış çıktı

| DEVİR ne diyordu | B15 ne buldu |
|---|---|
| **5.12.22/1:** "LM358'in mutlak giriş sınırı V+ +0.3 = **5.3 V**" | **Yanlış.** Sınır V−'ye göre **32 V** ve beslemeden BAĞIMSIZ. LM358'in girişinde V+'ya kelepçe diyodu **yoktur**. İki bağımsız üretici doğruladı: TI SLOS068AB §7.3.3 *"Inputs may exceed VS up to the maximum VS without device damage"* · onsemi LM358/D Not 5 *"either or both inputs can go to +32 V without damage, independent of the magnitude of VCC"* |
| **5.12.22/1:** "R7 üzerinden kaçak ≈ **0.67 mA**" | **Pozitif tarafta akım AKMIYOR** (kelepçe yok). Kaçak yalnızca NEGATİF tarafta var: −615 V'ta alt-taş jonksiyonundan **564 µA** — TI'ın kendi 1 mA sınırının altında. 0.67 mA rakamı hem yanlış mekanizmaya dayanıyordu hem de düğümün yüklenmesini ihmal ediyordu |
| **5.12.22/9:** "R16 açık → 123 µA'e sınırlı, **muhtemelen hayatta kalınır**" | **Akım doğru (≤118 µA), sonuç doğrulanamadı.** LM358'in V+'ya kelepçesi yok, düğümü aşağı çekecek hiçbir şey kalmıyor. Girişin nerede duracağını belirleyen tek şey jonksiyonun **ters kırılma gerilimi** — o değer hiçbir veri sayfasında **yok**. B15 bu yüzden tek sayı değil **tarama** raporluyor: 40 V varsayımından itibaren mutlak sınır aşılıyor, kırılma hiç olmazsa düğüm **615 V'a** oturuyor. Anında ölmüyor ama sürekli spek dışı — **sessizce yanlış ölçüyor** |
| **5.12.23:** "±12 V rayı **5.6 mA**" (orta nokta yükü sayılmış) | **Yanlış sayım.** Op-amp boşta akımı V+ → V− **doğrudan** akar, orta noktaya hiç değmez. Gerçek orta nokta yükü **6.4 mA** (7805 kolu). ESP32'nin düşürücüsü +12 V'tan beslenirse **250 mA** — LM358'in garantili çekme akımının (sıcakta 5 mA) **50 katı** |

##### 🔴 B15'in BULDUĞU ve ŞEMADA DÜZELTTİĞİ üç kusur

**1. ADS girişlerinde seri direnç HİÇ YOKTU** — ve bu bir arıza değil,
**normal menzil dışı okumanın** her anında geçerliydi.

Netlist kanıtı: `/V_TAMPON = U3.6, U3.7, U7.4` — tampon çıkışı ADS pinine
doğrudan. LM358'in çıkış tavanı için veri sayfası **tek yönlü** garanti
veriyor (TI SLOS068AB **§5.7** — düz LM358 tablosu; §5.5 LM358B'ye ait —
koşul V_S = 5 V, R_L ≥ 2 kΩ, 25 °C: raydan düşüm **en fazla** 1.5 V,
yani V_OH ≥ 3.5 V) — rayın ne kadar **yakınına** çıkacağına dair sınır **yok**.
ADS'in giriş empedansı 2.4 MΩ, yani tampon test koşulundan (2 kΩ) 1200 kat
daha hafif yüklü; yük azaldıkça çıkış raya yaklaşır.

| V_OH varsayımı | ADS pini | seri R yok | 1K seri ile |
|---|---|---|---|
| V+ − 1.5 V (garantili) | 3.50 V | 0 mA | 0 mA |
| V+ − 0.9 V (makul) | 3.85 V | 2.51 mA | 0.30 mA |
| V+ (spek dışı üst) | 3.99 V | **12.6 mA** | 1.30 mA |

12.6 mA, ADS'in **mutlak** 10 mA sınırının üstünde. TI'ın tasarım hedefi
zaten çok daha sıkı: **≤1 mA** (SLVAEX7A §2.1) veya mutlak maksimumun
%20'si = 2 mA (SBAA227 §3.1).

⚠ **B2 bu soruyu 2.7 kΩ seri dirençle ölçüp "kelepçe gerekmiyor" demişti —
o direnç şemada yoktu.** O 2.7 kΩ skop ve hızlı akım yollarının kelepçe
direnciydi. B2 düzeltildi ve artık gerçek değeri kullanıyor.

→ **DÜZELTİLDİ:** `R34` (U3B→AIN0), `R35` (U4A→AIN2), `R36` (VREF→AIN1/AIN3),
hepsi **1 kΩ**. Bölücü altları, C2/C3 ve R28 gerçek VREF'te kaldı.
PGA sabit olduğu için kazanç hatası da sabit: **%0.042**, kalibrasyon siliyor
(ADS'in kendi kademe uyumu speki %0.1). Stokta 30 adet 1K var.

**2. Şönt kanalı — B15'in bulduğu EN CİDDİ açık.** `SONT_P`/`SONT_N` de
ADS pinlerine doğrudan gidiyordu (`/SONT_P = C4.1, R18.2, R27.1, U6.4`).
Tek akım sınırlayıcı R18 = **100 Ω**.

| senaryo | R38 YOK | R38 (1K) ile | sonuç |
|---|---|---|---|
| 10R şönt, ADS 10 mA eşiği | 0.48 A yükte | **1.48 A** yükte | eşik 3.1× yukarı |
| Şönt açık + 12 V / 1 A yük | 66.3 mA | **7.3 mA** | ADS artık **yaşıyor** |
| Şönt açık + 12 V / 10 mA yük | 6.2 mA | 3.5 mA | zaten zararsızdı |
| J3'e 32 V **çıplak** besleme | 255 mA | **25 mA** | ADS gider, ESP32 **güvende** |

⚠ **Yük direnci devrede SERİDİR.** Şönt açılınca yük akımı eski
büyüklüğünde başka yola dönmez — sıfıra düşer ve yeni bir çevrim oluşur:
`V_kaynak → harici yük → J3.1 → R18 → R38 → ADS AIN0 → ESD → +3V3 → GND`.
Bu yüzden tehlike **koşulludur**: yüksek empedanslı bir yükte (10R şöntün
varlık sebebi olan mA kademesi) arıza zaten zararsız.

🔴 Düzeltme **öncesi** bunlar kabul ölçütünü ihlal ediyordu: kaçak ADS'in iç
ESD diyodundan +3V3 rayına biniyor; ESP32'nin kendi boşta tüketimini (40 mA)
aşınca ray yükseliyor ve ESP32 de tehlikeye giriyordu. **R38/R39 ile hiçbir
senaryoda 40 mA aşılmıyor — ESP32 artık her arızada güvende.**

⚠ **Bu kanalda KELEPÇE KULLANILAMAZ:** SONT_P normal çalışmada ±256 mV
salınıyor — hem Schottky hem silisyum diyot o gerilimde zaten iletir.
Seri direnç tek seçenek.

→ **DÜZELTİLDİ:** `R38`/`R39` (1 kΩ), yalnızca ADS kolunda. Hızlı yol
(R27/R29) direncin **önünden** taplıyor, yani bant genişliği etkilenmiyor.
Eşik 4.8 V → **14.8 V**'a (3.1×), ESP32'nin güvende olduğu şönt arıza
gerilimi **47.8 V**'a çıktı. PGA sıçraması 0.120 puan — ADS'in kendi kademe
uyumu speki (0.1 puan) mertebesinde.

**3. C1 (100 nF) TL431'i osile ettiriyordu.** TI SLVA482A: TL431'in
katot–anot arasındaki kondansatör **10 nF – 2.2 µF** aralığında osilasyona
yol açıyor; güvenli değerler `<1 nF` ya da `>22 µF`. Şemadaki C1 tam o
aralığın ortasındaydı. TL431 veri sayfası zaten kondansatör
**gerektirmediğini** söylüyor (*"internally compensated to be stable
without an output capacitor"*).

→ **DÜZELTİLDİ:** C1 = **1 nF** (envanterde C049, 10 adet).

##### 📁 Ham araştırma ve denetim kanıtı — `uretim/b15-arastirma.md`

B15'in dayandığı **her veri sayfası sayısı**, kaynağı, ve her iddianın
bağımsız doğrulama sonucu bu dosyada (**437 KB**):

- 10 araştırma konusu (LM358, ADS1115, ESP32-S3, TL072/TL431, direnç aşırı
  yük, USB/izolasyon, AC şebeke, gerçek dünya arızaları, ngspice yöntemi)
- **80 iddia ayrı ayrı doğrulandı** — 35'i **çürütüldü** ve *neden*
  çürütüldüğüyle birlikte kayıtta tutuldu
- 6 denetim boyutunun tüm bulguları + önerilen yamalar

Üreteci: `uretim/b15_kanit_uret.py`. Kaynak veri oturuma bağlı geçici bir
dizindeydi ve **kaybolacaktı** — bu yüzden kalıcı `kanit/` klasörüne
döküldü. Çürütülenlerin saklanma sebebi: aynı sayılar ileride başka bir
kaynaktan tekrar önerilirse neden reddedildikleri bilinsin.

##### B15'in kendisi adversaryel olarak denetlendi

B15 yazıldıktan sonra altı bağımsız denetçi (SPICE modelleme, devre analizi,
iddia mantığı, eksik senaryo, sabitlerin kaynağı, şema tutarlılığı) betiği
ayrı ayrı denetledi ve **kendi ngspice koşumlarını yaptı.** Buldukları ve
düzeltilenler:

| bulgu | sonuç |
|---|---|
| A6/A7'nin devresi şemadaki R38'i (1K) yok sayıyordu | ADS akımı 9 kat abartılıyordu; düzeltildi, iki bulgu tersine döndü |
| A3'ün transient devresinde LM358 hiç yoktu | "giriş −5.59 V" → gerçekte **−0.62 V** (parazitik jonksiyon kelepçeliyor) |
| A5'te Sallen-Key'in seri dirençleri (2×6.8K) atlanmıştı | TL072 kelepçe akımı 2.0 mA → **0.64 mA** |
| C3b ölçülen düğümü ADS pini sanıyordu | O düğüm LM358'in **girişi**; arada doymuş tampon var. Ölen parça U7 değil, hiçbiri |
| Kazanç hatası tek bacakla hesaplanmıştı | ADS'in Z_diff'i **iki** bacağı görür; sayı 2× |
| İki iddia doğrudan `True`, beşi yalnızca literal sınıyordu | Hepsi netlist'ten/sabitlerden okunan gerçek denetimlere çevrildi |
| B5 matrisi "U3 ölür" diyordu ama ölçüm "sağ çıkıyor" diyordu | Çelişki giderildi |
| Gövde tablosu kapsam denetimi tautolojikti | Artık **netlist'ten** okuyor; R34–R39 eksikliğini yakaladı |

**Mutasyon testi:** `ADS_SERI_R` 1 kΩ → 1 mΩ yapıldığında **7 iddia kırmızıya
dönüyor** (A1, A1b, A6, A7, C5). Yani korumaların gerçekten sınandığı
kanıtlanmış durumda — testler sessizce yeşil kalmıyor.

##### 🔴 B15'in KAPATAMADIĞI tek bileşen senaryosu: endüktif yük

Denetim bunun tamamen eksik olduğunu yakaladı — ve kullanıcının alanı
(SMPS/inverter) düşünülürse **en olası zorlanma** bu. Şönt yükün **dönüş
kolunda**, yani kart yük akımının tamamını taşıyor.

**İki ayrı olay var, karıştırılmamalı:**

**(a) Her anahtarlamada — L·di/dt.** Kablo/şönt parazitik endüktansı
(~100 nH) üzerinde. **İyi haber:** 10 A/µs'te L·di/dt 1.0 V olmasına rağmen
düğüm yalnızca **−0.14 V**'a iniyor — C4 (100 nF) ve bölücü ağı tepeyi
yutuyor. Mutlak sınırın (−0.3 V) içinde, kelepçe akımı 0.001 mA.
⚠ 1 m'lik bir yük kablosu (~1 µH) aynı di/dt'de **10 kat** büyük tepe verir
— kablo kısa olmalı.

**(b) Arıza — endüktif yük akım akarken sökülüyor.** Bobin akımı devam etmek
istiyor ama kartın **1100 Ω**'luk yolundan geçemez (birkaç mA); ark **sökülen
kontakta** oluşur ve gerilim ark gerilimine (~15–20 V) kelepçelenir. Kart bunu
görür:

| | R38 yok | R38 (1K) ile |
|---|---|---|
| ~20 V arkta ADS akımı | 195 mA | **17.7 mA** |

R38 riski **11 kat** azaltıyor ama **elemiyor** — 10 mA sınırı 11.5 V'luk bir
arkta zaten aşılıyor ve hava arkı en az ~15 V.

→ **Bu, B15'in donanımla kapatamadığı tek bileşen senaryosu.** Çözüm
kullanımda: **endüktif yüke serbest geçiş (freewheel) diyodu**. Güç
elektroniğinin standart kuralı ama ölçüm kartı kullanılırken unutulması çok
kolay — **kutu etiketine yazılmalı**.

##### B2b — her programlamada yaşanan hal

Denetim, görev tanımının 6. maddesindeki "**ve tersi**"nin kapsanmadığını
yakaladı: USB takılı (+5 V, +3V3, VREF var) ama 24 V kapalı (±12 V yok).
Kart **her programlanışında** bu durumda.

TL072'ler beslemesizken girişlerinde sinyal var: U8A VREF'e (10K üzerinden),
U5A skop bölücüsüne bakıyor. Kelepçe akımları **0.12 mA** ve **1.0 mA** —
TI'ın 10 mA sınırının çok altında. Sallen-Key'in 2×6.8K'sı sınırlıyor.
**Zararsız.**

⚠ Eski die TL072'de giriş kelepçesi **yok**; TI o durumda "giriş gerilimi
beslemenin büyüklüğünü aşmasın" diyor. Alınacak TL072CP'nin hangi die olduğu
bilinmiyor — ama akım her iki halde de güvenli.

##### Bir metodoloji notu — "60 V" bir ölçüm değildi

Denetim, C1 bölümündeki manşet sayının ("LM358 girişi 60 V görüyor") bir
ölçüm değil, SPICE modelindeki **kaynaksız `BV=60`** parametresinin doğrudan
çıktısı olduğunu gösterdi. Aynı devre `BV=1000` ile koşturulduğunda düğüm
**615 V**'a oturuyor — yani tek sayılık rapor kötümser değil **iyimser**ti.

Düzeltildi: kırılma gerilimi artık `tasarim3_sabit.py`'de **açıkça bir
varsayım** olarak duruyor (`LM358_GIRIS_KIRILMA_VARSAYIMI`) ve C1 bölümü
tek sayı yerine **tarama** raporluyor. Zincir akımı da elle hesaplanmıyor,
simülasyonun döndürdüğü `i(Vin)` kullanılıyor.

Bu, projenin kendi kuralının ("elle yazılmış sonuç sayısı yok") B15'in
kendisinde de uygulanması demek — ve sonucu **güçlendiriyor**: kırılma
varsayımı ne olursa olsun (≥40 V) mutlak sınır aşılıyor.

##### Arıza → ölen parça matrisi (27 senaryo)

| kod | senaryo | ölen parça | ESP32 | PC |
|---|---|---|---|---|
| A1/A2 | J1'e ±615 V DC | R4 (220K) — kızarır, **açılmaz** | ✅ | ✅ |
| A3 | J1'e 230 V AC şebeke | **hiçbiri** (LM358 girişi −0.62 V'ta kelepçeleniyor, 261 µA) | ✅ | ✅ |
| A4 | J2'ye 1000 V | **hiçbiri** | ✅ | ✅ |
| A5 | Skop girişine ±400 V | R20 (100K) | ✅ | ✅ |
| A6 | Yanlış şönt (10R) + aşırı yük | U6 (ADS #1) — eşik 58× FS | ⚠→✅ | ✅ |
| A7 | Şönt açık + **çıplak** besleme | U6 (ADS #1) | ⚠→✅ | ✅ |
| A8 | Şönt ters akım, tam ölçek | **hiçbiri** (pay 44 mV) | ✅ | ✅ |
| A9 | 615 V ucu skop girişine kayıyor | R20 (3.3 W = 13× gövde) | ✅ | ✅ |
| B1 | ±12 V açık, +3V3 kapalı | **hiçbiri** (pay 19 mV!) | ✅ | ✅ |
| B3 | ±12 V ters takılması | U5 + U8 (2× TL072) | ✅ | ✅ |
| B5 | 24 V yalıtımsız + USB | **hiçbiri** (DIP-8'de Tj 111 °C; SOIC'te ölürdü) | ✅ | ✅ |
| B6 | USB + harici besleme | **hiçbiri** | ✅ | ✅ |
| B7b | J3'e besleme bağlanması | RS + R18 | ✅ | ✅ |
| C1 | Alt bacak (R16) açık | U3/U4 — yavaş | ✅ | ✅ |
| C2 | Bir 820K açık | **hiçbiri** (düğüm VREF'e oturur) | ✅ | ✅ |
| C3 | TL431 açık | **hiçbiri** — ama **sessizce +0.538 V kayar** | ✅ | ✅ |
| C3b | TL431 kısa | **hiçbiri** — zorlanan LM358 girişi (−0.55 V, 14 µA), ADS değil | ✅ | ✅ |
| C4 | C1 osilasyonu | **hiçbiri** — referans salınır | ✅ | ✅ |
| C5 | Vref tamponu raya oturuyor | U3 (soketli) | ✅ | ✅ |
| D1a | J2 şebekeye, kart GND toprakta | **hiçbiri** (125 µA) | ✅ | ✅ |
| **D1b** | **Kart GND'si canlıya + USB takılı** | **USB kablosu + PC anakartı** | ❌ | ❌ |
| D2 | Pille yüzdürüp 615 V ölçmek | **hiçbiri** — ama kullanıcı riskte | ✅ | ✅ |
| **A10** | **Endüktif yük akım akarken sökülüyor** | **U6 (ADS #1)** — kalan risk | ✅ | ✅ |
| B2b | USB takılı, ±12 V yok (her programlamada) | **hiçbiri** (0.12 / 1.0 mA) | ✅ | ✅ |
| D3 | Skop girişine dolu 400 V kondansatör | R20 | ✅ | ✅ |

⚠→✅ = düzeltmeden **önce** riskliydi, R38/R39 ile kapandı.

**Kabul ölçütü sonucu:** düzeltmelerden sonra **27 senaryonun hiçbirinde**
ESP32 ya da PC ölmüyor (`sim3_ariza.py` bunu bir kural olarak sınıyor).
Kalan iki risk: **A10** (endüktif yük — ADS ölebilir, freewheel diyodu ile
kapanır) ve **D1b** (kart izole değil — prosedürel). (B5'te PC'ye akan akım tamponun kendi kısa
devre akımı kadar — 60 mA, zararsız; kart GND'si USB üzerinden zaten
toprakta olduğu için 24 V'un yalıtımsızlığı yeni bir toprak yolu eklemiyor.) Ölen en pahalı bileşen **ADS1115 modülü
(~45 TL, soketli, 3 adet var)**. Tek istisna D1b — o bir **bileşen arızası
değil**, "kart izole değil" kısıtının doğrudan sonucu ve donanımla değil
**prosedürle** çözülüyor.

##### 🔴 D1b sayısallaştırıldı — DEVİR'in en eski uyarısı

| | değer |
|---|---|
| Arıza akımı (döngü 0.3–1.2 Ω) | **192–767 A rms**, tipik ~330 A |
| USB GND teli erime süresi (Onderdonk) | 28AWG **4.9 ms** · 26AWG 12.3 ms · 24AWG **31.2 ms** |
| 30 mA RCD açma süresi | ≤ **40 ms** (5×IΔn'de, IEC 61008) |
| B16 MCB | 48–80 A bandı, ≤100 ms |
| PC'nin USB koruması | **VBUS'ta 0.9 A · GND hattında HİÇBİR ŞEY** |

**Kim neyi koruyor:** RCD **insanı** korur · kablo kendini feda eder ·
**PC'yi koruyan yok** (anakartın GND izi kablodan önce buharlaşır,
20 mil/1 oz iz ~0.24 ms). Schuko fişi polarize değil, yani şebeke
referanslı bir SMPS'te DC baranın eksi ucu toprağa göre **%50 ihtimalle
0…−325 V** arasında.

**"Pille yüzdürelim" planı (5.12.23) PC'yi kurtarır, kullanıcıyı kurtarmaz.**
Tektronix pille beslenen gerçek bir osiloskop için bile toprağa göre
**30 V rms / 42 V tepe** sınırı koyuyor — 615 V bunun 14.6 katı. Yalıtımlı
kutu **şart**. Delikli plakette IEC 60664-1 takviyeli kaçak yolu (615 V → **630 V basamağı**)
12.6 mm = **5 delik atlama (12.70 mm)**; şemadaki "delik atlayarak" notu artık sayıya
bağlı. Ayrıca direnç gövdesinin çevreye karşı **sürekli** yalıtımı yalnızca
**75 V** (Vishay MRS25; 500 V rakamı 1 dakikalık testtir) — HV zinciri
toprak düzleminden ve komşu izlerden uzak durmalı.

##### 🎯 HANGİSİ ÇÖZÜLDÜ, HANGİSİ AÇIK — makineyle doğrulanıyor

`sim3_ariza.py` BÖLÜM 7 SONU bu tabloyu **netlist'ten okuyarak** üretir:
"uygulandı" diyorsa o parça şemada **gerçekten var**. Tablo şemayla
sessizce ayrışamaz.

| kod | öneri | durum |
|---|---|---|
| **F1** | ADS gerilim girişlerine 1K seri (R34/R35/R36) | ✅ **UYGULANDI** |
| **F2** | ADS akım girişlerine 1K seri (R38/R39) | ✅ **UYGULANDI** |
| **F4** | C1 100nF → 1nF (TL431 kararlılığı) | ✅ **UYGULANDI** |
| F3 | R4 bölme ya da 350 V anmalı gövde | ❌ **KAPATILDI (2026-09-09, kullanıcı kararı):** yapılmayacak. Gerekçe: 1W metal film 100K elde yok, senaryo (615 V yanlış klemense) istisnai, ve **diğer parçaları tehlikeye atmıyor** — ölen tek şey 0.60 TL'lik R4 |
| F5 | LM358 giriş kelepçeleri (1N4148) | ❌ **KAPATILDI (2026-09-09, kullanıcı kararı):** eklenmeyecek. %0.055 FS sürekli doğruluk bedeli, karşılığında C1 (R16 açık devre) senaryosu — ölen parça soketli LM358, 10 adet sipariş edildi |
| F6 | Kelepçe üst ucu TL431 rayına | ❌ **REDDEDİLDİ (B18, 2026-09-09).** Kullanıcı onaylamıştı; ölçüm F6'nın hızlı akım menzilini de %43 kestiğini ve TL431 kalıntısını kapatmadığını gösterdi. Yerine **B18/F12** — bkz. **5.12.27** |
| F7 | Orta nokta tamponu (10 Ω / TLE2426) | ⏸️ **açık** — B11 işi, ray henüz kurulmadı |
| F8 | ±12 V mekanik anahtarlama + 50 mA sigorta | ⏸️ **açık** — B11 işi |
| F9 | Delikli plaket 615 V aralığı (5 delik) | ⏸️ **açık** — montaj işi |
| F10 | Prosedür — **8** kural (kutu etiketi) | ⏸️ **açık** — kutu yapılınca. 8. madde B18'de eklendi: *açma sırası önce USB sonra 24 V* |

**Yani: şemada düzeltilebilecek her şey düzeltildi.** Açık kalanların
hiçbiri "unutuldu" değil — üçü **takas içerdiği için senin kararını
bekliyor**, ikisi **B11'e** (±12 V rayı) ait, ikisi **montaj/prosedür**.

🔴 **B15 kapsamı dışında kalan, kapatılmamış iki iş:**
- **A10** — endüktif yük: freewheel diyodu (F10/6'ya kural olarak yazıldı;
  donanımla kapatılamıyor)
- ~~**B16** — akım kanalı örtüşme süzgeci ADS Nyquist'inin 18.5 katı
  üstünde, hızlı yol belgelenenden dar bantlı~~ → ✅ **KAPATILDI**,
  sonuçlar **5.12.26**'da

##### Kutunun üzerine yazılacak yedi kural (F10)

Donanımla çözülemeyen tek şey kullanım. `sim3_ariza.py` BÖLÜM 7/F10:

1. **HV bağlıyken USB TAKILI OLMAYACAK.**
2. Önce GND klemensi, sonra HV ucu bağlanır; sökerken ters.
3. GND klemensi **her zaman** devrenin en düşük potansiyeline.
4. Programlama/hata ayıklama **yalnızca HV sökülmüşken**.
5. 24 V kaynağın yalıtımı **ohmmetreyle doğrulanmış** olacak.
6. Endüktif yük ölçülürken yükün üzerinde **serbest geçiş (freewheel)
   diyodu** olacak — A10'un kapatamadığı tek bileşen senaryosu bu.
7. Yük kablosu **kısa** olacak (parazitik endüktans doğrudan L·di/dt
   tepesine dönüşüyor).

##### Uygulanmayan ama ölçülmüş öneriler (BÖLÜM 7)

| # | Öneri | Neden uygulanmadı |
|---|---|---|
| F3 | R4 (220K) → **2 × 110K (350 V anmalı)** ya da 3 × 73.2K | Film 257 °C → 153 °C. ⚠ 2 parça yalnızca gövde **350 V anmalıysa** yeter (Vishay MRS25); ucuz Yageo minyatürü 200 V, o zaman **3 parça** gerekiyor. N ikisinde de korunur — **karar kullanıcının** |
| F5 | LM358 girişlerine 1N4148 kelepçe | C1 senaryosunu kapatır ama **%0.055 FS hata** getiriyor (kaçak × düğüm empedansı). Takas ölçüldü; lehim sağlamsa gerekmeyebilir |
| F6 | Kelepçelerin üst ucu +3V3 yerine TL431 rayına | ❌ **REDDEDİLDİ (B18).** B15 burada yalnızca skop menzilini yazmıştı; ölçüm hızlı akım yolunun da %43 kesildiğini ve F6'nın TL431 kalıntısını kapatmadığını gösterdi. Yerine B18/F12 (5.12.27) |
| F7 | Orta nokta tamponuna **10 Ω yalıtım direnci** ya da **TLE2426** | ±12 V rayı henüz kurulmadı (B11). **Kurulmadan önce okunmalı** |
| F8 | ±12 V girişine **mekanik anahtarlama** + 50 mA sigorta | Aynı — B11 ile birlikte |

##### 🔴 B11'i kuracak oturuma: ±12 V rayı hakkında üç uyarı

1. **LM358'in kapasitif yük sınırı 50 pF** — veri sayfasının Application
   Information bölümünde, tam da orta nokta tamponunun bağlantısı
   (evirmeyen birim kazanç) için. Ayırma kondansatörleri C9..C15 =
   **700 nF**, yani sınırın **14 000 katı**. Çözüm: tampon çıkışıyla GND
   düğümü arasına **10 Ω**, geri besleme direncin ardından. Ya da
   **TLE2426** (TO-92, delikli uyumlu, 40 V giriş, 31 mA çekme).
2. **ESP32'nin düşürücü regülatörü +12 V'tan BESLENMEZ.** 250 mA'lik dönüş
   akımı hiçbir orta nokta tamponunun karşılayamayacağı kadar büyük.
   ESP32 USB'den ya da ayrı bir kaynaktan beslenmeli.
3. **Ters polarite TVS ile korunamaz.** 24 V rayını tutan hiçbir standart
   SMBJ parçası LM358'in 32 V mutlak maksimumunun altında kelepçeleyemiyor
   (SMBJ24A: 38.9 V @ 15.4 A). **Mekanik anahtarlama** tek doğru çözüm.
   Ayrıca **LM2904 almayın** — "LM358 muadili" diye satılıyor ama TI onu
   26 V'a derate ediyor; 24 V rayda bu mutlak maksimumun %92'si.

##### 🔴 ARIZA DEĞİL AMA "ÇALIŞIR MI" SORUSUNUN CEVABI — tamponun CM tavanı

B15'in arıza taraması sırasında çıkan, arıza **olmayan** ama tasarımın
işleyip işlemeyeceğini doğrudan belirleyen bulgu: **her iki gerilim kanalı
da tam ölçekte LM358'in garantili ortak-mod giriş aralığının sınırında
çalışıyor.**

LM358'in CM tavanı: TI 25 °C'de `V+ − 1.5 V`, onsemi `V+ − 1.7 V`,
TI tam sıcaklık aralığında `V+ − 2.0 V`.

| kanal | +5 V rayı | CM tavanı | FS düğümü | pay | CM tavanı FS'in kaç katında |
|---|---|---|---|---|---|
| NORMAL ±32 V | 5.00 V | 3.000 V | 2.688 V | 312 mV | 1.37× |
| NORMAL ±32 V | **4.75 V** | 2.750 V | 2.688 V | **62 mV** | 1.12× |
| YÜKSEK ±613 V | 5.00 V | 3.000 V | 2.736 V | 264 mV | 1.26× |
| YÜKSEK ±613 V | **4.75 V** | 2.750 V | 2.736 V | **14 mV** | **1.02×** |

USB'nin +5 V toleransı 4.75–5.25 V. **Düşük uçta HV kanalının payı 14 mV** —
yani tam ölçeğin %2 üstünde tampon garantili aralığın dışına çıkıyor.
Parça ölmez; veri sayfası çıkışın **TANIMSIZ** olduğunu söylüyor —
okuma sessizce yanlış olabilir.

⚠ Sezgiye aykırı: **"düşük gerilim" kanalı, "yüksek gerilim" kanalından
göreli olarak daha güvenli.** Herkes 615 V bacağına odaklanıyor ama CM
tavanına önce HV kanalı çarpıyor.

**Üç çözüm ölçüldü (hiçbiri uygulanmadı — karar kullanıcının):**

1. **+5 V'u USB yerine regüle bir kaynaktan al** — 5.00 V garanti edilirse
   pay 264 mV'a çıkar. En ucuzu, ama +5 V'un ESP32'den gelmesi
   B1'deki güç sırası güvenliğini sağlıyor; değiştirilirse 5.12.24'teki
   B6 uyarısı devreye girer.
2. 🌟 **Tamponları MCP6002 (3.3 V RRIO, DIP-8) yap.**
   ⏸️ **KULLANICI KARARI (2026-09-09): şimdilik ALINMAYACAK.** "Belki daha
   sonra alırız ama unutmayalım." Yani bu satır **kapanmadı, ertelendi** —
   bir sonraki sipariş listesine mutlaka girsin. Kartın bugünkü hali bu
   parça olmadan da çalışıyor (F1'in 1K seri dirençleri ADS'i koruyor);
   MCP6002'nin çözdüğü şey ortak-mod tavanı payının 14 mV'a inmesi.
   **Ara çözüm (bedava): +5 V'u USB yerine regüle bir kaynaktan al** —
   5.00 V garanti edilirse pay 264 mV'a çıkıyor. CM aralığı raydan
   raya → sorun tamamen kalkar. **Üstelik iki sorunu daha çözüyor:**
   TI'ın 1 numaralı ADC koruma önerisini sağlar (op-amp beslemesi = ADC
   beslemesi, SLAA593 §2) ve F1'deki seri direnç gereksinimini de
   kaldırır — çünkü çıkış 3.3 V'u hiç aşamaz.
   **Bu, kullanıcıya sorulacak tek satın alma kalemi: 2 × MCP6002-I/P.**
3. Tamponları +12 V'tan besle — CM tavanı 10 V'a çıkar ama doymuş çıkış
   10.65 V olur ve ADS'i korumak için 1K yerine ~7K seri direnç gerekir.

##### Skop kanalının negatif kapsamı YOK

Skop bölücüsü (R20/R23) GND referanslı — gerilim kanallarındaki gibi VREF
ofseti **yok** (netlist: `R23.2 → GND`), ESP32'nin ADC'si de tek yönlü.
Negatif girişlerin tamamı D2 tarafından kırpılıyor. Skop kanalı
**0 … 45.5 V tek yönlü**.

Kart "çift yönlü ön uç" diye tasarlandı ama bu **yalnızca ADS kanalları
ve hızlı akım yolu** için geçerli. Bobin akımı ters dönen bir ölçümde
skop kanalı **kör**. SMPS anahtarlama düğümü genelde pozitif olduğu için
pratikte sorun çıkmayabilir — ama bilinerek kabul edilmeli.

##### Yan bulgu — B15 kapsamı dışı ama gerçek

**Hızlı akım yolunun bant genişliği belgelenenden düşük.** Şema notu
*"Hızlı yol RC'nin ARDINDAN çekilseydi 7.96 kHz'e hapsolurdu"* diyor ama
netlist'te R27/R29 zaten `SONT_P`/`SONT_N`'den, yani **R18/R19 + C4
süzgecinin ardından** taplıyor. Diferansiyel RC = 200 Ω × 100 nF →
**7.96 kHz**, Sallen-Key'in 16.55 kHz'inin altında. Yani gerçek darboğaz
Sallen-Key değil, kaynak RC'si. Ayrıca aynı RC, ADS akım kanalının
Nyquist'inin (430 Hz) **18.5 katı** üstünde — akım kanalında etkili bir
örtüşme süzgeci **yok** (gerilim kanallarında 53–56 Hz).

**Bu bir B16 işi**, B15 kapsamında değil — ama tasarımın "gerçekten
çalışıp çalışmayacağı" sorusunun bir parçası.

✅ **B16 bunu kapattı (5.12.26).** Ek olarak B16, buradaki tarifin
**eksik** olduğunu gösterdi: asıl zarar örtüşme *ve* reaktif yükteki
güç hatası (PF=0.5'te %155). Dirençli yükte fark matematiksel olarak
kendini götürdüğü için bu oturum onu göremedi.

---

#### 5.12.25 ✅ B11 — ±12 V RAYI ÇÖZÜLDÜ: 7912 orta nokta regülatörü (2026-09-09)

`uretim/sim3_besleme.py` · **23 doğrulama** · `dogrula3.py`'de **B11** adımı.
Şemaya **BLOK 9** olarak eklendi (J6, F1, U9, C16, C17, R40).

##### 🔴 DEVIR 5.12.23'ün planı ÇALIŞMIYOR

B15 o planı iki ayrı yerden kırmıştı; B11 bunu somutlaştırdı:

| | LM358 orta nokta tamponu | Gerçek gereksinim |
|---|---|---|
| Çekme (sink) akımı | 10 mA @25 °C, **5 mA @0–70 °C** | **15.0 mA** |
| Kapasitif yük | yayınlanmış tek spec **100 pF** (o da LM358B/BA) | **700 nF** (C9–C15) |

**Dengesizlik TEK YÖNLÜ:** hepsi +12 → yük → GND, yani orta noktadan
**çekilmesi** gerekiyor. Bu, parça seçimini doğrudan belirliyor.

##### ✅ Çözüm: 7912 — ve **stokta zaten var**

DEVIR 5.12.21 "7812 ×3, 7912 ×2 stokta **ama onları besleyecek şey yok**"
diyordu. 24 V kaynak ortaya çıkınca o engel kalktı.

```
7912 GND pini -> 24V+   (= kart +12 V)
7912 VI  pini -> 24V-   (= kart -12 V)
7912 VO  pini -> kart GND
```

Regülatör `V(VO) − V(GND pini) = −12 V` tutuyor, yani **kart GND'si 24V+'ın
tam 12 V altında**. −12 V rayı **regüle**, +12 V rayı ham (kaynağı izliyor).

**🔴 NEDEN 7912, 7812 DEĞİL — akım yönü.** 79xx çıkış pininden akım
**çeker**, 78xx **verir**. Dengesizliğimiz GND'den çekilmeyi gerektiriyor;
7812 ile kurulsaydı orta nokta yükselir ve regülasyon kaybolurdu.

| | LM358 | TLE2426 | **7912** |
|---|---|---|---|
| Çekme | 5 mA | 31 mA | **1500 mA** |
| Kapasitif yük | 100 pF sınır | haritalı | **istiyor zaten** |
| Koruma | yok | var | **akım sınırı + SOA + termal kapatma** |
| Stok | 8 adet | **yok** | **2 adet (REG004)** |

##### Çalışma noktası (hepsi `sim3_besleme.py`'de kural)

| | değer |
|---|---|
| Toplam regülatör akımı | 30.0 mA (dengesizlik 15 + boşaltma 12 + Iq 3) |
| Güç / Tj | 360 mW → **62 °C** (sınır 125) — **soğutucu gerekmiyor** |
| Giriş gerilimi | −24 V; karakterize aralık −15…−25 V |
| C16/C17 | 68 µF 50 V (C035 ×8) — veri sayfası 25 µF ister |
| R40 boşaltma | 1K **1/2W** (R030) → 12 mA > 5 mA minimum yük |

⚠ **Boşaltma direncinin YÖNÜ önemli:** +12 → GND. GND → −12 konsaydı
regülatörün yükünü **azaltırdı**, çoğaltmazdı.

⚠ **Kaynak %10 yukarı kayarsa** (26.4 V) karakterize aralık aşılır —
bozulmaz (mutlak sınır 35 V) ama regülasyon garantili değil.
**24 V kaynağın gerçek gerilimi ölçülmeli.**

##### 🔴 İKİ MONTAJ TUZAĞI — 79xx, 78xx'ten FARKLI

1. **Pin sırası:** 79xx = **GND-VI-VO**, 78xx = IN-GND-OUT.
   7912'yi 7812 gibi bağlamak GND ile girişi takas eder.
2. **TO-220 tabı VI pinine bağlı** (78xx'te GND'ye). Bizim bağlantımızda
   VI = −12 V rayı, yani **tab −12 V'ta**. Topraklanmış bir soğutucuya
   vidalanırsa −12 V kısa devre olur. Soğutucu zaten gerekmiyor.

##### ERC'de bir kural bilerek kapatıldı — ve yerine daha kesini kondu

7912'nin GND pini kart GND'sine değil **+12 V rayına** bağlı; bu,
topolojinin ta kendisi. ERC bunu anlayamıyor (`ground_pin_not_ground`).
O kural `.kicad_pro`'da kapatıldı, **karşılığında `netlist3_dogrula.py`
U9'un üç pinini de tek tek sınıyor** — ayrıca C16/C17 polaritesi, R40'ın
yönü ve F1'in yeri. Netlist denetimi 100 → **111**.

Ayrıca GND'nin PWR_FLAG'i kaldırıldı: o ağı artık U9'un VO pini **gerçekten**
sürüyor, bayrak bırakılsa iki "power output" çakışırdı.

##### B15'in besleme senaryoları yeni topolojiyle

- **B3 (ters polarite):** değişmedi — TVS koruyamıyor, **mekanik
  anahtarlama + 50 mA sigorta** şart (F1 şemada).
- **B5 (24 V yalıtımsız):** 7912'nin **iç akım sınırı + termal kapatması**
  var, LM358'de yoktu. Ama asıl tehlike değişmedi: kart GND'si şebeke
  toprağına bağlanıyor → prosedür (F10/5, ohmmetre ile doğrula).
- **B1 (±12 açık, +3V3 kapalı):** etkilenmiyor, kelepçe yolları ±12'den
  bağımsız. ✅ **B18/F12 ile donanımda KAPATILDI** (5.12.27): pay 18 mV →
  1930 mV ve artık TL431'den bağımsız.

##### 🔴 KARAR: 7805 EKLENMİYOR — ve bunun bir bedeli var

DEVIR 5.12.23 analog +5 V için 24 V'tan beslenen bir 7805 önermişti.
B15/B6 ve B11 bunun **üç ayrı sorun** açtığını gösterdi:

1. İki +5 V kaynağı paralel (USB + 7805) → geri sürme; 7805 için
   çıkış→giriş ters diyodu şart olur
2. **"+5 V var / +3V3 yok" hali mümkün hale gelir** — bu, B15/A1b'nin en
   kötü senaryosu (ADS beslemesizken tampon çıkışı sürüyor). Bugün bu hal
   *imkânsız*, çünkü ikisi de aynı yerden (ESP32 başlığı) geliyor.
3. Orta nokta dengesizliği 6.4 mA artar

**Karar: 7805 yok. +5 V, J5.8'den (ESP32 başlığı) gelmeye devam ediyor.**
`netlist3_dogrula.py` bunu bir kural olarak sınıyor (+5V ağında **tek**
kaynak pini olmalı) — ileride biri 7805 eklerse zincir kırmızıya döner.

⚠ **Bedeli:** kart **USB olmadan çalışmaz** (analog kısım +5 V istiyor).
Pil + Wi-Fi izolasyon yoluna geçilirse +5 V'u **o zaman** çözmek gerekecek
— ve o noktada yukarıdaki üç sorun yeniden masaya gelir. Muhtemel çözüm:
analog tarafı da MCP6002'ye geçirip +5 V'u tamamen kaldırmak (o zaman
yalnızca +3.3 V ve ±12 V kalır).

##### Konnektör 3 pin değil 2 pin — ve pil yolu bundan KAZANIYOR

DEVIR 5.12.23 "+12 / GND / −12" 3 pinli bir giriş önermişti, çünkü orta
noktayı **dışarıda** üretmek planlanıyordu (pil paketinin ortası ya da
dirençli bölücü). B11'de orta noktayı **kart** üretiyor, o yüzden girişe
yalnızca 24 V geliyor → **2 pin**.

**Pil yolu bozulmuyor, iyileşiyor:** 6 hücre seri = 24 V aynı konnektöre
takılır, paketin orta noktası **kullanılmaz** ve GND'yi 7912 tanımlar.
Yani hücre eşleşmesi artık GND'nin yerini belirlemiyor — **dengesiz
boşalan bir paket bile ölçümü kaydırmaz.** 5.12.23'ün "hücreler eşleşmiş
olmalı" uyarısı bu yüzden hafifliyor (ölçüm için; hücre ömrü için hâlâ
geçerli).

##### Alınacaklar

Yalnızca **50 mA cam sigorta + yuva**. 7912, kondansatörler ve boşaltma
direnci **stokta**.

---

#### 5.12.26 ✅ B16 — V/I SÜZGEÇ EŞLEŞTİRMESİ (2026-09-09)

`uretim/sim3_ortusme.py` · **41 doğrulama** (ngspice + kural) · `dogrula3.py`'de B16 adımı ·
şemaya **C18/C19/C20**, `netlist3_dogrula.py`'ye **5 yeni denetim**
(111 → 116).

⚠️ Bu adım da **tasarımı** sınıyor, kurulmuş bir kartı değil.

##### Sorun neydi

Wattmetre gücü **V × I** diye hesaplıyor. İki kanal aynı sinyali **farklı**
süzüyordu:

| Kanal | R | C | τ | kesim |
|---|---|---|---|---|
| gerilim / NORMAL | 28.60 k | 100 nF | 2.860 ms | **55.66 Hz** |
| gerilim / HV | 30.19 k | 100 nF | 3.019 ms | **52.72 Hz** |
| akım (B16 öncesi) | 200 Ω | 100 nF | 0.020 ms | **8037 Hz** |

Üç ayrı sonucu vardı:

1. **🔴 ÖRTÜŞME — geri dönüşü yok.** ADS'in Nyquist'i 430 Hz; akım kanalı
   onun **18.7 katı** üstünde süzülüyordu. 430 Hz ile 8 kHz arasındaki her
   şey banda katlanıyordu. 860 Hz'te zayıflama **−0.0 dB** — 20 dB kuralını
   geçmiyor. Katlanmış bir bileşen ölçüme girdikten sonra **firmware onu
   ayırt edemez.** C18'in asıl gerekçesi bu; faz eşleşmesi ikinci kazanç.
2. **REAKTİF yükte güç hatası.** 50 Hz'te V/I faz farkı **−41.6°**.
3. **Hızlı yolun bandı belgelenenden dar.** I_HIZLI 7.76 kHz, skop kanalı
   16.55 kHz — hem dar hem **eşitsiz** (5 kHz'te aralarında 31.9° fark).

##### 🔴 Neden bugüne kadar gözden kaçtı — matematiksel sebebi var

Tek kutuplu süzgeçte **|H| · cos(atan x) = |H|²**. Yani "gerilim süzülüyor,
akım süzülmüyor" ile "ikisi de aynı süzülüyor" **dirençli yükte aynı güç
okumasını verir** (betikte sayısal olarak doğrulanıyor: 0.553380 = 0.553380).
Dirençli yükteki eşleşme hatası **%0.44**. Hata yalnızca **reaktif** yükte
ortaya çıkıyor — ve kullanıcının alanı SMPS/inverter, yani yük neredeyse
her zaman reaktif.

| Yük | okunan/gerçek | eşleşmiş/gerçek | **eşleşme hatası** |
|---|---|---|---|
| dirençli (PF=1) | 0.551 | 0.553 | **−0.4 %** |
| PF=0.87 (30°) | 0.833 | 0.553 | **+50.6 %** |
| PF=0.50 (60°) | 1.398 | 0.553 | **+152.5 %** |
| PF=0.26 (75°) | 2.375 | 0.553 | **+329.2 %** |

##### Çözüm — B15/F2'nin aynı mantığı

Süzmeyi **paylaşılan** düğümden alıp **ADS'in kendi koluna** taşımak.
B15/F2 *korumayı* ADS koluna koymuştu (R38/R39); B16 *süzgeci* koyuyor.

```
sont -[R18/R19]-+- SONT_P/N -[R38/R39 1K]-+- ADS
                |                          |
             C4 1nF                    C18+C19+C20
           (yalnızca RF)                 1.320 µF
                |
        hızlı yol (R27/R29) BURADAN taplıyor
```

| Parça | Değer | Envanter |
|---|---|---|
| **C4** (değişti) | 100 nF → **1 nF** | C049 ×10 |
| **C18** (yeni) | 1 µF | C023 ×5 (400 V polyester) |
| **C19** (yeni) | 220 nF | C052 ×10 (63 V) |
| **C20** (yeni) | 100 nF | C008 ×24 (50 V) |

**Satın alınacak hiçbir şey yok.** İdeal değer 1.300 µF (NORMAL menzile
göre); seçilen 1.320 µF.

##### Sonuçlar

| Ölçüt | önce | sonra |
|---|---|---|
| PF=0.5 eşleşme hatası @50 Hz — NORMAL | %155 | **%1.91** |
| aynı, 5–400 Hz en kötü | — | %2.18 |
| PF=0.5 eşleşme hatası @50 Hz — HV | %164 | **%5.31** |
| aynı, 5–400 Hz en kötü | — | %6.04 |
| V/I faz farkı @50 Hz (NORMAL) | −41.6° | **+0.42°** |
| akım kanalı örtüşme kesimi | 7958 Hz | **54.8 Hz** (Nyquist 430) |
| I_HIZLI −3 dB | 7.76 kHz | **16.52 kHz** (skop 16.55) |
| skop↔akım faz farkı @5 kHz | 31.9° | **0.39°** |

##### 🔴 B16'nın kendi bulduğu üç yeni şey

**(a) İki GERİLİM kanalı da birbirine eşit değil.** NORMAL 2.860 ms,
HV 3.019 ms — **%5.6 fark**. Sebebi bölücülerin Thevenin'lerinin farklı
olması (6.60 k / 8.19 k), ikisine de aynı 22K + 100 nF konması.
**Tek bir C18 ikisine birden tam eşleşemez**; seçilen 1.320 µF iki
menzilin ideali (1.300 / 1.372 µF) arasında duruyor. HV menzilindeki
%5.31 artık bundan.

Ayrıca `tasarim3_sabit.py`'deki `RC_R` yorumu **eskimişti**: "yalnızca
NORMAL kanal … HV Thevenin 21.96 kΩ, oraya seri direnç EKLENMİYOR"
diyordu. O not **2.2M'lik eski HV bölücüsüne** aitti; 6×820K/8.2K'ya
geçilince Thevenin 8.19 kΩ'a düştü ve R17 şemaya **eklendi**.
`tasarim3.py` ve `sim3_giris.py` zaten RC_R'yi her iki kanala uyguluyordu
— **not koda göre geride kalmıştı.** Düzeltildi.

**(b) 🔴 B16/F11 — hızlı yol, akım algılamasını YÜKLÜYOR.** R27/R29'un
diferansiyel giriş direnci 2×10K = 20 kΩ; bu, R18/R19 üzerinden akım
çekiyor ve şönt gerilimini ADS'e **ulaşmadan** bölüyor:

```
kayıp = (R18+R19) / (R18+R19+2×R27) = 200/20200 = %0.99
```

**Bu B16'nın getirdiği bir şey değil** — B8 (hızlı yol) eklendiğinde
oluştu ve **hiçbir adım modellemedi**. `tasarim2.py`'deki akım hata
bütçesi (h_i3, "Kelvin ile kalibrasyonsuz bile %1.5'in altında")
B8'den **önce** yazıldı; içinde bu kalem yok. Niteliği: **düz**
(frekanstan bağımsız) kazanç hatası — kalibrasyonla tamamen siliniyor,
B16'nın konusu olan faz eşleşmesini bozmuyor. Ama %1.5 bütçesinin
**%66'sını** tek başına yiyor.

Seçenekler (şema **değiştirilmedi**, karar kullanıcının):

| R27/R29 · R28/R30 | kayıp | kazanç |
|---|---|---|
| bugünkü 10K · 47K | %0.99 | 4.700 |
| 22K · 100K | %0.45 | 4.545 |
| 47K · 220K | %0.21 | 4.681 |
| ya da hiçbir şey yapma, kalibrasyona bırak | — | — |

**(c) 🔴 Baskın artık hata artık KONDANSATÖR TOLERANSI.** Yukarıdaki
sayılar nominal değerlerle. Gerçekte eşleşmeyi C2 ile C18'in **gerçek**
değerleri belirliyor; dirençler metal film %1, katkıları ihmal edilebilir.

| tolerans | en kötü τ sapması | 50 Hz Δfaz | PF=0.5 hata |
|---|---|---|---|
| ±%1 | ±%2 | 0.99° | %5.4 |
| ±%5 (J) | ±%11 | 3.27° | %15.4 |
| ±%10 (K) | ±%22 | 6.12° | %27.2 |

Monte Carlo (3σ = tolerans, 20 000 örnek): J ile ortanca %2.5 / %95 dilimi
%6.9; K ile ortanca %4.3 / %95 dilimi **%12.5**.

**Sonuç: nominal seçim değil tolerans belirliyor** — o yüzden 4. bir
kondansatörle 1.320 → 1.300 µF kovalamak sahte hassasiyet.
**Envanterde tolerans yazmıyor; parçanın üzerindeki harf okunmalı
(J = %5, K = %10).**

##### 🔴 Bedeller — dürüstlük bölümü

1. **ADS akım kanalının bandı bilerek düşürüldü** (8037 → 54.8 Hz). Kayıp
   değil: eski 8037 Hz zaten **kullanılamıyordu** (Nyquist 430 Hz) ve
   wattmetrede belirleyici olan **dar** kanal — gerilim kanalı zaten
   oradaydı. Üstü için hızlı yol var, o da 7.76 → 16.52 kHz'e çıktı.
2. **Hızlı yolun örtüşme payı düştü:** −30.6 dB → **−17.0 dB** (C4'ün
   kutbu yardım ediyordu). Ama skop kanalı zaten −16.1 dB — yani akım
   yolu artık skoptan **kötü değil**. Eskisi üstünlük değil **eşitsizlikti.**
   Yetersiz bulunursa çözüm **iki yola birden** eklenmeli.
3. **B16 hızlı yola ~55 Hz'te küçük bir BASAMAK koyuyor:** DC 0.9901 →
   plato 0.9010, yani **−0.82 dB (%9)**, en büyük faz çıkıntısı **2.71°**
   (öncesi bu bölgede 0.4°'nin altındaydı). **Kaldırılamaz:** basamağın
   büyüklüğünü R38/R39 belirliyor; onları büyütmek ADS'in **PGA'ya bağlı**
   giriş empedansı yüzünden oto-kademede kazanç sıçraması yaratır
   (1K'da %0.08→%0.28, 10K'da %0.83→%2.74). B15/F2'nin 1K seçimi doğru,
   basamak **kabul ediliyor** — hızlı yolun eşi ayrı bir konnektör (J4
   skop girişi), wattmetre çarpımı ADS yolunda yapılıyor ve basamak
   200 Hz üstünde tamamen oturmuş durumda.
4. **Ortak ölçek hatası KALIYOR:** 50 Hz'te iki kanal da 0.744 kazançla
   süzülüyor, güç 0.553 katı okunuyor (%45 düşük). **B16'nın çözdüğü şey
   bu değil.** Ama artık **yükten bağımsız** bir ölçek çarpanı (PF=1 ile
   PF=0.26 arası 2.7 puan) ve firmware'de 1/|H(f)|² ile silinebilir.
   B16 **öncesi bu mümkün değildi** — hata yükün güç faktörüne bağlıydı.
5. **SINIR: harmonikli yükte tek çarpan yetmez.** Süzgeç kutbu 50 Hz'in
   hemen üstünde; 5. harmoniğin gücü temele göre **11.7 kat** bastırılıyor.
   **ADS yolu bir TEMEL BİLEŞEN wattmetresidir.** Bu B16'nın getirdiği bir
   sınır değil — 860 SPS + 430 Hz Nyquist'in doğal sonucu ve gerilim
   kanalında zaten vardı; B16 akım kanalını da aynı sınıra getirerek
   **çarpımı anlamlı kıldı.** Dalga şekli/harmonik işi hızlı yolun.
6. **Yapılmadı: ortak-mod kondansatörleri.** C18 yalnızca diferansiyel
   süzüyor. Eklenmedi çünkü şönt yük dönüşünde (ortak-mod zaten GND'ye
   yakın), iki kondansatör daha delikli plakette yer + eşleşmezlik
   (CM→DM dönüşümü) riski demek, ve ADS'in kendi CMRR'i bu seviyede
   yeterli. Gerekirse 2 × 100 nF sonra eklenir.

##### Açık kalan iş kalemleri (B16'nın kapsamı dışı)

| # | İş | Neden |
|---|---|---|
| 1 | **firmware: menzil başına FAZ KALİBRASYONU** | 🔴 Tolerans artığının tek çözümü. **Referans cihaz gerekmiyor** — dirençli bir yük (rezistans/ampul) yeter: dirençli yükte gerçek faz farkı sıfır olmalı, okunan fark doğrudan süzgeç eşleşmezliğidir. 1°'ye kadar düzeltmek PF=0.26'da hatayı %6.5'e, PF=0.5'te %3.0'a indiriyor. Firmware'de Lagrange yarım-örnek hizalayıcı **zaten var** (B4/B5) — kesirli gecikme altyapısı mevcut |
| 2 | firmware: PGA değişiminde **13 örnek at** | Akım kolu τ = 2.90 ms, örnek aralığı 1.16 ms → 5τ = 13 örnek. Gereksinim **yeni değil**, gerilim kanalında zaten vardı |
| 3 | firmware: 1/H(f)² ölçek düzeltmesi | Yukarıdaki bedel (4). Yükten bağımsız olduğu için artık yapılabilir |
| 4 | **karar:** hızlı yolun örtüşme payı yeterli mi | Yukarıdaki bedel (2) |
| 5 | **karar:** B16/F11 — R27/R29 yüklemesi | Yukarıdaki bulgu (b) |

##### Analitik model ngspice'e karşı doğrulandı (bölüm 1b)

B16'nın bütün sayıları elle türetilmiş bir merdiven transfer fonksiyonuna
dayanıyor. Bölüm 1b onu **ngspice'te kurulmuş gerçek devreye** karşı
sınıyor — hızlı yolun fark yükselteci **sadeleştirilmeden** (R27/R28,
R29/R30 + ideal op-amp), şöntün alt ucu GND'de, yani sürüş **tek yönlü**.
Analitik model ise yükü tek bir 20 kΩ diferansiyel direnç sayıyor.

8 nokta (2 yapılandırma × 4 frekans), her birinde iki düğüm: **genlikte
en büyük sapma %0.001, fazda 0.0012°.** Yani fark yükseltecinin
asimetrisi diferansiyel sonucu değiştirmiyor — klasik fark yükseltecinin
diferansiyel giriş direnci gerçekten 2×R1. `RL`'yi 20k→40k yapınca 1b
kırmızıya dönüyor, yani denetim gerçekten bağlayıcı.

##### Mutasyon testi

Yeni denetimlerin gerçekten ısırdığı gösterildi:

| Mutasyon | Sonuç |
|---|---|
| C4'ü şemada 100 nF'a geri al | netlist **116→115** |
| C18/C19/C20'yi C4 düğümüne taşı | netlist **116→109** |
| `ADS_AKIM_C` 1.32 → 1 µF | B16 **41→30** |
| `SONT_C` 1 → 100 nF | B16 **41→34** |
| `RL` 20k → 40k (analitik modeli boz) | B16 **41→37** (ngspice çapraz denetimi) |

Ayrıca B15'in bulduğu **"boş iddia"** sınıfına karşı bilerek önlem alındı:
tek bir `True` ya da yalnız-literal karşılaştırma bırakılmadı. Malzeme
iddiası `envanter.csv`'yi **okuyor** (adetler elle yazılmıyor); PGA giriş
empedansları `PGA_TABLO`'dan geliyor; `|H|·cos(atan x) = |H|²`
özdeşliğinin bir de **negatif denetimi** var — aynı özdeşlik iki kutuplu
Sallen-Key'de tutmuyor (sapma 0.322), yani iddia gerçekten *tek-kutup*
özelliğini sınıyor, her şey için doğru bir totoloji değil.

---

#### 5.12.27 ✅ B18 — GPIO KELEPÇELERİ ve +3V3 GERİ BESLEMESİ (2026-09-09)

`uretim/sim3_kelepce.py` · **46 doğrulama** (ngspice + kural) ·
`dogrula3.py`'de B18 adımı · şemaya **R41**, R26/R33 değişti ·
`netlist3_dogrula.py` 116 → **123**.

⚠️ Bu adım da **tasarımı** sınıyor, kurulmuş bir kartı değil.

##### Kullanıcı F6'yı onayladı — B18 uygulamadan önce ölçtü ve F6 REDDEDİLDİ

Kullanıcı 2026-09-09'da B15/F6'yı ("kelepçelerin üst ucu +3V3 yerine
TL431 rayına") **onayladı**. B18 uygulamadan önce ölçtü ve **iki şey**
buldu:

**🔴 1. F6'nın belgelenmemiş bir bedeli var.** B15 yalnızca skop
menzilinden söz ediyordu (48.7 → 39.4 V). Ama **aynı kelepçe hızlı akım
yolunda da var** (D3, R33). Orada tam ölçek 294.6 mV şönt gerilimine
karşılık geliyor ve F6 onu **169 mV**'a düşürüyor — **%33 kayıp**.
Daha kötüsü: bu, ADS'in kendi kırpma noktasının (**256 mV**, PGA ±0.256)
**altına** iner. Yani hızlı yol, yavaş yoldan **önce** doyar — oysa hızlı
yolun varlık sebebi tepe yakalamak.

**🔴 2. F6 asıl kalıntıyı kapatmıyor.** TL431 açık devre olursa ray
9.9 V'a tırmanıyor ve ESP32 ölüyor — F6'yla da, F6'sız da. Sebebi: R1
(220R) TL_RAY ile +3V3'ü zaten köprülüyor.

##### Yerine uygulanan: B18/F12 — iki stok direnci

| Parça | Eski | Yeni | Envanter |
|---|---|---|---|
| **R26** (skop kelepçesi) | 2.7K | **10K** | R032/R033 ×10 |
| **R33** (hızlı yol kelepçesi) | 2.7K | **10K** | aynı |
| **R41** (YENİ, +3V3 → GND boşaltma) | — | **1K** | R029/R030/R031 ×10 |

**Satın alma yok.**

##### Sonuçlar

| Ölçüt | bugün | F6 | **B18/F12** |
|---|---|---|---|
| B1 payı (TL431 var) | **18 mV** | 1096 mV | **1930 mV** |
| B1 payı (TL431 açık devre) | **ÖLÜR** | **ÖLÜR** | **1930 mV** |
| skop menzili | 45.5 V | 39.4 V | **45.5 V** |
| hızlı akım tam ölçek | 252.1 mV | 169.1 mV | **252.1 mV** |

**🔴 En önemli özellik:** R41 rayı 2.495 V'un **altında** tuttuğu için
TL431 hiç iletmiyor — yani **kurtuluş artık TL431'e bağlı değil**.
B15 kurtuluşun "tesadüfi" olduğunu yazmıştı; B18 onu tasarıma çevirdi.
Bağımsızlık **0–85 °C boyunca** doğrulandı (en büyük fark 13 µV).

##### 🔴 En güçlü sonuç: iki koruma BİRBİRİNİ ÖRTÜYOR

Kabul ölçütü *"hiçbir TEK arıza ESP32'yi öldürmemeli"* idi. Eski tasarım
bunu **sağlamıyordu** — TL431'in açık devre kalması tek başına ESP32'yi
öldüren bir arızaydı. B18/F12 sonrası:

| Durum | 3V3 rayı | pay |
|---|---|---|
| sağlam | 1.670 V | 1930 mV ✅ |
| **TEK ARIZA:** TL431 açık devre | 1.670 V | 1930 mV ✅ (R41 devralıyor) |
| **TEK ARIZA:** R41 açık devre | 2.823 V | 777 mV ✅ (TL431 devralıyor) |
| ÇİFT ARIZA: ikisi de açık | 8.940 V | ölür |

**İki değişiklik ayrı ayrı değil, birlikte anlamlı:** R26/R33 10K'ya
çıkmasaydı, R41 açık devre halinde pay yine 18 mV'a düşerdi. 10K, R41'in
yedeğini güvenli seviyeye taşıyan şey.

##### Zorlama taraması (bölüm 3)

| Koşul | pay (TL431 var / yok) |
|---|---|
| nominal (TL072 tavan 10.5 V, 27 °C) | 1930 / 1930 mV |
| 24 V kaynak %10 yüksek → tavan 11.6 V | 1752 / 1752 mV |
| TL072 raya TAM oturuyor (12.0 V) | 1687 / 1687 mV |
| 0 °C / 60 °C | 1938 / 1921 mV |
| ölü 3V3 rayı 10k / 1k yüklüyor | 2056 / 2679 mV |

En kötü koşulda bile **1687 mV**.

##### 🔴 İki model hatası düzeltildi

**(a) TL431 akım VEREMEZ.** B15'in B1 modeli TL431'i ideal gerilim
kaynağı sayıyordu. Boşaltma direnci eklenince o model rayı 2.495 V'ta
**tutuyordu** — yani TL431 akım *veriyor*, fiziksel olarak imkânsız.
662 mV'luk sahte bir sonuç.

**(b) "İdeal-e yakın diyot" numarası sıcaklıkta kırıldı.** İkinci deneme
`.model D(IS=1E-9 N=0.02)` idi: 27 °C'de doğru, ama **60 °C'de ters
yönde iletti** (ray 1.67 yerine 2.33 V). Sebep: SPICE'ın diyot sıcaklık
modelinde doyma akımı `Eg/(N·Vt)` ile ölçekleniyor; N=0.02 o üsteli
50 katına çıkarıp IS'i patlatıyor. Üçüncü ve kullanılan model
**davranışsal tek yönlü şönt**: `I = max(0, V−Vref)/z_KA`.
*"Model parametresi sonuç değildir" kuralının canlı örneği.*

##### Yan bulgu: hangi sınır geçerli

B15 `ESP_MUTLAK_PIN_UST = 3.6 V`'u her yerde kullanıyordu. Doğrusu ikiye
ayrılıyor ([ESP32-S3 veri sayfası](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf), Absolute Maximum Ratings):

- **GPIO pini:** VDD + 0.3 V — beslemeyi **izleyen** bir sınır
- **Besleme pini:** 3.60 V **sabit**

B1'de zorlanan şey **besleme rayı**, o yüzden B15'in kullandığı ölçüt
doğruydu. Ama bu ayrım, kelepçenin **neden +3V3'te kalması gerektiğini**
de açıklıyor: seviye beslemeyi izliyor. TL_RAY'e taşınsaydı bu özellik
kaybolurdu.

##### 🔴 Yeni bulgu: kelepçe payı SOĞUKTA tükeniyor

Normal çalışmada (skop girişi aşırı menzilde) GPIO pini VDD+0.3'e ne
kadar yakın:

| Sıcaklık | 2.7K (bugün) | 10K (B18) |
|---|---|---|
| −10 °C | **−13 mV** (sınır aşılıyor) | +19 mV |
| 0 °C | +3 mV | +36 mV |
| 27 °C | +47 mV | +83 mV |
| 60 °C | +101 mV | +141 mV |

Yani 2.7K ile pay 0 °C civarında tükeniyor. **10K bunu da yaklaşık
ikiye katlıyor** — değişikliğin ikinci kazancı. (Bu hal yalnızca skop
girişi aşırı menzildeyken oluşuyor ve akım 3 mA'in altında kalıyor:
anlık ölüm değil, spek dışı zorlama.)

##### Seri direnci büyütmenin ADC tarafındaki bedeli (bölüm 4)

Üç risk ayrı ayrı ölçüldü:

| Risk | 2.7K | 10K | Ölçüt |
|---|---|---|---|
| Sızıntı ofseti (50 nA pin kaçağı) | 0.135 mV | **0.500 mV** | 12-bit LSB = 757 µV ✅ |
| Örnekleme oturması (τ) | 89 ns | **330 ns** | örnek aralığı 24 µs = 73× ✅ |
| Bant genişliği | 1786 kHz | **482 kHz** | Sallen-Key 16.55 kHz ✅ |
| Direnç gürültüsü | 0.95 µV | **1.83 µV** | LSB'nin 1/400'ü ✅ |

Düğüm kapasitesi **kötümser** alındı (33 pF: 2×BAT85 + pin + delikli
plaket kaçağı) — yani oturma sınavı gerçekte daha kolay.

R41'in sürekli maliyeti: **3.3 mA / 10.9 mW**. USB/LDO için önemsiz;
**pille çalışmada not edilmeli**.

##### B2'de bir iddia yeniden kuruldu

`sim3_giris.py`'deki *"TL072 kelepçesiz KABUL EDİLEMEZ"* iddiası **akım**
üzerine kuruluydu (>1 mA). Seri direnç 10K olunca akım 2.2 → **0.80 mA**'e
düştü, yani ölçütün altına. İddia **gerilim** üzerinden yeniden kuruldu:
kelepçesiz pin, ESP32'nin kendi ESD diyoduna dayanıp **3.958 V**'a
oturuyor; sınır VDD+0.3 = 3.60 V. **Kelepçe hâlâ şart** — ama artık
akım değil gerilim yüzünden. (Akıma bakıp "kelepçe gereksiz" demek
yanlış olurdu.)

##### Kutu kuralına 8. madde

> **8. AÇMA SIRASI: önce USB, sonra 24 V. Kapatırken önce 24 V.**

Donanımda B18/F12 ile çözüldü; bu kural **ikinci savunma** — bedava.

##### 🔴 BAĞIMSIZ DENETİM — B18'in ilk sürümünde 14 bulgu

B18'in ilk sürümü 30/30 yeşildi. İki bağımsız denetçiye (biri devre
akıl yürütmesi, biri saha/veri sayfası araştırması) verildi. **Ondan
fazla gerçek kusur çıktı; hepsi düzeltildi, doğrulama sayısı 30 → 46.**

**1. "18 mV payı" tek başına USB'yi çıkarmanın sonucu DEĞİL.**
B15/B1 iki TL072 çıkışını da doğrudan 10.5 V'a (doyma) koyuyor ve bunu
"açma sırasının doğal sonucu" diye sunuyordu. Eksik olan şey: **+5 V de
J5'ten geliyor**, yani USB çıkınca LM358'ler de ölüyor ve VREF ≈ 0
oluyor; op-amp çıkışları yalnızca **giriş sinyalinin** koyduğu yerde
durur. 10.5 V için skop girişinde ~**165 V** gerekiyor (belgelenen menzil
45.5 V'un 3.6 katı).

| op-amp çıkışı | ≈ J4 girişi | B18 öncesi pay | B18 sonrası |
|---|---|---|---|
| 1.0 V | 16 V | 2744 mV | 3463 mV |
| 2.9 V (tam ölçek) | 45 V | ~1100 mV | ~3150 mV |
| 7.0 V | 110 V | 506 mV | 2497 mV |
| 10.5 V (doyma) | 165 V | **18 mV** | **1930 mV** |

Senaryo yine de gerçek ve **tasarlanmış** bir hal — kutu kuralı zaten
"HV bağlıyken USB TAKILI OLMAYACAK" diyor ve B15/A9 skop girişine 615 V
uyguluyor. Ama gerekçesi "açma sırası" değil, **"aşırı menzilli giriş +
USB çıkık"**.

**2. 🔴 Kelepçe payı, veri sayfasının EN KÖTÜ Vf'i ile ZATEN NEGATİF.**
`tasarim3_sabit.py` kendi kuralını yazıyor: *"SPICE modeli TİPİK değerleri
veriyor; en kötü durum V_F MAKS tablosundan okunur."* B18'in ilk sürümü
bu kurala uymuyordu. Tabloya geçilince sonuç **işaret değiştiriyor**:

| R | I | Vf maks | GPIO | sınır (VDD+0.3) | pay |
|---|---|---|---|---|---|
| 2.7K | 2.54 mA | 0.352 V | 3.652 V | 3.600 V | **−52 mV** |
| 10K | 0.69 mA | 0.307 V | 3.607 V | 3.600 V | **−7 mV** |

Yani aşırı menzilde GPIO, tavsiye edilen koşulun üstünde — **B18'in
getirdiği bir kusur değil, zaten vardı**; 10K aşımı 7 kat küçültüyor.
İlk sürümdeki *"10K bu payı da büyütüyor, değişikliğin ikinci kazancı"*
cümlesi tipik-model artefaktıydı, **kaldırıldı**.

**3. 🔴 Kaçak hatası R ile büyüyor — değişikliğin gerçek bedeli.**
İlk sürümün §4'ü hiç simülasyon içermiyordu ve **R ile ölçeklenen tek
hata terimini atlamıştı**. Ölçüldü:

| | 2.7K | 10K |
|---|---|---|
| 25 °C | 0.57 mV (0.8 LSB) | **2.01 mV (2.7 LSB)** |
| 60 °C | 7.96 mV (10.5 LSB) | **19.9 mV (26.3 LSB, %0.64 FS)** |

İki diyot ters yönde kaçırdığı için bu bir ofset değil, menzilin iki
ucuna doğru büyüyen bir **eğrilik**; sıcaklıkla ~10 °C'de bir ikiye
katlanıyor, yani tek seferlik kalibrasyon silmez. Yalnızca **skop**
kanalını etkiliyor (ADS kanalları bu yoldan geçmiyor).

**Bu yüzden R artık varsayılmıyor, süpürülüyor:**

| R | B1 payı (R41 var) | B1 payı (R41 AÇIK) | kelepçe payı | kaçak 25 °C | kaçak 60 °C |
|---|---|---|---|---|---|
| 2.7K | 588 mV | **18 mV** | −52 mV | 0.57 mV | 7.96 mV |
| 4.7K | 969 mV | 440 mV | −33 mV | 0.98 mV | 12.1 mV |
| 6.8K | 1321 mV | 632 mV | −20 mV | 1.40 mV | 15.6 mV |
| **10K** | **1930 mV** | **777 mV** | **−7 mV** | **2.01 mV** | **19.9 mV** |
| 15K | 2422 mV | 883 mV | +7 mV | 2.92 mV | 25.1 mV |
| 22K | 2766 mV | 952 mV | +20 mV | 4.10 mV | 30.7 mV |

İlk üç sütun R ile **iyileşiyor**, son iki sütun **kötüleşiyor**. 10K bir
**takas** — tek yönlü bir iyileştirme değil.

**4. 🔴 Örnekleme penceresi — kapatılamayan tek kalem.**
İlk sürüm oturmayı **örnekler arası** 24 µs'ye karşı ölçüyordu. Yanlış
ölçüt: oturmanın **örnekleme penceresi** içinde bitmesi gerekiyor.
ESP32-S3'ün penceresi **Espressif tarafından yayınlanmamış** (arandı,
yok). Kanal değişiminde tutma kondansatörü *öteki kanalın* gerilimiyle
geliyor → en kötü 91 mV'lık bir sıçrama:

| pencere | 2.7K artık | 10K artık |
|---|---|---|
| 250 ns | 6.0 mV | **43.7 mV** |
| 500 ns | 0.4 mV | **21.0 mV** |
| 1 µs | 0.002 mV | 4.8 mV |

**Bu kalem açık bırakıldı.** Risk yeni değil (2.7K'da da vardı), 3.7 kat
büyüyor. Tezgah testi tanımlandı: GPIO4'e 0 V, GPIO5'e tam ölçek ver,
sonra ters çevir; kanaldan kanala kayma varsa pencere yetmiyordur.

**5. 🔴 Standart çözüm bu kartta UYGULANAMAZ — ve sebebi belgelendi.**
Espressif ADC pinlerine **0.1 µF** öneriyor ve veri sayfasındaki DNL/INL
(±4/±8 LSB) rakamları **"pine 100 nF bağlı"** koşuluyla verilmiş. TI
SPNA061 daha gevşek bir ölçüt veriyor: C ≥ (2^13−1)·C_sh = **8.2 nF**.
Ama:

| C | 2.7K kutup | 10K kutup |
|---|---|---|
| 8.2 nF | 7.19 kHz | 1.94 kHz |
| 100 nF | 0.59 kHz | 0.16 kHz |

Sallen-Key bandı **16.55 kHz**. **En gevşek öneri bile bandın altında.**
Yani hızlı yol, Espressif'in karakterize ettiği koşulda çalışamaz —
ESP32 ADC'siyle 16.5 kHz istemenin bedeli bu. Karar: bant korunuyor,
oturma belirsizliği tezgahta ölçülecek.

⚠️ **Ve bir tuzak:** o kondansatör ileride eklenirse V ve I kanallarına
**aynı R ve aynı C** konmalı. 100 nF + 10K = 159 Hz kutup, 50 Hz'te 17°
faz — **B16'nın tekrarı** olurdu.

**6. 🔴 Yeni bulunan yol: modülün LDO'suna ters akım.**
ESP32 modülünün 3V3 pini bir **LDO çıkışı**. Raya akım basmak onu kendi
girişinin üstüne çıkarıyor. TI SSZT658: *"ters akım ısınma,
elektromigrasyon ya da latch-up ile cihazı bozabilir."* ROHM 66AN115E
aynı şeyi söyleyip harici koruma diyodu istiyor. Üstelik LDO'nun gövde
diyodu üzerinden **+5 V ağına** da geçer — ve bu kartın analog +5 V'u
aynı modülden geliyor. **B15 de B18'in ilk sürümü de bu yolu görmemişti.**
B18/F12 LDO'ya binen gerilimi 3.582 → 1.670 V'a indiriyor: aranmamış ama
kazanılmış bir yan fayda.

**7. 🔴 ESP32-S3 veri sayfası pin sınırı YAYINLAMIYOR.**
Tablo 14 (Absolute Maximum Ratings) yalnızca **besleme pinini**
(−0.3…3.6 V), toplam IO çıkış akımını ve saklama sıcaklığını veriyor.
**Hiçbir pin için mutlak azami giriş gerilimi ve hiçbir pin için
enjeksiyon akımı sınırı yok.** Elimizdeki tek sınır "Recommended
Operating Conditions"taki V_IH maks = VDD+0.3. Karşılaştırma: ST, STM32
için ikisini de yayınlıyor ve **ADC'si etkin pinlerde enjeksiyonu açıkça
yasaklıyor**. Sonuç: 2. maddedeki "sınır aşılıyor" ifadesi **tavsiye
edilen koşul** aşımıdır, mutlak azami aşımı değil — ne kadar tehlikeli
olduğu **belgelenemiyor**.

**8. Bu arıza tipi belgelenmiş; bizim çözümümüz belgelenmemiş.**
Microchip *3V Tips'n Tricks* TIP #11: *"diyot kelepçe 3.3 V beslemesine
akım enjekte eder… **hafif yüklü** 3.3 V raylarında bu akım rayı 3.3 V'un
üstüne çıkarabilir."* TIP #17 aynısını analog hal için tekrarlıyor ve
seri direnç için tam bizim takasımızı yazıyor. TI SLVAEX7A'nın şekil
2-2'sinin başlığı zaten *"Input Current Path of a Back-Powered Op Amp"*.

**Ama "ölü raya boşaltma direnci" öneren bir üretici notu bulunamadı.**
Belgelenmiş çözümler: op-amp'i ADC'nin kendi beslemesinden çalıştır
(TI SLAA593, "en basit yol" — **bu kartta uygulanamaz**, TL072 ±12 V'ta
çünkü Sallen-Key VREF etrafında ±1.385 V salınmalı); transistörlü kelepçe
(TIP #11); GND'ye zener (TIP #17); op-amp'li hassas kelepçe (TIP #17);
seri direnci mikroamper düzeyine göre boyutla; ölü rayı yüzer bırakma;
besleme sırası kuralı (ADI). **Bizim çözümümüz 5. + 6.'nın yumuşak
hali** ve dayanağı EDN/ADI'nin şartı: *"ADC besleme rayı kelepçe akımını
soğurabilmeli."* Türevdir, alıntılanmış değil — **böyle yazıldı**.

**9. Akım nereye gidiyor — ölçüldü.** TI'in "≤1 mA" ölçütü **çipin kendi
ESD yapısına** giren akım için. Ölçüldü: BAT85'ten **1.72 mA**, ESP32'nin
ESD diyodundan **0.044 µA** (%0.0025). Schottky, silisyum ESD diyodundan
çok daha alçakta ilettiği için çipe pratik olarak akım girmiyor —
B15'in BAT85'i 1N4148'e tercih etmesinin sebebi tam bu.

**10. İki iç tutarsızlık.** (a) Menzil iddiaları `SKOP_TAVAN` (3.1 V)
kullanıyordu; B15 ise `ESP_ADC_ETKIN_UST` (2.9 V — Espressif'in etkin
aralığı, üstü *"undefined"*). İki betik ayrışıyordu; B18 2.9 V'a
geçirildi. Skop menzili **45.5 V**, hızlı akım tam ölçek **252.1 mV**
(F6 kaybı %43 değil **%33**). (b) `menzil()` seri dirence hiç bakmıyordu.

**11. Düzeltilen küçükler.** §5'te aynı simülasyon iki farklı etiketle
koşuyordu (kaldırıldı); gürültü hesabı R26'yı Sallen-Key'in *önünde*
sanıyordu — doğrusu kT/C limiti, **11.2 µV ve R'den bağımsız**; `True`
ve `abs(x−x)` biçiminde totolojik iddialar kaldırıldı; kelepçe tavanı
kendi türetildiği sabite karşı sınanıyordu; ESP32 sınırının atfı yanlış
kaynağı gösteriyordu.

**12. TL431 KISA devre de sınandı** (açık devrenin öteki ucu): B1'de
zararsız (pay 3242 mV), ama normal beslemede **sessiz**: R1 üzerinde
49 mW ve VREF sıfıra düşer — hiçbir şey yanmaz, **her ölçüm bozulur**.
R1 sigorta gibi açılmaz.

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| R41'i şemadan çıkar | netlist **123→118** (5 denetim) |
| R26'yı şemada 2.7K'ya döndür | netlist **123→121** |
| `BOSALTMA_R_3V3`'ü sonsuz yap (R41 yok) | B18 **46→40** |
| `R_SERI`'yi 2.7K'ya döndür | B18 **46→34** |

##### Kapanan kayıtlar

- **B15/F6** → ❌ değerlendirildi ve **reddedildi** (yukarıdaki iki sebep)
- **B15/B1** → ✅ **donanımla kapatıldı**, artık TL431'den bağımsız
- **B15'in "TL431 açık devre olursa ESP32 ölür" kalıntısı** → ✅ kapandı

---

#### 5.12.28 ✅ B19 — OSİLOSKOP KANALI ÇİFT YÖNLÜ (2026-09-09)

`uretim/sim3_skop.py` · **24 doğrulama** (ngspice + kural) ·
`dogrula3.py`'de B19 adımı · şemada R23, firmware'de dönüşüm,
arayüzde protokol · `netlist3_dogrula.py` 123 → **128**.

**Kullanıcı isteği:** *"Osiloskop tek yönlü değil çift yönlü istiyorum."*
Seçenekler sunuldu, kullanıcı **2.7K + alt uç VREF**'i seçti.

##### Sorun ve çözüm

ESP32'nin ADC'si yalnızca 0–2.9 V okuyor, eksi göremiyor. Skop
bölücüsünün alt ucu **GND'deydi**, o yüzden kanal tek yönlüydü.

Çözüm, gerilim kanallarının **zaten kullandığı** hilenin aynısı:
bölücünün alt ucunu GND yerine **VREF'e** (1.7153 V) bağlamak.

| | oran | menzil | adım |
|---|---|---|---|
| önce (R23 6.8K, GND) | 15.71 | 0 … +45.5 V **tek yönlü** | ~~11.1~~ **11.9** mV |
| **sonra (R23 2.7K, VREF)** | **38.04** | **−63.5 … +46.8 V** | ~~26.9~~ **28.8 mV** |

Artı taraf **daralmadı** (hatta 1.3 V büyüdü); 63.5 V eksi kazanıldı.
**Bedeli çözünürlük:** adım 2.4 kat büyüdü.

> 🔴 **B20 DÜZELTMESİ (2026-09-10):** buradaki adım sayıları yanlıştı.
> `SKOP_ADIM` "etkin aralık"tan (2.9 V) türetiliyordu, oysa adım bir
> **LSB**'dir ve nominal tam ölçekten (3.1 V) türer — firmware ve arayüzün
> üç kopyası zaten 3.1 kullanıyordu, ayrışan bu dosyaydı (**%6.92**).
> Doğrusu **11.9 → 28.8 mV**. Menzil satırları etkilenmiyor. Ayrıntı
> **5.12.30/(b)**.

Menzil simetrik değil çünkü VREF (1.7153 V), ADC penceresinin (0–2.9 V)
ortasında değil. Simetrik kullanılabilir bölüm **±46.8 V**.

##### 🔴 B19 kendi hatasını yakaladı — dönüşüm formülü yanlıştı

İlk yazdığım dönüşüm `V = (V_adc − VREF) × N` idi. Bölüm 1'deki **"0 V
giriş"** satırı bunu ortaya çıkardı: 0 V giriş **−65.2 V** okuyordu.

Doğrusu bölücünün gerçek denklemi:

```
V_düğüm = VREF + (V_giriş − VREF) · R23/(R20+R23)
V_giriş = VREF + (V_düğüm − VREF) · N  =  V_düğüm·N − VREF·(N−1)
```

Yani ofset **VREF×N değil, VREF×(N−1)** — 63.53 V. Baştaki `+VREF`
terimi unutulmuştu. Düzeltildi ve **kalıcı olarak kilitlendi**: bölüm 4b
devreyi ngspice'te kurup düğümü okuyor, firmware'in formülünü uyguluyor
ve girişe eşit çıktığını sınıyor (en büyük hata **0.2 mV**, bir ADC
adımı 26.9 mV). Ayrıca bölüm 3 formülün metnini hem firmware'de hem
arayüzde denetliyor.

##### Yeni akım yolu — asıl risk buydu, ölçüldü

Alt uç GND'deyken skop akımı toprağa gidiyordu. Artık **VREF'e** gidiyor
— ve VREF bütün kanalların referansı. Üç soru ölçüldü:

| Durum | VREF akımı | VREF sapması |
|---|---|---|
| tam artı menzil (+46.8 V) | −0.42 mA | — |
| tam eksi menzil (−63.5 V) | +0.65 mA | **4.5 µV** |
| 325 V (şebeke tepesi) arıza | −3.15 mA | — |
| 615 V arıza | −5.97 mA | — |
| −615 V arıza | +5.32 mA | **< 5 µV** |

**🔴 Arızada bile VREF kaymıyor** — tamponun geri beslemesi akımı
yutuyor. Yani skop girişindeki bir arıza diğer kanalların okumasını
bozmuyor. (VREF'in tamponlu olmasının sebebi tam buydu; B19 o kararın
karşılığını aldı.) LM358'in çıkış akımı sınırı 40 mA, en kötü 5.97 mA.

##### İyi yan etki: Sallen-Key girişi daha az zorlanıyor

Oran büyüdüğü için aynı arıza gerilimi bölücü düğümünde daha küçük bir
gerilime dönüşüyor:

| giriş | önce | sonra | kazanç |
|---|---|---|---|
| 325 V | 20.71 V | **10.22 V** | 2.03× |
| 615 V | 39.16 V | **17.84 V** | 2.19× |

Yani B19 bu yönden **koruma ekliyor**. R20'nin 615 V'taki yükü ise
pratikte değişmiyor (%+4) — B15/A9'un "R20 gider" sonucu geçerli.

##### Alt kelepçe ilk kez iş görüyor

Kanal artık eksiye indiği için D2 devreye girebiliyor. Ölçüldü: tam eksi
menzilde (−63.5 V) düğüm **−0.000 V**, yani kelepçe eşiğinin içinde —
**kelepçe menzili kısmıyor**, yalnızca aşırısında devreye giriyor
(−80 V'ta −0.43 V).

##### Firmware ve arayüz

- `olcum3.h`: `SKOP_ORAN` 15.706 → **38.037**, yeni `SKOP_VOLT_OFSET`
- `.ino`: `hizli_olcekle()` ofsetli; yeni `skop_ofsetle()` `skop_olc()`
  çıktısını düzeltiyor (vmax/vmin/vort/vrms), `S2` satırına **9. alan**
- `arayuz3/app.js`: `voltOfset` okunuyor, yoksa 0 → **geriye uyumlu**
- `arayuz3/sahte-kart.js`: aynı ofset

**🔴 `skop_olc.h`'ye DOKUNULMADI.** O dosya Aşama 2'nin `olcum2.h`'sinden
üretilen birebir kopya ve `test_skop_ayni.py` karakter karakter
karşılaştırıyor. Ofset **çağıran tarafta** uygulandı; böylece Aşama 2'nin
A6 kanıtı Aşama 3 için geçerli kalmaya devam ediyor.

Hangi alan düzeltilmeli, hangisi dokunulmamalı — sayısal olarak
gösterildi (bölüm 4): **vpp ve vac ofsetten etkilenmiyor**; vmax, vmin,
vort ofset kadar kayıyor; **vrms** ise `√(vac² + vort²)` özdeşliğinden
tam olarak yeniden kuruluyor. Frekans/periyot/duty/yükselme zaman
büyüklüğü, tetik eşikleri verinin kendisinden türetiliyor — hiçbiri
etkilenmiyor.

##### Sabit ayrışması denetimi

Aynı sayı **dört yerde** duruyor. Bölüm 3 hepsini okuyup karşılaştırıyor:

| kaynak | oran | VREF |
|---|---|---|
| `tasarim3_sabit.py` | 38.037037 | 1.7153125 |
| `kod/olcum3.h` | 38.037037 | 1.7153125 |
| `arayuz3/sahte-kart.js` | 38.037037 | 1.7153125 |
| şema (netlist) | R23 = 2.7K | R23.2 → /VREF |

Ayrıca `tasarim3.py`'de elle yazılmış bir kopya (`SKOP_ORAN_ =
15.70588235`) bulundu ve sabitler dosyasına bağlandı — **zaten
ayrışmıştı**.

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| Şemada R23'ü 6.8K'ya döndür | netlist kırmızı |
| Şemada R23'ün alt ucunu GND'ye döndür | netlist **4 denetim** kırmızı |
| Firmware oranını eski bırak | B19 kırmızı |
| Ofseti VREF×ORAN'a döndür | B19 kırmızı |

##### Montaj uyarısı (kılavuza eklendi)

> ⚠️ **R23'ü GND'ye lehimleme.** Şemada VREF'e gidiyor; GND'ye takılırsa
> kanal sessizce tek yönlü kalır ve okumalar 64 V kayar.

---

#### 5.12.29 ✅ B17 — ADS YOLUNDA EŞ ZAMANLILIK + SÜZGEÇ DÜZELTMESİ (2026-09-09)

`uretim/sim3_senkron.py` · **26 doğrulama** · `test_olcum3.py` 70 → **87**
(AVR emülatöründe gerçek kod) · `dogrula3.py`'de B17 adımı ·
firmware, `tipler3.h` ve arayüz güncellendi.

B16 üç firmware kalemi bırakmıştı. Onları ele alırken **çok daha büyük**
bir kusur çıktı.

##### 🔴 ANA BULGU: iki ADS birbirinden bağımsız koşuyordu

Firmware'in kendi yorumu şunu iddia ediyordu:

> *"İki AYRI ADS1115 olduğu için V ve I **yaklaşık eş zamanlı**
> örnekleniyor. Tek çip ile kanal değiştirseydik aralarında 1.16 ms
> gecikme kalırdı."*

İkinci cümle doğru, **birincisi değil.** Kodun gerçekte yaptığı:

- iki çip de **SÜREKLİ** kipte, her biri **kendi iç osilatörüyle**
- ALERT/RDY yalnızca **akım** çipinde kurulu
- döngü akım çipinin ALERT'ini bekliyor, sonra ikisini de okuyor
- → **gerilim çipi kendi çevriminin neresindeyse orada**

ADS1115'in iç osilatör toleransı **±%10** (TI veri sayfası; 860 SPS
nominal → 774…946 SPS). Yani gerilim örneğinin yaşı **0…1.29 ms**
arasında ve **iki osilatör aynı olmadığı için sürükleniyor** — okuma
sabit bir yerde durmuyor, geziniyor.

**50 Hz'te bunun karşılığı 0…23.3 DERECE.** B16'nın düzelttiği süzgeç
eşleşmezliği 0.44° idi; **bu onun 53 katı.**

| Yük | en iyi | en kötü | ortalama |
|---|---|---|---|
| dirençli (PF=1) | 0.0% | −8.1% | **−2.7%** |
| PF=0.87 | 0.0% | −30.9% | −14.3% |
| **PF=0.50** | 0.0% | **−76.5%** | **−37.4%** |
| **PF=0.26** | 0.0% | **−155.5%** | **−77.4%** |

Kayma bütün aralığı taradığı için **ortalama alarak kurtulunamıyor.**

🔴 **Neden bugüne kadar görülmedi:** dirençli yükte hata yalnızca %2.7.
Kart dirençli bir yükle denenirse **"çalışıyor" görünür.** (B16'daki
`|H|·cos = |H|²` özdeşliğiyle aynı sınıf bir gizlenme.)

##### Çözüm: eş zamanlı TEK ATIŞ

SÜREKLİ kip bırakıldı. Her ölçümde iki çipe de **ardı ardına** tek atış
başlatma komutu yazılıyor, sonra ikisi de okunuyor. Kalan kayma artık
osilatör farkı değil, iki I2C yazması arasındaki **sabit** süre
(400 kHz'te ~95 µs) — ve **bilinen** olduğu için silinebiliyor.

| | kayma | 50 Hz'te |
|---|---|---|
| önce (sürekli, iki osilatör) | 0…1292 µs, **sürüklenen** | 0…23.26° |
| sonra (tek atış) | ~95 µs, **sabit** | 1.71° |
| sonra + kesirli gecikme | — | **%0.011 hata** |

⚠️ **Kayma ölçülüyor, varsayılmıyor:** `micros()` ile iki yazma arası
gerçekten ölçülüyor. Örnek periyodu da ölçülüyor (döngü web sunucusu da
koştuğu için sabit hızlı değil) ve `d = t_kayma / T_gerçek`.

##### Kesirli gecikme genelleştirildi

Firmware'de Lagrange yarım-örnek hizalayıcı zaten vardı (`hizala_yarim`,
d = 1/2'ye **sabit**). B17 onu genelleştirdi: `hizala_kesirli(d, …)`.

🔴 **d = 1/2'de yeni fonksiyon eskisiyle BİREBİR aynı çıkıyor**
(AVR emülatöründe 64 rastgele giriş, en büyük fark **0.000e+00**) —
yani **B5'in kanıtı genel fonksiyona taşınabiliyor**. `hizala_yarim`
kaldırılmadı; hızlı yol onu kullanmaya devam ediyor.

Doğrulananlar (hepsi AVR'de gerçek kod): d=0 tam örneğe oturuyor,
d=1 bir sonrakine, DC kazancı her d için tam 1, ve **gerçek iş**:
PF=0.5'lik bir yükte 0.0817 örneklik bilinen bir kayma
0.236967 W → **0.249965 W** (hedef 0.250000) — hata **375 kat** azalıyor.

##### 1/|H(f)| ölçek düzeltmesi (B16'nın 3. kalemi)

50 Hz'te güç `|H_v|·|H_i| = 0.55` katı okunuyordu — **%45 düşük**.
B16 iki kanalı eşitlediği için bu artık **yükten bağımsız** ve frekans
bilinirse tam silinebiliyor.

| kol | τ | 50 Hz düzeltmesi |
|---|---|---|
| NORMAL | 2.860 ms | 1.3443× |
| YÜKSEK | 3.019 ms | 1.3781× |
| AKIM | 2.904 ms | 1.3536× |

Güç düzeltmesi (V×I) **1.82×**. İki gerilim kanalının τ'su **aynı
değil**, o yüzden düzeltme **kanal başına** yapılıyor (`Kanal3.tau`).

⚠️ **Frekans ölçülmüyor, AYARLANIYOR.** ADS yolu (860 SPS, 55 Hz süzgeç)
frekans ölçemez. Yeni komut **`f<Hz>`** — 0 = DC (düzeltme kapalı).
Yanlış ayar **öngörülebilir** bir hata yapar:

| gerçek f | 50 Hz ayarıyla hata |
|---|---|
| 45 Hz | +19.9% |
| 50 Hz | 0.0% |
| 60 Hz | **−19.9%** |

Düzeltme **yalnızca güce** uygulanıyor; ortalama V ve I ham kalıyor
(AC'de zaten ~0, DC'de düzeltme zaten 1).

##### Faz kalibrasyonu (B16'nın 1. kalemi)

Yeni komut **`F<örnek>`** — menzil başına kesirli gecikme, kalıcı ayarda
`faz_kal[2]` olarak saklanıyor. **Referans cihaz gerekmiyor:** dirençli
bir yükte gerçek faz farkı sıfır olmalı; okunan fark doğrudan süzgeç
eşleşmezliğidir. `F` tek başına mevcut değerleri gösteriyor.

Çözünürlük: 0.001 örnek adım = 50 Hz'te **0.0209°** — 1° hedefinin çok
altında.

##### ❌ B16'nın 2. kalemi GEÇERSİZ çıktı

B16 *"PGA değişiminden sonra 13 örnek atılmalı"* demişti. Firmware'e
bakınca: **PGA hiç değişmiyor.** İki gerilim kanalı da PGA ±1.024'te
sabit, akım kanalı ±0.256'da sabit; oto-menzil **KANAL** değiştiriyor,
PGA kademesi değil — ve bu bilerek böyle (DEVIR 4.14: giriş empedansı
PGA ile değişiyor, kazanç sıçraması kalibrasyonla silinemiyor).

Kanal değişiminde ilk dönüşümü atma işi ise `menzil_uygula()`'da
**zaten doğru yapılmış** (1300 µs bekleme + bir okuma atma).

**B16 bu kalemi firmware'e bakmadan yazmıştı; B17 doğruladı ve kapattı.**

##### Kalıcı ayar imzası değişti

`Ayar3` büyüdüğü için imza **0xC0F3 → 0xC0F4**. Eski NVS kaydı sessizce
yanlış okunmayacak.

> 🔴 **B20 DÜZELTMESİ (2026-09-10):** bu yarım uygulanmıştı. Yalnızca
> `tipler3.h` değişmişti; `.ino`'daki `ayar_yukle`/`ayar_kaydet` elle
> `0xC0F3` yazmaya devam ediyordu — **NVS'e hep eski imza gidiyordu, damga
> hiçbir şey korumuyordu.** Tek kaynağa bağlandı: `#define AYAR3_IMZA`.

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| Sürekli kipe dön | B17 **26→25** |
| Ölçek düzeltmesini kaldır | B17 **26→25** |
| `lagrange4` katsayısının işaretini boz | AVR **3 iddia** kırmızı |
| `suzgec_ters_kazanc` hep 1 dönsün | AVR **5 iddia** kırmızı |

##### 🔴 Tezgahta ölçülmesi gereken

I2C yazma süresi **hesap**. Gerçek kartta `micros()` ile ölçülüyor ama
o ölçümün doğruluğu (ve ESP32'nin Wire kütüphanesinin gecikmesi) ancak
tezgahta doğrulanır. Ayrıca tek atış kipinde gerçek örnekleme hızının ne
olduğu (döngü yükü + I2C) ölçülmeli — `D` satırındaki örnek sayısı bunu
zaten raporluyor.

---

#### 5.12.30 ✅ B20 — ÖRNEKLEME HIZI, BANT SINIRI ve MENZİL DAVRANIŞI (2026-09-10)

`uretim/sim3_bant.py` · **41 doğrulama** · `dogrula3.py`'de B20 adımı ·
firmware'de **7 düzeltme** · `tasarim3_sabit.py`, `sim3_skop.py`,
`sim3_senkron.py`, `arayuz3/app.js`, `arayuz3/sahte-kart.js` güncellendi.

⚠️ Bu adım da **tasarımı** ve **firmware'i** sınıyor, kurulmuş bir kartı değil.

> **Yöntem notu.** Bu adım 11 ölçüm ajanı + 49 adversaryel çürütme ajanıyla
> koşturuldu. **Çürütme katmanı 27 bulguyu reddetti** — aşağıdakiler ayakta
> kalan ve mutasyon testinden geçenler. Çürütücüler bu oturumun kendi
> mekanizma açıklamalarından **ikisini de düzeltti** (aşağıda "düzeltilen
> iddialar").

---

##### 🔴 ANA BULGU: kart 860 SPS'te değil ~91 SPS'te örnekliyordu

B17 ADS yolunu tek atış kipine aldı ve üstüne iki düzeltme koydu
(1/|H(f)| ölçek düzeltmesi + kesirli gecikme). **İddialarının hepsi
50 Hz'te ve 860 SPS varsayımıyla sınanmıştı.** İkisi de tutmuyordu.

İki ayrı kusur aynı yere vuruyordu:

**(1) `loop()`'un başında sürekli kipten kalma ÖLÜ bir bekleme.**

```c
if (!yeni_donusum_bekle(4000)) { delay(2); }   // <- ÖLÜ
Okuma3 o = olcum_al();                          // dönüşümü BU başlatıyor
```

Sürekli kipte bu bekleme döngünün **hız ayarlayıcısıydı** — doğru yerdeydi.
Tek atışa geçilince dönüşümü `olcum_al()` başlatıyor, dolayısıyla buraya
gelindiğinde **uçuşta dönüşüm yok**: bir önceki `olcum_al` iki yazmacı da
okumuştu ve tek atış kipi dönüşüm bitince kapanıyor. Yani bu bekleme
**ALERT kusursuz çalışsa bile her turda 4000 µs zaman aşımına düşüyordu.**

**(2) `COMP_QUE = 11b` — ALERT/RDY pini hiç etkin değildi.**

`setup()` doğru şeyi yapıyordu (Hi_thresh = 0x8000, Lo_thresh = 0x0000,
`INPUT_PULLUP`) ama **her ayar yazması** `ADS_KOMP_KAPALI = 0x0003`
gönderiyordu. TI SBAS444E §7.3.8, harfi harfine:

> *"Set the COMP_QUE[1:0] bits to any 2-bit value other than 11b to keep
> the ALERT/RDY pin enabled"*

ve yazmaç tablosu 11b için: *"Disable comparator and set ALERT/RDY pin to
high-impedance (default)"*. Yani pin yüksek empedansta kalıyor, dahili
pull-up ile hep HIGH okunuyor, `yeni_donusum_bekle` **hiçbir zaman**
başarılı olmuyordu.

| Senaryo | periyot | SPS | Nyquist |
|---|---|---|---|
| **B20 öncesi** (ölü bekleme + COMP_QUE=11b) | 11.0 ms | **91** | 45 Hz |
| yalnız COMP_QUE düzeltilse | 7.49 ms | 134 | 67 Hz |
| yalnız ölü bekleme silinse | 5.72 ms | 175 | 87 Hz |
| **B20 sonrası** (ikisi de) | 1.49 ms | **671** | 336 Hz |

**🔴 Varsayılan `sebeke_hz = 50` ayarı Nyquist'in ÜSTÜNDEYDİ** (45 Hz).
Firmware, `tipler3.h`, `olcum3.h` ve DEVIR'in dört ayrı yerinde "860 SPS"
yazıyordu; hiçbiri ölçülmemişti.

> **`delay(2)` neden tam 2000 µs değil:** Arduino-ESP32'de `delay(ms)` =
> `vTaskDelay(ms/portTICK_PERIOD_MS)`, tik 1 kHz. "Şu andan 2 tik" beklenir
> ve **tik sınırında** uyanılır. vTaskDelay dışı meşgul süre 9.72 ms olduğu
> için periyot **tam 11.000 ms'e kilitleniyordu** — ADS osilatörünün
> ±%10'undan bile bağımsız. (Bunu çürütme ajanı düzeltti; ilk hesap
> 11.72 ms / 85 SPS demişti.)

##### 🔴 TEK ATIŞIN BELGELENMEMİŞ BEDELİ

B17 sürekli kipten tek atışa geçerken bir bedel yazmadı: tek atışta I2C
yazma+okuma dönüşümle **serileşir**, sürekli kipte ise dönüşüm arka planda
akar. Tavan **671 SPS** — nominalin %78'i. Bu kaçınılmaz, ama yazılmalıydı.

Dürüst muhasebe:

| Tasarım | Hız | V/I kayması |
|---|---|---|
| Sürekli kip (B17 öncesi) | 860 SPS | 0…23°, **sürüklenen** |
| Tek atış (B17'nin tasarladığı) | **671 SPS tavan** | 95 µs, sabit |
| Tek atış (B17'nin **yazdığı** kod) | **91 SPS** | 95 µs, sabit |

##### 🔴 B17'nin kazanımı gerçek hızda YOKTU

Hizalayıcının PF=0.5'te sağladığı iyileşme (uzun ortalama):

| periyot | hizalayıcı kapalı → açık | kazanç |
|---|---|---|
| 11.0 ms (B20 öncesi) | +4.990% → +4.585% | **1.1×** |
| 5.72 ms | +4.991% → +0.332% | 15.0× |
| 1.49 ms (B20 sonrası) | +4.988% → −0.019% | **261×** |
| 1.163 ms (860 SPS) | +4.983% → −0.016% | 314× |

##### 🔴 `F` faz kalibrasyonu düşük hızda AKTİF ZARARLIYDI

Belgelenen yordam: *"dirençli yük bağla, okunan gücü en büyük yapacak
şekilde F ile ayarla"*. 11 ms periyotta f/fs = 0.55 ve orada Lagrange
süzgecinin **kazancı** d ile güçlü değişiyor — arama fazı değil kazancı
kovalıyor. Gerçek kod AVR emülatöründe: yordam `faz_kal ≈ −0.265`'e
gidiyor ve dirençli yükte 0.5000 yerine **0.5796 okuyor (+%15.9 hata,
hem de kalibrasyon yükünün ta kendisinde)**. Hız düzeltilince bu kendi
kendine kapanıyor.

---

##### 🔴 FAZ KALİBRASYONU TEK FREKANSTA — asıl sınır burası

Kullanıcının 3. sorusu. `F<örnek>` **sabit bir ZAMAN gecikmesi** saklıyor;
düzelttiği şey ise iki RC'nin **arctan farkı**:

```
Δφ(f) = atan(2πf·τ_i) − atan(2πf·τ_v)      ← düzeltilmesi gereken
Δφ_kal(f) = 360·f·d·T                       ← F'in yaptığı (DOĞRUSAL)
```

Bu ikisi **yalnızca kalibrasyon frekansında** örtüşür. 50 Hz'te kalibre
edilmiş kartta kalan faz hatası (kondansatör toleransı — B16: envanterde
tolerans yazmıyor, parçanın üzerindeki harf okunmalı, J=%5 / K=%10):

| f | tol ±%1 | tol ±%5 | **tol ±%10** | PF=0.5 güç hatası (±%10) |
|---|---|---|---|---|
| 50 Hz | 0.00° | 0.00° | **0.00°** | %0.0 |
| 60 Hz | −0.20° | −0.65° | **−1.21°** | %3.7 |
| 100 Hz | −1.16° | −3.78° | **−7.04°** | **%20.5** |
| 200 Hz | −3.52° | −11.46° | **−21.39°** | **%56.3** |
| 400 Hz | (eski `f` sınırı) | | | **tamamen geçersiz** |

**Bağlayıcı kısıt beklendiği yerde değil.** Lagrange sarkması 100 Hz'te
671 SPS'te yalnızca %0.78; kartı sınırlayan şey **faz kalibrasyonu**.

**Sonuç: `f` üst sınırı 400 → 100 Hz'e çekildi**, ve 40–70 Hz dışında
firmware artık uyarı basıyor. Ölçülen geçerlilik: 40–70 Hz bandında,
±%10 tolerans köşesinde, PF=0.5'te en kötü **%8.0** güç hatası.

> **🔴 AÇIK TASARIM SORUSU (kullanıcı kararı).** Kalibrasyon sabit gecikme
> yerine **τ eşleşmezliği** olarak saklanırsa (ölçülen fazdan `τ_i_etkin`
> çözülüp her frekansta arctan farkı hesaplanırsa) bant genişler.
> Maliyeti iki `atanf()` — ESP32'de önemsiz. **UYGULANMADI:** `F`
> komutunun anlamını değiştirir ve tezgahta doğrulanmadan yapılmamalı.
> Ayrıca çürütme ajanının uyarısı: bulunan `τ_i_etkin` **ölçek
> düzeltmesinde kullanılmamalı**, yalnızca fazda.

---

##### 🔴 OTOMATİK MENZİL AC'DE KULLANILAMIYORDU

Eşikler **anlık |v|**'ye uygulanıyordu. Bir sinüsün genliği her yarım
çevrimde alt eşiğin (22.7 V) altına inip tepede üst eşiği (29.2 V) aşıyor.
Tepesi 29.2 V'i geçen **her** AC sinyalde bu bir döngü:

| tepe | ESKİ geçiş/s | ESKİ doyan örnek | YENİ geçiş/s | YENİ doyan |
|---|---|---|---|---|
| 25 V | 0 | %0.0 | 0 | %0.0 |
| 30 V | **198** | %0.0 | **1** | %0.0 |
| 50 V | **199** | **%12.2** | **1** | %1.2 |
| 100 V | **193** | %13.5 | **1** | %1.5 |
| 300 V | 65 | %5.0 | 1 | %2.1 |

Her geçiş `menzil_uygula()`'nın **1518 µs**'sini ödetiyor → örnekleme
hızının %30'u menzil değişimine gidiyordu. Eski yorum *"Aradaki boşluk
gidip gelmeyi (chatter) önlüyor"* diyordu; **DC'de önlüyor, AC'de
önlemiyordu.**

**Çözüm — iki asimetrik karar:**
- **YUKARI**: anlık |v| ile (hızlı olmalı, yoksa kanal doyar)
- **AŞAĞI**: bir şebeke çevriminde **tutulan tepe** ile (sinüsün tepesi
  çevrim boyunca sabittir; anlık değere bakınca "aşağı in" AC'de sürekli
  tetikleniyordu)
- üstüne bir **susturma**: geçişten sonra bir şebeke çevrimi boyunca
  yeni geçiş yok

**Bedeli:** gerçek bir DC düşüşünde NORMAL'e dönüş artık anlık değil, en
çok iki pencere (50 Hz'te 40 ms) sonra. Yukarı yön — yani doymayı önleyen
yön — hâlâ anlık.

---

##### 🔴 SSE akış işleyicisi `loop()`'u sonsuza kadar kilitliyordu

```c
while (c.connected()) { ...; delay(20); sunucu.handleClient(); }
```

`akis_sayfa()`, `loop()` içindeki `sunucu.handleClient()`'tan çağrılıyor.
İstemci bağlı kaldığı sürece geri dönmediği için **loop() de geri
dönmüyordu**: `olcum_al()` koşmuyor, enerji birikmiyor. Daha kötüsü
`son_satir[]`'ı **yalnızca `loop()`** yazdığı için akış ilk (bayat) satırı
gönderip **sonsuza kadar susuyordu** — işlev kendi amacını bile yerine
getirmiyordu. Ayrıca içerideki `handleClient()` aynı sayfayı **iç içe**
çağırabiliyordu.

Blokaj bitince `enerji_biriktir`'in `dt > 1 s` koruması devreye girip o
aralığı **atlıyor**: 1 dk @ 25 W → **0.42 Wh, yani birikmesi gereken
enerjinin %100'ü** sayaca hiç girmiyor.

Bugün pratikte erişilemiyor (`WIFI_AD` boş) ama kök sayfa kullanıcıyı
açıkça oraya yönlendiriyor ve B12 bu yolu açacak. **Durum makinesine
çevrildi:** işleyici yalnızca başlıkları yazıp hemen dönüyor, `loop()`
her `D` satırında saklanan istemciye yazıyor.

---

##### 🔴 `ortalama_oku()` ortalama ALMIYORDU

Tek atış kipinde çip dönüşüm bitince kapanır; yeni bir `OS=1` yazılmadıkça
dönüşüm yazmacı **değişmez**. Eski gövde hiçbir dönüşüm başlatmadığı için
16–32 okuma **aynı bayat değeri** okuyup "ortalamasını" alıyordu:
**gürültü azaltma tam sıfır**, üstüne komut başına 48–96 ms ölü zaman
aşımı. Dört kalibrasyon komutu da (`z`, `g`, `Z`, `i`) bunu kullanıyor —
yani **sıfır ve kazanç kalibrasyonları tek bir gürültülü örnekle**
yapılıyordu. Düzeltildi: her turda dönüşüm kendimiz başlatılıyor.

---

##### Ayrışmalar

**(a) `Ayar3` imzası yarım uygulanmıştı.** B17 "0xC0F3 → 0xC0F4, eski NVS
kaydı sessizce yanlış okunmayacak" dedi ama yalnızca `tipler3.h`'yi
değiştirdi; `.ino`'daki `ayar_yukle`/`ayar_kaydet` elle `0xC0F3` yazmaya
devam ediyordu. Yani **NVS'e hep eski imza gidiyor, sürüm damgası hiçbir
şey korumuyordu.** Tek kaynağa bağlandı: `#define AYAR3_IMZA 0xC0F4u`.

**(b) 🔴 Skop adımı dört dosyada, biri ayrışmış.** B19 "sabit ayrışması
denetimi" yapmıştı ama yalnızca `SKOP_ORAN` ve `VREF`'e baktı, **adımı
atladı**:

| kaynak | önce | sonra |
|---|---|---|
| `tasarim3_sabit.py` | 2.9 V / 4096 → 26.93 mV | 3.1 V / 4096 → 28.79 mV |
| `kod/olcum3.h` | 3.10 V / **4095** → 28.80 mV | 3.1 V / 4096 → 28.79 mV |
| `arayuz3/app.js` | 3.10 / **4095** | 3.10 / 4096 |
| `arayuz3/sahte-kart.js` | 3.10 / **4095** | 3.10 / 4096 |

**%6.92 ayrışma, hiçbir iddia görmedi.** Kök sebep kavramsal: `SKOP_ADIM`
ile `SKOP_MENZIL_*` **aynı sabiti** kullanıyordu, oysa ikisi farklı şeyler:

- `SKOP_MENZIL_*` → girişin **kullanılabilir üstü** (2.9 V; üstünde ESP32
  ADC'si doğrusallığını kaybediyor) — **doğru sabit buydu, değişmedi**
- `SKOP_ADIM` → bir ADC kodunun kaç volt ettiği, yani **LSB** = nominal
  tam ölçek / 4096

> ⚠️ **DEVIR 5.12.28'in "adım 11.1 → 26.9 mV" satırı bu yüzden yanlıştı.**
> Doğrusu **11.9 → 28.8 mV**. Menzil satırları (−63.5 … +46.8 V) etkilenmiyor.
>
> ⚠️ Bu denetim dördünün **aynı** olduğunu sınar, **doğru** olduğunu değil.
> 3.1 V bir veri sayfası nominali; ESP32 ADC'sinin gerçek tam ölçeği
> yongaya göre değişiyor ve doğrusal değil — **tezgahta kalibre edilmeli.**

**(c) `TAU_*` sabitleri sıkı bağlandı.** `test_olcum3.py` bunları 1e-3 s
**mutlak** toleransla sınıyordu; τ ≈ 2.9 ms olduğu için bu **%35 tolerans**
demek. B20 üçünü de `tasarim3_sabit.py`'ye %0.1 bağıl toleransla bağlıyor.

---

##### ❌ Totoloji temizliği

`sim3_senkron.py:191` şunu yazıyordu:

```python
r.kosul("B17-1: kalan kayma SABIT ve BILINEN", True is not False, ...)
```

`True is not False` her zaman doğru — **26 iddiadan biri boştu.** Yerine
iddianın kendisi sınanıyor: "kayma sabit" demek, kaymanın ADS
osilatörünün toleransından **bağımsız** olması demek. Sürekli kipte
yayılım %22, tek atışta %0.

> Bağımsız bir AST taraması zincirin tamamında **10 boş iddia** daha
> buldu; ayrıca kaynaksız BAT85/ADS1115 SPICE model parametreleri.
> **Bunlar B20 kapsamında düzeltilmedi** — ayrı bir iş kalemi (aşağıda).

---

##### Çürütme katmanının DÜZELTTİĞİ iki iddiam

Dürüstlük bölümü — bu oturumun kendi mekanizma açıklamaları yanlıştı:

1. **"Nyquist 43 Hz, 50 Hz katlanıyor → ölçüm bozuk"** — **DAYANAKSIZ.**
   Belirleyici kontrol deneyi: hizalayıcı kapalıyken uzun ortalama hatası
   85 / 93 / 133 / 175 / 671 / 860 SPS'te **aynı** (PF=1: −0.042%,
   PF=0.5: +4.99%). Sebep: bu bir **wattmetre**; v ve i eş anda
   örnekleniyor ve **çarpımın ortalaması** alınıyor. Örtüşme dalga şeklini
   bozar, çarpımın ortalamasını bozmaz — Nyquist ölçütü **yeniden
   yapılandırma** içindir. Gerçek zarar mekanizması **Lagrange
   hizalayıcının f/fs = 0.55'te çökmesi**.
2. **"860 SPS'te pencere dalgalanması sıfır"** — **YANLIŞ GENELLEME.**
   Sıfır olması periyodun tam 1/860 s olmasına bağlı (172 örnek = tam
   10 şebeke çevrimi); 946 SPS'te 0.169 W, 774 SPS'te 0.053 W. **Tesadüf,
   özellik değil.**

Buna karşılık **pencere kırpılması** bulgusu ayakta: 200 ms rapor
penceresine gerçek hızda yalnızca 19 örnek sığıyordu ve saf sinüste bile
güç okuması **±%5.2** geziniyordu (tasarım hızında ±%0.4).

---

##### Mutasyon testi

Her yeni iddianın gerçekten ısırdığı gösterildi:

| Mutasyon | Sonuç |
|---|---|
| `loop()`'a ölü beklemeyi geri koy | B20 **41→38** |
| `ADS_KOMP_TEK`'i 0x0003'e (11b) döndür | B20 **41→40** |
| SSE blokajını geri getir | B20 **41→38** |
| İmzayı tekrar ayrıştır (`0xC0F3`) | B20 **41→40** |
| `menzil_gozet`'i anlık karara döndür | B20 **41→40** |
| `ortalama_oku`'nun dönüşüm başlatmasını sil | B20 **41→40** |
| `f` sınırını 400 Hz'e geri çıkar | B20 **41→37** |
| `TAU_NORMAL`'i %20 boz | B20 **41→40** |
| Skop adımını dört dosyanın **her birinde ayrı ayrı** boz | dördü de B20 **41→40** |

---

##### 🔴 Tezgahta ölçülmesi gerekenler (B20'den)

1. **`D` satırındaki örnek sayısı.** 200 ms'de ~134 bekleniyor (671 SPS).
   ~19 çıkarsa B20 düzeltmeleri işe yaramamış demektir. **Bu, K1'in
   bedava tezgah testidir.**
2. **ALERT/RDY darbesi skopla görülmeli.** Tek atış + `COMP_POL=0`'da
   beklenen dalga şekli: boşta HIGH, dönüşüm boyunca LOW (~1.16 ms),
   hazır olunca HIGH ve **bir sonraki başlatmaya kadar HIGH** (darbe
   değil, mandal). Kaynak: RobTillaart/ADS1X15 issue #76, iki bağımsız
   osiloskop ölçümü. Veri sayfası bu konuda **kendisiyle çelişiyor**
   (§7.3.8 "asserts low at the end" vs §8.1.4 "outputs the OS bit").
3. **`/HAZIR` hattında harici pull-up YOK** (net = yalnız J5.6 + U6.2);
   ESP32'nin dahili ~45 kΩ'u kullanılıyor. Tek atıştaki **seviye**
   assert'i için yeterli; sürekli kipin 8 µs'lik darbesi için
   olmazdı. En kötü hal (80 kΩ + 100 pF uzun şerit) yükselme 11.1 µs.
   **Stokta 10K var** (B18'in R032/R033'ü) — gerekirse eklenir.
4. **`micros()` ile ölçülen `t_kayma_us` gerçekten ~95 µs mi.**
   `Wire.begin(..., 400000)` gerçekten 400 kHz kuruyor mu; 100 kHz'e
   düşerse kayma 4 kat büyür. (I2C süreleri saf bit sayımı — ESP32 Wire
   sürücüsünün işlem başına ek yükü sayılmadı; bu periyodu yalnızca
   **uzatır**, yani 671 SPS bir **üst sınır**.)
5. **Skop ADC'sinin gerçek tam ölçeği.** 3.1 V nominal; yongaya göre
   değişiyor ve doğrusal değil.
6. **Kondansatör toleransı.** C2 ve C18'in üzerindeki harf okunmalı
   (J=%5, K=%10) — faz kalibrasyonunun geçerlilik bandını bu belirliyor.

---

##### B20'nin AÇTIĞI iş kalemleri

##### ✅ B20'nin ikinci turu — riski olmayan kalemler KAPATILDI (2026-09-10)

| # | İş | Durum |
|---|---|---|
| 1 | **Karar:** faz kalibrasyonunu τ eşleşmezliği olarak sakla | 🔴 **AÇIK — kullanıcı kararı.** Bant 40–70 Hz'ten genişler; `F`'in anlamını değiştirir, tezgah gerekir. Bilerek yapılmadı |
| 2 | Zincirde kalan **boş iddialar** | ✅ **KAPANDI.** AST taraması 13 aday buldu; 4'ü meşrudu (if/else dalları), **9'u gerçek totolojiydi** ve hepsi ölçen testlere çevrildi |
| 3 | SPICE model parametreleri | ✅ **KAPANDI.** İddia kısmen yanlışmış: BAT85 (Nexperia) ve ADS ESD kaynaklı ve gerekçeli. **Gerçek boşluk:** skaler `ADS_ESD_VF` ile SPICE `D_ESD` birbirine bağlı değildi — bağlandı (B20/6d) |
| 4 | `f` ve `F` komutları **arayüzde yok** | ✅ **KAPANDI.** Arayüze eklendi; ayrıca komut denetiminin **tek yönlü** olduğu düzeltildi |
| 5 | Fabrika ayarı `sebeke_hz = 50`, DC ölçümünde gücü %82 şişiriyor | ✅ **KAPANDI.** Arayüz artık uygulanan ölçek çarpanını ve uyarıyı gösteriyor |
| 6 | Kurulum kılavuzu U5A referansları yanlış | ✅ **KAPANDI.** Gerçek montaj tuzağıymış — netlist'e bağlandı |
| 7 | `test_olcum3.py` LK4'ün toleransı 177× kör | ✅ **KAPANDI.** Beklenen değer sarkmayı içeriyor, tolerans 200× sıkıldı |

**(2) 9 totoloji — hepsi ölçen teste çevrildi.** En ciddisi
`sim3_ariza.py:1260`: sart `True` ile *"skop kanalı çift yönlü DEĞİL — bu bir
tasarım gerçeği"* yazıyordu. **B19 (bir gün önce) tam da bunu değiştirmişti.**
İddia B19'dan beri yanlıştı ve `True` olduğu için zincir hiç görmedi. Ayrıca
`sim3_besleme.py`'de 7 tane (7912'nin kapasitif yükü, stok, regülasyon, kısa
devre koruması, soğutucu gereksinimi…) ve `bom_dogrula.py`'de 1 tane.
Mutasyon: `Cout` LM358 sınırının altına, `θ_JA` 100×, kısa devre akımı
küçültme, `-12 V` rayını regüle olmaktan çıkarma — **dördü de kırmızıya
dönüyor.**

**(4) Komut denetimi TEK YÖNLÜYDÜ — asıl kusur buydu.** `test_arayuz3.js`
yalnızca *"arayüzün gönderdiği her komut firmware'de var mı"* diye soruyordu.
Tersi sorulmadığı için B17'nin eklediği `f`/`F` arayüze konmadan **70/70 yeşil**
kalmıştı. Ters denetim eklendi; toplayıcı da üçlü ifadeleri
(`gonder(m === 1 ? 'y' : 'n')`) kaçırıyordu, düzeltildi. Arayüz **70 → 74**.

**(6) Kılavuzun montaj tuzağı — netlist'ten doğrulandı.** Kılavuz
*"Sallen-Key (U5A): R22/R23 = 6.8K, C7 = 2nF"* diyordu. Netlist'in söylediği:
**R23 bölücünün alt bacağı** (2.7K, VREF'e — B19'un konusu ve hemen üstteki
uyarının kendisi), Sallen-Key'in direnci **R21**; **C7 ise U5B'ye** ait,
U5A'nınki **C5**. R23'e 6.8K takmak skop kanalını **hem tek yönlü bırakır hem
ölçeğini bozardı.** Netlist denetimi **128 → 134**.

##### Bu turda ayrıca düzeltilenler

- **`guc_olc`: `i_rms` artık HAM örnekten.** `ii_top += ih * ih` yazıyordu,
  yani gösterilen Irms hizalayıcının genlik sarkmasını yiyordu (5 kHz'te
  %0.72), Vrms yemiyordu — asimetrik ve yanlış. Hizalama yalnızca **güç** için
  gerekli; RMS tek kanallı bir büyüklüktür.
- **`menzil_gozet(ham.volt)`.** Hizalayıcının çıkışı 2 örnek eski olduğu için
  menzil kararı 2.33 ms gecikiyordu; üst eşik ile NORMAL kanalın doyumu
  arasında yalnızca 3.24 V pay var ve **1395 V/s'ten hızlı her sinyalde** bu
  pay 2 örnekte yeniyordu.
- **`olcum3.h`'deki "güvenilir wattmetre bandı ~5 kHz" cümlesi ikiye ayrıldı.**
  Hızlı yol için doğru (41.7 kSa/s), ADS yolu için **değil** — aynı süzgeç
  orada 100 Hz'te %0.78, 200 Hz'te %8.3 sarkıyor. İki bant tek cümleye
  karışmıştı.

##### İkinci turun mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| `Cout`'u LM358 sınırının altına indir | B11 **23→22** |
| `θ_JA`'yı 100× yap (Tj patlar) | B11 **23→21** |
| Kısa devre akımını küçült | B11 **23→21** |
| −12 V rayını regüle olmaktan çıkar | B11 **23→22** |
| Kılavuzu eski yanlış referansa döndür | netlist **134→132** |
| `f` / `F`'i arayüzden sil (gövdeyi boşalt) | arayüz **74→72 / 74→73** |
| Ölçek uyarısını arayüzden kaldır | arayüz **74→73** |
| LK4'ün beklentisinden sarkmayı çıkar | AVR **87→86** |
| SPICE `D_ESD`'nin `IS`'ini boz | B20 **42→41** |

---

#### 5.12.31 ✅ B21 — PİL KAPASİTE TESTİ (2026-09-10)

`uretim/sim3_pil.py` · **32 doğrulama** · `dogrula3.py`'de B21 adımı ·
şemaya **BLOK 10** · firmware'de `pil_test.h` + `/pil` ucu · arayüzde panel
· netlist 134 → **150** · AVR 87 → **91** · arayüz 74 → **82**.

⚠️ Bu adım da **tasarımı** ve **firmware'i** sınıyor, kurulmuş bir kartı değil.

**Kullanıcı isteği:** *"ZB2L3 gibi çalışan bir sistem — mAh ölçümü, kapanacağı
gerilimi kendimiz ayarlayalım, akım ve voltaj grafiğini gözlemleyelim."*

##### Kararlar (kullanıcıyla birlikte alındı)

| Konu | Karar |
|---|---|
| Yük | **Taş direnç** (harici) + MOSFET **yalnızca anahtar** |
| Kurulum | **Ana karta** — ayrı modül tartışıldı, ölçüm çekirdeği bölünmesin diye vazgeçildi |
| Sıcaklık | Şimdilik yok (envanterde sensör yok) |
| Veri | Tarayıcı **IndexedDB** (sınırsız) + kartta **yetişme tamponu** |
| Kontrol | Arayüzden başlat/durdur + otomatik kesme |
| DCIR | Periyodik otomatik (5 dk'da bir) |

##### 🔴 3.3 V kapı IRFZ44N'i süremez

Stokta **mantık seviyeli (IRL…) MOSFET yok**. IRFZ44N'in eşiği **2–4 V** ve
RDS(on) **10 V'ta** ölçülmüş (INCHANGE şartnamesi s.2). ESP32'nin 3.3 V'u en
kötü halde eşiğin **altında**, iyi halde bile MOSFET'i doğrusal bölgede
bırakıp ısıtır.

Çözüm, B11'in karta koyduğu **+12 V rayından** iki transistörlü sürücü —
üçü de stokta (2N2222 ×12, BC557 ×7):

```
GPIO ──4.7K──┤2N2222├──10K──┤BC557├── +12 V
                              │
                       ──220R── MOSFET kapısı ──10K── GND
```

##### 🔴 Failsafe yönü — B21'in en önemli tek kararı

Kapı **R42 ile GND'ye çekili**. ESP32 reset atarsa, çökerse ya da WDT
tetiklenirse GPIO yüksek empedansa döner, kapı 0 V'a iner, **MOSFET kapanır
ve pil boşalmayı durdurur.** Ters kurulum (kapıyı +12 V'a çekmek) kart
ölürken yükü **bağlı bırakırdı** — saatler süren, başında kimsenin
beklemediği bir testte bu kabul edilemez.

Kaçak denetimi: Igss 100 nA × 10K = **1 mV**, eşiğin 2000 katı altında.
Açılışta da geçerli: `pinMode` çağrılmadan önce GPIO giriş kipinde.

Bu, ESP32'nin donanım WDT'sini **bedava bir emniyete** çeviriyor — ve B20
tam da böyle bir döngü takılması bulmuştu (SSE işleyicisi `loop()`'u
sonsuza kadar kilitliyordu).

##### 🔴 Neden ayrı konnektör (J7), köprü değil

J3 "Yük dönüşü" **doğrudan şönte bağlı kalıyor** (normal ampermetre
kullanımı). MOSFET'i ana akım yoluna koysaydık, ESP32 her reset attığında
**ölçülen devrenin akımı kesilirdi** — bir SMPS'i izlerken kabul edilemez.

Bunun bedeli bir **sessiz hata riski**: kullanıcı yükü yanlışlıkla J3'e
bağlarsa MOSFET baypas olur, ölçüm çalışır, grafik çizilir ama **kesme
çalışmaz.** Firmware bunu yakalıyor: test başlarken MOSFET'i **kapalı**
tutup akıma bakıyor; akım varsa testi **reddediyor**.

##### 🔴 Yeni tasarım sınırı: pil gerilimi ≤ 38.5 V

MOSFET **kapalıyken pilin tamamı üstüne biniyor**. IRFZ44N Vdss = 55 V,
%70 payla **38.5 V**. Kartın gerilim kanalı ±613 V ölçebiliyor ama **pil
testi bundan çok daha dar bir bantta** — bu ayrı bir sınır ve firmware
zorluyor.

| Pil | Gerilim | Yargı |
|---|---|---|
| 18650 1S · LiPo 3S/6S · 12 V akü · 24 V akü | ≤ 29 V | ✅ |
| **48 V paket** | 58 V | 🔴 **REDDEDİLİYOR** |

##### Isıl sınır: soğutucusuz 6.55 A

MOSFET yalnızca anahtar; güç **taş dirençte** yanıyor. MOSFET'in yediği tek
şey I²·RDS(on):

| Akım | Senaryo | P | Tj | Yargı |
|---|---|---|---|---|
| 0.89 A | 18650, 4.7 Ω | 25 mW | 41.6 °C | ✅ (+1.6 °C) |
| 2.56 A | 100 mΩ şöntün tavanı | 210 mW | 53 °C | ✅ |
| **6.55 A** | **soğutucusuz sınır** | 1.37 W | 125 °C | sınır |
| 11.5 A | 15 mΩ şöntün tavanı | 4.23 W | **302 °C** | 🔴 soğutucu şart |

##### Veri saklama — iki katmanlı

| | Kart | Tarayıcı (IndexedDB) |
|---|---|---|
| mAh / Wh | ✅ kesintisiz, **otoriter** | gösterim |
| Eğri (1 Hz) | son **1.5 saat** | **tamamı, sınırsız** |
| Sekme kapanınca | biriktirmeye devam | duraklar, açılınca **yetişir** |

Kart her noktaya **sıra numarası** veriyor; tarayıcı `/pil?sira=N` ile
eksikleri istiyor. Kartın penceresinden uzun kopmada **boşluk** oluyor ve
grafikte **açıkça işaretleniyor** — sessizce interpolasyon **yapılmıyor**.

**Kritik özellik:** mAh/Wh sayaçları **kartta** biriktiği için, eğride
boşluk olsa bile **toplam kapasite doğru kalıyor.**

> ⚠️ **Neden 2 saat değil 1.5 saat:** 2 saatlik tampon (7200 nokta = 86 KB)
> RAM kullanımını **%42'ye** çıkarıyor ve projenin kendi *"RAM < %40"*
> kuralını aşıyordu — **`test_firmware3.py` bunu yakaladı.** 5400 nokta
> (63 KB) ile toplam **%35**. Sınır donanımdan geliyor, tercihten değil.
> PSRAM bulunursa tampon 24 saate çıkıyor; bulunmazsa **işlev kaybolmuyor.**

##### 🔴 `--clean` eklendi — önbellek uyarıları GİZLİYORDU

B21 sırasında aynı kod için peş peşe **3, 2 ve 0** uyarı raporlandı.
Sebep: `arduino-cli` artımlı derliyor ve **önbellekten gelen çeviri
birimlerinin uyarılarını yeniden basmıyor.** Yani *"Derleme UYARISIZ"*
iddiası derleme önbelleği durumuna göre değişiyordu — **güvenilmezdi.**

`test_firmware3.py`'ye `--clean` eklendi (derleme 12 s → 75 s) ve
**hemen gerçek bir hata ortaya çıktı:**

```
warning: conversion from 'unsigned int' to 'uint16_t'
         changes value from '86400' to '20864'
```

PSRAM tamponu `24u * 3600u` = 86400 nokta istiyordu ama `PilHalka.kapasite`
**uint16_t** idi (tavan 65535) → **sessizce 20864'e** düşüyordu: 24 saat
yerine **5.8 saat**. Halka alanları `uint32_t` yapıldı.

##### Firmware

- `olcum3.h`: `yuk_ekle3` / `yuk_mAh3` / `yuk_coulomb3` — enerjinin birebir
  kardeşi, **işaretli** (şarj yönünde geri sayar), tavan **2562 Ah**
- `pil_test.h`: durum makinesi, halka tampon, saf denetim fonksiyonları
- `Ayar3` büyüdü → imza **0xC0F4 → 0xC0F5**
- Komutlar: `P<volt>` kesme · `p1`/`p0` başlat/durdur · `p` durum
- `/pil?sira=N` ucu — **bloklamıyor** (en çok 600 nokta/istek; B20'de
  `akis_sayfa()`'nin `loop()`'u kilitlediği görülmüştü)

##### AVR'de doğrulanan (gerçek kod)

`sim3_pil.py` yalnızca birim aritmetiğini sınayabiliyor; sayacın **işaretli
davranışı** ancak gerçek kodda görülür:

| İddia | Sonuç |
|---|---|
| 1 A × 3600 s = 1000 mAh | fark **0** |
| deşarj + eşit şarj → net | **TAM SIFIR** (ham 0 pC) |
| negatif akım → negatif yük | −0.8333334 vs −0.8333333 mAh |

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| Kapıyı +12 V'a çek (**ters failsafe**) | netlist **150→147** |
| Çekme direncini tamamen kaldır | netlist **150→147** |
| Yükü şönte doğrudan bağla (MOSFET baypas) | netlist **150→148** |
| Kapı seri direncini 0R yap | netlist **150→149** |
| Kapıyı 3.3 V'a düşür | B21 **32→31** |
| Kapıyı mutlak azaminin üstüne çıkar | B21 **32→31** |
| Isıl direnci 3 °C/W yap | B21 **32→30** |
| Vdss 600 V yap | B21 **32→31** |
| Tamponu 20 saate çıkar | B21 **32→30** |
| DCIR darbesini 30 s yap | B21 **32→31** |
| Sayacı **tek yönlü** yap | AVR **91→89** |
| mAh ölçeğini 1000× boz | AVR **91→89** |
| `p1`/`P` gövdesini boşalt | arayüz **82→80/81** |
| Boşluk sayımını/işaretini sil | arayüz **82→81** |
| IndexedDB'yi kaldır | arayüz **82→80** |
| J7/J3 uyarısını sil | arayüz **82→81** |

##### Bu adımda yakalanan iki test kusuru

1. **`test_arayuz3.js`'in `govdeIcinde` yardımcısı yorumdaki bir anmayı
   fonksiyon tanımı sanıyordu** — `pilCsvIndir` iddiası bu yüzden yanlışlıkla
   kırmızı yandı. Artık tanım biçimi aranıyor.
2. **Boşluk iddiası metin tabanlıydı** — değişken adını bırakıp mantığı
   silmek testi kandırıyordu. Davranışa bağlandı.

##### 🔴 Tezgahta ölçülmesi gerekenler (B21'den)

1. **MOSFET'in üzerindeki logo** — veri sayfası ikincil kaynak (INCHANGE).
2. **Kapı gerilimi** — yük açıkken Vgs gerçekten ~11.8 V mi.
3. **Failsafe** — kart çalışırken reset atıp yükün kesildiğini gör. En
   önemli tezgah testi bu.
4. **Baypas denetimi** — yükü bilerek J3'e bağlayıp testin reddedildiğini gör.
5. **Şöntün güç değeri** — ±11.5 A rakamı 2 W **çıkarımından** geliyor.
6. **Taş direncin gerçek değeri ve ısınması.**

##### B21'in AÇTIĞI iş kalemleri

| # | İş | Neden |
|---|---|---|
| 1 | **Sıcaklık ölçümü** | Pil testi sıcaklıksız yarım kör; envanterde sensör yok |
| 2 | **Elektronik yük (sabit akım)** | Taş dirençte akım pil çöktükçe düşüyor (0.89 → 0.64 A); C-oranı sabit değil |
| 3 | Kayıt hızı (`pil_kayit_hz`) arayüzden ayarlanamıyor | Firmware destekliyor, arayüzde denetim yok |
| 4 | Şarj yönünde test (mAh geri sayıyor) | Sayaç işaretli, ama şarj kaynağı yok |

---

#### 5.12.32 🗂 DOSYA DÜZENİ ve KULLANICI BELGELERİ (2026-09-10)

Kullanıcı *"dosya sisteminde çok fazla dosya var, neyin ne olduğunu
anlayamıyorum"* dedi. Kök dizin sadeleştirildi ve gözle okunacak belgeler
ayrı bir yere alındı.

##### Yeni düzen

| Klasör | Ne |
|---|---|
| **`BELGELER/`** | **Kullanıcının bakacağı yer** — yalnızca HTML + PDF |
| `kod/olcum-karti-a3/` · `sema3/` · `arayuz3/` | Güncel sürümler |
| `uretim/` | Doğrulama zinciri + belge üreteçleri |
| `arsiv/asama1/` · `arsiv/asama2/` | Eski aşamalar, zincirleriyle birlikte |
| `DEVIR.md` · `README.md` | Kayıt |

Kökte artık 8 girdi var (önce 19). **94 MB → 9.8 MB**: `build/`
klasörleri (85 MB) ve geçici simülasyon dizinleri silindi — hepsi
yeniden üretilebilir.

##### 🔴 Arşivleme zincirleri KIRDI — yollar düzeltildi

Aşama 1 ve 2'nin kodu/şeması/arayüzü taşınınca `dogrula.py` **4 adım**,
`dogrula2.py` **3 adım** kırmızıya döndü. **22 yol** güncellendi. İki tuzak:

1. **arduino-cli eskiz klasörünün `.ino` adıyla aynı olmasını istiyor** —
   `kod/olcum-karti-a2` → `arsiv/asama2/kod` yapınca derleme kırıldı.
   Klasör adları korundu: `arsiv/asama2/olcum-karti-a2/`.
2. Üreteçler eski yerlere yazmaya devam ediyordu; `sema/`, `sema2/`,
   `kanit/` kökte **yeniden doğuyordu**. Çıktı yolları da arşive çevrildi.

##### Zincir artık kendi çöpünü topluyor

`dogrula3.py` bitişte `build/`, `_chk*`, `__pycache__` ve `erc*.rpt`
siliyor. Önceden her koşu ~85 MB bırakıyordu.

##### BELGELER — üretilen, elle yazılmayan

Yedi sayfa, **12 grafik**, hepsi `uretim/belge-uret.py` ile üretiliyor ve
**zincire bağlı** (B9 adımı), yani tasarım değişince bayatlamıyor.

| Sayfa | İçerik |
|---|---|
| `index.html` | Giriş, hangi belge ne işe yarar |
| `1-ne-yapabilir.html` | Yetenekler · menzil grafiği · osiloskop ekranı · canlı ölçüm · multimetre karşılaştırması · yapamadıkları |
| `2-olcumler.html` | Menziller, hızlar, şönt tablosu, zaman tabanı tablosu, hassasiyet ≠ doğruluk |
| `3-pil-testi.html` | 8 pil tipi için akım/süre tablosu · 4 grafik (V–t, V–mAh, mAh+Wh birikimi, DCIR–SoC) |
| `2-malzemeler.html` | **Şemadan + envanterden üretiliyor** — alınacak / yolda / stokta |
| `4-kurulum.html` | Montaj (mevcut üreteç) |
| `5-muhendislik.html` | Nasıl çalışıyor — isteğe bağlı |

**Grafiklerin verisi hesaplanıyor**, dekoratif çizim yok: deşarj eğrisi
bir OCV modelinden + iç direnç düşüşünden, osiloskop ekranı 20 kHz'lik
bir SMPS dalgasından, menzil çubukları `tasarim3_sabit.py`'den.

Renk paleti `dataviz` becerisinin doğrulanmış varsayılan paleti;
`validate_palette.js` ile sınandı (bütün denetimler PASS, açık + koyu).
Kontrast uyarısı doğrudan etiketlemeyle karşılandı — hiçbir seri kimliğini
yalnız renge bırakmıyor. Açık/koyu tema ikisi de destekleniyor.

##### Not

`kurulum3.html` → `BELGELER/4-kurulum.html` taşındı; üreteci de oraya
yazıyor. Eski aşamaların HTML/PDF çıktıları `arsiv/` altında duruyor.

---

#### 5.12.32b 📚 B22 ÖNCESİ ARAŞTIRMA — mimarinin GEREKÇESİ (2026-09-10)

Kullanıcının soruları B22'yi başlattı: *"web sitesini bitirdik mi, ben nasıl
gireceğim, yayını bilgisayar mı yapacak, telefondan ulaşabilecek miyim"* ·
*"arayüz ESP32'ye sığar mı, kaldırabilir mi"* · *"kendi telefonumda bir HTML
dosyasını uygulama gibi açabilir miyim — böylece ESP'ye daha az yük biner"* ·
*"hem bilgisayar hem telefon bağlıysa telefonda gördüğüm şey bilgisayardan mı
yayınlanacak"*.

**Bu bölüm cevapları değil, cevapların DAYANAĞINI kaydediyor.** Aşağıdaki beş
bulgu üç bağlanma kipini ve "arayüz karttan servis edilsin" kararını
belirledi; biri değişirse mimari kararı yeniden gözden geçirilmeli.

| # | Bulgu | Sonucu |
|---|---|---|
| 1 | **`file://` bir `http://` sunucuya ULAŞAMAZ.** Sunucu hangi CORS başlığını gönderirse göndersin: `file://` kökeni *opaque*, `Access-Control-Allow-Origin: *` bu durumu kurtarmıyor | Kullanıcının *"telefonda HTML dosyası açayım"* fikri **çalışmaz**. Sayfa karttan ya da köprüden **servis edilmeli** |
| 2 | **PWA / service worker güvenli bağlam istiyor** — HTTPS ya da `localhost`. **LAN IP istisnası YOK** (`192.168.x.x` güvenli bağlam sayılmıyor) | Kartta HTTPS yok → gerçek PWA kurulumu **mümkün değil**. iOS'ta *Ana Ekrana Ekle* yine de tam ekran açıyor, Android'de yalnızca kısayol. Belgede **vaat edilmiyor** |
| 3 | **Chrome 142 Local Network Access**, public bir sayfanın yerel ağa istek atmasını kapatıyor | Bir bulut sayfasının karta bağlanması güvenilmez. Bu, **karttan servis edilen sayfayı en sağlam seçenek** yapıyor — sayfa ve veri aynı kökenden gelir |
| 4 | **IndexedDB düz HTTP'de çalışıyor** (güvenli bağlam gerekmiyor), Chrome diskin **%60**'ına kadar veriyor | Uzun ölçüm kaydı **tarayıcıda** birikebilir; kartın belleği sınır değil |
| 5 | **`NetworkClient::write(Stream&)` 1360 baytlık tampon kullanıyor** | 82 KB'lik bir dosyayı servis etmek yalnızca **~1.36 KB RAM** demek. *"Arayüz ESP32'ye sığar mı"* sorusunun cevabı: **flash'ta yer sorunu var, RAM'de yok** |

**Kullanıcının ikinci sorusunun cevabı** (*"hem PC hem telefon bağlıysa"*):
kart aynı anda **tek sürücüye** hizmet ediyor ve karta bağlanan her tarayıcı
ölçümü yavaşlatıyor (her HTTP isteği `loop()`'u bloke ediyor). İkisi birden
isteniyorsa **köprüden** geçilmeli — o kipte telefonun gördüğü sayfayı
**bilgisayar yayınlıyor**, kartın Wi-Fi'si hiç açılmıyor. Bu yüzden USB köprü
**tercih edilen** kip. Kullanıcıya görünen anlatımı `BELGELER/6-ag.html`'de.

⚠ **Bunların hiçbiri tezgahta doğrulanmadı** — hepsi belge/kaynak okumasına
dayanıyor. mDNS'in Android'de çözülmesi, CSRF savunmasının gerçek tarayıcıda
çalışması ve telefondan ilk yükleme süresi `uretim/_tezgah.md`'de.

---

#### 5.12.33 ✅ B22.0 — ARAYÜZ HİÇ AÇILMIYORDU (2026-09-10)

🔴 **Zincir 15/15 ve B7 82/82 yeşilken arayüz tarayıcıda hiç açılmıyordu.**
Bu, "yeşil test bir şey kanıtlamaz" kuralının dördüncü örneği ve şimdiye
kadarki en utandırıcı olanı: kusur bir modelde ya da zamanlamada değil,
**iki dosyanın yokluğunda**ydı.

##### Ne olmuştu

`index.html` `style.css` ve `vendor/vue.global.prod.js` istiyor.
`arayuz3/sunucu.py:37` bunları `ORTAK = BURASI.parent / "arayuz"`
yolundan düşürüyordu ("tek kopya kalsın" gerekçesiyle). **5.12.32'de o
dizin `arsiv/asama1/arayuz`'a taşındı ve bu dosya güncellenmedi.**
Aynı taşımada `demo-uret.py:28` düzeltilmiş, `sunucu.py` atlanmıştı —
DEVIR 5.12.32 "22 yol güncellendi" diyor, `sunucu.py` o 22'nin içinde yok.

Ölçüldü (sunucu ayaktayken `curl`):

| İstek | Önce | Sonra |
|---|---|---|
| `/style.css` | **404** | 200 (11 697 B) |
| `/vendor/vue.global.prod.js` | **404** | 200 (154 807 B) |

Zincirleme etki: Vue yüklenmiyor → `app.js:18` `ReferenceError` →
hiçbir metot kurulmuyor → `[v-cloak]` kalkmıyor → ekranda ham
`{{ bicim(volt, 3) }}` şablonu kalıyor. **Hiçbir düğme çalışmıyor.**

##### Zincir bunu neden göremedi

1. `test_arayuz3.js` Vue'yu **kendisi taklit ediyor** (`:36`) — vendor
   dosyasına ihtiyacı yok.
2. **Projede tek bir dosya-varlık denetimi yoktu** (`existsSync` sıfır kez).
3. Var olan `ok('ek.css bagli', htmlKaynak.includes('ek.css'))` iddiası
   bile yalnızca *dizenin HTML'de geçtiğine* bakıyor, **dosyanın diskte
   olduğuna değil**.

##### Yapılanlar

| # | İş | Neden |
|---|---|---|
| 1 | `style.css` + `vendor/` **`arayuz3/` altına kopyalandı** | Arşiv dokunulmadı |
| 2 | `sunucu.py`'den `ORTAK` ve `translate_path` **silindi** | Kusuru değil, **kusuru üreten mekanizmayı** kaldır. Aşama 1/2 arşivde olduğuna göre "tek kopya" gerekçesi zaten çökmüştü |
| 3 | `ek.css`'e `.kpi` · `.kpi-ad` · `.kpi-deger` · `.uyari` eklendi | Dördü de `index.html`'de **kullanılıyordu ama hiçbir CSS'te tanımlı değildi** |
| 4 | `style.css`'te 3 tanımsız değişken düzeltildi | `--kenar`→`--kenar-c`, `--metin`→`--yazi`, `--yuzey`→`--kart` — 8 yerde sessizce geçersize düşüyordu |
| 5 | `sahte-kart.js` statik `<script>`'ten **dinamiğe** çevrildi | 15 936 B her açılışta boşuna iniyordu; B22.5'te LittleFS görüntüsüne de girerdi |

🔴 **En ciddi görsel kusur `.uyari`'ydı:** *"Yükü **J7**'ye bağlayın, J3'e
değil. J3 doğrudan şönte gider; oraya bağlarsanız MOSFET **baypas** olur ve
**kesme çalışmaz**"* uyarısı **biçimsiz düz paragraf** olarak görünüyordu.
B21'in en önemli tezgah testi bu uyarıya dayanıyor. `.uyari`, `.hata`'dan
**bilerek farklı** tanımlandı (sol şerit ↔ tam çerçeve): `.hata` geçici bir
hatadır, `.uyari` kalıcı bir emniyet talimatıdır; ikisi aynı görünürse
kullanıcı emniyet uyarısını "geçmiş bir hata" sanır.

##### Yeni: `test_arayuz3.js` §8 varlık denetimi — **82 → 93**

Metin değil **varlık** sınıyor: referans verilen dosya gerçekten duruyor mu,
kullanılan sınıf gerçekten tanımlı mı, `sunucu.py` dizin dışına düşüyor mu.

##### 🔴 Mutasyon testi ÜÇ test kusuru buldu

İlk turda 14 mutasyonun **3'ü kaçtı**. Üçü de gerçek kusurdu:

| Kaçan mutasyon | Kök sebep | Düzeltme |
|---|---|---|
| `.kpi` kuralını sil | Sınıf araması **CSS yorumlarını da tarıyordu** — `ek.css`'in kendi açıklama yorumunda `.kpi` geçtiği için sınıf "tanımlı" sayılıyordu | Yorumlar çıkarılıyor. *Bir iddianın kendi yorumuyla karşılanması, iddia olmadığı anlamına gelir* |
| `.uyari` gövdesini `.hata` ile aynı yap | Ham **metin** karşılaştırması; iki kural ayrı dosyada ve ayrı girintide olduğu için anlamca aynı olsalar bile metinleri farklıydı | Bildirimler normalleştirilip **küme** olarak karşılaştırılıyor |
| `sahte-kart.js` statik `<script>` geri konsun | İddia sayısı **girdiyle birlikte büyüyordu**: etiket eklenince bir iddia düştü ama aynı anda bir referans (bir iddia) eklendi, **toplam değişmedi** | Referans denetimi tek bir toplu iddiaya indirildi — sayı sabit |

Üçüncüsü genel bir ders: **iddia sayısı girdiye bağlıysa, sayım tabanlı her
denetim körleşir** — planlanan `dogrula3.py` sayım kilidi dahil.

Düzeltmelerden sonra: **14/14 yakalandı, 0 kaçak.**

| Mutasyon | Sonuç |
|---|---|
| `style.css` yeniden adlandır | 93 → **88** |
| `vendor/` → `vendor2/` | → 92 |
| `.kpi` / `.kpi-deger` / `.uyari` kuralını sil | → 92 / 92 / **91** |
| `.uyari` gövdesini `.hata` ile birebir aynı yap | → 92 |
| CSS değişkenini tanımsız bırak | → 92 |
| `sunucu.py` `../arayuz` düşmesi geri gelsin | → 92 |
| `sunucu.py` `translate_path` geri gelsin | → 92 |
| `sahte-kart.js` statik `<script>` geri konsun | → 92 |
| `demoVeri`'den `betikYukle` kaldır | → 92 |
| `betikYukle` gövdesini boşalt | → 92 |
| J7/J3 uyarısından `.uyari` sınıfını kaldır | → 92 |

##### Doğrulama

Zincir **15/15** (B7 93/93). Ayrıca ölçüldü: sunucu ayakta tüm varlıklar
**200**; `vendor/vue.global.prod.js` node'da çalıştırılıp `Vue.createApp`
tanımlı ve `Vue.version = 3.5.13` doğrulandı; iki CSS dosyasının süslü
parantezleri dengeli.

⚠ **Zincirin kanıtlamadığı:** sayfanın gerçekten *doğru göründüğü*.
Tarayıcı açılmıyor, DOM kurulmuyor. Kullanıcının `python arayuz3/sunucu.py`
ile bakması gerekiyor — konsolda 0 hata, ham `{{ }}` yok, J7/J3 uyarısı
kırmızı şeritli.

#### 5.12.34 ✅ B22.1 — ÖLÇÜM TABANI (2026-09-10)

Yeni özellik yok. Amaç: WiFi açılmadan **önce** ölçülecek sayıların doğru
tabana oturması. Sonra düzeltilseydi WiFi'nin maliyeti bozuk tabana karşı
ölçülürdü — B20'nin düştüğü tuzağın aynısı.

##### 🔴 K1 — kart 665 değil **500.0 SPS**'te örnekliyordu

`loop()`'un ilk satırı `sunucu.handleClient()`. Kütüphane, **istemci
yokken** her turda `delay(1)` çağırıyor (`WebServer.cpp:422-425`,
`_nullDelay` varsayılan `true`). `CONFIG_FREERTOS_HZ = 1000` olduğu için bu
`vTaskDelay(1 tik)`: döngü bir sonraki tik sınırına kadar blokleniyor.

```
govde 1502.8 us -> ceil(1502.8/1000) x 1000 = 2000 us = 500.0 SPS
enableDelay(false) ile                                  665.4 SPS
pay 497.2 us  — web tarafına eklenecek her 497 us bir basamak düşürür
```

**Bu, B20'nin sildiği `delay(2)` kusurunun kütüphane sürümü.**
`sim3_bant.py:126` göremiyordu çünkü yalnız `.ino`'nun `loop()` gövdesinde
regex arıyor. Üstelik `sunucu.begin()` koşulsuz çağrıldığı için kusur
**WiFi kapalıyken de** geçerliydi. Düzeltme tek satır: `enableDelay(false)`.

⚠ Tersi de doğru: bekleyen bir istemci varken `_currentStatus != HC_NONE`
olduğundan `delay(1)` atlanıyor — yani **biri LAN'ı tararken kart daha
doğru ölçüyordu**. Model kurmadan akıl yürütülemeyeceğinin kanıtı.

##### 🔴 K2 — faz kalibrasyonu **örnek** cinsindendi, düzelttiği şey **sabit zaman**

```c
// eski:  d = t_kayma_us / ornek_periyot_us + faz_kal[m]
// yeni:  d = (t_kayma_us + faz_kal_us[m]) / ornek_periyot_us
```

Örnek cinsinden saklanınca uygulanan zaman `faz_kal × ornek_periyot_us`
oluyor — **döngü periyoduyla ölçekleniyor**. Oysa düzeltilen şey iki RC'nin
arctan farkı: sabit bir zaman. B20 bunu zaten *"faz kalibrasyonu (SABİT
zaman gecikmesi)"* diye yazıyordu; **uygulama o tanımla uyuşmuyordu.**

1502.8 µs'te kalibre edilen kartın artık hatası (en kötü τ eşleşmezliği,
kondansatör toleransı ±%10 → 292.8 µs):

| Periyot | Artık faz | PF=0.5'te güç |
|---|---|---|
| 1502.8 µs (kalibrasyon noktası) | 0.000° | — |
| **2000 µs (K1 yüzünden bugünkü)** | **+1.744°** | **−%5.3** |
| 3000 µs (menzil geçişi) | +5.251° | −%16 |

B17'nin kendi kabul ölçütü **≤1°**; bugünkü hata onun **1.74 katıydı**.
`AYAR3_IMZA` `0xC0F5 → 0xC0F6`. ⚠ Yapı **boyutu değişmedi**
(`float[2] → float[2]`), yani `n == sizeof(Ayar3)` denetimi bunu **göremez**
— imza tek korumadır.

##### 🔴 K3 — çıplak `g`/`i` kanalı **kalıcı olarak öldürüyordu**

`atof("")` = 0 → `kazanc *= 0/s` → 0 → `ayar_kaydet()`. Sonra
`olc_gerilim3` hep 0 döndüğü için `|s| > esik` şartı **bir daha asla**
sağlanmıyor: kanal NVS silinene kadar ölü. Kurtarma yolu **yoktu**.

Üç katmanlı düzeltme:
1. `strtof` + `son == s+1` ile **argüman varlığı** denetimi (`g`, `i`, `f`)
2. `kalibre_kazanc`'ta **sonuç kelepçesi** (0.2–5 kat) — ikinci savunma hattı
3. **`R!` fabrika sıfırlama** — bozulmuş NVS'ten tek kurtuluş yolu

Çıplak `f` de artık sessizce DC'ye geçirmiyor, **değeri gösteriyor**.

##### PSRAM öksüzü — RAM **%35 → %15**

`static PilNokta pil_ic_tampon[5400]` = **64 800 B**. PSRAM bulununca halka
PSRAM'e taşınıyor ama statik dizi serbest bırakılamıyor: iç RAM'in **%20'si**
ölü kalıyordu. Yığına alındı, ayırma tek yerde toplandı.

```
RAM 116 200 B (%35)  ->  51 400 B (%15)     serbest yığın 211 -> 276 KB
```

`test_firmware3.py` RAM eşiği **%40 → %25** sıkılaştırıldı — gevşek kalsaydı
statik tamponun geri gelmesi görünmez olurdu.

##### Belge/kod ayrışması ve blokaj görünürlüğü

Açılış satırı `"(2 saat)"` diyordu, `PIL_IC_KAPASITE` 5400 = **1.5 saat**.
Süre artık kapasiteden **türetiliyor**; elle yazılmış hâli `BULUNMAMALI`
listesinde.

Yeni **`K <kayip_ms> <loop_azami_us> <uzun_tur>`** satırı (yalnız değişince
basılıyor, `?` çıktısında da var). `enerji_biriktir`'in atladığı aralık artık
**sayılıyor** — eskiden tamamen sessizdi. Çift çekirdek kararının eşiği de bu:
`loop_azami_us > 20 000` ise görev ayrımı yapılır.

⚠ `D` satırına **alan eklenmedi** — 9 alan arayüzde, `sahte-kart.js`'te ve
testte sabit; alan eklemek üçünü aynı anda değiştirmeyi gerektirir
(B17'nin `f`/`F` kusurunun aynısı). Yeni önek geriye dönük uyumlu.

##### Zincire eklenenler

| Adım | Önce | Sonra | Ne eklendi |
|---|---|---|---|
| B17 `sim3_senkron.py` | 26 | **31** | faz düzeltmesi µs ve **bölmenin içinde**; imza bump; artık hatanın sayısallaştırılması |
| B20 `sim3_bant.py` | 42 | **47** | **kütüphane gövdesi taraması** (`WebServer.cpp`), tik kilidi modeli, `enableDelay` sırası |
| B4/B5 `test_olcum3.py` | 91 | **94** | **tuğlalama testi** — AVR emülatöründe davranışsal |
| B6 `test_firmware3.py` | 43 | **58** | 7 yeni ikili dize, eşikler **koşulsuz**, komut listesi kaynaktan |
| B7 `test_arayuz3.js` | 93 | **98** | faz birimi, iki aşamalı onay, her ret yolu sebebini söylüyor |

İki kör nokta kapandı: `test_firmware3.py`'nin **elle yazılmış komut
listesi** (`f`, `F`, `p`, `P` hiç yoktu) kaynaktan çıkarılıyor, ve
flash/RAM eşikleri `if mf:` koşulundan çıkarıldı — regex tutmazsa iddia
**sessizce buharlaşıyordu**.

##### 🔴 Mutasyon testi — 14/14, ama ilk turda 4 kaçak vardı

| Kaçan | Kök sebep | Düzeltme |
|---|---|---|
| NVS imzasını `0xC0F5`'te bırak | İddia **yoruma kanıyordu** — değişikliği anlatan açıklama da `0xC0F6` yazıyor | Yorumlar çıkarılıp koda bakılıyor |
| Fabrika sıfırlama onayını kaldır | İddia bayrağın **adına** bakıyordu; kapı silinse de `sifirlaOnay = false` gövdede duruyordu | Erken dönüş **kapısı** sınanıyor |
| `fazGonder` ret mesajını sil | Tek `this.hata` aranıyordu; iki ret yolundan biri silinince öteki iddiayı karşılıyordu | **Her iki** ret yolu ayrı ayrı |
| `kalibre_kazanc` kelepçesini kaldır | **Hiç iddia yoktu** — metin testi davranışı göremez | AVR emülatörüne davranışsal test |

Sonuncusu kaldırılınca emülatör tuğlalamayı birebir üretiyor: kazanç
`0.000000`, kurtarma başarısız, 12 V yerine **0 V**.

İki kaçağın kök sebebi aynı ve B22.0'dakiyle de aynı: **bir iddianın kendi
yorumuyla karşılanması (ya da yorumdan dolayı düşmesi), iddia olmadığı
anlamına gelir.** Metin tabanlı iddialar yazılırken yorumlar çıkarılmalı.

##### Doğrulama

Zincir **15/15**. Derleme uyarısız, flash %16, RAM **%15**.
⚠ Zincir hâlâ kurulmuş bir kartı değil tasarımı doğruluyor; K1'in gerçek
etkisi tezgahta `D` satırındaki örnek sayısıyla ölçülecek (200 ms'de
**133 ± 3** beklenir; **100 çıkarsa** `enableDelay` işe yaramamış demektir).

#### 5.12.35 ✅ B22.2 — TAŞIYICI KATMANI (2026-09-10)

Arayüz artık **üç taşıyıcıyı** destekliyor: `seri` (Web Serial), `akis`
(SSE — kart ya da PC köprüsü) ve `demo` (sahte kart). **Tek arayüz kodu**,
üç taşıma. Modlar arasındaki fark kodda değil `yetenek` tablosunda yaşıyor.

**Neden iki ayrı arayüz yazılmadı:** bu proje arayüz↔firmware ayrışmasından
üç kez yandı (DEVIR 4.1, 4.15, B17 — sonuncusunda zincir 70/70 yeşilken
kullanıcı gücü %82 yüksek okuyordu). "Basit sürüm + zengin sürüm" aynı riski
dördüncü kez açardı; üstelik en az bakılan kod, kart odanın öbür ucunda
613 V ölçerken çalışacaktı.

##### Dikişin çalıştığı zaten kanıtlıydı

`navigator.serial` yalnız 68 satırda geçiyordu ve aşağı akış tamamen
`satirIsle(string)`'den besleniyordu — `sahte-kart.js` bu dikişten **zaten**
takılıyordu. Yapılan iş dikişi genişletmek oldu, yeniden çizmek değil.

🔴 **`gonder()` çağrı yerlerinin şekli değişmedi.** `test_arayuz3.js`
`gonder('x')` / `komut('x')` düz metin kalıbını tarıyor; şekil korunduğu
için çift yönlü komut denetimi hiç bozulmadan çalışmaya devam etti.

##### 🔴 `pilYokla` — üç kusur birden kapandı

| # | Kusur | Sonucu |
|---|---|---|
| 1 | Adres **göreliydi** (`fetch('/pil?…')`) | İstek karta değil Python sunucusuna gidiyordu |
| 2 | `fetch` **404'te reddetmez** | Hata sayfasının HTML'i `anahtar=değer` sanılıp ayrıştırılıyor, **tüm KPI'lar sessizce 0** oluyordu — `pilKesme: 3.0` bile eziliyordu |
| 3 | Kısmi yanıt denetlenmiyordu | Kartta yığın sıkışırsa `String::concat` başarısız oluyor, `operator+=` bunu **yutuyor**, gövde kesiliyor ama `Content-Length` tutarlı → tarayıcı hata görmüyor |

Artık her uzak istek `kartAdres()`'ten geçiyor, `y.ok` ve `durum=` biçimi
denetleniyor, başarısızlık `pilHataMetni` ile **kullanıcıya söyleniyor**.

##### Yetenek tablosu ve tek kaynak

`yetenek = {ad, komut, skop, skop_azami, gecmis_s, cok_istemci, surucu}`.
🔴 Kural: **yetenek yoksa düğme görünmez ama nedeni görünür** — ölü düğme
bırakmak DEVIR 4.15'in ta kendisiydi. `desteksizNeden` computed'i her kip
için ayrı bir cümle veriyor (telefonda Web Serial yok → akış kipini seç).

`demo` ayrı bir bayrak olmaktan çıkıp `tasiyiciAdi`'ndan **türetilen**
computed oldu — iki bayrak tutmak DEVIR 4.1'in deseniydi.

Ayrıca `localStorage` ilk kez kullanılıyor: pencere, göstergeler, şönt,
şebeke Hz, kart adresi ve taşıyıcı tercihi saklanıyor. ⚠ Her erişim
try/catch içinde — özel kipte ve kota dolduğunda **erişimin kendisi** atıyor.

##### Zincir: arayüz 98 → **112**, ve çoğu METİN DEĞİL YAPI sınıyor

Taşıyıcılar `vm` bağlamında **gerçekten oluşturulup** yüzeyleri
karşılaştırılıyor (`vm.runInContext('TASIYICILAR', sandbox)`):

* üçü de aynı yüzeyi sunuyor (`ad·yetenek·destekli·ac·kapat·gonder`)
* yetenek tabloları aynı **alanlara** sahip
* tablo modları **gerçekten** ayırıyor (`gecmis_s: 0 / 86400`) — hepsi aynı
  değeri verseydi tablo süsleme olurdu
* `app.js`'te `kartAdres()` dışında `fetch(` **yok**
* `satirIsle` içinde taşıyıcıya özgü **dal yok** — dal açmak, tel üstündeki
  baytların ayrıştığı anlamına gelir

##### 🔴 Üçüncü kez: iddia yorumu okuyordu

Taşıyıcı katmanının açıklama yorumunda örnek olarak `gonder('x')` yazıyordu
ve **komut toplayıcı bunu gerçek komut sandı** — ileri yön denetimi
*"arayüz 'x' gönderiyor, firmware'de yok"* diye kırmızıya döndü.

Tersi çok daha kötü olurdu: firmware'e eklenip arayüze konmamış bir komut,
yalnızca bir yorumda adı geçtiği için **"erişilebilir" sayılabilirdi** —
ters yön denetiminin bütün değeri kaybolurdu.

`komutlariTopla` artık yorumları çıkarıyor. Bu, aynı sınıfın bu oturumdaki
**beşinci** örneği (CSS sınıfı, NVS imzası, `faz_kal` alanı, `.uyari`
gövdesi, komut toplayıcı). Kural netleşti: **metin tabanlı her iddia koda
bakmalı, prozaya değil.**

İkinci küçük kusur: varlık denetiminin `(?:href|src)="` deseni Vue'nun
`:href="kopruAdresi"` **bağlamasını** da yakalıyordu. `(?:^|\s)` şartı eklendi.

##### Mutasyon: 10/10, sıfır kaçak

`pilYokla`'yı göreli fetch'e geri al · `y.ok` sil · biçim denetimi sil ·
bir taşıyıcıdan metot sil · yetenek tablolarını aynı yap · bir yetenek
alanını çıkar · `satirIsle`'ye taşıyıcı dalı koy · `demo`'yu ayrı bayrak
yap · `ayarOku` try/catch kaldır · `pilHataMetni`'ni şablondan sil.

Önceki iki aşamada 4+3 kaçak vardı; bu turda **ilk denemede sıfır** —
yapısal iddiaların metin iddialarından üstünlüğü ölçüldü.

##### Doğrulama

Zincir **15/15**. Ayrıca işlevsel duman testi: `gonder('?')` demo
taşıyıcısından `SahteKart`'a gidip `satirIsle`'yi besliyor (`A` satırı
günlükte), `satirIsle` D satırını doğru ayrıştırıyor, `kartAdres` boş ve
dolu tabanda doğru çalışıyor.

⚠ `TasiyiciAkis` **henüz uçtan uca denenemedi** — `/akis` ve `/komut`
uçları B22.3/B22.4'te geliyor. Bugün yalnızca yapısal olarak doğrulandı.

#### 5.12.36 ✅ B22.3 — PC KÖPRÜSÜ (2026-09-10)

🎯 **Telefon burada çalışmaya başladı — firmware'e hiç dokunmadan.**
Köprü karta USB ile bağlanıyor, telefona kendisi yayın yapıyor. Bu kipte
kartın WiFi'si hiç açılmıyor: `loop()`'ta TCP yok, ölçüm doğruluğu en
yüksek, ve CORS / Chrome LNA / Android `.local` sorunlarının **üçü de
ortaya çıkmıyor** (sayfa ve veri aynı kökenden geliyor).

##### Köprünün asıl değeri güzel arayüz değil, **röle** olması

Karta bağlanan her tarayıcı ölçümü doğrudan bozuyor (`/pil` isteği
`loop()`'u 25–200 ms bloklıyor; >1 s ise enerji sayacı o aralığı
**tamamen atıyor**) ve kartın SSE'si **tek istemcilik**. Köprü N tarayıcıyı
**1**'e indiriyor.

##### Üç dosya, yalnız standart kütüphane

| Dosya | Ne |
|---|---|
| `kopru/kart_baglanti.py` | `SeriKart` (Win32 API, ctypes) · `KayitKart` (kayıttan oynatma) |
| `kopru/arsiv.py` | Eklemeli ham satır günlüğü + türetilmiş CSV |
| `kopru/kopru.py` | Röle · statik arayüz · `/akis` · `/komut` · `/devral` · `/durum` |

**pyserial kullanılmadı.** Bu makinede kurulu ama bir Python yeniden
kurulumunda kaybolabilir; projenin bütün Python tarafı stdlib. Win32 seri
API'si `ctypes` ile erişilebiliyor.

🔴 **İlk yazımda ciddi bir ctypes kusuru vardı:** `CreateFileW`'ye
`restype` verilmemişti, ctypes dönüşü `c_int` (32 bit) sayıp **64 bitlik
tanıtıcıyı kırpıyordu**. Başarısızlıkta dönen −1, `INVALID_HANDLE_VALUE`
ile karşılaştırılamıyor ve kod **geçersiz tanıtıcıyla devam ediyordu** —
hata "COM99 açılamadı" yerine bir sonraki adımda "GetCommState başarısız"
olarak, yani **yanlış yerde** görünüyordu. Bütün fonksiyonlara
argtypes/restype verildi.

Ayrıca: WinError 2 (port yok) ile WinError 5 (port meşgul) **ayrı ayrı**
raporlanıyor — yanlış sebep söylemek en can sıkıcı hata ayıklama türü.

⚠ DTR/RTS sürücüsü **kapalı**: ESP32 kartlarında bu iki hat otomatik-reset
devresine bağlı, açılışta değişirlerse kart **reset atar**.

##### Plandan bir sapma: `/k` değil `/komut`

Kartın B22.4'te açacağı uç da `/komut` olacak. Aynı yol, aynı yöntem, aynı
başlıklar — **istemci köprüye mi karta mı bağlı olduğunu bilmek zorunda
değil.** Köprü 204 + boş gövde dönüyor (kartın cevabı zaten SSE'den
geliyor); kart doğrudan bağlandığında yanıt gövdede geliyor. Aynı istemci
kodu ikisini de işliyor çünkü boş gövde hiçbir satır üretmiyor.

##### Sürücü hakemi

N izleyici, **bir sürücü**. Jeton SSE'nin `kimlik` olayıyla geliyor,
komutlarda `X-Jeton` başlığıyla dönüyor. Arayüzde "izleyici" şeridi ve
**Devral** düğmesi var.

🔴 **`p0` (pil deşarjını DURDUR) her taşımada, jetonsuz, kimliksiz geçiyor.**
Başlatmak yetki ister; durdurmayı hiçbir şey geciktiremez. Bu, testte ayrı
bir emniyet iddiası olarak duruyor.

⚠ Politika **tek yerde**: sunucuda. Arayüz yalnızca durumu gösteriyor ve
devri istiyor — politikayı iki yerde tutmak bu projenin cezalandırdığı
ayrışma deseni olurdu.

##### CSRF yüzeyi

`POST` zorunlu + `X-Olcum: 1` özel başlığı. `<img>`/`<form>` özel başlık
**ekleyemez**; çapraz kökende preflight'a zorluyor. Ölçüldü:
`GET /komut?k=p1` → **404**, başlıksız POST → **400**.

##### Zincir: yeni adım **B22**, 24 doğrulama — zincir 15 → **16 adım**

En önemli iddia **rölenin bayt-şeffaflığı**: 9 farklı önekten oluşan bir
örnek küme köprüden geçiriliyor ve girdiyle çıktı **bayt-bayt** karşılaştırılıyor.
Köprü satırı "düzeltmeye" kalksa (boşluk kırpma, sayı biçimleme, JSON'a
çevirme) ikinci bir temsil doğar ve ayrışma sınıfı geri gelir.

Ayrıca sınanıyor: arşivdeki satırlar da birebir aynı · CSV **günlükten
üretiliyor** (ayrı tutulmuyor) · Excel-TR uyumlu (BOM + `;` + `,`) · köprü
`arayuz3/`'ü **kopyalamıyor**, aynen servis ediyor (bayt karşılaştırması).

🔴 **Test sırası tuzağı:** yukarı-akış döngüsü SSE abonesinden önce
başlatılırsa `KayitKart`'ın bütün satırları abone yokken tüketiliyor ve
akış boş kalıyor. Testte önce abone olunuyor, sonra döngü başlıyor.

##### Mutasyon: 11/11, sıfır kaçak

Röle satırı düzeltsin · röle JSON sarsın · röle yalnız `D` taşısın ·
`X-Olcum` denetimini kaldır · GET ile komut kabul et · **`p0` de jeton
istesin** · sürücü hakemini kaldır · `devral` bilinmeyen jetonu kabul etsin ·
arşiv ham satırı bozsun · CSV BOM'suz · CSV ondalık nokta kalsın.

##### 🔴 Windows tuzağı: `0.0.0.0:80` ile `127.0.0.1:80` yan yana durabiliyor

stok-takip `127.0.0.1:80`'i tutuyor (Windows açılışında başlıyor). Köprü
`0.0.0.0:80`'e bağlanmayı denediğinde bu **başarılı olabiliyor** —
`SO_EXCLUSIVEADDRUSE` kullanılmamışsa. O durumda hangi sunucunun cevap
verdiği **hedef adrese** bağlı: `127.0.0.1` daha özel bağlamaya (stok'a)
gider, köprüye yalnızca LAN IP'sinden ulaşılır.

Bu makinede tam olarak öyle oldu ve köprünün *"Bu bilgisayardan:
http://127.0.0.1"* mesajı kullanıcıyı **stok arayüzüne** yollayacaktı.
Artık her iki satırda da LAN IP'si yazıyor.

Bağlama sırası: `0.0.0.0:80` → `<LAN-IP>:80` → `0.0.0.0:8770`.

##### Doğrulama

Zincir **16/16**. Uçtan uca ölçüldü (donanımsız, kayıtlı günlükle):
köprü ayakta, statik arayüz servis ediliyor ve `index.html` geliştirme
sunucusuyla **bayt-bayt aynı**, `/durum` yanıt veriyor, geliştirme
sunucusunda `/durum` 404 (otomatik algılama doğru şekilde sessiz kalıyor).

⚠ **`SeriKart` gerçek donanımla denenemedi** — kart kurulmadı. Sınanan:
port bulunamayınca doğru hata, DCB/COMMTIMEOUTS alan düzeni (28/20 bayt),
satır tamponlama. Gerçek baud ve DTR davranışı **tezgah listesinde**.

#### 5.12.37 ✅ B22.4 — KARTIN WEB KATMANI (2026-09-10)

Kartın web tarafı **üç yerden kırıktı** ve üçü de kapandı.

##### 🔴 1. WiFi hiç açılmamıştı

`WIFI_AD` boş bir sabitti, yani `WiFi.begin()` **bir kez bile
çağrılmadı**; AP kipi dosyada hiç yoktu. Yerine `ag.h`: STA dene →
10 s'de olmazsa **kendi ağını kur** (`OLCUM-KARTI-XXXX`, WPA2) + mDNS.

🔴 **AP parolası MAC'ten türetilmiyor.** İlk akla gelen "SSID'ye MAC son
eki koy, parolayı da MAC'ten üret" **hiçbir şey korumaz**: SSID zaten
beacon ile yayınlanıyor. Bunun yerine ilk açılışta **rastgele** üretilip
NVS'e yazılıyor ve seri konsola basılıyor.

🔴 **Ağ ayarları `Ayar3`'e EKLENMEDİ**, ayrı NVS ad alanında
(`olcumag`). Gerekçe: `Ayar3` büyürse `sizeof` denetimi bozulur, imza
bumplanır ve **kalibrasyon sıfırlanır**. Bir WiFi parolası değişikliği
yeniden kalibrasyona mal olamaz.

##### 🔴 2. SSE yalnızca `D` satırını taşıyordu

`akis_yolla` tek bir yerden — `loop()`'un rapor bloğundan — çağrılıyordu.
`S2`/`M`/ham skop/`E`/`T`/`W`/`B` ve bütün `*`/`!` yanıtları **yalnızca**
`Serial.print`'teydi. WiFi ile bağlanan arayüz **salt-okunur ve sessiz**
olurdu: osiloskop yakalar, hiçbir şey göremezdi.

Çözüm **`Serial` aynası**: `.ino`'da 245 `Serial.` çağrısı var, dört
başlık dosyasında **sıfır** (ölçüldü) — tek bir `#define` hepsini aynaya
alıyor ve **çağrı yerlerinin hiçbiri değişmiyor**. 245 satırı elle
değiştirmek, içinde bir tanesini atlamayı kolaylaştırırdı (DEVIR 4.15'te
`index.html`'in üç düğmesi tam böyle atlanmıştı).

⚠ `#undef Serial` şart: çekirdekte `Serial` **zaten** bir makro; doğrudan
yeniden tanımlamak `warning: "Serial" redefined` veriyor ve bu projede
uyarıya sıfır tolerans var.

Satır bölücü (`web_satir.h`) **saf C** yazıldı ve AVR emülatöründe
sınanıyor: CRLF temizleme, boş satır atlama, taşan satırın **yine de
tamamlanması** (yoksa ayrıştırıcı hizasını kaybeder) ve **kırpılan baytın
sayılması**. AVR 94 → **101**.

##### 🔴 3. Komut ucu yoktu

`komut_calistir`'a HTTP'den giden yol yoktu. Artık `POST /komut` var ve
komutlar **kuyruğa** giriyor, `loop()` boşaltıyor — HTTP işleyicisi uzun
bir komutu beklemiyor ve tek yazar disiplini kuruluyor.

**CSRF yüzeyi:** `HTTP_POST` açıkça yazılı (`HTTP_ANY` olsaydı
`GET /komut?k=p1` çalışırdı ve `<img>` ile pil deşarjı başlatılabilirdi) ·
`X-Olcum: 1` özel başlığı zorunlu · oturum jetonu · `Host` beyaz listesi
(DNS rebinding) · isteğe bağlı Basic auth.

⚠ **`collectHeaders` çağrılmazsa `header()` her zaman boş döner ve bütün
CSRF savunması sessizce ölür.** Zincirde ayrı bir iddia.

🔴 **`enableCORS(true)` KULLANILMIYOR** — üç başlığı da `*` yapıyor
(`WebServer.cpp:663-667`), yani herhangi bir sayfa yanıtı **okuyabilir**
ve oturum jetonu sızardı. Yalnızca kayıtlı köprü kökenine elle izin
veriliyor. `ACAO: null` da verilmiyor (sandbox'lı iframe'ler de `null`).

🔴 **`p0` (DURDUR) jetonsuz, parolasız geçiyor** — köprüdeki kuralın aynısı.

##### SSE düzeltmeleri

Önce **tek istemcilikti**: ikinci `GET /akis` birincisini sessizce üzerine
yazıyordu. Artık 4 yuva, 15 s kalp atışı, `retry: 3000`, `id:` yer imi ve
köprü kayıtlıysa **gerekçeli ret** (`event: kopru` + adres).

##### Ağ kurulum paneli — akış bilerek USB'den

Kartın WiFi'sini kartın WiFi'si üzerinden kurmak tavuk-yumurta olurdu.
`N` komut ailesi (`N?` `Na` `Np` `NA` `Ns` `N1` `N0`) arayüze eklendi;
ağ üzerinden kuruluyorsa **düz metin uyarısı** çıkıyor (kartta TLS yok).

##### Bütçe

```
flash  511 636 -> 1 024 631 B  (%16 -> %32)   esik %60   [WiFi+mDNS yigini]
RAM     51 416 ->    71 268 B  (%15 -> %21)   esik %25
```

##### Zincir: yeni adım **B22b** (`sim3_web.py`, 46) — zincir 16 → **17 adım**

##### 🔴 Mutasyon: 19/19 — ama ilk turda 4 kaçak

| Kaçan | Kök sebep | Düzeltme |
|---|---|---|
| `X-Olcum` denetimini komut ucundan kaldır | İddia **dosya genelinde** arıyordu; `kopru_sayfa` da aynı denetimi yaptığı için yeşil kaldı | Fonksiyon **gövdesinde** aranıyor |
| AP parolasını MAC'ten türet | İddia **adın geçmesine** bakıyordu; tanım yeniden adlansa çağrı yeri adı taşımaya devam ediyordu | Gövde sınanıyor: `esp_random` **var**, `macAddress` **yok** |
| Kaynağa sabit parola yaz | Desen `wifi_`/`ap_` öneki istiyordu; `String sifre = "..."` kaçtı | Adında `sifre`/`parola`/`pass` geçen **her** değişkene atanan uzun dize |
| `kirpilan` artırmasını kaldır | Ad yapı alanında ve yorumda da geçiyordu | **Artırmanın kendisi** (`s->kirpilan++`) sınanıyor |

Dördü de aynı ailenin üyesi: **iddia yanlış kapsamda arıyordu.** Ders
netleşti — metin tabanlı bir iddia (a) yorumları çıkarmalı, (b) **doğru
gövdenin içinde** aramalı, (c) adın varlığını değil **davranışı** temsil
eden ifadeyi aramalı.

##### Doğrulama

Zincir **17/17**, derleme **uyarısız**.

⚠ Bu adımın kanıtlamadıkları — hepsi tezgah listesinde: gerçek WiFi
bağlantısı · mDNS'in telefonda çözülmesi · CSRF savunmasının gerçek
tarayıcılardaki davranışı · `esp_wifi_start()` ↔ `adc_continuous_start()`
çarpışması (DEVIR 7.1 ①) · SSE'nin `loop()`'u ne kadar bloklandığı.

#### 5.12.38 ✅ B22.5 — ARAYÜZ KARTTAN SERVİS EDİLİYOR (2026-09-10)

🎯 **"Bilgisayar yoksa" senaryosu burada tamamlandı.** Kart arayüzü artık
kendisi sunuyor: telefon doğrudan karta bağlanıyor, PC hiç gerekmiyor.

##### Üretim zinciri — hiçbir adres elle yazılmıyor

| Betik | Ne |
|---|---|
| `uretim/ikon-uret.py` | 180×180 PNG + `manifest.json` üretiyor (stdlib zlib) |
| `uretim/arayuz-uret.py` | `arayuz3/` → gzip → mklittlefs → `_fs.bin` |
| `uretim/arayuz-yaz.py` | esptool ile karta yazıyor |

Bölüm ofseti (`0x310000`) ve boyutu (`0xE0000`) **`huge_app.csv`'den
okunuyor**. Elle yazılsaydı bölüm şeması değiştiğinde görüntü yanlış
adrese gider ve kart sessizce boş bir dosya sistemi görürdü.

```
index.html    26 683 ->  8 046      style.css   12 051 ->  2 906
app.js        64 505 -> 20 752      vue        154 807 -> 58 361
ek.css         3 317 ->  1 577      manifest       312 ->    214
ikon-180.png   1 150 ->  1 150      TOPLAM             93 753 B
                                    bölümün %10.2'si
```

🔴 **`arayuz-yaz.py` bayat görüntüyü YAZMIYOR.** Künyedeki sha256'ları
kaynakla karşılaştırıyor ve değişen dosyayı adıyla söylüyor. Bayat bir
görüntüyü karta yazmak, depodaki arayüz ile karttaki arayüzün sessizce
ayrışması demekti — bu projenin üç kez yandığı sınıf.

##### 🔴 `index.htm` tuzağı

`serveStatic` dizin isteğini `requestUri + "index.htm"` ile karşılıyor
(`RequestHandlersImpl.h:198`) — **`index.html` değil**. Dosyayı `index.htm`
diye adlandırmak yerine **açık bir kök işleyicisi** kondu: dosya adı
alışıldık kalıyor ve tuzak koda yazılı hale geliyor.

##### Önbellek — telefonda "her açılışta 58 KB" ile "bir kez" farkı

`/vendor/` → `max-age=31536000, immutable` (Vue sürümlenmiş bir varlık,
bir kez iniyor). Kök → `no-cache`. ⚠ `index.html` **immutable olamaz**:
olsaydı arayüz güncellemesi tarayıcıya **hiç ulaşmazdı**.

⚠ `enableETag` **kullanılmıyor**: `calcETag` dosyanın tamamını okuyup özet
çıkarıyor, yani göndermek kadar bloklar. `immutable` aynı işi sıfır
maliyetle yapıyor.

⚠ `LittleFS.begin(false)` — **otomatik biçimlendirme yok**. Başarısız bir
yazma "boş dosya sistemi"ne dönüşüp sebebi gizlerdi. Boş bölüm bir hata
değil; `kok_sayfa` ne yapılacağını **yazıyor**.

##### Telefonda uygulama gibi

`apple-mobile-web-app-capable` **düz HTTP'de çalışıyor**: iPhone'da Ana
Ekrana Ekle → adres çubuğu yok, kendi ikonu, kendi kartı. ⚠ Android'de
gerçek PWA kurulumu HTTPS + service worker istiyor; kısayol Chrome
sekmesinde açılıyor. **Bu vaat edilmiyor**, belgede de böyle yazıyor.

İkon **üretiliyor** — depoda kaynağı olmayan bir PNG değiştirilemeyen bir
esere dönüşürdü. Renkler `style.css`'in **koyu tema** belirteçlerinden
okunuyor (`#161b21` / `#6690ff` / `#f79009`); arayüzün rengi değişirse
ikon da değişiyor.

##### Toplu uçlar — asıl hafıza sıkışması burada

**`PIL_YANIT_NOKTA` 600 → 150** ve gövde **parçalı** gönderiliyor:

* *Blokaj:* 600 nokta ≈ 15 KB, lwIP `TCP_SND_BUF` ≈ 5 744 B → üç TCP
  penceresi, her biri ACK bekliyor ve o süre boyunca **örnekleme duruyor**.
  150 nokta ≈ 3.8 KB — en kötü blokaj **dört kat** azaldı. Kayıp yok:
  kayıt 1 Hz, yoklama 2 s, kararlı durumda zaten ~2 nokta geliyor.
* *Bitişik bellek:* eski kod `g.reserve(64 + n*34)` ile **tek parça
  20 464 B** istiyordu. Parçalanmış yığında bu ayırma başarısız olabilir
  ve `String::concat` `false` döner — ama `operator+=` bunu **yutuyor**:
  kesik gövde + tutarlı `Content-Length`, yani tarayıcı hiçbir hata
  görmeden eksik veri alıyor.

**`GET /skop.bin`** — 32 B başlık + `adet × uint16`. ASCII dökümü 4000
örnekte 20 250 B; ikili **8 032 B** (%40'ı). Kural: *bir kanal kalp atışı
için (D, 5 Hz), ikinci kanal toplu aktarım için (istek/yanıt, ikili);
ikisi karışmaz.*

🔴 **Uç tek başına yarım iş olurdu** (B17'nin `f`/`F` kusuru). İki taraf da
yapıldı: firmware'de **`tB`** (yakala ama ASCII **dökme** — yoksa `Serial`
aynası yüzünden aynı veri SSE'de iki kez taşınırdı), arayüzde
`skopIkiliAl()`.

🔴 **İki çözücü, tek gösterici:** ikili yol da ASCII yol da aynı
`osiloTopla` yapısını kurup aynı `osiloBitir()`'i çağırıyor. Çizim kodu iki
kez yazılsaydı ikisi ayrışır ve **biri sessizce yanlış çizerdi**.
Endian **açıkça** küçük (`DataView(..., true)`); `Uint16Array` platformun
endian'ını kullanır ve bir gün sessizce ters okuyabilirdi.

##### Bütçe

```
flash  1 024 631 -> 1 067 303 B  (%32 -> %33)   esik %60
RAM       71 268 ->    71 420 B  (%21)          esik %25
LittleFS       0 ->    93 753 B  (bolumun %10.2'si)
```

##### Mutasyon: 18/18 — ama bir kaçak vardı

*"iOS tam ekran etiketini kaldır"* kaçtı: `apple-mobile-web-app-capable`
dizesi etiketin **üstündeki açıklama yorumunda** da geçiyordu. HTML
yorumları da çıkarılıyor artık.

Bu, aynı sınıfın bu oturumdaki **altıncı** ortaya çıkışı: CSS sınıfı ·
NVS imzası · `faz_kal` alanı · `.uyari` gövdesi · komut toplayıcı · HTML
meta etiketi. Kural artık üç maddeli — metin tabanlı bir iddia
**(a)** yorumları çıkarmalı, **(b)** doğru gövdenin içinde aramalı,
**(c)** adın varlığını değil davranışı temsil eden ifadeyi aramalı.

Yakalanan diğerleri: otomatik biçimlendirme · serveStatic sırası ·
`immutable` kaldır · kök işleyicisinden LittleFS dalını çıkar ·
`enableETag` kullan · `PIL_YANIT_NOKTA` 600 · parçalı gönderimi kaldır ·
`/skop.bin` kaydını sil · `tB`'yi kaldır · görüntü listesinden varlık
çıkar · `sahte-kart.js` ekle · manifest bağlantısını kaldır · istemcide
`Uint16Array` · imza denetimini kaldır · uzunluk denetimini kaldır ·
hep ASCII kullan · ikili yol `osiloBitir` çağırmasın.

##### Doğrulama

Zincir **17/17**, derleme uyarısız. B22b 46 → **72**, arayüz 116 → **122**.
Görüntü bayatlığı ayrı bir iddia ve ısırdığı ölçüldü (`ek.css`'i değiştir
→ kırmızı).

⚠ **Karta hiç yazılmadı** — kart kurulmadı. `mklittlefs -l` ile görüntünün
yedi dosyayı doğru içerdiği doğrulandı; gerçek bağlama, `serveStatic`
davranışı ve telefondan ilk yükleme süresi **tezgah listesinde**.

#### 5.12.39 ✅ B23 — TEZGAH LİSTESİ · AĞ BELGESİ · ZİNCİR KORUMALARI (2026-09-10)

Donanım gelene kadar kapatılabilecek üç boşluk vardı ve üçü de aynı
sınıftandı: **elle yazıldığı için ölçümle bağı kopmuş bilgi.**

##### B23.1 — Tezgah listesi artık üretiliyor

Tek tezgah listesi `DEVIR.md`'de **elle yazılmış 8 kalemdi ve B20/B21
döneminde dondu.** B22.3, B22.4 ve B22.5'in üçü de *"tezgah listesinde"*
diyerek o listeye atıf yapıyordu — ve liste onların kalemlerini
**içermiyordu.** Ayrıca dört ayrı "kanıtlamaz" listesi vardı ve
**kesişimleri sıfırdı**; zincirin donanıma en bağımlı iki adımı
(`test_kopru.py`, `sim3_web.py`) hiçbir şey basmıyordu.

Yeni kural: **tezgah kalemi, onu doğrulayamayan kodun yanında yaşar.**

`uretim/tezgah.py` — ortak biçim. Çıktı hem insan hem makine için
okunabilir; ikinci bir "makine satırı" basılmıyor (o, aynı bilginin iki
temsili olurdu):

```
  === TEZGAH: B20 Ornekleme hizi ve bant ===
  [T] [!] `D` satirindaki ORNEK SAYISI — ilk, en ucuz ve en onemli test
      -> 200 ms'de 133 ± 3 bekleniyor. ~100 -> enableDelay ise yaramadi.
         ~19 -> B20 cokmus
```

`dogrula3.py` bunları adım çıktılarından toplayıp **tek birleşik liste**
basıyor ve `uretim/_tezgah.md` yazıyor. **17/17 adımın hepsi kalem
basıyor, toplam 72 kalem.**

**Taban çizgisi elle yazılmıyor — `ADIMLAR`'ın kendisi taban çizgisi.**
Bir betikten `tezgah(...)` silinirse o adım sıfıra düşer ve toplayıcı
kırmızı döner. Ölçüldü: `netlist3_dogrula.py`'den çağrı silindi → adım
**kendi başına 150/150 yeşil kaldı**, toplayıcı yakaladı.

`_tezgah.md`'nin başındaki **"İlk gün"** tablosu da türetiliyor: `[!]`
işaretli kalemler. Elle bir sıralama tutulsa yine bayatlardı.

🔴 **Kendi eklediğim kalem, eklediği adımı düşürüyordu.** Dört adımın
kalemine kırmızı daire emojisi, birine çevrelenmiş rakam koymuştum.
Windows konsolu cp1254: `python sim3_web.py` **tek başına** koşturulunca
codecs içinde `UnicodeEncodeError` ile çöküyordu (ölçüldü, rc=1). Kural
`tezgah.py`'nin docstring'inde yazılıydı ve **ilk gün çiğnendi** — yani
belge olarak tutulan her kural gibi. Artık `tezgah()` yazmadan önce
konsolun karakteri çizip çizemeyeceğine bakıyor ve hangi adımın hangi
kaleminin suçlu olduğunu söyleyerek düşüyor.

##### B23.2 — `BELGELER/6-ag.html`

Kullanıcının bu oturumdaki **ilk sorusu** (*"nasıl gireceğim, bilgisayar
mı yayın yapacak, telefondan ulaşabilecek miyim"*) belgelerde
cevapsızdı; dahası `index.html` **"Bilgisayara USB ile bağlanıyor"**
diyordu — B22'den sonra yanlış.

Yeni sayfa üç bağlantı kipini SVG diyagramla anlatıyor ve kaynakta
yazılı olup hiçbir belgede olmayan iki davranışı söylüyor: **kart aynı
anda tek sürücüye hizmet eder** ve **karta bağlanan her tarayıcı ölçümü
yavaşlatır** — "bilgisayar mı yayın yapacak" sorusunun asıl cevabı
**USB köprünün tercih edilen olduğu**.

Sayfadaki her sayı kaynaktan: `AG_MDNS` · AP SSID deseni · `10 s` ·
portlar · `_fs.json`. `h_metin()` yeni bir okuyucu — `h_sabit` yalnızca
`[0-9.]+f` yakalıyordu. **Ölçüldü:** `ag.h`'de `AG_MDNS` değiştirildi →
sayfadaki üç adres de kendiliğinden değişti, geri alındı → geri döndü.

Bu sırada üç bayat/yanlış sayı daha çıktı:

| Nerede | Yazıyordu | Gerçek |
|---|---|---|
| `index.html` | "15 adımlı bir zincir" | **17** — artık `dogrula3.ADIM_SAYISI`'ndan |
| `belge-uret.py` | `"5 sayfa"` | **7** — artık sayılıyor |
| `4-kurulum.html` | Firmware **481 935 B (%15)** | **1 067 423 B (%33)** — 2.2 kat sapma |

Firmware boyutu artık `test_firmware3.py`'nin **ölçtüğü** değerden
geliyor (`_firmware.json`); B6 zincirde B9'dan önce koştuğu için hep
taze. Yedek değer **bilerek yok** — elle bir sayı koymak bayatlamayı
geri getirirdi.

🔴 **`4-kurulum.html` gezinme şeridini hiç göstermiyordu** ve MENU'ye
eklenen "Bağlanma" sekmesi orada görünmedi: serit iki ayrı üreteçte
yaşıyordu. `belge_menu.py` ikisinin de tek kaynağı.

⚠ `index.html`'deki "hangi belgeye bakmalıyım" tablosu MENU'den
**türetilmiyor**, elle yazılıyor. Şimdi bir denetim ayrışmayı kırmızı
yapıyor. **İlk yazımı boştu:** tüm sayfaya bakıyordu ve gezinme şeridi
zaten her adresi içerdiği için her zaman geçiyordu — mutasyonla
ölçüldü, kaçtı. Denetim tabloyla sınırlandırıldı, mutasyon yakalandı.

##### B23.3 — Zincir korumaları

**`uretim/sayim.py`** — ortak özet ayrıştırıcı. Zincirdeki 18 özet
satırı dört ayrı biçimde yazılıyor; hem sayım kilidi hem mutasyon
koşucusu aynı deseni kullanıyor.

**`uretim/beklenen_sayim.json`** — iddia sayısı kilidi. Sapma **her iki
yönde de kırmızı**: DEVIR'in kendi uyarısı, B22.2'de bir iddia düşerken
başkası eklendi ve toplam sabit kaldığı için mutasyon kaçmıştı.
`python dogrula3.py --sayim-kilidi-yaz` ile tabanı tazeliyorsun.

Kilit yanlış alarm vermesin diye önce koşullu iddia blokları sabitlendi:
`test_olcum3.py`'nin üç `if "SZn" in s:` bloğu emülatör çıktısı bozulursa
**sekiz iddiayı birden sessizce** düşürüyordu. Varlığın kendisi artık bir
iddia — B22.1'de `test_firmware3.py`'nin flash/RAM regex'ine yapılanın
aynısı.

**`uretim/mutasyon.py`** — 10 mutasyon, `--adim` ile hedeflenebilir.
İki tasarım kararı: **yerinde mutasyon yok** (proje git deposu değil, bir
Ctrl-C kaynağı bozuk bırakır ve geri dönüş yolu yoktur) ve kopya
`%TEMP%`'e değil **kardeş dizine** (üç betik `Elekronic/` düzeyine
bakıyor; `projeler/_mutasyon-<pid>/` kullanılırsa üçü de çalışır).

🔴 **Koşucu ilk turunda üç gerçek kusur buldu:**

| Mutasyon | Neden kaçtı |
|---|---|
| `collectHeaders(` → `collectHeadersX(` | İddia `"collectHeaders" in INO_KOD` idi — **alt dizge**. `collectHeadersFoo` da geçerdi |
| `AG_MDNS ""` | **Hiçbir iddia yoktu.** mDNS adı boşalsa `olcum.local` çözülmez ve yeni ağ sayfası boş adres yazar |
| `enableDelay` yorumu | İddia B20'de, benim tablomda B22b yazıyordu — **mutasyon tablosunun kendi hatası** |

İlk ikisi düzeltildi (B22b 72 → **74** iddia), üçüncüsü tabloda
düzeltildi. Sekiz hafif mutasyonun hepsi artık yakalanıyor.

İki mutasyon **tam zinciri** koşturuyor (`AGIR`, yalnızca `--adim` ile,
her biri ~12 dk) çünkü ölçtükleri şey tek adımda değil `dogrula3.py`'nin
kendi düzenlemesinde:

| Mutasyon | Sonuç |
|---|---|
| `sema3-uret.py` çöksün | Zincir **kırmızı** (B23.3'ten önce yeşil kalıyordu) |
| Bir adım `tezgah(...)` çağırmasın | Zincir **kırmızı**, adım kendi başına 150/150 yeşilken |

##### Üç somut kusur

🔴 **B3, şema üretimi çökse bile yeşil kalıyordu.** `dogrula3.py`
`sema3-uret.py`'nin dönüş kodunu denetlemiyordu; ERC ve netlist
diskteki **bayat** `.kicad_sch` / `.net` dosyalarını okuyup temiz rapor
veriyordu. Zincirin en sessiz deliği.

🔴 **826 sızmış geçici dizin.** Altı betik `mkdtemp()` çağırıp
silmiyordu: `spice-` 618 · `olcum3_` 135 · `skopolc_` 47 · `kopru_` 22 ·
`fw3_` 4 · `skop_` 2. `spice.kos()` çalışma dizinini **döndürdüğü** için
`finally` yetmiyor — silme çağrı bitince değil **süreç** bitince olmalı.
`uretim/gecici.py` bunu `atexit` ile yapıyor; ölçüldü: `sim3_ortusme.py`
koşusu artık **sıfır** dizin bırakıyor (önce 9 bırakıyordu).

🔴 **Çöp toplama kapsamı.** `glob` özyinelemesiz ve `if d.is_dir()`
dosyaları eliyordu: `kopru/__pycache__`, `uretim/avr/__pycache__` ve
`_a4_*.elf` hiç silinmiyordu. ⚠ `kopru/arsiv/` **bilerek kapsam dışı** —
orası kullanıcının ölçüm günlüğü, proje çöpü değil.

##### Mutasyon koşucusunun kendi bulduğu iki kusur

Koşucu ilk kurulduğunda `arsiv/`'i kopya dışı bırakıyordu ("eski
aşamalar, mutasyonların hiçbiri oraya bakmıyor") ve **taban koşusu
kopyada kırmızı döndü** — mutasyon uygulanmadan önce.

Sebep: `kurulum3-uret.py:326` CSS'ini **`arsiv/asama2/kurulum2.html`**'den
okuyor. Yani **güncel kurulum kılavuzu bir arşiv dosyasına bağımlı** ve
bunu hiçbir yer söylemiyordu. Derleme çıktıları temizlendikten sonra
`arsiv/` zaten 6 MB / 52 dosya; dışlama kaldırıldı.

Ders: *"eski aşamalar"* diye işaretlenmiş bir dizin, güncel bir üretecin
bağımlılığı olabilir. Koşucu bunu ilk turunda buldu — ama yalnızca özet
satırı bastığı için **nedeni görünmüyordu**; artık taban kırmızıysa
kopyadaki başarısız satırları da basıyor.

Tanılama açılınca **ikinci kusur** çıktı: `kurulum3-uret.py`
`BELGELER/4-kurulum.html`'i yazarken klasörü **yaratmıyordu**, ve B9'da
`belge-uret.py`'den **önce** koşuyor — `mkdir` yapan tek betik oydu.
Yani `BELGELER/` silinmiş bir ağaçta B9 çöküyordu. Asıl ağaçta klasör
hep var olduğu için hiç görülmemişti; **mutasyon kopyası onu görünür
kıldı.** Düzeltildi.

İkisi de aynı sınıf: **temiz bir ağaçta koşmayı hiç denemediğimiz için
görünmeyen bağımlılıklar.**

Arşiv bağımlılığı **taşınmadı** — biçim çalışıyor ve kopyalamak yeni bir
ayrışma yüzeyi açardı. Onun yerine **görünür** kılındı: dosya yoksa
`kurulum3-uret.py` ne olduğunu söyleyen bir hatayla düşüyor (ölçüldü:
dosya geçici olarak yeniden adlandırıldı → rc=1 ve mesaj çıktı).

##### Bu bölümün kanıtlamadıkları

Hiçbiri donanımsız doğrulanamaz; hepsi `_tezgah.md`'de. **Ertelendi:**
B22.6 (köprünün ağ yukarı-akışı) · çift çekirdek (eşik `loop_azami_us >
20 000 µs`, ölçümü tezgah listesinde).

#### 5.12.40 ✅ B24 — GITHUB YAYINI VE YAYIN ÖNCESİ DENETİM (2026-09-11)

Proje **herkese açık** yayınlandı: <https://github.com/Muhammet933321/esp32-olcum-karti>
(MIT). `git init` + `.gitignore` + `.gitattributes`; 180 dosya, 11 MB.
Dışarıda: derleme çıktıları, `__pycache__`, `_fs.bin`, **kullanıcının
ölçüm günlüğü** (`kopru/arsiv/`) ve `fiyat_tara.py`.

İngilizce tanıtım `README.md`, mevcut Türkçe rehber `README.tr.md` oldu.

##### Yayından önce denetim — ve yayından SONRA çıkanlar

İki bağımsız denetim koşturuldu (12 + 10 ajan). **129 doğrulanmış bulgu.**
En pahalıları, yayınlanmış belgelerde **yanlış güvenlik ve emniyet
bilgisi** olmasıydı:

🔴 **`BELGELER/6-ag.html` dört yanlış iddia taşıyordu.** Üçü kaynağa
bakınca çürüdü: *"USB kipinde kartın Wi-Fi'si hiç açılmıyor"* (varsayılan
**açık**, `N0` gerekiyor) · *"kart aynı anda tek sürücüye hizmet eder"*
(aslında `AKIS_AZAMI`=4 tarayıcı; tek-sürücü kuralı **yalnızca köprü
kayıtlıyken**) · *"tehlikeli komutlar parola istiyor"* — `web_yetkili()`
parola kurulmamışsa **`true` dönüyor**, yani varsayılan kurulumda
yetkilendirme **kapalı**. Dördüncüsü çelişkiydi: ağ sayfası USB'yi
koşulsuz öneriyordu, kurulum kılavuzu izole olmayan devrede USB'yi
**yasaklıyor**.

🔴 **En ciddisi: "pil + Wi-Fi ile yüzdür" ÇÖZÜM DEĞİL.** Hem kurulum
kılavuzu hem benim yazdığım README bunu şebeke referanslı ölçümün cevabı
diye sunuyordu. B15/D2 bunu zaten ölçmüş ve yazmış: *"PC kurtulur;
KULLANICI kurtulmaz — kart 615 V'a çıkar. Yalıtımlı kutu + 5 delik
aralık ŞART."* **Yalıtımlı kutu şartı hiçbir kullanıcı belgesinde
geçmiyordu.** Artık kurulum kılavuzunun ilk uyarısında, ağ sayfasında ve
iki README'de de var; sayılar (12.6 mm creepage, 5 delik) kaynaktan.

🔴 **Firmware kullanıcıya yanlış söylüyordu.** `N` komutunun ortak
kuyruğu her alt komuttan sonra *"(bir sonraki açılışta geçerli)"*
basıyordu — ama `Ns` (web parolası) **anında** geçerli. Yani `Ns` ile
korumayı KALDIRAN kullanıcıya korumanın sürdüğü söyleniyordu. Mesaj
alt komuta göre ayrıldı ve **iki yeni iddiaya** bağlandı (B22b 74 → 76).

⚠ İlk yazdığım iddia **boştu**: dilim `alt == 's'`den ortak kuyruğa
kadardı ve sonraki dalların `break`'lerini de içeriyordu — mutasyon
kaçtı. Dilim dalın gövdesine daraltıldı, iki mutasyon da yakalandı.
**Aynı kapsam hatası, aynı oturumda üçüncü kez.**

##### Yayınlanan dosyada kişisel iz

`uretim/b15-arastirma.md` üç satırda Windows kullanıcı adı ve Claude
oturum kimliği taşıyordu (geçici dizin yolları). Temizlendi; bilgi değeri
(`<yerel-gecici-dizin>`) korundu.

##### Bayat sayılar — yine

| Nerede | Yazıyordu | Gerçek |
|---|---|---|
| `_tezgah.md` (B18 kalemi) | pay **18 mV** | **1930 mV** — 18 mV B18/F12 **öncesinin** değeri |
| `_tezgah.md` (B19 kalemleri) | skop `-65.2/+45.1 V`, `26.9 mV` | `-63.5/+46.8 V`, `28.8 mV` |
| `README.md` | "over 30 abuse scenarios" | **27** |
| `bom_dogrula.py` | "diğer 15 adım" | **16** |
| `CLAUDE.md` | zincir **15/15**, ~5 dk | **17/17**, ~6 dk |
| `DEVIR.md` (4 yer) | B15 **109** doğrulama | **111** |
| `README.md` · `DEVIR.md` | mutasyon **~2 dk** | ölçüldü: **~14 s** |

İlk ikisi **üretilen** `_tezgah.md`'nin içindeydi: kalem metinleri elle
yazılmıştı. İkisi de artık ölçümden türetiliyor.

⚠ Ayrıca README'nin *"hiçbir sayı elle yazılmadı"* iddiası **kendisi
için yanlıştı** — README üretilmiyor. Cümle, üretilen belgelerle sınırlı
hâle getirildi.

##### Klonlayan biri ne yaşar

* `arduino-cli` ve kişisel envanter depo **dışında**. İkisi de artık
  traceback yerine açık mesaj veriyor. B16 atlamayı **duyurup iddia
  sayısını koruyor**; B9 erken çıkıyor ve zincir kırmızı dönüyor —
  `--sayim-kilidi-yaz` bunu **susturmaz**, tezgah denetimi sayımdan
  bağımsız.
* FQBN eksikti: README yalnızca `huge_app` diyordu. **`PSRAM=opi` ve
  `FlashSize=16M` olmadan N16R8 kartta derleme yanlış çıkıyor** —
  LittleFS'in `0x310000` ofseti 4 MB sınırına düşüyor. Tam FQBN yazıldı.

##### Açık kalan

Denetimlerin düşük öncelikli bulguları (`__pycache__`'in kaynak yolu
taşıması, arşivde yinelenen kanıt dosyaları, `4-kurulum.html`'in tek dış
font bağlantısı, AVR emülatörünün ATmega328P olması) **kapatılmadı** —
listesi bu bölümde, biri canımı sıkarsa buradan bakılır.

---

#### 5.12.41 ✅ B25 — DONANIM BRINGUP KOSUCUSU (2026-09-11)

ESP32 **yarın geliyor.** Zincirin 18 adımı tasarımı doğruluyor ama kart
elde olduğunda çalıştırılabilecek tek bir donanım testi yoktu:
`uretim/_tezgah.md` bir **kontrol listesi** — insan okur, koşmaz. 75 kalemi
elle denemek hem yavaş hem atlamaya açık.

`uretim/tezgah_kart.py` bunu kapatıyor: gerçek karta **seri + HTTP**
üzerinden bağlanıp elle denenmesi gerekmeyen her şeyi otomatik sınıyor.

```
python tezgah_kart.py --liste                       # ne yapacağını gösterir
python tezgah_kart.py --sifirla                     # aşama 0: çıplak ESP32
python tezgah_kart.py --sifirla --asama 1           # + ADS1115
python tezgah_kart.py --sifirla --http olcum.local  # + web katmanı
```

##### Aşamalar — elde ne varsa o kadarı

| Aşama | Donanım | Ne sınanıyor |
|---|---|---|
| **0** | Yalnız ESP32-S3 | Açılış afişi (PSRAM boyutu, LittleFS, ağ kipi), komut yüzeyi, `K` blokaj sayacı, NVS savunmaları, web katmanı |
| **1** | + ADS1115 modülleri | I²C adresleri, `D` satırının biçimi · hızı · **örnek sayısı** |
| **2** | + analog ön uç | Değer denetimleri (henüz kalem yok — kart kurulunca eklenecek) |

**27 denetim.** Her beklenen yanıt **firmware kaynağından okunuyor** —
`D` satırının alan sayısı `.ino`'daki biçim dizesinden sayılıyor, mDNS adı
`ag.h`'den, beklenen örnek sayısı `sim3_bant.py` ile **aynı bütçeden**
hesaplanıyor. Elle yazılmış tek beklenti yok.

🔴 **`loop_azami_us` okunuyor ve 20 000 µs eşiğiyle karşılaştırılıyor.**
Aylardır açık duran çift çekirdek kararını kapatan tek ölçüm bu; artık bir
komut mesafesinde.

##### Emniyet

🔴 **Koşucu hiçbir aşamada yük sürmüyor.** Pil deşarjını başlatan komutu
bir test betiğinin kendiliğinden göndermesi kabul edilemez — ve bu bir
niyet beyanı değil, **iddiayla korunuyor**: B25 koşucunun kaynağını tarayıp
gönderdiği `p`-komutlarını çıkarıyor, `p0` (durdur) dışında bir şey varsa
kırmızı. `R!` (fabrika sıfırlama) de hiç gönderilmiyor.

NVS'e kalıcı yazan denetimler `--yazmaya-izin-ver` istiyor; varsayılan
kapalı, taze bir kartın kalibrasyonunu bringup koşusu bozmasın diye.

##### Koşucunun kendisi nasıl sınandı

Bu asıl mesele: **yanlış bir bringup testi, testsizlikten kötüdür** —
geçmeyen bir karta "geçti" der ve kusur tezgahtan çıkıp alana gider.

`kopru/kart_baglanti.py`'deki **`KayitKart`** tam bunun için vardı:
`SeriKart` ile aynı yüzey, komutlara betiklenmiş yanıt, ve yanıtı akışın
**içine** koyuyor — gerçek kartta olduğu gibi. `test_tezgah_kart.py`
(zincirde **B25**) koşucuyu bunun üzerinde iki yönlü sınıyor:

1. **Sağlıklı kart** senaryosunda her denetim yeşil
2. **15 kasıtlı bozuk senaryo** — doğru denetim kırmızı, ötekiler yeşil

| Bozuk senaryo | Yakalayan denetim |
|---|---|
| PSRAM yok (FQBN'de `PSRAM=opi` eksik) | PSRAM satırı |
| PSRAM 2 MB (yanlış modül) | PSRAM ≥ 8 MB |
| LittleFS boş (arayüz yazılmamış) | Arayüz LittleFS'te |
| Pil tamponu ayrılamadı | Tampon AYRILDI |
| `loop_azami_us` eşik üstünde | Çift çekirdek eşiği |
| Çıplak `g` **kabul ediliyor** (K3 geri geldi) | K3 tuğlalama koruması |
| `R` onaysız fabrika sıfırlıyor | Onay kapısı |
| Bilinmeyen komut sessizce yutuluyor | Açık ret |
| ADS bağlı değil / yalnız 0x48 var | I²C adresleri |
| Örnek sayısı ~100 / ~19 | Örnek sayısı bandı |
| `D` satırı hiç gelmiyor | Ölçüm satırı |

Ayrıca **telemetri ayıklama** ayrıca sınanıyor: kart sürekli `D` basıyor ve
komut yanıtı bu akışın içine düşüyor. Naif bir "gönder, bir satır oku"
%90 ihtimalle telemetri okur. **38/38 geçiyor.**

##### Öz-test koşucuda ÜÇ GERÇEK HATA buldu

Yazılmasının sebebi buydu ve daha yazılırken karşılığını verdi:

1. **`KayitKart` sonlu.** Gerçek kart sonsuza kadar `D` basıyor, kayıt
   bitiyor — `D` denetimleri kaydı tüketip **0 satır** görüyordu ve
   sağlıklı senaryoda bile kırmızıydı. Çözüm: aşamalama + `gecikme` ile
   gerçek tempoyu taklit etmek.
2. **Telemetri ayıklama testi BOŞTU.** `KayitKart.yaz()` yanıtı imlecin
   **önüne** koyuyor, yani yanıt her zaman ilk satır — ayıklanacak hiçbir
   şey yoktu (0 telemetri satırı). Test "çalışıyor" diyordu ama hiçbir şey
   sınamamıştı. Yanıtın kendisi telemetriyle sarılarak düzeltildi.
3. **Emniyet denetiminin kapsamı çok genişti.** Deseni her tırnaklı
   p-dizgesini yakalıyordu ve *"pil egri tamponu"* gibi **metinleri komut
   sanıyordu**. Artık yalnızca gerçekten gönderilen komutlara bakıyor.
   ⚠ **Aynı kapsam hatası, aynı oturumda üçüncü kez.**

##### Açılış afişi tuzağı

Afiş (PSRAM boyutu, pil tamponu, LittleFS) **yalnızca açılışta** basılıyor,
ama `SeriKart.ac()` DTR/RTS'i bilerek `DISABLE` kuruyor — bağlanmak kartı
sıfırlamıyor, yani afiş çoktan geçmiş oluyor.

`SeriKart.sifirla()` eklendi (klasik oto-reset dizisi: DTR→EN, RTS→IO0).
⚠ **Yerel USB CDC'li kartlarda etkisi yok** — orada DTR/RTS gerçek bir pine
bağlı değil. O yüzden `sifirla()` "sinyaller gönderildi" diyor, "kart
sıfırlandı" demiyor; çağıran taraf **afişi gördü mü** diye bakıyor.
Görülmezse PSRAM/LittleFS denetimleri **atlanıyor, kırmızı olmuyor** ve
kullanıcıya EN düğmesine basması söyleniyor.

`KayitKart`'a da aynı yüzey eklendi — yoksa koşucunun içinde `isinstance`
dalı doğar ve kayıtlı koşu gerçek koşudan **ayrışır**.

##### Yan düzeltme: bayat RAM sabiti

`tasarim3_sabit.ESP_DRAM_KULLANILAN` **51 084**'te donmuştu (yorumu
"güncellenir" diyordu), gerçek derleme **71 420 B**. Bu sayı B21'in *"pil
tamponu boş DRAM'in üçte birinden küçük"* iddiasını **20 KB iyimser**
besliyordu — iddia yine geçiyordu ama iddia edilen pay gerçek değildi.
Artık `_firmware.json`'dan okunuyor ve **B6 yedek sabitin ölçümle eşit
olduğunu sınıyor**, bir daha sessizce kayamaz.

##### Bağımsız araştırma iki gerçek kusur daha çıkardı

B25 hazırlanırken, "elde ne varsa onunla ne sınanabilir" sorusunu
kaynaktan cevaplaması için ayrı bir denetim koşturuldu (10 ajan, 161
doğrulanmış kalem). İki bulgusu koşucudan bağımsız, **firmware ve
zincirin kendisiyle** ilgiliydi.

🔴 **Açılış afişinde satır kapanmıyordu.** `Ag:` bloğunun sonunda
`Serial.println()` **yoktu**; çıktı şöyle yapışıyordu:

```
Ag: AP  SSID=OLCUM-KARTI-A1B2  http://192.168.4.1Arayuz: YOK — ...
```

Yani **kullanıcının seri konsoldan kopyalayacağı IP adresi bir sonraki
etikete karışıyordu** ve afiş ayrıştırılamaz haldeydi. Kart daha hiç
açılmadığı için kimse görmemişti. Düzeltildi; `sim3_web.py` artık `Ag:`
bloğunun `Arayuz:`den **önce kapandığını** ayrıca sınıyor (mutasyonla
doğrulandı: `println` geri silinince kırmızı).

🔴 **`olcum3.h` kendi kuralını çiğniyordu ve adımın iddiası yanlıştı.**
Dosyanın başında *"`int` ve `double` YASAK; her yerde açık genişlikli tip
ve `float`"* yazıyor — sebebi tek: **avr-gcc'de `double`, `float`a takma
addır (32 bit), Xtensa'da 64 bittir.** Kural, emülatörle kartın **bit
birebir aynı** aritmetiği koşturmasını garanti etmek için var.

Dört fonksiyon bu kuralı çiğniyordu (`enerji_joule3`, `enerji_wh3`,
`yuk_mAh3`, `yuk_coulomb3`), hepsi
`(float)((double)<int64> / <sabit>)` kalıbında — Aşama 1'den devralınmış
bir alışkanlık; kaynakta savunan tek satır yoktu.

Sonucu: **`uretim/avr/ornek_olcum3.c`'nin *"burada koşturulan kod,
ESP32'de koşacak kodun ta kendisidir"* iddiası bu dört fonksiyon için
DOĞRU DEĞİLDİ** — ve aynı iddia `DEVIR.md`'de ve **kullanıcıya gösterilen
belgede** (`5-muhendislik.html`: *"sınanan şey kartta çalışacak kodun ta
kendisi"*) tekrarlanıyordu.

**Ölçüldü, iki bağımsız yoldan.** Denetim kodu avr-gcc ile derleyip
projenin **kendi emülatöründe** koşturdu ve Xtensa çıktısını
disassemble etti (`__floatdidf`/`__divdf3` vs `__floatdisf`/`__divsf3`).
Ayrı olarak ben de sayısal modelle ölçtüm. İki ölçüm aynı yere çıktı:

| Büyüklük | Değer |
|---|---|
| İki yolun en kötü bağıl farkı | **6.8e-8** (1 ULP) |
| float32'nin kendi çözünürlüğü | 6.0e-8 |
| ADS1115 tek adımı | 3.1e-5 — **450 kat büyük** |
| ADS1115 kazanç hatası | 1.5e-3 — 22 000 kat büyük |

**İlk kararım "cast kalsın" idi** — çünkü `(double)` hedefte ölçülebilir
biçimde *daha doğru*: int64 uçlarında hata 0.046 yerine 0.016. Bağımsız
denetim buna katılmadı ve haklı çıktı: kazanılan şey **0.5 ULP**, kaybedilen
şey **emülatörün temsil gücü** — yani B4/B5'in bütün değerinin dayandığı
şey. Ayrıca yanlış bir iddia **kullanıcıya yayınlanmış** durumdaydı.

Dört cast kaldırıldı, saf `float`a geçildi. Mevcut 110 iddianın hiçbiri
bozulmadı — bu da denetimin *"B4/B5 bu satırları hiç ölçmüyordu"*
bulgusunu bağımsız olarak doğruluyor.

**Yeni kapsam:** `test_olcum3.py` B4.6 artık altı şey sınıyor — farkın
sınırı, ADS gürültüsüne oranı, bit-birebirlik, dosyada **hiç `(double)`
olmadığı**, kaldırma gerekçesinin kayıtta durduğu ve
`ornek_olcum3.c`'nin öncülünün artık geçerli olduğu.
`mutasyon.py`'ye de karşılığı eklendi (denetimin ayrı bir bulgusu:
**mutasyon tablosunda `olcum3.h`'ye ait tek kayıt yoktu**) — cast geri
konunca zincir kırmızı, ölçüldü.

⚠ **Açık kalan (arşiv):** `sim2_kart.py:267` Aşama 2'de beklenen değeri
**float64** modeliyle üretip emülatörün float32 çıktısıyla karşılaştırıyor.
Aşama 2 zinciri geçiyor ama model tutarsız; Aşama 2 arşiv olduğu için
dokunulmadı.

##### Yan bulgu: şema her koşuda değişiyordu

🔴 Depo GitHub'a çıkınca görüldü: `sema3-uret.py` UUID'leri
`uuid.uuid4()` ile üretiyordu, yani **şema her üretildiğinde bütün
UUID'ler değişiyordu.** 242 KB'lik `.kicad_sch` ve 114 KB'lik netlist
her zincir koşusunda **858 satırlık anlamsız bir diff** veriyordu — ve
bu her commit'te tekrarlayıp **gerçek bir tasarım değişikliğini
boğardı**.

UUID'ler artık bir sayaçtan türetiliyor (`uuid.uuid5` + sabit ad alanı).
KiCad için tek gereklilik dosya **içinde** benzersizlik; küresel
benzersizlik gerekmiyor. Ölçüldü: üç ardışık üretim **aynı SHA-256**.

Şema böylece projenin geri kalanıyla aynı disipline girdi —
**yeniden üretilebilir bir yapı**. `netlist3_dogrula.py` iki iddiayla
koruyor (mutasyon: `uuid4` geri konunca kırmızı, ölçüldü).

⚠ İddianın ilk iki yazımı **boştu**: aradığı `uuid4()` dizgesi kendi
gerekçe yorumunda ve bir docstring'te de geçiyordu, yani iddia
**kendi açıklaması yüzünden** kırmızı yanıyordu. Kapsam koda
sınırlandırıldı. *Aynı sınıf, bu oturumda dördüncü kez.*

##### Kayıt denetimi (10 ajan, 60 doğrulanmış bulgu)

Kayıt yazıldıktan **sonra** bağımsız bir denetim koşturuldu — "yeni bir
oturum bunu okuyup ne yapacağını bilebilir mi" diye. On yüksek öncelikli
bulgu çıktı ve hepsi kapatıldı:

🔴 **ESP32 gününün BİRİNCİ komutu olduğu gibi koşmuyordu.** İlk gün akışı
çıplak `arduino-cli compile` yazıyordu; ikili **PATH'te değil**,
`Elekronic/.araclar/` altında. Üstelik FQBN iki komutta **elle
tekrarlanıyordu** — tek kaynak `hedef2.py` olduğu hâlde. `uretim/yukle.py`
ikisini birden kapattı: `arduino-cli`'yi buluyor, FQBN'i `hedef2.py`'den
okuyor.

🔴 **DEVIR kendi içinde çelişiyordu:** aynı bölüm hem "24 denetim / 13
senaryo / 36-36" hem "27 denetim / 15 senaryo" diyordu. Sayılar
tazelendi; `--liste` artık **aşama başına** sayıyı basıyor.

🔴 **Bölüm 6.1'in emniyet kutusu** hâlâ *"pil + WiFi ile yüzdür"*ü
koşulsuz çözüm diye sunuyordu — 5.12.40'ın düzeltmesi oraya işlenmemişti.
Yalıtımlı kutu şartı eklendi.

🔴 **`tezgah_kart.py` boş bir vaat taşıyordu:** docstring "aşama 2 = değer
denetimleri" diyordu ama o aşamaya ait **tek denetim yoktu**; `--asama 2`
ile `--asama 1` aynı kümeyi koşturuyordu. Docstring dürüstleştirildi ve
`--liste` boş aşamayı **açıkça** gösteriyor.

🔴 **README'nin `#safety` bağlantısı yanlış yere gidiyordu** — lisans
bölümünü eklerken elektriksel emniyet metnini başlıksız bırakmışım, yani
*"615 V öldürür"* uyarısına giden bağlantı **ağ güvenliği** paragrafına
düşüyordu. Bölüm yeniden kuruldu: **elektriksel önce**.

🔴 **Envanteri iki değil ÜÇ adım okuyor.** B11 bunu `.exists()` ile
korumuyordu: temiz bir klonda iddia sessizce başarısız oluyor ve
*"envanter.csv okundu (0 B): 7912 var"* gibi anlamsız bir mesaj veriyordu.
B16'nın deseni uygulandı — atlama duyuruluyor, iddia sayısı korunuyor.

🔴 **Skop çözünürlüğü altı dosyada iki farklı tabandan** yazılıydı:
"11.1 → 26.9 mV" — öncesi **etkin aralıktan** (2.9 V), sonrası
**nominalden** (3.1 V). B20 adımın bir LSB olduğunu, yani nominalden
türediğini söylüyor. Hepsi aynı tabana getirildi (**11.9 → 28.8 mV**) ve
kullanıcı kılavuzu artık `SKOP_ADIM_ESKI` sabitinden türetiyor.

🔴 **`4-kurulum.html`'de `<!doctype>`, `charset` ve `viewport` yoktu** —
sekiz sayfadan yalnızca onda. Tezgahta okunacak, Türkçe karakterli bir
sayfa için tarayıcının kodlamayı tahmin etmesine bırakılmıştı.

##### Doğrulama

Zincir **18/18**, 75 tezgah kalemi (güncel iddia sayısı
`beklenen_sayim.json`'da). B25 `--liste` ile ne koşacağını yazıyor;
`--sifirla` olmadan afiş denetimleri atlanıyor. Bringup koşucusu
**27 denetim** yapıyor, öz-testi **15 bozuk senaryoyu** yakalıyor.

⚠ **Bu adım gerçek donanımı doğrulamıyor.** Yalnızca koşucunun doğru soruyu
sorup doğru cevaba baktığını sınıyor. Gerçek seri port, gerçek zamanlama ve
gerçek USB CDC davranışı yarın görülecek.

---

#### 5.12.42 ✅ B26 — KART GELDİ: İLK GERÇEK BRINGUP (2026-09-11)

ESP32-S3 elde. Firmware yüklendi, arayüz karta yazıldı, aşama 0 bringup
koşuldu. **Tasarım zinciri 18/18 yeşilken üç kusur çıktı** — ikisi
yalnızca gerçek donanımda görülebilirdi.

##### Kart gerçekten N16R8 mi — etikete değil silikona soruldu

`esptool flash-id`: ESP32-S3 (QFN56) rev v0.2 · flash **16 MB** ·
**Embedded PSRAM 8 MB (AP_3v3)** · MAC `…:96:9c` (tam adres kasıtlı kısaltıldı — depo herkese açık).
Açılış afişi: `PSRAM: 8192 KB`, pil eğri tamponu 86400 nokta = 24 saat,
**1012 KB PSRAM'de**.

Yani `hedef2.py`'nin uyarısı karşılandı: *"Derleme başarılı olması kartta
PSRAM bulunduğunu KANITLAMAZ — kanıt açılış satırıdır."* PSRAM hem var
hem gerçekten kullanılıyor. `PSRAM=opi` ve `FlashSize=16M` doğru seçim.

##### Hangi soket — VID ile ayırt edilir, "port göründü" yetmez

COM yazan soket: **CH343** USB-UART köprüsü (`VID_1A86` / `PID_55D3`,
wch.cn) → `COM6`. Sürücü Windows 11'de hazır geldi.

⚠ **"Bir COM portu belirdi" doğru sokete takıldığının kanıtı DEĞİL.**
ESP32-S3'ün içinde ayrı bir USB Serial/JTAG birimi var; yerel USB
soketine takılırsa Windows **yine** bir COM portu açar (`VID_303A`) ama
firmware `Serial`i UART0'da tuttuğu için o port **sessiz** kalır.
Ayırt edici ölçüt VID: `1A86`/`10C4`/`0403` = köprü çipi (doğru soket),
`303A` = yerel USB (yanlış soket).

`esptool`'un `Hard resetting via RTS pin` satırı da doğru sokette
olunduğunu bağımsız olarak doğruluyor — DTR/RTS otomatik reset yalnızca
köprü çipinde çalışıyor.

##### 🔴 Kusur 1 — AP SSID MAC'ten GELMİYORDU

`ag.h`'de sıra tersti:

```c
String ap = ag_ap_ssid();   // WiFi.macAddress(m) BURADA
WiFi.mode(WIFI_AP);         // WiFi ancak BURADA başlıyor
```

Kayıtlı ev ağı yokken (varsayılan durum) WiFi sürücüsü o ana kadar hiç
başlamamış oluyor. `esp_wifi_get_mac` böyle bir durumda
`ESP_ERR_WIFI_NOT_INIT` dönüp tampona **dokunmuyor**, yani `m[6]`
**ilklenmemiş yığın belleği** olarak SSID'e giriyordu.

**Kanıt:** gerçek MAC `…96:9c` iken ad, firmware yazıldıktan sonraki ilk
açılışta `OLCUM-KARTI-0400`, sonrasında **hep** `OLCUM-KARTI-ABAB`
(`AB AB` = tekrarlayan dolgu baytı deseni). Dört sıcak reset boyunca
sabit kaldığı için kusur *"rastgele ad"* gibi de görünmüyordu — aynı kod
yolu aynı yığın içeriğini bıraktığından **deterministik çöp** üretiyor.

⚠ Bu, "sabit olması doğru olduğu anlamına gelmez" sınıfının iyi bir
örneği: ilk hipotezim *"her açılışta değişiyor"* idi, dört resetlik
deney bunu **çürüttü**, ama kusur yine de oradaydı.

**Neden önemli:** B22'nin bütün *"telefondan, bilgisayarsız kullan"*
hikâyesi bu ada dayanıyor. Ad değiştiği her seferde telefondaki ağ
profili kırılıyor ve 12 karakterlik AP parolası elle yeniden giriliyor.
Ayrıca AP parolasını MAC'ten **türetmeme** kararının gerekçesi (*"SSID
zaten MAC son ekini yayınlıyor"*) fiilen yanlıştı.

**Düzeltme:** `esp_read_mac(m, ESP_MAC_WIFI_SOFTAP)` — eFuse'tan okur,
sürücünün başlatılmış olmasını gerektirmez, hem STA hem AP yolunda
çalışır. Kartta doğrulandı: **`SSID=OLCUM-KARTI-969C`**,
`MAC=…:96:9C`. (softAP MAC son baytı artırmıyor, ilk oktetteki
yerel-yönetim bitini kuruyor: `68`→`6A`.)

**Neden eski koşucu yakalamadı:** *"Ag kipi bildirildi"* denetimi yalnızca
satırın **var olduğuna** bakıyordu, içeriğin tutarlılığına değil.

Yeni denetim: afiş artık softAP **ayağa kalktıktan sonra** okunan gerçek
MAC'i de ilan ediyor ve `tezgah_kart.py` SSID sonekini onunla
karşılaştırıyor. ⚠ MAC'i `ag_ap_ssid()` ile **aynı kaynaktan** okusaydı
test totoloji olur ve eski kusuru kaçırırdı — bağımsızlık kasıtlı.

##### 🔴 Kusur 2 — çift çekirdek ölçütü kırılgandı → **KARAR ÇIKTI**

`loop_azami_us` açılıştan beri sıfırlanmayan **koşan maksimum** ve ısınma
payı yok (ölçüm ikinci `loop()` turunda başlıyor). Yani `setup()` sonrası
WiFi/mDNS ayağa kalkarken oluşan tek seferlik bir sıçrama kalıcı olarak
çakılıyordu.

Ölçülen: taze açılışta **18 203 µs** (eşiğin ALTINDA, 0 uzun tur),
dakikalar sonra **30 397 µs** (ÜSTÜNDE). **Aynı kart, ne zaman baktığına
göre iki farklı cevap veriyordu** — ve 5.12.34'ün *"bu tek ölçüm aylardır
açık duran mimari kararı kapatıyor"* dediği ölçüt buydu.

Firmware'e **`K` komutu** eklendi: blokaj sayaçlarını sıfırlar, **eski
değerleri basarak** (bu projede bir sayının sessizce kaybolması kabul
edilmiyor). Koşucu artık sıfırlayıp **45 sn kararlı hal** ölçüyor.

**Sonuç:** sıfırlamadan sonra 45 sn'de yine **30 382 µs**, 1 uzun tur.
Yani ~30 ms'lik olay **açılış sıçraması değil, kararlı halde ~45 sn'de
bir tekrarlıyor.** İlk yorumum *"muhtemelen açılış artığı"* idi; **ölçüm
onu çürüttü.** Tahmin etmek yerine sayacı eklemenin karşılığı buydu.

→ **DEVIR 5.12.34'ün kararı: ölçüm döngüsü çekirdek 1'e taşınacak.**

⚠ İki sınır: (1) ölçüm **ADS'ler bağlı değilken** alındı — ama 30 ms'lik
bir blokaj I²C okumasından gelemez (WiFi/mDNS bakımı olması muhtemel),
ADS eklemek bunu iyileştirmez, kötüleştirir. (2) `atlanan_ms` **hep 0**:
enerji penceresi kaçmıyor, yani bugün enerji sayacı zarar görmüyor; asıl
risk skop/örnekleme sürekliliğinde.

##### 🔴 Kusur 3 — bayat `f` denetimi (firmware doğru, TEST yanlıştı)

`d_ciplak_f_reddi` çıplak `f`'in `! f: frekans gerekli` ile reddedilmesini
bekliyordu ve gerçek kartta **kırmızı** döndü. Ama B22.1 bunu bilerek
değiştirmiş: çıplak `f` artık `F`/`P` gibi **değeri basıyor**
(`* sebeke frekansi 50.00 Hz`, kartta doğrulandı). Hata mesajı yalnızca
**bozuk** girdide (`fabc`) çıkıyor. Denetim `g`/`i` desenini kopyalarken
`f`'in farklı tasarımını görmemiş.

⚠ Üstelik kayıt tabanlı sahte kart da `f` için hata dönüyordu, yani
**bayat denetimi "doğruluyordu"**. İkisi birlikte onarıldı; artık iki şey
sınanıyor: çıplak `f` değeri basıyor **ve** `fabc` reddediliyor.

**Ders:** yeşil test bir şey kanıtlamaz — ama **kırmızı test de tek
başına kusur kanıtlamaz.** Önce kaynağa bakılır.

##### 🔴 Kusur 4 — koşucu `D` satırında YANLIŞ ALANI okuyordu

Aşama 1 ilk kez gerçek donanımda koşuldu (tek ADS, `0x48`) ve
**`ornek = 0`** raporladı. Kart suçsuzdu. Biçim:

```
D <volt> <amper> <watt> <joule> <wh> <ms> <ornek> <menzil>
```

Örnek sayısı **7.** alan, son alan `menzil`. `d_ornek_sayisi` ise
`split()[-1]` ile **son** alanı okuyor, yani menzili (NORMAL = `0`)
örnek sayısı sanıyordu.

**Neden kaçtı:** `test_tezgah_kart.py`'deki sahte kart da örnek sayısını
son alana koyuyordu. İkisi **birbiriyle tutarlı**, ikisi de firmware'den
farklıydı. Yandaki *"İlan edilen alan sayısı firmware biçimiyle AYNI"*
denetimi yalnızca **sayıya** bakıyor, **sıraya** bakmıyordu — `8 == 8`
olduğu için sessiz kaldı.

⚠️ Bu, B22.2'deki *"bir iddia düşerken başkası eklendi, toplam sabit
kaldığı için mutasyon kaçtı"* olayının **alan sırası sürümü.** Aynı sınıf:
**bir sayı korunuyor diye içerik korunuyor sanmak.**

**Düzeltme:** indeks artık **afişin ilan ettiği alan adlarından**
türetiliyor (`_ornek_indeksi`); firmware sırayı değiştirirse ayrıştırıcı
peşinden gider. Sahte kartın alan sırası gerçeğe uyduruldu. Üç yeni iddia:
protokol ilanı `ornek`i adlandırıyor mu · sahte kart onu **ilan edilen**
yere koyuyor mu · koşucu aynı indeksi afişten türetiyor mu. **Sahte kartın
kendi kendine tutarlı olması artık yetmiyor.**

##### İlk gerçek ölçüm: örnekleme hızı 4 kat düşük

Düzeltilmiş ayrıştırıcıyla, tek ADS bağlıyken:

| | |
|---|---|
| `ornek` | **33** / 200 ms → **~162 örnek/s** |
| beklenen | 133 / 200 ms → **665 örnek/s** |
| tur süresi | 203.5 ÷ 33 = **6.17 ms** |
| zaman aşımı yolu | 4000 µs + 1300 µs yedek + I²C ≈ **6.2 ms** |

Sayılar sebebi tek başına söylüyor: **ALERT/RDY sinyali gelmiyor**, kod
her turda `yeni_donusum_bekle(4000)`'de zaman aşımına düşüp
`delayMicroseconds(1300)` yedeğine kaçıyor.

Firmware doğru: eşik yazmaçları (`0x8000`/`0x0000`) `ADS_AKIM`'a
yazılıyor, `pinMode(PIN_HAZIR, INPUT_PULLUP)` kurulu. **Fiziksel bağlantı
sınanacak.** ⚠ `ALRT` pininin iki komşusu (`ADDR`, `A0`) bu kurulumda
GND'ye bağlı; tel bir delik kayarsa GPIO7 sürekli LOW kalır ve belirti
*"tel hiç yok"* ile **birebir aynı** olur.

⚠ Bu, B20'nin 91 SPS'inin **aynı sınıfı ama aynısı değil**: orada pin
yüksek empedansta kalıyordu (COMP_QUE=11b), burada firmware doğru,
donanım yolu şüpheli.

##### 🔴 Kusur 5 — ALERT/RDY KENAR YÖNÜ TERSTİ (162 SPS'in asıl sebebi)

Kablolama süreklilikle doğrulandı, 3V3 rayı 3.26 V — donanım sağlamdı.
Sebebi tahmin etmek yerine GPIO7'yi doğrudan dinleyen geçici bir tanı
yazılımı yüklendi (yalnızca `0x48` ile konuşuyor, yani eksik ikinci ADS
hipotezi tamamen devre dışı):

```
GPIO7 bosta: HIGH (beklenen)     -> kablo doğru, GND'ye kaçmamış
Hi_thresh=0x8000  Lo_thresh=0x0  -> eşikler yazıldı VE geri okundu
RDY dustu: EVET @1228 us         -> pin DÜŞÜYOR, tam dönüşüm süresinde
kalkti: HAYIR                    -> ama GERİ KALKMIYOR
```

Kontrol grubu (`COMP_QUE=11`, pin yüksek empedans) hiç darbe vermedi —
ölçüm düzeneğinin kendisi doğrulandı.

`yeni_donusum_bekle` önce **düşmeyi**, sonra **kalkmayı** bekliyordu. ADS'in
RDY pini ise dönüşüm bitince LOW'a çekip **öyle kalıyor**; pini geri
kaldıran şey **yeni dönüşümü başlatan ayar yazması**. (İlk hipotez "okuma
kaldırır"dı, o da ölçülüp çürütüldü: `okuma oncesi LOW | okuma sonrasi LOW`.)

Yani ikinci döngü **hiç gelmeyecek bir kenarı** bekliyor, her turda
4000 µs zaman aşımı + 1300 µs yedek = ölçülen 6.17 ms.

**Düzeltme:** kenar yönü ters çevrildi — önce kalkmayı (yeni dönüşüm
başladı), sonra düşmeyi (dönüşüm bitti) bekle. Ters sıra ayrıca teorik bir
yarışa açıktı: ayar yazması bitmeden pin hâlâ LOW iken bakılırsa ÖNCEKİ
dönüşüm okunur. Tezgahta 300 turda **sıfır zaman aşımı**, 620 örnek/s.

| | önce | sonra |
|---|---|---|
| örnek / 200 ms | 33 | **97** |
| örnek/s | 162 | **485** |
| tur süresi | 6.17 ms | 2.06 ms |

⚠️ **Bu kusur B20'nin düzeltmesinin ALTINDA duruyordu.** B20 `COMP_QUE=11b`
sorununu doğru teşhis edip düzeltmişti (91 SPS) — ama kenar yönü hatası
altta kaldı ve donanım olmadığı için 665 SPS hiç ölçülmemişti.
**Düzeltilmiş bir kusurun arkasında ikinci bir kusur.** Zincire kenar
yönünü sınayan iddia (`sim3_bant.py` 1b-bis) ve onu yalanlayan mutasyon
eklendi.

Kalan 97 → 133 farkının sebebi eksik `0x49`: firmware her turda ona da
yazıp okumaya çalışıyor. Yalın testte (tek ADS) 1.61 ms/tur, firmware'de
2.06 ms. **Tahmin: ikinci ADS takılınca bant tutar** — sınanabilir.

##### Web katmanı gerçek donanımda açıldı

Kart ev ağına alındı (`Na`/`Np`), web parolası kuruldu (`Ns`). Atlanan
5 denetim koştu ve **hepsi yeşil**:

| Denetim | Sonuç |
|---|---|
| Arayüz servis ediliyor | 200 · 26 683 bayt (gzip'li 8 046) |
| CSRF — özel başlık zorunlu | 400 |
| Geçersiz jeton | 403 |
| **`p0` jetonsuz geçiyor** | **204** ← emniyet özelliği |
| Yabancı Host (DNS rebinding) | 403 |

⚠️ Ama önce **beş koşucu kusuru** çıktı, hepsi kartı haksız yere suçluyordu:

1. **`Content-Type`.** `urllib` gövde verilince başlık yoksa
   `application/x-www-form-urlencoded` ekliyor; ESP32 `WebServer` onu FORM
   diye ayrıştırıp ham gövdeyi `arg("plain")`'e koymuyor → 400 "bos komut".
   Koşucu bunu *"`p0` GEÇMİYOR — EMNİYET kusuru"* diye raporluyordu.
   **Olmayan bir emniyet kusuru uyduruyordu**, ki bu yanlış-yeşilden beter.
   Ölçüldü: form-ct → 400, `text/plain` → 204.
2. **gzip.** Kök sayfa `Content-Encoding: gzip` geliyor; `urllib` açmıyor,
   denetim ham baytta `<!doctype` arıyordu.
3. **Afiş penceresi.** STA kipinde afiş `AG_STA_BEKLE_MS` (10 s) kadar
   gecikiyor; sabit 3 sn yüzünden afişe dayanan **12 denetim birden
   atlandı** ve koşu "23 geçti · 12 atlandı" diye yanıltıcı göründü. Artık
   `D` satırı görünene kadar bekliyor, tavan `ag.h`'den türetiliyor.
4. **SSID/MAC denetimi** STA kipinde yanlış kırmızı veriyordu — orada SSID
   yönlendiriciden geliyor, MAC'ten türetilmiyor. Artık AP kipi dışında
   atlanıyor.
5. **Parola uyarısı** "uyarı metni var mı" diye bakıyordu; parola kurulunca
   metin kaybolur ve denetim kırmızı olurdu — oysa o tam istenen durum.
   Artık koşullu: korumasızsa uyarı OLMALI, korumalıysa yanıltıcı uyarı
   OLMAMALI. İki yön de sınanıyor.

**Sonuç: 23 geçti · 5 kaldı · 12 atlandı → 48 geçti · 3 kaldı · 1 atlandı.**

##### NVS kalıcılığı — yeni kalıcı denetim

`NVS kalibrasyon kaliciligi` eklendi (tehlike sınıfı `NVS-yazar`, yani
`--yazmaya-izin-ver` olmadan koşmuyor). Ayırt edici bir değer yazıp
resetleyip hayatta kaldığını doğruluyor, sonra **eski değeri geri
yüklüyor** — tezgahta iz bırakmıyor. Gerçek kartta doğrulandı.

⚠️ İlk yazımı **boş bir iddiaydı**: `i_ofset` kullanıyordu ve girişler
GND'deyken hem varsayılan hem ölçülen değer 0 olduğu için NVS hiç
çalışmasa da `0 == 0` diye geçerdi. `s<ohm>`'a geçildi. Sahte kartın da
bunu modelleyebilmesi için küçük durumlu `AyarliKart` yazıldı — **durumsuz
bir taklit bu soruyu cevaplayamıyor**, ki boş iddianın kaynağı tam buydu.

##### PC köprüsü ilk kez gerçek kartla

`kopru/` tamamen sınanmamıştı. Uçtan uca çalıştığı görüldü: seri↔SSE
rölesi (6 sn'de 32 olay ≈ kartın rapor hızı), jeton, sürücü hakemi, disk
arşivi (gün dosyası gece yarısı döndü). Stok sunucusunu bozmuyor:
`127.0.0.1` stoka, köprü LAN adresine düşüyor.

##### Çift çekirdek: olay PERİYODİK, 30 saniyede bir

Daha önce "45 sn kararlı halde 30 382 µs" denmişti; o ölçüm **bozuk
firmware'le** ve tek pencereyle alınmıştı. 180 saniye ölçüldü:

```
 30 sn -> K 0 26209 1      120 sn -> K 0 26342 4
 60 sn -> K 0 26209 2      150 sn -> K 0 26342 5
 90 sn -> K 0 26342 3      180 sn -> K 0 26342 6
```

**Her 30 saniyede tam bir tane ~26 ms blokaj**, aralarda döngü en fazla
2.4 ms, `atlanan_ms` hep 0. Karar değişmiyor (eşik 20 ms aşılıyor) ama
gerekçe artık çok daha sağlam: seyrek/rastgele değil, **periyodik** —
muhtemelen mDNS ya da WiFi bakımı.

⚠️ Bu, koşucudaki bir iddiayı da düzeltti: "sayaçlar sıfırlandı mı" 45 sn
BEKLEDİKTEN SONRA bakıyordu, ama periyodik olay o pencerede değeri geri
tırmandırıyor — sıfırlama kusursuz çalışırken bile kırmızı dönüyordu.
Sıfırlamanın kanıtı **sıfırlama anındaki** değerdir.

##### Arayüz: sayfayı kart sunarken kip `seri`de kalıyordu

Kullanıcı `http://olcum.local`'ı açtı, "bağlı değil" gördü, telefonda hiç
açılmadı. Sebep: `kopruyuAlgila()` otomatik kip seçimi için `/durum`
ucunu yokluyor — o uç **yalnızca PC köprüsünde** var, kartta 404. B22.3
bu algılamayı köprü için yazmış; B22.4/B22.5 sonradan kartı da sunucu
yapmış ama algılama genişletilmemiş. Kart sunarken yoklama sessizce
başarısız oluyor, kip `seri`de kalıyor, Web Serial de güvenli bağlam
olmadığı için çalışmıyor.

İkinci kusur: hata metni *"tarayıcı Web Serial desteklemiyor"* diyordu.
Chrome destekliyor — `navigator.serial` **güvenli bağlam** istiyor ve
`http://olcum.local` güvenli bağlam değil. Metin yanlış yere baktırıyordu.

**Düzeltme:** sayfayı localhost olmayan bir adres sunuyorsa sunan taraf
kart ya da köprüdür, ikisi de `/akis` veriyor → doğrudan akış kipi.
Mesaj artık `window.isSecureContext`'e bakıp gerçek sebebi söylüyor.
Headless tarayıcıda doğrulandı: kip kendiliğinden "WiFi / köprü (akış)",
kırmızı kutu yok, sayfa tam render.

##### SSE: her satır İKİ KEZ yayınlanıyordu

Yayını ölçerken kart 5/s rapor ederken SSE'den **10/s** geldi:
8 sn'de 80 `D` olayı, 40 benzersiz satır, dağılım `{2: 40}` —
istisnasız hepsi çift. Sebep: B20 `loop()`'a `akis_yolla(son_satir)`
eklediğinde SSE'yi besleyen tek yol oydu; **B22.4 `Serial` aynasını
getirdi** (tamamlanan her satır zaten aynadan gidiyor) ama eski çağrı
kaldırılmadı. `K` satırında da aynısı. Bedeli: iki kat WiFi trafiği,
grafikte üst üste noktalar, CSV'de çift satır.

İki çağrı da kaldırıldı; ölçüldü: 40 olay / 40 benzersiz / `{1: 40}`.
Zincire *"`akis_yolla` yalnızca ayna geri çağrısından çağrılır"* iddiası
ve onu yalanlayan mutasyon eklendi.

⚠ **Bir mekanizma daha genelini getirdiğinde eskisini KALDIR.** İkisi
birlikte çalışırsa sonuç sessizce iki katına çıkar.

##### Gizlilik: yayınlanan depoda 59 kişisel iz + geçmişte kullanıcı adı

Kullanıcının isteğiyle iki bağımsız ajan depoyu denetledi (çalışma
ağacı + tüm git geçmişi). **Parola, e-posta, ağ kimliği yok** — ama:

* **HEAD'de 59 mutlak yol** (`C:\<proje kökü>\...`): `b15-arastirma.md`
  56×, `arsiv/*/tam-dogrulama.txt` 2×, üç netlist. Kural `dogrula3.py`'de
  bir **yorum** olarak duruyordu — ve **yorum kuralı korumaz.**
* Netlist temizliği vardı ama **işe yaramıyordu**: B3 temizliyor, B9
  netlist'i **sonradan yeniden üretiyordu**. Üstelik `count=1` ile
  yalnızca ilk geçişi değiştiriyordu.
* **Git geçmişinde `076a366`** (ilk yayın): `b15-arastirma.md`'de üç satır
  Windows kullanıcı klasörü altındaki geçici bir yol — B24'te temizlenmiş ama geçmişte
  duruyor. Windows hesap adı + ölü bir oturum UUID'si; kimlik bilgisi yok.
  **Geçmişi yeniden yazmak kullanıcının kararı**, yapılmadı.
* Benim MAC fikstürüm (`test_tezgah_kart.py`) gerçek kartın OUI'sini
  taşıyordu; DEVIR'deki kasıtlı kısaltmayla birleşince tam adres
  kurulabiliyordu. Sentetik OUI'ye (`02:00:00`) çevrildi.
* ⚠ **Bu ortamda `grep` güvenilmez.** Ajan `grep -i` ile birden fazla
  `-e` deseninin çöktüğünü (`Aborted`) ve `2>/dev/null` varsa **sessizce
  boş** döndüğünü bildirdi. Benim ilk taramam da bu yüzden "temiz"
  demişti. Gizlilik taraması artık saf Python.

**Düzeltmeler:** `netlist_temizle.py` (tek kaynak, her üretim yerinde
çağrılıyor, tüm geçişler) · 59 yol depoya göreli yapıldı (klonlayan için
zaten daha kullanışlı) · **`gizlilik_dogrula.py`** yeni araç, zincirin
bir **değişmezi** olarak her koşuda çalışıyor (adım değil; deponun
tamamına ait) · iki mutasyon (yol + e-posta enjeksiyonu) yakalanıyor.

⚠ Tarayıcı ilk yazımında **kendi test verisini yakaladı** — `mutasyon.py`
örnekleri ve `netlist_temizle.py` docstring'i. Metin tabanlı iddianın kendi
açıklamasını yakalaması, bu projede **beşinci** kez.

##### Mutasyon koşucusu bu oturumda benim iddiamı çürüttü

Yeni SSID denetimi için iki mutasyon yazıldı. İkincisi — afişten `MAC=`
satırını silmek — **KAÇTI**: iddiam `"MAC=" in INO` diyordu ve `N` komut
çıktısındaki kopya onu yeşil tutuyordu. Koşucu afişi okuyor, `N`'i değil.
Kapsam `setup()` gövdesine daraltıldı, mutasyon artık yakalanıyor.

⚠ **Bu tam olarak B23.3'te koşucunun kurulma gerekçesiydi** ve ilk turunda
üç boş iddia bulmuştu. Bugün dördüncüyü buldu — **yazan bendim.**

##### Yan düzeltmeler

* `test_tezgah_kart.py`'deki *"24 denetim / 72 kalem"* elle yazılıydı ve
  **ikisi de bayattı** (gerçek 27/75) — üstelik kalem sayısı `_tezgah.md`'nin
  kendi son satırında doğru yazıyordu, yani üretilen belge **kendi içinde
  çelişiyordu**. Denetim sayısı artık `len(TK.DENETIMLER)`'den türetiliyor,
  kalem sayısı hiç yazılmıyor.
* `yukle.py` derlerken `--clean` geçmiyor, zincirdeki `test_firmware3.py`
  geçiyor (B21 dersi: önbellek uyarı gizler). Bugün zararsız çıktı —
  temiz derleme de **0 uyarı** ve **bayt bayt aynı** boyut verdi — ama
  ayrışma yüzeyi duruyor.
* `mutasyon.py` geçici kopya dizinini `_mutasyon-<pid>` diye açıyor ve
  dizin varsa **çöküyor**. Windows PID'leri geri dönüştürdüğü için bir kez
  tetiklendi; `dirs_exist_ok` ya da önceden temizleme gerekiyor.

##### Henüz sınanmayanlar

* **Web katmanı** — 5 denetim atlandı, `--http` istiyor. PC'nin kartın
  AP'sine katılması gerek: `OLCUM-KARTI-969C`, parola seri konsoldan
  (`N` komutu) okunuyor.
* **Aşama 1** — ADS1115'ler bağlanınca. I²C taraması şu an boş (beklendiği
  gibi); envanterde 3 modül var (MOD003).
* **`_tezgah.md`'nin ilk gün kalemleri** — multimetre isteyenler.

---

#### 5.12.43 📋 B27 — ARAYÜZ YENİDEN YAPIMI: PLAN (2026-09-12, onaylandı)

Kullanıcı gerçek kartta arayüzü açtı ve iki şey istedi: *"yavan ve karışık,
her yerde bildirim; ayrı sayfalar olsun; PC'de güzel görünsün"* ve demin
bulunan beş kusurun çözülmesi.

**Teknik zemin — değişmeyecek kararlar:**

* Arayüz **tarayıcıda** çalışır; ESP32 yalnızca dosya sunar + SSE akıtır.
  Animasyon/sayfa/renk ESP'ye **yük bindirmez.** ESP'yi ilgilendiren:
  dosya boyutu (LittleFS 917 KB) ve istek sayısı (tek çekirdek servis).
* **Vue 3'te kalınıyor.** Framework değişimi kazandırmaz, kaybettirir:
  `test_arayuz3.js` (122 iddia) Vue'ya bağlı, "derleme adımı yok" ilkesi
  bozulur. Eksik olan yönlendirme ve tasarım.
* **Hash yönlendirme** (`#/olcum` …) — stok-takip'te kanıtlanmış desen.
  Tek HTML, sıfır ek istek.
* Aynı kod PC + telefon; CSS kırılma noktası.

**Aşama 0 · Doğruluk** — sahte sayıyı güzelleştirmek yanlış olur

| # | Kusur | Düzeltme |
|---|---|---|
| K1 | `ads_oku` yanıt gelmeyince sessizce 0 dönüyor; kalibrasyon o sıfıra uygulanıp **1.716 V** gösteriliyor (ters çevrilmiş `n_sifir`). Çip bozulunca da aynı sahte sayı | Firmware hata bayrağı; `D` satırına durum alanı; arayüzde "veri yok" |
| K5 | Şönt menüsü `localStorage`'daki tercihi gösteriyor, karttan hiç okumuyor (menü 10R, kart 0.1R) | Bağlanınca `?`'den `sont`/menzil/kalibrasyon okunur |
| K2 | "geri besleme" etiketi gürültüde yanıp sönüyor | Ölü bant |
| K4 | Skop metni "0–48.7 V tek yönlü" — B19 çift yönlü yaptı | Metin `tasarim3_sabit`'ten türetilir |
| K3 | Hızlı ölçüm boş pinden 223.5667 W basıyor | Sinyal varlığı eşiği, altında "sinyal yok" |

Her biri: iddia + mutasyon + kartta doğrulama.

**Aşama 1 · Yapı** — beş görünüm, kalıcı üst şerit

```
#/olcum   Ölçüm      KPI + zaman grafiği          (açılış)
#/skop    Osiloskop  skop + hızlı ölçüm
#/pil     Pil testi
#/ayar    Ayarlar    kalibrasyon · şönt · menzil · ağ
#/konsol  Konsol     ham satırlar, komut
```

Üst şerit: bağlantı durumu, kart adı, **tek** bildirim alanı. Emniyet
uyarısı (J7/J3) ayrı ve kalıcı. `test_arayuz3.js`'nin "her firmware komutu
arayüzden erişilebilir" denetimi korunur.

**Aşama 2 · Tasarım sistemi** — tek kaynak CSS değişkenleri; laboratuvar
cihazı yönü (koyu zemin, fosfor izler, tabular rakamlar, tek vurgu);
ölçülü hareket; açık/koyu tema sistem tercihine uyar.

**Aşama 3 · PC ↔ telefon** — telefonda KPI + grafik + durdur, gerisi katlanır.

**Aşama 4 · Doğrulama** — her görünüm headless Edge ile render (B22.0
dersi: zincir render etmiyor); gzip toplam **< 250 KB**, dosya **≤ 8**;
ilk yükleme karta karşı ölçülür; PC + telefonda gerçek deneme.

Çok oturumluk iş. Aşama 0 ≈ 1, 1 ≈ 1, 2 ≈ 1-2, 3-4 ≈ 1.

##### ✅ Aşama 0 bitti (2026-09-12) — beşi de gerçek kartta doğrulandı

| # | Yapılan | Kanıt |
|---|---|---|
| **K1** | `ads_oku` hata bitini kuruyor/temizliyor; `D`'ye 10. alan **`durum`** (bit0 V, bit1 I okunamadı); enerji `if (!ads_hata)` kapısıyla birikiyor; arayüz "—" ve "veri yok — ADC yanıt vermiyor" gösteriyor | Tek ADS ile `D … 97 0 1`; koşucu I²C taramasıyla tutarlılığını doğruluyor (`0x49 YOK → durum=1, kart 1 dedi`). **Enerji 0.03 J çöpten 0.0000'a düştü** |
| **K2** | `gucYon` ölü bandı 1 mW | −10 µW etiket üretmiyor, −6 W hâlâ "kaynak" diyor (birim test) |
| **K3** | `hizli_yolla` ham ADC ortalaması raydaysa (<%2 / >%98) `! hizli yol: giris RAYDA` basıp **W'yi atlıyor**; arayüz eski sonucu siliyor | Kartta 3/3: `V ham ort=6…62` — 218 W artık hiç basılmıyor |
| **K4** | Skop metni "−63.5 … +46.8 V, çift yönlü"; `sim3_bant.py` metni `SKOP_MENZIL_EKSI/ARTI` ile karşılaştırıyor | 57/57 |
| **K5** | Bağlanınca `?` gönderiliyor; `A menzil=… sont=…` ayrıştırılıp menü **kartın** değerine uyduruluyor; uyuşmazlık görünür | 0.1 → menü `0.1`; 0.123456 → menü dokunulmaz, "uyuşmuyor" uyarısı |

**Mutasyon kapsamı genişledi:** `mutasyon.py` artık `.js` betikleri de koşuyor — `test_arayuz3.js`'in 138 iddiası ilk kez mutasyon altında (önce **hiçbiri** sınanmıyordu). B7: 2/2, B20: 6/6 yakalanıyor.

**Bu aşamada yakalanan kendi hatalarım** (hepsi mutasyon ya da test tarafından):

* K3'ün ilk ölçütü "ortalama raydada **VE** yayılım < 41 LSB" idi; kartta **kaçırdı** — boştaki pin gürültülüdür (yayılım >41), 218 W yine basıldı. Yayılım rayda olmanın kanıtı değil; ortalama yeter.
* K1 kaynak iddiası `"ads_hata" in blok` idi; mutasyon **kaçtı** — `ads_hata_pencere` alt dizge olarak eşleşiyordu. Kelime sınırı eklendi.
* K3 sıra iddiası `RAYDA[^}]*return;` idi; iç `if {}` blokları yüzünden **doğru kodda bile** kırmızıydı. Sıra tabanlı yazıldı.
* `test_tezgah_kart.py` ve `test_arayuz3.js` D alan sayısını **sabit** (`8` / `9`) yazmıştı; "kaynaktan türetiliyor mu" iddiası beklentiyi elle tutuyordu. İkisi de bağımsız sayımla karşılaştırıyor artık.
* Heredoc `\n` tuzağına **üç kez** düşüldü (`mutasyon.py`'ye çok satırlı dizge, `app.js`'e `\b` → backspace 0x08). Hafızadaki ders, tekrar.

⚠ **Aşama 2 tezgah kalemi:** K3'ün %2 rayda eşiği gerçek ön uçla doğrulanacak — boştaki pin 62 LSB'ye kadar sürüklendi (eşik 82).

##### ✅ Aşama 1 bitti (2026-09-12) — beş görünüm, karttan sunuluyor

Tek kaydırmalı 569 satırlık sayfa **hash yönlendirmeli beş görünüme** bölündü; yapı stok-takip'teki desenle aynı (`#/olcum` … `#/konsol`, geri tuşu çalışır, adres paylaşılabilir). ESP'ye **ek istek yok**: aynı tek `index.html`, görünümler `v-show` ile saklanıyor.

| Ne | Nasıl | Neden böyle |
|---|---|---|
| `GORUNUMLER` listesi (app.js) | id · ad · alt açıklama; sekme şeridi `v-for` ile bundan üretiliyor | Elle kopya olsaydı sekme ↔ görünüm ayrışırdı |
| `hashtenGorunum()` | `#/skop`, `#skop` → `skop`; bilinmeyen/boş → `olcum` | Bozuk adres boş sayfa **açmasın** |
| `v-show`, `v-if` **değil** | beş `<main class="gorunum">` | `v-if` tuvali yok eder; skop'a dönünce yakalama kaybolurdu |
| `watch.gorunum` → `$nextTick` → `grafikCiz()+osiloCiz()` | görünüme dönünce yeniden çizim | `display:none` tuval **0 genişlik** okur; çizilmezse 300 px varsayılanda sola yapışık kalır — headless'ta `nodemo-olcum,skop.png` ile **ispatlandı** (skop gizliyken açıldı, tam genişlik + ortalı "yakalama yok") |
| Tek `.bildirimler` sarmalı | üst şeritteki dört koşullu blok | `:empty` ise yer kaplamaz |
| Konsol | `<details>` katlaması gitti, kendi sekmesi | "kartla ham konuşma" artık gizli değil |

**Ayrışınca ortaya çıkan iki yerleşim kusuru** (tek sayfada fark edilmiyordu):

* *"Sıra önemli — önce girişi 0 V'a bağla…"* ve *"Kalibrasyon değeri negatif de olabilir"* paragrafları **pil bölümünün altında** duruyordu; sekmeler ayrılınca "Pil testi" ekranında kalibrasyon talimatı belirdi. Kalibrasyon kartına taşındı; test artık yerini civiliyor.
* Köprü olayı (`kopru` SSE) aynı bilgiyi **hem** `.hata` **hem** `.uyari` kutusunda basıyordu — iki bildirim, tek olgu. Bağlantılı olan kaldı (kullanıcının "çok bildirim" şikâyetinin ilk somut kalemi).

**Doğrulama:** `test_arayuz3.js` 142 → **156** (bölüm 10: liste↔HTML birebir, v-show, hash çözümü 4 durum, `watch.gorunum` davranışı sahte `this` ile, bildirim sarmalı, paragraf yeri). `mutasyon.py` B7 **6/6** — v-if'e çevirme, skop çizimini düşürme, hash doğrulamasını kaldırma, `hashchange` dinleyicisini silme: hepsi yakalanıyor. Headless Edge: 5 görünüm dev sunucudan (demo) + 5 görünüm **gerçek karttan** (kartın ev ağı adresinden, LittleFS `_fs.bin` 98.3 KB, %10.7) render edildi; geçiş testi iframe'de yalnızca hash değiştirerek (yeniden yükleme yok) yapıldı.

**Aşama 2'ye devredilen gözlemler:** üst şeritte taşıyıcı seçici + adres kutusu dar alanda alt satıra sarıyor (tasarım işi); demo kipinde seçici boş görünüyor (`demo` seçeneği menüde yok); ~~sayfa karttan geldiğinde "Karta bağlan"a basmak gerekiyor~~ (A2-a'da yapıldı).

##### ✅ Aşama 2-a (2026-09-12) — kullanıcının ekran görüntüsünden çıkan dört kusur + rapor aralığı

Kullanıcı canlı paneli gösterip üç şey sordu: *görünüm nasıl · "463 /sn" yazıyor ama ekran o hızda değil · grafik hangi hıza göre?* Cevap ararken **dört kusur** çıktı, ikisi yalnızca gerçek kartta görülebilirdi.

| # | Kusur | Nasıl bulundu | Düzeltme |
|---|---|---|---|
| **G1** | Kartlar "veri yok" derken **grafik sahte 1.72 V'u düz çizgi** çiziyor, "tepe 1.72 V" yazıyordu — K1'in grafik yarısı eksikti | ekran görüntüsü | geçersiz kanal `NaN` → çizgi kopar, etiket "veri yok", CSV'de hücre boş |
| **G2** | "463 /sn" tek sayı: ADC hızı ile ekran hızı karışıyordu | kullanıcının sorusu | iki ölçülen sayı: **"480 örnek/s"** + **"5 güncelleme/s"** (`1000/ölçülen aralık`) |
| **G3** | Sayfa açılınca gönderilen `?` **her seferinde 403** alıyordu: `ac()` EventSource'u kurup hemen dönüyor, jeton `kimlik` olayıyla sonra geliyordu. K5 eşitlemesi WiFi yolunda **hiç çalışmamıştı**, her açılış bir hata bildirimiyle başlıyordu | **CDP ile kartta** (`tarayici.py`) | `ac()` `kimlik`i (ya da hata / 3 s tavan) bekliyor; `?` jetonla gidiyor |
| **G4** | `?` için parola sorulması: izleyici daha ilk saniyede parola penceresiyle karşılanıyordu | CDP | `?` (salt okunur ayar dökümü) `p0` gibi **serbest**; `N` (parolaları basar) serbest **değil** — kartta 204/403 doğrulandı |

**Rapor aralığı kullanıcı seçimine açıldı** (`r<ms>`, 20..5000, sınır dışı **kırpılır ve kırpılmış değer basılır**; NVS'e yazılmaz — görüntüleme tercihi, tarayıcı localStorage'da tutup bağlanınca uydurur; şönt'ün tersi yön: orada kart haklı, burada tarayıcı). Menü: 20 · 10 · 5 · 2 · 1 /s. `A` satırına `rapor=` eklendi. Demo kartı aynı kırpma ile aynı davranıyor.

**Kartta ölçülen maliyet** (tek ADS, 465 örnek/s taban):

| aralık | seri, istemcisiz | WiFi'de 1 SSE istemcisi | en uzun döngü |
|---|---|---|---|
| 200 ms | 483 örnek/s | 444 örnek/s | 2.8 / 18 ms |
| 50 ms | 478 | 460 | 3.2 / 5.0 ms |
| 20 ms | 469 | **425** (−%9) | 2.9 / 5.3 ms |

"Yorar" somutlaştı: her satır istemci başına bir TCP yazma ve bu yazma ölçüm döngüsünün **içinde**; 20 ms'de tek istemci ~%9 örnek götürüyor. Osiloskop farklı: tek yakalama, tek blok, sonra sessiz — sürekli akış değil. SSE olayı artık istemci başına **tek `write()`** (önce dört `print()`); bunun tek başına etkisi ölçülmedi (eski firmware'e dönülmedi).

**Otomatik bağlanma:** sayfa kart/köprüden geldiyse (`localhost`/`file://`/`?demo` değilse) `kopruyuAlgila()` sonrası kendiliğinden bağlanıyor. Yan ürün: headless doğrulama artık **canlı veriyle** yapılabiliyor.

**Yeni araç — `uretim/tarayici.py`:** headless Edge'i CDP ile süren, yalnızca stdlib (asgari WebSocket istemcisi). `--screenshot`'un yapamadığı üç şey: JS değerlendirme, Basic Auth isteğini iptal etme (askıda kalınca sayfa "bağlı ama veri yok" görünüyordu — **ölçüm aracı bozuktu, sayfa değil**), sayfada etkileşim. G3 ve G4 onunla bulundu.

**Doğrulama:** `test_arayuz3.js` 156 → **197** (bölüm 11: NaN/çizim sahte tuval bağlamıyla, iki hız, `A rapor=`/`* rapor araligi` akışı, watch, firmware sınırları, demo kartı; bölüm 12: **asenkron** — sahte EventSource ile `ac()` kimlik gelmeden çözülmüyor, `?` jetonla gidiyor). Bölüm 12 için yakalanmayan asenkron hata artık açıkça kırmızı (`unhandledRejection` → exit 1) — ilk yazımda sessizce 0 ile çıkıyordu. `mutasyon.py` B7 **17/17**, B22b **8/8**. `tezgah_kart.py`: `d_rapor_araligi` (yanıt + **davranış** + kırpma + geri alma; kartta 10.0/s ölçüldü), `d_web_soru_serbest`; öz-test 46/46 ("yanıt var, davranış yok" senaryosu yakalanıyor). `sim3_web.py` 82/82.

**Bu aşamada yakalanan kendi hatalarım:** `belge-uret.py` ve `yetenek_tablosu.py` de `rapor_ms = <sayı>` arıyordu — zincir B9'da **çöktü** (`--sayim-kilidi-yaz` yine de taban yazdı — çökmüş adımın yarım sayısı kilide girdi; `sayim_kilidi()` artık **kırık koşuda yazmayı reddediyor**, doğrudan çağrıyla doğrulandı: dosya değişmedi); `ino_sayi`/`ino_sabit` artık `#define`'a bir seviye iniyor. `govdeIcinde()` C fonksiyonlarında ilk girintili *çağrıyı* tanım sanıyordu (iki iddia yanlış kırmızı) → `cGovde()`; NaN kopma testinde `lineTo −1` beklemiştim, doğrusu −2 (kopan nokta iki lineTo götürür); `tezgah_kart.py` `rapor_ms` sayısını `=` ile arıyordu, `#define`'a taşınınca import anında patlayacaktı; CDP betiğinde `select[title]` taşıyıcı seçicisini yakaladı (yanlış seçici, sayfa kusuru değil).

**Aşama 2'ye kalan:** kart yeniden başlarken sayfa açılırsa `app.js` gelmeyip ham `{{ }}` kalıyor — yeniden yükleme ipucu/`v-cloak` dışı bir hata durumu gerek (Aşama 4 dayanıklılık kalemi). `K` sayaçları sayfa her yüklendiğinde 200+ ms sıçrıyor: 100 KB gzip'i LittleFS'ten loop() içinde sunmak — çift çekirdek kalemi, yeni değil.

##### ✅ Aşama 2-b (2026-09-12) — tasarım sistemi

Kullanıcı A2-a'yı onaylayıp "sıkıntı yoksa sonraki aşamaya geç" dedi. Önce onun gözlemi kapatıldı (**akım hep µA'larda**), sonra tasarım sistemi.

**Akım sorusu — kusur değil, eksik bilgi.** Kartta ölçüldü: 0.1 Ω şöntte ham gürültü tam **1 LSB** (78 µA), 200 ms penceresinde 96 örneğin ortalaması ort **10.7 µA** ± 7.9 µA — yani ekrandaki "7 µA" gerçek bir akım değil, **çözünürlük tabanı**. Şönt ADS'in diferansiyel girişine doğrudan bağlı (kademe sabit ±0.256 V), menzili şönt belirliyor: 10 Ω → LSB 0.78 µA, 0.1 Ω → **78 µA**. Gerilim kartı menzilini ve adımını yazıyordu, **akım kartı yazmıyordu** — eklendi (`±2.56 A · 78.1 µA`), kaynağı kartın `sont=` değeri (menü yalnızca yedek).

**Tasarım sistemi:** `ek.css` `style.css`'e katıldı → **tek stil dosyası** (karttan her ek istek `loop()`'u blokluyor). Koyu tema **varsayılan**, açık tema sistem tercihine uyuyor; bütün belirteçler `:root`ta, açık blok yalnızca **değerleri** değiştiriyor. Renk yalnızca ölçülen büyüklükte (kanal renkleri = tuvaldeki çizgi renkleri, `renk('--volt')` aynı kaynaktan) ve tek vurguda (camgöbeği). Sayılar mono + `tabular-nums`; ölçüm kartlarının üstünde 2 px kanal rengi şeridi. Hareket ölçülü: tek sonsuz animasyon bağlı noktasının nabzı, `prefers-reduced-motion` hepsini kapatıyor. Üst şeritteki dört ayrı öğe tek `.baglanti` öbeği oldu (dar ekranda dağılıyordu); taşıyıcı menüsüne **`demo` seçeneği** eklendi — `?demo`'da seçici **boş** görünüyordu.

**Headless render iki canlı kusur buldu** (ikisi de yalnızca tarayıcıda görünür):

| | Kusur | Sebep | Düzeltme |
|---|---|---|---|
| **R1** | `sahte-kart.js` **iki kez** iniyor → `Identifier 'SahteKart' has already been declared` → sayfanın o andan sonraki betikleri düşüyor | `?demo` açılışında `demoVeri()` hem `mounted()`'tan hem yeni `watch`'tan çağrılıyor, ikisi de betiği beklerken geçiyordu | `betikYukle` aynı `src`'yi ikinci kez eklemiyor + `demoKurulu` kapısı `await`ten **önce** kapanıyor |
| **R2** | Demo akışı ilk 300 noktadan sonra **susuyor**, rozet "bağlı değil" | `demoVeri()` önce `tasiyiciAdi`'yi 'demo' yapıp sonra `bagli`'yi açıyor; `watch` ondan sonra koşup **az önce açılan** bağlantıyı "eski taşıyıcı" sanıp kapatıyordu | bağlı taşıyıcı artık açıkça tutuluyor (`bagliTasiyici`), watch yalnızca **onu** kapatıyor |

**Doğrulama:** `test_arayuz3.js` 203 → **225**; bölüm 13 tasarım sistemini sınıyor (her renk belirteci **iki temada da** tanımlı, kanal renkleri üçü de farklı ve vurgudan ayrı, `app.js`'in tuvalde okuduğu her belirteç CSS'te var, reduced-motion karşılığı, sonsuz animasyon ≤ 1, tek stil dosyası, her taşıyıcının menüde seçeneği). Mutasyon B7 **26/26** (yeni 7'si: akım rengini gerilime eşitle, açık temadan belirteç sil, reduced-motion bloğunu boz, demo seçeneğini kaldır, `destekli()`'yi geri al, `demoKurulu` kapısını aç, taşıyıcı sahipliğini eski hâle döndür). Headless: 5 görünüm × 2 tema yerel + karttan `#/olcum` (0 konsol hatası, ham `{{ }}` yok, nabız animasyonu etkin). LittleFS 102.9 KB, %11.2.

**Bu aşamada yakalanan kendi hatalarım:**

* Bölüm 13'ün iki asenkron iddiası **özet satırından sonra** koşuyordu: sayılmıyor, kırmızı olsa bile süreç 0 ile çıkıyordu — iddia değil süsleme. Asenkron iddialar artık `SONRA` kuyruğunda, özetten önce bekleniyor.
* Sahte 2B bağlam `measureText()` için `undefined` dönüyordu; gerçek tarayıcı her zaman `TextMetrics` döner. Taklit düzeltildi (B17 dersi: taklit **gerçeği** modellemeli, kodu savunmacı yazmak yerine).
* Yerel `secenekler` değişkeni Vue'nun `secenekler`ini gölgeleyip asenkron bölümü çökertti — `unhandledRejection` kancası sayesinde sessiz kalmadı.
* `tarayici.py`'nin `bekle()`'si soket zaman aşımını 0.25 s'ye çekip `al()` çağırıyordu; zaman aşımı **çerçeve ortasında** düşünce okunan 2 başlık baytı kayboluyor ve CDP akışı bozuluyordu (açık tema render'ı böyle düştü) → `select` ile önce veri var mı bakılıyor. Ayrıca `Fetch.enable` uzun oturumlarda `captureScreenshot`'ı asıyor: parolasız sunucuda `auth_iptal=False`, her tema **kendi tarayıcı örneğinde**.

**Aşama 3'e kalan:** telefon kırılımı (şu an yalnızca 560 px altı için asgari kural var), `ayar` görünümünde alan genişlikleri düzensiz, grafik tepe etiketleri şeritli ama hâlâ çizgiye yakın.

##### ✅ Aşama 3 bitti (2026-09-12) — PC ↔ telefon

Kullanıcı telefondan karta bağlanamıyordu; sebep **kartta değil adreste**: `olcum.local` bir mDNS adı, Windows ve iPhone çözüyor, **Android çözmüyor** (Chrome `.local`'i arama sorgusuna çeviriyor). IP ile (`http://<kart-ip>`) her şey parolasız açılıyor — 200, 9.6 KB, 115 ms. Bu tuzak artık **Ayarlar → Bağlantı** kartında yazılı ve testle korunuyor; kullanıcı telefondan bağlandığını doğruladı.

| Ne | Neden |
|---|---|
| **Acil durdurma şeridi** — pil testi çalışırken **her görünümde**, gezinmenin üstünde, tek düğme (`p0`) | Telefonda deşarj sürerken önce doğru sekmeyi bulmak zorunda kalmak emniyet kusurudur. Şerit görünümlerin **dışında** (yoksa yalnızca açık sekmede görünür) ve düğmede `:disabled` **yok** — `p0` zaten jetonsuz geçen tek komut |
| **Üst şerit sadeleşti**: yalnızca durum rozeti + birincil eylem | Taşıyıcı seçici ve kart adresi oturumda bir kez dokunulan şeyler; Ayarlar'ın yeni **Bağlantı** kartına taşındı. Telefonda üst şerit 89 px'e indi |
| **Telefon yerleşimi** (≤620 px): gerilim + akım yan yana, güç tam genişlik, ikincil kutular iki sütun, alt başlık gizli | Tek sütunda güç kartı ilk ekrandan düşüyordu. Gerçek 390 px'te **üç ölçüm de ilk ekranda** |
| ≤380 px'te tek sütuna dönüş | 26 px'lik mono sayı iki sütunda kutuya sığmıyor |

**Ölçüm aracının kendi kusuru:** `--window-size=390,844` Windows'ta işe yaramıyor — pencere ~500 px'in altına inmiyor, yani "390 px testi" aslında 496 px'te koşuyordu ve **telefon kırılımı hiç sınanmamıştı**. `tarayici.py`'ye `ekran()` eklendi (CDP `Emulation.setDeviceMetricsOverride`); gerçek 390/360 px'te doğrulandı. Acil şeridi görmek için `/pil` ucunu taklit eden tek kullanımlık bir sunucu yazıldı (demo sahte kartı pil testini modellemiyor).

**Doğrulama:** `test_arayuz3.js` 225 → **239** (bölüm 14: şerit görünümlerin dışında mı, yalnızca `CALISIYOR`'da mı, `p0` gönderiyor mu, `:disabled` **yok** mu, telefon ızgarası, çok dar ekran, üst şeritte seçici kalmamış mı, Ayarlar'da var mı, Android `.local` uyarısı yazılı mı). Mutasyon B7 **30/30**. Headless: 390 · 360 · 768 · 1280 px'te yatay taşma yok; **gerçek kartta 390 px** — üç ölçüm ilk ekranda, 0 konsol hatası. LittleFS 104.1 KB (%11.3).

**Kendi hatam:** "sonsuz animasyon en fazla bir yerde" iddiası ikinci **meşru** gösterge (acil nokta) gelince yanlış yere kırmızı döndü. Doğru ölçüt sayı değil **hangi seçici**: nabız yalnızca `.rozet.acik .nokta` ve `.acil-nokta`'da, ölçüm sayılarında animasyon yasak.

---

#### 5.12.17 Sırada ne var

| Adım | İş | Not |
|---|---|---|
| B10 | **Donanımı kur** | Parçalar geldiğinde; kılavuz hazır |
| ~~B11~~ | ✅ **±12 V rayı (E0)** | **BİTTİ (2026-09-09).** 7912 orta nokta regülatörü; şemada BLOK 9. Sonuçlar **5.12.25**'te. Stoktan çıktı, yalnızca 50 mA sigorta alınacak |
| B12 | İkili aktarım + USB CDC | **Donanım çalıştıktan SONRA** — Serial'i değiştiriyor |
| B13 | Sürekli hızlı yol | Skop/ADC paylaşımı çözülmeli |
| ~~B15~~ | ✅ **Arıza ve zorlama simülasyonu** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.24**'te: 111 doğrulama, 27 senaryo, DEVİR'in 4 sayısı düzeltildi, şemada 3 kusur kapatıldı |
| ~~B17~~ | ✅ **ADS eş zamanlılığı + süzgeç düzeltmesi** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.29**'da: 26 doğrulama + AVR 70→87. Tek atış kipi, kesirli gecikme, ölçek düzeltmesi, faz kalibrasyonu |
| ~~B20~~ | ✅ **Örnekleme hızı + bant sınırı + menzil** | **BİTTİ (2026-09-10).** Sonuçlar **5.12.30**'da: 41 doğrulama, firmware'de 7 düzeltme. 91 → 671 SPS, `f` sınırı 400 → 100 Hz, AC menzil chatter'ı, SSE blokajı, imza, skop adımı |
| ~~B21~~ | ✅ **Pil kapasite testi** | **BİTTİ (2026-09-10).** Sonuçlar **5.12.31**'de: 32 doğrulama, şemada BLOK 10, `pil_test.h`, arayüzde panel. mAh + kesme + eğri + DCIR. Failsafe kapı, ≤38.5 V sınırı |
| ~~B19~~ | ✅ **Osiloskop kanalı çift yönlü** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.28**'de: 24 doğrulama, R23 2.7K + alt uç VREF, −63.5…+46.8 V. Firmware ve arayüz de güncellendi |
| ~~B18~~ | ✅ **GPIO kelepçeleri / +3V3 geri beslemesi** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.27**'de: 46 doğrulama, F6 reddedildi, R26/R33 10K + yeni R41. B1 payı 18 → 1930 mV, TL431'den bağımsız |
| ~~B16~~ | ✅ **V/I süzgeç eşleştirmesi** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.26**'da: 41 doğrulama, C4 100nF→1nF, yeni C18/C19/C20 = 1.32 µF (stoktan). Reaktif yükte hata %155 → %1.9. 5 açık iş kalemi bıraktı |
| **B17** | 🔬 **Firmware: faz kalibrasyonu + PGA oturması + ölçek düzeltmesi** | **YENİ, B16'dan çıktı.** 5.12.26'nın 1–3 numaralı kalemleri. Faz kalibrasyonu **referans cihaz istemiyor** — dirençli yük yeter. Tolerans artığının tek çözümü bu |
| **B14** | **Hızlı skop (MHz) — harici ADC** | 🔭 **Aşama 4, açık ihtimal.** Kullanıcı ilgileniyor, şimdilik almadı. Tam analiz + kademeli plan **5.12.20**'de. Adım 1 bedava: hazır açık kaynak kodu elde bir ESP32'de dene |

🔴 **Değişmeyen uyarı:** kart izole değil.


---

## 6. Fiziksel sınırlar — abartma

Yeni oturumun kullanıcıya yanlış vaat vermemesi için kanıtlanmış tavanlar tek yerde:

| Sınır | Değer | Kaynak |
|---|---|---|
| ADS1115 örnekleme | **860 SPS**, aşılamaz | veri sayfası SBAS444 |
| ADS1115 **bant genişliği** | **−3 dB @ 380 Hz** (sinc/boxcar) | 860 SPS'te 1.16 ms ortalama |
| ESP32 ADC | **83 333 Sa/s TOPLAM, 12 bit** | `SOC_ADC_SAMPLE_FREQ_THRES_HIGH` |
| Gerçek zamanlı Nyquist | tek kanal 41.7 kHz, **iki kanal 20.83 kHz** | toplam hız kanallara bölünür |
| V–I kanal kayması | **12.000 µs sabit** — eşzamanlı örnekleme imkânsız | tek SAR, sıralı pattern |
| ETS eşdeğer hız | 80 MSa/s | koherent örnekleme |
| **ETS analog bant** | 🧱 **bilinmiyor** — ölçülene kadar <500 kHz varsay | Espressif S/H açıklık süresini yayınlamıyor |
| ETS geçerliliği | **yalnız tekrarlayan sinyal**; tek seferlik olayı asla yakalamaz | yöntemin doğası |
| Gerilim tam ölçek — Aşama 2 | **32.2 V** (45 V değil) | ADS girişi VDD ile sınırlı |
| Gerilim tam ölçek — Aşama 3 | **±31.1 V / ±615.4 V** | 5.12, tasarlandı ve doğrulandı, kurulmadı |
| Giriş empedansı — Aşama 2 | **106.8 kΩ** (DMM'de 10 MΩ) | 100K+6.8K |
| Giriş empedansı — Aşama 3 | **0.21 MΩ / 4.93 MΩ** | 5.12 |
| Wattmetre güvenilir bandı | **~5 kHz** | Sallen-Key + Lagrange birlikte (5.12.7) |
| Direnç azami çalışma gerilimi | **200 V** (1/4W metal film) | Yageo MFR — 250 V varsayımı yanlıştı |
| İzolasyon | **yok** — şebeke bağlanamaz | tasarım |
| Burden gerilimi | tam ölçekte 256 mV, her akım kademesinde | PGA ±0.256 V |

⚠️ **Giriş empedansının anlamı:** 1 kΩ kaynak empedanslı bir düğümde %0.93, 10 kΩ'da
%8.6 hata. **Bu bir voltmetre değil, bir güç ölçer.** Besleme rayları ve yük uçları gibi
düşük empedanslı düğümlerde doğru; yüksek empedanslı düğümlerde multimetre kullanılmalı.

### 6.1 🔴 SMPS güvenliği — dipnot değil

> **İzole olmayan bir SMPS'in birincil tarafına bu kartla DOKUNMA.**
>
> Skop girişi kart toprağına referanslı. Şebekeden beslenen bir SMPS'in birincil
> "toprağı" **şebeke potansiyelindedir**. Kartın toprağını oraya bağlarsan **USB kablosu
> üzerinden bilgisayarına şebeke gerilimi taşırsın.**
>
> Yalnız **izole ikincil taraf**, ya da tamamen izole çalışma (pil + WiFi, USB takılı
> değil).
>
> 🔴 **AMA YÜZDÜRMEK TEK BAŞINA YETMEZ — B15/D2 bunu ölçtü.** Pille
> yüzdürmek **bilgisayarı kurtarır, KULLANICIYI kurtarmaz**: kart o anda
> şebeke potansiyeline çıkar ve **kartın her noktası** tehlikeli olur.
> 615 V, yüzen alet sınırının **14.6 katı**. Şebeke referanslı ölçümde
> **yalıtımlı kutu ŞART** (hiçbir noktaya el erişimi yok), delikli
> plakette takviyeli yalıtım için **5 delik atlanacak** (12.7 mm,
> IEC 60664 creepage 12.6 mm) ve enerji varken karta dokunulmayacak.
> Ayrıntı **5.12.40**'ta; kullanıcı tarafı `BELGELER/4-kurulum.html`'in
> ilk uyarısında.

Aşama 2 yol haritasındaki *"ESP-01 WiFi izolasyonu — 400 V ölçümüyle birlikte zorunlu"*
notu bunun aynısıydı. **Hızlı skop kanalı gelince bu not isteğe bağlı olmaktan çıkıp
zorunlu hale geliyor**, çünkü kullanıcının asıl bakmak isteyeceği yer tam olarak orası.

---

## 7. Yeni oturum için görevler

### 7.1 Araştır (kullanıcının açık isteği)

Bu oturumda başlanan araştırmanın devamı. **Şu üç bulguyu doğrula ve derinleştir:**

**① WiFi ile sürekli ADC çakışıyor.**
`esp_wifi_start()`, `adc_continuous_start()`'tan sonra çağrılırsa DMA tamponu dolmayı
bırakıyor; ADC çevre birimi çalıştığını sanıyor.
*Kaynak: [espressif/esp-idf#12749 (IDFGH-11635)](https://github.com/espressif/esp-idf/issues/12749)*

Mevcut firmware'de sıra **tesadüfen güvenli**: `skop_kur()` yalnız `adc_continuous_new_handle`
ve `adc_continuous_config` çağırıyor (yapılandırma), `adc_continuous_start()` ise komutla
çalışan `skop_yakala()` içinde — yani WiFi'den sonra. **Ama yeni mimaride ADC sürekli
koşacak.** O zaman WiFi her açılıp kapandığında ADC durdurulup yeniden başlatılmalı.
Bu, "kalibrasyon USB ile yapılır, WiFi uzaktan izleme içindir" kuralını güçlendiriyor.

**② ADC2 DMA S3'te desteklenmiyor** (errata; kararsız sonuç gözlenmiş). Tasarım zaten
ADC1'de (GPIO1–10); bu kısıt korunmalı.

**③ Çok kanallı sürekli kipte interleave deseni** ~270 kSa/s toplam üstünde bozuluyormuş
(tekrar eden ve atlanan örnekler). Biz 83 kSa/s'teyiz, güvenli — ama iki kanal
kullanınca desenin gerçekten beklendiği gibi çıktığını **ölçerek** doğrula.

*Ayrıca ADC1'de 11 dB zayıflatmayla sürekli kipte "çınlama/gürültü" bildiren kullanıcılar
var — [ESP32 Forum](https://esp32.com/viewtopic.php?t=26367).*

**Araştırılacak diğer başlıklar:**
- ESP32-S3 ADC doğrusalsızlığı ve eğri kalibrasyonu — tek kazanç+ofset yetmiyorsa ne yapılır
- Eşdeğer-zaman örnekleme uygulamaları: gerçek projelerde elde edilen etkin bant genişliği
- Elektronik yük kararlılığı: lineer MOSFET çevriminin kompanzasyonu, tipik salınım sebepleri
- Kelvin şönt yerleşimi: delikli plakette 4 telli bağlantı nasıl doğru yapılır
- Delikli plakette yıldız toprak ve yüksek akım izleri
- LEDC PWM'i DAC olarak kullanma: RC süzgeç tasarımı, oturma süresi, artık dalgalanma

### 7.2 Hata bul

- Bölüm 4'teki maddeleri **doğrula** — gerçekten var mı? (Biri zaten yanlış alarm çıktı;
  başkaları da olabilir.)
- Bölüm 5'teki mimari varsayımları sorgula. Özellikle **5.2'deki süzgeç çelişkisi** ve
  **5.5'teki verim hata bütçesi** — bunlar en kırılgan noktalar.
- Bu belgedeki her sayının kaynağına git.

### 7.3 Geliştir

Kullanıcı "bunların dışında yapabileceğimiz işime yarayabilecek neler var?" diye sordu.
Bu oturumda dört öneri sunuldu ve **dördü de seçildi**. Yeni oturum kendi önerilerini
eklesin — kullanıcının profili: **yazılım mühendisi, elektronikle hobi olarak ilgileniyor,
envanteri SMPS/güç elektroniği ağırlıklı** (SG3525, TL494, UC3843, IR2110, güç
MOSFET'leri, yüksek gerilim film kondansatörler). İnverter veya anahtarlamalı güç kaynağı
projeleri muhtemel.

Değerlendirilmemiş bir fikir: **ESR ölçer**. TV sökümü parçalar ve SMPS onarımı için çok
uygun; NE555 ×10 yolda ve uyarma sinyali için kullanılabilir. Bu oturumda seçenek olarak
sunulmadı (4 seçenek sınırı), kullanıcıya sorulabilir.

---

## 8. Açık sorular — kullanıcıya sor

1. ✅ **±12 V — TAMAMEN ÇÖZÜLDÜ (2026-09-09), bkz. 5.12.23.** Kullanıcıda 12 V
   adaptör YOK; **24 V güç kaynağı**, bir düşürücü regülatör modülü ve **2 adet**
   18650 var. Karar: **24 V + LM358 orta nokta tamponu ile ±12 V** — ek alım sıfır,
   hepsi elde (LM358 stokta 8). Kart 3 pinli besleme girişi taşıyacak
   (+12 / GND / −12), böylece ileride 4 hücre daha alınıp 6× 18650 paketine
   geçilirse **kartta değişiklik gerekmez**. O gün kart yüzer hale gelir ve
   Wi-Fi ile birlikte projenin en büyük tehlikesi (izole olmaması) kapanır.
   ⚠️ **Kurmadan önce ölç:** 24 V kaynağın negatif ucu ile şebeke toprağı arasına
   ohmmetre — toprağa bağlıysa bu şemada −12 V rayı toprağa kısa devre olur.
2. ⚠️ **Soğutucunun ölçüsü/termal direnci ne?** Kullanıcı 2026-09-08'de "soğutucu var"
   dedi ve `MEK002` olarak kaydedildi, **ama spesifikasyonu bilinmiyor.** Elektronik
   yükte **2 °C/W eşiği 2.4 W ile 30 W arasındaki farkı belirliyor** — kabaca
   100×60×30 mm kanatlı profil ya da 60×60 mm + 40 mm fan. Ölçüyü öğrenip CSV'yi
   güncelle.
3. **Bölüm 5.8'deki satın alma listesi onaylanıyor mu?** (~40 TL: LM319N ×2, NTC ×2,
   KSD9700, metal film direnç seti, 1N4148 ×20)
4. **Laboratuvar kalibrasyonu ne zaman, hangi cihazla?** Mutlak ölçümlerin (voltmetre,
   ampermetre) tavanını bu belirliyor. *Oransal ölçümler (verim) için kritik değil —
   bkz. 1.3 ve 5.7.*
5. **Ön panelde kaç uç çifti olacak?** Bugün 5 (V, µA/mA, A, 10A, SCOPE). Yeni yetenekler
   uç istiyor: eğri çizici (DUT soketi + 4 Kelvin ucu), elektronik yük (2), verim ölçer
   (+4), SMPS zamanlama (3 prob). Muz jak 5 renk × 2 sipariş edildi — yeniden bölüşüm
   gerekebilir; DUT için ZIF veya kaliteli TO-220 soketi düşünülmeli.
6. **Geliştirme kartında hangi GPIO'lar başlığa çıkmış?** Pin planı çakışmasının
   (bkz. 5.9) çözümü buna bağlı. Kartın fotoğrafı veya pin listesi lazım.
7. **ESR ölçer ilgisini çeker mi?** (Bu turda seçenek olarak sunulmadı, 4 seçenek sınırı
   vardı. TV sökümü parçalar ve SMPS onarımı için çok uygun; NE555 ×10 yolda.)

---

## 9. Dosya haritası ve komutlar

> ⚠️ **Adım başına doğrulama sayıları burada TUTULMUYOR.** Bir kuşak boyunca
> tutuldular ve bayatladılar (B17 26→31, B3 128→150, B15 109→111). Tek kaynak
> **`uretim/beklenen_sayim.json`** ve zincir her koşuda birebir karşılaştırıyor.

### Komutlar

```bash
cd projeler/olcum-karti/uretim
python dogrula3.py            # AŞAMA 3 — GÜNCEL, 17 adım, ~6 dk
python dogrula2.py            # Aşama 2 (arşiv), A1–A6, ~70 s
python dogrula.py             # Aşama 1 (arşiv), S1–S9, ~110 s
python dogrula.py --hizli     # Aşama 1 hızlı (S1–S7), ~20 s

python mutasyon.py            # iddialar gerçekten ısırıyor mu — ~15 s
python mutasyon.py --liste    # ne koşacağını yazar, koşmaz

python belge-uret.py          # BELGELER/ yeniden üret (7 sayfa)
python arayuz-uret.py         # arayüzü LittleFS görüntüsüne paketle
python arayuz-yaz.py          # görüntüyü karta yaz (esptool, 0x310000)

cd projeler/olcum-karti
python arayuz3/sunucu.py      # arayüzü PC'den sun (Web Serial)
Kopru Baslat.bat              # PC köprüsü (telefondan bağlanmak için)
```

### Üretim betikleri — Aşama 3 (güncel)

| Betik | Adım | Görevi |
|---|---|---|
| `dogrula3.py` | — | Zincir koşturucu + tezgah toplayıcı + sayım kilidi |
| `tasarim3.py` + `tasarim3_sabit.py` | **B1** | Aşama 3 tasarımı; **tüm mutlak sınırlar `tasarim3_sabit.py`'de, kaynaklarıyla** |
| `sim3_giris.py` | **B2** | Çift yönlü ön uç, ngspice |
| `sim3_ariza.py` | **B15** | Arıza ve zorlama — 27 senaryo. Kabul ölçütü: hiçbir TEK arıza ESP32'yi ya da PC'yi öldürmemeli |
| `sim3_besleme.py` | **B11** | ±12 V rayı, 7912 orta nokta regülatörü |
| `sim3_ortusme.py` | **B16** | V/I süzgeç eşleştirmesi + akım kanalı örtüşme süzgeci |
| `sim3_kelepce.py` | **B18** | GPIO kelepçeleri ve +3V3 geri beslemesi |
| `sim3_skop.py` | **B19** | Osiloskop kanalı çift yönlü |
| `sim3_senkron.py` | **B17** | ADS eş zamanlılığı, ölçek düzeltmesi, faz kalibrasyonu |
| `sim3_bant.py` | **B20** | Örnekleme hızı, bant sınırı, menzil + kütüphane taraması |
| `sim3_pil.py` | **B21** | Pil kapasite testi — anahtar, kapı yönü, tampon |
| `test_kopru.py` | **B22a** | PC köprüsü — röle bayt-şeffaflığı, arşiv, sürücü hakemi |
| `sim3_web.py` | **B22b** | Kartın web katmanı — SSE, komut ucu, CSRF, ağ |
| `sema3-uret.py` / `netlist3_dogrula.py` | **B3** | Şema üretimi + netlist polarite denetimi |
| `test_olcum3.py` | **B4/B5** | Ölçüm matematiği, GERÇEK kod AVR emülatöründe |
| `test_firmware3.py` | **B6** | Derleme (gerçek ESP32-S3) + ikilide ölü kod |
| `test_arayuz3.js` | **B7** | Arayüz + arayüz↔firmware komut denetimi |
| `bom_dogrula.py` / `kurulum3-uret.py` | **B9** | Malzeme listesi + tezgah kılavuzu |

### Ortak altyapı (B23'te eklendi)

| Betik | Görevi |
|---|---|
| `tezgah.py` | Tezgah kalemi biçimi; konsolun çizemeyeceği karakteri **yazmadan önce** yakalar |
| `mutasyon.py` | Mutasyon koşucusu — kaynağı bir **kopyada** bozup testin kırmızıya döndüğünü ölçer |
| `sayim.py` | Adım özet satırlarının ortak ayrıştırıcısı (dört ayrı biçim) |
| `gecici.py` | Kendini silen geçici dizin (`atexit`) |
| `belge_menu.py` | `BELGELER/` gezinme şeridi — **tek kaynak**, iki üreteç paylaşır |
| `spice.py` · `hedef2.py` · `kutuphane.py` | ngspice sürücüsü · FQBN · sembol kütüphanesi |

### Üretilen dosyalar (elle düzenlenmez)

| Dosya | Kim üretiyor |
|---|---|
| `uretim/_tezgah.md` | `dogrula3.py` — tezgahta ölçülecekler |
| `uretim/beklenen_sayim.json` | `dogrula3.py` — iddia sayısı kilidi |
| `uretim/_firmware.json` | `test_firmware3.py` — ölçülen flash/RAM |
| `uretim/_fs.json` · `_fs.bin` | `arayuz-uret.py` — LittleFS görüntüsü ve künyesi |
| `BELGELER/*.html` | `belge-uret.py` (+ `4-kurulum.html`: `kurulum3-uret.py`) |
| `uretim/b15-arastirma.md` | `b15_kanit_uret.py` — B15'in ham araştırma kanıtı |

### Arşiv betikleri (Aşama 1 · 2)

| Betik | Görevi |
|---|---|
| `tasarim2.py` | **A1** — tasarım belgesi + test |
| `sim_referans.py` `sim_bolucu.py` `sim_akim.py` | S1–S3 ngspice |
| `sim2_giris.py` | **A2** — 4 kelepçe seçeneğinin taranması |
| `sim_kart.py` / `sim2_kart.py` | S9 / **A4** — uçtan uca |
| `test_firmware.py` | S4 — aritmetik |
| `test_avr.py` | S8 — emülatörün kendisinin doğrulanması |
| `test_skop.py` + `test_skop_arayuz.js` | **A5** — osiloskop protokolü + ölü kod |
| `netlist_dogrula.py` / `netlist2_dogrula.py` | S5 / **A3** — netlist polarite ve adres |
| `sema-uret.py` / `sema2-uret.py` | Şema üreteçleri |
| `gorsel.py` `gorsel_a2.py` `gorsel_s9.py` | SVG grafik üreteçleri |
| `kanit-uret.py` `kanit2-uret.py` `sayfa-uret.py` `kurulum-uret.py` | Arşiv sayfaları |
| `avr/cekirdek.py` `avr/mega328.py` `avr/elf.py` | AVR emülatörü |

### Kaynak dosyalar

| Yol | İçerik |
|---|---|
| `kod/olcum-karti-a3/olcum-karti-a3.ino` | **Güncel firmware** (ESP32-S3) |
| `kod/olcum-karti-a3/olcum3.h` | **Platform bağımsız aritmetik** — AVR emülatöründe de koşar |
| `kod/olcum-karti-a3/pil_test.h` · `ag.h` · `web_akis.h` · `web_satir.h` · `tipler3.h` | Pil testi · ağ · `Serial` aynası · satır tamponu · tipler |
| `arayuz3/app.js` `index.html` `style.css` `ek.css` `sunucu.py` | **Güncel arayüz** — Vue 3, derleme adımı yok |
| `kopru/kopru.py` `kart_baglanti.py` `arsiv.py` | **PC köprüsü** — yalnızca standart kütüphane |
| `sema3/olcum-karti-a3.kicad_sch` | **Güncel şema** (betikle üretiliyor) |
| `arsiv/asama1/` · `arsiv/asama2/` | Eski aşamalar. ⚠ `arsiv/asama2/kurulum2.html` **canlı bağımlılık**: `kurulum3-uret.py` biçimini oradan okuyor |


### Arşiv kaynakları (Aşama 1 · 2)

| Yol | İçerik |
|---|---|
| `arsiv/asama1/olcum-karti/olcum-karti.ino` + `tipler.h` | Aşama 1 firmware (ATmega328P) |
| `arsiv/asama2/olcum-karti-a2/olcum-karti-a2.ino` | Aşama 2 firmware (ESP32-S3) |
| `arsiv/asama2/.../olcum2.h` | Aşama 2'nin platform bağımsız aritmetiği |
| `arsiv/asama1/arayuz/` · `arsiv/asama2/arayuz2/` | Eski arayüzler |
| `arsiv/asama1/sema/` · `arsiv/asama2/sema2/` | Eski KiCad şemaları |
| `arsiv/asama*/kanit/` | Doğrulama kayıtları ve kanıt sayfaları |
| `arsiv/asama2/kurulum2.html` | Aşama 2 kurulum kılavuzu — ⚠ **biçimi hâlâ kullanılıyor**, bkz. yukarıdaki uyarı |

### Firmware arayüzü (Aşama 2)

**Pinler:** SDA=8, SCL=9, SKOP=4, HAZIR=7 · **Adresler:** 0x48 akım, 0x49 gerilim

**Çıktı:**
```
D <volt> <amper> <watt> <joule> <wh> <ms> <örnek>     # "D %.3f %.5f %.5f %.4f %.7f %lu %lu"
S <adet> <Hz> <volt/adım>                              # ardından ham ADC kodları, 16'şar
```

**Komutlar:**

| Komut | İş |
|---|---|
| `?` | ayarları yaz |
| `#` | I2C taraması (0x08..0x77) |
| `t<esik>` | osiloskop yakala, 0 = tetiklemesiz |
| `z` | akım sıfırı — **yük bağlı değilken** |
| `v<gercek>` | gerilim kalibresi |
| `i<gercek>` | akım kalibresi |
| `s<ohm>` | şönt değeri |

Ayarlar NVS'te (`Preferences`, "olcum2" ad alanı), imza `0xC0FE`.

### Araçlar

| Araç | Yol |
|---|---|
| KiCad 10.0.6 | `C:\Program Files\KiCad\10.0\bin\` (kicad-cli + ngspice.dll) |
| arduino-cli 1.5.2 | `.araclar\arduino-cli.exe` (proje kökünün iki üstü) |
| ESP32 core | 3.3.11 · FQBN `esp32:esp32:esp32s3` |
| avr-gcc | Arduino15 paketi, 7.3.0-atmel3.6.1-arduino7 |
| node, numpy | sistemde |

### İlgili

- Envanter: `stok-takip/envanter.csv` — **tek gerçek kaynak**, `CLAUDE.md` kurallarına uy
- Aşama 2 kanıt sayfası: <https://claude.ai/code/artifact/f6a2ab16-0ea1-4dd1-9f35-0dd03859d993>
- Kurulum kılavuzu: <https://claude.ai/code/artifact/23d6637e-f723-4a5e-96ac-22ab6978cac6>
- Aşama 1 kanıt sayfası: <https://claude.ai/code/artifact/7aa77d26-7247-4661-b383-f69f2892e701>
