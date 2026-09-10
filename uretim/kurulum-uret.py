# -*- coding: utf-8 -*-
"""Kurulum sayfasini uretir (breadboard adimlari).

    python kurulum-uret.py   ->  ../kurulum.html

Sablon asagida; SVG'ler `../gorsel/` altindan gomulur. Sayfa her kosuda
sifirdan uretilir — elle yama yapilmaz.
"""
from __future__ import annotations

from pathlib import Path

KOK = Path(__file__).parent.parent
GORSEL = KOK / "gorsel"
HEDEF = KOK / "kurulum.html"


def svg(ad: str) -> str:
    s = (GORSEL / ad).read_text(encoding="utf-8")
    return s.replace("<svg", '<svg class="bb"', 1).strip()


STIL = """<style>
:root{--kagit:#f4f6f9;--yuzey:#fff;--murekkep:#131820;--soluk:#5b6675;
--cok-soluk:#8c95a3;--cizgi:#dce1ea;--cizgi-2:#c3cbd8;--olcum:#2853c6;
--gecti:#15734a;--uyari:#b45a09;--uyari-zem:#fdf3e7;
--golge:0 1px 2px rgba(19,24,32,.05),0 8px 24px rgba(19,24,32,.05);color-scheme:light}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){
--kagit:#0d1117;--yuzey:#151b23;--murekkep:#e3e8ef;--soluk:#8b95a5;
--cok-soluk:#6b7686;--cizgi:#242c37;--cizgi-2:#333d4a;--olcum:#7aa2ff;
--gecti:#4ec98d;--uyari:#f2a05a;--uyari-zem:#2a1d10;
--golge:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);color-scheme:dark}}
:root[data-theme="dark"]{--kagit:#0d1117;--yuzey:#151b23;--murekkep:#e3e8ef;
--soluk:#8b95a5;--cok-soluk:#6b7686;--cizgi:#242c37;--cizgi-2:#333d4a;
--olcum:#7aa2ff;--gecti:#4ec98d;--uyari:#f2a05a;--uyari-zem:#2a1d10;
--golge:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);color-scheme:dark}
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--kagit);color:var(--murekkep);
font-family:"IBM Plex Serif",Georgia,serif;font-size:16.5px;line-height:1.65;
-webkit-font-smoothing:antialiased}
.s{max-width:1000px;margin:0 auto;padding:38px 22px 90px}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:600;
letter-spacing:.11em;text-transform:uppercase;color:var(--olcum);margin:0 0 8px}
h1{font-size:clamp(26px,4.4vw,36px);line-height:1.1;font-weight:600;margin:0 0 10px;
letter-spacing:-.02em;text-wrap:balance}
.alt{color:var(--soluk);margin:0 0 26px;max-width:60ch}
h2{font-size:20px;font-weight:600;margin:40px 0 12px;letter-spacing:-.012em}
.levha{background:#fcfcfa;border:1px solid var(--cizgi-2);border-radius:4px;
padding:14px;overflow-x:auto;box-shadow:var(--golge);color:#2b2b2b}
.bb{display:block;width:100%;min-width:680px;height:auto}
table{border-collapse:collapse;width:100%;font-family:"IBM Plex Mono",monospace;
font-size:13.5px;min-width:400px}
.tw{overflow-x:auto;margin-top:14px}
th{text-align:left;font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;
color:var(--cok-soluk);font-weight:600;padding:0 14px 8px 0;
border-bottom:1px solid var(--cizgi-2)}
td{padding:8px 14px 8px 0;border-bottom:1px solid var(--cizgi);
font-variant-numeric:tabular-nums;vertical-align:top}
td.ad{font-weight:500;white-space:nowrap}
tr:last-child td{border-bottom:none}
ol{padding-left:20px;max-width:62ch}
li{margin-bottom:7px}
code{font-family:"IBM Plex Mono",monospace;font-size:.87em;
background:var(--cizgi);padding:1px 6px;border-radius:3px}
.kutu{border-left:3px solid var(--uyari);background:var(--uyari-zem);
padding:15px 19px;margin:22px 0;border-radius:0 4px 4px 0}
.kutu p{margin:0;font-size:15.5px}
.olc{background:var(--yuzey);border:1px solid var(--cizgi);border-radius:4px;
padding:20px 22px;margin-top:16px;box-shadow:var(--golge)}
.buyuk{font-family:"IBM Plex Mono",monospace;font-size:36px;font-weight:500;
color:var(--gecti);letter-spacing:-.02em;margin:6px 0 2px}
.tesh td:first-child{font-weight:600;white-space:nowrap}
.pinout{font-family:"IBM Plex Mono",monospace;font-size:15px;
background:var(--yuzey);border:1px solid var(--cizgi);border-radius:4px;
padding:16px 20px;margin-top:14px;text-align:center;line-height:2}
.pinout b{font-size:19px;color:var(--olcum)}
.ayrac{border:none;border-top:2px solid var(--cizgi-2);margin:60px 0 0}
.bitti{color:var(--gecti);font-weight:600}
</style>"""

