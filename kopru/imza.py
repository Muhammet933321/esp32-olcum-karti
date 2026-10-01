# -*- coding: utf-8 -*-
"""1D — cihaz eslestirmesi ve imzali istekler: PC istemcisi (yalniz stdlib).

    python imza.py esles --host olcum.local --ad PC          parolayla (parola sorulur, yankilanmaz)
    python imza.py esles-usb --port COM6 --ad PC             USB'den (parola yok)
    python imza.py liste --host olcum.local                  kartin cihaz listesi (imzali)
    python imza.py sil --host olcum.local --n 3              cihaz sil (imzali)
    python imza.py saat --host olcum.local                   NTP'siz karta saat ver (imzali)

Tasarim: tasarim/2026-10-01-1d-eslestirme.md (K4-K10, K13, K17). Bu dosyanin SAF
kismi kartin `guvenlik.h`'siyle ayni bicimi uretir; ikisi de
`uretim/vektor_guvenlik.json` vektorleriyle sinanir (B72.G, B71.U).

Bicimler (spec K5, K6, K9):
    P      = PBKDF2-HMAC-SHA256(parola, tuz, tur, 32)
    kanit  = HMAC(P, "OK1-istemci\\n" kimlik "\\n" nk_hex "\\n" nc_hex "\\n" ad)
    kart   = HMAC(P, "OK1-kart\\n"    kimlik "\\n" nk_hex "\\n" nc_hex "\\n" n)
    K      = HMAC(P, "OK1-anahtar\\n" kimlik "\\n" nk_hex "\\n" nc_hex "\\n" n)
    kanonik = "OK1\\n" yontem "\\n" yol ["?" a=d&...] "\\n" acilis "\\n" sayac "\\n" sha256(govde)_hex
    imza   = HMAC(K, kanonik)  (hex)
Sorgu argumanlari gelis sirasiyla, ad ve deger YUZDE KODLU (RFC 3986 ayrilmamis
karakterler aynen, gerisi %XX): boylece a="1&b=2" ile a=1&b=2 ayni metni vermez.

Anahtar saklama (K13): `kopru/.cihaz/<kart kimligi>.json` (git disi). Windows'ta
`K` DPAPI ile kullanici hesabina bagli sifrelenir; baska sistemde duz + dosya
izni 600 ve dosyada uyari. Sayac her istekte diske yazilir: yeni surec eskisinin
altina inmez (`max(son + 1, unix_ms)`).
"""
from __future__ import annotations

import argparse
import base64
import ctypes
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SURUM = "OK1"
AD_AZAMI = 24                      # bayt (UTF-8); kartta GUV_AD_AZAMI
_AYRILMAMIS = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
VARSAYILAN_DIZIN = Path(__file__).parent / ".cihaz"


# ── saf cekirdek (kartla ayni bicim) ─────────────────────────────────────
def yuzde_kodla(s: str) -> str:
    """RFC 3986: ayrilmamis karakterler aynen, gerisi UTF-8 baytlari %XX (buyuk harf)."""
    return "".join(chr(b) if b in _AYRILMAMIS else f"%{b:02X}" for b in s.encode("utf-8"))


def ad_gecerli(ad: str) -> bool:
    """1-24 bayt UTF-8, kontrol karakteri yok (kanit metninde ayirici '\\n')."""
    b = ad.encode("utf-8")
    return 0 < len(b) <= AD_AZAMI and not any(c < 0x20 or c == 0x7F for c in b)


