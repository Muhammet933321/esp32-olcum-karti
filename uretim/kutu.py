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
    USB oval yuva ESP32 soket yuksekliginde, SARJ yuvasi onun aynasi (B58:
    dis besleme yok, tek sarj girisi);
  * COM baypas uyarisi, sanal COM kablolari listede degil, kalibrasyon
    esikleri sabitten, on kosul kutusu, CAD arayuz tablosu.

  python kutu.py            # denetim + belge
  python kutu.py --belge-yok
"""
from __future__ import annotations

import argparse
import json
import itertools
import math
import re
import sys
from functools import lru_cache
from html import unescape as html_unescape
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
TABAN_RAY_X = (0.25, 0.75)  # taban raylarinin merkezi (dis enin orani) — kutu BU IKI RAYIN
                            # uzerinde durur: destek acikligi, ray yuk payi ve devrilme
                            # acisi buradan cikar (tek kaynak; sahne, kutle ve denetim ayni)
KALIB_ESIK_ORANI = 0.05     # firmware: kazanc kalibrasyonu tam skalanin %5'inden az olmaz
KAYNAK_AD = {"duz": "düz bölümden", "yarim": "çubuk ortadan ikiye",
             "tek_uc": "tam çubuktan (bir yuvarlak uç parçada kalır)"}   # kesim kaynagi -> metin
TAHTA_BEL = 0.20            # cubuk kutlesinin goreli belirsizligi (yogunluk 0.55-0.78)
KART_AM_ORANI = 0.40        # kartin AM'si: plaket yuzu + parca boyunun %40'i
KABLO_AM_Z = 20.0           # mm — dagilmis kablo demetinin ortalama yuksekligi (ic zeminden)
AM_KOTU_EN_AZ = 1.0         # mm — kotu hal nominali en az bu kadar asmali (katman bos degil)
STOK_ATLANDI = False        # envanter okunamadiysa 7 · STOK bolumu dusuyor (B55g):
                            # ozet satiri bunu SOYLEMEK zorunda, yoksa eksik kosu
                            # tam kosudan ayirt edilemiyor
CAL_ASGARI_KOD = 50         # CAL kare dalgasi skopta en az bu kadar ADC kodu genlikte
                            # olmali. 50 kod: iki seviye ve kenar, gurultu tabani
                            # (B44: ~60 kodluk tek-ornek igne) ile karistirilmadan
                            # okunur. Yuzde degil KOD, cunku okunabilirligi sinirlayan
                            # sey menzil degil cozunurluk (SKOP_ADIM).
E = B.e

AHSAP = {"ust": "#d9bb8c", "on": "#c3a173", "yan": "#a88a5d", "cizgi": "#7d6540"}
VURGU = {"ust": "#f2c14e", "on": "#e0a92f", "yan": "#c08f1f", "cizgi": "#7a5a00"}
PARCASIZ_TIP = {"yuva", "havalandirma"}   # kendi parcasi olmayan panel ogeleri
PARCA_RENK = {"A": "#3d6aa8", "B": "#8a3ca8", "ESP32": "#2f7d5a",
              "RS": "#b3261e", "Q1": "#8a6e42"}
JAK_RENK = {"kirmizi": "#c8372a", "siyah": "#2b2b2b", "sari": "#d9a300",
            "gri": "#8a8a85", "mavi": "#2f66c4", "yesil": "#2e9b4f"}
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


def jak_azami_gerilim(ref: str) -> float:
    """Bir panel jakinda olcum sirasinda bulunabilecek en buyuk |gerilim| (kart GND'ye gore).
    B59: CAL'in arıza hesabi yalniz PIL gerilimini (38 V) varsayiyordu; CAL panelde yer
    degistirince komsulari degisti (SKOP −63.5 V). Tehdit artik komsularin GERCEK menzilinden."""
    normal, hv = T.KANALLAR[0], T.KANALLAR[1]
    return {"J1.1": normal["fs_sim"], "J2.1": hv["fs_sim"],
            "J4.1": max(abs(T.SKOP_MENZIL_EKSI), abs(T.SKOP_MENZIL_ARTI)),
            "J7.1": T.PIL_GIRIS_AZAMI_V, "J7.2": T.PIL_GIRIS_AZAMI_V,
            "J3.1": T.PIL_GIRIS_AZAMI_V, "J3.2": T.PIL_GIRIS_AZAMI_V, "J1.2": 0.0}.get(ref, 0.0)


def cal_komsulari() -> list[dict]:
    cal = next(q for q in panel_ogeleri("ön") if q["ref"] == "CAL")
    return sorted((q for q in panel_ogeleri("ön") if q["tip"] == "jak" and q["ref"] != "CAL"
                   and math.dist((q["x"], q["z"]), (cal["x"], cal["z"])) <= K.CAL_KOMSU_R),
                  key=lambda q: q["x"])


def cal_tehdit_gerilimi() -> tuple[float, float]:
    """(en buyuk |V|, en buyuk ARTI V) — CAL'in komsularindan yanlis delikle gelebilecek."""
    ks = cal_komsulari()
    arti = {"J4.1": T.SKOP_MENZIL_ARTI}
    return (max((jak_azami_gerilim(q["ref"]) for q in ks), default=0.0),
            max((arti.get(q["ref"], jak_azami_gerilim(q["ref"])) for q in ks), default=0.0))


def panel_bosluk(ref: str) -> list[float]:
    """Bir panel ogesinin AYNI paneldeki her komsusuna metal-metal bosluklari (B56).

    Metinlerde 'komsu jaklara >= 20 mm' gibi sayilar ELLE yaziliydi ve panel
    yeniden dizilince eskidi."""
    o = next(q for q in panel_ogeleri() if q["ref"] == ref)
    r = max(o["metal_mm"], delik_genislik(o)) / 2
    out = []
    for q in panel_ogeleri(o["panel"]):
        if q["ref"] == ref or q["tip"] == "civata":
            continue
        rq = max(q["metal_mm"], delik_genislik(q)) / 2
        out.append(math.dist((o["x"], o["z"]), (q["x"], q["z"])) - r - rq)
    return out


def panel_etiketleri() -> str:
    """16.1'in etiket listesi — ELLE yazilmis ve panel verisinden kaymisti (B55n).
    Civata delikleri kullaniciya gorunmez, onlar disarida."""
    sat = []
    for p in ("ön", "arka"):
        ad = []
        for o in panel_ogeleri(p):
            # civata delikleri ve havalandirma kullaniciya gorunmez/adsiz: etiketlenmez
            if o["tip"] in ("civata", "havalandirma") or not o.get("etiket"):
                continue
            alt = o.get("alt_etiket")
            ad.append(f"<b>{E(o['etiket'])}</b>" + (f" <span class='kucuk'>({E(alt)})</span>" if alt else ""))
        sat.append(f"<b>{p.capitalize()} panel:</b> " + " · ".join(ad))
    return "<br>".join(sat)


def ic_konum_satirlari(s: dict) -> list[tuple]:
    """Adimda vurgulanan TABAN parcalarinin konumu (B55n).

    Adim metinleri "plandaki yere koy" diyordu; sayilar yalnizca belgenin en
    sonundaki "kutu arayuzu" bolumundeydi ve kullanici montaj sirasinda orayi
    acmiyor. Kusbakisi cizim var ama mm okunmuyor."""
    refs = set(s.get("vurgu") or []) | set(s.get("monte") or [])
    sat = []
    for p in list(K.IC_PARCA) + kutu_ek_parcalari():
        # kutunun kendi ek bloklari 'vurgu'da gecmiyor, kendi 'adim' alanini tasiyor
        if p["ref"] in refs or p.get("adim") == s["no"]:
            sat.append((f"<b>{E(p['ref'])}</b>", f"{p['x']:.0f}", f"{p['y']:.0f}",
                        f"{p['en']:.0f} × {p['boy']:.0f}", f"{p.get('yuk', 0):.0f}"))
    return sat


def adim_etiketleri(s: dict) -> str:
    """Bir adimin KENDI monte listesindeki panel ogelerinin etiketleri (B55n)."""
    ad = []
    for r in s.get("monte", []):
        for o in panel_ogeleri():
            if o["ref"].split(".")[0] == r and o.get("etiket") and o["etiket"] not in ad:
                ad.append(o["etiket"])
    return " · ".join(f"<b>{E(x)}</b>" for x in ad)


def yuvarlak_mi(o: dict) -> bool:
    """Arkasina ic kat cubugu ortalanan ogeler (her delik/yuva). Civata delikleri
    sabit cubuk istemez: var olan bir cubugun icine denk getirilir (denetim)."""
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
    rs = T.SONT_TAKILI
    i_maks = min(T.ADS_AKIM_KIRPMA / rs, T.SONT_AKIM_ISIL[rs])
    normal, hv = T.KANALLAR[0], T.KANALLAR[1]
    return {"normal": f"±{normal['fs_sim']:.0f} V", "yuksek": f"±{hv['fs_sim']:.0f} V",
            "skop": f"{T.SKOP_MENZIL_EKSI:.0f} … +{T.SKOP_MENZIL_ARTI:.0f} V",
            "akim": f"{i_maks:.1f} A", "pil_akim": f"{min(T.PIL_AKIM_SOGUTUCUSUZ, i_maks):.1f}",
            "akim_15m": f"{min(T.ADS_AKIM_KIRPMA / 0.015, T.SONT_AKIM_ISIL[0.015]):.1f} A",
            "adim_uA": f"{T.ADS_AKIM_KIRPMA / T.ADS_SAYIM / rs * 1e3:.2f}",
            "adim_15m_uA": f"{T.ADS_AKIM_KIRPMA / T.ADS_SAYIM / 0.015 * 1e3:.2f}",
            "i_maks": i_maks, "fs_normal": normal["fs_sim"], "fs_hv": hv["fs_sim"]}


def kalib_esikleri() -> dict:
    """Firmware kazanc kalibrasyonunu tam skalanin %5'inin altinda reddeder."""
    mz = menziller()
    return {"i": KALIB_ESIK_ORANI * T.ADS_AKIM_KIRPMA / T.SONT_TAKILI,
            "i_15m": KALIB_ESIK_ORANI * T.ADS_AKIM_KIRPMA / 0.015,
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
        if not yuvarlak_mi(oge):                        # civata delikleri var olan cubuga denk getirilir
            continue
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


def kizak_parcalari(p: dict, anten_cikinti: float | None = None) -> list[dict]:
    """B65: ESP32 kizagi — altligin USTUNDE dik raylar + anten ucunda iki omuz takozu.
    Ray = enine kesilmis serit (g uzun, ray_yuk yuksek, t kalin) uzun kenari ustunde dik,
    kart kenarina ray_pay ile. Raylar kanal hizasinda BOSLUKLU (bag oradan). Takozlar tek
    seridin iki yarisi; anten cikintisinin iki yaninda, kartin OMUZ yuzune (anten ucunun
    anten_cikinti kadar gerisi). anten_cikinti verilmezse veri; denetim araligi da kosuyor."""
    ts = p["tasiyici"]
    kz = ts["kizak"]
    g, t = olcu()["g"], olcu()["t"]
    par = (ts["uzunluk"] - (ts["bolum"] - 1) * ts["kanal"]) / ts["bolum"]
    kanal_bas, kanal_son = p["y"] + par, p["y"] + par + ts["kanal"]
    ci = kz["anten_cikinti"] if anten_cikinti is None else anten_cikinti
    omuz_y = p["y"] + p["boy"] - ci                     # kart govdesinin anten tarafindaki ucu
    orta = p["x"] + p["en"] / 2
    ic_sol = orta - kz["anten_en"] / 2 - kz["anten_pay"]  # sol takozun anten tarafindaki ucu
    ic_sag = orta + kz["anten_en"] / 2 + kz["anten_pay"]
    ray_x = (p["x"] - kz["ray_pay"] - t, p["x"] + p["en"] + kz["ray_pay"])
    out = []
    for yan, rx in zip(("sol", "sağ"), ray_x):
        for ad, y0 in (("arka", kanal_bas - g), ("ön", kanal_son)):
            out.append({"ref": f"{p['ref']}-ray-{yan}-{ad}", "sahip": p["ref"], "x": rx, "y": y0, "z": t,
                        "en": t, "boy": g, "yuk": kz["ray_yuk"], "adim": ts["adim"], "grup": "kizak",
                        "kesim_ad": f"{p['ref']} kızak rayı"})
    for yan, x0 in (("sol", ic_sol - kz["takoz_boy"]), ("sağ", ic_sag)):
        out.append({"ref": f"{p['ref']}-takoz-{yan}", "sahip": p["ref"], "x": x0, "y": omuz_y, "z": t,
                    "en": kz["takoz_boy"], "boy": t, "yuk": kz["ray_yuk"], "adim": ts["adim"], "grup": "kizak",
                    "kesim_ad": f"{p['ref']} omuz takozu"})
    return out


def esp_dolu_pinler(nl) -> list[str]:
    """B65: devkit'te dupont takili pinler — yerlesim 1.12'nin J5 tablosuyla AYNI kaynak
    (netlist J5 aglari + firmware pin sabitleri) + CAL (PIN_CAL). Kablo bagi bunlarin
    hizasindan gecmez."""
    pinler = B.firmware_pinleri()
    out = []
    for no in range(1, 11):
        ag = nl.pin_agi.get(f"J5.{no}", "?")
        if ag in B.J5_GUC:
            out.append(B.J5_GUC[ag].split(" ")[0])
        elif ag in B.J5_AG_PIN and B.J5_AG_PIN[ag] in pinler:
            out.append(f"GPIO{pinler[B.J5_AG_PIN[ag]]}")
    if "PIN_CAL" in pinler:
        out.append(f"GPIO{pinler['PIN_CAL']}")
    guc = [p for p in ("3V3", "5V", "GND") if p in out]
    gpio = sorted({p for p in out if p.startswith("GPIO")}, key=lambda s: int(s[4:]))
    return guc + gpio


def esp_kayma_payi(nl, parcalar) -> tuple[float, float]:
    """B65: ESP32 takimi (devkit + altlik + kizak) onden bakinca SOLA (-x) ve SAGA (+x) ne
    kadar kayabilir: govde envanteriyle cakisana kadar 0.25 mm adimla. COM soketi ovale
    denk gelmezse kullanicinin kaydirma payi — metne elle yazilmaz."""
    govde = kutu_govdeleri(nl, parcalar)
    takim = [g for g in govde if _kok_ref(g["ref"]) == "ESP32" or g.get("sahip") == "ESP32"]
    diger = [g for g in govde if g not in takim]

    def cakisir(s: float) -> bool:
        return any(a["x"] + s < b["x"] + b["en"] and b["x"] < a["x"] + s + a["en"]
                   and a["y"] < b["y"] + b["boy"] and b["y"] < a["y"] + a["boy"]
                   and a["z"] < b["z"] + b["yuk"] and b["z"] < a["z"] + a["yuk"]
                   for a in takim for b in diger)

    def pay(yon: int) -> float:
        s = 0.0
        while s < 30.0 and not cakisir(yon * (s + 0.25)):
            s += 0.25
        return s
    return pay(-1), pay(+1)


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
            # B55l: iki altlik BITISIKTI ve kablo bagi altindan gecemiyordu
            # (cubuk 2 mm, yanindan delik acilamaz). Aralarina bosluk kondu:
            # bag o bosluktan gecip devkit'in ustunden donuyor. Ek malzeme yok.
            # Raylar BOYLAMASINA bolunuyor: ortadaki kanaldan kablo bagi geciyor.
            # Yanlamasina ayirmak denendi ve kart A'nin ayagina giriyordu (yer yok).
            n, bol = ts["adet"], ts.get("bolum", 1)
            kanal = ts.get("kanal", 0.0)
            x0 = p["x"] + p["en"] / 2 - n * g / 2
            par = (ts["uzunluk"] - (bol - 1) * kanal) / bol
            for i in range(n):
                for j in range(bol):
                    ek = "" if bol == 1 else chr(ord("a") + j)
                    out.append({"ref": f"{p['ref']}-altlık{i + 1}{ek}", "sahip": p["ref"],
                                "x": x0 + i * g, "y": p["y"] + j * (par + kanal), "z": 0.0,
                                "en": g, "boy": par, "yuk": t, "adim": ts["adim"], "grup": "altlik"})
            if ts.get("kizak"):                       # B65: altliklardan SONRA (z0 = ilk tasiyicinin yuk'u)
                out += kizak_parcalari(p)
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
    k1: list[dict] = []
    k2: list[dict] = []

    def ekle(lst, ad, u, adet, adim, kaynak="duz"):
        """Kesim listesi kaydi: ad, uzunluk, adet, kaynak ve KULLANILDIGI alt adim —
        her alt adim kendi 'bu adimda gereken parcalar' tablosunu buradan cikarir."""
        lst.append({"ad": ad, "u": round(u, 1), "adet": int(adet), "kaynak": kaynak, "adim": adim})
    n_sira = o["taban_sira"]
    ekle(k1, "Taban sırası — kısa parça", L * TABAN_EK[0], n_sira, "2.1")
    ekle(k1, "Taban sırası — uzun parça", L * TABAN_EK[1], n_sira, "2.1")
    ekle(k1, "Taban rayı — kısa parça", D * TABAN_EK[0], 2, "2.2")
    ekle(k1, "Taban rayı — uzun parça", D * TABAN_EK[1], 2, "2.2")
    for panel in ("ön", "arka"):
        for r, ek in enumerate(ek_yerleri(panel)):
            # arka duvar parcalari ARKADAN bakan kisinin solundan adlanir —
            # delik tablosu ve ek yeri tablosuyla ayni cerceve
            sol, sag = (L - ek, ek) if panel == "arka" else (ek, L - ek)
            ek_ad = " (arkadan)" if panel == "arka" else ""
            adim = "4.1" if r == 0 else "4.3"
            ekle(k1, f"Dış kat {panel} sıra {r + 1} — sol{ek_ad}", sol, 1, adim)
            ekle(k1, f"Dış kat {panel} sıra {r + 1} — sağ{ek_ad}", sag, 1, adim)
    ekle(k1, "Dış kat yan sıra 1 — kısa parça", o["yan_dis"] * TABAN_EK[0], 2, "4.2")
    ekle(k1, "Dış kat yan sıra 1 — uzun parça", o["yan_dis"] * TABAN_EK[1], 2, "4.2")
    # B57: etiket "2–4" ELLE yaziliydi ve B54'te duvar 5 siraya cikinca eskimisti
    # (adet 2 x (sira-1) = 8 dogruydu, ad yanlisti). Artik siradan uretiliyor.
    ekle(k1, f"Dış kat yan sıra 2–{k['duvar_sira']} — kısa parça", o["yan_dis"] * TABAN_EK[0], 2 * (k["duvar_sira"] - 1), "4.3")
    ekle(k1, f"Dış kat yan sıra 2–{k['duvar_sira']} — uzun parça", o["yan_dis"] * TABAN_EK[1], 2 * (k["duvar_sira"] - 1), "4.3")
    ic_on, ic_arka, ic_yan = ic_kat_cubuklari("ön"), ic_kat_cubuklari("arka"), ic_kat_yan()
    tam = [s for s in ic_on + ic_arka if s[2] == 0]
    kisa = [s for s in ic_on + ic_arka if s[2] > 0]
    dikey_kaynak = "yarim" if o["ic_yuk"] <= o["yarim"] else "tek_uc"     # 90 mm > yarim 75: tam cubuktan
    ekle(k2, "İç kat dikey çubuk (yuvarlak uç aşağı)", o["ic_yuk"], len(tam) + 2 * len(ic_yan), "4.5", dikey_kaynak)
    for s in kisa:
        ekle(k2, f"İç kat kısa çubuk — x {s[0]:.0f}, yuvanın üstü (z {s[2]:.0f}'dan)", o["ic_yuk"] - s[2], 1, "4.5",
             "yarim" if o["ic_yuk"] - s[2] <= o["yarim"] else "tek_uc")
    ekle(k2, "Köşe direği parçası (yuvarlak uç aşağı)", o["ic_yuk"], 4 * k["direk_kat"], "4.6", dikey_kaynak)
    ekle(k2, "Kapak sırası — kısa parça", L * TABAN_EK[0], n_sira, "13.1")
    ekle(k2, "Kapak sırası — uzun parça", L * TABAN_EK[1], n_sira, "13.1")
    ekle(k2, "Kapak rayı (yan duvara yaslı, tek parça)", o["kapak_ray"], 2, "13.1")
    for p in K.IC_PARCA:
        ts = p.get("tasiyici")
        if not ts:
            continue
        if ts["tip"] == "ayak":
            ekle(k2, f"Ayak bloğu parçası — {p['ref']} ({ts['adet']} blok × {ts['kat']} kat)", g, ts["adet"] * ts["kat"], ts["adim"])
        elif ts["tip"] == "altlik":
            ekle(k2, f"Altlık — {p['ref']}", ts["uzunluk"], ts["adet"], ts["adim"])
            kz = ts.get("kizak")
            if kz:          # B65: seritler ENINE kesilir (u = serit genisligi), uzun kenari ustunde dik
                n_ray = sum(1 for a in kizak_parcalari(p) if "-ray-" in a["ref"])
                ekle(k2, f"{p['ref']} kızak rayı — {_mm(kz['ray_yuk'])} mm şerit, uzun kenarı üstünde dik",
                     kz["ray_yuk"], n_ray, ts["adim"])
                ekle(k2, f"{p['ref']} omuz takozu — {_mm(kz['ray_yuk'])} mm şerit, ikiye böl "
                         f"({_mm(kz['takoz_boy'])} + {_mm(kz['takoz_boy'])})", kz["ray_yuk"], 1, ts["adim"])
        elif ts["tip"] == "kosebent":
            ekle(k2, f"Köşebent parçası — {p['ref']} ({ts['adet']} kat)", ts["uzunluk"], ts["adet"], ts["adim"])
    for p in kutu_ek_parcalari():
        ekle(k2, f"{p['ref']} ({p['kat']} kat)", max(p["en"], p["boy"]), p["kat"], p["adim"])
    for d in K.DUVAR_PARCA:                    # duvara asili modullerin ahsap tutuculari (B55c)
        tt = K.DUVAR_TUTUCU[d["ref"]]
        if tt:
            for ad, u, n in tutucu_parcalari(tt):
                ek = f"{d['ref']} {tt['ad']}" + (f" — {ad}" if ad != tt["ad"] else "")
                ekle(k2, f"{ek} ({n} parça)", u, n, monte_adim().get(d["ref"], "10.2"))
    ekle(k2, f"Kapak somun bloğu parçası (4 blok × {k['kapak_somun_kat']} kat)", g,
         4 * k["kapak_somun_kat"], "13.1")     # 13.1 metni istiyordu, listede yoktu (B55c)
    parcalar = k1 + k2
    yarim_adet = sum(x["adet"] for x in parcalar if x["kaynak"] == "yarim")
    tek_uc = [x for x in parcalar if x["kaynak"] == "tek_uc"]
    tek_uc_adet = sum(x["adet"] for x in tek_uc)
    boylar = sorted((x["u"] for x in parcalar if x["kaynak"] == "duz" for _ in range(x["adet"])), reverse=True)
    # tek_uc: her parca bir tam cubuktan (bir yuvarlak uc parcada kalir); artan kisim (obur yuvarlak
    # uc dusulunce) duz havuza girer
    cubuklar: list[float] = [K.CUBUK["uzunluk"] - K.CUBUK["uc_egim"] - x["u"] - KERF
                             for x in tek_uc for _ in range(x["adet"])]
    for u in boylar:
        for i, kalan in enumerate(cubuklar):
            if kalan >= u + KERF:
                cubuklar[i] = kalan - u - KERF
                break
        else:
            cubuklar.append(duz - u)
    cubuk = len(cubuklar) + math.ceil(yarim_adet / 2)      # cubuklar: tek_uc'ler + duz icin acilanlar
    return dict(o, dikey_kaynak=dikey_kaynak, kesim1=k1, kesim2=k2, parcalar=parcalar, ic_on=ic_on, ic_arka=ic_arka, ic_yan=ic_yan,
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
    pay = k["kapak_ray_payi"]          # B55l: gecme payi, nominal sifirdi
    return [{"ref": "KR1", "x": pay, "y": g + 1, "z": o["ic_yuk"] - g, "en": t, "boy": o["kapak_ray"], "yuk": g},
            {"ref": "KR2", "x": k["ic_en"] - t - pay, "y": g + 1, "z": o["ic_yuk"] - g, "en": t,
             "boy": o["kapak_ray"], "yuk": g}]


def duvar_parcalari() -> list[dict]:
    """Duvara asili parcalar (pil blogu) — ic koordinat 3B kutu (x, y, z, en, boy, yuk)."""
    kb = K.KUTU
    out = []
    for d in K.DUVAR_PARCA:
        if d["duvar"] == "arka":
            y0 = 0.0
        elif d["duvar"] == "ön":
            y0 = kb["ic_boy"] - d["derin"]
        else:
            raise ValueError(d["duvar"])
        out.append({"ref": d["ref"], "x": d["x"], "y": y0, "z": d["z"], "en": d["en"], "boy": d["derin"],
                    "yuk": d["yuk"], "duvar": d["duvar"], "stok": d.get("stok"), "nasil": d["nasil"]})
    return out


def duvar_yontemi(ref: str) -> str:
    """Duvar parcasinin TUTTURMA yontemi — veriden: yapistirma istisnasi, kablo bagi
    tutucusu (DUVAR_TUTUCU'da cubuk), yoksa civata (PANEL_ARKA'da kaydi olmali)."""
    if ref in K.YAPISTIRMA_ISTISNA:
        return "yapistir"
    return "kablo_bagi" if K.DUVAR_TUTUCU.get(ref) else "civata"


def kutle_anahtari(o: dict) -> str:
    """Panel ogesi -> KUTLE anahtari."""
    if o["ref"] in K.KUTLE:
        return o["ref"]
    if o["tip"] == "civata":
        return "cıvata"
    if o["tip"] == "anahtar":
        return "anahtar"
    return "jak_büyük" if o["delik_mm"] >= 8 else "jak_küçük"


def kutle_kalemleri(hucre: int = 2) -> list[dict]:
    """Kutunun butun kutleleri: (ad, grup, m gram, x, y, z, bel).

    Koordinat DIS cerceve: x=0 sol dis yuz, y=0 ARKA dis yuz, z=0 kutunun
    UZERINDE DURDUGU yuzey (taban raylarinin alti). Ic koordinattan
    (kutu_veri) donusum burada, tek yerde.

    `hucre`: kac 18650 takili — 2 (normal), 1 (paralel paket tek hucreyle de
    calisir), 0 (hucreler cikarilmis: tasima / saklama). B58'den beri modullerin
    hepsi her zaman takili; degisen yalniz hucrelerin kutlesi.
    """
    o, h = olcu(), hesap()
    t, g, dt = o["t"], o["g"], o["duvar_t"]
    EN, BOY, YUK = h["dis_en"], h["dis_boy"], o["ic_yuk"]
    ks: list[dict] = []

    def ah(ad, grup, m, x, y, z, bel):
        ks.append({"ad": ad, "grup": grup, "m": m, "x": x, "y": y, "z": z, "bel": bel})

    def tahta(ad, x0, y0, z0, dx, dy, dz, grup="kutu"):
        ah(ad, grup, dx * dy * dz * K.CUBUK_YOGUNLUK, x0 + dx / 2, y0 + dy / 2, z0 + dz / 2, TAHTA_BEL)

    def tahta_hacim(ad, hacim, x, y, z, grup="kutu"):
        """Kucuk ahsap blok: geometrisi degil, hacmi ve yeri onemli (kesim listesiyle ayni hacim)."""
        ah(ad, grup, hacim * K.CUBUK_YOGUNLUK, x, y, z, TAHTA_BEL)

    def kut(anahtar, ad, grup, x, y, z):
        # eksik anahtar: kapsam denetimi (bolum 8) zaten kirmizi — burada cokmeden devam
        m, bel, _kaynak = K.KUTLE.get(anahtar, (0.0, 0.5, ""))
        ah(ad, grup, m, x, y, z, bel)

    IX, IY, IZ = (lambda v: v + dt), (lambda v: v + dt), (lambda v: v + 2 * t)
    for i, rx in enumerate(TABAN_RAY_X):                     # kutu bu iki rayin uzerinde durur
        tahta(f"Taban rayı {i + 1}", EN * rx - g / 2, 0, 0, g, BOY, t)
    tahta("Taban", 0, 0, t, EN, BOY, t)
    for r in range(K.KUTU["duvar_sira"]):                    # dis kat: dort duvar, yatay siralar
        z = IZ(r * g)
        tahta(f"Dış ön {r + 1}", 0, BOY - t, z, EN, t, g)
        tahta(f"Dış arka {r + 1}", 0, 0, z, EN, t, g)
        tahta(f"Dış sol {r + 1}", 0, t, z, t, BOY - 2 * t, g)
        tahta(f"Dış sağ {r + 1}", EN - t, t, z, t, BOY - 2 * t, g)
    for x0, w, z0 in h["ic_on"]:                             # ic kat: panel deliklerinden turemis
        tahta("İç kat ön", IX(x0), BOY - dt, IZ(z0), w, t, YUK - z0)
    for x0, w, z0 in h["ic_arka"]:
        tahta("İç kat arka", IX(x0), dt - t, IZ(z0), w, t, YUK - z0)
    for y0, w in h["ic_yan"]:
        tahta("İç kat sol", dt - t, IY(y0), IZ(0), t, w, YUK)
        tahta("İç kat sağ", IX(K.KUTU["ic_en"]), IY(y0), IZ(0), t, w, YUK)
    for d in direkler():
        tahta(f"Köşe direği {d['ref']}", IX(d["x"]), IY(d["y"]), IZ(0), d["en"], d["boy"], d["yuk"])
    tahta("Kapak", 0, 0, IZ(YUK), EN, BOY, t, grup="kapak")
    for r in kapak_raylari():
        tahta("Kapak rayı", IX(r["x"]), IY(r["y"]), IZ(r["z"]), r["en"], r["boy"], r["yuk"], grup="kapak")
        for yc in K.KUTU["kapak_civata_y"]:               # rayin ic yuzundeki gomme somunlu bloklar
            tahta_hacim("Kapak somun bloğu", g * g * t * K.KUTU["kapak_somun_kat"],
                        IX(r["x"]), IY(yc), IZ(K.KUTU["kapak_civata_z"]), grup="kapak")
    for a in ayaklar():                                      # ayak / altlik / kosebent / ek bloklar
        tahta(a["ref"], IX(a["x"]), IY(a["y"]), IZ(a["z"]), a["en"], a["boy"], a["yuk"])
    for p in K.IC_PARCA:                                     # kartlar: AM kart yuzeyinin biraz ustunde
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == p["ref"]), 0.0)
        kut(p["ref"], p["ref"], "parça", IX(p["x"] + p["en"] / 2), IY(p["y"] + p["boy"] / 2),
            IZ(z0 + p["yuk"] * KART_AM_ORANI))
    for d in duvar_parcalari():                              # pil blogu: arka duvara asili
        mx, my, mz = IX(d["x"] + d["en"] / 2), IY(d["y"] + d["boy"] / 2), IZ(d["z"] + d["yuk"] / 2)
        kut(d["ref"], d["ref"], "pil", mx, my, mz)
        tt = K.DUVAR_TUTUCU[d["ref"]]
        if tt:
            tahta_hacim(f"{d['ref']} {tt['ad']}", sum(u * g * t * n for _a, u, n in tutucu_parcalari(tt)),
                        mx, my, mz)
        if d["ref"].startswith("YUVA") and int(d["ref"][4:]) <= hucre:
            kut("HÜCRE", f"18650 ({d['ref']})", "pil", mx, my, mz)
    for x in panel_ogeleri():                                # panel: kutle duvarin icinde
        if x["tip"] in PARCASIZ_TIP:                         # kendi parcasi yok (oval yuva, havalandirma)
            continue
        y = BOY - dt / 2 if x["panel"] == "ön" else dt / 2
        kut(kutle_anahtari(x), x["etiket"], "panel", IX(x["x"]), y, IZ(x["z"]))
    kut("KABLO", "kablo demeti", "kablo", EN / 2, BOY / 2, IZ(KABLO_AM_Z))
    return ks


def _am(ks, oran=None) -> tuple[float, tuple[float, float, float]]:
    M = sum(k["m"] * (oran(k) if oran else 1.0) for k in ks)
    return M, tuple(sum(k["m"] * (oran(k) if oran else 1.0) * k[e] for k in ks) / M for e in "xyz")


def _am_uc(ks, eksen: str, yon: int) -> float:
    """Belirsizlik kutusunun icinde AM'yi `yon` tarafina en cok iten kutle secimi.

    AM = sum(m x)/sum(m) bir kesirli programdir: en buyugu, esigin bir
    yanindaki her kalem ust sinirda, obur yanindaki her kalem alt sinirda
    iken alinir. Esik AM'nin kendisi — sabit nokta yinelemesi.
    """
    c = _am(ks)[1]["xyz".index(eksen)]
    for _ in range(50):
        yeni = _am(ks, lambda k: 1 + k["bel"] if (k[eksen] - c) * yon > 0 else 1 - k["bel"])[1]["xyz".index(eksen)]
        if abs(yeni - c) < 1e-9:
            break
        c = yeni
    return c


def _ray_pay(cx: float, ray_merkez: tuple[float, float]) -> tuple[float, float]:
    """Iki dogrusal destegin (taban raylari) yuk payi: (sol, sag), toplam 1."""
    r1, r2 = ray_merkez
    sol = min(1.0, max(0.0, (r2 - cx) / (r2 - r1)))
    return sol, 1.0 - sol


def agirlik_merkezi(hucre: int = 2) -> dict:
    """Agirlik merkezi, ray yuk paylari, devrilme aci paylari.

    Her sayinin bir de KOTU HAL karsiligi var: kutlelerin belirsizlik
    araliginda AM'yi en kotu yere iten secim. Denetim ikisine de bakar —
    sonuc yalnizca nominal tahminlerle saglikliysa iddia kirmizi olur.
    """
    o, h = olcu(), hesap()
    EN, BOY = h["dis_en"], h["dis_boy"]
    dis_yuk = 2 * o["t"] + o["ic_yuk"] + o["t"]
    ks = kutle_kalemleri(hucre)
    M, (cx, cy, cz) = _am(ks)
    ray_m = tuple(EN * r for r in TABAN_RAY_X)              # ray merkezleri: yuk payi buradan
    ray_dis = (EN * TABAN_RAY_X[0] - o["g"] / 2, EN * TABAN_RAY_X[1] + o["g"] / 2)  # devrilme: dis kenarlar
    kotu = {e: (_am_uc(ks, e, -1), _am_uc(ks, e, +1)) for e in "xyz"}
    z_kotu = kotu["z"][1]                                   # AM ne kadar yukseğe cikabilir
    yon = {"sol": cx - ray_dis[0], "sağ": ray_dis[1] - cx, "arka": cy, "ön": BOY - cy}
    yon_kotu = {"sol": kotu["x"][0] - ray_dis[0], "sağ": ray_dis[1] - kotu["x"][1],
                "arka": kotu["y"][0], "ön": BOY - kotu["y"][1]}
    gruplar: dict[str, float] = {}
    for k in ks:
        gruplar[k["grup"]] = gruplar.get(k["grup"], 0.0) + k["m"]
    return {"hucre": hucre, "M": M, "x": cx, "y": cy, "z": cz, "kalem": ks, "grup": gruplar,
            "dis": (EN, BOY, dis_yuk), "destek_x": ray_dis, "ray_merkez": ray_m,
            "sapma": {"x": cx - EN / 2, "y": cy - BOY / 2},
            "yari": {"x": EN / 2, "y": BOY / 2},
            "kotu": {e: (kotu[e][0] - m, kotu[e][1] - m) for e, m in (("x", EN / 2), ("y", BOY / 2))},
            "ray_pay": _ray_pay(cx, ray_m),
            "kotu_ray_pay": (min(_ray_pay(kotu["x"][1], ray_m)[0], _ray_pay(kotu["x"][0], ray_m)[0]),
                             min(_ray_pay(kotu["x"][1], ray_m)[1], _ray_pay(kotu["x"][0], ray_m)[1])),
            "aci": {a: math.degrees(math.atan2(d, cz)) for a, d in yon.items()},
            "kotu_aci": {a: math.degrees(math.atan2(max(d, 0.0), z_kotu)) for a, d in yon_kotu.items()},
            "pay": yon, "kotu_pay": yon_kotu, "z_kotu": z_kotu, "z_orani": cz / dis_yuk}


def pil_grafi(acik: tuple[str, ...] = (), asama: str | None = None) -> dict[str, set[str]]:
    """PIL_KABLOLAR + modul ic baglantilari + KAPALI anahtarlar -> dugum bilesenleri
    (union-find). `acik`: acik tutulan anahtarlar (PIL_ANAHTAR anahtarlari);
    varsayilan hepsi kapali — en kotu hal, her yol bagli. `asama`: yalniz o
    asamaya kadar kurulan kablolar ("paket" < "analog"). B58: kaynak secici yok."""
    ebeveyn: dict[str, str] = {}

    def bul(a):
        ebeveyn.setdefault(a, a)
        while ebeveyn[a] != a:
            ebeveyn[a] = ebeveyn[ebeveyn[a]]
            a = ebeveyn[a]
        return a

    def birles(a, b):
        ra, rb = bul(a), bul(b)
        if ra != rb:
            ebeveyn[ra] = rb
    for kablo in K.PIL_KABLOLAR:
        if asama is None or ASAMA_SIRA[pil_asama(kablo)] <= ASAMA_SIRA[asama]:
            birles(kablo[0], kablo[1])
    for a, b in K.PIL_IC_BAG:
        birles(a, b)
    for ad, (a, b) in K.PIL_ANAHTAR.items():
        if ad not in acik:
            birles(a, b)
    out: dict[str, set[str]] = {}
    for d in list(ebeveyn):
        out.setdefault(bul(d), set()).add(d)
    return {d: out[bul(d)] for d in ebeveyn}


def kart_hacimleri(q: dict, z0: float, nl, parcalar) -> list[dict]:
    """Ic parcanin 3B hacimleri. Plaket icin iki kutu: yerlesimin KULLANDIGI bolge
    tam yukseklikte, kullanilmayan kenar seridi yalniz plaket kalinliginda —
    sutun indeksi 'sutun_yonu' yonunde artar (A: telli kenar one bakar)."""
    tam = dict(q, z=z0)
    if q.get("sutun_yonu") != "arka" or q["ref"] not in V.KARTLAR:
        return [tam]
    en_buyuk = max(d[0] for p in parcalar.values() if p.kart == q["ref"]
                   for dl in p.delikler(nl).values() for d in dl)
    adim = V.KARTLAR[q["ref"]].get("adim_mm", 2.54)
    bos = (V.KARTLAR[q["ref"]]["sutun"] - (en_buyuk + 1)) * adim      # arka kenardaki bos serit
    return [dict(q, ref=f"{q['ref']} (dolu)", y=q["y"] + bos, boy=q["boy"] - bos, z=z0),
            dict(q, ref=f"{q['ref']} (boş kenar)", boy=bos, yuk=q.get("bos_yuk", 2.0), z=z0)]


ANALOG_UC = ("F0.", "IZ.", "CB.", "MT2.", "KL.", "A.")
ASAMA_SIRA = {"paket": 1, "analog": 2}


def pil_asama(kablo) -> str:
    """B58: "paket" = pil paketi + 5 V barasi (10.3); "analog" = 5 V -> F0 ->
    B0505S -> MT2 -> klemens -> kart (10.4)."""
    return "analog" if any(u.startswith(ANALOG_UC) for u in kablo[:2]) else "paket"


# ── B73 · kablo guzergahi ─────────────────────────────────────────────────
KABLO_RENK = {"arti": "#d62828", "gnd": "#1f1f1f", "eksi12": "#2563eb", "sinyal": "#f77f00",
              "hucre": "#9d0208", "bacak": "#8a8a85"}
KABLO_E12 = frozenset({"IZ.OUT-", "MT2.IN-", "MT2.OUT-", "KL.-", "CB.-", "A.C36"})
KABLO_GND = frozenset({"H1-", "H2-", "TP1.B-", "TP1.OUT-", "MT1.IN-", "MT1.OUT-", "IZ.IN-",
                       "ESP32.GND", "LED1.K", "J1.2.L"})
KABLO_HUCRE = frozenset({"H1+", "H2+", "F1P.1", "F1P.2", "F2.1", "F2.2", "TP1.B+"})
KABLO_SINYAL = frozenset({"ESP32.J5", "A.J5", "ESP32.GPIO10", "CAL.L"})


def kablo_rol(a: str, b: str) -> str:
    """Cizim rengi ve kesit icin rol. Sira onemli: bacak > sinyal > -12 > GND > hucre > arti."""
    u = {a, b}
    if any(x.startswith("CB.") for x in u):
        return "bacak"
    if u & KABLO_SINYAL:
        return "sinyal"
    if u & KABLO_E12:
        return "eksi12"
    if u & KABLO_GND:
        return "gnd"
    if u & KABLO_HUCRE:
        return "hucre"
    return "arti"


def uc_adi(uc: str) -> str:
    return K.UC_AD.get(uc, uc.replace(".", " "))


def uc_noktasi(uc: str) -> tuple[tuple[float, float, float], set[str]]:
    """Kablo ucu -> (kutu ic koordinati, ucun sahibi govde ref'leri). Ad bicimi 'REF.UC'
    (REF noktali olabilir: 'J1.2.L'); hucre uclari H1± / H2± yuvanin telleridir."""
    uc = K.KABLO_UC_TAKMA.get(uc, uc)
    ref, u = uc.rsplit(".", 1)
    if ref == "A":
        A = next(p for p in K.IC_PARCA if p["ref"] == "A")
        if u in V.YER:                                     # adli yer (J5 basligi)
            c, r = V.YER[u][2], V.YER[u][3]
        else:                                              # delik adi: harf(ler) + sayi (C34)
            harf = "".join(ch for ch in u if ch.isalpha())
            c = next(i for i in range(80) if Y.sutun_adi(i) == harf)
            r = int("".join(ch for ch in u if ch.isdigit())) - 1
        x, y, z = kart_nokta(A, c, r)
        return (x, y, z + 2.0), {"A (dolu)", "A (boş kenar)"}
    duvar = {d["ref"]: d for d in duvar_parcalari()}
    if ref in duvar:
        d = duvar[ref]
        dx, dy, dz = K.KABLO_UCLARI[ref][u]
        sahip = {"CB", "MT2"} if ref in ("CB", "MT2") else {ref}
        return (d["x"] + dx, d["y"] + dy, d["z"] + dz), sahip
    if ref == "ESP32":
        e = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == "ESP32"), 0.0)
        dx, dy, dz = K.KABLO_UCLARI["ESP32"][u]
        return (e["x"] + dx, e["y"] + dy, z0 + dz), {"ESP32"}
    panel = {o["ref"]: o for o in panel_ogeleri()}
    if ref in panel:
        o = panel[ref]
        dx, dz = K.PANEL_UCLARI[ref][u]
        return (o["x"] + dx, K.KUTU["ic_boy"] - o["derin_mm"], o["z"] + dz), {ref}
    raise KeyError(uc)


def kablo_listesi() -> list[dict]:
    """B73: cizilen kablolar — PIL_KABLOLAR (10.3 paket / 10.4 analog) + KABLO_EK, K1.. sirayla."""
    out = [{"a": a, "b": b, "adim": "10.3" if pil_asama((a, b)) == "paket" else "10.4", "not": n}
           for a, b, _t, n in K.PIL_KABLOLAR]
    out += [{"a": e["a"], "b": e["b"], "adim": e["adim"], "not": e["not"]} for e in K.KABLO_EK]
    for i, k in enumerate(out, 1):
        rol = kablo_rol(k["a"], k["b"])
        k.update(no=i, rol=rol, soz=K.KABLO_YOL.get((k["a"], k["b"]), {}).get("soz", "kısa yoldan, parçaların önünden"),
                 kesit=K.KABLO_KESIT.get(rol, "0.5 mm²"))
    return out


def adim_kablolari(no: str) -> list[dict]:
    return [k for k in kablo_listesi() if k["adim"] == no]


def _guzergah_serit(k: dict, sr: tuple[float, float, float]) -> list[tuple[float, float, float]]:
    """Eksen eksen kirik cizgi; sr = (sx, sy, sz) serit kaydirmasi. Ara nokta yoksa: one cik
    (arka bolgede en derin ucun 3 + sy mm onu, onde varis ucunun sy mm arkasi), sx kadar yana,
    dik (varis yuksekliginin sz ustune), yatay, sz kadar in, gir. Ara noktalar sr kadar kayar ve
    her adimda y, z, x sirasiyla gidilir. 1 mm'den kisa kayma ayri nokta olmaz (onceki noktaya
    emilir) — kart deliginin 2.54 izgarasi ile yuvarlak ara nokta arasindaki 0.1 mm cizimi bozmasin."""
    a, b = uc_noktasi(k["a"])[0], uc_noktasi(k["b"])[0]
    sx, sy, sz = sr
    ara = [(float(p[0]) + sx, float(p[1]) + sy, float(p[2]) + sz)
           for p in K.KABLO_YOL.get((k["a"], k["b"]), {}).get("ara", [])]
    yol = [a]

    def ekle(r):
        r = tuple(r)
        d = max(abs(r[i] - yol[-1][i]) for i in range(3))
        if d < 1e-6:
            return
        if d < 1.0 and len(yol) > 1:
            yol[-1] = r
            return
        yol.append(r)
    if ara:
        for q in ara + [b]:
            cur = list(yol[-1])
            for e in (1, 2, 0):
                cur[e] = q[e]
                ekle(cur)
    else:
        yl = max(a[1], b[1]) + 3.0 + sy if a[1] < 45 and b[1] < 45 else b[1] - sy
        for r in ((a[0], yl, a[2]), (a[0] + sx, yl, a[2]), (a[0] + sx, yl, b[2] + sz),
                  (b[0], yl, b[2] + sz), (b[0], yl, b[2]), b):
            ekle(r)
    return yol


@lru_cache(maxsize=1)
def _kablo_govdeleri() -> tuple:
    return tuple(kutu_govdeleri(Y.Netlist(Y.NETLIST), Y.parcalari_yukle()))


def _serit_cakisir(y1, y2, ciplak: bool, izdusum: bool = True) -> bool:
    """Seritleme icin: iki guzergah ayni eksende 2 mm'den uzun ve 2 mm'den yakin (3B'de ya da,
    izdusum=True ise, ic bakisin x-z izdusumunde) gidiyor mu; ciplak bacakta yaklasma < 2.5 mm."""
    for p, q in zip(y1, y1[1:]):
        for r, t in zip(y2, y2[1:]):
            if ciplak:
                bos = [max(0.0, max(min(p[j], q[j]) - max(r[j], t[j]), min(r[j], t[j]) - max(p[j], q[j])))
                       for j in range(3)]
                if math.hypot(*bos) < 2.5:
                    return True
            # baskin eksen: kart deliginin 2.54 izgarasi 0.05 mm'lik kayma birakiyor (tam eksenel degil)
            e = max(range(3), key=lambda j: abs(p[j] - q[j]))
            if e != max(range(3), key=lambda j: abs(r[j] - t[j])):
                continue
            if min(max(p[e], q[e]), max(r[e], t[e])) - max(min(p[e], q[e]), min(r[e], t[e])) <= 2.0:
                continue
            if all(abs(p[j] - r[j]) < 2.0 for j in range(3) if j != e)                     or (izdusum and e != 1 and abs(p[2 - e] - r[2 - e]) < 2.0):
                return True
    return False


@lru_cache(maxsize=1)
def _seritler() -> dict:
    """B73 gozden gecirme: ucu ORTAK OLMAYAN kablolar ayni cizgiye binmesin (680 µF'in iki ciplak
    bacagi, 5 V ile GND, +24 ile −12 ust usteydi). Kablolar sirayla (K1, K2, ...) yerlesir; her
    biri icin aday seritler kucukten buyuge denenir ve govdeye girmeyen, kutudan tasmayan, kart
    B'nin HV girisine yaklasmayan, onceki kablolarla cakismayan ILK aday secilir. Ic bakis (x-z
    izdusumu) yalniz AYNI adimin kablolarini karsilastirir: onceki adimlarinkiler soluk cizilir. Bulunamazsa
    seritsiz kalir — denetim (bolum 10) cakismayi kendi koduyla ayrica arar ve kirmizi verir."""
    n = K.KABLO_SERIT
    adim = (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6)
    adaylar = sorted({(i * n, m * n, j * n) for i in adim for j in adim for m in (0, 1, 2, 3, 4)},
                     key=lambda sr: (abs(sr[0]) + abs(sr[1]) + abs(sr[2]), sr[1], sr))
    govde = list(_kablo_govdeleri())
    hv = hv_dugumu(next(p for p in K.IC_PARCA if p["ref"] == "B"))
    ic = (K.KUTU["ic_en"], K.KUTU["ic_boy"], hesap()["ic_yuk"])
    # Sira: once ciplak bacaklar (govdeye bagli, en kisitli; digerleri onlarin etrafindan dolasir),
    # sonra uzundan kisaya — kisa olanlar (K9 gibi) bandi once kaparsa uzunlara yer kalmiyordu.
    sira = sorted(kablo_listesi(), key=lambda k: (k["rol"] != "bacak",
                                                  0.0 if k["rol"] == "bacak" else -guzergah_boyu(_guzergah_serit(k, (0.0, 0.0, 0.0))),
                                                  k["no"]))
    out, yerlesik = {}, []
    for k in sira:
        uclar, ciplak = {k["a"], k["b"]}, k["rol"] == "bacak"
        secilen = (0.0, 0.0, 0.0)
        for sr in adaylar:
            yol = _guzergah_serit(k, sr)
            if (kablo_carpismalari(k, govde, yol)
                    or not all(0.0 <= p[i] <= ic[i] for p in yol for i in range(3))
                    or min(_seg_nokta(p, q, hv) for p, q in zip(yol, yol[1:])) < T.IEC60664_CREEPAGE_TAKVIYELI
                    or any(_serit_cakisir(yol, y2, ciplak or c2, a2 == k["adim"])
                           for u2, y2, c2, a2 in yerlesik if not uclar & u2)):
                continue
            secilen = sr
            break
        out[(k["a"], k["b"])] = secilen
        yerlesik.append((uclar, _guzergah_serit(k, secilen), ciplak, k["adim"]))
    return out


def guzergah(k: dict) -> list[tuple[float, float, float]]:
    """Kablonun cizilen / olculen guzergahi: _guzergah_serit + secilen serit (_seritler)."""
    return _guzergah_serit(k, _seritler().get((k["a"], k["b"]), (0.0, 0.0, 0.0)))


def guzergah_boyu(yol) -> float:
    return sum(math.dist(p, q) for p, q in zip(yol, yol[1:]))


def kesim_cm(yol) -> int:
    """Yeni kablonun kesim boyu: guzergah x pay + iki uctaki soyma, yukari cm."""
    return math.ceil((guzergah_boyu(yol) * K.KABLO_PAY + 2 * K.KABLO_SOYMA) / 10.0)


def _tel_sahibi(u: str) -> str | None:
    r = K.KABLO_UC_TAKMA.get(u, u).rsplit(".", 1)[0]
    return r if r in K.KENDI_TEL else None


def kesim_yazi(k: dict) -> str:
    """B73 gozden gecirme: tablo ve kartin 'Kesim' degeri. Bazi uclar parcanin KENDI teli (yuva
    telleri, 6.0'da TP4056 pedlerine lehimlenen ~20 cm'lik teller): orada yeni kablo kesilmez,
    o telin gereken boyu yazilir (TP4056'da pedden: araliga cikis + kivrim dahil)."""
    if k["rol"] == "bacak":
        return "kesilmez (kendi bacağı)"
    yol = guzergah(k)
    L = guzergah_boyu(yol)
    sahip = {_tel_sahibi(u) for u in (k["a"], k["b"])} - {None}
    tp = next(dp for dp in duvar_parcalari() if dp["ref"] == "TP1")
    tp_ped = K.KABLO_UCLARI["TP1"]["B+"][2] - tp["yuk"] + K.KENDI_TEL["TP1"]["kivrim_mm"]
    yuva = next((r for r in sorted(sahip) if r.startswith("YUVA")), None)
    if yuva:
        g = math.ceil((L * K.KABLO_PAY + K.KABLO_SOYMA) / 10)
        t = f"{K.KENDI_TEL[yuva]['ad']}: {g} cm gerekir (uzunsa kes, kısaysa ek)"
        if "TP1" in sahip:
            pt = math.ceil((tp_ped * K.KABLO_PAY + K.KABLO_SOYMA) / 10)
            t += f"; TP4056'nın telini pedden {pt} cm'de kes, ikisini orada birleştir (lehim + makaron)"
        return t
    if "TP1" in sahip:
        g = math.ceil(((L + tp_ped) * K.KABLO_PAY + K.KABLO_SOYMA) / 10)
        boy = K.KENDI_TEL["TP1"]["boy_mm"] / 10
        if g > boy:
            return (f"{K.KENDI_TEL['TP1']['ad']}: pedden {g} cm gerekir — tel ~{boy:.0f} cm, "
                    f"{g - boy:.0f} cm ek (lehim + makaron)")
        return f"{K.KENDI_TEL['TP1']['ad']}: pedden {g} cm'de kes"
    return f"{kesim_cm(yol)} cm"


def _uc_notu(k: dict) -> str:
    """Kablo kartinin notu: uc tahmini + o parcada ucu nasil bulacagin."""
    refs = {K.KABLO_UC_TAKMA.get(u, u).rsplit(".", 1)[0] for u in (k["a"], k["b"])}
    ek = []
    if refs & {"MT1", "MT2"}:
        ek.append("MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−)")
    if "TP1" in refs:
        ek.append("TP4056'da ped adları kartın üstünde (B+ / B− / OUT+ / OUT−)")
    if "IZ" in refs:
        ek.append("B0505S'in gövdesinde ad YOK: bacak numarası 1, 2, 4, 6 (10.1) — yan yana iki bacak giriş")
    return "Uç yerleri ±3 mm tahmin" + ("; " + "; ".join(ek) if ek else "") + "."


def _seg_nokta(p, q, x) -> float:
    """x noktasinin [p, q] dogru parcasina en kisa uzakligi (mm)."""
    d = [q[i] - p[i] for i in range(3)]
    L2 = sum(v * v for v in d)
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, sum((x[i] - p[i]) * d[i] for i in range(3)) / L2))
    return math.dist(x, [p[i] + t * d[i] for i in range(3)])


def kablo_carpismalari(k: dict, govde: list[dict], yol=None) -> list[str]:
    """Guzergah parcalarinin (cizgi) 1 mm'den derin girdigi govdeler. Ilk parca bas ucun,
    son parca son ucun sahibini saymaz (kablo oraya lehimli); aradakiler hicbirini.
    yol verilirse o denenir (seritleme adaylari)."""
    yol = guzergah(k) if yol is None else yol
    sa, sb = uc_noktasi(k["a"])[1], uc_noktasi(k["b"])[1]
    n = len(yol) - 1
    out = set()
    for i, (p, q) in enumerate(zip(yol, yol[1:])):
        haric = (sa if i == 0 else set()) | (sb if i == n - 1 else set())
        lo = [min(p[j], q[j]) for j in range(3)]
        hi = [max(p[j], q[j]) for j in range(3)]
        for g in govde:
            if g["ref"] in haric:
                continue
            gl = (g["x"], g["y"], g.get("z", 0.0))
            gh = (g["x"] + g["en"], g["y"] + g["boy"], g.get("z", 0.0) + g["yuk"])
            if all(lo[j] < gh[j] - 1.0 and hi[j] > gl[j] + 1.0 for j in range(3)):
                out.add(g["ref"])
    return sorted(out)


def aralik3(a: dict, b: dict) -> float:
    """Iki 3B kutu arasindaki en buyuk eksen boslugu (cakisiyorsa negatif)."""
    dx = max(b["x"] - (a["x"] + a["en"]), a["x"] - (b["x"] + b["en"]))
    dy = max(b["y"] - (a["y"] + a["boy"]), a["y"] - (b["y"] + b["boy"]))
    dz = max(b["z"] - (a["z"] + a["yuk"]), a["z"] - (b["z"] + b["yuk"]))
    m = max(dx, dy, dz)
    return m if m >= 0 else -1.0


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


def _stokta(html: str) -> bool:
    """Stok().ad_ile ciktisi kayit buldu mu? 'yeri kayitta yok' (konum bos) kayit VAR demektir;
    yalnizca <span class='kotu'> isareti yok demektir."""
    return "class='kotu'" not in html


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
    for x in h["parcalar"]:
        sinir = {"duz": h["duz"], "yarim": h["yarim"], "tek_uc": c["uzunluk"] - c["uc_egim"]}[x["kaynak"]]
        D.kosul(f"'{x['ad']}' {x['kaynak'].upper()} kaynaga sigiyor", x["u"] <= sinir + 1e-6,
                f"{x['u']:.1f} <= {sinir:.0f} mm · {x['adet']} adet")
        D.kosul(f"'{x['ad'][:34]}' bir alt adimda kullaniliyor ({x['adim']})", x["adim"] in sira)
    D.kosul("Hicbir parca TAM cubuk degil (yuvarlak uc duvar altina gelmez)",
            all(x["kaynak"] in ("duz", "yarim", "tek_uc") for x in h["parcalar"]))
    # Eskiden burada hesap()'taki formulun kopyasi vardi: iddia veriyi KENDISIYLE
    # karsilastiriyordu, hicbir degisiklikte kirmizi olamazdi. B54'te duvar 4->5 sira
    # olunca (ic_yuk 72->90 > yarim 75) kesim listesi tek_uc'e gecti ama 1.2 METNI
    # "yarim cubuktan" demeye devam etti: belge 75 mm'lik yarim cubuktan 90 mm parca
    # kestiriyordu (B55d). Iddia artik METIN ile VERIyi karsilastiriyor.
    dikey = [x for x in h["parcalar"] if x["ad"].startswith(("İç kat dikey", "Köşe direği"))]
    D.kosul("Dikey parcalarin kaynagi cubuk boyuna gercekten siginiyor",
            all(x["u"] <= (h["yarim"] if x["kaynak"] == "yarim" else c["uzunluk"] - c["uc_egim"]) + 1e-6
                for x in dikey), f"{h['ic_yuk']:.0f} mm, kaynak {h['dikey_kaynak']}, yarim {h['yarim']:.0f} mm")
    m12 = _kucuk(" ".join(hepsi["1.2"]["yap"]).format(**adim_bicim(h, nl, parcalar)))
    D.kosul("1.2 metnindeki dikey parca kaynagi kesim listesiyle ayni",
            ("yarım çubuk" in m12) == (h["dikey_kaynak"] == "yarim"), m12[:90])
    # duvar adimlari butun siralari kapsiyor mu (4.3 basligi 4 sira diyordu, tasarim 5)
    duvar_sira_kapsam = max(x.get("sira", 0) for x in aa if x["tur"] == "duvar")
    D.kosul("Duvar adimlari butun dis kat siralarini kapsiyor",
            duvar_sira_kapsam == kb["duvar_sira"], f"adimlar {duvar_sira_kapsam}, tasarim {kb['duvar_sira']}")
    D.kosul("Ilk kesimdeki (1.2) parcalar ikinci kesimden (4.4) once kullaniliyor",
            all(sira[x["adim"]] < sira["4.4"] for x in h["kesim1"]) and all(sira[x["adim"]] > sira["4.4"] for x in h["kesim2"]))
    D.kosul("Her montaj adimi (taban, duvar, ic kat, direk, kapak, ayak) parca tablosu aliyor",
            {"2.1", "2.2", "4.1", "4.2", "4.3", "4.5", "4.6", "6.1", "13.1"} <= {x["adim"] for x in h["parcalar"]})
    D.kosul("Dis derinlik tam sira sayisi (taban/kapak kirpma yok)",
            abs(h["taban_sira"] * g - h["dis_boy"]) < 1e-6, f"{h['dis_boy']:.0f} = {h['taban_sira']} x {g:.0f}")
    D.kosul("Ic kat kaynagi duvar yuksekligini karsiliyor (yarim 75 ya da tek uclu 140)",
            max(h["yarim"], c["uzunluk"] - c["uc_egim"]) >= h["ic_yuk"], f"{h['ic_yuk']:.0f} mm")
    D.kosul("Kapak rayi tek parca (ek yok)", h["kapak_ray"] <= h["duz"], f"{h['kapak_ray']:.0f} <= {h['duz']:.0f}")
    D.kosul("Duvar iki kat (capraz lamine)", kb["duvar_kat"] >= 2, f"{kb['duvar_kat']} kat = {h['duvar_t']:.0f} mm")
    D.kosul("Kose diregi M3 icin >= 6 mm et", h["direk_t"] >= 6.0, f"{h['direk_t']:.0f} mm")
    D.kosul("Gereken cubuk sayisi hesaplandi", h["cubuk_sayisi"] > 0,
            f"{h['cubuk_sayisi']} cubuk, elde {kb['elde_cubuk']}, eksik {h['eksik']}")
    D.kosul("Ilk kesim listesi (1.2) yalniz taban/ray/dis kat", all(
        x["ad"].startswith(("Taban", "Dış kat")) for x in h["kesim1"]))
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
    for i, v in enumerate(hacimler):                       # panel govdeleri birbirine girmiyor
        for w2 in hacimler[i + 1:]:
            D.kosul(f"{v['ref']} ve {w2['ref']} govdeleri cakismiyor", not cakisma3(v, w2))

    print("\n  2b · DUVARA ASILI PARCALAR (pil blogu)")
    dp = duvar_parcalari()
    ic3 = []
    for q in K.IC_PARCA:
        z0 = next((a["yuk"] for a in tasiyicilar if a["sahip"] == q["ref"]), 0.0)
        ic3 += kart_hacimleri(q, z0, nl, parcalar)
    a_dolu = next(q for q in ic3 if q["ref"] == "A (dolu)")
    D.kosul("A'nin kullanilmayan arka seridi yerlesimden turetiliyor (sutunlar arkaya artar)",
            a_dolu["y"] > next(q["y"] for q in K.IC_PARCA if q["ref"] == "A") + 10,
            f"dolu bolge y >= {a_dolu['y']:.1f} (bos serit {a_dolu['y'] - 12:.1f} mm)")
    for d in dp:
        n = _kucuk(d["nasil"])
        ist = K.YAPISTIRMA_ISTISNA.get(d["ref"])
        if ist:
            # B57b: kuralin istisnasi — yapistirici ve SOKME yolu metinde yazmali
            D.kosul(f"{d['ref']} yapistirma ISTISNASI: yapistiricisi ve sokme yolu metinde",
                    ist["yapistirici"] in n and "sökül" in n and len(ist["neden"]) >= K.DAR_ACIKLIK_GEREKCE_EN_AZ,
                    d["nasil"][:60])
        else:
            D.kosul(f"{d['ref']} sokulebilir (civata/vida/kablo bagi)",
                    ("cıvata" in n or "vida" in n or "kablo bağ" in n) and "sökül" in n
                    and "silikon" not in n and "japon" not in n, d["nasil"][:40])
        D.kosul(f"{d['ref']} duvar icinde ve direklerden uzak",
                h["direk_t"] <= d["x"] and d["x"] + d["en"] <= kb["ic_en"] - h["direk_t"] and d["z"] >= 0,
                f"x {d['x']:.0f}..{d['x'] + d['en']:.0f}")
        D.kosul(f"{d['ref']} kapaga >= 2 mm", d["z"] + d["yuk"] <= h["ic_yuk"] - 2.0, f"ust {d['z'] + d['yuk']:.0f}")
        for q in ic3:
            ar = aralik3(d, q)
            # B55j: payin altina inen cift YASAK degil, GEREKCELI olmali —
            # DAR_ACIKLIK ile ayni kural (kullanici: "yerinde ayarlarim").
            anahtar = "|".join(sorted((d["ref"], q["ref"])))
            D.kosul(f"{d['ref']} – {q['ref']} arasi >= parca payi (3B) ya da gerekceli",
                    ar >= kb["parca_payi"] or anahtar in K.DAR_ACIKLIK,
                    f"{ar:.1f} mm" + (" · DAR_ACIKLIK'te" if ar < kb["parca_payi"] else ""))
        for q in sabitler + tasiyicilar + hacimler:
            D.kosul(f"{d['ref']} ile {q['ref']} cakismiyor", not cakisma3(d, dict(q, z=q.get("z", 0.0))))
    for i, d in enumerate(dp):
        for d2 in dp[i + 1:]:
            ar = aralik3(d, d2)
            D.kosul(f"{d['ref']} – {d2['ref']} arasi >= parca payi", ar >= kb["parca_payi"], f"{ar:.1f} mm")
    # ── B58d · kart A'nin ALTINA giren duvar parcasi. TP1 10.2'de takiliyordu, kart A ise 6.2'de:
    # 27 mm'lik modul duvar-kart araligindan indirilip altina yatirilamaz, uc pedlerine havya
    # girmez. Denetim bunu hic gormuyordu (yalniz carpisma ve aciklik olculuyordu, SIRA degil).
    A_ = next(q for q in K.IC_PARCA if q["ref"] == "A")
    a_dolu_ = next(q for q in ic3 if q["ref"] == "A (dolu)")
    kart_alti = [d for d in dp if d["x"] < A_["x"] + A_["en"] and d["x"] + d["en"] > A_["x"]
                 and d["y"] < A_["y"] + A_["boy"] and d["y"] + d["boy"] > A_["y"]
                 and d["z"] + d["yuk"] <= a_dolu_["z"]]

    def _uc_y(d):                     # parca + tutucusunun duvardan en uzak noktasi
        tt = K.DUVAR_TUTUCU.get(d["ref"])
        return d["y"] + max([d["boy"]] + ([u for _a, u, _n in tutucu_parcalari(tt)] if tt else []))
    D.kosul("Kart A'nin altina giren parca (tutucusuyla) yalniz BOS seridin altinda — dolu bolgede atlama telleri sarkar",
            all(_uc_y(d) <= a_dolu_["y"] for d in kart_alti),
            f"{[(d['ref'], round(_uc_y(d), 1)) for d in kart_alti]} <= dolu y {a_dolu_['y']:.1f}")
    sira_l = {s["no"]: i for i, s in enumerate(alt_adimlar())}
    ma = monte_adim()
    gec_kalan = [d["ref"] for d in kart_alti if sira_l[ma[d["ref"]]] >= sira_l["6.2"]]
    D.kosul("Kart A'nin altina giren parca kart A'dan (6.2) ONCE takiliyor (sonra ne iner ne lehimlenir)",
            not gec_kalan, f"gec kalan {gec_kalan}" if gec_kalan else f"{[(d['ref'], ma[d['ref']]) for d in kart_alti]}")
    hepsi_ = {s["no"]: s for s in alt_adimlar()}
    lehimsiz = [d["ref"] for d in kart_alti
                if not re.search(r"tezgahta lehimle", _kucuk(" ".join(hepsi_[ma[d["ref"]]].get("yap", []))))]
    D.kosul("Kart A'nin altina giren parcanin kablolari tezgahta ONCEDEN lehimleniyor",
            not lehimsiz, f"eksik: {lehimsiz}" if lehimsiz else "on lehim talimati var")
    for r, tt in K.DUVAR_TUTUCU.items():
        if tt and tt.get("kanal"):
            ham_ = " ".join(hepsi_[ma[r]].get("yap", []))
            D.kosul(f"{r} tutucusunun bag kanali seridi geciriyor ve olcusu metne VERIDEN giriyor",
                    tt["kanal"] >= 2 * K.KABLO_BAGI["genislik"]
                    and re.search(r"\{[a-z0-9_]*kanal[^}]*\} mm kanal", ham_) is not None,
                    f"kanal {tt['kanal']:.0f} >= 2 x {K.KABLO_BAGI['genislik']} mm")
    yuva = [d for d in dp if d["ref"].startswith("YUVA")]
    D.kosul("Iki hucre yuvasi var, ikisi de ayni duvarda (kablolar kisa)", len(yuva) == 2 and len({d["duvar"] for d in yuva}) == 1)
    # B58: TEK sarj girisi — kullanici: "bunu tek kablo ile yapmam mumkun degil mi".
    sarj_yuva = [o for o in panel_ogeleri() if o["tip"] == "yuva" and "şarj" in _kucuk(o.get("etiket", ""))]
    sarj_modul = [d for d in dp if d["ref"].startswith("TP")]
    D.kosul("TEK sarj girisi: panelde tek SARJ yuvasi ve kutuda tek TP4056",
            len(sarj_yuva) == 1 and len(sarj_modul) == 1,
            f"yuva {[o['ref'] for o in sarj_yuva]} · modul {[d['ref'] for d in sarj_modul]}")
    for o in sarj_yuva:
        for t in sarj_modul:
            D.kosul(f"{o['ref']} yuvasi {t['ref']} rafinin soket kenarina hizali (x ±3, z raf seviyesinde)",
                    abs(o["x"] - (t["x"] + t["en"] / 2)) <= 3.0 and t["z"] <= o["z"] <= t["z"] + t["yuk"] + 3.0,
                    f"yuva x {o['x']:.0f} z {o['z']:.0f} · raf x {t['x'] + t['en'] / 2:.1f} z {t['z']:.0f}")
    # B58: dis besleme YOK — kullanici: "disaridan ekstra kaynak ile beslemek istemiyorum".
    dis = [o["ref"] for o in panel_ogeleri() if o["tip"] == "kuyruk"
           or "xt30" in _kucuk(o.get("ad", "") + " " + str(o.get("parca") or ""))]
    D.kosul("Dis besleme girisi yok (XT30 / kuyruk panelde degil)", not dis, str(dis))
    # pil + analog besleme grafi (B58)
    dugum = {d for c in K.PIL_KABLOLAR for d in c[:2]}
    for a, b in K.PIL_IC_BAG:
        D.kosul(f"Pil ic baglantisi {a}–{b} kablo listesindeki dugumlere oturuyor", a in dugum or b in dugum or a in ("-12", "KART_GND"))
    for ad, (a, b) in K.PIL_ANAHTAR.items():
        D.kosul(f"Anahtar {ad}: iki ucu da kablo listesinde ve panelde bir anahtar",
                a in dugum and b in dugum and ref_oge.get(ad, {}).get("tip") == "anahtar", f"{a}, {b}")
    gr = pil_grafi()
    D.kosul("Paketin eksisi (iki hucre) kart GND'de — ESP32 ile ortak",
            "KART_GND" in gr["H1-"] and "KART_GND" in gr["H2-"])
    D.kosul("Iki hucre PARALEL: eksileri ayni dugum, artilari sigortalardan sonra TP1.B+'da",
            "H2-" in gr["H1-"] and "H2+" in gr["H1+"] and "TP1.B+" in gr["H1+"])
    # YALITIM: tek sarj girisinin KOSULU. USB topragi paketin eksisine (= kart GND)
    # baglanir; kartin -12 rayi ona degseydi (eski duzende hucre 2'nin eksisi)
    # sarj kablosu -12'yi GND'ye kisa ederdi. Ayrim yalniz B0505S'in icinde.
    D.kosul("-12 rayi kart GND'den AYRI (yalitim B0505S'in icinde; grafta kenar yok)",
            "KART_GND" not in gr["-12"], str(sorted(gr["-12"]))[:90])
    IZ_CIKIS = {"IZ.OUT+", "IZ.OUT-", "CB.+", "CB.-", "MT2.IN+", "MT2.IN-", "MT2.OUT+", "MT2.OUT-",
                "KL.+", "KL.-", "A.C34", "A.C36", "-12"}
    IZ_GIRIS = {"IZ.IN+", "IZ.IN-", "F0.1", "F0.2", "MT1.OUT+", "MT1.OUT-",
                "ESP32.5V", "ESP32.GND", "KART_GND"}
    kopru = sorted({f"{a}–{b}" for a, b, *_ in list(K.PIL_KABLOLAR) + list(K.PIL_IC_BAG)
                    if (a in IZ_CIKIS and b in IZ_GIRIS) or (b in IZ_CIKIS and a in IZ_GIRIS)})
    D.kosul("B0505S'in giris ve cikis tarafini birlestiren kablo/ic bag yok",
            not kopru, f"kopru: {kopru}" if kopru else f"{len(IZ_GIRIS)} giris · {len(IZ_CIKIS)} cikis dugumu")
    D.kosul("B0505S'in iki tarafi grafta da ayri (0V ucu -12'de, GND ucu kart GND'de)",
            "-12" in gr["IZ.OUT-"] and "KART_GND" in gr["IZ.IN-"] and "KART_GND" not in gr["IZ.OUT-"])
    # ARTI taraf: yalitilmis tarafin hicbir artisi ESP32'nin 5V pinine degmemeli
    # (tek harf degisikligi devkit'i 24 V'la besletirdi — B55d).
    YIRMIDORT = {"MT2.OUT+", "KL.+", "A.C34", "IZ.OUT+", "MT2.IN+"}
    D.kosul("ESP32'nin 5V pini yalitilmis tarafin hicbir artisina baglanmiyor",
            not (gr["ESP32.5V"] & YIRMIDORT), str(sorted(gr["ESP32.5V"] & YIRMIDORT)))
    D.kosul("ESP32 5V yalniz MT1'den (5 V barasi) besleniyor", "MT1.OUT+" in gr["ESP32.5V"],
            str(sorted(gr["ESP32.5V"]))[:90])
    D.kosul("Kartin 24 V artisi MT2'den ve 5 V barasindan ayri",
            "MT2.OUT+" in gr["A.C34"] and "A.C34" not in gr["MT1.OUT+"])
    # Anahtarlar gercekten kesiyor mu: acik konumda o yol KOPMALI.
    g_pil = pil_grafi(acik=("SWP1",))
    D.kosul("PIL acikken paket MT1'e ulasmiyor (kutu enerjisiz)", "MT1.IN+" not in g_pil["TP1.OUT+"])
    # B58e (kullanici karari): ANALOG anahtari kalkti — kutunun TEK anahtari PIL. Iki sey
    # olculuyor: panelde tek guc anahtari var, ve USB kurali (PIL kapaliyken USB'den olcum
    # tarafi da beslenir, ~0.35 A) kullanicinin okudugu metinde.
    guc_anahtari = [o["ref"] for o in panel_ogeleri() if o["tip"] == "anahtar"]
    D.kosul("Panelde TEK guc anahtari var (PIL; B58e'de ANALOG kalkti)",
            guc_anahtari == ["SWP1"] and list(K.PIL_ANAHTAR) == ["SWP1"], str(guc_anahtari))
    usb_k = [x[0] for x in K.KULLANIM if "usb'yi pc'ye takarken pil açık" in _kucuk(x[2])]
    D.kosul("Kullanim tablosu USB kuralini veriyor (PC'ye takarken PIL acik)", len(usb_k) == 1, str(usb_k))
    ks = {(a, b) for a, b, *_ in K.PIL_KABLOLAR}
    D.kosul("PIL anahtari paket tarafinda (TP1.OUT+ -> SWP1 -> MT1.IN+)",
            ("TP1.OUT+", "SWP1.1") in ks and ("SWP1.2", "MT1.IN+") in ks and ("TP1.OUT+", "MT1.IN+") not in ks)
    D.kosul("F0 5 V barasi ile B0505S arasinda (analog arizasi paketi cekemez)",
            ("MT1.OUT+", "F0.1") in ks and ("F0.2", "IZ.IN+") in ks and ("MT1.OUT+", "IZ.IN+") not in ks)
    # B58e: F0 yalniz IC arizada atar -> kutu icinde. Panelde "F0 1A" olcum akiminin (YUK
    # jaklari, bilerek sigortasiz) korundugunu dusunduruyordu.
    D.kosul("F0 kutu icinde (duvar parcasi), panelde degil — olcum girisi sigortali sanilmasin",
            "F0" not in ref_oge and any(d["ref"] == "F0" for d in K.DUVAR_PARCA))
    D.kosul("TP4056 yuku OUT'tan aliyor (B- degil)", all(not (a.startswith("TP") and a.endswith("B-") and b.startswith("MT"))
                                                       for a, b, *_ in K.PIL_KABLOLAR))
    g_p = pil_grafi(asama="paket")
    D.kosul("Yalniz paket (10.3) kuruluyken ESP32 beslenebiliyor ve yalitilmis tarafa kablo yok",
            "ESP32.5V" in g_p.get("MT1.OUT+", set()) and not any(u in g_p for u in ("IZ.OUT-", "KL.+", "A.C34")))
    D.kosul("10.3 tablosu yalniz paket, 10.4 yalniz analog kablolarini listeliyor",
            hepsi["10.3"].get("asama") == "paket" and hepsi["10.4"].get("asama") == "analog"
            and {pil_asama(c) for c in K.PIL_KABLOLAR} == {"paket", "analog"})
    m103 = _kucuk(" ".join(hepsi["10.3"]["yap"] + hepsi["10.3"]["kontrol"]))
    D.kosul("10.3 paralel hucre esitleme kuralini veriyor (±0.1 V)", "±0.1 v" in m103 and "paralel" in m103)
    # Olcut AYNI kontrol maddesinde: 10.4'te "otmemeli" iki kez geciyor, adimin
    # tamaminda aramak yalitim maddesi "otmeli"ye donse bile yesil kalirdi.
    D.kosul("10.4 kontrolu B0505S yalitimini olcturuyor (bacak 2 ↔ 4 'otmemeli')",
            any("b0505s bacak 2 (−vin) ↔ bacak 4 (−vout)" in _kucuk(k) and "ötmemeli" in _kucuk(k)
                for k in hepsi["10.4"]["kontrol"]))
    # XT30 KODLUYDU; vidali klemens degil. Ters 24 V iki TL072'yi oldurur (B15/F8, TVS
    # koruyamaz) -> kutup enerjiden ONCE, ayni maddede iki uc da olculmeli.
    D.kosul("10.4 klemensin kutbunu enerjiden ONCE olcturuyor (+ ↔ C34, − ↔ C36)",
            any("kutup" in _kucuk(k) and "c34" in _kucuk(k) and "c36" in _kucuk(k) and "önce" in _kucuk(k)
                for k in hepsi["10.4"]["kontrol"]))
    m106 = _kucuk(" ".join(hepsi["10.6"]["yap"]))
    D.kosul("10.6 sarj kurali: PIL kapali, tek Type-C, sarjda olcum yok",
            "pil anahtarını kapat" in m106 and "tek type-c" in m106 and "ölçüm yapma" in m106)
    # Olcut sarj YORDAMINI veren satirda: kural iki satirda geciyor (guc + isil),
    # tum tabloda aramak birini kaybetse bile yesil kalirdi.
    guc = [x for x in K.KULLANIM if "şarj:" in _kucuk(x[2])]
    D.kosul("Kullanim tablosunun sarj yordami: PIL kapali, tek Type-C, sarjda olcum yok",
            len(guc) == 1 and all(w in _kucuk(guc[0][2]) for w in ("pil kapalı", "tek type-c", "ölçüm yapma")),
            guc[0][0] if guc else "sarj yordami veren satir yok")
    # B58 guc butcesi — sayilar tasarim3_sabit'ten, iddia fiziksel sinira karsi.
    bb = besleme_butcesi()
    # B58c: plan iki surum icin de gecerli (kullanici fiyatla secer) -> her secenek AYRI
    # denetlenir: kucuk modulde yuk siniri, buyuk modulde asgari yuk kritik.
    for pw in T.IZOLE_GUC_SECENEK:
        D.kosul(f"B0505S {pw:.0f} W: yuk anmanin %{T.IZOLE_YUK_PAYI * 100:.0f}'inin altinda",
                bb["iz_cikis"] / pw <= T.IZOLE_YUK_PAYI,
                f"{bb['iz_cikis']:.2f} W / {pw:.0f} W = %{bb['iz_cikis'] / pw * 100:.0f} (24 V yuku {bb['p24']:.2f} W)")
    # B58b: Hi-Link veri sayfasi: regulesiz modulde yuk anmanin %10'undan az olmasin (bosta cikis
    # yukselir). Olcut EN DUSUK yukte — 10 W'lik bir modul alinsa 24 V yuku ona "bos" kalirdi.
    for pw in T.IZOLE_GUC_SECENEK:
        D.kosul(f"B0505S {pw:.0f} W: en dusuk yuk ureticinin asgari yukunun (%{T.IZOLE_ASGARI_YUK * 100:.0f}) ustunde",
                bb["iz_asgari_w"] / pw >= T.IZOLE_ASGARI_YUK,
                f"%{bb['iz_asgari_w'] / pw * 100:.0f} (24 V rayi {T.RAY24_AKIM_ASGARI * 1e3:.0f} mA)")
    # B58f (sim3_kutu_besleme.py): ACILIS. Akim sinirli modul MT2'nin girisini UVLO'ya ceker ve
    # aktarilan guc ~ I_sinir x (UVLO + 0.1 V) kalir. Kart 24 V'ta P24 istiyor: modulun ANMA akimi
    # tek basina bunu tasiyabilmeli (sinirin anmadan yuksek oldugu garanti degil). 1 W'ta 0.2 A < 0.35 A.
    i_gerek = bb["p24"] / T.MT3608_VERIM / (T.MT3608_UVLO + 0.1)
    for pw in T.IZOLE_GUC_SECENEK:
        # tabloda olmayan bir secenek (ör. 0.5 W) CÖKERTMEMELI: anma = P / 5 V. Ilk surumde
        # KeyError atiyordu; mutasyon 'yakalandi' dedi ama asil iddialari cokus maskeliyordu.
        i_anma = T.IZOLE_ANMA_AKIM.get(pw, pw / 5.0)
        D.kosul(f"B0505S {pw:.0f} W: anma akimi acilista karti 24 V'a cikarmaya yetiyor (UVLO sinirinda)",
                i_anma >= i_gerek,
                f"anma {i_anma:.2f} A >= {i_gerek:.2f} A (= {bb['p24']:.2f} W / verim / "
                f"{T.MT3608_UVLO + 0.1:.2f} V)")
    # B58f: MT2 girisinde toplu kondansator — grafta MT2.IN±'da, degeri benzetimin alt sinirinin
    # ustunde ve STOK KAYDININ kendisi o degerde (sabit ile envanter ayrismasin).
    cb = next((d for d in K.DUVAR_PARCA if d["ref"] == "CB"), None)
    _st = B.Stok()
    cb_kayit = next((r for r in _st.kayit if cb and r["ad"].strip().lower().startswith(cb["stok"][0].lower())
                     and r["kategori"] == cb["stok"][1]), None) if _st.var else None
    m_cb = re.match(r"\s*(\d+)\s*µF\s+(\d+)\s*V", cb_kayit["ad"]) if cb_kayit else None
    D.kosul("MT2 girisinde toplu kondansator (CB) var ve MT2.IN±'ya bagli (B58f)",
            cb is not None and ("CB.+", "MT2.IN+") in ks and ("CB.-", "MT2.IN-") in ks,
            "yok" if cb is None else "CB.+ → MT2.IN+, CB.− → MT2.IN−")
    D.kosul("CB >= 470 uF (benzetimin her modelde yeten en kucuk degeri) ve anma >= 1.5 x 7 V",
            T.MT2_GIRIS_C >= 470e-6 and T.MT2_GIRIS_V >= 1.5 * 7.0,
            f"{T.MT2_GIRIS_C * 1e6:.0f} uF {T.MT2_GIRIS_V:.0f} V (B0505S bosta en fazla ~7 V, 10.1)")
    D.kosul("CB'nin stok kaydi sabitle ayni deger (envanter ile tasarim3_sabit ayrismiyor)",
            (not _st.var) or (m_cb is not None and math.isclose(float(m_cb.group(1)) * 1e-6, T.MT2_GIRIS_C)
                              and math.isclose(float(m_cb.group(2)), T.MT2_GIRIS_V)),
            cb_kayit["ad"] if cb_kayit else "stok kaydi yok")
    m104k = [_kucuk(k) for k in hepsi["10.4"]["kontrol"]]
    D.kosul("10.4 CB'nin kutbunu enerjiden ONCE olcturuyor (seritli bacak ↔ MT2 IN− ayni maddede)",
            any("şeritli" in k and "mt2" in k and "ötmeli" in k for k in m104k))
    # B58b: stoktaki 100 uF'lerin 13/15'i 16 V; 10.5 "100 uF ekle" diyordu, 24 V rayina
    # 16 V'luk elektrolitik takilirsa patlar. Onerilen her kondansator gerilimiyle yazilmali.
    m105k = _kucuk(" ".join(hepsi["10.5"]["yap"]))
    kond = [(float(c), float(v)) for c, v in re.findall(r"(\d+(?:\.\d+)?)\s*µf\s+(\d+)\s*v\b", m105k)]
    D.kosul("10.5'in 24 V rayina onerdigi kondansator gerilim sinifi rayin >= 1.5 kati",
            bool(kond) and all(v >= 1.5 * 24.0 for _c, v in kond), str(kond))
    D.kosul("F0 normal analog akiminin en az 3 kati (bosuna atmaz)",
            T.F0_SIGORTA >= 3 * bb["i_f0"], f"{T.F0_SIGORTA:.1f} A >= 3 x {bb['i_f0'] * 1e3:.0f} mA")
    D.kosul("Paket akimi (kotu hal, tek hucre) MT3608 modul anmasinin altinda",
            bb["i_kol"] <= T.MT3608_ANAHTAR_AKIM, f"{bb['i_kol']:.2f} A <= {T.MT3608_ANAHTAR_AKIM:.1f} A")
    D.kosul("Paket akimi kotu halde TP4056 korumasina (DW01A) 1.5x pay birakiyor — yuk altinda kesmez",
            1.5 * bb["i_kol"] <= T.DW01_ASIRI_AKIM, f"1.5 x {bb['i_kol']:.2f} A <= {T.DW01_ASIRI_AKIM:.1f} A")
    D.kosul("Calisma ve sarj suresi metne sabitten giriyor (elle yazilmis saat yok)",
            any("{pil_suresi}" in x[2] and "{sarj_suresi}" in x[2] for x in K.KULLANIM),
            f"calisma ≈ {bb['sure_sa']:.1f} sa · sarj ≈ {bb['sarj_sa']:.1f} sa")
    esp = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
    usb = ref_oge["USB"]
    D.kosul("ESP32 USB soketi arka duvara <= 3 mm", esp["y"] <= 3.0, f"y = {esp['y']:.0f}")
    D.kosul("USB yuvasi x'i soket x'iyle hizali (<= 1.5 mm)",
            abs(esp["x"] + esp["soket_x_ofset"] - usb["x"]) <= 1.5,
            f"soket {esp['x'] + esp['soket_x_ofset']:.0f} · yuva {usb['x']:.0f}")
    esp_alt = next(a["yuk"] for a in tasiyicilar if a["sahip"] == "ESP32")
    D.kosul("USB yuvasi z'si soket z'siyle hizali (<= 3 mm)",
            abs(esp_alt + esp["soket_z"] - usb["z"]) <= 3.0, f"soket {esp_alt + esp['soket_z']:.0f} · yuva {usb['z']:.0f}")
    # ── B55h · yalitkan kaplama (kullanici karari: tirnak cilasi) ───────────
    kart_ref = {p["ref"] for p in K.IC_PARCA}
    D.kosul("Kaplanacak her bolge gercek bir kart/parca gosteriyor",
            all(k["ref"] in kart_ref for k in K.KAPLAMA),
            " · ".join(sorted({k["ref"] for k in K.KAPLAMA})))
    # Kaplama, o kartin kutuya girdigi adimdan ONCE yapilmali (elde kolay,
    # kutuda imkansiz). 'ne_zaman' metni bunu soyluyor; sira veriden olculuyor.
    kart_adim = {p["ref"]: next((s["no"] for s in aa
                                 if p["ref"] in (s.get("vurgu") or []) and s["tur"] == "montaj"), None)
                 for p in K.IC_PARCA}
    D.kosul("Kaplama, kart kutuya girmeden ONCE yapiliyor (metin montaj adimindan once diyor)",
            all(kart_adim.get(k["ref"]) is None or kart_adim[k["ref"]] in k["ne_zaman"]
                or "ÖNCE" in k["ne_zaman"] or "önce" in k["ne_zaman"] for k in K.KAPLAMA),
            f"kart B montaj adimi {kart_adim.get('B')}")
    # En yuksek gerilimli kart MUTLAKA kaplama listesinde olmali.
    # 'Listede var mi' YETMEZ: ilk yazdigim iddia bunu soruyordu ve mutasyon
    # KACTI — kartin TAMAMINI kaplayan kayit A'ya tasinsa bile, ayni kartin
    # 'lehim noktalari' kaydi listede kaldigi icin yesil kaliyordu. Artik
    # kapsam soruluyor: zincirin kartinda TAM KART kaplamasi olmali.
    hv_kart = next(p["ref"] for p in K.IC_PARCA if p["ref"] == "B")
    tam = {k["ref"] for k in K.KAPLAMA if k["kapsam"] == "kart"}
    D.kosul("Zincirin bulundugu kartin TAMAMI kaplaniyor (nokta kaplamasi yetmez)",
            hv_kart in tam,
            f"tam kart: {sorted(tam)} · zincir {T.KANALLAR[1]['fs_ust']:.0f} V -> "
            f"{T.KANALLAR[1]['fs_ust'] / 6:.0f} V basamak")
    D.kosul("Her kaplama kaydinin kapsami tanimli (kart / nokta)",
            all(k.get("kapsam") in ("kart", "nokta") for k in K.KAPLAMA))
    D.kosul("Kaplanmayacak yerler de gerekcesiyle yazili (>= 40 karakter)",
            all(len(g) >= 40 for _a, g in K.KAPLAMA_HARIC), f"{len(K.KAPLAMA_HARIC)} kalem")

    # ── B55g · KUTU ICI ACIKLIK ENVANTERI ───────────────────────────────────
    # Bugune kadar hicbir iddia ACIKLIK olcmuyordu: cakisma3 yalnizca cakismaya
    # bakiyor ve parca_payi = 6 mm sadece IC_PARCA ciftlerine + duvar parcalarina
    # uygulaniyordu. Tasiyicilar, ek bloklar, direk/ray ve panel govdeleri kapsam
    # disindaydi; F0-kart A 1.70 mm, ESP32-B ayagi 0.54 mm, ankraj-kart B 0.30 mm
    # hepsi 1784 iddianin altindan gecti. Liste hem TAVAN hem TABAN:
    # yeni bir dar cift -> kirmizi, artik dar olmayan bir kayit -> kirmizi.
    # Kullanici karari (B55g-b): ahsap-ahsap milimetreler gerekcelendirilmiyor —
    # bicakla yerinde ayarlaniyor. Gerekce YALNIZ en az bir tarafi iletken olan
    # ciftlerden isteniyor; ahsap-ahsap ciftlerde sadece CAKISMA bakiliyor.
    dar = dar_aciklikllar(nl, parcalar, yalniz_iletken=True)
    dar_anahtar = {f"{a}|{b}" for _d, a, b in dar}
    tumu = dar_aciklikllar(nl, parcalar)
    D.kosul("Hicbir govde cifti CAKISMIYOR (3B, butun siniflar — ahsap dahil)",
            all(d >= 0.0 for d, _a, _b in tumu),
            f"{len(kutu_govdeleri(nl, parcalar))} govde · {len(dar)} iletken taraflı + {len(tumu) - len(dar)} ahşap-ahşap dar çift")
    yazisiz = sorted(dar_anahtar - set(K.DAR_ACIKLIK))
    D.kosul(f"{K.KUTU['parca_payi']:.0f} mm altindaki her ILETKEN tarafli cift gerekceli",
            not yazisiz, f"gerekcesiz: {yazisiz}" if yazisiz else f"{len(dar)} cift, hepsi yazili")
    eskimis = sorted(set(K.DAR_ACIKLIK) - dar_anahtar)
    D.kosul("DAR_ACIKLIK'te artik dar olmayan (eskimis) kayit yok",
            not eskimis, f"eskimis: {eskimis}" if eskimis else "sapma yok")
    kisa = sorted(k for k, v in K.DAR_ACIKLIK.items() if len(v) < K.DAR_ACIKLIK_GEREKCE_EN_AZ)
    D.kosul(f"Her dar aciklik gerekcesi en az {K.DAR_ACIKLIK_GEREKCE_EN_AZ} karakter",
            not kisa, f"kisa: {kisa}" if kisa else f"en kisa {min(len(v) for v in K.DAR_ACIKLIK.values())} karakter")
    D.kosul("Gerekcesinde olculen sayi yazan her kayit gercek boslukla tutuyor (0.3 mm)",
            all(abs(d - float(re.match(r"\s*([\d.]+) mm", K.DAR_ACIKLIK[f"{a}|{b}"]).group(1))) <= 0.3
                for d, a, b in dar if re.match(r"\s*([\d.]+) mm", K.DAR_ACIKLIK.get(f"{a}|{b}", ""))),
            f"en dar {dar[0][0]:.2f} mm ({dar[0][1]} ↔ {dar[0][2]})")

    # ── B55g · kart B'nin YONU ve HV kablosu ────────────────────────────────
    # Eski iddia ("kablo <= 60 mm") 43.6 mm yazip yesil geciyordu: 2B idi
    # (jakin z 63'u ile plaketin z 8'i arasindaki dususu saymiyordu), lehim
    # noktasi yerine kartin MERKEZINI aliyordu ve ankrajdan gecen kirik yolu
    # duz cizgi saniyordu. Gercek yol dort yonelimde 74-101 mm — yani 60 mm
    # kurali HICBIR yonelimde saglanamiyordu ve denetim bunu goremiyordu.
    hvj = ref_oge["J2.1"]
    bk = next(p for p in K.IC_PARCA if p["ref"] == "B")
    tablo = hv_yon_tablosu(nl, parcalar)
    D.kosul("Kart B'nin yonu VERI (kare plaket dort turlu takilabiliyor, ayaklar 6.1'de yapistiriliyor)",
            bk.get("yon") in (0, 90, 180, 270), f"yon = {bk.get('yon')}")
    en_uzak = max(tablo, key=lambda y: tablo[y][0])
    en_kisa = min(tablo, key=lambda y: tablo[y][1])
    D.kosul("Secilen yon HV dugumunu iletkenlerden EN UZAK tutan yonelim",
            bk["yon"] == en_uzak,
            " · ".join(f"{y}°:{tablo[y][0]:.1f}" for y in sorted(tablo)) + f" mm -> en iyi {en_uzak}°")
    D.kosul("Secilen yon ayni zamanda HV kablosunu EN KISA yapan yonelim (olcutler ayrisirsa kirmizi)",
            bk["yon"] == en_kisa,
            " · ".join(f"{y}°:{tablo[y][1]:.0f}" for y in sorted(tablo)) + f" mm -> en iyi {en_kisa}°")
    hv_nokta = hv_dugumu(bk)
    en_yakin = min(((nokta_kutu_mesafe(hv_nokta, g), g["ref"]) for g in iletken_govdeler("B", nl, parcalar)))
    D.kosul("Kutu icinde 617 V'luk dugum her iletkenden takviyeli kacak yolu kadar uzak",
            en_yakin[0] >= T.IEC60664_CREEPAGE_TAKVIYELI,
            f"en yakin {en_yakin[1]} {en_yakin[0]:.1f} mm >= {T.IEC60664_CREEPAGE_TAKVIYELI} mm")
    hv_uz, _yol = hv_kablo_yolu(bk)
    # Yon ve kablo boyu ELLE yazilmasin: kullanicinin okudugu adim metni de,
    # veri notu da yer tutucudan uretilsin (havalandirma dersi).
    yon_metin = [s["no"] for s in aa if "{yon_b}" in " ".join(s.get("yap", []))]
    D.kosul("Kart B'yi takan adim yonu VERIDEN yaziyor (elle kose adi yok)",
            bool(yon_metin) and "{yon_b}" in bk["nasil"],
            f"{yon_metin} · {kart_yon_cumlesi(bk)} · kablo {hv_uz:.0f} mm "
            f"(jak z {ref_oge['J2.1']['z']:.0f} -> plaket z 8)")
    sira_aa = {s["no"]: i for i, s in enumerate(aa)}
    hv_bagla = next((s["no"] for s in aa if "ankraj" in _kucuk(" ".join(s.get("yap", [])))), None)
    D.kosul("Yon, HV kablosu baglanmadan ONCEKI bir adimda soyleniyor",
            bool(yon_metin) and hv_bagla is not None
            and min(sira_aa[n] for n in yon_metin) < sira_aa[hv_bagla],
            f"yon {yon_metin} -> HV kablosu {hv_bagla}")
    # Ayaklar kutuda SABIT; kart uzerinde doner. Secilen yonde ayaklara denk
    # gelen plaket delikleri gercekten BOS 2x2 kose bloklarindan olmali.
    vm = Y.vida_merkezleri("B")
    ayak_delik = [kart_don("B", c, r, (360 - bk["yon"]) % 360) for c, r in (vm[0], vm[3])]
    D.kosul("Secilen yonde ayaklara denk gelen plaket delikleri bos kose bloklarindan",
            all(d in vm for d in ayak_delik), f"{ayak_delik} ⊂ {vm}")

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
        if o["tip"] == "civata":
            D.kosul(f"{o['ref']} civata deligi bir ic-kat cubugunun icinde (kenara >= 3 mm, cubuk o yukseklikte var)",
                    any(x0 + DELIK_KENAR_PAYI <= o["x"] - w / 2 and o["x"] + w / 2 <= x0 + cw - DELIK_KENAR_PAYI
                        and z0 <= o["z"] - w / 2 for x0, cw, z0 in cub), f"x={o['x']:.0f} z={o['z']:.0f}")
        elif o["tip"] == "yuva":
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
            D.kosul(f"{o['ref']} rengi stok adinda",
                    o["renk"].replace("kirmizi", "kırmızı").replace("sari", "sarı").replace("yesil", "yeşil")
                    in _kucuk(o["parca"][0]),
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
    # B58: XT30 kutuda kullanilmiyor — kartin 24 V telleri ic klemense. Yerlesim
    # notu (tezgahta XT30) bunu soylemeli, yoksa kullanici kuyrugu arar.
    n6 = _kucuk(V.KART_DISI_NOTU["J6"])
    D.kosul("KART_DISI_NOTU J6 kutuda XT30 degil ic klemens diyor",
            "klemens" in n6 and "kutuda" in n6, V.KART_DISI_NOTU["J6"][:60])
    for r in ("J3", "J7"):
        nr = _kucuk(V.KART_DISI_NOTU[r])
        D.kosul(f"KART_DISI_NOTU {r} born jak diyor (klemens degil)",
                "born" in nr and not nr.startswith("2 kutuplu") and "bariyer klemens (" not in nr)
    kul = _kucuk(" ".join(x[2] for x in K.KULLANIM))
    D.kosul("Kullanim metni COM baypasini yasakliyor", "com'a krokodil takma" in kul and "baypas" in kul)
    D.kosul("Kullanim metni HV'de USB/PC topragini yasakliyor", "usb'yi pc'ye takma" in kul)
    D.kosul("Pil testinde V jaki zorunlu ve YUK bos", "zorunlu" in kul and "yük boş" in kul)
    D.kosul("Kullanim menzilleri yer tutucudan (elle yazilmiyor)",
            all("{" in x[0] for x in K.KULLANIM[:3]) and any("{pil_akim}" in x[2] for x in K.KULLANIM))

    print("\n  5 · PARCALAR VE SIRA")
    m = monte_adim()
    for r in sorted(V.KART_DISI_NOTU):
        D.kosul(f"{r} bir alt adimda kutuya giriyor", r in m, m.get(r, "YOK"))
    for r in sorted(K.KUTU_NOTU):
        D.kosul(f"{r} (kutu parcasi) bir alt adimda monte ediliyor ve notu var", r in m, m.get(r, "YOK"))
    # Ters yon: monte edilen her ref'in BIR notu olmali. Eskiden yalniz var olan notlar
    # geziliyordu, eksik anahtar gorunmuyordu ve belgede SW'nin "Kural" hucresi bostu (B55d).
    for r in sorted({x for st in aa for x in st.get("monte", [])}):
        D.kosul(f"{r} icin kural metni var (belgede 'Kural' hucresi dolu)",
                bool(V.KART_DISI_NOTU.get(r) or K.KUTU_NOTU.get(r)))
    # B55 — kapak sirasi. Eskiden burada "pil blogu kapali kutu testinden SONRA"
    # yaziyordu: iddia kusuru ONAYLIYORDU (kapak 13'te kapaniyor, 14-15 kapali
    # kutunun icine parca takiyordu). Dogru degismez: kutu icine giren HICBIR is
    # kapanistan sonra olamaz — tek tek alt adim degil, kural olarak olculuyor.
    kapanislar = [s["no"] for s in aa if s.get("kapanis")]
    D.kosul("Kutunun kapandigi TEK alt adim isaretli ('kapanis')", len(kapanislar) == 1, str(kapanislar))
    kapanis = kapanislar[0] if kapanislar else aa[-1]["no"]
    IC_TUR = {"montaj", "duvar_parca", "pil_kablo", "kablo", "delik", "duvar_ic", "direk"}
    ic_isi = [s for s in aa if s.get("monte") or s.get("kablo") or s["tur"] in IC_TUR]
    gec = [s["no"] for s in ic_isi if sira[s["no"]] > sira[kapanis]]
    D.kosul(f"Kapak kapandiktan ({kapanis}) sonra kutu icine giren adim yok", not gec, str(gec))
    D.kosul("Kapanis son adimda ve kapali kutu testinden hemen once",
            sira[kapanis] == len(aa) - 2 and aa[-1]["no"] == "14.3")
    D.kosul("Kapak once yapilip denenip CIKARILIYOR (13.2), kapanis en sonda",
            sira["13.1"] < sira["13.2"] < sira["14.1"] and sira["13.2"] < sira[kapanis]
            and "çıkar" in _kucuk(" ".join(hepsi["13.2"]["yap"] + hepsi["13.2"]["kontrol"])))
    D.kosul("13.2 kapagin kapanis adimina kadar acik kaldigini soyluyor",
            f"adım {kapanis.split('.')[0]}" in _kucuk(" ".join(hepsi["13.2"]["yap"]))
            and "kaldır" in _kucuk(" ".join(hepsi["13.2"]["yap"])))
    D.kosul("MT3608 ayari montajdan once; paket analogdan once; ilk enerji en sonda (10.1 -> 10.5)",
            sira["10.1"] < sira["10.2"] < sira["10.3"] < sira["10.4"] < sira["10.5"] < sira["10.6"])
    # B58: pil blogu kalibrasyondan ONCE — kutu artik yalniz kendi pilinden
    # calisiyor, yani Adim 11-12'nin enerjisi bu paketten geliyor.
    pil_adim = [s["no"] for s in aa if s["tur"] in ("duvar_parca", "pil_kablo")]
    D.kosul("Pil blogu (duvar parcasi + pil kablolari) ilk kapidan (11.2) ONCE bitiyor",
            bool(pil_adim) and max(sira[n] for n in pil_adim) < sira["11.2"], str(pil_adim))
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
                    r in ref_oge or any(p["ref"] == r for p in K.IC_PARCA)
                    or any(d["ref"] == r for d in K.DUVAR_PARCA) or kok in m)
    D.kosul("Delme adimi duvar dikilmeden once (duz zeminde)", sira["3.1"] < sira["4.1"])
    # Kapak civata delikleri kutu BOSKEN acilmali: 13.2'de acilirken gerekcesi kendi kendisiyle
    # celisiyordu ("kutu dolduktan sonra delmek talasi kartlarin ustune doker") — oysa 13.2'de
    # kart A, B, ESP32, sont, Q1 ve butun kablolar coktan takilmisti (B55d).
    ilk_montaj = min(sira[x["no"]] for x in aa if x.get("monte") or x["tur"] == "montaj")
    D.kosul("Kapak civata delikleri kutuya parca girmeden ONCE aciliyor",
            sira["4.7"] < ilk_montaj, f"4.7 -> {sira['4.7']}, ilk montaj -> {ilk_montaj}")
    D.kosul("Somun bloklari delikler acildiktan SONRA yapistiriliyor (civataya merkezlenir)",
            sira["4.7"] < sira["13.1"] < sira["13.2"])
    D.kosul("Ic kat delikleri duvar bittikten sonra, jaklardan once", sira["4.5"] < sira["5.1"] < sira["5.2"])
    ref_panel = {o["ref"]: o["panel"] for o in panel_ogeleri()}
    for st in aa:
        if st["tur"] != "delik":
            continue
        # B58: panel ogesi anmayan delik adimi (5.1 — iki duvarin da ic katini deler)
        # IKI paneli de cizmeli; bos kume ile gecmesin (sabit-panel mutasyonu kaciyordu).
        ister = {ref_panel[r] for r in (st.get("vurgu", []) + st.get("monte", [])) if r in ref_panel}             or {"ön", "arka"}
        cizilen = cizim_panelleri(st)
        D.kosul(f"{st['no']} cizimi takilan ogelerin panellerini kapsiyor",
                ister <= set(cizilen), f"gereken {sorted(ister)}, cizilen {sorted(cizilen)}")
    D.kosul("Ikinci kesim (4.4) duvarlar bitince, ic kattan once", sira["4.3"] < sira["4.4"] < sira["4.5"])
    D.kosul("Sont demeti kutuya girmeden once lehimleniyor", sira["6.4"] < sira["6.6"] < sira["7.2"])
    D.kosul("Ayaklar kart vidalanmadan once", sira["6.1"] < sira["6.2"])
    for a in tasiyicilar:
        if a["sahip"]:
            D.kosul(f"{a['ref']} sahibi monte edilmeden once yapiliyor",
                    sira[a["adim"]] <= sira[m.get(a["sahip"], "6.2" if a["sahip"] == "A" else "6.3")])
    D.kosul("Ilk enerji kablolar bittikten sonra, ESP32'den once",
            all(sira[no] < sira["10.5"] for s in aa for no in [s["no"]] if s.get("kablo")) and sira["10.5"] < sira["11.1"])
    D.kosul("Her KAPI 3..8 kendi alt adiminda", all(any(s.get("kapi") == [kk] for s in aa) for kk in range(3, 9)))
    D.kosul("Kapali kutuda uctan uca test var", any(s["no"] == "14.3" and s.get("kapi") for s in aa))
    for kk in range(1, 9):
        D.kosul(f"KAPI {kk} planda geciyor", any(kk in s.get("kapi", []) for s in aa))
    yerlesim_nolar = {a.no for a in yerlesim_alt_adimlari(nl, parcalar)}
    for no, _ne in K.ON_KOSUL:
        D.kosul(f"On kosul Yerlesim {no} yerlesim planinda var", no in yerlesim_nolar)
    D.kosul("Firmware komutlari kalibrasyon tablosunda", {"Z", "n", "z", "y", "?"} <= {x[0] for x in K.KALIBRASYON})
    for o in oge:
        D.kosul(f"{o['ref']} icin 'neden' gerekcesi var (>= 40 karakter)", len(o.get("neden", "")) >= 40)
    D.kosul("PİL jaklari (buyuk boy) YÜK jaklariyla ayni delik/metal olcusunde",
            all(ref_oge[r]["delik_mm"] == ref_oge["J3.1"]["delik_mm"] and ref_oge[r]["metal_mm"] == ref_oge["J3.1"]["metal_mm"]
                for r in ("J7.1", "J7.2")))
    # B61 (kullanici 2026-09-26): "pilin + tarafi nerede, yukun hangi tarafi +". Semalar ELLE
    # renkliydi ve B60'ta eskidi (YUK siyah cizili, gercekte yesil). Artik veriden; olculen:
    # semadaki her jak dairesinin rengi panel verisindekiyle ayni, ve gereken jaklar semada.
    sema_renk = {}
    for tur, gerek in (("akim", {"J3.1", "J3.2", "J1.1", "J1.2"}), ("pil", {"J7.1", "J7.2", "J1.1", "J1.2"})):
        svg = ciz_kullanim(tur)
        bulunan = dict(re.findall(r'data-jak="([^"]+)"[^>]*fill="([^"]+)"', svg))
        yanlis = [f"{r}:{f}" for r, f in bulunan.items() if f != JAK_RENK[ref_oge[r]["renk"]]]
        sema_renk[tur] = (sorted(gerek - set(bulunan)), yanlis)
    D.kosul("Kullanim semalarinda jak renkleri panelle ayni ve gereken jaklar semada (B61)",
            all(not e and not y for e, y in sema_renk.values()), str(sema_renk))
    # Devreden gelen kutup: sont kart GND tarafinda (low-side) -> YUK 1/YUK 2 ikisi de EKSI hat;
    # PIL 2 = GND = pilin eksisi; PIL 1 = Q1 drain, pilin artisi DIRENC USTUNDEN gelir.
    kutup_bekle = {"J3.1": "−", "J3.2": "−", "J7.2": "−", "J7.1": "+"}
    kutup_yanlis = [f"{r} '{ref_oge[r].get('alt_etiket', '')}' ({b} bekleniyor)" for r, b in kutup_bekle.items()
                    if b not in ref_oge[r].get("alt_etiket", "") or ({"+", "−"} - {b}).pop() in ref_oge[r].get("alt_etiket", "")]
    D.kosul("PIL ve YUK jaklarinin etiketi DOGRU kutbu soyluyor (YUK 1/2, PIL 2 = −; PIL 1 = + direncten)",
            not kutup_yanlis and "direnç" in ref_oge["J7.1"].get("alt_etiket", ""),
            "; ".join(kutup_yanlis) if kutup_yanlis else " · ".join(f"{ref_oge[r]['etiket']}: {ref_oge[r]['alt_etiket']}"
                                                                   for r in kutup_bekle))
    kul_akim = _kucuk(next(x[2] for x in K.KULLANIM if x[1].startswith("YÜK 1")))
    D.kosul("Kullanim tablosu akimin EKSI hattan olculdugunu ve + ucun kutuya girmedigini soyluyor",
            "eksi hattan" in kul_akim and "kutuya" in kul_akim and "girmez" in kul_akim)
    # B60 (kullanici 2026-09-26): "iki farkli model yan yana uyumsuz gorunur" -> panelde TEK jak
    # modeli. Eskiden "buyuk boy > kucuk vidali" iddiasi vardi; kucuk model kalmadi.
    jaklar_on = [o for o in oge if o["tip"] == "jak"]
    modeller = {re.sub(r"\s+(Siyah|Kırmızı|Mavi|Sarı|Yeşil)\b", "", o["parca"][0]) for o in jaklar_on}
    olculer = {(o["delik_mm"], o["metal_mm"], o["derin_mm"]) for o in jaklar_on}
    D.kosul("Paneldeki butun born jaklar AYNI model ve olcude (gorunus birligi, B60)",
            len(modeller) == 1 and len(olculer) == 1, f"{sorted(modeller)} · {sorted(olculer)}")
    # HV'nin ayirt ediciligi artik RENKTE (boyut farki kalkti): B15/A1 — V'ye takilan 615 V R4'u yakar.
    hvr = ref_oge["J2.1"]["renk"]
    ayni = [o["ref"] for o in jaklar_on if o["ref"] != "J2.1" and o["renk"] == hvr]
    D.kosul("HV'nin rengini baska hicbir jak kullanmiyor (yanlis delik = 615 V)",
            not ayni, f"HV {hvr}" + (f" · ayni renk: {ayni}" if ayni else " · tek"))
    m31 = _kucuk(" ".join(hepsi["3.1"]["yap"]))
    D.kosul("3.1 metni olculerin delik MERKEZI oldugunu ve yuvarlak/oval ayrimini soyluyor",
            "merkezi" in m31 and "yuvarlak" in m31 and "oval" in m31)
    # ── B55i: her panel capinin DELME'de bir yontemi olmali ────────────────
    # Kok sebep ayni sinif: rehber Ø8'de bitiyordu, F0'in Ø12'si (kutudaki EN
    # BUYUK delik, 18 mm cubukta her yanda 3.0 mm et) hicbir yerde tarif
    # edilmiyordu ve kullanici Adim 3.1'e geliyor. Kapsam artik olculuyor.
    # ⚠ Ilk yazdigim suzgec `yuvarlak_mi()` idi — o "arkasina ic kat cubugu
    # ortalaniyor mu" sorusu, "yuvarlak delik mi" degil: havalandirmanin Ø5'ini
    # ve civatalarin Ø3.2'sini disarida birakiyordu. Yuvarlak = oval olmayan.
    delme_metni = " ".join(f"{a} {b}" for a, b in K.DELME).format(**delme_bicim())
    caplar = sorted({o["delik_mm"] for o in panel_ogeleri()
                     if o["delik_mm"] > 0 and o["tip"] != "yuva"})
    yontemsiz = [c for c in caplar
                 if not re.search(rf"Ø\s?{c:.0f}(?:[.,]\d)?\b", delme_metni)
                 and not re.search(rf"Ø\s?{c:g}\b", delme_metni)]
    D.kosul("Panelde kullanilan her yuvarlak cap DELME rehberinde geciyor",
            not yontemsiz, f"yontemsiz: {yontemsiz}" if yontemsiz
            else f"{len(caplar)} cap: " + " ".join(f"Ø{c:g}" for c in caplar))
    # ── B55l: panel deligi ile PARCANIN KENDI kaydi tutmali. Bu iddia bugun
    # gercek bir hatayi yakaladi: kullanici F0'in DISINI olctu (10-11 mm), ben
    # deligi Ø11 yaptim — oysa dis her zaman panel deliginden kucuk ve urunun
    # kaydi (FUS027, paket "panel Ø12mm") Ø12 istiyor. Ø11 acilsa yuva girmezdi
    # ve stokta tek parca var.
    # ⚠ Ilk yazdigim hali BOS KUMEDE DONUYORDU: stok.ad_ile() yalniz stok kodunu
    # ve kutuyu donduruyor, capi degil — hicbir eslesme bulunamiyordu ve iddia
    # "hepsi tuttu" diyordu. Artik envanter satirinin ad/paket alanlari okunuyor
    # ve karsilastirilan oge sayisi da AYRICA olculuyor (vacuous yesil olmasin).
    # ⚠ Ilk iki denemem de kusurluydu: birincisi BOS KUMEDE donuyordu (stok.ad_ile
    # yalniz kodu veriyor), ikincisi FAZLA GENISTI (jakin 4 mm muz capini ve
    # sigortanin 5x20 govdesini panel deligi saniyordu). Dogru olcut: kayitta
    # capin yaninda "panel" yaziyorsa o PANEL DELIGIDIR, baska hicbir sayi degil.
    stok_ = B.Stok()
    panel_cap = re.compile(r"panel[^,;]{0,12}?Ø?\s?(\d+(?:[.,]\d+)?)\s*mm", re.IGNORECASE)
    sapan, bakilan = [], []
    for o in panel_ogeleri():
        if not (o.get("parca") and o["delik_mm"] > 0 and stok_.var):
            continue
        ad, kat = o["parca"]
        for r in stok_.kayit:
            if not (r["ad"].strip().lower().startswith(ad.strip().lower()) and r["kategori"] == kat):
                continue
            for m in panel_cap.finditer(f"{r.get('ad', '')} {r.get('paket', '')}"):
                cap = float(m.group(1).replace(",", "."))
                bakilan.append(f"{o['ref']}/{r['id']}")
                if abs(cap - o["delik_mm"]) > 0.01:
                    sapan.append(f"{o['ref']}: veri Ø{o['delik_mm']:g} · kayit panel Ø{cap:g}")
    D.kosul("Panel deligi, parcanin STOK KAYDINDAKI panel capiyla tutuyor",
            not sapan, f"sapan: {sorted(set(sapan))}" if sapan
            else f"{sorted(set(bakilan))} — kayitta 'panel Ø' yazan oge(ler) tuttu")
    # B58e: tek oznesi F0'di (FUS027 "panel Ø12mm") ve panelden kalkti; bugun karsilastirilacak
    # panel parcasi yok. Bos donmesin diye olculen sey: ESLESTIRICI gercek envanterde calisiyor mu
    # (FUS027 kaydi hala orada) — desen bozulursa, ileride kaydinda panel capi olan bir parca
    # panele girdiginde iddia sessizce bos gecerdi.
    kayitta_cap = sorted({r["id"] for r in stok_.kayit
                          if panel_cap.search(f"{r.get('ad', '')} {r.get('paket', '')}")}) if stok_.var else []
    D.kosul("Panel capi eslestiricisi envanterde calisiyor (kayitta 'panel Ø' bulunuyor)",
            (not stok_.var) or bool(kayitta_cap),
            f"envanterde {kayitta_cap} · karsilastirilan panel parcasi {len(set(bakilan))}")
    # B55m: PLAKET (FR4) icin ayri bir yontem sart — ahsap rehberi burada
    # gecerli degil ve havya cam elyafi ERITMEZ, recineyi karbonlastirir
    # (karbon iletken -> kacak yolu bozulur). 6.1 karta Ø3.2 deldiriyor.
    plaket_delen = [s["no"] for s in aa
                    if "del" in _kucuk(" ".join(s.get("yap", [])))
                    and ("plaket" in _kucuk(" ".join(s.get("yap", [])))
                         or "kartın köşesinde" in " ".join(s.get("yap", [])))]
    fr4 = [b2 for a2, b2 in K.DELME if "plaket" in _kucuk(a2) or "fr4" in _kucuk(a2)]
    D.kosul("Delikli plaket (FR4) icin AYRI delme yontemi var ve havyayi yasakliyor",
            (not plaket_delen) or (len(fr4) == 1 and "havya" in _kucuk(fr4[0])
                                   and "kullanma" in _kucuk(fr4[0])),
            f"karta delen adim {plaket_delen} · FR4 satiri {len(fr4)}")
    en_buyuk = max(caplar)
    et = (K.CUBUK["genislik"] - en_buyuk) / 2
    D.kosul("En buyuk delik icin kalan et rehberde SAYIYLA yaziyor (en dar yer)",
            f"{et:.1f} mm" in delme_metni, f"Ø{en_buyuk:g} -> her yanda {et:.1f} mm")
    D.kosul("Delme rehberi matkapsiz yol veriyor (havya) ve oval yuva tarifi iceriyor",
            any("havya" in _kucuk(b) for _a, b in K.DELME) and any("oval" in _kucuk(a) for a, _b in K.DELME))
    D.kosul("Delik tablosunda her cap ya Ø ya oval olarak yaziliyor",
            all(d["cap"].startswith("Ø") or "oval" in d["cap"] for pnl in ("ön", "arka") for d in delik_tablosu(pnl)))
    # ── B55g: delik tablosu HAYALI delik uydurmasin ────────────────────────
    # Kok sebep: kutu.py'deki M3 satirlari ELLE yazilmisti ve "duvara asili
    # parcalar (yuva x2, MT3608 x2, TP4056 bloklari x2) Ø3.2 ikiser" diyordu —
    # veri (DUVAR_TUTUCU) MT/TP icin "montaj deligi yok, kablo bagi" diyor.
    # 8 hayali delik. B55c adim metinlerini duzeltmisti, bu tabloyu kacirmisti.
    civata_sahibi = {o["alt_etiket"] for o in K.PANEL_ARKA if o["tip"] == "civata"}
    yontem = {r: duvar_yontemi(r) for r in K.DUVAR_TUTUCU}
    D.kosul("Duvara civatali parca <=> PANEL_ARKA'da civata kaydi (ikisi de veriden)",
            all((y == "civata") == (r in civata_sahibi) for r, y in yontem.items()),
            f"civatali {sorted(civata_sahibi)} · kablo bagli {sorted(r for r, y in yontem.items() if y == 'kablo_bagi')}"
            f" · yapistirilan {sorted(r for r, y in yontem.items() if y == 'yapistir')}")
    # B57b: "EN AZ iki civata kaydi" iddiasi burada duruyordu; yuvalar yapistirilinca
    # CIVATALI DUVAR PARCASI KALMADI ve iddia bos kumede donerdi (tum([]) = dogru).
    # Yerine: yapistirilan parcanin civata ya da kablo bagi tutucusu OLMAMALI (tek yontem).
    ikili = sorted(r for r in K.YAPISTIRMA_ISTISNA if K.DUVAR_TUTUCU.get(r) or r in civata_sahibi)
    D.kosul("Yapistirilan duvar parcasinin ikinci bir tutturmasi yok (civata / kablo bagi)",
            not ikili, f"iki yontemli: {ikili}")
    eskimis_ist = sorted(r for r in K.YAPISTIRMA_ISTISNA
                         if r not in {d["ref"] for d in K.DUVAR_PARCA}
                         or K.YAPISTIRMA_ISTISNA[r]["yapistirici"] not in _kucuk(
                             next(d["nasil"] for d in K.DUVAR_PARCA if d["ref"] == r)))
    D.kosul("YAPISTIRMA_ISTISNA'da artik yapistirilmayan (eskimis) kayit yok",
            not eskimis_ist, f"eskimis: {eskimis_ist}")
    tablo_satiri = [r for r in kb["yapistirici"] if "18650" in r[0]]
    D.kosul("Istisnanin yapistiricisi yapistirici tablosunda KENDI satirinda tanimli",
            len(tablo_satiri) == 1 and all(_kucuk(v["yapistirici"]) in _kucuk(tablo_satiri[0][1])
                                           for v in K.YAPISTIRMA_ISTISNA.values()),
            tablo_satiri[0][1] if tablo_satiri else "18650 satiri yok")
    bag_adi = {p["ad"].split()[0] for p in K.DUVAR_PARCA
               if K.DUVAR_TUTUCU.get(p["ref"]) is not None}
    # Yalniz deligin ADI (1. sutun) taranir: HV* deliklerinin 'neden' metni de
    # TP4056'dan soz ediyor ama o bir gerekce, delik atfi degil.
    adlar = [s.split("</td>")[0] for s in delik_parca_html(B.Stok(), nl, parcalar).split("<tr")[1:] if "Ø" in s]
    kacak = sorted({ad for ad in bag_adi for s in adlar if ad in s})
    D.kosul("Delik tablosu kablo bagiyla tutulan parcaya delik ATFETMIYOR",
            not kacak, f"delik atfedilen: {kacak}" if kacak else f"{sorted(bag_adi)} temiz, {len(adlar)} delik satiri")
    # ── B55g: somun cebi metinleri SOMUN_CEP'ten (Ø6 / "3. kat" eskimisti) ──
    # Kaynak uclu: DELME (veri), adim metinleri (veri), VE delik tablosunun
    # URETTIGI html — B55e'nin iddiasi yalniz 6.1/13.1'e bakiyordu, eskiyen iki
    # metin de (DELME ve kutu.py'deki M3 satiri) o kapsamin disindaydi.
    cep_metin = " ".join([f"{a} {b}".format(**delme_bicim()) for a, b in K.DELME]
                         + [" ".join(s.get("yap", []) + s.get("kontrol", [])) for s in hepsi.values()]
                         + [delik_parca_html(B.Stok(), nl, parcalar)])
    # Iki yon: "somun ... Ø6" (eskimis DELME/tablo metni) ve "Ø6.5 somun cebi" /
    # "Ø6.5 cebinde" (bugunku). 'gomme M3 somun' gibi parca adlari tetiklemesin
    # diye ikinci kalip CEP kelimesini sart kosuyor.
    # Kalibin ILK hali bu mutasyonu KACIRDI ("Ø6 somun yuvasi" hicbir kalibina
    # uymuyordu): cep kelimesi Ø'nun ONUNDE de ARKASINDA da olabiliyor.
    cep_kaliplar = (re.compile(r"somun\s*(?:cebi|yuvası)[^.Ø]{0,25}Ø\s?(\d+(?:[.,]\d+)?)", re.IGNORECASE),
                    re.compile(r"Ø\s?(\d+(?:[.,]\d+)?)\s*(?:mm\s*)?(?:somun\s*)?(?:ceb(?:i|inde)|yuvas)",
                               re.IGNORECASE))
    cep_bulunan = [m.group(1) for k in cep_kaliplar for m in k.finditer(cep_metin)]
    yanlis_cap = sorted({c for c in cep_bulunan
                         if abs(float(c.replace(",", ".")) - K.SOMUN_CEP["cap"]) > 1e-9})
    D.kosul("Somun cebinden soz eden her metin SOMUN_CEP capini yaziyor",
            not yanlis_cap, f"veri Ø{K.SOMUN_CEP['cap']} · metinde "
                            + (f"SAPMA {yanlis_cap}" if yanlis_cap else f"{len(cep_bulunan)} yerde ayni"))
    yap_tab = {a[:12]: b for a, b, _c in kb["yapistirici"]}
    D.kosul("Yapistirici tablosu: ic kat japon, raylar sicak silikon, mastik KULLANMA",
            "Japon" in yap_tab.get("İç kat dikey", "") and "silikon" in _kucuk(yap_tab.get("Raylar (taba", ""))
            and yap_tab.get("Silikon mast", "") == "KULLANMA")
    m45 = _kucuk(" ".join(hepsi["4.5"]["yap"]))
    D.kosul("4.5 (ic kat) metni japon diyor, sicak silikonu yasakliyor", "japon" in m45 and "silikon kullanma" in m45)
    m22 = _kucuk(" ".join(hepsi["2.2"]["yap"]))
    D.kosul("2.2 (raylar) metni sicak silikon diyor", "sıcak silikon" in m22)
    # ── B55l: yukaridaki iki kosul bir KURAL degil, IKI ADIMLIK BEYAZ LISTE idi.
    # Yapistiricidan soz eden alt adimlarin geri kalani hic karsilastirilmiyordu ve
    # 6.6 ile tablonun celiskisi tam o bosluktan gecmisti. Artik butun alt adimlar
    # taraniyor: tabloda YASAK olan bir yapistirici hicbir adim metninde gecmemeli.
    # Liste TABLODAKILERDEN genis olmali: amac "tabloda olmayan bir yapistirici
    # kullanilmis mi" sorusunu sormak. Yalniz tablodakiler taransaydi kapali
    # dunya olurdu ve "epoksi" gibi bir uydurma hic gorunmezdi (mutasyon kacti).
    YAPISTIRICI = ("japon", "sıcak silikon", "silikon", "mastik", "maskeleme band",
                   "epoksi", "uhu", "poliüretan", "kontak yapıştırıcı", "sıvı çivi",
                   "tutkal", "ahşap tutkalı", "çift taraflı bant")
    yasak_satir = [r for r in kb["yapistirici"]
                   if "KULLANMA" in r[1] or "yapıştırıcı yok" in _kucuk(r[1])]
    D.kosul("Yapistirici tablosunda en az bir YASAK satiri var (kural bos kumede donmuyor)",
            len(yasak_satir) >= 2, f"{len(yasak_satir)} yasak satiri")
    # 'silikon mastik' hicbir adimda gecmemeli (tablo: KULLANMA)
    mastikli = sorted(s["no"] for s in aa
                      if "mastik" in _kucuk(" ".join(s.get("yap", []) + s.get("kontrol", []))))
    D.kosul("Hicbir alt adim 'mastik' kullandirmiyor (tablo KULLANMA diyor)",
            not mastikli, f"mastik gecen adim: {mastikli}" if mastikli
            else f"{len(aa)} alt adim tarandi")
    # Hicbir adim TABLODA OLMAYAN bir yapistirici uydurmasin. Esik yok: kume
    # karsilastirmasi. (Ilk yazdigim hali "en az 8 adim taraniyor" idi — esigi
    # gecsin diye secilmis bir sayiydi, bu oturumda elestirdigim kusurun aynisi.)
    tablo_yapistirici = {y for y in YAPISTIRICI
                         if any(y in _kucuk(r[1] + " " + r[2]) for r in kb["yapistirici"])}
    adimda = {y for s in aa for y in YAPISTIRICI
              if y in _kucuk(" ".join(s.get("yap", []) + s.get("kontrol", [])))}
    uydurma = sorted(adimda - tablo_yapistirici)
    D.kosul("Adim metinlerindeki her yapistirici tabloda TANIMLI (uydurma yok)",
            not uydurma, f"tabloda yok: {uydurma}" if uydurma
            else f"{sorted(adimda)} — hepsi tabloda")
    # Sogutucuya DEGEN yerlerde yapistirici yasak — 6.6'nin tabana yapistirmasi
    # bu yasagin disinda ve tablo artik bunu ACIKCA soyluyor.
    sogutucu_satir = next((r for r in kb["yapistirici"] if "Soğutucu" in r[0]), None)
    D.kosul("Sogutucu yasagi 'degen yerler' ile sinirli ve taban derzini ISTISNA tutuyor",
            sogutucu_satir is not None and "değen" in sogutucu_satir[0]
            and "TABANA" in sogutucu_satir[2],
            sogutucu_satir[0][:60] if sogutucu_satir else "satir yok")

    print("\n  6 · OLCUM DEGERLERI (netlist ve sabitlerden)")
    for ad, _ag, r in giris_direncleri(nl, parcalar):
        D.kosul(f"{ad} -> VREF direnci hesaplanabiliyor", r != float("inf") and r > 1e3,
                B._oku(r) if r != float("inf") else "sonsuz")
    D.kosul("Sont degeri kalibrasyon komutunda dogru",
            any(f"s{T.SONT_TAKILI}" in x[0] for x in K.KALIBRASYON), f"s{T.SONT_TAKILI}")
    D.kosul("Q1 akim siniri notu tasarim sabitiyle ayni", f"{T.PIL_AKIM_SOGUTUCUSUZ:.2f}" in V.KART_DISI_NOTU["Q1"])
    # ── B55g · CAL: panelin TEK korumasiz GPIO ucu (kullanici karari: 22K) ──
    # Tehdit: 25.5 mm otedeki PIL 1'de pil testinde PIL_GIRIS_AZAMI_V duruyor;
    # yanlis delige giren kablo CAL'e o gerilimi basar. Iki ayri yol, ikisi de
    # olculuyor. Rayin tek yuku R41 (1K, +3V3-GND) — netlistten okunuyor.
    r41 = _ohm(nl.deger["R41"])
    # B59: tehdit = CAL'in PANEL KOMSULARININ gercek menzili (eskiden sabit PIL 38 V'du).
    vtehdit, varti = cal_tehdit_gerilimi()
    rcal, vpil = T.CAL_SERI_R, vtehdit
    ray = varti * r41 / (r41 + rcal)         # kart KAPALI: bolucu, ray yukselir (yalniz ARTI)
    D.kosul("CAL'in komsulari tanimli ve HV aralarinda DEGIL (yanlis delik 614 V getirmez)",
            bool(cal_komsulari()) and all(q["ref"] != "J2.1" for q in cal_komsulari()),
            ", ".join(f"{q['etiket']} {jak_azami_gerilim(q['ref']):.0f} V" for q in cal_komsulari()))
    D.kosul("CAL'e komsu jak gerilimi kacarsa (kart kapali) +3V3 rayi mutlak siniri asmiyor",
            ray <= T.ESP_MUTLAK_PIN_UST,
            f"{ray:.2f} V <= {T.ESP_MUTLAK_PIN_UST} V · rayda GPIO10 + iki ADS VDD "
            f"({rcal / 1e3:.0f}K : R41 {r41 / 1e3:.0f}K bolucu)")
    # kart ACIK: ESD diyodu akitiyor. B59: SKOP'un EKSI ucu (−63.5 V) GND'ye kenetlenir, VDD'ye
    # degil -> kutuptan bagimsiz tutucu hesap |V| / R (eski (V − VDD) / R eksi kutbu kucuk sayiyordu).
    ienj = vpil / rcal
    D.kosul("CAL'e komsu jak gerilimi kacarsa (kart acik) GPIO enjeksiyon akimi hedefin altinda",
            ienj <= T.ESP_ENJEKSIYON_HEDEFI,
            f"{ienj * 1e3:.2f} mA <= {T.ESP_ENJEKSIYON_HEDEFI * 1e3:.0f} mA")
    D.kosul("CAL seri direnci arizada 1/4 W'i asmiyor", ienj ** 2 * rcal <= 0.25,
            f"{ienj ** 2 * rcal * 1e3:.0f} mW")
    # Bedel: seri direnc CAL sinyalinin de yolunda (skop girisi ~103K ile bolucu).
    # Esik KOD cinsinden ve TURETILMIS: kare dalganin seviyeleri ve kenari
    # okunabilsin diye skop adiminin en az CAL_ASGARI_KOD katini istiyoruz —
    # "gecsin diye" secilmis bir yuzde degil (B55d dersi).
    # ── B55g · hucre 2 kolunun sigortasi (kullanici karari 2026-09-23) ──────
    # Yapisal: hucre 2'nin ARTI ucu ile TP2.B+ arasinda bir sigorta dugumu
    # olmali. Koruma FET'i B-/OUT- arasinda oldugu icin hucre ucu kisasini
    # DW01A kesemez; o kolu YALNIZ sigorta korur.
    # B55k: kural artik HER IKI hucre icin. Once yalniz H2+ soruluyordu ve
    # hucre 1 kolu (ayni 42 A'lik yol) tamamen korumasizdi.
    kablo_ucu = {(a, b) for a, b, *_ in K.PIL_KABLOLAR}
    for huc, tp in (("H1+", "TP1.B+"), ("H2+", "TP1.B+")):     # B58: paralel, tek TP4056
        yol = [b for a, b, *_ in K.PIL_KABLOLAR if a == huc]
        D.kosul(f"{huc} once SIGORTAYA giriyor (TP4056'nin korumasi bu kolu kesemez)",
                any(u.startswith("F") for u in yol) and (huc, tp) not in kablo_ucu,
                f"{huc} -> {yol}")
    # B55k: olcut SARJ akimini da icermeli — sigorta TP4056'nin BAT ucunda, yani
    # sarj akiminin TAMAMI oradan geciyor. Ilk hali yalniz desarj kolunu
    # sayiyordu ve 500 mA seciyordu; o sigorta ILK SARJDA atardi.
    i_kol = pil_kol_akimi()
    i_en = max(i_kol, T.PIL_SARJ_AKIMI)
    D.kosul("Hucre kolu sigortasi SARJ ve desarj akiminin buyugunun 1.5 kati (bosuna atmaz)",
            T.PIL_KOL_SIGORTA >= 1.5 * i_en,
            f"{T.PIL_KOL_SIGORTA:.2f} A >= 1.5 x {i_en:.2f} A · sarj {T.PIL_SARJ_AKIMI:.2f} A "
            f"(Rprog {T.TP4056_RPROG / 1e3:.1f}k) · kol {i_kol * 1e3:.0f} mA")
    i_kisa = T.HUCRE_V_UST / T.HUCRE_IC_DIRENC
    # B55k: sarj sirasindaki ISIL kural. Kutu ici sicaklik artisi OLCULMEDI ve
    # modeli baskin belirsizlikle (h_ic +%39/-%33, ESP32 gucu 0.4-1.9 W) dolu;
    # o yuzden sayi iddia edilmiyor, KULLANIM'a kural + tezgah olcumu yazildi.
    # Iddia kuralin VARLIGINI ve tavanin sabitten geldigini olcuyor.
    sarj_satir = [s for s in K.KULLANIM if "ısıl kural" in s[0]]
    hucreli = any(d["ref"].startswith("YUVA") for d in K.DUVAR_PARCA)
    D.kosul("Hucre varsa KULLANIM'da sarj ISIL kurali var ve tavani sabitten yaziyor",
            (not hucreli) or (len(sarj_satir) == 1 and "{sarj_tavani}" in sarj_satir[0][2]
                              and "ölçüm yapma" in sarj_satir[0][2]),
            f"tavan {T.LIION_SARJ_TAVANI_C:.0f} °C · {len(sarj_satir)} satir")
    D.kosul("Sarj tavani desarj tavanindan DUSUK (Li-ion'un sarj penceresi dar)",
            T.LIION_SARJ_TAVANI_C < T.LIION_DESARJ_TAVANI_C,
            f"{T.LIION_SARJ_TAVANI_C:.0f} < {T.LIION_DESARJ_TAVANI_C:.0f} °C")
    D.kosul("Hucrenin kisa devre akimi sigorta anmasinin en az 5 kati (sigorta gercekten atar)",
            i_kisa >= 5 * T.PIL_KOL_SIGORTA,
            f"{i_kisa:.0f} A = anmanin {i_kisa / T.PIL_KOL_SIGORTA:.0f} kati "
            f"({T.HUCRE_V_UST} V / {T.HUCRE_IC_DIRENC} ohm)")
    zskop = T.SKOP_RUST + T.SKOP_RALT
    cal_genlik = T.VDD * zskop / (zskop + rcal)
    D.kosul(f"Korumanin bedeli okunabilirligi bozmuyor: CAL genligi >= {CAL_ASGARI_KOD} skop kodu",
            cal_genlik / T.SKOP_ADIM >= CAL_ASGARI_KOD,
            f"{cal_genlik:.2f} V = {cal_genlik / T.SKOP_ADIM:.0f} kod "
            f"(bolunmemis {T.VDD} V = {T.VDD / T.SKOP_ADIM:.0f} kod; skop girisi {zskop / 1e3:.0f}K)")
    mz, ke = menziller(), kalib_esikleri()
    D.kosul("Akim siniri sont isil sinirindan (ADC degil)", mz["i_maks"] == T.SONT_AKIM_ISIL[T.SONT_TAKILI],
            f"{mz['i_maks']:.2f} A")
    D.kosul("Takili sont 5 mOhm: surekli >= 9 A (kullanici >= 10 A istedi; 15 mOhm 3.4 A'di)",
            T.SONT_TAKILI == 0.005 and T.SONT_AKIM_ISIL[0.005] >= 9.0, f"{T.SONT_AKIM_ISIL[0.005]:.1f} A")
    D.kosul("Buyuk jak / kablo yolu takili sontun sinirini tasiyor (15 A jak, 1.5 mm2)", T.SONT_AKIM_ISIL[T.SONT_TAKILI] <= 15.0)
    # B53: isil sinir tel capindan (olculen Ø1 mm) — 2 W varsayimi (11.5 A) parcayi eritirdi
    D.kosul("15 mOhm Ø1 mm sontun surekli siniri 5 A'in ALTINDA (2 W varsayimi kalkti)",
            T.SONT_AKIM_ISIL[0.015] < 5.0, f"{T.SONT_AKIM_ISIL[0.015]:.2f} A (Ø{T.SONT_TEL_CAP_MM[0.015]} mm)")
    D.kosul("Isil model ureticinin 5 mOhm/9.5 A degerini geri veriyor (±%2)",
            abs(T.SONT_AKIM_ISIL[0.005] - T.SONT_REF[2]) / T.SONT_REF[2] < 0.02, f"{T.SONT_AKIM_ISIL[0.005]:.2f} A")
    D.kosul("Isil sinir yalniz tel capina bagli: I(15m)/I(5m) = (1/2)^1.5",
            abs(T.SONT_AKIM_ISIL[0.015] / T.SONT_AKIM_ISIL[0.005] - 0.5 ** 1.5) < 1e-6)
    D.kosul("Pil testi akim tavani takili sontun sinirini asmiyor (kullanim tablosu min alir)",
            min(T.PIL_AKIM_SOGUTUCUSUZ, mz["i_maks"]) <= T.SONT_AKIM_ISIL[T.SONT_TAKILI] + 1e-9, mz["pil_akim"])
    D.kosul("Kullanim tablosu sontun surekli sinirini ve 15 mOhm secenegini soyluyor",
            "{akim}" in K.KULLANIM[2][0] and "{akim_15m}" in K.KULLANIM[2][2] and "sürekli" in _kucuk(K.KULLANIM[2][2]))
    # Kazanc kalibrasyonu: firmware esigi tam skalanin %5'i = 1638 kod; 5 mOhm'da 2.56 A ister.
    # Kullanicinin kaynagi (12 V + 10 ohm = 1.2 A) yetmez -> kazanc 15 mOhm takiliyken (esik 0.85 A)
    # alinir, i_duzeltme sonttan bagimsiz (olc_akim3: ham -> ofset -> /sont_ohm x duzeltme), sonra 5 mOhm + s0.005.
    D.kosul("5 mOhm ile dogrudan kazanc kalibrasyonu 1.2 A'lik kaynakla YAPILAMAZ (esik > 1.2 A)", ke["i"] > 1.2, f"{ke['i']:.2f} A")
    D.kosul("15 mOhm ile kazanc kalibrasyonu 1.2 A'lik kaynakla yapilabilir", ke["i_15m"] < 1.2 < T.SONT_AKIM_ISIL[0.015], f"{ke['i_15m']:.2f} A")
    m122 = _kucuk(" ".join(hepsi["12.2"]["yap"]))
    D.kosul("12.2 iki asamali: kazanc 15 mOhm ile, sonra 5 mOhm + s0.005 + Z", "s0.015" in m122 and "s0.005" in m122 and "1.1" in m122)
    # B58: eski kural "kutuyu besleyen kaynak (WCT) test kaynagi olamaz"di — WCT
    # artik kutuya bagli degil. Yeni kural: kutunun KENDI paketi test kaynagi
    # olamaz (eksisi kart GND; donus akimi J5'in GND telinden gecer).
    D.kosul("12.2 kurali: kutunun kendi pil paketi test kaynagi olamaz; kaynak tezgah beslemesi",
            "kendi pil paketi olamaz" in m122 and "tezgah beslemesi" in m122 and "3.3 ω" in m122)
    test_i = T.TEST_KAYNAK_V / T.TEST_YUK_R
    D.kosul("Test kaynagi + yuk 15 mOhm kazanc esigini asiyor, 3.3 ohm'u gucunun yarisinda tutuyor",
            ke["i_15m"] < test_i and test_i ** 2 * T.TEST_YUK_R <= 11.0 * 0.5,
            f"{T.TEST_KAYNAK_V} V / {T.TEST_YUK_R} ohm = {test_i:.2f} A (esik {ke['i_15m']:.2f} A) · "
            f"{test_i ** 2 * T.TEST_YUK_R:.1f} W / 11 W")
    D.kosul("CAL panelde; 14.3 ve 12.5 CAL'i GPIO'dan degil jaktan aliyor",
            "CAL" in ref_oge
            and "gpio" not in _kucuk(" ".join(hepsi["14.3"]["yap"])) and "cal jakı" in _kucuk(" ".join(hepsi["12.5"]["yap"])))
    D.kosul("ESP32 yuksekligi disi dupont + tel bukumunu iceriyor (>= 26 mm; ciplak pin 14 degil)",
            esp["yuk"] >= 26.0, f"{esp['yuk']:.0f} mm")
    D.kosul("Kapak civatasi 5. sirada, rayin icinde (90 mm duvar)", h["ic_yuk"] == 90 and 72 < kb["kapak_civata_z"] < 90)
    D.kosul("HV kazanc esigi 24 V kaynagi asiyor -> 12.4 uyariyor",
            ke["g_yuksek"] > 24 and f"{ke['g_yuksek']:.0f} V" in " ".join(hepsi["12.4"]["yap"]), f"{ke['g_yuksek']:.1f} V")
    D.kosul("NORMAL kazanc esigi 12 V kaynakla saglaniyor", ke["g_normal"] < 12, f"{ke['g_normal']:.2f} V")

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
    # B55n (kullanici karari 2026-09-24): "takili olan hic atmadi, T'yi sonraki
    # plana alalim." Fizik iddiasi ayni kaliyor (315'e GECILMEZ), ama metnin
    # soylemesi gereken sey degisti: yuvadaki kalir, kurulum beklemez.
    D.kosul("Stoktaki hizli 315/400 mA da darbeye >= 3x pay vermiyor -> 315'e GECILMEZ",
            pay["F 315 mA"] < T.SIGORTA_DARBE_PAYI and pay["F 400 mA"] < T.SIGORTA_DARBE_PAYI
            and "değiştirmeye değmez" in _kucuk(" ".join(hepsi["10.4"]["yap"])),
            f"315: {pay['F 315 mA']:.1f}x · 400: {pay['F 400 mA']:.1f}x")
    D.kosul("10.4 takili sigortanin KALACAGINI ve T'nin ISTEGE BAGLI oldugunu soyluyor",
            "takılı sigorta kalıyor" in _kucuk(" ".join(hepsi["10.4"]["yap"]))
            and any(m["stok"] is None and "gecikmeli" in _kucuk(m["ad"])
                    and "isteğe bağlı" in _kucuk(m["ad"]) for m in K.MALZEME))
    D.kosul("Kullanicinin olctugu 0.4 ohm 50 mA'lik tel olamaz (>= 15 ohm)", T.SIGORTA["F 50 mA"][0] >= 15
            and abs(0.4 - T.SIGORTA["F 400 mA"][0]) < abs(0.4 - T.SIGORTA["F 50 mA"][0]),
            f"50 mA soguk {T.SIGORTA['F 50 mA'][0]:.1f} ohm · 400 mA {T.SIGORTA['F 400 mA'][0]:.3f} ohm")
    m101 = _kucuk(" ".join(hepsi["10.4"]["yap"]))
    D.kosul("10.4 metni T (gecikmeli) 50 mA diyor ve F'nin darbede attigini soyluyor",
            "gecikmeli" in m101 and "darbe" in m101 and "atar" in m101)
    # B55n: eskiden metin "yuvadaki FUS001'dir" DIYORDU. Kullanici "50 mA takili
    # ve hic atmadi" dedi; iki bilgi celisiyor ve hangisinin dogru oldugunu ancak
    # OLCUM soyler. Iddia artik metnin iddia degil YORDAM vermesini olcuyor:
    # iki direnc bandi da yazili olmali ve kullaniciya olcturmeli.
    # ⚠ Adimin TAMAMINDA "ohmmetre" aramak yetmiyor: eski 10.1'de KTS202'nin ortak
    #   ayagini bulma yordami da ohmmetre diyordu ve sigorta cumlesi etikete
    #   donse bile iddia yesil kaliyordu (mutasyon kacti). Olcut AYNI maddede.
    bic101 = adim_bicim(h, nl, parcalar)
    sig_madde = [_kucuk(y.format(**bic101)) for y in hepsi["10.4"]["yap"] if "sigorta" in _kucuk(y)]
    D.kosul("10.4 sigortayi etiketle degil OLCUMLE ayirt ettiriyor (iki direnc bandi ayni maddede)",
            any(f"{T.SIGORTA['F 50 mA'][0]:.0f}" in m and f"{T.SIGORTA['T 50 mA'][0]:.0f}" in m
                and f"{T.SIGORTA['F 400 mA'][0]:.1f}" in m
                and ("ohmmetre" in m or "direncini ölç" in m) for m in sig_madde),
            f"{len(sig_madde)} sigorta maddesi tarandi")
    D.kosul("Malzeme listesinde T 50 mA sigorta ALINACAK, F 50 mA STOKTAN",
            any(m["stok"] is None and "gecikmeli" in _kucuk(m["ad"]) for m in K.MALZEME)
            and any(m["stok"] and "50mA" in m["stok"][0] for m in K.MALZEME))
    # B58b: malzeme notlari tabloda KACISLI basiliyor (E()); "<b>...</b>" kullaniciya
    # cig etiket olarak gorunuyordu (kalin kablo satiri).
    etiketli = [m["ad"][:24] for m in K.MALZEME if re.search(r"</?[a-z]+>", m.get("not", ""))]
    D.kosul("Malzeme notlarinda HTML etiketi yok (tabloda kacisli basiliyor)", not etiketli, str(etiketli))

    print("\n  7 · STOK")
    stok = B.Stok()
    if stok.var:
        for o in oge:
            if o["parca"]:
                s2 = stok.ad_ile(*o["parca"])
                D.kosul(f"{o['ref']} envanterde", _stokta(s2), o["parca"][0][:40])
        for p in K.IC_PARCA:
            if p.get("stok"):
                D.kosul(f"{p['ref']} envanterde", _stokta(stok.ad_ile(*p["stok"])))
        for d in K.DUVAR_PARCA:
            if d.get("stok"):
                D.kosul(f"{d['ref']} envanterde", _stokta(stok.ad_ile(*d["stok"])), d["stok"][0][:30])
        for ad, kat in (("M3 Somun", "Mekanik"), ("M3 Pul", "Mekanik"), ("2 Pin Klemens 5.00mm", "Konnektör"),
                        ("1x40 Dişi Header 180°", "Konnektör")):
            D.kosul(f"'{ad}' envanterde", _stokta(stok.ad_ile(ad, kat)))
        stokta, alinacak = malzeme_ayir(stok)
        for m, _k in stokta:
            D.kosul(f"Stokta olan '{m['ad'][:30]}' alinacak listesinde DEGIL", 
                    # "\b" bir heredoc yamasinda GERCEK 0x08 olmustu (B39 ile ayni tuzak) — Write ile yazildi
                    not re.search(r"\b(al|alın|alınacak|satın al)\b", _kucuk(m["not"])))
        D.kosul("Malzeme listesindeki stok sorgulari envanterde karsilik buluyor",
                all(m["stok"] is None or _stokta(stok.ad_ile(*m["stok"])) for m in K.MALZEME),
                str([m["ad"] for m in K.MALZEME if m["stok"] and not _stokta(stok.ad_ile(*m["stok"]))]))
        # B58: yalitimli DC-DC stokta YOKTU — iddia "alinacak"ta kalmasini istiyordu (alim
        # gizlenmesin). 2026-09-28 GELDI (MOD013): iddia ters cevrildi — plan onu hala
        # "alinacak" sayarsa kullanici ikinci kez alir, 10.2'nin stok hucresi "stokta YOK" der.
        iz = next((d for d in K.DUVAR_PARCA if d["ref"] == "IZ"), None)
        D.kosul("B0505S stokta -> malzeme listesinde STOKTAN, duvar parcasi IZ envanter sorguluyor",
                iz is not None and bool(iz.get("stok")) and not iz.get("alinacak")
                and any("b0505s" in _kucuk(m["ad"]) for m, _k in stokta)
                and not any("b0505s" in _kucuk(m["ad"]) for m in alinacak)
                and any("b0505s" in _kucuk(r["ad"]) for r in stok.kayit))
        D.kosul("F 50 mA sigorta ve TO-220 yalitimi stoktan (alinacak degil)",
                {m["ad"] for m, _k in stokta} >= {"50 mA 5×20 cam sigorta (hızlı, F — stoktaki)",
                                                  "TO-220 yalıtım (mika/plastik izolatör + burç)"})
    else:
        # B55g: bu dal SESSIZ bir kusurdu. Envanter okunamayinca bu bolumun 43
        # iddiasi dusuyor, ama ozet yine "N/N dogrulama gecti" ve rc=0 diyordu —
        # yani 43 iddia eksik bir kosu, tam kosudan AYIRT EDILEMIYORDU. (Bu
        # oturumda kazara uretildi: `redirect_stdout` altinda bom_dogrula'nin
        # import'undaki sys.stdout.reconfigure patliyor, yerlesim3_belge.Stok
        # istisnayi yutuyor -> 1815 yerine 1772.) Envanter depo DISINDA oldugu
        # icin (herkese acik depo) bunu KIRMIZI yapmak yanlis olur; cozum:
        # atlandigini ozet satirina TASIMAK.
        global STOK_ATLANDI
        STOK_ATLANDI = True
        print("      (envanter okunamadi — bu bolumun iddialari ATLANDI)")

    print("\n  7b · SOMUN CEBI VE HAVALANDIRMA (B55e)")
    cep, som = K.SOMUN_CEP, K.M3_SOMUN
    D.kosul("Somun cebinin capi M3 somunun koseden koseye olcusunu geciyor",
            cep["cap"] >= som["kose"], f"cep {cep['cap']} >= somun {som['kose']} mm")
    D.kosul("Somun cebi somunu TAM gomuyor (lamine duz kalir)",
            cep["kat"] * olcu()["t"] >= som["kalinlik"], f"{cep['kat'] * olcu()['t']:.0f} >= {som['kalinlik']} mm")
    D.kosul("Cep yuvarlak: donmeyi yapistirici engelliyor, disine degil DIS yuzune",
            "japon" in cep["yapistirici"] and "diş" in cep["yapistirici"])
    ayak_kat = next(p["tasiyici"]["kat"] for p in K.IC_PARCA if p.get("tasiyici", {}).get("tip") == "ayak")
    for ad2, kat in (("kapak blogu", kb["kapak_somun_kat"]), ("ayak blogu", ayak_kat)):
        D.kosul(f"{ad2} kat sayisi cebi ve vida ucunu karsiliyor (1 + {cep['kat']} + 1)",
                kat >= 2 + cep["kat"], f"{kat} kat")
    D.kosul("Vida ucu icin son kat DELIKLI (tahtaya dayanmiyor)", cep["son_kat_delik"] >= 3.2)
    D.kosul("M3 gecme deligi ile somun cebinin son kat deligi ayni cap (vida gecebilsin)",
            abs(m3_gecme_cap() - cep["son_kat_delik"]) < 1e-9,
            f"panel civata Ø{m3_gecme_cap()} · cep son kat Ø{cep['son_kat_delik']}")
    # ── B55g: civatanin YOLUNDAKI her ahsap katmani delen bir talimat olmali ──
    # 13.1 fiziksel olarak YAPILAMIYORDU: 4.7 yalniz duvari deliyor, civatanin
    # onunde 2 mm'lik kapak rayi duruyor ve onu delen adim yoktu. Iddia metne
    # degil GEOMETRIYE bakiyor: civata ekseni rayin govdesini kesiyor mu?
    kesilen = sorted({r["ref"] for r in kapak_raylari() for y in kb["kapak_civata_y"]
                      if r["y"] - 1e-6 <= y <= r["y"] + r["boy"] + 1e-6
                      and r["z"] - 1e-6 <= kb["kapak_civata_z"] <= r["z"] + r["yuk"] + 1e-6})
    gereken = {"duvar"} | ({"ray"} if kesilen else set())     # geometriden
    planli = set(kb["kapak_civata_delen"])                    # plandan
    D.kosul("Kapak civatasinin gectigi her ahsap katmani DELEN bir alt adim var",
            gereken == planli,
            f"geometri {sorted(gereken)} (kesilen ray: {kesilen}) · plan {sorted(planli)}")
    # ── B55l: BUGUN alinan kararlarin kullanicinin okudugu ADIMLARA girmesi.
    # Tarama en agir kusuru boyle buldu: kart A'yi 115x115'e kesme karari
    # veriye ve DEVIR'e yazilmisti ama HICBIR ADIMDA yoktu — kullanici kesmeden
    # 6.1'e gelirdi ve kart kutuya sigmazdi.
    kart_a = next(q for q in K.IC_PARCA if q["ref"] == "A")
    kesim_adim = [s["no"] for s in aa
                  if "{kart_a_en" in " ".join(s.get("yap", [])) and s["tur"] == "kesim"]
    D.kosul("Kart A'yi plandaki olcuye getiren bir KESIM adimi var",
            bool(kesim_adim), f"{kesim_adim} -> {kart_a['en']:.0f} x {kart_a['boy']:.0f} mm")
    kart_takan = next((s["no"] for s in aa if "A" in (s.get("vurgu") or []) and s["tur"] == "montaj"), None)
    D.kosul("Kesim adimi, kartin kutuya takildigi adimdan ONCE",
            bool(kesim_adim) and kart_takan is not None
            and max(sira_aa[n] for n in kesim_adim) < sira_aa[kart_takan],
            f"{kesim_adim} -> montaj {kart_takan}")
    # Ilk kesim listesi elde olandan cok cubuk istiyorsa adim BUNU SOYLEMELI,
    # yoksa kullanici kesmeye baslar ve yarida kalir.
    k1 = sum(r["adet"] for r in h["kesim1"])
    m12_ham = " ".join(hepsi["1.2"]["yap"])
    D.kosul("Ilk kesim listesi elde olandan cok cubuk istiyorsa adim bunu SOYLUYOR",
            k1 <= kb["elde_cubuk"] or "{kesim1_cubuk" in m12_ham,
            f"kesim1 {k1} cubuk · elde {kb['elde_cubuk']} · eksik {max(0, k1 - kb['elde_cubuk'])}")
    # ── B55m: hicbir ADIM, stokta olmayan bir parcayi SART kosmasin. Kullanici
    # artik soru sormayacak ve alisverisini malzeme listesinden yapiyor; "halka
    # pabuc" uc adimda kosulsuz isteniyordu ve envanterde HIC YOK (Konnektor alani
    # CLAUDE.md'ye gore tam, yani gercekten yok). Alternatif yalnizca malzeme
    # listesinin not sutunundaydi, kullanici adimi okurken orayi gormuyor.
    yok_olan = []
    if stok_.var:
        for ad in ("halka pabuç", "1n5819"):     # B58b: 1N5819 stokta yok, SR5100 var
            bulunan = [r for r in stok_.kayit if ad in _kucuk(r["ad"])]
            gecen = [s["no"] for s in aa
                     if ad in _kucuk(" ".join(s.get("yap", []) + s.get("kontrol", [])))
                     and "stokta yok" not in _kucuk(" ".join(s.get("yap", [])))]
            if not bulunan and gecen:
                yok_olan.append(f"{ad} -> {gecen}")
    D.kosul("Hicbir adim stokta OLMAYAN bir parcayi kosulsuz istemiyor",
            not yok_olan, f"sart kosan: {yok_olan}" if yok_olan
            else "halka pabuc gecen adimlar alternatifi de yaziyor")
    # ── B55m: PIL_KABLOLAR'da gecen her FIZIKSEL parcanin kutuda bir yeri olmali.
    # B55k'da eklenen F1P/F2 sigorta yuvalari kablo listesinde, PIL_IC_BAG'da ve
    # iki adim metninde vardi ama hicbir geometrik listede degildi: konum yok,
    # cakisma denetimi gormuyor, kutle yok, kesim listesinde altligi yok.
    yerli = ({d["ref"] for d in K.DUVAR_PARCA} | {q["ref"] for q in K.IC_PARCA}
             | {o["ref"] for o in panel_ogeleri()} | {e["ref"] for e in kutu_ek_parcalari()})
    pil_ucu = {u.split(".")[0] for a, b, *_ in K.PIL_KABLOLAR for u in (a, b)}
    # H1/H2 hucrenin kendisi (yuvada), TP/MT/SWP/KL zaten listede, ESP32 ic parca
    yersiz = sorted(u for u in pil_ucu
                    if u.startswith("F") and u not in yerli)
    D.kosul("Pil kolundaki her SIGORTA yuvasinin kutuda gercek bir yeri var",
            not yersiz, f"yersiz: {yersiz}" if yersiz
            else f"{sorted(u for u in pil_ucu if u.startswith('F'))} yerlestirildi")

    # ══ B55n · TAMAMLANABILIRLIK ═══════════════════════════════════════════
    # Kullanici (2026-09-24): "artik devam edip son haline kadar sana birsey
    # sormadan devam edebilmem lazim." Asagidaki iddialar bu kurali olcuyor:
    # bir adim ya kendi kendine yeter ya da kirmizidir.
    bic = adim_bicim(h, nl, parcalar)

    def _metin(s: dict) -> str:
        ham = " ".join(s.get("yap", []) + s.get("kontrol", []))
        return re.sub(r"\s*/\s*", "/",      # "PIL / HARICI" ile "PIL/HARICI" ayni sey
                      _kucuk(ham.format(**{**bic, "bu_etiketler": adim_etiketleri(s)})))

    # 1) Hicbir adim kullaniciyi BANA yollamasin. 9.3 "600 V altiysa soyle"
    #    diyordu: kullanici o noktada takilir ve plan orada biter.
    # ⚠ Desenler TURKCE yazilmali: _kucuk() harfleri sadelestirmiyor, yalnizca
    # kucultuyor. Ilk surumde "soyle" yaziyordu ve HICBIR SEY eslesmiyordu —
    # iddia bos dogmustu, mutasyon kosucusu yakaladi (B55n).
    SORAN = (r"\bsöyle\b", r"\bbana (sor|söyle|yaz|bildir)", r"\bsorarsın\b",
             r"\bbana danış", r"\bbenimle\b")
    # Yalniz ADIMLAR degil: kural/malzeme metinleri de kullaniciya bakiyor ve
    # ilk surumde KULLANIM'daki "sayiyi bana soyle" taramanin disinda kalmisti.
    kullanici_metni = [(s["no"], _metin(s)) for s in aa]
    kullanici_metni += [(f"KULLANIM:{k[0]}", _kucuk(" ".join(str(x) for x in k[1:])))
                        for k in K.KULLANIM]
    kullanici_metni += [(f"MALZEME:{m['ad'][:18]}", _kucuk(m.get("not", ""))) for m in K.MALZEME]
    kullanici_metni += [(f"KUTU_NOTU:{r}", _kucuk(n)) for r, n in K.KUTU_NOTU.items()]
    soran = sorted({n for n, m in kullanici_metni for p in SORAN if re.search(p, m)})
    D.kosul("Hicbir kullanici metni karari bana birakmiyor (kullanici artik soru soramiyor)",
            not soran, f"bana yollayan: {soran}" if soran
            else f"{len(kullanici_metni)} metin tarandi")

    # 2) 'monte' listesindeki her parca o adimin METNINDE de gecsin. LED1 uc
    #    haftadir 5.3'un monte listesindeydi ama takilisini anlatan tek cumle
    #    yoktu: kullanici deligi acar, LED'i eline alir ve orada kalir.
    etiket_ile: dict[str, set[str]] = {}
    for o in panel_ogeleri():
        etiket_ile.setdefault(o["ref"].split(".")[0], set()).add(o.get("etiket", ""))
    # ⚠ Takma ad YALNIZ IC_PARCA icin: ref'leri tek harf olabiliyor ("A", "B").
    # DUVAR_PARCA'nin ref'leri zaten ayirt edici (TP1, MT2, F0B) ve adlarindan
    # turetilen sozcuk cok genel cikiyor — F0B'ninki "xt30" oluyordu ve 10.1'in
    # her yerinde geciyor, yani iddia F0B icin BOS kaliyordu (B55n).
    for q in K.IC_PARCA:
        # adin ILK dort harfli sozcugu ("5 mΩ Ø2 şönt ..." -> "şönt")
        ilk = next((w for w in re.findall(r"[0-9a-zçğıöşü]{4,}", _kucuk(q.get("ad", "")))), "")
        if ilk:
            etiket_ile.setdefault(q["ref"], set()).add(ilk)
    for r, es in list(etiket_ile.items()):          # "HV ⚡" -> "hv" (simge yok)
        es |= {re.sub(r"[^0-9a-zçğıöşü ]+", " ", _kucuk(e)).strip() for e in es if e}
    # ⚠ Olcut "adi geciyor mu" DEGIL, "takma TALIMATI var mi": uretilen etiket
    #   listesi ({bu_etiketler}) her ogeyi zaten sayiyor ve LED1'in montaj
    #   cumlesi silinse bile iddiayi yesil tutuyordu (B56, mutasyon kacti).
    #   Sozcuk listesi TUTTURMA yontemlerinden: adim o parcanin nasil
    #   sabitlendigini soylemek zorunda (Turkce'de fiil dusebiliyor —
    #   "YUVA1 alt siraya ... civatali" da bir talimattir).
    EYLEM = re.compile(r"tak|vidal|cıvata|somun|kablo bağ|yapıştır|lehim|sık|geçir|otur|"
                       r"tuttur|silikon|japon|monte")
    anlatilmayan = []
    for s in aa:
        for r in s.get("monte", []):
            adaylar = {re.sub(r"\s*/\s*", "/", _kucuk(e)) for e in etiket_ile.get(r, set()) if e}
            ref_kalip = r"(?<![0-9a-zçğıöşü])" + re.escape(_kucuk(r)) + r"(?![0-9a-zçğıöşü])"
            talimat = False
            for y in s.get("yap", []):
                # uretilen etiket listesi bu olcutte SAYILMAZ
                m = re.sub(r"\s*/\s*", "/", _kucuk(y.format(**{**bic, "bu_etiketler": ""})))
                if not EYLEM.search(m):
                    continue
                if re.search(ref_kalip, m) or any(a and a in m for a in adaylar):
                    talimat = True
                    break
            if not talimat:
                anlatilmayan.append(f"{s['no']}:{r}")
    D.kosul("Adimin 'monte' ettigi her parca icin bir TAKMA TALIMATI var (ad + eylem)",
            not anlatilmayan, f"talimatsiz: {anlatilmayan}" if anlatilmayan
            else f"{sum(len(s.get('monte', [])) for s in aa)} montaj kalemi")

    # 3) Taban raylarinin KONUMU metne girsin — kutu fiilen o iki rayin
    #    uzerinde duruyor ve devrilme/yuk payi hesabi konumu varsayiyor,
    #    ama metin yalnizca "uclardan iceride" diyordu.
    ray_m = [h["dis_en"] * r for r in TABAN_RAY_X]
    ray_adim = next((s for s in aa if s["tur"] == "taban" and "ray" in _metin(s)
                     and sira_aa[s["no"]] < sira_aa.get("3.1", 99)), None)
    ray_sayi = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*mm", _metin(ray_adim or {}))]
    D.kosul("Taban rayi adimi rayin KONUMUNU mm olarak yaziyor",
            ray_adim is not None and all(any(abs(x - m) <= 0.6 for x in ray_sayi) for m in ray_m),
            f"{ray_adim['no'] if ray_adim else '—'}: bekleniyor {[round(m) for m in ray_m]} · metinde {ray_sayi}")

    # 4) Kablo bagiyla tutulan her modulun deligi bir CAP soylemeli, ve cap
    #    bandin serit genisligini gecmeli (gecmezse serit girmez).
    kbg = K.KABLO_BAGI
    D.kosul("Kablo bagi deligi seridi geciriyor ama cubugu zayiflatmiyor",
            kbg["genislik"] < kbg["delik"] < K.CUBUK["genislik"] / 2,
            f"serit {kbg['genislik']} < delik {kbg['delik']} < cubuk/2 {K.CUBUK['genislik'] / 2}")
    bagli = [s for s in aa if "kablo bağıyla" in _metin(s) and s["tur"] == "duvar_parca"]
    # B58d: kanalli tutucu (TP1) delik degil kanal kullaniyor; olcusu kendi iddiasinda.
    capsiz = [s["no"] for s in bagli if f"ø{kbg['delik']:.1f}" not in _metin(s)
              and not re.search(r"\d+ mm kanal", _metin(s))]
    D.kosul("Kablo bagiyla modul tutan her adim delik capini yaziyor",
            bagli and not capsiz, f"capsiz: {capsiz}" if capsiz else f"{[s['no'] for s in bagli]}")

    # 5) 8.1: sont kutbuna kac iletken biniyor? KABLOLAR'dan sayiliyor. Ikiden
    #    fazlaysa (sont bacagi + 2 kalin kablo) adim AYRI bir dugum parcasi
    #    gostermek zorunda — XP128'in kafesine Ø2 manganin + damarli kablo
    #    birlikte girmez, cubuk basinci alir ve kablo gevser.
    rs_yuk = {}
    for a_, b_, tur_, *_ in V.KABLOLAR:
        if tur_ != "yuk":
            continue
        for u in (a_, b_):
            if u.startswith("X:RS."):
                rs_yuk[u] = rs_yuk.get(u, 0) + 1
    kalabalik = sorted(u for u, n in rs_yuk.items() if n > 1)
    # RS'e KALIN kablo indiren her adim (kelvin/yildiz adimlari haric)
    inen = [s for s in aa if any(V.KABLOLAR[i][2] == "yuk" and "X:RS." in str(V.KABLOLAR[i][:2])
                                 for i in s.get("kablo", []))]
    # B62: yalniz "bariyer" sozcugu yetmiyordu — 7.1'e "Bariyer tarafinda: teli soy..." cumlesi
    # girince, kablolari sont vidasina geri gonderen mutasyon KACTI. Olculen artik yonlendirme:
    # adim kablolari "bariyer kutup 1/2"ye goturuyor mu.
    dugumsuz = [s["no"] for s in inen
                if not re.search(r"bariyer\s+kutup\s+[12]", re.sub(r"<[^>]+>", "", _metin(s)))]
    dugum_malzeme = any("bariyer" in _kucuk(m["ad"]) for m in K.MALZEME)
    D.kosul("Sont kutbuna 1'den fazla kalin kablo biniyorsa o adimlar ayri bir DUGUM parcasi kuruyor",
            not kalabalik or (inen and not dugumsuz and dugum_malzeme),
            f"{ {u: n for u, n in sorted(rs_yuk.items())} } · dugumsuz {dugumsuz} "
            f"· inen {[s['no'] for s in inen]} · malzemede {dugum_malzeme}")

    # 6) Stokta yedegi olmayan cok kutuplu anahtarin ortak ayagi OLCEREK
    #    bulunmali: yanlis lehim = parca yanar ve yedek yok.
    # Yalniz LEHIMLEYEN adim: 5.3 anahtari yalnizca panele takiyor, ayak secmiyor.
    # B58: KTS202 (cift kutup, ortak ayagi olcerek bulunmasi gerekiyordu) artik
    #   kullanilmiyor — iki anahtar da KTS102. Yerine: panelde kullanilan her
    #   anahtar tipinin adedi stoktakini asmasin (KTS102: 2 var, 2 kullaniliyor).
    tip_say: dict[tuple, int] = {}
    jak_say: dict[tuple, int] = {}
    for o in panel_ogeleri():
        if o["tip"] == "anahtar" and o.get("parca") and "toggle" in _kucuk(o["parca"][0]):
            tip_say[o["parca"]] = tip_say.get(o["parca"], 0) + 1
        if o["tip"] == "jak" and o.get("parca"):          # B60: alim yok -> her renk stoktan
            jak_say[o["parca"]] = jak_say.get(o["parca"], 0) + 1
    if stok_.var:
        def _adet(p):
            return sum(int((r.get("adet") or "0").strip() or 0) for r in stok_.kayit
                       if r["ad"].startswith(p[0]) and r.get("kategori") == p[1])
        asan = {p[0]: (n, _adet(p)) for p, n in tip_say.items() if n > _adet(p)}
        jak_asan = {p[0]: (n, _adet(p)) for p, n in jak_say.items() if n > _adet(p)}
        D.kosul("Paneldeki her jak renginin adedi stoktakini asmiyor (B60: alim yok)",
                not jak_asan, f"asan: {jak_asan}" if jak_asan
                else " · ".join(f"{p[0].split('Şeffaf ')[-1].split(' (')[0]} {n}/{_adet(p)}" for p, n in jak_say.items()))
        D.kosul("Paneldeki her toggle tipinin adedi stoktakini asmiyor",
                bool(tip_say) and not asan,
                f"asan: {asan}" if asan else str({p[0][:6]: (n, _adet(p)) for p, n in tip_say.items()}))

    # 7) 13.1: somunlu blok RAYIN IC YUZUNE yapisiyor, yani kutunun icine.
    #    Kapak takiliyken oraya el girmez (kutunun tek acikligi kapagin
    #    kendisi). Metinde "kapagi kaldir" yapistirma cumlesinden ONCE gelmeli.
    m131 = _metin(hepsi["13.1"])
    # ⚠ "kapağı kaldırMADAN yap" (delme cumlesi) tam tersini soyluyor ve duz
    # find() onu kabul ediyordu — iddia bos dogmustu (B55n).
    kal = re.search(r"kapağı kaldır(?!ma)", m131)
    i_kaldir, i_yapis = (kal.start() if kal else -1), m131.find("rayın iç yüzüne")
    D.kosul("Kapak blogu kapak TEZGAHTAYKEN yapistiriliyor (kapali kutuya el girmez)",
            i_kaldir >= 0 and i_yapis > i_kaldir, f"kaldir@{i_kaldir} < yapistir@{i_yapis}")

    # 8) Her KAPI adimi SAYISAL bir olcut tasisin. 11.2'nin metni yalnizca
    #    WiFi ayariydi: basligindaki iki kapinin olcutu hicbir yerde yoktu.
    # ⚠ Cihaz adresi (0x48) olcut DEGIL: "var mi yok mu" der, "ne kadar" demez.
    # Ilk surumde 0x.. de sayiliyordu ve gerilim olcutu silinse bile iddia yesil
    # kaliyordu (mutasyon kacti, B55n). Olcut = sayi + FIZIKSEL birim.
    # ⚠ B58e: "<b>Enerji:</b>" satiri KAPI olcutu DEGIL (hangi anahtar acik, USB
    # takilir mi der). 11.2'ye "MT1 5.0 V / USB 4.7 V / 0.35 A" eklenince iki
    # kapinin olcutu silinse bile iddia yesil kaliyordu (mutasyon kacti).
    OLCUT = r"(\d[\d.,]*\s*(mv|ma|ω|v|a)\b)|(%\s*\d)"

    def _kapi_metni(s: dict) -> str:
        return _metin({**s, "yap": [y for y in s.get("yap", [])
                                    if not y.startswith("<b>Enerji:</b>")]})
    kapisiz = [s["no"] for s in aa if s.get("kapi") and not re.search(OLCUT, _kapi_metni(s))]
    D.kosul("Her KAPI adimi kendi metninde sayisal bir olcut veriyor",
            not kapisiz, f"olcutsuz: {kapisiz}" if kapisiz
            else f"{[s['no'] for s in aa if s.get('kapi')]}")

    # 9) Ayak blogu: cep lamine olduktan SONRA acilamaz (icte kaliyor), ve
    #    elle isaretlenen dort delik tutmaz. Metin kilavuz delmeyi cebi
    #    buyutmeden ONCE anlatmali; sira tersine cevrilirse blok yapilamaz.
    m61 = _metin(hepsi["6.1"])
    i_kil = m61.find("tek seferde")
    i_buy = m61.find(f"ø{K.SOMUN_CEP['cap']:.1f}'e büyüt")
    D.kosul("Ayak blogunda kilavuz delik, cebi buyutmeden ONCE anlatiliyor",
            0 <= i_kil < i_buy, f"kilavuz@{i_kil} < buyut@{i_buy}")

    # 10) 16.1'in etiket listesi ELLE yazilmisti ve panelden kaymisti: CAL,
    #     F0, GUC, SARJ 1/2 ve uc toggle listede hic yoktu.
    m161 = _metin(hepsi["14.1"])
    eksik_etiket = sorted({o["etiket"] for o in panel_ogeleri()
                           if o["tip"] not in ("civata", "havalandirma") and o.get("etiket")
                           and re.sub(r"\s*/\s*", "/", _kucuk(o["etiket"])) not in m161})
    # ── B56 · PANEL SIMETRISI (kullanici istegi 2026-09-24) ───────────────
    # "on ve arka yuzun cok daha duzgun gozukmesini istiyorum, su anda cok
    # asimetrik ve hos degil."  Simetri artik TASARIM HEDEFI, yani olculuyor:
    # yoksa bir sonraki kucuk degisiklik sessizce geri bozar.
    orta = K.KUTU["ic_en"] / 2
    tol = K.PANEL_SIMETRI_TOLERANS
    essiz, gereksiz_haric = [], []
    for o in panel_ogeleri("arka"):         # B59: simetri YALNIZ arka panelde
        es = [q for q in panel_ogeleri(o["panel"])
              if abs((o["x"] + q["x"]) / 2 - orta) <= tol and abs(o["z"] - q["z"]) <= 1.0]
        if not es:
            (gereksiz_haric if False else essiz).append(o["ref"])
        elif o["ref"] in K.PANEL_SIMETRI_HARIC:
            gereksiz_haric.append(o["ref"])
    # B59: simetri yalniz arka panelde; istisna listesinde arka panelde OLMAYAN bir ref
    # (ör. on paneldeki CAL) anlamsiz — o da eskimis kayit sayilir.
    arka_ref = {o["ref"] for o in panel_ogeleri("arka")}
    gereksiz_haric += [r for r in K.PANEL_SIMETRI_HARIC if r not in arka_ref]
    kayip_gerekce = sorted(set(essiz) - set(K.PANEL_SIMETRI_HARIC))
    D.kosul("Her ARKA panel deligi x ortasina gore AYNA esine sahip (ya da gerekcesi yazili)",
            not kayip_gerekce, f"essiz ve gerekcesiz: {kayip_gerekce}" if kayip_gerekce
            else f"{len(panel_ogeleri('arka')) - len(essiz)} oge simetrik, {len(essiz)} gerekceli istisna")
    D.kosul("PANEL_SIMETRI_HARIC'te artik simetrik olan (eskimis) kayit yok",
            not gereksiz_haric, f"eskimis: {sorted(set(gereksiz_haric))}")
    D.kosul("Her simetri istisnasinin gerekcesi en az "
            f"{K.DAR_ACIKLIK_GEREKCE_EN_AZ} karakter",
            all(len(v) >= K.DAR_ACIKLIK_GEREKCE_EN_AZ for v in K.PANEL_SIMETRI_HARIC.values()))
    # ── B59 · ON PANEL: simetrik DEGIL, toplu ve duzenli (kullanici 2026-09-26) ──
    # "Duzenli" olculebilir: her oge ayni izgaranin bir dugumunde. "Toplu" islevden:
    # olcum probu COM'un yaninda, CAL HV'nin komsusu degil ama SKOP'un komsusu.
    izgarada = [o["ref"] for o in K.PANEL_ON
                if not (any(abs(o["x"] - x) < 0.01 for x in K.ON_IZGARA_X)
                        and any(abs(o["z"] - z) < 0.01 for z in K.ON_IZGARA_Z))]
    D.kosul("On panelin her ogesi ayni izgarada (x 35+36k, z 9/45/81) — duzenli",
            not izgarada, f"izgara disi: {izgarada}" if izgarada else f"{len(K.PANEL_ON)} oge izgarada")
    on = {o["ref"]: o for o in K.PANEL_ON}

    def _m(a, b):
        return math.dist((on[a]["x"], on[a]["z"]), (on[b]["x"], on[b]["z"]))
    uzak = {r: _m("J1.2", r) for r in ("J1.1", "J2.1", "J4.1")}
    D.kosul("COM olcum jaklarinin (V, HV, SKOP) yaninda: en uzagi <= 2 izgara adimi",
            max(uzak.values()) <= 2 * 36.0 * math.sqrt(2) + 0.01,
            " · ".join(f"{on[r]['etiket']} {v:.0f} mm" for r, v in uzak.items()))
    D.kosul("CAL SKOP'un komsusu (CAL -> SKOP patch kablosu kisa)", _m("CAL", "J4.1") <= 36.0 + 0.01,
            f"{_m('CAL', 'J4.1'):.0f} mm")
    D.kosul("CAL HV'nin komsusu DEGIL (> CAL_KOMSU_R)", _m("CAL", "J2.1") > K.CAL_KOMSU_R,
            f"{_m('CAL', 'J2.1'):.0f} mm > {K.CAL_KOMSU_R:.0f}")

    # 11c) B58: 6.5 "kart GND'ye (klemensin siyah ucu ya da A:T_YILDIZ)" diyordu —
    #      B50'den beri YANLIS: 24 V klemensinin siyah ucu C36 = -12 RAYI. Klemensin
    #      eksi ucunu GND diye anan hicbir talimat kalmasin.
    kl_gnd = sorted({s["no"] for s in aa for y in s.get("yap", []) + s.get("kontrol", [])
                     if re.search(r"gnd[^.;]{0,20}\(\s*(24 v )?klemensin (siyah|eksi)", _kucuk(y))})
    D.kosul("Hicbir talimat 24 V klemensinin eksi ucunu kart GND diye anmiyor (o -12 rayi)",
            not kl_gnd, f"GND diyen: {kl_gnd}" if kl_gnd else "klemens − her yerde −12")

    # 11b) B55n (kullanici karari): Q1'in sogutucusu mika yuzunden kutuda YUZEN
    #      bir metal plaka. GND'ye DUZ TELLE baglanirsa mika delindiginde PIL 1
    #      (test edilen pil, o yolda BIZIM koydugumuz sigorta yok) sogutucu
    #      uzerinden GND'ye kisa devre olur. Direncle baglanacak ve ariza akimi
    #      zararsiz kalacak — ikisi de olculuyor.
    ariza_ma = T.PIL_GIRIS_AZAMI_V / T.SOGUTUCU_BOSALTMA_R * 1e3
    D.kosul("Sogutucu bosaltma direnci ariza akimini zararsiz tutuyor (< 1 mA)",
            ariza_ma < 1.0, f"{T.PIL_GIRIS_AZAMI_V:.1f} V / {T.SOGUTUCU_BOSALTMA_R / 1e6:.1f} MΩ "
                            f"= {ariza_ma * 1e3:.0f} µA")
    # ⚠ Adimin TAMAMINDA aramak yetmiyor: gerekce paragrafi da direnci aniyor ve
    #   talimat "kalin tel" dese bile iddia yesil kaliyordu (mutasyon kacti).
    #   Olcut TALIMAT CUMLESINDE: "soğutucuyu … {R} … bağla" aynı cumlede.
    r_yazi = f"{T.SOGUTUCU_BOSALTMA_R / 1e6:.0f} mω"
    desen = re.compile(r"soğutucuyu.{0,60}?" + re.escape(r_yazi) + r".{0,60}?bağla", re.S)
    sog = [s for s in aa if "soğutucu" in _metin(s) and "gnd" in _metin(s)]
    sog_direncli = [s["no"] for s in sog
                    if any(desen.search(_kucuk(y.format(**bic))) for y in s.get("yap", []))]
    D.kosul("Sogutucuyu GND'ye baglayan TALIMAT direnc kullaniyor (duz tel degil)",
            len(sog) == 1 and sog_direncli == [sog[0]["no"]],
            f"gecen {[s['no'] for s in sog]} · direncli {sog_direncli}")

    # 11) "plandaki yere koy" diyen her adim, o parcanin mm konumunu da
    #     gostermeli — sayilar yalnizca belgenin en sonundaki arayuz
    #     bolumundeydi, kullanici montaj sirasinda orayi acmiyor.
    konumsuz = [s["no"] for s in aa if "plandaki yer" in _metin(s)
                and not ic_konum_satirlari(s)]
    D.kosul("'Plandaki yere koy' diyen her adim mm konumunu da gosteriyor",
            not konumsuz, f"konumsuz: {konumsuz}" if konumsuz
            else f"{[s['no'] for s in aa if 'plandaki yer' in _metin(s)]}")

    D.kosul("Etiketleme adimi panelin BUTUN etiketlerini sayiyor",
            not eksik_etiket, f"eksik: {eksik_etiket}" if eksik_etiket
            else f"{len([o for o in panel_ogeleri() if o.get('etiket')])} etiket")
    # ── B55l: kapanistan SONRAKI hicbir adim, kutuya KILITLENEN bir tuketilebilir
    # parcayi istemesin. 16.3 "18650 + 3.3 ohm" istiyordu; stokta tam 2 hucre var
    # ve ikisi de 14.4/15.4'te yuvaya giriyor, 16.2'de kapak kapaniyor.
    kapanis_i = next((i for i, s in enumerate(aa) if s.get("kapanis")), len(aa))
    hucre_stok = 0
    if stok_.var:
        # ⚠ Ilk suzgecim yuvalari/contalari da sayip 33 diyordu. Hucrenin kendisi
        # "Li-ion" ve "Sarjli" geciyor; yuva/tutucu/baslik/conta gecmiyor.
        hucre_stok = sum(int((r["adet"] or "0").strip() or 0) for r in stok_.kayit
                         if "18650" in r["ad"] and "li-ion" in _kucuk(r["ad"])
                         and "şarjlı" in _kucuk(r["ad"]))
    hucre_kutuda = sum(1 for d in K.DUVAR_PARCA if d["ref"].startswith("YUVA"))
    isteyen = [s["no"] for i, s in enumerate(aa) if i > kapanis_i
               and "18650" in " ".join(s.get("yap", []))
               and "isteğe bağlı" not in " ".join(s.get("yap", []))]
    D.kosul("Kapanistan sonraki adimlar kutuya kilitlenen hucreyi SART kosmuyor",
            not isteyen,
            f"stokta {hucre_stok} hucre, kutuya {hucre_kutuda} giriyor, serbest "
            f"{hucre_stok - hucre_kutuda}" + (f" · isteyen adim {isteyen}" if isteyen else ""))
    # ── B55l: enerjili karta entegre/modul takilmasin. Ilk enerji adimi anahtari
    # ACIK birakiyordu, 11.1 dort DIP entegre + iki ADS modulu + J5 kablosu takiyor.
    # (B58: XT30 kuyrugunun boy iddiasi kuyrukla birlikte kalkti.)
    m105 = _kucuk(" ".join(hepsi["10.5"]["yap"]))
    D.kosul("Ilk enerjiden sonra 11.1'den ONCE enerjiyi KESEN talimat var",
            "pil'i kapat.</b>" in m105 and "11.1" in m105,
            "10.5 sonunda kapatma talimati var")
    # ── B55l: bir kontrol maddesi, o an HENUZ BAGLANMAMIS bir uca bakmasin.
    # 7.2 "C29 <-> COM jaki otmeli" diyordu ama COM'un teli 9.1'de baglaniyor:
    # kullanici kesin OL okur ve saglam lehimini sokmeye kalkar.
    com_adim = next((s["no"] for s in aa if s.get("kablo") and 12 in s["kablo"]), None)
    m72 = " ".join(hepsi["7.2"].get("kontrol", []))
    D.kosul("7.2 kontrolu, teli daha sonra baglanan COM JAKINA bakmiyor",
            "COM jakı: ötmeli" not in m72,
            f"COM teli {com_adim} adiminda baglaniyor, 7.2 ondan once")
    # ── B55l: kalin jak uclari kutu BOSKEN hazirlanmali. 7.1'de kart A takili ve
    # o jaklarin arkasinda yalniz ~12 mm kor bosluk var; havya oraya girmiyor.
    ic3_a = next((q for q in ic3 if q["ref"] == "A (dolu)"), None)
    kalin_jak = [o for o in oge if o["ref"] in ("J3.1", "J3.2", "J7.1", "J7.2")]
    yarik = min(kb["ic_boy"] - o["derin_mm"] - (ic3_a["y"] + ic3_a["boy"]) for o in kalin_jak) if ic3_a else 99
    m52 = _kucuk(" ".join(hepsi["5.2"]["yap"]))
    D.kosul("Kalin jak uclari kutu BOSKEN hazirlaniyor (kart takilinca yarik dar)",
            "pigtail" in m52 and "kutu boşken" in m52,
            f"kart A ile jak ucu arasi {yarik:.0f} mm — 5.2'de pigtail {'VAR' if 'pigtail' in m52 else 'YOK'}")
    D.kosul("Pigtail talimati, kalin kablolarin baglandigi adimdan ONCE geliyor",
            sira_aa["5.2"] < min(sira_aa[s["no"]] for s in aa if s.get("kablo") and 2 in s["kablo"]),
            "5.2 -> 7.1")
    # ── B62 (kullanici 2026-09-27: "kablolari nasil baglayacagim, pabuc lazim mi"):
    # plan kalin kabloyu "kalayli kanca somunun altina / kalayli uc vidanin altina"
    # koyduruyordu. Kalay basinc altinda zamanla akar (soguk akma), somun gevser;
    # 9.5 A'lik yolda gevsek baglanti isinir. Olculen: veride (adimlar, notlar,
    # malzeme, yerlesim kart-disi notlari) "kalayli kanca/uc" YALNIZ uyari olarak
    # geciyor (hemen ardindan "gevser").
    def _veri_metinleri(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for v in x.values():
                yield from _veri_metinleri(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                yield from _veri_metinleri(v)
    tum_metin = [m for ad in dir(K) if not ad.startswith("_")
                 for m in _veri_metinleri(getattr(K, ad))] + list(_veri_metinleri(V.KART_DISI_NOTU))
    kalay_talimat = [m[max(0, r.start() - 30):r.end() + 40] for m in tum_metin
                     for r in re.finditer(r"kalaylı\s+(kanca|uç)", _kucuk(m))
                     if "gevşer" not in _kucuk(m)[r.end():r.end() + 60]]
    D.kosul("Hicbir metin kalin kabloyu vida/somun altina KALAYLI koydurmuyor (B62)",
            not kalay_talimat, "; ".join(kalay_talimat) if kalay_talimat
            else f"{len(tum_metin)} metin tarandi — 'kalayli uc/kanca' yalniz uyari olarak")
    xp_kablo = [m[:90] for m in tum_metin
                if re.search(r"(kablo\w*|bacağıyla)\s+aynı\s+vida", _kucuk(re.sub(r"<[^>]+>", "", m)))]
    D.kosul("Hicbir metin kalin kabloyu sontun XP128 vidalarina gondermiyor (guc dugumu bariyerde, B55n)",
            not xp_kablo, "; ".join(xp_kablo) if xp_kablo else "XP128'de yalniz sont bacagi + tek kopru")
    yontem52 = {"kalaylama": "kalaylama" in m52, "saat yönü": "saat yönünde" in m52,
                "ikinci somun": "ikinci somun" in m52, "panel somunu değil": "jakı panele tutan somunu" in m52}
    D.kosul("5.2 jaka baglamayi tarif ediyor: kalaysiz, ikinci somun, saat yonu, panel somunu degil",
            all(yontem52.values()), " · ".join(f"{k} {'✔' if v else '✘'}" for k, v in yontem52.items()))
    m61k = _kucuk(" ".join(hepsi["6.1"]["yap"]))
    i_vid, i_fil = m61k.find("karta vidala"), m61k.find("fileto")
    D.kosul("6.1 ayak bloklarini karta VIDALIYKEN yapistirtiyor (hiza vidadan, kalem isaretinden degil)",
            0 <= i_vid < i_fil, f"karta vidala@{i_vid} < fileto@{i_fil}")
    kanalsiz = []
    for p in K.IC_PARCA:
        ts = p.get("tasiyici", {})
        if ts.get("tip") == "altlik" and ts.get("kanal", 0) > 0:
            if f"{ts['kanal']:.0f} mm kanal" not in _kucuk(" ".join(hepsi[ts["adim"]]["yap"])):
                kanalsiz.append(f"{p['ref']}@{ts['adim']}")
    D.kosul("Kanalli altligi takan her adim kanali (veriyle ayni olcuyle) soyluyor",
            not kanalsiz, f"soylemeyen: {kanalsiz}" if kanalsiz else "ESP32 (6.3), RS (6.6)")
    # ── B63 (kullanici 2026-09-27): SARJ ve USB ovalleri TIPATIP AYNI ve birbirinin aynasi;
    # etiketler 14.1'e kadar yapismiyor, arka cizim arkadan bakana gore. Kullanici TP4056'yi
    # USB ovaline takti. Olculen: (a) ters takilsa ESP32 kart A'nin altina dusuyor mu (evetse
    # 6.0 bunu soylemeli), (b) 3.2 ovallere ad yazdiriyor, 6.0/6.3 tarafi VERIDEN soyluyor,
    # (c) taraf fonksiyonu kullanicinin onayladigi bir gercekle kalibre: AC/KAPA sol ustte (B59).
    sarj_o = next(o for o in panel_ogeleri() if o["ref"] == "SARJ")
    esp_p = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
    kart_a = next(p for p in K.IC_PARCA if p["ref"] == "A")
    a_z0 = next(a["yuk"] for a in ayaklar() if a["sahip"] == "A")
    esp_z1 = next(a["yuk"] for a in ayaklar() if a["sahip"] == "ESP32") + esp_p["yuk"]
    ters_x0 = sarj_o["x"] - esp_p["soket_x_ofset"]
    ters_cakisir = (ters_x0 < kart_a["x"] + kart_a["en"] and kart_a["x"] < ters_x0 + esp_p["en"]
                    and esp_p["y"] < kart_a["y"] + kart_a["boy"] and kart_a["y"] < esp_p["y"] + esp_p["boy"]
                    and esp_z1 > a_z0)
    m32r, m60r, m63r = (" ".join(hepsi[n]["yap"]) for n in ("3.2", "6.0", "6.3"))
    taraf_ok = {"3.2 ovallere ad": "iç yüzüne" in _kucuk(m32r) and "ŞARJ / USB" in m32r,
                "3.2 taraf veriden": "{sarj_taraf}" in m32r and "{usb_taraf}" in m32r,
                "6.0 taraf veriden": "{sarj_taraf}" in m60r,
                "6.3 taraf veriden": "{usb_taraf}" in m63r,
                "6.0 kart A uyarısı": (not ters_cakisir) or "kart a'nın altına" in _kucuk(m60r),
                "taraf kalibre (AÇ/KAPA solda)": on_bakis_taraf("SWP1") == "solda",
                "ovaller ayrı tarafta": on_bakis_taraf("SARJ") != on_bakis_taraf("USB")}
    # ── B64 (kullanici 2026-09-27, 6.2: "kartin kablo olan taraflari ne yone bakmali?"): kart A'nin
    # yonu veride yoktu (yalniz 6.1'de parantez). Olculen: yon ile sutun_yonu tutarli, A-C
    # sutunlarindaki tel uclari kutu koordinatinda ON kenarda, 6.2 yonu veriden (A1 kosesi) soyluyor.
    ka = next(p for p in K.IC_PARCA if p["ref"] == "A")
    n_a = V.KARTLAR["A"]["sutun"] - 1
    y_c0, y_cn = kart_nokta(ka, 0, n_a / 2)[1], kart_nokta(ka, n_a, n_a / 2)[1]
    yon_tutarli = (ka.get("sutun_yonu") == "arka") == (y_c0 > y_cn)
    a_teller = {k: v for k, v in V.YER.items() if v[0] == "A" and v[1] == "TEL" and v[2] <= 2}
    on_uzak = {k: ka["y"] + ka["boy"] - kart_nokta(ka, v[2], v[3])[1] for k, v in a_teller.items()}
    arkada = sorted(k for k, d in on_uzak.items() if d > 3 * 2.54 + 1)
    m62r = " ".join(hepsi["6.2"]["yap"])
    D.kosul("Kart A'nin yonu veride ve 6.2'de: telli kenar (A–C) ON panele bakiyor (B64)",
            yon_tutarli and not arkada and len(a_teller) >= 5 and "{yon_a}" in m62r and "A–C" in m62r,
            f"{len(a_teller)} tel ucu on kenara <= {max(on_uzak.values()):.1f} mm"
            + (f" · ARKADA: {arkada}" if arkada else "") + f" · {kart_yon_cumlesi(ka)}"
            + f" · yon/sutun_yonu tutarli {yon_tutarli}")
    # ── B64b: B:O16 -> A:C11 telinin boyu. Yerlesim "<10 cm", kablo notu "15 cm kes" diyordu;
    # kutuda duz cizgi 14.5 cm. Iki yonden: kisa yetmez, cok uzun yuksek empedansli dugumde
    # gurultu toplar. 1.1 sayiyi veriden veriyor, hicbir metin GND ile burdurmuyor (B'de GND yok).
    ht = hvalt_tel()
    not_hv = next(c[4] for c in V.KABLOLAR if {c[0], c[1]} == {"B:T_N6", "A:T_HVALT"})
    not_cm = re.search(r"(\d+) cm kes", not_hv)
    kes_mm = int(not_cm.group(1)) * 10 if not_cm else 0
    m11r = " ".join(hepsi["1.1"]["yap"])
    burdurur = [m[:60] for m in tum_metin + [not_hv] if re.search(r"gnd ile bur\b", _kucuk(m))]
    D.kosul("B–A telinin boyu kutudaki yoldan: ne kisa ne gereksiz uzun, 1.1 veriden (B64b)",
            ht["kes"] <= kes_mm <= ht["kes"] + 50 and "{hvalt_kes" in m11r and not burdurur,
            f"duz {ht['duz']:.0f} mm · yol {ht['yol']:.0f} mm · gereken {ht['kes']:.0f} mm · notta {kes_mm} mm"
            + (f" · GND ile burduran: {burdurur}" if burdurur else ""))
    # ── B65 (kullanici 2026-09-27): ESP32 kizagi. "Bacaklarina dikkat et, USB takilirken geriye
    # gitmesin, anten cikintisi ~18-19 mm ortada." Olculen: kizak devkit'i dort yandan tutuyor,
    # takozlar antene DEGMEDEN omuza dayaniyor, olculmemis cikinti ARALIGININ iki ucunda da
    # takozlar kart B'nin ayagina ve ön raylara carpmiyor, raylar kanal hizasinda boslukl.
    ep = next(q for q in K.IC_PARCA if q["ref"] == "ESP32")
    ekz = ep["tasiyici"]["kizak"]
    # Gercek modelden (ayaklar: 3B, kutle, cakisma bunu goruyor) — yardimci fonksiyondan degil:
    # ilk surum kizak_parcalari()'ni okuyordu ve kizak modelden dusse de yesil kaliyordu.
    kp = [a for a in ayaklar() if a.get("sahip") == "ESP32" and a.get("grup") == "kizak"]
    raylar = [a for a in kp if "-ray-" in a["ref"]]
    takozlar = [a for a in kp if "-takoz-" in a["ref"]]
    sol_ray = [a for a in raylar if a["x"] + a["en"] <= ep["x"]]
    sag_ray = [a for a in raylar if a["x"] >= ep["x"] + ep["en"]]
    yan_bosluk = max([ep["x"] - (a["x"] + a["en"]) for a in sol_ray]
                     + [a["x"] - (ep["x"] + ep["en"]) for a in sag_ray], default=99.0)
    omuz = ep["y"] + ep["boy"] - ekz["anten_cikinti"]
    D.kosul("ESP32 kizagi devkit'i dort yandan tutuyor: iki yanda ray, anten ucunda iki takoz, arkada duvar (B65)",
            len(sol_ray) >= 2 and len(sag_ray) >= 2 and yan_bosluk <= 0.5 and len(takozlar) == 2
            and all(abs(a["y"] - omuz) < 0.01 for a in takozlar) and ep["y"] <= 3.0,
            f"ray sol {len(sol_ray)} / sag {len(sag_ray)} · kenara {yan_bosluk:.2f} mm · takoz {len(takozlar)} "
            f"omuzda (y {omuz:.0f}) · USB ucu duvara {ep['y']:.0f} mm")
    orta_e = ep["x"] + ep["en"] / 2
    anten = (orta_e - ekz["anten_en"] / 2, orta_e + ekz["anten_en"] / 2)
    if takozlar:
        t_sol = min(takozlar, key=lambda a: a["x"])       # en soldaki
        t_sag = max(takozlar, key=lambda a: a["x"])
        anten_pay = min(anten[0] - (t_sol["x"] + t_sol["en"]), t_sag["x"] - anten[1])
        omuz_temas = min(t_sol["x"] + t_sol["en"] - ep["x"], ep["x"] + ep["en"] - t_sag["x"])
    else:                                              # takoz yoksa kirmizi, cokme degil
        anten_pay = omuz_temas = -99.0
    D.kosul("Omuz takozlari anten cikintisina DEGMIYOR (>= 1 mm) ve omuza en az 2 mm dayaniyor (B65)",
            anten_pay >= 1.0 and omuz_temas >= 2.0,
            f"antene {anten_pay:.2f} mm · omuz temasi {omuz_temas:.2f} mm (omuz {(ep['en'] - ekz['anten_en']) / 2:.2f} mm)")
    ci_sorun = []
    govde_b65 = [g for g in kutu_govdeleri(nl, parcalar)
                 if not (_kok_ref(g["ref"]) == "ESP32" or g.get("sahip") == "ESP32")]
    for ci in ekz["anten_cikinti_aralik"]:
        kpi = kizak_parcalari(ep, ci)
        tk = [a for a in kpi if "-takoz-" in a["ref"]]
        ry = [a for a in kpi if "-ray-" in a["ref"]]
        for a in tk:
            for b in govde_b65 + ry:
                if aralik3(a, b) < 0:
                    ci_sorun.append(f"cikinti {ci:g}: {a['ref']} ↔ {b['ref']}")
    D.kosul("Olculmemis anten cikintisinin ARALIGI boyunca takozlar hicbir govdeye ve raya carpmiyor (B65)",
            not ci_sorun, "; ".join(ci_sorun[:4]) if ci_sorun
            else f"cikinti {ekz['anten_cikinti_aralik'][0]:g}–{ekz['anten_cikinti_aralik'][1]:g} mm, iki uc da temiz")
    ets = ep["tasiyici"]
    k_bas = ep["y"] + (ets["uzunluk"] - ets["kanal"]) / 2
    k_son = k_bas + ets["kanal"]
    ray_kanalda = [a["ref"] for a in raylar if a["y"] < k_son and k_bas < a["y"] + a["boy"]]
    D.kosul("Raylar kanal hizasinda BOSLUKLU: kablo bagi altliktan cikip devkit'in ustune donebiliyor (B65)",
            not ray_kanalda and ets["kanal"] >= 2 * K.KABLO_BAGI["genislik"],
            f"kanal y {k_bas:.0f}–{k_son:.0f} · rayda: {ray_kanalda or 'yok'}")
    # Kaydirma payi IKI yoldan: esp_kayma_payi (adim adim kaydirip cakisma arar) ile dogrudan
    # x-araligi (y ve z'de ortusen en yakin sol / sag komsu). Tutmazsa metindeki sayi yalan.
    takim_b65 = [g for g in kutu_govdeleri(nl, parcalar)
                 if _kok_ref(g["ref"]) == "ESP32" or g.get("sahip") == "ESP32"]
    araliklar = {"sol": [], "sag": []}
    for a in takim_b65:
        for b in govde_b65:
            if a["y"] < b["y"] + b["boy"] and b["y"] < a["y"] + a["boy"] and a["z"] < b["z"] + b["yuk"] \
                    and b["z"] < a["z"] + a["yuk"]:
                if b["x"] + b["en"] <= a["x"]:
                    araliklar["sol"].append(a["x"] - (b["x"] + b["en"]))
                elif b["x"] >= a["x"] + a["en"]:
                    araliklar["sag"].append(b["x"] - (a["x"] + a["en"]))
    dog_sol, dog_sag = min(araliklar["sol"], default=30.0), min(araliklar["sag"], default=30.0)
    k_sol, k_sag = esp_kayma_payi(nl, parcalar)
    D.kosul("ESP32 kaydirma payi iki bagimsiz hesapta tutuyor (6.3'teki sayilar) (B65)",
            abs(k_sol - min(dog_sol, 30.0)) <= 0.25 and abs(k_sag - min(dog_sag, 30.0)) <= 0.25,
            f"sola {k_sol:.2f} / {dog_sol:.2f} mm · saga {k_sag:.2f} / {dog_sag:.2f} mm (kaydirma / dogrudan)")
    m63k = _kucuk(re.sub(r"<[^>]+>", "", " ".join(hepsi["6.3"]["yap"])))
    m63r2 = " ".join(hepsi["6.3"]["yap"])
    b65_metin = {"boş pin": "boş pinlerin tepesinden" in m63k, "dolu pinler veriden": "{esp_dolu_pin}" in m63r2,
                 "antene değmez": "antene değmez" in m63k, "kaydırma payı veriden":
                 "{esp_sag_pay" in m63r2 and "{esp_sol_pay" in m63r2, "sökme yolu": "sökmek" in m63k}
    D.kosul("6.3 kizagi ve bagi uygulanabilir tarif ediyor (bos pin, veriden pinler/paylar, anten, sokme) (B65)",
            all(b65_metin.values()), " · ".join(f"{k} {'✔' if v else '✘'}" for k, v in b65_metin.items())
            + f" · dolu: {', '.join(esp_dolu_pinler(nl))}")
    # ── B66 (kullanici 2026-09-27: "o klemens kac amper kaldiriyor, baktin mi?"): yuk yolundaki
    # en zayif halka XP128 (10 A) idi; KULLANIM "13 A birkac dakika" vaat ediyordu. Olculen: akim
    # siniri klemensin anma akimini asmiyor, kullanim metnindeki hicbir akim onu asmiyor, 7.1
    # degeri kayitta olmayan HB950'nin baskisina baktiriyor.
    k_anma = K.KLEMENS_ANMA_A["XP128"]
    i_sinir = menziller()["i_maks"]
    kul_akim_ham = re.sub(r"<[^>]+>", "", next(x[2] for x in K.KULLANIM if x[1].startswith("YÜK 1")))
    asan = [v for v in re.findall(r"(\d+(?:[.,]\d+)?)\s*A\b", kul_akim_ham) if float(v.replace(",", ".")) > k_anma]
    hb_bak = "hb950'nin üstündeki baskıya bak" in _kucuk(re.sub(r"<[^>]+>", "", " ".join(hepsi["7.1"]["yap"])))
    D.kosul("Akim siniri sontu tutan klemensin anma akimini asmiyor, metin asan akim vaat etmiyor (B66)",
            i_sinir <= k_anma and not asan and hb_bak,
            f"sinir {i_sinir:.1f} A <= XP128 {k_anma:.0f} A · metinde asan: {asan or 'yok'} · HB950 baskisi 7.1'de {hb_bak}")
    # ── B67 (kullanici 2026-09-27 iki sont veri sayfasi gonderdi): metin R042'nin veri sayfasina
    # uyuyor mu? Eski tarif "iki bakir bacak, boncugun hemen altina bakira, 11 mm bük" idi; R042
    # tek parca manganin, basigin altinda 3.5 mm bacak var (klemense), W = 10 ± 0.5 mm.
    sv = K.SONT_VERI["R042"]
    m64 = _kucuk(re.sub(r"<[^>]+>", "", " ".join(hepsi["6.4"]["yap"])))
    m122 = _kucuk(re.sub(r"<[^>]+>", "", " ".join(hepsi["12.2"]["yap"])))
    # B68b: "5 mΩ Ø2" (B53 olcumu; veri sayfasi Ø1.6) ve Q1 notundaki "kaynagi sont ust bacagina"
    # (B55n'den beri guc dugumu bariyerde) de eski tarif sayiliyor.
    eski_sont = [m[:50] for m in tum_metin
                 if re.search(r"boncuğun hemen altına|iki bakır bacak|kaynağı şönt|5 mω ø2\b", _kucuk(m))]
    bukme_gereksiz = abs(sv["W_mm"] - K.KLEMENS_ADIM_MM["XP128"]) <= sv["W_tol_mm"]
    b67 = {"R042 takılı, R043 kullanılmaz": "r043" in m64 and "kullanma" in m64,
           "Kelvin basık yerde": "basık yerin kendisine" in m64,
           "lehim sınırı veri sayfasından": "350 °c" in m64,
           "bükme tarifi W ile tutarlı": ("önce bükmeden dene" in m64) == bukme_gereksiz,
           "eski tarif (bakır bacak / boncuk altı) yok": not eski_sont,
           "akım sınırı ≤ şönt anma": menziller()["i_maks"] <= sv["anma_A"],
           "12.2 tutmazsa s ile düzeltiyor": "±%2 tutmazsa" in m122 and "0.005 × x ÷ y" in m122}
    D.kosul("Sont tarifi takili sontun veri sayfasina uyuyor, 12.2 gercek degeri duzeltiyor (B67)",
            all(b67.values()), " · ".join(f"{k} {'✔' if v else '✘'}" for k, v in b67.items())
            + (f" · eski: {eski_sont}" if eski_sont else ""))
    # ── B68 (kullanici 2026-09-27: "silikonlasam nasil olur?"): sontun kendisine yapistirici
    # kurali yoktu. Tabloda YASAK satiri + 6.4 soyluyor + sontu tasiyan adimlar silikon surdurmuyor.
    sont_satir = next((r for r in kb["yapistirici"] if r[0].startswith("Şöntün kendisi")), None)
    sont_silikon = [s["no"] for s in aa if s["no"] in ("6.4", "7.2")
                    and re.search(r"(şönt|lehim)\w*\W+(\w+\W+){0,4}sıcak silikon(la\b| sür(?!me))",
                                  _kucuk(re.sub(r"<[^>]+>", "", " ".join(s.get("yap", [])))))]
    D.kosul("Sontun kendisine ve Kelvin lehimlerine yapistirici YASAK (tabloda ve 6.4'te) (B68)",
            sont_satir is not None and "yapıştırıcı yok" in _kucuk(sont_satir[1])
            and "silikon sürme" in m64 and not sont_silikon,
            (sont_satir[1] if sont_satir else "tabloda satir yok") + f" · silikon surduren: {sont_silikon or 'yok'}")
    D.kosul("Birbirinin aynasi iki ovale takilan moduller karistirilamiyor (B63)",
            all(taraf_ok.values()),
            " · ".join(f"{k} {'✔' if v else '✘'}" for k, v in taraf_ok.items())
            + f" · ters takilirsa ESP32 kart A ile {'CAKISIR' if ters_cakisir else 'cakismaz'}"
            + f" · onden SARJ {on_bakis_taraf('SARJ')}, USB {on_bakis_taraf('USB')}")
    # ── B55l: kablo bagi kanali. ESP32'nin altligi iki BITISIK tam boy cubuktu;
    # bagin gecebilecegi hicbir bosluk yoktu (2 mm cubuga yandan delik acilamaz).
    BAG_EN = 3.6            # mm — SRF012 kablo bagi genisligi (envanterde tek tip)
    for p in K.IC_PARCA:
        ts = p.get("tasiyici", {})
        n = _kucuk(p.get("nasil", ""))
        # Parcanin kendi 'nasil'i ya da onu monte eden ADIM metni kablo bagi
        # diyorsa kanal sart. (Sont icin 'kablo bagi' yalniz 6.6'nin metninde
        # geciyordu ve iddia onu KACIRIYORDU — ESP32'de duzeltilen kusurun ikizi.)
        adim_metni = _kucuk(" ".join(hepsi.get(ts.get("adim", ""), {}).get("yap", [])))
        if ts.get("tip") == "altlik" and ("kablo bağ" in n or "kablo bağ" in adim_metni):
            kanal = ts.get("kanal", 0.0)
            D.kosul(f"{p['ref']} kablo bagi icin kanal var (altlik bitisik degil)",
                    kanal >= BAG_EN * 2,
                    f"kanal {kanal:.0f} mm >= 2 x bag {BAG_EN} mm ({ts.get('bolum', 1)} bolum)")
    # ── B55l: kapak takiminin gecme payi. Nominal SIFIRDI: KR1+KR2'nin dis
    # yuzleri tam ic en kadardi, yani kapak acikligin TA KENDISI genislikteydi.
    kr = kapak_raylari()
    kapak_en = max(r["x"] + r["en"] for r in kr) - min(r["x"] for r in kr)
    pay_toplam = kb["ic_en"] - kapak_en
    D.kosul("Kapak takiminin gecme payi VAR (nominal sifir degil)",
            pay_toplam > 0.01, f"kapak {kapak_en:.1f} mm, ic en {kb['ic_en']:.0f} -> pay {pay_toplam:.1f} mm")
    # Pay cubuk toleransini karsilamali: dil basacagi genisligi tipik +-0.3 mm
    # (iki yan duvar = iki tolerans) ve ahsap nemle en yonunde oynuyor.
    D.kosul("Gecme payi iki yan duvarin cubuk toleransini karsiliyor (>= 2 x 0.3 mm)",
            pay_toplam >= 0.6, f"{pay_toplam:.1f} mm >= 0.6 mm")
    sira13 = {s["no"]: i for i, s in enumerate(aa)}
    takan = sira13.get(kb["kapak_civata_takan"], -1)
    gec_delen = sorted(k for k, no in kb["kapak_civata_delen"].items()
                       if no not in sira13 or sira13[no] >= takan)
    D.kosul("Her katman, civatalar takilmadan ONCEKI bir alt adimda deliniyor",
            not gec_delen, f"{kb['kapak_civata_delen']} -> takma {kb['kapak_civata_takan']}"
            if not gec_delen else f"gec kalan: {gec_delen}")
    for no in ("6.1", "13.1"):
        ham = " ".join(hepsi[no]["yap"])
        D.kosul(f"{no} metni somun cebini veriden yaziyor (sabit Ø6 yok)",
                "{cep_cap" in ham and "Ø6 " not in ham)
    # B55j: kat sayilari da ELLE yaziliyordu ("4 parça çubuk üst üste") ve kart A
    # 9 kata cikinca eskidi. Metin artik veriden; sabit sayi kalmasin.
    m61 = " ".join(hepsi["6.1"]["yap"])
    D.kosul("6.1 ayak blogunun kat sayisini VERIDEN yaziyor (sabit '4 parça' yok)",
            "{ayak_kat_a" in m61 and "{ayak_kat_b" in m61 and "4 parça çubuk" not in m61,
            f"A {ayak_bicim()['ayak_kat_a']} kat / {ayak_bicim()['ayak_yuk_a']:.0f} mm · "
            f"B {ayak_bicim()['ayak_kat_b']} kat / {ayak_bicim()['ayak_yuk_b']:.0f} mm")
    D.kosul("Vida ucu deligi CEBIN ALTINDAKI kata aciliyor (blok 4 kattan yuksek olabilir)",
            ayak_bicim()["cep_alt_kat"] <= min(p["tasiyici"]["kat"] for p in K.IC_PARCA
                                               if p.get("tasiyici", {}).get("tip") == "ayak"),
            f"{ayak_bicim()['cep_alt_kat']}. kat")
    # Kart yuksekligi + ayak, kapak rayinin altinda kalmali (kapak kapanabilsin).
    ray_alt = olcu()["ic_yuk"] - olcu()["g"]
    for p in K.IC_PARCA:
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == p["ref"]), 0.0)
        if p["ref"] in ("A", "B"):
            D.kosul(f"{p['ref']} ayakla birlikte kapak rayinin altinda kaliyor",
                    z0 + p["yuk"] <= ray_alt, f"ust {z0 + p['yuk']:.0f} <= {ray_alt:.0f} mm")
    # ── B55g: "<adim>'de acilan delik" atiflari gercekten DELEN bir adima gitsin
    # 16.2 "13.2'de acilan dort delikten" diyordu; delikler B55d'de 4.7'ye tasinmisti
    # ve 13.2'nin basligi "Kapagi dene — sonra CIKAR". Sira denetimi bunu goremiyordu.
    sira_no = {s["no"]: i for i, s in enumerate(aa)}
    atif_kalip = re.compile(r"(\d+\.\d+)['’]d[ae] açıl")
    kotu_atif = []
    for s in aa:
        for t in s.get("yap", []) + s.get("kontrol", []):
            for hedef in atif_kalip.findall(t):
                h = hepsi.get(hedef)
                if h is None or "del" not in _kucuk(h["baslik"]) or sira_no[hedef] >= sira_no[s["no"]]:
                    kotu_atif.append(f"{s['no']} -> {hedef}")
    D.kosul("'<adim>'de acilan delik' atiflari DELEN ve ONCE gelen bir adimi gosteriyor",
            not kotu_atif, f"kotu atif: {kotu_atif}" if kotu_atif
            else f"{sum(len(atif_kalip.findall(t)) for s in aa for t in s.get('yap', []) + s.get('kontrol', []))} atif dogru")
    # ── B55g: ic kat konumu ELLE yazilmasin (uc havalandirma gerekcesi de yanlisti)
    kalip_ic = re.compile(r"iç kat (?:çubuğunun|çubuğu|yok)")
    elle_konum = sorted({f"{o['ref']}.{alan}" for o in K.PANEL_ON + K.PANEL_ARKA
                         for alan in ("not", "neden") if kalip_ic.search(o.get(alan, ""))})
    D.kosul("Panel metinleri ic kat konumunu ELLE yazmiyor (uretilen {konum})",
            not elle_konum, f"elle yazan: {elle_konum}" if elle_konum
            else f"{sum(1 for o in K.PANEL_ON + K.PANEL_ARKA if '{konum}' in o.get('neden', ''))} oge {{konum}} kullaniyor")
    D.kosul("Her havalandirma deliginin gerekcesi konumu veriden aliyor",
            all("{konum}" in o.get("neden", "") for o in panel_ogeleri() if o["tip"] == "havalandirma"))
    hava = [o for o in panel_ogeleri() if o["tip"] == "havalandirma"]
    hucre_var = any(d["ref"].startswith("YUVA") for d in K.DUVAR_PARCA)
    D.kosul("Kutuda hucre varsa havalandirma deligi var (Li-ion gaz tahliyesi)",
            len(hava) >= 2 if hucre_var else True, f"{len(hava)} delik, hucre={hucre_var}")
    alan = sum(math.pi * (o["delik_mm"] / 2) ** 2 for o in hava)
    D.kosul("Havalandirma toplam alani >= 50 mm2", alan >= 50.0, f"{alan:.0f} mm2")
    ust = [o for o in hava if o["z"] > olcu()["ic_yuk"] / 2]
    D.kosul("En az iki havalandirma deligi UST yarida (gaz yukari cikar)", len(ust) >= 2, f"{len(ust)} adet")
    for o in hava:
        kapatan = [d["ref"] for d in duvar_parcalari()
                   if d["duvar"] == o["panel"] and d["x"] <= o["x"] <= d["x"] + d["en"]
                   and d["z"] <= o["z"] <= d["z"] + d["yuk"]]
        D.kosul(f"{o['ref']} deligini duvara asili bir parca KAPATMIYOR", not kapatan, str(kapatan))

    led = next(o for o in panel_ogeleri() if o["tip"] == "led")
    arti, donus = led["bagli"]
    D.kosul("GUC LED'i +12 rayina bagli (klemens ARTI ucu)", arti == "KL.+", arti)
    D.kosul("GUC LED'inin donusu kart GND — -12 rayina DEGIL (79xx o yonde akim veremez)",
            donus == "KART_GND" and "-" not in donus, donus)
    # Kullanicinin GORDUGU metnin tamami: panel notu + gerekce + montaj kurali.
    led_metin = led["not"] + " " + led["neden"] + " " + K.KUTU_NOTU["LED1"]
    D.kosul("LED belgesi +12 rayini soyluyor ve -12'ye baglamayi YASAKLIYOR",
            "+12" in led_metin and "−12" in led_metin and "bağlama" in _kucuk(led_metin))
    D.kosul("LED PASIF: ESP32'ye bagli degil (firmware'siz, ESP32 olu olsa da yanar)",
            "esp32" in _kucuk(led["not"]) and "pasif" in _kucuk(led["not"]))
    i_led = T.PANEL_LED_AKIM
    D.kosul("LED akimi B11 orta nokta butcesinde sayili (tasarim3_sabit'ten)",
            0 < i_led < 5e-3, f"{i_led*1e3:.2f} mA")
    D.kosul("LED akimi 7912'nin cekme kapasitesinin cok altinda",
            i_led < 0.01 * T.LM7912_IOUT_MAKS, f"{i_led*1e3:.2f} mA / {T.LM7912_IOUT_MAKS*1e3:.0f} mA")
    p_r = i_led ** 2 * T.PANEL_LED_R
    D.kosul("LED seri direncinin gucu 1/4 W'in %25'inin altinda", p_r < 0.25 * 0.25,
            f"{p_r*1e3:.1f} mW")
    f1_toplam = 25e-3 + i_led                                  # 24 V girisi en kotu + LED
    D.kosul("LED eklenince F1 (50 mA sinifi) payi >= %30",
            (50e-3 - f1_toplam) / 50e-3 >= 0.30, f"{f1_toplam*1e3:.1f} mA / 50 mA")

    print("\n  8 · AGIRLIK MERKEZI (B55)")
    dg = K.DENGE
    # Kapsam: bir parca eklenip kutlesi yazilmazsa burasi kirmizi olur —
    # agirlik merkezi sessizce eksik bir kutle setiyle hesaplanmasin.
    for p in K.IC_PARCA:
        D.kosul(f"{p['ref']} icin kutle kaydi var", p["ref"] in K.KUTLE)
    for d in K.DUVAR_PARCA:
        D.kosul(f"{d['ref']} icin kutle kaydi var", d["ref"] in K.KUTLE)
    for x in panel_ogeleri():
        if x["tip"] not in PARCASIZ_TIP:
            D.kosul(f"Panel ogesi {x['ref']} bir kutle anahtarina bagli", kutle_anahtari(x) in K.KUTLE,
                    kutle_anahtari(x))
    D.kosul("Her kutle satirinda kaynak yazili (>= 15 karakter)",
            all(len(v[2]) >= 15 for v in K.KUTLE.values()),
            str([k for k, v in K.KUTLE.items() if len(v[2]) < 15]))
    D.kosul("Her kutle satirinda belirsizlik tanimli (0 < bel <= 0.5)",
            all(0 < v[1] <= 0.5 for v in K.KUTLE.values()))
    D.kosul("Kullanilmayan kutle satiri yok (tablo olu satir tasimiyor)",
            set(K.KUTLE) == _kullanilan_kutle(),
            str(set(K.KUTLE) - _kullanilan_kutle()))
    am2 = agirlik_merkezi(2)
    tahta_g = sum(k["m"] for k in am2["kalem"] if k["grup"] in ("kutu", "kapak"))
    cubuk_g = K.CUBUK["uzunluk"] * K.CUBUK["genislik"] * K.CUBUK["kalinlik"] * K.CUBUK_YOGUNLUK
    # Iki BAGIMSIZ model: kesim listesi parca parca uzunluktan, kutle modeli
    # geometriden. Esit olmalari gerekir; ayrisma = bir parca birinde var
    # obruinde yok demektir (B55c: TP raf bloklari kutlede, MT yanaklari ve
    # kapak somun bloklari HIC BIR listede yoktu — bu iddia ucunu de yakalar).
    ol = olcu()
    kesim_hacim = sum(x["u"] * ol["g"] * ol["t"] * x["adet"] for x in hesap()["parcalar"])
    kutle_hacim = tahta_g / K.CUBUK_YOGUNLUK
    D.kosul("Kesim listesi ve kutle modelinin ahsap hacmi ayni (iki bagimsiz model)",
            abs(kesim_hacim - kutle_hacim) <= 0.005 * kesim_hacim,
            f"kesim {kesim_hacim:.0f} mm3 vs kutle {kutle_hacim:.0f} mm3 "
            f"(fark {kesim_hacim - kutle_hacim:+.0f})")
    for d in K.DUVAR_PARCA:
        D.kosul(f"{d['ref']} icin ahsap tutucu karari verilmis (DUVAR_TUTUCU)", d["ref"] in K.DUVAR_TUTUCU)
    # "blok" ile arama TP2'yi kacirdi: metinde "çubuk bloğuna" geciyor ve Turkce
    # yumusak g yuzunden "blok" alt dizgisi YOK (deponun bilinen tuzagi) -> kok "blo".
    def _ahsap_der(n):
        return "çubuk" in _kucuk(n) or "blo" in _kucuk(n)
    D.kosul("Metinde ahsap tutucu diyen her duvar parcasinin kesim listesinde karsiligi var",
            all(bool(K.DUVAR_TUTUCU[d["ref"]]) == _ahsap_der(d["nasil"]) for d in K.DUVAR_PARCA),
            str([d["ref"] for d in K.DUVAR_PARCA
                 if bool(K.DUVAR_TUTUCU[d["ref"]]) != _ahsap_der(d["nasil"])]))
    D.kosul("Kutudaki tahta, kesim listesinin cubuk sayisindan az (fire disarida kaliyor)",
            tahta_g < hesap()["cubuk_sayisi"] * cubuk_g,
            f"{tahta_g:.0f} g = {tahta_g / cubuk_g:.0f} cubuk esdegeri < {hesap()['cubuk_sayisi']} cubuk")
    for hc, ad in ((2, "iki hucre"), (1, "tek hucre"), (0, "pilsiz")):
        am = agirlik_merkezi(hc)
        D.kosul(f"Taban raylarinin yuk payi dengeli ({ad}): her biri >= %{dg['ray_pay'] * 100:.0f}",
                min(am["ray_pay"]) >= dg["ray_pay"],
                f"sol %{am['ray_pay'][0] * 100:.0f} / sağ %{am['ray_pay'][1] * 100:.0f} "
                f"(AM x {am['sapma']['x']:+.1f} mm)")
        D.kosul(f"Ray yuk payi KOTU HALDE de dengeli ({ad}): >= %{dg['kotu_ray_pay'] * 100:.0f}",
                min(am["kotu_ray_pay"]) >= dg["kotu_ray_pay"],
                f"en kotu %{min(am['kotu_ray_pay']) * 100:.0f} "
                f"(AM x {am['kotu']['x'][0]:+.1f} … {am['kotu']['x'][1]:+.1f} mm)")
        oran = abs(am["sapma"]["y"]) / am["yari"]["y"]
        D.kosul(f"AM derinlikte orta bolgede ({ad}): sapma yari derinligin %{dg['y_orta'] * 100:.0f}'undan az",
                oran <= dg["y_orta"], f"{am['sapma']['y']:+.1f} mm = %{oran * 100:.1f}")
        kotu_y = max(abs(v) for v in am["kotu"]["y"]) / am["yari"]["y"]
        D.kosul(f"AM derinlikte KOTU HALDE de orta bolgede ({ad}): %{dg['kotu_y_orta'] * 100:.0f}",
                kotu_y <= dg["kotu_y_orta"],
                f"{am['kotu']['y'][0]:+.1f} … {am['kotu']['y'][1]:+.1f} mm = %{kotu_y * 100:.1f}")
        for yon, aci in am["kotu_aci"].items():
            D.kosul(f"Devrilme acisi {yon} ({ad}, kotu hal) >= {dg['devrilme_aci']:.0f} derece",
                    aci >= dg["devrilme_aci"],
                    f"{aci:.0f}° (nominal {am['aci'][yon]:.0f}°, pay {am['kotu_pay'][yon]:.0f} mm, "
                    f"AM yuksekligi {am['z_kotu']:.0f} mm)")
        D.kosul(f"AM destek alaninin ({ad}) icinde (devrilmez), kotu halde de",
                all(v > 0 for v in am["pay"].values()) and all(v > 0 for v in am["kotu_pay"].values()))
        D.kosul(f"AM yuksekligi ({ad}) dis yuksekligin yarisindan az", am["z_orani"] <= dg["am_yukseklik"],
                f"{am['z']:.0f} / {am['dis'][2]:.0f} mm = %{am['z_orani'] * 100:.0f}")
        # Kotu-hal KATMANININ CALISTIGI iddiasi. Bunsuz `_am_uc`'yi devre disi birakan
        # bir degisiklik (yineleme sayisi 0) butun kotu-hal iddialarini nominal degerle
        # besliyor ve 24'u birden yesil kaliyor — mutasyon kosucusu bunu KACIRDI (B55d).
        # Butun kutlelerin belirsizligi > 0 ve kalemler ayni noktada olmadigi icin kotu
        # hal nominali her eksende belirgin sekilde ASMAK ZORUNDA.
        for e in ("x", "y"):
            lo, hi = am["kotu"][e]
            D.kosul(f"Kotu hal {e} ({ad}) nominali iki yandan da asiyor (katman gercekten calisiyor)",
                    lo < am["sapma"][e] - AM_KOTU_EN_AZ and hi > am["sapma"][e] + AM_KOTU_EN_AZ,
                    f"{lo:+.1f} < {am['sapma'][e]:+.1f} < {hi:+.1f} mm")
        D.kosul(f"Kotu hal z ({ad}) nominalin uzerinde (katman gercekten calisiyor)",
                am["z_kotu"] > am["z"] + AM_KOTU_EN_AZ, f"{am['z_kotu']:.1f} > {am['z']:.1f} mm")
        z_kotu_orani = am["z_kotu"] / am["dis"][2]
        D.kosul(f"AM yuksekligi KOTU HALDE de sinirda ({ad}): %{dg['kotu_am_yukseklik'] * 100:.0f}",
                z_kotu_orani <= dg["kotu_am_yukseklik"],
                f"{am['z_kotu']:.0f} / {am['dis'][2]:.0f} mm = %{z_kotu_orani * 100:.1f} "
                f"(nominal %{am['z_orani'] * 100:.1f})")
        D.kosul(f"Toplam kutle ({ad}) makul aralikta (0.3-3 kg)", 300 <= am["M"] <= 3000, f"{am['M']:.0f} g")
    D.kosul("Hucre sayisi arttikca kutle artiyor (yapilandirmalar ayirt ediliyor)",
            agirlik_merkezi(0)["M"] < agirlik_merkezi(1)["M"] < am2["M"])

    # ── B57 · PARCA BILGI KARTLARI ───────────────────────────────────────
    # Kullanici: "mouse ile uzerine getirince veya bir tusa basinca o parcanin
    # detaylarini gorebilmem lazim — uzunlugu, adi, olculeri." Kartin TARAYICIDA
    # acildigini kutu_ipucu_test.py olcuyor; burasi kartlarin VERIDEN DOGRU ve
    # EKSIKSIZ uretildigini olcuyor.
    print("\n  9 · PARCA BILGI KARTLARI (B57)")
    sah = sahne()
    # B59b (kullanici 2026-09-26): ic kat da 5.1'de deliniyor ama 3B'de delik yalniz DIS yuzde
    # ciziliyordu — iceriden bakinca ic kat cubuklari deliksiz gorunuyordu. Her panel deligi
    # (USB/SARJ yuvasi haric: arkasindaki cubuk kisa) ic yuzde de plakali olmali, 5.1'den itibaren.
    boy_ic = K.KUTU["ic_boy"]
    ic_plaka = [b for b in sah if b["g"] == "delik" and b["ad"].endswith("(iç kat)")]
    eksik_ic = []
    for o in panel_ogeleri():
        if o["tip"] in ("yuva", "kuyruk"):
            continue
        yi = -0.3 if o["panel"] == "ön" else boy_ic - 0.3
        if not any(abs(b["y"] - yi) < 0.01 and abs(b["x"] + b["dx"] / 2 - o["x"]) < 0.01
                   and abs(b["z"] + b["dz"] / 2 - o["z"]) < 0.01 and b["gor"] == sira["5.1"] for b in ic_plaka):
            eksik_ic.append(f"{o['panel']}:{o['etiket']}")
    D.kosul("3B: her panel deliginin IC kat yuzunde de plakasi var ve 5.1'de (delindigi adim) beliriyor",
            not eksik_ic, f"eksik: {eksik_ic}" if eksik_ic else f"{len(ic_plaka)} ic kat deligi")
    anahtarsiz = sorted({b["ad"] for b in sah if not b.get("k") or b["k"] not in _BILGI})
    D.kosul("3B'deki her blogun bir bilgi karti var",
            not anahtarsiz, f"kartsiz: {anahtarsiz[:6]}" if anahtarsiz else f"{len(sah)} blok, {len({b['k'] for b in sah})} kart")
    # Iki BAGIMSIZ hesap: sahne() geometrisi ve hesap()['parcalar'] (kesim listesi).
    # 3B'de olup kesim listesinde olmayan parca = kullanici kesmeden kurmaya kalkar
    # (B55c'de kesim listesinde 16 parca eksikti — bu iddia o sinifi yakalar).
    cubuk = {b["k"] for b in sah if b["k"].startswith("c:")}
    listesiz = sorted(k.split("|")[0][2:] for k in cubuk
                      if any("kesim listesinde YOK" in r[1] for r in _BILGI[k]["r"]))
    D.kosul("3B'deki her cubuk parcasinin KESIM LISTESINDE boyu ayni bir satiri var",
            cubuk and not listesiz, f"listede yok: {listesiz[:5]}" if listesiz else f"{len(cubuk)} cubuk karti")
    uzunluksuz = sorted(k for k in cubuk if not re.match(r"^\d+(\.\d)? mm$", dict(
        (r[0], r[1]) for r in _BILGI[k]["r"]).get("Uzunluk", "")))
    D.kosul("Her cubuk kartinin ILK vurgulu satiri uzunluk (mm)",
            not uzunluksuz and all(_BILGI[k]["r"][0][0] == "Uzunluk" and len(_BILGI[k]["r"][0]) == 3 for k in cubuk),
            f"uzunluksuz: {uzunluksuz[:4]}")
    # Uzunluk karti BLOGUN GERCEK boyuna esit mi? Blok cizimde 0.4 mm kisaltiliyor
    # (derz gorunsun diye); kart kisaltilmamis boyu gostermeli, yoksa kullanici
    # 110.6 keser. En uzun kenar + 0.4, karttaki sayiya 0.6 mm icinde esit olmali.
    sapan = []
    for b in sah:
        if not b["k"].startswith("c:"):
            continue
        kart_u = float(dict((r[0], r[1]) for r in _BILGI[b["k"]]["r"])["Uzunluk"].split()[0])
        blok_u = max(b["dx"], b["dy"], b["dz"])
        if not (abs(kart_u - blok_u) <= 0.6 or abs(kart_u - (blok_u + 0.4)) <= 0.6):
            sapan.append(f"{b['ad']}: kart {kart_u} / blok {blok_u}")
    D.kosul("Cubuk kartindaki uzunluk 3B'deki blogun gercek boyuyla tutuyor", not sapan, "; ".join(sapan[:4]))
    # Verideki HER parca 3B'de uzerine gelinebilir olmali (kapsam): panel ogesi,
    # ic parca, duvar parcasi, ayak/altlik, kose diregi.
    beklenen = ({f"j:{o['ref']}" for o in panel_ogeleri()} | {f"p:{q['ref']}" for q in K.IC_PARCA}
                | {f"d:{d['ref']}" for d in K.DUVAR_PARCA} | {f"a:{a['ref']}" for a in ayaklar()}
                | {f"k:{d['ref']}" for d in direkler()})
    sahnede = {b["k"] for b in sah}
    gorunmez = sorted(beklenen - sahnede)
    D.kosul("Verideki her parca (panel/ic/duvar/ayak/direk) 3B'de uzerine gelinebilir",
            not gorunmez, f"3B'de karti yok: {gorunmez}" if gorunmez else f"{len(beklenen)} parca")
    delik_yok = sorted(k for k in sahnede if k.startswith("j:")
                       and not any(r[0] == "Delik" and r[1].startswith(("Ø", "1", "2", "3", "4", "5", "6", "7", "8", "9"))
                                   for r in _BILGI[k]["r"]))
    D.kosul("Her panel ogesinin kartinda delik olcusu var", not delik_yok, f"deliksiz: {delik_yok}")

    # ── 10 · KABLO GUZERGAHI (B73) ─────────────────────────────────────────
    # Kullanici (2026-10-01): "hangi kablo nereye gidecek ve nasil gidecek ... web
    # sayfasinda gosterelim". Cizim, 3B, tablo ve kart AYNI guzergah()'tan.
    print("\n  10 · KABLO GUZERGAHI (B73)")
    kl = kablo_listesi()
    D.kosul("Kablo listesi PIL_KABLOLAR'in ve KABLO_EK'in hepsini tam bir kez tasiyor",
            len(kl) == len(K.PIL_KABLOLAR) + len(K.KABLO_EK) and len({(k["a"], k["b"]) for k in kl}) == len(kl),
            f"{len(kl)} kablo")
    bayat = sorted(f"{a}→{b}" for a, b in K.KABLO_YOL if (a, b) not in {(k["a"], k["b"]) for k in kl})
    D.kosul("KABLO_YOL'da kablosu olmayan (bayat) guzergah kaydi yok", not bayat, f"bayat: {bayat}")
    cozulmez = []
    for k in kl:
        for u in (k["a"], k["b"]):
            try:
                uc_noktasi(u)
            except (KeyError, ValueError, StopIteration) as h:
                cozulmez.append(f"{u}: {h!r}")
    D.kosul("Her kablonun iki ucu bilinen bir terminale cozuluyor", not cozulmez, "; ".join(cozulmez[:4]))
    govde = kutu_govdeleri(nl, parcalar)
    gb = {g["ref"]: g for g in govde}
    uzak = []
    for k in kl:
        for u in (k["a"], k["b"]):
            p, sahip = uc_noktasi(u)
            sinir = max(K.KABLO_UC_SAPMA.get(r, 3.0) for r in sahip)
            if not any(nokta_kutu_mesafe(p, gb[r]) <= sinir for r in sahip if r in gb):
                uzak.append(u)
    D.kosul("Her terminal kendi parcasinin govdesinde (≤ 3 mm; TP1 tel ucu ≤ 15 mm)", not uzak,
            f"uzak: {sorted(set(uzak))[:5]}")
    ic_disi = [k["no"] for k in kl if not all(0.0 <= p[0] <= K.KUTU["ic_en"] and 0.0 <= p[1] <= K.KUTU["ic_boy"]
                                               and 0.0 <= p[2] <= hesap()["ic_yuk"] for p in guzergah(k))]
    D.kosul("Her guzergah kutunun icinde", not ic_disi, f"disari tasan: K{ic_disi}")
    carpan = {k["no"]: c for k in kl if (c := kablo_carpismalari(k, govde))}
    D.kosul("Hicbir guzergah (uclarin kendi parcasi disinda) bir govdenin icinden gecmiyor",
            not carpan, "; ".join(f"K{n}: {','.join(c)}" for n, c in list(carpan.items())[:4]))
    # Gozden gecirme (B73): ucu ORTAK OLMAYAN iki kablo ayni cizgiye binmesin. Ic bakista
    # (x-z izdusumu, 3 px/mm, cizgi 1 mm; AYNI adimin kablolari — oncekiler soluk) 2 mm'den yakin
    # paralel ve 3 mm'den uzun ortusme ya da 3B'de ayni dogru (butun ciftler). Ilk surumde 680 µF'in iki CIPLAK bacagi ayni cizgideydi; 5 V ile GND,
    # +24 ile −12 ust uste. Bu denetim seritleme kodundan BAGIMSIZ yazildi (ortak yardimci yok).
    yollar = {k["no"]: guzergah(k) for k in kl}

    def _eksen_parcalari(yol):
        for p, q in zip(yol, yol[1:]):          # baskin eksen (kart deligi 0.05 mm kaydirabiliyor)
            e = max(range(3), key=lambda i: abs(p[i] - q[i]))
            if abs(p[e] - q[e]) > 1e-6:
                yield e, p, q
    ortusen = []
    for i, ka in enumerate(kl):
        for kb_ in kl[i + 1:]:
            if {ka["a"], ka["b"]} & {kb_["a"], kb_["b"]}:
                continue
            bulundu = False
            for e, p, q in _eksen_parcalari(yollar[ka["no"]]):
                for f, r, t in _eksen_parcalari(yollar[kb_["no"]]):
                    if e != f:
                        continue
                    ort = min(max(p[e], q[e]), max(r[e], t[e])) - max(min(p[e], q[e]), min(r[e], t[e]))
                    if ort <= 3.0:
                        continue
                    ayni3 = all(abs(p[j] - r[j]) < 2.0 for j in range(3) if j != e)
                    izd = (ka["adim"] == kb_["adim"] and e in (0, 2)      # ic bakis: ayni adim kalin cizilir
                           and abs(p[2 - e] - r[2 - e]) < 2.0)                # x parcasi z'de, z parcasi x'te
                    if ayni3 or izd:
                        bulundu = True
                        break
                if bulundu:
                    break
            if bulundu:
                ortusen.append(f"K{ka['no']}/K{kb_['no']}")
    D.kosul("Ucu ortak olmayan iki kablo ayni cizgiye binmiyor (ic bakis + 3B; aralarinda ≥ 2 mm)",
            not ortusen, f"{len(ortusen)} cift: {ortusen[:8]}")

    def _kutu_mesafe(p, q, r, t):          # eksene paralel iki dogru parcasi = iki ince kutu
        return math.sqrt(sum(max(0.0, max(min(p[j], q[j]) - max(r[j], t[j]), min(r[j], t[j]) - max(p[j], q[j]))) ** 2
                             for j in range(3)))
    ciplak = []
    for k in kl:
        if k["rol"] != "bacak":
            continue
        for o in kl:
            if o is k or {k["a"], k["b"]} & {o["a"], o["b"]}:
                continue
            dmin = min(_kutu_mesafe(p, q, r, t) for p, q in zip(yollar[k["no"]], yollar[k["no"]][1:])
                       for r, t in zip(yollar[o["no"]], yollar[o["no"]][1:]))
            if dmin < 2.0:
                ciplak.append(f"K{k['no']}–K{o['no']} {dmin:.1f} mm")
    D.kosul("Kondansatorun CIPLAK bacaklari baska bir kabloya ≥ 2 mm", not ciplak, f"{ciplak[:6]}")
    # ESP32 pin uclari pin dizilimiyle capraz: 5V ile GPIO10 ayni baslikta (J1) pin farki x 2.54
    j1 = K.ESP32_J1
    beklenen_dy = (j1.index("5V") - j1.index("GPIO10")) * K.PIN_ADIM
    gercek_dy = K.KABLO_UCLARI["ESP32"]["GPIO10"][1] - K.KABLO_UCLARI["ESP32"]["5V"][1]
    D.kosul("ESP32 GPIO10 ucu 5V pininden J1 pin farki kadar uzakta (DevKitC-1: 21 = 5V, 16 = GPIO10)",
            abs(gercek_dy - beklenen_dy) <= 1.0
            and K.KABLO_UCLARI["ESP32"]["GPIO10"][0] == K.KABLO_UCLARI["ESP32"]["5V"][0],
            f"veri {gercek_dy:.1f} mm, pin dizilimi {beklenen_dy:.1f} mm")
    hv = hv_dugumu(next(p for p in K.IC_PARCA if p["ref"] == "B"))
    hv_en = {k["no"]: min(_seg_nokta(p, q, hv) for p, q in zip(guzergah(k), guzergah(k)[1:])) for k in kl}
    D.kosul(f"Hicbir kablo kart B'nin HV girisine {T.IEC60664_CREEPAGE_TAKVIYELI} mm'den yakin gecmiyor",
            min(hv_en.values()) >= T.IEC60664_CREEPAGE_TAKVIYELI, f"en yakin {min(hv_en.values()):.1f} mm")
    # Kesim: guzergah + %10 (uc tahmini, kivrim) + IKI uctaki soyma (gozden gecirme: 30 mm'lik
    # K9'a 4 cm, 42 mm'lik K13'e 5 cm veriliyordu — iki uc soyulunca 8-10 mm kaliyordu).
    tablo_kesim = {}
    for no_ in ("10.3", "10.4", "11.1"):
        for k_, hucre in re.findall(r'class="bi-satir" data-bi="t:([^"]+)"[^>]*>(?:<td>.*?</td>){4}<td><b>(.*?)</b></td>',
                                    kablo_b73_tablosu(no_)):
            tablo_kesim[html_unescape(k_)] = html_unescape(hucre)
    tel_ucu = {"TP1", "YUVA1", "YUVA2"}

    def _sahip(u):
        return K.KABLO_UC_TAKMA.get(u, u).rsplit(".", 1)[0]
    kisa, kendi_yanlis = [], []
    for k in kl:
        sahipler = {_sahip(k["a"]), _sahip(k["b"])} & tel_ucu
        hucre = tablo_kesim.get(f"{k['a']}|{k['b']}", "")
        L = guzergah_boyu(guzergah(k))
        if k["rol"] == "bacak":
            continue
        if not sahipler:
            m_ = re.match(r"(\d+) cm", hucre)
            if not m_ or int(m_.group(1)) * 10.0 < L * 1.1 + 2 * 5.0:     # 5 mm: veriden bagimsiz soyma tabani
                kisa.append(k["no"])
            continue
        # parcanin KENDI teli: hucre hangi tel oldugunu ve (TP1'de) pedden olcuyu soylemeli
        if {"YUVA1", "YUVA2"} & sahipler:
            if "yuva" not in _kucuk(hucre):
                kendi_yanlis.append(f"K{k['no']}: yuva yok")
            if "TP1" in sahipler and "tp4056" not in _kucuk(hucre):
                kendi_yanlis.append(f"K{k['no']}: TP4056 teli birlesme yok")
        else:
            tp = next(d_ for d_ in duvar_parcalari() if d_["ref"] == "TP1")
            yuksel = K.KABLO_UCLARI["TP1"]["B+"][2] - tp["yuk"]          # pedden araliga cikis
            gerek = math.ceil(((L + yuksel + K.KENDI_TEL["TP1"]["kivrim_mm"]) * K.KABLO_PAY + K.KABLO_SOYMA) / 10)
            ek_var = re.search(r"\bek\b", _kucuk(hucre)) is not None
            if "pedden" not in _kucuk(hucre) or f"{gerek} cm" not in hucre \
                    or ek_var != (gerek * 10 > K.KENDI_TEL["TP1"]["boy_mm"]):
                kendi_yanlis.append(f"K{k['no']}: '{hucre}' (gerek {gerek} cm)")
    D.kosul("Yeni kablolarin kesimi guzergah +%10 + iki uctaki soyma payi", not kisa, f"kisa: K{kisa}")
    D.kosul("Parcanin KENDI teliyle yapilan kablolar (TP4056, yuva) o teli ve pedden gereken boyu soyluyor; "
            "TP4056'nin 20 cm'si yetmezse 'ek'", not kendi_yanlis, f"{kendi_yanlis[:4]}")
    karisik = [k["no"] for k in kl if {k["a"], k["b"]} & KABLO_E12 and {k["a"], k["b"]} & KABLO_GND]
    D.kosul("Hicbir kablo -12 tarafini kart GND tarafina baglamiyor", not karisik, f"{karisik}")
    # Rol, grafin KENDI bilesenleriyle capraz sinanir (iki bagimsiz kaynak): -12'ye bagli uc
    # 'eksi12', KART_GND'ye bagli uc 'gnd' rolunde olmali (bacak haric).
    gr_ = pil_grafi()
    yanlis_rol = [k["no"] for k in kl if (k["a"], k["b"]) in {(a, b) for a, b, *_ in K.PIL_KABLOLAR}
                  and k["rol"] != "bacak"
                  and (("-12" in gr_[k["a"]]) != (k["rol"] == "eksi12")
                       or ("KART_GND" in gr_[k["a"]]) != (k["rol"] == "gnd"))]
    D.kosul("Kablo rolu dugum grafiyla tutarli (-12 -> mavi, KART_GND -> siyah)", not yanlis_rol, f"K{yanlis_rol}")
    D.kosul("10.3 / 10.4 / 11.1'in her birinde en az bir kablo var",
            all(adim_kablolari(n) for n in ("10.3", "10.4", "11.1")),
            str({n: len(adim_kablolari(n)) for n in ("10.3", "10.4", "11.1")}))
    yapisik_beklenen = {"YUVA1", "YUVA2", "MT1", "MT2", "IZ", "CB", "KL", "F0", "F1P", "F2"}
    D.kosul("Kullanici karari (2026-09-30): moduller ve kucuk duvar parcalari sicak silikonla, tutucusuz",
            yapisik_beklenen <= set(K.YAPISTIRMA_ISTISNA)
            and all(K.DUVAR_TUTUCU.get(r) is None for r in yapisik_beklenen),
            f"eksik: {sorted(yapisik_beklenen - set(K.YAPISTIRMA_ISTISNA))}")
    degerli = {"A", "B", "ESP32", "RS", "Q1"}
    D.kosul("Degerli parcalar (kartlar, ESP32, sont, Q1) yapistirma istisnasinda DEGIL",
            not (degerli & set(K.YAPISTIRMA_ISTISNA)))
    adm = {s["no"]: s for s in alt_adimlar()}

    def _metin(no):
        s = adm[no]
        return _kucuk(" ".join(s.get("yap", []) + s.get("kontrol", [])))
    ks_ = {(a, b) for a, b, *_ in K.PIL_KABLOLAR}
    D.kosul("§4.1 F2'nin cikisi F1P'nin cikis klipsine: veri ve 10.3 metni ayni",
            ("F2.2", "F1P.2") in ks_ and ("F2.2", "TP1.B+") not in ks_ and "f1p'nin çıkış klipsine" in _metin("10.3"))
    D.kosul("§4.2 hucre telleri yuvanin kendi telleri; yuva yonleri 10.2'de yazili",
            "yuvanın kendi" in _metin("10.3") and "kırmızı telinin çıktığı ucu sola" in _metin("10.2"))
    D.kosul("§4.3 GUC lambasi katodu COM jakinda (veri + 10.4 metni); 'klemens/GND noktasi' muglakligi yok",
            any(e["a"] == "LED1.K" and e["b"] == "J1.2.L" for e in K.KABLO_EK)
            and "com jakının lehim kulağına" in _metin("10.4") and "klemens/gnd noktası" not in _metin("10.4"))
    D.kosul("§4.4 10.3'te J5'ten once imkansiz 'B- <-> kart GND oter' kontrolu yok; paket-GND kontrolu 11.1'de",
            "tp1.b− ↔ kart gnd" not in _metin("10.3") and "tp4056 out− ↔ kart gnd" in _metin("11.1"))
    D.kosul("§4.5 sigorta yuvasi iki klips + <= 25 mm plaket seridi (10.2) ve veri ayni olcude",
            "iki ayrı klips" in _metin("10.2") and "25 mm" in _metin("10.2")
            and all(d["en"] <= 25.0 for d in K.DUVAR_PARCA if d["ref"] in ("F0", "F1P", "F2")))
    iz_sira = sorted(K.KABLO_UCLARI["IZ"], key=lambda u: K.KABLO_UCLARI["IZ"][u][0])
    D.kosul("§4.6 B0505S bacaklari: 10.1 veri sayfasini soyluyor, KABLO_UCLARI ayni sirada, eski cumle yok",
            all(p in _metin("10.1") for p in ("1 = +vin", "2 = −vin", "4 = −vout", "6 = +vout"))
            and iz_sira == ["IN+", "IN-", "OUT-", "OUT+"] and "gövdede basılı" not in _metin("10.1"))
    D.kosul("§4.8 MT1/MT2 kablolari tezgahta onceden lehimleniyor (10.2)", "tezgahta önce" in _metin("10.2"))
    # Gozden gecirme: B0505S'in govdesinde bacak ADI yok (§4.6) — belge Vin/GND/+Vo/0V adiyla nokta
    # aratmamali; yalitim kontrolu bacak NUMARASIYLA. Kablo kartinin notu da "ped adini oku" dememeli.
    h104 = alt_kart(adm["10.4"], nl, parcalar, stok, hesap())
    b5 = _kucuk(" ".join(_metin(n) for n in ("10.1", "10.2", "10.4")) + " " + html_unescape(h104)
                + " " + K.KUTU_NOTU["IZ"])
    eski_ad = [a for a in ("giriş gnd", "çıkış 0v", "vin/gnd", "+vo/0v", "(+vo, 0v)", "(vin, gnd)", "girişi (vin)")
               if a in b5]
    iz_kart = [k_ for k_ in _BILGI if k_.startswith("t:") and "IZ." in k_]
    iz_not = [k_ for k_ in iz_kart if "ped adını" in _BILGI[k_].get("n", "") or "1, 2, 4, 6" not in _BILGI[k_].get("n", "")]
    D.kosul("B0505S: belge govdede olmayan adlari (Vin/GND, +Vo/0V) aratmiyor; yalitim kontrolu bacak 2 ↔ 4; "
            "kablo kartlari bacak numarasini veriyor",
            not eski_ad and all("bacak 2 (−vin) ↔ bacak 4 (−vout)" in _metin(n) for n in ("10.1", "10.4"))
            and bool(iz_kart) and not iz_not, f"eski ad: {eski_ad} · not: {len(iz_not)}/{len(iz_kart)}")
    # Gozden gecirme: 10.4'te eski "Baglanacak kablolar" tablosu (J6 -> C34/C36, notu XT30)
    # yeni numarali tabloyla AYNI telleri ikinci kez listeliyordu (spec K5: iki liste).
    D.kosul("10.4: kart A'nin 24 V telleri tek tabloda (eski kablo tablosu tekrar etmiyor)",
            "Bağlanacak kablolar" not in h104 and all(f"kart A {c} teli" in html_unescape(h104) for c in ("C34", "C36")))
    # 10.4 metnindeki LED -> COM uzunlugu ELLE yazilmis "36 mm"di (yalniz x farki); kablo 9 cm.
    led = next(k_ for k_ in kl if (k_["a"], k_["b"]) == ("LED1.K", "J1.2.L"))
    D.kosul("10.4: GUC lambasi katot kablosunun boyu metinde tablodakiyle ayni (elle mm yok)",
            f"kablo {led['no']}, {kesim_cm(guzergah(led))} cm" in html_unescape(h104)
            and "LED'den 36 mm" not in html_unescape(h104))
    for no in ("10.3", "10.4", "11.1"):
        s_ = adm[no]
        sv = cizimler(s_)
        tb = kablo_b73_tablosu(no)
        beklenen = {f"t:{k['a']}|{k['b']}" for k in adim_kablolari(no)}
        cizimde = {html_unescape(x) for x in re.findall(r'class="bi kb" data-bi="([^"]+)"', sv)}
        tabloda = {html_unescape(x) for x in re.findall(r'class="bi-satir" data-bi="([^"]+)"', tb)}
        rozet = len(re.findall(r'class="kno-r"', sv))
        D.kosul(f"{no}: cizimdeki, tablodaki ve listedeki kablolar AYNI kume; her kablonun bir rozeti var",
                beklenen <= cizimde and tabloda == beklenen
                and rozet == len(beklenen) + sum(any(p[1] > 45 for p in guzergah(k)) for k in adim_kablolari(no)),
                f"liste {len(beklenen)} · cizim {len(cizimde & beklenen)} · tablo {len(tabloda)} · rozet {rozet}")
    # Review Focus 1 (B73): bitisik uclarda rozetler ve 'ön →' yazilari ust uste binmemeli.
    cakisan = []
    for no in ("10.3", "10.4", "11.1"):
        for ad, sv in (("iç", ciz_arka_ic(set(), no)), ("kuş", ciz_yerlesim(set(), kablo_adim=no))):
            rz = [(float(a), float(b)) for a, b in re.findall(r'class="kno-r" cx="([\d.]+)" cy="([\d.]+)"', sv)]
            if any(math.dist(p, q) < 16.0 for i, p in enumerate(rz) for q in rz[i + 1:]):
                cakisan.append(f"{no}/{ad}: rozet")
            yz = [(float(a), float(b), html_unescape(t)) for a, b, t in
                  re.findall(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>(ön → [^<]*)</text>', sv)]
            if any(abs(p[1] - q[1]) < 9 and abs(p[0] - q[0]) < (len(p[2]) + len(q[2])) * 2.4
                   for i, p in enumerate(yz) for q in yz[i + 1:]):
                cakisan.append(f"{no}/{ad}: yazı")
    D.kosul("Rozetler (≥ 16 px arayla) ve 'ön →' yazilari ust uste binmiyor", not cakisan, f"{cakisan}")
    # x KONUMUNA bakilir: ilk surum yazilarin belgedeki SIRASINA bakiyordu (SARJ hep once
    # yaziliyor) ve aynali cizimde de geciyordu — mutasyon kosucusu yakaladi (B73).
    sv_ic = ciz_arka_ic(set(), "10.3")
    ox = {t: float(x) for x, t in re.findall(r'<text x="([\d.]+)"[^>]*>(ŞARJ|USB)</text>', sv_ic)}
    D.kosul("Arka duvar kablo cizimi ICERIDEN (aynasiz): SARJ ovali USB'nin SOLUNDA (x)",
            {"ŞARJ", "USB"} <= set(ox) and ox["ŞARJ"] < ox["USB"], str(ox))
    sah_k = [b for b in sahne() if b["g"] == "kablo"]
    ix3 = {s["no"]: i for i, s in enumerate(alt_adimlar())}
    bozuk3 = []
    for k in kl:
        bl = [b for b in sah_k if b["k"] == f"t:{k['a']}|{k['b']}"]
        toplam = sum(max(b["dx"], b["dy"], b["dz"]) - 2.0 for b in bl)
        if not bl or abs(toplam - guzergah_boyu(guzergah(k))) > 0.6 or any(b["gor"] != ix3[k["adim"]] for b in bl):
            bozuk3.append(k["no"])
    D.kosul("3B: her kablo guzergahiyla ayni boyda bloklar zinciri ve kendi adiminda beliriyor",
            not bozuk3, f"bozuk: K{bozuk3}" if bozuk3 else f"{len(sah_k)} blok")
    kart_t = [k for k in _BILGI if k.startswith("t:")]
    D.kosul("Her kablonun karti kesim boyu, yol ve '±3 mm tahmin' notu tasiyor",
            kart_t and all(_BILGI[k]["r"][0][0] == "Kesim boyu" and "±3 mm" in _BILGI[k].get("n", "")
                           and any(r[0] == "Yol" for r in _BILGI[k]["r"]) for k in kart_t), f"{len(kart_t)} kart")
    return D


def _kullanilan_kutle() -> set[str]:
    """Kutle tablosundan gercekten kullanilan anahtarlar (olu satir denetimi)."""
    k = {p["ref"] for p in K.IC_PARCA} | {d["ref"] for d in K.DUVAR_PARCA} | {"HÜCRE", "KABLO"}
    return k | {kutle_anahtari(x) for x in panel_ogeleri() if x["tip"] != "yuva"}


# ═══════════════════════════════════════════════════════════════════════
#  CIZIM — yardimcilar
# ═══════════════════════════════════════════════════════════════════════

def _svg(ic: str, gen: float, yuk: float, baslik: str) -> str:
    return (f'<svg viewBox="0 0 {gen:.0f} {yuk:.0f}" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="ui-monospace,Consolas,monospace" role="group" aria-label="{E(baslik)}">'
            f'<title>{E(baslik)}</title>{ic}</svg>')


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
    for i, x in enumerate(parcalar):
        ad, u, adet, kaynak = x["ad"], x["u"], x["adet"], x["kaynak"]
        y = ust + i * satir
        o.append(_bi_ac(bi_kesim(x)))                    # B57: satir = kart
        o.append(_dikdortgen(sol, y, c["uzunluk"] * olc, 20, "var(--yz2)", "var(--cizgi)"))
        for ux in (sol, sol + (c["uzunluk"] - c["uc_egim"]) * olc):
            o.append(_dikdortgen(ux, y, c["uc_egim"] * olc, 20, "#8a8a85", "var(--cizgi)", 0.45))
        bas = sol + (c["uc_egim"] * olc if kaynak == "duz" else 0)
        o.append(_dikdortgen(bas, y, u * olc, 20, AHSAP["on"], AHSAP["cizgi"]))
        if kaynak == "tek_uc":
            o.append(_yazi(sol + (u + (c["uzunluk"] - u) / 2) * olc, y + 14, "artan (düz)", 9, "var(--m3)"))
        if kaynak == "yarim":
            o.append(_dikdortgen(bas + h["yarim"] * olc, y, u * olc, 20, AHSAP["ust"], AHSAP["cizgi"]))
            o.append(_yazi(bas + h["yarim"] * olc + u * olc / 2, y + 14, "2. yarım", 9, "#2b2b2b"))
        o.append(_yazi(sol - 10, y + 14, ad[:44], 10, "var(--m1)", "end"))
        o.append(_yazi(bas + u * olc / 2, y + 14, f"{u:.0f}", 10, "#2b2b2b"))
        o.append(_yazi(sol + c["uzunluk"] * olc + 10, y + 14, f"× {adet}", 11, "var(--m1)", "start", True))
        kalan = h["duz"] - u if kaynak == "duz" else 0.0
        if kaynak == "tek_uc":
            kalan = 0.0
        if kalan > 14:
            o.append(_yazi(bas + (u + kalan / 2) * olc, y + 14, f"artan {kalan:.0f}", 9, "var(--m3)"))
        o.append("</g>")
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
            o.append(_bi(bi_sira("kapak" if kapak else "taban", i, boy, h["dis_en"]),
                         _dikdortgen(sol + bas * olc, y, boy * olc - 1, g * olc - 1, AHSAP["ust"], AHSAP["cizgi"])
                         + _yazi(sol + (bas + boy / 2) * olc, y + g * olc / 2 + 4, f"{boy:.0f}", 9, "#5a4a2a")))
    if kapak:
        for r in kapak_raylari():
            x = sol + (r["x"] + h["duvar_t"]) * olc
            o.append(_bi(bi_kapak_ray(r),
                         _dikdortgen(x - 1, ust + (r["y"] + h["duvar_t"]) * olc, c["kalinlik"] * olc + 2, r["boy"] * olc,
                                     VURGU["on"], VURGU["cizgi"], 0.9)))
        for y in K.KUTU["kapak_civata_y"]:
            for x in (0.0, K.KUTU["ic_en"]):
                cx, cy = sol + (x + h["duvar_t"]) * olc, ust + (y + h["duvar_t"]) * olc
                o.append(_bi(bi_kapak_civata(), f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#333" stroke="var(--yz)"/>'))
    else:
        for rx in TABAN_RAY_X:
            x = sol + h["dis_en"] * rx * olc - g * olc / 2
            ek = h["dis_boy"] * TABAN_EK[0 if rx < 0.5 else 1]
            for bas, boy in ((0.0, ek), (ek, h["dis_boy"] - ek)):
                o.append(_bi(bi_ray(rx, boy, h["dis_boy"]),
                             _dikdortgen(x, ust + bas * olc, g * olc, boy * olc - 1, VURGU["on"], VURGU["cizgi"], 0.85)))
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


def ciz_agirlik(hucre: int = 2) -> str:
    """Kusbakisi denge cizimi: destek bandi, agir kalemler, agirlik merkezi."""
    h, am = hesap(), agirlik_merkezi(hucre)
    olc, sol, ust = 1.7, 44.0, 46.0
    gen, yuk = sol * 2 + h["dis_en"] * olc, ust * 2 + h["dis_boy"] * olc
    X = lambda v: sol + v * olc
    Y = lambda v: ust + v * olc
    o = [_dikdortgen(X(0), Y(0), h["dis_en"] * olc, h["dis_boy"] * olc, "var(--yz2)", "var(--cizgi)")]
    d0, d1 = am["destek_x"]
    o.append(_dikdortgen(X(d0), Y(0), (d1 - d0) * olc, h["dis_boy"] * olc, VURGU["ust"], "none", 0.16))
    for rx in TABAN_RAY_X:                                   # kutu bu iki rayin uzerinde duruyor
        o.append(_dikdortgen(X(h["dis_en"] * rx - h["g"] / 2), Y(0), h["g"] * olc, h["dis_boy"] * olc,
                             VURGU["on"], VURGU["cizgi"], 0.5))
    buyuk = sorted(am["kalem"], key=lambda k: -k["m"])[:10]
    for k in buyuk:
        if k["grup"] in ("kutu", "kapak"):
            continue
        r = max(4.0, math.sqrt(k["m"]) * 1.6)
        o.append(f'<circle cx="{X(k["x"]):.1f}" cy="{Y(k["y"]):.1f}" r="{r:.1f}" fill="#3d6aa8" '
                 f'fill-opacity="0.35" stroke="#3d6aa8"/>')
        o.append(_yazi(X(k["x"]), Y(k["y"]) - r - 3, f"{k['ad']} {k['m']:.0f} g", 9, "var(--m2)"))
    gx, gy = X(h["dis_en"] / 2), Y(h["dis_boy"] / 2)
    o.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="5" fill="none" stroke="var(--m3)" stroke-dasharray="3 3"/>')
    ax, ay = X(am["x"]), Y(am["y"])
    o.append(_cizgi(ax - 13, ay, ax + 13, ay, "#c8372a", 2.2))
    o.append(_cizgi(ax, ay - 13, ax, ay + 13, "#c8372a", 2.2))
    o.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="7" fill="none" stroke="#c8372a" stroke-width="2.2"/>')
    o.append(_yazi(ax, ay + 24, f"AM  {am['sapma']['x']:+.1f} / {am['sapma']['y']:+.1f} mm", 10, "#c8372a", "middle", True))
    o.append(_yazi(gen / 2, ust - 14, f"Kuşbakışı — ağırlık merkezi, {['pilsiz', 'tek hücre', 'iki hücre'][hucre]} "
                                      f"({am['M']:.0f} g)", 12, "var(--m1)", "middle", True))
    o.append(_yazi(gen / 2, yuk - 24, "sarı = kutunun üzerinde durduğu iki taban rayı (destek açıklığı) · "
                                      "kesikli daire = geometrik merkez · kırmızı = ağırlık merkezi", 10, "var(--m3)"))
    o.append(_yazi(gen / 2, yuk - 10, "üst kenar = ARKA duvar (pil bloğu) · alt kenar = ÖN panel (jaklar)", 10, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Ağırlık merkezi")


def agirlik_html() -> str:
    """'Kutu dengeli mi' bolumu — sayilar agirlik_merkezi()'nden, elle yazilmaz."""
    dg = K.DENGE
    ams = [(agirlik_merkezi(n), ad) for n, ad in ((2, "İki hücre (normal)"),
                                                  (1, "Tek hücre (paket tek hücreyle de çalışır)"),
                                                  (0, "Hücresiz (taşıma / saklama)"))]
    am = ams[0][0]
    satir = [(f"<b>{E(ad)}</b>", f"{a['M']:.0f} g",
              f"{a['sapma']['x']:+.1f} mm", f"{a['sapma']['y']:+.1f} mm",
              f"%{a['ray_pay'][0] * 100:.0f} / %{a['ray_pay'][1] * 100:.0f}",
              f"{min(a['aci'].values()):.0f}°", f"{min(a['kotu_aci'].values()):.0f}°")
             for a, ad in ams]
    grup_ad = {"kutu": "kutunun tahtası", "kapak": "kapak", "parça": "kartlar ve güç parçaları",
               "pil": "pil bloğu (hücreler dahil)", "panel": "panel öğeleri", "kablo": "kablolar"}
    dagilim = _tablo(("Ne", "Kütle", "Pay"),
                     [(E(grup_ad.get(g, g)), f"{m:.0f} g", f"%{m / am['M'] * 100:.0f}")
                      for g, m in sorted(am["grup"].items(), key=lambda x: -x[1])])
    kutle_tablo = _tablo(("Kalem", "Kütle", "± belirsizlik", "Nereden"),
                         [(f"<b>{E(k)}</b>", f"{v[0]:.0f} g", f"%{v[1] * 100:.0f}", E(v[2]))
                          for k, v in K.KUTLE.items()])
    return (_liste([
        f"<b>Sonuç: kutu dengeli.</b> Ağırlık merkezi geometrik merkezden yanlara "
        f"<b>{am['sapma']['x']:+.1f} mm</b>, öne-arkaya <b>{am['sapma']['y']:+.1f} mm</b> kaçıyor "
        f"(kutu {am['dis'][0]:.0f} × {am['dis'][1]:.0f} mm). Bir taraf ağır değil: iki taban rayı "
        f"yükün <b>%{am['ray_pay'][0] * 100:.0f} / %{am['ray_pay'][1] * 100:.0f}</b>'ünü taşıyor.",
        f"Devrilmeye pay bol: kutu her yönde <b>{min(am['aci'].values()):.0f}°</b> eğilene kadar devrilmiyor "
        f"(kütle tahminlerinin en kötü halinde bile {min(am['kotu_aci'].values()):.0f}°). Ağırlık merkezi "
        f"tabandan <b>{am['z']:.0f} mm</b>, yani dış yüksekliğin yüzde {am['z_orani'] * 100:.0f}'ünde — alçak.",
        f"Denge kendiliğinden değil, iki şeyden geliyor: kutunun kendi tahtası toplamın "
        f"<b>%{(am['grup']['kutu'] + am['grup'].get('kapak', 0)) / am['M'] * 100:.0f}</b>'si ve simetrik; "
        "ağır parçalar da zıt yanlarda (ana kart solda, Q1 soğutucusu ve 18650'ler sağda).",
        "<b>Hiçbiri tartılmadı</b> — sayılar hacim × yoğunluk ya da benzerinden kestirme. Bu yüzden denetim "
        "her sonucu bir de kütlelerin <i>en kötü</i> halinde hesaplıyor: her kalemi ağırlık merkezini en çok "
        "kaydıracak yönde sınırına itip tekrar bakıyor. Bir kalemi tartarsan söyle, "
        "<code>kutu_veri.KUTLE</code>'yi günceller, sayıları yeniden üretirim.",
        f"Ölçüt neydi: her ray yükün en az %{dg['ray_pay'] * 100:.0f}'ini taşısın (kötü halde "
        f"%{dg['kotu_ray_pay'] * 100:.0f}), ağırlık merkezi derinlikte orta bölgede kalsın, devrilme açısı "
        f"her yönde ≥ {dg['devrilme_aci']:.0f}°, ağırlık merkezi kutunun yarı yüksekliğinin altında.",
    ])
        + "<figure><figcaption>Destek açıklığı ve ağırlık merkezi</figcaption>" + ciz_agirlik(2) + "</figure>"
        + "<h3>Yapılandırmaya göre</h3>"
        + _tablo(("Yapılandırma", "Toplam", "AM x (yan)", "AM y (derinlik)", "Ray yük payı sol/sağ",
                  "En küçük devrilme açısı", "Kötü halde"), satir)
        + "<p class='kucuk'>AM x/y = ağırlık merkezinin geometrik merkezden sapması; + değer sağa ve öne. "
          "Pil bloğu yoksa ön panelin jakları dengelenmiyor, ağırlık merkezi "
          f"{ams[2][0]['sapma']['y']:+.0f} mm öne kayıyor — devrilme açısı yine "
          f"{min(ams[2][0]['aci'].values()):.0f}°, sorun değil.</p>"
        + "<h3>Kütle nereye dağılıyor</h3>" + dagilim
        + "<h3>Kullanılan kütleler</h3>" + kutle_tablo
        + f"<p class='kucuk'>Çubuk yoğunluğu {K.CUBUK_YOGUNLUK * 1e3:.2f} g/cm³ varsayıldı → bir çubuk "
          f"{K.CUBUK['uzunluk'] * K.CUBUK['genislik'] * K.CUBUK['kalinlik'] * K.CUBUK_YOGUNLUK:.1f} g. "
          "<b>10 çubuğu tartıp söyle</b> (÷10): kutunun tahtası toplamın en büyük parçası, en çok bu sayı "
          "önemli.</p>")


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


def ciz_panel(hangi: str, vurgu: set[str], ic_kat: bool = True, duvar_parca: bool = False) -> str:
    """Duvar gorunusu DISARIDAN: dis kat siralari, ek yerleri, ic kat cubuklari, delikler.
    Arka duvar aynali: kullanici arkaya gecince x'i kendi solundan sayar."""
    kb, h = K.KUTU, hesap()
    g, dt = h["g"], h["duvar_t"]
    olc, sol, ust = 2.0, 40.0, 34.0
    satirlar = sorted({int(q["z"] // g) for q in panel_ogeleri(hangi)})   # etiket satiri = delik sirasi
    gen, yuk = sol * 2 + h["dis_en"] * olc, ust + h["ic_yuk"] * olc + 74 + 50 * len(satirlar)
    taban_y = ust + h["ic_yuk"] * olc
    ayna = hangi == "arka"

    def X(x_ic):                               # ic koordinat -> ekran (dis kenardan)
        xo = x_ic + dt
        return sol + (arka_ayna(xo) if ayna else xo) * olc
    o = []
    ekler = ek_yerleri(hangi)
    for r in range(kb["duvar_sira"]):
        y = taban_y - (r + 1) * g * olc
        o.append(_bi(bi_satir(hangi, r), _dikdortgen(sol, y, h["dis_en"] * olc, g * olc - 1, AHSAP["on"], AHSAP["cizgi"])))
        ex = sol + (arka_ayna(ekler[r]) if ayna else ekler[r]) * olc
        o.append(_cizgi(ex, y + 1, ex, y + g * olc - 2, VURGU["cizgi"], 2.0))
        o.append(_yazi(ex, y + 8, f"ek {(arka_ayna(ekler[r]) if ayna else ekler[r]):.0f}", 8, "var(--m3)"))
        o.append(_yazi(sol - 8, y + g * olc / 2 + 4, f"{r + 1}", 10, "var(--m3)", "end"))
    if ic_kat:
        for x0, w, z0 in ic_kat_cubuklari(hangi):
            xa, xb = X(x0), X(x0 + w)
            o.append(_bi(bi_ic_kat(hangi, x0, w, z0),
                         f'<rect x="{min(xa, xb) + 1.5:.1f}" y="{ust + z0 * olc + 1:.1f}" width="{abs(xb - xa) - 3:.1f}" '
                         f'height="{(h["ic_yuk"] - z0) * olc - 2:.1f}" rx="2" fill="rgba(255,255,255,.10)" '
                         f'stroke="var(--m1)" stroke-width="1.2" stroke-dasharray="4 3"/>'))
            o.append(_yazi((xa + xb) / 2, ust - 2, f"{x0:.0f}", 8, "var(--m3)"))
    if duvar_parca:                            # ic yuze asili parcalar (disaridan bakinca konumu)
        for d in [q for q in duvar_parcalari() if q["duvar"] == hangi]:
            xa, xb = X(d["x"]), X(d["x"] + d["en"])
            v = d["ref"] in vurgu
            o.append(_bi(bi_duvar(d),
                         _dikdortgen(min(xa, xb), taban_y - (d["z"] + d["yuk"]) * olc, abs(xb - xa), d["yuk"] * olc,
                                     "#3c6e71", "#f2c14e" if v else "#1f3f41", 0.75)
                         + _yazi((xa + xb) / 2, taban_y - (d["z"] + d["yuk"] / 2) * olc + 4, d["ref"], 10, "#fff", "middle", v)))
    sira_sayac: dict[int, int] = {}                # ayni siradaki komsu etiketler bir asagi bir yukari
    for i, x in enumerate(sorted(panel_ogeleri(hangi), key=lambda q: -q["x"] if ayna else q["x"])):
        cx, cy = X(x["x"]), taban_y - x["z"] * olc
        r_ = int(x["z"] // g)
        sira_sayac[r_] = sira_sayac.get(r_, 0) + 1
        v = x["ref"] in vurgu
        renk = JAK_RENK.get(x["renk"], "#8a8a85")
        o.append(_bi_ac(bi_panel(x)))                    # B57: delik + etiketleri tek kart
        if x["tip"] == "yuva":
            o.append(_dikdortgen(cx - x["yuva_en_mm"] / 2 * olc, cy - x["delik_mm"] / 2 * olc,
                                 x["yuva_en_mm"] * olc, x["delik_mm"] * olc, "var(--yz)", "#f2c14e" if v else "var(--m3)", 1, 6))
        else:
            r = max(x["metal_mm"], x["delik_mm"]) / 2 * olc
            o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{renk}" stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{3 if v else 1.2}" opacity=".95"/>')
            o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{x["delik_mm"] / 2 * olc:.1f}" fill="var(--yz)" opacity=".6"/>')
        kay = 50 * satirlar.index(r_) + (24 if sira_sayac[r_] % 2 == 0 else 0)   # sira basina satir, komsular kaydirmali
        o.append(_yazi(cx, taban_y + 16 + kay, x["etiket"], 10, "var(--m1)", "middle", v))
        xo = x["x"] + dt
        o.append(_yazi(cx, taban_y + 28 + kay, f"x {(arka_ayna(xo) if ayna else xo):.0f} · z {x['z']:.0f}", 9, "var(--m3)"))
        o.append("</g>")
    o.append(_dikdortgen(sol, taban_y, h["dis_en"] * olc, 5, AHSAP["yan"], AHSAP["cizgi"]))
    alt_y = taban_y + 22 + 50 * len(satirlar)
    o.append(_yazi(sol + h["dis_en"] * olc / 2, alt_y,
                   f"{'Arka' if ayna else 'Ön'} duvar — DIŞARIDAN bakış · x dış sol kenardan"
                   + (" (arkaya geçince kendi solun)" if ayna else ""), 10, "var(--m3)"))
    o.append(_yazi(sol + h["dis_en"] * olc / 2, alt_y + 14,
                   "turuncu çizgi = dış kat ek yeri" + (" · kesikli = iç kat dikey çubuk (iç yüzde, üstte sol kenarı)"
                                                       if ic_kat else ""), 10, "var(--m3)"))
    o.append(_yazi(sol + h["dis_en"] * olc / 2, ust - 14, f"{h['dis_en']:.0f} mm (dış)", 11))
    return _svg("".join(o), gen, yuk, f"{hangi} duvar")


def _adim_sirasi() -> dict[str, int]:
    return {s["no"]: i for i, s in enumerate(alt_adimlar())}


ROZET_ARA = 18.0      # px — iki numara rozetinin merkezleri arasi en az (r = 8)


def _rozet_yeri(noktalar: list[tuple[float, float]], yerlesik: list[tuple[float, float]]) -> tuple[float, float]:
    """Rozet icin kablonun UZERINDE, oncekilere en az ROZET_ARA uzak bir nokta. Adaylar:
    parcalar uzundan kisaya, her parcada orta / ceyrek / uc yakini. Hicbiri uzak degilse
    en uzak aday (bitisik B0505S bacaklari gibi sikisik yerde en az kotu yer)."""
    adaylar = []
    for p, q in sorted(zip(noktalar, noktalar[1:]), key=lambda s: -math.dist(s[0], s[1])):
        if math.dist(p, q) < 6.0:
            continue
        for t in (0.5, 0.3, 0.7, 0.15, 0.85):
            adaylar.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    adaylar = adaylar or [noktalar[len(noktalar) // 2]]

    def bosluk(c):
        return min((math.dist(c, r) for r in yerlesik), default=1e9)
    sec = next((c for c in adaylar if bosluk(c) >= ROZET_ARA), max(adaylar, key=bosluk))
    yerlesik.append(sec)
    return sec


def _kablo_svg(k: dict, noktalar: list[tuple[float, float]], soluk: bool,
               yerlesik: list[tuple[float, float]] | None = None, rozet: bool = True) -> tuple[str, str]:
    """Bir kablonun 2B izdusumu: (cizgi grubu, rozet grubu). Rozet AYRI grupta (ayni data-bi)
    cunku cagiran onu butun cizgilerden SONRA yazar — sonraki kablonun cizgisi numarayi ortmesin.
    soluk = onceki adim (rozetsiz). `yerlesik`: ayni cizimdeki rozet merkezleri (paylasilir)."""
    renk = KABLO_RENK[k["rol"]]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in noktalar)
    ac = _bi_ac(bi_kablo(k)).replace('class="bi"', 'class="bi kb"', 1)
    cizgi = (ac + f'<polyline points="{pts}" fill="none" stroke="{renk}" stroke-width="3" '
             f'stroke-linejoin="round" stroke-linecap="round" opacity="{0.22 if soluk else 1.0}"/></g>')
    if soluk or not rozet:
        return cizgi, ""
    mx, my = _rozet_yeri(noktalar, yerlesik if yerlesik is not None else [])
    return cizgi, (ac + f'<circle class="kno-r" cx="{mx:.1f}" cy="{my:.1f}" r="8" fill="{renk}" stroke="#fff" '
                   f'stroke-width="1.2"/>' + _yazi(mx, my + 3.5, str(k["no"]), 9, "#fff", "middle", True) + "</g>")


def _yazi_istif(x: float, y: float, metin: str, yerlesik: list[tuple[float, float, float]]) -> float:
    """Ust uste binen 'ön →' yazisini 10 px yukari kaydirir (8 px monospace ~ 4.8 px/harf)."""
    w = len(metin) * 4.8
    while any(abs(y - yy) < 9 and abs(x - xx) < (w + ww) / 2 for xx, yy, ww in yerlesik):
        y -= 10.0
    yerlesik.append((x, y, w))
    return y


def ciz_arka_ic(vurgu: set[str], adim_no: str) -> str:
    """B73: arka duvar ICERIDEN (jak tarafindan bakis, x soldan, AYNASIZ) + bu adima kadarki
    kablolar (onceki adimlar soluk). Arka duvara inmeyen uclar 'ön →' yazisi alir."""
    kb, h = K.KUTU, hesap()
    olc, sol, ust = 3.0, 30.0, 26.0
    W, H = kb["ic_en"], h["ic_yuk"]
    gen, yuk = sol * 2 + W * olc, ust + H * olc + 110

    def X(x):
        return sol + x * olc

    def Z(z):
        return ust + (H - z) * olc
    o = [_dikdortgen(sol, ust, W * olc, H * olc, AHSAP["on"], AHSAP["cizgi"], 0.55)]
    for x in panel_ogeleri("arka"):
        if x["tip"] == "yuva":
            o.append(_dikdortgen(X(x["x"] - x["yuva_en_mm"] / 2), Z(x["z"] + x["delik_mm"] / 2),
                                 x["yuva_en_mm"] * olc, x["delik_mm"] * olc, "var(--yz)", "var(--m3)", 0.9, 6)
                     + _yazi(X(x["x"]), Z(x["z"]) + 4, x["etiket"], 9, "var(--m2)"))
    A = next(p for p in K.IC_PARCA if p["ref"] == "A")
    za = next(a["yuk"] for a in ayaklar() if a["sahip"] == "A")
    o.append(_cizgi(X(A["x"]), Z(za), X(A["x"] + A["en"]), Z(za), "var(--m3)", 1.4, kesik=True)
             + _yazi(X(A["x"] + A["en"] / 2), Z(za) + 12, "kart A'nın arka kenarı (duvardan 12 mm önde)", 9, "var(--m3)"))
    e = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
    ze = next((a["yuk"] for a in ayaklar() if a["sahip"] == "ESP32"), 0.0)
    o.append(_dikdortgen(X(e["x"]), Z(ze + e["yuk"]), e["en"] * olc, e["yuk"] * olc, "none", "var(--m3)", 0.8)
             + _yazi(X(e["x"] + e["en"] / 2), Z(ze + e["yuk"]) - 4, "ESP32 (önde)", 9, "var(--m3)"))
    for d in [q for q in duvar_parcalari() if q["duvar"] == "arka"]:
        v = d["ref"] in vurgu
        o.append(_bi(bi_duvar(d), _dikdortgen(X(d["x"]), Z(d["z"] + d["yuk"]), d["en"] * olc, d["yuk"] * olc,
                                              "#3c6e71", "#f2c14e" if v else "#1f3f41", 0.85)
                     + _yazi(X(d["x"] + d["en"] / 2), Z(d["z"] + d["yuk"] / 2) + 4, d["ref"], 10, "#fff", "middle", v)))
    sira = _adim_sirasi()
    rozetler: list[tuple[float, float]] = []
    yazilar: list[tuple[float, float, float]] = []
    ust_kat: list[str] = []                       # rozetler + yazilar: butun cizgilerin USTUNE
    for k in kablo_listesi():
        if sira[k["adim"]] > sira[adim_no]:
            continue
        yol = guzergah(k)
        cz, rz = _kablo_svg(k, [(X(p[0]), Z(p[2])) for p in yol], soluk=k["adim"] != adim_no, yerlesik=rozetler)
        o.append(cz)
        ust_kat.append(rz)
        if k["adim"] == adim_no:
            for u, p in ((k["a"], yol[0]), (k["b"], yol[-1])):
                if p[1] > 45:
                    metin = f"ön → {uc_adi(u)}"
                    ust_kat.append('<g class="kb-yazi">' + _yazi(X(p[0]), _yazi_istif(X(p[0]), Z(p[2]) - 10, metin, yazilar),
                                                                 metin, 8, KABLO_RENK[k["rol"]]) + "</g>")
    o.extend(ust_kat)
    ly = ust + H * olc + 22
    for i, (r, ad) in enumerate(K.KABLO_ROL_AD.items()):
        lx, lyy = sol + (i % 3) * 215, ly + (i // 3) * 16
        o.append(_cizgi(lx, lyy, lx + 26, lyy, KABLO_RENK[r], 3) + _yazi(lx + 32, lyy + 4, ad, 10, "var(--m2)", "start"))
    o.append(_yazi(sol + W * olc / 2, ly + 46, "arka duvar İÇERİDEN · jak tarafından bakış · x soldan, z yerden · "
                   "soluk = önceki adımların kabloları · uç yerleri ±3 mm tahmin", 10, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Arka duvar içeriden — kablolar")


def ciz_yerlesim(vurgu: set[str], direk_vurgu: bool = False, kablo_adim: str | None = None) -> str:
    kb, h = K.KUTU, hesap()
    dt = h["duvar_t"]
    olc, sol, ust = 1.7, 46.0, 46.0
    gen, yuk = sol * 2 + kb["ic_en"] * olc, ust * 2 + kb["ic_boy"] * olc + 76
    o = [_dikdortgen(sol - dt * olc, ust - dt * olc, h["dis_en"] * olc, h["dis_boy"] * olc, AHSAP["yan"], AHSAP["cizgi"]),
         _dikdortgen(sol - dt * olc / 2, ust - dt * olc / 2, (kb["ic_en"] + dt) * olc, (kb["ic_boy"] + dt) * olc, AHSAP["on"], AHSAP["cizgi"]),
         _dikdortgen(sol, ust, kb["ic_en"] * olc, kb["ic_boy"] * olc, "var(--yz2)", "var(--cizgi)")]
    for d in direkler():
        o.append(_bi(bi_direk(d), _dikdortgen(sol + d["x"] * olc, ust + d["y"] * olc, d["en"] * olc, d["boy"] * olc,
                                              VURGU["on"] if direk_vurgu else AHSAP["yan"],
                                              VURGU["cizgi"] if direk_vurgu else AHSAP["cizgi"])))
    for a in ayaklar():
        v = a["sahip"] in vurgu or a["ref"] in vurgu
        o.append(_bi(bi_ayak(a), _dikdortgen(sol + a["x"] * olc, ust + a["y"] * olc, a["en"] * olc, a["boy"] * olc,
                                             VURGU["ust"] if v else AHSAP["ust"], AHSAP["cizgi"], 0.9)))
    for p in K.IC_PARCA:
        v = p["ref"] in vurgu
        x, y = sol + p["x"] * olc, ust + p["y"] * olc
        o.append(_bi(bi_parca(p), _dikdortgen(x, y, p["en"] * olc, p["boy"] * olc, PARCA_RENK.get(p["ref"], "#666"),
                                              "#f2c14e" if v else "var(--cizgi)", 0.95 if v else 0.5)
                     + _yazi(x + p["en"] * olc / 2, y + p["boy"] * olc / 2 + 4, p["ref"], 11, "#fff", "middle", v)))
    for q in panel_ogeleri():
        hac = panel_hacim(q)
        if hac:
            o.append(_bi(bi_panel(q), _dikdortgen(sol + hac["x"] * olc, ust + hac["y"] * olc, hac["en"] * olc,
                                                  hac["boy"] * olc, "none", "var(--m3)", 0.7)))
    # B65b: duvara asili moduller ayni x'te farkli yukseklikte (IZ/KL/F0, CB/MT1/MT2/TP1) — etiketleri
    # ust uste biniyordu. Acgozlu satir atama: etiketi oncekilerle yatayda ortusen bir alt satira iner.
    yerlesen: list[tuple[float, float, int]] = []
    for d in sorted(duvar_parcalari(), key=lambda q: -q["z"]):
        v = d["ref"] in vurgu
        yazi = f"{d['ref']} z{d['z']:.0f}"
        mx = sol + (d["x"] + d["en"] / 2) * olc
        yari = len(yazi) * 2.6 + 2
        satir = 0
        while any(r == satir and a < mx + yari and mx - yari < b for a, b, r in yerlesen):
            satir += 1
        yerlesen.append((mx - yari, mx + yari, satir))
        o.append(_bi(bi_duvar(d), _dikdortgen(sol + d["x"] * olc, ust + d["y"] * olc, d["en"] * olc, d["boy"] * olc,
                                              "#3c6e71" if v else "none", "#f2c14e" if v else "#3c6e71", 0.85 if v else 1.0)
                     + _yazi(mx, ust + d["y"] * olc + 11 + 10 * satir, yazi, 8, "#fff" if v else "var(--m2)")))
    # B65b: on panelde AYNI x'te uc oge var (CAL/V/YUK 1 x 143, SKOP/HV/YUK 2 x 179 — B59 izgarasi).
    # Kusbakisinda ust uste dusup etiketleri "HVÜK 2", "YÖK1" gibi okunmaz oluyordu. Ayni x'tekiler
    # grup: daireler yan yana, etiketler paneldeki sirayla (usttekiler once) alt alta.
    on_grup: dict[float, list] = {}
    for x in panel_ogeleri("ön"):
        on_grup.setdefault(round(x["x"], 1), []).append(x)
    for grup in on_grup.values():
        grup.sort(key=lambda q: -q["z"])
        n = len(grup)
        for k, x in enumerate(grup):
            cx = sol + x["x"] * olc + (k - (n - 1) / 2) * 11
            v = x["ref"] in vurgu
            o.append(_bi(bi_panel(x),
                         f'<circle cx="{cx:.1f}" cy="{ust + kb["ic_boy"] * olc + 6:.1f}" r="5" fill="{JAK_RENK.get(x["renk"], "#888")}" stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{2 if v else 1}"/>'
                         + _yazi(sol + x["x"] * olc, ust + kb["ic_boy"] * olc + 22 + 11 * k, x["etiket"], 9,
                                 "var(--m1)" if v else "var(--m3)")))
    for i, x in enumerate(sorted(panel_ogeleri("arka"), key=lambda q: q["x"])):
        cx = sol + x["x"] * olc
        v = x["ref"] in vurgu
        o.append(_bi(bi_panel(x),
                     f'<circle cx="{cx:.1f}" cy="{ust - 6:.1f}" r="5" fill="{JAK_RENK.get(x["renk"], "#888")}" stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{2 if v else 1}"/>'
                     + _yazi(cx, ust - (14 if i % 2 == 0 else 26), x["etiket"], 9, "var(--m1)" if v else "var(--m3)")))
    if kablo_adim:                                   # B73: bu adima kadarki kablolar, kusbakisi
        sira = _adim_sirasi()
        rozetler: list[tuple[float, float]] = []
        ust_kat: list[str] = []
        for k in kablo_listesi():
            if sira[k["adim"]] <= sira[kablo_adim]:
                yol = guzergah(k)       # rozet yalniz one uzanan kabloda: arka duvar kablolari burada
                cz, rz = _kablo_svg(k, [(sol + p[0] * olc, ust + p[1] * olc) for p in yol],   # ince seritte
                                    soluk=k["adim"] != kablo_adim, yerlesik=rozetler,
                                    rozet=any(p[1] > 45 for p in yol))
                o.append(cz)
                ust_kat.append(rz)
        o.extend(ust_kat)
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust + kb["ic_boy"] * olc + 62,
                   "kuşbakışı · alt kenar = ön duvar (jaklar) · açık kahverengi = ayak / altlık / köşebent", 10, "var(--m3)"))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust + kb["ic_boy"] * olc + 76,
                   "ince çerçeve = panel parçasının içeri uzanan gövdesi · köşelerde direkler", 10, "var(--m3)"))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust + kb["ic_boy"] * olc + 90,
                   "aynı hizadaki jaklar: daireler soldan sağa, adlar alt alta = panelde üstten alta", 10, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Yerleşim")


def ciz_izo(vurgu: set[str]) -> str:
    c, kb, h = K.CUBUK, K.KUTU, hesap()
    s, o0, gen, yuk = _izo_sigdir(kb["ic_en"], kb["ic_boy"], -c["kalinlik"], h["ic_yuk"])
    o = [_izo_kutu(0, 0, -c["kalinlik"], kb["ic_en"], kb["ic_boy"], c["kalinlik"], o0, s, AHSAP),
         _izo_kutu(0, kb["ic_boy"], 0, kb["ic_en"], h["duvar_t"], h["ic_yuk"], o0, s, AHSAP, 0.9),
         _izo_kutu(kb["ic_en"], 0, 0, h["duvar_t"], kb["ic_boy"], h["ic_yuk"], o0, s, AHSAP, 0.9)]
    for a in ayaklar():
        v = a["sahip"] in vurgu or a["ref"] in vurgu
        o.append(_bi(bi_ayak(a), _izo_kutu(a["x"], a["y"], 0, a["en"], a["boy"], a["yuk"], o0, s, VURGU if v else AHSAP, 0.9)))
    for p in sorted(K.IC_PARCA, key=lambda q: -(q["x"] + q["y"])):
        v = p["ref"] in vurgu
        renk = {"ust": PARCA_RENK.get(p["ref"], "#666"), "on": PARCA_RENK.get(p["ref"], "#666"),
                "yan": PARCA_RENK.get(p["ref"], "#666"), "cizgi": "#111"}
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == p["ref"]), 0.0)
        m = _izo(p["x"] + p["en"] / 2, p["y"] + p["boy"] / 2, z0 + max(p["yuk"] * .5, 6) + 4, o0, s)
        o.append(_bi(bi_parca(p),
                     _izo_kutu(p["x"], p["y"], z0, p["en"], p["boy"], max(p["yuk"] * .5, 6), o0, s, renk, 1.0 if v else 0.42)
                     + _yazi(m[0], m[1], p["ref"], 11, "#fff" if v else "var(--m3)", "middle", v)))
    o.append(_izo_kutu(-h["duvar_t"], 0, 0, h["duvar_t"], kb["ic_boy"], h["ic_yuk"], o0, s, AHSAP, 0.55))
    o.append(_izo_kutu(0, -h["duvar_t"], 0, kb["ic_en"], h["duvar_t"], h["ic_yuk"], o0, s, AHSAP, 0.55))
    o.append(_yazi(gen / 2, yuk - 12, "ön ve sol duvar saydam çizildi (içeriyi görmek için)", 11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "İzometrik")


def ciz_kullanim(hangi: str) -> str:
    """Kullanim semalari: YUK jaklari SERI akim yolu; PIL jaklari desarj yolu.
    COM icin krokodil YOK: COM = YUK 2 (icerde bagli) — sema bunu gosteriyor.

    B61 (kullanici 2026-09-26: "pilin + tarafi nerede, yukun hangi tarafi +"): jak RENGI ve
    ADI panel verisinden (eskiden elle yaziliydi; B60'ta YUK yesil olunca sema siyah kaldi),
    kaynak/yuk/pil kutularinda + ve − isaretli. Her jak dairesi data-jak ile isaretli —
    denetim rengini oradan dogruluyor."""
    KIR, SIY = "#c8372a", "#8a8a85"
    KUTU_Y, UST = 215.0, 60.0
    on = {q["ref"]: q for q in K.PANEL_ON}
    o = []

    def kutu_govde(x1, x2, baslik, alt):
        return (_dikdortgen(x1, KUTU_Y, x2 - x1, 78, "var(--yz2)", "var(--s1)")
                + _yazi((x1 + x2) / 2, KUTU_Y + 34, baslik, 12, "var(--s1)", "middle", True)
                + _yazi((x1 + x2) / 2, KUTU_Y + 54, alt, 10, "var(--m3)"))

    def ucbas(x, ref, etiket=None, alt=None, kat=0):
        q = on[ref]
        k = 26 * kat
        return (f'<circle data-jak="{ref}" cx="{x:.0f}" cy="{KUTU_Y:.0f}" r="6" fill="{JAK_RENK[q["renk"]]}" '
                f'stroke="var(--yz)" stroke-width="1.5"/>'
                + _yazi(x, KUTU_Y - 26 - k, etiket or q["etiket"], 11, "var(--m1)", "middle", True)
                + _yazi(x, KUTU_Y - 12 - k, alt if alt is not None else q.get("alt_etiket", ""), 9, "var(--m3)"))

    def kutup(x, y, isaret):
        renk = KIR if isaret == "+" else "var(--m1)"
        return _yazi(x, y, isaret, 16, renk, "middle", True)
    if hangi == "akim":
        o.append(_dikdortgen(20, 30, 130, 80, "var(--yz2)"))
        o.append(_yazi(85, 62, "KAYNAK", 12, "var(--m1)", "middle", True))
        o.append(_yazi(85, 82, "pil / güç kaynağı", 10, "var(--m3)"))
        o.append(kutup(140, UST - 6, "+")); o.append(kutup(97, 106, "−"))
        o.append(_dikdortgen(420, 30, 150, 80, "var(--yz2)"))
        o.append(_yazi(495, 62, "ÖLÇÜLEN DEVRE", 12, "var(--m1)", "middle", True))
        o.append(_yazi(495, 82, "motor, kart, lamba…", 10, "var(--m3)"))
        o.append(kutup(430, UST - 6, "+")); o.append(kutup(507, 106, "−"))
        o.append(kutu_govde(150, 470, "ÖLÇÜM KUTUSU", f"içeride: {T.SONT_TAKILI * 1e3:.0f} mΩ şönt · COM = YÜK 2"))
        o.append(_cizgi(150, UST, 420, UST, KIR))
        o.append(_yazi(285, UST - 12, "+ hattı: kaynağın + → yükün + (kutuya girmez)", 10, "var(--m3)"))
        o.append(_cizgi(495, 110, 495, 170, SIY)); o.append(_cizgi(495, 170, 430, 170, SIY)); o.append(_cizgi(430, 170, 430, KUTU_Y, SIY))
        o.append(ucbas(430, "J3.1"))
        o.append(_cizgi(190, KUTU_Y, 190, 170, SIY)); o.append(_cizgi(190, 170, 85, 170, SIY)); o.append(_cizgi(85, 170, 85, 110, SIY))
        o.append(ucbas(190, "J3.2"))
        o.append(_cizgi(340, KUTU_Y, 340, 140, KIR, 2.0, True)); o.append(_cizgi(340, 140, 400, 140, KIR, 2.0, True)); o.append(_cizgi(400, 140, 400, UST, KIR, 2.0, True))
        o.append(ucbas(340, "J1.1", "V jakı", "yükün +"))
        o.append(ucbas(260, "J1.2", "COM", "BOŞ — içeride YÜK 2", 1))
        o.append(_cizgi(260, KUTU_Y + 8, 190, KUTU_Y + 8, "var(--s1)", 1.6, True))
        o.append(_yazi(300, 318, "Akım YÜK 1 → şönt → YÜK 2 yolundan geçer (eksi hat).", 11, "var(--m2)"))
        o.append(_yazi(300, 336, "COM'a krokodil takma: yükün eksisine takarsan şönt baypas olur.", 11, "var(--m2)"))
        return _svg("".join(o), 600, 350, "Akım ve gerilim ölçümü")
    o.append(_dikdortgen(20, 30, 130, 90, "var(--yz2)"))
    o.append(_yazi(85, 66, "PİL", 13, "var(--m1)", "middle", True)); o.append(_yazi(85, 88, "≤ 38 V", 10, "var(--m3)"))
    o.append(kutup(140, UST - 6, "+")); o.append(kutup(97, 116, "−"))
    o.append(_dikdortgen(250, 38, 140, 46, "var(--yz2)", "#2f7d5a"))
    o.append(_yazi(320, UST + 6, "YÜK DİRENCİ", 11, "var(--m1)", "middle", True))
    o.append(_yazi(320, 98, "örn. 3.3 Ω 11 W taş direnç", 10, "var(--m3)"))
    o.append(kutu_govde(150, 490, "ÖLÇÜM KUTUSU", "içeride: Q1 anahtarı + şönt · COM = PİL 2"))
    o.append(_cizgi(150, UST, 250, UST, KIR)); o.append(_yazi(200, UST - 12, "pil +", 10, "var(--m3)"))
    o.append(_cizgi(390, UST, 450, UST, KIR)); o.append(_cizgi(450, UST, 450, KUTU_Y, KIR))
    o.append(ucbas(450, "J7.1"))
    o.append(ucbas(190, "J7.2"))
    o.append(_cizgi(190, KUTU_Y, 190, 170, SIY)); o.append(_cizgi(190, 170, 85, 170, SIY)); o.append(_cizgi(85, 170, 85, 120, SIY))
    o.append(_cizgi(350, KUTU_Y, 350, 140, KIR, 2.0, True)); o.append(_cizgi(350, 140, 210, 140, KIR, 2.0, True)); o.append(_cizgi(210, 140, 210, UST, KIR, 2.0, True))
    o.append(ucbas(350, "J1.1", "V jakı", "pilin + — ZORUNLU"))
    o.append(ucbas(260, "J1.2", "COM", "BOŞ — içeride PİL 2", 1))
    o.append(_yazi(300, 318, "Pilin + ucu jaka DEĞİL: direnç üstünden PİL 1'e, ayrıca V'ye.", 11, "var(--m2)"))
    o.append(_yazi(300, 336, "Kart Q1 ile yükü açıp kapatır, kesme geriliminde keser. YÜK boş kalır.", 11, "var(--m2)"))
    return _svg("".join(o), 600, 350, "Pil kapasite testi")


# ═══════════════════════════════════════════════════════════════════════
#  3B SAHNE
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
#  PARCA BILGISI — ipucu kartlari (B57)
# ═══════════════════════════════════════════════════════════════════════
# Kullanici (2026-09-24): "Elimi mouse ile uzerine getirince veya bir tusa
# basinca o parcanin detaylarini gorebilmem lazim — uzunlugu ne kadar, adi ne,
# olculeri ne. Yoksa hangi parca ne, ne kadar uzun anlamak zorlasiyor."
# TEK KAYNAK: her kart VERIDEN uretilir (panel ogesi, ic parca, duvar parcasi,
# ayak, direk, kesim listesi). 3B bloklar 'k' alaniyla, SVG gruplari data-bi
# ile AYNI anahtara bakar; sayfaya tek bir BILGI tablosu gomulur.

_BILGI: dict[str, dict] = {}
_BILGI_STOK = None                                   # yaz() doldurur; yoksa stok satiri yazilmaz
_BILGI_BICIM: dict | None = None                     # yaz() doldurur: adim metinleriyle AYNI sozluk


def _mm(v: float) -> str:
    return f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"


def _duz_metin(s: str, en_cok: int = 220) -> str:
    """HTML etiketlerini sok, bosluklari sadelestir, uzunsa kes (kart kisa kalsin).
    Kaynak notlar yer tutucu tasiyabilir ({hv_kablo}, {yon_b}): adim metinleriyle
    ayni sozlukle BICIMLENIR — ilk surum ciger ciger belgeye sizdiriyordu, belgenin
    yer tutucu kapisi yakaladi (B57)."""
    s = s or ""
    if "{" in s:
        try:
            s = s.format(**(_BILGI_BICIM or {}))
        except (KeyError, IndexError, ValueError):
            s = re.sub(r"\{[a-z_][a-z0-9_]*(?::[^}]*)?\}", "…", s)
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
    return t if len(t) <= en_cok else t[:en_cok - 1].rsplit(" ", 1)[0] + " …"


def _adim_etiket(no: str | None) -> str:
    if not no:
        return ""
    s = next((x for x in alt_adimlar() if x["no"] == no), None)
    return f"{no} · {s['baslik']}" if s else no


def _stok_metin(kayit) -> str:
    """('4mm Born Jak ...', 'Konnektör') -> 'CON030 · Soketler 1 Kutusu' (duz metin)."""
    st = _BILGI_STOK
    if not kayit or st is None or not st.var:
        return ""
    _t, bulunan, _s = st.B.stok_bul(st.kayit, kayit[0], kayit[1], "")
    elde = [r for r in bulunan if (r["adet"] or "").strip() != "0"]
    if not elde:
        return "kayıtta yok"
    kutu_ = sorted({r["konum"] or "yeri kayıtta yok" for r in elde})
    return ", ".join(r["id"] for r in elde[:3]) + " · " + " / ".join(kutu_)


def _bilgi(anahtar: str, baslik: str, tur: str, satirlar, not_: str = "") -> str:
    """Karti kaydet, anahtari dondur. satir: (etiket, deger) ya da (etiket, deger, 1=vurgulu)."""
    r = [[s[0], s[1]] + ([1] if len(s) > 2 and s[2] else []) for s in satirlar if s[1]]
    kart = {"t": baslik, "s": tur, "r": r}
    if not_:
        kart["n"] = _duz_metin(not_)
    _BILGI[anahtar] = kart
    return anahtar


def kesim_bul(aile: str, uzunluk: float) -> dict | None:
    """3B/cizimdeki bir cubuk parcasinin KESIM LISTESINDEKI satiri (aile adi + boy).
    Iki bagimsiz hesap: sahne() geometrisi ve hesap()['parcalar']. Eslesmeyen
    parca = kesim listesinde olmayan parca (B55c'deki '16 parca eksikti' sinifi)."""
    adaylar = [p for p in hesap()["parcalar"]
               # 0.05: YUVARLAMA payi, fazlasi degil. Ilk surum 0.6'ydi ve karta
               # cizimdeki 0.4 mm kisaltilmis boy (110.6) girse bile esliyordu.
               if p["ad"].startswith(aile) and abs(p["u"] - uzunluk) <= 0.05]
    return adaylar[0] if adaylar else None


KAYNAK_ACIK = {"duz": "çubuğun düz bölümünden", "tek_uc": "tek uçlu: yuvarlak uç bir tarafta kalır",
               "yarim": "yarım çubuk: bir çubuktan iki tane"}


def bi_cubuk(baslik: str, aile: str, uzunluk: float, kesit: tuple[float, float], adim: str | None,
             ek: str = "") -> str:
    """Tek bir cubuk parcasi: uzunluk + kesit + kesim listesindeki satiri."""
    kl = kesim_bul(aile, uzunluk)
    return _bilgi(f"c:{baslik}|{uzunluk:.1f}", baslik, f"çubuk parçası · {K.CUBUK['ad']}", [
        ("Uzunluk", f"{_mm(uzunluk)} mm", 1),
        ("Kesit", f"{_mm(kesit[0])} × {_mm(kesit[1])} mm"),
        ("Kesim listesi", f"{kl['ad']} — {_mm(kl['u'])} mm × {kl['adet']}" if kl else "⚠ kesim listesinde YOK"),
        ("Nereden", KAYNAK_ACIK.get(kl["kaynak"], "") if kl else ""),
        ("Adım", _adim_etiket(adim or (kl or {}).get("adim"))),
    ], ek)


def bi_sira(tur: str, i: int, u: float, toplam: float) -> str:
    """Taban / kapak sirasinin bir parcasi. Baslik YONDEN bagimsiz (kisa/uzun) —
    3B ve kusbakisi cizim ayni anahtara baksin, kesim listesiyle ayni dil."""
    kapak = tur == "kapak"
    ad = "Kapak" if kapak else "Taban"
    boy = "kısa" if u <= toplam - u + 1e-6 else "uzun"
    return bi_cubuk(f"{ad} — {i + 1}. sıra, {boy} parça", f"{ad} sırası — {boy}", u, (hesap()["g"], hesap()["t"]),
                    "13.1" if kapak else "2.1")


def bi_ray(rx: float, u: float, toplam: float) -> str:
    boy = "kısa" if u <= toplam - u + 1e-6 else "uzun"
    return bi_cubuk(f"Taban rayı — {'sol' if rx < 0.5 else 'sağ'} ray, {boy} parça", f"Taban rayı — {boy}", u,
                    (hesap()["g"], hesap()["t"]), "2.2", "Tabanın altına, sıralara dik; kutu bu iki rayın üstünde durur.")


def bi_ic_kat(panel: str, x0: float, w: float, z0: float) -> str:
    h = hesap()
    return bi_cubuk(f"İç kat — {panel} duvar, x {_mm(x0)}–{_mm(x0 + w)}", "İç kat", h["ic_yuk"] - z0, (w, h["t"]), "4.5",
                    f"Kısa çubuk: altındaki yuvanın üstünden, z {_mm(z0)} mm'den başlıyor." if z0 else "")


def bi_kapak_ray(r: dict) -> str:
    return bi_cubuk(f"Kapak rayı — {'sol' if r['x'] < K.KUTU['ic_en'] / 2 else 'sağ'}", "Kapak rayı", r["boy"],
                    (r["yuk"], r["en"]), "13.1",
                    f"Yan duvara {_mm(K.KUTU['kapak_ray_payi'])} mm pay bırakarak, 18 mm yüzü dik.")


def bi_panel(o: dict) -> str:
    """Panel ogesi (jak, anahtar, LED, sigorta, yuva, delik, havalandirma, civata)."""
    h = hesap()
    ayna = o["panel"] == "arka"
    xo = o["x"] + h["duvar_t"]
    x_goz = arka_ayna(xo) if ayna else xo
    TUR = {"jak": "born jak", "anahtar": "anahtar / panel parçası", "led": "LED",
           "yuva": "oval yuva (delik)", "kuyruk": "kablo çıkışı", "civata": "cıvata deliği",
           "havalandirma": "havalandırma deliği"}
    delik = (f"{_mm(o['yuva_en_mm'])} × {_mm(o['delik_mm'])} mm oval" if o["tip"] == "yuva"
             else f"Ø{_mm(o['delik_mm'])} mm")
    montaj = monte_adim().get(o["ref"].split(".")[0])
    etiket = o.get("etiket", "") + (f" ({o['alt_etiket']})" if o.get("alt_etiket") else "")
    return _bilgi(f"j:{o['ref']}", o.get("ad") or o.get("etiket") or o["ref"],
                  f"{TUR.get(o['tip'], o['tip'])} · {o['panel']} duvar", [
        ("Panelde yazan", etiket),
        ("Delik", delik, 1),
        ("Metal gövde", f"Ø{_mm(o['metal_mm'])} mm" if o.get("metal_mm") else ""),
        ("İçeri uzantı", f"{_mm(o['derin_mm'])} mm" if o.get("derin_mm") else ""),
        ("Konum", f"x {_mm(x_goz)} · z {_mm(o['z'])} mm  ({int(o['z'] // h['g']) + 1}. sıra)"),
        ("Delindiği adım", _adim_etiket("3.1" if o["panel"] == "ön" else "3.2")),
        ("Takıldığı adım", _adim_etiket(montaj)),
        ("Stok", _stok_metin(o.get("parca"))),
    ], o.get("not", ""))


def bi_parca(p: dict) -> str:
    """Kutunun tabanindaki kart / guc parcasi (IC_PARCA)."""
    z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == p["ref"]), 0.0)
    tas = p.get("tasiyici") or {}
    tasi = (f"{tas.get('adet', '')} × {tas.get('tip', '')}" + (f", {tas['kat']} kat" if tas.get("kat") else "")
            if tas else "")
    return _bilgi(f"p:{p['ref']}", p.get("ad") or p["ref"], "kart / güç parçası · kutunun tabanında", [
        ("Ölçü", f"{_mm(p['en'])} × {_mm(p['boy'])} mm, yükseklik {_mm(p['yuk'])} mm", 1),
        ("Yerden", f"{_mm(z0)} mm (ayak / altlık üstünde)" if z0 else "tabanda"),
        ("Taban izi", f"x {_mm(p['x'])}–{_mm(p['x'] + p['en'])} · y {_mm(p['y'])}–{_mm(p['y'] + p['boy'])} mm (sol-arka iç köşeden)"),
        ("Taşıyıcı", tasi),
        ("Takıldığı adım", _adim_etiket(monte_adim().get(p["ref"]) or tas.get("adim"))),
        ("Stok", _stok_metin(p.get("stok"))),
    ], p.get("nasil", ""))


def bi_duvar(d: dict) -> str:
    """Duvara asili parca (18650 yuvasi, TP4056, MT3608, sigorta yuvasi)."""
    ham = next(q for q in K.DUVAR_PARCA if q["ref"] == d["ref"])
    tt = K.DUVAR_TUTUCU.get(d["ref"])
    ist = K.YAPISTIRMA_ISTISNA.get(d["ref"])
    tut = (f"{ist['yapistirici']} ile yapıştırılı — sökmek: {ist['sokme']}" if ist
           else (f"{tt['ad']}: " + " + ".join(f"{n} × {_mm(u)} mm" for _a, u, n in tutucu_parcalari(tt))
                 + " çubuk" + (f", {_mm(tt['kanal'])} mm bağ kanalı" if tt.get("kanal") else ""))
           if tt and tt.get("parcalar")
           else f"{tt['ad']} × {tt['adet']} ({_mm(tt['uzunluk'])} mm çubuk)" if tt else "cıvatalı (M3, dıştan)")
    return _bilgi(f"d:{d['ref']}", ham.get("ad") or d["ref"], f"duvara asılı · {d['duvar']} duvarın iç yüzü", [
        ("Ölçü", f"{_mm(d['en'])} × {_mm(d['yuk'])} mm, duvardan {_mm(d['boy'])} mm çıkıntı", 1),
        ("Konum", f"x {_mm(d['x'])}–{_mm(d['x'] + d['en'])} · z {_mm(d['z'])}–{_mm(d['z'] + d['yuk'])} mm"),
        ("Tutturma", tut),
        ("Takıldığı adım", _adim_etiket(monte_adim().get(d["ref"]))),
        ("Stok", _stok_metin(ham.get("stok"))),
    ], ham.get("nasil", ""))


def bi_kablo(k: dict) -> str:
    """B73: kablo karti — cizim, 3B ve tablo satiri ayni anahtara bakar."""
    yol = guzergah(k)
    return _bilgi(f"t:{k['a']}|{k['b']}", f"Kablo {k['no']}: {uc_adi(k['a'])} → {uc_adi(k['b'])}",
                  f"kablo · {K.KABLO_ROL_AD[k['rol']]}", [
        ("Kesim boyu", kesim_yazi(k), 1),
        ("Yol", k["soz"]),
        ("Güzergah", f"{guzergah_boyu(yol):.0f} mm"),
        ("Kesit", k["kesit"]),
        ("Adım", _adim_etiket(k["adim"])),
    ], f"{k['not']} · {_uc_notu(k)}")


def bi_ayak(a: dict) -> str:
    """Ayak / altlik / kosebent / kutunun ek blogu."""
    t = K.CUBUK["kalinlik"]
    kat = round(a["yuk"] / t) if a.get("grup") in ("ayak",) else None
    ek = next((e for e in K.KUTU_EK_PARCA if e["ref"] == a["ref"]), None)
    if a.get("kesim_ad"):                    # B65: kizak parcalari kendi satirina (altlik satirina degil)
        kl = next((p for p in hesap()["parcalar"] if p["ad"].startswith(a["kesim_ad"])), None)
    else:
        kl = next((p for p in hesap()["parcalar"] if p["adim"] == a["adim"]
                   and (a["ref"].split("-")[0] in p["ad"] or a["ref"] in p["ad"])), None)
    TUR = {"ayak": "ayak bloğu · gömme M3 somunlu", "altlik": "altlık", "kosebent": "köşebent",
           "blok": "kutunun ek bloğu", "kizak": "ESP32 kızağı · dik şerit, kutu parçası"}
    return _bilgi(f"a:{a['ref']}", a["ref"] + (f" — {a['sahip']} için" if a.get("sahip") else ""),
                  TUR.get(a.get("grup"), "kutu parçası · ahşap"), [
        ("Ölçü", f"{_mm(a['en'])} × {_mm(a['boy'])} mm, yükseklik {_mm(a['yuk'])} mm", 1),
        ("Kat", f"{kat} çubuk üst üste lamine" if kat else ""),
        ("Kesim listesi", f"{kl['ad']} — {_mm(kl['u'])} mm × {kl['adet']}" if kl else ""),
        ("Konum", f"x {_mm(a['x'])} · y {_mm(a['y'])} mm (sol-arka iç köşeden)"),
        ("Adım", _adim_etiket(a.get("adim"))),
    ], (ek or {}).get("nasil", ""))


def bi_direk(d: dict) -> str:
    h = hesap()
    kl = kesim_bul("Köşe direği", h["ic_yuk"])
    return _bilgi(f"k:{d['ref']}", f"Köşe direği {d['ref']}", "kutu iskeleti · lamine çubuk", [
        ("Yükseklik", f"{_mm(h['ic_yuk'])} mm", 1),
        ("Kesit", f"{_mm(d['en'])} × {_mm(d['boy'])} mm ({K.KUTU['direk_kat']} çubuk üst üste)"),
        ("Kesim listesi", f"{kl['ad']} — {_mm(kl['u'])} mm × {kl['adet']}" if kl else "⚠ kesim listesinde YOK"),
        ("Adım", _adim_etiket("4.6")),
    ])


def bi_kapak_civata() -> str:
    kb = K.KUTU
    return _bilgi("x:kapak-civata", f"Kapak cıvatası — {kb['kapak_civata']}", "bağlantı elemanı", [
        ("Cıvata", f"{kb['kapak_civata']} + somun + pul", 1),
        ("Delik", f"Ø{_mm(m3_gecme_cap())} mm, yan duvardan kapak rayına"),
        ("Konum", f"y {' / '.join(_mm(y) for y in kb['kapak_civata_y'])} · z {_mm(kb['kapak_civata_z'])} mm"),
        ("Delindiği adım", _adim_etiket(kb["kapak_civata_delen"]["duvar"])),
        ("Takıldığı adım", _adim_etiket(kb["kapak_civata_takan"])),
    ])


def bi_satir(panel: str, r: int) -> str:
    """Dis kat bir SIRASI (iki parca) — panel ciziminde tek dikdortgen."""
    h = hesap()
    ek = ek_yerleri(panel)[r]
    parca = [(0.0, ek), (ek, h["dis_en"] - ek)]
    aile = f"Dış kat {panel} sıra {r + 1}"
    sat = []
    for i, (_bas, u) in enumerate(parca):
        kl = kesim_bul(aile, u)
        sat.append((("sol" if i == 0 else "sağ") + " parça", f"{_mm(u)} mm" + ("" if kl else " ⚠ listede yok"), 1))
    return _bilgi(f"r:{panel}:{r}", f"Dış kat — {panel} duvar, {r + 1}. sıra", "iki çubuk parçası, ek yeri kaydırmalı", sat + [
        ("Ek yeri", f"x {_mm(arka_ayna(ek) if panel == 'arka' else ek)} mm (dış sol kenardan, bu yüze bakınca)"),
        ("Kesit", f"{_mm(h['g'])} × {_mm(h['t'])} mm"),
        ("Adım", _adim_etiket("4.1" if r == 0 else "4.3")),
    ])


def bi_kesim(p: dict) -> str:
    """Kesim listesi satiri."""
    return _bilgi(f"kl:{p['ad']}", p["ad"], "kesim listesi satırı", [
        ("Uzunluk", f"{_mm(p['u'])} mm", 1),
        ("Adet", f"× {p['adet']}"),
        ("Nereden", KAYNAK_ACIK.get(p["kaynak"], p["kaynak"])),
        ("Adım", _adim_etiket(p["adim"])),
    ])


def _bi_ac(anahtar: str) -> str:
    """Ipucu grubunun ACILIS etiketi — TEK yer. Iki cizim (panel, kesim) grubu elle
    aciyordu; tabindex'i buradan silen bir mutasyon onlari gormuyordu (B57)."""
    return f'<g class="bi" data-bi="{E(anahtar)}" tabindex="0">'


def _bi(anahtar: str, ic: str) -> str:
    """SVG'de bir parcayi (sekil + yazisi) ipucu grubuna sarar; Tab ile odaklanir."""
    return _bi_ac(anahtar) + ic + "</g>"


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

    def blok(ad, x, y, z, dx, dy, dz, renk, grup, gor, vur=None, n=None, on=None, k=None):
        b = {"ad": ad, "x": round(x, 2), "y": round(y, 2), "z": round(z, 2),
             "dx": round(dx, 2), "dy": round(dy, 2), "dz": round(dz, 2),
             "r": renk, "g": grup, "gor": gor, "vur": sorted({v for v in (vur or []) if v is not None})}
        if k:                                    # B57: ipucu karti (BILGI tablosunda)
            b["k"] = k
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
            blok(f"Taban sırası {i + 1}", -dt + bas, y, -t, b2 - 0.4, g - 0.5, t, "#c3a173", "kutu", ix["2.1"], [ix["2.1"]],
                 k=bi_sira("taban", i, b2, h["dis_en"]))
    for rx in TABAN_RAY_X:
        ek = h["dis_boy"] * TABAN_EK[0 if rx < 0.5 else 1]
        for bas, b2 in ((0.0, ek), (ek, h["dis_boy"] - ek)):
            blok("Taban rayı", h["dis_en"] * rx - dt - g / 2, -dt + bas, -2 * t, g, b2 - 0.4, t, "#e0a92f", "kutu", ix["2.2"], [ix["2.2"]],
                 k=bi_ray(rx, b2, h["dis_boy"]))
    for r in range(kb["duvar_sira"]):                       # dis kat: yatay siralar
        z = r * g
        gor = ix["4.1"] if r == 0 else ix["4.3"]
        gor_yan = ix["4.2"] if r == 0 else ix["4.3"]
        for panel, y0, nrm, delme in (("ön", -dt, ON, ix["3.1"]), ("arka", boy + dt - t, ARKA, ix["3.2"])):
            ek = ek_yerleri(panel)[r]
            for bas, b2 in ((0.0, ek), (ek, h["dis_en"] - ek)):
                # arka icin ilk parca (bas=0) ONDEN bakinca soldur = ARKADAN bakinca sag
                taraf = ("sol" if bas == 0 else "sağ") if panel == "ön" else ("sağ (arkadan)" if bas == 0 else "sol (arkadan)")
                blok(f"Dış kat {panel} {r + 1}", -dt + bas, y0, z, b2 - 0.4, t, g, "#c3a173", "duvar", gor, [gor], nrm,
                     on=[delme], k=bi_cubuk(f"Dış kat — {panel} duvar, {r + 1}. sıra, {taraf}",
                                            f"Dış kat {panel} sıra {r + 1} — {taraf}", b2, (g, t),
                                            "4.1" if r == 0 else "4.3"))
        ek = yan_ek(r)
        for bas, b2 in ((0.0, ek), (ek, h["yan_dis"] - ek)):
            yan_aile = "Dış kat yan sıra 1" if r == 0 else "Dış kat yan sıra 2"
            for yan, xw, nrm2 in (("sol", -dt, SOL), ("sağ", en + dt - t, SAG)):
                blok(f"Dış kat {yan} {r + 1}", xw, -dt + t + bas, z, t, b2 - 0.4, g, "#b0915f", "duvar", gor_yan, [gor_yan], nrm2,
                     k=bi_cubuk(f"Dış kat — {yan} yan duvar, {r + 1}. sıra", yan_aile, b2, (g, t), "4.2" if r == 0 else "4.3"))
    gi = ix["4.5"]                                          # ic kat: deliklerden turetilmis
    for x0, w, z0 in h["ic_on"]:
        blok("İç kat ön", x0 + 0.2, -t, z0, w - 0.4, t, yuk - z0, "#d5b78a", "duvar_ic", gi, [gi], ON,
             k=bi_ic_kat("ön", x0, w, z0))
    for x0, w, z0 in h["ic_arka"]:
        blok("İç kat arka", x0 + 0.2, boy, z0, w - 0.4, t, yuk - z0, "#d5b78a", "duvar_ic", gi, [gi], ARKA,
             k=bi_ic_kat("arka", x0, w, z0))
    for y0, w in h["ic_yan"]:
        for yan, xw, nrm2 in (("sol", -t, SOL), ("sağ", en, SAG)):
            blok(f"İç kat {yan}", xw, cev(y0, w) + 0.2, 0, t, w - 0.4, yuk, "#c9a877", "duvar_ic", gi, [gi], nrm2,
                 k=bi_cubuk(f"İç kat — {yan} yan duvar, y {_mm(y0)}–{_mm(y0 + w)}", "İç kat", yuk, (w, t), "4.5"))
    gd = ix["4.6"]
    for d in direkler():
        blok(f"Köşe direği {d['ref'][1]}", d["x"], cev(d["y"], d["boy"]), 0, d["en"], d["boy"], yuk, "#a07a48", "direk", gd, [gd],
             k=bi_direk(d))
    for x in panel_ogeleri():                               # delikler: dis yuzde koyu plaka
        on = x["panel"] == "ön"
        w, hh = delik_genislik(x), x["delik_mm"]
        y0 = -dt - 0.3 if on else boy + dt - 0.3
        delme = ix["3.1"] if on else ix["3.2"]
        r = int(x["z"] // g)                                # delik, duvar sirasiyla birlikte gorunur
        gor = ix["4.1"] if r == 0 else ix["4.3"]
        blok(f"delik {x['etiket']}", x["x"] - w / 2, y0, x["z"] - hh / 2, w, 0.6, hh, "#151515", "delik", gor,
             [delme, ix["5.1"]], ON if on else ARKA, on=[delme], k=bi_panel(x))
        # B59b (kullanici 2026-09-26): ic kat da deliniyor (5.1, dis kattaki delik kilavuz) ama
        # 3B'de yalniz DIS yuzde plaka vardi — iceriden bakinca ic kat cubuklari deliksiz
        # gorunuyordu. Ic yuze de plaka; USB/SARJ yuvalarinin arkasindaki cubuk KISA (yuvanin
        # ustunden basliyor), orada delik yok.
        if x["tip"] not in ("yuva", "kuyruk"):
            yi = -0.3 if on else boy - 0.3
            blok(f"delik {x['etiket']} (iç kat)", x["x"] - w / 2, yi, x["z"] - hh / 2, w, 0.6, hh, "#151515", "delik",
                 ix["5.1"], [ix["5.1"]], ARKA if on else ON, k=bi_panel(x))
    for x in panel_ogeleri():                               # panel ogeleri: govde
        on = x["panel"] == "ön"
        if x["tip"] in ("yuva", "kuyruk"):
            continue
        w = x["metal_mm"] or 12
        gor = ix.get(monte.get(x["ref"].split(".")[0], ""), ix["5.2"])
        renk = JAK_RENK.get(x["renk"], "#8a8a85")
        if on:
            blok(x["etiket"], x["x"] - w / 2, -dt - 14, x["z"] - w / 2, w, dt + 14, w, renk, "panel", gor, vur_ix(x["ref"]),
                 k=bi_panel(x))
            blok(x["etiket"] + " (iç)", x["x"] - w / 4, 0, x["z"] - w / 4, w / 2, x["derin_mm"], w / 2, "#555", "panel", gor, [],
                 k=bi_panel(x))
        else:
            blok(x["etiket"], x["x"] - w / 2, boy, x["z"] - w / 2, w, dt + 14, w, renk, "panel", gor, vur_ix(x["ref"]),
                 k=bi_panel(x))
            blok(x["etiket"] + " (iç)", x["x"] - w / 4, boy - x["derin_mm"], x["z"] - w / 4, w / 2, x["derin_mm"], w / 2, "#555",
                 "panel", gor, [], k=bi_panel(x))
    for a in ayaklar():                                     # ayaklar / altliklar / kosebent / ek bloklar
        vur = [ix[a["adim"]]] + (vur_ix(a["sahip"]) if a["sahip"] else [])
        blok(a["ref"], a["x"], cev(a["y"], a["boy"]), a["z"], a["en"], a["boy"], a["yuk"], "#b8975f", "tasiyici", ix[a["adim"]], vur,
             k=bi_ayak(a))
    for pp in K.IC_PARCA:
        gor = ix.get(monte.get(pp["ref"], ""), None)
        if gor is None:
            gor = {"A": ix["6.2"], "B": ix["6.3"], "ESP32": ix["6.3"]}.get(pp["ref"], ix["6.6"])
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == pp["ref"]), 0.0)
        kz = pp.get("tasiyici", {}).get("kizak")
        if kz:      # B65: govde + ortada dar anten cikintisi (omuz takozlari cikintinin iki yaninda)
            ci = kz["anten_cikinti"]
            blok(pp["ref"], pp["x"], cev(pp["y"], pp["boy"] - ci), z0, pp["en"], pp["boy"] - ci,
                 max(pp["yuk"] * 0.55, 6), PARCA_RENK.get(pp["ref"], "#666"), "parca", gor, vur_ix(pp["ref"]),
                 k=bi_parca(pp))
            blok(pp["ref"] + " (anten)", pp["x"] + (pp["en"] - kz["anten_en"]) / 2,
                 cev(pp["y"] + pp["boy"] - ci, ci), z0, kz["anten_en"], ci, 3.0,
                 PARCA_RENK.get(pp["ref"], "#666"), "parca", gor, vur_ix(pp["ref"]), k=bi_parca(pp))
            continue
        blok(pp["ref"], pp["x"], cev(pp["y"], pp["boy"]), z0, pp["en"], pp["boy"], max(pp["yuk"] * 0.55, 6),
             PARCA_RENK.get(pp["ref"], "#666"), "parca", gor, vur_ix(pp["ref"]), k=bi_parca(pp))
    for d in duvar_parcalari():                             # pil blogu: duvara asili
        gor = ix.get(monte.get(d["ref"], ""), ix["10.2"])       # B58: pil blogu Adim 10'da
        renk = {"YUVA1": "#3c6e71", "YUVA2": "#3c6e71", "TP1": "#284b63", "IZ": "#7a4e9c"}.get(d["ref"], "#5a7d9a")
        blok(d["ref"], d["x"], cev(d["y"], d["boy"]), d["z"], d["en"], d["boy"], d["yuk"], renk, "parca", gor, vur_ix(d["ref"]),
             k=bi_duvar(d))
    for k in kablo_listesi():                               # B73: kablolar — eksen eksen ince bloklar
        gor = ix[k["adim"]]
        yol = guzergah(k)
        for p, q in zip(yol, yol[1:]):
            x0, y0, z0 = (min(p[i], q[i]) - 1.0 for i in range(3))
            dx, dy, dz = (abs(p[i] - q[i]) + 2.0 for i in range(3))
            blok(f"Kablo {k['no']}", x0, cev(y0, dy), z0, dx, dy, dz, KABLO_RENK[k["rol"]], "kablo", gor, [gor],
                 k=bi_kablo(k))
    # Kapak 13.1'de YAPILIR, 13.2'de denenip CIKARILIR, kapanis adiminda takilir:
    # 3B'de 13.1/13.2'de hayalet onizleme (tezgahta hazir ama kutuda degil),
    # takili gorunum kapanistan sonra (B55; B58'den beri kapanis 14.2).
    gk, kapak_on = ix[K.KUTU["kapak_civata_takan"]], [ix["13.1"], ix["13.2"]]
    for i in range(h["taban_sira"]):                        # kapak: siralar x yonunde
        y = -dt + i * g
        ek = taban_ek(i, kapak=True)
        for bas, b2 in ((0.0, ek), (ek, h["dis_en"] - ek)):
            blok(f"Kapak sırası {i + 1}", -dt + bas, y, yuk, b2 - 0.4, g - 0.5, t, "#d9bb8c", "kapak", gk,
                 [ix["13.1"], gk], UST, on=kapak_on,
                 k=bi_sira("kapak", i, b2, h["dis_en"]))
    for r in kapak_raylari():
        blok("Kapak rayı", r["x"], cev(r["y"], r["boy"]), r["z"], r["en"], r["boy"], r["yuk"], "#e0a92f", "kapak", gk,
             [ix["13.1"], ix["13.2"], gk], UST, on=kapak_on,
             k=bi_kapak_ray(r))
    for xw in (-dt - 1.5, en + dt - 1.5):
        for y in kb["kapak_civata_y"]:
            blok("Kapak cıvatası", xw, cev(y, 3), kb["kapak_civata_z"] - 1.6, 3, 3, 3.2, "#333333", "kapak", gk,
                 [ix["13.2"], gk], UST, on=[ix["13.2"]], k=bi_kapak_civata())
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


def kablo_b73_tablosu(no: str) -> str:
    """B73: adimin kablolari, cizimdeki numarayla. Satir data-bi ile karta ve cizime bagli."""
    bas = ("No", "Nereden", "Nereye", "Yol", "Kesim", "Kesit", "Not")
    sat = []
    for k in adim_kablolari(no):
        kesim = "—" if k["rol"] == "bacak" else E(kesim_yazi(k))
        sat.append(f'<tr class="bi-satir" data-bi="{E(bi_kablo(k))}" tabindex="0">'
                   f'<td><span class="kno" style="background:{KABLO_RENK[k["rol"]]}">{k["no"]}</span></td>'
                   f"<td><b>{E(uc_adi(k['a']))}</b></td><td><b>{E(uc_adi(k['b']))}</b></td>"
                   f"<td>{E(k['soz'])}</td><td><b>{kesim}</b></td><td>{E(k['kesit'])}</td>"
                   f"<td><span class='kucuk'>{E(k['not'])}</span></td></tr>")
    return ("<table class='kablo-tablo'><tr>" + "".join(f"<th>{b}</th>" for b in bas) + "</tr>"
            + "".join(sat) + "</table>")


def cizim_panelleri(s: dict) -> list[str]:
    """Bir delik alt adiminda HANGI panel(ler) cizilir — cizim ve denetim ayni kaynaktan.

    Eskiden `cizimler()` sabit `s["panel"]` kullaniyordu: 5.3'un alti ogesinden besi ON
    panelde oldugu halde belge ARKA duvari ciziyordu. Denetim iddiasi da ayni mantigi
    IKINCI KEZ yazdigi icin cizim kodunu degistiren mutasyon KACIYORDU (B55d).
    """
    if s["tur"] == "delik_parca":
        return [s["panel"]]
    ref_panel = {o["ref"]: o["panel"] for o in panel_ogeleri()}
    vurgu = set(s.get("vurgu", [])) | set(s.get("monte", []))
    return sorted({ref_panel[r] for r in vurgu if r in ref_panel}) or ["ön", "arka"]


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
        paneller = cizim_panelleri(s)
        for p in paneller:
            c.append((f"{p.capitalize()} duvar — dışarıdan", ciz_panel(p, vurgu, ic_kat=(tur == "delik"))))
        if vurgu and tur == "delik" and s["no"] != "5.1":
            c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
    elif tur == "montaj":
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
        c.append(("İzometrik", ciz_izo(vurgu)))
    elif tur == "duvar_parca":
        c.append(("Arka duvar — iç yüzdeki parçalar (arkadan bakış; delikler dıştan)", ciz_panel("arka", vurgu, ic_kat=False, duvar_parca=True)))
        c.append(("Ön duvar — iç yüzdeki parçalar", ciz_panel("ön", vurgu, ic_kat=False, duvar_parca=True)))
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
    elif tur == "pil_kablo":
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
        c.append(("Arka duvar — iç yüz", ciz_panel("arka", vurgu, ic_kat=False, duvar_parca=True)))
    elif tur == "kablo":
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
        if any(r in {o["ref"] for o in panel_ogeleri("ön")} for r in vurgu):
            c.append(("Ön duvar", ciz_panel("ön", vurgu, ic_kat=False)))
        if any(r in {o["ref"] for o in panel_ogeleri("arka")} for r in vurgu):
            c.append(("Arka duvar (arkadan bakış)", ciz_panel("arka", vurgu, ic_kat=False)))
    if adim_kablolari(s["no"]):                      # B73: kablo adiminda ana cizim icten arka duvar
        c = ([("Arka duvar — içeriden bakış: bu adımın kabloları", ciz_arka_ic(vurgu, s["no"])),
              ("Kuşbakışı — kablolar", ciz_yerlesim(vurgu, kablo_adim=s["no"]))]
             + [x for x in c if not x[0].startswith(("Kuşbakışı", "Arka duvar"))])
    if not c:
        return ""
    fig = [f"<figure><figcaption>{E(b)}</figcaption>{sv}</figure>" for b, sv in c]
    ana, kalan = fig[0], fig[1:]
    if not kalan:
        return ana
    return ana + (f"<details class='ayrinti'><summary>Diğer çizimler ({len(kalan)})</summary>"
                  + "".join(kalan) + "</details>")


def delik_tablosu_html(panel: str) -> str:
    h = hesap()
    ayna = panel == "arka"
    sat = []
    for d in sorted(delik_tablosu(panel), key=lambda q: (q["sira"], q["parca"], q["ofset"])):
        sat.append((f"<b>{E(d['etiket'])}</b>", f"{d['sira']}", f"{d['parca']} ({d['parca_boy']:.0f} mm)",
                    f"<b>{d['ofset']:.0f} mm</b>", f"{d['z_ic']:.0f} mm", E(d["cap"])))
    ekler = ek_yerleri(panel)
    ek_metin = ", ".join(f"{r + 1}. sıra {(arka_ayna(x) if ayna else x):.0f}" for r, x in enumerate(ekler))
    return (_tablo(("Delik", "Sıra", "Parça", "Merkez: parçanın sol ucundan", "Merkez: çubuğun alt kenarından",
                    "Çap / yuva"), sat)
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


def adim_bicim(h, nl, parcalar) -> dict:
    """Adim metinlerinin yer tutucu sozlugu — TEK KAYNAK.
    B55l: bu sozluk IKI YERDE elle yazilmisti (belge ureteci + denetim) ve
    yenisi eklenince denetim tarafi KeyError ile cokuyordu."""
    kb = K.KUTU
    return {"u": K.CUBUK["uzunluk"], "g": h["g"], "k": h["t"], "sira": kb["duvar_sira"], "h": h["ic_yuk"],
             "ue": K.CUBUK["uc_egim"], "duz": h["duz"], "direk_g": h["g"], "direk_t": h["direk_t"],
             "direk_kat": kb["direk_kat"], "kapak_civata": kb["kapak_civata"], "dis_en": h["dis_en"],
             "dis_boy": h["dis_boy"], "taban_sira": h["taban_sira"], "kapak_ray": h["kapak_ray"],
             "yarim": h["yarim"], "dikey_kaynak": KAYNAK_AD[h["dikey_kaynak"]],
             "cep_cap": K.SOMUN_CEP["cap"], "son_delik": K.SOMUN_CEP["son_kat_delik"],
             "m3_cap": m3_gecme_cap(), **metin_bicim(nl, parcalar), **ayak_bicim(),
             "cep_yapistirici": K.SOMUN_CEP["yapistirici"], "somun_kose": K.M3_SOMUN["kose"],
            "kapak_somun_kat": kb["kapak_somun_kat"],
            "elde": kb["elde_cubuk"], "cubuk": h["cubuk_sayisi"],
            "ray1_x": h["dis_en"] * TABAN_RAY_X[0], "ray2_x": h["dis_en"] * TABAN_RAY_X[1],
            "bag_delik": K.KABLO_BAGI["delik"], "bag_genislik": K.KABLO_BAGI["genislik"],
            "bag_aralik": K.KABLO_BAGI["aralik"],
            "eksik": h["eksik"], "eksik_pay": h["eksik_pay"],
            "sarj_taraf": on_bakis_taraf("SARJ"), "usb_taraf": on_bakis_taraf("USB"), **led_kablo_bicim()}


def led_kablo_bicim() -> dict:
    """10.4: GUC lambasi katot kablosu (LED1.K -> COM kulagi) — numara ve boy tablodan, elle mm yok."""
    k = next(k for k in kablo_listesi() if (k["a"], k["b"]) == ("LED1.K", "J1.2.L"))
    return {"led_k_no": k["no"], "led_k_kesim": kesim_cm(guzergah(k))}


_ESP_KAYMA: dict[int, tuple[float, float]] = {}      # adim_bicim her alt adimda cagriliyor


def esp_kizak_bicim(nl, parcalar) -> dict:
    """B65: 6.3 metninin kizak yer tutuculari — hepsi veriden."""
    p = next(q for q in K.IC_PARCA if q["ref"] == "ESP32")
    kz = p["tasiyici"]["kizak"]
    if id(nl) not in _ESP_KAYMA:
        _ESP_KAYMA[id(nl)] = esp_kayma_payi(nl, parcalar)
    sol, sag = _ESP_KAYMA[id(nl)]
    return {"esp_sol_pay": sol, "esp_sag_pay": sag, "esp_dolu_pin": ", ".join(esp_dolu_pinler(nl)),
            "esp_ray_pay": kz["ray_pay"], "esp_ray_yuk": kz["ray_yuk"], "esp_takoz_boy": kz["takoz_boy"],
            "esp_anten_en": kz["anten_en"], "esp_anten_bosluk": kz["anten_en"] + 2 * kz["anten_pay"]}


def on_bakis_taraf(ref: str) -> str:
    """Arka panel ogesi ONDEN (jak tarafindan) bakinca hangi yarida — veri ekseni x
    zaten onden-soldan (B63: kullanici arkadan cizime bakip TP4056'yi USB ovaline takti)."""
    o = next(q for q in panel_ogeleri() if q["ref"] == ref)
    return "solda" if o["x"] < K.KUTU["ic_en"] / 2 else "sağda"


def alt_kart(s: dict, nl, parcalar, stok, h) -> str:
    kb = K.KUTU
    bicim = {**adim_bicim(h, nl, parcalar), "bu_etiketler": adim_etiketleri(s)}
    ic = [f"<div class='aa-bas'><span class='ano'>{E(s['no'])}</span> <b>{E(s['baslik'])}</b>"
          f"<label class='yaptim'><input type='checkbox'> yaptım</label></div>", "<div class='aa-ic'>"]
    if s.get("monte"):
        def _stok(r):
            kayit = next((o["parca"] for o in panel_ogeleri() if o["ref"].split(".")[0] == r and o["parca"]), None) \
                or next((p.get("stok") for p in K.IC_PARCA if p["ref"] == r), None) \
                or next((d.get("stok") for d in K.DUVAR_PARCA if d["ref"] == r), None)
            alim = next((d.get("alinacak") for d in K.DUVAR_PARCA if d["ref"] == r), None)
            if alim:                                   # B58: stokta olmayan parca bos hucre birakmasin
                return f"<span class='kotu'>stokta YOK — alınacak</span> ({E(alim)})"
            return stok.ad_ile(*kayit) if (kayit and stok.var) else ""
        ic.append(_tablo(("Kutuya giren", "Kural", "Stokta"),
                         [(f"<b>{E(r)}</b>", E((V.KART_DISI_NOTU.get(r) or K.KUTU_NOTU.get(r, "")).format(**metin_bicim(nl, parcalar))),
                           _stok(r)) for r in s["monte"]]))
    if s.get("yap"):
        ic.append(_liste(x.format(**bicim) for x in s["yap"]))
    bu_adim = [x for x in h["parcalar"] if x["adim"] == s["no"]]
    if bu_adim:                                   # kullanici: "o adimda hangi uzunlukta kac tane lazim?"
        toplam = sum(x["adet"] for x in bu_adim)
        ic.append(f"<h4>Bu adımda gereken çubuk parçaları — toplam {toplam}</h4>")
        ic.append(_tablo(("Parça", "Uzunluk", "Adet", "Nereden"),
                         [(E(x["ad"]), f"<b>{x['u']:.0f} mm</b>", f"<b>× {x['adet']}</b>", KAYNAK_AD[x["kaynak"]])
                          for x in bu_adim]))
        ic.append("<details class='ayrinti'><summary>Parçaları çubuk üstünde gör</summary>"
                  "<figure><figcaption>Bu adımın parçaları çubuk üstünde</figcaption>" + ciz_kesim(bu_adim)
                  + "</figure></details>")
    if adim_kablolari(s["no"]):                      # B73: kablolari goster / gizle (2B + 3B tek ayar)
        ic.append("<label class='kucuk kb-ac'><input type='checkbox' class='kb-goster' checked> "
                  "kabloları göster (çizimler ve 3B)</label>")
    ic.append(cizimler(s))
    if s["no"] == "1.2":
        ic.append(_tablo(("Parça", "Uzunluk", "Adet", "Nereden", "Hangi adımda"),
                         [(E(x["ad"]), f"{x['u']:.0f} mm", f"<b>{x['adet']}</b>", KAYNAK_AD[x["kaynak"]], x["adim"])
                          for x in h["kesim1"]]))
        ic.append(f"<div class='uy'>Bütün plan için <b>{h['cubuk_sayisi']} çubuk</b> gerekiyor "
                  f"({KERF:.0f} mm testere payıyla, {h['artik']:.0f} mm artık). Elde ~{kb['elde_cubuk']}: en az "
                  f"<b>{h['eksik']}</b> daha, fire payıyla {h['eksik_pay']}.</div>")
    if s["no"] == "4.4":
        ic.append(_tablo(("Parça", "Uzunluk (nominal)", "Adet", "Nereden", "Hangi adımda"),
                         [(E(x["ad"]), f"{x['u']:.0f} mm", f"<b>{x['adet']}</b>", KAYNAK_AD[x["kaynak"]], x["adim"])
                          for x in h["kesim2"]]))

    if s["tur"] == "delik_parca":
        ic.append("<h4>Delik tablosu — parça parça</h4>")
        ic.append(delik_tablosu_html(s["panel"]))
    if s["no"] in ("4.1", "4.3"):
        ic.append("<details class='ayrinti'><summary>Bütün sıraların parça boyları ve ek yerleri</summary>"
                  + ek_tablosu_html() + "</details>")
    if s["no"] == "4.5":
        ic.append("<h4>İç kat çubuk konumları</h4>")
        ic.append(ic_kat_tablosu_html())
    # B55n: "plandaki yere koy" diyen adimlar sayiyi da gostersin.
    kon = ic_konum_satirlari(s)
    if kon and (s["tur"] == "montaj" or "plandaki yer" in " ".join(s.get("yap", []))):
        ic.append("<h4>Bu adımdaki parçaların yeri — sol-arka iç köşeden (mm)</h4>")
        ic.append(_tablo(("Parça", "x", "y", "en × boy", "yük"), kon))
    if s["no"] in ("4.7", "13.1", kb["kapak_civata_takan"]):     # 4.7 deler (kutu bos), 13.1 blogu civataya merkezler, kapanis kapatir
        ic.append(_tablo(("Duvar", "y (arka dış köşeden)", "z (tabandan)", "Cıvata"),
                         [(d, f"{y + h['duvar_t']:.0f} mm", f"{kb['kapak_civata_z']:.0f} mm", kb["kapak_civata"])
                          for d in ("sol", "sağ") for y in kb["kapak_civata_y"]]))
    # B73 gozden gecirme: numarali kablo tablosunun kart deliklerine giden telleri eski tabloda
    # TEKRAR listelenmez (10.4: J6 -> C34/C36 iki tabloda, eskisinin notu XT30 diyordu).
    b73_delik = {u.split(".", 1)[1] for k_ in adim_kablolari(s["no"]) for u in (k_["a"], k_["b"]) if u.startswith("A.")}
    eski_kablo = [i for i in s.get("kablo", [])
                  if not (kablo_delikleri(i, nl, parcalar) and set(kablo_delikleri(i, nl, parcalar)) <= b73_delik)]
    if eski_kablo:
        ic.append("<h4>Bağlanacak kablolar</h4>")
        ic.append(kablo_tablosu(eski_kablo, nl, parcalar))
    if s["tur"] == "duvar_parca":
        ic.append("<h4>Duvara asılı parçalar — konumlar (iç koordinat, önden bakınca soldan; arka duvar için "
                  "arkadan bakınca sağdan)</h4>")
        ic.append(_tablo(("Parça", "Duvar", "x (sol kenar)", "z (alt kenar)", "en × yük × derin", "Nasıl"),
                         [(f"<b>{E(d['ref'])}</b>", E(d["duvar"]), f"{d['x']:.0f} mm", f"{d['z']:.0f} mm",
                           f"{d['en']:.0f} × {d['yuk']:.0f} × {d['derin']:.0f}", E(d["nasil"])) for d in K.DUVAR_PARCA]))
    if adim_kablolari(s["no"]):                      # B73: numarali kablo tablosu (cizimle ayni kaynak)
        ic.append("<h4>Kablolar — çizimdeki numaralarla (satıra dokun: çizimde yanar)</h4>")
        ic.append(kablo_b73_tablosu(s["no"]))
    if s["tur"] == "pil_kablo":
        ic.append("<p class='kucuk'>Uç adları: H1±/H2± hücre uçları · TP1.B±/OUT± şarj modülü · MT1/MT2.IN±/OUT± "
                  "yükselticiler · IZ.IN± = B0505S bacak 1/2, IZ.OUT± = bacak 6/4 (gövdede ad yok) · KL.± iç klemens · A.C34/C36 "
                  "kartın 24 V telleri. Denetim bu listeden düğüm grafını kurup kartın −12 rayının kart GND'den "
                  "ayrı kaldığını ölçüyor — iki taraf yalnız B0505S'in içinden ayrılıyor.</p>")
    if s["no"] in ("9.1", "9.2", "9.3"):
        ic.append("<h4>Yol kontrolü — jaktan karta</h4>")
        ic.append(_tablo(("Uç 1", "Uç 2", "Beklenen"),
                         [(E(ad), "A:R8 (VREF)", f"<b>≈ {B._oku(r)}</b> (±%2)") for ad, _ag, r in giris_direncleri(nl, parcalar)]))
        ic.append("<p class='kucuk'>Bölücüler GND'ye değil VREF'e iniyor; jak ile COM arası enerji yokken sonsuz "
                  "okur. Anlamlı ölçüm jak ile VREF arası: kartta U3'ün 1. bacağı, delik <b>A:R8</b>.</p>")
    if s["tur"] == "kalibrasyon":
        ke = kalib_esikleri()
        ic.append("<p class='kucuk'>Seri konsoldan (USB). Her komut ayarı NVS'e yazar. Kazanç kalibrasyonu "
                  f"(<code>i</code>, <code>g</code>) tam skalanın %{KALIB_ESIK_ORANI * 100:.0f}'inin altındaki "
                  "değeri reddeder — 'en az' sütunu.</p>")
        enaz = {"i&lt;amper&gt;": f"{ke['i_15m']:.2f} A (15 mΩ takılıyken) · {ke['i']:.2f} A (5 mΩ)",
                "g&lt;volt&gt;": f"{ke['g_normal']:.1f} V (NORMAL) · {ke['g_yuksek']:.0f} V (YÜKSEK)"}
        ic.append(_tablo(("Komut", "Ne yapar", "Ne zaman", "En az"),
                         [(f"<code>{k}</code>", E(n), E(z), enaz.get(k, "—")) for k, n, z in K.KALIBRASYON]))
    for k in s.get("kapi", []):
        gerek = ", ".join(sorted(kapi_gerek().get(k, set()))) or "—"
        ic.append(f"<div class='ok'><b>KAPI {k}</b> — {B.KAPI.get(k, '')}"
                  f"<div class='kucuk'>gerekli kart dışı parça: {E(gerek)}</div></div>")
    if s.get("kontrol"):
        ic.append("<h4>Kontrol</h4>")
        ic.append(_liste(x.format(**bicim) for x in s["kontrol"]))   # B55n: kontrol de bicimleniyor
    ic.append("</div>")
    return f"<li class='aa' data-no='{E(s['no'])}'>" + "".join(ic) + "</li>"


def malzeme_ayir(stok) -> tuple[list, list]:
    """MALZEME'yi envantere gore boler: (stokta [(kayit, html)], alinacak [kayit])."""
    stokta, alinacak = [], []
    for m in K.MALZEME:
        k = stok.ad_ile(*m["stok"]) if (m["stok"] and stok.var) else ""
        if k and _stokta(k):
            stokta.append((m, k))
        else:
            alinacak.append(m)
    return stokta, alinacak


def ic_kat_konumu(o: dict) -> str:
    """Bir panel ogesinin ic kat cubuguna gore konumu — TEK cumle, veriden.

    B55g: havalandirma deliklerinin 'neden' metinleri bu cumleyi ELLE yaziyordu
    ve UCU DE YANLISTI (HV2 'x 187' derken veri 81, HV3 'x 117' derken 81,
    HV4 'bu noktada ic kat yok' derken cubuk z 0'dan basliyor). Artik uretiliyor.
    """
    s = next((c for c in ic_kat_cubuklari(o["panel"])
              if c[0] - 1e-6 <= o["x"] <= c[0] + c[1] + 1e-6), None)
    if s is None:
        return f"x {o['x']:.0f}: bu noktada iç kat çubuğu YOK, duvar tek kat"
    if o["z"] < s[2] - 1e-6:
        return (f"x {o['x']:.0f}: iç kat çubuğu z {s[2]:.0f}'ten başlıyor, "
                "bu yükseklikte duvar tek kat")
    orta = s[0] + s[1] / 2
    yer = "ortası" if abs(o["x"] - orta) < 0.6 else f"içinde (ortası x {orta:.0f})"
    return f"x {o['x']:.0f} iç kat çubuğunun ({s[0]:.0f}–{s[0] + s[1]:.0f}) {yer}"


def _ohm(s: str) -> float:
    """Netlist direnc degeri ('1K', '820K', '220R', '10R') -> ohm."""
    m = re.fullmatch(r"([\d.]+)\s*([RKkMm]?)", s.strip())
    if not m:
        raise ValueError(f"direnc degeri cozulemedi: {s!r}")
    return float(m.group(1)) * {"": 1.0, "R": 1.0, "K": 1e3, "k": 1e3, "M": 1e6, "m": 1e-3}[m.group(2)]


def kutu_govdeleri(nl, parcalar) -> list[dict]:
    """Kutu icindeki BUTUN kati govdeler, tek listede: kartlar/moduller
    (IC_PARCA), tasiyicilar ve kutu ek bloklari (ayaklar), sabitler (kose
    diregi + kapak rayi) ve panel ogelerinin ice uzanan govdeleri.
    B55g: aciklik denetimi bu listeden kuruluyor — daha once her sinif ayri
    ayri ve yalnizca CAKISMA icin bakiliyordu."""
    o = olcu()
    out = []
    for p in K.IC_PARCA:
        z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == p["ref"]), 0.0)
        # B55j: `tasma` = plaketin delik alanindan disari tasan kenar payi.
        # Kart B fabrika 5x5 cm ve KESILMIYOR: govde 50, delik alani 45.7.
        # x/y delik izgarasinin cipasi (vida merkezleri oradan), govde tasmali.
        t = p.get("tasma", 0.0)
        genis = dict(p, x=p["x"] - t, y=p["y"] - t, en=p["en"] + 2 * t, boy=p["boy"] + 2 * t)
        # Plaket TEK kutu degil: yerlesimin kullanmadigi arka serit yalniz plaket
        # kalinliginda (bos_yuk) ve duvara asili moduller TAM ORAYA sarkiyor.
        # Tek kutu sayilirsa A-MT1/TP1/YUVA1 sahte cakisma verir (B55j'de oldu).
        for h in kart_hacimleri(genis, z0, nl, parcalar):
            out.append({"ref": h["ref"], "sinif": "parça", "sahip": None, "x": h["x"], "y": h["y"],
                        "z": h.get("z", z0), "en": h["en"], "boy": h["boy"], "yuk": h["yuk"]})
    for a in ayaklar():                                  # KUTU_EK_PARCA da burada
        out.append({**a, "sinif": "taşıyıcı"})
    for r in kapak_raylari() + direkler():
        out.append({**r, "sinif": "sabit", "sahip": None})
    # B55j: duvara asili moduller (yuva, TP4056, MT3608) envantere GIRMIYORDU —
    # ayri bir iddia ailesi onlara tek tek bakiyordu. Kart A'nin gercek yuksekligi
    # (35 mm, olculdu) TP1'i 4.8 mm'ye dusurunce fark edildi. Tek mekanizma olsun.
    for d in duvar_parcalari():
        out.append({**d, "sinif": "duvar", "sahip": None})
    for q in panel_ogeleri():
        if q["derin_mm"] <= 0:
            continue
        y0 = (K.KUTU["ic_boy"] - q["derin_mm"]) if q["panel"] == "ön" else 0.0
        m = max(q["metal_mm"], q["delik_mm"])
        out.append({"ref": q["ref"], "sinif": "panel", "sahip": None, "x": q["x"] - m / 2,
                    "y": y0, "z": q["z"] - m / 2, "en": m, "boy": q["derin_mm"], "yuk": m})
    return [g for g in out if g["en"] > 0 and o]


def govde_bosluk(a: dict, b: dict) -> float:
    """Iki dikdortgen prizma arasindaki GERCEK 3B bosluk (mm). aralik3()
    eksenlerin en buyugunu donduruyor (ayirici eksen); bu ise Oklid."""
    dx = max(0.0, b["x"] - (a["x"] + a["en"]), a["x"] - (b["x"] + b["en"]))
    dy = max(0.0, b["y"] - (a["y"] + a["boy"]), a["y"] - (b["y"] + b["boy"]))
    dz = max(0.0, b.get("z", 0.0) - (a.get("z", 0.0) + a["yuk"]),
             a.get("z", 0.0) - (b.get("z", 0.0) + b["yuk"]))
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def iletken_mi(g: dict) -> bool:
    """Govde ILETKEN mi? Kartlar/moduller (IC_PARCA) ve metal govdeli panel
    ogeleri iletken; ahsap tasiyicilar, ek bloklar, direk ve raylar degil.

    B55g-b (kullanici: "ahsap-ahsap milimetreleri hesaplama, yerinde ayarlarim"):
    dar aciklik envanteri artik yalniz EN AZ BIR TARAFI ILETKEN ciftleri
    gerekcelendiriyor. Ahsap-ahsap ciftler yalnizca CAKISMA icin bakiliyor
    (bicakla ayarlanir), sayilari belgede tek satirda geciyor."""
    return g["sinif"] in ("parça", "panel", "duvar")


def _kok_ref(r: str) -> str:
    """'A (dolu)' / 'A (boş kenar)' -> 'A'. Plaket iki hacme bolunuyor."""
    return r.split(" (")[0]


def _ayni_takim(a: dict, b: dict) -> bool:
    """Parca ile KENDI tasiyicisi, ayni parcanin iki tasiyicisi, ya da ayni
    plaketin iki hacmi (dolu / bos kenar)."""
    ra, rb = _kok_ref(a["ref"]), _kok_ref(b["ref"])
    return (ra == rb or a.get("sahip") == rb or b.get("sahip") == ra
            or bool(a.get("sahip")) and a.get("sahip") == b.get("sahip"))


def dar_aciklikllar(nl, parcalar, yalniz_iletken: bool = False) -> list[tuple[float, str, str]]:
    """parca_payi'nin ALTINA inen govde ciftleri (kendi tasiyicisi haric),
    dar olandan genise dogru. Anahtar: siralanmis 'ref|ref'.
    yalniz_iletken=True: en az bir tarafi iletken olanlar (gerekce istenenler)."""
    g = kutu_govdeleri(nl, parcalar)
    out = []
    for a, b in itertools.combinations(g, 2):
        if _ayni_takim(a, b):
            continue
        if yalniz_iletken and not (iletken_mi(a) or iletken_mi(b)):
            continue
        d = govde_bosluk(a, b)
        if d < K.KUTU["parca_payi"]:
            out.append((d, *sorted((a["ref"], b["ref"]))))
    return sorted(out)


def kart_don(ref: str, c: float, r: float, yon: int) -> tuple[float, float]:
    """Plaket delik indeksini kartin YONUNE gore cevirir (kare kartlar).
    yon: kartin saat yonunde donme acisi. 0 -> (c,r) oldugu gibi."""
    n = V.KARTLAR[ref]["sutun"] - 1
    return {0: (c, r), 90: (n - r, c), 180: (n - c, n - r), 270: (r, n - c)}[yon]


def kart_nokta(p: dict, c: float, r: float) -> tuple[float, float, float]:
    """Bir plaket deliginin KUTU koordinati (mm). z = kartin oturma yuzeyi."""
    adim = V.KARTLAR[p["ref"]].get("adim_mm", 2.54)
    c2, r2 = kart_don(p["ref"], c, r, p.get("yon", 0))
    z0 = next((a["yuk"] for a in ayaklar() if a["sahip"] == p["ref"]), 0.0)
    return (p["x"] + (c2 + 0.5) * adim, p["y"] + (r2 + 0.5) * adim, z0)


def hv_dugumu(p: dict) -> tuple[float, float, float]:
    """Kart B uzerindeki 617 V'luk giris dugumunun (T_HV) kutu koordinati."""
    c, r = V.YER["T_HV"][2], V.YER["T_HV"][3]
    return kart_nokta(p, c, r)


def hvalt_tel() -> dict:
    """B:O16 (T_N6) -> A:C11 (T_HVALT) telinin kutudaki boyu (B64b). duz: iki lehim noktasi
    arasi; yol: eksen eksen (tel kart kenarlarini izler, capraz gecmez); kes: yol + 30 mm pay,
    ust 10 mm'ye yuvarli — kablo notundaki sayi (V.HVALT_TEL_KES_CM) bununla sinaniyor."""
    ka = next(p for p in K.IC_PARCA if p["ref"] == "A")
    kb_ = next(p for p in K.IC_PARCA if p["ref"] == "B")
    a = kart_nokta(ka, V.YER["T_HVALT"][2], V.YER["T_HVALT"][3])
    b = kart_nokta(kb_, V.YER["T_N6"][2], V.YER["T_N6"][3])
    yol = sum(abs(p - q) for p, q in zip(a, b))
    return {"duz": math.dist(a, b), "yol": yol, "kes": math.ceil((yol + 30.0) / 10.0) * 10.0}


def kart_yon_cumlesi(p: dict) -> str:
    """Kartin yonunu KULLANICININ uygulayabilecegi bicimde anlatir: A1 kosesi
    (sutun 0, satir 0) kutunun hangi kosesine bakiyor. Elle yazilmaz."""
    x, y, _z = kart_nokta(p, 0.0, 0.0)
    yatay = "sol" if x < p["x"] + p["en"] / 2 else "sağ"
    derin = "arka" if y < p["y"] + p["boy"] / 2 else "ön"
    return f"A1 köşesi ({derin}-{yatay})"


def hv_kablo_yolu(p: dict) -> tuple[float, list]:
    """HV jakinin ic ucundan ankraj blogunun tepesine, oradan T_HV'ye.
    Duz cizgi DEGIL: kablo ankraja bagla ile tutturuluyor (9.3), yol oradan
    kiriliyor ve jakin z 63'u ile plaketin z'si arasindaki dusus de sayiliyor.
    Eski iddia (kutu.py, B50g) 2B idi, kartin MERKEZINI kullaniyordu ve
    ankraji hic gormuyordu: 44 mm yazip yesil geciyordu, gercek 74-101 mm."""
    j = {o["ref"]: o for o in panel_ogeleri()}["J2.1"]
    jak = (j["x"], K.KUTU["ic_boy"] - j["derin_mm"], j["z"])
    a = next(q for q in kutu_ek_parcalari() if q["ref"].startswith("HV ankraj"))
    ank = (a["x"] + a["en"] / 2, a["y"] + a["boy"] / 2, a["yuk"])
    hv = hv_dugumu(p)
    return math.dist(jak, ank) + math.dist(ank, hv), [jak, ank, hv]


def iletken_govdeler(haric: str, nl, parcalar) -> list[dict]:
    """Kutu icindeki ILETKEN govdeler (kartlar, moduller, panel metalleri).
    B55j: ARTIK kutu_govdeleri()'nden suzuluyor — daha once AYRI bir kopya
    kuruyordu ve `tasma` (kart B 50 mm) ile dolu/bos ayrimini gormuyordu,
    yani HV yon hesabi eski modelle calisiyordu."""
    return [g for g in kutu_govdeleri(nl, parcalar)
            if iletken_mi(g) and _kok_ref(g["ref"]) != haric]


def nokta_kutu_mesafe(p: tuple, b: dict) -> float:
    """Bir noktanin bir dikdortgen prizmaya 3B en kisa mesafesi (mm)."""
    dx = max(b["x"] - p[0], 0.0, p[0] - (b["x"] + b["en"]))
    dy = max(b["y"] - p[1], 0.0, p[1] - (b["y"] + b["boy"]))
    dz = max(b.get("z", 0.0) - p[2], 0.0, p[2] - (b.get("z", 0.0) + b["yuk"]))
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def hv_yon_tablosu(nl, parcalar) -> dict:
    """Dort yonelim icin (en yakin iletken, HV kablo boyu) — karar burada."""
    b = dict(next(p for p in K.IC_PARCA if p["ref"] == "B"))
    govde = iletken_govdeler("B", nl, parcalar)
    out = {}
    for yon in (0, 90, 180, 270):
        b["yon"] = yon
        hv = hv_dugumu(b)
        out[yon] = (min(nokta_kutu_mesafe(hv, g) for g in govde), hv_kablo_yolu(b)[0])
    return out


def besleme_butcesi() -> dict:
    """B58 guc butcesi (A, W, saat) — sayilar tasarim3_sabit'ten.

    Analog: 24 V rayi (kart + GUC lambasi) <- MT2 <- B0505S <- 5 V barasi.
    ESP32 ve kartin +5 V'u da 5 V barasindan; 5 V barasi MT1 uzerinden paketten.
    Kotu hal: ESP32 WiFi tepesi, hucre en alt gerilimde (DW01A kesme esigi) ve
    TEK hucre takili (paralel paket tek hucreyle de calisir) -> kol akimi."""
    p24 = 24.0 * (T.RAY24_AKIM_KOTU + T.PANEL_LED_AKIM)
    iz_cikis = p24 / T.MT3608_VERIM                     # B0505S'in verdigi guc
    # asgari: regulesiz modulun "en az %10 yuk" sarti EN DUSUK yukte olculur
    iz_asgari = 24.0 * (T.RAY24_AKIM_ASGARI + T.PANEL_LED_AKIM) / T.MT3608_VERIM
    iz_giris = iz_cikis / T.IZOLE_VERIM                 # 5 V barasindan cektigi
    i_f0 = iz_giris / 5.0
    i5_kotu = i_f0 + T.ESP32_5V_AKIM_KOTU + T.KART_5V_AKIM
    i5_tipik = i_f0 + T.ESP32_5V_AKIM_TIPIK + T.KART_5V_AKIM
    p_kotu, p_tipik = 5.0 * i5_kotu / T.MT3608_VERIM, 5.0 * i5_tipik / T.MT3608_VERIM
    kucuk, buyuk = min(T.IZOLE_GUC_SECENEK), max(T.IZOLE_GUC_SECENEK)
    return {"p24": p24, "iz_cikis": iz_cikis, "iz_giris": iz_giris, "iz_asgari_w": iz_asgari,
            "iz_yuk": iz_cikis / kucuk, "iz_yuk_buyuk": iz_cikis / buyuk,     # metin icin
            "iz_yuk_asgari": iz_asgari / buyuk,
            "i_f0": i_f0, "i5_kotu": i5_kotu, "i5_tipik": i5_tipik,
            "i_kol": p_kotu / T.HUCRE_V_ALT, "p_paket_tipik": p_tipik,
            # %90 kullanilabilir enerji; sarjda CV kuyrugu icin %20 pay
            "sure_sa": T.HUCRE_SAYISI * T.HUCRE_KAPASITE_AH * T.HUCRE_V_NOM * 0.9 / p_tipik,
            "sarj_sa": T.HUCRE_SAYISI * T.HUCRE_KAPASITE_AH / T.PIL_SARJ_AKIMI * 1.2}


def tutucu_parcalari(tt: dict) -> list[tuple[str, float, int]]:
    """Duvar tutucusunun cubuk parcalari: (ad, uzunluk, adet). Tek tip tutucu ad/uzunluk/adet
    ile, cok parcali olan (B58d TP1 rafi: kanalli alt kat + ust kat + dayanak) 'parcalar' ile."""
    if tt.get("parcalar"):
        return [(ad, float(u), int(n)) for ad, u, n in tt["parcalar"]]
    return [(tt["ad"], float(tt["uzunluk"]), int(tt["adet"]))]


def pil_kol_akimi() -> float:
    """Hucre kolunun SUREKLI kotu hal akimi (A) — B58 butcesinden (tek hucre,
    en alt gerilim, ESP32 WiFi tepesi + analog tam yuk). Sigorta anmasi buna gore."""
    return besleme_butcesi()["i_kol"]


def metin_bicim(nl, parcalar) -> dict:
    """Metinlerde gecen elektriksel sabitler — tasarim3_sabit TEK kaynak (B55g).
    CAL direnci dort ayri metinde geciyordu ve hepsi elle yazilmisti."""
    return {"cal_r": f"{T.CAL_SERI_R / 1e3:.0f} kΩ", "cal_stok": T.CAL_SERI_STOK,
            "pil_azami": f"{T.PIL_GIRIS_AZAMI_V:.0f} V",
            "pil_sigorta": (f"{T.PIL_KOL_SIGORTA:.0f} A F" if T.PIL_KOL_SIGORTA >= 1
                            else f"{T.PIL_KOL_SIGORTA * 1e3:.0f} mA F"),
            "sarj_akimi": f"{T.PIL_SARJ_AKIMI:.2f} A",
            "f0_sigorta": f"{T.F0_SIGORTA:.0f} A hızlı, FUS003",
            "test_v": T.TEST_KAYNAK_V, "test_i": T.TEST_KAYNAK_V / T.TEST_YUK_R,
            "pil_suresi": f"{besleme_butcesi()['sure_sa']:.0f} saat (ESP32 WiFi'de, analog açık)",
            "sarj_suresi": f"{besleme_butcesi()['sarj_sa']:.1f} saat",
            "iz_yuk": besleme_butcesi()["iz_yuk"] * 100, "iz_yuk_w": besleme_butcesi()["iz_cikis"],
            "iz_yuk_asgari": besleme_butcesi()["iz_yuk_asgari"] * 100,
            "iz_yuk_buyuk": besleme_butcesi()["iz_yuk_buyuk"] * 100,
            "sogutucu_r": f"{T.SOGUTUCU_BOSALTMA_R / 1e6:.0f} MΩ",
            "sogutucu_stok": T.SOGUTUCU_BOSALTMA_STOK,
            "sogutucu_akim": T.PIL_GIRIS_AZAMI_V / T.SOGUTUCU_BOSALTMA_R * 1e6,
            "r50f": T.SIGORTA["F 50 mA"][0], "r50t": T.SIGORTA["T 50 mA"][0],
            "r400": T.SIGORTA["F 400 mA"][0],
            "kanal": next((q["tasiyici"].get("kanal", 0.0) for q in K.IC_PARCA
                           if q["ref"] == "ESP32"), 0.0),
            "kesim1_cubuk": sum(r["adet"] for r in hesap()["kesim1"]),
            "kesim1_eksik": max(0, sum(r["adet"] for r in hesap()["kesim1"]) - K.KUTU["elde_cubuk"]),
            "kart_a_en": next(q["en"] for q in K.IC_PARCA if q["ref"] == "A"),
            "kart_a_boy": next(q["boy"] for q in K.IC_PARCA if q["ref"] == "A"),
            # B56: kartin on duvara payi (eski {a_f0_pay}); B58e'de F0 panelden kalkti.
            "a_on_pay": K.KUTU["ic_boy"] - (lambda q: q["y"] + q["boy"])(
                next(q for q in K.IC_PARCA if q["ref"] == "A")),
            "cal_pay": min(panel_bosluk("CAL")),
            "cal_komsu": " ve ".join(o["etiket"] for o in cal_komsulari()),
            "cal_tehdit": cal_tehdit_gerilimi()[0],
            "panel_orta": K.KUTU["ic_en"] / 2,
            "ray_payi": K.KUTU["kapak_ray_payi"],
            "ray_payi_toplam": 2 * K.KUTU["kapak_ray_payi"],
            "sarj_tavani": f"{T.LIION_SARJ_TAVANI_C:.0f} °C",
            "desarj_tavani": f"{T.LIION_DESARJ_TAVANI_C:.0f} °C",
            "yon_b": kart_yon_cumlesi(next(p for p in K.IC_PARCA if p["ref"] == "B")),
            "yon_a": kart_yon_cumlesi(next(p for p in K.IC_PARCA if p["ref"] == "A")),
            "hvalt_duz": hvalt_tel()["duz"], "hvalt_yol": hvalt_tel()["yol"], "hvalt_kes": hvalt_tel()["kes"],
            **esp_kizak_bicim(nl, parcalar),
            "hv_fs": menziller()["fs_hv"],
            "panel_etiketleri": panel_etiketleri(),
            "tl431": T.TL431_V, "tl431_alt": T.TL431_V * 0.98, "tl431_ust": T.TL431_V * 1.02,
            "vref": T.VREF,
            "hv_kablo": f"{hv_kablo_yolu(next(p for p in K.IC_PARCA if p['ref'] == 'B'))[0]:.0f} mm",
            **tp1_bicim()}


def tp1_bicim() -> dict:
    """6.0 metninin sayilari (B58d) — raf parcalari DUVAR_TUTUCU'dan, bosluklar geometriden."""
    tp = next(d for d in K.DUVAR_PARCA if d["ref"] == "TP1")
    a = next(q for q in K.IC_PARCA if q["ref"] == "A")
    z0 = next(x["yuk"] for x in ayaklar() if x["sahip"] == "A")
    tt = K.DUVAR_TUTUCU["TP1"]
    (_a1, alt, _n1), (_a2, ust, _n2), (_a3, day, _n3) = tutucu_parcalari(tt)
    return {"tp1_bosluk": z0 - (tp["z"] + tp["yuk"]), "tp1_aralik": a["y"] - 0.0,
            "tp1_alt": alt, "tp1_ust": ust, "tp1_day": day, "tp1_kanal": tt.get("kanal", 0.0)}


def ayak_bicim() -> dict:
    """Ayak bloklarinin kat sayisi/yuksekligi — 6.1 metni bunlari ELLE yaziyordu
    ("4 parça çubuk üst üste") ve kart A 9 kata cikinca eskidi (B55j)."""
    t = K.CUBUK["kalinlik"]
    kat = {p["ref"]: p["tasiyici"]["kat"] for p in K.IC_PARCA
           if p.get("tasiyici", {}).get("tip") == "ayak"}
    return {"ayak_kat_a": kat["A"], "ayak_yuk_a": kat["A"] * t,
            "ayak_kat_b": kat["B"], "ayak_yuk_b": kat["B"] * t,
            "cep_alt_kat": 1 + K.SOMUN_CEP["kat"] + 1}


def m3_gecme_cap() -> float:
    """M3 gecme deliginin capi (TEK kaynak). B57b: eskiden yuva civata kayitlarindan
    okunuyordu; yuvalar yapistirilinca o kayitlar kalkti."""
    return K.KUTU["m3_gecme"]


def delme_bicim() -> dict:
    """DELME metinlerinin yer tutuculari — somun cebi SOMUN_CEP'ten (B55g).
    Cep 2. kattan basliyor: kat=1 -> "2", kat=2 -> "2.-3"."""
    cep = K.SOMUN_CEP
    # B58e: yalniz YUVARLAK delikler (14x9 oval yuvalar ayri satirda). Onceden F0'in
    # Ø12'si ovallerin 9'unu ortuyordu; F0 panelden kalkinca "en buyuk Ø9" diye yanlis cikti.
    buyuk = max(o["delik_mm"] for o in panel_ogeleri() if o["delik_mm"] > 0 and o["tip"] != "yuva")
    return {"buyuk_cap": buyuk, "buyuk_et": (K.CUBUK["genislik"] - buyuk) / 2,
            "cubuk_g": K.CUBUK["genislik"], **ayak_bicim(),
            "m3_cap": m3_gecme_cap(), "cep_cap": cep["cap"],
            "cep_katlari": "2" if cep["kat"] == 1 else f"2.–{1 + cep['kat']}"}


def delik_parca_html(stok, nl, parcalar) -> str:
    """Her delik: parca (stok kaydiyla), cap, konum, gerekce — panel verisinden + M3 delikleri."""
    kb, h = K.KUTU, hesap()
    sat = []
    for o in sorted(panel_ogeleri(), key=lambda q: (q["panel"] != "ön", q["z"], q["x"])):
        cap = f"{o['yuva_en_mm']:.0f} × {o['delik_mm']:.0f} oval" if o["tip"] == "yuva" else f"Ø{o['delik_mm']:.1f}"
        kayit = stok.ad_ile(*o["parca"]) if (o["parca"] and stok.var) else "—"
        parca = E(o["parca"][0]) if o["parca"] else "(kendi parçası yok)"
        sat.append((f"<b>{E(o['etiket'])}</b><br><span class='kucuk'>{E(o['panel'])} · x {o['x']:.0f} · z {o['z']:.0f}</span>",
                    cap, f"{parca}<br><span class='kucuk'>{kayit}</span>",
                    E(o.get("neden", "").format(konum=ic_kat_konumu(o), **metin_bicim(nl, parcalar)))))
    # B55g: bu uc satir ELLE yazilmis sabitlerdi ve ikisi veriyle celisiyordu —
    # (a) somun cebi hala "Ø6 / 3. kat" diyordu (B55e Ø6.5 / 2.-3. kat / 4 kat yapti),
    # (b) "duvara asili parcalar ... Ø3.2 ikiser" MT3608 ve TP4056 icin 8 HAYALI delik
    # deldiriyordu (DUVAR_TUTUCU'ya gore onlar kablo bagiyla tutuluyor, delikleri yok).
    # Artik ucu de veriden turetiliyor.
    cep, ayak_kat = K.SOMUN_CEP, {}
    for p in K.IC_PARCA:
        ts = p.get("tasiyici")
        if ts and ts["tip"] == "ayak":
            ayak_kat.setdefault(ts["kat"], []).append(f"{p['ref']} ×{ts['adet']}")
    kat = max(ayak_kat)                                   # tek deger bekleniyor; iddia olcuyor
    son = 1 + cep["kat"]                                  # cep 2. kattan basliyor
    cep_kat = "2." if cep["kat"] == 1 else f"2.–{son}."
    ayak_n = sum(int(s.split("×")[1]) for v in ayak_kat.values() for s in v)
    ab = ayak_bicim()
    alt_kat, kat_a, kat_b = ab["cep_alt_kat"], ab["ayak_kat_a"], ab["ayak_kat_b"]
    yapisik = sorted(K.YAPISTIRMA_ISTISNA)
    bag_ile = [r for r, v in K.DUVAR_TUTUCU.items() if v is not None]
    m3 = [(f"Kapak cıvataları ×{2 * len(kb['kapak_civata_y'])}", "Ø3.2", f"{kb['kapak_civata']} + somun + pul (MEK034/035)",
           f"Yan duvarlardan (y {kb['kapak_civata_y'][0]:.0f} / {kb['kapak_civata_y'][1]:.0f}, z {kb['kapak_civata_z']:.0f}) "
           "kapak rayına; tahtaya diş açılmaz, somun tutar → kapak tak-çıkar. "
           "RAY DA DELİNİR (13.1): duvardaki delik kılavuz olur, aynı Ø3.2."),
          (f"Kart ayak blokları ×{ayak_n} ({', '.join(s for v in ayak_kat.values() for s in v)})",
           # B55l: burada "son kat" yaziliyordu ve max(kat)=9 aliniyordu; 6.1 metni ise
           # cebin ALTINDAKI kati (4.) soyluyordu — ayni belgede iki farkli kat numarasi.
           # Delinen katlar her iki blokta da AYNI: 1, cep, cebin alti. Gerisi sagir.
           f"Ø{cep['son_kat_delik']:.1f} (1. kat) + Ø{cep['cap']:.1f} ({cep_kat} kat) + "
           f"Ø{cep['son_kat_delik']:.1f} ({alt_kat}. kat)",
           f"{K.KUTU['kart_vida']} vida + gömme M3 somun",
           f"Somun {cep_kat} katın Ø{cep['cap']:.1f} cebinde, dış yüzüne bir damla japon: kartlar vidayla "
           f"sökülebilir, tahtaya diş yok. Cebin altındaki {alt_kat}. kat da Ø{cep['son_kat_delik']:.1f} "
           f"delik — vidanın ucu dayanmasın; <b>altındaki katlar delinmez</b> (kart A bloğu {kat_a} kat, "
           f"kart B bloğu {kat_b} kat). Merkezler kartın 2×2 boş köşe deliklerinden."),
          (f"Duvara asılı parçalar — EK DELİK YOK ({', '.join(bag_ile)})", "—", "kablo bağı (SRF012)",
           f"{', '.join(yapisik)} duvara sıcak silikonla yapıştırılı (B57b yuvalar, B73 modüller ve küçük "
           f"parçalar — kullanıcı kararı). {', '.join(bag_ile)} modülünde montaj deliği YOK: ahşap tutucuya "
           "kablo bağıyla tutuluyor. Duvar parçaları için duvara hiç delik açılmıyor.")]
    for a, b, c2, d in m3:
        sat.append((f"<b>{E(a)}</b>", E(b), E(c2), E(d)))
    return (_tablo(("Delik", "Çap / yuva", "Gelen parça · stok", "Neden bu parça / bu delik"), sat)
            + "<p class='kucuk'>Konumlar iç koordinat (önden bakınca soldan); 3.1/3.2'deki parça-parça tablo aynı "
              "delikleri parçanın kendi ucundan ölçer. Bütün jaklar aynı model (büyük şeffaf, B60). Renk: kırmızı = "
              "V/SKOP, siyah = COM ve CAL, SARI = yalnız HV, mavi = PİL, yeşil = YÜK.</p>")


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


def arayuz_html(nl, parcalar) -> tuple[str, dict]:
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
            + "<h4>Panel delikleri (mm)</h4>" + _tablo(("Ref", "Panel", "x", "z", "Delik", "İçeri uzantı"), sat_p)
            # B55g: 6 mm'nin altina inen ILETKEN tarafli ciftler, gerekcesiyle.
            # B55h: yalitkan kaplama — nereye, ne zaman, nereye DEGIL.
            + "<h4>Yalıtkan kaplama (tırnak cilası / konformal lak)</h4>"
            + _tablo(("Nereye", "Ne zaman", "Neden"),
                     [(f"<b>{E(k['ref'])}</b> — {E(k['nerede'])}", E(k["ne_zaman"]),
                       E(k["neden"] + " " + k["onkosul"])) for k in K.KAPLAMA])
            + "<h5 style='margin:10px 0 4px'>Kaplanmayacak yerler</h5>"
            + _tablo(("Nereye DEĞİL", "Neden"), [(f"<b>{E(a)}</b>", E(g)) for a, g in K.KAPLAMA_HARIC])
            + "<p class='kucuk'>4–5 <b>ince</b> kat, her kat kurusun (tek kalın kat çözücüyü içeride "
              "hapseder). Kaplama <b>yüzey kaçağını</b> keser, havadan atlamayı kesmez — mesafe yerine "
              "geçmez. Asıl kazanç doğrulukta: HV bölücüsü 4.92 MΩ olduğu için yüzey kaçağı orana "
              "paralel girer (100 MΩ kirli yüzey ≈ %4.7 okuma hatası). Sökmek gerekirse aseton çıkarır, "
              "ama aseton bazı plastiklere de saldırır.</p>"
            + f"<h4>Dar açıklıklar (&lt; {kb['parca_payi']:.0f} mm, iletken taraflı)</h4>"
            + _tablo(("Boşluk", "Çift", "Sorun mu, ne yapmalı"),
                     [(f"<b>{d:.2f} mm</b>", E(f"{a} ↔ {b}"), E(K.DAR_ACIKLIK[f"{a}|{b}"]))
                      for d, a, b in dar_aciklikllar(nl, parcalar, yalniz_iletken=True)])
            + f"<p class='kucuk'>Gerçek 3B boşluk (Öklid), parçanın kendi taşıyıcısı hariç. Liste "
              f"<b>kilitli</b>: yeni bir iletken taraflı çift 6 mm'nin altına inerse denetim kırmızıya "
              f"döner. Ayrıca <b>{len(dar_aciklikllar(nl, parcalar)) - len(dar_aciklikllar(nl, parcalar, True))} ahşap–ahşap çift</b> "
              "6 mm'nin altında — bunlar tek tek yazılmıyor, bıçakla yerinde ayarlanıyor; denetim "
              "yalnız çakışmadıklarına bakıyor.</p>")
    return html, veri


def yaz(nl, parcalar, hedef: Path) -> None:
    global _BILGI_STOK, _BILGI_BICIM
    stok = B.Stok()
    _BILGI_STOK = stok                                  # B57: kartlardaki "Stok" satiri
    _BILGI.clear()                                      # denetimde (stoksuz) kaydedilenler yeniden uretilsin
    h = hesap()
    _BILGI_BICIM = adim_bicim(h, nl, parcalar)          # B57: kart notlari adim metinleriyle ayni sozlukle
    c, kb = K.CUBUK, K.KUTU
    aa = alt_adimlar()
    mz = menziller()
    g = []

    def ref(kimlik, baslik, icerik):
        """Adim gorunumunu bogmasin diye referans bolumleri katlanir (durum tarayicida kalir)."""
        return (f"<details class='ref' id='{kimlik}'><summary><h2>{E(baslik)}</h2></summary>"
                f"<div class='ref-ic'>{icerik}</div></details>")
    g.append(ref("ref-belge", "Bu belge ne — kurallar", _liste([
        "Kartlar bitti. Bundan sonrası: <b>çubuktan kutu</b>, panel delikleri, şönt ve Q1, jaklar, kablolar, testler.",
        "<b>Parça bilgisi:</b> çizimlerde ve 3B görünümde bir parçanın <b>üzerine gel</b> (telefonda dokun): adı, "
        "ölçüsü, çubuksa <b>uzunluğu</b> ve kesim listesindeki satırı, hangi adımda takıldığı, stoktaki yeri çıkar. "
        "Tıkla / dokun: kart sabit kalır. Klavyeyle: çizimlerde <b>Tab</b> parçadan parçaya geçer, 3B'de "
        "<b>N / P</b> sonraki / önceki parça, <b>Esc</b> kapatır.",
        f"Kutu <b>{c['ad']}</b> ({c['uzunluk']:.0f} × {c['genislik']:.0f} × {c['kalinlik']:.0f} mm) çubuklardan. "
        f"İç ölçü <b>{kb['ic_en']:.0f} × {kb['ic_boy']:.0f} × {h['ic_yuk']:.0f} mm</b>, dış "
        f"{h['dis_en']:.0f} × {h['dis_boy']:.0f} × {h['ic_yuk'] + 2 * h['t']:.0f}.",
        f"<b>Sağlamlık:</b> duvarlar iki kat (dışta {kb['duvar_sira']} yatay sıra, içte dikey çubuklar; {h['duvar_t']:.0f} mm), "
        f"dört köşede {h['direk_t']:.0f} × {h['g']:.0f} mm direk; kapak yan duvarlardan {kb['kapak_civata']} "
        "cıvata + somunla tak-çıkar; kartlar gömme somunlu ayaklara vidalı. Taban ve kapak parçaları düz bölümden: "
        "yuvarlak uç hiçbir duvarın altına gelmiyor. Delikler duvar dikilmeden, parça düz zemindeyken.",
        "<b>Kural:</b> değerli parçalar — kartlar (A, B), ESP32, şönt, Q1 — yapıştırılmaz (vida, ayak, "
        "konnektör); kutunun kendi parçaları (çubuk, ayak, altlık) yapıştırılır. <b>Sıcak silikonla yapıştırılan "
        "duvar parçaları</b> (senin kararın): "
        + ", ".join(f"{r} ({v['yapistirici']})" for r, v in K.YAPISTIRMA_ISTISNA.items())
        + " — izopropil alkol ya da ısı tabancasıyla sökülür.",
        "<b>Kullanım sınırı:</b> yalnız pil / DC-DC beslemeli, toprağa göre yüzen devreler. HV ölçerken USB takılı olmaz.",
        "Aşağıda <b>ileri / geri</b> ile tek tek ilerle; 3B görünüm adım şeridinin altında (sürükle: döndür, "
        "Ctrl+tekerlek: yakınlaştır). Tezgahta telefondan: <code>python uretim/belge_sun.py</code>.",
        "Çubuk kullanan her adımda <b>\"Bu adımda gereken çubuk parçaları\"</b> tablosu var: hangi uzunluktan "
        "kaç tane, çubuk üstünde çizili. 1.2 ve 4.4 toplu kesim listeleri; oradaki \"hangi adımda\" sütunu "
        "aynı bilgiyi verir.",
    ])))
    g.append(ref("ref-yapistirici", "Hangi yapıştırıcı nerede",
                 _tablo(("İş", "Yapıştırıcı", "Nasıl"), [(E(a), f"<b>{E(b)}</b>", E(c2)) for a, b, c2 in kb["yapistirici"]])))
    g.append(ref("ref-delik-parca", "Hangi deliğe ne geliyor — ve neden", delik_parca_html(stok, nl, parcalar)))
    g.append(ref("ref-delme", "Delikleri nasıl açarım (matkapsız)",
                 _tablo(("Aşama", "Nasıl"), [(f"<b>{E(a.format(**delme_bicim()))}</b>",
                                              E(b.format(**delme_bicim()))) for a, b in K.DELME])
                 + "<p class='kucuk'>Bütün delik ölçüleri deliğin <b>merkezi</b>. Çap sütunu Ø = yuvarlak delik; "
                   "\"14 × 9 oval\" = genişlik × yükseklik dikdörtgen yuva (USB, ŞARJ). Yuvarlak: born "
                   "jaklar Ø6.5 / Ø8, toggle'lar Ø6, M3 cıvatalar Ø3.2.</p>"))
    g.append(ref("ref-onkosul", "Başlamadan önce — Yerleşim planında bitmiş olmalı", on_kosul_html(nl, parcalar)))
    bicim_al = dict(kb, cubuk=h["cubuk_sayisi"], elde=kb["elde_cubuk"], eksik=h["eksik"], eksik_pay=h["eksik_pay"],
                    **metin_bicim(nl, parcalar), pil_kol_ma=f"{pil_kol_akimi() * 1e3:.0f}")
    stokta, alinacak = malzeme_ayir(stok)
    malzeme_html = ("<h3>Stoktan çıkar</h3>"
                    # B55g: 'ad' de bicimlenmeli — {pil_sigorta} ham cikiyordu
                    # (B55c'de {adim_uA} ile ayni kusur; artik belge taramasi da var)
                    + (_tablo(("Ne", "Kayıt", "Not"), [(f"<b>{E(m['ad'].format(**bicim_al))}</b>", k,
                                                        E(m["not"].format(**bicim_al)))
                                                        for m, k in stokta]) if stokta else "<p class='kucuk'>—</p>")
                    + "<h3>Alınacak</h3>"
                    + (_tablo(("Ne", "Not"), [(f"<b>{E(m['ad'].format(**bicim_al))}</b>", E(m["not"].format(**bicim_al)))
                                              for m in alinacak])
                       if alinacak else "<p class='kucuk'>Alınacak bir şey yok.</p>"))
    g.append(ref("ref-malzeme", f"Malzeme — stoktan {len(stokta)}, alınacak {len(alinacak)}", malzeme_html))

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

    kullanim_html = (_tablo(("Ölçüm", "Hangi uç", "Nasıl bağlanır", "Çözünürlük"),
                            # B55k: KULLANIM'a sarj isil kurali eklendi ve o satir
                            # {sarj_tavani}/{desarj_tavani} kullaniyor — menziller()
                            # disindaki sabitler metin_bicim(nl, parcalar)'den geliyor.
                            [(f"<b>{E(a.format(**mz, **metin_bicim(nl, parcalar)))}</b>", f"<b>{E(b)}</b>",
                              c2.format(**mz, **metin_bicim(nl, parcalar)),
                              f"<span class='kucuk'>{E(d.format(**mz, **metin_bicim(nl, parcalar)))}</span>")
                             for a, b, c2, d in K.KULLANIM])
                     + "<h3>Akım ve gerilim ölçümü — bağlantı</h3>"
                     + "<figure><figcaption>YÜK jakları devreye SERİ girer; COM içeride YÜK 2'dir</figcaption>" + ciz_kullanim("akim") + "</figure>"
                     + "<h3>Pil kapasite testi — bağlantı</h3>"
                     + "<figure><figcaption>PİL jakları deşarj yolu; V jakı zorunlu</figcaption>" + ciz_kullanim("pil") + "</figure>")
    g.append(ref("ref-kullanim", "Bitince: neyi nereden ölçerim", kullanim_html))
    g.append(ref("ref-agirlik", "Ağırlık merkezi — kutu dengeli mi", agirlik_html()))
    ara_html, ara_veri = arayuz_html(nl, parcalar)
    g.append(ref("ref-arayuz", "Kutu arayüzü — 3D baskı / başka kap için", ara_html))
    g.append(f"<script id='kutu-arayuz' type='application/json'>{json.dumps(ara_veri, ensure_ascii=False)}</script>")

    ek_stil = U.PANEL_CSS + U.IPUCU_CSS + """
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
details.ref{border:1px solid var(--cizgi);border-radius:14px;margin:10px 0;background:var(--yz2)}
details.ref>summary{cursor:pointer;padding:10px 16px;list-style:none;display:flex;align-items:center;gap:10px}
details.ref>summary::before{content:"▸";color:var(--m3);font-size:14px}
details.ref[open]>summary::before{content:"▾"}
details.ref>summary h2{margin:0;padding:0;border:0;font-size:16px;font-weight:600}
details.ref .ref-ic{padding:4px 18px 16px}
details.ayrinti{margin:8px 0 12px;border-left:3px solid var(--cizgi);padding-left:12px}
details.ayrinti>summary{cursor:pointer;color:var(--m2);font-size:13px;padding:4px 0}
.aa>.aa-ic>h4:first-of-type{margin-top:6px}
ul.is{margin:8px 0 14px;padding-left:20px}
ul.is li{margin:6px 0}
figure{margin:14px 0;padding:10px;border:1px solid var(--cizgi);border-radius:10px;background:var(--yz2);overflow-x:auto}
figure figcaption{font-size:12px;color:var(--m3);margin-bottom:6px}
figure svg{width:100%;min-width:460px;max-height:540px;height:auto;display:block;margin:0 auto}
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
__JS_IPUCU__
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
   if (ipSabit && ipSabit.el && !ipSabit.el.getClientRects().length) ipBirak();
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
 [].forEach.call(document.querySelectorAll('details.ref'), function(d){
   try { if (localStorage.getItem('kutu-ref-' + d.id) === '1') d.open = true; } catch(e) {}
   d.addEventListener('toggle', function(){ try { localStorage.setItem('kutu-ref-' + d.id, d.open ? '1' : ''); } catch(e) {} });
 });
 var bas = adresten();
 goster(bas >= 0 ? bas : 0, false);
})();
</script>""".replace("__JS_IPUCU__", U.JS_IPUCU).replace("__JS_3B__", U.JS_3B).replace("__ALTADIM__", basliklar).replace(
        "__SAHNE__", json.dumps(sahne(), ensure_ascii=False))
    # B57: kart tablosu EN SON — sahne() ve bütün çizimler kartlarını kaydettikten sonra.
    # Yalnız sayfada ya da sahnede ANILAN anahtarlar gömülür; '</' betiği kapatmasın.
    anilan = set(re.findall(r'data-bi="([^"]+)"', "".join(g))) | {b["k"] for b in sahne() if b.get("k")}
    anilan = {html_unescape(k) for k in anilan}
    js = js.replace("__BILGI__", json.dumps({k: _BILGI[k] for k in sorted(anilan) if k in _BILGI},
                                            ensure_ascii=False).replace("</", "<\\/"))

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
</div>{U.IPUCU_HTML}{js}</body></html>"""
    # B55g: bicimlenmemis yer tutucu belgeye SIZMASIN. B55c'de {adim_uA}, bu
    # turda {pil_sigorta} ham cikti — ikisi de bir alanin .format() edilmemesi.
    # Burasi tek cikis noktasi, o yuzden denetim burada: 'del' KALIP degil,
    # sadece suslu parantez icinde tek bir kelime olanlar aranir.
    kacak = sorted(set(re.findall(r"\{[a-z_][a-z0-9_]{2,24}\}", sayfa)))
    if kacak:
        raise AssertionError(f"belgede bicimlenmemis yer tutucu kaldi: {kacak}")
    # B57: sayfadaki her data-bi'nin karti GOMULU olmali. Kartsiz anahtar sessizce
    # dusuyordu (BILGI tablosu yalniz var olanlari aliyor) — fare o parcanin
    # uzerine gelince hicbir sey olmazdi. Tek cikis noktasi, denetim burada.
    gomulu = json.loads(re.search(r"var BILGI = (\{.*?\});\n", sayfa, re.S).group(1).replace("<\\/", "</"))
    kartsiz = sorted({html_unescape(k) for k in re.findall(r'data-bi="([^"]+)"', sayfa)} - set(gomulu))
    if kartsiz:
        raise AssertionError(f"belgede karti olmayan parca anahtari: {kartsiz[:5]}")
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
    print(f"  {D.gecti}/{D.gecti + D.kaldi} dogrulama gecti"
          + ("  ⚠ EKSIK KOSU: envanter okunamadi, 7 · STOK bolumu atlandi" if STOK_ATLANDI else ""))
    if D.kaldi == 0 and not a.belge_yok:
        yaz(nl, parcalar, BELGE)
        print(f"  belge: {BELGE.relative_to(KOK)}")
    return 0 if D.kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
