# Alt proje 5 — Android uygulaması (tasarım)

**Durum:** ✅ kullanıcı onayladı (2026-10-04) — §10'daki 7 karar, şartlarıyla (§10 sonu). Plan: `2026-10-04-plan-5-android.md`.
**Dal / ağaç:** `5-android`, ayrı çalışma ağacı; uygulama `mobil/` altında. Push ve `main`'e birleştirme yok.

Üst tasarım: [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §3 (Ionic Vue + Capacitor,
telefona özel ekranlar), §5 (eşitleme), §6 (güvenlik), §8 (bildirimler), §9 (Android), §10, §11; Ö3–Ö7.
Protokoller: [1D](2026-10-01-1d-eslestirme.md) K5–K12, [1E](2026-10-01-1e-mqtt-bildirim.md) K3–K10 + zarf.
Hesap kodu: [alt proje 2](2026-10-02-alt-proje-2-ortak.md) (`ortak/src`). Dersler:
[alt proje 4](2026-10-03-alt-proje-4-pc.md) (sayaç kilidi 4B-12, kimlik 4B-6, `p0` 4B-7, IP önbelleği 4J).

## 1. Amaç ve kapsam

Telefonda kartı izleyen, kaydı başlatıp durduran, kayıtları telefona eşitleyip inceleyen ve kayıt
sürerken kart düşerse ~10 s'de haber veren bir uygulama. Kullanıcı kararı (2026-10-03): **önce hızlı
çalışan bir uygulama**; osiloskop ve pil testi ekranları ilk kabulden sonra.

| İlk kabulde (5A–5G) VAR | İlk kabulden SONRA (5H) | Kapsam dışı |
|---|---|---|
| Kartı bulma, eşleştirme, imzalı istekler | Osiloskop ekranı (canlı yakalama, günlük) | Dışarıdan canlı veri / uzaktan komut |
| Durum · Canlı (V/A/W + grafik + kayıt başlat/durdur) | Pil testi ekranı (`p1` başlatma) | iOS, Play Store |
| `p0` her ekranda | Karşılaştırma ekranı | Birden çok kart |
| Kayıt eşitleme, Kayıtlar listesi, kayıt görünümü (grafik, aralık istatistiği, notları okuma) | Zamanlanmış kayıt kurma, not/ad düzenleme, kalibrasyon seçimi | OTA, bulut yedek |
| Bildirimler (ön plan servisi + MQTT, WorkManager) | | |
| CSV / ham dosya / rapor paylaşımı, TR + EN, açık/koyu | | |

Kayıtlar'da osiloskop ve pil **oturumları** ilk kabulde de listelenir ve açılır (veri `ortak/` ile
zaten çözülüyor); ertelenen yalnız bunların canlı ekranlarıdır.

**Hedef cihazlar:** asıl telefon Honor DNP-NX9 (Android 16, API 36, MagicOS 10, WebView 154) — kurulum
ve test öncesi kullanıcıya sorulur, asıl kabul burada; geliştirme telefonu Xiaomi Redmi Note 10S
(M2101K7BG, Android 13, API 33, MIUI 14, WebView 153) — günlük kurma/kaldırma ve testler burada.
İkisi de arm64. `minSdk` **28** (Android 9) ikisini de kapsar. adb komutları her zaman `-s <seri>` ile. Ö6 eski telefonda ölçülür ama tasarım ona
göre küçültülmez; Ö4 son kabulde yeni telefonda da ölçülür.

## 2. Yaklaşım seçenekleri ve seçilen

### 2.1 Karta ağ erişimi

| Seçenek | Artı | Eksi |
|---|---|---|
| A. Capacitor'ın yerleşik `CapacitorHttp`'si | Kod yok | Akış (SSE) okuyamaz; isteği belirli ağa bağlayamaz; `p0`'a ayrı yol veremez |
| **B. Kendi küçük Kotlin eklentisi `KartAg`** (`HttpURLConnection`, bağımlılık yok) | SSE satır satır; Wi-Fi ağına bağlama; `p0` için ayrı iş parçacığı; vekilsiz | ~300 satır Kotlin, bizim bakımımızda |
| C. Yerel köprü sunucusu (uygulama içinde localhost vekili) | WebView `fetch`/`EventSource` aynen | Fazladan açık port; karmaşık |

**Seçilen: B.** Belirleyici iki gerekçe: (1) canlı akış SSE'dir; (2) kart kendi erişim noktasını
açtığında (sahada) o ağın interneti yoktur ve Android trafiği hücresel veriye yollar — istek
`Network.openConnection` ile **Wi-Fi ağına bağlanmadan** karta ulaşmaz. A bunu yapamaz.

### 2.2 Kayıtların telefonda saklanması

