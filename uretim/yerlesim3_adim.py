# -*- coding: utf-8 -*-
"""Yerlesim planinin ALT ADIMLARI — LEGO kilavuzu sirasi.

Buyuk adim (0..8) kilavuzun KAPI'li bloklari. Bir blok tek seferde
kurulmasin diye her biri kucuk, sirali alt adimlara bolunuyor:

  hazirlik  plaketi hazirla (kartin ilk kullanildigi adimda)
  parca     parcalari tak + lehimle — ALCAKTAN YUKSEGE; yonlu parca
            (elektrolitik, diyot, DIP, TO-92, TO-220, baslik) kendi adiminda
  iz        lehim yuzu izleri, ag ag (once raylar)
  tel       yalitimli teller
  kablo     kart disi lehim noktalari + kablolar
  esp32     J5 basligi -> ESP32-S3 devkit kablosu (ESP32 karta lehimlenmez)
  kontrol   enerji vermeden once ohmmetre, sonra KAPI

Sira VERIDEN uretiliyor, elle yazilmiyor. Denetim (`yerlesim3.py`,
bolum 9) siranin kurallarini BAGIMSIZ veriden sinar — ayak izinin
fiziksel yuksekligi (`AYAKLAR[..]["yukseklik_mm"]`), delik sahipligi,
`V.ALT_ADIM_SINIR`. Uretici kendi sirasini kendisi onaylamaz: asagidaki
`SIRA` listesi yanlis dizilirse yukseklik iddiasi kirmiziya doner.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yerlesim3_veri as V

# Parca turlerinin takilma sirasi (alcaktan yuksege). Elle secilmis bir
# sira — denetim bunu ayak izlerinin yukseklik_mm degeriyle karsilastirir.
SIRA = ["D3", "R4", "R5", "DIP8", "C1", "C1x2", "C2", "TO92", "HDR10", "ADS",
        "R1D", "SIG", "C6", "CE", "TO220"]

# Uretici grup buyuklukleri. Denetimin sinirlari AYRI: V.ALT_ADIM_SINIR.
GRUP_PARCA = 4
GRUP_IZ = 6
GRUP_IZ_DELIK = 40
GRUP_TEL = 4
GRUP_KABLO = 4

# Bir kartta parcalar izlerden, izler tellerden once.
KART_TURLERI = ("parca", "iz", "tel")
# Buyuk adimin sonu: once kart disi kablolar, EN SON kontrol (KAPI).
SON_TURLER = ("kablo", "kontrol")

# Izlerde ag sirasi: once raylar, sonra sinyaller (ada gore).
RAY_SIRASI = ["GND", "+12V", "Net-(J6-Pin_1)", "-12V", "+5V", "+3V3", "/VREF"]


@dataclass
class AltAdim:
    adim: int
    tur: str
    kart: str | None
    parcalar: list[str] = field(default_factory=list)
    izler: list[tuple[str, int]] = field(default_factory=list)      # (kart, sira)
    teller: list[tuple[str, int]] = field(default_factory=list)
    kablolar: list[int] = field(default_factory=list)                # V.KABLOLAR sirasi
    kart_disi: list[str] = field(default_factory=list)
    ilgili: list[str] = field(default_factory=list)   # yalniz vurgu/yakinlik; SAYILMAZ
    no: str = ""
    sira: int = 0


def dogal(ref: str) -> str:
    return re.sub(r"\d+", lambda m: m.group(0).zfill(3), ref)


def _yonlu(p) -> bool:
    return bool(p.a.get("yonlu"))


def _birlesebilir(a: list, b: list) -> bool:
    return not (_yonlu(a[0]) or _yonlu(b[0])) and len(a) + len(b) <= GRUP_PARCA


def parca_gruplari(ps: list) -> list[list]:
    turler = sorted({p.ayak for p in ps}, key=SIRA.index)
    gruplar = []
    for tur in turler:
        tp = sorted((p for p in ps if p.ayak == tur), key=lambda p: dogal(p.ref))
        for i in range(0, len(tp), GRUP_PARCA):
            gruplar.append(tp[i:i + GRUP_PARCA])
    birlesik: list[list] = []
    for g in gruplar:
        if birlesik and _birlesebilir(birlesik[-1], g):
            birlesik[-1] = birlesik[-1] + g
        else:
            birlesik.append(g)
    return birlesik


def _ag_anahtari(ag: str):
    return (0, RAY_SIRASI.index(ag)) if ag in RAY_SIRASI else (1, dogal(ag))


def iz_gruplari(izler: list[tuple[int, dict]]) -> list[list[int]]:
    """izler: (teller[kart] icindeki sira, iz). Ag ag, raylar once."""
    aglar: dict[str, list] = {}
    for i, t in izler:
        aglar.setdefault(t["ag"], []).append((i, t))
    gruplar: list[list[int]] = []
    sayi = delik = 0
    for ag in sorted(aglar, key=_ag_anahtari):
        for i, t in aglar[ag]:
            d = len(t["yol"]) - 1
            if gruplar and (sayi + 1 > GRUP_IZ or delik + d > GRUP_IZ_DELIK):
                gruplar.append([])
                sayi = delik = 0
            if not gruplar:
                gruplar.append([])
            gruplar[-1].append(i)
            sayi += 1
            delik += d
    return gruplar


def alt_adimlar(nl, parcalar: dict, teller: dict) -> list[AltAdim]:
    son = max([p.adim for p in parcalar.values()] + [a for _g, a in V.KART_DISI.values()])
    ilk_adim = {}
    for p in parcalar.values():
        ilk_adim[p.kart] = min(ilk_adim.get(p.kart, 99), p.adim)

    out: list[AltAdim] = []
    for k in range(son + 1):
        bu: list[AltAdim] = []
        for kart in V.KARTLAR:
            if ilk_adim.get(kart) == k:
                bu.append(AltAdim(k, "hazirlik", kart))
            for tur in KART_TURLERI:
                if tur == "parca":
                    ps = [p for p in parcalar.values()
                          if p.kart == kart and p.adim == k and p.ayak != "TEL"]
                    for g in parca_gruplari(ps):
                        bu.append(AltAdim(k, "parca", kart, parcalar=[p.ref for p in g]))
                elif tur == "iz":
                    izl = [(i, t) for i, t in enumerate(teller.get(kart, []))
                           if t["adim"] == k and t["tur"] == "iz"]
                    for g in iz_gruplari(izl):
                        bu.append(AltAdim(k, "iz", kart, izler=[(kart, i) for i in g]))
                elif tur == "tel":
                    tl = [i for i, t in enumerate(teller.get(kart, []))
                          if t["adim"] == k and t["tur"] == "tel"]
                    for j in range(0, len(tl), GRUP_TEL):
                        bu.append(AltAdim(k, "tel", kart,
                                          teller=[(kart, i) for i in tl[j:j + GRUP_TEL]]))
        for tur in SON_TURLER:
            if tur == "kablo":
                kab = [j for j, c in enumerate(V.KABLOLAR) if c[3] == k]
                pedler = sorted((p for p in parcalar.values()
                                 if p.adim == k and p.ayak == "TEL"),
                                key=lambda p: (p.kart, dogal(p.ref)))
                atanan: set[str] = set()
                for j in range(0, len(kab), GRUP_KABLO):
                    grup = kab[j:j + GRUP_KABLO]
                    uclar = {u.split(":", 1)[1] for c in grup for u in V.KABLOLAR[c][:2]}
                    ped = [p.ref for p in pedler if p.ref in uclar and p.ref not in atanan]
                    atanan.update(ped)
                    disi = sorted({u[2:].split(".")[0] for c in grup for u in V.KABLOLAR[c][:2]
                                   if u.startswith("X:")}, key=dogal)
                    bu.append(AltAdim(k, "kablo", ped and parcalar[ped[0]].kart or None,
                                      parcalar=ped, kablolar=grup, kart_disi=disi))
                kalan = [p.ref for p in pedler if p.ref not in atanan]
                if kalan:
                    bu.append(AltAdim(k, "kablo", parcalar[kalan[0]].kart, parcalar=kalan))
                # ESP32 karta LEHIMLENMEZ: J5 basligina 10 telli kabloyla baglanir.
                # KAPI olcumu +3V3/+5V'u J5'ten aldigi icin baglanti o adimin
                # KAPI'sindan ONCE bir alt adim olmali (denetim 9h).
                j5 = sorted(p.ref for p in parcalar.values() if p.adim == k and p.ayak == "HDR10")
                if j5:
                    bu.append(AltAdim(k, "esp32", "A", ilgili=j5))
            elif tur == "kontrol":
                bu.append(AltAdim(k, "kontrol", None))
        for n, s in enumerate(bu, 1):
            s.no = f"{k}.{n}"
        out += bu
    for i, s in enumerate(out):
        s.sira = i
    return out
