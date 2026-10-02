# -*- coding: utf-8 -*-
"""B73 / 2A — kayit bicimi CAPRAZ UYGULAMA vektorleri (tasarim 2026-10-02 O3).

Python basvurusu `kopru/kayit_bicim.py` (kartla dogrulandi) sabit tohumlu sentetik
akislari cozer; sonuc `ortak/test/vektor/kayit.json`'a yazilir. JS (`ortak/src/kayit.js`)
`node --test ortak/test/kayit.test.js` ile ayni ciktiyi BIT BIT vermeli.

    python ortak_vektor_kayit.py            # dosyayi (yeniden) yaz
    python ortak_vektor_kayit.py --denetle  # depodaki dosya Python'la hala ayni mi (degilse 1)

Kapsam: her kayit turu (BASLA v1/v2, NOKTA, DEVAM, BITIR, SAAT, TEKRAR, OLAY'in her turu,
NOT + degistirir, AYRINTI + bosluklar/sarma/esit yuvarlama, SKOP + META), coklu oturum,
ortada bozuk CRC, kesik kuyruk, bilinmeyen tur, sektorlu flas goruntusu, her *_coz'un
sinir uzunluklari (Python'un REDDETTIGI girdiler dahil), paketleyiciler, volt/amper.

JSON: float repr ile (JS ayni double'i okur); NaN/sonsuz {"$f": ...}, bayt {"$b": hex},
int anahtarli sozluk {"$map": [[k, v], ...]} (sira korunur), Python istisnasi {"hata": ad}.
Rastgelelik kendi splitmix64'umuzden: Python surumune bagli degil.
"""
from __future__ import annotations

import argparse
import dataclasses
import inspect
import json
import math
import struct
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
import kayit_bicim as KB  # noqa: E402

HEDEF = KOK / "ortak" / "test" / "vektor" / "kayit.json"
M64 = (1 << 64) - 1


# ── deterministik rastgele ────────────────────────────────────────────
class Rng:
    def __init__(self, tohum: int):
        self.s = tohum & M64

    def _u64(self) -> int:
        self.s = (self.s + 0x9E3779B97F4A7C15) & M64
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def tam(self, a: int, b: int) -> int:
        return a + self._u64() % (b - a + 1)

    def kesir(self, a: float, b: float) -> float:
        return a + (b - a) * ((self._u64() >> 11) / 2**53)

    def secim(self, s):
        return s[self.tam(0, len(s) - 1)]

    def bayt(self, n: int) -> bytes:
        return bytes(self.tam(0, 255) for _ in range(n))


# ── JSON'a cevirme ────────────────────────────────────────────────────
def jmap(d: dict) -> dict:
    return {"$map": [[j(k), j(v)] for k, v in d.items()]}


def j(x):
    if x is None or isinstance(x, (bool, str)):
        return x
    if isinstance(x, int):
        assert abs(x) < 2**53, x          # JS Number'a kayipsiz sigmali
        return x
    if isinstance(x, float):
        if math.isnan(x):
            return {"$f": "nan"}
        if math.isinf(x):
            return {"$f": "inf" if x > 0 else "-inf"}
        return x
    if isinstance(x, (bytes, bytearray)):
        return {"$b": bytes(x).hex()}
    if isinstance(x, (list, tuple)):
        return [j(e) for e in x]
    if isinstance(x, KB.Oturum):
        d = {}
        for f in dataclasses.fields(x):
            v = getattr(x, f.name)
            d[f.name] = jmap(v) if f.name in ("notlar", "skoplar") else j(v)
        return d
    if dataclasses.is_dataclass(x):
        return {f.name: j(getattr(x, f.name)) for f in dataclasses.fields(x)}
    if isinstance(x, dict):
        assert all(isinstance(k, str) for k in x), x
        return {k: j(v) for k, v in x.items()}
    raise TypeError(type(x))


def hata(e: Exception) -> dict:
    return {"hata": type(e).__name__}


def dene(f, *a):
    try:
        return j(f(*a))
    except Exception as e:  # noqa: BLE001 — Python'un reddi de vektor
        return hata(e)


# ── uretec yardimcilari ───────────────────────────────────────────────
def kanal_r(r: Rng, n0: float) -> KB.Kanal:
    return KB.Kanal(n0 * r.kesir(0.99, 1.01), r.secim([6.144, 4.096, 2.048, 1.024]),
                    r.kesir(0.98, 1.02), r.tam(-400, 400), r.kesir(0.0, 0.5))


def kal_r(r: Rng) -> KB.Kalibrasyon:
    return KB.Kalibrasyon(kanal_r(r, 21.0), kanal_r(r, 201.0), r.tam(-300, 300),
                          r.secim([0.256, 0.512, 1.024]), r.secim([0.005, 0.015, 0.0049]),
                          r.kesir(0.97, 1.03), r.secim([50.0, 60.0]),
                          (r.kesir(-80, 80), r.kesir(-80, 80)))


def basla_r(r: Rng, tur: int, hiz: int, kal_no: int = 0, surum: str = "A3-1C4d") -> KB.Basla:
    return KB.Basla(tur, KB.KAL_BICIM, hiz, r.secim([0, 1_790_000_000 + r.tam(0, 10**6)]),
                    r.tam(0, 2**32 - 1), r.tam(1, 60), surum, kal_r(r), KB.SURUM, kal_no)


def basla_v1(b: KB.Basla) -> bytes:
    """Bicim surum 1 (98 B, kal_no yok) — 1B oncesi kartin yazdigi."""
    y = bytearray(KB.basla_paketle(b)[:KB.BASLA_V1_BAYT])
    struct.pack_into("<H", y, 2, 1)
    return bytes(y)


def nokta_r(r: Rng, ms: int) -> KB.Nokta:
    vmin = r.tam(-32768, 32767)
    vmaks = r.tam(vmin, 32767)
    imin = r.tam(-32768, 32767)
    imaks = r.tam(imin, 32767)
    return KB.Nokta(ms, r.tam(0, 65535), r.tam(0, 255), r.kesir(vmin, vmaks), vmin, vmaks,
                    r.kesir(imin, imaks), imin, imaks, r.kesir(-500, 500), r.kesir(-500, 0),
                    r.kesir(0, 500))


def nokta_yuk(ilk: int, ps, kuyruk: bytes = b"") -> bytes:
    return struct.pack("<I", ilk) + b"".join(KB.nokta_paketle(p) for p in ps) + kuyruk


def olay_r(r: Rng, tur: int, ms: int) -> dict:
    if tur == KB.KO_PIL_AYAR:
        return {"tur": tur, "kart_ms": ms, "kesme_v": r.kesir(2.5, 3.2), "ocv": r.kesir(3.5, 4.2),
                "azami_s": r.tam(0, 86400), "dcir_aralik_ms": r.tam(0, 600000),
                "dcir_ms": r.tam(0, 2000), "kayit_hz": r.secim([1.0, 2.0, 0.5])}
    if tur == KB.KO_DCIR:
        return {"tur": tur, "kart_ms": ms, "no": r.tam(0, 100),
                **{a: r.kesir(-5, 5) for a in ("v_once", "i_once", "v_ani", "v_oturmus",
                                               "r_ani", "r_oturmus", "mah", "wh")}}
    if tur == KB.KO_PIL_SONUC:
        return {"tur": tur, "kart_ms": ms, "durum": r.tam(0, 255), "hata": r.tam(0, 255),
                "mah": r.kesir(0, 3500), "wh": r.kesir(0, 13), "ocv": r.kesir(3, 4.2),
                "v_son": r.kesir(2.5, 3.0), "sure_ms": r.tam(0, 2**32 - 1),
                "dcir_sayisi": r.tam(0, 2**32 - 1)}
    if tur == KB.KO_SKOP_KAL:
        return {"tur": tur, "kart_ms": ms, "mv": [r.tam(-32768, 32767) for _ in range(17)]}
    if tur == KB.KO_PLAN:
        return {"tur": tur, "kart_ms": ms, "bas_unix": r.tam(1_700_000_000, 1_900_000_000),
                "sure_s": r.tam(0, 30 * 86400), "hiz_ms": r.tam(0, 60000), "plan_no": r.tam(1, 99)}
    raise ValueError(tur)


