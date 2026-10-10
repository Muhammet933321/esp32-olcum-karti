# -*- coding: utf-8 -*-
"""BELGELER iki dilli mi?  ->  python test_belge_dil.py

Turkce sayfalar BELGELER/'de, Ingilizce esleri BELGELER/en/'de (belge_dil.py).
Bu test URETILMIS sayfalara bakar (uretecleri kosmaz); once
`kurulum3-uret.py` + `belge-uret.py` kosulmus olmali.

Denetimler:
  1. Her TR sayfanin EN esi var (ayni dosya adi).
  2. EN sayfalarda gorunur metinde Turkceye ozgu harf (çğıöşüİ...) kalmamis.
     Istisnalar asagidaki IZIN listesinde, her biri gerekcesiyle.
  3. Her iki dilde karsilikli dil baglantisi var (TR -> en/<ad>, EN -> ../<ad>).
  4. TR/EN sayfalardaki sayisal tablo hucrelerinin sayilari (sira dahil)
     birebir esit: sayilar tek kaynaktan gelir, ceviri yalnizca metni
     (birim adi "sa" -> "h", aciklama) degistirir.

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KOK = Path(__file__).resolve().parent.parent
BELGELER = KOK / "BELGELER"
EN = BELGELER / "en"

# Baska uretecin (paralel calisan yerlesim/kutu rehberi) sayfalari: EN esi bu
# dalda henuz yoksa ATLANIR (duyurularak), varsa butun denetimlere girer.
BASKA_URETEC = {"7-yerlesim.html": "uretim/yerlesim3*.py",
                "8-kutu.html": "uretim/kutu*.py"}

TR_HARF = re.compile(r"[çğıöşüÇĞİÖŞÜ]")

# EN sayfada Turkce harf tasiyabilecek kelimeler — HER BIRI GEREKCELI.
# Kelime, Turkce harf iceren butun bir kelime olarak (noktalama atilmis) eslesir.
IZIN = {
    # Dil baglantisi: Ingilizce sayfadan Turkce ese giden etiketin adi Turkce
    # yazilir (lang="tr" ile isaretli; dil seciciler kendi dillerinde yazilir).
    "Türkçe": "dil baglantisi etiketi",
}

# Gorunur metin sayilmayan elemanlar.
GIZLI = {"style", "script", "head", "title"}
# `code`/`pre`/`kbd`: dosya adi, komut, kaynak koddan alinti — cevrilmez.
KOD = {"code", "pre", "kbd", "samp"}


class Metin(HTMLParser):
    """Gorunur metni (kod ve lang="tr" disinda) ve tablo hucrelerini toplar."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.yigin: list[tuple[str, bool, bool, bool]] = []  # (etiket, gizli, kod, tr)
        self.parcalar: list[str] = []
        self.hucreler: list[tuple[bool, list[str]]] = []      # (class s mi, metin)
        self.hucre: tuple[bool, list[str]] | None = None
        self.dil_bag: list[tuple[str, str]] = []              # (href, metin)
        self._a_dil: str | None = None

    def _durum(self):
        return self.yigin[-1][1:] if self.yigin else (False, False, False)

    def handle_starttag(self, etiket, nit):
        n = dict(nit)
        gizli, kod, tr = self._durum()
        gizli = gizli or etiket in GIZLI
        kod = kod or etiket in KOD
        tr = tr or n.get("lang") == "tr"
        if etiket in ("td", "th"):
            self.hucre = ("s" in (n.get("class") or "").split(), [])
        if etiket == "a" and "dil" in (n.get("class") or "").split():
            self._a_dil = n.get("href") or ""
        for ad in ("title", "alt", "aria-label", "placeholder"):
            if n.get(ad) and not (gizli or kod or tr):
                self.parcalar.append(n[ad])
        if etiket in ("br", "img", "meta", "link", "input", "hr", "wbr"):
            return
        self.yigin.append((etiket, gizli, kod, tr))

    def handle_startendtag(self, etiket, nit):
        self.handle_starttag(etiket, nit)
        if self.yigin and self.yigin[-1][0] == etiket and etiket not in (
                "br", "img", "meta", "link", "input", "hr", "wbr"):
            self.yigin.pop()

    def handle_endtag(self, etiket):
        if etiket in ("td", "th") and self.hucre is not None:
            self.hucreler.append((self.hucre[0], " ".join("".join(self.hucre[1]).split())))
            self.hucre = None
        for i in range(len(self.yigin) - 1, -1, -1):
            if self.yigin[i][0] == etiket:
                del self.yigin[i:]
                break

    def handle_data(self, veri):
        gizli, kod, tr = self._durum()
        if self.hucre is not None and not gizli:
            self.hucre[1].append(veri)
        if self._a_dil is not None and veri.strip():
            self.dil_bag.append((self._a_dil, veri.strip()))
            self._a_dil = None
        if not (gizli or kod or tr):
            self.parcalar.append(veri)


