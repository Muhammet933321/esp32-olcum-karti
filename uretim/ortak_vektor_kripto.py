# -*- coding: utf-8 -*-
"""2B capraz vektorleri: ortak/test/vektor/kripto.json'u URETIR (sabit girdiler).

    python ortak_vektor_kripto.py             # JSON'u yeniden yazar
    python ortak_vektor_kripto.py --denetle   # yazmadan: dosya Python'la HALA ayni mi (0/1)

Tasarim: tasarim/2026-10-02-alt-proje-2-ortak.md (O3, dilim 2B). Baslangic Python kodu:
hashlib/hmac (SHA-256, HMAC, PBKDF2), kopru/chacha.py (ChaCha20-Poly1305), kopru/imza.py
(1D kanonik istek, imza, eslestirme), kopru/bildirim.py (1E zarf, bilgi_coz). JS tarafi
(ortak/src/kripto.js, imza.js, zarf.js) bu dosyadaki her degeri BAYT BAYT uretmeli:
ortak/test/{kripto,imza,zarf}.test.js.

Ag ve disk YOK: imza.py'nin HTTP istekleri sahte `urlopen` ile yakalanir (URL, yontem,
basliklar, govde) ve yanitlar sabittir; `Cihaz.kaydet` devre disi (DPAPI/dosya yazilmaz);
saat (`time.time`) ve rastgele (`secrets.token_bytes`) sabitlenir. Boylece Python'un GERCEK
`ac`, `akis_url`, `esles` akislari kosar ve JS ayni yanitlarla ayni istekleri uretmeli.

Bozuk girdi vektorlerinde Python'un gercekten reddettigi burada DOGRULANIR (assert); JS de
reddetmeli. Cikti belirlenimci: rastgele veri SHA-256 sayac kipiyle sabit etiketlerden.
"""
from __future__ import annotations

import contextlib
import email.message
import hashlib
import hmac
import io
import json
import sys
import types
import urllib.error
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
import bildirim as BL                                      # noqa: E402
import chacha as CC                                        # noqa: E402
import imza as IM                                          # noqa: E402

HEDEF = KOK / "ortak" / "test" / "vektor" / "kripto.json"


def _bayt(etiket: str, n: int) -> bytes:
    """Belirlenimci 'rastgele' bayt: SHA-256(etiket/sayac) zinciri."""
    c, i = b"", 0
    while len(c) < n:
        c += hashlib.sha256(f"{etiket}/{i}".encode("utf-8")).digest()
        i += 1
    return c[:n]


def _hata_adi(islev) -> str | None:
    """Islevi kostur; hata verirse sinif adini, vermezse None dondur."""
    try:
        islev()
    except Exception as h:                                 # noqa: BLE001 — sinif adi kaydediliyor
        return type(h).__name__
    return None


# ── SHA-256 / HMAC / PBKDF2 ──────────────────────────────────────────────
def sha_vektorleri() -> list:
    c = []
    for n in (0, 1, 3, 55, 56, 57, 63, 64, 65, 111, 112, 119, 120, 127, 128, 129, 1000, 4096):
        v = _bayt(f"sha/{n}", n)
        c.append({"n": n, "veri": v.hex(), "ozet": hashlib.sha256(v).hexdigest()})
    return c


def hmac_vektorleri() -> list:
    c = []
    mesajlar = (0, 1, 55, 64, 65, 200, 1000)
    for i, kn in enumerate((0, 1, 20, 31, 32, 63, 64, 65, 100, 131, 200)):
        mn = mesajlar[i % len(mesajlar)]
        k, m = _bayt(f"hmac/k/{kn}", kn), _bayt(f"hmac/m/{mn}/{kn}", mn)
        c.append({"anahtar": k.hex(), "veri": m.hex(),
                  "hmac": hmac.new(k, m, hashlib.sha256).hexdigest()})
    return c


PROJE_PAROLA = "Ölçüm-kartı1"                             # 12 karakter (PAROLA_EN_AZ), 15 bayt UTF-8
PROJE_TUZ = _bayt("pbkdf2/proje/tuz", 16)
PROJE_TUR = 20_000                                         # kartin varsayilan turu (GUV_TUR_VARSAYILAN)


