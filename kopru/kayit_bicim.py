# -*- coding: utf-8 -*-
"""B71 — KAYIT BICIMI (surum 1): kartin flasa yazdigi baytlarin Python cozucusu.

TEK TANIM `kod/olcum-karti-a3/kayit_bicim.h`; bu dosya ona UYAR. Iki taraf
`uretim/test_kayit.py`'de ORTAK test vektorleriyle sinaniyor: C'nin
urettigi baytlar burada cozulup yeniden paketleniyor; biri degisip oteki
degismezse zincir kirmizi.

Telefon/PC karttan gelen baytlari AYNEN saklar (tasarim §5); bu modul o
baytlari okur. Yalniz standart kutuphane (kopru kurali).

Birimler: kayitta V ve A icin HAM ADC KODU var; volt/amper `volt()` /
`amper()` ile kaydin KENDI kalibrasyon kopyasindan hesaplanir (tasarim §7).
Guc (W) kayit anindaki kalibrasyonla watt olarak saklanir.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

SURUM = 2              # 1B: BASLA'da kal_no; surum 1 (98 B) okunur
IMZA = 0xA5
BASLIK_BAYT = 16
NOKTA_BAYT = 36
BASLA_BAYT = 102
BASLA_V1_BAYT = 98
KAL_BAYT = 62          # kalibrasyon kopyasi (BASLA 36..97 ve kalibrasyon gecmisi)

T_BASLA, T_NOKTA, T_DEVAM, T_BITIR, T_SAAT, T_TEKRAR = 1, 2, 3, 4, 5, 6
T_OLAY, T_NOT = 7, 8   # 1C-1
T_AYRINTI = 9          # 1C-2: her ornek (hiz_ms 0)
T_SKOP = 10            # 1C-3: osiloskop yakalamasi, parca parca (0. parca META)
# AYRINTI kayit bayraklari. KA_SILME: kaydin ILK ornegi kirli sektor silmesinden
# (~25 ms, iki cekirdek durur) SONRA uretildi — ilk ornegin onundeki bosluk silmedir.
KA_KAYIP_ONCE, KA_SILME = 0x01, 0x02
KAO_YUKSEK, KAO_V_HATA, KAO_I_HATA, KAO_V_DOYDU = 0x1, 0x2, 0x4, 0x8   # ornek bayraklari
KN_YUKSEK, KN_V_HATA, KN_I_HATA = 0x01, 0x02, 0x04
KN_V_DOYDU, KN_DURAKLAMA, KN_KAYIP_ONCE = 0x08, 0x10, 0x20
KN_DCIR = 0x40         # 1C-1: en az bir ornek DCIR darbesinde (yuk KAPALI)
SEBEP = {1: "kullanici", 2: "bellek doldu", 3: "hata", 4: "pil testi bitti",
         5: "kart yeniden basladi", 6: "baska oturum basladi", 7: "planli sure doldu"}
OTURUM_OLCUM = 1
OTURUM_PIL = 2         # 1C-1: yeniden baslamada SURMEZ
OTURUM_SKOP = 3        # 1C-3: osiloskop gunlugu; hiz_ms = aralik (0 = her tetik); SURMEZ
KO_PIL_AYAR, KO_DCIR, KO_PIL_SONUC = 1, 2, 3
KO_SKOP_KAL = 4        # 1C-3: skop ADC'nin eFuse egrisi, 17 x i16 mV
KO_PLAN = 5            # 1C-4: zamanlanmis kayit (bas_unix, sure_s, hiz_ms, plan_no)
KNT_AD, KNT_ETIKET, KNT_NOT = 1, 2, 3
NOT_METIN = 120
KAL_BICIM = 1
ADS_SAYIM = 32768.0

_BASLIK = struct.Struct("<BBHII")        # imza, tur, yuk_bayt, sira, oturum
_NOKTA = struct.Struct("<IHBxfhhfhhfff")
_KANAL = struct.Struct("<fffhf")
_AKIM = struct.Struct("<hffffff")
_BASLA_BAS = struct.Struct("<BBHIIII16s")
_DEVAM = struct.Struct("<IIII")
_BITIR = struct.Struct("<IB3x")
_SAAT = struct.Struct("<III")
_OLAY_BAS = struct.Struct("<B3xI")                 # olay_tur, kart_ms
_OLAY = {                                          # tur -> (yapi, alan adlari)
    KO_PIL_AYAR: (struct.Struct("<ffIIIf"),
                  ("kesme_v", "ocv", "azami_s", "dcir_aralik_ms", "dcir_ms", "kayit_hz")),
    KO_DCIR: (struct.Struct("<Iffffffff"),
              ("no", "v_once", "i_once", "v_ani", "v_oturmus", "r_ani", "r_oturmus",
               "mah", "wh")),
    KO_PIL_SONUC: (struct.Struct("<BBxxffffII"),
                   ("durum", "hata", "mah", "wh", "ocv", "v_son", "sure_ms", "dcir_sayisi")),
    KO_SKOP_KAL: (struct.Struct("<17h"), ("mv",)),   # tek alan: 17 elemanli liste
    KO_PLAN: (struct.Struct("<IIII"), ("bas_unix", "sure_s", "hiz_ms", "plan_no")),
}
_NOT_BAS = struct.Struct("<IB3xII")                # hedef, alan, nokta_ms, degistirir
_AYRINTI_BAS = struct.Struct("<IIIHBx")            # ilk, t0_ms, t0_us, adet, bayrak
_AYRINTI_ORNEK = struct.Struct("<hhH")             # v, i, (dt4 << 4 | bayrak)
_SKOP_BAS = struct.Struct("<IHHHBx")               # no, ilk, adet, toplam, parca
_SKOP_META = struct.Struct("<IIIIffHHH5Bx")
_SKOP_META_AD = ("t_ms", "sure_ms", "hz", "tdiv_us", "adim", "ofset", "tetik", "esik",
                 "histerezis", "kip", "tetiklendi", "kenar", "on_yuzde", "onay")
assert _NOKTA.size == NOKTA_BAYT
assert [_OLAY_BAS.size + y.size for y, _ in _OLAY.values()] == [32, 44, 36, 42, 24]
assert _SKOP_BAS.size == 12 and _SKOP_META.size == 36
assert _NOT_BAS.size == 16
assert _AYRINTI_BAS.size == 16 and _AYRINTI_ORNEK.size == 6
assert 2 * _KANAL.size + _AKIM.size == KAL_BAYT
assert _BASLA_BAS.size + KAL_BAYT == BASLA_V1_BAYT and BASLA_V1_BAYT + 4 == BASLA_BAYT


def toplam_bayt(yuk_bayt: int) -> int:
    """Kaydin flasta kapladigi bayt: baslik + yuk, 4'un katina."""
    return (BASLIK_BAYT + yuk_bayt + 3) & ~3


