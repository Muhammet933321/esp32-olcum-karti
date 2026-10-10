# -*- coding: utf-8 -*-
"""BELGELER/*.html sayfalarinin govdeleri.

belge-uret.py bu modulu cagirir. Ayri dosya cunku belge-uret.py'de
sabitler + stil, burada icerik duruyor.
"""
from __future__ import annotations

import math

import belge_grafik as G
from belge_dil import M, sec  # noqa: F401


def sek(sayi, basamak=0):
    return f"{sayi:,.{basamak}f}".replace(",", " ")


# ═══════════════════════════════════════════════════════════ index

def index(d, dil="tr"):
    tr = f"""
<div class="kpi">
  <div><span>Gerilim</span><b>±{d['nv_fs']:.0f} / ±{d['hv_fs']:.0f} V</b></div>
  <div><span>Akım</span><b>±{d['i_maks']:.1f} A</b></div>
  <div><span>Ölçüm hızı</span><b>{sek(d['sps'])} /s</b></div>
  <div><span>Osiloskop</span><b>{d['skop_azami']/1000:.0f} kSa/s</b></div>
</div>

<p>Bu kart bir <b>voltmetre</b>, <b>ampermetre</b>, <b>wattmetre</b>,
<b>enerji sayacı</b>, <b>osiloskop</b> ve <b>pil kapasite test cihazı</b>.
Tarayıcıdan kullanılıyor: <b>telefondan doğrudan</b>, ya da bilgisayara
USB ile bağlayıp oradan — <a href="6-ag.html">Bağlanma</a>.</p>

<h2>Hangi belgeye bakmalıyım?</h2>
<table>
<tr><th>Belge</th><th>İçinde ne var</th></tr>
<tr><td><a href="1-ne-yapabilir.html"><b>Ne yapabilir</b></a></td>
    <td>Kartın bütün yetenekleri, menziller, hızlar, örnek ekran
        görüntüleri. <b>Buradan başlayın.</b></td></tr>
<tr><td><a href="2-olcumler.html"><b>Ölçümler</b></a></td>
    <td>Neyi ne kadar hassas ölçüyor, ne sıklıkla, sınırları neler</td></tr>
<tr><td><a href="3-pil-testi.html"><b>Pil testi</b></a></td>
    <td>Hangi pilleri, kaç amperle, ne kadar sürede test edebiliyoruz —
        grafiklerle</td></tr>
<tr><td><a href="6-ag.html"><b>Bağlanma</b></a></td>
    <td>Karta telefondan mı bilgisayardan mı gireceğiniz, hangi adres,
        hangi kip <b>hangi durumda</b></td></tr>
<tr><td><a href="9-pc-uygulamasi.html"><b>PC uygulaması</b></a></td>
    <td>Bilgisayardaki köprü: ilk eşleştirme, başlatma, kayıtların bilgisayarda
        arşivi, Windows bildirimleri, otomatik başlatma, sorun giderme</td></tr>
<tr><td><a href="2-malzemeler.html"><b>Malzemeler</b></a></td>
    <td>Gereken her parça, elinizde olan ve alınacak olanlar</td></tr>
<tr><td><a href="4-kurulum.html"><b>Kurulum</b></a></td>
    <td>Adım adım montaj kılavuzu</td></tr>
<tr><td><a href="7-yerlesim.html"><b>Yerleşim</b></a></td>
    <td><b>Kurulum buradan başlar.</b> LEGO kılavuzu gibi alt adım alt adım:
        hangi parça hangi deliğe, hangi iz ve tel nereye, her adımda gerekenler
        ve KAPI ölçümü — çizimli</td></tr>
<tr><td><a href="8-kutu.html"><b>Kutu</b></a></td>
    <td><b>Kartlar bittikten sonrası.</b> Panel delikleri, şönt ve yük yolu, Q1,
        jaklar, kablolar — adım adım, kontrolleriyle; sonunda hangi ölçümü
        nereden yapacağın</td></tr>
<tr><td><a href="sema.pdf"><b>Şema (PDF)</b></a></td>
    <td>Devrenin tam şeması</td></tr>
<tr><td><a href="5-muhendislik.html"><b>Mühendislik</b></a></td>
    <td>Nasıl çalıştığı, tasarım kararları, doğrulama — <span
        class="rozet">isteğe bağlı</span></td></tr>
</table>

<div class="uy"><b>Kart kuruluyor.</b> Ölçüm kartı ESP32 ile çalışıyor; ADS
modülleri henüz takılı değil, yani ölçülen değerler henüz anlamlı değil. Bütün
tasarım bilgisayarda doğrulandı ({d['adim_sayisi']} adımlı bir zincir, binin
üzerinde otomatik denetim). Bu sayfalardaki değerler <b>tasarımın vaadi</b>;
tezgâhta ölçülecekler ayrı ayrı işaretli.</div>
"""
    # EN: sema.pdf BELGELER/'de, EN sayfa BELGELER/en/'de -> bir ust klasor
    en = f"""
<div class="kpi">
  <div><span>Voltage</span><b>±{d['nv_fs']:.0f} / ±{d['hv_fs']:.0f} V</b></div>
  <div><span>Current</span><b>±{d['i_maks']:.1f} A</b></div>
  <div><span>Sample rate</span><b>{sek(d['sps'])} /s</b></div>
  <div><span>Oscilloscope</span><b>{d['skop_azami']/1000:.0f} kSa/s</b></div>
</div>

<p>This board is a <b>voltmeter</b>, <b>ammeter</b>, <b>wattmeter</b>,
<b>energy meter</b>, <b>oscilloscope</b> and <b>battery capacity tester</b>.
You use it from a browser: <b>straight from your phone</b>, or by plugging it
into a computer over USB and working from there — see
<a href="6-ag.html">Connecting</a>.</p>

<h2>Which page should I read?</h2>
<table>
<tr><th>Page</th><th>What's in it</th></tr>
<tr><td><a href="1-ne-yapabilir.html"><b>What it can do</b></a></td>
    <td>Everything the board can do: ranges, speeds, example
        screens. <b>Start here.</b></td></tr>
<tr><td><a href="2-olcumler.html"><b>Measurements</b></a></td>
    <td>What it measures, how finely, how often, and where the limits are</td></tr>
<tr><td><a href="3-pil-testi.html"><b>Battery test</b></a></td>
    <td>Which batteries we can test, at what current, and how long it takes —
        with charts</td></tr>
<tr><td><a href="6-ag.html"><b>Connecting</b></a></td>
    <td>Whether to reach the board from a phone or a computer, which address,
        which mode <b>in which situation</b></td></tr>
<tr><td><a href="9-pc-uygulamasi.html"><b>PC app</b></a></td>
    <td>The bridge on your computer: first pairing, starting it, archiving
        recordings on the computer, Windows notifications, autostart,
        troubleshooting</td></tr>
<tr><td><a href="2-malzemeler.html"><b>Parts</b></a></td>
    <td>Every part you need, what you already have and what to buy</td></tr>
<tr><td><a href="4-kurulum.html"><b>Assembly</b></a></td>
    <td>Step-by-step build guide</td></tr>
<tr><td><a href="7-yerlesim.html"><b>Layout</b></a></td>
    <td><b>Assembly starts here.</b> Sub-step by sub-step, like a LEGO manual:
        which part goes in which hole, where each trace and wire runs, what each
        step needs, and a GATE measurement — illustrated</td></tr>
<tr><td><a href="8-kutu.html"><b>Enclosure</b></a></td>
    <td><b>After the boards are done.</b> Panel holes, the shunt and load path, Q1,
        jacks, cables — step by step, with checks; at the end, which measurement
        to take from where</td></tr>
<tr><td><a href="../sema.pdf"><b>Schematic (PDF)</b></a></td>
    <td>The full circuit schematic</td></tr>
<tr><td><a href="5-muhendislik.html"><b>Engineering</b></a></td>
    <td>How it works, design decisions, verification — <span
        class="rozet">optional</span></td></tr>
</table>

<div class="uy"><b>The board is being built.</b> The Measurement Board runs on
the ESP32; the ADS modules are not fitted yet, so the readings don't mean
anything yet. The whole design has been verified on the computer (a
{d['adim_sayisi']}-step chain, more than a thousand automated checks). The values
on these pages are <b>what the design promises</b>; the ones still to be measured
on the bench are marked individually.</div>
"""
    return sec(M(tr, en), dil)


# ═══════════════════════════════════════════════════ 1 · ne yapabilir