def pbkdf2_vektorleri() -> list:
    assert len(PROJE_PAROLA) == 12
    durumlar = [
        ("proje", PROJE_PAROLA.encode("utf-8"), PROJE_TUZ, PROJE_TUR, 32),
        ("bos_parola", b"", _bayt("pbkdf2/t1", 16), 1, 32),
        ("bos_tuz", b"a", b"", 2, 32),
        ("parola_64", _bayt("pbkdf2/p64", 64), _bayt("pbkdf2/t64", 16), 5, 64),
        ("parola_65_ozetlenir", _bayt("pbkdf2/p65", 65), _bayt("pbkdf2/t65", 16), 3, 32),
        ("turkce_40", "şifre-ĞÜŞİÖÇ".encode("utf-8"), _bayt("pbkdf2/t40", 16), 7, 40),
        ("uzun_parola_33", b"x" * 200, _bayt("pbkdf2/t33", 20), 1000, 33),
        ("alt_sinir", b"dogru-parola-12", _bayt("pbkdf2/t10k", 16), 10_000, 32),
    ]
    c = []
    for ad, p, t, tur, n in durumlar:
        o = {"ad": ad, "parola_hex": p.hex(), "tuz": t.hex(), "tur": tur, "uzunluk": n,
             "dk": hashlib.pbkdf2_hmac("sha256", p, t, tur, n).hex()}
        try:
            o["parola"] = p.decode("utf-8")
        except UnicodeDecodeError:
            pass
        if n == 32 and "parola" in o:                       # imza.pbkdf2 de ayni sonucu vermeli
            assert IM.pbkdf2(o["parola"], t, tur).hex() == o["dk"]
        c.append(o)
    return c


# ── ChaCha20 / Poly1305 / AEAD ───────────────────────────────────────────
def chacha_vektorleri() -> dict:
    bloklar = []
    for sayac in (0, 1, 7, 0xFFFFFFFE, 0xFFFFFFFF):
        k, n = _bayt(f"cc/k/{sayac}", 32), _bayt(f"cc/n/{sayac}", 12)
        bloklar.append({"anahtar": k.hex(), "sayac": sayac, "nonce": n.hex(),
                        "blok": CC.blok(k, sayac, n).hex()})
    akislar = []
    for sayac, dn in ((0, 0), (0, 1), (1, 64), (5, 65), (1, 200), (0xFFFFFFFE, 128)):
        k, n = _bayt(f"ca/k/{dn}", 32), _bayt(f"ca/n/{dn}", 12)
        d = _bayt(f"ca/d/{dn}", dn)
        akislar.append({"anahtar": k.hex(), "sayac": sayac, "nonce": n.hex(), "duz": d.hex(),
                        "sifreli": CC.akis_sifrele(k, sayac, n, d).hex()})
    # 2^32 - 1'den sonra blok gerekirse Python reddeder (JS de)
    k, n = _bayt("ca/k/tasma", 32), _bayt("ca/n/tasma", 12)
    assert _hata_adi(lambda: CC.akis_sifrele(k, 0xFFFFFFFF, n, b"\x00" * 65)) == "ValueError"
    return {"blok": bloklar, "akis": akislar}


def poly_vektorleri() -> list:
    z = "00" * 16
    hx = bytes.fromhex
    # RFC 8439 Ek A.3 #1, #5-#11 (tasima kenarlari) + uc degerler; etiketler Python'dan
    r10 = "01000000000000000400000000000000"
    m10 = ("e33594d7505e43b900000000000000003394d7505e4379cd0100000000000000"
           "0000000000000000000000000000000001000000000000000000000000000000")
    sabit = [
        ("A3-1", z + z, "00" * 64),
        ("A3-5", "02" + "00" * 15 + z, "ff" * 16),
        ("A3-6", "02" + "00" * 15 + "ff" * 16, "02" + "00" * 15),
        ("A3-7", "01" + "00" * 15 + z, "ff" * 16 + "f0" + "ff" * 15 + "11" + "00" * 15),
        ("A3-8", "01" + "00" * 15 + z, "ff" * 16 + "fb" + "fe" * 15 + "01" * 16),
        ("A3-9", "02" + "00" * 15 + z, "fd" + "ff" * 15),
        ("A3-10", r10 + z, m10),
        ("A3-11", r10 + z, m10[:96]),
    ]
    for n in (0, 1, 15, 16, 17, 32, 64, 100):
        sabit.append((f"uc-ff-{n}", "ff" * 32, "ff" * n))
    c = [{"ad": ad, "anahtar": k, "mesaj": m, "etiket": CC.poly1305(hx(k), hx(m)).hex()}
         for ad, k, m in sabit]
    for n in (0, 1, 2, 15, 16, 17, 31, 33, 47, 48, 49, 63, 64, 65, 97, 128, 255, 1000):
        k, m = _bayt(f"poly/k/{n}", 32), _bayt(f"poly/m/{n}", n)
        c.append({"ad": f"rastgele-{n}", "anahtar": k.hex(), "mesaj": m.hex(),
                  "etiket": CC.poly1305(k, m).hex()})
    return c


