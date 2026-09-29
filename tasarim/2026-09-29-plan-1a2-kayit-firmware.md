# Alt proje 1A-2 — Kayıt motorunun karta bağlanması Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 1A-1'de doğrulanan kayıt motorunu (B71) ESP32 firmware'ine bağlamak, kartı gerçekten kaydeder hale getirmek, PC'nin bu kayıtları eşitleyebilmesini sağlamak ve bunu gerçek kartta ölçmek.

**Architecture:**
- Motor (`kayit_*.h`) değişmeden kalır; yalnızca ESP32 ayarı ve bir tarama iyileştirmesi eklenir.
- Yeni `kayit_esp.h` ESP32 yapıştırıcısıdır: flaş bölümü, NVS, çekirdek 0'da kayıt görevi, kuyruklar, kilit. Bu dosya `Serial` kullanmaz.
- `.ino` tarafı ölçüm çekirdeğinde (1) örneği noktacıya verir. `G` komutu ile `G` durum satırı da ölçüm çekirdeğinde (1) çalışır; `/kayit/*` uçları ağ görevinde (çekirdek 0) çalışır.
- PC'de `kopru/kayit_esitle.py` eksik kayıtları çeker. Kayıtları doğrular, diske yazar ve ancak ondan sonra onaylar.

**Tech Stack:** ESP32-S3 Arduino çekirdeği 3.3.11 (ESP-IDF, FreeRTOS, `esp_partition`, `Preferences`, `WebServer`); Python 3.14 stdlib; mevcut tezgah araçları (`kart_baglanti`, `esptool`).

**Spec:** [tasarim/2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) (§5 kayıt modeli ve eşitleme, §8 zaman, §11 riskler). Önceki dilim: [1A-1 planı](2026-09-29-plan-1a1-kayit-motoru.md), DEVIR 5.12.65.

## Kapsam

| Dahil | Dahil değil (neden) |
|---|---|
| Bölüm tablosu (`partitions.csv`, ~11.4 MB kayıt bölümü) | Köprünün "kayıtlıysa ikinci istemciyi reddet" kuralı → **alt proje 4** (köprü zaten yeniden tasarlanacak; bu kural 3 testi birden değiştiriyor) |
| Kayıt görevi, kuyruk, kilit, NVS (açılış sayacı, onay, sıra tabanı), NTP | Pil testi ve osiloskop oturum türleri, zamanlanmış kayıt → **1C** |
| `G` komutu + `G` durum satırı + yardım | Eşleştirme ve imzalı istekler → **1D**. `/kayit/*` okuması bugünkü `/pil` gibi açık; onay mevcut komut yolundan gider (jeton + parola ya da USB) |
| `/kayit/liste` (JSON), `/kayit/veri` (ikili) | MQTT, bildirim → **1E** |
| `kopru/kayit_esitle.py` + sahte kart testleri | Web panelinin kayıt ekranları → **alt proje 3** |
| Karta yükleme, tam flaş yedeği, tezgah ölçümleri | ADS'e bağlı ölçümler (D satırı ile çözücü volt karşılaştırması) → ADS takılınca |

## Bu planın kilitlediği kararlar
- **Bölüm tablosu:** `nvs` 0x9000/0x5000, `otadata`, `app0` 0x10000/3 MB aynı yerde. Böylece WiFi parolaları ve `Ayar3` kalibrasyonu korunur.
  - `spiffs` aynı ofsette büyür: 0x310000'dan başlayıp 896 KB → 1.5 MB.
  - **`kayit`** bölümü: `data`, alt tür `0x40`, 0x490000'dan başlar, 0xB60000 bayt (2912 sektör).
  - `coredump` en sona taşınır: 0xFF0000.
