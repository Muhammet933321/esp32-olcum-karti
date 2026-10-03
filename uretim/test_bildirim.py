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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gercek_dizin_koru                                   # noqa: E402
_KORUMA = gercek_dizin_koru.koru()   # LOCALAPPDATA gecici dizine — gercek PC dizinine asla yazilmaz
import os                                                  # noqa: E402
os.environ["OLCUM_TOAST_YOK"] = "1"  # 4E: sinamada GERCEK Windows bildirimi / kayit defteri yazimi YOK
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
    # S7: Python json.loads NaN/Infinity'yi KABUL eder, JS JSON.parse reddeder; kart sonlu
    # olmayani zaten basmaz. Iki istemci ayni zarfi farkli yorumlamasin.
    ok("S7: etiket gecerli ama icerikte NaN / Infinity / -Infinity -> ValueError (JS ile ayni)",
       all(hata_verir(lambda d=d: bildirim.zarf_ac(ANAHTAR, KONU_OLAY, ham(d)))
           for d in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}')))
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


# ── 4E: PC bildirimleri (pc_bildirim.py · windows_bildirim.py · bildirim_metin.py) ──────────
class _SahteCikis:
    """Bildirim cikisi yerine: cagrilari kaydeder (GERCEK toast YOK)."""
    yol = "sahte"

    def __init__(self):
        self.cagri: list[tuple] = []

    def goster(self, etiket, baslik, metin, sessiz=False):
        self.cagri.append((etiket, baslik, metin, sessiz))

    def kapat(self):
        pass


class _Saat:
    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


def _g(durum: int, oturum: int) -> str:
    """Kartin `G` satiri (13 alan, olcum-karti-a3.ino kayit_durum_bas)."""
    return f"G {durum} {oturum} 100 101 50 120 10 0 900 25000 3 400 0"


def _mantik(acik=None, dil="tr", kalici=None):
    import pc_bildirim as PB
    cikis, saat, yay = _SahteCikis(), _Saat(), []
    acik = acik or {s: True for s in PB.SINIFLAR}
    m = PB.Mantik(cikis, yayinla=yay.append, ayar=lambda: (acik, dil, None), saat=saat,
                  duvar=lambda: 1_790_000_000.0, kalici=kalici)
    m.mqtt_bagli_oldu(True)
    return m, cikis, saat, yay


def _durum4e(k: int, o: int = 7, c: int = 1, a: int = 77, t: int = 1_790_000_000, y: int = 1) -> dict:
    if c == 0:
        return {"c": 0, "a": a}
    return {"c": 1, "a": a, "t": t, "k": k, "o": o, "y": y, "d": 5, "e": 0, "f": "A3-4E"}


def _olay4e(n: int, o: str, a: int = 77, **alan) -> dict:
    return {"n": n, "a": a, "t": 1_790_000_100, "o": o, **alan}


def bolum_4e_metin() -> None:
    import re
    import bildirim_metin as BM
    print("\n-- 4E: bildirim metinleri (TR/EN, firmware olay adlari, sozluk.js ile ayni) --")
    h = (KOK / "kod" / "olcum-karti-a3" / "bildirim.h").read_text(encoding="utf-8")
    olaylar = set(re.findall(r'bld__olay_ac\([^;"]*"([a-z_]+)"\)', h))
    eksik = [o for o in sorted(olaylar)
             if not (o in BM.OLAY_ANAHTAR and BM.METIN.get(BM.OLAY_ANAHTAR[o], {}).get("tr")
                     and BM.METIN[BM.OLAY_ANAHTAR[o]].get("en"))]
    ok("4E: kartin HER olay adinin (bildirim.h bld__olay_ac) TR VE EN bildirim metni var",
       len(olaylar) >= 6 and not eksik, f"{sorted(olaylar)} eksik={eksik}")
    yer = re.compile(r"\{([a-z_]+)\}")
    bozuk = [k for k, v in BM.METIN.items()
             if not (v.get("tr") and v.get("en")) or set(yer.findall(v["tr"])) != set(yer.findall(v["en"]))]
    ok("4E: her metnin bos olmayan TR ve EN'i var, yer tutuculari iki dilde AYNI",
       not bozuk and len(BM.METIN) > 30, f"bozuk={bozuk}")
    soz = (KOK / "ortak" / "src" / "sozluk.js").read_text(encoding="utf-8")
    js = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(
        r'"((?:sebep|pil\.durum|oturum\.tur)\.[a-z0-9]+)":\s*S\("((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"\)', soz)}
    py = {k: (v["tr"], v["en"]) for k, v in BM.METIN.items()
          if k.startswith(("sebep.", "pil.durum.", "oturum.tur."))}
    farkli = [k for k in py if js.get(k) != py[k]]
    eksik_py = [k for k in js if k not in py and k != "sebep.acik"]
    ok("4E: ortak aileler (sebep.* / pil.durum.* / oturum.tur.*) sozluk.js ile BIREBIR ayni metin",
       len(js) >= 18 and not farkli and not eksik_py, f"farkli={farkli} eksik={eksik_py}")
    ok("4E: metin(): dil secimi, yer tutucu, bilinmeyen anahtar ATMAZ (anahtar doner), kod_metni bilinmeyen kod",
       BM.metin("bld.kopuk", "en", oturum=7).startswith("No news from the board") and "7" in
       BM.metin("bld.kopuk", "tr", oturum=7) and BM.metin("yok.boyle", "tr") == "yok.boyle"
       and BM.kod_metni("sebep.", 99, "tr") == "bilinmeyen sebep (99)"
       and BM.kod_metni("sebep.", 5, "en") == "board restarted" and BM.metin("bld.dolu", "xx") == "Bellek doldu, kayıt durdu")