def aead_vektorleri() -> list:
    c = []
    for dn, an in ((0, 0), (0, 12), (1, 1), (15, 12), (16, 16), (17, 17), (63, 0), (64, 13),
                   (65, 32), (128, 1), (300, 12), (300, 0), (1, 100), (1000, 7)):
        k, n = _bayt(f"aead/k/{dn}/{an}", 32), _bayt(f"aead/n/{dn}/{an}", 12)
        d, a = _bayt(f"aead/d/{dn}/{an}", dn), _bayt(f"aead/a/{dn}/{an}", an)
        s = CC.sifrele(k, n, d, a)
        assert CC.coz(k, n, s, a) == d
        c.append({"anahtar": k.hex(), "nonce": n.hex(), "aad": a.hex(), "duz": d.hex(),
                  "sifreli": s.hex()})
    return c


# ── 1D: imza ve eslestirme ───────────────────────────────────────────────
KIMLIK = "a1b2c3d4e5f60718"
ACILIS = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
YENI_ACILIS = "ffeeddccbbaa99887766554433221100"
NK = _bayt("esles/nk", 16)
NC = _bayt("esles/nc", 16)
SIMDI_S = 1759000000.5                                     # *1000 tam: 1759000000500 ms
TABAN = "http://olcum.local"


def imza_saf_vektorleri() -> dict:
    yuzde = ["", "abc", "AZaz09-._~", "a b", "a&b=c ğ", "100%", "ü", "🔋", "/?#[]@!$&'()*+,;=",
             "\x00\x1f\x7f", "ÇÖĞÜŞİıçöğüşi", "+", "%20"]
    ad = ["", "PC", "PC ğ", "a" * 24, "a" * 25, "ğ" * 12, "ğ" * 12 + "a", "a\nb", "a\x7f", "tab\t",
          "🔋" * 6, "🔋" * 6 + "x", " "]
    taban = ["olcum.local", "olcum.local/", "http://1.2.3.4/", "https://x//", "httpfoo", "192.168.4.1"]
    K = _bayt("imza/K", 32)
    durumlar = [
        ("GET", "/kayit/liste", [], ACILIS, 1, b""),
        ("GET", "/kayit/veri", [("sira", "12"), ("not", "a&b=c ğ")], ACILIS, 1759000000123, b""),
        ("POST", "/komut", [], ACILIS, 2, "Go1234".encode()),
        ("POST", "/cihaz/sil", [("n", "3")], ACILIS, 1759000000500, b""),
        ("GET", "/x", [("a", "1&b=2")], ACILIS, 3, b""),
        ("GET", "/x", [("a", "1"), ("b", "2")], ACILIS, 3, b""),
        ("GET", "/x", [("", "")], ACILIS, 4, b""),
        ("GET", "/x", [("ü 🔋", "~-._ /?#")], ACILIS, 5, b""),
        ("POST", "/saat", [("unix", "1759000000")], ACILIS, 6, b"\x00\xff\x80"),
        ("GET", "/kayit/liste", [], ACILIS, 18446744073709551615, b""),
        ("GET", "/kayit/liste", [], ACILIS, 0, b""),
        ("GET", "/kayit/liste", [], "", 7, b""),
        ("POST", "/komut", [], YENI_ACILIS, 8, _bayt("imza/govde", 1000)),
        ("GET", "/kayıt", [], ACILIS, 9, b""),
        ("GET", "/akis", [], ACILIS, 10, b""),
    ]
    kanonik = []
    for y, yol, args, ac, s, gv in durumlar:
        kanonik.append({"yontem": y, "yol": yol, "argumanlar": [list(a) for a in args],
                        "acilis": ac, "sayac": str(s), "govde": gv.hex(),
                        "kanonik": IM.kanonik(y, yol, args, ac, s, gv).hex(),
                        "imza": IM.imzala(K, y, yol, args, ac, s, gv)})
    # a="1&b=2" ile a=1&b=2 AYNI metni vermemeli (yuzde kodlama sebebi)
    assert kanonik[4]["imza"] != kanonik[5]["imza"]
    for s in ("\ud800",):
        assert _hata_adi(lambda: IM.yuzde_kodla(s)) == "UnicodeEncodeError"
    return {
        "yuzde": [{"metin": m, "kodlu": IM.yuzde_kodla(m)} for m in yuzde],
        "ad_gecerli": [{"ad": a, "gecerli": IM.ad_gecerli(a)} for a in ad],
        "taban_url": [{"host": h, "taban": IM.taban_url(h)} for h in taban],
        "K": K.hex(),
        "kanonik": kanonik,
    }


