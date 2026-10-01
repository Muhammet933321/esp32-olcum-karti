# -*- coding: utf-8 -*-
"""1E (spec "Dogrulama" B72, PC kismi) — bildirim zarfi, ChaCha20-Poly1305, MQTT istemcisi.

    python uretim/test_bildirim.py        (kok dizinden ya da uretim/ icinden)

Donanim ve ag GEREKMIYOR: aracı yerine test icinde yerel TCP'de (127.0.0.1) calisan SAHTE
ARACI var; kart yerine yerel HTTP sunucusu. Saf Python ChaCha20-Poly1305 RFC 8439 vektorleriyle
(2.1.1, 2.2.1, 2.3.2, 2.4.2, 2.5.2, 2.6.2, 2.8.2) sinanir; zarf bicimi BAGIMSIZ hesaplanmis
bilinen-cevap vektorlerine (KAT) sabitlenmistir — kart tarafinin (bildirim.h, B71) ayni
vektorleri kullanmasi icindir.

Son bolum tezgah aracı `kopru/sahte_araci.py`'yi sinar (kimlik, ACL, retained, joker karakter,
QoS 1, keepalive zaman asimi -> vasiyet, ani kopus -> vasiyet, DISCONNECT -> vasiyet YOK,
ayni kimlikle takeover, kesinti + ayni portta yeniden acma). Sahte aracı kartin vasiyet/keepalive
davranisini olcen tezgahin (uretim/tezgah_bildirim.py) olcu aleti: kendisi once burada sinaniyor.

SinanMAYAN: gercek TLS (sertifika/ad denetimi) ve gercek aracı (HiveMQ) — tezgah kalemi.
"""
from __future__ import annotations

import contextlib
import http.server
import io
import json
import random
import socket
import ssl
import struct
import sys
import tempfile
import threading
import time
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import bildirim                                            # noqa: E402
import chacha                                              # noqa: E402
import imza                                                # noqa: E402
import mqtt_istemci as mq                                  # noqa: E402
import sahte_araci as SA                                   # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))


def hata_verir(islev, tur=ValueError) -> bool:
    try:
        islev()
    except tur:
        return True
    except Exception:                                      # baska tur = beklenen degil
        return False
    return False


def hx(metin: str) -> bytes:
    return bytes.fromhex(metin.replace(" ", "").replace("\n", ""))


# ── RFC 8439 vektorleri ──────────────────────────────────────────────────
RFC_ANAHTAR = bytes(range(32))                                       # 00..1f
RFC_METIN = (b"Ladies and Gentlemen of the class of '99: If I could offer you only "
             b"one tip for the future, sunscreen would be it.")
AEAD_ANAHTAR = bytes(range(0x80, 0xA0))                              # 80..9f
AEAD_NONCE = hx("07 00 00 00 40 41 42 43 44 45 46 47")
AEAD_AAD = hx("50 51 52 53 c0 c1 c2 c3 c4 c5 c6 c7")
AEAD_SIFRELI = hx("""
    d3 1a 8d 34 64 8e 60 db 7b 86 af bc 53 ef 7e c2
    a4 ad ed 51 29 6e 08 fe a9 e2 b5 a7 36 ee 62 d6
    3d be a4 5e 8c a9 67 12 82 fa fb 69 da 92 72 8b
    1a 71 de 0a 9e 06 0b 29 05 d6 a5 b6 7e cd 3b 36
    92 dd bd 7f 2d 77 8b 8c 98 03 ae e3 28 09 1b 58
    fa b3 24 e4 fa d6 75 94 55 85 80 8b 48 31 d7 bc
    3f f4 de f0 8e 4b 7a 9d e5 76 d2 65 86 ce c6 4b
    61 16""")
AEAD_ETIKET = hx("1a e1 0b 59 4f 09 e2 6a 7e 90 2e cb d0 60 06 91")


def bolum_chacha() -> None:
    print("\n-- ChaCha20-Poly1305: RFC 8439 vektorleri --")
    # 2.1.1
    ok("2.1.1 ceyrek tur (a,b,c,d tamsayi)",
       chacha.ceyrek_tur(0x11111111, 0x01020304, 0x9B8D6F43, 0x01234567)
       == (0xEA2A92F4, 0xCB1CF8CE, 0x4581472E, 0x5881C4BB))
    # 2.2.1
    d = [0x879531E0, 0xC5ECF37D, 0x516461B1, 0xC9A62F8A,
         0x44C20EF3, 0x3390AF7F, 0xD9FC690B, 0x2A5F714C,
         0x53372767, 0xB00A5631, 0x974C541A, 0x359E9963,
         0x5C971061, 0x3D631689, 0x2098D9D6, 0x91DBD320]
    chacha.ceyrek_tur_durum(d, 2, 7, 8, 13)
    ok("2.2.1 ceyrek tur (durum uzerinde 2,7,8,13)",
       d[2] == 0xBDB886DC and d[7] == 0xCFACAFD2 and d[8] == 0xE46BEA80 and d[13] == 0xCCC07C79
       and d[0] == 0x879531E0 and d[15] == 0x91DBD320)
    # 2.3.2
    beklenen_blok = hx("""
        10 f1 e7 e4 d1 3b 59 15 50 0f dd 1f a3 20 71 c4
        c7 d1 f4 c7 33 c0 68 03 04 22 aa 9a c3 d4 6c 4e
        d2 82 64 46 07 9f aa 09 14 c2 d7 05 d9 8b 02 a2
        b5 12 9c d1 de 16 4e b9 cb d0 83 e8 a2 50 3c 4e""")
    blok = chacha.blok(RFC_ANAHTAR, 1, hx("00 00 00 09 00 00 00 4a 00 00 00 00"))
    ok("2.3.2 blok fonksiyonu (sayac 1)", blok == beklenen_blok, blok.hex()[:32] + "...")
    # 2.4.2
    beklenen_sifre = hx("""
        6e 2e 35 9a 25 68 f9 80 41 ba 07 28 dd 0d 69 81
        e9 7e 7a ec 1d 43 60 c2 0a 27 af cc fd 9f ae 0b
        f9 1b 65 c5 52 47 33 ab 8f 59 3d ab cd 62 b3 57
        16 39 d6 24 e6 51 52 ab 8f 53 0c 35 9f 08 61 d8
        07 ca 0d bf 50 0d 6a 61 56 a3 8e 08 8a 22 b6 5e
        52 bc 51 4d 16 cc f8 06 81 8c e9 1a b7 79 37 36
        5a f9 0b bf 74 a3 5b e6 b4 0b 8e ed f2 78 5e 42
        87 4d""")
    nonce_242 = hx("00 00 00 00 00 00 00 4a 00 00 00 00")
    c = chacha.akis_sifrele(RFC_ANAHTAR, 1, nonce_242, RFC_METIN)
    ok("2.4.2 ChaCha20 sifreleme (114 bayt, 2 blok)", c == beklenen_sifre and len(c) == 114)
    ok("2.4.2 ayni islev cozer", chacha.akis_sifrele(RFC_ANAHTAR, 1, nonce_242, c) == RFC_METIN)
    # 2.5.2
    mac = chacha.poly1305(hx("85 d6 be 78 57 55 6d 33 7f 44 52 fe 42 d5 06 a8 "
                             "01 03 80 8a fb 0d b2 fd 4a bf f6 af 41 49 f5 1b"),
                          b"Cryptographic Forum Research Group")
    ok("2.5.2 Poly1305 etiketi", mac == hx("a8 06 1d c1 30 51 36 c6 c2 2b 8b af 0c 01 27 a9"),
       mac.hex())
    # 2.6.2
    pk = chacha.poly1305_anahtar_uret(AEAD_ANAHTAR, hx("00 00 00 00 00 01 02 03 04 05 06 07"))
    ok("2.6.2 Poly1305 anahtar uretimi",
       pk == hx("8a d5 a0 8b 90 5f 81 cc 81 50 40 27 4a b2 94 71 "
                "a8 33 b6 37 e3 fd 0d a5 08 db b8 e2 fd d1 a6 46"))
    # 2.8.2
    s = chacha.sifrele(AEAD_ANAHTAR, AEAD_NONCE, RFC_METIN, AEAD_AAD)
    ok("2.8.2 AEAD sifreleme: sifreli metin", s[:-16] == AEAD_SIFRELI)
    ok("2.8.2 AEAD sifreleme: etiket", s[-16:] == AEAD_ETIKET, s[-16:].hex())
    ok("2.8.2 AEAD cozme", chacha.coz(AEAD_ANAHTAR, AEAD_NONCE, AEAD_SIFRELI + AEAD_ETIKET,
                                      AEAD_AAD) == RFC_METIN)


