# Ölçüm Kartı — Türkçe kılavuz

> İngilizce tanıtım için [README.md](README.md). Bu dosya projenin
> kendi Türkçe rehberi: nereye bakılır, ne çalıştırılır.

Voltmetre · ampermetre · wattmetre · enerji sayacı · osiloskop · pil
kapasite testi. ESP32-S3 + 2× 16 bit ADC, tarayıcıdan kullanılıyor.

**Üç bağlanma yolu var:** USB kablosuyla bilgisayardan · kartın kendi
WiFi'sinden **telefonla, bilgisayar olmadan** · ya da bir PC köprüsü
üzerinden (sınırsız kayıt ve aynı anda birden çok izleyici). Hangisini
ne zaman kullanacağınız `BELGELER/6-ag.html`'de.

**Donanım henüz kurulmadı.** Tasarım bilgisayarda doğrulandı; kart
fiziksel olarak kurulmayı bekliyor.

---

## 👉 Okumak istiyorsanız: `BELGELER/`

Gözle okunacak her şey orada. Tarayıcıda açın:

| Dosya | İçinde ne var |
|---|---|
| **`BELGELER/index.html`** | **Buradan başlayın** |
| `1-ne-yapabilir.html` | Bütün yetenekler, menziller, örnek ekranlar — grafiklerle |
| `2-olcumler.html` | Neyi ne kadar hassas, ne sıklıkla ölçüyor |
| `3-pil-testi.html` | Hangi pilleri, kaç amperle, ne kadar sürede |
| `2-malzemeler.html` | Gereken her parça; elinizde olan / alınacak |
| `4-kurulum.html` | Adım adım montaj |
| **`6-ag.html`** | **Nasıl bağlanılır** — USB, telefon, PC köprüsü; hangi adres |
| `5-muhendislik.html` | Nasıl çalışıyor (isteğe bağlı) |
| `sema.pdf` | Devrenin tam şeması |

Bu sayfaların hepsi `uretim/belge-uret.py` ile **üretiliyor** — içindeki
hiçbir sayı elle yazılmadı, tasarım dosyalarından hesaplanıyor. Tasarım
değişince belgeleri yeniden üretmek için:

```
cd uretim && python belge-uret.py
```

---

## Klasörler

| Klasör | Ne |
|---|---|
| `BELGELER/` | **Okunacak belgeler** (HTML + PDF) |
| `kod/olcum-karti-a3/` | Güncel firmware (ESP32-S3) |
| `sema3/` | Güncel şema (KiCad) |
| `arayuz3/` | Güncel web arayüzü — hem PC'den hem karttan servis ediliyor |
| `kopru/` | **PC köprüsü** — kartı USB'den okuyup telefona/PC'ye yayınlar, diske arşivler |
| `uretim/` | Doğrulama zinciri, simülasyonlar, belge üreteçleri |
| `arsiv/` | Eski aşamalar — Aşama 1 (Arduino) ve Aşama 2 |
| `DEVIR.md` | Mühendislik günlüğü (uzun, kronolojik) |
| `uretim/_tezgah.md` | **Üretiliyor** — tezgahta ölçülecekler |

Çift tıklanacaklar: **`Kopru Baslat.bat`** (PC köprüsü — telefondan
bağlanmak için). Arayüzü USB ile açmak için `cd arayuz3 && python sunucu.py`.

---

## Doğrulama zinciri

Tasarımın tamamı otomatik sınanıyor. Her iddia çalıştırılabilir bir
testle destekleniyor.

```
cd uretim
python dogrula3.py     # Aşama 3 — GÜNCEL — 18 adım, ~6 dk
python dogrula2.py     # Aşama 2 (arşiv) — 6 adım
python dogrula.py      # Aşama 1 (arşiv) — 9 adım
```

Zincir sonunda iki şey üretiyor:

* **`uretim/_tezgah.md`** — kart kurulunca tezgahta ölçülecekler. Her
  kalem, onu **doğrulayamayan adımın yanında** yazıyor; liste elle
  tutulmuyor. Başındaki *"İlk gün"* tablosu `[!]` işaretlilerden türüyor