def esles_hesap_vektorleri() -> dict:
    P = IM.pbkdf2(PROJE_PAROLA, PROJE_TUZ, PROJE_TUR)
    adlar = ["PC", "PC ğ", "Telefon 🔋", "a" * 24]
    return {
        "parola": PROJE_PAROLA, "tuz": PROJE_TUZ.hex(), "tur": PROJE_TUR, "P": P.hex(),
        "kimlik": KIMLIK, "nk": NK.hex(), "nc": NC.hex(),
        "kanit_istemci": [{"ad": a, "kanit": IM.kanit_istemci(P, KIMLIK, NK, NC, a).hex()} for a in adlar],
        "kart": [{"n": n, "kanit_kart": IM.kanit_kart(P, KIMLIK, NK, NC, n).hex(),
                  "K": IM.cihaz_anahtari(P, KIMLIK, NK, NC, n).hex()} for n in (1, 3, 8, 10)],
    }


class _Yanit:
    def __init__(self, durum: int, govde: bytes):
        self.status, self._g = durum, govde

    def read(self) -> bytes:
        return self._g

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _SahteAg:
    """urllib.request.urlopen yerine: istegi kaydeder, sirali sabit yaniti verir."""

    def __init__(self, yanitlar: list):
        self.yanitlar = list(yanitlar)
        self.istekler: list = []

    def __call__(self, istek, timeout=None):
        if isinstance(istek, str):
            k = {"url": istek, "yontem": "GET", "basliklar": {}, "govde": None}
        else:
            k = {"url": istek.full_url, "yontem": istek.get_method(),
                 "basliklar": {a.lower(): d for a, d in istek.header_items()},
                 "govde": None if istek.data is None else bytes(istek.data).hex()}
        self.istekler.append(k)
        if not self.yanitlar:
            raise AssertionError("beklenmeyen istek: " + k["url"])
        y = self.yanitlar.pop(0)
        govde = bytes.fromhex(y["govde"])
        if 200 <= y["durum"] < 300:
            return _Yanit(y["durum"], govde)
        b = email.message.Message()
        for a, d in y["basliklar"].items():
            b[a] = d
        raise urllib.error.HTTPError(k["url"], y["durum"], "hata", b, io.BytesIO(govde))


def _yanit(durum: int, govde=b"", basliklar=None) -> dict:
    if isinstance(govde, (dict, list)):
        govde = json.dumps(govde).encode("utf-8")
    elif isinstance(govde, str):
        govde = govde.encode("utf-8")
    return {"durum": durum, "basliklar": basliklar or {}, "govde": govde.hex()}


@contextlib.contextmanager
def _yalitim(ag: _SahteAg, nc: bytes = NC):
    """Ag, saat, rastgele ve disk yazimini sabitle; cikista eski hallerine don."""
    eski = (IM.urllib.request.urlopen, IM.time, IM.secrets, IM.Cihaz.kaydet)
    IM.urllib.request.urlopen = ag
    IM.time = types.SimpleNamespace(time=lambda: SIMDI_S)
    IM.secrets = types.SimpleNamespace(token_bytes=lambda n: nc[:n])
    IM.Cihaz.kaydet = lambda self: None
    try:
        yield
    finally:
        IM.urllib.request.urlopen, IM.time, IM.secrets, IM.Cihaz.kaydet = eski


def _cihaz_d(c) -> dict:
    return {"kimlik": c.kimlik, "n": c.n, "K": c.K.hex(), "ad": c.ad, "sayac": c.sayac,
            "acilis": c.acilis}


