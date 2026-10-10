# -*- coding: utf-8 -*-
"""SK1 — Osiloskop on suzgecinin (medyan-3 + kutu ortalamasi) AVR emulatorunde dogrulanmasi.

    python test_skop_suz.py

`kod/olcum-karti-a3/skop_suz.h` PLATFORM BAGIMSIZ ve yalniz tamsayi. Burada GERCEK KOD avr-gcc ile
derlenip bit birebir dogrulanmis AVR emulatorunde kosturuluyor (test_skop_olcum.py ile ayni yontem).

NEDEN VAR (kartta olculdu, 2026-10-10, 12 yakalamanin ham kodlari):
  * skop izindeki sivri darbeler HEP tek ornek genisliginde (nadiren 2), 64-138 kod (1.8-4 V);
    giristeki RC (6.4 kohm x 1 nF, 25 kHz) tek ornekte (12 us) bu kadar sicrayamaz -> darbe girisin
    degil donusum aninin urunu. Medyan-3 12 yakalamada hepsini sildi (0 kaldi).
  * yavas zaman tabaninda ADC de yavas ornekliyordu: her nokta TEK ham okuma. Simdi ADC hep
    ust hiza yakin kosar, cikis ornegi k ham ornegin (medyandan sonra) ortalamasidir.

Beklenenler ANALITIK: igne silinir, iki ornekli darbe ve basamak AYNEN kalir, rampa/DC/yuvarlama
elle hesaplanir. Gurultu durumunda ayrica bagimsiz bir Python basvurusuyla birebir karsilastirilir.
"""
from __future__ import annotations

import os
import statistics
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
URETIM = Path(os.environ.get("SUZ_URETIM", BURASI))
sys.path.insert(0, str(URETIM))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr import mega328                          # noqa: E402
from avr.cekirdek import Cekirdek                # noqa: E402
from avr.elf import flash_goruntusu              # noqa: E402
import gecici                                    # noqa: E402

KOK = URETIM.parent
BASLIK_DIZIN = Path(os.environ.get("SUZ_BASLIK_DIZIN", KOK / "kod" / "olcum-karti-a3"))
ORNEK = Path(os.environ.get("SUZ_ORNEK", URETIM / "avr" / "ornek_skop_suz.c"))
AVR_GCC = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin" / "avr-gcc.exe")
SAAT_HZ = 2_500_000      # S3 surekli ADC: APB 80 MHz / 16 / 2; ornekleme = bu / tamsayi aralik
N_ASGARI = 30            # 2.5 MHz / 30 = 83 333 Sa/s (SOC ust siniri)

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"  {ek}" if ek else ""))


# ── girdi kurallari: ornek_skop_suz.c'deki `girdi()` ile BIREBIR ayni ──────────────
class Girdi:
    def __init__(self) -> None:
        self.lcg = 12345

    def al(self, durum: int, i: int) -> int:
        if durum == 0:
            if i in (10, 20, 22, 45):
                return 3000
            if i in (37, 46):
                return 0
            if i in (60, 61):
                return 3000
            return 1000
        if durum == 1:
            return 500 if i < 30 else 3500
        if durum == 2:
            return 100 + 3 * i
        if durum == 3:
            return 2047
        if durum == 4:
            return 1000 + (i & 1)
        self.lcg = (self.lcg * 1103515245 + 12345) & 0xFFFFFFFF
        v = 2000 + ((self.lcg >> 16) & 127) - 64
        if i % 97 == 50:
            v += 1500
        return v & 0xFFFF


def dizi(durum: int, adet: int) -> list[int]:
    g = Girdi()
    return [g.al(durum, i) for i in range(adet)]


