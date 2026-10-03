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
- **WiFi'de skop yakalaması** köprüde hâlâ `tB → t` + ASCII dökümü SSE'den topluyor; kartın akış kuyruğu (48 satır) büyük dökümde satır düşürürse yakalama "kırpık" (503). Kartın `/skop.bin`'ini imzalı vekil etmek PC11 / 4D.
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
- Panelde eşitleme durumu (4D).

### 4E uygulama kararları (2026-10-03)

Köprü süreci kartın MQTT bildirimlerine **yalnız abone** olup Windows bildirimi gösteriyor
(`kopru/pc_bildirim.py`: `Mantik` saf karar katmanı + `PcBildirim` ipliği; `kopru/windows_bildirim.py`;
metinler `kopru/bildirim_metin.py`; `pc.bildirim_kur`). Sınama: B72.Q16 = `uretim/test_bildirim.py`
"4E" bölümleri (sahte aracı `127.83.41.7` + imzayı doğrulayan sahte kart + gerçek `WifiKart`; karar katmanı
sahte saatle), B22a "4E" (4 iddia: `pc.py` bağlantısı, yerel satır, `/bildirim/durum`). Her iddianın `4E:`
önekli yalanlayan mutasyonu var (59). Testte ve zincirde GERÇEK toast yok (`OLCUM_TOAST_YOK=1`, sahte çıkış).