def istek_vektorleri() -> list:
    K = _bayt("istek/K", 32)
    bilgi_y = _yanit(200, {"kimlik": KIMLIK, "acilis": ACILIS, "tuz": PROJE_TUZ.hex(),
                           "tur": PROJE_TUR, "zorunlu": 0, "misafir": 0, "saat": "ntp"})
    ok = _yanit(200, "tamam")
    durumlar = [
        ("get_liste", "ac", TABAN, "GET", "/kayit/liste", [], b"", 0, ACILIS, [ok]),
        ("get_sorgu_sayac_artar", "ac", TABAN, "GET", "/kayit/veri",
         [("sira", "12"), ("not", "a&b=c ğ")], b"", 1759000000900, ACILIS, [ok]),
        ("post_komut", "ac", TABAN, "POST", "/komut", [], b"Go1234", 0, ACILIS, [ok]),
        ("post_sil", "ac", TABAN, "POST", "/cihaz/sil", [("n", "3")], b"", 0, ACILIS, [ok]),
        ("taban_egik", "ac", TABAN + "/", "GET", "/kayit/liste", [], b"", 0, ACILIS, [ok]),
        ("yeniden_dene", "ac", TABAN, "GET", "/kayit/liste", [], b"", 0, ACILIS,
         [_yanit(401, "imza", {"X-Acilis": YENI_ACILIS}), ok]),
        ("ayni_acilis_hata", "ac", TABAN, "GET", "/kayit/liste", [], b"", 0, ACILIS,
         [_yanit(401, "imza", {"X-Acilis": ACILIS})]),
        ("acilissiz_401_hata", "ac", TABAN, "GET", "/kayit/liste", [], b"", 0, ACILIS,
         [_yanit(401, "imza")]),
        ("iki_401_hata", "ac", TABAN, "POST", "/komut", [], b"Go1", 0, ACILIS,
         [_yanit(401, "imza", {"X-Acilis": YENI_ACILIS}),
          _yanit(401, "imza", {"X-Acilis": "00" * 16})]),
        ("sunucu_500", "ac", TABAN, "POST", "/komut", [], b"Go1", 0, ACILIS, [_yanit(500, "x")]),
        ("acilis_bilgiden", "ac", TABAN, "GET", "/kayit/liste", [], b"", 0, "", [bilgi_y, ok]),
        ("akis", "akis_url", TABAN, None, None, None, None, 41, ACILIS, []),
        ("akis_acilis_bilgiden", "akis_url", TABAN + "/", None, None, None, None, 0, "", [bilgi_y]),
    ]
    c = []
    for ad, islev, taban, y, yol, args, gv, sayac, acilis, yanitlar in durumlar:
        ag = _SahteAg(yanitlar)
        cihaz = IM.Cihaz(Path("yok.json"), KIMLIK, 3, K, "PC ğ", sayac, acilis)
        bas = _cihaz_d(cihaz)
        o = {"ad": ad, "islev": islev, "taban": taban, "cihaz": bas, "simdi_ms": int(SIMDI_S * 1000),
             "yanitlar": yanitlar}
        if islev == "ac":
            o.update({"yontem": y, "yol": yol, "argumanlar": [list(a) for a in args], "govde": gv.hex()})
        with _yalitim(ag):
            try:
                if islev == "ac":
                    with IM.ac(cihaz, taban, y, yol, args, gv) as r:
                        o["sonuc"] = {"durum": r.status}
                else:
                    o["sonuc"] = {"url": IM.akis_url(cihaz, taban)}
            except urllib.error.HTTPError as h:
                o["sonuc"] = {"hata": "HTTPError", "durum": h.code}
        assert not ag.yanitlar, ad
        o["istekler"] = ag.istekler
        o["cihaz_son"] = _cihaz_d(cihaz)
        c.append(o)
    return c


