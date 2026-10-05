# Çürütücü 5D — bulgular

İncelenen: `7f3f7db..898cfee` (5D-1 … 5D-4: kayıt eşitleme, Kayıtlar, kayıt görünümü, Ö6 ölçümü).
Kaynak dosyalara dokunulmadı; yazılan her şey bu dizinde. Kart / telefon / `adb` kullanılmadı; ağ yalnız
127.0.0.1'deki sahte kart.

Koşum (hepsi `mobil/` içinden):

```
npx vitest run test/curutucu-5d                      # 18 test: 15 KIRMIZI (bulgular) + 3 yeşil (denetim)
bash test/curutucu-5d/kotlin/derle.sh "$(mktemp -d)"  # Kotlin kanıtı: 4 KIRMIZI iddia (B13); çıkış kodu = kırmızı sayısı
node mutasyon/kos.mjs --liste test/curutucu-5d/yasayan-liste.mjs   # yaşayan mutasyonlar (hepsi YASIYOR beklenir)
```

Her kırmızı test DOĞRU davranışı iddia eder: düzeltme yapılınca yeşile döner. Her biri için kusurun kaynakta
gerçekten bulunduğu ayrıca okunarak doğrulandı (aşağıda satır / işlev adıyla).

Önem sırası: **B1–B3** kullanıcıya yanlış bilgi / kartta geri alınamaz etki; **B4–B9** yanlış ya da eksik
bilgi, dar koşul; **B10–B13** düşük.

---

## B1 — 5D'nin eşitleme metinleri, eşleştirme ekranının aynı adlı sözlük anahtarlarını EZDİ

- **Ne:** `src/cekirdek/sozluk_mobil.js`'te dört anahtar İKİ kez tanımlı: `m.es.suruyor`, `m.es.tamam`,
  `m.es.hata_ag`, `m.es.hata_bagli_degil`. İlk tanımlar eşleştirmenin (5B), ikinciler eşitlemenin (5D). Nesne
  değişmezinde son tanım kazanır; hata / uyarı yok.
- **Nasıl tetiklenir:** Karta eşleştir. Düğmede "Eşleştiriliyor…" yerine **"Kayıtlar telefona alınıyor…"**,
  başarıda "Eşleştirildi." yerine **"Telefondaki kopya güncel · {dk} dk önce"** (ham yer tutucuyla) çıkar.
  Eşleştirmede ağ hatası: "Karta ulaşılamadı. Wi-Fi bağlantısını kontrol et." yerine **"Eşitlenemedi: karta
  ulaşılamadı. Yeniden denenecek."** (yeniden denenmez); `bagli-degil`: "Önce kartı bul." yerine
  "Eşitlenemedi: kart bağlı değil." (`Esles.vue` satır 45, 49; `esles_durum.js` satır 45, 48.)
