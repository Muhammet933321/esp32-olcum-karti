# mobil/ — durum

Alt proje 5 (Android). Dal `5-android`, ayrı çalışma ağacı. Push yok, `main`'e birleştirme yok.
Tasarım: `tasarim/2026-10-04-alt-proje-5-android.md`.

## 2026-10-03

**Biten**
- Okuma: üst tasarım, 1D, 1E, alt proje 2 ve 4, `ortak/src` arayüzleri.
- Çalışma ağacı ve dal açıldı.
- Tasarım belgesi TASLAK olarak yazıldı.

**Açık**
- Tasarımın kullanıcı onayı (§10'daki 7 madde). Onaydan önce kod yok.
- Geliştirme telefonu adb'de `unauthorized`: telefondaki "USB hata ayıklamaya izin ver" penceresi
  bu bilgisayar için onaylanmalı. Model / Android sürümü okunamadı; `minSdk 28` geçici.
- Kart diğer oturumda: "kart serbest" denene kadar karta istek yok, sahte kartla çalışılır.

**Diğer oturumdan istekler:** `mobil/DEVIR-ISTEK.md`.

## 2026-10-04

**Biten**
- Tasarım onaylandı (7 karar + Ş1–Ş6); plan `tasarim/2026-10-04-plan-5-android.md`.
- 5A-1 iskelet: Capacitor 6.2.2 + Ionic Vue 8 + Vite; debug APK **JDK 17 ile ilk denemede derlendi**
  (ilk derleme ~3 dk, APK 8.4 MB). `minSdk 28`, hedef 34, yedekleme kapalı. JDK 21 gerekmedi (Ş4).
- 5A-2 test altyapısı: vitest (`@ortak` takma adı, 1D vektörleri), sözlük kuralları + "şablonda gömülü
  metin yok" testi, mutasyon koşucusu `mutasyon/kos.mjs` (kopyada bozar; ÖLDÜ / YAŞIYOR / ŞÜPHELİ /
  UYGULANAMADI; kendi testi var).
- 5A-3 sahte kart (`test/sahte-kart/`): gerçek kartın kaynağından okunan davranış, bağımsız imza
  doğrulayıcı (`node:crypto`), 30 test.
- 5A-4 (cihaz adımları hariç): hedef kuralı JS + Kotlin aynı vektör dosyasından (`test/vektor/hedef.tsv`,
  96 satır), `HttpIstek.kt` (JVM testleri 9/9), `KartAgPlugin.kt`, `ag.js` (ortak `esles()`/`ac()` içinden
  geçiyor). Mutasyon 14/14 öldü.

**Kartın kaynağından öğrenilenler (plan varsayımından farklı)**
- `X-Olcum` eksikse kart **400** döner ve yalnız POST uçlarında arar; GET uçları ve `/eslestir/bilgi` istemez.
- `p0` başarı kodu **204**.
- `/akis` Host denetimi yapmıyor; `dolu` bir HTTP hatası değil (200 + `event: dolu` + kapanış).
- `E…`/`Q…` komutları imzalı olsa da 403; komut ≥ 176 bayt 413.

**Açık**
- ⚠ Geliştirme telefonuna kurulum reddedildi: `INSTALL_FAILED_USER_RESTRICTED` (MIUI). Geliştirici
  seçeneklerinde "USB üzerinden yükle" açılmalı ve telefonda çıkan kurulum onayı verilmeli.
  Bekleyenler: WebView'de `ortak/` kanıtı, cleartext ölçümü (A5/Ş5), "Kartı bul" duman testi.