def crc(veri: bytes, onceki: int = 0) -> int:
    return zlib.crc32(veri, onceki) & 0xFFFFFFFF


# ── kayit ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Kayit:
    tur: int
    sira: int
    oturum: int
    yuk: bytes
    adres: int | None = None      # flas goruntusundeki yeri (flas_coz)


def kayit_paketle(tur: int, sira: int, oturum: int, yuk: bytes) -> bytes:
    bas = _BASLIK.pack(IMZA, tur, len(yuk), sira, oturum)
    c = crc(yuk, crc(bas))
    ham = bas + struct.pack("<I", c) + yuk
    return ham + b"\x00" * (toplam_bayt(len(yuk)) - len(ham))


def _kayit_oku(veri: bytes, a: int, son: int) -> tuple[int, Kayit | None]:
    """(durum, kayit): 1 gecerli, 0 bos (0xFF), -1 cop ya da yarim."""
    if a + BASLIK_BAYT > son:
        return 0, None
    b = bytes(veri[a:a + BASLIK_BAYT])
    if b == b"\xff" * BASLIK_BAYT:
        return 0, None
    imza, tur, n, sira, oturum, c = struct.unpack("<BBHIII", b)
    # bilinmeyen tur GECERLI (C ile ayni): ileride eklenen turler esitlemeyi kirmasin
    if imza != IMZA or tur in (0, 0xFF) or sira in (0, 0xFFFFFFFF):
        return -1, None
    if a + toplam_bayt(n) > son:
        return -1, None
    yuk = bytes(veri[a + BASLIK_BAYT:a + BASLIK_BAYT + n])
    if crc(yuk, crc(b[:12])) != c:
        return -1, None
    return 1, Kayit(tur, sira, oturum, yuk, a)


