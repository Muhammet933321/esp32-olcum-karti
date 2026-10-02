# -*- coding: utf-8 -*-
"""2E capraz vektorleri: ortak/test/vektor/skop.json'u URETIR (osiloskop olcumleri).

    python ortak_vektor_skop.py             # JSON'u yeniden yazar
    python ortak_vektor_skop.py --denetle   # yazmadan: dosya C ile HALA ayni mi (0/1)

Tasarim: tasarim/2026-10-02-alt-proje-2-ortak.md (O3, dilim 2E).

BASVURU = KARTIN GERCEK C KODU. `kod/olcum-karti-a3/skop_olc.h` (olcum2.h'den uretilen
birebir kopya, test_skop_ayni.py denetler) avr-gcc ile derlenir ve `test_skop_olcum.py`'nin
kullandigi, 39/39 bit birebir dogrulanmis AVR emulatorunde (uretim/avr) kosturulur. Python'da
skop_olc'un bir YENIDEN-UYGULAMASI yok ve burada da yazilmiyor: beklenen degerler C'nin
float32 ciktisinin bit deseninden gelir. JS (ortak/src/skop.js) her alani BIT BIT
(Object.is) uretmeli: ortak/test/skop.test.js.

Girdi kartin RAM'ine dogrudan yazilir (UART yok): emulatorun RAM'i 0x900'den buyutulur,
derleyicinin hic dokunmadigi sabit adreslere (0x0A00 parametreler, 0x0A10 ham kodlar)
konur. Yigin RAMEND'de (0x8FF) kalir, .data/.bss 0x100'den baslar — cakisma yok.

Girdiler belirlenimci: gurultu kendi LCG'mizden (random modulu degil), dalgalar tamsayi
aritmetigi ya da math.sin + round ile.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr import mega328                    # noqa: E402
from avr.cekirdek import Cekirdek          # noqa: E402
from avr.elf import flash_goruntusu        # noqa: E402
import gecici                              # noqa: E402

HEDEF = KOK / "ortak" / "test" / "vektor" / "skop.json"
BASLIK = KOK / "kod" / "olcum-karti-a3" / "skop_olc.h"
AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"

GIRDI_ADRES = 0x0A00          # adet (u16) · volt_adim (f32) · hz (f32)
HAM_ADRES = 0x0A10            # uint16_t ham[]
AZAMI_ADET = 4000             # kartin SKOP_AZAMI_ADET'i
RAM_BOYUT = HAM_ADRES + 2 * AZAMI_ADET + 16

# Alan sirasi = C'deki SkopOlcum; adlar = kartin `M` satiri (arayuz3 skopMCoz).
ALANLAR = ("f", "T", "Vpp", "Vmax", "Vmin", "Vort", "Vrms", "Vac", "duty", "tr", "tf")

HARNESS = r"""
#include <avr/io.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "skop_olc.h"

#define G_ADET (*(const uint16_t *)0x0A00u)
#define G_VA   (*(const float *)0x0A02u)
#define G_HZ   (*(const float *)0x0A06u)
#define G_HAM  ((const uint16_t *)0x0A10u)

static void yaz(char c) { while (!(UCSR0A & (1 << UDRE0))) {} UDR0 = c; }
static void metin(const char *s) { while (*s) yaz(*s++); }
static void hexf(float f)
{
    const char *h = "0123456789abcdef";
    uint8_t b[4];
    int8_t i;
    memcpy(b, &f, 4);
    for (i = 3; i >= 0; i--) { yaz(h[b[i] >> 4]); yaz(h[b[i] & 15]); }
    yaz(' ');
}

int main(void)
{
    SkopOlcum o;
    char t[8];
    UBRR0H = 0; UBRR0L = 0;
    UCSR0A = (1 << U2X0); UCSR0B = (1 << TXEN0); UCSR0C = (3 << UCSZ00);
    skop_olc(G_HAM, G_ADET, G_VA, G_HZ, &o);
    metin("R ");
    hexf(o.frekans); hexf(o.periyot); hexf(o.vpp); hexf(o.vmax); hexf(o.vmin);
    hexf(o.vort); hexf(o.vrms); hexf(o.vac); hexf(o.duty); hexf(o.t_yuksel);
    hexf(o.t_dus);
    utoa(o.cevrim, t, 10); metin(t);
    metin("\nBITTI\n");
    for (;;) {}
}
"""


def f32(x: float) -> float:
    """float32'ye yuvarla (C'deki `(float)x`)."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


