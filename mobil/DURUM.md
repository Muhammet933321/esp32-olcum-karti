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