def akis_onek(veri: bytes) -> tuple[list[Kayit], int]:
    """Akisin GECERLI on eki: ilk gecersiz/yarim kayitta durur. Donus:
    (kayitlar, gecerli bayt). B72: esitleme istemcisinin cokme sonrasi ileri
    sarmasi (fsync'lenmis ama durum dosyasina gecmemis kayitlar korunur)."""
    kayitlar, a = [], 0
    while a < len(veri):
        d, k = _kayit_oku(veri, a, len(veri))
        if d != 1:
            break
        kayitlar.append(k)
        a += toplam_bayt(len(k.yuk))
    return kayitlar, a


def akis_coz(veri: bytes) -> list[Kayit]:
    """Esitleme yaniti: art arda kayitlar. Tek bozuk kayit -> ValueError."""
    kayitlar, a = [], 0
    while a < len(veri):
        d, k = _kayit_oku(veri, a, len(veri))
        if d != 1:
            raise ValueError(f"{a}. baytta gecersiz kayit")
        kayitlar.append(k)
        a += toplam_bayt(len(k.yuk))
    return kayitlar


def flas_coz(veri: bytes, sektor: int) -> tuple[list[Kayit], int]:
    """Flas goruntusu. Her sektor bastan; ilk gecersiz kayitta o sektor
    biter (kg_ac ile ayni kural). Donus: (sira ile sirali kayitlar,
    cop/yarim gorulen sektor sayisi).
    S6: goruntu tam sektor olmak zorunda DEGIL (yarim dokum). Son sektor
    goruntunun sonunda biter: < 16 B kalan kuyruk (yarim baslik) sektor
    sonundaki < 16 B gibi BOS sayilir (bozuk degil); basligi tam ama yuku
    goruntuden tasan kayit yarim kayittir (bozuk +1). Cokmez."""
    kayitlar, bozuk = [], 0
    for s in range(0, len(veri), sektor):
        a, son_sira = s, 0
        son = min(s + sektor, len(veri))
        while True:
            d, k = _kayit_oku(veri, a, son)
            if d == 1 and k.sira <= son_sira:
                d = -1
            if d != 1:
                bozuk += 1 if d < 0 else 0
                break
            kayitlar.append(k)
            son_sira = k.sira
            a += toplam_bayt(len(k.yuk))
    kayitlar.sort(key=lambda x: x.sira)
    return kayitlar, bozuk


# ── nokta ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Nokta:
    kart_ms: int
    n: int
    bayrak: int
    v_ort_kod: float
    v_min_kod: int
    v_maks_kod: int
    i_ort_kod: float
    i_min_kod: int
    i_maks_kod: int
    w_ort: float
    w_min: float
    w_maks: float


def nokta_paketle(p: Nokta) -> bytes:
    return _NOKTA.pack(p.kart_ms, p.n, p.bayrak, p.v_ort_kod, p.v_min_kod,
                       p.v_maks_kod, p.i_ort_kod, p.i_min_kod, p.i_maks_kod,
                       p.w_ort, p.w_min, p.w_maks)


def nokta_coz(b: bytes) -> Nokta:
    return Nokta(*_NOKTA.unpack(b))


# ── BASLA ve kalibrasyon ──────────────────────────────────────────────
@dataclass(frozen=True)
class Kanal:
    n: float
    pga: float
    kazanc: float
    sifir_ham: int
    tau: float


@dataclass(frozen=True)
class Kalibrasyon:
    normal: Kanal
    yuksek: Kanal
    i_ofset: int
    i_pga: float
    sont_ohm: float
    i_duzeltme: float
    sebeke_hz: float
    faz_kal_us: tuple[float, float]


