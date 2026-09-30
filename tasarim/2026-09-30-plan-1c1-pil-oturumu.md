# Alt proje 1C-1 — Pil testi oturumu + oturuma ad/not Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Her pil testi kartın flaşında kendi oturumu olarak saklansın: noktalar, DCIR olayları, sonuç. Kayıtlara ad, etiket ve not eklenebilsin. PC bunları kaybetmeden eşitlesin.

**Architecture:**
- **Biçim:** `kayit_bicim.h`'ye OLAY (7) ve NOT (8) kayıtları, `KN_DCIR` bayrağı, üç bitiş sebebi ve `PIL` oturum türü eklenir. Python eşi aynı vektörlerle sınanır.
- **Yazıcı ve yönetici (platformsuz):**
  - Yeni işlevler: `ky_olay`, `kyn_olay`, `kyn_pil_bitir`, `kyn_not`.
  - `ky_baslat` sürmekte olan oturumu "başka oturum" sebebiyle kapatır.
  - Açılışta ölçüm dışı açık oturum kapatılır.
  - Hepsi AVR emülatöründe açılıştan açılışa sınanır.
- **Firmware yapıştırıcısı:** mesajlar (`KM_PIL_BASLAT`, `KM_OLAY`, `KM_PIL_BITIR`, `KM_NOT`), pil durum makinesine bağlama, `Ga/Ge/Gn/Gx` komutları.

**Tech Stack:** C (AVR emülatörü + ESP32 Arduino 3.3.11), Python 3.14 stdlib.

