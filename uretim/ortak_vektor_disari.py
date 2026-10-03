# -*- coding: utf-8 -*-
"""B73 / 2F — disa aktarma CAPRAZ UYGULAMA vektorleri (tasarim 2026-10-02 O3).

Python basvurusu `kopru/kayit_bicim.py` (kartla dogrulandi) ile sabit tohumlu sentetik
akislar kurulur ve CSV'nin SAYI/ZAMAN hucreleri BAGIMSIZ olarak (bu dosyadaki ayri Python
kodu) hesaplanir; sonuc `ortak/test/vektor/disari.json`. JS (`ortak/src/disari.js`,
`rapor.js`) `node --test ortak/test/disari.test.js` ile ayni hucreleri BIRE BIR vermeli.

    python ortak_vektor_disari.py            # dosyayi (yeniden) yaz
    python ortak_vektor_disari.py --denetle  # depodaki dosya Python'la hala ayni mi (degilse 1)

Kapsam:
  sayi    : format(x, ".Nf") (Python: tam ikili degerden en yakin, yarida cifte) — JS sayiYaz
            ayni dizgeyi vermeli. Tek bilinen fark: sifira yuvarlanan eksi isaretsiz ("0.000").
  akislar : olcum (DEVAM'li, unix'li, kart_ms 2^32 sarmali, YUKSEK menzil, n=0 nokta),
            saatsiz BASLA + sonradan SAAT + saatsiz DEVAM, pil (DCIR olaylariyla, birikimli
            mAh/Wh), ayrintili (her ornek, KA_SILME/KA_KAYIP_ONCE, DEVAM, hatali ornek).
  Zaman modeli disari.js'teki belgeli kural: acilis capasi BASLA/DEVAM (unix 0 ise ayni
  acilisin SAAT'i), acilis icinde ardisik isaretli 32 bit fark; gecen = capa farki + rel.
  Enerji: acilis basina yamuk + Neumaier, bosluk > hiz x 2.5 (ayrintili > 16.38 ms) haric.
  W1: ayrintili W = HIZALI guc (bu dosyadaki ayri kod, `hizali_guc`; kayit_bicim.ayrinti_guc'un
  tanimi): V akim ornegi anina (zaman + VI_KAYMA_US + faz_kal_us) Lagrange'la, x I, sebeke
  RC ters kazanci. Y7: yakalamalar META t_ms ile; kayit sirasi zaman sirasi DEGIL (akislarda
  SKOP kaydi sonraki verilerden sonra yazilir); yakalamadan sonraki ilk satir `skop_sonra`.

JSON: float repr ile (JS ayni double'i okur); sonsuz/NaN {"$f": ...}. Ondalik ayraci '.'.
Rastgelelik kendi splitmix64'umuzden: Python surumune bagli degil.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
import kayit_bicim as KB  # noqa: E402

HEDEF = KOK / "ortak" / "test" / "vektor" / "disari.json"
M64 = (1 << 64) - 1
AYRINTI_BOSLUK_MS = 4095 * 4 / 1000


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


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def jf(x: float):
    if math.isnan(x):
        return {"$f": "nan"}
    if math.isinf(x):
        return {"$f": "inf" if x > 0 else "-inf"}
    return x


# ── sayi yazimi (Python basvurusu) ────────────────────────────────────
def sayi_yaz(x: float, b: int) -> str:
    if not math.isfinite(x):
        return ""
    s = format(x, f".{b}f")
    if s.startswith("-") and not any(c in "123456789" for c in s):
        s = s[1:]
    return s


def sayi_vektorleri() -> list:
    r = Rng(0x2F5A11)
    xs = [0.0, -0.0, 0.5, 1.5, 2.5, -2.5, 0.125, 0.375, -0.375, 0.0078125, 0.9765625, 1.0000005,
          0.15, 2.675, 1.005, 1e-7, -1e-9, 5e-324, 1e15 + 0.5, 123456789.123456789, 1e21, 1e22,
          -1e22, 1.7976931348623157e308, 2.0 ** -30, 4.35, 0.045, 999999.9999995, -999999.9999995,
          float("nan"), float("inf"), float("-inf")]
    # tam ortadaki degerler: tek / 2^(b+1) (b = 0..9) — toFixed'in yarida yukari gittigi yer
    for b in range(0, 10):
        for _ in range(6):
            xs.append(r.tam(-10**6, 10**6) * 2 + 1)
            xs[-1] = xs[-1] / 2 ** (b + 1)
    # float32 kokenli ve olcum buyuklugunde rastgele degerler
    for _ in range(300):
        e = r.tam(-12, 9)
        x = r.kesir(-1, 1) * 10.0 ** e
        xs.append(f32(x) if r.tam(0, 1) else x)
    out = []
    for x in xs:
        for b in (0, 3, 6, 9):
            out.append([jf(x), b, sayi_yaz(x, b)])
    return out


# ── zaman modeli (bagimsiz Python) ────────────────────────────────────
def i32(x: int) -> int:
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x >= 1 << 31 else x


def segmentler(o: KB.Oturum):
    b = o.basla
    dv = sorted(o.devamlar, key=lambda d: d["nokta_sira"])
    seg = [{"acilis": b.acilis, "kart": b.kart_ms, "unix": b.unix_s * 1000 if b.unix_s else None}]
    for d in dv:
        seg.append({"acilis": d["acilis"], "kart": d["kart_ms"],
                    "unix": d["unix_s"] * 1000 if d["unix_s"] else None})
    for s in seg:
        if s["unix"] is None:
            for z in o.saatler:
                if z["acilis"] == s["acilis"] and z["unix_s"]:
                    s["unix"] = z["unix_s"] * 1000 - i32(z["kart_ms"] - s["kart"])
                    break
    u0 = seg[0]["unix"]
    for j, s in enumerate(seg):
        s["ofset"] = 0 if j == 0 else (s["unix"] - u0 if s["unix"] is not None and u0 is not None else None)
    return seg, [d["nokta_sira"] for d in dv]


def olcekli(n: int, b: int) -> str:
    eksi = n < 0
    s = str(abs(n)).rjust(b + 1, "0")
    s = s[:-b] + "." + s[-b:] if b else s
    return ("-" if eksi and abs(n) else "") + s


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms // 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{ms % 1000:03d}Z"


class Toplam:
    def __init__(self):
        self.s = 0.0
        self.d = 0.0

    def ekle(self, x: float) -> None:
        s = self.s + x
        if abs(self.s) >= abs(x):
            self.d += (self.s - s) + x
        else:
            self.d += (x - s) + self.s
        self.s = s

    @property
    def deger(self) -> float:
        return self.s + self.d


def nokta_satirlari(o: KB.Oturum) -> list[dict]:
    seg, dsira = segmentler(o)
    kal = o.basla.kal
    rows, once = [], None
    for s, p in sorted(o.noktalar, key=lambda x: x[0]):
        sg = sum(1 for d in dsira if d <= s)
        rel = once[2] + i32(p.kart_ms - once[1]) if once and once[0] == sg else i32(p.kart_ms - seg[sg]["kart"])
        once = (sg, p.kart_ms, rel)
        z = seg[sg]
        g = z["ofset"] + rel if z["ofset"] is not None else None
        u = z["unix"] + rel if z["unix"] is not None else None
        nan = float("nan")
        if p.n:
            k = kal.yuksek if p.bayrak & KB.KN_YUKSEK else kal.normal
            vs = [KB.volt(p.v_ort_kod, k), KB.volt(p.v_min_kod, k), KB.volt(p.v_maks_kod, k)]
            as_ = [KB.amper(p.i_ort_kod, kal), KB.amper(p.i_min_kod, kal), KB.amper(p.i_maks_kod, kal)]
            ws = [p.w_ort, p.w_min, p.w_maks]
        else:
            vs, as_, ws = [nan] * 3, [nan] * 3, [nan] * 3
        rows.append({"sira": s, "acilis": sg, "rel": rel, "kart": p.kart_ms, "gecen": g, "unix": u,
                     "n": p.n, "v": vs, "a": as_, "w": ws, "bayrak": p.bayrak})
    return rows


def birikimli(rows, deger, bolen, bosluk) -> list[float]:
    out, devir, toplam, var, seg = [], 0.0, Toplam(), False, None
    t_once = a_once = 0.0
    for r in rows:
        if r["acilis"] != seg:
            if seg is not None:
                devir += toplam.deger / bolen
            toplam, var, seg = Toplam(), False, r["acilis"]
        x = deger(r)
        if not math.isnan(x):
            if var:
                dt = float(r["rel"] - t_once)
                if dt <= bosluk:
                    toplam.ekle((a_once + x) * dt / 2)
            var, t_once, a_once = True, r["rel"], x
        out.append(devir + toplam.deger / bolen)
    return out


def nokta_hucreleri(rows) -> list[list]:
    out = []
    for r in rows:
        out.append([str(r["sira"]), str(r["acilis"]), str(r["kart"]),
                    "" if r["gecen"] is None else str(r["gecen"]),
                    "" if r["unix"] is None else olcekli(r["unix"], 3),
                    "" if r["unix"] is None else iso(r["unix"]),
                    str(r["n"])] + [sayi_yaz(x, 6) for x in r["v"] + r["a"] + r["w"]] + [str(r["bayrak"])])
    return out


# ── akis kurucu ───────────────────────────────────────────────────────
class Akis:
    def __init__(self, sira0: int = 0):
        self.sira = sira0
        self.parca: list[bytes] = []

    def ekle(self, tur: int, oturum: int, yuk: bytes) -> int:
        self.sira += 1
        self.parca.append(KB.kayit_paketle(tur, self.sira, oturum, yuk))
        return self.sira

    def bayt(self) -> bytes:
        return b"".join(self.parca)


def kanal_r(r: Rng, n0: float) -> KB.Kanal:
    return KB.Kanal(f32(n0 * r.kesir(0.99, 1.01)), f32(r.secim([6.144, 4.096, 2.048])),
                    f32(r.kesir(0.95, 1.05)), r.tam(-300, 300), 0.0)


def kal_r(r: Rng) -> KB.Kalibrasyon:
    return KB.Kalibrasyon(kanal_r(r, 21.0), kanal_r(r, 201.0), r.tam(-200, 200), f32(0.256),
                          f32(r.secim([0.005, 0.015])), f32(r.kesir(0.98, 1.02)), 50.0, (0.0, 0.0))


def basla(r, tur, hiz, unix, kart, acilis, kal) -> bytes:
    return KB.basla_paketle(KB.Basla(tur, 1, hiz, unix, kart, acilis, "A3-2F", kal, kal_no=r.tam(1, 9)))


def nokta_r(r: Rng, ms: int, bos: bool = False) -> KB.Nokta:
    if bos:
        return KB.Nokta(ms, 0, KB.KN_V_HATA | KB.KN_I_HATA, 0.0, 0, 0, 0.0, 0, 0, 0.0, 0.0, 0.0)
    v = r.tam(-20000, 30000)
    i = r.tam(-3000, 20000)
    w = f32(r.kesir(-2, 40))
    bayrak = r.secim([0, 0, 0, KB.KN_YUKSEK, KB.KN_DURAKLAMA, KB.KN_KAYIP_ONCE, KB.KN_V_DOYDU])
    return KB.Nokta(ms, r.tam(1, 500), bayrak, f32(v + r.kesir(-0.5, 0.5)), v - r.tam(0, 900),
                    min(32767, v + r.tam(0, 900)), f32(i + r.kesir(-0.5, 0.5)), i - r.tam(0, 300),
                    i + r.tam(0, 300), w, f32(w - 1), f32(w + 1))


def noktalar_yaz(a: Akis, ot: int, ilk: int, ns: list) -> None:
    for j in range(0, len(ns), 5):          # 5'er noktalik kayitlar
        a.ekle(KB.T_NOKTA, ot, struct.pack("<I", ilk + j) + b"".join(KB.nokta_paketle(p) for p in ns[j:j + 5]))


def olcum_akisi(r: Rng, saatsiz: bool) -> tuple[bytes, int]:
    a = Akis(r.tam(0, 50))
    kal = kal_r(r)
    hiz = 1000
    kart0 = 2**32 - 3500 if not saatsiz else 1234
    unix0 = 0 if saatsiz else 1_790_000_000
    ot = a.ekle(KB.T_BASLA, a.sira + 1, basla(r, KB.OTURUM_OLCUM, hiz, unix0, kart0, 7, kal))
    ns, ms = [], kart0
    for k in range(23):
        ms = (ms + hiz + (5000 if k == 15 else 0)) & 0xFFFFFFFF   # 15'te ic bosluk
        ns.append(nokta_r(r, ms, bos=(k == 9)))
    noktalar_yaz(a, ot, 0, ns)
    # Y7: yakalama nokta 2'nin icine duser (kart_ms 2^32 sarmasinin ustunden), kaydi 23 noktadan
    # SONRA yazilir (kayit sirasi zaman sirasi degil)
    a.ekle(KB.T_SKOP, ot, skop_yuk(1, (kart0 + 2500) & 0xFFFFFFFF, 80))
    if saatsiz:
        a.ekle(KB.T_SAAT, ot, struct.pack("<III", 1_790_100_000, (kart0 + 7300) & 0xFFFFFFFF, 7))
    a.ekle(KB.T_DEVAM, ot, struct.pack("<IIII", 8, 0 if saatsiz else 1_790_000_060, 5200, 23))
    ns = [nokta_r(r, 5200 + 1000 * (k + 1)) for k in range(12)]
    noktalar_yaz(a, ot, 23, ns)
    # DEVAM'dan sonra: t_ms 8700 HEM acilis 0'in HEM acilis 1'in araligina uyar (sezgi BELIRSIZ);
    # acilis yakalamanin kendisinden (kayitta DEVAM sayisi) — W1
    a.ekle(KB.T_SKOP, ot, skop_yuk(2, 8700, 300))
    a.ekle(KB.T_DEVAM, ot, struct.pack("<IIII", 9, 0 if saatsiz else 1_790_000_200, 4800, 35))
    ns = [nokta_r(r, 4800 + 1000 * (k + 1)) for k in range(6)]
    noktalar_yaz(a, ot, 35, ns)
    a.ekle(KB.T_BITIR, ot, struct.pack("<IB3x", 41, 1))
    return a.bayt(), ot


def skop_yuk(no: int, t_ms: int, sure_ms: int) -> bytes:
    """Tek parcali, META'li yakalama (rastgelelik CEKMEZ: diger vektorler kaymasin)."""
    meta = {"t_ms": t_ms, "sure_ms": sure_ms, "hz": 50000, "tdiv_us": 100, "adim": 0.0119140625,
            "ofset": 63.5, "tetik": 2, "esik": 2048, "histerezis": 40, "kip": 1, "tetiklendi": 1,
            "kenar": 0, "on_yuzde": 25, "onay": 2}
    return KB.skop_paketle({"no": no, "ilk": 0, "toplam": 4, "parca": 0, "meta": meta,
                            "kodlar": [100, 2048, 4000, 7]})