@dataclass(frozen=True)
class Basla:
    oturum_turu: int
    kal_bicim: int
    hiz_ms: int
    unix_s: int
    kart_ms: int
    acilis: int
    surum: str
    kal: Kalibrasyon
    bicim_surum: int = SURUM       # cozulen kayitta: yazildigi bicim
    kal_no: int = 0                # 1B: kalibrasyon gecmisindeki numara (0 = bilinmiyor)


def _kanal_paketle(k: Kanal) -> bytes:
    return _KANAL.pack(k.n, k.pga, k.kazanc, k.sifir_ham, k.tau)


def kal_paketle(k: Kalibrasyon) -> bytes:
    """Kalibrasyon kopyasi (62 B) — C'deki kayit_kal_paketle ile ayni."""
    return (_kanal_paketle(k.normal) + _kanal_paketle(k.yuksek)
            + _AKIM.pack(k.i_ofset, k.i_pga, k.sont_ohm, k.i_duzeltme,
                         k.sebeke_hz, *k.faz_kal_us))


def kal_coz(y: bytes, a: int = 0) -> Kalibrasyon:
    normal = Kanal(*_KANAL.unpack_from(y, a))
    yuksek = Kanal(*_KANAL.unpack_from(y, a + _KANAL.size))
    io, ip, so, idz, sh, f0, f1 = _AKIM.unpack_from(y, a + 2 * _KANAL.size)
    return Kalibrasyon(normal, yuksek, io, ip, so, idz, sh, (f0, f1))


def basla_paketle(b: Basla) -> bytes:
    return (_BASLA_BAS.pack(b.oturum_turu, b.kal_bicim, SURUM, b.hiz_ms,
                            b.unix_s, b.kart_ms, b.acilis,
                            b.surum.encode("ascii")[:16].ljust(16, b"\0"))
            + kal_paketle(b.kal) + struct.pack("<I", b.kal_no))


def basla_coz(y: bytes) -> Basla:
    """Surum 2 (102 B) ya da surum 1 (98 B; kal_no yok -> 0)."""
    tur, kb, bs, hiz, unix, kms, acilis, surum = _BASLA_BAS.unpack_from(y, 0)
    kal_no = struct.unpack_from("<I", y, BASLA_V1_BAYT)[0] if len(y) >= BASLA_BAYT else 0
    return Basla(tur, kb, hiz, unix, kms, acilis,
                 surum.split(b"\0", 1)[0].decode("ascii", "replace"),   # C dizgisi: ilk NUL
                 kal_coz(y, _BASLA_BAS.size), bs, kal_no)


# S5: DEVAM/BITIR/SAAT yuku bilinen boydan UZUNSA on ek cozulur (yeni firmware alan
# ekleyebilir — ileri uyumluluk); KISAYSA struct.error (oturumlari_kur onu atlar + uyarir).
def devam_coz(y: bytes) -> dict:
    a, u, k, n = _DEVAM.unpack_from(y)
    return {"acilis": a, "unix_s": u, "kart_ms": k, "nokta_sira": n}


def bitir_coz(y: bytes) -> dict:
    n, s = _BITIR.unpack_from(y)
    return {"nokta_adedi": n, "sebep": s}


def saat_coz(y: bytes) -> dict:
    u, k, a = _SAAT.unpack_from(y)
    return {"unix_s": u, "kart_ms": k, "acilis": a}


def olay_paketle(d: dict) -> bytes:
    """OLAY yuku (kayit_bicim.h kayit_olay_*_paketle ile ayni)."""
    yapi, adlar = _OLAY[d["tur"]]
    if adlar == ("mv",):                               # liste alanli olay (KO_SKOP_KAL)
        return _OLAY_BAS.pack(d["tur"], d["kart_ms"]) + yapi.pack(*d["mv"])
    return _OLAY_BAS.pack(d["tur"], d["kart_ms"]) + yapi.pack(*(d[a] for a in adlar))


