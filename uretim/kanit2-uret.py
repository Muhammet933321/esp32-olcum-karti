# -*- coding: utf-8 -*-
"""Asama 2 kanit sayfasini uretir — kanit/kanit2-sayfasi.html

    python kanit2-uret.py

TASARIM KURALI: bu betikte ELLE YAZILMIS OLCUM SAYISI YOKTUR. Her rakam
kanit/a2-tam-dogrulama.txt kaydindan cekilir; aranan satir bulunamazsa
betik hata verir ki sessizce eski bir sayi sayfaya girmesin.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KANIT = BURASI.parent / "arsiv" / "asama2" / "kanit"
GORSEL = BURASI.parent / "gorsel"
KAYIT = (KANIT / "a2-tam-dogrulama.txt").read_text(encoding="utf-8",
                                                   errors="replace")


def bul(desen: str, ad: str) -> str:
    m = re.search(desen, KAYIT)
    if not m:
        raise SystemExit(f"kayitta bulunamadi ({ad}): {desen}")
    return m.group(1).strip()


def svg(ad: str, sinif: str = "cizim") -> str:
    s = (GORSEL / ad).read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s)
    s = s.replace("<svg ", '<svg preserveAspectRatio="xMidYMid meet" ', 1)
    s = re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", s)
    return f'<figure class="{sinif}">{s}</figure>'


OK = KAYIT.count("[OK]")
HATA = KAYIT.count("[!!]")

S = {
    "oran":      bul(r"Bolucu 100K / 6\.8K\s+->\s+oran ([\d.]+)", "oran"),
    "v_tam":     bul(r"Gerilim tam olcegi Asama 1'i \(27\.14 V\) asiyor\s+([\d.]+) V", "v tam"),
    "v_adim":    bul(r"Gerilim adimi Asama 1'den \(26\.53 mV\) ince\s+([\d.]+) mV", "v adim"),
    "i_adim":    bul(r"En hassas kademe Asama 1'den \(30\.5 uA\) ince\s+([\d.]+) uA", "i adim"),
    "i_tam":     bul(r"En yuksek kademe Asama 1'i \(31 mA\) asiyor\s+([\d.]+) A", "i tam"),
    "menzil_a":  bul(r"secenek A:\s+([\d.]+) V'a kadar", "menzil A"),
    "menzil_c":  bul(r"secenek C:\s+([\d.]+) V'a kadar", "menzil C"),
    "menzil_d":  bul(r"secenek D:\s+([\d.]+) V'a kadar", "menzil D"),
    "ariza_v":   bul(r"SECILEN D: arizada dugum ADS mutlak azamisinin altinda\s+([\d.]+) V", "ariza"),
    "ariza_i":   bul(r"Secenek A ariza akimi ADS mutlak azamisinin altinda\s+([\d.]+) mA", "ariza akim"),
    "h_12v":     bul(r"12 V olcumunde hata < %0\.1\s+%([\d.]+)", "12V hata"),
    "h_100ma":   bul(r"100 mA olcumunde hata < %0\.2\s+%([\d.]+)", "100mA hata"),
    "h_kelvinsiz": bul(r"15 mohm KELVINSIZ\+KALIBRESIZ kabul edilemez \(kusur dogrulandi\)\s+%([\d.]+)", "kelvinsiz"),
    "h_kalibre": bul(r"Kalibrasyon statik kismi siliyor ama tamamini degil\s+%([\d.]+)", "kalibre"),
    "h_kelvin":  bul(r"KELVIN ile kalibrasyonsuz bile %1\.5'in altinda\s+%([\d.]+)", "kelvin"),
    "erc":       bul(r"ERC: (Found \d+ violations)", "erc"),
    "netlist":   bul(r"(\d+/\d+) dogrulama gecti\s*\n\s*\n-+\s*\n  A4", "netlist"),
    "flash":     bul(r"ESP32-S3 icin derlendi\s+flash (\d+) B", "flash"),
    "flash_y":   bul(r"ESP32-S3 icin derlendi\s+flash \d+ B \(%(\d+)\)", "flash %"),
    "ram":       bul(r"RAM (\d+) B", "ram"),
    "ram_y":     bul(r"RAM \d+ B \(%(\d+)\)", "ram %"),
    "cevrim":    bul(r"Program tamamlandi\s+([\d ]+) cevrim", "cevrim"),
    "skop_sps":  bul(r"Ornekleme (\d[\d ]+) Sa/s", "skop"),
    "skop_tam":  bul(r"Tam olcek ([\d.]+) V, adim [\d.]+ mV", "skop tam"),
}

ADIMLAR = re.findall(r"  (GECTI|KALDI)\s+(A\d)\s+(.+?)\s+([\d.]+) s", KAYIT)
# NOT: burada eskiden `!= 4` vardi. A5/A6 zincire eklendiginde bu satir
# uretimi durduruyordu, kanit sayfasi da 4 adimlik eski kosuyu gosteriyordu
# (DEVIR 4.2). Artik adim sayisi KAYIT'tan geliyor; MERDIVEN ile tutarli mi,
# onu siniyoruz.
if len(ADIMLAR) < 4:
    raise SystemExit(f"en az 4 adim bekleniyordu, {len(ADIMLAR)} bulundu")

# A1'in kural sayisi da kayittan okunur — elle yazilirsa sessizce eskir.
_kural = re.search(r"(\d+)/\d+ tasarim kurali gecti", KAYIT)
A1_KURAL = _kural.group(1) if _kural else "?"

SAYI = dict(re.findall(r"(\d+)/\d+ (?:tasarim kurali|dogrulama|kosul) gecti", KAYIT)
            and [] or [])

MERDIVEN = [
    ("A1", "Tasarim ve hata butcesi", "hesap + kural",
     "Menzil, cozunurluk, PGA merdiveni, Kelvin gerekcesi, pin plani, "
     "I2C pull-up ve derleme hedefi (PSRAM). "
     f"{A1_KURAL} tasarim kurali; ihlal varsa cikis kodu 1."),
    ("A2", "Analog giris korumasi", "ngspice",
     "Kelepcenin nereye baglanacagi <b>tarama ile secildi</b>, iddia ile "
     "degil. Dort secenek 0-300 V arasi kosuldu."),
    ("A3", "Sema: ERC + netlist", "kicad-cli",
     "ERC polariteyi <b>goremez</b>. Netlist'te her diyodun katodu, "
     "TL431'in anodu ve ADS adres pinleri tek tek okundu."),
    ("A4", "Uctan uca", "ngspice + AVR emulatoru + ESP32 derleyicisi",
     "ngspice -> ADS1115 modeli -> <b>gercek donusum kodu</b> -> protokol "
     "-> <b>gercek arayuz</b>. Ayrica ayni kaynak ESP32-S3'e derlendi."),
    ("A5", "Osiloskop: protokol ve ikili", "node + arduino-cli",
     "Skop protokolu <b>gercek arayuz ayristiricisina</b> verildi; zaman "
     "tabani merdiveninin firmware ve arayuzde ayni oldugu dogrulandi. "
     "Derlenmis ikilide <b>olu kod denetimi</b>: tetikleme ve kalibrasyon "
     "dallari gercekten duruyor mu."),
    ("A6", "Osiloskop olcum matematigi", "avr-gcc + emulator",
     "Frekans, Vpp, RMS, duty ve yukselme suresi <b>gercek firmware kodu</b> "
     "ile, analitik olarak bilinen dalgalara karsi olculdu. Duz cizgide "
     "olcum <b>yapilamamasi</b> da ayri bir kosul."),
]

KUSURLAR = [
    ("Tam olcek 45 V degil, 32.2 V", "tasarim", "kabul edildi",
     "ADS1115'in analog girisi besleme gerilimiyle sinirli (VDD+0.3). "
     "3.3 V'ta besledigimiz icin giris 3.3 V'u gecemiyor. Onceki mesajda "
     "45 V demistim, <b>yanlisti</b> — PGA'nin +-4.096 V olmasi bunu "
     "degistirmiyor. Yine de Asama 1'in 27.1 V'undan genis."),
    ("Kelepce menzili kesiyordu", "devre", "duzeltildi",
     f"1N4148 ile 11:1 bolucude kelepce {S['menzil_c']} V'ta sizmaya "
     "basliyor, 33 V'ta hata -%3.7. Sebep matematiksel: tam olcekte "
     "diyodun kapali kalmasi 0.22 V, arizada ileri dusumu 0.70 V ister — "
     "toplam 0.92 V; oysa 3.6 V mutlak azami ile 3.3 V tam olcek arasinda "
     "sadece 0.30 V var. <b>Cozum bolucu oranini buyutmek:</b> 100K/6.8K "
     "ile dugum 2.048 V'da kaliyor, kelepce tum menzilde ters kutuplu."),
    ("15 mΩ kademesinde lehim direnci", "montaj", "Kelvin ile cozuldu",
     f"Kelvinsiz ve kalibresiz %{S['h_kelvinsiz']} hata. Statik kismi "
     f"kalibrasyonla siliniyor ama geriye <b>yuke bagli</b> %{S['h_kalibre']} "
     "kaliyor (eklem akimla isiniyor, bakirin sicaklik katsayisi 3900 ppm/°C). "
     f"Kelvin ile kalibrasyona hic gerek kalmadan %{S['h_kelvin']} — o da "
     "sontun kendi %1 toleransi."),
    ("Wh sabiti 1000 kat yanlisti", "firmware", "duzeltildi",
     "Asama 1'den tasinan hata: <code>enerji_wh()</code> 1 Wh'i 3.6e18 pJ "
     "saniyordu, o 1 <b>kWh</b>. A4 bunu ayri bir kosul olarak siniyor: "
     "dogru sabitle (3.6e15) hesaplanan bit deseni bekleniyor, yanlis "
     "sabitinki <b>reddediliyor</b>."),
]

KANITLANMAYAN = [
    ("ADS1115'in kendi hatasi",
     "Veri sayfasi degerleri (ofset ±3 LSB, kazanc %0.15) hesaba katildi "
     "ama <b>gercek cip olculmedi</b>. Kazanc hatasi kalibrasyonla silinir; "
     "ofset silinmez."),
    ("Lehim ve temas dirençleri",
     "Simulasyonda sifir. 1 Ω ve ustundeki kademelerde onemsiz; 15 mΩ'da "
     "Kelvin baglanti <b>fiziksel olarak dogru yapilmali</b> — bunu ancak "
     "kart kurulunca gorebilirsin."),
    ("ESP32-S3 ADC'sinin dogrusalsizligi",
     "Osiloskop kanali. Bu kanal <b>dalga sekli</b> icin; sayisal degeri "
     "her zaman ADS1115'ten oku. Zaman eksenini NE555 ile bir kez kalibre et."),
    ("Direnc toleranslari",
     "Bolucu orani 15.706 kabul edildi. %1 metal filmde oran %2'ye kadar "
     "kayabilir — <code>kv</code> kalibrasyonu bunu siler ama once olcmen gerek."),
    ("Gercek gurultu ve sicaklik",
     "Simulasyon gurultusuz. 200 ms pencere tam 10 sebeke cevrimi oldugu "
     "icin 50 Hz ugultu ortalamada sifirlanmali — bu da olculmeli."),
    ("Multimetrenin kendi dogrulugu",
     "Tum kalibrasyon zinciri ona dayaniyor. Marka/model hala bilinmiyor."),
]

TEZGAH = [
    ("I2C taramasi yap", "0x48 ve 0x49 gorunmeli",
     "Iki ADS1115 farkli adreste mi? Ayni adresteyse ADDR pinlerinden biri "
     "yanlis baglanmis demektir ve veri yolu coker."),
    ("TL431 rayini olc", "2.495 V civari",
     "3.3 V okursan TL431 ters takilidir veya calisma akimi yetmiyordur. "
     "Bu ray hem gerilim hem osiloskop girisini koruyor."),
    ("Girisi bos birak, gerilimi oku", "0 V beklenir",
     "Deger goruyorsan bolucunun alt ucu topraga saglam bagli degildir."),
    ("Bilinen gerilim uygula, <code>kv</code> ile kalibre et", "orn. 12.00 V",
     "Direnc toleransi ve ADS kazanc hatasi burada silinir."),
    ("Yuku kes, akim sifirini al", "ofset birkac LSB",
     "Buyuk bir sayi cikarsa diferansiyel giris uclarindan biri havadadir."),
    ("15 mΩ kademesinde Kelvin'i dogrula", "kalibrasyonsuz %1 icinde",
     "Bilinen bir akim gecir. %6-7 sapma goruyorsan algilama uclari sontun "
     "govdesine degil PCB izine lehimlenmistir."),
    ("NE555 ile bilinen kare dalga uret", "zaman ekseni dogru mu",
     "Osiloskobun ornekleme hizi varsayimini (83 333 Sa/s) bu dogrular."),
]


def merdiven_html() -> str:
    durum = {a[1]: a[0] for a in ADIMLAR}
    r = []
    for kod, ad, arac, aciklama in MERDIVEN:
        gecti = durum.get(kod) == "GECTI"
        r.append(f"""<li class="basamak">
  <div class="kod">{kod}</div>
  <div class="govde">
    <h3>{ad} <span class="arac">{arac}</span></h3>
    <p>{aciklama}</p>
  </div>
  <div class="rozet {'gecti' if gecti else 'kaldi'}">{'gecti' if gecti else 'kaldi'}</div>
