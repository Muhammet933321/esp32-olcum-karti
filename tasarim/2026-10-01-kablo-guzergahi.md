# B73 — Kutu belgesinde kablo güzergahı (tasarım)

Belge: `BELGELER/8-kutu.html` (kaynak `uretim/kutu_veri.py` + `uretim/kutu.py` +
`uretim/kutu_3b.py`). Önceki kutu işleri: B50…B70 (DEVIR 5.12.64). Firmware dizisi
B71/B72'yi aldığı için bu iş **B73**.

> **Karar yetkisi:** kullanıcı 2026-10-01'de kapsam sorusuna "sence hangisi mantıklı ise
> öyle yap" dedi. Bu belgedeki kararlar benim, gerekçeleri ve yanlışsa maliyetleriyle.
> Kullanıcının kendi verdiği kararlar **Kullanıcı:** diye işaretli. Belge onayına sunulur.

## İstek

Kullanıcı (kurulumda, 10.2'de): *"hangi tel nereye gidiyor tam olarak söyle … acaba bu kutu
web sayfasında hangi kablo nereye gidecek ve nasıl gidecek bunu da mı göstersek? Çok daha
kolay ve anlaşılır olur."* Ardından: *"web panelde adım adım kısmında da … kablolar da
gözüksün … kutuyu oluşturma kısmında"* — yani `8-kutu.html`'in alt adım görünümü
(`#a10.2` gibi). Kullanıcı belgeyi bilgisayarda `file://` ile ve telefonda açıyor.

## Amaç

Kablo alt adımında kullanıcı tablo okumadan, çizime bakarak her kablonun **hangi uçtan
çıkıp hangi uca gittiğini** ve **hangi yoldan** gideceğini görsün; kesim boyunu ve
kesitini aynı yerden okusun.

**Başarı ölçütleri**
- 10.3, 10.4 ve 11.1'in her kablosu o adımın 2B çiziminde ve 3B görünümde **çizili**;
  çizimde olup tabloda olmayan ya da tersi **yok** (denetim ölçer).
- Kablonun üstüne gelince (dokununca) bilgi kartı: numara, nereden → nereye, güzergah
  sözü ("arka duvarın dibinden"), kesim boyu, kesit, not. Tablodaki satıra dokununca
  çizimde o kablo vurgulanır.
- Arka duvar kablolarının çizimi kullanıcının çalışırken gördüğü yönden: **içeriden,
  jak tarafından bakış** (x soldan) — bu oturumda verilen konum tabloları bu eksende.
- Çizim ve 3B **tek** güzergah hesabından üretilir; kesim boyu bu hesaptan gelir.

## Kapsam

**İçinde:** 10.3 (pil paketi), 10.4 (analog besleme), 11.1 (J5 10 telli kablo + CAL teli)
ve bu adımların kablolarını doğru çizmek için gereken plan verisi düzeltmeleri (aşağıda §4).

**Dışında (faz 2):** bitmiş kablo adımları 5.2, 6.x, 7.x, 8.x, 9.x. Bunların çizimi için
önce kurulumda gerçekleşen yerleşim (güç bloğu sağ duvarda dik, Q1 kafesi, kart B'nin
gerçek yönü) plana işlenmeli; yoksa çizim gerçeğe uymaz. Tasarım bu adımları yalnız veri
ekleyerek kapsayacak şekilde kuruluyor (K9). Engelden kendisi kaçan otomatik rota arama da
dışarıda (K4).

## Kararlar

| # | Karar | Gerekçe / yanlışsa maliyeti |
|---|---|---|
| K1 | **Kullanıcı:** kablolar `8-kutu.html`'in adım adım görünümünde, hem çizimde hem 3B'de gösterilir | — |
| K2 | Kapsam önce 10.3 / 10.4 / 11.1 | Kullanıcı tam orada; arka duvar parçalarının plandaki yerleri gerçekle aynı. Bitmiş adımlar gerçek yerleşim plana girmeden yanlış çizilirdi. Maliyet: 5–9'un çizimi faz 2'ye kalır |
| K3 | **Uç (terminal) verisi:** her parça için adlı uçlar, parçanın kendi köşesine göre ofset (x, z, y). Ör. `MT1`: `IN+ IN− OUT+ OUT−`; `IZ` (B0505S): `+Vin −Vin −Vout +Vout` (veri sayfası: 1·2·4·6); `KL`: `+ −`; `F0/F1P/F2`: `1 2` (klipsler); `YUVA1/2`: `+ −` (yuvanın kendi telleri yaysız uçtan çıkar); `TP1`: `B+ B− OUT+ OUT−`; panelde `SWP1` bacakları, `LED1` bacakları, `COM`/`CAL` lehim kulağı; `ESP32` pinleri; kart A'nın tel delikleri (C34, C36, J5) kart yerleşiminden dönüştürülür | Tek kaynak `kutu_veri`. Uç ofsetleri ölçülmedi, modül fotoğrafı/veri sayfasından **tahmin** (±3 mm) — çizim "yaklaşık yer" gösterir, kesim boyuna %15 pay girer |
| K4 | **Güzergah = kural + ara nokta istisnası.** Varsayılan (arka bölgedeki iki uç): uçtan öne çık (en derin ucun 3 mm önü), dik, yatay, gir — eksen eksen. Gövdeye giren ya da öne uzanan kablolar `KABLO_YOL`'da açık **ara noktalarla** (x, y, z) ve kullanıcıya söylenen yol cümlesiyle ("arka duvarın dibinden", "kapağın altından öne") tanımlı. *(Plan sırasında prototiple güncellendi: adlı kanal fonksiyonları yerine ara nokta — 26 kablonun 13'ü istisna, hepsi çarpışmasız doğrulandı)* | Tam otomatik arama öngörülemez rota üretir ve 3B'de anlatması zor; adlı kanal fonksiyonları kart A'nın arka kenarı (duvara 12 mm) gibi dar geçitleri genelleyemedi, açık nokta denetimle sınanıyor |
| K5 | Bağlantıların **tek kaynağı** `PIL_KABLOLAR` (10.3/10.4). 11.1 için yeni kayıtlar: J5 10 telli kablo (ESP32 pinleri → kart A'daki J5 başlığı; tel eşlemesi Yerleşim 1.12'den okunur, yeniden yazılmaz) ve CAL teli (GPIO10 → 22 kΩ → CAL lehim kulağı). Çizim, tablo ve bilgi kartı aynı listeden | B55c dersi: iki ayrı liste kayar. J5 bugün hiçbir kablo listesinde yok, yalnız metinde |
| K6 | Arka duvar kabloları **içeriden bakış** çiziminde (x soldan, aynasız). Mevcut "dışarıdan / arkadan bakış" çizimleri delik adımlarında kalır | B63: arka çizimin aynalı olması kullanıcıyı yanlış ovale götürmüştü. Kablo işi içeriden yapılıyor |
| K7 | Kablo adımlarının çizimleri: ① arka duvar içeriden (ana çizim) ② kuşbakışı (ön panele giden kablolar: PİL anahtarı, C34/C36, LED→COM, CAL) | Ön panele uzanan kablo arka duvar görünüşünde kaybolur |
| K8 | 3B'de kablo = **ince bloklar zinciri** (2 × 2 mm kesit, her Manhattan parçası bir blok); mevcut blok çizicisi değişmeden kullanılır; kablo o adımda görünmeye başlar (`gor`), o adımda vurgulu (`vur`), bilgi kartı anahtarı `k` | Yeni çizim türü (silindir/eğri) eklemek gereksiz; dik açılı kablo zaten gerçeğe yakın |
| K9 | Faz 2 için: bir kablo adımı yalnız uç verisi + `KABLO_YOL` eklenerek kapsanır, kod değişmez | Bitmiş adımlar sonra kolay eklensin |
| K10 | Renk **role göre** (kullanıcının gerçek tel rengine değil): artı (5 V/24 V) kırmızı · paket/kart GND siyah · **−12 tarafı mavi** · sinyal (J5, CAL) turuncu · sigorta–hücre yolu koyu kırmızı. Lejant çizimin altında | Yalıtım kuralı (B0505S'in iki tarafı) renkle görünür olur. Maliyet: kullanıcının teli başka renkse çizimle karışabilir — lejant "rol rengi" der |
| K11 | Kesim boyu = güzergah uzunluğu × 1.15, yukarı 1 cm'e yuvarlanmış; tabloda ve kartta aynı fonksiyondan | Uç tahmini ±3 mm + kıvrım payı |
| K12 | Kesit: hücre/paket kolu ve MT1 girişi 0.5 mm²; diğer besleme 0.5 mm²; J5 hazır jumper; CAL ince tel | 10.3'teki "0.5 mm² rahat taşır" ile aynı; 1.16 A en kötü hal |

## §4 — Aynı adımlarda düzeltilecek plan verisi ve metinleri

Çizim yanlış bir şeyi göstermesin diye bu adımların bilinen hataları aynı işte düzeltilir
(hepsi bu oturumda kullanıcıyla konuşuldu):

1. **F2 çıkışı:** F2.2 → F1P.2 (TP1.B+ ile aynı düğüm; kullanıcı böyle kurdu). Graf aynı
   kalır, uç değişir.
2. **Hücre telleri:** H1+/H2+ = yuvanın kendi kırmızı teli doğrudan F1P/F2 klipsine; yuva
   yönü: YUVA1'in + ucu solda, YUVA2'nin sağda.
3. **GÜÇ lambası katodu → COM jakının lehim kulağı** (kart GND). Eski metin "klemens/GND
   noktası" diyordu; 10.5'te J5 takılı değilken MT1 eksisine bağlı katot LED'i yakmaz.
4. **10.3 kontrolü:** "hücreler takılı değilken TP1.B− ↔ kart GND öter" yanlış (J5'ten
   önce yol yok; FS8205 gövde diyotları da açık tutar). Yerine uç uca kontroller; paket–kart
   GND sınaması 11.1'e taşınır. Graf modelindeki `ESP32.GND = KART_GND` varsayımı "J5 takılınca"
   diye açıklanır.
5. **Sigorta yuvası:** FUS009 iki ayrı çıplak klips → "iki klips + plaket şeridi (≤ 25 mm)"
   (KF-03 denendi, yerleşime sığmadı: DEVIR'e yazılır).
6. **B0505S bacakları:** gövdede ad yok; 1 = +Vin, 2 = −Vin, 4 = −Vout, 6 = +Vout, yan yana
   iki bacak giriş.
7. **Yapıştırma:** kullanıcı modülleri (MT1, MT2, B0505S) de sıcak silikonla yapıştırıyor
   (İPA ile sökülür). `YAPISTIRMA_ISTISNA` ve 10.2 metni buna göre; kartlar, ESP32, şönt,
   Q1 yapıştırılmaz kalır.
8. **MT1/MT2 kabloları tezgahta önceden lehimlenir** (TP1 gibi), uçlar etiketli.

## Doğrulama

`kutu.py` yeni bölüm (B73) iddiaları:
- 10.3/10.4/11.1'in her bağlantısı tam bir kez çizilmiş; her çizgi bir bağlantı (iki yön).
- Her uç bilinen bir terminal; terminal kendi parçasının gövdesinin üstünde/kenarında.
- Güzergah kutunun içinde; uç parçaları dışında hiçbir parçanın içinden geçmiyor; kart B'nin
  zincir alanından ve HV giriş noktasının 13 mm çevresinden geçmiyor.
- −12 tarafı kabloları kart GND tarafına değmiyor (mevcut union-find, yeni uçlarla).
- Kesim boyu ≥ güzergah uzunluğu; tablo ve kart aynı sayıyı gösteriyor.
- 2B ve 3B aynı güzergahtan (3B blok uzunlukları toplamı = güzergah uzunluğu).
- §4 düzeltmeleri metinde (eski cümleler yok, yenileri var).

Mutasyonlar (`mutasyon.py`, B50 grubu): bir güzergahı sil · bir ucu başka parçaya taşı ·
güzergahı MT1'in içinden geçir · kesim payını 1.0 yap · F2.2'yi TP1'e geri al (metin–veri
ayrışması) · LED katodunu MT1 OUT−'ye al (10.5 lamba iddiası kırmızı).

Tarayıcı testi (`kutu_ipucu_test.py`, B57 grubu): 10.4 adımında bir kablonun üstüne gelince
kartta "MT2 OUT+ → KL +" görünür; tablodaki satıra tıklayınca o kablo vurgulanır; 3B'de
kablo seçilebilir. JS bozulursa test kırmızı.

Zincir: `kutu.py` yeşil, `mutasyon.py` B50/B57 hepsi yakalanır, `dogrula3.py` sayım kilidi
bilerek güncellenir.

## Riskler ve açık noktalar

- Uç ofsetleri tahmin: MT3608 pedlerinin yeri modülden modüle 1–3 mm oynar. Çizim yön ve
  sıra gösterir; milimetrik lehim yeri değil.
- Kullanıcının kurduğu gerçek düzen planla ayrışırsa (10.2'de parçaları başka yere
  yapıştırırsa) çizim yanlış olur — 10.2 fotoğrafıyla karşılaştırılır.
- Depo durumu: çalışma ağacı `1d-eslestirme` dalında ve kullanıcının commit'lenmemiş B55–B70
  işini taşıyor. Bu iş de commit'siz kalır; commit/push kullanıcı isteyince.

## Dokunulacak dosyalar

`uretim/kutu_veri.py` (uçlar, `KABLO_YOL`, `PIL_KABLOLAR` düzeltmeleri, CAL kaydı, §4
metinleri) · `uretim/kutu.py` (güzergah hesabı, içeriden arka duvar çizimi, kuşbakışı
kabloları, `sahne()` kablo blokları, `bi_kablo`, tablo↔çizim bağı, B73 denetimi) ·
`uretim/kutu_3b.py` (yalnız gerekirse: kablo bloklarının seçim önceliği) ·
`uretim/mutasyon.py` · `uretim/kutu_ipucu_test.py` · `uretim/beklenen_sayim.json` ·
`DEVIR.md` (5.12.73 B73) · `BELGELER/8-kutu.html` (üretilir).
