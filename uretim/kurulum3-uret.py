# -*- coding: utf-8 -*-
"""Asama 3 tezgah kurulum kilavuzunu uretir  ->  ../BELGELER/4-kurulum.html

    python kurulum3-uret.py

NEDEN URETILIYOR, ELLE YAZILMIYOR: sayfadaki her olcum degeri
`tasarim3_sabit.py`'den geliyor. Bolucu degisirse kilavuzdaki "sunu
olcmelisin" degeri de pesinden gidiyor. Asama 2'nin kurulum2.html'i elle
yazilmisti ve icindeki 4.7K pull-up onerisi tasarimla AYRISMISTI
(DEVIR 4.7); ayni hatayi tekrarlamamak icin bu uretiliyor.

Her adimin bir KAPISI var: gecmeden sonrakine gecilmez. Bu, projenin
dogrulama kulturunun tezgahtaki karsiligi — bir kapi tutmuyorsa hata O
adimdadir, sonraki adimi kurmak onu gizler, cozmez.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import tasarim3_sabit as T                        # noqa: E402
import belge_menu as MN                           # noqa: E402
import json                                       # noqa: E402
import dogrula3 as D3                             # noqa: E402
from belge_dil import DILLER, M, sec, cikis_yolu, dil_baglantisi  # noqa: E402


_FW = Path(__file__).parent / "_firmware.json"
if _FW.exists():
    _f = json.loads(_FW.read_text(encoding="utf-8"))
    _fb = f"{_f['flash_bayt']:,} B".replace(",", " ")
    FW = M(f"{_fb} (%{_f['flash_yuzde']})", f"{_fb} ({_f['flash_yuzde']}%)")
else:
    FW = M("olculmedi (dogrula3.py kosturun)", "not measured (run dogrula3.py)")


def semada_kac(deger: str) -> int:
    """Semada bu degerden kac adet var — netlist'ten SAYILIYOR.

    Elle yazilmis adet, semadan sessizce ayrisir: bu tablo bir sure
    'BAT85 x6' dedi, semada 4 vardi. Sayilar artik tek kaynaktan.
    """
    import re
    net = Path(__file__).parent / "netlist3.net"
    if not net.exists():
        raise SystemExit("netlist3.net yok — once sema3-uret.py + kicad-cli "
                         "netlist calistirilmali (zincirde B3, B9'dan once)")
    return sum(1 for _r, v in re.findall(
        r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\)',
        net.read_text(encoding="utf-8")) if v == deger)


BAT85_ADET = semada_kac("BAT85")
# DIP-8 govdeli entegreler: LM358 x2 (U3, U4) + TL072 x2 (U5, U8).
# TL431 TO-92, ADS1115'ler modul — soket almiyorlar.
DIP8_ADET = semada_kac("LM358") + semada_kac("TL072")

BURASI = Path(__file__).parent
KOK = BURASI.parent
HEDEF = KOK / "BELGELER" / "4-kurulum.html"

KN, KH = T.KANALLAR[0], T.KANALLAR[1]
HIZLI_KAZANC = 4.7
ESP_TAVAN = 3.1
salinim = min(ESP_TAVAN - T.VREF, T.VREF)


def e(x):
    return html.escape(str(x))


# ─────────────────────────────────────────────────────── adimlar
ADIMLAR = [
    dict(
        no="01",
        baslik=M("Vref rayı — her şey buna dayanıyor", "Vref rail — everything rests on it"),
        govde=M(f"""
<p>TL431 rayını ve ondan türeyen <b>Vref</b>'i kur. Çift yönlü ölçümün
tamamı Vref'e dayanıyor: bölücülerin alt ucu GND'ye değil buraya gidiyor.</p>
<pre>  +3V3 ──[ 220R ]──┬── TL431 katot ──┬── <span class="y">TL_RAY {T.TL431_V} V</span>
                   │       (U1)      │
                   │                 └──[100nF]── GND
                   └── TL431 REF (katoda bağlı)

  TL_RAY ──[ {T.VREF_RA/1e3:.0f}K ]──┬──[ {T.VREF_RB/1e3:.0f}K ]── GND
                     │
                  U3A izleyici ── <span class="y">VREF {T.VREF:.4f} V</span></pre>
<p><b>Vref TAMPONSUZ OLAMAZ.</b> İki bölücünün akımı (~290 µA) tamponsuz
bölücünün {T.par(T.VREF_RA, T.VREF_RB)/1e3:.1f} kΩ'luk Thevenin'inden aksa
2 V'a varan kayma yapardı.</p>
<p>U3 = LM358, <b>+5 V</b>'ta beslenecek. 3.3 V'ta çıkışı yeterince
yükselemez; +12 V'ta ise ADS'i zorlar.</p>
""", f"""
<p>Build the TL431 rail and the <b>Vref</b> derived from it. All
bidirectional measurement rests on Vref: the bottom ends of the dividers go
here, not to GND.</p>
<pre>  +3V3 ──[ 220R ]──┬── TL431 cath. ──┬── <span class="y">TL_RAY {T.TL431_V} V</span>
                   │       (U1)      │
                   │                 └──[100nF]── GND
                   └── TL431 REF (tied to cathode)

  TL_RAY ──[ {T.VREF_RA/1e3:.0f}K ]──┬──[ {T.VREF_RB/1e3:.0f}K ]── GND
                    │
                 U3A follower ── <span class="y">VREF {T.VREF:.4f} V</span></pre>
<p><b>Vref CANNOT BE UNBUFFERED.</b> The current of the two dividers
(~290 µA) flowing out of the {T.par(T.VREF_RA, T.VREF_RB)/1e3:.1f} kΩ
Thevenin resistance of an unbuffered divider would shift it by up to 2 V.</p>
<p>U3 = LM358, powered from <b>+5 V</b>. At 3.3 V its output cannot swing
high enough; at +12 V it would stress the ADS.</p>
"""),
        kapi=M(f"""TL431 katodunda <b>{T.TL431_V} V</b> ±%2, U3A çıkışında
