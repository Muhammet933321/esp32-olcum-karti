# Alt proje 1C-2 — Ayrıntılı kip (her örnek) Uygulama Planı

> **Durum (2026-10-01): UYGULANDI** (DEVIR 5.12.69). Bağımsız son incelemeden
> sonra altı düzeltme yapıldı; üçü görev metinlerinin ötesine geçiyor: kirli
> silme sayımı ve `KA_SILME`'nin durustan sonraki ilk örneğe taşınması (K8a–K8c),
> PC'de açılış numarası, tezgah ölçümlerinin boşta silmeyi beklemesi.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Gb0` ile ölçüm oturumu her ADS örneğini (~500/s) ham koduyla ve 4 µs çözünürlüklü zamanıyla kaydetsin. Hazır alan (önceden silinmiş sektörler) yeterliyse kayıt boyunca 25 ms'lik silme duraklaması olmasın.

**Architecture:**
- **Biçim:** AYRINTI (9) kaydı, 16 B baş + N×6 B.
- **Örnek halkası:** platformsuz, kilitsiz, tek üretici (çekirdek 1) / tek tüketici (çekirdek 0), `kayit_halka.h`.
- **Yazıcı:** `ky_ayrinti_ornek` / `ky_ayrinti_bosalt`. Nicemlenmiş zaman farkı, sektöre sığmayan kaydı bölme, boşlukta yeni kayıt.
- **Günlük:** `hazir` sayacı ve `kg_on_sil_adim` (onaylı sektörleri başın önünde önceden silme); `kg_ilerle` hazır sektörü silmez.
- **Yönetici:** `kyn_adim` ön silmeyi izin bayrağıyla ve 500 ms arayla yürütür.
- **Firmware:** `Gb0`, `loop`'ta halkaya itme, görevde boşaltma, `GA` durum satırı.

**Tech Stack:** C (AVR emülatörü + ESP32 Arduino 3.3.11), Python 3.14 stdlib.

**Spec:** [tasarim/2026-10-01-1c2-ayrintili-kip.md](2026-10-01-1c2-ayrintili-kip.md) (K1–K11); üstü [2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) §5/§11.

## Global Constraints

- Elle paketleme, küçük uçlu; başlık işlevleri `static inline`; AVR + C++ `-Wall -Wextra` uyarısız (B71.0, B10).
- `kayit_esp.h` `Serial` kullanmaz (B72.F1). Python yalnız stdlib.
- Biçim sürümü 2 kalır (K11). Firmware `A3-1C2`.
- Mevcut hızlar, pil oturumu (1C-1), eşitleme ve `G` satırı değişmez (K10). Emniyet (Ö7) değişmez.
- Kullanıcının commit'lenmemiş dosyaları (`mutasyon.py`, `beklenen_sayim.json`, `tasarim3_sabit.py`, `DEVIR.md`…) yalnız index cerrahisiyle.
- Ters bölü içeren betikler heredoc'la YAZILMAZ; Write aracıyla dosyaya.
- Karta yüklemeden önce NVS yedeği depo dışına; kartta kalibrasyon komutu yok.

## Review Focus

1. **Ön silme yanlış sektöre dokunursa veri kaybolur.** Onaysız sektöre, başın kendisine ve halkanın sarmasına asla dokunmamalı. Bir yazma hatasında ya da biçimlemede `hazir` tutarlı kalmalı (Görev 4).
2. **Bölünen kaydın zamanı kayarsa bir olayın şekli bozulur.** Her örneğin PC'de kurulan zamanı gerçek `micros`'tan en fazla 2 µs sapmalı, bölmelerde ve DEVAM'da birikmemeli (Görev 3).
3. **Halka taşarsa, `micros` sararsa (71.6 dk) ya da skop örneği keserse:** örnek sessizce birleştirilmemeli; yeni kayıt ve bayrak (Görev 2–3).
4. **Ayrıntılı oturum sürerken kart yeniden başlarsa:** oturum DEVAM ile ayrıntılı sürmeli, örnek sırası kesintisiz ilerlemeli (Görev 3).
5. **Ön silme canlı ölçüme ya da skop yakalamasına denk gelirse:** izin bayrağı skop/pil/kayıt varken kapalı olmalı ve yeniden açılınca hemen silmeye koşmamalı (Görev 5).

