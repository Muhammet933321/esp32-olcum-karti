# -*- coding: utf-8 -*-
"""A6 — Osiloskop olcum matematiginin AVR emulatorunde dogrulanmasi.

    python test_skop_olcum.py

`skop_olc()` fonksiyonu `kod/olcum-karti-a2/olcum2.h` icinde ve PLATFORM
BAGIMSIZ yazildi. Burada GERCEK KOD, avr-gcc ile derlenip 39/39 bit-birebir
dogrulanmis AVR emulatorunde (test_avr.py) kosturuluyor.

Beklenen degerler bir YENIDEN-UYGULAMADAN gelmiyor: sentetik dalgalarin
frekansi, genligi ve duty'si ANALITIK OLARAK biliniyor.

    kare   periyot 80 ornek @ 10 kSa/s -> 125.00 Hz, %50 duty
    ucgen  periyot 100 ornek           -> 100.00 Hz, %50 duty
    sinus  periyot 64 ornek            -> 156.25 Hz, %50 duty
    duz    olcum yapilamaz             -> hepsi 0
    %25    periyot 80, 20 ornek ustte  -> 125.00 Hz, %25 duty
  1F (2026-10-02) kusurlarinin TAM degerli capalari:
    S3 kare / %25        -> duty TAM 50.0 / 25.0 (eskiden 120/241, 60/241)
    S1 duz 2048 / 4000   -> Vac TAM 0 (float32 kare farki sadelesmesi)
    S1 3000 + {-3..+3}   -> Vac TAM 2 kod (eskisi kaybediyordu)
    S4 cuce darbe + kenar -> tr = tf = TAM kenarin 8 ornegi (cuce disarida)
"""
from __future__ import annotations

import math
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr import mega328                          # noqa: E402
from avr.cekirdek import Cekirdek                # noqa: E402
from avr.elf import flash_goruntusu          # noqa: E402
import gecici                                   # noqa: E402

BURASI = Path(__file__).parent
KOK = BURASI.parent
AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"

gecti = kaldi = 0

# ornek_skop.c'nin bastigi dalgalar (satir basi)
DALGALAR = ("KARE", "UCGN", "SINS", "DUZ", "D25", "DZ40", "DZ33", "GRT", "CUCE")


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"  {ek}" if ek else ""))


def yakin(ad: str, olculen: float, beklenen: float, tol: float,
          birim: str = "") -> None:
    fark = abs(olculen - beklenen)
    ok(ad, fark <= tol,
       f"{olculen:.6g}{birim} ~ {beklenen:.6g}{birim} (fark {fark:.3g})")


def cozf(h: str) -> float:
    """32 bitlik hex bit desenini float'a cevirir."""
    return struct.unpack(">f", bytes.fromhex(h))[0]


def kostur() -> dict:
    """ornek_skop.c'yi derler, emulatorde kosturur, satirlari cozer."""
    gec_dizin = gecici.dizin("skopolc_")
    elf = gec_dizin / "ornek_skop.elf"
    d = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os",
         "-std=gnu11", "-Wall", "-Wextra",
         f"-I{KOK / 'arsiv' / 'asama2' / 'olcum-karti-a2'}",
         "-o", str(elf), str(BURASI / "avr" / "ornek_skop.c"), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if d.returncode != 0:
        print(d.stderr)
        raise SystemExit("avr-gcc derleyemedi")

    uyari = [x for x in d.stderr.splitlines() if "warning:" in x]
    ok("olcum2.h skop katmani AVR'de uyarisiz derlendi", not uyari,
       f"{len(uyari)} uyari")
    if uyari:
        for u in uyari[:5]:
            print("       " + u)

    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    kart.cevrim_kadar_kos(120_000_000)
    metin = kart.tx.decode("ascii", "replace")
    ok("Program tamamlandi (BITTI)", "BITTI" in metin,
       f"{kart.cpu.cevrim:,} cevrim".replace(",", " "))

    sonuc = {}
    for sat in metin.splitlines():
        p = sat.split()
        if len(p) >= 2 and p[0] == "VA":
            sonuc["VA"] = cozf(p[1])
        elif len(p) >= 24 and p[0] in DALGALAR:
            d2 = {}
            i = 1
            while i + 1 < len(p):
                anahtar, deger = p[i], p[i + 1]
                d2[anahtar] = (int(deger) if anahtar in ("cv", "n")
                               else cozf(deger))
                i += 2
            sonuc[p[0]] = d2
    return sonuc


