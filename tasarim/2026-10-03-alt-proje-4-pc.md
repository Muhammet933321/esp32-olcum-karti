# Alt proje 4 — PC uygulaması (tasarım)

Üst tasarım: [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) — §3 (PC uygulaması = köprünün
`localhost`'tan sunduğu kurulabilir PWA; asıl kayıt kartta), §4 tablo satır 4 ("Köprü: USB **ve** WiFi eşitleme,
disk arşivi, PWA, Windows bildirimi, MQTT aboneliği"), §5 (eşitleme: küçük parçalar, kalıcı yazımdan SONRA onay,
baytlar aynen), §6 (eşleştirme, imza, DPAPI), §8 (bildirimler), §13 (PC bildirim yolu bu alt projeye bırakıldı).
Önceki alt projeler: 1 (kart), 2 (`ortak/`), 3 (web paneli; `tasarim/2026-10-02-alt-proje-3-panel.md`).

> **Karar yetkisi:** kullanıcı 2026-10-03 gecesi "bana soru sorma, en uygun yoldan devam et; iş biterse sıradaki
> adım" dedi. Kararlar benim; her birinin gerekçesi ve yanlışsa maliyeti yazılı, hepsi geri alınabilir. Firmware
> değişiklikleri yalnız tam flaş yedeğinden sonra. Kullanıcının bildiği sırlar (MQTT aracı parolaları) istenmez,
> basılmaz, kaydedilmez.

## Keşif (2026-10-03, iş akışı: 5 okuyucu + sentez)

Parçalar var ama birbirine bağlı değil: `kopru/kopru.py` (USB akışını tarayıcılara röle + eski `.satir` arşivi),
`kopru/kayit_esitle.py` (WiFi'den bayt bayt `kayitlar.kyt`, kalıcı yazımdan sonra onay — B72'de sınanıyor),
`kopru/imza.py` (eşleştirme, DPAPI), `kopru/bildirim.py` + `mqtt_istemci.py` + `chacha.py` (MQTT dinleme +
zarf çözme, konsola). Eksikler: tek süreç, güvenli köken, arka planda eşitleme, panelin PC arşivini görmesi,
Windows bildirimi, PWA kabuğu. **Güvenlik açığı (ilk iş):** köprü `0.0.0.0`'a bağlanıyor ve yerel ağdaki İLK
istemci sürücü olup USB üzerinden `Ns` / `Na` / `Np` / `GF!` / `R!` / `p1` gönderebiliyor — kart USB'de kimlik
sormadığından 1D'nin bütün koruması atlanıyor.

## Dilimler (sıra)

4A köprü ana süreci → 4B kartla WiFi + eşleşmiş köprü (firmware dahil) → 4C arka plan disk arşivi → 4D panel
PC'de (arşiv "bu PC" olarak) → 4E MQTT + Windows bildirimi → 4G kart kabulü. 4F (PWA kabuğu) 4A'dan sonra
paralel.

