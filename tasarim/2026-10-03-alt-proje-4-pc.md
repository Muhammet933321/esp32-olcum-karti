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
| 4A-10 | ~~**`.satir` arşivinin yeri DEĞİŞMEDİ**~~ (4C-9'da `%LOCALAPPDATA%\olcum-karti\satir\`'a taşındı, eskisi kopyalanır) (`kopru/arsiv/`, gitignore'da); 4A'da depo dışına taşınan yalnız çökme izi (`%LOCALAPPDATA%\olcum-karti\arkaplan-hata.txt`, `OLCUM_PC_DIZIN`) | PC5 yeni arşivle (4C) birlikte; şimdi taşımak kullanıcının mevcut B35 arşivini "kaybolmuş" gösterirdi (PC12 onu salt okuma eski arşiv yapıyor) |
| 4A-11 | **Başlangıç kısayolu araçları var, KURULMADI:** `kopru/Otomatik Baslat Kur.bat` / `Otomatik Baslatmayi Kapat.bat` → `otomatik-baslat.ps1` (gerçek `pythonw.exe` yolunu `sys.executable`'dan bulur; WindowsApps takma adı değil). Kısayol, kurulumun yapıldığı çalışma ağacının `pc.py`'sini gösterir | Kurulum kullanıcının kararı. Birden çok çalışma ağacı var — betik yolu ekrana yazar |
| 4A-12 | **`sunucu_kur` her sunucuya özel işleyici alt sınıfı** kurar (`Isleyici.kopru` paylaşılan sınıf niteliği değil) | Aynı süreçte iki sunucu (test, ölü tekrar) birbirinin köprüsünü eziyordu |
| 4A-13 | **`gizlilik_dogrula.py`:** düz eğik çizgili mutlak yol (her sürücü harfi + `Users`/`home`/`Muhammet`), ters eğik çizgili desenler de her sürücü harfine genişledi; gömülü parola = adı parola/sifre/password ile BİTEN alana yazılmış ≥ 4 karakterlik düz metin. Deneme değeri işareti: `sinama`/`deneme`/`test`/`ornek`/`gizli`/`dogru`/`yanlis`/`sahte`, 4+ tekrar, sözlük anahtarı (`es.parola`) ya da tam değer beyaz listesi (iki kayıt, gerekçeli); üretilmiş çapraz vektör JSON'ları atlanır (üreten `.py` taranıyor). Bulunan değer EKRANA BASILMAZ | "kart", "1234" gibi gerçek parolada da geçebilecek parçalar bilerek işaret değil. Yeni test parolası işaret sözcüğü taşımalı |

**4A inceleme düzeltmeleri (2026-10-03, bağımsız inceleme + çürütücüler).** Her biri önce B22a / T4A'da
kırmızı görüldü, her iddianın `4A:` önekli yalanlayan mutasyonu var.

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| 4A-14 | **Çapraz köken (CSRF) kapısı:** `/akis`, `/skop.bin`, `/skop/liste`, `/skop/al`, `/devral`, `/kapat` ve `p0` dışındaki `/komut`, `Sec-Fetch-Site` varsa ve `same-origin`/`none` değilse ya da `Origin` varsa ve `http://<Host>` değilse **403**. Başlıksız istek (curl, araçlar) kabul | `<img src="http://127.0.0.1:8770/skop.bin">` özel başlık ekleyemez ama GET köprüye ulaşır: başka bir 127.0.0.1 portundaki sayfa (stok-takip, geliştirme sunucusu) karta `t` yollatıyor ve köprü arka planda açıkken **sürücülüğü** kapıyordu (gerçek panel `surucu:false`). Başsız Edge'de T4A ölçüyor: istekler köprüye ulaşıyor, karta hiçbir şey gitmiyor, sürücü/jeton yok, sonra açılan panel sürücü |
| 4A-15 | **`/skop.bin` kendi `t`sini `/komut`'un kapısından yollar:** `X-Olcum` + `komut_izinli("t", jeton)` (sürücü varsa yalnız sürücü). Bekleme yolu (komut zaten `/komut`'tan geçti, `skop_kurulu`) başlık istemez; döngü dışı istemci o yolda da 403 | Panel köprüde `/skop.bin` çekmiyor (`skopArsivVar` → `t` `/komut`'tan) — `app.js` değişmedi, kartın sunduğu panel etkilenmedi. `tezgah_skop_arsiv.py` artık `X-Olcum` yolluyor |
| 4A-16 | **`gun` yalnız `YYYY-AA-GG`** (ASCII rakam): HTTP'de 400, `Arsiv.gun_yolu`'nda da `ValueError` + çözülen yol arşiv dizininde mi; `gunler()` tarih dışı `.satir`'ı listelemez | Windows'ta mutlak/UNC `gun` arşiv dizinini EZİYORDU: `//saldirgan/pay/x` → `exists()` SMB bağlantısı (NTLM özeti), makinedeki başka `.satir` okunabiliyordu. ⚠ `resolve()` denetimi regex'in arkasında erişilemez (ayrı mutasyonu yok) |
| 4A-17 | **Her açılışta ilk (yarım) satır atılır** (`SeriKart._baglanti_basladi`); köprü her (yeniden) bağlantıda (`OtoSeriKart.baglanti_no`) süzgeç penceresini **en az** `GIZLI_PENCERE` yapar, asla kısaltmaz | Kart AP parolasını `"AP parolasi (yalniz USB): "` + parola + `"\r\n"` diye üç parçada basıyor; port aradan açılırsa ilk "satır" işaretsiz parolaydı ve süzgeçten geçip akışa/arşive gidiyordu. PurgeComm yok: ilk satırı atmak yetiyor (en kötü 1 + 2 ölçüm satırı kaybı) |
| 4A-18 | **Otomatik seçim kartı DOĞRULAR:** aday sırası kartın kendi VID:PID'i (CH343 `1A86:55D3`) önce; açılan portta 2 s pasif dinleme (`D`/`K` satırı), gelmezse yalnız serbest `?` ve 2 s `A menzil=` beklenir. Kart değilse port **kapatılır**, 120 s ya da aygıt çıkarılana dek yeniden açılmaz; doğrulamada okunan satırlar akışa geri verilir. Elle `--port` doğrulanmaz | VID'i uyan ilk CH34x (Arduino Nano klonu, USB-TTL) arka planda tutuluyordu: Arduino IDE "Access denied", Nano çıktısı kart verisi diye arşive, sonra takılan kart hiç seçilmiyordu. **`N?` asla.** Gerçek kartta (COM6, CH343) 2026-10-03: pasif `D` satırıyla 0.06 s'de doğrulandı, karta hiçbir şey yazılmadı |
| 4A-19 | **Süzgeç işaretleri daraltıldı:** `EK \d+(?: \|$)` (firmware'in tek biçimi `"EK %u "`), AP parolası `\(yalniz USB\)` ya da bölünmüş `AP parolas` yalnız ardından ` (` / satır sonu gelirse | `F` yanıtı "… YUKSEK 1.50" ve `NA` onayı "* AP parolasi kaydedildi" işarete takılıp kendisiyle birlikte 2 ölçüm satırını da yutuyordu. Bölünmüş değer testleri aynen yeşil |
| 4A-20 | **Port adı büyük harfe** (`--port com7` → `COM7`) | Küçük harf 303A reddini atlatıyordu |
| 4A-21 | **Köprü yoklamaları vekilsiz** (`pc_ayar.yerel_istek`, `ProxyHandler({})`) | Windows `<local>` istisnası 127.0.0.1'i kapsamıyor: vekil açıkken `zaten_calisiyor` köprüyü göremiyor, ikinci kopya "port başka programda" diyordu |
| 4A-22 | **Durdurma yolu:** `POST /kapat` (yalnız döngü, `X-Olcum`, aynı köken) + `pc.py --durdur` + `kopru/Kopruyu Durdur.bat`; mesajlar artık "Görev Yöneticisi > pythonw.exe" demiyor | Aynı yoldan stok-takip'in arka plan sunucusu da `pythonw.exe` — yanlışı öldürülüyordu |
| 4A-23 | **Küçükler:** ölü tekrar bitince `KayitKart.satir_oku` bekler (çekirdek %100 yanıyordu; `yaz` beklemeyi keser) · `OtoSeriKart.yaz/kapat` ve `SeriKart` Read/Write/Close aynı kilitte · konsolda (sessiz değilken) kart durum satırları da basılır (`--port COMx` hatası görünür) · kart açılışı döngü ipliğinde, HTTP hemen hizmet verir · POST gövdesi erken ret yanıtından önce okunur (Windows'ta RST → istemcide `ConnectionAborted`) | ⚠ `SeriKart` kilidinin belirlenimci testi yok (gerçek tanıtıcı gerekir); `OtoSeriKart` sıralaması sınanıyor |
| 4A-24 | **Başlangıç kısayolu YALNIZ ana çalışma ağacından** (`projeler/olcum-karti`), ASLA geçici dal ağacından (git worktree) kurulur. `otomatik-baslat.ps1 -Kur` `.git` DOSYA ise (worktree) reddeder (`-Zorla` ile geçilir) | Ağaç silinince kısayol ölü bir `pc.py`'yi gösterir, köprü iz bırakmadan ölür (`arkaplan-hata.txt` bile yazılmaz) |

**Bilerek düzeltilmeyenler (inceleme bulguları, gerekçeli):**
- **Makine adıyla gelen yerel ağ istemcisi** (`desktop-x.local:8770`) Host denetiminde 403 alıyor — `p0` dahil. Telefonlar IP ile geliyor (4A-3); `p0`'ı Host katmanından muaf tutmak kullanıcı kararı (kalıcı kural "p0 her katmanda serbest" ile gerilim). Açık.
- **`gizlilik_dogrula.py` desen boşlukları** (`ap_parolasi = "…"`, `Ns<parola>`, `(yalniz USB): <değer>`, `EK n <64 hex>`, alt-dize beyaz listesi) — bu turun kapsamı dışında; ayrı iş.
- **Ölü tekrar 8770'te açılabiliyor** ve `zaten_calisiyor` onu canlı köprüden ayırmıyor (kökteki `Kopru Baslat.bat` ipucu `--http-port` vermiyor) — açık.
- **`pc.py`'nin modül düzeyi `import`'ları** `--sessiz`'in `try`'ı dışında (ImportError iz bırakmaz) — açık.
- **`yukle.py`** köprü portu tuttuğunda arduino-cli'nin genel hatasını veriyor (`acma_hatasi`'ndan geçmiyor); metinler artık "önce `Kopruyu Durdur.bat`" diyor, `yukle.py`'ye ön denetim eklenmedi — açık.
- **Açılış yarışının** `OSError` dalında ikinci deneme yok; kart açılışı döngü ipliğine alındığı için pencere küçüldü — kalan risk küçük.

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

### 4B uygulama kararları (2026-10-03)

Köprü kartla WiFi'den **eşleşmiş cihaz** olarak konuşuyor (`kopru/kart_wifi.py`: `WifiKart`, `SecmeliKart`);
firmware `A3-4B` (PC8 + D5 #12 kök düzeltmesi). Sınama: B72.W1–W12 (sahte kart, bağımsız imza doğrulayıcı),
B22a "4B" (seçim + `pc.py`), B22b 2d/3b/4a, B72 D0/F74/F77/F81c/F88/F91/F25, B6 (ikilide `event: kopru` /
`POST /kopru` yok). Her iddianın `4B:` önekli yalanlayan mutasyonu var. Gerçek kartta henüz koşulmadı.

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| 4B-1 | **Firmware: `/kopru` kaydı, ikinci `/akis` reddi ve CORS izni KALKTI** — on-uçuş (`OPTIONS`) işleyicisi `onuc_sayfa` ve `/komut` OPTIONS kaydı da gitti; kartta hiçbir kökene `Access-Control-Allow-Origin` verilmiyor. Tek `/akis` reddi 4 yuvanın dolması (`event: dolu`) | PC8 + spec §5. On-uçuş işleyicisi zaten yalnız kayıtlı köprüye izin veriyordu (kayıt yokken izinsiz 204 → tarayıcı isteği göndermiyordu): kayıt kalkınca ölü koddu. Maliyet: tarayıcıdan karta çapraz kökenli istek (ör. ileride `http://localhost` kökenli bir WebView) imkânsız — doğal HTTP ya da köprü gerekir (alt proje 6'da not) |
| 4B-2 | **Eski iddialar gerekçesiyle güncellendi** (spec §10): sim3_web 2d ×2 ("köprü kayıtlıysa ret", "kayıt RAM'de") → "ikinci `/akis` kabul, tek ret yuva dolu" + "`/kopru` yok"; 3b ("köprü ucunda X-Olcum") → "`/kopru` hiçbir yöntemle kayıtlı değil"; 4a ("ACAO yalnız kayıtlı köprüye") → "hiçbir kökene ACAO / OPTIONS yok"; B72 F81c, F88, F74 tablosu; B6 `event: kopru` BEKLENEN → BULUNMAMALI | Eski iddialar kalkan kuralı kodluyordu; yerine kuralın yokluğunu ölçen iddialar |
| 4B-3 | **D5 #12 kökü: gizli satırlar TEK yazımla** — `EK` satırı `"EK %u %s\r\n"` tek tamponda, tek `Serial.ham`; AP parolası satırı (`N?` ve AP açılış afişi) tek yerde, `ap_parolasi_bas` (işaret + parola + CRLF bir `String`'de, tek `ham`); iki tampon da yazımdan sonra silinir. Köprünün gizli satır süzgeci (4A-5) derinlemesine savunma olarak KALDI | Üç ayrı `ham()` arasına IDF günlüğü girerse sır işaretsiz ayrı satıra düşüyordu. AP parolası `NA` ile ~170 karaktere dek olabildiği için sabit tampon yerine `String` (kırpma, CRLF kaybı yok). ⚠ Tek `uart_write` IDF günlüğüyle kesişmezliği gerçek kartta ölçülmedi (tezgah) |
| 4B-4 | **Sürüm `A3-4B`**; derleme: flaş 1 414 210 → 1 412 758 B (−1 452), DRAM 81 724 → 81 684 B (−40: `kopru_adres[40]` + zaman damgası) | `KAYIT_FW_SURUM` her firmware değişikliğinde değişir (B72.F25); `_ESP_DRAM_SON_OLCUM` gerekçesiyle güncellendi |
| 4B-5 | **Panelin `kopru` olay dinleyicisi (`app.js`) DURDU** | A3-4B onu hiç göndermez; eski firmware'de (A3-1F ve önce) panel hâlâ "köprüye git" uyarısını gösterir. Kaldırmak B7'ye dokunurdu, kazancı yok |
| 4B-6 | **Kart kimliği (D5 #18) her (yeniden) bağlanmadan ÖNCE**: açık `/eslestir/bilgi` → `kimlik` (16 onaltılık değilse ret — dosya adına gider) → cihaz dosyası `<kimlik>.json` (cihaz dizininde) ya da `--cihaz` ile verilen dosya; dosya yoksa ya da içindeki kimlik uymuyorsa `/akis` AÇILMAZ, komut GÖNDERİLMEZ, mesaj hangi kimlik/hangi dosya olduğunu ve `imza.py esles` komutunu söyler | Yanlış karta (iki kart, mDNS karışması) imzalı komut gitmesin; kullanıcı neden bağlanmadığını bilsin |
| 4B-7 | **`p0` WiFi'de İMZASIZ, `X-Olcum`'lu, kimlik/cihaz denetimine TAKILMADAN**; `SecmeliKart` önce etkin yolu, olmazsa ötekini dener; ikisi de olmazsa açık hata | Kart `p0`'ı serbest bırakıyor (`komut_serbest`); DURDUR'u imza/sayaç/eşleşme sorunu geciktiremez (Ö7). Tanımadığı bir karta `p0` göndermenin zararı yok |
| 4B-8 | **Akış döngüsü**: her denemede `bilgi` (kimlik + `acilis` tazeleme) → `imza.akis_url` ile YENİ adres (D5 #17) → `http.client` ile SSE; bekleme 1, 2, 4, 8, 16, 30 s; veri gelen bağlantıdan sonra 1 s'ye döner; okuma zaman aşımı 40 s (kart 15 s'de bir `: kalp`). `kimlik` olayı (kartın oturum jetonu), `id:`, `retry:`, yorumlar TAŞINMAZ; `event: dolu` söylenir. 401 → "cihaz kartta silinmiş olabilir — `imza.py esles`" | İmzalı adres tek kullanımlık (sayaç): aynı adres 401 alır. Kartın web çekirdeği seri: istek fırtınası olmasın. Köprü tarayıcılarına kendi jetonunu verir |
| 4B-9 | **Saat (R11)**: `bilgi.saat` ≠ 1 (0 yok, 2 cihaz) ise her bağlantıda akış açıldıktan sonra BİR KEZ imzalı `/saat` (unix = PC saati); 409 (arada NTP geldi) sessiz | Zamanlanmış kayıt ve kayıt zaman damgaları NTP'siz kartta da doğru olsun; NTP varken kart reddediyor zaten |
| 4B-10 | **USB önceliği (`SecmeliKart`)**: USB'de doğrulanmış kart (`OtoSeriKart.bagli`) varsa canlı akış/komut USB'den ve WiFi bağlantısı KAPATILIR; yoksa WiFi. Geçiş `* kopru: …` durum satırıyla (akışa, arşive DEĞİL); geçişte WiFi kuyruğundaki satırlar atılır; her geçiş/yeniden bağlanma `baglanti_no`'yu artırır → gizli satır penceresi 2 satır (USB ile AYNI kural) | İki yukarı-akış aynı satırı iki kez arşive yazmasın; USB yerel ve kimliksiz (fiziksel erişim) olduğu için tercih. Maliyet: her WiFi (yeniden) bağlanmada ilk 2 ölçüm satırı düşer (~0.4–2 s); SSE yarım satır üretmediği için pencere WiFi'de yalnız derinlemesine savunma |
| 4B-11 | **WiFi istekleri vekilsiz** (`ProxyHandler({})`, akış `http.client`) | Kart yerel ağda ya da kendi AP'sinde; sistem vekiline giden istek imzalı trafiği dışarı taşırdı (4A-21 ile aynı ders). Ölçülmedi (vekilli makine yok) |
| 4B-12 | **Sayaç kilidi**: aynı `Cihaz` nesnesini akış ipliği (`akis_url`) ve HTTP ipliği (`ac`) kullanıyor; ikisi tek kilitte | Aynı milisaniyede iki imza aynı sayacı alırsa kart birini tekrar diye reddederdi. ⚠ 4C'de eşitleyici aynı süreçte aynı kilidi paylaşmalı |
| 4B-13 | **PC5 cihaz dizini** `pc_ayar.cihaz_dizini()`: `OLCUM_CIHAZ_DIZIN` > `OLCUM_PC_DIZIN\cihaz` > `%LOCALAPPDATA%\olcum-karti\cihaz`. Göç: çalışan ağacın `kopru/.cihaz/*.json`'u, yeni dizinde hiç cihaz dosyası yoksa BİR KEZ **kopyalanır** (taşınmaz) ve söylenir (`imza.py`, `pc.py`, `kayit_esitle.py`, `bildirim.py` girişlerinde). K basılmaz | Kopyalama: eski ağaçtaki araçlar ve geri dönüş çalışmaya devam eder; DPAPI kullanıcı hesabına bağlı olduğundan dosya kopyası geçerli |
| 4B-14 | **Etkileşimsiz eşleştirme** `imza.py esles … --parola-ortamdan`: parola YALNIZ bayrakla `OLCUM_PAROLA`'dan, okunur okunmaz sürecin ortamından silinir; ekrana/dosyaya yazılmaz; değişken yoksa karta hiç istek gitmeden çıkış. Bayrak yoksa ortam OKUNMAZ (getpass; istem artık "WEB parolası — WiFi parolası DEĞİL" diyor) | Gerçek kart sınaması betikle yapılabilsin, ama unutulmuş bir ortam değişkeni sessizce kullanılmasın. Kullanıcı WiFi ve web parolasını daha önce karıştırmıştı |
| 4B-15 | **`imza.ac` / `akis_url` (D5 #18)**: açılışı `bilgi`'den alırken kimlik denetimi (`KartKimligiHatasi`); 401 + yeni `X-Acilis` yolunda ilk yanıt kapatılır; `acici` parametresi (köprü vekilsiz açıcı verir). İstek SIRASI değişmedi | B73 çapraz vektörleri (Python ↔ `ortak/src/imza.js`) bayt bayt aynı kalsın. JS istemcisinde kimlik denetimi YOK (açık) |
| 4B-16 | **`pc.py` seçenekleri**: `--kart-host` (> `OLCUM_KART_HOST` > `olcum.local`), `--cihaz DOSYA`, `--wifi-yok` (yalnız USB = 4A davranışı), `--usb-yok` (yalnız WiFi: COM portu HİÇ açılmaz); ikisi birlikte reddedilir | Sahada kartın AP'si (`192.168.4.1`) ya da IP verilebilsin. `--usb-yok`: kart PC'nin USB'sinden beslenirken WiFi yolu sınanabilsin ve köprü açıkken tezgah araçları / `yukle.py` COM portunu kullanabilsin (PC3 çekişmesine ikinci çözüm) |
| 4B-17 | **Testler gerçek karta gitmez**: `test_kopru.py` `OLCUM_KART_HOST=127.0.0.1:9` (kapalı port) ve geçici cihaz dizini kuruyor | `pc.calistir` artık USB yoksa WiFi'yi deniyor; test makinesinin ağındaki gerçek kart (ve kullanıcının cihaz dizini) testlere karışmasın |

Açık (4B dışı / sonraki dilimler):
- **WiFi'de skop yakalaması** köprüde hâlâ `tB → t` + ASCII dökümü SSE'den topluyor; kartın akış kuyruğu (48 satır) büyük dökümde satır düşürürse yakalama "kırpık" (503). Kartın `/skop.bin`'ini imzalı vekil etmek PC11 / 4D — 4D'de YAPILMADI (vekil beyaz listesi `/pil`, `/kal/liste`, `/kunye.json`; açık).
- ~~**Kayıt verisi WiFi'den** (PC6'nın ikinci yarısı) ve eşitleyicinin aynı sayaç kilidini paylaşması 4C.~~
  4C'de yapıldı (aşağıda 4C-2).
- `ortak/src/imza.js`'te kimlik denetimi yok (panel); kart her uçta `_i` sorgu imzasını kabul ediyor (D5 #17'nin ilk yarısı).
- Gerçek kartta: tek `ham()` yazımının IDF günlüğüyle kesişmediği, 4 izleyici + köprü, köprünün kablo çekip takmada USB ↔ WiFi geçişi (aşağıdaki tezgah listesi orkestratörde).

### 4C uygulama kararları (2026-10-03)

Köprü süreci kartın kayıtlarını arka planda diske eşitliyor (`kopru/arka_esitle.py`: `ArkaEsitleme`;
`pc.esitleme_kur`). Sınama: B72.A1–A12 (sahte kart, bağımsız imza doğrulayıcı, sanal saat), B22a "4C"
(7 iddia: `pc.py` bağlantısı, `/esitleme/durum`, `.satir` göçü). Her iddianın `4C:` önekli yalanlayan
mutasyonu var (38).

**Gerçek kartta ölçüldü (2026-10-03, A3-4B, WiFi, `--onaysız`, geçici veri dizini).** Kartta 44 oturum,
sıra 59043–61276 (öncesi temizlenmiş, boşluk 1–59042 olarak raporlandı), 2234 kayıt, 1 268 956 B.
Köprünün arşivi kartın `/kayit/liste`'siyle aynı: son sıra 61276, 44 oturum; farklı ayarlarla alınan altı
tam eşitlemenin hepsi bayt bayt aynı. Kartın onayı (61276) değişmedi (onay gönderilmedi). Canlı akış
(köprünün `/akis`'i, `D`/`K` satırları) ölçüm sırasında:

| Parça arası | Süre (1.27 MB) | Akış satır/s | p95 aralık | en uzun aralık |
|---|---|---|---|---|
| boşta (eşitleme yok) | — | 4.7–5.1 | 208–222 ms | 213–861 ms |
| yok (arka arkaya) | 15.6 · 18.9 · 19.7 s | 4.87 · 4.96 · 4.91 | 225–266 ms | 470–2365 ms |
| sabit 20 ms | 28.1 s | 4.84 | 229 ms | 827 ms |
| sabit 50 ms | 33.3 · 36.2 s | 4.93 · 4.94 | 226–233 ms | 512–2101 ms |
| **istek başları arası ≥ 100 ms (seçilen)** | 28.5 s; uçtan uca `pc.py` 29.6 s | 4.94 | 230 ms | 2183 ms |

Hiçbir düzende satır kaybı yok (hız boştakine eşit); 0.5–2.4 s'lik tekil boşluklar her düzende (ve bir kez
boşta 861 ms) görülüyor — eşitlemeye bağlı değil. Bir imzalı istek PC tarafında zaten ~100–120 ms
sürüyor (her istekte yeni TCP + ad çözümü + sayaç dosyası DPAPI + fsync), kartın web çekirdeği bunun
~44 ms'inde meşgul.

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| 4C-1 | **Zamanlama:** ilk tur hemen; her yukarı-akış (yeniden) bağlantısında (`baglanti_no` değişince — USB ya da WiFi); sonra **120 s**'de bir (`--esitleme-aralik` / ayar, en az **30 s**). Hata: **15 s**'den 2 katlanarak **600 s** tavan; başarıda sıfırlanır. **Mutlak taban:** iki tur BAŞLANGICI arası en az **10 s** (yeniden bağlanma fırtınası dahil). Tek iplik, tek tur = sıralı istekler | Kart en yüksek hızda (ayrıntılı kip) ~3.1 KB/s yazar: 120 s ≈ 370 KB ≈ 46 parça, birkaç saniye; olağan hızda çok daha az. 503 (`kayit mesgul`, tarama) saniyeler içinde geçer → 15 s; kart geri gelince yeniden bağlanma tetiği 10 s tabanla hemen eşitletir, tavan yalnız "kart erişilir ama eşitleme hata veriyor" (sıra geri gitti vb.) durumunu seyreltir. Sanal saatle sınanıyor (A11a–c) |
| 4C-2 | **Aynı `Cihaz` nesnesi + aynı sayaç kilidi:** `WifiKart` cihaz dosyası başına TEK nesne tutar (`_paylasilan`; yeniden eşleştirmede n/K/kimlik değişince yenisi), `dogrula()` (bilgi → kimlik → dosya → kimlik uyuşması) akışla ortak; eşitleme bütün imzalı isteklerini `WifiKart.imzali_ac` ile kilitte yapar. **İmzalı `/akis` adresinin üretimi + isteği + yanıt başı da kilitte** (`_akis_iste`) | 4B-12'nin açığı. İki nesne aynı milisaniyede aynı sayacı üretir → kart 401 (A9, donuk saatle belirlenimci). Kilit yalnız imza üretimini kapsasaydı: yavaş bağlantıda (`olcum.local` mDNS çözümü) araya giren eşitleme isteği büyük sayaçla önce ulaşır, akışın eski sayacı 64 ms penceresinin dışında kalır → 401 (A10, 0.4 s geciktirilmiş bağlantıyla ölçülüyor). Bedel: yavaş bağlantı sırasında eşitleme bekler |
| 4C-3 | **Parça ≤ 8192 B** (kartın `KAYIT_VERI_AZAMI`); **hız tavanı: iki parça isteğinin başlangıcı arası ≥ 100 ms** (≤ 10 istek/s, ≤ 80 KB/s) — sabit ara değil, istek zaten o kadar sürdüyse bekleme yok | Ölçüm (yukarıdaki tablo): canlı akış hiçbir düzende aksamıyor; sabit ara yalnız süreyi uzatıyor (50 ms → 2×). Tavan bugün tam eşitlemede ~%45 süre ekliyor (1.27 MB: ~20 → ~29 s; dolu 11.4 MB bölüm ~3 → ~4.5 dk), 120 s'lik olağan turda < 1 s. Korur: PC tarafı hızlanırsa (keep-alive, tek bağlantı) kartın seri web çekirdeği telefonlara / `p0`'a yine pay bırakır. Spec §11 riski ölçülerek kapatıldı |
| 4C-4 | **Onay (PC9):** varsayılan VERİR — `Go<sira>` imzalı, ANCAK `kayitlar.kyt` fsync + atomik `durum.json`'dan SONRA (A2: kart onayı aldığı anda dosyada o sıraya kadar her bayt ve durum yazılmış), kart `X-Onay` ile doğrular. **64 parçada bir + tur sonunda** (kısa turda TEK `Go`). Kapatma: `--onaysiz` ya da `ayar.json` `"esitleme_onay": false`; ayar dosyası okunamaz / değer true-false değilse **ONAYSIZ** (güvenli taraf) ve söylenir | Her `Go` kartın akışına `* G onay istegi` satırı basıyor; parça başına onay 1.27 MB'de 155 satır + 155 istek olurdu. Onay geri alınamaz sonuç doğurabilir (kart dolunca o veri silinebilir; eşitlenmemiş telefon göremez) — şüphede onaysız. **Gerçek karta ilk onaylı koşu bu dilimde YAPILMADI** (orkestratör kararı) |
| 4C-5 | **Arşiv yeri (PC5):** `%LOCALAPPDATA%\olcum-karti\arsiv\<kart kimliği>\akis-<akış kimliği>\` (`kayitlar.kyt`, `durum.json`, `kalibrasyon.json`, `esitle.kilit`); `OLCUM_PC_DIZIN` ile taşınır. Akış kimliği her turda imzalı `/kayit/liste`'nin `kimlik`'i; değişince (biçim / sıfırlama) YENİ alt dizin, eskisi bayt bayt yerinde, durum satırı söyler | `kayit_esitle` zaten akış kimliği değişince DURUYORDU (eski akışa eklemez); arka planda durmak yerine yeni dizin — iki akış asla karışmaz (A5). `kalibrasyon.json` akış dizininde: o akışın kayıtlarıyla birlikte okunur (NVS geçmişi biçimle silinmez; her akış dizininde bir kopya — küçük dosya) |
| 4C-6 | **Durum satırları** `* esitleme: N yeni kayit, son sira S; onay gitti (kart dogruladi)` / `onay gitmedi (onaysiz)` / boşluk / kalibrasyon yedeği; hata/atlama `! esitleme: … — T s sonra yeniden`. Yeni kayıt yokken sessiz; aynı hata bir kez. Köprüden TARAYICILARA, `.satir` arşivine GİRMEZ (A8 — `pc.esitleme_kur` bağlantısı üzerinden) | `* kopru:` satırlarıyla aynı kural (4A-8). Her 120 s'de bir "yeni kayıt yok" panel günlüğünü doldururdu |
| 4C-7 | **`GET /esitleme/durum`** (köprü): yalnız bu bilgisayardan (yerel ağ 403), JSON: etkin, onay, aralık, son sonuç/mesaj, son deneme/başarı (unix), yeni/toplam kayıt, son sıra, kartın son sırası, oturum sayısı, arşiv baytı, onay gitti/doğrulandı, **arşivin göreli adı** (`arsiv/<kart>/akis-<n>`), sonraki denemeye kalan s. Mutlak yol YOK. Eşitleme kurulmadıysa `etkin:false` + sebep. Panel arayüzü değişmedi (4D) | 4D'nin "bu PC" görünümü buradan beslenecek. Döngü dışı istemciye arşiv bilgisi gerekmez |
| 4C-8 | **USB (PC6):** kayıt verisinin seri yolu yok. USB yukarı-akış etkinken de eşitleme kartı **WiFi'den** dener (kart aynı anda ağdaysa çalışır); WiFi'den doğrulanamazsa tur ATLANIR: `! esitleme: atlandi — kart yalniz USB'den erisilebilir; … (USB seri dokumu 4C-2, ertelendi)` (A7). `--wifi-yok`: eşitleme kurulmaz, sebep konsolda ve `/esitleme/durum`'da. `--esitleme-yok` kapatır | 4C-2 (seri döküm) ERTELENDİ — kullanıcı "WiFi kapalı, yalnız USB" (`N0`) durumunu isterse |
| 4C-9 | **`.satir` günlüğü (PC12 bağlamı) taşındı:** varsayılan `%LOCALAPPDATA%\olcum-karti\satir\` (4A-10'un yerine). Açılışta yeni dizinde hiç `.satir` yoksa çalışan ağacın `kopru/arsiv/*.satir`'ı **BİR KEZ KOPYALANIR** (taşınmaz, silinmez) ve konsolda söylenir; başka dosya gitmez | Kullanıcının B35 arşivi ana ağaçta (`projeler/olcum-karti/kopru/arsiv`) — kopya: eski ağaçtaki araçlar ve geri dönüş çalışır. 4A-10'daki "kaybolmuş görünür" endişesi kopyayla yok |
| 4C-10 | **`ayar.json`** (`%LOCALAPPDATA%\olcum-karti\`, isteğe bağlı): `esitleme_onay` (bool), `esitleme_aralik_s` (sayı); bayraklar ayarı ezer | Başlangıç kısayolu `pythonw pc.py --sessiz` çalıştırıyor: onaysız arka plan için kısayolu düzenlemek gerekmesin |
| 4C-11 | **`Esitleyici` ek parametreleri** (`istek`, `parca_arasi`, `uyu`, `durdu`, `onay_parca`) komut satırında eski davranışta (parça başı onay, ara yok); köprü kapanırken tur parçalar arasında durur (yazılan kalıcı kalır, onay doğrulaması atlanır) | `kayit_esitle.py` CLI ve B72.E iddiaları değişmedi |

Açık (4C dışı / sonraki):
- **Gerçek karta ilk ONAYLI koşu** (varsayılan) — onay geri alınamaz sonuç doğurabildiği için orkestratörde.
- **Köprü açıkken `kayit_esitle.py` / `imza.py` CLI'si** aynı cihaz dosyasını AYRI süreçte kullanır: sayaç
  yarışabilir (aynı ms → 401). Kural: önce `pc.py --durdur`. Süreçler arası kilit yok.
- İstek başına PC yükü (~100 ms: yeni TCP + `olcum.local` çözümü + sayaç dosyası DPAPI/fsync): keep-alive ve
  sayaç yazımını seyreltmek tam eşitlemeyi ~2× hızlandırır; 4C-3 tavanı o zaman da kartı korur.
- `--kayit` (ölü tekrar) satırları da `satir\`'a yazar (eski davranış `kopru/arsiv`) — geliştirme aracı.
- Uçtan uca ölçümde akış eşitlemeyle AYNI anda bağlanıyordu (köprü açılışı): pencere hızı 4.29/s, en uzun
  2.3 s — bağlanma payı; akış önceden bağlıyken (tablo) hız boştakine eşit.
- ~~Panelde eşitleme durumu (4D).~~ 4D'de yapıldı (4D-13).

### 4D uygulama kararları (2026-10-03)

Panel PC köprüsünde (`http://olcum.localhost:8770`): Kayıtlar köprünün **disk arşivini** okur ("bu PC'de"),
Ayarlar ve Pil kartın uçlarını köprünün **imzalı vekilinden** alır, B35 satır arşivi Osiloskop'ta **"Eski
arşiv"** başlığı altında. Köprü tarafı yeni modülde (`kopru/vekil.py`); `kopru.py`'de tek dağıtım satırı +
`/durum`'a iki alan. Panel tarafı `ekran/depo_pc.js` (yeni, salt okuma DEPO), `ekran/esitleme.js` (kaynak kararı),
`ekran/kayitlar.js`, `ekran/ayarlar.js`, `app.js` (pil kaynağı), metinler `ortak/src/sozluk_pc.js` (yeni).
Sınama: B22a "4D" (12 iddia: arşiv uçları, parametre / yol içerme, kapılar, salt okuma, vekil imzası, beyaz liste,
ortak sayaç, p0, hata JSON'u, yolsuz yanıt), B7 bölüm 33 (20 iddia), B73 `sozluk_pc.test.js`, **T4D**
`uretim/tarayici_pc_kayit.py` (20 iddia: GERÇEK `sunucu_kur` + GERÇEK `ArkaEsitleme` turu + sahte kart + Edge).
Her iddianın `4D:` önekli yalanlayan mutasyonu var (67).

**Gerçek arşivde ölçüldü (2026-10-03, SALT OKUMA, karta hiçbir istek yok):** kullanıcının
`%LOCALAPPDATA%\olcum-karti\arsiv\<kart>\akis-3995957410` arşivi, yukarı-akışı sahte (`KayitKart`) olan bir köprü
(`sunucu_kur`, bu çalışma ağacından) + başlıksız Edge: Kayıtlar 44 oturumun hepsini "bu PC'de" listeledi (Python
`kayit_bicim` çözümüyle aynı sayı), özet "1 akış · 44 oturum · 1.21 MB", ölçüm #61147 ve ayrıntılı #60089 açıldı
(KPI'lar: 1628 nokta / 9975 örnek, firmware A3-1E / A3-1C4, "bu PC'de (köprü arşivi)"), konsol hatası yok; arşivin
öncesi/sonrası (boy, mtime, sha256) AYNI. Grafiklerde çizgi yok — **veri öyle**: o oturumların bütün noktaları `n=0`,
bütün ayrıntılı örnekleri `V_HATA|I_HATA` (ADS'ler o gün takılı değildi); aynı baytlar tarayıcı kopyasından da boş çizilir.

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| 4D-1 | **Kaynak kararı denetçide** (`EsitlemeDenetcisi.kaynak()`): sayfa döngü kökenindeyse (`localhost`, `*.localhost`, `127/8`, `[::1]`) `/durum` sorulur, `pc_arsiv === true` (ve `kart` alanı) ise kaynak **'pc'**; değilse **'tarayici'** (IndexedDB). **Kart kökeninde (olcum.local, IP) bu karar için İSTEK YOK** — kartın sunduğu panel bayt bayt bugünkü gibi. `/durum`'a `pc_arsiv` (bu istemci döngüden mi) ve `vekil` (döngü + köprünün WiFi kolu var mı) eklendi. Ağ hatası ezberlenmez | Mevcut `kopruda` bayrağı yalnız bağlanınca (`baglan` → `kopruYokla`) doluyor ve yerel ağ istemcisinde de doğru — Kayıtlar bağlantıdan bağımsız açılabiliyor, LAN istemcisi `/arsiv/*`'den 403 alırdı. Karar denetçide olduğu için beş tüketici (Kayıtlar, Karşılaştırma, Pil kaydı, Osiloskop kayıtlı yakalama, Ayarlar) prop zinciri olmadan aynı kaynağı görür |
| 4D-2 | **PC kipinde IndexedDB hiç açılmaz;** liste yalnız PC arşivi (`nerede: 'pc'`), panel eşitlemesi yok (C1 sebebi `'pc'`, kullanıcıya hata kutusu DEĞİL), arşiv onayı kutusu ve kopya silme yok, kartın dizini (`/kayit/liste`) sorulmaz — Kayıtlar'da da Ayarlar > Depolama'da da | PC10: tek yazar Python (`esitle.kilit`'in önlediği iki yazar / iki kopya yok). Köprü kökenindeki IndexedDB'de 4D öncesi de kayıt kopyası olamazdı (C1: köprüde `/kayit/liste` 404) — kaybolan veri yok. `olcum.local` kökenindeki kopyalar ayrı köken (PC10 a) |
| 4D-3 | **Arşiv uçları** `GET /arsiv/liste` · `/arsiv/veri?kart=&akis=&ofset=&bayt=` · `/arsiv/kal?kart=&akis=` (`kalibrasyon.json` ayrı uç: DEPO `kalOku`). Parametre KATI: kart 16 küçük onaltılık, akış/ofset/bayt baştaki sıfırsız ondalık, `bayt ≤ 4 MiB`, bilinmeyen / tekrar eden / eksik parametre 400; çözülen yol arşiv kökünün İÇİNDE (sembolik bağ ve junction dışarı çıkamaz; listede de yok). **Boy = `durum.json`'un `bayt`ı** (kalıcı önek; dosyadaki çökme kuyruğu / süren yazım verilmez), `X-Arsiv-Boy` başlığında. Yalnız bu bilgisayar (yerel ağ 403), yalnız aynı köken (CSRF 403), POST/PUT/DELETE yok, yanıtta mutlak yol yok. Liste oturum özetini Python'dan (`kayit_bicim`, boy+mtime önbellekli) verir; panel kayıtları kendi çözümüyle (`ortak/kayit.js`) kurar | 4A-16 dersi (UNC / mutlak yol arşivi ezer, `exists()` SMB açar). Kalıcı önek: Esitleyici veriyi fsync'ten SONRA `durum.json`'u atomik yazıyor. Panel aynı çözümü kullanınca kayıt görünümü, grafik, dışa aktarma, rapor, Karşılaştırma tarayıcı kopyasıyla AYNI kod yolu. Gerçek arşivde liste çözümü 1.27 MB'de ~50 ms |
| 4D-4 | **Rota anahtarı = kartın kayıt AKIŞ kimliği** (`#/kayit/<no>@<akış>`), kart kimliği satır bilgisinde. İki kartın akış kimliği çakışırsa (olasılık ~2^-32) yalnız en yenisi listelenir | Rota, Karşılaştırma (KR1), Pil ve Osiloskop rotaları tarayıcı kopyasıyla AYNI biçimde kalır. Maliyet: çakışan eski kartın kaydı panelde görünmez (diskte durur) — açık |
| 4D-5 | **`ekran/depo_pc.js`** `ortak/src/esitle.js` DEPO arayüzünün OKUMA tarafı (`durumOku`, `veriBoyu`, `veriOku` (2 MB'lık aralıklarla, `X-Arsiv-Boy`'da durur), `kalOku`); yazan her yöntem (`kilitAl`, `durumYaz`, `veriEkle`, `veriKirp`, `kalYaz`, `kalArsivle`) `CalismaHatasi` ile reddeder — Esitleyici bu depoyla ilk adımda durur, ağa istek gitmez. `esitleme.js` onu **dinamik** `import()` ile, yalnız 'pc' kaynağında indirir; ağ enjekte (`getir`), dosyada `fetch` yok | Kart onu hiç indirmez; Ayarlar'ın IndexedDB zinciri 6 dosya kaldı (AY4/AY5 bütçesi). Kart görüntüsüne girer (~2 KB gzip, SW izin listesi `/ekran/*.js`) — çıkarmak ölü bağlantı riski, kazancı yok |
| 4D-6 | **EU8' (EU8'in yeniden yazımı):** köprüye özgü uçlar (`/durum`, `/devral`, `/skop/liste`, `/skop/al`, **`/arsiv/*`, `/esitleme/durum`**) imza katmanına GİRMEZ — düz `fetch(kartAdres(yol))` (`EsitlemeDenetcisi._kopruGetir`). Kartın uçları (`/pil`, `/kal/liste`, `/kunye.json`) eskisi gibi `kartIstek`'ten | Köprü panelin imzasını doğrulamaz; köprü uçlarını imzalamak sayaç harcar, köprüde anlamı yok. B7 33(e) iki yönü de ölçüyor |
| 4D-7 | **EU9' (EU9'un yeniden yazımı):** köprü `/eslestir/*`'i **VEKİL ETMEZ** — panelin imza katmanı köprüde HER ZAMAN imzasız yola düşer (`/eslestir/bilgi` 404 → `yok`, EU9 kuralı köprü için aynen geçerli); köprü panelin imza başlıklarını (`X-Cihaz/X-Sayac/X-Imza`) TAŞIMAZ, `_c _s _i` parametresi 400; karta kendi eşleşmiş cihazıyla imzalar. "Köprüden 404 = imzasız yol" artık yalnız `/eslestir/bilgi` için: `/kal/liste`, `/pil`, `/kunye.json` köprüde 200 (vekil) ya da **502 + `X-Kopru-Vekil: hata`** (JSON sebep) döner | PC7: panelden köprü için eşleştirme yok (K tarayıcı deposuna düşmesin). Vekil `/eslestir/*`'i taşısaydı panel köprüyü kart sanıp kendi anahtarıyla imzalamaya kalkardı (B22a mutasyonu). Panel 502'yi "kart vermedi" değil "köprü karta ulaşamadı" diye yazar |
| 4D-8 | **Vekil (PC11)** `GET /pil[?sira]`, `/kal/liste`, `/kunye.json` — beyaz liste, yalnız GET; kart doğrulaması (`WifiKart.dogrula`) 30 s yeniden kullanılır; imzalı istek `WifiKart.imzali_ac` (canlı akış ve arka plan eşitlemesiyle AYNI `Cihaz` + sayaç kilidi). Kartın 401'i → **502 `imza`** ("köprüyü yeniden eşleştirin"); 404/503 aynen; doğrulanamadı / erişilemedi / WiFi kolu yok → 502 JSON; mesajlardan mutlak yol çıkarılır (`yolsuz`). Yerel ağa kapalı (403) | 401 aynen geçseydi panel "bu tarayıcı eşleşmemiş" derdi. Donuk saatle (aynı ms) vekil + eşitleme istekleri: 401 yok (B22a). LAN telefonu karta doğrudan bağlanır (PC2) |
| 4D-9 | **`p0` vekilde YOK, her katmanda serbest:** `/komut` → `SecmeliKart` → `WifiKart._p0` imzasız ve **sayaç kilidini beklemeden**. Ölçüldü: kart 1.5 s'de yanıtlayan bir vekil isteği kilidi tutarken p0 0.02 s'de karta ulaştı | Ö7; kalıcı kural "p0 her yeni katmanda serbest" — iddia + iki mutasyon (kilit beklemesi, p0'ın imzalanması) |
| 4D-10 | **`/kunye.json` köprüde = KARTIN arayüz görüntüsünün künyesi** (vekil). Ayarlar etiketi "Kartın arayüz görüntüsü (panel sürümü)" — iki kökende de doğru; künye okunamazsa vekilin sebebi yazılır | 4F-5 bunu öngörmüştü (kabuk sürümü sw.js SURUM'da). Köprünün sunduğu panelin kendi sürümü panelde gösterilmiyor — açık |
| 4D-11 | **Pil (PC11):** köprüde `/durum.vekil` doğruysa pil durum kaynağı **'http'** (`/pil` vekilden — eğri noktaları gelir); vekil 502 dönerse o bağlantıda **'satir'**a döner (sürücüyse `p` → B satırı, PU13) | PU13'te köprüde eğri yoktu. Kart WiFi'de değilse (yalnız USB) eski davranış |
| 4D-12 | **Ayarlar:** kalibrasyon geçmişi köprüde vekilden (kaynak "kartın kalibrasyon geçmişi"); vekil 502 → sebep (JSON) + **bu PC'deki arşivin kopyası** (kaynak 'pc': kart + akış + son eşitleme; IndexedDB açılmaz). Depolama PC arşivini SALT OKUMA gösterir (silme yok, "köprü yazar, panel yalnız okur"). PC metinleri (`sozluk_pc.js`) yalnız köprüde dinamik iner | Kart kökeninde Ayarlar'ın davranışı ve Gelişmiş'in tek dosya kuralı (AY2) aynen |
| 4D-13 | **Köprü eşitlemesinin durumu** (`/esitleme/durum`) Kayıtlar'da canlı bölgede (aria-live) tek satır: son başarılı zaman · son turda / açılıştan beri yeni kayıt · kartın son sırası · **karta onay açık/kapalı** (açıkken "kart, PC'ye kopyalanan eski kayıtları yer gerekince silebilir"); hata (sebep + kaç s sonra), atlandı, kapalı, bekliyor, alınamadı. Ekran açılınca ve Yenile'de; yoklama yok | PC9 uyarısının UI'daki yeri. Sebep metinleri köprünün ASCII Türkçesi (veri olarak) |
| 4D-14 | **PC12:** B35 satır arşivi Osiloskop'ta **"Eski arşiv — köprünün satır günlüğündeki yakalamalar"** (sözlükten, TR+EN; `data-skop-eski-arsiv`), açıklama "salt okuma, dönüştürülmez", yer 4C'nin `olcum-karti/satir`'ı (bayat `kopru/arsiv/<gün>.satir` kalktı); kartın kendi 1C-3 skop günlükleri Kayıtlar'da | R13: iki arşiv yan yana karışmasın |
| 4D-15 | **Metinler:** yeni metinler `ortak/src/sozluk_pc.js` (EU30 deseni: Kayıtlar zinciri statik, Ayarlar yalnız köprüde dinamik; açılışta YOK). Bayat metinler düzeltildi (TR+EN): `kl.neden_imza` (panel eşleştirmesi 3H-2'den beri var → "Ayarlar → Eşleştirme"; PC yolu `kopru/pc.py`), `kl.neden_yok` (köprünün yerel ağ adresi / geliştirme sunucusu; PC arşivi yalnız köprünün bilgisayarında), `kl.neden_usb`, `ay.kal_neden_imza`, `ay.panel`, `ay.panel_yok`. EN'de çevrilmemiş metin kilidi 274 → 272. Açılış kümesi +692 B gzip (209 211 B; EU31 259 803 ≤ 262 144) | Açılış bütçesi dar (EU31 kalan ~2.3 KB): PC metinleri açılışa girseydi ~2 KB daha yerdi. B7 iddiaları bayat metni KODLUYORDU (401 metni, WIG f) — gerekçesiyle yeniden yazıldı |

Açık (4D dışı / sonraki):
- İki kartın akış kimliği çakışırsa eski kartın PC kayıtları listede görünmez (4D-4).
- Köprünün sunduğu panelin kendi sürümü (sw.js SURUM) panelde gösterilmiyor.
- WiFi'de canlı skop yakalaması hâlâ `tB → t` + ASCII dökümü; `/skop.bin` vekili yapılmadı (4B açık maddesi, kapsam dışı).
- Yerel ağ istemcisine panelde "salt okuma" arayüzü yok (4A'dan devreden; 403 metni görünür).
- Vekilin gerçek kartta (imzalı `/kal/liste`, `/pil`, `/kunye.json`) koşusu yapılmadı — bu dilimde karta komut / istek
  gönderilmedi; tezgah kalemi (4G).

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