# Kartin skop adimi: SKOP_ADC_TAVAN / SKOP_ADC_SAYIM * SKOP_ORAN (olcum3.h), float32'de
VA_A3 = f32(f32(f32(3.10) / 4096.0) * f32(38.03703704))


class Lcg:
    """Belirlenimci gurultu (Numerical Recipes LCG, 32 bit)."""

    def __init__(self, tohum: int) -> None:
        self.x = tohum & 0xFFFFFFFF

    def __call__(self) -> float:
        """[0, 1)"""
        self.x = (1664525 * self.x + 1013904223) & 0xFFFFFFFF
        return self.x / 4294967296.0

    def tam(self, a: int, b: int) -> int:
        """[a, b] tamsayi"""
        return a + int(self() * (b - a + 1))


def kirp(k: int) -> int:
    return 0 if k < 0 else (65535 if k > 65535 else k)


def sinus(n, periyot, merkez, genlik, faz=0.0, gurultu=0, tohum=1, alt=0, ust=65535):
    r = Lcg(tohum)
    c = []
    for i in range(n):
        g = r.tam(-gurultu, gurultu) if gurultu else 0
        k = int(math.floor(merkez + genlik * math.sin(2 * math.pi * i / periyot + faz) + 0.5)) + g
        c.append(min(max(k, alt), ust))
    return c


def kare(n, periyot, ust_pay, dusuk, yuksek, faz=0.0):
    """ust_pay: periyodun yuksekte gecen kesri; periyot kesirli olabilir."""
    c = []
    for i in range(n):
        p = (i / periyot + faz) % 1.0
        c.append(yuksek if p < ust_pay else dusuk)
    return c


