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
CPP_BASLIKLAR = ["kayit_bicim.h", "kayit_nokta.h", "kayit_gunluk.h", "kayit_oturum.h"]
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
    # Son inceleme bulgu 6: bicim surumu yaziliyor, bilinmeyen tur reddedilmiyor.
    basla_c = bytes.fromhex(s["BASLA"][0])
    ok("B71.B12 BASLA bayt 2-3 = bicim surumu (1): kayit hangi bicimde yazildigini soyler",
       basla_c[2:4] == bytes([KB.SURUM, 0]), basla_c[2:4].hex())
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
    ok("B71.G16 bilinmeyen kayit turu (9) gecerli: tarama durmaz, esitleme onu tasir",
       tek.get("EK9") == ["37"]
       and d["G12"] == _g(38, 1, 56, bozuk=2, kull=568, onaysiz=568)
       and [k.tur for k in kay9] == [9], f"{d['G12']} {[k.tur for k in kay9]}")
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
            bolum_tarama, bolum_dizin, bolum_kesinti]


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
