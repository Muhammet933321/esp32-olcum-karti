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
Saglamlik (S5/S6): her turun bilinen boydan UZUN kaydi (on ek), en kisa boydan KISA kaydi
(atlanir + `oturumlari_kur_uyarilar`), oturum numarali bilinmeyen tur (oturum acmaz), tam
sektor olmayan flas goruntusu, sont_ohm 0 -> NaN. `kurallar()` bu kurallari Python
basvurusunda ayrica ASSERT eder (vektor yalniz "ayni" der, kural "dogru" der).

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
import re
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
    if tur == KB.KO_PIL_HAT:
        return {"tur": tur, "kart_ms": ms, "hat_mohm": r.tam(0, 1000)}
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
    a.k(43, 13, r.bayt(3), sira=21)                                      # bilinmeyen: 13 ACILMAZ (S6)
    a.k(KB.T_NOT, 14, r.bayt(10), sira=22)                               # kisa NOT: uyari, 14 ACILMAZ
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
        # gecerli CRC, yanlis uzunluk. S5 oncesi oturumlari_kur bunlarda struct.error
        # veriyordu; simdi kisa -> atla + uyari, uzun -> on ek
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


# S5: turun en kisa gecerli yuku — kayit_bicim.h'den BAGIMSIZ yazildi (KB._EN_AZ'dan
# okunmaz: tablo kayarsa vektor de kaysin, kural iddiasi kirmizi olsun)
EN_AZ_BAGIMSIZ = [(KB.T_BASLA, 98), (KB.T_TEKRAR, 98), (KB.T_NOKTA, 4), (KB.T_DEVAM, 16),
                  (KB.T_BITIR, 8), (KB.T_SAAT, 12), (KB.T_OLAY, 8), (KB.T_NOT, 16),
                  (KB.T_AYRINTI, 16), (KB.T_SKOP, 12)]


def akis_uzun_kayitlar() -> tuple[str, bytes]:
    """S5: her sabit boylu tur bilinen boydan UZUN (yeni firmware alan eklemis olabilir):
    bilinen on ek cozulur, fazlasi yok sayilir, uyari YOK."""
    r = Rng(0x2A12)
    a = Akis()
    o = 60
    a.k(KB.T_BASLA, o, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100, kal_no=5)) + r.bayt(9))
    a.k(KB.T_TEKRAR, o, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100)) + r.bayt(1))
    a.k(KB.T_SAAT, o, struct.pack("<III", 1_790_000_200, 70, 1) + r.bayt(4))
    a.k(KB.T_NOKTA, o, nokta_yuk(0, [nokta_r(r, 1), nokta_r(r, 2)], kuyruk=r.bayt(35)))
    for t in (KB.KO_PIL_AYAR, KB.KO_DCIR, KB.KO_PIL_SONUC, KB.KO_SKOP_KAL, KB.KO_PLAN):
        a.k(KB.T_OLAY, o, KB.olay_paketle(olay_r(r, t, 90 + t)) + r.bayt(t + 3))
    a.k(KB.T_NOT, 0, not_yuk(o, KB.KNT_AD, 0, 0, "uzun kayitlar"))
    a.k(KB.T_DEVAM, o, struct.pack("<IIII", 2, 1_790_000_300, 80, 2) + r.bayt(12))
    a.k(KB.T_AYRINTI, o, ayrinti_yuk(r, 0, 100, 100_000, 0, 3, kuyruk=r.bayt(11)))
    a.k(KB.T_SKOP, o, skop_yuk(r, 1, 0, 6, 0, 3, kuyruk=r.bayt(5)))
    a.k(KB.T_SKOP, o, skop_yuk(r, 1, 3, 6, 1, 3, kuyruk=r.bayt(1)))
    a.k(KB.T_BITIR, o, struct.pack("<IB3x", 2, 1) + r.bayt(6))
    # BASLA'si olmayan oturum: TEKRAR'dan bilgi; surum 1 + 3 B (101 B: kal_no YOK -> 0)
    a.k(KB.T_TEKRAR, o + 1, basla_v1(basla_r(r, KB.OTURUM_PIL, 1000, kal_no=4)) + r.bayt(3))
    a.k(KB.T_NOKTA, o + 1, nokta_yuk(0, [nokta_r(r, 3)]))
    a.k(KB.T_TEKRAR, o + 2, KB.basla_paketle(basla_r(r, KB.OTURUM_SKOP, 7, kal_no=6)) + r.bayt(40))
    return "uzun_kayitlar", bytes(a.b)


def akis_kisa_kayitlar() -> tuple[str, bytes]:
    """S5/S6: her bilinen tur en kisa boyundan 1 B (ve bazisi 0 B) KISA: kayit atlanir +
    uyari (sirayla), YALNIZ kisa kaydi olan oturum (70..79) ACILMAZ, var olan oturum (69)
    degismez; cokme yok. Baslik oturumu 0 olan kisa kayit da uyarir."""
    r = Rng(0x2A13)
    a = Akis()
    a.k(KB.T_BASLA, 69, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100)))
    for i, (tur, n) in enumerate(EN_AZ_BAGIMSIZ):
        a.k(tur, 70 + i, r.bayt(n - 1))
        a.k(tur, 69, r.bayt(n - 1))
    a.k(KB.T_DEVAM, 69, b"")
    a.k(KB.T_OLAY, 69, b"")
    a.k(KB.T_SAAT, 0, r.bayt(11))
    a.k(KB.T_NOT, 0, r.bayt(15))
    a.k(KB.T_NOKTA, 69, nokta_yuk(0, [nokta_r(r, 5)]))
    a.k(KB.T_BITIR, 69, struct.pack("<IB3x", 1, 1))
    return "kisa_kayitlar", bytes(a.b)


