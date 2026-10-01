# 1D — Eşleştirme + imzalı istekler + cihazdan saat (tasarım)

Üst tasarım: [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md):
- **§6 Güvenlik** (bağlayıcı): eşleştirme PBKDF2 + HMAC-SHA256, `K` iki tarafta türetilir; güvenilir cihaz listesi; her istek imzalı; `p0` serbest; parola sıfırlama yalnız USB.
- **§5 Zaman:** "yoksa eşleşmiş cihaz saati verir".
- **§13** bu dilime iki ayrıntı bırakıyor: eşleştirme mesaj sırası ve PBKDF2 tur sayısı (ölçüt: telefonda < 1 s, kartta < 1 s).

Önceki dilimler: 1A-1 … 1C-4 (DEVIR 5.12.65–5.12.71). Açık işler: [1-acik-isler.md](1-acik-isler.md).

> **Karar yetkisi:** kullanıcı 2026-10-01 öğlen "ben hâlâ inceleyemiyorum, sen devam
> et, ancak kritik bir şey varsa hemen commit atma" dedi. Bu dilim **güvenlik**; aşağıdaki
> kararlar benim, ama "⚠ Onay bekleyen kritik kararlar" bölümündekiler kullanıcı onaylamadan
> `main`'e girmez. Bütün 1D işi yerel `1d-eslestirme` dalında; push edilmez.

## Amaç

Bugün kartın komut ucu oturum jetonu + HTTP Basic Auth ile korunuyor. Ama:
- web parolası **her komutta açık** gidiyor;
- ölçüm verisi, kayıtlar ve kalibrasyon geçmişi parolasız okunabiliyor;
- onay (kaydın kartta silinmesine izin) ağdaki herkesçe yollanabiliyor ([1-acik-isler.md](1-acik-isler.md) "devredilenler");
- internetsiz ağda kartın saati yok: zamanlanmış kayıt kurulamıyor.

1D, §6'daki **cihaz eşleştirmesini** ve **imzalı istekleri** kartta ve PC istemcisinde kuruyor. Eşleşmiş bir cihaz:
- parola göndermeden komut verir, eşitler ve onaylar;
- NTP yoksa karta saat verir.

**Başarı ölçütleri**
- Parola ağa **hiç** çıkmaz: eşleştirme ve sonraki bütün trafik kaydında parola ve `K` bulunmaz.
- İmzalı istek tekrar oynatılamaz: aynı istek ikinci kez ve kart yeniden başladıktan sonra reddedilir.
- Değiştirilmiş gövde, yol, sorgu ya da yöntem reddedilir.
- Geçiş kırılmasız: **bugünkü panel ve araçlar 1D'den sonra da aynen çalışır** (K2).
- C ve Python aynı test vektörlerinde aynı sonucu verir (spec §9).

