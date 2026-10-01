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
import dataclasses
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

from avr.nor_flas import (NorFlas, A0, A1, A2, VERI, KOMUT, SIL,  # noqa: E402
                          ARIZA_OKU, ARIZA_YAZ)
from avr import mega328                          # noqa: E402
from avr.cekirdek import Cekirdek                # noqa: E402
from avr.elf import flash_goruntusu              # noqa: E402
import gecici                                    # noqa: E402
import kayit_bicim as KB                         # noqa: E402
from tezgah import tezgah                         # noqa: E402

AVR_BIN = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin")
AVR_GCC = AVR_BIN / "avr-gcc.exe"
AVR_GXX = AVR_BIN / "avr-g++.exe"
HARNESS = BURASI / "avr" / "ornek_kayit.c"
SEKTOR = 512          # testte kucuk sektor: halka cok doner, emulatorde ucuz
SEKTOR_ADET = 8       # varsayilan; derle() -DNOR_SEKTOR_ADET ile gecirir
AZAMI_YUK = 256       # 4 + 7 nokta
CPP_BASLIKLAR = ["kayit_bicim.h", "kayit_nokta.h", "kayit_gunluk.h", "kayit_oturum.h",
                 "kayit_yonet.h", "kalgec.h", "kayit_halka.h", "kayit_plan.h"]
_ELF: dict[str, Path] = {}

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
    # Son inceleme (bulgu 4): hata yollari sinanabilsin diye ariza enjeksiyonu.
    f = NorFlas(1024, sektor=512)
    f.tak(k)
    f.bellek[0:4] = b"\x11\x22\x33\x44"
    y[ARIZA_OKU](2)
    adres(0)
    ilk, ikinci = o[VERI](), o[VERI]()
    d1, d2 = o[KOMUT](), o[KOMUT]()
    ok("B71.N8 okuma arizasi: n. bayt bozulur, durum biti 1 bir kez okunur",
       ilk == 0x11 and ikinci == 0xFF and d1 & 2 and not d2 & 2,
       f"{ilk:#x} {ikinci:#x} durum {d1} {d2}")
    y[ARIZA_YAZ](1)
    adres(0x100)
    y[VERI](0x00)
    y[VERI](0x00)
    d1 = o[KOMUT]()
    ok("B71.N9 yazma arizasi: bayt ve ardindakiler PROGRAMLANMAZ, durum biti 1",
       f.bellek[0x100] == 0xFF and f.bellek[0x101] == 0xFF and d1 & 2,
       f"{f.bellek[0x100]:#x} {f.bellek[0x101]:#x} durum {d1}")