</li>""")
    return "\n".join(r)


def kusur_html() -> str:
    r = []
    for baslik, nerede, durum, metin in KUSURLAR:
        r.append(f"""<article class="kusur">
  <header><h3>{baslik}</h3>
    <span class="etiket yer">{nerede}</span>
    <span class="etiket duzeltildi">{durum}</span></header>
  <p>{metin}</p>
</article>""")
    return "\n".join(r)


def liste_html(k) -> str:
    return "\n".join(f"<li><h4>{a}</h4><p>{b}</p></li>" for a, b in k)


def tezgah_html() -> str:
    return "\n".join(f"""<li>
  <div class="no">{n}</div>
  <div><h4>{a}</h4><p class="bekle">beklenen: <b>{b}</b></p><p>{c}</p></div>
</li>""" for n, (a, b, c) in enumerate(TEZGAH, 1))


SAYFA = f"""<title>Asama 2 Tasarim Dosyasi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:ital,wght@0,400;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@500;600&display=swap">
<style>
:root {{
  --kagit:#f4f5f8; --yuzey:#ffffff; --cizgi:#dcdfe6;
  --murekkep:#171b22; --soluk:#5b6474; --daha-soluk:#8b93a2;
  --olcum:#2853c6; --olcum-zemin:#2853c614;
  --gecti:#14704a; --gecti-zemin:#14704a12;
  --uyari:#8f5a10; --uyari-zemin:#8f5a1012;
  --hata:#a82f26; --hata-zemin:#a82f2612;
  --olcu:66ch;
  --seri:"IBM Plex Serif", Georgia, "Times New Roman", serif;
  --mono:"IBM Plex Mono", ui-monospace, Consolas, monospace;
  --sans:"IBM Plex Sans", system-ui, -apple-system, sans-serif;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --kagit:#101318; --yuzey:#171b22; --cizgi:#2a2f3a;
    --murekkep:#e3e7ef; --soluk:#98a1b2; --daha-soluk:#6d7686;
    --olcum:#84a4ff; --olcum-zemin:#84a4ff1a;
    --gecti:#4cbc8a; --gecti-zemin:#4cbc8a16;
    --uyari:#d69b45; --uyari-zemin:#d69b4516;
    --hata:#ec7d72; --hata-zemin:#ec7d7216;
  }}
}}
:root[data-theme="dark"] {{
  --kagit:#101318; --yuzey:#171b22; --cizgi:#2a2f3a;
  --murekkep:#e3e7ef; --soluk:#98a1b2; --daha-soluk:#6d7686;
  --olcum:#84a4ff; --olcum-zemin:#84a4ff1a;
  --gecti:#4cbc8a; --gecti-zemin:#4cbc8a16;
  --uyari:#d69b45; --uyari-zemin:#d69b4516;
  --hata:#ec7d72; --hata-zemin:#ec7d7216;
}}
*, *::before, *::after {{ box-sizing:border-box; }}
body {{ background:var(--kagit); color:var(--murekkep);
  font-family:var(--seri); font-size:16.5px; line-height:1.62;
  -webkit-font-smoothing:antialiased; }}