def bolum_oynama() -> None:
    print("\n-- AEAD: bozulma her halde reddedilir --")
    tam = AEAD_SIFRELI + AEAD_ETIKET

    def coz(sifreli=tam, anahtar=AEAD_ANAHTAR, nonce=AEAD_NONCE, aad=AEAD_AAD):
        return chacha.coz(anahtar, nonce, sifreli, aad)

    def cevir(b: bytes, i: int, maske: int = 0x01) -> bytes:
        m = bytearray(b)
        m[i] ^= maske
        return bytes(m)

    ok("kontrol: bozulmamis veri COZULUR (reddetmeye takilmis kod degil)", coz() == RFC_METIN)
    ok("sifreli metnin bir biti -> ValueError", hata_verir(lambda: coz(cevir(tam, 5))))
    ok("sifreli metnin SON baytinin biti -> ValueError",
       hata_verir(lambda: coz(cevir(tam, len(AEAD_SIFRELI) - 1))))
    ok("etiketin ilk baytinin biti -> ValueError", hata_verir(lambda: coz(cevir(tam, len(tam) - 16))))
    ok("MUTASYON: etiketin yalniz SON bayti farkli -> ValueError",
       hata_verir(lambda: coz(cevir(tam, len(tam) - 1, 0x80))))
    ok("yanlis AAD -> ValueError", hata_verir(lambda: coz(aad=AEAD_AAD + b"x")))
    ok("bos AAD (AAD'siz) -> ValueError", hata_verir(lambda: coz(aad=b"")))
    ok("yanlis anahtar (1 bit) -> ValueError",
       hata_verir(lambda: coz(anahtar=cevir(AEAD_ANAHTAR, 0))))
    ok("yanlis nonce (1 bit) -> ValueError", hata_verir(lambda: coz(nonce=cevir(AEAD_NONCE, 11))))
    ok("bir bayt eklenmis -> ValueError", hata_verir(lambda: coz(tam + b"\x00")))
    ok("bir bayt eksik -> ValueError", hata_verir(lambda: coz(tam[:-1])))
    ok("etiketten kisa girdi (15 B) -> ValueError", hata_verir(lambda: coz(tam[:15])))
    ok("bos girdi -> ValueError", hata_verir(lambda: coz(b"")))
    ok("anahtar 31 bayt -> ValueError",
       hata_verir(lambda: chacha.sifrele(AEAD_ANAHTAR[:31], AEAD_NONCE, b"x")))
    ok("nonce 8 bayt -> ValueError",
       hata_verir(lambda: chacha.sifrele(AEAD_ANAHTAR, AEAD_NONCE[:8], b"x")))
    ok("blok sayaci 2^32 -> ValueError",
       hata_verir(lambda: chacha.blok(AEAD_ANAHTAR, 1 << 32, AEAD_NONCE)))

    rng = random.Random(8439)
    kotu = []
    for n in (0, 1, 15, 16, 17, 63, 64, 65, 127, 128, 129, 1000):
        for aad_n in (0, 1, 16, 17):
            duz, aad = rng.randbytes(n), rng.randbytes(aad_n)
            nonce = rng.randbytes(12)
            if chacha.coz(AEAD_ANAHTAR, nonce, chacha.sifrele(AEAD_ANAHTAR, nonce, duz, aad),
                          aad) != duz:
                kotu.append((n, aad_n))
    ok("gidis-donus: 0..1000 bayt x AAD 0/1/16/17 bayt (dolgu sinirlari)", not kotu, str(kotu))


# ── zarf ─────────────────────────────────────────────────────────────────
ANAHTAR = bytes(range(0xA0, 0xC0))
ONEK = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
KONU_DURUM = f"ok/{ONEK}/durum"
KONU_OLAY = f"ok/{ONEK}/olay"
TR = "kayıt bitti: şarj ÇÖĞÜŞİ ≥ %5"     # kayıt bitti: şarj ÇÖĞÜŞİ ≥ %5
DURUM = {"c": 1, "a": 3, "t": 1790000000, "k": 1, "o": 12, "y": 1, "d": 5, "e": 0, "f": "A3-1E"}
OLAY = {"n": 7, "a": 3, "t": 1790000100, "o": "kayit_bitti", "s": TR}