def ne_yapabilir(d, T, NORMAL, HV, dil="tr"):
    nok = G.pil_egrisi(4.2, 3.0, 2.5, 4.7)
    g_menzil = G.menzil(T, NORMAL, HV, d['skop_adim'], dil=dil)
    g_skop = G.skop_ekrani(d['skop_bolme'], d['skop_azami'], d['skop_asgari'],
                           d['skop_adim'], dil=dil)
    g_canli = G.canli_olcum(dil=dil)
    g_mah = G.pil_mah(nok, dil=dil)
    g_hiz = G.hizlar(d['hiz_kalem'], dil=dil)
    tr = f"""
<p>Kart altı işi birden yapıyor. Hepsi aynı anda çalışıyor; tarayıcıdan
tek ekranda görüyorsunuz.</p>

<div class="kpi">
  <div><span>1 · Voltmetre</span><b>±{d['hv_fs']:.0f} V</b></div>
  <div><span>2 · Ampermetre</span><b>±{d['i_maks']:.1f} A</b></div>
  <div><span>3 · Wattmetre</span><b>±{d['p_maks']/1000:.1f} kW</b></div>
  <div><span>4 · Enerji sayacı</span><b>{sek(d['wh_tavan'])} Wh</b></div>
  <div><span>5 · Osiloskop</span><b>{d['skop_azami']/1000:.0f} kSa/s</b></div>
  <div><span>6 · Pil testi</span><b>≤ {d['pil_azami_v']:.0f} V pil</b></div>
</div>

<h2>Ne kadarını, ne kadar ince ölçüyor</h2>
<figure>{g_menzil}
<figcaption>Her çubuğun sol ucu <b>ayırt edebildiği en küçük değişim</b>,
sağ ucu <b>ölçebildiği en büyük değer</b>. Çubuk ne kadar uzunsa menzil o
kadar geniş.</figcaption></figure>

<h2>Osiloskop — dalga şeklini görmek</h2>
<p>Multimetreniz size bir <i>sayı</i> verir. Osiloskop <i>şekli</i>
gösterir: anahtarlama, çalma, tepe, gürültü. Aşağıda kartın 20 kHz'lik bir
anahtarlamalı güç kaynağını nasıl gördüğü var.</p>
<figure>{g_skop}
<figcaption>Zaman tabanı 100 µs/bölme'den 500 ms/bölme'ye kadar
ayarlanabiliyor — yani hem mikrosaniyelik anahtarlamayı hem saniyelerce
süren bir olayı görebiliyorsunuz.</figcaption></figure>

<h2>Wattmetre — gerçek güç, işaretli</h2>
<p>Güç, gerilim ile akımın <b>her örnekte çarpımı</b>. Bu yüzden reaktif
yükte de doğru: akım gerilimden geri kalsa bile kart gerçek gücü buluyor.
İşaretli olması da önemli — <b>negatif güç</b> yükün geri besleme yaptığı
anlamına gelir.</p>
<figure>{g_canli}
<figcaption>Reaktif bir yük: akım gerilimden 60° geride. Ortalama güç,
tepe değerlerin çarpımından çok daha küçük — kart bunu doğru
hesaplıyor.</figcaption></figure>

<h2>Pil kapasite testi</h2>
<p>Bir pilin gerçekte kaç mAh olduğunu ölçüyor. Kesme gerilimini siz
giriyorsunuz, kart pili boşaltıyor ve o gerilime inince <b>kendisi
kesiyor</b>.</p>
<figure>{g_mah}
<figcaption>Örnek: 2500 mAh'lik bir 18650, 4.7 Ω taş dirençle boşaltılıyor.
Sonuç <b>{nok[-1][3]:.0f} mAh</b>. Ayrıntılar
<a href="3-pil-testi.html">pil testi sayfasında</a>.</figcaption></figure>

<h2>Hangi işi ne sıklıkta ölçüyor</h2>
<figure>{g_hiz}
<figcaption>Wattmetre saniyede {sek(d['sps'])} kez ölçüyor — yani
{d['rapor_ms']:.0f} ms'lik her raporda {sek(d['ornek_pencere'])} ölçümün
ortalaması var. Osiloskop çok daha hızlı ama sadece kısa bir pencere
yakalıyor.</figcaption></figure>

<h2>Multimetrenizle karşılaştırma</h2>
<table>
<tr><th></th><th>ANENG AN8000</th><th>Bu kart</th></tr>
<tr><td>Gerilim çözünürlüğü (40 V'ta)</td><td class="s">10 mV</td>
    <td class="s"><b>{NORMAL['adim']*1e3:.2f} mV</b></td></tr>
<tr><td>Akım çözünürlüğü</td><td class="s">1 mA (10 A kademesi)</td>
    <td class="s"><b>{d['i_adim_100m']*1e6:.0f} µA</b></td></tr>
<tr><td>Saniyede okuma</td><td class="s">3</td>
    <td class="s"><b>{sek(d['sps'])}</b></td></tr>
<tr><td>Dalga şekli</td><td>—</td><td><b>var</b></td></tr>
<tr><td>Güç / enerji</td><td>—</td><td><b>var</b></td></tr>
<tr><td>Pil kapasitesi</td><td>—</td><td><b>var</b></td></tr>
<tr><td>Mutlak doğruluk</td><td>±%0.5 + 4 hane</td>
    <td>kalibrasyon referansı kadar</td></tr>
</table>
<div class="uy"><b>Önemli:</b> kart multimetrenizden çok daha <b>ince</b>
ölçüyor ama daha <b>doğru</b> değil. Kartı multimetrenize göre kalibre
ederseniz mutlak doğruluğu multimetreniz kadar olur (±%0.8). Kart küçük
<i>değişimleri</i> görür; "gerçek değer bu" demek için referans
gerekir.</div>

<h2>Yapamadıkları</h2>
<table>
<tr><th>Yapamaz</th><th>Neden</th></tr>
<tr><td>Direnç, kapasite, diyot, süreklilik</td>
    <td>Bilerek yapılmadı — multimetreniz zaten yapıyor</td></tr>
<tr><td>AC gerilimi doğrudan okumak</td>
    <td>Wattmetre yolu ortalama gösteriyor, AC'de ~0. AC dalga için
        osiloskop yolunu kullanın</td></tr>
<tr><td>{d['f_sinir']:.0f} Hz üstünde güç ölçmek</td>
    <td>Faz kalibrasyonu şebeke bandı için geçerli
        (<a href="2-olcumler.html">ayrıntı</a>)</td></tr>
<tr><td>Bozuk dalgada (harmonikli) doğru güç</td>
    <td>Wattmetre yolu <b>temel bileşen</b> ölçer; dalga şekli işi hızlı
        yolun</td></tr>
<tr><td>{d['pil_azami_v']:.0f} V üstündeki pilleri test etmek</td>
    <td>Anahtarlama MOSFET'inin sınırı — kart bunu reddediyor</td></tr>
<tr><td>Şebekeden izole ölçüm</td>
    <td>Kart izole değil; şebeke gerilimiyle çalışırken prosedür gerekir</td></tr>
</table>
"""
    en = f"""
<p>The board does six jobs at once. They all run at the same time, and you see
them on one screen in the browser.</p>

<div class="kpi">
  <div><span>1 · Voltmeter</span><b>±{d['hv_fs']:.0f} V</b></div>
  <div><span>2 · Ammeter</span><b>±{d['i_maks']:.1f} A</b></div>
  <div><span>3 · Wattmeter</span><b>±{d['p_maks']/1000:.1f} kW</b></div>
  <div><span>4 · Energy meter</span><b>{sek(d['wh_tavan'])} Wh</b></div>
  <div><span>5 · Oscilloscope</span><b>{d['skop_azami']/1000:.0f} kSa/s</b></div>
  <div><span>6 · Battery test</span><b>≤ {d['pil_azami_v']:.0f} V battery</b></div>
</div>

<h2>How much it measures, and how finely</h2>
<figure>{g_menzil}
<figcaption>The left end of each bar is the <b>smallest change it can
resolve</b>, the right end the <b>largest value it can measure</b>. The longer
the bar, the wider the range.</figcaption></figure>

<h2>Oscilloscope — seeing the waveform</h2>
<p>Your multimeter gives you a <i>number</i>. An oscilloscope shows the
<i>shape</i>: switching edges, ringing, peaks, noise. Below is how the board
sees a 20 kHz switch-mode power supply.</p>
<figure>{g_skop}
<figcaption>The time base goes from 100 µs/div to 500 ms/div — so you can see
both microsecond switching and an event that lasts several
seconds.</figcaption></figure>

<h2>Wattmeter — real power, signed</h2>
<p>Power is voltage times current <b>multiplied sample by sample</b>. That is
why it is right on reactive loads too: even when the current lags the voltage,
the board finds the real power. Being signed matters as well — <b>negative
power</b> means the load is feeding energy back.</p>
<figure>{g_canli}
<figcaption>A reactive load: the current lags the voltage by 60°. The average
power is much smaller than the product of the peaks — and the board gets
it right.</figcaption></figure>

<h2>Battery capacity test</h2>
<p>It measures how many mAh a battery really holds. You enter the cut-off
voltage, the board discharges the battery and <b>disconnects the load by
itself</b> when it gets there.</p>
<figure>{g_mah}
<figcaption>Example: a 2500 mAh 18650 discharged through a 4.7 Ω power
resistor. Result: <b>{nok[-1][3]:.0f} mAh</b>. Details on the
<a href="3-pil-testi.html">battery test page</a>.</figcaption></figure>

<h2>How often it measures each thing</h2>
<figure>{g_hiz}
<figcaption>The wattmeter measures {sek(d['sps'])} times a second — so every
{d['rapor_ms']:.0f} ms report is the average of {sek(d['ornek_pencere'])}
measurements. The oscilloscope is much faster, but it only captures a short
window.</figcaption></figure>

<h2>Compared with your multimeter</h2>
<table>
<tr><th></th><th>ANENG AN8000</th><th>This board</th></tr>
<tr><td>Voltage resolution (at 40 V)</td><td class="s">10 mV</td>
    <td class="s"><b>{NORMAL['adim']*1e3:.2f} mV</b></td></tr>
<tr><td>Current resolution</td><td class="s">1 mA (10 A range)</td>
    <td class="s"><b>{d['i_adim_100m']*1e6:.0f} µA</b></td></tr>
<tr><td>Readings per second</td><td class="s">3</td>
    <td class="s"><b>{sek(d['sps'])}</b></td></tr>
<tr><td>Waveform</td><td>—</td><td><b>yes</b></td></tr>
<tr><td>Power / energy</td><td>—</td><td><b>yes</b></td></tr>
<tr><td>Battery capacity</td><td>—</td><td><b>yes</b></td></tr>
<tr><td>Absolute accuracy</td><td>±0.5% + 4 digits</td>
    <td>as good as the calibration reference</td></tr>
</table>
<div class="uy"><b>Important:</b> the board measures much more <b>finely</b>
than your multimeter, but not more <b>accurately</b>. Calibrate it against your
multimeter and its absolute accuracy becomes that of the multimeter (±0.8%).
The board sees small <i>changes</i>; to say "this is the true value" you need
a reference.</div>

<h2>What it can't do</h2>
<table>
<tr><th>Can't</th><th>Why</th></tr>
<tr><td>Resistance, capacitance, diode, continuity</td>
    <td>Left out on purpose — your multimeter already does them</td></tr>
<tr><td>Read AC voltage directly</td>
    <td>The wattmeter path shows the average, ~0 on AC. For an AC waveform use
        the oscilloscope path</td></tr>
<tr><td>Measure power above {d['f_sinir']:.0f} Hz</td>
    <td>The phase calibration holds for the mains band
        (<a href="2-olcumler.html">details</a>)</td></tr>
<tr><td>Correct power on distorted (harmonic-rich) waveforms</td>
    <td>The wattmeter path measures the <b>fundamental</b>; waveform shape is
        the fast path's job</td></tr>
<tr><td>Test batteries above {d['pil_azami_v']:.0f} V</td>
    <td>The limit of the switching MOSFET — the board refuses them</td></tr>
<tr><td>Measure isolated from the mains</td>
    <td>The board is not isolated; working on mains voltage needs a
        procedure</td></tr>
</table>
"""
    return sec(M(tr, en), dil)


# ═══════════════════════════════════════════════════════ 2 · olcumler