**Spec:** [tasarim/2026-09-30-1c1-pil-oturumu.md](2026-09-30-1c1-pil-oturumu.md) (kararlar K1–K15), üstü [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §5/§7/§8/Ö7.

## Global Constraints

- Kayıt biçimi **elle paketlenir**, küçük uçlu; `memcpy(struct)` yok. Başlık işlevleri `static inline`. AVR ve C++ derlemesi `-Wall -Wextra` ile **uyarısız** olmalı (B71.0, B10).
- `kayit_esp.h` **`Serial` kullanmaz**: `#define Serial CIKIS`'ten önce dahil ediliyor (B72.F1).
- Python yalnız standart kütüphane.
- Biçim sürümü **2 kalır** (K11). Bilinmeyen tür geçerli sayılmaya devam eder (B13).
- Emniyet (Ö7, K6):
  - `p0` her zaman serbest.
  - `pil_durdur` yükü **her şeyden önce** keser.
  - Yeniden başlamada test sürmez.
  - Pil sürerken skop yakalaması yasak (B41).
  - Pil sürerken `GF!`, `Gb` ve `Gd` reddedilir.
- `/pil`, `PilHalka` ve bugünkü panel **değişmez** (K9).
- Depo herkese açık: sır, mutlak Windows yolu ve IP yazılmaz; `gizlilik_dogrula.py` temiz kalır.
- Kullanıcının commit'lenmemiş dosyaları (`mutasyon.py`, `beklenen_sayim.json`, `tasarim3_sabit.py`, `DEVIR.md`, `dogrula3.py`, `_tezgah.md`, `BELGELER/`…) **yalnız index cerrahisiyle** değişir; `git add` kullanılmaz.
- Kartta kalibrasyon komutu (`z g Z i s f F R`) çalıştırılmaz (ADS takılı değil). Karta yüklemeden önce NVS yedeği depo dışına (`Elekronic/.yedek/olcum-karti/`).
- Firmware sürümü `A3-1C1` (K15).

## Review Focus

1. **`KM_PIL_BITIR` kuyruk doluyken gönderilemezse:** pil oturumu açık kalmamalı. Bekleyen mesaj her turda yeniden denenmeli (Görev 4, F-iddiası + mutasyon).
2. **`p0`, kayıt görevi kilitliyken ya da kuyruk doluyken gelirse:** yük gecikmeden kesilmeli. `pil_durdur` kayıt işlemlerinden önce `pil_yuk(false)` yapmalı ve kuyruğa beklemeden göndermeli (Görev 4).
3. **Kayıt açılamazken `p1`** (tarama sürüyor, hata, dolu, bölüm yok): test başlamalı, kart "KAYDEDİLMİYOR" demeli, eski ölçüm oturumu kapatılmamalı (Görev 4, F-iddiası).
4. **DCIR darbesinin ortasında elektrik kesilirse:** açılışta oturum "yeniden başladı" ile kapanmalı, DEVAM almamalı. Yer yoksa durum 4'te bekleyip sonra kapanmalı (Görev 3, P-iddiaları).
5. **Bozuk not metni** (geçersiz UTF-8, `"`, `\`, kontrol karakteri, 120 baytı aşan) ya da bozuk `Gx` argümanları: metin temizlenmeli, bozuk argümanda kayıt yazılmamalı (Görev 1 metin testleri, Görev 4 ayrıştırıcı iddiası).

---

### Task 1: Biçim — OLAY, NOT, KN_DCIR, sebepler, PIL türü, ortak metin temizleyici

**Files:**
- Modify: `kod/olcum-karti-a3/kayit_bicim.h`: sabitler, `KayitOlay` paketleyicileri, `KayitNot` paketleyicisi, `kayit_metin_kopyala`
- Modify: `kod/olcum-karti-a3/kalgec.h`: `kgc_not_kopyala` artık `kayit_metin_kopyala(d, s, KALGEC_NOT)`
- Modify: `kopru/kayit_bicim.py`: sabitler, `olay_coz/olay_paketle`, `not_coz/not_paketle`, `Oturum.olaylar`, `Oturum.ad/etiketler/notlar`, `oturumlari_kur`
- Modify: `uretim/avr/ornek_kayit.c`: SENARYO_BICIM'e OLAY/NOT vektörleri
- Test: `uretim/test_kayit.py`: `bolum_bicim` (B71.B16–B20)

**Interfaces:**
- Produces (C, `kayit_bicim.h`):
  - Sabitler:
    - `KAYIT_T_OLAY 7u`, `KAYIT_T_NOT 8u`, `KAYIT_T_AZAMI 8u`, `KAYIT_OTURUM_PIL 2u`
    - `KN_DCIR 0x40u`
    - `KB_SEBEP_PIL 4u`, `KB_SEBEP_YENIDEN 5u`, `KB_SEBEP_OTURUM 6u`
    - `KO_PIL_AYAR 1u`, `KO_DCIR 2u`, `KO_PIL_SONUC 3u`
    - `KAYIT_OLAY_AYAR_BAYT 32u`, `KAYIT_OLAY_DCIR_BAYT 44u`, `KAYIT_OLAY_SONUC_BAYT 36u`, `KAYIT_OLAY_AZAMI 44u`
    - `KNT_AD 1u`, `KNT_ETIKET 2u`, `KNT_NOT 3u`
    - `KAYIT_NOT_METIN 120u`, `KAYIT_NOT_BAS 16u`
  - `typedef struct { float kesme_v, ocv; uint32_t azami_s, dcir_aralik_ms, dcir_ms; float kayit_hz; } KayitPilAyar;`
  - `typedef struct { uint32_t no; float v_once, i_once, v_ani, v_oturmus, r_ani, r_oturmus, mah, wh; } KayitDcir;`
  - `typedef struct { uint8_t durum, hata; float mah, wh, ocv, v_son; uint32_t sure_ms, dcir_sayisi; } KayitPilSonuc;`
  - `uint16_t kayit_olay_ayar_paketle(uint32_t kart_ms, const KayitPilAyar *a, uint8_t *p)` → 32
  - `uint16_t kayit_olay_dcir_paketle(uint32_t kart_ms, const KayitDcir *d, uint8_t *p)` → 44
  - `uint16_t kayit_olay_sonuc_paketle(uint32_t kart_ms, const KayitPilSonuc *s, uint8_t *p)` → 36
  - `uint8_t kayit_metin_kopyala(char *d, const char *s, uint8_t azami)`: `d`'nin `azami` baytı var. En fazla `azami-1` bayt metin + NUL yazılır, geri kalanı sıfırlanır; dönüş metin uzunluğu. Kurallar 1B'nin `kgc_not_kopyala`'sıyla aynı (RFC 3629, kontrol, `"`, `\`, karakter sınırı).
  - `uint16_t kayit_not_paketle(uint32_t hedef, uint8_t alan, uint32_t nokta_ms, uint32_t degistirir, const char *metin, uint8_t *p)`: metin `kayit_metin_kopyala` ile en fazla 120 B temizlenir. Dönüş `16 + uzunluk`; `p` en az `16 + 121` bayt olmalı.
- Produces (Python, `kayit_bicim.py`):
  - `T_OLAY = 7`, `T_NOT = 8`, `OTURUM_PIL = 2`
  - `SEBEP` sözlüğüne 4 "pil testi bitti", 5 "kart yeniden başladı", 6 "başka oturum başladı" eklenir.
  - `KO_PIL_AYAR/KO_DCIR/KO_PIL_SONUC`, `KNT_AD/KNT_ETIKET/KNT_NOT`
  - `olay_coz(yuk) -> dict` (`{"tur", "kart_ms", ...alanlar}`), `olay_paketle(d) -> bytes` (test vektörü için)
  - `not_coz(yuk) -> dict` (`{"hedef", "alan", "nokta_ms", "degistirir", "metin"}`; metin `errors="replace"`), `not_paketle(...)`
  - `Oturum.olaylar: list[dict]`, `Oturum.ad: str | None`, `Oturum.etiketler: list[str]`, `Oturum.notlar: dict[int, dict]` (sıra → not)
  - `oturumlari_kur` bu alanları doldurur. NOT kaydı başlıktaki `oturum` 0 olsa da yükteki `hedef`e bağlanır. Ad ve etiket için en son kayıt geçerlidir. `degistirir > 0` o notu değiştirir, metin boşsa siler.

- [ ] **Step 1: Kırmızı test.** `test_kayit.py` `bolum_bicim` içine:
  - **B71.B16:** ornek_kayit.c SENARYO_BICIM sabit girdilerle üç olay paketini ve bir NOT paketini hex basar (`OA`, `OD`, `OS`, `NT`). Python `olay_paketle`/`not_paketle` aynı baytları üretir, `olay_coz`/`not_coz` alanları geri verir.
  - **B71.B17:** metin temizleyici 120 B sınırında. 118 × 'a' + "ş" → 118 'a'. 119 × 'a' + "ş" → 119 'a' (sınır `azami-1` = 120 bayt metin). Python eşi (`_not_bekle` genellemesi, `azami` parametresi) aynı sonucu verir.
  - **B71.B18:** Python `oturumlari_kur` sentetik bir akışta:
    - Ad iki kez verilir, son geçerlidir.
    - Etiketler `"a, b"` → `["a", "b"]`.
    - İki not eklenir; biri değiştirilir, biri boş metinle silinir.
    - `oturum=0` başlıklı NOT, `hedef`e bağlanır.
    - OLAY kayıtları `olaylar`a sırayla düşer.
  - **B71.B19:** `KN_DCIR` diğer `KN_*` bitleriyle çakışmaz. Python `NOKTA` bayrak sözlüğünde adı var.
  - **B71.B20:** sürüm 2 kaldı. `KAYIT_T_AZAMI` = 8, Python `T_NOT` = 8.

  C10/C10b (kalibrasyon notu) aynen kalır; `kgc_not_kopyala` artık ortak işlevi çağırır.
- [ ] **Step 2:** `python test_kayit.py` (ya da yalnız `bolum_bicim` + `bolum_kalgec` koşan odak betiği). Beklenen: B16–B20 KIRMIZI (işlev/sabit yok → derleme hatası ya da `AttributeError`).
- [ ] **Step 3:** C ve Python eklemelerini yaz. Python `_not_bekle(ham, azami=32)` genellenir.
- [ ] **Step 4:** Test yeşil, `B71.0` uyarısız, `B71.B10` (C++) uyarısız, C10/C10b yeşil.
- [ ] **Step 5:** Commit: `1C-1 bicim: OLAY/NOT kayitlari, KN_DCIR, PIL turu, ortak metin temizleyici`

### Task 2: Noktacı — `KN_DCIR` doğru noktaya

**Files:**
- Modify: `kod/olcum-karti-a3/kayit_nokta.h`: `kn_ornek`'e `uint8_t ek` (kapanıştan SONRA yeni noktanın bayrağına OR)
- Modify: `kod/olcum-karti-a3/kayit_esp.h`: `kayit_ornek(float watt, uint32_t simdi, uint8_t ek)`
- Modify: `uretim/avr/ornek_kayit.c`: `kn_ornek` çağrıları (SENARYO_NOKTACI ve diğerleri) + yeni vektör
- Test: `uretim/test_kayit.py`: `bolum_noktaci` (B71.N-yeni)

**Interfaces:**
- Consumes: `KN_DCIR` (Görev 1)
- Produces: `uint8_t kn_ornek(KayitNoktaci *k, uint32_t simdi_ms, uint8_t menzil, int16_t ham_v, int16_t ham_i, float watt, uint8_t hata, uint8_t v_doydu, uint8_t ek, KayitNokta *cikan)`

- [ ] **Step 1: Kırmızı test.** Noktacı senaryosuna bir dizi eklenir: hız 100 ms; örnekler 10 ms aralıklı; 95–125 ms arasındaki örnekler `ek = KN_DCIR` taşır. Beklenen:
  - 0–100 noktası `KN_DCIR`'lı (95 ms örneği).
  - 100–200 noktası `KN_DCIR`'lı (105–125).
  - 200–300 noktası temiz.
  - Özellikle 100. ms'deki örnek bir önceki noktayı kapatır ve bayrağı **yeni** noktaya verir; eski noktaya ancak kendi örneğiyle düşer.
- [ ] **Step 2:** Kırmızı (parametre yok → derleme hatası).
- [ ] **Step 3:** `ek` parametresi, kapanıştan sonra `k->bayrak |= ek`. Firmware `kayit_ornek` imzası güncellenir, `.ino` çağrısı Görev 4'te bağlanır. Bu görevde `.ino` `kayit_ornek(o.watt, millis(), 0u)` olarak derlenir.
- [ ] **Step 4:** B71 yeşil (mevcut noktacı iddiaları dahil).
- [ ] **Step 5:** Commit: `1C-1 noktaci: ek bayrak (KN_DCIR) kapanistan sonra yeni noktaya`

### Task 3: Yazıcı + yönetici — olay, pil bitir, not, açılışta kapatma

**Files:**
- Modify: `kod/olcum-karti-a3/kayit_oturum.h`
  - `ky_olay`
  - `ky_baslat`: sürmekte olan oturumu `KB_SEBEP_OTURUM` ile kapatır
  - `ky_devam` yorumu
- Modify: `kod/olcum-karti-a3/kayit_yonet.h`
  - `kyn_olay`, `kyn_pil_bitir`, `kyn_not`
  - `kyn__kapat(m, id, b, nokta_sonraki, sebep)`
  - `kyn__devam_dene`: ölçüm dışını kapatır
- Modify: `uretim/avr/ornek_kayit.c`: yeni `SENARYO_PIL` (YÖNET'in NVS/NOR düzeniyle, ayrı ELF: RAM)
- Test: `uretim/test_kayit.py`: yeni `bolum_pil` (B71.P1–P9), BOLUMLER'e eklenir. `bolum_yonet`'te "kayıt sürerken `kyn_baslat`" geçen yer varsa sebep beklentisi 6 olur.

**Interfaces:**
- Consumes: Görev 1 sabitleri ve paketleyicileri
- Produces:
  - `int ky_olay(KayitYazici *y, const uint8_t *yuk, uint16_t n)`: oturum yoksa `KG_YOK`. Önce `ky_bosalt`, sonra `ky__kayit(KAYIT_T_OLAY)`. Dolu ise `ky__dolu`.
  - `int kyn_olay(KayitYonetici *m, const uint8_t *yuk, uint16_t n)`
  - `int kyn_pil_bitir(KayitYonetici *m, const uint8_t *sonuc, uint16_t n, uint8_t sebep)`: etkin oturum `KAYIT_OTURUM_PIL` değilse `KG_YOK`, hiçbir şey yazmaz. Öyleyse `ky_olay(sonuc)` + `ky_bitir(sebep)`.
  - `int kyn_not(KayitYonetici *m, const uint8_t *yuk, uint16_t n)`: `!hazir` → `KG_HATA`. Hedef 0 ya da `>= g->sonraki_sira` → `KG_YOK`. `ky__yer` (etkin oturum varsa TEKRAR) + `kg_ekle(KAYIT_T_NOT, 0, ...)`. Dolu ise `KG_DOLU` döner, etkin oturumu **kapatmaz**.
  - `kyn__devam_dene`: açık oturum `KAYIT_OTURUM_OLCUM` ise bugünkü gibi (DEVAM ya da kapatma niyeti). Değilse `kyn__kapat(..., KB_SEBEP_YENIDEN)`. Yazılamazsa `devam_bekliyor = 1` (durum 4), onay gelince yeniden dener ve kapatır. Asla `ky_devam` çağırmaz.

- [ ] **Step 1: Kırmızı test.** `SENARYO_PIL` aşamaları (her aşama bir açılış, NVS + NOR kalıcı):
  1. ÖLÇÜM başlat, 20 nokta. Sonra PİL `kyn_baslat` + `kyn_olay(AYAR)`, 15 nokta, `kyn_olay(DCIR)`, 10 nokta. Elektrik gider (`ky_bosalt` yok).
  2. Açılış: açık PİL oturumu `BITIR(5)` ile kapanır. `D` satırında durum 1 (boş), oturum 0.
  3. PİL başlat, 12 nokta, `kyn_pil_bitir(SONUC, 4)`. İkinci `kyn_pil_bitir` → `KG_YOK`. ÖLÇÜM başlat, 5 nokta. `kyn_pil_bitir` → `KG_YOK` ve ölçüm açık kalır. `kyn_not` × 4 (ad, ad2, not, not-sil; hedef = aşama 1'in ölçüm oturumu). Geçersiz hedefli `kyn_not` → `KG_YOK`. `kyn_durdur`.
  4. PİL başlat. Halka onaysız dolana kadar nokta. Elektrik gider.
  5. Açılış: yer yok → durum 4, PİL hâlâ açık. `kyn_adim(onay = son)` → kapanır, `BITIR(5)`.

  `bolum_pil` (Python, flaşı `flas_coz` + `oturumlari_kur` ile okur) iddiaları:
  - **B71.P1:** Aşama 1'in ölçüm oturumu `BITIR(6)` ile kapandı; pil oturumu ondan sonra açıldı.
  - **B71.P2:** Pil oturumunun kayıtları sıra ile: BASLA, AYAR olayı, noktalar, DCIR olayı, noktalar. Olayın `kart_ms`'i komşu noktalarınkiyle sıralı. Olaydan önce bekleyen noktalar boşaltılmış.
  - **B71.P3:** Açılışta PİL `BITIR(5)`; o oturumda **hiç DEVAM yok**. Nokta sayısı BITIR'daki `nokta_adedi` ile tutarlı.
  - **B71.P4:** `kyn_pil_bitir`: SONUC olayı BITIR'dan hemen önce; sebep 4. İkinci çağrı `KG_YOK`. Ölçüm sürerken `KG_YOK` ve ölçüm oturumunda SONUC/BITIR yok.
  - **B71.P5:** NOT kayıtları başlıkta oturum 0. Ölçüm oturumu sürerken yazıldılar ve o oturumun sektör kuralını bozmadılar (`tekrar_kurali`). `oturumlari_kur` hedef oturuma ad2, 1 not (silinen yok) verir. Geçersiz hedef yazılmadı.
  - **B71.P6:** Yer yokken açılış → durum 4 (BEKLİYOR). Onaydan sonra PİL `BITIR(5)`; DEVAM yok.
  - **B71.P7:** Aşama 1'deki ölçüm oturumunun noktaları eksiksiz (0..19).
  - **B71.P8:** Mevcut YÖNET iddiaları (ölçüm DEVAM, niyet, biçimleme) yeşil. Ölçüm oturumu hâlâ DEVAM alıyor (regresyon).
  - **B71.P9:** Bütün aşamalarda CRC geçerli, `flas_coz` bozuk kayıt görmüyor.
- [ ] **Step 2:** Kırmızı (işlevler yok).
- [ ] **Step 3:** C eklemeleri.
- [ ] **Step 4:** B71 bütünü yeşil (kesinti dahil tam koşu).
- [ ] **Step 5:** Commit: `1C-1 yonetici: pil oturumu olay/bitir, not kaydi, acilista olcum disi oturum kapanir`

### Task 4: Firmware — mesajlar, pil durum makinesine bağlama, `Ga/Ge/Gn/Gx`

**Files:**
- Modify: `kod/olcum-karti-a3/kayit_esp.h`
  - `KM_PIL_BASLAT 4u`, `KM_OLAY 5u`, `KM_PIL_BITIR 6u`, `KM_NOT 7u`
  - `KayitMesaj { uint8_t tur, sebep; uint16_t n; KayitBasla basla; uint8_t yuk[KAYIT_NOT_BAS + KAYIT_NOT_METIN + 1]; }`
  - `kayit__mesaj` yeni dalları
  - `kayit_mesaj_gonder(const KayitMesaj *m)` (dönüş 1/0, düşeni sayar)
  - `KAYIT_FW_SURUM "A3-1C1"`
- Modify: `kod/olcum-karti-a3/olcum-karti-a3.ino`
  - `kayit_basla_doldur(b, hiz, tur)`
  - `kayit_pil_baslat()` (`pil_baslat` kabul edince), `kayit_pil_dcir()` (DCIR bitiminde), `kayit_pil_bitir(sebep)` (`pil_durdur` içinde, `pil_yuk(false)`'tan SONRA)
  - `kayit_pil_bekleyen` bayrağı + `loop`'ta yeniden deneme
  - `kayit_ornek(o.watt, millis(), pil.dcir_icinde ? KN_DCIR : 0u)`
  - `Gb`/`Gd`: `pil_testi_suruyor()` iken ret
  - `Ga/Ge/Gn/Gx` + yardım satırı
- Modify: `uretim/tasarim3_sabit.py` (DRAM ölçümü; index cerrahisi)
- Test: `uretim/test_kayit_esp.py`: `bolum_kaynak` (B72.F27–F35)

**Interfaces:**
- Consumes: Görev 1–3'ün hepsi. `pil` alanları: `v_bas`, `dcir_v_once`, `dcir_i_once`, `dcir_ani`, `dcir_oturmus`, `dcir_sayisi`, `yuk_pC`, `enerji_pJ`, `v_son`, `durum`, `hata`, `baslama_ms`, `bitis_ms`. `ayar.pil_kesme_v`, `ayar.pil_azami_s`, `ayar.pil_kayit_hz`.
- Produces:
  - Pil kayıt hızı: `hiz_ms = clamp(round(1000 / pil_kayit_hz), 100, 60000)`.
  - `p1` kabulünde kayıt açılamıyorsa (`kayit_bolum` yok, durum `TARIYOR/HATA/DOLU/BEKLIYOR`, ya da kuyruk dolu) `! pil testi KAYDEDILMIYOR — <sebep>` basılır.

- [ ] **Step 1: Kırmızı test** (kaynak iddiaları, yorumsuz kaynakta):
  - **F27:** `pil_baslat`'ın kabul dalında `kayit_pil_baslat()` var; ret dalında yok.
  - **F28:** `pil_durdur` gövdesinde `pil_yuk(false)` **ilk** çağrı; `kayit_pil_bitir(` ondan sonra.
  - **F29:** `pil_isle`'nin DCIR bitimi dalında (`pil.dcir_sayisi++` ile aynı blok) `kayit_pil_dcir()` var.
  - **F30:** `kayit_ornek(` çağrısı `pil.dcir_icinde` ile `KN_DCIR` veriyor.
  - **F31:** `kayit_komut`'ta `alt == 'b'` ve `alt == 'd'` dallarında `pil_testi_suruyor()` reddi. `komut_serbest`'te `p0` hâlâ serbest (mevcut iddianın ikizi).
  - **F32:** `KM_PIL_BITIR` gönderilemezse bekletiliyor. `loop` bekleyeni yeniden gönderiyor (`kayit_pil_bekleyen`), düşürmüyor.
  - **F33:** `kayit__mesaj`'ta `KM_PIL_BITIR` → `kyn_pil_bitir`, `KM_OLAY` → `kyn_olay`, `KM_NOT` → `kyn_not`, `KM_PIL_BASLAT` → `kyn_baslat` + `kyn_olay`.
  - **F34:** `Ga`/`Ge`/`Gn`/`Gx` dalları ve yardım satırı (`Ga<oturum>`). `Gx` `:` içermeyen argümanı reddediyor (`! G:`). Hedef 0 reddediliyor.
  - **F35:** `KAYIT_FW_SURUM "A3-1C1"`.
- [ ] **Step 2:** Kırmızı.
- [ ] **Step 3:** Uygula. `python yukle.py --derle` uyarısız. `Global variables` değerini `tasarim3_sabit._ESP_DRAM_SON_OLCUM`'a index cerrahisiyle yaz.
- [ ] **Step 4:** `python test_kayit_esp.py` yeşil. `node test_arayuz3.js` yeşil (G alt komutları `alt == 'x'` deseniyle; ARAYUZSUZ gerekmez).
- [ ] **Step 5:** Commit: `1C-1 kartta: pil testi kendi oturumunda, DCIR/sonuc olaylari, Ga/Ge/Gn/Gx`

### Task 5: Tezgah — gerçek kart

**Files:**
- Modify: `uretim/tezgah_kayit.py`: `--pil` kipi
- Modify: `uretim/test_kayit_esp.py`: tezgah kalemleri (ADS takılınca tam pil testi)

**Interfaces:**
- Consumes: kart `A3-1C1`, `kayit_bicim.oturumlari_kur` (ad/notlar)

- [ ] **Step 1:** NVS yedeği `Elekronic/.yedek/olcum-karti/nvs-<zaman>.bin` (`tezgah_kayit.flas_oku`), sonra `python yukle.py --port COM6`.
- [ ] **Step 2:** `python tezgah_kayit.py --pil --http <kart-ip>` şunları sınar:
  - `p1` (ADS takılı değil) reddedilir; `G?`'de oturum sayısı değişmez; `KAYDEDILMIYOR` basılmaz, çünkü test hiç başlamadı.
  - `Gb200` → 3 s → `Ga<id> tezgah adı ğ` · `Gn<id> not 1` · `Gn<id>@<ms> not 2` · `Gx<id>:<sira> ` (sil) → `Gd`.
  - Eşitle. `oturumlari_kur` adı "tezgah adı ğ" ve tek not verir.
  - `Gb` sürerken yeniden başlat → ölçüm oturumu DEVAM alır (regresyon).
  - `Gd`.
  - Beklenen: hepsi OK.
- [ ] **Step 3:** Tezgah kalemi: "ADS takılınca gerçek pil testi — `PIL_AYAR` + `DCIR` + `PIL_SONUC`; sonuç `B` raporuyla aynı; test ortasında fiş çekilirse oturum açılışta `BITIR(5)`".
- [ ] **Step 4:** Commit: `1C-1 tezgah: --pil (ret yolu, ad/not gercek kartta, DEVAM regresyonu)`

### Task 6: Mutasyon, sayım kilidi, zincir, belgeler

**Files (index cerrahisi):** `uretim/mutasyon.py`, `uretim/beklenen_sayim.json`, `DEVIR.md` (5.12.68). Normal: `tasarim/2026-09-29-yazilim-sistemi.md` (§5 notu), bu plan (durum satırı).

- [ ] **Step 1:** Her yeni iddia için onu yalanlayan mutasyon (B71: B16–B20, N-yeni, P1–P9; B72: F27–F35). Desenler kaynakta var mı denetlenir, odaklı koşucuyla (ilgili bölümler) çalıştırılır. Beklenen: hepsi YAKALANDI.
- [ ] **Step 2:** `beklenen_sayim.json` B71/B72 yeni sayılar (cerrahi).
- [ ] **Step 3:** `python dogrula3.py` → 21/21. `gizlilik_dogrula.py` temiz.
- [ ] **Step 4:** DEVIR 5.12.68, spec §5 notu, CLAUDE.md, hafıza.
- [ ] **Step 5:** Commit + `git push origin main`.
