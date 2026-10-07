# 5P — Panel telefonda (Android'i PC uygulaması seviyesine getirme)

**Durum:** ONAYLI (2026-10-07). Kullanıcı: *"Android uygulama tarafını da bilgisayar uygulaması seviyesine
getir. Orada ne yapabiliyorsak aynıları olmalı."* Kullanıcının verdiği kararlar: Android işini bu oturum
devralır (öbür oturum durur) · **yaklaşım A** (panel uygulamaya gömülür) · Bölüm 1 mimarisi. Geri kalan
kararları kullanıcı devretti (*"ipler sende, gerekli şekilde hallet"*) — aşağıdaki K tablosu, her biri
gerekçe ve "yanlışsa maliyeti" ile.

Üst tasarım: `2026-10-04-alt-proje-5-android.md` (A1–A48). Bu belge onun §10-7 "5H"sini (osiloskop, pil
testi, karşılaştırma, zamanlanmış kayıt, düzenleme, kalibrasyon) ve PC'de olup telefonda olmayan her şeyi
TEK hamlede kapatır; A-kurallarından değişenler §6'da.

## 1. Amaç ve başarı ölçütü

PC uygulamasında (köprü + `arayuz3/` paneli) kullanıcının yapabildiği her iş telefonda da yapılabilir.
Ölçüt: panelin yedi görünümü (Canlı, Osiloskop, Pil testi, Kayıtlar, Karşılaştırma, Ayarlar, Konsol) ve
Ayarlar'ın bütün bölümleri telefonda GERÇEK kartla çalışır; telefona özel olanlar (bildirim, ACİL DURDUR,
kart bulma/hotspot, paylaşma, telefon kopyası) kaybolmaz.

**Kapsam dışı (değişmedi):** kartı telefona USB ile bağlamak · ev dışından canlı veri / komut · birden
fazla kart · iOS / Play Store · PC köprüsüne özgü işler (bildirim alanı simgesi, Windows'la başlama,
köprünün LAN salt-okuma kipi, köprü skop `.satir` arşivi).

## 2. Mimari

```
APK
 ├─ panel.html  (derlemede arayuz3/index.html'den ÜRETİLİR — şablon önceden derlenmiş, satır içi betik yok)
 ├─ arayuz3/app.js + ekran/*.js + ortak/src/*  (PC paneliyle AYNI kaynak, vite paketler)
 ├─ mobil/src/ortam/*   "telefon ortamı": globalThis.__olcumOrtam  ← panel bunu görürse telefon kipine geçer
 │     tasiyici (akış + komut) · istek (imzalı) · p0 · depo (telefon kopyası) · dosya (Paylaş) · yazdır
 │     · esitle (Android eşitleyicisi) · ayarBolumu ("Bu telefon" bileşeni)
 └─ Kotlin eklentileri (DEĞİŞMEZ ya da küçük ek): KartAg, Kasa, KartDepo, Kesif, Paylas, Bildirim + YENİ Yazdir
```

Panel tek bir kancaya bakar: `globalThis.__olcumOrtam`. Kanca yoksa (PC, kart, köprü) panel bugünküyle
**bayt bayt aynı yoldan** gider — PC zinciri (B7, tarayıcı testleri) bunu korur.

## 3. Kararlar

