# README yenileme planı — 2026-10-09

**Durum:** YAZILDI (2026-10-10). Bütün ekran görüntüleri gerçek karttan (demo yok). Kalan: belgelerin ve görsellerin İngilizcesi.

**İstek (kullanıcı):** README kolay, basit, anlaşılır ve **görsellerle** desteklenmiş olsun: kutunun gerçek
fotoğrafları, birisi yapmak isterse hangi HTML belgeleriyle yapacağı (belgelerden örnek görüntüler), PC ve mobil
uygulamanın yapabildikleri ve içinden ekran görüntüleri.

**Kararlar (kullanıcı onayladı):** README.md **Türkçe** (ana), aynı görsellerle **README.en.md** İngilizce
(bugünkü README.tr.md → README.md'ye dönüşür; bugünkü İngilizce README.md'nin geliştirici içeriği
**GELISTIRICI.md**'ye taşınır, silinmez). Yapı aşağıdaki gibi.

## Yapı

1. **Vitrin** — kutunun bitmiş hali (kullanıcı fotoğrafı) + tek cümle tanım + lisans.
2. **Ne yapar** — altı kutucuk, her birinin altında görsel: voltmetre/ampermetre/wattmetre · osiloskop ·
   pil kapasite testi · kartın kendi kaydı · PC uygulaması · Android uygulaması.
3. **Uygulamalar** — PC: Canlı, Osiloskop, pil deşarj eğrisi, Kayıtlar + kayıt görünümü, Karşılaştırma,
   "ⓘ Bağlantı" penceresi (ön panel resmi). Telefon (Honor): Canlı, Pil testi, Kayıtlar — yan yana.
4. **Kendin yap** — `BELGELER/` rehberleri, her biri küçük resim + bir cümle: 1-ne-yapabilir, 2-malzemeler,
   7-yerlesim (plakete adım adım lehim), 8-kutu (3B kutu kılavuzu), 3-pil-testi, 6-ag, 9-pc-uygulamasi;
   HTML'lerin nasıl açılacağı (indir + tarayıcıda aç; istenirse GitHub Pages).
5. **İçi nasıl** — kutunun içi (kullanıcı fotoğrafı) + basit blok şema (18650 → TP4056 → MT3608/B0505S →
   analog kart ±12 V → ADS1115 ×2 → ESP32-S3; Wi-Fi/USB → PC / telefon).
6. **Hızlı başlangıç** — firmware yükleme (`uretim/yukle.py`), PC uygulaması (`kopru/pc.py`, kısayol), APK,
   Wi-Fi ayarı (Ayarlar → Ağ), web parolası.
7. **Güvenlik** — kısa: şebekeye bağlanmaz, HV kuralları, COM'a güç akımı sokma, ADS girişine >3.3 V verme.
8. **Geliştiriciler için** — doğrulama zinciri birkaç satır (`dogrula3.py --tam`, mutasyon) + GELISTIRICI.md.
9. **Lisans** (MIT).

⚠ Eski README'de eskimiş bilgi var ("18 adım"); yeni metinde sayı yazılacaksa zincirden okunur.
⚠ `uretim/mutasyon.py` B26 girdileri README.md'de `"# "` çapasını arıyor — README.md bir `# ` başlığıyla başlamalı.

## Görseller

Yer: `gorsel/readme/` (PNG/JPG, tek tek ~≤300 KB, genişlik ≤ 1440 px).

| Dosya | Kaynak | Not |
|---|---|---|
| kutu-on, kutu-capraz, kutu-ic, kart-a, pil-duzenek | **kullanıcı fotoğrafları** | EXIF/GPS temizlenecek; sade arka plan |
| pc-canli, pc-skop, pc-pil | panel **demo kipi** (`arayuz3/sunucu.py`, `http://localhost:8772/?demo#/...`) | kişisel veri yok |
| pc-kayitlar, pc-kayit, pc-karsilastir | PC köprüsü (`http://olcum.localhost:8770`) gerçek arşiv | "deneme ful" pil oturumu (#64955) |
| pc-baglanti | ⓘ Bağlantı penceresi | ön panel resmi |
| tel-canli, tel-pil, tel-kayit | Honor (`adb exec-out screencap`) | durum çubuğu kırpılır |
| belge-yerlesim, belge-kutu, belge-malzeme, belge-pil | `BELGELER/*.html` başsız Chromium | 8-kutu WebGL: `--use-angle=swiftshader` |

**Gizlilik (depo herkese açık):** Ağ adı (SSID, komşu ağlar), IP adresi, kart kimliği, cihaz seri numarası,
e-posta, kullanıcı klasörü yolu görünen ekran KULLANILMAZ ya da kırpılır (Ayarlar → Ağ / Eşleştirme / Bu telefon
görüntülenmez). Push öncesi `python uretim/gizlilik_dogrula.py` + görsellerin gözle denetimi.

## Araç notları (2026-10-09 denemesi)

- Playwright Node kütüphanesi depoda DEĞİL: yolu `PLAYWRIGHT` ortam değişkeniyle verilir
  (Python playwright KURULU DEĞİL). Betik taslağı: `uretim/readme_gorsel/cek.js`.
- Demo kipinde Canlı grafiği ilk açılışta ~15 s'de geliyor (tembel modül) — çekmeden önce ≥ 15 s bekle.
- Osiloskop demo sinyal seçicisi: 50 Hz sinüs / 1 kHz sinüs / 1 kHz kare / 20 kHz PWM / 20 kHz anahtarlama +
  çalma / 100 Hz doğrultulmuş / sabit 12 V; düğmeler "Yakala", "▶ Sürekli", "Otomatik"; FFT penceresi seçicisi var.
- Pil testi demo: "Li-ion 3.0 V" hazır ayarı + "Testi başlat" (sahte kart zamanı hızlandırır).
- Telefon: kart ve telefon aynı ağda olmalı; Honor hotspot sahibiyse uygulama hotspot alt ağını tarar.
