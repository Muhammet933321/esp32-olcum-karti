# Alt proje 1B — Kalibrasyon geçmişi Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kart her kalibrasyonu numaralı, kalıcı bir geçmiş kaydı olarak tutsun. Her kayıt oturumu hangi kalibrasyonla ölçüldüğünü (numara + tam kopya) taşısın. PC geçmişi eşitlesin.

**Architecture:**
- **Geçmiş yöneticisi `kalgec.h` platformsuz.** NVS'i bir işlev tablosu üzerinden kullanır; AVR emülatöründe emüle NVS blob'larıyla açılıştan açılışa sınanır (B71.C). 1A-2'deki `kayit_yonet.h` ile aynı düzen.
- **Taslak modeli** (kullanıcı kararı, 2026-09-30): kalibrasyon komutları yalnız `Ayar3`'ü değiştirir. Bu değerler geçmişteki son kayıttan farklıysa ortada bir **taslak** vardır.
  - `kk` komutu taslağı not ve türle numaralı kayda çevirir.
  - Unutulursa kayıt başlarken **otomatik** kaydedilir; hiçbir oturum numarasız kalmaz.
  - Not ve tür sonradan düzeltilebilir; değerler değişmez.
- **Saklama NVS'te** (kullanıcı kararı): ad alanı `kalgec`, anahtarlar `adet` + `k1…k40`.
- **Oturum başlığı biçim sürümü 2:** BASLA 98 → 102 bayt, sona `u32 kal_no` eklenir. Okuyucular 98 baytlık sürüm 1'i de kabul eder (numara 0); yükseltmeden önce açılmış oturum sürdürülebilir.

**Tech Stack:** C (AVR emülatörü + ESP32 Arduino 3.3.11 `Preferences`, `nvs_get_stats`), Python 3.14 stdlib.

