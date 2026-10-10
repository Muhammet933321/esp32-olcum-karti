# -*- coding: utf-8 -*-
"""BELGELER/2-malzemeler.html govdesi.

Listeyi SEMADAN (netlist3.net) ve ENVANTERDEN (stok-takip/envanter.csv)
uretiyor — elle yazilmis parca listesi YOK. bom_dogrula.py'nin ayni
eslesme tablolarini kullaniyor, yani iki liste ayrisamaz.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bom_dogrula as B                                 # noqa: E402
from belge_dil import M, sec                            # noqa: E402

BURASI = Path(__file__).parent
KOK = BURASI.parent

GRUP = {
    "Direnç": "Dirençler", "Kondansatör": "Kondansatörler",
    "Diyot": "Diyotlar", "MOSFET": "Yarı iletkenler",
    "Transistör": "Yarı iletkenler", "Entegre": "Yarı iletkenler",
    "Regülatör": "Yarı iletkenler",
}


# Ingilizce sayfa (BELGELER/en/2-malzemeler.html) icin cevirmeler.
# Anahtar: bom_dogrula.ESLEME / BILINEN_DIS'teki notun BIREBIR Turkce hali.
# Tabloda olmayan bir not Turkce kalir — test_belge_dil bunu yakalar.
NOT_EN = {
    "anahtar; dogrusal kip YOK, sogutucusuz 6.55 A'e kadar":
        "switch; NO linear mode, up to 6.55 A without a heatsink",
    "kapi surucusu alt kol (NPN)": "gate driver, low side (NPN)",
    "kapi surucusu ust kol (PNP)": "gate driver, high side (PNP)",
    "C023 1uF 400V — B16, C18; C021/C022 de var":
        "C023 1uF 400V — B16, C18; C021/C022 also in stock",
    "C052 63V — B16, C19": "C052 63V — B16, C19",
    "her biri 2 adet 1nF paralel": "each is 2 x 1nF in parallel",
    "REG009 yeni (L7912CV); REG004 x2 SOKUM, test edilmemis — "
    "kartta yenisini kullan":
        "REG009 new (L7912CV); REG004 x2 salvaged, untested — "
        "use the new one on the board",
    "C035 — 7912'nin giris ve cikis kondansatoru":
        "C035 — input and output capacitor of the 7912",
    "FUS010 — B15/F8: +-12 V yuku 30 mA, 1.7x pay; "
    "yuvadaki gecici 400 mA (FUS001) ile DEGISTIRILECEK":
        "FUS010 — B15/F8: +-12 V load 30 mA, 1.7x margin; "
        "REPLACES the temporary 400 mA (FUS001) in the holder",
    "BRD003 — N16R8, 2026-09-11": "BRD003 — N16R8, 2026-09-11",
    "MOD003 — 3 adet, ADDR->GND = 0x48": "MOD003 — 3 pcs, ADDR->GND = 0x48",
    "MOD003 — ayni stok, ADDR->VDD = 0x49":
        "MOD003 — same stock, ADDR->VDD = 0x49",
    "IC — B16/B17 tamponlari": "IC — B16/B17 buffers",
    "D012 — kelepceler; DO-34": "D012 — clamps; DO-34",
    "R055 1/4W metal film — HV zinciri; 2W'lik R038 SAYILMAZ":
        "R055 1/4W metal film — HV chain; the 2W R038 does NOT count",
    "R061 1/4W metal film — HV bolucusunun alt bacagi":
        "R061 1/4W metal film — lower leg of the HV divider",
    "RS tek konum; 5mR/0.1R/1R de stokta — kademe secimi":
        "RS is a single footprint; 5mR/0.1R/1R also in stock — range choice",
    "CON058 — B48: 24 V girisi XT30 (kodlu); tezgah icin. Kutuda (B58) "
    "kullanilmiyor: teller ic klemense, 24 V kutunun kendi pilinden":
        "CON058 — B48: 24 V input is XT30 (keyed); for the bench. Not used "
        "in the enclosure (B58): wires go to an internal terminal, 24 V "
        "comes from the enclosure's own battery",
    "ayni stok": "same stock",
    "B21. J3'ten AYRI olmali: J3 dogrudan sonte gider, "
    "J7 MOSFET'ten gecer. Karistirilirsa kesme CALISMAZ":
        "B21. Must be SEPARATE from J3: J3 goes straight to the shunt, "
        "J7 goes through the MOSFET. Mix them up and the cutoff will NOT work",
    "sase born jak": "panel-mount banana jack",
    "615 V icin AYRI ve ISARETLI olmali — kirmizi/siyah ayir":
        "must be SEPARATE and MARKED for 615 V — keep red/black apart",
    "envanterde yetersiz": "not enough in stock",
}

# Semadaki (netlist3.net) Turkce deger adlarinin gorunen Ingilizcesi.
DEGER_EN = {
    "24V girisi": "24 V input",
    "Yuk donusu": "Load return",
    "Pil testi yuk donusu": "Battery test load return",
    "V girisi +-32V": "V input +-32V",
    "Skop girisi": "Scope input",
    "ADS1115 #1 akim": "ADS1115 #1 current",
    "ADS1115 #2 gerilim": "ADS1115 #2 voltage",
}


def _parcalar():
    """netlist3.net'ten ref -> deger, sonra deger -> [ref] toplami."""
    net = (BURASI / "netlist3.net").read_text(encoding="utf-8",
                                              errors="replace")
    d = defaultdict(list)
    for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\)\s*\(value "([^"]*)"\)',
                         net):
        d[m.group(2)].append(m.group(1))
    return d