<b>{T.VREF:.4f} V</b> ±10 mV ölç. Vref multimetreyle ölçülürken
<b>yük altında</b> (bölücüler bağlıyken) da aynı kalmalı — kaymıyorsa
tampon çalışıyor demektir.""", f"""Measure <b>{T.TL431_V} V</b> ±2% at the TL431 cathode and
<b>{T.VREF:.4f} V</b> ±10 mV at the U3A output. Vref must stay the same
when measured with the multimeter <b>under load</b> (dividers connected) —
if it doesn't shift, the buffer is working."""),
    ),
    dict(
        no="02",
        baslik=M("ESP32-S3 + I²C — iki ADS de görünmeli", "ESP32-S3 + I²C — both ADS must show up"),
        govde=M(f"""
<p>ADS1115 modüllerini <b>3.3 V</b>'ta besle (5 V'ta VIH 3.5 V olurdu ve
ESP32'nin 3.3 V çıkışı yetmezdi). Adresler:</p>
<table>
  <thead><tr><th>Modül</th><th>ADDR</th><th>Adres</th><th>Görev</th></tr></thead>
  <tbody>
    <tr><td>ADS #1 (U6)</td><td class="mono">GND</td><td class="mono">0x48</td><td>AKIM, AIN0-AIN1 diferansiyel</td></tr>
    <tr><td>ADS #2 (U7)</td><td class="mono">+3V3</td><td class="mono">0x49</td><td>GERİLİM, AIN0-1 ve AIN2-3</td></tr>
  </tbody>
</table>
<p><b>Pull-up: R24/R25 = 2.7K</b> — 4.7K DEĞİL. İki modülde 4.7K ile
yükselme süresi 308 ns çıkıyor ve Fast-mode sınırı 300 ns. 2.7K hem iki
hem üç modülde geçiyor (223 / 190 ns).</p>
<p>Modüllerin kendi 10K pull-up'ları var; 2.7K onlara <em>paralel</em> geliyor.</p>
""", """
<p>Power the ADS1115 modules from <b>3.3 V</b> (at 5 V, VIH would be 3.5 V
and the ESP32's 3.3 V outputs would not reach it). Addresses:</p>
<table>
  <thead><tr><th>Module</th><th>ADDR</th><th>Address</th><th>Role</th></tr></thead>
  <tbody>
    <tr><td>ADS #1 (U6)</td><td class="mono">GND</td><td class="mono">0x48</td><td>CURRENT, AIN0-AIN1 differential</td></tr>
    <tr><td>ADS #2 (U7)</td><td class="mono">+3V3</td><td class="mono">0x49</td><td>VOLTAGE, AIN0-1 and AIN2-3</td></tr>
  </tbody>
</table>
<p><b>Pull-ups: R24/R25 = 2.7K</b> — NOT 4.7K. With two modules, 4.7K gives
a rise time of 308 ns, and the Fast-mode limit is 300 ns. 2.7K passes with
both two and three modules (223 / 190 ns).</p>
<p>The modules have their own 10K pull-ups; the 2.7K ends up <em>in parallel</em> with them.</p>
"""),
        kapi=M("""Firmware'i yükle, seri portu 115200'de aç, <code>#</code> yaz.
<b>0x48 ve 0x49 ikisi de görünmeli.</b> Görünmüyorsa sorun kabloda:
SDA/SCL ters, ADDR boşta, ya da pull-up yok. Kalibrasyona geçme.""", """Flash the firmware, open the serial port at 115200 and type <code>#</code>.
<b>Both 0x48 and 0x49 must show up.</b> If not, the problem is in the wiring:
SDA/SCL swapped, ADDR floating, or no pull-ups. Don't move on to calibration."""),
    ),
    dict(
        no="03",
        baslik=M("Akım kanalı — şönt, Kelvin, çift yönlü", "Current channel — shunt, Kelvin, bidirectional"),
        govde=M(f"""
<p>Şöntü <b>soketli</b> tak. Kelvin (4 telli) algılama uçlarını şöntün
<em>kendi gövdesinden</em> al, akımın geçtiği izden değil.</p>
<p><b>Kelvin uçları İKİ yere gidiyor:</b> ADS'in koluna (R18/R19 100R,
sonra B15/F2'nin koruma dirençleri R38/R39 1K) ve hızlı yolun fark
yükseltecine (R27/R29). Hızlı yol R38/R39'un <em>önünden</em> çekiliyor.</p>
<p><b>B16 — süzgeç ADS'in KENDİ kolunda:</b> C4 artık
{T.SONT_C*1e9:.0f}nF (yalnızca RF). Örtüşme süzgeci
<b>C18 1µF + C19 220nF + C20 100nF = {T.ADS_AKIM_C*1e6:.2f} µF</b>
olarak <b>R38/R39'un ardına</b>, ADS'in giriş pinleri arasına konuyor —
bacaklar kısa, pinlere yakın. Süzgeç C4 düğümüne konsaydı hızlı yolun
bandı da kapanırdı (B16 öncesi tam bu oluyordu: I_HIZLI 7.8 kHz'te
kalıyor, skop kanalı 16.55 kHz'te duruyordu).</p>
<p><b>Neden bu değer:</b> gerilim kanalının zaman sabitiyle eşleşsin diye.
Eşleşmezse wattmetre <em>reaktif</em> yükte çöker — B16 öncesi 50 Hz'te
V/I faz farkı −41.6°, PF=0.5'te %155 hata. Dirençli yükte fark kendini
götürdüğü için gözden kaçmıştı.</p>
<p><b>Kondansatörlerin üzerindeki tolerans harfini oku (J = %5,
K = %10).</b> B16 bölüm 4: artık baskın hata kaynağı tolerans. %10'luk
parçalarla kartların %5'i PF=0.5'te %13'ten kötü olabiliyor — o yüzden
firmware'de menzil başına <b>faz kalibrasyonu</b> (dirençli yükle,
referans cihaz gerekmiyor) gerekli.</p>
<table>
  <thead><tr><th>Şönt</th><th>ADS menzili</th><th>Adım</th><th>Not</th></tr></thead>
  <tbody>
    <tr><td class="mono">10R</td><td>±26 mA</td><td>0.78 µA</td><td></td></tr>
    <tr><td class="mono">1R</td><td>±256 mA</td><td>7.81 µA</td><td></td></tr>
    <tr><td class="mono">0.1R</td><td>±2.56 A</td><td>78 µA</td><td></td></tr>
    <tr><td class="mono">15 mΩ</td><td>±11.5 A</td><td>521 µA</td><td><b>Kelvin şart</b></td></tr>
  </tbody>
</table>
""", f"""
<p>Fit the shunt <b>in a socket</b>. Take the Kelvin (4-wire) sense leads
from the <em>shunt body itself</em>, not from the trace carrying the current.</p>
<p><b>The Kelvin leads go to TWO places:</b> the ADS branch (R18/R19 100R,
then the B15/F2 protection resistors R38/R39 1K) and the fast path's
difference amplifier (R27/R29). The fast path is tapped <em>before</em> R38/R39.</p>
<p><b>B16 — the filter sits in the ADS's OWN branch:</b> C4 is now
{T.SONT_C*1e9:.0f}nF (RF only). The anti-aliasing filter
<b>C18 1µF + C19 220nF + C20 100nF = {T.ADS_AKIM_C*1e6:.2f} µF</b>
goes <b>after R38/R39</b>, across the ADS input pins — short legs, close
to the pins. Had the filter been placed at the C4 node, it would also have
closed the fast path's bandwidth (exactly what happened before B16: I_HIZLI
stopped at 7.8 kHz while the scope channel reached 16.55 kHz).</p>
<p><b>Why this value:</b> to match the time constant of the voltage channel.
Without the match the wattmeter breaks down on <em>reactive</em> loads — before
B16 the V/I phase difference at 50 Hz was −41.6°, a 155% error at PF=0.5. On
resistive loads the difference cancels out, which is why it went unnoticed.</p>
<p><b>Read the tolerance letter on the capacitors (J = 5%,
K = 10%).</b> B16 section 4: tolerance is now the dominant error source. With
10% parts, 5% of boards can be worse than 13% at PF=0.5 — hence the
firmware needs a per-range <b>phase calibration</b> (with a resistive load,
no reference instrument required).</p>
<table>
  <thead><tr><th>Shunt</th><th>ADS range</th><th>Step</th><th>Note</th></tr></thead>
  <tbody>
    <tr><td class="mono">10R</td><td>±26 mA</td><td>0.78 µA</td><td></td></tr>
    <tr><td class="mono">1R</td><td>±256 mA</td><td>7.81 µA</td><td></td></tr>
    <tr><td class="mono">0.1R</td><td>±2.56 A</td><td>78 µA</td><td></td></tr>
    <tr><td class="mono">15 mΩ</td><td>±11.5 A</td><td>521 µA</td><td><b>Kelvin required</b></td></tr>
  </tbody>
</table>
"""),
        kapi=M("""Yükü <b>tamamen kes</b>, <code>Z</code> yaz (akım sıfırı).
Sonra bilinen bir akım uygula ve <code>i&lt;amper&gt;</code> ile kalibre et.
<b>Akımı ters çevir</b> — okuma negatif olmalı. Sıfırda kalıyorsa
firmware kırpması geri gelmiş demektir.""", """<b>Disconnect the load completely</b> and type <code>Z</code> (current zero).
Then apply a known current and calibrate with <code>i&lt;amps&gt;</code>.
<b>Reverse the current</b> — the reading must go negative. If it sticks at
zero, the firmware clipping has come back."""),
    ),
    dict(
        no="04",
        baslik=M("NORMAL gerilim kanalı — ±32 V, çift yönlü", "NORMAL voltage channel — ±32 V, bidirectional"),
        govde=M(f"""
<pre>  V_GİRİŞ ──[ {KN['rust']/1e3:.0f}K ]──┬──[ {KN['ralt']/1e3:.1f}K ]── <span class="y">VREF</span>
                       │
                    [{T.RC_R/1e3:.0f}K]── C2 {T.RC_C*1e9:.0f}nF ── VREF
                       │
                  U3B izleyici ── ADS #2 AIN0     (AIN1 = VREF)</pre>
<table>
  <thead><tr><th></th><th>Değer</th></tr></thead>
  <tbody>
    <tr><td>Bölme oranı N</td><td class="mono">{KN['N']:.3f}</td></tr>
    <tr><td><b>Simetrik menzil</b></td><td class="mono deger">±{KN['fs_sim']:.2f} V</td></tr>
    <tr><td>Gerçek sınırlar</td><td class="mono">{KN['fs_alt']:.2f} .. {KN['fs_ust']:.2f} V</td></tr>
    <tr><td>Adım</td><td class="mono">{KN['adim']*1e3:.3f} mV</td></tr>
    <tr><td>Giriş empedansı</td><td class="mono">{KN['giris_z']/1e3:.0f} kΩ</td></tr>
  </tbody>
</table>
<p>⚠️ <b>Menzil simetrik değil.</b> <code>fark = (Vin − Vref)/N</code>
olduğu için ADS'in ±PGA penceresi girişe <b>Vref kadar yukarı kaymış</b>
bir aralık veriyor. Güvenle kullanılabilir aralık ±{KN['fs_sim']:.2f} V;
üstünde kırpar.</p>
""", f"""
<pre>  V_INPUT ──[ {KN['rust']/1e3:.0f}K ]──┬──[ {KN['ralt']/1e3:.1f}K ]── <span class="y">VREF</span>
                      │
                   [{T.RC_R/1e3:.0f}K]── C2 {T.RC_C*1e9:.0f}nF ── VREF
                      │
                 U3B follower ── ADS #2 AIN0     (AIN1 = VREF)</pre>
<table>
  <thead><tr><th></th><th>Value</th></tr></thead>
  <tbody>
    <tr><td>Division ratio N</td><td class="mono">{KN['N']:.3f}</td></tr>
    <tr><td><b>Symmetric range</b></td><td class="mono deger">±{KN['fs_sim']:.2f} V</td></tr>
    <tr><td>Actual limits</td><td class="mono">{KN['fs_alt']:.2f} .. {KN['fs_ust']:.2f} V</td></tr>
    <tr><td>Step</td><td class="mono">{KN['adim']*1e3:.3f} mV</td></tr>
    <tr><td>Input impedance</td><td class="mono">{KN['giris_z']/1e3:.0f} kΩ</td></tr>
  </tbody>
</table>
<p>⚠️ <b>The range is not symmetric.</b> Since <code>diff = (Vin − Vref)/N</code>,
the ADS's ±PGA window maps to an input range <b>shifted up by Vref</b>. The
safely usable range is ±{KN['fs_sim']:.2f} V; above that it clips.</p>
"""),
        kapi=M(f"""Girişi <b>0 V'a bağla</b> ve <code>z</code> yaz (gerilim
sıfırı — Vref'in gerçek değerini ölçüp çıkarır). Sonra bilinen bir gerilim
uygula, <code>g&lt;volt&gt;</code> ile kalibre et. <b>Sonra girişi ters
çevir</b> — okuma negatif ve aynı büyüklükte olmalı. +{KN['fs_sim']:.0f} V
ve −{KN['fs_sim']:.0f} V'ta kırpma olmamalı.""", f"""<b>Connect the input to 0 V</b> and type <code>z</code> (voltage
zero — it measures the actual Vref and subtracts it). Then apply a known
voltage and calibrate with <code>g&lt;volts&gt;</code>. <b>Then reverse the
input</b> — the reading must be negative with the same magnitude. There must
be no clipping at +{KN['fs_sim']:.0f} V and −{KN['fs_sim']:.0f} V."""),
    ),
    dict(
        no="05",
        baslik=M("YÜKSEK gerilim kanalı — ±613 V", "HIGH voltage channel — ±613 V"),
        tehlike=True,
        govde=M(f"""
<pre>  HV_GİRİŞ ──[ {KH['rust_adet']}× {KH['rust_bir']/1e3:.0f}K seri ]──┬──[ {KH['ralt']/1e3:.1f}K ]── <span class="y">VREF</span>
                                 │
                              [R17 {T.RC_R/1e3:.0f}K]── C3 {T.RC_C*1e9:.0f}nF ── VREF
                                 │
                            U4A izleyici ── ADS #2 AIN2   (AIN3 = VREF)</pre>
<p><b>Alt bacak {KH['ralt']/1e3:.1f}K, zincirin yüzde biri.</b> 6 × R /
(R/100) her R için bölme oranını tam 601 yapar; listede hem R hem R/100
bulunan en büyük çift 820K / 8.2K, giriş empedansı da orada en yüksek.</p>
<table>
  <thead><tr><th></th><th>Değer</th></tr></thead>
  <tbody>
    <tr><td>Bölme oranı N</td><td class="mono">{KH['N']:.1f}</td></tr>
    <tr><td><b>Simetrik menzil</b></td><td class="mono deger">±{KH['fs_sim']:.1f} V</td></tr>
    <tr><td>Adım</td><td class="mono">{KH['adim']*1e3:.2f} mV</td></tr>
    <tr><td>Giriş empedansı</td><td class="mono">{KH['giris_z']/1e6:.2f} MΩ</td></tr>
    <tr><td>Direnç başına (tam ölçekte)</td><td class="mono">{KH['r_gerilim']:.0f} V — sınırın %{KH['r_gerilim']/T.R_1_4W_AZAMI_V*100:.0f}'i</td></tr>
  </tbody>
</table>
<p><b>Neden {KH['rust_adet']} adet:</b> 1/4W metal filmin azami
<em>çalışma</em> gerilimi 200 V. 4 adetle hem direnç başına 154 V düşerdi
hem tam ölçek 410 V'ta kalırdı.</p>
<p><b>Neden 820K, 2.2M değil:</b> alt bacak zincirin yüzde biri olduğu
sürece oran <b>tam 601.0</b> kalıyor, yani 820K / 2.2M / 6.8M üçü de aynı
menzili ve aynı adımı verirdi. Ayıran tek şey <b>yüzey kaçağı</b>: delikli
plakette zincire paralel oluşan bir kaçak yolu bölme oranını aşağı çeker ve
hata doğrudan zincir direnciyle orantılıdır. 10 GΩ'luk bir kaçakta 820K
%0.049, 2.2M %0.132, 6.8M %0.408 hata yapar. Kaçak <b>kalibrasyonla
silinmez</b> — nemle günden güne değişir, tıpkı karbon filmi eleyen gerekçe
gibi. 2.2M'in kazandırdığı şey giriş empedansı (13.2 MΩ'a karşı 4.9 MΩ) ama
bu kanalın ölçeceği şeyler (doğrultulmuş şebeke, DC bara, SMPS çıkışı)
miliohm mertebesinde kaynaklar; orada fark ölçülemez.</p>
<p class="not"><b>Kartı temiz tut:</b> zincirin etrafındaki lehim pastası
kalıntısı ve parmak izi kaçak yolu demektir. Lehimledikten sonra izopropil
alkolle sil ve iyice kurut — bu bölücüde temizlik bir doğruluk parametresi.</p>
""", f"""
<pre>  HV_INPUT ──[ {KH['rust_adet']}× {KH['rust_bir']/1e3:.0f}K series ]──┬──[ {KH['ralt']/1e3:.1f}K ]── <span class="y">VREF</span>
                                 │
                              [R17 {T.RC_R/1e3:.0f}K]── C3 {T.RC_C*1e9:.0f}nF ── VREF
                                 │
                            U4A follower ── ADS #2 AIN2   (AIN3 = VREF)</pre>
<p><b>Bottom leg {KH['ralt']/1e3:.1f}K, one hundredth of the chain.</b> 6 × R /
(R/100) gives a division ratio of exactly 601 for any R; the largest pair
where both R and R/100 exist in the series is 820K / 8.2K, which also gives
the highest input impedance.</p>
<table>
  <thead><tr><th></th><th>Value</th></tr></thead>
  <tbody>
    <tr><td>Division ratio N</td><td class="mono">{KH['N']:.1f}</td></tr>
    <tr><td><b>Symmetric range</b></td><td class="mono deger">±{KH['fs_sim']:.1f} V</td></tr>
    <tr><td>Step</td><td class="mono">{KH['adim']*1e3:.2f} mV</td></tr>
    <tr><td>Input impedance</td><td class="mono">{KH['giris_z']/1e6:.2f} MΩ</td></tr>
    <tr><td>Per resistor (at full scale)</td><td class="mono">{KH['r_gerilim']:.0f} V — {KH['r_gerilim']/T.R_1_4W_AZAMI_V*100:.0f}% of the limit</td></tr>
  </tbody>
</table>
<p><b>Why {KH['rust_adet']} of them:</b> the maximum <em>working</em> voltage
of a 1/4 W metal film resistor is 200 V. With 4 of them, each resistor would
drop 154 V and full scale would stop at 410 V.</p>
<p><b>Why 820K and not 2.2M:</b> as long as the bottom leg is one hundredth
of the chain, the ratio stays <b>exactly 601.0</b>, so 820K / 2.2M / 6.8M
would all give the same range and the same step. The only difference is
<b>surface leakage</b>: on perfboard, a leakage path forming in parallel with
the chain pulls the division ratio down, and the error is directly
proportional to the chain resistance. With 10 GΩ of leakage, 820K gives a
0.049% error, 2.2M 0.132%, 6.8M 0.408%. Leakage <b>cannot be calibrated
out</b> — it changes from day to day with humidity, the same argument that
rules out carbon film. What 2.2M buys is input impedance (13.2 MΩ versus
4.9 MΩ), but what this channel measures (rectified mains, DC bus, SMPS
output) are sources in the milliohm range; there the difference is not
measurable.</p>
<p class="not"><b>Keep the board clean:</b> solder paste residue and
fingerprints around the chain are leakage paths. After soldering, wipe with
isopropyl alcohol and let it dry thoroughly — on this divider cleanliness is
an accuracy parameter.</p>
"""),
        kapi=M(f"""<b>ÖNCE DÜŞÜK GERİLİMLE.</b> 12 V uygula ve okumayı kontrol
et — {KH['adim']*1e3:.1f} mV adımla 12 V ≈ {12/KH['adim']:.0f} kod, gürültü
içinde kaybolmaz. Sonra 100 V, sonra kademeli olarak yukarı.
Her adımda <b>eller uzakta</b>, tek elle çalış.""", f"""<b>LOW VOLTAGE FIRST.</b> Apply 12 V and check the reading —
with a {KH['adim']*1e3:.1f} mV step, 12 V ≈ {12/KH['adim']:.0f} codes, it won't
get lost in the noise. Then 100 V, then step up gradually.
At every step <b>hands away</b>, work one-handed."""),
    ),
    dict(
        no="06",
        baslik=M("Osiloskop kanalı + Sallen-Key", "Oscilloscope channel + Sallen-Key"),
        govde=M(f"""
<p>Ayrı giriş, ayrı bölücü (100K/{T.SKOP_RALT/1e3:.1f}K, oran
{T.SKOP_N:.3f}) — gerilim kanallarıyla <b>aynı düğüm değil</b>.</p>
<p><b>B19 — kanal ÇİFT YÖNLÜ.</b> R23'ün alt ucu <b>GND'ye değil VREF'e</b>
gidiyor (gerilim kanallarının zaten kullandığı çözüm). Sıfır giriş =
VREF, eksi giriş aşağı, artı giriş yukarı. Menzil
<span class="deger">{T.SKOP_MENZIL_EKSI:.1f} … +{T.SKOP_MENZIL_ARTI:.1f} V</span>,
adım {T.SKOP_ADIM*1e3:.1f} mV. Öncesi 0…45.5 V tek yönlüydü, adım
{T.SKOP_ADIM_ESKI*1e3:.1f} mV —
<b>bedeli çözünürlük</b>.</p>
<p>⚠️ <b>R23'ü GND'ye lehimleme.</b> Şemada VREF'e gidiyor; GND'ye
takılırsa kanal sessizce tek yönlü kalır ve okumalar
{T.SKOP_VOLT_OFSET:.0f} V kayar.</p>
<p><b>Sallen-Key örtüşme süzgeci</b> (U5A): R21/R22 = {T.SK_R/1e3:.1f}K,
C5 = {T.SK_C1*1e9:.0f}nF (2× 1nF paralel), C6 = {T.SK_C2*1e9:.0f}nF →
f0 = <span class="deger">{T.SK_F0/1e3:.2f} kHz</span>, Q = {T.SK_Q:.4f}.</p>
<p>🔴 <b>B20 düzeltmesi:</b> bu satır eskiden <b>R22/R23</b> ve <b>C7</b>
diyordu; ikisi de yanlıştı ve <b>montaj tuzağıydı</b>. Netlistten
doğrulanan gerçek: <b>R23 bölücünün alt bacağıdır</b> (2.7K, VREF'e —
yukarıdaki uyarının konusu), Sallen-Key'in direnci <b>R21</b>'dir; <b>C7
ise U5B'ye</b> (hızlı akım Sallen-Key'i) aittir, U5A'nınki <b>C5</b>.
R23'e {T.SK_R/1e3:.1f}K takmak skop kanalını hem tek yönlü bırakır hem
ölçeğini bozardı.</p>
<p>Eski tasarımdaki tek kutuplu RC 25 kHz'teydi — kanal başına Nyquist
{T.ESP_NYQUIST/1e3:.2f} kHz olduğu için <b>Nyquist'in üstünde</b>, yani
hiçbir şey süzmüyordu. 100 kHz'lik bir SMPS dalgalanması hiç zayıflamadan
16.7 kHz'e katlanıp <em>gerçekmiş gibi</em> görünürdü.</p>
<p><b>Koruma:</b> {T.R_SERI/1e3:.0f}K seri + 2× BAT85 (D1 üste +3V3'e,
D2 altta GND'ye). <b>1N4148 OLMAZ</b> — SPICE ölçtü: arıza akımının
%25'i ADS'in iç ESD diyoduna gidiyor. BAT85 ile pin −0.268 V'ta kalıyor.</p>
<p><b>B18/F12 — seri direnç {T.R_SERI_ESKI/1e3:.1f}K değil {T.R_SERI/1e3:.0f}K.</b>
Bu direnç, kart <em>beslemesizken</em> (USB çıkık ama 24 V takılı) ölü
+3V3 rayına geri beslenen akımı belirliyor. 2.7K'da ray 3.582 V'a
çıkıyordu — ESP32 besleme pini sınırı 3.60 V, <b>pay 18 mV</b>.
10K + <b>R41 (1K boşaltma direnci)</b> ile ray 1.67 V'ta kalıyor.
Menzillerde hiçbir kayıp yok; ADC tarafındaki bedel sızıntı 0.5 mV
(&lt;1 LSB), oturma 330 ns (örnek aralığının 1/73'ü).</p>
<p><b>R41'i unutma:</b> +3V3 ile GND arasına 1K. Küçük görünür ama
kartın beslemesiz haldeki tek koruması odur — ve TL431'e bağlı değildir.</p>
""", f"""
<p>Separate input, separate divider (100K/{T.SKOP_RALT/1e3:.1f}K, ratio
{T.SKOP_N:.3f}) — <b>not the same node</b> as the voltage channels.</p>
<p><b>B19 — the channel is BIDIRECTIONAL.</b> The bottom end of R23 goes
<b>to VREF, not GND</b> (the solution the voltage channels already use).
Zero input = VREF, negative input goes down, positive input goes up. Range
<span class="deger">{T.SKOP_MENZIL_EKSI:.1f} … +{T.SKOP_MENZIL_ARTI:.1f} V</span>,
step {T.SKOP_ADIM*1e3:.1f} mV. Before, it was unidirectional 0…45.5 V with a
{T.SKOP_ADIM_ESKI*1e3:.1f} mV step —
<b>the price is resolution</b>.</p>
<p>⚠️ <b>Don't solder R23 to GND.</b> In the schematic it goes to VREF; fitted
to GND, the channel silently stays unidirectional and readings shift by
{T.SKOP_VOLT_OFSET:.0f} V.</p>
<p><b>Sallen-Key anti-aliasing filter</b> (U5A): R21/R22 = {T.SK_R/1e3:.1f}K,
C5 = {T.SK_C1*1e9:.0f}nF (2× 1nF in parallel), C6 = {T.SK_C2*1e9:.0f}nF →
f0 = <span class="deger">{T.SK_F0/1e3:.2f} kHz</span>, Q = {T.SK_Q:.4f}.</p>
<p>🔴 <b>B20 correction:</b> this line used to say <b>R22/R23</b> and <b>C7</b>;
both were wrong and an <b>assembly trap</b>. The truth, verified against the
netlist: <b>R23 is the bottom leg of the divider</b> (2.7K, to VREF — the
subject of the warning above), the Sallen-Key resistor is <b>R21</b>; <b>C7
belongs to U5B</b> (the fast current Sallen-Key), U5A's is <b>C5</b>.
Fitting {T.SK_R/1e3:.1f}K at R23 would both leave the scope channel
unidirectional and break its scaling.</p>
<p>The single-pole RC in the old design sat at 25 kHz — with a per-channel
Nyquist of {T.ESP_NYQUIST/1e3:.2f} kHz that is <b>above Nyquist</b>, so it
filtered nothing. A 100 kHz SMPS ripple would fold down to 16.7 kHz
completely unattenuated and look <em>real</em>.</p>
<p><b>Protection:</b> {T.R_SERI/1e3:.0f}K series + 2× BAT85 (D1 on top to +3V3,
D2 below to GND). <b>NO 1N4148</b> — SPICE measured it: 25% of the fault
current goes into the ADS's internal ESD diode. With BAT85 the pin stays at −0.268 V.</p>
<p><b>B18/F12 — the series resistor is {T.R_SERI/1e3:.0f}K, not {T.R_SERI_ESKI/1e3:.1f}K.</b>
This resistor sets the current fed back into the dead +3V3 rail while the
board is <em>unpowered</em> (USB unplugged but 24 V connected). With 2.7K the
rail rose to 3.582 V — the ESP32 supply pin limit is 3.60 V, <b>a margin of
18 mV</b>. With 10K + <b>R41 (1K bleeder resistor)</b> the rail stays at
1.67 V. No loss in any range; the cost on the ADC side is 0.5 mV of leakage
(&lt;1 LSB) and 330 ns of settling (1/73 of the sample interval).</p>
<p><b>Don't forget R41:</b> 1K between +3V3 and GND. It looks minor, but it is
the board's only protection while unpowered — and it is not tied to the TL431.</p>
"""),
        kapi=M("""Bilinen bir kare dalga uygula (NE555 ya da ESP32'nin kendi
PWM'i). <code>ta</code> yaz (otomatik kurulum) — frekans ve duty doğru
çıkmalı. Düz çizgide ölçüm <b>yapılamamalı</b> (frekans 0).""", """Apply a known square wave (an NE555 or the ESP32's own
PWM). Type <code>ta</code> (auto setup) — frequency and duty must come out
right. On a flat line a measurement <b>must not be possible</b> (frequency 0)."""),
    ),
    dict(
        no="07",
        baslik=M("Hızlı akım yolu — gerçek güç ve PF", "Fast current path — real power and PF"),
        govde=M(f"""
<pre>  SONT_P ──[10K]──┬── U8A(+)      <span class="y">fark yükselteci, G = {HIZLI_KAZANC}</span>
                  └──[47K]── VREF   (REF ucu VREF'te → çift yönlü)
  SONT_N ──[10K]──┬── U8A(−)
                  └──[47K]── çıkış
  çıkış ── U5B Sallen-Key {T.SK_F0/1e3:.2f} kHz ── {T.R_SERI/1e3:.1f}K ── 2× BAT85 ── GPIO5</pre>
<p>Kazanç <b>{HIZLI_KAZANC}</b> (47K/10K): tam ölçek şönt gerilimi
{salinim/HIZLI_KAZANC*1e3:.1f} mV, yani ADS'in 256 mV'undan geniş —
<b>önce ADS kırpar</b>, hızlı yol değil.</p>
<p>U5B Aşama 3'e kadar boşta duruyordu; artık hızlı akım Sallen-Key'i.</p>
""", f"""
<pre>  SONT_P ──[10K]──┬── U8A(+)      <span class="y">difference amp, G = {HIZLI_KAZANC}</span>
                  └──[47K]── VREF   (REF at VREF → bidirectional)
  SONT_N ──[10K]──┬── U8A(−)
                  └──[47K]── out
  out ── U5B Sallen-Key {T.SK_F0/1e3:.2f} kHz ── {T.R_SERI/1e3:.1f}K ── 2× BAT85 ── GPIO5</pre>
<p>Gain <b>{HIZLI_KAZANC}</b> (47K/10K): the full-scale shunt voltage is
{salinim/HIZLI_KAZANC*1e3:.1f} mV, i.e. wider than the ADS's 256 mV —
<b>the ADS clips first</b>, not the fast path.</p>
<p>U5B sat unused until Stage 3; it is now the fast current Sallen-Key.</p>
"""),
        kapi=M(f"""Dirençsel bir yük bağla, <code>w</code> yaz.
<b>PF ≈ 1.00</b> çıkmalı ve arayüz "hizalama farkı yok (dirençsel)"
demeli. Sonra bir kondansatör/bobin ekle — PF düşmeli ve arayüz
hizalamanın kaç yüzde düzelttiğini göstermeli.
<br><br>⚠️ Çıktıdaki <b>pencere</b> satırına bak: 50 Hz'te 1 çevrimin
altındaysa yanlılık büyük. Bu sayı <em>mutlak watt</em> için değil,
<b>güç faktörü ve dalga şekli</b> için.""", """Connect a resistive load and type <code>w</code>.
<b>PF ≈ 1.00</b> must come out and the interface must say "no alignment
difference (resistive)". Then add a capacitor/inductor — PF must drop and
the interface must show by how many percent the alignment corrected it.
<br><br>⚠️ Look at the <b>window</b> line in the output: below 1 cycle at
50 Hz the bias is large. This number is not for <em>absolute watts</em>, it
is for <b>power factor and waveform</b>."""),
    ),
]