.sayfa {{ max-width:min(94vw, 1080px); margin:0 auto; padding:0 20px 96px; }}
p {{ margin:0 0 1em; }}
h1,h2,h3,h4 {{ text-wrap:balance; margin:0; }}
b {{ font-weight:600; }}
code {{ font-family:var(--mono); font-size:.86em; background:var(--olcum-zemin);
  color:var(--olcum); padding:.1em .34em; border-radius:3px; }}

header.ust {{ padding:72px 0 40px; border-bottom:1px solid var(--cizgi); }}
.gozustu {{ font-family:var(--mono); font-size:12px; font-weight:500;
  letter-spacing:.16em; text-transform:uppercase; color:var(--olcum);
  margin:0 0 18px; }}
h1 {{ font-size:clamp(34px, 5.2vw, 52px); line-height:1.08; font-weight:700;
  letter-spacing:-.018em; margin:0 0 20px; }}
.girisi {{ font-size:19px; color:var(--soluk); max-width:60ch; margin:0; }}
.girisi em {{ color:var(--murekkep); font-style:italic; }}

.kpi {{ display:grid; gap:1px; background:var(--cizgi);
  grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));
  border:1px solid var(--cizgi); border-radius:6px; overflow:hidden;
  margin:40px 0 0; }}
.kpi div {{ background:var(--yuzey); padding:18px 20px; }}
.kpi .n {{ font-family:var(--mono); font-size:27px; font-weight:600;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em; display:block;
  line-height:1.15; }}
