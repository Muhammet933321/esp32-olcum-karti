# 1C-1 — Pil testi oturumu + oturuma ad/not (tasarım)

Üst tasarım: [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §5, §7,
§8, Ö7. Önceki dilim: 1B (DEVIR 5.12.67). 1C dört dilime bölündü (kullanıcı
kararı, 2026-09-30): **1C-1 pil testi** → 1C-2 ayrıntılı kip → 1C-3 osiloskop
günlüğü → 1C-4 zamanlanmış kayıt.

> **Karar yetkisi:** kullanıcı 2026-09-30'da "ben şu an inceleyemiyorum, sen
> ver kararları, en son ben kontrol edeceğim" dedi. Aşağıdaki "Karar"
> satırlarından kullanıcının verdikleri ayrıca işaretli; diğerleri benim,
> gerekçesiyle.

## Amaç

Pil testi bugün yalnız RAM'de yaşıyor. Eğri `PilHalka`'da (1 Hz, kalibre
V/I), DCIR'ın yalnız **son** değeri ve sayısı tutuluyor, olay geçmişi yok.
Panel kapalıyken ya da kart yeniden başlarken veri yalnız tarayıcının
IndexedDB'sinde kalıyor. 1C-1'den sonra her pil testi kartın flaşında kendi
oturumu olarak saklanacak: noktalar, her DCIR darbesi, sonuç. PC bu oturumu
ölçüm kayıtları gibi kaybetmeden eşitleyecek. Kayıtlara ad, etiket ve not da
eklenebilecek (1A-1 planı bu işi 1C'ye bırakmıştı).

**Başarı ölçütleri**
- Her kabul edilen `p1` bir PİL oturumu açar. Oturum, testin bitiş sebebini
  taşıyan bir sonuç olayı ve bitişle kapanır.
- Emniyet davranışı değişmez (Ö7):
  - `p0` her zaman serbesttir ve yükü **her şeyden önce** keser.
  - Kart yeniden başlarsa test sürmez.
  - Pil testi sürerken skop yakalaması yasaktır (B41).
- Kart yeniden başladığında açık kalmış bir pil oturumu **kapatılır**, sürdürülmez.
- `/pil` ve bugünkü panel aynen çalışır.

## Kararlar

| # | Karar | Gerekçe / maliyet |
|---|---|---|
| K1 | **Kullanıcı:** 1C dört dilim, önce pil testi | — |
| K2 | **Kullanıcı:** ölçüm kaydı sürerken `p1` gelirse ölçüm kaydı "başka oturum başladı" sebebiyle kapanır, pil kaydı açılır. Test bitince ölçüm kaydı kendiliğinden yeniden başlamaz | Aynı anda tek oturum (spec §5) |
| K3 | **Kullanıcı** (yaklaşım A): pil oturumu ölçüm kaydının nokta biçimini aynen kullanır; yeni olarak yalnız OLAY kaydı eklenir | Ham kod saklanır, sonradan başka kalibrasyon uygulanabilir (§7). `ortak/` tek nokta biçimi okur |
| K4 | Her pil testi **otomatik** kaydedilir; ayrı bir "kaydet" adımı yok | Kullanıcının en çok kullandığı özellik, kaydı unutulmasın |
| K5 | Kayıt açılamazsa (bölüm yok, dolu, tarama sürüyor) **test yine başlar**; kart "pil testi KAYDEDİLMİYOR — sebep" der | Testin emniyeti ve kesmesi kayda bağlı değil; bugünkü davranış kaybolmasın. `/pil` veriyi yine tutar |
| K6 | Test sürerken `Gb` ve `Gd` **reddedilir** ("testi `p0` ile durdur"). `GF!` zaten reddediliyor | Kayıt testle birlikte başlar ve biter; `p0` tek durdurma yolu |
| K7 | Kayıt yeri test sırasında dolarsa oturum "dolu" ile kapanır, **test sürer** | Emniyet kayda bağlı değil. Sonuç `B` raporunda ve `/pil`'de kalır |
| K8 | Açılışta açık bulunan **ölçüm dışı** her oturum kapatılır (yeni bitiş sebebi "kart yeniden başladı"). Yazılamazsa (yer yok) durum 4'te bekler, yer açılınca kapanır; asla DEVAM almaz | Bugün yönetici bu oturumu açık bırakıyordu (1C'ye bırakılmış açık) |
| K9 | `/pil` ve `PilHalka` alt proje 3'e kadar **kalır**; aynı test ikisine birden yazılır | Spec "yerine geçer" diyor; bugünkü panel `/pil` okuyor, panel yenilenince kaldırılır |
| K10 | Darbe (DCIR) içindeki örnekler noktadan atılmaz; nokta yeni **`KN_DCIR`** bayrağını taşır | Ö1: veri gizlenmez, işaretlenir. Analiz bu noktaları ayırabilir |
| K11 | Biçim sürümü **2 kalır**: BASLA'nın baytları değişmedi, yeni kayıt türleri eklendi | Biçim 1A-1'den beri bilinmeyen türü geçerli sayıp atlıyor (B13); sürüm artırmak eski PC araçlarını gereksiz yere reddettirirdi |
| K12 | Ad/etiket/not kayıtları başlıkta `oturum = 0` taşır, hedef oturum yükte yazar | Başka bir oturum sürerken de yazılabilirler; oturumun kendi kayıt dizisi karışmaz |
| K13 | Kart adları ve notları **yorumlamaz**: yazar, eşitler. Son hali PC (bugün `kayit_bicim.py`, sonra `ortak/`) kurar | Kartta ad dizini gerekmez; spec "bütün cihazlar aynı görür" — eşitlemeyle görürler |
| K14 | Metin temizleme 1B'deki not temizleyicinin genellemesi: geçersiz UTF-8, kontrol karakteri, `"`, `\` atılır, karakter sınırında kesilir. Kalibrasyon notu da aynı işlevi kullanır | Tek işlev, tek test; JSON'a kaçışsız girer |
| K15 | Firmware sürümü `A3-1C1` | PC/tezgah ayırt eder |

## Kayıt biçimi eklemeleri (`kayit_bicim.h` + `kopru/kayit_bicim.py`)

**Oturum türü:** `KAYIT_OTURUM_PIL = 2`. BASLA'da `hiz_ms` = pil kayıt
aralığı. Bugünkü `pil_kayit_hz` ayarından türer (varsayılan 1 Hz), 100 ile
60 000 ms arasına kısılır.

**Nokta bayrağı:** `KN_DCIR = 0x40`. Noktanın örneklerinden en az biri DCIR
darbesi sırasında, yani yük kapalıyken alınmıştır.

**Bitiş sebepleri** (mevcut 1 kullanıcı, 2 dolu, 3 hata):
- `KB_SEBEP_PIL = 4`: test kendi bitti (kesme ya da emniyet); ayrıntı SONUÇ olayında.
- `KB_SEBEP_YENIDEN = 5`: kart yeniden başladı, açık oturum açılışta kapatıldı.
- `KB_SEBEP_OTURUM = 6`: başka bir oturum başladı. Bu, `Gb`'nin kayıt sürerken
  verilmesini de kapsar; eskiden o durum "kullanıcı" yazıyordu.

**OLAY kaydı** `KAYIT_T_OLAY = 7`. Başlıkta oturum = etkin oturum. Yük:

```
 0 u8 olay_tur · 1 u8 0 · 2 u16 0 · 4 u32 kart_ms · 8.. türe özel
KO_PIL_AYAR 1   (32 B)  8 f32 kesme_v · 12 f32 ocv · 16 u32 azami_s ·
                        20 u32 dcir_aralik_ms · 24 u32 dcir_ms · 28 f32 kayit_hz
KO_DCIR     2   (44 B)  8 u32 no · 12 f32 v_once · 16 f32 i_once · 20 f32 v_ani ·
                        24 f32 v_oturmus · 28 f32 r_ani · 32 f32 r_oturmus ·
                        36 f32 mah · 40 f32 wh           (mah/wh: o ana kadarki)
KO_PIL_SONUC 3  (36 B)  8 u8 durum · 9 u8 hata · 10 u16 0 · 12 f32 mah · 16 f32 wh ·
                        20 f32 ocv · 24 f32 v_son · 28 u32 sure_ms · 32 u32 dcir_sayisi
```

Olay yazılmadan önce tamponda bekleyen noktalar boşaltılır. Böylece kayıt
sırası zaman sırasıyla aynı kalır.

**NOT kaydı** `KAYIT_T_NOT = 8`. Başlıkta oturum = 0. Yük:

```
 0 u32 hedef_oturum · 4 u8 alan (1 ad · 2 etiketler · 3 not) · 5 u8 0 · 6 u16 0 ·
 8 u32 nokta_ms (not: grafikteki kart_ms; 0 = oturumun geneli) ·
12 u32 degistirir (0 = yeni; > 0 = o sıradaki NOT kaydının yerine geçer,
                   metin boşsa onu SİLER) · 16 metin (UTF-8, en fazla 120 B, NUL'suz)
```

Son halin kurulması:
- Ad ve etiketler için **en son** gelen kayıt geçerlidir. Etiketler virgülle ayrılır.
- Notlar sırayla birikir. `degistirir` alanı doluysa ilgili notu değiştirir,
  metin boşsa siler.
- *(Son inceleme, 2026-10-01)* `degistirir` her zaman **asıl** notun (ilk
  yazılan NOT kaydının) sırasını gösterir; düzeltilmiş bir not yine asıl
  sırasıyla hedeflenir.
- Düzeltmede `nokta_ms = 0` ise notun grafik yeri **korunur**.
- Bilinmeyen ya da silinmiş bir sıra **yok sayılır**, hayalet not doğmaz.
  `ortak/` aynı kuralı taşır.

## Akış

**Kart, çekirdek 1 (komut + `pil_isle`)**
- **`p1` kabul edilince:** `kayit_pil_baslat()` çağrılır.
  1. Kayıt açılamazsa bir satır uyarı basılır (K5).
  2. Açılabiliyorsa **tek mesaj** gider: `KM_PIL_BASLAT`. Mesaj BASLA
     (tür PİL, kalibrasyon kopyası ve numarası, 1B) ile `PIL_AYAR`
     olayının yükünü birlikte taşır.
  3. Çekirdek 0'da yönetici, açık oturum varsa onu "başka oturum" sebebiyle
     kapatır (K2), pil oturumunu açar ve olayı yazar.
- **Her DCIR darbesi bitince:** `KM_OLAY` (`DCIR`) gönderilir.
- **`pil_durdur()` (kesme, emniyet, `p0`):**
  1. Önce **yük kesilir** (bugünkü sıra).
  2. Ardından tek mesaj gider: `KM_PIL_BITIR`. Mesaj `PIL_SONUC` yükünü ve
     sebebi taşır: `p0` ise "kullanıcı", değilse "pil".
  3. Yönetici etkin oturum **PİL ise** önce olayı, sonra bitişi yazar;
     değilse hiçbir şey yapmaz.
- **Noktalar:** `kayit_ornek` yeni bir bayrak argümanı alır. `pil.dcir_icinde`
  doğruysa bayrak `KN_DCIR` olur.
- **Mesaj kuyruğu dolarsa** sessiz kalınmaz: sayaç artar ve `! G` satırı basılır.
  Olaylar seyrek (5 dk'da bir), mesaj kuyruğu 4.
  - **`KM_PIL_BITIR` asla düşmez.** Gönderilemezse bekletilir ve döngünün her
    turunda yeniden denenir. Düşseydi pil oturumu açık kalır, test bittiği
    halde nokta yazmayı sürdürürdü. Yük o sırada zaten kesilmiştir.

**Yönetici (`kayit_yonet.h`, platformsuz, AVR'de sınanır)**
- `kyn_olay(m, yuk, n)`: etkin oturum yoksa `KG_YOK`.
- `kyn_pil_bitir(m, yuk, n, sebep)`: yalnız etkin oturum PİL ise çalışır.
- `kyn_not(m, yuk, n)`: `oturum = 0` ile yazar. Yer açmak gerekirse etkin
  oturumun TEKRAR kaydı normal şekilde yazılır.
- `kyn__devam_dene`: yalnız ÖLÇÜM sürdürülür, diğer türler kapatılır (K8).
- `ky_baslat`: sürmekte olan oturumu "başka oturum" sebebiyle kapatır.

**Ad/not komutları** (seri + `/komut`; web ucu panelle, alt proje 3):
- `Ga<oturum> <ad>` ad koyar.
- `Ge<oturum> <etiket, etiket>` etiket koyar.
- `Gn<oturum> <not>` oturumun geneline not ekler; `Gn<oturum>@<kart_ms> <not>`
  grafikteki bir ana not ekler.
- `Gx<oturum>:<sıra>[@<kart_ms>] <metin>` o notu değiştirir; `@` yoksa grafik
  yeri korunur, metin boşsa siler.
- Hedef oturum `1 ≤ id < sonraki_sira` olmalıdır. Kartta artık bulunmayan eski
  bir oturuma da not eklenebilir; PC'de o oturum durur.
- *(Son inceleme)* Ayrıştırıcı platformsuzdur (`kayit_not_ayir`, B71.B21).
  Sayılar yalnız rakamdan oluşur: işaret, boşluk, boş sayı, 0 ve 32 bit
  taşması reddedilir. Bozuk argümanda kayıt yazılmaz.
- Komut satırı en fazla 175 karakterdir; uzun komut **reddedilir**, kesilmez.

**PC:** `kayit_bicim.py` OLAY ve NOT kayıtlarını çözer. `oturumlari_kur`
olayları oturumlarına bağlar, adları ve notları K13'e göre kurar.
`kayit_esitle.py` değişmez: kartın baytlarını aynen saklar.

## Doğrulama

- **B71 (`test_kayit.py`):**
  - OLAY ve NOT paketleri C ile Python arasında aynı (ortak vektör).
  - Metin temizleyici: C10/C10b yeşil kalır, yeni alanın sınırı (120 B) da sınanır.
  - Yönetici senaryosu (AVR, emüle NOR + NVS, açılıştan açılışa):
    1. `p1` sırasında ölçüm oturumu "başka oturum" ile kapanır, pil oturumu açılır.
    2. Olaylar noktalarla zaman sırasında yazılır.
    3. `PIL_SONUC`, BITIR'dan önce gelir.
    4. Ölçüm oturumu varken gelen pil bitir mesajı hiçbir şey yapmaz.
    5. Açılışta açık pil oturumu "yeniden başladı" ile kapanır, DEVAM kaydı yok.
    6. Yer yoksa durum 4'te bekler, onay gelince kapanır, yine DEVAM yok.
    7. Not kayıtları başka oturum sürerken yazılır ve o oturumun TEKRAR/nokta
       dizisini bozmaz.
    8. Python ad/not son halini doğru kurar (değiştir, sil).
  - Noktacı: `KN_DCIR` bayrağı yalnız darbe örneklerini içeren noktada.
- **B72 (`test_kayit_esp.py`, firmware kaynağı):**
  - `p1` kabulünden sonra `kayit_pil_baslat`.
  - `pil_durdur` yükü mesajdan **önce** keser.
  - DCIR bitiminde olay gönderilir.
  - `Gb`/`Gd` pil sürerken reddedilir.
  - `p0` hâlâ serbest (`komut_serbest`).
  - `Ga/Ge/Gn/Gx` yardımda ve ayrıştırılıyor; sürüm `A3-1C1`.
- **Mutasyon:** her yeni iddiaya onu yalanlayan bir mutasyon.
- **Tezgah (gerçek kart, ADS takılı değil):**
  - `p1` reddedilir ve oturum açmaz.
  - `Ga`/`Gn` gerçek bir ölçüm oturumuna yazılır; eşitlenen dosyada PC adı ve notu okur.
  - Yeniden başlatmada ölçüm oturumu yine DEVAM alır.
- **Tezgah kalemi (ADS takılınca, gerçek pil):** tam test.
  - Oturumda `PIL_AYAR` + `DCIR` + `PIL_SONUC` bulunur.
  - Sonuç olayı `B` raporuyla aynıdır.
  - Test ortasında fiş çekilirse açılışta oturum "yeniden başladı" ile kapanır.

## Kapsam dışı (1C-1)

- `/pil`'in kaldırılması ve panelin oturumdan okuması (alt proje 3).
- Ad/not için web ucu (alt proje 3); bugün `/komut` üzerinden gönderilebilir.
- "Pil testi kesildi" bildirimi (1E).
- Ayrıntılı kip, osiloskop günlüğü, zamanlanmış kayıt (1C-2…4).