def pbkdf2(parola: str, tuz: bytes, tur: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", parola.encode("utf-8"), tuz, tur, 32)


def _h(anahtar: bytes, metin: str) -> bytes:
    return hmac.new(anahtar, metin.encode("utf-8"), hashlib.sha256).digest()


def _ortak(kimlik: str, nk: bytes, nc: bytes) -> str:
    return f"\n{kimlik}\n{nk.hex()}\n{nc.hex()}\n"


def kanit_istemci(P: bytes, kimlik: str, nk: bytes, nc: bytes, ad: str) -> bytes:
    return _h(P, f"{SURUM}-istemci" + _ortak(kimlik, nk, nc) + ad)


def kanit_kart(P: bytes, kimlik: str, nk: bytes, nc: bytes, n: int) -> bytes:
    return _h(P, f"{SURUM}-kart" + _ortak(kimlik, nk, nc) + str(n))


def cihaz_anahtari(P: bytes, kimlik: str, nk: bytes, nc: bytes, n: int) -> bytes:
    return _h(P, f"{SURUM}-anahtar" + _ortak(kimlik, nk, nc) + str(n))


def kanonik(yontem: str, yol: str, argumanlar, acilis: str, sayac: int,
            govde: bytes) -> bytes:
    sorgu = "&".join(yuzde_kodla(a) + "=" + yuzde_kodla(d) for a, d in argumanlar)
    return (f"{SURUM}\n{yontem}\n{yol}" + (f"?{sorgu}" if sorgu else "")
            + f"\n{acilis}\n{sayac}\n{hashlib.sha256(govde).hexdigest()}").encode("utf-8")


def imzala(K: bytes, yontem: str, yol: str, argumanlar, acilis: str, sayac: int,
           govde: bytes) -> str:
    return hmac.new(K, kanonik(yontem, yol, argumanlar, acilis, sayac, govde),
                    hashlib.sha256).hexdigest()


# ── anahtar saklama: DPAPI (Windows) ─────────────────────────────────────
class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(veri: bytes, koru: bool) -> bytes:
    crypt32 = ctypes.windll.crypt32                 # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32               # type: ignore[attr-defined]
    tampon = ctypes.create_string_buffer(veri, len(veri))
    giris = _BLOB(len(veri), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_char)))
    cikis = _BLOB()
    islev = crypt32.CryptProtectData if koru else crypt32.CryptUnprotectData
    islev.argtypes = [ctypes.POINTER(_BLOB), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                      ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(_BLOB)]
    islev.restype = ctypes.c_int
    if not islev(ctypes.byref(giris), None, None, None, None, 0x1, ctypes.byref(cikis)):
        raise OSError("DPAPI " + ("koruma" if koru else "cozme") + " basarisiz")
    try:
        return ctypes.string_at(cikis.pbData, cikis.cbData)
    finally:
        kernel32.LocalFree(cikis.pbData)


class Cihaz:
    """Eslesmis cihaz: kart kimligi, numara, anahtar (diskte korunur), sayac, acilis."""

    def __init__(self, dosya: Path, kimlik: str, n: int, K: bytes, ad: str,
                 sayac: int = 0, acilis: str = ""):
        self.dosya, self.kimlik, self.n, self.K, self.ad = Path(dosya), kimlik, n, K, ad
        self.sayac, self.acilis = sayac, acilis

    def kaydet(self) -> None:
        d = {"surum": 1, "kimlik": self.kimlik, "n": self.n, "ad": self.ad,
             "sayac": self.sayac, "acilis": self.acilis}
        if sys.platform == "win32":
            d["K_dpapi"] = base64.b64encode(_dpapi(self.K, True)).decode("ascii")
        else:
            d["K_duz"] = self.K.hex()
            d["uyari"] = "DPAPI yok: anahtar yalniz dosya izniyle (600) korunuyor"
        self.dosya.parent.mkdir(parents=True, exist_ok=True)
        gecici = self.dosya.with_suffix(".tmp")
        gecici.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        if sys.platform != "win32":
            os.chmod(gecici, 0o600)
        os.replace(gecici, self.dosya)

    @classmethod
    def yukle(cls, dosya) -> "Cihaz":
        d = json.loads(Path(dosya).read_text(encoding="utf-8"))
        K = (_dpapi(base64.b64decode(d["K_dpapi"]), False) if "K_dpapi" in d
             else bytes.fromhex(d["K_duz"]))
        return cls(Path(dosya), d["kimlik"], int(d["n"]), K, d["ad"], int(d["sayac"]),
                   d.get("acilis", ""))

    def sonraki_sayac(self) -> int:
        s = max(self.sayac + 1, int(time.time() * 1000))
        self.sayac = s
        self.kaydet()
        return s

    def basliklar(self, yontem: str, yol: str, argumanlar, govde: bytes) -> dict:
        s = self.sonraki_sayac()
        return {"X-Cihaz": str(self.n), "X-Sayac": str(s),
                "X-Imza": imzala(self.K, yontem, yol, argumanlar, self.acilis, s, govde)}


# ── ag ───────────────────────────────────────────────────────────────────
def taban_url(host: str) -> str:
    return (host if host.startswith("http") else f"http://{host}").rstrip("/")


