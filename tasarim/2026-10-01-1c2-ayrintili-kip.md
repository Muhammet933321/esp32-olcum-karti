# 1C-2 — Ayrıntılı kip: her örnek (tasarım)

Üst tasarım: [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §5
("Ayrıntılı kip (her örnek) 1C'de tasarlanacak"), §11 (flaş duraklaması riski).
Önceki dilim: 1C-1 (DEVIR 5.12.68). Sıra (kullanıcı): 1C-1 → **1C-2** → 1C-3
osiloskop günlüğü → 1C-4 zamanlanmış kayıt.

> **Karar yetkisi:** kullanıcı 2026-10-01 gece "sen devam et ben yatıyorum,
> adım adım devam et" dedi. Bu belgedeki bütün kararlar benim, gerekçeleri ve
> yanlışsa maliyetleriyle. Kullanıcı sonunda kontrol edecek.

## Amaç

Bugün kayıt en hızlı 50/s nokta yazıyor. Her nokta 20 ms'nin ort/min/maks'ı
olduğu için kısa bir olayın **şekli** kaybolur, yalnız varlığı kalır. Ayrıntılı
kip ADS'in ürettiği **her örneği** (~500/s, periyot 2000 µs'e kilitli) ham koduyla
ve zamanıyla kaydeder. Amaç: bir geçici olayın (açılış akımı, röle, motor
kalkışı) dalga şeklini dakikalarca, boşluk bırakmadan kaydetmek.

**Başarı ölçütleri**
- Her örnek ham V ve I koduyla, 4 µs çözünürlüklü zamanıyla kaydedilir.
- Boşluk **gizlenmez**. Örnekler arası süre 16.4 ms'yi aşarsa yeni bir kayıt
  başlar ve boşluk o kaydın başlangıç zamanından açıkça görünür. Düşen örnek
  sayılır ve işaretlenir.
- Hazır alan yeterliyse kayıt boyunca 25 ms'lik dolu sektör silmesi **olmaz**.
- Güç kesilirse kayıp en fazla ~5 s olur (Ö2). Kart yeniden başlarsa kayıt
  sürer; bu bir ölçüm oturumu olduğu için DEVAM alır.
- Mevcut kayıt hızları, pil oturumu ve eşitleme değişmez.