def adim_html(a, dil="tr"):
    tehlike = a.get("tehlike")
    kutu = "tehlike" if tehlike else "kanit"
    baslik = sec(M("TEHLİKE", "DANGER") if tehlike else
                 M("KAPI — geçmeden ilerleme", "GATE — don't proceed until it passes"), dil)
    return f"""
<section>
  <div class="adim-basi"><span class="adim-no">{a['no']}</span><h2>{e(sec(a['baslik'], dil))}</h2></div>
  {sec(a['govde'], dil)}
  <div class="{kutu}">
    <div class="kanit-baslik">{baslik}</div>
    <p>{sec(a['kapi'], dil)}</p>
  </div>
</section>
<hr>
"""


# ⚠ GUNCEL KILAVUZ, ARSIVDEN BESLENIYOR. Bicim Asama 2'nin kurulum
#   sayfasindan aliniyor — yani `arsiv/` "eski asamalar" degil, bu
#   uretecin CANLI bagimliligi. B23.3'te mutasyon kopyasi `arsiv/`'i
#   disladigi icin B9 kirmizi dondu ve bagimlilik boyle gorunur oldu.
#   Tasinmadi: bicim calisiyor ve kopyalamak yeni bir ayrisma yuzeyi
#   acardi. Arsivi tasirken ya da silerken BURAYA BAK.
_BICIM_KAYNAGI = KOK / "arsiv" / "asama2" / "kurulum2.html"
if not _BICIM_KAYNAGI.exists():
    raise SystemExit(
        f"kurulum3-uret.py: bicim kaynagi yok -> {_BICIM_KAYNAGI}\n"
        f"  Guncel kurulum kilavuzunun CSS'i ARSIVDEN geliyor; arsiv "
        f"tasindiysa bu yolu guncelle.")
