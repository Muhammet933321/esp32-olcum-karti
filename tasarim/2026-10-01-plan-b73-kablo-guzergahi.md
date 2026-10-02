# B73 — Kablo güzergahı · uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `BELGELER/8-kutu.html`'in 10.3 / 10.4 / 11.1 alt adımlarında her kablo, iç (jak tarafından) arka duvar çiziminde, kuşbakışında ve 3B'de çizili, numaralı ve bilgi kartlı olsun. Tablo satırı çizimdeki kabloyu yaksın. Aynı adımların bilinen metin/veri hataları düzeltilsin.

**Architecture:** Bağlantılar tek kaynaktan gelir: `PIL_KABLOLAR` + yeni `KABLO_EK`. Her uç, parçaya göre ofsetli bir terminal noktasına çözülür (`KABLO_UCLARI`, `PANEL_UCLARI`, kart delikleri `kart_nokta`). Güzergah kural tabanlıdır: arka bölgede "öne çık → dik → yatay → gir"; istisnalar `KABLO_YOL` ara noktalarıyla. 2B, 3B, tablo ve kart aynı `guzergah()` çıktısını kullanır. Denetim (`kutu.py` bölüm 10) kapsam, çarpışma, HV açıklığı ve kesim payını ölçer. Mutasyon ve tarayıcı testi bunları ısırır.

**Tech Stack:** Python 3.14 (yalnız standart kütüphane + numpy, mevcut), satır içi SVG, WebGL (mevcut `kutu_3b.py`), başsız Edge + CDP (`kutu_ipucu_test.py`).

**Spec:** [2026-10-01-kablo-guzergahi.md](2026-10-01-kablo-guzergahi.md)

## Global Constraints