| # | Karar | Gerekçe | Yanlışsa maliyeti |
|---|---|---|---|
| K1 | CSP GEVŞEMEZ (`script-src 'self'`, `unsafe-eval` / `unsafe-inline` betik YOK). Panelin kök şablonu (`#uyg`) ve bütün `template:` dizgileri derlemede `@vue/compiler-dom` ile render işlevine çevrilir; çalışma anında Vue'nun derleyicisiz sürümü (npm `vue` 3.5.x runtime) kullanılır | A47'nin güvencesi (yalnız paketteki kod çalışır) aynen kalır; `new Function` hiç yok. Ek kazanç: açılış hızlı | Derleme dönüşümü yanlışsa bir ekran açılmaz → başsız tarayıcı açılış testi + cihaz kabulü yakalar |
| K2 | Satır içi `<script>` blokları (tema ön boyama, açılış bekçisi) ve `onclick`/`onerror` öznitelikleri `panel.html` üretilirken ayrı paket dosyalarına taşınır; PC `index.html` DEĞİŞMEZ | Kart her ek dosya isteğinde ölçümü blokluyor (B27 A2) — PC'de birleşik kalmalı | Tema kuralı iki yerde → `tema.js` B7 karşılaştırması zaten var; mobil testi aynı karşılaştırmayı panel.html betiğine de yapar |
| K3 | `inline style="…"` öznitelikleri kalır (`style-src 'unsafe-inline'` bugün de açık) | Stil enjeksiyonu kod çalıştırmaz; 47 yeri taşımak kazançsız risk | Yok denecek kadar az |
| K4 | Vue sürümü: telefonda npm 3.5.43 (runtime), PC'de vendor 3.5.13 (tam). Aynı ana/ara sürüm | npm sürümü zaten bağımlılık; yama farkı | Bir davranış farkı çıkarsa vendor sürümü npm'e sabitlenir |
| K5 | Kökenin `localhost` olması: telefon kipinde `kopruyuAlgila`, `kokenSinama`, `kopruKokeni`, `swKur` köprü dalına GİRMEZ (önce ortam denetlenir) | `https://localhost` köprü sanılıyordu: `/durum` yoklaması, servis işçisi | Gözden kaçan bir dal → telefon kipinde `/durum` isteği; testte "WebView ağ isteği" sayacı 0 olmalı |
| K6 | Yeni taşıyıcı `telefon` (`TASIYICILAR`'a ortam verirse eklenir, otomatik seçilir, seçici menüde görünmez). `yetenek`: `{ad:'telefon', komut:'hepsi', skop:'ikili', skop_azami:4000, gecmis_s:86400, cok_istemci:false, surucu:false}`. Akış: Android imzalı akışı (Kotlin `Akis`), her `data` satırı `uyg.satirIsle`'ye. Komut: imzalı `POST /komut` (`X-Olcum: 1`), yanıt satırları `satirIsle`'ye | Panelin taşıyıcı sözleşmesi tam bunun için var; kartın `/akis`'i tek istemci (dolu) → `cok_istemci:false` | — |
| K7 | Kart isteklerinin TAMAMI (`kartIstek`, `/pil`, `/kal/liste`, `/kunye.json`, `/kayit/*`, `/skop.bin`, `/cihaz/*`, `/saat`, `/eslestir/*`) telefon kipinde ortamın `istek`'inden (Android `kart.istek`: imzalı, yalnız özel/yerel adres, kimliği doğrulanmış kart) geçer. `kartTaban` boş kalır. Panelin tarayıcı eşleştirmesi (K'nin IndexedDB'de açık durduğu yol) telefon kipinde KAPALI; anahtar Keystore'da kalır | A2/A14 güvenceleri; tek anahtar deposu | — |
| K8 | `p0` telefon kipinde Android'in P0 kanalına (ayrı iş parçacığı, 4 adres) gider; tek dokunuş, onaysız (B7 kuralı korunur) | A8–A11 ölçülmüş yol (20/20, en kötü 526 ms) | — |
| K9 | ACİL DURDUR şeridi: panelin şeridi kullanılır; telefon kipinde görünürlük kuralı kullanıcının 2026-10-05 kararı — **yalnız pil testinin SÜRMEDİĞİ KESİNSE gizli**, şüphede görünür | Kullanıcı kararı, Android'de ölçüldü | — |
| K10 | Kayıtlar: panelin `EsitlemeDenetcisi`'ne üçüncü kaynak `telefon`: depo = Android `depoKur(KartDepo, kimlik)` (aynı DEPO sözleşmesi). Eşitlemeyi Android eşitleyicisi yürütür (bağlanınca, kayıt bitince, 60 s, yalnız ön planda — A22); panelin "Eşitle" düğmesi ortamın `esitle`'sini tetikler. "Bu telefon da onaylar" ayarı (varsayılan KAPALI) aynen | Tek eşitleyici, tek kopya; PC'deki `pc` kaynağının telefon karşılığı | — |
| K11 | Dosya üretimi (6 yer: pil CSV ×2, canlı CSV, kayıt dışa aktarma, karşılaştırma CSV) panelde tek yardımcıya `dosyaVer(ad, mime, bayt)` toplanır: tarayıcıda bugünkü Blob + `a.download`, telefonda Android **Paylaş** penceresi. Paylaş dosya adı deseni `html` ve `pdf` ile genişler | 6 kopyalı kod tek yere; telefonda `a.download` çalışmaz | — |
| K12 | Rapor "Yazdır" telefonda Android yazdırma penceresi (yeni küçük Kotlin eklentisi `Yazdir`: `WebView.createPrintDocumentAdapter`) — "PDF olarak kaydet" de buradan | `window.print()` Android WebView'da hiçbir şey yapmaz | — |
| K13 | Ayarlar'a **"Bu telefon"** bölümü (yalnız telefon kipinde): Kart (bul · adres · hotspot · eşleş / kaldır), Eşitleme, Bildirimler (izni, anlık izleme, olay sınıfları, pil yöneticisi yönergeleri, deneme), Gelişmiş (keşif tanısı, DURDUR ölçümü, PBKDF2 ölçümü, sürümler). Bileşen `mobil/`'de yaşar (panel kaynağı büyümez), PC'deki "Bildirimler (bu bilgisayar)" gibi dinamik bağlanır. Ionic bileşenleri KALKAR — düz HTML + panel sınıfları | Tek görsel dil; Ionic'i panelin uygulamasına takmak gereksiz yük | — |
| K14 | Telefon kipinde panelin "Bağlantı" bölümündeki taşıyıcı seçici ve adres alanı gizlenir (bağlantı Bu telefon → Kart'ta); Eşleştirme bölümü: telefonun eşleştirmesi Bu telefon'da, **eşleşmiş cihaz listesi + silme + kart saati** panelinkinden (istekler K7 yoluyla imzalı) | İki eşleştirme yüzü kafa karıştırır; cihaz listesi PC'de olan bir iş | — |
| K15 | Eski Android ekranları (Durum, Canlı, Kayıtlar, Kayıt, sekmeler, yönlendirici, Ionic kabuk) SİLİNİR; çekirdek modüller (kart, kasa, ag, kesif, depo, esitleme, bildirim, durdur, paylas, pil_durum) kalır. Silinen ekranların testleri ve mutasyon girdileri temizlenir (`desen-denetle` 0 eskimiş) | Tek arayüz | Eski ekranda olup panelde olmayan küçük bir şey kaybolabilir → §4'te tek tek eşlendi |
| K16 | Komut yetkisi PC paneliyle AYNI (kalibrasyon, ağ, fabrika ayarı, `Ns` dahil; panelin iki adımlı onayları). `E…`/`Q…`'yu kart Wi-Fi'den zaten reddeder | Kullanıcı "aynısı" dedi; yetkiyi kart verir | Wi-Fi parolası HTTP'de açık gider — panelin bugünkü uyarısı telefonda da görünür |
| K17 | Arka plan: Android eşitleyicisi ve bildirim izleyicisi uygulama açılışında (panelden bağımsız) kurulur; canlı akış arka planda kapanır, dönüşte yeniden açılır (bugünkü A22 davranışı) | Pil ve kartın tek-istemci akışı | — |
| K18 | Panel değişiklikleri `arayuz3/` + `ortak/` dosyalarına girer (paylaşılan kaynak) → `main`'e almadan önce TAM `dogrula3.py` + B7 yeşil; panelin PC davranışı değişmez | Proje kuralı | — |
| K19 | Dar/dokunmatik ekran: panelin 900 px altı çekmece düzeni temel; telefonda ölçülen sorunlar düzeltilir (dokunma hedefi ≥ 40 px, yatay taşma yok, osiloskop/grafik dokunmayla kaydırma/yakınlaştırma çalışır) | Panel telefon tarayıcısında denenmişti (5.12.106) | — |

## 4. Eski Android ekranlarının panelde karşılığı (K15)

| Eski Android | Panelde |
|---|---|
| Durum: bağlantı satırı, son görülme | Üst rozet + kart-yok uyarısı ("N sn önce") |
| Durum: kayıt kartı, bellek %, eşitlenmemiş %, mini grafik | Canlı → etkin kayıt kartı + sol şerit eşitlenmemiş sayısı |
| Canlı: V/A/W, grafik, kayıt hızı, başlat/durdur, "anlık izleme" sorusu | Canlı (fazlasıyla); "anlık izleme" sorusu ortamın kayıt-başladı kancasıyla korunur |
| Kayıtlar + Kayıt görünümü + paylaş | Kayıtlar + Kayıt görünümü + dışa aktarma (K11) |
| Ayarlar: Kart, Eşitleme, Bildirimler, Görünüm, Gelişmiş | Bu telefon (K13) + panelin Dil/Görünüm'ü |
| ACİL DURDUR şeridi | Panelin şeridi + K9 kuralı |

## 5. Doğrulama

1. **Birim (vitest):** ortam modülleri (taşıyıcı, istek, p0, depo köprüsü, dosya, eşitle) sahte kart
   (`test/sahte-kart/`) ve sahte eklentilerle; şablon derleme dönüşümü (her `template:` derlendi, kalan
   yok; derlenen çıktıda `new Function`/`eval` yok).
2. **Başsız tarayıcı açılış testi:** `dist/` sıkı CSP ile Chromium'da (Edge), Capacitor eklentileri
   sahte kartla taklit; yedi görünüm + Ayarlar bölümleri açılır, konsolda CSP/Vue hatası 0, ağa giden
   istek 0 (her şey ortamdan).
3. **PC zinciri:** B7 (`test_arayuz3.js`) + panel tarayıcı testleri + TAM `dogrula3.py`; ortam yokken
   panel davranışı değişmedi.
4. **Kotlin:** Gradle birim testleri (Yazdir dahil).
5. **Cihaz kabulü (Xiaomi, gerçek kart):** bağlan, canlı, kayıt başlat/durdur + not, osiloskop yakala,
   kalibrasyon geçmişi, ağ listesi (YAZMADAN — yalnız `Nl`/`Nt`), Kayıtlar eşitle + aç + paylaş, rapor
   yazdır, karşılaştırma, ACİL DURDUR, bildirim. Kartın durumunu değiştiren komutlar (kalibrasyon, `Na`,
   `Ns`, `R!`, `p1`) kabulde ÇALIŞTIRILMAZ — kullanıcının işi.
6. Honor: kullanıcı bağladığında aynı kabul (asıl telefon).

## 6. Üst tasarımdan değişenler

- §10-7 "5H" bu belgeyle kapanır (ayrı yazım yok).
- A8 "şerit her zaman" → K9 (kullanıcı 2026-10-05 kararı, zaten uygulanmıştı).
- A47 "yalnız paketteki dosyalar" AYNEN; CSP AYNEN (K1).
- Ekran listesi (4 sekme) → panelin 7 görünümü + Bu telefon.