def malzemeler(d, dil="tr"):
    kayit = B.envanteri_oku()
    parca = _parcalar()
    stokta, alinacak, yolda = [], [], []
    for deger, refler in sorted(parca.items()):
        n = len(refler)
        eslesme = B.ESLEME.get(deger)
        if eslesme:
            env_ad, kat, notu, *paket = eslesme
            adet, _kayitlar, _sayilmamis = B.stok_bul(kayit, env_ad, kat,
                                                       paket[0] if paket else "")
            grup = GRUP.get(kat, kat)
            if adet is not None and adet >= n:
                stokta.append((deger, n, refler, adet, grup, notu or ""))
            else:
                alinacak.append((deger, n, refler, grup,
                                 notu or "envanterde yetersiz"))
        else:
            durum, notu = B.BILINEN_DIS.get(deger, ("?", ""))
            (yolda if durum == "yolda" else alinacak).append(
                (deger, n, refler, "Bağlantı / modül", notu))

    def tablo(kalemler, stok=False):
        s = sec(M("<table><tr><th>Parça</th><th class='s'>Gereken</th>"
                  + ("<th class='s'>Elimizde</th>" if stok else "")
                  + "<th>Nerede</th><th>Not</th></tr>",
                  "<table><tr><th>Part</th><th class='s'>Needed</th>"
                  + ("<th class='s'>In stock</th>" if stok else "")
                  + "<th>Where</th><th>Note</th></tr>"), dil)
        for k in kalemler:
            if dil == "en":
                k = (DEGER_EN.get(k[0], k[0]),) + tuple(k[1:-1]) + \
                    (NOT_EN.get(k[-1], k[-1]),)
            if stok:
                deger, n, refler, adet, grup, notu = k
                s += (f"<tr><td><b>{deger}</b></td><td class='s'>{n}</td>"
                      f"<td class='s'>{adet}</td>"
                      f"<td class='kucuk'>{', '.join(refler)}</td>"
                      f"<td class='kucuk'>{notu}</td></tr>")
            else:
                deger, n, refler, grup, notu = k
                s += (f"<tr><td><b>{deger}</b></td><td class='s'>{n}</td>"
                      f"<td class='kucuk'>{', '.join(refler)}</td>"
                      f"<td class='kucuk'>{notu}</td></tr>")
        return s + "</table>"

    if dil == "en":
        return f"""
<p>This list is <b>generated from the schematic</b> and checked against
<b>your stock records</b>. When a part is added to the schematic, this page
updates itself — it is not a hand-written list.</p>

<div class="kpi">
  <div><span>In stock</span><b>{len(stokta)}</b></div>
  <div><span>Ordered</span><b>{len(yolda)}</b></div>
  <div><span>To buy</span><b>{len(alinacak)}</b></div>
</div>

<h2>🛒 To buy</h2>
<p>What is still missing to build the board.</p>
{tablo(alinacak)}
<div class="uy"><b>The battery test also needs a power resistor</b>
(external, not on the schematic): <b>4.7–7.5 Ω / 10 W</b> for an 18650. If
a 12 V lead-acid battery will be tested too, add 10–15 Ω / <b>50 W</b>.
<br><span class="kucuk">There is an unsorted pile of resistors — check it
first; if one turns up, it drops off this list.</span></div>

<h2>📦 Ordered, on the way</h2>
{tablo(yolda)}

<h2>✅ In stock</h2>
<p>Enough of these according to your stock records.</p>
{tablo(stokta, stok=True)}

<div class="uy"><b>Resistor quantities are rough counts.</b> Even if the
records say "enough", count them when the number matters for a project —
and there is another unsorted pile outside the records.</div>

<h2>Tools and consumables</h2>
<table>
<tr><th>Needed</th><th>Note</th></tr>
<tr><td>Perfboard</td><td>The board is built on this permanently</td></tr>
<tr><td>Soldering iron + solder wire</td><td></td></tr>
<tr><td>Isopropyl alcohol</td><td>Cleaning after soldering — reduces leakage
    current on the high-voltage side</td></tr>
<tr><td>Spare ESP32-S3</td><td>Optional, but testing stops if the main board
    dies</td></tr>
<tr><td>Multimeter</td><td>For calibration — an ANENG AN8000 is available</td></tr>
</table>
"""
    return f"""
<p>Bu liste <b>şemadan</b> üretiliyor ve <b>stok kaydınızla</b>
karşılaştırılıyor. Yani şemaya bir parça eklendiğinde burası kendiliğinden
güncelleniyor — elle yazılmış bir liste değil.</p>

<div class="kpi">
  <div><span>Elinizde var</span><b>{len(stokta)}</b></div>
  <div><span>Sipariş edildi</span><b>{len(yolda)}</b></div>
  <div><span>Alınacak</span><b>{len(alinacak)}</b></div>
</div>

<h2>🛒 Alınacaklar</h2>
<p>Kartı kurabilmek için eksik olanlar.</p>
{tablo(alinacak)}
<div class="uy"><b>Pil testi için ayrıca bir taş direnç gerekiyor</b>
(şemada değil, harici): 18650 için <b>4.7–7.5 Ω / 10 W</b>. 12 V akü de
test edilecekse ayrıca 10–15 Ω / <b>50 W</b>.
<br><span class="kucuk">Dirençlerde ayrılmamış dağınık bir yığın var —
oraya bakın, çıkarsa bu listeden düşer.</span></div>

<h2>📦 Sipariş edilmiş, yolda</h2>
{tablo(yolda)}

<h2>✅ Elinizde olanlar</h2>
<p>Stok kaydınıza göre yeterli miktarda var.</p>
{tablo(stokta, stok=True)}

<div class="uy"><b>Direnç adetleri göz kararı sayım.</b> Kayıtta
"yeterli" görünse bile bir projede sayı kritikse saydırın — ayrıca
kayıt dışı dağınık bir yığın daha var.</div>

<h2>Alet ve sarf</h2>
<table>
<tr><th>Gereken</th><th>Not</th></tr>
<tr><td>Delikli plaket</td><td>Kart buna kalıcı kurulacak</td></tr>
<tr><td>Havya + lehim teli</td><td></td></tr>
<tr><td>İzopropil alkol</td><td>Lehim sonrası temizlik — yüksek gerilim
    kolunda kaçak akımı azaltır</td></tr>
<tr><td>Yedek ESP32-S3</td><td>Zorunlu değil ama ana kart ölürse test
    durur</td></tr>
<tr><td>Multimetre</td><td>Kalibrasyon için — ANENG AN8000 var</td></tr>
</table>
"""