**PC13 denemesi (ölçüldü, bu PC: Windows 11 26200, PowerShell 5.1, 2026-10-03 sabahı; iki deneme bildirimi).**
`powershell.exe -EncodedCommand` + `[Windows.UI.Notifications.ToastNotificationManager, …, ContentType =
WindowsRuntime]` stdlib Python'dan çalışıyor: `Show()` 0.19 s (alt süreç dahil, ikinci çağrı 0.19 s),
`Notifier.Setting = Enabled`. **Yerinde güncelleme:** aynı `Tag='deneme'` + `Group='olcum'` ile ikinci
`Show` sonrası `History.GetHistory` **1 kayıt**; Bildirim merkezinde tek kart, yeni metin ("2/2 — aynı
bildirim yerinde güncellendi"). **Kaynak adı:** AUMID `OlcumKarti.Kopru`, `HKCU\Software\Classes\
AppUserModelId\OlcumKarti.Kopru` altına `DisplayName = "Ölçüm kartı"` + `IconUri` (panel ikonu) yazılınca
Bildirim merkezinde **"Ölçüm kartı" + dalga ikonu** (ekran görüntüsüyle doğrulandı); Başlat menüsü kısayolu
ya da paket GEREKMEDİ. **Tarayıcı / panel kapalıyken** (o an hiç `msedge` süreci yok) bildirim çıktı.
⚠ Kullanıcıda **"Rahatsız Etmeyin" açıktı**: açılır pencere (banner) görünmedi, bildirim doğrudan Bildirim
merkezine düştü — Windows ayarı, kod değil (tezgah kalemi: öncelikli uygulamalara "Ölçüm kartı").
Tepsi simgesi (`Shell_NotifyIconW`) **yapılmadı**: pencere + mesaj döngüsü ister, ucuz değil; çıkış zaten
`Kopruyu Durdur.bat` / `pc.py --durdur`. Deneme bildirimlerinden biri ("2/2") Bildirim merkezinde duruyor.

**Gerçek aracı (EMQX, 2026-10-03, kart A3-4B WiFi'de, köprü kapalıyken ayrı betikle, sahte çıkış, geçici
önbellek dizini, hiçbir sır basılmadan):** imzalı `/bildirim/bilgi` 1 kez alındı, önbellek `OKB1` zarfı,
aracıya yalnız abone bağlanıldı, **retained `durum` 3.4 s'de çözüldü** (`c=1 k=1 f=A3-4B`), çözülemeyen
mesaj 0; veri dizininde, durum satırlarında ve `/bildirim/durum`'da aracı adresi/kullanıcı/parola/önek/
anahtar YOK (bellekteki değerlerle tarandı). Yayın yapılmadı, karta komut gitmedi.

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| 4E-1 | **Bildirim yolu WinRT toast** (`powershell.exe` alt süreci, `CREATE_NO_WINDOW`, ayrı iplik + kuyruk); kaynak adı HKCU AUMID kaydıyla (ilk bildirimde, ikon çalışma ağacından veri dizinine KOPYALANIR); metin XML'e kaçırılıp YALNIZ base64 olarak betiğe girer, etiket/grup `[a-z0-9-]{1,16}` | PC13 ölçümü. Base64: bildirim metni (kartın şifreli yükünden gelir) PowerShell komutu olarak yorumlanamaz. Geri alma: `HKCU\Software\Classes\AppUserModelId\OlcumKarti.Kopru` anahtarını silmek. Windows dışı: bildirim akışa durum satırı (`YokBildirim`) |
| 4E-2 | **MQTT ipliği köprü sürecinde** (`pc.bildirim_kur`, `--bildirim-yok`); bilgi kartın WiFi kolundan, **canlı akış ve eşitlemeyle AYNI `Cihaz` + sayaç kilidi** (`WifiKart.dogrula` + `imzali_ac`); `--wifi-yok`'ta da kurulur (yalnız önbellekle çalışır) | 4B-12/4C-2'nin kuralı: ayrı nesne aynı ms'de aynı sayacı üretir → 401. Kart MQTT'si köprünün yukarı-akışından bağımsız |
| 4E-3 | **PC14 önbellek:** `/bildirim/bilgi` yanıtı AYNEN `…\olcum-karti\bildirim\<kart kimliği>.okb` (fsync + atomik); açılışta ÖNCE önbellek (kart erişilemezken de abone olunur). Yeniden alma YALNIZ: (a) zarf çözülemedi, (b) CONNACK 4/5, (c) kart çevrimiçi görünürken `durum` konusu **180 s sessiz** — ve yalnız kart erişilebilirse; (a)/(b) en sık 60 s'de bir, (c) 30 dk'da bir. Erişilemezse eldeki bilgiyle devam | (c) eklendi: `QR!` **öneki de değiştirir** — eski konu yalnız susar, çözme hatası hiç olmaz (eski retained durum eski anahtarla çözülür). Kart 60 s'de bir durum yolluyor; vasiyet geldiyse sessizlik beklenen, tetiklemez |
| 4E-4 | **Sır disiplini:** çözülmüş adres/kullanıcı/parola/önek/anahtar yalnız bellekte; hata metinleri istisnadan DEĞİL sınıftan (`hata_sinifi`: ssl hatası aracı adını taşır); her durum metni ayrıca bellekteki sırlardan arındırılır; iplik istisnayı yakalar, iz yazmaz; `/bildirim/durum` önek dahil hiçbir sır taşımaz. Diskte yalnız `OKB1` zarfı + son `(a, n)` | Ö5 kapsamı (MQTT bilgisi). Test veri dizinini, durum satırlarını, `/bildirim/durum`'u, bildirim metinlerini ve konsolu parola/adres/kullanıcı/önek/anahtar/K için tarıyor |
| 4E-5 | **Sınıflar ve ayar:** `kopuk`, `bitti`, `dolu`, `esik`, `yeniden_basladi` (§8'in beşi) + `kacirilan`, `deneme`; `ayar.json` `"bildirim": {...}` (true/false, yoksa açık), `"bildirim_dil": "tr"|"en"`. Bozuk dosya / biçimsiz değer → o sınıf AÇIK (+ uyarı). Yazma `pc_bildirim.ayar_yaz` (CLI `python kopru/pc_bildirim.py ayar kopuk=0 dil=en`): 4C anahtarlarıyla **birleştirir**, bozuk dosyanın üstüne YAZMAZ | 4C'nin tersi güvenli taraf: kaybolan bildirim, fazla bildirimden pahalı. Panelde ayar arayüzü YOK (sonraki dilim; panelin "Bildirimler (MQTT)" metni kartın `Q` ayarı hakkında, hâlâ doğru — değişmedi) |
| 4E-6 | **"Karttan haber yok" yalnız kayıt sürerken** (son bilinen kayıt durumu `k ∈ {2 KAYIT, 4 BEKLIYOR}`; yerel `G` satırı ile aracının `durum`'undan HANGİSİ daha yeniyse); tek bildirim, etiket `baglanti`: vasiyet/`{c:0}` → kart yerelde görünüyorsa (son kart satırı ≤ 15 s) **"Ev interneti koptu — kart çalışıyor"**, değilse "Karttan haber yok"; durum değişince AYNI bildirim güncellenir; kart dönünce "yeniden bağlandı — kayıt sürüyor/sürmüyor". Retained `{c:0}` her yeniden bağlanmada tekrar açılmaz | §8. Yerel erişim = köprünün yukarı-akışından satır gelmesi (USB ya da WiFi). Köprü açılırken retained `c:0` ve kayıt bilinmiyorsa bildirim yok |
| 4E-7 | **Yalnız yerel yol** (aracı yok / bağlı değil / kart hiç durum yollamadı): kayıt sürerken kart satırları **20 s** susarsa "Karttan haber yok — yerel bağlantı da koptu" (aynı etiket), dönünce "yeniden bağlandı" | Kartta MQTT ayarsızken de PC uyarır |
| 4E-8 | **PC16 yineleme:** MQTT içinde `(a, n)` (son 1024); yollar arası aile + `a` (iki tarafta biliniyorsa) + `oturum` (iki tarafta biliniyorsa; yoksa ≤ 120 s) + 15 dk pencere. Ayrıntı sırası yerel `G` geçişi (1) < `kayit_bitti`/`dolu` (2) < `pil_bitti` (3): daha ayrıntılı ikinci haber AYNI bildirimi **sessizce** (`SuppressPopup`) günceller, eşit/az ayrıntılı düşer. `kayit_bitti` sebep 2 → `dolu` sınıfı, sebep 5 → `yeniden_basladi` ("<tür> kesildi, son haber <saat>"), sebep 4 → `pil_bitti` ile birleşir | Bellek dolunca kart `kayit_bitti(2)` + `dolu` + yerel `G 3` üretir → tek bildirim. Yerel yol kartın kendiliğinden bastığı `G` satırından (yeni kanal yok); köprü `satir_oku`'yu sarar, `Kopru.dongu` değişmedi |
| 4E-9 | **`basladi`:** yalnız `devam=1` bildirilir ("kayıt kesildi ve sürüyor"); düz açılış bildirim değil; kesilen oturum ardından gelen `kayit_bitti` sebep 5 ile | Her açılışta bildirim gürültü olurdu; spec §8 "kayıt kesildi ve sürüyor / pil testi şu saatte kesildi" |
| 4E-10 | **PC15 kaçırılanlar:** kalıcı oturum YOK (temiz oturum, rastgele kimlik); aynı açılışta `n` boşluğu, yeni açılışta `1..n-1`, köprü yeniden açılınca diskteki son `(a, n)`'den — "N olay kaçırıldı" tek bildirim (etiket `kacirilan`, birikerek); önceki çalışmada görülen olay yeniden bildirilmez | Olayların içeriği kayıp (aracı saklamaz); ayrıntı eşitlenen kayıtlarda. EMQX'in kalıcı oturumu ölçülmeden kullanılmadı |
| 4E-11 | **`GET /bildirim/durum`** (yalnız bu bilgisayar, yerel ağ 403): `etkin`, `bilgi` (yok/önbellek/karttan), `abone`, `kart_cevrimici`, `kayit_suruyor`, `yerel_erisim`, son mesaj/olay zamanı ve türü, `kacirilan`, `baglanti_bildirimi`, `ayar`, `dil`, `bildirim_yolu`, `mesaj` (arındırılmış). Kurulmadıysa `etkin:false` + `neden` | 4C-7 deseni; sonraki panel bölümü buradan beslenir |
| 4E-12 | **Metinler** `bildirim_metin.py`: `sebep.*` / `pil.durum.*` / `oturum.tur.*` `ortak/src/sozluk.js` ile AYNI anahtar ve metin (test sözlüğü okuyup karşılaştırır), bildirime özgüler `bld.*`; firmware'in her olay adı (`bildirim.h`'den okunur) için TR+EN | Panel ve PC aynı kelimeyi kullansın; Python'dan JS modülü okumak yerine kopya + eşitlik testi (stdlib, derleme yok) |

**PC18 (Ö4'ün PC karşılığı): hedef 10 s, kabul 15 s — ÖLÇÜLMEDİ.** Aracı parolaları yalnız kullanıcıda;
tezgah kalemi B22a listesinde ("4E: PC'de Windows bildirimi + Ö4"): kayıt sürerken kartın fişini çek →
"Karttan haber yok" bildirimine kadar süre (10 tekrar; aracının ilanı ~7.5 s + PC), geri tak → aynı
bildirim "yeniden bağlandı", modem WAN'ı çek → "Ev interneti koptu", `Qt` → "Deneme bildirimi".

Açık (4E dışı / sonraki):
- Panelde bildirim bölümü (durum + aç/kapa; `POST` ucu YOK — yazma şimdilik CLI ve `ayar.json`).
- Tepsi simgesi (çıkış menüsü) yapılmadı; "Rahatsız Etmeyin"de banner çıkmaz (kullanıcı ayarı); `scenario="urgent"`
  denenmedi.
- Ö4 PC ölçümü (yukarıda), E7 (`basladi` kaybı) gerçek aracıda yeniden gözlenmedi.
- Yerel yol yalnız `G` satırından: kartın açılış afişi ("yeniden başladı") yerel olarak bildirilmiyor (MQTT'den geliyor).
- `esik` yalnız MQTT'den (eşik değeri kartta); yerel `G`'nin `onaysiz` alanından türetilmedi.

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