def bolum_4e_mantik() -> None:
    import pc_bildirim as PB
    print("\n-- 4E: karar katmani (sahte cikis + sahte saat; ag yok) --")
    # kopuk: yalniz kayit surerken; donunce AYNI bildirim (etiket) guncellenir
    m, c, s, _ = _mantik()
    m.mqtt_mesaj("durum", _durum4e(k=1, o=0))
    m.mqtt_mesaj("durum", _durum4e(0, c=0))
    sessiz_kayitsiz = list(c.cagri)
    m.mqtt_mesaj("durum", _durum4e(k=2, o=7))
    m.mqtt_mesaj("durum", _durum4e(0, c=0))
    m.mqtt_mesaj("durum", _durum4e(0, c=0))             # retained yeniden teslim: tekrar acilmaz
    kopuk = list(c.cagri)
    m.mqtt_mesaj("durum", _durum4e(k=2, o=7))
    ok("4E: vasiyet/{c:0} kayit YOKKEN bildirim YOK; kayit surerken 'Karttan haber yok' (BIR KEZ, etiket "
       "'baglanti'); kart donunce AYNI etiketle 'yeniden baglandi — kayit suruyor'",
       sessiz_kayitsiz == [] and len(kopuk) == 1 and kopuk[0][0] == "baglanti"
       and "Karttan haber yok" in kopuk[0][2] and "oturum 7" in kopuk[0][2]
       and len(c.cagri) == 2 and c.cagri[1][0] == "baglanti" and "yeniden bağlandı" in c.cagri[1][2]
       and "kayıt sürüyor" in c.cagri[1][2] and c.cagri[0][1] == "Ölçüm kartı", str(c.cagri))
    # ev interneti: kart yerelde gorunuyor, araci cevrimdisi diyor
    m, c, s, _ = _mantik()
    m.mqtt_mesaj("durum", _durum4e(k=2, o=9))
    m.yerel_satir(_g(2, 9))
    m.mqtt_mesaj("durum", _durum4e(0, c=0))
    s.t += PB.YEREL_ERISIM_SN + 1
    m.tik()
    m.yerel_satir(_g(2, 9))
    m.tik()
    m.mqtt_mesaj("durum", _durum4e(k=2, o=9))
    metinler = [x[2] for x in c.cagri]
    ok("4E: kart yerelde gorunurken araci 'cevrimdisi' -> 'Ev interneti koptu, kart calisiyor'; yerel de "
       "susunca AYNI bildirim 'Karttan haber yok'a, yerel donunce yine 'ev interneti'ne, kart araciya "
       "donunce 'yeniden baglandi'ya guncellenir (hep etiket 'baglanti')",
       len(c.cagri) == 4 and {x[0] for x in c.cagri} == {"baglanti"} and "Ev interneti koptu" in metinler[0]
       and "Karttan haber yok" in metinler[1] and "Ev interneti koptu" in metinler[2]
       and "yeniden bağlandı" in metinler[3], str(metinler))
    # yalniz yerel yol (araci yok): yerel satirlar susarsa, kayit suruyorsa
    m, c, s, _ = _mantik()
    m.mqtt_bagli_oldu(False)
    m.yerel_satir(_g(2, 5))
    s.t += PB.YEREL_KOPUK_SN + 1
    m.tik()
    m.tik()
    yerel_kopuk = list(c.cagri)
    m.yerel_satir(_g(2, 5))
    m.tik()
    m2, c2, s2, _ = _mantik()
    m2.mqtt_bagli_oldu(False)
    m2.yerel_satir(_g(1, 0))
    s2.t += PB.YEREL_KOPUK_SN + 1
    m2.tik()
    ok("4E: araci yokken (MQTT ayarsiz / bagli degil) kayit surerken yerel satirlar susarsa 'Karttan haber "
       "yok' (BIR KEZ), satirlar donunce ayni bildirim 'yeniden baglandi'; kayit yokken HICBIR sey",
       len(yerel_kopuk) == 1 and "yerel bağlantı da koptu" in yerel_kopuk[0][2] and len(c.cagri) == 2
       and c.cagri[1][0] == "baglanti" and "yeniden bağlandı" in c.cagri[1][2] and c2.cagri == [],
       str(c.cagri))
    m, c, s, _ = _mantik()
    m.mqtt_mesaj("durum", _durum4e(k=2, o=4))
    s.t += 1
    m.yerel_satir(_g(1, 0))
    m.mqtt_mesaj("durum", _durum4e(0, c=0))
    ok("4E: 'kayit suruyor mu' HANGI haber daha yeniyse ondan (araci k=2 dedikten sonra yerel G kaydin "
       "bittigini gosterdi -> vasiyette bildirim YOK)", c.cagri == [], str(c.cagri))
    # (a, n) yineleme
    m, c, s, _ = _mantik()
    m.mqtt_mesaj("olay", _olay4e(1, "deneme"))
    m.mqtt_mesaj("olay", _olay4e(1, "deneme"))
    m.mqtt_mesaj("olay", _olay4e(2, "kayit_bitti", sebep=1, oturum=7, nokta=321))
    m.mqtt_mesaj("olay", _olay4e(2, "kayit_bitti", sebep=1, oturum=7, nokta=321))
    ok("4E (PC16): MQTT icinde (a, n) ayni olay (QoS 1 yeniden teslim) TEK bildirim",
       len(c.cagri) == 2 and "Deneme" in c.cagri[0][2] and "kullanıcı durdurdu" in c.cagri[1][2]
       and "321" in c.cagri[1][2], str(c.cagri))
    # yollar arasi: yerel G gecisi + MQTT kayit_bitti -> tek bildirim, ayrintili olan sessizce gunceller
    m, c, s, _ = _mantik()
    m.yerel_satir(_g(2, 7))
    m.yerel_satir(_g(1, 7))
    s.t += 3
    m.mqtt_mesaj("olay", _olay4e(5, "kayit_bitti", sebep=1, oturum=7, nokta=321))
    ileri = list(c.cagri)
    m2, c2, s2, _ = _mantik()
    m2.mqtt_mesaj("olay", _olay4e(5, "kayit_bitti", sebep=1, oturum=7, nokta=321))
    m2.yerel_satir(_g(2, 7))
    m2.yerel_satir(_g(1, 7))
    ok("4E (PC16): ayni oturum sonu yerelden (G 2->1) VE MQTT'den: TEK acilir bildirim; once yerel gelirse "
       "MQTT'deki ayrintili metin AYNI etiketi SESSIZCE gunceller; once MQTT gelirse yerel duser",
       len(ileri) == 2 and ileri[0][0] == ileri[1][0] == "os-7" and ileri[0][3] is False
       and ileri[1][3] is True and "Kayıt bitti (oturum 7)" == ileri[0][2] and "321" in ileri[1][2]
       and len(c2.cagri) == 1, f"{ileri} | {c2.cagri}")
    m, c, s, _ = _mantik()
    m.mqtt_mesaj("olay", _olay4e(6, "kayit_bitti", sebep=2, oturum=8, nokta=9))
    m.mqtt_mesaj("olay", _olay4e(7, "dolu"))
    m.yerel_satir(_g(2, 8))
    m.yerel_satir(_g(3, 8))
    dolu = list(c.cagri)
    m, c, s, _ = _mantik()
    m.yerel_satir(_g(2, 7))
    m.yerel_satir(_g(1, 7))
    m.mqtt_mesaj("olay", _olay4e(8, "pil_bitti", durum=2, mah_milli=1234567, wh_milli=4567, sure_ms=3723000))
    m.mqtt_mesaj("olay", _olay4e(9, "kayit_bitti", sebep=4, oturum=7, nokta=50))
    ok("4E (PC16): bellek dolu (kayit_bitti sebep 2 + dolu + yerel G->3) TEK bildirim; pil testi bitisi "
       "yerel bitisi SESSIZCE sonucla (mAh, Wh, sure) gunceller, ardindan gelen kayit_bitti sebep 4 DUSER",
       len(dolu) == 1 and "Bellek doldu" in dolu[0][2] and len(c.cagri) == 2 and c.cagri[1][3] is True
       and c.cagri[0][0] == c.cagri[1][0] and "1234,6 mAh" in c.cagri[1][2] and "4,57 Wh" in c.cagri[1][2]
       and "1:02:03" in c.cagri[1][2], f"{dolu} | {c.cagri}")
    m, c, s, _ = _mantik()
    m.yerel_satir(_g(2, 7))
    m.yerel_satir(_g(1, 7))
    s.t += PB.PENCERE_SN + 1
    m.mqtt_mesaj("olay", _olay4e(1, "kayit_bitti", sebep=1, oturum=7, nokta=321))
    m.mqtt_mesaj("olay", _olay4e(2, "esik", deger=520, esik=500))
    s.t += PB.YAKIN_SN + 1
    m.mqtt_mesaj("olay", _olay4e(3, "esik", deger=530, esik=500))
    ok("4E (PC16): zaman penceresi — pencere disinda gelen ayni oturum sonu YENI bildirim; esik metni "
       "binde -> %, YAKIN_SN disinda tekrar eden esik yeni bildirim",
       len(c.cagri) == 4 and c.cagri[1][3] is False and "%52,0" in c.cagri[2][2]
       and "%50,0" in c.cagri[2][2] and c.cagri[3][0] != c.cagri[2][0], str(c.cagri))
    # yeniden basladi
    m, c, s, _ = _mantik()
    m.mqtt_mesaj("olay", _olay4e(1, "basladi", a=90, devam=0, oturum=0))
    sade = list(c.cagri)
    m.mqtt_mesaj("durum", _durum4e(k=2, o=12, a=90, y=2, t=1_790_003_600))
    m.mqtt_mesaj("olay", _olay4e(1, "basladi", a=91, devam=1, oturum=12))
    m.mqtt_mesaj("olay", _olay4e(2, "kayit_bitti", a=91, sebep=5, oturum=12, nokta=5))
    ok("4E: duz acilis (basladi devam=0, oturum yok) bildirim DEGIL; devam=1 'kayit kesildi ve suruyor'; "
       "kayit_bitti sebep 5 'Pil testi kesildi' + kartin son goruldugu saat",
       sade == [] and len(c.cagri) >= 2 and "kesildi ve sürüyor" in c.cagri[-2][2]
       and "Pil testi kesildi" in c.cagri[-1][2] and "son haber" in c.cagri[-1][2], str(c.cagri))
    # kacirilan (PC15)
    with tempfile.TemporaryDirectory() as d:
        kalici = Path(d) / "son.json"
        m, c, s, _ = _mantik(kalici=kalici)
        m.mqtt_mesaj("olay", _olay4e(1, "basladi", a=20, devam=0, oturum=0))
        m.mqtt_mesaj("olay", _olay4e(2, "deneme", a=20))
        m.mqtt_mesaj("olay", _olay4e(5, "deneme", a=20))
        k1 = [x for x in c.cagri if x[0] == "kacirilan"]
        m.mqtt_mesaj("olay", _olay4e(3, "deneme", a=21))
        k2 = [x for x in c.cagri if x[0] == "kacirilan"]
        m2, c2, _, _ = _mantik(kalici=kalici)
        m2.mqtt_mesaj("olay", _olay4e(3, "deneme", a=21))        # onceki calismada gorulmus
        m2.mqtt_mesaj("olay", _olay4e(6, "deneme", a=21))
        ok("4E (PC15): (a, n) bosluklari 'N olay kacirildi' (etiket 'kacirilan', birikerek); yeni acilista "
           "1..n-1; kopru yeniden acilinca son (a, n) diskten: gorulen DUSER, bosluk sayilir",
           len(k1) == 1 and "2 olay" in k1[0][2] and len(k2) == 2 and "4 olay" in k2[1][2] and m.kacirilan == 4
           and m2.kacirilan == 2 and len([x for x in c2.cagri if "Deneme" in x[2]]) == 1
           and json.loads(kalici.read_text()) == {"a": 21, "n": 6}, f"{c.cagri} | {c2.cagri}")
    # dil + yerel satir ayristirma
    m, c, s, _ = _mantik(dil="en")
    m.mqtt_mesaj("olay", _olay4e(3, "dolu"))
    gizli = "EK 3 " + "ab" * 32
    m.yerel_satir("G 2 7")
    m.yerel_satir("GA 1 2 3 4")
    m.yerel_satir(_g(2, 7) + " x")
    m.yerel_satir(gizli)
    ok("4E: dil 'en' -> Ingilizce metin ve baslik; yerel satirda yalniz TAM 13 alanli `G` ayristirilir, "
       "baska satirin icerigi (ör. EK anahtar satiri) SAKLANMAZ",
       c.cagri and c.cagri[0][1] == "Measurement board" and c.cagri[0][2] == "Storage full, recording stopped"
       and m._yerel_g is None and "ab" * 32 not in repr(vars(m)), str(c.cagri))
    # hata metni sinifi
    h = ssl.SSLCertVerificationError(1, "hostname 'gizli.araci.example' doesn't match")
    ok("4E: baglanti hatasi metni istisnadan DEGIL siniftan (TLS hatasi araci adini tasir)",
       PB.hata_sinifi(h) == "TLS sertifika/ad denetimi" and "gizli" not in PB.hata_sinifi(h)
       and PB.hata_sinifi(socket.gaierror(11001, "x")) == "ad cozulemedi"
       and PB.hata_sinifi(mq.BaglantiKoptu("araci.x kapatti")) == "baglanti koptu")