def meta_r(r: Rng) -> dict:
    return {"t_ms": r.tam(0, 2**32 - 1), "sure_ms": r.tam(0, 5000), "hz": r.tam(1000, 900000),
            "tdiv_us": r.tam(1, 10**6), "adim": r.kesir(1e-4, 0.1), "ofset": r.kesir(-70, 70),
            "tetik": r.tam(0, 65535), "esik": r.tam(0, 65535), "histerezis": r.tam(0, 65535),
            "kip": r.tam(0, 255), "tetiklendi": r.tam(0, 3), "kenar": r.tam(0, 2),
            "on_yuzde": r.tam(0, 100), "onay": r.tam(0, 10)}


def skop_yuk(r: Rng, no: int, ilk: int, toplam: int, parca: int, n: int,
             meta: dict | None = None, adet: int | None = None, kuyruk: bytes = b"") -> bytes:
    d = {"no": no, "ilk": ilk, "toplam": toplam, "parca": parca,
         "kodlar": [r.tam(0, 65535) for _ in range(n)],
         "meta": meta if meta is not None else (meta_r(r) if parca == 0 else None)}
    y = bytearray(KB.skop_paketle(d))
    if adet is not None:
        struct.pack_into("<H", y, 6, adet)
    return bytes(y) + kuyruk


def ayrinti_yuk(r: Rng, ilk: int, ms: int, us: int, bayrak: int, n: int,
                adet: int | None = None, kuyruk: bytes = b"") -> bytes:
    orn = [(r.secim([-32768, 32767, 0, r.tam(-32768, 32767)]), r.tam(-32768, 32767),
            r.secim([0, 1, 4095, r.tam(0, 4095)]), r.tam(0, 15)) for _ in range(n)]
    y = bytearray(KB.ayrinti_paketle({"ilk": ilk, "t0_ms": ms, "t0_us": us, "bayrak": bayrak,
                                      "ornekler": orn}))
    if adet is not None:
        struct.pack_into("<H", y, 12, adet)
    return bytes(y) + kuyruk


def not_yuk(hedef: int, alan: int, ms: int, dg: int, metin) -> bytes:
    if isinstance(metin, str):
        metin = metin.encode("utf-8")
    return KB.not_paketle(hedef, alan, ms, dg, metin)


class Akis:
    def __init__(self):
        self.b = bytearray()
        self.sira = 0

    def k(self, tur: int, oturum: int, yuk: bytes, sira: int | None = None) -> int:
        if sira is None:
            self.sira += 1
            sira = self.sira
        else:
            self.sira = max(self.sira, sira)
        self.b += KB.kayit_paketle(tur, sira, oturum, bytes(yuk))
        return sira

    def ham(self, b: bytes) -> None:
        self.b += bytes(b)


# UTF-8 tuzaklari: Python errors="replace" ile WHATWG TextDecoder ayni mi
UTF8_OZEL = [
    b"", b"duz ascii", "Şönt ölçümü ğüşİı — 5 mΩ ±%5 µs".encode(), b"\xef\xbb\xbfBOM basta",
    b"orta\xef\xbb\xbfBOM", b"\x00NUL\x00ici\x00", b"\xff\xfe", b"\x80", b"\xbf\x80\xbf",
    b"\xc0\xaf", b"\xc1\xbf", b"\xe0\x80\xaf", b"\xed\xa0\x80", b"\xed\xbf\xbf", b"\xf0\x80\x80\x80",
    b"\xf4\x90\x80\x80", b"\xf5\x80\x80\x80", b"\xe2\x82", b"\xe2\x82A", b"\xe2A\x82",
    b"\xf0\x9f\x98", b"\xf0\x9f\x98\x80", b"\xf0\x9f\x98\x80\xf0\x9f", b"a\xc3", b"\xc3\x28",
    b"\xe2\x28\xa1", b"\xf0\x28\x8c\xbc", b"\xf8\x88\x80\x80\x80", b"\xfc\x84\x80\x80\x80\x80",
    "\u2028\u2029\ufeff\u0085".encode(),
]


# ── akislar ───────────────────────────────────────────────────────────
def akis_olcum_v2() -> tuple[str, bytes]:
    r = Rng(0x2A01)
    a = Akis()
    a.k(KB.T_BASLA, 1, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100, kal_no=3)))
    a.k(KB.T_SAAT, 0, struct.pack("<III", 1_790_000_123, 5000, 1))
    a.k(KB.T_SAAT, 1, struct.pack("<III", 1_790_000_124, 6000, 1))
    a.k(KB.T_NOKTA, 1, nokta_yuk(0, [nokta_r(r, 100 * i) for i in range(3)]))
    a.k(KB.T_NOKTA, 1, nokta_yuk(3, [nokta_r(r, 300 + 100 * i) for i in range(2)]))
    # Y5: ayni siradaki noktalar ikinci kez (farkli icerik) — ilki kalir; kuyrukta yarim nokta
    a.k(KB.T_NOKTA, 1, nokta_yuk(4, [nokta_r(r, 1), nokta_r(r, 2)], kuyruk=r.bayt(10)))
    a.k(KB.T_OLAY, 1, KB.olay_paketle(olay_r(r, KB.KO_PLAN, 7000)))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_AD, 0, 0, "Pil 18650 #3 — Şönt ölçümü"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_ETIKET, 0, 0,
                             " a , b,, \u0085c\u0085 ,\ufeffd\ufeff, \u3000e\u3000, \x1ff\x1f ,"
                             "\u180eg\u180e,\u200bh,  "))
    n1 = a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 1234, 0, "ilk not"))
    n2 = a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 2000, 0, "ikinci not"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 3000, 0, "ucuncu not"))
    d1 = a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 0, n1, "ilk not (duzeltildi, yer korunur)"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 0, n2, b""))                 # sil
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 999, d1, "duzeltmenin duzeltmesi: yok sayilir"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 5, 999_999, "bilinmeyen asil: yok sayilir"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 77, 0, b""))                  # bos not: yok
    a.k(KB.T_NOT, 0, not_yuk(1, 9, 77, 0, "bilinmeyen alan"))
    a.k(KB.T_NOT, 0, not_yuk(0, KB.KNT_AD, 0, 0, "hedef 0: atlanir"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 4500, 0, "dorduncu not"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_NOT, 4600, n1, "ilk not yeniden, yeni yer"))
    a.k(KB.T_DEVAM, 1, struct.pack("<IIII", 2, 1_790_000_500, 900, 6))
    a.k(KB.T_NOKTA, 1, nokta_yuk(6, [nokta_r(r, 1000 + i) for i in range(4)]))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_AD, 0, 0, "ad iki kez: sonuncusu"))
    a.k(KB.T_NOT, 0, not_yuk(1, KB.KNT_ETIKET, 0, 0, b""))               # etiketler bosalir
    a.k(KB.T_BITIR, 1, struct.pack("<IB3x", 10, 1))
    return "olcum_v2", bytes(a.b)


