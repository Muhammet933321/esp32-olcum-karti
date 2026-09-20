# -*- coding: utf-8 -*-
"""B50 — kutu / panel kurulum plani: DENETIM + CIZIMLI BELGE (+ 3B).

`yerlesim3.py` plaketi denetleyip `7-yerlesim.html`'i uretiyor; bu dosya
ayni isi PLAKETE GIRMEYEN her sey icin yapiyor ve `8-kutu.html`'i
uretiyor: kullanicinin DIL CUBUGUNDAN yapacagi kutu, panel delikleri,
sont/Q1 yerlesimi, kablolar, kapilar.

Kural: sayilar `kutu_veri.py`'de, kablolar `yerlesim3_veri.KABLOLAR`'da,
KAPI metinleri `yerlesim3_belge.KAPI`'da, menziller `tasarim3_sabit`'te —
burada HIC BIRI tekrar yazilmiyor; hepsi turetilip DENETLENIYOR.

B50g (2026-09-20): dort yonlu bagimsiz inceleme (mekanik, kablolama,
plan, goruntuleyici) 71 bulgu uretti; dogrulananlar burada:
  * taban/kapak siralari x yonunde DUZ parcalardan (yuvarlak uc hicbir
    duvarin altina gelmez), ek yeri kaydirmali;
  * ic kat cubuklari panel deliklerinden TURETILIR: her yuvarlak delik bir
    cubugun ortasina, ek yeri deligin arkasina gelmez (denetim);
  * dis kat ek yeri sira basina deliklerden kacarak secilir; delme duvar
    dikilmeden, parca parca tabloyla;
  * panel ogelerinin kutu icine uzanan govdesi 3B cakisma denetiminde;
  * kapak yan duvardan somunlu civatayla, ayaklarda gomme somun;
  * YUK/PIL born jak cifti (bariyer klemens panele vidalanamiyordu),
    XT30 kuyruk, USB oval yuva ESP32 soket yuksekliginde;
  * COM baypas uyarisi, sanal COM kablolari listede degil, kalibrasyon
    esikleri sabitten, on kosul kutusu, CAD arayuz tablosu.

  python kutu.py            # denetim + belge
  python kutu.py --belge-yok
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))

import belge_menu as MN                                   # noqa: E402
import kutu_veri as K                                     # noqa: E402
import kutu_3b as U                                       # noqa: E402
import tasarim3_sabit as T                                # noqa: E402
import yerlesim3 as Y                                     # noqa: E402
import yerlesim3_adim as AD                               # noqa: E402
import yerlesim3_belge as B                               # noqa: E402
import yerlesim3_veri as V                                # noqa: E402

BELGE = KOK / "BELGELER" / "8-kutu.html"
JAK_ARASI_EN_AZ = 20.0      # mm — 4 mm muzlu fisin govdesi + parmak payi
DELIK_KENAR_PAYI = 3.0      # mm — delik kenari ile cubuk kenari / ek yeri arasi
EK_DELIK_PAYI = 8.0         # mm — dis kat ek yeri ile delik kenari arasi
EK_KAYDIRMA = 10.0          # mm — ardisik siralarda ek yerleri en az bu kadar farkli
KERF = 1.0                  # mm — testere payi
TABAN_EK = (0.45, 0.55)     # taban/kapak/ray/yan siralarinda ek yeri (donusumlu)
KALIB_ESIK_ORANI = 0.05     # firmware: kazanc kalibrasyonu tam skalanin %5'inden az olmaz
E = B.e

AHSAP = {"ust": "#d9bb8c", "on": "#c3a173", "yan": "#a88a5d", "cizgi": "#7d6540"}
VURGU = {"ust": "#f2c14e", "on": "#e0a92f", "yan": "#c08f1f", "cizgi": "#7a5a00"}
PARCA_RENK = {"A": "#3d6aa8", "B": "#8a3ca8", "ESP32": "#2f7d5a",
              "RS": "#b3261e", "Q1": "#8a6e42"}
JAK_RENK = {"kirmizi": "#c8372a", "siyah": "#2b2b2b", "sari": "#d9a300",
            "gri": "#8a8a85", "mavi": "#2f66c4"}
GRUP_AD = {"kutu": "taban", "duvar": "dış kat", "duvar_ic": "iç kat", "direk": "direk",
           "delik": "delik", "panel": "panel", "parca": "parça", "kapak": "kapak",
           "tasiyici": "ayak/altlık"}


# ═══════════════════════════════════════════════════════════════════════
#  VERIDEN TUREYENLER
# ═══════════════════════════════════════════════════════════════════════

def alt_adimlar() -> list[dict]:
    return [dict(s, adim=a["no"], adim_baslik=a["baslik"])
            for a in K.ADIMLAR for s in a["alt"]]


def panel_ogeleri(hangi: str | None = None) -> list[dict]:
    o = [dict(x, panel="ön") for x in K.PANEL_ON] + \
        [dict(x, panel="arka") for x in K.PANEL_ARKA]
    return [x for x in o if hangi is None or x["panel"] == hangi]


def yuvarlak_mi(o: dict) -> bool:
    """Arkasina ic kat cubugu ortalanan ogeler (her delik/yuva)."""
    return o["tip"] in ("jak", "anahtar", "yuva", "kuyruk")


def delik_genislik(o: dict) -> float:
    return o.get("yuva_en_mm", o["delik_mm"])


@lru_cache(maxsize=None)
def olcu() -> dict:
    """Temel olculer — CUBUK ve KUTU'dan; kesim listesi hesap()'ta."""
    c, k = K.CUBUK, K.KUTU
    g, t = c["genislik"], c["kalinlik"]
    duz = c["uzunluk"] - 2 * c["uc_egim"]
    duvar_t = k["duvar_kat"] * t
    return {"g": g, "t": t, "duz": duz, "yarim": c["uzunluk"] / 2,
            "ic_yuk": k["duvar_sira"] * g, "duvar_t": duvar_t,
            "direk_t": k["direk_kat"] * t,
            "dis_en": k["ic_en"] + 2 * duvar_t, "dis_boy": k["ic_boy"] + 2 * duvar_t,
            "yan_dis": k["ic_boy"] + 2 * t,          # yan dis kat on/arka dis katlarin arasina
            "taban_sira": math.ceil((k["ic_boy"] + 2 * duvar_t) / g),
            "kapak_ray": k["ic_boy"] - 2 * g - 2}    # direklerin arasina


def menziller() -> dict:
    """Kullanici belgesindeki her menzil sayisi tasarim sabitinden."""
    rs = min(T.SONT_SECENEK)
    i_maks = min(T.ADS_AKIM_KIRPMA / rs, T.SONT_AKIM_ISIL[rs])
    normal, hv = T.KANALLAR[0], T.KANALLAR[1]
    return {"normal": f"±{normal['fs_sim']:.0f} V", "yuksek": f"±{hv['fs_sim']:.0f} V",
            "skop": f"{T.SKOP_MENZIL_EKSI:.0f} … +{T.SKOP_MENZIL_ARTI:.0f} V",
            "akim": f"{i_maks:.1f} A", "pil_akim": f"{T.PIL_AKIM_SOGUTUCUSUZ:.1f}",
            "i_maks": i_maks, "fs_normal": normal["fs_sim"], "fs_hv": hv["fs_sim"]}


def kalib_esikleri() -> dict:
    """Firmware kazanc kalibrasyonunu tam skalanin %5'inin altinda reddeder."""
    mz = menziller()
    return {"i": KALIB_ESIK_ORANI * T.ADS_AKIM_KIRPMA / min(T.SONT_SECENEK),
            "g_normal": KALIB_ESIK_ORANI * mz["fs_normal"],
            "g_yuksek": KALIB_ESIK_ORANI * mz["fs_hv"]}


@lru_cache(maxsize=None)
def ic_kat_cubuklari(panel: str) -> tuple[tuple[float, float, float], ...]:
    """On/arka ic kat dikey cubuklari: (x0, genislik, z0) — x ic koordinat.

    Sabitler: iki kose (direklerin arkasi) ve her delik/yuva icin ORTALANMIS
    bir cubuk. Kalan boslugu soldan saga duzenli cubuklar doldurur, sigmayan
    yerde bosluk kalir (dis kat kapatiyor). Oval USB yuvasi 18 mm cubukta
    2 mm et birakirdi: onun arkasindaki cubuk KISA, yuvanin ustunden baslar.
    """
    o = olcu()
    g = o["g"]
    son = K.KUTU["ic_en"]
    yer: list[tuple[float, float, float]] = []

    def carpisan(x0):
        return next((s for s in yer if not (x0 + g <= s[0] + 1e-6 or x0 >= s[0] + s[1] - 1e-6)), None)
    for oge in panel_ogeleri(panel):
        z0 = 0.0
        if oge["tip"] == "yuva":
            z0 = float(math.ceil(oge["z"] + oge["delik_mm"] / 2 + DELIK_KENAR_PAYI))
        if (oge["x"] - g / 2, g, z0) not in yer:          # ayni x'te iki delik (alt alta)
            yer.append((oge["x"] - g / 2, g, z0))
    for kose in (0.0, son - g):                       # direklerin arkasi
        if carpisan(kose) is None:
            yer.append((kose, g, 0.0))
    x = 0.0
    while x + g <= son + 1e-6:
        s = carpisan(x)
        if s is None:
            yer.append((x, g, 0.0))
            x += g
        else:
            x = s[0] + s[1]
    return tuple(sorted(yer))


@lru_cache(maxsize=None)
def ic_kat_yan() -> tuple[tuple[float, float], ...]:
    """Yan duvar ic kat: on/arka ic katlarin arasi (y = 0 .. ic_boy), duzenli."""
    g = olcu()["g"]
    out, y = [], 0.0
    while y + g <= K.KUTU["ic_boy"] + 1e-6:
        out.append((y, g))
        y += g
    return tuple(out)


def ek_adaylari(L: float) -> list[float]:
    """Iki parcali bir sira icin ek yeri adaylari: iki parca da duz bolume sigsin."""
    duz = olcu()["duz"]
    lo, hi = max(L - duz, 0.0) + 4.0, min(duz, L) - 4.0
    if hi <= lo:
        return [L / 2]
    return [lo + (hi - lo) * i / 6 for i in range(7)]


@lru_cache(maxsize=None)
def ek_yerleri(panel: str) -> tuple[float, ...]:
    """Dis kat her sira icin ek yeri x'i (DIS koordinat, onden bakan icin soldan).

    Delikli siralar once: ek yeri o siradaki deliklerden en uzak aday.
    Deliksiz siralar donusumlu hedefe (%45/%55) yakin aday. Ardisik
    siralarda ek yeri en az EK_KAYDIRMA farkli (tugla orgusu).
    """
    o, k = olcu(), K.KUTU
    g, dt, L = o["g"], o["duvar_t"], o["dis_en"]
    adaylar = ek_adaylari(L)
    delik = {}
    for r in range(k["duvar_sira"]):
        alt, ust = r * g, (r + 1) * g
        delik[r] = [(oge["x"] + dt, delik_genislik(oge)) for oge in panel_ogeleri(panel)
                    if alt - 1e-6 <= oge["z"] <= ust + 1e-6]
    sec: dict[int, float] = {}
    for r in sorted(delik, key=lambda r: (-len(delik[r]), r)):
        hedef = L * TABAN_EK[r % 2]

        def puan(x):
            uz = min((abs(x - dx) - dw / 2 for dx, dw in delik[r]), default=99.0)
            return min(uz, 40.0) - 0.1 * abs(x - hedef)
        uygun = [x for x in adaylar
                 if all(abs(x - sec[q]) >= EK_KAYDIRMA for q in (r - 1, r + 1) if q in sec)]
        sec[r] = max(uygun or adaylar, key=puan)
    return tuple(sec[r] for r in range(k["duvar_sira"]))


def arka_ayna(xo: float) -> float:
    """Dis koordinati arkadan bakan kisinin solundan olculene cevirir."""
    return olcu()["dis_en"] - xo


def yan_ek(r: int) -> float:
    return olcu()["yan_dis"] * TABAN_EK[r % 2]


def taban_ek(i: int, kapak: bool = False) -> float:
    return olcu()["dis_en"] * TABAN_EK[(i + (1 if kapak else 0)) % 2]


def kutu_ek_parcalari() -> list[dict]:
    """Kutunun kendi ek bloklari (ankraj, klemens cubugu) — kutu_veri'den."""
    return [dict(p) for p in K.KUTU_EK_PARCA]


def vida_merkezleri_mm(p: dict) -> list[tuple[float, float]]:
    """Kartin vida merkezleri (ic koordinat, mm) — yerlesim planinin kosede
    bos biraktigi 2x2 delik blogunun ortasi (yerlesim3.vida_merkezleri).
    Delik (0,0) merkezi kart kenarindan yarim adim iceride. 2 ayakli kart:
    capraz iki kose."""
    adim = V.KARTLAR[p["ref"]].get("adim_mm", 2.54)
    merkez = Y.vida_merkezleri(p["ref"])
    if p["tasiyici"]["adet"] == 2:
        merkez = [merkez[0], merkez[3]]
    return [(p["x"] + (cx + 0.5) * adim, p["y"] + (cy + 0.5) * adim) for cx, cy in merkez[:p["tasiyici"]["adet"]]]


def ayaklar() -> list[dict]:
    """Ayak bloklari, altliklar, kosebent, ek bloklar: kutunun parcasi,
    sahnede ve cakisma denetiminde. x,y,z,en,boy,yuk ic koordinat."""
    g, t = olcu()["g"], olcu()["t"]
    out = []
    for p in K.IC_PARCA:
        ts = p.get("tasiyici")
        if not ts:
            continue
        if ts["tip"] == "ayak":
            for i, (cx, cy) in enumerate(vida_merkezleri_mm(p)):
                out.append({"ref": f"{p['ref']}-ayak{i + 1}", "sahip": p["ref"], "x": cx - g / 2, "y": cy - g / 2,
                            "z": 0.0, "en": g, "boy": g, "yuk": ts["kat"] * t, "adim": ts["adim"], "grup": "ayak",
                            "vida": (cx, cy)})
        elif ts["tip"] == "altlik":
            n = ts["adet"]
            x0 = p["x"] + p["en"] / 2 - n * g / 2
            for i in range(n):
                out.append({"ref": f"{p['ref']}-altlık{i + 1}", "sahip": p["ref"], "x": x0 + i * g, "y": p["y"],
                            "z": 0.0, "en": g, "boy": ts["uzunluk"], "yuk": t, "adim": ts["adim"], "grup": "altlik"})
        elif ts["tip"] == "kosebent":
            out.append({"ref": f"{p['ref']}-köşebent", "sahip": p["ref"], "x": p["x"] - ts["adet"] * t,
                        "y": p["y"], "z": 0.0, "en": ts["adet"] * t, "boy": ts["uzunluk"], "yuk": g,
                        "adim": ts["adim"], "grup": "kosebent"})
    for p in kutu_ek_parcalari():
        out.append({"ref": p["ref"], "sahip": None, "x": p["x"], "y": p["y"], "z": 0.0,
                    "en": p["en"], "boy": p["boy"], "yuk": p["yuk"], "adim": p["adim"], "grup": "ek"})
    return out


