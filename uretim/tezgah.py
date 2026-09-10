# -*- coding: utf-8 -*-
"""TEZGAH KALEMLERI — her adim KENDI sinirlarini basar.

    from tezgah import tezgah
    tezgah("B22b Kart web katmani", [
        ("mDNS telefonda cozuluyor mu",
         "http://olcum.local acilmali; Android'de cozulmezse AP'nin "
         "sabit 192.168.4.1'i kullanilacak"),
    ])

🔴 NEDEN BOYLE — COZULEN KUSUR

Tek bir tezgah listesi vardi: `DEVIR.md`'de ELLE yazilmis 8 kalem, ve o
liste B20/B21 doneminde DONMUSTU. B22.3, B22.4 ve B22.5'in ucu de
*"tezgah listesinde"* diyerek o listeye atif yapiyordu — ve liste onlarin
kalemlerini ICERMIYORDU. Yani bu projenin defalarca yandigi AYRISMA
SINIFININ belge surumu.

Ayrica dort ayri "kanitlamaz" listesi vardi (`dogrula3.py`,
`test_firmware3.py`, `test_olcum3.py`, `tasarim3.py`) ve KESISIMLERI
SIFIRDI: `test_olcum3.py`'nin "ADS1115 ofset ±3 LSB / kazanc %0.15"
kalemi kullanicinin gordugu ozete HIC ulasmiyordu.

Ve en kotusu: zincirin donanima EN BAGIMLI iki adimi (`test_kopru.py`,
`sim3_web.py`) hicbir sey basmiyordu — sinirlari yalnizca docstring'e
gomuluydu, ekrana cikmiyordu.

KURAL: tezgah kalemi, onu DOGRULAYAMAYAN kodun YANINDA yasar. Yeni bir
adim eklerken kalemini de yaninda yazarsin; unutulursa toplayici bunu
soyler.

── BICIM ────────────────────────────────────────────────────────────
Cikti hem INSAN hem MAKINE icin okunabilir; ikinci bir "makine satiri"
basilmiyor (o, ayni bilginin IKI temsili olurdu):

      === TEZGAH: <adim> ===
      [T] <kalem>
          -> <kabul olcutu>

`dogrula3.py` bunlari adim ciktilarindan toplayip TEK birlesik liste
basiyor ve `uretim/_tezgah.md` yaziyor.

⚠ Tamamen ASCII: konsol cp1254 ve emoji/unicode isaret cokertiyor
  (B22.3'te olculdu).
"""
from __future__ import annotations

import re
import sys

BASLIK = "  === TEZGAH: "
KALEM = "  [T] "
KABUL = "      -> "

# Kalem basinda: "kart calisir calismaz, digerlerinden ONCE".
# `_tezgah.md`'nin ilk gun tablosu bundan TURETILIYOR.
ONCELIK = "[!]"


def _konsol_guvenli(adim: str, metin: str) -> None:
    """Konsolun cizemeyecegi karakteri YAZMADAN once yakalar.

    Kural once yalnizca bu dosyanin docstring'inde yaziyordu ve ilk gunde
    cignendi: dort adima kirmizi daire emojisi, birine cevrelenmis rakam
    kondu. Windows konsolu cp1254; `python sim3_web.py` TEK BASINA
    kosturuldugunda codecs icinde UnicodeEncodeError ile cokuyordu —
    yani adimin kendi tezgah kalemi, adimi dusuruyordu.

    Burada patlarsa hangi adimin hangi kaleminin sucu oldugu yaziyor;
    codecs izinde yazmiyordu.
    """
    try:
        metin.encode(sys.stdout.encoding or "utf-8", errors="strict")
    except (UnicodeEncodeError, LookupError):
        kotu = [f"U+{ord(c):04X}" for c in dict.fromkeys(metin)
                if not _cizilebilir(c)]
        raise ValueError(
            f"tezgah({adim!r}): konsol ({sys.stdout.encoding}) su "
            f"karakterleri cizemiyor: {' '.join(kotu)} -- kalem: {metin!r}. "
            f"Tezgah kalemleri ASCII olmali."
        ) from None