def akis_olcum_v1() -> tuple[str, bytes]:
    r = Rng(0x2A02)
    a = Akis()
    b = basla_r(r, KB.OTURUM_OLCUM, 250)
    y = bytearray(basla_v1(b))
    y[20:36] = b"A3\xff\x00x\x80" + b"\x00" * 10      # ascii disi + ic NUL + sondaki NUL'lar
    a.k(KB.T_BASLA, 2, bytes(y))
    a.k(KB.T_TEKRAR, 2, basla_v1(basla_r(r, KB.OTURUM_OLCUM, 999)))
    a.k(KB.T_NOKTA, 2, nokta_yuk(0, [nokta_r(r, i) for i in range(5)]))
    a.k(KB.T_BITIR, 2, struct.pack("<IB3x", 5, 7))
    # BASLA 100 B (98..101: kal_no YOK -> 0) ve 110 B (fazlasi yok sayilir)
    a.k(KB.T_BASLA, 3, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 10, kal_no=8))[:100])
    a.k(KB.T_BASLA, 4, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 20, kal_no=0xFFFFFFFF))
        + r.bayt(8))
    return "olcum_v1", bytes(a.b)


def akis_basi_eksik() -> tuple[str, bytes]:
    r = Rng(0x2A03)
    a = Akis()
    for hiz in (111, 222, 333):                      # BASLA temizlendi: ilk TEKRAR bilgi verir
        a.k(KB.T_TEKRAR, 5, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, hiz, kal_no=hiz)))
        a.k(KB.T_NOKTA, 5, nokta_yuk(hiz, [nokta_r(r, hiz)]))
    a.k(KB.T_TEKRAR, 6, KB.basla_paketle(basla_r(r, KB.OTURUM_PIL, 1)))
    a.k(KB.T_BASLA, 6, KB.basla_paketle(basla_r(r, KB.OTURUM_PIL, 2)))  # BASLA ustune yazar
    a.k(KB.T_TEKRAR, 6, basla_v1(basla_r(r, KB.OTURUM_PIL, 3)))
    a.k(KB.T_BASLA, 6, basla_v1(basla_r(r, KB.OTURUM_PIL, 4)))           # ikinci BASLA da yazar
    a.k(KB.T_BITIR, 6, struct.pack("<IB3x", 0, 6))
    a.k(KB.T_BITIR, 6, struct.pack("<IBBBB", 1, 5, 1, 2, 3))             # son BITIR; dolgu dolu
    return "basi_eksik", bytes(a.b)


def akis_pil() -> tuple[str, bytes]:
    r = Rng(0x2A04)
    a = Akis()
    a.k(KB.T_BASLA, 7, KB.basla_paketle(basla_r(r, KB.OTURUM_PIL, 1000, kal_no=12)))
    a.k(KB.T_OLAY, 7, KB.olay_paketle(olay_r(r, KB.KO_PIL_AYAR, 10)))
    for i in range(3):
        p = nokta_r(r, 1000 * i)
        p = dataclasses.replace(p, bayrak=p.bayrak | KB.KN_DCIR)
        a.k(KB.T_NOKTA, 7, nokta_yuk(i, [p]))
        a.k(KB.T_OLAY, 7, KB.olay_paketle(olay_r(r, KB.KO_DCIR, 1000 * i + 5)))
    a.k(KB.T_OLAY, 7, KB.olay_paketle(olay_r(r, KB.KO_SKOP_KAL, 20)))
    a.k(KB.T_OLAY, 7, struct.pack("<B3xI", 99, 21) + r.bayt(13))          # bilinmeyen olay: ham
    a.k(KB.T_OLAY, 7, struct.pack("<B3xI", KB.KO_DCIR, 22) + r.bayt(10))  # kisa DCIR: ham
    a.k(KB.T_OLAY, 7, struct.pack("<B3xI", KB.KO_PLAN, 23))               # yuksuz: ham b""
    a.k(KB.T_OLAY, 7, KB.olay_paketle(olay_r(r, KB.KO_PIL_SONUC, 24)) + r.bayt(4))  # fazlasi atilir
    a.k(KB.T_OLAY, 7, r.bayt(5))                                          # < 8 B: hic islenmez
    a.k(KB.T_OLAY, 7, KB.olay_paketle(olay_r(r, KB.KO_PIL_SONUC, 25)))
    a.k(KB.T_BITIR, 7, struct.pack("<IB3x", 3, 4))
    return "pil", bytes(a.b)


def akis_ayrinti() -> tuple[str, bytes]:
    r = Rng(0x2A05)
    a = Akis()
    a.k(KB.T_BASLA, 8, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 0, kal_no=1)))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 0, 1000, 1_000_123, KB.KA_SILME, 20))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 20, 1001, 1_001_000, KB.KA_KAYIP_ONCE, 10))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 25, 1001, 1_001_500, 0, 10))       # Y5: 25..29 tekrar
    a.k(KB.T_DEVAM, 8, struct.pack("<IIII", 3, 0, 50, 40))
    # 32 bit micros sarmasi: t0_ms*1000 > 2^32
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 40, 4_400_000, 4_400_000_000 - 2**32 + 17,
                                     KB.KA_SILME | KB.KA_KAYIP_ONCE, 8))
    # esit uzaklik: (t0_ms*1000 - t0_us) / 2^32 = 0.5, 1.5, 2.5, -0.5 -> Python round CIFTE
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 48, 2_147_484, 352, 0, 3))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 51, 6_442_451, 56, 0, 3))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 54, 10_737_419, 760, 0, 3))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 57, 0, 2**31, 0, 3))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 60, 4_294_967_295, 4_294_967_295, 0xFF, 3))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 63, 77, 77_000, 0, 5, adet=50, kuyruk=r.bayt(3)))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 68, 78, 78_000, 0, 0))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 68, 79, 79_000, 0, 2, adet=0))     # adet 0: ornek yok
    a.k(KB.T_AYRINTI, 8, r.bayt(15))                                       # < 16 B: islenmez
    a.k(KB.T_DEVAM, 8, struct.pack("<IIII", 4, 1_790_000_000, 10, 68))
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 68, 80, 80_000, 0, 6))             # yalniz 70..73 yeni
    a.k(KB.T_DEVAM, 8, struct.pack("<IIII", 5, 1_790_000_100, 10, 68))      # ayni nokta_sira
    a.k(KB.T_AYRINTI, 8, ayrinti_yuk(r, 200, 900, 900_000, 0, 4))
    a.k(KB.T_BITIR, 8, struct.pack("<IB3x", 204, 2))
    # ikinci ayrintili oturum: DEVAM yok, sira tersten
    a.k(KB.T_BASLA, 9, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 0)))
    a.k(KB.T_AYRINTI, 9, ayrinti_yuk(r, 10, 5, 5000, 0, 3), sira=a.sira + 5)
    a.k(KB.T_AYRINTI, 9, ayrinti_yuk(r, 0, 4, 4000, 0, 10), sira=a.sira - 2)
    return "ayrinti", bytes(a.b)