* **`uretim/beklenen_sayim.json`** — iddia sayısı kilidi. Bir iddia
  düşerse **ya da eklenirse** zincir kırmızı döner; bilerekse
  `python dogrula3.py --sayim-kilidi-yaz`

Bir iddianın gerçekten ısırdığını görmek için:

```
python mutasyon.py                 # hafif mutasyonlar (~15 s)
python mutasyon.py --adim B22b     # tek adım
python mutasyon.py --liste         # ne koşacağını yazar
python mutasyon.py --adim B3       # tam zincir koşar (~12 dk) —
python mutasyon.py --adim B23      # bu ikisi zincirin KENDİ korumalarını sınar
```

Kaynağı **bozup** testin kırmızıya döndüğünü ölçüyor. Mutasyon bir
**kopya** üzerinde koşuyor — asıl ağaç hiç değişmiyor.

Üçü de yeşil olmalı. `dogrula3.py` şunları koşturuyor: devre
simülasyonu (ngspice), şema + netlist denetimi (KiCad), ölçüm
matematiği (gerçek firmware kodu, AVR emülatöründe), firmware derlemesi
(gerçek ESP32-S3 derleyicisi), arayüz, **PC köprüsü** (röle bayt-şeffaf
mı, sürücü hakemi çalışıyor mu), **kartın web katmanı** (SSE, komut ucu,
CSRF yüzeyi) ve malzeme listesi.

> Zincir **tasarımı** doğrular, kurulmuş bir kartı değil. Gerçek bileşen
> toleransları, sıcaklık sürüklenmesi ve gürültü tezgâhta ölçülür.

---

## 🔌 ESP32 geldiğinde — sırayla

> Bu bölüm **kart elinize geçtiği gün** için. Analog ön uç kurulmuş olmasına
> gerek yok; aşağıdakilerin çoğu **çıplak ESP32-S3 ile** koşuyor.

**1 · Firmware'i yükle.** Tam FQBN şart — varsayılanlar çalışmaz:

```bash
cd projeler/olcum-karti
arduino-cli compile --warnings all \
  --fqbn esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=huge_app \
  kod/olcum-karti-a3
arduino-cli upload -p COM? \
  --fqbn esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=huge_app \
  kod/olcum-karti-a3
```

`FlashSize=16M` olmadan LittleFS'in `0x310000` ofseti 4 MB sınırına düşer;
`PSRAM=opi` olmadan 8 MB PSRAM hiç açılmaz. Tek kaynak `uretim/hedef2.py`.

**2 · Arayüzü karta yaz.**

```bash
cd uretim
python arayuz-uret.py     # LittleFS görüntüsünü paketle
python arayuz-yaz.py      # 0x310000'e yaz (esptool)
```

