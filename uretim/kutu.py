# -*- coding: utf-8 -*-
"""B50 — kutu / panel kurulum plani: DENETIM + CIZIMLI BELGE.

`yerlesim3.py` plaketi denetleyip `7-yerlesim.html`'i uretiyor; bu dosya
ayni isi PLAKETE GIRMEYEN her sey icin yapiyor ve `8-kutu.html`'i
uretiyor: kullanicinin DIL CUBUGUNDAN yapacagi kutu, panel delikleri,
sont/Q1 yerlesimi, kablolar, kapilar.

Kullanici (2026-09-20): "adim adim istiyorum, ben next next diyeyim; ve
gorsellestir — neyi nereye, nasil sabitleyecegimi, nasil gozukmesi
gerektigini goreyim." Bu yuzden her alt adimin kendi cizimi var:
kusbakisi (taban plani), on/arka gorunus (duvar + delikler) ve
izometrik (3 boyutlu gibi) — hepsi ayni veriden uretiliyor.

Kural: sayilar `kutu_veri.py`'de, kablolar `yerlesim3_veri.KABLOLAR`'da,
KAPI metinleri `yerlesim3_belge.KAPI`'da — burada HIC BIRI tekrar
yazilmiyor.

  python kutu.py            # denetim + belge
  python kutu.py --belge-yok
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))

import belge_menu as MN                                   # noqa: E402
import kutu_veri as K                                     # noqa: E402
import tasarim3_sabit as T                                # noqa: E402
import yerlesim3 as Y                                     # noqa: E402
import yerlesim3_belge as B                               # noqa: E402
import yerlesim3_veri as V                                # noqa: E402

BELGE = KOK / "BELGELER" / "8-kutu.html"
JAK_ARASI_EN_AZ = 20.0      # mm — 4 mm muzlu fisin govdesi + parmak payi
DELIK_KENAR_PAYI = 3.0      # mm — delik kenari ile cubuk kenari arasi
E = B.e

AHSAP = {"ust": "#d9bb8c", "on": "#c3a173", "yan": "#a88a5d", "cizgi": "#7d6540"}
VURGU = {"ust": "#f2c14e", "on": "#e0a92f", "yan": "#c08f1f", "cizgi": "#7a5a00"}
PARCA_RENK = {"A": "#3d6aa8", "B": "#8a3ca8", "ESP32": "#2f7d5a",
              "RS": "#b3261e", "Q1": "#8a6e42"}
JAK_RENK = {"kirmizi": "#c8372a", "siyah": "#2b2b2b", "sari": "#d9a300", "gri": "#8a8a85"}


# ═══════════════════════════════════════════════════════════════════════
#  VERIDEN TUREYENLER
# ═══════════════════════════════════════════════════════════════════════

def hesap() -> dict:
    """Kutu ve kesim sayilari — hepsi CUBUK ve KUTU'dan turuyor."""
    c, k = K.CUBUK, K.KUTU
    ic_yuk = k["duvar_sira"] * c["genislik"]
    dis_en = k["ic_en"] + 2 * c["kalinlik"]
    dis_boy = k["ic_boy"] + 2 * c["kalinlik"]
    taban_adet = math.ceil(k["ic_en"] / c["genislik"])
    # Duvar: on/arka disaridan disariya, yanlar aralarina giriyor.
    # Cubuktan UZUN kenarlar iki parcaya bolunur: bir tam cubuk + ek parca.
    # Ek yeri her sirada kaydirilir (duvar o cizgiden ayrilmasin).
    duz = c["uzunluk"] - 2 * c["uc_egim"]        # cubugun duz (dikdortgen) bolumu
    # Taban ve kapak cubuklari KESILMEZ: dis derinlik tam cubuk boyu kadar,
    # yuvarlak uclar duvarlarin altinda kalir (denetim bunu kilitliyor).
    kenarlar = [("Taban çubuğu (kesilmez)", c["uzunluk"], taban_adet, False),
                ("Kapak çubuğu (kesilmez)", c["uzunluk"], taban_adet, False),
                ("Taban rayı", k["ic_en"], 2, True),
                ("Duvar — ön/arka", dis_en, 2 * k["duvar_sira"], True),
                ("Duvar — yan", k["ic_boy"], 2 * k["duvar_sira"], True),
                ("Kapak rayı", k["ic_en"] - 2 * c["kalinlik"] - 2, 2, True),
                ("Ayak bloğu (kart altı)", c["genislik"], 16, True)]
    parcalar = []                      # (ad, kesilecek uzunluk, adet)
    for ad, u, adet, kes in kenarlar:
        if not kes or u <= duz:
            parcalar.append((ad, u, adet))
        else:
            n = math.ceil(u / duz)     # esit parcalara bol; ekler kaydirilir
            parcalar.append((f"{ad} — {n} parça", u / n, adet * n))
    # Kac cubuk gerekir: her parcayi 150 mm'lik cubuklardan kes (greedy).
    # Kesilmeyen parcalar bir cubugun tamamini yer; kesilenler DUZ bolumden.
    kesilmez = sum(int(adet) for ad, _u, adet in parcalar if "kesilmez" in ad)
    boylar = sorted((u for ad, u, adet in parcalar if "kesilmez" not in ad
                     for _ in range(int(adet))), reverse=True)
    cubuklar: list[float] = []
    for u in boylar:
        for i, kalan in enumerate(cubuklar):
            if kalan >= u + 1.0:       # 1 mm testere payi
                cubuklar[i] = kalan - u - 1.0
                break
        else:
            cubuklar.append(duz - u)
    return {"ic_yuk": ic_yuk, "dis_en": dis_en, "dis_boy": dis_boy, "kenarlar": kenarlar,
            "taban_adet": taban_adet, "parcalar": parcalar, "duz": duz,
            "cubuk_sayisi": len(cubuklar) + kesilmez,
            "ek_parca": dis_en - c["uzunluk"]}


def alt_adimlar() -> list[dict]:
    out = []
    for a in K.ADIMLAR:
        for s in a["alt"]:
            out.append(dict(s, adim=a["no"], adim_baslik=a["baslik"]))
    return out


def kart_disi_kablolar() -> list[int]:
    return [i for i, c in enumerate(V.KABLOLAR)
            if c[0].startswith("X:") or c[1].startswith("X:")]


def kapi_gerek() -> dict[int, set[str]]:
    """KAPI k -> gerektirdigi kart disi parcalar (KABLOLAR'dan turuyor)."""
    g: dict[int, set[str]] = {}
    for c in V.KABLOLAR:
        for uc in c[:2]:
            if uc.startswith("X:"):
                g.setdefault(c[3], set()).add(uc[2:].split(".")[0])
    return g


def monte_adim() -> dict[str, str]:
    return {r: s["no"] for s in alt_adimlar() for r in s.get("monte", [])}


def panel_ogeleri(hangi: str | None = None) -> list[dict]:
    o = [dict(x, panel="ön") for x in K.PANEL_ON] + \
        [dict(x, panel="arka") for x in K.PANEL_ARKA]
    return [x for x in o if hangi is None or x["panel"] == hangi]


def giris_direncleri(nl, parcalar) -> list[tuple[str, str, float]]:
    """Panel jakindan VREF'e beklenen direnc — netlistten.

    Bolucu zincirleri GND'ye DEGIL VREF'e iniyor, bu yuzden jak-COM
    arasi enerji yokken sonsuz okur; anlamli kontrol jak ile VREF."""
    d = B._dc_direnc(9, nl, parcalar)
    return [(ad, ag, d(ag, "/VREF"))
            for ag, ad in (("/V_GIRIS", "V jakı"), ("/HV_GIRIS", "HV jakı"),
                           ("/SKOP_GIRIS", "SKOP jakı"))]


def cakisma(a: dict, b: dict) -> bool:
    return (a["x"] < b["x"] + b["en"] and b["x"] < a["x"] + a["en"]
            and a["y"] < b["y"] + b["boy"] and b["y"] < a["y"] + a["boy"])


# ═══════════════════════════════════════════════════════════════════════
#  DENETIM
# ═══════════════════════════════════════════════════════════════════════

