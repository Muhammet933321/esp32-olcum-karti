# -*- coding: utf-8 -*-
"""A4 — Asama 2 kartinin UCTAN UCA dogrulanmasi.

Zincir:
  uygulanan V ve I
    -> ngspice            (gercek bolucu + kelepce, gercek sont)
    -> ADS1115 modeli     (veri sayfasi: kod = V / (PGA/32768))
    -> GERCEK DONUSUM KODU (kod/olcum-karti-a2/olcum2.h, avr-gcc ile
                            derlenip 39/39 dogrulanmis emulatorde kosuyor)
    -> protokol satiri
    -> GERCEK ARAYUZ      (arayuz/app.js ayristiricisi, node ile)

NEDEN AVR: ESP32-S3'u komut komut calistiran emulatorumuz yok. olcum2.h
hicbir platform cagrisi icermedigi, `int` ve `double` kullanmadigi icin
iki mimaride de ayni IEEE-754 sonucu verir. Ayrica ayni kaynagin gercek
ESP32-S3 derleyicisiyle derlendigi de ayrica sinaniyor.

KAPSAM DISI: gercek lehim/temas direnci, gercek gurultu, ADS1115'in kendi
ofset/kazanc hatasi, ESP32 ADC'sinin dogrusalsizligi. Bunlar tezgahta
olculur; test sonunda o liste basilir.
"""
from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import spice                                        # noqa: E402
import hedef2                                       # noqa: E402
from avr import elf, mega328                        # noqa: E402
from avr.cekirdek import Cekirdek                   # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOD = BURASI.parent / "arsiv" / "asama2" / "olcum-karti-a2"
CIKTI = BURASI.parent / "arsiv" / "asama2" / "kanit"
AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"
ARDUINO_CLI = BURASI.parents[2] / ".araclar" / "arduino-cli.exe"

f32 = np.float32

# --- tasarim sabitleri (tasarim2.py ile ayni)
R_UST, R_ALT = 100e3, 6.8e3
ORAN = f32((R_UST + R_ALT) / R_ALT)
PGA_V, PGA_I = 2.048, 0.256
ADS_SAYIM = 32768
TL431_V = 2.495

D1N4148 = (".model D1N4148 D(IS=4.352E-9 N=1.906 BV=110 IBV=1E-4 RS=0.6458 "
           "CJO=7.048E-13 VJ=0.869 M=0.03 FC=0.5 TT=3.48E-9)")


class Rapor:
    def __init__(self):
        self.gecti = self.kaldi = 0

    def bilgi(self, s=""):
        print(s)

    def kosul(self, ad, tamam, ek=""):
        self.gecti += bool(tamam)
        self.kaldi += not tamam
        print(f"  {'[OK]' if tamam else '[!!]'} {ad}" + (f"  {ek}" if ek else ""))
        return tamam


def bit(x) -> str:
    return f"{struct.unpack('<I', struct.pack('<f', f32(x)))[0]:08x}"


# ═══════════════════════════════════════════ 1. ngspice: analog kat
def bolucu_tablosu():
    net = f"""* Asama 2 gerilim girisi (secenek D)
{D1N4148}
V33 v33 0 DC 3.3
Rbias v33 tlray 220
BTL431 tlray 0 I = max(0, (V(tlray)-{TL431_V})/0.2)
Ctl tlray 0 100n
Vin giris 0 DC 0
Rust giris dugum {R_UST}
Ralt dugum 0 {R_ALT}
Cf dugum 0 1n
Dklm dugum tlray D1N4148
Dalt 0 dugum D1N4148
.control
dc Vin 0 35 0.0175
wrdata dc.txt v(dugum)
.endc
.end
"""
    _, d = spice.kos(net, BURASI / "_a4_v")
    veri = spice.degerler(d / "dc.txt")
    return np.array([s[0] for s in veri]), np.array([s[1] for s in veri])


def sont_tablosu(sont: float, imaks: float):
    """Sont + diferansiyel RC. ADS girisi 710 kohm."""
    net = f"""* sont + Kelvin algilama + diferansiyel RC
Iyuk 0 sontust DC 0
Rsont sontust 0 {sont}
Rsa sontust p 100
Rsb 0 n 100
Cd p n 100n
Rads p n 710k
.control
dc Iyuk 0 {imaks} {imaks/2000}
wrdata dc.txt v(p,n)
.endc
.end
"""
    _, d = spice.kos(net, BURASI / "_a4_i")
    veri = spice.degerler(d / "dc.txt")
    return np.array([s[0] for s in veri]), np.array([s[1] for s in veri])


