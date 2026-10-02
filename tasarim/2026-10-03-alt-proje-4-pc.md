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