def bolum_zarf() -> None:
    print("\n-- zarf: kur / ac --")
    # Bilinen-cevap vektorleri: BAGIMSIZ bir uygulamayla (cryptography) hesaplandi, buraya sabitlendi.
    K, nonce = bytes(range(32)), bytes(range(0x40, 0x4C))
    kat1 = hx("4f4b4231404142434445464748494a4b83761fa3487bc22339edcc3797cd0bef"
              "8eee222b69cd044d8355fca4e3eb33ea5f335ec73080bc9959")
    z1 = bildirim.zarf_kur(K, "ok/00112233445566778899aabbccddeeff/durum",
                           {"c": 1, "a": 7, "f": "A3-1E"}, nonce)
    ok("KAT 1: zarf baytlari bilinen cevapla BIREBIR (dizilim + kompakt JSON + AAD = konu)",
       z1 == kat1, z1.hex())
    kat2 = hx("4f4b4231404142434445464748494a4b837612a34878c2232bedcc22d08e1409"
              "05b8437a2d883506c42c17c48b55504a33345ae6e2d5a16acff1ebf748293761"
              "f856627411acd4c44d9d2a9f12dd")
    z2 = bildirim.zarf_kur(K, "ok/00112233445566778899aabbccddeeff/olay",
                           {"n": 2, "s": "kayıt bitti: şarj ÇÖĞÜŞİ"}, nonce)
    ok("KAT 2: Turkce icerik UTF-8 ham baytla (ensure_ascii=False) BIREBIR", z2 == kat2, z2.hex())

    z = bildirim.zarf_kur(ANAHTAR, KONU_OLAY, OLAY)
    ok("zarf basi 'OKB1', nonce 12 bayt, uzunluk = 4+12+JSON+16",
       z[:4] == b"OKB1" and len(z) == 4 + 12 + len(
           json.dumps(OLAY, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 16)
    ok("zarf_ac: gidis-donus + Turkce karakterler", bildirim.zarf_ac(ANAHTAR, KONU_OLAY, z) == OLAY
       and bildirim.zarf_ac(ANAHTAR, KONU_OLAY, z)["s"] == TR)
    ok("her zarfta yeni rastgele nonce",
       bildirim.zarf_kur(ANAHTAR, KONU_OLAY, OLAY)[4:16] != z[4:16])
    ok("duz metin kompakt (bosluk/satir yok)",
       b'{"n":7,"a":3,' in chacha.coz(ANAHTAR, z[4:16], z[16:], KONU_OLAY.encode("utf-8")))

    ok("YANLIS KONU -> ValueError (AAD baglama)",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_DURUM, z)))
    ok("baska onekli konu -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, f"ok/{'0' * 32}/olay", z)))
    ok("yanlis anahtar -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(bytes(range(32)), KONU_OLAY, z)))
    ok("yanlis sihir 'OKB2' -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, b"OKB2" + z[4:])))
    ok("sihirsiz (nonce'tan baslayan) -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, z[4:])))
    ok("kisa zarf (31 bayt) -> ValueError", hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, z[:31])))
    ok("bos zarf -> ValueError", hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, b"")))
    ok("sifreli metnin 1 biti -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, z[:20] + bytes([z[20] ^ 1]) + z[21:])))
    ok("etiketin SON baytinin biti -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, z[:-1] + bytes([z[-1] ^ 1]))))
    ok("nonce'un 1 biti -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, z[:4] + bytes([z[4] ^ 1]) + z[5:])))

    def ham(duz: bytes) -> bytes:                  # etiketi GECERLI ama icerigi JSON-nesnesi olmayan zarf
        return b"OKB1" + nonce + chacha.sifrele(ANAHTAR, nonce, duz, KONU_OLAY.encode("utf-8"))
    ok("etiket gecerli ama JSON degil -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, ham(b"bu json degil"))))
    ok("etiket gecerli ama JSON liste -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, ham(b"[1,2]"))))
    ok("etiket gecerli ama UTF-8 degil -> ValueError",
       hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, ham(b"\xff\xfe{}"))))
    ok("zarf_kur: anahtar 31 bayt -> ValueError",
       hata_verir(lambda: bildirim.zarf_kur(ANAHTAR[:31], KONU_OLAY, OLAY)))
    ok("zarf_kur: nonce 11 bayt -> ValueError",
       hata_verir(lambda: bildirim.zarf_kur(ANAHTAR, KONU_OLAY, OLAY, nonce[:11])))
    ok("zarf_kur: NaN JSON'a girmez -> ValueError",
       hata_verir(lambda: bildirim.zarf_kur(ANAHTAR, KONU_OLAY, {"x": float("nan")})))


# ── /bildirim/bilgi ──────────────────────────────────────────────────────
K_CIHAZ = bytes(range(0x10, 0x30))
KIMLIK = "0123456789abcdef"
CIHAZ_N = 3
A_HEX = ANAHTAR.hex()


def bilgi_govde(d: dict, K=K_CIHAZ, kimlik=KIMLIK, n=CIHAZ_N, nonce=b"\x07" * 12) -> bytes:
    duz = json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return b"OKB1" + nonce + chacha.sifrele(K, nonce, duz, f"OK1-bildirim\n{kimlik}\n{n}".encode())


IYI_BILGI = {"u": "mqtts://x1.s1.eu.hivemq.cloud:8883", "k": "cihaz", "p": "pârola/şifre",
             "o": ONEK, "a": A_HEX}


def bolum_bilgi() -> None:
    print("\n-- /bildirim/bilgi: bilgi_coz --")
    ok("AAD bicimi tam: OK1-bildirim\\n<kimlik>\\n<n>",
       bildirim.bilgi_aad(KIMLIK, CIHAZ_N) == b"OK1-bildirim\n0123456789abcdef\n3")
    b = bildirim.bilgi_coz(K_CIHAZ, KIMLIK, CIHAZ_N, bilgi_govde(IYI_BILGI))
    ok("bilgi_coz: dort metin alani + anahtar BAYT olarak",
       b == {"uri": IYI_BILGI["u"], "kullanici": "cihaz", "parola": IYI_BILGI["p"],
             "onek": ONEK, "anahtar": ANAHTAR} and isinstance(b["anahtar"], bytes), str(sorted(b)))
    ok("bilgi_coz: anahtar zarf_ac ile uyumlu (bilgideki anahtarla bildirim cozulur)",
       bildirim.zarf_ac(b["anahtar"], KONU_DURUM, bildirim.zarf_kur(ANAHTAR, KONU_DURUM, DURUM)) == DURUM)
    ok("yanlis K -> ValueError", hata_verir(lambda: bildirim.bilgi_coz(
        bytes(32), KIMLIK, CIHAZ_N, bilgi_govde(IYI_BILGI))))
    ok("baska cihaz numarasi -> ValueError", hata_verir(lambda: bildirim.bilgi_coz(
        K_CIHAZ, KIMLIK, CIHAZ_N + 1, bilgi_govde(IYI_BILGI))))
    ok("baska kart kimligi -> ValueError", hata_verir(lambda: bildirim.bilgi_coz(
        K_CIHAZ, "fedcba9876543210", CIHAZ_N, bilgi_govde(IYI_BILGI))))
    ok("alan ayrimi: bildirim zarfi (konu AAD'li) bilgi diye KABUL EDILMEZ",
       hata_verir(lambda: bildirim.bilgi_coz(K_CIHAZ, KIMLIK, CIHAZ_N,
                                             bildirim.zarf_kur(K_CIHAZ, KONU_DURUM, IYI_BILGI))))
    ok("alan ayrimi: bilgi govdesi bildirim diye KABUL EDILMEZ",
       hata_verir(lambda: bildirim.zarf_ac(K_CIHAZ, KONU_DURUM, bilgi_govde(IYI_BILGI))))
    ok("bilgi govdesi bozuk -> ValueError", hata_verir(lambda: bildirim.bilgi_coz(
        K_CIHAZ, KIMLIK, CIHAZ_N, bilgi_govde(IYI_BILGI)[:-1])))

    def kotu(**degisiklik):
        d = {**IYI_BILGI, **degisiklik}
        return hata_verir(lambda: bildirim.bilgi_coz(K_CIHAZ, KIMLIK, CIHAZ_N, bilgi_govde(d)))
    ok("onek BUYUK harfli -> ValueError", kotu(o=ONEK.upper()))
    ok("onek 31 hane -> ValueError", kotu(o=ONEK[:-1]))
    ok("onek 33 hane -> ValueError", kotu(o=ONEK + "0"))
    ok("onek hex degil -> ValueError", kotu(o="g" + ONEK[1:]))
    ok("onek konu ayiricisi iceriyor -> ValueError", kotu(o=ONEK[:30] + "/#"))
    ok("anahtar 63 hane -> ValueError", kotu(a=A_HEX[:-1]))
    ok("anahtar 66 hane -> ValueError", kotu(a=A_HEX + "00"))
    ok("anahtar hex degil -> ValueError", kotu(a="zz" + A_HEX[2:]))
    ok("anahtar bos -> ValueError", kotu(a=""))
    ok("uri bos -> ValueError", kotu(u=""))
    ok("uri sayi -> ValueError", kotu(u=5))
    ok("parola alani sayi -> ValueError", kotu(p=5))
    eksik = {k: v for k, v in IYI_BILGI.items() if k != "p"}
    ok("alan eksik (p yok) -> ValueError", hata_verir(lambda: bildirim.bilgi_coz(
        K_CIHAZ, KIMLIK, CIHAZ_N, bilgi_govde(eksik))))

    ok("bilgi_coz(anahtar buyuk hex) kabul: A-F", bildirim.bilgi_coz(
        K_CIHAZ, KIMLIK, CIHAZ_N, bilgi_govde({**IYI_BILGI, "a": A_HEX.upper()}))["anahtar"] == ANAHTAR)


class _BilgiSunucu(http.server.BaseHTTPRequestHandler):
    def do_GET(self):                                       # noqa: N802
        # urllib baslik adlarini 'X-cihaz' diye yazar: karsilastirma kucuk harfle
        type(self).istekler.append((self.path, {k.lower(): v for k, v in self.headers.items()}))
        govde = type(self).govde
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def log_message(self, *a):                              # sessiz
        pass


def bolum_bilgi_al() -> None:
    print("\n-- bilgi_al: imzali GET --")
    _BilgiSunucu.istekler, _BilgiSunucu.govde = [], bilgi_govde(IYI_BILGI)
    sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _BilgiSunucu)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    acilis = "ab" * 16
    try:
        with tempfile.TemporaryDirectory() as dizin:
            cihaz = imza.Cihaz(Path(dizin) / f"{KIMLIK}.json", KIMLIK, CIHAZ_N, K_CIHAZ, "test",
                               0, acilis)
            b = bildirim.bilgi_al(cihaz, f"http://127.0.0.1:{sunucu.server_port}")
            ok("bilgi_al: sifreli govde cozuldu (K, kimlik, n cihazdan)",
               b["onek"] == ONEK and b["anahtar"] == ANAHTAR and b["kullanici"] == "cihaz")
            yol, basl = _BilgiSunucu.istekler[0]
            beklenen = imza.imzala(K_CIHAZ, "GET", "/bildirim/bilgi", [], acilis,
                                   int(basl["x-sayac"]), b"")
            ok("istek /bildirim/bilgi'ye IMZALI gitti (X-Cihaz, X-Sayac, X-Imza dogru)",
               yol == "/bildirim/bilgi" and basl["x-cihaz"] == str(CIHAZ_N)
               and basl["x-imza"] == beklenen, f"{yol} cihaz={basl.get('x-cihaz')}")
    finally:
        sunucu.shutdown()
        sunucu.server_close()


# ── MQTT cekirdegi ───────────────────────────────────────────────────────
def bolum_mqtt_cekirdek() -> None:
    print("\n-- MQTT: kalan uzunluk, ayristirici, PUBLISH --")
    vektor = {0: "00", 127: "7f", 128: "8001", 16383: "ff7f", 16384: "808001",
              2097151: "ffff7f", 2097152: "80808001", 268435455: "ffffff7f"}
    for n, beklenen in vektor.items():
        k = mq.uzunluk_kodla(n)
        ok(f"uzunluk_kodla({n}) = {beklenen}", k.hex() == beklenen, k.hex())
        c = mq.uzunluk_coz(k + b"\xaa")
        ok(f"uzunluk_coz({beklenen}) = {n}, {len(k)} bayt tuketir", c == (n, len(k)), str(c))
    ok("uzunluk_kodla(268435456) -> ValueError", hata_verir(lambda: mq.uzunluk_kodla(268435456)))
    ok("uzunluk_kodla(-1) -> ValueError", hata_verir(lambda: mq.uzunluk_kodla(-1)))
    ok("uzunluk_coz: yarim (80 80) -> None (henuz tam degil)", mq.uzunluk_coz(b"\x80\x80") is None)
    ok("uzunluk_coz: 4 bayt devam bitli -> MqttHata",
       hata_verir(lambda: mq.uzunluk_coz(b"\x80\x80\x80\x80\x01"), mq.MqttHata))
    ok("dize: Turkce UTF-8 + 2 bayt uzunluk", mq.dize("ş") == b"\x00\x02\xc5\x9f")

    yayin1 = mq.paket(0x31, mq.dize("ok/x/durum") + b"\x01\x02")
    buyuk = random.Random(5).randbytes(200)                          # 2 bayt kalan uzunluk
    yayin2 = mq.paket(0x32, mq.dize("ok/x/olay") + struct.pack(">H", 513) + buyuk)
    akis = yayin1 + b"\xd0\x00" + yayin2
    a = mq.Ayristirici()
    paketler, erken = [], False
    for i, bayt in enumerate(akis):                                  # BAYT BAYT besle
        a.besle(bytes([bayt]))
        while (p := a.sonraki()) is not None:
            paketler.append((i + 1, p))
    ok("ayristirici: bayt bayt beslemede 3 paket, tam paket gelmeden HICBIRI cikmaz",
       [p for _, p in paketler] == [(0x31, yayin1[2:]), (0xD0, b""), (0x32, yayin2[3:])]
       and [i for i, _ in paketler] == [len(yayin1), len(yayin1) + 2, len(akis)],
       str([i for i, _ in paketler]))
    ok("ayristirici: tampon bosaldi", a.bekleyen() == 0)
    b = mq.Ayristirici()
    b.besle(akis)
    ilk = [b.sonraki(), b.sonraki(), b.sonraki(), b.sonraki()]
    ok("ayristirici: tek yutumda 3 paket + sonra None",
       [p[0] for p in ilk[:3]] == [0x31, 0xD0, 0x32] and ilk[3] is None)
    c = mq.Ayristirici()
    c.besle(b"\x30\xff\xff\xff\xff\x01")
    ok("ayristirici: bicimsiz uzunluk -> MqttHata", hata_verir(c.sonraki, mq.MqttHata))

    ok("publish_coz: QoS0 retain",
       mq.publish_coz(0x31, mq.dize("ok/x/durum") + b"\x01\x02") == ("ok/x/durum", b"\x01\x02", True, 0, None))
    ok("publish_coz: QoS1 paket no 513, retain yok",
       mq.publish_coz(0x32, mq.dize("ok/x/olay") + struct.pack(">H", 513) + b"abc")
       == ("ok/x/olay", b"abc", False, 1, 513))
    ok("publish_coz: QoS 3 -> MqttHata", hata_verir(lambda: mq.publish_coz(0x36, mq.dize("a")), mq.MqttHata))
    ok("publish_coz: konu eksik -> MqttHata", hata_verir(lambda: mq.publish_coz(0x30, b"\x00\x09ab"), mq.MqttHata))
    ok("parola kullanici adi olmadan -> ValueError",
       hata_verir(lambda: mq.Istemci("h", 1883, False, None, "p")))


# ── sahte aracı ──────────────────────────────────────────────────────────
BUYUK_YUK = random.Random(1).randbytes(20000)            # 3 bayt kalan uzunluk
DURUM_ZARF = bildirim.zarf_kur(ANAHTAR, KONU_DURUM, DURUM)
OLAY_ZARF = bildirim.zarf_kur(ANAHTAR, KONU_OLAY, OLAY)
SONRA_OLAY = {"n": 8, "a": 3, "t": 1790000200, "o": "dolu"}
SONRA_ZARF = bildirim.zarf_kur(ANAHTAR, KONU_OLAY, SONRA_OLAY)
BEKLENEN_PAROLA = "gizli-parola-1234"


def _uz(n: int) -> bytes:                                # testin KENDI kodlayicisi (istemcininkine bagimli degil)
    cikis = bytearray()
    while True:
        b, n = n % 128, n // 128
        cikis.append(b | 0x80 if n else b)
        if not n:
            return bytes(cikis)


def _yayin_paketi(konu: str, yuk: bytes, retain=False, qos=0, no=None) -> bytes:
    k = konu.encode("utf-8")
    govde = struct.pack(">H", len(k)) + k + (struct.pack(">H", no) if qos else b"") + yuk
    return bytes([0x30 | (qos << 1) | int(retain)]) + _uz(len(govde)) + govde


class SahteAraci:
    """Tek baglantilik MQTT 3.1.1 araci taklidi (127.0.0.1, duz TCP).
    Istemcinin gonderdiklerini KAYDEDER; CONNECT'te kullanici/parola denetler; SUBSCRIBE'tan
    sonra retained QoS0 durum + QoS1 olay (bayt bayt parca parca) + 20000 B QoS0 yayinlar;
    ilk PINGREQ'e PINGRESP + bir QoS0 mesaj daha."""

    def __init__(self, connack_kodu=None, ping_cevapla=True, mesajlar=True,
                 suback_once=False, kullanici="cihaz", parola=BEKLENEN_PAROLA):
        self.connack_kodu, self.ping_cevapla, self.mesajlar = connack_kodu, ping_cevapla, mesajlar
        self.suback_once, self.kullanici, self.parola = suback_once, kullanici, parola
        self.baglanti: dict | None = None
        self.abonelikler: list = []
        self.puback: list = []
        self.pingreq = 0
        self.alinan_yayinlar: list = []
        self.disconnect = False
        self.hata: str | None = None
        self.bitti = threading.Event()
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.srv.settimeout(10)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self._calis, daemon=True).start()

    # -- okuma / yazma
    def _oku(self, n: int) -> bytes:
        veri = b""
        while len(veri) < n:
            p = self.conn.recv(n - len(veri))
            if not p:
                raise EOFError
            veri += p
        return veri

    def _paket(self) -> tuple[int, bytes]:
        ilk = self._oku(1)[0]
        carpan, deger = 1, 0
        while True:
            b = self._oku(1)[0]
            deger += (b & 0x7F) * carpan
            if not b & 0x80:
                break
            carpan *= 128
        return ilk, self._oku(deger)

    def _yaz(self, veri: bytes, parcali: bool = False) -> None:
        if not parcali:
            self.conn.sendall(veri)
            return
        for i in range(0, len(veri), 3):                    # istemcinin parcali okuma yolunu zorla
            self.conn.sendall(veri[i:i + 3])
            time.sleep(0.001)

    @staticmethod
    def _connect_coz(g: bytes) -> dict:
        i = 0

        def dize_oku():
            nonlocal i
            n = struct.unpack(">H", g[i:i + 2])[0]
            s = g[i + 2:i + 2 + n].decode("utf-8")
            i += 2 + n
            return s
        ad = dize_oku()
        seviye, bayrak = g[i], g[i + 1]
        keepalive = struct.unpack(">H", g[i + 2:i + 4])[0]
        i += 4
        istemci_id = dize_oku()
        kullanici = dize_oku() if bayrak & 0x80 else None
        parola = dize_oku() if bayrak & 0x40 else None
        return {"ad": ad, "seviye": seviye, "bayrak": bayrak, "keepalive": keepalive,
                "id": istemci_id, "kullanici": kullanici, "parola": parola, "kalan": len(g) - i}

    def _mesajlari_gonder(self) -> None:
        if not self.mesajlar:
            return
        self._yaz(_yayin_paketi(KONU_DURUM, DURUM_ZARF, retain=True))
        self._yaz(_yayin_paketi(KONU_OLAY, OLAY_ZARF, qos=1, no=77), parcali=True)
        self._yaz(_yayin_paketi(f"ok/{ONEK}/buyuk", BUYUK_YUK))

    def _calis(self) -> None:
        try:
            self.conn, _ = self.srv.accept()
        except OSError:
            self.bitti.set()
            return
        self.conn.settimeout(10)
        self.conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        ilk_ping = True
        try:
            ilk, g = self._paket()
            if ilk >> 4 != 1:
                raise ValueError("ilk paket CONNECT degil")
            self.baglanti = self._connect_coz(g)
            kod = 0
            if self.connack_kodu is not None:
                kod = self.connack_kodu
            elif (self.baglanti["kullanici"], self.baglanti["parola"]) != (self.kullanici, self.parola):
                kod = 4
            self._yaz(bytes([0x20, 2, 0, kod]))
            if kod:
                return
            while True:
                ilk, g = self._paket()
                tur = ilk >> 4
                if tur == 8:                                     # SUBSCRIBE
                    no = struct.unpack(">H", g[:2])[0]
                    n = struct.unpack(">H", g[2:4])[0]
                    filtre, qos = g[4:4 + n].decode("utf-8"), g[4 + n]
                    self.abonelikler.append((ilk, filtre, qos))
                    suback = bytes([0x90, 3]) + struct.pack(">H", no) + bytes([min(qos, 1)])
                    if self.suback_once:
                        self._mesajlari_gonder()
                        self._yaz(suback)
                    else:
                        self._yaz(suback)
                        self._mesajlari_gonder()
                elif tur == 4:                                   # PUBACK
                    self.puback.append(struct.unpack(">H", g[:2])[0])
                elif tur == 12:                                  # PINGREQ
                    self.pingreq += 1
                    if self.ping_cevapla:
                        self._yaz(bytes([0xD0, 0]))
                        if ilk_ping and self.mesajlar:
                            ilk_ping = False
                            self._yaz(_yayin_paketi(KONU_OLAY, SONRA_ZARF))
                elif tur == 3:                                   # istemci PUBLISH
                    qos, retain = (ilk >> 1) & 3, bool(ilk & 1)
                    n = struct.unpack(">H", g[:2])[0]
                    konu, i, no = g[2:2 + n].decode("utf-8"), 2 + n, None
                    if qos:
                        no = struct.unpack(">H", g[i:i + 2])[0]
                        i += 2
                    self.alinan_yayinlar.append({"konu": konu, "yuk": g[i:], "qos": qos,
                                                 "retain": retain, "no": no})
                    if qos == 1:
                        self._yaz(bytes([0x40, 2]) + struct.pack(">H", no))
                elif tur == 14:                                  # DISCONNECT
                    self.disconnect = True
                    return
        except (OSError, EOFError):
            pass
        except Exception as h:                                   # test hatasi: gorunur olsun
            self.hata = repr(h)
        finally:
            try:
                self.conn.close()
            except OSError:
                pass
            self.bitti.set()

    def kapat(self) -> None:
        self.srv.close()
        self.bitti.wait(3)


def bolum_araci() -> None:
    print("\n-- MQTT istemcisi <-> sahte aracı (yerel TCP) --")
    a = SahteAraci()
    c = mq.Istemci("127.0.0.1", a.port, False, "cihaz", BEKLENEN_PAROLA, istemci_id="test-1",
                   keepalive=1, zaman_asimi=5.0)
    c.baglan()
    b = a.baglanti or {}
    ok("CONNECT: MQTT 3.1.1 (ad 'MQTT', seviye 4), temiz oturum, kullanici+parola bayragi",
       b.get("ad") == "MQTT" and b.get("seviye") == 4 and b.get("bayrak") == 0xC2, str(b.get("bayrak")))
    ok("CONNECT: kullanici/parola/istemci kimligi/keepalive aracıya ulasti, baska yuk yok",
       (b.get("kullanici"), b.get("parola"), b.get("id"), b.get("keepalive"), b.get("kalan"))
       == ("cihaz", BEKLENEN_PAROLA, "test-1", 1, 0))

    qos = c.abone(f"ok/{ONEK}/#", qos=1)
    ok("SUBSCRIBE: filtre + QoS 1, SUBACK onayi QoS 1",
       qos == 1 and a.abonelikler == [(0x82, f"ok/{ONEK}/#", 1)], str(a.abonelikler))

    mesajlar = []
    son = time.monotonic() + 8
    while len(mesajlar) < 4 and time.monotonic() < son:
        m = c.bekle(1.0)
        if m is not None:
            mesajlar.append(m)
    ok("4 mesaj geldi (retained + QoS1 parcali + 20 KB + ping sonrasi)", len(mesajlar) == 4,
       str([(m[0][-5:], len(m[1]), m[2]) for m in mesajlar]))
    if len(mesajlar) == 4:
        (k0, y0, r0), (k1, y1, r1), (k2, y2, r2), (k3, y3, r3) = mesajlar
        ok("1. mesaj: durum konusu, RETAIN=True, yuk bayt bayt ayni",
           k0 == KONU_DURUM and r0 is True and y0 == DURUM_ZARF)
        ok("1. mesaj zarf_ac ile cozulur (durum)", bildirim.zarf_ac(ANAHTAR, k0, y0) == DURUM)
        ok("2. mesaj: olay konusu, RETAIN=False, QoS1 bayt bayt parcali geldi ve cozuldu",
           k1 == KONU_OLAY and r1 is False and bildirim.zarf_ac(ANAHTAR, k1, y1) == OLAY)
        ok("2. mesaj: Turkce karakterler korunmus", bildirim.zarf_ac(ANAHTAR, k1, y1)["s"] == TR)
        ok("QoS1 PUBLISH icin PUBACK, DOGRU paket numarasiyla (77) gitti", a.puback == [77],
           str(a.puback))
        ok("3. mesaj: 20 000 bayt (3 bayt kalan uzunluk), RETAIN=False, bayt bayt ayni",
           k2 == f"ok/{ONEK}/buyuk" and r2 is False and y2 == BUYUK_YUK)
        ok("PINGREQ gitti (bos kalinan sure keepalive/2'yi gecince), aracı yanitladi",
           a.pingreq >= 1, f"{a.pingreq} adet")
        ok("PINGRESP sonrasi baglanti saglam: 4. mesaj geldi ve cozuldu",
           k3 == KONU_OLAY and bildirim.zarf_ac(ANAHTAR, k3, y3) == SONRA_OLAY)
        ok("yanlis konuyla (durum konusu, olay zarfi) cozme REDDEDILIR",
           hata_verir(lambda: bildirim.zarf_ac(ANAHTAR, k0, y1)))
        ok("yanlis anahtarla cozme reddedilir", hata_verir(lambda: bildirim.zarf_ac(bytes(32), k0, y0)))
    ok("bekle: gelecek bir sey yokken zaman asiminda None (hata degil)", c.bekle(0.2) is None)

    c.yayinla(f"ok/{ONEK}/olay", b"\x00\x01abc", qos=1, retain=True)
    c.yayinla(f"ok/{ONEK}/durum", b"q0", qos=0, retain=False)
    time.sleep(0.2)
    y = a.alinan_yayinlar
    ok("yayinla QoS1+retain: konu/yuk/bayraklar aracıya ulasti, PUBACK beklendi ve geldi",
       len(y) >= 1 and y[0]["konu"] == f"ok/{ONEK}/olay" and y[0]["yuk"] == b"\x00\x01abc"
       and y[0]["qos"] == 1 and y[0]["retain"] is True and y[0]["no"] not in (None, 0), str(y[:1]))
    ok("yayinla QoS0: PUBACK beklemeden gitti",
       len(y) == 2 and y[1]["qos"] == 0 and y[1]["retain"] is False and y[1]["yuk"] == b"q0", str(y[1:]))
    c.kapat()
    a.bitti.wait(3)
    ok("kapat(): DISCONNECT gonderdi", a.disconnect is True)
    ok("sahte aracı protokol hatasi gormedi", a.hata is None, str(a.hata))
    a.kapat()


def bolum_baglanti_hatalari() -> None:
    print("\n-- baglanti hatalari --")
    a = SahteAraci(connack_kodu=5)
    c = mq.Istemci("127.0.0.1", a.port, False, "cihaz", BEKLENEN_PAROLA, zaman_asimi=3.0)
    try:
        c.baglan()
        h = None
    except mq.BaglantiReddedildi as e:
        h = e
    ok("CONNACK donus kodu 5 (yetkisiz) -> BaglantiReddedildi(kod=5)", h is not None and h.kod == 5, str(h))
    ok("hata MqttHata alt sinifi ve parolayi ICERMIYOR", isinstance(h, mq.MqttHata)
       and BEKLENEN_PAROLA not in str(h))
    ok("reddedilen baglanti sonrasi bekle() 'baglanti yok' diye patlar (sessiz kalmaz)",
       hata_verir(lambda: c.bekle(0.1), mq.BaglantiKoptu))
    a.kapat()

    a = SahteAraci()                                       # aracı kullanici/parola denetler
    c = mq.Istemci("127.0.0.1", a.port, False, "cihaz", "yanlis-parola", zaman_asimi=3.0)
    try:
        c.baglan()
        h = None
    except mq.BaglantiReddedildi as e:
        h = e
    ok("yanlis parola: aracı kod 4 verir -> BaglantiReddedildi(kod=4)", h is not None and h.kod == 4, str(h))
    a.kapat()

    s = socket.socket()                                    # kimsenin dinlemedigi port
    s.bind(("127.0.0.1", 0))
    kapali = s.getsockname()[1]
    s.close()
    ok("kapali porta baglanma -> OSError (ConnectionRefusedError)",
       hata_verir(lambda: mq.Istemci("127.0.0.1", kapali, False, zaman_asimi=2.0).baglan(), OSError))

    a = SahteAraci(mesajlar=False, ping_cevapla=False)
    c = mq.Istemci("127.0.0.1", a.port, False, "cihaz", BEKLENEN_PAROLA, keepalive=1, zaman_asimi=3.0)
    c.baglan()
    c.abone(f"ok/{ONEK}/#")
    t0 = time.monotonic()
    try:
        c.bekle(6.0)
        h = None
    except mq.BaglantiKoptu as e:
        h = e
    gecen = time.monotonic() - t0
    ok("PINGRESP gelmezse baglanti OLU sayilir (BaglantiKoptu), keepalive+epsilon icinde",
       h is not None and a.pingreq == 1 and 1.0 < gecen < 3.5, f"{gecen:.2f} s, ping {a.pingreq}")
    c.kapat()
    a.kapat()

    a = SahteAraci(suback_once=True)
    c = mq.Istemci("127.0.0.1", a.port, False, "cihaz", BEKLENEN_PAROLA, zaman_asimi=3.0)
    c.baglan()
    q = c.abone(f"ok/{ONEK}/#")
    m = c.bekle(1.0)
    ok("PUBLISH, SUBACK'ten ONCE gelse de kaybolmaz (abone() kuyruga alir, bekle() verir)",
       q == 1 and m is not None and m[0] == KONU_DURUM and m[2] is True and m[1] == DURUM_ZARF)
    m2 = c.bekle(1.0)
    time.sleep(0.3)                                        # aracı PUBACK'i okusun
    ok("kuyruga alinan QoS1 mesaj da sirayla gelir, PUBACK gitti",
       m2 is not None and m2[0] == KONU_OLAY and a.puback == [77])
    c.kapat()
    a.kapat()


def bolum_tls_yolu() -> None:
    print("\n-- TLS yolu (sertifika denetimi gercek aracida: tezgah) --")
    gercek = ssl.create_default_context
    cagrilar = []

    class SahteBaglam:
        def wrap_socket(self, soket, server_hostname=None):
            cagrilar.append(server_hostname)
            return soket

    def sahte(*a, **k):
        cagrilar.append(("create_default_context", a, k))
        return SahteBaglam()

    a = SahteAraci()
    ssl.create_default_context = sahte
    try:
        c = mq.Istemci("127.0.0.1", a.port, True, "cihaz", BEKLENEN_PAROLA, zaman_asimi=3.0)
        c.baglan()
        c.kapat()
    finally:
        ssl.create_default_context = gercek
    ok("tls=True: ssl.create_default_context() (varsayilan = sertifika + ad denetimi) kullanilir",
       cagrilar[:1] == [("create_default_context", (), {})], str(cagrilar))
    ok("tls=True: server_hostname = baglanilan ad (ad denetimi icin)", cagrilar[1:] == ["127.0.0.1"], str(cagrilar))
    a.kapat()
    ok("varsayilan portlar: tls 8883, duz 1883",
       mq.Istemci("h", None, True).port == 8883 and mq.Istemci("h", None, False).port == 1883)
    ok("gercek varsayilan baglam sertifika+ad denetimi ister",
       ssl.create_default_context().check_hostname is True
       and ssl.create_default_context().verify_mode == ssl.CERT_REQUIRED)


# ── dinleyici (dinle / main) ─────────────────────────────────────────────
def bolum_dinleyici() -> None:
    print("\n-- dinleyici: dinle() ve komut satiri --")
    ok("uri_coz mqtts://h.ornek:8884", bildirim.uri_coz("mqtts://h.ornek:8884") == ("h.ornek", 8884, True))
    ok("uri_coz mqtts varsayilan port 8883", bildirim.uri_coz("mqtts://h.ornek") == ("h.ornek", 8883, True))
    ok("uri_coz mqtt://127.0.0.1 -> 1883, TLS yok", bildirim.uri_coz("mqtt://127.0.0.1") == ("127.0.0.1", 1883, False))
    ok("uri_coz http:// -> ValueError", hata_verir(lambda: bildirim.uri_coz("http://x")))
    ok("uri_coz ana adsiz -> ValueError", hata_verir(lambda: bildirim.uri_coz("mqtts://")))
    ok("onek_denetle: gecerli kabul, BUYUK/kisa reddedilir",
       bildirim.onek_denetle(ONEK) == ONEK and hata_verir(lambda: bildirim.onek_denetle(ONEK.upper()))
       and hata_verir(lambda: bildirim.onek_denetle(ONEK[:-1])))
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "anahtar.txt"
        p.write_text(A_HEX + "\n", encoding="ascii")
        hexten = bildirim.anahtar_oku(p)
        p.write_bytes(ANAHTAR)
        hamdan = bildirim.anahtar_oku(p)
        p.write_text("bu bir anahtar degil", encoding="ascii")
        ok("anahtar_oku: 64 hex metin ve ham 32 bayt ayni anahtari verir",
           hexten == ANAHTAR and hamdan == ANAHTAR)
        ok("anahtar_oku: bicimsiz dosya -> ValueError", hata_verir(lambda: bildirim.anahtar_oku(p)))

    a = SahteAraci()
    satirlar: list[str] = []
    n = bildirim.dinle(f"mqtt://127.0.0.1:{a.port}", "cihaz", BEKLENEN_PAROLA, ONEK, ANAHTAR,
                       sure=2.5, yaz=satirlar.append, zaman_asimi=3.0, keepalive=1)
    tum = "\n".join(satirlar)
    ok("dinle(): 4 mesaj alip cozdu (retained + olay + 20 KB zarf degil + ping sonrasi)",
       n == 4, f"{n} mesaj")
    ok("dinle(): durum satiri '(retained)' ve cozulmus JSON iceriyor",
       any("durum (retained)" in s and '"f":"A3-1E"' in s for s in satirlar))
    ok("dinle(): olay satiri Turkce karakterleri duz yaziyor", any(TR in s for s in satirlar))
    ok("dinle(): zarf OLMAYAN 20 KB yuk [COZULEMEDI] diye bildirilir, sessizce yutulmaz",
       any("buyuk" in s and "COZULEMEDI" in s for s in satirlar))
    ok("dinle(): satirlarda zaman damgasi (YYYY-AA-GG SS:DD:SS)",
       all(len(s) > 20 and s[4] == "-" and s[13] == ":" for s in satirlar))
    ok("dinle(): cikti PAROLAYI ve ANAHTARI icermez (hex, ham bayt, onek)",
       BEKLENEN_PAROLA not in tum and A_HEX not in tum and ANAHTAR.hex()[:16] not in tum
       and ONEK not in tum)
    ok("dinle(): TLS'siz baglantida aciktan uyarir", "TLS YOK" in tum)
    a.kapat()

    a = SahteAraci()
    hatali = None
    try:
        bildirim.dinle(f"mqtt://127.0.0.1:{a.port}", "cihaz", "yanlis", ONEK, ANAHTAR, sure=2.0,
                       yaz=lambda s: None, zaman_asimi=3.0)
    except mq.BaglantiReddedildi as e:
        hatali = e
    ok("dinle(): kimlik reddi (kod 4) YENIDEN DENENMEZ, hata verir", hatali is not None and hatali.kod == 4)
    a.kapat()

    # komut satiri: --uri ile elle kullanim
    with tempfile.TemporaryDirectory() as d:
        kf = Path(d) / "anahtar.hex"
        kf.write_text(A_HEX, encoding="ascii")
        a = SahteAraci()
        eski_argv, eski_getpass = sys.argv, bildirim.getpass.getpass
        sorulan = []
        bildirim.getpass.getpass = lambda istem="": sorulan.append(istem) or BEKLENEN_PAROLA
        sys.argv = ["bildirim.py", "dinle", "--uri", f"mqtt://127.0.0.1:{a.port}", "--kullanici",
                    "cihaz", "--onek", ONEK, "--anahtar-dosya", str(kf), "--sure", "2.5"]
        cikti, hata = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(hata):
                kod = bildirim.main()
        finally:
            sys.argv, bildirim.getpass.getpass = eski_argv, eski_getpass
        a.kapat()
    tum = cikti.getvalue() + hata.getvalue()
    ok("CLI: 'dinle --uri ...' cikis kodu 0, mesajlar yazildi",
       kod == 0 and "durum (retained)" in tum and TR in tum, f"kod {kod}")
    ok("CLI: parola getpass ile soruldu (argumanda yok) ve ciktida gorunmuyor",
       len(sorulan) == 1 and BEKLENEN_PAROLA not in tum and A_HEX not in tum)
    sys.argv = ["bildirim.py", "dinle", "--uri", "mqtt://127.0.0.1:1"]
    hata = io.StringIO()
    with contextlib.redirect_stderr(hata), contextlib.suppress(SystemExit):
        bildirim.main()
    ok("CLI: --uri ile --kullanici/--onek/--anahtar-dosya eksikse reddeder (argparse hatasi)",
       "birlikte gerekir" in hata.getvalue())
    sys.argv = eski_argv


# ── tezgah araci: kopru/sahte_araci.py ───────────────────────────────────
def _dz(s) -> bytes:
    b = s.encode("utf-8") if isinstance(s, str) else s
    return struct.pack(">H", len(b)) + b


def connect_paketi(cid: str, ka: int = 30, kul=None, par=None, temiz: bool = True, will=None) -> bytes:
    """will = (konu, yuk, qos, retain)."""
    bayrak, yuk = 0x02 if temiz else 0, _dz(cid)
    if will:
        wk, wy, wq, wr = will
        bayrak |= 0x04 | (wq << 3) | (0x20 if wr else 0)
        yuk += _dz(wk) + _dz(wy)
    if kul is not None:
        bayrak |= 0x80
        yuk += _dz(kul)
    if par is not None:
        bayrak |= 0x40
        yuk += _dz(par)
    govde = _dz("MQTT") + bytes([4, bayrak]) + struct.pack(">H", ka) + yuk
    return bytes([0x10]) + _uz(len(govde)) + govde


class Ham:
    """Ham soketli MQTT uygulamasi: sahte aracıyi `SA`dan BAGIMSIZ (mq.Ayristirici) sinar."""

    def __init__(self, port: int):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=3)
        self.ayr = mq.Ayristirici()
        self.t_connect = 0.0
        self._no = 0

    def gonder(self, veri: bytes) -> None:
        self.s.sendall(veri)

    def paket(self, zaman: float = 2.0):
        """(ilk, govde) | None (zaman asimi); baglanti kapaliysa EOFError."""
        son = time.monotonic() + zaman
        while True:
            p = self.ayr.sonraki()
            if p is not None:
                return p
            kalan = son - time.monotonic()
            if kalan <= 0:
                return None
            self.s.settimeout(kalan)
            try:
                v = self.s.recv(65536)
            except TimeoutError:
                return None
            except ConnectionError as h:
                raise EOFError from h
            if not v:
                raise EOFError
            self.ayr.besle(v)

    def bosalt(self, zaman: float = 1.5) -> tuple[list, bool]:
        """`zaman` s boyunca gelenleri topla; (paketler, baglanti_kapandi_mi)."""
        paketler = []
        try:
            while (p := self.paket(zaman)) is not None:
                paketler.append(p)
        except EOFError:
            return paketler, True
        return paketler, False

    def baglan(self, cid: str, **kw) -> int:
        self.t_connect = time.monotonic()
        self.gonder(connect_paketi(cid, **kw))
        p = self.paket(3.0)
        return p[1][1] if p and p[0] >> 4 == 2 else -1

    def abone(self, filtre: str, qos: int = 1) -> int:
        self._no += 1
        govde = struct.pack(">H", self._no) + _dz(filtre) + bytes([qos])
        self.gonder(bytes([0x82]) + _uz(len(govde)) + govde)
        p = self.paket(3.0)
        return p[1][2] if p and p[0] >> 4 == 9 else -1

    def yayinla(self, konu: str, yuk: bytes, qos: int = 0, retain: bool = False, no: int = 1) -> None:
        govde = _dz(konu) + (struct.pack(">H", no) if qos else b"") + yuk
        self.gonder(bytes([0x30 | (qos << 1) | int(retain)]) + _uz(len(govde)) + govde)

    def yayin_al(self, zaman: float = 2.0):
        """Siradaki PUBLISH: (konu, yuk, retain, qos, no) | None."""
        son = time.monotonic() + zaman
        while (kalan := son - time.monotonic()) > 0:
            p = self.paket(kalan)
            if p is not None and p[0] >> 4 == 3:
                return mq.publish_coz(*p)
        return None

    def nazik_kapat(self) -> None:
        try:
            self.gonder(b"\xe0\x00")
        except OSError:
            pass
        self.s.close()