@lru_cache(maxsize=None)
def hesap() -> dict:
    """Kesim listesi ve cubuk sayisi.

    Parca kaynaklari:
      duz   — cubugun duz bolumunden (uzunluk - 2*uc_egim), iki ucu duz
      yarim — cubuk ortadan ikiye, duz uctan kirpilir; yuvarlak uc asagi
              (ic kat dikey cubuklar, direk parcalari)
    Iki liste: kesim1 = simdi (taban, raylar, dis kat); kesim2 = duvar
    bitince gercek olcuyle (ic kat, direkler, kapak, ayaklar).
    """
    o, k = olcu(), K.KUTU
    g, t, duz = o["g"], o["t"], o["duz"]
    L, D = o["dis_en"], o["dis_boy"]
    k1: list[tuple[str, float, int, str]] = []
    k2: list[tuple[str, float, int, str]] = []

    def ekle(lst, ad, u, adet, kaynak="duz"):
        lst.append((ad, round(u, 1), int(adet), kaynak))
    n_sira = o["taban_sira"]
    ekle(k1, "Taban sırası — kısa parça", L * TABAN_EK[0], n_sira)
    ekle(k1, "Taban sırası — uzun parça", L * TABAN_EK[1], n_sira)
    ekle(k1, "Taban rayı — kısa parça", D * TABAN_EK[0], 2)
    ekle(k1, "Taban rayı — uzun parça", D * TABAN_EK[1], 2)
    for panel in ("ön", "arka"):
        for r, ek in enumerate(ek_yerleri(panel)):
            # arka duvar parcalari ARKADAN bakan kisinin solundan adlanir —
            # delik tablosu ve ek yeri tablosuyla ayni cerceve
            sol, sag = (L - ek, ek) if panel == "arka" else (ek, L - ek)
            ek_ad = " (arkadan)" if panel == "arka" else ""
            ekle(k1, f"Dış kat {panel} sıra {r + 1} — sol{ek_ad}", sol, 1)
            ekle(k1, f"Dış kat {panel} sıra {r + 1} — sağ{ek_ad}", sag, 1)
    ekle(k1, "Dış kat yan — kısa parça", o["yan_dis"] * TABAN_EK[0], 2 * k["duvar_sira"])
    ekle(k1, "Dış kat yan — uzun parça", o["yan_dis"] * TABAN_EK[1], 2 * k["duvar_sira"])
    ic_on, ic_arka, ic_yan = ic_kat_cubuklari("ön"), ic_kat_cubuklari("arka"), ic_kat_yan()
    tam = [s for s in ic_on + ic_arka if s[2] == 0]
    kisa = [s for s in ic_on + ic_arka if s[2] > 0]
    ekle(k2, "İç kat dikey çubuk (yuvarlak uç aşağı)", o["ic_yuk"], len(tam) + 2 * len(ic_yan), "yarim")
    for s in kisa:
        ekle(k2, "İç kat kısa çubuk — USB yuvasının üstü", o["ic_yuk"] - s[2], 1, "yarim")
    ekle(k2, "Köşe direği parçası (yuvarlak uç aşağı)", o["ic_yuk"], 4 * k["direk_kat"], "yarim")
    ekle(k2, "Kapak sırası — kısa parça", L * TABAN_EK[0], n_sira)
    ekle(k2, "Kapak sırası — uzun parça", L * TABAN_EK[1], n_sira)
    ekle(k2, "Kapak rayı (yan duvara yaslı, tek parça)", o["kapak_ray"], 2)
    for p in K.IC_PARCA:
        ts = p.get("tasiyici")
        if not ts:
            continue
        if ts["tip"] == "ayak":
            ekle(k2, f"Ayak bloğu parçası — {p['ref']} ({ts['adet']} blok × {ts['kat']} kat)", g, ts["adet"] * ts["kat"])
        elif ts["tip"] == "altlik":
            ekle(k2, f"Altlık — {p['ref']}", ts["uzunluk"], ts["adet"])
        elif ts["tip"] == "kosebent":
            ekle(k2, f"Köşebent parçası — {p['ref']} ({ts['adet']} kat)", ts["uzunluk"], ts["adet"])
    for p in kutu_ek_parcalari():
        ekle(k2, f"{p['ref']} ({p['kat']} kat)", max(p["en"], p["boy"]), p["kat"])
    parcalar = k1 + k2
    yarim_adet = sum(a for _ad, _u, a, kk in parcalar if kk == "yarim")
    boylar = sorted((u for _ad, u, a, kk in parcalar if kk == "duz" for _ in range(a)), reverse=True)
    cubuklar: list[float] = []                # her cubugun kalan duz bolumu
    for u in boylar:
        for i, kalan in enumerate(cubuklar):
            if kalan >= u + KERF:
                cubuklar[i] = kalan - u - KERF
                break
        else:
            cubuklar.append(duz - u)
    cubuk = len(cubuklar) + math.ceil(yarim_adet / 2)
    return dict(o, kesim1=k1, kesim2=k2, parcalar=parcalar, ic_on=ic_on, ic_arka=ic_arka, ic_yan=ic_yan,
                cubuk_sayisi=cubuk, eksik=max(0, cubuk - k["elde_cubuk"]),
                eksik_pay=max(0, math.ceil(cubuk * 1.15) - k["elde_cubuk"]),
                artik=sum(cubuklar))


def direkler() -> list[dict]:
    """Dort kose diregi: 18 mm yuzu yan duvara, 6 mm yuzu on/arkaya yasli."""
    k, o = K.KUTU, olcu()
    t, g, h = o["direk_t"], o["g"], o["ic_yuk"]
    return [{"ref": "D1", "x": 0.0, "y": 0.0, "z": 0.0, "en": t, "boy": g, "yuk": h},
            {"ref": "D2", "x": k["ic_en"] - t, "y": 0.0, "z": 0.0, "en": t, "boy": g, "yuk": h},
            {"ref": "D3", "x": 0.0, "y": k["ic_boy"] - g, "z": 0.0, "en": t, "boy": g, "yuk": h},
            {"ref": "D4", "x": k["ic_en"] - t, "y": k["ic_boy"] - g, "z": 0.0, "en": t, "boy": g, "yuk": h}]


def kapak_raylari() -> list[dict]:
    """Iki kapak rayi: yan duvarlarin ic yuzune yasli, direklerin arasinda, 18 mm dik."""
    k, o = K.KUTU, olcu()
    g, t = o["g"], o["t"]
    return [{"ref": "KR1", "x": 0.0, "y": g + 1, "z": o["ic_yuk"] - g, "en": t, "boy": o["kapak_ray"], "yuk": g},
            {"ref": "KR2", "x": k["ic_en"] - t, "y": g + 1, "z": o["ic_yuk"] - g, "en": t, "boy": o["kapak_ray"], "yuk": g}]


def panel_hacim(o: dict) -> dict | None:
    """Panel ogesinin kutu ICINE uzanan govdesi (ic koordinat kutusu)."""
    if not o.get("derin_mm"):
        return None
    w = max(o["metal_mm"], o["delik_mm"])
    on = o["panel"] == "ön"
    y0 = K.KUTU["ic_boy"] - o["derin_mm"] if on else 0.0
    return {"ref": o["ref"], "x": o["x"] - w / 2, "y": y0, "z": o["z"] - w / 2,
            "en": w, "boy": o["derin_mm"], "yuk": w}