def ads_kod(volt: float, pga: float) -> int:
    """ADS1115 veri sayfasi: delta-sigma, tam olcek +-PGA, 32768 sayim."""
    k = int(round(volt / pga * ADS_SAYIM))
    return max(-32768, min(32767, k))


# ═══════════════════════════════════════════ 2. vektor.h uret
def vektor_yaz(vektorler, yol: Path):
    satirlar = ["/* Python tarafindan uretildi — sim2_kart.py */",
                "#ifndef VEKTOR_H", "#define VEKTOR_H", "#include <stdint.h>",
                "typedef struct {", "    int16_t ham_v;", "    int16_t ham_i;",
                "    int16_t i_ofset;", "    float   sont;", "    float   v_pga;",
                "    float   i_pga;", "    uint32_t dt_us;", "} Vektor;", "",
                f"#define VEKTOR_ADET {len(vektorler)}",
                "static const Vektor VEKTOR[VEKTOR_ADET] = {"]
    for v in vektorler:
        satirlar.append(
            f"    {{ {v['ham_v']}, {v['ham_i']}, {v['i_ofset']}, "
            f"{v['sont']:.6f}f, {v['v_pga']:.6f}f, {v['i_pga']:.6f}f, "
            f"{v['dt_us']}u }},")
    # Arayuz testi icin SABIT calisma noktasi (12 V / 100 mA)
    sabit = vektorler[2]
    satirlar += [
        "};",
        "",
        "/* Arayuz testi icin sabit calisma noktasi (12.00 V / 100.0 mA) */",
        f"#define SABIT_HAM_V {sabit['ham_v']}",
        f"#define SABIT_HAM_I {sabit['ham_i']}",
        f"#define SABIT_SONT  {sabit['sont']:.6f}f",
        f"#define SABIT_V_PGA {sabit['v_pga']:.6f}f",
        f"#define SABIT_I_PGA {sabit['i_pga']:.6f}f",
        "#endif", ""]
    yol.write_text("\n".join(satirlar), encoding="utf-8")


# ═══════════════════════════════════════════ 3. bagimsiz hesap (numpy f32)
def beklenen(v):
    ham_v, ham_i = f32(v["ham_v"]), f32(v["ham_i"] - v["i_ofset"])
    volt = f32(f32(ham_v * f32(v["v_pga"] / ADS_SAYIM)) * ORAN)
    amper = f32(f32(ham_i * f32(v["i_pga"] / ADS_SAYIM)) / f32(v["sont"]))
    if amper < 0:
        amper = f32(0.0)
    return volt, amper, f32(volt * amper)