# ── SK2 (2026-10-10): alt / ust DURUM seviyeleri ──────────────────────────────────────
# (c) "eski davranis": iki durumlu OLMAYAN dalgalarda (sinus, ucgen, DC) skop_olc'un ciktisi
# SK2'DEN ONCEKI C'nin ciktisiyla BIT BIT ayni. Asagidaki desenler o C'nin (A3-SK1) urettigi
# ortak/test/vektor/skop.json'dan DONDURULDU (f T Vpp Vmax Vmin Vort Vrms Vac duty tr tf, float32
# bit deseni, buyuk endian; son sayi n). Vektor dosyasi SK2 ile yeniden uretildi — bu liste degil.
SK2_ESKI = {
    "sinus64": "431c4000 3bd1b717 42acba0e 42cc4738 417c6951 426bd462 4284ca78 41f44776 424e4000 3af7fb71 3af7fb71 4",
    "ucgen": "42c80000 3c23d70a 42cf45aa 42dac989 40b83ded 42664d68 4281c7a3 41ef6ed6 424c0000 3b83126f 3b83126f 3",
    "duz": "00000000 00000000 00000000 426bd462 426bd462 426bd462 426bd462 00000000 00000000 00000000 00000000 0",
    "sinus_kesirli": "43536a7e 3b9afe36 42664d68 42acba0e 41e64d68 42664c2f 427467ef 41a3ac90 4247593a 3ab71219 3ab78693 13",
    "sinus_hz_kesirli": "43481782 3ba3c3ca 42cf45aa 42e08b78 410a2e71 426d403f 428b3dcc 4211d2f4 42485c41 3ac174b5 3ac1a05e 9",
    "sinus_gurultu": "42dc6dbd 3c14a7e3 4299705f 42c2600d 41a3beb7 426d2f75 4280632e 41c4bcd8 4245cb97 3b3378a7 3b3f4345 7",
    "kirpik": "4326aaab 3bc49ba6 42ebc5a5 42ebc5a5 00000000 426bcd03 429975d7 424476df 424eaaab 3a90d3ba 3a90d3bb 8",
    "sinus_4000": "447a01e9 3a83116e 42c6a2c3 42e1fbf4 415ac989 427d4d05 429053ba 420a6b52 42486899 399df805 399e9cf9 47",
    "duz_4095_4000": "00000000 00000000 00000000 42ebc5a5 42ebc5a5 42ebc5a5 42ebc5a5 00000000 00000000 00000000 00000000 0",
    "dc_ustu_kucuk_ac": "00000000 00000000 3e30e000 42ace646 42ac8dd6 42acbae4 42acbae7 3d6908e3 00000000 00000000 00000000 0",
    "sabit_65535": "00000000 00000000 00000000 44498526 44498526 44498527 44498527 00000000 00000000 00000000 00000000 0",
}
SK2_ALAN = ("f", "T", "Vpp", "Vmax", "Vmin", "Vort", "Vrms", "Vac", "duty", "tr", "tf")