def delik_tablosu(panel: str) -> list[dict]:
    """Her delik: sira, parca (sol/sag), parcanin sol ucundan ve cubugun alt
    kenarindan kac mm. Arka duvar icin olculer ARKADAN bakan kisinin solundan:
    onden-sol parca arkadan sag parcadir."""
    o = olcu()
    g, dt, L = o["g"], o["duvar_t"], o["dis_en"]
    ekler = ek_yerleri(panel)
    ayna = panel == "arka"
    out = []
    for oge in panel_ogeleri(panel):
        r = int(oge["z"] // g)
        ek = ekler[r]
        xo = oge["x"] + dt
        if not ayna:
            parca = "sol" if xo < ek else "sağ"
            ofset = xo if parca == "sol" else xo - ek
            boy = ek if parca == "sol" else L - ek
        else:
            parca = "sol" if xo > ek else "sağ"
            ofset = L - xo if parca == "sol" else ek - xo
            boy = L - ek if parca == "sol" else ek
        out.append({"ref": oge["ref"], "etiket": oge["etiket"], "sira": r + 1, "parca": parca,
                    "parca_boy": boy, "ofset": ofset, "z_ic": oge["z"] - r * g,
                    "cap": (f"{oge['yuva_en_mm']:.0f} × {oge['delik_mm']:.0f} oval"
                            if oge["tip"] == "yuva" else f"Ø{oge['delik_mm']:.1f}")})
    return out


def kart_disi_kablolar() -> list[int]:
    """KABLOLAR'in kutuda baglanacak olanlari: en az bir ucu X:, sanal degil."""
    return [i for i, c in enumerate(V.KABLOLAR)
            if (c[0].startswith("X:") or c[1].startswith("X:")) and c[2] != "sanal"]


def kapi_gerek() -> dict[int, set[str]]:
    g: dict[int, set[str]] = {}
    for c in V.KABLOLAR:
        if c[2] == "sanal":
            continue
        for uc in c[:2]:
            if uc.startswith("X:"):
                g.setdefault(c[3], set()).add(uc[2:].split(".")[0])
    return g


def monte_adim() -> dict[str, str]:
    return {r: s["no"] for s in alt_adimlar() for r in s.get("monte", [])}


def giris_direncleri(nl, parcalar) -> list[tuple[str, str, float]]:
    d = B._dc_direnc(9, nl, parcalar)
    return [(ad, ag, d(ag, "/VREF"))
            for ag, ad in (("/V_GIRIS", "V jakı"), ("/HV_GIRIS", "HV jakı"),
                           ("/SKOP_GIRIS", "SKOP jakı"))]


def yerlesim_alt_adimlari(nl, parcalar):
    """7-yerlesim'in alt adimlari — HTML'den degil kaynaktan (yerlesim3_adim)."""
    teller = json.loads(Y.TELLER.read_text(encoding="utf-8")) if Y.TELLER.exists() else {}
    return AD.alt_adimlar(nl, parcalar, teller)


def kablo_delikleri(i: int, nl, parcalar) -> list[str]:
    """Kablonun kart ucundaki delik adlari (C4, B16 ...) — netlistten."""
    out = []
    for uc in V.KABLOLAR[i][:2]:
        if not uc.startswith("X:"):
            k = Y.kablo_ucu(uc, parcalar, nl)
            out.append(Y.delik_adi(k[1], k[2]))
    return out


def _kucuk(s: str) -> str:
    """Turkce kucuk harf: 'DİŞİ'.lower() 'dişi' vermez (İ -> i + nokta)."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def _uf(deger: str) -> float:
    """'68uF 50V' -> 68e-6 (netlist degeri)."""
    m = re.match(r"\s*([\d.]+)\s*([munp]?)F", deger)
    assert m, deger
    return float(m.group(1)) * {"": 1.0, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12}[m.group(2)]


def darbe_i2t(c_farad: float, r_sigorta: float) -> float:
    """Anahtar kapaninca dolu 24 V'un C'yi sigorta + kablo uzerinden doldurmasi: V^2 C / 2R."""
    return T.KAYNAK_24V ** 2 * c_farad / (2 * (r_sigorta + T.SIGORTA_KABLO_R))


def sigorta_paylari(nl) -> dict[str, float]:
    """Her sigorta icin erime I2t / darbe I2t (kotu hal: C16 + C17 birlikte)."""
    c = _uf(nl.deger["C16"]) + _uf(nl.deger["C17"])
    return {ad: i2t / darbe_i2t(c, r) for ad, (r, i2t, _tip) in T.SIGORTA.items()}


def cakisma(a: dict, b: dict) -> bool:
    return (a["x"] < b["x"] + b["en"] and b["x"] < a["x"] + a["en"]
            and a["y"] < b["y"] + b["boy"] and b["y"] < a["y"] + a["boy"])


def cakisma3(a: dict, b: dict) -> bool:
    return cakisma(a, b) and a["z"] < b["z"] + b["yuk"] and b["z"] < a["z"] + a["yuk"]


def aralik2(a: dict, b: dict) -> float:
    """Iki taban izi arasindaki en kucuk aciklik (cakisiyorsa negatif)."""
    dx = max(b["x"] - (a["x"] + a["en"]), a["x"] - (b["x"] + b["en"]))
    dy = max(b["y"] - (a["y"] + a["boy"]), a["y"] - (b["y"] + b["boy"]))
    if dx < 0 and dy < 0:
        return -1.0
    return max(dx, dy)


# ═══════════════════════════════════════════════════════════════════════
#  DENETIM
# ═══════════════════════════════════════════════════════════════════════

def denetle(nl, parcalar) -> Y.Denetim:
    D = Y.Denetim()
    h = hesap()
    c, kb = K.CUBUK, K.KUTU
    g, t = h["g"], h["t"]
    oge = panel_ogeleri()
    ref_oge = {o["ref"]: o for o in oge}
    aa = alt_adimlar()
    hepsi = {s["no"]: s for s in aa}
    numaralar = [s["no"] for s in aa]
    sira = {no: i for i, no in enumerate(numaralar)}

    print("\n  1 · MALZEME VE KESIM")
    D.kosul("Cubugun yuvarlak uclari veride", c.get("uc_egim", 0) > 0,
            f"uc egim {c['uc_egim']:.0f} -> duz {h['duz']:.0f} mm")
    for ad, u, adet, kaynak in h["parcalar"]:
        sinir = {"duz": h["duz"], "yarim": h["yarim"]}[kaynak]
        D.kosul(f"'{ad}' {kaynak.upper()} kaynaga sigiyor", u <= sinir + 1e-6,
                f"{u:.1f} <= {sinir:.0f} mm · {adet} adet")
    D.kosul("Hicbir parca TAM cubuk degil (yuvarlak uc duvar altina gelmez)",
            all(kk in ("duz", "yarim") for _a, _u, _n, kk in h["parcalar"]))
    D.kosul("Dis derinlik tam sira sayisi (taban/kapak kirpma yok)",
            abs(h["taban_sira"] * g - h["dis_boy"]) < 1e-6, f"{h['dis_boy']:.0f} = {h['taban_sira']} x {g:.0f}")
    D.kosul("Ic kat yarim cubuk duvar yuksekligini karsiliyor", h["yarim"] >= h["ic_yuk"],
            f"{h['yarim']:.0f} >= {h['ic_yuk']:.0f}")
    D.kosul("Kapak rayi tek parca (ek yok)", h["kapak_ray"] <= h["duz"], f"{h['kapak_ray']:.0f} <= {h['duz']:.0f}")
    D.kosul("Duvar iki kat (capraz lamine)", kb["duvar_kat"] >= 2, f"{kb['duvar_kat']} kat = {h['duvar_t']:.0f} mm")
    D.kosul("Kose diregi M3 icin >= 6 mm et", h["direk_t"] >= 6.0, f"{h['direk_t']:.0f} mm")
    D.kosul("Gereken cubuk sayisi hesaplandi", h["cubuk_sayisi"] > 0,
            f"{h['cubuk_sayisi']} cubuk, elde {kb['elde_cubuk']}, eksik {h['eksik']}")
    D.kosul("Ilk kesim listesi (1.2) yalniz taban/ray/dis kat", all(
        ad.startswith(("Taban", "Dış kat")) for ad, *_ in h["kesim1"]))
    for panel in ("ön", "arka"):
        ekler = ek_yerleri(panel)
        for r in range(1, len(ekler)):
            D.kosul(f"{panel} dis kat ek yeri sira {r}->{r + 1} kaydirmali",
                    abs(ekler[r] - ekler[r - 1]) >= EK_KAYDIRMA, f"{ekler[r - 1]:.0f} / {ekler[r]:.0f}")
    D.kosul("Taban/kapak ek yerleri kaydirmali", abs(TABAN_EK[0] - TABAN_EK[1]) * h["dis_en"] >= EK_KAYDIRMA)

    print("\n  2 · IC YERLESIM (sokulebilir montaj)")
    for p in K.IC_PARCA:
        n = _kucuk(p["nasil"])
        D.kosul(f"{p['ref']} sokulebilir tutturuluyor",
                ("vida" in n or "kablo bağ" in n) and not re.search(r"yapıştırıl(?!maz)", n), p["nasil"][:48])
        D.kosul(f"{p['ref']} ic alana sigiyor",
                0 <= p["x"] and p["x"] + p["en"] <= kb["ic_en"] and 0 <= p["y"] and p["y"] + p["boy"] <= kb["ic_boy"],
                f"x {p['x']:.0f}+{p['en']:.0f} / y {p['y']:.0f}+{p['boy']:.0f}")
        D.kosul(f"{p['ref']} tasiyicisi bir alt adimda yapiliyor",
                p.get("tasiyici", {}).get("adim") in sira, str(p.get("tasiyici", {}).get("adim")))
    for i, p in enumerate(K.IC_PARCA):
        for q in K.IC_PARCA[i + 1:]:
            ar = aralik2(p, q)
            D.kosul(f"{p['ref']} – {q['ref']} arasi >= parca payi", ar >= kb["parca_payi"],
                    f"{ar:.1f} >= {kb['parca_payi']:.0f} mm")
    sabitler = direkler() + kapak_raylari()
    tasiyicilar = ayaklar()
    for d in sabitler:
        for q in K.IC_PARCA:
            D.kosul(f"{d['ref']} ile {q['ref']} cakismiyor", not cakisma3(d, dict(q, z=0.0)))
    for a in tasiyicilar:
        for q in K.IC_PARCA:
            if q["ref"] == a["sahip"]:
                continue
            D.kosul(f"{a['ref']} ile {q['ref']} cakismiyor", not cakisma3(a, dict(q, z=0.0)))
        for d in sabitler:
            D.kosul(f"{a['ref']} ile {d['ref']} cakismiyor", not cakisma3(a, d))
        D.kosul(f"{a['ref']} ic alanda", 0 <= a["x"] and a["x"] + a["en"] <= kb["ic_en"]
                and 0 <= a["y"] and a["y"] + a["boy"] <= kb["ic_boy"])
        D.kosul(f"{a['ref']} alt adimi var", a["adim"] in sira, a["adim"])
    for i, a in enumerate(tasiyicilar):
        for b2 in tasiyicilar[i + 1:]:
            D.kosul(f"{a['ref']} ile {b2['ref']} cakismiyor", not cakisma3(a, b2))
    hacimler = [v for v in (panel_hacim(o) for o in oge) if v]
    for v in hacimler:
        for q in K.IC_PARCA + sabitler + tasiyicilar:
            D.kosul(f"{v['ref']} ic govdesi {q['ref']} ile cakismiyor", not cakisma3(v, dict(q, z=q.get("z", 0.0))))
    en_yuksek = max(p["yuk"] for p in K.IC_PARCA)
    D.kosul("Duvar yuksekligi en yuksek parca + pay", h["ic_yuk"] >= en_yuksek + 10,
            f"{h['ic_yuk']:.0f} >= {en_yuksek + 10:.0f}")
    esp = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
    usb = ref_oge["USB"]
    D.kosul("ESP32 USB soketi arka duvara <= 3 mm", esp["y"] <= 3.0, f"y = {esp['y']:.0f}")
    D.kosul("USB yuvasi x'i soket x'iyle hizali (<= 1.5 mm)",
            abs(esp["x"] + esp["soket_x_ofset"] - usb["x"]) <= 1.5,
            f"soket {esp['x'] + esp['soket_x_ofset']:.0f} · yuva {usb['x']:.0f}")
    esp_alt = next(a["yuk"] for a in tasiyicilar if a["sahip"] == "ESP32")
    D.kosul("USB yuvasi z'si soket z'siyle hizali (<= 3 mm)",
            abs(esp_alt + esp["soket_z"] - usb["z"]) <= 3.0, f"soket {esp_alt + esp['soket_z']:.0f} · yuva {usb['z']:.0f}")
    hvj = ref_oge["J2.1"]
    bk = next(p for p in K.IC_PARCA if p["ref"] == "B")
    hv_uz = math.hypot(bk["x"] + bk["en"] / 2 - hvj["x"], kb["ic_boy"] - (bk["y"] + bk["boy"]))
    D.kosul("Kart B HV jakina yakin (kablo <= 60 mm)", hv_uz <= 60, f"{hv_uz:.0f} mm")

    print("\n  3 · PANEL")
    for o in oge:
        yari = max(o["metal_mm"], delik_genislik(o)) / 2
        D.kosul(f"{o['ref']} panelin icinde",
                kb["kenar_payi"] <= o["x"] - yari and o["x"] + yari <= kb["ic_en"] - kb["kenar_payi"], f"x={o['x']:.0f}")
        r = int(o["z"] // g)
        alt, ust = r * g, (r + 1) * g
        D.kosul(f"{o['ref']} deligi tek dis-kat sirasinin icinde",
                o["z"] - o["delik_mm"] / 2 - DELIK_KENAR_PAYI >= alt - 1e-6
                and o["z"] + o["delik_mm"] / 2 + DELIK_KENAR_PAYI <= ust + 1e-6,
                f"sira {r + 1}, z={o['z']:.0f}, Ø{o['delik_mm']:.1f}")
        cub = ic_kat_cubuklari(o["panel"])
        w = delik_genislik(o)
        if o["tip"] == "yuva":
            arka = next((s for s in cub if abs(s[0] + s[1] / 2 - o["x"]) <= 0.5), None)
            D.kosul(f"{o['ref']} arkasindaki ic-kat cubugu yuvanin USTUNDEN basliyor (kisa)",
                    arka is not None and arka[2] >= o["z"] + o["delik_mm"] / 2 + DELIK_KENAR_PAYI,
                    f"z0 = {arka[2] if arka else None}")
        else:
            icinde = any(x0 + DELIK_KENAR_PAYI <= o["x"] - w / 2 and o["x"] + w / 2 <= x0 + cw - DELIK_KENAR_PAYI
                         and z0 == 0 for x0, cw, z0 in cub)
            D.kosul(f"{o['ref']} deliginin arkasinda TEK ic-kat cubugu var (ek yeri yok)", icinde,
                    f"x={o['x']:.0f}, Ø{w:.0f}")
        ekx = ek_yerleri(o["panel"])[r] - h["duvar_t"]
        D.kosul(f"{o['ref']} dis-kat ek yerinden uzak",
                abs(o["x"] - ekx) >= w / 2 + EK_DELIK_PAYI,
                f"|{o['x']:.0f} - {ekx:.0f}| >= {w / 2 + EK_DELIK_PAYI:.0f}")
    for panel in ("ön", "arka"):
        cub = ic_kat_cubuklari(panel)
        for i in range(len(cub) - 1):
            D.kosul(f"{panel} ic kat cubuklari ust uste binmiyor ({i + 1}-{i + 2})",
                    cub[i][0] + cub[i][1] <= cub[i + 1][0] + 1e-6, f"{cub[i][0]:.0f}+{cub[i][1]:.0f} <= {cub[i + 1][0]:.0f}")
        D.kosul(f"{panel} ic kat duvarin >= %80'ini kapatiyor",
                sum(s[1] for s in cub) >= 0.80 * kb["ic_en"], f"{sum(s[1] for s in cub):.0f} / {kb['ic_en']:.0f}")
        D.kosul(f"{panel} ic kat iki kosede de cubuk var (direklerin arkasi)",
                any(abs(s[0]) < 1e-6 for s in cub) and any(abs(s[0] + s[1] - kb["ic_en"]) < 1e-6 for s in cub))
        for x0, cw, _z in cub:
            D.kosul(f"{panel} ic kat cubugu ({x0:.0f}) ic alanda", 0 <= x0 and x0 + cw <= kb["ic_en"] + 1e-6)
    D.kosul("Yan ic kat duvarin >= %80'ini kapatiyor",
            sum(s[1] for s in ic_kat_yan()) >= 0.80 * kb["ic_boy"])
    for a in tasiyicilar:
        if a["grup"] == "ayak":
            p = next(q for q in K.IC_PARCA if q["ref"] == a["sahip"])
            vx, vy = a["vida"]
            D.kosul(f"{a['ref']} vidasi kartin kose blogunda (yerlesim plani 2x2 bosluk)",
                    p["x"] < vx < p["x"] + p["en"] and p["y"] < vy < p["y"] + p["boy"]
                    and min(vx - p["x"], p["x"] + p["en"] - vx) <= V.VIDA_KOSE * 2.54 + 0.01
                    and min(vy - p["y"], p["y"] + p["boy"] - vy) <= V.VIDA_KOSE * 2.54 + 0.01,
                    f"({vx:.1f}, {vy:.1f})")
            D.kosul(f"{a['ref']} somunu blok ortasinda (kenara >= 6 mm)",
                    min(vx - a["x"], a["x"] + a["en"] - vx, vy - a["y"], a["y"] + a["boy"] - vy) >= 6.0)
    jaklar = [o for o in oge if o["tip"] == "jak"]
    for i, a in enumerate(jaklar):
        for b2 in jaklar[i + 1:]:
            if a["panel"] != b2["panel"]:
                continue
            m = math.dist((a["x"], a["z"]), (b2["x"], b2["z"]))
            D.kosul(f"{a['ref']} – {b2['ref']} merkez arasi >= {JAK_ARASI_EN_AZ:.0f} mm", m >= JAK_ARASI_EN_AZ, f"{m:.1f}")
    for o in oge:
        if o is hvj or o["panel"] != hvj["panel"] or o["metal_mm"] <= 0:
            continue
        acik = math.dist((hvj["x"], hvj["z"]), (o["x"], o["z"])) - hvj["metal_mm"] / 2 - o["metal_mm"] / 2
        D.kosul(f"HV jaki – {o['ref']} metal arasi >= takviyeli kacak yolu",
                acik >= T.IEC60664_CREEPAGE_TAKVIYELI, f"{acik:.1f} >= {T.IEC60664_CREEPAGE_TAKVIYELI}")
    hv_ic = (hvj["x"], kb["ic_boy"] - hvj["derin_mm"], hvj["z"])
    for x in (0.0, kb["ic_en"]):
        for y in kb["kapak_civata_y"]:
            m = math.dist(hv_ic, (x, y, kb["kapak_civata_z"])) - hvj["metal_mm"] / 2 - 3
            D.kosul(f"HV ic ucu – kapak civatasi ({x:.0f},{y:.0f}) >= kacak yolu",
                    m >= T.IEC60664_CREEPAGE_TAKVIYELI, f"{m:.1f} mm")
    ray = kapak_raylari()[0]
    D.kosul("Kapak civatalari direklerin arasinda ve rayin uzerinde (y)",
            all(ray["y"] + 3 < y < ray["y"] + ray["boy"] - 3 for y in kb["kapak_civata_y"]))
    rz = int(kb["kapak_civata_z"] // g)
    D.kosul("Kapak civatasi tek dis-kat sirasinin icinde",
            rz * g + DELIK_KENAR_PAYI + 1.6 <= kb["kapak_civata_z"] <= (rz + 1) * g - DELIK_KENAR_PAYI - 1.6)
    D.kosul("Kapak rayi civata yuksekligini kapsiyor (z)",
            ray["z"] + 3 <= kb["kapak_civata_z"] <= ray["z"] + ray["yuk"] - 3)
    D.kosul("Kapak civatasi yan ic kat cubugunun ortasina yakin (ek yeri degil)",
            all(any(y0 + DELIK_KENAR_PAYI <= y - 1.6 and y + 1.6 <= y0 + w - DELIK_KENAR_PAYI for y0, w in ic_kat_yan())
                for y in kb["kapak_civata_y"]))
    for o in oge:
        if o["parca"] and o["tip"] == "jak":
            D.kosul(f"{o['ref']} rengi stok adinda", o["renk"].replace("kirmizi", "kırmızı") in _kucuk(o["parca"][0]),
                    o["parca"][0][:36])

    print("\n  4 · KABLOLAR")
    gereken = set(kart_disi_kablolar())
    verilen: dict[int, list[str]] = {}
    for s in aa:
        for i in s.get("kablo", []):
            verilen.setdefault(i, []).append(s["no"])
    D.kosul("Kart disi kablolarin hepsi bir alt adimda", gereken <= set(verilen), f"eksik: {sorted(gereken - set(verilen))}")
    D.kosul("Hicbir kablo iki alt adimda degil", all(len(v) == 1 for v in verilen.values()))
    D.kosul("Kutu planinda kart-kart ve sanal kablo yok", not (set(verilen) - gereken), f"fazla: {sorted(set(verilen) - gereken)}")
    sanal = [i for i, cc in enumerate(V.KABLOLAR) if cc[2] == "sanal"]
    D.kosul("Sanal COM baglantilari var ve listede degil", bool(sanal) and all(i not in verilen for i in sanal), str(sanal))
    for i in sanal:
        D.kosul(f"Sanal kablo {i} tek COM jakina bagli", "X:J1.2" in V.KABLOLAR[i][:2], V.KABLOLAR[i][0])
    yuk_adim = {verilen[i][0] for i, cc in enumerate(V.KABLOLAR) if cc[2] == "yuk" and i in verilen}
    for no in sorted(yuk_adim):
        D.kosul(f"{no} metninde kalin kablo geciyor",
                any("alın kablo" in m for m in hepsi[no].get("yap", [])))
    kelvin = {verilen[i][0] for i, cc in enumerate(V.KABLOLAR) if cc[2] in ("kelvin", "yildiz") and i in verilen}
    D.kosul("Kelvin cifti ve yildiz GND ayni alt adimda", len(kelvin) == 1, str(kelvin))
    D.kosul("Yildiz teli etiketi klemens vidasi demiyor", "klemens" not in _kucuk(V.TEL_ETIKET.get("T_YILDIZ", "")))
    for s in aa:                                    # kart ucu delik adlari metinde
        metin = " ".join(s.get("yap", []) + s.get("kontrol", []))
        for i in s.get("kablo", []):
            for d in kablo_delikleri(i, nl, parcalar):
                D.kosul(f"{s['no']} metni kart deligini adiyla veriyor ({d})", re.search(rf"\b{d}\b", metin) is not None)
    j6 = _kucuk(ref_oge["J6"]["not"])
    D.kosul("XT30 notu: kutu tarafi erkek, kaynak tarafi disi",
            "erkek" in j6 and "dişi" in j6 and "kaynak" in j6 and j6.index("erkek") < j6.index("dişi"))
    m53 = _kucuk(" ".join(hepsi["5.3"]["yap"]))
    D.kosul("5.3 metni XT30 cinsiyetini notla ayni veriyor",
            "pimli (erkek)" in m53 and "kılıflı (dişi)" in m53 and m53.index("erkek") < m53.index("dişi"))
    n6 = _kucuk(V.KART_DISI_NOTU["J6"])
    D.kosul("KART_DISI_NOTU J6 ile kutu notu celismiyor",
            "erkek" in n6 and "dişi" in n6 and n6.index("erkek") < n6.index("dişi"))
    for r in ("J3", "J7"):
        nr = _kucuk(V.KART_DISI_NOTU[r])
        D.kosul(f"KART_DISI_NOTU {r} born jak diyor (klemens degil)",
                "born" in nr and not nr.startswith("2 kutuplu") and "bariyer klemens (" not in nr)
    kul = _kucuk(" ".join(x[2] for x in K.KULLANIM))
    D.kosul("Kullanim metni COM baypasini yasakliyor", "com'a krokodil takma" in kul and "baypas" in kul)
    D.kosul("Kullanim metni HV'de USB/PC topragini yasakliyor", "usb'yi pc'ye takma" in kul)
    D.kosul("Pil testinde V jaki zorunlu ve YUK bos", "zorunlu" in kul and "yük boş" in kul)
    D.kosul("Kullanim menzilleri yer tutucudan (elle yazilmiyor)",
            all("{" in x[0] for x in K.KULLANIM[:3]) and "{pil_akim}" in K.KULLANIM[5][2])

    print("\n  5 · PARCALAR VE SIRA")
    m = monte_adim()
    for r in sorted(V.KART_DISI_NOTU):
        D.kosul(f"{r} bir alt adimda kutuya giriyor", r in m, m.get(r, "YOK"))
    sayim = [r for s in aa for r in s.get("monte", [])]
    D.kosul("Hicbir parca iki kez monte edilmiyor", len(sayim) == len(set(sayim)))
    D.kosul("Alt adim numaralari tekil", len(numaralar) == len(set(numaralar)))
    gerek = kapi_gerek()
    for s in aa:
        for kk in s.get("kapi", []):
            for r in sorted(gerek.get(kk, set())):
                D.kosul(f"KAPI {kk} ({s['no']}) icin {r} daha once monte", r in m and sira[m[r]] <= sira[s["no"]],
                        f"{r}: {m.get(r, 'YOK')}")
    for s in aa:
        for i in s.get("kablo", []):
            for uc in V.KABLOLAR[i][:2]:
                if uc.startswith("X:"):
                    r = uc[2:].split(".")[0]
                    D.kosul(f"{s['no']} kablosu icin {r} monte edilmis", r in m and sira[m[r]] <= sira[s["no"]])
    for s in aa:
        for r in s.get("vurgu", []) + s.get("monte", []):
            kok = r.split(".")[0]
            D.kosul(f"{s['no']} vurgusu {r} tanimli",
                    r in ref_oge or any(p["ref"] == r for p in K.IC_PARCA) or kok in m)
    D.kosul("Delme adimi duvar dikilmeden once (duz zeminde)", sira["3.1"] < sira["4.1"])
    D.kosul("Ic kat delikleri duvar bittikten sonra, jaklardan once", sira["4.5"] < sira["5.1"] < sira["5.2"])
    D.kosul("Ikinci kesim (4.4) duvarlar bitince, ic kattan once", sira["4.3"] < sira["4.4"] < sira["4.5"])
    D.kosul("Sont demeti kutuya girmeden once lehimleniyor", sira["6.4"] < sira["6.6"] < sira["7.2"])
    D.kosul("Ayaklar kart vidalanmadan once", sira["6.1"] < sira["6.2"])
    for a in tasiyicilar:
        if a["sahip"]:
            D.kosul(f"{a['ref']} sahibi monte edilmeden once yapiliyor",
                    sira[a["adim"]] <= sira[m.get(a["sahip"], "6.2" if a["sahip"] == "A" else "6.3")])
    D.kosul("Ilk enerji kablolar bittikten sonra, ESP32'den once",
            all(sira[no] < sira["10.2"] for s in aa for no in [s["no"]] if s.get("kablo")) and sira["10.2"] < sira["11.1"])
    D.kosul("Her KAPI 3..8 kendi alt adiminda", all(any(s.get("kapi") == [kk] for s in aa) for kk in range(3, 9)))
    D.kosul("Kapali kutuda uctan uca test var", any(s["no"] == "13.4" and s.get("kapi") for s in aa))
    for kk in range(1, 9):
        D.kosul(f"KAPI {kk} planda geciyor", any(kk in s.get("kapi", []) for s in aa))
    yerlesim_nolar = {a.no for a in yerlesim_alt_adimlari(nl, parcalar)}
    for no, _ne in K.ON_KOSUL:
        D.kosul(f"On kosul Yerlesim {no} yerlesim planinda var", no in yerlesim_nolar)
    D.kosul("Firmware komutlari kalibrasyon tablosunda", {"Z", "n", "z", "y", "?"} <= {x[0] for x in K.KALIBRASYON})

    print("\n  6 · OLCUM DEGERLERI (netlist ve sabitlerden)")
    for ad, _ag, r in giris_direncleri(nl, parcalar):
        D.kosul(f"{ad} -> VREF direnci hesaplanabiliyor", r != float("inf") and r > 1e3,
                B._oku(r) if r != float("inf") else "sonsuz")
    D.kosul("Sont degeri kalibrasyon komutunda dogru",
            any(f"s{min(T.SONT_SECENEK)}" in x[0] for x in K.KALIBRASYON), f"s{min(T.SONT_SECENEK)}")
    D.kosul("Q1 akim siniri notu tasarim sabitiyle ayni", f"{T.PIL_AKIM_SOGUTUCUSUZ:.2f}" in V.KART_DISI_NOTU["Q1"])
    mz, ke = menziller(), kalib_esikleri()
    D.kosul("Akim siniri sont isil sinirindan (ADC degil)", mz["i_maks"] == T.SONT_AKIM_ISIL[min(T.SONT_SECENEK)],
            f"{mz['i_maks']:.2f} A")
    D.kosul("HV kazanc esigi 24 V kaynagi asiyor -> 12.4 uyariyor",
            ke["g_yuksek"] > 24 and f"{ke['g_yuksek']:.0f} V" in " ".join(hepsi["12.4"]["yap"]), f"{ke['g_yuksek']:.1f} V")
    D.kosul("NORMAL kazanc esigi 12 V kaynakla saglaniyor", ke["g_normal"] < 12, f"{ke['g_normal']:.2f} V")
    D.kosul("Akim kazanc esigi 12.2'deki 1.2 A ile saglaniyor", ke["i"] < 1.2, f"{ke['i']:.2f} A")
    # ── F1 sigortasi ve anahtar darbesi (B52): sayilar veri sayfasindan, C netlistten
    pay = sigorta_paylari(nl)
    c_toplam = _uf(nl.deger["C16"]) + _uf(nl.deger["C17"])
    D.kosul("Giris elektrolitikleri netlistten okunuyor (C16 + C17)", 100e-6 <= c_toplam <= 200e-6, f"{c_toplam * 1e6:.0f} uF")
    D.kosul("Gercek 50 mA HIZLI sigorta anahtar darbesini TASIMAZ (her acmada erir)", pay["F 50 mA"] < 1.0,
            f"erime/darbe = {pay['F 50 mA']:.2f} (darbe {darbe_i2t(c_toplam, T.SIGORTA['F 50 mA'][0]) * 1e3:.2f} mA²s)")
    D.kosul("50 mA GECIKMELI (T) sigorta darbeyi >= 3x payla tasiyor", pay["T 50 mA"] >= T.SIGORTA_DARBE_PAYI,
            f"pay {pay['T 50 mA']:.1f}x (2009 tablosu 6.9 mA²s ile {6.9e-3 / darbe_i2t(c_toplam, T.SIGORTA['T 50 mA'][0]):.1f}x)")
    # Dusuk direncli F sigortalarda darbeyi yalniz kablo/ESR sinirlar: stoktaki 315/400 mA
    # bile 3x pay vermiyor (kullanicinin 400'u birkac acmada sag kaldi — ESR modelde yok,
    # kotu yon). Ara cozum olarak 315'e GECILMEZ; yuvadaki 400 T gelene kadar kalir.
    D.kosul("Stoktaki hizli 315/400 mA da darbeye >= 3x pay vermiyor -> ara cozum 'yuvadaki 400 kalsin'",
            pay["F 315 mA"] < T.SIGORTA_DARBE_PAYI and pay["F 400 mA"] < T.SIGORTA_DARBE_PAYI
            and "400 ma (fus001) kalsın" in _kucuk(" ".join(hepsi["10.1"]["yap"])),
            f"315: {pay['F 315 mA']:.1f}x · 400: {pay['F 400 mA']:.1f}x")
    D.kosul("Kullanicinin olctugu 0.4 ohm 50 mA'lik tel olamaz (>= 15 ohm)", T.SIGORTA["F 50 mA"][0] >= 15
            and abs(0.4 - T.SIGORTA["F 400 mA"][0]) < abs(0.4 - T.SIGORTA["F 50 mA"][0]),
            f"50 mA soguk {T.SIGORTA['F 50 mA'][0]:.1f} ohm · 400 mA {T.SIGORTA['F 400 mA'][0]:.3f} ohm")
    m101 = _kucuk(" ".join(hepsi["10.1"]["yap"]))
    D.kosul("10.1 metni T (gecikmeli) 50 mA diyor ve F'nin darbede attigini soyluyor",
            "gecikmeli" in m101 and "darbe" in m101 and "atar" in m101)
    D.kosul("10.1 metni 0.4 ohm = 400 mA (FUS001) diyor, '50 mA etiketli' demiyor",
            "400 ma" in m101 and "fus001" in m101 and "etiketli" not in m101)
    D.kosul("Malzeme listesinde T 50 mA sigorta ALINACAK, F 50 mA STOKTAN",
            any(m["stok"] is None and "gecikmeli" in _kucuk(m["ad"]) for m in K.MALZEME)
            and any(m["stok"] and "50mA" in m["stok"][0] for m in K.MALZEME))

    print("\n  7 · STOK")
    stok = B.Stok()
    if stok.var:
        for o in oge:
            if o["parca"]:
                s2 = stok.ad_ile(*o["parca"])
                D.kosul(f"{o['ref']} envanterde", "kayıtta yok" not in s2, o["parca"][0][:40])
        for p in K.IC_PARCA:
            if p.get("stok"):
                D.kosul(f"{p['ref']} envanterde", "kayıtta yok" not in stok.ad_ile(*p["stok"]))
        for ad, kat in (("M3 Somun", "Mekanik"), ("M3 Pul", "Mekanik"), ("2 Pin Klemens 5.00mm", "Konnektör"),
                        ("1x40 Dişi Header 180°", "Konnektör")):
            D.kosul(f"'{ad}' envanterde", "kayıtta yok" not in stok.ad_ile(ad, kat))
        stokta, alinacak = malzeme_ayir(stok)
        for m, _k in stokta:
            D.kosul(f"Stokta olan '{m['ad'][:30]}' alinacak listesinde DEGIL", 
                    # "\b" bir heredoc yamasinda GERCEK 0x08 olmustu (B39 ile ayni tuzak) — Write ile yazildi
                    not re.search(r"\b(al|alın|alınacak|satın al)\b", _kucuk(m["not"])))
        D.kosul("Malzeme listesindeki stok sorgulari envanterde karsilik buluyor",
                all(m["stok"] is None or "kayıtta yok" not in stok.ad_ile(*m["stok"]) for m in K.MALZEME),
                str([m["ad"] for m in K.MALZEME if m["stok"] and "kayıtta yok" in stok.ad_ile(*m["stok"])]))
        D.kosul("F 50 mA sigorta ve TO-220 yalitimi stoktan (alinacak degil)",
                {m["ad"] for m, _k in stokta} >= {"50 mA 5×20 cam sigorta (hızlı, F — stoktaki)",
                                                  "TO-220 yalıtım (mika/plastik izolatör + burç)"})
    else:
        print("      (envanter okunamadi — atlandi)")
    return D


# ═══════════════════════════════════════════════════════════════════════
#  CIZIM — yardimcilar
# ═══════════════════════════════════════════════════════════════════════

def _svg(ic: str, gen: float, yuk: float, baslik: str) -> str:
    return (f'<svg viewBox="0 0 {gen:.0f} {yuk:.0f}" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="ui-monospace,Consolas,monospace" role="img"><title>{E(baslik)}</title>{ic}</svg>')


def _yazi(x, y, s, boy=11, renk="var(--m2)", hiza="middle", kalin=False):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{hiza}" font-size="{boy}" '
            f'fill="{renk}"{" font-weight=\"600\"" if kalin else ""}>{E(s)}</text>')


def _dikdortgen(x, y, w, h, dolgu, cizgi="var(--cizgi)", opak=1.0, rx=2):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{dolgu}" stroke="{cizgi}" stroke-width="1" opacity="{opak}"/>')


def _cizgi(x1, y1, x2, y2, renk="var(--m2)", kalin=2.4, kesik=False):
    d = ' stroke-dasharray="5 4"' if kesik else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{renk}" stroke-width="{kalin}" stroke-linecap="round"{d}/>')


IZO_ACI = math.radians(30)


def _izo(x, y, z, o, s):
    px = (x - y) * math.cos(IZO_ACI) * s
    py = ((x + y) * math.sin(IZO_ACI) - z) * s
    return (o[0] + px, o[1] + py)


def _izo_sigdir(dx, dy, z0, z1, hedef_en=560.0, pay=26.0, alt=44.0):
    ham = [_izo(x, y, z, (0.0, 0.0), 1.0) for x in (0, dx) for y in (0, dy) for z in (z0, z1)]
    gx = max(p[0] for p in ham) - min(p[0] for p in ham)
    gy = max(p[1] for p in ham) - min(p[1] for p in ham)
    s = hedef_en / gx
    o = (pay - min(p[0] for p in ham) * s, pay - min(p[1] for p in ham) * s)
    return s, o, gx * s + 2 * pay, gy * s + 2 * pay + alt


def _izo_kutu(x, y, z, dx, dy, dz, o, s, renk, opak=1.0):
    p = {}
    for i, (ax, ay, az) in enumerate([(0, 0, 0), (dx, 0, 0), (dx, dy, 0), (0, dy, 0),
                                      (0, 0, dz), (dx, 0, dz), (dx, dy, dz), (0, dy, dz)]):
        p[i] = _izo(x + ax, y + ay, z + az, o, s)

    def yuz(idx, renk_):
        d = " ".join(f"{p[i][0]:.1f},{p[i][1]:.1f}" for i in idx)
        return (f'<polygon points="{d}" fill="{renk_}" stroke="{renk["cizgi"]}" '
                f'stroke-width="0.7" opacity="{opak}"/>')
    return yuz((4, 5, 6, 7), renk["ust"]) + yuz((0, 1, 5, 4), renk["on"]) + yuz((1, 2, 6, 5), renk["yan"])


# ═══════════════════════════════════════════════════════════════════════
#  CIZIM — gorunusler
# ═══════════════════════════════════════════════════════════════════════

def ciz_kesim(parcalar) -> str:
    h, c = hesap(), K.CUBUK
    olc, sol, ust, satir = 2.0, 250.0, 30.0, 30.0
    gen = sol + c["uzunluk"] * olc + 120
    yuk = ust + satir * len(parcalar) + 20
    o = [_yazi(sol, 18, f"bir çubuk {c['uzunluk']:.0f} mm · gri uçlar yuvarlak "
                        f"({c['uc_egim']:.0f} mm) · düz bölüm {h['duz']:.0f} mm", 11, "var(--m3)", "start")]
    for i, (ad, u, adet, kaynak) in enumerate(parcalar):
        y = ust + i * satir
        o.append(_dikdortgen(sol, y, c["uzunluk"] * olc, 20, "var(--yz2)", "var(--cizgi)"))
        for ux in (sol, sol + (c["uzunluk"] - c["uc_egim"]) * olc):
            o.append(_dikdortgen(ux, y, c["uc_egim"] * olc, 20, "#8a8a85", "var(--cizgi)", 0.45))
        bas = sol + (c["uc_egim"] * olc if kaynak == "duz" else 0)
        o.append(_dikdortgen(bas, y, u * olc, 20, AHSAP["on"], AHSAP["cizgi"]))
        if kaynak == "yarim":
            o.append(_dikdortgen(bas + h["yarim"] * olc, y, u * olc, 20, AHSAP["ust"], AHSAP["cizgi"]))
            o.append(_yazi(bas + h["yarim"] * olc + u * olc / 2, y + 14, "2. yarım", 9, "#2b2b2b"))
        o.append(_yazi(sol - 10, y + 14, ad[:44], 10, "var(--m1)", "end"))
        o.append(_yazi(bas + u * olc / 2, y + 14, f"{u:.0f}", 10, "#2b2b2b"))
        o.append(_yazi(sol + c["uzunluk"] * olc + 10, y + 14, f"× {adet}", 11, "var(--m1)", "start", True))
        kalan = h["duz"] - u if kaynak == "duz" else 0.0
        if kalan > 14:
            o.append(_yazi(bas + (u + kalan / 2) * olc, y + 14, f"artan {kalan:.0f}", 9, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Kesim listesi")


def ciz_taban(kapak=False) -> str:
    """Kusbakisi: taban/kapak siralari (x yonunde, ek yerleri kaydirmali) + raylar."""
    h, c = hesap(), K.CUBUK
    g = h["g"]
    olc, sol, ust = 1.7, 40.0, 40.0
    gen, yuk = sol * 2 + h["dis_en"] * olc, ust * 2 + h["dis_boy"] * olc
    o = []
    for i in range(h["taban_sira"]):
        y = ust + i * g * olc
        ek = taban_ek(i, kapak)
        for bas, boy in ((0.0, ek), (ek, h["dis_en"] - ek)):
            o.append(_dikdortgen(sol + bas * olc, y, boy * olc - 1, g * olc - 1, AHSAP["ust"], AHSAP["cizgi"]))
            o.append(_yazi(sol + (bas + boy / 2) * olc, y + g * olc / 2 + 4, f"{boy:.0f}", 9, "#5a4a2a"))
    if kapak:
        for r in kapak_raylari():
            x = sol + (r["x"] + h["duvar_t"]) * olc
            o.append(_dikdortgen(x - 1, ust + (r["y"] + h["duvar_t"]) * olc, c["kalinlik"] * olc + 2, r["boy"] * olc,
                                 VURGU["on"], VURGU["cizgi"], 0.9))
        for y in K.KUTU["kapak_civata_y"]:
            for x in (0.0, K.KUTU["ic_en"]):
                cx, cy = sol + (x + h["duvar_t"]) * olc, ust + (y + h["duvar_t"]) * olc
                o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#333" stroke="var(--yz)"/>')
    else:
        for rx in (0.25, 0.75):
            x = sol + h["dis_en"] * rx * olc - g * olc / 2
            ek = h["dis_boy"] * TABAN_EK[0 if rx < 0.5 else 1]
            for bas, boy in ((0.0, ek), (ek, h["dis_boy"] - ek)):
                o.append(_dikdortgen(x, ust + bas * olc, g * olc, boy * olc - 1, VURGU["on"], VURGU["cizgi"], 0.85))
    o.append(_yazi(sol + h["dis_en"] * olc / 2, ust - 12,
                   f"{h['dis_en']:.0f} × {h['dis_boy']:.0f} mm — {h['taban_sira']} sıra, her sıra iki parça, "
                   "ek yeri sırada bir sola bir sağa", 11))
    o.append(f'<text x="{sol - 14:.0f}" y="{ust + h["dis_boy"] * olc / 2:.0f}" text-anchor="middle" font-size="11" '
             f'fill="var(--m2)" transform="rotate(-90 {sol - 14:.0f} {ust + h["dis_boy"] * olc / 2:.0f})">'
             f'{h["taban_sira"]} sıra × {h["g"]:.0f} mm</text>')
    o.append(_yazi(sol + h["dis_en"] * olc / 2, ust + h["dis_boy"] * olc + 22,
                   "sarı = " + ("yan duvarlara yaslanan iki kapak rayı (altta, 18 mm yüzü dik) · siyah = M3 cıvata" if kapak else
                                "alttan yapıştırılan iki ray (sıralara dik, ikişer parça)"), 11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Kapak" if kapak else "Taban")


def ciz_duvar(sira: int) -> str:
    c, kb, h = K.CUBUK, K.KUTU, hesap()
    s, o0, gen, yuk = _izo_sigdir(kb["ic_en"], kb["ic_boy"], -c["kalinlik"], sira * h["g"])
    dt = h["duvar_t"]
    o = [_izo_kutu(-dt, -dt, -c["kalinlik"], h["dis_en"], h["dis_boy"], c["kalinlik"], o0, s, AHSAP)]
    for r in range(sira):
        z = r * h["g"]
        renk = VURGU if r == sira - 1 else AHSAP
        opak = 1.0 if r == sira - 1 else 0.92
        o.append(_izo_kutu(-dt, kb["ic_boy"] + dt - c["kalinlik"], z, h["dis_en"], c["kalinlik"], h["g"], o0, s, renk, opak))
        o.append(_izo_kutu(kb["ic_en"] + dt - c["kalinlik"], -dt + c["kalinlik"], z, c["kalinlik"], h["yan_dis"], h["g"], o0, s, renk, opak))
        o.append(_izo_kutu(-dt, -dt + c["kalinlik"], z, c["kalinlik"], h["yan_dis"], h["g"], o0, s, renk, opak))
        o.append(_izo_kutu(-dt, -dt, z, h["dis_en"], c["kalinlik"], h["g"], o0, s, renk, opak))
    o.append(_yazi(gen / 2, yuk - 26, f"{sira}. sıra bitti · dış kat yüksekliği {sira * h['g']:.0f} mm", 12, "var(--m1)", "middle", True))
    o.append(_yazi(gen / 2, yuk - 10, "öne bakan kenar = ön duvar (jaklar)", 11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, f"{sira}. sıra")


def ciz_panel(hangi: str, vurgu: set[str], ic_kat: bool = True) -> str:
    """Duvar gorunusu DISARIDAN: dis kat siralari, ek yerleri, ic kat cubuklari, delikler.
    Arka duvar aynali: kullanici arkaya gecince x'i kendi solundan sayar."""
    kb, h = K.KUTU, hesap()
    g, dt = h["g"], h["duvar_t"]
    olc, sol, ust = 2.0, 40.0, 34.0
    satirlar = sorted({int(q["z"] // g) for q in panel_ogeleri(hangi)})   # etiket satiri = delik sirasi
    gen, yuk = sol * 2 + h["dis_en"] * olc, ust + h["ic_yuk"] * olc + 74 + 26 * len(satirlar)
    taban_y = ust + h["ic_yuk"] * olc
    ayna = hangi == "arka"

    def X(x_ic):                               # ic koordinat -> ekran (dis kenardan)
        xo = x_ic + dt
        return sol + (arka_ayna(xo) if ayna else xo) * olc
    o = []
    ekler = ek_yerleri(hangi)
    for r in range(kb["duvar_sira"]):
        y = taban_y - (r + 1) * g * olc
        o.append(_dikdortgen(sol, y, h["dis_en"] * olc, g * olc - 1, AHSAP["on"], AHSAP["cizgi"]))
        ex = sol + (arka_ayna(ekler[r]) if ayna else ekler[r]) * olc
        o.append(_cizgi(ex, y + 1, ex, y + g * olc - 2, VURGU["cizgi"], 2.0))
        o.append(_yazi(ex, y + 8, f"ek {(arka_ayna(ekler[r]) if ayna else ekler[r]):.0f}", 8, "var(--m3)"))
        o.append(_yazi(sol - 8, y + g * olc / 2 + 4, f"{r + 1}", 10, "var(--m3)", "end"))
    if ic_kat:
        for x0, w, z0 in ic_kat_cubuklari(hangi):
            xa, xb = X(x0), X(x0 + w)
            o.append(f'<rect x="{min(xa, xb) + 1.5:.1f}" y="{ust + z0 * olc + 1:.1f}" width="{abs(xb - xa) - 3:.1f}" '
                     f'height="{(h["ic_yuk"] - z0) * olc - 2:.1f}" rx="2" fill="rgba(255,255,255,.10)" '
                     f'stroke="var(--m1)" stroke-width="1.2" stroke-dasharray="4 3"/>')
            o.append(_yazi((xa + xb) / 2, ust - 2, f"{x0:.0f}", 8, "var(--m3)"))
    for i, x in enumerate(sorted(panel_ogeleri(hangi), key=lambda q: -q["x"] if ayna else q["x"])):
        cx, cy = X(x["x"]), taban_y - x["z"] * olc
        v = x["ref"] in vurgu
        renk = JAK_RENK.get(x["renk"], "#8a8a85")
        if x["tip"] == "yuva":
            o.append(_dikdortgen(cx - x["yuva_en_mm"] / 2 * olc, cy - x["delik_mm"] / 2 * olc,
                                 x["yuva_en_mm"] * olc, x["delik_mm"] * olc, "var(--yz)", "#f2c14e" if v else "var(--m3)", 1, 6))
        else:
            r = max(x["metal_mm"], x["delik_mm"]) / 2 * olc
            o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{renk}" stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{3 if v else 1.2}" opacity=".95"/>')
            o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{x["delik_mm"] / 2 * olc:.1f}" fill="var(--yz)" opacity=".6"/>')
        kay = 26 * satirlar.index(int(x["z"] // g))     # her delik sirasi kendi etiket satirinda
        o.append(_yazi(cx, taban_y + 16 + kay, x["etiket"], 10, "var(--m1)", "middle", v))
        xo = x["x"] + dt
        o.append(_yazi(cx, taban_y + 28 + kay, f"x {(arka_ayna(xo) if ayna else xo):.0f} · z {x['z']:.0f}", 9, "var(--m3)"))
    o.append(_dikdortgen(sol, taban_y, h["dis_en"] * olc, 5, AHSAP["yan"], AHSAP["cizgi"]))
    alt_y = taban_y + 22 + 26 * len(satirlar)
    o.append(_yazi(sol + h["dis_en"] * olc / 2, alt_y,
                   f"{'Arka' if ayna else 'Ön'} duvar — DIŞARIDAN bakış · x dış sol kenardan"
                   + (" (arkaya geçince kendi solun)" if ayna else ""), 10, "var(--m3)"))
    o.append(_yazi(sol + h["dis_en"] * olc / 2, alt_y + 14,
                   "turuncu çizgi = dış kat ek yeri" + (" · kesikli = iç kat dikey çubuk (iç yüzde, üstte sol kenarı)"
                                                       if ic_kat else ""), 10, "var(--m3)"))
    o.append(_yazi(sol + h["dis_en"] * olc / 2, ust - 14, f"{h['dis_en']:.0f} mm (dış)", 11))
    return _svg("".join(o), gen, yuk, f"{hangi} duvar")


def ciz_yerlesim(vurgu: set[str], direk_vurgu: bool = False) -> str:
    kb, h = K.KUTU, hesap()
    dt = h["duvar_t"]
    olc, sol, ust = 1.7, 46.0, 46.0
    gen, yuk = sol * 2 + kb["ic_en"] * olc, ust * 2 + kb["ic_boy"] * olc + 48
    o = [_dikdortgen(sol - dt * olc, ust - dt * olc, h["dis_en"] * olc, h["dis_boy"] * olc, AHSAP["yan"], AHSAP["cizgi"]),
         _dikdortgen(sol - dt * olc / 2, ust - dt * olc / 2, (kb["ic_en"] + dt) * olc, (kb["ic_boy"] + dt) * olc, AHSAP["on"], AHSAP["cizgi"]),
         _dikdortgen(sol, ust, kb["ic_en"] * olc, kb["ic_boy"] * olc, "var(--yz2)", "var(--cizgi)")]
    for d in direkler():
        o.append(_dikdortgen(sol + d["x"] * olc, ust + d["y"] * olc, d["en"] * olc, d["boy"] * olc,
                             VURGU["on"] if direk_vurgu else AHSAP["yan"], VURGU["cizgi"] if direk_vurgu else AHSAP["cizgi"]))
    for a in ayaklar():
        v = a["sahip"] in vurgu or a["ref"] in vurgu
        o.append(_dikdortgen(sol + a["x"] * olc, ust + a["y"] * olc, a["en"] * olc, a["boy"] * olc,
                             VURGU["ust"] if v else AHSAP["ust"], AHSAP["cizgi"], 0.9))
    for p in K.IC_PARCA:
        v = p["ref"] in vurgu
        x, y = sol + p["x"] * olc, ust + p["y"] * olc
        o.append(_dikdortgen(x, y, p["en"] * olc, p["boy"] * olc, PARCA_RENK.get(p["ref"], "#666"),
                             "#f2c14e" if v else "var(--cizgi)", 0.95 if v else 0.5))
        o.append(_yazi(x + p["en"] * olc / 2, y + p["boy"] * olc / 2 + 4, p["ref"], 11, "#fff", "middle", v))
    for hac in (v2 for v2 in (panel_hacim(q) for q in panel_ogeleri()) if v2):
        o.append(_dikdortgen(sol + hac["x"] * olc, ust + hac["y"] * olc, hac["en"] * olc, hac["boy"] * olc,
                             "none", "var(--m3)", 0.7))
    for i, x in enumerate(sorted(panel_ogeleri("ön"), key=lambda q: q["x"])):
        cx = sol + x["x"] * olc
        v = x["ref"] in vurgu
        o.append(f'<circle cx="{cx:.1f}" cy="{ust + kb["ic_boy"] * olc + 6:.1f}" r="5" fill="{JAK_RENK.get(x["renk"], "#888")}" stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{2 if v else 1}"/>')
        o.append(_yazi(cx, ust + kb["ic_boy"] * olc + (24 if i % 2 == 0 else 36), x["etiket"], 9, "var(--m1)" if v else "var(--m3)"))
    for i, x in enumerate(sorted(panel_ogeleri("arka"), key=lambda q: q["x"])):
        cx = sol + x["x"] * olc
        v = x["ref"] in vurgu
        o.append(f'<circle cx="{cx:.1f}" cy="{ust - 6:.1f}" r="5" fill="{JAK_RENK.get(x["renk"], "#888")}" stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{2 if v else 1}"/>')
        o.append(_yazi(cx, ust - (14 if i % 2 == 0 else 26), x["etiket"], 9, "var(--m1)" if v else "var(--m3)"))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust + kb["ic_boy"] * olc + 52,
                   "kuşbakışı · alt kenar = ön duvar (jaklar) · açık kahverengi = ayak / altlık / köşebent", 10, "var(--m3)"))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust + kb["ic_boy"] * olc + 66,
                   "ince çerçeve = panel parçasının içeri uzanan gövdesi · köşelerde direkler", 10, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Yerleşim")


def ciz_izo(vurgu: set[str]) -> str:
    c, kb, h = K.CUBUK, K.KUTU, hesap()
    s, o0, gen, yuk = _izo_sigdir(kb["ic_en"], kb["ic_boy"], -c["kalinlik"], h["ic_yuk"])
    o = [_izo_kutu(0, 0, -c["kalinlik"], kb["ic_en"], kb["ic_boy"], c["kalinlik"], o0, s, AHSAP),
         _izo_kutu(0, kb["ic_boy"], 0, kb["ic_en"], h["duvar_t"], h["ic_yuk"], o0, s, AHSAP, 0.9),
         _izo_kutu(kb["ic_en"], 0, 0, h["duvar_t"], kb["ic_boy"], h["ic_yuk"], o0, s, AHSAP, 0.9)]
    for a in ayaklar():
        v = a["sahip"] in vurgu or a["ref"] in vurgu
        o.append(_izo_kutu(a["x"], a["y"], 0, a["en"], a["boy"], a["yuk"], o0, s, VURGU if v else AHSAP, 0.9))
    for p in sorted(K.IC_PARCA, key=lambda q: -(q["x"] + q["y"])):
        v = p["ref"] in vurgu
        renk = {"ust": PARCA_RENK.get(p["ref"], "#666"), "on": PARCA_RENK.get(p["ref"], "#666"),
                "yan": PARCA_RENK.get(p["ref"], "#666"), "cizgi": "#111"}
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == p["ref"]), 0.0)
        o.append(_izo_kutu(p["x"], p["y"], z0, p["en"], p["boy"], max(p["yuk"] * .5, 6), o0, s, renk, 1.0 if v else 0.42))
        m = _izo(p["x"] + p["en"] / 2, p["y"] + p["boy"] / 2, z0 + max(p["yuk"] * .5, 6) + 4, o0, s)
        o.append(_yazi(m[0], m[1], p["ref"], 11, "#fff" if v else "var(--m3)", "middle", v))
    o.append(_izo_kutu(-h["duvar_t"], 0, 0, h["duvar_t"], kb["ic_boy"], h["ic_yuk"], o0, s, AHSAP, 0.55))
    o.append(_izo_kutu(0, -h["duvar_t"], 0, kb["ic_en"], h["duvar_t"], h["ic_yuk"], o0, s, AHSAP, 0.55))
    o.append(_yazi(gen / 2, yuk - 12, "ön ve sol duvar saydam çizildi (içeriyi görmek için)", 11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "İzometrik")


def ciz_kullanim(hangi: str) -> str:
    """Kullanim semalari: YUK jaklari SERI akim yolu; PIL jaklari desarj yolu.
    COM icin krokodil YOK: COM = YUK 2 (icerde bagli) — sema bunu gosteriyor."""
    KIR, SIY, MAV = "#c8372a", "#8a8a85", "#2f66c4"
    KUTU_Y, UST = 215.0, 60.0
    o = []

    def kutu_govde(x1, x2, baslik, alt):
        return (_dikdortgen(x1, KUTU_Y, x2 - x1, 78, "var(--yz2)", "var(--s1)")
                + _yazi((x1 + x2) / 2, KUTU_Y + 34, baslik, 12, "var(--s1)", "middle", True)
                + _yazi((x1 + x2) / 2, KUTU_Y + 54, alt, 10, "var(--m3)"))

    def ucbas(x, renk, etiket, alt, kat=0):
        k = 26 * kat
        return (f'<circle cx="{x:.0f}" cy="{KUTU_Y:.0f}" r="6" fill="{renk}" stroke="var(--yz)" stroke-width="1.5"/>'
                + _yazi(x, KUTU_Y - 26 - k, etiket, 11, "var(--m1)", "middle", True)
                + _yazi(x, KUTU_Y - 12 - k, alt, 9, "var(--m3)"))
    if hangi == "akim":
        o.append(_dikdortgen(20, 30, 130, 80, "var(--yz2)"))
        o.append(_yazi(85, 62, "KAYNAK", 12, "var(--m1)", "middle", True))
        o.append(_yazi(85, 82, "pil / güç kaynağı", 10, "var(--m3)"))
        o.append(_dikdortgen(420, 30, 150, 80, "var(--yz2)"))
        o.append(_yazi(495, 62, "ÖLÇÜLEN DEVRE", 12, "var(--m1)", "middle", True))
        o.append(_yazi(495, 82, "motor, kart, lamba…", 10, "var(--m3)"))
        o.append(kutu_govde(150, 470, "ÖLÇÜM KUTUSU", "içeride: 15 mΩ şönt · COM = YÜK 2"))
        o.append(_cizgi(150, UST, 420, UST, KIR))
        o.append(_yazi(285, UST - 12, "+ hattı — buna dokunmuyoruz", 10, "var(--m3)"))
        o.append(_cizgi(495, 110, 495, 170, SIY)); o.append(_cizgi(495, 170, 430, 170, SIY)); o.append(_cizgi(430, 170, 430, KUTU_Y, SIY))
        o.append(ucbas(430, "#2b2b2b", "YÜK 1", "devreden gelen uç"))
        o.append(_cizgi(190, KUTU_Y, 190, 170, SIY)); o.append(_cizgi(190, 170, 85, 170, SIY)); o.append(_cizgi(85, 170, 85, 110, SIY))
        o.append(ucbas(190, "#2b2b2b", "YÜK 2", "kaynağa giden uç"))
        o.append(_cizgi(340, KUTU_Y, 340, 140, KIR, 2.0, True)); o.append(_cizgi(340, 140, 400, 140, KIR, 2.0, True)); o.append(_cizgi(400, 140, 400, UST, KIR, 2.0, True))
        o.append(ucbas(340, KIR, "V jakı", "devrenin artısı"))
        o.append(ucbas(260, "#2b2b2b", "COM", "BOŞ — içeride YÜK 2", 1))
        o.append(_cizgi(260, KUTU_Y + 8, 190, KUTU_Y + 8, "var(--s1)", 1.6, True))
        o.append(_yazi(300, 320, "Akım YÜK 1 → şönt → YÜK 2 yolundan geçer. COM'a krokodil takma: "
                                 "devrenin eksisine takarsan şönt baypas olur.", 11, "var(--m2)"))
        return _svg("".join(o), 600, 336, "Akım ve gerilim ölçümü")
    o.append(_dikdortgen(20, 30, 130, 90, "var(--yz2)"))
    o.append(_yazi(85, 66, "PİL", 13, "var(--m1)", "middle", True)); o.append(_yazi(85, 88, "≤ 38 V", 10, "var(--m3)"))
    o.append(_dikdortgen(250, 38, 140, 46, "var(--yz2)", "#2f7d5a"))
    o.append(_yazi(320, UST + 6, "YÜK DİRENCİ", 11, "var(--m1)", "middle", True))
    o.append(_yazi(320, 98, "örn. 3.3 Ω 11 W taş direnç", 10, "var(--m3)"))
    o.append(kutu_govde(150, 490, "ÖLÇÜM KUTUSU", "içeride: Q1 anahtarı + şönt · COM = PİL 2"))
    o.append(_cizgi(150, UST, 250, UST, KIR)); o.append(_yazi(200, UST - 12, "pil +", 10, "var(--m3)"))
    o.append(_cizgi(390, UST, 450, UST, KIR)); o.append(_cizgi(450, UST, 450, KUTU_Y, KIR))
    o.append(ucbas(450, MAV, "PİL 1", "direncin ucu"))
    o.append(ucbas(190, MAV, "PİL 2", "pilin eksisi"))
    o.append(_cizgi(190, KUTU_Y, 190, 170, SIY)); o.append(_cizgi(190, 170, 85, 170, SIY)); o.append(_cizgi(85, 170, 85, 120, SIY))
    o.append(_cizgi(350, KUTU_Y, 350, 140, KIR, 2.0, True)); o.append(_cizgi(350, 140, 210, 140, KIR, 2.0, True)); o.append(_cizgi(210, 140, 210, UST, KIR, 2.0, True))
    o.append(ucbas(350, KIR, "V jakı", "pilin artısı — ZORUNLU"))
    o.append(ucbas(260, "#2b2b2b", "COM", "BOŞ — içeride PİL 2", 1))
    o.append(_yazi(300, 320, "Kart Q1 ile yükü açıp kapatıyor, şöntten akımı okuyor, kesme "
                             "gerilimine inince kendi kesiyor. YÜK boş kalır.", 11, "var(--m2)"))
    return _svg("".join(o), 600, 336, "Pil kapasite testi")


# ═══════════════════════════════════════════════════════════════════════
#  3B SAHNE
# ═══════════════════════════════════════════════════════════════════════

def sahne() -> list[dict]:
    """Kutunun 3B blok listesi — WebGL ciziyor (kutu_3b.py).

    Veri ekseni: y=0 ARKA, y=ic_boy ON. Sahne sag-el: on duvar y<0 tarafinda.
    Tek donusum burada: cev(y0, dy) = ic_boy - y0 - dy. x cevrilmez (panel
    x'leri de ic koordinat). gor: gorunmeye basladigi alt adim; vur: alt
    adimlarin 'vurgu'/'monte' listelerinden; n: duvar disa normali ('yakin
    olanlar saydam' kipi bununla karar verir).
    """
    kb, h = K.KUTU, hesap()
    aa = alt_adimlar()
    ix = {x["no"]: i for i, x in enumerate(aa)}
    monte = monte_adim()
    bloklar = []

    def vur_ix(ref: str) -> list[int]:
        kok = ref.split(".")[0]
        return [ix[s["no"]] for s in aa
                if ref in s.get("vurgu", []) or kok in s.get("vurgu", []) or kok in s.get("monte", [])]

    def blok(ad, x, y, z, dx, dy, dz, renk, grup, gor, vur=None, n=None, on=None):
        b = {"ad": ad, "x": round(x, 2), "y": round(y, 2), "z": round(z, 2),
             "dx": round(dx, 2), "dy": round(dy, 2), "dz": round(dz, 2),
             "r": renk, "g": grup, "gor": gor, "vur": sorted({v for v in (vur or []) if v is not None})}
        if n:
            b["n"] = n
        if on:                                   # bu adimlarda hayalet onizleme (tezgahta hazirlanan parca)
            b["on"] = sorted(set(on))
        bloklar.append(b)

    t, g = h["t"], h["g"]
    dt = h["duvar_t"]
    en, boy, yuk = kb["ic_en"], kb["ic_boy"], h["ic_yuk"]
    ON, ARKA, SOL, SAG, UST = [0, -1, 0], [0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 0, 1]

    def cev(y0, dy):
        return boy - y0 - dy

    for i in range(h["taban_sira"]):                        # taban: siralar x yonunde
        y = -dt + i * g
        ek = taban_ek(i)
        for bas, b2 in ((0.0, ek), (ek, h["dis_en"] - ek)):
            blok(f"Taban sırası {i + 1}", -dt + bas, y, -t, b2 - 0.4, g - 0.5, t, "#c3a173", "kutu", ix["2.1"], [ix["2.1"]])
    for rx in (0.25, 0.75):
        ek = h["dis_boy"] * TABAN_EK[0 if rx < 0.5 else 1]
        for bas, b2 in ((0.0, ek), (ek, h["dis_boy"] - ek)):
            blok("Taban rayı", h["dis_en"] * rx - dt - g / 2, -dt + bas, -2 * t, g, b2 - 0.4, t, "#e0a92f", "kutu", ix["2.2"], [ix["2.2"]])
    for r in range(kb["duvar_sira"]):                       # dis kat: yatay siralar
        z = r * g
        gor = ix["4.1"] if r == 0 else ix["4.3"]
        gor_yan = ix["4.2"] if r == 0 else ix["4.3"]
        for panel, y0, nrm, delme in (("ön", -dt, ON, ix["3.1"]), ("arka", boy + dt - t, ARKA, ix["3.2"])):
            ek = ek_yerleri(panel)[r]
            for bas, b2 in ((0.0, ek), (ek, h["dis_en"] - ek)):
                blok(f"Dış kat {panel} {r + 1}", -dt + bas, y0, z, b2 - 0.4, t, g, "#c3a173", "duvar", gor, [gor], nrm,
                     on=[delme])
        ek = yan_ek(r)
        for bas, b2 in ((0.0, ek), (ek, h["yan_dis"] - ek)):
            blok(f"Dış kat sol {r + 1}", -dt, -dt + t + bas, z, t, b2 - 0.4, g, "#b0915f", "duvar", gor_yan, [gor_yan], SOL)
            blok(f"Dış kat sağ {r + 1}", en + dt - t, -dt + t + bas, z, t, b2 - 0.4, g, "#b0915f", "duvar", gor_yan, [gor_yan], SAG)
    gi = ix["4.5"]                                          # ic kat: deliklerden turetilmis
    for x0, w, z0 in h["ic_on"]:
        blok("İç kat ön", x0 + 0.2, -t, z0, w - 0.4, t, yuk - z0, "#d5b78a", "duvar_ic", gi, [gi], ON)
    for x0, w, z0 in h["ic_arka"]:
        blok("İç kat arka", x0 + 0.2, boy, z0, w - 0.4, t, yuk - z0, "#d5b78a", "duvar_ic", gi, [gi], ARKA)
    for y0, w in h["ic_yan"]:
        blok("İç kat sol", -t, cev(y0, w) + 0.2, 0, t, w - 0.4, yuk, "#c9a877", "duvar_ic", gi, [gi], SOL)
        blok("İç kat sağ", en, cev(y0, w) + 0.2, 0, t, w - 0.4, yuk, "#c9a877", "duvar_ic", gi, [gi], SAG)
    gd = ix["4.6"]
    for d in direkler():
        blok(f"Köşe direği {d['ref'][1]}", d["x"], cev(d["y"], d["boy"]), 0, d["en"], d["boy"], yuk, "#a07a48", "direk", gd, [gd])
    for x in panel_ogeleri():                               # delikler: dis yuzde koyu plaka
        on = x["panel"] == "ön"
        w, hh = delik_genislik(x), x["delik_mm"]
        y0 = -dt - 0.3 if on else boy + dt - 0.3
        delme = ix["3.1"] if on else ix["3.2"]
        r = int(x["z"] // g)                                # delik, duvar sirasiyla birlikte gorunur
        gor = ix["4.1"] if r == 0 else ix["4.3"]
        blok(f"delik {x['etiket']}", x["x"] - w / 2, y0, x["z"] - hh / 2, w, 0.6, hh, "#151515", "delik", gor,
             [delme, ix["5.1"]], ON if on else ARKA, on=[delme])
    for x in panel_ogeleri():                               # panel ogeleri: govde
        on = x["panel"] == "ön"
        if x["tip"] in ("yuva", "kuyruk"):
            continue
        w = x["metal_mm"] or 12
        gor = ix.get(monte.get(x["ref"].split(".")[0], ""), ix["5.2"])
        renk = JAK_RENK.get(x["renk"], "#8a8a85")
        if on:
            blok(x["etiket"], x["x"] - w / 2, -dt - 14, x["z"] - w / 2, w, dt + 14, w, renk, "panel", gor, vur_ix(x["ref"]))
            blok(x["etiket"] + " (iç)", x["x"] - w / 4, 0, x["z"] - w / 4, w / 2, x["derin_mm"], w / 2, "#555", "panel", gor, [])
        else:
            blok(x["etiket"], x["x"] - w / 2, boy, x["z"] - w / 2, w, dt + 14, w, renk, "panel", gor, vur_ix(x["ref"]))
            blok(x["etiket"] + " (iç)", x["x"] - w / 4, boy - x["derin_mm"], x["z"] - w / 4, w / 2, x["derin_mm"], w / 2, "#555", "panel", gor, [])
    kuy = next(o for o in panel_ogeleri("arka") if o["tip"] == "kuyruk")
    blok("XT30 kuyruğu", kuy["x"] - 3, boy + dt, kuy["z"] - 3, 6, 40, 6, "#d9a300", "panel",
         ix.get(monte.get("J6", ""), ix["5.3"]), vur_ix("J6"))
    for a in ayaklar():                                     # ayaklar / altliklar / kosebent / ek bloklar
        vur = [ix[a["adim"]]] + (vur_ix(a["sahip"]) if a["sahip"] else [])
        blok(a["ref"], a["x"], cev(a["y"], a["boy"]), a["z"], a["en"], a["boy"], a["yuk"], "#b8975f", "tasiyici", ix[a["adim"]], vur)
    for pp in K.IC_PARCA:
        gor = ix.get(monte.get(pp["ref"], ""), None)
        if gor is None:
            gor = {"A": ix["6.2"], "B": ix["6.3"], "ESP32": ix["6.3"]}.get(pp["ref"], ix["6.6"])
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == pp["ref"]), 0.0)
        blok(pp["ref"], pp["x"], cev(pp["y"], pp["boy"]), z0, pp["en"], pp["boy"], max(pp["yuk"] * 0.55, 6),
             PARCA_RENK.get(pp["ref"], "#666"), "parca", gor, vur_ix(pp["ref"]))
    gk = ix["13.1"]
    for i in range(h["taban_sira"]):                        # kapak: siralar x yonunde
        y = -dt + i * g
        ek = taban_ek(i, kapak=True)
        for bas, b2 in ((0.0, ek), (ek, h["dis_en"] - ek)):
            blok(f"Kapak sırası {i + 1}", -dt + bas, y, yuk, b2 - 0.4, g - 0.5, t, "#d9bb8c", "kapak", gk, [gk], UST)
    for r in kapak_raylari():
        blok("Kapak rayı", r["x"], cev(r["y"], r["boy"]), r["z"], r["en"], r["boy"], r["yuk"], "#e0a92f", "kapak", gk, [gk, ix["13.2"]], UST)
    for xw in (-dt - 1.5, en + dt - 1.5):
        for y in kb["kapak_civata_y"]:
            blok("Kapak cıvatası", xw, cev(y, 3), kb["kapak_civata_z"] - 1.6, 3, 3, 3.2, "#333333", "kapak", ix["13.2"], [ix["13.2"]], UST)
    return bloklar


# ═══════════════════════════════════════════════════════════════════════
#  BELGE
# ═══════════════════════════════════════════════════════════════════════

def _liste(xs) -> str:
    return "<ul class='is'>" + "".join(f"<li>{x}</li>" for x in xs) + "</ul>"


def _tablo(bas, satirlar) -> str:
    return ("<table><tr>" + "".join(f"<th>{b}</th>" for b in bas) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{h}</td>" for h in s) + "</tr>" for s in satirlar) + "</table>")


def kablo_tablosu(idx, nl, parcalar) -> str:
    sat = []
    for i in idx:
        a, b, tur, _adim, notu = V.KABLOLAR[i]
        delik = " / ".join(kablo_delikleri(i, nl, parcalar))
        sat.append((E(B._uc_adi(a)), E(B._uc_adi(b)), "<b>KALIN KABLO</b>" if tur == "yuk" else E(tur),
                    f"<b>{E(delik)}</b>" if delik else "—", f"<span class='kucuk'>{E(notu)}</span>"))
    return _tablo(("Nereden", "Nereye", "Tür", "Kart deliği", "Not"), sat)


def cizimler(s: dict) -> str:
    vurgu = set(s.get("vurgu", [])) | set(s.get("monte", []))
    tur = s["tur"]
    c = []
    if tur == "kesim" and s["no"] == "1.2":
        c.append(("Kesim listesi — şimdi kesilecekler", ciz_kesim(hesap()["kesim1"])))
    elif tur == "kesim" and s["no"] == "4.4":
        c.append(("Kesim listesi — duvar ölçüldükten sonra", ciz_kesim(hesap()["kesim2"])))
    elif tur == "taban":
        c.append(("Kapak — kuşbakışı" if s.get("kapak") else "Taban — kuşbakışı", ciz_taban(s.get("kapak", False))))
    elif tur == "duvar":
        c.append((f"{s['sira']}. sıra — izometrik", ciz_duvar(s["sira"])))
        c.append(("Ön duvar — ek yerleri", ciz_panel("ön", set(), ic_kat=False)))
        c.append(("Arka duvar — ek yerleri (arkadan bakış)", ciz_panel("arka", set(), ic_kat=False)))
    elif tur == "duvar_ic":
        c.append(("Ön duvar — iç kat çubukları", ciz_panel("ön", set())))
        c.append(("Arka duvar — iç kat çubukları (arkadan bakış)", ciz_panel("arka", set())))
    elif tur == "direk":
        c.append(("Kuşbakışı — köşe direkleri", ciz_yerlesim(set(), direk_vurgu=True)))
    elif tur in ("delik", "delik_parca"):
        paneller = [s.get("panel", "ön")] if tur == "delik_parca" or s["no"] != "5.1" else ["ön", "arka"]
        for p in paneller:
            c.append((f"{p.capitalize()} duvar — dışarıdan", ciz_panel(p, vurgu, ic_kat=(tur == "delik"))))
        if vurgu and tur == "delik" and s["no"] != "5.1":
            c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
    elif tur == "montaj":
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
        c.append(("İzometrik", ciz_izo(vurgu)))
    elif tur == "kablo":
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
        if any(r in {o["ref"] for o in panel_ogeleri("ön")} for r in vurgu):
            c.append(("Ön duvar", ciz_panel("ön", vurgu, ic_kat=False)))
        if any(r in {o["ref"] for o in panel_ogeleri("arka")} for r in vurgu):
            c.append(("Arka duvar (arkadan bakış)", ciz_panel("arka", vurgu, ic_kat=False)))
    return "".join(f"<figure><figcaption>{E(b)}</figcaption>{sv}</figure>" for b, sv in c)


def delik_tablosu_html(panel: str) -> str:
    h = hesap()
    ayna = panel == "arka"
    sat = []
    for d in sorted(delik_tablosu(panel), key=lambda q: (q["sira"], q["parca"], q["ofset"])):
        sat.append((f"<b>{E(d['etiket'])}</b>", f"{d['sira']}", f"{d['parca']} ({d['parca_boy']:.0f} mm)",
                    f"<b>{d['ofset']:.0f} mm</b>", f"{d['z_ic']:.0f} mm", E(d["cap"])))
    ekler = ek_yerleri(panel)
    ek_metin = ", ".join(f"{r + 1}. sıra {(arka_ayna(x) if ayna else x):.0f}" for r, x in enumerate(ekler))
    return (_tablo(("Delik", "Sıra", "Parça", "Parçanın sol ucundan", "Çubuğun alt kenarından", "Çap"), sat)
            + f"<p class='kucuk'>Ölçüler <b>{'arkaya geçip arkadan' if ayna else 'önden'} bakan kişinin solundan</b>. "
              f"Sıra {h['dis_en']:.0f} mm, iki parça; ek yerleri (soldan): {E(ek_metin)}. "
              "Sol parça sıfırdan ek yerine, sağ parça ek yerinden sona. Deliksiz sıralar da aynı ek yerleriyle.</p>")


def ek_tablosu_html() -> str:
    h = hesap()
    sat = []
    for r, (a, b) in enumerate(zip(ek_yerleri("ön"), ek_yerleri("arka"))):
        sat.append((f"{r + 1}", f"{a:.0f} + {h['dis_en'] - a:.0f}", f"{arka_ayna(b):.0f} + {h['dis_en'] - arka_ayna(b):.0f}",
                    f"{yan_ek(r):.0f} + {h['yan_dis'] - yan_ek(r):.0f}"))
    return (_tablo(("Sıra", "Ön (sol + sağ, önden)", "Arka (sol + sağ, arkadan)", "Yanlar (önden arkaya)"), sat)
            + "<p class='kucuk'>Her sıra iki parça; sayılar parça boyu, soldan sağa. Ek yerleri deliklerden ≥ "
              f"{EK_DELIK_PAYI:.0f} mm uzakta ve ardışık sıralarda ≥ {EK_KAYDIRMA:.0f} mm kaymış (denetimli). "
              "Yan sıralar ön ve arka dış katların arasına girer.</p>")


def ic_kat_tablosu_html() -> str:
    kb, h = K.KUTU, hesap()
    sat = []
    for panel in ("ön", "arka"):
        cub = ic_kat_cubuklari(panel)
        sat.append((E(panel), ", ".join(f"{x0:.0f}" + (f" (kısa, z {z0:.0f}'dan)" if z0 else "") for x0, _w, z0 in cub),
                    f"{len(cub)}"))
    yan = ic_kat_yan()
    sat.append(("sol / sağ (y)", ", ".join(f"{y0:.0f}" for y0, _w in yan), f"{len(yan)} × 2"))
    return (_tablo(("Duvar", "Çubuk sol kenarları (mm, İÇ sol köşeden — önden bakınca)", "Adet"), sat)
            + "<p class='kucuk'>Ön/arka çubuklar iç sol köşeden ölçülür (ikisi de önden bakan kişinin solundan; arka "
              "duvarda içeriden bakarken sağdan sayman gerekir). Her delik bir çubuğun ortasına geliyor; aradaki dar "
              f"boşluklar boş kalır. Yan çubuklar arka iç köşeden. Direkler köşede {h['direk_t']:.0f} mm; "
              f"kapak rayı direkler arasında ({h['kapak_ray']:.0f} mm).</p>")


def alt_kart(s: dict, nl, parcalar, stok, h) -> str:
    kb = K.KUTU
    bicim = {"u": K.CUBUK["uzunluk"], "g": h["g"], "k": h["t"], "sira": kb["duvar_sira"], "h": h["ic_yuk"],
             "ue": K.CUBUK["uc_egim"], "duz": h["duz"], "direk_g": h["g"], "direk_t": h["direk_t"],
             "direk_kat": kb["direk_kat"], "kapak_civata": kb["kapak_civata"], "dis_en": h["dis_en"],
             "dis_boy": h["dis_boy"], "taban_sira": h["taban_sira"], "kapak_ray": h["kapak_ray"]}
    ic = [f"<div class='aa-bas'><span class='ano'>{E(s['no'])}</span> <b>{E(s['baslik'])}</b>"
          f"<label class='yaptim'><input type='checkbox'> yaptım</label></div>", "<div class='aa-ic'>"]
    if s.get("monte"):
        def _stok(r):
            kayit = next((o["parca"] for o in panel_ogeleri() if o["ref"].split(".")[0] == r and o["parca"]), None) \
                or next((p.get("stok") for p in K.IC_PARCA if p["ref"] == r), None)
            return stok.ad_ile(*kayit) if (kayit and stok.var) else ""
        ic.append(_tablo(("Kutuya giren", "Kural", "Stokta"),
                         [(f"<b>{E(r)}</b>", E(V.KART_DISI_NOTU.get(r, "")), _stok(r)) for r in s["monte"]]))
    if s.get("yap"):
        ic.append(_liste(x.format(**bicim) for x in s["yap"]))
    ic.append(cizimler(s))
    KAYNAK_AD = {"duz": "düz bölümden", "yarim": "çubuk ortadan ikiye"}
    if s["no"] == "1.2":
        ic.append(_tablo(("Parça", "Uzunluk", "Adet", "Nereden"),
                         [(E(ad), f"{u:.0f} mm", f"<b>{adet}</b>", KAYNAK_AD[kk]) for ad, u, adet, kk in h["kesim1"]]))
        ic.append(f"<div class='uy'>Bütün plan için <b>{h['cubuk_sayisi']} çubuk</b> gerekiyor "
                  f"({KERF:.0f} mm testere payıyla, {h['artik']:.0f} mm artık). Elde ~{kb['elde_cubuk']}: en az "
                  f"<b>{h['eksik']}</b> daha, fire payıyla {h['eksik_pay']}.</div>")
    if s["no"] == "4.4":
        ic.append(_tablo(("Parça", "Uzunluk (nominal)", "Adet", "Nereden"),
                         [(E(ad), f"{u:.0f} mm", f"<b>{adet}</b>", KAYNAK_AD[kk]) for ad, u, adet, kk in h["kesim2"]]))
    if s["tur"] == "delik_parca":
        ic.append("<h4>Delik tablosu — parça parça</h4>")
        ic.append(delik_tablosu_html(s["panel"]))
    if s["no"] in ("4.1", "4.3"):
        ic.append("<h4>Parça boyları ve ek yerleri</h4>")
        ic.append(ek_tablosu_html())
    if s["no"] == "4.5":
        ic.append("<h4>İç kat çubuk konumları</h4>")
        ic.append(ic_kat_tablosu_html())
    if s["no"] == "13.2":
        ic.append(_tablo(("Duvar", "y (arka dış köşeden)", "z (tabandan)", "Cıvata"),
                         [(d, f"{y + h['duvar_t']:.0f} mm", f"{kb['kapak_civata_z']:.0f} mm", kb["kapak_civata"])
                          for d in ("sol", "sağ") for y in kb["kapak_civata_y"]]))
    if s.get("kablo"):
        ic.append("<h4>Bağlanacak kablolar</h4>")
        ic.append(kablo_tablosu(s["kablo"], nl, parcalar))
    if s["no"] in ("9.1", "9.2", "9.3"):
        ic.append("<h4>Yol kontrolü — jaktan karta</h4>")
        ic.append("<p class='kucuk'>Bölücüler GND'ye değil VREF'e iniyor; jak ile COM arası enerji yokken sonsuz "
                  "okur. Anlamlı ölçüm jak ile VREF arası: kartta U3'ün 1. bacağı, delik <b>A:R8</b>.</p>")
        ic.append(_tablo(("Uç 1", "Uç 2", "Beklenen"),
                         [(E(ad), "A:R8 (VREF)", f"<b>≈ {B._oku(r)}</b> (±%2)") for ad, _ag, r in giris_direncleri(nl, parcalar)]))
    if s["tur"] == "kalibrasyon":
        ke = kalib_esikleri()
        ic.append("<p class='kucuk'>Seri konsoldan (USB). Her komut ayarı NVS'e yazar. Kazanç kalibrasyonu "
                  f"(<code>i</code>, <code>g</code>) tam skalanın %{KALIB_ESIK_ORANI * 100:.0f}'inin altındaki "
                  "değeri reddeder — 'en az' sütunu.</p>")
        enaz = {"i&lt;amper&gt;": f"{ke['i']:.2f} A",
                "g&lt;volt&gt;": f"{ke['g_normal']:.1f} V (NORMAL) · {ke['g_yuksek']:.0f} V (YÜKSEK)"}
        ic.append(_tablo(("Komut", "Ne yapar", "Ne zaman", "En az"),
                         [(f"<code>{k}</code>", E(n), E(z), enaz.get(k, "—")) for k, n, z in K.KALIBRASYON]))
    for k in s.get("kapi", []):
        gerek = ", ".join(sorted(kapi_gerek().get(k, set()))) or "—"
        ic.append(f"<div class='ok'><b>KAPI {k}</b> — {B.KAPI.get(k, '')}"
                  f"<div class='kucuk'>gerekli kart dışı parça: {E(gerek)}</div></div>")
    if s.get("kontrol"):
        ic.append("<h4>Kontrol</h4>")
        ic.append(_liste(s["kontrol"]))
    ic.append("</div>")
    return f"<li class='aa' data-no='{E(s['no'])}'>" + "".join(ic) + "</li>"


def malzeme_ayir(stok) -> tuple[list, list]:
    """MALZEME'yi envantere gore boler: (stokta [(kayit, html)], alinacak [kayit])."""
    stokta, alinacak = [], []
    for m in K.MALZEME:
        k = stok.ad_ile(*m["stok"]) if (m["stok"] and stok.var) else ""
        if k and "kayıtta yok" not in k:
            stokta.append((m, k))
        else:
            alinacak.append(m)
    return stokta, alinacak


def on_kosul_html(nl, parcalar) -> str:
    """Yerlesim planinda bitmis olmasi gerekenler (kutu_veri.ON_KOSUL) + kart-kart kablolar."""
    sat = [(f"<a href='7-yerlesim.html#s{no}'>Yerleşim {no}</a>", ne) for no, ne in K.ON_KOSUL]
    for i, c in enumerate(V.KABLOLAR):
        if c[0].startswith("X:") or c[1].startswith("X:"):
            continue
        d = kablo_delikleri(i, nl, parcalar)
        sat.append(("Kart-kart tel", f"{E(c[0][0])}:{E(d[0])} → {E(c[1][0])}:{E(d[1])} "
                                     f"<span class='kucuk'>({E(c[0])} → {E(c[1])}: {E(c[4][:60])})</span>"))
    return _tablo(("Nerede", "Ne"), sat)


def arayuz_html() -> tuple[str, dict]:
    """CAD / 3D baski icin kutu arayuzu: sayilar + JSON."""
    h, kb = hesap(), K.KUTU
    veri = {"eksen": "x sol->sag (onden bakinca), y=0 arka duvar ic yuzu, y=ic_boy on duvar, z taban; mm",
            "ic_mm": [kb["ic_en"], kb["ic_boy"], h["ic_yuk"]], "duvar_mm": h["duvar_t"],
            "direk_mm": [h["direk_t"], h["g"]], "kacak_yolu_mm": T.IEC60664_CREEPAGE_TAKVIYELI,
            "kapak_civata": {"tip": kb["kapak_civata"], "y": list(kb["kapak_civata_y"]), "z": kb["kapak_civata_z"]},
            "ic_parcalar": [{k2: p[k2] for k2 in ("ref", "x", "y", "en", "boy", "yuk")} for p in K.IC_PARCA],
            "panel": [{k2: o.get(k2) for k2 in ("ref", "panel", "x", "z", "delik_mm", "yuva_en_mm", "metal_mm", "derin_mm", "tip")}
                      for o in panel_ogeleri()],
            "tasiyicilar": [{k2: a[k2] for k2 in ("ref", "x", "y", "z", "en", "boy", "yuk")} for a in ayaklar()]}
    sat_ic = [(f"<b>{E(p['ref'])}</b>", f"{p['x']:.1f}", f"{p['y']:.1f}", f"{p['en']:.1f} × {p['boy']:.1f}", f"{p['yuk']:.0f}") for p in K.IC_PARCA]
    sat_p = [(f"<b>{E(o['ref'])}</b>", E(o["panel"]), f"{o['x']:.0f}", f"{o['z']:.0f}",
              f"{o['yuva_en_mm']:.0f} × {o['delik_mm']:.0f}" if o["tip"] == "yuva" else f"Ø{o['delik_mm']:.1f}",
              f"{o['derin_mm']:.0f}") for o in panel_ogeleri()]
    html = ("<p>İleride 3D baskı ya da başka bir kaba geçersen ihtiyacın olan her sayı burada; aynı veri "
            "JSON olarak da gömülü (<code>&lt;script id='kutu-arayuz'&gt;</code>). Panel x'leri iç sol köşeden, "
            "önden bakınca — arka panel için de aynı eksen.</p>"
            + _tablo(("İç ölçü", "Duvar", "Köşe direği", "HV kaçak yolu", "Kapak cıvatası"),
                     [(f"{kb['ic_en']:.0f} × {kb['ic_boy']:.0f} × {h['ic_yuk']:.0f} mm", f"{h['duvar_t']:.0f} mm",
                       f"{h['direk_t']:.0f} × {h['g']:.0f} mm", f"≥ {T.IEC60664_CREEPAGE_TAKVIYELI} mm",
                       f"{kb['kapak_civata']}, yan duvar, y {kb['kapak_civata_y'][0]:.0f}/{kb['kapak_civata_y'][1]:.0f}, z {kb['kapak_civata_z']:.0f}")])
            + "<h4>İç parçalar (sol-arka köşe, mm)</h4>" + _tablo(("Ref", "x", "y", "en × boy", "yük"), sat_ic)
            + "<h4>Panel delikleri (mm)</h4>" + _tablo(("Ref", "Panel", "x", "z", "Delik", "İçeri uzantı"), sat_p))
    return html, veri


def yaz(nl, parcalar, hedef: Path) -> None:
    stok = B.Stok()
    h = hesap()
    c, kb = K.CUBUK, K.KUTU
    aa = alt_adimlar()
    mz = menziller()
    g = []
    g.append("<h2>Bu belge ne</h2>")
    g.append(_liste([
        "Kartlar bitti. Bundan sonrası: <b>çubuktan kutu</b>, panel delikleri, şönt ve Q1, jaklar, kablolar, testler.",
        f"Kutu <b>{c['ad']}</b> ({c['uzunluk']:.0f} × {c['genislik']:.0f} × {c['kalinlik']:.0f} mm) çubuklardan. "
        f"İç ölçü <b>{kb['ic_en']:.0f} × {kb['ic_boy']:.0f} × {h['ic_yuk']:.0f} mm</b>, dış "
        f"{h['dis_en']:.0f} × {h['dis_boy']:.0f} × {h['ic_yuk'] + 2 * h['t']:.0f}.",
        f"<b>Sağlamlık:</b> duvarlar iki kat (dışta {kb['duvar_sira']} yatay sıra, içte dikey çubuklar; {h['duvar_t']:.0f} mm), "
        f"dört köşede {h['direk_t']:.0f} × {h['g']:.0f} mm direk; kapak yan duvarlardan {kb['kapak_civata']} "
        "cıvata + somunla tak-çıkar; kartlar gömme somunlu ayaklara vidalı. Taban ve kapak parçaları düz bölümden: "
        "yuvarlak uç hiçbir duvarın altına gelmiyor. Delikler duvar dikilmeden, parça düz zemindeyken.",
        "<b>Kural:</b> kutuya giren hiçbir parça yapıştırılmaz (vida, kablo bağı, konnektör); kutunun kendi "
        "parçaları (çubuk, ayak, altlık) yapıştırılır.",
        "<b>Kullanım sınırı:</b> yalnız pil / DC-DC beslemeli, toprağa göre yüzen devreler. HV ölçerken USB takılı olmaz.",
        "Aşağıda <b>ileri / geri</b> ile tek tek ilerle; 3B görünüm adım şeridinin altında (sürükle: döndür, "
        "Ctrl+tekerlek: yakınlaştır). Tezgahta telefondan: <code>python uretim/belge_sun.py</code>.",
    ]))
    g.append("<h3>Başlamadan önce — Yerleşim planında bitmiş olmalı</h3>")
    g.append(on_kosul_html(nl, parcalar))
    bicim_al = dict(kb, cubuk=h["cubuk_sayisi"], elde=kb["elde_cubuk"], eksik=h["eksik"], eksik_pay=h["eksik_pay"])
    stokta, alinacak = malzeme_ayir(stok)
    g.append("<h3>Stoktan çıkar</h3>")
    g.append(_tablo(("Ne", "Kayıt", "Not"), [(f"<b>{E(m['ad'])}</b>", k, E(m["not"].format(**bicim_al)))
                                             for m, k in stokta]) if stokta else "<p class='kucuk'>—</p>")
    g.append("<h3>Alınacak</h3>")
    g.append(_tablo(("Ne", "Not"), [(f"<b>{E(m['ad'])}</b>", E(m["not"].format(**bicim_al))) for m in alinacak])
             if alinacak else "<p class='kucuk'>Alınacak bir şey yok.</p>")

    kartlar = "".join(alt_kart(s, nl, parcalar, stok, h) for s in aa)
    basliklar = json.dumps([{"no": s["no"], "b": s["baslik"], "a": s["adim"], "ab": s["adim_baslik"]} for s in aa], ensure_ascii=False)
    adim_dugme = "".join(f"<button data-git='{a['no']}'>{a['no']}</button>" for a in K.ADIMLAR)
    g.append(f"""
<div class="gorus">
  <div class="gorus-ust">
    <button id="geri">◀ geri</button>
    <div class="gorus-bilgi"><span class="ano" id="g-no"></span> <b id="g-baslik"></b> <span class="rozet" id="g-adim"></span></div>
    <button id="ileri">ileri ▶</button>
  </div>
  <div class="gorus-alt"><div class="adimsec">{adim_dugme}</div><span class="kucuk" id="g-sayac"></span></div>
  <div class="cubuk"><div id="g-cubuk"></div></div>
</div>
{U.PANEL_HTML}
<ol class="aalist" id="aalist">{kartlar}</ol>""")

    g.append("<section class='buyuk'><h2>Bitince: neyi nereden ölçerim</h2>")
    g.append(_tablo(("Ölçüm", "Hangi uç", "Nasıl bağlanır", "Çözünürlük"),
                    [(f"<b>{E(a.format(**mz))}</b>", f"<b>{E(b)}</b>", c2.format(**mz), f"<span class='kucuk'>{E(d)}</span>")
                     for a, b, c2, d in K.KULLANIM]))
    g.append("<h3>Akım ve gerilim ölçümü — bağlantı</h3>")
    g.append("<figure><figcaption>YÜK jakları devreye SERİ girer; COM içeride YÜK 2'dir</figcaption>" + ciz_kullanim("akim") + "</figure>")
    g.append("<h3>Pil kapasite testi — bağlantı</h3>")
    g.append("<figure><figcaption>PİL jakları deşarj yolu; V jakı zorunlu</figcaption>" + ciz_kullanim("pil") + "</figure>")
    g.append("</section>")
    ara_html, ara_veri = arayuz_html()
    g.append("<section class='buyuk'><h2>Kutu arayüzü — 3D baskı / başka kap için</h2>" + ara_html + "</section>")
    g.append(f"<script id='kutu-arayuz' type='application/json'>{json.dumps(ara_veri, ensure_ascii=False)}</script>")

    ek_stil = U.PANEL_CSS + """
.gorus{position:sticky;top:0;z-index:9;background:var(--yz);border:1px solid var(--cizgi);border-radius:14px;padding:10px 12px;margin:18px 0}
.gorus-ust{display:flex;align-items:center;gap:12px}
.gorus-ust button{font:inherit;padding:6px 14px;border-radius:99px;cursor:pointer;border:1px solid var(--cizgi);background:var(--yz2);color:var(--m1)}
.gorus-bilgi{flex:1;text-align:center}
.gorus-alt{display:flex;justify-content:space-between;align-items:center;margin-top:8px}
.adimsec button{font:inherit;font-size:12px;padding:2px 9px;margin-right:4px;border-radius:99px;border:1px solid var(--cizgi);background:transparent;color:var(--m2);cursor:pointer}
.adimsec button.sec{background:var(--s1);color:#fff;border-color:var(--s1)}
.cubuk{height:4px;background:var(--cizgi);border-radius:2px;margin-top:8px}
.cubuk div{height:100%;background:var(--s3);border-radius:2px;width:0}
.aalist{list-style:none;padding:0;margin:0}
.aa{border:1px solid var(--cizgi);border-radius:14px;padding:16px 18px;margin:14px 0;scroll-margin-top:104px}
.aa[hidden]{display:none}
.aa-bas{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.ano{font:600 13px ui-monospace,Consolas,monospace;background:var(--s1);color:#fff;border-radius:99px;padding:2px 10px}
.yaptim{margin-left:auto;font-size:13px;color:var(--m2);cursor:pointer}
.buyuk{border:1px solid var(--cizgi);border-radius:14px;padding:18px 20px;margin:26px 0}
ul.is{margin:8px 0 14px;padding-left:20px}
ul.is li{margin:6px 0}
figure{margin:14px 0;padding:10px;border:1px solid var(--cizgi);border-radius:10px;background:var(--yz2);overflow-x:auto}
figure figcaption{font-size:12px;color:var(--m3);margin-bottom:6px}
figure svg{width:100%;min-width:460px;height:auto;display:block}
h4{margin:16px 0 6px;font-size:14px;color:var(--m2);text-transform:uppercase;letter-spacing:.04em}
@media (max-width:640px){ figure svg{min-width:340px} .gorus-ust button{padding:8px 12px} }
"""
    js = """<script>
(function(){
 var S = __ALTADIM__;
 var kartlar = [].slice.call(document.querySelectorAll('.aa'));
 var cur = 0, yaptim = {};
 try { yaptim = JSON.parse(localStorage.getItem('kutu-yaptim') || '{}'); } catch(e) {}
 function kaydet(){ try { localStorage.setItem('kutu-yaptim', JSON.stringify(yaptim)); } catch(e) {} }
__JS_3B__
 function kaydirGor(el){
   var g = document.querySelector('.gorus');
   var pay = (g ? g.getBoundingClientRect().height : 96) + 10;
   var y = el.getBoundingClientRect().top + window.pageYOffset - pay;
   window.scrollTo({top: Math.max(0, y), behavior: 'smooth'});
 }
 function goster(i, kaydir){
   cur = Math.max(0, Math.min(S.length - 1, i));
   kartlar.forEach(function(k, j){ k.hidden = j !== cur; });
   var s = S[cur];
   document.getElementById('g-no').textContent = s.no;
   document.getElementById('g-baslik').textContent = s.b;
   document.getElementById('g-adim').textContent = 'Adım ' + s.a + ' — ' + s.ab;
   var bitti = S.filter(function(x){ return yaptim[x.no]; }).length;
   document.getElementById('g-sayac').textContent = (cur+1) + ' / ' + S.length + ' · yapılan ' + bitti;
   document.getElementById('g-cubuk').style.width = (100*bitti/S.length) + '%';
   [].forEach.call(document.querySelectorAll('.adimsec button'), function(b){ b.classList.toggle('sec', String(s.a) === b.dataset.git); });
   try { history.replaceState(null, '', '#a' + s.no); } catch(e) {}
   ciz();
   if (kaydir) kaydirGor(document.querySelector('.uc-boyut') || kartlar[cur]);
 }
 kartlar.forEach(function(k, j){
   var kutucuk = k.querySelector('.yaptim input');
   kutucuk.checked = !!yaptim[S[j].no];
   kutucuk.addEventListener('change', function(){
     if (kutucuk.checked) yaptim[S[j].no] = 1; else delete yaptim[S[j].no];
     kaydet(); goster(cur, false);
   });
 });
 document.getElementById('geri').addEventListener('click', function(){ goster(cur-1, true); });
 document.getElementById('ileri').addEventListener('click', function(){ goster(cur+1, true); });
 [].forEach.call(document.querySelectorAll('.adimsec button'), function(b){
   b.addEventListener('click', function(){ for (var i = 0; i < S.length; i++) if (String(S[i].a) === b.dataset.git) { goster(i, true); return; } });
 });
 document.addEventListener('keydown', function(ev){
   if (ev.target.closest && ev.target.closest('input,textarea,select,canvas')) return;
   if (ev.key === 'ArrowRight') { goster(cur+1, true); ev.preventDefault(); }
   if (ev.key === 'ArrowLeft') { goster(cur-1, true); ev.preventDefault(); }
 });
 function adresten(){
   var m = /^#a([0-9.]+)$/.exec(location.hash);
   if (!m) return -1;
   for (var i = 0; i < S.length; i++) if (S[i].no === m[1]) return i;
   return -1;
 }
 window.addEventListener('hashchange', function(){ var i = adresten(); if (i >= 0) goster(i, true); });
 var bas = adresten();
 goster(bas >= 0 ? bas : 0, false);
})();
</script>""".replace("__JS_3B__", U.JS_3B).replace("__ALTADIM__", basliklar).replace(
        "__SAHNE__", json.dumps(sahne(), ensure_ascii=False))

    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kutu ve panel — Ölçüm Kartı</title><style>{B.stil()}{ek_stil}</style></head><body>
<div class="kutu">{MN.serit('8-kutu.html')}
<h1>Kutu ve panel</h1>
<p class="alt">Çubuktan kutu, panel delikleri, şönt ve Q1, jaklar, kablolar — alt adım alt adım,
her birinin çizimi ve 3B görünümüyle. Sonunda hangi ölçümü nereden yapacağın yazıyor.</p>
{''.join(g)}
<p class="kucuk" style="margin-top:60px;border-top:1px solid var(--cizgi);padding-top:14px">
Bu sayfa <code>uretim/kutu.py</code> tarafından, denetim geçtikten sonra üretildi. Kutu ölçüleri ve
adımlar <code>kutu_veri.py</code>'den, kablolar <code>yerlesim3_veri.KABLOLAR</code>'dan, KAPI metinleri
<code>yerlesim3_belge.KAPI</code>'dan, menziller <code>tasarim3_sabit</code>'ten; çizimler, tablolar ve 3B sahne
aynı sayılardan üretiliyor.</p>
</div>{js}</body></html>"""
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(sayfa, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--belge-yok", action="store_true")
    a = ap.parse_args()
    nl = Y.Netlist(Y.NETLIST)
    parcalar = Y.parcalari_yukle()
    print("  KUTU / PANEL PLANI — denetim")
    D = denetle(nl, parcalar)
    print("\n  OZET")
    print(f"  {D.gecti}/{D.gecti + D.kaldi} dogrulama gecti")
    if D.kaldi == 0 and not a.belge_yok:
        yaz(nl, parcalar, BELGE)
        print(f"  belge: {BELGE.relative_to(KOK)}")
    return 0 if D.kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