def olcumler(d, T, NORMAL, HV, dil="tr"):
    sont = ""
    sont_en = ""
    for r in T.SONT_SECENEK:
        adc = T.ADS_AKIM_KIRPMA / r
        isil = T.SONT_AKIM_ISIL[r]
        m = min(adc, isil)
        a = (T.ADS_AKIM_KIRPMA / T.ADS_SAYIM) / r
        ad = f"{r:g} Ω" if r >= 1 else f"{r*1e3:.0f} mΩ"
        kim = "ADC" if adc < isil else "şöntün ısınması"
        sont += (f"<tr><td>{ad}</td><td class='s'>±{m:.3f} A</td>"
                 f"<td class='s'>{a*1e6:.1f} µA</td><td>{kim}</td></tr>")
        kim_en = "ADC" if adc < isil else "shunt heating"
        sont_en += (f"<tr><td>{ad}</td><td class='s'>±{m:.3f} A</td>"
                    f"<td class='s'>{a*1e6:.1f} µA</td><td>{kim_en}</td></tr>")
    tdiv = ""
    for us in d['skop_tdiv']:
        hz = min(max(d['skop_bolme'] * 100 / (us * 1e-6 * d['skop_bolme']),
                     d['skop_asgari']), d['skop_azami'])
        pen = us * d['skop_bolme'] * 1e-6
        n = max(100, min(pen * hz, 4096))
        et = (f"{us} µs" if us < 1000 else
              (f"{us/1000:.0f} ms" if us < 1e6 else f"{us/1e6:.0f} s"))
        tdiv += (f"<tr><td>{et}</td><td class='s'>{hz/1000:.2f} kSa/s</td>"
                 f"<td class='s'>{pen*1000:.0f} ms</td>"
                 f"<td class='s'>{n:.0f}</td></tr>")
    g_hiz = G.hizlar(d['hiz_kalem'], dil=dil)
    tr = f"""
<p>Bu sayfa "neyi, ne kadar hassas, ne sıklıkla" sorusunun cevabı.</p>

<h2>Gerilim</h2>
<p>İki menzil var ve kart <b>otomatik</b> geçiş yapıyor. İkisi de
<b>çift yönlü</b> — eksi gerilimi de okuyor.</p>
<table>
<tr><th>Menzil</th><th class="s">Ölçebildiği</th><th class="s">Adım</th>
    <th class="s">Saniyede</th></tr>
<tr><td><b>NORMAL</b></td><td class="s">±{NORMAL['fs_sim']:.1f} V</td>
    <td class="s">{NORMAL['adim']*1e3:.3f} mV</td>
    <td class="s">{sek(d['sps'])}</td></tr>
<tr><td><b>YÜKSEK</b></td><td class="s">±{HV['fs_sim']:.1f} V</td>
    <td class="s">{HV['adim']*1e3:.2f} mV</td>
    <td class="s">{sek(d['sps'])}</td></tr>
</table>
<div class="no"><b>⚠ 615 V ölümcüldür.</b> Yüksek menzil şebeke ve
üstündeki gerilimler için. Ayrı, işaretli bir girişten bağlanıyor ve
o girişteyken karta dokunulmaz.</div>

<h2>Akım</h2>
<p>Şöntü değiştirerek menzil seçiyorsunuz. Küçük şönt = büyük akım,
büyük şönt = ince çözünürlük.</p>
<table>
<tr><th>Takılı şönt</th><th class="s">Ölçebildiği</th><th class="s">Adım</th>
    <th>Sınırı koyan</th></tr>{sont}</table>
<p class="kucuk">15 mΩ şöntte <b>Kelvin bağlantısı şart</b> — lehim
direnci şöntün kendisiyle aynı mertebede olduğu için.</p>

<h2>Güç ve enerji</h2>
<table>
<tr><td>Güç</td><td class="s">±{d['p_maks']/1000:.1f} kW</td>
    <td>gerilim × akım, <b>işaretli</b> (negatif = geri besleme)</td></tr>
<tr><td>Enerji</td><td class="s">±{sek(d['wh_tavan'])} Wh</td>
    <td>25 W'ta {d['wh_tavan']/25:.0f} saat boyunca taşmaz</td></tr>
<tr><td>Yük (pil testi)</td><td class="s">±{sek(d['mah_tavan']/1000)} Ah</td>
    <td>şarj yönünde <b>geri sayar</b></td></tr>
</table>
<div class="uy"><b>Güç ölçümünün geçerli olduğu bant: 40–70 Hz.</b>
Kart şebeke frekansında (50/60 Hz) kalibre ediliyor ve o bandın dışında
kalibrasyon geçerliliğini yitiriyor. <code>f</code> ayarı bu yüzden
{d['f_sinir']:.0f} Hz'de kesiliyor. DC ölçerken ayarı <b>DC</b> yapın —
yoksa güç %82 yüksek okunur (arayüz bunu uyarıyor).</div>

<h2>Osiloskop</h2>
<table>
<tr><th>Zaman tabanı</th><th class="s">Örnekleme</th>
    <th class="s">Pencere</th><th class="s">Örnek</th></tr>{tdiv}</table>
<table>
<tr><td>Dikey menzil</td>
    <td class="s">{d['skop_eksi']:.1f} … +{d['skop_arti']:.1f} V</td></tr>
<tr><td>Dikey adım</td><td class="s">{d['skop_adim']*1e3:.1f} mV</td></tr>
<tr><td>Bant genişliği</td><td class="s">{d['sk_f0']/1000:.1f} kHz</td></tr>
</table>
<p class="kucuk">Osiloskop kanalı <b>dalga şekli</b> için. Sayısal
kesinlik isteyen ölçümü wattmetre yolundan alın — o 16 bit, bu 12 bit.</p>

<h2>Ölçüm hızı — ne demek</h2>
<figure>{g_hiz}
<figcaption>Wattmetre yolu saniyede {sek(d['sps'])} kez örnekliyor.
Ekrandaki değer varsayılan olarak {d['rapor_ms']:.0f} ms'de bir yenileniyor
(panelden 50 ms … 1 s arası seçilebilir) ve her yenileme
{sek(d['ornek_pencere'])} ölçümün ortalaması — bu, gürültüyü
{math.sqrt(d['ornek_pencere']):.0f} kat bastırıyor.</figcaption></figure>

<h2>Hassasiyet ile doğruluk aynı şey değil</h2>
<table>
<tr><th></th><th>Ne demek</th><th>Bu kartta</th></tr>
<tr><td><b>Adım</b></td><td>Okuyabildiği en küçük basamak</td>
    <td class="s">{NORMAL['adim']*1e3:.2f} mV</td></tr>
<tr><td><b>Gürültü</b></td><td>Sabit girişte okumanın oynaması</td>
    <td class="s">{d['gurultu_ort']*1e3:.3f} mV</td></tr>
<tr><td><b>Doğruluk</b></td><td>Gerçek değere ne kadar yakın</td>
    <td>kalibrasyon referansı kadar (±%0.8)</td></tr>
</table>
<p>Kart 0.04 mV'luk bir <i>değişimi</i> görebiliyor ama "bu gerilim tam
12.000 V" diyemiyor — çünkü onu söyleyebilmek için ondan daha doğru bir
referans gerekiyor. Pratikte bu şu demek: <b>karşılaştırma ve eğilim
için mükemmel, mutlak kalibrasyon için multimetreniz kadar.</b></p>
"""
    en = f"""
<p>This page answers "what, how precisely, and how often".</p>

<h2>Voltage</h2>
<p>There are two ranges and the board switches between them
<b>automatically</b>. Both are <b>bidirectional</b> — it reads negative voltage
too.</p>
<table>
<tr><th>Range</th><th class="s">Measures up to</th><th class="s">Step</th>
    <th class="s">Per second</th></tr>
<tr><td><b>NORMAL</b></td><td class="s">±{NORMAL['fs_sim']:.1f} V</td>
    <td class="s">{NORMAL['adim']*1e3:.3f} mV</td>
    <td class="s">{sek(d['sps'])}</td></tr>
<tr><td><b>HIGH</b></td><td class="s">±{HV['fs_sim']:.1f} V</td>
    <td class="s">{HV['adim']*1e3:.2f} mV</td>
    <td class="s">{sek(d['sps'])}</td></tr>
</table>
<div class="no"><b>⚠ 615 V is lethal.</b> The high range is for mains and
above. It connects through a separate, marked input, and while that input is in
use nobody touches the board.</div>

<h2>Current</h2>
<p>You pick the range by changing the shunt. Small shunt = large current,
large shunt = fine resolution.</p>
<table>
<tr><th>Fitted shunt</th><th class="s">Measures up to</th><th class="s">Step</th>
    <th>Limited by</th></tr>{sont_en}</table>
<p class="kucuk">The 15 mΩ shunt <b>needs a Kelvin connection</b> — the solder
joints have about the same resistance as the shunt itself.</p>

<h2>Power and energy</h2>
<table>
<tr><td>Power</td><td class="s">±{d['p_maks']/1000:.1f} kW</td>
    <td>voltage × current, <b>signed</b> (negative = feeding back)</td></tr>
<tr><td>Energy</td><td class="s">±{sek(d['wh_tavan'])} Wh</td>
    <td>at 25 W it doesn't overflow for {d['wh_tavan']/25:.0f} hours</td></tr>
<tr><td>Charge (battery test)</td><td class="s">±{sek(d['mah_tavan']/1000)} Ah</td>
    <td><b>counts down</b> in the charging direction</td></tr>
</table>
<div class="uy"><b>Power measurement is valid in the 40–70 Hz band.</b>
The board is calibrated at mains frequency (50/60 Hz) and the calibration no
longer holds outside that band. That is why the <code>f</code> setting stops at
{d['f_sinir']:.0f} Hz. When measuring DC, set it to <b>DC</b> — otherwise power
reads 82% high (the interface warns you about this).</div>

<h2>Oscilloscope</h2>
<table>
<tr><th>Time base</th><th class="s">Sample rate</th>
    <th class="s">Window</th><th class="s">Samples</th></tr>{tdiv}</table>
<table>
<tr><td>Vertical range</td>
    <td class="s">{d['skop_eksi']:.1f} … +{d['skop_arti']:.1f} V</td></tr>
<tr><td>Vertical step</td><td class="s">{d['skop_adim']*1e3:.1f} mV</td></tr>
<tr><td>Bandwidth</td><td class="s">{d['sk_f0']/1000:.1f} kHz</td></tr>
</table>
<p class="kucuk">The oscilloscope channel is for <b>waveform shape</b>. Take
measurements that need numeric precision from the wattmeter path — that one is
16-bit, this one 12-bit.</p>

<h2>Sample rate — what it means</h2>
<figure>{g_hiz}
<figcaption>The wattmeter path samples {sek(d['sps'])} times a second.
By default the value on screen refreshes every {d['rapor_ms']:.0f} ms
(selectable from 50 ms to 1 s in the panel), and each refresh is the average of
{sek(d['ornek_pencere'])} measurements — which suppresses noise by a factor of
{math.sqrt(d['ornek_pencere']):.0f}.</figcaption></figure>

<h2>Resolution is not the same as accuracy</h2>
<table>
<tr><th></th><th>What it means</th><th>On this board</th></tr>
<tr><td><b>Step</b></td><td>The smallest digit it can read</td>
    <td class="s">{NORMAL['adim']*1e3:.2f} mV</td></tr>
<tr><td><b>Noise</b></td><td>How much the reading wanders with a steady input</td>
    <td class="s">{d['gurultu_ort']*1e3:.3f} mV</td></tr>
<tr><td><b>Accuracy</b></td><td>How close it is to the true value</td>
    <td>as good as the calibration reference (±0.8%)</td></tr>
</table>
<p>The board can see a 0.04 mV <i>change</i>, but it can't say "this voltage is
exactly 12.000 V" — to say that you need a reference more accurate than the
board. In practice: <b>excellent for comparisons and trends; for absolute
calibration, as good as your multimeter.</b></p>
"""
    return sec(M(tr, en), dil)