## Kararlar

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| PC1 | **Köken `http://olcum.localhost:8770`, yalnız `127.0.0.1`'e bağlı;** Edge'de `isSecureContext === true` ve service worker kaydı ölçülmeden kesinleşmez, tutmazsa `http://127.0.0.1:8770` | `*.localhost` döngüye çözülür ve güvenli bağlamdır; stok-takip'in `127.0.0.1:80` / `stok` adlarıyla çakışmaz, hosts dosyası gerekmez. Yanlışsa: köken bir satırda değişir |
| PC2 | **Yerel ağa açılma varsayılan KAPALI;** `--lan` ile açılırsa SALT OKUMA (canlı izleme), tek komut istisnası `p0` | Telefonlar karta doğrudan bağlanabiliyor (panel destekliyor), köprü üzerinden komut kanalı gereksiz. 1D'yi atlayan açık kapanır. Maliyet: telefonda köprünün LAN adresini kullanan, kartı göremeyen kullanım (yok) |
| PC3 | **COM portunu VID'den seç** (`1A86`/`10C4`/`0403`; `303A` reddedilir); köprü portu tutarken tezgah araçları portu yoklayıp "köprü kullanıyor — kapat" der (sessiz tutulma yok); ileride gerekirse döngü-yalnız `POST /seri/birak` | Yanlış sokete (yerel USB) bağlanma sessiz kalıyordu (CLAUDE.md). Tek port tek süreç |
| PC4 | **Tek ana süreç** `kopru/pc.py` (ad önerisi): röle + (4C) eşitleme döngüsü + (4E) MQTT aynı süreçte; `pythonw --sessiz`, `zaten_calisiyor()`, `arkaplan-hata.txt`, Başlangıç kısayolu + kapatma `.bat` (stok-takip deseni); Windows'ta `allow_reuse_address = False` | Kanıtlanmış desen; iki köprü aynı portu ele geçirmesin |
| PC5 | **Cihaz anahtarı ve arşiv depo DIŞINDA:** `%LOCALAPPDATA%\olcum-karti\cihaz\` ve `…\arsiv\<kart kimliği>\` (ortam değişkeniyle değiştirilebilir) | Çalışma ağacı değişince / `git clean`'de kaybolmaz; DPAPI zaten kullanıcı hesabına bağlı |
| PC6 | **Köprü kartla WiFi'den, EŞLEŞMİŞ cihaz olarak konuşur:** imzalı `/akis` (her yeniden bağlanmada YENİ URL), imzalı `/komut`, kart kimliği cihaz dosyasıyla denetlenir; USB varsa canlı akış ve komut USB'den, kayıt verisi her zaman WiFi'den (sahada kartın kendi AP'si de WiFi) | Kayıt verisinin seri yolu yok; 115200 baud'da 11.4 MB ≈ 17–35 dk ve ölçüm döngüsünü bloklama riski. USB-yalnız (`N0`) durumu için seri döküm ayrı dilim **4C-2, ERTELENDİ** (kullanıcı ihtiyaç derse) |
| PC7 | **Köprüyü eşleştirme `imza.py esles`** (WiFi, parola bir kez); panelden eşleştirme köprü için YOK | K tarayıcı deposuna düşmesin (spec §6'nın en zayıf seçeneği) |
| PC8 | ⚠ **Firmware: "köprü kayıtlıyken ikinci `/akis` reddi" KALKAR, `/kopru` CORS kaydı da kalkar** (köprü sunucu tarafında vekil olduğundan CORS gereksiz). Tam flaş yedeği + `yukle.py`; üç eski iddia gerekçesiyle güncellenir | Spec §5 "4 istemci, ret kalkar". Saldırı yüzeyi küçülür. Maliyet: kart firmware'i değişir (yedekten geri dönülür) |
| PC9 | **Arka plan eşitleme:** `Esitleyici` köprü sürecinde döngüde (yeniden bağlanınca + aralıkla, artan bekleme), parça ≤ 8192 B; **PC varsayılan ONAY VERİR** (ayarla kapatılabilir) — kalıcı yazım + fsync'ten SONRA | Spec §3 temizlik "en az bir cihaza kopyalanmış"; PC doğal arşiv. Uyarı UI'da: onaylı eski kayıt kart dolunca silinebilir, eşitlenmemiş telefon onu göremez. Panelin kendi varsayılanı ONAYSIZ kalır (C3) |
| PC10 | **Panel PC'de arşivi Python'un yazdığı dosyalardan okur:** köprüde salt okunur `/arsiv/liste`, `/arsiv/veri` + panelde salt okunur DEPO uyarlayıcısı (`ortak/src/esitle.js` DEPO arayüzü, `bellekDepo` örnek); tek yazar Python. Kayıtlar'da "nerede: PC". `olcum.local` kökenindeki IndexedDB kopyaları yok sayılır (kayıt kartta duruyor, diske eşitlenir) | İki yazar / iki kopya yok; `esitle.kilit`'in önlediği yarış doğmaz. Spec P6 "PC diske yazan depoyu takar" bu biçimde güncellenir |
| PC11 | **Köprü kart uçlarını imzalı vekil eder:** `/pil`, `/kal/liste`, `/kunye.json`; `p0` vekilde de serbest ve imzasız | Panel PC'de kart özelliklerini kaybetmesin; Ö7 |
| PC12 | **B35 `.satir` skop arşivi** salt okuma, "eski arşiv" başlığı altında; dönüştürülmez | Spec l.436 |
| PC13 | **Windows bildirimi:** önce ölçülü bir deneme — kapalı panelde görünür mü, aynı bildirim yerinde güncellenir mi, kaynak adı ne. Varsayılan: WinRT toast (`powershell.exe` alt süreci, Tag/Group ile yerinde güncelleme) + ctypes tepsi simgesi (çıkış menüsü). PWA Notification ana yol DEĞİL (pencere kapalıyken çalışmaz) | Spec l.21-23 "uygulama kapalıyken de"; stdlib kuralı (§13) |
| PC14 | **MQTT bilgisi önbelleği:** `/bildirim/bilgi`'nin K ile şifreli `OKB1` zarfı OLDUĞU GİBİ saklanır (K DPAPI'de); çözme hatasında (`QR!` sonrası) ya da CONNACK 4/5'te kart erişilebilirse yeniden alınır. Çözülmüş kimlik bilgisi diske YAZILMAZ | Yeni sır biçimi yok |
| PC15 | **Kaçırılan olaylar:** kalıcı oturum (clean_session=0) ölçülmeden kullanılmaz; çevrimdışıyken kaçan olaylar `(a, n)` boşluklarından + eşitlemeden "kaçırılanlar" özeti olarak bildirilir | EMQX Serverless'ın kalıcı oturum davranışı ölçülmedi |
| PC16 | **Yineleme anahtarı:** MQTT içinde `(a, n)`; yollar arası anlamsal anahtar (`tur`, `a`, `oturum`) + zaman penceresi | `n` her açılışta 1'den başlıyor |
| PC17 | **PWA kabuğu:** service worker yalnız güvenli bağlamda kaydolur; kabuk + `/ortak/` için AĞ ÖNCE (önbellek yedek), `/akis`, `/komut`, `/arsiv`, `/kayit`, API ASLA önbelleklenmez; köprü yoksa "köprü çalışmıyor" sayfası; 192/512 px (maskable) simge, manifest `id`/`scope` | Derleme adımı yok: bayat kabuk, karttaki panelle sürüm ayrışması demek |
| PC18 | **Ö4'ün PC karşılığı:** hedef 10 s, kabul 15 s (telefonla aynı); ölçümü gerçek aracıda kullanıcı yapar (parolalar onda) | Spec PC tarafına sayı vermiyordu |

### 4A uygulama kararları (2026-10-03)

**PC1 ölçümü (kesinleşti).** Edge 154 başlıksız, sunucu yalnız `127.0.0.1:8770`'e bağlı:
`http://olcum.localhost:8770/` isteği 127.0.0.1'deki sunucuya ulaştı (`Host: olcum.localhost:8770`),
`isSecureContext === true`, deneme service worker'ı kaydoldu ve yeniden yüklemede sayfayı denetledi
(`controller` var). Yedek köken (`127.0.0.1:8770`) gerekmedi. İşletim sistemi `*.localhost`'u
**çözmüyor** (`getaddrinfo` hata) — yalnız tarayıcı çözüyor; Python tarafı köprüye hep `127.0.0.1` ile
bağlanır. Ölçüm her koşuda `uretim/tarayici_pc.py` (T4A) ile tekrarlanıyor: gerçek `sunucu_kur` +
gerçek panel, panel bu kökende taşıyıcıyı kendiliğinden `akis` seçip "Bağlan"sız bağlanıyor.
Panelde değişiklik gerekmedi: `kopruyuAlgila`/`otomatikBaglanmali` yalnız düz `localhost`'u
geliştirme sunucusu sayıyor; `olcum.localhost` sayfayı sunan köprü — B7'ye iki iddia eklendi.

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| 4A-1 | **Port 8770 sabit, başka porta düşülmez** (eski zincir 0.0.0.0:80 → LAN IP:80 → 8770 kalktı). Port meşgulse açık hata; `--http-port` yalnız ölü tekrar / test için | Köken porta bağlı: IndexedDB, service worker, izinler kökende. Düşülseydi panelin yerel verisi her açılışta başka kökende kalırdı |
| 4A-2 | **Döngü dışı istemci HER kipte salt okuma** (yalnız `--lan`'da değil): sürücü olamaz, `/devral` 403, `/skop.bin` 403 (canlı yakalama karta `t` yollatır — okuma değil komut), `/komut`'ta yalnız tam `p0`; `X-Olcum` başlığı p0 için de kalır (CSRF, kimlik değil) | Varsayılan bağlama zaten 127.0.0.1; kural bağlamaya güvenmesin (derinlemesine savunma). `p0` sıra olarak salt okuma denetiminden ÖNCE — Ö7 |
| 4A-3 | **Host başlığı denetimi:** yalnız `localhost`, `*.localhost`, IP adresi; diğer ad 403, başlıksız istek kabul | Döngü bağlaması DNS yeniden bağlamaya karşı korumaz: kötü bir site adını 127.0.0.1'e çözdürüp aynı köken sayılır, `X-Olcum`'u ön-uçuşsuz ekler ve USB'den `Ns`/`GF!` yollatır. Telefonlar IP ile gelir — etkilenmez |
| 4A-4 | **Windows'ta `SO_EXCLUSIVEADDRUSE`** (+ `allow_reuse_address = False`) | Ölçüldü: 127.0.0.1:P başka süreçteyken 0.0.0.0:P bağlaması bu bayrak olmadan BAŞARILI; `--lan` köprüsü "açıldı" der, döngü trafiği öteki sürece gider |
| 4A-5 | **Gizli satır süzgeci (D5 #12):** `EK <n>` her yerde (önekli de), eksik `EK` ya da `(yalniz USB)` satırından sonra 2 satır pencere, pencere dışında harf içeren ≥ 24 onaltılık dizi düşer; 16'lık kart kimliği ve uzun ondalık sayılar geçer. Tam `EK` satırında pencere açılmaz | **Bulunan açık:** firmware AP parolasını (`N?` ve AP kipindeki açılış afişi) "yalnız USB" diye ham UART'a basıyor, köprü ham UART'ı okuduğu için o satırı `/akis`'e ve arşive taşıyordu. Kök düzeltme (tek `ham()` çağrısı) firmware işi → 4B'ye |
| 4A-6 | **VID seçimi:** kayıt defteri `Enum\USB` + `Enum\FTDIBUS` ∩ `SERIALCOMM` (takılı olanlar); aynı COM'a iki VID düşerse belirsiz → seçilmez; elle verilen 303A da reddedilir | Enum takılı olmayan eski aygıtları tutuyor (bu makinede COM3/COM5 eski CH340). 303A portu açılır ama sessiz kalır |
| 4A-7 | **Meşgul port mesajı `kart_baglanti.acma_hatasi`'nda** (bütün araçların açma yolu): WinError 5'te 127.0.0.1:8770/`durum`'a sorulur; köprü o portu tutuyorsa "PC kopru bu portu kullaniyor — kapatin" | Tek yerde; tezgah araçları sessizce "açılamadı" demesin. Gerçek kartta (COM6) doğrulandı |
| 4A-8 | **`OtoSeriKart`:** köprü kart takılı değilken de açılır, port VID'den yeniden aranır (3 s), kopunca (`ReadFile`/`WriteFile` FALSE → `SeriKart.kopuk`) kapatıp yeniden arar; durum satırları akışa BİR KEZ, arşive hiç; kart yokken son durum satırı sonradan bağlanan tarayıcıya da `/akis` açılışında gönderilir | Başlangıç kısayolu kartsız açılışta ölmesin. ⚠ Gerçek kabloyu çekip takma tezgah kalemi (sahte kartla sınandı) |
| 4A-9 | **`kopru.py`'nin `main`'i `pc.py`'ye devreder** — eski komut ve seçenekler çalışır; ön planda tarayıcı açılır (stok-takip deseni), `--tarayici-acma` ile kapanır | Tek giriş noktası; iki ayrı `main` ayrışırdı |
| 4A-10 | **`.satir` arşivinin yeri DEĞİŞMEDİ** (`kopru/arsiv/`, gitignore'da); 4A'da depo dışına taşınan yalnız çökme izi (`%LOCALAPPDATA%\olcum-karti\arkaplan-hata.txt`, `OLCUM_PC_DIZIN`) | PC5 yeni arşivle (4C) birlikte; şimdi taşımak kullanıcının mevcut B35 arşivini "kaybolmuş" gösterirdi (PC12 onu salt okuma eski arşiv yapıyor) |
| 4A-11 | **Başlangıç kısayolu araçları var, KURULMADI:** `kopru/Otomatik Baslat Kur.bat` / `Otomatik Baslatmayi Kapat.bat` → `otomatik-baslat.ps1` (gerçek `pythonw.exe` yolunu `sys.executable`'dan bulur; WindowsApps takma adı değil). Kısayol, kurulumun yapıldığı çalışma ağacının `pc.py`'sini gösterir | Kurulum kullanıcının kararı. Birden çok çalışma ağacı var — betik yolu ekrana yazar |
| 4A-12 | **`sunucu_kur` her sunucuya özel işleyici alt sınıfı** kurar (`Isleyici.kopru` paylaşılan sınıf niteliği değil) | Aynı süreçte iki sunucu (test, ölü tekrar) birbirinin köprüsünü eziyordu |
| 4A-13 | **`gizlilik_dogrula.py`:** düz eğik çizgili mutlak yol (her sürücü harfi + `Users`/`home`/`Muhammet`), ters eğik çizgili desenler de her sürücü harfine genişledi; gömülü parola = adı parola/sifre/password ile BİTEN alana yazılmış ≥ 4 karakterlik düz metin. Deneme değeri işareti: `sinama`/`deneme`/`test`/`ornek`/`gizli`/`dogru`/`yanlis`/`sahte`, 4+ tekrar, sözlük anahtarı (`es.parola`) ya da tam değer beyaz listesi (iki kayıt, gerekçeli); üretilmiş çapraz vektör JSON'ları atlanır (üreten `.py` taranıyor). Bulunan değer EKRANA BASILMAZ | "kart", "1234" gibi gerçek parolada da geçebilecek parçalar bilerek işaret değil. Yeni test parolası işaret sözcüğü taşımalı |

Açık kalanlar (4A dışı): `yukle.py`, `tezgah_kart.py`, `arayuz-yaz.py` kendi port seçicileriyle (`portlari_listele`)
hâlâ VID'e bakmıyor — açma yolunda meşgul port mesajı var ama otomatik seçim eski; yerel ağ istemcisine panelde
"salt okuma" arayüzü yok (403 metni görünür) — 4D/4F.

### 4F uygulama kararları (2026-10-03)

**PC17 ölçümü (Edge, başlıksız, gerçek `sunucu_kur` + gerçek panel, `uretim/tarayici_pwa.py` = T4F 16/16).**
Panel `olcum.localhost`'ta `sw.js`'i kaydediyor (kapsam `/`), yeniden yüklemede sayfayı denetliyor; denetim
altındaki yüklemede `/app.js`, `/style.css`, `/vendor/vue.global.prod.js`, `/ortak/sozluk.js` yine köprüden
isteniyor (ağ önce). Edge'in kendi denetimi: `Page.getAppManifest` hatasız, `Page.getInstallabilityErrors` BOŞ
(kurulabilir). Cache Storage'da tek `olcum-kabuk-<SURUM>`, içinde yalnız kabuk dosyaları (cevrimdisi.html,
manifest, ikonlar, app.js, style.css, vendor, `/ekran/*.js`, `/ortak/*.js`); `/durum`, `/skop/liste`,
`/kunye.json`, `/arsiv/liste`, `/app.js?v=1`, `/akis`, `/komut` istendikten sonra da YOK. Köprü kapatılınca
yeniden yükleme "Köprü çalışmıyor" sayfasını veriyor (adres ve `#/canli` korunuyor, dış kaynak yok); köprü
aynı portta yeniden açılınca sayfa kendiliğinden panele dönüp bağlanıyor. Kart kökeni benzetimi
(`http://olcum.local`, Edge'de ad 127.0.0.1'e eşleniyor): `isSecureContext` false, `serviceWorker` yok, panel
`atlandi`; geliştirme sunucusu (`localhost`): güvenli bağlam ama kayıt yok.

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| 4F-1 | **Kayıt yalnız güvenli bağlamdaki `*.localhost` kökeninde** (`swKaydiUygun`: `isSecureContext === true` + `serviceWorker` API + `^[a-z0-9-]+\.localhost$`); düz `localhost`/`127.0.0.1` (geliştirme sunucusu, testler) ve kart HAYIR. Uygun olmayan güvenli kökende eski kayıt varsa silinir | Kart zaten güvenli değil (tarayıcı izin vermez) ama koruma tarayıcıya bırakılmadı. Geliştirme sunucusunda kaydolsaydı düz `localhost`'taki her test bir SW arkasında kalırdı. Yanlışsa: tek regex |
| 4F-2 | **Kayıt `load`'dan sonra, bir sonraki görev turunda** (`setTimeout 0`); `updateViaCache: 'none'` | Açılışı, ilk boyamayı ve p0 yolunu bekletmez; sw.js güncellemesi HTTP önbelleğine takılmaz |
| 4F-3 | **İZİN listesi** (yasak listesi değil): `KABUK` (app.js, style.css, vendor, manifest, cevrimdisi.html) + desen `/ekran/*.js`, `/ortak/*.js`, `/ikon-*.png`; GET + aynı köken + sorgusuz. Başka her istekte `respondWith` YOK | Yeni bir API ucu unutulursa sonuç "önbelleklenmez" olur, tersi değil. B7 kart görüntüsündeki her durağan dosyanın listede olduğunu sınıyor (yeni varlık unutulmasın) |
| 4F-4 | **Ağ önce `cache: 'no-cache'` ile**; önbellek yalnız ağ hatasında. Gezinme ağdan, yoksa cevrimdisi.html; gezinme yanıtı (index.html) ÖNBELLEĞE ALINMAZ | Köprü `Last-Modified` veriyor, sezgisel HTTP önbelleği bayat kabuk verebilirdi (304 ucuz). Eski index.html yeni modüllerle karışmasın |
| 4F-5 | **Önbellek adı `olcum-kabuk-<SURUM>`; SURUM satırını `arayuz-uret.py` yazar** (`kabuk_surumu` = panel sürümü kuralı, kapsam panelin kaynakları + cevrimdisi.html, sw.js hariç). `skipWaiting` + `clients.claim`; `activate` yalnız eski `olcum-kabuk-*`'ı siler | Panel değişince sw.js baytları değişir → yeni SW → tutarlı kabuk. `sim3_web.py` 6p satırın bayat olmadığını sınar (unutulursa kırmızı). Köprüde `/kunye.json` yok ve PC11'de KARTIN künyesi olacak — sürüm oradan alınamazdı |
| 4F-6 | **sw.js ve cevrimdisi.html karta GİRMEZ** (`arayuz-uret.py` `PC_KABUGU`); **manifestteki her ikon GİRER** (`manifest_ikonlari`, liste manifestten) | Kart SW kullanamaz: ölü bayt. Manifest kartta da sunuluyor; ikonları 404 olsaydı Android "Ana Ekrana Ekle" ikonsuz kalırdı. Kart görüntüsü 387 348 → 402 622 B (P5 600 KB'nin %66'sı); ikonlar 15 090 B (sim3_web bütçesi 24 KB). Açılış kümesi DEĞİŞMEDİ (index.html yalnız ikon-180'i istiyor; B7 sınıyor) |
| 4F-7 | **İkonlar `ikon-uret.py`'den** (stdlib zlib PNG): 180/192/512 any + 192/512 maskable, aynı iki sinüs, kenar yumuşatmalı, **paletli PNG** (RGB'nin ~⅓'ü); maskable ölçeği hesaplanıyor (çizim güvenli dairenin, yarıçap %40, içinde). Renkler style.css KOYU bloğundan; manifest aynı üreteçten (`id`/`scope`/`start_url` = `/`, `lang` tr) | sim3_web 6p ikonları ve manifesti bayt bayt yeniden üretip karşılaştırıyor; B7 PNG'yi çözüp ölçü, zemin ve maskable güvenli bölgesini ölçüyor. Eski manifestin teması (#161b21) index.html'in theme-color'ından (#101821) ayrışmıştı — artık aynı (B7) |
| 4F-8 | **SW kayıt hatası kullanıcı günlüğüne değil konsola** (`console.warn`, `_sw.hata`) | Panel kabuksuz da tam çalışır; günlüğe yazmak çevrilmemiş metin kilidine (AY3) yeni metin eklerdi |

Açık (4F dışı): kurulu PWA penceresinde gerçek "Yükle" akışı ve görev çubuğu ikonu elle denenmedi (başlıksız
Edge'de kurulum istemi yok; `getInstallabilityErrors` boş olması ölçüt); köprü `--lan` ile IP'den açılırsa
güvenli bağlam değil → kabuk yok (beklenen).

## Güvenlik (kalıcı kurallar)

- `p0` her yeni katmanda serbest (LAN salt okuma, vekil, imza zorunluluğu): her birine iddia + mutasyon.
- E ve Q komutları köprüden ASLA (yalnız USB konsolu); `EK` satırı (64 onaltılık) yayınlanmaz/arşivlenmez.
- `N?` asla gönderilmez. Parolalar dosyaya/kayda yazılmaz. Aracı adresi depoya yazılmaz.
- `gizlilik_dogrula.py`'nin iki açığı kapatılır: parola deseni, `C:/…` eğik çizgili mutlak yol.
- `Ez1` yalnız köprü eşleştikten sonra ve kullanıcıya önerilerek.

## Doğrulama

B22a (`test_kopru.py`) ve B72 genişler; gerekirse yeni zincir adımı (ör. `test_pc.py`). Tarayıcı testleri
`uretim/tarayici.py` ile (her koşudan sonra Edge sızıntısı = 0). Her iddiaya yalanlayan mutasyon (`4A:` … önekli).
Gerçek kart kabulü 4G: Ö3 uzun kopukluk + bayt karşılaştırma, Ö5 trafik kaydında parola/K/MQTT bilgisi yok,
4 canlı izleyici + köprü.