def basvuru(x: list[int], k: int) -> list[int]:
    """Bagimsiz basvuru: IKI KAT medyan-3 (ilk dort ornek pencereleri doldurur), sonra k'lik kutu, yarim YUKARI."""
    k = max(k, 1)
    med = [sorted(x[i:i + 3])[1] for i in range(len(x) - 2)]
    med = [sorted(med[i:i + 3])[1] for i in range(len(med) - 2)]
    return [(sum(med[j:j + k]) + k // 2) // k for j in range(0, len(med) - k + 1, k)]


def kostur() -> dict:
    gec_dizin = gecici.dizin("skopsuz_")
    elf = gec_dizin / "ornek_skop_suz.elf"
    d = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu11", "-Wall", "-Wextra",
         f"-I{BASLIK_DIZIN}", "-o", str(elf), str(ORNEK)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if d.returncode != 0:
        print(d.stderr)
        raise SystemExit("avr-gcc derleyemedi")
    uyari = [s for s in d.stderr.splitlines() if "warning:" in s]
    ok("skop_suz.h AVR'de uyarisiz derlendi", not uyari, f"{len(uyari)} uyari")
    for u in uyari[:5]:
        print("       " + u)

    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    kart.cevrim_kadar_kos(60_000_000)
    metin = kart.tx.decode("ascii", "replace")
    ok("Program tamamlandi (BITTI)", "BITTI" in metin, f"{kart.cpu.cevrim:,} cevrim".replace(",", " "))

    sonuc: dict = {"PLAN": {}}
    for sat in metin.splitlines():
        p = sat.split()
        if len(p) == 6 and p[0] == "PLAN":
            sonuc["PLAN"][int(p[1])] = tuple(int(v) for v in p[2:])
        elif len(p) >= 3 and p[-2] == "n":
            sonuc[p[0]] = {"cikis": [int(h, 16) for h in p[1:-2]], "n": int(p[-1])}
    return sonuc


def main() -> int:
    print("=" * 78)
    print("  SK1  OSILOSKOP ON SUZGECI  (gercek kod, AVR emulatorunde)")
    print("=" * 78)
    print("\n--- 1. Derleme ve kosum -------------------------------------------")
    s = kostur()
    adlar = ("IGNE", "BASAMAK", "ORT4", "DC", "YUVARLA", "GURULTU", "SIFIRK")
    ok("Emulator butun durumlari isledi", all(a in s for a in adlar) and len(s["PLAN"]) == 11,
       f"{sum(a in s for a in adlar)}/{len(adlar)} durum, {len(s['PLAN'])} plan")
    if not all(a in s for a in adlar) or len(s["PLAN"]) != 11:
        print(f"\n  SONUC: {gecti} gecti, {kaldi + 1} kaldi")
        return 1

    print("\n--- 2. Hiz plani: ADC ust hiza yakin, GERCEK hiz bildirilir -----------")
    print("       nominal -> k x N    ADC istenen   gercek cikis   sapma")
    plan = {hz: v for hz, v in s["PLAN"].items() if 0 < hz <= SAAT_HZ // N_ASGARI}
    for hz, (k, n, hz_adc, hz_g) in sorted(plan.items()):
        print(f"       {hz:6d} -> {k:3d} x {n:2d}   {hz_adc:6d}        {hz_g:6d}         "
              f"{100 * (hz_g - hz) / hz:+.2f} %")
    ok("ADC araligi N her zaman 30..59 (ADC ust hizin yarisindan hizli, ust siniri asmaz)",
       all(N_ASGARI <= n < 2 * N_ASGARI for (_k, n, _a, _g) in plan.values()),
       "N < 30 SOC ust sinirini (83 333 Sa/s) asar; N >= 60 ortalama alacak ornek birakmaz")
    ok("k >= 1 ve k = T / 30 (T = saat / nominal, yuvarlanmis)",
       all(k == max(((SAAT_HZ + hz // 2) // hz) // N_ASGARI, 1) for hz, (k, _n, _a, _g) in plan.items()))
    ok("Surucu istenen hizdan TAM N araligini kuruyor (saat // hz_adc == N)",
       all(SAAT_HZ // hz_adc == n for (_k, n, hz_adc, _g) in plan.values()),
       "surucu araligi asagi yuvarlar; baska bir N'ye dusseydi gercek hiz bildirilenden farkli olurdu")
    ok("Bildirilen gercek cikis hizi = saat / (N k), en yakin Hz",
       all(hz_g == (SAAT_HZ + (n * k) // 2) // (n * k) for (k, n, _a, hz_g) in plan.values()))
    en_sapma = max(abs(hz_g - hz) / hz for hz, (_k, _n, _a, hz_g) in plan.items())
    ok("Gercek hiz nominalden en cok ~%1.7 sapiyor (1 / 2N); BILDIRILDIGI icin zaman ekseni dogru",
       en_sapma <= 1 / (2 * N_ASGARI) + 0.002, f"en buyuk sapma %{100 * en_sapma:.2f}")
    ok("Ust hizda (83 333) ve 50 kSa/s'te k = 1, hiz TAM nominal",
       plan[83333] == (1, 30, 83333, 83333) and plan[50000] == (1, 50, 50000, 50000),
       f"{plan[83333]} {plan[50000]}")
    ok("N YUVARLANIYOR (asagi kesilmiyor): 26 316 Sa/s -> T = 95, k = 3, N = 32 (31.67)",
       plan[26316][:2] == (3, 32), f"{plan[26316]} — N = 31 olsaydi sapma %+2.2 olurdu")
    ok("Yavas tabanda cok ornek ortalaniyor: 1 kSa/s -> k = 83, 611 Sa/s -> k = 136",
       plan[1000][0] == 83 and plan[611][0] == 136, f"k = {plan[1000][0]}, {plan[611][0]}")
    ok("Ust sinirin ustunde nominal (100 kSa/s): k = 1, N = 30 (ust hiza kirpilir)",
       s["PLAN"][100000] == (1, 30, 83333, 83333), f"{s['PLAN'][100000]}")
    ok("Nominal 0 verilirse cokme yok: k >= 1, N >= 30 (0'a bolme yok)",
       s["PLAN"][0][0] >= 1 and s["PLAN"][0][1] >= N_ASGARI, f"{s['PLAN'][0]}")

    print("\n--- 3. IGNE: tek ornek darbe silinir, iki ornek darbe KALIR ---------")
    c = s["IGNE"]["cikis"]
    ok("Cikis adedi = girdi - 4 (iki medyan penceresi)", s["IGNE"]["n"] == 76 and len(c) == 76, f"{len(c)}")
    beklenen = [1000] * 76
    beklenen[58] = beklenen[59] = 3000          # 60-61'deki iki ornekli darbe IKI ornek gecikmeyle
    ok("+2000 kodluk tek ornek igne (10) SILINDI", c[6:11] == [1000] * 5, f"{c[6:11]}")
    ok("[!] BIR ATLAYARAK iki igne (20, 22) SILINDI — tek kat medyan ortadakini igne birakirdi",
       c[16:23] == [1000] * 7, f"{c[16:23]}")
    ok("-1000 kodluk tek ornek igne (37) SILINDI", c[33:38] == [1000] * 5, f"{c[33:38]}")
    ok("YAN YANA zit iki igne (45 +, 46 -) SILINDI", c[41:47] == [1000] * 6, f"{c[41:47]}")
    ok("IKI ornekli darbe AYNEN kaldi (gercek sinyal olabilir)", c[57:61] == [1000, 3000, 3000, 1000],
       f"{c[57:61]}")
    ok("Geri kalan her ornek tabanda", c == beklenen)

    print("\n--- 4. BASAMAK: kenar bozulmaz, yalniz bir ornek gecikir -----------")
    x = dizi(1, 60)
    c = s["BASAMAK"]["cikis"]
    ok("Cikis = girdinin iki ornek kaydirilmisi (kenar TEK ornekte, yumusama yok)", c == x[2:-2],
       f"kenar cikista {c.index(3500)}. ornekte (girdide 30)")

    print("\n--- 5. Kutu ortalamasi: rampa, DC, yuvarlama ------------------------")
    c = s["ORT4"]["cikis"]
    ok("ORT4 cikis adedi = (42 - 4) // 4", len(c) == 9, f"{len(c)}")
    ok("Rampada 4'luk ortalama = 110.5 + 12 j -> yarim YUKARI 111 + 12 j",
       c == [111 + 12 * j for j in range(9)], f"{c[:4]} ...")
    c = s["DC"]["cikis"]
    ok("DC 2047, k = 7: her cikis TAM 2047", c == [2047] * 9, f"{len(c)} cikis")
    c = s["YUVARLA"]["cikis"]
    ok("1000/1001 almasik, k = 2: 1000.5 -> 1001 (kesme degil yuvarlama)", c == [1001] * 19, f"{c[:3]} ...")
    c = s["SIFIRK"]["cikis"]
    ok("k = 0 verilirse 1 sayilir (0'a bolme yok, cikis akar)", c == [2047] * 8, f"{len(c)} cikis")

    print("\n--- 6. GURULTU: +-64 kod gurultu + 1500 kodluk igneler, k = 16 ------")
    x = dizi(5, 962)
    c = s["GURULTU"]["cikis"]
    ok("Cikis bagimsiz basvuruyla BIREBIR ayni", c == basvuru(x, 16), f"{len(c)} ornek")
    ok("Cikis adedi = (962 - 4) // 16", len(c) == 59, f"{len(c)}")
    igne = [v for v in x if v > 3000]
    ok("Girdide igneler var (sinama bos degil)", len(igne) >= 9, f"{len(igne)} igne, en buyuk {max(x)}")
    ok("Cikista hicbir ornek igne tasimiyor (|sapma| <= 40 kod)", all(abs(v - 2000) <= 40 for v in c),
       f"en buyuk sapma {max(abs(v - 2000) for v in c)} kod")
    temiz = [v for v in x if v <= 3000]
    ok("Gurultu std'si en az 3 kat dustu (16'lik ortalama, beyaz gurultude 4 kat)",
       statistics.pstdev(c) * 3 <= statistics.pstdev(temiz),
       f"girdi {statistics.pstdev(temiz):.1f} kod -> cikis {statistics.pstdev(c):.1f} kod")

    print("\n" + "=" * 78)
    print(f"  SONUC: {gecti} gecti, {kaldi} kaldi")
    print("=" * 78)
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
