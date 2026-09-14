# -*- coding: utf-8 -*-
"""Delikli plaket YERLESIMI — ayak izleri, yol uretici, denetim, cizim.

    python yerlesim3.py                  denetim (+ BELGELER/7-yerlesim.html)
    python yerlesim3.py --ascii          yerlesimi konsola ciz (gelistirme)
    python yerlesim3.py --yol-uret       lehim yuzu tellerini YENIDEN uret
    python yerlesim3.py --belge-yok      yalnizca denetim

Veri `yerlesim3_veri.py`'de (parca konumlari, kart disi kablolar, bacak
siralari). Teller `yerlesim3_teller.json`'da — kullanicinin lehimleyecegi
plan ODUR; yol uretici yalnizca `--yol-uret` ile calisir, yani bir parca
kaydirildiginda butun teller sessizce yeniden dizilmez.

── DENETIM YOL URETICIYE GUVENMIYOR ──────────────────────────────────

Yol uretici her tele bir `ag` adi yazar. Denetim o adi KULLANMAZ: baglantiyi
yalnizca geometriden (hangi delik hangi delige bakirla bagli) ve kart disi
kablolardan yeniden kurar, sonra `netlist3.net` ile birebir karsilastirir.
Uretici bir teli yanlis agla etiketlese ya da iki agi bir delikte birlestirse
etiket yalan soyler ama geometri soylemez.

── NEYI DENETLER ─────────────────────────────────────────────────────

  * her netlist pini bir yerde ve TEK kez; ayak izi pinleri netlistle ayni
  * acik devre yok, kisa devre yok (netlist ↔ bakir birebir)
  * HER KURULUM ADIMINDA da ayni sey — kilavuzun "KAPI — gecmeden
    ilerleme" olcumu yarim kurulmus kartta yapiliyor; o anki bakir o
    adima kadar takilan parcalari tam baglamali
  * govdeler cakismiyor, bacaklar baska govdenin altina dusmuyor
  * TO-92/TO-220/ADS bacaklari NUMARAYLA degil ISLEVLE eslesiyor
    (2N2222-331 E-B-C, sema sembolu BC547 C-B-E)
  * Kelvin: sont algilama uclari kartta YALNIZ; toprak TEK noktadan
    guc yoluna bagli; yuk akimi plakete hic girmiyor
  * kacak yolu (IEC 60664-1 Tablo F.4): bakirdan bakira, merkezden
    merkeze DEGIL
  * ayirma kondansatorleri bakir yolu uzunluguyla pinlerine yakin
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))

from netlist_dogrula import netleri_oku                 # noqa: E402
from tezgah import tezgah                               # noqa: E402
import tasarim3_sabit as T                              # noqa: E402
import yerlesim3_veri as V                              # noqa: E402

NETLIST = BURASI / "netlist3.net"
TELLER = BURASI / "yerlesim3_teller.json"
BELGE = KOK / "BELGELER" / "7-yerlesim.html"

ADIM_MM = T.DELIKLI_ADIM


# ═══════════════════════════════════════════════════════════════════════
#  AYAK IZLERI — delik biriminde; x saga, y asagi; PARCA YUZUNDEN bakis
# ═══════════════════════════════════════════════════════════════════════
# pin   : anahtar -> [(dx, dy), ...]  (bir pinin birden fazla deligi olabilir)
# govde : (x0, y0, x1, y1) parca yuzundeki izdusum
# bos   : bacak girmeyen ama DOLU sayilan delikler (tel gerginlik deligi)
# ic_bag: bir pinin delikleri parcanin KENDI metaliyle bagli mi (sigorta
#         klipsi evet; iki paralel kondansator HAYIR — bakirla baglanmali)
AYAKLAR: dict[str, dict] = {
    # 1/4 W metal film: govde 6.3 x 2.4 mm, bacak 4 adim (10.16 mm)
    "R4": {"pin": {"1": [(0, 0)], "2": [(4, 0)]},
           "govde": (0.76, -0.47, 3.24, 0.47)},
    # 1/4 W DIK montaj: govde pin 1'in ustunde, bacak kivrilip pin 2'ye
    # iner. Yalnizca DUSUK GERILIMDE (HV zincirinde yatay kalir).
    "R1D": {"pin": {"1": [(0, 0)], "2": [(1, 0)]},
            "govde": (-0.48, -0.48, 1.3, 0.48)},
    # 1/2 W (R40, R030): govde ~9 x 3.2 mm, bacak 5 adim
    "R5": {"pin": {"1": [(0, 0)], "2": [(5, 0)]},
           "govde": (0.73, -0.63, 4.27, 0.63)},
    # seramik, 2.5 mm bacak (C051)
    "C1": {"pin": {"1": [(0, 0)], "2": [(1, 0)]},
           "govde": (-0.45, -0.5, 1.45, 0.5)},
    # seramik, 5 mm bacak (C008, C049, C052)
    "C2": {"pin": {"1": [(0, 0)], "2": [(2, 0)]},
           "govde": (-0.4, -0.6, 2.4, 0.6)},
    # "2nF (2x1nF)": IKI ayri disk kondansator, yan yana — bakirla paralel
    "C1x2": {"pin": {"1": [(0, 0), (0, 1)], "2": [(1, 0), (1, 1)]},
             "govde": (-0.45, -0.5, 1.45, 1.5)},
    # film kutu, 15 mm bacak (C022 1uF 400V)
    "C6": {"pin": {"1": [(0, 0)], "2": [(6, 0)]},
           "govde": (-0.55, -1.2, 6.55, 1.2)},
    # radyal elektrolitik 68uF 50V: 8 mm govde varsayildi, bacak 1 adim.
    # pin 1 = ARTI
    "CE": {"pin": {"1": [(0, 0)], "2": [(1, 0)]},
           "govde": (-1.08, -1.58, 2.08, 1.58)},
    # BAT85 DO-34: govde 3 mm; pin 1 = KATOT (bant)
    "D3": {"pin": {"1": [(0, 0)], "2": [(3, 0)]},
           "govde": (0.85, -0.4, 2.15, 0.4)},
    # DIP-8 soket; pin 1 sol ust, 1-4 asagi, 5-8 yukari (standart)
    "DIP8": {"pin": {**{str(i + 1): [(0, i)] for i in range(4)},
                     **{str(8 - i): [(3, i)] for i in range(4)}},
             "govde": (-0.47, -0.47, 3.47, 3.47)},
    # TO-92 / TO-220: L-M-R bacak, islevleri `V.BACAK[kod]`'dan
    "TO92": {"pin": {"L": [(0, 0)], "M": [(1, 0)], "R": [(2, 0)]},
             "govde": (-0.45, -0.8, 2.45, 0.8)},
    "TO220": {"pin": {"L": [(0, 0)], "M": [(1, 0)], "R": [(2, 0)]},
              "govde": (-1.0, -1.4, 3.0, 0.45)},
    # 5x20 sigorta klipsi cifti: klips basina 2 bacak, klips merkezleri
    # 6 adim (15.24 mm). ⚠ Bacak araligi URUNE bagli — yuvayi plakete
    # oturtup dogrula; plan 9 x 3 delik alan ayiriyor.
    "SIG": {"pin": {"1": [(0, 0), (2, 0)], "2": [(6, 0), (8, 0)]},
            "govde": (-0.6, -1.2, 8.6, 1.2), "ic_bag": True},
    # 1x10 erkek pin basligi (J5 -> ESP32)
    "HDR10": {"pin": {str(i + 1): [(i, 0)] for i in range(10)},
              "govde": (-0.5, -0.5, 9.5, 0.5)},
    # ADS1115 modulu, 1x10 disi baslikta; govde basligin SAGINA uzanir
    # (modul ~28 x 18 mm). Bacak islevleri `V.ADS_MODUL` sirasiyla.
    "ADS": {"pin": {f"h{i + 1}": [(0, i)] for i in range(10)},
            "govde": (-0.5, -1.0, 6.5, 10.0)},
    # kart disina giden tel: lehim noktasi + gerginlik deligi
    "TEL": {"pin": {"1": [(0, 0)]}, "bos": [(1, 0)],
            "govde": (-0.5, -0.5, 1.5, 0.5)},
}


def dondur(dx: float, dy: float, aci: int) -> tuple[float, float]:
    """Parca yuzunden bakista SAAT YONUNDE (y asagi) dondurme."""
    a = aci % 360
    if a == 0:
        return dx, dy
    if a == 90:
        return -dy, dx
    if a == 180:
        return -dx, -dy
    if a == 270:
        return dy, -dx
    raise ValueError(f"aci {aci}")


def sutun_adi(x: int) -> str:
    s, n = "", x + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def delik_adi(x: int, y: int) -> str:
    return f"{sutun_adi(x)}{y + 1}"


# ═══════════════════════════════════════════════════════════════════════
#  NETLIST
# ═══════════════════════════════════════════════════════════════════════

class Netlist:
    def __init__(self, dosya: Path):
        ham = netleri_oku(dosya)
        self.ag_pinleri: dict[str, set[str]] = {}
        self.pin_agi: dict[str, str] = {}
        self.islev: dict[str, dict[str, str]] = {}    # ref -> islev -> no
        self.ref_pinleri: dict[str, set[str]] = {}
        for ag, pinler in ham.items():
            kume = set()
            for p in pinler:
                m = re.fullmatch(r"([^.]+)\.([^(]+)(?:\((.*)\))?", p)
                ref, no, isl = m.group(1), m.group(2), m.group(3)
                pid = f"{ref}.{no}"
                kume.add(pid)
                self.pin_agi[pid] = ag
                self.ref_pinleri.setdefault(ref, set()).add(no)
                if isl:
                    self.islev.setdefault(ref, {})[isl] = no
            self.ag_pinleri[ag] = kume
        # parca degerleri (belge icin)
        metin = dosya.read_text(encoding="utf-8")
        self.deger: dict[str, str] = dict(re.findall(
            r'\(comp\s*\(ref "([^"]+)"\)\s*\(value "([^"]*)"\)', metin))
        assert self.deger, "netlist3.net'te parca degeri okunamadi"


# ═══════════════════════════════════════════════════════════════════════
#  PARCALAR — veri + ayak izi -> delikler
# ═══════════════════════════════════════════════════════════════════════

class Parca:
    def __init__(self, ref: str, t: tuple):
        self.ref = ref
        self.kart, ayak, self.x, self.y, self.aci, self.adim = t[:6]
        ek = t[6] if len(t) > 6 else None
        self.kod = None
        if ":" in ayak:
            ayak, self.kod = ayak.split(":", 1)
        self.ayak = ayak
        self.a = AYAKLAR[ayak]
        self.ag = ek if ayak == "TEL" else None     # TEL'in beyan edilen agi

    def _yer(self, dx, dy):
        rx, ry = dondur(dx, dy, self.aci)
        return (int(round(self.x + rx)), int(round(self.y + ry)))

    def pin_anahtarlari(self, nl: Netlist | None) -> dict[str, str]:
        """ayak izi anahtari -> pin kimligi (REF.NO)."""
        out = {}
        for k in self.a["pin"]:
            if self.ayak == "TEL":
                out[k] = f"{self.ref}.1"
            elif self.ayak in ("TO92", "TO220"):
                isl = V.BACAK[self.kod]["LMR".index(k)]
                no = (nl.islev.get(self.ref, {}).get(isl, f"?{isl}")
                      if nl else isl)
                out[k] = f"{self.ref}.{no}"
            elif self.ayak == "ADS":
                isl = V.ADS_MODUL[int(k[1:]) - 1]
                no = (nl.islev.get(self.ref, {}).get(isl, f"?{isl}")
                      if nl else isl)
                out[k] = f"{self.ref}.{no}"
            else:
                out[k] = f"{self.ref}.{k}"
        return out

    def delikler(self, nl: Netlist | None) -> dict[str, list[tuple[int, int]]]:
        """pin kimligi -> delikler."""
        ad = self.pin_anahtarlari(nl)
        out: dict[str, list] = {}
        for k, konumlar in self.a["pin"].items():
            out.setdefault(ad[k], []).extend(self._yer(dx, dy)
                                             for dx, dy in konumlar)
        return out

    def bos_delikler(self) -> list[tuple[int, int]]:
        return [self._yer(dx, dy) for dx, dy in self.a.get("bos", [])]

    def govde(self) -> tuple[float, float, float, float]:
        x0, y0, x1, y1 = self.a["govde"]
        k = [dondur(x0, y0, self.aci), dondur(x1, y1, self.aci)]
        xs = [self.x + p[0] for p in k]
        ys = [self.y + p[1] for p in k]
        return (min(xs), min(ys), max(xs), max(ys))


def parcalari_yukle() -> dict[str, Parca]:
    return {ref: Parca(ref, t) for ref, t in V.YER.items()}


def vida_delikleri(kart: str) -> set[tuple[int, int]]:
    k = V.KARTLAR[kart]
    W, H, n = k["sutun"], k["satir"], V.VIDA_KOSE
    out = set()
    for x in range(W):
        for y in range(H):
            if (x < n or x >= W - n) and (y < n or y >= H - n):
                out.add((x, y))
    return out


def vida_merkezleri(kart: str) -> list[tuple[float, float]]:
    """Vida deliginin merkezi (delik biriminde) — kose bosluklarinin ortasi."""
    k = V.KARTLAR[kart]
    W, H, n = k["sutun"], k["satir"], V.VIDA_KOSE
    c = (n - 1) / 2.0
    return [(c, c), (W - 1 - c, c), (c, H - 1 - c), (W - 1 - c, H - 1 - c)]


# ═══════════════════════════════════════════════════════════════════════
#  GERILIM MODELI — kacak yolu icin
# ═══════════════════════════════════════════════════════════════════════

def gerilim_modeli():
    """ag -> ('zincir', k) ya da ('aralik', vmin, vmax)."""
    kan = {k["kod"]: k for k in T.KANALLAR}
    hv = max(abs(kan["hv"]["fs_alt"]), abs(kan["hv"]["fs_ust"]))
    nor = kan["normal"]
    ray = T.KAYNAK_24V * (1 + T.KAYNAK_24V_TOLERANS) - abs(T.LM7912_VO)
    model = {ag: ("zincir", k) for k, ag in enumerate(V.ZINCIR)}
    model["/V_GIRIS"] = ("aralik", nor["fs_alt"], nor["fs_ust"])
    model["/SKOP_GIRIS"] = ("aralik", T.SKOP_MENZIL_EKSI, T.SKOP_MENZIL_ARTI)
    # ±12 V: hangi rayin regule oldugundan BAGIMSIZ zarf (DEVIR 5.12.25'in
    # "-12 regule" iddiasi baglantiyla celisiyor — ikisini de kapsa)
    for ag in ("+12V", "Net-(J6-Pin_1)"):
        model[ag] = ("aralik", 0.0, abs(T.LM7912_VO) + max(0.0, ray - 12.0) + 2.4)
    model["-12V"] = ("aralik", -(abs(T.LM7912_VO) + max(0.0, ray - 12.0) + 2.4), 0.0)
    return model, hv


def delta_v(a: str, b: str, model, hv) -> float:
    ma = model.get(a, ("aralik", -0.3, 5.0))
    mb = model.get(b, ("aralik", -0.3, 5.0))
    n = len(V.ZINCIR) - 1
    if ma[0] == "zincir" and mb[0] == "zincir":
        return hv * abs(ma[1] - mb[1]) / n
    if ma[0] == "zincir" or mb[0] == "zincir":
        z, o = (ma, mb) if ma[0] == "zincir" else (mb, ma)
        return hv * (n - z[1]) / n + max(abs(o[1]), abs(o[2]))
    return max(abs(ma[2] - mb[1]), abs(mb[2] - ma[1]))


def takviyeli_mi(a: str, b: str, model) -> bool:
    """F9 kurali: zincirin tehlikeli dugumu ile zincir DISI arasi takviyeli."""
    n = len(V.ZINCIR) - 1
    za = model.get(a, ("",))[0] == "zincir" and model[a][1] < n
    zb = model.get(b, ("",))[0] == "zincir" and model[b][1] < n
    return za != zb


def gereken_mm(dv: float, takviyeli: bool) -> float:
    """IEC 60664-1 Tablo F.4, PD2, malzeme grubu III — dogrusal aradeger.
    Kaynak: b15-arastirma.md (TI SLUP421 sl.17: 63/400/800/1000 V satirlari;
    aradeger serbest). 50 V altinda kural uygulanmiyor (tabloda satir yok)."""
    if dv < V.KACAK_ESIK_V:
        return 0.0
    tab = V.IEC_F4
    if dv <= tab[0][0]:
        mm = tab[0][1]
    else:
        mm = tab[-1][1] * dv / tab[-1][0]
        for (v0, m0), (v1, m1) in zip(tab, tab[1:]):
            if v0 <= dv <= v1:
                mm = m0 + (m1 - m0) * (dv - v0) / (v1 - v0)
                break
    return mm * (2.0 if takviyeli else 1.0)


# ═══════════════════════════════════════════════════════════════════════
#  YOL URETICI (yalnizca --yol-uret)
# ═══════════════════════════════════════════════════════════════════════

YONLER = ((1, 0), (0, 1), (-1, 0), (0, -1))


def _yonlendirme_agi(pid: str, nl: Netlist, parcalar) -> str:
    if pid in V.KELVIN_AYRI:
        return V.KELVIN_AYRI[pid]
    ref = pid.split(".")[0]
    p = parcalar.get(ref)
    if p is not None and p.ayak == "TEL":
        return p.ag
    return nl.pin_agi.get(pid, f"?{pid}")


def yol_uret(nl: Netlist, parcalar: dict[str, Parca], sira_anahtari=None) -> dict:
    model, hv = gerilim_modeli()
    cikti = {}
    for kart, kb in V.KARTLAR.items():
        W, H = kb["sutun"], kb["satir"]
        engel = vida_delikleri(kart)
        sahip: dict[tuple, str] = {}         # delik -> ag (pin + iz)
        pin_adimi: dict[tuple, int] = {}
        pinler = []                          # (adim, ag, delik, grup)
        for p in parcalar.values():
            if p.kart != kart:
                continue
            engel.update(p.bos_delikler())
            for pid, dl in p.delikler(nl).items():
                ag = _yonlendirme_agi(pid, nl, parcalar)
                if ag.startswith("unconnected"):
                    for d in dl:
                        sahip[d] = ag
                        pin_adimi[d] = p.adim
                    continue
                grup = tuple(dl) if p.a.get("ic_bag") else None
                for d in dl:
                    sahip[d] = ag
                    pin_adimi[d] = p.adim
                    pinler.append((p.adim, ag, d, grup))
        agac: dict[str, set] = {}
        parcalar_json = []

        def gecilir(d, ag, adim):
            if d in engel:
                return False
            o = sahip.get(d)
            if o is None:
                return True
            if o != ag:
                return False
            # ayni agin HENUZ takilmamis parcasinin deligine lehim akitma
            return pin_adimi.get(d, -1) <= adim

        def ceza(d, ag):
            c = 0.0
            for dx, dy in YONLER:
                o = sahip.get((d[0] + dx, d[1] + dy))
                if o is not None and o != ag:
                    if delta_v(o, ag, model, hv) >= V.KACAK_ESIK_V:
                        return None
                    c += 0.35
            return c

        def ara(bas, hedef, ag, adim):
            pq = [(0.0, bas, -1)]
            en = {(bas, -1): 0.0}
            geri = {}
            while pq:
                c, d, yon = heapq.heappop(pq)
                if en.get((d, yon), 1e18) < c:
                    continue
                if d in hedef and d != bas:
                    yol = [d]
                    s = (d, yon)
                    while s in geri:
                        s = geri[s]
                        yol.append(s[0])
                    return c, yol[::-1]
                for yi, (dx, dy) in enumerate(YONLER):
                    n = (d[0] + dx, d[1] + dy)
                    if not (0 <= n[0] < W and 0 <= n[1] < H):
                        continue
                    if not gecilir(n, ag, adim):
                        continue
                    cz = ceza(n, ag)
                    if cz is None:
                        continue
                    nc = c + 1.0 + cz + (2.0 if yon not in (-1, yi) else 0.0)
                    if nc < en.get((n, yi), 1e18):
                        en[(n, yi)] = nc
                        geri[(n, yi)] = (d, yon)
                        heapq.heappush(pq, (nc, n, yi))
            return None

        # Ag SIRASI adimdan bagimsiz: once kisa yerel aglar, en son raylar.
        # Adim denetimi yine gecerli — her agin agaci KENDI icinde adim
        # sirasiyla buyuyor (yeni parca, o adima kadar kurulmus agaca baglanir).
        def hpwl(ag):
            xs = [d[0] for _a, g, d, _gr in pinler if g == ag]
            ys = [d[1] for _a, g, d, _gr in pinler if g == ag]
            return (max(xs) - min(xs)) + (max(ys) - min(ys))
        # ⚠ Once ADA gore sirala: `set` uzerinden gidilirse esit anahtarli
        #   aglarin sirasi Python'un rastgele dize hash'ine bagli kalir ve
        #   ayni veri her kosuda BASKA plan uretir (olculdu: iki ardisik
        #   --yol-uret farkli JSON yazdi).
        aglar = sorted(sorted({x[1] for x in pinler}),
                       key=(lambda a: sira_anahtari(a, hpwl(a))) if sira_anahtari
                       else (lambda a: (a in V.GUC_AGLARI, hpwl(a))))
        for ag in aglar:
            a_pin = sorted([x for x in pinler if x[1] == ag], key=lambda x: x[0])
            ag_agac = agac.setdefault(ag, set())
            for adim in sorted({x[0] for x in a_pin}):
                while True:
                    kalan = [x for x in a_pin if x[0] == adim and x[2] not in ag_agac]
                    if not kalan:
                        break
                    if not ag_agac:
                        _a, _g, d, grup = kalan[0]
                        ag_agac.update(grup or [d])
                        continue
                    kalan.sort(key=lambda x: min(abs(x[2][0] - t[0]) + abs(x[2][1] - t[1])
                                                 for t in ag_agac))
                    _a, _g, d, grup = kalan[0]
                    if grup and any(g in ag_agac for g in grup):
                        ag_agac.update(grup)
                        continue
                    manh = min(abs(d[0] - t[0]) + abs(d[1] - t[1]) for t in ag_agac)
                    r = ara(d, ag_agac, ag, adim)
                    if r and r[0] <= 1.8 * manh + 6:
                        _c, yol = r
                        for h in yol:
                            if h not in sahip:
                                sahip[h] = ag
                                pin_adimi[h] = adim
                        ag_agac.update(yol)
                        if grup:
                            ag_agac.update(grup)
                        parcalar_json.append({"tur": "iz", "adim": adim, "ag": ag,
                                              "yol": [list(h) for h in yol]})
                    else:
                        hedef = min(ag_agac, key=lambda t: abs(t[0] - d[0]) + abs(t[1] - d[1]))
                        ag_agac.add(d)
                        if grup:
                            ag_agac.update(grup)
                        parcalar_json.append({"tur": "tel", "adim": adim, "ag": ag,
                                              "uclar": [list(d), list(hedef)]})
        cikti[kart] = parcalar_json
    return cikti


def yol_bedeli(teller: dict) -> float:
    """Elle kurulum zahmeti: yalitimli tel pahali, uzun iz de zahmet."""
    b = 0.0
    for liste in teller.values():
        for t in liste:
            if t["tur"] == "iz":
                b += 0.35 * (len(t["yol"]) - 1)
            else:
                (x0, y0), (x1, y1) = t["uclar"]
                b += 6.0 + abs(x0 - x1) + abs(y0 - y1)
    return b


def en_iyi_yol(nl, parcalar, deneme: int = 40):
    """Ag sirasini degistirerek birkac yonlendirme dener, en az zahmetliyi
    secer. Tohum sabit — ayni veri ayni plani uretir."""
    import random
    rnd = random.Random(12345)
    stratejiler = [
        None,
        lambda a, h: (a != "GND", a in V.GUC_AGLARI, h),
        lambda a, h: (a not in V.GUC_AGLARI, h),
        lambda a, h: (a in V.GUC_AGLARI and a != "GND", h),
    ]
    for _ in range(deneme):
        agirlik = {}
        def rast(a, h, _ag=agirlik, _r=rnd.random()):
            if a not in _ag:
                _ag[a] = rnd.random()
            return (a in V.GUC_AGLARI and rnd.random() < 0.0, h * (0.5 + _ag[a]))
        stratejiler.append(rast)
    en, en_b = None, 1e18
    for i, st in enumerate(stratejiler):
        t = yol_uret(nl, parcalar, st)
        b = yol_bedeli(t)
        if b < en_b:
            en, en_b = t, b
            print(f"  sira {i:2d}: bedel {b:.0f}  tel {sum(1 for l in t.values() for x in l if x['tur'] == 'tel')}")
    return en


# ═══════════════════════════════════════════════════════════════════════
#  DENETIM
# ═══════════════════════════════════════════════════════════════════════

class BirlesimBul:
    def __init__(self):
        self.u = {}

    def bul(self, a):
        self.u.setdefault(a, a)
        while self.u[a] != a:
            self.u[a] = self.u[self.u[a]]
            a = self.u[a]
        return a

    def birles(self, a, b):
        ra, rb = self.bul(a), self.bul(b)
        if ra != rb:
            self.u[ra] = rb


class Denetim:
    def __init__(self):
        self.gecti = 0
        self.kaldi = 0

    def kosul(self, ad: str, tamam: bool, ek: str = ""):
        if tamam:
            self.gecti += 1
        else:
            self.kaldi += 1
        print(f"  {'[OK]' if tamam else '[!!]'} {ad}" + (f"   {ek}" if ek else ""))
        return tamam


def kablo_ucu(uc: str, parcalar, nl):
    """'A:T_VGIR' -> ('A', x, y) · 'X:J1.1' -> ('X', 'J1.1')."""
    yer, ad = uc.split(":", 1)
    if yer == "X":
        return ("X", ad)
    p = parcalar[ad]
    (d,) = p.delikler(nl)[f"{ad}.1"]
    return (p.kart, d[0], d[1])


def denetle(nl: Netlist, parcalar: dict[str, Parca], teller: dict,
            yazdir_ayrinti: bool = True) -> tuple[Denetim, dict]:
    D = Denetim()
    model, hv = gerilim_modeli()
    bilgi = {}

    # ── 1 · her netlist parcasi bir yerde ve TEK kez
    print("\n  1 · PARCALAR — netlistteki her parca yerlestirilmis mi")
    yerde = set(parcalar) | set(V.KART_DISI)
    netlist_ref = set(nl.ref_pinleri)
    eksik = sorted(netlist_ref - yerde)
    D.kosul("netlistteki her parca bir kartta ya da kart disinda", not eksik,
            f"{len(netlist_ref)} parca" + (f" · EKSIK {eksik}" if eksik else ""))
    fazla = sorted(r for r in yerde - netlist_ref
                   if not (r in parcalar and parcalar[r].ayak == "TEL"))
    D.kosul("netlistte olmayan parca yok (TEL lehim noktalari haric)", not fazla,
            f"FAZLA {fazla}" if fazla else "")
    cift = sorted(set(parcalar) & set(V.KART_DISI))
    D.kosul("hicbir parca hem kartta hem kart disinda degil", not cift, str(cift) if cift else "")

    # ── 2 · ayak izi pinleri netlistle ayni
    print("\n  2 · AYAK IZLERI — pin kumesi ve fiziksel bacak islevi")
    uyumsuz = []
    for ref, p in parcalar.items():
        if p.ayak == "TEL":
            continue
        ayak_no = {pid.split(".", 1)[1] for pid in p.delikler(nl)}
        if ayak_no != nl.ref_pinleri.get(ref, set()):
            uyumsuz.append(f"{ref}: ayak {sorted(ayak_no)} / netlist "
                           f"{sorted(nl.ref_pinleri.get(ref, set()))}")
    D.kosul("her kart parcasinin ayak izi pinleri = netlist pinleri", not uyumsuz,
            "; ".join(uyumsuz[:4]))
    islevli = [p for p in parcalar.values() if p.ayak in ("TO92", "TO220", "ADS")]
    kotu = []
    for p in islevli:
        beklenen = (V.ADS_MODUL if p.ayak == "ADS" else V.BACAK[p.kod])
        for isl in beklenen:
            if isl not in nl.islev.get(p.ref, {}):
                kotu.append(f"{p.ref}:{isl}")
    D.kosul(f"TO-92/TO-220/ADS bacaklari ISLEVLE eslesiyor ({len(islevli)} parca)",
            not kotu, f"netlistte olmayan islev {kotu}" if kotu else
            "; ".join(f"{p.ref}={'-'.join(V.BACAK[p.kod])}" for p in islevli
                      if p.ayak != "ADS"))

    # ── 3 · geometri
    print("\n  3 · GEOMETRI — kart siniri, vida, cakisma")
    delik_sahibi: dict[tuple, str] = {}
    cakisan, disarida, vidada = [], [], []
    for p in parcalar.values():
        kb = V.KARTLAR[p.kart]
        vida = vida_delikleri(p.kart)
        tum = [d for dl in p.delikler(nl).values() for d in dl] + p.bos_delikler()
        for d in tum:
            if not (0 <= d[0] < kb["sutun"] and 0 <= d[1] < kb["satir"]):
                disarida.append(f"{p.ref}@{d}")
            if d in vida:
                vidada.append(f"{p.ref}@{delik_adi(*d)}")
            k = (p.kart, d)
            if k in delik_sahibi:
                cakisan.append(f"{delik_sahibi[k]}/{p.ref}@{p.kart}:{delik_adi(*d)}")
            delik_sahibi[k] = p.ref
    D.kosul("butun bacaklar kart sinirinda", not disarida, str(disarida[:5]))
    D.kosul("vida kose bosluklarina bacak yok", not vidada, str(vidada[:5]))
    D.kosul("hicbir delige iki bacak girmiyor", not cakisan, str(cakisan[:5]))

    govde_cak, govde_alti, govde_dis = [], [], []
    liste = list(parcalar.values())
    for i, p in enumerate(liste):
        g = p.govde()
        kb = V.KARTLAR[p.kart]
        if g[0] < -0.6 or g[1] < -0.6 or g[2] > kb["sutun"] - 0.4 or g[3] > kb["satir"] - 0.4:
            govde_dis.append(p.ref)
        for q in liste[i + 1:]:
            if q.kart != p.kart:
                continue
            h = q.govde()
            ox = min(g[2], h[2]) - max(g[0], h[0])
            oy = min(g[3], h[3]) - max(g[1], h[1])
            if ox > 0.02 and oy > 0.02:
                govde_cak.append(f"{p.ref}/{q.ref}")
        for q in liste:
            if q is p or q.kart != p.kart:
                continue
            for d in [d for dl in q.delikler(nl).values() for d in dl]:
                if g[0] + 0.15 < d[0] < g[2] - 0.15 and g[1] + 0.15 < d[1] < g[3] - 0.15:
                    # kendi govdesinin altindaki kendi bacagi zaten haric (q is p)
                    govde_alti.append(f"{q.ref} bacagi {p.ref} altinda @{delik_adi(*d)}")
    D.kosul("govdeler kart icinde", not govde_dis, str(govde_dis[:5]))
    D.kosul("govdeler cakismiyor", not govde_cak, str(govde_cak[:6]))
    D.kosul("hicbir bacak baska bir parcanin govdesinin altinda degil", not govde_alti,
            "; ".join(govde_alti[:4]))

    # ── 4 · bakir — izler ve teller
    print("\n  4 · BAKIR — izler, teller, kablolar")
    iz_hata, tel_hata = [], []
    for kart, liste_t in teller.items():
        kb = V.KARTLAR[kart]
        vida = vida_delikleri(kart)
        bos = {d for p in parcalar.values() if p.kart == kart for d in p.bos_delikler()}
        for t in liste_t:
            if t["tur"] == "iz":
                yol = [tuple(h) for h in t["yol"]]
                for a, b in zip(yol, yol[1:]):
                    if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
                        iz_hata.append(f"{kart}: {delik_adi(*a)}->{delik_adi(*b)} komsu degil")
                for h in yol:
                    if not (0 <= h[0] < kb["sutun"] and 0 <= h[1] < kb["satir"]) \
                            or h in vida or h in bos:
                        iz_hata.append(f"{kart}: iz {delik_adi(*h)} yasak delikte")
            else:
                for h in t["uclar"]:
                    h = tuple(h)
                    if h in vida or h in bos:
                        tel_hata.append(f"{kart}: tel ucu {delik_adi(*h)} yasak delikte")
    D.kosul("izler komsu deliklerden geciyor, vida/gerginlik deligine girmiyor",
            not iz_hata, "; ".join(iz_hata[:4]))
    D.kosul("tel uclari gecerli deliklerde", not tel_hata, "; ".join(tel_hata[:4]))
    D.kosul("kart B'de (HV) ic tel yok — butun baglanti bakirda",
            not any(t["tur"] == "tel" for t in teller.get("B", [])))

    # ── 5 · baglanti — netlist ile birebir, her kurulum adiminda
    print("\n  5 · BAGLANTI — bakir netlistle birebir mi (her kurulum adiminda)")

    def pin_dugumleri(adim_sinir):
        out = {}
        for p in parcalar.values():
            if p.adim > adim_sinir:
                continue
            for pid, dl in p.delikler(nl).items():
                out.setdefault(pid, []).extend((p.kart, d[0], d[1]) for d in dl)
        for ref, (grup, adim) in V.KART_DISI.items():
            if adim > adim_sinir:
                continue
            for no in nl.ref_pinleri.get(ref, ()):
                out.setdefault(f"{ref}.{no}", []).append(("X", f"{ref}.{no}"))
        return out

    def graf(adim_sinir, kablolar=True, yalniz_kart=None):
        bb = BirlesimBul()
        for kart, liste_t in teller.items():
            if yalniz_kart and kart != yalniz_kart:
                continue
            for t in liste_t:
                if t["adim"] > adim_sinir:
                    continue
                if t["tur"] == "iz":
                    yol = [tuple(h) for h in t["yol"]]
                    bb.bul((kart, *yol[0]))
                    for a, b in zip(yol, yol[1:]):
                        bb.birles((kart, *a), (kart, *b))
                else:
                    a, b = (tuple(h) for h in t["uclar"])
                    bb.birles((kart, *a), (kart, *b))
        for p in parcalar.values():
            if p.adim <= adim_sinir and p.a.get("ic_bag"):
                for dl in p.delikler(nl).values():
                    for a, b in zip(dl, dl[1:]):
                        bb.birles((p.kart, *a), (p.kart, *b))
        if kablolar:
            for u1, u2, tur, adim, _not in V.KABLOLAR:
                if adim <= adim_sinir:
                    bb.birles(kablo_ucu(u1, parcalar, nl), kablo_ucu(u2, parcalar, nl))
        return bb

    def karsilastir(adim_sinir):
        bb = graf(adim_sinir)
        pd = pin_dugumleri(adim_sinir)
        acik, kisa = [], []
        kok_aglari: dict = {}
        for pid, dugumler in pd.items():
            ag = nl.pin_agi.get(pid)
            if ag is None:
                continue
            for d in dugumler:
                kok_aglari.setdefault(bb.bul(d), set()).add(ag)
        for ag, pinler in nl.ag_pinleri.items():
            koklar = {bb.bul(d) for pid in pinler for d in pd.get(pid, [])}
            if len(koklar) > 1:
                acik.append(ag)
        for kok, aglar in kok_aglari.items():
            if len(aglar) > 1:
                kisa.append(sorted(aglar))
        return acik, kisa, bb, kok_aglari

    son = max([p.adim for p in parcalar.values()] + [a for _, a in V.KART_DISI.values()])
    acik, kisa, bb_son, kok_aglari = karsilastir(son)
    D.kosul("ACIK DEVRE yok — her ag tek parca bakir", not acik,
            f"{len(nl.ag_pinleri)} ag" + (f" · ACIK: {acik[:6]}" if acik else ""))
    D.kosul("KISA DEVRE yok — hicbir bakir parcasi iki agi birlestirmiyor", not kisa,
            f"KISA: {kisa[:3]}" if kisa else "")
    yerlesmemis = [pid for pid in nl.pin_agi
                   if not any(pid in p.delikler(nl) for p in parcalar.values())
                   and pid.split(".")[0] not in V.KART_DISI]
    D.kosul("her netlist pini fiziksel bir dugume oturuyor", not yerlesmemis,
            str(yerlesmemis[:6]))

    adim_hata = []
    for k in range(son + 1):
        a, s, _bb, _ = karsilastir(k)
        if a or s:
            adim_hata.append(f"adim {k}: acik {a[:3]} kisa {s[:2]}")
    D.kosul(f"her kurulum adiminda (0..{son}) yarim kart da tam bagli ve kisasiz",
            not adim_hata, "; ".join(adim_hata[:3]))

    # beyan edilen ag etiketi geometriyle ayni mi (bayat plan). "GND@kelvin"
    # yol ureticinin ic adi: gercek agi GND.
    etiket_hata = []
    for kart, liste_t in teller.items():
        for t in liste_t:
            h = tuple(t["yol"][0] if t["tur"] == "iz" else t["uclar"][0])
            gercek = kok_aglari.get(bb_son.bul((kart, *h)), set())
            beyan = t["ag"].split("@")[0]
            if gercek and beyan not in gercek:
                etiket_hata.append(f"{kart}:{delik_adi(*h)} '{t['ag']}' / {sorted(gercek)}")
    D.kosul("tel planindaki ag etiketleri geometriyle ayni (plan bayat degil)",
            not etiket_hata, "; ".join(etiket_hata[:3]))

    bosta = []
    for kart, liste_t in teller.items():
        for t in liste_t:
            h = tuple(t["yol"][0] if t["tur"] == "iz" else t["uclar"][0])
            if not kok_aglari.get(bb_son.bul((kart, *h))):
                bosta.append(f"{kart}:{delik_adi(*h)}")
    D.kosul("bostaki bakir yok (hicbir ize bagli olmayan iz/tel)", not bosta, str(bosta[:5]))

    # ── 6 · Kelvin + yildiz toprak + yuk akimi
    print("\n  6 · SONT — Kelvin, yildiz toprak, yuk akimi plakete girmiyor")
    bb_kart = graf(son, kablolar=False)

    def ada(kart, pid):
        ref = pid.split(".")[0]
        (d, *_) = parcalar[ref].delikler(nl)[pid]
        kok = bb_kart.bul((kart, *d))
        icerik = set()
        for p in parcalar.values():
            if p.kart != kart:
                continue
            for q, dl in p.delikler(nl).items():
                if any(bb_kart.bul((kart, *x)) == kok for x in dl):
                    icerik.add(q)
        return icerik

    for pin, ped in V.KELVIN:
        ic = ada("A", pin)
        D.kosul(f"Kelvin: {pin} kartta YALNIZ {ped} ile bagli", ic == {pin, ped},
                f"ada = {sorted(ic)}")
    yuk_kartta = [f"{u1}-{u2}" for u1, u2, tur, *_ in V.KABLOLAR
                  if tur == "yuk" and not (u1.startswith("X:") and u2.startswith("X:"))]
    D.kosul("yuk akimi tasiyan hicbir kablo plakete girmiyor", not yuk_kartta,
            str(yuk_kartta))
    gnd_ada = ada("A", V.YILDIZ_ORNEK_PIN)
    guc_yolu = {r for r, (g, _a) in V.KART_DISI.items() if g == "guc"}
    ciktilar = []
    for u1, u2, tur, *_ in V.KABLOLAR:
        for a, b in ((u1, u2), (u2, u1)):
            if a.startswith("A:") and b.startswith("X:") \
                    and b[2:].split(".")[0] in guc_yolu \
                    and f"{a[2:]}.1" in gnd_ada:
                ciktilar.append((a, tur))
    D.kosul("kart toprak adasi guc yoluna TEK noktadan bagli (yildiz)",
            len(ciktilar) == 1 and ciktilar[0][1] == "yildiz", str(ciktilar))

    # ── 7 · kacak yolu
    print("\n  7 · KACAK YOLU — bakirdan bakira (IEC 60664-1 Tablo F.4)")
    bakir: dict[str, dict[tuple, str]] = {}
    for kart, liste_t in teller.items():
        hucre = bakir.setdefault(kart, {})
        for t in liste_t:
            hs = t["yol"] if t["tur"] == "iz" else t["uclar"]
            for h in hs:
                aglar = kok_aglari.get(bb_son.bul((kart, *h)), set())
                if aglar:
                    hucre[tuple(h)] = next(iter(aglar))
    for p in parcalar.values():
        for pid, dl in p.delikler(nl).items():
            for d in dl:
                aglar = kok_aglari.get(bb_son.bul((p.kart, *d)), set())
                if aglar:
                    bakir.setdefault(p.kart, {})[d] = next(iter(aglar))
    ihlal = []
    en_dar = {}
    for kart, hucre in bakir.items():
        ogeler = list(hucre.items())
        vidalar = [("VIDA", c) for c in vida_merkezleri(kart)]
        for i, (h1, a1) in enumerate(ogeler):
            for h2, a2 in ogeler[i + 1:]:
                if a1 == a2:
                    continue
                dv = delta_v(a1, a2, model, hv)
                if dv < V.KACAK_ESIK_V:
                    continue
                gerek = gereken_mm(dv, takviyeli_mi(a1, a2, model))
                kenar = math.dist(h1, h2) * ADIM_MM - V.PAD_ETKIN_MM
                if kenar < gerek:
                    ihlal.append(f"{kart}:{delik_adi(*h1)}({a1})-{delik_adi(*h2)}({a2}) "
                                 f"{kenar:.2f}<{gerek:.2f} mm @{dv:.0f} V")
                pay = kenar - gerek
                if kart not in en_dar or pay < en_dar[kart][0]:
                    en_dar[kart] = (pay, f"{delik_adi(*h1)}-{delik_adi(*h2)} "
                                         f"{kenar:.2f}/{gerek:.2f} mm @{dv:.0f} V")
            if model.get(a1, ("",))[0] == "zincir" or model.get(a1, ("",))[0] == "aralik":
                for _v, c in vidalar:
                    dv = delta_v(a1, "GND", model, hv)
                    if dv < V.KACAK_ESIK_V:
                        continue
                    n = len(V.ZINCIR) - 1
                    tak = model.get(a1, ("",))[0] == "zincir" and model[a1][1] < n
                    gerek = gereken_mm(dv, tak)
                    kenar = (math.dist(h1, c) * ADIM_MM - V.PAD_ETKIN_MM / 2
                             - V.VIDA_YARICAP_MM)
                    if kenar < gerek:
                        ihlal.append(f"{kart}:{delik_adi(*h1)}({a1})-VIDA "
                                     f"{kenar:.2f}<{gerek:.2f} mm @{dv:.0f} V")
    D.kosul("50 V ustu her bakir cifti Tablo F.4 araligini sagliyor", not ihlal,
            "; ".join(ihlal[:4]))
    for kart, (pay, s) in sorted(en_dar.items()):
        print(f"       en dar ({kart}): {s}  pay {pay:+.2f} mm")
    bilgi["en_dar"] = {k: f"{s} (pay {pay:+.2f} mm)" for k, (pay, s) in en_dar.items()}
    # F9'un "5 delik" sayisi merkezden merkeze: bakirdan bakira yetiyor mu
    tak615 = gereken_mm(hv, True)
    bes = 5 * ADIM_MM - V.PAD_ETKIN_MM
    n_gerek = math.ceil((tak615 + V.PAD_ETKIN_MM) / ADIM_MM)
    print(f"       F9 bilgi: 5 adim merkezden merkeze {5 * ADIM_MM:.2f} mm ama bakirdan "
          f"bakira {bes:.2f} mm; {hv:.0f} V takviyeli {tak615:.2f} mm -> {n_gerek} adim")
    bilgi["f9_adim"] = n_gerek

    # ── 8 · ayirma kondansatorleri — bakir yolu uzunlugu
    print("\n  8 · AYIRMA — kondansatorden pine bakir yolu (delik)")
    komsu: dict = {}
    for kart, liste_t in teller.items():
        for t in liste_t:
            if t["tur"] == "iz":
                yol = [tuple(h) for h in t["yol"]]
                for a, b in zip(yol, yol[1:]):
                    komsu.setdefault((kart, *a), []).append(((kart, *b), 1))
                    komsu.setdefault((kart, *b), []).append(((kart, *a), 1))
            else:
                a, b = (tuple(h) for h in t["uclar"])
                L = abs(a[0] - b[0]) + abs(a[1] - b[1])
                komsu.setdefault((kart, *a), []).append(((kart, *b), L))
                komsu.setdefault((kart, *b), []).append(((kart, *a), L))

    def mesafe(a, b):
        pq, en = [(0, a)], {a: 0}
        while pq:
            c, d = heapq.heappop(pq)
            if d == b:
                return c
            if c > en.get(d, 1e9):
                continue
            for n, w in komsu.get(d, []):
                if c + w < en.get(n, 1e9):
                    en[n] = c + w
                    heapq.heappush(pq, (c + w, n))
        return None

    def pin_dugum(pid):
        ref = pid.split(".")[0]
        p = parcalar[ref]
        (d, *_) = p.delikler(nl)[pid]
        return (p.kart, *d)

    for c_pin, ic_pin, sinir, neden in V.YAKINLIK:
        m = mesafe(pin_dugum(c_pin), pin_dugum(ic_pin))
        D.kosul(f"{c_pin} -> {ic_pin} bakir yolu <= {sinir} delik ({neden})",
                m is not None and m <= sinir, f"{m}" if m is not None else "BAGLI DEGIL")

    # belge icin: delik -> ag (bakir + bacaklar, geometriden)
    bilgi["delik_agi"] = {(kart, h): ag for kart, hucre in bakir.items()
                          for h, ag in hucre.items()}

    # ── ozet
    print("\n  OZET")
    for kart, liste_t in teller.items():
        iz = [t for t in liste_t if t["tur"] == "iz"]
        tel = [t for t in liste_t if t["tur"] == "tel"]
        uzun = sum(len(t["yol"]) - 1 for t in iz)
        telu = sum(abs(t["uclar"][0][0] - t["uclar"][1][0]) + abs(t["uclar"][0][1] - t["uclar"][1][1])
                   for t in tel)
        dolu = [d for p in parcalar.values() if p.kart == kart
                for dl in p.delikler(nl).values() for d in dl]
        xs = [d[0] for d in dolu]
        ys = [d[1] for d in dolu]
        kb = V.KARTLAR[kart]
        print(f"    kart {kart} ({kb['plaket']}, {kb['sutun']}x{kb['satir']} delik): "
              f"{sum(1 for p in parcalar.values() if p.kart == kart)} parca · "
              f"{len(iz)} iz ({uzun} adim) · {len(tel)} yalitimli tel ({telu} adim) · "
              f"kullanilan alan {max(xs) - min(xs) + 1}x{max(ys) - min(ys) + 1}")
        bilgi[kart] = {"iz": len(iz), "tel": len(tel)}
    bilgi["gecti"], bilgi["toplam"] = D.gecti, D.gecti + D.kaldi
    return D, bilgi


# ═══════════════════════════════════════════════════════════════════════
#  ASCII (gelistirme)
# ═══════════════════════════════════════════════════════════════════════

def ascii_ciz(nl, parcalar, teller):
    for kart, kb in V.KARTLAR.items():
        W, H = kb["sutun"], kb["satir"]
        izgara = [["  ." for _ in range(W)] for _ in range(H)]
        for p in parcalar.values():
            if p.kart != kart:
                continue
            x0, y0, x1, y1 = p.govde()
            for y in range(H):
                for x in range(W):
                    if x0 < x < x1 and y0 < y < y1 and izgara[y][x] == "  .":
                        izgara[y][x] = "  :"
        for t in teller.get(kart, []):
            hs = t["yol"] if t["tur"] == "iz" else t["uclar"]
            for h in hs:
                if izgara[h[1]][h[0]] in ("  .", "  :"):
                    izgara[h[1]][h[0]] = "  #" if t["tur"] == "iz" else "  @"
        for p in parcalar.values():
            if p.kart != kart:
                continue
            for pid, dl in p.delikler(nl).items():
                for d in dl:
                    if 0 <= d[0] < W and 0 <= d[1] < H:
                        izgara[d[1]][d[0]] = p.ref[-3:].rjust(3)
            for d in p.bos_delikler():
                if 0 <= d[0] < W and 0 <= d[1] < H:
                    izgara[d[1]][d[0]] = "  o"
        for d in vida_delikleri(kart):
            izgara[d[1]][d[0]] = "  X"
        print(f"\n  KART {kart} — {kb['ad']} ({W}x{H})")
        print("     " + "".join(sutun_adi(x).rjust(3) for x in range(W)))
        for y in range(H):
            print(f"  {y + 1:3d}" + "".join(izgara[y]))


# ═══════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ascii", action="store_true")
    ap.add_argument("--yol-uret", action="store_true")
    ap.add_argument("--belge-yok", action="store_true")
    a = ap.parse_args()

    nl = Netlist(NETLIST)
    parcalar = parcalari_yukle()

    if a.yol_uret:
        teller = en_iyi_yol(nl, parcalar)
        # satir basina bir tel: diff okunur, mutasyon kosucusu tek satiri
        # hedefleyebilir
        satirlar = ["{"]
        for i, (kart, liste) in enumerate(teller.items()):
            satirlar.append(f'"{kart}": [')
            satirlar += [json.dumps(t, ensure_ascii=False) + ("," if j < len(liste) - 1 else "")
                         for j, t in enumerate(liste)]
            satirlar.append("]" + ("," if i < len(teller) - 1 else ""))
        satirlar.append("}")
        TELLER.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        print(f"  yazildi: {TELLER.name}")
    teller = json.loads(TELLER.read_text(encoding="utf-8")) if TELLER.exists() else {}

    if a.ascii:
        ascii_ciz(nl, parcalar, teller)

    print("=" * 78)
    print("  DELIKLI PLAKET YERLESIMI — bakir netlistle birebir mi")
    print("=" * 78)
    D, bilgi = denetle(nl, parcalar, teller)
    print()
    print(f"  {D.gecti}/{D.gecti + D.kaldi} dogrulama gecti")
    # Plan geometriyi dogruluyor; PARCA OLCULERI ve BACAK SIRASI tahmin.
    # Bunlar ancak parca elde, plaket masadayken dogrulanir.
    tezgah("B48 Yerlesim plani", [
        ("[!] BJT/TL431/7912 bacak sirasi multimetrenin diyot kademesiyle",
         f"Plan {'-'.join(V.BACAK['2N2222-331'])} (2N2222-331), "
         f"{'-'.join(V.BACAK['BC557'])} (BC557), {'-'.join(V.BACAK['TL431'])} (TL431), "
         f"{'-'.join(V.BACAK['L7912'])} (7912) varsayiyor. Semadaki Q2 sembolu "
         "BC547 (C-B-E); yanlis sira transistoru YARI calistirir, sessiz kusur"),
        ("Plaket ped capi kumpasla",
         f"Kacak yolu hesabi lehimli iletken capini {V.PAD_ETKIN_MM:.2f} mm aliyor. "
         "Olculen buyukse yerlesim3_veri/tasarim3_sabit guncellenip denetim "
         "yeniden kosulacak (HV kartinda pay +1.97 mm)"),
        ("Sigorta klipsi, 68uF ve C18 bacak araliklari",
         "Ayak izleri tahmin: klips cifti 6 adim, 68uF 1 adim / 8 mm govde, "
         "C18 film 6 adim. Parcayi plakete oturt, delikleri say; uymayan "
         "varsa plan yeniden uretilecek (--yol-uret)"),
        ("Her adimin sonunda bakir sureklilik (ohmmetre)",
         "Plan acik/kisa devre olmadigini GEOMETRIDEN kanitliyor; soguk lehim "
         "ve lehim koprusunu kanitlayamaz. Her adimda kilavuzun KAPI olcumunden "
         "once komsu pedler arasi kisa, ag iclerinde sureklilik"),
    ])
    if not a.belge_yok and D.kaldi == 0:
        import yerlesim3_belge
        yerlesim3_belge.yaz(nl, parcalar, teller, bilgi, BELGE)
        print(f"  belge: {BELGE.relative_to(KOK)}")
    return 0 if D.kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
