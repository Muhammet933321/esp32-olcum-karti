# README.en.md için gereken İngilizce ekran görüntüleri

*English: the screenshots [README.en.md](../../../README.en.md) expects in this folder — same file names as the
Turkish ones in `gorsel/readme/`, captured with the panel, the PC app and the guides switched to English.*

[README.en.md](../../../README.en.md) aşağıdaki 12 dosyayı **bu klasörde** (`gorsel/readme/en/`) arıyor. Adlar
Türkçe görüntülerle (`gorsel/readme/*.png`) **birebir aynı**; her biri Türkçesinin İngilizce karşılığı olmalı:
aynı ekran, aynı ölçüm, aynı kırpma ve boyut — yalnız arayüz dili İngilizce.

✅ **12 görüntünün hepsi gerçek karttan çekildi** (2026-10-11, firmware A3-SK2, panel çevirisi tamamlandıktan sonra).
PC ve rehber görüntüleri `uretim/readme_gorsel/cek_en_pc.js` ve `cek_en_belge.js` ile; telefon görüntüleri Honor'dan
`adb` ile (Türkçeleri Xiaomi'dendi: başlık iki satıra kırılıyor, boyut aynı). Canlı ekranlarda ölçüm 18650 + 3.3 Ω
(~3.82 V · 1.11 A · 4.23 W), grafikte yükün takılıp çıkarılması görünüyor. Osiloskopta sinyal Arduino Uno **D9**
(D13'te alt seviye kayıyor — `tasarim/1-acik-isler.md` SK-8).

## Neden yalnız PNG'ler?

`gorsel/readme/*.png` dosyaları arayüzün ve rehber sayfalarının ekran görüntüleri — içlerinde yazı var, o yüzden
her dilin kendi kopyası gerekiyor. Fotoğraflar (`kart-a.jpg`, `kutu-ic.jpg`, `kutu-on.jpg`) gerçek donanımın
fotoğrafı; üzerlerinde arayüz yazısı yok (kutunun üstündeki jak etiketleri fiziksel olarak Türkçe ve her dilde
aynı). Bu yüzden iki README de fotoğrafları ortak `gorsel/readme/` yolundan kullanıyor; `en/` altına kopyaları
konmaz.

## Çekim ayarları

- **Panel / PC uygulaması:** **Settings → Language and appearance** (Ayarlar → Dil ve görünüm) bölümünden dil
  **English** yapılır. Görünüm Türkçe görüntülerdekiyle aynı kalır (PC: koyu; telefon: koyu).
- **PC uygulaması:** `kopru/pc.py` (`kopru\PC Baslat.bat`), panel `http://olcum.localhost:8770`. Pencere boyutu
  Türkçe görüntüyle aynı genişlikte olsun (aşağıdaki boyutlar).
- **Telefon:** Android uygulaması, `adb exec-out screencap -p`; üstteki durum çubuğu kırpılır, 540 × 1086'ya
  küçültülür.
- **Rehberler:** `BELGELER/en/*.html` başsız Chromium'da, 1280 px genişlikte; `8-kutu.html` WebGL istediği için
  `--use-angle=swiftshader`. Taslak betik `uretim/readme_gorsel/cek.js` şu an Türkçe sayfaları (`BELGELER/`) ve
  `tr-TR` yerel ayarını kullanıyor; İngilizce çekimde `BELGELER/en/`, `en-US` ve `CIKIS=gorsel/readme/en`
  verilmeli.
- **Gizlilik (depo herkese açık):** ağ adı (SSID, komşu ağlar), IP adresi (`192.168.4.1` hariç), kart kimliği,
  cihaz seri numarası, e-posta ve kullanıcı klasörü yolu görünen hiçbir ekran kullanılmaz ya da kırpılır;
  **Settings → Network / Pairing / This phone** ekranları çekilmez. Göndermeden önce
  `python uretim/gizlilik_dogrula.py` ve her görüntüye gözle bakılır.
- Boyut: tek tek ~≤ 300 KB, genişlik ≤ 1440 px.

## Dosyalar

### PC uygulaması (dil: English)

| Dosya | Türkçesi (boyut) | Ne çekilecek |
|---|---|---|
| `pc-canli.png` | `pc-canli.png` (1440 × 775) | **Live** ekranı: Voltage / Current / Power / energy kartları ve grafik. Ölçüm: bir 18650 hücre 3.3 Ω dirence bağlanıp çıkarılıyor (~3.10 V · 0.875 A · 2.72 W); grafikte yükün takılıp çıkarıldığı basamaklar görünsün. |
| `pc-skop.png` | `pc-skop.png` (1440 × 762) | **Oscilloscope** ekranı: bir Arduino'nun ürettiği 1 kHz / 5 V kare dalga; kartın ölçtüğü frekans (~1.001 kHz), doluluk (~%49.9) ve yükselme süresi (~10 µs) görünür olsun. |
| `pc-pil.png` | `pc-pil.png` (1152 × 1165) | **Recordings** → 18650 pil testi kaydı (3.3 Ω yük, kesme 2.9 V, **1432 mAh · 5.22 Wh**, 1 saat 18 dakika): deşarj eğrisi (başta OCV bölümü) ve sonuç özeti. |
| `pc-karsilastir.png` | `pc-karsilastir.png` (1128 × 657) | **Compare** ekranı: iki 18650 hücrenin gerçek testleri aynı grafikte (1366 mAh ve 1432 mAh). |
| `pc-baglanti.png` | `pc-baglanti.png` (920 × 620) | Sol şeritteki **ⓘ Wiring** düğmesiyle açılan **What plugs where** penceresi, **Current** sekmesi seçili: ön panel resmi, YÜK 1 / YÜK 2 vurgulu, devre çizimi ve "do not clip anything to COM" uyarısı. |

### Android uygulaması (dil: English)

| Dosya | Türkçesi (boyut) | Ne çekilecek |
|---|---|---|
| `tel-canli.png` | `tel-canli.png` (540 × 1086) | Telefonda **Live** ekranı, kart bağlı (üst şeritte "Board connected · WiFi"); 18650 + 3.3 Ω yük takılıyken gerilim, akım, güç ve enerji kartları (~3.1 V · ~0.85 A · ~2.65 W). |
| `tel-kayit.png` | `tel-kayit.png` (540 × 1086) | **Recordings** → bir pil testi kaydının **Chart** bölümü: deşarj eğrisi, OCV işareti ve altındaki gezinme şeridi (Türkçesindeki 18650 kaydı). |
| `tel-pil.png` | `tel-pil.png` (540 × 1086) | **Battery test** → yeni test formu (**New test**), test başlamadan: kesme gerilimi alanı, Li-ion / kurşun-asit hazır düğmeleri, kayıt hızı, DCIR onay kutusu, oturum adı ve başlat düğmesi. |

### Rehber sayfaları (`BELGELER/en/`)

| Dosya | Türkçesi (boyut) | Ne çekilecek |
|---|---|---|
| `belge-yerlesim.png` | `belge-yerlesim.png` (1280 × 800) | `BELGELER/en/7-yerlesim.html` (**Layout**), adım **4.1 — R4, R6, R7, R34**: plaket çizimi (yalnız bu adımın parçaları parlıyor), adım gezgini ve altındaki parça / değer / bacak → delik tablosu. |
| `belge-kutu-3b.png` | `belge-kutu-3b.png` (890 × 441) | `BELGELER/en/8-kutu.html` (**Enclosure**), 3D görünüm: bitmiş, kapağı kapalı kutu, izometrik. (Görüntüde neredeyse yazı yok; adların tutarlı kalması için yine İngilizce sayfadan çekilir.) |
| `belge-kutu-ici.png` | `belge-kutu-ici.png` (890 × 441) | Aynı sayfa, duvarlar saydam: kutunun içi, parça adları (A, ESP32, Q1, RS …) ve kablolar. |
| `belge-kutu-adim.png` | `belge-kutu-adim.png` (1280 × 1000) | Aynı sayfa, adım **10.1** (MT1'i 5.0 V'a, MT2'yi 24.0 V'a yüksüz ayarlama): üstte adım gezgini, ortada 3D görünüm (kablolar açık), altta adımın yazılı talimatı. |