## Kararlar

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| K1 | **Kapsam:** eşleştirme, imza doğrulama, cihaz listesi, cihazdan saat, zorunluluk anahtarı, PC (Python) istemcisi. **ChaCha20-Poly1305 → 1E** (sırrı taşıyan ilk iş MQTT kimlik bilgileri; ayrıca kartın mbedTLS derlemesinde ChaCha kapalı, `CONFIG_MBEDTLS_CHACHA20_C` yok). JS imzalama → alt proje 2 (`ortak/`), panel → 3, Android Keystore → 5 | Dilim tek başına sınanabilir kalsın. Maliyet: 1E'de RFC 8439 uygulaması ayrıca |
| K2 | ⚠ **Geçiş: zorunluluk anahtarı** NVS `guv`/`zorunlu`, **varsayılan 0**. 0 iken bugünkü davranış aynen sürer (izleme ve okuma açık, komut jeton + parola); **ek olarak** imzalı istek her uçta kabul edilir ve komut için jeton + parolanın yerine geçer. 1 iken imzasız her istek 401, istisnalar K10. Anahtar **yalnız USB seriden**: `Ez1` / `Ez0` | Bugünkü panel ve araçlar imzalayamaz; zorunlu açık gelirse kullanıcı kendi kartına erişemez. Maliyet: alt proje 3/5 gelene dek okuma tarafı bugünkü kadar açık |
| K3 | ⚠ **Parola:** mevcut web parolası (`web_sifre`, `Ns<parola>`); yeni sır yok. Parola yoksa ya da **12 karakterden kısaysa eşleştirme REDDEDİLİR** (kullanıcı onayı 2026-10-01: 10'dan 12'ye — kartta yalnız 20 000 tur sığıyor), kart nedenini söyler | Çevrimdışı tahmin riskine karşı (aşağıda "Onay bekleyen" madde 2). Maliyet: kısa parolası olan kullanıcı eşleştirmeden önce parolasını uzatmalı |
| K4 | **Türetme:** `P = PBKDF2-HMAC-SHA256(parola, tuz, tur, 32)`. Tuz: kart başına 16 B rastgele, NVS `guv`/`tuz`, ilk kullanımda üretilir. Tur: NVS `guv`/`tur`, protokolde taşınır (sonradan değiştirilebilir; yalnız yeni eşleştirmeleri etkiler). **Varsayılan tur kartta ölçülerek** < 1 s seçilir (hedef ≥ 50 000). *(Kart tezgahı 2026-10-01:)* Ölçüldü: hedefe ulaşılamıyor. PBKDF2 artık HMAC'in ipad/opad SHA durumunu bir kez kurup her turda kopyalıyor (`sha_kopya`; tur başına 2 sıkıştırma). Kartta 85 → ~38 µs/tur; en hızlı yolla bile 50 000 tur 1.9 s. **Varsayılan 20 000 = 764 ms** (25 000 = 956 ms, pay %4, WiFi yükünde aşar). `Et` sabit sınama parolasıyla ölçer ve P'nin ilk 8 baytını basar: tezgah kartın PBKDF2'sini `hashlib` ile karşılaştırır. `Ez`/`Em` P'yi yalnız ayar bozukken yeniden hesaplatır; eskiden her seferinde çekirdek 1'i 4.7 s donduruyordu. *(Son inceleme sonrası:)* Kart `P`'yi **çekirdek 1'de** hesaplar: açılışta, `Ns`'den, `Er`'den sonra, pil testi sürmüyorken. PBKDF2 çekirdektedir (`guv_pbkdf2`) ve 1000 turda bir zamanlayıcıya pay verir. **Web yolunda PBKDF2 yok:** yüksek tur web görevinde bekçiyi tetikleyip kartı yeniden başlatabilirdi. Tur sınırları: kartta `Er` 10 000…200 000, `Et` 1 000…200 000 (pil testinde ikisi de reddedilir). **İstemci 10 000'in altını ve 1 000 000'un üstünü REDDEDER** | §13 ölçütü. Telefondaki saf JS süresi alt proje 2'de ölçülür; tur protokolde taşındığı için o zaman ayarlanır. Son incelemenin kritik bulgusu: tur ve tuz karttan geliyordu; sahte kart `tur=1` dayatıp kanıtı toplasaydı parola HMAC hızında tahmin edilirdi |
| K5 | **Mesaj sırası** (3 adım, hepsi `Host` + `X-Olcum` ister): ① `GET /eslestir/bilgi` → `{kimlik, acilis, tuz, tur, zorunlu, misafir, saat}`. ② `POST /eslestir/baslat` gövde `ad=<≤24>&nc=<32 hex>` → `{eno, nk}`: aynı anda tek bekleyen eşleştirme, 60 s geçerli. ③ `POST /eslestir/kanit` gövde `eno=..&kanit=<hex>`. `kanit = HMAC(P, "OK1-istemci" ‖ kimlik ‖ nk ‖ nc ‖ ad)`. Doğruysa kart cihaz numarası `n` atar, `K`'yı saklar ve `{n, kart_kanit}` döner; `kart_kanit = HMAC(P, "OK1-kart" ‖ kimlik ‖ nk ‖ nc ‖ n)`. İstemci kart kanıtını doğrulamadan `K`'yı kullanmaz (karşılıklı) | İstemci kanıtı önce gelir: kart kanıtı önce gelseydi, kanıt istemeden herkes parola tahmini için malzeme toplayabilirdi. "OK1-" sürümlü alan ayırıcı |
| K6 | **Cihaz anahtarı:** `K = HMAC(P, "OK1-anahtar" ‖ kimlik ‖ nk ‖ nc ‖ n)`. İki taraf ayrı türetir; ağa çıkmaz. Kart cihaz kaydında saklar | §6 |
| K7 | ⚠ **Deneme sınırı:** yanlış kanıttan sonra yeni eşleştirme `2^k` s bekler (k ≤ 8, ≈ 4 dk). Açılışta sıfırlanır. Her ret seri konsola yazılır. Eşleştirme **her zaman açık**; fiziksel düğme penceresi yok. *(Son inceleme sonrası:)* **Eski Basic-Auth yolu da aynı biçimde sınırlı:** yanlış web parolası `2^k` s bekletir (429). Yalnız `Authorization` başlığı varken sayılır; doğru parola sıfırlar | Çevrimiçi parola tahminini yavaşlatır. Basic-Auth sınırsız kalsaydı eşleştirmenin sınırı boşa çıkardı. Maliyet: fiziksel erişim şartı olmadığından ağdaki saldırgan deneme yapabilir (yavaşça); yanlış parolayı ezberlemiş bir tarayıcı birkaç saniye 429 alır |
| K8 | **Cihaz listesi:** en fazla 8 cihaz. NVS ad alanı `cihaz`, blob `c1…c8`: `K` 32 B, ad ≤ 24 B, eklenme unix, son görülme unix. "Son görülme" saatte en fazla bir kez yazılır (NVS aşınması). Liste doluysa eşleştirme reddedilir. Seri komutlar: `E?` liste, `Ex<n>` sil, `Ex!` hepsini sil. İmzalı web: `GET /cihaz/liste`, `POST /cihaz/sil` (`n=`; cihaz kendini de silebilir). Parola değişince (`Ns`) cihazlar **kalır**; kart "eski cihazları çıkarmak için `Ex!`" der | §6 "tek dokunuşla kaldırma", "parolayı değiştir ayrıca bütün cihazları çıkar seçeneği" |
| K9 | **İmza:** başlıklar `X-Cihaz: n`, `X-Sayac: s`, `X-Imza: hex`. Kanonik metin: `"OK1\n" ‖ yöntem ‖ "\n" ‖ yol[?sorgu] ‖ "\n" ‖ acilis ‖ "\n" ‖ s ‖ "\n" ‖ hex(SHA-256(gövde))`. Sorgu: argümanlar geliş sırasıyla `ad=değer` (URL-çözülmüş), `&` ile; ham gövde (`plain`) ve `_c _s _i` hariç. İmzalı POST gövdesi `text/plain` olmalı; form kodlamalı imzalı istek 400 alır (çünkü WebServer gövde argümanlarını sorguya karıştırır). EventSource başlık taşıyamaz: imza `_c _s _i` sorgu argümanlarında | §6 "yöntem ‖ yol ‖ açılış-nonce'u ‖ sayaç ‖ gövde özeti" |
| K10 | **Tekrar koruması:** `acilis` her açılışta 16 B rastgele, hex. `/eslestir/bilgi`'de ve her 401 yanıtında `X-Acilis` başlığında verilir. Sayaç cihaz başına, açılış başına. Kart **64'lük kayan pencere** tutar, çünkü eşzamanlı istekler sırasız gelebilir; pencerenin gerisi ya da tekrar → 401. İstemci sayacı diskte saklar ve `max(son + 1, unix_ms)` kullanır, böylece süreç yeniden başlasa da tekdüze kalır | §6. Maliyet: pencere 64'ten fazla eşzamanlı istek kaldırmaz |
| K11 | **İstisnalar** (zorunlu açıkken de serbest): `p0` ve `?` (bugünkü gibi), `/eslestir/bilgi`, `/eslestir/baslat`, `/eslestir/kanit`, `/` (panel sayfası; veri taşımaz). **Misafir izleme** NVS `guv`/`misafir`, varsayılan 0 (§6). Açıkken zorunlulukta `/akis` ve `/pil` imzasız okunur. Seri komut: `Em1` / `Em0`. Host beyaz listesi ve `X-Olcum` korunur | §6 |
| K12 | **Cihazdan saat:** imzalı `POST /saat` gövde `unix=<n>`. **Yalnız kartın NTP saati yoksa** kabul edilir; NTP gelince NTP kazanır. `n ≥ 1 700 000 000` olmalı (1C-4'teki alt sınır). Saat kaynağı `N?` ve `/eslestir/bilgi`'de görünür | §5. Böylece internetsiz ağda zamanlanmış kayıt (1C-4) kurulabilir |
| K13 | **PC istemcisi** `kopru/imza.py`, yalnız stdlib (`hashlib.pbkdf2_hmac`, `hmac`, `secrets`, `ctypes`): eşleştirme, imzalama, sayaç ve anahtar saklama. Windows'ta anahtar **DPAPI** ile kullanıcı hesabına bağlı şifrelenir; DPAPI yoksa dosya izni + uyarı. Komut satırı: `python kopru/imza.py esles --host <ad> --ad <cihaz adı>` (parola `getpass` ile sorulur, yankılanmaz). `kayit_esitle.py` eşleşmişse imzalı yolu, değilse bugünkü jeton + parola yolunu kullanır | §6 "PC'de DPAPI (ctypes)" |
| K14 | **Platformsuz çekirdek `guvenlik.h`:** cihaz tablosu, eşleştirme durumu, deneme sınırı, kanonik metin, kayan pencere, doğrulama. Kriptografi bir işlev tablosundan gelir (`GuvKripto`: sha256, hmac, pbkdf2, rastgele): kartta mbedTLS (donanım SHA), AVR testinde sınama amaçlı küçük bir SHA-256. NVS 1A-2'deki `KayitNvs` deseniyle. AVR'de açılıştan açılışa sınanır | 1A-2 / 1B / 1C-4 deseni: mantık ESP32'siz sınanır |
| K15 | **Test vektörleri** tek dosyada: `uretim/vektor_guvenlik.json`. İçerik: RFC 4231 HMAC-SHA256, PBKDF2-HMAC-SHA256 bilinen vektörleri, K5'in kanıtları, K6 anahtarı, K9 kanonik metin ve imza örnekleri. C (AVR), Python ve alt proje 2'nin JS'i aynı dosyayı kullanır | §9 |
| K16 | **Firmware sürümü** `A3-1D`. Kayıt biçimi değişmez (sürüm 2) | — |
| K18 | *(Son inceleme sonrası)* **Sağlamlık:** kriptografi hatası (mbedTLS ayırma vb.) bir karar değildir. İmza **reddedilir**, eşleştirme `KRIPTO` hatası döner. Ayar kaydı **var ama okunamıyorsa** kart fail-closed davranır: imza zorunlu olur, `Ez0`/`Ez1` ayarı yeniden yazar. Rastgele sayılar RF (WiFi) açıldıktan **sonra** üretilir, `Ep` WiFi kapalıyken reddedilir: ESP32'nin RNG'si RF'siz yalancı-rastgeledir ve açılış değeri her açılışta aynı olsaydı tekrar koruması çökerdi. Köprü, satır sonu ya da kontrol karakteri gömülü komutu reddeder (`?\nEz0` E süzgecini atlatıyordu) | Bağımsız son incelemenin bulguları |
| K17 | ⚠ **USB'den eşleştirme:** seri komut `Ep<ad>`. Kart rastgele 32 B `K` üretir, cihazı listeye ekler ve `K`'yı **yalnız seri porta** basar: `EK <n> <hex>`. Bu satır web'e ya da SSE'ye **asla** yansıtılmaz (B72 iddiası). PC istemcisi: `imza.py esles-usb --port COM6 --ad <ad>`. Parola kullanılmaz | USB erişimi zaten tam denetim demek (kart yeniden yüklenebilir; §6'da da parola sıfırlama yalnız USB). PC araçları zaten USB'den bağlanıyor. Tezgahın parolayı bilmeden sınayabilmesini de sağlar. Maliyet: USB'ye erişen herkes cihaz ekleyebilir — bugün de tam erişimi var |

## ✅ Kritik kararlar — ONAYLANDI (kullanıcı, 2026-10-01: "önerilerinin hepsi olur")

Her maddede önerilen yol kabul edildi:
1 geçiş kipi (zorunluluk kapalı başlar) ·
2 PAKE şimdilik yok — uzun parola + eşleştirme kendi ağında; PAKE ileride, imza katmanı değişmez ·
3 en kısa parola **12** ·
4 eşleştirme hep açık, deneme sınırlı — BOOT düğmesi kutunun içinde kaldığı için düğme penceresi yok;
  USB eşleştirmesi (K17) var ·
5 NTP yokken cihazdan saat ·
6 USB'den parolasız eşleştirme ·
7 imzalı istemciler gelince `Ns` ile web parolasını değiştir, `E?` ile cihazlara bak.

Aşağıdaki metin kararların gerekçesi olarak duruyor.

1. **K2 — geçiş.** Zorunluluk kapalı başlar. Okuma tarafı alt proje 3/5 gelene dek bugünkü kadar açık kalır. Kart bu durumu açılış afişinde ve `N?`'de "imza zorunlu DEĞİL" diye söyler.
2. **Bilinen zayıflık** (bu §6'nın kendi tasarımından gelir, 1D'nin bir hatası değil). PBKDF2 + HMAC eşleştirmesi bir **PAKE değildir**:
   - Eşleştirme anında WiFi'yi dinleyen biri `tuz`, `tur`, `nk`, `nc` ve istemci kanıtını görür. Bunlarla parolayı **çevrimdışı** tahmin edebilir; tahmin başına maliyet bir PBKDF2.
   - Ağda aktif bir saldırgan sahte kart gibi davranıp aynı malzemeyi toplayabilir.
   - Önlemler: ≥ 10 karakter parola (K3), yüksek tur (K4), eşleştirmeyi kendi WiFi'nde yapmak.
   - ⚠ *(Kart tezgahı 2026-10-01)* "Yüksek tur" ölçülünce zayıfladı: kartta < 1 s'ye yalnız **20 000** tur sığıyor (hedef 50 000'di). Çevrimdışı tahmin, planlanandan 2.5 kat ucuz. Bu, PAKE sorusunu ve parola uzunluğunu (K3: 10 karakter yeterli mi, 12+ mi) daha önemli yapıyor.
   - Kesin çözüm bir PAKE'dir (SPAKE2+ ya da SRP-6a): pasif dinleyici hiçbir şey öğrenmez. Bedeli kartta ve saf JS'de eliptik eğri ya da büyük sayı kodu; iş birkaç kat büyür.
   - **Önerim:** §6'daki tasarım + K3 + K4. Kullanıcı PAKE isterse yalnız K5–K6 değişir (imza katmanı aynı kalır).
3. **K3** — 10 karakterden kısa parola eşleştirmeyi reddeder.
4. **K7** — eşleştirme her zaman açık (deneme sınırlı). Fiziksel düğme penceresi yok. Düğme istenirse ESP32 kartındaki BOOT (GPIO0) çalışma anında okunabilir.
5. **K12** — NTP yokken eşleşmiş her cihaz saat verebilir.
6. **K17** — USB'den parolasız eşleştirme (§6'da yok; eklendi). USB'ye erişen herkes cihaz ekleyebilir. Bugün de karta tam erişimi olduğu için yeni bir yetki doğmuyor; yine de kullanıcı bilsin.
7. **Bugünkü web parolası zaten ağda AÇIK gitti** (son inceleme): eski panel her komutta Basic-Auth ile parolayı gönderiyor. Pasif dinleyiciye karşı madde 2'deki analiz ancak Basic-Auth kullanımı bitince geçerli olur. **Öneri:** alt proje 3/5 imzalı istemcileri getirip `Ez1` açılınca USB'den `Ns<yeni parola>` ile parolayı değiştir, `E?` ile cihaz listesini gözden geçir, tanımadığın cihazı `Ex<n>` ile sil. Eşleşmiş cihazların anahtarları parola değişince **geçerli kalır** (K8).