---

### Task 1: Biçim — AYRINTI kaydı (C + Python)

**Files:** `kod/olcum-karti-a3/kayit_bicim.h`, `kopru/kayit_bicim.py`, `uretim/avr/ornek_kayit.c` (SENARYO_BICIM), `uretim/test_kayit.py` (B71.B22–B23).

**Interfaces (Produces):**
- C:
  - `KAYIT_T_AYRINTI 9u`, `KAYIT_T_AZAMI 9u`
  - `KAYIT_AYRINTI_BAS 16u`, `KAYIT_AYRINTI_ORNEK 6u`, `KAYIT_AYRINTI_DT_AZAMI 4095u`
  - `KA_KAYIP_ONCE 0x01u`, `KA_SILME 0x02u`
  - `KAO_YUKSEK 0x1u`, `KAO_V_HATA 0x2u`, `KAO_I_HATA 0x4u`, `KAO_V_DOYDU 0x8u`
  - `void kayit_ayrinti_bas_paketle(uint8_t *p, uint32_t ilk, uint32_t t0_ms, uint32_t t0_us, uint16_t adet, uint8_t bayrak)`
  - `void kayit_ayrinti_ornek_paketle(uint8_t *p, int16_t v, int16_t i, uint16_t dt4, uint8_t bayrak)`
- Python:
  - `T_AYRINTI = 9`, `KA_KAYIP_ONCE`, `KA_SILME`, `KAO_*`
  - `ayrinti_coz(yuk) -> dict{ilk, t0_ms, t0_us, bayrak, ornekler: [(v, i, dt4, bayrak)]}`, `ayrinti_paketle(d) -> bytes`
  - `Oturum.ayrinti: list[dict]` (kayıt kayıt, `sira` ile)
  - `ayrinti_ornekler(o) -> list[tuple[int, int, int, int, int]]`: `(sira_no, t_us, v, i, bayrak)`, t_us = t0_us + 4·Σdt4 (32 bit sarması düzeltilmiş, oturum başına göre)

- [ ] **Kırmızı:**
  - **B22:** C'nin paketlediği bir AYRINTI (3 örnek, dt4 4095 dahil, bayraklar) Python'la bayt bayt aynı; `ayrinti_coz` geri verir.
  - **B23:** tür 9 ve `AZAMI` 9 C == Python; sürüm 2.
- [ ] **Yeşil:** uygulama; B71 bütünü yeşil.
- [ ] **Commit:** `1C-2 bicim: AYRINTI kaydi (9)`

### Task 2: Örnek halkası — `kayit_halka.h` (platformsuz SPSC)

**Files:** yeni `kod/olcum-karti-a3/kayit_halka.h`; `uretim/avr/ornek_kayit.c` (yeni SENARYO_HALKA); `uretim/test_kayit.py` (`bolum_halka`, B71.H1–H3); `CPP_BASLIKLAR` += `kayit_halka.h`.

**Interfaces (Produces):**
- `typedef struct { uint32_t us, ms; int16_t v, i; uint8_t bayrak; } KayitOrnek;`
  - `bayrak`: `KAO_*` alt 4 bit + `KO_KAYIP_ONCE 0x10u` (yalnız bellekte).
- `typedef struct { KayitOrnek *tampon; uint32_t kapasite; volatile uint32_t yaz, oku, dusen; volatile uint8_t kayip; } KayitHalka;`
  - Kapasite 2'nin kuvveti.
- `void kh_kur(KayitHalka *h, KayitOrnek *t, uint32_t kapasite)`
- `uint8_t kh_it(KayitHalka *h, const KayitOrnek *o)`: doluysa 0; `dusen++`, `kayip = 1`. Sonraki başarılı itmede `KO_KAYIP_ONCE` eklenir.
- `uint8_t kh_al(KayitHalka *h, KayitOrnek *o)`
- `uint32_t kh_adet(const KayitHalka *h)`
- Bellek bariyeri `KAYIT_BARIYER()` (varsayılan `__sync_synchronize()`).