def akis_skop() -> tuple[str, bytes]:
    r = Rng(0x2A06)
    a = Akis()
    o = 4
    a.k(KB.T_BASLA, o, KB.basla_paketle(basla_r(r, KB.OTURUM_SKOP, 5000)))
    # A: tam yakalama, arada TEKRAR (kapatmaz)
    a.k(KB.T_SKOP, o, skop_yuk(r, 1, 0, 30, 0, 10))
    a.k(KB.T_TEKRAR, o, KB.basla_paketle(basla_r(r, KB.OTURUM_SKOP, 5000)))
    a.k(KB.T_SKOP, o, skop_yuk(r, 1, 10, 30, 1, 10))
    a.k(KB.T_SKOP, o, skop_yuk(r, 1, 20, 30, 2, 10))
    # B: SAAT araya girer -> yakalama kapanir, sonraki parca yetim
    a.k(KB.T_SKOP, o, skop_yuk(r, 2, 0, 20, 0, 10))
    a.k(KB.T_SAAT, o, struct.pack("<III", 1_790_000_000, 1, 1))
    a.k(KB.T_SKOP, o, skop_yuk(r, 2, 10, 20, 1, 10))
    # C: ayni no yeniden (Gtd + Gt): ayri, tam
    a.k(KB.T_SKOP, o, skop_yuk(r, 2, 0, 20, 0, 12))
    a.k(KB.T_SKOP, o, skop_yuk(r, 2, 12, 20, 1, 8))
    # D: bosluk (ilk kesintili) -> yeni yetim
    a.k(KB.T_SKOP, o, skop_yuk(r, 3, 0, 20, 0, 10))
    a.k(KB.T_SKOP, o, skop_yuk(r, 3, 15, 20, 1, 5))
    # E: toplam farkli -> yeni yetim
    a.k(KB.T_SKOP, o, skop_yuk(r, 4, 0, 20, 0, 10))
    a.k(KB.T_SKOP, o, skop_yuk(r, 4, 10, 21, 1, 10))
    # F: 0. parca ama META'ya yetmez (yuk < 48 B) -> meta yok
    a.k(KB.T_SKOP, o, struct.pack("<IHHHBx", 5, 0, 10, 10, 0) + r.bayt(20))
    # G: yetim ama verisi TAM (ilk 0, toplam kadar) — yalniz meta yok diye tam degil
    a.k(KB.T_SKOP, o, skop_yuk(r, 6, 0, 10, 1, 10))
    # H: adet buyuk yazilmis (kirpilir) + tek bayt kuyruk
    a.k(KB.T_SKOP, o, skop_yuk(r, 7, 0, 10, 0, 10, adet=40, kuyruk=b"\x07"))
    # I: bos parca ayni ilk'le iki kez: ilki kalir (setdefault)
    a.k(KB.T_SKOP, o, skop_yuk(r, 8, 0, 20, 0, 10))
    a.k(KB.T_SKOP, o, skop_yuk(r, 8, 10, 20, 1, 0))
    a.k(KB.T_SKOP, o, skop_yuk(r, 8, 10, 20, 2, 10))
    # J: kisa SKOP (< 12 B): hic islenmez, yakalamayi da kapatmaz
    a.k(KB.T_SKOP, o, skop_yuk(r, 9, 0, 4, 0, 2))
    a.k(KB.T_SKOP, o, r.bayt(11))
    a.k(KB.T_SKOP, o, skop_yuk(r, 9, 2, 4, 1, 2))
    # K: tetik/hz/kip uc degerleri (skop_ikili alanlari)
    m = meta_r(r)
    m.update(tetik=65535, kip=255, tetiklendi=0, hz=2**32 - 1, adim=-0.0, ofset=3.4e38)
    a.k(KB.T_SKOP, o, skop_yuk(r, 2**32 - 1, 0, 5, 0, 5, meta=m))
    m = meta_r(r)
    m.update(tetiklendi=200, adim=1e-45, ofset=-1e-40)
    a.k(KB.T_SKOP, o, skop_yuk(r, 10, 0, 0, 0, 0, meta=m))               # toplam 0: bos ama tam
    a.k(KB.T_BITIR, o, struct.pack("<IB3x", 0, 1))
    return "skop", bytes(a.b)


def akis_skop_nan() -> tuple[str, bytes]:
    """META'da SESSIZ NaN (silinmis flas 0xFFFFFFFF, yuklu): skop_ikili bunlari geri paketler,
    Python 3.14 ve V8 (x64) bitleri korur. ⚠ SINYALLI NaN (0x7F800001) BILEREK YOK: V8
    float32 -> double donusumunde onu sessizlestirir (0x7FC00001), Python korur. Firmware
    aritmetigi sNaN uretemez; fark yalniz elle bozulmus META'da gorunur."""
    r = Rng(0x2A0F)
    a = Akis()
    a.k(KB.T_BASLA, 40, KB.basla_paketle(basla_r(r, KB.OTURUM_SKOP, 0)))
    for no, (adim, ofset) in enumerate([(0x7FC00000, 0xFFFFFFFF), (0x7FC00001, 0x7FFFFFFF),
                                        (0xFFC12345, 0x7FE00000)]):
        y = bytearray(skop_yuk(r, no, 0, 3, 0, 3))
        struct.pack_into("<II", y, 12 + 16, adim, ofset)
        a.k(KB.T_SKOP, 40, bytes(y))
    return "skop_nan", bytes(a.b)


def akis_coklu() -> tuple[str, bytes]:
    r = Rng(0x2A07)
    a = Akis()
    # sira KARISIK verilir: oturumlari_kur siraya gore dizer (kararli)
    a.k(KB.T_NOKTA, 11, nokta_yuk(0, [nokta_r(r, 5)]), sira=30)
    a.k(KB.T_BASLA, 10, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100)), sira=10)
    a.k(KB.T_BASLA, 11, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 200)), sira=11)
    a.k(KB.T_SKOP, 10, skop_yuk(r, 1, 0, 8, 0, 4), sira=12)               # OLCUM'e skop
    a.k(KB.T_NOKTA, 11, nokta_yuk(1, [nokta_r(r, 6)]), sira=13)           # baska oturum: kapatmaz
    a.k(KB.T_NOT, 0, not_yuk(10, KB.KNT_NOT, 1, 0, "araya NOT: kapatmaz"), sira=14)
    a.k(KB.T_SKOP, 10, skop_yuk(r, 1, 4, 8, 1, 4), sira=15)               # tam
    a.k(KB.T_NOKTA, 10, nokta_yuk(0, [nokta_r(r, 7)]), sira=16)           # kendi oturumu: kapatir
    a.k(KB.T_SKOP, 10, skop_yuk(r, 1, 8, 12, 2, 4), sira=17)              # yetim
    a.k(KB.T_SAAT, 0, struct.pack("<III", 1, 2, 3), sira=18)              # oturum 0: atlanir
    a.k(KB.T_OLAY, 0, KB.olay_paketle(olay_r(r, KB.KO_PLAN, 1)), sira=19)
    a.k(42, 11, r.bayt(7), sira=20)                                      # bilinmeyen tur
    a.k(43, 13, r.bayt(3), sira=21)                                      # bilinmeyen: bos oturum
    a.k(KB.T_NOT, 14, r.bayt(10), sira=22)                               # kisa NOT, baslikta oturum
    a.k(KB.T_NOT, 0, not_yuk(15, KB.KNT_AD, 0, 0, "yalniz NOT'la var"), sira=23)
    a.k(KB.T_NOT, 12, not_yuk(16, KB.KNT_NOT, 9, 0, "baslik oturumu 12, hedef 16"), sira=24)
    a.k(KB.T_NOKTA, 12, nokta_yuk(0, [nokta_r(r, 8)]), sira=25)
    a.k(KB.T_NOKTA, 12, nokta_yuk(1, [nokta_r(r, 9)]), sira=25)          # ayni sira: ikisi de
    a.k(KB.T_DEVAM, 12, struct.pack("<IIII", 1, 2, 3, 4), sira=26)
    a.k(KB.T_NOKTA, 11, nokta_yuk(2, [nokta_r(r, 6)]) , sira=2)           # en kucuk sira, en sonda
    a.k(KB.T_BITIR, 11, struct.pack("<IB3x", 3, 6), sira=40)
    a.k(KB.T_BITIR, 10, struct.pack("<IB3x", 1, 1), sira=39)
    a.k(KB.T_NOKTA, 12, b"\x01\x00\x00\x00", sira=41)                    # 4 B: sifir nokta
    a.k(KB.T_SAAT, 12, struct.pack("<III", 7, 8, 9), sira=0xFFFFFFFE)
    return "coklu", bytes(a.b)