def _url(taban: str, yol: str, argumanlar) -> str:
    q = "&".join(yuzde_kodla(a) + "=" + yuzde_kodla(d) for a, d in argumanlar)
    return taban.rstrip("/") + yol + (f"?{q}" if q else "")


def bilgi(taban: str, zaman_asimi: float = 10.0) -> dict:
    with urllib.request.urlopen(taban.rstrip("/") + "/eslestir/bilgi", timeout=zaman_asimi) as y:
        return json.loads(y.read().decode("utf-8"))


def ac(cihaz: Cihaz, taban: str, yontem: str, yol: str, argumanlar=(), govde: bytes = b"",
       zaman_asimi: float = 10.0):
    """Imzali istek; urlopen gibi yanit nesnesi dondurur (`with` ile kullan).
    401 + YENI `X-Acilis` (kart yeniden basladi): acilis guncellenir, BIR KEZ
    yeniden denenir. Acilis ayniysa (cihaz silinmis, saat/sayac sorunu) hata."""
    argumanlar = list(argumanlar)
    if not cihaz.acilis:
        cihaz.acilis = bilgi(taban, zaman_asimi)["acilis"]
        cihaz.kaydet()
    for deneme in (0, 1):
        b = {"X-Olcum": "1", **cihaz.basliklar(yontem, yol, argumanlar, govde)}
        if yontem == "POST":
            b["Content-Type"] = "text/plain"
        istek = urllib.request.Request(_url(taban, yol, argumanlar),
                                       data=govde if yontem == "POST" else None,
                                       method=yontem, headers=b)
        try:
            return urllib.request.urlopen(istek, timeout=zaman_asimi)
        except urllib.error.HTTPError as h:
            yeni = h.headers.get("X-Acilis") if h.code == 401 else None
            if deneme == 0 and yeni and yeni != cihaz.acilis:
                cihaz.acilis = yeni
                cihaz.kaydet()
                continue
            raise
    raise RuntimeError("erisilemez")                 # pragma: no cover


def akis_url(cihaz: Cihaz, taban: str) -> str:
    """EventSource baslik tasiyamaz: imza `_c _s _i` sorgu argumanlarinda (kanonige girmez)."""
    if not cihaz.acilis:
        cihaz.acilis = bilgi(taban)["acilis"]
        cihaz.kaydet()
    s = cihaz.sonraki_sayac()
    return (f"{taban.rstrip('/')}/akis?_c={cihaz.n}&_s={s}"
            f"&_i={imzala(cihaz.K, 'GET', '/akis', [], cihaz.acilis, s, b'')}")


def _post_acik(taban: str, yol: str, argumanlar, zaman_asimi: float) -> dict:
    istek = urllib.request.Request(_url(taban, yol, argumanlar), data=b"", method="POST",
                                   headers={"X-Olcum": "1", "Content-Type": "text/plain"})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            return json.loads(y.read().decode("utf-8"))
    except urllib.error.HTTPError as h:
        metin = h.read().decode("utf-8", "replace")
        raise RuntimeError(f"{yol}: {h.code} {metin}") from None


def esles(taban: str, ad: str, parola: str, dizin=None, zaman_asimi: float = 30.0) -> Cihaz:
    """Parolali eslestirme (K5). Parola ve P aga CIKMAZ. Kartin kaniti dogrulanmadan
    anahtar KAYDEDILMEZ (karsilikli: sahte kart parolayi bilmez)."""
    if not ad_gecerli(ad):
        raise ValueError("ad 1-24 bayt olmali, kontrol karakteri yok")
    b = bilgi(taban, zaman_asimi)
    kimlik, tuz, tur, acilis = b["kimlik"], bytes.fromhex(b["tuz"]), int(b["tur"]), b["acilis"]
    nc = secrets.token_bytes(16)
    y = _post_acik(taban, "/eslestir/baslat", [("ad", ad), ("nc", nc.hex())], zaman_asimi)
    eno, nk = int(y["eno"]), bytes.fromhex(y["nk"])
    P = pbkdf2(parola, tuz, tur)
    kanit = kanit_istemci(P, kimlik, nk, nc, ad)
    y = _post_acik(taban, "/eslestir/kanit", [("eno", str(eno)), ("kanit", kanit.hex())],
                   zaman_asimi)
    n = int(y["n"])
    if not hmac.compare_digest(bytes.fromhex(y["kart_kanit"]), kanit_kart(P, kimlik, nk, nc, n)):
        raise RuntimeError("kart kaniti YANLIS — bu kart parolayi bilmiyor (sahte kart?); "
                           "cihaz KAYDEDILMEDI")
    c = Cihaz(Path(dizin or VARSAYILAN_DIZIN) / f"{kimlik}.json", kimlik, n,
              cihaz_anahtari(P, kimlik, nk, nc, n), ad, 0, acilis)
    c.kaydet()
    return c


