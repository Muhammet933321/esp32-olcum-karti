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