| Seçenek | Artı | Eksi |
|---|---|---|
| A. IndexedDB (panelin `depo_idb.js` yolu) | Hazır örnek | WebView deposu; dosya olarak paylaşılamaz; servis okuyamaz |
| **B. Uygulamanın özel dizininde dosya** (`KartDepo` eklentisi; PC ile aynı üç dosya) | PC ile bayt bayt aynı biçim; `fsync`; "ham dosya" paylaşımı dosyanın kendisi | Kotlin eklentisi gerekir |

**Seçilen: B** — `files/kart/<kimlik>/kayitlar.kyt`, `durum.json`, `kalibrasyon.json`. `ortak/src/esitle.js`
DEPO arayüzünün dosya uygulaması; sözleşme oradaki gibi (ekleme dayanıklı, durum atomik).

### 2.3 MQTT istemcisi (Kotlin, servis içinde)

| Seçenek | Artı | Eksi |
|---|---|---|
| A. HiveMQ MQTT Client | Bakımlı, tam | Netty ile birkaç MB, onlarca geçişli bağımlılık |
| B. Eclipse Paho | Yaygın | Android servisi bakımsız; 3.1.1 çekirdeği yaşlı |
| **C. Kendi asgari MQTT 3.1.1 abonesi** (`SSLSocket`, sistem CA'ları) | ~250 satır; projede iki emsal (`kopru/mqtt_istemci.py`, `mqtt_paket.h`); bağımlılık yok | Bizim bakımımızda |

**Seçilen: C.** Gereken yalnız CONNECT, SUBSCRIBE, PUBLISH alma (QoS 0/1 + PUBACK), PINGREQ. Üst
tasarım §13'ün ölçütü "bakımı süren, açık lisanslı" idi; bu ölçütten **bilerek sapılıyor** — onay
maddesi (§10-3).

### 2.4 Araç zinciri

Capacitor **6** + Ionic Vue 8 + Vue 3 + Vite; uygulama kodu düz JS (ES modülleri, `ortak/` ile aynı).
Gerekçe: makinede JDK 17 ve API 34 var; Capacitor 7+ JDK 21 ister. `compileSdk`/`targetSdk` 34,
`minSdk` 28. Sürüm uyumu 5A'nın ilk adımında **ölçülür** (boş proje derlenir, iki telefonda açılır);
tutmazsa karar kullanıcıya döner (JDK 21 kurmak sistem değişikliğidir). Bağımlılıklar
`package-lock.json` ile sabit; CLI'lar proje içinde.

## 3. Mimari

```
┌────────────── WebView (yalnız paketteki dosyalar, uzak içerik YOK) ──────────────┐
│ Ionic Vue ekranları: Durum · Canlı · Kayıtlar · Ayarlar      [DURDUR p0 her yerde]│
│ mobil/src/cekirdek/  kart.js (bağlantı durumu) · kesif.js · kasa.js · depo.js    │
│                      canli.js · bildirim.js · sozluk_mobil.js                    │
│ ortak/src/*  (içe aktarılır, DEĞİŞTİRİLMEZ): imza · kripto · zarf · esitle ·     │
│              kayit · ozet · istatistik · grafik · disari · rapor · sozluk        │
└───────────────┬──────────────────────────────────────────────────────────────────┘
                │ Capacitor köprüsü
┌───────────────┴────────────────── Kotlin ────────────────────────────────────────┐
│ KartAg   : istek(), akisAc()/akisKapat(), p0() — Wi-Fi ağına bağlı, vekilsiz     │
│ Kesif    : NSD tarama, .local çözme, etkin Wi-Fi ağı                             │
│ Kasa     : K'yi Keystore AES-GCM ile sarar/açar; sayaç işaretini saklar          │
│ KartDepo : kayitlar.kyt ekle(fsync)/kırp/oku, durum.json atomik                  │
│ Izleme   : ön plan servisi + MQTT abonesi + bildirimler + WorkManager işi        │
│ Paylas   : dosya paylaşımı (FileProvider)                                        │
└──────────────────────────────────────────────────────────────────────────────────┘
```

`ortak/` Vite takma adıyla (`@ortak` → `../ortak/src`) içe aktarılır: tek kopya, derlemede pakete girer.

## 4. Kararlar

### Bağlantı ve keşif

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| A1 | **Aday sırası (yarışarak, her biri ≤ 1.5 s):** önbellekteki son IP → `olcum.local` (sistem çözücüsü) → NSD (`_http._tcp`, kart duyurunca) → `192.168.4.1` (kartın AP'si) → elle girilen adres | NSD duyurusu firmware'de henüz yok; kod yazılır ama hiçbir akış ona bağlı değildir. PC'de mDNS 2.7 s takılıyordu (4J) → önbellek önce |
| A2 | **Her adayın kimliği `/eslestir/bilgi` ile doğrulanır;** kimlik eşleştirme kaydındakiyle aynı değilse o adrese imzalı istek ve komut GİTMEZ. İstisna yalnız `p0` (A9). Kimlik 16 onaltılık değilse ret | 4B-6. Yanlış cihaza komut gitmesin |
| A3 | **İstek adresi her zaman IP;** `Host` başlığı = o IP. Ad çözülse bile bağlantı çözülen IP'ye, başlık IP ile | Kart `Host`'ta yalnız `olcum.local`, `olcum` ve kendi IP'sini kabul ediyor (`host_gecerli`); IP her zaman geçerli, özel başlık gerekmez |
| A4 | **Bütün kart istekleri etkin Wi-Fi `Network`'üne bağlanır;** Wi-Fi yoksa istek hiç denenmez, ekran "Wi-Fi kapalı" der. Vekil kullanılmaz | §2.1. 4B-11 dersi |
| A5 | **Şifresiz HTTP yalnız uygulamanın kart isteklerinde:** `network_security_config` ile genel cleartext KAPALI kalır; izin verilen alanlar `olcum.local` + `192.168.4.1`. Sorun: yapılandırma adres aralığı (CIDR) tanımıyor, kartın ev ağındaki IP'si ise önceden bilinmiyor. **5A'da ölçülür:** `HttpURLConnection` listede olmayan özel bir IP'ye şifresiz isteği reddediyor mu. Reddediyorsa **ikinci yol:** yapılandırmada cleartext açılır, ama uygulamada ağa çıkan TEK kod `KartAg`'dir ve o hedefi **yalnız özel (RFC 1918) + bağlantı-yerel** adreslerle sınırlar; WebView'in kendi ağ isteği CSP ile kapalıdır (A47), MQTT ayrı yoldan TLS'tir | Kullanıcı şartı "genel cleartext açma". Ölçülmeden kesinleşmez — onay maddesi (§10-5) |
| A6 | **Canlı akış uygulama öndeyken açık;** arka plana geçince 5 s içinde kapatılır, öne gelince imzalı YENİ adresle açılır (`akisUrl`). Yeniden bağlanma 1, 2, 4, 8, 16, 30 s | Kartta 4 akış yuvası var; arka plandaki telefon yuva tutmasın. İmzalı adres tek kullanımlık (4B-8) |
| A7 | `X-Olcum` başlığı her istekte; `kimlik` olayı, `id:`, `retry:` yok sayılır; `event: dolu` kullanıcıya söylenir | 1D K5, 4B-8 |

### `p0` (acil durdurma)

| # | Karar | Gerekçe |
|---|---|---|
| A8 | **Düğme uygulama kabuğunda,** sekmelerin üstünde, her ekranda ve her iletişim kutusunun üstünde görünür; tek dokunuş, onay yok, ≥ 56 dp | Ö7 |
| A9 | **Ayrı yol:** `KartAg.p0()` kendi iş parçacığında, kendi bağlantısıyla; imzasız, `X-Olcum`'lu; imza kilidini, sayaç yazımını, eşitlemeyi, kimlik doğrulamayı, yeniden deneme kuyruğunu BEKLEMEZ. Hedef: bilinen son IP + (farklıysa) `192.168.4.1`, **eşzamanlı** | 4B-7. Tanınmayan karta `p0`'ın zararı yok |
| A10 | **Yeniden deneme:** 503 / ağ hatasında 150, 300, 450 ms ile en fazla 4 deneme; bağlantı zaman aşımı 800 ms. Sonuç düğmede: "durduruldu" / "ULAŞILAMADI" (kırmızı, kalıcı) | P0-S (DEVIR 5.12.84). Hedef < 1 s |
| A11 | `p0` eşleşmemiş telefonda da çalışır (adres biliniyorsa) | Emniyet eşleşmeye bağlı olmasın |

### Eşleştirme, anahtar, imza

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| A12 | **Protokol `ortak/src/imza.js` `esles()` ile birebir;** tur 10 000…1 000 000 dışı ret, kart kanıtı doğrulanmadan K kullanılmaz. Cihaz adı varsayılan telefon modeli (≤ 24 bayt), değiştirilebilir | 1D K4–K6. Kendi kripto yok |
| A13 | **Parola ekranı "WEB parolası — Wi-Fi parolası DEĞİL" der;** parola yalnız `esles()` çağrısı süresince bellekte, alan sonra temizlenir; diske, günlüğe, hata raporuna gitmez; alan otomatik doldurma/önbellekten muaf | Kullanıcı ikisini daha önce karıştırdı |
| A14 | ⚠ **K'nin saklanması: Keystore'daki dışa verilemez AES-256-GCM anahtarıyla SARILI** (`files/kasa/<kimlik>.bin`); donanım destekliyse StrongBox/TEE. "K'yi Keystore'a HMAC anahtarı olarak içe aktar" seçeneği **reddedildi**: K aynı zamanda `/bildirim/bilgi` zarfının ChaCha20 anahtarı (1E K10) ve Keystore içe aktarılmış anahtarla ChaCha20 yapamaz | Bedeli: uygulama çalışırken K süreç belleğinde (WebView + servis). Durağan halde dosya tek başına işe yaramaz. Kullanıcı kimlik doğrulaması (parmak izi) İSTENMEZ — servis ekran kilitliyken de açabilmeli |
| A15 | **Yalnız WebView imzalar; servis hiç imzalı istek atmaz.** Bütün imzalar tek `cihaz` nesnesinden, `imza.js` `ac()`/`akisUrl()` ile | JS tek iş parçacıklı: `sonrakiSayac` eşzamanlı olamaz → PC'deki 401 yarışı (4B-12) yapısal olarak yok. Servis imzalasaydı süreçler arası kilit gerekirdi |
| A16 | **Sayaç kalıcılığı blok ayırmayla:** `ortam.kaydet` kancası, sayaç diskteki işareti geçecekse işareti `sayaç + 4096` olarak **istek gitmeden önce** dayanıklı yazar. Açılışta `son = diskteki işaret`. Sayaç = `max(son + 1, unix_ms)` (`imza.js`) | Uygulama çökse, saat geri alınsa da sayaç geri gitmez; her istekte disk yazımı yok |
| A17 | 401 + yeni `X-Acilis` → `ac()` bir kez yeniden dener (hazır). 401 + aynı açılış → "Bu telefon kartta silinmiş" ekranı, yeniden eşleştirme önerisi; K silinmez (kullanıcı siler) | 4B-8 |
| A18 | NTP'siz kartta (`bilgi.saat` ≠ 1) bağlantı başına bir kez imzalı `/saat` | 1D K12, 4B-9 |
| A19 | "Eşleşmeyi kaldır": kartta `/cihaz/sil` (ulaşılıyorsa) + sarılı K + Keystore anahtarı + MQTT zarfı silinir; kayıtlar ayrı soruyla | — |

### Kayıtlar ve eşitleme

| # | Karar | Gerekçe |
|---|---|---|
| A20 | **`ortak/src/esitle.js` `Esitleyici` + dosya deposu** (§2.2); parça 8192 B, istek başları arası ≥ 100 ms | 4C ölçümü: canlı akış etkilenmiyor |
| A21 | ⚠ **Varsayılan ONAYSIZ** (`onay: null`). Ayarlar'da "Bu telefon da onaylasın" anahtarı, açıklamasıyla: "Açarsan kart, PC'nin henüz almadığı kayıtları silebilir." Açıkken onay yalnız `veriEkle` dayanıklı döndükten sonra | Kullanıcı şartı; PC9 |
| A22 | **Eşitleme uygulama öndeyken:** bağlanınca, kayıt biterken ve 60 s'de bir; elle "Şimdi eşitle". Arka planda eşitleme YOK | Servis imzalamıyor (A15); telefon arşiv değil, kopya |
| A23 | **Bozulmaya dayanıklılık `esitle.js` sözleşmesiyle:** açılışta akış durumdan uzunsa geçerli kayıtlar ileri sarılır, yarım kuyruk kırpılır; kısaysa hata ve kullanıcıya "kopyayı sıfırla" seçeneği. CRC `kayit.js` `akisCoz` | Yarım yazma |
| A24 | **Büyük dosya WebView'e ham bayt olarak** (yerel dosya adresi + `fetch` → `ArrayBuffer`), base64 köprüsünden değil; çözme ve özet piramidi Web Worker'da | 11.4 MB'lık akışta arayüz donmasın (Ö6) |
| A25 | **Kayıtlar listesi telefondaki kopyadan** + kart erişilebilirse `/kayit/liste` ile "nerede: kart / telefon / ikisi" | Dışarıdayken de çalışır |

### Grafik (Ö6)

| # | Karar | Gerekçe |
|---|---|---|
| A26 | **`ortak/src/grafik.js` `Grafik` + `ozet.js` piramidi** (kendi tuval çizimi, uPlot değil); dokunma hareketleri hazır (kıskaç, sürükleme). Yan çevirince tam ekran | Tek kopya çizim kuralı (Ö1) |
| A27 | **Ö6 ölçümü uygulamanın içinde:** Ayarlar › Gelişmiş › "Grafik ölçümü" — 800 bin noktalık üretilmiş seride betikli 200 yakınlaştırma/kaydırma karesi; kare süresi ortanca / p95 / en uzun ekranda ve paylaşılabilir. Ölçüt p95 < 33 ms. Eski telefonda ve Honor'da koşulur, sayılar spec'e yazılır | Ölçüm tekrarlanabilir olsun; "akıcı görünüyor" kanıt değil |

### Bildirimler

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| A28 | **Servis yalnız kayıt sürerken:** ön plan servisi (tür `connectedDevice`; reddedilirse `specialUse`), kalıcı bildirim "Ölçüm kartı izleniyor". Kayıt bitince bitiş bildirimi atılır ve servis kendini durdurur | §8. `dataSync` türü Android 15+'ta günde 6 saatle sınırlı — uzun kayıtta ölür |
| A29 | **Servis ne zaman başlar:** (a) kayıt bu telefondan başlatıldığında, (b) uygulama öndeyken kartın kayıtta olduğu görüldüğünde, (c) WorkManager işi aracıdaki kalıcı (retained) durumda kayıt gördüğünde. (c)'de Android 12+ arka plandan servis başlatmayı engelliyorsa (pil muafiyeti yoksa) iş "Kayıt sürüyor — izlemek için dokun" bildirimi atar | Kayıt PC'den başlatılmış olabilir |
| A30 | **WorkManager işi 15 dk'da bir, yalnız eşleşmiş + bildirim ayarı tamamken;** aracıya bağlanır, kalıcı durumu okur, kapanır (≤ 20 s). "Anlık izleme" kapalıyken olaylar da bu yoldan (≤ 15 dk gecikme) | §8 tablo |
| A31 | **Aracı bilgisi:** WebView imzalı `/bildirim/bilgi`'yi alır, **zarfı olduğu gibi** `files/kasa/<kimlik>.zarf`'a yazar. Servis K'yi `Kasa`'dan açar, zarfı platformun ChaCha20-Poly1305'iyle (API 28+) çözer; çözülmüş URI/kullanıcı/parola/önek/anahtar yalnız bellekte. Çözme hatası ya da CONNACK 4/5 → "bildirim ayarı yenilenmeli, uygulamayı kartın ağında aç" | PC14. Kotlin'de ikinci bir zarf çözücü var ama kripto platformun; `ortak/test/vektor/kripto.json` ve `uretim/vektor_guvenlik.json` ile bayt bayt sınanır |
| A32 | **Yük çözme:** her mesaj `OKB1` zarfı, AAD = konu adı; etiketi tutmayan mesaj atılır ve sayılır. Yalnız abone; uygulama hiçbir konuya yayın yapmaz | 1E K3, K5 |
| A33 | **"Karttan haber yok":** vasiyet (`c:0`) gelince, yalnız son bilinen durumda kayıt sürüyorsa. Sabit bildirim kimliği → hat dönünce **aynı bildirim** "yeniden bağlandı, kayıt sürüyor" olur | §8 |
| A34 | **Telefonun kendi interneti:** aracı bağlantısı koparsa ya da 7.5 s PINGRESP gelmezse kart için alarm VERİLMEZ; kalıcı bildirim "Telefonun interneti yok — kart izlenemiyor" olur. `ConnectivityManager` geri bildirimiyle hemen yeniden bağlanılır | §8 |
| A35 | **Yineleme:** MQTT içinde `(a, n)`; yerel akıştan duyulan aynı olay için anlamsal anahtar (`tür`, `a`, `oturum`) + 30 s pencere → tek bildirim | PC16 |
| A36 | **Evde:** telefon kartı yerelde görüyor ama aracı "düştü" diyorsa bildirim "ev interneti koptu, kart çalışıyor" | §8. Servis yerel yoklamayı yalnız İMZASIZ `/eslestir/bilgi` ile yapar (kimlik + açılış değeri karşılaştırılır); imzalı istek atmaz (A15) |
| A37 | **İzinler açıklamayla istenir:** bildirim izni (Android 13+) ilk eşleştirmeden sonra; pil optimizasyonu muafiyeti "Anlık izleme" ilk açıldığında, neden gerektiği yazılarak; reddedilirse uygulama çalışır ve Durum'da "bildirim gecikebilir" yazar. Honor'a özel "otomatik başlatma / arka planda çalışma" ayarı için adım adım yönerge ekranı | §11 Doze riski. ⚠ Honor'un pil yöneticisi muafiyete rağmen servisi öldürebilir — Ö4'te ölçülür, sonuç dürüstçe yazılır |
| A38 | **Bildirim kanalları:** `izleme` (sessiz, kalıcı), `uyari` (sesli: haber yok, bellek doldu, eşik), `bilgi` (kayıt/pil bitti, kart yeniden başladı). Her olay Ayarlar'dan ayrı açılıp kapanır | §8 |

### Ekranlar

| # | Karar |
|---|---|
| A39 | **Durum:** bağlantı (bu ağda / dışarıda-MQTT / ulaşılamıyor + son görülme), aktif kayıt kartı (tür, süre, doluluk, eşitlenmemiş oran, son V/A/W, küçük grafik), başlat/durdur, eşitleme durumu. Dışarıdayken MQTT'nin son durumu, komut düğmeleri kapalı ve nedenini söyler |
| A40 | **Canlı:** büyük V/A/W, canlı grafik (son 60 s / 5 dk), kayıt hızı seçimi + başlat (`Gb<ms>`) / durdur (`Gd`). Kart bu ağda değilse "kart bu ağda değil". Pil testi sürüyorsa salt okuma + "pil testi sürüyor" |
| A41 | **Kayıtlar:** liste (ad, tür, tarih, süre, nerede), arama; kayıt görünümü: grafik + gezgin şeridi, parmakla aralık → alt panelde istatistik (`istatistik.js`, ham veriden), notlar (okuma), paylaş (CSV `;`+BOM, ham `.kyt`, rapor) |
| A42 | **Ayarlar:** kart (adres, kimlik, eşleşme, eşleşmeyi kaldır) · bildirimler (anlık izleme, olaylar, izin durumu) · eşitleme (onay anahtarı, depolama, kopyayı sıfırla) · dil · tema · Gelişmiş (kendini sınama: kripto vektörleri WebView'de ve Kotlin'de; grafik ölçümü; sürümler) |
| A43 | **Metinler sözlükte:** `ortak/src/sozluk.js` (ortak anahtarlar) + `mobil/src/sozluk_mobil.js` (telefona özel; `sozluk_pc.js` deseni), TR + EN. Kotlin tarafındaki bildirim metinleri `strings.xml` (tr, en) |
| A44 | ✅ **Seçildi (2026-10-04): aday A — "Tezgah"** (panelin Koyu görünümünden; DURDUR sekmelerin üstünde tam genişlik şerit). Adaylar `mobil/tasarim-adaylari/`. **Görsel tasarım ayrı tur:** 5A'dan sonra 3 aday (Durum + Canlı + kayıt görünümü, açık ve koyu), telefonda gerçek boyutta; kullanıcı seçer. Ortak şartlar: dokunma alanı ≥ 48 dp, metin kontrastı ≥ 4.5:1, sistem yazı boyutuna uyum |

### Gizlilik ve dağıtım

| # | Karar |
|---|---|
| A45 | **Günlük kuralı:** parola, K, P, zarf içeriği, aracı adresi/kullanıcı/parolası, konu öneki, bildirim anahtarı hiçbir günlüğe yazılmaz. Kotlin'de tek `Gunluk` sarmalayıcısı; release derlemesinde ayrıntı günlüğü kapalı. Test: derlenmiş kaynakta `Log.`/`console.` çağrılarının argümanları taranır + cihazda eşleştirme sonrası `logcat` (yalnız kendi paketimiz) içinde bilinen sınama sırları aranır |
| A46 | **Yedekleme kapalı** (`allowBackup=false`, veri çıkarma kuralları boş): sarılı K ve zarf bulut yedeğine gitmez |
| A47 | **WebView:** yalnız paket içi dosyalar; CSP `default-src 'self'`; gezinme dışarı kapalı; uzak betik yok |
| A48 | **İmza:** debug anahtarı geliştirmede; release anahtarı depo DIŞINDA (çalışma alanının `.yedek/` klasörü altında, yedekli), Gradle onu ortam değişkeninden okur. `mobil/.gitignore`: `node_modules`, `dist`, `android/app/build`, `android/.gradle`, `local.properties`, `*.keystore`, `*.jks`, `*.apk`, `*.aab` |

## 5. Hata durumları (özet)

| Durum | Davranış |
|---|---|
| Wi-Fi yok / kart bulunamadı | Durum "ulaşılamıyor" + son başarılı adres + "elle adres"; MQTT durumu varsa o gösterilir |
| Kimlik uymuyor | "Bu adresteki kart eşleştiğin kart değil" — imzalı istek gitmez |
| 401 aynı açılış | A17 |
| 4 akış yuvası dolu | "Karta 4 izleyici bağlı" + 10 s'de yeniden dene |
| Eşitleme yarıda | Kaldığı sıradan sürer; durum dosyası atomik |
| Depo bozuk | A23 |
| Zarf çözülmüyor | A31 |
| Bildirim izni yok | Servis çalışır, Durum'da uyarı; izin ekranına kısayol |

## 6. Doğrulama

Kural: her iddia çalıştırılabilir bir testle; her iddianın onu **yalanlayan** bir mutasyonu.

| Katman | Araç | Ne |
|---|---|---|
| JS çekirdek | vitest (Node) | keşif sırası ve kimlik reddi · sayaç işareti (çökme, saat geri) · `p0`'ın hiçbir kilidi beklemediği (kilit tutulurken `p0` süresi) · depo sözleşmesi · sözlük eksiksizliği (TR = EN anahtar kümesi) · şablonlarda gömülü metin yok |
| `ortak/` paket içinde | `node --test ../ortak/test` (salt çalıştırma) + uygulama içi kendini sınama | Paketlenmiş kod WebView'de vektörleri geçiyor |
| Sahte kart | `mobil/test/sahte-kart/` (Node `http`): 1D uçları, imza doğrulama (bağımsız uygulama — Python `kopru/imza.py`'nin vektörleriyle sınanmış), 64'lük pencere, `Host` beyaz listesi, CORS yok, `/akis` 4 yuva, `/kayit/*`, `/bildirim/bilgi`, 503 enjeksiyonu | Uçtan uca, kartsız |
| Sahte aracı | `mobil/test/sahte-araci/` (Node `net`/`tls`): keepalive, vasiyet, retained | Ö4'ün kartsız ön ölçümü |
| Kotlin | JUnit (JVM): MQTT paketleri, zarf çözme vektörleri, yineleme, sayaç işareti dosyası; `Kasa` cihaz testi (instrumented) | — |
| Cihaz | adb ile debug APK; yalnız kendi paketimiz | eşleştirme, akış, `p0` süresi, eşitleme, servis ömrü |
| Mutasyon | `mobil/mutasyon/` — liste + koşucu: kaynağı **kopyada** bozar, ilgili testi koşar, kırmızı bekler | Her dilimde; yaşayan mutasyon = boş iddia |
| Gizlilik | `python uretim/gizlilik_dogrula.py` (salt okuma) her commit'ten önce | — |

**Gerçek kart kabulü (5G; "kart serbest" denince).** İzinli: `?`, `G?`, `p0`, `p`, `Gb<ms>`/`Gd` (kısa
kayıt, adı "Android test"), salt okuma uçları. Yasak: `N…`, `E…`, `Q…`, `k…`, `GF!`, `p1`, firmware,
seri port. Ölçülecekler: eşleştirme (parolayı kullanıcı yazar) · `p0` dokunuştan kart yanıtına süre,
20 tekrar (< 1 s) · Ö3 telefon kopyası = kartın baytları (PC arşiviyle karşılaştırma) · Ö5 trafik
kaydında parola/K yok · 4 izleyici dolu davranışı · Ö4 fiş çekme ≥ 10 tekrar, ekran kapalı, iki telefonda
(yeni telefon için kullanıcıya "Honor'u bağla" denir) · Ö6 iki telefonda · 8 saat ekran kapalı servis
ömrü + pil tüketimi.

## 7. Dilimler

| Dilim | Teslim | Kart |
|---|---|---|
| **5A** | İskelet (araç zinciri ölçümü), `mobil/.gitignore`, vitest + mutasyon koşucusu, sahte kart, `KartAg` + `Kesif`, A5 cleartext ölçümü, telefonda "kartı bul" ekranı (sahte karta karşı) | Hayır |
| — | **Görsel tasarım turu** (3 aday) → kullanıcı seçer | — |
| **5B** | `Kasa`, eşleştirme ekranı, imzalı istek, sayaç işareti, kimlik doğrulama, eşleşmeyi kaldır | Hayır |
| **5C** | Kabuk + `p0`, Durum, Canlı (akış, grafik, başlat/durdur) | Hayır |
| **5D** | `KartDepo`, eşitleme, Kayıtlar, kayıt görünümü, Ö6 ölçüm aracı | Hayır |
| **5E** | `Izleme` servisi, MQTT abonesi, zarf, bildirimler, WorkManager, izin akışları | Sahte aracı |
| **5F** | Paylaşım (CSV/ham/rapor), EN, erişilebilirlik geçişi, tema | Hayır |
| **5G** | Gerçek kart + iki telefon kabulü, release imzası | **Evet** |
| 5H | Osiloskop + pil testi + karşılaştırma + düzenleme özellikleri | Sonra |

5B ∥ 5D'nin depo kısmı ∥ 5E'nin Kotlin çekirdeği paralel yürüyebilir (ortak dosyaları yok). Her
dilimin sonunda bağımsız çürütücü; doğrulanan bulgu önce kırmızı testle.

## 8. Diğer oturumdan istekler (`mobil/DEVIR-ISTEK.md`)

1. `MDNS.addService("http", "tcp", 80)` + TXT kaydında kart kimliği (planlı; A1 ona bağımlı değil).
2. Bilgi: `ortak/src/imza.js` `ac()` kimlik denetlemiyor (4B-15'te açık yazılı) — telefon denetimi
   kendi sarmalayıcısında yapıyor; `ortak/`'ta değişiklik İSTENMİYOR.

## 9. Riskler

| Risk | Nerede ölçülür | Kötü çıkarsa |
|---|---|---|
| Honor pil yöneticisi servisi öldürür → Ö4 tutmaz | 5E (eski telefon), 5G (Honor) | Yönerge ekranı; olmazsa kullanıcıya dürüst süre |
| Capacitor 6 + API 34 hedefi Android 16'da sorun çıkarır | 5A ilk adım | JDK 21 + yeni Capacitor (kullanıcı kararı) |
| Özel IP'ye cleartext yapılandırmayla açılamıyor | 5A | A5'teki ikinci yol |
| 800 bin noktada eski telefon < 33 ms tutmaz | 5D | Sayı yazılır; tasarım küçültülmez (kullanıcı kararı); piramidi diske yazma seçeneği |
| Saf JS PBKDF2 (20 000 tur) telefonda > 1 s | 5B | Ölçülür, ekranda ilerleme; protokol değişmez |
| `connectedDevice` servis türü Wi-Fi cihazı için reddedilir | 5E | `specialUse` |

## 10. ✅ Onaylanan kararlar (2026-10-04) ve şartları

1. **A14** — K, Keystore AES anahtarıyla sarılı saklanır (HMAC içe aktarma değil); parmak izi istenmez.
2. **A15** — yalnız WebView imzalar; servis karta imzalı istek atmaz, arka planda eşitleme yok (A22).
3. **§2.3** — MQTT istemcisi kütüphane değil, kendi asgari abonemiz (§13 ölçütünden sapma).
4. **§2.4** — Capacitor 6 / JDK 17 / hedef API 34; uygulama kodu düz JS.
5. **A5** — cleartext'in nasıl sınırlanacağı 5A'da ölçülüp kesinleşir; ikinci yol kabul mü.
6. **A28–A29** — servis türü `connectedDevice`; kayıt PC'den başlatıldıysa telefon bunu en geç 15 dk'da
   fark eder (kayıt yokken sürekli bağlantı yok).
7. **§1 tablo** — ilk kabulde not/ad düzenleme, zamanlanmış kayıt kurma ve kalibrasyon seçimi YOK (5H).

### A5 ölçümü (2026-10-04, Xiaomi M2101K7BG, Android 13) — İKİNCİ YOL kesinleşti

Yapılandırma cleartext'i kapalı tutup yalnız `olcum.local` ve `192.168.4.1`'e izin verirken gerçek kartın
ev ağındaki özel IP'sine istek **engellendi** (`NetworkSecurityPolicy.isCleartextTrafficPermitted(ip)` =
false; ekranda `cleartext`). `olcum.local` adayı da engellendi, çünkü istek çözülen IP'ye gidiyor (A3).
Yapılandırma adres aralığı tanımadığından onaylı ikinci yola geçildi: `network_security_config` cleartext
AÇIK; sınır kodda — ağa çıkan tek kod `KartAg`, hedef yalnız RFC 1918 + bağlantı-yerel IPv4
(`Hedef.kt` / `hedef.js`, ortak vektör `mobil/test/vektor/hedef.tsv`; herkese açık IP'nin reddi orada
sabit). İkinci yolla aynı telefonda gerçek kart bulundu: `olcum.local` ile 1175 ms, önbellekten 370 ms;
NSD duyurusu (`_http._tcp`, port 80) görüldü ve TXT `kimlik` `/eslestir/bilgi` ile aynı.
Açık: Android 16'nın yerel ağ erişimi kuralları Honor'da ölçülecek (Ş5; kullanıcıya sorularak).

### Kullanıcının şartları (bağlayıcı)

| # | Şart | Nerede sabitlenir |
|---|---|---|
| Ş1 | **Sayaç dosyasına YALNIZ tek süreç yazar** (uygulamanın ana süreci, `Kasa` eklentisi). Servis aynı süreçte çalışır (`android:process` verilmez) ve sayaç dosyasına dokunmaz. İkinci yazar eklenirse karar yeniden değerlendirilir (PC'de iki süreç → 401, 4J-6) | 5B: manifestte `android:process` olmadığını ve `Kasa` dışında sayaç yoluna yazan Kotlin kodu bulunmadığını ölçen test + mutasyonu |
| Ş2 | **MQTT TLS'inde sertifika VE ana bilgisayar adı doğrulaması zorunlu** (`SSLSocket` kendiliğinden ad doğrulamaz → `endpointIdentificationAlgorithm = "HTTPS"`); `mqtt://` (şifresiz) uygulamada HİÇ kabul edilmez | 5E: sahte aracıya karşı — yanlış ada kesilmiş sertifika, kendinden imzalı sertifika, süresi geçmiş sertifika → bağlantı REDDİ; gerçek aracıda yalnız-abone bağlantı (5G) |
| Ş3 | **Aracı adresi / kullanıcı / parola / konu öneki / yük anahtarı hiçbir günlüğe, hata metnine, dosyaya düşmez.** Hata metni istisnanın `message`'ından değil **türünden** kurulur (sabit metin tablosu) | 5E: bilinen sınama sırlarıyla her hata yolunun çıktısında arama + mutasyon |
| Ş4 | **JDK 21 gerekirse yalnız proje içinde** (Gradle toolchain ya da `org.gradle.java.home`); sistem `JAVA_HOME`/`PATH` değiştirilmez | 5A |
| Ş5 | **Cleartext önce ölçülür;** ikinci yol gerekirse herkese açık IP'nin REDDİ testle sabit. Android 16'nın yerel ağ erişimi kuralları Honor'da ölçülür; kart isteği orada da çalışmalı | 5A (ölçüm + ret testi), Honor ölçümü kullanıcıya sorularak |
| Ş6 | **Pil yöneticisi yönergesi iki üretici için:** MIUI (Otomatik başlatma · Pil tasarrufu "Kısıtlama yok" · son uygulamalarda kilitle) ve MagicOS (Uygulama başlatma "Elle yönet": otomatik başlat + ikincil başlatma + arka planda çalış · pil optimizasyonu "İzin verme") | 5E (A37) |
