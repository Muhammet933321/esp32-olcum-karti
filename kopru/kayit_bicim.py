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
KN_YUKSEK, KN_V_HATA, KN_I_HATA = 0x01, 0x02, 0x04
KN_V_DOYDU, KN_DURAKLAMA, KN_KAYIP_ONCE = 0x08, 0x10, 0x20
KN_DCIR = 0x40         # 1C-1: en az bir ornek DCIR darbesinde (yuk KAPALI)
SEBEP = {1: "kullanici", 2: "bellek doldu", 3: "hata", 4: "pil testi bitti",
         5: "kart yeniden basladi", 6: "baska oturum basladi"}
OTURUM_OLCUM = 1
OTURUM_PIL = 2         # 1C-1: yeniden baslamada SURMEZ
KO_PIL_AYAR, KO_DCIR, KO_PIL_SONUC = 1, 2, 3
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
}
_NOT_BAS = struct.Struct("<IB3xII")                # hedef, alan, nokta_ms, degistirir
assert _NOKTA.size == NOKTA_BAYT
assert [_OLAY_BAS.size + y.size for y, _ in _OLAY.values()] == [32, 44, 36]
assert _NOT_BAS.size == 16
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
    cop/yarim gorulen sektor sayisi)."""
    kayitlar, bozuk = [], 0
    for s in range(0, len(veri), sektor):
        a, son_sira = s, 0
        while True:
            d, k = _kayit_oku(veri, a, s + sektor)
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
                 surum.rstrip(b"\0").decode("ascii", "replace"),
                 kal_coz(y, _BASLA_BAS.size), bs, kal_no)


def devam_coz(y: bytes) -> dict:
    a, u, k, n = _DEVAM.unpack(y)
    return {"acilis": a, "unix_s": u, "kart_ms": k, "nokta_sira": n}


def bitir_coz(y: bytes) -> dict:
    n, s = _BITIR.unpack(y)
    return {"nokta_adedi": n, "sebep": s}


def saat_coz(y: bytes) -> dict:
    u, k, a = _SAAT.unpack(y)
    return {"unix_s": u, "kart_ms": k, "acilis": a}


def olay_paketle(d: dict) -> bytes:
    """OLAY yuku (kayit_bicim.h kayit_olay_*_paketle ile ayni)."""
    yapi, adlar = _OLAY[d["tur"]]
    return _OLAY_BAS.pack(d["tur"], d["kart_ms"]) + yapi.pack(*(d[a] for a in adlar))


def olay_coz(y: bytes) -> dict:
    """OLAY yuku -> {"tur", "kart_ms", ...alanlar}. Bilinmeyen olay turu
    atilmaz: {"tur", "kart_ms", "ham"} (1C-2… yeni olaylar ekleyecek)."""
    t, ms = _OLAY_BAS.unpack_from(y)
    d = {"tur": t, "kart_ms": ms}
    if t in _OLAY and len(y) >= _OLAY_BAS.size + _OLAY[t][0].size:
        yapi, adlar = _OLAY[t]
        d.update(zip(adlar, yapi.unpack_from(y, _OLAY_BAS.size)))
    else:
        d["ham"] = bytes(y[_OLAY_BAS.size:])
    return d


def not_paketle(hedef: int, alan: int, nokta_ms: int, degistirir: int,
                metin: bytes) -> bytes:
    """NOT yuku. `metin` kartin TEMIZLEDIGI bayt dizisi (Python temizlemez)."""
    return _NOT_BAS.pack(hedef, alan, nokta_ms, degistirir) + bytes(metin)


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
    """olc_akim3 (olcum3.h) ile ayni formul, float64."""
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


def oturumlari_kur(kayitlar: list[Kayit]) -> dict[int, Oturum]:
    ot: dict[int, Oturum] = {}
    for k in sorted(kayitlar, key=lambda x: x.sira):
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
        if k.tur == T_BASLA:
            o.basla = basla_coz(k.yuk)
            o.basi_eksik = False
        elif k.tur == T_TEKRAR:
            o.tekrar_adet += 1
            if o.basla is None:
                o.basla = basla_coz(k.yuk)
        elif k.tur == T_NOKTA:
            ilk = struct.unpack_from("<I", k.yuk)[0]
            for j in range((len(k.yuk) - 4) // NOKTA_BAYT):
                a = 4 + j * NOKTA_BAYT
                o.noktalar.append((ilk + j, nokta_coz(k.yuk[a:a + NOKTA_BAYT])))
        elif k.tur == T_DEVAM:
            o.devamlar.append(devam_coz(k.yuk))
        elif k.tur == T_BITIR:
            o.bitir = bitir_coz(k.yuk)
        elif k.tur == T_SAAT:
            o.saatler.append(saat_coz(k.yuk))
    return ot