def _cizilebilir(c: str) -> bool:
    try:
        c.encode(sys.stdout.encoding or "utf-8", errors="strict")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def tezgah(adim: str, kalemler) -> None:
    """Adimin tezgahta olculecek kalemlerini basar.

    `kalemler`: (kalem, kabul_olcutu) ciftleri.
    """
    if not kalemler:
        return
    for kalem, kabul in kalemler:
        _konsol_guvenli(adim, kalem)
        _konsol_guvenli(adim, kabul)
    print()
    print(f"{BASLIK}{adim} ===")
    for kalem, kabul in kalemler:
        print(f"{KALEM}{kalem}")
        print(f"{KABUL}{kabul}")


def ayristir(metin: str) -> list[tuple[str, str, str]]:
    """Bir adim ciktisindan (adim, kalem, kabul) uclulerini cikarir."""
    adim = ""
    kalem = ""
    bulunan = []
    for sat in metin.splitlines():
        if sat.startswith(BASLIK):
            adim = sat[len(BASLIK):].removesuffix(" ===").strip()
            kalem = ""
        elif sat.startswith(KALEM):
            kalem = sat[len(KALEM):].strip()
        elif sat.startswith(KABUL) and kalem:
            bulunan.append((adim, kalem, sat[len(KABUL):].strip()))
            kalem = ""
    return bulunan


def markdown(kalemler) -> str:
    """Toplanan kalemleri `_tezgah.md` icin bicimler."""
    satir = ["# Tezgahta olculecekler — URETILMIS liste",
             "",
             "Bu dosya `dogrula3.py` tarafindan uretiliyor. **Elle duzenleme.**",
             "Her kalem, onu dogrulayamayan adimin yaninda yaziyor;",
             "yeni bir kalem eklemek icin o adimin `tezgah(...)` cagrisina ekle.",
             ""]
    # ILK GUN listesi TURETILIYOR: `ONCELIK` isaretini tasiyan kalemler.
    # Elle ikinci bir siralama yazilirsa yine bayatlar — DEVIR'in eski
    # sekiz satirlik tablosunun basina gelen tam olarak buydu.
    ilk = [(a, k) for a, k, _o in kalemler if k.startswith(ONCELIK)]
    if ilk:
        satir += ["## Ilk gun", "",
                  f"Bu {len(ilk)} kalem `{ONCELIK}` ile isaretli: kart "
                  "calisir calismaz, digerlerinden ONCE.", "",
                  "> Asagidaki sira ZINCIR sirasi, oncelik sirasi DEGIL — "
                  "kalemler arasinda elle bir siralama tutulsaydi yine "
                  "bayatlardi. Hepsi ilk gun yapilacak; hangisinin once "
                  "oldugu kalemin kendi kabul olcutunde yaziyor "
                  "(orn. *bedava test*, *kart calisir calismaz*).", "",
                  "| # | Adim | Olcum |", "|---|---|---|"]
        for i, (a, k) in enumerate(ilk, 1):
            satir.append(f"| {i} | {a} | {k[len(ONCELIK):].strip()} |")
        satir.append("")

    son = None
    for i, (adim, kalem, kabul) in enumerate(kalemler, 1):
        if adim != son:
            satir += ["", f"## {adim}", "", "| # | Olcum | Kabul olcutu |",
                      "|---|---|---|"]
            son = adim
        satir.append(f"| {i} | {kalem} | {kabul} |")
    satir += ["", f"**Toplam {len(kalemler)} kalem, {len(ilk)} tanesi "
              f"ilk gun.**", ""]
    return "\n".join(satir)


# Adim adiyla eslesen basit anahtar — toplayicinin "hangi adim hic
# kalem basmadi" diye sorabilmesi icin.
def adim_anahtari(baslik: str) -> str:
    m = re.match(r"\s*(B[0-9]+[a-z]?(?:/B[0-9]+)?)", baslik)
    return m.group(1) if m else baslik.strip()[:8]