def esles_akis_vektorleri() -> list:
    P = IM.pbkdf2(PROJE_PAROLA, PROJE_TUZ, PROJE_TUR)
    n = 3
    kart_kanit = IM.kanit_kart(P, KIMLIK, NK, NC, n)
    yanlis = bytes([kart_kanit[0]]) + kart_kanit[1:-1] + bytes([kart_kanit[-1] ^ 1])

    def bilgi(**degis):
        b = {"kimlik": KIMLIK, "acilis": ACILIS, "tuz": PROJE_TUZ.hex(), "tur": PROJE_TUR,
             "zorunlu": 0, "misafir": 0, "saat": "ntp"}
        b.update(degis)
        return _yanit(200, b)

    baslat = _yanit(200, {"eno": 5, "nk": NK.hex()})
    kanit = _yanit(200, {"n": n, "kart_kanit": kart_kanit.hex()})
    durumlar = [
        ("basarili", "PC ğ", PROJE_PAROLA, [bilgi(), baslat, kanit]),
        ("tur_metin", "PC", PROJE_PAROLA,
         [bilgi(tur="20000"), baslat, _yanit(200, {"n": n, "kart_kanit": IM.kanit_kart(
             P, KIMLIK, NK, NC, n).hex()})]),
        ("kart_kaniti_yanlis", "PC", PROJE_PAROLA,
         [bilgi(), baslat, _yanit(200, {"n": n, "kart_kanit": yanlis.hex()})]),
        ("kart_kaniti_kisa", "PC", PROJE_PAROLA,
         [bilgi(), baslat, _yanit(200, {"n": n, "kart_kanit": kart_kanit[:31].hex()})]),
        ("tur_dusuk", "PC", PROJE_PAROLA, [bilgi(tur=9_999)]),
        ("tur_yuksek", "PC", PROJE_PAROLA, [bilgi(tur=1_000_001)]),
        ("tur_yok", "PC", PROJE_PAROLA, [bilgi(tur=None)]),
        ("kimlik_buyuk_harf", "PC", PROJE_PAROLA, [bilgi(kimlik=KIMLIK.upper())]),
        ("tuz_kisa", "PC", PROJE_PAROLA, [bilgi(tuz=PROJE_TUZ.hex()[:30])]),
        ("acilis_bicimsiz", "PC", PROJE_PAROLA, [bilgi(acilis="xyz")]),
        ("kisa_parola", "PC", "a" * 11, []),
        ("parola_kod_noktasi", "PC", "🔋🔋abcdefghi", []),        # 11 kod noktasi, 13 UTF-16 birimi
        ("ad_bos", "", PROJE_PAROLA, []),
        ("ad_uzun", "a" * 25, PROJE_PAROLA, []),
        ("baslat_429", "PC", PROJE_PAROLA, [bilgi(), _yanit(429, "bekle 4 s")]),
        ("kanit_403", "PC", PROJE_PAROLA, [bilgi(), baslat, _yanit(403, "kanit yanlis")]),
    ]
    c = []
    for ad_, ad, parola, yanitlar in durumlar:
        ag = _SahteAg(yanitlar)
        o = {"ad": ad_, "taban": TABAN, "cihaz_adi": ad, "parola": parola, "nc": NC.hex(),
             "yanitlar": yanitlar}
        with _yalitim(ag):
            try:
                cihaz = IM.esles(TABAN, ad, parola, dizin=Path("yok"))
                o["sonuc"] = {"cihaz": _cihaz_d(cihaz)}
            except (ValueError, RuntimeError, TypeError) as h:
                o["sonuc"] = {"hata": type(h).__name__}
        assert not ag.yanitlar, ad_
        o["istekler"] = ag.istekler
        c.append(o)
    beklenen_basari = {"basarili", "tur_metin"}
    for o in c:
        assert ("cihaz" in o["sonuc"]) == (o["ad"] in beklenen_basari), o["ad"]
    return c


def bilgi_denetle_vektorleri() -> list:
    temel = {"kimlik": KIMLIK, "tuz": PROJE_TUZ.hex(), "acilis": ACILIS, "tur": PROJE_TUR}
    degisler = [
        ("temel", {}),
        ("tur_ondalik", {"tur": 20000.7}),
        ("tur_metin_alt_cizgi", {"tur": "20_000"}),
        ("tur_metin_bosluk", {"tur": " 20000 "}),
        ("tur_alt_sinir", {"tur": 10_000}),
        ("tur_ust_sinir", {"tur": 1_000_000}),
        ("tur_alti", {"tur": 9_999}),
        ("tur_ustu", {"tur": 1_000_001}),
        ("tur_true", {"tur": True}),
        ("tur_null", {"tur": None}),
        ("tur_metin_bozuk", {"tur": "20k"}),
        ("tur_yok", {"tur": "__sil__"}),
        ("kimlik_tamsayi", {"kimlik": 1234567890123456}),
        ("kimlik_15", {"kimlik": KIMLIK[:15]}),
        ("kimlik_buyuk", {"kimlik": KIMLIK.upper()}),
        ("kimlik_yok", {"kimlik": "__sil__"}),
        ("tuz_buyuk", {"tuz": PROJE_TUZ.hex().upper()}),
        ("tuz_34", {"tuz": PROJE_TUZ.hex() + "00"}),
        ("acilis_null", {"acilis": None}),
        ("acilis_satir_sonu", {"acilis": ACILIS + "\n"}),
    ]
    c = []
    for ad, d in degisler:
        b = dict(temel)
        for k, v in d.items():
            if v == "__sil__":
                del b[k]
            else:
                b[k] = v
        o = {"ad": ad, "bilgi": b}
        try:
            kim, tuz, tur, acilis = IM._bilgi_denetle(b)
            o["sonuc"] = {"kimlik": kim, "tuz": tuz.hex(), "tur": tur, "acilis": acilis}
        except (ValueError, TypeError) as h:
            o["sonuc"] = {"hata": type(h).__name__}
        c.append(o)
    return c