def denetle(nl, parcalar) -> Y.Denetim:
    D = Y.Denetim()
    h = hesap()
    c, kb = K.CUBUK, K.KUTU
    oge = panel_ogeleri()
    ref_oge = {o["ref"]: o for o in oge}

    print("\n  1 · MALZEME VE KESIM")
    D.kosul("Cubugun yuvarlak uclari veride", c.get("uc_egim", 0) > 0,
            f"uc egim {c.get('uc_egim', 0):.0f} mm -> duz bolum {h['duz']:.0f} mm")
    for ad, u, adet in h["parcalar"]:
        sinir = c["uzunluk"] if "kesilmez" in ad else h["duz"]
        D.kosul(f"'{ad}' {'cubuk boyuna' if 'kesilmez' in ad else 'DUZ bolume'} sigiyor",
                u <= sinir + 1e-6, f"{u:.1f} <= {sinir:.0f} mm · {adet} adet")
    D.kosul("Taban/kapak cubuklari kesilmeden kullaniliyor "
            "(dis derinlik = cubuk boyu)",
            abs(h["dis_boy"] - c["uzunluk"]) < 1e-6,
            f"dis derinlik {h['dis_boy']:.0f} = cubuk {c['uzunluk']:.0f} mm")
    D.kosul("Taban cubuklari ic eni kapatiyor",
            h["taban_adet"] * c["genislik"] >= kb["ic_en"],
            f"{h['taban_adet']} x {c['genislik']:.0f} = "
            f"{h['taban_adet'] * c['genislik']:.0f} >= {kb['ic_en']:.0f} mm")
    D.kosul("Gereken cubuk sayisi hesaplandi", h["cubuk_sayisi"] > 0,
            f"{h['cubuk_sayisi']} cubuk")

    print("\n  2 · IC YERLESIM (sokulebilir montaj)")
    # Kullanici (2026-09-20): "ileride baska bir kaba gecebilirim; kartlar ve
    # parcalar sokulemez sekilde yapistirilmasin." -> her ic parcanin tutturma
    # yontemi VIDA ya da KABLO BAGI olmali.
    for p in K.IC_PARCA:
        n = p["nasil"].lower()
        D.kosul(f"{p['ref']} sokulebilir tutturuluyor",
                ("vida" in n or "kablo bağ" in n) and "yapıştırıl" not in n,
                p["nasil"][:50])
    for p in K.IC_PARCA:
        D.kosul(f"{p['ref']} ic alana sigiyor",
                0 <= p["x"] and p["x"] + p["en"] <= kb["ic_en"]
                and 0 <= p["y"] and p["y"] + p["boy"] <= kb["ic_boy"],
                f"x {p['x']:.0f}+{p['en']:.0f} / y {p['y']:.0f}+{p['boy']:.0f}")
    for i, p in enumerate(K.IC_PARCA):
        for q in K.IC_PARCA[i + 1:]:
            D.kosul(f"{p['ref']} ile {q['ref']} cakismiyor", not cakisma(p, q))
    en_yuksek = max(p["yuk"] for p in K.IC_PARCA)
    D.kosul("Duvar yuksekligi en yuksek parcayi + pay aliyor",
            h["ic_yuk"] >= en_yuksek + 10, f"{h['ic_yuk']:.0f} >= {en_yuksek + 10:.0f} mm")
    esp = next(p for p in K.IC_PARCA if p["ref"] == "ESP32")
    usb = ref_oge["USB"]
    D.kosul("ESP32 arka duvardaki USB deligine hizali",
            abs((esp["x"] + esp["en"] / 2) - usb["x"]) <= 30,
            f"|{esp['x'] + esp['en'] / 2:.0f} - {usb['x']:.0f}| mm")

    print("\n  3 · PANEL")
    for o in oge:
        yari = max(o["metal_mm"], o["delik_mm"]) / 2
        D.kosul(f"{o['ref']} panelin icinde",
                kb["kenar_payi"] <= o["x"] - yari
                and o["x"] + yari <= kb["ic_en"] - kb["kenar_payi"],
                f"x={o['x']:.0f}")
        sira = int(o["z"] // c["genislik"])
        alt, ust = sira * c["genislik"], (sira + 1) * c["genislik"]
        D.kosul(f"{o['ref']} deligi tek cubuk sirasinin icinde",
                o["z"] - o["delik_mm"] / 2 - DELIK_KENAR_PAYI >= alt
                and o["z"] + o["delik_mm"] / 2 + DELIK_KENAR_PAYI <= ust,
                f"sira {sira + 1} ({alt:.0f}–{ust:.0f} mm), z={o['z']:.0f}")
        D.kosul(f"{o['ref']} delik capi cubuk genisligine sigiyor",
                o["delik_mm"] + 2 * DELIK_KENAR_PAYI <= c["genislik"],
                f"Ø{o['delik_mm']:.1f} + 2x{DELIK_KENAR_PAYI:.0f} <= {c['genislik']:.0f}")
    jaklar = [o for o in oge if o["tip"] == "jak"]
    for i, a in enumerate(jaklar):
        for b in jaklar[i + 1:]:
            if a["panel"] != b["panel"]:
                continue
            m = math.dist((a["x"], a["z"]), (b["x"], b["z"]))
            D.kosul(f"{a['ref']} – {b['ref']} merkez arasi >= {JAK_ARASI_EN_AZ:.0f} mm",
                    m >= JAK_ARASI_EN_AZ, f"{m:.1f} mm")
    hv = ref_oge["J2.1"]
    for o in oge:
        if o is hv or o["panel"] != hv["panel"] or o["metal_mm"] <= 0:
            continue
        acik = math.dist((hv["x"], hv["z"]), (o["x"], o["z"])) \
            - hv["metal_mm"] / 2 - o["metal_mm"] / 2
        D.kosul(f"HV jaki – {o['ref']} metal arasi >= takviyeli kacak yolu",
                acik >= T.IEC60664_CREEPAGE_TAKVIYELI,
                f"{acik:.1f} >= {T.IEC60664_CREEPAGE_TAKVIYELI} mm")

    print("\n  4 · KABLOLAR")
    gereken = set(kart_disi_kablolar())
    verilen: dict[int, list[str]] = {}
    for s in alt_adimlar():
        for i in s.get("kablo", []):
            verilen.setdefault(i, []).append(s["no"])
    D.kosul("Kart disi kablolarin hepsi bir alt adimda",
            gereken <= set(verilen), f"eksik: {sorted(gereken - set(verilen))}")
    D.kosul("Hicbir kablo iki alt adimda degil",
            all(len(v) == 1 for v in verilen.values()),
            str({i: v for i, v in verilen.items() if len(v) > 1}))
    D.kosul("Kutu planinda kart-kart kablosu yok (o yerlesim planinda)",
            not (set(verilen) - gereken), f"fazla: {sorted(set(verilen) - gereken)}")
    yuk_adim = {verilen[i][0] for i, cc in enumerate(V.KABLOLAR)
                if cc[2] == "yuk" and i in verilen}
    D.kosul("Yuk akimi kablolari guc yolu adimlarinda (7 ve 8)",
            all(no.startswith(("7.", "8.")) for no in yuk_adim), str(sorted(yuk_adim)))
    hepsi = {s["no"]: s for s in alt_adimlar()}
    for no in sorted(yuk_adim):
        D.kosul(f"{no} metninde kalin kablo kurali geciyor",
                any("1.5 mm²" in m or "alın kablo" in m for m in hepsi[no].get("yap", [])))
    kelvin = {verilen[i][0] for i, cc in enumerate(V.KABLOLAR)
              if cc[2] in ("kelvin", "yildiz") and i in verilen}
    D.kosul("Kelvin cifti ve yildiz GND ayni alt adimda", len(kelvin) == 1, str(kelvin))

    print("\n  5 · KART DISI PARCALAR")
    m = monte_adim()
    for r in sorted(V.KART_DISI_NOTU):
        D.kosul(f"{r} bir alt adimda kutuya giriyor", r in m, m.get(r, "YOK"))
    sayim = [r for s in alt_adimlar() for r in s.get("monte", [])]
    D.kosul("Hicbir parca iki kez monte edilmiyor", len(sayim) == len(set(sayim)),
            str([r for r in set(sayim) if sayim.count(r) > 1]))

    print("\n  6 · SIRA")
    numaralar = [s["no"] for s in alt_adimlar()]
    D.kosul("Alt adim numaralari tekil", len(numaralar) == len(set(numaralar)))
    sira = {no: i for i, no in enumerate(numaralar)}
    gerek = kapi_gerek()
    for s in alt_adimlar():
        for k in s.get("kapi", []):
            for r in sorted(gerek.get(k, set())):
                onc = m.get(r)
                D.kosul(f"KAPI {k} icin {r} daha once monte ediliyor",
                        onc is not None and sira[onc] <= sira[s["no"]],
                        f"{r}: {onc} · KAPI: {s['no']}")
    for s in alt_adimlar():
        for i in s.get("kablo", []):
            for uc in V.KABLOLAR[i][:2]:
                if not uc.startswith("X:"):
                    continue
                r = uc[2:].split(".")[0]
                D.kosul(f"{s['no']} kablosu icin {r} monte edilmis",
                        r in m and sira[m[r]] <= sira[s["no"]],
                        f"{r}: {m.get(r, 'YOK')}")

    print("\n  7 · OLCUM DEGERLERI (netlistten)")
    for ad, _ag, r in giris_direncleri(nl, parcalar):
        D.kosul(f"{ad} -> VREF direnci hesaplanabiliyor",
                r != float("inf") and r > 1e3,
                B._oku(r) if r != float("inf") else "sonsuz")
    D.kosul("Sont degeri kalibrasyon komutunda dogru",
            any(f"s{min(T.SONT_SECENEK)}" in x[0] for x in K.KALIBRASYON),
            f"s{min(T.SONT_SECENEK)}")
    D.kosul("Q1 akim siniri notu tasarim sabitiyle ayni",
            f"{T.PIL_AKIM_SOGUTUCUSUZ:.2f}" in V.KART_DISI_NOTU["Q1"])

    print("\n  8 · STOK")
    stok = B.Stok()
    if stok.var:
        for o in oge:
            if o["parca"]:
                s = stok.ad_ile(*o["parca"])
                D.kosul(f"{o['ref']} envanterde", "kayıtta yok" not in s,
                        f"{o['parca'][0][:38]}")
    else:
        print("      (envanter okunamadi — atlandi)")
    return D


# ═══════════════════════════════════════════════════════════════════════
#  CIZIM — ortak yardimcilar
# ═══════════════════════════════════════════════════════════════════════

def _svg(ic: str, gen: float, yuk: float, baslik: str) -> str:
    return (f'<svg viewBox="0 0 {gen:.0f} {yuk:.0f}" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="ui-monospace,Consolas,monospace" role="img">'
            f'<title>{E(baslik)}</title>{ic}</svg>')


def _yazi(x, y, s, boy=11, renk="var(--m2)", hiza="middle", kalin=False):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{hiza}" font-size="{boy}" '
            f'fill="{renk}"{" font-weight=\"600\"" if kalin else ""}>{E(s)}</text>')


def _dikdortgen(x, y, w, h, dolgu, cizgi="var(--cizgi)", opak=1.0, rx=2):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{dolgu}" stroke="{cizgi}" stroke-width="1" opacity="{opak}"/>')


IZO_ACI = math.radians(30)


def _izo(x, y, z, o, s):
    px = (x - y) * math.cos(IZO_ACI) * s
    py = ((x + y) * math.sin(IZO_ACI) - z) * s
    return (o[0] + px, o[1] + py)