def sk2() -> None:
    """SK2: gercek C (skop_olc.h) AVR emulatorunde, ortak_vektor_skop.py'nin dalgalariyla.

    Beklenenler ANALITIK (dalganin kurulus degerleri) — kartta gorulen iki kusurun tersi:
      (a) gurultu + igne Vpp'yi sisirmez (5 V kare 6.3 V okunuyordu); tr ve tf tutarli
      (b) alt seviyedeki TEK dip %10 esigini kaydirmaz (tf 3/20 yakalamada 63-123 us idi)
      (c) iki durumlu olmayan dalga (sinus / ucgen / DC) eski uc-deger davranisinda (bit bit)
      (d) %10 ve %90 doluluklu kare de iki durumlu sayilir (dar durum bandi elenmez)
    """
    import ortak_vektor_skop as OV                       # noqa: E402 (ayni dizin)
    print("\n--- 11. SK2: alt / ust DURUM seviyeleri (histogram) ---------------")
    flash = OV.derle()
    V = {v["ad"]: v for v in OV.vakalar()}
    R = {ad: OV.kostur(flash, V[ad]) for ad in V if ad.startswith("sk2_") or ad in SK2_ESKI}
    va = OV.VA_A3
    gen = 174 * va                                       # alt 10 / ust 184 kod

    for ad in ("sk2_kare_igneli", "sk2_kare_ham_igne", "sk2_kare10", "sk2_kare90"):
        r, hz = R[ad], V[ad]["hz"]
        yakin(f"SK2 (a/d) {ad}: Vpp = durum seviyeleri farki (5.009 V) +-%3", r["Vpp"], gen, 0.03 * gen, " V")
        ok(f"SK2 (a/d) {ad}: gercek tepe kaybolmaz — Vmax / Vmin uc ornekler (Vmax - Vmin >= Vpp)",
           r["Vmax"] - r["Vmin"] >= r["Vpp"], f"Vmax {r['Vmax']:.3f} Vmin {r['Vmin']:.3f} V")
        ok(f"SK2 (a/d) {ad}: yukselme VE dusme olculdu, ikisi de <= 3 ornek, farklari <= 1 ornek",
           0 < r["tr"] <= 3 / hz and 0 < r["tf"] <= 3 / hz and abs(r["tr"] - r["tf"]) <= 1 / hz,
           f"tr {r['tr'] * 1e6:.2f} us tf {r['tf'] * 1e6:.2f} us (ornek {1e6 / hz:.2f} us)")
    for ad in ("sk2_kare_igneli", "sk2_kare10", "sk2_kare90"):
        r = R[ad]
        yakin(f"SK2 (a/d) {ad}: frekans 1 kHz +-%0.5", r["f"], 83333.0 / 83.333, 5.0, " Hz")
    for ad, d in (("sk2_kare10", 10.0), ("sk2_kare90", 90.0), ("sk2_kare_igneli", 50.0)):
        yakin(f"SK2 (d) {ad}: doluluk %{d:.0f} +-1", R[ad]["duty"], d, 1.0, " %")

    r, hz = R["sk2_igne_tam"], V["sk2_igne_tam"]["hz"]
    ok("[!] SK2 (a) iki esigi birden gecen 1 / 2 ornekluk igne kenar sayilmaz: tr = tf = gercek rampa (3.1998 ornek)",
       abs(r["tr"] * hz - 3.1998) < 0.01 and abs(r["tf"] * hz - 3.1998) < 0.01,
       f"tr {r['tr'] * hz:.4f} tf {r['tf'] * hz:.4f} ornek")

    tf0, tf1 = R["sk2_rc_kare"]["tf"], R["sk2_rc_kare_dip"]["tf"]
    hz = V["sk2_rc_kare"]["hz"]
    ideal = 3.0 * math.log(9.0) / hz                     # tau ln 9
    yakin("SK2 (b) ustel kenar: tf = tau ln 9 (dip yok) +-%10", tf0, ideal, 0.1 * ideal, " s")
    yakin("SK2 (b) ustel kenar: tr = tau ln 9 +-%10", R["sk2_rc_kare"]["tr"], ideal, 0.1 * ideal, " s")
    ok("[!] SK2 (b) alt seviyedeki TEK dip (kod 0) tf'yi bozmaz: dipli tf, dipsizin %2'si icinde",
       tf0 > 0 and abs(tf1 - tf0) <= 0.02 * tf0, f"dipsiz {tf0 * 1e6:.1f} us, dipli {tf1 * 1e6:.1f} us")
    yakin("SK2 (b) dip %50 esigini (doluluk) de kaydirmaz: dipli doluluk dipsizinkiyle ayni +-0.2 puan",
          R["sk2_rc_kare_dip"]["duty"], R["sk2_rc_kare"]["duty"], 0.2, " %")
    yakin("SK2 (b) dip Vpp'yi de sisirmez (durum seviyeleri)", R["sk2_rc_kare_dip"]["Vpp"],
          R["sk2_rc_kare"]["Vpp"], 0.01 * R["sk2_rc_kare"]["Vpp"], " V")

    bozuk = []
    for ad, desen in SK2_ESKI.items():
        p = desen.split()
        eski = [struct.unpack(">f", bytes.fromhex(h))[0] for h in p[:11]]
        yeni = [R[ad][a] for a in SK2_ALAN]
        if any(struct.pack(">f", x) != struct.pack(">f", y) for x, y in zip(eski, yeni)) or R[ad]["n"] != int(p[11]):
            bozuk.append(ad)
    ok(f"[!] SK2 (c) iki durumlu OLMAYAN {len(SK2_ESKI)} dalga (sinus, ucgen, DC, kirpik sinus) SK2 oncesiyle BIT BIT ayni",
       not bozuk, ", ".join(bozuk) or ", ".join(SK2_ESKI))
    for ad in ("sk2_ucgen_gurultu", "sk2_dc_igne"):
        r = R[ad]
        ok(f"SK2 (c) {ad}: tek durum — Vpp uc ornek farki (Vmax - Vmin, float32'de ayni islem)",
           struct.pack(">f", r["Vpp"]) == struct.pack(">f", OV.f32(r["Vmax"] - r["Vmin"])),
           f"Vpp {r['Vpp']:.4f} Vmax-Vmin {r['Vmax'] - r['Vmin']:.4f}")


