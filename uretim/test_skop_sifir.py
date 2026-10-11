# -*- coding: utf-8 -*-
"""SZ — Osiloskop kanalinin KULLANICI SIFIRI (`tz` / `tz0` / `tz?`, A3-SK3).

    python test_skop_sifir.py

1. CEKIRDEK: `kod/olcum-karti-a3/skop_sifir.h` (platformsuz) GERCEK KOD olarak iki yerde kosar:
   avr-gcc + AVR emulatoru (test_skop_suz.py ile ayni yontem) ve host gcc. Iki cikti BIT BIT ayni
   olmali; beklenenler Python'da float32 islem sirasiyla (her islem ayri yuvarlanir) hesaplanir.
   Sinanan: bilinen kod ortalamasindan dogru volt, +-6 V sinir reddi, saçılma ve kayma reddi,
   eksik yakalama reddi, `tz0` sonrasi ofset = fabrika (bit bit), NVS'ten bozuk deger reddi,
   `skop_ofsetle` aritmetigi, kartta olculen kisa devre gurultusunun KABULU.
2. FIRMWARE KAYNAK DENETIMI (.ino): kullanici sifiri `skop_ofsetle` (M satiri) VE `CT ofset=`'e
   birlikte giriyor (tek kaynak `skop_volt_ofset`), ret kosullari komut dalinda, `tz` kullanicinin
   skop ayarlarini her yolda geri yukluyor, NVS ayri ad alani (kalibrasyon gecmisine girmez),
   `?` / `CT` / `tz?` ciktisinda gorunur, skop gunlugunun META ofseti kullanici sifirini tasiyor.
Bulutta ESP32 derleyicisi yok: gercek derleme ve kartta `tz` yerelde (DEVIR 5.12.123).
"""
from __future__ import annotations

import math
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
URETIM = Path(os.environ.get("SZ_URETIM", BURASI))
sys.path.insert(0, str(URETIM))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr import mega328                          # noqa: E402
from avr.cekirdek import Cekirdek                # noqa: E402
from avr.elf import flash_goruntusu              # noqa: E402
import gecici                                    # noqa: E402

KOK = URETIM.parent
BASLIK_DIZIN = Path(os.environ.get("SZ_BASLIK_DIZIN", KOK / "kod" / "olcum-karti-a3"))
INO = BASLIK_DIZIN / "olcum-karti-a3.ino"
ORNEK = URETIM / "avr" / "ornek_skop_sifir.c"
AVR_GCC = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin" / "avr-gcc.exe")
PROGRAM_ADRES = 0x0A00
PROGRAM_AZAMI = 0xC000 - PROGRAM_ADRES
RAM_BOYUT = 0xC000 + 2 * 1024 + 16

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> bool:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"  {ek}" if ek else ""))
    return kosul


# ── float32 (her islem ayri yuvarlanir; double'da yapip f32'ye yuvarlamak +-*/ sqrt icin TAM) ──
def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def bit(x: float) -> str:
    return struct.pack(">f", x).hex()


def cozf(h: str) -> float:
    return struct.unpack(">f", bytes.fromhex(h))[0]


ORAN = f32(38.03703704)
VREF = f32(1.7153125)
FAB = f32(VREF * f32(ORAN - 1.0))                  # SKOP_VOLT_OFSET (derleyicinin float katlamasi)
KOD_V = f32(f32(f32(3.10) / 4096.0) * ORAN)        # SKOP_VOLT_ADIM
SINIR, SACILMA, KAYMA, YAKALAMA = 6.0, 1.2, 0.6, 10
TAMAM, E_AZ, E_SINIR, E_SACILMA, E_KAYMA = range(5)