def akis_utf8() -> tuple[str, bytes]:
    r = Rng(0x2A08)
    a = Akis()
    a.k(KB.T_BASLA, 20, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100)))
    for i, m in enumerate(UTF8_OZEL):
        a.k(KB.T_NOT, 0, not_yuk(20, KB.KNT_NOT, i + 1, 0, m))
    for i in range(40):
        n = r.tam(1, 24)
        m = bytes(r.secim([r.tam(0x80, 0xFF), r.tam(0xC0, 0xF7), r.tam(0x20, 0x7E), 0x80, 0xBF])
                  for _ in range(n))
        a.k(KB.T_NOT, 0, not_yuk(20, KB.KNT_NOT, 100 + i, 0, m))
    a.k(KB.T_NOT, 0, not_yuk(21, KB.KNT_AD, 0, 0, b"\xef\xbb\xbfad BOM'lu"))
    a.k(KB.T_NOT, 0, not_yuk(21, KB.KNT_ETIKET, 0, 0, b"\xef\xbb\xbfx,\xc3,\xe2\x80\xa8y\xe2\x80\xa9"))
    return "utf8", bytes(a.b)


def akis_ozel_float() -> tuple[str, bytes]:
    r = Rng(0x2A09)
    a = Akis()
    b = bytearray(KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100)))
    b[36:98] = b"\xff" * 62                       # silinmis flas kalibrasyonu: NaN + -1
    a.k(KB.T_BASLA, 30, bytes(b))
    nan_b = struct.pack("<I", 0x7FC00000)
    p = bytearray(KB.nokta_paketle(nokta_r(r, 1)))
    p[8:12] = nan_b                               # v_ort NaN
    p[16:20] = struct.pack("<f", float("inf"))
    p[24:28] = struct.pack("<f", -0.0)
    p[28:32] = struct.pack("<I", 1)               # en kucuk alt-normal
    p[32:36] = struct.pack("<f", float("-inf"))
    a.k(KB.T_NOKTA, 30, struct.pack("<I", 0) + bytes(p))
    a.k(KB.T_BASLA, 31, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100)))
    q = dataclasses.replace(nokta_r(r, 2), v_ort_kod=32767.0, v_min_kod=-32768, v_maks_kod=32767,
                            i_ort_kod=-32768.0, i_min_kod=-32768, i_maks_kod=32767)
    a.k(KB.T_NOKTA, 31, nokta_yuk(0, [q]))
    return "ozel_float", bytes(a.b)


def akis_rastgele(tohum: int, adet: int) -> tuple[str, bytes]:
    """Karisik gecerli kayitlar: her tur, birkac oturum (Python'un cokmedigi uzunluklar)."""
    r = Rng(tohum)
    a = Akis()
    oturumlar = [100 + i for i in range(5)]
    for o in oturumlar:
        a.k(KB.T_BASLA, o, KB.basla_paketle(basla_r(r, r.tam(1, 3), r.tam(0, 5000), r.tam(0, 40))))
    nokta = {o: 0 for o in oturumlar}
    for _ in range(adet):
        o = r.secim(oturumlar)
        t = r.secim([KB.T_NOKTA] * 4 + [KB.T_OLAY, KB.T_NOT, KB.T_AYRINTI, KB.T_SKOP, KB.T_SAAT,
                                          KB.T_DEVAM, KB.T_TEKRAR, KB.T_BITIR, 77])
        if t == KB.T_NOKTA:
            n = r.tam(1, 6)
            a.k(t, o, nokta_yuk(nokta[o], [nokta_r(r, r.tam(0, 2**32 - 1)) for _ in range(n)]))
            nokta[o] += n
        elif t == KB.T_OLAY:
            a.k(t, o, KB.olay_paketle(olay_r(r, r.tam(1, 5), r.tam(0, 2**32 - 1))))
        elif t == KB.T_NOT:
            a.k(t, 0, not_yuk(o, r.tam(1, 3), r.tam(0, 9999), 0,
                              r.secim(["x", "a,b", " c ", "Ölçüm ", ""])))
        elif t == KB.T_AYRINTI:
            a.k(t, o, ayrinti_yuk(r, r.tam(0, 10**6), r.tam(0, 2**32 - 1), r.tam(0, 2**32 - 1),
                                  r.tam(0, 3), r.tam(0, 12)))
        elif t == KB.T_SKOP:
            parca = r.tam(0, 2)
            a.k(t, o, skop_yuk(r, r.tam(0, 3), r.secim([0, 8, 16]), 24, parca, 8))
        elif t == KB.T_SAAT:
            a.k(t, o, struct.pack("<III", r.tam(0, 2**32 - 1), r.tam(0, 2**32 - 1), r.tam(0, 99)))
        elif t == KB.T_DEVAM:
            a.k(t, o, struct.pack("<IIII", r.tam(0, 99), r.tam(0, 2**32 - 1), r.tam(0, 2**32 - 1),
                                  nokta[o]))
        elif t == KB.T_TEKRAR:
            a.k(t, o, KB.basla_paketle(basla_r(r, 1, r.tam(0, 5000))))
        elif t == KB.T_BITIR:
            a.k(t, o, struct.pack("<IB3x", nokta[o], r.tam(1, 7)))
        else:
            a.k(t, o, r.bayt(r.tam(0, 40)))
    return f"rastgele_{tohum:x}", bytes(a.b)


