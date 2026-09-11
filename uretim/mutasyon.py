# -*- coding: utf-8 -*-
"""MUTASYON KOSUCUSU — "yesil test bir sey kanitlamaz"i olculebilir kilar.

    python mutasyon.py                 butun mutasyonlar
    python mutasyon.py --adim B22b     yalnizca o adimin mutasyonlari
    python mutasyon.py --liste         ne kosacagini yazar, kosmaz

Bu projenin altin kurali: bir iddia, onu YALANLAYAN bir degisiklikle
kirmiziya donmuyorsa BOSTUR. Simdiye kadar her mutasyon ELLE yapildi ve
sonucu DEVIR'e ELLE yazildi — yani tekrarlanabilir DEGILDI ve bir sure
sonra hangi mutasyonun hala tuttugu bilinmiyordu.

── IKI TASARIM KARARI ───────────────────────────────────────────────

🔴 YERINDE MUTASYON YOK. Proje bir git deposu DEGIL. "Boz, kostur, geri
al" deseninde bir Ctrl-C kaynagi bozuk birakir ve GERI DONUS YOLU YOKTUR.
Her mutasyon bir KOPYA uzerinde kosuyor; asil agac hic dokunulmuyor.

🔴 KOPYA `%TEMP%`'E DEGIL KARDES DIZINE. Uc betik agactan cikip
`Elekronic/` duzeyine bakiyor:

    test_firmware3.py   .araclar/arduino-cli.exe   (KOK.parents[1])
    bom_dogrula.py      stok-takip/envanter.csv
    sim3_ortusme.py     stok-takip/envanter.csv

`projeler/_mutasyon-<pid>/` kullanilirsa `KOK.parents[1]` yine
`Elekronic`'e cozulur ve ucu de calisir. `%TEMP%`'te hicbiri calismaz.

⚠ `_fs.json` ve `_fs.bin` KOPYALANIYOR — yoksa `sim3_web.py`'nin kosullu
  dali degisir ve iddia sayisi oynar, mutasyon sonucu yaniltir.

⚠ `--adim` HEDEFLEMESI SART: tam zincir ~6 dk; 20 mutasyonluk bir tur
  hedefsiz iki saat surer.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sayim                                            # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent

# Kopyalanmayacaklar: yeniden uretilebilir ya da agir.
#
# 🔴 `arsiv/` ONCE DISLANMISTI ve taban kosusu kopyada KIRMIZI dondu:
#    `kurulum3-uret.py:326` CSS'ini `arsiv/asama2/kurulum2.html`'den
#    okuyor — yani GUNCEL kurulum kilavuzu bir ARSIV dosyasina bagimli.
#    Derleme ciktilari temizlendikten sonra `arsiv/` zaten 6 MB / 52
#    dosya; dislamaya degmiyor. Ders: "eski asamalar" diye isaretlenmis
#    bir dizin, guncel uretecin bagimliligi olabilir.
ATLA = {"BELGELER", "__pycache__", ".git", "build"}
ATLA_DOSYA = {"DEVIR.md"}


# ── Mutasyon tanimlari ────────────────────────────────────────────────
# (adim, betik, dosya, eski, yeni, ne_kanitliyor)
#
# `betik` mutasyondan SONRA kosturulan sey. Beklenen sonuc: KIRMIZI
# (sifirdan farkli cikis) ya da IDDIA SAYISI degisimi.
# Tam zinciri kosturan mutasyonlar (~6 dk): yalnizca --adim ile.
AGIR = {"B3", "B23"}

MUTASYONLAR = [
    # ── B22b · kart web katmani
    ("B20", "sim3_bant.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "sunucu.enableDelay(false);", "/* sunucu.enableDelay(false); */",
     "WebServer'in kendi delay(1)'i periyodu tik sinirina kilitliyor "
     "(665 -> 500 SPS). B22.1'in en pahali bulgusu"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "sunucu.collectHeaders(", "sunucu.collectHeadersX(",
     "collectHeaders cagrilmazsa CSRF/Host savunmasi SESSIZCE oluyor: "
     "basliklar hic okunmuyor, denetim hep geciyor"),
    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/ag.h",
     '#define AG_MDNS "olcum"', '#define AG_MDNS ""',
     "mDNS adi bosalirsa http://olcum.local cozulmez"),

    ("B22b", "sim3_web.py", "kod/olcum-karti-a3/olcum-karti-a3.ino",
     "korumasiz", "parola yok",
     "web parolasi KALDIRILDI mesaji, komut ucunun O AN korumasiz "
     "kaldigini soylemeli — sessiz bir 'kaldirildi' yetmez"),

    # ── B22a · PC koprusu
    ("B22a", "test_kopru.py", "kopru/kopru.py",
     'SERBEST_KOMUTLAR = {"p0"}', "SERBEST_KOMUTLAR = set()",
     "p0 (pil desarjini DURDUR) her zaman parolasiz gecmeli — "
     "emniyet ozelligi, kolaylik degil"),
    ("B22a", "test_kopru.py", "kopru/arsiv.py",
     "def ham_satirlar", "def ham_satirlar_",
     "role BAYT-SEFFAF olmali; arsivin ham okuma yolu kaybolursa "
     "girdi/cikti karsilastirmasi yapilamaz"),

    # ── B20 · ornekleme hizi
    ("B20", "sim3_bant.py", "uretim/tasarim3_sabit.py",
     "ADS_SPS = 860", "ADS_SPS = 250",
     "ornekleme hizi butun zamanlama butcesinin tabani"),

    # ── B4/B5 · platform bagimsizligi (B25'te bulunan kapsam bosluğu:
    #    mutasyon tablosunda olcum3.h'ye ait TEK kayit yoktu)
    ("B4", "test_olcum3.py", "kod/olcum-karti-a3/olcum3.h",
     "return (float)pJ / 1.0e12f;", "return (float)((double)pJ / 1.0e12);",
     "olcum3.h'de `double` YASAK: AVR'de 32 bit, Xtensa'da 64 bit. "
     "Geri konursa emulator ile kart ayni aritmetigi kosturmaz ve "
     "adimin 'kodun ta kendisi' iddiasi YANLIS olur"),

    # ── B17 · es zamanlilik
    ("B17", "sim3_senkron.py", "kod/olcum-karti-a3/tipler3.h",
     "float    faz_kal_us[2];", "float    faz_kal[2];",
     "faz kalibrasyonu ORNEK degil MIKROSANIYE cinsinden olmali "
     "(B22.1'in K2 duzeltmesi)"),

    # ── B21 · pil testi
    ("B21", "sim3_pil.py", "kod/olcum-karti-a3/pil_test.h",
     "#define PIL_AZAMI_V", "#define PIL_AZAMI_V_",
     "pil gerilim tavani yoksa sinir disi pil kabul edilir"),

    # ── B3 · sema YENIDEN URETILEBILIR mi (B25'te bulundu)
    ("B3s", "netlist3_dogrula.py", "uretim/sema_uret_ortak.py",
     'return str(uuid.uuid5(_AD_ALANI, f"olcum-karti/{_SAYAC}"))',
     "return str(uuid.uuid4())",
     "sema UUID'leri belirlenimli olmali; uuid4 geri gelirse .kicad_sch "
     "ve netlist HER kosuda degisir, 858 satirlik anlamsiz diff verir "
     "ve gercek bir tasarim degisikligini bogar"),

    # ── B3 · sema (B23.3'te bulunan delik)
    ("B3", "dogrula3.py", "uretim/sema3-uret.py",
     'print(f"yazildi: {hedef}")', "raise SystemExit(1)",
     "sema uretimi cokerse ERC ve netlist BAYAT dosyalari okur; "
     "dogrula3.py bunu B23.3'e kadar goremiyordu"),

    # ── B23.1 · tezgah toplayicisinin kendisi
    ("B23", "dogrula3.py", "uretim/netlist3_dogrula.py",
     'tezgah("B3 Sema"', 'if False: tezgah("B3 Sema"',
     "bir adim tezgah kalemi basmayi birakirsa toplayici KIRMIZI "
     "donmeli — adim kendi basina yesil kalsa bile"),
]


def kopyala(hedef: Path) -> None:
    def gormezden(dizin, adlar):
        return [a for a in adlar
                if a in ATLA or a in ATLA_DOSYA
                or a.endswith((".pyc", ".elf", ".rpt"))]
    shutil.copytree(KOK, hedef, ignore=gormezden)


def kosut(kopya: Path, betik: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, betik], cwd=kopya / "uretim",
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    return r.returncode, r.stdout + r.stderr


def uygula(kopya: Path, dosya: str, eski: str, yeni: str) -> bool:
    p = kopya / dosya
    if not p.exists():
        return False
    s = p.read_text(encoding="utf-8", errors="replace")
    if eski not in s:
        return False
    p.write_text(s.replace(eski, yeni), encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adim", help="yalnizca bu adimin mutasyonlari")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()

    if a.adim:
        secili = [m for m in MUTASYONLAR if m[0].lower() == a.adim.lower()]
    else:
        secili = [m for m in MUTASYONLAR if m[0] not in AGIR]
    if not a.adim and any(m[0] in AGIR for m in MUTASYONLAR):
        print(f"  (atlandi: {', '.join(sorted(AGIR))} — tam zincir "
              f"kosturuyor, --adim ile calistirin)")
    if not secili:
        adlar = sorted({m[0] for m in MUTASYONLAR})
        print(f"  '{a.adim}' icin mutasyon yok. Var olanlar: "
              f"{', '.join(adlar)}")
        return 1

    print("=" * 78)
    print(f"  MUTASYON KOSUCUSU — {len(secili)} mutasyon")
    print("=" * 78)
    if a.liste:
        for adim, betik, dosya, eski, _y, neden in secili:
            print(f"  {adim:5} {betik:22} {dosya}")
            print(f"        {eski}  ->  bozuluyor")
            print(f"        {neden}")
        return 0

    kopya = KOK.parent / f"_mutasyon-{os.getpid()}"
    kacan, uygulanamayan = [], []
    try:
        print(f"  kopya: {kopya}")
        t0 = time.time()
        kopyala(kopya)
        print(f"  kopyalandi ({time.time() - t0:.1f} s)")

        # Once TEMIZ taban: mutasyonsuz kosu gercekten yesil mi?
        taban = {}
        for betik in sorted({m[1] for m in secili}):
            rc, cikti = kosut(kopya, betik)
            taban[betik] = (rc, sayim.sayimlar(cikti))
            print(f"  taban {betik:24} rc={rc} {taban[betik][1]}")
            if rc != 0:
                print(f"  KIRMIZI: {betik} mutasyonsuz da KALIYOR — "
                      f"once onu duzelt. Kopyadaki cikti:")
                # Yalnizca ozet satiri basmak yetmiyordu: taban kirmizi
                # olunca NEDENI gorunmuyordu ve tanilamak icin kopyayi
                # elle kurmak gerekti.
                ilginc = [x for x in cikti.splitlines()
                          if ("KALDI" in x and "[OK]" not in x)
                          or "KIRMIZI" in x or "Traceback" in x
                          or x.strip().startswith("[!!]")]
                for x in ilginc[-25:]:
                    print("      " + x.rstrip()[:110])
                if not ilginc:
                    for x in cikti.rstrip().splitlines()[-15:]:
                        print("      " + x.rstrip()[:110])
                return 1

        for i, (adim, betik, dosya, eski, yeni, neden) in enumerate(secili, 1):
            shutil.rmtree(kopya, ignore_errors=True)
            kopyala(kopya)
            print()
            print(f"  [{i}/{len(secili)}] {adim} · {dosya}")
            print(f"        {eski}  ->  {yeni}")
            if not uygula(kopya, dosya, eski, yeni):
                print(f"        ATLANDI: desen bulunamadi (kod degisti mi?)")
                uygulanamayan.append((adim, dosya, eski))
                continue
            rc, cikti = kosut(kopya, betik)
            simdi = sayim.sayimlar(cikti)
            yakalandi = rc != 0 or simdi != taban[betik][1]
            print(f"        rc={rc} sayim={simdi} "
                  f"-> {'YAKALANDI' if yakalandi else 'KACTI'}")
            if not yakalandi:
                print(f"        !! {neden}")
                kacan.append((adim, dosya, eski, neden))
    finally:
        shutil.rmtree(kopya, ignore_errors=True)

    print()
    print("=" * 78)
    if uygulanamayan:
        print(f"  {len(uygulanamayan)} mutasyon UYGULANAMADI (desen yok):")
        for adim, dosya, eski in uygulanamayan:
            print(f"    * {adim} {dosya}: {eski}")
    if kacan:
        print(f"  {len(kacan)} MUTASYON KACTI — o iddialar bos:")
        for adim, dosya, eski, neden in kacan:
            print(f"    * {adim} {dosya}: {eski}")
            print(f"      {neden}")
        return 1
    if uygulanamayan:
        return 1
    print(f"  {len(secili)} mutasyonun hepsi YAKALANDI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