SA_KUL = {"kart": ("kpw-1", "rw"), "cihaz": ("cpw-2", "r"), "diger": ("dpw-3", "rw")}


def bolum_sahte_araci_birim() -> None:
    print("\n-- sahte aracı: konu eslestirme, kullanici ayristirma, olay satiri --")
    tablo = [("ok/+/durum", "ok/x/durum", True), ("ok/+/durum", "ok/x/y/durum", False),
             ("ok/+/durum", "ok/durum", False), ("ok/#", "ok", True), ("ok/#", "ok/a/b", True),
             ("ok/#", "okx/a", False), ("#", "a/b/c", True), ("#", "$SYS/x", False),
             ("+/x", "$a/x", False), ("$SYS/#", "$SYS/x", True), ("a/b", "a/b", True),
             ("a/b", "a", False), ("a", "a/b", False), ("a/+", "a", False), ("a/+", "a/", True),
             ("+/+", "a/b", True), ("+", "a/b", False)]
    kotu = [(f, k, b) for f, k, b in tablo if SA.konu_eslesir(f, k) != b]
    ok(f"konu_eslesir: + tek seviye, # ust seviye dahil hepsi, $ konulari ({len(tablo)} durum)",
       not kotu, str(kotu))
    gec = ["a/#", "#", "+", "a/+/b", "+/+", "ok/+/durum"]
    gecersiz = ["", "a/#/b", "a#", "a/+b", "a/b+", "#/a", "a\x00b"]
    ok("filtre_gecerli: dogru filtreler kabul, # ortada/yapisik, + yapisik, bos reddedilir",
       all(SA.filtre_gecerli(f) for f in gec) and not any(SA.filtre_gecerli(f) for f in gecersiz))
    ok("konu_gecerli: joker ve bos konu yayinlanamaz",
       SA.konu_gecerli("a/b") and not SA.konu_gecerli("a/+") and not SA.konu_gecerli("a/#")
       and not SA.konu_gecerli(""))
    ok("kullanici_coz: ad:parola:rw / :r / rolsuz / parolada ':'",
       SA.kullanici_coz("kart:pw:rw") == ("kart", ("pw", "rw"))
       and SA.kullanici_coz("cihaz:pw2:r") == ("cihaz", ("pw2", "r"))
       and SA.kullanici_coz("x:pw") == ("x", ("pw", "rw"))
       and SA.kullanici_coz("x:a:b") == ("x", ("a:b", "rw"))
       and SA.kullanici_coz("x:a:b:r") == ("x", ("a:b", "r")))
    ok("kullanici_coz: parolasiz ya da adsiz -> ValueError",
       hata_verir(lambda: SA.kullanici_coz("x")) and hata_verir(lambda: SA.kullanici_coz(":pw")))
    ok("gecersiz rol -> ValueError",
       hata_verir(lambda: SA.SahteAraci("127.0.0.1", 0, {"x": ("p", "w")})))
    satir = SA.olay_satiri({"t": 5.0, "i": 0, "tur": "publish", "konu": "ok/x", "yuk": b"GIZLI-YUK"}, 2.0)
    ok("olay_satiri: yuk icerigi basilmaz (yalniz boyut), zaman aracı acilisina gore",
       "GIZLI" not in satir and "<9 bayt>" in satir and "3.000" in satir, satir)