## Kararlar

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| K1 | **Kullanıcı:** 1C'nin ikinci dilimi ayrıntılı kip | — |
| K2 | Ayrıntılı kip ayrı bir oturum türü değil, **ÖLÇÜM oturumu, `hiz_ms = 0`**. `Gb0` başlatır, `Gd` durdurur | Açılışta DEVAM kuralı, eşitleme ve dizin aynen çalışır. Maliyet: `hiz_ms = 0`'ı bilmeyen eski bir okuyucu bu oturumu "nokta yok" diye görür (biçim bunu zaten tolere ediyor) |
| K3 | Örnek başına **6 bayt:** ham V (i16), ham I (i16), 16 bitte 12 bit zaman farkı (4 µs birim) + 4 bayrak (yüksek menzil, V hatası, I hatası, V doydu). **Watt saklanmaz** | Kayıt 3.1 KB/s → dolu bölüm ~60 dk. W, BASLA'daki kalibrasyon kopyası ve faz hizalamasıyla PC'de hesaplanır (`ortak/`, alt proje 2). Maliyet: `ortak/` firmware'in hizalamasını (olcum3.h) aynen taşımalı; ortak test vektörü şart |
| K4 | Yeni kayıt türü **AYRINTI (9)**: 16 B baş + N × 6 B, bir kayıtta en fazla 166 örnek (mevcut 1012 B'lik yazıcı tamponu; RAM eklemez) | ~0.33 s'lik kayıtlar; 5 s boşaltma kuralı zaten sağlanır |
| K5 | Zaman farkı 16.38 ms'yi aşarsa, halka taşıp örnek düşerse ya da menzil dışında bir kesinti olursa (skop yakalaması) **yeni kayıt** başlar. Kaydın `t0_ms`/`t0_us`'u mutlak zamandır, boşluk oradan okunur | Boşluk ayrı bir alan gerektirmeden görünür; sessiz birleştirme yok (Ö1) |
| K6 | Çekirdek 1 → 0 örnek yolu: **kilitsiz tek üretici / tek tüketici halka**, PSRAM'de 4096 örnek (~8 s). Doluysa örnek düşer, sayılır; sonraki kaydın başlığı "önce örnek düştü" der | Mevcut 256'lık nokta kuyruğu 500/s'de ~0.5 s ederdi; FreeRTOS kuyruğu örnek başına maliyetli |
| K7 | **Hazır alan (ön silme):** kayıt yok, skop yakalaması yok ve pil testi yokken, kayıt görevi **onaylanmış** eski sektörleri başın önünde sırayla önceden siler (500 ms arayla, en fazla 480 sektör ≈ 1.9 MB ≈ 10 dk ayrıntılı). Kafa bu sektörlere geçince **silme yapılmaz**, çünkü bu açılışta silindikleri biliniyor (sayaç RAM'de; yeniden başlamada sıfırlanır, yani güvenli) | Dolu sektör silmesi iki çekirdeği 25 ms durduruyor (1A-2'de ölçüldü). Maliyet: onaylanmış eski kayıtlar kartta daha erken silinir; PC'de zaten var (spec §5: bir cihaza kopyalanmış veri silinebilir). Boşta ön silme sürerken canlı ölçüm %5 duraklar (500 ms'de 25 ms), ancak hazır alan dolana kadar (en fazla ~4 dk) |
| K8 | Hazır alan biterse kayıt **sürer**; o andan sonraki 25 ms'lik silme boşlukları kayıtta görünür (yeni kayıt + "silme duraklaması" bayrağı) ve sayılır | Olayın geri kalanını kaybetmek, boşluklu kayıttan kötü |
| K9 | Süre sınırı yok: `Gd` ya da bellek dolunca `BITIR(DOLU)` | YAGNI; zamanlanmış kayıt 1C-4'te |
| K10 | Durum: `G?`'nin ardından yeni **`GA`** satırı: hazır sektör · ayrıntılı örnek · düşen örnek · kayıt içi silme duraklaması. `G` satırı **değişmez** | Mevcut `G` ayrıştırıcıları (tezgah, köprü) bozulmaz |
| K11 | Biçim sürümü **2 kalır**; firmware `A3-1C2` | Yeni kayıt türü, eski okuyucu atlar (B13) |

## Kayıt biçimi

**AYRINTI** `KAYIT_T_AYRINTI = 9`. Başlıkta oturum = etkin ölçüm oturumu.

```
 0 u32 ilk_ornek   (oturumdaki ilk örneğin sırası; DEVAM'da sürer)
 4 u32 t0_ms       (ilk örneğin kart_ms'i)
 8 u32 t0_us       (ilk örneğin micros()'u, alt 32 bit)
12 u16 adet        (N)
14 u8  bayrak      (KA_KAYIP_ONCE 0x01: önceki kayıttan beri örnek düştü ·
                    KA_SILME 0x02: bu kayıttan hemen önce dolu sektör silindi)
15 u8  0
16 + 6·k: i16 v_kod · i16 i_kod · u16 (dt4 << 4 | ornek_bayrak)
      dt4: bir önceki örnekten bu yana 4 µs birimi (12 bit; ilk örnekte 0)
      ornek_bayrak: 0x1 yüksek menzil · 0x2 V hatası · 0x4 I hatası · 0x8 V doydu
```

Bir örneğin zamanı: `t0_us + 4 × Σ dt4`, kart_ms karşılığı `t0_ms`'den. Hatalı
örneğin kodu yine yazılır; bayrak onu işaretler, analiz dışarıda bırakabilir.