# ── ortak yardimcilar ─────────────────────────────────────────────────
def f32(x: float) -> float:
    """float32'ye yuvarla — C'nin float islemini taklit etmek icin."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def derle(senaryo: str, sektor_adet: int = SEKTOR_ADET,
          ek: tuple[str, ...] = ()) -> Path:
    """ornek_kayit.c'yi TEK senaryo icin derle; UYARISIZ olmali.
    `sektor_adet` emule flasin sektor sayisi (NOR_SEKTOR_ADET); `ek` ek -D
    bayraklari (B72: -DKG__PARCA=256u, ESP32'deki okuma parcasi)."""
    anahtar = f"{senaryo}_{sektor_adet}" + "".join(ek)
    if anahtar in _ELF:
        return _ELF[anahtar]
    dosya = "".join(c if c.isalnum() or c == "_" else "_" for c in anahtar)
    elf = gecici.dizin("kayit_") / f"ornek_kayit_{dosya}.elf"
    d = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os",
         "-std=gnu11", "-Wall", "-Wextra", f"-DSENARYO_{senaryo}",
         f"-DKAYIT_SEKTOR={SEKTOR}UL", f"-DKAYIT_AZAMI_YUK={AZAMI_YUK}u",
         f"-DNOR_SEKTOR_ADET={sektor_adet}u", *ek,
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
        unix_s=0, kart_ms=1000, acilis=3, surum="B71-test", kal_no=7,
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
    ok("B71.B3 BASLA paketi C == Python (102 bayt: kalibrasyon kopyasi + numarasi)",
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
    # Son inceleme bulgu 6: bicim surumu yaziliyor, bilinmeyen tur reddedilmiyor.
    basla_c = bytes.fromhex(s["BASLA"][0])
    ok("B71.B12 BASLA bayt 2-3 = bicim surumu (2): kayit hangi bicimde yazildigini soyler",
       KB.SURUM == 2 and basla_c[2:4] == bytes([2, 0]) and len(basla_c) == 102,
       basla_c[2:4].hex())
    # 1B: surum 1 (98 B, kal_no yok) 1A-2 firmware'inin yazdiklari — okunmali
    v1 = bytearray(KB.basla_paketle(b)[:98])
    v1[2] = 1
    v1[3] = 0
    b1 = KB.basla_coz(bytes(v1))
    ok("B71.B14 surum 1 BASLA (98 B) Python'da cozulur: kal_no 0, kalibrasyon ayni",
       b1.bicim_surum == 1 and b1.kal_no == 0 and b1.kal == b.kal and b1.hiz_ms == b.hiz_ms,
       f"surum={b1.bicim_surum} kal_no={b1.kal_no}")
    bv = alanlar(kos(derle("SURUM"), NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)), "BV")
    ok("B71.B15 C'nin kg_basla_oku'su surum 2 VE surum 1 BASLA'yi okur (1A-2'de "
       "acilmis oturum yukseltmeden sonra DEVAM edebilsin)",
       bv == [["0", "2", "7", "250"], ["0", "1", "0", "250"]], str(bv))
    akis = (KB.kayit_paketle(KB.T_SAAT, 4, 0, bytes(12))
            + KB.kayit_paketle(9, 5, 0, b"\x01\x02")
            + KB.kayit_paketle(KB.T_SAAT, 6, 0, bytes(12)))
    kay: list = []
    try:
        kay = KB.akis_coz(akis)
    except ValueError:
        pass
    ok("B71.B13 bilinmeyen kayit turu (9) CRC'si dogruysa akis cozucu REDDETMEZ, dondurur",
       [k.tur for k in kay] == [KB.T_SAAT, 9, KB.T_SAAT], str([k.tur for k in kay]))
    _bicim_1c1(s)
    _bicim_1c2(s)
    _bicim_1c3(s)
    _bicim_1c4(s)


def _bicim_1c4(s: dict) -> None:
    """1C-4: OLAY PLAN + sebep 7 (ornek_kayit.c bicim_1c4 ile AYNI girdiler)."""
    c = bytes.fromhex(s["PLAN"][0]) if s.get("PLAN") else b""
    ko = getattr(KB, "KO_PLAN", -1)
    d = {"tur": ko, "kart_ms": 424242, "bas_unix": 1790000000, "sure_s": 21600, "hiz_ms": 60000,
         "plan_no": 3}
    ok("B71.B30 OLAY PLAN (8 B olay basi + bas_unix, sure_s, hiz_ms, plan_no) C == Python; coz",
       len(c) == 24 and ko == 5 and c == KB.olay_paketle(d) and KB.olay_coz(c) == d, c.hex())
    ok("B71.B31 BITIR sebep 7 = 'planli sure doldu' (C == Python)",
       (s.get("SEB7") or [""])[0] == "7" and KB.SEBEP.get(7) == "planli sure doldu",
       f"{s.get('SEB7')} {KB.SEBEP.get(7)}")


def _bicim_1c3(s: dict) -> None:
    """1C-3: SKOP kaydi + SKOP_KAL olayi (ornek_kayit.c bicim_1c3 ile AYNI girdiler)."""
    meta = {"t_ms": 123456, "sure_ms": 250, "hz": 83333, "tdiv_us": 200, "adim": 0.03125,
            "ofset": -1.25, "tetik": 1234, "esik": 2048, "histerezis": 300, "kip": 1,
            "tetiklendi": 1, "kenar": 0, "on_yuzde": 25, "onay": 2}   # histerezis > 255
    p0 = {"no": 7, "ilk": 0, "adet": 3, "toplam": 5, "parca": 0, "meta": meta,
          "kodlar": [0, 4095, 2048]}
    p1 = {"no": 7, "ilk": 3, "adet": 2, "toplam": 5, "parca": 1, "meta": None, "kodlar": [1, 4094]}
    mv = [-12, 120, 330, 541, 752, 963, 1174, 1385, 1596, 1807, 2018, 2229, 2440, 2651,
          2862, 3073, 3184]
    c0 = bytes.fromhex(s["SK0"][0]) if s.get("SK0") else b""
    c1 = bytes.fromhex(s["SK1"][0]) if s.get("SK1") else b""
    ck = bytes.fromhex(s["SKAL"][0]) if s.get("SKAL") else b""
    pk = getattr(KB, "skop_paketle", None)
    cz = getattr(KB, "skop_coz", None)
    ok("B71.B25 SKOP parcasi (12 B bas + 0. parcada 36 B META + u16 kodlar) ve SKOP_KAL olayi "
       "(17 x i16 mV) C == Python; coz -> ayni alanlar",
       len(c0) == 12 + 36 + 6 and len(c1) == 12 + 4 and pk is not None and cz is not None
       and c0 == pk(p0) and c1 == pk(p1) and cz(c0) == p0 and cz(c1) == p1
       and ck == KB.olay_paketle({"tur": getattr(KB, "KO_SKOP_KAL", -1), "kart_ms": 98765,
                                  "mv": mv})
       and KB.olay_coz(ck).get("mv") == mv, f"{c0.hex()} {c1.hex()} {ck.hex()}")
    t3 = [int(x) for x in (s.get("TUR3") or [])]
    ok("B71.B26 SKOP turu 10 (AZAMI 10), SKOP oturumu 3 C == Python; bicim surumu 2 KALDI",
       t3 == [10, 10, 3] and getattr(KB, "T_SKOP", 0) == 10 and getattr(KB, "OTURUM_SKOP", 0) == 3
       and KB.SURUM == 2, str(t3))
    # 🔴 1C-3 incelemesi: `no` bir oturumda TEKRARLANABILIR (Gtd + yeniden Gt,
    # DEVAM'dan sonra Gt) ve no'ya gore gruplama iki yakalamayi sessizce
    # birlestiriyordu. Yakalama artik KAYIT SIRASIYLA kurulur: 0. parca acar,
    # sonraki parca ancak hemen onceki acik yakalamaya (ayni no/toplam, ilk
    # kesintisiz) eklenir; skoplar anahtari 0. parcanin (ya da yetim parcanin) sirasi.
    T10 = getattr(KB, "T_SKOP", 10)
    kur = [KB.Kayit(T10, 18, 5, c1), KB.Kayit(T10, 19, 5, c0), KB.Kayit(T10, 21, 5, c1)]
    o = KB.oturumlari_kur(kur).get(5)
    sk = getattr(o, "skoplar", {}) if o else {}
    y, yetim = sk.get(19), sk.get(18)
    eksik = KB.oturumlari_kur(kur[1:2]).get(5)
    ye = getattr(eksik, "skoplar", {}).get(19) if eksik else None
    ok("B71.B27 yakalama KAYIT SIRASIYLA kurulur: 0. parca (19) + hemen sonraki 1. parca (21) "
       "tam, 5 kod, META; 0. parcadan ONCEKI 1. parca (18) yetim: tam degil, kodlar YOK; yalniz "
       "0. parca: tam=False",
       y is not None and y["tam"] and y["kodlar"] == [0, 4095, 2048, 1, 4094] and y["no"] == 7
       and y["meta"] == meta and yetim is not None and not yetim["tam"] and yetim["kodlar"] is None
       and ye is not None and not ye["tam"] and ye["kodlar"] is None,
       f"{sorted(sk)} {y and (y['tam'], y['kodlar'])} yetim={yetim and yetim['tam']} "
       f"eksik={ye and (ye['tam'], ye['kodlar'])}")
    m2 = dict(meta, t_ms=999)
    a = pk({"no": 7, "ilk": 0, "adet": 2, "toplam": 2, "parca": 0, "meta": meta, "kodlar": [10, 11]})
    b = pk({"no": 7, "ilk": 0, "adet": 2, "toplam": 2, "parca": 0, "meta": m2, "kodlar": [20, 21]})
    nk = KB.Kayit(KB.T_NOKTA, 42, 5, bytes(4 + KB.NOKTA_BAYT))
    o2 = KB.oturumlari_kur([KB.Kayit(T10, 30, 5, a), KB.Kayit(T10, 31, 5, b),
                            KB.Kayit(T10, 41, 5, c0), nk, KB.Kayit(T10, 43, 5, c1)]).get(5)
    s2 = getattr(o2, "skoplar", {}) if o2 else {}
    ok("B71.B29 ayni `no` ile IKI yakalama ayri kalir (kodlar ve META kendi); arada baska "
       "kayit giren parca bagli sayilmaz (yarim yakalama tam DEGIL)",
       sorted(s2) == [30, 31, 41, 43] and s2[30]["kodlar"] == [10, 11] and s2[31]["kodlar"] == [20, 21]
       and s2[30]["meta"]["t_ms"] == 123456 and s2[31]["meta"]["t_ms"] == 999
       and not s2[41]["tam"] and not s2[43]["tam"],
       f"{sorted(s2)} {[(k, v['tam'], v['kodlar']) for k, v in s2.items()]}")
    ikili = KB.skop_ikili(y) if y is not None and hasattr(KB, "skop_ikili") else b""
    ok("B71.B28 skop_ikili: /skop.bin bicimi (S3B, surum 1, adet, hz, adim, ofset, tdiv, tetik, "
       "kip, tetiklendi, sira) + u16 kodlar; eksik yakalama icin None",
       len(ikili) == 32 + 10 and ikili[0:4] == b"S3B\x01"
       and struct.unpack_from("<H", ikili, 4)[0] == 5
       and struct.unpack_from("<I", ikili, 8)[0] == 83333
       and struct.unpack_from("<ff", ikili, 12) == (0.03125, -1.25)
       and struct.unpack_from("<I", ikili, 20)[0] == 200
       and struct.unpack_from("<H", ikili, 24)[0] == 1234 and ikili[26] == 1 and ikili[27] == 1
       and struct.unpack_from("<I", ikili, 28)[0] == 7
       and list(struct.unpack_from("<5H", ikili, 32)) == [0, 4095, 2048, 1, 4094]
       and (ye is None or KB.skop_ikili(ye) is None), ikili[:32].hex())


def _bicim_1c2(s: dict) -> None:
    """1C-2: AYRINTI kaydi (ornek_kayit.c bicim_1c2 ile AYNI girdiler)."""
    ay = {"ilk": 1000, "t0_ms": 123456, "t0_us": 4000000000,
          "bayrak": KB.KA_KAYIP_ONCE | KB.KA_SILME,
          "ornekler": [(1234, -567, 0, KB.KAO_YUKSEK),
                       (-32768, 32767, 500, KB.KAO_V_HATA | KB.KAO_V_DOYDU),
                       (0, 0, 4095, KB.KAO_I_HATA)]}
    c_ay = bytes.fromhex(s["AY"][0]) if s.get("AY") else b""
    ok("B71.B22 AYRINTI (16 B bas + 3 x 6 B; dt4 4095 ve butun ornek bayraklari) C == "
       "Python; coz -> ayni alanlar",
       len(c_ay) == 34 and c_ay == KB.ayrinti_paketle(ay) and KB.ayrinti_coz(c_ay) == ay,
       c_ay.hex())
    t2 = [int(x) for x in (s.get("TUR2") or [])]
    ok("B71.B23 AYRINTI turu 9 (AZAMI >= 9; 1C-3'te 10) C == Python; bicim surumu 2 KALDI",
       len(t2) == 2 and t2[0] == 9 and t2[1] >= 9 and KB.T_AYRINTI == 9 and KB.SURUM == 2,
       str(t2))
    # ayrinti_ornekler: mutlak zaman micros() sarmasinda da dogru (t0_ms'den)
    gercek = 2**32 - 3000                       # micros sarmadan 3 ms once
    o = KB.Oturum(7)
    o.ayrinti = [
        {"ilk": 0, "t0_ms": gercek // 1000, "t0_us": gercek % 2**32, "bayrak": 0, "sira": 5,
         "ornekler": [(1, 2, 0, 0), (3, 4, 500, 1), (5, 6, 500, 0)]},
        {"ilk": 3, "t0_ms": (gercek + 30000) // 1000, "t0_us": (gercek + 30000) % 2**32,
         "bayrak": KB.KA_SILME, "sira": 6, "ornekler": [(7, 8, 0, 8)]},
        {"ilk": 4, "t0_ms": 700, "t0_us": 700_123, "bayrak": 0, "sira": 9,
         "ornekler": [(9, 10, 0, 0), (11, 12, 500, 0)]}]
    o.devamlar = [{"nokta_sira": 4, "kart_ms": 650}]     # ornek 4'ten itibaren YENI acilis
    beklenen = [(0, gercek, 1, 2, 0, 0), (1, gercek + 2000, 3, 4, 1, 0),
                (2, gercek + 4000, 5, 6, 0, 0), (3, gercek + 30000, 7, 8, 8, 0),
                (4, 700_123, 9, 10, 0, 1), (5, 702_123, 11, 12, 0, 1)]
    ok("B71.B24 ayrinti_ornekler: sira, mutlak mikrosaniye (t0_ms ile 32 bit sarmasi "
       "cozulur), kod, bayrak ve ACILIS (DEVAM'dan sonra saat yeni acilisin); boslukta "
       "yeni kaydin t0'i",
       KB.ayrinti_ornekler(o) == beklenen, str(KB.ayrinti_ornekler(o)))


def _bicim_1c1(s: dict) -> None:
    """1C-1: OLAY ve NOT kayitlari (ornek_kayit.c bicim_1c1 ile AYNI girdiler)."""
    ayar = {"tur": KB.KO_PIL_AYAR, "kart_ms": 1234, "kesme_v": 3.0, "ocv": 4.1875,
            "azami_s": 86400, "dcir_aralik_ms": 300000, "dcir_ms": 200, "kayit_hz": 1.0}
    dcir = {"tur": KB.KO_DCIR, "kart_ms": 300123, "no": 1, "v_once": 3.875, "i_once": 1.25,
            "v_ani": 3.75, "v_oturmus": 3.6875, "r_ani": 0.09375, "r_oturmus": 0.15625,
            "mah": 104.5, "wh": 0.40625}
    sonuc = {"tur": KB.KO_PIL_SONUC, "kart_ms": 3600000, "durum": 2, "hata": 0,
             "mah": 2512.25, "wh": 9.125, "ocv": 4.1875, "v_son": 2.9921875,
             "sure_ms": 3599000, "dcir_sayisi": 12}
    c = {a: bytes.fromhex(s[a][0]) if a in s and s[a] else b"" for a in ("OA", "OD", "OS", "NT")}
    ok("B71.B16 OLAY paketleri (PIL_AYAR 32 B, DCIR 44 B, PIL_SONUC 36 B) C == Python; "
       "Python coz -> ayni alanlar",
       c["OA"] == KB.olay_paketle(ayar) and c["OD"] == KB.olay_paketle(dcir)
       and c["OS"] == KB.olay_paketle(sonuc) and [len(c[a]) for a in ("OA", "OD", "OS")] == [32, 44, 36]
       and KB.olay_coz(c["OA"]) == ayar and KB.olay_coz(c["OD"]) == dcir
       and KB.olay_coz(c["OS"]) == sonuc, f"{[len(c[a]) for a in ('OA', 'OD', 'OS')]}")
    ham = b'\xc5\x9f\xc3\xb6nt "de\xc4\x9fi\xc5\x9fti" \\ \x01a\xfe'
    temiz = _not_bekle(ham, 121)
    ok("B71.B16b NOT paketi C == Python: hedef, alan, nokta_ms, degistirir + TEMIZLENMIS "
       "metin (gecersiz UTF-8, cift tirnak, ters bolu, kontrol karakteri atilir)",
       c["NT"] == KB.not_paketle(42, KB.KNT_NOT, 5000, 0, temiz)
       and KB.not_coz(c["NT"]) == {"hedef": 42, "alan": KB.KNT_NOT, "nokta_ms": 5000,
                                   "degistirir": 0, "metin": temiz.decode("utf-8")},
       f"{c['NT'][16:]!r} beklenen {temiz!r}")
    nt2 = int((s.get("NT2") or ["0"])[0])
    nt3 = (s.get("NT3") or ["0", "0"])
    ok("B71.B17 not metni en fazla 120 bayt, KARAKTER sinirinda: 118 a + 'ş' sigar (136 B), "
       "119 a + 'ş' sigmaz -> 119 a (135 B)",
       nt2 == 16 + 120 and int(nt3[0]) == 16 + 119 and int(nt3[1]) == ord("a")
       and len(_not_bekle(b"a" * 118 + "ş".encode(), 121)) == 120
       and len(_not_bekle(b"a" * 119 + "ş".encode(), 121)) == 119, f"NT2={nt2} NT3={nt3}")
    # sentetik akis: oturum 5 + olaylar + ad/etiket/not (oturum 0 basligiyla)
    b = basla_uret(100)
    nt = lambda alan, metin, deg=0, ms=0: KB.not_paketle(5, alan, ms, deg, metin.encode())
    akis = [KB.kayit_paketle(KB.T_BASLA, 5, 5, KB.basla_paketle(b)),
            KB.kayit_paketle(KB.T_OLAY, 6, 5, KB.olay_paketle(ayar)),
            KB.kayit_paketle(KB.T_NOT, 7, 0, nt(KB.KNT_AD, "ilk ad")),
            KB.kayit_paketle(KB.T_OLAY, 8, 5, KB.olay_paketle(dcir)),
            KB.kayit_paketle(KB.T_NOT, 9, 0, nt(KB.KNT_AD, "son ad")),
            KB.kayit_paketle(KB.T_NOT, 10, 0, nt(KB.KNT_NOT, "n1", 0, 1500)),
            KB.kayit_paketle(KB.T_NOT, 11, 0, nt(KB.KNT_NOT, "n2")),
            KB.kayit_paketle(KB.T_NOT, 12, 0, nt(KB.KNT_ETIKET, "18650, samsung ,")),
            KB.kayit_paketle(KB.T_NOT, 13, 0, nt(KB.KNT_NOT, "n1 duzeltildi", 10, 0)),
            KB.kayit_paketle(KB.T_NOT, 14, 0, nt(KB.KNT_NOT, "", 11)),
            KB.kayit_paketle(KB.T_NOT, 16, 0, nt(KB.KNT_NOT, "hayalet", 99)),
            KB.kayit_paketle(KB.T_NOT, 17, 0, nt(KB.KNT_NOT, "yine hayalet", 13)),
            KB.kayit_paketle(KB.T_OLAY, 15, 5, KB.olay_paketle(sonuc))]
    ot = KB.oturumlari_kur(KB.akis_coz(b"".join(akis)))
    o = ot.get(5)
    ok("B71.B18 oturumlari_kur: olaylar sirayla; ad = SON ad; etiketler virgulden; not "
       "degistirilir (nokta_ms 0: grafik yeri KORUNUR) ve bos metinle SILINIR; bilinmeyen "
       "ya da duzeltme kaydinin sirasi hayalet not URETMEZ; oturum 0 baslikli NOT hedefe "
       "baglanir",
       o is not None and [x["tur"] for x in o.olaylar] == [1, 2, 3]
       and o.ad == "son ad" and o.etiketler == ["18650", "samsung"]
       and o.notlar == {10: {"nokta_ms": 1500, "metin": "n1 duzeltildi"}} and 0 not in ot,
       f"{o and (o.ad, o.etiketler, o.notlar, [x['tur'] for x in o.olaylar])}")
    nk = {int(a[2:]): v for a, v in s.items() if a.startswith("NK") and a[2:].isdigit()}
    h = lambda t: t.encode("utf-8").hex()
    beklenen_nk = {   # kod hedef ms degistirir alan metin(hex)  (kod: 0 tamam, 1 oturum,
        0: ["0", "12", "0", "0", "1", h("ad")],   #  2 sira, 3 zaman, 4 metin, 5 alt)
        1: ["0", "12", "0", "0", "1"], 2: ["1", "0", "0", "0", "1"], 3: ["1", "0", "0", "0", "1"],
        4: ["1", "0", "0", "0", "1"], 5: ["4", "12", "0", "0", "1"],
        6: ["0", "7", "0", "0", "2", h("a, b")], 7: ["0", "5", "0", "0", "3", h("not")],
        8: ["4", "5", "0", "0", "3"], 9: ["0", "5", "1500", "0", "3", h("not")],
        10: ["3", "5", "0", "0", "3"], 11: ["3", "5", "0", "0", "3"],
        12: ["0", "5", "0", "7", "3"], 13: ["0", "5", "1500", "7", "3", h("yeni")],
        14: ["2", "5", "0", "0", "3"], 15: ["2", "5", "0", "0", "3"], 16: ["2", "5", "0", "0", "3"],
        17: ["1", "0", "0", "0", "3"], 18: ["5", "0", "0", "0", "0"],
        19: ["0", "4294967295", "4294967295", "0", "3", h("son")]}
    ok("B71.B21 Ga/Ge/Gn/Gx ayristirici: sayilar YALNIZ rakam (isaret, bosluk, bos, 32 bit "
       "tasmasi, 0 oturum/sira REDDEDILIR — strtoul hepsini kabul ediyordu); Gn metni "
       "zorunlu; Gx ':' + sira; '@' sonrasi rakam",
       nk == beklenen_nk, str({j: v for j, v in nk.items() if beklenen_nk.get(j) != v}))
    kn = (s.get("KN") or ["0", "0"])
    ok("B71.B19 KN_DCIR (0x40) diger nokta bayraklariyla CAKISMAZ; Python'da ayni",
       int(kn[0]) == 0x40 == KB.KN_DCIR and not (int(kn[0]) & int(kn[1])), str(kn))
    tur = [int(x) for x in (s.get("TUR") or [])]
    ok("B71.B20 yeni turler C == Python: OLAY 7, NOT 8 (AZAMI >= 8), PIL oturumu 2, sebepler "
       "4/5/6; bicim surumu 2 KALDI (BASLA baytlari degismedi)",
       len(tur) == 7 and tur[:2] == [7, 8] and tur[2] >= 8 and tur[3:] == [2, 4, 5, 6]
       and [KB.T_OLAY, KB.T_NOT, KB.OTURUM_PIL] == [7, 8, 2]
       and all(k in KB.SEBEP for k in (4, 5, 6)) and KB.SURUM == 2, str(tur))


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
        elif p[:1] and p[0] in ("S1", "S2", "S3", "S4", "S5"):
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
    s5 = [beklenen(100 * (m + 1),
                   [(100 + j, -j, j * 0.5) for j in range(10 * m, 10 * m + 10)],
                   bayrak=(0, KB.KN_DCIR, KB.KN_DCIR)[m])
          for m in range(3)]
    ok("B71.P6 (1C-1) DCIR bayragi ornegin AIT OLDUGU noktada: sinirdaki ornek onceki "
       "noktayi kapatir, bayragi YENISINE verir (1. nokta temiz)",
       gruplar.get("S5") == s5, str([p.bayrak for p in gruplar.get("S5", [])]))


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
    tek = {p[0]: p[1:] for p in (x.split() for x in sat)
           if p and p[0] in ("RED", "ONAY", "EK9", "ACHATA", "ACHATA2", "YAZHATA")}
    oku = alanlar(sat, "OKU")
    veri = [bytes.fromhex(p[0]) if p else b"" for p in alanlar(sat, "VERI")]
    d = {a: _durum(sat, a) for a in [f"G{i}" for i in range(1, 15)] + ["G5b"]}
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
    ok("B71.G6 sahte buyuk onay (sonraki siradan buyuk) REDDEDILDI: onay 0, bellek hala dolu",
       tek.get("RED") == ["-2"]
       and d["G5"] == _g(34, 7, 464, dolu=1, kull=4048, onaysiz=4048),
       f"{tek.get('RED')} {d['G5']}")
    ok("B71.G6b gecerli onay kabul; yeniden acilista onay_taban ile KORUNUR (dolu sayilmaz)",
       tek.get("ONAY") == ["0"]
       and d["G5b"] == _g(34, 7, 464, onay=33, kull=4048, onaysiz=0), str(d["G5b"]))
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
    kay9 = KB.akis_coz(veri[4]) if len(veri) > 4 else []
    # 🔴 1C-2: tur 9 AYRINTI oldu; bu iddia 9 ile BOS kaliyordu (tam mutasyon
    # kosusu yakaladi: `> KAYIT_T_AZAMI` reddi yesildi). Bilinmeyen tur 200.
    ok("B71.G16 bilinmeyen kayit turu (200) gecerli: tarama durmaz, esitleme onu tasir",
       tek.get("EK9") == ["37"]
       and d["G12"] == _g(38, 1, 56, bozuk=2, kull=568, onaysiz=568)
       and [k.tur for k in kay9] == [200], f"{d['G12']} {[k.tur for k in kay9]}")
    ok("B71.G17 okuma hatasinda kg_ac acmayi REDDEDER (KG_HATA); tekrar denemede durum ayni",
       tek.get("ACHATA") == ["-2"] and tek.get("ACHATA2") == ["-2"]
       and d["G13"] == d["G12"],
       f"1.gecis={tek.get('ACHATA')} 2.gecis={tek.get('ACHATA2')} {d['G13']}")
    tum, _ = KB.flas_coz(bytes(flas.bellek), SEKTOR)
    siralar = [k.sira for k in tum]
    ok("B71.G18 yarim kalan yazmada sira HARCANIR: hata sonrasi yeni sira, flasta tekrar yok",
       tek.get("YAZHATA") == ["-2"] and ek[6:7] == [39]
       and len(siralar) == len(set(siralar))
       and d["G14"] == _g(40, 2, 28, bozuk=2, kull=1052, onaysiz=1052),
       f"YAZHATA={tek.get('YAZHATA')} EK={ek[6:7]} "
       f"tekrar={len(siralar) - len(set(siralar))} {d['G14']}")


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


def bitir_payi_korunur(bellek: bytes) -> bool:
    """BITIR disinda hicbir kayit sektorun son 24 baytina (KY_BITIR_PAY)
    tasmaz: bellek onaysiz veriyle dolunca BITIR(DOLU) HER ZAMAN yazilabilir.
    (Mutasyon B71 bunu ilk kosuda KACIRMISTI: pay kaldirilinca BITIR cogu
    zaman tesadufen kuyruga sigiyordu; kural sonuctan degil yerlesimden
    olculmeli.)"""
    pay = KB.BASLIK_BAYT + 8
    kayitlar, _ = KB.flas_coz(bellek, SEKTOR)
    return bool(kayitlar) and all(
        k.tur == KB.T_BITIR
        or (k.adres % SEKTOR) + KB.toplam_bayt(len(k.yuk)) + pay <= SEKTOR
        for k in kayitlar)


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
    ok("B71.Y14 BITIR payi: BITIR disinda hicbir kayit sektorun son 24 baytina girmez",
       bitir_payi_korunur(bellek))


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


# ── B71.M · mantiksal bicimleme ───────────────────────────────────────
def _dm(sat: list[str], ad: str) -> dict:
    for s in sat:
        p = s.split()
        if p and p[0] == ad:
            return {k: int(v) for k, v in (x.split("=") for x in p[1:])}
    return {}


def bolum_mantiksal() -> None:
    """B72 son inceleme O4: dolu bolumde fiziksel bicimleme 2912 x ~25 ms =
    ~73 s surup kayit kilidini tutuyor, web sunucusunu (p0 dahil) donduruyordu.
    Bicimleme artik NVS'e TABAN yazmak: tabanin altindaki her kayit yok
    sayilir; silme arka planda ya da sil-sonra-kullan ile."""
    print("\n── B71.M  mantiksal bicimleme (taban) + arka plan temizligi")
    flas = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    sat = kos(derle("MANTIKSAL"), flas)
    m = {a: _dm(sat, a) for a in ("M1", "M2", "M3", "M4", "M5", "M6", "M7")}
    ok_ = {a: alanlar(sat, a) for a in ("OK2", "OK3", "OK4", "OK5", "OK6", "OK7")}
    kay = 3 * KB.toplam_bayt(100)
    ok("B71.M1 bicimleme aninda: tablo/dizin bos, onay = taban-1, kafa kapali, okuma bos",
       m["M2"].get("kull") == 0 and m["M2"].get("dizin") == 0
       and m["M2"].get("onay") == m["M1"].get("sonraki", 0) - 1
       and m["M2"].get("ofset") == SEKTOR and ok_["OK2"] == [["0", "0", "0"]],
       f"{m['M2']} {ok_['OK2']}")
    ok("B71.M2 bicimlemeden sonraki kayit TAZE sektore gider, sira tabandan surer",
       m["M3"].get("bas") != m["M1"].get("bas") and m["M3"].get("ofset") == kay
       and ok_["OK3"] == [[str(kay), "13", "15"]], f"{m['M3']} {ok_['OK3']}")
    ok("B71.M3 yeniden acilista tabanin alti BOS sayilir, oturum listesine girmez",
       m["M4"].get("eski") == 3 and m["M4"].get("dizin") == 1
       and ok_["OK4"] == ok_["OK3"], f"{m['M4']} {ok_['OK4']}")
    bas5 = alanlar(sat, "BAS5")
    ok("B71.M4 arka plan temizligi yalniz eski sektorleri siler, canliya dokunmaz",
       alanlar(sat, "TEMIZ") == [["3"]]
       and bas5 == [["ff", "ff", "ff", "a5", "ff", "ff", "ff", "ff"]]
       and ok_["OK5"] == ok_["OK3"], f"TEMIZ={alanlar(sat, 'TEMIZ')} {bas5}")
    ok("B71.M5 taban yazilip RAM'e gecmeden kesilen bicimleme de tutarli: eski "
       "gorunmez, sira tabandan, yeni kayit eski kafanin ARKASINA yazilmaz",
       m["M6"].get("kull") == 0 and m["M6"].get("dizin") == 0
       and m["M6"].get("sonraki") == 16 and m["M6"].get("ofset") == SEKTOR
       and ok_["OK6"] == [["0", "0", "0"]]
       and m["M7"].get("bas") == 4 and ok_["OK7"] == [["28", "16", "16"]],
       f"{m['M6']} {m['M7']} {ok_['OK6']} {ok_['OK7']}")


# ── B71.V · kayit yoneticisi (kayit_yonet.h) ─────────────────────────
_DR = ["durum", "oturum", "sonraki", "onay", "kull", "hata", "kapat", "kimlik", "taban"]


def _dr(sat: list[str], ad: str) -> dict:
    for s in sat:
        p = s.split()
        if p and p[0] == ad and len(p) == len(_DR) + 1:
            return dict(zip(_DR, (int(x) for x in p[1:])))
    return {}


def _yonet(flas: NorFlas, elf: Path, adimlar: list[int]) -> list[list[str]]:
    """Her adim bir ACILIS: NVS ve flas kalici, program BITTI deyince
    elektrik kesilmis gibi biter."""
    cikti = []
    for a in adimlar:
        flas.nvs["t_adim"] = a
        cikti.append(kos(elf, flas))
    return cikti


def bolum_yonet() -> None:
    """B72 son inceleme O1-O5: kartin kayit durum makinesi ESP32'ye ozgu
    yapistiricidaydi ve HIC calistirilarak sinanmiyordu. Artik platformsuz
    (kayit_yonet.h, NVS islev tablosu) ve burada emule NVS + NOR ile
    acilistan acilisa sinaniyor."""
    print("\n── B71.V  kayit yoneticisi: DEVAM · durum 4 · durdurma niyeti · "
          "bicimleme · onay · kimlik")
    elf = derle("YONET")
    # A: kayit -> kesinti -> halka dolar + kafada yarim yazma -> Gd -> onay
    fa = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    fa.nvs["t_rast"] = 7
    a1, a2, a3 = _yonet(fa, elf, [1, 2, 3])
    nvs_kapat_3 = fa.nvs.get("kapat")        # 3. acilistan HEMEN sonra
    a4, a5 = _yonet(fa, elf, [4, 5])
    oid = _dr(a1, "D1").get("oturum")
    ok("B71.V1 kayit surerken elektrik kesilirse acilista AYNI oturum surer (DEVAM)",
       bool(oid) and _dr(a2, "D0").get("durum") == 2 and _dr(a2, "D0").get("oturum") == oid,
       f"{_dr(a1, 'D1')} -> {_dr(a2, 'D0')}")
    d30 = _dr(a3, "D0")
    ok("B71.V2 halka onaysiz dolu + kafa yarim: durum 4 (BEKLIYOR), bekleyen oturum gorunur",
       d30.get("durum") == 4 and d30.get("oturum") == oid, f"{d30}")
    ok("B71.V3 durum 4'te durdurma KAYBOLMAZ: niyet RAM'de ve NVS'te",
       _dr(a3, "D3").get("kapat") == oid and nvs_kapat_3 == oid,
       f"{_dr(a3, 'D3')} nvs={nvs_kapat_3}")
    ot = KB.oturumlari_kur(KB.flas_coz(bytes(fa.bellek), SEKTOR)[0]).get(oid)
    ok("B71.V4 niyet acilistan sonra da durur; onay yer acinca oturum BITIR(kullanici) "
       "ile KAPANIR, SURMEZ (tek DEVAM), sonraki acilis surdurmez",
       _dr(a4, "D0").get("durum") == 4 and _dr(a4, "D4").get("durum") == 1
       and _dr(a4, "D4").get("kapat") == 0 and fa.nvs.get("kapat") == 0
       and bool(ot) and bool(ot.bitir) and ot.bitir["sebep"] == 1 and len(ot.devamlar) == 1
       and _dr(a5, "D0").get("durum") == 1,
       f"D4={_dr(a4, 'D4')} bitir={ot and ot.bitir} devam={ot and len(ot.devamlar)} "
       f"D5={_dr(a5, 'D0')}")
    kim = {_dr(c, "D0").get("kimlik") for c in (a1, a2, a3, a4, a5)}
    (a14,) = _yonet(fa, elf, [14])
    ok("B71.V12 acilista onay NVS'ten gelir: onaylanmis eski veri silinip YENI kayda "
       "yer acar (onay RAM'de kalsaydi kart ~1 sektor sonra DOLU derdi)",
       alanlar(a14, "YAZ") == [["0"]] and _dr(a14, "D14").get("durum") == 2
       and fa.nvs.get("onay", 0) > 0, f"YAZ={alanlar(a14, 'YAZ')} D14={_dr(a14, 'D14')}")
    # B: ayni, durdurma YOK -> onay gelince SURER
    fb = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    b1, b2, b6 = _yonet(fb, elf, [1, 2, 6])
    bid = _dr(b1, "D1").get("oturum")
    otb = KB.oturumlari_kur(KB.flas_coz(bytes(fb.bellek), SEKTOR)[0]).get(bid)
    ok("B71.V5 durdurma yoksa onay yer acinca oturum SURER (ikinci DEVAM), kapanmaz",
       _dr(b6, "D6").get("durum") == 2 and _dr(b6, "D6").get("oturum") == bid
       and bool(otb) and len(otb.devamlar) == 2 and not otb.bitir,
       f"D6={_dr(b6, 'D6')} devam={otb and len(otb.devamlar)} bitir={otb and otb.bitir}")
    # C: durum 4'te YENI kayit istenirse eski oturum kapatilacak, surdurulmeyecek
    fc = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    c1, c2, c13, c4 = _yonet(fc, elf, [1, 2, 13, 4])
    cid = _dr(c1, "D1").get("oturum")
    otc = KB.oturumlari_kur(KB.flas_coz(bytes(fc.bellek), SEKTOR)[0]).get(cid)
    ok("B71.V6 durum 4'te yeni kayit: yer yoksa reddedilir ve ESKI oturum kapatma "
       "niyetine alinir; onayda eski BITIR(kullanici), surmez",
       alanlar(c13, "BAS") == [["-1"]] and _dr(c13, "D13").get("kapat") == cid
       and bool(otc) and bool(otc.bitir) and otc.bitir["sebep"] == 1
       and len(otc.devamlar) == 1,
       f"BAS={alanlar(c13, 'BAS')} D13={_dr(c13, 'D13')} bitir={otc and otc.bitir}")
    # F: bicimleme mantiksal + atomik + arka planda temizlik
    ff = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    f7, f8 = _yonet(ff, elf, [7, 8])
    d7a, d7b, d80 = _dr(f7, "D7a"), _dr(f7, "D7b"), _dr(f8, "D0")
    ok("B71.V7 bicimleme: taban NVS'e yazilir, kayit durur, tablo bos; ardindan yeni kayit",
       alanlar(f7, "BIC") == [["0"]] and d7a.get("durum") == 1 and d7a.get("kull") == 0
       and ff.nvs.get("taban") == d7a.get("taban") and d7b.get("durum") == 2,
       f"D7a={d7a} D7b={d7b} nvs.taban={ff.nvs.get('taban')}")
    sb = [x for x in (s.split() for s in f8) if x[:1] == ["SB"]]
    temiz = all(int(x[2]) == 255 for x in sb if x[3] == "0")
    # 🔴 mutasyon: ilk surum yalniz "eskiler 0xFF mi" diyordu; CANLI sektor
    # korumasi kaldirilsa da yesildi (kafa ikinci bir korumayla guvende)
    canli = [x for x in sb if x[3] == "1"]
    canli_saglam = len(canli) >= 2 and all(int(x[2]) == 0xA5 for x in canli)
    ok("B71.V8 yeniden acilis: eski oturum gorunmez, yeni oturum surer; arka plan "
       "temizligi bitince canli olmayan her sektor 0xFF, CANLI sektorler (kafa "
       "disindakiler dahil) saglam",
       d80.get("durum") == 2 and d80.get("oturum") == d7b.get("oturum")
       and d80.get("taban") == d7a.get("taban") and len(sb) == SEKTOR_ADET and temiz
       and canli_saglam and _dr(f8, "D8").get("kull", 0) > 0,
       f"D0={d80} SB={[(x[1], x[2], x[3]) for x in sb]}")
    tur = int((alanlar(f8, "TUR") or [["0"]])[0][0])
    ilerleme = int((alanlar(f8, "ILERLEME") or [["0"]])[0][0])
    ok("B71.V13 arka plan silmeleri ARALIKLI (KYN_TEMIZ_MS): dolu sektor silme ~25 ms "
       "iki cekirdegi durdurur, art arda silme olcumu bogmasin",
       ilerleme >= 2 and tur >= 3 * ilerleme, f"tur={tur} ilerleme={ilerleme}")
    # H: taban NVS'e yazilamazsa bicimleme IPTAL
    fh = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    fh.nvs_hata = {"taban"}
    (h9,) = _yonet(fh, elf, [9])
    ok("B71.V9 taban NVS'e yazilamazsa bicimleme IPTAL: veri yerinde, hata raporlu",
       alanlar(h9, "BIC") == [["-2"]] and _dr(h9, "D9b").get("kull") == _dr(h9, "D9a").get("kull")
       and _dr(h9, "D9a").get("kull", 0) > 0 and _dr(h9, "D9b").get("hata") == 2,
       f"{alanlar(h9, 'BIC')} {_dr(h9, 'D9a')} {_dr(h9, 'D9b')}")
    # L: onay son gelen kazanir, sahte onay reddedilir
    fl = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    (l12,) = _yonet(fl, elf, [12])
    ok("B71.V10 onay: son gelen kazanir, geriye onay yok sayilir, sahte onay reddedilir",
       [_dr(l12, a).get("onay") for a in ("D12a", "D12b", "D12c")] == [5, 5, 5]
       and _dr(l12, "D12c").get("hata") == 2, str([_dr(l12, a) for a in ("D12a", "D12b", "D12c")]))
    # K: kimlik (akis kimligi) — NVS ya da flas kaybolunca DEGISIR
    fa.nvs = {"t_rast": 99}                  # NVS kayboldu (tam silme / eski yedek)
    (k0,) = _yonet(fa, elf, [0])
    kim_nvs = _dr(k0, "D0").get("kimlik")
    kim_b = _dr(b6, "D0").get("kimlik")      # B: onay NVS'e yazildi (b6)
    fb.nvs["t_rast"] = 1234
    fb.bellek[:] = b"\xff" * len(fb.bellek)  # flas bolumu kayboldu, NVS duruyor
    (k1,) = _yonet(fb, elf, [0])
    ok("B71.V11 akis kimligi acilislar boyunca SABIT; NVS kaybolunca da, flas "
       "kaybolup NVS kalinca da DEGISIR (PC eski akisa eklemesin)",
       len(kim) == 1 and None not in kim and kim_nvs not in kim
       and fb.nvs.get("onay", 0) > 0 and _dr(k1, "D0").get("kimlik") not in (kim_b, None),
       f"A={kim} nvs_kaybi={kim_nvs} B={kim_b} flas_kaybi={_dr(k1, 'D0').get('kimlik')} "
       f"B.nvs.onay={fb.nvs.get('onay')}")


# ── B71.A · ayrintili kip yazicisi (1C-2) ────────────────────────────
AYR_SEKTOR = 16


def _ayr_uret(k: int) -> tuple[int, int, int, int, int]:
    """ornek_kayit.c ayr_uret ile AYNI: (us, ms, v, i, bayrak). k >= 400: DEVAM'dan
    sonraki YENI acilisin saati."""
    if k >= 400:
        us = 500_000 + 2000 * (k - 400)
    else:
        us = 1_000_000 + 2000 * k + (30000 if k >= 100 else 0) + (20000 if k >= 250 else 0)
    us = us + (k * 37) % 401 - 200
    b = (k // 50) & 0xF
    return us, us // 1000, k * 13 - 500, -(k * 7), b


def bolum_ayrinti() -> None:
    """1C-2: ayrintili kip (hiz_ms 0) — her ornek AYRINTI kayitlarinda. Zaman
    4 us nicemli, <= 2 us sapma, bolmede birikmez; bosluk ve kayip yeni kayit;
    sektor sonu bosa gitmez; elektrik kesilince DEVAM, sira kesintisiz."""
    print("\n── B71.A  ayrintili kip: ornek · zaman · bosluk · bolme · DEVAM")
    elf = derle("AYRINTI", AYR_SEKTOR)
    fl = NorFlas(SEKTOR * AYR_SEKTOR, sektor=SEKTOR)
    fl.nvs["t_rast"] = 11
    a1, a2 = _yonet(fl, elf, [1, 2])
    kay, bozuk = KB.flas_coz(bytes(fl.bellek), SEKTOR)
    ot = KB.oturumlari_kur(kay)
    oid = _say(a1, "BAS")
    o = ot.get(oid)
    orn = KB.ayrinti_ornekler(o) if o else []
    # beslenen (k=299 dustu) ve kartta kalan ornekler: asama 1'in bosaltilmamis
    # kuyrugu (elektrik kesildi) gider, sira KESINTISIZ surer
    beslenen = [k for k in range(640) if k != 299]
    kalan1 = sum(len(r["ornekler"]) for r in o.ayrinti if r["sira"] < min(
        (d_s for d_s in [x.sira for x in kay if x.oturum == oid and x.tur == KB.T_DEVAM]),
        default=10**9)) if o else 0
    eslesen = beslenen[:kalan1] + beslenen[beslenen.index(400):] if o else []
    hata_kod, hata_t, hata_ac = [], [], []
    for (sira, t, v, i, b, ac), k in zip(orn, eslesen):
        us, ms, vv, ii, bb = _ayr_uret(k)
        if (v, i, b) != (vv, ii, bb):
            hata_kod.append((sira, k))
        if abs(t - us) > 2:
            hata_t.append((sira, k, t - us))
        if ac != (1 if k >= 400 else 0):
            hata_ac.append((sira, k, ac))
    artan = all(a[1] < b[1] for a, b in zip(orn, orn[1:]) if a[5] == b[5])
    ok("B71.A1 her ornek sirasi, ham V/I kodu ve bayragi BIREBIR (PC'de kurulan); durdurulurken "
       "tamponda kalan kuyruk da flasta",
       bool(orn) and len(orn) == len(eslesen) and [s for s, *_ in orn] == list(range(len(orn)))
       and not hata_kod, f"{len(orn)}/{len(eslesen)} hata={hata_kod[:3]}")
    # 🔴 son inceleme: uretec DEVAM'da saati SURDURUYORDU (gercekte micros sifirlanir)
    # ve PC iki acilisin saatini tek listede karistiriyordu. Asama 2 artik yeni
    # acilisin saatiyle; her ornek hangi ACILIS'ta oldugunu tasir.
    ok("B71.A2 her ornegin kurulan zamani KENDI ACILISININ micros'undan <= 2 us (4 us nicem, "
       "bolmelerde birikmez); DEVAM'dan sonraki ornekler acilis 1, zaman her acilista artan",
       bool(orn) and not hata_t and not hata_ac and artan,
       f"{hata_t[:3]} en buyuk {max((abs(x[2]) for x in hata_t), default=0)} acilis={hata_ac[:3]} "
       f"artan={artan}")
    bas_k = {r["ilk"]: r for r in o.ayrinti} if o else {}
    def kayit_basi(k):
        j = eslesen.index(k) if k in eslesen else -1
        return bas_k.get(j)
    r100, r250 = kayit_basi(100), kayit_basi(250)
    ok("B71.A3 16.38 ms'yi asan bosluk YENI kayit acar; kaydin t0_us'u o ornegin zamani",
       r100 is not None and r250 is not None
       and abs(r100["t0_us"] - _ayr_uret(100)[0]) <= 2 and abs(r250["t0_us"] - _ayr_uret(250)[0]) <= 2
       and r100["ornekler"][0][2] == 0,
       f"r100={r100 and r100['t0_us']} r250={r250 and r250['t0_us']}")
    r300 = kayit_basi(300)
    ok("B71.A4 dusen ornekten (halka tasti) sonraki ornek YENI kayit acar, kayit KA_KAYIP_ONCE",
       r300 is not None and r300["bayrak"] & KB.KA_KAYIP_ONCE
       and all(not r["bayrak"] & KB.KA_KAYIP_ONCE for r in o.ayrinti if r is not r300),
       f"{r300 and r300['bayrak']}")
    en_az = KB.BASLIK_BAYT + 16 + 8 * 6 + KB.BASLIK_BAYT + 8
    sektorler: dict[int, int] = {}
    for x in kay:
        s = x.adres // SEKTOR
        sektorler[s] = max(sektorler.get(s, 0), x.adres % SEKTOR + KB.toplam_bayt(len(x.yuk)))
    ayr_sek = {x.adres // SEKTOR for x in kay if x.tur == KB.T_AYRINTI}
    bas_sek = max(ayr_sek, key=lambda s: max(x.sira for x in kay if x.adres // SEKTOR == s)) if ayr_sek else -1
    bosa = {s: SEKTOR - u for s, u in sektorler.items() if s in ayr_sek and s != bas_sek}
    ok("B71.A5 sektor sonu bosa gitmez: sigmayan kayit BOLUNUR (en fazla bir asgari kayit "
       "kadar bos kalir)",
       bool(bosa) and all(v < en_az for v in bosa.values()), str(bosa))
    devam = [x for x in kay if x.oturum == oid and x.tur == KB.T_DEVAM]
    ilk_kay = sorted(o.ayrinti, key=lambda r: r["sira"]) if o else []
    zincir = all(a["ilk"] + len(a["ornekler"]) == b["ilk"] for a, b in zip(ilk_kay, ilk_kay[1:]))
    ok("B71.A6 elektrik kesilince DEVAM: ayrintili surer (hiz_ms 0), ornek sirasi KESINTISIZ; "
       "BITIR nokta_adedi = ornek sayisi",
       len(devam) == 1 and _say(a2, "AYR") == 1 and zincir and o.bitir is not None
       and o.bitir["nokta_adedi"] == len(orn) and o.bitir["sebep"] == 1,
       f"devam={len(devam)} zincir={zincir} bitir={o and o.bitir} n={len(orn)}")
    olcum = [x for x in ot.values() if x.id != oid and x.basla and x.basla.hiz_ms == 100]
    ok("B71.A7 ayrintili oturumda NOKTA yazilmaz, noktali oturumda ORNEK yazilmaz (KG_YOK)",
       _say(a1, "AYR") == 1 and _say(a1, "NK") == -4 and _say(a2, "AO") == -4
       and o is not None and not o.noktalar and len(olcum) == 1 and not olcum[0].ayrinti,
       f"AYR={_say(a1, 'AYR')} NK={_say(a1, 'NK')} AO={_say(a2, 'AO')}")
    ok("B71.A8 5 s bosaltma kurali ornek tamponunu da kapsar (4999 ms'de bekler, 5000'de yazar)",
       (_say(a2, "TAMP1") or 0) > 0 and _say(a2, "TAMP2") == _say(a2, "TAMP1")
       and _say(a2, "TAMP3") == 0 and (_say(a2, "TAMP4") or 0) > 0,
       f"{[_say(a2, a) for a in ('TAMP1', 'TAMP2', 'TAMP3')]}")
    ok("B71.A9 flas temiz: bozuk kayit yok, BITIR payi korunuyor, sektor kurali (TEKRAR)",
       bozuk == 0 and bitir_payi_korunur(bytes(fl.bellek)) and tekrar_kurali(bytes(fl.bellek)),
       f"bozuk={bozuk}")
    # son inceleme: bolunen kaydin kalani yazilamazsa tamponda kalir; sonraki
    # ornegin zaman farki YENI origine gore hesaplanmali (a_q -= top). Once bu
    # satir "olu kod" diye silinmisti — basari yolunda oyle, hata yolunda degil.
    fl3 = NorFlas(SEKTOR * AYR_SEKTOR, sektor=SEKTOR)
    fl3.nvs["t_rast"] = 13
    (a3,) = _yonet(fl3, elf, [3])
    kay3, _ = KB.flas_coz(bytes(fl3.bellek), SEKTOR)
    o3 = KB.oturumlari_kur(kay3).get(_say(a3, "BAS3"))
    R, k0, A = _say(a3, "R3") or 0, _say(a3, "K0") or 0, _say(a3, "A3") or 0
    t_son = 2_000_000 + 2000 * (k0 + A - 1)

    def a3_zaman(k: int) -> int | None:
        if k < k0 + A:
            return 2_000_000 + 2000 * k
        if k == k0 + A:
            return None                               # tetik: bosaltma hatasi, duser
        return t_son + R * 2000 + 5000 + 2000 * (k - (k0 + A + 1))
    o3_orn = KB.ayrinti_ornekler(o3) if o3 else []
    h3 = [(v - 3000, t - a3_zaman(v - 3000)) for _s, t, v, *_r in o3_orn
          if v - 3000 >= k0 and a3_zaman(v - 3000) is not None and abs(t - a3_zaman(v - 3000)) > 2]
    sonraki = k0 + A + 1 in {v - 3000 for _s, _t, v, *_r in o3_orn}
    ok("B71.A10 bolmeden sonra yazma HATASI: kalan tamponda kalir, sonraki ornegin zamani "
       "yine <= 2 us (a_q yeni origine tasinir)",
       8 <= R <= 36 and A > R and (_say(a3, "KALAN3") or 0) == A - R and sonraki and o3 is not None
       and not h3, f"R={R} A={A} KALAN={_say(a3, 'KALAN3')} sonraki={sonraki} hata={h3[:3]}")


# ── B71.Z · hazir alan: onayli sektorlerin onceden silinmesi (1C-2) ───
HZ_SEKTOR = 16


def _sektor_kayitlari(bellek: bytes, s: int) -> list:
    kay, _ = KB.flas_coz(bellek[s * SEKTOR:(s + 1) * SEKTOR], SEKTOR)
    return kay


def _silme_bosluk(o) -> tuple[list, dict]:
    """(KA_SILME kayitlari, {ilk_sira: onceki ornekten bosluk_us}) — her kaydin
    ilk orneginin onundeki zaman farki (ilk kayit haric)."""
    if o is None:
        return [], {}
    kl = sorted(o.ayrinti, key=lambda r: r["sira"])
    t = {s: us for s, us, *_ in KB.ayrinti_ornekler(o)}
    return ([r for r in kl if r["bayrak"] & KB.KA_SILME],
            {r["ilk"]: t[r["ilk"]] - t[r["ilk"] - 1] for r in kl if r["ilk"] - 1 in t})


def bolum_hazir() -> None:
    """1C-2: bosta (kayit yok, izin acik) onayli eski sektorler basin onunde
    sirayla ONCEDEN silinir (500 ms arayla); kafa bu sektorlere SILMEDEN gecer
    (dolu sektor silmesi iki cekirdegi ~25 ms durduruyor). Onaysiza, basa ve
    halka sarmasina dokunulmaz; acilista ve bicimlemede sayac sifir."""
    print("\n── B71.Z  hazir alan: on silme · kafa silmeden gecer · sinirlar")
    elf_a = derle("HAZIR", HZ_SEKTOR, ek=("-DKYN_HAZIR_HEDEF=5u",))
    fa = NorFlas(SEKTOR * HZ_SEKTOR, sektor=SEKTOR)
    fa.nvs["t_rast"] = 13
    z1, z2, z3 = _yonet(fa, elf_a, [1, 2, 3])
    kay, bozuk = KB.flas_coz(bytes(fa.bellek), SEKTOR)
    ok("B71.Z1 izin KAPALIYKEN on silme yok; izin acilinca KYN_TEMIZ_MS (kartta 500, testte 200 "
       "ms) dolmadan yok, sonra onayli "
       "sektorler sirayla hedefe (5) kadar silinir — her silme bir hazir sektor",
       _say(z1, "KAPALI") == 0 and _say(z2, "HZ4") == 0 and _say(z2, "HZ") == 5
       and _say(z2, "SIL2") == 5,
       f"KAPALI={_say(z1, 'KAPALI')} HZ4={_say(z2, 'HZ4')} HZ={_say(z2, 'HZ')} SIL2={_say(z2, 'SIL2')}")
    ayr = [o for o in KB.oturumlari_kur(kay).values() if o.basla and o.basla.hiz_ms == 0]
    ka2, bosluk2 = _silme_bosluk(ayr[0] if ayr else None)
    # 🔴 son inceleme: KA_SILME eskiden silmeyi YAPAN bosaltmadan sonraki kayda
    # konuyordu; o kayit halkada bekleyen (silmeden ONCE uretilmis) orneklerle
    # doluyordu ve bosluk ONDAN SONRA geliyordu. Artik cekirdek 1 silmeden sonra
    # urettigi ilk ornegi isaretler: bayrakli kayit bosluktan HEMEN sonra baslar.
    ok("B71.Z2 kafa HAZIR sektorlere gecerken SILME YOK (0); hazir bitince onayli dolu "
       "sektorler yeniden silinir; her kirli silme bir KA_SILME kaydi ve o kayit silme "
       "boslugundan (>= 25 ms) HEMEN SONRA baslar; bayraksiz kayit boslukla baslamaz",
       _say(z2, "HAZIRDA") == 0 and (_say(z2, "SONRA") or 0) > 0
       and (_say(z2, "KIRLI2") or 0) > 0 and len(ka2) == _say(z2, "KIRLI2")
       and all(bosluk2.get(r["ilk"], 0) >= 25000 for r in ka2)
       and not [s for s, b in bosluk2.items() if b >= 25000 and s not in {r["ilk"] for r in ka2}],
       f"HAZIRDA={_say(z2, 'HAZIRDA')} SONRA={_say(z2, 'SONRA')} KIRLI={_say(z2, 'KIRLI2')} "
       f"KA_SILME {len(ka2)}={[(r['ilk'], bosluk2.get(r['ilk'])) for r in ka2][:4]} "
       f"bayraksiz_bosluk={[s for s, b in bosluk2.items() if b >= 25000 and s not in {r['ilk'] for r in ka2}][:4]}")
    ok("B71.Z3 oturum surerken ve izin kapaliyken silme yok; izin yeniden acilinca KYN_TEMIZ_MS "
       "BEKLER (hemen silmeye kosmaz), sonra surer",
       _say(z3, "OTURUMDA") == 0 and _say(z3, "IZINSIZ") == 0 and _say(z3, "HEMEN") == 0
       and (_say(z3, "SONRA3") or 0) >= 1,
       f"OTURUMDA={_say(z3, 'OTURUMDA')} IZINSIZ={_say(z3, 'IZINSIZ')} HEMEN={_say(z3, 'HEMEN')} "
       f"SONRA3={_say(z3, 'SONRA3')}")
    # 🔴 ilk surum yalniz yeni SURECTE acilisa bakiyordu: RAM zaten sifir,
    # kg_ac'in sifirlamasi silinse de yesildi (mutasyon kacti). Artik hazir > 0
    # iken AYNI surecte kg_ac (YAC) de 0 vermeli.
    ok("B71.Z4 hazir sayaci her ACILISTA 0 (yalniz bu acilista silinen guvenilir): yeni "
       "surecte ve hazir > 0 iken ayni surecte kg_ac'ta; mantiksal bicimlemede 0",
       [_say(z, "HZ0") for z in (z1, z2, z3)] == [0, 0, 0] and (_say(z3, "HZ3") or 0) > 0
       and _say(z3, "BIC") == 0 and _say(z3, "BICHZ") == 0
       and (_say(z3, "HZ5") or 0) > 0 and _say(z3, "YAC") == 0 and _say(z3, "YACHZ") == 0,
       f"HZ0={[_say(z, 'HZ0') for z in (z1, z2, z3)]} HZ3={_say(z3, 'HZ3')} BICHZ={_say(z3, 'BICHZ')} "
       f"HZ5={_say(z3, 'HZ5')} YAC={_say(z3, 'YAC')} YACHZ={_say(z3, 'YACHZ')}")
    # son inceleme (Important 1): GF! sonrasi sektor tablosu bos ama flas KIRLI;
    # kafanin bu silmeleri sayilmiyordu ve arka plan temizligi kayit SURERKEN
    # 500 ms'de bir ~25 ms durduruyordu. Artik temizlik ayrintili kayitta durur,
    # kafa bos olmayan her sektoru kirli sayar.
    fc = NorFlas(SEKTOR * HZ_SEKTOR, sektor=SEKTOR)
    fc.nvs["t_rast"] = 19
    _c1, c5 = _yonet(fc, elf_a, [1, 5])
    kay_c, _ = KB.flas_coz(bytes(fc.bellek), SEKTOR)
    o5 = KB.oturumlari_kur(kay_c).get(_say(c5, "BAS5"))
    ka5, bosluk5 = _silme_bosluk(o5)
    ok("B71.Z7 GF! sonrasi hemen ayrintili kayit: arka plan temizligi kayitta SILMEZ (silme "
       "sayisi = sektor ilerlemesi); kirli (tabloda olmayan) her sektor sayilir ve bir "
       "KA_SILME kaydi birakir; 16.38 ms'den KISA durusta da (10 ms) isaretli ornek yeni kayit "
       "acar, bayrak bosluktan hemen sonraki kayitta",
       _say(c5, "BIC5") == 0 and (_say(c5, "ILERLE5") or 0) >= 3
       and _say(c5, "SIL5") == _say(c5, "ILERLE5") and _say(c5, "KIRLI5") == _say(c5, "ILERLE5")
       and len(ka5) == _say(c5, "KIRLI5") and all(bosluk5.get(r["ilk"], 0) >= 10000 for r in ka5),
       f"ILERLE={_say(c5, 'ILERLE5')} SIL={_say(c5, 'SIL5')} KIRLI={_say(c5, 'KIRLI5')} "
       f"KA_SILME={len(ka5)}")
    elf_b = derle("HAZIR", HZ_SEKTOR, ek=("-DKYN_HAZIR_HEDEF=100u",))
    fb = NorFlas(SEKTOR * HZ_SEKTOR, sektor=SEKTOR)
    fb.nvs["t_rast"] = 17
    b1, b4 = _yonet(fb, elf_b, [1, 4])
    bas = _say(b4, "BAS")
    arka = (bas - 1) % HZ_SEKTOR if bas is not None else -1
    bellek = bytes(fb.bellek)
    ok("B71.Z5 on silme ONAYSIZ sektorde durur (arka sektor kalir: 16 - 2 = 14 hazir); hepsi "
       "onaylaninca bile BAS sektore dokunulmaz (en fazla 15); ikisinin kayitlari yerinde",
       _say(b4, "HZB1") == HZ_SEKTOR - 2 and _say(b4, "HZB2") == HZ_SEKTOR - 1
       and bool(_sektor_kayitlari(bellek, bas)) and _say(b1, "KAPALI") == 0,
       f"HZB1={_say(b4, 'HZB1')} HZB2={_say(b4, 'HZB2')} bas={bas} "
       f"bas_kayit={len(_sektor_kayitlari(bellek, bas))} arka={arka}")
    ok("B71.Z6 on silmeden sonra acilis temiz (AC 0), flasta bozuk kayit yok, BITIR payi ve "
       "sektor kurali korunuyor",
       _say(z2, "AC") == 0 and _say(z3, "AC") == 0 and bozuk == 0
       and bitir_payi_korunur(bytes(fa.bellek)) and tekrar_kurali(bytes(fa.bellek)),
       f"AC={_say(z2, 'AC')},{_say(z3, 'AC')} bozuk={bozuk}")


# ── B71.S · osiloskop gunlugu yazicisi (1C-3) ─────────────────────────
SK_SEKTOR = 16


def _skop_no(o, no: int) -> dict | None:
    """Oturumdaki `no` numarali ILK yakalama (skoplar anahtari kayit sirasi)."""
    for s in sorted(getattr(o, "skoplar", {}) if o else {}):
        if o.skoplar[s]["no"] == no:
            return o.skoplar[s]
    return None


def _skop_kod(k: int, no: int) -> int:
    return (37 * k + 101 * no + 11) & 0xFFF


def _skop_meta(no: int) -> dict:
    return {"t_ms": 1000 + no, "sure_ms": 50 + no, "hz": 83333, "tdiv_us": 200, "adim": 0.03125,
            "ofset": -1.25, "tetik": 3 * no, "esik": 2048, "kip": 1, "tetiklendi": 1, "kenar": 0,
            "histerezis": 40, "on_yuzde": 25, "onay": 2}


def bolum_skop() -> None:
    """1C-3: yakalama SKOP kayitlarina parca parca (0. parca META); sektore
    sigdigi kadar, gerisi yeni sektorde. SKOP oturumunda nokta/ornek yok, hiz 0
    ayrintili kip DEGIL; OLCUM'e eklenen yakalama bekleyen nokta ve orneklerden
    SONRA; acik SKOP oturumu acilista sebep 5; DOLU'da BITIR."""
    print("\n── B71.S  osiloskop gunlugu: parcalama · oturum turu · ekleme · acilis · DOLU")
    elf = derle("SKOP", SK_SEKTOR)
    fl = NorFlas(SEKTOR * SK_SEKTOR, sektor=SEKTOR)
    fl.nvs["t_rast"] = 23
    s1, s2 = _yonet(fl, elf, [1, 2])
    kay, bozuk = KB.flas_coz(bytes(fl.bellek), SEKTOR)
    ot = KB.oturumlari_kur(kay)
    o1 = ot.get(_say(s1, "OT1"))
    y1 = _skop_no(o1, 1)
    y2 = _skop_no(o1, 2)
    p1 = [x for x in kay if x.tur == getattr(KB, "T_SKOP", 10) and x.oturum == _say(s1, "OT1")
          and struct.unpack_from("<I", x.yuk)[0] == 1]
    sek1 = {x.adres // SEKTOR for x in p1}
    ok("B71.S1 sektorden buyuk yakalama (240 ornek) parca parca yazilir, birden cok sektore "
       "yayilir; PC birebir birlestirir (kodlar + META); ikinci yakalama da",
       _say(s1, "SK1") == 0 and _say(s1, "SK2") == 0 and y1 is not None and y1["tam"]
       and y1["kodlar"] == [_skop_kod(k, 1) for k in range(240)] and y1["meta"] == _skop_meta(1)
       and y2 is not None and y2["tam"] and y2["kodlar"] == [_skop_kod(k, 2) for k in range(100)]
       and len(sek1) >= 2,
       f"SK1={_say(s1, 'SK1')} parca={len(p1)} sektor={sorted(sek1)} tam={y1 and y1['tam']}")
    en_az = KB.BASLIK_BAYT + 12 + 2 * 32 + KB.BASLIK_BAYT + 8
    p1s = sorted(p1, key=lambda x: x.sira)
    bosa = [SEKTOR - (a.adres % SEKTOR + KB.toplam_bayt(len(a.yuk)))
            for a, b in zip(p1s, p1s[1:]) if a.adres // SEKTOR != b.adres // SEKTOR]
    ok("B71.S2 parca sektor sonunu bosa harcamaz: sigmayan yakalama BOLUNUR (sektor sonunda en "
       "fazla bir asgari parca kadar bos)", bool(bosa) and all(v < en_az for v in bosa), str(bosa))
    ok("B71.S3 SKOP oturumu (hiz_ms 0 = her tetik) AYRINTILI KIP DEGIL; nokta ve ayrintili ornek "
       "KG_YOK; oturumda yalniz yakalama",
       _say(s1, "AYR3") == 0 and _say(s1, "NK3") == -4 and _say(s1, "AO3") == -4
       and o1 is not None and o1.basla is not None and o1.basla.oturum_turu == 3
       and o1.basla.hiz_ms == 0 and not o1.noktalar and not o1.ayrinti,
       f"AYR={_say(s1, 'AYR3')} NK={_say(s1, 'NK3')} AO={_say(s1, 'AO3')}")
    o4 = ot.get(_say(s1, "OT4"))
    sk4 = [x.sira for x in kay if x.tur == getattr(KB, "T_SKOP", 10) and x.oturum == _say(s1, "OT4")]
    nk4 = {struct.unpack_from("<I", x.yuk)[0]: x.sira for x in kay
           if x.tur == KB.T_NOKTA and x.oturum == _say(s1, "OT4")}
    once = [s for ilk, s in nk4.items() if ilk <= 4]
    sonra = [s for ilk, s in nk4.items() if ilk >= 5]
    ok("B71.S4 OLCUM oturumuna eklenen yakalama AYNI oturumda; ondan once beslenen noktalar "
       "ONCE yazilir (kayit sirasi zaman sirasi), sonrakiler sonra; noktalar surer (10)",
       _say(s1, "SK4") == 0 and o4 is not None and len(o4.noktalar) == 10
       and (_skop_no(o4, 1) or {}).get("tam") and bool(sk4) and bool(once) and bool(sonra)
       and max(once) < min(sk4) and max(sk4) < min(sonra),
       f"nokta={o4 and len(o4.noktalar)} once={once} skop={sk4} sonra={sonra}")
    o5 = ot.get(_say(s1, "OT5"))
    ok("B71.S5 kart yeniden basladi: acik SKOP oturumu sebep 5 ile KAPANIR, DEVAM almaz; "
       "yakalamasi yerinde",
       o5 is not None and o5.bitir is not None and o5.bitir["sebep"] == 5 and not o5.devamlar
       and (_skop_no(o5, 1) or {}).get("tam"),
       f"bitir={o5 and o5.bitir} devam={o5 and len(o5.devamlar)}")
    o8 = ot.get(_say(s1, "OT8"))
    ay8 = [x.sira for x in kay if x.tur == KB.T_AYRINTI and x.oturum == _say(s1, "OT8")]
    sk8 = [x.sira for x in kay if x.tur == getattr(KB, "T_SKOP", 10) and x.oturum == _say(s1, "OT8")]
    ok("B71.S8 ayrintili OLCUM'e eklenen yakalamadan ONCE ornek tamponu bosaltilir (10 ornek "
       "flasta, yakalamadan once)",
       _say(s1, "ATAMP0") == 10 and _say(s1, "ATAMP") == 0 and o8 is not None
       and len(KB.ayrinti_ornekler(o8)) == 10 and bool(ay8) and bool(sk8) and max(ay8) < min(sk8),
       f"ATAMP0={_say(s1, 'ATAMP0')} ATAMP={_say(s1, 'ATAMP')} ayr={ay8} skop={sk8}")
    ok("B71.S7 flas temiz: bozuk kayit yok, BITIR payi korunuyor, sektor kurali (TEKRAR)",
       bozuk == 0 and bitir_payi_korunur(bytes(fl.bellek)) and tekrar_kurali(bytes(fl.bellek)),
       f"bozuk={bozuk}")
    fd = NorFlas(SEKTOR * SK_SEKTOR, sektor=SEKTOR)
    fd.nvs["t_rast"] = 29
    (s3,) = _yonet(fd, elf, [3])
    kay3, _ = KB.flas_coz(bytes(fd.bellek), SEKTOR)
    o6 = KB.oturumlari_kur(kay3).get(_say(s3, "OT6"))
    n = _say(s3, "SKN") or 0
    tamlar = [o6.skoplar[j]["tam"] for j in sorted(o6.skoplar)] if o6 else []
    ok("B71.S6 onaysiz bellek dolunca DOLU: oturum BITIR(DOLU) ile kapanir; onceki yakalamalar "
       "tam, yarida kalan yakalama tam DEGIL (sessiz doldurma yok)",
       _say(s3, "SKR") == -1 and _say(s3, "OTUR6") == 0 and o6 is not None
       and o6.bitir is not None and o6.bitir["sebep"] == 2 and n >= 3
       and all(tamlar[:-1]) and len(tamlar) == n and not tamlar[-1],
       f"SKR={_say(s3, 'SKR')} n={n} tam={tamlar} bitir={o6 and o6.bitir}")


# ── B71.R · zamanlanmis kayit karar mantigi (1C-4) ─────────────────────
def bolum_plan() -> None:
    """1C-4: plan_adim gercek saate gore BASLAT/BITIR der; mesgulse atlar,
    kacirilan baslangici pencere icinde gec baslatir; NVS'te kalici, yeniden
    baslamada DEVAM'li oturumun bitisini korur; saat yokken bekler."""
    print("\n── B71.R  zamanlanmis kayit: baslat · bitir · atla · gec · kacirildi · acilis")
    elf = derle("PLAN")
    fl = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    a1, a2, a3, a4 = _yonet(fl, elf, [1, 2, 3, 4])

    def r(c, ad):
        x = alanlar(c, ad)
        return [int(v) for v in x[0]] if x else None
    YOK, BASLAT, BITIR = 0, 1, 2
    D_YOK, BEK, SUR, BIT, ATL, KAC = 0, 1, 2, 3, 4, 5
    ok("B71.R1 baslangicta BASLAT, oturum gorulunce baglanir (SURUYOR), sure dolunca BITIR, "
       "oturum kapaninca BITTI",
       _say(a1, "K1") == 0 and r(a1, "R1a") == [YOK, BEK, 0] and r(a1, "R1b") == [BASLAT, BEK, 0]
       and r(a1, "R1c") == [YOK, SUR, 77] and r(a1, "R1d") == [YOK, SUR, 77]
       and r(a1, "R1e") == [BITIR, SUR, 77] and r(a1, "R1f") == [YOK, BIT, 77],
       str([r(a1, x) for x in ("R1a", "R1b", "R1c", "R1d", "R1e", "R1f")]))
    ok("B71.R2 baslangicta oturum (elle/pil/skop) varsa ATLANDI, sonra kendiliginden BASLAMAZ",
       _say(a1, "K2") == 0 and r(a1, "R2a") == [YOK, ATL, 0] and r(a1, "R2b") == [YOK, ATL, 0],
       str([r(a1, "R2a"), r(a1, "R2b")]))
    ok("B71.R3 kart baslangicta kapaliydi, pencere icinde acildi: GEC baslar (kalan sure)",
       _say(a1, "K3") == 0 and r(a2, "AC") == [0, BEK, 0] and r(a2, "R3a") == [BASLAT, BEK, 0]
       and r(a2, "R3b") == [YOK, SUR, 90], str([r(a2, "AC"), r(a2, "R3a"), r(a2, "R3b")]))
    ok("B71.R4 pencere gecmisse KACIRILDI, baslamaz",
       _say(a1, "K4") == 0 and r(a1, "R4") == [YOK, KAC, 0], str(r(a1, "R4")))
    ok("B71.R5 saat yokken kur REDDEDILIR; bekleyen plan saat yokken BEKLER, saat gelince karar",
       _say(a1, "K5a") == -1 and _say(a1, "K5b") == 0 and r(a1, "R5a") == [YOK, BEK, 0]
       and r(a1, "R5b") == [BASLAT, BEK, 0], str([_say(a1, "K5a"), r(a1, "R5a"), r(a1, "R5b")]))
    ok("B71.R6 yeniden baslama: plan NVS'ten SURUYOR + oturum; DEVAM'li oturumda bitis zamaninda, "
       "saat geri gitse de yeniden baslama yok, surerken kur RED; DEVAM alamadiysa BITTI ve "
       "yeni oturum ACILMAZ",
       r(a3, "AC") == [0, SUR, 90] and r(a3, "R6a") == [YOK, SUR, 90] and r(a3, "R6b") == [YOK, SUR, 90]
       and r(a3, "R6c") == [BITIR, SUR, 90] and _say(a3, "K6") == -4
       and r(a4, "AC") == [0, SUR, 90] and r(a4, "R6d") == [YOK, BIT, 90]
       and r(a4, "R6e") == [YOK, BIT, 90],
       str([r(a3, x) for x in ("AC", "R6a", "R6b", "R6c")] + [_say(a3, "K6")]
           + [r(a4, x) for x in ("AC", "R6d", "R6e")]))
    ok("B71.R7 kullanici Gd ile kapattiysa (oturum yok) plan BITTI, ikinci BITIR yok",
       r(a1, "R7") == [YOK, BIT, 77], str(r(a1, "R7")))
    ok("B71.R8 iptal: plan YOK, baslangicta bir sey olmaz; 30 gunden uzun sure ve gecmis pencere "
       "REDDEDILIR",
       _say(a1, "K8") == 0 and r(a1, "R8a") == [YOK, D_YOK, 0] and _say(a1, "KS") == -2
       and _say(a1, "KG") == -3, str([r(a1, "R8a"), _say(a1, "KS"), _say(a1, "KG")]))
    ok("B71.R9 BASLAT'tan sonra oturum 10 s icinde gorunmezse plan BITTI (baslatilamadi, takili "
       "kalmaz)",
       r(a1, "R9a") == [YOK, SUR, 0] and r(a1, "R9b") == [YOK, BIT, 0],
       str([r(a1, "R9a"), r(a1, "R9b")]))


# ── B71.H · ornek halkasi (1C-2) ─────────────────────────────────────
def bolum_halka() -> None:
    """1C-2: cekirdek 1 -> 0 ornek halkasi (kayit_halka.h), kilitsiz tek
    uretici / tek tuketici. Dolu halkada ornek DUSER, sayilir ve bir sonraki
    itilene KO_KAYIP_ONCE konur; sayac sarmasi (32 bit) dogru."""
    print("\n── B71.H  ornek halkasi: sira · tasma · sarma")
    sat = kos(derle("HALKA"))
    tek = {p[0]: p[1:] for p in (x.split() for x in sat) if p and p[0] not in ("H1", "H2")}
    h1 = [[int(x) for x in p] for p in alanlar(sat, "H1")]
    beklenen1 = [[100 + k, k, (k - 4) & 0xFFFF, (-k) & 0xFFFF, k & 0xF] for k in range(8)]
    ok("B71.H1 8'lik halka: 8 it / 8 al — sira, zaman, kodlar, bayrak birebir",
       tek.get("IT1") == ["8"] and tek.get("AD1") == ["8"] and h1 == beklenen1, str(h1[:2]))
    h2 = [[int(x) for x in p] for p in alanlar(sat, "H2")]
    ko = 0x10
    ok("B71.H2 dolu halkada itme REDDEDILIR ve sayilir; ilk basarili itmede KO_KAYIP_ONCE, "
       "sonrakinde yok (yazici yeni kayit acsin)",
       tek.get("RED") == ["0"] and tek.get("DUSEN") == ["3"] and tek.get("IT2") == ["1"]
       and tek.get("IT3") == ["1"] and len(h2) == 8
       and h2[-2][0] == 150 and h2[-2][4] & ko and h2[-1][0] == 151 and not h2[-1][4] & ko
       and all(not r[4] & ko for r in h2[:-2]),
       f"RED={tek.get('RED')} DUSEN={tek.get('DUSEN')} son={h2[-2:]}")
    h4 = {a: (tek.get(a) or ["?"])[0] for a in ("A0", "A1", "A2", "A3", "B1", "B2", "CMS", "D1")}
    # 🔴 kartta 204 kirli silmenin 3'unde isaret durustan ONCEKI ornege dustu;
    # ilk duzeltme (1C-3 incelemesi) `fark = simdi | 1` ile cift ms'de kaniti
    # atliyordu. Kural artik platformsuz (ksi_*) ve burada davranisla sinaniyor.
    ok("B71.H4 kirli silme isareti: sayac degisince bosluk (>= 15 ms) olmadan ISARET YOK (cift "
       "ms dahil); durustan sonraki ornek isaretli; isaretli ornek DUSERSE kanit surer, sonraki "
       "isaretlenir; bosluk yoksa 100 ms sonra; ayrintili degilken esitleme isareti siler",
       h4 == {"A0": "0", "A1": "0", "A2": "1", "A3": "0", "B1": "1", "B2": "1", "CMS": h4["CMS"],
              "D1": "0"} and h4["CMS"].isdigit() and 2106 <= int(h4["CMS"]) < 2112, str(h4))
    # CMS: degisim ilk 2006'daki ornekte gorulur; 100 ms sonraki ilk ornek 2108
    ok("B71.H3 32 bit sayac sarmasinda (0xFFFFFFF0'dan) 40 ornek sirayla, eksiksiz",
       tek.get("H3N") == ["40"] and tek.get("H3HATA") == ["0"] and tek.get("H3ADET") == ["0"],
       f"{tek.get('H3N')} {tek.get('H3HATA')}")


# ── B71.PL · pil testi oturumu (1C-1) ────────────────────────────────
PIL_SEKTOR = 16      # 1-3. asamalar ~8 sektor tutar; halka 4. asamada dolar


def _say(sat: list[str], ad: str) -> int | None:
    a = alanlar(sat, ad)
    return int(a[0][0]) if a and a[0] else None


def _oturum_kayitlari(kay: list, oid) -> list:
    return sorted((k for k in kay if k.oturum == oid), key=lambda k: k.sira)


def bolum_pil() -> None:
    """1C-1: pil testi kendi oturumunda (kayit_yonet.h, AVR + emule NOR/NVS).
    Olcum -> pil gecisi, olaylar, pil bitir, not kayitlari (oturum 0),
    acilista acik pil oturumunun KAPANMASI (DEVAM yok: emniyet), yer yokken
    durum 4 -> onayla kapanis."""
    print("\n── B71.PL  pil testi oturumu: gecis · olay · bitir · not · acilista kapanis")
    elf = derle("PIL", PIL_SEKTOR)
    fl = NorFlas(SEKTOR * PIL_SEKTOR, sektor=SEKTOR)
    fl.nvs["t_rast"] = 9
    c1, c2, c3 = _yonet(fl, elf, [1, 2, 3])
    kay, bozuk = KB.flas_coz(bytes(fl.bellek), SEKTOR)
    ot = KB.oturumlari_kur(kay)
    olc1, pil1 = _say(c1, "OLC"), _say(c1, "PIL")
    o1, p1 = ot.get(olc1), ot.get(pil1)
    ok("B71.PL1 olcum kaydi surerken pil oturumu acilinca olcum 'baska oturum basladi' "
       "(6) ile kapanir, noktalari eksiksiz; pil oturumunun turu PIL (2); olaylar yazildi",
       o1 is not None and p1 is not None and bool(o1.bitir) and o1.bitir["sebep"] == 6
       and [j for j, _ in o1.noktalar] == list(range(20)) and pil1 > olc1
       and p1.basla is not None and p1.basla.oturum_turu == KB.OTURUM_PIL
       and _say(c1, "OA") == 0 and _say(c1, "OD") == 0,
       f"olcum={o1 and o1.bitir} pil_tur={p1 and p1.basla and p1.basla.oturum_turu}")
    pk = _oturum_kayitlari(kay, pil1)
    sn = [(k.sira, struct.unpack_from("<I", k.yuk)[0], (len(k.yuk) - 4) // KB.NOKTA_BAYT)
          for k in pk if k.tur == KB.T_NOKTA]
    olay = [(k.sira, KB.olay_coz(k.yuk)["tur"]) for k in pk if k.tur == KB.T_OLAY]
    ayar = next((s for s, t in olay if t == KB.KO_PIL_AYAR), None)
    dcir = next((s for s, t in olay if t == KB.KO_DCIR), None)
    once = [s for s, ilk, n in sn if ilk + n <= 15]
    sonra = [s for s, ilk, n in sn if ilk >= 15]
    ok("B71.PL2 pil oturumu ZAMAN sirasinda: BASLA, PIL_AYAR, noktalar 0-14, DCIR, "
       "noktalar 15+ — olaydan once bekleyen noktalar BOSALTILDI (hicbir NOKTA kaydi "
       "DCIR'i ortadan bolmez)",
       bool(pk) and pk[0].tur == KB.T_BASLA and ayar is not None and dcir is not None
       and bool(sn) and ayar < min(s for s, _, _ in sn)
       and all(s < dcir for s in once) and all(s > dcir for s in sonra)
       and len(once) + len(sonra) == len(sn),
       f"olay={olay} nokta={[(i, n) for _, i, n in sn]}")
    l2 = _dr(c2, "L2")
    ok("B71.PL3 acilista acik PIL oturumu 'kart yeniden basladi' (5) ile KAPANIR, DEVAM "
       "YAZILMAZ (emniyet: pil testi surmez); nokta sayisi BITIR ile tutarli; etkin "
       "oturum kalmaz",
       p1 is not None and bool(p1.bitir) and p1.bitir["sebep"] == 5 and not p1.devamlar
       and not any(k.tur == KB.T_DEVAM for k in pk)
       and p1.bitir["nokta_adedi"] >= 15
       and [j for j, _ in p1.noktalar] == list(range(p1.bitir["nokta_adedi"]))
       and l2.get("durum") == 1 and l2.get("oturum") == 0 and _say(c2, "OY") == -4,
       f"bitir={p1 and p1.bitir} devam={p1 and p1.devamlar} L2={l2} OY={_say(c2, 'OY')}")
    pil3, olc3 = _say(c3, "PIL"), _say(c3, "OLC")
    p3, o3 = ot.get(pil3), ot.get(olc3)
    p3k = _oturum_kayitlari(kay, pil3)
    pb = [_say(c3, a) for a in ("PB", "PB2", "PB3")]
    l3a = _dr(c3, "L3a")
    ok("B71.PL4 pil bitir: SONUC olayi BITIR'dan HEMEN once, sebep 4; ikinci cagri ve "
       "olcum surerken cagri hicbir sey yazmaz (KG_YOK), olcum acik kalir",
       p3 is not None and bool(p3.bitir) and p3.bitir["sebep"] == 4 and len(p3k) >= 2
       and p3k[-1].tur == KB.T_BITIR and p3k[-2].tur == KB.T_OLAY
       and KB.olay_coz(p3k[-2].yuk)["tur"] == KB.KO_PIL_SONUC
       and {a: KB.olay_coz(p3k[-2].yuk).get(a) for a in ("durum", "mah", "sure_ms", "dcir_sayisi")}
       == {"durum": 2, "mah": 12.5, "sure_ms": 5000, "dcir_sayisi": 1} and pb == [0, -4, -4]
       and l3a.get("durum") == 2 and l3a.get("oturum") == olc3
       and o3 is not None and not o3.olaylar and bool(o3.bitir) and o3.bitir["sebep"] == 1,
       f"PB={pb} pil={p3 and p3.bitir} L3a={l3a}")
    nk = [k for k in kay if k.tur == KB.T_NOT]
    n1 = _say(c3, "N1")
    ng = [_say(c3, a) for a in ("NG0", "NGB")]
    ok("B71.PL5 not kayitlari baslikta oturum 0 (olcum surerken yazildi, sektor kurali "
       "bozulmadi); pil oturumu: ad = son ad, n1 degisti, n2 silindi; gecersiz hedef "
       "YAZILMAZ; olcum noktalari eksiksiz",
       len(nk) == 6 and all(k.oturum == 0 for k in nk) and tekrar_kurali(bytes(fl.bellek))
       and p3 is not None and p3.ad == "son ad"
       and p3.notlar == {n1: {"nokta_ms": 1500, "metin": "n1b"}} and ng == [-4, -4]
       and o3 is not None and [j for j, _ in o3.noktalar] == list(range(10)),
       f"not={len(nk)} ad={p3 and p3.ad} notlar={p3 and p3.notlar} NG={ng}")
    ok("B71.PL6 1-3. asamalarin flasi temiz: bozuk kayit yok, BITIR payi korunuyor",
       bozuk == 0 and bitir_payi_korunur(bytes(fl.bellek)), f"bozuk={bozuk}")
    c4, c5 = _yonet(fl, elf, [4, 5])
    kay5, _ = KB.flas_coz(bytes(fl.bellek), SEKTOR)
    pil4 = _say(c4, "PIL")
    p4 = KB.oturumlari_kur(kay5).get(pil4)
    l5a, l5b = _dr(c5, "L5a"), _dr(c5, "L5b")
    ok("B71.PL7 yer yokken acilis: PIL oturumu acik BEKLER (durum 4, surdurulmez); onay "
       "yer acinca 'yeniden basladi' (5) ile KAPANIR, DEVAM yok",
       l5a.get("durum") == 4 and l5a.get("oturum") == pil4 and l5b.get("durum") != 4
       and l5b.get("oturum") == 0 and p4 is not None and bool(p4.bitir)
       and p4.bitir["sebep"] == 5 and not p4.devamlar,
       f"L5a={l5a} L5b={l5b} bitir={p4 and p4.bitir} devam={p4 and p4.devamlar}")


# ── B71.C · kalibrasyon gecmisi (kalgec.h) ───────────────────────────
KALGEC_BAYT = 116
_KD = ["adet", "son_no", "taslak", "hata", "tur", "kaynak"]


def _kal_uret(t: int) -> KB.Kalibrasyon:
    """ornek_kayit.c kal_uret() ile AYNI."""
    return KB.Kalibrasyon(
        normal=KB.Kanal(16.5, 2.0, f32(1.0 + t / 1024.0), -12 + t, 0.0029296875),
        yuksek=KB.Kanal(312.5, 2.0, 0.9921875, 5, 0.0030517578125),
        i_ofset=-3, i_pga=0.25, sont_ohm=0.0048828125, i_duzeltme=1.0,
        sebeke_hz=50.0, faz_kal_us=(12.5, -3.25))


def _kalgec_coz(b: bytes) -> dict:
    """Blobu C'den BAGIMSIZ coz (paket: plan 1B)."""
    if len(b) != KALGEC_BAYT or zlib.crc32(b[:112]) != struct.unpack_from("<I", b, 112)[0]:
        raise ValueError("kalgec blobu bozuk")
    no, unix, acilis, tur, kaynak, surum = struct.unpack_from("<IIIBBH", b, 0)
    return {"no": no, "unix_s": unix, "acilis": acilis, "tur": tur, "kaynak": kaynak,
            "surum": surum, "not": b[16:48].split(b"\0", 1)[0].decode("utf-8"),
            "kal": KB.kal_coz(b, 48)}


def _not_bekle(ham: bytes, azami: int = 32) -> bytes:
    """kgc_not_kopyala'nin C'den BAGIMSIZ esi: gecersiz UTF-8 atilir (Python'un
    katı cozucusu: asiri uzun, vekil, 10FFFF ustu), kontrol karakteri / \" / \\
    atilir, 31 bayti asmayan en uzun KARAKTER oneki."""
    s = "".join(c for c in ham.decode("utf-8", errors="ignore")
                if ord(c) >= 0x20 and c not in '\x7f"\\')
    b = b""
    for c in s:
        if len(b) + len(c.encode("utf-8")) > azami - 1:
            break
        b += c.encode("utf-8")
    return b


def _kalgec_paketle(no: int, kal: KB.Kalibrasyon, not_: bytes = b"") -> bytes:
    """Blob — _kalgec_coz'un tersi (C'den bagimsiz; yalniz NVS'i onceden
    doldurmak icin)."""
    b = (struct.pack("<IIIBBH", no, 0, 0, 0, 0, 1) + not_[:31].ljust(32, b"\0")
         + KB.kal_paketle(kal) + b"\0\0")
    return b + struct.pack("<I", zlib.crc32(b))


def _nt(sat: list[str], ad: str) -> bytes | None:
    for s in sat:
        p = s.split()
        if p[:1] == [ad]:
            return bytes.fromhex(p[1]) if len(p) > 1 else b""
    return None


def _kd_al(sat: list[str], ad: str) -> dict:
    for s in sat:
        p = s.split()
        if p and p[0] == ad and len(p) == len(_KD) + 1:
            return dict(zip(_KD, (int(x) for x in p[1:])))
    return {}


def _ke(sat: list[str], no: int) -> list | None:
    for s in sat:
        p = s.split()
        if p[:2] == ["KE", str(no)]:
            return p[2:5] + [bytes.fromhex(p[5]).decode("utf-8") if len(p) > 5 else ""]
    return None


def bolum_kalgec() -> None:
    """1B: kalibrasyon gecmisi — taslak, elle kaydet, kayit baslarken
    otomatik, not/tur duzenleme, elektrik kesilmesi, 40 siniri, NVS dolu,
    Turkce not. NVS emule (ADA gore blob) ve acilistan acilisa kalici."""
    print("\n── B71.C  kalibrasyon gecmisi: taslak · kaydet · otomatik · sinirlar")
    elf = derle("KALGEC")
    f = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    c1, c2 = _yonet(f, elf, [1, 2])
    k2_blob = f.nvs.get("k2", b"")           # 3. acilis notu duzeltmeden ONCE
    (c3,) = _yonet(f, elf, [3])
    d1 = _kd_al(c1, "C1")
    k1 = _kalgec_coz(f.nvs.get("k1", b""))
    ok("B71.C1 ilk acilista bugunku kalibrasyon gecmisin #1'i olur (kaynak 'ilk'), taslak yok",
       alanlar(c1, "AC") == [["0"]] and d1 == {"adet": 1, "son_no": 1, "taslak": 0, "hata": 0,
                                               "tur": 0, "kaynak": 2}
       and k1["no"] == 1 and k1["kal"] == _kal_uret(0) and k1["unix_s"] == 100,
       f"{d1} {k1['not']!r}")
    ok("B71.C2 degisen alan TASLAK olur; 'kaydet' not + turle #2 yapar, taslak kalkar",
       _kd_al(c2, "C2a").get("taslak") == 1 and alanlar(c2, "KAY") == [["2"]]
       and _kd_al(c2, "C2b") == {"adet": 2, "son_no": 2, "taslak": 0, "hata": 0,
                                 "tur": 1, "kaynak": 0},
       f"{_kd_al(c2, 'C2a')} {alanlar(c2, 'KAY')} {_kd_al(c2, 'C2b')}")
    ok("B71.C3 taslak YOKKEN oturum numarasi = son kayit (yeni kayit acilmaz)",
       alanlar(c2, "OTNO") == [["2"]], str(alanlar(c2, "OTNO")))
    ok("B71.C4 taslak VARKEN kayit baslarken OTOMATIK kaydedilir (#3, kaynak 'otomatik'): "
       "hicbir oturum numarasiz kalmaz",
       alanlar(c2, "OTNO2") == [["3"]] and _kd_al(c2, "C4").get("kaynak") == 1
       and _kd_al(c2, "C4").get("adet") == 3, f"{alanlar(c2, 'OTNO2')} {_kd_al(c2, 'C4')}")
    k2 = _kalgec_coz(k2_blob)
    ok("B71.C5 yeniden acilista gecmis kalici; blob C'den bagimsiz cozulur (CRC, alanlar, "
       "kalibrasyon)",
       _kd_al(c3, "C5") == {"adet": 3, "son_no": 3, "taslak": 0, "hata": 0, "tur": 0, "kaynak": 1}
       and _ke(c3, 3)[:3] == ["0", "0", "1"] and k2["kal"] == _kal_uret(1)
       and k2["not"] == "sont 5 mohm" and k2["tur"] == 1 and k2["surum"] == 1,
       f"{_kd_al(c3, 'C5')} KE3={_ke(c3, 3)} k2={k2['not']!r}")
    f.nvs_hata = {"adet"}
    (c4,) = _yonet(f, elf, [4])
    f.nvs_hata = set()
    ok("B71.C6 not ve tur sonradan duzeltilir; acilistan sonra kalici, degerler degismez",
       alanlar(c3, "DUZ") == [["0"]] and _ke(c4, 2) == ["0", "2", "0", "ince ayar notu"]
       and _kalgec_coz(f.nvs["k2"])["kal"] == _kal_uret(1), str(_ke(c4, 2)))
    (c5,) = _yonet(f, elf, [5])
    ok("B71.C7 `adet` yazilamazsa kaydet HATA verir; acilista adet eski kalir, yetim blobun "
       "uzerine siradaki numara yazilir (numara tekrar/atlama yok)",
       alanlar(c4, "YETIM") == [["-2"]] and _kd_al(c4, "C7a").get("adet") == 3
       and _kd_al(c5, "C7b").get("adet") == 3 and alanlar(c5, "KAY4") == [["4"]]
       and _ke(c5, 4)[3] == "dorduncu" and f.nvs.get("adet") == (4).to_bytes(4, "little"),
       f"{alanlar(c4, 'YETIM')} {_kd_al(c5, 'C7b')} {alanlar(c5, 'KAY4')} {_ke(c5, 4)}")
    (c6,) = _yonet(f, elf, [6])
    ok("B71.C8 40 dolunca kaydet ACIK hata (KGC_DOLU), eski kayit silinmez; kayit "
       "baslarken numara 0 + hata (oturum yine tam kopyayla)",
       alanlar(c6, "ADET") == [["40"]] and alanlar(c6, "DOLU") == [["-3"]]
       and alanlar(c6, "OTNO") == [["0"]] and alanlar(c6, "HATA") == [["-3"]]
       and "k1" in f.nvs and "k41" not in f.nvs, f"{[alanlar(c6, a) for a in ('ADET', 'DOLU', 'OTNO', 'HATA')]}")
    ok("B71.C13 gecmis DOLMAK UZERE uyarisi 35. kayitta baslar (dolmadan 5 kayit once)",
       alanlar(c6, "UY") == [["35"]], str(alanlar(c6, "UY")))
    f9 = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    f9.nvs_bos = 10
    (c7,) = _yonet(f9, elf, [7])
    ok("B71.C9 NVS'te yer yoksa #1 bile yazilmaz: acik hata (KGC_NVS_DOLU), numara 0",
       alanlar(c7, "AC") == [["-4"]] and _kd_al(c7, "C9").get("adet") == 0
       and alanlar(c7, "OTNO") == [["0"]] and not any(k.startswith("k") for k in f9.nvs),
       f"{alanlar(c7, 'AC')} {_kd_al(c7, 'C9')}")
    f10 = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    (c8,) = _yonet(f10, elf, [8])
    beklenen = _not_bekle('Türkçe "not" \\ şönt değişti ğü'.encode("utf-8")).decode("utf-8")
    kay = int((alanlar(c8, "KAY") or [["0"]])[0][0])
    ok("B71.C10 Turkce not 31 baytta KARAKTER sinirinda kesilir; \" ve \\ atilir (JSON'a "
       "kacissiz girer)",
       kay == 2 and _ke(c8, 2) is not None and _ke(c8, 2)[3] == beklenen
       and len(beklenen.encode()) <= 31, f"{_ke(c8, 2)} beklenen={beklenen!r}")
    # ornek_kayit.c case 8 ile AYNI girdiler
    girdi = {"N1": b"a" * 30 + "ş".encode(), "N2": b"a" * 29 + "ş".encode(),
             "N3": b"a" * 29 + "€".encode(), "N4": b"a" * 28 + "€".encode(),
             "N5": b"a" * 28 + "🔋".encode(), "N6": b"a" * 27 + "🔋".encode(),
             "N7": (b"a\xfe" b"b\x80" b"c\xc5" b"d\xc0\xaf" b"e\xed\xa0\x80" b"f\xe2\x82"
                    b"g\xf5\x80\x80\x80" b"h\xe0\x80\x80" b"i\xf4\x90\x80\x80" b"j\xc5"),
             "N8": b"\xfe\xf0\xfd\xe7x"}
    gelen = {a: _nt(c8, a) for a in girdi}
    ayni = {a: gelen[a] == _not_bekle(g) for a, g in girdi.items()}
    ok("B71.C10b 31 bayt siniri 2/3/4 baytlik karakterin ORTASINA duserse karakter "
       "butun atilir; gecersiz UTF-8 (cp1254 'ş'=FE, kopuk dizi, asiri uzun, vekil, "
       "10FFFF ustu) atilir — /kal/liste JSON'u PC'de hep cozulur",
       all(ayni.values()) and all(g is not None and g.decode("utf-8") is not None
                                  for g in gelen.values())
       and gelen["N7"] == b"abcdefghij" and gelen["N8"] == b"x",
       f"{[a for a, v in ayni.items() if not v]} N1={gelen['N1']!r} N7={gelen['N7']!r}")
    # C11-C12: sifir ofsetleri gecmise girmez; ayni degerlere donunce ESKI numara
    f11 = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    (c9,) = _yonet(f11, elf, [9])
    ok("B71.C11 yalniz SIFIR ofsetleri degisince (gerilim iki kanal + akim) taslak YOK: "
       "`kk` reddeder, oturum eski numarayi alir, yeni kayit acilmaz (kullanici karari "
       "2026-09-30; gercek sifir oturum basliginda)",
       _kd_al(c9, "C11a").get("taslak") == 0 and alanlar(c9, "S_KAY") == [["-1"]]
       and alanlar(c9, "S_OTNO") == [["1"]] and _kd_al(c9, "C11b").get("adet") == 1,
       f"{_kd_al(c9, 'C11a')} {alanlar(c9, 'S_KAY')} {alanlar(c9, 'S_OTNO')} {_kd_al(c9, 'C11b')}")
    ok("B71.C12 sont/sebeke A->B->C->A->B: yeni kayit yalniz ILK kez gorulen degerlere "
       "(#2, #3); A'ya donunce #1, B'ye donunce #2 — gecmis ancak gercekten farkli "
       "kalibrasyonlarla dolar",
       alanlar(c9, "B_OTNO") == [["2"]] and alanlar(c9, "C_OTNO") == [["3"]]
       and _kd_al(c9, "C12a").get("taslak") == 0 and alanlar(c9, "A_OTNO") == [["1"]]
       and alanlar(c9, "A_KAY") == [["-1"]] and alanlar(c9, "B2_OTNO") == [["2"]]
       and _kd_al(c9, "C12b").get("adet") == 3,
       f"B={alanlar(c9, 'B_OTNO')} C={alanlar(c9, 'C_OTNO')} A={alanlar(c9, 'A_OTNO')} "
       f"B2={alanlar(c9, 'B2_OTNO')} {_kd_al(c9, 'C12b')}")
    # C12c: ayni degerli iki kayit (duzeltmeden once acilmis gecmis) -> EN YENISI
    f12 = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    b_kal = dataclasses.replace(_kal_uret(0), sont_ohm=0.015625)
    f12.nvs.update({"k1": _kalgec_paketle(1, _kal_uret(0)), "k2": _kalgec_paketle(2, _kal_uret(0)),
                    "k3": _kalgec_paketle(3, b_kal), "adet": (3).to_bytes(4, "little")})
    (c10,) = _yonet(f12, elf, [10])
    ok("B71.C12c ayni degerli iki kayit varsa oturum EN YENISINI alir (#2, #1 degil)",
       alanlar(c10, "YENI") == [["2"]] and _kd_al(c10, "C12c").get("adet") == 3,
       f"{alanlar(c10, 'YENI')} {_kd_al(c10, 'C12c')}")


# ── B71.D · oturum dizini ─────────────────────────────────────────────
DIZIN_KAP = 6        # ornek_kayit.c DIZIN_KAP ile ayni


def bolum_dizin() -> None:
    """Son inceleme bulgu 5: dizin bakimi (tahliye, temizlikte dusurme) hic
    sinanmiyordu; kg__sektor_dusur'u bos yapan mutasyon 74/74 geciyordu."""
    print("\n── B71.D  oturum dizini: tahliye · temizlik · kimlik denetimi")
    flas = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    sat = kos(derle("DIZIN"), flas)
    idler = [int(p[0]) for p in alanlar(sat, "ID")]
    tek = {p[0]: p[1:] for p in (x.split() for x in sat)
           if p and p[0] in ("ID9", "ID10", "SILINEN", "YANLIS", "DOGRU", "ACIK", "HATA")}
    dz, dc, dr = _oz(sat, "DZ"), _oz(sat, "DC"), _oz(sat, "DR")
    ok("B71.D1 dizin kapasitesi asilinca EN ESKI duser: 8 oturumdan son 6'si, sirayla",
       len(idler) == 8 and [x[0] for x in dz] == idler[2:8],
       f"dizin={[x[0] for x in dz]} idler={idler}")
    ayni = len(dc) == len(dr) and all(
        a[:3] == b[:3] and a[4:] == b[4:] and a[3] <= b[3] for a, b in zip(dc, dr))
    ok("B71.D2 temizlikten sonra CANLI dizin flastan kurulanla ayni; silinen oturum "
       "dustu, yarim kalanin basi silindi",
       ayni and "HATA" not in tek and int(tek.get("SILINEN", ["0"])[0]) >= 2
       and any(x[7] == 1 for x in dc) and 0 < len(dc) < DIZIN_KAP,
       f"canli={dc} kurulan={dr} silinen={tek.get('SILINEN')} hata={tek.get('HATA')}")
    ok("B71.D3 kg_basla_oku baska oturumun adresini REDDEDER",
       tek.get("YANLIS") == ["-2"] and tek.get("DOGRU") == ["0"],
       f"{tek.get('YANLIS')} {tek.get('DOGRU')}")
    ok("B71.D4 iki ACIK oturum varsa surdurulecek olan EN YENISI",
       tek.get("ACIK") is not None and tek.get("ACIK") == tek.get("ID10"),
       f"ACIK={tek.get('ACIK')} ID10={tek.get('ID10')}")


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
    ok("B71.K10 kesintiler altinda da BITIR payi korunuyor",
       bitir_payi_korunur(bellek))


BOLUMLER = [bolum_nor, bolum_bicim, bolum_noktaci, bolum_gunluk, bolum_yazici,
            bolum_tarama, bolum_mantiksal, bolum_yonet, bolum_pil, bolum_halka, bolum_ayrinti,
            bolum_hazir, bolum_skop, bolum_plan, bolum_kalgec, bolum_dizin,
            bolum_kesinti]


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
    tezgah("B71 Kayit motoru", [
        ("Flas yazma/silmenin olcume etkisi (gercek kart, 1A-2)",
         "kayit 50/s ve 5/s surerken K satirinda loop_azami ve uzun tur "
         "kayitsiz tabanla ayni sinifta; kuyrukta dusen nokta 0"),
        ("Gercek elektrik kesme: fis cekme, PIL anahtari kapali",
         "20 tekrar: kurtarma hatasiz, oturum DEVAM ile suruyor, kayip en "
         "fazla son ~5 s (spec O2)"),
        ("Emule NOR ariza modeli gercek ESP32 flasini temsil ediyor mu",
         "kartta RTS sifirlamasiyla rastgele 100 kesme: K5-K10'un "
         "karsiliklari yesil"),
        ("Python cozucunun volt/amper cevrimi kartin kendi hesabiyla ayni mi",
         "karttan alinan kayit kayit_bicim.volt()/amper() ile cozulunce ayni "
         "anin D satiriyla bagil fark <= 1e-6"),
    ])
    print(f"\nB71: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