def pil_akisi(r: Rng) -> tuple[bytes, int]:
    a = Akis(r.tam(100, 200))
    kal = kal_r(r)
    hiz = 500
    kart0 = 90_000
    ot = a.sira + 1
    ot = a.ekle(KB.T_BASLA, ot, basla(r, KB.OTURUM_PIL, hiz, 1_790_500_000, kart0, 12, kal))
    a.ekle(KB.T_OLAY, ot, KB.olay_paketle({"tur": KB.KO_PIL_AYAR, "kart_ms": kart0 + 1, "kesme_v": 3.0,
                                           "ocv": 4.1, "azami_s": 36000, "dcir_aralik_ms": 3000,
                                           "dcir_ms": 200, "kayit_hz": 2.0}))
    ms, ns = kart0, []
    for k in range(30):
        ms += hiz + (2000 if k == 20 else 0)
        ns.append(nokta_r(r, ms, bos=(k == 4)))
    sira_n = 0
    for j in range(0, 30, 6):
        a.ekle(KB.T_NOKTA, ot, struct.pack("<I", sira_n) + b"".join(KB.nokta_paketle(p) for p in ns[j:j + 6]))
        sira_n += 6
        d_ms = ns[j + 5].kart_ms if j == 12 else ns[j + 2].kart_ms + 120   # biri noktayla AYNI an
        a.ekle(KB.T_OLAY, ot, KB.olay_paketle({
            "tur": KB.KO_DCIR, "kart_ms": d_ms, "no": j // 6 + 1, "v_once": f32(r.kesir(3, 4.2)),
            "i_once": f32(r.kesir(0.5, 1.5)), "v_ani": f32(r.kesir(3, 4.2)), "v_oturmus": f32(r.kesir(3, 4.2)),
            "r_ani": f32(r.kesir(0.02, 0.2)), "r_oturmus": f32(r.kesir(0.02, 0.2)),
            "mah": f32(r.kesir(0, 3000)), "wh": f32(r.kesir(0, 10))}))
    a.ekle(KB.T_OLAY, ot, KB.olay_paketle({"tur": KB.KO_PIL_SONUC, "kart_ms": ms + 3, "durum": 2, "hata": 0,
                                           "mah": 12.5, "wh": 0.05, "ocv": 4.1, "v_son": 3.0,
                                           "sure_ms": ms - kart0, "dcir_sayisi": 5}))
    a.ekle(KB.T_BITIR, ot, struct.pack("<IB3x", 30, 4))
    return a.bayt(), ot