def vakalar() -> list[dict]:
    V = []

    def ekle(ad, aciklama, ham, va=VA_A3, hz=10000.0, adet=None):
        V.append({"ad": ad, "aciklama": aciklama, "ham": [kirp(int(k)) for k in ham],
                  "adet": len(ham) if adet is None else adet, "volt_adim": f32(va), "hz": f32(hz)})

    # ── test_skop_olcum.py (A6) ile ayni bes dalga ─────────────────────
    ekle("kare50", "A6 KARE: periyot 80, %50, 200/3800",
         [3800 if (i % 80) < 40 else 200 for i in range(400)])
    ekle("kare25", "A6 D25: periyot 80, %25",
         [3800 if (i % 80) < 20 else 200 for i in range(400)])
    ekle("ucgen", "A6 UCGN: periyot 100, 200..3800",
         [200 + (min(i % 100, 100 - i % 100)) * 3600 // 50 for i in range(400)])
    ekle("sinus64", "periyot 64, 2048 +- 1500, 6 cevrim", sinus(384, 64, 2048, 1500))
    ekle("duz", "A6 DUZ: sabit 2048 -> olcum yok, Vac 0", [2048] * 400)

    # ── gorev orani ve kesirli periyot ─────────────────────────────────
    ekle("kare10_kesirli", "%10 gorev, periyot 33.3 ornek (kesirli kenar)",
         kare(500, 33.3, 0.10, 500, 3500))
    ekle("kare90", "%90 gorev, periyot 50", kare(400, 50, 0.90, 300, 3300, faz=0.37))
    ekle("sinus_kesirli", "periyot 47.3, faz 0.7 rad, 2000 +- 1000",
         sinus(700, 47.3, 2000, 1000, faz=0.7))
    ekle("sinus_hz_kesirli", "hz 12345.678 (float32), periyot 61.7",
         sinus(600, 61.7, 2100, 1800, faz=2.0), hz=12345.678)

    # ── gurultu ve histerezis ─────────────────────────────────────────
    ekle("sinus_gurultu", "periyot 90.7, +-150 gurultu < histerezis (sahte kenar yok)",
         sinus(800, 90.7, 2048, 1200, gurultu=150, tohum=7))
    k = kare(400, 100, 0.5, 400, 3600)
    for i in range(400):                 # ust seviyede orta-hist'e INMEYEN dipler
        if (i % 100) in (10, 30):
            k[i] = 1700                  # orta 2000, hist 400 -> 1600'un ustu: yeniden kurulmaz
    ekle("ani_dip_hist_ustu", "ustte orta altina inen ama orta-hist'e inmeyen dipler", k)
    k = kare(400, 100, 0.5, 400, 3600)
    for i in range(400):                 # orta-hist'in ALTINA inen dip: C sahte kenar sayar
        if (i % 100) == 20:
            k[i] = 1500
    ekle("ani_dip_hist_alti", "ustte orta-hist altina inen dip: C fazladan kenar sayar (gercek davranis)", k)
    ekle("hist_7", "fark 7 kod -> hist 0.875 < 1: zaman olcumu YOK (erken donus)",
         kare(200, 20, 0.5, 1000, 1007))
    ekle("hist_8", "fark 8 kod -> hist 1.0: olculur", kare(200, 20, 0.5, 1000, 1008))
    ekle("esik_tam_orta", "ornek tam orta seviyede (s >= orta, kesisim 1)",
         [0, 0, 50, 100, 100, 50, 0, 0] * 30)
    ekle("kirpik", "2048 +- 3000 sinus, 0..4095'te kirpilmis", sinus(600, 60, 2048, 3000, alt=0, ust=4095))

    # ── float32 davranisi: double ile ayni cikmayan durumlar ──────────
    # alt = 4000 + 500*0.1f: float32'de TAM 4050, double'da 4050.0000007. Ornek 4050'de durup
    # geri inerse float32'de t10 burada baslar, double'da bir SONRAKI kenarda -> tr cok farkli.
    k = [4000] * 20 + [4020, 4040, 4050, 4040, 4020] + [4000] * 20 + \
        [4000 + 50 * j for j in range(11)] + [4500] * 40 + [4000] * 20
    ekle("esik_float32", "alt esik float32'de tamsayi: ornek esige ESIT (double ile farkli tr)", k)
    ekle("dc_ustu_kucuk_ac", "3000 kod DC + +-3 kod gurultu: float32'de Vac kare farkindan (kayip)",
         [3000 + j for j in lcg_dizi(1000, -3, 3, 11)])
    ekle("tam_olcek_65535", "0/65535 kare, va 0.001 (dogrusallastirilmis kod tavani)",
         kare(300, 30, 0.5, 0, 65535), va=0.001)
    ekle("sabit_65535", "sabit 65535: kare farki yuvarlamasi (Vac kirpma yolu)", [65535] * 333, va=0.0123)

    # ── tek kenar, kisa, bos ──────────────────────────────────────────
    ekle("tek_yukselen", "tek yukselen kenar (7 ornek rampa): f yok, tr var",
         [300] * 120 + [300 + 3000 * j // 7 for j in range(1, 7)] + [3300] * 174)
    ekle("tek_dusen", "tek dusen kenar: f yok, tf var",
         [3300] * 100 + [3300 - 3000 * j // 9 for j in range(1, 9)] + [300] * 92)
    ekle("bos", "adet 0 -> her alan 0", [])
    ekle("tek_ornek", "adet 1", [1234])
    ekle("iki_ornek", "adet 2: kenar sayilamaz ama tr olculur", [100, 3000])
    ekle("adet_kisa", "dizi 300, adet 150: yalniz ilk 150", kare(300, 40, 0.5, 100, 2000), adet=150)

    # ── parametre uclari ──────────────────────────────────────────────
    s = sinus(300, 50, 2048, 1500)
    ekle("hz_sifir", "hz 0 -> her alan 0 (gerilimler DAHIL)", s, hz=0.0)
    ekle("hz_eksi", "hz -5 -> her alan 0", s, hz=-5.0)
    ekle("va_sifir", "va 0 -> gerilimler 0, zaman olculur", s, va=0.0)
    ekle("va_eksi", "va eksi: Vmax = hmax*va (Vmin'den KUCUK) — C sozlesmesi", s, va=-0.01)

    # ── yukselme/dusme ozel durumlari ─────────────────────────────────
    k = [200] * 30 + [200 + 300 * j for j in range(1, 8)] + [2300] * 5 + [200] * 30 + \
        [200 + 400 * j for j in range(1, 10)] + [3800] * 30 + [200] * 20
    ekle("cuce_darbe", "%90'a ulasmayan darbe sonra tam kenar: tr ikisini kapsar (C davranisi)", k)
    ekle("yuksekte_baslar", "yuksekte baslayip dusen kare: hazir mantigi",
         kare(450, 90, 0.5, 250, 3750, faz=0.1))

    # ── kartin gercek boyutu ──────────────────────────────────────────
    ekle("sinus_4000", "4000 ornek @ 83333 Hz, ~1 kHz + gurultu (kartin azami adedi)",
         sinus(4000, 83.333, 2200, 1700, faz=0.3, gurultu=25, tohum=3), hz=83333.0)
    return V


def lcg_dizi(n: int, a: int, b: int, tohum: int) -> list[int]:
    r = Lcg(tohum)
    return [r.tam(a, b) for _ in range(n)]


def derle() -> bytearray:
    if not AVR_GCC.exists():
        raise SystemExit(f"avr-gcc yok: {AVR_GCC}")
    d = gecici.dizin("skopolc_")
    c = d / "ortak_skop.c"
    c.write_text(HARNESS, encoding="utf-8")
    elf = d / "ortak_skop.elf"
    r = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu11",
         "-Wall", "-Wextra", f"-I{BASLIK.parent}", "-o", str(elf), str(c), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("avr-gcc derleyemedi:\n" + r.stderr)
    uyari = [x for x in r.stderr.splitlines() if "warning:" in x]
    if uyari:
        raise SystemExit("avr-gcc uyari verdi:\n" + "\n".join(uyari))
    flash, _ = flash_goruntusu(elf)
    return flash


def cozf(h: str) -> float:
    return struct.unpack(">f", bytes.fromhex(h))[0]


def kostur(flash: bytearray, v: dict) -> dict:
    assert len(v["ham"]) <= AZAMI_ADET and v["adet"] <= len(v["ham"])
    kart = mega328.Kart(flash, lambda f: Cekirdek(f, ram_boyut=RAM_BOYUT))
    m = kart.cpu.m
    struct.pack_into("<Hff", m, GIRDI_ADRES, v["adet"], v["volt_adim"], v["hz"])
    if v["ham"]:
        struct.pack_into(f"<{len(v['ham'])}H", m, HAM_ADRES, *v["ham"])
    for _ in range(4000):
        kart.cevrim_kadar_kos(250_000)
        if b"BITTI" in kart.tx:
            break
    else:
        raise SystemExit(f"{v['ad']}: emulator bitmedi")
    satir = [s for s in kart.tx.decode("ascii", "replace").splitlines() if s.startswith("R ")]
    p = satir[0].split()
    assert len(p) == 13, satir
    sonuc = {ad: cozf(h) for ad, h in zip(ALANLAR, p[1:12])}
    sonuc["n"] = int(p[12])
    for ad in ALANLAR:
        assert math.isfinite(sonuc[ad]), (v["ad"], ad, sonuc[ad])
    return sonuc


def uret() -> str:
    flash = derle()
    satirlar = []
    for v in vakalar():
        v["beklenen"] = kostur(flash, v)
        satirlar.append(json.dumps(v, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    bas = {
        "aciklama": "2E capraz vektorleri: skop_olc (kod/olcum-karti-a3/skop_olc.h) AVR emulatorunde "
                    "kosturuldu; beklenen = C'nin float32 ciktisi (double'a tam cevrilmis). "
                    "JS skopOlc(ham, adet, volt_adim, hz) her alani Object.is ile ayni vermeli.",
        "kaynak": "kod/olcum-karti-a3/skop_olc.h",
        "kaynak_sha256": hashlib.sha256(BASLIK.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "alanlar": list(ALANLAR) + ["n"],
    }
    ust = json.dumps(bas, ensure_ascii=False, indent=1)[:-2]       # son "\n}" kesilir
    return ust + ',\n "vakalar": [\n  ' + ",\n  ".join(satirlar) + "\n ]\n}\n"


def main() -> int:
    metin = uret()
    if "--denetle" in sys.argv:
        guncel = HEDEF.exists() and HEDEF.read_text(encoding="utf-8") == metin
        print("guncel" if guncel else f"ESKI — python uretim/{Path(__file__).name}")
        return 0 if guncel else 1
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_text(metin, encoding="utf-8", newline="\n")
    n = metin.count('"ad":')
    print(f"yazildi: {HEDEF.relative_to(KOK).as_posix()} ({n} vaka, {len(metin.encode('utf-8'))} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