- Kotlin mutasyonları koşucuda yok (koşucu `android/`'i kopyalamıyor) — Gradle kipli mutasyon 5B'de.
- `package-lock.json`: npm'in "deprecated" serbest metinleri (üçüncü taraf e-postası içeriyordu) gizlilik
  denetimine takılıyor → her `npm install`'dan sonra `npm run kilit`.
- 5A-5 keşif, 5A-6 ekran, 5A-7 çürütücü.

### 2026-10-04 (devam) — 5A-5, 5A-6; gerçek kart

**Yetki (kullanıcı, kalıcı):** rutin işler sorulmadan yürütülür, kararlar buraya yazılır. Durulacak
haller: kartın durumunu değiştiren her şey (eşleştirme dahil) · Honor · güvenlik ödünü / spec'ten sapma ·
paylaşılan dosyalar, push, birleştirme · sistem çapında değişiklik · para/hesap · geri alınamaz silme ·
kapsam değişikliği. Kart serbest; izinli komutlar `?` `G?` `p0` `p` `Gb`/`Gd`. `N?` her zaman yasak.

**Biten**
- 5A-5 keşif (`kesif.js` 14 test, `KesifPlugin.kt` NSD): adaylar eşzamanlı; kimlik `/eslestir/bilgi` ile;
  elle adres eşleşmemişken önce; NSD'den gelen herkese açık adres aday olmaz; yanlış TXT kimliği istek
  atılmadan elenir.
- 5A-6 "Kartı bul" ekranı Xiaomi'de **gerçek kartla**: bulundu (`olcum.local` 1175 ms; ikinci aramada
  önbellekten 370 ms); NSD duyurusu görüldü, TXT kimliği kartınkiyle aynı (DEVIR-ISTEK #1 kapandı).
  Android 13 `.local` adını sistem çözücüsüyle çözdü.
- A5 ölçüldü → ikinci yol (spec'te "A5 ölçümü").
- Testler 74 (JS) + 13 (Kotlin), mutasyon 25/25.

**Kararlar ve gerekçeleri**
- `KartAg` isteği atmadan önce `NetworkSecurityPolicy`'ye sorar ve engeli `cleartext` türüyle söyler:
  Android bu engeli sıradan `IOException` olarak atıyor, "bağlantı hatası" gibi görünüyordu.
- **Capacitor köprü günlüğü kapatıldı** (`loggingBehavior: none`, testle sabit): telefonda görüldü —
  köprü her eklenti çağrısının TÜM verisini logcat'e yazıyordu (adres bugün; yarın imza başlıkları ve
  Kasa'ya giden anahtar). ⚠ Kapandığı henüz telefonda doğrulanmadı (sonraki toplu kurulumda bakılacak).
  Ayrıca `CapacitorCookies` bütün `HttpURLConnection`'lara çerez yöneticisi takıyor ve adresi günlüğe
  yazıyor — kart çerez kullanmıyor; 5B'de `KartAg` bağlantısı çerez yöneticisinden ayrılacak.
- Mutasyon koşucusu artık **taban yeşil** şartı arıyor ve `android/` kaynağını da kopyalıyor: eski hali
  manifesti okuyan testte, kopyada dosya olmadığı için YALANCI "öldü" veriyordu (kendi testi eklendi).
- Yeni firmware: `G` satırı 15 alan (son ikisi `son_not`, `mesaj_dusen`); 5C'de 13 alanlı da kabul edilecek.

**Açık**
- 5A-7 bağımsız çürütücü.
- Honor'da (Android 16) yerel ağ erişimi ölçümü — kullanıcıya sorulacak.
- Kotlin mutasyonları (Gradle kipi) — 5B.

### 2026-10-04 (devam 2) — WebView kapısı, günlük doğrulaması

**Kullanıcı kararları:** Honor'a 5B bitince TEK kurulum (yalnız debug APK; "Kartı bul" + eşleştirme
ekranı görülür, eşleştirme YAPILMAZ; ölçüm bitince APK kaldırılır ve buraya yazılır). Kartın gerçek
adresi / ağ adı / MAC hiçbir dosyaya ve commit'e girmez ("ev ağı özel IP" denir). Gerçek kartta
eşleştirmeden önce durulur; parolayı kullanıcı telefonda girer.

**Biten**
- **Ağa çıkan tek yol KartAg** (kullanıcı şartı): üç katman.
  1. Yerel kapı `WebKapi.kt` — `MainActivity` her WebView isteğini (`shouldInterceptRequest`) ve her
     gezintiyi (`shouldOverrideUrlLoading`) buradan geçirir; `https://localhost/…` ve data/blob/about
     dışındaki her adres 403 / engel. Dış adres tarayıcıya da açtırılmaz (Capacitor'ın varsayılanı
     dış bağlantıyı tarayıcıda açmaktı).
  2. CSP: `default-src`/`script-src`/`connect-src 'self'`, `frame-src`/`object-src`/`base-uri`/
     `form-action 'none'`.
  3. Üretim kodunda `fetch`/XHR/WebSocket/EventSource çağrısı yok (kaynak testi).
  Xiaomi'de ölçüldü (uygulama içi "WebView ağ sınaması", herkese açık örnek adrese http ve https):
  fetch, XHR, img, script → engellendi; iframe → içeriksiz; gezinti → engellendi, uygulama yerinde kaldı.
  Kart keşfi kapıdan sonra da çalışıyor.
- **Köprü günlüğü kapalı — telefonda doğrulandı:** kendi sürecimizin logcat'inde (396 satır) `methodData`
  0, adres / kimlik / `eslestir` 0.
- Capacitor'ın çerez yöneticisi kaldırıldı (`CookieHandler.setDefault(null)`): kart bağlantıları çerez
  taşımaz, saklamaz.
- WebView hata ayıklaması her derlemede kapalı (`webContentsDebuggingEnabled: false`).
- Kotlin birim testleri yeniden koştu: 15/15. JS 78 test; 5A-8 mutasyonları 7/7 öldü.

**Dikkat**
- Test dosyalarında ters eğik çizgi + b (sözcük sınırı) gibi kaçışlar iki kez kontrol karakterine döndü (kabuk + betik katmanı);
  ikisini de `gizlilik_dogrula.py`'nin "kontrol karakteri" denetimi yakaladı. O iddiaların artık mutasyonu var.

### 2026-10-04 (devam 3) — 5A-7 bağımsız çürütücü ve düzeltmeler

Çürütücü hedef kuralını DELEMEDİ (60 082 girdilik JS↔Kotlin fark taraması: 0 delik; gerçek `Hedef.kt`
JVM'de koşuldu). Kanıtlı 7 bulgu getirdi; kanıt testleri `test/curutucu/` altında, hepsini önce kendim
kırmızı gördüm (9/9), sonra düzelttim. Bulundukları gün yaşayan 16 mutasyon ana listeye katıldı.

| # | Bulgu | Düzeltme |
|---|---|---|
| 1 | `HttpIstek` toplam süre sınırı başlık evresinde işlemiyordu: başlık baytlarını damlatan sunucu 300 ms sınırlı isteği 4.4 s tuttu (sınırsız uzar); iş parçacığı havuzu sınırsızdı | Bekçi: süre dolunca bağlantıyı keser (Kotlin testleri: başlık damlası < 900 ms, geç gövde < 800 ms). Havuz 8 iş parçacığı + 32 kuyruk, taşarsa `mesgul` |
| 2 | `kartFetch` ve `kesif.bul()` eklenti dönmezse sonsuza dek asılı kalıyordu; elle adres asılıyken sağlam kart "yedek"te bekliyordu | JS'te kendi süreleri (`sureli`): istek T + 500 ms, yoklama T + 700 ms, NSD taraması süre + 1 s |
| 3 | NSD ile gerçek kart gizlenebiliyordu: yanlış TXT kimliğiyle duyuru kartı yoklanmadan eletiyor, 8 sahte duyuru gerçeğin önüne geçiyordu | TXT kimliği artık yalnız SIRALAR (uyan önce), elemez; sıralamadan sonra en fazla 8 aday; Kotlin'de kayıt anahtarı kimliği de içerir (ezilmez) |
| 4 | Test altyapısında boş iddialar: `Log.wtf`, `printStackTrace`, `console.trace`, taranmayan dosyalar, dolaylı `fetch`, WebRTC, ölü koda alınmış kapı, bağlı özellik / `v-text` / tek tırnak / betik / `{{ }}` içindeki gömülü metin | Kaynak taramaları elle listeyle değil `src/` ve `android/` ağacıyla; desenler genişledi; gömülü metin ayıklayıcısı `test/yardim/gomulu_metin.mjs` (kendi testiyle); ekrandaki ham tür adları sözlüğe alındı |
| 5 | Koşucu boş süzgeçte (yanlış `--neden`) "0/0 öldü, çıkış 0" veriyordu; CSP meta etiketi silinince test iddiasız çöküyordu; fazladan CSP yönergesi yaşıyordu | Boş liste çıkış 1; CSP yönerge kümesi TAM eşitlikle sınanıyor |
| 6 | Aynı karta iki eşzamanlı istek (`olcum.local` + önbellekteki IP) | Kabul: ad çözülmeden aynı kart olduğu bilinemez. Liste artık aynı kartı bir kez gösteriyor |
| 7 | `urlDenetle` ad çevresinde boşluğu kabul ediyordu (Kotlin reddediyor); bozuk yanıt ham istisna atıyordu | İkisi de `bicim` / `ic-hata` |

Okuyarak verdiği bulgulardan yapılanlar: `hazirla`'nın saf kısmı `HedefCoz.kt`'ye çıkarıldı ve JVM'de
sınanıyor (çözülen adres de kuraldan geçer; herkese açık IP döndüren ad sunucusu `ozel-degil`) · Wi-Fi
seçimi VPN ağını dışlıyor (`NOT_VPN`) · `User-Agent` sabit `olcum-mobil` (model/sürüm sızmaz) ·
"Kartı bul" ekranı duyuru taramasını keşiften SONRA yapıyor (eşzamanlı iki tarama birbirini düşürebilir).

**WebRTC:** ne CSP'nin öteki yönergeleri ne yerel istek kapısı WebRTC'yi kapsıyor. CSP'ye `webrtc 'block'`
eklendi; uygulama içi sınamaya WebSocket ve WebRTC denemeleri eklendi. ⚠ Telefonda henüz ölçülmedi
(kurulum yapıldı ama ekran kapalıydı); `webrtc` yönergesini bu WebView sürümünün uyguladığı ÖLÇÜLMEDEN
kesin sayılmaz.

**Kabul edilen / açık**
- Eşleşmemişken ilk yanıt veren kart kazanır ve önbelleğe yazılır (spec A2: kimlik eşleştirme kaydıyla
  karşılaştırılır; eşleşme yokken karşılaştıracak bir şey yok). Eşleştirme ekranı kimliği kullanıcıya gösterecek.
- NSD seli hâlâ bir hizmet engeli olabilir (64 kayıt sınırı); yalnız NSD yolunu etkiler, önbellek ve ad çalışır.
- Çift yığınlı duyuruda ilk adres IPv6 ise aday düşer (Android 13 tek adres veriyor) — ölçülmedi.
- Kotlin mutasyonları: 5B.

Sayılar: JS 91 test, Kotlin 23 test, mutasyon 60 (hepsi ölü).

### 2026-10-04 (devam 4) — WebRTC ölçümü, 5B ve görsel tur başlıyor

**Kullanıcı kuralı (kalıcı):** rutin hiçbir şey sorulmaz, beklenmez. Telefon ekranı kapalıysa
`svc power stayon usb` + `KEYCODE_WAKEUP` (Xiaomi'de serbest); kilit PIN istiyorsa ölçüm kuyruğa alınır,
işe devam edilir, ekran açılınca kendiliğinden koşulur. Görsel tasarım 5B ile paralel; 3 aday web
panelinin görünümlerinden (Koyu · Açık · Ön panel) türetilir, TEK mesajla sunulur.

**Ölçüm (Xiaomi, Android 13, WebView 153)**
- `webrtc 'block'` CSP yönergesi bu WebView'de UYGULANMIYOR: sınamada WebRTC "GEÇTİ" çıktı (ICE adayı toplandı).
- Karar: WebRTC arayüzleri kaldırılır — yerelde belge başı betiğiyle (`addDocumentStartJavaScript`, her
  çerçeve, sayfa betiklerinden önce; `WebKapi.RTC_KAPAT`) ve JS'te uygulamanın İLK içe aktarımıyla
  (`rtc_kapat.js`; yerel özellik yoksa yedek). İki liste testle eşit tutulur; arayüz geri konamaz
  (yazılamaz, yapılandırılamaz). CSP yönergesi ileriki WebView'ler için duruyor.
- Yeniden ölçüm: fetch, XHR, img, script, **WebSocket**, **WebRTC**, gezinti → engellendi; iframe içeriksiz
  (http ve https). Kart keşfi çalışıyor (önbellekten 416 ms). Kendi logcat'imiz (463 satır): eklenti
  verisi 0, adres/kimlik 0.
- `svc power stayon usb` Xiaomi'de açık bırakıldı (kullanıcı izniyle).

Sayılar: JS 92 test, Kotlin 23 test, mutasyon 64 (hepsi ölü).

### 2026-10-04 (devam 5) — 5B: kasa, sayaç, imzalı istek, eşleştirme ekranı

**Biten (iki alt ajan yazdı; testleri ve duman testini ben yeniden koştum)**
- Kotlin `Kasa` eklentisi: K, Keystore'daki dışa verilemez AES-256-GCM anahtarıyla sarılı
  `files/kasa/<kimlik>.anahtar` (AAD kimliği içerir: başka kimliğin dosyası açılmaz); sayaç dosyası
  sağlamalı, küçük değeri `geri` ile reddeder, bozuksa 0 DÖNMEZ (`bozuk`). Atomik yazım + fsync.
  JVM testleri 36 yeni (toplam 59). 8 Kotlin mutasyonu elle doğrulandı (`mutasyon/kotlin-liste.mjs`).
- `kasa.js`: sayaç işareti blok ayırmayla (4096), işaret istekten ÖNCE dayanıklı yazılır, açılışta
  sayaç = işaret; kimlik başına tek cihaz nesnesi. `kart.js`: imzalı istek, her bağlantıda kimlik
  doğrulaması, 401 + aynı açılış → `cihaz-silinmis` (K silinmez), `/saat`, eşleşmeyi kaldır.
  `Esles.vue`: "WEB parolası — Wi-Fi parolası DEĞİL"; parola alanı istekten önce temizlenir.
  `araclar/logcat_tara.mjs`: logcat sır tarayıcısı (imza başlıkları, 64 onaltılık, kanıt, parola,
  köprü verisi, kimlik, adres + yol, verilen sınama sırları; değeri BASMAZ).
- JS 148 test; `5B:` mutasyonları 64 (tam koşu sürüyor).
- **Xiaomi'de sahte kartla duman testi (adb reverse, hata ayıklama derlemesi):** kart bulundu →
  eşleştirme ekranı → fixture sınama parolasıyla eşleşti (Keystore sarma telefonda çalıştı) → imzalı
  `/kayit/liste` geçti → uygulama öldürülüp yeniden açıldı → Keystore'dan K açıldı, sayaç işaretten
  devam etti, imzalı istek yine geçti → eşleşme kartta ve telefonda kaldırıldı.
  Kendi logcat'imiz (496 satır) `logcat_tara` ile tarandı (sınama parolası + kimlik sır olarak verildi): TEMİZ.

**Kararlar**
- Bozuk sayaç dosyasında tek kurtarma kaydı silip yeniden eşleşmek (güvenli taraf: sayaç geri gidemez).
- `gizlilik.test.js`'e tek dar istisna: `ortam = { fetch: <ad>Fetch }` anahtarı (imza.js bu adı şart
  koşuyor); çağrı, `window.fetch`, `{ fetch }` hâlâ kırmızı (kendi sınaması var).
- `/saat` değeri sorgu argümanıyla gider: kartın kaynağı `arg("unix")` okuyor, imzalı gövde form olamaz.
- Varsayılan cihaz adı "Telefon" (A12 "telefon modeli" diyordu; model okumak ayrı eklenti ister ve modeli
  karta yazmak gereksiz iz) — kullanıcı değiştirebilir.
- Geçici `Baglanti.vue` ekranı: kabuk 5C'de gelince kalkacak.

**Honor (kullanıcı onayı: tek kurulum, yalnız debug APK, eşleştirme yok, sonra kaldır)**
- Debug APK KURULDU. Ekran kapalı ve kilitli → ölçüm kuyruğa alındı (kilit açılmaz, ayar değiştirilmez).
  Bekleyen: "Kartı bul" (Android 16 yerel ağ kuralları, Ş5) + eşleştirme ekranının görünümü; ardından
  APK KALDIRILACAK ve buraya yazılacak.

**Açık**
- 5B bağımsız çürütücü (çalışıyor).
- Gerçek kartta eşleştirme: DURULACAK — web parolasını kullanıcı Xiaomi'de kendisi girer.
- Kotlin mutasyonları koşucuya bağlı değil (elle doğrulandı); `kos-kotlin` kipi yazılacak.
- Görsel tasarım seçimi kullanıcıda (A / B / C; önerim A).

- **Mutasyon (5B, tam koşu):** JS `5B:` 64/64 öldü. Kotlin: `mutasyon/kos-kotlin.mjs` yazıldı (tek kopya,
  taban yeşil şartı, her mutasyon uygulanır → Gradle → geri alınır; beklenen test kırmızı değilse ŞÜPHELİ)
  — 8/8 öldü, kopya temizlendi. Komut: `npm run mutasyon:kotlin` (Gradle ağır; başka koşu yokken).

### 2026-10-04 (devam 6) — kota sonrası devam

- Kaldığım yer git günlüğü ve bu dosyadan çıkarıldı: 5B commit'li; çürütücü kota sınırında yarıda
  kesilmişti (iki kanıt dosyası yazmıştı) → kaldığı yerden sürdürülüyor.
- Telefon ölçümleri (WebRTC/WebSocket yasağı, köprü günlüğü, kapıdan sonra keşif) "devam 4"te yapılmıştı;
  yeniden koşulacak tek şey yeni firmware'le (E6F) "Kartı bul".
- ⚠ **Kart şu an ULAŞILAMIYOR:** Xiaomi'de `olcum.local` çözülmedi, NSD duyurusu yok; PC'den de ad
  çözülmüyor (salt okuma denemesi). Uygulama doğru davrandı ("Kart bu ağda bulunamadı", üç aday listelendi,
  asılı kalmadı). Kart geri gelince kendiliğinden yeniden denenecek. Seri porta dokunulmadı.
- Honor: kilit açık görüldü ama ölçüm (Android 16 yerel ağ kuralı) kart olmadan anlamsız → kart gelince.
  Debug APK Honor'da hâlâ KURULU.

### 2026-10-04 (devam 7) — p0 çekirdeği, 5B çürütücüsü, kart döndü

**Kullanıcı kararları:** görsel tasarım **A (Tezgah)** — DURDUR sekmelerin üstünde tam genişlik şerit;
değiştirmek isterse söyler. Gerçek kartta eşleştirme çürütücü düzeltmeleri bitene kadar ERTELENDİ; web
parolası değişti (yalnız kullanıcıda), eşleştirmeden önce haber verilecek. Kart ileride ~10 dk yeniden
Honor'un hotspot'una alınacak (öbür oturumun testi): o arada kart görünmezse kartsız işe devam.

**Biten**
- 5C-p0 çekirdeği (kartsız): Kotlin `P0.kt` (adreslere aynı anda; 503 / ağ hatasında 150-300-450 ms ile
  en fazla 4 deneme; kart olmayan yanıt denenmez; kendi iş parçacıkları — ortak havuz bekletemez) +
  `KartAg.p0`; JS `ag.p0` + `durdur.js` (eklentiye basıldığı görev turunda gider; kasa/imza/kart modüllerini
  içe aktarmaz; asla atmaz; kartın AP adresi hep listede). Kotlin 67 test; `durdur.test.js` 8; mutasyon 7/7.
- 5B bağımsız çürütücü: 8 kanıtlı bulgu (`test/curutucu-5b/`). En ağırları: kart yeniden başlarken eşzamanlı
  isteklerin yanlışlıkla "cihaz-silinmis" alması; yarıda kalan eşleştirmede anahtarın diskte kalıp 32 sıfır
  baytla imza üretilmesi; iki kasa nesnesinin aynı sayacı kullanması; sahte kasa ↔ gerçek Kotlin ayrışması;
  logcat tarayıcısının kaçırdığı sır biçimleri. Düzeltmeler SÜRÜYOR (ayrı ajan).

**Kart döndü (yeni firmware) — Xiaomi'de yeniden ölçüm**
- "Kartı bul": kartın ev ağı adresi DEĞİŞMİŞ; önbellekteki eski kayıt işe yaramadı, kart `olcum.local` ile
  1270 ms'de bulundu; kimlik aynı; NSD duyurusu (`_http._tcp`, port 80) görüldü, TXT kimliği
  `/eslestir/bilgi` ile aynı.
- Not: kart ulaşılamazken (öbür oturumun ağ testi) uygulama "Kart bu ağda bulunamadı" dedi, asılı kalmadı.

**Honor (Android 16)** — debug APK açıldı, arayüz çiziliyor. Telefon henüz Wi-Fi'de DEĞİL (hotspot veriyor):
uygulama iki adayda da "Wi-Fi yok" dedi (doğru davranış: yalnız Wi-Fi ağına bağlanır, hücresele çıkmaz).
Asıl ölçüm (yerel ağ kuralı + kartı bulma) kullanıcı Honor'u ev Wi-Fi'sine bağlayınca; sonra APK kaldırılacak.

**Yeni firmware notları (5C/5D için)**
- `Q?` satırının sonunda canlılık alanları (tur adim adim_yas ping_yas pong_yas); `G` satırı 15 alan.
- Kart dosyaları ETag ile geliyor; `If-None-Match` eşleşirse 304 + boş gövde. `KartAg` 304'ü hata saymaz
  (HTTP kodunu aynen döndürür); uygulama şu an `If-None-Match` göndermiyor. `imza.ac()` 2xx dışını hata
  sayar → 5D'de koşullu istek kullanılırsa 304 ayrı ele alınacak.

### 2026-10-04 (devam 8) — Honor ölçümü YAPILDI, APK KALDIRILDI

Honor DNP-NX9, Android 16 (API 36), ev Wi-Fi'sinde; hata ayıklama APK'sı (hedef API 34), 5B derlemesi.
- **Yerel ağ erişimi (Ş5): ÇALIŞIYOR.** "Kartı bul" gerçek kartı `olcum.local` ile 1408 ms'de buldu; kimlik
  aynı; NSD duyurusu görüldü, TXT kimliği `/eslestir/bilgi` ile aynı. Hiçbir izin penceresi çıkmadı;
  şifresiz HTTP ev ağı özel IP'sine gitti (ikinci yol Android 16'da da geçerli).
- Wi-Fi yokken (telefon hotspot veriyorken) uygulama "Wi-Fi yok" dedi ve hücresele çıkmadı.
- Bağlantı ekranı: "kart bulundu, eşleşmemiş"; eşleştirme ekranı açıldı ve GÖRÜLDÜ (kimlik, adres, ad,
  "WEB parolası — Wi-Fi parolası DEĞİL"). **Eşleştirme YAPILMADI**, parola alanına dokunulmadı.
- Kendi sürecimizin logcat'i: Honor yalnız tampon başlığını verdi (uygulama satırı yok) — sır taraması
  için Honor'da veri yok; tarama Xiaomi'de yapılıyor.
- **APK Honor'dan KALDIRILDI** (`uninstall` → Success; paket listesinde yok). Honor'da hiçbir ayar değiştirilmedi.
- ⚠ Hedef API 34 ile ölçüldü. Hedef API 36+'ya çıkılırsa Android'in yerel ağ izni devreye girebilir —
  o gün yeniden ölçülmeli.
- Geçici ekranda görsel kusur: alttaki ekran değiştirme düğmesi içerikle üst üste biniyor (yalnız geçici
  kabuk; A tasarımındaki sekmelerle kalkacak).

**Kural (kullanıcı, kalıcı):** `git stash` HİÇ kullanılmaz — stash yığını bütün çalışma ağaçlarıyla ortak;
kenara koymak gerekirse bu dalda geçici WIP commit.

### 2026-10-04 (devam 9) — 5B çürütücü düzeltmeleri bitti; gerçek eşleştirmeye HAZIR

Çürütücünün 8 kanıtlı bulgusu + okuyarak verdiği 3 uyarı düzeltildi (alt ajan yazdı; testleri ben yeniden
koştum: JS **199/199** — `test/curutucu-5b/` kanıt testleri artık regresyon testi; Kotlin **69/69**).

| # | Bulgu | Düzeltme |
|---|---|---|
| 1 | Kart yeniden başlarken eşzamanlı isteklerin biri hariç hepsi "cihaz-silinmis" | Ölçüt isteğin İMZALANDIĞI açılış; farklıysa kimlik yeniden doğrulanır, bir kez yeniden imza |
| 2 | "Eşleşmeyi kaldır" cihaz kartta dururken "kartta kaldırıldı" diyordu | Üç durum: kaldırıldı (yalnız 2xx) · bilinmiyor (401) · karta ulaşılamadı; üç ayrı metin |
| 3 | 64'lük pencerenin gerisine düşen istek "cihaz-silinmis" | Aynı açılışta 401 → yeni sayaçla BİR kez yeniden imza; istek başına en çok 2 imza |
| 4 | Yarıda kalan eşleştirmede anahtar diskte kalıyor, 32 sıfır baytla imza üretiliyordu | `cihazSakla` ya tam ya hiç; tutarsız kayıt açılışta tanınıp silinir; sıfır K ile imza yok |
| 5 | Aynı diskte iki kasa nesnesi aynı sayacı kullanıyordu | `uygulama.js` tekil kart/kasa; Kotlin'de dosya varken EŞİT yazım da `geri` |
| 6 | 401'deki `X-Acilis` biçim denetimsiz imzaya giriyordu; kanıt alıp yanıt vermeyen kart "anlaşılmayan yanıt" | Yalnız 32 küçük onaltılık; kanıt gittikten sonraki her biçimsiz yanıt `kart-sahte` (kullanıcı uyarılır) |
| 7 | Sahte kasa gerçek Kotlin eklentisinden ayrışıyordu | Sahte aynı kurallara çekildi (ad ≤ 24 bayt, katı base64, Long sınırı, sıralı liste) |
| 8 | 9 boş iddia; logcat tarayıcısı sır biçimlerini kaçırıyordu | Testler güçlendi; tarayıcı boşluklu/`0x`'li onaltılık, bayt dizisi dökümü, bölünmüş base64, URL/form/JSON kodlu parolayı yakalıyor |
| + | Kasa bozukken / kimlik uymazken uygulama içinden çıkış yoktu; `sil` sırası; cihazdan cihaza aktarım | "Eşleşmeyi kaldır" o durumlarda da görünür; önce `.anahtar` silinir; `dataExtractionRules` (bulut yedeği + cihaz aktarımı hariç) |

**Xiaomi'de düzeltmeli derlemeyle duman testi (sahte kart, adb reverse):** bulundu → eşleşti → imzalı istek →
uygulama öldürülüp açıldı → imzalı istek yine geçti (Kotlin "eşit yazım geri" kuralıyla sayaç doğru ilerliyor) →
eşleşme kartta ve telefonda kaldırıldı. `logcat_tara` (450 satır, sınama parolası + kimlik sır): TEMİZ.
Sahte kart süreci durduruldu, adb reverse kaldırıldı. Ardından **gerçek kart** elle adres vermeden bulundu:
"kart bulundu, eşleşmemiş" (salt okuma; karta komut gitmedi).

**Kabul edilen / açık (düzeltme ajanının notlarından)**
- `X-Acilis`'siz 401 ve açılışı her seferinde değişen kart: 2 imzadan sonra `cihaz-silinmis` denir.
- Çok dar pencere: ilk işaret yazılmış ama hata dönmüş VE silme de başarısız VE kart o an ulaşılamıyorsa
  telefon eşleşmiş kalabilir (kartta da kayıt vardır). Kapatmak iki aşamalı "tamamlandı" işareti ister.
- `key=` deseni gerçek logcat'te gürültü yapabilir (Xiaomi'de şimdilik temiz).
- Mutasyonlar: `5B` 124 (JS) + `5B-K` 9 (Kotlin) — ajan "hepsi öldü" dedi; kendi koşum sürüyor.