def olay_coz(y: bytes) -> dict:
    """OLAY yuku -> {"tur", "kart_ms", ...alanlar}. Bilinmeyen olay turu
    atilmaz: {"tur", "kart_ms", "ham"} (1C-2… yeni olaylar ekleyecek)."""
    t, ms = _OLAY_BAS.unpack_from(y)
    d = {"tur": t, "kart_ms": ms}
    if t in _OLAY and len(y) >= _OLAY_BAS.size + _OLAY[t][0].size:
        yapi, adlar = _OLAY[t]
        if adlar == ("mv",):
            d["mv"] = list(yapi.unpack_from(y, _OLAY_BAS.size))
        else:
            d.update(zip(adlar, yapi.unpack_from(y, _OLAY_BAS.size)))
    else:
        d["ham"] = bytes(y[_OLAY_BAS.size:])
    return d


def not_paketle(hedef: int, alan: int, nokta_ms: int, degistirir: int,
                metin: bytes) -> bytes:
    """NOT yuku. `metin` kartin TEMIZLEDIGI bayt dizisi (Python temizlemez)."""
    return _NOT_BAS.pack(hedef, alan, nokta_ms, degistirir) + bytes(metin)


def ayrinti_paketle(d: dict) -> bytes:
    """AYRINTI yuku (kayit_bicim.h ile ayni). ornekler: [(v, i, dt4, bayrak)]."""
    return (_AYRINTI_BAS.pack(d["ilk"], d["t0_ms"], d["t0_us"], len(d["ornekler"]), d["bayrak"])
            + b"".join(_AYRINTI_ORNEK.pack(v, i, (dt4 << 4) | (b & 0xF))
                       for v, i, dt4, b in d["ornekler"]))


