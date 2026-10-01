# Alt proje 1C-4 — Zamanlanmış kayıt Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Gp` ile tek bir kayıt gerçek saate göre başlasın ve bitsin. Plan NVS'te kalıcı olsun, yeniden başlamada korunsun, başka bir işi bölmesin.

**Architecture:**
- **Mantık:** platformsuz `kayit_plan.h` (plan durumu + `plan_adim` karar işlevi + NVS işlev tablosu), AVR'de emüle NVS ve sahte saatle sınanır.
- **Kart:** çekirdek 1 her saniye `plan_adim` çağırır ve eylemi mevcut mesaj yollarına çevirir: `KM_BASLAT` + `KM_OLAY(PLAN)` ile başlar, `KM_PLAN_BITIR` ile biter. BASLA'yı `Gb` gibi çekirdek 1 kurar; kalibrasyon kopyası ve numarası onun elinde.
- **Kalıcılık:** kendi `Preferences` ad alanı `plan`.

**Tech Stack:** C (platformsuz başlık, AVR emülatörü), ESP32-S3 Arduino, Python (kopru), mevcut zincir.

**Spec:** `tasarim/2026-10-01-1c4-zamanlanmis-kayit.md` (K1–K11).

## Global Constraints

- Biçim sürümü 2 kalır; sebep 7 ve `KO_PLAN` (5) bilinmeyen okuyucuda zararsız.
- Plan hiçbir oturumu (elle, pil, skop günlüğü) bölmez; pil testinde başlamaz (Ö7).
- Kullanıcının B55–B70 dosyaları yalnız cerrahiyle; heredoc'la kaçışlı Python yazılmaz (Write aracı).
- Görev testleri `bash -o pipefail -c '…'`; zincir mutasyon koşusuyla AYNI ANDA koşmaz.
- Depo herkese açık: gizlilik temiz olmadan push yok; NVS yedeği depo dışında.

## Review Focus

1. **Yanlış oturumu kapatmak:** plan bitişi yalnız planın açtığı oturumu kapatmalı. Kullanıcı arada `Gd` + `Gb` yaptıysa yeni oturuma dokunulmamalı (Görev 2–3).
2. **Saat sıçraması:** NTP geç gelirse ya da saat geri giderse plan iki kez başlamamalı, hiç bitmeden kalmamalı (Görev 2).
3. **Yeniden başlama:** başlamış planın oturumu DEVAM alırsa bitiş korunmalı; DEVAM alamadıysa plan "bitti" olmalı, yeni oturum açmamalı (Görev 2).
4. **Kaçırılan başlangıç:** pencere içindeyse geç başlamalı (kalan süre), pencere dışındaysa hiç başlamamalı (Görev 2).
5. **Meşgul:** başlangıçta oturum varsa plan atlanmalı ve kart bunu `GP`'de söylemeli; sonradan kendiliğinden başlamamalı (Görev 2).

---

### Task 1: Biçim — sebep 7, OLAY `PLAN`

**Files:** `kayit_bicim.h`, `kopru/kayit_bicim.py`, `ornek_kayit.c` (`bicim_1c4`), `test_kayit.py` (B71.B30–B31).

**Produces:** `KB_SEBEP_PLAN 7u`; `KO_PLAN 5u`, `KAYIT_OLAY_PLAN_BAYT 24u`; `typedef struct { uint32_t bas_unix, sure_s, hiz_ms, plan_no; } KayitPlanOlay;`; `kayit_olay_plan_paketle(kart_ms, const KayitPlanOlay*, p)`. Python `SEBEP[7]`, `_OLAY[KO_PLAN]`.

- [ ] Test (önce kırmızı): B30 PLAN olayı C == Python. B31 sebep 7 metni ve `bitir_coz`.
- [ ] Uygula; B71 yeşil. Commit.

### Task 2: Platformsuz plan mantığı — `kayit_plan.h`