**DURULDU:** gerçek kartta eşleştirme (karta 3. cihazı yazar; web parolası yalnız kullanıcıda).

### 2026-10-04 (devam 10) — GERÇEK KARTTA eşleştirme ve imzalı istek

- **Eşleştirme kullanıcı tarafından yapıldı** (web parolasını Xiaomi'de kendisi girdi): kartta cihaz 3 "Telefon".
- Kurulan derleme doğrulandı ("Yükle" penceresi çıkmamıştı): paketin `lastUpdateTime` 19:25:19, APK derleme
  19:25:01, telefondaki ve yereldeki APK boyutu aynı (8 803 617 B) → düzeltmeli derleme.
- **Gerçek kartta imzalı istek:** imzalı `GET /kayit/liste` geçti. Uygulama öldürülüp açıldıktan sonra kart
  önbellekteki adresten bulundu, kimlik doğrulandı, K Keystore'dan açıldı, sayaç işaretten devam etti ve imzalı
  istek yine geçti (**52 oturum**). Karta giden uçlar: `/eslestir/bilgi` (imzasız) ve `/kayit/liste` (imzalı).
  Komut gönderilmedi.
- **Logcat sır taraması (gerçek kart):** eşleştirmenin yapıldığı süreç (276 satır) + yeniden başlatma sonrası
  süreç (307 satır) `logcat_tara` ile tarandı — TEMİZ. Parola bilinmediği için desen tabanlı (imza başlıkları,
  40+/64 onaltılık, kanıt, parola/anahtar alanları, köprü verisi, adres + yol) + kart kimliği "sır" olarak verildi.
- **PBKDF2 süresi (Xiaomi Redmi Note 10S, WebView 153, saf JS — eşleştirmede kullanılan kod):** 20 000 tur,
  üçer tekrar, iki koşu: **28–44 ms** (ortanca 29 ve 42 ms). Hedef < 1 s → **tutuyor, 20+ kat payla**.
  Oranlamayla istemcinin kabul ettiği üst sınır (1 000 000 tur) ≈ 1.5–2.2 s; kartın bugünkü değeri 20 000.
  Ölçüm düğmesi geçici olarak "Kartı bul" ekranında (`src/cekirdek/olcum.js`); Ayarlar › Gelişmiş'e taşınacak.
- Ölçüm sırasında kart yine ağda görünmedi (ad çözülemedi; öbür oturumun testi olabilir) — uygulama
  "Kart bu ağda bulunamadı" dedi. PBKDF2 ölçümü kart gerektirmiyor.
- Mutasyon (kendi koşum): `5B` JS **124/124**, `5B-K` Kotlin **9/9** öldü.

**5B BİTTİ.** Açık işler (bilerek bırakıldı, kullanıcı onayıyla):
1. **Yarım eşleştirme penceresi:** ilk sayaç işareti diske yazılmış ama hata dönmüş VE geri alma silmesi de
   başarısız VE kart o an ulaşılamıyorsa telefon eşleşmiş kalabilir. Çözüm: iki aşamalı "tamamlandı" işareti.
2. **Art arda 401 metni:** kart 401'in sebebini başlıkta söylemediği için iki imza denemesinden sonra her
   durumda "cihaz kartta silinmiş" denir (sayaç / saat sorunu da aynı ekrana düşer). Daha dürüst bir tür
   ("kart isteği reddediyor") ya da firmware'den sebep başlığı — ikincisi DEVIR-ISTEK konusu olur.
3. PBKDF2 saf JS ana iş parçacığında: 20 000 turda ~30–45 ms, sorun değil; tur çok büyürse gösterge donar.
4. Honor'da hedef API 36+'ya çıkılırsa yerel ağ izni yeniden ölçülmeli.

**Sıradaki: 5C** — A tasarımıyla kabuk + 4 sekme + DURDUR şeridi (p0 çekirdeği hazır), akış (SSE), Durum, Canlı.

### 2026-10-04 (devam 11) — PBKDF2 ölçümünün doğrulanması; keşif için kural

**PBKDF2 "çok hızlı" sorusu (kullanıcı):** telefonda ölçülen uygulama **saf JS** — `ortak/src/imza.js` `pbkdf2`
→ `kripto.js` `pbkdf2HmacSha256` (WebCrypto `crypto.subtle` DEĞİL, Kotlin DEĞİL), WebView'in JS motorunda
(JIT derlemeli V8), ana iş parçacığında. Eşleştirmede kullanılan kodun aynısı. Kart aynı işi 764 ms'de yapıyor
çünkü 240 MHz'lik mikrodenetleyici (tur başına ~38 µs); telefonun çekirdeği JIT ile tur başına ~1.5–2 µs.
- **Doğruluk kanıtı (sabitlendi):** `test/olcum.test.js` — aynı parola (`sinama-parolasi-olcum`) + 16 sıfır bayt tuz +
  20 000 tur + 32 bayt için saf JS sonucu, testin o anda ÇAĞIRDIĞI Python `hashlib.pbkdf2_hmac` ile bayt bayt aynı
  (`3f042897…464cc676`); başka turda sonuç farklı (tur gerçekten kullanılıyor); `ortak/` kripto `subtle` içermiyor.
- Ek bağımsız kanıt zaten vardı: gerçek kartla eşleştirme BAŞARILI oldu — kart, telefonun PBKDF2'den türettiği
  P ile hesaplanan kanıtı kabul etti ve kart kanıtı telefonda doğrulandı; P yanlış olsaydı eşleşme olmazdı.
- Telefonda ölçüm çıktısı artık sonucu başvuru değeriyle karşılaştırıp "AYNI / YANLIŞ" diye gösterecek
  (`pbkdf2Olc` `dogru` alanı); yeni derlemede telefonda yeniden okunacak.

**Kural (kullanıcı): kart telefonda görünmezse** — önce NSD, olmazsa son bilinen IP; üç yol (NSD, `olcum.local`,
son bilinen IP) da başarısızsa telefonun Wi-Fi'de olup olmadığı ve telefonun IP'sinin ÖZEL olup olmadığı (adresin
kendisi değil) buraya yazılır. 19:34'teki "bulunamadı"da kart PC'den yanıt veriyordu → telefon tarafında geçici.
⚠ O koşuda sıra şuydu: `olcum.local` → ad çözülemedi; son bilinen IP → yanıt yok; NSD adayı listede YOKTU (tarama
1.2 s; duyuru o pencerede gelmemiş). 5C'de keşif süresi/yeniden deneme gözden geçirilecek (NSD penceresi 1.2 s kısa
olabilir; "bulunamadı"dan önce bir kez daha denemek).