def ayrinti_coz(y: bytes) -> dict:
    ilk, ms, us, adet, bayrak = _AYRINTI_BAS.unpack_from(y)
    adet = min(adet, (len(y) - _AYRINTI_BAS.size) // _AYRINTI_ORNEK.size)
    orn = []
    for k in range(adet):
        v, i, w = _AYRINTI_ORNEK.unpack_from(y, _AYRINTI_BAS.size + k * _AYRINTI_ORNEK.size)
        orn.append((v, i, w >> 4, w & 0xF))
    return {"ilk": ilk, "t0_ms": ms, "t0_us": us, "bayrak": bayrak, "ornekler": orn}


def skop_paketle(d: dict) -> bytes:
    """SKOP parcasi (kayit_bicim.h kayit_skop_*_paketle ile ayni). 0. parca META'li."""
    b = _SKOP_BAS.pack(d["no"], d["ilk"], len(d["kodlar"]), d["toplam"], d["parca"])
    if d["parca"] == 0:
        b += _SKOP_META.pack(*(d["meta"][a] for a in _SKOP_META_AD))
    return b + struct.pack(f"<{len(d['kodlar'])}H", *d["kodlar"])


def skop_coz(y: bytes) -> dict:
    no, ilk, adet, toplam, parca = _SKOP_BAS.unpack_from(y)
    a, meta = _SKOP_BAS.size, None
    if parca == 0 and len(y) >= a + _SKOP_META.size:
        meta = dict(zip(_SKOP_META_AD, _SKOP_META.unpack_from(y, a)))
        a += _SKOP_META.size
    adet = min(adet, (len(y) - a) // 2)
    return {"no": no, "ilk": ilk, "adet": adet, "toplam": toplam, "parca": parca,
            "meta": meta, "kodlar": list(struct.unpack_from(f"<{adet}H", y, a))}


def _skop_birlestir(o) -> None:
    """Yakalamalarin parcalarini birlestir. Eksik parca DOLDURULMAZ: tam=False,
    kodlar None."""
    for y in o.skoplar.values():
        y.pop("_sonraki", None)
        p = y.pop("_parca")
        kodlar, beklenen = [], 0
        for ilk in sorted(p):
            if ilk != beklenen:
                break
            kodlar += p[ilk]
            beklenen = ilk + len(p[ilk])
        y["tam"] = y["meta"] is not None and beklenen == y["toplam"] and len(kodlar) == y["toplam"]
        y["kodlar"] = kodlar if y["tam"] else None


def skop_ikili(y: dict) -> bytes | None:
    """Tam yakalamayi bugunku `/skop.bin` bicimine cevir (32 B S3B baslik + u16).
    Tek kodlama: kopru/arsiv.py skop_ikili'yi kullanir. Eksik yakalama: None."""
    if not y.get("tam"):
        return None
    from arsiv import skop_ikili as ikili
    m = y["meta"]
    return ikili({"ornek": y["kodlar"], "hz": m["hz"], "adim": m["adim"], "ofset": m["ofset"],
                  "tdiv_us": m["tdiv_us"], "tetik_idx": m["tetik"], "kip": m["kip"],
                  "tetiklendi": m["tetiklendi"], "sira": y["no"]})


def ayrinti_ornekler(o) -> list[tuple[int, int, int, int, int, int]]:
    """Oturumun ayrintili ornekleri: (sira, us, v_kod, i_kod, bayrak, acilis).
    us = t0_us + 4 x (dt4 toplami), KARTIN O ACILISINDAKI micros()'u; 32 bit
    sarmasi t0_ms'den cozulur (ikisi ayni zamanlayicidan). `acilis`: 0 = BASLA'nin
    acilisi, n = n. DEVAM'dan sonrasi. Kart yeniden baslayinca micros/millis
    SIFIRLANIR: farkli acilislarin zamanlari birbirine gore anlamsizdir, tek
    zaman ekseninde birlestirmek icin DEVAM/BASLA kart_ms/unix_s kullanilmali.
    Y5: ayni sirali ornek iki kayitta olabilir (kart yazdigi kaydi HATA diye
    donup tamponu yeniden yazar) — her sira BIR kez, ilk kopyasiyla."""
    devam = sorted(d["nokta_sira"] for d in o.devamlar)
    cikti, gorulen = [], set()
    for r in sorted(o.ayrinti, key=lambda x: x["sira"]):
        k = round((r["t0_ms"] * 1000 - r["t0_us"]) / 2**32)
        t = r["t0_us"] + k * 2**32
        ac = sum(1 for d in devam if d <= r["ilk"])
        for j, (v, i, dt4, b) in enumerate(r["ornekler"]):
            t += 4 * dt4
            if r["ilk"] + j in gorulen:
                continue
            gorulen.add(r["ilk"] + j)
            cikti.append((r["ilk"] + j, t, v, i, b, ac))
    return cikti


def not_coz(y: bytes) -> dict:
    h, a, ms, dg = _NOT_BAS.unpack_from(y)
    return {"hedef": h, "alan": a, "nokta_ms": ms, "degistirir": dg,
            "metin": bytes(y[_NOT_BAS.size:]).decode("utf-8", errors="replace")}


# ── birimler ─────────────────────────────────────────────────────────
def _kirp(d: int) -> int:
    return max(-32768, min(32767, d))


def volt(kod: float, k: Kanal) -> float:
    """olc_gerilim3 (olcum3.h) ile ayni formul, float64. Tam sayi kodda
    firmware'in int16 kirpmasi da uygulanir."""
    d = kod - k.sifir_ham
    if isinstance(kod, int):
        d = _kirp(d)
    return d * (k.pga / ADS_SAYIM) * k.n * k.kazanc


def amper(kod: float, kal: Kalibrasyon) -> float:
    """olc_akim3 (olcum3.h) ile ayni formul, float64.
    S6: sont_ohm 0 (ya da -0; bozuk/eksik kalibrasyon) -> NaN: akim BILINMIYOR.
    ZeroDivisionError YOK (tek bozuk kalibrasyon butun disari aktarimi dusurmesin)."""
    if kal.sont_ohm == 0:
        return float("nan")
    d = kod - kal.i_ofset
    if isinstance(kod, int):
        d = _kirp(d)
    return d * (kal.i_pga / ADS_SAYIM) / kal.sont_ohm * kal.i_duzeltme


def unix_zaman(s: int) -> datetime | None:
    """0 = kartin saati bilinmiyordu. 1970 tarihi URETILMEZ."""
    return None if not s else datetime.fromtimestamp(s, timezone.utc)


# ── oturumlar ────────────────────────────────────────────────────────
@dataclass
class Oturum:
    id: int
    basla: Basla | None = None
    basi_eksik: bool = True          # BASLA temizlikte gitti, TEKRAR'dan bilgi
    tekrar_adet: int = 0
    noktalar: list[tuple[int, Nokta]] = field(default_factory=list)
    devamlar: list[dict] = field(default_factory=list)
    saatler: list[dict] = field(default_factory=list)
    bitir: dict | None = None
    olaylar: list[dict] = field(default_factory=list)     # 1C-1: olay_coz + "sira"
    ad: str | None = None                                 # 1C-1: en son NOT(ad)
    etiketler: list[str] = field(default_factory=list)    # en son NOT(etiket), virgulden
    notlar: dict[int, dict] = field(default_factory=dict)  # NOT kaydinin sirasi -> not
    ayrinti: list[dict] = field(default_factory=list)     # 1C-2: ayrinti_coz + "sira"
    skoplar: dict[int, dict] = field(default_factory=dict)  # 1C-3: 0. parcanin (ya da yetim
                                                            # parcanin) SIRASI -> {no, meta,
                                                            # toplam, kodlar, tam, t_sira}


def _not_uygula(o: Oturum, k: Kayit) -> None:
    """NOT kaydini oturumun son haline isle (kayit_bicim.h NOT aciklamasi)."""
    n = not_coz(k.yuk)
    if n["alan"] == KNT_AD:
        o.ad = n["metin"]
    elif n["alan"] == KNT_ETIKET:
        o.etiketler = [e.strip() for e in n["metin"].split(",") if e.strip()]
    elif n["alan"] == KNT_NOT:
        dg = n["degistirir"]
        if dg:
            # ASIL notun sirasi (kayit_bicim.h); bilinmeyen/silinmis ya da bir
            # duzeltme kaydinin sirasi YOK SAYILIR — hayalet not uretmez
            if dg in o.notlar:
                if n["metin"]:
                    o.notlar[dg] = {"nokta_ms": n["nokta_ms"] or o.notlar[dg]["nokta_ms"],
                                    "metin": n["metin"]}    # nokta_ms 0: yer KORUNUR
                else:
                    del o.notlar[dg]
        elif n["metin"]:
            o.notlar[k.sira] = {"nokta_ms": n["nokta_ms"], "metin": n["metin"]}


# S5: bilinen kayit turunun EN KISA gecerli yuku (bayt). Daha uzun yuk: bilinen on ek
# cozulur (BASLA 98..101 = surum 1, >= 102 = surum 2 + fazlasi; NOKTA'da yarim nokta,
# AYRINTI/SKOP'ta adet'i asan kuyruk, OLAY'da govdeyi asan bayt yok sayilir). Daha kisa:
# kayit ATLANIR, oturum ACMAZ, Oturumlar.uyarilar'a girer. Tabloda olmayan (bilinmeyen)
# tur sessizce yok sayilir ve o da oturum ACMAZ (S6).
_EN_AZ = {T_BASLA: BASLA_V1_BAYT, T_TEKRAR: BASLA_V1_BAYT, T_NOKTA: 4,
          T_DEVAM: _DEVAM.size, T_BITIR: _BITIR.size, T_SAAT: _SAAT.size,
          T_OLAY: _OLAY_BAS.size, T_NOT: _NOT_BAS.size,
          T_AYRINTI: _AYRINTI_BAS.size, T_SKOP: _SKOP_BAS.size}
assert list(_EN_AZ.values()) == [98, 98, 4, 16, 8, 12, 8, 16, 16, 12]


class Oturumlar(dict):
    """oturumlari_kur donusu: {oturum id: Oturum}, oturumun ilk VERI kaydinin
    sirasiyla. `uyarilar`: yuku turunun en kisa boyundan (`_EN_AZ`) KISA oldugu icin
    ATLANAN kayitlar, kayit sirasiyla: {"sira", "tur", "oturum" (baslik), "bayt"
    (yuk boyu), "en_az"}. Bos liste = hepsi cozuldu. JS: Map + sayilamaz `uyarilar`."""

    def __init__(self):
        super().__init__()
        self.uyarilar: list[dict] = []


def oturumlari_kur(kayitlar: list[Kayit]) -> Oturumlar:
    """Kayitlardan oturumlar. CRC'si gecerli her kayitta COKMEZ (S5): boyu yanlis
    kayit atlanir + uyari (`Oturumlar.uyarilar`), uzun kayidin on eki cozulur."""
    ot = Oturumlar()
    # 1C-3: yakalama KAYIT SIRASIYLA kurulur. `no` bir oturumda tekrarlanabilir
    # (Gtd + yeniden Gt, DEVAM'dan sonra Gt): 0. parca yeni yakalama acar; sonraki
    # parca yalniz HEMEN onceki acik yakalamaya (ayni no/toplam, ilk kesintisiz)
    # eklenir — ky_skop parcalari art arda yazar, arada yalniz TEKRAR olabilir.
    acik: dict[int, dict] = {}
    nokta_gorulen: dict[int, set] = {}
    for k in sorted(kayitlar, key=lambda x: x.sira):
        if k.oturum and k.tur not in (T_SKOP, T_TEKRAR):
            acik.pop(k.oturum, None)
        en_az = _EN_AZ.get(k.tur)
        if en_az is None:
            continue                    # bilinmeyen tur: yok sayilir, oturum ACMAZ (S6)
        if len(k.yuk) < en_az:          # S5: kisa kayit cozulemez — atla, oturum ACMA, uyar
            ot.uyarilar.append({"sira": k.sira, "tur": k.tur, "oturum": k.oturum,
                                "bayt": len(k.yuk), "en_az": en_az})
            continue
        if k.tur == T_NOT and len(k.yuk) >= _NOT_BAS.size:
            h = struct.unpack_from("<I", k.yuk)[0]     # baslikta oturum 0; hedef yukte
            if h:
                _not_uygula(ot.setdefault(h, Oturum(h)), k)
            continue
        if not k.oturum:
            continue
        o = ot.setdefault(k.oturum, Oturum(k.oturum))
        if k.tur == T_OLAY and len(k.yuk) >= _OLAY_BAS.size:
            o.olaylar.append({**olay_coz(k.yuk), "sira": k.sira})
            continue
        if k.tur == T_AYRINTI and len(k.yuk) >= _AYRINTI_BAS.size:
            o.ayrinti.append({**ayrinti_coz(k.yuk), "sira": k.sira})
            continue
        if k.tur == T_SKOP and len(k.yuk) >= _SKOP_BAS.size:
            p = skop_coz(k.yuk)
            y = acik.get(k.oturum)
            if (p["parca"] == 0 or y is None or y["no"] != p["no"]
                    or y["toplam"] != p["toplam"] or p["ilk"] != y["_sonraki"]):
                y = {"no": p["no"], "meta": None, "toplam": p["toplam"], "t_sira": k.sira,
                     "_parca": {}, "_sonraki": 0}
                o.skoplar[k.sira] = y
                acik[k.oturum] = y
            if p["parca"] == 0:
                y["meta"] = p["meta"]
            y["_parca"].setdefault(p["ilk"], p["kodlar"])
            y["_sonraki"] = p["ilk"] + len(p["kodlar"])
            continue
        if k.tur == T_BASLA:
            o.basla = basla_coz(k.yuk)
            o.basi_eksik = False
        elif k.tur == T_TEKRAR:
            o.tekrar_adet += 1
            if o.basla is None:
                o.basla = basla_coz(k.yuk)
        elif k.tur == T_NOKTA:
            ilk = struct.unpack_from("<I", k.yuk)[0]
            gorulen = nokta_gorulen.setdefault(k.oturum, set())
            for j in range((len(k.yuk) - 4) // NOKTA_BAYT):
                if ilk + j in gorulen:      # Y5: yeniden deneme kopyasi — ilki kalir
                    continue
                gorulen.add(ilk + j)
                a = 4 + j * NOKTA_BAYT
                o.noktalar.append((ilk + j, nokta_coz(k.yuk[a:a + NOKTA_BAYT])))
        elif k.tur == T_DEVAM:
            o.devamlar.append(devam_coz(k.yuk))
        elif k.tur == T_BITIR:
            o.bitir = bitir_coz(k.yuk)
        elif k.tur == T_SAAT:
            o.saatler.append(saat_coz(k.yuk))
    for o in ot.values():
        _skop_birlestir(o)
    return ot