def bolum_4e_ayar() -> None:
    import pc_ayar
    import pc_bildirim as PB
    print("\n-- 4E: olay basina ac/kapa (ayar.json; 4C anahtarlariyla BIRLESIR) --")
    p = pc_ayar.veri_dizini() / pc_ayar.AYAR
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"esitleme_onay": False, "esitleme_aralik_s": 300}), encoding="utf-8")
    try:
        PB.ayar_yaz({"bitti": False, "kopuk": False})
        d = json.loads(p.read_text(encoding="utf-8"))
        acik, dil, uyari = PB.ayar_oku()
        cikis = _SahteCikis()
        m = PB.Mantik(cikis, saat=_Saat())
        m.mqtt_mesaj("durum", _durum4e(k=2, o=7))
        m.mqtt_mesaj("durum", _durum4e(0, c=0))
        m.mqtt_mesaj("olay", _olay4e(2, "kayit_bitti", sebep=1, oturum=7, nokta=3))
        m.mqtt_mesaj("olay", _olay4e(3, "esik", deger=600, esik=500))
        ok("4E: ayar_yaz bildirim anahtarlarini BIRLESTIRIR (esitleme_onay / aralik aynen); kapali siniflar "
           "(kopuk, bitti) bildirim VERMEZ, acik olan (esik) verir",
           d.get("esitleme_onay") is False and d.get("esitleme_aralik_s") == 300
           and d["bildirim"] == {"bitti": False, "kopuk": False} and acik["bitti"] is False
           and acik["esik"] is True and uyari is None and len(cikis.cagri) == 1 and "Eşitlenmemiş" in
           cikis.cagri[0][2], str(cikis.cagri))
        PB.ayar_yaz({}, dil="en")
        d2 = json.loads(p.read_text(encoding="utf-8"))
        dil_en = PB.ayar_oku()[1]
        p.write_text(json.dumps({"bildirim": {"bitti": "hayir"}}), encoding="utf-8")
        acik2, _, uyari2 = PB.ayar_oku()
        p.write_text("{bozuk", encoding="utf-8")
        acik3, _, uyari3 = PB.ayar_oku()
        yazamadi = hata_verir(lambda: PB.ayar_yaz({"bitti": True}))
        bozuk_kaldi = p.read_text(encoding="utf-8") == "{bozuk"
        ok("4E: dil ayari birlesir; true/false olmayan deger o sinifi ACIK sayar (+uyari); bozuk ayar.json'da "
           "hepsi acik (+uyari) ve ayar_yaz dosyanin USTUNE YAZMAZ; bilinmeyen sinif reddedilir",
           d2.get("bildirim_dil") == "en" and dil_en == "en" and d2["bildirim"] == {"bitti": False, "kopuk": False}
           and acik2["bitti"] is True and uyari2 and all(acik3.values()) and uyari3 and yazamadi
           and bozuk_kaldi and hata_verir(lambda: PB.ayar_yaz({"yok": True}))
           and hata_verir(lambda: PB.ayar_yaz({"esik": 1})))
    finally:
        p.unlink(missing_ok=True)


