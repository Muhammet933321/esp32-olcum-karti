# 1C-4 — Zamanlanmış kayıt (tasarım)

Üst tasarım: [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §3
("Kayıt başlatma: elle + zamanlanmış"), §5 ("aktif oturum ve zamanlanmış kayıtlar
flaşta işaretli → yeniden başlamada ölçüm kaydı sürer"; "saat yoksa zamanlanmış
kayıt kurulamaz, arayüz bunu söyler"). Önceki dilimler: 1C-1 (5.12.68), 1C-2
(5.12.69), 1C-3 (5.12.70). Sıra (kullanıcı): 1C-1 → 1C-2 → 1C-3 → **1C-4**.

> **Karar yetkisi:** kullanıcı 2026-10-01 gecesi "sen devam et ben yatıyorum,
> adım adım devam et sisteme" dedi. Bu belgedeki bütün kararlar benim, gerekçeleri
> ve yanlışsa maliyetleriyle. Kullanıcı sonunda kontrol edecek.

## Amaç

Bugün bir kayıt yalnız elle başlar ve biter. Zamanlanmış kayıt, kartı başında
beklemeden belli bir saatte, belli bir süre ve hızda kayıt almayı sağlar. Örnek
kullanımlar: gece 02:00'de 6 saat boyunca dakikada 1 nokta almak ya da
yarın 09:00'da 10 dakikalık ayrıntılı kayıt almak.

**Başarı ölçütleri**
- Plan **gerçek saate** göre başlar ve biter (± 1 s). Saat yoksa plan kurulmaz;
  kart bunu söyler.
- Plan kalıcıdır (NVS). Kart kapanıp açılırsa:
  - bekleyen plan bekler;
  - başlamış plan DEVAM ile sürer ve planlanan anda biter.
- Plan başka bir kaydı ya da pil testini **bölmez**.
- PC, eşitlenen dosyadan oturumun planlı olduğunu ve neden bittiğini okur.

## Kararlar

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| K1 | **Kullanıcı:** 1C'nin dördüncü dilimi zamanlanmış kayıt | — |
| K2 | **Tek** bekleyen plan: başlangıç (unix s), süre (s; 0 = `Gd`'ye dek), hız (`hiz_ms`, `Gb` ile aynı küme, 0 = ayrıntılı). Tekrarlı plan YOK | YAGNI; tek plan NVS'te 4 anahtar. Maliyet: "her gün 02:00" yok — PC/telefon her gün yeniden kurar |
| K3 | Komut: `Gp<bas_unix>,<sure_s>,<hiz_ms>` ya da göreli `Gp+<saniye>,<sure_s>,<hiz_ms>`; `Gp-` iptal; `G?` ardından **`GP`** satırı | Seri/web aynı yoldan. Göreli biçim kartın kendi saatine çevrilir (seri konsolda kullanışlı) |
| K4 | Saat: yalnız **NTP** (STA kipinde). Saat yoksa `Gp` **reddedilir**. Cihazdan saat alma 1D'de (imzalı istek) | Spec: "saat yoksa kurulamaz". Yalnız seriden saat vermek 1D'nin güvenlik tasarımını atlardı. Maliyet: internetsiz ağda plan yok |
| K5 | Başlangıç anında meşgul değilse ÖLÇÜM oturumu açılır ve hemen ardından bir **OLAY `PLAN`** yazılır (başlangıç, süre, hız, plan kimliği). **Meşgul** = oturum (elle kayıt, pil, skop günlüğü) VAR **ya da** pil testi oturumsuz sürüyor (DOLU'da) **ya da** skop günlüğü açık; o zaman plan **atlanır**, durumu "atlandı" olur. Çekirdek 0 da aynı anda bakar: istek geldiğinde oturum ya da DEVAM bekleyişi varsa (kuyrukta önde bir `Gb` olabilir) **açmaz**, "meşgul" der → atlandı. *(1C-4 incelemesi I1/I2 ile güncellendi)* | Plan kullanıcının elle yaptığı işi bölmemeli; pil testini bölmek emniyet (Ö7) |
| K6 | Bitiş: süre dolunca oturum **BITIR sebep 7 "planlı süre doldu"** ile kapanır. Kullanıcı önce `Gd` derse plan biter (sebep 1). **`Gp-` sürmekte olan planın kaydını da durdurur** (sebep 1) — yoksa otomatik bitiş sessizce kalkar ve kayıt `Gd`'ye dek sürerdi *(I4)* | Sebep ayrımı PC'de "kendisi mi bitti, kullanıcı mı kesti" |
| K7 | **Kaçırılan başlangıç:** kart başlangıçta kapalıydı ve pencere (başlangıç + süre) bitmediyse **geç başlar**, kalan süre için. Pencere geçmişse plan "kaçırıldı" | Gece elektrik gidip gelirse kayıt yine alınır. `PLAN` olayı ile BASLA'nın saati gecikmeyi gösterir |
| K8 | Kalıcılık: plan NVS'te, **kendi ad alanında `plan`** (`pl_bas`, `pl_sure`, `pl_hiz`, `pl_no`, `pl_ot`, `pl_bu`, en son `pl_dur`). Başlamış planın oturumu bilinir (`pl_ot`); yeniden başlamada o oturum DEVAM alırsa bitiş yine plandan. Açılışta "sürüyor" ama oturumu henüz bilinmiyorsa (sonuç gelmeden elektrik gitti) plan **bitti** sayılır — o an etkin oturum tahminle benimsenmez. Saat yoksa bitiş saat gelene dek **bekler** (oturum sürer) *(uygulamadaki ad alanı ve anahtarlarla eşitlendi, M6)* | Spec §5. Saatsiz bitirmek yanlış an demek |
| K9 | Karar mantığı platformsuz **`kayit_plan.h`**: `plan_adim(plan, simdi_unix, mesgul, oturum_id)` → eylem `PE_YOK` · `PE_BASLAT` · `PE_BITIR` (atlandı / kaçırıldı / bitti / başlatılamadı durum geçişidir, eylem değil). Plan **yalnız çekirdek 0'ın bildirdiği oturuma** bağlanır: `plan_sonuc(plan, sonuc)` (> 0 oturum, 0 meşgul → atlandı, < 0 hata → başlatılamadı; 10 s içinde sonuç yoksa başlatılamadı). Kart yapıştırıcısı eylemi `KM_*` mesajına çevirir *(I1/I3, M6)* | AVR'de emüle NVS ve sahte saatle açılıştan açılışa sınanır (1A-2 deseni). İlk sürüm BASLAT'tan sonra beliren HERHANGİ bir oturumu benimsiyordu: kullanıcının `Gb`/`p1`'ini sonunda sebep 7 ile kapatabilirdi |
| K10 | `GP <durum> <bas> <sure> <hiz> <oturum>`; durum: 0 yok · 1 bekliyor · 2 sürüyor · 3 bitti · 4 atlandı · 5 kaçırıldı · 6 saat bekleniyor · **7 başlatılamadı** (bölüm dolu / kayıt hatası / çekirdek 0 cevap vermedi; kart sebebini yazar). `G`, `GA`, `GT` değişmez | Mevcut ayrıştırıcılar bozulmaz. Başlatılamayan plana "bitti" demek yanlış bilgiydi (I3) |
| K12 | Başlangıç denetimi: `bas` 1 700 000 000'den (2023-11) küçükse ya da şimdiden **1 yıldan** ileriyse ret (`KP_ZAMAN`); göreli ofset de en fazla 1 yıl (toplamada 32 bit taşması yok) *(M2)* | `+` unutulmuş `Gp20,600,200` 1970 sayılıp plan HEMEN başlıyordu |
| K11 | Biçim sürümü **2 kalır**; yeni sebep 7 ve olay türü `KO_PLAN` (5) bilinmeyen okuyucuda zararsız; firmware `A3-1C4` | — |

## Akış

**Çekirdek 1 (`loop`):** `Gp`/`Gp-` planı ayrıştırır, saat ve sınırları denetler,
planı NVS'e yazar (çekirdek 1 tek yazar). Saniyede bir `plan_adim` çağrılır;
eylem `KM_PLAN_BASLAT` (BASLA + PLAN olayı tek mesajda, istek numarasıyla) ya
da `KM_PLAN_BITIR` (sebep mesajda: 7 süre doldu, 1 `Gp-`) olur. Kart oturum
durumunu `kayit_durum_al()`'dan okur. Çekirdek 0'ın sonucu istek numarası
eşleşince `plan_sonuc`'a verilir; plan artık beklemiyorsa (zaman aşımı, `Gp-`)
ve sonuç bir oturumsa o oturum **kapatılır** — sahipsiz kayıt kalmaz.

**Çekirdek 0 (kayıt görevi):** `KM_PLAN_BASLAT`'ı oturum ya da DEVAM bekleyişi
varken **açmaz**; sonucu (oturum / 0 meşgul / hata) volatile'a, ardından istek
numarasını yazar. `KM_PLAN_BITIR` yalnız etkin oturum planın oturumuysa kapatır
(yanlış oturumu kapatmaz).

**Yeniden başlama:** açılışta plan NVS'ten okunur. "Sürüyor" ise:
- planın oturumu DEVAM aldıysa bitiş beklenir;
- oturum yoksa (DEVAM alamadı) plan "bitti" sayılır;
- oturumu hiç bilinmiyorsa (sonuç gelmeden elektrik gitti) plan "bitti" sayılır.

## Doğrulama

- **B71 (AVR):** `SENARYO_PLAN`, emüle NVS ve sahte saatle açılıştan açılışa:
  - başlangıçta başlat, süre dolunca bitir;
  - meşgulse atla;
  - kaçırılan başlangıç: pencere içinde geç başla, dışında "kaçırıldı";
  - saat yokken bekle;
  - yeniden başlamada bitiş korunur;
  - `Gd` planı bitirir;
  - iptal;
  - *(inceleme sonrası)* başka oturum benimsenmez, plan yalnız bildirilen
    oturuma bağlanır; sonuç gelmezse / hata → başlatılamadı, meşgul → atlandı;
    geç sonuç alınmaz; süre 0 hiç BITIR demez; açılışta oturumu bilinmeyen
    plan bitti; anlamsız başlangıç reddi (B71.R1–R13).
  - Python: sebep 7 ve OLAY `PLAN` C == Python.
- **B72 (kaynak):**
  - `Gp` ayrıştırma ve sınırlar;
  - saat yoksa ret;
  - NVS anahtarları;
  - `KM_PLAN_BITIR` yalnız planın oturumunu kapatır;
  - `GP` satırı;
  - `A3-1C4`;
  - *(inceleme sonrası)* çekirdek 0 meşgulse açmaz ve sonucu istek
    numarasıyla yayınlar; meşgul = oturum / oturumsuz pil / skop günlüğü;
    `Gp-` kaydı da durdurur; geç açılan oturum kapatılır (F66–F73).
- **Mutasyon:** her yeni iddiaya bir yalanlayıcı.
- **Tezgah (gerçek kart, NTP):**
  - `Gp+20,30,200`: ~20 s sonra başlar, 30 s sonra sebep 7 ile biter; `PLAN` olayı var.
  - Plan sürerken yeniden başlatma: DEVAM, bitiş zamanı tutar.
  - Elle kayıt sürerken plan: atlandı.
  - `Gp-` iptal.
  - *(inceleme sonrası)* `Gp20,…` ve 1 yıldan ileri ret; süre 0 kendiliğinden
    bitmez, `Gp-` kaydı sebep 1 ile kapatır.

## Kapsam dışı

- Tekrarlı (günlük/haftalık) plan, birden fazla bekleyen plan.
- Cihazdan saat alma (1D).
- Planlı osiloskop günlüğü / pil testi.
- Koşullu/tetikli başlatma (spec §12).