def _izo_sigdir(dx, dy, z0, z1, hedef_en=560.0, pay=26.0, alt=44.0):
    """Izometrik cizimi kutuya sigdir: olcek, orijin ve viewBox.

    Onceki surumde olcek ve orijin ELLE yazilmisti; kutu buyuyunce cizim
    viewBox'in disina tasiyordu (kullaniciya yarim kutu gorunuyordu)."""
    ham = [_izo(x, y, z, (0.0, 0.0), 1.0)
           for x in (0, dx) for y in (0, dy) for z in (z0, z1)]
    gx = max(p[0] for p in ham) - min(p[0] for p in ham)
    gy = max(p[1] for p in ham) - min(p[1] for p in ham)
    s = hedef_en / gx
    o = (pay - min(p[0] for p in ham) * s, pay - min(p[1] for p in ham) * s)
    return s, o, gx * s + 2 * pay, gy * s + 2 * pay + alt


def _izo_kutu(x, y, z, dx, dy, dz, o, s, renk, opak=1.0):
    """Eksen hizali bir prizmanin uc gorunen yuzu."""
    p = {}
    for i, (ax, ay, az) in enumerate([(0, 0, 0), (dx, 0, 0), (dx, dy, 0), (0, dy, 0),
                                      (0, 0, dz), (dx, 0, dz), (dx, dy, dz), (0, dy, dz)]):
        p[i] = _izo(x + ax, y + ay, z + az, o, s)
    def yuz(idx, renk_):
        d = " ".join(f"{p[i][0]:.1f},{p[i][1]:.1f}" for i in idx)
        return (f'<polygon points="{d}" fill="{renk_}" stroke="{renk["cizgi"]}" '
                f'stroke-width="0.7" opacity="{opak}"/>')
    return (yuz((4, 5, 6, 7), renk["ust"])       # üst
            + yuz((0, 1, 5, 4), renk["on"])      # ön (y=0)
            + yuz((1, 2, 6, 5), renk["yan"]))    # sağ (x=dx)


# ═══════════════════════════════════════════════════════════════════════
#  CIZIM — gorunusler
# ═══════════════════════════════════════════════════════════════════════

def ciz_kesim() -> str:
    """Kesim listesi: her parca bir cubuk seridi uzerinde."""
    h, c = hesap(), K.CUBUK
    olc, sol, ust, satir = 2.2, 215.0, 30.0, 34.0   # sol: en uzun parca adi sigsin
    gen = sol + c["uzunluk"] * olc + 120
    yuk = ust + satir * len(h["parcalar"]) + 20
    o = [_yazi(sol, 18, f"bir çubuk {c['uzunluk']:.0f} mm · gri uçlar yuvarlak "
                        f"({c['uc_egim']:.0f} mm) · düz bölüm {h['duz']:.0f} mm",
               11, "var(--m3)", "start")]
    for i, (ad, u, adet) in enumerate(h["parcalar"]):
        y = ust + i * satir
        o.append(_dikdortgen(sol, y, c["uzunluk"] * olc, 20, "var(--yz2)", "var(--cizgi)"))
        # yuvarlak uclar: kesilecek parcalar bu bolgeye giremez
        for ux in (sol, sol + (c["uzunluk"] - c["uc_egim"]) * olc):
            o.append(_dikdortgen(ux, y, c["uc_egim"] * olc, 20, "#8a8a85",
                                 "var(--cizgi)", 0.45))
        bas = sol if "kesilmez" in ad else sol + c["uc_egim"] * olc
        o.append(_dikdortgen(bas, y, u * olc, 20, AHSAP["on"], AHSAP["cizgi"]))
        o.append(_yazi(sol - 10, y + 14, ad, 11, "var(--m1)", "end"))
        o.append(_yazi(bas + u * olc / 2, y + 14, f"{u:.0f} mm", 10, "#2b2b2b"))
        o.append(_yazi(sol + c["uzunluk"] * olc + 10, y + 14, f"× {int(adet)}",
                       11, "var(--m1)", "start", True))
        kalan = (c["uzunluk"] if "kesilmez" in ad else h["duz"]) - u
        if kalan > 4:
            o.append(_yazi(bas + (u + kalan / 2) * olc, y + 14,
                           f"artan {kalan:.0f}", 9, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Kesim listesi")


def ciz_taban(kapak=False) -> str:
    """Kusbakisi: taban (ya da kapak) cubuklari + raylar."""
    h, c, kb = hesap(), K.CUBUK, K.KUTU
    olc, sol, ust = 1.9, 40.0, 40.0
    gen, yuk = sol * 2 + kb["ic_en"] * olc, ust * 2 + kb["ic_boy"] * olc
    o = []
    for i in range(h["taban_adet"]):
        x = sol + i * c["genislik"] * olc
        w = min(c["genislik"], kb["ic_en"] - i * c["genislik"]) * olc
        o.append(_dikdortgen(x, ust, w - 1, kb["ic_boy"] * olc, AHSAP["ust"], AHSAP["cizgi"]))
    for ry in (0.18, 0.82):
        y = ust + kb["ic_boy"] * olc * ry
        o.append(_dikdortgen(sol, y - c["genislik"] * olc / 2, kb["ic_en"] * olc,
                             c["genislik"] * olc, VURGU["on"], VURGU["cizgi"], 0.85))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust - 12,
                   f"{kb['ic_en']:.0f} mm — {h['taban_adet']} çubuk yan yana", 11))
    o.append(_yazi(sol - 12, ust + kb["ic_boy"] * olc / 2,
                   f"{kb['ic_boy']:.0f} mm", 11, "var(--m2)", "end"))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust + kb["ic_boy"] * olc + 22,
                   "sarı = alttan yapıştırılan iki ray (çubukları birbirine bağlar)",
                   11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Kapak" if kapak else "Taban")


def ciz_duvar(sira: int) -> str:
    """Izometrik: taban + `sira` kadar duvar sirasi, ust sira vurgulu."""
    c, kb = K.CUBUK, K.KUTU
    s, o0, gen, yuk = _izo_sigdir(kb["ic_en"], kb["ic_boy"], -c["kalinlik"],
                                  sira * c["genislik"])
    o = []
    o.append(_izo_kutu(0, 0, -c["kalinlik"], kb["ic_en"], kb["ic_boy"], c["kalinlik"],
                       o0, s, AHSAP))
    for r in range(sira):
        z = r * c["genislik"]
        renk = VURGU if r == sira - 1 else AHSAP
        opak = 1.0 if r == sira - 1 else 0.92
        # arka + sag once (derinlik sirasi), sonra sol + on
        o.append(_izo_kutu(0, kb["ic_boy"], z, kb["ic_en"], c["kalinlik"],
                           c["genislik"], o0, s, renk, opak))
        o.append(_izo_kutu(kb["ic_en"], 0, z, c["kalinlik"], kb["ic_boy"],
                           c["genislik"], o0, s, renk, opak))
        o.append(_izo_kutu(-c["kalinlik"], 0, z, c["kalinlik"], kb["ic_boy"],
                           c["genislik"], o0, s, renk, opak))
        o.append(_izo_kutu(0, -c["kalinlik"], z, kb["ic_en"], c["kalinlik"],
                           c["genislik"], o0, s, renk, opak))
    o.append(_yazi(gen / 2, yuk - 26,
                   f"{sira}. sıra bitti · duvar yüksekliği {sira * c['genislik']:.0f} mm",
                   12, "var(--m1)", "middle", True))
    o.append(_yazi(gen / 2, yuk - 10,
                   "öne bakan kenar = ön duvar (jaklar oraya gelecek)", 11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, f"{sira}. sıra")


def ciz_panel(hangi: str, vurgu: set[str]) -> str:
    """On ya da arka duvar gorunusu: cubuk siralari + delikler."""
    c, kb, h = K.CUBUK, K.KUTU, hesap()
    olc, sol, ust = 2.0, 40.0, 30.0
    gen, yuk = sol * 2 + kb["ic_en"] * olc, ust + h["ic_yuk"] * olc + 100
    taban_y = ust + h["ic_yuk"] * olc
    o = []
    for r in range(kb["duvar_sira"]):
        y = taban_y - (r + 1) * c["genislik"] * olc
        o.append(_dikdortgen(sol, y, kb["ic_en"] * olc, c["genislik"] * olc - 1,
                             AHSAP["on"], AHSAP["cizgi"]))
        o.append(_yazi(sol - 8, y + c["genislik"] * olc / 2 + 4,
                       f"{r + 1}", 10, "var(--m3)", "end"))
    for i, x in enumerate(sorted(panel_ogeleri(hangi), key=lambda q: q["x"])):
        cx = sol + x["x"] * olc
        cy = taban_y - x["z"] * olc
        kay = 0 if i % 2 == 0 else 13           # etiketler ust uste binmesin
        v = x["ref"] in vurgu
        r = max(x["metal_mm"], x["delik_mm"]) / 2 * olc
        renk = JAK_RENK.get(x["renk"], "#8a8a85")
        if x["tip"] == "klemens":
            o.append(_dikdortgen(cx - r, cy - 9, 2 * r, 18, renk, "var(--yz)", 0.9))
            for kk in (-1, 1):
                o.append(f'<circle cx="{cx + kk * r / 2.2:.1f}" cy="{cy:.1f}" r="3" '
                         'fill="var(--yz)"/>')
        else:
            o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{renk}" '
                     f'stroke="{"#f2c14e" if v else "var(--m3)"}" '
                     f'stroke-width="{3 if v else 1.2}" opacity=".95"/>')
            o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{x["delik_mm"] / 2 * olc:.1f}" '
                     'fill="var(--yz)" opacity=".6"/>')
        o.append(_yazi(cx, cy + r + 13 + kay, x["etiket"], 11, "var(--m1)", "middle", v))
        o.append(_yazi(cx, cy + r + 25 + kay, f"x {x['x']:.0f} · z {x['z']:.0f}",
                       9, "var(--m3)"))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, taban_y + 74,
                   f"{'Ön' if hangi == 'ön' else 'Arka'} duvar — içeriden bakış · "
                   f"x sol kenardan, z tabandan", 11, "var(--m3)"))
    o.append(_dikdortgen(sol, taban_y, kb["ic_en"] * olc, 5, AHSAP["yan"], AHSAP["cizgi"]))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust - 10,
                   f"{kb['ic_en']:.0f} mm", 11))
    return _svg("".join(o), gen, yuk, f"{hangi} duvar")