# ═══════════════════════════════════════════════════════ 3 · pil testi

def pil_testi(d, T, dil="tr"):
    piller = [("18650 Li-ion (1 hücre)", 4.2, 3.0, 2.5),
              ("LiPo 2S", 8.4, 6.0, 2.2),
              ("LiPo 3S", 12.6, 9.0, 2.2),
              ("LiPo 6S", 25.2, 18.0, 2.2),
              ("12 V kurşun asit", 13.0, 10.5, 7.0),
              ("24 V akü", 29.0, 21.0, 7.0),
              ("9 V pil", 9.0, 6.0, 0.5),
              ("AA / AAA (NiMH)", 1.45, 0.9, 2.0)]
    # EN adlar ayni sirada (piller ile eslesir)
    adlar_en = ["18650 Li-ion (1 cell)", "LiPo 2S", "LiPo 3S", "LiPo 6S",
                "12 V lead-acid", "24 V battery", "9 V battery",
                "AA / AAA (NiMH)"]
    sat = ""
    sat_en = ""
    for (ad, v0, vk, ah), ad_en in zip(piller, adlar_en):
        if v0 > d['pil_azami_v']:
            sat += (f"<tr><td>{ad}</td><td class='s'>{v0} V</td>"
                    f"<td colspan='3' style='color:var(--kotu)'>"
                    f"sınır dışı — {d['pil_azami_v']:.1f} V üstü</td></tr>")
            sat_en += (f"<tr><td>{ad_en}</td><td class='s'>{v0} V</td>"
                       f"<td colspan='3' style='color:var(--kotu)'>"
                       f"out of range — above {d['pil_azami_v']:.1f} V</td></tr>")
            continue
        R = max(1.0, round(v0 / 0.9 / 0.5) * 0.5)
        i0 = v0 / R
        sure = ah / ((i0 + vk / R) / 2)
        sat += (f"<tr><td>{ad}</td><td class='s'>{v0} V</td>"
                f"<td class='s'>{vk} V</td>"
                f"<td class='s'>{R:.1f} Ω</td>"
                f"<td class='s'>{i0*1000:.0f} mA</td>"
                f"<td class='s'>{sure:.1f} sa</td></tr>")
        sat_en += (f"<tr><td>{ad_en}</td><td class='s'>{v0} V</td>"
                   f"<td class='s'>{vk} V</td>"
                   f"<td class='s'>{R:.1f} Ω</td>"
                   f"<td class='s'>{i0*1000:.0f} mA</td>"
                   f"<td class='s'>{sure:.1f} h</td></tr>")
    nok = G.pil_egrisi(4.2, 3.0, 2.5, 4.7)
    g_zaman = G.pil_zaman(nok, dil=dil)
    g_mah = G.pil_mah(nok, dil=dil)
    g_birikim = G.pil_birikim(nok, dil=dil)
    g_dcir = G.pil_dcir(nok, dil=dil)
    tr = f"""
<p>Bir pilin gerçekte kaç mAh olduğunu ölçer. Piyasadaki
<b>ZB2L3</b> gibi çalışır ama fazlası var: aynı anda <b>Wh</b>,
saniyede {sek(d['sps'])} örnek ve <b>iç direnç</b> ölçümü.</p>

<div class="kpi">
  <div><span>En yüksek pil gerilimi</span><b>{d['pil_azami_v']:.1f} V</b></div>
  <div><span>En yüksek akım</span><b>{d['pil_akim']:.2f} A</b></div>
  <div><span>Kapasite tavanı</span><b>{sek(d['mah_tavan']/1000)} Ah</b></div>
  <div><span>Kayıt</span><b>1, 5, 20, 50/s ya da her örnek</b></div>
</div>

<h2>Nasıl kullanılır</h2>
<ol>
<li>Bir <b>taş direnç</b> (yük) alın — 18650 için 4.7–7.5 Ω / 10 W</li>
<li>Pilin (+) ucunu <b>V girişine</b>, direnç üzerinden (−) ucunu
    <b>J7</b>'ye bağlayın</li>
<li>Arayüzde <b>kesme gerilimini</b> girin (Li-ion 3.0 V)</li>
<li><b>Testi başlat</b>'a basın — kart önce {d['pil_ocv_s']:.0f} s yükü bağlamadan
    pilin boştaki gerilimini (<b>OCV</b>) kaydeder, sonra yükü açar; gerisi
    kendiliğinden</li>
</ol>
<p>Kesme tek bir anlık okumaya değil, gerilimin {d['pil_tau_s']:.0f} saniyelik
<b>kayan ortalamasına</b> bakar: yük altındaki gürültü testi erken bitirmez.</p>

<h2>Kablo ve temas düşümü (hat direnci)</h2>
<p>Kart pilin gerilimini kutunun içinde ölçer. Akımın geçtiği eksi hatta (kutu içi
PİL 2 → COM bağlantısı, kablo, krokodil temasları) küçük bir direnç vardır ve yük
altında pil olduğundan <b>düşük</b> görünür: 1.13 A'de 0.15 Ω yaklaşık
<b>0.17 V</b> demek. COM ayrı bir ölçüm teli olarak kullanılamaz (kutuda PİL 2 ile
aynı nokta); bunun yerine kart bu <b>hat direncini</b> (0–1000 mΩ) bilip pil testinin
gerilimini <b>V + I × R</b> olarak düzeltir. Kısa ve kalın kablo düşümü zaten azaltır.</p>
<ol>
<li>Test sürerken (akım en az 0.1 A) multimetreyi pilin <b>kendi kutuplarına</b> tutun</li>
<li>Panelde <b>Multimetreyle düzelt</b>'e multimetrenin gösterdiğini yazın — kart
    direnci hesaplayıp hemen uygular (elle: <code>Ph150</code> = 150 mΩ)</li>
</ol>
<p class="kucuk">Düzeltme <b>yalnız pil testinin gerilimine</b> uygulanır (kesme, eğri,
sonuç). Canlı ekran, ölçüm kayıtları, osiloskop ve akım her zaman ham ölçümdür.
Kayıtta ölçüm ham kalır, direncin değiştiği an kayda yazılır ve Kayıtlar her noktayı o
andaki dirençle gösterir. Varsayılan 0 = düzeltme yok.</p>
<div class="no"><b>⚠ Yükü J7'ye bağlayın, J3'e değil.</b> J3 doğrudan
ölçüme gider; oraya bağlarsanız <b>otomatik kesme çalışmaz</b> ve pil
aşırı boşalır. Kart bunu başlangıçta denetleyip testi reddediyor, ama
yine de dikkat edin.</div>
<div class="ok"><b>Kart ölürse yük kendiliğinden kesilir.</b> Anahtarın
kapısı toprağa çekili; kart resetlense, çökse ya da fişi çekilse MOSFET
kapanır ve pil boşalmayı durdurur.</div>

<h2>Hangi pilleri test edebiliyoruz</h2>
<table>
<tr><th>Pil</th><th class="s">Dolu</th><th class="s">Kesme</th>
    <th class="s">Önerilen yük</th><th class="s">Akım</th>
    <th class="s">Süre</th></tr>{sat}</table>
<p class="kucuk">Süreler tipik kapasiteye göre. Daha hızlı test için daha
küçük direnç kullanın — ama direncin gücüne dikkat: 18650'de 4.7 Ω
yaklaşık 3.8 W yakar, yani <b>en az 10 W</b>'lık bir direnç gerekir.</p>

<h2>Test sırasında ne görüyorsunuz</h2>
<figure>{g_zaman}
<figcaption>Gerilim ve akım, zamana göre. Taş direnç sabit değer olduğu
için pil çöktükçe akım da düşüyor ({nok[0][2]*1000:.0f} →
{nok[-1][2]*1000:.0f} mA) — bu normal.</figcaption></figure>

<figure>{g_mah}
<figcaption>Asıl <b>deşarj eğrisi</b>: gerilim, çekilen kapasiteye göre.
Aynı pili tekrar test edip eğrileri üst üste koyarsanız yaşlanmayı
görürsünüz. Bu testte sonuç <b>{nok[-1][3]:.0f} mAh</b>.</figcaption></figure>

<figure>{g_birikim}
<figcaption>Kapasite (mAh) ve enerji (Wh) ayrı ayrı birikiyor. İkisi
farklı şeyler: mAh pilin <i>yükünü</i>, Wh yaptığı <i>işi</i>
anlatır.</figcaption></figure>

<h2>İç direnç — ZB2L3'ün yapamadığı</h2>
<p><b>İç direnç ölçümü</b> açıksa (varsayılan <b>kapalı</b>) kart 5 dakikada
bir yükü {d['dcir_ms']:.0f} ms kesip gerilimin ne kadar sıçradığına bakıyor. Bu, pilin <b>iç direncini</b> veriyor — ve iç direnç
pil sağlığının en iyi göstergesi.</p>
<figure>{g_dcir}
<figcaption>Pil boşaldıkça iç direnç yükseliyor. <b>Yaşlanan bir pilde bu
eğrinin tamamı yukarı kayar</b> — kapasite düşmeden önce bile.</figcaption>
</figure>
<div class="uy"><b>Dürüst not:</b> ölçülen değer saf "ohmik" iç direnç
değil; kartın ilk örneği yükü kestikten 1.5 ms sonra geliyor, o yüzden
içinde biraz polarizasyon da var. <b>Mutlak bir değer olarak
kullanmayın</b> — ama aynı pili tekrar ölçtüğünüzde
<b>karşılaştırılabilir</b>.</div>

<h2>Veri kaybolmuyor</h2>
<p>Eğri tarayıcıda saklanıyor; <b>sekmeyi kapatsanız da duruyor</b>.
Kart da son 1.5 saati tutuyor, yani sekmeyi kapatıp açtığınızda aradaki
noktaları da alıyorsunuz. Test bitince <b>CSV indirebiliyorsunuz</b>.</p>
<div class="ok">Bilgisayarı uzun süre kapatırsanız eğride bir
<b>boşluk</b> oluşur — arayüz bunu açıkça işaretler, sessizce
uydurmaz. Ve <b>mAh/Wh toplamları etkilenmez</b>, çünkü sayaçlar
kartta kesintisiz çalışıyor.</div>

<h2>Sınırlar</h2>
<table>
<tr><td>Pil gerilimi</td><td class="s">≤ {d['pil_azami_v']:.1f} V</td>
    <td>anahtarlama MOSFET'inin sınırı; 48 V paket <b>reddedilir</b></td></tr>
<tr><td>Akım (soğutucusuz)</td><td class="s">≤ {d['pil_akim']:.2f} A</td>
    <td>üstünde MOSFET'e soğutucu gerekir</td></tr>
<tr><td>Sıcaklık ölçümü</td><td>yok</td>
    <td>ısınan hücreyi göremezsiniz — teste göz kulak olun</td></tr>
<tr><td>Sabit akım</td><td>yok</td>
    <td>taş dirençte akım düşüyor; kapasite doğru ama C-oranı değişiyor</td></tr>
</table>
"""
    en = f"""
<p>It measures how many mAh a battery really holds. It works like the common
<b>ZB2L3</b> tester, but does more: <b>Wh</b> at the same time,
{sek(d['sps'])} samples a second and <b>internal resistance</b>.</p>

<div class="kpi">
  <div><span>Max battery voltage</span><b>{d['pil_azami_v']:.1f} V</b></div>
  <div><span>Max current</span><b>{d['pil_akim']:.2f} A</b></div>
  <div><span>Capacity ceiling</span><b>{sek(d['mah_tavan']/1000)} Ah</b></div>
  <div><span>Logging</span><b>1, 5, 20, 50/s or every sample</b></div>
</div>

<h2>How to use it</h2>
<ol>
<li>Get a <b>power resistor</b> (the load) — 4.7–7.5 Ω / 10 W for an 18650</li>
<li>Connect the battery's (+) to the <b>V input</b>, and its (−) through the
    resistor to <b>J7</b></li>
<li>Enter the <b>cut-off voltage</b> in the interface (3.0 V for Li-ion)</li>
<li>Press <b>Start test</b> — the board first records the battery's open-circuit
    voltage (<b>OCV</b>) for {d['pil_ocv_s']:.0f} s with no load, then switches the
    load on; the rest is automatic</li>
</ol>
<p>The cut-off doesn't act on a single instantaneous reading but on a
{d['pil_tau_s']:.0f}-second <b>moving average</b> of the voltage, so noise under load
doesn't end the test early.</p>

<h2>Cable and contact drop (lead resistance)</h2>
<p>The board measures the battery voltage inside the enclosure. The negative
lead that carries the current (the <code>PİL 2</code> → COM link inside the
enclosure, the cable, the crocodile clip contacts) has a small resistance, so
under load the battery looks <b>lower</b> than it is: 0.15 Ω at 1.13 A is about
<b>0.17 V</b>. COM can't be used as a separate sense wire (in the enclosure it is
the same node as <code>PİL 2</code>); instead the board is told this <b>lead
resistance</b> (0–1000 mΩ) and corrects the battery test voltage to
<b>V + I × R</b>. A short, thick cable reduces the drop in the first place.</p>
<ol>
<li>While the test is running (current at least 0.1 A), hold the multimeter on the
    battery's <b>own terminals</b></li>
<li>In the panel, type what the multimeter shows into <b>Correct with
    multimeter</b> — the board works out the resistance and applies it at once
    (by hand: <code>Ph150</code> = 150 mΩ)</li>
</ol>
<p class="kucuk">The correction applies <b>only to the battery test voltage</b>
(cut-off, curve, result). The live screen, measurement recordings, oscilloscope
and current are always the raw measurement. In a recording the measurement stays
raw, the moment the resistance changes is written to the recording, and
Recordings shows every point with the resistance in force at that time.
Default 0 = no correction.</p>
<div class="no"><b>⚠ Connect the load to J7, not J3.</b> J3 goes straight to
the measurement; if you connect it there, <b>the automatic cut-off doesn't
work</b> and the battery is over-discharged. The board checks for this at the
start and refuses the test, but be careful anyway.</div>
<div class="ok"><b>If the board dies, the load is disconnected by itself.</b>
The switch's gate is pulled to ground; if the board resets, crashes or loses
power, the MOSFET turns off and the battery stops discharging.</div>

<h2>Which batteries we can test</h2>
<table>
<tr><th>Battery</th><th class="s">Full</th><th class="s">Cut-off</th>
    <th class="s">Suggested load</th><th class="s">Current</th>
    <th class="s">Time</th></tr>{sat_en}</table>
<p class="kucuk">Times are for typical capacity. For a faster test use a smaller
resistor — but mind its power rating: on an 18650, 4.7 Ω dissipates about
3.8 W, so you need a resistor of <b>at least 10 W</b>.</p>

<h2>What you see during the test</h2>
<figure>{g_zaman}
<figcaption>Voltage and current against time. Because the power resistor has a
fixed value, the current falls as the battery sags ({nok[0][2]*1000:.0f} →
{nok[-1][2]*1000:.0f} mA) — that's normal.</figcaption></figure>

<figure>{g_mah}
<figcaption>The actual <b>discharge curve</b>: voltage against capacity drawn.
Test the same battery again and overlay the curves, and you see it ageing.
Result of this test: <b>{nok[-1][3]:.0f} mAh</b>.</figcaption></figure>

<figure>{g_birikim}
<figcaption>Capacity (mAh) and energy (Wh) accumulate separately. They are
different things: mAh is the battery's <i>charge</i>, Wh is the <i>work</i> it
does.</figcaption></figure>

<h2>Internal resistance — what the ZB2L3 can't do</h2>
<p>With <b>internal resistance measurement</b> on (default <b>off</b>), every
5 minutes the board cuts the load for {d['dcir_ms']:.0f} ms and looks at how far
the voltage jumps. That gives the battery's <b>internal resistance</b> — and
internal resistance is the best indicator of battery health.</p>
<figure>{g_dcir}
<figcaption>Internal resistance rises as the battery discharges. <b>On an
ageing battery the whole curve shifts up</b> — even before the capacity
drops.</figcaption>
</figure>
<div class="uy"><b>Honest note:</b> the measured value is not the pure "ohmic"
internal resistance; the board's first sample comes 1.5 ms after the load is
cut, so some polarisation is included. <b>Don't use it as an absolute
value</b> — but it is <b>comparable</b> when you measure the same battery
again.</div>

<h2>No data is lost</h2>
<p>The curve is stored in the browser; <b>it stays even if you close the
tab</b>. The board also keeps the last 1.5 hours, so when you close and reopen
the tab you get the points in between as well. When the test ends you can
<b>download a CSV</b>.</p>
<div class="ok">If you switch the computer off for a long time, a <b>gap</b>
appears in the curve — the interface marks it clearly and doesn't quietly make
it up. And <b>the mAh/Wh totals are not affected</b>, because the counters run
on the board without interruption.</div>

<h2>Limits</h2>
<table>
<tr><td>Battery voltage</td><td class="s">≤ {d['pil_azami_v']:.1f} V</td>
    <td>the limit of the switching MOSFET; a 48 V pack is <b>refused</b></td></tr>
<tr><td>Current (no heatsink)</td><td class="s">≤ {d['pil_akim']:.2f} A</td>
    <td>above that the MOSFET needs a heatsink</td></tr>
<tr><td>Temperature measurement</td><td>none</td>
    <td>you can't see a cell heating up — keep an eye on the test</td></tr>
<tr><td>Constant current</td><td>none</td>
    <td>with a power resistor the current falls; capacity is right but the
        C-rate changes</td></tr>
</table>
"""
    return sec(M(tr, en), dil)


