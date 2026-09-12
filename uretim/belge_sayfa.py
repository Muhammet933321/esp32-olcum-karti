# -*- coding: utf-8 -*-
"""BELGELER/*.html sayfalarinin govdeleri.

belge-uret.py bu modulu cagirir. Ayri dosya cunku belge-uret.py'de
sabitler + stil, burada icerik duruyor.
"""
from __future__ import annotations

import math

import belge_grafik as G


def sek(sayi, basamak=0):
    return f"{sayi:,.{basamak}f}".replace(",", " ")


# ═══════════════════════════════════════════════════════════ index

def index(d):
    return f"""
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
<tr><td><a href="2-malzemeler.html"><b>Malzemeler</b></a></td>
    <td>Gereken her parça, elinizde olan ve alınacak olanlar</td></tr>
<tr><td><a href="4-kurulum.html"><b>Kurulum</b></a></td>
    <td>Adım adım montaj kılavuzu</td></tr>
<tr><td><a href="sema.pdf"><b>Şema (PDF)</b></a></td>
    <td>Devrenin tam şeması</td></tr>
<tr><td><a href="5-muhendislik.html"><b>Mühendislik</b></a></td>
    <td>Nasıl çalıştığı, tasarım kararları, doğrulama — <span
        class="rozet">isteğe bağlı</span></td></tr>
</table>

<div class="uy"><b>Donanım henüz kurulmadı.</b> Bütün tasarım
bilgisayarda doğrulandı ({d['adim_sayisi']} adımlı bir zincir, binin
üzerinde otomatik denetim), ama kart fiziksel olarak hâlâ kurulmadı. Bu sayfalardaki
değerler <b>tasarımın vaadi</b>; tezgâhta ölçülecekler ayrı ayrı
işaretli.</div>
"""


# ═══════════════════════════════════════════════════ 1 · ne yapabilir

def ne_yapabilir(d, T, NORMAL, HV):
    nok = G.pil_egrisi(4.2, 3.0, 2.5, 4.7)
    return f"""
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
<figure>{G.menzil(T, NORMAL, HV, d['skop_adim'])}
<figcaption>Her çubuğun sol ucu <b>ayırt edebildiği en küçük değişim</b>,
sağ ucu <b>ölçebildiği en büyük değer</b>. Çubuk ne kadar uzunsa menzil o
kadar geniş.</figcaption></figure>

<h2>Osiloskop — dalga şeklini görmek</h2>
<p>Multimetreniz size bir <i>sayı</i> verir. Osiloskop <i>şekli</i>
gösterir: anahtarlama, çalma, tepe, gürültü. Aşağıda kartın 20 kHz'lik bir
anahtarlamalı güç kaynağını nasıl gördüğü var.</p>
<figure>{G.skop_ekrani(d['skop_bolme'], d['skop_azami'], d['skop_asgari'],
                       d['skop_adim'])}
<figcaption>Zaman tabanı 100 µs/bölme'den 500 ms/bölme'ye kadar
ayarlanabiliyor — yani hem mikrosaniyelik anahtarlamayı hem saniyelerce
süren bir olayı görebiliyorsunuz.</figcaption></figure>

<h2>Wattmetre — gerçek güç, işaretli</h2>
<p>Güç, gerilim ile akımın <b>her örnekte çarpımı</b>. Bu yüzden reaktif
yükte de doğru: akım gerilimden geri kalsa bile kart gerçek gücü buluyor.
İşaretli olması da önemli — <b>negatif güç</b> yükün geri besleme yaptığı
anlamına gelir.</p>
<figure>{G.canli_olcum()}
<figcaption>Reaktif bir yük: akım gerilimden 60° geride. Ortalama güç,
tepe değerlerin çarpımından çok daha küçük — kart bunu doğru
hesaplıyor.</figcaption></figure>

<h2>Pil kapasite testi</h2>
<p>Bir pilin gerçekte kaç mAh olduğunu ölçüyor. Kesme gerilimini siz
giriyorsunuz, kart pili boşaltıyor ve o gerilime inince <b>kendisi
kesiyor</b>.</p>
<figure>{G.pil_mah(nok)}
<figcaption>Örnek: 2500 mAh'lik bir 18650, 4.7 Ω taş dirençle boşaltılıyor.
Sonuç <b>{nok[-1][3]:.0f} mAh</b>. Ayrıntılar
<a href="3-pil-testi.html">pil testi sayfasında</a>.</figcaption></figure>

<h2>Hangi işi ne sıklıkta ölçüyor</h2>
<figure>{G.hizlar(d['hiz_kalem'])}
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


# ═══════════════════════════════════════════════════════ 2 · olcumler

def olcumler(d, T, NORMAL, HV):
    sont = ""
    for r in T.SONT_SECENEK:
        adc = T.ADS_AKIM_KIRPMA / r
        isil = T.SONT_AKIM_ISIL[r]
        m = min(adc, isil)
        a = (T.ADS_AKIM_KIRPMA / T.ADS_SAYIM) / r
        ad = f"{r:g} Ω" if r >= 1 else f"{r*1e3:.0f} mΩ"
        kim = "ADC" if adc < isil else "şöntün ısınması"
        sont += (f"<tr><td>{ad}</td><td class='s'>±{m:.3f} A</td>"
                 f"<td class='s'>{a*1e6:.1f} µA</td><td>{kim}</td></tr>")
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
    return f"""
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
<figure>{G.hizlar(d['hiz_kalem'])}
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


