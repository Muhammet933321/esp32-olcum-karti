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
    if len(dosya) > 60:      # 1D: -D ile gelen vektorler adi Windows yol sinirina tasirir
        import hashlib as _hl
        dosya = f"{senaryo}_{_hl.sha256(anahtar.encode()).hexdigest()[:16]}"
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
    kn = (s.get("KN") or ["0", "0", "0", "0"]) + ["0", "0"]
    ok("B71.B19 KN_DCIR (0x40) diger nokta bayraklariyla CAKISMAZ; Python'da ayni",
       int(kn[0]) == 0x40 == KB.KN_DCIR and not (int(kn[0]) & int(kn[1])), str(kn))
    ok("B71.B19b (PT2) KN_OCV = 0x80 (son bos bit), DCIR ve digerleriyle CAKISMAZ; PT4 her "
       "ornek kipindeki PIL noktasinin araligi 1000 ms; Python'da ayni",
       int(kn[2]) == 0x80 == KB.KN_OCV and not (int(kn[2]) & (int(kn[0]) | int(kn[1])))
       and int(kn[3]) == 1000 == KB.PIL_AYR_NOKTA_MS, str(kn))
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
        elif p[:1] and p[0] in ("S1", "S2", "S3", "S4", "S5", "S6"):
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
    s6 = [beklenen(50, [(5, 1, 0.25), (3, 3, 0.5)], bayrak=KB.KN_V_HATA | KB.KN_I_HATA)]
    ok("B71.P7 (W2, 1A-1 D) yapistiricinin hata bayragi OLMADAN gelen NaN ve +Inf watt: noktaci "
       "kendisi HATALI sayar (V+I hata bayragi), (int64_t) donusumu yapilmaz, istatistige yalniz "
       "sonlu iki ornek girer (isfinite kayit_nokta.h'de)",
       gruplar.get("S6") == s6, str(gruplar.get("S6"))[:200])


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
    tamp = (AZAMI_YUK - 4) // KB.NOKTA_BAYT
    o5 = ot.get(int(d["O5"][0])) if "O5" in d else None
    r5a, r5b = int(d["R5A"][0]), int(d["R5B"][0])
    ok("B71.Y15 (W2, 1A-1 O) tampon DOLU iken yazma hatasi: ilk hatada noktalar tamponda kalir "
       f"({tamp}); dolu tamponda yine hata alan SONRAKI nokta reddedilir ve dusen'e SAYILIR (1); "
       "bitiste tampondakiler eksiksiz, sira 0..n-1, BITIR nokta adedi tutar",
       r5a < 0 and r5a != -1 and r5b < 0 and r5b != -1 and int(d["YN5"][0]) == tamp
       and int(d["DUS5"][0]) == 1 and d["B5"] == ["0"]
       and _noktalar_mi(o5, range(tamp), lambda j: 5000 + j)
       and o5.bitir == {"nokta_adedi": tamp, "sebep": 1},
       f"R5A={r5a} R5B={r5b} YN5={d['YN5']} DUS5={d['DUS5']} B5={d['B5']} "
       f"nokta={len(o5.noktalar) if o5 else None} bitir={o5.bitir if o5 else None}")


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
    r_son = next((r for r in (o3.ayrinti if o3 else []) if r["ornekler"]
                  and r["ornekler"][0][0] - 3000 == k0 + A + 1), None)
    ok("B71.A11 (Y5, 1C-2 inceleme) bosaltma hatasinda dusen ornek SAYILIR (dusen 1) ve "
       "bosluktan SONRAKI kayit KA_KAYIP_ONCE tasir (PC eksigi gorur)",
       _say(a3, "DUS3") == 1 and r_son is not None and bool(r_son["bayrak"] & KB.KA_KAYIP_ONCE),
       f"dusen={_say(a3, 'DUS3')} bayrak={r_son and r_son['bayrak']}")
    fl4 = NorFlas(SEKTOR * AYR_SEKTOR, sektor=SEKTOR)
    fl4.nvs["t_rast"] = 17
    (a4,) = _yonet(fl4, elf, [4])
    kay4, bozuk4 = KB.flas_coz(bytes(fl4.bellek), SEKTOR)
    o4 = KB.oturumlari_kur(kay4).get(_say(a4, "BAS4"))
    ilk0 = [r for r in (o4.ayrinti if o4 else []) if r["ilk"] == 0]
    orn4 = KB.ayrinti_ornekler(o4) if o4 else []
    ok("B71.A12 (Y5) kayit flasa TAM yazildi ama yazma HATA dondu: tampon kalir (7), yeniden deneme "
       "ayni ornekleri tekrar yazar (flasta ilk=0 olan IKI kayit); PC her ornegi BIR kez verir "
       "(0..9, sira ve deger birebir), kayip sayilmaz",
       (_say(a4, "Z4") or 0) < 0 and _say(a4, "KAL4") == 7 and len(ilk0) == 2 and bozuk4 == 0
       and [s for s, *_r in orn4] == list(range(10))
       and [v - 3000 for _s, _t, v, *_r in orn4] == list(range(10)) and _say(a4, "DUS4") == 0,
       f"Z4={_say(a4, 'Z4')} KAL4={_say(a4, 'KAL4')} ilk0={len(ilk0)} bozuk={bozuk4} "
       f"sira={[s for s, *_r in orn4]} dusen={_say(a4, 'DUS4')}")
    # NOKTA kayitlari ayni yeniden deneme yolundan gecer (ky_bosalt); kartin flasi yazdigi
    # kaydi dogrulama hatasiyla da dondurebilir — PC her noktayi BIR kez vermeli
    def _nk(j: int) -> bytes:
        return KB.nokta_paketle(KB.Nokta(1000 + j, 1, 0, float(j), j, j, 0.0, 0, 0, 0.0, 0.0, 0.0))
    yk = [KB.Kayit(KB.T_NOKTA, 2, 1, struct.pack("<I", 0) + b"".join(_nk(j) for j in range(3))),
          KB.Kayit(KB.T_NOKTA, 4, 1, struct.pack("<I", 0) + b"".join(_nk(j) for j in range(5))),
          KB.Kayit(KB.T_NOKTA, 5, 1, struct.pack("<I", 5) + b"".join(_nk(j) for j in range(5, 7)))]
    o5 = KB.oturumlari_kur(yk).get(1)
    ok("B71.A13 (Y5) ayni noktalari tasiyan iki NOKTA kaydi (yeniden deneme): PC her noktayi BIR "
       "kez, ILK kopyasiyla verir (0..6)",
       o5 is not None and [j for j, _ in o5.noktalar] == list(range(7))
       and [n.v_min_kod for _, n in o5.noktalar] == list(range(7)),
       str(o5 and [j for j, _ in o5.noktalar]))


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
    """1C-4: plan_adim gercek saate gore BASLAT/BITIR der; mesgulse (oturum, pil
    testi, skop gunlugu) atlar, kacirilan baslangici pencere icinde gec baslatir;
    plan YALNIZ cekirdek 0'in bildirdigi oturuma baglanir (benimseme yok);
    baslatilamazsa BASLATILAMADI; NVS'te kalici."""
    print("\n── B71.R  zamanlanmis kayit: baslat · bitir · atla · gec · kacirildi · acilis")
    elf = derle("PLAN")
    fl = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    a1, a2, a3, a4, a5, a6, a7, a8, a9 = _yonet(fl, elf, [1, 2, 3, 4, 5, 6, 7, 8, 9])

    def r(c, ad):
        x = alanlar(c, ad)
        return [int(v) for v in x[0]] if x else None
    YOK, BASLAT, BITIR = 0, 1, 2
    D_YOK, BEK, SUR, BIT, ATL, KAC, BAS_YOK = 0, 1, 2, 3, 4, 5, 7
    ok("B71.R1 baslangicta BASLAT; arada beliren BASKA oturum BENIMSENMEZ, saat geri gitse de "
       "zaman asimi sayilmaz; plan cekirdek 0'in bildirdigi oturuma baglanir, sure dolunca BITIR, "
       "oturum kapaninca BITTI",
       _say(a1, "K1") == 0 and r(a1, "R1a") == [YOK, BEK, 0] and r(a1, "R1b") == [BASLAT, BEK, 0]
       and r(a1, "R1x") == [YOK, SUR, 0] and r(a1, "R1y") == [YOK, SUR, 0] and _say(a1, "S1") == 1 and r(a1, "R1c") == [YOK, SUR, 77]
       and _say(a1, "S1b") == 0 and r(a1, "R1d") == [YOK, SUR, 77] and r(a1, "R1e") == [BITIR, SUR, 77]
       and r(a1, "R1f") == [YOK, BIT, 77],
       str([r(a1, x) for x in ("R1a", "R1b", "R1x", "R1y", "R1c", "R1d", "R1e", "R1f")]))
    ok("B71.R2 baslangicta mesgulse (oturum, oturumsuz pil testi, skop gunlugu) ATLANDI, sonra "
       "kendiliginden BASLAMAZ",
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
    ok("B71.R8 iptal: plan YOK; 30 gunden uzun sure, gecmis pencere, anlamsiz baslangic ('+' "
       "unutulmus Gp20, 1 yildan ileri) REDDEDILIR",
       _say(a1, "K8") == 0 and r(a1, "R8a") == [YOK, D_YOK, 0] and _say(a1, "KS") == -2
       and _say(a1, "KG") == -3 and _say(a1, "KZa") == -5 and _say(a1, "KZb") == -5,
       str([r(a1, "R8a"), _say(a1, "KS"), _say(a1, "KG"), _say(a1, "KZa"), _say(a1, "KZb")]))
    ok("B71.R9 BASLAT'tan sonra cekirdek 0'dan sonuc 10 s icinde gelmezse BASLATILAMADI "
       "(takili kalmaz, 'bitti' denmez)",
       r(a1, "R9a") == [YOK, SUR, 0] and r(a1, "R9b") == [YOK, BAS_YOK, 0]
       and _say(a1, "S9") == 0 and r(a1, "R9c") == [YOK, BAS_YOK, 0],
       str([r(a1, "R9a"), r(a1, "R9b"), _say(a1, "S9"), r(a1, "R9c")]))
    ok("B71.R12 cekirdek 0 MESGUL dediyse (kuyrukta onde Gb vardi) plan ATLANDI — isi bolmez",
       _say(a1, "K12") == 0 and r(a1, "R12a") == [BASLAT, BEK, 0] and r(a1, "R12b") == [0, ATL, 0],
       str([r(a1, "R12a"), r(a1, "R12b")]))
    ok("B71.R10 sure 0 = Gd'ye dek: baslar, BITIR HIC demez; oturum kapaninca BITTI",
       _say(a1, "K10") == 0 and r(a1, "R10a") == [BASLAT, BEK, 0]
       and r(a1, "R10b") == [YOK, SUR, 91] and r(a1, "R10c") == [YOK, BIT, 91],
       str([r(a1, x) for x in ("R10a", "R10b", "R10c")]))
    ok("B71.R11 cekirdek 0 oturumu acamadiysa (DOLU/hata/mesgul) plan BASLATILAMADI — 'bitti' "
       "DEGIL",
       _say(a1, "K11") == 0 and r(a1, "R11a") == [BASLAT, BEK, 0] and r(a1, "R11b") == [0, BAS_YOK, 0],
       str([r(a1, "R11a"), r(a1, "R11b")]))
    ok("B71.R13 BASLAT'tan sonra sonuc gelmeden elektrik gitti, cekirdek 0'dan KANIT yok: acilista "
       "plan oturumu BILINMIYOR -> BITTI; o an etkin olan oturumu BENIMSEMEZ (karar tarama "
       "bittikten sonra plan_acilis'te, plan_ac'ta degil)",
       _say(a4, "K13") == 0 and r(a4, "R13a") == [BASLAT, BEK, 0]
       and r(a5, "AC") == [0, SUR, 0] and _say(a5, "KA") == 0 and r(a5, "AK") == [0, BIT, 0]
       and r(a5, "R13b") == [YOK, BIT, 0],
       str([r(a4, "R13a"), r(a5, "AC"), r(a5, "AK"), r(a5, "R13b")]))
    ok("B71.R14 (Y2, 1C-4 inceleme M3) BASLAT gitti ama plan NVS'i yazilmadan elektrik gitti "
       "(plan BEKLIYOR kaldi): acilista cekirdek 0'in KANITI bu planin numarasiysa plan o "
       "oturumu BENIMSER, sure dolunca BITIR (kayit bitissiz SURMEZ, ATLANDI demez)",
       _say(a6, "K14") == 0 and r(a6, "R14a") == [BASLAT, BEK, 0] and r(a7, "AC") == [0, BEK, 0]
       and _say(a7, "KA") == 1 and r(a7, "AK") == [0, SUR, 44] and r(a7, "R14b") == [YOK, SUR, 44]
       and r(a7, "R14c") == [BITIR, SUR, 44] and r(a7, "R14d") == [YOK, BIT, 44],
       str([r(a6, "R14a"), r(a7, "AC"), _say(a7, "KA"), r(a7, "AK"), r(a7, "R14b"), r(a7, "R14c")]))
    ok("B71.R15 (Y2) plan SURUYOR ama oturumu bilinmiyorken elektrik gitti: KANIT varsa BITTI "
       "DEGIL, oturumu benimser ve zamaninda BITIR",
       _say(a7, "K15") == 0 and r(a7, "R15a") == [BASLAT, BEK, 0] and r(a8, "AC") == [0, SUR, 0]
       and _say(a8, "KA") == 1 and r(a8, "AK") == [0, SUR, 46] and r(a8, "R15b") == [BITIR, SUR, 46]
       and r(a8, "R15c") == [YOK, BIT, 46],
       str([r(a7, "R15a"), r(a8, "AC"), _say(a8, "KA"), r(a8, "AK"), r(a8, "R15b")]))
    ok("B71.R16 (Y2) kanit BASKA bir planin (numara tutmuyor): BENIMSENMEZ; BEKLIYOR plan "
       "pencere icinde yeniden BASLAT der",
       _say(a8, "K16") == 0 and r(a8, "R16a") == [BASLAT, BEK, 0] and _say(a9, "KA") == 0
       and r(a9, "AK") == [0, BEK, 0] and r(a9, "R16b") == [BASLAT, BEK, 0],
       str([r(a8, "R16a"), _say(a9, "KA"), r(a9, "AK"), r(a9, "R16b")]))
    (a10,) = _yonet(fl, elf, [10])
    fl.nvs_hata = {"pl_bas"}
    (a11,) = _yonet(fl, elf, [11])
    fl.nvs_hata = set()
    (a12,) = _yonet(fl, elf, [12])
    ok("B71.R17 (Y3, 1C-4 inceleme M4) plan NVS'e YAZILAMAZSA (kismi hata: yalniz pl_bas) KURULMAZ "
       "(KP_NVS -6, kart 'kuruldu' demez); ONCEKI plan RAM'de ve NVS'te bozulmadan kalir, "
       "acilista geri gelir ve zamaninda BASLAT der",
       _say(a10, "K17") == 0 and _say(a11, "K18") == -6 and r(a11, "R18") == [0, BEK, 0]
       and _say(a11, "PBAS") == 800000 and r(a12, "AC") == [0, BEK, 0]
       and _say(a12, "PBAS") == 800000 and r(a12, "R17") == [BASLAT, BEK, 0],
       str([_say(a11, "K18"), r(a11, "R18"), _say(a11, "PBAS"), r(a12, "AC"), _say(a12, "PBAS"),
            r(a12, "R17")]))

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
    ok("B71.PL8 (Y1, 1C-1 inceleme M7: kayitsiz pil testi) olcum oturumu acikken hedefi PIL "
       "olan olay YAZILMAZ (KG_YOK), olcum oturumunda olay yok; KN_DCIR ve (PT2) KN_OCV "
       "noktada YALNIZ PIL oturumunda kalir (baska bitler korunur)",
       _say(c3, "OYO") == -4 and o3 is not None and not o3.olaylar
       and _say(c3, "EKO") == 0x01 and _say(c3, "EKP") == 0xC1 and _say(c3, "EKY") == 0x01,
       f"OYO={_say(c3, 'OYO')} olay={o3 and o3.olaylar} EKO={_say(c3, 'EKO')} "
       f"EKP={_say(c3, 'EKP')} EKY={_say(c3, 'EKY')}")
    _pil_her_ornek(elf)


def _pil_her_ornek(elf: Path) -> None:
    """PT4 (2026-10-07): PIL oturumunda hiz 0 = her ornek. AYRINTI kayitlari (OLCUM'deki
    gibi) ARTI 1/s NOKTA (ozet/eksen, ilk ikisi KN_OCV); ikisi ayni sira uzayinda, kayit
    sirasi = sira sirasi (nokta once bekleyen ornekleri, olay da ornekleri bosaltir).
    ornek_kayit.c SENARYO_PIL asama 6, AYRI flas: 300 ornek (v = 1000 + k, 2.5 ms),
    k = 49, 99, ... 299'da nokta, k = 120'de DCIR olayi."""
    fl = NorFlas(SEKTOR * PIL_SEKTOR, sektor=SEKTOR)
    fl.nvs["t_rast"] = 5
    (c6,) = _yonet(fl, elf, [6])
    kay, bozuk = KB.flas_coz(bytes(fl.bellek), SEKTOR)
    ot = KB.oturumlari_kur(kay)
    pil6 = _say(c6, "PIL6")
    o = ot.get(pil6)
    nk6 = [int(a[0]) for a in alanlar(c6, "NK6")]
    ok("B71.PL9 (PT4) PIL oturumu hiz 0: yazici AYRINTILI; her nokta, olay ve bitir YAZILDI "
       "(KG_TAMAM), ornekte hata yok; PIL_AYAR'da dcir_aralik_ms 0 (PT5 KAPALI) ve kayit_hz 0 "
       "(her ornek) cozulur",
       o is not None and _say(c6, "AYR6") == 1 and nk6 == [0] * 6
       and [_say(c6, a) for a in ("OA6", "OD6", "PB6")] == [0, 0, 0] and not alanlar(c6, "AH6")
       and o.basla is not None and o.basla.hiz_ms == 0 and o.basla.oturum_turu == KB.OTURUM_PIL
       and [x["tur"] for x in o.olaylar] == [KB.KO_PIL_AYAR, KB.KO_DCIR, KB.KO_PIL_SONUC]
       and o.olaylar[0]["dcir_aralik_ms"] == 0 and o.olaylar[0]["kayit_hz"] == 0.0,
       f"AYR6={_say(c6, 'AYR6')} NK6={nk6} olay={o and [x['tur'] for x in o.olaylar]} "
       f"ayar={o and o.olaylar and o.olaylar[0]}")
    orn = KB.ayrinti_ornekler(o) if o else []
    ok("B71.PL10 (PT4) pil oturumundaki 300 ornegin HEPSI ayrinti_ornekler'de: kod ve "
       "mikrosaniye birebir (o.ayrinti dolu), bayrak/kayip yok",
       [r[2] for r in orn] == [1000 + k for k in range(300)]
       and [r[1] for r in orn] == [2_000_000 + 2500 * k for k in range(300)]
       and [r[3] for r in orn] == [-k for k in range(300)] and all(r[4] == 0 for r in orn),
       f"{len(orn)} ornek")
    nok = sorted(o.noktalar) if o else []
    sira_o = {r[2] - 1000: r[0] for r in orn}
    ok("B71.PL11 (PT4) 6 nokta (1/s), ilk ikisi KN_OCV; noktanin sirasi kendinden ONCEKI "
       "orneklerden buyuk, SONRAKILERDEN kucuk; ornek + nokta siralari AYRIK ve birlikte "
       "0 .. BITIR.nokta_adedi - 1",
       len(nok) == 6 and [n.bayrak for _, n in nok] == [KB.KN_OCV, KB.KN_OCV, 0, 0, 0, 0]
       and all(sira_o[50 * j + 49] < sj < sira_o.get(50 * j + 50, 1 << 30)
               for j, (sj, _) in enumerate(nok))
       and bool(o.bitir) and sorted([r[0] for r in orn] + [sj for sj, _ in nok])
       == list(range(o.bitir["nokta_adedi"])) and o.bitir["sebep"] == 4,
       f"nokta={[(sj, n.bayrak) for sj, n in nok]} bitir={o and o.bitir}")
    veri = []
    for k in _oturum_kayitlari(kay, pil6):
        if k.tur == KB.T_NOKTA:
            veri.append(("N", k.sira, [struct.unpack_from("<I", k.yuk)[0]]))
        elif k.tur == KB.T_AYRINTI:
            a = KB.ayrinti_coz(k.yuk)
            veri.append(("A", k.sira, [a["ilk"] + j for j in range(len(a["ornekler"]))]))
        elif k.tur == KB.T_OLAY and KB.olay_coz(k.yuk)["tur"] == KB.KO_DCIR:
            veri.append(("D", k.sira, []))
    duz = [x for _, _, v in veri for x in v]
    dcir = next((i for i, (t, _, _) in enumerate(veri) if t == "D"), None)
    once = [x for _, _, v in veri[:dcir or 0] for x in v]
    sonra = [x for _, _, v in veri[(dcir or 0) + 1:] for x in v]
    ok("B71.PL12 (PT4) kayit sirasi = sira sirasi (NOKTA ve AYRINTI kayitlari arka arkaya "
       "artan): nokta oncesindeki ornekler kendinden ONCE yazildi; DCIR olayi k <= 120 "
       "orneklerinden SONRA, k >= 121'den ONCE (olay ayrintiyi bosaltir); flas temiz",
       duz == sorted(duz) == list(range(len(duz))) and dcir is not None
       and max(once) == sira_o[120] and min(sonra) > sira_o[120] and bozuk == 0
       and bitir_payi_korunur(bytes(fl.bellek)),
       f"dcir={dcir} once_son={once and max(once)} k120={sira_o.get(120)} bozuk={bozuk}")
    ok("B71.PL13 (PT4) OLCUM hiz 0 hala ayrintili ve NOKTA ALMAZ (KG_YOK); SKOP hiz 0 "
       "ayrintili DEGIL (her tetik)",
       _say(c6, "AYO6") == 1 and _say(c6, "NKO6") == -4 and _say(c6, "AYS6") == 0
       and _say(c6, "OLC6") > pil6 and _say(c6, "SKP6") > _say(c6, "OLC6"),
       f"AYO6={_say(c6, 'AYO6')} NKO6={_say(c6, 'NKO6')} AYS6={_say(c6, 'AYS6')}")


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
    # Y4 (1B inceleme M1): `adet` kaybolursa #1 EZILMEZ — k1..k40 taranip sayi yeniden kurulur;
    # ortadaki bozuk kayit (k3) taramayi durdurmaz (yoksa k4 ezilirdi)
    oncesi = {a: f.nvs[a] for a in ("k1", "k2", "k3", "k4")}
    del f.nvs["adet"]
    k3b = bytearray(f.nvs["k3"])
    k3b[20] ^= 0xFF
    f.nvs["k3"] = bytes(k3b)
    (c14,) = _yonet(f, elf, [11])
    sonrasi = {a: f.nvs.get(a) for a in ("k1", "k2", "k4")}
    f.nvs["k3"] = oncesi["k3"]
    ok("B71.C14 (Y4, 1B inceleme M1) `adet` KAYBOLURSA #1 ezilmez: k1..k40 taranir, adet = en buyuk "
       "gecerli numara (4; ortadaki bozuk k3 taramayi durdurmaz), NVS'e geri yazilir, kayitlar "
       "degismez",
       alanlar(c14, "AC") == [["0"]] and _kd_al(c14, "C14").get("adet") == 4
       and _kd_al(c14, "C14").get("son_no") == 4 and f.nvs.get("adet") == (4).to_bytes(4, "little")
       and all(sonrasi[a] == oncesi[a] for a in ("k1", "k2", "k4")),
       f"{alanlar(c14, 'AC')} {_kd_al(c14, 'C14')} adet={f.nvs.get('adet')!r} "
       f"degisen={[a for a in ('k1', 'k2', 'k4') if sonrasi[a] != oncesi[a]]}")
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


def bolum_plan_kanit() -> None:
    """Y2 (1C-4 inceleme M3): cekirdek 0 planin oturumunu KANITLA baglar. Oturumu
    acmadan ONCE NVS'e plan no + sonraki sira, actiktan sonra oturum; acilista
    (kyn_ac) bu kanit devam eden oturumla karsilastirilip yayinlanir. Elektrik
    hangi anda giderse gitsin planin oturumu taninir, baska oturum benimsenmez."""
    print("\n── B71.PK  plan oturumu kaniti (Y2): kyn_plan_baslat · kyn_ac")
    elf = derle("YONET")
    fl = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    c15, c16, c17, c18, c19 = _yonet(fl, elf, [15, 16, 17, 18, 19])

    def kn(c, ad):
        x = alanlar(c, ad)
        return [int(v) for v in x[0]] if x else None
    pk1, pk2, el = _say(c15, "PK1"), _say(c16, "PK2"), _say(c17, "EL")
    ok("B71.PK1 tam yol (KM_PLAN_BASLAT): plan 5'in oturumu acildi; acilista cekirdek 0 kaniti "
       "(plan 5, o oturum) yayinlar, oturum DEVAM'li",
       bool(pk1) and pk1 > 0 and _say(c15, "PKOT") == pk1 and kn(c16, "KN16") == [5, pk1, pk1],
       f"PK1={pk1} pk_ot={_say(c15, 'PKOT')} KN16={kn(c16, 'KN16')}")
    ok("B71.PK2 TEHLIKELI pencere: oturum acildi ama pk_ot yazilmadan elektrik gitti — acilista "
       "kanit, pk_alt'tan YENI devam eden oturumdan (plan 6); pk_ot onarilir",
       bool(pk2) and pk2 > pk1 and kn(c17, "KN17") == [6, pk2, pk2] and _say(c17, "PKO") == pk2,
       f"PK2={pk2} KN17={kn(c17, 'KN17')} pk_ot={_say(c17, 'PKO')}")
    ok("B71.PK3 oturum surerken planin oturumu ACILMAZ (0 = mesgul), kanit degismez",
       _say(c17, "PB0") == 0 and _say(c17, "PKN") == 6, f"{_say(c17, 'PB0')} {_say(c17, 'PKN')}")
    ok("B71.PK4 kullanicinin ELLE kaydi DEVAM alsa da plan kanitina UYMAZ (benimseme yok, I1)",
       bool(el) and el > pk2 and kn(c18, "KN18") == [0, 0, el], f"EL={el} KN18={kn(c18, 'KN18')}")
    ok("B71.PK5 plan oturumu acilmadan elektrik gitti (pk_ot 0): devam eden oturum pk_alt'tan "
       "ESKI (o anda acik olan elle kayit) -> kanit YOK ve pk_no TEMIZLENIR (bayat kanit sonraki "
       "bir kayda uymaz)",
       kn(c19, "KN19") == [0, 0, el] and _say(c19, "PKN") == 0, f"{kn(c19, 'KN19')} {_say(c19, 'PKN')}")
def bolum_guvenlik() -> None:
    """1D: eslestirme + imzali istek (guvenlik.h) AVR'de, sinama SHA-256'siyla;
    vektorler uretim/vektor_guvenlik.json'dan (Python ile AYNI sonuc)."""
    import json as _json
    print("\n── B71.U  1D guvenlik: vektorler · eslestirme · deneme siniri · imza · "
          "tekrar penceresi · kalicilik")
    V = _json.loads((BURASI / "vektor_guvenlik.json").read_text(encoding="utf-8"))
    im = {o["ad"]: o for o in V["imza"]}
    pr = V["protokol"]
    ek = (f"-DGUV_V_KANIT={pr['kanit_istemci']}", f"-DGUV_V_IMZA_GET={im['get']['imza']}",
          f"-DGUV_V_IMZA_POST={im['post']['imza']}", f"-DGUV_V_IMZA_AKIS={im['akis']['imza']}",
          f"-DGUV_V_IMZA_GET_SORGU={im['get_sorgu']['imza']}")
    elf = derle("GUV", ek=ek)
    fl = NorFlas(SEKTOR * SEKTOR_ADET, sektor=SEKTOR)
    a1, a2, a3, a4, a5 = _yonet(fl, elf, [1, 2, 3, 4, 5])

    def k(c, ad):
        x = alanlar(c, ad)
        return int(x[0][0]) if x and x[0] else None

    def h(c, ad):
        x = alanlar(c, ad)
        return x[0][0] if x and x[0] else None
    YOK, IMZA, TEKRAR, CIHAZ, BEKLE, DOLU, PAROLA, KANIT, AD = -1, -2, -3, -4, -5, -6, -7, -8, -9
    KRIPTO, AYAR = -11, -12
    rfc = {x["veri"]: x["hmac"] for x in V["hmac"]}
    ok("B71.U1 sinama SHA-256/HMAC RFC 4231 durum 1 ve 2 ile ayni (C'nin kriptografisi dogru)",
       h(a1, "H1") == rfc[b"Hi There".hex()]
       and h(a1, "H2") == rfc[b"what do ya want for nothing?".hex()],
       f"{h(a1, 'H1')} {h(a1, 'H2')}")
    ok("B71.U2 PBKDF2 CEKIRDEKTE (guv_pbkdf2): RFC 7914 passwd/salt/1 ve tur 3 vektoru Python ile "
       "ayni; uzun dongude nefes cagriliyor (kartta bekci/WDT)",
       k(a1, "PB1R") == 0 and h(a1, "PB1") == V["pbkdf2"][0]["dk"][:64] and k(a1, "PB3R") == 0
       and h(a1, "PB3") == pr["pbkdf2_uc"]["P"] and (k(a1, "NEF") or 0) >= 1,
       f"{h(a1, 'PB1')} {h(a1, 'PB3')} nefes={k(a1, 'NEF')}")
    import hashlib as _hl
    u19 = _hl.pbkdf2_hmac("sha256", b"u" * 70, b"salt", 3, 32).hex()
    ok("B71.U19 (kart tezgahi: 50 000 tur 4.76 s) guv_pbkdf2 HMAC'in ipad/opad durumunu BIR KEZ "
       "kurar: tur basina 2 SHA kopyasi, HMAC kurulumu YOK; 70 baytlik parola (once SHA-256) "
       "Python hashlib ile ayni",
       k(a1, "U19R") == 0 and h(a1, "U19") == u19 and k(a1, "U19K") == 6 and k(a1, "U19H") == 0,
       f"{h(a1, 'U19')} kopya={k(a1, 'U19K')} hmac_bas={k(a1, 'U19H')}")
    ok("B71.U3 VEKTOR eslestirmesi: kart Python'un istemci kanitini KABUL eder (P = PBKDF2 tur 2), "
       "numara 3, kart kaniti ve K Python ile AYNI",
       k(a1, "UP") == 0 and k(a1, "USB1") == 1 and k(a1, "USB2") == 2 and k(a1, "U3") == 0
       and k(a1, "U3N") == 3
       and h(a1, "U3KK") == pr["kanit_kart"] and h(a1, "U3K") == pr["K"],
       f"{k(a1, 'U3')} n={k(a1, 'U3N')} kk={str(h(a1, 'U3KK'))[:12]} K={str(h(a1, 'U3K'))[:12]}")
    ok("B71.U4 imza VEKTORLERI kartta dogrulanir: GET, POST govdeli, akis, yuzde kodlu sorgu",
       [k(a1, x) for x in ("U4A", "U4B", "U4C", "U4D")] == [0, 0, 0, 0],
       str([k(a1, x) for x in ("U4A", "U4B", "U4C", "U4D")]))
    ok("B71.U10a (Review Focus 1) not='a&b=c' ile imzalanmis istek not=a & b=c olarak "
       "sunulunca IMZA reddi (tekrar degil)", k(a1, "U10A") == IMZA, str(k(a1, "U10A")))
    ok("B71.U5 P yalniz uygun parolayla hesaplanir (9 / 11 karakter / bos -> PAROLA; K3 kullanici "
       "onayi: en az 12); P yokken eslestirme PAROLA reddi; bos ad -> AD reddi",
       [k(a1, x) for x in ("U5A", "U5F", "U5D", "U5B", "U5E", "U5C")]
       == [PAROLA, PAROLA, PAROLA, PAROLA, 0, AD],
       str([k(a1, x) for x in ("U5A", "U5F", "U5D", "U5B", "U5E", "U5C")]))
    u17 = [k(a1, "U17" + x) for x in "ABCDEFGH"]
    ok("B71.U17 kriptografi hatasi: DOGRU imza bile REDDEDILIR, hata gecince ayni istek kabul; "
       "eslestirme kaniti ve P hesabi KRIPTO hatasi doner; YALNIZ istemci kanitinin HMAC'i "
       "hata verince de (cikti dogru MAC olsa bile) KRIPTO",
       u17 == [IMZA, 0, 0, KRIPTO, KRIPTO, 0, 0, KRIPTO], str(u17))
    ok("B71.U18 ayar kaydi BOZUK (boy yanlis): ac AYAR doner, imza ZORUNLU (fail-closed), kimlik "
       "bilinmiyor; ayar yazilinca kimlik/tuz yeniden uretilir, sonraki acilis normal ve zorunlu 0",
       k(a4, "AC") == AYAR and alanlar(a4, "U18Z") == [["1"]] and h(a4, "KIMLIK") == "0" * 16
       and k(a4, "U18Y") == 0 and h(a4, "U18K") not in (None, "0" * 16) and k(a5, "AC") == 0
       and h(a5, "KIMLIK") == h(a4, "U18K") and alanlar(a5, "U18S") == [["0"]],
       f"{k(a4, 'AC')} {alanlar(a4, 'U18Z')} {h(a4, 'U18K')} {k(a5, 'AC')} {alanlar(a5, 'U18S')}")
    ok("B71.U6 tam eslestirme: rastgele nk ile bagimsiz istemci kaniti kabul, numara 4; kartin "
       "kaniti ve sakladigi K, test tarafinin spec bicimiyle hesapladigiyla ayni",
       [k(a1, x) for x in ("U6A", "U6B", "U6N", "U6KART", "U6K")] == [0, 0, 4, 1, 1],
       str([k(a1, x) for x in ("U6A", "U6B", "U6N", "U6KART", "U6K")]))
    u7 = [k(a1, "U7" + x) for x in "ABCDEFGHIJKLMN"]
    ok("B71.U7 deneme siniri: yanlis kanit -> 1 s bekle, ikinci -> 2 s; basarida sifirlanir (tekrar 1 s); "
       "her bekleyen TEK deneme (yanlistan sonra dogru kanit da YOK)",
       u7 == [0, KANIT, BEKLE, 0, KANIT, BEKLE, 0, 0, 0, KANIT, BEKLE, 0, KANIT, YOK], str(u7))
    ok("B71.U8 60 s'den eski bekleyen eslestirme dogru kanitla bile YOK",
       [k(a1, "U8A"), k(a1, "U8B")] == [0, YOK], str([k(a1, "U8A"), k(a1, "U8B")]))
    u9 = [k(a1, "U9" + x) for x in "ABCDEFGHIJKLM"]
    ok("B71.U9 tekrar penceresi (64): ayni sayac ret, sirasiz s+1 kabul, pencere gerisi ret; "
       "SAHTE imzali buyuk sayac pencereyi ilerletemez; sayac 0 ret; son karakteri degismis "
       "imza ret (tam karsilastirma), duzgunu kabul",
       u9 == [0, TEKRAR, 0, 0, TEKRAR, 0, TEKRAR, 0, IMZA, 0, TEKRAR, IMZA, 0], str(u9))
    u10 = [k(a1, "U10" + x) for x in "BCDEFGH"]
    ok("B71.U10 tek degisiklik = ret: yontem, yol, ek arguman, govde, acilis; degismemis kabul; "
       "olmayan cihaz CIHAZ", u10 == [IMZA, IMZA, IMZA, IMZA, IMZA, 0, CIHAZ], str(u10))
    u11 = [int(x[0]) for x in alanlar(a1, "U11")]
    ok("B71.U11 liste en fazla 8: 6, 7, 8 eklenir, 9. DOLU; doluyken parolali baslat da DOLU",
       u11 == [6, 7, 8, DOLU] and k(a1, "U11B") == DOLU and k(a1, "U11N") == 8,
       f"{u11} {k(a1, 'U11B')} {k(a1, 'U11N')}")
    ok("B71.U12 yeniden baslama: 8 cihaz kalici; acilis nonce'u YENI; eski acilisli imza ret, "
       "yeni acilisla sayac 1 kabul",
       k(a2, "U12N") == 8 and h(a1, "ACILIS") != h(a2, "ACILIS") and k(a2, "U12A") == IMZA
       and k(a2, "U12Z") == TEKRAR and k(a2, "U12B") == 0, f"{h(a1, 'ACILIS')} -> {h(a2, 'ACILIS')} {k(a2, 'U12A')} {k(a2, 'U12B')}")
    u13 = [k(a2, "U13" + x) for x in "ABCDEF"]
    ok("B71.U13 (Review Focus 4) sil -> CIHAZ; ayni numaraya yeniden eslesme; ESKI K ile imza ret; "
       "olmayan numara YOK; tek silme NVS'e yazilir (asama 3'te 7 cihaz)",
       u13 == [0, CIHAZ, 1, IMZA, YOK, 0] and k(a3, "U15P") == 7, f"{u13} {k(a3, 'U15P')}")
    ok("B71.U14 ayar (zorunlu, misafir, tur) ve tuz/kimlik acilistan acilisa kalici",
       k(a2, "U14Y") == 0 and alanlar(a3, "U14") == [["1", "1", "3"]]
       and h(a2, "TUZ") == h(a3, "TUZ") == bytes(range(0xA0, 0xB0)).hex()
       and h(a2, "KIMLIK") == h(a3, "KIMLIK") == pr["kimlik"],
       f"{alanlar(a3, 'U14')} {h(a3, 'TUZ')} {h(a3, 'KIMLIK')}")
    ok("B71.U15 hepsini sil (Ex!) -> 0 cihaz", [k(a3, "U15A"), k(a3, "U15N")] == [0, 0],
       str([k(a3, "U15A"), k(a3, "U15N")]))
    def cz(ad):
        x = alanlar(a3, ad)
        return (int(x[0][0]), int(x[0][1])) if x and len(x[0]) == 2 else None
    ws = {x: cz("WS" + x) for x in "ABCDEFGHIJKL"}
    ok("B71.U20 (W2, D5 #10) /saat ayristiricisi TAM cozer, sonra sinirlar: 1700000000 ve "
       "4102444799 kabul; alt sinirin alti, 2100 ve sonrasi, '-1' (strtoul: 4294967295 = 2106), "
       "11+ hane, sonek, bos, bosluk/arti onek RET ve ret degeri DEGISTIRMEZ",
       ws["A"] == (0, 1700000000) and ws["E"] == (0, 4102444799)
       and all(ws[x] == (-1, 77) for x in "BCDFGHIJKL"), str(ws))
    wx = {x: cz("WX" + x) for x in "ABCDEFGHIJK"}
    ok("B71.U21 (W2, D5 #11) Ex<n> ayristiricisi TAM cozer: '!' -> 0 (hepsi), 1 ve 8 kabul; 9, 0, "
       "257 (eskiden uint8 kesimiyle 1), -255 (atoi: 1), '1x', bos, '!x', 4294967297 (32 bit "
       "tasmasiyla 1) RET ve numara DEGISMEZ (cihaz 1 silinmez)",
       wx["A"] == (0, 0) and wx["B"] == (0, 1) and wx["C"] == (0, 8)
       and all(wx[x] == (-1, 77) for x in "DEFGHIJK"), str(wx))
    wen = [int(v) for v in (alanlar(a3, "WEN") or [[]])[0]]
    ok("B71.U22 (W2, D5 #14) eslestirme numarasi RASTGELE 31 bit: ardisik uc baslatmada "
       "1..2^31-1, hepsi farkli, hicbiri oncekinin +1'i degil, 8 bite sigmayan var; ucuncu "
       "kisinin tahminleri (sonraki ardisik, 8 bite kesik, eski numara) YOK alir ve bekleyeni "
       "TUKETMEZ: dogru numara + dogru kanit ardindan KABUL",
       [k(a3, x) for x in ("WEP", "WE1", "WE2", "WE3")] == [0, 0, 0, 0] and len(wen) == 3
       and all(1 <= e <= 0x7FFFFFFF for e in wen) and len(set(wen)) == 3
       and wen[1] != wen[0] + 1 and wen[2] != wen[1] + 1 and max(wen) > 255
       and (wen[2] & 0xFF) != wen[2]
       and [k(a3, x) for x in ("WEA", "WEB", "WEC")] == [YOK, YOK, YOK] and k(a3, "WED") == 0,
       f"eno={wen} tahmin={[k(a3, x) for x in ('WEA', 'WEB', 'WEC')]} dogru={k(a3, 'WED')}")
    ok("B71.U16 acilis: her acilista AC 0, kimlik ve tuz uretildi (bos degil)",
       all(k(a, "AC") == 0 for a in (a1, a2, a3)) and h(a1, "TUZ") not in (None, "0" * 32),
       str([k(a, "AC") for a in (a1, a2, a3)]))


# ── B71.Q · 1E MQTT bildirimleri (bildirim.h) ─────────────────────────
_BLD_T0 = 1800000000
_BLD_ONEK = "0123456789abcdef0123456789abcdef"
_BLD_ANAHTAR = bytes(range(0x40, 0x60))
_BLD_TOHUM = 0x2545F491


def _bld_xs(durum: int, n: int) -> tuple[int, bytes]:
    """ornek_kayit.c sahte_rastgele (xorshift32) ile AYNI."""
    cikti = bytearray()
    for _ in range(n):
        durum ^= (durum << 13) & 0xFFFFFFFF
        durum ^= durum >> 17
        durum ^= (durum << 5) & 0xFFFFFFFF
        cikti.append((durum >> 8) & 0xFF)
    return durum, bytes(cikti)


def _bld_aead(k: bytes, nonce: bytes, aad: bytes, duz: bytes) -> bytes:
    """ornek_kayit.c sahte_aead ile AYNI formul (sinama AEAD'i; gercegi ChaCha20-Poly1305).
    Etiket AAD'ye bagli: baska konuyla dogrulanmaz."""
    ct = bytes(d ^ k[i % 32] ^ nonce[i % 12] for i, d in enumerate(duz))
    h = 0x811C9DC5
    for x in aad + b"\xff" + ct:
        h = ((h ^ x) * 16777619) & 0xFFFFFFFF
    return ct + bytes(((h >> (8 * (i & 3))) & 0xFF) ^ i ^ k[i] for i in range(16))


def _bld_ac(k: bytes, konu: str, zarf: bytes | None) -> bytes | None:
    """Zarfi SPEC bicimine gore ayir ("OKB1" | nonce 12 | sifreli | etiket 16), AAD = konu
    ile dogrula; duz metin ya da None."""
    if not zarf or len(zarf) < 32 or zarf[:4] != b"OKB1":
        return None
    nonce, govde = zarf[4:16], zarf[16:]
    duz = bytes(c ^ k[i % 32] ^ nonce[i % 12] for i, c in enumerate(govde[:-16]))
    return duz if _bld_aead(k, nonce, konu.encode(), duz) == govde else None


def bolum_bildirim() -> None:
    """1E: platformsuz bildirim cekirdegi (bildirim.h) AVR'de, tek acilis: olay uretimi
    anlik goruntu dizilerinden, esik histerezisi, kuyruk tasmasi + `n` sirasi, durum
    gerekliligi, durum/vasiyet JSON, konu, zarf yerlesimi (sahte AEAD; Python ayni
    formulle yeniden hesaplar, AAD = konu). Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md."""
    import json as _json
    print("\n── B71.Q  1E bildirim: olaylar · esik · kuyruk · n sirasi · durum · konu · zarf")
    d = subprocess.run(
        [str(AVR_GXX), "-mmcu=atmega328p", "-std=gnu++11", "-fsyntax-only", "-Wall", "-Wextra",
         f"-I{KOD}", "-x", "c++", "-"],
        input='#include "bildirim.h"\nint main() { return 0; }\n', capture_output=True,
        text=True, encoding="utf-8", errors="replace")
    cpp = (d.stderr or "") if (d.returncode or "warning:" in (d.stderr or "")) else ""
    ok("B71.Q0 bildirim.h kartin varsayilanlariyla (16 x 192) C++ olarak (.ino) UYARISIZ "
       "(-Wall -Wextra)", not cpp, cpp.strip()[:300])
    sat = kos(derle("BILDIRIM"))

    def k(ad):
        return _say(sat, ad)

    def ham(ad):
        return [x[0] for x in alanlar(sat, ad) if x]

    def js(s):
        try:
            return _json.loads(s)
        except (ValueError, TypeError):
            return None

    def ob(ad):
        return [js(x) for x in ham(ad)]

    def hx(ad):
        x = alanlar(sat, ad)
        try:
            return bytes.fromhex(x[0][0]) if x and x[0] else None
        except ValueError:
            return None
    T0 = _BLD_T0

    def ol(n, ad, a=7, t=T0, **ek):
        return {"n": n, "a": a, "t": t, "o": ad, **ek}
    q1 = [k(x) for x in ("Q1A", "Q1B", "Q1C")]
    e1 = ob("E1")
    ok("B71.Q1 basladi tarama BITINCE (TARIYOR'da hicbir olay yok — esitlenmemis 900 binde "
       "olsa bile esik de yok), ilk olay n 1: a, t, devam, oturum; ayni goruntu tekrar olay "
       "uretmez",
       q1 == [0, 3, 0] and ham("E1")[:1]
       == ['{"n":1,"a":7,"t":1800000000,"o":"basladi","devam":2,"oturum":42}'],
       f"{q1} {ham('E1')[:1]}")
    ok("B71.Q2 acilis taramasinda kapanan oturum (sebep 5) ve biten pil testi (sayaclar ilk "
       "goruntude 1): basladi'dan SONRA, sirayla kayit_bitti sonra pil_bitti (son gorulen "
       "sayaclar 0'dan baslar)",
       e1 == [ol(1, "basladi", devam=2, oturum=42),
              ol(2, "kayit_bitti", sebep=5, oturum=41, nokta=777),
              ol(3, "pil_bitti", durum=1, mah_milli=1000, wh_milli=3700, sure_ms=60000)],
       str(e1))
    q2 = [k(x) for x in ("Q2A", "Q2B", "Q2C")]
    ok("B71.Q3 bitir_say ARTINCA kayit_bitti (sebep, oturum, nokta); sayac degismezse tekrar "
       "YOK; sayac geri giderse olay YOK",
       q2 == [1, 0, 0] and ob("E2") == [ol(4, "kayit_bitti", sebep=1, oturum=42, nokta=1234)],
       f"{q2} {ob('E2')}")
    q3 = [k(x) for x in ("Q3A", "Q3B", "Q3C", "Q3D")]
    ok("B71.Q4 dolu yalniz DOLU'ya GECISTE: DOLU'da kalmak tekrar uretmez, BOS'a cikip yeniden "
       "DOLU olunca yine (ek alan yok)",
       q3 == [1, 0, 0, 1] and ob("E3") == [ol(5, "dolu"), ol(6, "dolu")], f"{q3} {ob('E3')}")
    q4 = [k(x) for x in ("Q4A", "Q4B", "Q4C")]
    ok("B71.Q5 pil_say ARTINCA pil_bitti: durum, mah_milli, wh_milli, sure_ms (tamsayi milli "
       "birim); tekrar YOK; sayac geri giderse olay YOK",
       q4 == [1, 0, 0] and ob("E4") == [ol(7, "pil_bitti", durum=2, mah_milli=2345678,
                                         wh_milli=8765432, sure_ms=36000123)],
       f"{q4} {ob('E4')}")
    q5 = [k("Q5" + x) for x in "ABCDEFGHIJK"]
    ok("B71.Q6 esik (varsayilan 500, 2000 -> 1000'e kirpilir): >= esikte BIR kez; ustte kalirken "
       "ve 450/400'e inip yeniden cikinca TEKRAR YOK; esik-100'un ALTINA (399) ya da 0'a inince "
       "yeniden kurulur ve tekrar uretir; tarama surerken karar yok",
       k("ESIK") == 500 and k("ESIK2") == 1000 and q5 == [0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1]
       and ob("E5") == [ol(8, "esik", deger=500, esik=500), ol(9, "esik", deger=520, esik=500),
                        ol(10, "esik", deger=900, esik=500)],
       f"{k('ESIK')} {k('ESIK2')} {q5} {ob('E5')}")
    e6 = ob("E6")
    ok("B71.Q7 kuyruk tasmasi (4 yer, 6 olay): EN ESKI iki olay (n 11, 12) duser, dusen 2; "
       "kalanlar sirayla n 13-16",
       k("Q6ADET") == 4 and k("Q6DUSEN") == 2
       and e6 == [ol(13, "kayit_bitti", sebep=1, oturum=42, nokta=102),
                  ol(14, "kayit_bitti", sebep=1, oturum=42, nokta=103),
                  ol(15, "kayit_bitti", sebep=1, oturum=42, nokta=104),
                  ol(16, "deneme", a=9, t=T0 + 5)],
       f"adet={k('Q6ADET')} dusen={k('Q6DUSEN')} {[x and x.get('n') for x in e6]}")
    ok("B71.Q8 deneme (Qt): ayni kuyruk ve numara yolundan, a/t cagirandan, ek alan yok; dolu "
       "kuyrukta o da en eskiyi dusurur",
       ham("E6")[-1:] == ['{"n":16,"a":9,"t":1800000005,"o":"deneme"}'] and k("Q6DUSEN") == 2,
       str(ham("E6")[-1:]))
    ok("B71.Q9 kuyruk uclari: bosken bas BLD_E_BOS (-4); kucuk tamponla bas BLD_E_YER (-1) ve "
       "olay KUYRUKTA KALIR, sonra tam alinir",
       k("Q7BOS") == -4 and k("Q7A") == 1 and k("Q7YER") == -1 and k("Q7ADET") == 1
       and ob("E7") == [ol(17, "dolu")],
       f"{k('Q7BOS')} {k('Q7YER')} {k('Q7ADET')} {ob('E7')}")
    hepsi = [ham("E" + str(i)) for i in range(1, 8)]
    nler = [(js(x) or {}).get("n") for grup in hepsi for x in grup]
    ok("B71.Q10 n acilis basina 1'den surekli artar; tek bosluk tasmada dusen 11-12 (alici "
       "kaybi bosluktan gorur)",
       nler == list(range(1, 11)) + list(range(13, 18)), str(nler))
    duz = [x for grup in hepsi for x in grup] + ham("E8")
    ok("B71.Q11 olay JSON'u kompakt ve tamsayi: ham metin == json.dumps(ayirici ',' ':'), anahtar "
       "sirasi n, a, t, o",
       bool(duz) and all(js(x) is not None
                         and x == _json.dumps(js(x), separators=(",", ":"))
                         and list(js(x))[:4] == ["n", "a", "t", "o"] for x in duz),
       f"{len(duz)} olay")
    e8 = ham("E8")
    m = 0xFFFFFFFF
    ok("B71.Q12 en buyuk olay (pil_bitti, butun sayilar en buyuk) BLD_OLAY_AZAMI'ye TAM sigar: "
       "140 karakter + NUL = 141 (AVR'de BLD_MESAJ = 141), dusmez",
       k("Q8") == 1 and k("Q8DUSEN") == 2 and len(e8) == 1 and len(e8[0]) == 140
       and js(e8[0]) == ol(4294967290, "pil_bitti", a=m, t=m, durum=255, mah_milli=m,
                           wh_milli=m, sure_ms=m),
       f"Q8={k('Q8')} dusen={k('Q8DUSEN')} uzunluk={[len(x) for x in e8]}")
    dg = [k("D" + str(i)) for i in range(16)]
    ok("B71.Q13 durum gerekli: hic yayinlanmadiysa; 60 s dolunca (59.999 s degil); doluluk ya "
       "da esitlenmemis >= 10 binde oynayinca (9 degil, iki yon); kayit/oturum/tur degisince; "
       "yayinlanan imza yenilenir; ms sayaci sarmasi dogru",
       dg == [1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0], str(dg))
    dj = '{"c":1,"a":7,"t":1800000000,"k":2,"o":42,"y":1,"d":100,"e":50,"f":"B71-test"}'
    ok("B71.Q14 durum JSON birebir; tam sigan tamponda yazilir, bir bayt kisada BLD_E_YER ve "
       "YARIM dize birakmaz; firmware adinda \" ve \\ kacislanir, denetim karakteri '?'",
       ham("DJ") == [dj] and k("DJN") == len(dj) and k("DJT") == len(dj) and k("DJU") == -1
       and k("DJU0") == 0 and (js((ham("DJE") or [""])[0]) or {}).get("f") == 'A"1\\?'
       and k("DJEN") == len((ham("DJE") or [""])[0]),
       f"{ham('DJ')} DJU={k('DJU')} DJE={ham('DJE')}")
    ok("B71.Q15 vasiyet JSON birebir {\"c\":0,\"a\":<acilis>}",
       ham("VJ") == ['{"c":0,"a":7}'] and k("VJN") == 13, str(ham("VJ")))
    konu, konu2 = f"ok/{_BLD_ONEK}/olay", f"ok/{_BLD_ONEK}/durum"
    kb = [k("KB" + str(i)) for i in range(1, 8)]
    ok("B71.Q16 konu ok/<onek>/<son>; onek tam 32 KUCUK hex (buyuk harf, 31 karakter ret), son "
       "bos degil ve '/', '+', '#' icermez (BLD_E_ARG -3); tampon tam sigarsa yazilir, kisaysa "
       "BLD_E_YER",
       ham("KONU") == [konu] and k("KN") == 40 and ham("KONU2") == [konu2] and k("KD") == 41
       and kb == [-3, -3, -3, -3, -1, 40, -3], f"{ham('KONU')} {kb}")
    s, n1 = _bld_xs(_BLD_TOHUM, 12)
    s, n2 = _bld_xs(s, 12)
    s, n4 = _bld_xs(s, 12)
    z1, z2, z4 = hx("Z1"), hx("Z2"), hx("Z4")
    z1j = (ham("Z1J") or [""])[0].encode()
    ok("B71.Q17 zarf yerlesimi: \"OKB1\" | nonce 12 (rastgeleden) | sifreli | etiket 16, boy = "
       "JSON + 32; Python AYNI AEAD'le AAD = olay konusu ile dogrular ve olayi geri alir; ayni "
       "zarf durum konusuyla DOGRULANMAZ (AAD baglayici)",
       z1 is not None and z1[:4] == b"OKB1" and z1[4:16] == n1 and len(z1) == len(z1j) + 32
       and _bld_ac(_BLD_ANAHTAR, konu, z1) == z1j
       and js(z1j.decode()) == ol(1, "basladi", devam=0, oturum=0)
       and _bld_ac(_BLD_ANAHTAR, konu2, z1) is None,
       f"{z1[:16].hex() if z1 else None} boy={len(z1) if z1 else None}")
    ok("B71.Q18 vasiyet durum konusunda zarflanir; her zarf YENI nonce (rastgeleden sirayla)",
       z2 is not None and k("Z2N") == 45 and z2[4:16] == n2 and n2 != n1
       and _bld_ac(_BLD_ANAHTAR, konu2, z2) == b'{"c":0,"a":7}',
       f"{z2[4:16].hex() if z2 else None}")
    ok("B71.Q19 zarf hatalari: bir bayt kisa tampon BLD_E_YER ve rastgele HARCANMAZ (sonraki "
       "zarfin nonce'u siradaki blok); tam sigan tampon yazilir; AEAD hatasi BLD_E_KRIPTO ve "
       "cikti SILINIR; AEAD islevi yoksa BLD_E_KRIPTO",
       k("Z3") == -1 and z4 is not None and len(z4) == 45 and z4[4:16] == n4
       and _bld_ac(_BLD_ANAHTAR, konu2, z4) == b'{"c":0,"a":7}'
       and k("Z5") == -2 and k("Z5S") == 0 and k("Z6") == -2,
       f"Z3={k('Z3')} Z4={z4[4:16].hex() if z4 else None} Z5={k('Z5')} Z6={k('Z6')}")
    def ez(ad):
        x = alanlar(sat, ad)
        return (int(x[0][0]), int(x[0][1])) if x and len(x[0]) == 2 else None
    wq = {x: ez("WQ" + x) for x in "ABCDEFGHIJK"}
    ok("B71.Q21 (W2, E3) Qe<binde> ayristiricisi: bos -> 0 (varsayilana don), 700 / 100 / 1000 "
       "kabul; 99, 1001, -5, 7x, 0, 65636 (16 bit tasmasi), bosluk onekli RET ve deger DEGISMEZ",
       wq["A"] == (0, 0) and wq["B"] == (0, 700) and wq["C"] == (0, 100) and wq["D"] == (0, 1000)
       and all(wq[x] == (-1, 77) for x in "EFGHIJK"), str(wq))
    wqa = [k("WQ" + x) for x in "12345"]
    wqv = ob("WQV")
    ok("B71.Q22 (W2, E3) calisirken esik degisimi: olay numarasi SURER (bld_kur gibi sifirlamaz); "
       "esik indirilince (500 -> 300) mevcut 400 HEMEN bildirilir; bildirilmisken yine indirmek "
       "(350) TEKRAR uretmez; yukseltmek (800) histerezisle yeniden kurar ve 820'de yeni esikle "
       "bildirir; gecersiz (30) -> varsayilan 500",
       wqa == [1, 1, 0, 0, 1] and k("WQE1") == 800 and k("WQE2") == 500
       and [x and x.get("o") for x in wqv] == ["basladi", "esik", "esik"]
       and wqv[1:] == [ol(2, "esik", a=8, deger=400, esik=300), ol(3, "esik", a=8, deger=820, esik=800)],
       f"{wqa} {k('WQE1')} {k('WQE2')} {wqv}")
    ok("B71.Q20 AVR yigini (2 KB RAM) tasmadi: bss sonu ile en derin yigin arasi >= 64 B",
       (k("YIGIN") or 0) >= 64, f"{k('YIGIN')} B")


# ── B71.MQ · 1E MQTT 3.1.1 istemci paketleri (mqtt_paket.h) ───────────
# (B71.M1-M5 bolum_mantiksal'in; bu bolum B71.MQ*)
def _mq_connect_coz(p: bytes | None) -> dict | None:
    """CONNECT'i ELLE coz (MQTT 3.1.1 §3.1) — kopru/mqtt_istemci.py'den de C'den de
    BAGIMSIZ: sabit baslik, kalan uzunluk, protokol adi/seviyesi, bayraklar,
    keepalive, kimlik, [vasiyet konusu + yuku], [kullanici], [parola]; artik bayt 0 olmali."""
    if not p or p[0] != 0x10:
        return None
    try:
        kalan, carpan, i = 0, 1, 1
        while True:
            b = p[i]
            i += 1
            kalan += (b & 0x7F) * carpan
            if not b & 0x80:
                break
            carpan *= 128
            if i > 4:
                return None
        g = p[i:]
        if len(g) != kalan:
            return None
        j = 0

        def al(n: int) -> bytes:
            nonlocal j
            v = g[j:j + n]
            if len(v) != n:
                raise IndexError
            j += n
            return v

        def dize() -> bytes:
            return al(int.from_bytes(al(2), "big"))
        d = {"proto": dize(), "seviye": al(1)[0], "bayrak": al(1)[0],
             "keepalive": int.from_bytes(al(2), "big"), "istemci": dize()}
        if d["bayrak"] & 0x04:
            d["vkonu"] = dize()
            d["vyuk"] = dize()
        if d["bayrak"] & 0x80:
            d["kul"] = dize()
        if d["bayrak"] & 0x40:
            d["par"] = dize()
        d["artik"] = len(g) - j
        return d
    except IndexError:
        return None


def bolum_mqtt() -> None:
    """1E: kartin MQTT 3.1.1 istemci paketleri (mqtt_paket.h) AVR'de; baytlar Python'da
    IKI bagimsiz yoldan cozulur: kopru/mqtt_istemci.py (Ayristirici, publish_coz,
    uzunluk_kodla/coz) ve elle CONNECT cozumu (_mq_connect_coz)."""
    import mqtt_istemci as MI
    print("\n── B71.MQ  1E MQTT 3.1.1: CONNECT · PUBLISH · kalan uzunluk · okuyucu · URI")
    d = subprocess.run(
        [str(AVR_GXX), "-mmcu=atmega328p", "-std=gnu++11", "-fsyntax-only", "-Wall", "-Wextra",
         f"-I{KOD}", "-x", "c++", "-"],
        input='#include "mqtt_paket.h"\nint main() { return 0; }\n', capture_output=True,
        text=True, encoding="utf-8", errors="replace")
    cpp = (d.stderr or "") if (d.returncode or "warning:" in (d.stderr or "")) else ""
    ok("B71.MQ0 mqtt_paket.h C++ olarak (.ino) UYARISIZ (-Wall -Wextra)", not cpp, cpp.strip()[:300])
    sat = kos(derle("MQTT"))

    def k(ad):
        return _say(sat, ad)

    def pk(ad):
        x = alanlar(sat, ad)
        if not x or not x[0]:
            return None, None
        try:
            n = int(x[0][0])
            return n, (bytes.fromhex(x[0][1]) if n > 0 and len(x[0]) > 1 else None)
        except ValueError:
            return None, None

    def ayir(p):
        """Ayristirici ile TEK paket, artik bayt yok."""
        if not p:
            return None
        a = MI.Ayristirici()
        a.besle(p)
        try:
            s = a.sonraki()
        except MI.MqttHata:
            return None
        return s if s and a.bekleyen() == 0 else None

    def pub(p):
        s = ayir(p)
        try:
            return (s[0], MI.publish_coz(*s)) if s else None
        except MI.MqttHata:
            return None
    VKONU = b"ok/0123456789abcdef0123456789abcdef/durum"
    VAS = bytes([0x4F, 0x4B, 0x42, 0x31, 0x00, 0xFF, 0x10, 0x20, 0x7F, 0x80, *range(1, 11)])
    n1, c1 = pk("C1")
    d1 = _mq_connect_coz(c1)
    a1 = ayir(c1)
    ok("B71.MQ1 CONNECT vasiyetli (QoS 1, retain) + kullanici + parola: elle cozum — 'MQTT' "
       "seviye 4, bayrak 0xEE (kul|par|v.retain|v.QoS1|vasiyet|temiz, bit0 0), keepalive 5, "
       "kimlik, vasiyet konusu + ikili yuk (00/FF dahil), kullanici, parola, artik 0; "
       "Ayristirici tek paket, kalan 101 (10 + 12 + 43 + 22 + 6 + 8)",
       n1 == 103 and d1 == {"proto": b"MQTT", "seviye": 4, "bayrak": 0xEE, "keepalive": 5,
                            "istemci": b"olcum-a1b2", "vkonu": VKONU, "vyuk": VAS,
                            "kul": b"kart", "par": b"p@ss:1", "artik": 0}
       and a1 is not None and a1[0] == 0x10 and len(a1[1]) == 101,
       f"n={n1} {d1 and {x: d1[x] for x in ('bayrak', 'keepalive', 'artik')}}")
    n2, c2 = pk("C2")
    d8 = _mq_connect_coz(pk("C8")[1])
    d7b, d7c = _mq_connect_coz(pk("C7B")[1]), _mq_connect_coz(pk("C7C")[1])
    ok("B71.MQ2 CONNECT vasiyetsiz/kullanicisiz birebir 10 0d 00 04 'MQTT' 04 02 00 3c 00 01 'x'; "
       "kullanici var parola yok -> bayrak 0x82, parola alani YOK; bos kimlik (\"\"/NULL) temiz "
       "oturumla gecerli",
       c2 == bytes.fromhex("100d00044d5154540402003c000178") and n2 == 15
       and d8 == {"proto": b"MQTT", "seviye": 4, "bayrak": 0x82, "keepalive": 60,
                  "istemci": b"x", "kul": b"u", "artik": 0}
       and d7b is not None and d7b["bayrak"] == 0x02 and d7b["istemci"] == b""
       and d7b["artik"] == 0 and pk("C7B")[1] == pk("C7C")[1],
       f"{c2.hex() if c2 else None} {d8} {d7b}")
    ok("B71.MQ3 CONNECT ret (MQP_E_ALAN -5): kullanicisiz parola (NULL ve \"\" kullanici, "
       "MQTT-3.1.2-22), vasiyet QoS 2, vasiyetsiz retain / QoS",
       [k(x) for x in ("C3", "C3B", "C4", "C5", "C5B")] == [-5] * 5,
       str([k(x) for x in ("C3", "C3B", "C4", "C5", "C5B")]))
    ok("B71.MQ4 (inceleme duzeltmesi) vasiyet konusu da konu ADI: '+' / '#' / bos -> E_KONU (-3); "
       "bos istemci kimligi temiz oturumsuz -> E_ALAN (MQTT-3.1.3-7)",
       [k(x) for x in ("C6", "C6B", "C6C", "C7")] == [-3, -3, -3, -5],
       str([k(x) for x in ("C6", "C6B", "C6C", "C7")]))
    ok("B71.MQ5 CONNECT tampon siniri: bir bayt kisa E_YER (-1), tam sigan yazilir (iki paket)",
       k("C1Y") == -1 and k("C1T") == n1 and k("C2Y") == -1 and k("C2T") == n2,
       str([k(x) for x in ("C1Y", "C1T", "C2Y", "C2T")]))
    n_p1, p1 = pk("P1")
    n_p2, p2 = pk("P2")
    u1, u2 = pub(p1), pub(p2)
    ok("B71.MQ6 PUBLISH QoS 0 retain: ilk bayt 0x31, publish_coz -> (konu, yuk, retain, 0, "
       "pid YOK) — verilen pid 77 yazilmaz",
       n_p1 == 19 and u1 == (0x31, ("ok/x/durum", b'{"c"}', True, 0, None)), str(u1))
    ok("B71.MQ7 PUBLISH QoS 1: ilk bayt 0x32 (retain yok), pid 0x1234 konudan sonra, yuk sonra",
       n_p2 == 18 and u2 == (0x32, ("ok/x/olay", b'{"c', False, 1, 0x1234)), str(u2))
    desen = bytes((i * 7 + 3) & 0xFF for i in range(125))
    n7a, p7a = pk("P7A")
    n7b, p7b = pk("P7B")
    p5 = [int(x[0]) for x in alanlar(sat, "P5")]
    ok("B71.MQ8 PUBLISH ret: QoS 1 pid 0 / QoS 2 -> E_ALAN; konu '+', '#', ortada '+', bos, "
       "NULL -> E_KONU",
       k("P3") == -5 and k("P4") == -5 and p5 == [-3, -3, -3, -3] and k("P5N") == -3,
       f"{k('P3')} {k('P4')} {p5} {k('P5N')}")
    ok("B71.MQ9 her kurucuda tampon siniri: PUBLISH (QoS 0/1, kalan 127/128) bir bayt kisa E_YER, "
       "tam sigan yazilir; kalan 16383/16384'te (toplam 16386/16388) bir eksik azami E_YER "
       "(YAZMADAN); PINGREQ/DISCONNECT 1 bayta E_YER, 2'ye 2",
       [k(x) for x in ("P1Y", "P1T", "P2Y", "P2T", "P7AY", "P7BY", "P7BT", "P8A", "P8B",
                       "K1Y", "K1T", "K2Y", "K2T")]
       == [-1, n_p1, -1, n_p2, -1, -1, n7b, -1, -1, -1, 2, -1, 2] and n7b == 131,
       str([k(x) for x in ("P1Y", "P1T", "P2Y", "P2T", "P7AY", "P7BY", "P7BT", "P8A", "P8B",
                           "K1Y", "K1T", "K2Y", "K2T")]))
    ok("B71.MQ10 kalan uzunluk sinirinda PUBLISH: 127 -> tek bayt 7f (toplam 129), 128 -> 80 01 "
       "(toplam 131); kopru uzunluk_kodla ile ayni, publish_coz yuku birebir geri verir",
       n7a == 129 and n7b == 131 and p7a is not None and p7b is not None
       and p7a[1:2] == MI.uzunluk_kodla(127) == b"\x7f"
       and p7b[1:3] == MI.uzunluk_kodla(128) == b"\x80\x01"
       and pub(p7a) == (0x30, ("t", desen[:124], False, 0, None))
       and pub(p7b) == (0x30, ("t", desen, False, 0, None)),
       f"{p7a[:3].hex() if p7a else None} {p7b[:4].hex() if p7b else None}")
    L = alanlar(sat, "L")
    beklenen_boy = {0: 1, 1: 1, 127: 1, 128: 2, 16383: 2, 16384: 3, 2097151: 3, 2097152: 4,
                    268435455: 4}

    def l_dogru(x):
        try:
            v, boy, n, h = int(x[0]), int(x[1]), int(x[2]), bytes.fromhex(x[3])
        except (ValueError, IndexError):
            return False
        return (boy == n == len(h) == beklenen_boy.get(v) and h == MI.uzunluk_kodla(v)
                and MI.uzunluk_coz(h) == (v, len(h)))
    ok("B71.MQ11 kalan uzunluk kodlayicisi 0/1/127/128/16383/16384/2097151/2097152/268435455: "
       "boy ve baytlar kopru uzunluk_kodla ile ayni, uzunluk_coz geri verir",
       [int(x[0]) for x in L] == list(beklenen_boy) and all(l_dogru(x) for x in L),
       str([x[:4] for x in L if not l_dogru(x)][:3]))
    ok("B71.MQ12 PINGREQ c0 00, DISCONNECT e0 00",
       pk("K1") == (2, b"\xc0\x00") and pk("K2") == (2, b"\xe0\x00"), f"{pk('K1')} {pk('K2')}")
    akis = bytes.fromhex((alanlar(sat, "AKIS") or [["00"]])[0][0])
    a = MI.Ayristirici()
    a.besle(akis)
    py = []
    while (s := a.sonraki()) is not None:
        ilk, g = s
        tip = ilk >> 4
        py.append([str(tip), str(len(g)),
                   str(g[1] if tip == 2 and len(g) == 2 else -1),
                   str(int.from_bytes(g, "big") if tip == 4 and len(g) == 2 else -1),
                   g[:8].hex() or "-"])
    ra, rb, rc = alanlar(sat, "RA"), alanlar(sat, "RB"), alanlar(sat, "RC")
    ok("B71.MQ13 okuyucu 1 baytlik parcalarla: 6 paketin hepsi, kopru Ayristirici'nin ayni "
       "akistan cikardigiyla birebir (tip, uzunluk, CONNACK kodu, PUBACK pid, ilk 8 bayt)",
       len(py) == 6 and a.bekleyen() == 0 and ra == py, f"C={ra} PY={py}")
    ok("B71.MQ14 okuyucu 5 baytlik parcalarla (paket sinirlari kayik) ve TEK parcada (birkac "
       "paket birden) ayni sonuc",
       rb == py and rc == py, f"RB={len(rb)} RC={len(rc)}")
    ok("B71.MQ15 okunan degerler: CONNACK kod 0 ve 5, PUBACK pid 0x1234 ve 7, PINGRESP govdesiz "
       "(uzunluk 0), MQP_GOVDE_AZAMI'den uzun PUBLISH (130, 2 bayt uzunluk) ilk 8 bayti saklanip "
       "atlanir, ardindaki PUBACK dogru",
       ra == [["2", "2", "0", "-1", "0000"], ["4", "2", "-1", "4660", "1234"],
              ["13", "0", "-1", "-1", "-"], ["2", "2", "5", "-1", "0105"],
              ["3", "130", "-1", "-1", "0003616263101112"], ["4", "2", "-1", "7", "0007"]],
       str(ra))
    try:
        MI.uzunluk_coz(b"\xff\xff\xff\xff\x01")
        py_bozuk = False
    except MI.MqttHata:
        py_bozuk = True
    ok("B71.MQ16 5 baytlik kalan uzunluk MQP_E_BOZUK (-4): tek parcada baslik + 4 uzunluk bayti "
       "tuketilir, 1 baytlik parcalarda 5. bayt (4. uzunluk bayti) hata verir, bozuk okuyucu "
       "bozuk kalir; kopru uzunluk_coz da reddeder",
       [k(x) for x in ("BZ", "BZK", "BZ2", "BZ1", "BZ1R")] == [-4, 5, -4, 4, -4] and py_bozuk,
       str([k(x) for x in ("BZ", "BZK", "BZ2", "BZ1", "BZ1R")]))
    ok("B71.MQ17 4 baytlik en buyuk kalan uzunluk (ff ff ff 7f = 268435455) ve 80 80 80 01 "
       "(2097152) dogru cozulur, govde beklenir (0); bos parca 0 bayt tuketir",
       [k(x) for x in ("L4", "L4K", "L4U", "L4B", "L4BU", "N0", "N0K")]
       == [0, 5, 268435455, 0, 2097152, 0, 0]
       and MI.uzunluk_coz(b"\xff\xff\xff\x7f") == (268435455, 4),
       str([k(x) for x in ("L4", "L4K", "L4U", "L4B", "L4BU", "N0", "N0K")]))
    U = {x: alanlar(sat, x)[0] if alanlar(sat, x) else None
         for x in ("U" + c for c in "ABCDEFGHIJKLMNOPQRST")}
    ok("B71.MQ18 URI: mqtts varsayilan 8883 + TLS, mqtt varsayilan 1883 + TLS yok, acik port, "
       "65535 siniri, ad tampona TAM sigar (8 karakter, azami 9)",
       U["UA"] == ["0", "8883", "1", "abc.hivemq.cloud"] and U["UB"] == ["0", "1883", "0", "localhost"]
       and U["UC"] == ["0", "1234", "1", "h-1.Example"] and U["UD"] == ["0", "65535", "1", "h"]
       and U["UO"] == ["0", "8883", "1", "abcdefgh"],
       str([U[x] for x in ("UA", "UB", "UC", "UD", "UO")]))
    ret = [x for x in ("UE", "UF", "UG", "UH", "UI", "UJ", "UK", "UL", "UM", "UN", "UP", "UQ",
                       "UR", "US", "UT")]
    ok("B71.MQ19 URI ret (E_ALAN -5): port 0 / 65536 / bos / harfli / tasan / eksi / sonda '/'; "
       "'@' (kullanici bilgisi), '/' (yol), '?' (sorgu); bos ad (iki bicim); ad tampona sigmiyor; "
       "baska sema (http, ws)",
       all(U[x] == ["-5"] for x in ret), str({x: U[x] for x in ret if U[x] != ["-5"]}))


BOLUMLER = [bolum_nor, bolum_bicim, bolum_noktaci, bolum_gunluk, bolum_yazici,
            bolum_tarama, bolum_mantiksal, bolum_yonet, bolum_pil, bolum_halka, bolum_ayrinti,
            bolum_hazir, bolum_skop, bolum_plan, bolum_plan_kanit, bolum_guvenlik, bolum_kalgec,
            bolum_dizin,
            bolum_kesinti, bolum_bildirim, bolum_mqtt]


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