# ═══════════════════════════════════════════════════════ 5 · muhendislik

def muhendislik(d, T, NORMAL, HV, dil="tr"):
    tr = f"""
<p>Bu sayfa <b>nasıl çalıştığını</b> anlatıyor. Kartı kullanmak için
gerekmiyor — merak edenler için.</p>

<h2>Sinyal yolu</h2>
<table>
<tr><th>Aşama</th><th>Ne yapıyor</th></tr>
<tr><td>Gerilim bölücü</td>
    <td>±{HV['fs_sim']:.0f} V'u ADC'nin görebileceği seviyeye indiriyor.
    Bölücünün alt ucu toprağa değil <b>referans gerilime</b> bağlı — çift
    yönlülük buradan geliyor</td></tr>
<tr><td>Şönt + Kelvin</td>
    <td>Akımı gerilime çeviriyor; ölçüm uçları akım yolundan
    <b>ayrı</b> çekiliyor, böylece lehim direnci ölçüme karışmıyor</td></tr>
<tr><td>Örtüşme süzgeci</td>
    <td>Her iki kanalda <b>aynı</b> zaman sabiti ({d['tau_v']*1e3:.2f} ms /
    {d['tau_i']*1e3:.2f} ms). Farklı olsalardı reaktif yükte güç hatası
    devasa olurdu</td></tr>
<tr><td>16 bit ADC ×2</td>
    <td>Gerilim ve akım <b>eş zamanlı</b> tek atışla örnekleniyor; kalan
    {d['t_yaz']:.0f} µs'lik kayma yazılımda siliniyor</td></tr>
<tr><td>Güç hesabı</td>
    <td><b>Örnek başına</b> çarpım: ort(V×I). ort(V)×ort(I) <b>değil</b> —
    anahtarlamalı yükte o yanlış cevap verir</td></tr>
</table>

<h2>Neden bu sayılar</h2>
<table>
<tr><td>Ölçüm hızı {sek(d['sps'])}/s</td>
    <td>ADC'nin 860/s'i ile I2C yazma-okuma süresinin toplamı. Tek atış
    kipi eş zamanlılık kazandırıyor, karşılığında hızın
    %{(1-d['sps']/T.ADS_SPS)*100:.0f}'i gidiyor</td></tr>
<tr><td>Süzgeç {1/(2*math.pi*d['tau_v']):.0f} Hz</td>
    <td>Örnekleme hızının yarısının altında kalmalı, yoksa yüksek frekanslı
    bileşenler banda katlanır ve <b>geri döndürülemez</b></td></tr>
<tr><td>Geçerli bant 40–70 Hz</td>
    <td>Faz kalibrasyonu sabit bir gecikme saklıyor; düzelttiği şey ise
    frekansa göre değişen bir faz farkı. İkisi yalnızca kalibrasyon
    frekansı civarında örtüşüyor</td></tr>
<tr><td>Pil ≤ {d['pil_azami_v']:.1f} V</td>
    <td>Anahtar kapalıyken pilin tamamı MOSFET'in üstünde; 55 V'luk parçaya
    %70 pay bırakıldı</td></tr>
</table>

<h2>Doğrulama</h2>
<p>Tasarımın tamamı bilgisayarda sınanıyor. Her iddia <b>çalıştırılabilir
bir testle</b> destekleniyor; hiçbir sayı elle yazılmıyor.</p>
<div class="kpi">
  <div><span>Doğrulama adımı</span><b>15</b></div>
  <div><span>Otomatik denetim</span><b>900+</b></div>
  <div><span>Devre simülasyonu</span><b>ngspice</b></div>
  <div><span>Firmware</span><b>emülatörde koşuyor</b></div>
</div>
<p>Ölçüm matematiği <b>gerçek firmware kodu</b> olarak, bit-birebir
doğrulanmış bir işlemci emülatöründe koşturuluyor — yani sınanan şey
kartta çalışacak kodun ta kendisi.</p>
<p>Ayrıca her yeni iddia <b>mutasyon testinden</b> geçiyor: ilgili sabit
bilerek bozuluyor ve testin kırmızıya döndüğü gösteriliyor. Dönmüyorsa
iddia boştur ve siliniyor.</p>

<div class="uy"><b>Zincir tasarımı doğruluyor, kurulmuş bir kartı
değil.</b> Gerçek bileşen toleransları, sıcaklık sürüklenmesi, delikli
plaketteki kaçaklar ve gürültü ancak tezgâhta ölçülür.</div>

<h2>Ayrıntı nerede</h2>
<p>Tasarım kararlarının tam kaydı, bulunan kusurlar ve gerekçeleri
<code>DEVIR.md</code> dosyasında (bu klasörün bir üstünde). Orası
mühendislik günlüğü — 250 KB ve kronolojik.</p>
"""
    # EN sayfa BELGELER/en/'de: DEVIR.md iki ust klasorde
    en = f"""
<p>This page explains <b>how it works</b>. You don't need it to use the
board — it's for the curious.</p>

<h2>Signal path</h2>
<table>
<tr><th>Stage</th><th>What it does</th></tr>
<tr><td>Voltage divider</td>
    <td>Brings ±{HV['fs_sim']:.0f} V down to a level the ADC can see. The
    bottom of the divider goes to a <b>reference voltage</b>, not to ground —
    that's where the bidirectional range comes from</td></tr>
<tr><td>Shunt + Kelvin</td>
    <td>Turns current into voltage; the sense leads are routed
    <b>separately</b> from the current path, so solder resistance doesn't get
    into the measurement</td></tr>
<tr><td>Anti-aliasing filter</td>
    <td>The <b>same</b> time constant on both channels ({d['tau_v']*1e3:.2f} ms /
    {d['tau_i']*1e3:.2f} ms). If they differed, the power error on reactive
    loads would be huge</td></tr>
<tr><td>16-bit ADC ×2</td>
    <td>Voltage and current are sampled <b>simultaneously</b> in single-shot
    mode; the remaining {d['t_yaz']:.0f} µs skew is removed in software</td></tr>
<tr><td>Power calculation</td>
    <td>Product <b>per sample</b>: avg(V×I). <b>Not</b> avg(V)×avg(I) —
    on a switching load that gives the wrong answer</td></tr>
</table>

<h2>Why these numbers</h2>
<table>
<tr><td>Sample rate {sek(d['sps'])}/s</td>
    <td>The ADC's 860/s plus the I2C write-read time. Single-shot mode buys
    simultaneity at the cost of
    {(1-d['sps']/T.ADS_SPS)*100:.0f}% of the rate</td></tr>
<tr><td>Filter {1/(2*math.pi*d['tau_v']):.0f} Hz</td>
    <td>Must stay below half the sample rate, otherwise high-frequency
    components fold into the band and <b>can't be undone</b></td></tr>
<tr><td>Valid band 40–70 Hz</td>
    <td>The phase calibration stores a fixed delay, but what it corrects is a
    phase difference that changes with frequency. The two only match near the
    calibration frequency</td></tr>
<tr><td>Battery ≤ {d['pil_azami_v']:.1f} V</td>
    <td>With the switch off, the whole battery sits across the MOSFET; the
    55 V part was given a 70% margin</td></tr>
</table>

<h2>Verification</h2>
<p>The whole design is tested on the computer. Every claim is backed by
<b>a test you can run</b>; no number is typed in by hand.</p>
<div class="kpi">
  <div><span>Verification steps</span><b>15</b></div>
  <div><span>Automated checks</span><b>900+</b></div>
  <div><span>Circuit simulation</span><b>ngspice</b></div>
  <div><span>Firmware</span><b>runs in an emulator</b></div>
</div>
<p>The measurement maths runs as <b>the real firmware code</b> on a
bit-exact verified processor emulator — so what gets tested is the very code
that will run on the board.</p>
<p>On top of that, every new claim goes through <b>mutation testing</b>: the
relevant constant is deliberately broken and the test is shown to turn red. If
it doesn't, the claim is empty and gets deleted.</p>

<div class="uy"><b>The chain verifies the design, not a built
board.</b> Real component tolerances, temperature drift, leakage on the
perfboard and noise can only be measured on the bench.</div>

<h2>Where the details are</h2>
<p>The full record of design decisions, the defects found and the reasoning
behind them is in <code>DEVIR.md</code> (at the root of the repository, two
folders above this one). It is the engineering log — in Turkish, 250 KB and
chronological.</p>
"""
    return sec(M(tr, en), dil)