# ── 1E: zarf ─────────────────────────────────────────────────────────────
ONEK = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def _json(d) -> str:
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def zarf_vektorleri() -> dict:
    A = _bayt("zarf/anahtar", 32)
    icerikler = [
        ("durum", f"ok/{ONEK}/durum",
         {"c": 1, "a": 3, "t": 1790000000, "k": 1, "o": 12, "y": 1, "d": 5, "e": 0, "f": "A3-1E"}),
        ("olay_turkce", f"ok/{ONEK}/olay",
         {"n": 7, "a": 3, "t": 1790000100, "o": "kayit_bitti", "s": "kayıt bitti: şarj ÇÖĞÜŞİ ≥ %5"}),
        ("vasiyet", f"ok/{ONEK}/durum", {"c": 0, "a": 3}),
        ("kacislar", f"ok/{ONEK}/olay",
         {"q": "\"\\/\b\f\n\r\t\x01\x1f\x7f  ", "e": "🔋", "bos": ""}),
        ("ic_ice", f"ok/{ONEK}/olay",
         {"z": 1, "a": [1, 2, {"y": None, "b": True, "f": False}], "m": {}, "l": []}),
        ("ondalik", f"ok/{ONEK}/olay",
         {"f": [0.1, 1e-05, 1.5e-07, 5e-324, 0.0001, 9.99e-05, 123456.789, -2.5,
                4503599627370495.5, 1e-300, -0.000123, 0.5]}),
        ("buyuk_tamsayi", f"ok/{ONEK}/olay",
         {"b": 9007199254740991, "c": -9007199254740991, "d": 2 ** 60, "e": 10 ** 20, "s": 0}),
        ("bos_nesne", f"ok/{ONEK}/olay", {}),
        ("turkce_konu", "ok/ğüşiöç/olay", {"n": 1}),
        ("bos_konu", "", {"n": 1}),
        ("uzun", f"ok/{ONEK}/olay", {"s": "x" * 500, "n": list(range(40))}),
    ]
    kur = []
    for i, (ad, konu, icerik) in enumerate(icerikler):
        nonce = _bayt(f"zarf/nonce/{i}", 12)
        z = BL.zarf_kur(A, konu, icerik, nonce)
        assert BL.zarf_ac(A, konu, z) == icerik
        kur.append({"ad": ad, "konu": konu, "nonce": nonce.hex(), "icerik": icerik,
                    "duz": _json(icerik), "zarf": z.hex()})
    # JS duz nesnesi tamsayi benzeri anahtarlari one alir: sira Map ile korunur
    cifler = [["b", 1], ["10", 2], ["2", 3], ["a", 4]]
    nonce = _bayt("zarf/nonce/cifler", 12)
    z = BL.zarf_kur(A, f"ok/{ONEK}/olay", dict(cifler), nonce)
    sirali = {"ad": "tamsayi_anahtar_sirasi", "konu": f"ok/{ONEK}/olay", "nonce": nonce.hex(),
              "icerik_cifler": cifler, "duz": _json(dict(cifler)), "zarf": z.hex()}

    # bozuk zarflar: Python REDDETMELI (dogrulanir), JS de
    konu = f"ok/{ONEK}/olay"
    z = bytes.fromhex(kur[1]["zarf"])
    nonce = z[4:16]

    def ham(duz: bytes) -> bytes:
        return b"OKB1" + nonce + CC.sifrele(A, nonce, duz, konu.encode("utf-8"))

    def cevir(b: bytes, i: int, m: int = 1) -> bytes:
        x = bytearray(b)
        x[i] ^= m
        return bytes(x)

    bozuk = [
        ("yanlis_konu", f"ok/{ONEK}/durum", A, z),
        ("baska_onek", f"ok/{'0' * 32}/olay", A, z),
        ("yanlis_anahtar", konu, _bayt("zarf/baska", 32), z),
        ("sihir_OKB2", konu, A, b"OKB2" + z[4:]),
        ("sihirsiz", konu, A, z[4:]),
        ("kisa_31", konu, A, z[:31]),
        ("bos", konu, A, b""),
        ("sifreli_bit", konu, A, cevir(z, 20)),
        ("etiket_son_bit", konu, A, cevir(z, len(z) - 1, 0x80)),
        ("nonce_bit", konu, A, cevir(z, 4)),
        ("bir_bayt_fazla", konu, A, z + b"\x00"),
        ("json_degil", konu, A, ham(b"bu json degil")),
        ("json_liste", konu, A, ham(b"[1,2]")),
        ("json_metin", konu, A, ham(b'"x"')),
        ("utf8_degil", konu, A, ham(b'{"s":"\xff"}')),
        ("bom_json", konu, A, ham(b"\xef\xbb\xbf{}")),
    ]
    red = []
    for ad, k, an, v in bozuk:
        assert _hata_adi(lambda: BL.zarf_ac(an, k, v)) is not None, ad
        assert _hata_adi(lambda: BL.zarf_ac(an, k, v)) in ("ValueError", "UnicodeDecodeError",
                                                           "JSONDecodeError"), ad
        red.append({"ad": ad, "konu": k, "anahtar": an.hex(), "zarf": v.hex()})

    # /bildirim/bilgi
    K = _bayt("bilgi/K", 32)
    kimlik, n = KIMLIK, 3
    aad = BL.bilgi_aad(kimlik, n).decode("utf-8")
    temel = {"u": "mqtts://x.emqxsl.com:8883", "k": "olcum-cihaz", "p": "parola-ğ 🔋",
             "o": ONEK, "a": _bayt("bilgi/a", 32).hex()}
    bilgi_durum = [
        ("temel", temel, None),
        ("anahtar_buyuk_hex", {**temel, "a": temel["a"].upper()}, None),
        ("fazla_alan", {**temel, "x": 1}, None),
        ("onek_buyuk", {**temel, "o": ONEK.upper()}, None),
        ("onek_31", {**temel, "o": ONEK[:31]}, None),
        ("onek_hex_degil", {**temel, "o": "g" + ONEK[1:]}, None),
        ("onek_satir_sonu", {**temel, "o": ONEK + "\n"}, None),
        ("anahtar_63", {**temel, "a": temel["a"][:63]}, None),
        ("anahtar_hex_degil", {**temel, "a": "g" + temel["a"][1:]}, None),
        ("parola_yok", {k: v for k, v in temel.items() if k != "p"}, None),
        ("kullanici_sayi", {**temel, "k": 5}, None),
        ("uri_bos", {**temel, "u": ""}, None),
        ("liste", [temel], None),
        ("yanlis_n", temel, (kimlik, n + 1)),
        ("yanlis_kimlik", temel, ("a1b2c3d4e5f60719", n)),
    ]
    bilgi = []
    for i, (ad, icerik, coz_ile) in enumerate(bilgi_durum):
        nonce = _bayt(f"bilgi/nonce/{i}", 12)
        govde = BL.zarf_kur(K, aad, icerik, nonce)
        ck, cn = coz_ile or (kimlik, n)
        o = {"ad": ad, "K": K.hex(), "kimlik": ck, "n": cn, "govde": govde.hex()}
        try:
            s = BL.bilgi_coz(K, ck, cn, govde)
            o["sonuc"] = {**s, "anahtar": s["anahtar"].hex()}
        except ValueError as h:
            o["sonuc"] = {"hata": type(h).__name__}
        bilgi.append(o)
    gecerli = {"temel", "anahtar_buyuk_hex", "fazla_alan"}
    for o in bilgi:
        assert ("hata" not in o["sonuc"]) == (o["ad"] in gecerli), o["ad"]

    return {"anahtar": A.hex(), "kur": kur, "sirali": sirali, "red": red,
            "bilgi_aad": {"kimlik": kimlik, "n": n, "aad": BL.bilgi_aad(kimlik, n).hex()},
            "bilgi": bilgi}


