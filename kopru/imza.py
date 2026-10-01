# -*- coding: utf-8 -*-
"""1D — cihaz eslestirmesi ve imzali istekler: PC istemcisi (yalniz stdlib).

Tasarim: tasarim/2026-10-01-1d-eslestirme.md (K4-K10). Bu dosyanin SAF kismi
(asagida) kartin `guvenlik.h`'siyle ayni bicimi uretir; ikisi de
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
"""
from __future__ import annotations

import hashlib
import hmac

SURUM = "OK1"
AD_AZAMI = 24                      # bayt (UTF-8); kartta GUV_AD_AZAMI
_AYRILMAMIS = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


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