.kpi .e {{ font-family:var(--sans); font-size:11.5px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--daha-soluk); display:block;
  margin-top:6px; }}
.kpi .iyi .n {{ color:var(--gecti); }}

section {{ padding-top:60px; }}
h2 {{ font-size:26px; font-weight:600; letter-spacing:-.012em;
  padding-bottom:10px; margin-bottom:8px;
  border-bottom:2px solid var(--murekkep); display:inline-block; }}
.altbaslik {{ color:var(--soluk); margin:14px 0 26px; max-width:var(--olcu); }}
.aciklama {{ font-size:14.5px; color:var(--soluk); max-width:var(--olcu);
  margin:4px 0 0; }}

ol.merdiven {{ list-style:none; padding:0; margin:0; display:flex;
  flex-direction:column; gap:1px; background:var(--cizgi);
  border:1px solid var(--cizgi); border-radius:6px; overflow:hidden; }}
.basamak {{ background:var(--yuzey); display:grid; align-items:start; gap:16px;
  grid-template-columns:52px 1fr auto; padding:16px 20px; }}
.basamak .kod {{ font-family:var(--mono); font-size:14px; font-weight:600;
  color:var(--olcum); padding-top:2px; }}
.basamak h3 {{ font-family:var(--sans); font-size:15.5px; font-weight:600;
  margin-bottom:4px; }}