## Akış

**Çekirdek 0 (web görevi):** bütün uçlar ortak bir kapıdan geçer: `guv_kapi(uç)`:
1. Host beyaz listesi.
2. İstisnalar (K11).
3. İmza varsa doğrulanır: başarılıysa istek yetkilidir; başarısızsa 401 + `X-Acilis`.
4. İmza yoksa: zorunlu 0 ise bugünkü kurallar (açık okuma; komut için jeton + parola), zorunlu 1 ise 401.

Eşleştirme uçları `guvenlik.h` durum makinesini çağırır. Cihaz tablosunu ve NVS'i
çekirdek 0 tutar. Seri komutlar (`E…`, `Ez`, `Em`) çekirdek 1'den bir istek kuyruğuyla
gelir; tek yazar kuralı 1C-4'teki gibi.

**İmzalı komut:** `/komut` imzalıysa jeton ve Basic Auth aranmaz.

**Saat:** `/saat` imzalı ve NTP yoksa `settimeofday` çağrılır, kaynak "cihaz" diye işaretlenir. NTP eşitlenince kaynak "ntp" olur.

## Doğrulama

- **B71 (AVR, `SENARYO_GUV`)** — emüle NVS, sınama SHA-256'sı, açılıştan açılışa:
  - vektörler: HMAC, PBKDF2 (düşük tur), kanıt, `K`, kanonik metin, imza; C == Python;
  - eşleştirme baştan sona; yanlış kanıt → deneme sınırı (`2^k`); 60 s zaman aşımı; liste dolu; sil;
  - imza: doğru → kabul; tekrar, pencere gerisi, değişik yöntem / yol / sorgu / gövde / açılış → ret;
  - yeniden başlamada cihaz tablosu kalıcı; açılış nonce'u yeni; eski sayaç reddedilir.
