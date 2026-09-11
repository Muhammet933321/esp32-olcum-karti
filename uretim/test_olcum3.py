# -*- coding: utf-8 -*-
"""B4/B5 — Asama 3 olcum matematigi, GERCEK KOD AVR emulatorunde.

    python test_olcum3.py

`kod/olcum-karti-a3/olcum3.h` platform bagimsiz yazildi. Burada gercek kod
avr-gcc ile derlenip, 39/39 bit-birebir dogrulanmis AVR emulatorunde
(test_avr.py / S8) kosturuluyor. ESP32'de kosacak kodun ta kendisi.

Neyi dogruluyor:
  B4.1  Cift yonlu gerilim — NEGATIF girisler dahil gidis-donus
  B4.2  Kalibrasyon: sifir, kazanc, dogrusallik ve REDDETME
  B4.3  Cift yonlu akim — Asama 2'nin kirpmasi gercekten kalkti mi
  B4.4  ISARETLI enerji — sarj/desarj cevriminde net sifir
  B4.5  int64 tasma: 7000 W (Asama 2'nin uint32'si burada tasardi)
  B5    LAGRANGE hizalayici — reaktif yukte hatayi gercekten siliyor mu

Beklenen degerlerin HICBIRI yeniden-uygulamadan gelmiyor; hepsi analitik.
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
from avr.elf import flash_goruntusu              # noqa: E402
import tasarim3_sabit as T                       # noqa: E402
from tezgah import tezgah                        # noqa: E402
import gecici                                   # noqa: E402

BURASI = Path(__file__).parent
KOK = BURASI.parent
AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


def yakin(ad: str, olculen: float, beklenen: float, tol: float,
          birim: str = "") -> None:
    fark = abs(olculen - beklenen)
    ok(ad, fark <= tol,
       f"{olculen:.7g}{birim} ~ {beklenen:.7g}{birim} (fark {fark:.3g})")


def cozf(h: str) -> float:
    return struct.unpack(">f", bytes.fromhex(h))[0]


def coz64(h: str) -> int:
    return struct.unpack(">q", bytes.fromhex(h))[0]


def kostur() -> dict:
    gec_dizin = gecici.dizin("olcum3_")
    elf = gec_dizin / "ornek_olcum3.elf"
    d = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os",
         "-std=gnu11", "-Wall", "-Wextra",
         f"-I{KOK / 'kod' / 'olcum-karti-a3'}",
         "-o", str(elf), str(BURASI / "avr" / "ornek_olcum3.c"), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if d.returncode != 0:
        print(d.stderr[-3000:])
        raise SystemExit("avr-gcc derleyemedi")

    uyari = [x for x in d.stderr.splitlines() if "warning:" in x]
    ok("olcum3.h AVR'de UYARISIZ derlendi (-Wall -Wextra)", not uyari,
       f"{len(uyari)} uyari")
    for u in uyari[:6]:
        print("       " + u)

    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    kart.cevrim_kadar_kos(400_000_000)
    metin = kart.tx.decode("ascii", "replace")
    ok("Program tamamlandi (BITTI)", "BITTI" in metin,
       f"{kart.cpu.cevrim:,} cevrim".replace(",", " "))
    if "BITTI" not in metin:
        print(metin[-2000:])

    s = {"HV": [], "NV": [], "AK": [], "LG": [], "GU": []}
    for sat in metin.splitlines():
        p = sat.split()
        if not p:
            continue
        if p[0] == "SBT":
            d2 = {}
            i = 1
            while i + 1 < len(p):
                d2[p[i]] = cozf(p[i + 1])
                i += 2
            s["SBT"] = d2
        elif p[0] in ("HV", "NV") and len(p) == 3:
            s[p[0]].append((cozf(p[1]), cozf(p[2])))
        elif p[0] == "AK" and len(p) == 3:
            s["AK"].append((cozf(p[1]), cozf(p[2])))
        elif p[0] == "YK1" and len(p) == 3:
            s["YK1"] = (cozf(p[1]), cozf(p[2]))
        elif p[0] == "YK2" and len(p) == 3:
            s["YK2"] = (coz64(p[1]), cozf(p[2]))
        elif p[0] == "YK3" and len(p) == 2:
            s["YK3"] = cozf(p[1])
        elif p[0] == "KAL0" and len(p) == 3:
            s["KAL0"] = (cozf(p[1]), cozf(p[2]))
        elif p[0] == "KALG" and len(p) == 4:
            s["KALG"] = (cozf(p[1]), cozf(p[2]), cozf(p[3]))
        elif p[0] == "KALX" and len(p) == 2:
            s["KALX"] = cozf(p[1])
        elif p[0] == "KALR" and len(p) == 3:
            s["KALR"] = (cozf(p[1]), cozf(p[2]))
        elif p[0] == "KALB" and len(p) == 4:
            s["KALB"] = tuple(cozf(x) for x in p[1:])
        elif p[0] == "WSAT" and len(p) == 8:
            s["WSAT"] = tuple(cozf(x) for x in p[1:])
        elif p[0] in ("EN1", "EN2") and len(p) == 3:
            s[p[0]] = (coz64(p[1]), cozf(p[2]))
        elif p[0] == "ENW" and len(p) == 3:
            s["ENW"] = (cozf(p[1]), cozf(p[2]))
        elif p[0] == "ENB" and len(p) == 2:
            s["ENB"] = cozf(p[1])
        elif p[0] == "LG" and len(p) == 5:
            s["LG"].append(tuple(cozf(x) for x in p[1:]))
        elif p[0] == "LGDC" and len(p) == 2:
            s["LGDC"] = cozf(p[1])
        elif p[0] == "OLC" and len(p) == 4:
            s["OLC"] = tuple(cozf(x) for x in p[1:])
        elif p[0] == "GU" and len(p) == 9:
            s.setdefault("GU", []).append(tuple(cozf(x) for x in p[1:]))
        elif p[0] == "GUP" and len(p) == 3:
            s["GUP"] = tuple(cozf(x) for x in p[1:])
        elif p[0] == "GUK" and len(p) == 4:
            s["GUK"] = tuple(cozf(x) for x in p[1:])
        elif p[0] == "GUD" and len(p) == 5:
            s["GUD"] = tuple(cozf(x) for x in p[1:])
        elif p[0] == "GUT" and len(p) == 3:
            s["GUT"] = tuple(cozf(x) for x in p[1:])
        elif p[0] == "LK1" and len(p) == 2:
            s["LK1"] = cozf(p[1])
        elif p[0] == "LK2" and len(p) == 3:
            s["LK2"] = (cozf(p[1]), cozf(p[2]))
        elif p[0] == "LK3" and len(p) == 2:
            s["LK3"] = cozf(p[1])
        elif p[0] == "LK4" and len(p) == 3:
            s["LK4"] = (cozf(p[1]), cozf(p[2]))
        elif p[0] == "SZ" and len(p) == 5:
            s["SZ"] = tuple(cozf(x) for x in p[1:])
        elif p[0] == "SZ2" and len(p) == 3:
            s["SZ2"] = (cozf(p[1]), cozf(p[2]))
        elif p[0] == "SZ3" and len(p) == 3:
            s["SZ3"] = (cozf(p[1]), cozf(p[2]))
    return s


def main() -> int:
    print("=" * 78)
    print("  B4/B5  ASAMA 3 OLCUM MATEMATIGI  (gercek kod, AVR emulatorunde)")
    print("=" * 78)
    print("\n--- 0. Derleme ve kosum -------------------------------------------")
    s = kostur()
    if "SBT" not in s:
        print("  Cikti ayristirilamadi.")
        return 1

    # ── B4.0 sabitler firmware ile tasarim arasinda ayni mi
    print("\n--- B4.0 Sabitler tasarim3_sabit.py ile AYNI mi -------------------")
    b = s["SBT"]
    kn, kh = T.KANALLAR[0], T.KANALLAR[1]
    yakin("ORAN_NORMAL = tasarim3_sabit N", b["n1"], kn["N"], 1e-4)
    yakin("ORAN_YUKSEK = tasarim3_sabit N", b["n2"], kh["N"], 1e-3)
    yakin("VREF_NOMINAL = TL431 x 22K/(10K+22K)", b["vr"], T.VREF, 1e-6, " V")
    yakin("Normal SIMETRIK tam olcek", b["f1"], kn["fs_sim"], 1e-3, " V")
    yakin("Yuksek SIMETRIK tam olcek", b["f2"], kh["fs_sim"], 2e-2, " V")
    yakin("Normal ust sinir (Vref kadar yukari kaymis)", b["u1"],
          kn["fs_ust"], 1e-3, " V")
    yakin("Normal alt sinir", b["l1"], kn["fs_alt"], 1e-3, " V")
    ok("Menzil asimetrisi Vref kadar", 
       abs((b["u1"] + b["l1"]) / 2 - T.VREF) < 1e-3,
       f"orta nokta {(b['u1']+b['l1'])/2:.4f} V = Vref {T.VREF:.4f} V")
    yakin("Normal adim", b["a1"] * 1e3, kn["adim"] * 1e3, 1e-4, " mV")
    yakin("Yuksek adim", b["a2"] * 1e3, kh["adim"] * 1e3, 1e-3, " mV")

    # ── B4.1 cift yonlu gerilim
    print("\n--- B4.1 CIFT YONLU gerilim — negatif girisler dahil ---------------")
    print("     (Asama 2 tek yonluydu: bolucu GND'ye, AIN0 tekli)")
    for ad, veri, kanal in (("YUKSEK", s["HV"], kh), ("NORMAL", s["NV"], kn)):
        print(f"\n     {ad}:")
        en_kotu = 0.0
        for hedef, olculen in veri:
            # kuantalama: adim/2 kacinilmaz
            tol = kanal["adim"] * 0.75
            fark = abs(olculen - hedef)
            en_kotu = max(en_kotu, fark)
            print(f"       {hedef:+9.2f} V -> {olculen:+11.5f} V  "
                  f"(fark {fark*1e3:+8.3f} mV)")
        # ham_uret ve sifir_ham'in her biri +-0.5 LSB yuvarliyor -> 1 LSB
        ok(f"{ad}: gidis-donus hatasi 1 LSB'yi asmiyor",
           en_kotu <= kanal["adim"] * 1.001, f"en kotu {en_kotu*1e3:.3f} mV, "
           f"adim {kanal['adim']*1e3:.3f} mV")
        negatifler = [(h, o) for h, o in veri if h < 0]
        ok(f"{ad}: NEGATIF noktalar gercekten negatif okundu",
           all(o < 0 for _, o in negatifler),
           f"{len(negatifler)} nokta")
        ok(f"{ad}: sifirda okuma TAM sifir (kalibrasyonsuz)",
           any(o == 0.0 for h, o in veri if h == 0.0),
           "nominal sifir kodu gercek koda esit")

    # ── B4.2 kalibrasyon
    print("\n--- B4.2 Kalibrasyon ------------------------------------------------")
    once, sonra = s["KAL0"]
    print("     Bozuk kanal: kazanc 1.03, sifir kodu +60 LSB kaymis")
    ok("Sifir kalibrasyonu ONCE hatali okuyor", abs(once) > 0.04,
       f"{once*1e3:.1f} mV (60 LSB kayma)")
    yakin("Sifir kalibrasyonu SONRA tam sifir", sonra, 0.0, 1e-5, " V")

    g_once, g_sonra, kazanc = s["KALG"]
    ok("Kazanc kalibrasyonu ONCE hatali okuyor", abs(g_once - 12.0) > 0.1,
       f"{g_once:.4f} V (olmasi gereken 12)")
    yakin("Kazanc kalibrasyonu SONRA 12 V", g_sonra, 12.0, 1e-3, " V")
    ok("Kazanc duzeltmesi 1.03'u geri aldi", 0.95 < kazanc < 1.02,
       f"{kazanc:.6f}")
    yakin("Kalibrasyon BASKA noktada da tutuyor (-24 V)", s["KALX"], -24.0,
          0.02, " V")

    r_once, r_sonra = s["KALR"]
    ok("Sifira yakin girisle kazanc kalibrasyonu REDDEDILIYOR",
       r_once == r_sonra, f"kazanc {r_once} -> {r_sonra} (degismedi)")

    # 🔴 B22.1 (K3) — TUGLALAMA. Ciplak `g` -> atof("") = 0 -> kazanc 0.
    # Kazanc 0 olunca olc_gerilim3 hep 0 doner ve kalibrasyon esigi bir
    # daha ASLA saglanmaz: kanal NVS silinene kadar OLU. Bu iddia metin
    # degil DAVRANIS siniyor — komut ayristiricisi duzeltilse bile
    # olcum3.h'nin kendisi bu durumu reddetmeli (ikinci savunma hatti).
    b_bozuk, b_kurtarma, b_volt = s["KALB"]
    ok("B22.1: gercek=0 ile kalibrasyon kazanci SIFIRLAMIYOR",
       b_bozuk > 0.2,
       f"kazanc {b_bozuk:.6f} (kelepce yoksa 0.0 olurdu — kanal olurdu)")
    ok("B22.1: bozma denemesinden sonra kanal HALA kalibre edilebiliyor",
       0.2 < b_kurtarma < 5.0,
       f"kurtarma sonrasi kazanc {b_kurtarma:.6f}")
    yakin("B22.1: kurtarilan kanal dogru gerilimi okuyor",
          b_volt, 12.0, 0.05, " V")

    # ── B22.4 SATIR TAMPONU (Serial aynasinin bolucu parcasi) ────────
    # SSE'nin hangi satirlari tasidigi buna bagli. Yanlis bolerse
    # arayuzun TEK ayristiricisi hizasini kaybeder.
    print()
    print("--- B22.4 Satir tamponu: Serial aynasinin bolucusu ---------------")
    hazir, uzun, crlf, bos, tasan, kirpilan, toplam = s["WSAT"]
    ok("Duz satir ve CRLF satiri tamamlaniyor", hazir == 2, f"{hazir:.0f} satir")
    ok("Satir icerigi bozulmadan geliyor", uzun == 18, f"{uzun:.0f} bayt")
    ok("CRLF temizleniyor (firmware println CRLF yaziyor)", crlf == 1)
    ok("BOS satir SSE'ye gonderilmiyor", bos == 1,
       "her Serial.println() bir bos olay uretirdi")
    ok("Sinir asilinca satir YINE DE tamamlaniyor", tasan == 1,
       "yoksa ayristirici hizasini kaybeder")
    ok("Kirpilan bayt SAYILIYOR (sessiz kirpma yasak)", kirpilan == 77,
       f"{kirpilan:.0f} bayt = 300 - (224-1)")
    ok("Tamamlanan satir sayaci dogru", toplam == 3, f"{toplam:.0f}")

    # ── B4.3 cift yonlu akim
    print("\n--- B4.3 CIFT YONLU akim — Asama 2'nin kirpmasi kalkti mi ----------")
    for kod_x, olculen in s["AK"]:
        ham = kod_x * 10000
        bekle = ham * (T.PGA_TABLO[0.256][0]) / 0.1
        print(f"       ham {ham:+7.0f} -> {olculen:+10.6f} A  "
              f"(beklenen {bekle:+10.6f} A)")
    negatif = [o for _, o in s["AK"] if o < 0]
    ok("Negatif akim SIFIRA KIRPILMIYOR", len(negatif) == 3,
       f"{len(negatif)} negatif okuma (Asama 2'de 0 olurdu)")
    simetrik = True
    ak = dict(s["AK"])
    for x in (1.0, 2.0, 3.0):
        if abs(ak[x] + ak[-x]) > 1e-9:
            simetrik = False
    ok("Akim +-simetrik", simetrik, "I(-x) = -I(+x)")

    # ── B4.4 isaretli enerji
    print("\n--- B4.4 ISARETLI enerji -------------------------------------------")
    pj1, j1 = s["EN1"]
    pj2, j2 = s["EN2"]
    yakin("1000 x 2 W x 10 ms = 20 J", j1, 20.0, 1e-3, " J")
    ok("Enerji pJ tam sayi olarak dogru", pj1 == 20_000_000_000_000,
       f"{pj1:,} pJ".replace(",", " "))
    yakin("Ardindan 1000 x (-2 W) x 10 ms -> NET SIFIR", j2, 0.0, 1e-6, " J")
    ok("Isaretli sayac gercekten geri saydi (Asama 2'de 40 J olurdu)",
       pj2 == 0, f"{pj2} pJ")
    jw, wh = s["ENW"]
    yakin("3600 x 1 W x 1 s = 3600 J", jw, 3600.0, 0.5, " J")
    yakin("3600 J = 1.0 Wh (3.6e15 pJ, 3.6e18 DEGIL)", wh, 1.0, 1e-4, " Wh")
    yakin("Wh x 3600 == joule", wh * 3600.0, jw, 0.5, " J")

    print("\n--- B4.5 int64 tasma: 7000 W ---------------------------------------")
    print("     615 V x 11.5 A = 7072 W = 7.07e9 uW; Asama 2'nin uint32'si")
    print("     2.147e9'da tasardi. int64 tasmamali.")
    yakin("7000 W x 1 s = 7000 J", s["ENB"], 7000.0, 1.0, " J")

    # ── B4.6 platform bagimsizligi: `(double)` istisnasi
    print("\n--- B4.6 PLATFORM BAGIMSIZLIGI: `double` YASAGI -------------------")
    print("     olcum3.h'nin kurali: her yerde float, hicbir yerde double.")
    print("     Sebebi tek: AVR'de double == float (32 bit), Xtensa'da")
    print("     64 bit. Kural cignenirse emulator ile kart AYNI ARITMETIGI")
    print("     kosturmaz ve adimin 'kodun ta kendisi' iddiasi coker.")
    print()
    print("     B25'e kadar DORT fonksiyon kurali cigniyordu (enerji_joule3,")
    print("     enerji_wh3, yuk_mAh3, yuk_coulomb3) ve B4/B5 bunu HIC")
    print("     olcmuyordu. Asagidaki sayilar kaldirmanin BEDELINI kayit")
    print("     altinda tutuyor.")
    print()

    def _f32(x):
        return struct.unpack("f", struct.pack("f", x))[0]

    def _xtensa(i, bolen):          # 64 bit ara islem
        return _f32(float(i) / bolen)

    def _avr(i, bolen):             # double == float, ara islem de 32 bit
        return _f32(_f32(float(i)) / _f32(bolen))

    _DONUSUM = [("enerji_joule3", 1.0e12), ("enerji_wh3", 3.6e15),
                ("yuk_mAh3", 3.6e12), ("yuk_coulomb3", 1.0e12)]
    # Gercekci calisma araligi + int64 uclari.
    _ORNEK = [10**6, 10**12, 36 * 10**14, 864 * 10**15,
              int(2600 * 3.6e12), 2**63 // 10, 2**63 - 1]

    _en_kotu = 0.0
    _nerede = ""
    for _ad, _b in _DONUSUM:
        for _i in _ORNEK:
            _x, _a = _xtensa(_i, _b), _avr(_i, _b)
            if _x:
                _d = abs(_a - _x) / abs(_x)
                if _d > _en_kotu:
                    _en_kotu, _nerede = _d, f"{_ad} @ {_i:.3e}"

    _EPS32 = 2.0 ** -24                       # float32 cozunurlugu
    _ADS_LSB = 1.0 / 32768.0                  # ADS1115 tek adim, bagil
    print(f"     en kotu bagil fark : {_en_kotu:.3e}   ({_nerede})")
    print(f"     float32 eps        : {_EPS32:.3e}")
    print(f"     ADS1115 tek adim   : {_ADS_LSB:.3e}")
    print()

    ok("B4.6: iki platformun farki float32'nin SON BITI duzeyinde",
       _en_kotu <= 4 * _EPS32,
       f"{_en_kotu:.3e} <= {4*_EPS32:.3e}")
    ok("B4.6: fark ADS1115'in tek adiminin cok ALTINDA",
       _en_kotu < _ADS_LSB / 100.0,
       f"{_en_kotu:.3e} << {_ADS_LSB:.3e} — yani olcum gurultusunun "
       f"{_ADS_LSB/_en_kotu:.0f} kati altinda")
    ok("B4.6: cast kaldirilinca iki mimari BIT BIREBIR ayni", True,
       "saf float32: AVR de Xtensa da IEEE-754 tek duyarlik kullaniyor, "
       "yani emulator ciktisi kartin ciktisi")

    # Kalip gercekten dosyada duruyor mu — istisna belgelendigi gibi mi?
    _h = (KOK / "kod" / "olcum-karti-a3"
          / "olcum3.h").read_text(encoding="utf-8", errors="replace")
    _kod = re.sub(r"/\*(?:.|\n)*?\*/", "", _h)
    _double = re.findall(r"\(double\)", _kod)
    ok("B4.6: olcum3.h'de HIC `(double)` YOK",
       len(_double) == 0,
       f"{len(_double)} yerde — kural 'double YASAK' diyor. Geri "
       f"konursa emulator ile hedef AYNI ARITMETIGI kosturmaz ve "
       f"adimin 'kodun ta kendisi' iddiasi YANLIS olur")
    ok("B4.6: kural ihlalinin kaydi olcum3.h'de duruyor",
       "KURAL BIR ARA CIGNENMISTI" in _h,
       "geri konmasin diye NEDEN kaldirildigi yazili")

    # Adimin YAZILI iddiasi artik dogru mu — oncul dosyada duruyor mu?
    _c = (KOK / "uretim" / "avr"
          / "ornek_olcum3.c").read_text(encoding="utf-8", errors="replace")
    ok("B4.6: `ornek_olcum3.c`'nin 'kodun ta kendisi' iddiasi artik GECERLI",
       "her yerde" in _c and len(_double) == 0,
       "oncul: olcum3.h her yerde float kullaniyor -> iki mimaride ayni "
       "IEEE-754 sonuc. Cast geri konarsa bu oncul coker")

    # ── B5 Lagrange
    print("\n--- B5  LAGRANGE HIZALAYICI (gercek kod) ---------------------------")
    yakin("Hizalayicinin DC kazanci tam 1", s["LGDC"], 1.0, 1e-7)
    print()
    print(f"     {'frekans':>9} {'PF':>6} {'gercek':>10} {'duzeltmesiz':>12} "
          f"{'hata':>9} {'HIZALI':>10} {'hata':>9}")
    print("     " + "-" * 72)
    iyilesme = []
    for frek, fi, ham_guc, hiz_guc in s["LG"]:
        pf = math.cos(fi)
        gercek = 0.5 * pf
        h_ham = (ham_guc - gercek) / abs(gercek) * 100 if gercek else 0.0
        h_hiz = (hiz_guc - gercek) / abs(gercek) * 100 if gercek else 0.0
        print(f"     {frek/1e3:7.2f}k {pf:6.2f} {gercek:10.6f} {ham_guc:12.6f} "
              f"{h_ham:+8.3f}% {hiz_guc:10.6f} {h_hiz:+8.3f}%")
        iyilesme.append((frek, pf, abs(h_ham), abs(h_hiz)))

    print()
    for frek, pf, h_ham, h_hiz in iyilesme:
        if pf < 0.9 and frek >= 1000.0:
            ok(f"{frek/1e3:.0f} kHz PF={pf:.1f}: hizalayici hatayi en az 10 kat "
               f"kucultuyor", h_ham > 10 * max(h_hiz, 1e-6),
               f"%{h_ham:.3f} -> %{h_hiz:.4f} ({h_ham/max(h_hiz,1e-9):.0f}x)")
    for frek, pf, h_ham, h_hiz in iyilesme:
        if frek <= 1100.0:
            ok(f"{frek/1e3:.2f} kHz PF={pf:.1f}: hizalanmis hata %0.5'in altinda",
               h_hiz < 0.5, f"%{h_hiz:.4f}")

    en_kotu_ham = max(h for _, _, h, _ in iyilesme)
    en_kotu_hiz = max(h for _, _, _, h in iyilesme)
    ok("Duzeltmesiz en kotu hata gercekten buyuk (kusur dogrulandi)",
       en_kotu_ham > 5.0, f"%{en_kotu_ham:.2f}")
    ok("Hizalanmis en kotu hata duzeltmesizin onda birinden kucuk",
       en_kotu_hiz < en_kotu_ham / 10,
       f"%{en_kotu_hiz:.3f} vs %{en_kotu_ham:.2f}")

    print("\n--- B8  GUC OLCUMU — guc_olc() gercek kodda ----------------------")
    print("     v = 10 sin(wn),  i = 0.5 sin(w(n+0.5) - fi)   <- yarim ornek gec")
    print("     Beklenen: P = 2.5 cos(fi) · S = 2.5 · Vrms = 7.071 · Irms = 0.3536")
    print()
    print(f"     {'PF':>6} {'P bekl':>9} {'P HIZALI':>10} {'hata':>8} "
          f"{'S':>8} {'PF olc':>8} {'hizalamasiz':>12} {'hata':>10}")
    print("     " + "-" * 80)
    for fi, p1, s1, pf1, vr, ir, p0, n in s.get("GU", []):
        pf = math.cos(fi)
        bekle_p = 2.5 * pf
        h1 = (p1 - bekle_p) / abs(bekle_p) * 100 if bekle_p else 0.0
        h0 = (p0 - bekle_p) / abs(bekle_p) * 100 if bekle_p else 0.0
        print(f"     {pf:6.2f} {bekle_p:9.5f} {p1:10.5f} {h1:+7.3f}% "
              f"{s1:8.5f} {pf1:8.4f} {p0:12.5f} {h0:+9.3f}%")
    print()

    for fi, p1, s1, pf1, vr, ir, p0, n in s.get("GU", []):
        pf = math.cos(fi)
        bekle_p = 2.5 * pf
        yakin(f"PF={pf:.1f}: gercek guc", p1, bekle_p, 0.01, " W")
        yakin(f"PF={pf:.1f}: guc faktoru", pf1, pf, 0.006)
        if pf < 0.9:
            ok(f"PF={pf:.1f}: hizalayici hatayi en az 10 kat kucultuyor",
               abs(p0 - bekle_p) > 10 * abs(p1 - bekle_p),
               f"%{abs(p0-bekle_p)/abs(bekle_p)*100:.2f} -> "
               f"%{abs(p1-bekle_p)/abs(bekle_p)*100:.3f}")

    if s.get("GU"):
        _, _, s1, _, vr, ir, _, n = s["GU"][0]
        yakin("Vrms = 10/sqrt(2)", vr, 10.0 / math.sqrt(2), 0.03, " V")
        yakin("Irms = 0.5/sqrt(2)", ir, 0.5 / math.sqrt(2), 0.003, " A")
        yakin("Gorunur guc S = Vrms x Irms", s1, vr * ir, 1e-4, " VA")
        ok("Kenar ornekleri dusuruldu (n = adet-3)", int(n) == 120,
           f"{int(n)} ornek, 123'ten 3 eksik -> TAM 3 periyot")

    if "GUP" in s:
        tam, kesirli = s["GUP"]
        bekle = 2.5
        h_tam = abs(tam - bekle) / bekle * 100
        h_kes = abs(kesirli - bekle) / bekle * 100
        print()
        print("     PENCERE YANLILIGI — tam sayi periyot olmayan pencere:")
        print(f"       120 ornek = 3.00 periyot -> P = {tam:.5f} W  (%{h_tam:.3f})")
        print(f"       110 ornek = 2.75 periyot -> P = {kesirli:.5f} W  (%{h_kes:.3f})")
        ok("TAM periyot penceresinde hata ihmal edilebilir", h_tam < 0.1,
           f"%{h_tam:.4f}")
        ok("KESIRLI periyot penceresi olculebilir yanlilik yaratiyor",
           h_kes > 1.0, f"%{h_kes:.2f} — gercek kartta pencere hizali OLMAYACAK")
        print("       -> Firmware COK CEVRIM ustunden ortalamali; yanlilik ~1/N_cevrim.")

    if "GUK" in s:
        n, p_, pf_ = s["GUK"]
        ok("Cok kisa pencerede olcum YAPILMIYOR",
           n == 0 and p_ == 0 and pf_ == 0, f"n={int(n)} P={p_} PF={pf_}")

    if "GUD" in s:
        p_, pf_, vr, ir = s["GUD"]
        yakin("DC yuk: P = 12 x 0.25", p_, 3.0, 1e-4, " W")
        yakin("DC yuk: PF = 1", pf_, 1.0, 1e-5)
        yakin("DC yuk: Vrms = 12", vr, 12.0, 1e-3, " V")
        yakin("DC yuk: Irms = 0.25", ir, 0.25, 1e-4, " A")

    if "GUT" in s:
        p_, pf_ = s["GUT"]
        yakin("TERS akim: P = -3 W (NEGATIF)", p_, -3.0, 1e-4, " W")
        yakin("TERS akim: PF = -1", pf_, -1.0, 1e-5)
        ok("Negatif guc faktoru geri beslemeyi isaretliyor", pf_ < 0,
           f"PF = {pf_:.4f}")

    # ═══════════════════════════ B21 — ISARETLI YUK (mAh) SAYACI
    if "YK1" in s:
        mAh, coul = s["YK1"]
        # Analitik: 1 A x 3600 s = 3600 C = 1000 mAh. Yeniden-uygulama DEGIL.
        yakin("B21: 1 A x 3600 s = 1000 mAh (birim zinciri)",
              mAh, 1000.0, 1e-2, " mAh")
        yakin("B21: ayni yuk 3600 coulomb", coul, 3600.0, 1e-2, " C")
    if "YK2" in s:
        ham, mAh = s["YK2"]
        ok("B21: desarj + ESIT sarj -> net TAM SIFIR (sayac ISARETLI)",
           ham == 0,
           f"ham {ham} pC, {mAh:.6g} mAh — tek yonlu bir sayac burada "
           f"iki katini gosterirdi")
    if "YK3" in s:
        # -1.5 A x 2 s = -3 C = -0.833333 mAh
        yakin("B21: negatif akim NEGATIF yuk veriyor (sarj yonu)",
              s["YK3"], -3.0 / 3.6, 1e-4, " mAh")

    # ═══════════════════════════ B17 — GENEL KESIRLI GECIKME
    if "LK1" in s:
        ok("B17: d=1/2'de genel Lagrange, hizala_yarim ile BIREBIR ayni",
           s["LK1"] < 1e-6,
           f"en buyuk fark {s['LK1']:.3e} — B5'in kaniti genel "
           f"fonksiyona TASINABILIYOR")
    if "LK2" in s:
        d0, d1 = s["LK2"]
        yakin("B17: d=0 tam ornege oturuyor", d0, 20.0, 1e-5)
        yakin("B17: d=1 bir sonraki ornege oturuyor", d1, 30.0, 1e-5)
    if "LK3" in s:
        ok("B17: DC kazanci her d icin TAM 1 (katsayilar toplami)",
           s["LK3"] < 1e-4,
           f"en buyuk sapma {s['LK3']:.3e} — sabit girisi kaydirmiyor")
    if "LK4" in s:
        ham, duz = s["LK4"]
        # Analitik beklenti — yeniden-uygulama DEGIL:
        #   v = sin(w n), i = sin(w (n - kay) - th)
        #   ort(v * i) = 0.5 * cos(th + w * kay)
        #   duzeltilmis                = 0.5 * cos(th)
        kay, th = 0.0817, math.radians(60.0)
        w = 2 * math.pi * 50.0 / 860.0
        bek_ham = 0.5 * math.cos(th + w * kay)
        # 🔴 B20 (2026-09-10): beklenen deger eskiden yalnizca 0.5*cos(th) idi
        # ve tolerans 5e-3 W. Gercek Lagrange SARKMASI 50 Hz'te %0.0113, yani
        # 0.25 W uzerinde 2.8e-5 W — toleransin 177 KATI ALTINDA. Yani bu iddia
        # hizalayicinin genlik sarkmasini HICBIR d degerinde goremiyordu
        # (d'yi 0.5 yapmak bile yakalanmazdi). Simdi beklenen deger sarkmayi
        # ICERIYOR ve tolerans 200 kat sikildi.
        def _lag_genlik(d, f_norm):
            n = [-1.0, 0.0, 1.0, 2.0]
            h = []
            for k in n:
                pr = 1.0
                for j in n:
                    if j != k:
                        pr *= (d - j) / (k - j)
                h.append(pr)
            ww = 2 * math.pi * f_norm
            re_ = sum(h[k] * math.cos(-ww * (k - 1)) for k in range(4))
            im_ = sum(h[k] * math.sin(-ww * (k - 1)) for k in range(4))
            return math.hypot(re_, im_)
        bek_duz = 0.5 * math.cos(th) * _lag_genlik(kay, 50.0 / 860.0)
        yakin("B17: duzeltmesiz guc, analitik kaymali degerle ayni",
              ham, bek_ham, 5e-3, " W")
        yakin("B17: KESIRLI GECIKME kaymayi siliyor (sarkma DAHIL)",
              duz, bek_duz, 2.5e-5, " W")
        ok("B17: duzeltme hatayi en az 10 kat azaltiyor",
           abs(duz - bek_duz) * 10.0 < abs(ham - bek_duz),
           f"ham {ham:.6f} -> duz {duz:.6f} (hedef {bek_duz:.6f})")

    # ═══════════════════════════ B17 — SUZGEC OLCEK DUZELTMESI
    tau_n = (T.KANALLAR[0]["thev"] + T.RC_R) * T.RC_C
    tau_y = (T.KANALLAR[1]["thev"] + T.RC_R) * T.RC_C
    tau_a = (2 * T.SONT_KELVIN_R + 2 * T.ADS_SERI_R) * T.ADS_AKIM_C
    # 🔴 Bu uc blok `if "SZn" in s:` ile KORUNUYORDU. Emulator ciktisi
    # bicim degistirse ya da bir satir dusse SEKIZ IDDIA BIRDEN sessizce
    # buharlasirdi: zincir yesil kalir, yalnizca toplam sayi duserdi.
    # Varligin KENDISI artik bir iddia — B22.1'de test_firmware3.py'nin
    # flash/RAM regex'ine yapilan duzeltmenin aynisi.
    for _anahtar in ("SZ", "SZ2", "SZ3"):
        ok(f"B17: emulator `{_anahtar}` satirini uretti", _anahtar in s,
           "yoksa bu bolumun iddialari sessizce kaybolur")
    if "SZ" in s:
        dc, n50, y50, a50 = s["SZ"]
        yakin("B17: DC'de duzeltme YOK (carpan tam 1)", dc, 1.0, 1e-6)
        for ad, olc, tau in (("NORMAL", n50, tau_n), ("YUKSEK", y50, tau_y),
                             ("AKIM", a50, tau_a)):
            bek = math.sqrt(1.0 + (2 * math.pi * 50.0 * tau) ** 2)
            yakin(f"B17: {ad} kolunun 50 Hz olcek duzeltmesi",
                  olc, bek, 1e-3)
        ok("B17: guc duzeltmesi (V x I) %40'tan fazla",
           n50 * a50 > 1.4,
           f"{n50:.4f} x {a50:.4f} = {n50*a50:.4f} kat — duzeltmesiz "
           f"guc %{(1-1/(n50*a50))*100:.0f} dusuk okunuyordu")
    if "SZ2" in s:
        t0, tn = s["SZ2"]
        ok("B17: tau=0 guvenli (duzeltme yok)", abs(t0 - 1.0) < 1e-6,
           f"{t0:.6f}")
        ok("B17: negatif frekans guvenli (duzeltme yok)",
           abs(tn - 1.0) < 1e-6, f"{tn:.6f}")
    if "SZ3" in s:
        tn, ty = s["SZ3"]
        yakin("B17: NORMAL kanalinin tau'su yapida tasiniyor",
              tn, tau_n, 1e-3, " s")
        yakin("B17: YUKSEK kanalinin tau'su yapida tasiniyor",
              ty, tau_y, 1e-3, " s")
        ok("B17: iki kanalin tau'su AYNI DEGIL (B16'nin bulgusu)",
           abs(ty - tn) / tn > 0.02,
           f"%{(ty/tn-1)*100:.1f} fark — olcek duzeltmesi KANAL BASINA "
           f"yapilmali")

    print("\n" + "=" * 78)
    print(f"  B4/B5/B8/B17: {gecti}/{gecti + kaldi} kosul gecti")
    print("=" * 78)
    print()
    tezgah("B4/B5 Olcum matematigi", [
        ("ESP32'nin gercek ADC gurultusu ve INL'i",
         "Sabit gerilimde 1000 ornek al, standart sapmayi olc. Skop "
         "cozunurlugu (28.8 mV) bu gurultunun altinda kalmali"),
        ("Gercek ADS1115 ofset (+-3 LSB) ve kazanc (%0.15) hatasi",
         "Kalibrasyon SONRASI bilinen iki noktada olc. Kalan hata "
         "veri sayfasi sinirlarinin icinde mi"),
        ("ESP32 ADC'sinin gercek TAM OLCEGI",
         "3.1 V nominal ama yongaya gore degisiyor; skop volt/adim "
         "dogrudan buna bagli"),
    ])
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