def bolum_4e_windows() -> None:
    import base64
    import windows_bildirim as WB
    print("\n-- 4E: Windows bildirimi (WinRT toast) betigi — GERCEK toast YOK --")
    giden: list[str] = []
    kayit: list[int] = []
    hatalar: list[str] = []
    s = WB.WindowsBildirim(Path(tempfile.gettempdir()), calistir=lambda b: giden.append(b) or 0,
                           kaydet=lambda: kayit.append(1), hata=hatalar.append)
    kotu = "kayıt <b>&'\"; Remove-Item C:\\ -Recurse #"
    s.goster("baglanti", "Ölçüm kartı", kotu)
    s.goster("baglanti", "Ölçüm kartı", "ikinci", sessiz=True)
    son = time.monotonic() + 5
    while len(giden) < 2 and time.monotonic() < son:
        time.sleep(0.02)
    b64 = giden[0].split("FromBase64String('")[1].split("'")[0] if giden else ""
    xml = base64.b64decode(b64).decode("utf-8") if b64 else ""
    ok("4E (PC13): toast betigi — Tag/Group (yerinde guncelleme), AUMID 'OlcumKarti.Kopru', ikinci SessizPopup; "
       "metin XML'e kacirilip YALNIZ base64 olarak girer (PowerShell komutu olarak yorumlanamaz)",
       len(giden) == 2 and "$t.Tag='baglanti'" in giden[0] and "$t.Group='olcum'" in giden[0]
       and "CreateToastNotifier('OlcumKarti.Kopru')" in giden[0] and "SuppressPopup=$false" in giden[0]
       and "SuppressPopup=$true" in giden[1] and "Remove-Item" not in giden[0]
       and "kayıt &lt;b&gt;&amp;'\"; Remove-Item" in xml and "<text>Ölçüm kartı</text>" in xml, xml[:160])
    k = WB.komut(giden[0]) if giden else []
    ok("4E: powershell -NoProfile -NonInteractive -EncodedCommand (UTF-16LE); kaynak adi kaydi BIR KEZ",
       k[:1] == [str(WB.POWERSHELL)] and "-EncodedCommand" in k and "-NoProfile" in k
       and base64.b64decode(k[-1]).decode("utf-16-le") == giden[0] and kayit == [1])
    ok("4E: etiket/grup bicimi denetlenir ([a-z0-9-], <= 16) — gecersiz etiket betige GIRMEZ",
       hata_verir(lambda: WB.betik("x'; kotu", "a", "b")) and hata_verir(lambda: WB.betik("a" * 17, "a", "b"))
       and hata_verir(lambda: WB.betik("ok", "a", "b", aumid="x'y")))
    s2 = WB.WindowsBildirim(Path(tempfile.gettempdir()), calistir=lambda b: 1, kaydet=lambda: None,
                            hata=hatalar.append)
    s2.goster("a1", "b", "c")
    s2.goster("a2", "b", "c")
    son = time.monotonic() + 5
    while not hatalar and time.monotonic() < son:
        time.sleep(0.02)
    time.sleep(0.2)
    s.kapat()
    s2.kapat()
    import subprocess as _sp
    asil_run, cagrildi = _sp.run, []
    _sp.run = lambda *a, **kw: cagrildi.append(a) or None
    try:
        s3 = WB.WindowsBildirim(Path(tempfile.gettempdir()))
        s3.goster("a3", "b", "c")
        time.sleep(0.3)
        s3.kapat()
    finally:
        _sp.run = asil_run
    y: list[str] = []
    WB.YokBildirim(y.append).goster("x", "b", "metin")
    ok("4E: powershell hatasi BIR KEZ soylenir; OLCUM_TOAST_YOK (sinama/zincir) iken alt surec HIC "
       "baslatilmaz; Windows disinda bildirim durum satiri olur",
       len(hatalar) == 1 and "powershell: 1" in hatalar[0] and s3.sinama and not cagrildi
       and s3.gosterilen == 1 and y == ["* bildirim: metin"], f"{hatalar} {cagrildi}")