# ── program (ornek_skop_sifir.c) ────────────────────────────────────────
class Program:
    def __init__(self) -> None:
        self.b = bytearray()
        self.beklenen: list[tuple[str, object]] = []   # (tur, bilgi) — cikti satirlariyla sirali

    def _f(self, *x: float) -> None:
        for v in x:
            self.b += struct.pack("<f", v)

    def bas(self) -> None:
        self.b += b"B"

    def ekle(self, kodlar: list[int], bilgi: object = None) -> None:
        self.b += b"E" + struct.pack("<H", len(kodlar)) + struct.pack(f"<{len(kodlar)}H", *kodlar)
        self.beklenen.append(("E", bilgi))

    def karar(self, mv: float, oran: float, fab: float, kod_v: float, bilgi: object) -> None:
        self.b += b"K"
        self._f(mv, oran, fab, kod_v)
        self.beklenen.append(("K", bilgi))

    def ofset(self, fab: float, kul: float, bilgi: object = None) -> None:
        self.b += b"O"
        self._f(fab, kul)
        self.beklenen.append(("O", bilgi))

    def volt(self, mv: float, oran: float, fab: float, bilgi: object = None) -> None:
        self.b += b"V"
        self._f(mv, oran, fab)
        self.beklenen.append(("V", bilgi))

    def gecerli(self, kul: float, bilgi: object = None) -> None:
        self.b += b"G"
        self._f(kul)
        self.beklenen.append(("G", bilgi))

    def ofsetle(self, mx: float, mn: float, av: float, rm: float, ac: float, of: float, bilgi=None) -> None:
        self.b += b"F"
        self._f(mx, mn, av, rm, ac, of)
        self.beklenen.append(("F", bilgi))

    def sebep(self, e: int) -> None:
        self.b += b"S" + bytes([e])
        self.beklenen.append(("S", e))

    def bitir(self) -> bytes:
        return bytes(self.b + b"Q")


def avr_kostur(program: bytes) -> list[str]:
    if len(program) > PROGRAM_AZAMI:
        raise SystemExit(f"program {len(program)} B > {PROGRAM_AZAMI} B")
    d = gecici.dizin("skopsifir_")
    elf = d / "ornek_skop_sifir.elf"
    r = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu11", "-Wall", "-Wextra",
         f"-I{BASLIK_DIZIN}", "-o", str(elf), str(ORNEK), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit("avr-gcc derleyemedi")
    uyari = [s for s in r.stderr.splitlines() if "warning:" in s]
    ok("skop_sifir.h (+ skop_olc.h) AVR'de uyarisiz derlendi", not uyari, f"{len(uyari)} uyari")
    for u in uyari[:5]:
        print("       " + u)
    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, lambda f: Cekirdek(f, ram_boyut=RAM_BOYUT))
    kart.cpu.m[PROGRAM_ADRES:PROGRAM_ADRES + len(program)] = program
    for _ in range(20000):
        kart.cevrim_kadar_kos(1_000_000)
        if b"BITTI" in kart.tx:
            break
    metin = kart.tx.decode("utf-8", "replace")
    ok("AVR: program tamamlandi (BITTI)", "BITTI" in metin, f"{kart.cpu.cevrim:,} cevrim".replace(",", " "))
    return [s for s in metin.splitlines() if s and s != "BITTI"]


def host_kostur(program: bytes) -> list[str] | None:
    gcc = shutil.which("gcc") or shutil.which("cc")
    if not gcc:
        print("  [--] host gcc yok — host karsilastirmasi ATLANDI")
        return None
    d = gecici.dizin("skopsifir_host_")
    exe = d / "ornek_skop_sifir"
    r = subprocess.run([gcc, "-DHOST", "-std=gnu11", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                        f"-I{BASLIK_DIZIN}", "-o", str(exe), str(ORNEK), "-lm"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr)
        ok("host gcc derledi", False)
        return None
    uyari = [s for s in r.stderr.splitlines() if "warning:" in s]
    ok("skop_sifir.h host gcc'de (-Wall -Wextra) uyarisiz derlendi", not uyari, f"{len(uyari)} uyari")
    for u in uyari[:5]:
        print("       " + u)
    c = subprocess.run([str(exe)], input=program, capture_output=True, timeout=60)
    metin = c.stdout.decode("utf-8", "replace")
    return [s for s in metin.splitlines() if s and s != "BITTI"]


# ── girdiler ────────────────────────────────────────────────────────────
class Lcg:
    def __init__(self, tohum: int) -> None:
        self.x = tohum & 0xFFFFFFFF

    def __call__(self) -> float:
        self.x = (self.x * 1103515245 + 12345) & 0xFFFFFFFF
        return ((self.x >> 8) & 0xFFFF) / 65536.0

    def gauss(self) -> float:
        u1 = max(self(), 1e-6)
        return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * self())