def ayrinti_akisi(r: Rng) -> tuple[bytes, int]:
    a = Akis(r.tam(300, 400))
    kal = kal_r(r)
    # W1: hizalama yollari — normal kayma 152+55 > 0, YUKSEK 152-300 < 0; normal kanalda RC
    # (sebeke 50 Hz: ters kazanc), yuksekte tau 0 (carpan 1)
    kal = dataclasses.replace(kal, faz_kal_us=(55.0, -300.0),
                              normal=dataclasses.replace(kal.normal, tau=0.0021))
    kart0 = 1_000_000
    ot = a.sira + 1
    ot = a.ekle(KB.T_BASLA, ot, basla(r, KB.OTURUM_OLCUM, 0, 1_790_900_000, kart0, 20, kal))

    def kayit(ilk, t_ms, t_us, adet, bayrak):
        orn = []
        for k in range(adet):
            b = r.secim([0, 0, 0, KB.KAO_YUKSEK, KB.KAO_V_HATA, KB.KAO_I_HATA, KB.KAO_V_DOYDU])
            orn.append((r.tam(-20000, 30000), r.tam(-3000, 20000), 0 if k == 0 else r.tam(400, 600), b))
        a.ekle(KB.T_AYRINTI, ot, KB.ayrinti_paketle({"ilk": ilk, "t0_ms": t_ms, "t0_us": t_us,
                                                     "ornekler": orn, "bayrak": bayrak}))
        return ilk + adet
    s = kayit(0, kart0 + 3, (kart0 + 3) * 1000 + 417, 20, 0)
    s = kayit(s, kart0 + 70, (kart0 + 70) * 1000 + 5, 15, KB.KA_SILME)            # 25+ ms duraklama
    s = kayit(s, kart0 + 140, (kart0 + 140) * 1000 + 999, 10, KB.KA_KAYIP_ONCE)
    # Y7: yakalama (t_ms kart0+165, 30 ms); kaydi SONRAKI orneklerden sonra
    s = kayit(s, kart0 + 200, (kart0 + 200) * 1000 + 333, 6, 0)
    a.ekle(KB.T_SKOP, ot, skop_yuk(1, kart0 + 165, 30))
    a.ekle(KB.T_SKOP, ot, skop_yuk(3, kart0 + 1, 1))      # verinin ONCESINDE; kaydi GEC (zaman sirasi)
    a.ekle(KB.T_DEVAM, ot, struct.pack("<IIII", 21, 1_790_900_030, 4000, s))
    s = kayit(s, 4100, 4_100_250, 12, 0)
    s = kayit(s, 4160, 4_160_010, 5, 0)
    a.ekle(KB.T_SKOP, ot, skop_yuk(2, 4130, 20))       # DEVAM'dan sonra: t_ms acilis 0'dan KUCUK
    a.ekle(KB.T_BITIR, ot, struct.pack("<IB3x", s, 1))
    return a.bayt(), ot