**Files:** `kod/olcum-karti-a3/kayit_plan.h` (yeni), `ornek_kayit.c` (`SENARYO_PLAN`), `test_kayit.py` (`bolum_plan`, B71.R1–R8), `CPP_BASLIKLAR`.

**Produces:**
- `KayitPlan` (bas, sure, hiz, no, durum, oturum);
- `PLAN_YOK/BEKLIYOR/SURUYOR/BITTI/ATLANDI/KACIRILDI/SAAT_YOK`;
- `plan_ac(KayitPlan*, const KayitNvs*)`, `plan_kur(…, bas, sure, hiz, simdi_unix)` → 0/hata, `plan_iptal`;
- `plan_adim(KayitPlan*, uint32_t simdi_unix, uint8_t oturum_var, uint32_t oturum_id)` → `PE_YOK/PE_BASLAT/PE_BITIR/PE_ATLA`;
- `plan_basladi(KayitPlan*, uint32_t oturum_id)`, `plan_bitti(KayitPlan*)`.

Durum her değişimde NVS'e yazılır.

- [ ] Test (önce kırmızı), açılıştan açılışa emüle NVS + sahte saat:
  - R1 başlangıçta BASLAT, süre dolunca BITIR;
  - R2 meşgulse ATLA, sonra başlamaz;
  - R3 pencere içinde geç başlar (kalan süre);
  - R4 pencere dışı KACIRILDI;
  - R5 saat yok → bekler, saat gelince karar verir;
  - R6 yeniden başlamada SURUYOR + oturum aynı → BITIR yine zamanında; oturum yok → BITTI;
  - R7 kullanıcı `Gd` (oturum kapandı) → BITTI, ikinci BITIR yok;
  - R8 iptal; saat geri gitse de çift başlama yok.
- [ ] Uygula; B71 yeşil. Commit.

### Task 3: Kart — `Gp`, `KM_PLAN_BITIR`, `GP`

**Files:** `kayit_esp.h`, `olcum-karti-a3.ino`, `test_kayit_esp.py` (B72.F63–F70), `tasarim3_sabit.py` (DRAM, cerrahi).

- `Gp<bas>,<sure>,<hiz>`, `Gp+<s>,<sure>,<hiz>`, `Gp-`.
- Saat yoksa ret; hız `kayit__hiz_gecerli`; süre 0..30 gün.
- `loop` saniyede bir `plan_adim`:
  - BASLAT → `kayit_basla_doldur` + `KM_PLAN_BASLAT` (BASLA + PLAN olayı tek mesaj, `KM_PIL_BASLAT` yolu);
  - BITIR → `KM_PLAN_BITIR` (oturum id, sebep 7).
- Görev yalnız etkin oturum == planınki ise kapatır.
- `Gd` planı bitirir.
- `G?` ardından `GP`.
- `A3-1C4`.
- [ ] Test (önce kırmızı) B72.F63–F70; derle (uyarısız); B72 + arayüz yeşil. Commit.

### Task 4: Tezgah — `--plan`

- [ ] NVS yedeği → yükle.
- [ ] `--plan`:
  - `Gp+20,30,200` → başlar (± 2 s), sebep 7 ile biter, PLAN olayı;
  - plan sürerken yeniden başlatma → DEVAM, bitiş zamanında;
  - elle kayıt sürerken plan → atlandı (`GP` durum 4);
  - `Gp-` iptal;
  - geçersiz argüman reddi.
- [ ] Regresyon `--duman --pil --ayrinti --skop`. Commit.

### Task 5: Mutasyon, kilit, zincir, belgeler, inceleme, push

- [ ] Yalanlayıcılar; odaklı + tam koşu; kilit; zincir 21/21; gizlilik.
- [ ] Bağımsız son inceleme (opus); düzeltme turu.
- [ ] DEVIR 5.12.71, spec §5 notu, CLAUDE.md, hafıza; commit + `git push origin main`.