- **Açılış taraması** kayıt görevinde (çekirdek 0) yapılır; `setup()` beklemez. Tarama bitene kadar `G` durumu `0` (tarıyor) olur, komutlar kuyrukta bekler.
- **Kayıt hızları:** 20, 100, 200, 1000, 10000, 60000 ms (50/s, 10/s, 5/s, 1/s, 10 s'de 1, dakikada 1).
- **`G` satırı** (çekirdek 1 basar; kayıt sürerken saniyede bir, durum değişince hemen):
  `G <durum> <oturum> <nokta> <sonraki_sira> <onay> <doluluk‰> <onaysız‰> <düşen> <yaz_azami_us> <sil_azami_us> <sil_adet> <tarama_ms> <son_hata>`
  - Durum kodları: 0 tarıyor · 1 boş · 2 kayıt · 3 dolu · 4 bekliyor (açık oturum var, yer yok) · 5 hata.
- **NVS** (`Preferences` ad alanı `kayit`) üç değer tutar:
  - `acilis`: her açılışta +1.
  - `onay`: en az 16 sıra ilerleyince ya da 30 s geçince yazılır.
  - `taban`: biçimlemeden **önce** yazılır.
- **Bellek doluyken yeniden başlama:** oturum sürdürülemezse (inceleme bulgusu 2) durum 4 olur. Bir sonraki geçerli onayda sürdürme yeniden denenir.
- **Eşitleme:** istemci `/kayit/veri?sira=N&bayt=M` ile çeker (M ≤ 8192). CRC'yi `kayit_bicim.akis_coz` ile doğrular. Kartın baytlarını `kayitlar.kyt`'ye **aynen** ekler, `fsync` eder, `durum.json`'u atomik yazar ve **ancak ondan sonra** onaylar.

## Global Constraints

- **Motor başlıkları** (`kayit_*.h`) platformdan bağımsız kalır:
  - C11/C++11 uyarısız.
  - AVR testleri (`test_kayit.py`) yeşil kalır.
- **Firmware derlemesi:**
  - `--warnings all` ile **UYARISIZ** (`test_firmware3.py`).
  - Statik RAM payı **< %25**; bugün %22, 72 108 B. Büyük tamponlar statik değil, çalışma anında ayrılır: sektör tablosu ve dizin PSRAM'de, veri tamponu dahili yığında.
  - C++20'de `volatile` üzerinde `++`/`+=` uyarı verir; `x = x + 1` biçimi kullanılır (mevcut `ag_tur` deseni).
- **Kayıt başlığında (`kayit_esp.h`) `Serial` YOK**, çünkü bu dosya `#define Serial CIKIS`'ten önce dahil ediliyor. Satır basma yalnızca `.ino`'da, çekirdek 1'de.
- **Python:** yalnızca stdlib.
- **Doğrulama:**
  - Her yeni iddianın çalıştırılabilir bir testi ve onu yalanlayan bir mutasyonu olur.
  - Zincir adımı `B72` olur, özet satırı `B72: X/Y kosul gecti`.
- **Depoya sır girmez:** WiFi parolası, web parolası ve ev ağı IP'si depoda olmaz. Tam flaş yedeği NVS'i, yani parolaları içerir; **depo dışına** yazılır: `<çalışma alanı>/.yedek/olcum-karti/` (depo kökünün iki üstü).
- **Commit:**
  - Kullanıcının commit'lenmemiş B55–B70 işi bulunan dosyalara (`dogrula3.py`, `mutasyon.py`, `beklenen_sayim.json`, `DEVIR.md`, `tasarim3_sabit.py`) yalnızca "HEAD + bu planın eki" sürümü index cerrahisiyle (`git hash-object -w --path` + `git update-index --cacheinfo`) konur. Bu dosyalarda `git add` **KULLANILMAZ**.
  - Mesaj sonu `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Karta yazan her işlemden önce** (`yukle.py`, `arayuz-yaz.py`) tam flaş yedeği alınmış olmalı (Task 8 Step 1).

## Review Focus

1. **Kart kayıt sürerken sıfırlanırsa** kayıt kaldığı yerden DEVAM etmeli ve nokta sırası kesintisiz olmalı. → Task 8 `--kesinti` (gerçek RTS sıfırlaması)
2. **Flaş silinirken ölçüm çekirdeği noktaları kuyruğa atmaya devam eder;** kuyruk taşarsa kayıp sessiz olmamalı: `düşen` sayacı + `KN_KAYIP_ONCE`. → Task 8 `--durma` (50/s'de düşen = 0 beklenir; değilse sayı raporlanır)
3. **Eşitleme istemcisi bozuk ya da geri giden yanıtta** diske yazmamalı, onaylamamalı. → Task 6 E3, E6
4. **Kayıt bölümü olmayan eski tabloyla açılan firmware** kaydı sessizce kapatmamalı: afişte "Kayit: KAPALI", `G` komutunda açık hata. → Task 3 F2, Task 8 `--duman`
5. **Biçimlemede sıra tabanı NVS'e biçimlemeden ÖNCE** yazılmalı; yarıda kesilen biçimleme numarayı başa döndürmemeli. → Task 4 F9

---

### Task 1: Motor — ESP32 okuma parçası ve boş sektör taraması

**Files:**
- Modify: `kod/olcum-karti-a3/kayit_gunluk.h`
- Modify: `uretim/avr/nor_flas.py` (okunan bayt sayacı)
- Modify: `uretim/avr/ornek_kayit.c` (TARAMA senaryosu)
- Modify: `uretim/test_kayit.py` (`bolum_tarama`)

**Interfaces:**
- Produces: `KG__PARCA` artık `#ifndef` ile dışarıdan verilebilir (ESP32: 256). `kg__sektor_tara(..., uint8_t *temiz)` `temiz == NULL` kabul eder. `NorFlas.okunan_bayt`. `derle(senaryo, sektor_adet, ek=())` ek `-D` bayrakları alır.

**Neden:**
1. Kurtarma bugün her boş sektörün 4096 baytının hepsini "0xFF mi" diye okuyor. 2912 sektörlük bölümde bu, her açılışta 11.4 MB demek. Oysa `temiz` bilgisi yalnızca yazılan (baş) sektör için gerekiyor.
2. **Plan denetiminde bulunan gizli kusur:** `kg__ff_mi` döngüsü `uint8_t i; i < (uint8_t)n`. `KG__PARCA` 256 olunca `(uint8_t)256 == 0` olur ve döngü hiç çalışmaz. O zaman kirli kuyruk "temiz" sayılır ve yeni kayıt 0xFF olmayan baytların üstüne yazılır; NOR'da bu, bozuk kayıt demek. AVR testi 32 ile koştuğu için bunu hiç görmedi. T2 bunu 256 ile sınar.

- [ ] **Step 1: Testi yaz**

`uretim/avr/nor_flas.py`'de `self.kesilen_silme = 0` satırının altına ekle:

```python
        self.okunan_bayt = 0      # kurtarma maliyeti olculsun (B72)
```

`_veri_oku` içinde `self.adres = a + 1` satırının hemen altına ekle:

```python
        self.okunan_bayt += 1
```

`uretim/avr/ornek_kayit.c`'de hata denetimindeki senaryo listesine `|| defined(SENARYO_TARAMA)` ekle. İki yerde:
- `#if defined(SENARYO_GUNLUK) || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI) \` ile başlayan NOR bloğu koşulu
- `#if !(defined(SENARYO_BICIM) ...` hata koşulu

`/* ── giris ── */` satırının hemen üstüne ekle:

```c
#if defined(SENARYO_TARAMA)
/* B72: bos flasta kurtarma yalniz sektor BASLIKLARINI okumali; baslik
   disindaki 0xFF denetimi yalniz yazilan (bas) sektorde gerekli.
   BAS/OFSET: bas sektorun kuyrugu kirliyse yeni kayit oraya YAZILMAMALI
   (OFSET = KAYIT_SEKTOR). */
static void senaryo(void)
{
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    sayi("AC", kg_ac(&g, 0u, 0u));
    sayi("BAS", (int32_t)g.bas);
    sayi("OFSET", (int32_t)g.bas_ofset);
    metin("BITTI\n");
}
#endif
```

`uretim/test_kayit.py`'de `derle` imzasını `def derle(senaryo: str, sektor_adet: int = SEKTOR_ADET, ek: tuple[str, ...] = ()) -> Path:` yap. Önbellek anahtarı `anahtar = f"{senaryo}_{sektor_adet}" + "".join(ek)` olsun. `-DNOR_SEKTOR_ADET={sektor_adet}u",` satırından sonra `*ek,` ekle. Aynı yerde ELF adı `ornek_kayit_{anahtar}.elf`; `ek` içinde `=` olduğundan dosya adında sorun çıkarmaz.

`bolum_dizin`'in üstüne ekle:

```python
# ── B71.T · kurtarma maliyeti ve kirli kuyruk ─────────────────────────
def bolum_tarama() -> None:
    """B72 (1A-2): gercek bolum 2912 sektor; bos sektorun tamamini okumak
    her acilista 11.4 MB demekti. ESP32'de okuma parcasi 256: `kg__ff_mi`
    uint8_t sayaci (uint8_t)256 == 0 yuzunden parcayi HIC denetlemiyordu."""
    print("\n── B71.T  kurtarma maliyeti · 256'lik parcada kirli kuyruk")
    flas = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    sat = kos(derle("TARAMA"), flas)
    sinir = SEKTOR_ADET * 2 * KB.BASLIK_BAYT + SEKTOR
    ok("B71.T1 bos flasta kurtarma yalniz sektor basliklarini (+ bas sektoru) okur",
       alanlar(sat, "AC") == [["0"]] and flas.okunan_bayt <= sinir,
       f"okunan {flas.okunan_bayt} B (sinir {sinir}, tam tarama "
       f"{SEKTOR_ADET * (SEKTOR + 2 * KB.BASLIK_BAYT)})")
    elf = derle("TARAMA", ek=("-DKG__PARCA=256u",))
    kay = KB.kayit_paketle(KB.T_SAAT, 1, 0, bytes(12))
    sonuc = {}
    for kirli in (False, True):
        flas = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
        a = 3 * SEKTOR
        flas.bellek[a:a + len(kay)] = kay
        if kirli:
            flas.bellek[a + 100] = 0x00      # ilk 256'lik parcanin icinde
        s = kos(elf, flas)
        sonuc[kirli] = (alanlar(s, "BAS"), alanlar(s, "OFSET"))
    ok("B71.T2 KG__PARCA=256: kirli kuyruk algilanir (yeni kayit sonraki sektore), "
       "temiz kuyrukta kayit arkasina yazilir",
       sonuc[False] == ([["3"]], [[str(len(kay))]])
       and sonuc[True] == ([["3"]], [[str(SEKTOR)]]), f"{sonuc}")
```

`BOLUMLER` listesine `bolum_tarama`'yı `bolum_dizin`'den önce ekle.

- [ ] **Step 2: Kırmızıyı gör**

Run: `cd uretim && python test_kayit.py --kesinti 20`
Expected:
- `[!!] B71.T1 …   okunan 4352 B (sinir 768, …)`
- `[!!] B71.T2 …` kirli kuyrukta `OFSET 28`. Kusur yüzünden kuyruk temiz sayılıyor.

- [ ] **Step 3: Motoru değiştir**

`kod/olcum-karti-a3/kayit_gunluk.h`'de:

```c
#define KG__PARCA 32u
```

satırını şununla değiştir:

```c
#ifndef KG__PARCA
#define KG__PARCA 32u   /* okuma parcasi (yigin); ESP32'de 256 (kayit_esp.h) */
#endif
```

`kg__sektor_tara`'nın başındaki açıklama satırını ve sonunu şöyle değiştir. `temiz` NULL olabilir:

```c
/* Sektoru bastan tara. Donus: son gecerli kaydin bittigi ofset.
   `temiz` NULL degilse: o ofsetten sektor sonuna kadar her bayt 0xFF mi.
   NULL: denetleme (yalniz BAS sektorde gerekli — bos sektorun 4 KB'ini
   okumak 2912 sektorde her acilista 11.4 MB demekti). */
```

Aynı fonksiyonun sonundaki:

```c
    if (d == -2) {
        g->oku_hata = 1u;          /* okunamayan veri COP DEGIL */
        *temiz = 0u;
    } else if (d < 0) {
        g->bozuk++;
        *temiz = 0u;
    } else {
        *temiz = kg__ff_mi(g, a, son);
    }
```

bloğunu şununla değiştir:

```c
    if (d == -2) {
        g->oku_hata = 1u;          /* okunamayan veri COP DEGIL */
        if (temiz) *temiz = 0u;
    } else if (d < 0) {
        g->bozuk++;
        if (temiz) *temiz = 0u;
    } else if (temiz) {
        *temiz = kg__ff_mi(g, a, son);
    }
```

`kg_ac`'ta `uint8_t temiz, bos = 1u;` satırını `uint8_t temiz = 0u, bos = 1u;` yap. Ardından:

```c
        ofset = kg__sektor_tara(g, s, kg__besle, &temiz);
```

satırını şununla değiştir:

```c
        ofset = kg__sektor_tara(g, s, kg__besle, (s == bas) ? &temiz : 0);
```

`kg__ff_mi`'de:

```c
        uint8_t i;
        if (n > KG__PARCA) n = KG__PARCA;
        if (g->f.oku(g->f.baglam, a, parca, n)) { g->oku_hata = 1u; return 0u; }
        for (i = 0; i < (uint8_t)n; i++) {
```

bloğunu şununla değiştir:

```c
        uint32_t i;                 /* uint8_t DEGIL: (uint8_t)256 == 0 (B72) */
        if (n > KG__PARCA) n = KG__PARCA;
        if (g->f.oku(g->f.baglam, a, parca, n)) { g->oku_hata = 1u; return 0u; }
        for (i = 0; i < n; i++) {
```

- [ ] **Step 4: Yeşili gör**

Run: `cd uretim && python test_kayit.py`
Expected: `B71: 95/95 kosul gecti`. Önceki 88'e 7 iddia ekleniyor:
- 2 derleme
- 3 BITTI
- T1 ve T2

G ve K bölümleri değişmeden yeşil kalır.

- [ ] **Step 5: Commit**

```bash
git add kod/olcum-karti-a3/kayit_gunluk.h uretim/avr/nor_flas.py uretim/avr/ornek_kayit.c uretim/test_kayit.py
git commit -q -F - <<'EOF'
B72 motor: bos sektor taramasi yalniz baslik, okuma parcasi disaridan

Kurtarma yalniz bas sektorun kuyrugunu 0xFF diye denetliyor; bos flasta
okunan 4352 -> 768 B (gercek bolumde 11.4 MB -> ~97 KB). T1.
kg__ff_mi uint8_t sayaci KG__PARCA=256'da parcayi hic denetlemiyordu
((uint8_t)256 == 0): kirli kuyruk temiz sayilirdi. T2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Bölüm tablosu

**Files:**
- Create: `kod/olcum-karti-a3/partitions.csv`
- Create: `uretim/test_kayit_esp.py` (iskelet + bölüm tablosu iddiaları)
- Modify: `uretim/arayuz-uret.py` (spiffs'i `partitions.csv`'den oku)
- Modify: `uretim/hedef2.py` (yalnız açıklama)

**Interfaces:**
- Produces:
  - `partitions.csv`: `kayit` data `0x40` 0x490000/0xB60000.
  - `test_kayit_esp.py` iskeleti: `ok()`, `BOLUMLER`, `kod()`, `govde()`, `bolum_tablosu() -> list[dict]`.

- [ ] **Step 1: Testi yaz**

`uretim/test_kayit_esp.py`:

```python
# -*- coding: utf-8 -*-
"""B72 — KAYIT MOTORUNUN KARTA BAGLANMASI: bolum tablosu · firmware kaynagi · esitleme.

    python test_kayit_esp.py

Gercek karti DEGIL; tabloyu, firmware KAYNAGINI (yorumlar cikarilarak) ve
PC esitleme istemcisini (sahte kart sunucusuna karsi) sinar. Kartta
olculecekler `tezgah_kayit.py`'de ve tezgah kalemi olarak basiliyor.
Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tezgah import tezgah                          # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


def kod(metin: str) -> str:
    """C/C++ yorumlarini cikar — iddialar KODA baksin, prozaya degil."""
    return re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", metin, flags=re.S))


def govde(kaynak: str, imza: str) -> str:
    """`imza` ile baslayan fonksiyonun { ... } govdesi (yorumsuz kaynakta)."""
    i = kaynak.find(imza)
    if i < 0:
        return ""
    j = kaynak.find("{", i)
    derinlik = 0
    for k in range(j, len(kaynak)):
        if kaynak[k] == "{":
            derinlik += 1
        elif kaynak[k] == "}":
            derinlik -= 1
            if derinlik == 0:
                return kaynak[j:k + 1]
    return ""


def bolum_tablosu(yol: Path) -> list[dict]:
    """ESP-IDF bolum CSV'si -> [{ad, tur, alt, ofset, boyut}]."""
    satirlar = []
    for s in yol.read_text(encoding="utf-8").splitlines():
        s = s.split("#", 1)[0].strip()
        if not s:
            continue
        p = [x.strip() for x in s.split(",")]
        satirlar.append({"ad": p[0], "tur": p[1], "alt": p[2],
                         "ofset": int(p[3], 0), "boyut": int(p[4], 0)})
    return satirlar


def huge_app_csv() -> Path | None:
    taban = Path(os.environ.get("LOCALAPPDATA", "")) / "Arduino15" / "packages" / "esp32"
    return next(iter(sorted((taban / "hardware" / "esp32").glob(
        "*/tools/partitions/huge_app.csv"), reverse=True)), None)


# ── B72.P · bolum tablosu ─────────────────────────────────────────────
def bolum_tablo() -> None:
    print("\n── B72.P  bolum tablosu (partitions.csv)")
    yol = KOD / "partitions.csv"
    ok("B72.P0 cizim klasorunde partitions.csv var (cekirdegin semasini gecersiz kilar)",
       yol.exists())
    if not yol.exists():
        return
    t = {b["ad"]: b for b in bolum_tablosu(yol)}
    eski_yol = huge_app_csv()
    eski = {b["ad"]: b for b in bolum_tablosu(eski_yol)} if eski_yol else {}
    ayni = all(t.get(a) == eski.get(a) for a in ("nvs", "otadata", "app0"))
    ok("B72.P1 nvs / otadata / app0 huge_app ile BIREBIR (WiFi parolalari ve "
       "kalibrasyon NVS'te yerinde kalir)", bool(eski) and ayni,
       f"nvs={t.get('nvs')}")
    sp, esp = t.get("spiffs"), eski.get("spiffs")
    ok("B72.P2 panel bolumu ayni ofsette ve kuculmedi",
       bool(sp and esp) and sp["ofset"] == esp["ofset"] and sp["boyut"] >= esp["boyut"],
       f"{sp}")
    k = t.get("kayit")
    ok("B72.P3 kayit bolumu: data, alt tur 0x40, 4096'nin kati, >= 10 MB",
       bool(k) and k["tur"] == "data" and int(k["alt"], 0) == 0x40
       and k["boyut"] % 4096 == 0 and k["boyut"] >= 10 * 1024 * 1024,
       f"{k} = {k['boyut'] // 4096 if k else 0} sektor")
    sirali = sorted(t.values(), key=lambda b: b["ofset"])
    cakisma = any(a["ofset"] + a["boyut"] > b["ofset"] for a, b in zip(sirali, sirali[1:]))
    son = sirali[-1]
    ok("B72.P4 bolumler cakismiyor, 16 MB'i asmiyor, coredump en sonda",
       not cakisma and son["ofset"] + son["boyut"] <= 16 * 1024 * 1024
       and son["ad"] == "coredump", f"son={son}")
    au = (BURASI / "arayuz-uret.py").read_text(encoding="utf-8")
    ok("B72.P5 arayuz-uret.py panel ofsetini partitions.csv'den okuyor (tek kaynak)",
       "partitions.csv" in au and "huge_app.csv\"), reverse" not in au)


BOLUMLER = [bolum_tablo]


def main() -> int:
    for b in BOLUMLER:
        b()
    tezgah("B72 Kayit firmware + esitleme", [
        ("Flas yazma/silmenin olcume etkisi (spec §11 ilk risk)",
         "tezgah_kayit.py --durma: 50/s ve 5/s'de kuyrukta dusen nokta 0; "
         "loop_azami ve sil_azami_us raporlanir"),
        ("Kayit surerken sifirlama (RTS) -> DEVAM",
         "tezgah_kayit.py --kesinti 20: her sifirlamada durum 2'ye doner, "
         "flasta tek oturum, noktalar bosluksuz, sira tekrar yok"),
        ("Esitlenen dosya == karttaki flas bolumu (bayt bayt)",
         "tezgah_kayit.py --esit: esptool ile okunan bolumdeki her kayit "
         "esitlenen dosyadakiyle ayni"),
        ("Gercek fis cekme (USB + PIL kapali)",
         "elle 5 kez: kurtarma hatasiz, kayit DEVAM ile surer, kayip en fazla "
         "son ~5 s"),
    ])
    print(f"\nB72: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `cd uretim && python test_kayit_esp.py`
Expected: `[!!] B72.P0 …`, `B72: 0/1 kosul gecti`. Dosya olmadığı için bölüm burada durur.

- [ ] **Step 3: `kod/olcum-karti-a3/partitions.csv` yaz**

```
# B72 — olcum karti bolum tablosu (16 MB flas, N16R8).
# Cizim klasorundeki bu dosya Arduino cekirdeginin semasini (FQBN'deki
# huge_app) GECERSIZ KILAR (platform.txt prebuild.3). huge_app FQBN'de
# kalir: 3 MB uygulama ust sinirini o veriyor.
# 🔴 nvs / otadata / app0 huge_app ile BIREBIR: NVS'teki WiFi parolalari
#    ve kalibrasyon (Ayar3) yuklemeden sonra yerinde kalsin.
# Name,   Type, SubType,  Offset,   Size
nvs,      data, nvs,      0x9000,   0x5000
otadata,  data, ota,      0xe000,   0x2000
app0,     app,  ota_0,    0x10000,  0x300000
spiffs,   data, spiffs,   0x310000, 0x180000
kayit,    data, 0x40,     0x490000, 0xB60000
coredump, data, coredump, 0xFF0000, 0x10000
```

- [ ] **Step 4: `arayuz-uret.py`'yi tabloya bağla**

`araclar()` fonksiyonunu şununla değiştir:

```python
def araclar() -> tuple[Path, Path, Path]:
    """mklittlefs ve esptool makineye ozgu, ARANIYOR. Bolum tablosu TEK
    kaynaktan: cizim klasorundeki partitions.csv (B72; cekirdegin
    huge_app.csv'sini gecersiz kilan dosya)."""
    kok = os.environ.get("LOCALAPPDATA")
    if not kok:
        raise SystemExit("LOCALAPPDATA yok — Windows disi ortam")
    taban = Path(kok) / "Arduino15" / "packages" / "esp32"
    mk = next(iter(sorted((taban / "tools" / "mklittlefs").glob("*/mklittlefs.exe"),
                          reverse=True)), None)
    esp = next(iter(sorted((taban / "tools" / "esptool_py").glob("*/esptool.exe"),
                           reverse=True)), None)
    csv = KOK / "kod" / "olcum-karti-a3" / "partitions.csv"
    for ad, y in (("mklittlefs", mk), ("esptool", esp), ("partitions.csv", csv)):
        if y is None or not Path(y).exists():
            raise SystemExit(f"{ad} bulunamadi")
    return mk, esp, csv
```

`bolum()` fonksiyonunun docstring'ini `"""partitions.csv'den spiffs bolumunun (ofset, boyut) degerleri."""`, hata iletisini `"partitions.csv icinde spiffs bolumu yok"` yap. `bolum()` yorum satırlarını atlamalı; ilk satırına `sat = sat.split("#", 1)[0]` ekle. `main()` içindeki `print(f"  ofset   : {hex(ofset)}   (huge_app.csv'den OKUNDU)")` satırını `(partitions.csv'den OKUNDU)` yap.

`uretim/hedef2.py`'de `#   PartitionScheme=huge_app   3 MB uygulama — 473 KB'lik firmware buyuyecek` satırının altına ekle:

```python
#                              B72: YERLESIM cizim klasorundeki
#                              kod/olcum-karti-a3/partitions.csv'den gelir
#                              (kayit bolumu); huge_app yalniz 3 MB ust siniri.
```

- [ ] **Step 5: Yeşili gör**

Run: `cd uretim && python test_kayit_esp.py`
Expected: `B72: 6/6 kosul gecti`.

Run: `cd uretim && python arayuz-uret.py`
Expected: `ofset   : 0x310000   (partitions.csv'den OKUNDU)` ve görüntü boyutu 1 572 864 B.

- [ ] **Step 6: Commit**

```bash
git add kod/olcum-karti-a3/partitions.csv uretim/test_kayit_esp.py uretim/arayuz-uret.py uretim/hedef2.py uretim/_fs.json
git commit -q -F - <<'EOF'
B72 bolum tablosu: 11.4 MB kayit bolumu, panel 1.5 MB, nvs yerinde

partitions.csv cizim klasorunde (cekirdegin huge_app yerlesimini gecersiz
kilar); arayuz-uret.py panel ofsetini buradan okur. test_kayit_esp.py 6/6.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: `kayit_esp.h` — yapıştırıcı, görev, NVS, açılış

**Files:**
- Create: `kod/olcum-karti-a3/kayit_esp.h`
- Modify: `kod/olcum-karti-a3/olcum-karti-a3.ino` (include + `setup()` afiş)
- Modify: `uretim/test_kayit_esp.py` (`bolum_kaynak`)
- Modify (index cerrahisi): `uretim/tasarim3_sabit.py` (`_ESP_DRAM_SON_OLCUM`)

**Interfaces:**
- Produces (C++, `kayit_esp.h`):
  - `bool kayit_kur()`, `KayitDurum kayit_durum_al()`, `uint32_t kayit__unix()`
  - `kayit_ornek(float watt, uint32_t simdi)`, `kayit_duraklama(uint32_t simdi)`
  - `KayitHam kayit_ham` (olcum_al doldurur)
  - `KayitMesaj`, `kayit_mesaj_q`, `KM_*`, `KDR_*`
  - `kayit_kilit`, `kayit_g`, `kayit_dizin`, `kayit_veri_tampon`, `kayit_bolum`
  - sabitler: `KAYIT_FW_SURUM`, `KAYIT_VERI_AZAMI`, `KAYIT_DIZIN_KAP`

- [ ] **Step 1: Testi yaz**

`uretim/test_kayit_esp.py`'de `BOLUMLER = [bolum_tablo]` satırının üstüne ekle:

```python
# ── B72.F · firmware kaynagi ──────────────────────────────────────────
def _oku(ad: str) -> str:
    y = KOD / ad
    return y.read_text(encoding="utf-8", errors="replace") if y.exists() else ""


def bolum_kaynak() -> None:
    print("\n── B72.F  firmware kaynagi (yorumlar cikarilarak)")
    esp_h, ino = _oku("kayit_esp.h"), _oku("olcum-karti-a3.ino")
    esp_k, ino_k = kod(esp_h), kod(ino)
    ok("B72.F1 kayit_esp.h Serial KULLANMIYOR (cekirdek 0'dan basmak aynayi "
       "yarisa sokar; baslik makrodan ONCE dahil)",
       bool(esp_k) and "Serial" not in esp_k)
    i_dahil = ino_k.find('#include "kayit_esp.h"')
    i_makro = ino_k.find("#define Serial CIKIS")
    ok("B72.F2 kayit_esp.h `#define Serial`'dan ONCE dahil; kayit bolumu yoksa "
       "afis KAPALI der",
       0 <= i_dahil < i_makro and "KAPALI" in ino and "kayit_kur()" in ino_k)
    ok("B72.F3 kayit gorevi CEKIRDEK 0'da (olcum cekirdegi flas beklemesin)",
       re.search(r"xTaskCreatePinnedToCore\(\s*kayit_gorevi[^;]*,\s*0\s*\)", esp_k)
       is not None)
    g = govde(esp_k, "static void kayit_gorevi(")
    ok("B72.F4 gorev butun ky_/kg_ islerini kilit ALTINDA yapiyor",
       "xSemaphoreTake(kayit_kilit" in g and "xSemaphoreGive(kayit_kilit" in g
       and g.find("xSemaphoreTake(kayit_kilit") < g.find("ky_nokta("))
    a = govde(esp_k, "static void kayit__ac(")
    ok("B72.F5 acilista onay ve sira tabani NVS'ten; kg_ac(g, taban, onay)",
       re.search(r"kg_ac\(\s*&kayit_g\s*,\s*taban\s*,\s*onay\s*\)", a) is not None
       and 'getUInt("onay"' in a and 'getUInt("taban"' in a)
    i_parca = esp_k.find("#define KG__PARCA")
    i_motor = esp_k.find('#include "kayit_oturum.h"')
    ok("B72.F6 ESP32 okuma parcasi (256) motordan ONCE tanimli",
       0 <= i_parca < i_motor and "256u" in esp_k[i_parca:i_parca + 40])
```

`BOLUMLER`'i `[bolum_tablo, bolum_kaynak]` yap.

- [ ] **Step 2: Kırmızıyı gör**

Run: `cd uretim && python test_kayit_esp.py`
Expected: F1–F6 kırmızı (`kayit_esp.h` yok).

- [ ] **Step 3: `kod/olcum-karti-a3/kayit_esp.h` yaz**

```cpp
#ifndef KAYIT_ESP_H
#define KAYIT_ESP_H
/*
 * B72 — KAYIT MOTORUNUN KARTA BAGLANMASI (alt proje 1A-2).
 *
 * Motor kayit_*.h'de (B71; AVR emulatorunde emule NOR + elektrik kesme ile
 * sinaniyor). Bu dosya YALNIZ ESP32 yapistiricisi: flas bolumu
 * (esp_partition), NVS, cekirdek 0'daki kayit gorevi, kuyruklar, kilit.
 * Tasarim: tasarim/2026-09-29-yazilim-sistemi.md §5.
 * Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md.
 *
 * 🔴 BURADA `Serial` YOK. Bu baslik `#define Serial CIKIS`'ten ONCE dahil
 *    ediliyor; burada basilan satir web aynasini (SSE) atlardi, ustelik
 *    cekirdek 0'dan basmak aynanin satir bolucusunu yarisa sokardi (B28:
 *    tek yazar). Butun basma .ino'da, cekirdek 1'de.
 *
 * CEKIRDEKLER:
 *   cekirdek 1 (loop)   kayit_ornek / kayit_duraklama: noktaci, nokta KUYRUGA
 *   cekirdek 0 (kayit)  kayit_gorevi: kuyruk -> ky_nokta, komutlar, NTP, NVS
 *   cekirdek 0 (ag)     /kayit/* uclari: kg_oku
 * Butun kg_* / ky_* cagrilari `kayit_kilit` ALTINDA (1A-1 son inceleme).
 */
#include <Arduino.h>
#include <Preferences.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include "esp_partition.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "ag.h"

#define KG__PARCA 256u            /* flasi 256'lik parcalarla oku (AVR testinde 32) */
#include "kayit_nokta.h"
#include "kayit_oturum.h"

#define KAYIT_FW_SURUM    "A3-B72"
#define KAYIT_ALT_TUR     0x40      /* partitions.csv: kayit, data, 0x40 */
#define KAYIT_DIZIN_KAP   64u
#define KAYIT_KUYRUK      256u      /* nokta; 50/s'de ~5 s flas beklemesini yutar */
#define KAYIT_VERI_AZAMI  8192u     /* /kayit/veri tek yanit tavani (dahili RAM) */
#define KAYIT_ONAY_ARALIK 16u       /* NVS'e onay: en az bu kadar sira ilerleyince */
#define KAYIT_ONAY_MS     30000u    /* ... ya da bu kadar sure gecince */

/* G satirindaki durum kodlari */
#define KDR_TARIYOR  0u
#define KDR_BOS      1u
#define KDR_KAYIT    2u
#define KDR_DOLU     3u
#define KDR_BEKLIYOR 4u   /* acik oturum var, yer yok: gecerli onay gelince DEVAM */
#define KDR_HATA     5u

/* cekirdek 1 -> 0 istekleri */
#define KM_BASLAT  1u
#define KM_DURDUR  2u
#define KM_ONAY    3u
#define KM_BICIMLE 4u

typedef struct {
    uint8_t    tur;
    uint32_t   deger;
    KayitBasla basla;
} KayitMesaj;

typedef struct {
    uint8_t  durum;
    uint32_t oturum, nokta_sira, sonraki_sira, onay;
    uint16_t doluluk_binde, onaysiz_binde;
    uint32_t dusen, bozuk, silinen, sil_adet;
    uint32_t yaz_azami_us, sil_azami_us, tarama_ms;
    uint32_t acilis, hiz_ms, nesil;
    int32_t  son_hata;
} KayitDurum;

/* olcum_al'in son HAM ornegi — ikisi de cekirdek 1: olcum_al yazar, loop okur */
typedef struct {
    int16_t ham_v, ham_i;
    uint8_t hata, v_doydu, menzil;
} KayitHam;
static KayitHam kayit_ham;

static const esp_partition_t *kayit_bolum = nullptr;
static KayitSektor *kayit_sektor = nullptr;
static KayitOzet   *kayit_dizin = nullptr;
static uint8_t     *kayit_veri_tampon = nullptr;
static KayitGunluk  kayit_g;
static KayitYazici  kayit_y;
static SemaphoreHandle_t kayit_kilit = nullptr;
static QueueHandle_t kayit_nokta_q = nullptr;
static QueueHandle_t kayit_mesaj_q = nullptr;
static TaskHandle_t  kayit_gorev_kolu = nullptr;
static Preferences   kayit_nvs;
static KayitDurum    kayit_durum = {};
static portMUX_TYPE  kayit_mux = portMUX_INITIALIZER_UNLOCKED;

static volatile uint32_t kayit_kuyruk_dusen = 0;   /* cekirdek 1 yazar */
static volatile uint32_t kayit_yaz_azami_us = 0;
static volatile uint32_t kayit_sil_azami_us = 0;
static volatile uint32_t kayit_sil_adet = 0;

static uint8_t  kayit_hazir = 0, kayit_hata = 0;
static uint32_t kayit_acilis = 0, kayit_tarama_ms = 0;
static int32_t  kayit_son_hata = 0;
static uint8_t  kayit_devam_bekliyor = 0;
static uint32_t kayit_onay_nvs = 0, kayit_onay_nvs_ms = 0;
static uint8_t  kayit_saat_ntp = 0, kayit_saat_gecerli = 0;

/* ─────────────────────────────── flas: esp_partition */
static int kayit_f_oku(void *b, uint32_t a, void *h, uint32_t n)
{
    (void)b;
    return esp_partition_read(kayit_bolum, a, h, n) == ESP_OK ? 0 : -1;
}

static int kayit_f_yaz(void *b, uint32_t a, const void *k, uint32_t n)
{
    uint32_t t = micros();
    esp_err_t e;
    (void)b;
    e = esp_partition_write(kayit_bolum, a, k, n);
    t = micros() - t;
    if (t > kayit_yaz_azami_us) kayit_yaz_azami_us = t;
    return e == ESP_OK ? 0 : -1;
}

static int kayit_f_sil(void *b, uint32_t a)
{
    uint32_t t = micros();
    esp_err_t e;
    (void)b;
    e = esp_partition_erase_range(kayit_bolum, a, KAYIT_SEKTOR);
    t = micros() - t;
    if (t > kayit_sil_azami_us) kayit_sil_azami_us = t;
    kayit_sil_adet = kayit_sil_adet + 1u;
    return e == ESP_OK ? 0 : -1;
}

/* ─────────────────────────────── zaman */
static uint32_t kayit__unix(void)
{
    time_t t = time(nullptr);
    return (t > (time_t)1700000000) ? (uint32_t)t : 0u;   /* 0 = bilinmiyor */
}

/* ─────────────────────────────── durum (cekirdek 0 yazar, herkes okur) */
static KayitDurum kayit_durum_al(void)
{
    KayitDurum t;
    portENTER_CRITICAL(&kayit_mux);
    t = kayit_durum;
    portEXIT_CRITICAL(&kayit_mux);
    return t;
}

/* KILIT ALTINDA cagrilir */
static void kayit__durum_guncelle(void)
{
    KayitDurum t;
    memset(&t, 0, sizeof(t));
    if (!kayit_hazir) t.durum = kayit_hata ? KDR_HATA : KDR_TARIYOR;
    else if (kayit_y.oturum) t.durum = KDR_KAYIT;
    else if (kayit_devam_bekliyor) t.durum = KDR_BEKLIYOR;
    else if (kayit_g.dolu) t.durum = KDR_DOLU;
    else t.durum = KDR_BOS;
    t.oturum = kayit_y.oturum;
    t.nokta_sira = kayit_y.nokta_sira + kayit_y.yuk_nokta;
    t.sonraki_sira = kayit_g.sonraki_sira;
    t.onay = kayit_g.onay;
    if (kayit_hazir) {
        t.doluluk_binde = kg_binde(&kayit_g, kg_kullanilan(&kayit_g));
        t.onaysiz_binde = kg_binde(&kayit_g, kg_onaysiz(&kayit_g));
    }
    t.dusen = kayit_y.dusen + kayit_kuyruk_dusen;
    t.bozuk = kayit_g.bozuk;
    t.silinen = kayit_g.silinen_sektor;
    t.sil_adet = kayit_sil_adet;
    t.yaz_azami_us = kayit_yaz_azami_us;
    t.sil_azami_us = kayit_sil_azami_us;
    t.tarama_ms = kayit_tarama_ms;
    t.acilis = kayit_acilis;
    t.hiz_ms = kayit_y.oturum ? kayit_y.basla.hiz_ms : 0u;
    t.son_hata = kayit_son_hata;
    portENTER_CRITICAL(&kayit_mux);
    t.nesil = kayit_durum.nesil
            + ((t.durum != kayit_durum.durum || t.oturum != kayit_durum.oturum) ? 1u : 0u);
    kayit_durum = t;
    portEXIT_CRITICAL(&kayit_mux);
}

/* ─────────────────────────────── NVS'e onay (kisitli yazim) */
static void kayit__onay_kaydet(uint8_t zorla)
{
    uint32_t o = kayit_g.onay;
    if (o == kayit_onay_nvs) return;
    if (zorla || o - kayit_onay_nvs >= KAYIT_ONAY_ARALIK
        || millis() - kayit_onay_nvs_ms >= KAYIT_ONAY_MS) {
        kayit_nvs.putUInt("onay", o);
        kayit_onay_nvs = o;
        kayit_onay_nvs_ms = millis();
    }
}

/* ─────────────────────────────── acik oturumu surdur (KILIT ALTINDA) */
static void kayit__devam_dene(void)
{
    const KayitOzet *o = kg_acik_oturum(&kayit_g);
    KayitBasla b;
    KayitDevam d;
    uint32_t id;
    int r;
    if (!o || o->tur != KAYIT_OTURUM_OLCUM) return;
    id = o->id;
    if (kg_basla_oku(&kayit_g, o->basla_adres, id, &b)) return;
    d.acilis = kayit_acilis;
    d.unix_s = kayit__unix();
    d.kart_ms = millis();
    d.nokta_sira = 0u;
    r = ky_devam(&kayit_y, id, &b, o->nokta_sonraki, &d);
    /* DOLU: kafa sektoru temizse ky__dolu BITIR(DOLU) yazip oturumu kapatti.
       Kapatamadiysa (kafa yarim — 1A-1 bulgu 2) oturum hala ACIK: onay
       gelince yeniden denenecek. */
    const KayitOzet *h = kg_acik_oturum(&kayit_g);
    kayit_devam_bekliyor = (r == KG_DOLU && h && h->id == id) ? 1u : 0u;
    if (r) kayit_son_hata = r;
}

/* ─────────────────────────────── acilis (gorevde, KILIT ALTINDA) */
static void kayit__ac(void)
{
    static const KayitFlas f = { kayit_f_oku, kayit_f_yaz, kayit_f_sil, nullptr };
    uint32_t taban, onay, t0;
    uint8_t deneme;
    int r = KG_HATA;
    kayit_nvs.begin("kayit", false);
    kayit_acilis = kayit_nvs.getUInt("acilis", 0u) + 1u;
    kayit_nvs.putUInt("acilis", kayit_acilis);
    taban = kayit_nvs.getUInt("taban", 0u);
    onay = kayit_nvs.getUInt("onay", 0u);
    kayit_onay_nvs = onay;
    kayit_onay_nvs_ms = millis();
    kg_kur(&kayit_g, &f, kayit_bolum->size / KAYIT_SEKTOR,
           kayit_sektor, kayit_dizin, (uint16_t)KAYIT_DIZIN_KAP);
    ky_kur(&kayit_y, &kayit_g);
    t0 = millis();
    for (deneme = 0; deneme < 3u && r != KG_TAMAM; deneme++) r = kg_ac(&kayit_g, taban, onay);
    kayit_tarama_ms = millis() - t0;
    if (r != KG_TAMAM) {
        kayit_hata = 1u;
        kayit_son_hata = r;
        return;
    }
    kayit_hazir = 1u;
    kayit__devam_dene();
}

/* ─────────────────────────────── istekler (KILIT ALTINDA) */
static void kayit__mesaj(const KayitMesaj *m)
{
    int32_t r = 0;
    switch (m->tur) {
    case KM_BASLAT: {
        KayitBasla b = m->basla;
        if (!b.unix_s) b.unix_s = kayit__unix();
        kayit_devam_bekliyor = 0u;
        r = ky_baslat(&kayit_y, &b);
        break;
    }
    case KM_DURDUR:
        r = ky_bitir(&kayit_y, KB_SEBEP_KULLANICI);
        break;
    case KM_ONAY:
        r = kg_onayla(&kayit_g, m->deger);
        if (r == KG_TAMAM && kayit_devam_bekliyor) kayit__devam_dene();
        break;
    case KM_BICIMLE:
        if (kayit_y.oturum) (void)ky_bitir(&kayit_y, KB_SEBEP_KULLANICI);
        /* ONCE taban: bicimleme yarida kesilse de numara tekrar verilmez */
        kayit_nvs.putUInt("taban", kayit_g.sonraki_sira);
        r = kg_bicimle(&kayit_g);
        kayit__onay_kaydet(1u);
        kayit_devam_bekliyor = 0u;
        break;
    default:
        break;
    }
    kayit_son_hata = (r < 0 && r != KG_YOK) ? r : 0;   /* oturumsuz Gd hata degil */
}

/* ─────────────────────────────── NTP (gorevde) */
static void kayit__saat(void)
{
    if (!kayit_saat_ntp && ag_durum.kip == AG_STA) {
        configTime(0, 0, "pool.ntp.org", "time.google.com");
        kayit_saat_ntp = 1u;
    }
    if (!kayit_saat_gecerli && kayit__unix()) {
        kayit_saat_gecerli = 1u;
        if (kayit_y.oturum) {
            KayitSaat z;
            z.unix_s = kayit__unix();
            z.kart_ms = millis();
            z.acilis = kayit_acilis;
            (void)ky_saat(&kayit_y, &z);
        }
    }
}

/* ─────────────────────────────── gorev (cekirdek 0) */
static void kayit_gorevi(void *)
{
    KayitNokta p;
    KayitMesaj m;
    xSemaphoreTake(kayit_kilit, portMAX_DELAY);
    kayit__ac();
    kayit__durum_guncelle();
    xSemaphoreGive(kayit_kilit);
    for (;;) {
        bool var = xQueueReceive(kayit_nokta_q, &p, pdMS_TO_TICKS(100)) == pdTRUE;
        xSemaphoreTake(kayit_kilit, portMAX_DELAY);
        if (kayit_hazir) {
            while (var) {
                int r = ky_nokta(&kayit_y, &p, millis());
                if (r && r != KG_YOK) kayit_son_hata = r;
                var = xQueueReceive(kayit_nokta_q, &p, 0) == pdTRUE;
            }
            while (xQueueReceive(kayit_mesaj_q, &m, 0) == pdTRUE) kayit__mesaj(&m);
            (void)ky_zaman(&kayit_y, millis());
            kayit__saat();
            kayit__onay_kaydet(0u);
        }
        kayit__durum_guncelle();
        xSemaphoreGive(kayit_kilit);
    }
}

/* ─────────────────────────────── kurulum (setup, cekirdek 1) */
static bool kayit_kur(void)
{
    uint32_t adet;
    kayit_bolum = esp_partition_find_first(ESP_PARTITION_TYPE_DATA,
                                           (esp_partition_subtype_t)KAYIT_ALT_TUR, "kayit");
    if (!kayit_bolum) return false;
    adet = kayit_bolum->size / KAYIT_SEKTOR;
    kayit_sektor = (KayitSektor *)heap_caps_malloc(adet * sizeof(KayitSektor), MALLOC_CAP_SPIRAM);
    kayit_dizin = (KayitOzet *)heap_caps_malloc(KAYIT_DIZIN_KAP * sizeof(KayitOzet),
                                                 MALLOC_CAP_SPIRAM);
    kayit_veri_tampon = (uint8_t *)heap_caps_malloc(KAYIT_VERI_AZAMI,
                                                     MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    kayit_kilit = xSemaphoreCreateMutex();
    kayit_nokta_q = xQueueCreate(KAYIT_KUYRUK, sizeof(KayitNokta));
    kayit_mesaj_q = xQueueCreate(4, sizeof(KayitMesaj));
    if (!kayit_sektor || !kayit_dizin || !kayit_veri_tampon || !kayit_kilit
        || !kayit_nokta_q || !kayit_mesaj_q) {
        kayit_bolum = nullptr;
        return false;
    }
    xTaskCreatePinnedToCore(kayit_gorevi, "kayit", 8192, nullptr, 1, &kayit_gorev_kolu, 0);
    return true;
}

/* ─────────────────────────────── noktaci (cekirdek 1) */
static KayitNoktaci kayit_kn;
static uint32_t kayit_kn_nesil = 0xFFFFFFFFu;
static uint8_t  kayit_kn_aktif = 0;

static void kayit__gonder(const KayitNokta *c)
{
    if (!kayit_nokta_q || xQueueSend(kayit_nokta_q, c, 0) != pdTRUE) {
        kn_kayip(&kayit_kn);                           /* sonraki nokta isaretli */
        kayit_kuyruk_dusen = kayit_kuyruk_dusen + 1u;
    }
}

static void kayit__nesil(uint32_t simdi, uint8_t menzil)
{
    KayitDurum d = kayit_durum_al();
    if (d.nesil == kayit_kn_nesil) return;
    kayit_kn_nesil = d.nesil;
    kayit_kn_aktif = (d.durum == KDR_KAYIT && d.hiz_ms) ? 1u : 0u;
    if (kayit_kn_aktif) kn_baslat(&kayit_kn, d.hiz_ms, simdi, menzil);
}

/* Her ornekte (loop, olcum_al'dan sonra). */
static void kayit_ornek(float watt, uint32_t simdi)
{
    KayitNokta c;
    uint8_t hata = kayit_ham.hata;
    kayit__nesil(simdi, kayit_ham.menzil);
    if (!kayit_kn_aktif) return;
    if (!isfinite(watt)) hata |= (uint8_t)(KN_HATA_V | KN_HATA_I);   /* NaN int64'e cevrilemez */
    if (kn_ornek(&kayit_kn, simdi, kayit_ham.menzil, kayit_ham.ham_v, kayit_ham.ham_i,
                 watt, hata, kayit_ham.v_doydu, &c))
        kayit__gonder(&c);
}

/* Skop ADS'i sustururken (loop'un erken donusu). */
static void kayit_duraklama(uint32_t simdi)
{
    KayitNokta c;
    kayit__nesil(simdi, kayit_ham.menzil);
    if (kayit_kn_aktif && kn_zaman(&kayit_kn, simdi, &c)) kayit__gonder(&c);
}

#endif /* KAYIT_ESP_H */
```

- [ ] **Step 4: `.ino`'ya bağla (include + afiş)**

`#include "ag.h"         // B22.4 — WiFi durum makinesi` satırının altına ekle:

```cpp
#include "kayit_esp.h"  // B72 — kayit motorunun ESP32 yapistiricisi (Serial KULLANMAZ)
```

`setup()`'ta `Serial.println(F("Cikis: D <volt> <amper> <watt> <joule> <wh> <ms> "` satırının hemen **üstüne** ekle:

```cpp
  // ── B72: KAYIT — bolum ve bellek burada; flas TARAMASI cekirdek 0'daki
  //    gorevde (acilisi bloklamasin). Durum `G?` ile.
  Serial.print(F("Kayit: "));
  if (kayit_kur()) {
    Serial.print(kayit_bolum->size / 1024u);
    Serial.print(F(" KB, "));
    Serial.print(kayit_bolum->size / KAYIT_SEKTOR);
    Serial.println(F(" sektor — tarama gorevde, `G?` durum"));
  } else {
    Serial.println(F("KAPALI — 'kayit' bolumu ya da bellek yok (partitions.csv ile tam yukleme)"));
  }
```

- [ ] **Step 5: Kaynak testi ve derleme**

Run: `cd uretim && python test_kayit_esp.py`
Expected: `B72: 12/12 kosul gecti`.

Run: `cd uretim && python test_firmware3.py`
Expected:
- Derleme **UYARISIZ**, RAM payı < %25.
- **Tek kırmızı:** `Yedek DRAM sabiti olculen degerle AYNI`. Çıktı yeni değeri söyler.

Yeni değeri `uretim/tasarim3_sabit.py`'deki `_ESP_DRAM_SON_OLCUM` sabitine yaz. Bu dosyada kullanıcının bekleyen işi var: **aynı düzenlemeyi hem çalışma dizinine hem HEAD sürümüne** uygula, index'e HEAD sürümünü koy (Global Constraints). Sonra `test_firmware3.py`'yi yeniden koştur.
Expected: hepsi yeşil.

- [ ] **Step 6: Commit**

```bash
git add kod/olcum-karti-a3/kayit_esp.h kod/olcum-karti-a3/olcum-karti-a3.ino uretim/test_kayit_esp.py uretim/_firmware.json
# tasarim3_sabit.py: index cerrahisi (HEAD + _ESP_DRAM_SON_OLCUM)
git commit -q -F - <<'EOF'
B72 kayit_esp.h: flas bolumu, NVS, cekirdek 0 gorevi, acilis afisi

Tarama gorevde (setup beklemez); onay ve sira tabani NVS'ten; bellek
doluyken acik oturum onay gelince surdurulur. Serial yok (makrodan once).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Örnek beslemesi, `G` komutu, `G` satırı

**Files:**
- Modify: `kod/olcum-karti-a3/olcum-karti-a3.ino`
- Modify: `uretim/test_kayit_esp.py` (`bolum_kaynak`'a F7–F10)

**Interfaces:**
- Consumes: `kayit_ham`, `kayit_ornek`, `kayit_duraklama`, `kayit_durum_al`, `kayit__unix`, `KayitMesaj`, `kayit_mesaj_q` (Task 3)
- Produces: `kayit_komut(const char*)`, `kayit_durum_bas(bool)`, `kayit_basla_doldur(KayitBasla*, uint32_t)` (`.ino`)

- [ ] **Step 1: Testi yaz**

`bolum_kaynak`'ın sonuna ekle:

```python
    oa = govde(ino_k, "Okuma3 olcum_al(")
    lp = govde(ino_k, "void loop(")
    ok("B72.F7 olcum_al HAM kodu, hata bitlerini ve menzili kayit_ham'a veriyor",
       all(x in oa for x in ("kayit_ham.ham_v = ham_v", "kayit_ham.ham_i = ham_i",
                             "kayit_ham.hata = ads_hata", "kayit_ham.menzil")))
    skop = lp[lp.find("if (skop_is != SKOP_IS_YOK)"):]
    ok("B72.F8 loop noktaciyi besliyor; skop duraklamasinda kayit_duraklama; "
       "G satiri yalniz loop'ta (cekirdek 1)",
       "kayit_ornek(o.watt" in lp and "kayit_duraklama(" in skop[:skop.find("return;")]
       and "kayit_durum_bas(false)" in lp and '"G %u' in ino_k)
    km = govde(esp_k, "static void kayit__mesaj(")
    ok("B72.F9 bicimlemede sira tabani NVS'e kg_bicimle'den ONCE",
       0 <= km.find('putUInt("taban"') < km.find("kg_bicimle("))
    ok("B72.F10 `G` komutu tanimli ve yardimda; hiz listesi dar",
       "case 'G': kayit_komut(s)" in ino_k and "Gb<ms>" in ino
       and "h == 60000" in ino_k)
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `cd uretim && python test_kayit_esp.py`
Expected: F7–F10 kırmızı.

- [ ] **Step 3: `.ino` değişiklikleri**

(a) `olcum_al()`'da:

```cpp
  int16_t ham_v = ads_oku(ADS_GERILIM);
  int16_t ham_i = ads_oku(ADS_AKIM);
  uint32_t t3 = micros();
```

bloğunun hemen altına ekle:

```cpp
  /* B72: kayit noktacisi HAM kodu istiyor (tasarim §7: yeniden kalibrasyon).
     Menzil BU ornegin menzili — menzil_gozet asagida degistirebilir. */
  kayit_ham.ham_v = ham_v;
  kayit_ham.ham_i = ham_i;
  kayit_ham.hata = ads_hata;
  kayit_ham.v_doydu = gerilim_doydu(ham_v, etkin_kanal()) ? 1u : 0u;
  kayit_ham.menzil = ayar.menzil;
```

(b) `loop()`'ta `  skop_dokum_ilerle();       // B40: skop dokumu, TX'te yer oldugu kadar` satırının altına ekle:

```cpp
  kayit_durum_bas(false);    // B72: G satiri — yalniz cekirdek 1 basar
```

Skop dalında `    if (kuplaj_aktif) kuplaj_patlat();       /* B44 deneyi — yalnizca `tK` */` satırının altına (`return;`'den önce) ekle:

```cpp
    kayit_duraklama(millis());   /* B72: ornek gelmeyen aralik noktayi kapatir */
```

`  Okuma3 o = olcum_al();` satırının altına ekle:

```cpp
  kayit_ornek(o.watt, millis());   // B72: noktaci (cekirdek 1)
```

(c) `void komut_sayfa() {` satırının hemen **üstüne** ekle:

```cpp
// ═════════════════════════════════════════════════ B72 — KAYIT ════════
// Basma ve komut burada (cekirdek 1, `Serial` aynasi); gorev kayit_esp.h'de.
static bool kayit__hiz_gecerli(long h) {
  return h == 20 || h == 100 || h == 200 || h == 1000 || h == 10000 || h == 60000;
}

static void kayit_basla_doldur(KayitBasla *b, uint32_t hiz) {
  memset(b, 0, sizeof(*b));
  b->oturum_turu = KAYIT_OTURUM_OLCUM;
  b->kal_bicim = KAYIT_KAL_BICIM;
  b->hiz_ms = hiz;
  b->unix_s = kayit__unix();
  b->kart_ms = millis();
  b->acilis = kayit_durum_al().acilis;
  memcpy(b->surum, KAYIT_FW_SURUM, sizeof(KAYIT_FW_SURUM) - 1u);
  b->kal.normal.n = ayar.normal.n;
  b->kal.normal.pga = ayar.normal.pga;
  b->kal.normal.kazanc = ayar.normal.kazanc;
  b->kal.normal.sifir_ham = ayar.normal.sifir_ham;
  b->kal.normal.tau = ayar.normal.tau;
  b->kal.yuksek.n = ayar.yuksek.n;
  b->kal.yuksek.pga = ayar.yuksek.pga;
  b->kal.yuksek.kazanc = ayar.yuksek.kazanc;
  b->kal.yuksek.sifir_ham = ayar.yuksek.sifir_ham;
  b->kal.yuksek.tau = ayar.yuksek.tau;
  b->kal.i_ofset = ayar.i_ofset;
  b->kal.i_pga = ayar.i_pga;
  b->kal.sont_ohm = ayar.sont_ohm;
  b->kal.i_duzeltme = ayar.i_duzeltme;
  b->kal.sebeke_hz = ayar.sebeke_hz;
  b->kal.faz_kal_us[0] = ayar.faz_kal_us[0];
  b->kal.faz_kal_us[1] = ayar.faz_kal_us[1];
}

/* G <durum> <oturum> <nokta> <sonraki> <onay> <doluluk%o> <onaysiz%o> <dusen>
     <yaz_azami_us> <sil_azami_us> <sil_adet> <tarama_ms> <son_hata>
   Kayit surerken saniyede bir, durum degisince HEMEN; `G?` ile istenince. */
static void kayit_durum_bas(bool zorla) {
  static uint32_t son_ms = 0, son_nesil = 0xFFFFFFFFu;
  if (!kayit_bolum) {
    if (zorla) Serial.println(F("! G: kayit bolumu yok (partitions.csv ile tam yukleme)"));
    return;
  }
  uint32_t ms = millis();
  KayitDurum d = kayit_durum_al();
  bool periyot = d.durum == KDR_KAYIT && (ms - son_ms) >= 1000u;
  if (!zorla && d.nesil == son_nesil && !periyot) return;
  son_ms = ms;
  son_nesil = d.nesil;
  char t[176];
  snprintf(t, sizeof(t), "G %u %lu %lu %lu %lu %u %u %lu %lu %lu %lu %lu %ld",
           (unsigned)d.durum, (unsigned long)d.oturum, (unsigned long)d.nokta_sira,
           (unsigned long)d.sonraki_sira, (unsigned long)d.onay,
           (unsigned)d.doluluk_binde, (unsigned)d.onaysiz_binde,
           (unsigned long)d.dusen, (unsigned long)d.yaz_azami_us,
           (unsigned long)d.sil_azami_us, (unsigned long)d.sil_adet,
           (unsigned long)d.tarama_ms, (long)d.son_hata);
  Serial.println(t);
}

static void kayit_komut(const char *s) {
  KayitMesaj m;
  if (!kayit_bolum) {
    Serial.println(F("! G: kayit bolumu yok (partitions.csv ile tam yukleme)"));
    return;
  }
  memset(&m, 0, sizeof(m));
  switch (s[1]) {
    case 0:
    case '?':
      kayit_durum_bas(true);
      return;
    case 'b': {
      long h = atol(s + 2);
      if (!kayit__hiz_gecerli(h)) {
        Serial.println(F("! G: hiz 20/100/200/1000/10000/60000 ms olmali"));
        return;
      }
      m.tur = KM_BASLAT;
      kayit_basla_doldur(&m.basla, (uint32_t)h);
      break;
    }
    case 'd': m.tur = KM_DURDUR; break;
    case 'o': m.tur = KM_ONAY; m.deger = strtoul(s + 2, nullptr, 10); break;
    case 'F':
      if (s[2] != '!') {
        Serial.println(F("! G: butun kayitlari silmek icin `GF!` yaz"));
        return;
      }
      m.tur = KM_BICIMLE;
      break;
    default:
      Serial.println(F("! G: alt komut b<ms> d ? o<sira> F!"));
      return;
  }
  if (xQueueSend(kayit_mesaj_q, &m, 0) == pdTRUE)
    Serial.println(F("* G istek kuyrukta — sonuc G satirinda"));
  else
    Serial.println(F("! G: istek kuyrugu dolu"));
}
```

(d) `komut_calistir`'da `    case 'e':` satırının hemen üstüne ekle:

```cpp
    case 'G': kayit_komut(s); break;   // B72 — kayit
```

(e) `yardim()`'da son satırın (`  tl<0-4095> esik …`) altına ekle:

```cpp
  Serial.println(F("  Gb<ms> kayit baslat (20/100/200/1000/10000/60000)  Gd durdur  G? durum"));
  Serial.println(F("  Go<sira> esitlenen kayitlari onayla   GF! BUTUN kayitlari sil"));
```

- [ ] **Step 4: Yeşili gör, derle**

Run: `cd uretim && python test_kayit_esp.py`
Expected: `B72: 16/16 kosul gecti`.

Run: `cd uretim && python test_firmware3.py`
Expected: uyarısız, RAM < %25. DRAM sabiti değiştiyse Task 3 Step 5'teki gibi güncelle ve yeniden koştur. `Komut harfleri` listesinde `G` görünür.

- [ ] **Step 5: Commit**

```bash
git add kod/olcum-karti-a3/olcum-karti-a3.ino uretim/test_kayit_esp.py uretim/_firmware.json
# tasarim3_sabit.py degistiyse: index cerrahisi
git commit -q -F - <<'EOF'
B72 ornek beslemesi, G komutu ve G durum satiri

olcum_al ham kodu kayit_ham'a verir; loop noktaciyi besler, skop
duraklamasinda noktayi kapatir; G satiri yalniz cekirdek 1'de basilir.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: `/kayit/liste` ve `/kayit/veri`

**Files:**
- Modify: `kod/olcum-karti-a3/olcum-karti-a3.ino`
- Modify: `uretim/test_kayit_esp.py` (F11–F12)

**Interfaces:**
- Produces:
  - `GET /kayit/liste` → JSON `{surum, durum, sektor, sektor_bayt, sonraki, onay, doluluk_binde, onaysiz_binde, aktif, acilis, unix, oturumlar:[{id,tur,hiz_ms,unix_s,kart_ms,acilis,ilk,son,nokta,durum,basi_silindi}]}`
  - `GET /kayit/veri?sira=N&bayt=M` → `application/octet-stream`, başlıklar `X-Ilk-Sira`, `X-Son-Sira`, `X-Sonraki-Sira`, `X-Onay`

- [ ] **Step 1: Testi yaz**

`bolum_kaynak`'ın sonuna ekle:

```python
    vs = govde(ino_k, "void kayit_veri_sayfa(")
    ls = govde(ino_k, "void kayit_liste_sayfa(")
    ok("B72.F11 /kayit/liste ve /kayit/veri kayitli; ikisi de Host denetimli",
       'sunucu.on("/kayit/liste"' in ino_k and 'sunucu.on("/kayit/veri"' in ino_k
       and "host_gecerli()" in vs and "host_gecerli()" in ls)
    ok("B72.F12 /kayit/veri kg_oku'yu KILIT altinda, tavanla (8192) cagiriyor",
       vs.find("xSemaphoreTake(kayit_kilit") < vs.find("kg_oku(")
       < vs.find("xSemaphoreGive(kayit_kilit") and "KAYIT_VERI_AZAMI" in vs
       and "X-Ilk-Sira" in ino)
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `cd uretim && python test_kayit_esp.py`
Expected: F11, F12 kırmızı.

- [ ] **Step 3: Uçları yaz**

`void komut_sayfa() {` satırının üstüne, Task 4'teki B72 bloğunun altına ekle:

```cpp
void kayit_liste_sayfa() {
  if (!host_gecerli()) { sunucu.send(403, "text/plain", "Host reddedildi"); return; }
  if (!kayit_bolum) { sunucu.send(503, "text/plain", "kayit bolumu yok"); return; }
  static KayitOzet oz[KAYIT_DIZIN_KAP];     /* yalniz ag gorevi (sirali istekler) */
  uint16_t n;
  xSemaphoreTake(kayit_kilit, portMAX_DELAY);
  n = kayit_g.dizin_adet;
  if (n > KAYIT_DIZIN_KAP) n = KAYIT_DIZIN_KAP;
  if (n) memcpy(oz, kayit_dizin, (size_t)n * sizeof(KayitOzet));
  xSemaphoreGive(kayit_kilit);
  KayitDurum d = kayit_durum_al();
  char t[240];
  sunucu.setContentLength(CONTENT_LENGTH_UNKNOWN);
  sunucu.send(200, "application/json", "");
  snprintf(t, sizeof(t),
           "{\"surum\":%u,\"durum\":%u,\"sektor\":%lu,\"sektor_bayt\":%lu,"
           "\"sonraki\":%lu,\"onay\":%lu,\"doluluk_binde\":%u,\"onaysiz_binde\":%u,"
           "\"aktif\":%lu,\"acilis\":%lu,\"unix\":%lu,\"oturumlar\":[",
           (unsigned)KAYIT_SURUM, (unsigned)d.durum,
           (unsigned long)(kayit_bolum->size / KAYIT_SEKTOR), (unsigned long)KAYIT_SEKTOR,
           (unsigned long)d.sonraki_sira, (unsigned long)d.onay,
           (unsigned)d.doluluk_binde, (unsigned)d.onaysiz_binde,
           (unsigned long)d.oturum, (unsigned long)d.acilis, (unsigned long)kayit__unix());
  sunucu.sendContent(t);
  for (uint16_t i = 0; i < n; i++) {
    const KayitOzet *o = &oz[i];
    snprintf(t, sizeof(t),
             "%s{\"id\":%lu,\"tur\":%u,\"hiz_ms\":%lu,\"unix_s\":%lu,\"kart_ms\":%lu,"
             "\"acilis\":%lu,\"ilk\":%lu,\"son\":%lu,\"nokta\":%lu,\"durum\":%u,"
             "\"basi_silindi\":%u}",
             i ? "," : "", (unsigned long)o->id, (unsigned)o->tur, (unsigned long)o->hiz_ms,
             (unsigned long)o->unix_s, (unsigned long)o->kart_ms, (unsigned long)o->acilis,
             (unsigned long)o->ilk_sira, (unsigned long)o->son_sira,
             (unsigned long)o->nokta_sonraki, (unsigned)o->durum, (unsigned)o->basi_silindi);
    sunucu.sendContent(t);
  }
  sunucu.sendContent("]}");
  sunucu.sendContent("");
}

void kayit_veri_sayfa() {
  if (!host_gecerli()) { sunucu.send(403, "text/plain", "Host reddedildi"); return; }
  if (!kayit_bolum) { sunucu.send(503, "text/plain", "kayit bolumu yok"); return; }
  KayitDurum d = kayit_durum_al();
  if (d.durum == KDR_TARIYOR || d.durum == KDR_HATA) {
    sunucu.send(503, "text/plain", "kayit hazir degil (G durumu)");
    return;
  }
  uint32_t sira = sunucu.hasArg("sira") ? strtoul(sunucu.arg("sira").c_str(), nullptr, 10) : 1u;
  uint32_t kap = sunucu.hasArg("bayt") ? strtoul(sunucu.arg("bayt").c_str(), nullptr, 10)
                                       : KAYIT_VERI_AZAMI;
  if (kap > KAYIT_VERI_AZAMI) kap = KAYIT_VERI_AZAMI;
  uint32_t ilk = 0, son = 0, n, sonraki;
  xSemaphoreTake(kayit_kilit, portMAX_DELAY);
  n = kg_oku(&kayit_g, sira, kayit_veri_tampon, kap, &ilk, &son);
  sonraki = kayit_g.sonraki_sira;
  xSemaphoreGive(kayit_kilit);
  sunucu.sendHeader("X-Ilk-Sira", String(ilk));
  sunucu.sendHeader("X-Son-Sira", String(son));
  sunucu.sendHeader("X-Sonraki-Sira", String(sonraki));
  sunucu.sendHeader("X-Onay", String(d.onay));
  sunucu.setContentLength(n);
  sunucu.send(200, "application/octet-stream", "");
  if (n) sunucu.sendContent((const char *)kayit_veri_tampon, n);
}
```

`setup()`'ta `  sunucu.on("/pil", pil_sayfa);   // B21` satırının altına ekle:

```cpp
  sunucu.on("/kayit/liste", kayit_liste_sayfa);   // B72
  sunucu.on("/kayit/veri", kayit_veri_sayfa);     // B72 — esitleme (ham kayitlar)
```

- [ ] **Step 4: Yeşili gör, derle**

Run: `cd uretim && python test_kayit_esp.py`
Expected: `B72: 18/18 kosul gecti`.

Run: `cd uretim && python test_firmware3.py`
Expected: uyarısız, RAM < %25. `oz[]` statik ve 64 × ~40 B, yani ~2.6 KB; RAM payı %25'i aşarsa `oz` yığın/PSRAM'e taşınır ve bu bir karar olarak deftere yazılır.

- [ ] **Step 5: Commit**

```bash
git add kod/olcum-karti-a3/olcum-karti-a3.ino uretim/test_kayit_esp.py uretim/_firmware.json
git commit -q -F - <<'EOF'
B72 /kayit/liste (JSON) ve /kayit/veri (ham kayitlar, kilit altinda)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Eşitleme istemcisi `kopru/kayit_esitle.py`

**Files:**
- Create: `kopru/kayit_esitle.py`
- Modify: `uretim/test_kayit_esp.py` (`bolum_esitle`, sahte kart)

**Interfaces:**
- Consumes: `kayit_bicim.akis_coz`, `kayit_paketle` (B71)
- Produces:
  - `Esitleyici(taban_url, dizin, onay=None, bayt=8192)`
  - `.esitle(azami_tur=100000) -> {"yeni_kayit", "son_sira", "bosluk":[(istenen, ilk)]}`
  - `.son_sira()`
  - `seri_onay(kart) -> callable(sira)`, `http_onay(taban_url, parola=None) -> callable(sira)`
  - dosyalar: `<dizin>/kayitlar.kyt` (ham kayıt akışı), `<dizin>/durum.json`

- [ ] **Step 1: Testi yaz**

`uretim/test_kayit_esp.py`'nin import'larına ekle:

```python
import http.server
import struct
import tempfile
import threading
import urllib.parse

import kayit_bicim as KB                             # noqa: E402
import kayit_esitle as KE                            # noqa: E402
```

`BOLUMLER` satırının üstüne ekle:

```python
# ── B72.E · esitleme istemcisi (sahte kart) ───────────────────────────
class _SahteKart:
    """Kartin /kayit/veri ucunun sahtesi — kg_oku ile ayni anlam: `sira` ve
    sonrasi, kayit bolunmeden `bayt`a kadar."""

    def __init__(self, kayitlar: list[bytes]):
        self.kayitlar = kayitlar
        self.bozuk = False
        self.komutlar: list[str] = []

    def veri(self, sira: int, bayt: int) -> tuple[bytes, int, int]:
        govde, ilk, son = b"", 0, 0
        for ham in self.kayitlar:
            s = struct.unpack_from("<I", ham, 4)[0]
            if s < sira:
                continue
            if len(govde) + len(ham) > bayt:
                break
            govde += ham
            ilk, son = ilk or s, s
        if self.bozuk and len(govde) > 20:
            govde = govde[:20] + bytes([govde[20] ^ 1]) + govde[21:]
        return govde, ilk, son


def _sunucu(kart: _SahteKart):
    class Isleyici(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/akis":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'retry: 3000\n\nevent: kimlik\ndata: {"jeton":"abc123","surucu":true}\n\n')
                return
            if u.path != "/kayit/veri":
                self.send_error(404)
                return
            govde, ilk, son = kart.veri(int(q.get("sira", ["1"])[0]), int(q.get("bayt", ["8192"])[0]))
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("X-Ilk-Sira", str(ilk))
            self.send_header("X-Son-Sira", str(son))
            self.end_headers()
            self.wfile.write(govde)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            govde = self.rfile.read(n).decode()
            if self.headers.get("X-Olcum") == "1" and self.headers.get("X-Jeton") == "abc123":
                kart.komutlar.append(govde)
                self.send_response(200)
            else:
                self.send_response(403)
            self.end_headers()

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def _kayitlar(n: int, bas: int = 1) -> list[bytes]:
    return [KB.kayit_paketle(KB.T_NOKTA if i % 3 else KB.T_SAAT, i, 7,
                             bytes((i + j) & 0xFF for j in range(4 + (i % 5) * 36)))
            for i in range(bas, bas + n)]


def bolum_esitle() -> None:
    print("\n── B72.E  esitleme istemcisi (sahte kart)")
    kay = _kayitlar(50)
    kart = _SahteKart(kay)
    sunucu, taban = _sunucu(kart)
    try:
        with tempfile.TemporaryDirectory() as d:
            onaylar: list[tuple[int, int]] = []

            def onay(s):   # onay aninda dosyada kac bayt var
                onaylar.append((s, (Path(d) / KE.DOSYA).stat().st_size))

            e = KE.Esitleyici(taban, d, onay, bayt=1024)
            r = e.esitle(azami_tur=2)
            r = e.esitle()
            dosya = (Path(d) / KE.DOSYA).read_bytes()
            ok("B72.E1 karttaki butun kayitlar diske AYNEN (bayt bayt) geldi",
               dosya == b"".join(kay) and e.son_sira() == 50, f"{r}")
            ok("B72.E2 kesilen esitleme kaldigi yerden surdu, tekrar yok",
               len(KB.akis_coz(dosya)) == 50)
            yazili = [len(b"".join(k for k in kay if struct.unpack_from("<I", k, 4)[0] <= s))
                      for s, _ in onaylar]
            ok("B72.E4 onay YALNIZ diske yazildiktan sonra ve yazilanin sonuna kadar",
               bool(onaylar) and all(b == y for (_, b), y in zip(onaylar, yazili))
               and onaylar[-1][0] == 50, f"{onaylar[:3]}…")
            n_onay = len(onaylar)
            r2 = e.esitle()
            ok("B72.E5 yeni kayit yokken tekrar kosmak hicbir sey cekmez, onaylamaz",
               r2["yeni_kayit"] == 0 and len(onaylar) == n_onay)
        with tempfile.TemporaryDirectory() as d:
            kart.bozuk = True
            onaylar2: list[int] = []
            hata = False
            try:
                KE.Esitleyici(taban, d, onaylar2.append).esitle()
            except ValueError:
                hata = True
            ok("B72.E3 bozuk yanit REDDEDILIR: diske yazilmaz, onaylanmaz",
               hata and not onaylar2 and not (Path(d) / KE.DOSYA).exists())
            kart.bozuk = False
        with tempfile.TemporaryDirectory() as d:
            kart.kayitlar = kay[10:]            # 1..10 temizlikte silinmis
            r = KE.Esitleyici(taban, d).esitle()
            ok("B72.E6 temizlikte silinmis aralik BOSLUK olarak bildirilir",
               r["bosluk"] == [(1, 11)] and r["son_sira"] == 50, f"{r['bosluk']}")
            kart.kayitlar = kay
            geri = KB.kayit_paketle(KB.T_SAAT, 5, 0, bytes(12))
            kart.kayitlar = kay + [geri]
            hata = False
            try:
                KE.Esitleyici(taban, d).esitle()
            except ValueError:
                hata = True
            ok("B72.E7 sira geri giderse (kart sifirlanmis gibi) esitleme DURUR",
               hata or KE.Esitleyici(taban, d).son_sira() == 50)
            kart.kayitlar = kay
        KE.http_onay(taban)(42)
        ok("B72.E8 HTTP onayi jetonu /akis'ten alip X-Olcum + X-Jeton ile Go<sira> yollar",
           kart.komutlar == ["Go42"], str(kart.komutlar))
    finally:
        sunucu.shutdown()
```

`BOLUMLER`'i `[bolum_tablo, bolum_kaynak, bolum_esitle]` yap.

- [ ] **Step 2: Kırmızıyı gör**

Run: `cd uretim && python test_kayit_esp.py`
Expected: `ModuleNotFoundError: No module named 'kayit_esitle'`

- [ ] **Step 3: `kopru/kayit_esitle.py` yaz**

```python
# -*- coding: utf-8 -*-
"""B72 — KARTIN KAYITLARINI ESITLE (PC tarafi; PC uygulamasi da kullanacak).

    python kayit_esitle.py --http olcum.local --dizin kayitlar/ --port COM6
    python kayit_esitle.py --http olcum.local --dizin kayitlar/     # HTTP onayi

Kart asil kaydi tutar (tasarim §5). Bu istemci eksik kayitlari
`/kayit/veri`'den ceker, CRC'lerini dogrular, kartin baytlarini diske AYNEN
ekler, fsync eder ve ANCAK ONDAN SONRA "N'e kadar aldim" onayi yollar. Kartin
akilli temizligi yalniz bu onaylara bakar: onay erken gitseydi kartta
silinen veri diskte olmayabilirdi.

Onay yollari:
  * seri (`Go<sira>`, USB — parola gerekmez)
  * HTTP (`/komut`: oturum jetonu /akis'ten + Basic Auth; parola ORTAM
    DEGISKENINDEN, depoya ASLA yazilmaz)
Yalniz standart kutuphane.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kayit_bicim as KB                                   # noqa: E402

DOSYA = "kayitlar.kyt"
DURUM = "durum.json"


class Esitleyici:
    def __init__(self, taban_url: str, dizin, onay=None, bayt: int = 8192,
                 zaman_asimi: float = 10.0):
        self.taban = taban_url.rstrip("/")
        self.dizin = Path(dizin)
        self.dizin.mkdir(parents=True, exist_ok=True)
        self.onay = onay
        self.bayt = bayt
        self.zaman_asimi = zaman_asimi

    def son_sira(self) -> int:
        p = self.dizin / DURUM
        return json.loads(p.read_text(encoding="utf-8"))["son_sira"] if p.exists() else 0

    def _getir(self, sira: int) -> bytes:
        url = f"{self.taban}/kayit/veri?sira={sira}&bayt={self.bayt}"
        with urllib.request.urlopen(url, timeout=self.zaman_asimi) as y:
            return y.read()

    def _ekle(self, govde: bytes) -> None:
        with open(self.dizin / DOSYA, "ab") as f:
            f.write(govde)
            f.flush()
            os.fsync(f.fileno())

    def _durum_yaz(self, son: int) -> None:
        p = self.dizin / DURUM
        g = p.with_suffix(".tmp")
        with open(g, "w", encoding="utf-8") as f:
            json.dump({"son_sira": son}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(g, p)

    def esitle(self, azami_tur: int = 100000) -> dict:
        son = self.son_sira()
        yeni, bosluk = 0, []
        for _ in range(azami_tur):
            govde = self._getir(son + 1)
            if not govde:
                break
            kayitlar = KB.akis_coz(govde)      # CRC: bozuk yanit diske YAZILMAZ, onaylanmaz
            siralar = [k.sira for k in kayitlar]
            if siralar[0] <= son or siralar != sorted(set(siralar)):
                raise ValueError(f"kart sirasi geri gitti ya da tekrar etti: {siralar[:3]} (son {son})")
            if siralar[0] > son + 1:
                bosluk.append((son + 1, siralar[0]))
            self._ekle(govde)                  # once KALICI yaz (fsync)
            son = siralar[-1]
            self._durum_yaz(son)
            yeni += len(kayitlar)
            if self.onay:
                self.onay(son)                 # ancak diske yazildiktan SONRA
        return {"yeni_kayit": yeni, "son_sira": son, "bosluk": bosluk}


def seri_onay(kart):
    """USB seri uzerinden `Go<sira>` (kart_baglanti.SeriKart)."""
    def onayla(sira: int) -> None:
        kart.yaz(f"Go{sira}\n")
    return onayla


def http_onay(taban_url: str, parola: str | None = None, zaman_asimi: float = 5.0):
    """`/komut` uzerinden `Go<sira>`: jeton /akis'in `kimlik` olayindan."""
    taban = taban_url.rstrip("/")

    def jeton() -> str:
        with urllib.request.urlopen(f"{taban}/akis", timeout=zaman_asimi) as y:
            for _ in range(50):
                s = y.readline().decode("utf-8", "replace").strip()
                if s.startswith("data:") and "jeton" in s:
                    return json.loads(s[5:].strip())["jeton"]
        raise RuntimeError("oturum jetonu alinamadi")

    def onayla(sira: int) -> None:
        istek = urllib.request.Request(
            f"{taban}/komut", data=f"Go{sira}".encode("ascii"), method="POST",
            headers={"X-Olcum": "1", "X-Jeton": jeton(), "Content-Type": "text/plain"})
        if parola:
            istek.add_header("Authorization", "Basic " + base64.b64encode(
                f"olcum:{parola}".encode()).decode("ascii"))
        urllib.request.urlopen(istek, timeout=zaman_asimi).read()
    return onayla


def main() -> int:
    ap = argparse.ArgumentParser(description="Kartin kayitlarini esitle")
    ap.add_argument("--http", default="olcum.local")
    ap.add_argument("--dizin", required=True)
    ap.add_argument("--port", help="USB seri onay (orn. COM6)")
    ap.add_argument("--parola-ortam", default="OLCUM_WEB_PAROLA",
                    help="HTTP onayi icin web parolasini tutan ortam degiskeni")
    a = ap.parse_args()
    taban = a.http if a.http.startswith("http") else f"http://{a.http}"
    kart = None
    if a.port:
        import kart_baglanti
        kart = kart_baglanti.SeriKart(a.port)
        kart.ac()
        onay = seri_onay(kart)
    else:
        onay = http_onay(taban, os.environ.get(a.parola_ortam))
    try:
        r = Esitleyici(taban, a.dizin, onay).esitle()
    finally:
        if kart:
            kart.kapat()
    print(f"yeni {r['yeni_kayit']} kayit, son sira {r['son_sira']}, bosluk {r['bosluk']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Yeşili gör**

Run: `cd uretim && python test_kayit_esp.py`
Expected: `B72: 26/26 kosul gecti`. Önceki 18'e E1–E8 ekleniyor.

- [ ] **Step 5: Commit**

```bash
git add kopru/kayit_esitle.py uretim/test_kayit_esp.py
git commit -q -F - <<'EOF'
B72 esitleme istemcisi: CRC dogrula, diske aynen yaz + fsync, sonra onayla

Sahte kart sunucusuna karsi 8 iddia: tam, kaldigi yerden, bozuk yanit,
onay zamanlamasi, bosluk, sira geri gitmesi, HTTP onayi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Zincir adımı B72, mutasyonlar, kilit

**Files:**
- Modify (index cerrahisi): `uretim/dogrula3.py`, `uretim/mutasyon.py`, `uretim/beklenen_sayim.json`

- [ ] **Step 1: Mutasyonları ekle**

`MUTASYONLAR`'ın sonuna, kapanan `]`'nin üstüne ekle:

```python
    # ── B71 (1A-2 motor ayari) ──
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "(s == bas) ? &temiz : 0", "&temiz",
     "bos sektorlerin tamami taranirsa acilis 11.4 MB okur: T1 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "for (i = 0; i < n; i++) {", "for (i = 0; i < (uint8_t)n; i++) {",
     "256'lik parcada sayac tasarsa kirli kuyruk temiz sayilir: T2 kirmizi"),
    # ── B72 · kayit firmware + esitleme (test_kayit_esp.py) ──
    ("B72", "test_kayit_esp.py", "kod/olcum-karti-a3/partitions.csv",
     "nvs,      data, nvs,      0x9000,   0x5000", "nvs,      data, nvs,      0xA000,   0x5000",
     "nvs yer degistirirse WiFi parolasi ve kalibrasyon kaybolur: P1 kirmizi"),
    ("B72", "test_kayit_esp.py", "kod/olcum-karti-a3/kayit_esp.h",
     'kayit_nvs.putUInt("taban", kayit_g.sonraki_sira);', "(void)0;",
     "bicimlemeden once taban yazilmazsa numara tekrar verilebilir: F9 kirmizi"),
    ("B72", "test_kayit_esp.py", "kod/olcum-karti-a3/kayit_esp.h",
     "r = kg_ac(&kayit_g, taban, onay);", "r = kg_ac(&kayit_g, taban, 0u);",
     "onay NVS'ten verilmezse yeniden baslamada kayit DOLU'ya duser: F5 kirmizi"),
    ("B72", "test_kayit_esp.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "kayit_ornek(o.watt, millis());", "(void)0;",
     "loop noktaciyi beslemezse hic nokta kaydedilmez: F8 kirmizi"),
    ("B72", "test_kayit_esp.py", "kopru/kayit_esitle.py",
     "kayitlar = KB.akis_coz(govde)", "kayitlar = KB.akis_coz(govde[:0]) or KB.akis_coz(govde[:20])",
     "CRC dogrulanmazsa bozuk yanit diske yazilir ve onaylanir: E3 kirmizi"),
    ("B72", "test_kayit_esp.py", "kopru/kayit_esitle.py",
     "            self._ekle(govde)                  # once KALICI yaz (fsync)",
     "            pass",
     "diske yazmadan onaylarsa kartta silinen veri kaybolur: E1/E4 kirmizi"),
```

- [ ] **Step 2: Mutasyon koşusu**

Run: `cd uretim && python mutasyon.py --adim B72` (6 mutasyon)
ve `python mutasyon.py --adim B71` (+2 yeni, toplam 26).
Expected: hepsi YAKALANDI.

- [ ] **Step 3: Zincir adımı**

`dogrula3.py`'de B71 satırının altına ekle:

```python
    # B72 — KAYIT FIRMWARE ENTEGRASYONU (alt proje 1A-2): bolum tablosu,
    # firmware KAYNAGI (yorumsuz), PC esitleme istemcisi sahte karta karsi.
    # Gercek kart olcumleri tezgah_kayit.py'de (tezgah kalemi basiliyor).
    ("B72 Kayit firmware + esitleme (tablo + kaynak + sahte kart)", "test_kayit_esp.py"),
```

Docstring adım tablosuna B71 paragrafının altına ekle:

```
  B72 Kayit firmware + esitleme              (kaynak + sahte kart)
      Bolum tablosu nvs'i yerinde tutuyor mu, kayit gorevi cekirdek 0'da
      ve kilit altinda mi, PC istemcisi ancak diske yazdiktan sonra mi
      onayliyor. Gercek kart olcumleri tezgah_kayit.py'de.
```

- [ ] **Step 4: Kilit ve zincir**

- `beklenen_sayim.json`'a elle, B71'in ardına şunu ekle: `"B72 Kayit firmware + esitleme (tablo + kaynak + sahte kart)": [[26, 26]]`.
- B71'i 95 yap.
- B6 (derleme) değiştiyse kilitteki karşılığını çıktıdaki sayıya getir.

Run: `cd uretim && python dogrula3.py`
Expected: **21/21**.

- [ ] **Step 5: Commit** (üç dosya index cerrahisiyle; B72 ekleri + B71 kilit 91)

```bash
git commit -q -F - <<'EOF'
B72 zincire girdi (21/21), mutasyonlar, sayim kilidi

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Karta yükleme ve tezgah

**Files:**
- Create: `uretim/tezgah_kayit.py`

**Interfaces:**
- Consumes: `kart_baglanti.SeriKart`, `kayit_esitle.Esitleyici/seri_onay`, `kayit_bicim`, `partitions.csv`, esptool

- [ ] **Step 1: `uretim/tezgah_kayit.py` yaz**

```python
# -*- coding: utf-8 -*-
"""B72 — KAYIT MOTORU GERCEK KARTTA (tezgah; zincirde DEGIL).

    python tezgah_kayit.py --yedek                 tam flas yedegi (depo DISINA)
    python tezgah_kayit.py --duman                 G komutlari + 10 s kayit + esitleme
    python tezgah_kayit.py --durma                 flas yazmasinin olcume etkisi
    python tezgah_kayit.py --kesinti 20            kayit surerken 20 RTS sifirlamasi
    python tezgah_kayit.py --esit                  esitlenen dosya == flastaki bolum
    secenekler: --port COM6  --http olcum.local

🔴 --yedek NVS'i (WiFi ve web parolalarini) icerir: DEPO DISINA yazilir
   (<calisma alani>/.yedek/olcum-karti/). Geri donus:
   esptool --port COM6 -b 921600 write-flash 0x0 <yedek>.bin
"""
from __future__ import annotations

import datetime
import random
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                   # noqa: E402
import kayit_bicim as KB                               # noqa: E402
import kayit_esitle as KE                              # noqa: E402

YEDEK = KOK.parents[1] / ".yedek" / "olcum-karti"
G_ALAN = ["durum", "oturum", "nokta", "sonraki", "onay", "doluluk", "onaysiz",
          "dusen", "yaz_azami_us", "sil_azami_us", "sil_adet", "tarama_ms", "son_hata"]
gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    gecti, kaldi = gecti + bool(kosul), kaldi + (not kosul)
    print(f"  [{'OK' if kosul else '!!'}] {ad}" + (f"   {ek}" if ek else ""))


def esptool() -> Path:
    import os
    taban = Path(os.environ["LOCALAPPDATA"]) / "Arduino15" / "packages" / "esp32" / "tools"
    return sorted(taban.glob("esptool_py/*/esptool.exe"))[-1]


def kayit_bolumu() -> tuple[int, int]:
    for s in (KOK / "kod" / "olcum-karti-a3" / "partitions.csv").read_text().splitlines():
        p = [x.strip() for x in s.split("#", 1)[0].split(",")]
        if len(p) >= 5 and p[0] == "kayit":
            return int(p[3], 0), int(p[4], 0)
    raise SystemExit("partitions.csv'de kayit bolumu yok")


def g_coz(satir: str) -> dict | None:
    p = satir.split()
    if len(p) != 14 or p[0] != "G":
        return None
    return dict(zip(G_ALAN, (int(x) for x in p[1:])))


def dinle(k, sn: float, kosul=None) -> tuple[list[str], dict | None]:
    son, satirlar, g = time.time() + sn, [], None
    while time.time() < son:
        s = k.satir_oku(0.2)
        if s is None:
            continue
        satirlar.append(s)
        gg = g_coz(s)
        if gg:
            g = gg
            if kosul and kosul(g):
                break
    return satirlar, g


def komut(k, c: str, bekle: float = 1.0):
    k.yaz(c + "\n")
    return dinle(k, bekle)


def esitle(k, host: str, dizin: Path) -> dict:
    return KE.Esitleyici(f"http://{host}", dizin, KE.seri_onay(k)).esitle()


def yedek(port: str) -> int:
    YEDEK.mkdir(parents=True, exist_ok=True)
    hedef = YEDEK / f"tam-{datetime.datetime.now():%Y%m%d-%H%M%S}.bin"
    print(f"tam flas yedegi -> {hedef} (16 MB, ~3 dk)")
    rc = subprocess.run([str(esptool()), "--port", port, "-b", "921600", "read-flash",
                         "0x0", "0x1000000", str(hedef)]).returncode
    ok("tam flas yedegi alindi (16 MB)", rc == 0 and hedef.stat().st_size == 16 * 1024 * 1024,
       str(hedef))
    return rc


def duman(k, host: str) -> None:
    _, g = dinle(k, 1)
    satir, g = komut(k, "G?", 2)
    ok("G? durum satiri geliyor ve tarama bitmis (durum 1)", bool(g) and g["durum"] == 1,
       f"{g}")
    komut(k, "Gb200")
    _, g = dinle(k, 12, lambda x: x["durum"] == 2 and x["nokta"] >= 40)
    ok("Gb200: kayit basladi, 10 s'de >= 40 nokta", bool(g) and g["durum"] == 2
       and g["nokta"] >= 40, f"{g}")
    komut(k, "Gd", 2)
    with tempfile.TemporaryDirectory() as d:
        r = esitle(k, host, Path(d))
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
        ot = KB.oturumlari_kur(kay)
        son = max(ot.values(), key=lambda o: o.id) if ot else None
        ok("esitlenen son oturum: BASLA + noktalar + BITIR, kalibrasyon kopyasi var",
           bool(son) and son.basla is not None and len(son.noktalar) >= 40
           and son.bitir is not None, f"{r} nokta={len(son.noktalar) if son else 0}")
    _, g = dinle(k, 2)
    ok("onay karta ulasti (G onay = sonraki-1)", bool(g) and g["onay"] == g["sonraki"] - 1,
       f"{g}")


def durma(k) -> None:
    sonuc = {}
    for ad, c in (("kayitsiz", "Gd"), ("5/s", "Gb200"), ("50/s", "Gb20")):
        komut(k, "Gd", 1)
        if c != "Gd":
            komut(k, c, 2)
        k.yaz("K\n")
        satirlar, g = dinle(k, 60)
        kk = [s.split() for s in satirlar if s.startswith("K ")]
        kk = [x for x in kk if len(x) == 4 and x[1].isdigit()]
        sonuc[ad] = (kk[-1] if kk else None, g)
        print(f"  {ad:9s} K={kk[-1] if kk else '-'}  "
              f"G yaz_azami={g and g['yaz_azami_us']} sil_azami={g and g['sil_azami_us']} "
              f"sil={g and g['sil_adet']} dusen={g and g['dusen']}")
    komut(k, "Gd", 1)
    for ad in ("5/s", "50/s"):
        g = sonuc[ad][1]
        ok(f"{ad}: kuyrukta dusen nokta 0 (flas beklemesi sessiz kayip yapmadi)",
           bool(g) and g["dusen"] == 0, f"{g}")


def devam_tutarli(kayitlar) -> bool:
    beklenen: dict = {}
    for k in kayitlar:
        if k.tur == KB.T_BASLA:
            beklenen[k.oturum] = 0
        elif k.tur == KB.T_NOKTA:
            ilk = struct.unpack_from("<I", k.yuk)[0]
            if beklenen.get(k.oturum, ilk) != ilk:
                return False
            beklenen[k.oturum] = ilk + (len(k.yuk) - 4) // KB.NOKTA_BAYT
        elif k.tur == KB.T_DEVAM:
            ns = KB.devam_coz(k.yuk)["nokta_sira"]
            if beklenen.get(k.oturum, ns) != ns:
                return False
            beklenen[k.oturum] = ns
    return True


def kesinti(k, host: str, n: int) -> None:
    rng = random.Random(72)
    komut(k, "Gb100", 2)
    _, g = dinle(k, 5, lambda x: x["durum"] == 2)
    oturum = g["oturum"] if g else 0
    geri = 0
    for i in range(n):
        time.sleep(rng.uniform(2.0, 15.0))
        k.sifirla()
        _, g = dinle(k, 20, lambda x: x["durum"] == 2)
        geri += bool(g and g["durum"] == 2 and g["oturum"] == oturum)
        print(f"  sifirlama {i + 1}/{n}: {g and g['durum']} tarama={g and g['tarama_ms']} ms")
    komut(k, "Gd", 2)
    ok(f"{n} sifirlamanin hepsinde kayit AYNI oturumla surdu", geri == n, f"{geri}/{n}")
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
    ot = KB.oturumlari_kur(kay).get(oturum)
    siralar = [x.sira for x in kay]
    ok("flasta DEVAM sayisi sifirlama sayisina esit", bool(ot) and len(ot.devamlar) == n,
       f"{len(ot.devamlar) if ot else 0}")
    ok("nokta siralari bosluksuz/tekrarsiz (DEVAM tutarli), kayit sirasi tekrarsiz",
       devam_tutarli(kay) and len(siralar) == len(set(siralar)))


def esit(k, host: str, port: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))
        dosya = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
        k.kapat()
        ofset, boyut = kayit_bolumu()
        dokum = Path(d) / "kayit.bin"
        subprocess.run([str(esptool()), "--port", port, "-b", "921600", "read-flash",
                        hex(ofset), hex(boyut), str(dokum)], check=True)
        flas, _ = KB.flas_coz(dokum.read_bytes(), 4096)
    sozluk = {x.sira: x for x in flas}
    def ozu(x):
        return (x.tur, x.sira, x.oturum, x.yuk)
    ayni = [x for x in dosya if x.sira in sozluk and ozu(sozluk[x.sira]) == ozu(x)]
    ok("esitlenen her kayit flastaki kayitla BAYT BAYT ayni",
       len(ayni) == len(dosya), f"{len(ayni)}/{len(dosya)}")


def main() -> int:
    a = sys.argv[1:]

    def sec(ad, v=None):
        return a[a.index(ad) + 1] if ad in a else v

    port, host = sec("--port", "COM6"), sec("--http", "olcum.local")
    if "--yedek" in a:
        return yedek(port)
    k = kart_baglanti.SeriKart(port)
    k.ac()
    time.sleep(1.0)
    try:
        if "--duman" in a:
            duman(k, host)
        if "--durma" in a:
            durma(k)
        if "--kesinti" in a:
            kesinti(k, host, int(sec("--kesinti", "20")))
        if "--esit" in a:
            esit(k, host, port)
    finally:
        try:
            k.kapat()
        except Exception:
            pass
    print(f"\n{gecti}/{gecti + kaldi} tezgah denetimi gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

Not: `kart_baglanti.SeriKart.kapat()` iki kez çağrılırsa hata vermemeli; `esit()` kapattıktan sonra `finally` tekrar dener. Hata verirse `try/except` yukarıdaki gibi yutar.

- [ ] **Step 2: Tam yedek (karta YAZMADAN önce)**

Run: `cd uretim && python tezgah_kayit.py --yedek --port COM6`
Expected: `[OK] tam flas yedegi alindi (16 MB)`. Dosya `…/Elekronic/.yedek/olcum-karti/tam-*.bin`'de, depo dışında.

- [ ] **Step 3: Yükle (firmware + bölüm tablosu) ve paneli yeniden yaz**

Run: `cd uretim && python yukle.py --port COM6`
Expected: derleme ve yükleme başarılı. Kart açılışta `Kayit: 11648 KB, 2912 sektor — tarama gorevde` basar. Paneli yazmadan önce `Arayuz: YOK` görünmesi normal: bölüm büyüdü.

Run: `cd uretim && python arayuz-uret.py && python arayuz-yaz.py --port COM6`
Expected: görüntü 1 572 864 B, `partitions.csv'den OKUNDU`. Kart sıfırlanınca `Arayuz: LittleFS'te`.

- [ ] **Step 4: Tezgah koşuları**

Run: `cd uretim && python tezgah_kayit.py --duman --port COM6 --http olcum.local`
Expected: 4 denetimin hepsi OK. `tarama_ms` (boş bölüm) kaydedilir.

Run: `cd uretim && python tezgah_kayit.py --durma --port COM6`
Expected:
- 5/s ve 50/s'de `dusen` 0.
- `sil_azami_us` ve K satırı tablo halinde basılır; **sayılar DEVIR'e yazılır.**
- ADS takılı değil: döngü RDY zaman aşımıyla yavaş (~6 ms/tur). Bu sayılar flaşın etkisini **göreli** gösterir; ADS takılınca tekrarlanır.

Run: `cd uretim && python tezgah_kayit.py --kesinti 20 --port COM6 --http olcum.local`
Expected: 3 denetim OK. Her sıfırlamadaki `tarama_ms` basılır.

Run: `cd uretim && python tezgah_kayit.py --esit --port COM6 --http olcum.local`
Expected: `esitlenen her kayit … BAYT BAYT ayni`.

Herhangi bir denetim kırmızıysa `superpowers:systematic-debugging` ile kök neden bulunur. Tezgah denetimini gevşetmek yok.

- [ ] **Step 5: Commit**

```bash
git add uretim/tezgah_kayit.py
git commit -q -F - <<'EOF'
B72 tezgah: yedek, duman, durma (flas etkisi), RTS kesinti, bayt esitligi

Gercek kartta olculen sayilar DEVIR 5.12.66'da.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 9: Belgeler, son inceleme, gönderme

**Files:**
- Modify (index cerrahisi): `DEVIR.md` (5.12.66)
- Modify: `tasarim/2026-09-29-yazilim-sistemi.md` (§11 ilk riskin sonucu)
- Modify (depo dışı): çalışma alanı kökündeki `CLAUDE.md`, hafıza

- [ ] **Step 1: DEVIR 5.12.66** (5.12.65'in ardına, `#### 5.12.62`'nin önüne). İçeriği:
  - ne yapıldı
  - bölüm tablosu
  - `G` satırı biçimi
  - uçlar
  - eşitleme istemcisi
  - **tezgahta ölçülen sayılar:** tarama_ms (boş ve dolu), yaz/sil azami µs, K satırı kayıtsız/5/s/50/s, düşen, kesinti sonucu, bayt eşitliği
  - ADS'siz ölçümün sınırı
  - kalan tezgah kalemleri: fiş çekme, ADS ile tekrar

- [ ] **Step 2: Spec §11:** "Flaş silme/yazma işlemciyi on ms'ler durdurur" satırına ölçüm sonucunu ve kararı ekle.

- [ ] **Step 3: CLAUDE.md:** ölçüm kartı bölümüne B72 durumunu yaz. Zincir 21/21 ve süresi. `G` komutu, `tezgah_kayit.py`.

- [ ] **Step 4: Son bağımsız inceleme** (executing-plans'ın Final Review'ı). Kritik ve Önemli bulgular tek düzeltme turunda.

- [ ] **Step 5: Commit + push** (kullanıcıya sorarak; B71'deki gibi).