def akis_pil_hat() -> tuple[str, bytes]:
    """HT3 (2026-10-08): PIL oturumunda hat direnci olaylari (KO_PIL_HAT, 12 B): test basinda R, test
    icinde degisim — millis sarmasinin IKI yaninda (isaretli 32 bit fark) —, ayni deger, uzun olay
    (fazlasi atilir) ve kisa olay (ham: R'ye girmez). Ayri tohum: diger akislar degismez."""
    r = Rng(0x2A1A)
    a = Akis()
    o, s = 8, 2**32
    b = dataclasses.replace(basla_r(r, KB.OTURUM_PIL, 1000, kal_no=3), kart_ms=s - 2500)
    a.k(KB.T_BASLA, o, KB.basla_paketle(b))
    a.k(KB.T_OLAY, o, KB.olay_paketle(olay_r(r, KB.KO_PIL_AYAR, s - 2499)))
    a.k(KB.T_OLAY, o, KB.olay_paketle({"tur": KB.KO_PIL_HAT, "kart_ms": s - 2499, "hat_mohm": 50}))
    a.k(KB.T_NOKTA, o, nokta_yuk(0, [nokta_r(r, s - 1500), nokta_r(r, s - 500)]))
    a.k(KB.T_OLAY, o, KB.olay_paketle({"tur": KB.KO_PIL_HAT, "kart_ms": s - 400, "hat_mohm": 80}))
    a.k(KB.T_NOKTA, o, nokta_yuk(2, [nokta_r(r, 500), nokta_r(r, 1500)]))
    a.k(KB.T_OLAY, o, KB.olay_paketle({"tur": KB.KO_PIL_HAT, "kart_ms": 1000, "hat_mohm": 80}))        # ayni deger
    a.k(KB.T_OLAY, o, KB.olay_paketle({"tur": KB.KO_PIL_HAT, "kart_ms": 2000, "hat_mohm": 0}) + r.bayt(4))
    a.k(KB.T_OLAY, o, struct.pack("<B3xI", KB.KO_PIL_HAT, 2100) + r.bayt(3))                     # kisa: ham
    a.k(KB.T_NOKTA, o, nokta_yuk(4, [nokta_r(r, 2500)]))
    a.k(KB.T_OLAY, o, KB.olay_paketle(olay_r(r, KB.KO_PIL_SONUC, 2600)))
    a.k(KB.T_BITIR, o, struct.pack("<IB3x", 5, 4))
    return "pil_hat", bytes(a.b)


def _hat_anlari(o) -> list[int]:
    """pil_hat_mohm_at'in sinandigi anlar: her nokta, her olayin kendisi ve +-1 ms, sarma uclari."""
    t = {p.kart_ms for _, p in o.noktalar} | {0, 2**32 - 1}
    for d in o.olaylar:
        t |= {d["kart_ms"], (d["kart_ms"] - 1) % 2**32, (d["kart_ms"] + 1) % 2**32}
    return sorted(t)


def akis_bilinmeyen_oturum() -> tuple[str, bytes]:
    """S6: oturum numarali bilinmeyen tur oturum ACMAZ ve oturum SIRASINI etkilemez: 50'nin
    ilk kaydi bilinmeyen tur ama ilk VERI kaydi 51'inkinden sonra -> sira [51, 50]; yalniz
    bilinmeyen kaydi olan 52 yok."""
    r = Rng(0x2A14)
    a = Akis()
    a.k(77, 50, r.bayt(20))
    a.k(KB.T_BASLA, 51, KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100)))
    a.k(200, 52, b"")
    a.k(11, 52, r.bayt(30))
    a.k(KB.T_BASLA, 50, KB.basla_paketle(basla_r(r, KB.OTURUM_PIL, 1000)))
    a.k(254, 51, r.bayt(3))
    a.k(KB.T_BITIR, 51, struct.pack("<IB3x", 0, 1))
    return "bilinmeyen_oturum", bytes(a.b)


def akis_surum_nul() -> tuple[str, bytes]:
    """[1A-1 D] Firmware surumu C dizgisi: ILK NUL'da biter. Alanin NUL'dan sonrasi cop
    olabilir (eski strncpy/yari yazma); rstrip yalniz SONDAKI NUL'lari atip copu tutuyordu."""
    r = Rng(0x2A15)
    a = Akis()
    b = bytearray(KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100, surum="A3-1F")))
    b[20 + 6:20 + 9] = b"xyz"                     # surum alani 20..36: "A3-1F\0xyz\0..."
    assert KB.basla_coz(bytes(b)).surum == "A3-1F", KB.basla_coz(bytes(b)).surum
    a.k(KB.T_BASLA, 70, bytes(b))
    c = bytearray(KB.basla_paketle(basla_r(r, KB.OTURUM_PIL, 1000, surum="A3-1F")))
    c[20:36] = b"\0" + b"A3" + b"\0" * 13         # bos surum + cop
    assert KB.basla_coz(bytes(c)).surum == "", KB.basla_coz(bytes(c)).surum
    a.k(KB.T_BASLA, 71, bytes(c))
    return "surum_nul", bytes(a.b)


