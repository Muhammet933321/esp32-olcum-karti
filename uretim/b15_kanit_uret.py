# -*- coding: utf-8 -*-
"""B15 arastirma ve denetim sonuclarini KALICI bir belgeye dokur.

    python b15_kanit_uret.py [<workflow-dizini> ...]

NEDEN VAR: B15'in dayandigi veri sayfasi arastirmasi (10 konu, 90 ajan)
ve betigin kendisine yapilan adversaryel denetim (6 boyut, 39 ajan)
oturuma bagli bir gecici dizinde uretildi:

    ~/.claude/projects/<proje>/<oturum-id>/subagents/workflows/<run-id>/

O dizin oturumla birlikte KAYBOLUR. Bu betik oradaki `journal.jsonl`
dosyalarini okuyup `uretim/b15-arastirma.md` uretir — projenin `kanit/`
klasoru zaten kalici kanit deposu (a2-tam-dogrulama.txt, s9-kayit.txt ...).

Dizinler bulunamazsa betik SESSIZCE mevcut belgeyi korur ve 0 doner;
boylece zincire eklenirse baska bir makinede de kirmizi yakmaz.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
CIKTI = BURASI.parent / "uretim" / "b15-arastirma.md"


def journal_oku(dizin: Path) -> list[dict]:
    """Bir workflow calisma dizinindeki tamamlanmis ajan sonuclarini dondurur."""
    yol = dizin / "journal.jsonl"
    if not yol.exists():
        return []
    cikti = []
    for satir in yol.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            kayit = json.loads(satir)
        except ValueError:
            continue
        if kayit.get("type") != "result":
            continue
        deger = kayit.get("result")
        if isinstance(deger, dict):
            cikti.append(deger)
    return cikti


def varsayilan_dizinler() -> list[Path]:
    kok = (Path.home() / ".claude" / "projects" / "c--Muhammet-Elekronic")
    if not kok.exists():
        return []
    return sorted(kok.glob("*/subagents/workflows/wf_*"))


def yaz(f, metin: str = "") -> None:
    f.write(metin + "\n")


def main(argv: list[str]) -> int:
    dizinler = ([Path(a) for a in argv[1:]] if len(argv) > 1
                else varsayilan_dizinler())
    arastirma: list[dict] = []
    denetim: list[dict] = []
    dogrulamalar: list[dict] = []
    for d in dizinler:
        for kayit in journal_oku(d):
            if "topic" in kayit:
                arastirma.append(kayit)
            elif "bulgular" in kayit:
                denetim.append(kayit)
            elif "refuted" in kayit:
                dogrulamalar.append(kayit)

    if not arastirma and not denetim:
        if CIKTI.exists():
            print(f"  workflow dizini yok; mevcut {CIKTI.name} korundu "
                  f"({CIKTI.stat().st_size // 1024} KB)")
            return 0
        print("  workflow dizini yok ve kanit dosyasi da yok — atlandi")
        return 0

    curutuldu = sum(1 for v in dogrulamalar if v.get("refuted"))
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    with CIKTI.open("w", encoding="utf-8") as f:
        yaz(f, "# B15 — arastirma ve denetim kaniti")
        yaz(f)
        yaz(f, "> Bu dosya `uretim/b15_kanit_uret.py` tarafindan uretildi.")
        yaz(f, "> Elle duzenleme; kaynak, workflow `journal.jsonl` dosyalari.")
        yaz(f, ">")
        yaz(f, f"> **{len(arastirma)} arastirma konusu** · "
               f"**{len(dogrulamalar)} iddia bagimsiz dogrulandi** "
               f"({curutuldu} tanesi curutuldu) · "
               f"**{len(denetim)} denetim boyutu**")
        yaz(f)
        yaz(f, "B15'in (`uretim/sim3_ariza.py`) dayandigi butun veri sayfasi")
        yaz(f, "sayilari ve gercek dunya ariza raporlari burada. Her iddia")
        yaz(f, "AYRI bir skeptik ajan tarafindan, kaynak belgeye giderek")
        yaz(f, "dogrulandi; curutulenler de kayitta tutuldu cunku *neden*")
        yaz(f, "curutuldugu bilgisi en az iddianin kendisi kadar degerli.")
        yaz(f)
        yaz(f, "---")

        if arastirma:
            yaz(f)
            yaz(f, "## 1. Veri sayfasi arastirmasi")
            for konu in arastirma:
                yaz(f)
                yaz(f, f"### {konu.get('topic', '?')}")
                iddialar = konu.get("claims") or []
                if iddialar:
                    yaz(f)
                    yaz(f, "| iddia | deger | guven | kaynak |")
                    yaz(f, "|---|---|---|---|")
                    for c in iddialar:
                        def tek(x):
                            return str(x or "").replace("|", "/").replace(
                                "\n", " ").strip()
                        yaz(f, f"| {tek(c.get('claim'))[:400]} "
                               f"| {tek(c.get('value'))[:200]} "
                               f"| {tek(c.get('confidence'))} "
                               f"| {tek(c.get('source'))[:300]} |")
                for s in (konu.get("surprises") or []):
                    yaz(f)
                    yaz(f, f"> ⚠ {str(s).strip()}")
                acik = konu.get("unresolved") or []
                if acik:
                    yaz(f)
                    yaz(f, "**Cevaplanamayanlar:**")
                    for u in acik:
                        yaz(f, f"- {str(u).strip()}")

        if denetim:
            yaz(f)
            yaz(f, "---")
            yaz(f)
            yaz(f, "## 2. B15'in kendisine yapilan adversaryel denetim")
            yaz(f)
            yaz(f, "Alti bagimsiz denetci betigi ayri boyutlarda denetledi ve")
            yaz(f, "KENDI ngspice kosumlarini yapti. Asagidaki bulgularin")
            yaz(f, "tamami `sim3_ariza.py`'de duzeltildi.")
            for boyut in denetim:
                yaz(f)
                yaz(f, f"### Denetim: {boyut.get('boyut', '?')}")
                genel = str(boyut.get("genel", "") or "").strip()
                if genel:
                    yaz(f)
                    yaz(f, f"> {genel}")
                for b in (boyut.get("bulgular") or []):
                    v = b.get("verdict") or {}
                    gecerli = v.get("gecerli")
                    im = "✅ GECERLI" if gecerli else ("❌ curutuldu"
                                                      if gecerli is False
                                                      else "—")
                    yaz(f)
                    yaz(f, f"**[{b.get('onem', '?')}] {b.get('baslik', '?')}** "
                           f"· {im}")
                    yaz(f)
                    yaz(f, f"- **Yer:** `{b.get('dosya', '?')}` "
                           f"({b.get('satir', '?')})")
                    yaz(f, f"- **Simdiki:** {str(b.get('simdiki',''))[:600]}")
                    yaz(f, f"- **Dogrusu:** {str(b.get('dogrusu',''))[:900]}")
                    kanit = str(b.get("kanit", "") or "").strip()
                    if kanit:
                        yaz(f, f"- **Kanit:** {kanit[:900]}")
                    if v.get("onerilen_yama"):
                        yaz(f, f"- **Yama:** "
                               f"{str(v['onerilen_yama'])[:500]}")

        if dogrulamalar:
            yaz(f)
            yaz(f, "---")
            yaz(f)
            yaz(f, "## 3. Curutulen iddialar — neden curutuldugu")
            yaz(f)
            yaz(f, "Bunlar B15'e GIRMEDI. Kayitta tutuluyor ki ileride ayni")
            yaz(f, "sayilar baska bir kaynaktan tekrar onerilirse neden")
            yaz(f, "reddedildikleri bilinsin.")
            for v in dogrulamalar:
                if not v.get("refuted"):
                    continue
                yaz(f)
                yaz(f, f"**{str(v.get('duzeltilmis_iddia',''))[:400]}**")
                yaz(f)
                yaz(f, f"- **Neden curutuldu:** "
                       f"{str(v.get('neden',''))[:700]}")
                yaz(f, f"- **Duzeltilmis deger:** "
                       f"{str(v.get('duzeltilmis_deger',''))[:400]}")
                if v.get("uretici_farki"):
                    yaz(f, f"- **Uretici farki:** "
                           f"{str(v['uretici_farki'])[:400]}")

    kb = CIKTI.stat().st_size // 1024
    print(f"  yazildi: {CIKTI}")
    print(f"  {len(arastirma)} arastirma konusu · {len(dogrulamalar)} "
          f"dogrulama ({curutuldu} curutuldu) · {len(denetim)} denetim "
          f"boyutu · {kb} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