# ── W1: hizali guc ve yakalamanin yeri (bagimsiz Python) ──────────────
VI_KAYMA_US = 152.0                 # kartta olculen V-I baslatma kaymasi (B29)
TAU_AKIM = f32(0.002904)            # olcum3.h TAU_AKIM
US_M = 2**32 * 1000


def us_fark(a: int, b: int) -> int:
    d = (a - b) % US_M
    return d - US_M if d >= US_M // 2 else d


def hizali_guc(o: KB.Oturum) -> list[float]:
    """Ornek sirasiyla hizali W. Kesintisiz parca: ayni acilis, ardisik 0 < dt <= 16 380 us.
    Dugum: k-1..k+2 (hepsi parcada + gecerli V) yoksa kaymanin yonundeki komsu ile dogrusal,
    o da yoksa V_k. x dugum araligina kirpilir."""
    kal = o.basla.kal
    orn = sorted(KB.ayrinti_ornekler(o), key=lambda x: x[0])
    n = len(orn)
    nan = float("nan")
    vs = [nan if b & KB.KAO_V_HATA else KB.volt(vk, kal.yuksek if b & KB.KAO_YUKSEK else kal.normal)
          for _s, _u, vk, _i, b, _a in orn]
    parca, p = [0] * n, 0
    for k in range(1, n):
        d = us_fark(orn[k][1], orn[k - 1][1])
        if orn[k][5] != orn[k - 1][5] or not 0 < d <= 4095 * 4:
            p += 1
        parca[k] = p

    def g(f: float, tau: float) -> float:
        if f <= 0 or tau <= 0:
            return 1.0
        w = 2 * math.pi * f * tau
        return math.sqrt(1 + w * w)
    f = kal.sebeke_hz
    olc = [g(f, kn.tau) * g(f, TAU_AKIM) if f > 0 else 1.0 for kn in (kal.normal, kal.yuksek)]
    out = []
    for k, (_s, us, _vk, ik, b, _a) in enumerate(orn):
        if b & KB.KAO_I_HATA or vs[k] != vs[k]:
            out.append(nan)
            continue
        yk = 1 if b & KB.KAO_YUKSEK else 0
        kay = VI_KAYMA_US + kal.faz_kal_us[yk]

        def var(j: int) -> bool:
            return 0 <= j < n and parca[j] == parca[k] and vs[j] == vs[j]
        if all(var(j) for j in (k - 1, k + 1, k + 2)):
            dg = [k - 1, k, k + 1, k + 2]
        elif kay >= 0 and var(k + 1):
            dg = [k, k + 1]
        elif kay < 0 and var(k - 1):
            dg = [k - 1, k]
        else:
            dg = [k]
        dx = [us_fark(orn[j][1], us) for j in dg]
        x = min(max(kay, dx[0]), dx[-1]) if kay == kay else kay
        t = 0.0
        for j in range(len(dg)):
            pay = payda = 1.0
            for m in range(len(dg)):
                if m != j:
                    pay *= x - dx[m]
                    payda *= dx[j] - dx[m]
            t += pay / payda * vs[dg[j]]
        out.append(t * KB.amper(ik, kal) * olc[yk])
    return out