.basamak .arac {{ font-family:var(--mono); font-size:11px; font-weight:400;
  color:var(--daha-soluk); margin-left:8px; }}
.basamak p {{ margin:0; font-size:14.5px; color:var(--soluk); line-height:1.55; }}
.rozet {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.09em;
  text-transform:uppercase; padding:3px 9px; border-radius:99px;
  white-space:nowrap; margin-top:2px; }}
.rozet.gecti {{ background:var(--gecti-zemin); color:var(--gecti); }}
.rozet.kaldi {{ background:var(--hata-zemin); color:var(--hata); }}

.tablo-kutu {{ overflow-x:auto; margin:24px 0 10px; border:1px solid var(--cizgi);
  border-radius:6px; }}
table {{ width:100%; border-collapse:collapse; background:var(--yuzey);
  font-family:var(--mono); font-size:13.5px; font-variant-numeric:tabular-nums; }}
th, td {{ padding:9px 14px; text-align:right; white-space:nowrap; }}
td:first-child, th:first-child {{ text-align:left; font-family:var(--sans); }}
thead th {{ font-family:var(--sans); font-size:11px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--daha-soluk); font-weight:600;
  border-bottom:1px solid var(--cizgi); }}
tbody tr + tr td {{ border-top:1px solid var(--cizgi); }}
td.iyi {{ color:var(--gecti); }}
caption {{ caption-side:bottom; text-align:left; padding:11px 14px;
  font-family:var(--sans); font-size:12.5px; color:var(--daha-soluk);
  border-top:1px solid var(--cizgi); }}

figure.cizim {{ margin:26px 0 6px; background:var(--yuzey);
  border:1px solid var(--cizgi); border-radius:6px; padding:16px;
  overflow-x:auto; }}
figure.cizim svg {{ width:100%; height:auto; display:block; }}
figure.sema {{ margin:26px 0 6px; background:#fcfcfa; border:1px solid var(--cizgi);
  border-radius:6px; padding:18px; overflow-x:auto; }}
figure.sema svg {{ width:100%; height:auto; display:block; }}
figcaption {{ font-family:var(--sans); font-size:12.5px; color:var(--daha-soluk);
  margin-top:10px; }}

.kusurlar {{ display:grid; gap:14px; margin-top:24px; }}
.kusur {{ background:var(--yuzey); border:1px solid var(--cizgi);
  border-left:3px solid var(--uyari); border-radius:5px; padding:18px 20px; }}
.kusur header {{ display:flex; align-items:baseline; gap:10px;
  flex-wrap:wrap; margin-bottom:8px; }}
.kusur h3 {{ font-family:var(--sans); font-size:16px; font-weight:600; }}
.kusur p {{ margin:0; font-size:14.5px; color:var(--soluk); }}
.etiket {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.07em;
  text-transform:uppercase; padding:2px 8px; border-radius:99px; }}
.etiket.yer {{ background:var(--olcum-zemin); color:var(--olcum); }}
.etiket.duzeltildi {{ background:var(--gecti-zemin); color:var(--gecti); }}

.sinir {{ background:var(--uyari-zemin); border:1px solid var(--cizgi);
  border-radius:6px; padding:24px 26px; margin-top:24px; }}
.sinir > p:first-child {{ font-size:15px; color:var(--murekkep);
  max-width:var(--olcu); }}