# ── W1: yakalamanin yeri (Y7) + hizali guc ────────────────────────────
def yer_ornekler(r: Rng, n: int, us0: int, bayrak: dict | None = None, faz: float = 0.0):
    """n ayrintili ornek, 50 Hz sinus (V) + 0.3 rad kaymali akim, dt ~2 ms titresimli.
    Donus (ornekler [(v, i, dt4, b)], son ornegin us'i). Ilk ornek us0'da (dt4 0)."""
    orn, us = [], us0
    for k in range(n):
        dt4 = 0 if k == 0 else r.tam(470, 530)
        us += 4 * dt4
        t = us / 1e6
        orn.append((int(round(12000 * math.sin(2 * math.pi * 50 * t + faz))),
                    int(round(9000 * math.sin(2 * math.pi * 50 * t + faz + 0.3))),
                    dt4, (bayrak or {}).get(k, 0)))
    return orn, us


def yer_ayrinti(ilk: int, us0: int, orn, bayrak: int = 0) -> bytes:
    return KB.ayrinti_paketle({"ilk": ilk, "t0_ms": (us0 // 1000) & 0xFFFFFFFF,
                               "t0_us": us0 & 0xFFFFFFFF, "bayrak": bayrak, "ornekler": orn})


def yer_skop(r: Rng, no: int, t_ms: int, sure_ms: int, parca: int = 0) -> bytes:
    m = meta_r(r)
    m.update(t_ms=t_ms & 0xFFFFFFFF, sure_ms=sure_ms)
    return skop_yuk(r, no, 0 if parca == 0 else 6, 12, parca, 6, meta=m if parca == 0 else None)


def akis_yerlesim() -> tuple[str, bytes]:
    """Y7 + hizali W: kayit sirasi zaman sirasi DEGIL (yakalama SONRAKI orneklerden sonra
    yazilir), DEVAM'dan sonra sayisal olarak KUCUK t_ms, yakalama verinin oncesinde/sonunda,
    META'siz yetim, menzil gecisi, V/I hatasi, tek ornekli parca, millis sarmali nokta oturumu,
    BASLA'siz ayrinti oturumu."""
    r = Rng(0x2A20)
    a = Akis()
    kal = dataclasses.replace(kal_r(r), sebeke_hz=50.0, faz_kal_us=(40.0, -400.0))
    kal = dataclasses.replace(kal, normal=dataclasses.replace(kal.normal, tau=0.0021),
                              yuksek=dataclasses.replace(kal.yuksek, tau=0.0))
    b = dataclasses.replace(basla_r(r, KB.OTURUM_OLCUM, 0), kal=kal, kart_ms=1_000_000, acilis=3)
    o = 50
    a.k(KB.T_BASLA, o, KB.basla_paketle(b))
    us = 1_000_010_250
    r1, son = yer_ornekler(r, 30, us, {7: KB.KAO_YUKSEK, 8: KB.KAO_YUKSEK, 12: KB.KAO_V_HATA,
                                       20: KB.KAO_I_HATA})
    a.k(KB.T_AYRINTI, o, yer_ayrinti(0, us, r1))
    us = son + 2004
    r2, son = yer_ornekler(r, 20, us)                     # sektor bolmesi: zaman kesintisiz
    a.k(KB.T_AYRINTI, o, yer_ayrinti(30, us, r2))
    t1 = son // 1000                                      # istek son ornekten hemen sonra
    us = (t1 + 37) * 1000 + 1500
    r3, son = yer_ornekler(r, 25, us)
    a.k(KB.T_AYRINTI, o, yer_ayrinti(50, us, r3))
    a.k(KB.T_SKOP, o, yer_skop(r, 1, t1, 37))             # Y7: SONRAKI orneklerden sonra yazilir
    a.k(KB.T_SKOP, o, yer_skop(r, 1, t1, 37, parca=1))
    us = son + 21_000
    r4, son = yer_ornekler(r, 1, us)                      # tek ornekli parca: hizasiz V_k
    a.k(KB.T_AYRINTI, o, yer_ayrinti(75, us, r4, KB.KA_SILME))
    us = son + 30_000
    r5, son = yer_ornekler(r, 10, us)
    a.k(KB.T_AYRINTI, o, yer_ayrinti(76, us, r5))
    t2 = son // 1000 + 1
    a.k(KB.T_SKOP, o, yer_skop(r, 9, 1_000_005, 4))      # verinin ONCESINDE; kayit sirasi gec
    a.k(KB.T_SKOP, o, yer_skop(r, 2, t2, 60, parca=1))    # META'siz yetim: listede yok
    us = (t2 + 60) * 1000 + 900
    r6, son = yer_ornekler(r, 8, us)
    a.k(KB.T_AYRINTI, o, yer_ayrinti(86, us, r6))
    a.k(KB.T_SKOP, o, yer_skop(r, 3, t2, 60))
    a.k(KB.T_DEVAM, o, struct.pack("<IIII", 4, 0, 500, 94))
    us = 600_123
    r7, son = yer_ornekler(r, 15, us, {3: KB.KAO_YUKSEK, 4: KB.KAO_YUKSEK, 5: KB.KAO_YUKSEK})
    a.k(KB.T_AYRINTI, o, yer_ayrinti(94, us, r7))
    t4 = son // 1000 + 2                                  # DEVAM'dan sonra: t_ms acilis 0'dan KUCUK
    us = (t4 + 25) * 1000 + 700
    r8, son = yer_ornekler(r, 10, us)
    a.k(KB.T_AYRINTI, o, yer_ayrinti(109, us, r8))
    a.k(KB.T_SKOP, o, yer_skop(r, 1, t4, 25))
    a.k(KB.T_SKOP, o, yer_skop(r, 2, son // 1000 + 50, 10))   # verinin SONUNDA: sonra None
    a.k(KB.T_BITIR, o, struct.pack("<IB3x", 119, 1))
    # nokta oturumu, millis 2^32 sarmali: yakalama sarmadan once, icine dustugu nokta sonra
    o = 51
    kart0 = 2**32 - 250
    a.k(KB.T_BASLA, o, KB.basla_paketle(dataclasses.replace(basla_r(r, KB.OTURUM_OLCUM, 100),
                                                            kart_ms=kart0)))
    ps = [nokta_r(r, (kart0 + 100 * (k + 1)) & 0xFFFFFFFF) for k in range(6)]
    a.k(KB.T_NOKTA, o, nokta_yuk(0, ps[:3]))
    a.k(KB.T_NOKTA, o, nokta_yuk(3, ps[3:]))
    a.k(KB.T_SKOP, o, yer_skop(r, 1, kart0 + 230, 40))
    a.k(KB.T_SKOP, o, yer_skop(r, 2, kart0 + 100, 5))     # kart_ms TAM esit: o nokta "once"
    a.k(KB.T_BITIR, o, struct.pack("<IB3x", 6, 1))
    # BASLA'siz ayrinti: guc NaN (kalibrasyon yok), yer yine bulunur
    o = 52
    us = 77_000_000
    r9, son = yer_ornekler(r, 6, us)
    a.k(KB.T_AYRINTI, o, yer_ayrinti(0, us, r9))
    a.k(KB.T_SKOP, o, yer_skop(r, 1, us // 1000 + 3, 2))
    return "yerlesim", bytes(a.b)


def w1_kurallar() -> list[str]:
    """W1: hizali guc ve yakalama yeri Python basvurusunda DOGRU mu (vektor yalniz 'ayni' der).
    Bozulan her kural icin bir satir."""
    hatalar: list[str] = []

    def bak(ad: str, kosul: bool, ek: str = "") -> None:
        if not kosul:
            hatalar.append(f"{ad}{': ' + ek if ek else ''}")

    # 1) PC'nin tanimi firmware'inki: kaynak hala bu formulle mi hesapliyor
    ino = (KOK / "kod" / "olcum-karti-a3" / "olcum-karti-a3.ino").read_text(encoding="utf-8")
    o3 = (KOK / "kod" / "olcum-karti-a3" / "olcum3.h").read_text(encoding="utf-8")
    for parca in ("float d = ((float)t_kayma_us + ayar.faz_kal_us[ayar.menzil ? 1 : 0])",
                  "o.volt = hizala_kesirli(d, hv_tampon[0], hv_tampon[1],",
                  "o.amper = hi_tampon[1];", "o.watt = o.volt * o.amper;",
                  "o.watt *= suzgec_ters_kazanc(ayar.sebeke_hz, etkin_kanal()->tau)",
                  "* suzgec_ters_kazanc(ayar.sebeke_hz, TAU_AKIM);"):
        bak("W1.K1 firmware guc tanimi degismedi (olcum_al)", parca in ino, parca)
    m = re.search(r"#define TAU_AKIM\s+([0-9.eE+-]+)f", o3)
    bak("W1.K2 TAU_AKIM == olcum3.h", bool(m) and KB.TAU_AKIM == struct.unpack(
        "<f", struct.pack("<f", float(m.group(1))))[0], m.group(1) if m else "yok")
    for parca in ("h[0] = (d - 0.0f) * (d - 1.0f) * (d - 2.0f) / (-6.0f);",
                  "h[1] = (d + 1.0f) * (d - 1.0f) * (d - 2.0f) / (2.0f);",
                  "h[2] = (d + 1.0f) * (d - 0.0f) * (d - 2.0f) / (-2.0f);",
                  "h[3] = (d + 1.0f) * (d - 0.0f) * (d - 1.0f) / (6.0f);",
                  "w = 6.28318531f * f_hz * tau_s;", "return sqrtf(1.0f + w * w);"):
        bak("W1.K3 olcum3.h lagrange4 / suzgec_ters_kazanc degismedi", parca in o3, parca)
    bak("W1.K4 VI_KAYMA_US tezgah bandinda (tezgah_kart.py 80..400 us)", 80.0 <= KB.VI_KAYMA_US <= 400.0)

    def kanal(pga: float = 4.096, tau: float = 0.0) -> KB.Kanal:
        return KB.Kanal(1.0, pga, 1.0, 0, tau)

    def kal(faz=(0.0, 0.0), f=0.0, tau=0.0, sont=0.005) -> KB.Kalibrasyon:
        return KB.Kalibrasyon(kanal(tau=tau), kanal(40.96), 0, 0.256, sont, 1.0, f, faz)

    def oturum(k: KB.Kalibrasyon, orn, devam=()) -> KB.Oturum:
        o = KB.Oturum(1, basla=KB.Basla(1, 1, 0, 0, 0, 1, "t", k))
        us = orn[0][0]
        o.ayrinti = [{"ilk": 0, "t0_ms": (us // 1000) & 0xFFFFFFFF, "t0_us": us & 0xFFFFFFFF,
                      "bayrak": 0, "sira": 1,
                      "ornekler": [(v, i, 0 if j == 0 else (orn[j][0] - orn[j - 1][0]) // 4, b)
                                   for j, (_t, v, i, b) in enumerate(orn)]}]
        o.devamlar = list(devam)
        return o

    # 2) esit aralikta ic ornek: firmware'in lagrange4 + suzgec olcegiyle AYNI sayi
    T, faz, f, tau = 2000, 37.0, 50.0, 0.0021
    orn = [(5_000_000 + T * j, 1000 * j - 3000 + (j * j) % 7, 500 + 3 * j, 0) for j in range(8)]
    k0 = kal((faz, 0.0), f, tau)
    w = dict(KB.ayrinti_guc(oturum(k0, orn)))
    d = (KB.VI_KAYMA_US + faz) / T
    h = [(d - 0.0) * (d - 1.0) * (d - 2.0) / (-6.0), (d + 1.0) * (d - 1.0) * (d - 2.0) / 2.0,
         (d + 1.0) * (d - 0.0) * (d - 2.0) / (-2.0), (d + 1.0) * (d - 0.0) * (d - 1.0) / 6.0]
    for k in (1, 3, 4):
        vv = [KB.volt(orn[k - 1 + j][1], k0.normal) for j in range(4)]
        g = math.sqrt(1 + (2 * math.pi * f * tau) ** 2) * math.sqrt(1 + (2 * math.pi * f * KB.TAU_AKIM) ** 2)
        fw = sum(h[j] * vv[j] for j in range(4)) * KB.amper(orn[k][2], k0) * g
        bak("W1.K5 esit aralikta PC guc == firmware lagrange4 x I x 1/|H|^2 (ic ornek)",
            abs(w[k] - fw) <= 1e-12 * max(1.0, abs(fw)), f"k={k} pc={w[k]!r} fw={fw!r}")
    # 3) fiziksel: V ve I ayni fazda, I ornegi 1000 us GEC (kayma 152 + faz 848): hizali
    #    ortalama P = AB/2, hizasiz cos(18 derece) = %4.9 dusuk okur
    A, B, faz = 16000, 12000, 1000.0 - KB.VI_KAYMA_US
    kp = kal((faz, 0.0))
    orn, t = [], 9_000_000
    for j in range(2000):                                          # 4 s, titresimli ~2 ms
        t += 4 * (475 + (j * 7919) % 75)
        orn.append((t, int(round(A * math.sin(2 * math.pi * 50 * t / 1e6))),
                    int(round(B * math.sin(2 * math.pi * 50 * (t + 1000) / 1e6))), 0))
    w = [x for _, x in KB.ayrinti_guc(oturum(kp, orn))][2:-2]
    p = sum(w) / len(w)
    gercek = KB.volt(A, kp.normal) * KB.amper(B, kp) / 2
    hizasiz = sum(KB.volt(v, kp.normal) * KB.amper(i, kp) for _, v, i, _ in orn) / len(orn)
    bak("W1.K6 sinus: hizali ortalama guc gercegin %0.5'i icinde (d=0.5'te Lagrange sarkmasi %0.35)",
        abs(p / gercek - 1) < 0.005,
        f"{p / gercek:.5f}")
    bak("W1.K7 sinus: hizasiz V*I %3'ten fazla sapar (test bos degil)", abs(hizasiz / gercek - 1) > 0.03,
        f"{hizasiz / gercek:.5f}")
    # 4) yedek dugumler: parca basi/sonu dogrusal, tek ornek V_k, hata/sont 0 -> NaN
    kq = kal((100.0, -400.0))
    orn = [(1_000_000 + 2000 * j, 100 * j, 50, 0) for j in range(3)] + [(1_100_000, 777, 9, 0)]
    w = dict(KB.ayrinti_guc(oturum(kq, orn)))
    lin = (100 * 1 * 252 / 2000) * (4.096 / KB.ADS_SAYIM) * KB.amper(50, kq)
    bak("W1.K8 parca sonundan bir onceki ornek [k, k+1] dogrusal (k+2 yok)",
        abs(w[1] - KB.volt(100, kq.normal) * KB.amper(50, kq) - lin) < 1e-12, repr(w[1]))
    bak("W1.K9 parcanin son ornegi (kayma >= 0, k+1 baska parcada): hizasiz V_k x I_k",
        w[2] == KB.volt(200, kq.normal) * KB.amper(50, kq), repr(w[2]))
    bak("W1.K10 tek ornekli parca: V_k x I_k", w[3] == KB.volt(777, kq.normal) * KB.amper(9, kq))
    orn = [(1_000_000 + 2000 * j, 100 * (j + 1), 50, KB.KAO_YUKSEK) for j in range(3)]
    w = dict(KB.ayrinti_guc(oturum(kq, orn)))
    vy = [KB.volt(100 * (j + 1), kq.yuksek) for j in range(3)]
    son = (vy[2] - (vy[2] - vy[1]) * 248 / 2000) * KB.amper(50, kq)
    bak("W1.K11 YUKSEK menzil, kayma 152-400 < 0: ilk ornek ([k-1] yok) V_k; son ornek [k-1, k]",
        w[0] == vy[0] * KB.amper(50, kq) and abs(w[2] - son) <= 1e-12 * abs(son), f"{w} {son}")
    orn = [(1_000_000 + 2000 * j, 100, 50, b) for j, b in
           enumerate([0, KB.KAO_V_HATA, 0, KB.KAO_I_HATA, 0])]
    w = dict(KB.ayrinti_guc(oturum(kq, orn)))
    bak("W1.K12 V/I hatali ornek NaN; V hatali komsu dugum olamaz",
        math.isnan(w[1]) and math.isnan(w[3]) and w[0] == KB.volt(100, kq.normal) * KB.amper(50, kq)
        and math.isfinite(w[2]) and math.isfinite(w[4]),
        f"{w}")
    w = KB.ayrinti_guc(oturum(kal(sont=0.0), orn))
    bak("W1.K13 sont 0: hepsi NaN", all(math.isnan(x) for _, x in w))
    orn = [(2_000_000 + 2000 * j, 100 * j * j, 50, 0) for j in range(6)]
    kz = kal((9000.0, -9000.0))
    w = dict(KB.ayrinti_guc(oturum(kz, orn)))
    bak("W1.K18 kayma dugum araligini asarsa x kirpilir (kartin d kirpmasi): ic ornekte V_(k+2)",
        w[2] == KB.volt(1600, kz.normal) * KB.amper(50, kz), f"{w[2]!r}")
    # 5) yakalamanin yeri: kayit sirasi zaman sirasi degil; acilis DEVAM'dan
    ot = KB.oturumlari_kur(KB.akis_coz(akis_yerlesim()[1]))
    y = KB.skop_yerleri(ot[50])
    orn = {s: (us, ac) for s, us, *_x, ac in KB.ayrinti_ornekler(ot[50])}
    bak("W1.K14 yerler ZAMAN sirasinda (no 9 verinin oncesinde, kaydi gec)",
        [x["no"] for x in y] == [9, 1, 3, 1, 2], f"{[x['no'] for x in y]}")
    ic = [x for x in y if x["once"] is not None and x["sonra"] is not None]
    bak("W1.K15 once < istek <= sonra, ayni acilis; bosluk yakalama suresinden uzun",
        len(ic) == 3 and all(orn[x["once"]][0] < (x["t_ms"] + 1) * 1000 <= orn[x["sonra"]][0]
                             and orn[x["once"]][1] == orn[x["sonra"]][1] == x["acilis"]
                             and orn[x["sonra"]][0] - orn[x["once"]][0] > x["sure_ms"] * 1000
                             for x in ic), f"{ic}")
    bak("W1.K16 verinin oncesi: once None, sonra ilk ornek; sonu: sonra None",
        y[0]["once"] is None and y[0]["sonra"] == 0 and y[-1]["sonra"] is None
        and y[-1]["once"] == 118 and [x["acilis"] for x in y] == [0, 0, 0, 1, 1], f"{y}")
    yn = KB.skop_yerleri(ot[51])
    bak("W1.K17 nokta oturumu, millis sarmasi: yakalama icine dustugu noktada (kart_ms > t_ms)",
        [(x["no"], x["once"], x["sonra"]) for x in yn] == [(2, 0, 1), (1, 1, 2)], f"{yn}")
    return hatalar


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
    # S6: tam sektor olmayan goruntu (yarim dokum). < 16 B kuyruk BOS sayilir (cop olsa da),
    # basligi tam / yuku eksik kayit yarim (bozuk +1)
    v += [("flas_kuyruk_cop_8", s0 + devam(90) + bytes(0xA5 ^ i for i in range(8)), S),
          ("flas_kuyruk_baslik_15", s0 + devam(91) + devam(92)[:15], S),
          ("flas_kuyruk_yuk_eksik", s0 + devam(93) + devam(94)[:20], S),
          ("flas_kuyruk_yalniz_baslik", s0 + devam(95) + devam(96)[:16], S),
          ("flas_goruntu_baslik_kisa", devam(97)[:10], S),
          ("flas_kuyruk_ikinci_sektor_ortasi", s0 + s4[:100], S)]
    out = []
    for ad, veri, sek in v:
        d = {"ad": ad, "veri": j(veri), "sektor": sek, "flas_coz": dene(KB.flas_coz, veri, sek)}
        if "hata" not in d["flas_coz"]:
            try:
                ot = KB.oturumlari_kur(KB.flas_coz(veri, sek)[0])
                d["oturumlari_kur"] = jot(ot)
                if ot.uyarilar:
                    d["oturumlari_kur_uyarilar"] = j(ot.uyarilar)
            except Exception as e:  # noqa: BLE001
                d["oturumlari_kur"] = hata(e)
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
    if ot.uyarilar:                       # S5: yalniz doluysa (eski vektorler bayt bayt ayni)
        d["oturumlari_kur_uyarilar"] = j(ot.uyarilar)
    d["ayrinti_ornekler"] = [[i, j(KB.ayrinti_ornekler(o))] for i, o in ot.items() if o.ayrinti]
    d["skop_ikili"] = [[i, s, j(KB.skop_ikili(y))] for i, o in ot.items()
                       for s, y in o.skoplar.items()]
    # W1: yakalamanin yeri (Y7) ve hizali guc — yalniz ilgili oturumlar
    d["skop_yerleri"] = [[i, j(KB.skop_yerleri(o))] for i, o in ot.items() if o.skoplar]
    d["ayrinti_guc"] = [[i, j(KB.ayrinti_guc(o))] for i, o in ot.items() if o.ayrinti]
    # HT3: hat direnci — yalniz KO_PIL_HAT olayli oturum varsa (eski akislarin vektoru bayt bayt ayni)
    hat = [(i, o) for i, o in ot.items() if any(x["tur"] == KB.KO_PIL_HAT for x in o.olaylar)]
    if hat:
        d["pil_hat_mohm_at"] = [[i, [[t, KB.pil_hat_mohm_at(o, t)] for t in _hat_anlari(o)]] for i, o in hat]
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
    # HT3: KO_PIL_HAT (12 B) ve pil_v_duzelt — ayri tohum: onceki vakalar degismez
    rh = Rng(0x2A1B)
    y = KB.olay_paketle(olay_r(rh, KB.KO_PIL_HAT, rh.tam(0, 2**32 - 1)))
    vaka("olay_coz", y)
    vaka("olay_coz", y[:-1])                             # kisa: ham
    vaka("olay_coz", y + rh.bayt(3))                     # uzun: fazlasi atilir
    vaka("olay_paketle", olay_r(rh, KB.KO_PIL_HAT, rh.tam(0, 2**32 - 1)))
    vaka("olay_paketle", {"tur": KB.KO_PIL_HAT, "kart_ms": 1, "hat_mohm": -1})          # struct.error
    for v, i, h in ((3.793, 1.128, 153), (3.793, 1.128, 0), (4.1, float("nan"), 0), (4.1, float("nan"), 5),
                    (-0.0, 1.0, 0), (3.0, 0.5, -3), (3.0, 0.5, float("nan")), (3.0, -0.25, 1000),
                    (2.5, 0.75, 1), (12.0, float("inf"), 0),
                    (3.2542, 2.5122, 559), (1.2249, 2.5759, 202)):   # i x (R / 1000) != (i x R) / 1000: aritmetik SIRASI
        vaka("pil_v_duzelt", v, i, h)
    # HT2 (butunlestirici karari): pilin verdigi guc w + I^2 x R — son ikisi aritmetik SIRASINI ayirt eder
    for w, i, h in ((3.793 * 1.128, 1.128, 153), (4.0, 1.0, 0), (4.0, float("nan"), 0), (4.0, float("nan"), 5),
                    (-0.0, 1.0, 0), (3.0, 0.5, -3), (3.0, 0.5, float("nan")), (-1.85, -0.5, 100),
                    (12.0, float("inf"), 0), (7.3408, 2.1328, 993), (8.3464, 1.4824, 737)):
        vaka("pil_w_duzelt", w, i, h)
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


# ── S5/S6 kurallari: Python basvurusunda DOGRUDAN (vektor yalniz JS == Python der) ──
def kurallar() -> list[str]:
    """Bozulan her kural icin bir satir; bos liste = hepsi tutuyor."""
    r = Rng(0x2A15)
    hatalar: list[str] = []

    def bak(ad: str, kosul: bool, ek: str = "") -> None:
        if not kosul:
            hatalar.append(f"{ad}{': ' + ek if ek else ''}")

    def kur(*kayitlar):
        try:
            return KB.oturumlari_kur(list(kayitlar))
        except Exception as e:  # noqa: BLE001
            return e

    def ayni(x, y) -> bool:
        return (not isinstance(x, Exception) and not isinstance(y, Exception)
                and tek(jot(x)) == tek(jot(y)))

    K = KB.Kayit
    o = 9
    bas2 = KB.basla_paketle(basla_r(r, KB.OTURUM_OLCUM, 100, kal_no=3))
    bas1 = basla_v1(basla_r(r, KB.OTURUM_PIL, 5))
    tam = {   # tur -> bilinen boyda yuk(ler)
        KB.T_BASLA: [bas2, bas1], KB.T_TEKRAR: [bas2, bas1],
        KB.T_NOKTA: [nokta_yuk(0, [nokta_r(r, 1), nokta_r(r, 2)])],
        KB.T_DEVAM: [struct.pack("<IIII", 2, 3, 4, 5)], KB.T_BITIR: [struct.pack("<IB3x", 6, 1)],
        KB.T_SAAT: [struct.pack("<III", 7, 8, 9)],
        KB.T_OLAY: [KB.olay_paketle(olay_r(r, t, 10)) for t in (1, 2, 3, 4, 5, 6)],
        KB.T_AYRINTI: [ayrinti_yuk(r, 0, 1, 1000, 0, 3)],
        KB.T_SKOP: [skop_yuk(r, 1, 0, 4, 0, 4), skop_yuk(r, 1, 4, 8, 1, 4)],
    }
    # S5-1: UZUN kayit = bilinen on ek + fazlasi; sonuc ayni, uyari yok, cokme yok.
    # Fazlalik < 36 (NOKTA'da 36 B yeni bir nokta olur); surum 1 BASLA'da < 4 (102 B'tan
    # itibaren boy surum 2 der: kal_no okunur — boya gore surum karari)
    for tur, yukler in tam.items():
        for y in yukler:
            for ek in ((1, 3) if y is bas1 else (1, 3, 4, 35)):
                a, b = kur(K(tur, 1, o, y)), kur(K(tur, 1, o, y + r.bayt(ek)))
                bak(f"S5 uzun tur {tur} (+{ek} B) on eki cozulmedi", ayni(a, b)
                    and not b.uyarilar and o in b, repr(b) if isinstance(b, Exception) else "")
    # S5-2: KISA kayit: cokmez, atlanir, oturum ACMAZ, uyari (sira/tur/oturum/bayt/en_az)
    for tur, n in EN_AZ_BAGIMSIZ:
        for m in sorted({0, n - 1}):
            x = kur(K(tur, 5, o, r.bayt(m)), K(KB.T_DEVAM, 6, 3, bytes(16)))
            bak(f"S5 kisa tur {tur} ({m} B) atlanmadi / uyarmadi",
                not isinstance(x, Exception) and list(x) == [3]
                and x.uyarilar == [{"sira": 5, "tur": tur, "oturum": o, "bayt": m, "en_az": n}],
                repr(x) if isinstance(x, Exception) else f"{list(x)} {x.uyarilar}")
        x = kur(K(tur, 5, o, bytes(n)))
        bak(f"S5 tam en kisa boy tur {tur} ({n} B) reddedildi",
            not isinstance(x, Exception) and not x.uyarilar, repr(x))
    # S6: bilinmeyen tur oturum ACMAZ, sirayi etkilemez; uyari da yok
    x = kur(K(77, 1, 50, b"abc"), K(KB.T_DEVAM, 2, 51, bytes(16)), K(KB.T_DEVAM, 3, 50, bytes(16)),
            K(200, 4, 52, b""))
    bak("S6 bilinmeyen tur oturum acti / sirayi degistirdi",
        not isinstance(x, Exception) and list(x) == [51, 50] and not x.uyarilar, repr(x))
    # S6: flas goruntusu HER uzunlukta kesilince cokmez; tam icerilen kayitlar AYNEN cozulur;
    # yarim kayit (basligi tam) bozuk, < 16 B kuyruk bos
    S = 112                                   # 3 kayit (96 B) + 16 B silinmis
    img = b""
    for s in range(2):
        sek = b"".join(KB.kayit_paketle(KB.T_DEVAM, 10 * s + i, 1, struct.pack("<IIII", i, 0, 0, 0))
                       for i in range(1, 3)) + KB.kayit_paketle(KB.T_SAAT, 10 * s + 3, 1, bytes(13))
        img += sek + b"\xff" * (S - len(sek))
    tum, bz = KB.flas_coz(img, S)
    bak("S6 flas taban", bz == 0 and len(tum) == 6, f"{len(tum)} {bz}")
    for L in range(len(img) + 1):
        try:
            kay, bz = KB.flas_coz(img[:L], S)
        except Exception as e:  # noqa: BLE001
            bak(f"S6 flas {L} B'de cokuyor", False, repr(e))
            continue
        bek = [k.sira for k in tum if k.adres + KB.toplam_bayt(len(k.yuk)) <= L]
        yarim = any(k.adres + 16 <= L < k.adres + KB.toplam_bayt(len(k.yuk)) for k in tum)
        bak(f"S6 flas {L} B: kayitlar/bozuk", [k.sira for k in kay] == bek and bz == int(yarim),
            f"{[k.sira for k in kay]} != {bek} ya da bozuk {bz} != {int(yarim)}")
    # S6: sont_ohm 0 / -0 -> NaN (ZeroDivisionError YOK); sifir olmayan sont degismedi
    kal = kal_r(r)
    for so in (0.0, -0.0):
        try:
            v = [KB.amper(kod, dataclasses.replace(kal, sont_ohm=so)) for kod in (0, 5, 1.5, -40000)]
            bak(f"S6 amper sont {so!r} NaN degil", all(math.isnan(x) for x in v), str(v))
        except Exception as e:  # noqa: BLE001
            bak(f"S6 amper sont {so!r} cokuyor", False, repr(e))
    kb = dataclasses.replace(kal, i_ofset=0, i_pga=32768.0, sont_ohm=2.0, i_duzeltme=1.0)
    bak("S6 amper sifir olmayan sont", KB.amper(100, kb) == 50.0, str(KB.amper(100, kb)))
    return hatalar


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
            akis_rastgele(0x2A10, 70), akis_rastgele(0x2A11, 70)] + akis_bozuklar() + [
        akis_uzun_kayitlar(), akis_kisa_kayitlar(), akis_bilinmeyen_oturum(), akis_surum_nul(),
        akis_yerlesim(), akis_pil_hat()]
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
    kh = kurallar() + w1_kurallar()
    for s in kh[:30]:
        print("  KURAL " + s)
    if kh:
        print(f"KIRMIZI: S5/S6 kurallari Python basvurusunda tutmuyor ({len(kh)})")
        return 1
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
