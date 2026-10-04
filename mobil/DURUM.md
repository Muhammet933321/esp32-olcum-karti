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