class _Kart4E(http.server.BaseHTTPRequestHandler):
    """Sahte kart: /eslestir/bilgi (acik) + IMZALI /bildirim/bilgi (imza dogrulanir)."""
    kart: dict = {}

    def _ham(self, kod: int, govde: bytes) -> None:
        self.send_response(kod)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):                                       # noqa: N802
        k = type(self).kart
        yol = self.path.split("?")[0]
        if yol == "/eslestir/bilgi":
            return self._ham(200, json.dumps({"kimlik": k["kimlik"], "acilis": k["acilis"],
                                              "saat": 1}).encode())
        if yol == "/bildirim/bilgi":
            b = {a.lower(): v for a, v in self.headers.items()}
            try:
                sayac = int(b.get("x-sayac", "-1"))
            except ValueError:
                sayac = -1
            if b.get("x-cihaz") != str(k["n"]) or b.get("x-imza") != imza.imzala(
                    k["K"], "GET", "/bildirim/bilgi", [], k["acilis"], sayac, b""):
                k["imzasiz"] += 1
                return self._ham(401, b"imza")
            k["istek"] += 1
            if k["bilgi"] is None:
                return self._ham(404, b"bildirim ayarlanmamis")
            govde = bilgi_govde(k["bilgi"], K=k["K"], kimlik=k["kimlik"], n=k["n"], nonce=os.urandom(12))
            k["son_govde"] = govde
            return self._ham(200, govde)
        self._ham(404, b"")

    def log_message(self, *a):
        pass


class _Ham4E(Ham):
    def __init__(self, host: str, port: int):                # noqa: D107 — Ham'in ayni, adresli
        self.s = socket.create_connection((host, port), timeout=3)
        self.ayr = mq.Ayristirici()
        self.t_connect = 0.0
        self._no = 0


def _kosul(f, sure: float = 8.0) -> bool:
    son = time.monotonic() + sure
    while time.monotonic() < son:
        try:
            if f():
                return True
        except Exception:                                   # noqa: BLE001
            pass
        time.sleep(0.05)
    return bool(f())