def ag(d, T, dil="tr"):
    """Kartla nasil konusulur — uc kip, hangi adres, hangi sinirlar.

    Bu sayfa var olmadan once BELGELER/ icinde ag hakkinda TEK SATIR
    yoktu ve `index.html` "Bilgisayara USB ile baglaniyor" diyordu.
    """
    g_bag = G.baglanti_modlari(d, dil=dil)
    tr = f"""
<p>Kartın ekranı yok; <b>tarayıcıdan</b> kullanılıyor. Üç yolu var ve
üçü de aynı arayüzü gösteriyor — hangisini kullanacağınız
<b>bilgisayarın olup olmadığına</b> ve <b>ölçümün ne kadar hassas
olması gerektiğine</b> bağlı.</p>

<figure>{g_bag}
<figcaption>Üç bağlantı kipi. Kart her kipte aynı arayüzü sunuyor;
değişen şey <b>kim yayınlıyor</b>.</figcaption></figure>

<h2>Hangisini seçmeliyim?</h2>
<table>
<tr><th>Durum</th><th>Kip</th><th>Adres</th></tr>
<tr><td>Bilgisayar yok, sadece telefon</td>
    <td><b>1 · Kartın kendi ağı</b></td>
    <td><code>192.168.4.1</code></td></tr>
<tr><td>Ev Wi-Fi'sı var, kart uzakta</td>
    <td><b>2 · Kart ev ağında</b></td>
    <td><code>http://{d['mdns']}.local</code></td></tr>
<tr><td>Bilgisayar var, ölçüm <b>izole</b></td>
    <td><b>3 · USB köprü</b></td>
    <td><code>{d['kopru_adres']}</code> (yalnız bu bilgisayar)</td></tr>
</table>

<div class="no"><b>USB her ölçümde kullanılamaz — ama Wi-Fi de tek
başına yetmez.</b> Kart izole <b>değil</b>: USB takılıyken kartın
toprağı bilgisayarınızın toprağıdır, yani şebeke referanslı bir devrede
(izole olmayan SMPS'in birincil tarafı gibi) bilgisayarınıza şebeke
gerilimi taşırsınız.
<br><br>Pil + Wi-Fi ile yüzdürmek <b>bilgisayarı kurtarır, SİZİ
KURTARMAZ</b>: kart o anda şebeke potansiyeline çıkar ve <b>kartın her
noktası</b> tehlikeli olur. Bu ölçüm için <b>yalıtımlı kutu şart</b> ve
enerji varken karta dokunulmaz. Ayrıntısı
<a href="4-kurulum.html">Kurulum</a> belgesinin başındaki uyarıda.</div>

<div class="uy"><b>Neden USB köprü (uygun olduğunda) önerilen?</b> Karta
bağlanan <b>her tarayıcı ölçümü biraz yavaşlatıyor</b> — kart hem ölçüp
hem web sunucusu çalıştırıyor. Köprü kipinde sayfayı bilgisayar
yayınlıyor ve ölçümler bilgisayarda <b>arşivleniyor</b>, kartın belleği
dolmuyor.
<br><br>⚠ <b>Kartın Wi-Fi'si kendiliğinden kapanmıyor.</b> Varsayılan
açık; kapatmak için seri konsoldan <code>N0</code> gönderin (tekrar
açmak: <code>N1</code>). Kapatınca ölçüm döngüsü web sunucusuyla hiç
uğraşmaz.</div>

<h2>1 · Bilgisayar yokken — kartın kendi ağı</h2>
<p>Kart açıldığında ev Wi-Fi'sı tanımlı değilse (ya da
<b>{d['sta_bekle_s']:.0f} saniye</b> içinde bağlanamazsa) <b>kendi
Wi-Fi ağını kuruyor</b>:</p>
<table>
<tr><th>Ağ adı</th><td><code>{d['ap_onek']}XXXX</code> — sondaki dört
    karakter kartın kendi numarası, her kartta farklı</td></tr>
<tr><th>Parola</th><td>{d['ap_parola_n']} karakter, kart ilk açılışta
    kendisi üretiyor ve <b>USB konsoluna yazıyor</b>. Bir kez okuyup
    telefona kaydedin</td></tr>
<tr><th>Adres</th><td><code>192.168.4.1</code> — sabit</td></tr>
</table>
<p>Telefon bu ağa bağlandığında internet <b>yok</b> (kart internete
çıkmıyor); Android "bu ağın interneti yok, bağlı kalınsın mı" diye
sorabilir, <b>evet</b> deyin.</p>

<h2>2 · Kart ev ağındayken</h2>
<p>Kart kendi Wi-Fi'sını kurmak yerine <b>evin ağına</b> bağlanır;
telefon ve bilgisayar zaten o ağdadır. Bağlanma {d['sta_bekle_s']:.0f}
saniye deneniyor, olmazsa 1. kipe düşüyor — yani <b>kart hiçbir zaman
erişilemez kalmıyor</b>. Kendi ağındayken ev ağını <b>{d['sta_yeniden_s']:.0f}
saniyede bir yeniden dener</b>: ev ağı sonradan gelirse (ör. elektrik
kesintisinden sonra modem karttan geç açılınca) kart kendiliğinden eve geçer,
kendi ağını {d['ap_pay_s']:.0f} saniye sonra kapatır — sıfırlamak gerekmez.
Bağlıyken ağ kısa süre koparsa kart kendiliğinden geri bağlanır;
<b>{d['sta_kopuk_s']:.0f} saniyeden uzun</b> koparsa (ör. kartı başka yere
götürdünüz) kendi ağını kurar ve kayıtlı ağları <b>hemen</b>, sonra
{d['sta_yeniden_s']:.0f} saniyede bir yeniden dener.</p>

<h3>Ağları karta tanıtmak (en çok {d['agl_azami']} ağ)</h3>
<p>Kart <b>{d['agl_azami']} ağa kadar</b> hatırlar (ev, iş yeri, telefonun
hotspot'u …). Açılışta en son bağlandığı ağı dener; o yoksa görünen kayıtlı
ağlardan <b>öncelikli</b> olanı, sonra sinyali en güçlü olanı seçer. En kolayı
panelde <b>Ayarlar → Ağ</b>: listeyi yenile, ağları tara, ekle, öncelik ver,
sil, <b>“Bu ağa geç”</b>. Aynısı seri konsoldan (115200):</p>
<table>
<tr><th><code>Na<i>AğAdı</i></code> + <code>Np<i>parola</i></code></th><td>Listeye ekle (aynı ad varsa
    seçer; <code>Np</code> son eklenenin parolasını yazar)</td></tr>
<tr><th><code>Nl</code> · <code>Nt</code></th><td>Kayıtlı ağları listele · çevredeki ağları tara
    (parola hiçbir çıktıda yok)</td></tr>
<tr><th><code>Ng<i>no</i></code></th><td><b>Bu ağa geç:</b> kart önce ağı arar, görünmüyorsa
    ayrılmaz; {d['gecis_s']:.0f} saniyede bağlanamazsa önceki ağa döner</td></tr>
<tr><th><code>No<i>no</i></code> · <code>Nx<i>no</i></code></th><td>Öncelik aç/kapa · sil (bağlı ağı
    silmek bağlantıyı koparmaz)</td></tr>
<tr><th><code>N</code></th><td>Durumu yazdırır: kip, SSID, IP, mDNS, kayıtlı ağ sayısı</td></tr>
</table>
<p>Ayarlar kartın kalıcı belleğinde durur; bir daha girmeniz gerekmez. Kart
telefonun hotspot listesinde kendi ağının adıyla (<code>OLCUM-KARTI-XXXX</code>)
görünür.</p>

<table>
<tr><th>Adres</th><td><code>http://{d['mdns']}.local</code></td></tr>
<tr><th>Çalışmazsa</th><td>Kartın IP'si USB konsolunda (<code>N</code>
    komutu) yazıyor; doğrudan onu yazın. <b>Android'de
    <code>.local</code> güvenilir değildir</b> — iPhone ve masaüstünde
    sorunsuz çalışır</td></tr>
</table>
<div class="uy"><b>Aynı anda kaç kişi bakabilir?</b> Doğrudan karta
bağlanınca <b>{d['akis_azami']} tarayıcıya</b> kadar izleyebilir; her biri
ölçümü biraz yavaşlatır. PC köprüsü karta WiFi'den bağlıyken bu yerlerden
<b>birini</b> kullanır, USB'den bağlıyken hiçbirini. Daha çok izleyici
istiyorsanız 3. kipi kullanın.</div>

<h2>3 · USB köprü — bilgisayarda; telefon yalnız izler</h2>
<p>Kart bilgisayara <b>USB ile</b> bağlanıyor, bilgisayarda küçük bir
program (<code>kopru</code> klasöründeki <code>PC Baslat.bat</code>) çalışıyor. O program hem
arayüzü yayınlıyor hem ölçümleri kaydediyor. Durdurmak için aynı
klasördeki <code>Kopruyu Durdur.bat</code>. İlk eşleştirme, kayıtların
bilgisayardaki arşivi, bildirimler ve sorun giderme:
<a href="9-pc-uygulamasi.html">PC uygulaması</a>.</p>
<table>
<tr><th>Bilgisayarda</th><td>Panel <b><code>{d['kopru_adres']}</code></b>
    — köprü yalnız bu bilgisayarı (<code>127.0.0.1</code>) dinler, başka
    bir cihaz bu adrese bağlanamaz. Port {d['kopru_port']} <b>sabit</b>:
    başka bir program tutuyorsa köprü açılmaz ve bunu söyler (başka
    porta düşmez — panelin bu bilgisayardaki ayarları adrese bağlı)</td></tr>
<tr><th>Telefonda</th><td>Köprü <code>--lan</code> ile açılırsa
    (<code>PC Baslat.bat --lan</code>) telefon aynı Wi-Fi'dan
    <code>http://&lt;bilgisayarın IP'si&gt;:{d['kopru_port']}</code>
    adresiyle <b>salt okuma</b> izler: ölçümü görür, yalnız
    <b>DURDUR</b> (pil testini kes) gönderebilir. Komut vermek için
    telefon karta doğrudan (1. ya da 2. kip) bağlanır</td></tr>
<tr><th>Kartın Wi-Fi'si</th><td>Varsayılan <b>açık</b>. Ölçüme tam hız
    istiyorsanız seri konsoldan <code>N0</code> ile kapatın</td></tr>
<tr><th>Kayıt</th><td>Her ölçüm satırı zaman damgasıyla bilgisayarda
    saklanıyor, sonradan CSV olarak alınabiliyor</td></tr>
</table>
<p>Bu kipte <b>telefonun gördüğü sayfayı bilgisayar yayınlıyor</b>,
kart değil. Telefon ile bilgisayar aynı anda kullanılabilir ve ikisi
de aynı veriyi görür; komut yalnız bilgisayardaki panelden gider.</p>

<h2>Telefonda uygulama gibi açmak</h2>
<p>Tarayıcıda sayfayı açıp <b>Ana Ekrana Ekle</b> deyin.</p>
<table>
<tr><th>iPhone</th><td>Kendi ikonuyla, <b>adres çubuğu olmadan</b>
    açılır — uygulamadan farkı yoktur</td></tr>
<tr><th>Android</th><td>Kısayol oluşur ama <b>Chrome sekmesinde</b>
    açılır. Tam ekran kurulum HTTPS istiyor; kartta HTTPS yok. Bu
    beklenen davranış</td></tr>
</table>

<h2>Arayüz nerede duruyor?</h2>
<p>Arayüzün tamamı — sayfa, Vue kütüphanesi, biçim dosyaları —
<b>kartın kendi belleğinde</b>. İnternet gerekmiyor, hiçbir dosya
dışarıdan indirilmiyor.</p>
<table>
<tr><th>Arayüz boyutu</th><td>{d['fs_icerik']/1024:.0f} KB</td></tr>
<tr><th>Ayrılan yer</th><td>{d['fs_bolum']/1024:.0f} KB
    ({d['fs_icerik']/d['fs_bolum']*100:.0f}% dolu)</td></tr>
<tr><th>Canlı veri</th><td>saniyede {d['sse_hz']:.0f} güncelleme</td></tr>
</table>

<h2>Güvenlik — ne koruyor, ne korumuyor</h2>
<p>Bağlantı <b>şifreli değil</b> (HTTPS yok). Aynı ağdaki biri
ölçümleri görebilir; bu kart için kabul edilen bir sınır.</p>
<table>
<tr><th>Her komutta</th><td><b>Oturum anahtarı</b> ve özel başlık
    zorunlu. Bu, başka bir web sayfasının sizin adınıza karta komut
    göndermesini engelliyor (CSRF)</td></tr>
<tr><th>Parola</th><td><b>Varsayılan olarak KURULU DEĞİL.</b>
    Kurulmadığı sürece, <b>ağınızdaki herkes</b> kartın sayfasını açıp
    tehlikeli komut gönderebilir. Kart bunu açılışta yüksek sesle
    söylüyor</td></tr>
<tr><th>Parolayı kurmak</th><td>Seri konsoldan
    <code>Ns<i>parola</i></code>. Kaldırmak: <code>Ns</code> (boş).
    Durumu <code>N</code> gösteriyor</td></tr>
<tr><th>Kartın kendi ağı</th><td>AP parolası kart tarafından
    üretiliyor ({d['ap_parola_n']} karakter) ve ilk açılışta USB
    konsoluna yazılıyor</td></tr>
</table>
<div class="ok"><b>Tek istisna: durdurma.</b> Pil deşarjını durduran
komut <b>her zaman</b> çalışır — oturum anahtarı da parola da
istemez. Emniyet, kolaylıktan önce gelir.</div>

<div class="uy">Parolanın koruduğu şey <i>"evdeki başka biri
yanlışlıkla basmasın"</i>dır. TLS olmadığı için ağı dinleyen birine
karşı koruma <b>değildir</b>.</div>
"""
    en = f"""
<p>The board has no screen; you use it <b>from a browser</b>. There are three
ways in, and all three show the same interface — which one you use depends on
<b>whether you have a computer</b> and <b>how precise the measurement needs to
be</b>.</p>

<figure>{g_bag}
<figcaption>The three connection modes. The board offers the same interface in
every mode; what changes is <b>who serves it</b>.</figcaption></figure>

<h2>Which one should I pick?</h2>
<table>
<tr><th>Situation</th><th>Mode</th><th>Address</th></tr>
<tr><td>No computer, just a phone</td>
    <td><b>1 · The board's own network</b></td>
    <td><code>192.168.4.1</code></td></tr>
<tr><td>Home Wi-Fi available, board elsewhere in the house</td>
    <td><b>2 · Board on the home network</b></td>
    <td><code>http://{d['mdns']}.local</code></td></tr>
<tr><td>Computer available, measurement <b>isolated</b></td>
    <td><b>3 · USB bridge</b></td>
    <td><code>{d['kopru_adres']}</code> (this computer only)</td></tr>
</table>

<div class="no"><b>USB can't be used for every measurement — but Wi-Fi alone
isn't enough either.</b> The board is <b>not</b> isolated: with USB plugged in,
the board's ground is your computer's ground, so on a mains-referenced circuit
(such as the primary side of a non-isolated SMPS) you bring mains voltage to
your computer.
<br><br>Floating it on battery + Wi-Fi <b>saves the computer, NOT
YOU</b>: the board rises to mains potential and <b>every point on the
board</b> becomes dangerous. For this measurement an <b>insulated enclosure is
a must</b>, and nobody touches the board while it is live. Details in the
warning at the top of the <a href="4-kurulum.html">Assembly</a> page.</div>

<div class="uy"><b>Why is the USB bridge recommended (when it fits)?</b>
<b>Every browser connected to the board slows the measurement down a
little</b> — the board both measures and runs a web server. In bridge mode the
computer serves the page and the measurements are <b>archived</b> on the
computer, so the board's memory doesn't fill up.
<br><br>⚠ <b>The board's Wi-Fi doesn't switch itself off.</b> It is on by
default; to turn it off send <code>N0</code> from the serial console (to turn it
back on: <code>N1</code>). With it off, the measurement loop never deals with the
web server at all.</div>

<h2>1 · Without a computer — the board's own network</h2>
<p>If no home Wi-Fi is configured when the board starts (or it can't connect
within <b>{d['sta_bekle_s']:.0f} seconds</b>), it <b>sets up its own Wi-Fi
network</b>:</p>
<table>
<tr><th>Network name</th><td><code>{d['ap_onek']}XXXX</code> — the last four
    characters are the board's own ID, different on every board</td></tr>
<tr><th>Password</th><td>{d['ap_parola_n']} characters, generated by the board on
    first start and <b>printed to the USB console</b>. Read it once and save it
    on your phone</td></tr>
<tr><th>Address</th><td><code>192.168.4.1</code> — fixed</td></tr>
</table>
<p>When the phone joins this network there is <b>no</b> internet (the board
doesn't go online); Android may ask "this network has no internet, stay
connected?" — say <b>yes</b>.</p>

<h2>2 · Board on the home network</h2>
<p>Instead of setting up its own Wi-Fi, the board joins <b>the home
network</b>; the phone and computer are already on it. It tries to connect for
{d['sta_bekle_s']:.0f} seconds, and if that fails it falls back to mode 1 — so
<b>the board is never left unreachable</b>. While on its own network it
<b>retries the home network every {d['sta_yeniden_s']:.0f} seconds</b>: if the
home network appears later (e.g. after a power cut, when the router comes up
after the board), the board moves home by itself and closes its own network
{d['ap_pay_s']:.0f} seconds later — no reset needed. If the network drops
briefly while connected, the board reconnects by itself; if it is gone for
<b>more than {d['sta_kopuk_s']:.0f} seconds</b> (e.g. you took the board
somewhere else) it sets up its own network and retries the saved networks
<b>immediately</b>, then every {d['sta_yeniden_s']:.0f} seconds.</p>

<h3>Telling the board about networks (up to {d['agl_azami']})</h3>
<p>The board remembers <b>up to {d['agl_azami']} networks</b> (home, work, your
phone's hotspot …). At start-up it tries the network it last connected to; if
that's not there, it picks a <b>preferred</b> one among the visible saved
networks, then the one with the strongest signal. The easiest way is
<b>Settings → Network</b> in the panel: Refresh list, Scan networks, add, make
preferred, Delete, <b>“Switch to this network”</b>. The same from the serial
console (115200):</p>
<table>
<tr><th><code>Na<i>NetworkName</i></code> + <code>Np<i>password</i></code></th><td>Add to the list (if the name
    exists it is selected; <code>Np</code> sets the password of the last one added)</td></tr>
<tr><th><code>Nl</code> · <code>Nt</code></th><td>List saved networks · scan for nearby networks
    (no password appears in any output)</td></tr>
<tr><th><code>Ng<i>no</i></code></th><td><b>Switch to this network:</b> the board looks for the
    network first and doesn't leave if it can't see it; if it can't connect within
    {d['gecis_s']:.0f} seconds it goes back to the previous network</td></tr>
<tr><th><code>No<i>no</i></code> · <code>Nx<i>no</i></code></th><td>Toggle preferred · delete (deleting the
    connected network doesn't drop the connection)</td></tr>
<tr><th><code>N</code></th><td>Prints the status: mode, SSID, IP, mDNS, number of saved networks</td></tr>
</table>
<p>The settings live in the board's non-volatile memory; you don't have to
enter them again. On your phone's hotspot list the board shows up under its
own network name (<code>OLCUM-KARTI-XXXX</code>).</p>

<table>
<tr><th>Address</th><td><code>http://{d['mdns']}.local</code></td></tr>
<tr><th>If that fails</th><td>The board's IP is printed on the USB console
    (<code>N</code> command); type it in directly. <b>On Android
    <code>.local</code> is not reliable</b> — on iPhone and desktop it works
    fine</td></tr>
</table>
<div class="uy"><b>How many people can watch at once?</b> Connected
directly, the board serves up to <b>{d['akis_azami']} browsers</b>; each one
slows the measurement a little. The PC bridge takes <b>one</b> of these slots
when it is connected to the board over Wi-Fi, and none over USB. If you want
more viewers, use mode 3.</div>

<h2>3 · USB bridge — on the computer; the phone only watches</h2>
<p>The board connects to the computer <b>over USB</b>, and a small program runs
on the computer (<code>PC Baslat.bat</code> in the <code>kopru</code> folder).
That program both serves the interface and records the measurements. To stop
it, use <code>Kopruyu Durdur.bat</code> in the same folder. First pairing, the
recordings archive on the computer, notifications and troubleshooting:
<a href="9-pc-uygulamasi.html">PC app</a>.</p>
<table>
<tr><th>On the computer</th><td>Panel at <b><code>{d['kopru_adres']}</code></b>
    — the bridge listens only on this computer (<code>127.0.0.1</code>); no other
    device can connect to this address. Port {d['kopru_port']} is <b>fixed</b>:
    if another program holds it, the bridge doesn't start and says so (it
    doesn't fall back to another port — the panel's settings on this computer
    are tied to the address)</td></tr>
<tr><th>On the phone</th><td>If the bridge is started with <code>--lan</code>
    (<code>PC Baslat.bat --lan</code>), a phone on the same Wi-Fi can watch
    <b>read-only</b> at
    <code>http://&lt;computer's IP&gt;:{d['kopru_port']}</code>: it sees the
    measurement and can only send <b>STOP</b> (end the battery test). To give
    commands, the phone connects to the board directly (mode 1 or 2)</td></tr>
<tr><th>Board's Wi-Fi</th><td><b>On</b> by default. If you want full measurement
    speed, turn it off with <code>N0</code> from the serial console</td></tr>
<tr><th>Recording</th><td>Every measurement row is stored on the computer with a
    timestamp and can be exported as CSV later</td></tr>
</table>
<p>In this mode <b>the page the phone sees is served by the computer</b>, not
by the board. The phone and computer can be used at the same time and both see
the same data; commands only go from the panel on the computer.</p>

<h2>Opening it like an app on the phone</h2>
<p>Open the page in the browser and choose <b>Add to Home Screen</b>.</p>
<table>
<tr><th>iPhone</th><td>Opens with its own icon, <b>without the address
    bar</b> — no different from an app</td></tr>
<tr><th>Android</th><td>A shortcut is created, but it opens <b>in a Chrome
    tab</b>. Full-screen install needs HTTPS, and the board has no HTTPS. This
    is expected behaviour</td></tr>
</table>

<h2>Where does the interface live?</h2>
<p>The whole interface — the page, the Vue library, the stylesheets — is
<b>in the board's own memory</b>. No internet is needed and no file is
downloaded from outside.</p>
<table>
<tr><th>Interface size</th><td>{d['fs_icerik']/1024:.0f} KB</td></tr>
<tr><th>Space allocated</th><td>{d['fs_bolum']/1024:.0f} KB
    ({d['fs_icerik']/d['fs_bolum']*100:.0f}% full)</td></tr>
<tr><th>Live data</th><td>{d['sse_hz']:.0f} updates per second</td></tr>
</table>

<h2>Security — what it protects, what it doesn't</h2>
<p>The connection is <b>not encrypted</b> (no HTTPS). Someone on the same
network can see the measurements; that is an accepted limit for this
board.</p>
<table>
<tr><th>On every command</th><td>A <b>session key</b> and a custom header are
    required. This stops another web page from sending commands to the board in
    your name (CSRF)</td></tr>
<tr><th>Password</th><td><b>NOT SET by default.</b> Until one is set,
    <b>anyone on your network</b> can open the board's page and send dangerous
    commands. The board says so loudly at start-up</td></tr>
<tr><th>Setting the password</th><td>From the serial console:
    <code>Ns<i>password</i></code>. To remove it: <code>Ns</code> (empty).
    <code>N</code> shows the status</td></tr>
<tr><th>The board's own network</th><td>The AP password is generated by the
    board ({d['ap_parola_n']} characters) and printed to the USB console on
    first start</td></tr>
</table>
<div class="ok"><b>The one exception: stopping.</b> The command that stops a
battery discharge <b>always</b> works — it needs neither the session key nor
the password. Safety comes before convenience.</div>

<div class="uy">What the password protects against is <i>"someone else at home
pressing something by mistake"</i>. Without TLS it is <b>not</b> protection
against someone listening on the network.</div>
"""
    return sec(M(tr, en), dil)