def main() -> int:
    r = Rapor()
    t0 = time.time()
    CIKTI.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("  A4 — ASAMA 2 UCTAN UCA")
    print("=" * 78)

    # ---------------------------------------------------- 1. analog kat
    print("\n--- 1. Analog kati ngspice ile tara -------------------------------")
    vx, vy = bolucu_tablosu()
    oran_olculen = vx[-1] / vy[-1]
    r.kosul("Bolucu orani ngspice'tan", abs(oran_olculen / float(ORAN) - 1) < 0.01,
            f"{oran_olculen:.3f} (tasarim {float(ORAN):.3f})")
    ix, iy = sont_tablosu(1.0, 0.256)
    egim = (iy[-1] - iy[len(iy) // 2]) / (ix[-1] - ix[len(ix) // 2])
    r.kosul("Sont + RC suzgeci egimi 1 ohm'a esit",
            abs(egim / 1.0 - 1) < 0.001, f"{egim:.6f} ohm")

    # ---------------------------------------------------- 2. vektorler
    print("\n--- 2. Uygulanan degerleri ADS1115 koduna cevir --------------------")
    noktalar = [(3.30, 0.0100), (5.00, 0.0500), (12.00, 0.1000),
                (24.00, 0.2000), (30.00, 0.2500)]
    vektorler = []
    print(f"  {'V uyg':>7} {'dugum':>9} {'kod_v':>7} | "
          f"{'I uyg':>8} {'sont mV':>9} {'kod_i':>7}")
    print("  " + "-" * 60)
    for vu, iu in noktalar:
        dugum = float(np.interp(vu, vx, vy))
        vsont = float(np.interp(iu, ix, iy))
        kv, ki = ads_kod(dugum, PGA_V), ads_kod(vsont, PGA_I)
        vektorler.append(dict(ham_v=kv, ham_i=ki, i_ofset=0, sont=1.0,
                              v_pga=PGA_V, i_pga=PGA_I, dt_us=1163,
                              v_uyg=vu, i_uyg=iu))
        print(f"  {vu:7.2f} {dugum:9.5f} {kv:7d} | "
              f"{iu:8.4f} {vsont*1000:9.4f} {ki:7d}")

    vektor_yaz(vektorler, BURASI / "avr" / "vektor.h")

    # ---------------------------------------------------- 3. AVR'de kostur
    print("\n--- 3. GERCEK donusum kodunu AVR'de kostur ------------------------")
    elf_yol = BURASI / "_a4_olcum2.elf"
    d = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os",
         "-std=gnu99", "-Wall", f"-I{KOD}", f"-I{BURASI / 'avr'}",
         "-o", str(elf_yol), str(BURASI / "avr" / "ornek_olcum2.c"), "-lm"],
        capture_output=True, text=True, timeout=300)
    if d.returncode != 0:
        print("avr-gcc derleyemedi:\n" + d.stderr)
        return 1
    uyari = [s for s in d.stderr.splitlines() if "warning:" in s]
    r.kosul("olcum2.h AVR'de uyarisiz derlendi", not uyari,
            f"{len(uyari)} uyari" if uyari else "0 uyari")

    flash, _ = elf.flash_goruntusu(elf_yol)
    kart = mega328.Kart(flash, Cekirdek)
    kart.cevrim_kadar_kos(60_000_000)
    cikti = kart.tx.decode("ascii", "replace")
    r.kosul("Program tamamlandi", "BITTI" in cikti,
            f"{kart.cpu.cevrim:,} cevrim".replace(",", " "))

    # ---------------------------------------------------- 4. bit birebir
    print("\n--- 4. Her deger BIT BIREBIR karsilastiriliyor --------------------")
    satirlar = [s for s in cikti.splitlines() if s.startswith("V ")]
    r.kosul(f"{len(vektorler)} olcum satiri geldi", len(satirlar) == len(vektorler),
            f"{len(satirlar)} satir")
    print()
    print(f"  {'nokta':>10} {'volt (AVR)':>12} {'volt (numpy)':>13} "
          f"{'amper':>10} {'watt':>10}")
    print("  " + "-" * 62)
    tum_tamam = True
    for k, (s, v) in enumerate(zip(satirlar, vektorler)):
        p = s.split()
        avr = {p[0]: p[1], p[2]: p[3], p[4]: p[5]}
        bv, bi, bw = beklenen(v)
        esit = (avr["V"] == bit(bv) and avr["I"] == bit(bi)
                and avr["W"] == bit(bw))
        tum_tamam &= esit
        print(f"  {v['v_uyg']:6.2f} V   {avr['V']:>12} {bit(bv):>13} "
              f"{'OK' if avr['I'] == bit(bi) else 'FARK':>10} "
              f"{'OK' if avr['W'] == bit(bw) else 'FARK':>10}")
    r.kosul("Tum donusumler bit birebir tuttu", tum_tamam)

    # --- enerji
    me = re.search(r"^E ([0-9a-f]{16}) J ([0-9a-f]{8}) H ([0-9a-f]{8})$",
                   cikti, re.M)
    r.kosul("Enerji satiri geldi", me is not None)
    if me:
        pJ = int(me.group(1), 16)
        bek = 0
        for v in vektorler:
            _, _, w = beklenen(v)
            guc_uW = int(f32(w) * f32(1e6)) if w > 0 else 0
            bek += guc_uW * v["dt_us"]
        r.kosul("uint64 pJ birikimi birebir", pJ == bek,
                f"{pJ:,} pJ".replace(",", " "))
        r.kosul("Joule donusumu birebir", me.group(2) == bit(np.float64(pJ) / 1e12),
                f"{np.float64(pJ)/1e12:.6f} J")
        # Wh: Asama 1'de 3.6e18 yaziliydi (1 kWh), 3.6e15 olmali
        wh_dogru = bit(np.float64(pJ) / 3.6e15)
        wh_yanlis = bit(np.float64(pJ) / 3.6e18)
        r.kosul("Wh donusumu DOGRU sabitle (3.6e15, 3.6e18 DEGIL)",
                me.group(3) == wh_dogru and me.group(3) != wh_yanlis,
                f"{np.float64(pJ)/3.6e15:.9f} Wh")

    # --- PGA otomatik kademe
    mp = re.search(r"^P ((?:[0-9a-f]{8} ?){5})$", cikti, re.M)
    r.kosul("PGA kademe satiri geldi", mp is not None)
    if mp:
        alinan = mp.group(1).split()
        bekleniyor = []
        for dugum in (2.00, 1.00, 0.40, 0.20, 0.05):
            m = abs(dugum)
            p = (2.048 if m > 0.9 * 1.024 else 1.024 if m > 0.9 * 0.512
                 else 0.512 if m > 0.9 * 0.256 else 0.256)
            bekleniyor.append(bit(p))
        r.kosul("Otomatik kademe secimi birebir", alinan == bekleniyor,
                " ".join(f"{v:.3f}" for v in (2.048, 1.024, 0.512, 0.256, 0.256)))

    # --- tam olcek ve adim
    for harf, fn, ad in (("F", lambda p: f32(f32(p) * ORAN), "tam olcek"),
                         ("A", lambda p: f32(f32(p / ADS_SAYIM) * ORAN), "adim")):
        m = re.search(rf"^{harf} ((?:[0-9a-f]{{8}} ?){{4}})$", cikti, re.M)
        if m:
            alinan = m.group(1).split()
            bek = [bit(fn(p)) for p in (2.048, 1.024, 0.512, 0.256)]
            r.kosul(f"Kademe {ad} degerleri birebir", alinan == bek,
                    " / ".join(f"{float(fn(p)):.4f}" for p in
                               (2.048, 1.024, 0.512, 0.256)))
        else:
            r.kosul(f"Kademe {ad} satiri geldi", False)

    # ---------------------------------------------------- 5. arayuze ver
    print("\n--- 5. Protokol satirini GERCEK arayuze ver -----------------------")
    # IKI satir gerekiyor: arayuz ornekleme hizini iki raporun zaman
    # damgasi FARKINDAN cikariyor, tek satirla hesaplayamaz.
    d_satirlari = re.findall(r"^D .*$", cikti, re.M)
    r.kosul("Sabit noktadan IKI protokol satiri uretildi",
            len(d_satirlari) == 2, " | ".join(d_satirlari))
    md = d_satirlari[-1] if d_satirlari else None
    if md:
        akis = "\n".join(d_satirlari) + "\n"
        (CIKTI / "a2-seri-akis.txt").write_text(akis, encoding="utf-8")
        alanlar = md.split()
        ui = subprocess.run(
            ["node", "test_arayuz_akis.js", str(CIKTI / "a2-seri-akis.txt"),
             f"{float(alanlar[1])}", f"{float(alanlar[2])}"],
            cwd=BURASI, capture_output=True, timeout=300)
        metin = (ui.stdout or ui.stderr).decode("utf-8", "replace").strip()
        print("  " + metin.replace("\n", "\n  "))
        r.kosul("Arayuz zincirin sonunu dogruladi", ui.returncode == 0)

    # ---------------------------------------------------- 6. ESP32 derleme
    print("\n--- 6. AYNI kaynak gercek ESP32-S3 derleyicisiyle -----------------")
    e = subprocess.run(
        [str(ARDUINO_CLI), "compile", "--fqbn", hedef2.FQBN,
         "--warnings", "all", str(KOD)],
        capture_output=True, text=True, timeout=900)
    uyari = [s for s in (e.stdout + e.stderr).splitlines() if "warning:" in s]
    mf = re.search(r"Sketch uses (\d+) bytes \((\d+)%\)", e.stdout)
    mr = re.search(r"Global variables use (\d+) bytes \((\d+)%\)", e.stdout)
    r.kosul("ESP32-S3 icin derlendi", e.returncode == 0,
            f"flash {mf.group(1)} B (%{mf.group(2)}), "
            f"RAM {mr.group(1)} B (%{mr.group(2)})" if mf and mr else "")
    r.kosul("ESP32-S3 derlemesi uyarisiz", not uyari,
            f"{len(uyari)} uyari" if uyari else "0 uyari")

    # ---------------------------------------------------- ozet
    print("\n" + "=" * 78)
    print(f"  A4: {r.gecti}/{r.gecti + r.kaldi} kosul gecti   ({time.time()-t0:.1f} s)")
    print("=" * 78)
    print()
    print("  BU TEST KANITLAMAZ (tezgahta olculmeli):")
    print("    * ADS1115'in kendi ofset (+-3 LSB) ve kazanc (%0.15) hatasi")
    print("    * lehim/temas direnci — 15 mohm kademesinde Kelvin sart")
    print("    * gercek gurultu, sicaklik suruklenmesi")
    print("    * ESP32-S3 ADC'sinin dogrusalsizligi (osiloskop kanali)")
    print("    * direnc toleranslari (%1 metal film varsayildi)")

    import shutil
    for d2 in BURASI.glob("_a4_*"):
        if d2.is_dir():
            shutil.rmtree(d2, ignore_errors=True)
    return 0 if r.kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