def akis_bozuklar() -> list[tuple[str, bytes]]:
    r = Rng(0x2A0A)
    a = Akis()
    a.k(KB.T_BASLA, 1, KB.basla_paketle(basla_r(r, 1, 100)))
    for i in range(4):
        a.k(KB.T_NOKTA, 1, nokta_yuk(i, [nokta_r(r, i)]))
    on = bytes(a.b)

    def kayit(tur=KB.T_DEVAM, sira=50, oturum=1, yuk=None):
        return KB.kayit_paketle(tur, sira, oturum, yuk if yuk is not None else r.bayt(16))

    def sonra():
        s = Akis()
        s.sira = 60
        s.k(KB.T_DEVAM, 1, struct.pack("<IIII", 1, 2, 3, 4))
        s.k(KB.T_BITIR, 1, struct.pack("<IB3x", 4, 1))
        return bytes(s.b)

    def boz(b: bytes, i: int, x: int) -> bytes:
        y = bytearray(b)
        y[i] ^= x
        return bytes(y)

    iyi = kayit(yuk=struct.pack("<IIII", 1, 2, 3, 4))
    out = [
        ("bos", b""),
        ("bozuk_crc_orta", on + boz(iyi, 20, 0x01) + sonra()),
        ("bozuk_crc_alani", on + boz(iyi, 12, 0x80) + sonra()),
        ("bozuk_baslik_yuk_bayt", on + boz(iyi, 2, 0x04) + sonra()),
        ("imza_yanlis", on + boz(iyi, 0, 0xFF) + sonra()),
        ("tur_0", on + kayit(tur=0) + sonra()),
        ("tur_ff", on + kayit(tur=0xFF) + sonra()),
        ("sira_0", on + kayit(sira=0) + sonra()),
        ("sira_ffffffff", on + kayit(sira=0xFFFFFFFF) + sonra()),
        ("kesik_kuyruk", on + iyi[:-5]),
        ("kesik_baslik", on + iyi[:10]),
        ("ff_dolgu", on + b"\xff" * 64),
        ("ff_dolgu_sonra_kayit", on + b"\xff" * 16 + sonra()),
        ("sifir_dolgu", on + b"\x00" * 32),
        # 3 B yuk -> 20 B kayit; 19. bayt DOLGU: CRC'ye girmez, kayit gecerli kalir
        ("dolgu_baytlari_dolu", on + boz(kayit(tur=77, yuk=b"\x01\x02\x03"), 19, 0x55) + sonra()),
        ("bilinmeyen_turler", on + kayit(tur=11) + kayit(tur=200, sira=51)
         + kayit(tur=254, sira=52, oturum=0) + sonra()),
        # Python oturumlari_kur bunlarda struct.error verir (gecerli CRC, yanlis uzunluk)
        ("kisa_basla", on + kayit(tur=KB.T_BASLA, yuk=r.bayt(50))),
        ("kisa_tekrar", on + kayit(tur=KB.T_TEKRAR, yuk=r.bayt(97))),      # BASLA var: cozulmez
        ("kisa_tekrar_yeni_oturum", on + kayit(tur=KB.T_TEKRAR, oturum=2, yuk=r.bayt(97))),
        ("uzun_devam", on + kayit(tur=KB.T_DEVAM, yuk=r.bayt(17))),
        ("kisa_bitir", on + kayit(tur=KB.T_BITIR, yuk=r.bayt(7))),
        ("uzun_saat", on + kayit(tur=KB.T_SAAT, yuk=r.bayt(13))),
        ("kisa_nokta", on + kayit(tur=KB.T_NOKTA, yuk=r.bayt(3))),
        ("nokta_yarim", on + kayit(tur=KB.T_NOKTA, yuk=struct.pack("<I", 9) + r.bayt(40))),
    ]
    return out


# ── flas goruntuleri ─────────────────────────────────────────────────
def flas_vektorleri() -> list[dict]:
    r = Rng(0x2A0B)
    S = 256

    def kayit(tur, sira, oturum, yuk):
        return KB.kayit_paketle(tur, sira, oturum, yuk)

    def devam(sira, o=1):
        return kayit(KB.T_DEVAM, sira, o, struct.pack("<IIII", sira, 0, sira, 0))

    def sektor(b: bytes) -> bytes:
        assert len(b) <= S
        return bytes(b) + b"\xff" * (S - len(b))

    basla = kayit(KB.T_BASLA, 1, 1, KB.basla_paketle(basla_r(r, 1, 100)))
    s0 = sektor(basla + b"".join(kayit(KB.T_NOKTA, s, 1, nokta_yuk(s, [nokta_r(r, s)]))
                                 for s in (2,)) + devam(5))
    s1 = sektor(devam(20) + devam(21) + devam(22) + b"\xa5\x03\x10\x00" + r.bayt(12))   # cop
    s2 = sektor(b"")
    s3 = sektor(devam(10) + devam(11) + devam(12) + devam(11))         # sira geri: sektor biter
    s4 = b"".join(devam(30 + i) for i in range(8))                     # tam dolu (8 x 32)
    s5 = sektor(b"".join(devam(40 + i) for i in range(7))
                + kayit(KB.T_SKOP, 47, 1, skop_yuk(r, 1, 0, 9, 1, 9))[:32])   # sektor sinirini asar
    s6 = sektor(b"\x5a" + devam(50)[1:])                                # imza yanlis
    s7 = sektor(devam(3) + devam(4) + devam(5) + devam(6))             # 5: s0'daki ile ayni sira
    s8 = sektor(kayit(KB.T_NOT, 60, 0, not_yuk(1, KB.KNT_AD, 0, 0, "flas"))
                + kayit(KB.T_BITIR, 61, 1, struct.pack("<IB3x", 2, 2)))
    s9 = sektor(devam(14) + devam(14) + devam(15))                     # ESIT sira: sektor biter
    tam = s0 + s1 + s2 + s3 + s4 + s5 + s6 + s7 + s8 + s9
    assert len(tam) == 10 * S
    v = [("flas_10_sektor", tam, S),
         ("flas_kucuk_sektor", tam[:2 * S], 8),                        # sektor < baslik: hic kayit
         ("flas_son_sektor_kisa", s0 + s4 + devam(70) + devam(71) + b"\xff" * 20, S),
         ("flas_son_sektor_yarim_kayit", s0 + kayit(KB.T_SKOP, 80, 1, skop_yuk(r, 1, 0, 9, 1, 9))[:26], S),
         # Python struct.error: sektor ortasinda biten goruntude kalan < 16 B
         ("flas_son_sektor_baslik_kisa", s0 + devam(90) + b"\xff" * 8, S),
         ("flas_bos", b"", S),
         ("flas_hepsi_ff", b"\xff" * (3 * S), S),
         ("flas_buyuk_sektor", tam, 4 * S)]
    out = []
    for ad, veri, sek in v:
        d = {"ad": ad, "veri": j(veri), "sektor": sek, "flas_coz": dene(KB.flas_coz, veri, sek)}
        if "hata" not in d["flas_coz"]:
            d["oturumlari_kur"] = dene(lambda x: jot(KB.oturumlari_kur(x)),
                                       KB.flas_coz(veri, sek)[0])
        out.append(d)
    return out


def jot(ot: dict) -> dict:
    return {"$map": [[i, j(o)] for i, o in ot.items()]}


def akis_vektoru(ad: str, veri: bytes) -> dict:
    d = {"ad": ad, "veri": j(veri), "akis_onek": j(KB.akis_onek(veri))}
    try:
        d["akis_coz"] = j(KB.akis_coz(veri))
    except ValueError as e:
        d["akis_coz"] = {"hata": type(e).__name__, "mesaj": str(e)}
    kayitlar = KB.akis_onek(veri)[0]
    try:
        ot = KB.oturumlari_kur(kayitlar)
    except Exception as e:  # noqa: BLE001
        d["oturumlari_kur"] = hata(e)
        return d
    d["oturumlari_kur"] = jot(ot)
    d["ayrinti_ornekler"] = [[i, j(KB.ayrinti_ornekler(o))] for i, o in ot.items() if o.ayrinti]
    d["skop_ikili"] = [[i, s, j(KB.skop_ikili(y))] for i, o in ot.items()
                       for s, y in o.skoplar.items()]
    return d


