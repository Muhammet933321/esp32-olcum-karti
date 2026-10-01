# -*- coding: utf-8 -*-
"""1E — ChaCha20-Poly1305 IETF AEAD (RFC 8439), saf Python, yalniz stdlib.

    sifrele(anahtar, nonce, duz, aad=b"")        -> sifreli metin + 16 B etiket
    coz(anahtar, nonce, sifreli_etiket, aad=b"")  -> duz metin (etiket tutmazsa ValueError)

Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K5, K10, K12). Kart tarafi ayni
algoritmayi C++'ta kosar; ikisi de RFC 8439 vektorleriyle sinanir
(uretim/test_bildirim.py: 2.1.1, 2.3.2, 2.4.2, 2.5.2, 2.6.2, 2.8.2).

Dahili parcalar vektor sinamasi icin acik: `ceyrek_tur`, `blok`, `akis_sifrele`,
`poly1305`, `poly1305_anahtar_uret`.

Not: bu gercekleme performans icin degil okunurluk icin yazildi (bildirim
yukleri < 1 KB). Etiket karsilastirmasi sabit zamanli (`hmac.compare_digest`);
Python tamsayi aritmetigi ise sabit zamanli DEGIL — tehdit modeli aracinin icerik
okuyamamasi / sahte olay uretememesi, yerel zamanlama yan kanali degil.
"""
from __future__ import annotations

import hmac
import struct

ANAHTAR_UZUNLUK = 32
NONCE_UZUNLUK = 12
ETIKET_UZUNLUK = 16
_MASKE = 0xFFFFFFFF
_SABIT = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)    # "expand 32-byte k"
_P = (1 << 130) - 5
_R_MASKE = 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF


def _rotl(v: int, n: int) -> int:
    return ((v << n) & _MASKE) | (v >> (32 - n))


def ceyrek_tur(a: int, b: int, c: int, d: int) -> tuple[int, int, int, int]:
    """RFC 8439 2.1: ChaCha ceyrek turu (32 bit sozcuklerde)."""
    a = (a + b) & _MASKE
    d = _rotl(d ^ a, 16)
    c = (c + d) & _MASKE
    b = _rotl(b ^ c, 12)
    a = (a + b) & _MASKE
    d = _rotl(d ^ a, 8)
    c = (c + d) & _MASKE
    b = _rotl(b ^ c, 7)
    return a, b, c, d


def ceyrek_tur_durum(durum: list[int], a: int, b: int, c: int, d: int) -> None:
    """RFC 8439 2.2: 16 sozcuklu durumda dort indisin ceyrek turu (yerinde)."""
    durum[a], durum[b], durum[c], durum[d] = ceyrek_tur(durum[a], durum[b], durum[c], durum[d])


def _denetle(anahtar: bytes, nonce: bytes) -> None:
    if len(anahtar) != ANAHTAR_UZUNLUK:
        raise ValueError(f"anahtar {ANAHTAR_UZUNLUK} bayt olmali ({len(anahtar)} verildi)")
    if len(nonce) != NONCE_UZUNLUK:
        raise ValueError(f"nonce {NONCE_UZUNLUK} bayt olmali ({len(nonce)} verildi)")


def baslangic_durumu(anahtar: bytes, sayac: int, nonce: bytes) -> list[int]:
    """RFC 8439 2.3: sabit(4) + anahtar(8) + sayac(1) + nonce(3), hepsi little-endian."""
    _denetle(anahtar, nonce)
    if not 0 <= sayac <= _MASKE:
        raise ValueError("blok sayaci 32 bit olmali")
    return [*_SABIT, *struct.unpack("<8I", anahtar), sayac, *struct.unpack("<3I", nonce)]


def blok(anahtar: bytes, sayac: int, nonce: bytes) -> bytes:
    """RFC 8439 2.3: 20 turluk blok fonksiyonu, 64 baytlik anahtar akisi blogu."""
    ilk = baslangic_durumu(bytes(anahtar), sayac, bytes(nonce))
    d = ilk[:]
    for _ in range(10):
        ceyrek_tur_durum(d, 0, 4, 8, 12)
        ceyrek_tur_durum(d, 1, 5, 9, 13)
        ceyrek_tur_durum(d, 2, 6, 10, 14)
        ceyrek_tur_durum(d, 3, 7, 11, 15)
        ceyrek_tur_durum(d, 0, 5, 10, 15)
        ceyrek_tur_durum(d, 1, 6, 11, 12)
        ceyrek_tur_durum(d, 2, 7, 8, 13)
        ceyrek_tur_durum(d, 3, 4, 9, 14)
    return struct.pack("<16I", *[(x + y) & _MASKE for x, y in zip(d, ilk)])