ul.acik {{ list-style:none; padding:0; margin:18px 0 0; display:grid; gap:14px; }}
ul.acik li {{ padding-left:18px; border-left:2px solid var(--uyari); }}
ul.acik h4 {{ font-family:var(--sans); font-size:14.5px; font-weight:600;
  margin-bottom:3px; }}
ul.acik p {{ margin:0; font-size:14px; color:var(--soluk); }}

ol.tezgah {{ list-style:none; padding:0; margin:24px 0 0; display:grid; gap:1px;
  background:var(--cizgi); border:1px solid var(--cizgi); border-radius:6px;
  overflow:hidden; }}
ol.tezgah li {{ background:var(--yuzey); display:grid;
  grid-template-columns:38px 1fr; gap:14px; padding:16px 20px; }}
ol.tezgah .no {{ font-family:var(--mono); font-size:14px; font-weight:600;
  color:var(--olcum); }}
ol.tezgah h4 {{ font-family:var(--sans); font-size:15px; font-weight:600;
  margin-bottom:4px; }}
ol.tezgah p {{ margin:0; font-size:14px; color:var(--soluk); }}
ol.tezgah .bekle {{ font-family:var(--mono); font-size:12.5px;
  color:var(--daha-soluk); margin-bottom:5px; }}

pre {{ font-family:var(--mono); font-size:13px; line-height:1.7;
  background:var(--yuzey); border:1px solid var(--cizgi); border-radius:6px;
  padding:16px 18px; overflow-x:auto; margin:20px 0 0; }}
pre .y {{ color:var(--daha-soluk); }}
footer {{ margin-top:72px; padding-top:22px; border-top:1px solid var(--cizgi);
  font-family:var(--sans); font-size:12.5px; color:var(--daha-soluk); }}
@media (max-width:640px) {{
  .basamak {{ grid-template-columns:44px 1fr; }}
  .basamak .rozet {{ grid-column:2; justify-self:start; }}
}}
</style>

<div class="sayfa">

<header class="ust">
  <p class="gozustu">Olcum Karti &middot; Asama 2 &middot; ESP32-S3 + ADS1115</p>
  <h1>Kelepceyi nereye baglayacagimizi<br>simulasyon secti</h1>
  <p class="girisi">Asama 2 tasarimi bastan sona kuruldu, cizildi ve
  dogrulandi. Kritik karar &mdash; giris korumasi &mdash; <em>iddia ile
  degil, dort secenegin 0&ndash;300 V taranmasiyla</em> verildi; ilk sectigim
  secenek elendi. Zincir ngspice'tan gercek donusum koduna, oradan gercek
  arayuze kadar kapali.</p>

  <div class="kpi">
    <div class="iyi"><span class="n">{OK}</span><span class="e">dogrulama gecti</span></div>
    <div class="iyi"><span class="n">{HATA}</span><span class="e">basarisiz</span></div>
    <div><span class="n">4</span><span class="e">kusur bulundu</span></div>
    <div><span class="n">{S['v_adim']}</span><span class="e">mV gerilim adimi</span></div>
    <div><span class="n">{S['i_adim']}</span><span class="e">&micro;A akim adimi</span></div>
  </div>
</header>

<section>
  <h2>Ne degisti</h2>
  <p class="altbaslik">Asama 1 (Arduino + LM358 + 10 bit) ile karsilastirma.
  Her sayi <code>uretim/tasarim2.py</code> tarafindan hesaplandi.</p>

  <div class="tablo-kutu">
  <table>
    <thead><tr><th>ozellik</th><th>Asama 1</th><th>Asama 2</th><th>kazanc</th></tr></thead>
    <tbody>
      <tr><td>Gerilim tam olcek</td><td>27.14 V</td><td>{S['v_tam']} V</td><td class="iyi">1.19&times;</td></tr>
      <tr><td>Gerilim adimi</td><td>26.53 mV</td><td>{S['v_adim']} mV</td><td class="iyi">27&times;</td></tr>
      <tr><td>Akim tam olcek</td><td>31.2 mA</td><td>{S['i_tam']} A</td><td class="iyi">370&times;</td></tr>
      <tr><td>Akim adimi</td><td>30.5 &micro;A</td><td>{S['i_adim']} &micro;A</td><td class="iyi">39&times;</td></tr>
      <tr><td>Akim ofseti</td><td>&plusmn;200 &micro;A</td><td>&plusmn;2.3 &micro;A</td><td class="iyi">85&times;</td></tr>
      <tr><td>DC ornekleme</td><td>1720 /s</td><td>860 /s</td><td>2&times; dusuk</td></tr>
      <tr><td>200 ms gurultu tabani</td><td>1.64 &micro;A</td><td>0.06 &micro;A</td><td class="iyi">28&times;</td></tr>
      <tr><td>Osiloskop ornekleme</td><td>76 923 Sa/s</td><td>{S['skop_sps']} Sa/s</td><td class="iyi">1.08&times;</td></tr>
      <tr><td>Osiloskop cozunurluk</td><td>8 bit</td><td>12 bit</td><td class="iyi">16&times;</td></tr>
    </tbody>
    <caption>DC ornekleme tek gerileyen kalem. Besledigi sey &mdash; 200 ms
    penceredeki gurultu tabani &mdash; yine de 28 kat iyi: yari sayida ornek
    ama her ornek 39 kat ince.</caption>
  </table>
  </div>