**5C ölçümleri için kullanıcı onayı:** `Gb`/`Gd` ile kısa "Android test" kaydı, 20× `p0`, canlı akış SERBEST.
`Go` (onay) GÖNDERİLMEZ. Kart ileride ~10 dk Honor hotspot'una alınacak (AG1); o arada görünmezse kuyruğa.

- **Keşif (kullanıcı kararı):** NSD tarama penceresi 1.2 s → **3 s** (`NSD_SURE_MS`; başarı bu süreyi beklemez) ve
  "bulunamadı" demeden önce **bir kez daha** denenir (kimliği uymayan bir kart yanıt verdiyse denenmez). Testler +
  4 mutasyon (`5C-kesif`). 5C ajanları kota sınırında yarıda kesildi; kaldıkları yerden sürdürülüyor.

### 2026-10-04 (devam 12) — 5C birleştirildi; telefon ölçümleri KUYRUKTA

**Biten (iki alt ajan yazdı, kota kesintisinden sonra kaldıkları yerden sürdürüldü; testleri ben yeniden koştum)**
- Kabuk (A tasarımı): 4 sekme, DURDUR şeridi sekmelerin üstünde tek yerde ve koşulsuz; düğme `@click="acilDurdur"`
  — `uygulama.js`'te modül düzeyinde hazır (kart / kasa / keşif kurulmadan). Durum, Canlı, Kayıtlar (yer tutucu),
  Ayarlar (Bağlantı + eşleştirme + Kartı bul + ölçümler). Tema `src/tema.css` (koyu asıl, açık karşıt).
- Akış: Kotlin `SseAyirici.kt` + `Akis.kt` + `KartAg.akisAc/akisKapat` (arka planda 4 s sonra kapanır; `kimlik`
  olayı JS'e geçmez; satır > 4096 B atılır), `akis_ayir.js` (D, G 13/15 alan, GA, GT, GP, K, A), `canli.js` (yeniden
  bağlanma 1…30 s, her seferinde YENİ imzalı adres, 45 s sessizlikte düşürme, komut beyaz listesi).
- Birleştirmede eklenenler (ben): `kart.akisUrl()` (kimliği doğrulanmış + eşleşmiş karta imzalı akış adresi; adres
  ekrana/hata metnine verilmez); `Gb` alt sınırı 50 → **20 ms** (kartın 50/s hızı; plan aralığını ben yanlış yazmıştım).
- Sayılar: JS **296/296**, Kotlin **95/95**; derleme hatasız. Mutasyon (ajan bildirimi): akış 35/35, kabuk 36/36,
  Kotlin 3/3 — kendi koşum sürüyor.

**Alt ajanların kendi verdiği kararlar (kullanıcıya bildirildi; itiraz gelmezse kalır)**
- "Kaydı durdur" iki dokunuş (ikinci dokunuş "Eminim, durdur", 4 s); ACİL DURDUR tek dokunuş, onaysız.
- `G` satırı tür / hız / başlangıç anını taşımıyor → Durum kartında oturum numarası; hız bu telefonun gönderdiği
  `Gb`'den ya da nokta artışından ("~5/s"); süre bilinmiyorsa "—".
- Grafikte sağ eksen tek birim (A ya da W), V sol eksen.
- Akış açılınca bir kez imzalı `G?` gönderilir (kart `G`'yi yalnız değişince basıyor). Salt okuma, izinli komut.
- `canli.js`'te `yenidenBul` kapalı; kartı yeniden arama kabukta (`kabuk_durum.js`: bulunamazsa 15 s'de bir, akış
  30 s hatadaysa). ⚠ İki tarafın birlikte davranışı telefonda denenmedi.

**⚠ Telefonlar USB'den AYRILMIŞ** (adb'de cihaz yok, 23:45). Xiaomi'ye 5C derlemesi KURULAMADI. Kuyruk (Xiaomi bağlanınca):
1. Kurulum + `lastUpdateTime` doğrulaması; ilk açılış (Vue bileşenleri hiçbir testte çalıştırılmadı — ilk gerçek deneme).
2. Canlı akış gerçek kartta (D satırları, grafik); arka plana alınca yuvanın boşalması.
3. Kısa "Android test" kaydı: `Gb1000` → Durum'da görünür → `Gd`. `Go` GÖNDERİLMEZ.
4. DURDUR: dokunuş → kart yanıtı, 20 tekrar, hedef < 1 s.
5. PBKDF2 çıktısında doğruluk işareti; yeni keşif süresi (NSD 3 s + bir kez yeniden deneme).
6. Klavye açıkken şerit; koyu / açık tema görünümü; sistem yazı boyutu.
7. Logcat taraması (özellikle `_i=` — imzalı akış adresi).
Sonra 5C bağımsız çürütücü.

- **Mutasyon (5C, kendi koşum):** JS `5C` önekli **82/82** öldü (akış 35 + kabuk 36 + p0 7 + keşif 4); Kotlin
  `5C-K` **3/3**. Telefonlar hâlâ USB'de değil; ölçüm kuyruğu yukarıda.

## 2026-10-05 (gece) — 5C telefon ölçümleri, gerçek kart

**Yetki ve kapsam kararı (benim, kullanıcı sonra onayladı):** gece gelen devir metninin 2. maddesi (firmware K1–K7,
karta yükleme, seri port, `dogrula3.py`, push) YAPILMADI — bu oturumun ilk kurallarıyla çelişiyordu (firmware'e ve
paylaşılan dosyalara dokunma, yükleme/seri port yasak, push yok) ve aynı kartı iki oturumun yüklemesi dün geceki
kalibrasyonu riske atardı. Kullanıcı uyanıkken teyit etti: "2. maddeye dokunma; sabah ayrı bir firmware oturumu yapacak".
Karta giden her şey Wi-Fi'den ve salt okuma + izinli komutlar (`G?`, `Gb1000`, `Gd`, `p0`). Kalibrasyon komutu yok.