def main() -> int:
    print("=" * 78)
    print("  A6  OSILOSKOP OLCUM MATEMATIGI  (gercek kod, AVR emulatorunde)")
    print("=" * 78)
    print("\n--- 1. Derleme ve kosum -------------------------------------------")
    s = kostur()

    ok("Emulator tum dalgalari isledi",
       all(k in s for k in ("VA",) + DALGALAR),
       f"{len(s) - 1}/{len(DALGALAR)} dalga")
    if len(s) < len(DALGALAR) + 1:
        return 1

    # volt/adim: olcum2.h'deki SKOP_VOLT_ADIM
    va = s["VA"]
    print("\n--- 2. Volt/adim ---------------------------------------------------")
    beklenen_va = 3.10 / 4095.0 * 15.70588235
    yakin("SKOP_VOLT_ADIM olcum2.h ile ayni", va, beklenen_va, 1e-9, " V")
    yakin("Tam olcek 48.7 V (tasarim2.py ile ayni)", va * 4095, 48.7, 0.1, " V")

    print("\n--- 3. KARE dalga: 80 ornek periyot, 5 cevrim ----------------------")
    k = s["KARE"]
    yakin("Frekans = 10000/80", k["f"], 125.0, 0.05, " Hz")
    yakin("Periyot = 1/125", k["T"], 1.0 / 125.0, 1e-7, " s")
    yakin("Vpp = 3600 kod", k["pp"], 3600 * va, 1e-4, " V")
    yakin("Vmax = 3800 kod", k["mx"], 3800 * va, 1e-4, " V")
    yakin("Vmin = 200 kod", k["mn"], 200 * va, 1e-4, " V")
    yakin("Vort = 2000 kod (simetrik kare)", k["av"], 2000 * va, 1e-3, " V")
    yakin("Duty = %50", k["du"], 50.0, 1.5, " %")
    # 1F (S3): tam sayida periyotlu ideal karede gorev orani TAM %50 —
    # eskiden ilk kenarin oncesindeki ornek fazladan sayiliyordu: 120/241.
    ok("1F S3: Duty TAM %50.000 (eskiden %49.79 = 120/241)", k["du"] == 50.0,
       f"%{k['du']!r}")
    # 400 ornekte 5 periyot var ama yukselen kenarlar i = 0, 80, 160, 240, 320'de.
    # i=0'daki kenarin ONCESINDE ornek olmadigi icin algilanamaz -> 4 kesisim,
    # yani 3 tam cevrim. Periyot yine (320-80)/3 = 80 ornek, frekans tam 125 Hz.
    ok("Cevrim 3 (i=0'daki kenar oncesi ornek yok, algilanamaz)",
       k["cv"] == 3, f"{k['cv']}")
    # Kare dalgada RMS: sqrt((3800^2 + 200^2)/2) kod
    rms_kod = math.sqrt((3800 ** 2 + 200 ** 2) / 2)
    # 1F (S1): tam tamsayi toplamlar -> float32 yuvarlamasi duzeyinde (1e-5 V);
    # eski float32 toplamlar 400 ornekte ~1e-4 V kaciriyordu.
    yakin("Vrms = kare dalga RMS'i", k["rm"], rms_kod * va, 1e-5, " V")
    # AC RMS = tepe genligi = 1800 kod
    yakin("Vac = 1800 kod (AC bileseni)", k["ac"], 1800 * va, 1e-5, " V")

    print("\n--- 4. UCGEN dalga: 100 ornek periyot, 4 cevrim --------------------")
    u = s["UCGN"]
    yakin("Frekans = 10000/100", u["f"], 100.0, 0.05, " Hz")
    yakin("Vpp = 3600 kod", u["pp"], 3600 * va, 5e-3, " V")
    yakin("Duty = %50", u["du"], 50.0, 2.0, " %")
    # Ucgen AC RMS = genlik/sqrt(3) = 1800/1.732
    yakin("Vac = ucgen RMS'i (genlik/√3)", u["ac"], 1800 / math.sqrt(3) * va,
          0.02, " V")

    print("\n--- 5. SINUS: 64 ornek periyot, 6 cevrim ---------------------------")
    n = s["SINS"]
    yakin("Frekans = 10000/64", n["f"], 156.25, 0.1, " Hz")
    yakin("Vpp = 3000 kod", n["pp"], 3000 * va, 0.02, " V")
    yakin("Vort = 2048 kod (merkez)", n["av"], 2048 * va, 0.02, " V")
    yakin("Duty = %50", n["du"], 50.0, 2.0, " %")
    # Sinus AC RMS = genlik/sqrt(2) = 1500/1.414
    yakin("Vac = sinus RMS'i (genlik/√2)", n["ac"], 1500 / math.sqrt(2) * va,
          0.02, " V")

    print("\n--- 6. DUZ CIZGI: olcum YAPILAMAMALI -------------------------------")
    d = s["DUZ"]
    ok("Frekans 0 (periyodik sinyal yok)", d["f"] == 0.0, f"{d['f']}")
    ok("Cevrim 0", d["cv"] == 0, f"{d['cv']}")
    yakin("Vpp 0", d["pp"], 0.0, 1e-6, " V")
    yakin("Vort = 2048 kod", d["av"], 2048 * va, 1e-3, " V")
    yakin("Vac 0 (AC bileseni yok)", d["ac"], 0.0, 1e-3, " V")
    # 1F (S1): toplamlar tamsayi ve TAM -> varyans payi tam 0, karekok tam 0
    ok("1F S1: duz cizgide Vac TAM 0 (kare farki sadelesmesi yok)",
       d["ac"] == 0.0, f"{d['ac']!r} V")

    print("\n--- 7. ASIMETRIK KARE: %25 duty ------------------------------------")
    a = s["D25"]
    yakin("Frekans yine 125 Hz", a["f"], 125.0, 0.05, " Hz")
    yakin("Duty = %25", a["du"], 25.0, 1.5, " %")
    ok("Duty simetrikten AYIRT EDILIYOR", abs(a["du"] - k["du"]) > 15.0,
       f"%{a['du']:.1f} vs %{k['du']:.1f}")
    ok("1F S3: Duty TAM %25.000 (eskiden 60/241 = %24.90)", a["du"] == 25.0,
       f"%{a['du']!r}")

    print("\n--- 8. 1F (S1): YUKSEK DUZ CIZGI 4000 kod --------------------------")
    z = s["DZ40"]
    ok("1F S1: 4000 kodda da Vac TAM 0", z["ac"] == 0.0, f"{z['ac']!r} V")
    ok("1F S1: duz cizgide Vrms == Vort (Vrms = √(ort² + ac²), ac TAM 0)",
       z["rm"] == z["av"], f"{z['rm']!r} / {z['av']!r} V")
    yakin("Vort = 4000 kod", z["av"], 4000 * va, 1e-5, " V")
    z = s["DZ33"]
    ok("1F S1: 3332 kodda Vac TAM 0, Vrms == Vort (S2/n yolu burada 1 ulp sapar)",
       z["ac"] == 0.0 and z["rm"] == z["av"], f"Vac {z['ac']!r}, {z['rm']!r} / {z['av']!r} V")

    print("\n--- 9. 1F (S1): 3000 kod DC + {-3..+3} kod -------------------------")
    g = s["GRT"]
    # Ortalama TAM 3000, varyans TAM 4 kod^2 -> Vac TAM 2 kod (n·S2 − S1²
    # = 399²·4, karekoku 798, /399 = 2: her adim float32'de tam).
    ok("1F S1: kucuk AC (DC ustunde) Vac = 2 kod, float32'de BIT BIT",
       g["ac"] == 2.0 * va,             # va float32; 2·va da tam float32
       f"{g['ac']!r} V ~ {2 * va!r} V (eski float32 kare farki bunu kaybediyordu)")
    yakin("Vort = 3000 kod", g["av"], 3000 * va, 1e-5, " V")
    ok("Fark 6 kod < 8: zaman olcumu yok (hist < 1)",
       g["f"] == 0.0 and g["tr"] == 0.0 and g["tf"] == 0.0, f"f {g['f']}")

    print("\n--- 10. 1F (S4): %90'a VARMAYAN cuce darbeler + tam kenarlar ------")
    c = s["CUCE"]
    # Tam kenarlar 360 kod/ornek: 560 (%10) ile 3440 (%90) arasi TAM 8 ornek.
    yakin("1F S4: tr = yalniz TAM kenar (8 ornek = 0.8 ms), cuce darbe disarida",
          c["tr"], 8 / 10000.0, 1e-10, " s")
    yakin("1F S4: tf = yalniz TAM kenar (8 ornek = 0.8 ms), cuce darbe disarida",
          c["tf"], 8 / 10000.0, 1e-10, " s")
    ok("Tek yukselen kenar: periyot yok", c["f"] == 0.0 and c["cv"] == 0,
       f"f {c['f']} cv {c['cv']}")

    sk2()

    print("\n" + "=" * 78)
    print(f"  A6: {gecti}/{gecti + kaldi} kosul gecti")
    print("=" * 78)
    if kaldi:
        print(f"\n  {kaldi} KOSUL BASARISIZ")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