def coz(yol: Path) -> Metin:
    m = Metin()
    m.feed(yol.read_text(encoding="utf-8"))
    m.close()
    return m


# Sayisal hucre: rakam iceren ve harf olarak yalnizca birim/sembol tasiyan
# hucre ("665", "±32 V", "0.13 mV", "4.7–7.5 Ω", "1 000 Sa/s"). Kelime iceren
# hucreler (cevrilen metin) sayilmaz.
BIRIM = r"(?:[munpkMG]?(?:V|A|W|Ω|Hz|Sa/s|SPS|Ah|Wh|s|ms|µs|us|ns|F|B|KB|MB|bit|dB|°C|C|%|x|×|h|min|dk|sa))"
SAYISAL = re.compile(
    r"^[\s~≈±<>≤≥+\-−–·/]*\d[\d\s.,:/×x+\-−–±~≈%°]*(?:\s*" + BIRIM + r"(?:\s*/\s*" + BIRIM
    + r")?[\s\d.,:/×+\-−–±%]*)*$")


def sayilar(t: str) -> str:
    """Hucredeki sayilar, sirasiyla ("3.1 sa" ve "3.1 h" -> "3.1"). Birim ve
    aciklama kelimeleri cevrilebilir ("10 A kademesi" / "10 A range"); sayilar
    ve isaretleri (±, −) cevrilemez."""
    return " ".join(re.findall(r"[±−\-]?\d+(?:[ .,]\d+)*", t))


def sayisal_hucreler(m: Metin) -> list[str]:
    """Sayisal hucreler (class="s" ya da SAYISAL), her biri yalnizca sayilariyla."""
    return [sayilar(t) for s, t in m.hucreler
            if t and (s or SAYISAL.match(t)) and re.search(r"\d", t)]


def turkce_kelimeler(m: Metin) -> list[str]:
    kelimeler = []
    for parca in m.parcalar:
        for k in re.findall(r"[^\s<>()\[\]{},.;:!?\"'“”‘’«»/—–=+*|]+", parca):
            if TR_HARF.search(k) and k not in IZIN:
                kelimeler.append(k)
    return kelimeler


def main() -> int:
    gecen = kalan = 0

    def ok(ad, kosul, ek=""):
        nonlocal gecen, kalan
        if kosul:
            gecen += 1
            print(f"  [OK] {ad}" + (f" — {ek}" if ek else ""))
        else:
            kalan += 1
            print(f"  [!!] {ad}" + (f" — {ek}" if ek else ""))

    tr_sayfalar = sorted(p.name for p in BELGELER.glob("*.html"))
    ok("BELGELER/'de Turkce sayfa var", bool(tr_sayfalar), f"{len(tr_sayfalar)} sayfa")
    for ad in tr_sayfalar:
        en = EN / ad
        if not en.exists() and ad in BASKA_URETEC:
            print(f"  [--] {ad}: EN esi bu dalda yok, ATLANDI "
                  f"(ureteci {BASKA_URETEC[ad]}, paralel is)")
            continue
        ok(f"{ad}: EN esi var", en.exists(), str(en.relative_to(KOK)))
        if not en.exists():
            continue
        mt, me = coz(BELGELER / ad), coz(en)
        ok(f"{ad}: TR -> EN dil baglantisi",
           any(h == f"en/{ad}" for h, _t in mt.dil_bag), str(mt.dil_bag[:1]))
        ok(f"{ad}: EN -> TR dil baglantisi",
           any(h == f"../{ad}" for h, _t in me.dil_bag), str(me.dil_bag[:1]))
        tk = turkce_kelimeler(me)
        ok(f"{ad}: EN gorunur metinde Turkce harf yok", not tk,
           f"{len(tk)} kelime: {', '.join(sorted(set(tk))[:12])}" if tk else "temiz")
        st, se = sayisal_hucreler(mt), sayisal_hucreler(me)
        fark = next((i for i, (a, b) in enumerate(zip(st, se)) if a != b), None)
        if fark is None and len(st) != len(se):
            fark = min(len(st), len(se))
        ok(f"{ad}: sayisal tablo hucreleri TR = EN", fark is None,
           f"{len(st)} hucre" if fark is None else
           f"#{fark}: TR {st[fark:fark + 1]} / EN {se[fark:fark + 1]} "
           f"(TR {len(st)}, EN {len(se)} hucre)")
    # Tersine: TR esi olmayan yetim EN sayfasi da olmasin.
    yetim = sorted(p.name for p in EN.glob("*.html") if not (BELGELER / p.name).exists()) \
        if EN.exists() else []
    ok("BELGELER/en/'de TR esi olmayan sayfa yok", not yetim, ", ".join(yetim) or "temiz")
    print(f"{gecen}/{gecen + kalan} kural gecti (BELGELER iki dil)")
    return 0 if kalan == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