def akis_sifrele(anahtar: bytes, sayac: int, nonce: bytes, duz: bytes) -> bytes:
    """RFC 8439 2.4: ChaCha20 sifreleme (XOR; ayni islev cozer). Sayac `sayac`'tan baslar."""
    anahtar, nonce, duz = bytes(anahtar), bytes(nonce), bytes(duz)
    cikis = bytearray()
    for i in range(0, len(duz), 64):
        anahtar_akisi = blok(anahtar, sayac + i // 64, nonce)
        parca = duz[i:i + 64]
        cikis += bytes(x ^ y for x, y in zip(parca, anahtar_akisi))
    return bytes(cikis)


def poly1305(anahtar: bytes, mesaj: bytes) -> bytes:
    """RFC 8439 2.5: Poly1305 tek kullanimlik MAC; anahtar 32 B (r || s), cikis 16 B."""
    anahtar, mesaj = bytes(anahtar), bytes(mesaj)
    if len(anahtar) != 32:
        raise ValueError("Poly1305 anahtari 32 bayt olmali")
    r = int.from_bytes(anahtar[:16], "little") & _R_MASKE
    s = int.from_bytes(anahtar[16:], "little")
    a = 0
    for i in range(0, len(mesaj), 16):
        a = (a + int.from_bytes(mesaj[i:i + 16] + b"\x01", "little")) * r % _P
    return ((a + s) & ((1 << 128) - 1)).to_bytes(16, "little")


def poly1305_anahtar_uret(anahtar: bytes, nonce: bytes) -> bytes:
    """RFC 8439 2.6: Poly1305 anahtari = ChaCha20 blogu (sayac 0) ilk 32 bayti."""
    return blok(anahtar, 0, nonce)[:32]


def _dolgu(b: bytes) -> bytes:
    return b"\x00" * (-len(b) % 16)


def _etiket(otk: bytes, aad: bytes, sifreli: bytes) -> bytes:
    """RFC 8439 2.8: aad || dolgu || sifreli || dolgu || len(aad) u64 LE || len(sifreli) u64 LE."""
    return poly1305(otk, aad + _dolgu(aad) + sifreli + _dolgu(sifreli)
                    + struct.pack("<QQ", len(aad), len(sifreli)))


def sifrele(anahtar: bytes, nonce: bytes, duz: bytes, aad: bytes = b"") -> bytes:
    """RFC 8439 2.8: AEAD sifreleme. Donus = sifreli metin + 16 B etiket."""
    anahtar, nonce, duz, aad = bytes(anahtar), bytes(nonce), bytes(duz), bytes(aad)
    _denetle(anahtar, nonce)
    otk = poly1305_anahtar_uret(anahtar, nonce)
    sifreli = akis_sifrele(anahtar, 1, nonce, duz)
    return sifreli + _etiket(otk, aad, sifreli)


def coz(anahtar: bytes, nonce: bytes, sifreli_etiket: bytes, aad: bytes = b"") -> bytes:
    """AEAD cozme. Etiket tutmazsa (bozuk veri, yanlis anahtar/nonce/aad) ValueError;
    etiket DOGRULANMADAN hicbir duz metin dondurulmez."""
    anahtar, nonce, sifreli_etiket, aad = (bytes(anahtar), bytes(nonce),
                                          bytes(sifreli_etiket), bytes(aad))
    _denetle(anahtar, nonce)
    if len(sifreli_etiket) < ETIKET_UZUNLUK:
        raise ValueError("sifreli metin etiketten kisa")
    sifreli, etiket = sifreli_etiket[:-ETIKET_UZUNLUK], sifreli_etiket[-ETIKET_UZUNLUK:]
    beklenen = _etiket(poly1305_anahtar_uret(anahtar, nonce), aad, sifreli)
    if not hmac.compare_digest(beklenen, etiket):
        raise ValueError("etiket tutmadi (bozuk veri, yanlis anahtar ya da yanlis konu)")
    return akis_sifrele(anahtar, 1, nonce, sifreli)