def olcum_zamanlari(o: KB.Oturum) -> list[tuple[int, int, int]]:
    if o.ayrinti and not o.noktalar:
        return [(s_, us, ac) for s_, us, _v, _i, _b, ac in sorted(KB.ayrinti_ornekler(o), key=lambda x: x[0])]
    dv = [d["nokta_sira"] for d in o.devamlar]
    return [(s_, p.kart_ms * 1000, sum(1 for d in dv if d <= s_))
            for s_, p in sorted(o.noktalar, key=lambda x: x[0])]


def yakalama_yerleri(o: KB.Oturum, kayitlar: list) -> list[dict]:
    """Zaman sirasiyla {anahtar, acilis, t_ms, sonra}. Acilis HAM kayitlardan (yakalamanin
    kaydindan once gelen DEVAM sayisi); sonra = ayni acilista zamani >= (t_ms+1) ms olan ilk
    olcum verisi (dogrusal tarama)."""
    dv = sorted(k.sira for k in kayitlar if k.tur == KB.T_DEVAM and k.oturum == o.id)
    veri = olcum_zamanlari(o)
    ilk, out = {}, []
    for anahtar in sorted(o.skoplar):
        y = o.skoplar[anahtar]
        if y["meta"] is None:
            continue
        ac = sum(1 for d in dv if d < anahtar)
        t = y["meta"]["t_ms"]
        t0 = ilk.setdefault(ac, t)
        sonra = next((s_ for s_, us, a in veri if a == ac and us_fark(us, (t + 1) * 1000) >= 0), None)
        out.append(((ac, i32(t - t0), anahtar), {"anahtar": anahtar, "acilis": ac, "t_ms": t, "sonra": sonra}))
    return [d for _, d in sorted(out, key=lambda x: x[0])]