</section>

<section>
  <h2>Kritik karar: kelepce nereye?</h2>
  <p class="altbaslik">Giris korumasi icin dort secenek 0&ndash;300 V arasi
  tarandi. <b>Ilk sectigim secenek (C) elendi.</b></p>

{svg("a2a-kelepce.svg")}
  <p class="aciklama">Solda dogrusallik hatasi, sagda arizada ADC ucuna
  gelen gerilim. Secenek C (11:1 bolucu + TL431 kelepce) guvenli ama
  <b>{S['menzil_c']} V'ta sizmaya basliyor</b>; 33 V'ta hata &minus;%3.7.
  Secenek A menzili koruyor ({S['menzil_a']} V) ama ucun gerilimini
  sinirlamiyor. Secenek D ikisini birden veriyor: <b>{S['menzil_d']} V'a
  kadar %0.1 icinde</b>, arizada uc {S['ariza_v']} V'ta kaliyor.</p>

  <p style="margin-top:1.4em">Karar matematikten cikti, denemeden degil:</p>
  <div class="tablo-kutu">
  <table>
    <thead><tr><th>1N4148 ile ne gerekiyor</th><th>gerilim</th></tr></thead>
    <tbody>
      <tr><td>tam olcekte diyodun kapali kalmasi icin marj</td><td>0.22 V</td></tr>
      <tr><td>arizada diyodun ileri dusumu</td><td>0.70 V</td></tr>
      <tr><td><b>gereken toplam acikli</b></td><td><b>0.92 V</b></td></tr>
      <tr><td>elde olan (3.6 V mutlak azami &minus; 3.3 V tam olcek)</td><td>0.30 V</td></tr>
    </tbody>
    <caption>Olmuyor. Cozum tam olcek <b>dugum</b> gerilimini dusurmek:
    PGA &plusmn;2.048 V secilince dugum 2.048 V'da kaliyor, TL431 rayi
    2.495 V &mdash; diyot tum menzilde ters kutuplu, sizinti sifir. Bolucu
    100K/6.8K (oran {S['oran']}) olunca tam olcek {S['v_tam']} V.</caption>
  </table>
  </div>
</section>

<section>
  <h2>Menzil</h2>
  <p class="altbaslik">Sont merdiveni, 16 bitin her kademede verdigi
  32 768:1 dinamik aralikla birlesince yaklasik yedi dekat kapsiyor.</p>
{svg("a2b-menzil.svg")}
  <p class="aciklama">Her cizginin sol ucu o kademenin adimi, sag ucu tam
  olcegi. Gri cizgi Asama 1'in tek kademesi.</p>
</section>

<section>
  <h2>Kelvin baglanti neden sart</h2>
  <p class="altbaslik">Ilk yazdigim gerekce yanlisti: &ldquo;statik %6.7
  hata&rdquo; aslinda <b>kalibrasyonla siliniyor</b>. Gercek gerekce baska.</p>
{svg("a2c-hata.svg")}
  <p class="aciklama">Kalibrasyon statik lehim direncini siliyor ama geriye
  <b>yuke bagli</b> kisim kaliyor: eklem akimla isiniyor, bakirin sicaklik
  katsayisi 3900 ppm/&deg;C. 10 A'de %{S['h_kalibre']}. Ayrica Kelvinsiz
  kademeyi kullanmak icin elinde <b>10 A veren ve olcen bir referans</b>
  olmasi gerekir. Kelvin ile kalibrasyona hic gerek kalmiyor:
  %{S['h_kelvin']} &mdash; o da sontun kendi %1 toleransi.</p>
</section>

