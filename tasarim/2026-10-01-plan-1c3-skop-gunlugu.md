# Alt proje 1C-3 — Osiloskop günlüğü Uygulama Planı

> **Durum (2026-10-01): UYGULANDI** (DEVIR 5.12.70). Bağımsız son incelemeden
> sonra altı düzeltme yapıldı; görev metinlerinin ötesine geçenler: yakalamanın
> kayıt sırasıyla kurulması (K15), yuvanın oturuma bağlanması (K16), her yakalamadan
> sonra ölçüm (K17), kirli silme işaretinin platformsuz `ksi_*`'ye taşınması.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Gt` ile osiloskop yakalamaları kartın kayıt günlüğüne yazılsın (her tetikte ya da N ms'de bir), PC eşitlenen dosyadan onları `/skop.bin` biçimine birebir çevirebilsin.

**Architecture:**
- **Biçim:** SKOP (10) kaydı parça parça; ilk parça META. OLAY `SKOP_KAL` kalibrasyon tablosunu taşır.
- **Yazıcı:** `ky_skop` (platformsuz), sektöre bölerek yazar.
- **Oturum:** ÖLÇÜM oturumu varsa onun içine; yoksa SKOP oturumu (3).
- **Kart:** çekirdek 1 yakalamayı tek PSRAM yuvasına kopyalar, `KM_SKOP` ile görev yazar ve yuvayı boşaltır; günlük ancak bundan sonra yeniden kurar.

**Tech Stack:** C (platformsuz başlıklar, AVR emülatörü), ESP32-S3 Arduino 3.3.11, Python 3.14 (kopru), mevcut test zinciri.

**Spec:** `tasarim/2026-10-01-1c3-skop-gunlugu.md` (K1–K14).

## Global Constraints

- Biçim sürümü 2 kalır; yeni tür bilinmeyen okuyucuda geçerli (CRC) ve atlanır.
- Ölçüm tarafı (çekirdek 1) asla beklemez; skop kilidi zaman aşımı 0 kalır.
- Pil testinde yakalama yok; `p0` koşulsuz (Ö7).
- Kullanıcının B55–B70 dosyaları (`mutasyon.py`, `beklenen_sayim.json`, `tasarim3_sabit.py`, `DEVIR.md`, …) yalnız cerrahiyle; `git add` ile süpürme yok.
- Görev bitiş testleri `bash -o pipefail -c '…'`.
- Depo herkese açık: gizlilik denetimi temiz olmadan push yok; NVS yedeği depo dışında.

## Review Focus

1. **Yuva yarışı:** çekirdek 1 yuvayı yazarken çekirdek 0 okuyamaz, okurken yeni yakalama yuvaya kopyalanamaz. Yeniden kurma yuva boşalmadan olmamalı (Görev 3).
2. **Parçalama:** 4000 örnek sektör sınırlarında bölünür; bir parça kaybolursa yakalama "tam" sayılmamalı, sessizce sıfırla doldurulmamalı (Görev 1–2).
3. **Oturum türü sızıntısı:** SKOP oturumu `hiz_ms 0` iken ayrıntılı kip ya da noktacı açılmamalı; ÖLÇÜM'e eklenen günlük ölçümü kapatmamalı (Görev 2–3).
4. **Emniyet:** günlük sürerken `p1` ve elle yakalama reddedilmeli; pil testinde `Gt` reddi (Görev 3).
5. **Yeniden başlama:** açık SKOP oturumu sebep 5 ile kapanmalı, DEVAM almamalı (Görev 2).

---

### Task 1: Biçim — SKOP kaydı, SKOP oturumu, SKOP_KAL olayı

**Files:** `kod/olcum-karti-a3/kayit_bicim.h`, `kopru/kayit_bicim.py`, `uretim/avr/ornek_kayit.c` (SENARYO_BICIM `bicim_1c3`), `uretim/test_kayit.py` (B71.B25–B28).