# ═══════════════════════════════════════════════════════ 3 · pil testi

def pil_testi(d, T):
    piller = [("18650 Li-ion (1 hücre)", 4.2, 3.0, 2.5),
              ("LiPo 2S", 8.4, 6.0, 2.2),
              ("LiPo 3S", 12.6, 9.0, 2.2),
              ("LiPo 6S", 25.2, 18.0, 2.2),
              ("12 V kurşun asit", 13.0, 10.5, 7.0),
              ("24 V akü", 29.0, 21.0, 7.0),
              ("9 V pil", 9.0, 6.0, 0.5),
              ("AA / AAA (NiMH)", 1.45, 0.9, 2.0)]
    sat = ""
    for ad, v0, vk, ah in piller:
        if v0 > d['pil_azami_v']:
            sat += (f"<tr><td>{ad}</td><td class='s'>{v0} V</td>"
                    f"<td colspan='3' style='color:var(--kotu)'>"
                    f"sınır dışı — {d['pil_azami_v']:.1f} V üstü</td></tr>")
            continue
        R = max(1.0, round(v0 / 0.9 / 0.5) * 0.5)
        i0 = v0 / R
        sure = ah / ((i0 + vk / R) / 2)
        sat += (f"<tr><td>{ad}</td><td class='s'>{v0} V</td>"
                f"<td class='s'>{vk} V</td>"
                f"<td class='s'>{R:.1f} Ω</td>"
                f"<td class='s'>{i0*1000:.0f} mA</td>"
                f"<td class='s'>{sure:.1f} sa</td></tr>")
    nok = G.pil_egrisi(4.2, 3.0, 2.5, 4.7)
    return f"""
<p>Bir pilin gerçekte kaç mAh olduğunu ölçer. Piyasadaki
<b>ZB2L3</b> gibi çalışır ama fazlası var: aynı anda <b>Wh</b>,
saniyede {sek(d['sps'])} örnek ve <b>iç direnç</b> ölçümü.</p>

<div class="kpi">
  <div><span>En yüksek pil gerilimi</span><b>{d['pil_azami_v']:.1f} V</b></div>
  <div><span>En yüksek akım</span><b>{d['pil_akim']:.2f} A</b></div>
  <div><span>Kapasite tavanı</span><b>{sek(d['mah_tavan']/1000)} Ah</b></div>
  <div><span>Kayıt</span><b>saniyede 1 nokta</b></div>
</div>

<h2>Nasıl kullanılır</h2>
<ol>
<li>Bir <b>taş direnç</b> (yük) alın — 18650 için 4.7–7.5 Ω / 10 W</li>
<li>Pilin (+) ucunu <b>V girişine</b>, direnç üzerinden (−) ucunu
    <b>J7</b>'ye bağlayın</li>
<li>Arayüzde <b>kesme gerilimini</b> girin (Li-ion 3.0 V)</li>
<li><b>Testi başlat</b>'a basın — gerisi kendiliğinden</li>
</ol>
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
<figure>{G.pil_zaman(nok)}
<figcaption>Gerilim ve akım, zamana göre. Taş direnç sabit değer olduğu
için pil çöktükçe akım da düşüyor ({nok[0][2]*1000:.0f} →
{nok[-1][2]*1000:.0f} mA) — bu normal.</figcaption></figure>

<figure>{G.pil_mah(nok)}
<figcaption>Asıl <b>deşarj eğrisi</b>: gerilim, çekilen kapasiteye göre.
Aynı pili tekrar test edip eğrileri üst üste koyarsanız yaşlanmayı
görürsünüz. Bu testte sonuç <b>{nok[-1][3]:.0f} mAh</b>.</figcaption></figure>

<figure>{G.pil_birikim(nok)}
<figcaption>Kapasite (mAh) ve enerji (Wh) ayrı ayrı birikiyor. İkisi
farklı şeyler: mAh pilin <i>yükünü</i>, Wh yaptığı <i>işi</i>
anlatır.</figcaption></figure>

<h2>İç direnç — ZB2L3'ün yapamadığı</h2>
<p>Kart 5 dakikada bir yükü {d['dcir_ms']:.0f} ms kesip gerilimin ne kadar
sıçradığına bakıyor. Bu, pilin <b>iç direncini</b> veriyor — ve iç direnç
pil sağlığının en iyi göstergesi.</p>
<figure>{G.pil_dcir(nok)}
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


# ═══════════════════════════════════════════════════════ 5 · muhendislik

def muhendislik(d, T, NORMAL, HV):
    return f"""
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