def bolum_4e_iplik() -> None:
    import kart_wifi as KW
    import pc_bildirim as PB
    print("\n-- 4E: MQTT ipligi — sahte araci + sahte kart (imzali /bildirim/bilgi) + gercek WifiKart --")
    HOST, KUL = "127.83.41.7", "cihaz-sinama-4e"
    PAROLA, PAROLA_B = "araci-sinama-parola-4e!", "araci-sinama-yeni-4e?"
    ONEK_A, ONEK_B = "4e" * 16, "b4" * 16
    A1, A2, A3 = bytes(range(0x30, 0x50)), bytes(range(0x60, 0x80)), bytes(range(0x90, 0xB0))
    K4, KIMLIK4, N4, ACILIS4 = bytes(range(0x50, 0x70)), "4e4e0011aabbccdd", 2, "cd" * 16
    araci = SA.SahteAraci(HOST, 0, {"kart": ("kart-sinama-pw", "rw"), KUL: (PAROLA, "r")}).start()
    uri = f"mqtt://{HOST}:{araci.port}"
    kart = {"kimlik": KIMLIK4, "acilis": ACILIS4, "K": K4, "n": N4, "istek": 0, "imzasiz": 0,
            "son_govde": b"", "bilgi": {"u": uri, "k": KUL, "p": PAROLA, "o": ONEK_A, "a": A1.hex()}}
    sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", 0), type("_K4", (_Kart4E,), {"kart": kart}))
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    tmp = Path(tempfile.mkdtemp(prefix="okb4e-"))
    cdizin, pdizin = tmp / "cihaz", tmp / "pc"
    cdizin.mkdir()
    imza.Cihaz(cdizin / f"{KIMLIK4}.json", KIMLIK4, N4, K4, "pc-sinama", 0, ACILIS4).kaydet()

    def yay(onek, anahtar, son, icerik, retain=False):
        konu = f"ok/{onek}/{son}"
        araci.yayinla(konu, bildirim.zarf_kur(anahtar, konu, icerik), 1, retain)

    def kur(dizin, wifi_host):
        cikis, durumlar = _SahteCikis(), []
        m = PB.Mantik(cikis, yayinla=durumlar.append,
                      ayar=lambda: ({s: True for s in PB.SINIFLAR}, "tr", None),
                      kalici=dizin / "bildirim" / "son.json")
        pb = PB.PcBildirim(KW.WifiKart(wifi_host, dizin=cdizin), m, yayinla=durumlar.append,
                           veri_dizini=dizin, keepalive=5, sessizlik=999, yenile_en_az=0.3,
                           beklemeler=(lambda n: 0.2, lambda n: 0.3))
        return pb, m, cikis, durumlar

    kart_host = f"127.0.0.1:{sunucu.server_port}"
    cikti = io.StringIO()
    pb = pb2 = pb3 = pb4 = None
    try:
        with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(cikti):
            yay(ONEK_A, A1, "durum", _durum4e(k=2, o=7), retain=True)
            pb, m, cikis, durumlar = kur(pdizin, kart_host)
            pb.baslat()
            bagli = _kosul(lambda: m.kart_cevrimici is True and m.mqtt_bagli)
            onb = pdizin / "bildirim" / f"{KIMLIK4}.okb"
            bag = [b for b in araci.baglantilar if b.get("kullanici") in (KUL, KUL.encode())]
            ok("4E (PC14): kart erisilebilir + onbellek yok -> IMZALI /bildirim/bilgi (bir kez), zarf "
               "onbellege BAYT BAYT ayni yazildi; araciya cihaz hesabiyla baglanip ok/<onek>/# abone; "
               "retained durum cozuldu",
               bagli and kart["istek"] == 1 and kart["imzasiz"] == 0 and onb.read_bytes() == kart["son_govde"]
               and onb.read_bytes()[:4] == b"OKB1" and pb.durum()["bilgi"] == "karttan" and bag
               and araci.olaylar_sec("abone", filtre=f"ok/{ONEK_A}/#"),
               f"bagli={bagli} istek={kart['istek']} {durumlar[-3:]}")

            yay(ONEK_A, A1, "olay", _olay4e(2, "kayit_bitti", sebep=1, oturum=7, nokta=321))
            yay(ONEK_A, A1, "olay", _olay4e(2, "kayit_bitti", sebep=1, oturum=7, nokta=321))
            gitti = _kosul(lambda: any(x[0] == "os-7" for x in cikis.cagri))
            time.sleep(0.5)
            ok("4E: araciya gelen olay (zarf, konu AAD) bildirime; ayni (a, n) ikinci kez bildirim DEGIL",
               gitti and len([x for x in cikis.cagri if x[0] == "os-7"]) == 1, str(cikis.cagri))

            konu_d = f"ok/{ONEK_A}/durum"
            sim = _Ham4E(HOST, araci.port)
            rc = sim.baglan("kart-sim", ka=30, kul="kart", par="kart-sinama-pw",
                            will=(konu_d, bildirim.zarf_kur(A1, konu_d, {"c": 0, "a": 77}), 1, True))
            sim.s.close()                                   # fis cekildi: araci vasiyeti yayinlar
            kopuk = _kosul(lambda: any(x[0] == "baglanti" and "Karttan haber yok" in x[2] for x in cikis.cagri))
            yay(ONEK_A, A1, "durum", _durum4e(k=2, o=7), retain=True)
            geri = _kosul(lambda: any(x[0] == "baglanti" and "yeniden bağlandı" in x[2] for x in cikis.cagri))
            ok("4E: kartin vasiyeti (araci yayinlar, {c:0}) kayit surerken 'Karttan haber yok'; kart donunce "
               "AYNI bildirim (etiket 'baglanti') 'yeniden baglandi'",
               rc == 0 and kopuk and geri and [x[0] for x in cikis.cagri].count("baglanti") == 2, str(cikis.cagri))

            yay(ONEK_A, A1, "durum", _durum4e(k=1, o=0), retain=True)
            _kosul(lambda: m._durum and m._durum.get("k") == 1)
            once = len(cikis.cagri)
            yay(ONEK_A, A1, "durum", _durum4e(0, c=0), retain=True)
            _kosul(lambda: m.kart_cevrimici is False)
            time.sleep(0.3)
            sessiz = len(cikis.cagri) == once
            yay(ONEK_A, A1, "durum", _durum4e(k=1, o=0), retain=True)
            ok("4E: kayit YOKKEN kart cevrimdisi olursa bildirim YOK", sessiz and m.kart_cevrimici is not None)

            # anahtar degisti (ayni onek): cozulemeyen mesaj -> bilgi yeniden alinir
            kart["bilgi"] = dict(kart["bilgi"], a=A2.hex())
            yay(ONEK_A, A2, "durum", _durum4e(k=1, o=0, t=1_790_000_500), retain=True)
            yeni = _kosul(lambda: m._durum and m._durum.get("t") == 1_790_000_500)
            ok("4E (PC14): cozulemeyen zarf (anahtar degisti) -> kart erisilebilir: /bildirim/bilgi YENIDEN "
               "alindi, onbellek yeni zarf, yeni anahtarla retained durum cozuldu",
               yeni and kart["istek"] == 2 and pb.cozulemeyen >= 1 and onb.read_bytes() == kart["son_govde"],
               f"istek={kart['istek']} {durumlar[-3:]}")

            # CONNACK 5: araci parolasi degisti
            araci.kullanicilar[KUL] = (PAROLA_B, "r")
            kart["bilgi"] = dict(kart["bilgi"], p=PAROLA_B)
            araci.kapali_tut()
            araci.ac()
            yenilendi = _kosul(lambda: kart["istek"] == 3 and m.mqtt_bagli, 10.0)
            ok("4E (PC14): CONNACK 5 (araci parolasi degisti) -> kart erisilebilir: bilgi yeniden alinir, "
               "yeni parolayla baglanilir",
               yenilendi and any("kod 5" in x for x in durumlar), f"istek={kart['istek']} {durumlar[-4:]}")

            # QR!: yeni onek + anahtar — eski konu susar
            kart["bilgi"] = dict(kart["bilgi"], o=ONEK_B, a=A3.hex())
            yay(ONEK_B, A3, "durum", _durum4e(k=1, o=0, t=1_790_000_900), retain=True)
            pb.sessizlik = 1.0
            qr = _kosul(lambda: m._durum and m._durum.get("t") == 1_790_000_900, 10.0)
            pb.sessizlik = 999
            ok("4E: QR! (yeni onek): kart cevrimici gorunurken durum konusu sessiz -> bilgi yeniden alinir, "
               "yeni konuya abone olunur",
               qr and kart["istek"] == 4 and araci.olaylar_sec("abone", filtre=f"ok/{ONEK_B}/#"),
               f"istek={kart['istek']}")

            # kartta MQTT ayarli degil (404) — ayri dizin
            kart_bilgi = kart["bilgi"]
            kart["bilgi"] = None
            pb4, m4, _, d4 = kur(tmp / "pc4", kart_host)
            pb4.baslat()
            yok = _kosul(lambda: any("ayarli degil" in x for x in d4))
            pb4.durdur()
            kart["bilgi"] = kart_bilgi
            ok("4E: kartta MQTT ayarli degil (404) -> soylenir, onbellek yazilmaz, iplik olmez",
               yok and not list((tmp / "pc4").rglob("*.okb")), str(d4[-2:]))

            yayinlar = [o for o in araci.olaylar_sec("publish")]
            ok("4E: PC araciya HICBIR SEY yayinlamadi (yalniz abone; ACL reddi yok)",
               not yayinlar and not araci.olaylar_sec("acl_red"), str(yayinlar[:2]))

            # sir taramasi (pb calisirken)
            sirlar = [PAROLA, PAROLA_B, HOST, KUL, ONEK_A, ONEK_B, A1.hex(), A2.hex(), A3.hex(), K4.hex(),
                      f"{HOST}:{araci.port}"]
            ham_sirlar = [s.encode() for s in sirlar] + [A1, A2, A3, K4]
            disk = b"".join(p.read_bytes() for p in pdizin.rglob("*") if p.is_file())
            disk_dosya = sorted(p.relative_to(pdizin).as_posix() for p in pdizin.rglob("*") if p.is_file())
            metin = "\n".join(durumlar) + json.dumps(pb.durum(), ensure_ascii=False) + repr(cikis.cagri)
            ok("4E (PC14): veri dizininde, durum satirlarinda, /bildirim/durum'da, bildirim metinlerinde ve "
               "konsolda araci adresi / kullanici / parola / konu oneki / yuk anahtari / K YOK; diskte yalniz "
               "OKB1 zarfi + son (a, n)",
               not [s for s in ham_sirlar if s in disk] and not [s for s in sirlar if s in metin]
               and not [s for s in sirlar if s in cikti.getvalue()]
               and disk_dosya == [f"bildirim/{KIMLIK4}.okb", "bildirim/son.json"],
               f"{disk_dosya} {[s for s in sirlar if s in metin]}")
            pb.durdur()
            sunucu.shutdown()
            sunucu.server_close()

            # kart ERISILEMEZ: onbellekteki zarfla abone olunur
            pb2, m2, _, d2 = kur(pdizin, kart_host)
            pb2.baslat()
            onbellek = _kosul(lambda: m2.kart_cevrimici is True and m2._durum.get("t") == 1_790_000_900)
            ok("4E (PC14): kart erisilemezken (sunucu kapali) ONBELLEKTEKI zarf (K ile cozulur) kullanilir, "
               "abone olunur",
               onbellek and pb2.bilgi_alimi == 0 and pb2.durum()["bilgi"] == "onbellek", str(d2[-2:]))
            pb2.durdur()

            pb3, m3, _, d3 = kur(tmp / "pc3", kart_host)
            pb3.baslat()
            soylendi = _kosul(lambda: any("dogrulanamadi" in x for x in d3))
            canli = pb3._is is not None and pb3._is.is_alive()
            pb3.durdur()
            ok("4E: onbellek yok + kart erisilemez -> soylenir, MQTT yok, iplik olmez (yeniden dener)",
               soylendi and canli and pb3.durum()["bilgi"] == "yok" and not m3.mqtt_bagli, str(d3[-1:]))
    finally:
        for p in (pb, pb2, pb3, pb4):
            if p is not None:
                p.durdur()
        try:
            sunucu.shutdown()
            sunucu.server_close()
        except Exception:                                   # noqa: BLE001
            pass
        araci.stop()
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def bolum_4e_iplik_birim() -> None:
    import kart_wifi as KW
    import pc_bildirim as PB
    print("\n-- 4E: ipligin kararlari (sahte saat, sahte kart/araci; ag yok) --")

    class _Wifi:
        def __init__(self):
            self.dogrula_n = 0

        def dogrula(self):
            self.dogrula_n += 1
            raise KW.KartDogrulanamadi("erisilemiyor")

    s = _Saat()
    m, _, _, _ = _mantik()
    w = _Wifi()
    durumlar: list[str] = []
    pb = PB.PcBildirim(w, m, yayinla=durumlar.append, veri_dizini=Path(tempfile.gettempdir()) / "okb4e-yok",
                       saat=s, yenile_en_az=60.0, sessizlik=180.0)
    pb._b = {"uri": "mqtt://127.0.0.1:1", "kullanici": "u", "parola": "sinama-pw", "onek": "cd" * 16,
             "anahtar": bytes(32)}
    pb._yenile = True
    pb._bilgi_hazirla()
    pb._yenile = True
    pb._bilgi_hazirla()
    once = w.dogrula_n
    s.t += 61
    pb._yenile = True
    sonra_b = pb._bilgi_hazirla()
    ok("4E: bilgi yeniden alma en sik YENILE_EN_AZ_SN'de bir (kart dovulmez); alinamazsa eldeki bilgiyle devam",
       once == 1 and w.dogrula_n == 2 and sonra_b is pb._b and pb._b is not None, f"{once} {w.dogrula_n}")
    m.kart_cevrimici = False
    s.t += 1000
    kapali = pb._sessiz_mi(0.0)
    m.kart_cevrimici = True
    m.son_durum_mono = s.t - 10
    taze = pb._sessiz_mi(0.0)
    m.son_durum_mono = s.t - 200
    ilk = pb._sessiz_mi(0.0)
    pb._yenile = False
    ikinci = pb._sessiz_mi(0.0)
    ok("4E: durum konusu sessizligi yalniz kart CEVRIMICI gorunurken ve SESSIZLIK_SN'den uzunsa yeniden "
       "almayi tetikler; en sik SESSIZ_YENILE_ARALIK'ta bir",
       not kapali and not taze and ilk and pb._yenile is False and not ikinci, f"{kapali} {taze} {ilk} {ikinci}")

    class _TlsHata:
        def __init__(self, *a, **kw):
            pass

        def baglan(self):
            raise ssl.SSLCertVerificationError(1, "certificate verify failed: Hostname mismatch, "
                                                  "certificate is not valid for 'baska.ad.example'")

        def kapat(self, nazik=True):
            pass
    pb2 = PB.PcBildirim(w, m, yayinla=durumlar.append, istemci=_TlsHata, saat=s)
    pb2._b = dict(pb._b)
    sonuc = pb2._oturum(pb2._b)
    ok("4E: araci baglanti hatasi durum satirina SINIFIYLA yazilir (istisna metni — ad / adres — degil)",
       sonuc is False and durumlar[-1] == "! bildirim: araciya baglanilamadi (TLS sertifika/ad denetimi) — "
       "yeniden denenecek" and "baska.ad" not in "".join(durumlar), durumlar[-1])