# ── dogrudan cozucu ve paketleyici vakalari ─────────────────────────
def vakalar() -> list[dict]:
    r = Rng(0x2A0C)
    out = []

    def vaka(fn: str, *arg):
        f = getattr(KB, fn)
        d = {"fn": fn, "arg": j(list(arg))}
        try:
            d["cikti"] = j(f(*arg))
        except Exception as e:  # noqa: BLE001
            d.update(hata(e))
        out.append(d)

    p = KB.nokta_paketle(nokta_r(r, 1))
    for b in (p, KB.nokta_paketle(nokta_r(r, 2**32 - 1)), p[:35], p + b"\x00", b""):
        vaka("nokta_coz", b)
    bas = KB.basla_paketle(basla_r(r, 1, 100, kal_no=77))
    kal = KB.kal_paketle(kal_r(r))
    for y, a in ((bas, 36), (kal, 0), (kal, -62), (kal + b"\x01", -63), (kal[:61], 0), (kal, 1),
                 (kal, -63), (kal + kal, 62)):
        vaka("kal_coz", y, a)
    for y in (bas, basla_v1(basla_r(r, 2, 5)), bas[:100], bas + r.bayt(8), bas[:97], bas[:36],
              bas[:35], b""):
        vaka("basla_coz", y)
    for n in (16, 15, 17, 0):
        vaka("devam_coz", r.bayt(n))
    for n in (8, 7, 9):
        vaka("bitir_coz", r.bayt(n))
    vaka("bitir_coz", struct.pack("<IBBBB", 123, 4, 9, 9, 9))
    for n in (12, 11, 13):
        vaka("saat_coz", r.bayt(n))
    for t in (KB.KO_PIL_AYAR, KB.KO_DCIR, KB.KO_PIL_SONUC, KB.KO_SKOP_KAL, KB.KO_PLAN):
        y = KB.olay_paketle(olay_r(r, t, r.tam(0, 2**32 - 1)))
        vaka("olay_coz", y)
        vaka("olay_coz", y[:-1])                         # kisa: ham
        vaka("olay_coz", y + r.bayt(3))                  # uzun: fazlasi atilir
    for y in (struct.pack("<B3xI", 0, 1), struct.pack("<B3xI", 255, 2) + r.bayt(30),
              r.bayt(7), b""):
        vaka("olay_coz", y)
    for m in (b"", b"merhaba", "Şönt".encode(), b"\xef\xbb\xbfBOM", b"\xe2\x82", b"a\x00b"):
        vaka("not_coz", not_yuk(r.tam(0, 2**32 - 1), r.tam(0, 255), r.tam(0, 2**32 - 1),
                                r.tam(0, 2**32 - 1), m))
    vaka("not_coz", r.bayt(15))
    vaka("not_coz", struct.pack("<IB3xII", 1, 2, 3, 4)[:16])
    for y in (ayrinti_yuk(r, 5, 6, 7, 3, 4), ayrinti_yuk(r, 5, 6, 7, 0, 4, adet=9),
              ayrinti_yuk(r, 5, 6, 7, 0, 2, kuyruk=b"\x01\x02\x03\x04\x05"),
              ayrinti_yuk(r, 0, 0, 0, 0, 0, adet=3), r.bayt(15), b""):
        vaka("ayrinti_coz", y)
    for y in (skop_yuk(r, 1, 0, 10, 0, 10), skop_yuk(r, 2, 10, 30, 1, 10),
              skop_yuk(r, 3, 0, 10, 0, 4, adet=11), skop_yuk(r, 4, 6, 10, 3, 4, kuyruk=b"\x09"),
              struct.pack("<IHHHBx", 5, 0, 3, 3, 0) + r.bayt(35),       # 0. parca, META'ya 1 B eksik
              struct.pack("<IHHHBx", 5, 0, 3, 3, 0), r.bayt(11), b""):
        vaka("skop_coz", y)

    # paketleyiciler (JS paketleyicisi Python'la bayt bayt ayni mi)
    vaka("kayit_paketle", 1, 1, 1, b"")
    vaka("kayit_paketle", 0x42, 7, 9, r.bayt(5))
    vaka("kayit_paketle", KB.T_NOKTA, 0xFFFFFFFF, 0xFFFFFFFF, r.bayt(37))
    vaka("kayit_paketle", 256, 1, 1, b"")                # struct.error
    vaka("kayit_paketle", 1, -1, 1, b"")
    for _ in range(3):
        vaka("nokta_paketle", nokta_r(r, r.tam(0, 2**32 - 1)))
    vaka("nokta_paketle", dataclasses.replace(nokta_r(r, 1), w_ort=1e39))     # OverflowError
    vaka("nokta_paketle", dataclasses.replace(nokta_r(r, 1), w_min=3.4028235677973366e38))
    vaka("nokta_paketle", dataclasses.replace(nokta_r(r, 1), v_ort_kod=float("nan"),
                                              w_maks=float("-inf"), w_min=1e-50))
    vaka("nokta_paketle", dataclasses.replace(nokta_r(r, 1), v_min_kod=40000))  # struct.error
    vaka("nokta_paketle", dataclasses.replace(nokta_r(r, 1), n=-1))
    vaka("kal_paketle", kal_r(r))
    vaka("basla_paketle", basla_r(r, 2, 3, kal_no=9))
    vaka("basla_paketle", basla_r(r, 2, 3, surum="cok-uzun-surum-adi-16-ustu"))
    vaka("basla_paketle", basla_r(r, 2, 3, surum=""))
    vaka("basla_paketle", basla_r(r, 2, 3, surum="Ölçüm"))   # UnicodeEncodeError
    for t in (KB.KO_PIL_AYAR, KB.KO_DCIR, KB.KO_PIL_SONUC, KB.KO_SKOP_KAL, KB.KO_PLAN):
        vaka("olay_paketle", olay_r(r, t, r.tam(0, 2**32 - 1)))
    vaka("olay_paketle", {"tur": 99, "kart_ms": 1})          # KeyError
    vaka("not_paketle", 1, KB.KNT_NOT, 2, 3, "Ölçüm".encode())
    vaka("not_paketle", 0xFFFFFFFF, 255, 0, 0, b"")
    vaka("ayrinti_paketle", {"ilk": 1, "t0_ms": 2, "t0_us": 3, "bayrak": 3,
                             "ornekler": [(-32768, 32767, 4095, 15), (0, -1, 0, 0x1F), (5, 6, 7, -1)]})
    vaka("ayrinti_paketle", {"ilk": 1, "t0_ms": 2, "t0_us": 3, "bayrak": 0, "ornekler": []})
    vaka("ayrinti_paketle", {"ilk": 1, "t0_ms": 2, "t0_us": 3, "bayrak": 0,
                             "ornekler": [(0, 0, 4096, 0)]})           # struct.error
    vaka("skop_paketle", {"no": 1, "ilk": 0, "toplam": 4, "parca": 0, "meta": meta_r(r),
                          "kodlar": [0, 1, 65535, 7]})
    vaka("skop_paketle", {"no": 2, "ilk": 4, "toplam": 8, "parca": 1, "meta": None,
                          "kodlar": [9, 8, 7, 6]})
    vaka("skop_paketle", {"no": 3, "ilk": 0, "toplam": 0, "parca": 2, "meta": None, "kodlar": []})
    return out