def _bekle(kart, kosul, zaman_asimi: float) -> str:
    son = time.monotonic() + zaman_asimi
    while time.monotonic() < son:
        s = kart.satir_oku(0.2)
        if s and kosul(s):
            return s
    raise TimeoutError("kart yanit vermedi (USB? dogru soket COM yazan)")


def esles_usb(kart, ad: str, dizin=None, zaman_asimi: float = 5.0) -> Cihaz:
    """USB eslestirmesi (K17): `kart` yaz()/satir_oku() sunan seri baglanti
    (kart_baglanti.SeriKart). Kart anahtari YALNIZ seriye basar (`EK n hex`)."""
    if not ad_gecerli(ad):
        raise ValueError("ad 1-24 bayt olmali, kontrol karakteri yok")
    kart.yaz("E?")
    durum = _bekle(kart, lambda s: s.startswith("E zorunlu=") or s.startswith("! E"), zaman_asimi)
    if durum.startswith("! E"):
        raise RuntimeError(durum)
    kimlik = next(t.split("=", 1)[1] for t in durum.split() if t.startswith("kimlik="))
    kart.yaz(f"Ep{ad}")
    satir = _bekle(kart, lambda s: s.startswith("EK ") or s.startswith("! E"), zaman_asimi)
    if satir.startswith("! E"):
        raise RuntimeError(satir)
    _, n, h = satir.split()
    c = Cihaz(Path(dizin or VARSAYILAN_DIZIN) / f"{kimlik}.json", kimlik, int(n),
              bytes.fromhex(h), ad, 0, "")
    c.kaydet()
    return c


def cihaz_bul(dizin=None, dosya=None) -> Cihaz:
    if dosya:
        return Cihaz.yukle(dosya)
    adaylar = sorted(Path(dizin or VARSAYILAN_DIZIN).glob("*.json"))
    if len(adaylar) != 1:
        raise SystemExit(f"{len(adaylar)} cihaz dosyasi var — --cihaz ile sec")
    return Cihaz.yukle(adaylar[0])


def main() -> int:
    ap = argparse.ArgumentParser(description="Olcum karti cihaz eslestirmesi ve imzali istekler")
    alt = ap.add_subparsers(dest="komut", required=True)
    e = alt.add_parser("esles")
    e.add_argument("--host", default="olcum.local")
    e.add_argument("--ad", required=True)
    u = alt.add_parser("esles-usb")
    u.add_argument("--port", default=None)
    u.add_argument("--ad", required=True)
    for ad in ("liste", "sil", "saat"):
        p = alt.add_parser(ad)
        p.add_argument("--host", default="olcum.local")
        p.add_argument("--cihaz", default=None)
        if ad == "sil":
            p.add_argument("--n", type=int, required=True)
    a = ap.parse_args()
    if a.komut == "esles":
        parola = getpass.getpass("kartin web parolasi (ekrana yazilmaz): ")
        c = esles(taban_url(a.host), a.ad, parola)
        print(f"eslesti: cihaz {c.n} ({c.ad}) -> {c.dosya}")
        return 0
    if a.komut == "esles-usb":
        import kart_baglanti
        kart = kart_baglanti.SeriKart(a.port)
        kart.ac()
        try:
            c = esles_usb(kart, a.ad)
        finally:
            kart.kapat()
        print(f"eslesti (USB): cihaz {c.n} ({c.ad}) -> {c.dosya}")
        return 0
    c = cihaz_bul(dosya=a.cihaz)
    taban = taban_url(a.host)
    if a.komut == "liste":
        with ac(c, taban, "GET", "/cihaz/liste") as y:
            print(y.read().decode("utf-8"))
    elif a.komut == "sil":
        with ac(c, taban, "POST", "/cihaz/sil", [("n", str(a.n))]) as y:
            print(y.status)
    elif a.komut == "saat":
        with ac(c, taban, "POST", "/saat", [("unix", str(int(time.time())))]) as y:
            print(y.status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