def bolum_e7() -> None:
    """E7 (W5): `tezgah_bildirim.py --basladi`'nin olcu aleti — kayip kartta mi aracida mi."""
    print("\n-- E7: basladi kaybi siniflandirici (tezgah_bildirim) --")
    import re
    import pc_ayar
    import tezgah_bildirim as TB
    oz = "ok/" + ONEK + "/olay"

    def m(a, o="basladi", konu=oz, icerik=True):
        return {"konu": konu, "icerik": ({"o": o, "a": a, "n": 1} if icerik else None)}
    gelen = TB.basladi_gelenler([m(11), m(12, o="kayit_bitti"), m(13, konu="ok/" + ONEK + "/durum"),
                                 m(14, icerik=False), m(15), m(15)], oz)
    ok("E7.1 basladi_gelenler: yalniz olay konusundaki COZULMUS basladi (durum/baska olay/cozulemeyen "
       "disarida), tekrar korunur", gelen == [11, 15, 15], str(gelen))
    q1, q0 = {"olay": 1, "kuyruk": 0}, {"olay": 0, "kuyruk": 1}
    s = TB.basladi_siniflandir(10, [q1, q0, q1, None, q0], [11, 14, 15, 10, 99], 15)
    ok("E7.2 siniflar: acilis a0+i; gelen -> ulasti (Q? olay 0 olsa da: PUBACK Q?'den SONRA geldi); "
       "gelmeyen + olay 0 -> kartta_kaldi; gelmeyen + olay >= 1 -> aracida_kayip; Q? yok -> belirsiz",
       s == [(11, "ulasti"), (12, "kartta_kaldi"), (13, "aracida_kayip"), (14, "ulasti"), (15, "ulasti")]
       and TB.basladi_siniflandir(10, [None], [], 11) == [(11, "belirsiz")], str(s))
    ok("E7.3 acilis numaralari sifirlamalarla eslesmiyorsa (son_a != a0 + n) HEPSI belirsiz — "
       "kayip 'aracida' diye yanlis yazilmaz",
       TB.basladi_siniflandir(10, [q1, q1], [11], 13) == [(11, "belirsiz"), (12, "belirsiz")])
    k = TB.basladi_karar
    ok("E7.4 karar: kayip yok / kartta / aracida / ikisinde / belirsiz",
       [k([(1, "ulasti")]), k([(1, "ulasti"), (2, "kartta_kaldi")]), k([(1, "aracida_kayip")]),
        k([(1, "kartta_kaldi"), (2, "aracida_kayip")]), k([(1, "ulasti"), (2, "belirsiz")]), k([])]
       == ["kayip yok", "kayip kartta", "kayip aracida", "kayip ikisinde", "belirsiz", "belirsiz"])
    # pc_bilgi_onbellek: PC'nin 4E onbellegini YALNIZ OKUR (guard: gecici dizinler)
    cdiz, vdiz = pc_ayar.cihaz_dizini(), pc_ayar.veri_dizini()
    imza.Cihaz(cdiz / f"{KIMLIK}.json", KIMLIK, CIHAZ_N, K_CIHAZ, "e7-sinama", 0, "").kaydet()
    (vdiz / "bildirim").mkdir(parents=True, exist_ok=True)
    (vdiz / "bildirim" / f"{KIMLIK}.okb").write_bytes(bilgi_govde(IYI_BILGI))

    def dokum():
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size)
                      for kok in (cdiz, vdiz) for p in kok.rglob("*") if p.is_file())
    once = dokum()
    b = TB.pc_bilgi_onbellek()
    ok("E7.5 pc_bilgi_onbellek PC'nin sifreli onbellegini cozer (cihaz anahtari) ve HICBIR dosyaya "
       "yazmaz (cihaz sayaci dahil)",
       bool(b) and b["onek"] == ONEK and b["kullanici"] == "cihaz" and dokum() == once,
       f"{bool(b)} degisti={dokum() != once}")
    (vdiz / "bildirim" / f"{KIMLIK}.okb").unlink()
    (cdiz / f"{KIMLIK}.json").unlink()
    ok("E7.6 onbellek yoksa None (tezgah 'kopruyu bir kez calistirin' der, karta istek ATMAZ)",
       TB.pc_bilgi_onbellek() is None)
    src = (BURASI / "tezgah_bildirim.py").read_text(encoding="utf-8")
    g = src[src.find("def basladi_kaybi("):src.find("# ── tezgah ──")]
    ana = src[src.find("    if a.basladi:"):src.find("    t = Tezgah(")]
    ok("E7.7 --basladi kartin bildirim ayarina DOKUNMAZ: yalniz Q? okunur (Q komutu yazilmaz, Tezgah "
       "akisi ve temizligi KURULMAZ), karta imzali istek yok",
       bool(g) and "q_ayar(" not in g and "imzali(" not in g and "IM.ac(" not in g
       and not re.search(r'yaz\(\s*f?"Q(?!\?)', g) and "Tezgah(" not in ana and ".temizlik(" not in ana
       and "return" in ana)


def bolum_4e() -> None:
    bolum_4e_metin()
    bolum_4e_mantik()
    bolum_4e_ayar()
    bolum_4e_windows()
    bolum_4e_iplik_birim()
    bolum_4e_iplik()


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
    bolum_4e()
    bolum_e7()
    gercek_dizin_koru.denetle(_KORUMA, ok)
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