# ── birimler ─────────────────────────────────────────────────────────
def birimler() -> dict:
    r = Rng(0x2A0D)
    out = []

    def birim(fn: str, kod, kal_i: int, kanal: str | None):
        kal = kallar[kal_i]
        k = getattr(kal, kanal) if kanal else kal
        d = {"fn": fn, "kod": j(kod), "tamsayi": isinstance(kod, int), "kal": kal_i, "kanal": kanal}
        try:
            d["cikti"] = j(getattr(KB, fn)(kod, k))
        except Exception as e:  # noqa: BLE001
            d.update(hata(e))
        out.append(d)

    def f32(x: float) -> float:
        return struct.unpack("<f", struct.pack("<f", x))[0]

    kallar = [KB.kal_coz(KB.kal_paketle(kal_r(r))) for _ in range(4)]
    kallar.append(KB.kal_coz(b"\xff" * KB.KAL_BAYT))                  # silinmis flas: NaN
    kallar.append(KB.Kalibrasyon(KB.Kanal(1.0, 32768.0, 1.0, -10, 0.0),
                                 KB.Kanal(1.0, 32768.0, 1.0, 10, 0.0),
                                 -10, 32768.0, 1.0, 1.0, 50.0, (0.0, 0.0)))
    kallar.append(dataclasses.replace(kallar[0], sont_ohm=0.0))
    kallar.append(dataclasses.replace(kallar[1], sont_ohm=-0.0, i_duzeltme=-1.5))
    kallar.append(dataclasses.replace(kallar[2], sont_ohm=f32(1e-40)))
    for i, kal in enumerate(kallar):
        kodlar = [0, 1, -1, 32767, -32768, 40000, -40000, kal.normal.sifir_ham, kal.i_ofset,
                  r.tam(-32768, 32767), r.tam(-32768, 32767),
                  r.kesir(-32768, 32767), f32(r.kesir(-32768, 32767)), 32767.0, -32768.0, 0.0,
                  -0.0, 12345.5, 40000.0, float("nan"), float("inf"), 1e308]
        for kod in kodlar:
            birim("volt", kod, i, "normal")
            birim("volt", kod, i, "yuksek")
            birim("amper", kod, i, None)
    return {"kallar": j(kallar), "vakalar": out}


def api() -> list[str]:
    return sorted(n for n, f in vars(KB).items()
                  if inspect.isfunction(f) and not n.startswith("_") and f.__module__ == KB.__name__)


def sabitler() -> dict:
    d = {}
    for n, v in vars(KB).items():
        if n.isupper() and not n.startswith("_") and isinstance(v, (int, float, str, dict)):
            d[n] = jmap(v) if isinstance(v, dict) else j(v)
    return d


def vektorler() -> dict:
    r = Rng(0x2A0E)
    akis = [akis_olcum_v2(), akis_olcum_v1(), akis_basi_eksik(), akis_pil(), akis_ayrinti(),
            akis_skop(), akis_skop_nan(), akis_coklu(), akis_utf8(), akis_ozel_float(),
            akis_rastgele(0x2A10, 70), akis_rastgele(0x2A11, 70)] + akis_bozuklar()
    crc_v = [{"veri": j(b"123456789"), "onceki": 0, "cikti": KB.crc(b"123456789")},
             {"veri": j(b""), "onceki": 0x12345678, "cikti": KB.crc(b"", 0x12345678)}]
    for _ in range(12):
        b = r.bayt(r.tam(0, 70))
        o = r.secim([0, r.tam(0, 2**32 - 1)])
        crc_v.append({"veri": j(b), "onceki": o, "cikti": KB.crc(b, o)})
    bir = birimler()
    return {
        "birim_kallar": bir["kallar"],
        "birimler": bir["vakalar"],
        "aciklama": "uretim/ortak_vektor_kayit.py uretti (Python kopru/kayit_bicim.py); ELLE DUZENLEME",
        "api": api(),
        "sabitler": sabitler(),
        "crc": crc_v,
        "toplam_bayt": [[n, KB.toplam_bayt(n)] for n in list(range(0, 21)) + [65535]],
        "akislar": [akis_vektoru(ad, v) for ad, v in akis],
        "flaslar": flas_vektorleri(),
        "vakalar": vakalar(),
        "unix_zaman": [[s, None if KB.unix_zaman(s) is None else KB.unix_zaman(s).isoformat()]
                       for s in (0, 1, 1_790_000_000, 2**31, 2**32 - 1)],
    }


def tek(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def metin(v: dict) -> str:
    """Kararli metin: her vektor kendi satirinda (fark okunabilir)."""
    s = ["{"]
    an = sorted(v)
    for i, k in enumerate(an):
        virgul = "," if i < len(an) - 1 else ""
        d = v[k]
        if isinstance(d, list) and d and isinstance(d[0], (dict, list)):
            s.append(f"{tek(k)}: [")
            s += [tek(e) + ("," if m < len(d) - 1 else "") for m, e in enumerate(d)]
            s.append("]" + virgul)
        else:
            s.append(f"{tek(k)}: {tek(d)}{virgul}")
    s.append("}")
    return "\n".join(s) + "\n"


def farklar(eski: dict, yeni: dict) -> list[str]:
    out = []
    for k in sorted(set(eski) | set(yeni)):
        a, b = eski.get(k), yeni.get(k)
        if a == b:
            continue
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                out.append(f"{k}: {len(a)} vektor -> {len(b)}")
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    ad = (y.get("ad") or y.get("fn")) if isinstance(y, dict) else None
                    out.append(f"{k}[{i}]{' ' + ad if ad else ''} farkli")
        else:
            out.append(f"{k} farkli")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--denetle", action="store_true",
                    help="dosyayi yazma; depodakiyle karsilastir, farkliysa 1 don")
    a = ap.parse_args()
    v = vektorler()
    m = metin(v)
    sayi = sum(len(x) for x in v.values() if isinstance(x, list))
    if a.denetle:
        if not HEDEF.exists():
            print(f"YOK: {HEDEF.relative_to(KOK).as_posix()} - once 'python ortak_vektor_kayit.py'")
            return 1
        eski = HEDEF.read_bytes().decode("ascii", "replace")
        if eski == m:
            print(f"OK: {HEDEF.relative_to(KOK).as_posix()} Python basvurusuyla ayni ({sayi} vektor)")
            return 0
        try:
            fl = farklar(json.loads(eski), json.loads(m))
        except ValueError:
            fl = ["depodaki dosya JSON degil"]
        for s in fl[:30] or ["metin farkli (bicim/sira)"]:
            print("  FARK " + s)
        print(f"FARKLI: {HEDEF.relative_to(KOK).as_posix()} Python'la uyusmuyor "
              f"({len(fl)} fark) - bilerek degistiyse yeniden uret")
        return 1
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_bytes(m.encode("ascii"))
    print(f"yazildi: {HEDEF.relative_to(KOK).as_posix()} ({sayi} vektor, {len(m)} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