- [ ] **Kırmızı:**
  - **H1:** 8'lik halka: 8 it / 8 al sırayla birebir.
  - **H2:** dolu halkada 3 itme reddedilir, `dusen` 3; bir alıştan sonra itilen örnekte `KO_KAYIP_ONCE` var, ondan sonrakinde yok.
  - **H3:** sayaç sarması (`yaz`, `oku` 0xFFFFFFF0'dan başlatılır) doğru çalışır.
- [ ] **Yeşil; commit:** `1C-2 halka: kilitsiz tek uretici/tek tuketici ornek halkasi`

### Task 3: Yazıcı — `ky_ayrinti_*`, dizin, DEVAM

**Files:** `kayit_oturum.h`, `kayit_gunluk.h` (`kg__dizin_isle` AYRINTI → `nokta_sonraki`), yeni SENARYO_AYRINTI, `test_kayit.py` (`bolum_ayrinti`, B71.A1–A8).

**Interfaces:**
- Consumes: Görev 1–2.
- Produces:
  - `KayitYazici` alanları: `ayrinti`, `a_adet`, `a_ilk_ms`, `a_ilk_us`, `a_q`, `a_bayrak`.
  - `ky_baslat` / `ky_devam` `b->hiz_ms == 0` ise `ayrinti = 1`.
  - `int ky_ayrinti_ornek(KayitYazici *y, const KayitOrnek *o, uint32_t simdi_ms)`: `!oturum || !ayrinti` → `KG_YOK`.
    - `q = (o->us - a_ilk_us + 2) / 4`; `dt4 = q - a_q`.
    - `dt4 > 4095`, tampon dolu ya da `KO_KAYIP_ONCE` ise önce boşaltır; `KO_KAYIP_ONCE` → `a_bayrak |= KA_KAYIP_ONCE`.
  - `int ky_ayrinti_bosalt(KayitYazici *y)`: sığdığı kadar yazar (en az 8 örnek, yoksa yeni sektör). Kalanı başa kaydırır; yeni `t0_us = a_ilk_us + 4·Σdt4`, `t0_ms = a_ilk_ms + (4·Σdt4 + 500)/1000`. İlk kalan `dt4 = 0`.
  - `ky_bitir` / `ky_zaman` AYRINTI tamponunu da boşaltır.
  - Yazma sırasında dolu sektör silindiyse (`g->silinen_sektor` değiştiyse) sonraki kaydın bayrağı `KA_SILME`.
  - `ky_nokta` ayrıntılı oturumda `KG_YOK`.

- [ ] **Kırmızı** (Python, sentetik giriş: gerçek `us` dizisi rastgele ±200 µs oynayan 2000 µs periyot, iki 30 ms'lik boşluk, bir halka kaybı, menzil/hata bayrakları; 3 sektörü aşan uzunluk). Her iddia bağımsız Python referansıyla:
  - **A1:** her örnek sırası, kodu ve bayrağı birebir.
  - **A2:** kurulan zaman gerçek `us`'tan ≤ 2 µs, bölmelerde birikmez.
  - **A3:** 16.38 ms'yi aşan boşluk yeni kayıt açar, `t0` doğru.
  - **A4:** kayıp sonrası kayıt `KA_KAYIP_ONCE`.
  - **A5:** sektör sonu boş kalmaz: sektör başına boşa giden < bir örnek kaydı başı + 8 örnek.
  - **A6:** elektrik kesilip açılınca DEVAM; örnek sırası kesintisiz; BITIR `nokta_adedi` = örnek sayısı.
  - **A7:** ayrıntılı oturumda nokta yazılmaz, noktalı oturumda örnek yazılmaz.
  - **A8:** 5 s boşaltma kuralı örnek tamponunu da kapsar.
- [ ] **Yeşil; commit:** `1C-2 yazici: ayrintili ornek kaydi, bolme, bosluk, DEVAM`

### Task 4: Hazır alan — ön silme

**Files:** `kayit_gunluk.h` (`hazir`, `kg_on_sil_adim`, `kg_ilerle`, sıfırlamalar), `kayit_yonet.h` (`on_sil_izin`, `KYN_HAZIR_HEDEF`, `kyn_adim`), SENARYO_HAZIR, `test_kayit.py` (`bolum_hazir`, B71.Z1–Z6).

**Interfaces (Produces):**
- `KayitGunluk.hazir`
- `int kg_on_sil_adim(KayitGunluk *g)`: 1 silindi · 0 yapılacak yok (sonraki sektör onaysız ya da halka sonu) · `KG_HATA`.
- `KayitYonetici.on_sil_izin` (dışarıdan yazılır), `.on_sil_ms`
- `KYN_HAZIR_HEDEF` (#ifndef; ESP 480, AVR testte küçük)

- [ ] **Kırmızı:**
  - **Z1:** onaylı eski sektörler başın önünde sırayla silinir, `hazir` artar; onaysız sektörde durur ve ona dokunmaz.
  - **Z2:** kafa hazır sektörlere geçerken NOR `silme_adet` ARTMAZ; hazır bitince yeniden artar.
  - **Z3:** izin kapalıyken, oturum sürerken ya da hedefe ulaşınca silme yok; 500 ms aralığa uyulur.
  - **Z4:** açılışta ve mantıksal biçimlemede `hazir` 0.
  - **Z5:** halka neredeyse boşken bile baş sektöre dokunmaz (`hazir + 1 < sektor_adet`).
  - **Z6:** silinen sektörlerin oturumları dizinden doğru düşer (`kg__sektor_dusur`), eşitleme için veri tutarlı.
- [ ] **Yeşil; commit:** `1C-2 hazir alan: onayli sektorler bosta onceden silinir, kafa silmeden gecer`

### Task 5: Firmware

**Files:** `kayit_esp.h` (halka PSRAM 4096, `kayit_ayrinti_it`, görevde boşaltma, `on_sil_izin` volatile, `KayitDurum` hazır/örnek/düşen/silme, `A3-1C2`), `.ino` (`kayit__hiz_gecerli(0)`, `loop`'ta itme, izin bayrağı: kayıt yok + skop yok + pil yok, `GA` satırı `G?`'de, yardım), `tasarim3_sabit.py` (DRAM, cerrahi), `test_kayit_esp.py` (B72.F40–F46).

- [ ] **Kırmızı:**
  - **F40:** `Gb0` kabul edilir, yardımda "0 = her ornek".
  - **F41:** `loop` ayrıntılı oturumda örneği halkaya iter (`kayit_ayrinti_it`), noktacı ile aynı yerde.
  - **F42:** görev halkayı boşaltıp `ky_ayrinti_ornek`'e verir; halka PSRAM'de.
  - **F43:** ön silme izni kayıt/skop/pil koşuluyla; görev izni `on_sil_izin`'e yazar.
  - **F44:** `GA` satırı.
  - **F45:** `A3-1C2`.
  - **F46:** `KayitDurum` yeni alanları çekirdek 0'da doldurulur.
- [ ] **Yeşil:** derleme uyarısız; DRAM cerrahi; B72 + arayüz yeşil.
- [ ] **Commit:** `1C-2 kartta: Gb0 ayrintili kip, ornek halkasi, hazir alan, GA satiri`

### Task 6: Tezgah — gerçek kart

- [ ] NVS yedeği → yükle.
- [ ] `tezgah_kayit.py --ayrinti`:
  - `GA`'da hazır sektör (eşitleme + onaydan sonra boştayken artıyor).
  - `Gb0` 60 s → `Gd` → eşitle.
  - Örnek sayısı / süre ≈ döngü hızı.
  - Zaman farkı dağılımı (ortanca, en büyük) ve boşluk kayıtları.
  - `KA_SILME` sayısı = `GA` silme sayısı; hazır alan varken 0.
  - Ayrıntılı oturum sürerken yeniden başlatma → DEVAM, örnek sırası kesintisiz.
  - Regresyon `--duman --pil`.
- [ ] Tezgah kalemi (ADS takılınca): 500/s, PC W hesabı `D` satırıyla.
- [ ] **Commit:** `1C-2 tezgah: --ayrinti`

### Task 7: Mutasyon, kilit, zincir, belgeler, inceleme, push

- [ ] Her yeni iddiaya yalanlayan mutasyon (cerrahi); desenler var mı denetimi; odaklı + B72 tam koşu.
- [ ] Kilit (cerrahi); zincir 21/21; gizlilik temiz.
- [ ] Bağımsız son inceleme (opus); düzeltme turu.
- [ ] DEVIR 5.12.69 (cerrahi), spec §5 notu, CLAUDE.md, hafıza.
- [ ] Commit + `git push origin main`.