**Spec:** [tasarim/2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §7 (kalibrasyon), §5 (başlık: "kalibrasyonun tam kopyası + numarası", "mevcut Ayar3 ilk açılışta 1 numaralı kayıt"). Önceki dilim: DEVIR 5.12.66.

## Kapsam

| Dahil | Dahil değil (neden) |
|---|---|
| Biçim v2 (BASLA'da `kal_no`), C + Python, sürüm 1 uyumu | Eski kayda başka kalibrasyon **uygulama** ve "aynı dönemde daha yeni ince ayar öner" → **alt proje 2** (`ortak/`) + 3 (ekran) |
| `kalgec.h` + AVR davranış testleri | B34 ADC doğrusalsızlık düzeltmesi (karar açık, DEVIR 5.12.48) |
| `k` komutu (durum · liste · değer · kaydet · not · tür), `/kal/liste` | Panelde kalibrasyon ekranı → alt proje 3 (`k` arayüzsüz listesine gerekçeyle girer) |
| PC istemcisi `kalibrasyon.json` eşitlemesi | Kalibrasyon **silme** (yok: geçmiş kalıcı; 40 dolarsa açık hata) |

## Bu planın kilitlediği kararlar
- **Kapasite 40 kayıt.** Yedekteki NVS ölçüldü: 179 dolu giriş, yeni veriye ~325 giriş kalıyor. 116 baytlık blob NVS'te 6 giriş tutar; 40 × 6 = 240. Kullanıcıya "64" denmişti; ölçüm 40'ı gösterdi, DEVIR'e yazılır.
  - Dolunca `KGC_DOLU` açık hatası verilir, sessiz silme yok.
  - Kaydetmeden önce `nvs_get_stats` ile boş giriş payı denetlenir (`KGC_NVS_DOLU`). Payın eşiği tezgahta ölçülür (Task 5).
- **Paket 116 B:**
  - 0 u32 no · 4 u32 unix_s · 8 u32 acilis · 12 u8 tür · 13 u8 kaynak · 14 u16 biçim (1)
  - 16 not[32] (UTF-8, NUL'lu; 31 bayt, karakter sınırında kesilir; `"` `\` ve kontrol karakterleri atılır: JSON'a kaçışsız girer)
  - 48 kalibrasyon[62] (BASLA'daki ile aynı paket) · 110 u16 0
  - 112 CRC-32 (zlib, 0..111)
- **Tür:** 0 belirtilmemiş · 1 donanım değişti · 2 ince ayar.
- **Kaynak:** 0 elle (`kk`) · 1 otomatik (kayıt başlarken) · 2 ilk (1B öncesi `Ayar3`).
- **Yazım sırası:** önce `k<no>`, sonra `adet`. Aradan elektrik giderse `adet` eski kalır; yetim blob sonraki kaydetmede üzerine yazılır. Numara oturuma ancak ikisi de yazıldıktan sonra verilir.
- **`k` komutu:**
  - `k` / `k?` → `KG <adet> <son_no> <taslak> <nvs_bos> <azami> <son_hata>`
  - `kl` → her kayıt için `KL <no> <unix> <acilis> <tur> <kaynak> <not>`, sonunda `KL.`
  - `kv<no>` → `KV <no> <n_n> <n_pga> <n_kaz> <n_sif> <n_tau> <y_n> <y_pga> <y_kaz> <y_sif> <y_tau> <i_ofset> <i_pga> <sont> <i_duz> <hz> <faz0> <faz1>`
  - `kk<t><not>` (t: `d` donanım, `i` ince, `-` belirtilmemiş) · `kn<no> <not>` · `kt<no><t>`
- **Web:** `GET /kal/liste` → `{"surum":1,"adet":…,"taslak":0|1,"azami":40,"kayitlar":[{"no","unix","acilis","tur","kaynak","not","kal":{…}}]}`. Kendi salt-okunur `Preferences` örneğini açar.

## Global Constraints
- Motor, `kalgec.h` ve `kayit_bicim.h` platformsuz; C11/C++11'de uyarısız, AVR testleri (`test_kayit.py`) yeşil.
- Firmware `--warnings all` UYARISIZ; statik RAM < %25. `_ESP_DRAM_SON_OLCUM` ölçülen değere eşit; index cerrahisiyle güncellenir.
- `kayit_esp.h`'de `Serial` yok. Basma yalnız `.ino`'da, çekirdek 1'de.
- Python yalnız stdlib. Depoya sır, mutlak yol ya da IP girmez (`gizlilik_dogrula` temiz).
- Kullanıcının commit'lenmemiş işi olan dosyalar (`dogrula3.py`, `mutasyon.py`, `beklenen_sayim.json`, `DEVIR.md`, `tasarim3_sabit.py`) YALNIZ index cerrahisiyle (`scratchpad/cerrahi.py`) güncellenir.
- ⚠ **Tezgahta kalibrasyon komutu (`z g Z i s f F R`) ÇALIŞTIRILMAZ:** ADS'ler takılı değil. Ölçülen çöp kullanıcının gerçek kalibrasyonunun yerine yazılırdı. Kartta yalnız `k` komutları, not/tür düzenleme ve kısa bir kayıt denenir. Taslak/kaydet yolu AVR'de sınanır.
- Karta yüklemeden önce NVS yedeği (0x9000, 0x5000) depo dışına alınır.
- Her yeni iddianın onu yalanlayan bir mutasyonu olur.

## Review Focus
1. **Kaydetme sırasında elektrik kesilmesi:** `k<no>` yazıldı, `adet` yazılmadı. Numara tekrar verilmemeli ya da kaybolmamalı; hiçbir oturum yazılmamış bir kayda işaret etmemeli. → Task 2 C7
2. **NVS dolu ya da 40 dolu:** açık hata; oturum yine tam kopyayla kaydedilir (`kal_no` 0). → Task 2 C8/C9
3. **1A-2 ile açılmış eski oturum** (sürüm 1, 98 B) yeni firmware'de hâlâ çözülmeli ve sürdürülebilmeli. → Task 1 B14/B15
4. **Türkçe not:** 31 baytta çok baytlı karakter bölünmemeli; `"` ve `\` JSON'u bozmamalı. → Task 2 C10, Task 4 E19
5. **`/kal/liste` çekirdek 1 kaydederken okunursa** tutarlı olmalı (önce `adet`, sonra bloblar). → Task 3 F19 (kaynak sırası), tezgah

---

### Task 1: Biçim v2 — oturum başlığında kalibrasyon numarası

**Files:**
- Modify: `kod/olcum-karti-a3/kayit_bicim.h`, `kod/olcum-karti-a3/kayit_gunluk.h` (`kg_basla_oku`)
- Modify: `kopru/kayit_bicim.py`
- Modify: `uretim/avr/ornek_kayit.c` (SENARYO_SURUM), `uretim/test_kayit.py` (B3/B12 güncelle, B14/B15)

**Interfaces:**
- Produces:
  - C: `KAYIT_SURUM 2u` · `KAYIT_BASLA_BAYT 102u` · `KAYIT_BASLA_V1_BAYT 98u` · `KAYIT_KAL_BAYT 62u`
  - C: `KayitBasla.kal_no` (u32) · `kayit_kal_paketle(const KayitKalibrasyon*, uint8_t*)` · `kayit_kal_coz(const uint8_t*, KayitKalibrasyon*)`
  - C: `kayit_basla_coz(const uint8_t *p, uint16_t n, KayitBasla *b)` (n = 98 ya da 102)
  - Python: `Basla.kal_no` (varsayılan 0) · `kal_paketle(Kalibrasyon)->bytes` · `kal_coz(bytes)->Kalibrasyon` · `BASLA_BAYT = 102`, `BASLA_V1_BAYT = 98`

- [ ] **Step 1: Testleri yaz.** `bolum_bicim`'de B3'ün beklentisini 102'ye, B12'yi sürüm 2'ye çek. `ornek_kayit.c`'ye SENARYO_SURUM ekle:
  - v2 BASLA'yı paketle; `kal_no` = 7.
  - Aynı paketi 98 bayta kesip bayt 2–3'ü 1 yaparak v1 üret.
  - İkisini `kg_ekle` ile flaşa yaz; `kg_basla_oku` ile oku.
  - `BV <surum> <kal_no> <hiz>` bas.
  - Python iddiaları:
    - **B14:** C ve Python v1'i çözer, `kal_no` 0, kalibrasyon aynı.
    - **B15:** v1 BASLA'lı açık oturum `kg_basla_oku` ile okunur (yükseltmeden sonra DEVAM edebilsin).
- [ ] **Step 2: Kırmızı:** B3, B12 ve SURUM derlemesi kırmızı.
- [ ] **Step 3: Uygula.**
  - C: kalibrasyon paketlemesini `kayit_kal_paketle`/`coz`'a ayır (36..97); `kayit_basla_paketle` 98..101'e `kal_no` yazar.
  - C: `kayit_basla_coz(p, n, b)`: `n >= 102` ise `kal_no` okunur, değilse 0.
  - C: `kg_basla_oku` `yuk_bayt` 98 ya da 102 kabul eder, ikisini de 102'lik tampona okur.
  - Python: `basla_coz` uzunluğa bakar.
  - Çağıranları güncelle: `kayit_oturum.h` TEKRAR/BASLA, `ornek_kayit.c` BICIM senaryosu.
- [ ] **Step 4: Yeşil:** `python test_kayit.py` → B71 hepsi yeşil (iddia sayısı +B14 +B15 + derleme/BITTI).
- [ ] **Step 5: Commit** `1B bicim v2: BASLA'da kalibrasyon numarasi, surum 1 okunur`.

### Task 2: `kalgec.h` + AVR davranış testleri

**Files:**
- Create: `kod/olcum-karti-a3/kalgec.h`
- Modify: `uretim/avr/nor_flas.py` (ada göre NVS blob: 0xED ad portu, 0xEE veri portu, 0xEF boş giriş; komut 3 oku, 4 yaz)
- Modify: `uretim/avr/ornek_kayit.c` (SENARYO_KALGEC), `uretim/test_kayit.py` (`bolum_kalgec`, B71.C1–C10), `kopru/kayit_bicim.py` (`kalgec_coz`)

**Interfaces:**
- Produces:
  - Tipler/sabitler: `KalKayit`, `KalNvs{oku, yaz, bos, baglam}`, `KalGecmis{nvs, adet, son_var, son, son_hata}`, `KALGEC_AZAMI 40`, `KALGEC_NOT 32`, `KALGEC_BAYT 116`, `KGT_*`, `KGK_*`, `KGC_*`
  - `kgc_ac(m, nvs, simdiki, unix, acilis)`, `kgc_taslak(m, simdiki)`, `kgc_kaydet(m, simdiki, tur, not, unix, acilis)`, `kgc_oturum_no(m, simdiki, unix, acilis)`
  - `kgc_oku(m, no, KalKayit*)`, `kgc_duzenle(m, no, tur|-1, not|NULL)`, `kgc_paketle`/`kgc_coz`, `kgc_not_kopyala`

- [ ] **Step 1: Testleri yaz.** SENARYO_KALGEC aşamalı (`t_adim` NVS'ten; her açılış bir aşama, NVS kalıcı):
  - **C1:** ilk açılış → #1 (kaynak ilk), taslak yok.
  - **C2:** bir alan değişti → taslak; `kgc_kaydet(donanım, "şönt 5 mΩ")` → #2; taslak yok.
  - **C3:** taslak yokken `kgc_oturum_no` → 2 (yeni kayıt yok).
  - **C4:** değişiklik + `kgc_oturum_no` → #3 otomatik.
  - **C5:** yeniden açılış → adet 3, son = #3 (değerler aynı).
  - **C6:** #2'nin notu/türü düzeltilir, açılıştan sonra kalıcı.
  - **C7:** `adet` yazımı başarısız → kaydet hata; açılış → adet 3; sonraki kaydet #4 (yetim üzerine).
  - **C8:** 40'a kadar doldur → `KGC_DOLU`; doluyken `kgc_oturum_no` taslakla → 0 + hata.
  - **C9:** NVS boş < pay → `KGC_NVS_DOLU`.
  - **C10:** 40 baytlık Türkçe not 31 baytta karakter sınırında kesilir; `"` ve `\` atılır.
  - Python `kalgec_coz` C'nin blobunu bayt bayt çözer (CRC dahil).
- [ ] **Step 2: Kırmızı** (başlık yok).
- [ ] **Step 3: `kalgec.h` + emülatör NVS blob'ları.**
- [ ] **Step 4: Yeşil** `python test_kayit.py`.
- [ ] **Step 5: Commit** `1B kalgec.h: kalibrasyon gecmisi (taslak, kaydet, otomatik, 40 sinir)`.

### Task 3: Kartta yapıştırıcı, `k` komutu, `/kal/liste`, başlıkta numara

**Files:**
- Modify: `kod/olcum-karti-a3/kayit_esp.h` (Preferences `kalgec` tablosu, `nvs_get_stats`, `kalgec_kur`)
- Modify: `kod/olcum-karti-a3/olcum-karti-a3.ino`:
  - `setup` → `kalgec_kur` (`ayar_yukle`'den sonra)
  - `kayit_kal_doldur` (`kayit_basla_doldur`'dan ayrılır) + `kal_no`
  - `kalgec_komut` + `case 'k'` + yardım
  - `/kal/liste`
- Modify: `uretim/test_kayit_esp.py` (F17–F20), `uretim/test_arayuz3.js` (`k` arayüzsüz, gerekçeli)

- [ ] **Step 1: F-testleri yaz:**
  - **F17:** `setup` `kalgec_kur`'u `ayar_yukle`'den sonra çağırıyor.
  - **F18:** `kayit_basla_doldur` `kal_no`'yu `kgc_oturum_no` ile alıyor.
  - **F19:** `/kal/liste` Host denetimli ve önce `adet`'i okuyor.
  - **F20:** NVS boşu `nvs_get_stats`'tan.
  - B7: `k` gerekçeli.
- [ ] **Step 2: Kırmızı.**
- [ ] **Step 3: Uygula;** `test_firmware3.py` uyarısız, DRAM sabiti.
- [ ] **Step 4: Yeşil** (`test_kayit_esp.py`, `node test_arayuz3.js`, `test_firmware3.py`).
- [ ] **Step 5: Commit** `1B kartta: k komutu, /kal/liste, oturumda kalibrasyon numarasi`.

### Task 4: PC — `kalibrasyon.json`

**Files:** Modify `kopru/kayit_esitle.py`, `uretim/test_kayit_esp.py` (E18, E19)

- [ ] **Step 1:** Sahte karta `/kal/liste` ekle.
  - **E18:** eşitleme `kalibrasyon.json`'u atomik yazar ve karttakiyle aynı olur.
  - **E19:** Türkçe notlu liste bozulmadan gelir; eski firmware (404) eşitlemeyi durdurmaz.
- [ ] **Step 2: Kırmızı.**
- [ ] **Step 3:** `Esitleyici._kal_esitle()` → `esitle()` sonunda.
- [ ] **Step 4: Yeşil.**
- [ ] **Step 5: Commit** `1B PC: kalibrasyon gecmisi esitlenir`.

### Task 5: Zincir, mutasyon, kart, belgeler

- [ ] Mutasyonlar (her yeni iddia için) + kilit (index cerrahisi); `mutasyon.py --adim B71/B72`.
- [ ] NVS yedeği (depo dışı) → yükle → tezgah:
  - `k?`: #1 var, taslak 0; `nvs_bos` ve toplam ölçülür → `KALGEC_NVS_PAY` bu ölçüme göre sabitlenir.
  - `kv1` == `?`'nin A satırı (n/y kazanç, sıfır, şönt, i_duz, i_ofset).
  - `kn1` not + `kt1` tür → yeniden açılışta kalıcı.
  - `Gb200`/`Gd` → eşitlenen BASLA `bicim_surum` 2, `kal_no` 1.
  - `/kal/liste` == `kl`.
- [ ] Zincir 21/21, gizlilik temiz. DEVIR 5.12.67, CLAUDE.md, hafıza. Son bağımsız inceleme → düzeltme → push.