def ciz_yerlesim(vurgu: set[str]) -> str:
    """Kusbakisi taban plani: ic parcalar + panel ogeleri."""
    c, kb = K.CUBUK, K.KUTU
    olc, sol, ust = 1.9, 46.0, 46.0
    gen, yuk = sol * 2 + kb["ic_en"] * olc, ust * 2 + kb["ic_boy"] * olc + 34
    o = [_dikdortgen(sol - c["kalinlik"] * olc, ust - c["kalinlik"] * olc,
                     (kb["ic_en"] + 2 * c["kalinlik"]) * olc,
                     (kb["ic_boy"] + 2 * c["kalinlik"]) * olc, AHSAP["yan"], AHSAP["cizgi"]),
         _dikdortgen(sol, ust, kb["ic_en"] * olc, kb["ic_boy"] * olc,
                     "var(--yz2)", "var(--cizgi)")]
    for p in K.IC_PARCA:
        v = p["ref"] in vurgu
        x, y = sol + p["x"] * olc, ust + p["y"] * olc
        o.append(_dikdortgen(x, y, p["en"] * olc, p["boy"] * olc,
                             PARCA_RENK.get(p["ref"], "#666"),
                             "#f2c14e" if v else "var(--cizgi)", 0.95 if v else 0.45))
        o.append(_yazi(x + p["en"] * olc / 2, y + p["boy"] * olc / 2 + 4,
                       p["ref"], 12, "#fff", "middle", v))
    for i, x in enumerate(sorted(panel_ogeleri("ön"), key=lambda q: q["x"])):
        cx = sol + x["x"] * olc
        v = x["ref"] in vurgu
        kay = 24 if i % 2 == 0 else 36          # etiketler ust uste binmesin
        o.append(f'<circle cx="{cx:.1f}" cy="{ust + kb["ic_boy"] * olc + 6:.1f}" r="5" '
                 f'fill="{JAK_RENK.get(x["renk"], "#888")}" '
                 f'stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{2 if v else 1}"/>')
        o.append(_yazi(cx, ust + kb["ic_boy"] * olc + kay, x["etiket"], 9,
                       "var(--m1)" if v else "var(--m3)"))
    for x in panel_ogeleri("arka"):
        cx = sol + x["x"] * olc
        v = x["ref"] in vurgu
        o.append(f'<circle cx="{cx:.1f}" cy="{ust - 6:.1f}" r="5" '
                 f'fill="{JAK_RENK.get(x["renk"], "#888")}" '
                 f'stroke="{"#f2c14e" if v else "var(--m3)"}" stroke-width="{2 if v else 1}"/>')
        o.append(_yazi(cx, ust - 14, x["etiket"], 9, "var(--m1)" if v else "var(--m3)"))
    o.append(_yazi(sol + kb["ic_en"] * olc / 2, ust + kb["ic_boy"] * olc + 52,
                   "kuşbakışı · alt kenar = ön duvar (jaklar), üst kenar = arka duvar",
                   11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "Yerleşim")


def ciz_izo(vurgu: set[str]) -> str:
    """Izometrik: kutu + ic parcalar (vurgulu olan parlak)."""
    c, kb = K.CUBUK, K.KUTU
    h = hesap()
    s, o0, gen, yuk = _izo_sigdir(kb["ic_en"], kb["ic_boy"], -c["kalinlik"], h["ic_yuk"])
    o = [_izo_kutu(0, 0, -c["kalinlik"], kb["ic_en"], kb["ic_boy"], c["kalinlik"],
                   o0, s, AHSAP)]
    o.append(_izo_kutu(0, kb["ic_boy"], 0, kb["ic_en"], c["kalinlik"], h["ic_yuk"],
                       o0, s, AHSAP, 0.9))
    o.append(_izo_kutu(kb["ic_en"], 0, 0, c["kalinlik"], kb["ic_boy"], h["ic_yuk"],
                       o0, s, AHSAP, 0.9))
    for p in sorted(K.IC_PARCA, key=lambda q: -(q["x"] + q["y"])):
        v = p["ref"] in vurgu
        renk = {"ust": PARCA_RENK.get(p["ref"], "#666"),
                "on": PARCA_RENK.get(p["ref"], "#666"),
                "yan": PARCA_RENK.get(p["ref"], "#666"), "cizgi": "#111"}
        o.append(_izo_kutu(p["x"], p["y"], 0, p["en"], p["boy"], max(p["yuk"] * .5, 6),
                           o0, s, renk, 1.0 if v else 0.42))
        m = _izo(p["x"] + p["en"] / 2, p["y"] + p["boy"] / 2,
                 max(p["yuk"] * .5, 6) + 4, o0, s)
        o.append(_yazi(m[0], m[1], p["ref"], 11, "#fff" if v else "var(--m3)",
                       "middle", v))
    o.append(_izo_kutu(-c["kalinlik"], 0, 0, c["kalinlik"], kb["ic_boy"], h["ic_yuk"],
                       o0, s, AHSAP, 0.55))
    o.append(_izo_kutu(0, -c["kalinlik"], 0, kb["ic_en"], c["kalinlik"], h["ic_yuk"],
                       o0, s, AHSAP, 0.55))
    o.append(_yazi(gen / 2, yuk - 12,
                   "ön ve sol duvar saydam çizildi (içeriyi görmek için)",
                   11, "var(--m3)"))
    return _svg("".join(o), gen, yuk, "İzometrik")


def _cizgi(x1, y1, x2, y2, renk="var(--m2)", kalin=2.4, kesik=False):
    d = ' stroke-dasharray="5 4"' if kesik else ""
    return (f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="{renk}" stroke-width="{kalin}" stroke-linecap="round"{d}/>')


def _uc(x, y, renk, etiket, alt=""):
    o = [f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="{renk}" '
         'stroke="var(--yz)" stroke-width="1.5"/>',
         _yazi(x, y - 12, etiket, 11, "var(--m1)", "middle", True)]
    if alt:
        o.append(_yazi(x, y + 22, alt, 10, "var(--m3)"))
    return "".join(o)


def ciz_kullanim(hangi: str) -> str:
    """Kullanim semalari: akim+gerilim olcumu ve pil testi baglantisi.

    Kullanici (2026-09-20): "yuk ve pil girisi olarak kullanacagim giris ne,
    anlayamadim." Sozle anlatmak yetmedi: J3 bir GIRIS degil, devrenin donus
    hattinin icinden gectigi SERI yol; J7 ise Q1'in anahtarladigi desarj yolu.
    Jaklar ve klemensler kutunun on panelinde oldugu icin cizimde de kutunun
    ust kenarinda duruyorlar."""
    KIR, SIY = "#c8372a", "#8a8a85"
    KUTU_Y, UST = 215.0, 60.0
    o = []

    def kutu_govde(x1, x2, baslik, alt):
        return (_dikdortgen(x1, KUTU_Y, x2 - x1, 78, "var(--yz2)", "var(--s1)")
                + _yazi((x1 + x2) / 2, KUTU_Y + 34, baslik, 12, "var(--s1)", "middle", True)
                + _yazi((x1 + x2) / 2, KUTU_Y + 54, alt, 10, "var(--m3)"))

    def ucbas(x, renk, etiket, alt, kat=0):
        # ucu kutunun UST kenarina koy, yazilari disina; kat=1 bir satir yukari
        # (yan yana uclarin alt yazilari ust uste biniyordu)
        k = 26 * kat
        return (f'<circle cx="{x:.0f}" cy="{KUTU_Y:.0f}" r="6" fill="{renk}" '
                'stroke="var(--yz)" stroke-width="1.5"/>'
                + _yazi(x, KUTU_Y - 26 - k, etiket, 11, "var(--m1)", "middle", True)
                + _yazi(x, KUTU_Y - 12 - k, alt, 9, "var(--m3)"))

    if hangi == "akim":
        o.append(_dikdortgen(20, 30, 130, 80, "var(--yz2)"))
        o.append(_yazi(85, 62, "KAYNAK", 12, "var(--m1)", "middle", True))
        o.append(_yazi(85, 82, "pil / güç kaynağı", 10, "var(--m3)"))
        o.append(_dikdortgen(420, 30, 150, 80, "var(--yz2)"))
        o.append(_yazi(495, 62, "ÖLÇÜLEN DEVRE", 12, "var(--m1)", "middle", True))
        o.append(_yazi(495, 82, "motor, kart, lamba…", 10, "var(--m3)"))
        o.append(kutu_govde(150, 470, "ÖLÇÜM KUTUSU", "içeride: 15 mΩ şönt"))
        # arti hatti (dokunmuyoruz)
        o.append(_cizgi(150, UST, 420, UST, KIR))
        o.append(_yazi(285, UST - 12, "+ hattı — buna dokunmuyoruz", 10, "var(--m3)"))
        # devrenin eksisi -> J3.1
        o.append(_cizgi(495, 110, 495, 170, SIY))
        o.append(_cizgi(495, 170, 430, 170, SIY))
        o.append(_cizgi(430, 170, 430, KUTU_Y, SIY))
        o.append(ucbas(430, SIY, "J3 · 1", "devreden gelen uç"))
        # J3.2 -> kaynagin eksisi
        o.append(_cizgi(190, KUTU_Y, 190, 170, SIY))
        o.append(_cizgi(190, 170, 85, 170, SIY))
        o.append(_cizgi(85, 170, 85, 110, SIY))
        o.append(ucbas(190, SIY, "J3 · 2", "kaynağa giden uç"))
        # V jaki: devrenin artisina
        o.append(_cizgi(340, KUTU_Y, 340, 140, KIR, 2.0, True))
        o.append(_cizgi(340, 140, 400, 140, KIR, 2.0, True))
        o.append(_cizgi(400, 140, 400, UST, KIR, 2.0, True))
        o.append(ucbas(340, KIR, "V jakı", "devrenin artısı"))
        # COM: kaynagin eksi hattina
        o.append(_cizgi(260, KUTU_Y, 260, 170, "#2b2b2b", 2.0, True))
        o.append(ucbas(260, "#2b2b2b", "COM", "eksi hat", 1))
        o.append(_yazi(300, 320, "Akım J3'ün İÇİNDEN geçer: dönüş hattını kesip iki ucunu "
                                 "klemense bağlıyorsun.", 11, "var(--m2)"))
        return _svg("".join(o), 600, 336, "Akım ve gerilim ölçümü")

    o.append(_dikdortgen(20, 30, 130, 90, "var(--yz2)"))
    o.append(_yazi(85, 66, "PİL", 13, "var(--m1)", "middle", True))
    o.append(_yazi(85, 88, "≤ 38 V", 10, "var(--m3)"))
    o.append(_dikdortgen(250, 38, 140, 46, "var(--yz2)", "#2f7d5a"))
    o.append(_yazi(320, UST + 6, "YÜK DİRENCİ", 11, "var(--m1)", "middle", True))
    o.append(_yazi(320, 98, "örn. 3.3 Ω 11 W taş direnç", 10, "var(--m3)"))
    o.append(kutu_govde(150, 490, "ÖLÇÜM KUTUSU", "içeride: Q1 anahtarı + şönt"))
    o.append(_cizgi(150, UST, 250, UST, KIR))
    o.append(_yazi(200, UST - 12, "pil +", 10, "var(--m3)"))
    o.append(_cizgi(390, UST, 450, UST, KIR))
    o.append(_cizgi(450, UST, 450, KUTU_Y, KIR))
    o.append(ucbas(450, KIR, "J7 · 1", "direncin ucu"))
    o.append(_cizgi(190, KUTU_Y, 190, 170, SIY))
    o.append(_cizgi(190, 170, 85, 170, SIY))
    o.append(_cizgi(85, 170, 85, 120, SIY))
    o.append(ucbas(190, SIY, "J7 · 2", "pilin eksisi"))
    o.append(_cizgi(350, KUTU_Y, 350, 140, KIR, 2.0, True))
    o.append(_cizgi(350, 140, 210, 140, KIR, 2.0, True))
    o.append(_cizgi(210, 140, 210, UST, KIR, 2.0, True))
    o.append(ucbas(350, KIR, "V jakı", "pilin artısı"))
    o.append(_cizgi(260, KUTU_Y, 260, 170, "#2b2b2b", 2.0, True))
    o.append(ucbas(260, "#2b2b2b", "COM", "pilin eksisi", 1))
    o.append(_yazi(300, 320, "Kart Q1 ile yükü açıp kapatıyor, şöntten akımı okuyor, "
                             "kesme gerilimine inince kendi kesiyor.", 11, "var(--m2)"))
    return _svg("".join(o), 600, 336, "Pil kapasite testi")



# ═══════════════════════════════════════════════════════════════════════
#  3B SAHNE — tarayicida dondurulebilen gorunum
# ═══════════════════════════════════════════════════════════════════════

def sahne() -> list[dict]:
    """Kutunun 3B blok listesi.

    Kullanici (2026-09-20): "3D uzayda hareket edebileyim, saginA soluna
    bakabileyim." Dis kutuphane YOK: blok listesi burada uretiliyor,
    tarayicida ~120 satirlik ressam algoritmasi ciziyor (cevrimdisi da
    calissin, belgeler tek dosya kalsin).

    gor: bu alt adim indeksinden itibaren gorunur · vur: parlayacagi indeks
    """
    c, kb, h = K.CUBUK, K.KUTU, hesap()
    aa = alt_adimlar()
    ix = {x["no"]: i for i, x in enumerate(aa)}
    monte = monte_adim()
    bloklar = []

    def blok(ad, x, y, z, dx, dy, dz, renk, grup, gor, vur=None):
        bloklar.append({"ad": ad, "x": round(x, 1), "y": round(y, 1), "z": round(z, 1),
                        "dx": round(dx, 1), "dy": round(dy, 1), "dz": round(dz, 1),
                        "r": renk, "g": grup, "gor": gor,
                        "vur": [v for v in (vur or []) if v is not None]})

    k, g = c["kalinlik"], c["genislik"]
    # Taban ve kapak: her cubuk AYRI blok. Hem gercege yakin duruyor hem de
    # ressam algoritmasi buyuk tek yuzeyde parcalari ortuyordu.
    for i in range(h["taban_adet"]):
        x = i * g
        en = min(g - 0.6, kb["ic_en"] - x)
        if en <= 0:
            break
        blok(f"Taban çubuğu {i + 1}", x, 0, -k, en, kb["ic_boy"], k,
             "#c3a173", "kutu", ix["2.1"], [ix["2.1"], ix["2.2"]])
    for ry in (0.18, 0.82):
        blok("Taban rayı", 0, kb["ic_boy"] * ry - g / 2, -2 * k, kb["ic_en"], g, k,
             "#e0a92f", "kutu", ix["2.2"], [ix["2.2"]])
    # Duvarlar: her sira, her kenar -- gercek kesim parcalarina bolunmus,
    # ek yeri her sirada kaydirilmis (plan da boyle soyluyor).
    def parca_sinirlari(uzunluk, kaydir):
        n = max(1, math.ceil(uzunluk / h["duz"]))
        if n == 1:
            return [(0.0, uzunluk)]
        pay = uzunluk / n
        ilk = pay * (0.65 if kaydir else 1.0)
        sinir, bas = [], 0.0
        for j in range(n):
            boy = ilk if j == 0 else (uzunluk - ilk) / (n - 1)
            sinir.append((bas, boy))
            bas += boy
        return sinir

    for r in range(kb["duvar_sira"]):
        z = r * g
        gor = ix["3.1"] if r == 0 else ix["3.3"]
        gor_yan = ix["3.2"] if r == 0 else ix["3.3"]
        kaydir = r % 2 == 1
        for bas, boy in parca_sinirlari(kb["ic_en"] + 2 * k, kaydir):
            blok(f"Arka duvar {r + 1}", bas - k, kb["ic_boy"], z, boy - 0.4, k, g,
                 "#c3a173", "duvar", gor, [gor])
            blok(f"Ön duvar {r + 1}", bas - k, -k, z, boy - 0.4, k, g,
                 "#c3a173", "duvar", gor, [gor])
        for bas, boy in parca_sinirlari(kb["ic_boy"], not kaydir):
            blok(f"Sol duvar {r + 1}", -k, bas, z, k, boy - 0.4, g,
                 "#b0915f", "duvar", gor_yan, [gor_yan])
            blok(f"Sağ duvar {r + 1}", kb["ic_en"], bas, z, k, boy - 0.4, g,
                 "#b0915f", "duvar", gor_yan, [gor_yan])
    for x in panel_ogeleri():
        on = x["panel"] == "ön"
        y0 = kb["ic_boy"] if on else -k - 14
        w = x["metal_mm"] or 12
        gor = ix.get(monte.get(x["ref"].split(".")[0], ""), ix["5.1"])
        blok(x["etiket"], x["x"] - w / 2, y0, x["z"] - w / 2, w, k + 14, w,
             JAK_RENK.get(x["renk"], "#8a8a85"), "panel", gor, [gor])
    for pp in K.IC_PARCA:
        gor = ix.get(monte.get(pp["ref"], ""), None)
        if gor is None:
            gor = ix["6.2"] if pp["ref"] == "A" else ix["6.3"]
        blok(pp["ref"], pp["x"], pp["y"], 0, pp["en"], pp["boy"],
             max(pp["yuk"] * 0.55, 6), PARCA_RENK.get(pp["ref"], "#666"),
             "parca", gor, [gor])
    for i in range(h["taban_adet"] + 1):
        x = -k + i * g
        en = min(g - 0.6, kb["ic_en"] + k - x)
        if en <= 0:
            break
        blok(f"Kapak çubuğu {i + 1}", x, -k, h["ic_yuk"], en, kb["ic_boy"] + 2 * k, k,
             "#d9bb8c", "kapak", ix["13.1"], [ix["13.1"]])
    return bloklar

# ═══════════════════════════════════════════════════════════════════════
#  BELGE
# ═══════════════════════════════════════════════════════════════════════

def _liste(xs) -> str:
    return "<ul class='is'>" + "".join(f"<li>{x}</li>" for x in xs) + "</ul>"


def _tablo(bas, satirlar) -> str:
    return ("<table><tr>" + "".join(f"<th>{b}</th>" for b in bas) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{h}</td>" for h in s) + "</tr>"
                      for s in satirlar) + "</table>")


def kablo_tablosu(idx) -> str:
    sat = []
    for i in idx:
        a, b, tur, _adim, notu = V.KABLOLAR[i]
        sat.append((E(B._uc_adi(a)), E(B._uc_adi(b)),
                    "<b>KALIN KABLO</b>" if tur == "yuk" else E(tur),
                    f"<span class='kucuk'>{E(notu)}</span>"))
    return _tablo(("Nereden", "Nereye", "Tür", "Not"), sat)


def cizimler(s: dict) -> str:
    """Alt adimin gorunusleri — turune gore."""
    vurgu = set(s.get("vurgu", [])) | set(s.get("monte", []))
    tur = s["tur"]
    c = []
    if tur == "kesim":
        c.append(("Kesim listesi", ciz_kesim()))
    elif tur == "taban":
        c.append(("Kapak" if s.get("kapak") else "Taban — kuşbakışı",
                  ciz_taban(s.get("kapak", False))))
    elif tur == "duvar":
        c.append((f"{s['sira']}. sıra — izometrik", ciz_duvar(s["sira"])))
    elif tur == "delik":
        c.append((f"{s.get('panel', 'ön').capitalize()} duvar",
                  ciz_panel(s.get("panel", "ön"), vurgu)))
        if vurgu:
            c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
    elif tur == "montaj":
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
        c.append(("İzometrik", ciz_izo(vurgu)))
    elif tur == "kablo":
        c.append(("Kuşbakışı", ciz_yerlesim(vurgu)))
        if any(r in {o["ref"] for o in panel_ogeleri("ön")} for r in vurgu):
            c.append(("Ön duvar", ciz_panel("ön", vurgu)))
        if any(r in {o["ref"] for o in panel_ogeleri("arka")} for r in vurgu):
            c.append(("Arka duvar", ciz_panel("arka", vurgu)))
    return "".join(f"<figure><figcaption>{E(b)}</figcaption>{sv}</figure>"
                   for b, sv in c)


def alt_kart(s: dict, nl, parcalar, stok, h) -> str:
    kb = K.KUTU
    bicim = {"u": K.CUBUK["uzunluk"], "g": K.CUBUK["genislik"],
             "k": K.CUBUK["kalinlik"], "sira": kb["duvar_sira"], "h": h["ic_yuk"],
             "ue": K.CUBUK["uc_egim"], "duz": h["duz"]}
    ic = [f"<div class='aa-bas'><span class='ano'>{E(s['no'])}</span> "
          f"<b>{E(s['baslik'])}</b>"
          f"<label class='yaptim'><input type='checkbox'> yaptım</label></div>"]
    ic.append("<div class='aa-ic'>")
    if s.get("monte"):
        def _stok(r):
            # once panel parcasi, yoksa ic parcanin stok alani (RS, Q1 ...)
            kayit = next((o["parca"] for o in panel_ogeleri()
                          if o["ref"].split(".")[0] == r and o["parca"]), None)                 or next((p.get("stok") for p in K.IC_PARCA if p["ref"] == r), None)
            return stok.ad_ile(*kayit) if (kayit and stok.var) else ""
        ic.append(_tablo(("Kutuya giren", "Kural", "Stokta"),
                         [(f"<b>{E(r)}</b>", E(V.KART_DISI_NOTU.get(r, "")), _stok(r))
                          for r in s["monte"]]))
    if s.get("yap"):
        ic.append(_liste(x.format(**bicim) for x in s["yap"]))
    ic.append(cizimler(s))
    if s["tur"] == "kesim" and s["no"].endswith(".2"):
        ic.append(_tablo(("Parça", "Uzunluk", "Adet"),
                         [(E(ad), f"{u:.0f} mm", f"<b>{int(adet)}</b>")
                          for ad, u, adet in h["parcalar"]]))
        ic.append(f"<div class='uy'>Toplam <b>{h['cubuk_sayisi']} çubuk</b> gerekiyor "
                  f"(150 mm'lik çubuklardan, 1 mm testere payıyla hesaplandı). "
                  f"Ön/arka duvar bir çubuktan uzun: her sıra bir tam çubuk + "
                  f"<b>{h['ek_parca']:.0f} mm</b> ek parça.</div>")
    if s.get("kablo"):
        ic.append("<h4>Bağlanacak kablolar</h4>")
        ic.append(kablo_tablosu(s["kablo"]))
    if s["no"] == "9.3":
        ic.append("<h4>Yol kontrolü — jaktan karta</h4>")
        ic.append("<p class='kucuk'>Bölücüler GND'ye değil VREF'e iniyor, bu yüzden "
                  "jak ile COM arası enerji yokken sonsuz okur. Anlamlı ölçüm jak ile "
                  "VREF arası: kartta U3'ün 1. bacağı, delik <b>A:R8</b>.</p>")
        ic.append(_tablo(("Uç 1", "Uç 2", "Beklenen"),
                         [(E(ad), "A:R8 (VREF)", f"<b>≈ {B._oku(r)}</b> (±%2)")
                          for ad, _ag, r in giris_direncleri(nl, parcalar)]))
    if s["tur"] == "kalibrasyon":
        ic.append("<p class='kucuk'>Seri konsoldan (USB). Her komut ayarı NVS'e yazar, "
                  "elektrik kesilse de kalır.</p>")
        ic.append(_tablo(("Komut", "Ne yapar", "Ne zaman"),
                         [(f"<code>{k}</code>", E(n), E(z)) for k, n, z in K.KALIBRASYON]))
    for k in s.get("kapi", []):
        gerek = ", ".join(sorted(kapi_gerek().get(k, set()))) or "—"
        ic.append(f"<div class='ok'><b>KAPI {k}</b> — {B.KAPI.get(k, '')}"
                  f"<div class='kucuk'>gerekli kart dışı parça: {E(gerek)}</div></div>")
    if s.get("kontrol"):
        ic.append("<h4>Kontrol</h4>")
        ic.append(_liste(s["kontrol"]))
    ic.append("</div>")
    return f"<li class='aa' data-no='{E(s['no'])}'>" + "".join(ic) + "</li>"


def yaz(nl, parcalar, hedef: Path) -> None:
    stok = B.Stok()
    h = hesap()
    c, kb = K.CUBUK, K.KUTU
    aa = alt_adimlar()
    g = []

    g.append("<h2>Bu belge ne</h2>")
    g.append(_liste([
        "Kartlar bitti. Bundan sonrası: <b>çubuktan kutu</b>, panel delikleri, "
        "şönt ve Q1, jaklar, kablolar ve testler.",
        f"Kutu <b>{c['ad']}</b> ({c['uzunluk']:.0f} × {c['genislik']:.0f} × "
        f"{c['kalinlik']:.0f} mm) çubuklardan yapılıyor. İç ölçü "
        f"<b>{kb['ic_en']:.0f} × {kb['ic_boy']:.0f} × {h['ic_yuk']:.0f} mm</b>; "
        f"duvar {kb['duvar_sira']} sıra çubuk.",
        "Aşağıda <b>ileri / geri</b> ile tek tek ilerle. Her alt adımın çizimi "
        "var; “yaptım” işaretleri bu tarayıcıda saklanır.",
        "<b>3B görünüm</b> adım şeridinin hemen altında: sürükleyip döndür, "
        "tekerlekle yakınlaştır. Soluk çizilenler <b>henüz yapmadıkların</b> — "
        "yani hedef. Tezgâhta <b>telefondan</b> bakmak için bilgisayarda "
        "<code>python uretim/belge_sun.py</code> çalıştır; yazdığı adresi "
        "telefonda aç (aynı Wi-Fi).",
        "İleride 3D baskı kutuya geçersen yalnız 1–5. adımlar değişir; elektrik "
        "adımları (6–13) aynı kalır.",
    ]))
    bicim_al = dict(kb, cubuk=h["cubuk_sayisi"],
                    cubuk_pay=int(h["cubuk_sayisi"] * 1.15 + 0.5))
    g.append(_tablo(("Ne", "Açıklama"),
                    [(f"<b>{E(a)}</b>", E(b.format(**bicim_al))) for a, b in K.ALINACAK]))

    kartlar = "".join(alt_kart(s, nl, parcalar, stok, h) for s in aa)
    basliklar = json.dumps([{"no": s["no"], "b": s["baslik"], "a": s["adim"],
                             "ab": s["adim_baslik"]} for s in aa], ensure_ascii=False)
    adim_dugme = "".join(
        f"<button data-git='{a['no']}'>{a['no']}</button>" for a in K.ADIMLAR)

    g.append(f"""
<div class="gorus">
  <div class="gorus-ust">
    <button id="geri">◀ geri</button>
    <div class="gorus-bilgi"><span class="ano" id="g-no"></span>
      <b id="g-baslik"></b> <span class="rozet" id="g-adim"></span></div>
    <button id="ileri">ileri ▶</button>
  </div>
  <div class="gorus-alt"><div class="adimsec">{adim_dugme}</div>
    <span class="kucuk" id="g-sayac"></span></div>
  <div class="cubuk"><div id="g-cubuk"></div></div>
</div>
<div class="uc-boyut">
  <div class="uc-ust">
    <button id="uc-katla" aria-expanded="true">▾</button>
    <b>3B görünüm</b>
    <span class="kucuk">sol tuş: döndür · orta/sağ tuş ya da Shift: kaydır ·
      tekerlek: yakınlaştır · çift tık: sıfırla</span>
    <span class="uc-dugmeler">
      <button data-gorus="izo">izometrik</button>
      <button data-gorus="ust">üst</button>
      <button data-gorus="on">ön</button>
      <button data-gorus="arka">arka</button>
      <button data-gorus="sol">sol</button>
      <button data-gorus="sag">sağ</button>
      <label class="kucuk"><input type="checkbox" id="uc-hedef" checked> hedefi göster</label>
      <label class="kucuk"><input type="checkbox" id="uc-saydam"> duvarlar saydam</label>
      <label class="kucuk"><input type="checkbox" id="uc-hepsi"> hepsini göster</label>
    </span>
  </div>
  <div id="uc-govde">
    <canvas id="uc-tuval" height="420"></canvas>
    <div class="kucuk" id="uc-bilgi" style="margin-top:6px"></div>
  </div>
</div>
<ol class="aalist" id="aalist">{kartlar}</ol>""")

    g.append("<section class='buyuk'><h2>Bitince: neyi nereden ölçerim</h2>")
    g.append(_tablo(("Ölçüm", "Hangi uç", "Nasıl bağlanır", "Çözünürlük"),
                    [(f"<b>{E(a)}</b>", f"<b>{E(b)}</b>", c2,
                      f"<span class='kucuk'>{E(d)}</span>")
                     for a, b, c2, d in K.KULLANIM]))
    g.append("<h3>Akım ve gerilim ölçümü — bağlantı</h3>")
    g.append("<figure><figcaption>YÜK klemensi (J3) devreye SERİ girer</figcaption>"
             + ciz_kullanim("akim") + "</figure>")
    g.append(_liste([
        "<b>J3 (YÜK)</b> bir giriş değil, <b>akımın geçtiği yol</b>. Ölçmek istediğin "
        "devrenin dönüş (eksi) hattını kes: devreden gelen ucu <b>J3.1</b>'e, kaynağa "
        "giden ucu <b>J3.2</b>'ye vidala. Akım şöntün üstünden geçer, kart okur.",
        "Aynı anda gerilim de istiyorsan <b>V jakını</b> devrenin artısına, "
        "<b>COM jakını</b> kaynağın eksisine (yani J3.2 tarafına) bağla.",
        "Artı hattına hiç dokunmuyoruz; kart hep <b>eksi/dönüş</b> tarafından ölçüyor.",
    ]))
    g.append("<h3>Pil kapasite testi — bağlantı</h3>")
    g.append("<figure><figcaption>PİL klemensi (J7) deşarj yolu</figcaption>"
             + ciz_kullanim("pil") + "</figure>")
    g.append(_liste([
        "<b>J7 (PİL)</b> da bir giriş değil, kartın açıp kapattığı <b>deşarj yolu</b>. "
        "Pilin artısı yük direncine, direncin öbür ucu <b>J7.1</b>'e, pilin eksisi "
        "<b>J7.2</b>'ye gider.",
        "Yük direncini sen seçiyorsun; akım = pil gerilimi ÷ direnç. Örnek: 3.7 V "
        "18650 + 3.3 Ω → ~1.1 A, direnç ~4 W harcar (11 W taş direnç uygun).",
        "Pilin gerilimini de görmek için V jakını pilin artısına bağla; COM zaten "
        "pilin eksisinde (J7.2).",
        "Q1 soğutucusuz <b>6.5 A</b>'e kadar; daha fazlasını isteme.",
    ]))
    g.append("</section>")

    ek_stil = """
.gorus{position:sticky;top:0;z-index:9;background:var(--yz);border:1px solid var(--cizgi);
       border-radius:14px;padding:10px 12px;margin:18px 0}
.gorus-ust{display:flex;align-items:center;gap:12px}
.gorus-ust button{font:inherit;padding:6px 14px;border-radius:99px;cursor:pointer;
       border:1px solid var(--cizgi);background:var(--yz2);color:var(--m1)}
.gorus-bilgi{flex:1;text-align:center}
.gorus-alt{display:flex;justify-content:space-between;align-items:center;margin-top:8px}
.adimsec button{font:inherit;font-size:12px;padding:2px 9px;margin-right:4px;
       border-radius:99px;border:1px solid var(--cizgi);background:transparent;
       color:var(--m2);cursor:pointer}
.adimsec button.sec{background:var(--s1);color:#fff;border-color:var(--s1)}
.cubuk{height:4px;background:var(--cizgi);border-radius:2px;margin-top:8px}
.cubuk div{height:100%;background:var(--s3);border-radius:2px;width:0}
.uc-boyut{border:1px solid var(--cizgi);border-radius:14px;padding:10px 12px;margin:14px 0;
          background:var(--yz2);scroll-margin-top:104px}
.uc-ust{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
#uc-katla{font:inherit;width:28px;height:28px;border-radius:8px;cursor:pointer;
          border:1px solid var(--cizgi);background:var(--yz);color:var(--m1)}
#uc-govde[hidden]{display:none}
.uc-dugmeler{margin-left:auto;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.uc-dugmeler button{font:inherit;font-size:12px;padding:3px 10px;border-radius:99px;
          border:1px solid var(--cizgi);background:var(--yz);color:var(--m1);cursor:pointer}
#uc-tuval{width:100%;display:block;border-radius:10px;cursor:grab;touch-action:none}
#uc-tuval:active{cursor:grabbing}
.aalist{list-style:none;padding:0;margin:0}
.aa{border:1px solid var(--cizgi);border-radius:14px;padding:16px 18px;margin:14px 0;
    scroll-margin-top:104px}
.aa[hidden]{display:none}
.aa-bas{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.ano{font:600 13px ui-monospace,Consolas,monospace;background:var(--s1);color:#fff;
     border-radius:99px;padding:2px 10px}
.yaptim{margin-left:auto;font-size:13px;color:var(--m2);cursor:pointer}
ul.is{margin:8px 0 14px;padding-left:20px}
ul.is li{margin:6px 0}
figure{margin:14px 0;padding:10px;border:1px solid var(--cizgi);border-radius:10px;
       background:var(--yz2);overflow-x:auto}
figure figcaption{font-size:12px;color:var(--m3);margin-bottom:6px}
figure svg{width:100%;min-width:460px;height:auto;display:block}
@media (max-width:640px){
  figure svg{min-width:340px}
  .uc-ust{font-size:13px}
  .uc-dugmeler{margin-left:0}
  .gorus-ust button{padding:8px 12px}
}
h4{margin:16px 0 6px;font-size:14px;color:var(--m2);text-transform:uppercase;
   letter-spacing:.04em}
"""
    js = """<script>
(function(){
 var S = __ALTADIM__;
 var kartlar = [].slice.call(document.querySelectorAll('.aa'));
 var cur = 0, yaptim = {};
 try { yaptim = JSON.parse(localStorage.getItem('kutu-yaptim') || '{}'); } catch(e) {}
 function kaydet(){ try { localStorage.setItem('kutu-yaptim', JSON.stringify(yaptim)); } catch(e) {} }

 // ── 3B: dis kutuphane yok. Ortografik izdusum + ressam algoritmasi.
 var SAHNE = __SAHNE__;
 var tuval = document.getElementById('uc-tuval'), ctx = tuval.getContext('2d');
 var yaw = -0.62, pitch = 0.52, zoom = 1, surukle = null, pan = {x: 0, y: 0};
 var merkez = (function(){
   var x0 = 1e9, y0 = 1e9, z0 = 1e9, x1 = -1e9, y1 = -1e9, z1 = -1e9;
   SAHNE.forEach(function(b){
     x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); z0 = Math.min(z0, b.z);
     x1 = Math.max(x1, b.x + b.dx); y1 = Math.max(y1, b.y + b.dy); z1 = Math.max(z1, b.z + b.dz);
   });
   return {x: (x0 + x1) / 2, y: (y0 + y1) / 2, z: (z0 + z1) / 2, en: x1 - x0, boy: y1 - y0};
 })();
 function izdusum(px, py, pz){
   var x = px - merkez.x, y = py - merkez.y, z = pz - merkez.z;
   var cy = Math.cos(yaw), sy = Math.sin(yaw);
   var X = x * cy - y * sy, Y = x * sy + y * cy;
   var cp = Math.cos(pitch), sp = Math.sin(pitch);
   return {x: X, y: -(z * cp - Y * sp), d: Y * cp + z * sp};
 }
 // Yuzler DISA donuk sarimla: arka yuzler izdusumde ters isaretli alan
 // verir, ayiklaniyor. Onceki surumde sarim tutarsizdi ve ince kutular
 // birbirinin onune geciyordu ("bir kismi yukarida bir kismi asagida").
 var YUZLER = [[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]];
 var NORMAL = [[0,0,-1],[0,0,1],[0,-1,0],[0,1,0],[-1,0,0],[1,0,0]];
 function alan(p){                       // izdusum coklugeninin isaretli alani
   var t = 0;
   for (var i = 0; i < p.length; i++) {
     var q = p[(i + 1) % p.length];
     t += p[i].x * q.y - q.x * p[i].y;
   }
   return t / 2;
 }
 function koseler(b){
   return [[b.x,b.y,b.z],[b.x+b.dx,b.y,b.z],[b.x+b.dx,b.y+b.dy,b.z],[b.x,b.y+b.dy,b.z],
           [b.x,b.y,b.z+b.dz],[b.x+b.dx,b.y,b.z+b.dz],[b.x+b.dx,b.y+b.dy,b.z+b.dz],
           [b.x,b.y+b.dy,b.z+b.dz]];
 }
 function renkle(hex, k, alfa){
   var n = parseInt(hex.slice(1), 16);
   var r = Math.min(255, ((n >> 16) & 255) * k) | 0;
   var g = Math.min(255, ((n >> 8) & 255) * k) | 0;
   var b = Math.min(255, (n & 255) * k) | 0;
   return 'rgba(' + r + ',' + g + ',' + b + ',' + alfa + ')';
 }
 function ciz(){
   var gv = document.getElementById('uc-govde');
   if (gv && gv.hidden) return;
   var op = window.devicePixelRatio || 1;
   var w = tuval.clientWidth, h = w < 620 ? 300 : 420;
   if (tuval.width !== w * op) { tuval.width = w * op; tuval.height = h * op; }
   ctx.setTransform(op, 0, 0, op, 0, 0);
   ctx.clearRect(0, 0, w, h);
   var s = Math.min(w / (merkez.en * 1.9), h / (merkez.boy * 1.25)) * zoom;
   var ox = w / 2 + pan.x, oy = h / 2 + 30 + pan.y;
   var hepsi = document.getElementById('uc-hepsi').checked;
   var saydam = document.getElementById('uc-saydam').checked;
   var hedef = document.getElementById('uc-hedef').checked;
   var kuruldu = SAHNE.filter(function(b){ return b.gor <= cur; }).length;
   document.getElementById('uc-bilgi').textContent = kuruldu
     ? kuruldu + ' parça kuruldu · soluk olanlar sırada'
     : 'henüz parça yok — soluk çizgiler yapacağın kutuyu gösteriyor';
   var kutular = [];          // ressam sirasi BLOK duzeyinde
   SAHNE.forEach(function(b){
     var ileride = b.gor > cur;
     if (ileride && !hepsi && !hedef) return;
     if (b.g === 'kapak' && ileride && !hepsi) return;
     var vur = b.vur.indexOf(cur) >= 0;
     var alfa = (b.g === 'duvar' || b.g === 'kapak') ? (saydam ? 0.18 : 0.92) : 0.97;
     if (!vur && b.g === 'parca') alfa = 0.85;
     if (ileride) alfa = 0.10;              // hedef onizlemesi: soluk hayalet
     var om = izdusum(b.x + b.dx / 2, b.y + b.dy / 2, b.z + b.dz / 2);
     // OTOMATIK KESIT: kameraya kutu merkezinden DAHA YAKIN duvarlar
     // soluklasir, yoksa on duvar icerideki parcalari kapatiyor.
     if (!ileride && (b.g === 'duvar' || b.g === 'kapak') && om.d > 0)
       alfa = Math.min(alfa, 0.22);
     var ks = koseler(b).map(function(p){ return izdusum(p[0], p[1], p[2]); });
     var yuzler = [];
     YUZLER.forEach(function(y, i){
       var pts = y.map(function(j){ return ks[j]; });
       if (alan(pts) <= 0) return;        // arka yuz: cizme
       var n = NORMAL[i];
       var isik = 0.62 + 0.38 * Math.abs(n[0] * 0.4 + n[1] * 0.25 + n[2] * 0.88);
       var d = (pts[0].d + pts[1].d + pts[2].d + pts[3].d) / 4;
       yuzler.push({d: d, p: pts,
                    renk: renkle(b.r, vur ? isik * 1.25 : isik, alfa),
                    kenar: vur ? '#f2c14e' : 'rgba(0,0,0,.35)', kalin: vur ? 2 : 0.6});
     });
     yuzler.sort(function(x, y){ return x.d - y.d; });
     if (!ileride && ((b.g === 'parca' && b.ad.length <= 6) || (vur && b.g !== 'duvar'))) {
       var m = izdusum(b.x + b.dx / 2, b.y + b.dy / 2, b.z + b.dz + 3);
       yuzler.push({yazi: b.ad, x: m.x, y: m.y, vur: vur});
     }
     // Blok derinligi = merkez + kucuk bir "yukseklik" payi: zeminde duran
     // parcalar (z=0..13) zemin cubugunun (z=-2..0) ARDINDAN cizilsin.
     // Taban/kapak cubuklari kutunun ALTINDA: derinlikleri parcalarla
     // yarisinca uzun zemin cubuklari uzerindeki parcayi ortuyordu -> zemini
     // her zaman once ciz.
     kutular.push({d: om.d + (b.g === 'kutu' ? -1e3 : 0) + (b.z + b.dz) * 0.02,
                   yuzler: yuzler});
   });
   kutular.sort(function(x, y){ return x.d - y.d; });
   var cizilecek = [];
   kutular.forEach(function(k){ cizilecek = cizilecek.concat(k.yuzler); });
   cizilecek.forEach(function(f){
     if (f.yazi) {
       ctx.font = (f.vur ? '600 ' : '') + '12px ui-monospace,Consolas,monospace';
       ctx.textAlign = 'center';
       ctx.fillStyle = f.vur ? '#f2c14e' : 'rgba(255,255,255,.75)';
       ctx.strokeStyle = 'rgba(0,0,0,.55)'; ctx.lineWidth = 3;
       ctx.strokeText(f.yazi, ox + f.x * s, oy + f.y * s);
       ctx.fillText(f.yazi, ox + f.x * s, oy + f.y * s);
       return;
     }
     ctx.beginPath();
     f.p.forEach(function(q, i){
       var X = ox + q.x * s, Y = oy + q.y * s;
       if (i === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y);
     });
     ctx.closePath();
     ctx.fillStyle = f.renk; ctx.fill();
     ctx.lineWidth = f.kalin; ctx.strokeStyle = f.kenar; ctx.stroke();
   });
 }
 tuval.addEventListener('contextmenu', function(e){ e.preventDefault(); });
 tuval.addEventListener('pointerdown', function(e){
   // sol tus: dondur · orta/sag tus ya da Shift: kaydir (Blender gibi)
   surukle = {x: e.clientX, y: e.clientY,
              kaydir: e.button === 1 || e.button === 2 || e.shiftKey};
   tuval.setPointerCapture(e.pointerId);
   e.preventDefault();
 });
 tuval.addEventListener('pointermove', function(e){
   if (!surukle) return;
   var dx = e.clientX - surukle.x, dy = e.clientY - surukle.y;
   if (surukle.kaydir) { pan.x += dx; pan.y += dy; }
   else {
     yaw += dx * 0.01;
     pitch = Math.max(-0.2, Math.min(1.45, pitch + dy * 0.008));
   }
   surukle = {x: e.clientX, y: e.clientY, kaydir: surukle.kaydir}; ciz();
 });
 tuval.addEventListener('pointerup', function(){ surukle = null; });
 tuval.addEventListener('dblclick', function(){       // cift tikla: sifirla
   pan = {x: 0, y: 0}; zoom = 1; yaw = -0.62; pitch = 0.52; ciz();
 });
 tuval.addEventListener('wheel', function(e){
   e.preventDefault(); zoom = Math.max(0.4, Math.min(4, zoom * (e.deltaY < 0 ? 1.12 : 0.9))); ciz();
 }, {passive: false});
 // Ekseni: +x saga, +y ARKAYA, +z yukari. "on" = on duvara bakmak (y ekseni
 // bize dogru), "sag" = sag duvar (x = ic_en) karsimizda. Onceki surumde
 // sag/sol terstiydi.
 var GORUSLER = {izo: [-0.62, 0.52], ust: [-0.0001, 1.45], on: [0, 0.02],
                 arka: [3.1416, 0.02], sag: [1.5708, 0.02], sol: [-1.5708, 0.02]};
 [].forEach.call(document.querySelectorAll('[data-gorus]'), function(b){
   b.addEventListener('click', function(){
     var g = GORUSLER[b.dataset.gorus];
     yaw = g[0]; pitch = g[1]; pan = {x: 0, y: 0}; zoom = 1; ciz();
   });
 });
 document.getElementById('uc-saydam').addEventListener('change', ciz);
 document.getElementById('uc-hedef').addEventListener('change', ciz);
 // panel acilir-kapanir; tercih tarayicida saklanir
 var katla = document.getElementById('uc-katla');
 var govde = document.getElementById('uc-govde');
 function katlaUygula(kapali){
   govde.hidden = kapali;
   katla.textContent = kapali ? '▸' : '▾';
   katla.setAttribute('aria-expanded', kapali ? 'false' : 'true');
   try { localStorage.setItem('kutu-3b-kapali', kapali ? '1' : ''); } catch(e) {}
   if (!kapali) ciz();
 }
 katla.addEventListener('click', function(){ katlaUygula(!govde.hidden); });
 var kapaliBas = false;
 try { kapaliBas = localStorage.getItem('kutu-3b-kapali') === '1'; } catch(e) {}
 katlaUygula(kapaliBas);
 document.getElementById('uc-hepsi').addEventListener('change', ciz);
 window.addEventListener('resize', ciz);

 function kaydirGor(el){
   // serit telefonda 3 satira sariyor: sabit scroll-margin yetmiyordu,
   // yuksekligi CALISMA ANINDA olcuyoruz.
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
   [].forEach.call(document.querySelectorAll('.adimsec button'), function(b){
     b.classList.toggle('sec', String(s.a) === b.dataset.git); });
   try { history.replaceState(null, '', '#a' + s.no); } catch(e) {}
   ciz();
   // 3B panel kartin USTUNDE: ona kaydiriyoruz ki adim degisince hem kutuyu
   // hem metni goresin (kullanici 'kutuyu hazirlarken 3B'ye bakamiyorum' dedi).
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
   b.addEventListener('click', function(){
     for (var i = 0; i < S.length; i++) if (String(S[i].a) === b.dataset.git) { goster(i, true); return; }
   });
 });
 document.addEventListener('keydown', function(ev){
   if (ev.target.closest && ev.target.closest('input,textarea,select')) return;
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
</script>""".replace("__ALTADIM__", basliklar).replace(
        "__SAHNE__", json.dumps(sahne(), ensure_ascii=False))

    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kutu ve panel — Ölçüm Kartı</title><style>{B.stil()}{ek_stil}</style></head><body>
<div class="kutu">{MN.serit('8-kutu.html')}
<h1>Kutu ve panel</h1>
<p class="alt">Çubuktan kutu, panel delikleri, şönt ve Q1, jaklar, kablolar —
alt adım alt adım, her birinin çizimiyle. Sonunda hangi ölçümü nereden
yapacağın yazıyor.</p>
{''.join(g)}
<p class="kucuk" style="margin-top:60px;border-top:1px solid var(--cizgi);padding-top:14px">
Bu sayfa <code>uretim/kutu.py</code> tarafından, denetim geçtikten sonra üretildi.
Kutu ölçüleri ve adımlar <code>kutu_veri.py</code>'den, kablolar
<code>yerlesim3_veri.KABLOLAR</code>'dan, KAPI metinleri
<code>yerlesim3_belge.KAPI</code>'dan geliyor; çizimler aynı sayılardan üretiliyor.</p>
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