def uret() -> dict:
    return {
        "aciklama": "2B capraz vektorleri — uretim/ortak_vektor_kripto.py uretir; elle duzenleme. "
                    "Python baslangici: hashlib/hmac, kopru/chacha.py, kopru/imza.py, kopru/bildirim.py",
        "sha256": sha_vektorleri(),
        "hmac": hmac_vektorleri(),
        "pbkdf2": pbkdf2_vektorleri(),
        "chacha": chacha_vektorleri(),
        "poly1305": poly_vektorleri(),
        "aead": aead_vektorleri(),
        "imza": imza_saf_vektorleri(),
        "esles_hesap": esles_hesap_vektorleri(),
        "istekler": istek_vektorleri(),
        "esles_akis": esles_akis_vektorleri(),
        "bilgi_denetle": bilgi_denetle_vektorleri(),
        "zarf": zarf_vektorleri(),
    }


def main() -> int:
    metin = json.dumps(uret(), ensure_ascii=False, indent=1) + "\n"
    if "--denetle" in sys.argv:
        guncel = HEDEF.exists() and HEDEF.read_text(encoding="utf-8") == metin
        print("guncel" if guncel else f"ESKI — python uretim/{Path(__file__).name}")
        return 0 if guncel else 1
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_text(metin, encoding="utf-8", newline="\n")
    print(f"yazildi: {HEDEF.relative_to(KOK).as_posix()} ({len(metin.encode('utf-8'))} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
