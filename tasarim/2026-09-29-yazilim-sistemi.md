# Ölçüm kartı — yazılım sistemi tasarımı (kayıt · analiz · PC · Android)

**Tarih:** 2026-09-29 · **Durum:** ✅ kullanıcı onayladı (2026-09-29) — kod yok; sırada alt proje 1 planı
**Kapsam:** kartın yazılım tarafının tamamı. Donanım (kutu, kart A/B) bu belgenin dışında.

Bu belge 2026-09-29 beyin fırtınasında kullanıcıyla bölüm bölüm onaylanan
kararların tek kaynağıdır. Her alt proje kendi ayrıntılı tasarımını ve
uygulama planını ayrıca yazar; o belgeler bu belgeyle çelişemez, çelişki
çıkarsa önce burası güncellenir.

---

## 1. Amaç

Kullanıcının istediği, kendi sözleriyle özetle:

1. Sistem **profesyonel, sade ve anlaşılır** görünsün — web, PC ve Android'de.
2. Ölçümler **kaydedilsin**, sonra **analiz** edilsin, **dışarı aktarılsın**.
   Kayıt yalnız pil testinde değil, voltmetre · ampermetre · wattmetre ·
   osiloskop — her modda.
3. Kayıt **güvenilir** olsun; bağlantı koparsa ya da bellek tehlikeye
   girerse telefona ve PC'ye **bildirim** düşsün — dışarıdayken de,
   **~10 saniyede**.
4. Android deneyimi bugünkünden belirgin şekilde iyi olsun.

### Başarı ölçütleri (ölçülebilir)

| # | Ölçüt | Nasıl ölçülür |
|---|---|---|
| Ö1 | **Hiçbir sıçrama kaybolmaz:** kayıt hızı ne olursa olsun tek örneklik bir olay kayıtta (min/maks) ve her yakınlaştırma düzeyinde grafikte görünür | `ortak/` testi: rastgele veriye gömülü tek-nokta sıçramalar; gerçek kartta bilinen darbe |
| Ö2 | Kayıt sırasında elektrik kesilirse o ana kadarki kayıt bozulmadan kalır; kayıp **en fazla son ~5 s** | Tezgahta kayıt sürerken fiş çekme, en az 20 tekrar |
| Ö3 | Bağlantı dönünce eksik veri **kendiliğinden** gelir; cihazdaki dosya karttakiyle **bayt bayt aynı** | Tezgah: uzun kopukluk + karşılaştırma |
| Ö4 | Dışarıda, "Anlık izleme" açıkken kartın fişi çekilince telefona bildirim **hedef ≤ 10 s, kabul ≤ 15 s** | Tezgah + gerçek telefon, kronometreli, en az 10 tekrar |
| Ö5 | Parola ve cihaz anahtarı ağda **hiçbir zaman** açık gitmez | Eşleştirme + kullanım trafiği kaydında arama |
| Ö6 | ~800 bin noktalık kayıtta orta sınıf telefonda yakınlaştırma/kaydırma akıcı (**hedef: kare başına < 33 ms**) | Android'de ölçüm |
| Ö7 | Mevcut emniyet kuralları bozulmaz: `p0` her zaman serbest; pil testinde osiloskop yakalaması yasak (B41); kart yeniden başlarsa pil testi **asla** kendiliğinden sürmez | Mevcut + yeni iddialar, mutasyonla |

---

## 2. Bugünkü durum (2026-09-29, koddan okundu)

