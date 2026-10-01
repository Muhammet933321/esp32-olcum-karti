# Alt proje 1D — Eşleştirme + imzalı istekler Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Durum:** TASLAK, yerel `1d-eslestirme` dalında. Kullanıcı onaylayana dek `main`'e
> girmez, push edilmez (kullanıcı 2026-10-01: "kritik bir şey varsa hemen commit atma").

**Goal:** Kart, şu iki yoldan eşleşen cihazların imzalı isteklerini kabul etsin:
- parolayla eşleştirme (parola ağa çıkmaz);
- USB'den eşleştirme.

Zorunluluk anahtarı kapalıyken bugünkü bütün yollar aynen çalışsın.

**Architecture:**
- **Mantık:** platformsuz `guvenlik.h` — cihaz tablosu, eşleştirme, deneme sınırı, kanonik metin, kayan pencere. Kriptografi işlev tablosundan gelir (`GuvKripto`), NVS blob tablosundan (`GuvNvs`).
  - Kartta: mbedTLS (donanım SHA) + Preferences.
  - AVR testinde: sınama SHA-256'sı + emüle NVS.
- **Web:** ESP32 yapıştırıcısı `guvenlik_esp.h`, her ucu tek bir kapıdan (`guv_kapi`) geçirir.
- **PC istemcisi:** `kopru/imza.py`, yalnız stdlib.
- **Ortak doğruluk:** C ve Python `uretim/vektor_guvenlik.json` vektörlerinde birebir aynı sonucu verir.

**Tech Stack:** C (platformsuz başlık, AVR emülatörü), ESP32-S3 Arduino çekirdeği 3.3.11 (mbedTLS md/HMAC, pkcs5/PBKDF2), Python 3.14 stdlib (hashlib, hmac, secrets, ctypes/DPAPI).

**Spec:** `tasarim/2026-10-01-1d-eslestirme.md` (K1–K17, "⚠ Onay bekleyen kritik kararlar").

## Global Constraints

- Platformsuz başlıklar avr-gcc `-Wall -Wextra` ile **UYARISIZ** derlenir ve B10 C++ denetimine girer.
- Python yalnız standart kütüphane.
- Depo herkese açık. Parola hiçbir çıktıya yazılmaz.
- `K` yalnız `Ep` yanıtında ve yalnız ham UART'tan basılır (`Serial` aynası SSE'ye taşır).
- `kopru.py` `EK ` satırını hiçbir istemciye iletmez ve `E…` komutlarını reddeder.
- Firmware `/komut` ucu `E…` komutlarını reddeder (yalnız USB).
- Kullanıcının commit'lenmemiş dosyaları (`mutasyon.py`, `beklenen_sayim.json`, `dogrula3.py`, `tasarim3_sabit.py`, `DEVIR.md`, `_tezgah.md`) yalnız indeks cerrahisiyle (`cerrahi.py`) değişir.
- `N?` çalıştırılmaz. `web_sifre` okunmaz, değiştirilmez. Kalibrasyon komutları çalıştırılmaz.
- Her yüklemeden önce NVS yedeği (depo dışı). Tezgah sonunda kart `main`'in firmware'ine (`A3-1C4`) geri yüklenir, test cihazları silinir, zorunlu 0.
- Bütün commit'ler `1d-eslestirme` dalında. Push YOK, `main`'e birleştirme YOK.
- Sürüm `A3-1D`.

## Review Focus

1. Sorgu değerinde `&` ya da `=` var (çözülmüş değer). Kanonik metin belirsiz olmamalı: değerler yüzde kodlanır; `a=1&b=2` ile `a="1&b=2"` farklı imza verir → T1 vektörü + T2 C testi.
2. Kart yeniden başladı, PC eski `acilis` ile imzalıyor. Kart 401 + `X-Acilis` döner; istemci **bir kez** eşitlenip yeniden dener, döngüye girmez → T4 testi.
3. İki eşzamanlı imzalı istek sırasız gelir (önce `s+1`, sonra `s`). İkisi de pencere içinde kabul; aynısı ikinci kez ret → T2 testi.
4. Cihaz silinir (`Ex<n>`) ve sonra aynı numara yeniden eşleşir. Eski `K` ile imza reddedilmeli (yeni `K` farklıdır) → T2 testi.
5. Zorunlu 0'da bütün bugünkü imzasız yollar aynen durur. Ama bozuk imza başlığı taşıyan istek "imzasız" sayılıp geçirilmez, 401 alır → T3 testi + tezgah.