ADIM2 = """
<p class="eyebrow">Adım 2 / 6 <span class="bitti">· tamamlandı</span></p>
<h1>TL431 gerilim referansı</h1>
<p class="alt">Bu bloğun tek işi Arduino'nun ADC'sine oynamayan bir referans
vermek. Doğru kurulduğunun kanıtı tek bir sayı — ölçülen: <strong>2.470 V</strong>.</p>

<div class="levha">
{SVG2}
</div>

<h2>Parçalar</h2>
<div class="tw"><table>
<thead><tr><th>Parça</th><th>Envanter</th><th>Nereye</th></tr></thead>
<tbody>
<tr><td class="ad">1 kΩ</td><td>R029</td><td>C2 → C6</td></tr>
<tr><td class="ad">TL431</td><td>IC002</td><td>A6 · A7 · A8</td></tr>
<tr><td class="ad">220 Ω</td><td>R006</td><td>D6 → D12</td></tr>
<tr><td class="ad">100 nF</td><td>C008</td><td>A12 → − ray</td></tr>
</tbody></table></div>

<h2>TL431'in bacakları — dert etme</h2>
<div class="pinout">
<span style="font-size:12.5px;color:var(--soluk)">iki dış bacak aynı düğüme gider</span><br>
<b>dış</b> &nbsp;·&nbsp; <b style="color:var(--uyari)">ANOT</b> &nbsp;·&nbsp; <b>dış</b>
</div>
<div class="kutu"><p><strong>TL431'in iki farklı pinoutu vardır ve birbirinin
tersidir:</strong> TI'da 1=Katot·2=Anot·3=REF, ON Semi'de 1=REF·2=Anot·3=Katot.
Ama ikisinde de <strong>orta bacak ANOT</strong>, ve bu devrede REF zaten katoda
köprüleniyor. <strong>Hangisinin hangisi olduğunun önemi yok.</strong></p></div>

<h2>Ölçüm</h2>
<div class="olc">
<p style="margin:0;color:var(--soluk);font-size:14px">Multimetre — AREF ile GND arası</p>
<div class="buyuk">2.470 V</div>
<p style="margin:0;color:var(--soluk);font-size:14px">kabul aralığı 2.46 – 2.50 V ✓</p>
</div>
<div class="tw" style="margin-top:16px"><table class="tesh">
<thead><tr><th>Okuduğun</th><th>Ne demek</th></tr></thead>
<tbody>
<tr><td style="color:var(--gecti)">2.46 – 2.50 V</td><td>Doğru — hem TL431 hem firmware çalışıyor</td></tr>
<tr><td style="color:var(--uyari)">tam 2.495 V</td><td>Firmware yüklenmemiş; AREF yük görmüyor</td></tr>
<tr><td style="color:var(--uyari)">~5 V</td><td>Orta bacak GND'ye gitmiyor, ya da yeşil köprü eksik</td></tr>
<tr><td style="color:var(--uyari)">~0.6 V</td><td>Çip ters — 180° çevir, orta bacak yine A7'de</td></tr>
<tr><td style="color:var(--uyari)">0 V</td><td>Besleme yok — rayları kontrol et</td></tr>
</tbody></table></div>
<div class="kutu"><p><strong>25 mV'lik düşüm hata değil, kanıt.</strong>
AREF pini ADC etkinken ~100 µA çekiyor; bu akım 220 Ω üzerinden geçince
TL431'in gerilimini aşağı çekiyor. Tam 2.495 okusaydın çip harici referans
kipinde değil demekti.</p></div>
"""

