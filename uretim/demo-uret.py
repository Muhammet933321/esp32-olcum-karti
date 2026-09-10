# -*- coding: utf-8 -*-
"""Arayuzun TEK DOSYALIK demo surumunu uretir.

    python demo-uret.py   ->  ../arayuz-demo.html

Neden: arayuz normalde `arayuz/sunucu.py` uzerinden calisiyor (Web Serial
guvenli baglam istiyor). Ama donanim olmadan arayuzu GORMEK icin sunucuya
gerek yok. Bu betik style.css, sahte-kart.js ve app.js'i tek bir HTML'e
gomup dogrudan acilabilir (ve yayinlanabilir) bir dosya uretiyor.

Vue yerel kopyadan degil cdnjs'ten yukleniyor — yayinlanan sayfada yerel
dosya olmadigi icin. Surum SABITLENMIS.

Kaynak dosyalar hic degistirilmiyor; bu bir TUREV.

NOT: re.sub KULLANILMIYOR. Gomulen JavaScript `\\s+` gibi diziler icerdigi
icin regex degistirme metni onlari kacis dizisi sanip patliyordu. Duz
string.replace() hem daha basit hem de bu tuzagi tamamen yok ediyor.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
ARAYUZ = BURASI.parent / "arsiv" / "asama1" / "arayuz"
CIKTI = BURASI.parent / "arayuz-demo.html"

VUE_CDN = ("https://cdnjs.cloudflare.com/ajax/libs/vue/3.5.13/"
           "vue.global.prod.min.js")

hata = 0


def degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    global hata
    if metin.count(eski) != 1:
        print(f"  [!!] {ad}: {metin.count(eski)} kez bulundu (1 bekleniyordu)")
        hata += 1
        return metin
    return metin.replace(eski, yeni, 1)


def main() -> int:
    html = (ARAYUZ / "index.html").read_text(encoding="utf-8")
    css = (ARAYUZ / "style.css").read_text(encoding="utf-8")
    sahte = (ARAYUZ / "sahte-kart.js").read_text(encoding="utf-8")
    app = (ARAYUZ / "app.js").read_text(encoding="utf-8")

    html = degistir(html,
                    '<link rel="stylesheet" href="style.css">',
                    "<style>\n" + css + "\n</style>",
                    "style.css")
    html = degistir(html,
                    '<script src="vendor/vue.global.prod.js"></script>',
                    f'<script src="{VUE_CDN}"></script>',
                    "Vue")
    html = degistir(html,
                    '<script src="sahte-kart.js"></script>',
                    "<script>\n" + sahte + "\n</script>",
                    "sahte-kart.js")
    html = degistir(html,
                    '<script src="app.js"></script>',
                    "<script>\n" + app + "\n</script>",
                    "app.js")

    # Demo kipini ZORLA — yayinlanan sayfada ?demo yazmaya gerek kalmasin
    html = degistir(
        html,
        "if (location.search.includes('demo')) this.demoVeri();",
        "this.demoVeri();   /* tek dosyalik surumde demo her zaman acik */",
        "demo kipi")

    html = degistir(html, "<title>Ölçüm Kartı</title>",
                    "<title>Ölçüm Kartı Arayüzü</title>", "baslik")

    CIKTI.write_text(html, encoding="utf-8")
    kb = CIKTI.stat().st_size // 1024
    print(f"  {CIKTI.name} yazildi ({kb} KB)")
    print(f"  gomulu: style.css {len(css) // 1024} KB · "
          f"sahte-kart.js {len(sahte) // 1024} KB · "
          f"app.js {len(app) // 1024} KB")

    # Kaba denetimler
    for parca, ad in (("<style>", "gomulu CSS"),
                      ("SahteKart", "sahte kart"),
                      ("createApp", "Vue uygulamasi"),
                      ("this.demoVeri();   /*", "demo kipi zorlanmis"),
                      (VUE_CDN, "Vue cdnjs baglantisi")):
        if parca not in html:
            print(f"  [!!] {ad} bulunamadi")
            globals()["hata"] += 1
    for yerel in ('src="app.js"', 'href="style.css"', 'src="sahte-kart.js"',
                  'vendor/vue'):
        if yerel in html:
            print(f"  [!!] hala yerel baglanti: {yerel}")
            globals()["hata"] += 1

    if not hata:
        print("  [OK] tum parcalar gomulu, yerel baglanti kalmadi")
    return hata


if __name__ == "__main__":
    raise SystemExit(main())