def _sa_kimlik(a) -> None:
    port = a.port

    def dene(kul, par, **kw):
        c = mq.Istemci("127.0.0.1", port, False, kul, par, zaman_asimi=3.0, **kw)
        try:
            c.baglan()
            return 0, c
        except mq.BaglantiReddedildi as e:
            return e.kod, None
    ok("yanlis parola -> CONNACK 5", dene("kart", "yanlis")[0] == 5)
    ok("bilinmeyen kullanici -> CONNACK 5", dene("yok-kisi", "kpw-1")[0] == 5)
    ok("kimliksiz baglanti (kullanici tanimliyken) -> CONNACK 5", dene(None, None)[0] == 5)
    ok("parolasiz baglanti -> CONNACK 5", dene("kart", None)[0] == 5)
    kod, c = dene("kart", "kpw-1", istemci_id="ok-test", keepalive=7)
    ok("dogru kimlik -> CONNACK 0", kod == 0)
    if c:
        c.kapat()
    sonuclar = [x["sonuc"] for x in a.baglantilar]
    ok("her CONNECT kaydedildi: 4 red + 1 kabul", sonuclar == [5, 5, 5, 5, 0], str(sonuclar))
    k = a.baglantilar[-1]
    ok("kayit: istemci kimligi, keepalive 7, temiz oturum, kullanici adi, vasiyet yok",
       (k["istemci_id"], k["keepalive"], k["temiz"], k["kullanici"], k["will"], k["will_konu"])
       == ("ok-test", 7, True, "kart", False, None), str(k))
    a.olay_bekle("disconnect", 1.0, istemci="ok-test")
    ok("reddedilen CONNECT baglanti birakmaz; nazik kapanan istemci de listeden duser",
       a.bagli_istemciler() == [])

    h = Ham(port)
    rc = h.baglan("ok-w", ka=5, kul="kart", par="kpw-1", will=("ok/vsy/durum", b"\x00VASIYET\xff", 1, True))
    k = a.baglantilar[-1]
    ok("vasiyetli CONNECT kaydi: konu, yuk (ikili), QoS 1, retain, keepalive 5, temiz",
       rc == 0 and (k["will_konu"], k["will_yuk"], k["will_qos"], k["will_retain"], k["keepalive"],
                    k["temiz"]) == ("ok/vsy/durum", b"\x00VASIYET\xff", 1, True, 5, True), str(k))
    h.nazik_kapat()
    h2 = Ham(port)
    rc = h2.baglan("ok-nc", temiz=False, kul="kart", par="kpw-1")
    ok("temiz oturum bayragi 0 kaydedilir", rc == 0 and a.baglantilar[-1]["temiz"] is False)
    h2.nazik_kapat()
    h3 = Ham(port)
    ok("bos istemci kimligi + temiz=0 -> CONNACK 2",
       h3.baglan("", temiz=False, kul="kart", par="kpw-1") == 2)
    h4 = Ham(port)
    ok("bos istemci kimligi + temiz=1 -> aracı kimlik atar (CONNACK 0)",
       h4.baglan("", kul="kart", par="kpw-1") == 0 and a.baglantilar[-1]["istemci_id"].startswith("sahte-"))
    h4.nazik_kapat()
    ok("parola hicbir kayda ve olaya girmez",
       not any(p in repr(a.baglantilar) + repr(a.olaylar) for p in ("kpw-1", "cpw-2", "dpw-3", "yanlis")))
    ok("olay gunlugu: connect olaylari sonuc kodlariyla, sira ve time.monotonic() damgalari artan",
       [o["sonuc"] for o in a.olaylar_sec("connect")][:5] == [5, 5, 5, 5, 0]
       and all(a.olaylar[j]["i"] == j for j in range(len(a.olaylar)))
       and all(a.olaylar[j]["t"] <= a.olaylar[j + 1]["t"] for j in range(len(a.olaylar) - 1)))