ADIM4 = """
<hr class="ayrac">
<p class="eyebrow" style="margin-top:36px">Adım 4 / 6 · alt bank sağ</p>
<h1>Şönt ve LM358 akım katı</h1>
<p class="alt">Şöntün üzerindeki minik gerilimi 7.9 kat büyütüp A1'e veriyor.
LM358 sekiz bacaklı — kanalın üstünden geçecek şekilde oturuyor.</p>

<div class="levha">
{SVG4}
</div>

<h2>Parçalar</h2>
<div class="tw"><table>
<thead><tr><th>Parça</th><th>Envanter</th><th>Nereye</th></tr></thead>
<tbody>
<tr><td class="ad">LM358</td><td>IC003</td><td>sütun 18–21, kanalı atlayarak</td></tr>
<tr><td class="ad">47 kΩ</td><td>R040</td><td>H15 → H19</td></tr>
<tr><td class="ad">6.8 kΩ</td><td>R018</td><td>I19 → alt − ray</td></tr>
<tr><td class="ad">10 Ω</td><td>R001</td><td>I26 → alt − ray  <em>(şönt)</em></td></tr>
<tr><td class="ad">100 nF</td><td>C008</td><td>üst + ray → üst − ray</td></tr>
</tbody></table></div>

<div class="kutu"><p><strong>LM358'in çentiği sola bakacak.</strong> Pin 1 sol
alt köşede. Kanalın üstüne oturur — alt sıra (pin 1–4) alt bankta, üst sıra
(pin 5–8) üst bankta.</p></div>

<h2>Sıra</h2>
<ol>
<li><strong>LM358</strong>'i sütun 18–21'e otur, çentik solda</li>
<li>Kırmızı: <strong>D18 → üst + ray</strong> (pin 8, besleme)</li>
<li>Mavi: <strong>G21 → alt − ray</strong> (pin 4, toprak)</li>
<li><strong>100 nF</strong>'ı üst + ray ile üst − ray arasına</li>
<li>Yeşil köprü: <strong>G18 → G15</strong> (çıkışı sola uzat)</li>
<li><strong>47 kΩ</strong> → H15 ile H19 arasına</li>
<li><strong>6.8 kΩ</strong> → I19 ile alt − ray arasına</li>
<li><strong>10 Ω</strong> (şönt) → I26 ile alt − ray arasına</li>
<li>Yeşil köprü: <strong>G26 → G20</strong> (şönt üstü → pin 3)</li>
<li>Turuncu: <strong>J15 → Uno A1</strong> <em>(A1'deki geçici GND jumperını sök)</em></li>
<li>Kullanılmayan kat: mavi <strong>C21 → üst − ray</strong>, yeşil <strong>C20 → C19</strong></li>
</ol>

<h2>Kalibrasyon</h2>
<ol>
<li><strong>Yük bağlama.</strong> Seri porttan <code>s</code> gönder —
LM358'in ofseti ölçülüp çıkarılır</li>
<li>Bilinen bir yük bağla: <strong>+ ray → 220 Ω → mor kablo (F26)</strong></li>
<li>Multimetreyi seri bağlayıp gerçek akımı oku (~22 mA bekleniyor)</li>
<li><code>ka0.022</code> gönder</li>
</ol>
"""