- **B72 (kaynak + Python):**
  - uç listesi ve her ucun kapıdan geçtiği;
  - istisnalar; zorunlu 0'da bugünkü yolların aynen durduğu;
  - seri `E` komutları; `A3-1D`;
  - Python `imza.py` vektörleri; `kayit_esitle` imzalı yolu (sahte kart); DPAPI dalı.
- **Mutasyon:** her yeni iddiaya bir yalanlayıcı.
- **Tezgah** (gerçek kart, `--guvenlik`). ⚠ Kullanıcının web parolası bilinmiyor ve
  okunmaz/değiştirilmez. Bu yüzden parolalı eşleştirmenin **başarı** yolu kartta
  sınanamaz: AVR + vektörlerle sınanır, kartta kullanıcı dener. Tezgahta:
  - PBKDF2 süre ölçümü → varsayılan tur;
  - USB'den eşleştirme (K17); `EK` satırının SSE akışında GÖRÜNMEDİĞİ dinlenerek doğrulanır;
  - parolalı eşleştirmenin RET yolu: yanlış kanıt → ret + deneme sınırı;
  - imzalı `/kayit/veri`, imzalı `/komut` ile `Go` onayı (parolasız);
  - tekrar / yanlış imza / bozuk gövde / değişik yol reddi;
  - yeniden başlatma sonrası eski açılış ve sayaç reddi;
  - `Ez1`: imzasız okuma 401, `p0` serbest, imzalı okuma çalışır; `Em1` misafir izleme; `Ez0` / `Em0` ile geri;
  - imzalı trafikte `K` dizgisi aranır, bulunmamalı;
  - sonunda test cihazları silinir (`Ex<n>`), zorunlu 0, kart `main`'deki firmware'e geri yüklenir.

## Kapsam dışı

- ChaCha20-Poly1305 ve sır aktarımı (1E).
- JS imzalama (alt proje 2), paneldeki eşleştirme ekranı (3), Android Keystore (5).
- PAKE (yukarıda madde 2; istenirse ayrı karar).
- HTTPS (§ tasarım tablosu: reddedildi).