# Emniyet uyarisinin sayilari da kaynaktan (B15/D2 ile AYNI hesap).
import math as _math
creepage = T.IEC60664_CREEPAGE_TAKVIYELI
# B48: bakirdan bakira — merkez araligindan ped capi dusuluyor
n_delik = _math.ceil((creepage + T.DELIKLI_PAD_ETKIN_MM) / T.DELIKLI_ADIM)
mesafe = n_delik * T.DELIKLI_ADIM - T.DELIKLI_PAD_ETKIN_MM

CSS = _BICIM_KAYNAGI.read_text(encoding="utf-8")
CSS = CSS[CSS.index("<style>"):CSS.index("</style>") + 8]

def sayfa_uret(dil):
    """4-kurulum.html'in `dil` dilindeki tam metni. Sayilar iki dilde de
    ayni degiskenlerden geliyor; ceviri yalnizca metni degistiriyor."""
    serit = MN.serit("4-kurulum.html", gomulu=True, dil=dil)
    serit = serit[:-len("</nav>")] + dil_baglantisi("4-kurulum.html", dil) + "</nav>"
    fw = sec(FW, dil)
    baslik = sec(M("Aşama 3 Tezgâh Kurulumu", "Stage 3 Bench Assembly"), dil)
    ust = sec(M(f"""<header>
  <div class="ust-etiket">Ölçüm Kartı · Aşama 3 · ÇİFT YÖNLÜ ön uç</div>
  <h1>Aşama 3 Tezgâh Kurulumu</h1>
  <p class="ozet">Yedi adım, her birinin sonunda geçilmeden ilerlenmeyen bir
     ölçüm kapısı. Bir kapı tutmuyorsa hata o adımdadır — sonraki adımı
     kurmak onu gizler, çözmez.</p>
  <div class="kunye">
    <span>Doğrulama <b>{D3.ADIM_SAYISI} adımlık zincir</b></span>
    <span>ERC <b>0 ihlal</b></span>
    <span>Firmware <b>{fw}</b></span>
    <span>Menzil <b>±{KN['fs_sim']:.1f} V · ±{KH['fs_sim']:.0f} V · ±11.5 A</b></span>
  </div>
</header>""", f"""<header>
  <div class="ust-etiket">Measurement Board · Stage 3 · BIDIRECTIONAL front end</div>
  <h1>Stage 3 Bench Assembly</h1>
  <p class="ozet">Seven steps, each ending in a measurement GATE you don't
     pass until it holds. If a GATE doesn't hold, the fault is in that
     step — building the next step hides it, it doesn't fix it.</p>
  <div class="kunye">
    <span>Verification <b>{D3.ADIM_SAYISI}-step chain</b></span>
    <span>ERC <b>0 violations</b></span>
    <span>Firmware <b>{fw}</b></span>
    <span>Range <b>±{KN['fs_sim']:.1f} V · ±{KH['fs_sim']:.0f} V · ±11.5 A</b></span>
  </div>
</header>"""), dil)
    bolum00 = sec(M(f"""<section>
  <div class="adim-basi"><span class="adim-no">00</span><h2>Önce bunlar</h2></div>

  <div class="tehlike">
    <div class="uyari-baslik">615 V öldürür — ve bu kart izole DEĞİL</div>
    <p>Kart USB üzerinden bilgisayarına bağlı. Şebeke referanslı bir devreye
       (izole olmayan SMPS'in birincil tarafı gibi) bağlarsan
       <b>bilgisayarına şebeke gerilimi taşırsın</b>. Yalnız izole ikincil
       taraf, ya da tamamen izole çalışma (pil + WiFi, USB takılı değil).</p>
    <p><b>Ama yüzdürmek yetmez.</b> Arıza analizi (B15/D2) bunu ölçtü:
       pille yüzdürmek <b>bilgisayarı kurtarır, SENİ KURTARMAZ</b> — kart
       o anda şebeke potansiyeline çıkar ve kartın <b>her noktası</b>
       tehlikelidir. 615 V, yüzen alet sınırının <b>14.6 katı</b>.
       Bu yüzden şebeke referanslı ölçümde:</p>
    <ul>
      <li><b>Yalıtımlı kutu ŞART</b> — kartın hiçbir noktasına elle
          erişilememeli, prob uçları dahil</li>
      <li>Delikli plakette takviyeli yalıtım için <b>{n_delik} delik
          atla</b> ({mesafe:.2f} mm <b>bakırdan bakıra</b> — ped çapı
          düşülmüş; IEC 60664 creepage {creepage:.1f} mm). Yerleşim planı:
          <a href="7-yerlesim.html">Yerleşim</a></li>
      <li>Enerji verilmişken karta <b>dokunma</b>; ölçüm bitince önce
          devreyi kes, sonra probu al</li>
    </ul>
    <p>Yüksek gerilim ucunu ölçüm ucundan <b>fiziksel olarak ayrı</b> tut,
       farklı renk kullan, tek elle çalış.</p>
  </div>

  <div class="uyari">
    <div class="uyari-baslik">Delikli plakette 615 V — delik adımı yetmez</div>
    <p>Delik adımı 2.54 mm. 6 adetlik HV zincirini <b>delik atlayarak</b>,
       aralarında boşluk bırakarak koy; tercihen doğrudan muz jakın üstünde
       havada kur. Bu, lehim becerisinden bağımsız ayrı bir dikkat konusu.</p>
  </div>

  <h3>Satın alınacak</h3>
  <div class="uyari">
    <div class="uyari-baslik">Dirençler METAL FİLM olmalı — karbon film tasarımı anlamsız kılıyor</div>
    <p>601:1'lik bölücüde direncin <b>tipi</b>, değerinden daha belirleyici.
       20 °C oda salınımı ve direnç başına 102 V ile toplam hata:
       karbon film <b>%4.10</b>, metal film %1/50 ppm <b>%0.41</b>.
       Kıyas: ADS kalibrasyon sonrası %0.03, referans multimetre %0.5.</p>
    <p>İki kalem <b>kalibrasyonla silinmez</b>: VCR gerilime bağlı olduğu
       için doğrusal değil (12 V'ta kalibre edip 600 V ölçersen hata geri
       gelir), ve karbon filmin %1–3'lük 1000 saatlik sürüklenmesi
       <b>kalibrasyonu haftalar içinde bayatlatır</b> — sayı hâlâ
       inandırıcı görünürken.</p>
    <p>Ayırt etme: metal film genelde <b>mavi/yeşil gövde, 5 halka</b> (%1);
       karbon film <b>bej, 4 halka</b> (%5).</p>
  </div>
  <p><b>Güncel alışveriş listesi <a href="2-malzemeler.html">Malzemeler</a>
     sayfasında</b> — şemadan ve envanterden üretiliyor, burada ikinci bir
     kopya tutulmuyor. (Bu tabloda önceden elle yazılı BAT85 / 820K / 8.2K /
     DIP-8 soket / silikon kablo kalemleri vardı; hepsi 11 Eylül'de geldi ve
     tablo üç gün "alınacak" demeye devam etti — B48'de kaldırıldı.)</p>
  <table>
    <thead><tr><th>Parça</th><th>Adet</th><th>Neden</th></tr></thead>
    <tbody>
      <tr><td class="mono">BAT85</td><td>{BAT85_ADET}</td><td>Kelepçe (skop yolu 2, hızlı akım yolu 2). 1N4148 <b>olmaz</b>: arıza akımının %25'ini ADS'in iç ESD diyoduna bırakıyor. Stoktaki 1N4148'ler Aşama 1/2 kartları için</td></tr>
      <tr><td class="mono">DIP-8 IC soketi</td><td>{DIP8_ADET}</td><td>LM358 ×2, TL072 ×2. TL431 TO-92, ADS1115'ler modül — onlar soket almaz. Zorunlu değil ama delikli plakette 8 bacaklı bir DIP'i sökmek eziyet; ayrıca lehim ısısı op-amp'e hiç gitmez</td></tr>
      <tr><td>Yedek ESP32-S3</td><td>1</td><td><i>önerilen</i> — 615 V ile çalışılacak, elde tek kart var. Tek gerçek "alınsa iyi olur" kalemi</td></tr>
    </tbody>
  </table>
  <p><b>10K dikkat:</b> karbon film R019 tükenmiş; bu kartta zaten metal film
     R060 kullanılacak. 220R ve 100R metal film olmak zorunda değil — onlar
     oranı kurmuyor (TL431 ön gerilimi ve şönt RC'si).</p>

  <h3>Gereken aletler</h3>
  <ul>
    <li>Multimetre — kalibrasyonun referansı bu, kartın <em>mutlak</em>
        doğruluğu bunu aşamaz</li>
    <li>Ayarlanabilir güç kaynağı (12 V adaptör başlangıç için yeter)</li>
    <li>±12 V rayı — TL072'ler (U5, U8) buna bağlı. Tek besleme olmaz:
        çıkışları 0.69 V'a inemez.</li>
    <li>+5 V — LM358'ler (U3, U4) buna bağlı</li>
  </ul>

  <h3>Ayırma kondansatörleri — atlanmaz</h3>
  <p>Her op-amp besleme ucuna <b>yerel 100nF</b>: C9 (U3, +5V), C10 (U4, +5V),
     C11/C12 (U5, ±12V), C13/C14 (U8, ±12V), C15 (ADS rayı). Yedisi de stokta.</p>
  <p>Op-amp çıkışı kapasitif yük sürüyor (Sallen-Key'in C'leri); besleme
     empedansı yüksekse bu <b>salınıma</b> dönüşür. TL072'nin slew hızı
     13 V/µs — ani akım talebini yerel kondansatör karşılamalı, 20 cm'lik
     besleme teli değil.</p>
</section>
<hr>
""", f"""<section>
  <div class="adim-basi"><span class="adim-no">00</span><h2>Read this first</h2></div>

  <div class="tehlike">
    <div class="uyari-baslik">615 V kills — and this board is NOT isolated</div>
    <p>The board is connected to your computer over USB. If you connect it to
       a mains-referenced circuit (such as the primary side of a non-isolated
       SMPS) <b>you carry mains voltage into your computer</b>. Only the
       isolated secondary side, or fully isolated operation (battery + WiFi,
       USB unplugged).</p>
    <p><b>But floating it is not enough.</b> The fault analysis (B15/D2)
       measured it: floating on battery <b>saves the computer, it does NOT SAVE
       YOU</b> — the board rises to mains potential at that moment and
       <b>every point</b> on it is dangerous. 615 V is <b>14.6 times</b> the
       limit for a floating instrument. So for mains-referenced measurements:</p>
    <ul>
      <li><b>An insulated enclosure is MANDATORY</b> — no point of the board may
          be reachable by hand, probe tips included</li>
      <li>For reinforced insulation on perfboard, <b>skip {n_delik}
          holes</b> ({mesafe:.2f} mm <b>copper to copper</b> — pad diameter
          subtracted; IEC 60664 creepage {creepage:.1f} mm). Layout plan:
          <a href="7-yerlesim.html">Layout</a></li>
      <li><b>Don't touch</b> the board while it is energized; when the
          measurement is done, first disconnect the circuit, then remove the probe</li>
    </ul>
    <p>Keep the high-voltage lead <b>physically separate</b> from the measurement
       lead, use a different color, work one-handed.</p>
  </div>

  <div class="uyari">
    <div class="uyari-baslik">615 V on perfboard — the hole pitch is not enough</div>
    <p>The hole pitch is 2.54 mm. Place the 6-resistor HV chain <b>skipping
       holes</b>, with gaps between them; preferably build it in the air
       directly on the banana jack. This is a separate point of care,
       independent of soldering skill.</p>
  </div>

  <h3>To buy</h3>
  <div class="uyari">
    <div class="uyari-baslik">Resistors must be METAL FILM — carbon film makes the design pointless</div>
    <p>In a 601:1 divider the resistor <b>type</b> matters more than its value.
       Total error with a 20 °C room swing and 102 V per resistor:
       carbon film <b>4.10%</b>, metal film 1%/50 ppm <b>0.41%</b>.
       For comparison: ADS after calibration 0.03%, reference multimeter 0.5%.</p>
    <p>Two terms <b>cannot be calibrated out</b>: VCR depends on voltage, so it
       is not linear (calibrate at 12 V and measure 600 V and the error comes
       back), and carbon film's 1–3% drift over 1000 hours <b>makes the
       calibration stale within weeks</b> — while the number still looks
       convincing.</p>
    <p>Telling them apart: metal film is usually a <b>blue/green body, 5 bands</b> (1%);
       carbon film is <b>beige, 4 bands</b> (5%).</p>
  </div>
  <p><b>The current shopping list is on the <a href="2-malzemeler.html">Parts</a>
     page</b> — generated from the schematic and the inventory; no second copy
     is kept here. (This table used to list BAT85 / 820K / 8.2K / DIP-8
     socket / silicone wire by hand; all of them arrived on 11 September and
     the table kept saying "to buy" for three days — removed in B48.)</p>
  <table>
    <thead><tr><th>Part</th><th>Qty</th><th>Why</th></tr></thead>
    <tbody>
      <tr><td class="mono">BAT85</td><td>{BAT85_ADET}</td><td>Clamps (scope path 2, fast current path 2). 1N4148 <b>won't do</b>: it leaves 25% of the fault current to the ADS's internal ESD diode. The 1N4148s in stock are for the Stage 1/2 boards</td></tr>
      <tr><td class="mono">DIP-8 IC socket</td><td>{DIP8_ADET}</td><td>LM358 ×2, TL072 ×2. The TL431 is TO-92 and the ADS1115s are modules — they take no socket. Not mandatory, but desoldering an 8-pin DIP from perfboard is a pain; and soldering heat never reaches the op-amp</td></tr>
      <tr><td>Spare ESP32-S3</td><td>1</td><td><i>recommended</i> — you'll be working with 615 V and there is only one board on hand. The only real "nice to have" item</td></tr>
    </tbody>
  </table>
  <p><b>Note on 10K:</b> the carbon film R019 is out of stock; this board uses the
     metal film R060 anyway. The 220R and 100R don't have to be metal film — they
     don't set a ratio (TL431 bias and the shunt RC).</p>

  <h3>Tools needed</h3>
  <ul>
    <li>Multimeter — it is the calibration reference; the board's <em>absolute</em>
        accuracy cannot exceed it</li>
    <li>Adjustable power supply (a 12 V adapter is enough to start with)</li>
    <li>±12 V rail — the TL072s (U5, U8) run from it. A single supply won't do:
        their outputs cannot get down to 0.69 V.</li>
    <li>+5 V — the LM358s (U3, U4) run from it</li>
  </ul>

  <h3>Decoupling capacitors — not optional</h3>
  <p>A <b>local 100nF</b> on every op-amp supply pin: C9 (U3, +5V), C10 (U4, +5V),
     C11/C12 (U5, ±12V), C13/C14 (U8, ±12V), C15 (ADS rail). All seven are in stock.</p>
  <p>The op-amp outputs drive a capacitive load (the Sallen-Key capacitors); with a
     high supply impedance this turns into <b>oscillation</b>. The TL072's slew rate
     is 13 V/µs — sudden current demand must be met by the local capacitor, not by
     20 cm of supply wire.</p>
</section>
<hr>
"""), dil)
    bolum08 = sec(M(f"""<section>
  <div class="adim-basi"><span class="adim-no">08</span><h2>Sorun giderme</h2></div>
  <div class="kaydir">
  <table>
    <thead><tr><th>Belirti</th><th>Muhtemel sebep</th></tr></thead>
    <tbody>
      <tr><td><span class="mono">#</span> hiç adres bulmuyor</td><td>SDA/SCL ters, ADDR boşta, ya da pull-up yok</td></tr>
      <tr><td>Yalnız 0x48 görünüyor</td><td>ADS #2'nin ADDR'ı +3V3'e bağlı değil</td></tr>
      <tr><td>Gerilim hep aynı sayıda takılı</td><td>Bölücünün altı VREF'e değil GND'ye gitmiş — çift yönlülük buna bağlı</td></tr>
      <tr><td>Negatif giriş 0 okunuyor</td><td>ADS tekli (single-ended) kipte; diferansiyel MUX yazılmamış</td></tr>
      <tr><td>Kalibrasyon başka noktada tutmuyor</td><td>Sıfır ve kazanç sırası: önce <span class="mono">z</span>, sonra <span class="mono">g</span></td></tr>
      <tr><td><span class="mono">PSRAM: YOK</span></td><td>FQBN'de <span class="mono">PSRAM=opi</span> yok; bazı N16R8'lerde quad — <span class="mono">PSRAM=enabled</span> dene</td></tr>
      <tr><td>Hızlı yolda PF saçma</td><td>Pencere 1 çevrimin altında; sinyal frekansı çok düşük</td></tr>
      <tr><td>Menzil sürekli gidip geliyor</td><td>Giriş histerezis bandında (NORMAL FS'in %70–90'ı); <span class="mono">a0</span> ile otomatiği kapat</td></tr>
    </tbody>
  </table>
  </div>
</section>

<footer>
  Üretildi: <span class="mono">uretim/kurulum3-uret.py</span> ·
  Değerler <span class="mono">uretim/tasarim3_sabit.py</span>'den okunuyor,
  elle yazılmıyor. Tasarım değişirse bu sayfa peşinden gider.
</footer>
""", f"""<section>
  <div class="adim-basi"><span class="adim-no">08</span><h2>Troubleshooting</h2></div>
  <div class="kaydir">
  <table>
    <thead><tr><th>Symptom</th><th>Likely cause</th></tr></thead>
    <tbody>
      <tr><td><span class="mono">#</span> finds no address at all</td><td>SDA/SCL swapped, ADDR floating, or no pull-ups</td></tr>
      <tr><td>Only 0x48 shows up</td><td>ADDR of ADS #2 is not connected to +3V3</td></tr>
      <tr><td>Voltage stuck at the same number</td><td>The bottom of the divider went to GND instead of VREF — bidirectionality depends on it</td></tr>
      <tr><td>Negative input reads 0</td><td>ADS in single-ended mode; differential MUX not written</td></tr>
      <tr><td>Calibration doesn't hold at another point</td><td>Order of zero and gain: first <span class="mono">z</span>, then <span class="mono">g</span></td></tr>
      <tr><td><span class="mono">PSRAM: YOK</span> (none)</td><td>No <span class="mono">PSRAM=opi</span> in the FQBN; some N16R8s are quad — try <span class="mono">PSRAM=enabled</span></td></tr>
      <tr><td>PF nonsense on the fast path</td><td>Window under 1 cycle; signal frequency too low</td></tr>
      <tr><td>Range keeps flipping back and forth</td><td>Input inside the hysteresis band (70–90% of NORMAL FS); turn auto off with <span class="mono">a0</span></td></tr>
    </tbody>
  </table>
  </div>
</section>

<footer>
  Generated by: <span class="mono">uretim/kurulum3-uret.py</span> ·
  Values are read from <span class="mono">uretim/tasarim3_sabit.py</span>,
  not typed by hand. If the design changes, this page follows.
</footer>
"""), dil)
    return f"""<!doctype html>
<!-- URETILDI: uretim/kurulum3-uret.py — ELLE DUZENLEME -->
<html lang="{dil}"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{baslik}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
{CSS}
</head><body>

<div class="sayfa">

{serit}

{ust}

{bolum00}{''.join(adim_html(a, dil) for a in ADIMLAR)}

{bolum08}</div>
</body></html>
"""


# BELGELER/ yoksa YARAT. Bu betik B9'da `belge-uret.py`'den ONCE
# kosuyor ve yalnizca o mkdir yapiyordu; klasor silinmis bir agacta
# (ya da mutasyon kopyasinda) B9 burada cokuyordu. `cikis_yolu` klasoru
# (en/ dahil) kendisi olusturuyor.
for dil in DILLER:
    hedef = cikis_yolu(KOK / "BELGELER", "4-kurulum.html", dil)
    hedef.write_text(sayfa_uret(dil), encoding="utf-8")
    if dil == "tr":
        print(f"yazildi: {hedef}")
        print(f"  {len(ADIMLAR)} adim, {hedef.stat().st_size // 1024} KB")
    else:
        print(f"  en: {hedef}")