def _sa_acl(a) -> None:
    b0 = len(a.olaylar)
    sub = Ham(a.port)
    sub.baglan("acl-sub", kul="diger", par="dpw-3")
    sub.abone("ok/acl/#")
    r = Ham(a.port)
    rc = r.baglan("acl-r", kul="cihaz", par="cpw-2")
    ok("'r' kullanicisi baglanabilir ve abone olabilir", rc == 0 and r.abone("ok/acl/#") == 1)
    w = Ham(a.port)
    w.baglan("acl-w", kul="diger", par="dpw-3")
    w.yayinla("ok/acl/x", b"rw")
    m = r.yayin_al(2.0)
    ok("rw kullanicisinin yayini 'r' aboneye ulasir (retain=0)",
       m is not None and m[0] == "ok/acl/x" and m[1] == b"rw" and m[2] is False, str(m))
    sub.yayin_al(1.0)                                    # sub'in kopyasi
    r.yayinla("ok/acl/yetkisiz", b"HACK", qos=1, retain=True, no=9)
    paketler, kapandi = r.bosalt(2.0)
    ok("'r' kullanicisi PUBLISH ederse baglanti KESILIR, PUBACK dahi gelmez",
       kapandi and not any(p[0] >> 4 == 4 for p in paketler), f"{kapandi} {paketler}")
    ok("acl_red + disconnect(neden acl) olaylari",
       a.olay_bekle("acl_red", 1.0, b0, istemci="acl-r") is not None
       and a.olay_bekle("disconnect", 1.0, b0, istemci="acl-r", neden="acl") is not None)
    ok("reddedilen yayin DAGITILMADI ve retained'a GIRMEDI",
       sub.yayin_al(0.5) is None and a.retained_al("ok/acl/yetkisiz") is None
       and not a.olaylar_sec("publish", b0, konu="ok/acl/yetkisiz"))
    for h in (sub, w):
        h.nazik_kapat()