---

### Task 1: Test vektörleri + Python başvuru çekirdeği

**Files:**
- Create: `kopru/imza.py`. Bu görevde yalnız saf işlevler; G/Ç T4'te eklenir.
- Create: `uretim/vektor_guvenlik.json`, üreten betik `uretim/vektor_guvenlik.py`. Vektörler kodda sabit; JSON çıktısı yazılır ve test onu karşılaştırır.
- Test: `uretim/test_kayit_esp.py`, yeni bölüm `bolum_guvenlik_py()` (B72.G…). Neden B72: Python + kaynak iddiaları orada.

**Interfaces (Produces):**
- `imza.yuzde_kodla(s: str) -> str`: UTF-8 baytları; `A–Z a–z 0–9 - . _ ~` aynen, gerisi büyük harf `%XX`.
- `imza.pbkdf2(parola: str, tuz: bytes, tur: int) -> bytes`: 32 B.
- `imza.kanit_istemci(P: bytes, kimlik: str, nk: bytes, nc: bytes, ad: str) -> bytes`. Girdi: `"OK1-istemci\n" + kimlik + "\n" + nk.hex() + "\n" + nc.hex() + "\n" + ad`.
- `imza.kanit_kart(P, kimlik, nk, nc, n: int) -> bytes`. Girdi: `"OK1-kart\n…\n" + str(n)`.
- `imza.cihaz_anahtari(P, kimlik, nk, nc, n: int) -> bytes`. Girdi: `"OK1-anahtar\n…\n" + str(n)`.
- `imza.kanonik(yontem: str, yol: str, argumanlar: list[tuple[str, str]], acilis: str, sayac: int, govde: bytes) -> bytes`. Biçim:
  - `"OK1\n" + yontem + "\n" + yol`;
  - argüman varsa `"?" + "&".join(yuzde_kodla(a) + "=" + yuzde_kodla(d))`;
  - sonra `"\n" + acilis + "\n" + str(sayac) + "\n" + sha256(govde).hexdigest()`.
- `imza.imzala(K: bytes, …aynı…) -> str` (hex).
- `imza.ad_gecerli(ad: str) -> bool`: 1–24 bayt UTF-8, kontrol karakteri yok.

- [ ] **Step 1:** RFC vektörlerini kopyala:
  - RFC 4231 HMAC-SHA256 test durumları 1, 2, 3, 4, 6, 7;
  - RFC 7914 §11 PBKDF2-HMAC-SHA256: `passwd`/`salt`/c=1/dkLen=64 ve `Password`/`NaCl`/c=80000/dkLen=64.