ADIM3 = """
<hr class="ayrac">
<p class="eyebrow" style="margin-top:36px">Adım 3 / 6 · alt bank <span class="bitti">· tamamlandı</span></p>
<h1>Gerilim bölücü</h1>
<p class="alt">1:11 bölücü, iki koruma diyotu ve örtüşme süzgeci.
Girişe kazara 400 V gelse bile düğüm 5.7 V'ta kelepçeleniyor — Arduino sağ kalır.</p>

<div class="levha">
{SVG3}
</div>

<h2>Parçalar</h2>
<div class="tw"><table>
<thead><tr><th>Parça</th><th>Envanter</th><th>Nereye</th></tr></thead>
<tbody>
<tr><td class="ad">100 kΩ</td><td>R025</td><td>G2 → G7</td></tr>
<tr><td class="ad">10 kΩ</td><td>R032</td><td>I7 → alt − ray</td></tr>
<tr><td class="ad">1 nF</td><td>C049</td><td>J7 → alt − ray</td></tr>
<tr><td class="ad">1N4148</td><td>D003</td><td>D1: G11 → alt + ray<br>D2: J11 → alt − ray</td></tr>
</tbody></table></div>

<div class="kutu"><p><strong>Diyotların yönü kritik.</strong> Siyah bant = katot.
<strong>D1</strong>: bant <em>alt + ray</em> tarafında. <strong>D2</strong>: bant
<em>düğüm</em> tarafında (J11). Ters takılırsa devre ölçmez — simülasyonda
yakalanan üçüncü hata tam olarak buydu.</p></div>

<h2>Sıra</h2>
<ol>
<li>Kırmızı uzun kablo: <strong>üst + ray → alt + ray</strong> (sütun 18)</li>
<li>Mavi uzun kablo: <strong>üst − ray → alt − ray</strong> (sütun 19)</li>
<li><strong>100 kΩ</strong> → G2 ile G7 arasına</li>
<li>Yeşil köprü: <strong>H7 → H11</strong></li>
<li><strong>10 kΩ</strong> → I7 ile alt − ray arasına</li>
<li><strong>1 nF</strong> → J7 ile alt − ray arasına</li>
<li><strong>D2</strong> → J11 ile alt − ray arasına, <em>bant yukarıda</em></li>
<li><strong>D1</strong> → G11 ile alt + ray arasına, <em>bant aşağıda</em></li>
<li>Turuncu kablo: <strong>F7 → Uno A0</strong></li>
</ol>

<h2>Kalibrasyon</h2>
<ol>
<li>Mor kabloyu (<strong>F2</strong>) <strong>+ raya</strong> tak — 5 V'u ölçüyorsun</li>
<li>Multimetreyle + ray ile − ray arasını ölç, mesela <code>5.02</code></li>
<li>Seri porttan gönder: <code>kv5.02</code></li>
</ol>
<div class="olc">
<p style="margin:0;color:var(--soluk);font-size:14px">Kalibrasyondan sonra kart</p>
<div class="buyuk">5.02 V</div>
<p style="margin:0;color:var(--soluk);font-size:14px">multimetreyle aynı değeri göstermeli</p>
</div>
"""


def main() -> None:
    html = (
        "<title>Ölçüm Kartı Kurulum</title>\n"
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=IBM+Plex+Mono:wght@400;500;600&'
        'family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&display=swap">\n'
        + STIL + '\n<div class="s">\n'
        + ADIM2.replace("{SVG2}", svg("breadboard-adim2.svg"))
        + ADIM3.replace("{SVG3}", svg("breadboard-adim3.svg"))
        + ADIM4.replace("{SVG4}", svg("breadboard-adim4.svg"))
        + "\n</div>\n")
    HEDEF.write_text(html, encoding="utf-8")
    print(f"yazildi: {HEDEF.name}  ({HEDEF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
