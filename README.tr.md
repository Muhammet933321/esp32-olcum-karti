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
python dogrula3.py     # Aşama 3 — GÜNCEL — 17 adım, ~6 dk
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