def kisa_devre(tohum: int, adet: int, merkez: float, sigma_kod: float, kayma_kod: float,
               igne_binde: float = 0.0) -> list[list[int]]:
    """Kartta olculen kisa devre modeli (SK-8): her yakalamanin ortalamasi yavas oynar
    (kayma_kod std), ornek gurultusu sigma_kod, seyrek tek ornek igneler 64..138 kod (ham kip)."""
    r = Lcg(tohum)
    out = []
    for _ in range(YAKALAMA):
        m = merkez + kayma_kod * r.gauss()
        c = []
        for _ in range(adet):
            v = m + sigma_kod * r.gauss()
            if igne_binde and r() * 1000 < igne_binde:
                v += (1 if r() < 0.5 else -1) * (64 + 74 * r())
            c.append(max(0, min(4095, round(v))))
        out.append(c)
    return out


def bekle_istat(yakalamalar: list[list[int]]) -> dict:
    """skop_sifir_ekle + ort/sacilma hesabinin float32 basvurusu (C ile ayni islem sirasi)."""
    n = top = kare = 0
    ort_az = ort_cok = 0.0
    for j, c in enumerate(yakalamalar):
        t = sum(c)
        o = f32(f32(float(t)) / f32(float(len(c))))
        if j == 0 or o < ort_az:
            ort_az = o
        if j == 0 or o > ort_cok:
            ort_cok = o
        n += len(c)
        top += t
        kare += sum(x * x for x in c)
    ort = f32(f32(float(top)) / f32(float(n)))
    a, b = n * kare, top * top
    if n < 2 or a <= b:
        sac = 0.0
    else:
        x = a - b
        uf = f32(f32(f32(float(x >> 32)) * 4294967296.0) + f32(float(x & 0xFFFFFFFF)))
        nf = f32(float(n))
        sac = f32(math.sqrt(f32(f32(uf / nf) / nf)))
    return {"n": n, "ort": ort, "sac": sac, "ort_az": ort_az, "ort_cok": ort_cok}


def bekle_volt(mv: float, oran: float, fab: float) -> float:
    return f32(f32(f32(mv / 1000.0) * oran) - fab)


def mv_icin(volt: float) -> float:
    """Fabrika donusumu `volt` versin diye pin mV'u (yaklasik — beklenen yine f32 ile hesaplanir)."""
    return f32((volt + FAB) / ORAN * 1000.0)


