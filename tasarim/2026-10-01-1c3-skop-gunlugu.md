# 1C-3 — Osiloskop günlüğü (tasarım)

Üst tasarım: [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §5
("Osiloskop günlüğü: her tetikte ya da her N saniyede bir yakalama (≤ 4000
örnek, 8 KB). İsteğe bağlı olarak bir ölçüm kaydıyla aynı oturumda; yakalama
anı ölçüm kaydında işaretli boşluk"). Önceki dilimler: 1C-1 (DEVIR 5.12.68),
1C-2 (DEVIR 5.12.69). Sıra (kullanıcı): 1C-1 → 1C-2 → **1C-3** → 1C-4
zamanlanmış kayıt.

> **Karar yetkisi:** kullanıcı 2026-10-01 gecesi "sen devam et ben yatıyorum,
> adım adım devam et sisteme" dedi. Bu belgedeki bütün kararlar benim,
> gerekçeleri ve yanlışsa maliyetleriyle. Kullanıcı sonunda kontrol edecek.

## Amaç

Bugün bir osiloskop yakalaması yalnız ekranda (ya da PC köprüsünün
arşivinde) yaşıyor; kart onu saklamıyor. Osiloskop günlüğü yakalamaları
**kartın kayıt günlüğüne** yazar. Böylece ölçüm kaydı ve pil testi gibi
eşitlenir, PC'de ve ileride telefonda açılır. Amaç: aralıklı bir arızayı
(her tetikte) ya da yavaş değişen bir dalga şeklini (her N saniyede bir)
kart başında durmadan toplamak.

**Başarı ölçütleri**
- Her yakalama ham kodlarıyla (≤ 4000 × 12 bit) ve onu yorumlamaya yeten
  bilgiyle saklanır: hız, zaman tabanı, tetik ve ayarları, ölçek, yakalama
  anı ve ADS'in sustuğu süre. Kartın eFuse kalibrasyon tablosu oturuma bir kez
  yazılır.
- PC, eşitlenen dosyadan yakalamayı bugünkü `/skop.bin` biçimine **birebir**
  çevirebilir. Arayüzün tek ikili çözücüsü değişmez.
- Bir ölçüm kaydına eklenirse yakalama anı o kayıtta işaretli boşluktur:
  yakalamanın başlangıcı ve süresi kayıtta durur.
- Yakalama düşmez: kart bir sonraki yakalamayı ancak bir öncekini flaşa
  yazınca başlatır. Yazılamayan yakalama sayılır.
- Emniyet kuralları değişmez: pil testinde yakalama yok, `p0` her zaman
  serbest (Ö7).

## Kararlar

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| K1 | **Kullanıcı:** 1C'nin üçüncü dilimi osiloskop günlüğü | — |
| K2 | Yakalama yeni kayıt türü **SKOP (10)** ile, parça parça yazılır. Bir kayıt en fazla yazıcının 1012 B tamponu kadar (≈ 480 örnek); 4000 örnek ≈ 9 parça. İlk parça **META** taşır | Kayıt sınırı 4096 B ve sektör başı TEKRAR + BITIR payı; yazıcının tamponu zaten var, RAM eklemez. Maliyet: parça başına 16 + 12 B ek (~%3) |
| K3 | Örnek **u16 ham kod** (12 bit paketlenmez) | `/skop.bin` ve arayüz çözücüsü u16; tek kodlama (Ö: bir dalga iki yolda farklı çözülmesin). Maliyet: %25 fazla yer; 8 KB/yakalama |
| K4 | Kalibrasyon: günlük başlarken **OLAY `SKOP_KAL`** (17 noktalı eFuse tablosu, mV). Yakalama başına kopya yok | Tablo çipe özgü ve sabit; her yakalamada 34 B gereksiz. Kayıt kendi başına yorumlanabilir kalır |
| K5 | İki kip: **`Gt0` = her tetikte** (NORMAL kip, zaman aşımında yeniden kurulur, kayıt yok) · **`Gt<ms>` = N ms'de bir** (1000…3 600 000; o anki kip, OTO ise tetiksiz de yakalar). `Gtd` durdurur. Yakalama ayarları o anki `SkopAyar`; her yakalamanın META'sı ayarı taşır | Spec'in iki kipi; ayar NVS'te değil, günlük onu donduramaz — META her yakalamayı kendi başına anlatır |
| K6 | **Oturum:** etkin bir ÖLÇÜM oturumu varsa yakalamalar **onun içine** yazılır (aynı oturum, "işaretli boşluk"). Yoksa yeni oturum türü **SKOP (3)** açılır; `hiz_ms` alanı N'yi tutar | Spec "isteğe bağlı olarak bir ölçüm kaydıyla aynı oturumda". Ayrıntılı kip `hiz_ms 0`'a bağlıydı: artık **yalnız ÖLÇÜM** oturumunda (SKOP oturumu `hiz_ms 0` = her tetik) |
| K7 | SKOP oturumunda ölçüm noktası ve ayrıntılı örnek **yazılmaz** | Oturum yalnız yakalamalardan oluşur; PC türünden bilir |
| K8 | Çekirdek 1 → 0: yakalama bitince çekirdek 1 kodları ve META'yı **tek PSRAM yuvasına** kopyalar (~8 KB, ~0.2 ms), kayıt görevine kısa bir mesaj atar. Görev parçaları yazıp yuvayı boşaltır. Günlük bir sonraki yakalamayı **yuva boşalınca** kurar | Mesaj kuyruğu 137 B taşıyor; `skop_veri` iç RAM'de ve kilidi ölçüm tarafı beklemez. Tek yuva: bir yakalamanın flaş yazması bir sonraki yakalamayla çakışmaz (yazma da iki çekirdeği kısa durdurur). Maliyet: N ms kipinde gerçek aralık N ile "yakala + yaz" süresinin büyüğü |
| K9 | PSRAM yoksa `Gt` **reddedilir** | Sessiz düşme yerine açık ret (1C-2 incelemesinden ders: PSRAM yokken `Gb0` kabul edilip boş kalıyordu) |
| K10 | Pil testi sürerken `Gt` reddedilir; günlük sürerken **`p1` reddedilir** (önce `Gtd`). `p0` hep serbest. Günlük sürerken elle yakalama komutları (`t`, `tB`, `ta`) reddedilir, ayar komutları serbest | Ö7: yakalama ADS'i susturur, pil testinde kesme denetimi durur. Elle yakalama günlüğün yuvasını ve sırasını bozar; ayar değişikliği META'da görünür |
| K11 | `Gd` etkin oturumu kapatır ve günlüğü durdurur. `Gtd` yalnız günlüğü durdurur: SKOP oturumu kapanır (BITIR kullanıcı), ÖLÇÜM oturumu **sürer** | Ölçüme eklenmiş günlük ölçümü kapatmamalı |
| K12 | Kart yeniden başlarsa **günlük sürmez**: SKOP oturumu "kart yeniden başladı" (5) ile kapanır (mevcut kural: ölçüm dışı açık oturum DEVAM almaz). ÖLÇÜM oturumu DEVAM ile sürer ama günlük olmadan | Günlük durumu ve `SkopAyar` RAM'de; sürdürmek için NVS'e yazmak gerekir — 1C-4 (zamanlanmış kayıt) ile birlikte ele alınacak |
| K13 | Durum: `G?`'nin ardından yeni **`GT`** satırı: etkin · aralık · yakalama sayısı · yazılamayan. `G`, `GA` değişmez | Mevcut ayrıştırıcılar bozulmaz |
| K14 | Biçim sürümü **2 kalır**; firmware `A3-1C3` | Yeni kayıt türü, eski okuyucu atlar (B13) |

## Kayıt biçimi

**SKOP** `KAYIT_T_SKOP = 10`. Başlıkta oturum = etkin oturum.

```
 0 u32 no        (yakalamanın oturumdaki sırası, 1'den)
 4 u16 ilk       (bu parçadaki ilk örneğin indeksi)
 6 u16 adet      (bu parçadaki örnek)
 8 u16 toplam    (yakalamanın toplam örneği, ≤ 4000)
10 u8  parca     (0'dan; 0. parça META taşır)
11 u8  0
12 [parca 0] META 36 B:
     u32 t_ms     yakalama istendiği an (kart_ms) — ADS burada susar
     u32 sure_ms  istekten sonuca (ADS'in sustuğu süre)
     u32 hz       örnekleme hızı
     u32 tdiv_us  zaman tabanı
     f32 adim     V / kod adımı (nominal, `/skop.bin` ile aynı)
     f32 ofset    V
     u16 tetik    tetik indeksi
     u16 esik     tetik eşiği (kod)
     u16 histerezis (kod; `SkopAyar`'da u16)
     u8  kip · tetiklendi · kenar · on_yuzde · onay · 0
   + u16 kod × adet
```

**OLAY `SKOP_KAL`** (`KO_SKOP_KAL = 4`, ortak 8 B olay başı + 34 B):
`i16 mv[17]` — `kal_mv_tab`, eşit aralıklı 17 kod noktasında mV.

PC: `Oturum.skoplar` = `{no: {"meta", "kodlar", "tam"}}`. `tam` yalnız bütün
parçalar varsa doğrudur; eksik parça sessizce doldurulmaz. `skop_ikili(y)`
yakalamayı bugünkü 32 B başlıklı `S3B` biçimine çevirir.

## Akış

**Çekirdek 1 (`loop`):**
- `Gt` günlük durumunu kurar: aralık, sıra, PSRAM yuvası. ÖLÇÜM oturumu yoksa SKOP oturumu açılır ve ilk mesajla birlikte `SKOP_KAL` gider.
- Her turda günlük şunlara bakar: skop boşta mı, döküm yok mu, yuva boş mu, aralık doldu mu. Hepsi tutuyorsa `skop_is_ver(SKOP_IS_GUNLUK)` çağrılır ve `t_ms` saklanır.
- `skop_sonuc_isle` sonuçları şöyle ele alır:
  - `GUNLUK` + OK: kodlar ve META yuvaya kopyalanır, mesaj gider.
  - `TETIK_YOK`: kayıt yok, yeniden kurulur.
  - `KILIT`: sayılır.
- `skop_dokum` / `M` satırı **basılmaz**; günlükte yakalama seri porta dökülmez.

**Çekirdek 0 (kayıt görevi):** `KM_SKOP` mesajında yuvadan `ky_skop` çağrılır:
1. Bekleyen noktalar ve ayrıntılı örnekler önce boşaltılır (kayıt sırası zaman sırası).
2. Parçalar sektöre sığdığı kadar yazılır (en az 32 örnek; yoksa yeni sektör).
3. Yuva boşaltılır.

DOLU olursa oturum BITIR(DOLU) ile kapanır ve günlük durur.

**Yazıcı (`kayit_oturum.h`):** `ky_skop(y, meta, kodlar, toplam, no)`.
SKOP oturumu `ky_nokta`/`ky_ayrinti_ornek`'i `KG_YOK` ile reddeder.

## Doğrulama

- **B71 (AVR):**
  - SKOP paketi C == Python (META ve parça başı).
  - `SKOP_KAL` olayı.
  - Yazıcı küçük sektörlü emülatörde 4000 örneği **sektörlere bölerek** yazar; PC birebir birleştirir.
  - Eksik parça `tam = False`.
  - ÖLÇÜM oturumuna eklenen yakalama noktalarla aynı oturumda ve zaman sırasında.
  - SKOP oturumunda nokta ve örnek yok.
  - Açılışta açık SKOP oturumu sebep 5 ile kapanır.
  - DOLU'da BITIR.
- **B72 (kaynak):**
  - `Gt` ayrıştırma ve sınırları.
  - PSRAM yoksa ret.
  - Pil testinde ret, günlükte `p1` reddi.
  - Elle yakalama reddi.
  - Yuva boşalmadan yeniden kurma yok.
  - `GT` satırı.
  - Ayrıntılı kip yalnız ÖLÇÜM'de.
  - `A3-1C3`.
- **Mutasyon:** her yeni iddiaya bir yalanlayıcı.
- **Tezgah (gerçek kart, ADS yok; skop ADS'e bağlı değil — GPIO4):**
  - CAL kare dalgası (`X1000`) ile `Gt0` 30 s ve `Gt2000` 30 s.
  - Eşitlenen yakalama `/skop.bin` ile aynı biçimde çözülür, frekans ~1 kHz ölçülür.
  - Sayı ≈ beklenen.
  - `Gb200` + `Gt2000`: noktalar ve yakalamalar aynı oturumda.
  - Günlükte `p1` ve `t` reddi.
  - Yeniden başlatmada SKOP oturumu sebep 5.

## Kapsam dışı

- Yakalamaların panelde/telefonda gösterimi (alt proje 3/5) — bugün PC dosyadan okur.
- Günlüğün yeniden başlatmada sürmesi ve zamanlanmış başlatma (1C-4).
- Yakalamayı 12 bit paketleme ya da sıkıştırma.