| Konu | Bugün |
|---|---|
| Canlı ölçüm + "CSV indir" | Yalnız açık sekmenin belleğinde; tavan 60 000 nokta (`arayuz3/app.js:1279`). Sekme kapanınca gider |
| Pil testi | Kartta `PilHalka` (PSRAM, 86 400 nokta = 1 Hz'te 24 saat), `/pil?sira=N` ile kaldığı yerden eşitleniyor; tarayıcıda IndexedDB. CSV virgüllü + BOM'suz (Excel-TR'de bozuk) |
| Osiloskop | Geçmiş yakalamalar yalnız PC köprüsü kipinde; dışarı aktarma yok |
| PC köprüsü | Her satırı `kopru/arsiv/<gün>.satir`'a yazıyor; `csv_uret` var ama yalnız test çağırıyor. Son kayıt 12 Eylül |
| Kart belleği | Kalıcı kayıt yok. `huge_app` bölüm şeması 4 MB'a göre → 16 MB flaşın **~12 MB'ı bölümlenmemiş**. PSRAM 8 MB, 1 MB kullanımda |
| Canlı akış | **4 istemci** (`AKIS_AZAMI`, B22.4); B28'den beri soket yazımı yalnız çekirdek 0'da. Köprü kayıtlıyken ikinci istemci reddediliyor |
| Güvenlik | İzleme parolasız. Komut: `Host` beyaz listesi + `X-Olcum` başlığı + açılışta üretilen oturum jetonu + HTTP Basic Auth (`olcum` / NVS `web_sifre`). Parola her komutta **açık** gidiyor, tarayıcı kapanınca yeniden soruluyor |
| Kalibrasyon | Tek küme, NVS `Ayar3`; yeniden kalibrasyon üzerine yazıyor, geçmiş yok |
| Android | Uygulama yok; telefonda aynı web sayfası. `.local` Android'de çözülmüyor, PWA kurulumu HTTPS istiyor |
| Analiz | Yok |

---

## 3. Kararlar özeti

| Karar | Seçilen | Reddedilen ve neden |
|---|---|---|
| Platformlar | Web paneli + PC uygulaması + Android uygulaması | — |
| Android ekranları | **Ayrı, telefona özel** (Ionic Vue + Capacitor), hesap kodu `ortak/`'ta tek kopya | Ortak panel: telefonda "yeterince güzel olmaz" (kullanıcı). Tamamen Kotlin/Compose: hesaplar iki kez yazılır, grafik sıfırdan, ~2× iş |
| PC uygulaması | Köprü `localhost`'tan paneli sunar → kurulabilir PWA (localhost güvenli bağlam) | Ayrı masaüstü programı: gereksiz |
| Asıl kaydı kim tutar | **Kart**; cihazlar sıra numarasıyla eşitlenen kalıcı kopya tutar | Cihazlar kaydeder: kopuklukta veri kaybı. Köprü kaydeder: PC hep açık olmalı |
| Kayıt noktası | Ortalama **+ en düşük + en yüksek** (V, A, W ayrı), **ham ADC kodu** | Yalnız ortalama: 200 ms'lik ortalamada kısa sıçrama VERİDE kaybolur |
| Bellek dolunca | **Akıllı temizlik:** en az bir cihaza kopyalanmış eski kayıt silinir; kopyalanmamış veri asla; yine yer yoksa kayıt durur + bildirim | Hiç silmeme; halka (kopyalanmamışı ezer) |
| Kayıt başlatma | Elle + zamanlanmış | Koşullu/tetikli: "belki ileride" |
| Yeniden başlama | Ölçüm kaydı **devam eder** (işaretli boşluk); pil testi **etmez** | — |
| Grafik motoru | **uPlot** (`vendor/`, ~50 KB) | Kendi tuval kodu: büyük iş; ECharts: ~1 MB, kartın panel alanına sığmaz |
| Çizim özetleme | Piksel sütunu başına min+maks, önceden hesaplı katmanlar; **hesaplar hep ham veriden** | Ortalama/atlamalı özetleme: sıçrama siler |
| Güvenlik | Cihaz eşleştirme + imzalı istekler; her işlem yetkili | Kartta HTTPS: kendi imzalı sertifika uyarısı + yavaşlık |
| Kalibrasyon | Sürümlü geçmiş; her kayıt kendi kalibrasyonunu taşır | Tek küme |
| Uzaktan bildirim | **MQTT + vasiyet (LWT)**, ~10 s; telefonda "Anlık izleme" anahtarı (varsayılan açık) | ntfy kalp atışı: 10 s için günde ~17 000 mesaj, en iyi 15–30 dk |
| Dil | Türkçe + İngilizce, geçişli | — |

---

## 4. Mimari

```
                    ┌──────────── KART (ESP32-S3) ─────────────┐
                    │ ölçer → KAYDEDİCİ → flaş (~10 MB, kalıcı)│
                    │ oturumlar: sıra no + gerçek saat         │
                    │ eşitleme ucu · canlı akış (4) · MQTT     │
                    └──────┬──────────────┬──────────────┬─────┘
             USB ya da WiFi│        WiFi  │     internet │ LWT + olaylar
                           ▼              ▼              ▼
             ┌──────────────────┐  ┌───────────────┐  ┌────────────┐
             │ PC UYGULAMASI    │  │ ANDROID       │◀─│ MQTT aracı │
             │ köprü: eşitler,  │  │ Ionic ekranlar│  │ (bulut,    │
             │ diske yazar,     │  │ + Kotlin:     │  │ ücretsiz   │
             │ paneli localhost │  │ bul · arka    │  │ katman)    │
             │ tan sunar (PWA)  │  │ plan · bildi- │  └────────────┘
             └────────┬─────────┘  │ rim · dosya   │        ▲
                      │            └───────┬───────┘        │ PC de abone
                      ▼                    ▼
             ┌─────────────────────────────────────────┐
             │ ortak/ — TEK KOPYA hesap kodu (düz JS)   │
             └─────────────────────────────────────────┘
```

### Alt projeler ve sıra

Her biri kendi tasarım → onay → plan → uygulama turundan geçer.

| # | Alt proje | Başlıca teslimler | Bağımlılık |
|---|---|---|---|
| 1 | **Kart kaydedici** (firmware) | Yeni bölüm tablosu · oturumlar · flaş günlüğü · eşitleme ucu · kalibrasyon geçmişi · eşleştirme + imza · NTP · MQTT · `MDNS.addService` · köprü kuralının gevşemesi | — |
| 2 | **`ortak/`** | Kayıt okuyucu · eşitleme istemcisi · imzalama · kalibrasyon · özet katmanları · istatistik · osiloskop ölçümleri + FFT · dışa aktarma · rapor içeriği · TR/EN sözlük · grafik çekirdeği | 1'in biçimi |
| 3 | **Web paneli** (PC öncelikli) | Görsel tasarım turu · ekranlar (§9) · `app.js`'in modüllere bölünmesi | 2 |
| 4 | **PC uygulaması** | Köprü: USB **ve** WiFi eşitleme, disk arşivi, PWA, Windows bildirimi, MQTT aboneliği | 2, 3 |
| 5 | **Android uygulaması** | Görsel tasarım turu · Ionic ekranlar · Kotlin eklentileri | 2 |

Görsel tasarım 3 ve 5'in başında ayrı karar turudur: 2–4 aday, kullanıcı seçer.

### Bağlantı durumları

- **Evde:** kart ev WiFi'sinde; cihazlar ağdan bağlanır; MQTT çalışır.
- **Sahada:** ev ağı yoksa kart kendi erişim noktasını açar (bugün var,
  `ag.h`); telefon doğrudan bağlanır. İnternet yok → MQTT yok; telefonun
  yerel tespiti çalışır.

---

## 5. Kayıt modeli ve eşitleme (alt proje 1 + 2)

### Oturumlar

Aynı anda **tek** oturum.

| Tür | İçerik |
|---|---|
| Ölçüm kaydı | V/A/W; her nokta ort + min + maks. Hız: ayrıntılı (her örnek) · 50/s · 10/s · 5/s · 1/s · 10 s'de 1 · dakikada 1 |
| Osiloskop günlüğü | Her tetikte ya da her N saniyede bir yakalama (≤ 4000 örnek, 8 KB). İsteğe bağlı olarak bir ölçüm kaydıyla aynı oturumda; yakalama anı ölçüm kaydında işaretli boşluk |
| Pil testi | Ölçüm kaydı + mAh · Wh · DCIR olayları · kesme olayı. `PilHalka` ve `/pil` bunun yerine geçer; emniyet kuralları aynen |

**Başlık** (oturum açılırken yazılır): kimlik · tür · başlangıç (gerçek
saat + kart ms) · hız · menzil · şönt · firmware sürümü · **kalibrasyonun
tam kopyası + numarası**. Ad, etiket, notlar sonradan eklenir — oturuma
**ek kayıt** olarak, yine kartta (bütün cihazlar aynı görür).

### Kapasite (1A-1'de kesinleşen biçimle)

Nokta 36 bayt · kayıt başlığı 16 bayt · her sektör başında 116 baytlık
TEKRAR · 5 saniyelik boşaltma · sektör başına 24 baytlık BITIR payı.
~11.4 MB'lık kayıt bölümü (2912 sektör; bölüm tablosu 1A-2'de) için:

| Hız | Nokta/sektör | Süre |
|---|---|---|
| 50/s | ~107 | ~1.7 saat |
| 10/s | ~107 | ~8.7 saat |
| 5/s | ~107 | ~17 saat |
| 1/s | ~100 | ~3.4 gün |
| 10 s'de 1 | ~70 | ~24 gün |
| dakikada 1 | ~70 | ~140 gün |

Yavaş hızlarda verim düşük: nokta 5 s içinde tek başına yazılıyor (Ö2'nin
bedeli). Ayrıntılı kip (her örnek) 1C'de tasarlanacak.

### Kartta saklama

- Flaşa **yalnız sona ekleme**; her blokta sağlama kodu (CRC).
  Yarım blok açılışta tanınır ve atılır; öncesi sağlam.
- RAM/PSRAM'de birikir, en geç **~5 s**'de bir flaşa yazılır (Ö2).
- Aktif oturum ve zamanlanmış kayıtlar flaşta işaretli → yeniden başlamada
  ölçüm kaydı sürer (işaretli boşluk), pil testi sürmez (yük kapalı kalır).
- Mevcut `Ayar3` kalibrasyonu ilk açılışta geçmişin **1 numaralı kaydı** olur
  — bugünkü kalibrasyon kaybolmaz.
- ⚠ **Bölüm tablosu değişikliği** tek seferlik USB tam yüklemesi ister;
  `nvs` bölümü **aynı konum ve boyutta** kalmalı (WiFi parolaları ve
  kalibrasyon orada).

### Eşitleme

1. `oturum listesi` → her oturumun kimliği, türü, durumu, son sıra no, boyutu.
2. `oturum X, sıra N'den` → ikili veri, **küçük parçalar** halinde (kartın
   web sunucusu istekleri sırayla işliyor; büyük indirme canlı akışı
   aç bırakmasın).
3. Cihaz veriyi **kalıcı diske yazdıktan sonra** `N'e kadar aldım` onayı
   gönderir. Akıllı temizlik yalnız bu onaylara bakar.
4. Cihaz kartın baytlarını **aynen** saklar. "Ham kayıt dosyası" dışa
   aktarımı bu dosyanın kendisidir.

### Bellek bildirimi eşiği — metrik

Akıllı temizlik kopyalanmış veriyi sildiği için gerçek risk **eşitlenmemiş
veri**dir. Eşik (varsayılan %50, ayarlanabilir) bu yüzden
**"eşitlenmemiş veri / kayıt bölümü"** oranına bakar. Kart bu oranı her
an bilir ve MQTT'ye yazar; kart hiç ulaşılamıyorsa telefon son bilinen
oran + hızdan tahmin eder.

### Canlı görünüm

Kayıttan bağımsız; 4 istemci (bugün var). Köprü kayıtlıyken ikinci
istemciyi reddetme kuralı kalkar.

### Zaman

İnternet varsa NTP. Yoksa eşleşmiş ilk cihaz saatini (imzalı istekle)
verir. Saat yoksa zamanlanmış kayıt kurulamaz, arayüz bunu söyler.

### Geçiş

Köprünün `kopru/arsiv/*.satir` dosyaları (11–12 Eylül) çevrilmez, kalır.

---

## 6. Güvenlik (alt proje 1 + 2 + 4 + 5)

- **Eşleştirme:** cihaz başına parola **bir kez**. Parola ağa hiç çıkmaz:
  kart rastgele bir sayı yollar, cihaz paroladan türetilmiş anahtarla
  yanıtlar (PBKDF2 + HMAC-SHA256). Cihaz anahtarı `K` iki tarafta ayrı
  ayrı **türetilir**, ağda gitmez.
- **Güvenilir cihaz listesi** kartta: ad, eklenme, son görülme; tek
  dokunuşla kaldırma. "Parolayı değiştir" ayrıca "bütün cihazları çıkar"
  seçeneği sunar.
- **Her istek imzalı:** `HMAC(K, yöntem | yol | açılış-nonce'u | sayaç | gövde özeti)`.
  Açılış nonce'u her yeniden başlamada değişir, sayaç tekdüze → eski istek
  tekrar oynatılamaz. Canlı akış (EventSource başlık taşıyamaz) imzalı
  sorgu parametresiyle açılır.
- **Kapsam:** izleme, indirme, kayıt alma/silme, ayar — hepsi yetkili.
  "Misafir izleme" ayarı, **varsayılan kapalı**.
- **İstisnalar (emniyet):** `p0` her zaman serbest. Parola sıfırlama yalnız
  USB seri konsoldan.
- **Sırların aktarımı** (ör. MQTT kimlik bilgileri cihaza): `K` ile
  **ChaCha20-Poly1305** (RFC 8439). Kartta Arduino çekirdeğinin mbedTLS
  derlemesinde etkinse o kullanılır, değilse küçük bir uygulama; iki
  tarafta da RFC 8439 test vektörleriyle doğrulanır. Kendi şifreleme
  **icadı** yapılmaz — yalnız standart yapı.
- ⚠ Kartın `http://` kökeni güvenli bağlam değil → tarayıcıda
  `crypto.subtle` **yok**; SHA-256/HMAC/PBKDF2/ChaCha20 saf JS (`ortak/`).
- **Anahtarın cihazda saklanması:** Android Keystore · PC'de Windows
  kullanıcı hesabına bağlı şifreleme (DPAPI, `ctypes`) · tarayıcıda
  tarayıcı deposu (en zayıfı; temizlenirse yeniden eşleştirme).
- **Sınır (bilinçli):** ölçüm verisi ağda şifrelenmez; erişim korunur.
  Aynı WiFi'yi dinleyen değerleri görebilir, hiçbir şey değiştiremez.
- Mevcut `Host` beyaz listesi ve `X-Olcum` başlığı korunur.

---

## 7. Kalibrasyon (alt proje 1 + 2)

- Her kalibrasyon ayrı, kalıcı kayıt: numara · tarih · not ·
  **"donanım değişti" / "ince ayar"** işareti. Geçmiş kartta; cihazlara eşitlenir.
- Her oturum başlığında kalibrasyonun **tam kopyası** → kayıt nereye
  giderse kalibrasyonu yanında.
- Açılışta varsayılan: **kaydın kendi kalibrasyonu**. İstenirse geçmişten
  başka biri seçilir — tek kayda ya da seçili kayıtlara. Ham veri
  değişmez; seçim geri alınabilir; ekranda ve dışa aktarmada hangi
  kalibrasyonun uygulandığı yazar.
- Aynı donanım dönemindeki daha yeni ince ayar **önerilir**; başka
  döneme ait kalibrasyon uygulanırken **açık uyarı**.
- B34 ADC doğrusalsızlık düzeltmesi karara bağlanırsa kalibrasyon
  kümesinin parçası olur ve eski kayıtlara da uygulanabilir.
- **Yeniden kalibrasyonun kesinliği (1A-1'de kesinleşti):** V ve A ham kod
  olarak saklanıyor; başka kalibrasyonla ort/min/maks **tam** yeniden
  hesaplanır (min/maks tekdüze dönüşümde korunur). **W** ise kayıt anındaki
  kalibrasyonla **watt** olarak (ort/min/maks) saklanıyor; ham çarpım toplamı
  saklanmıyor. Sebep: firmware gücü hizalanmış volt × amper ve süzgeç
  düzeltmesiyle hesaplıyor; aynı hesabı kod biriminde yeniden kurmak menzil
  geçişlerinde kesintili ikinci bir hat olurdu. Sonuç: başka kalibrasyon
  uygulanınca W (ort dahil) **yaklaşık** olur ve ekranda öyle yazar.

---

## 8. Bildirimler (alt proje 1 + 4 + 5)

### Olaylar (her biri ayrı açılıp kapanır)

| Olay | Not |
|---|---|
| **Karttan haber yok** | Yalnız kayıt sürerken. Evde (aynı ağ) saniyeler; dışarıda Anlık izleme açık ~10 s, kapalı 15–30 dk. Hat dönünce **aynı bildirim** "yeniden bağlandı, kayıt sürüyor" olarak güncellenir |
| Eşitlenmemiş veri eşiği | Varsayılan %50 (§5) |
| Bellek doldu, kayıt durdu | — |
| Kayıt / pil testi bitti | Sonuçla (süre, mAh, Wh) |
| Kart yeniden başladı | "Kayıt kesildi ve sürüyor" ya da "pil testi şu saatte kesildi" |

Aynı olay iki yoldan (yerel + MQTT) duyulursa **tek** bildirim.
Evde telefon kartı yerelde görüyor ama aracı "kart düştü" diyorsa:
"ev interneti koptu, kart çalışıyor".

### MQTT düzeni

- Kart, aracıya TLS ile **sürekli bağlı**; keepalive **5 s** → aracı
  sessizliği en geç 1.5 × 5 = 7.5 s'de ilan eder.
- Bağlanırken **vasiyet (LWT)**: `durum = çevrimdışı`, retained.
- Bağlanınca `durum = çevrimiçi + son durum` (kayıt, doluluk, eşitlenmemiş
  oran), retained → uygulama açılır açılmaz görür.
- Olaylar ayrı konuya, QoS 1. İnternet yokken kart olayları biriktirir,
  dönünce yollar.
- Konu adı uzun rastgele önek; aracı kimlik bilgileri kartta NVS'te
  (depoda **asla**), cihazlara eşleştirmede şifreli aktarılır (§6).
- Aracı: bulut ücretsiz katman (HiveMQ Cloud / EMQX adayları) —
  koşullar alt proje 1'de doğrulanıp seçilir. Kendi sunucuya (Mosquitto)
  geçiş hep mümkün.
- İki yönlü olduğu için **ileride uzaktan yönetime** kapı açık — şimdi
  kapsam dışı.

### Telefon: "Anlık izleme" anahtarı (varsayılan AÇIK)

| | Açık | Kapalı |
|---|---|---|
| Tespit | ~10 s | 15–30 dk |
| Olaylar | anında | ≤ 15 dk gecikme |
| Nasıl | Ön plan servisi, aracıya sürekli bağlı | WorkManager, 15 dk'da bir |
| Kalıcı simge | "Ölçüm kartı izleniyor" — yalnız kayıt sürerken | yok |

Kayıt yokken ikisinde de hiçbir şey çalışmaz. Telefonun kendi interneti
yoksa alarm verilmez, "senin internetin yok" denir.
⚠ Android pil tasarrufu (Doze) uzun bağlantıyı kısabilir; pil
optimizasyonu muafiyeti gerekebilir — alt proje 5'te ölçülür (Ö4).

### PC

PC uygulaması da aracıya abone olur. Windows bildirimi köprüden
(`ctypes` ile bildirim alanı) ya da açık PWA penceresinden — alt proje
4'te seçilir. Köprü **yalnız standart kütüphane** kuralını korur: gerekirse
asgari MQTT 3.1.1 istemcisi yazılır (projede `tarayici.py`'nin WebSocket
istemcisi emsal).

---

## 9. Ekranlar ve ortak kod (alt proje 2 + 3 + 5)

### `ortak/` (düz JS, ES modülleri, Vue'ya bağlı değil)

Kayıt biçimi okuma · eşitleme istemcisi · imzalama (SHA-256, HMAC, PBKDF2,
ChaCha20-Poly1305) · kalibrasyon uygulama · min/maks özet katmanları ·
istatistik (min/ort/maks/RMS/tepe-tepe, aralık Wh/mAh) · osiloskop
ölçümleri (frekans, periyot, görev oranı, yükselme süresi) + FFT ·
CSV (Excel-TR: `;` + BOM) ve ham dışa aktarma · rapor içeriği · TR/EN
sözlük · **grafik çekirdeği** (uPlot sarmalayıcı, gezgin şeridi, tekerlek /
sürükleme / iki parmak hareketleri, eş imleç, boşluk kesik çizimi).

**Çizim kuralı:** özetlenen yalnız ekran resmidir. Piksel sütunu başına
min+maks; nokta sayısı piksel sayısının altına inince ham noktalar.
İmleç, istatistik, FFT, rapor, CSV **her zaman ham veriden** (Ö1).

### Web paneli (PC öncelikli; kartın ve PC uygulamasının sunduğu aynı panel)

| Ekran | İçerik |
|---|---|
| Canlı | V/A/W göstergeleri, canlı grafik, "Kaydı başlat" (elle/zamanlanmış), aktif kayıt durumu |
| Osiloskop | Dalga geniş alanda, kontroller yanda; yakalama günlüğü seçenekleri |
| Pil testi | Bugünkü akış, yeni kaydediciyle |
| Kayıtlar | Liste: ad · tür · tarih · süre · boyut · **nerede** (kart / bu cihaz / diğer cihaz); arama + etiket |
| Kayıt görünümü | Gezinmeli grafik + gezgin şeridi · aralık istatistiği · notlar · kalibrasyon seçimi · (osiloskop) ölçümler + FFT · dışa aktarma · rapor |
| Karşılaştırma | Çok kayıt üst üste; eksen zaman / mAh / "başlangıçtan beri" |
| Ayarlar | Bağlantı · güvenilir cihazlar · bildirimler · kalibrasyon geçmişi · depolama · dil · tema · Gelişmiş (bugünkü konsol) |

- Derleme adımı **yok** (kartın sunduğu panel). `app.js` (2364 satır)
  ekran başına modüllere bölünür.
- Telefon tarayıcısında yalnız "kullanılabilir" olması hedef.
- Kartın panel bölümü yeni bölüm tablosunda büyütülür; panel boyutu
  bütçesi alt proje 3'te iddia olarak konur.

### Android uygulaması (telefona özel, sade)

- **Ionic Vue + Capacitor**; derleme adımı yalnız bu klasörde (npm + Vite + Gradle).
  Makinede JDK 17 + Android SDK (API 34/36) kurulu.
- Alt gezinme: **Durum** (kart çevrimiçi mi, aktif kayıt kartı: doluluk,
  süre, son değerler, küçük grafik, başlat/durdur) · **Canlı** (osiloskop
  ve pil testi dahil) · **Kayıtlar** (analiz ve karşılaştırma; yan
  çevirince tam ekran grafik; aralık parmakla, istatistik alt panelde) ·
  **Ayarlar**.
- Analiz özelliklerinin tamamı telefonda da var, daha sade dizilmiş.
- **Kotlin eklentileri:** ağda bulma (NSD; kart `MDNS.addService` ile
  duyurur) · ön plan servisi · WorkManager · bildirimler · MQTT istemcisi ·
  dosya + paylaşım · Keystore.
- Dağıtım: imzalı APK, elle kurulum. İmza anahtarı güvenli yerde
  yedeklenir (kaybı = güncelleme yerine sil-kur).

### Rapor

Tek sayfa: grafik + özet tablo + kalibrasyon bilgisi + notlar. PC'de
PDF (yazdırma sayfası), telefonda PDF ya da resim olarak paylaşım.

### Dil

TR + EN, geçişli, iki arayüzde. Metinler sözlükte; ekrana gömülü metin yok.

---

## 10. Doğrulama

Projenin kuralı: her iddia çalıştırılabilir bir testle desteklenir,
**yeşil test bir şey kanıtlamaz**; her yeni iddianın `mutasyon.py`'de onu
yalanlayan bir mutasyonu olur.

| Katman | Yöntem |
|---|---|
| `ortak/` | Node birim testleri (Ö1: gömülü sıçramalar, her yakınlaştırma düzeyi); JS ve firmware aynı test vektörlerini kullanır (kayıt biçimi, imza) |
| Firmware | `test_firmware3.py` + benzetimler genişler; RAM bütçesi kuralı (< %40) korunur |
| Gerçek kart | Flaş yazmanın ölçüme etkisi · fiş çekme (Ö2) · uzun kopukluk + bayt karşılaştırma (Ö3) · 4 canlı izleyici · MQTT tespit süresi (Ö4) · trafik kaydında sır arama (Ö5) · bringup koşucusu kırmızıya dönmez |
| Panel | `tarayici.py` ile başsız render, iki tema, telefon genişliği, konsol hatası yok |
| Android | Emülatör + gerçek telefon: NSD · ekran kapalı saatlerce hayatta kalma · Ö4 · Ö6 · pil tüketimi ölçümü |

Mevcut iddialar kırmızıya dönmez; eskiyenler **gerekçesiyle** güncellenir
(ör. `/pil` ucu, köprünün ikinci istemci kuralı).

---

## 11. Riskler — ölçülmeden karar verilmeyecekler

| Risk | Nerede ölçülür | Ölçüm kötü çıkarsa |
|---|---|---|
| Flaş silme/yazma işlemciyi on ms'ler durdurur → ölçüm boşluğu | Alt proje 1, gerçek kart | PSRAM'de biriktirip toplu yazma; silmeyi boş zamana kaydırma; ayrıntılı kipte süre sınırı |
| Sürekli TLS bağlantısı RAM bütçesini (< %40) aşar | Alt proje 1 | Tampon küçültme; TLS'i yalnız kayıt sürerken açma |
| Ücretsiz MQTT katmanı koşulları (bağlantı süresi, trafik, keepalive alt sınırı) | Alt proje 1 | Başka aracı; kendi Mosquitto sunucusu |
| Android Doze uzun bağlantıyı keser → Ö4 tutmaz | Alt proje 5 | Pil optimizasyonu muafiyeti; olmazsa kullanıcıya dürüst süre |
| 800 bin noktada telefon akıcılığı (Ö6) | Alt proje 2 + 5 | Özet katmanlarını önceden diske yazma |
| Pil testinde yeni kaydedici emniyet davranışını değiştirir | Alt proje 1 | Mevcut B21/B41 iddiaları + mutasyon |

---

## 12. Kapsam dışı (şimdilik)

- Dışarıdan **canlı veri izleme** ve **uzaktan yönetim** (MQTT kapıyı açık bırakıyor).
- Koşullu/tetikli kayıt başlatma.
- iOS, Play Store yayını.
- Birden fazla kart.
- Bulut yedekleme (kayıtlar kart + PC + telefonda).
- Kablosuz firmware güncellemesi (OTA).
- Köprünün eski `.satir` arşivinin yeni biçime çevrilmesi.

---

## 13. Alt proje tasarımlarına bırakılan ayrıntılar

Bunlar belirsiz değil, **sahibi ve karar ölçütü belli** ayrıntılar:

| Ayrıntı | Sahibi | Karar ölçütü |
|---|---|---|
| İkili kayıt biçimi (alanlar, blok boyu, CRC) | 1 | Kapasite + Ö2 + `ortak/` ile ortak test vektörü |
| Ham bölüm mü LittleFS mi | 1 | Flaş durma ölçümü + güç kesme testi |
| Yeni bölüm tablosu (panel / kayıt / nvs aynı) | 1 | nvs konumu değişmez; panel bütçesi |
| Eşitleme uçlarının adları ve parça boyu | 1 | Canlı akışın takılmaması (ölçüm) |
| Eşleştirme mesaj sırası, PBKDF2 tur sayısı | 1 + 2 | Telefonda < 1 s, kartta < 1 s |
| MQTT aracısı seçimi | 1 | §11 |
| PC bildirim yolu | 4 | Stdlib kuralı |
| MQTT Android istemcisi | 5 | Bakımı süren, açık lisanslı |
| Görsel tasarım | 3, 5 | Kullanıcı seçimi (aday turu) |
