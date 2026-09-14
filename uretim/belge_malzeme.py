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

BURASI = Path(__file__).parent
KOK = BURASI.parent

GRUP = {
    "Direnç": "Dirençler", "Kondansatör": "Kondansatörler",
    "Diyot": "Diyotlar", "MOSFET": "Yarı iletkenler",
    "Transistör": "Yarı iletkenler", "Entegre": "Yarı iletkenler",
    "Regülatör": "Yarı iletkenler",
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


def malzemeler(d):
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
        s = ("<table><tr><th>Parça</th><th class='s'>Gereken</th>"
             + ("<th class='s'>Elimizde</th>" if stok else "")
             + "<th>Nerede</th><th>Not</th></tr>")
        for k in kalemler:
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