def _sa_yayin(a) -> None:
    pub = Ham(a.port)
    pub.baglan("pub", kul="kart", par="kpw-1")
    pub.yayinla("ok/r1/durum", b"A", qos=0, retain=True)
    pub.yayinla("ok/r2/durum", b"B", qos=1, retain=True, no=4242)
    p = pub.paket(2.0)
    ok("QoS 1 PUBLISH -> yayinciya PUBACK, AYNI paket numarasiyla (4242)",
       p is not None and p[0] == 0x40 and struct.unpack(">H", p[1])[0] == 4242, str(p))
    ok("`publish` olayi: istemci, konu, yuk, qos, retain kaydedildi",
       a.olay_bekle("publish", 2.0, konu="ok/r2/durum", yuk=b"B", qos=1, retain=True, istemci="pub") is not None)

    s1 = Ham(a.port)
    s1.baglan("s1", kul="cihaz", par="cpw-2")
    ok("abonelik: joker filtre 'ok/+/durum' QoS 1 verildi", s1.abone("ok/+/durum", 1) == 1)
    d = {m[0]: m for m in (s1.yayin_al(2.0), s1.yayin_al(2.0)) if m}
    ok("abone olunca retained mesajlar iletilir (retain=1) — ikisi de, bir kez",
       set(d) == {"ok/r1/durum", "ok/r2/durum"} and all(m[2] for m in d.values()), str(sorted(d)))
    ok("retained iletim QoS = min(yayin, abonelik): QoS0 yayin QoS 0, QoS1 yayin QoS 1 (paket no ile)",
       d["ok/r1/durum"][3] == 0 and d["ok/r2/durum"][3] == 1 and bool(d["ok/r2/durum"][4]))
    s0 = Ham(a.port)
    s0.baglan("s0", kul="cihaz", par="cpw-2")
    ok("QoS 0 abonelik: verilen QoS 0", s0.abone("ok/+/durum", 0) == 0)
    d0 = {m[0]: m for m in (s0.yayin_al(2.0), s0.yayin_al(2.0)) if m}
    ok("QoS 0 abonelik: QoS 1 retained mesaj QoS 0 olarak iner (min)",
       d0["ok/r2/durum"][3] == 0 and d0["ok/r2/durum"][4] is None, str(d0.get("ok/r2/durum")))

    pub.yayinla("ok/r1/durum", b"C", qos=1, retain=False, no=7)
    pub.paket(1.0)
    m1, m0 = s1.yayin_al(2.0), s0.yayin_al(2.0)
    ok("canli iletimde retain bayragi 0 (3.1.1); QoS 1 abone QoS 1, QoS 0 abone QoS 0 alir",
       m1 is not None and m1[1] == b"C" and m1[2] is False and m1[3] == 1
       and m0 is not None and m0[1] == b"C" and m0[2] is False and m0[3] == 0, f"{m1} {m0}")
    ok("retained deposu canli (retain=0) yayindan ETKILENMEDI", a.retained_al("ok/r1/durum") == (b"A", 0))

    s2 = Ham(a.port)
    s2.baglan("s2", kul="cihaz", par="cpw-2")
    s2.abone("ok/#", 1)
    s2.yayin_al(1.0)
    s2.yayin_al(1.0)                                    # retained'lari bosalt
    pub.yayinla("ok/r1/x/y", b"derin")
    pub.yayinla("xx/aa", b"disarida")
    pub.yayinla("ok", b"ust")
    gelen = [s2.yayin_al(1.0) for _ in range(3)]
    ok("'ok/#': derin konu ve 'ok' (ust seviye) gelir; 'xx/aa' gelmez",
       [m[0] if m else None for m in gelen] == ["ok/r1/x/y", "ok", None], str(gelen))
    ok("'ok/+/durum' derin konuyu ('ok/r1/x/y') ve 'ok'u almaz",
       all(m is None or m[0] not in ("ok/r1/x/y", "ok", "xx/aa") for m in
           [s1.yayin_al(0.5) for _ in range(2)]))

    pub.yayinla("ok/r1/durum", b"", retain=True)
    a.olay_bekle("publish", 2.0, konu="ok/r1/durum", yuk=b"")
    s1.yayin_al(0.5)                                    # bos yuklu canli kopya (s1, s2 aldi)
    s0.yayin_al(0.5)
    ok("bos yuklu retained yayin o konunun retained'ini SILER", a.retained_al("ok/r1/durum") is None
       and a.retained_al("ok/r2/durum") == (b"B", 1))
    s3 = Ham(a.port)
    s3.baglan("s3", kul="cihaz", par="cpw-2")
    s3.abone("ok/+/durum", 1)
    d3 = [s3.yayin_al(1.0), s3.yayin_al(0.5)]
    ok("silinen retained yeni aboneye gelmez (yalniz 'ok/r2/durum')",
       d3[0] is not None and d3[0][0] == "ok/r2/durum" and d3[1] is None, str(d3))

    ok("gecersiz filtre ('a/#/b') -> SUBACK 0x80", s3.abone("a/#/b", 1) == 0x80)
    ok("QoS 2 istenen abonelik QoS 1'e indirilir (QoS 2 yok)", s3.abone("ok/q2x/#", 2) == 1)
    s1.gonder(bytes([0xA2]) + _uz(2 + len(_dz("ok/+/durum"))) + struct.pack(">H", 99) + _dz("ok/+/durum"))
    ub = s1.paket(1.0)
    ok("UNSUBSCRIBE -> UNSUBACK (ayni no); sonra o filtreye yayin gelmez",
       ub is not None and ub[0] == 0xB0 and ub[1] == struct.pack(">H", 99), str(ub))
    pub.yayinla("ok/r9/durum", b"yeni")
    s2g = [s2.yayin_al(1.0), s2.yayin_al(1.0)]
    ok("abonelik kalkinca s1'e mesaj gelmez; 'ok/#' abonesi s2 hepsini alir",
       s1.yayin_al(0.5) is None and [m[0] if m else None for m in s2g] == ["ok/r1/durum", "ok/r9/durum"],
       str(s2g))

    c = mq.Istemci("127.0.0.1", a.port, False, "diger", "dpw-3", zaman_asimi=3.0)
    c.baglan()
    c.abone("ok/h/#", 1)
    pub.yayinla("ok/h/x", b"merhaba", qos=1, no=11)
    m = c.bekle(2.0)
    ok("mq.Istemci ile uctan uca: abone ol, QoS1 yayin al (PUBACK istemciden gider)",
       m == ("ok/h/x", b"merhaba", False))
    c.kapat()

    q2 = Ham(a.port)
    q2.baglan("q2", kul="kart", par="kpw-1")
    q2.gonder(bytes([0x34]) + _uz(len(_dz("ok/q2")) + 2 + 1) + _dz("ok/q2") + struct.pack(">H", 3) + b"x")
    ok("QoS 2 PUBLISH desteklenmez: baglanti kesilir (sessizce kabul edilmez)", q2.bosalt(1.5)[1])
    for h in (pub, s0, s1, s2, s3):
        h.nazik_kapat()


