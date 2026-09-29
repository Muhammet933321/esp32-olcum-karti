# Alt proje 1A-1 — Kayıt motoru (saf C + Python çözücü) Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kartın kayıt motorunu (kayıt biçimi, nokta biriktirici, NOR flaş günlüğü, oturum yazıcı) platformdan bağımsız C başlıkları olarak yazmak. Bunu AVR emülatöründe, emüle NOR flaş üstünde, rastgele elektrik kesmeleri dahil doğrulamak. Aynı baytları çözen bağımsız bir Python çözücü eklemek.

**Architecture:** Dört başlık dosyası katman katman birbirine dayanır: `kayit_bicim.h` (baytların tek tanımı) → `kayit_nokta.h` (ham örnek → nokta) ve `kayit_gunluk.h` (flaşta halka günlük) → `kayit_oturum.h` (oturum kayıtlarını günlüğe yazar). Flaş erişimi işlev işaretçileriyle soyutlanır. Kartta `esp_partition_*` (1A-2), testte emüle NOR kullanılır. Böylece testte koşan kod, kartta koşacak kodun kendisidir. Python tarafı (`kopru/kayit_bicim.py`) aynı baytları bağımsız çözer; iki taraf ortak test vektörleriyle sınanır.

**Tech Stack:** C (gnu11, C++11 uyumlu; testte avr-gcc 7.3, 1A-2'de ESP32), Python 3.14 (yalnız stdlib), projenin AVR emülatörü (`uretim/avr/`).

**Spec:** [tasarim/2026-09-29-yazilim-sistemi.md](2026-09-29-yazilim-sistemi.md) (§5 kayıt modeli ve eşitleme, §7 kalibrasyon, §10 doğrulama, §11 riskler)

## Bu plan neyi kapsar

Alt proje 1 (kart kaydedici) beş dilime bölündü. Bu plan **yalnızca 1A-1**'i kapsar.

| Dilim | İçerik | Karta dokunur mu |
|---|---|---|
| **1A-1 (bu plan)** | Kayıt biçimi, noktacı, günlük, oturum yazıcı, Python çözücü, elektrik kesme testi, zincir adımı B71 | **Hayır**: yalnızca bilgisayarda test |
| 1A-2 | Bölüm tablosu · çekirdek 0 kayıt görevi · `G` komutu ve durum satırı · `/kayit/liste`, `/kayit/veri` · NTP · eşitleme istemcisi · tezgah ölçümleri | Evet |
| 1B | Kalibrasyon geçmişi | Evet |
| 1C | Pil testi ve osiloskop günlüğü oturum türleri · ayrıntılı kip · zamanlanmış kayıt · ad/etiket/not | Evet |
| 1D | Eşleştirme + imzalı istekler (ChaCha20-Poly1305 kendi uygulamamız: Arduino çekirdeğinin mbedTLS'inde kapalı) | Evet |
| 1E | MQTT + vasiyet · mDNS servis ilanı | Evet |

Firmware (`olcum-karti-a3.ino`) bu planda **değişmez**.

## Bu planın kilitlediği biçim kararları

- **Kayıt** = 16 bayt başlık + yük + 0..3 bayt sıfır dolgu (4'ün katı). Başlık alanları: imza `0xA5` · tür · yük_bayt · sıra · oturum · CRC-32 (zlib ile aynı; dolgu CRC'ye girmez).
- **Sıra** kartın bütün kayıtları için artar ve **asla tekrar verilmez**. Biçimlendirmeden sonra da vermemesi için `kg_ac(sira_taban)` alır; taban 1A-2'de NVS'ten gelir.
- **Oturum kimliği** = oturumun BASLA kaydının sırası.
- **Nokta** 36 bayttır:
  - `kart_ms`, `n`, `bayrak`
  - V ve A: ort (float, **ham kod**) + min/maks (int16 **ham kod**)
  - W: ort/min/maks, **watt** (kayıt anındaki kalibrasyonla)
- **Menzil** nokta ortasında değişirse nokta orada kapanır; iki menzilin kodu aynı noktaya girmez.
- **Sektör** 4096 bayt (testte 512). Kurallar:
  - Kayıt sektör sınırını aşmaz.
  - Sektör kullanılmadan önce **her zaman** silinir.
  - Aktif oturumun her yeni sektörü **TEKRAR** kaydıyla başlar (BASLA'nın kopyası); her sektör kendini anlatır.
  - Sektörde her zaman bir BITIR kaydına (24 bayt) yer ayrılır. Bellek dolarsa BITIR(DOLU) yine yazılabilir.
- **Akıllı temizlik:** en eski sektör, son kaydının sırası `onay`dan büyük değilse silinir. Onaysız veri asla silinmez.
- **Boşaltma:** noktalar RAM tamponunda en fazla 28 nokta ya da 5 sn bekler. Elektrik kesilirse kayıp üst sınırı budur.

## Global Constraints

- **Python:** yalnız standart kütüphane (`kopru/` kuralı: "pip install gerektiren her bağımlılık ileride 'çalışmıyor' riski").
- **C başlıkları:**
  - Platformdan bağımsız, yalnız `static inline` fonksiyonlar.
  - C11 **ve** C++11 olarak `-Wall -Wextra` ile **UYARISIZ** derlenir; ESP32 `.ino`'yu C++ olarak derler.
  - Paketleme elle, küçük uçlu; `memcpy(struct)` yok.
  - Açık genişlikli tipler kullanılır; AVR'de `int` 16 bittir.
  - Bellek çağırandan gelir; `malloc` yok.
- **Adlandırma:** kaynak kod tanımlayıcıları ve yorumlar ASCII Türkçe, mevcut firmware üslubunda.
- **Doğrulama:**
  - Her iddianın çalıştırılabilir bir testi olur.
  - Her yeni iddianın `uretim/mutasyon.py`'de onu yalanlayan bir mutasyonu olur (Task 7).
  - Özet satırı `B71: X/Y kosul gecti` biçiminde olur (`uretim/sayim.py` deseni).
- **Komutlar:** depo kökünden (`projeler/olcum-karti/`) yazılır; testler `uretim/` içinden koşulur.
- **Commit:**
  - Yalnızca o görevin dosyaları `git add <dosya>` ile eklenir. Depoda kutu kurulumundan kalan commit'lenmemiş 23 değişikliğe **dokunulmaz**.
  - Mesaj sonu: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - Commit Git Bash'te `git commit -q -F - <<'EOF' … EOF` ile yapılır. PowerShell here-string'i çift tırnakta bölünüyor.

## Review Focus

Spec'in ima ettiği ama gözden kaçması en kolay beş durum:

1. **Silme sırasında elektrik kesilirse sektör yarı silinmiş çöp olur.** Kurtarma bu çöpü veri sanmamalı; o sektörü yeniden silip kullanmalı. → Task 1 (N6), Task 6 (K2, K6)
2. **Sıra numarası tekrar verilmemeli.** Ne yeniden başlamada ne biçimlendirmeden sonra. → Task 4 (G11), Task 6 (K9)
3. **Bozuk bir istemci kartın bildiğinden büyük bir onay yollarsa** onaysız veri silinmemeli. → Task 4 (G6, G7)
4. **Bellek onaysız veriyle dolunca kayıt sessizce durmamalı.** BITIR(DOLU) flaşta olmalı, yazıcı DOLU döndürmeli. → Task 5 (Y12)
5. **Menzil nokta ortasında değişirse** iki menzilin kodları aynı noktada karışmamalı. → Task 3 (P2, P3)

---

### Task 1: Emüle NOR flaş ve test iskeleti

**Files:**
- Create: `uretim/avr/nor_flas.py`
- Create: `uretim/test_kayit.py`

**Interfaces:**
- Produces: `NorFlas(boyut, sektor=4096, sil_cevrim=0)`
  - alanlar: `.bellek` (bytearray), `.silme_adet`, `.kesilen_silme`, `.yazilan_bayt`
  - yöntemler: `.tak(kart)`, `.kes(rng)`
  - sabitler: `A0, A1, A2, VERI, KOMUT, SIL`
- Produces: `test_kayit.py` iskeleti: `ok()`, `BOLUMLER` listesi, `main()` (`--kesinti N` seçeneği)

- [ ] **Step 1: Testi yaz**

`uretim/test_kayit.py`:

```python
# -*- coding: utf-8 -*-
"""B71 — KAYIT MOTORU: bicim · noktaci · gunluk · yazici · elektrik kesme.

    python test_kayit.py                  # zincir adimi
    python test_kayit.py --kesinti 1000   # uzun elektrik kesme denemesi

Gercek C kodu (kod/olcum-karti-a3/kayit_*.h) avr-gcc ile derlenip AVR
emulatorunde, EMULE NOR FLASIN (avr/nor_flas.py) ustunde kosuyor. Python
cozucu (kopru/kayit_bicim.py) ayni baytlari BAGIMSIZ olarak cozuyor; iki
taraf ayni sonucu vermezse kirmizi.
Tasarim: tasarim/2026-09-29-yazilim-sistemi.md §5
Plan:    tasarim/2026-09-29-plan-1a1-kayit-motoru.md

Beklenen degerler analitik ya da elle hesaplanmis; C kodunun Python'da
yeniden yazilmis bir kopyasindan GELMIYOR. Tek istisna `f32`: sonucu degil
float32 YUVARLAMASINI taklit ediyor.
"""
from __future__ import annotations

import argparse
import random
import struct
import subprocess
import sys
import zlib
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr.nor_flas import NorFlas, A0, A1, A2, VERI, KOMUT, SIL   # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


# ── B71.N · emule NOR flas ─────────────────────────────────────────────
class _Cpu:
    def __init__(self):
        self.cevrim = 0
        self.gc_oku = {}
        self.gc_yaz = {}


class _Kart:
    def __init__(self):
        self.cpu = _Cpu()


def bolum_nor() -> None:
    print("\n── B71.N  emule NOR flas")
    k = _Kart()
    f = NorFlas(1024, sektor=512, sil_cevrim=100)
    f.tak(k)
    y, o = k.cpu.gc_yaz, k.cpu.gc_oku

    def adres(a: int) -> None:
        y[A0](a & 0xFF)
        y[A1]((a >> 8) & 0xFF)
        y[A2]((a >> 16) & 0xFF)

    ok("B71.N1 yeni flas tamamen 0xFF", f.bellek == b"\xff" * 1024)
    adres(0x10)
    y[VERI](0x0F)
    adres(0x10)
    y[VERI](0xF0)
    ok("B71.N2 yazma yalniz 1->0 yapar (0x0F sonra 0xF0 = 0x00)",
       f.bellek[0x10] == 0x00, f"bayt={f.bellek[0x10]:#04x}")
    adres(0x10)
    v = o[VERI]()
    ok("B71.N3 okuma bayti verir ve adresi ilerletir", v == 0 and f.adres == 0x11)
    f.bellek[0x200:0x400] = b"\x00" * 512
    adres(0x200)
    y[KOMUT](SIL)
    ok("B71.N4 silme ZAMAN alir: hemen sonra mesgul", o[KOMUT]() == 1)
    k.cpu.cevrim += 100
    ok("B71.N5 sil_cevrim sonra sektor 0xFF ve mesgul degil",
       o[KOMUT]() == 0 and f.bellek[0x200:0x400] == b"\xff" * 512)
    f.bellek[0:512] = b"\x00" * 512
    adres(0)
    y[KOMUT](SIL)
    f.kes(random.Random(1))
    yari = bytes(f.bellek[0:512])
    ok("B71.N6 kesilen silme sektoru YARIM birakir (ne hepsi 0xFF ne hepsi eski)",
       yari != b"\xff" * 512 and yari != b"\x00" * 512 and f.kesilen_silme == 1,
       f"0xFF={yari.count(0xFF)} 0x00={yari.count(0)}")
    try:
        f.tak(k)
        adres(1024)
        o[VERI]()
        ok("B71.N7 alan disi okuma sessiz gecmez", False)
    except IndexError:
        ok("B71.N7 alan disi okuma sessiz gecmez", True)


BOLUMLER = [bolum_nor]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kesinti", type=int, default=120,
                    help="elektrik kesme denemesi sayisi")
    arg = ap.parse_args()
    for b in BOLUMLER:
        if b.__name__ == "bolum_kesinti":
            b(arg.kesinti)
        else:
            b()
    print(f"\nB71: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Testin kırmızı olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `ModuleNotFoundError: No module named 'avr.nor_flas'`

- [ ] **Step 3: `uretim/avr/nor_flas.py` yaz**

```python
# -*- coding: utf-8 -*-
"""Emule NOR flas — AVR testlerinde kayit gunlugunun altindaki 'disk' (B71).

Kayit gunlugu (kod/olcum-karti-a3/kayit_gunluk.h) kartta ESP32'nin
esp_partition_* cagrilariyla GERCEK NOR flasa yazar. AVR emulatorunde ayni
C kodu bu cevre birimine yazar. NOR'un iki kurali birebir:
  * yazma yalniz 1 -> 0 yapar (eski & yeni); 0'i 1'e ancak silme dondurur
  * silme bir SEKTORU 0xFF yapar ve ZAMAN alir (`sil_cevrim`)
Iki ariza modeli:
  * yazma bayt bayt ilerler: elektrik kesilirse kaydin bir kismi kalir
  * suren bir silme kesilirse sektor YARI SILINMIS kalir: baytlarin bir
    kismi 0xFF, bir kismi eski, bir kismi rastgele (`kes()`)

Yazmaclar (ATmega328P veri uzayinda REZERV adresler; gercek cipte bos,
emulatorde `gc_oku`/`gc_yaz` kancalari 0x20-0xFF arasinda calisiyor):
  0xE0 KOMUT   yaz 0x5E: adresin sektorunu sil · oku bit0: silme suruyor
  0xE1..0xE3   adres bayt 0/1/2 (kucuk uclu)
  0xE4 VERI    oku: bayt, adres++ · yaz: bayt &= v, adres++
"""
from __future__ import annotations

import random

KOMUT, A0, A1, A2, VERI = 0xE0, 0xE1, 0xE2, 0xE3, 0xE4
SIL = 0x5E


class NorFlas:
    def __init__(self, boyut: int, sektor: int = 4096, sil_cevrim: int = 0):
        if boyut % sektor:
            raise ValueError("boyut sektorun kati olmali")
        self.bellek = bytearray(b"\xff" * boyut)
        self.sektor = sektor
        self.sil_cevrim = sil_cevrim
        self.adres = 0
        self.cpu = None
        self._silinen: int | None = None    # suren silmenin sektor adresi
        self._sil_bitis = 0
        self.yazilan_bayt = 0
        self.silme_adet = 0
        self.kesilen_silme = 0

    # ------------------------------------------------------------ baglanti
    def tak(self, kart) -> None:
        """Yazmaclari bir emulator kartina bagla (her acilista yeniden)."""
        self.cpu = kart.cpu
        o, y = kart.cpu.gc_oku, kart.cpu.gc_yaz
        y[A0] = lambda v: self._adres_bayt(0, v)
        y[A1] = lambda v: self._adres_bayt(1, v)
        y[A2] = lambda v: self._adres_bayt(2, v)
        o[VERI] = self._veri_oku
        y[VERI] = self._veri_yaz
        o[KOMUT] = self._durum
        y[KOMUT] = self._komut

    def _adres_bayt(self, i: int, v: int) -> None:
        self.adres = (self.adres & ~(0xFF << (8 * i))) | ((v & 0xFF) << (8 * i))

    # ------------------------------------------------------------ silme
    def _silme_bitti_mi(self) -> None:
        if (self._silinen is not None and self.cpu is not None
                and self.cpu.cevrim >= self._sil_bitis):
            s = self._silinen
            self.bellek[s:s + self.sektor] = b"\xff" * self.sektor
            self._silinen = None

    def _mesgul(self, a: int) -> bool:
        return (self._silinen is not None
                and self._silinen <= a < self._silinen + self.sektor)

    def _alan(self, a: int) -> None:
        if not 0 <= a < len(self.bellek):
            raise IndexError(f"NOR erisimi alan disi: {a:#x}")

    # ------------------------------------------------------------ yazmaclar
    def _veri_oku(self) -> int:
        self._silme_bitti_mi()
        a = self.adres
        self._alan(a)
        self.adres = a + 1
        return 0xFF if self._mesgul(a) else self.bellek[a]

    def _veri_yaz(self, v: int) -> None:
        self._silme_bitti_mi()
        a = self.adres
        self._alan(a)
        if self._mesgul(a):
            raise RuntimeError(f"silme surerken yazma: {a:#x}")
        self.bellek[a] &= v & 0xFF
        self.adres = a + 1
        self.yazilan_bayt += 1

    def _komut(self, v: int) -> None:
        self._silme_bitti_mi()
        if v != SIL:
            raise RuntimeError(f"bilinmeyen NOR komutu {v:#x}")
        s = (self.adres // self.sektor) * self.sektor
        self._alan(s)
        self.silme_adet += 1
        if self.sil_cevrim <= 0 or self.cpu is None:
            self.bellek[s:s + self.sektor] = b"\xff" * self.sektor
        else:
            self._silinen = s
            self._sil_bitis = self.cpu.cevrim + self.sil_cevrim

    def _durum(self) -> int:
        self._silme_bitti_mi()
        return 1 if self._silinen is not None else 0

    # ------------------------------------------------------------ ariza
    def kes(self, rng: random.Random) -> None:
        """Elektrik kesildi. Suren bir silme YARIM kalir."""
        self._silme_bitti_mi()
        if self._silinen is not None:
            s = self._silinen
            for a in range(s, s + self.sektor):
                r = rng.random()
                if r < 0.45:
                    self.bellek[a] = 0xFF
                elif r < 0.55:
                    self.bellek[a] = rng.randrange(256)
                # kalan %45: eski bayt oldugu gibi
            self._silinen = None
            self.kesilen_silme += 1
        self.cpu = None
```

- [ ] **Step 4: Testin yeşil olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: yedi satır `[OK] B71.N…`, son satır `B71: 7/7 kosul gecti`, çıkış kodu 0.

- [ ] **Step 5: Commit**

```bash
git add uretim/avr/nor_flas.py uretim/test_kayit.py
git commit -q -F - <<'EOF'
B71 kayit motoru: emule NOR flas + test iskeleti

NOR kurallari (yazma yalniz 1->0, silme zaman alir) ve iki ariza modeli
(yarim yazma, yarim silme). test_kayit.py 7/7.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Kayıt biçimi — `kayit_bicim.h`, `kayit_bicim.py`, çapraz test

**Files:**
- Create: `kod/olcum-karti-a3/kayit_bicim.h`
- Create: `kopru/kayit_bicim.py`
- Create: `uretim/avr/ornek_kayit.c`
- Modify: `uretim/test_kayit.py` (yardımcılar + `bolum_bicim`)
- Modify: `uretim/gecici.py` (`ONEKLER`'e `"kayit_"`)

**Interfaces:**
- Consumes: `NorFlas` (Task 1)
- Produces (C, `kayit_bicim.h`):
  - tipler: `KayitBaslik`, `KayitNokta`, `KayitKanal`, `KayitKalibrasyon`, `KayitBasla`, `KayitDevam`, `KayitBitir`, `KayitSaat`
  - `kayit_crc_ekle(uint32_t crc, const uint8_t*, uint32_t) -> uint32_t`
  - `kayit_toplam_bayt(uint32_t yuk) -> uint32_t`
  - `kayit_baslik_yaz(uint8_t b[16], uint8_t tur, uint32_t sira, uint32_t oturum, const uint8_t *yuk, uint16_t yuk_bayt)`
  - `kayit_baslik_coz(const uint8_t b[16], KayitBaslik*) -> int8_t`: 1 geçerli görünen, 0 boş, −1 çöp
  - paketle/çöz çiftleri: `kayit_nokta_paketle/coz`, `kayit_basla_paketle/coz`, `kayit_devam_paketle/coz`, `kayit_bitir_paketle/coz`, `kayit_saat_paketle/coz`
  - bayt yardımcıları: `kayit_y16/y32/yf`, `kayit_o16/o32/of`
  - sabitler: `KAYIT_*`, `KN_*`, `KB_SEBEP_*`
- Produces (Python, `kayit_bicim.py`):
  - sabitler: `T_*`, `KN_*`, `OTURUM_OLCUM`, `KAL_BICIM`, `NOKTA_BAYT`
  - veri sınıfları: `Kayit`, `Nokta`, `Kanal`, `Kalibrasyon`, `Basla`, `Oturum`
  - paketleme: `kayit_paketle(tur, sira, oturum, yuk) -> bytes`, `nokta_paketle/nokta_coz`, `basla_paketle/basla_coz`
  - çözme: `akis_coz(bytes) -> list[Kayit]` (bozuksa `ValueError`), `flas_coz(bytes, sektor) -> (list[Kayit], bozuk:int)`, `devam_coz/bitir_coz/saat_coz -> dict`, `oturumlari_kur(list[Kayit]) -> dict[int, Oturum]`
  - birim: `volt(kod, Kanal)`, `amper(kod, Kalibrasyon)`, `unix_zaman(s) -> datetime|None`
- Produces (test yardımcıları): `f32`, `derle(senaryo, sektor_adet=8) -> Path`, `kart_kur`, `kos(elf, flas=None) -> list[str]`, `alanlar(satirlar, onek)`, `nokta_uret(k)`, `basla_uret(hiz_ms)`, `CPP_BASLIKLAR`

- [ ] **Step 1: Testi yaz**

`uretim/test_kayit.py`'de `from avr.nor_flas import …` satırının hemen altına şunu ekle:

```python
from avr import mega328                          # noqa: E402
from avr.cekirdek import Cekirdek                # noqa: E402
from avr.elf import flash_goruntusu              # noqa: E402
import gecici                                    # noqa: E402
import kayit_bicim as KB                         # noqa: E402

AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"
AVR_GXX = AVR_BIN / "avr-g++.exe"
HARNESS = BURASI / "avr" / "ornek_kayit.c"
SEKTOR = 512          # testte kucuk sektor: halka cok doner, emulatorde ucuz
SEKTOR_ADET = 8       # varsayilan; derle() -DNOR_SEKTOR_ADET ile gecirir
AZAMI_YUK = 256       # 4 + 7 nokta
CPP_BASLIKLAR = ["kayit_bicim.h"]
_ELF: dict[str, Path] = {}
```

`bolum_nor` fonksiyonunun hemen altına şunu ekle:

```python
# ── ortak yardimcilar ─────────────────────────────────────────────────
def f32(x: float) -> float:
    """float32'ye yuvarla — C'nin float islemini taklit etmek icin."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def derle(senaryo: str, sektor_adet: int = SEKTOR_ADET) -> Path:
    """ornek_kayit.c'yi TEK senaryo icin derle; UYARISIZ olmali.
    `sektor_adet` emule flasin sektor sayisi (NOR_SEKTOR_ADET)."""
    anahtar = f"{senaryo}_{sektor_adet}"
    if anahtar in _ELF:
        return _ELF[anahtar]
    elf = gecici.dizin("kayit_") / f"ornek_kayit_{anahtar}.elf"
    d = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os",
         "-std=gnu11", "-Wall", "-Wextra", f"-DSENARYO_{senaryo}",
         f"-DKAYIT_SEKTOR={SEKTOR}UL", f"-DKAYIT_AZAMI_YUK={AZAMI_YUK}u",
         f"-DNOR_SEKTOR_ADET={sektor_adet}u",
         f"-I{KOD}", "-o", str(elf), str(HARNESS), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if d.returncode != 0:
        print(d.stderr[-3000:])
        raise SystemExit(f"avr-gcc derleyemedi (SENARYO_{senaryo})")
    uyari = [x for x in d.stderr.splitlines() if "warning:" in x]
    ok(f"B71.0 SENARYO_{senaryo} AVR'de UYARISIZ derlendi (-Wall -Wextra)",
       not uyari, f"{len(uyari)} uyari")
    for u in uyari[:6]:
        print("       " + u)
    _ELF[anahtar] = elf
    return elf


def kart_kur(elf: Path, flas: NorFlas | None = None) -> mega328.Kart:
    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    if flas is not None:
        flas.tak(kart)
    return kart


def kos(elf: Path, flas: NorFlas | None = None,
        azami: int = 300_000_000) -> list[str]:
    """Senaryoyu `BITTI` satirina kadar kostur; cikti satirlarini dondur."""
    kart = kart_kur(elf, flas)
    hedef = kart.cpu.cevrim + azami
    while kart.cpu.cevrim < hedef and b"BITTI\n" not in kart.tx:
        kart.cevrim_kadar_kos(2_000_000)
    satirlar = kart.satirlar()
    ok(f"B71.0 {elf.stem} tamamlandi (BITTI)", "BITTI" in satirlar,
       f"{kart.cpu.cevrim:,} cevrim".replace(",", " "))
    return satirlar


def alanlar(satirlar: list[str], onek: str) -> list[list[str]]:
    """`onek` ile baslayan satirlarin kelimeleri (onek haric), sirayla."""
    return [s.split()[1:] for s in satirlar if s.split()[:1] == [onek]]


def nokta_uret(k: int) -> KB.Nokta:
    """ornek_kayit.c nokta_uret() ile AYNI deterministik nokta."""
    return KB.Nokta(
        kart_ms=(k * 37 + 5) & 0xFFFFFFFF, n=k % 50 + 1, bayrak=k & 0x3F,
        v_ort_kod=f32((k % 30000) + 0.25), v_min_kod=(k % 30000) - 7,
        v_maks_kod=(k % 30000) + 7,
        i_ort_kod=f32(-(k % 20000) - 0.5), i_min_kod=-(k % 20000) - 3,
        i_maks_kod=-(k % 20000) + 3,
        w_ort=f32(k * 0.5), w_min=f32(k * 0.25), w_maks=f32(k * 0.75))


def basla_uret(hiz_ms: int) -> KB.Basla:
    """ornek_kayit.c basla_uret() ile AYNI. Butun kesirler ikili (tam temsil)."""
    return KB.Basla(
        oturum_turu=KB.OTURUM_OLCUM, kal_bicim=KB.KAL_BICIM, hiz_ms=hiz_ms,
        unix_s=0, kart_ms=1000, acilis=3, surum="B71-test",
        kal=KB.Kalibrasyon(
            normal=KB.Kanal(16.5, 2.0, 1.0078125, -12, 0.0029296875),
            yuksek=KB.Kanal(312.5, 2.0, 0.9921875, 5, 0.0030517578125),
            i_ofset=-3, i_pga=0.25, sont_ohm=0.0048828125, i_duzeltme=1.0,
            sebeke_hz=50.0, faz_kal_us=(12.5, -3.25)))


def _hata_verir(f) -> bool:
    try:
        f()
    except ValueError:
        return True
    return False


def _cpp_denetim() -> str:
    """Basliklari avr-g++ ile -fsyntax-only derle. Sorun yoksa bos metin."""
    kaynak = ("".join(f'#include "{h}"\n' for h in CPP_BASLIKLAR)
              + "int main() { return 0; }\n")
    d = subprocess.run(
        [str(AVR_GXX), "-mmcu=atmega328p", "-std=gnu++11", "-fsyntax-only",
         "-Wall", "-Wextra", f"-I{KOD}", "-x", "c++", "-"],
        input=kaynak, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    metin = d.stderr or ""
    return metin if (d.returncode or "warning:" in metin) else ""


# ── B71.B · kayit bicimi ──────────────────────────────────────────────
def bolum_bicim() -> None:
    print("\n── B71.B  kayit bicimi: C == Python")
    s = {p[0]: p[1:] for p in (x.split() for x in kos(derle("BICIM"))) if p}
    ok("B71.B1 CRC-32 bilinen vektor ('123456789' -> cbf43926)",
       s.get("CRC") == ["cbf43926"], str(s.get("CRC")))
    ok("B71.B1 C'nin CRC'si zlib.crc32 ile ayni",
       s.get("CRC") == [f"{zlib.crc32(b'123456789'):08x}"])
    ok("B71.B2 nokta paketi C == Python (36 bayt)",
       bytes.fromhex(s["NOKTA"][0]) == KB.nokta_paketle(nokta_uret(12345)))
    b = basla_uret(200)
    ok("B71.B3 BASLA paketi C == Python (98 bayt, kalibrasyon kopyasi dahil)",
       bytes.fromhex(s["BASLA"][0]) == KB.basla_paketle(b))
    yuk20 = KB.basla_paketle(b)[:20]
    ok("B71.B4 kayit basligi + CRC C == Python",
       bytes.fromhex(s["BASLIK"][0])
       == KB.kayit_paketle(KB.T_NOKTA, 7, 42, yuk20)[:16])
    ok("B71.B5 C'de paketle -> coz -> paketle birebir",
       s.get("GIDISDONUS") == ["1"])
    ok("B71.B6 Python'da BASLA coz -> paketle birebir",
       KB.basla_paketle(KB.basla_coz(KB.basla_paketle(b))) == KB.basla_paketle(b))
    ok("B71.B7 unix 0 = 'bilinmiyor' (1970 tarihi uretilmez)",
       KB.unix_zaman(0) is None and KB.unix_zaman(1790000000).year == 2026)
    ham = KB.kayit_paketle(KB.T_SAAT, 9, 0, b"\x01\x02\x03")
    bozuk = ham[:17] + bytes([ham[17] ^ 1]) + ham[18:]
    ok("B71.B8 akis cozucu tek bitlik bozulmayi REDDEDER",
       _hata_verir(lambda: KB.akis_coz(bozuk)) and len(KB.akis_coz(ham)) == 1)
    ok("B71.B9 kayit 4 baytin katina dolgulanir, dolgu CRC'ye girmez",
       len(ham) == 20 and ham[19:] == b"\x00")
    kh = _cpp_denetim()
    ok("B71.B10 kayit_*.h C++ olarak da UYARISIZ (ESP32 .ino'yu C++ derler)",
       not kh, kh[:300])
    kn = KB.Kanal(16.5, 2.0, 1.0078125, -12, 0.0029296875)
    ok("B71.B11 volt(): sifir kodunda 0 V; +16384 kod = pga/2 x n x kazanc",
       KB.volt(-12, kn) == 0.0
       and abs(KB.volt(-12 + 16384, kn) - 1.0 * 16.5 * 1.0078125) < 1e-12)
```

`BOLUMLER` satırını şöyle değiştir:

```python
BOLUMLER = [bolum_nor, bolum_bicim]
```

`uretim/gecici.py`'de:

```python
ONEKLER = ("spice-", "olcum3_", "skopolc_", "kopru_", "fw3_", "skop_")
```

satırını şununla değiştir:

```python
ONEKLER = ("spice-", "olcum3_", "skopolc_", "kopru_", "fw3_", "skop_", "kayit_")
```

- [ ] **Step 2: Testin kırmızı olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `ModuleNotFoundError: No module named 'kayit_bicim'`

- [ ] **Step 3: `kod/olcum-karti-a3/kayit_bicim.h` yaz**

```c
#ifndef KAYIT_BICIM_H
#define KAYIT_BICIM_H
/*
 * B71 — KAYIT BICIMI, surum 1.
 *
 * Kartin flasa yazdigi ve telefon/PC'nin AYNEN sakladigi baytlarin TEK
 * tanimi. Platform bagimsiz: firmware (ESP32) ve AVR emulator testi
 * (uretim/test_kayit.py) ayni dosyayi derler. Python karsiligi
 * kopru/kayit_bicim.py; iki taraf ortak test vektorleriyle sinaniyor.
 * Tasarim: tasarim/2026-09-29-yazilim-sistemi.md §5.
 *
 * KAYIT = 16 bayt baslik + yuk + 0..3 bayt SIFIR dolgu (4'un katina):
 *    0  u8   imza 0xA5  (silinmis flas 0xFF: bos yer boyle taninir)
 *    1  u8   tur        KAYIT_T_*
 *    2  u16  yuk_bayt
 *    4  u32  sira       kartin BUTUN kayitlari icin artan sira (>= 1),
 *                       asla tekrar verilmez
 *    8  u32  oturum     oturum kimligi = oturumun BASLA kaydinin sirasi;
 *                       0 = oturuma bagli degil
 *   12  u32  crc        CRC-32 (zlib.crc32 ile ayni): bayt 0..11 + yuk.
 *                       Dolgu CRC'ye GIRMEZ.
 *
 * NOKTA (36 bayt): kart_ms u32 · n u16 · bayrak u8 · 0 u8 ·
 *   V: ort f32 (HAM KOD) · min i16 · maks i16 (HAM KOD)
 *   A: ort f32 (HAM KOD) · min i16 · maks i16 (HAM KOD)
 *   W: ort f32 · min f32 · maks f32 (WATT — kayit anindaki kalibrasyonla)
 *
 * 🔴 ELLE PAKETLEME. Butun sayilar kucuk uclu, bayt bayt yaziliyor;
 *    memcpy(struct) YOK. AVR ile Xtensa'nin hizalama ve dolgu kurallari
 *    ayni olmak zorunda degil — struct kopyalamak iki mimaride farkli
 *    bayt dizisi uretebilirdi.
 * 🔴 Butun fonksiyonlar `static inline`: harness her fonksiyonu
 *    kullanmiyor; duz `static` -Wunused-function uyarisi verirdi ve
 *    zincir uyarisiz derleme istiyor.
 */
#include <stdint.h>
#include <string.h>

#define KAYIT_SURUM        1u
#define KAYIT_IMZA         0xA5u
#define KAYIT_BASLIK_BAYT  16u
#define KAYIT_NOKTA_BAYT   36u
#define KAYIT_BASLA_BAYT   98u
#define KAYIT_DEVAM_BAYT   16u
#define KAYIT_BITIR_BAYT   8u
#define KAYIT_SAAT_BAYT    12u

/* kayit turleri */
#define KAYIT_T_BASLA   1u   /* oturum basladi; kalibrasyon kopyasi burada */
#define KAYIT_T_NOKTA   2u   /* u32 ilk_nokta + N x 36 bayt nokta */
#define KAYIT_T_DEVAM   3u   /* kart yeniden basladi, oturum SURUYOR */
#define KAYIT_T_BITIR   4u   /* oturum bitti */
#define KAYIT_T_SAAT    5u   /* kart ms <-> unix eslemesi */
#define KAYIT_T_TEKRAR  6u   /* BASLA'nin sektor basi kopyasi (ayni yuk) */
#define KAYIT_T_AZAMI   6u

/* nokta bayraklari */
#define KN_YUKSEK      0x01u  /* nokta YUKSEK gerilim menzilinde */
#define KN_V_HATA      0x02u  /* en az bir ornekte gerilim ADS'i okunamadi */
#define KN_I_HATA      0x04u  /* en az bir ornekte akim ADS'i okunamadi */
#define KN_V_DOYDU     0x08u  /* en az bir gerilim ornegi doydu */
#define KN_DURAKLAMA   0x10u  /* bu noktadan once/icinde olcum durdu */
#define KN_KAYIP_ONCE  0x20u  /* bundan ONCEKI noktalar kuyrukta dustu */

/* BITIR sebepleri */
#define KB_SEBEP_KULLANICI 1u
#define KB_SEBEP_DOLU      2u
#define KB_SEBEP_HATA      3u

#define KAYIT_OTURUM_OLCUM 1u   /* BASLA.oturum_turu: V/A/W olcum kaydi */
#define KAYIT_KAL_BICIM    1u   /* BASLA.kal_bicim: KayitKalibrasyon v1 */

/* ─────────────────────────────── kucuk uclu elle paketleme */
static inline void kayit_y16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}

static inline void kayit_y32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static inline uint16_t kayit_o16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8));
}

static inline uint32_t kayit_o32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
         | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline void kayit_yf(uint8_t *p, float f)
{
    uint32_t u;
    memcpy(&u, &f, 4);
    kayit_y32(p, u);
}

static inline float kayit_of(const uint8_t *p)
{
    uint32_t u = kayit_o32(p);
    float f;
    memcpy(&f, &u, 4);
    return f;
}

/* Kaydin flasta kapladigi toplam bayt: baslik + yuk, 4'un katina. */
static inline uint32_t kayit_toplam_bayt(uint32_t yuk_bayt)
{
    return (KAYIT_BASLIK_BAYT + yuk_bayt + 3u) & ~(uint32_t)3u;
}

/* ─────────────────────────────── CRC-32 (ISO-HDLC, zlib ile ayni)
 * Yarim bayt (nibble) tablosu: 64 bayt. AVR'de 256'lik tablo 1 KB RAM
 * yerdi; bitsel dongu ise emulatorde 4 kat yavasti. */
static const uint32_t KAYIT_CRC_TABLO[16] = {
    0x00000000u, 0x1DB71064u, 0x3B6E20C8u, 0x26D930ACu,
    0x76DC4190u, 0x6B6B51F4u, 0x4DB26158u, 0x5005713Cu,
    0xEDB88320u, 0xF00F9344u, 0xD6D6A3E8u, 0xCB61B38Cu,
    0x9B64C2B0u, 0x86D3D2D4u, 0xA00AE278u, 0xBDBDF21Cu,
};

/* zlib.crc32(veri, crc) ile ayni: parca parca cagrilabilir. */
static inline uint32_t kayit_crc_ekle(uint32_t crc, const uint8_t *p, uint32_t n)
{
    crc = ~crc;
    while (n--) {
        crc ^= *p++;
        crc = (crc >> 4) ^ KAYIT_CRC_TABLO[crc & 15u];
        crc = (crc >> 4) ^ KAYIT_CRC_TABLO[crc & 15u];
    }
    return ~crc;
}

/* ─────────────────────────────── baslik */
typedef struct {
    uint8_t  tur;
    uint16_t yuk_bayt;
    uint32_t sira;
    uint32_t oturum;
    uint32_t crc;
} KayitBaslik;

/* `b` 16 bayt. CRC baslik (0..11) + yuk uzerinden hesaplanir. */
static inline void kayit_baslik_yaz(uint8_t *b, uint8_t tur, uint32_t sira,
                                    uint32_t oturum, const uint8_t *yuk,
                                    uint16_t yuk_bayt)
{
    uint32_t c;
    b[0] = (uint8_t)KAYIT_IMZA;
    b[1] = tur;
    kayit_y16(b + 2, yuk_bayt);
    kayit_y32(b + 4, sira);
    kayit_y32(b + 8, oturum);
    c = kayit_crc_ekle(0u, b, 12u);
    c = kayit_crc_ekle(c, yuk, yuk_bayt);
    kayit_y32(b + 12, c);
}

/* 1 = gecerli GORUNEN baslik, 0 = bos (16 bayt 0xFF), -1 = cop.
   CRC burada DENETLENMEZ: yuk okunmadan denetlenemez. */
static inline int8_t kayit_baslik_coz(const uint8_t *b, KayitBaslik *h)
{
    uint8_t i, hepsi_ff = 1u;
    for (i = 0; i < KAYIT_BASLIK_BAYT; i++) {
        if (b[i] != 0xFFu) { hepsi_ff = 0u; break; }
    }
    if (hepsi_ff) return 0;
    if (b[0] != KAYIT_IMZA) return -1;
    if (b[1] < 1u || b[1] > KAYIT_T_AZAMI) return -1;
    h->tur = b[1];
    h->yuk_bayt = kayit_o16(b + 2);
    h->sira = kayit_o32(b + 4);
    h->oturum = kayit_o32(b + 8);
    h->crc = kayit_o32(b + 12);
    if (h->sira == 0u || h->sira == 0xFFFFFFFFUL) return -1;
    return 1;
}

/* ─────────────────────────────── nokta */
typedef struct {
    uint32_t kart_ms;      /* noktanin BITTIGI an (millis) */
    uint16_t n;            /* gecerli ornek sayisi */
    uint8_t  bayrak;       /* KN_* */
    float    v_ort_kod;
    int16_t  v_min_kod, v_maks_kod;
    float    i_ort_kod;
    int16_t  i_min_kod, i_maks_kod;
    float    w_ort, w_min, w_maks;
} KayitNokta;

static inline void kayit_nokta_paketle(const KayitNokta *k, uint8_t *p)
{
    kayit_y32(p, k->kart_ms);
    kayit_y16(p + 4, k->n);
    p[6] = k->bayrak;
    p[7] = 0u;
    kayit_yf(p + 8, k->v_ort_kod);
    kayit_y16(p + 12, (uint16_t)k->v_min_kod);
    kayit_y16(p + 14, (uint16_t)k->v_maks_kod);
    kayit_yf(p + 16, k->i_ort_kod);
    kayit_y16(p + 20, (uint16_t)k->i_min_kod);
    kayit_y16(p + 22, (uint16_t)k->i_maks_kod);
    kayit_yf(p + 24, k->w_ort);
    kayit_yf(p + 28, k->w_min);
    kayit_yf(p + 32, k->w_maks);
}

static inline void kayit_nokta_coz(const uint8_t *p, KayitNokta *k)
{
    k->kart_ms = kayit_o32(p);
    k->n = kayit_o16(p + 4);
    k->bayrak = p[6];
    k->v_ort_kod = kayit_of(p + 8);
    k->v_min_kod = (int16_t)kayit_o16(p + 12);
    k->v_maks_kod = (int16_t)kayit_o16(p + 14);
    k->i_ort_kod = kayit_of(p + 16);
    k->i_min_kod = (int16_t)kayit_o16(p + 20);
    k->i_maks_kod = (int16_t)kayit_o16(p + 22);
    k->w_ort = kayit_of(p + 24);
    k->w_min = kayit_of(p + 28);
    k->w_maks = kayit_of(p + 32);
}

/* ─────────────────────────────── BASLA (98 bayt)
 *    0 u8 oturum_turu · 1 u8 kal_bicim · 2 u16 0 · 4 u32 hiz_ms ·
 *    8 u32 unix_s (0 = bilinmiyor) · 12 u32 kart_ms · 16 u32 acilis ·
 *   20 char[16] surum · 36 kalibrasyon v1 (62 bayt):
 *   36 kanal normal (n f32, pga f32, kazanc f32, sifir_ham i16, tau f32)
 *   54 kanal yuksek · 72 i_ofset i16 · 74 i_pga · 78 sont_ohm ·
 *   82 i_duzeltme · 86 sebeke_hz · 90 faz_kal_us[0] · 94 faz_kal_us[1]
 * Kalibrasyon kopyasi olc_gerilim3/olc_akim3'un (olcum3.h) girdilerinin
 * TAMAMI: kayit hangi cihaza giderse gitsin kendi ham kodunu volta
 * cevirebilir (tasarim §7). */
typedef struct {
    float   n, pga, kazanc;
    int16_t sifir_ham;
    float   tau;
} KayitKanal;

typedef struct {
    KayitKanal normal, yuksek;
    int16_t    i_ofset;
    float      i_pga, sont_ohm, i_duzeltme, sebeke_hz;
    float      faz_kal_us[2];
} KayitKalibrasyon;

typedef struct {
    uint8_t  oturum_turu, kal_bicim;
    uint32_t hiz_ms, unix_s, kart_ms, acilis;
    char     surum[16];
    KayitKalibrasyon kal;
} KayitBasla;

static inline void kayit__kanal_yaz(uint8_t *p, const KayitKanal *k)
{
    kayit_yf(p, k->n);
    kayit_yf(p + 4, k->pga);
    kayit_yf(p + 8, k->kazanc);
    kayit_y16(p + 12, (uint16_t)k->sifir_ham);
    kayit_yf(p + 14, k->tau);
}

static inline void kayit__kanal_oku(const uint8_t *p, KayitKanal *k)
{
    k->n = kayit_of(p);
    k->pga = kayit_of(p + 4);
    k->kazanc = kayit_of(p + 8);
    k->sifir_ham = (int16_t)kayit_o16(p + 12);
    k->tau = kayit_of(p + 14);
}

static inline void kayit_basla_paketle(const KayitBasla *b, uint8_t *p)
{
    p[0] = b->oturum_turu;
    p[1] = b->kal_bicim;
    p[2] = 0u;
    p[3] = 0u;
    kayit_y32(p + 4, b->hiz_ms);
    kayit_y32(p + 8, b->unix_s);
    kayit_y32(p + 12, b->kart_ms);
    kayit_y32(p + 16, b->acilis);
    memcpy(p + 20, b->surum, 16);
    kayit__kanal_yaz(p + 36, &b->kal.normal);
    kayit__kanal_yaz(p + 54, &b->kal.yuksek);
    kayit_y16(p + 72, (uint16_t)b->kal.i_ofset);
    kayit_yf(p + 74, b->kal.i_pga);
    kayit_yf(p + 78, b->kal.sont_ohm);
    kayit_yf(p + 82, b->kal.i_duzeltme);
    kayit_yf(p + 86, b->kal.sebeke_hz);
    kayit_yf(p + 90, b->kal.faz_kal_us[0]);
    kayit_yf(p + 94, b->kal.faz_kal_us[1]);
}

static inline void kayit_basla_coz(const uint8_t *p, KayitBasla *b)
{
    b->oturum_turu = p[0];
    b->kal_bicim = p[1];
    b->hiz_ms = kayit_o32(p + 4);
    b->unix_s = kayit_o32(p + 8);
    b->kart_ms = kayit_o32(p + 12);
    b->acilis = kayit_o32(p + 16);
    memcpy(b->surum, p + 20, 16);
    kayit__kanal_oku(p + 36, &b->kal.normal);
    kayit__kanal_oku(p + 54, &b->kal.yuksek);
    b->kal.i_ofset = (int16_t)kayit_o16(p + 72);
    b->kal.i_pga = kayit_of(p + 74);
    b->kal.sont_ohm = kayit_of(p + 78);
    b->kal.i_duzeltme = kayit_of(p + 82);
    b->kal.sebeke_hz = kayit_of(p + 86);
    b->kal.faz_kal_us[0] = kayit_of(p + 90);
    b->kal.faz_kal_us[1] = kayit_of(p + 94);
}

/* ─────────────────────────────── DEVAM (16) · BITIR (8) · SAAT (12) */
typedef struct { uint32_t acilis, unix_s, kart_ms, nokta_sira; } KayitDevam;
typedef struct { uint32_t nokta_adedi; uint8_t sebep; } KayitBitir;
typedef struct { uint32_t unix_s, kart_ms, acilis; } KayitSaat;

static inline void kayit_devam_paketle(const KayitDevam *d, uint8_t *p)
{
    kayit_y32(p, d->acilis);
    kayit_y32(p + 4, d->unix_s);
    kayit_y32(p + 8, d->kart_ms);
    kayit_y32(p + 12, d->nokta_sira);
}

static inline void kayit_devam_coz(const uint8_t *p, KayitDevam *d)
{
    d->acilis = kayit_o32(p);
    d->unix_s = kayit_o32(p + 4);
    d->kart_ms = kayit_o32(p + 8);
    d->nokta_sira = kayit_o32(p + 12);
}

static inline void kayit_bitir_paketle(const KayitBitir *b, uint8_t *p)
{
    kayit_y32(p, b->nokta_adedi);
    p[4] = b->sebep;
    p[5] = 0u;
    p[6] = 0u;
    p[7] = 0u;
}

static inline void kayit_bitir_coz(const uint8_t *p, KayitBitir *b)
{
    b->nokta_adedi = kayit_o32(p);
    b->sebep = p[4];
}

static inline void kayit_saat_paketle(const KayitSaat *s, uint8_t *p)
{
    kayit_y32(p, s->unix_s);
    kayit_y32(p + 4, s->kart_ms);
    kayit_y32(p + 8, s->acilis);
}

static inline void kayit_saat_coz(const uint8_t *p, KayitSaat *s)
{
    s->unix_s = kayit_o32(p);
    s->kart_ms = kayit_o32(p + 4);
    s->acilis = kayit_o32(p + 8);
}

#endif /* KAYIT_BICIM_H */
```

- [ ] **Step 4: `kopru/kayit_bicim.py` yaz**

```python
# -*- coding: utf-8 -*-
"""B71 — KAYIT BICIMI (surum 1): kartin flasa yazdigi baytlarin Python cozucusu.

TEK TANIM `kod/olcum-karti-a3/kayit_bicim.h`; bu dosya ona UYAR. Iki taraf
`uretim/test_kayit.py`'de ORTAK test vektorleriyle sinaniyor: C'nin
urettigi baytlar burada cozulup yeniden paketleniyor; biri degisip oteki
degismezse zincir kirmizi.

Telefon/PC karttan gelen baytlari AYNEN saklar (tasarim §5); bu modul o
baytlari okur. Yalniz standart kutuphane (kopru kurali).

Birimler: kayitta V ve A icin HAM ADC KODU var; volt/amper `volt()` /
`amper()` ile kaydin KENDI kalibrasyon kopyasindan hesaplanir (tasarim §7).
Guc (W) kayit anindaki kalibrasyonla watt olarak saklanir.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

SURUM = 1
IMZA = 0xA5
BASLIK_BAYT = 16
NOKTA_BAYT = 36
BASLA_BAYT = 98

T_BASLA, T_NOKTA, T_DEVAM, T_BITIR, T_SAAT, T_TEKRAR = 1, 2, 3, 4, 5, 6
KN_YUKSEK, KN_V_HATA, KN_I_HATA = 0x01, 0x02, 0x04
KN_V_DOYDU, KN_DURAKLAMA, KN_KAYIP_ONCE = 0x08, 0x10, 0x20
SEBEP = {1: "kullanici", 2: "bellek doldu", 3: "hata"}
OTURUM_OLCUM = 1
KAL_BICIM = 1
ADS_SAYIM = 32768.0

_BASLIK = struct.Struct("<BBHII")        # imza, tur, yuk_bayt, sira, oturum
_NOKTA = struct.Struct("<IHBxfhhfhhfff")
_KANAL = struct.Struct("<fffhf")
_AKIM = struct.Struct("<hffffff")
_BASLA_BAS = struct.Struct("<BBHIIII16s")
_DEVAM = struct.Struct("<IIII")
_BITIR = struct.Struct("<IB3x")
_SAAT = struct.Struct("<III")
assert _NOKTA.size == NOKTA_BAYT
assert _BASLA_BAS.size + 2 * _KANAL.size + _AKIM.size == BASLA_BAYT


def toplam_bayt(yuk_bayt: int) -> int:
    """Kaydin flasta kapladigi bayt: baslik + yuk, 4'un katina."""
    return (BASLIK_BAYT + yuk_bayt + 3) & ~3


def crc(veri: bytes, onceki: int = 0) -> int:
    return zlib.crc32(veri, onceki) & 0xFFFFFFFF


# ── kayit ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Kayit:
    tur: int
    sira: int
    oturum: int
    yuk: bytes
    adres: int | None = None      # flas goruntusundeki yeri (flas_coz)


def kayit_paketle(tur: int, sira: int, oturum: int, yuk: bytes) -> bytes:
    bas = _BASLIK.pack(IMZA, tur, len(yuk), sira, oturum)
    c = crc(yuk, crc(bas))
    ham = bas + struct.pack("<I", c) + yuk
    return ham + b"\x00" * (toplam_bayt(len(yuk)) - len(ham))


def _kayit_oku(veri: bytes, a: int, son: int) -> tuple[int, Kayit | None]:
    """(durum, kayit): 1 gecerli, 0 bos (0xFF), -1 cop ya da yarim."""
    if a + BASLIK_BAYT > son:
        return 0, None
    b = bytes(veri[a:a + BASLIK_BAYT])
    if b == b"\xff" * BASLIK_BAYT:
        return 0, None
    imza, tur, n, sira, oturum, c = struct.unpack("<BBHIII", b)
    if imza != IMZA or not T_BASLA <= tur <= T_TEKRAR or sira in (0, 0xFFFFFFFF):
        return -1, None
    if a + toplam_bayt(n) > son:
        return -1, None
    yuk = bytes(veri[a + BASLIK_BAYT:a + BASLIK_BAYT + n])
    if crc(yuk, crc(b[:12])) != c:
        return -1, None
    return 1, Kayit(tur, sira, oturum, yuk, a)


def akis_coz(veri: bytes) -> list[Kayit]:
    """Esitleme yaniti: art arda kayitlar. Tek bozuk kayit -> ValueError."""
    kayitlar, a = [], 0
    while a < len(veri):
        d, k = _kayit_oku(veri, a, len(veri))
        if d != 1:
            raise ValueError(f"{a}. baytta gecersiz kayit")
        kayitlar.append(k)
        a += toplam_bayt(len(k.yuk))
    return kayitlar


def flas_coz(veri: bytes, sektor: int) -> tuple[list[Kayit], int]:
    """Flas goruntusu. Her sektor bastan; ilk gecersiz kayitta o sektor
    biter (kg_ac ile ayni kural). Donus: (sira ile sirali kayitlar,
    cop/yarim gorulen sektor sayisi)."""
    kayitlar, bozuk = [], 0
    for s in range(0, len(veri), sektor):
        a, son_sira = s, 0
        while True:
            d, k = _kayit_oku(veri, a, s + sektor)
            if d == 1 and k.sira <= son_sira:
                d = -1
            if d != 1:
                bozuk += 1 if d < 0 else 0
                break
            kayitlar.append(k)
            son_sira = k.sira
            a += toplam_bayt(len(k.yuk))
    kayitlar.sort(key=lambda x: x.sira)
    return kayitlar, bozuk


# ── nokta ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Nokta:
    kart_ms: int
    n: int
    bayrak: int
    v_ort_kod: float
    v_min_kod: int
    v_maks_kod: int
    i_ort_kod: float
    i_min_kod: int
    i_maks_kod: int
    w_ort: float
    w_min: float
    w_maks: float


def nokta_paketle(p: Nokta) -> bytes:
    return _NOKTA.pack(p.kart_ms, p.n, p.bayrak, p.v_ort_kod, p.v_min_kod,
                       p.v_maks_kod, p.i_ort_kod, p.i_min_kod, p.i_maks_kod,
                       p.w_ort, p.w_min, p.w_maks)


def nokta_coz(b: bytes) -> Nokta:
    return Nokta(*_NOKTA.unpack(b))


# ── BASLA ve kalibrasyon ──────────────────────────────────────────────
@dataclass(frozen=True)
class Kanal:
    n: float
    pga: float
    kazanc: float
    sifir_ham: int
    tau: float


@dataclass(frozen=True)
class Kalibrasyon:
    normal: Kanal
    yuksek: Kanal
    i_ofset: int
    i_pga: float
    sont_ohm: float
    i_duzeltme: float
    sebeke_hz: float
    faz_kal_us: tuple[float, float]


@dataclass(frozen=True)
class Basla:
    oturum_turu: int
    kal_bicim: int
    hiz_ms: int
    unix_s: int
    kart_ms: int
    acilis: int
    surum: str
    kal: Kalibrasyon


def _kanal_paketle(k: Kanal) -> bytes:
    return _KANAL.pack(k.n, k.pga, k.kazanc, k.sifir_ham, k.tau)


def basla_paketle(b: Basla) -> bytes:
    k = b.kal
    return (_BASLA_BAS.pack(b.oturum_turu, b.kal_bicim, 0, b.hiz_ms,
                            b.unix_s, b.kart_ms, b.acilis,
                            b.surum.encode("ascii")[:16].ljust(16, b"\0"))
            + _kanal_paketle(k.normal) + _kanal_paketle(k.yuksek)
            + _AKIM.pack(k.i_ofset, k.i_pga, k.sont_ohm, k.i_duzeltme,
                         k.sebeke_hz, *k.faz_kal_us))


def basla_coz(y: bytes) -> Basla:
    tur, kb, _, hiz, unix, kms, acilis, surum = _BASLA_BAS.unpack_from(y, 0)
    a = _BASLA_BAS.size
    normal = Kanal(*_KANAL.unpack_from(y, a))
    yuksek = Kanal(*_KANAL.unpack_from(y, a + _KANAL.size))
    io, ip, so, idz, sh, f0, f1 = _AKIM.unpack_from(y, a + 2 * _KANAL.size)
    return Basla(tur, kb, hiz, unix, kms, acilis,
                 surum.rstrip(b"\0").decode("ascii", "replace"),
                 Kalibrasyon(normal, yuksek, io, ip, so, idz, sh, (f0, f1)))


def devam_coz(y: bytes) -> dict:
    a, u, k, n = _DEVAM.unpack(y)
    return {"acilis": a, "unix_s": u, "kart_ms": k, "nokta_sira": n}


def bitir_coz(y: bytes) -> dict:
    n, s = _BITIR.unpack(y)
    return {"nokta_adedi": n, "sebep": s}


def saat_coz(y: bytes) -> dict:
    u, k, a = _SAAT.unpack(y)
    return {"unix_s": u, "kart_ms": k, "acilis": a}


# ── birimler ─────────────────────────────────────────────────────────
def _kirp(d: int) -> int:
    return max(-32768, min(32767, d))


def volt(kod: float, k: Kanal) -> float:
    """olc_gerilim3 (olcum3.h) ile ayni formul, float64. Tam sayi kodda
    firmware'in int16 kirpmasi da uygulanir."""
    d = kod - k.sifir_ham
    if isinstance(kod, int):
        d = _kirp(d)
    return d * (k.pga / ADS_SAYIM) * k.n * k.kazanc


def amper(kod: float, kal: Kalibrasyon) -> float:
    """olc_akim3 (olcum3.h) ile ayni formul, float64."""
    d = kod - kal.i_ofset
    if isinstance(kod, int):
        d = _kirp(d)
    return d * (kal.i_pga / ADS_SAYIM) / kal.sont_ohm * kal.i_duzeltme


def unix_zaman(s: int) -> datetime | None:
    """0 = kartin saati bilinmiyordu. 1970 tarihi URETILMEZ."""
    return None if not s else datetime.fromtimestamp(s, timezone.utc)


# ── oturumlar ────────────────────────────────────────────────────────
@dataclass
class Oturum:
    id: int
    basla: Basla | None = None
    basi_eksik: bool = True          # BASLA temizlikte gitti, TEKRAR'dan bilgi
    tekrar_adet: int = 0
    noktalar: list[tuple[int, Nokta]] = field(default_factory=list)
    devamlar: list[dict] = field(default_factory=list)
    saatler: list[dict] = field(default_factory=list)
    bitir: dict | None = None


def oturumlari_kur(kayitlar: list[Kayit]) -> dict[int, Oturum]:
    ot: dict[int, Oturum] = {}
    for k in sorted(kayitlar, key=lambda x: x.sira):
        if not k.oturum:
            continue
        o = ot.setdefault(k.oturum, Oturum(k.oturum))
        if k.tur == T_BASLA:
            o.basla = basla_coz(k.yuk)
            o.basi_eksik = False
        elif k.tur == T_TEKRAR:
            o.tekrar_adet += 1
            if o.basla is None:
                o.basla = basla_coz(k.yuk)
        elif k.tur == T_NOKTA:
            ilk = struct.unpack_from("<I", k.yuk)[0]
            for j in range((len(k.yuk) - 4) // NOKTA_BAYT):
                a = 4 + j * NOKTA_BAYT
                o.noktalar.append((ilk + j, nokta_coz(k.yuk[a:a + NOKTA_BAYT])))
        elif k.tur == T_DEVAM:
            o.devamlar.append(devam_coz(k.yuk))
        elif k.tur == T_BITIR:
            o.bitir = bitir_coz(k.yuk)
        elif k.tur == T_SAAT:
            o.saatler.append(saat_coz(k.yuk))
    return ot
```

- [ ] **Step 5: `uretim/avr/ornek_kayit.c` yaz (ortak kısım + BICIM senaryosu)**

```c
/*
 * B71 — kayit motorunun AVR emulatorunde kosturulmasi.
 *
 * NEDEN AVR: ESP32-S3'u komut komut calistiran bir emulatorumuz yok, ama
 * AVR'yi calistiran ve bit birebir dogrulanmis bir emulatorumuz var
 * (test_avr.py). kayit_*.h hicbir platform cagrisi icermiyor; flas
 * erisimi KayitFlas islev isaretcileriyle geliyor. Burada o isaretciler
 * emule NOR flasa (uretim/avr/nor_flas.py) bagli. Kosturulan kod, kartta
 * kosacak kodun ta kendisi.
 *
 * Tek senaryo derlenir: -DSENARYO_BICIM | _NOKTACI | _GUNLUK | _YAZICI |
 * _KESINTI. Testte -DKAYIT_SEKTOR=512UL -DKAYIT_AZAMI_YUK=256u.
 * Surucu: uretim/test_kayit.py.
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>

#include "kayit_bicim.h"

#define KULLANILMAYABILIR __attribute__((unused))

/* ─────────────────────────────── seri cikis */
static void uart_baslat(void)
{
    UBRR0H = 0;
    UBRR0L = 16;
    UCSR0A = (1 << U2X0);
    UCSR0B = (1 << TXEN0);
    UCSR0C = (3 << UCSZ00);
}

static void yaz(char c)
{
    while (!(UCSR0A & (1 << UDRE0))) {}
    UDR0 = c;
}

static KULLANILMAYABILIR void metin(const char *s)
{
    while (*s) yaz(*s++);
}

static KULLANILMAYABILIR void satir(void) { yaz('\n'); }

static KULLANILMAYABILIR void hex8(uint8_t v)
{
    static const char h[] = "0123456789abcdef";
    yaz(h[v >> 4]);
    yaz(h[v & 15u]);
}

static KULLANILMAYABILIR void hex32(uint32_t v)
{
    int8_t i;
    for (i = 3; i >= 0; i--) hex8((uint8_t)(v >> (8 * i)));
}

static KULLANILMAYABILIR void hexdizi(const uint8_t *p, uint16_t n)
{
    while (n--) hex8(*p++);
}

static KULLANILMAYABILIR void ondalik(uint32_t v)
{
    char b[11];
    int8_t i = 0;
    do { b[i++] = (char)('0' + (v % 10u)); v /= 10u; } while (v);
    while (i) yaz(b[--i]);
}

static KULLANILMAYABILIR void sayi(const char *ad, int32_t v)
{
    metin(ad);
    yaz(' ');
    if (v < 0) { yaz('-'); ondalik((uint32_t)(-v)); }
    else ondalik((uint32_t)v);
    satir();
}

/* ─────────────────────────────── deterministik veri (test_kayit.py ile AYNI) */
static KULLANILMAYABILIR void nokta_uret(uint32_t k, KayitNokta *p)
{
    uint16_t v = (uint16_t)(k % 30000u), i = (uint16_t)(k % 20000u);
    p->kart_ms = k * 37u + 5u;
    p->n = (uint16_t)(k % 50u + 1u);
    p->bayrak = (uint8_t)(k & 0x3Fu);
    p->v_ort_kod = (float)v + 0.25f;
    p->v_min_kod = (int16_t)((int16_t)v - 7);
    p->v_maks_kod = (int16_t)((int16_t)v + 7);
    p->i_ort_kod = -(float)i - 0.5f;
    p->i_min_kod = (int16_t)(-(int16_t)i - 3);
    p->i_maks_kod = (int16_t)(-(int16_t)i + 3);
    p->w_ort = (float)k * 0.5f;
    p->w_min = (float)k * 0.25f;
    p->w_maks = (float)k * 0.75f;
}

static KULLANILMAYABILIR void basla_uret(KayitBasla *b, uint32_t hiz_ms)
{
    memset(b, 0, sizeof(*b));
    b->oturum_turu = KAYIT_OTURUM_OLCUM;
    b->kal_bicim = KAYIT_KAL_BICIM;
    b->hiz_ms = hiz_ms;
    b->unix_s = 0u;
    b->kart_ms = 1000u;
    b->acilis = 3u;
    memcpy(b->surum, "B71-test", 8);
    b->kal.normal.n = 16.5f;
    b->kal.normal.pga = 2.0f;
    b->kal.normal.kazanc = 1.0078125f;
    b->kal.normal.sifir_ham = -12;
    b->kal.normal.tau = 0.0029296875f;
    b->kal.yuksek.n = 312.5f;
    b->kal.yuksek.pga = 2.0f;
    b->kal.yuksek.kazanc = 0.9921875f;
    b->kal.yuksek.sifir_ham = 5;
    b->kal.yuksek.tau = 0.0030517578125f;
    b->kal.i_ofset = -3;
    b->kal.i_pga = 0.25f;
    b->kal.sont_ohm = 0.0048828125f;
    b->kal.i_duzeltme = 1.0f;
    b->kal.sebeke_hz = 50.0f;
    b->kal.faz_kal_us[0] = 12.5f;
    b->kal.faz_kal_us[1] = -3.25f;
}

/* ── senaryolar ── */

#if defined(SENARYO_BICIM)
static void senaryo(void)
{
    static const uint8_t dokuz[9] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    uint8_t p[KAYIT_BASLA_BAYT], p2[KAYIT_NOKTA_BAYT], h[KAYIT_BASLIK_BAYT];
    KayitNokta n, n2;
    KayitBasla b;

    metin("CRC "); hex32(kayit_crc_ekle(0u, dokuz, 9u)); satir();
    nokta_uret(12345u, &n);
    kayit_nokta_paketle(&n, p);
    metin("NOKTA "); hexdizi(p, KAYIT_NOKTA_BAYT); satir();
    kayit_nokta_coz(p, &n2);
    kayit_nokta_paketle(&n2, p2);
    metin("GIDISDONUS "); metin(memcmp(p, p2, KAYIT_NOKTA_BAYT) ? "0" : "1"); satir();
    basla_uret(&b, 200u);
    kayit_basla_paketle(&b, p);
    metin("BASLA "); hexdizi(p, KAYIT_BASLA_BAYT); satir();
    kayit_baslik_yaz(h, KAYIT_T_NOKTA, 7u, 42u, p, 20u);
    metin("BASLIK "); hexdizi(h, KAYIT_BASLIK_BAYT); satir();
    metin("BITTI\n");
}
#endif

/* ── giris ── */
#if !(defined(SENARYO_BICIM) || defined(SENARYO_NOKTACI) || defined(SENARYO_GUNLUK) \
      || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI))
#error "SENARYO_* tanimli degil"
#endif

int main(void)
{
    uart_baslat();
    senaryo();
    for (;;) {}
}
```

- [ ] **Step 6: Testin yeşil olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `B71: 21/21 kosul gecti`. Bu sayı N'den 7, B'den 14 iddianın toplamı.
Kırmızı çıkarsa sırayla şunlara bak:
- B2/B3 kırmızıysa: C ile Python alan sırası farklıdır. `_NOKTA` / `_BASLA_BAS` biçimleri başlıktaki ofset tablosuyla birebir aynı olmalı.
- B10 kırmızıysa: çıktıda C++ uyarısının metni yazar.

- [ ] **Step 7: Commit**

```bash
git add kod/olcum-karti-a3/kayit_bicim.h kopru/kayit_bicim.py uretim/avr/ornek_kayit.c uretim/test_kayit.py uretim/gecici.py
git commit -q -F - <<'EOF'
B71 kayit bicimi: C baslik + Python cozucu, ortak vektorlerle capraz test

Kayit = 16 B baslik (imza, tur, yuk, sira, oturum, CRC-32) + yuk + dolgu.
Nokta 36 B (V/A ham kod ort+min+maks, W watt). BASLA kalibrasyonun tam
kopyasini tasir. C++ olarak da uyarisiz. test_kayit.py 21/21.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Noktacı — `kayit_nokta.h`

**Files:**
- Create: `kod/olcum-karti-a3/kayit_nokta.h`
- Modify: `uretim/avr/ornek_kayit.c` (include + NOKTACI senaryosu)
- Modify: `uretim/test_kayit.py` (`bolum_noktaci`, `CPP_BASLIKLAR`)

**Interfaces:**
- Consumes: `KayitNokta`, `KN_*` (Task 2)
- Produces:
  - tip: `KayitNoktaci`
  - `kn_baslat(KayitNoktaci*, uint32_t hiz_ms, uint32_t simdi_ms, uint8_t menzil)`
  - `kn_ornek(KayitNoktaci*, uint32_t simdi_ms, uint8_t menzil, int16_t ham_v, int16_t ham_i, float watt, uint8_t hata, uint8_t v_doydu, KayitNokta *cikan) -> uint8_t`: 1 = `cikan`'a bir nokta yazıldı
  - `kn_zaman(KayitNoktaci*, uint32_t simdi_ms, KayitNokta *cikan) -> uint8_t`
  - `kn_kayip(KayitNoktaci*)`, `kn_bayrak(KayitNoktaci*, uint8_t)`
  - `KN_HATA_V = 0x01`, `KN_HATA_I = 0x02` (`hata` bitleri)

- [ ] **Step 1: Testi yaz**

`uretim/test_kayit.py`'de `CPP_BASLIKLAR` satırını değiştir:

```python
CPP_BASLIKLAR = ["kayit_bicim.h", "kayit_nokta.h"]
```

`bolum_bicim`'in altına ekle:

```python
# ── B71.P · noktaci ───────────────────────────────────────────────────
def beklenen(kart_ms: int, ornekler: list[tuple[int, int, float]],
             bayrak: int = 0, yuksek: bool = False) -> KB.Nokta:
    """Gecerli ornekler [(ham_v, ham_i, watt)] -> noktacinin uretmesi GEREKEN
    nokta. Toplamlar tam sayi (C'de int32/int64, tasma yok); ortalamalar
    C'nin float32 islem sirasiyla: (float)top / (float)n; W icin
    toplam mikrowatt tam sayisi ve * 1e-6f."""
    b = bayrak | (KB.KN_YUKSEK if yuksek else 0)
    n = len(ornekler)
    if n == 0:
        return KB.Nokta(kart_ms, 0, b, 0.0, 0, 0, 0.0, 0, 0, 0.0, 0.0, 0.0)

    def uw(w: float) -> int:                    # (int64_t)(w*1e6f +- 0.5f)
        m = f32(f32(w) * f32(1e6))
        return int(f32(m + (0.5 if f32(w) >= 0 else -0.5)))

    v = [o[0] for o in ornekler]
    i = [o[1] for o in ornekler]
    w = [f32(o[2]) for o in ornekler]
    return KB.Nokta(
        kart_ms, n, b,
        f32(f32(sum(v)) / f32(n)), min(v), max(v),
        f32(f32(sum(i)) / f32(n)), min(i), max(i),
        f32(f32(f32(sum(uw(x) for x in w)) / f32(n)) * f32(1e-6)),
        min(w), max(w))


def bolum_noktaci() -> None:
    print("\n── B71.P  noktaci: ham ornek -> ort + min + maks")
    gruplar, simdiki = {}, []
    for s in kos(derle("NOKTACI")):
        p = s.split()
        if p[:1] == ["P"]:
            simdiki.append(KB.nokta_coz(bytes.fromhex(p[1])))
        elif p[:1] and p[0] in ("S1", "S2", "S3", "S4"):
            gruplar[p[0]], simdiki = simdiki, []
    s1 = [beklenen(100 * (m + 1),
                   [(100 + j, -j, j * 0.5) for j in range(10 * m, 10 * m + 10)])
          for m in range(3)]
    ok("B71.P1 aralik sinirlari: 10 ms'lik 30 ornek -> 100/200/300 ms'de 3 nokta, birebir",
       gruplar.get("S1") == s1, str(gruplar.get("S1"))[:200])
    s2 = [beklenen(45, [(1000, 10, 1.0)] * 5),
          beklenen(145, [(2000, 20, 2.0)] * 5, yuksek=True)]
    ok("B71.P2 menzil degisince nokta ORADA kapanir (45 ms), kodlar karismaz",
       gruplar.get("S2") == s2, str(gruplar.get("S2"))[:200])
    ok("B71.P3 YUKSEK bayragi yalniz yuksek menzildeki noktada",
       [p.bayrak & KB.KN_YUKSEK for p in gruplar.get("S2", [])] == [0, KB.KN_YUKSEK])
    s3 = [beklenen(50, [(5, 1, 0.25), (7, 3, 0.75)],
                   bayrak=KB.KN_V_HATA | KB.KN_V_DOYDU | KB.KN_KAYIP_ONCE),
          beklenen(310, [(1, 1, 1.0)], bayrak=KB.KN_DURAKLAMA)]
    ok("B71.P4 hatali ornek istatistige girmez; hata/doyma/kayip/duraklama dogru noktada",
       gruplar.get("S3") == s3, str(gruplar.get("S3"))[:200])
    s4 = [beklenen(1000000, [(32767, -32768, 7000.0)] * 40000)]
    ok("B71.P5 40 000 uc deger ornek tasmadan toplanir (int32/int64)",
       gruplar.get("S4") == s4, str(gruplar.get("S4"))[:200])
```

`BOLUMLER`'i güncelle:

```python
BOLUMLER = [bolum_nor, bolum_bicim, bolum_noktaci]
```

- [ ] **Step 2: Testin kırmızı olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `avr-gcc derleyemedi (SENARYO_NOKTACI)`, çünkü `senaryo` tanımsız ya da `kayit_nokta.h` yok.

- [ ] **Step 3: `kod/olcum-karti-a3/kayit_nokta.h` yaz**

```c
#ifndef KAYIT_NOKTA_H
#define KAYIT_NOKTA_H
/*
 * B71 — NOKTACI: ham ornekleri kayit noktasina toplar (olcum cekirdeginde,
 * her ornekte cagrilir).
 *
 * Kullanicinin kurali (2026-09-29): "sicramalari goz onunden alacak bir
 * islem asla istemiyorum". Bu yuzden her nokta ORTALAMANIN yaninda aralik
 * icindeki EN DUSUK ve EN YUKSEK HAM kodu da tasir: 200 ms'lik bir noktada
 * 5 ms'lik bir sicrama ortalamada erir ama min/maks'ta kalir.
 *
 * Kurallar:
 *   * Aralik `hiz_ms`; nokta cizelgesi kaymaz (bas += hiz).
 *   * Menzil degisirse nokta O ANDA kapanir: NORMAL ve YUKSEK kanalin kodu
 *     ayni noktada ASLA karismaz (ayni kod iki menzilde 19 kat farkli volt).
 *   * Okunamayan ornek (ADS hatasi) istatistige GIRMEZ, bayrak birakir.
 *   * Ornek gelmeyen aralik (skop ADS'i susturdu) bos nokta URETMEZ;
 *     sonraki nokta KN_DURAKLAMA tasir.
 *   * Toplamlar tam sayi: kod int32 (65535 x 32768 sigar), guc int64
 *     mikrowatt. float toplam uzun aralikta hassasiyet yerdi.
 */
#include "kayit_bicim.h"

#define KN_HATA_V 0x01u   /* kn_ornek `hata`: gerilim ADS'i okunamadi */
#define KN_HATA_I 0x02u   /* kn_ornek `hata`: akim ADS'i okunamadi */

typedef struct {
    uint32_t hiz_ms;
    uint32_t bas_ms;       /* bu noktanin basladigi an */
    uint8_t  menzil;       /* bu noktanin menzili (0/1) */
    uint8_t  ornek_var;    /* bu noktaya (gecerli ya da hatali) ornek geldi */
    uint8_t  bayrak;       /* bu noktanin birikmis KN_* bayraklari */
    uint8_t  bekleyen;     /* SONRAKI noktaya tasinacak bayraklar */
    uint16_t n;
    int32_t  v_top, i_top;
    int64_t  w_top_uw;
    int16_t  v_min, v_maks, i_min, i_maks;
    float    w_min, w_maks;
} KayitNoktaci;

static inline void kn__sifirla(KayitNoktaci *k)
{
    k->ornek_var = 0u;
    k->n = 0u;
    k->v_top = 0;
    k->i_top = 0;
    k->w_top_uw = 0;
    k->v_min = 32767;
    k->i_min = 32767;
    k->v_maks = -32768;
    k->i_maks = -32768;
    k->w_min = 0.0f;
    k->w_maks = 0.0f;
    k->bayrak = k->bekleyen;
    k->bekleyen = 0u;
}

static inline void kn_baslat(KayitNoktaci *k, uint32_t hiz_ms, uint32_t simdi_ms,
                             uint8_t menzil)
{
    k->hiz_ms = hiz_ms ? hiz_ms : 1u;
    k->bas_ms = simdi_ms;
    k->menzil = menzil ? 1u : 0u;
    k->bekleyen = 0u;
    kn__sifirla(k);
}

static inline void kn__kapat(KayitNoktaci *k, uint32_t bitis_ms, KayitNokta *c)
{
    c->kart_ms = bitis_ms;
    c->n = k->n;
    c->bayrak = (uint8_t)(k->bayrak | (k->menzil ? KN_YUKSEK : 0u));
    if (k->n) {
        c->v_ort_kod = (float)k->v_top / (float)k->n;
        c->i_ort_kod = (float)k->i_top / (float)k->n;
        c->w_ort = (float)k->w_top_uw / (float)k->n * 1.0e-6f;
        c->v_min_kod = k->v_min;
        c->v_maks_kod = k->v_maks;
        c->i_min_kod = k->i_min;
        c->i_maks_kod = k->i_maks;
        c->w_min = k->w_min;
        c->w_maks = k->w_maks;
    } else {
        c->v_ort_kod = 0.0f;
        c->i_ort_kod = 0.0f;
        c->w_ort = 0.0f;
        c->v_min_kod = c->v_maks_kod = 0;
        c->i_min_kod = c->i_maks_kod = 0;
        c->w_min = c->w_maks = 0.0f;
    }
    kn__sifirla(k);
}

/* Bir ornek ekle. Once sinir: menzil degistiyse ya da aralik dolduysa
   ELDEKI nokta `cikan`a yazilir ve 1 doner; ornek YENI noktaya girer. */
static inline uint8_t kn_ornek(KayitNoktaci *k, uint32_t simdi_ms, uint8_t menzil,
                               int16_t ham_v, int16_t ham_i, float watt,
                               uint8_t hata, uint8_t v_doydu, KayitNokta *cikan)
{
    uint8_t cikti = 0u;
    menzil = menzil ? 1u : 0u;
    if (k->ornek_var) {
        if (menzil != k->menzil) {
            kn__kapat(k, simdi_ms, cikan);
            cikti = 1u;
            k->bas_ms = simdi_ms;
        } else if ((uint32_t)(simdi_ms - k->bas_ms) >= k->hiz_ms) {
            kn__kapat(k, k->bas_ms + k->hiz_ms, cikan);
            cikti = 1u;
            k->bas_ms += k->hiz_ms;
            if ((uint32_t)(simdi_ms - k->bas_ms) >= k->hiz_ms) {
                k->bas_ms = simdi_ms;
                k->bayrak |= KN_DURAKLAMA;
            }
        }
    } else if ((uint32_t)(simdi_ms - k->bas_ms) >= k->hiz_ms) {
        /* ornek gelmeyen aralik(lar): nokta URETILMEZ, zaman ilerler */
        k->bas_ms = simdi_ms;
        k->bayrak |= KN_DURAKLAMA;
    }
    k->menzil = menzil;
    k->ornek_var = 1u;
    if (hata & KN_HATA_V) k->bayrak |= KN_V_HATA;
    if (hata & KN_HATA_I) k->bayrak |= KN_I_HATA;
    if (v_doydu) k->bayrak |= KN_V_DOYDU;
    if (!hata && k->n < 0xFFFFu) {
        int64_t w = (int64_t)(watt * 1.0e6f + (watt >= 0.0f ? 0.5f : -0.5f));
        if (k->n == 0u) {
            k->w_min = watt;
            k->w_maks = watt;
        } else {
            if (watt < k->w_min) k->w_min = watt;
            if (watt > k->w_maks) k->w_maks = watt;
        }
        k->n++;
        k->v_top += ham_v;
        k->i_top += ham_i;
        k->w_top_uw += w;
        if (ham_v < k->v_min) k->v_min = ham_v;
        if (ham_v > k->v_maks) k->v_maks = ham_v;
        if (ham_i < k->i_min) k->i_min = ham_i;
        if (ham_i > k->i_maks) k->i_maks = ham_i;
    }
    return cikti;
}

/* Ornek gelmese de (skop duraklamasi) aralik dolduysa noktayi kapat. */
static inline uint8_t kn_zaman(KayitNoktaci *k, uint32_t simdi_ms, KayitNokta *cikan)
{
    if (!k->ornek_var || (uint32_t)(simdi_ms - k->bas_ms) < k->hiz_ms) return 0u;
    kn__kapat(k, k->bas_ms + k->hiz_ms, cikan);
    k->bas_ms += k->hiz_ms;
    return 1u;
}

/* Kuyruk doluydu, az once uretilen nokta dustu: DEVAM EDEN noktaya isaret. */
static inline void kn_kayip(KayitNoktaci *k) { k->bayrak |= KN_KAYIP_ONCE; }

static inline void kn_bayrak(KayitNoktaci *k, uint8_t b) { k->bayrak |= b; }

#endif /* KAYIT_NOKTA_H */
```

- [ ] **Step 4: Harness'e NOKTACI senaryosunu ekle**

`uretim/avr/ornek_kayit.c`'de `#include "kayit_bicim.h"` satırının altına ekle:

```c
#include "kayit_nokta.h"
```

`/* ── giris ── */` satırının hemen üstüne ekle:

```c
#if defined(SENARYO_NOKTACI)
static void p_yaz(const KayitNokta *p)
{
    uint8_t b[KAYIT_NOKTA_BAYT];
    kayit_nokta_paketle(p, b);
    metin("P ");
    hexdizi(b, KAYIT_NOKTA_BAYT);
    satir();
}

static void senaryo(void)
{
    KayitNoktaci k;
    KayitNokta c;
    uint32_t t;
    int16_t i;

    /* S1: 100 ms aralik, 10 ms'de bir ornek v=100+i, i_kod=-i, w=i/2 */
    kn_baslat(&k, 100u, 0u, 0u);
    for (i = 0; i < 30; i++) {
        t = (uint32_t)i * 10u;
        if (kn_ornek(&k, t, 0u, (int16_t)(100 + i), (int16_t)(-i),
                     (float)i * 0.5f, 0u, 0u, &c)) p_yaz(&c);
    }
    if (kn_zaman(&k, 300u, &c)) p_yaz(&c);
    metin("S1\n");

    /* S2: t=0..40 NORMAL (1000), t=45..85 YUKSEK (2000) */
    kn_baslat(&k, 100u, 0u, 0u);
    for (i = 0; i < 5; i++)
        if (kn_ornek(&k, (uint32_t)i * 10u, 0u, 1000, 10, 1.0f, 0u, 0u, &c)) p_yaz(&c);
    for (i = 0; i < 5; i++)
        if (kn_ornek(&k, 45u + (uint32_t)i * 10u, 1u, 2000, 20, 2.0f, 0u, 0u, &c)) p_yaz(&c);
    if (kn_zaman(&k, 145u, &c)) p_yaz(&c);
    metin("S2\n");

    /* S3: hatali ornek, doyma, kuyruk kaybi, uzun duraklama */
    kn_baslat(&k, 50u, 0u, 0u);
    kn_ornek(&k, 0u, 0u, 5, 1, 0.25f, 0u, 0u, &c);
    kn_ornek(&k, 10u, 0u, 9999, 1, 99.0f, KN_HATA_V, 0u, &c);
    kn_ornek(&k, 20u, 0u, 7, 3, 0.75f, 0u, 1u, &c);
    kn_kayip(&k);
    if (kn_ornek(&k, 260u, 0u, 1, 1, 1.0f, 0u, 0u, &c)) p_yaz(&c);
    if (kn_zaman(&k, 310u, &c)) p_yaz(&c);
    metin("S3\n");

    /* S4: 40 000 uc deger ornek tek noktada — int32/int64 tasmaz */
    kn_baslat(&k, 1000000UL, 0u, 0u);
    for (t = 0; t < 40000UL; t++)
        kn_ornek(&k, t, 0u, 32767, -32768, 7000.0f, 0u, 0u, &c);
    if (kn_zaman(&k, 1000000UL, &c)) p_yaz(&c);
    metin("S4\nBITTI\n");
}
#endif
```

- [ ] **Step 5: Testin yeşil olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `B71: 28/28 kosul gecti`. N ve B'nin 21 iddiasına P'nin 7 iddiası ekleniyor.

- [ ] **Step 6: Commit**

```bash
git add kod/olcum-karti-a3/kayit_nokta.h uretim/avr/ornek_kayit.c uretim/test_kayit.py
git commit -q -F - <<'EOF'
B71 noktaci: ham ornek -> ort + min + maks, menzil sinirinda bolunme

Kisa sicrama min/maks'ta kalir (kullanicinin kurali). Hatali ornek
istatistige girmez; kayip ve duraklama bayraklari. test_kayit.py 28/28.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Günlük — `kayit_gunluk.h`

**Files:**
- Create: `kod/olcum-karti-a3/kayit_gunluk.h`
- Modify: `uretim/avr/ornek_kayit.c` (include + NOR sürücüsü + GUNLUK senaryosu)
- Modify: `uretim/test_kayit.py` (`bolum_gunluk`, `CPP_BASLIKLAR`)

**Interfaces:**
- Consumes: `kayit_bicim.h` (Task 2)
- Produces:
  - tipler: `KayitFlas {oku, yaz, sil, baglam}` (hepsi 0 = başarı), `KayitSektor {ilk, son}`, `KayitOzet`, `KayitGunluk`
  - `KayitOzet` alanları: `id, hiz_ms, unix_s, kart_ms, acilis, ilk_sira, son_sira, nokta_sonraki, basla_adres, tur, durum, basi_silindi`
  - `kg_kur(g, const KayitFlas*, sektor_adet, KayitSektor*, KayitOzet*, dizin_kap) -> int`
  - `kg_ac(g, sira_taban) -> int`: kurtarma
  - `kg_ekle(g, tur, oturum, yuk, yuk_bayt) -> int32_t`: sıra (>0) ya da `KG_*`
  - `kg_ilerle(g) -> int`
  - `kg_onayla(g, sira)`
  - `kg_oku(g, sira, hedef, kap, *ilk, *son) -> uint32_t` bayt
  - `kg_bicimle(g) -> int`
  - `kg_kullanilan(g)`, `kg_onaysiz(g) -> uint32_t` bayt; `kg_binde(g, bayt) -> uint16_t`
  - `kg_basla_oku(g, adres, KayitBasla*) -> int`
  - sabitler: `KG_TAMAM/DOLU/HATA/BUYUK/YOK`, `KD_ACIK/KD_BITTI`, `KG_ADRES_YOK`, `KAYIT_SEKTOR`

- [ ] **Step 1: Testi yaz**

`CPP_BASLIKLAR`'ı güncelle:

```python
CPP_BASLIKLAR = ["kayit_bicim.h", "kayit_nokta.h", "kayit_gunluk.h"]
```

`bolum_noktaci`'nin altına ekle:

```python
# ── B71.G · gunluk ────────────────────────────────────────────────────
def _durum(satirlar: list[str], ad: str) -> dict | None:
    for s in satirlar:
        p = s.split()
        if p[:1] == [ad]:
            return {k: int(v) for k, v in (x.split("=") for x in p[1:])}
    return None


def _g(sonraki, bas, ofset, onay=0, bozuk=0, dolu=0, silinen=0, kull=0,
       onaysiz=0, dizin=0) -> dict:
    return dict(sonraki=sonraki, bas=bas, ofset=ofset, onay=onay, bozuk=bozuk,
                dolu=dolu, silinen=silinen, kull=kull, onaysiz=onaysiz,
                dizin=dizin)


def bolum_gunluk() -> None:
    """Beklenen sayilar elle: kayit 12 B -> 28, 13 B -> 32, 100 B -> 116
    bayt; 512'lik sektore 4 x 116 = 464 sigar. `kull`/`onaysiz`: yazilan
    (bas) sektor dolu kismiyla, OTEKILER TAM sektor sayilir — kuyruktaki
    bos yer sektor silinene kadar kullanilamaz. Ornek G4: sektor 0..6
    7 x 512 + sektor 7'de 464 = 4048."""
    print("\n── B71.G  gunluk: yazma · okuma · kurtarma · temizlik")
    flas = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    sat = kos(derle("GUNLUK"), flas)
    ek = [int(p[0]) for p in alanlar(sat, "EK")]
    oku = alanlar(sat, "OKU")
    veri = [bytes.fromhex(p[0]) if p else b"" for p in alanlar(sat, "VERI")]
    d = {a: _durum(sat, a) for a in [f"G{i}" for i in range(1, 12)]}
    ok("B71.G1 bos flas: sira 1'den, ilk yazma sektor 0'i SILIP kullanacak",
       d["G1"] == _g(1, 7, 512), str(d["G1"]))
    ok("B71.G2 uc kayit 1,2,3; 4 bayt dolgu dogru (28+32+116 = 176)",
       ek[:3] == [1, 2, 3] and d["G2"] == _g(4, 0, 176, kull=176, onaysiz=176),
       str(d["G2"]))
    ok("B71.G3 sira 2'den okuma: iki kayit, 148 bayt", oku[0] == ["148", "2", "3"],
       str(oku[0]))
    kay = KB.akis_coz(veri[0])
    ok("B71.G3 okunan baytlar Python'da cozuluyor (sira 2,3; yuk birebir)",
       [k.sira for k in kay] == [2, 3] and kay[0].yuk == bytes(range(13))
       and kay[1].yuk == bytes(range(100)))
    ok("B71.G4 yeniden acilis ayni durumu kuruyor", d["G3"] == d["G2"], str(d["G3"]))
    ok("B71.G5 onay yokken bellek DOLAR: 30 kayit sigdi, 31. KG_DOLU",
       alanlar(sat, "DOLU")[0] == ["31", "1"], str(alanlar(sat, "DOLU")))
    ok("B71.G5 dolulukta HICBIR sektor silinmedi (onaysiz veri korunur)",
       d["G4"] == _g(34, 7, 464, dolu=1, kull=4048, onaysiz=4048), str(d["G4"]))
    ok("B71.G6 sahte buyuk onay kirpildi: onay = son yazilan sira (33)",
       d["G5"] == _g(34, 7, 464, onay=33, dolu=1, kull=4048, onaysiz=0),
       str(d["G5"]))
    ok("B71.G7 onaydan sonra en eski sektor silinip yeniden kullanildi",
       ek[3] == 34 and d["G6"] == _g(35, 0, 116, onay=33, silinen=1, kull=3700,
                                     onaysiz=116), str(d["G6"]))
    ok("B71.G8 silinmis araliktan okuma BOSLUGU soyler (ilk 6 > istenen 1)",
       oku[1] == ["116", "6", "6"], str(oku[1]))
    ok("B71.G9 okuma kapasitesi kaydi bolmez (116 > 100 -> 0 bayt)",
       oku[2] == ["0", "0", "0"], str(oku[2]))
    ok("B71.G10 bicimleme sirayi korur (35)",
       d["G7"] == _g(35, 7, 512, onay=34, silinen=1), str(d["G7"]))
    ok("B71.G11 bos flasta taban sira: numara TEKRAR VERILMEZ (35)",
       d["G8"] == _g(35, 7, 512) and ek[4:5] == [35], f"{d['G8']} EK={ek[4:5]}")
    ok("B71.G12 cop sektor veri sanilmaz (bozuk=1), yazma kaldigi yerden",
       d["G9"] == _g(36, 0, 28, bozuk=1, kull=28, onaysiz=28), str(d["G9"]))
    ok("B71.G13 yarim kayitli sektore bir daha yazilmaz (ofset 512)",
       d["G10"] == _g(36, 0, 512, bozuk=2, kull=512, onaysiz=512), str(d["G10"]))
    ok("B71.G14 sonraki kayit yeni sektore (sektor 1)",
       ek[5:6] == [36] and d["G11"] == _g(37, 1, 28, bozuk=2, kull=540,
                                          onaysiz=540), str(d["G11"]))
    kay = KB.akis_coz(veri[3]) if len(veri) > 3 else []
    ok("B71.G15 esitleme okumasi yarim kaydi ATLAR: yalniz gecerli 35 ve 36",
       oku[3:4] == [["56", "35", "36"]] and [k.sira for k in kay] == [35, 36],
       str(oku[3:4]))
```

`BOLUMLER`'i güncelle:

```python
BOLUMLER = [bolum_nor, bolum_bicim, bolum_noktaci, bolum_gunluk]
```

- [ ] **Step 2: Testin kırmızı olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `avr-gcc derleyemedi (SENARYO_GUNLUK)`

- [ ] **Step 3: `kod/olcum-karti-a3/kayit_gunluk.h` yaz**

```c
#ifndef KAYIT_GUNLUK_H
#define KAYIT_GUNLUK_H
/*
 * B71 — KAYIT GUNLUGU: NOR flas uzerinde yalniz-sona-ekleyen halka.
 *
 * Flas KAYIT_SEKTOR baytlik sektorlere bolunur (ESP32: 4096 = silme
 * birimi). Kayitlar bir sektorun basindan itibaren arka arkaya yazilir,
 * sektor sinirini ASLA asmaz. Sektorler halka sirasiyla kullanilir; bir
 * sektor kullanilmadan once HER ZAMAN silinir — kesik bir silmenin
 * coplugu veri sanilmasin diye.
 *
 * AKILLI TEMIZLIK (tasarim §5): en eski sektor ancak icindeki son kaydin
 * sirasi `onay`dan buyuk DEGILSE silinir, yani en az bir cihaz o veriyi
 * kalici diske yazdigini bildirdiyse. Aksi halde KG_DOLU: onaysiz veri
 * ASLA silinmez.
 *
 * KURTARMA (kg_ac): her sektor bastan taranir; CRC'si tutmayan ilk
 * kayitta durulur. Yazilan (en yeni) sektorun geri kalani 0xFF degilse o
 * sektore bir daha yazilmaz: yarim kaydin ardina yazmak yeni kaydi da
 * bozardi.
 *
 * Flas erisimi KayitFlas islev isaretcileriyle: kartta esp_partition_*
 * (1A-2), AVR testinde emule NOR (uretim/avr/nor_flas.py). Butun bellek
 * (sektor tablosu, oturum dizini) CAGIRANDAN gelir; burada malloc yok.
 */
#include "kayit_bicim.h"

#ifndef KAYIT_SEKTOR
#define KAYIT_SEKTOR 4096UL
#endif

#define KG_TAMAM   0
#define KG_DOLU   (-1)   /* onaysiz veri yuzunden yer yok */
#define KG_HATA   (-2)   /* flas islemi basarisiz ya da gecersiz arguman */
#define KG_BUYUK  (-3)   /* kayit bir sektore sigmiyor */
#define KG_YOK    (-4)   /* aktif oturum yok */

#define KD_ACIK   1u
#define KD_BITTI  2u
#define KG_ADRES_YOK 0xFFFFFFFFUL
#define KG__PARCA 32u

typedef struct {
    int (*oku)(void *baglam, uint32_t adres, void *hedef, uint32_t n);
    int (*yaz)(void *baglam, uint32_t adres, const void *kaynak, uint32_t n);
    int (*sil)(void *baglam, uint32_t sektor_adres);
    void *baglam;
} KayitFlas;

typedef struct { uint32_t ilk, son; } KayitSektor;   /* 0,0 = bos */

typedef struct {
    uint32_t id;
    uint32_t hiz_ms, unix_s, kart_ms, acilis;
    uint32_t ilk_sira, son_sira;   /* flasta KALAN kayitlarinin araligi */
    uint32_t nokta_sonraki;        /* oturumun sonraki noktasinin sirasi */
    uint32_t basla_adres;          /* son BASLA/TEKRAR'in adresi; KG_ADRES_YOK */
    uint8_t  tur, durum, basi_silindi;
} KayitOzet;

typedef struct KayitGunluk_ {
    KayitFlas    f;
    uint32_t     sektor_adet;
    KayitSektor *sektor;
    KayitOzet   *dizin;
    uint16_t     dizin_kap, dizin_adet;
    uint32_t     bas, bas_ofset;       /* yazilan sektor ve icindeki yer */
    uint32_t     sonraki_sira, onay;
    uint32_t     bozuk;                /* son kg_ac'ta atilan cop/yarim */
    uint32_t     silinen_sektor;       /* son kg_ac'tan beri temizlik */
    uint8_t      dolu;
} KayitGunluk;

typedef void (*KgBesle)(KayitGunluk *g, const KayitBaslik *h, uint32_t adres);

static inline int kg_kur(KayitGunluk *g, const KayitFlas *f, uint32_t sektor_adet,
                         KayitSektor *sektor, KayitOzet *dizin, uint16_t dizin_kap)
{
    memset(g, 0, sizeof(*g));
    if (sektor_adet < 2u) return KG_HATA;
    g->f = *f;
    g->sektor_adet = sektor_adet;
    g->sektor = sektor;
    g->dizin = dizin;
    g->dizin_kap = dizin_kap;
    g->sonraki_sira = 1u;
    g->bas = sektor_adet - 1u;
    g->bas_ofset = KAYIT_SEKTOR;
    memset(sektor, 0, (size_t)sektor_adet * sizeof(KayitSektor));
    return KG_TAMAM;
}

/* `adres`teki kaydi dogrula. 1 gecerli, 0 bos, -1 cop/yarim. */
static inline int8_t kg__kayit_dogrula(KayitGunluk *g, uint32_t adres,
                                       uint32_t sektor_sonu, KayitBaslik *h)
{
    uint8_t b[KAYIT_BASLIK_BAYT], parca[KG__PARCA];
    uint32_t c, kalan, a;
    int8_t d;
    if (adres + KAYIT_BASLIK_BAYT > sektor_sonu) return 0;
    if (g->f.oku(g->f.baglam, adres, b, KAYIT_BASLIK_BAYT)) return -1;
    d = kayit_baslik_coz(b, h);
    if (d <= 0) return d;
    if (adres + kayit_toplam_bayt(h->yuk_bayt) > sektor_sonu) return -1;
    c = kayit_crc_ekle(0u, b, 12u);
    a = adres + KAYIT_BASLIK_BAYT;
    kalan = h->yuk_bayt;
    while (kalan) {
        uint32_t n = kalan < KG__PARCA ? kalan : KG__PARCA;
        if (g->f.oku(g->f.baglam, a, parca, n)) return -1;
        c = kayit_crc_ekle(c, parca, n);
        a += n;
        kalan -= n;
    }
    return (c == h->crc) ? 1 : -1;
}

static inline uint8_t kg__ff_mi(KayitGunluk *g, uint32_t a, uint32_t son)
{
    uint8_t parca[KG__PARCA];
    while (a < son) {
        uint32_t n = son - a;
        uint8_t i;
        if (n > KG__PARCA) n = KG__PARCA;
        if (g->f.oku(g->f.baglam, a, parca, n)) return 0u;
        for (i = 0; i < (uint8_t)n; i++) {
            if (parca[i] != 0xFFu) return 0u;
        }
        a += n;
    }
    return 1u;
}

/* ─────────────────────────────── oturum dizini */
static inline KayitOzet *kg__ozet(KayitGunluk *g, uint32_t id)
{
    uint16_t i;
    KayitOzet *o;
    for (i = 0; i < g->dizin_adet; i++) {
        if (g->dizin[i].id == id) return &g->dizin[i];
    }
    if (!g->dizin_kap) return 0;
    if (g->dizin_adet == g->dizin_kap) {        /* en eskiyi dusur */
        memmove(&g->dizin[0], &g->dizin[1],
                (size_t)(g->dizin_kap - 1u) * sizeof(KayitOzet));
        g->dizin_adet--;
    }
    o = &g->dizin[g->dizin_adet++];
    memset(o, 0, sizeof(*o));
    o->id = id;
    o->basla_adres = KG_ADRES_YOK;
    o->basi_silindi = 1u;
    o->durum = KD_ACIK;
    return o;
}

/* `y`: yukun ilk `n` bayti (en fazla 20). */
static inline void kg__dizin_isle(KayitGunluk *g, const KayitBaslik *h,
                                  uint32_t adres, const uint8_t *y, uint16_t n)
{
    KayitOzet *o;
    if (!h->oturum) return;
    o = kg__ozet(g, h->oturum);
    if (!o) return;
    if (!o->ilk_sira) o->ilk_sira = h->sira;
    o->son_sira = h->sira;
    switch (h->tur) {
    case KAYIT_T_BASLA:
    case KAYIT_T_TEKRAR:
        if (n >= 20u) {
            o->tur = y[0];
            o->hiz_ms = kayit_o32(y + 4);
            o->unix_s = kayit_o32(y + 8);
            o->kart_ms = kayit_o32(y + 12);
            o->acilis = kayit_o32(y + 16);
        }
        o->basla_adres = adres;
        if (h->tur == KAYIT_T_BASLA) {
            o->basi_silindi = 0u;
            o->nokta_sonraki = 0u;
        }
        break;
    case KAYIT_T_NOKTA:
        if (n >= 4u && h->yuk_bayt >= 4u)
            o->nokta_sonraki = kayit_o32(y)
                             + (uint32_t)(h->yuk_bayt - 4u) / KAYIT_NOKTA_BAYT;
        break;
    case KAYIT_T_DEVAM:
        if (n >= 16u) o->nokta_sonraki = kayit_o32(y + 12);
        o->durum = KD_ACIK;
        break;
    case KAYIT_T_BITIR:
        o->durum = KD_BITTI;
        break;
    default:
        break;
    }
}

static inline void kg__besle(KayitGunluk *g, const KayitBaslik *h, uint32_t adres)
{
    uint8_t y[20];
    uint16_t n = (uint16_t)(h->yuk_bayt < 20u ? h->yuk_bayt : 20u);
    if (n && g->f.oku(g->f.baglam, adres + KAYIT_BASLIK_BAYT, y, n)) return;
    kg__dizin_isle(g, h, adres, y, n);
}

/* Sektoru bastan tara. Donus: son gecerli kaydin bittigi ofset.
   *temiz = 1: o ofsetten sektor sonuna kadar her bayt 0xFF. */
static inline uint32_t kg__sektor_tara(KayitGunluk *g, uint32_t s, KgBesle besle,
                                       uint8_t *temiz)
{
    uint32_t bas = s * KAYIT_SEKTOR, son = bas + KAYIT_SEKTOR, a = bas;
    KayitBaslik h;
    int8_t d;
    g->sektor[s].ilk = 0u;
    g->sektor[s].son = 0u;
    for (;;) {
        d = kg__kayit_dogrula(g, a, son, &h);
        if (d == 1 && g->sektor[s].son && h.sira <= g->sektor[s].son) d = -1;
        if (d != 1) break;
        if (!g->sektor[s].ilk) g->sektor[s].ilk = h.sira;
        g->sektor[s].son = h.sira;
        if (besle) besle(g, &h, a);
        a += kayit_toplam_bayt(h.yuk_bayt);
    }
    if (d < 0) {
        g->bozuk++;
        *temiz = 0u;
    } else {
        *temiz = kg__ff_mi(g, a, son);
    }
    return a - bas;
}

/* KURTARMA. `sira_taban`: bu siranin altinda numara verilmez (bicimleme
   sonrasi NVS'ten gelir; 1A-2). */
static inline int kg_ac(KayitGunluk *g, uint32_t sira_taban)
{
    uint32_t s, i, en_ilk = 0u, en_son = 0u, bas = 0u, ofset;
    uint8_t temiz, bos = 1u;
    KayitBaslik h;
    g->dizin_adet = 0u;
    g->onay = 0u;
    g->bozuk = 0u;
    g->silinen_sektor = 0u;
    g->dolu = 0u;
    /* 1. gecis: en yeni sektor = ilk kaydinin sirasi en buyuk olan */
    for (s = 0; s < g->sektor_adet; s++) {
        if (kg__kayit_dogrula(g, s * KAYIT_SEKTOR, (s + 1u) * KAYIT_SEKTOR, &h) == 1
            && h.sira > en_ilk) {
            en_ilk = h.sira;
            bas = s;
            bos = 0u;
        }
    }
    /* 2. gecis: halka sirasiyla; bas'tan SONRAKI sektor en eskidir */
    g->bas = bas;
    g->bas_ofset = KAYIT_SEKTOR;
    for (i = 1; i <= g->sektor_adet; i++) {
        s = (bas + i) % g->sektor_adet;
        ofset = kg__sektor_tara(g, s, kg__besle, &temiz);
        if (g->sektor[s].son > en_son) en_son = g->sektor[s].son;
        if (s == bas && temiz) g->bas_ofset = ofset;
    }
    if (bos) { g->bas = g->sektor_adet - 1u; g->bas_ofset = KAYIT_SEKTOR; }
    g->sonraki_sira = en_son + 1u;
    if (g->sonraki_sira < sira_taban) g->sonraki_sira = sira_taban;
    return KG_TAMAM;
}

/* Silinecek sektorun izini dizinden cikar. */
static inline void kg__sektor_dusur(KayitGunluk *g, uint32_t s)
{
    uint32_t son = g->sektor[s].son, a0 = s * KAYIT_SEKTOR;
    uint16_t i, j = 0u;
    for (i = 0; i < g->dizin_adet; i++) {
        KayitOzet *o = &g->dizin[i];
        if (o->son_sira <= son) continue;          /* butunuyle gitti */
        if (o->ilk_sira <= son) {
            o->ilk_sira = son + 1u;
            o->basi_silindi = 1u;
        }
        if (o->basla_adres != KG_ADRES_YOK && o->basla_adres >= a0
            && o->basla_adres < a0 + KAYIT_SEKTOR) o->basla_adres = KG_ADRES_YOK;
        if (j != i) g->dizin[j] = *o;
        j++;
    }
    g->dizin_adet = j;
}

/* Sonraki sektore gec: gerekirse AKILLI TEMIZLIK, her durumda SIL. */
static inline int kg_ilerle(KayitGunluk *g)
{
    uint32_t s = (g->bas + 1u) % g->sektor_adet;
    if (g->sektor[s].ilk) {
        if (g->sektor[s].son > g->onay) { g->dolu = 1u; return KG_DOLU; }
        kg__sektor_dusur(g, s);
        g->silinen_sektor++;
    }
    if (g->f.sil(g->f.baglam, s * KAYIT_SEKTOR)) return KG_HATA;
    g->sektor[s].ilk = 0u;
    g->sektor[s].son = 0u;
    g->bas = s;
    g->bas_ofset = 0u;
    g->dolu = 0u;
    return KG_TAMAM;
}

/* Kayit ekle. Donus: verilen sira (>0) ya da KG_*. */
static inline int32_t kg_ekle(KayitGunluk *g, uint8_t tur, uint32_t oturum,
                              const uint8_t *yuk, uint16_t yuk_bayt)
{
    static const uint8_t sifir[3] = {0u, 0u, 0u};
    uint8_t b[KAYIT_BASLIK_BAYT];
    KayitBaslik h;
    uint32_t toplam = kayit_toplam_bayt(yuk_bayt), adres, dolgu;
    int r;
    if (toplam > KAYIT_SEKTOR) return KG_BUYUK;
    if (g->bas_ofset + toplam > KAYIT_SEKTOR) {
        r = kg_ilerle(g);
        if (r) return r;
    }
    h.tur = tur;
    h.yuk_bayt = yuk_bayt;
    h.sira = g->sonraki_sira;
    h.oturum = oturum;
    kayit_baslik_yaz(b, tur, h.sira, oturum, yuk, yuk_bayt);
    h.crc = kayit_o32(b + 12);
    adres = g->bas * KAYIT_SEKTOR + g->bas_ofset;
    dolgu = toplam - KAYIT_BASLIK_BAYT - yuk_bayt;
    if (g->f.yaz(g->f.baglam, adres, b, KAYIT_BASLIK_BAYT)
        || (yuk_bayt && g->f.yaz(g->f.baglam, adres + KAYIT_BASLIK_BAYT, yuk, yuk_bayt))
        || (dolgu && g->f.yaz(g->f.baglam, adres + KAYIT_BASLIK_BAYT + yuk_bayt,
                              sifir, dolgu))) {
        g->bas_ofset = KAYIT_SEKTOR;   /* sektorun durumu belirsiz: bir daha yazma */
        return KG_HATA;
    }
    if (!g->sektor[g->bas].ilk) g->sektor[g->bas].ilk = h.sira;
    g->sektor[g->bas].son = h.sira;
    g->bas_ofset += toplam;
    g->sonraki_sira = h.sira + 1u;
    kg__dizin_isle(g, &h, adres, yuk, (uint16_t)(yuk_bayt < 20u ? yuk_bayt : 20u));
    return (int32_t)h.sira;
}

/* Bir cihaz `sira`ya kadar KALICI aldigini bildirdi. */
static inline void kg_onayla(KayitGunluk *g, uint32_t sira)
{
    if (g->sonraki_sira && sira >= g->sonraki_sira) sira = g->sonraki_sira - 1u;
    if (sira > g->onay) g->onay = sira;
}

/* Esitleme: `sira` ve sonrasini, flasta nasilsa oyle, `kap` bayta kadar
   kopyala. Kayit asla bolunmez. *ilk > istenen ise arada silinmis veri
   var (bosluk). */
static inline uint32_t kg_oku(KayitGunluk *g, uint32_t sira, uint8_t *hedef,
                              uint32_t kap, uint32_t *ilk, uint32_t *son)
{
    uint8_t b[KAYIT_BASLIK_BAYT];
    KayitBaslik h;
    uint32_t i, s, a, bitis, t, n = 0u;
    *ilk = 0u;
    *son = 0u;
    if (!sira) sira = 1u;
    for (i = 1; i <= g->sektor_adet; i++) {
        s = (g->bas + i) % g->sektor_adet;
        if (!g->sektor[s].ilk || g->sektor[s].son < sira) continue;
        a = s * KAYIT_SEKTOR;
        bitis = a + ((s == g->bas) ? g->bas_ofset : KAYIT_SEKTOR);
        while (a + KAYIT_BASLIK_BAYT <= bitis) {
            if (g->f.oku(g->f.baglam, a, b, KAYIT_BASLIK_BAYT)) return n;
            if (kayit_baslik_coz(b, &h) != 1) break;
            if (h.sira > g->sektor[s].son) break;
            t = kayit_toplam_bayt(h.yuk_bayt);
            if (a + t > bitis) break;
            if (h.sira >= sira) {
                if (n + t > kap) return n;
                if (g->f.oku(g->f.baglam, a, hedef + n, t)) return n;
                if (!*ilk) *ilk = h.sira;
                *son = h.sira;
                n += t;
            }
            a += t;
        }
    }
    return n;
}

/* Butun kayitlari sil. Sira KORUNUR: numara tekrar verilmez. */
static inline int kg_bicimle(KayitGunluk *g)
{
    uint32_t s;
    for (s = 0; s < g->sektor_adet; s++) {
        if (g->f.sil(g->f.baglam, s * KAYIT_SEKTOR)) return KG_HATA;
        g->sektor[s].ilk = 0u;
        g->sektor[s].son = 0u;
    }
    g->dizin_adet = 0u;
    g->bas = g->sektor_adet - 1u;
    g->bas_ofset = KAYIT_SEKTOR;
    g->onay = g->sonraki_sira - 1u;
    g->dolu = 0u;
    return KG_TAMAM;
}

static inline uint32_t kg_kullanilan(const KayitGunluk *g)
{
    uint32_t s, t = 0u;
    for (s = 0; s < g->sektor_adet; s++) {
        if (g->sektor[s].ilk) t += (s == g->bas) ? g->bas_ofset : KAYIT_SEKTOR;
    }
    return t;
}

/* Muhafazakar: onaysiz kayit iceren sektorun TAMAMI sayilir. */
static inline uint32_t kg_onaysiz(const KayitGunluk *g)
{
    uint32_t s, t = 0u;
    for (s = 0; s < g->sektor_adet; s++) {
        if (g->sektor[s].ilk && g->sektor[s].son > g->onay)
            t += (s == g->bas) ? g->bas_ofset : KAYIT_SEKTOR;
    }
    return t;
}

static inline uint16_t kg_binde(const KayitGunluk *g, uint32_t bayt)
{
    return (uint16_t)((uint64_t)bayt * 1000u
                      / ((uint64_t)g->sektor_adet * KAYIT_SEKTOR));
}

/* Dizindeki `basla_adres`ten oturumun BASLA/TEKRAR bilgisini oku. */
static inline int kg_basla_oku(KayitGunluk *g, uint32_t adres, KayitBasla *b)
{
    uint8_t p[KAYIT_BASLA_BAYT];
    KayitBaslik h;
    uint32_t s;
    if (adres == KG_ADRES_YOK) return KG_HATA;
    s = adres / KAYIT_SEKTOR;
    if (s >= g->sektor_adet) return KG_HATA;
    if (kg__kayit_dogrula(g, adres, (s + 1u) * KAYIT_SEKTOR, &h) != 1) return KG_HATA;
    if ((h.tur != KAYIT_T_BASLA && h.tur != KAYIT_T_TEKRAR)
        || h.yuk_bayt != KAYIT_BASLA_BAYT) return KG_HATA;
    if (g->f.oku(g->f.baglam, adres + KAYIT_BASLIK_BAYT, p, KAYIT_BASLA_BAYT))
        return KG_HATA;
    kayit_basla_coz(p, b);
    return KG_TAMAM;
}

#endif /* KAYIT_GUNLUK_H */
```

- [ ] **Step 4: Harness'e NOR sürücüsünü ve GUNLUK senaryosunu ekle**

`#include "kayit_nokta.h"` satırının altına ekle:

```c
#include "kayit_gunluk.h"
```

`/* ── senaryolar ── */` satırının hemen üstüne ekle:

```c
/* ─────────────────────────────── emule NOR (uretim/avr/nor_flas.py) */
#if defined(SENARYO_GUNLUK) || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI)
#define NOR_KOMUT (*(volatile uint8_t *)0xE0)
#define NOR_A0    (*(volatile uint8_t *)0xE1)
#define NOR_A1    (*(volatile uint8_t *)0xE2)
#define NOR_A2    (*(volatile uint8_t *)0xE3)
#define NOR_VERI  (*(volatile uint8_t *)0xE4)
#ifndef NOR_SEKTOR_ADET
#define NOR_SEKTOR_ADET 8u      /* test_kayit.py derle() -D ile gecirir */
#endif
#define DIZIN_KAP 6u

static void nor_adres(uint32_t a)
{
    NOR_A0 = (uint8_t)a;
    NOR_A1 = (uint8_t)(a >> 8);
    NOR_A2 = (uint8_t)(a >> 16);
}

static int f_oku(void *b, uint32_t a, void *h, uint32_t n)
{
    uint8_t *p = (uint8_t *)h;
    (void)b;
    nor_adres(a);
    while (n--) *p++ = NOR_VERI;
    return 0;
}

static int f_yaz(void *b, uint32_t a, const void *k, uint32_t n)
{
    const uint8_t *p = (const uint8_t *)k;
    (void)b;
    nor_adres(a);
    while (n--) NOR_VERI = *p++;
    return 0;
}

static int f_sil(void *b, uint32_t a)
{
    (void)b;
    nor_adres(a);
    NOR_KOMUT = 0x5E;
    while (NOR_KOMUT & 1u) {}
    return 0;
}

static const KayitFlas FLAS = { f_oku, f_yaz, f_sil, 0 };
static KayitSektor sektor[NOR_SEKTOR_ADET];
static KayitOzet dizin[DIZIN_KAP];
static KayitGunluk g;
#endif
```

`/* ── giris ── */` satırının hemen üstüne ekle:

```c
#if defined(SENARYO_GUNLUK)
static uint8_t tampon[600];
/* cop: imza + gecerli gorunen alanlar, CRC tutmaz (sektor 3'un basina) */
static const uint8_t COP[16] = {0xA5, 0x02, 0x0A, 0x00, 0x11, 0x11, 0x11, 0x11,
                                0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x11};
/* yarim: sira 36'nin basligi yazilmis, yuku yazilmadan elektrik kesilmis */
static const uint8_t YARIM[16] = {0xA5, 0x05, 0x0C, 0x00, 0x24, 0x00, 0x00, 0x00,
                                  0x00, 0x00, 0x00, 0x00, 0x78, 0x56, 0x34, 0x12};

static void durum(const char *ad)
{
    metin(ad);
    metin(" sonraki="); ondalik(g.sonraki_sira);
    metin(" bas="); ondalik(g.bas);
    metin(" ofset="); ondalik(g.bas_ofset);
    metin(" onay="); ondalik(g.onay);
    metin(" bozuk="); ondalik(g.bozuk);
    metin(" dolu="); ondalik(g.dolu);
    metin(" silinen="); ondalik(g.silinen_sektor);
    metin(" kull="); ondalik(kg_kullanilan(&g));
    metin(" onaysiz="); ondalik(kg_onaysiz(&g));
    metin(" dizin="); ondalik(g.dizin_adet);
    satir();
}

static void oku(uint32_t sira, uint32_t kap)
{
    uint32_t ilk, son, n = kg_oku(&g, sira, tampon, kap, &ilk, &son);
    metin("OKU "); ondalik(n); yaz(' '); ondalik(ilk); yaz(' '); ondalik(son); satir();
    metin("VERI "); hexdizi(tampon, (uint16_t)n); satir();
}

static void senaryo(void)
{
    uint8_t yuk[100];
    int32_t s;
    uint16_t i;
    for (i = 0; i < sizeof(yuk); i++) yuk[i] = (uint8_t)i;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u); durum("G1");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u));
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 13u));
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u));
    durum("G2");
    oku(2u, sizeof(tampon));
    kg_ac(&g, 0u); durum("G3");
    i = 0;
    do { s = kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u); i++; } while (s > 0 && i < 1000u);
    metin("DOLU "); ondalik(i); yaz(' '); ondalik((uint32_t)(-s)); satir();
    durum("G4");
    kg_onayla(&g, 0xFFFFFFF0UL); durum("G5");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u)); durum("G6");
    oku(1u, 200u);
    oku(6u, 100u);
    kg_bicimle(&g); durum("G7");
    kg_ac(&g, g.sonraki_sira); durum("G8");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u));
    f_yaz(0, 3u * KAYIT_SEKTOR, COP, sizeof(COP));
    kg_ac(&g, 0u); durum("G9");
    f_yaz(0, 28u, YARIM, sizeof(YARIM));
    kg_ac(&g, 0u); durum("G10");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u)); durum("G11");
    oku(35u, sizeof(tampon));
    metin("BITTI\n");
}
#endif
```

- [ ] **Step 5: Testin yeşil olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `B71: 47/47 kosul gecti`. Önceki 28'e G'nin 19 iddiası ekleniyor.
Bir `G` satırı kırmızıysa çıktıdaki sözlüğü `_g(...)` beklentisiyle alan alan karşılaştır. Beklentiler bu bölümün başındaki elle hesaptan geliyor; hesabı değil kodu düzelt.

- [ ] **Step 6: Commit**

```bash
git add kod/olcum-karti-a3/kayit_gunluk.h uretim/avr/ornek_kayit.c uretim/test_kayit.py
git commit -q -F - <<'EOF'
B71 gunluk: NOR flasta halka, kurtarma, akilli temizlik

Kayit sektor asmaz; sektor kullanilmadan once hep silinir; onaysiz veri
asla silinmez (KG_DOLU); sira bicimlemeden sonra da tekrar verilmez;
esitleme okumasi yarim kaydi atlar, boslugu bildirir. 47/47.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Oturum yazıcı — `kayit_oturum.h`

**Files:**
- Create: `kod/olcum-karti-a3/kayit_oturum.h`
- Modify: `uretim/avr/ornek_kayit.c` (include + YAZICI senaryosu)
- Modify: `uretim/test_kayit.py` (`bolum_yazici`, `devam_tutarli`, `tekrar_kurali`, `_noktalar_mi`, `_oz`, `CPP_BASLIKLAR`)

**Interfaces:**
- Consumes: `KayitGunluk`, `kg_*` (Task 4); `KayitBasla`, `KayitNokta`, `KayitDevam`, `KayitSaat` (Task 2)
- Produces:
  - tip: `KayitYazici`
  - `ky_kur(y, g)`
  - `ky_baslat(y, const KayitBasla*) -> int32_t`: oturum kimliği ya da `KG_*`
  - `ky_nokta(y, const KayitNokta*, simdi_ms) -> int`
  - `ky_zaman(y, simdi_ms) -> int`, `ky_bosalt(y) -> int`
  - `ky_bitir(y, sebep) -> int`
  - `ky_devam(y, oturum, const KayitBasla*, nokta_sira, const KayitDevam*) -> int`
  - `ky_saat(y, const KayitSaat*) -> int`
  - sabitler: `KAYIT_AZAMI_YUK` (varsayılan 1012), `KAYIT_TAMPON_NOKTA`, `KAYIT_BOSALT_MS` (5000), `KY_BITIR_PAY` (24)
- Produces (test): `devam_tutarli(kayitlar) -> bool`, `tekrar_kurali(bellek) -> bool`, `_noktalar_mi(o, siralar, k_fn) -> bool`

- [ ] **Step 1: Testi yaz**

`CPP_BASLIKLAR`'ı güncelle:

```python
CPP_BASLIKLAR = ["kayit_bicim.h", "kayit_nokta.h", "kayit_gunluk.h", "kayit_oturum.h"]
```

`bolum_gunluk`'un altına ekle:

```python
# ── B71.Y · oturum yazici ─────────────────────────────────────────────
def _noktalar_mi(o, siralar, k_fn) -> bool:
    """Oturumun noktalari tam `siralar` ve her biri nokta_uret(k_fn(j))."""
    return (o is not None and [j for j, _ in o.noktalar] == list(siralar)
            and all(p == nokta_uret(k_fn(j)) for j, p in o.noktalar))


def devam_tutarli(kayitlar) -> bool:
    """Her oturumda NOKTA'nin ilk_nokta'si ve DEVAM'in nokta_sira'si
    beklenen siraya esit: nokta ne kayboldu ne ikilendi."""
    beklenen: dict[int, int] = {}
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


def tekrar_kurali(bellek: bytes) -> bool:
    """Her sektorde, bir oturumun o sektordeki ILK kaydi BASLA ya da TEKRAR:
    her sektor kendi oturumunu anlatir (temizlikten sonra da cozulebilir)."""
    for s in range(0, len(bellek), SEKTOR):
        kayitlar, _ = KB.flas_coz(bellek[s:s + SEKTOR], SEKTOR)
        gorulen: set[int] = set()
        for k in kayitlar:
            if k.oturum and k.oturum not in gorulen:
                if k.tur not in (KB.T_BASLA, KB.T_TEKRAR):
                    return False
                gorulen.add(k.oturum)
    return True


def _oz(satirlar: list[str], onek: str) -> list[tuple[int, ...]]:
    """OZ/OZS: id tur hiz ilk son nokta durum basi_silindi."""
    return [tuple(int(x) for x in p) for p in alanlar(satirlar, onek)]


YAZICI_SEKTOR = 16   # O1..O3 ~10 sektor tutar; 8 sektorde O3 DEVAM'dan
                     # sonra yanlis sebeple (DOLU) kapanirdi. O4 kalanini doldurur.


def bolum_yazici() -> None:
    print("\n── B71.Y  oturum yazici: BASLA/TEKRAR/NOKTA/DEVAM/BITIR/SAAT")
    flas = NorFlas(SEKTOR * YAZICI_SEKTOR, sektor=SEKTOR)
    sat = kos(derle("YAZICI", YAZICI_SEKTOR), flas)
    d = {p[0]: p[1:] for p in (s.split() for s in sat)
         if p and p[0] not in ("OZ", "OZS")}
    bellek = bytes(flas.bellek)
    kayitlar, bozuk = KB.flas_coz(bellek, SEKTOR)
    ot = KB.oturumlari_kur(kayitlar)
    id1, id2, id3, id4 = (int(d[x][0]) for x in ("O1", "O2", "O3", "O4"))
    o1, o2, o3, o4 = (ot.get(i) for i in (id1, id2, id3, id4))
    ok("B71.Y1 oturum kimligi = BASLA kaydinin sirasi (bos flasta ilk oturum 1)",
       id1 == 1, str(d["O1"]))
    ok("B71.Y2 flasta cozulemeyen kayit yok", bozuk == 0, f"bozuk={bozuk}")
    ok("B71.Y3 O1: 40 nokta, sira 0..39, degerler birebir, hata yok",
       d["R1"] == ["0"] and _noktalar_mi(o1, range(40), lambda j: j))
    ok("B71.Y4 O1: BITIR 40 nokta, sebep kullanici",
       o1 is not None and o1.bitir == {"nokta_adedi": 40, "sebep": 1})
    ok("B71.Y5 O2: 10 nokta + ortadaki SAAT kaydi (unix 1790000000)",
       _noktalar_mi(o2, range(10), lambda j: 100 + j)
       and [s["unix_s"] for s in o2.saatler] == [1790000000])
    ok("B71.Y6 O3: yeniden baslama sonrasi DEVAM (10), 15 nokta bosluksuz",
       _noktalar_mi(o3, range(15), lambda j: 200 + j)
       and [x["nokta_sira"] for x in o3.devamlar] == [10]
       and o3.bitir == {"nokta_adedi": 15, "sebep": 1})
    ok("B71.Y7 her DEVAM ardindaki noktanin sirasini dogru biliyor",
       devam_tutarli(kayitlar))
    ok("B71.Y8 her sektorde bir oturumun ILK kaydi BASLA ya da TEKRAR",
       tekrar_kurali(bellek))
    ok("B71.Y9 kg_basla_oku + ky_devam basarili", d["DV"] == ["0"], str(d["DV"]))
    oz = [(t[0], t[1], t[2], t[5], t[6], t[7]) for t in _oz(sat, "OZ")]
    ok("B71.Y10 yeniden acilista dizin: O1/O2 bitti, O3 ACIK ve 10. noktada",
       oz == [(id1, 1, 200, 40, 2, 0), (id2, 1, 1000, 10, 2, 0),
              (id3, 1, 500, 10, 1, 0)], str(oz))
    ozs = _oz(sat, "OZS")
    sira = {i: [k.sira for k in kayitlar if k.oturum == i] for i in (id1, id2, id3)}
    ok("B71.Y11 son dizin: O3 bitti (15 nokta); ilk/son sira flasla ayni",
       [(t[0], t[1], t[2], t[5], t[6], t[7]) for t in ozs]
       == [(id1, 1, 200, 40, 2, 0), (id2, 1, 1000, 10, 2, 0),
           (id3, 1, 500, 15, 2, 0)]
       and all((t[3], t[4]) == (min(sira[t[0]]), max(sira[t[0]])) for t in ozs),
       str(ozs))
    besl, dus = int(d["BESLENEN"][0]), int(d["DUSEN"][0])
    ucta = len(o4.noktalar) if o4 else -1
    ok("B71.Y12 bellek dolunca: KG_DOLU, oturum kapandi, BITIR(DOLU) flasta, "
       "noktalar hesapta",
       d["DOLU"] == ["-1"] and d["AKTIF"] == ["0"] and o4 is not None
       and o4.bitir == {"nokta_adedi": ucta, "sebep": 2}
       and 0 <= besl - ucta - dus <= 1,
       f"beslenen={besl} flasta={ucta} dusen={dus} bitir={o4.bitir if o4 else None}")
    ok("B71.Y13 O4'un flasa giden noktalari birebir",
       o4 is not None and _noktalar_mi(o4, range(ucta), lambda j: 1000 + j))
```

`BOLUMLER`'i güncelle:

```python
BOLUMLER = [bolum_nor, bolum_bicim, bolum_noktaci, bolum_gunluk, bolum_yazici]
```

- [ ] **Step 2: Testin kırmızı olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `avr-gcc derleyemedi (SENARYO_YAZICI)`

- [ ] **Step 3: `kod/olcum-karti-a3/kayit_oturum.h` yaz**

```c
#ifndef KAYIT_OTURUM_H
#define KAYIT_OTURUM_H
/*
 * B71 — OTURUM YAZICI: noktalari tamponlar, oturum kayitlarini gunluge
 * yazar (kartta cekirdek 0'daki kayit gorevi; 1A-2).
 *
 * Kurallar (tasarim §5):
 *   * Oturum kimligi = BASLA kaydinin sirasi.
 *   * Noktalar RAM'de en fazla KAYIT_TAMPON_NOKTA ya da KAYIT_BOSALT_MS
 *     bekler: elektrik kesilirse kayip bununla sinirli (hedef <= ~5 s).
 *   * Aktif oturumun her YENI sektoru TEKRAR kaydiyla baslar: temizlik
 *     BASLA'yi silse de her sektor kendi oturumunu anlatir; yeniden
 *     baslamada kalibrasyon kopyasi hep bulunur.
 *   * Her sektorde BITIR icin KY_BITIR_PAY bayt AYRILIR: bellek onaysiz
 *     veriyle dolunca BITIR(DOLU) yine yazilir, kayit sessizce durmaz.
 */
#include "kayit_gunluk.h"

#ifndef KAYIT_AZAMI_YUK
#define KAYIT_AZAMI_YUK 1012u      /* 4 + 28 nokta */
#endif
#define KAYIT_TAMPON_NOKTA ((KAYIT_AZAMI_YUK - 4u) / KAYIT_NOKTA_BAYT)
#ifndef KAYIT_BOSALT_MS
#define KAYIT_BOSALT_MS 5000UL
#endif
#define KY_BITIR_PAY (KAYIT_BASLIK_BAYT + KAYIT_BITIR_BAYT)

/* Sektor en az TEKRAR (116) + tam NOKTA kaydi + BITIR payi almali; yoksa
   ky_bosalt hic ilerleyemezdi. Derleme aninda denetim. */
typedef char kayit__sektor_yeter[
    (KAYIT_SEKTOR >= (uint32_t)(KAYIT_BASLIK_BAYT + KAYIT_BASLA_BAYT + 2u
                                + KAYIT_BASLIK_BAYT + KAYIT_AZAMI_YUK
                                + KY_BITIR_PAY)) ? 1 : -1];

typedef struct {
    KayitGunluk *g;
    uint32_t     oturum;          /* 0 = kayit yok */
    KayitBasla   basla;           /* TEKRAR icin */
    uint32_t     nokta_sira;      /* oturumdaki sonraki noktanin sirasi */
    uint8_t      yuk[KAYIT_AZAMI_YUK];   /* [0..3] ilk_nokta, sonra noktalar */
    uint16_t     yuk_nokta;
    uint32_t     yuk_ilk_ms;
    uint32_t     dusen;           /* dolulukta atilan nokta */
    int          son_hata;
} KayitYazici;

static inline void ky_kur(KayitYazici *y, KayitGunluk *g)
{
    memset(y, 0, sizeof(*y));
    y->g = g;
}

static inline int ky__yeni_sektor(KayitYazici *y)
{
    uint8_t p[KAYIT_BASLA_BAYT];
    int32_t s;
    int r = kg_ilerle(y->g);
    if (r) return r;
    if (!y->oturum) return KG_TAMAM;
    kayit_basla_paketle(&y->basla, p);
    s = kg_ekle(y->g, KAYIT_T_TEKRAR, y->oturum, p, KAYIT_BASLA_BAYT);
    return s < 0 ? (int)s : KG_TAMAM;
}

/* `toplam` baytlik kayit + BITIR payi bu sektore sigmiyorsa yeni sektor. */
static inline int ky__yer(KayitYazici *y, uint32_t toplam)
{
    if (y->g->bas_ofset + toplam + KY_BITIR_PAY <= KAYIT_SEKTOR) return KG_TAMAM;
    return ky__yeni_sektor(y);
}

static inline int ky__kayit(KayitYazici *y, uint8_t tur, const uint8_t *yuk,
                            uint16_t n)
{
    int32_t s;
    int r = ky__yer(y, kayit_toplam_bayt(n));
    if (r) return r;
    s = kg_ekle(y->g, tur, y->oturum, yuk, n);
    return s < 0 ? (int)s : KG_TAMAM;
}

/* Yer kalmadi: BITIR(DOLU)'yu AYRILMIS paya yaz, oturumu kapat. */
static inline int ky__dolu(KayitYazici *y, int r)
{
    if (r == KG_DOLU && y->oturum) {
        uint8_t p[KAYIT_BITIR_BAYT];
        KayitBitir b;
        b.nokta_adedi = y->nokta_sira;
        b.sebep = KB_SEBEP_DOLU;
        kayit_bitir_paketle(&b, p);
        (void)kg_ekle(y->g, KAYIT_T_BITIR, y->oturum, p, KAYIT_BITIR_BAYT);
        y->dusen += y->yuk_nokta;
        y->yuk_nokta = 0u;
        y->oturum = 0u;
    }
    y->son_hata = r;
    return r;
}

static inline int ky_bosalt(KayitYazici *y)
{
    KayitGunluk *g = y->g;
    while (y->oturum && y->yuk_nokta) {
        uint32_t kalan = KAYIT_SEKTOR - g->bas_ofset;
        uint32_t sabit = KAYIT_BASLIK_BAYT + 4u + KY_BITIR_PAY;
        uint32_t n = 0u;
        int32_t s;
        if (kalan >= sabit + KAYIT_NOKTA_BAYT) n = (kalan - sabit) / KAYIT_NOKTA_BAYT;
        if (n > y->yuk_nokta) n = y->yuk_nokta;
        if (!n) {
            int r = ky__yeni_sektor(y);
            if (r) return ky__dolu(y, r);
            continue;
        }
        kayit_y32(y->yuk, y->nokta_sira);
        s = kg_ekle(g, KAYIT_T_NOKTA, y->oturum, y->yuk,
                    (uint16_t)(4u + n * KAYIT_NOKTA_BAYT));
        if (s < 0) return ky__dolu(y, (int)s);
        y->nokta_sira += n;
        y->yuk_nokta = (uint16_t)(y->yuk_nokta - n);
        if (y->yuk_nokta)
            memmove(y->yuk + 4, y->yuk + 4 + n * KAYIT_NOKTA_BAYT,
                    (size_t)y->yuk_nokta * KAYIT_NOKTA_BAYT);
    }
    return KG_TAMAM;
}

static inline int ky_nokta(KayitYazici *y, const KayitNokta *p, uint32_t simdi_ms)
{
    if (!y->oturum) return KG_YOK;
    if (y->yuk_nokta >= KAYIT_TAMPON_NOKTA) {
        int r = ky_bosalt(y);
        if (r) return r;
    }
    kayit_nokta_paketle(p, y->yuk + 4 + (uint32_t)y->yuk_nokta * KAYIT_NOKTA_BAYT);
    if (!y->yuk_nokta) y->yuk_ilk_ms = simdi_ms;
    y->yuk_nokta++;
    if (y->yuk_nokta >= KAYIT_TAMPON_NOKTA) return ky_bosalt(y);
    return KG_TAMAM;
}

static inline int ky_zaman(KayitYazici *y, uint32_t simdi_ms)
{
    if (y->oturum && y->yuk_nokta
        && (uint32_t)(simdi_ms - y->yuk_ilk_ms) >= KAYIT_BOSALT_MS)
        return ky_bosalt(y);
    return KG_TAMAM;
}

static inline int ky_bitir(KayitYazici *y, uint8_t sebep)
{
    uint8_t p[KAYIT_BITIR_BAYT];
    KayitBitir b;
    int32_t s;
    int r;
    if (!y->oturum) return KG_YOK;
    r = ky_bosalt(y);
    if (r) return r;           /* DOLU ise ky__dolu BITIR'i zaten yazdi */
    b.nokta_adedi = y->nokta_sira;
    b.sebep = sebep;
    kayit_bitir_paketle(&b, p);
    s = kg_ekle(y->g, KAYIT_T_BITIR, y->oturum, p, KAYIT_BITIR_BAYT);
    y->oturum = 0u;
    return s < 0 ? (int)s : KG_TAMAM;
}

/* Donus: oturum kimligi (> 0) ya da KG_*. */
static inline int32_t ky_baslat(KayitYazici *y, const KayitBasla *b)
{
    uint8_t p[KAYIT_BASLA_BAYT];
    int32_t s;
    int r;
    if (y->oturum) {
        r = ky_bitir(y, KB_SEBEP_KULLANICI);
        if (r && r != KG_DOLU) return r;
    }
    y->basla = *b;
    y->nokta_sira = 0u;
    y->yuk_nokta = 0u;
    y->son_hata = 0;
    kayit_basla_paketle(b, p);
    r = ky__yer(y, kayit_toplam_bayt(KAYIT_BASLA_BAYT));   /* oturum 0: TEKRAR yok */
    if (r) { y->son_hata = r; return r; }
    y->oturum = y->g->sonraki_sira;
    s = kg_ekle(y->g, KAYIT_T_BASLA, y->oturum, p, KAYIT_BASLA_BAYT);
    if (s < 0) { y->oturum = 0u; y->son_hata = (int)s; }
    return s;
}

/* Kart yeniden basladi: acik oturumu surdur (pil testi ICIN CAGRILMAZ —
   emniyet: yuk kapali kalir; 1C). */
static inline int ky_devam(KayitYazici *y, uint32_t oturum, const KayitBasla *b,
                           uint32_t nokta_sira, const KayitDevam *d)
{
    uint8_t p[KAYIT_DEVAM_BAYT];
    KayitDevam dd = *d;
    int r;
    y->oturum = oturum;
    y->basla = *b;
    y->nokta_sira = nokta_sira;
    y->yuk_nokta = 0u;
    y->son_hata = 0;
    dd.nokta_sira = nokta_sira;
    kayit_devam_paketle(&dd, p);
    r = ky__kayit(y, KAYIT_T_DEVAM, p, KAYIT_DEVAM_BAYT);
    return r ? ky__dolu(y, r) : KG_TAMAM;
}

static inline int ky_saat(KayitYazici *y, const KayitSaat *z)
{
    uint8_t p[KAYIT_SAAT_BAYT];
    int r;
    kayit_saat_paketle(z, p);
    r = ky__kayit(y, KAYIT_T_SAAT, p, KAYIT_SAAT_BAYT);
    return r ? ky__dolu(y, r) : KG_TAMAM;
}

#endif /* KAYIT_OTURUM_H */
```

- [ ] **Step 4: Harness'e YAZICI senaryosunu ekle**

`#include "kayit_gunluk.h"` satırının altına ekle:

```c
#include "kayit_oturum.h"
```

`/* ── giris ── */` satırının hemen üstüne ekle:

```c
#if defined(SENARYO_YAZICI)
static KayitYazici y;

static void oz(const char *ad)
{
    uint16_t i;
    for (i = 0; i < g.dizin_adet; i++) {
        const KayitOzet *o = &g.dizin[i];
        metin(ad);
        yaz(' '); ondalik(o->id); yaz(' '); ondalik(o->tur);
        yaz(' '); ondalik(o->hiz_ms); yaz(' '); ondalik(o->ilk_sira);
        yaz(' '); ondalik(o->son_sira); yaz(' '); ondalik(o->nokta_sonraki);
        yaz(' '); ondalik(o->durum); yaz(' '); ondalik(o->basi_silindi);
        satir();
    }
}

static void senaryo(void)
{
    KayitBasla b, bb;
    KayitNokta p;
    KayitSaat z;
    KayitDevam d;
    uint32_t k, t = 0u, id, ns;
    uint16_t i;
    int r = 0;

    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u);
    ky_kur(&y, &g);

    /* O1: 40 nokta, 200 ms; tampon dolunca ve 5 s'de bir bosaltilir */
    basla_uret(&b, 200u);
    sayi("O1", ky_baslat(&y, &b));
    for (k = 0; k < 40u && !r; k++) {
        nokta_uret(k, &p);
        t += 200u;
        r = ky_nokta(&y, &p, t);
        if (!r) r = ky_zaman(&y, t);
    }
    sayi("R1", r);
    sayi("B1", ky_bitir(&y, KB_SEBEP_KULLANICI));

    /* O2: ortada saat kaydi */
    basla_uret(&b, 1000u);
    sayi("O2", ky_baslat(&y, &b));
    for (k = 100; k < 110u; k++) {
        nokta_uret(k, &p);
        t += 1000u;
        ky_nokta(&y, &p, t);
        if (k == 104u) {
            z.unix_s = 1790000000UL;
            z.kart_ms = t;
            z.acilis = 3u;
            ky_saat(&y, &z);
        }
    }
    sayi("B2", ky_bitir(&y, KB_SEBEP_KULLANICI));

    /* O3: acik birakilir, "yeniden baslama" sonrasi surdurulur */
    basla_uret(&b, 500u);
    sayi("O3", ky_baslat(&y, &b));
    for (k = 200; k < 210u; k++) { nokta_uret(k, &p); t += 500u; ky_nokta(&y, &p, t); }
    sayi("BO", ky_bosalt(&y));
    kg_ac(&g, 0u);                      /* RAM'deki her sey unutuldu */
    ky_kur(&y, &g);
    oz("OZ");
    r = -9;
    for (i = 0; i < g.dizin_adet; i++) {
        if (g.dizin[i].durum != KD_ACIK) continue;
        id = g.dizin[i].id;
        ns = g.dizin[i].nokta_sonraki;
        if (kg_basla_oku(&g, g.dizin[i].basla_adres, &bb)) break;
        d.acilis = 4u; d.unix_s = 0u; d.kart_ms = 50u; d.nokta_sira = 0u;
        r = ky_devam(&y, id, &bb, ns, &d);
        break;
    }
    sayi("DV", r);
    for (k = 210; k < 215u; k++) { nokta_uret(k, &p); t += 500u; ky_nokta(&y, &p, t); }
    sayi("B3", ky_bitir(&y, KB_SEBEP_KULLANICI));
    kg_ac(&g, 0u);
    oz("OZS");

    /* O4: onay YOK -> bellek dolar; BITIR(DOLU) yazilmali */
    ky_kur(&y, &g);
    basla_uret(&b, 100u);
    sayi("O4", ky_baslat(&y, &b));
    k = 1000u;
    r = 0;
    while (!r && k < 20000u) { nokta_uret(k, &p); k++; t += 100u; r = ky_nokta(&y, &p, t); }
    sayi("DOLU", r);
    sayi("BESLENEN", (int32_t)(k - 1000u));
    sayi("AKTIF", (int32_t)y.oturum);
    sayi("DUSEN", (int32_t)y.dusen);
    metin("BITTI\n");
}
#endif
```

- [ ] **Step 5: Testin yeşil olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `B71: 62/62 kosul gecti`. Önceki 47'ye Y'nin 15 iddiası ekleniyor.

- [ ] **Step 6: Commit**

```bash
git add kod/olcum-karti-a3/kayit_oturum.h uretim/avr/ornek_kayit.c uretim/test_kayit.py
git commit -q -F - <<'EOF'
B71 oturum yazici: tampon, TEKRAR, DEVAM, BITIR(DOLU)

Her sektor TEKRAR ile kendini anlatir; yeniden baslamada oturum DEVAM
ile surer; bellek dolunca ayrilmis payla BITIR(DOLU) yazilir. 62/62.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Elektrik kesme denemesi

**Files:**
- Modify: `uretim/avr/ornek_kayit.c` (KESINTI senaryosu)
- Modify: `uretim/test_kayit.py` (`bolum_kesinti`)

**Interfaces:**
- Consumes: her şey (Task 1–5); `devam_tutarli`, `tekrar_kurali` (Task 5)
- Produces: `bolum_kesinti(n_deneme)`. Varsayılan 120 deneme; `--kesinti N` ile uzatılır.

- [ ] **Step 1: Testi yaz**

`bolum_yazici`'nin altına ekle:

```python
# ── B71.K · elektrik kesme ────────────────────────────────────────────
def bolum_kesinti(n_deneme: int) -> None:
    """Ayni is yuku rastgele cevrimlerde kesilir, kart yeniden acilir.
    Kesme yazmanin, silmenin ya da kurtarmanin tam ortasina denk gelebilir.
    Tohum sabit: sonuc tekrarlanabilir."""
    print(f"\n── B71.K  elektrik kesme: {n_deneme} rastgele kesinti")
    elf = derle("KESINTI")
    rng = random.Random(71)
    flas = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR, sil_cevrim=20_000)
    ac_sira: list[int] = []
    yeni = devam = hata = bozuk_top = 0
    for _ in range(n_deneme):
        kart = kart_kur(elf, flas)
        kart.cevrim_kadar_kos(rng.randrange(100_000, 1_500_000))
        flas.kes(rng)
        for s in kart.satirlar():
            p = s.split()
            if p[:1] == ["AC"] and len(p) == 3 and p[1].isdigit() and p[2].isdigit():
                ac_sira.append(int(p[1]))
                bozuk_top += int(p[2])
            elif p[:1] == ["YENI"]:
                yeni += 1
            elif p[:1] == ["DEVAM"]:
                devam += 1
            elif p[:1] == ["HATA"]:
                hata += 1
    bellek = bytes(flas.bellek)
    kayitlar, _ = KB.flas_coz(bellek, SEKTOR)
    ot = [o for o in KB.oturumlari_kur(kayitlar).values() if o.noktalar]
    o = ot[0] if len(ot) == 1 else None
    idx = [j for j, _ in o.noktalar] if o else []
    ok("B71.K1 hicbir acilista kurtarma/surdurme hatasi yok", hata == 0,
       f"HATA={hata}")
    ok("B71.K2 en az bir SILME ortasinda kesildi (yarim sektor modeli sinandi)",
       flas.kesilen_silme >= 1, f"{flas.kesilen_silme} kesik silme")
    ok("B71.K3 en az bir YARIM kayit kurtarmada atildi", bozuk_top >= 1,
       f"toplam {bozuk_top}")
    ok("B71.K4 kesintiler oturumu bolmedi: flasta tek oturum, DEVAM ile surdu",
       o is not None and devam >= 10,
       f"oturum={len(ot)} DEVAM={devam} YENI={yeni}")
    ok("B71.K5 nokta siralari bosluksuz ve tekrarsiz",
       bool(idx) and idx == list(range(idx[0], idx[0] + len(idx))),
       f"{len(idx)} nokta {idx[:1]}..{idx[-1:]}")
    ok("B71.K6 her nokta deterministik degerine BIREBIR esit (bozuk veri yok)",
       o is not None and all(p == nokta_uret(j) for j, p in o.noktalar))
    ok("B71.K7 her DEVAM ardindaki noktanin sirasini dogru biliyor",
       devam_tutarli(kayitlar))
    ok("B71.K8 her sektorde oturumun ilk kaydi BASLA ya da TEKRAR",
       tekrar_kurali(bellek))
    ok("B71.K9 sira numarasi acilislar boyunca hic geri gitmedi",
       len(ac_sira) >= 10 and all(a <= b for a, b in zip(ac_sira, ac_sira[1:])),
       f"{len(ac_sira)} acilis")
```

`BOLUMLER`'i güncelle:

```python
BOLUMLER = [bolum_nor, bolum_bicim, bolum_noktaci, bolum_gunluk, bolum_yazici,
            bolum_kesinti]
```

- [ ] **Step 2: Testin kırmızı olduğunu gör**

Run: `cd uretim && python test_kayit.py`
Expected: `avr-gcc derleyemedi (SENARYO_KESINTI)`

- [ ] **Step 3: Harness'e KESINTI senaryosunu ekle**

`/* ── giris ── */` satırının hemen üstüne ekle:

```c
#if defined(SENARYO_KESINTI)
static KayitYazici y;

/* Sonsuz is yuku: test_kayit.py rastgele bir cevrimde KESER, karti
   yeniden acar. Her acilis: kurtar -> acik oturum varsa DEVAM, yoksa YENI. */
static void senaryo(void)
{
    KayitNokta p;
    KayitBasla b;
    uint32_t k = 0u, t = 0u, id = 0u;
    uint16_t i;
    int32_t r;

    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u);
    ky_kur(&y, &g);
    kg_onayla(&g, g.sonraki_sira - 1u);    /* cihaz her seyi aldi: halka donsun */
    metin("AC "); ondalik(g.sonraki_sira); yaz(' '); ondalik(g.bozuk); satir();
    for (i = 0; i < g.dizin_adet; i++) {
        if (g.dizin[i].durum == KD_ACIK) { id = g.dizin[i].id; k = g.dizin[i].nokta_sonraki; }
    }
    if (id) {
        KayitDevam d;
        uint32_t adres = KG_ADRES_YOK;
        for (i = 0; i < g.dizin_adet; i++) if (g.dizin[i].id == id) adres = g.dizin[i].basla_adres;
        memset(&d, 0, sizeof(d));
        d.acilis = 1u;
        r = kg_basla_oku(&g, adres, &b);
        if (!r) r = ky_devam(&y, id, &b, k, &d);
        metin("DEVAM "); ondalik(id); yaz(' '); ondalik(k); satir();
    } else {
        basla_uret(&b, 100u);
        r = ky_baslat(&y, &b);
        metin("YENI "); ondalik(r > 0 ? (uint32_t)r : 0u); satir();
        r = (r > 0) ? 0 : r;
    }
    if (r) { metin("HATA "); ondalik((uint32_t)(-r)); satir(); metin("BITTI\n"); return; }
    for (;;) {
        nokta_uret(k, &p);
        k++;
        t += 100u;
        r = ky_nokta(&y, &p, t);
        if (!r && (k & 3u) == 0u) {
            r = ky_bosalt(&y);
            kg_onayla(&g, g.sonraki_sira - 1u);
        }
        if (r) { metin("HATA "); ondalik((uint32_t)(-r)); satir(); metin("BITTI\n"); return; }
    }
}
#endif
```

- [ ] **Step 4: Testin yeşil olduğunu gör ve süresini ölç**

Run: `cd uretim && time python test_kayit.py`
Expected: `B71: 72/72 kosul gecti`. Önceki 62'ye K'nin 10 iddiası ekleniyor. Toplam süre **2 dakikanın altında** olmalı.
- Süre 2 dakikayı aşarsa `main()`'deki `--kesinti` varsayılanını 120'den, toplam 2 dakikanın altına inecek en büyük 20'nin katına indir.
- K2 ya da K3'ün değeri 0 çıkarsa varsayılanı düşürmek yok. Bu, arıza modelinin sınanmadığı anlamına gelir; önce `sil_cevrim`'i 20 000'den 60 000'e çıkar.

Ayrıca uzun koşuyu **bir kez** çalıştır ve süresini not al:

Run: `cd uretim && python test_kayit.py --kesinti 1000`
Expected: bütün K iddiaları yeşil.

- [ ] **Step 5: Commit**

```bash
git add uretim/avr/ornek_kayit.c uretim/test_kayit.py
git commit -q -F - <<'EOF'
B71 elektrik kesme: rastgele cevrimde kes, yeniden ac, butunlugu olc

Yarim yazma + yarim silme. Tek oturum DEVAM ile surer; noktalar
bosluksuz ve birebir; sira geri gitmez. 72/72 (+ --kesinti 1000).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Doğrulama zinciri, mutasyonlar, sayım kilidi

**Files:**
- Modify: `uretim/dogrula3.py` (`ADIMLAR`)
- Modify: `uretim/mutasyon.py` (`MUTASYONLAR`)
- Modify: `uretim/beklenen_sayim.json` (`--sayim-kilidi-yaz` ile üretilir)

**Interfaces:**
- Consumes: `test_kayit.py` (Task 1–6)
- Produces: zincir adımı `B71 Kayit motoru (bicim + gunluk + elektrik kesme)`; `ADIM_SAYISI` 19'dan 20'ye çıkar.

- [ ] **Step 1: Mutasyonları ekle (önce kırmızıyı üretecek olanlar)**

`uretim/mutasyon.py`'de `MUTASYONLAR = [` listesinin **son elemanından sonra**, kapanan `]`'nin hemen üstüne ekle:

```python
    # ── B71 · kayit motoru (test_kayit.py) ──────────────────────────────
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_bicim.h",
     "0x1DB71064u", "0x1DB71065u",
     "CRC tablosunda tek bit: bilinen vektor ve C==Python basligi kirmizi"),
    ("B71", "test_kayit.py", "kopru/kayit_bicim.py",
     '"<IHBxfhhfhhfff"', '"<IHxBfhhfhhfff"',
     "Python cozucu bayrak ile dolgunun yerini karistirirsa nokta C==Python "
     "kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_nokta.h",
     "if (menzil != k->menzil) {", "if (0) {",
     "menzil degisince nokta bolunmezse iki menzilin kodlari karisir: P2 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_nokta.h",
     "if (!hata && k->n < 0xFFFFu) {", "if (k->n < 0xFFFFu) {",
     "hatali ornek istatistige girerse P4 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "if (g->sektor[s].son > g->onay) { g->dolu = 1u; return KG_DOLU; }",
     "if (0) { g->dolu = 1u; return KG_DOLU; }",
     "onaysiz veri silinirse G5 kirmizi — akilli temizligin tek emniyeti"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "if (g->sonraki_sira && sira >= g->sonraki_sira) sira = g->sonraki_sira - 1u;",
     "/* kirpma yok */",
     "bozuk istemcinin buyuk onayi kirpilmazsa G6 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "if (h.sira > g->sektor[s].son) break;", "if (0) break;",
     "yarim kayit esitleme yanitina girerse G15 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "if (bos) { g->bas = g->sektor_adet - 1u; g->bas_ofset = KAYIT_SEKTOR; }",
     "/* bos */",
     "bos flasta ilk yazma silinmemis sektore giderse G1 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "if (g->sonraki_sira < sira_taban) g->sonraki_sira = sira_taban;",
     "/* taban yok */",
     "bicimlemeden sonra sira 1'e donerse numara tekrar verilir: G11 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_gunluk.h",
     "return (c == h->crc) ? 1 : -1;", "return 1;",
     "CRC denetlenmezse cop ve yarim kayit veri sanilir: G12/G13/K kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_oturum.h",
     "s = kg_ekle(y->g, KAYIT_T_TEKRAR, y->oturum, p, KAYIT_BASLA_BAYT);",
     "s = 1;",
     "yeni sektor TEKRAR'siz baslarsa sektor kendini anlatamaz: Y8/K8 kirmizi"),
    ("B71", "test_kayit.py", "kod/olcum-karti-a3/kayit_oturum.h",
     "#define KY_BITIR_PAY (KAYIT_BASLIK_BAYT + KAYIT_BITIR_BAYT)",
     "#define KY_BITIR_PAY 0u",
     "BITIR payi ayrilmazsa dolulukta BITIR(DOLU) yazilamaz: Y12 kirmizi"),
    ("B71", "test_kayit.py", "uretim/avr/nor_flas.py",
     "self.bellek[a] &= v & 0xFF", "self.bellek[a] = v & 0xFF",
     "emule NOR 'yalniz 1->0' kuralini kaybederse N2 kirmizi"),
```

- [ ] **Step 2: Mutasyonları koştur, hepsi yakalanmalı**

Run: `cd uretim && python mutasyon.py --adim B71`
Expected: 13 mutasyonun **13'ü de** yakalanır; her biri kırmızı ya da iddia sayısı değişir.
Yakalanmayan (kaçan) bir mutasyon varsa, o iddianın testi boş demektir. Testi **düzelt**, mutasyonu gevşetme. Kaçağı ve düzeltmeyi DEVIR girişine yaz (Task 8).

- [ ] **Step 3: Zincir adımını ekle**

`uretim/dogrula3.py`'de `ADIMLAR` listesinde `("B25 Kart bringup kosucusu (kayitli kart)", "test_tezgah_kart.py"),` satırının altına ekle:

```python
    # B71 — KAYIT MOTORU (alt proje 1A-1). Kartin kayit bicimi, noktacisi,
    # NOR flas gunlugu ve oturum yazicisi AVR emulatorunde EMULE NOR flas
    # uzerinde, rastgele elektrik kesmeleri dahil. Python cozucu ayni
    # baytlari bagimsiz cozuyor. Donanim GEREKMIYOR.
    ("B71 Kayit motoru (bicim + gunluk + elektrik kesme)", "test_kayit.py"),
```

- [ ] **Step 4: Sayım kilidini yaz, zinciri yeşil gör**

Run: `cd uretim && python dogrula3.py --sayim-kilidi-yaz`
Expected: zincir sonunda `beklenen_sayim.json` yazılır. Dosyaya yeni `"B71 Kayit motoru ..."` anahtarı eklenir.

Run: `cd uretim && python dogrula3.py`
Expected: **20/20** adım yeşil. B71'in satırı `B71: 72/72 kosul gecti`. Diğer 19 adımın iddia sayıları değişmez (kilit bunu kendisi karşılaştırır).

- [ ] **Step 5: Commit**

```bash
git add uretim/dogrula3.py uretim/mutasyon.py uretim/beklenen_sayim.json
git commit -q -F - <<'EOF'
B71 zincire girdi (20/20), 13 mutasyon, sayim kilidi

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Belgeler, spec düzeltmesi, gönderme

**Files:**
- Modify: `DEVIR.md` (yeni bölüm)
- Modify: `tasarim/2026-09-29-yazilim-sistemi.md` (§5 kapasite tablosu, §7 W notu)
- Modify: çalışma alanı kökündeki `CLAUDE.md` (depo dışında; commit'lenmez)
- Modify: Claude hafıza dizinindeki `olcum-karti-panel-kayit-plani.md` (depo dışında)

**Interfaces:**
- Consumes: Task 1–7'nin gerçek çıktıları: iddia sayısı, süre, mutasyon sonucu, `--kesinti 1000` süresi

- [ ] **Step 1: Spec §5 kapasite tablosunu kesinleşen biçimle değiştir**

`tasarim/2026-09-29-yazilim-sistemi.md`'de `### Kapasite (tahmini — biçim alt proje 1'de kesinleşir)` başlığından `### Kartta saklama` başlığına kadar olan bölümü şununla değiştir:

```markdown
### Kapasite (1A-1'de kesinleşen biçimle)

Nokta 36 bayt · kayıt başlığı 16 bayt · her sektör başında 116 baytlık
TEKRAR · 5 saniyelik boşaltma · sektör başına 24 baytlık BITIR payı.
~11.4 MB'lık kayıt bölümü (2912 sektör; bölüm tablosu 1A-2'de) için:

| Hız | Nokta/sektör | Süre |
|---|---|---|
| 50/s | ~107 | ~1.7 saat |
| 10/s | ~107 | ~8.7 saat |
| 5/s | ~107 | ~17 saat |
| 1/s | ~100 | ~3.4 gün |
| 10 s'de 1 | ~70 | ~24 gün |
| dakikada 1 | ~70 | ~140 gün |

Yavaş hızlarda verim düşük: nokta 5 s içinde tek başına yazılıyor (Ö2'nin
bedeli). Ayrıntılı kip (her örnek) 1C'de tasarlanacak.
```

- [ ] **Step 2: Spec §7'deki W notunu değiştir**

`- **Yeniden kalibrasyonun kesinliği (dürüst sınır):**` ile başlayan maddeyi (4 satır, `Kayıt biçimi (alt proje 1) bu yaklaşıklığı en aza indirecek alanları seçer.` satırına kadar) şununla değiştir:

```markdown
- **Yeniden kalibrasyonun kesinliği (1A-1'de kesinleşti):** V ve A ham kod
  olarak saklanıyor; başka kalibrasyonla ort/min/maks **tam** yeniden
  hesaplanır (min/maks tekdüze dönüşümde korunur). **W** ise kayıt anındaki
  kalibrasyonla **watt** olarak (ort/min/maks) saklanıyor; ham çarpım toplamı
  saklanmıyor. Sebep: firmware gücü hizalanmış volt × amper ve süzgeç
  düzeltmesiyle hesaplıyor; aynı hesabı kod biriminde yeniden kurmak menzil
  geçişlerinde kesintili ikinci bir hat olurdu. Sonuç: başka kalibrasyon
  uygulanınca W (ort dahil) **yaklaşık** olur ve ekranda öyle yazar.
```

- [ ] **Step 3: DEVIR.md'ye bölüm ekle**

`DEVIR.md`'nin en sonuna, Task 1–7'nin **gerçek çıktılarını** kullanarak şu yapıda bir bölüm ekle. Aşağıdaki sayılar koşuda ölçülenlerle aynı olmalı; farklıysa ölçüleni yaz:

```markdown
#### 5.12.65 ✅ B71 — KAYIT MOTORU (alt proje 1A-1, 2026-09-29)

Tasarım: `tasarim/2026-09-29-yazilim-sistemi.md` · Plan:
`tasarim/2026-09-29-plan-1a1-kayit-motoru.md`. Karta dokunulmadı.

**Ne yapıldı:** `kayit_bicim.h` (tek bayt tanımı) · `kayit_nokta.h`
(ort + min + maks; menzil sınırında bölünme) · `kayit_gunluk.h` (NOR
flaşta halka, kurtarma, akıllı temizlik) · `kayit_oturum.h` (TEKRAR,
DEVAM, BITIR(DOLU)) · `kopru/kayit_bicim.py` (bağımsız çözücü) ·
`uretim/avr/nor_flas.py` (yarım yazma + yarım silme arıza modeli).

**Doğrulama:** `test_kayit.py` 72/72 (süre: ölçülen) · `--kesinti 1000`
yeşil (süre: ölçülen) · mutasyon B71 13/13 · zincir 20/20.

**Kilitlenen biçim kararları:** (plan belgesindeki listeyi kısaca yaz)
**W notu:** W watt olarak saklanıyor → yeniden kalibrasyonda yaklaşık
(spec §7 güncellendi).

**Sırada:** 1A-2 — bölüm tablosu, çekirdek 0 kayıt görevi, `G` komutu,
`/kayit/*` uçları, NTP, eşitleme istemcisi, tezgah ölçümleri (flaş
durmasının ölçüme etkisi = spec §11'in ilk riski).
```

- [ ] **Step 4: CLAUDE.md'yi güncelle (depo dışında)**

Çalışma alanı kökündeki `CLAUDE.md`'de:

```
python dogrula3.py     # GÜNCEL — 19/19 olmalı, ~8 dk
```

satırını şununla değiştir (dakikayı Task 7'deki gerçek süreyle yaz):

```
python dogrula3.py     # GÜNCEL — 20/20 olmalı, ~10 dk
```

Aynı dosyada `## Aktif proje: ölçüm kartı` bölümünün ilk paragrafının altına ekle:

```markdown
🗂️ **Yazılım sistemi planı (2026-09-29):** kayıt · analiz · PC · Android.
Tasarım `projeler/olcum-karti/tasarim/2026-09-29-yazilim-sistemi.md`
(onaylı); 5 alt proje. **1A-1 kayıt motoru bitti (B71, DEVIR 5.12.65)**:
`kayit_*.h` + `kopru/kayit_bicim.py`, AVR emülatöründe emüle NOR +
rastgele elektrik kesmesiyle sınanıyor (`uretim/test_kayit.py`). Sırada
1A-2 (firmware entegrasyonu, karta dokunur).
```

- [ ] **Step 5: Hafızayı güncelle**

`memory/olcum-karti-panel-kayit-plani.md`'deki `- **SPEC YAZILDI (2026-09-29):**` maddesinin altına ekle:

```markdown
- **1A-1 BİTTİ:** B71 kayıt motoru; plan `tasarim/2026-09-29-plan-1a1-kayit-motoru.md`;
  test_kayit.py 72/72, mutasyon 13/13, zincir 20/20. Sırada 1A-2 (karta dokunur —
  kullanıcı kutu kurulumunda; karta yüklemeden önce sor).
```

- [ ] **Step 6: Commit ve gönder**

```bash
git add DEVIR.md tasarim/2026-09-29-yazilim-sistemi.md
git commit -q -F - <<'EOF'
B71 belgeler: DEVIR 5.12.65, spec kapasite tablosu ve W notu

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log origin/main..main --oneline
git push origin main
```

Expected: `git log` Task 1–8'in commit'lerini gösterir; push `main -> main` ile biter. Kutu kurulumundan kalan commit'lenmemiş değişiklikler `git status`'ta aynen durur.

---

## Sonraki plan (1A-2) için hazır bilgi

Bu plan bittiğinde 1A-2'nin planı yazılacak. Plan yazılırken bilinmesi gerekenler (inceleme sırasında bulundu):

- **Bölüm tablosu:** çizim klasörüne konan `partitions.csv` çekirdeğin şemasını geçersiz kılıyor (`platform.txt` prebuild.3). `PartitionScheme=huge_app` FQBN'de kalmalı; 3 MB uygulama üst sınırını o veriyor.
  - `nvs` bölümü **0x9000 / 0x5000'de kalmalı**: WiFi parolaları ve `Ayar3` kalibrasyonu orada.
  - `arayuz-uret.py` ofseti bugün `huge_app.csv`'den okuyor; tabloyu yeni dosyadan okumalı.
- **Örnek beslemesi:** `olcum_al()` ham kodları (`ham_v`, `ham_i`) yerel tutuyor. Noktacı için dışarı verilmeli.
  - `loop()`'ta `Okuma3 o = olcum_al();` satırının ardı besleme noktası.
  - Skop duraklamasında (`skop_is != SKOP_IS_YOK` dalı) `kn_zaman` çağrılmalı.
- **Çekirdekler:**
  - Soket yazımı yalnızca çekirdek 0'da (B28); `Serial` basımı çekirdek 1'de. Bu yüzden `G` durum satırını çekirdek 1 basmalı; kayıt görevi yalnızca paylaşılan bir durum yapısı yazmalı.
  - Komutlar çekirdek 1'de çalışıyor (`komut_calistir`).
- **Komut ve satır harfleri:** `G` komut harfi boş. `L` bir çıktı satırında kullanılıyor (`?` dökümünde `L normal …`), bu yüzden `G` seçildi.
- **Köprü kuralı:** köprü kayıtlıyken kart canlı akışı reddedip köprüye yönlendiriyor (`akis_sayfa`, `kopru_canli()`). `sim3_web.py` 2d iddiası bunu şart koşuyor; kuralla birlikte o da değişecek.
- **Şifreleme:** ChaCha20/Poly1305 Arduino çekirdeği 3.3.11'in `sdkconfig`'inde kapalı. 1D kendi uygulamasını yazacak (RFC 8439 vektörleriyle).