- [ ] **Step 2:** Bölümü yaz:
  - G1 HMAC vektörleri; G2 PBKDF2 (`hashlib.pbkdf2_hmac` ile ve `imza.pbkdf2`'nin 32 B ön eki).
  - G3 yüzde kodlama: `a&b=c` → `a%26b%3Dc`; `ğ` → `%C4%9F`; boşluk → `%20`.
  - G4 kanonik belirsizlik: `[("a","1&b=2")]` ile `[("a","1"),("b","2")]` farklı kanonik.
  - G5 protokol örnekleri, JSON'daki beklenenle aynı: sabit `P`, kimlik, `nk`, `nc`, ad `"PC ğ"`, `n=3`.
  - G6 imza örnekleri: GET sorgusuz, GET sorgulu, POST gövdeli, EventSource `_c _s _i` argümanları **hariç** (kanoniğe girmez).
  - G7 `ad_gecerli`: 25 bayt ret, `"\n"` ret, `"Telefon ğ"` kabul.
- [ ] **Step 3:** `python test_kayit_esp.py` → G testleri KIRMIZI (modül yok).
- [ ] **Step 4:** `imza.py`'yi ve `vektor_guvenlik.py`'yi yaz, JSON'u üret.
- [ ] **Step 5:** YEŞİL; bütün B72 yeşil. Sayım kilidi (`kilit_yaz.py B72 eski yeni`).
- [ ] **Step 6:** Mutasyonlar (`c3_mut_ekle.py`):
  - yüzde kodlamada `~` kodlanıyor;
  - kanonikte gövde özeti yerine gövde;
  - kanit etiketinde "OK1-kart";
  - `ad` uzunluk sınırı 24 → 25.
  Commit.

### Task 2: Platformsuz çekirdek `guvenlik.h` + AVR `SENARYO_GUV`

**Files:**
- Create: `kod/olcum-karti-a3/guvenlik.h`.
- Create: `uretim/avr/sha256_sinama.h`. Yalnız test: FIPS 180-4 SHA-256 ve RFC 2104 HMAC, artımlı; PBKDF2 bunun üstünde.
- Modify: `uretim/avr/ornek_kayit.c` (yeni `SENARYO_GUV`, giriş `#if` listesi), `uretim/test_kayit.py` (yeni `bolum_guvenlik()`).

**Interfaces (Produces, `guvenlik.h`):**
- Tablolar:
  - `typedef struct { void (*hmac_bas)(void *ctx, const uint8_t *anahtar, uint16_t n); void (*hmac_ekle)(void *ctx, const void *v, uint16_t n); void (*hmac_bit)(void *ctx, uint8_t c[32]); void (*sha_bas)(void *ctx); void (*sha_ekle)(void *ctx, const void *v, uint16_t n); void (*sha_bit)(void *ctx, uint8_t c[32]); int (*pbkdf2)(const char *parola, const uint8_t *tuz, uint16_t tn, uint32_t tur, uint8_t c[32]); void (*rastgele)(uint8_t *h, uint16_t n); } GuvKripto;`
  - `GUV_CTX_BOYU 224`: çağıranın verdiği bağlam belleği; yapıştırıcı `_Static_assert` ile sığdığını gösterir.
  - `typedef struct { int (*oku)(void *b, const char *ad, void *h, uint16_t n); int (*yaz)(void *b, const char *ad, const void *k, uint16_t n); void *baglam; } GuvNvs;` (0 = tamam).
- Sabitler:
  - `GUV_CIHAZ_AZAMI 8`, `GUV_AD_AZAMI 24`, `GUV_PAROLA_EN_AZ 10`, `GUV_ESLES_SURE_MS 60000`, `GUV_PENCERE 64`, `GUV_TUR_VARSAYILAN 50000`.
  - Hata kodları: `GUV_E_YOK -1`, `GUV_E_IMZA -2`, `GUV_E_TEKRAR -3`, `GUV_E_CIHAZ -4`, `GUV_E_BEKLE -5`, `GUV_E_DOLU -6`, `GUV_E_PAROLA -7`, `GUV_E_KANIT -8`, `GUV_E_AD -9`, `GUV_E_NVS -10`.
- NVS düzeni:
  - `ayar` blob = `GuvAyar { uint8_t surum, zorunlu, misafir, _; uint32_t tur; uint8_t tuz[16]; uint8_t kimlik[8]; }`;
  - cihaz `c1…c8` blob = `GuvCihaz { uint8_t var; char ad[25]; uint8_t K[32]; uint32_t eklenme, son; }`.
- Durum: `typedef struct GuvDurum { … }`. RAM'de yalnız şunlar durur:
  - cihaz başına `var`, `son_sayac` (u64), `pencere` (u64 bit), `son_yazim_unix`;
  - bekleyen eşleştirme (`eno`, `nk[16]`, `nc[16]`, ad, başlangıç ms);
  - deneme sınırı (`k`, `serbest_ms`); `acilis[16]`; `P` önbelleği (`p_var`, `P[32]`); ayar.
  - `K` RAM'de **tutulmaz**; doğrulamada NVS'ten okunur.
- İşlevler:
  - `int guv_ac(GuvDurum*, const GuvKripto*, const GuvNvs*)`: ayar yoksa üretir (tuz, kimlik rastgele, tur varsayılan); `acilis` yeni rastgele.
  - `void guv_parola_degisti(GuvDurum*)`: `P` önbelleğini siler.
  - `int guv_esles_baslat(GuvDurum*, const char *ad, const uint8_t nc[16], const char *parola, uint32_t simdi_ms, uint8_t *eno, uint8_t nk[16])`.
  - `int guv_esles_kanit(GuvDurum*, uint8_t eno, const uint8_t kanit[32], const char *parola, uint32_t simdi_ms, uint32_t unix, uint8_t *n, uint8_t kart_kanit[32])`. Hata dönerse `serbest_ms = simdi + 2^k s`, `k++` (k ≤ 8); başarıda k = 0. Kanıt karşılaştırması sabit zamanlı.
  - `int guv_esles_usb(GuvDurum*, const char *ad, uint32_t unix, uint8_t *n, uint8_t K[32])`.
  - `int guv_cihaz_sil(GuvDurum*, uint8_t n)` (n = 0: hepsi); `int guv_cihaz_oku(const GuvDurum*, uint8_t n, GuvCihaz *c)`.
  - İmza doğrulama:
    - `typedef struct { … uint8_t ctx[GUV_CTX_BOYU]; uint8_t ilk_arg; … } GuvImza;`
    - `int guv_imza_bas(GuvDurum*, GuvImza*, uint8_t n, const char *yontem, const char *yol)`: cihaz yoksa `GUV_E_CIHAZ`.
    - `void guv_imza_arg(GuvDurum*, GuvImza*, const char *ad, const char *deger)`: yüzde kodlar.
    - `int guv_imza_bit(GuvDurum*, GuvImza*, uint64_t sayac, const uint8_t govde_ozet[32], const char *imza_hex, uint32_t unix)`. Önce HMAC sabit zamanlı karşılaştırılır, **sonra** pencere denetlenir. "Son görülme" saatte en fazla bir kez NVS'e yazılır.
  - `int guv_ayar_yaz(GuvDurum*, int zorunlu /*-1 = değiştirme*/, int misafir, uint32_t tur /*0 = değiştirme*/)`.
  - `void guv_acilis_hex(const GuvDurum*, char h[33])`, `void guv_kimlik_hex(const GuvDurum*, char h[17])`.

- [ ] **Step 1:** `test_kayit.py`'de `bolum_guvenlik()` (B71.U…) ve `ornek_kayit.c`'de `SENARYO_GUV`. Açılışlar, `t_adim` ile:
  - **Açılış 1 — vektörler:**
    - U1 HMAC RFC 4231 durum 1 ve 2;
    - U2 PBKDF2 RFC 7914 c=1 (ilk 32 B);
    - U3 kanıt, `K`, kart kanıtı, `P`'si JSON'daki örnekle aynı (`P` doğrudan verilir: test `guv__p_yukle` kancası, yalnız `GUV_SINAMA`);
    - U4 kanonik / imza: JSON'daki G6 örnekleri C'de aynı imzayı doğrular, yüzde kodlu sorgu dahil.
  - **Açılış 1 — akış:**
    - U5 parola 9 karakter → `GUV_E_PAROLA`; boş → `GUV_E_PAROLA`.
    - U6 başarılı eşleştirme (tur 2, AVR hızı için; ayar tur'u yazılır):
      - `n = 1`;
      - kart kanıtı Python'un beklediğiyle aynı;
      - `K` NVS'te.
    - U7 yanlış kanıt → `GUV_E_KANIT`; hemen yeni `baslat` → `GUV_E_BEKLE`; 1 s sonra serbest, ikinci yanlış → 2 s.
    - U8 60 s'den eski bekleyen → `GUV_E_YOK`.
    - U9 imza:
      - doğru → 0;
      - aynı sayaç → `GUV_E_TEKRAR`;
      - `s + 2`'den sonra `s + 1` → 0 (sırasız);
      - `s − 64` → `GUV_E_TEKRAR`.
    - U10 tek bayt değiştirince ret (`GUV_E_IMZA`): yöntem, yol, argüman değeri, gövde özeti, `acilis`. Review Focus 1: `a=1&b=2` ile imzalanmış istek `a="1&b=2"` olarak sunulunca da ret.
    - U11 USB eşleştirme → `n = 2`; 8'e kadar doldur; 9. → `GUV_E_DOLU`.
  - **Açılış 2:**
    - U12 cihaz tablosu kalıcı;
    - `acilis` açılış 1'dekinden farklı;
    - açılış 1'in imzası (eski `acilis`) → `GUV_E_IMZA`;
    - yeni `acilis` ile sayaç 1 → kabul (pencere yeni açılışta sıfırdan).
  - **Açılış 2, devam:**
    - U13 `guv_cihaz_sil(1)` → n = 1 ile imza `GUV_E_CIHAZ`;
    - yeniden eşleştirme n = 1'i alır;
    - eski `K` ile imza `GUV_E_IMZA` (Review Focus 4).
  - **Açılış 3:** U14 zorunlu / misafir / tur ayarları kalıcı; tuz ve kimlik açılışlar arasında aynı.
- [ ] **Step 2:** Koş → derleme hatası (başlık yok) = KIRMIZI.
- [ ] **Step 3:** `guvenlik.h` ve `sha256_sinama.h`'yi yaz. `nor_flas.py`'nin blob adlarına `ayar`, `c1`–`c8` girer (ada göre blob zaten var; gerekirse liste).
- [ ] **Step 4:** YEŞİL; bütün B71 yeşil. Sayım kilidi B71.
- [ ] **Step 5:** Mutasyonlar:
  - pencere denetimi kaldırıldı (U9);
  - HMAC karşılaştırması ilk baytta çıkış — sabit zamanlılık davranışla sınanamaz, U9 kırmızı olmaz → **kaynak iddiası** B72'de;
  - `k++` yok (U7);
  - süre 60 → 600 s (U8);
  - `acilis` kanoniğe girmiyor (U12);
  - silmede `var = 0` yazılmıyor (U13);
  - yüzde kodlama kaldırıldı (U10);
  - parola en az 10 → 9 (U5);
  - doğrulama sırası ters, pencere HMAC'tan önce: sahte sayaçla pencere ilerletilebilir. Test: sahte imzalı büyük sayaçtan sonra doğru `s` hâlâ kabul (U9b).
  Commit.

### Task 3: Kart yapıştırıcısı + uçlar + seri `E` komutları

**Files:**
- Create: `kod/olcum-karti-a3/guvenlik_esp.h`:
  - mbedTLS `GuvKripto`: `mbedtls_md_*` ile HMAC/SHA, `mbedtls_pkcs5_pbkdf2_hmac_ext`, `esp_fill_random`;
  - Preferences `GuvNvs` (ad alanı `guv`: `ayar`; ad alanı `cihaz`: `c1…c8`);
  - FreeRTOS muteks (web çekirdek 0, seri çekirdek 1);
  - `bool guv_kapi(uint8_t sinif)`;
  - uç işleyicileri.
- Modify: `kod/olcum-karti-a3/web_akis.h`: `void ham(const char *s)` yalnız `_s`'ye yazar.
- Modify: `kod/olcum-karti-a3/olcum-karti-a3.ino`:
  - uç kayıtları;
  - her işleyicinin başında `guv_kapi`;
  - `komut_sayfa` imzalı yol + `E` reddi;
  - seri `E` komutları;
  - açılış afişi;
  - `N?` satırına zorunlu / misafir / saat kaynağı (yalnız ekleme, mevcut alanlar değişmez).
- Modify: `kod/olcum-karti-a3/kayit_esp.h`: `KAYIT_FW_SURUM "A3-1D"`.
- Modify: `kopru/kopru.py`: `E` komutu reddi, `EK ` satırını yayınlamama. Test `uretim/test_kopru.py`.
- Test: `uretim/test_kayit_esp.py`, B72.F74…

**Interfaces:**
- Consumes: `guvenlik.h` (T2).
- Produces:
  - Uç sınıfları: `GUV_ACIK 0` (`/`, `/eslestir/*`), `GUV_IZLEME 1` (`/akis`, `/pil`), `GUV_OKUMA 2` (`/kayit/*`, `/kal/liste`, `/skop.bin`), `GUV_KOMUT 3` (`/komut`, `/kopru`), `GUV_CIHAZ 4` (`/cihaz/*`, `/saat`). Global `guv_imzali` (son istek imzalı ve geçerli mi; çekirdek 0).
  - Uçlar: `GET /eslestir/bilgi` (JSON: kimlik, acilis, tuz, tur, zorunlu, misafir, saat), `POST /eslestir/baslat`, `POST /eslestir/kanit`, `GET /cihaz/liste`, `POST /cihaz/sil`, `POST /saat`.
  - Seri komutlar: `E?`, `Ex<n>`, `Ex!`, `Ep<ad>` (yanıt `EK <n> <64 hex>` yalnız `CIKIS.ham`), `Ez0|1`, `Em0|1`, `Et<tur>` (PBKDF2 süre ölçümü sabit sahte parolayla; `ET <tur> <ms>`; ayara yazmaz), `Er<tur>` (varsayılan turu ayara yazar).

- [ ] **Step 1:** B72 iddialarını yaz:
  - F74: her `sunucu.on` işleyicisinin gövdesi `guv_kapi(` ile başlar; sınıflar tabloyla eşleşir.
  - F75: `komut_sayfa`'da `guv_imzali` dalı jeton + Basic aramaz; imzasız dal bugünkü metinle aynı (regresyon).
  - F76: `/komut`, `E` ile başlayan komutu 403 ile reddeder (`komut_kuyruga`'dan önce).
  - F77: `EK ` yalnız `ham(` ile basılır. Kaynakta `Serial.print` / `printf` ile `EK` yok; `K` hex'i `Serial`'a giden hiçbir çağrıda yok.
  - F78: imza başlıkları varken doğrulama başarısızsa 401 + `X-Acilis`, zorunlu 0'da da (Review Focus 5). İmzasız dala düşmez.
  - F79: form kodlamalı imzalı POST 400.
  - F80: `/saat` yalnız NTP yokken `settimeofday`; `unix < 1700000000` ret.
  - F81: zorunlu 1'de `p0` ve `?` serbest (`komut_serbest` önce); misafir yalnız IZLEME'yi açar.
  - F82: `Ez`/`Em` yalnız seri dispatcher'da; web yolunda yok.
  - F83: mbedTLS tablosu `GUV_CTX_BOYU`'na sığar (`static_assert` metni var); PBKDF2 `mbedtls_pkcs5_pbkdf2_hmac_ext(MBEDTLS_MD_SHA256…)`.
  - F84: sabit zamanlı karşılaştırma (`guv__esit` XOR biriktirme; erken `return` yok; `guvenlik.h` kaynak iddiası).
  - F85: `Ns` (parola değişti) `guv_parola_degisti` çağırır ve "eski cihazları çıkarmak için `Ex!`" der (K8).
  - F86: `/akis` imzasını `_c _s _i` sorgu argümanlarından okur; bu üçü kanoniğe girmez (K9).
  - F25: `A3-1D`.
  - `test_kopru.py`: `E…` komutu reddi ve `EK …` satırının yayınlanmaması (davranış testi, mevcut sahte kart deseniyle).
- [ ] **Step 2:** KIRMIZI.
- [ ] **Step 3:** Uygula. Derle (`yukle.py --derle`): uyarısız. DRAM'i cerrahiyle `tasarim3_sabit.py`'ye yaz.
- [ ] **Step 4:** YEŞİL (B72, test_kopru, B71). Kilitler.
- [ ] **Step 5:** Mutasyonlar:
  - `guv_kapi` tek bir uçtan kaldırıldı (F74);
  - `E` reddi kaldırıldı (F76);
  - `ham` yerine `Serial.print` (F77);
  - bozuk imzada imzasız dala düşme (F78);
  - `/saat` NTP denetimi kaldırıldı (F80);
  - `kopru.py` `EK` süzgeci kaldırıldı (test_kopru).
  Commit.

### Task 4: PC istemcisi — eşleştirme, saklama, imzalı istek, eşitleme

**Files:**
- Modify: `kopru/imza.py`:
  - `class Cihaz` (dosya: `kopru/.cihaz/<kimlik>.json`, git dışı; `K` DPAPI ile şifreli, `sayac`, `acilis`, `n`, `ad`);
  - `esles(host, ad, parola) -> Cihaz`;
  - `esles_usb(port, ad) -> Cihaz`;
  - `istek(cihaz, yontem, yol, argumanlar=(), govde=b"") -> (durum, başlıklar, gövde)`: 401 + `X-Acilis` gelirse bir kez eşitleyip yeniden dener;
  - CLI `esles`, `esles-usb`, `liste`, `sil`, `saat`.
- Modify: `kopru/kayit_esitle.py`: `Esitleyici(..., cihaz: Cihaz | None)`; eşleşmişse `/kayit/liste`, `/kayit/veri`, `/kal/liste` ve onay (`/komut` `Go<sıra>`) imzalı; değilse bugünkü yol.
- Modify: `.gitignore`: `kopru/.cihaz/`.
- Test: `uretim/test_kayit_esp.py`. Sahte kart `imza.py`'nin çekirdeğiyle değil, **ayrı** bir doğrulayıcıyla imza denetler: test içinde `hmac` + kanonik kurallarının yeniden yazımı, T1 vektörleriyle sınanmış.

- [ ] **Step 1:** Testler:
  - E20: eşleşmiş `Esitleyici` her isteği imzalar; sahte kart imzasızı reddeder.
  - E21: sahte kart "yeniden başladı" (`acilis` değişti) → istemci 401 + `X-Acilis` ile bir kez eşitlenir, ikinci denemede başarır, sonsuz döngü yok (Review Focus 2).
  - E22: sayaç dosyada kalıcı; yeni süreç eski sayacın altına inmez.
  - E23: eşleşmemiş `Esitleyici` bugünkü jeton + parola yolunu kullanır (regresyon).
  - E24: DPAPI dalı (Windows'ta gidiş-dönüş; değilse atla ve söyle).
  - E25: `esles` sahte karta karşı (sahte kart parolayı bilir); istek gövdelerinde parola dizgisi ve `P` hex'i YOK.
  - E26: `esles_usb` sahte seri hatta `EK 3 <hex>` satırını okur.
- [ ] **Step 2:** KIRMIZI.
- [ ] **Step 3:** Uygula.
- [ ] **Step 4:** YEŞİL; kilit; mutasyonlar:
  - 401'de eşitlemeden yeniden deneme (E21);
  - sayaç dosyaya yazılmıyor (E22);
  - `K` düz yazılıyor (E24 dosya içeriği iddiası).
  Commit.

### Task 5: Tezgah `--guvenlik` + PBKDF2 turu + belgeler

**Files:**
- Modify: `uretim/tezgah_kayit.py`: `guvenlik(k, host)`.
- Modify: DEVIR (cerrahi), `tasarim/1-acik-isler.md` (devredilen "onay kimliksiz" maddesinin üstü çizilir: zorunlu açılınca kapanır), spec durum notu.

- [ ] **Step 1:** NVS yedeği → yükle → `--duman` regresyonu.
- [ ] **Step 2:** `Et50000`, `Et100000` ölç. Tur, kartta < 1 s ve en büyük "10 000'in katı" olacak şekilde seçilir. `Er<tur>` ile yazılır, plan defterine kaydedilir.
- [ ] **Step 3:** `--guvenlik` (spec "Doğrulama/Tezgah"):
  - USB eşleştirme; `EK` satırı aynı anda açık `/akis` SSE'sinde YOK;
  - imzalı `/kayit/liste`, `/kayit/veri`, `Go` onayı;
  - tekrar / bozuk imza / değişik yol 401;
  - yanlış parolalı eşleştirme reddi + `GUV_E_BEKLE`;
  - yeniden başlatma → eski `acilis` 401 → istemci eşitlenir;
  - `Ez1`: imzasız `/kayit/liste` 401, `p0` 204, imzalı 200; `Em1` → imzasız `/akis` açık; `Ez0` / `Em0`;
  - trafik dökümünde `K` hex'i yok;
  - sonunda `Ex<n>`.
- [ ] **Step 4:** Kartı `main` firmware'ine geri yükle (NVS yedeği önce). Tam mutasyon (mut_par B71/B72), zincir, gizlilik. Bütün commit'ler dalda; push yok.