- **Commit YOK.** Çalışma ağacı `1d-eslestirme` dalında ve kullanıcının commit'lenmemiş B55–B70 işini taşıyor. "Checkpoint" adımları yalnız doğrulama + `git diff --stat`. Commit/push kullanıcı isteyince.
- Bağlantının tek kaynağı `kutu_veri.PIL_KABLOLAR` (10.3/10.4) ve `kutu_veri.KABLO_EK` (diğer adımlar). Başka yerde kablo listesi yazılmaz.
- Arka duvar kablo çizimi **içeriden, aynasız**: x soldan (veri ekseni), z yerden.
- Rol renkleri: `arti #d62828` · `gnd #1f1f1f` · `eksi12 #2563eb` · `sinyal #f77f00` · `hucre #9d0208` · `bacak #8a8a85`.
- Kesim boyu = `ceil(güzergah × 1.15 / 10)` cm (`KABLO_PAY = 1.15`). Kondansatör bacağı (`bacak`) kesilmez.
- HV açıklığı: her kablo parçası kart B'nin HV girişine ≥ `T.IEC60664_CREEPAGE_TAKVIYELI` (12.6 mm).
- Türkçe metin desenleri Türkçe yazılır ve `_kucuk()` ile karşılaştırılır (CLAUDE.md tuzağı).
- Duvar parçası `nasil` metninde yapıştırılan parçalar için **"kablo", "çubuk", "blok" geçmez.** `_ahsap_der()` bunların herhangi birinde "blo"/"çubuk" görür ("kablo" ⊃ "blo").
- Belge yalnız üretilir: `python kutu.py` (denetim yeşilse `BELGELER/8-kutu.html`'i yazar). Elle HTML düzenlenmez.

## Review Focus

1. **Bitişik düşük uçlar:** B0505S'in 1–2 bacağı 2.5 mm arayla. Çizimde iki kablo üst üste binip okunmaz olmamalı. Rozetler her kablonun en uzun parçasının ortasında, tek kablo için bile görünür olmalı (Task 4 testi: rozet sayısı = kablo sayısı).
2. **Telefonda dokunma:** fare olmadan, tabloya dokununca kart açılmalı ve çizimdeki kablo seçili olmalı. `click` yolu her ikisini de kapsıyor (Task 6 tarayıcı testi `tikla`).
3. **Kapalı `<details>` içindeki çizim:** kuşbakışı "Diğer çizimler" içinde. Satıra tıklayınca ilk görünür SVG kopyasına kaydırılmalı; kapalı detaydaki kopya seçili olsa da sorun değil (Task 6, `isaretle` ilk **görünür** öğeye kaydırır).
4. **Önceki adımın kablosu:** 10.4'te 10.3'ün kabloları soluk ama üzerine gelinince kart açılmalı (Task 4: soluk kablolar da `data-bi` taşır).
5. **Uç tahmini yanlış çıkarsa:** kullanıcı modülü ters takarsa çizim yanıltır. Kart notu "uç yerleri ±3 mm tahmin; ped adını modülün üstünden oku" demeli (Task 4 `bi_kablo` notu, iddia ile).

---

### Task 1: Güzergah çekirdeği — terminaller, kablo listesi, güzergah, denetim

**Files:**
- Modify: `uretim/kutu_veri.py:586` (F2 kaydı), `uretim/kutu_veri.py:617` sonrası (B73 veri bloğu)
- Modify: `uretim/kutu.py` (yeni fonksiyonlar `pil_asama()`'nın hemen altına, ~826; bölüm 10 `denetle()`'nin sonundaki `return D`'den önce, ~3007)

**Interfaces:**
- Produces:
  - `uc_noktasi(uc: str) -> tuple[tuple[float, float, float], set[str]]` (nokta, sahip gövde ref'leri)
  - `uc_adi(uc: str) -> str`
  - `kablo_rol(a: str, b: str) -> str` (`arti|gnd|eksi12|sinyal|hucre|bacak`)
  - `kablo_listesi() -> list[dict]`. Anahtarlar: `no:int, a, b, adim:str, not, rol, soz, kesit`
  - `adim_kablolari(no: str) -> list[dict]`
  - `guzergah(k: dict) -> list[tuple[float, float, float]]`
  - `guzergah_boyu(yol) -> float` (mm) · `kesim_cm(yol) -> int` · `_seg_nokta(p, q, x) -> float`
  - `kablo_carpismalari(k: dict, govde: list[dict]) -> list[str]`
  - `KABLO_RENK: dict[str, str]`, `KABLO_E12`, `KABLO_GND`, `KABLO_HUCRE`, `KABLO_SINYAL` (frozenset)

- [ ] **Step 1: Bölüm 10 iddialarını yaz (önce kırmızı)**

`uretim/kutu.py` `denetle()` içinde, `return D`'nin hemen önüne:

```python
    # ── 10 · KABLO GUZERGAHI (B73) ─────────────────────────────────────────
    # Kullanici (2026-10-01): "hangi kablo nereye gidecek ve nasil gidecek ... web
    # sayfasinda gosterelim". Cizim, 3B, tablo ve kart AYNI guzergah()'tan.
    print("\n  10 · KABLO GUZERGAHI (B73)")
    kl = kablo_listesi()
    D.kosul("Kablo listesi PIL_KABLOLAR'in ve KABLO_EK'in hepsini tam bir kez tasiyor",
            len(kl) == len(K.PIL_KABLOLAR) + len(K.KABLO_EK) and len({(k["a"], k["b"]) for k in kl}) == len(kl),
            f"{len(kl)} kablo")
    bayat = sorted(f"{a}→{b}" for a, b in K.KABLO_YOL if (a, b) not in {(k["a"], k["b"]) for k in kl})
    D.kosul("KABLO_YOL'da kablosu olmayan (bayat) guzergah kaydi yok", not bayat, f"bayat: {bayat}")
    cozulmez = []
    for k in kl:
        for u in (k["a"], k["b"]):
            try:
                uc_noktasi(u)
            except (KeyError, ValueError, StopIteration) as h:
                cozulmez.append(f"{u}: {h!r}")
    D.kosul("Her kablonun iki ucu bilinen bir terminale cozuluyor", not cozulmez, "; ".join(cozulmez[:4]))
    govde = kutu_govdeleri(nl, parcalar)
    gb = {g["ref"]: g for g in govde}
    uzak = []
    for k in kl:
        for u in (k["a"], k["b"]):
            p, sahip = uc_noktasi(u)
            sinir = max(K.KABLO_UC_SAPMA.get(r, 3.0) for r in sahip)
            if not any(nokta_kutu_mesafe(p, gb[r]) <= sinir for r in sahip if r in gb):
                uzak.append(u)
    D.kosul("Her terminal kendi parcasinin govdesinde (≤ 3 mm; TP1 tel ucu ≤ 15 mm)", not uzak,
            f"uzak: {sorted(set(uzak))[:5]}")
    ic_disi = [k["no"] for k in kl if not all(0.0 <= p[0] <= K.KUTU["ic_en"] and 0.0 <= p[1] <= K.KUTU["ic_boy"]
                                               and 0.0 <= p[2] <= hesap()["ic_yuk"] for p in guzergah(k))]
    D.kosul("Her guzergah kutunun icinde", not ic_disi, f"disari tasan: K{ic_disi}")
    carpan = {k["no"]: c for k in kl if (c := kablo_carpismalari(k, govde))}
    D.kosul("Hicbir guzergah (uclarin kendi parcasi disinda) bir govdenin icinden gecmiyor",
            not carpan, "; ".join(f"K{n}: {','.join(c)}" for n, c in list(carpan.items())[:4]))
    hv = hv_dugumu(next(p for p in K.IC_PARCA if p["ref"] == "B"))
    hv_en = {k["no"]: min(_seg_nokta(p, q, hv) for p, q in zip(guzergah(k), guzergah(k)[1:])) for k in kl}
    D.kosul(f"Hicbir kablo kart B'nin HV girisine {T.IEC60664_CREEPAGE_TAKVIYELI} mm'den yakin gecmiyor",
            min(hv_en.values()) >= T.IEC60664_CREEPAGE_TAKVIYELI, f"en yakin {min(hv_en.values()):.1f} mm")
    kisa = [k["no"] for k in kl if k["rol"] != "bacak"
            and kesim_cm(guzergah(k)) * 10.0 < guzergah_boyu(guzergah(k)) * 1.1]
    D.kosul("Kesim boyu guzergahin en az %10 fazlasi (uc tahmini + kivrim payi)", not kisa, f"kisa: K{kisa}")
    karisik = [k["no"] for k in kl if {k["a"], k["b"]} & KABLO_E12 and {k["a"], k["b"]} & KABLO_GND]
    D.kosul("Hicbir kablo -12 tarafini kart GND tarafina baglamiyor", not karisik, f"{karisik}")
    # Rol, grafin KENDI bilesenleriyle capraz sinanir (iki bagimsiz kaynak): -12'ye bagli uc
    # 'eksi12', KART_GND'ye bagli uc 'gnd' rolunde olmali (bacak haric).
    gr_ = pil_grafi()
    yanlis_rol = [k["no"] for k in kl if (k["a"], k["b"]) in {(a, b) for a, b, *_ in K.PIL_KABLOLAR}
                  and k["rol"] != "bacak"
                  and (("-12" in gr_[k["a"]]) != (k["rol"] == "eksi12")
                       or ("KART_GND" in gr_[k["a"]]) != (k["rol"] == "gnd"))]
    D.kosul("Kablo rolu dugum grafiyla tutarli (-12 -> mavi, KART_GND -> siyah)", not yanlis_rol, f"K{yanlis_rol}")
    D.kosul("10.3 / 10.4 / 11.1'in her birinde en az bir kablo var",
            all(adim_kablolari(n) for n in ("10.3", "10.4", "11.1")),
            str({n: len(adim_kablolari(n)) for n in ("10.3", "10.4", "11.1")}))
```

- [ ] **Step 2: Kırmızı olduğunu gör**

Run: `cd projeler/olcum-karti/uretim && python kutu.py --belge-yok`
Expected: `NameError: name 'kablo_listesi' is not defined` (bölüm 10'da çöker).

- [ ] **Step 3: Veriyi ekle (`kutu_veri.py`)**

`PIL_KABLOLAR` içindeki F2 satırını değiştir (spec §4.1; kullanıcı böyle kurdu, düğüm aynı):

```python
    ("F2.2", "F1P.2", "pil", "sigorta → F1P'nin çıkış klipsi = TP4056 B+ düğümü (iki hücre burada paralel)"),
```

`PIL_ANAHTAR = {...}` satırının altına B73 bloğunu ekle (sayılar prototipte doğrulandı: 26 kablo, çarpışma yok, HV ≥ 58 mm):

```python
# ── B73 · kablo guzergahi (8-kutu.html'de cizim + 3B) ──────────────────────
# Uc ofsetleri parcanin KENDI kosesine gore (dx, dy, dz) mm; duvar parcasinda dy = on yuz.
# OLCULMEDI — modul fotografi / veri sayfasindan TAHMIN (±3 mm): cizim yon ve sira
# gosterir, milimetrik lehim yeri degil. Kart notu bunu soyler.
KABLO_UCLARI = {
    "MT1": {"OUT+": (2.0, 14.0, 12.0), "OUT-": (2.0, 14.0, 5.0), "IN+": (34.0, 14.0, 12.0), "IN-": (34.0, 14.0, 5.0)},
    "MT2": {"IN+": (2.0, 14.0, 12.0), "IN-": (2.0, 14.0, 5.0), "OUT+": (34.0, 14.0, 12.0), "OUT-": (34.0, 14.0, 5.0)},
    # B0505S (Hi-Link veri sayfasi): 1 +Vin, 2 -Vin, 4 -Vout, 6 +Vout; bacaklar asagi
    "IZ": {"IN+": (3.0, 7.0, 0.0), "IN-": (5.5, 7.0, 0.0), "OUT-": (10.6, 7.0, 0.0), "OUT+": (15.7, 7.0, 0.0)},
    "KL": {"+": (4.0, 10.0, 5.0), "-": (12.0, 10.0, 5.0)},
    "F0": {"1": (3.0, 10.0, 5.0), "2": (22.0, 10.0, 5.0)},
    "F1P": {"1": (3.0, 10.0, 5.0), "2": (22.0, 10.0, 5.0)},
    "F2": {"1": (3.0, 10.0, 5.0), "2": (22.0, 10.0, 5.0)},
    "CB": {"+": (2.0, 10.0, 2.0), "-": (2.0, 10.0, 8.0)},
    # yuvanin kendi telleri yaysiz (+) uctan cikar; YUVA1'in + ucu SOLDA, YUVA2'ninki SAGDA (spec §4.2)
    "YUVA1": {"+": (0.0, 10.0, 14.0), "-": (0.0, 10.0, 7.0)},
    "YUVA2": {"+": (80.0, 10.0, 14.0), "-": (80.0, 10.0, 7.0)},
    # TP1'in 6.0'da lehimlenen telleri duvar ile kart A arasindaki araliktan yukari cikar: uc = tel ucu
    "TP1": {"OUT+": (2.5, 6.0, 18.0), "B+": (6.5, 6.0, 18.0), "B-": (10.5, 6.0, 18.0), "OUT-": (14.5, 6.0, 18.0)},
    # ESP32 devkit (kizakta, USB arka duvara): pin tepeleri govdenin ustu (dz = yuk)
    "ESP32": {"5V": (2.0, 10.0, 28.0), "GND": (25.5, 10.0, 28.0), "GPIO10": (2.0, 34.0, 28.0), "J5": (13.75, 40.0, 28.0)},
}
KABLO_UC_SAPMA = {"TP1": 15.0}        # mm — TP1 ucu govde degil, araliktan cikan TEL UCU
KABLO_UC_TAKMA = {"H1+": "YUVA1.+", "H1-": "YUVA1.-", "H2+": "YUVA2.+", "H2-": "YUVA2.-"}
# Panel ogesinin ic ucu (dx, dz): y = panel govdesinin ice uzanan ucu (panel_hacim)
PANEL_UCLARI = {"SWP1": {"1": (0.0, 0.0), "2": (0.0, -4.7)}, "LED1": {"A": (1.3, 0.0), "K": (-1.3, 0.0)},
                "J1.2": {"L": (0.0, 0.0)}, "CAL": {"L": (0.0, 0.0)}}
UC_AD = {
    "H1+": "1. yuvanın kırmızı teli", "H1-": "1. yuvanın siyah teli",
    "H2+": "2. yuvanın kırmızı teli", "H2-": "2. yuvanın siyah teli",
    "F1P.1": "F1P klips 1", "F1P.2": "F1P klips 2 (çıkış)", "F2.1": "F2 klips 1", "F2.2": "F2 klips 2 (çıkış)",
    "F0.1": "F0 klips 1", "F0.2": "F0 klips 2",
    "TP1.B+": "TP4056 B+ teli", "TP1.B-": "TP4056 B− teli", "TP1.OUT+": "TP4056 OUT+ teli", "TP1.OUT-": "TP4056 OUT− teli",
    "SWP1.1": "PİL anahtarı orta bacak", "SWP1.2": "PİL anahtarı dış bacak (AÇ'ta ortayla öten)",
    "MT1.IN+": "MT1 IN+", "MT1.IN-": "MT1 IN−", "MT1.OUT+": "MT1 OUT+", "MT1.OUT-": "MT1 OUT−",
    "MT2.IN+": "MT2 IN+", "MT2.IN-": "MT2 IN− (−12 tarafı)", "MT2.OUT+": "MT2 OUT+", "MT2.OUT-": "MT2 OUT−",
    "IZ.IN+": "B0505S 1 (+Vin)", "IZ.IN-": "B0505S 2 (−Vin)", "IZ.OUT-": "B0505S 4 (−Vout)", "IZ.OUT+": "B0505S 6 (+Vout)",
    "CB.+": "680 µF uzun bacak", "CB.-": "680 µF şeritli bacak",
    "KL.+": "KL + vidası", "KL.-": "KL − vidası",
    "A.C34": "kart A C34 teli (24 V +)", "A.C36": "kart A C36 teli (−12)", "A.J5": "kart A J5 başlığı",
    "ESP32.5V": "ESP32 5V pini", "ESP32.GND": "ESP32 GND pini (ikinci)", "ESP32.GPIO10": "ESP32 GPIO10",
    "ESP32.J5": "ESP32 pinleri (J5 kablosu)",
    "LED1.A": "GÜÇ LED'i uzun bacak (10 kΩ ile)", "LED1.K": "GÜÇ LED'i kısa bacak",
    "J1.2.L": "COM jakının lehim kulağı", "CAL.L": "CAL jakının lehim kulağı",
}
# PIL_KABLOLAR disinda cizilen kablolar. Graf (union-find) bunlari GORMEZ: LED + direnc
# iletken degil, J5/CAL sinyal. Adim numarasi yerlerini belirler.
KABLO_EK = [
    {"a": "KL.+", "b": "LED1.A", "adim": "10.4", "not": "10 kΩ (R060) LED'in uzun bacağına lehimli, makaronlu"},
    {"a": "LED1.K", "b": "J1.2.L", "adim": "10.4",
     "not": "katot → COM jakının lehim kulağı = kart GND (J5'ten önce de lamba yanar)"},
    {"a": "ESP32.J5", "b": "A.J5", "adim": "11.1", "not": "10 telli kablo; tel eşlemesi Yerleşim 1.12"},
    {"a": "ESP32.GPIO10", "b": "CAL.L", "adim": "11.1", "not": "22 kΩ seri direnç jakın iç ucunda, makaronlu"},
]
# Guzergah istisnalari: ara noktalar (x, y, z) mm + kullaniciya soylenen yol.
# Kayitsiz kablo varsayilan yolu izler: one cik, dik, yatay, gir (arka bolgede).
KABLO_YOL = {
    ("H1+", "F1P.1"): {"ara": [(88, 7, 50), (88, 7, 13), (80, 13, 13)],
                       "soz": "yuvanın sol ucundan duvar dibine iner, F1P'nin üstünden girer"},
    ("H2+", "F2.1"): {"ara": [(176, 7, 77), (176, 7, 13), (180, 13, 13)],
                      "soz": "2. yuvanın sağ ucundan sağ alt köşeye iner"},
    ("F2.2", "F1P.2"): {"ara": [(199, 13, 13), (199, 7, 33), (104, 7, 33), (104, 7, 13)],
                        "soz": "ESP32'nin üstünden, 1. yuvanın altından (yerden 33 mm) arka duvar boyunca sola"},
    ("F1P.2", "TP1.B+"): {"ara": [(99, 13, 13), (84, 7, 13), (84, 7, 22), (60, 7, 22)],
                          "soz": "duvar ile kart A arasındaki aralıktan TP4056'nın teline"},
    ("H1-", "TP1.B-"): {"ara": [(88, 7, 43), (88, 7, 22), (64, 7, 22)],
                        "soz": "yuvanın sol ucundan aralığa iner, TP4056'nın teline"},
    ("H2-", "TP1.B-"): {"ara": [(176, 7, 70), (176, 7, 33), (88, 7, 33), (88, 7, 22), (64, 7, 22)],
                        "soz": "2. yuvanın sağ ucundan ESP32'nin üstünden sola; yuvanın teli yetmez, ek gerekir"},
    ("TP1.OUT+", "SWP1.1"): {"ara": [(56, 7, 22), (84, 7, 22), (84, 7, 80), (84, 130, 80), (35, 130, 81)],
                             "soz": "aralıktan yukarı, kapağın altından öne, PİL anahtarına"},
    ("SWP1.2", "MT1.IN+"): {"ara": [(35, 130, 80), (84, 130, 80), (84, 18, 80), (84, 18, 36)],
                            "soz": "PİL anahtarından kapağın altından arkaya, MT1'in sağ ucuna"},
    ("KL.+", "A.C34"): {"ara": [(24, 30, 60), (98, 120, 60)],
                        "soz": "klemensten kart A'nın üstünden öne, kartın ön kenarındaki tele"},
    ("KL.-", "A.C36"): {"ara": [(32, 30, 62), (103, 120, 62)],
                        "soz": "klemensten kart A'nın üstünden öne, kartın ön kenarındaki tele"},
    ("KL.+", "LED1.A"): {"ara": [(24, 30, 70), (24, 130, 70), (72, 130, 81)],
                         "soz": "klemensten kart A'nın üstünden öne, GÜÇ lambasına"},
    ("ESP32.GPIO10", "CAL.L"): {"ara": [(141, 40, 78), (141, 130, 78), (143, 130, 81)],
                                "soz": "ESP32'den yukarı, kart B'nin üstünden (HV'ye ≥ 13 mm) öne, CAL jakına"},
    ("ESP32.J5", "A.J5"): {"ara": [(153, 45, 58), (50, 45, 58)],
                           "soz": "ESP32'den yukarı, kart A'nın üstünden J5 başlığına"},
}
KABLO_PAY = 1.15                     # kesim = guzergah x pay, yukari 1 cm
KABLO_KESIT = {"sinyal": "ince tel (jumper)", "bacak": "kondansatörün kendi bacağı"}   # gerisi 0.5 mm²
KABLO_ROL_AD = {"arti": "artı (5 V / 24 V)", "gnd": "paket / kart GND", "eksi12": "−12 tarafı (B0505S çıkışı)",
                "hucre": "hücre → sigorta → TP4056", "sinyal": "sinyal (J5, CAL)", "bacak": "kondansatör bacağı"}
```

- [ ] **Step 4: Hesabı ekle (`kutu.py`, `pil_asama()`'nın altına)**

```python
# ── B73 · kablo guzergahi ─────────────────────────────────────────────────
KABLO_RENK = {"arti": "#d62828", "gnd": "#1f1f1f", "eksi12": "#2563eb", "sinyal": "#f77f00",
              "hucre": "#9d0208", "bacak": "#8a8a85"}
KABLO_E12 = frozenset({"IZ.OUT-", "MT2.IN-", "MT2.OUT-", "KL.-", "CB.-", "A.C36"})
KABLO_GND = frozenset({"H1-", "H2-", "TP1.B-", "TP1.OUT-", "MT1.IN-", "MT1.OUT-", "IZ.IN-",
                       "ESP32.GND", "LED1.K", "J1.2.L"})
KABLO_HUCRE = frozenset({"H1+", "H2+", "F1P.1", "F1P.2", "F2.1", "F2.2", "TP1.B+"})
KABLO_SINYAL = frozenset({"ESP32.J5", "A.J5", "ESP32.GPIO10", "CAL.L"})


def kablo_rol(a: str, b: str) -> str:
    """Cizim rengi ve kesit icin rol. Sira onemli: bacak > sinyal > -12 > GND > hucre > arti."""
    u = {a, b}
    if any(x.startswith("CB.") for x in u):
        return "bacak"
    if u & KABLO_SINYAL:
        return "sinyal"
    if u & KABLO_E12:
        return "eksi12"
    if u & KABLO_GND:
        return "gnd"
    if u & KABLO_HUCRE:
        return "hucre"
    return "arti"


def uc_adi(uc: str) -> str:
    return K.UC_AD.get(uc, uc.replace(".", " "))


def uc_noktasi(uc: str) -> tuple[tuple[float, float, float], set[str]]:
    """Kablo ucu -> (kutu ic koordinati, ucun sahibi govde ref'leri). Ad bicimi 'REF.UC'
    (REF noktali olabilir: 'J1.2.L'); hucre uclari H1± / H2± yuvanin telleridir."""
    uc = K.KABLO_UC_TAKMA.get(uc, uc)
    ref, u = uc.rsplit(".", 1)
    if ref == "A":
        A = next(p for p in K.IC_PARCA if p["ref"] == "A")
        if u in V.YER:                                     # adli yer (J5 basligi)
            c, r = V.YER[u][2], V.YER[u][3]
        else:                                              # delik adi: harf(ler) + sayi (C34)
            harf = "".join(ch for ch in u if ch.isalpha())
            c = next(i for i in range(80) if Y.sutun_adi(i) == harf)
            r = int("".join(ch for ch in u if ch.isdigit())) - 1
        x, y, z = kart_nokta(A, c, r)
        return (x, y, z + 2.0), {"A (dolu)", "A (boş kenar)"}
    duvar = {d["ref"]: d for d in duvar_parcalari()}
    if ref in duvar:
        d = duvar[ref]
        dx, dy, dz = K.KABLO_UCLARI[ref][u]
        sahip = {"CB", "MT2"} if ref in ("CB", "MT2") else {ref}
        return (d["x"] + dx, d["y"] + dy, d["z"] + dz), sahip
    if ref == "ESP32":
        e = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == "ESP32"), 0.0)
        dx, dy, dz = K.KABLO_UCLARI["ESP32"][u]
        return (e["x"] + dx, e["y"] + dy, z0 + dz), {"ESP32"}
    panel = {o["ref"]: o for o in panel_ogeleri()}
    if ref in panel:
        o = panel[ref]
        dx, dz = K.PANEL_UCLARI[ref][u]
        return (o["x"] + dx, K.KUTU["ic_boy"] - o["derin_mm"], o["z"] + dz), {ref}
    raise KeyError(uc)


def kablo_listesi() -> list[dict]:
    """B73: cizilen kablolar — PIL_KABLOLAR (10.3 paket / 10.4 analog) + KABLO_EK, K1.. sirayla."""
    out = [{"a": a, "b": b, "adim": "10.3" if pil_asama((a, b)) == "paket" else "10.4", "not": n}
           for a, b, _t, n in K.PIL_KABLOLAR]
    out += [{"a": e["a"], "b": e["b"], "adim": e["adim"], "not": e["not"]} for e in K.KABLO_EK]
    for i, k in enumerate(out, 1):
        rol = kablo_rol(k["a"], k["b"])
        k.update(no=i, rol=rol, soz=K.KABLO_YOL.get((k["a"], k["b"]), {}).get("soz", "kısa yoldan, parçaların önünden"),
                 kesit=K.KABLO_KESIT.get(rol, "0.5 mm²"))
    return out


def adim_kablolari(no: str) -> list[dict]:
    return [k for k in kablo_listesi() if k["adim"] == no]


def guzergah(k: dict) -> list[tuple[float, float, float]]:
    """Eksen eksen kirik cizgi. Ara nokta yoksa ve iki uc arka bolgedeyse (y < 45):
    one cik (en derin ucun 3 mm onu), dik, yatay, gir. Ara noktalarla: her adimda y, z, x
    sirasi. 1 mm'den kisa kayma ayri nokta olmaz (onceki noktaya emilir) — kart deliginin
    2.54 izgarasi ile yuvarlak ara nokta arasindaki 0.1 mm'lik kirik cizimi bozmasin."""
    a, b = uc_noktasi(k["a"])[0], uc_noktasi(k["b"])[0]
    ara = [tuple(float(v) for v in p) for p in K.KABLO_YOL.get((k["a"], k["b"]), {}).get("ara", [])]
    yol = [a]

    def ekle(r):
        r = tuple(r)
        d = max(abs(r[i] - yol[-1][i]) for i in range(3))
        if d < 1e-6:
            return
        if d < 1.0 and len(yol) > 1:
            yol[-1] = r
            return
        yol.append(r)
    for p, q in zip([a] + ara, ara + [b]):
        if not ara and p[1] < 45 and q[1] < 45:
            yl = max(p[1], q[1]) + 3.0
            for r in ((p[0], yl, p[2]), (p[0], yl, q[2]), (q[0], yl, q[2]), q):
                ekle(r)
        else:
            cur = list(yol[-1])
            for e in (1, 2, 0):
                cur[e] = q[e]
                ekle(cur)
    return yol


def guzergah_boyu(yol) -> float:
    return sum(math.dist(p, q) for p, q in zip(yol, yol[1:]))


def kesim_cm(yol) -> int:
    return math.ceil(guzergah_boyu(yol) * K.KABLO_PAY / 10.0)


def _seg_nokta(p, q, x) -> float:
    """x noktasinin [p, q] dogru parcasina en kisa uzakligi (mm)."""
    d = [q[i] - p[i] for i in range(3)]
    L2 = sum(v * v for v in d)
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, sum((x[i] - p[i]) * d[i] for i in range(3)) / L2))
    return math.dist(x, [p[i] + t * d[i] for i in range(3)])


def kablo_carpismalari(k: dict, govde: list[dict]) -> list[str]:
    """Guzergah parcalarinin (cizgi) 1 mm'den derin girdigi govdeler. Ilk parca bas ucun,
    son parca son ucun sahibini sayaz (kablo oraya lehimli); aradakiler hicbirini."""
    yol = guzergah(k)
    sa, sb = uc_noktasi(k["a"])[1], uc_noktasi(k["b"])[1]
    n = len(yol) - 1
    out = set()
    for i, (p, q) in enumerate(zip(yol, yol[1:])):
        haric = (sa if i == 0 else set()) | (sb if i == n - 1 else set())
        lo = [min(p[j], q[j]) for j in range(3)]
        hi = [max(p[j], q[j]) for j in range(3)]
        for g in govde:
            if g["ref"] in haric:
                continue
            gl = (g["x"], g["y"], g.get("z", 0.0))
            gh = (g["x"] + g["en"], g["y"] + g["boy"], g.get("z", 0.0) + g["yuk"])
            if all(lo[j] < gh[j] - 1.0 and hi[j] > gl[j] + 1.0 for j in range(3)):
                out.add(g["ref"])
    return sorted(out)
```

- [ ] **Step 5: Yeşil olduğunu gör**

Run: `cd projeler/olcum-karti/uretim && python kutu.py --belge-yok`
Expected: bölüm 10'un 12 iddiası `[OK]`. "en yakin 58.2 mm"; `{'10.3': 9, '10.4': 15, '11.1': 2}`. Önceki bölümler değişmeden yeşil (F2 değişikliği grafı bozmaz: F1P.2 zaten TP1.B+'ya bağlı). Toplam **2403 + 12 = 2415**.
Bir iddia kırmızıysa: `kablo_carpismalari` çıktısındaki kablo için `KABLO_YOL`'a, çarptığı gövdenin çevresinden 3 mm payla dolaşan bir ara nokta ekle ve yeniden koş. Eşiği gevşetme.

- [ ] **Step 6: Checkpoint** — `git diff --stat uretim/kutu.py uretim/kutu_veri.py` (commit yok).

---

### Task 2: Yapıştırma kuralı — modüller ve küçük parçalar sıcak silikonla (spec §4.7)

**Files:**
- Modify: `uretim/kutu_veri.py` (`YAPISTIRMA_ISTISNA` ~769, `DUVAR_TUTUCU`, `DUVAR_PARCA`'nın `nasil` metinleri MT1/MT2/IZ/CB/KL/F0/F1P/F2, `KUTU["yapistirici"]`'nin "18650" satırı)
- Modify: `uretim/kutu.py:~4709` ("Kural:" giriş cümlesi)

**Interfaces:**
- Consumes: mevcut iddialar (`sokulebilir`, `ikinci tutturma`, `eskimis istisna`, `_ahsap_der`, `istisnanin yapistiricisi tabloda`).
- Produces: `K.YAPISTIRMA_ISTISNA` anahtarları ⊇ {YUVA1, YUVA2, MT1, MT2, IZ, CB, KL, F0, F1P, F2}; bu parçalar için `DUVAR_TUTUCU[ref] is None`.

- [ ] **Step 1: İddia (kırmızı)** — bölüm 10'a ekle:

```python
    yapisik_beklenen = {"YUVA1", "YUVA2", "MT1", "MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"}
    D.kosul("Kullanici karari (2026-09-30): moduller ve kucuk duvar parcalari sicak silikonla, tutucusuz",
            yapisik_beklenen <= set(K.YAPISTIRMA_ISTISNA)
            and all(K.DUVAR_TUTUCU.get(r) is None for r in yapisik_beklenen),
            f"eksik: {sorted(yapisik_beklenen - set(K.YAPISTIRMA_ISTISNA))}")
    degerli = {"A", "B", "ESP32", "RS", "Q1"}
    D.kosul("Degerli parcalar (kartlar, ESP32, sont, Q1) yapistirma istisnasinda DEGIL",
            not (degerli & set(K.YAPISTIRMA_ISTISNA)))
```

Run: `python kutu.py --belge-yok` → ilk iddia `[!!]` (eksik: CB, F0, F1P, F2, IZ, KL, MT1, MT2).

- [ ] **Step 2: Veri.** `YAPISTIRMA_ISTISNA`'ya sekiz kayıt ekle:

```python
_MODUL_SILIKON = {"yapistirici": "sıcak silikon",
                  "sokme": "derze izopropil alkol damlat, plastik kartla kaldır",
                  "neden": "Kullanıcı kararı (2026-09-30): 'B0505S, MT1 ve MT2'yi sıcak silikonla yapıştırabilirim, "
                           "elimde izopropil alkol var, sökmesi kolay'; küçük parçalar için 2026-09-27: 'küçük parçaları "
                           "yapıştırabiliriz, değerli şeyler yapıştırılmasın'. Kablo bağı tutucuları ve çubukları kalktı."}
for _r in ("MT1", "MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"):
    YAPISTIRMA_ISTISNA[_r] = dict(_MODUL_SILIKON)
```

`DUVAR_TUTUCU`'da bu sekiz anahtarı `None` yap. `DUVAR_PARCA`'daki `nasil` metinlerini şunlarla değiştir. Metinlerde "kablo", "çubuk" ve "blok" yok; "sıcak silikon" ve "sökül" var:

```python
# MT1
"Arka duvarın iç yüzüne düz (A'nın boş arka şeridinin üstü), sıcak silikonla — PCB'nin arkasından, çipin ve bobinin üstüne değil. OUT pedleri SOLA (F0 ve B0505S). Trimpot içe bakar, ayar kapak açıkken. Derze izopropil alkol damlatıp plastik kartla kaldırarak sökülür."
# MT2
"MT1'in üstüne, aynı yöntemle (sıcak silikon, PCB'nin arkasından); IN pedleri SOLA (B0505S ve 680 µF). İzopropil alkolle sökülür."
# IZ
"MT2'nin soluna, bacaklar aşağı; dört bacağına ince tel lehimli ve makaronlu. Gövdesinden sıcak silikonla duvara; izopropil alkolle sökülür. Giriş (1 +Vin, 2 −Vin) ve çıkış (4 −Vout, 6 +Vout) tarafı hiçbir telle birleşmez."
# CB
"MT2'nin üstüne, yatık (gövde x yönünde), gövdesinden sıcak silikonla. Bacakları MT2'nin giriş pedlerine lehimli — ⚠ Elektrolitik: şeritli bacak EKSİ (MT2 IN−), uzun bacak artı (MT2 IN+). İzopropil alkol ve iki bacağın lehimi sökülerek sökülür."
# KL
"B0505S'in üstüne, tabanından sıcak silikonla (PCB klemensinde montaj deliği yok). Vidalar içe: 10.4'te MT2'nin çıkışı ve kartın 24 V telleri buraya vidalanır. Hangi vidanın + olduğunu kalemle yaz. İzopropil alkolle sökülür."
# F0
"Arka duvarın sol ucuna, MT1'in soluna ve B0505S'in altına (konum tabloda): iki klips + en fazla 25 mm'lik plaket şeridi (FUS009 tek gövde değil), şeridin arkasından sıcak silikonla. İçine 1 A hızlı cam sigorta (FUS003) — 10.5'e kadar TAKMA. Sigorta içe doğru çekilerek çıkar. İzopropil alkolle sökülür."
# F1P
"Arka duvarın en alt sırasına, TP4056 rafının sağına (konum tabloda): klips şeridi, arkasından sıcak silikonla. Sigorta içe çekilerek değişir. İzopropil alkolle sökülür."
# F2
"Arka duvarın SAĞ ALT köşesine, en alt sıraya, aynı yöntemle (klips şeridi, sıcak silikon). Çıkışı arka duvar boyunca F1P'nin çıkış klipsine (= TP4056 B+). İzopropil alkolle sökülür."
```

`KUTU["yapistirici"]`'de ilk sütununda "18650" geçen tek satırın adını şöyle yap: `"18650 yuvaları, modüller (MT1, MT2, B0505S), 680 µF, KL, sigorta şeritleri"`. Yapıştırıcı sütunu "sıcak silikon" içeriyorsa öyle kalsın.

`kutu.py`'de "Kural:" cümlesini (`"<b>Kural:</b> kutuya giren hiçbir parça yapıştırılmaz ...`) şununla değiştir:

```python
        "<b>Kural:</b> değerli parçalar — kartlar (A, B), ESP32, şönt, Q1 — yapıştırılmaz (vida, ayak, "
        "konnektör); kutunun kendi parçaları (çubuk, ayak, altlık) yapıştırılır. <b>Sıcak silikonla yapıştırılan "
        "duvar parçaları</b> (senin kararın): "
        + ", ".join(f"{r} ({v['yapistirici']})" for r, v in K.YAPISTIRMA_ISTISNA.items())
        + " — izopropil alkol ya da ısı tabancasıyla sökülür.",
```

`grep -n "Tek istisna\|tek istisna\|TEK, gerekceli" uretim/kutu.py` ile bu cümleye bakan başka bir iddia var mı bak. Varsa iddiayı yeni cümleye göre güncelle (ör. "Sıcak silikonla yapıştırılan" ifadesini arasın).

- [ ] **Step 3: Yeşil** — `python kutu.py --belge-yok`. Beklenen: iki yeni iddia `[OK]`; `sokulebilir`, `ikinci tutturma`, `eskimis istisna`, `ahsap tutucu` ve `istisnanin yapistiricisi tabloda` iddiaları da yeşil. Kesim listesi ve kütle modeli tutucu çubukları birlikte bırakır ("ahşap hacmi eşit" yeşil kalır). Toplam önceki + 2 ± (kesim/kütle döngülerinin parça sayısı değişimi). Yeni toplamı not et.

- [ ] **Step 4: Checkpoint** — `git diff --stat`.

---

### Task 3: Aynı adımların metin düzeltmeleri (spec §4.1–§4.6, §4.8)

**Files:**
- Modify: `uretim/kutu_veri.py` — alt adım 10.1 (`"no": "10.1"`), 10.2, 10.3, 10.4, 11.1 `yap`/`kontrol` listeleri

**Interfaces:**
- Consumes: `KABLO_EK` (LED katodu `J1.2.L`), `PIL_KABLOLAR` F2 kaydı (Task 1), `YAPISTIRMA_ISTISNA` (Task 2).

- [ ] **Step 1: İddialar (kırmızı)** — bölüm 10'a:

```python
    adm = {s["no"]: s for s in alt_adimlar()}
    def _metin(no):
        s = adm[no]
        return _kucuk(" ".join(s.get("yap", []) + s.get("kontrol", [])))
    ks_ = {(a, b) for a, b, *_ in K.PIL_KABLOLAR}
    D.kosul("§4.1 F2'nin cikisi F1P'nin cikis klipsine: veri ve 10.3 metni ayni",
            ("F2.2", "F1P.2") in ks_ and ("F2.2", "TP1.B+") not in ks_ and "f1p'nin çıkış klipsine" in _metin("10.3"))
    D.kosul("§4.2 hucre telleri yuvanin kendi telleri; yuva yonleri 10.2'de yazili",
            "yuvanın kendi" in _metin("10.3") and "kırmızı telinin çıktığı ucu sola" in _metin("10.2"))
    D.kosul("§4.3 GUC lambasi katodu COM jakinda (veri + 10.4 metni); 'klemens/GND noktasi' muglakligi yok",
            any(e["a"] == "LED1.K" and e["b"] == "J1.2.L" for e in K.KABLO_EK)
            and "com jakının lehim kulağına" in _metin("10.4") and "klemens/gnd noktası" not in _metin("10.4"))
    D.kosul("§4.4 10.3'te J5'ten once imkansiz 'B- <-> kart GND oter' kontrolu yok; paket-GND kontrolu 11.1'de",
            "tp1.b− ↔ kart gnd" not in _metin("10.3") and "tp4056 out− ↔ kart gnd" in _metin("11.1"))
    D.kosul("§4.5 sigorta yuvasi iki klips + <= 25 mm plaket seridi (10.2) ve veri ayni olcude",
            "iki ayrı klips" in _metin("10.2") and "25 mm" in _metin("10.2")
            and all(d["en"] <= 25.0 for d in K.DUVAR_PARCA if d["ref"] in ("F0", "F1P", "F2")))
    iz_sira = sorted(K.KABLO_UCLARI["IZ"], key=lambda u: K.KABLO_UCLARI["IZ"][u][0])
    D.kosul("§4.6 B0505S bacaklari: 10.1 veri sayfasini soyluyor, KABLO_UCLARI ayni sirada, eski cumle yok",
            all(p in _metin("10.1") for p in ("1 = +vin", "2 = −vin", "4 = −vout", "6 = +vout"))
            and iz_sira == ["IN+", "IN-", "OUT-", "OUT+"] and "gövdede basılı" not in _metin("10.1"))
    D.kosul("§4.8 MT1/MT2 kablolari tezgahta onceden lehimleniyor (10.2)", "tezgahta önce" in _metin("10.2"))
```

Run: `python kutu.py --belge-yok` → yedi iddiadan en az altısı `[!!]` (F2 verisi Task 1'de değişti; metni değil).

- [ ] **Step 2: Metinleri değiştir (`kutu_veri.py`)**

**10.1:** B0505S maddesini (`"<b>B0505S'i de tezgahta dene</b> ...`) şununla değiştir:
```python
"<b>B0505S'i de tezgahta dene</b> (duvara gitmeden). <b>Gövdede bacak adı yazmaz</b>: yazılı yüz sana dönük, "
"bacaklar aşağıdayken noktanın altındaki en soldaki bacak 1. Hi-Link veri sayfası: <b>1 = +Vin, 2 = −Vin, "
"4 = −Vout, 6 = +Vout</b> (3 ve 5 yok) — <b>yan yana duran iki bacak GİRİŞ</b>, aralıklı ikisi ÇIKIŞ. ⚠ Mornsun "
"B0505S'te 1 = GND, 2 = Vin: başka markanın şemasına bakma; girişi ters beslemek modülü bozar (−0.7 V sınırı). "
"Bacaklara krokodil takma (1–2 arası 2.5 mm): önce dört bacağa ince tel lehimle (havya ≤ 300 °C, gövdeden "
"≥ 1.5 mm), makaronla kapla — 10.2'de modül zaten böyle takılıyor. Gövdede <b>2WR3</b> yazmalı (1 W sürümü "
"açılışta yetmez, B58f). Girişine 5 V (USB şarj adaptörü ya da ayarlı MT1), çıkışında 5–7 V oku (yüksüzken "
"regülesiz modül biraz yüksek okur; kutuda MT2 onu yükler). Veri sayfası uzun süre yüksüz çalıştırmayı "
"önermiyor: oku ve kapat."
```

**10.2:** `yap` listesini şu sırayla yeniden yaz (yuva maddesi korunur, yön cümlesi eklenir; kablo bağı deliği maddesi silinir):
```python
"Arka duvar (içeriden): iki 18650 yuvası üst üste — YUVA1 alt, YUVA2 üst (konum tabloda). <b>Sıcak silikonla "
"yapıştır — cıvata yok</b> (kullanıcı kararı): önce yerini kurşun kalemle işaretle, yuvanın tabanına boydan boya "
"iki şerit çek, duvara 10 s bastır. İç kat çubuklarının arasına denk gelen yerde silikonu kalın bırak. "
"<b>Yön:</b> YUVA1'in kırmızı telinin çıktığı ucu SOLA (F1P'ye), YUVA2'ninki SAĞA (F2'ye). Hücreleri henüz "
"TAKMA (10.5). YUVA2'nin üstü kapağa 6 mm.",
"Şarj modülü (TP1) 6.0'da, kart A'dan önce takıldı; burada ona dokunma.",
"<b>Tezgahta önce:</b> MT1 ve MT2'ye kablolarını lehimle (TP1 gibi; kutuda pedlere havya rahat girmez): teli "
"kartın parça yüzünden sok, alttan lehimle, taşan ucu kes — modülün arkası duvara düz otursun. Uçları etiketle. "
"Hangi pede ne geldiği ve kesim boyları 10.3 / 10.4'ün kablo tablosunda ve çiziminde (numaralı). MT2'nin IN− "
"ucuna '−12 tarafı' yaz.",
"<b>Sigorta yuvası = iki ayrı klips</b> (FUS009), tek gövde değil: iki klipsi kart A'dan artan plaketten "
"kestiğin en fazla <b>25 mm</b>'lik bir şeride lehimle — önce sigortayı iki klipse tak, bacakları şeride geçir, "
"lehimle; sigorta aralığı kendiliğinden doğru olur. Her klipsin iki bacağını altta birleştir; teli klipsin "
"yanındaki boş delikten ön yüzden sok, arkada klips bacağına lehimle. Üç şerit: F0, F1P, F2. (Kapaklı KF-03 "
"denendi: 27 × 14 mm ölçüsüyle yerleşime sığmıyor — F1P kart A'nın altına giriyor, kapaklar üst üste geliyor.)",
"<b>Tutturma — sıcak silikon</b> (kullanıcı kararı 2026-09-30): MT1, MT2, B0505S, 680 µF, KL ve üç sigorta "
"şeridi duvara sıcak silikonla; sökmek için izopropil alkol damlat, plastik kartla kaldır. Silikon PCB'nin "
"ARKASINA ya da kenarına — çipin ve bobinin üstüne değil (ısınan yerler). MT1/MT2'nin trimpotu içe ve "
"erişilebilir kalsın. Kartlar, ESP32, şönt ve Q1 yapıştırılmaz.",
"MT1 ve MT2 arka duvarın solunda, üst üste (x 43–79; MT1 z 24, MT2 z 47). MT1'in OUT pedleri SOLA (F0 ve "
"B0505S), MT2'nin IN pedleri SOLA (B0505S ve 680 µF).",
"<b>B0505S (IZ)</b> MT2'nin soluna, bacaklar aşağı. ⚠ Bu modül kutunun <b>iki toprağını ayıran TEK parça</b>: "
"giriş tarafı (1 +Vin, 2 −Vin) ile çıkış tarafı (4 −Vout, 6 +Vout) hiçbir telle birleşmesin.",
"<b>MT2'nin giriş kondansatörü (CB, 680 µF 16 V, C042)</b> MT2'nin üstüne, yatık. Bacaklarını MT2'nin giriş "
"pedlerine lehimle: uzun bacak IN+, ⚠ <b>şeritli bacak EKSİ → IN−</b>.",
"<b>24 V iç klemensi (KL, CON007)</b> B0505S'in üstüne; vidalar içe. Hangi vidanın + olduğunu kalemle yaz: "
"10.4'te MT2'nin çıkışı ve kartın 24 V telleri aynı kutupla buraya vidalanacak.",
"<b>Analog sigortası F0</b> B0505S'in altına, MT1'in soluna (konum tabloda); içine 1 A hızlı cam sigorta "
"(FUS003) — şimdilik <b>TAKMA</b>, 10.5'te ilk enerji sırası için çıkarılmış duracak.",
"Hücre sigortaları <b>F1P ve F2</b> en alt sırada (konum tabloda); içlerine <b>{pil_sigorta}</b> cam sigorta "
"(FUS004). Anma neden bu kadar yüksek: sigorta hücrenin artısında, yani şarj akımı da buradan geçiyor "
"({sarj_akimi}; tek hücre takılıysa tamamı) — daha küçüğü ilk şarjda atar.",
```
`kontrol`a ekle: `"Silikon soğuyunca modülleri ve yuvaları elle it; oynamamalı."` ve `"B0505S'in giriş (1, 2) ve çıkış (4, 6) telleri arasında bip: ötmemeli."`

**10.3:** "Aşağıdaki tabloya göre; hücreler TAKILI DEĞİLKEN ..." maddesinde H1+/H2+ cümlesinden sonra şunu ekle:
```python
"Hücre telleri <b>yuvanın kendi telleri</b>: kırmızı (+, yaysız uç) doğrudan sigorta klipsine, siyah TP4056 "
"B−'ye. F2'nin çıkışı arka duvar boyunca <b>F1P'nin çıkış klipsine</b> gelir; TP4056 B+'ya oradan tek tel "
"gider (iki hücre burada paralel). 2. yuvanın siyah teli yetmez — tablodaki kesim boyuna göre ek."
```
PİL anahtarı maddesinin sonuna: `" KTS102'nin <b>orta</b> bacağı TP4056 OUT+'ya; öbür tel, anahtar AÇ konumundayken orta bacakla <b>öten</b> dış bacağa (multimetreyle bul)."`
`kontrol`un ilk maddesini (`"Hücreler takılı değilken: TP1.B− ↔ kart GND (C29): <b>ötmeli</b> ..."`) şu ikisiyle değiştir:
```python
"1. ve 2. yuvanın siyah teli ↔ TP4056 B−: ötmeli. F1P'nin ve F2'nin çıkış klipsi ↔ TP4056 B+: ötmeli.",
"Paket eksisi kart GND'ye J5 kablosuyla bağlanır — o kontrol 11.1'de (şimdi ötmemesi NORMAL: FS8205'in "
"gövde diyotları hücresizken B− ile OUT−'yu da ayrı tutar).",
```

**10.4:** "GÜÇ lambası" maddesini şununla değiştir:
```python
"<b>GÜÇ lambası:</b> 10 kΩ direnci (R060) LED'in <b>uzun bacağına</b> lehimle, makaronla kapat; direncin öbür "
"ucu <b>klemensin ARTI</b> ucuna (KL.+ = +12 rayı). LED'in kısa bacağı (katot) <b>COM jakının lehim kulağına</b> "
"(= kart GND; LED'den 36 mm). ⚠ MT1'in eksisine bağlama: o nokta kart GND'ye ancak 11.1'deki J5 ile bağlanır, "
"10.5'te lamba yanmaz. ⚠ Klemensin EKSİ ucuna da bağlama: −12 rayıdır, 7912 o yönde akım veremez."
```

**11.1:** `kontrol`a ekle:
```python
"J5 takılınca, hücreler takılı değilken: TP4056 OUT− ↔ kart GND (C29): ötmeli (paket eksisi = kart GND; "
"bağ ESP32'nin GND'si ve J5 üzerinden).",
```

`kutu.py`'deki pil grafı yorumuna (PIL_IC_BAG'den önce ya da `pil_grafi` docstring'ine) tek satır ekle:
`# ("ESP32.GND", "KART_GND") J5 TAKILI varsayar (11.1); 10.3'te paket-GND bagi fiziksel olarak YOK (B73 §4.4).`

- [ ] **Step 3: Yeşil** — `python kutu.py --belge-yok`. Yedi iddia `[OK]`, öncekiler yeşil. 10.2'deki kablo bağı deliği maddesi silinince `{bag_delik}` yer tutucusunu kullanan bir iddia kırmızı olabilir. `grep -n "bag_delik\|Kablo bağı delikleri" uretim/kutu.py` ile bul. İddia "10.2 kablo bağı deliğini söylüyor" ise kaldır; KABLO_BAGI artık yalnız kapakta/kızakta kullanılıyor. Yeni toplamı not et.

- [ ] **Step 4: Checkpoint** — `git diff --stat`.

---

### Task 4: 2B çizimler — içeriden arka duvar, kuşbakışı kablolar, numaralı tablo, bilgi kartı

**Files:**
- Modify: `uretim/kutu.py` (`bi_kablo` → `bi_duvar`'ın altına; `_kablo_svg`, `ciz_arka_ic` → `ciz_yerlesim`'in üstüne; `ciz_yerlesim(..., kablo_adim=None)`; `cizimler()` sonu; `kablo_b73_tablosu` → `kablo_tablosu`'nun altına; adım derlemesindeki `pil_kablo` tablosu ~4182)
- Modify: `uretim/kutu_3b.py` (PANEL_CSS: kablo vurgusu, satır, rozet)

**Interfaces:**
- Consumes: Task 1'in bütün fonksiyonları.
- Produces: `bi_kablo(k: dict) -> str` (anahtar `t:<a>|<b>`), `ciz_arka_ic(vurgu: set[str], adim_no: str) -> str`, `kablo_b73_tablosu(no: str) -> str`, SVG grupları `<g class="bi kb" data-bi="t:...">`, tablo satırları `<tr class="bi-satir" data-bi="t:...">`.

- [ ] **Step 1: İddialar (kırmızı)** — bölüm 10'a:

```python
    for no in ("10.3", "10.4", "11.1"):
        s_ = adm[no]
        sv = cizimler(s_)
        tb = kablo_b73_tablosu(no)
        beklenen = {f"t:{k['a']}|{k['b']}" for k in adim_kablolari(no)}
        cizimde = {html_unescape(x) for x in re.findall(r'class="bi kb" data-bi="([^"]+)"', sv)}
        tabloda = {html_unescape(x) for x in re.findall(r'class="bi-satir" data-bi="([^"]+)"', tb)}
        rozet = len(re.findall(r'class="kno-r"', sv))
        D.kosul(f"{no}: cizimdeki, tablodaki ve listedeki kablolar AYNI kume; her kablonun bir rozeti var",
                beklenen <= cizimde and tabloda == beklenen and rozet >= 2 * len(beklenen),
                f"liste {len(beklenen)} · cizim {len(cizimde & beklenen)} · tablo {len(tabloda)} · rozet {rozet}")
    D.kosul("Arka duvar kablo cizimi ICERIDEN (aynasiz): SARJ ovali USB'nin solunda",
            (lambda sv: sv.find(">ŞARJ<") < sv.find(">USB<"))(ciz_arka_ic(set(), "10.3")))
    kart_t = [k for k in _BILGI if k.startswith("t:")]
    D.kosul("Her kablonun karti kesim boyu, yol ve '±3 mm tahmin' notu tasiyor",
            kart_t and all(_BILGI[k]["r"][0][0] == "Kesim boyu" and "±3 mm" in _BILGI[k].get("n", "")
                           and any(r[0] == "Yol" for r in _BILGI[k]["r"]) for k in kart_t), f"{len(kart_t)} kart")
```

(`rozet >= 2 * len` çünkü her adım iki çizimde (iç arka duvar + kuşbakışı) rozet basar.)

Run: `python kutu.py --belge-yok` → `NameError: kablo_b73_tablosu`.

- [ ] **Step 2: `bi_kablo` (bi_duvar'ın altına)**

```python
def bi_kablo(k: dict) -> str:
    """B73: kablo karti — cizim, 3B ve tablo satiri ayni anahtara bakar."""
    yol = guzergah(k)
    return _bilgi(f"t:{k['a']}|{k['b']}", f"Kablo {k['no']}: {uc_adi(k['a'])} → {uc_adi(k['b'])}",
                  f"kablo · {K.KABLO_ROL_AD[k['rol']]}", [
        ("Kesim boyu", "kesilmez (kendi bacağı)" if k["rol"] == "bacak" else f"{kesim_cm(yol)} cm", 1),
        ("Yol", k["soz"]),
        ("Güzergah", f"{guzergah_boyu(yol):.0f} mm"),
        ("Kesit", k["kesit"]),
        ("Adım", _adim_etiket(k["adim"])),
    ], f"{k['not']} · Uç yerleri ±3 mm tahmin — ped adını modülün üstünden oku.")
```

- [ ] **Step 3: `_kablo_svg` ve `ciz_arka_ic` (ciz_yerlesim'in üstüne)**

```python
def _adim_sirasi() -> dict[str, int]:
    return {s["no"]: i for i, s in enumerate(alt_adimlar())}


def _kablo_svg(k: dict, noktalar: list[tuple[float, float]], soluk: bool) -> str:
    """Bir kablonun 2B izdusumu: polyline + numara rozeti (soluk = onceki adim, rozetsiz)."""
    renk = KABLO_RENK[k["rol"]]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in noktalar)
    g = _bi_ac(bi_kablo(k)).replace('class="bi"', 'class="bi kb"', 1)
    g += (f'<polyline points="{pts}" fill="none" stroke="{renk}" stroke-width="3" '
          f'stroke-linejoin="round" stroke-linecap="round" opacity="{0.22 if soluk else 1.0}"/>')
    if not soluk:
        p, q = max(zip(noktalar, noktalar[1:]), key=lambda s: math.dist(s[0], s[1]))
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        g += (f'<circle class="kno-r" cx="{mx:.1f}" cy="{my:.1f}" r="8" fill="{renk}" stroke="#fff" stroke-width="1.2"/>'
              + _yazi(mx, my + 3.5, str(k["no"]), 9, "#fff", "middle", True))
    return g + "</g>"


def ciz_arka_ic(vurgu: set[str], adim_no: str) -> str:
    """B73: arka duvar ICERIDEN (jak tarafindan bakis, x soldan, AYNASIZ) + bu adima kadarki
    kablolar (onceki adimlar soluk). Arka duvara inmeyen uclar 'ön →' yazisi alir."""
    kb, h = K.KUTU, hesap()
    olc, sol, ust = 3.0, 30.0, 26.0
    W, H = kb["ic_en"], h["ic_yuk"]
    gen, yuk = sol * 2 + W * olc, ust + H * olc + 110

    def X(x):
        return sol + x * olc

    def Z(z):
        return ust + (H - z) * olc
    o = [_dikdortgen(sol, ust, W * olc, H * olc, AHSAP["on"], AHSAP["cizgi"], 0.55)]
    for x in panel_ogeleri("arka"):
        if x["tip"] == "yuva":
            o.append(_dikdortgen(X(x["x"] - x["yuva_en_mm"] / 2), Z(x["z"] + x["delik_mm"] / 2),
                                 x["yuva_en_mm"] * olc, x["delik_mm"] * olc, "var(--yz)", "var(--m3)", 0.9, 6)
                     + _yazi(X(x["x"]), Z(x["z"]) + 4, x["etiket"], 9, "var(--m2)"))
    A = next(p for p in K.IC_PARCA if p["ref"] == "A")
    za = next(a["yuk"] for a in ayaklar() if a["sahip"] == "A")
    o.append(_cizgi(X(A["x"]), Z(za), X(A["x"] + A["en"]), Z(za), "var(--m3)", 1.4, kesik=True)
             + _yazi(X(A["x"] + A["en"] / 2), Z(za) + 12, "kart A'nın arka kenarı (duvardan 12 mm önde)", 9, "var(--m3)"))
    e = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
    ze = next((a["yuk"] for a in ayaklar() if a["sahip"] == "ESP32"), 0.0)
    o.append(_dikdortgen(X(e["x"]), Z(ze + e["yuk"]), e["en"] * olc, e["yuk"] * olc, "none", "var(--m3)", 0.8)
             + _yazi(X(e["x"] + e["en"] / 2), Z(ze + e["yuk"]) - 4, "ESP32 (önde)", 9, "var(--m3)"))
    for d in [q for q in duvar_parcalari() if q["duvar"] == "arka"]:
        v = d["ref"] in vurgu
        o.append(_bi(bi_duvar(d), _dikdortgen(X(d["x"]), Z(d["z"] + d["yuk"]), d["en"] * olc, d["yuk"] * olc,
                                              "#3c6e71", "#f2c14e" if v else "#1f3f41", 0.85)
                     + _yazi(X(d["x"] + d["en"] / 2), Z(d["z"] + d["yuk"] / 2) + 4, d["ref"], 10, "#fff", "middle", v)))
    sira = _adim_sirasi()
    for k in kablo_listesi():
        if sira[k["adim"]] > sira[adim_no]:
            continue
        yol = guzergah(k)
        o.append(_kablo_svg(k, [(X(p[0]), Z(p[2])) for p in yol], soluk=k["adim"] != adim_no))
        if k["adim"] == adim_no:
            for u, p in ((k["a"], yol[0]), (k["b"], yol[-1])):
                if p[1] > 45:
                    o.append(_yazi(X(p[0]), Z(p[2]) - 10, f"ön → {uc_adi(u)}", 8, KABLO_RENK[k["rol"]]))
    ly = ust + H * olc + 22
    for i, (r, ad) in enumerate(K.KABLO_ROL_AD.items()):
        lx, lyy = sol + (i % 3) * 215, ly + (i // 3) * 16
        o.append(_cizgi(lx, lyy, lx + 26, lyy, KABLO_RENK[r], 3) + _yazi(lx + 32, lyy + 4, ad, 10, "var(--m2)", "start"))
    o.append(_yazi(sol + W * olc / 2, ly + 46, "arka duvar İÇERİDEN · jak tarafından bakış · x soldan, z yerden · "
                   "soluk = önceki adımların kabloları · uç yerleri ±3 mm tahmin", 10, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Arka duvar içeriden — kablolar")
```

- [ ] **Step 4: Kuşbakışında kablolar** — `ciz_yerlesim` imzası `def ciz_yerlesim(vurgu: set[str], direk_vurgu: bool = False, kablo_adim: str | None = None) -> str:`. Arka panel öğelerinin döngüsünden sonra, alt yazılardan önce:

```python
    if kablo_adim:                                   # B73: bu adima kadarki kablolar, kusbakisi
        sira = _adim_sirasi()
        for k in kablo_listesi():
            if sira[k["adim"]] <= sira[kablo_adim]:
                o.append(_kablo_svg(k, [(sol + p[0] * olc, ust + p[1] * olc) for p in guzergah(k)],
                                    soluk=k["adim"] != kablo_adim))
```

- [ ] **Step 5: `cizimler()`'e bağla** — `if not c: return ""` satırının hemen önüne:

```python
    if adim_kablolari(s["no"]):                      # B73: kablo adiminda ana cizim icten arka duvar
        c = ([("Arka duvar — içeriden bakış: bu adımın kabloları", ciz_arka_ic(vurgu, s["no"])),
              ("Kuşbakışı — kablolar", ciz_yerlesim(vurgu, kablo_adim=s["no"]))]
             + [x for x in c if not x[0].startswith(("Kuşbakışı", "Arka duvar"))])
```

- [ ] **Step 6: Tablo** — `kablo_tablosu`'nun altına:

```python
def kablo_b73_tablosu(no: str) -> str:
    """B73: adimin kablolari, cizimdeki numarayla. Satir data-bi ile karta ve cizime bagli."""
    bas = ("No", "Nereden", "Nereye", "Yol", "Kesim", "Kesit", "Not")
    sat = []
    for k in adim_kablolari(no):
        yol = guzergah(k)
        kesim = "—" if k["rol"] == "bacak" else f"{kesim_cm(yol)} cm"
        sat.append(f'<tr class="bi-satir" data-bi="{E(bi_kablo(k))}" tabindex="0">'
                   f'<td><span class="kno" style="background:{KABLO_RENK[k["rol"]]}">{k["no"]}</span></td>'
                   f"<td><b>{E(uc_adi(k['a']))}</b></td><td><b>{E(uc_adi(k['b']))}</b></td>"
                   f"<td>{E(k['soz'])}</td><td><b>{kesim}</b></td><td>{E(k['kesit'])}</td>"
                   f"<td><span class='kucuk'>{E(k['not'])}</span></td></tr>")
    return ("<table class='kablo-tablo'><tr>" + "".join(f"<th>{b}</th>" for b in bas) + "</tr>"
            + "".join(sat) + "</table>")
```

Adım derlemesinde (`if s["tur"] == "pil_kablo":` bloğu) eski `_tablo(("Nereden", "Nereye", "Tür", "Not"), ...)` çağrısını kaldır. "Uç adları: ..." paragrafını tut. Bloğun ÜSTÜNE, her adım için:

```python
    if adim_kablolari(s["no"]):
        ic.append("<h4>Kablolar — çizimdeki numaralarla (satıra dokun: çizimde yanar)</h4>")
        ic.append(kablo_b73_tablosu(s["no"]))
```

`grep -n "Kablolar —" uretim/kutu.py` ile eski tabloya bakan bir iddia var mı bak; varsa yeni tabloya (`kablo_b73_tablosu`) çevir.

- [ ] **Step 7: CSS (`kutu_3b.py` PANEL_CSS, `svg .bi.secili ...` satırının altına)**

```css
svg .bi.kb:hover>polyline,svg .bi.kb:focus>polyline,svg .bi.kb.secili>polyline{stroke-width:6px;opacity:1}
svg .bi.kb.secili>circle{stroke:#2ec4b6;stroke-width:3px}
.kno{display:inline-block;min-width:20px;padding:1px 5px;border-radius:10px;color:#fff;font-weight:700;text-align:center}
tr.bi-satir{cursor:pointer}
tr.bi-satir:hover td,tr.bi-satir:focus td,tr.bi-satir.secili td{background:rgba(46,196,182,.16)}
```

- [ ] **Step 8: Yeşil** — `python kutu.py --belge-yok`. Üç adım iddiası, iç bakış iddiası ve kart iddiası `[OK]`. Bölüm 9'daki "sayfadaki her data-bi'nin kartı gömülü" iddiası da yeşil kalmalı (`bi_kablo` kartı `_BILGI`'ye yazıyor). Sonra `python kutu.py` → `BELGELER/8-kutu.html` üretilir. Tarayıcıda `#a10.3`'ü aç ve gözle bak: ŞARJ solda, kablolar renkli ve numaralı, lejant okunuyor.

- [ ] **Step 9: Checkpoint** — `git diff --stat`.

---

### Task 5: 3B — kablolar ince bloklar zinciri

**Files:**
- Modify: `uretim/kutu.py` `sahne()` (duvar parçaları döngüsünün altına)
- Modify: `uretim/kutu_3b.py` (`GRUP` ve `SIRA` sözlükleri)

**Interfaces:**
- Consumes: `kablo_listesi`, `guzergah`, `bi_kablo`, `KABLO_RENK`.
- Produces: `sahne()` blokları `g == "kablo"`, `k == "t:<a>|<b>"`, `gor == ix[adim]`.

- [ ] **Step 1: İddia (kırmızı)** — bölüm 10'a:

```python
    sah_k = [b for b in sahne() if b["g"] == "kablo"]
    ix3 = {s["no"]: i for i, s in enumerate(alt_adimlar())}
    bozuk3 = []
    for k in kl:
        bl = [b for b in sah_k if b["k"] == f"t:{k['a']}|{k['b']}"]
        toplam = sum(max(b["dx"], b["dy"], b["dz"]) - 2.0 for b in bl)
        if not bl or abs(toplam - guzergah_boyu(guzergah(k))) > 0.6 or any(b["gor"] != ix3[k["adim"]] for b in bl):
            bozuk3.append(k["no"])
    D.kosul("3B: her kablo guzergahiyla ayni boyda bloklar zinciri ve kendi adiminda beliriyor",
            not bozuk3, f"bozuk: K{bozuk3}" if bozuk3 else f"{len(sah_k)} blok")
```

Run → `[!!]` (sahnede kablo bloğu yok).

- [ ] **Step 2: `sahne()`** — `for d in duvar_parcalari():` döngüsünden sonra:

```python
    for k in kablo_listesi():                               # B73: kablolar — eksen eksen ince bloklar
        gor = ix[k["adim"]]
        yol = guzergah(k)
        for p, q in zip(yol, yol[1:]):
            x0, y0, z0 = (min(p[i], q[i]) - 1.0 for i in range(3))
            dx, dy, dz = (abs(p[i] - q[i]) + 2.0 for i in range(3))
            blok(f"Kablo {k['no']}", x0, cev(y0, dy), z0, dx, dy, dz, KABLO_RENK[k["rol"]], "kablo", gor, [gor],
                 k=bi_kablo(k))
```

- [ ] **Step 3: `kutu_3b.py`** — `var GRUP = {...}` sözlüğüne `kablo: 'kablo'` ekle; `var SIRA = {...}` sözlüğüne `kablo: 0` ekle (N/P gezintisinde bu adımın kabloları parçalarla birlikte önce gelir).

- [ ] **Step 4: Yeşil** — `python kutu.py --belge-yok`. Yeni iddia `[OK]`; bölüm 9'daki "3B'deki her blogun bir bilgi karti var" ve "Verideki her parca 3B'de" iddiaları yeşil. Sonra `python kutu.py`, tarayıcıda 10.4'ü aç, 3B'de kabloların göründüğüne ve üzerine gelince kart açıldığına bak.

- [ ] **Step 5: Checkpoint** — `git diff --stat`.

---

### Task 6: Tablo ↔ çizim bağı (JS) ve gerçek tarayıcı testi

**Files:**
- Modify: `uretim/kutu_3b.py` `JS_IPUCU` (`ipSabitTemizle`, `click` dinleyicisi)
- Modify: `uretim/kutu_ipucu_test.py` (`main()` sonuna B73 bölümü; `merkez()` seçicisine `polyline`)

**Interfaces:**
- Consumes: `tr.bi-satir[data-bi]`, `svg g.kb[data-bi]` (Task 4).
- Produces: JS `isaretle(k)`: aynı `data-bi`'li bütün öğelere `secili` ekler, ilk görünür SVG kopyasını görünüme kaydırır.

- [ ] **Step 1: Test (kırmızı)** — `kutu_ipucu_test.py`:

`merkez()` içinde `var s = L[0].querySelector('rect,circle,polygon') || L[0];` → `var s = L[0].querySelector('rect,circle,polygon,polyline') || L[0];`

`main()`'in sonunda, tarayıcı kapanmadan önce:

```python
        # ── B73: kablolar — uzerine gel (kart) ve tablo satiri (cizimde secili) ──
        adima_git(t, "10.4")
        m = merkez(t, "svg g.kb")
        kosul("B73: 10.4'te çizimde kablo var", m is not None)
        if m:
            fare(t, m["x"], m["y"])
            t.bekle(0.2)
            kk = kart(t)
            kosul("B73: kablonun üzerine gelince kablo kartı açılıyor",
                  kk["gorunur"] and kk["k"].startswith("t:") and "→" in kk["baslik"]
                  and any(r[0] == "Kesim boyu" for r in kk["satir"]), str(kk)[:160])
            tus(t, "Escape", 27)
        r = merkez(t, "tr.bi-satir")
        kosul("B73: 10.4'te kablo tablosu var", r is not None)
        if r:
            tikla(t, r["x"], r["y"])
            t.bekle(0.3)
            d = t.js("""(function(){ var tr = document.querySelector('tr.bi-satir.secili'); if (!tr) return null;
              var k = tr.getAttribute('data-bi');
              var n = document.querySelectorAll('svg [data-bi="' + CSS.escape(k) + '"].secili').length;
              var i = document.getElementById('ipucu');
              return {k: k, svg: n, kart: !i.hidden && i.dataset.k === k}; })()""")
            kosul("B73: tablo satırına dokununca kart açılıyor ve çizimdeki aynı kablo seçili",
                  bool(d) and d["svg"] >= 1 and d["kart"], str(d))
            tus(t, "Escape", 27)
            n_sec = t.js("document.querySelectorAll('.secili').length")
            kosul("B73: Esc bütün seçimleri temizliyor (satır + çizim)", n_sec == 0, str(n_sec))
```

Run: `cd projeler/olcum-karti/uretim && python kutu_ipucu_test.py` → yalnız "tablo satırına dokununca ... seçili" ve "Esc bütün seçimleri" `[!!]`. Satıra tıklayınca kart açılır ama çizimdeki eşi seçilmez; Esc yalnız satırı temizler.

- [ ] **Step 2: JS** — `JS_IPUCU` içinde `ipSabitTemizle`'yi ve `click` dinleyicisindeki seçme satırını değiştir:

```js
 function isaretle(k){
   var s = '[data-bi="' + (window.CSS && CSS.escape ? CSS.escape(k) : k) + '"]';
   var ilk = null;
   [].forEach.call(document.querySelectorAll(s), function(e){
     e.classList.add('secili');
     if (!ilk && e.closest('svg') && e.getClientRects().length && !e.closest('details:not([open])')) ilk = e;
   });
   return ilk;
 }
 function ipSabitTemizle(){
   [].forEach.call(document.querySelectorAll('.secili'), function(e){ e.classList.remove('secili'); });
   if (ipSabit && ipSabit.el) ipSabit.el.removeAttribute('aria-describedby');
   ipSabit = null;
 }
```

`click` dinleyicisinde `el.classList.add('secili'); el.setAttribute('aria-describedby', 'ipucu');` satırını şununla değiştir:

```js
       var esi = isaretle(ipSabit.k); el.setAttribute('aria-describedby', 'ipucu');
       if (el.tagName === 'TR' && esi) esi.scrollIntoView({block: 'nearest', behavior: 'instant'});
```

- [ ] **Step 3: Yeşil** — `python kutu_ipucu_test.py` → bütün iddialar `[OK]` (eski 30 + yeni 6). `python kutu.py --belge-yok` yeşil.

- [ ] **Step 4: Checkpoint** — `git diff --stat`.

---

### Task 7: Mutasyonlar, zincir, sayım kilidi, günlük, belge

**Files:**
- Modify: `uretim/mutasyon.py` (`MUTASYONLAR`, B50 ve B57 grupları)
- Modify: `uretim/beklenen_sayim.json` (yalnız `"B9  Malzeme + kurulum kilavuzu"`'nun 3. çifti)
- Modify: `DEVIR.md` (5.12.73 B73), `BELGELER/8-kutu.html` (üretilir)
- Modify: hafıza notu `olcum-karti-kurulum-ilerleme.md` ("PLANA HENÜZ İŞLENMEDİ"den biten maddeleri düş)

- [ ] **Step 1: Mutasyonları ekle** — `MUTASYONLAR`'da B50 grubunun sonuna:

```python
    # ── B73 · kablo guzergahi
    ("B50", "kutu.py", "uretim/kutu_veri.py", '("H2-", "TP1.B-"): {"ara": [', '("H2-", "TP1.B-"): {"ara_yok": [',
     "guzergah istisnasi silinirse varsayilan yol ESP32'nin icinden gecer: carpisma iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"MT1": {"OUT+": (2.0, 14.0, 12.0)', '"MT1": {"OUT+": (60.0, 14.0, 12.0)',
     "terminal parcasinin disina kayarsa 'terminal kendi govdesinde' kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", "KABLO_PAY = 1.15", "KABLO_PAY = 1.0",
     "kesim payi kalkarsa 'kesim >= guzergah x 1.1' kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '("F2.2", "F1P.2", "pil",', '("F2.2", "TP1.B+", "pil",',
     "F2 eski uca donerse veri-metin (§4.1) ve bayat KABLO_YOL iddialari kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '{"a": "LED1.K", "b": "J1.2.L"', '{"a": "LED1.K", "b": "MT1.OUT-"',
     "LED katodu MT1 eksisine giderse 10.5'te yanmaz: §4.3 iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu.py", 'KABLO_E12 = frozenset({"IZ.OUT-", "MT2.IN-", "MT2.OUT-", "KL.-", ',
     'KABLO_E12 = frozenset({"IZ.OUT-", "MT2.IN-", "MT2.OUT-", ',
     "-12 kablosu yanlis renge duserse rol-graf capraz iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu.py", '"kablo", gor, [gor],', '"kablo", gor + 1, [gor],',
     "3B'de kablo yanlis adimda belirirse 3B iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", '"IN+": (3.0, 7.0, 0.0), "IN-": (5.5, 7.0, 0.0)',
     '"IN+": (5.5, 7.0, 0.0), "IN-": (3.0, 7.0, 0.0)',
     "B0505S giris bacaklari yer degistirirse (Mornsun sirasi) §4.6 iddiasi kirmizi"),
    ("B50", "kutu.py", "uretim/kutu_veri.py", 'for _r in ("MT1", "MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"):',
     'for _r in ("MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"):',
     "MT1 yapistirma istisnasindan duserse metin silikon dedigi icin sokulebilir + karar iddiasi kirmizi"),
```

B57 grubunun sonuna:

```python
    ("B57", "kutu_ipucu_test.py", "uretim/kutu_3b.py",
     "       var esi = isaretle(ipSabit.k); el.setAttribute('aria-describedby', 'ipucu');",
     "       var esi = null; el.classList.add('secili'); el.setAttribute('aria-describedby', 'ipucu');",
     "tablo satiri cizimdeki kabloyu secmezse B73 tarayici iddiasi kirmizi"),
```

- [ ] **Step 2: Mutasyonları koş**

Run: `cd projeler/olcum-karti/uretim && python mutasyon.py --adim B50`
Expected: bütün B50 mutasyonları YAKALANDI (önceki sayı + 9). Bir mutasyon "ATLANDI" derse eşleşme dizesi kaynakta yok demektir: o dizeyi kaynaktan birebir kopyala. "KAÇTI" derse iddia zayıftır: iddiayı güçlendir, eşiği gevşetme.
Run: `python mutasyon.py --adim B57` → hepsi YAKALANDI (önceki + 1).

- [ ] **Step 3: Zincir ve sayım kilidi**

Run: `python kutu.py` (yeşil olmalı ve belgeyi yazar). `kutu.py`'nin son toplamını not et (N).
`beklenen_sayim.json`'da `"B9  Malzeme + kurulum kilavuzu"` değerinin 3. çiftini `[N, N]` yap. Öbür çiftlere ve öbür adımlara **dokunma**. B70'teki gibi tam `--sayim-kilidi-yaz` YOK: ağaçta 1D'nin ve kullanıcının commit'lenmemiş işi var.
Run: `python dogrula3.py` (~20 dk). Expected: B9 yeşil. Başka adımlar bu işten önce de kırmızıysa (ör. 1D dalının adımları) onları raporla, düzeltmeye kalkma.

- [ ] **Step 4: DEVIR ve hafıza**

`DEVIR.md`'ye 5.12.72'den sonra `#### 5.12.73 ✅ B73 — KABLO GÜZERGAHI (kutu belgesi, 2026-10-01)` bölümü ekle: istek (kullanıcı cümleleri), kararlar K1–K12, prototipte bulunanlar, iddialar, sayılar ve açık kalanlar. Ölçülecekler:
- 26 kablo, HV en yakın 58.2 mm.
- 0 çarpışma için 13 güzergah istisnası. Varsayılan yolla gövdeye giren: H2−, F2.2→F1P.2, ESP32 J5/CAL, KL→C34/C36, PİL anahtarı.
- TP1 uçları tel ucu, terminal sapması 15 mm.
- §4 düzeltmeleri; 10.3'teki "B− ↔ GND öter" kontrolü J5'ten önce fiziksel olarak imkânsızdı.
- Faz 2: 5–9 adımları; önce gerçek yerleşim (güç bloğu sağ duvarda, Q1 kafesi, kart B 90° dönük).

Hafıza notu `olcum-karti-kurulum-ilerleme.md`'de "PLANA HENÜZ İŞLENMEDİ" listesinden B73'ün kapattığı maddeleri düş (F2, LED, 10.3 kontrolü, sigorta klipsi, B0505S, yapıştırma, MT ön-lehim); kalanları (7.1/7.2 metinleri, HB950 yeri, Q1/kart B gerçek yeri, U3 bacak notu) bırak.

- [ ] **Step 5: Son doğrulama** — `python kutu.py` yeşil · `python kutu_ipucu_test.py` yeşil · `python mutasyon.py --adim B50` ve `--adim B57` hepsi yakalandı. Belgeyi aç, kullanıcıya göster: `BELGELER/8-kutu.html#a10.3`, `#a10.4`, `#a11.1`. `git diff --stat` (commit yok).