**Produces:**
- C: `KAYIT_T_SKOP 10u`, `KAYIT_T_AZAMI 10u`, `KAYIT_OTURUM_SKOP 3u`, `KO_SKOP_KAL 4u`, `KAYIT_SKOP_PARCA_BAS 12u`, `KAYIT_SKOP_META 36u`, `KAYIT_SKOP_AZAMI 4000u`.
- C: `typedef struct { uint32_t t_ms, sure_ms, hz, tdiv_us; float adim, ofset; uint16_t tetik, esik; uint8_t kip, tetiklendi, kenar, histerezis, on_yuzde, onay; } KayitSkopMeta;`
- C: `kayit_skop_parca_paketle(uint8_t *p, uint32_t no, uint16_t ilk, uint16_t adet, uint16_t toplam, uint8_t parca)`, `kayit_skop_meta_paketle(uint8_t *p, const KayitSkopMeta *m)`, `kayit_olay_skop_kal_paketle(uint8_t *p, uint32_t kart_ms, const int16_t mv[17])` (dönüş: bayt).
- Python: `T_SKOP=10`, `OTURUM_SKOP=3`, `KO_SKOP_KAL=4`, `skop_paketle(d)`/`skop_coz(yuk)`, `Oturum.skoplar`, `oturumlari_kur` birleştirme (`tam`), `skop_ikili(y) -> bytes` (32 B `S3B` başlık + u16 kodlar, `kopru/arsiv.py skop_ikili` ile aynı başlık).

- [ ] Test (önce kırmızı): `bicim_1c3` iki parça (META'lı 0. parça 3 kod, 1. parça 2 kod) + `SKOP_KAL` olayı basar. B25 C == Python paket. B26 tür 10 ve AZAMI 10, sürüm 2. B27 `oturumlari_kur` iki parçayı birleştirir (`tam`), eksik parçada `tam=False`, kodlar sessizce doldurulmaz. B28 `skop_ikili` başlığı `arsiv.skop_ikili` ile bayt bayt aynı.
- [ ] Uygula; `python test_kayit.py` yeşil.
- [ ] Commit "1C-3 bicim: SKOP kaydi (10), SKOP oturumu (3), SKOP_KAL olayi".

### Task 2: Yazıcı ve yönetici — `ky_skop`, oturum türü kuralları

**Files:** `kayit_oturum.h`, `kayit_yonet.h`, `ornek_kayit.c` (yeni `SENARYO_SKOP`), `test_kayit.py` (`bolum_skop`, B71.S1–S8).

**Consumes:** Task 1 packers. **Produces:** `int ky_skop(KayitYazici *y, const KayitSkopMeta *m, const uint16_t *kod, uint16_t toplam, uint32_t no)`; `int kyn_skop(KayitYonetici *m, const KayitSkopMeta *mt, const uint16_t *kod, uint16_t toplam, uint32_t no)`.

- `ky_skop`: oturum yoksa `KG_YOK`; önce `ky_bosalt` + `ky_ayrinti_bosalt`. Sonra parça döngüsü: `kalan = KAYIT_SEKTOR - bas_ofset`, `sabit = BASLIK + 12 + (parca0 ? 36 : 0) + KY_BITIR_PAY`, `n = min(kalan-sabit)/2, tampon sınırı (KAYIT_AZAMI_YUK-12-meta)/2, kalan örnek)`. `n < 32` ve kalan örnek > n ise yeni sektör. Parça `y->yuk`'ta kurulur, `kg_ekle(KAYIT_T_SKOP)`. Hata → `ky__dolu`.
- `ky_baslat`/`ky_devam`: `ayrinti = (tür == ÖLÇÜM && hiz_ms == 0)`.
- `ky_nokta`, `ky_ayrinti_ornek`: SKOP oturumunda `KG_YOK`.

- [ ] Test (önce kırmızı), SENARYO_SKOP (küçük sektör):
  - S1: 1000 örneklik yakalama birden çok sektöre bölünür, PC birebir birleştirir, META aynı.
  - S2: parça sektör sonunu boşa harcamaz (en fazla bir asgari parça kadar).
  - S3: SKOP oturumu `hiz_ms 0` iken ayrıntılı kip KAPALI, `ky_nokta` ve `ky_ayrinti_ornek` `KG_YOK`.
  - S4: ÖLÇÜM oturumuna eklenen yakalama aynı oturumda, bekleyen noktalardan SONRA (sıra), noktalar sürer.
  - S5: açılışta açık SKOP oturumu sebep 5 ile kapanır.
  - S6: DOLU'da BITIR(DOLU), oturum kapanır.
  - S7: flaş temiz (bozuk 0, BITIR payı, TEKRAR kuralı).
  - S8: ayrıntılı ÖLÇÜM'e eklenen yakalamadan önce örnek tamponu boşaltılır.
- [ ] Uygula; B71 yeşil (önceki 224 + yeni).
- [ ] Commit "1C-3 yazici: ky_skop parcali yazar, ayrintili kip yalniz OLCUM'de".

### Task 3: Kart — `Gt`, PSRAM yuvası, `KM_SKOP`, `GT`

**Files:** `kayit_esp.h`, `olcum-karti-a3.ino`, `test_kayit_esp.py` (B72.F49–F58), `tasarim3_sabit.py` (DRAM, cerrahi).

**Consumes:** `kyn_skop`, `KO_SKOP_KAL`, `KAYIT_OTURUM_SKOP`.

- `kayit_esp.h`:
  - `KM_SKOP 8u`;
  - yuva `KayitSkopYuva { KayitSkopMeta meta; uint16_t toplam; uint32_t no; uint16_t kod[4000]; }`, `heap_caps_malloc(..., MALLOC_CAP_SPIRAM)`;
  - `volatile uint8_t kayit_skop_dolu`;
  - görev `KM_SKOP`'ta `kyn_skop` → `kayit_skop_dolu = 0` (hata olursa `kayit_skop_hata++`);
  - `kayit__nesil`: noktacı `tür != SKOP && hiz_ms`, ayrıntılı `tür == ÖLÇÜM && hiz_ms == 0` (durumda `tur` alanı);
  - `GT` alanları.
- `.ino`:
  - `SKOP_IS_GUNLUK`;
  - günlük durumu `skop_gunluk {aktif, aralik_ms, no, son_ms, t_istek}`;
  - `loop`'ta `skop_gunluk_isle()` (`skop_sonuc_isle`'den sonra; skop boşta, döküm yok, yuva boş, aralık doldu → `skop_is_ver(SKOP_IS_GUNLUK)`);
  - `skop_sonuc_isle`:
    - GUNLUK + OK: yuvaya kopyala + META → `KM_SKOP` gönder (gönderilemezse yuva boşaltılır, `atlanan++`);
    - TETIK_YOK: yeniden kur;
  - `Gt<ms>` (0 ya da 1000…3 600 000): PSRAM yoksa, pil testindeyse, skop meşgulse ret; ÖLÇÜM oturumu yoksa `KM_BASLAT` (tür SKOP, `hiz_ms` = aralık); `KO_SKOP_KAL` olayı;
  - `Gtd`;
  - `Gd` günlüğü de durdurur;
  - `p1`, `t`/`tB`/`ta` günlükte ret;
  - `G?` ardından `GT <aktif> <aralik> <yakalama> <atlanan>`;
  - `A3-1C3`.