def ag(d, T):
    """Kartla nasil konusulur — uc kip, hangi adres, hangi sinirlar.

    Bu sayfa var olmadan once BELGELER/ icinde ag hakkinda TEK SATIR
    yoktu ve `index.html` "Bilgisayara USB ile baglaniyor" diyordu.
    """
    return f"""
<p>Kartın ekranı yok; <b>tarayıcıdan</b> kullanılıyor. Üç yolu var ve
üçü de aynı arayüzü gösteriyor — hangisini kullanacağınız
<b>bilgisayarın olup olmadığına</b> ve <b>ölçümün ne kadar hassas
olması gerektiğine</b> bağlı.</p>

<figure>{G.baglanti_modlari(d)}
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
    <td>Köprünün yazdığı adres, port {d['kopru_port']}</td></tr>
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
erişilemez kalmıyor</b>.</p>

<h3>Ev ağını karta bir kez tanıtmak</h3>
<p>Kartı USB ile bilgisayara takıp seri konsoldan (115200) üç komut:</p>
<table>
<tr><th><code>Na<i>AğAdı</i></code></th><td>Wi-Fi adı (SSID)</td></tr>
<tr><th><code>Np<i>parola</i></code></th><td>Wi-Fi parolası</td></tr>
<tr><th><code>N</code></th><td>Durumu yazdırır: kip, SSID, IP, mDNS</td></tr>
</table>
<p>Kaydedildikten sonra kartı yeniden başlatın. Ayarlar kartın kalıcı
belleğinde durur; bir daha girmeniz gerekmez.</p>

<table>
<tr><th>Adres</th><td><code>http://{d['mdns']}.local</code></td></tr>
<tr><th>Çalışmazsa</th><td>Kartın IP'si USB konsolunda (<code>N</code>
    komutu) yazıyor; doğrudan onu yazın. <b>Android'de
    <code>.local</code> güvenilir değildir</b> — iPhone ve masaüstünde
    sorunsuz çalışır</td></tr>
</table>
<div class="uy"><b>Aynı anda kaç kişi bakabilir?</b> Doğrudan karta
bağlanınca <b>{d['akis_azami']} tarayıcıya</b> kadar izleyebilir; her biri
ölçümü biraz yavaşlatır. <b>Köprü kayıtlıyken</b> kart doğrudan bağlanan
tarayıcıları <b>reddedip köprünün adresine yönlendiriyor</b> — o zaman
kartla konuşan tek şey köprü olur. İkiden çok izleyici istiyorsanız
3. kipi kullanın.</div>

<h2>3 · USB köprü — hem bilgisayar hem telefon</h2>
<p>Kart bilgisayara <b>USB ile</b> bağlanıyor, bilgisayarda küçük bir
program (<code>Kopru Baslat.bat</code>) çalışıyor. O program hem
arayüzü yayınlıyor hem ölçümleri kaydediyor.</p>
<table>
<tr><th>Bilgisayarda</th><td>Köprü açılırken <b>adresi ekrana
    yazıyor</b> — onu kullanın. Port {d['kopru_port']} başka bir program
    tarafından tutuluyorsa köprü sessizce
    {d['kopru_yedek']}'e düşer</td></tr>
<tr><th>Telefonda</th><td>Bilgisayarın adresi — aynı Wi-Fi'da olmak
    yeterli</td></tr>
<tr><th>Kartın Wi-Fi'si</th><td>Varsayılan <b>açık</b>. Ölçüme tam hız
    istiyorsanız seri konsoldan <code>N0</code> ile kapatın</td></tr>
<tr><th>Kayıt</th><td>Her ölçüm satırı zaman damgasıyla bilgisayarda
    saklanıyor, sonradan CSV olarak alınabiliyor</td></tr>
</table>
<p>Bu kipte <b>telefonun gördüğü sayfayı bilgisayar yayınlıyor</b>,
kart değil. Telefon ile bilgisayar aynı anda kullanılabilir ve ikisi
de aynı veriyi görür.</p>

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