- **Etki:** yanlış bilgi (5D'nin getirdiği gerileme; her eşleştirmede görünür).
- **Kanıt:** `sozluk-cakisma.test.js` — "sozluk_mobil.js'te hicbir anahtar IKI kez tanimlanmaz …" ve
  "eslestirme ekrani (Esles.vue) kendi metnini gosterir …".
- **Düzeltme:** eşitleme anahtarlarına ayrı önek (`m.et.*` gibi); `test/sozluk.test.js`'e kaynak metninde
  yinelenen anahtar denetimi (nesne üzerinden görülemez).

## B2 — İşçi (Web Worker) çökünce Kayıtlar "telefonda kayıt yok", kayıt görünümü "bu kayıt yok" diyor

- **Ne:** `kayit_istemci.js` işçi `onerror` verince yedeğe (ana iş parçacığı) geçer; yedek işlemcinin `veri`si
  BOŞTUR. `kayitlar.js` `yuklenen` (kimlik + boy + akış kimliği) önbelleği ise "dosya zaten yüklü" demeye devam
  eder → `yukle` yeniden çağrılmaz → `liste` boş veriden kurulur.
- **Nasıl tetiklenir:** WebView işçiyi öldürür (bellek baskısı; 11 MB'lık akışta çözme + piramit), sonra liste
  yenilenir (eşitleme bitti, sekme değişti, arama). Dosya değişmedikçe düzelmez.
- **Etki:** yanlış bilgi — kopya telefonda dururken "Telefonda henüz kayıt yok"; kart bağlıysa bütün oturumlar
  "Kartta / önce eşitle" görünür; açık kayıt görünümü "yok" der; aralık istatistiği sessizce boşalır.
- **Kanıt:** `kayitlar-yalan.test.js` — "isci (Worker) coktukten sonra liste BOS gosterilmez …" ve
  "isci coktukten sonra kayit gorunumu 'bu kayit telefonda yok' DEMEZ …".
- **Düzeltme:** istemci "işlemci değişti" bilgisini versin (kuşak sayacı) ya da `kayitlar.js` `yuklenen`i
  istemcinin kuşağıyla birlikte tutsun; işçi hatasında `yuklenen = null`.

## B3 — Onay ayarı tur SÜRERKEN kapatılırsa karta `Go` gitmeye devam ediyor (A21)

- **Ne:** `esitleme.js` `kos()` `onayAcik()`'ı tur başında BİR kez okur; `onay` kapanışı tur boyunca sabit.
- **Nasıl tetiklenir:** Onay açık, uzun bir eşitleme sürüyor (ilk eşitleme: 1.4 MB ≈ 40 s, ~170 parça, her
  parçadan sonra bir `Go`). Kullanıcı Ayarlar › Eşitleme'de anahtarı KAPATIR (ekran hemen "Kapalı" der).
  Tur bitene kadar her parçada `Go<sıra>` gitmeyi sürdürür. Sınamada: kapatıldıktan sonra 12 `Go` daha.
- **Etki:** kartta geri alınamaz — kart, onaylanan kayıtları silebilir; kullanıcı "kapattım" sanırken onay
  noktası ilerler (PC henüz almamış olabilir: ayarın uyarısının ta kendisi).
- **Kanıt:** `esitleme-kenar.test.js` — "kullanici onayi tur SURERKEN kapatirsa, o andan sonra karta Go GITMEZ".
- **Düzeltme:** `onay` işlevi her çağrıda `onayAcik() === true` denetlesin (kapalıysa göndermeden dönsün).
  Not: `ortak/src/esitle.js` `_onayDogrula` da aynı işlevi çağırır; denetim sarmalayıcıda olmalı.

## B4 — "Kopyayı sıfırla", tur sürerken bir olay (kayıt bitti / bağlandı) geldiyse hata veriyor

- **Ne:** `esitleme.js` `sifirla()` süren turu bekler; ama `simdi()`'nin `finally`'si `tekrar` bayrağı varsa
  HEMEN yeni tur başlatır. `sifirla` devam ettiğinde yeni tur depo kilidini almıştır → `depo.sifirla()`
  `CalismaHatasi` atar → kabuk bunu `KabukHatasi("?")` yapar → ekranda "sıfırlanamadı (?)".
- **Nasıl tetiklenir:** Eşitleme sürerken kayıt biter (ya da bağlantı yenilenir), kullanıcı o sırada iki
  dokunuşla sıfırlar. Kopya SİLİNMEZ.
- **Etki:** işlev çalışmıyor + anlamsız hata türü (veri kaybı yok). `sifirlaOner` durumunda (akış kimliği
  değişti) kullanıcıya önerilen tek çıkış yolu bu düğme.
- **Kanıt:** `esitleme-kenar.test.js` — "tur surerken 'kayit bitti' olayi geldiyse sifirla() BASARIR …".
- **Düzeltme:** `sifirla` bir "sıfırlanıyor" bayrağı koysun (`simdi` / `olay` / `tik` o sırada tur başlatmasın,
  `tekrar` silinsin), `while (suren) await suren` ile beklesin.

## B5 — Uygulama arka plana geçtikten sonra YENİ bir eşitleme turu başlıyor (A22)

- **Ne:** `kabuk.kapat()` yalnız zamanlayıcıyı ve canlı akışı durdurur; süren tur sürer ve `tekrar` bayrağı
  varsa bitince — arka planda — bir tur DAHA başlar (`esitleme.js` `simdi()` görünürlüğü bilmez).
- **Nasıl tetiklenir:** Eşitleme sürerken kayıt biter (`kayitBitti`), kullanıcı uygulamadan çıkar.
- **Etki:** A22 ("arka planda eşitleme YOK") ihlali; onay açıksa arka planda `Go` da gider. Android'in
  WebView'i arka planda ne kadar yürüttüğü cihazda ÖLÇÜLMEDİ; mantık hatası Node'da kanıtlı.
- **Kanıt:** `esitleme-kenar.test.js` — "uygulama arka plana gectikten SONRA yeni bir esitleme turu BASLAMAZ …".
- **Düzeltme:** kabuk `kapat()`'ta eşitlemeye "görünmez" desin (`esit.gorunur(false)`): `tekrar` silinir, yeni
  tur başlamaz; istenirse süren tur parça sınırında kesilir (Esitleyici kaldığı yerden sürdürür).

## B6 — Kayıt görünümü: "Tümünü göster"den sonra istatistik, grafikte GÖRÜNMEYEN aralığa ait kalabiliyor

- **Ne:** `Kayit.vue` `pencereDegisti` istatistiği 150 ms gecikmeyle ister; `tumunuGoster` bekleyen
  zamanlayıcıyı SİLMEZ. Zamanlayıcı sonradan eski pencereyle `okumaIste` çağırır; `okumaNo` onu "en yeni"
  sayar ve tablo eski pencerenin sayılarını gösterir.
- **Nasıl tetiklenir:** Yakınlaştır / kaydır, 150 ms içinde "Tümünü göster"e bas. Grafik tüm aralığı, tablo
  (ort / min / maks / mAh / Wh, süre) dar aralığı gösterir; bir sonraki harekete kadar öyle kalır.
- **Etki:** yanlış bilgi (ekrandaki grafikle uyuşmayan mAh / Wh). Dar zaman penceresi.
- **Kanıt:** `kayit-ekrani-yaris.test.js` — "kaydirmadan hemen sonra 'Tumunu goster'e basilirsa tablo TUM
  araligin istatistigini gosterir …" (Kayit.vue'nun `<script setup>` metni aynen çalıştırılır).
- **Düzeltme:** `tumunuGoster` (ve sağ eksen değişimi) başında `clearTimeout(gecikme)`.

## B7 — Ö6 ölçümü kayıt görünümünün GERÇEK çizim yolunu ölçmüyor: Kayit.vue serileri Vue Proxy'si içinde

- **Ne:** `GrafikOlcum.vue` `Grafik`'e ham diziler verir. `Kayit.vue` işçiden gelen veriyi `const veri =
  ref(null)` içinde tutar; `ref` derin tepkilidir → seri nesneleri ve piramit (`oz`, `oz.duzeyler`) Proxy olur
  ve `Grafik.ciz()` her karede piramide Proxy tuzaklarından erişir.
- **Nasıl tetiklenir:** Her kayıt görünümünde. Bu makinede 800 bin nokta × 2 kanal, 200 karelik aynı betik:
  çizim p95 **0.50 ms (ölçüm aracının yolu) → 3.80 ms (kayıt ekranının yolu), 7.6 kat**.
- **Etki:** performans + ölçüm geçerliliği. DURUM.md'deki "çizimin kendisi ~2–4 ms" sayısı kullanıcının
  gördüğü ekran için geçerli değil (aynı oranla ~15–30 ms: 60 Hz karesinin sınırı). Telefonda ölçülmedi.
- **Kanıt:** `grafik-tepkili.test.js` — "Kayit.vue'nun Grafik'e verdigi seriler ve piramitleri Vue Proxy'si
  DEGIL …" (belirlenimci, `isReactive`) ve "800 bin noktada kayit ekraninin yolu … en cok 2 kat yavas" (süre).
- **Düzeltme:** `Kayit.vue`'da `veri` için `shallowRef` (ya da seriler `markRaw`). Ölçüm aracı aynı kabı
  kullanmalı; gerçek oturumdaki seri sayısı (6 görünür + zarf) da ölçüme girmeli.

## B8 — Ö6 ölçümü HİÇBİR ŞEY çizilmeden "GEÇTİ" diyebiliyor

- **Ne:** `Grafik.ciz()` tuvalin görünen boyu 0 ise temizleyip `null` döner. `grafikOlc` dönüşe bakmaz: kare
  aralığı ekranın 16.7 ms'si olur → `gecti: true`.
- **Nasıl tetiklenir:** Tuval ölçüm sırasında 0 × 0 (düzen kurulmadan başladı, bölüm kapandı / gizlendi, CSS
  değişti). Yaşayan mutasyon C5D-Y9 (`<canvas hidden>`) bütün testlerden geçiyor.
- **Etki:** yanlış "GEÇTİ" (ölçüt kanıtı sahte olabilir). Xiaomi koşusunda çizim süresi 1.6–4 ms ölçüldüğü
  için o koşu gerçekten çizmiş görünüyor; kusur aracın kendini denetlememesi.
- **Kanıt:** `grafik-olcum-bos.test.js` — "tuval gorunmuyorken (0 x 0: hicbir sey cizilmez) olcum 'GECTI' DEMEZ".
- **Düzeltme:** her karede `ciz()`'in plan döndürdüğünü ve planın nokta içerdiğini say; biri bile boşsa sonuç
  `null` / hata.

## B9 — Kartın akışı değiştiyse aynı numaralı iki oturum listede AYIRT EDİLEMİYOR (yinelenen `:key`)

- **Ne:** `kayit_veri.js` satırlara `anahtar` (`<akış>:<oturum>`) ve `eskiKart` koyar; `kayitlar_gorunum.js`
  `satirGorunumu` ikisini de ATAR, `Kayitlar.vue` `:key="s.oturum"` kullanır. (Panel `s.anahtar` + "eski kart"
  rozeti kullanıyor.)
- **Nasıl tetiklenir:** Kart biçimlendi (`GF!`) ya da akışı yeniden başladı; telefonda eski akışın kopyası
  duruyor (eşitleme "kopya uyuşmuyor" der, kullanıcı henüz sıfırlamadı). Yeni akışta da aynı numaralı oturum
  var → listede iki "Oturum #101": biri "Kartta", biri "Telefonda"; hangisinin eski karttan kaldığı yazmaz.
- **Etki:** yanlış / eksik bilgi + Vue'da yinelenen anahtar (liste güncellenirken satırlar karışabilir).
- **Kanıt:** `kayitlar-yalan.test.js` — "kartin akisi degistiyse (GF! / baska akis) ayni numarali iki oturum
  AYIRT edilir …".
- **Düzeltme:** `satirGorunumu` `anahtar` ve `eskiKart`'ı taşısın; `:key="s.anahtar"`; "eski kart" rozeti.

## B10 — Kartta telefonun alamadığı daha yeni kayıt varken satır yeşil ve "Telefondaki kopya güncel" diyor

- **Ne:** `durum_gorunum.js` `esitlemeGorunumu`: `hal === "tamam"` ise `bekleyen > 0` olsa da anahtar
  `m.es.tamam_simdi`, sınıf `iyi`; yalnız alt satıra "Kartta daha yeni kayıt var ama henüz okunamadı" eklenir.
- **Nasıl tetiklenir:** Kart boş yanıt verip `X-Sonraki-Sira`'yı ileride bildirdiğinde (yarım yazılmış /
  biçimlenmiş bölge; Esitleyici `{ bekleyen: N }` döner).
- **Etki:** çelişen iki cümle; üst satır yanlış.
- **Kanıt:** `ekran-yalan.test.js` — "kartta telefonun ALAMADIGI daha yeni kayit varken (bekleyen > 0) …".
  (Ayrıca C5D-Y3: `bekleyen`in durumdan düşmesi hiçbir testi kırmıyor.)
- **Düzeltme:** `bekleyen > 0` için ayrı anahtar ("Kopya N kayıt geride") ve `uyari` sınıfı.

## B11 — Aralık istatistiği işçide O AN yüklü olan dosyadan hesaplanıyor (ekrandaki kartın değil)

- **Ne:** `kayitlar.js` `okuma()` `sirayla` kuyruğuna girmez ve `hazirla` çağırmaz; işçide tek bir `veri`
  durur. Araya başka kimlikle bir `liste` girerse (kart değişti) istatistik öbür kartın aynı numaralı
  oturumundan gelir.
- **Nasıl tetiklenir:** Kayıt görünümü açıkken Kayıtlar ekranının yolda kalmış yenilemesi (`sira` yalnız
  ekranı korur, isteği iptal etmez) kart kimliği değiştikten sonra koşar. DÜŞÜK olasılık: eşleşmemiş
  telefonda başka bir kartın bulunduğu an gerekir.
- **Etki:** yanlış bilgi (grafik 10 V, tablo 20 V).
- **Kanıt:** `kayitlar-yalan.test.js` — "aralik istatistigi (okuma) EKRANDAKI kartin kopyasindan hesaplanir …".
- **Düzeltme:** `oturum()` sonucu bir veri kuşağı taşısın; `okuma(no, tA, tB, kusak)` kuşak uymuyorsa `null`.

## B12 — `onayAcik()` atarsa `simdi()` reddediyor ("ASLA atmaz" sözü)

- **Ne:** `kos()` içinde `onayAcik()` `try`'ın DIŞINDA çağrılır.
- **Nasıl tetiklenir:** Üretimde ulaşılamaz (`uygulama.js` `esitlemeOnayi` kendi `try`'ına sahip); yalnız
  sözleşme. `tik` / `olay` yolunda yakalanmamış söz reddi olurdu. `Go` GİTMEZ (A21 bozulmuyor).
- **Etki:** yalnız sağlamlık.
- **Kanıt:** `esitleme-kenar.test.js` — "onayAcik() atarsa simdi() REDDETMEZ …".
- **Düzeltme:** okuma `try` içine; atarsa `false`.

## B13 — WebView kapısı Capacitor'ın dosya ön ekini (`/_capacitor_file_/…`) geçiriyor: A24'ün dar kuralının YANINDAN özel dizin okunabilir

- **Ne:** `MainActivity.shouldInterceptRequest`: `WebKapi.izinli` → `DepoYolu.depoAdresi` → aksi halde
  Capacitor'ın yerel sunucusu. `https://localhost/_capacitor_file_/<mutlak yol>` ilk ikisinden geçer;
  Capacitor (`WebViewLocalServer.isLocalFile`, `AndroidProtocolHandler.openFile`) uygulamanın okuyabildiği HER
  dosyayı verir: `files/kart/<kimlik>/durum.json`, kasa dosyaları, `_capacitor_content_` ile içerik sağlayıcılar.
- **Nasıl tetiklenir:** WebView'de çalışan kodun böyle bir adrese `fetch` yapması gerekir. Bugün `src/`'te tek
  `fetch` `depo_oku.js`'te ve kalıbı dar; yani istismar için kod enjeksiyonu ya da kalıbın gevşemesi gerekir
  (C5D-Y10: kalıba `|^\/_capacitor_file_\/` eklemek bütün testlerden geçiyor). Derinlemesine savunma açığı.
  5D öncesinde de vardı; 5D ilk `fetch`'i ve "yalnız şu adres" iddiasını getirdiği için burada.
- **Etki:** güvenlik (ikinci savunma hattı yok). Kotlin kısmı (kapı geçiriyor) koşularak, Capacitor'ın dosyayı
  verdiği kaynak OKUNARAK doğrulandı; cihazda denenmedi.
- **Kanıt:** `kotlin/Curutucu5d.kt` + `kotlin/derle.sh` — "D1 ozel dizindeki dosyayi veren Capacitor adresi
  ENGELLENMELI" (4 adres, 4 KIRMIZI). Örnek yollar uydurmadır.
- **Düzeltme:** `WebKapi.izinli` yolu `/_capacitor_file_` / `/_capacitor_content_` ile başlayan adresleri
  reddetsin (uygulama `convertFileSrc` kullanmıyor); `WebKapiTest`'e eklenir.

---

## Yaşayan mutasyonlar

Aday listesi `aday-liste.mjs`: 30 aday, her biri BÜTÜN mevcut takıma (39 dosya / 457 test) karşı koşuldu →
16 OLDU, 14 YAŞIYOR. Yaşayanlar `yasayan-liste.mjs`'te; resmî koşucuyla ikinci kez koşuldu: 14/14 yine YAŞIYOR
(aynı koşuda denetim olarak eklenen, ilk turda "taban kırmızı" yüzünden uygulanamayan aday OLDU).

| # | Dosya | Mutasyon | Neyi gösteriyor |
|---|---|---|---|
| Y1 | `esitleme.js` | `sifirla` süren turu beklemiyor | Tur sürerken sıfırlama hiç sınanmıyor (B4'ün komşusu) |
| Y2 | `esitleme.js` | sıfırlamadan sonra `sonDeneme = null` yok | "Ardından kendiliğinden baştan indi" (DURUM) testsiz |
| Y3 | `esitleme.js` | `bekleyen` hep 0 | Eşitleyicinin `bekleyen`i ekrana taşınıyor mu, sınanmıyor (B10) |
| Y4 | `kayitlar.js` | önbellekte kart kimliği karşılaştırılmıyor | "kart kimliği izlenir" iddiası testsiz |
| Y5 | `kayit_veri.js` | akış kimliği işçiye geçmiyor | Eski akıştan kalan kopyanın `eskiKart` işareti uçtan uca sınanmıyor (B9) |
| Y6 | `kayit_veri.js` | `tahmini` hep `false` | "Zaman tahmini" uyarısı testsiz |
| Y7 | `kayit_veri.js` | oturum önbelleği yeniden yüklemede kalıyor | Büyüyen oturumda bayat grafik: testsiz |
| Y8 | `GrafikOlcum.vue` | ölçüm tek kanal çiziyor | Ekranın ölçtüğü yük sabitlenmemiş |
| Y9 | `GrafikOlcum.vue` | tuval `hidden` | B8: hiçbir şey çizilmeden "GEÇTİ" |
| Y10 | `depo_oku.js` | kalıp `/_capacitor_file_/` ve `http://10.` de kabul ediyor | Gizlilik testinin "kötü adres" listesi kalıbı SABİTLEMİYOR (B13) |
| Y11 | `kayit_isci.js` | mesajdaki adresten `import()` | Muaf dosyada dinamik içe aktarma yasak listesinde yok |
| Y12 | `depo_oku.js` | `new Image().src = url` | Muaf dosyada (ve genel yasakta) `Image` yok |
| Y13 | `MainActivity.java` | depo dosyası GET dışı yöntemlere de veriliyor | `depoYaniti` hiçbir testle sabitlenmemiş (JVM testi de yok) |
| Y14 | `MainActivity.java` | depo isteği `depoYaniti`'na gitmiyor | Aynı: yerel akıtmanın bağlanması testsiz |

Y10–Y12 ağa sızıntı DEĞİLDİR (yerelde `WebKapi` + CSP yine engeller); gösterdikleri, DURUM.md'de "her biri
kendi dar kuralıyla denetleniyor" denen JS testinin o üç dosyada bu değişiklikleri görmediğidir.

## Saldırdım, açık bulamadım

- **A21, varsayılan onaysız:** bozuk / boş / `"true"` / `"1 "` yerel depo değeri, `getItem` atması, kabuğun
  yeniden kurulması, süren tura bağlanma: `Go` gitmiyor. Onay açıkken `Go` yalnız `veriEkle` + `durumYaz`
  sonrasında; `durumYaz` atarsa gitmiyor (Esitleyici sırası). "Bir sonraki sırayı onayla" mutasyonu ÖLDÜ.
- **Sıfırlama ↔ eşitleme veri yarışı:** `sifirla` eklenti çağrısı yoldayken başlayan tur, eklentinin tek iş
  parçacığında sıfırlamanın ARKASINA girer → boş depodan temiz başlar; kopya bozulmuyor (yalnız B4).
- **Yarıda kesilen eşitleme / dolu disk:** yarım kuyruk kırpılıyor, tam kayıt ileri sarılıyor; `durumYaz`
  sürekli atarsa hata + veri yerinde; yanlış "tamam" yok.
- **İki `esitlemeKur` / aynı kimlikte iki depo:** kilit kimliğe bağlı, ikinci tur "meşgul".
- **CRC'si geçerli tuhaf kayıtlar (25 çeşit):** BAŞLA'sız NOKTA / BİTİR, boş ve kısa yükler, bilinmeyen tür,
  çift BAŞLA, geçersiz UTF-8 ad, boş ayrıntı / skop kaydı: `veriKur` / `listeKur` / `oturumGorunumu` /
  `aralikOkuma` hiçbiri atmıyor, liste düşmüyor.
- **`depo_oku.js` + `DepoYolu.kt` + `depoYaniti`:** bu ÜÇLÜ üzerinden başka dosya ya da ağ adresi okunamıyor
  (kalıp iki tarafta tam eşleme; sorgu / parça / `..` / büyük harf / satır sonu reddediliyor). Açık yan
  yoldan (B13).
- **`kayit_veri.js` `yukle`'nin `url`'yi denetlememesi:** tek çağıran `kayitlar.js` (`depoAdresi`: kimlik
  kalıbı) ve `getir` her iki yolda `yerelOku` (kendi kalıbı). Kötü `url` verilebilen yol bulamadım.
- **KartDepo.kt:** kimlik denetimi her yolda; `veriKirp` büyütme Esitleyici'den ulaşılamıyor (yalnız
  `d.bayt + gecerli ≤ boy`); `boyutlar` `Long`; atomik yazım yerinde.
- **`structuredClone`:** `oz.t === s.t` kimliği tek mesajda korunuyor (piramit yeniden kurulmuyor).

## Kanıtsız şüpheler (bulgu DEĞİL)

- **(kanıtsız)** `MainActivity.depoYaniti` dosyayı eklentinin iş parçacığıyla eşgüdümsüz okur
  (`FileInputStream`, kilit yok). `_hazirla` kırparken / ardından eklerken okuyan akış, hiçbir an var olmamış
  bir bayt dizisi görebilir; `akisOnek` CRC ile geçerli ön eki alır, ama `kayitlar.js` `boy`'u okumadan ÖNCE
  ölçtüğü için "yüklü" sayılan veri eksik kalabilir (boy aynı kaldıkça). Android gerekir.
- **(kanıtsız)** `depoYaniti` her istisnada 404 döner; `yerelOku` 404'ü "boş kopya" sayar → dosya açılamazsa
  (G/Ç hatası) ekran hata yerine "telefonda kayıt yok" der.
- **(kanıtsız)** `KartDepo.sifirla` dosyaları tek tek siler; yarıda kalırsa `durum.json` gitmiş,
  `kayitlar.kyt` kalmış olabilir → sonraki eşitleme durumu sıfırdan sayar ve dosya 1. sıradan başlamıyorsa
  (kartın eski kayıtları silinmiş) kopyayı SESSİZCE 0'a kırpar. Silme sırası `listFiles()`'a bağlı.
- **(kanıtsız)** Eşleşme kaldırılınca telefondaki kopya silinmiyor ve sorulmuyor (A19 "kayıtlar ayrı soruyla";
  `KartDepo.sifirla` yorumu "eşleşmeyi kaldırırken" diyor, çağıran yok). Başka kartla eşleşince eski kopya
  arayüzden ne görülebilir ne silinebilir. 5D kapsamında mı, belirsiz.
- **(kanıtsız)** Kayıtlar, kart ağda ama eşleşmemişken / `/kayit/liste` geçici hata verdiğinde de "Kart bu
  ağda değil: liste telefondaki kopyadan" der (`kartVar` yalnız dizin okunabildiyse `true`).
- **(kanıtsız)** Eşleşme kaldırıldıktan sonra eşitleme durumu "tamam"da kalır: Durum "Telefondaki kopya güncel
  · N dk önce" demeyi sürdürür (N büyür); durum hangi karta ait olduğunu taşımıyor.
- **(kanıtsız)** `grafik.durumAyarla` kendi `istek()`'ini de kurar: Ö6 ölçümünde her kare İKİ kez çizilir
  (biri ölçülen `ciz()`, biri animasyon karesinde). Kare aralığı bunu içerir (ölçüt aleyhine, yanlış "GEÇTİ"
  üretmez) ama "çizim süresi" satırı karenin gerçek JS yükünün yarısını gösterir.
- **(kanıtsız)** Hedefi kopyada olmayan NOT kaydı (eski oturumun adı sonradan değişti, oturumun verisi karttan
  silinmişti) listede veri taşımayan hayalet bir "oturum" üretir (panelle ortak davranış).
- **Takımda oynak test:** aday koşusunda bir kez "taban kırmızı" görüldü (bozulmamış kopyada bütün takım
  yeşil değildi); hangisi olduğu yakalanmadı — yük altında zamana bağlı bir test var.