⚠️ **İKİ USB SOKETİ VARSA: UART/COM soketine takın, yerel USB'ye değil.**
Firmware `Serial`i UART köprüsünde tutuyor — `hedef2.py` `CDCOnBoot`/
`USBMode` seçeneklerini **bilerek** eklemiyor (yerel CDC tezgah ilk
açılışını bozabilir, bu iş 4.11'de ayrı ele alınacak). Yanlış sokette
hiçbir satır gelmez ve boşuna sürücü aranır. Aynı sebeple `--sifirla`'nın
DTR/RTS reset'i **UART soketinde çalışır**.

**3 · Bringup koşucusunu çalıştır** — elle denenmesi gerekmeyen her şeyi
otomatik sınıyor:

```bash
python tezgah_kart.py --liste            # ne yapacağını göster
python tezgah_kart.py --sifirla          # aşama 0: çıplak ESP32
python tezgah_kart.py --sifirla --asama 1        # ADS'ler bağlıyken
python tezgah_kart.py --sifirla --http olcum.local   # web katmanı da
```

**24 denetim.** Açılış afişi (PSRAM boyutu, LittleFS, ağ kipi), komut
yüzeyi, çıplak `g`/`i` reddi (K3 tuğlalama), `R` onay kapısı, I²C taraması,
`D` satırının biçimi/hızı/**örnek sayısı**, ve web tarafında CSRF · jeton ·
`p0` serbestliği · Host beyaz listesi.

⚠ Açılış afişi yalnızca açılışta basılıyor. `--sifirla` DTR/RTS ile reset
denemesi yapıyor ama **yerel USB CDC'li kartlarda bu çalışmaz** — o zaman
EN düğmesine basıp komutu tekrar çalıştırın. Afiş alınamazsa PSRAM ve
LittleFS denetimleri **atlanır**, kırmızı olmaz.

🔴 **Koşucu hiçbir aşamada yük sürmüyor.** Pil deşarjını başlatan komut
otomatik gönderilmiyor; failsafe ve baypas denetimi elle yapılacak.

**4 · İlk gün ölçümleri** — `uretim/_tezgah.md`'nin başındaki `[!]` işaretli
9 kalem. Bunlar multimetre isteyen, koşucunun yapamadığı şeyler. En kritiği:
**+3V3 rayının geri beslenmesi** (USB'yi çıkar, 24 V takılı bırak, rayı ölç
— beklenen 1.670 V).

**5 · Çift çekirdek kararı.** Koşucu `K` satırından `loop_azami_us` okuyup
**20 000 µs** eşiğiyle karşılaştırıyor. Üstündeyse ölçüm döngüsü çekirdek
1'e taşınacak (5.12.34); altındaysa **yapılmayacak**. Bu tek ölçüm, aylardır
açık duran bir mimari kararı kapatıyor.

---

## ⚠️ Emniyet — önce bunu okuyun

**615 V öldürür ve bu kart izole DEĞİL.** USB takılıyken kartın toprağı
bilgisayarınızın toprağıdır; şebeke referanslı bir devreye (izole olmayan
bir SMPS'in birincil tarafı gibi) bağlarsanız **bilgisayarınıza şebeke
gerilimi taşırsınız.**

**Pille yüzdürmek çözüm değil.** Arıza analizi (B15/D2) bunu ölçtü:
yüzdürmek **bilgisayarı kurtarır, sizi kurtarmaz** — kart o anda şebeke
potansiyeline çıkar ve **kartın her noktası** tehlikeli olur. 615 V,
yüzen alet sınırının **14.6 katı**. Şebeke referanslı ölçüm için:

* **yalıtımlı kutu şart** — hiçbir noktaya elle erişilememeli
* delikli plakette takviyeli yalıtım için **5 delik atlayın** (12.7 mm)
* enerji varken karta **dokunmayın**

Ayrıntısı `BELGELER/4-kurulum.html`'in başındaki uyarıda.

**Ağ tarafı:** tehlikeli komutlar (pil deşarjı başlatmak, kalibrasyon
yazmak) her zaman oturum anahtarı ister, ama **web parolası varsayılan
olarak KURULU DEĞİLDİR** — `Ns<parola>` ile kurana kadar ağınızdaki
herkes bu komutları gönderebilir. Kart bunu açılışta yüksek sesle söyler.
**Deşarjı durdurma komutu hiçbir şey istemez** — emniyet, kolaylıktan
önce gelir.

---

## Lisans

**MIT** — bkz. [LICENSE](LICENSE). Kullanın, değiştirin, satın; telif
bildirimini koruyun. Arayüzdeki Vue 3.5.13 de MIT, aynı dosyada belirtildi.

⚠️ Lisans hiçbir garanti vermiyor ve bu proje için bunun ağırlığı normalden
fazla: **615 V'luk, hiç kurulmamış ve hiç ölçülmemiş** bir alet tasarımı.
Kendi emniyetinizden siz sorumlusunuz.

---

## Yeni bir oturuma başlıyorsanız

`DEVIR.md`'nin başındaki **"YENİ OTURUM — ÖNCE BUNU YAP"** bloğunu okuyun.
Kısaca: önce doğrulama zincirini koşturun, sonra hiçbir sayıyı
doğrulamadan kabul etmeyin.