def yakalama_vektoru(o: KB.Oturum, veri: bytes) -> dict:
    yer = yakalama_yerleri(o, KB.akis_coz(veri))
    seg, _ = segmentler(o)
    yak = []
    for y in yer:
        z = seg[y["acilis"]]
        yak.append([y["anahtar"], y["acilis"],
                    None if z["ofset"] is None else z["ofset"] + i32(y["t_ms"] - z["kart"])])
    return {"skop_sonra": sorted(y["sonra"] for y in yer if y["sonra"] is not None), "yakalamalar": yak}


# ── beklenen hucreler ─────────────────────────────────────────────────
def olcum_vektoru(ad: str, veri: bytes, ot: int) -> dict:
    o = KB.oturumlari_kur(KB.akis_coz(veri))[ot]
    rows = nokta_satirlari(o)
    bosluk = o.basla.hiz_ms * 2.5
    wh = birikimli(rows, lambda r: r["w"][0], 3_600_000, bosluk)
    mah = birikimli(rows, lambda r: r["a"][0] if not math.isnan(r["v"][0]) else float("nan"), 3_600, bosluk)
    return {"ad": ad, "veri": veri.hex(), "oturum": ot, "nokta": nokta_hucreleri(rows),
            "enerji": {"wh": jf(wh[-1]), "mah": jf(mah[-1])}, **yakalama_vektoru(o, veri)}