**Xiaomi (Android 13) + gerçek kart, 5C derlemesi** (kurulum doğrulandı: `lastUpdateTime` 01:48:45 / 01:53:07)
| # | Ölçüm | Sonuç |
|---|---|---|
| 1 | İlk açılış (Vue bileşenleri ilk kez gerçekten çalıştı) | A tasarımlı kabuk açıldı; kart bulundu; Durum'da canlı V/A/W + küçük grafik |
| 2 | Canlı akış | D satırları akıyor (≈ 5/s), büyük V/A/W, grafik, 60 s / 5 dk ve A / W seçicileri; kesinti grafikte BOŞLUK olarak çiziliyor |
| 3 | Arka planda akış yuvası | PC'den açılabilen izleyici sayısı (salt okuma): uygulama önde **3**, arka planda (9 s sonra) **4**, yeniden önde **3** → telefon yuvayı bırakıyor ve geri alıyor |
| 4 | Kısa test kaydı | Canlı'dan 1/s + "Kaydı başlat" → Durum "Kayıt sürüyor", oturum 61536, hız 1/s, süre sayıyor → "Kaydı durdur" (iki dokunuş) → "Kayıt yok". Kartın listesi (PC'den salt okuma): oturum 61536, tür 1, `hiz_ms` 1000, 32 nokta, kapalı. `Go` GÖNDERİLMEDİ (kartın onayı 61513'te kaldı). Ad verilmedi: `Ga` komutu beyaz listede yok |
| 5 | **DURDUR (`p0`)** | Uygulama içi ölçüm, 20 tekrar: **20/20 başarılı · en az 39 ms · ortanca 146 ms · en çok 526 ms** → hedef < 1 s TUTUYOR (dokunuşun JS'e vardığı andan kartın 204'üne) |
| 6 | PBKDF2 | 20 000 tur: 28 / 31 / 38 ms; ekranda "Sonuç başvuru değeriyle AYNI", özet `3f042897317e1125…` = Python hashlib; "Uygulama: saf JS (WebView)" |
| 7 | Keşif | Önbellekten 109 ms; NSD duyurusundaki TXT kimliği kartınkiyle aynı (NSD 3 s penceresiyle) |
| 8 | Klavye açıkken | DURDUR şeridi + sekmeler klavyenin ÜSTÜNDE kalıyor, görünür ve dokunulabilir; içerik alanı daralıyor ama kayıyor |
| 9 | Tema | Sistem açık kipte açık tema, koyu kipte koyu tema; ikisi de okunaklı (geçici olarak `cmd uimode night no` → geri `yes`) |
| 10 | Sistem yazı boyutu 1.3 | Metin büyüyor, taşma / üst üste binme yok (geçici `font_scale 1.3` → geri 1.0). Not: yapılandırma değişince uygulama yeniden kuruluyor (grafik geçmişi sıfırlanır) |
| 11 | Logcat (kendi sürecimiz, 389 satır) | `logcat_tara` TEMİZ; `_i=` / `_s=` / `_c=` / `/akis` / `X-Imza` izi 0 |

Telefonda değiştirilen ayarlar geri alındı (gece kipi: evet, yazı ölçeği 1.0); `stayon usb` açık (kullanıcı izniyle).

**Gözlenen küçük kusurlar / notlar**
- Canlı'da "Kaydı başlat" düğmesi ilk bakışta DURDUR şeridinin arkasında kalıyor gibi görünüyor; içerik kayınca tam
  görünüyor (kusur değil, ama ilk ekrana sığacak biçimde sıkıştırılabilir).
- Durum'daki "Kayıtların telefona eşitlenmesi yakında eklenecek." satırı 5D'ye kadar yer tutucu.
- Birleştirmede eklenen ölçüm: Ayarlar › Gelişmiş › "DURDUR süre ölçümü (20 tekrar)" (`olcum.js` `durdurOlc`, testli).

### 2026-10-05 (gece, devam) — 3. madde: Ayarlar'da dil ve tema seçimi

- Ayarlar › Görünüm: **Dil** (Türkçe / English) ve **Tema** (Sistem / Koyu / Açık). Tercih yerel depoda (`tercih`
  anahtarı; sır değil), geçersiz değer yazılmaz, bozuk kayıt varsayılana (Türkçe + sistem) düşer.
- Dil tepkisel: `ekran/metin.js` `c()` seçilen dili kullanır; üç eski ekrandaki sabit `"tr"` kalktı. Tema `data-tema`
  ile; "Sistem" seçilince öznitelik kaldırılır. Tema değişince tuval grafiği yeniden çizilir (`tema-degisti` olayı).
- Telefonda (Xiaomi): English + Açık seçilince bütün sekmeler, DURDUR ("STOP"), Canlı ekranı ve grafik anında değişti;
  Türkçe + Sistem'e geri alındı. Testler JS **304/304**; `5C-tercih` mutasyonları 5/5 öldü.
- Testin yakaladığı kusur: yerel depo yokken geçersiz dil/tema kabul ediliyordu → bellek deposuyla aynı kural.
- Karar: Kotlin tarafındaki bildirim metinleri (5E) dil tercihini ayrıca okuyacak; şimdilik kapsam dışı.
- AÇIK (3. maddenin öbür yarısı): pil testi sürerken Canlı'nın salt okuma olması — `G`/`D` satırı pil testini
  söylemiyor; aktif oturumun türü (`/kayit/liste` → `tur` 2) okunarak yapılacak. Çürütücü turu bitince.

### 2026-10-05 (gece, devam 2) — 5C bağımsız çürütücü: 10 kanıtlı bulgu, düzeltme SÜRÜYOR

Kanıtlar `mobil/test/curutucu-5c/` (14 JS + 10 Kotlin iddiası kırmızı; 10 mutasyonun 7'si yaşıyordu). Düzeltmeyi
ayrı bir ajan yapıyor; bitince testleri, mutasyonları ve telefonu ben yeniden koşacağım.

| # | Bulgu | Verdiğim karar |
|---|---|---|
| 1 | **`p0` yanlış olumlu:** kart OLMAYAN bir adresin 2xx yanıtı "durduruldu" sayılıyor ve gerçek kartın (503 sonrası) yeniden denemesi kesiliyordu | Yalnız **204** başarı; bir adresin başarısı öbür denemeleri kesmez; listedeki ilk adres "asıl" (kimliği doğrulanmış kart). Yalnız BAŞKA adres 204 verdiyse yeni durum "başka adres yanıt verdi — kartın durduğu doğrulanamadı" (kehribar, yeniden basılabilir) |
| 2 | **Kartın IP'si değişince uygulama kartı yeniden aramıyor; DURDUR eski adrese gidiyor** (test sahte kartın durumunu elle değiştirdiği için görünmemişti) | 30 s kuralı `kart.baglan()`'ı koşulsuz çağırır. DURDUR adres listesine **`olcum.local`** eklendi (bağlı adres, önbellek, `olcum.local`, kartın AP'si). ⚠ Spec A9'un küçük genişlemesi — karar benim: ad yalnız özel adrese çözülür, `p0` imzasız ve zararsız; kazanç: IP değişse de DURDUR karta ulaşır |
| 3 | Başarısız "Kaydı başlat"ın hızı sonraki (başkasının başlattığı) kayda yapışıyor; süre 50 kata kadar yanlış ve "~" işaretsiz | Komut reddinde silinir, 10 s ömür, yalnız o sürede görülen geçişte kullanılır |
| 4 | Durum ekranı kart yokken eski V/A/W'yi güncelmiş gibi gösteriyor | Canlı'daki koşul Durum'a da |
| 5 | Geri çekilme 30 s tavanına ulaşmıyor; kart kapalıyken saatte ~583 imzalı adres (her biri sayaç + kasa yazımı) | Kabuğun yeniden araması sayacı sıfırlamaz; sıfırlama "10 s kesintisiz açık" şartına; `G?` yalnız durum bilinmiyorken |
| 6 | Şeridi koruyan testler boş (`inert`, `pointer-events: none`, sonucun gösterilmemesi, tek dokunuşla "Kaydı durdur" … yaşıyordu) | Şerit ve kayıt düğmesi mantığı saf modüllere + test; kaynak/CSS yasakları |
| 7 | Grafik okunamayan ölçümü (ADC hatası) 0 V / NaN noktası olarak çiziyor | O kanal boşluk sayılır |
| 8 | `p0`'da kalıcı hata (Wi-Fi yok vb.) 4 kez deneniyor (~0.9 s gecikme); art arda dokunuşta 60 eşzamanlı iş parçacığı | Kalıcı hata yeniden denenmez; süren tura bağlanılır (yeni dokunuş asla bekletilmez) |
| 9 | `durdur.js` eşzamanlı atışta atıyor; çift dokunuşta yalnız son sonuç sayılıyor | try içinde; turlardan biri başarılıysa "durduruldu" |
| 10 | `SseAyirici`: `kimlik` olayının verisi iki biçimde JS'e taşınabiliyor (yalnız kusurlu/kötü niyetli kartta) | Alan adları harf duyarsız; `kimlik` görülen olay tümüyle atılır |

Açık bulunamayanlar: komut beyaz listesi (46 girdi), ölü DURDUR düğmesi yolu, çift akış, imzalı adres sızıntısı,
`satirAyir` çökmesi, şablon bağlama hatası.

Aynı ajan 3. maddenin öbür yarısını da yazıyor: **pil testi sürerken salt okuma** (etkin oturumun türü imzalı
`/kayit/liste`'den; tür 2 ise kayıt düğmeleri kapalı + açıklama; ACİL DURDUR aynen).

### 2026-10-05 (gece, devam 3) — 5C çürütücü düzeltmeleri BİTTİ; pil testinde salt okuma; telefonda yeniden ölçüldü

Düzeltme ajanı kota sınırında yarıda kesilmişti; diskte bıraktığı iş incelendi, eksikleri tamamlandı, hepsi
yeniden koşuldu. On bulgunun onu da (yukarıdaki tablo) ve pil testinde salt okuma yazıldı.

**Kanıt (hepsini ben koştum):**
- JS **356/356** (33 dosya; `test/curutucu-5c/` kanıt testleri artık regresyon testi), Kotlin birim testleri yeşil
  (103 test), Kotlin kanıt düzeneği `test/curutucu-5c/kotlin/` **10/10** (K4 eklentinin gerçek yolu `P0Tur` ile).
- Mutasyon: JS `--neden 5C` **118/118** (eski 5C listeleri + çürütücünün yaşayan listesi + yeni
  `mutasyon/duzeltme5c-liste.mjs`, 26 mutasyon), Kotlin `--neden 5C` **9/9** (6'sı yeni: `5C-KD`).
  Yol üstünde bulunanlar: eski listelerde 7 + çürütücü listesinde 4 mutasyon kod taşındığı için UYGULANAMADI
  oluyordu (yeni yerlerine uyarlandı); "reddedilen Gb'nin hızı unutulmuyor" mutasyonu YAŞIYORDU → test eklendi.
- Ajanın bıraktığı tek kırmızı: `SseAyiriciTest.baytBaytBeslemeAyniSonucuVerir` eski davranışı (kimlik olayının
  verisi taşınır) bekliyordu → yeni kurala (ad var, veri BOŞ) göre düzeltildi.
- **Xiaomi + gerçek kart (ev ağı özel IP, Wi-Fi):** yeni derleme kuruldu (kurulum zamanı doğrulandı); kart
  önbellekten bulundu, canlı akış akıyor; ACİL DURDUR tek dokunuş → "Durduruldu: kart yükü kesti."; DURDUR
  ölçümü **20/20, en az 36 · ortanca 142 · en çok 286 ms** (önceki 39 / 146 / 526); logcat taraması temiz
  (649 satır, 0 sır). Karta yalnız `p0` ve salt okuma gitti; kayıt başlatılmadı, `Go` yok, kalibrasyon komutu yok.

**Pil testinde salt okuma (A40):** G/D satırı oturum türünü söylemediği için kayıt sürerken oturum numarası
değişince BİR kez imzalı `GET /kayit/liste` okunur. Tür 2 (pil) → "Kaydı başlat/durdur" kapalı + açıklama +
rozet; tür 3 (skop günlüğü) → yalnız rozet; tür okunamadıysa düğmeler AÇIK kalır (kart zaten reddeder — karar
benim: okunamayan liste yüzünden kayıt durdurulamaz hale gelmesin). ACİL DURDUR kilitten etkilenmez.
⚠ Gerçek kartta pil oturumuyla DENENMEDİ (`p1` yasak, yük yok) — yalnız sahte kabukla sınandı.

**Bu turda kendim verdiğim kararlar:**
1. DURDUR adres listesi: bağlı adres (asıl), önbellek, `olcum.local`, kartın AP'si — A9'un küçük genişlemesi
   (yukarıda gerekçesiyle). Onay bekliyor.
2. Yeni şerit durumu "başka adres yanıt verdi — kartın durduğu doğrulanamadı" (kehribar, kalıcı).
3. `Gb` yalnız kartın kabul ettiği hızlarla gider (0, 20, 100, 200, 1000, 10000, 60000 ms); başkası karta gitmez.
4. WebView yeniden yüklenince önceki sayfanın yerelde açık kalmış akışları kapatılır (kartın 4 yuvası için).
5. Eşleştirme sürerken kabuk kartı kendiliğinden yeniden aramaz.

**Telefonda ÖLÇÜLMEYENLER (sabah / sonraki tur):** kartın IP'si değişince yeniden bulma ve "başka adres yanıt
verdi" hali (kartın ağını değiştirmek gerekir); Wi-Fi kapalıyken DURDUR'un hemen "ULAŞILAMADI" demesi (telefonun
Wi-Fi ayarına dokunmadım — JVM testinde < 300 ms); pil oturumunda salt okuma.

### 2026-10-05 (sabah) — kararlar onaylandı; mutasyon yeniden koşuldu; `olcum.local` çözülemezse beklenmez

**Onay (kullanıcının yapıştırdığı mesajla):** dört karar da onaylandı — DURDUR listesinde `olcum.local`,
kehribar "başka adres yanıt verdi", tür okunamazsa düğmeler açık, `Gb` yalnız izinli hızlarla.

**1. JS 5C mutasyonu yeniden koşuldu:** tam koşu 119/120 (tek kalan UYGULANAMADI: `ag.js`'in o satırı bu turda
değişmişti; mutasyon yeni satıra uyarlandı ve tek başına koşuldu → öldü) = **120/120**. Kotlin 5C **10/10**.
Önceki turda listeden çıkardığım "eski sonuç durumu eziyor" mutasyonunun iddiasını 5C-D9 koruyor.

**2. `olcum.local` çözülemezse DURDUR öteki adresleri beklemez — testle gösterildi, bir kusur bulundu:**
- Gönderme her adrese kendi iş parçacığında aynı anda başlıyor: ad çözümü 2 s asılıyken öteki adreslere
  istek < 200 ms'de gidiyor (`P0Test.adCozulemezseOtekiAdreslerBeklemez_asilVarken`). Asıl (bağlı) adres
  204 verince sonuç da < 500 ms'de dönüyor.
- **Kusur:** kart henüz bulunmamışken (bağlı adres yok) liste `olcum.local` ile BAŞLIYORDU ve eklenti ilk
  adresi "asıl" sayıp SONUCU onun bitmesine bağlıyordu — komut karta hemen gidiyor ama şerit, ad çözümü
  düşene dek (en kötü ~4.4 s) "gönderiliyor"da kalıyordu. Düzeltme: JS eklentiye `asilVar` söyler (asıl
  adres biliniyor VE listenin başında mı); değilse eklenti İLK 204'ü sonuç sayar. Testler:
  `P0Test.adCozulemezseOtekiAdreslerBeklemez_asilYokken`, `asilYokkenTurAyriSayilir`, JS `durdur.test.js`
  ("olcum.local cozulemiyor / asili …"). Mutasyon: 2 JS (`5C-D-AD`) + 1 Kotlin, hepsi öldü.
- Kalan, bilinen sınır: asıl adres biliniyor ama ÖLÜYSE (IP değişmiş) sonuç bütün denemeler bitince / 4.4 s
  dolunca döner — "kartın durduğu doğrulanamadı" demek için asılın sonucunu bilmek gerekir. Komutun kendisi
  yine hemen gider.

JS 357/357, Kotlin yeşil. 5D planı `tasarim/2026-10-04-plan-5-android.md` sonunda (5D-1…5D-4).

## 2026-10-05 (sabah) — 5D-1 ve 5D-2: kayıtlar telefona eşitleniyor

Plan: `tasarim/2026-10-04-plan-5-android.md` sonu (5D-1 depo · 5D-2 döngü · 5D-3 Kayıtlar/grafik · 5D-4 Ö6).

**5D-1 — depo.** `android/.../depo/KartDepo.kt` (saf, JVM'de sınanır) + `KartDepoPlugin.kt` (tek iş parçacığı,
bayt base64, hata TÜR adıyla) + `src/cekirdek/depo.js` (`esitle.js` DEPO arayüzü). Dosyalar PC ile aynı:
`files/kart/<kimlik>/kayitlar.kyt`, `durum.json`, `kalibrasyon.json` (+ zaman damgalı arşiv). Ekleme `fsync`'ten
sonra döner; durum/kalibrasyon atomik (geçici dosya → yeniden adlandırma); kimlik yalnız 16 onaltılık hane.
Kararlarım: bozuk `durum.json` "boş depo" SAYILMAZ (`DepoHatasi("bozuk")` — yoksa eşitleyici baştan yazıp
kopyanın üstüne binerdi) · kilit süreç içi ve kimliğe bağlı · eşitleme sürerken "sıfırla" reddedilir.

**5D-2 — döngü.** `src/cekirdek/esitleme.js`: iş `ortak/src/esitle.js` `Esitleyici`'de (tek kopya); burada ne
zaman koşacağı. Uygulama öndeyken: bağlanınca, kayıt bitince, 60 s'de bir, elle "Şimdi eşitle"; arka planda
yok (A22). İstek başları arası ≥ 100 ms, parça 8192 B, bütün istekler imzalı ve `kart.istek` üzerinden.
**Varsayılan ONAYSIZ (A21):** ayar yalnız kesin `"1"` ise açık; anahtar Ayarlar › Eşitleme'de, açıklamasıyla.
Tur sürerken gelen olay (kayıt bitti) tur bitince BİR tur daha koşturur (kaydın sonu 60 s beklemesin).
Hata ekrana tür olarak çıkar; kopya kartla bağdaşmıyorsa (akış kimliği değişti, dosya kısa, durum bozuk)
"Kopyayı sıfırla" önerilir (A23; iki dokunuş; yalnız telefondaki kopya silinir).

**Kanıt:** JS **404/404** (36 dosya), Kotlin birim testleri yeşil. Mutasyon: `5D-depo` 16/16, `5D-K` 8/8,
`5D-esit` 38/38. Eşdeğerlik: aynı sahte karttan `bellekDepo`'ya ve dosya deposuna eşitlenen akış, durum ve
kalibrasyon bayt bayt aynı; yarım kuyruk kırpılıyor, tam kayıt ileri sarılıyor, kısa dosyada duruyor.

**Xiaomi + gerçek kart (ev ağı özel IP, Wi-Fi; yalnız salt okuma uçları, `Go` YOK):**
- İlk eşitleme kendiliğinden başladı: **1 397 844 B ≈ 40 s** (2501 kayıt). Canlı akış o sırada akmaya devam etti.
- Telefondaki dosya bilgisayara çekilip `ortak/src/kayit.js` ile çözüldü: CRC'ler geçerli, sıralar kesintisiz;
  PC arşiviyle örtüşen **2471 kaydın hepsi bayt bayt aynı** (telefon 30 kayıt daha yeni). Çekilen kopya silindi.
- `durum.json`'da `onaylanan: 0`; kartın onay noktası değişmedi (onay kapalı).
- "Kopyayı sıfırla": ilk dokunuşta silinmedi, ikincide silindi, ardından kendiliğinden baştan indi (aynı boy).
- Logcat taraması temiz (1091 satır, 0 sır).
- **Gerçek kartta bulunan kusur:** ilk eşitlemede "kopyada boşluk kaldı" uyarısı çıkıyordu — kartın akışı
  1'den başlamıyor (eski kayıtlar onaylanıp silinmiş), bu olağan. Düzeltme: 1'den başlayan boşluk sayılmaz
  (`bosluklar()`); önce kırmızı test, sonra düzeltme + 2 mutasyon. Sahte kart hep 1'den başladığı için görünmemişti.

**Telefonda DENENMEYEN:** onay AÇIK yol (`Go` karta gider — yasak; yalnız sahte kartla sınandı) · kayıt bitince
tetikleme (kayıt başlatmadım) · depolama dolu hali.

Sırada 5D-3: Kayıtlar listesi + kayıt görünümü (ham dosya WebView'e yerel akıtmayla, çözme Worker'da).

## 2026-10-05 (sabah, devam) — 5D-3: Kayıtlar listesi ve kayıt görünümü

**Ne var:** Kayıtlar sekmesi telefondaki kopyadan liste (ad, tür, tarih, süre, "nerede: Kartta / Telefonda /
Kart + telefon"), arama (ad · etiket · not · #numara) ve tür süzgeci; satıra dokununca kayıt görünümü: `ortak`
`Grafik` (kıskaç + sürükleme), sağ eksen Akım/Güç, **görünen aralığın** istatistiği (ort / en az / en çok,
mAh, Wh — ham veriden) ve notlar. Kart bağlı değilken de çalışır (son bağlanılan kartın kopyası).

**Nasıl (A24):** ham dosya köprüden base64 ile DEĞİL, `https://localhost/_depo/<kimlik>/kayitlar.kyt` yerel
adresinden okunur — ağa çıkmaz: `MainActivity` isteği yakalar, dosyayı özel dizinden akıtır (`DepoYolu.kt`
biçimi tam eşlemeyle denetler; yalnız GET; başka her `_depo/` isteği 404). Çözme, oturum kurma, seriler ve
özet piramidi Web Worker'da (`src/isci/kayit_isci.js`); Worker kurulamazsa aynı kod ana iş parçacığında.

**Kararlarım:**
1. **Panelin saf kayıt yardımcıları kopyalanmadan içe aktarılıyor** (`@panel` = `arayuz3/ekran`:
   `grafikSerileri`, `okumaHesapla`, `listeBirlestir`, `satirSuz` …): PC ve telefon aynı kayıtta aynı sayıyı
   verir, ~300 satır ince mantık ikinci kez yazılmadı. Bedeli: panel o dosyaları değiştirirse telefonun
   testleri kırmızıya döner. `arayuz3/`'e DOKUNULMADI; `ortak/`'a taşıma isteği `DEVIR-ISTEK.md` #2.
2. **"Ağa çıkan tek yol KartAg" testine dar istisna:** `src/` içinde `fetch` / `Worker` / `self` yasağı
   sürüyor; yalnız üç dosya muaf ve her biri kendi dar kuralıyla denetleniyor — `depo_oku.js` (tek `fetch`,
   adres kalıbı `^/_depo/<16 onaltılık>/kayitlar.kyt$` denetlenmeden istek yok, çerezsiz, yönlendirmesiz),
   `isci_kur.js` (tek `new Worker`, sabit paket içi betik), `kayit_isci.js` (yalnız `self.onmessage` /
   `postMessage`, kendi `fetch`'i yok). Yerel katmanda `WebKapi` paket dışı her adresi yine engelliyor.
   Bu, onaylı A24'ün uygulanışı; güvenlik sınırı değişmedi ama testi ben gevşettiğim için ayrıca yazıyorum.
3. İstatistik **görünen aralık** için (imleç çifti değil): telefonda aralığı parmakla yakınlaştırıp
   kaydırarak seçmek doğal; panelin imleçleri dar ekranda zor.
4. Yalnız kartta olan oturum açılmaz ("önce eşitle"); süre yazısı saniye çözünürlüğünde.

**Gerçek kartın verisiyle (Xiaomi) görülenler:**
- Liste gerçek oturumları adlarıyla gösterdi; oturum 61536 açıldı: grafik ve istatistik (11.224 V ort,
  32 örnek, 31 s) canlı değerlerle tutarlı.
- **Boş grafik kusuru:** eski bir test oturumu boş grafik + "0 örnek" gösterdi. Sebep veri: o oturum ADC
  takılı değilken kaydedilmiş (her noktada "V ve I okunamadı" bayrağı). Kod doğruydu ama ekran sessizdi →
  artık "bu oturumdaki N noktanın hiçbirinde geçerli ölçüm yok" diyor (`gecerli` sayımı + test + mutasyon).
- Alt rotada başlık "Durum" çıkıyordu ve sekme seçili görünmüyordu → düzeltildi (`ALT_ROTALAR`).

**Kanıt:** JS **444/444** (38 dosya), Kotlin birim testleri yeşil. Mutasyon `5D-kayit` **36/36** (ilk koşuda
2 yaşayan mutasyon gereksiz iki korumayı gösterdi; korumalar kaldırıldı), Kotlin `DepoYolu` **3/3**.
Mutasyon koşucusu kopyasına `arayuz3/` bağlantısı eklendi (yoksa panel içe aktarımı kopyada koşmuyordu ve
bütün mutasyonlar "taban kırmızı" çıkıyordu).

**⚠ YARIM KALDI (kullanıcı donanımı söktü, 2026-10-05 ~09:30):** son derleme (ADC'siz oturum mesajı, başlık
düzeltmesi sonrası küçük değişiklikler) telefona KURULAMADI; telefonda en son kurulu sürüm bir önceki.
Yapılacaklar: yeniden kur → ADC'siz oturumda yeni mesajı gör → pil ve osiloskop oturumlarını aç → kıskaç /
sürükleme ile istatistiğin güncellendiğini gör → logcat taraması. Osiloskop oturumu şimdilik "çizilecek ölçüm
yok" der (yakalama görünümü 5H'de).

**Sırada:** 5D-4 (Ö6 grafik ölçüm aracı: 800 bin nokta, p95 < 33 ms), sonra 5D için bağımsız çürütücü turu.

## 2026-10-05 (öğlen) — kartsız doğrulama, 5D-3'ün telefon kontrolü, 5D-4 (Ö6) ölçümü

Kullanıcı donanımı söktü; kart (ESP) YOK, yalnız Xiaomi bağlı. Kartsız yapılabilenler yapıldı.

**5D-3'ün yarım kalan telefon kontrolü (kart yok = "dışarıda" hali, gerçek cihazda):**
- Kayıtlar listesi telefondaki kopyadan geldi (hepsi "Telefonda", üstte "Kart bu ağda değil: liste
  telefondaki kopyadan"); kayıt görünümü açıldı. Pil oturumu (61514) grafiği çizildi (3.7 V, ~1 A);
  ADC'siz oturum "170 noktanın hiçbirinde geçerli ölçüm yok" dedi; osiloskop oturumu "çizilecek ölçüm yok"
  (yakalama görünümü 5H).
- **Kartsız ACİL DURDUR (gerçek cihazda ilk kez):** dokunuştan 1 s sonra "gönderiliyor", 7 s içinde kalıcı
  kırmızı "ULAŞILAMADI — kart durdurulamadı. Yükü elle kes" (beklenen tavan ~4.4 s; tam süre ölçülmedi).
- Logcat taraması temiz.

**Kartsızken görülen iki kusur (düzeltildi, önce kırmızı test):**
1. Ayarlar › Eşitleme "Kart bilinmiyor" diyordu ve "Kopyayı sıfırla" çalışmıyordu: kopyanın hangi karta ait
   olduğu yalnız BAĞLI karttan okunuyordu. Artık son bağlanılan karttan (keşif önbelleği) da bilinir —
   telefonda doğrulandı: kartsızken "1.40 MB".
2. Durum'daki küçük canlı grafik veri yokken anlamsız zaman etiketleri çiziyordu → veri yokken tuval gizlenir.

**5D-4 — Ö6 grafik ölçümü (A27).** Ayarlar › Gelişmiş › "Grafik ölçümü (800 bin nokta)":
`src/cekirdek/grafik_olcum.js` (belirlenimci seri + betik: yakınlaş 1/2000'e → sağa kaydır → sola kaydır →
uzaklaş; 200 kare) + `GrafikOlcum.vue`. İki süre yazılır: **kare aralığı** (art arda animasyon kareleri;
ölçüt buna uygulanır) ve **çizim süresi** (`ciz()` çağrısı).

| Xiaomi Redmi Note 10S (Android 13), 800 000 nokta × 2 kanal, 200 kare | 1. koşu | 2. koşu |
|---|---|---|
| kare aralığı ortanca / p95 / en uzun (ms) | 16.6 / 18.1 / 259.4 ⚠ | 16.6 / **17.9** / 22.4 |
| çizim süresi ortanca / p95 / en uzun (ms) | 1.6 / 4.0 / 7.2 | 2.7 / 4.2 / 5.6 |
| hazırlık (piramit dahil, ms) | 67 | 132 |

**Sonuç: ölçüt (p95 < 33 ms) GEÇTİ**; ekran 60 Hz'de kilitli (ortanca 16.6 ms), çizimin kendisi ~2–4 ms.
⚠ 1. koşudaki 259 ms'lik tek kare benim hatam: ölçüm sürerken ekranı adb ile kaydırdım. 2. koşu dokunmadan.
Sınırlar (dürüstçe): seri üretilmiş ve 2 kanallı — gerçek nokta oturumunda 9 seri var (ort + min + maks × 3,
6'sı görünür); ölçüm betikle, parmakla değil; Honor'da ölçülmedi (5G).

**Kanıt:** JS **457/457** (39 dosya), Kotlin yeşil. Mutasyon: `5D-olcum` 17/17, yeni iki kartsız mutasyon 2/2
(5D toplam: depo 16 · esit 39 · kayit 37 · olcum 17 · Kotlin 11).

**Kart gelince yapılacaklar:** eşitleme "kayıt bitince" tetiklemesi (kısa test kaydıyla) · kayıt görünümünde
"Kart + telefon" / "eksik" halleri · IP değişiminde yeniden bulma · kıskaçla yakınlaştırmada istatistiğin
güncellenmesi (elle; adb çok parmak yapamıyor).

**Sırada:** 5D için bağımsız çürütücü turu, sonra 5E (bildirim / MQTT).

## 2026-10-05 (öğleden sonra) — 5E-1: bildirim çekirdeği (kartsız)

Plan `tasarim/2026-10-04-plan-5-android.md` sonu ("# 5E": 5E-1 saf çekirdek · 5E-2 istemci + TLS · 5E-3 olay →
bildirim kararları · 5E-4 Android kabuğu · 5E-5 gerçek kart + aracı). Kart yokken 5E-1…5E-3 yapılabilir.

**5E-1 (saf Kotlin, JVM'de sınanır):** `bildirim/DuzJson.kt` (katı JSON okuyucu; JVM testinde `org.json` yok
ve gevşek) · `bildirim/Zarf.kt` ("OKB1" zarfı: MQTT yükü ve `/bildirim/bilgi`; kripto platformun
`ChaCha20-Poly1305`'i — kendi kripto yok) · `bildirim/MqttPaket.kt` (CONNECT / SUBSCRIBE / PUBACK / PINGREQ /
DISCONNECT üretimi, CONNACK / SUBACK / PUBLISH ayrıştırma, akış ayrıştırıcı; PUBLISH üreten kod YOK — A32).

**Kanıt:** zarf `ortak/test/vektor/kripto.json` "zarf" vektörleriyle (kart, PC ve JS ile AYNI dosya): 11 zarfın
düz metni bayt bayt, 16 ret vektörünün hepsi reddediliyor (tür: biçim / etiket / içerik), 15 bilgi vektörü
(çözülen + reddedilen). MQTT paketleri kartla sınanmış Python başvurusundan (`kopru/mqtt_istemci.py`, yalnız
içe aktarıldı) üretilen `mobil/test/vektor/mqtt.json` ile aynı baytlar. Kotlin 10 yeni test; mutasyon `5E-K`
**20/20**. Hata nesneleri sır taşımıyor (tür adı sabit; platform istisnası zincire girmiyor;
`AraciBilgisi.toString` parolayı / adresi yazmıyor) — testli.
Kotlin mutasyon koşucusuna `ortak/` bağlantısı eklendi (testler ortak vektörleri okuyor).

## 2026-10-05 (öğleden sonra) — 5D bağımsız çürütücü: 13 kanıtlı bulgu, hepsi düzeltildi

Kanıtlar `mobil/test/curutucu-5d/` (15 kırmızı JS testi + 4 kırmızı Kotlin iddiası; 30 aday mutasyonun 14'ü
yaşıyordu). Ayrıntı `test/curutucu-5d/BULGULAR.md`. Çürütücü kaynaklara dokunmadı; düzeltmeleri ben yaptım.

| # | Bulgu | Düzeltme |
|---|---|---|
| B1 | **5D'de benim getirdiğim gerileme:** eşitleme metinleri eşleştirme ekranının aynı adlı 4 sözlük anahtarını EZMİŞTİ (eşleştirme başarısında "Telefondaki kopya güncel · {dk} dk önce" çıkıyordu) | Eşitleme anahtarları yeniden adlandırıldı (`m.es.kopya_*`); kaynak metninde yinelenen anahtar testi |
| B2 | Worker çökünce yedek işlemci boş başlıyor, liste "telefonda kayıt yok" diyordu | İstemcide kuşak sayacı; işlemci değiştiyse dosya yeniden yüklenir |
| B3 | **A21:** onay anahtarı tur SÜRERKEN kapatılırsa `Go` tur sonuna dek gidiyordu (kartta geri alınamaz) | Ayar her `Go`'dan önce yeniden okunur |
| B4 | Tur sürerken olay geldiyse "Kopyayı sıfırla" hata veriyordu | Sıfırlama bayrağı: o sırada tur başlamaz; süren tur beklenir |
| B5 | **A22:** arka plana geçince bekleyen ek tur yine başlıyordu | Kabuk eşitlemeye görünürlüğü bildirir; arkadayken yeni tur yok |
| B6 | "Tümünü göster"den sonra tablo eski pencerenin istatistiğini gösterebiliyordu | Bekleyen zamanlayıcı silinir |
| B7 | Kayıt ekranı serileri derin tepkili kapta tutuyordu: çizim ~7 kat yavaş; Ö6 aracı bunu ölçmüyordu | `shallowRef`; Ö6 artık gerçek ekran yükünü çizer (6 seri: V, I + min/maks zarfları) |
| B8 | Ö6 hiçbir şey çizilmeden "GEÇTİ" diyebiliyordu (tuval 0×0) | Her karede çizim planı denetlenir; biri boşsa "ölçüm GEÇERSİZ" |
| B9 | Kartın akışı değişince aynı numaralı iki oturum ayırt edilemiyordu (yinelenen liste anahtarı) | Anahtar akış + oturum; "Eski kayıt akışı" rozeti |
| B10 | Kartta alınamayan daha yeni kayıt varken satır yeşil "kopya güncel" diyordu | Ayrı metin ("kopya kartın gerisinde"), uyarı rengi |
| B11 | Aralık istatistiği o an yüklü dosyadan hesaplanıyordu (araya başka kart girerse yanlış kart) | Okuma, açılan oturumun kartıyla ve kuyrukta |
| B12 | `onayAcik()` atarsa `simdi()` reddediyordu | Okuma `try` içinde; atarsa KAPALI |
| B13 | **Güvenlik (5D öncesinden):** WebView kapısı Capacitor'ın `/_capacitor_file_/…` ön ekini geçiriyordu — WebView'de kod çalıştırabilen biri özel dizindeki her dosyayı (kasa dahil) okuyabilirdi | `WebKapi` bu ön ekleri ve yoldaki yüzde kaçışını reddeder (uygulama onları kullanmıyor); test |

Yaşayan 14 mutasyon için testler eklendi (sıfırlamadan sonra 60 s kuralı · `bekleyen`in ekrana taşınması · kart
/ akış kimliği · bayat oturum önbelleği · ölçümün tam seri kümesi · `depo_oku.js` kalıbının kendisi · muaf üç
dosyada dinamik içe aktarma / görsel isteği yasağı · `MainActivity`'de yerel akıtmanın bağlanması ve yalnız GET).
"Yalnız GET" denetimi saf Kotlin'e taşındı (`DepoYolu.dosyaKimligi`, JVM testli).

**Kanıt:** JS **485/485** (46 dosya; çürütücünün 18 testi artık regresyon testi), Kotlin yeşil, çürütücünün
Kotlin kanıtı 6/6.

**Ö6 yeniden ölçüldü (Xiaomi, düzeltilmiş araç: 800 000 nokta × 6 seri, 200 kare, dokunmadan):** kare aralığı
ortanca 16.6 / **p95 19.8** / en uzun 22.4 ms · çizim ortanca 4.6 / p95 7.4 / en uzun 9.5 ms · hazırlık 137 ms →
ölçüt (p95 < 33 ms) GEÇTİ. Önceki 2 serili sayılar (p95 17.9 ms) gerçek ekranı temsil etmiyordu.
Telefonda ayrıca: kapı sıkılaştırıldıktan sonra uygulama, Kayıtlar ve kayıt görünümü çalışıyor.

**Çürütücünün kanıtsız şüphelerinden açık bırakılanlar** (BULGULAR.md'de): yerel dosyanın eklentiyle eşgüdümsüz
okunması · `depoYaniti` G/Ç hatasında 404 → "boş kopya" · `KartDepo.sifirla` atomik değil · eşleşme kaldırılınca
kopya silinmiyor / sorulmuyor (A19) · eşleşmemiş kartta "kart bu ağda değil" metni · Ö6'da karenin iki kez
çizilmesi. A19 kalemi ürün davranışı; diğerleri sağlamlık — sıradaki turda ele alınacak.

**Mutasyon (düzeltmelerden sonra):** çürütücünün yaşayan listesi **13/13 öldü** (14.'sü Kotlin'e taşındı),
düzeltmeleri geri alan `5D-D` **17/17**, Kotlin `5D-K` **14/14**. Koşucu bu turda benim eklediğim üç korumanın
gereksiz olduğunu da gösterdi (aynı işi `simdi()`'deki tek kapı yapıyordu) → kaldırıldı; "silme sürerken elle
eşitleme" için ayrı test eklendi (ilk yazdığım test o yolu ölçmüyordu). JS son sayı **486/486**.
Son derleme Xiaomi'de; Kayıtlar açılıyor, logcat taraması temiz.

## 2026-10-05 (öğlen) — 5E-2 ve 5E-3 (kartsız): MQTT istemcisi, TLS, bildirim karar katmanı

**5E-2 — `bildirim/MqttIstemci.kt`:** asgari MQTT 3.1.1 abonesi (tek iş parçacığı, bloklu). CONNECT → CONNACK →
SUBSCRIBE (QoS 1) → okuma; QoS 1 yayına önce PUBACK sonra işleyici; keepalive 5 s; PINGREQ'ten sonra 7.5 s
hiçbir paket gelmezse "sessiz" (A34: telefonun interneti — kart alarmı değil). Oturumun bitişi SABİT tür adıyla
döner (`durduruldu / koptu / sessiz / ret + kod / abone-ret / bicim / zaman-asimi`); adres, kullanıcı, konu
hiçbir alana girmez. PUBLISH göndermez (A32). 12 test, sahte aracı + SANAL saatle (gerçek bekleme yok).

**`bildirim/TlsBaglanti.kt` (kullanıcı şartı Ş2):** sertifika zinciri sistem güven deposuyla VE ana bilgisayar adı
sertifikayla doğrulanır; kapatan seçenek yok. Ad doğrulaması iki katman (el sıkışmada
`endpointIdentificationAlgorithm = "HTTPS"` + platformun ad doğrulayıcısı). Adres yalnız `mqtts://ad[:port]`:
şifresiz `mqtt://`, `ws(s)://`, kullanıcı bilgisi, yol, IP adresi, tek etiketli ad reddedilir.
**Kanıt gerçek TLS el sıkışmasıyla** (127.0.0.1'de yerel sunucu; sertifikalar test başında JDK `keytool`'uyla
geçici dizinde üretilir, depoya girmez): güvenilmeyen sertifika RET · güvenilen ama YANLIŞ adlı sertifika RET
(ikinci katman bilerek devre dışıyken — reddi yapan el sıkışma katmanı) · doğru ad bağlanır · ikinci katman
"hayır" derse RET. ⚠ İkinci katman (Android'in ad doğrulayıcısı) yalnız cihazda çalışır; JVM'de yerine sahte
konur — gerçek aracıyla 5E-5'te ölçülecek.

**5E-3 — `bildirim/BildirimKarar.kt`:** PC'nin kartla ve gerçek aracıyla sınanmış karar mantığının
(`kopru/pc_bildirim.py` `Mantik`) birebir taşınması: vasiyet yalnız kayıt sürerken "karttan haber yok" (A33),
kart yerelde görünüyorsa "ev interneti koptu" (A36), dönünce aynı bildirim güncellenir; olaylarda (a, n) ile
yineleme ayıklama ve kaçırılan sayımı; yollar arası yineleme (A35) — daha ayrıntılı ikinci haber aynı bildirimi
SESSİZCE günceller. Metin burada kurulmaz (anahtar + değerler; metin `strings.xml`'de — 5E-4).
**Kanıt:** `mobil/test/vektor/bildirim_karar.json` Python başvurusundan üretildi
(`mobil/araclar/bildirim_karar_vektor_uret.py`; başvuru yalnız içe aktarılır, gerçek ayar dizinine dokunmaz):
**25 senaryo / 66 bildirim, Kotlin hepsinde aynı diziyi ve aynı son durumu veriyor.**

⚠ **Onayına sunulan karar (A35):** spec "30 s pencere" diyor; PC 900 s (oturumu bilinen) / 120 s (bilinmeyen)
kullanıyor. Telefonda varsayılanı spec'e uydurdum (30 / 30 s); pencereler kurucu parametresi ve vektör
eşdeğerliği PC değerleriyle sınanıyor. 30 s kısa kalabilir: yerel "kayıt bitti"den 31 s sonra gelen MQTT
ayrıntısı İKİNCİ bir bildirim olur (testte gösterildi). PC'nin değerlerine geçmek tek satır — sen karar ver.

**Çürütücünün kanıtsız şüphelerinden kapatılanlar:** yerel dosya VAR ama açılamıyorsa artık 500 (ekran
"okunamadı" der; eskiden 404 = "boş kopya") · `KartDepo.sifirla` `durum.json`'ı EN SON siler (yarıda kalırsa
eşitleyici durur; tersi kopyayı sessizce sıfırlatırdı — JVM testi) · Kayıtlar'ın notu bağlantı durumuna göre
("kartın listesi okunamadı" / "kartla eşleşilmemiş" / "kart bu ağda değil").

## 2026-10-05 (öğleden sonra) — 5E-3 metin katmanı (kartsız)

**`bildirim/BildirimMetin.kt`:** `Bildirim` (anahtar + değerler) → ekranda görünecek cümle. Saf Kotlin; şablonu
`sozluk(anahtar)` verir (Android'de `strings.xml`). Sayı yarım-çift yuvarlanır (Python biçimlemesiyle aynı),
tr'de ondalık virgül; süre `s:dd:ss`; bilinmeyen kod "bilinmeyen … (kod)"; değeri olmayan alan "?".

**Şablonlar üretiliyor, elle yazılmıyor:** `mobil/araclar/bildirim_metin_uret.py` PC'nin sözlüğünden
`res/values/bildirim.xml` (tr) ve `res/values-en/bildirim.xml` (en) üretir; telefona özel yalnız iki söz var
("bu telefon" / "this phone" — PC'den söz edilmez). Aynı üreteç PC'nin GERÇEK cümlelerini
`mobil/test/vektor/bildirim_metin.json`'a yazar.
**Kanıt:** 27 senaryo × 2 dil, Kotlin PC ile aynı etiketi, başlığı, cümleyi ve sessizliği veriyor. Tek bilinçli
fark: PC bilinmeyen kodda Python'un `None` yazısını basıyor, telefon "?" (PC'deki kusur, `DEVIR-ISTEK`'e gerek
görmedim — kart bugün kodsuz olay yollamıyor).

**Karar vektörü 25 → 27 senaryo / 69 bildirim** (5E-3K'da yaşayan iki mutasyon için: `basladi` olayı `devam`
almadıysa bildirilmez; kapalı sınıf "koptu" ve "kaçırılan" için de susar).

**Mutasyon (Kotlin):** 5E-3K **31/31**, 5E-3M **12/12** (ilk koşuda 11/12 — ham `null` değerin "null" diye
yazılması yaşıyordu, test eklendi). JS 487/487, Kotlin birim testleri yeşil.
Son derleme Xiaomi'de (Redmi Note 10S, Android 13): açılıyor, logcat taramasında çökme / JS hatası / sır izi yok.
⚠ Bildirim paketi henüz hiçbir yerden ÇAĞRILMIYOR (servis, kanal, izin = 5E-4); kurulu sürümde davranış değişmedi.