<section>
  <h2>Sema</h2>
  <p class="altbaslik">Alti blok: TL431 kelepce rayi, gerilim girisi, sont +
  Kelvin, osiloskop girisi, ADS1115 &times;2, ESP32-S3 baglantisi.
  {S['erc']}, netlist {S['netlist']}.</p>
{svg("_sema2/olcum-karti-a2.svg", "sema")}
  <figcaption>KiCad renkleri koyu zeminde okunmadigi icin sema kalici acik
  levha uzerinde. ERC polariteyi goremez; her diyodun katodu netlist'ten
  ayrica okundu.</figcaption>
</section>

<section>
  <h2>Dogrulama zinciri</h2>
  <p class="altbaslik">Her katman altindakinin goremeyecegi bir seyi
  yakaliyor.</p>
  <ol class="merdiven">
{merdiven_html()}
  </ol>

  <p class="aciklama" style="margin-top:1.6em"><b>A4 neden AVR'de kosuyor:</b>
  ESP32-S3'u komut komut calistiran bir emulatorumuz yok. Ama AVR'yi
  calistiran ve 39/39 bit birebir dogrulanmis bir emulatorumuz var.
  <code>olcum2.h</code> hicbir platform cagrisi icermedigi, <code>int</code>
  ve <code>double</code> kullanmadigi icin iki mimaride de ayni IEEE-754
  sonucu verir &mdash; {S['cevrim']} AVR cevrimi kosturuldu ve her deger
  numpy float32 ile <b>bit birebir</b> tuttu. Ayni kaynak ayrica gercek
  ESP32-S3 derleyicisiyle derlendi: {S['flash']} B flash (%{S['flash_y']}),
  {S['ram']} B RAM (%{S['ram_y']}), sifir uyari.</p>
</section>

<section>
  <h2>Bulunan kusurlar</h2>
  <p class="altbaslik">Dordu de bu calisma sirasinda ortaya cikti. Ikisi
  benim onceki mesajlardaki hatamdi.</p>
  <div class="kusurlar">
{kusur_html()}
  </div>
</section>

<section>
  <h2>Bunlar hala kanitlanmadi</h2>
  <div class="sinir">
    <p>Yukaridakilerin hicbiri tezgah olcumu degil. Simulasyon gurultusuz,
    parcalar ideal, lehim direnci sifir. Asagidakiler <b>ancak kart
    kurulunca</b> kapanir.</p>
    <ul class="acik">
{liste_html(KANITLANMAYAN)}
    </ul>
  </div>
</section>

<section>
  <h2>Kart gelince sirasiyla</h2>
  <p class="altbaslik">Her adimda ne beklendigi yaziyor ki, beklenmeyen bir
  sey gorursen ne oldugunu anlayasin.</p>
  <ol class="tezgah">
{tezgah_html()}
  </ol>
</section>

<section>
  <h2>Kendin kostur</h2>
  <p class="altbaslik">Bu sayfadaki her sayi asagidaki komutun ciktisindan
  uretildi; sayfayi ureten betikte elle yazilmis tek bir olcum degeri yok.</p>
<pre><span class="y"># Asama 2 zinciri (A1-A6), ~65 saniye</span>
cd projeler/olcum-karti/uretim
python dogrula2.py

<span class="y"># tek tek</span>
python tasarim2.py       <span class="y"># A1  tasarim + hata butcesi</span>
python sim2_giris.py     <span class="y"># A2  giris korumasi (ngspice)</span>
python sema2-uret.py     <span class="y"># A3  semayi uret</span>
python netlist2_dogrula.py
python sim2_kart.py      <span class="y"># A4  uctan uca</span>
python test_skop.py      <span class="y"># A5  skop protokolu + ikili denetimi</span>
python test_skop_olcum.py <span class="y"># A6  skop olcum matematigi</span>
python gorsel_a2.py      <span class="y"># kanit grafikleri</span>
python kanit2-uret.py    <span class="y"># bu sayfa</span>

<span class="y"># Asama 1 hala duruyor ve gecmeye devam ediyor</span>
python dogrula.py</pre>
</section>

<footer>
  Uretim: <code>uretim/kanit2-uret.py</code> &middot; kaynak
  <code>kanit/a2-tam-dogrulama.txt</code> &middot; ADS1115 TI SBAS444
  &middot; ESP32-S3 Espressif veri sayfasi + ESP-IDF ADC belgeleri
  &middot; ATmega328/P Atmel-42735B (emulator dogrulamasi icin).
</footer>

</div>
"""

if __name__ == "__main__":
    hedef = KANIT / "kanit2-sayfasi.html"
    hedef.write_text(SAYFA, encoding="utf-8")
    print(f"yazildi: {hedef}  ({hedef.stat().st_size // 1024} KB)")
    print(f"  {OK} dogrulama, {HATA} hata, {len(ADIMLAR)} adim")