def pil_vektoru(veri: bytes, ot: int) -> dict:
    o = KB.oturumlari_kur(KB.akis_coz(veri))[ot]
    rows = nokta_satirlari(o)
    bosluk = o.basla.hiz_ms * 2.5
    wh = birikimli(rows, lambda r: r["w"][0], 3_600_000, bosluk)
    mah = birikimli(rows, lambda r: r["a"][0] if not math.isnan(r["v"][0]) else float("nan"), 3_600, bosluk)
    sat = [((r["acilis"], r["rel"], 0, k), ["nokta", str(r["sira"]), str(r["kart"]), sayi_yaz(mah[k], 6),
                                            sayi_yaz(wh[k], 6), "", "", "", ""])
           for k, r in enumerate(rows)]
    for o_ in sorted(o.olaylar, key=lambda x: x["sira"]):
        if o_["tur"] != KB.KO_DCIR:
            continue
        rel = i32(o_["kart_ms"] - o.basla.kart_ms)
        sat.append(((0, rel, 1, o_["sira"]), ["dcir", "", str(o_["kart_ms"]), "", "", str(o_["no"]),
                                              sayi_yaz(o_["r_ani"], 6), sayi_yaz(o_["r_oturmus"], 6),
                                              sayi_yaz(o_["mah"], 6)]))
    sat.sort(key=lambda x: x[0])
    return {"veri": veri.hex(), "oturum": ot, "satirlar": [s for _, s in sat],
            "enerji": {"wh": jf(wh[-1]), "mah": jf(mah[-1])}}