def _sa_vasiyet(a) -> None:
    # --- keepalive zaman asimi -> vasiyet
    b0 = len(a.olaylar)
    dinle = Ham(a.port)
    dinle.baglan("v-dinle", kul="diger", par="dpw-3")
    for f in ("ok/will/#", "ok/will2/#", "ok/will3/#", "ok/will4/#"):
        dinle.abone(f, 1)
    sess = Ham(a.port)
    sess.baglan("ka-1", ka=1, kul="kart", par="kpw-1", will=("ok/will/durum", b"LWT-KA", 1, True))
    t0 = sess.t_connect
    o = a.olay_bekle("will_published", 5.0, b0, istemci="ka-1")
    dt = (o["t"] - t0) if o else -1.0
    ok("keepalive 1 s: sessiz istemci icin vasiyet 1.5 x keepalive icinde yayinlandi (>= 1.5, <= 1.5 + 0.6 s)",
       o is not None and 1.45 <= dt <= 2.1 and o["neden"] == "keepalive", f"{dt:.2f} s")
    m = dinle.yayin_al(2.0)
    ok("vasiyet aboneye ulasti: konu, yuk, QoS 1 (paket no ile), canli iletimde retain=0",
       m is not None and m[0] == "ok/will/durum" and m[1] == b"LWT-KA" and m[2] is False and m[3] == 1
       and bool(m[4]), str(m))
    ok("vasiyet retain bayragi retained deposuna yazar", a.retained_al("ok/will/durum") == (b"LWT-KA", 1))
    ok("disconnect olayi neden 'keepalive'; sessiz istemcinin soketi kapatildi",
       a.olay_bekle("disconnect", 1.0, b0, istemci="ka-1", neden="keepalive") is not None
       and sess.bosalt(1.0)[1])

    # --- PINGREQ ile canli tutulan istemci vasiyet YAYINLAMAZ; DISCONNECT -> vasiyet yok
    b1 = len(a.olaylar)
    pg = Ham(a.port)
    pg.baglan("ka-2", ka=1, kul="kart", par="kpw-1", will=("ok/will2/durum", b"LWT-DC", 1, True))
    pongs, bitis = 0, time.monotonic() + 2.6
    while time.monotonic() < bitis:                   # 1.5 s'lik pencerenin ~2 kati
        pg.gonder(b"\xc0\x00")
        p = pg.paket(1.0)
        pongs += bool(p and p[0] == 0xD0 and p[1] == b"")
        time.sleep(0.5)
    ok("PINGREQ -> PINGRESP; ping atan istemci 1.5 x keepalive'i asinca da dusurulmez, vasiyet yok",
       pongs >= 4 and "ka-2" in a.bagli_istemciler() and not a.olaylar_sec("will_published", b1),
       f"{pongs} PINGRESP")
    pg.gonder(b"\xe0\x00")
    od = a.olay_bekle("disconnect", 2.0, b1, istemci="ka-2")
    time.sleep(0.6)
    ok("DISCONNECT: disconnect olayi neden 'disconnect', vasiyet YAYINLANMADI, retained'a yazilmadi",
       od is not None and od["neden"] == "disconnect" and not a.olaylar_sec("will_published", b1)
       and a.retained_al("ok/will2/durum") is None and dinle.yayin_al(0.3) is None)
    pg.s.close()

    # --- ani kopus (DISCONNECT yok) -> vasiyet
    b2 = len(a.olaylar)
    ab = Ham(a.port)
    ab.baglan("ka-3", ka=60, kul="kart", par="kpw-1", will=("ok/will3/durum", b"LWT-KOPUS", 1, True))
    t_kes = time.monotonic()
    ab.s.close()
    o = a.olay_bekle("will_published", 3.0, b2, istemci="ka-3")
    ok("ani kopus (DISCONNECT'siz soket kapanisi): vasiyet hemen (< 1 s) yayinlandi, neden 'kopus'",
       o is not None and o["neden"] == "kopus" and o["t"] - t_kes < 1.0, f"{o and o['t'] - t_kes:.3f} s")
    m = dinle.yayin_al(2.0)
    ok("ani kopus vasiyeti aboneye ulasti ve retained'a yazildi",
       m is not None and m[:2] == ("ok/will3/durum", b"LWT-KOPUS")
       and a.retained_al("ok/will3/durum") == (b"LWT-KOPUS", 1), str(m))

    # --- ayni kimlik: takeover
    b3 = len(a.olaylar)
    eski = Ham(a.port)
    eski.baglan("dup", ka=60, kul="kart", par="kpw-1", will=("ok/will4/durum", b"LWT-TAKEOVER", 1, False))
    yeni = Ham(a.port)
    rc = yeni.baglan("dup", ka=60, kul="kart", par="kpw-1")
    o = a.olay_bekle("will_published", 3.0, b3, istemci="dup")
    ok("ayni kimlikle ikinci baglanti eskisini dusurur: eskinin vasiyeti yayinlanir (neden 'takeover'), "
       "yeni baglanti kabul edilir", rc == 0 and o is not None and o["neden"] == "takeover"
       and eski.bosalt(1.0)[1] and a.bagli_istemciler().count("dup") == 1)
    m = dinle.yayin_al(2.0)
    ok("takeover vasiyeti aboneye ulasti; retain=0 oldugundan retained'a YAZILMADI",
       m is not None and m[:2] == ("ok/will4/durum", b"LWT-TAKEOVER")
       and a.retained_al("ok/will4/durum") is None, str(m))
    yeni.nazik_kapat()
    dinle.nazik_kapat()

    # --- Condition: bekleyen uyanir, zaman asimi None dondurur
    t = time.monotonic()
    bos = a.olay_bekle("yok-boyle-olay", 0.3)
    gecen = time.monotonic() - t
    threading_baslat = threading.Timer(0.2, lambda: a.yayinla("ok/tetik", b"x"))
    threading_baslat.start()
    t = time.monotonic()
    uyanan = a.olay_bekle("arac_yayin", 3.0, konu="ok/tetik")
    uyanma = time.monotonic() - t
    ok("olay_bekle: olmayan olay icin zaman asiminda None (0.3 s); Condition olay gelince hemen uyandirir",
       bos is None and 0.25 <= gecen < 1.0 and uyanan is not None and uyanma < 1.0,
       f"{gecen:.2f} s, {uyanma:.2f} s")


def _sa_kesinti() -> None:
    print("\n-- sahte aracı: kesinti (kapali_tut) + AYNI portta yeniden acma --")
    a = SA.SahteAraci("127.0.0.1", 0, SA_KUL).start()
    try:
        port = a.port
        pub = Ham(port)
        pub.baglan("k-pub", kul="kart", par="kpw-1")
        pub.yayinla("ok/kes/durum", b"RET", retain=True)
        a.olay_bekle("publish", 2.0, konu="ok/kes/durum")
        vs = Ham(port)
        vs.baglan("k-vsy", ka=30, kul="kart", par="kpw-1", will=("ok/kes/vasiyet", b"X", 1, True))
        c = mq.Istemci("127.0.0.1", port, False, "diger", "dpw-3", istemci_id="k-ist", zaman_asimi=3.0)
        c.baglan()
        c.abone("ok/kes/#", 1)
        c.bekle(1.0)                                       # retained'i al
        ok("kesinti oncesi: 3 istemci bagli", a.bagli_istemciler() == ["k-ist", "k-pub", "k-vsy"],
           str(a.bagli_istemciler()))
        b0 = len(a.olaylar)
        a.kapali_tut()
        try:
            c.bekle(2.0)
            koptu = False
        except mq.BaglantiKoptu:
            koptu = True
        ok("kapali_tut(): bagli istemciler DUSURULUR (istemci BaglantiKoptu gorur)",
           koptu and a.bagli_istemciler() == [] and vs.bosalt(0.5)[1])
        ok("kapali_tut(): yeni baglanti REDDEDILIR (dinleme yok)",
           hata_verir(lambda: socket.create_connection(("127.0.0.1", port), timeout=1), OSError))
        ok("kesintide VASIYET YAYINLANMAZ (aracı kendisi yok); olaylar: arac_kapali + neden 'sunucu_kapali'",
           not a.olaylar_sec("will_published", b0) and a.olay_bekle("arac_kapali", 0.5, b0) is not None
           and len(a.olaylar_sec("disconnect", b0, neden="sunucu_kapali")) == 3)
        a.ac()
        ok("ac(): AYNI portta yeniden dinler (arac_acik olayi)", a.port == port
           and a.olay_bekle("arac_acik", 1.0, b0) is not None)
        c2 = mq.Istemci("127.0.0.1", port, False, "diger", "dpw-3", istemci_id="k-ist2", zaman_asimi=3.0)
        c2.baglan()
        c2.abone("ok/kes/#", 1)
        m = c2.bekle(2.0)
        ok("kesintiden sonra baglanti calisir; retained deposu KORUNDU (kalici aracı gibi)",
           m == ("ok/kes/durum", b"RET", True), str(m))
        ok("ac() ikinci kez cagrilirsa zararsiz", (a.ac() or True) and a.port == port)
        c2.kapat()
        sayi = len(a.olaylar_sec("arac_kapali"))
        a.stop()
        a.stop()
        ok("stop() bir kez daha cagrilirsa zararsiz; baglanti reddedilir",
           len(a.olaylar_sec("arac_kapali")) == sayi + 1
           and hata_verir(lambda: socket.create_connection(("127.0.0.1", port), timeout=1), OSError))
    finally:
        a.stop()


def bolum_sahte_araci() -> None:
    bolum_sahte_araci_birim()
    print("\n-- sahte aracı: kimlik, ACL, retained, joker karakter, QoS 1, vasiyet --")
    a = SA.SahteAraci("127.0.0.1", 0, SA_KUL).start()
    ok("start(): rastgele port atandi (port 0 -> gercek port)", a.port > 0)
    try:
        _sa_kimlik(a)
        _sa_acl(a)
        _sa_yayin(a)
        _sa_vasiyet(a)
    finally:
        a.stop()
    _sa_kesinti()
    eski_argv = sys.argv
    sys.argv = ["sahte_araci.py", "--kullanici", "parolasiz"]
    hata = io.StringIO()
    try:
        with contextlib.redirect_stderr(hata):
            kod = SA.main()
    finally:
        sys.argv = eski_argv
    ok("CLI: bicimsiz --kullanici cikis kodu 2 ve hata mesaji", kod == 2 and "HATA" in hata.getvalue())


def main() -> int:
    print("=" * 78)
    print("  1E  BILDIRIM ZARFI + CHACHA20-POLY1305 + MQTT ISTEMCISI + DINLEYICI")
    print("=" * 78)
    bolum_chacha()
    bolum_oynama()
    bolum_zarf()
    bolum_bilgi()
    bolum_bilgi_al()
    bolum_mqtt_cekirdek()
    bolum_araci()
    bolum_baglanti_hatalari()
    bolum_tls_yolu()
    bolum_dinleyici()
    bolum_sahte_araci()
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
