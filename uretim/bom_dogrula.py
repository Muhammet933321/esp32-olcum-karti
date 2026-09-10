# -*- coding: utf-8 -*-
"""B9 — Asama 3 malzeme listesi ENVANTERLE tutuyor mu?

    python bom_dogrula.py

NEDEN: tasarim ne kadar dogrulanmis olursa olsun, elde olmayan bir parca
istiyorsa kart kurulamaz. Siparisler acikken bunu bilmek gerekiyor.

Malzeme listesi SEMADAN uretiliyor (netlist3.net), elle yazilmiyor —
sema degisince liste pesinden gidiyor.

CLAUDE.md kurali: envanter TEK GERCEK KAYNAK, tahminle cevap verilmez.
Ayni kural sunu da soyluyor: direnc adetleri GOZ KARARI sayim ve ayrica
kayit disi dagimik bir yigin var. Bu yuzden "yetersiz" ciktisi
"kesinlikle yok" degil, "SAYDIR" demektir.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path
from tezgah import tezgah                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
SEMA = KOK / "sema3" / "olcum-karti-a3.kicad_sch"
ENVANTER = KOK.parents[1] / "stok-takip" / "envanter.csv"
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

# Sema degeri -> (envanterdeki ad, aranacak kategori, not)
# Baglanti ve modul gibi semada "deger" olarak gecen seyler ayri ele alinir.
ESLEME = {
    # B15/F1-F2: ADS giris koruma direncleri (R34..R39).
    # R013 "1K" dokme kalemi TUKENMIS (0) ama R029/R030/R031 paketleri
    # duruyor — 1/4W, 1/2W ve 1W'tan 10'ar adet.
    "1K":     ("1K", "Direnç", None),
    "6.8K":   ("6.8K", "Direnç", None),
    "10K":    ("10K", "Direnç", None),
    "2.7K":   ("2.7K", "Direnç", None),
    "22K":    ("22K", "Direnç", None),
    "47K":    ("47K", "Direnç", None),
    "100K":   ("100K", "Direnç", None),
    "220K":   ("220K", "Direnç", None),
    "220R":   ("220R", "Direnç", None),
    # ── B21 (pil kapasite testi) — HEPSI STOKTA
    "4.7K":   ("4.7K", "Direnç", None),
    "IRFZ44N": ("IRFZ44N", "MOSFET",
                "anahtar; dogrusal kip YOK, sogutucusuz 6.55 A'e kadar"),
    "2N2222": ("2N2222", "Transistör", "kapi surucusu alt kol (NPN)"),
    "BC557":  ("BC557", "Transistör", "kapi surucusu ust kol (PNP)"),
    "100R":   ("100R", "Direnç", None),
    "100nF":  ("100nF", "Kondansatör", None),
    "1nF":    ("1nF", "Kondansatör", None),
    # B16 — ADS akim girisi ortusme suzgeci (C18+C19+C20 = 1.32 uF)
    "1uF":    ("1µF", "Kondansatör",
               "C023 1uF 400V — B16, C18; C021/C022 de var"),
    "220nF":  ("220nF", "Kondansatör", "C052 63V — B16, C19"),
    "2nF (2x1nF)": ("1nF", "Kondansatör", "her biri 2 adet 1nF paralel"),
    "TL431LP": ("TL431", "Entegre", None),
    # B11 — +-12 V rayi (7912 orta nokta regulatoru)
    "L7912":   ("7912", "Regülatör",
                "REG004 x2 — DEVIR 5.12.21 'besleyecek sey yok' demisti; "
                "24 V kaynak ortaya cikinca kullanilabilir oldu"),
    "68uF 50V": ("68µF 50V", "Kondansatör",
                 "C035 — 7912'nin giris ve cikis kondansatoru"),
    "LM358":  ("LM358", "Entegre", None),
}

# Envanterde OLMAYAN ama durumu BILINEN parcalar.
# `yolda`  : siparis edildi, DEVIR 3.2'de belgelendi
# `alinacak`: satin alma listesinde (DEVIR 5.12.9)
BILINEN_DIS = {
    "TL072":  ("yolda", "direnc.net siparisi, 4 adet — DEVIR 3.2"),
    "BAT85":  ("alinacak", "DO-34 eksenel Schottky — 1N5711 de olur"),
    "820K":   ("alinacak", "metal film %1, 1/4W — tedarikcinin metal film hatti 820K'da bitiyor; 6 adet + 2 yedek"),
    "8.2K":   ("alinacak", "metal film %1, 1/4W — HV bolucusunun alt bacagi; stokta yok"),
    "ADS1115 #1 akim": ("yolda", "Robotistan siparisi, 3 adet"),
    "ADS1115 #2 gerilim": ("yolda", "Robotistan siparisi, 3 adet"),
    "ESP32-S3": ("yolda", "direnc.net siparisi, 1 adet"),
    "V girisi +-32V": ("yolda", "muz jak / bariyer klemens siparisi"),
    "HV +-615V": ("yolda", "muz jak — 615 V icin AYRI ve isaretli olmali"),
    "Yuk donusu": ("yolda", "bariyer klemens"),
    "Pil testi yuk donusu": ("yolda",
        "bariyer klemens — B21. J3'ten AYRI olmali: J3 dogrudan sonte "
        "gider, J7 MOSFET'ten gecer. Karistirilirsa kesme CALISMAZ"),
    "Skop girisi": ("yolda", "muz jak"),
    "10R/1R/0R1/15mR": ("yolda", "sont seti: 0.1R tas, 15mR Type-C — DEVIR 3.2"),
    "24V girisi": ("yolda", "bariyer klemens — B11, 24 V kaynak girisi"),
    "50mA": ("alinacak", "cam sigorta + yuva; +-12 V yuku 30 mA, 1.7x pay — B15/F8"),
}

gecti = kaldi = uyari = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


def envanteri_oku():
    # `envanter.csv` bu deponun DISINDA (kullanicinin kisisel stok kaydi,
    # `Elekronic/stok-takip/`). Depoyu klonlayan birinde YOKTUR; eskiden
    # burada ciplak bir FileNotFoundError patliyordu. Artik ne oldugunu
    # soyluyor. ⚠ Dosya VARSA davranis birebir ayni — iddia sayisi da.
    if not ENVANTER.exists():
        print("=" * 78)
        print("  B9 ATLANDI — envanter kaydi bulunamadi")
        print("=" * 78)
        print(f"  Beklenen yol: {ENVANTER}")
        print("  Bu adim, semadan uretilen malzeme listesini KULLANICININ")
        print("  kisisel stok kaydiyla karsilastiriyor. O kayit bu deponun")
        print("  parcasi degil, o yuzden depoyu klonlayan birinde bu adim")
        print("  KOSAMAZ. Diger 15 adim envanterden bagimsiz calisir.")
        print("  Malzeme listesinin kendisi: BELGELER/2-malzemeler.html")
        raise SystemExit(0)
    kayit = []
    with open(ENVANTER, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            kayit.append(r)
    return kayit


def stok_bul(kayit, ad, kategori):
    """Ada gore toplam adet ve kayit dokumu. Potansiyometreler HARIC —
    `POT` onekli kayitlar direnc degil."""
    bulunan = [r for r in kayit
               if not r["id"].startswith("POT")
               and r["kategori"].strip() == kategori
               and (r["ad"].strip().upper() == ad.upper()
                    or r["ad"].strip().upper().startswith(ad.upper() + " "))]
    toplam = sum(int(r["adet"]) for r in bulunan
                 if r["adet"].strip().isdigit())
    sayilmamis = [r["id"] for r in bulunan if not r["adet"].strip()]
    return toplam, bulunan, sayilmamis


def main() -> int:
    global uyari
    print("=" * 78)
    print("  B9  MALZEME LISTESI — envanterle tutuyor mu?")
    print("=" * 78)

    u = subprocess.run(
        [KICAD_CLI, "sch", "export", "netlist", "--output", "netlist3.net",
         str(SEMA)],
        cwd=BURASI, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300)
    if u.returncode != 0:
        print(u.stdout, u.stderr)
        return 1

    t = (BURASI / "netlist3.net").read_text(encoding="utf-8")
    comps = re.findall(r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\)', t)
    gerekli: dict[str, list[str]] = {}
    for ref, val in comps:
        if ref.startswith("#"):
            continue
        gerekli.setdefault(val, []).append(ref)

    print(f"\n--- Semadan {sum(len(v) for v in gerekli.values())} bilesen, "
          f"{len(gerekli)} farkli deger --------------------\n")

    kayit = envanteri_oku()

    print(f"  {'deger':<16} {'ger':>4} {'stok':>6}  durum")
    print("  " + "-" * 74)

    eksikler = []
    for val in sorted(gerekli, key=lambda v: (-len(gerekli[v]), v)):
        adet = len(gerekli[val])
        # 2nF = 2 x 1nF paralel
        carpan = 2 if val.startswith("2nF") else 1
        ihtiyac = adet * carpan

        if val in ESLEME:
            env_ad, kat, notu = ESLEME[val]
            toplam, bulunan, sayilmamis = stok_bul(kayit, env_ad, kat)
            yeterli = toplam >= ihtiyac
            durum = "yeterli" if yeterli else "YETERSIZ"
            ek = f" ({notu})" if notu else ""
            print(f"  {val:<16} {ihtiyac:4d} {toplam:6d}  {durum}{ek}")
            if not yeterli:
                eksikler.append((val, ihtiyac, toplam, bulunan))
            # sifir adetli kayitlari ayrica goster
            sifirlar = [r for r in bulunan
                        if r["adet"].strip() == "0"]
            if sifirlar:
                alternatif = [r for r in bulunan
                              if r["adet"].strip().isdigit()
                              and int(r["adet"]) > 0]
                print(f"       ! {', '.join(r['id'] for r in sifirlar)} "
                      f"TUKENMIS; alternatif: "
                      f"{', '.join(r['id'] + ' (' + (r['paket'] or '1/4W') + ') x' + r['adet'] for r in alternatif) or 'YOK'}")
                uyari += 1
        elif val in BILINEN_DIS:
            durum, notu = BILINEN_DIS[val]
            print(f"  {val:<16} {ihtiyac:4d} {'—':>6}  {durum} — {notu}")
        else:
            print(f"  {val:<16} {ihtiyac:4d} {'?':>6}  BILINMIYOR")
            eksikler.append((val, ihtiyac, 0, []))

    print()
    print("--- Kurallar --------------------------------------------------")
    ok("Semadaki her deger ya envanterde ya BILINEN_DIS listesinde",
       all(v in ESLEME or v in BILINEN_DIS for v in gerekli),
       "eslenmemis deger yok" if all(v in ESLEME or v in BILINEN_DIS
                                     for v in gerekli)
       else str([v for v in gerekli if v not in ESLEME and v not in BILINEN_DIS]))

    stokta_olmasi_gerekenler = [v for v in gerekli if v in ESLEME]
    yetersizler = [e[0] for e in eksikler if e[0] in ESLEME]
    ok("Envanterde olmasi gereken her parca YETERLI",
       not yetersizler,
       "hepsi yeterli" if not yetersizler else f"yetersiz: {yetersizler}")

    alinacaklar = [v for v in gerekli
                   if BILINEN_DIS.get(v, ("", ""))[0] == "alinacak"]
    # B20: `True` yerine BELGENIN kendisi aranıyor — her "alinacak"
    # kaleminin BILINEN_DIS'te bos olmayan bir gerekcesi var mi?
    _belgesiz = [v for v in alinacaklar
                 if not (BILINEN_DIS.get(v, ("", ""))[1] or "").strip()]
    ok("Satin alinacaklar BELGELENMIS (surpriz yok)", not _belgesiz,
       (", ".join(f"{v} x{len(gerekli[v])}" for v in alinacaklar) or "yok")
       + (f"  — BELGESIZ: {_belgesiz}" if _belgesiz else ""))

    print()
    print("  ⚠ CLAUDE.md: direnc adetleri GOZ KARARI sayim ve kayit disi")
    print("    dagimik bir yigin daha var. 'Yetersiz' = KESIN YOK degil,")
    print("    'saydir' demektir. Bir projede sayi kritikse kayda guvenme.")
    print()
    print(f"  {gecti}/{gecti + kaldi} kural gecti"
          + (f", {uyari} uyari" if uyari else ""))
    tezgah("B9 Malzeme listesi", [
        ("[!] Direnc adetleri SAYIM degil goz karari",
         "envanter.csv'nin direnc adetleri yaklasik (CLAUDE.md). "
         "Listede yeter gorunen bir deger tezgahta bitebilir. "
         "Olcum: montajdan ONCE kritik degerleri say"),
        ("Kayitta gorunmeyen parca GERCEKTEN yok mu",
         "Bobin/cekirdek ve modul alanlari KISMEN girildi. "
         "'kayitta yok' = 'elde yok' DEGIL. Olcum: kutuya bak"),
        ("Parcalarin gercek degerleri etiketiyle ayni mi",
         "Ozellikle HV bolucusundeki 4.9 M ohm zinciri. Olcum: "
         "lehimlemeden once her direnci ohmmetreyle gec"),
    ])
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