def ayrinti_vektoru(veri: bytes, ot: int) -> dict:
    o = KB.oturumlari_kur(KB.akis_coz(veri))[ot]
    seg, _ = segmentler(o)
    kal = o.basla.kal
    M = 2**32 * 1000
    # kaydin KA bayragi: ornegi SAGLAYAN kaydin ilk ornegiyse
    ka, gorulen = {}, set()
    for rk in sorted(o.ayrinti, key=lambda x: x["sira"]):
        for j in range(len(rk["ornekler"])):
            s = rk["ilk"] + j
            if s in gorulen:
                continue
            gorulen.add(s)
            if j == 0 and rk["bayrak"]:
                ka[s] = rk["bayrak"]
    rows = []
    wler = hizali_guc(o)
    tum = []                         # enerji: (acilis, rel us, v, i, w)
    for (s, us, v, i, b, ac), w_al in zip(sorted(KB.ayrinti_ornekler(o), key=lambda x: x[0]), wler):
        z = seg[ac]
        rel = (us - z["kart"] * 1000) % M
        if rel >= M // 2:
            rel -= M
        g = z["ofset"] * 1000 + rel if z["ofset"] is not None else None
        u = z["unix"] * 1000 + rel if z["unix"] is not None else None
        if u is not None:
            q, kalan = divmod(u, 1000)
            if 2 * kalan > 1000 or (2 * kalan == 1000 and q % 2):
                q += 1
            u = q
        vv = float("nan") if b & KB.KAO_V_HATA else KB.volt(v, kal.yuksek if b & KB.KAO_YUKSEK else kal.normal)
        ii = float("nan") if b & KB.KAO_I_HATA else KB.amper(i, kal)
        rows.append([str(s), str(ac), str(us), "" if g is None else olcekli(g, 3),
                     "" if u is None else olcekli(u, 3), "" if u is None else iso(u),
                     sayi_yaz(vv, 6), sayi_yaz(ii, 6), sayi_yaz(w_al, 6), str(b), str(ka.get(s, 0))])
        tum.append((ac, rel, vv, ii, w_al))
    # enerji: acilis basina yamuk (ms), bosluk > 16.38 ms haric; Wh hizali W'den, mAh A'dan
    wh = mah = 0.0
    for ac in sorted({x[0] for x in tum}):
        tw, ta, once = Toplam(), Toplam(), None
        for _a, rel, vv, ii, w_al in (x for x in tum if x[0] == ac):
            if math.isnan(vv) or math.isnan(ii):
                continue
            if once is not None and (rel - once[0]) / 1000 <= AYRINTI_BOSLUK_MS:
                dt = (rel - once[0]) / 1000
                if not math.isnan(w_al) and not math.isnan(once[2]):
                    tw.ekle((once[2] + w_al) * dt / 2)
                ta.ekle((once[1] + ii) * dt / 2)
            once = (rel, ii, w_al)
        wh += tw.deger / 3_600_000
        mah += ta.deger / 3_600
    return {"veri": veri.hex(), "oturum": ot, "satirlar": rows, "w": [jf(x) for x in wler],
            "enerji": {"wh": jf(wh), "mah": jf(mah)}, **yakalama_vektoru(o, veri)}


def vektorler() -> dict:
    r = Rng(0x2F0C5A)
    v1, o1 = olcum_akisi(r, saatsiz=False)
    v2, o2 = olcum_akisi(r, saatsiz=True)
    vp, op = pil_akisi(r)
    va, oa = ayrinti_akisi(r)
    return {
        "aciklama": "uretim/ortak_vektor_disari.py uretti (Python kopru/kayit_bicim.py); ELLE DUZENLEME",
        "sayi": sayi_vektorleri(),
        "olcum": [olcum_vektoru("unixli_sarmali_devamli", v1, o1), olcum_vektoru("saatsiz_saat_kaydi", v2, o2)],
        "pil": [pil_vektoru(vp, op)],
        "ayrinti": [ayrinti_vektoru(va, oa)],
    }


def tek(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def metin(v: dict) -> str:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--denetle", action="store_true",
                    help="dosyayi yazma; depodakiyle karsilastir, farkliysa 1 don")
    a = ap.parse_args()
    v = vektorler()
    m = metin(v)
    sayi = sum(len(x) for x in v.values() if isinstance(x, list))
    yol = HEDEF.relative_to(KOK).as_posix()
    if a.denetle:
        if not HEDEF.exists():
            print(f"YOK: {yol} - once 'python ortak_vektor_disari.py'")
            return 1
        if HEDEF.read_bytes().decode("ascii", "replace") == m:
            print(f"OK: {yol} Python basvurusuyla ayni ({sayi} vektor)")
            return 0
        print(f"FARKLI: {yol} Python'la uyusmuyor - bilerek degistiyse yeniden uret")
        return 1
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_bytes(m.encode("ascii"))
    print(f"yazildi: {yol} ({sayi} vektor, {len(m)} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
