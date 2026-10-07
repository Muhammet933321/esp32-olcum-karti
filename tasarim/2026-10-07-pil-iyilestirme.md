# Pil testi iyileştirmesi (PT) — 2026-10-07

**Durum:** ONAYLI (kullanıcı: "Uygun, yap"). Kullanıcı 3.3 Ω 11 W taş dirençle 18650 deşarjı yaptı, kesme 3 V;
test 2 s'de bitti. İstekler: OCV grafikte/kayıtta görünsün; kayıt hızı seçilsin (1/s, 20/s, her örnek); iç
direnç ölçümü aç/kapa, varsayılan kapalı.

## Bulgu (kartın kaydından, oturum 64108 / 64114)

OCV 4.11 V; yük altında ortalama 3.13 V / 0.82 A; saniye içinde V 3.01…3.26 (±0.12 V), I ±0.01 A. Bitiş
`durum=2` (kesme), `v_son` 2.99 V, 2.2–2.6 s. **Kök sebep:** `pil_isle()` kesmeyi TEK ANLIK örnekte veriyor
(`pil_kesmeli_mi(o.volt, …)`, ~400 örnek/s) — gürültünün ilk dibi kesiyor. (Ayrıca pil + kablo yolu ~1.2 Ω:
kullanıcıya bildirildi; kart kusuru değil.)

## Kararlar

| # | Karar |
|---|---|
| PT1 | Kesme **üstel kayan ortalama** ile: τ = 1 s (`PIL_KESME_TAU_MS 1000`), yük AÇIK ve en az 1 τ geçmişken `ema ≤ kesme` → BITTI. Anlık örnek kesmez. `v_son` yine son anlık değer (kayıt), kesme kararı ema ile; PIL_SONUC `v_son` alanı EMA'yı yazar (kesme anını temsil eder). |
| PT2 | **OCV ön evresi** 5 s (`PIL_OCV_MS 5000`): `p1` kabul edilince yük KAPALI kalır, durum CALISIYOR, evre OCV; bu sürede noktalar kaydedilir (yük akımı ~0, mAh birikmez), kesme denetlenmez (başlangıç reddi zaten `v_bos ≤ kesme`). 5 s sonra yük açılır, evre YUK. Azami süre başlangıçtan sayılır; DCIR zamanlayıcısı yük açılınca başlar. OCV evresindeki Nokta'lara `bayrak` biti **KN_OCV** (kayit_bicim'de bir sonraki boş bit) konur. |
| PT3 | **Kayıt hızı** `Pr<hz>` komutu: izinli 1, 5, 20, 50 ve **0 = her örnek**. Mevcut `Ayar3.pil_kayit_hz` alanı (BÜYÜMEZ → AYAR3_IMZA değişmez → kalibrasyon sıfırlanmaz); anlamı: 0 = her örnek. Eski kayıtlı 0.2 değeri geçerli kalır (okunur), yeni giriş yalnız listeden. `P` (argümansız) satırı hızı ve DCIR'ı da yazar. |
| PT4 | **Her örnek (0):** pil oturumunda ölçüm oturumunun 1C-2 AYRINTI kayıtları (tür 9, 6 B/örnek) yazılır; Nokta'lar 1/s'de sürer (özet/eksen için); `/pil` canlı eğrisi (RAM halkası) en çok 20/s. Bellek: ~1 sa'te dolar → form uyarır. Ayrıntı kipinin kısıtları (hazır alan, KA_SILME) aynen. |
| PT5 | **DCIR aç/kapa** `Pd1` / `Pd0`, **varsayılan KAPALI**. Ayrı NVS ad alanı `pilayar`, anahtar `dcir` (u8). Kapalıyken DCIR darbesi HİÇ olmaz; PIL_AYAR olayında `dcir_aralik_ms = 0` (biçim değişmez; çözücüler 0'ı "kapalı" okur). |
| PT6 | `/pil` başlığına `evre=ocv|yuk`, `kayit_hz=`, `dcir=0|1` eklenir (eski alanlar aynen). |
| PT7 | Panel Pil testi formu: kesme (var), **Kayıt hızı** seçici (1/s · 5/s · 20/s · 50/s · her örnek) + seçilen hızda tahmini azami kayıt süresi, **İç direnç ölçümü** onay kutusu (varsayılan kapalı). Başlatırken `Pr…`, `Pd…`, `P<v>`, sonra `p1`. Grafik: OCV evresi ayırt edici (gölge/etiket "OCV"), DCIR kapalıyken DCIR tablosu "kapalı" der. Kayıt görünümü: KN_OCV noktaları ve pil oturumundaki AYRINTI örnekleri çizilir. |
| PT8 | Firmware sürümü `A3-PT1`. |