def program_kur() -> Program:
    p = Program()
    # 1) bilinen ortalama: 2200 / 2201 almasik -> 2200.5 kod, saçılma 0.5 kod
    p.bas()
    bilinen = [[2200 + (i & 1) for i in range(100)] for _ in range(YAKALAMA)]
    for c in bilinen:
        p.ekle(c, 1)
    mv1 = f32(1800.25)
    p.karar(mv1, ORAN, FAB, KOD_V, ("BILINEN", bilinen, mv1))
    # 2) fabrika: kart fabrika donusumuyle 0 V gosteriyorsa kullanici sifiri ~0
    mv0 = mv_icin(0.0)
    p.karar(mv0, ORAN, FAB, KOD_V, ("FABRIKA", bilinen, mv0))
    # 3) sinir: +6.5 V / -6.5 V / +5.9 V / NaN
    for ad, v in (("SINIR+", 6.5), ("SINIR-", -6.5), ("SINIR_ICI", 5.9), ("SINIR_KENAR", 6.0005)):
        p.karar(mv_icin(v), ORAN, FAB, KOD_V, (ad, bilinen, mv_icin(v)))
    p.karar(float("nan"), ORAN, FAB, KOD_V, ("NAN", bilinen, float("nan")))
    # 4) eksik yakalama: 9
    p.bas()
    for c in bilinen[:YAKALAMA - 1]:
        p.ekle(c, 1)
    p.karar(mv1, ORAN, FAB, KOD_V, ("AZ", bilinen[:YAKALAMA - 1], mv1))
    p.ekle([], "BOS")                                  # bos yakalama EKLENMEZ
    p.karar(mv1, ORAN, FAB, KOD_V, ("AZ_BOS", bilinen[:YAKALAMA - 1], mv1))
    # 5) saçılma: 2100 / 2300 almasik (std 100 kod ~ 2.9 V) — giriste sinyal var
    p.bas()
    sac = [[2100 if i & 1 else 2300 for i in range(100)] for _ in range(YAKALAMA)]
    for c in sac:
        p.ekle(c, 1)
    p.karar(mv1, ORAN, FAB, KOD_V, ("SACILMA", sac, mv1))
    # 5b) Arduino'nun 5 V karesi (174 kod tepe-tepe, %50) — reddedilmeli
    p.bas()
    kare5 = [[2200 + (174 if (i // 10) & 1 else 0) for i in range(200)] for _ in range(YAKALAMA)]
    for c in kare5:
        p.ekle(c, 1)
    p.karar(mv1, ORAN, FAB, KOD_V, ("KARE5V", kare5, mv1))
    # 6) kayma: yakalama ortalamalari 2200 .. 2236 (36 kod ~ 1.04 V), ornekler sakin
    p.bas()
    kay = [[2200 + 4 * j + (i & 1) for i in range(100)] for j in range(YAKALAMA)]
    for c in kay:
        p.ekle(c, 1)
    p.karar(mv1, ORAN, FAB, KOD_V, ("KAYMA", kay, mv1))
    # 7) kartta olculen kisa devre: ornek std 17 kod (~0.5 V), yakalama ortalamasi std 2 kod
    #    (~0.06 V; 0.14 V'luk olculen oynama), suzgecsiz (ham) kipteki igneler (%3, 64..138 kod)
    for ad, sig, igne in (("KISA_SUZGECLI", 6.0, 0.0), ("KISA_HAM", 17.0, 30.0), ("KISA_USBSIZ", 21.0, 30.0)):
        p.bas()
        kd = kisa_devre(len(ad) * 7919, 400, 2290.0 if ad != "KISA_USBSIZ" else 2380.0, sig, 2.0, igne)
        for c in kd:
            p.ekle(c, 1)
        p.karar(mv1, ORAN, FAB, KOD_V, (ad, kd, mv1))
    # 8) tz0 = fabrika (bit bit), kullanici sifiri toplanir
    for kul in (0.0, 2.6, -0.33, 6.0, -6.0):
        p.ofset(FAB, f32(kul), f32(kul))
    p.volt(mv1, ORAN, FAB, mv1)
    # 9) NVS'ten okunan deger: bozuksa fabrika
    for kul, b in ((0.0, 1), (2.6, 1), (-6.0, 1), (6.0, 1), (6.0001, 0), (-7.0, 0), (float("nan"), 0),
                   (float("inf"), 0), (float("-inf"), 0)):
        p.gecerli(kul, b)
    # 10) skop_ofsetle aritmetigi
    for mx, mn, av, ac, kul in ((70.0, 60.0, 63.6, 0.4, 0.0), (65.0, 61.5, 63.53, 1.2, 2.6),
                                (64.1, 63.0, 63.4, 0.01, -0.3)):
        of = f32(FAB + f32(kul))
        p.ofsetle(f32(mx), f32(mn), f32(av), 0.0, f32(ac), of, (f32(mx), f32(mn), f32(av), f32(ac), of))
    for e in range(6):
        p.sebep(e)
    return p


def main() -> int:
    print("=" * 78)
    print("  SZ  OSILOSKOP KULLANICI SIFIRI  (gercek kod: AVR emulatoru + host gcc)")
    print("=" * 78)
    print("\n--- 1. Derleme ve kosum ----------------------------------------------")
    p = program_kur()
    prog = p.bitir()
    avr = avr_kostur(prog)
    host = host_kostur(prog)
    ok("Cikti satiri sayisi = istenen", len(avr) == len(p.beklenen), f"{len(avr)} / {len(p.beklenen)}")
    if host is not None:
        ok("[!] AVR ve host ciktisi BIT BIT ayni (platformsuz cekirdek; float islem sirasi sabit)",
           avr == host, f"{sum(a != h for a, h in zip(avr, host))} farkli satir")
    if len(avr) != len(p.beklenen):
        print(f"\n  SONUC: {gecti} gecti, {kaldi} kaldi")
        return 1

    kararlar: dict[str, tuple[int, float, float, float, float, int, int]] = {}
    ofsetler, gecerli, ofsetle, sebepler, ekler = [], [], [], {}, []
    volt = None
    for sat, (tur, bilgi) in zip(avr, p.beklenen):
        q = sat.split()
        if tur == "K":
            kararlar[bilgi[0]] = (int(q[1]), cozf(q[2]), cozf(q[3]), cozf(q[4]), cozf(q[5]), int(q[6]),
                                  int(q[7]), bilgi)
        elif tur == "O":
            ofsetler.append((bilgi, cozf(q[1]), q[1]))
        elif tur == "V":
            volt = (bilgi, cozf(q[1]))
        elif tur == "G":
            gecerli.append((bilgi, int(q[1])))
        elif tur == "F":
            ofsetle.append((bilgi, [cozf(h) for h in q[1:5]]))
        elif tur == "S":
            sebepler[bilgi] = sat[2:]
        elif tur == "E":
            ekler.append((bilgi, int(q[1])))

    print("\n--- 2. Bilinen kod ortalamasindan dogru volt --------------------------")
    e, ort, sac, kay, sif, yak, n, b = kararlar["BILINEN"]
    ist = bekle_istat(b[1])
    ok("Ortalama kod 2200.5 (2200/2201 almasik), saçılma 0.5 kod, kayma 0",
       ort == 2200.5 and bit(sac) == bit(f32(ist["sac"] * KOD_V)) and abs(sac / KOD_V - 0.5) < 1e-4 and kay == 0.0,
       f"ort {ort} sac {sac / KOD_V:.4f} kod kayma {kay}")
    ok("[!] Kullanici sifiri = mv / 1000 * oran - fabrika (float32, bit bit)",
       e == TAMAM and bit(sif) == bit(bekle_volt(b[2], ORAN, FAB)),
       f"sebep {e}, {sif:+.6f} V = {b[2]} mV x {ORAN:.6f} / 1000 - {FAB:.6f}")
    ok("10 yakalama, 1000 ornek sayildi", (yak, n) == (10, 1000), f"{yak} / {n}")
    ok("skop_sifir_volt (V komutu) ayni formul", volt is not None and bit(volt[1]) == bit(bekle_volt(volt[0], ORAN, FAB)))
    e, *_r = kararlar["FABRIKA"]
    ok("Fabrika donusumu 0 V gosteriyorsa kullanici sifiri ~0 (< 0.1 mV)",
       e == TAMAM and abs(kararlar["FABRIKA"][4]) < 1e-4, f"{kararlar['FABRIKA'][4]:+.7f} V")

    print("\n--- 3. Ret: fabrika degerinden +-6 V, eksik yakalama ------------------")
    for ad in ("SINIR+", "SINIR-", "SINIR_KENAR", "NAN"):
        e, _o, _s, _k, sif, *_ = kararlar[ad]
        ok(f"{ad}: E_SINIR, sifir YAZILMADI (0)", e == E_SINIR and sif == 0.0, f"sebep {e}, sifir {sif}")
    e, _o, _s, _k, sif, *_ = kararlar["SINIR_ICI"]
    ok("+5.9 V kabul (sinirin ici)", e == TAMAM and abs(sif - 5.9) < 1e-3, f"{sif:+.5f}")
    e, *_x = kararlar["AZ"]
    ok("9 yakalama: E_AZ", e == E_AZ and kararlar["AZ"][5] == 9, f"sebep {e}, yakalama {kararlar['AZ'][5]}")
    bos = [x for x in ekler if x[0] == "BOS"]
    ok("Bos yakalama EKLENMEZ (0 doner), yine E_AZ", bos == [("BOS", 0)] and kararlar["AZ_BOS"][0] == E_AZ
       and kararlar["AZ_BOS"][5] == 9, f"{bos}")

    print("\n--- 4. Ret: saçılma ve kayma (giris kisa devre degil) -----------------")
    for ad, bek in (("SACILMA", E_SACILMA), ("KARE5V", E_SACILMA), ("KAYMA", E_KAYMA)):
        e, _o, sac, kay, sif, *_ = kararlar[ad]
        ok(f"{ad}: sebep {bek}, sifir yazilmadi", e == bek and sif == 0.0,
           f"sebep {e}, saçılma {sac:.3f} V, kayma {kay:.3f} V")
    e, _o, sac, kay, *_ = kararlar["KAYMA"]
    ok("Kayma reddi saçılmadan bagimsiz: KAYMA'da saçılma esigin ALTINDA", sac <= SACILMA and kay > KAYMA,
       f"saçılma {sac:.3f} V, kayma {kay:.3f} V")

    print("\n--- 5. Kartta olculen kisa devre gurultusu KABUL ----------------------")
    for ad in ("KISA_SUZGECLI", "KISA_HAM", "KISA_USBSIZ"):
        e, ort, sac, kay, sif, yak, n, b = kararlar[ad]
        ist = bekle_istat(b[1])
        ok(f"{ad}: TAMAM; ort / saçılma C = float32 basvurusu (bit bit)",
           e == TAMAM and bit(ort) == bit(ist["ort"]) and bit(sac) == bit(f32(ist["sac"] * KOD_V))
           and bit(kay) == bit(f32(f32(ist["ort_cok"] - ist["ort_az"]) * KOD_V)),
           f"saçılma {sac:.3f} V (esik {SACILMA}), kayma {kay:.3f} V (esik {KAYMA}), {n} ornek")
    e, ort, sac, *_ = kararlar["KISA_HAM"]
    ok("Ham kipte (tepe-tepe 2-4 V, igneli) saçılma esigin en az %33 altinda (< 0.8 V)",
       sac < 0.8, f"{sac:.3f} V")

    print("\n--- 6. tz0 = fabrika; NVS'ten bozuk deger fabrika ---------------------")
    ok("[!] Toplam ofset kul = 0'da fabrika degerinin KENDISI (bit bit) — tz0 sonrasi eski davranis",
       ofsetler[0][2] == bit(FAB), f"{ofsetler[0][2]} = {bit(FAB)}")
    ok("Toplam ofset = fabrika + kullanici (float32)",
       all(bit(o) == bit(f32(FAB + k)) for k, o, _h in ofsetler), str([round(o, 6) for _k, o, _h in ofsetler]))
    ok("NVS'ten okunan deger: sonlu ve |x| <= 6 V gecerli; 6.0001, -7, NaN, +-inf GECERSIZ (fabrika)",
       all(b == g for b, g in gecerli), str(gecerli))

    print("\n--- 7. skop_ofsetle aritmetigi ve ret metinleri ----------------------")
    ok("Vmax / Vmin / Vort ofset kadar kayar, Vrms = sqrtf(Vac^2 + Vort^2) (float32, bit bit)",
       all(bit(r[0]) == bit(f32(mx - of)) and bit(r[1]) == bit(f32(mn - of)) and bit(r[2]) == bit(f32(av - of))
           and bit(r[3]) == bit(f32(math.sqrt(f32(f32(ac * ac) + f32(f32(av - of) * f32(av - of))))))
           for (mx, mn, av, ac, of), r in ofsetle))
    ok("Ret metinleri dolu ve birbirinden farkli; giris kaynakli olanlar 'kisa devre degil' diyor",
       len(set(sebepler.values())) == 6 and all(sebepler[k] for k in sebepler)
       and all("kisa devre degil" in sebepler[k] for k in (E_SINIR, E_SACILMA, E_KAYMA)),
       " | ".join(sebepler[k][:28] for k in sorted(sebepler)))

    firmware()
    print(f"\n  SONUC: {gecti} gecti, {kaldi} kaldi")
    return 0 if kaldi == 0 else 1


# ── 2. firmware kaynak denetimi ─────────────────────────────────────────
def govde(kaynak: str, imza: str) -> str:
    """`imza` ile baslayan fonksiyonun govdesi (ilk { ile eslesen })."""
    i = kaynak.find(imza)
    if i < 0:
        return ""
    j = kaynak.find("{", i)
    d = 0
    for k in range(j, len(kaynak)):
        if kaynak[k] == "{":
            d += 1
        elif kaynak[k] == "}":
            d -= 1
            if d == 0:
                return kaynak[j:k + 1]
    return ""


def yorumsuz(s: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", s, flags=re.S)


def tdiv_us(ham: str, ad: str) -> int:
    """SKOP_TDIV_US[<ad>] — dizi ve indis kaynaktan (C++'ta static_assert edilemiyor: dizi constexpr degil)."""
    d = re.search(r"SKOP_TDIV_US\[\]\s*=\s*\{([^}]*)\}", ham)
    i = re.search(r"static const uint8_t\s+" + ad + r"\s*=\s*(\d+)", ham)
    if not d or not i:
        return -1
    dizi = [int(x) for x in re.findall(r"\d+", d.group(1))]
    return dizi[int(i.group(1))] if int(i.group(1)) < len(dizi) else -1


def firmware() -> None:
    print("\n--- 8. Firmware kaynak denetimi (.ino) -------------------------------")
    ino = yorumsuz(INO.read_text(encoding="utf-8"))
    ham = INO.read_text(encoding="utf-8")
    esp = (BASLIK_DIZIN / "kayit_esp.h").read_text(encoding="utf-8")
    ok("skop_sifir.h .ino'ya dahil", '#include "skop_sifir.h"' in ham)
    of = govde(ino, "static float skop_volt_ofset()")
    ok("[!] TEK KAYNAK: skop_volt_ofset() = skop_sifir_ofset(fabrika, kullanici sifiri)",
       "skop_sifir_ofset(skop_fabrika_ofset(), skop_kul_sifir)" in of, of.strip()[:90])
    ok("[!] SKOP_VOLT_OFSET .ino'da YALNIZ skop_fabrika_ofset()'te (baska yer fabrika degerini dogrudan kullanmaz)",
       ino.count("SKOP_VOLT_OFSET") == 1 and "SKOP_VOLT_OFSET" in govde(ino, "static float skop_fabrika_ofset()"),
       f"{ino.count('SKOP_VOLT_OFSET')} kullanim")
    so = govde(ino, "static void skop_ofsetle(SkopOlcum *m)")
    ok("[!] skop_ofsetle (M satiri Vmax/Vmin/Vort/Vrms) skop_volt_ofset() ile, aritmetik cekirdekte",
       "skop_sifir_ofsetle(" in so and "skop_volt_ofset()" in so, so.strip()[:120])
    ct = govde(ino, "    case 'C': {")
    ok("[!] CT ofset= skop_volt_ofset() (panel ekseni / JS kodVolt bundan) + sifir= alani",
       re.search(r'F\(" ofset="\)\);\s*Serial\.print\(skop_volt_ofset\(\), 6\)', ct) is not None
       and 'F(" sifir=")' in ct, "")
    ok("S2 basligi, /skop.bin ve skop_otomatik ayni kaynaktan (skop_volt_ofset())",
       ino.count("skop_volt_ofset()") >= 6, f"{ino.count('skop_volt_ofset()')} kullanim")
    gs = govde(ino, "static void skop_gunluk_sonuc(uint8_t sonuc)")
    ok("[!] (e) skop gunlugu: her yakalamanin META ofseti skop_volt_ofset() — kullanici sifiri DAHIL "
       "(eski kayitlar kendi META'siyla cozulur)", "y->meta.ofset = skop_volt_ofset();" in gs)
    sk = govde(ino, "void skop_komut(const char *s)")
    tz = govde(ino, "static void skop_sifir_komut(const char *s)")
    ok("tz ailesi skop_komut'ta, MESGUL denetimlerinden ONCE (tz? her zaman okunur)",
       0 <= sk.find("skop_sifir_komut(s)") < sk.find("skop_is != SKOP_IS_YOK") and bool(tz))
    ok("[!] tz suruyorken baska skop komutu (ayar, yakalama) REDDEDILIR",
       re.search(r"skop_sifir_is\.aktif[^;]*\)\s*\{\s*Serial\.println\(F\(\"! skop: sifirlama suruyor", sk)
       is not None)
    for ad, desen in (("pil testi", r"pil_testi_suruyor\(\)"), ("skop gunlugu", r"skop_gunluk\.aktif"),
                      ("baska yakalama", r"skop_is != SKOP_IS_YOK"), ("dokum", r"skop_dokum\.aktif"),
                      ("tz zaten", r"skop_sifir_is\.aktif")):
        m = re.search(desen + r"[^;{]*\)\s*\{?\s*Serial\.println\(F\(\"! tz:", tz)
        ok(f"[!] Ret (komut dalinda): {ad} -> `! tz: ...`, hicbir sey yazilmaz", m is not None)
    bt = govde(ino, "static void skop_sifir_bitir(")
    ok("[!] tz kullanicinin skop ayarlarini AYNEN geri yukler (bitir'de, basari / ret / iptal tek yol)",
       "skop_ayar = skop_sifir_is.eski;" in bt and "skop_sifir_is.aktif = 0" in bt)
    isle = govde(ino, "static void skop_sifir_isle()")
    ok("Yakalamalar arasi: pil testi / gunluk baslarsa IPTAL (bitir), yakalama ayri gorevde (SKOP_IS_SIFIR)",
       "pil_testi_suruyor()" in isle and "skop_gunluk.aktif" in isle and "skop_sifir_bitir(" in isle
       and "skop_is_ver(SKOP_IS_SIFIR)" in isle)
    bas = govde(ino, "static void skop_sifir_baslat()")
    ok("tz yakalamasi zaman tabanindan BAGIMSIZ, tetiklemesiz: oto, esik 0, 10 ms/bol, suzgecli",
       all(x in bas for x in ("skop_sifir_is.eski = skop_ayar;", "skop_ayar.kip = SKOP_KIP_OTO;",
                              "skop_ayar.esik = 0u;", "skop_ayar.tdiv = SKOP_SIFIR_TDIV;",
                              "skop_ayar.suzgec = 1u;")) and tdiv_us(ham, "SKOP_SIFIR_TDIV") == 10000,
       f"SKOP_TDIV_US[SKOP_SIFIR_TDIV] = {tdiv_us(ham, 'SKOP_SIFIR_TDIV')} us")
    ok("tz sirasinda kart 'sifirlaniyor' satiri basar (panel bekleme gosterir)",
       '"* tz: sifirlaniyor' in bas)
    yk = govde(ino, "static uint8_t skop_yakala()")
    ok("tz yakalamasi pencere dolunca BITER (tetik beklemez: OTO zaman asimi 300 ms + 1.2 pencere yok)",
       "const bool hemen = (skop_is == SKOP_IS_SIFIR);" in yk and yk.count("hemen && dolu >= n") >= 2)
    gv = govde(ino, "static void skop_gorevi(void *)")
    ok("Gorev SKOP_IS_SIFIR'i yakalar; olcum (skop_dokum_m) tz yakalamasinda HESAPLANMAZ",
       "is == SKOP_IS_SIFIR" in gv and "is != SKOP_IS_SIFIR" in gv)
    nv = govde(ino, "static bool skop_sifir_yaz(")
    ok("[!] NVS ayri ad alani `skopayar` / `sifir` (kalibrasyon gecmisine GIRMEZ: kalgec yok)",
       '#define SKOP_NVS "skopayar"' in ham and 'putFloat("sifir"' in nv and "kalgec" not in nv
       and "ayar_kaydet" not in nv)
    yu = govde(ino, "static void skop_sifir_yukle()")
    ok("Acilista NVS'ten: bozuk / sinir disi deger fabrika (skop_sifir_gecerli)", "skop_sifir_gecerli(" in yu
       and "skop_sifir_yukle();" in ino)
    ok("Hesap cekirdekte: ortalama -> eFuse egrisi (kal_mv) -> skop_sifir_karar",
       "skop_sifir_karar(" in bt and "kal_mv(" in bt)
    ok("`?` ayar dokumunde ve `tz?`de TZ satiri", "skop_sifir_durum_yaz();" in govde(ino, "void ayar_yaz_seri()")
       and re.search(r"s\[2\] == '\?' && s\[3\] == 0\) \{ skop_sifir_durum_yaz\(\); return; \}", tz) is not None)
    kg = govde(ino, "static void kayit_skop_komut(const char *s)")
    ok("Skop gunlugu tz surerken BASLAMAZ (`! G:`)", "skop_sifir_is.aktif" in kg)
    ok("Firmware surumu A3-SK3", re.search(r'#define KAYIT_FW_SURUM\s+"A3-SK3"', esp) is not None)
    ok("Yardim satiri tz / tz0 / tz?", "tz sifirla" in ham and "tz0" in ham)


if __name__ == "__main__":
    sys.exit(main())