## Akış

**Çekirdek 1 (`loop`):** `olcum_al` sonrası, etkin oturum ayrıntılıysa
(`hiz_ms == 0`) örnek halkaya itilir: `{micros, ham_v, ham_i, bayrak}` (8 B).
Nokta biriktirici (noktacı) `hiz_ms == 0`'da zaten kapalı. Skop yakalaması
ADS'i susturduğunda örnek gelmez; sonraki örneğin büyük farkı yeni kayıt açar.

**Çekirdek 0 (kayıt görevi):** halkayı boşaltır → yazıcıda `ky_ayrinti_ornek`
(tampon dolunca, fark 16.38 ms'yi aşınca ya da 5 s dolunca kayıt yazılır).
`kyn_adim` boşta ön silmeyi (`kg_on_sil_adim`) 500 ms arayla yürütür. Ön
silmeye yalnız **izin bayrağı** açıkken dokunulur; bayrağı çekirdek 1 her
turda günceller: kayıt yok, skop yok, pil testi yok.

**Günlük (`kayit_gunluk.h`):**
- `g->hazir`: başın önünde bu açılışta silinmiş, boş sektör sayısı.
- `kg_ilerle`, bir sonraki sektör hazır sayılıyorsa silmez ve sayacı azaltır.
- `kg_on_sil_adim`: başın önündeki bir sonraki sektör onaylıysa (ya da boşsa)
  onu düşürür, siler ve sayacı artırır; onaysız veriye asla dokunmaz.
- Sayaç şu durumlarda sıfırlanır: açılışta (`kg_ac`), mantıksal biçimlemede,
  bir yazma hatasında.

## Doğrulama

- **B71 (AVR):**
  - AYRINTI paketi C == Python.
  - Halka: tek üretici/tek tüketici sınırları, taşmada sayma ve bayrak.
  - Yazıcı:
    - 166 örnekte kayıt bölünür;
    - 16.38 ms'yi aşan farkta yeni kayıt ve doğru `t0`;
    - bayrak değişimi örnekte kalır;
    - DEVAM'da `ilk_ornek` sürer;
    - `KA_SILME` bayrağı.
  - Hazır alan:
    - onaylı sektörler önceden silinir;
    - onaysıza dokunulmaz;
    - kafa hazır sektöre geçerken **silme sayısı artmaz** (NOR emülatörü `silme_adet`);
    - hazır bitince silme yeniden olur;
    - açılışta sayaç sıfır.
  - Python, yeniden kurulan örnek dizisini sentetik girdiyle **birebir** karşılaştırır.
- **B72 (kaynak):**
  - `Gb0` kabul edilir;
  - `loop` örneği halkaya iter;
  - görev halkayı boşaltır;
  - ön silme izni skop/pil/kayıt koşuluyla kapıda;
  - `GA` satırı;
  - `A3-1C2`.
- **Mutasyon:** her yeni iddiaya bir yalanlayıcı.
- **Tezgah (gerçek kart, ADS yok):**
  - `Gb0` 60 s kayıt → eşitle.
  - Örnek sayısı ≈ süre × gerçek hız (ADS yokken döngü hızı).
  - Zaman farkı dağılımı çıkarılır; en büyük boşluk ve nedeni raporlanır.
  - Hazır alanla ve hazır alan olmadan kayıt içi silme duraklaması sayılır.
- **Tezgah kalemi (ADS takılınca):**
  - 500/s gerçek örnek.
  - PC'de W hesabı kartın `D` satırıyla karşılaştırılır.

## Kapsam dışı

- PC'de W'nin hizalamalı hesabı ve grafik (alt proje 2/3; bugün yalnız ham kod ve zaman çözülür).
- Ayrıntılı kipte süre sınırı ve zamanlanmış başlatma (1C-4).
- Skop günlüğü (1C-3).