- [ ] Test (önce kırmızı) B72:
  - F49 `Gt` sınırları;
  - F50 PSRAM ret;
  - F51 pil ret / `p1` ret;
  - F52 elle yakalama ret;
  - F53 yuva boşalmadan kurma yok;
  - F54 GUNLUK sonucu dökümsüz;
  - F55 `KM_SKOP` görevde `kyn_skop` + yuva boşaltma;
  - F56 noktacı/ayrıntılı tür kuralı;
  - F57 `GT` satırı;
  - F58 `Gd` günlüğü durdurur.
  - F25 → `A3-1C3`.
- [ ] Derle (uyarısız), DRAM güncelle (cerrahi), B72 + arayüz yeşil.
- [ ] Commit "1C-3 kartta: Gt osiloskop gunlugu, PSRAM yuvasi, GT satiri".

### Task 4: Tezgah — `--skop`

**Files:** `uretim/tezgah_kayit.py`, `test_kayit_esp.py` (tezgah kalemi).

- [ ] NVS yedeği → yükle.
- [ ] `tezgah_kayit.py --skop`:
  - CAL `X1000`;
  - `Gt0` 30 s ve `Gt2000` 30 s: eşitle → her yakalama `tam`, `skop_ikili` başlığı geçerli, ölçülen frekans ~1 kHz, sayı ≈ beklenen, `GT` sayaçları = flaştaki;
  - `Gb200` + `Gt2000`: noktalar ve yakalamalar aynı oturumda;
  - günlükte `p1` ve `t` reddi;
  - yeniden başlatmada SKOP oturumu sebep 5;
  - `X0`.
- [ ] Regresyon `--duman --pil --ayrinti`.
- [ ] Commit "1C-3 tezgah: --skop".

### Task 5: Mutasyon, kilit, zincir, belgeler, inceleme, push

- [ ] Her yeni iddiaya yalanlayan mutasyon (cerrahi); odaklı + B72 tam koşu; değişen satırlara bağlı eski mutasyon desenleri güncellenir.
- [ ] Kilit (cerrahi); zincir 21/21 (mutasyon koşusuyla AYNI ANDA değil: zincir sonunda %TEMP% temizler); gizlilik temiz.
- [ ] Bağımsız son inceleme (opus); düzeltme turu.
- [ ] DEVIR 5.12.70 (cerrahi), spec §5 notu, CLAUDE.md, hafıza.
- [ ] Commit + `git push origin main`.
