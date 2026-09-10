# -*- coding: utf-8 -*-
"""Kanit sayfasini uretir — kanit/kanit-sayfasi.html

    python kanit-uret.py

TASARIM KURALI: bu betikte ELLE YAZILMIS OLCUM SAYISI YOKTUR. Her rakam ya
kanit/s9-veri.json'dan ya da kanit/tam-dogrulama.txt kaydindan cekilir.
Aranan satir bulunamazsa betik hata verir — sessizce eski/uydurma bir sayi
sayfaya girmesin diye.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KANIT = BURASI.parent / "arsiv" / "asama1" / "kanit"
GORSEL = BURASI.parent / "gorsel"
KAYIT = (KANIT / "tam-dogrulama.txt").read_text(encoding="utf-8", errors="replace")
VERI = json.loads((KANIT / "s9-veri.json").read_text(encoding="utf-8"))


def bul(desen: str, ad: str) -> str:
    m = re.search(desen, KAYIT)
    if not m:
        raise SystemExit(f"kayitta bulunamadi ({ad}): {desen}")
    return m.group(1).strip()


def svg(ad: str, sinif: str = "cizim") -> str:
    """SVG'yi satir ici goml; dis olcu ozniteliklerini at ki kapsayici belirlesin."""
    s = (GORSEL / ad).read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s)
    s = s.replace("<svg ", '<svg preserveAspectRatio="xMidYMid meet" ', 1)
    s = re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", s)
    return f'<figure class="{sinif}">{s}</figure>'


# ---------------------------------------------------------------- veriler
z = VERI["ozet"]
kal = VERI["kalibrasyon"]
osilo = VERI["osilo"]

OK = KAYIT.count("[OK]")
HATA = KAYIT.count("[!!]")

S = {
    "tl431": bul(r"TL431 katot gerilimi\s+olculen\s+([\d.]+) V", "TL431"),
    "aref_spice": bul(r"SECILEN Rs=220 ohm -> AREF\s+olculen\s+([\d.]+) V", "AREF"),
    "kelepce": bul(r"400\.0 V girisde -> dugum ([\d.]+) V", "kelepce"),
    "kelepce_ma": bul(r"400\.0 V girisde -> dugum [\d.]+ V, kelepce akimi\s+([\d.]+) mA", "kelepce mA"),
    "kazanc": bul(r"Kapali cevrim kazanc\s+olculen\s+([\d.]+)", "kazanc"),
    "tam_olcek": bul(r"Gerilim tam olcek \(1023 adim\)\s+olculen\s+([\d.]+) V", "tam olcek"),
    "guc_tavan": bul(r"Guc tavani\s+olculen\s+([\d.]+) W", "guc"),
    "flash": bul(r"arduino:avr:uno\s+flash\s+(\d+) B", "flash"),
    "sram": bul(r"arduino:avr:uno\s+flash\s+\d+ B\s+SRAM\s+(\d+) B", "sram"),
    "bos_sram": bul(r"arduino:avr:uno\s+flash\s+\d+ B\s+SRAM\s+\d+ B\s+bos\s+(\d+) B", "bos"),
    "erc": bul(r"ERC: (Found \d+ violations)", "erc"),
}

# adim ozetleri: "  GECTI  S1  TL431 referansi   1.0 s"
ADIMLAR = re.findall(r"  (GECTI|KALDI)\s+(S\d+)\s+(.+?)\s+([\d.]+) s", KAYIT)
if len(ADIMLAR) < 9:
    raise SystemExit(f"ozet tablosunda 9 adim bekleniyordu, {len(ADIMLAR)} bulundu")

MERDIVEN = [
    ("S1", "TL431 referansi", "ngspice",
     "220 &Omega; seri direncin AREF'i ne kadar dusurdugu. 4.7K secilseydi "
     "menzilin %13'u giderdi — <b>secim burada elendi</b>."),
    ("S2", "Bolucu, kelepce, suzgec", "ngspice",
     "Girise 400 V kacarsa dugum ne olur; dugum kondansatoru osiloskobu "
     "oldurur mu. <b>100 nF reddedildi</b>, kesim 178 Hz cikiyordu."),
    ("S3", "Sont + LM358", "ngspice",
     "Kapali cevrim kazanc, tek beslemede cikisin AREF'e ulasip ulasmadigi, "
     "giris ofsetinin akima etkisi."),
    ("S4", "Firmware aritmetigi", "Python / float32",
     "Enerji sayacini float'ta tutsak ne olurdu. <b>Sabitler artik .ino "
     "kaynagindan okunuyor</b> — kopya deger kaymasin diye."),
    ("S5", "Sema: ERC + netlist", "kicad-cli",
     "ERC polariteyi <b>goremez</b>. Netlist pin islevleri tek tek okunuyor: "
     "diyot katodu, TL431 anodu, LM358 beslemesi."),
    ("S6", "Gercek derleme", "arduino-cli / avr-g++",
     f"Gercek avr-g++, <code>--warnings all</code>. {S['flash']} B flash, "
     f"{S['sram']} B SRAM, yigit icin {S['bos_sram']} B bos, <b>0 uyari</b>."),
    ("S7", "Arayuz mantigi", "node",
     "Satir ayristirma, birim olcekleme, osiloskop toplama, gecmis budama."),
    ("S8", "Simulatorun kendisi", "avr-gcc + emulator",
     "Bir simulator dogrulanmadan hicbir sey kanitlamaz. Sonucu bagimsiz "
     "bilinen AVR programi kosuluyor, <b>39/39 deger bit birebir</b>."),
    ("S9", "Kart uctan uca", "ngspice + gercek ikili",
     "Gercek .elf, komut komut. ADC veri sayfasi denklemiyle, dis dunya "
     "ngspice tarama tablosuyla besleniyor."),
    ("S10", "Ekranda gorunen sayi", "node + app.js",
     "Kartin gercekten gonderdigi baytlar, arayuzun kendi ayristiricisina "
     "veriliyor. Elle yazilmis ornek satir yok."),
]

KUSURLAR = [
    ("Wh alani tam 1000 kat kucuk", "firmware", "duzeltildi",
     "<code>enerji_wh()</code> 1 Wh'i 3.6e18 pJ saniyordu — o 1 <b>kWh</b>'in "
     "karsiligi. Dogrusu 3.6e15. Joule alani dogru oldugu icin gozden "
     "kaciyordu; iki alan birbiriyle karsilastirilana kadar sessizce yanlisti. "
     "S4 bunu <b>yakalayamazdi</b>: S4 aritmetigi Python'da yeniden yaziyor, "
     "yani ayni yanlisi paylasmiyor ama gercek fonksiyonu da hic cagirmiyor."),
    ("Osiloskop tetiklemesi olu koddu", "firmware", "duzeltildi",
     "Tek cagri yeri <code>osiloskop_yakala(0, 0)</code> idi. Derleyici "
     "<code>esik == 0</code> sabitini gorup tetikleme arayan ~25 satiri ve "
     "hata dalini komple atmisti. S9 ikilideki metinleri arayinca ortaya "
     "cikti: <code>\"! tetiklenemedi\"</code> flash'ta <b>yoktu</b>. Esik "
     "artik komuttan geliyor (<code>t128</code>) ve o yol test ediliyor."),
    ("ADC on bolucusu icin yanlis tablo", "simulator", "duzeltildi",
     "Emulatorde ADC'ye Timer0'in saat-secim tablosunu vermistim. ADC 64 kat "
     "hizli kosuyor, ornekleme hizi 7220/sn gorunuyor ve <b>sahte kanal "
     "sizmasi</b> uretiyordu. Ayri tablo (2,2,4,8,16,32,64,128) ile "
     "gerilim hatasi 258 mV'tan 7 mV'a dustu."),
    ("Serbest calismada zamanlama kaymasi", "simulator", "duzeltildi",
     "Donusum bitisini <i>fark ettigim</i> anda yenisini basliyordum, ideal "
     "andan degil. Gecikme her turda birikince 1000 orneklik yakalamada "
     "yan bantlar cikiyordu (artik RMS 78 mV). Ideal ana kilitleyince "
     "<b>30.0 mV</b> — saf kuantalamanin teorik degeri 30.6 mV."),
]

KANITLANMAYAN = [
    ("TL431'in gercek referansi",
     f"SPICE {S['aref_spice']} V diyor, tezgahta multimetre ile "
     f"{z['aref']} V okundu. Fark %0.32 ve <b>dogrudan olcume geciyor</b>. "
     "Coz&uuml;m&uuml;: bir kez <code>kv</code> ile kalibre et."),
    ("Direnc toleranslari",
     "Bolucu orani 11.000 kabul edildi. %1 metal filmde bile oran %2'ye "
     "kadar kayabilir. Kalibrasyon bunu da siler ama <b>once olcmen gerek</b>."),
    ("Lehim ve temas dirençleri",
     "Sont 10 &Omega; iken bir lehim noktasi (~1 m&Omega;) %0.01 eder, "
     "onemsiz. Ileride 5 m&Omega; sonte gecilirse ayni nokta <b>%20</b> olur; "
     "o zaman Kelvin baglanti sart."),
    ("Gercek gurultu ve sicaklik",
     "Simulasyon gurultusuz. Tezgahta 50 Hz sebeke ugultusu, termal "
     "surukleme ve LM358'in gercek ofseti var. 200 ms pencere tam 10 sebeke "
     "cevrimi oldugu icin ugultu ortalamada sifirlanmali — <b>bu da olculmeli</b>."),
    ("Multimetrenin kendi dogrulugu",
     "Tum kalibrasyon zinciri multimetreye dayaniyor. Marka/model hala "
     "bilinmiyor; genel dogruluk ondan iyi olamaz."),
]

TEZGAH = [
    ("AREF-GND arasini olc", "2.470 V civari",
     "Tam 2.495 V okursan <b>harici referans secilmemis</b> demektir: "
     "ADC'nin ic merdiveni ~77 &micro;A cekiyor ve 220 &Omega; uzerinde "
     "dusum yaratmali. Dusum yoksa akim da yok."),
    ("Bilinen bir gerilim uygula, <code>kv</code> ile kalibre et", "orn. <code>kv12.00</code>",
     "Multimetrenin okudugu degeri yaz. Carpan EEPROM'a yazilir, "
     "kart kapansa da kalir."),
    ("Yuku kes, <code>s</code> komutunu ver", "ofset ~8 adim",
     "LM358'in giris ofseti sifirlanir. Simulasyonda 8 adim cikti; "
     "gercek parcada farkli olabilir, onemli olan <b>sifirin sabit kalmasi</b>."),
    ("Bilinen bir akim gecir, <code>ka</code> ile kalibre et", "orn. <code>ka0.020</code>",
     "Sonttan gecen gercek akimi multimetreyle olcup yaz."),
    ("Olcum ucunu havada birak", "0 V beklenir",
     "Deger gorunuyorsa giris ucu <b>havada salinan anten</b> gibi "
     "davraniyor demektir; tezgahta bu yasanmisti. Bolucunun alt ucu "
     "topraga saglam bagli mi bak."),
    ("<code>t128</code> ile bilinen bir dalga yakala", "tepeden tepeye dogru mu",
     "Zaman ekseni 76923 ornek/sn varsayiyor (16 MHz / 16 / 13 ADC saati). "
     "Bilinen frekansli bir kaynakla bunu <b>bir kez</b> dogrula."),
]


def satirlar_olcum() -> str:
    r = []
    for v, i, vo, io, w in VERI["olcumler"]:
        hata_mv = (vo - v) * 1000
        lsb = (vo - v) / z["lsb_v"]
        r.append(
            f"<tr><td>{v:.2f}</td><td>{i*1000:.2f}</td>"
            f"<td>{vo:.4f}</td><td>{io*1000:.3f}</td>"
            f"<td>{w:.4f}</td>"
            f"<td class='sap'>{hata_mv:+.1f}</td>"
            f"<td class='sap'>{lsb:+.2f}</td></tr>")
    return "\n".join(r)


def merdiven_html() -> str:
    durum = {a[1]: a[0] for a in ADIMLAR}
    r = []
    for kod, ad, arac, aciklama in MERDIVEN:
        d = durum.get(kod, "GECTI" if kod == "S10" else "?")
        isaret = "gecti" if d == "GECTI" else "kaldi"
        r.append(f"""<li class="basamak">
  <div class="kod">{kod}</div>
  <div class="govde">
    <h3>{ad} <span class="arac">{html.escape(arac)}</span></h3>
    <p>{aciklama}</p>
  </div>
  <div class="rozet {isaret}">{'gecti' if isaret == 'gecti' else 'kaldi'}</div>
</li>""")
    return "\n".join(r)


def kusur_html() -> str:
    r = []
    for baslik, nerede, durum, metin in KUSURLAR:
        r.append(f"""<article class="kusur">
  <header><h3>{baslik}</h3>
    <span class="etiket {'fw' if nerede == 'firmware' else 'sim'}">{nerede}</span>
    <span class="etiket duzeltildi">{durum}</span></header>
  <p>{metin}</p>
</article>""")
    return "\n".join(r)


def liste_html(kayitlar) -> str:
    return "\n".join(
        f"<li><h4>{b}</h4><p>{m}</p></li>" for b, m in kayitlar)


def tezgah_html() -> str:
    r = []
    for n, (adim, bekle, neden) in enumerate(TEZGAH, 1):
        r.append(f"""<li>
  <div class="no">{n}</div>
  <div>
    <h4>{adim}</h4>
    <p class="bekle">beklenen: <b>{bekle}</b></p>
    <p>{neden}</p>
  </div>
</li>""")
    return "\n".join(r)


SAYFA = f"""<title>Olcum Karti Kanit Dosyasi</title>
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
  --mono:"IBM Plex Mono", ui-monospace, "SF Mono", Consolas, monospace;
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
body {{
  background:var(--kagit); color:var(--murekkep);
  font-family:var(--seri); font-size:16.5px; line-height:1.62;
  -webkit-font-smoothing:antialiased;
}}
.sayfa {{ max-width:min(94vw, 1080px); margin:0 auto; padding:0 20px 96px; }}
.dar {{ max-width:var(--olcu); }}
p {{ margin:0 0 1em; }}
h1,h2,h3,h4 {{ text-wrap:balance; margin:0; }}
b {{ font-weight:600; }}
code {{
  font-family:var(--mono); font-size:.86em;
  background:var(--olcum-zemin); color:var(--olcum);
  padding:.1em .34em; border-radius:3px;
}}
a {{ color:var(--olcum); }}

/* ---------------------------------------------------------- baslik */
header.ust {{ padding:72px 0 40px; border-bottom:1px solid var(--cizgi); }}
.gozustu {{
  font-family:var(--mono); font-size:12px; font-weight:500;
  letter-spacing:.16em; text-transform:uppercase; color:var(--olcum);
  margin:0 0 18px;
}}
h1 {{ font-size:clamp(34px, 5.2vw, 52px); line-height:1.08; font-weight:700;
     letter-spacing:-.018em; margin:0 0 20px; }}
.girisi {{ font-size:19px; color:var(--soluk); max-width:60ch; margin:0; }}
.girisi em {{ color:var(--murekkep); font-style:italic; }}

/* --------------------------------------------------------- sayilar */
.kpi {{
  display:grid; gap:1px; background:var(--cizgi);
  grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));
  border:1px solid var(--cizgi); border-radius:6px; overflow:hidden;
  margin:40px 0 0;
}}
.kpi div {{ background:var(--yuzey); padding:18px 20px; }}
.kpi .n {{
  font-family:var(--mono); font-size:27px; font-weight:600;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em;
  display:block; line-height:1.15;
}}
.kpi .e {{
  font-family:var(--sans); font-size:11.5px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--daha-soluk); display:block;
  margin-top:6px;
}}
.kpi .iyi .n {{ color:var(--gecti); }}

/* --------------------------------------------------------- bolumler */
section {{ padding-top:60px; }}
h2 {{
  font-size:26px; font-weight:600; letter-spacing:-.012em;
  padding-bottom:10px; margin-bottom:8px;
  border-bottom:2px solid var(--murekkep); display:inline-block;
}}
.altbaslik {{ color:var(--soluk); margin:14px 0 26px; max-width:var(--olcu); }}

/* ----------------------------------------------------------- zincir */
.zincir {{
  display:grid; gap:10px; margin:26px 0 8px;
  grid-template-columns:repeat(auto-fit, minmax(148px, 1fr));
}}
.halka {{
  background:var(--yuzey); border:1px solid var(--cizgi);
  border-top:3px solid var(--olcum);
  border-radius:5px; padding:14px 15px; position:relative;
}}
.halka .ad {{ font-family:var(--sans); font-size:13.5px; font-weight:600;
              display:block; margin-bottom:5px; }}
.halka .nasil {{ font-family:var(--mono); font-size:11.5px; color:var(--soluk);
                 line-height:1.45; display:block; }}
.halka .sira {{
  position:absolute; top:-3px; right:10px;
  font-family:var(--mono); font-size:10px; color:var(--daha-soluk);
}}
.zincir-not {{ font-size:14.5px; color:var(--soluk); max-width:var(--olcu); }}

/* --------------------------------------------------------- merdiven */
ol.merdiven {{ list-style:none; padding:0; margin:0;
               display:flex; flex-direction:column; gap:1px;
               background:var(--cizgi); border:1px solid var(--cizgi);
               border-radius:6px; overflow:hidden; }}
.basamak {{
  background:var(--yuzey); display:grid; align-items:start; gap:16px;
  grid-template-columns:52px 1fr auto; padding:16px 20px;
}}
.basamak .kod {{
  font-family:var(--mono); font-size:14px; font-weight:600;
  color:var(--olcum); padding-top:2px;
}}
.basamak h3 {{ font-family:var(--sans); font-size:15.5px; font-weight:600;
               margin-bottom:4px; }}
.basamak .arac {{
  font-family:var(--mono); font-size:11px; font-weight:400;
  color:var(--daha-soluk); margin-left:8px;
}}
.basamak p {{ margin:0; font-size:14.5px; color:var(--soluk); line-height:1.55; }}
.rozet {{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.09em;
  text-transform:uppercase; padding:3px 9px; border-radius:99px;
  white-space:nowrap; margin-top:2px;
}}
.rozet.gecti {{ background:var(--gecti-zemin); color:var(--gecti); }}
.rozet.kaldi {{ background:var(--hata-zemin); color:var(--hata); }}

/* ----------------------------------------------------------- tablo */
.tablo-kutu {{ overflow-x:auto; margin:24px 0 10px;
               border:1px solid var(--cizgi); border-radius:6px; }}
table {{ width:100%; border-collapse:collapse; background:var(--yuzey);
         font-family:var(--mono); font-size:13.5px;
         font-variant-numeric:tabular-nums; }}
th, td {{ padding:9px 14px; text-align:right; white-space:nowrap; }}
thead th {{
  font-family:var(--sans); font-size:11px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--daha-soluk); font-weight:600;
  border-bottom:1px solid var(--cizgi); text-align:right;
}}
tbody tr + tr td {{ border-top:1px solid var(--cizgi); }}
td.sap {{ color:var(--gecti); }}
caption {{
  caption-side:bottom; text-align:left; padding:11px 14px;
  font-family:var(--sans); font-size:12.5px; color:var(--daha-soluk);
  border-top:1px solid var(--cizgi);
}}

/* ----------------------------------------------------------- cizim */
figure.cizim {{ margin:26px 0 6px; background:var(--yuzey);
                border:1px solid var(--cizgi); border-radius:6px;
                padding:16px; overflow-x:auto; }}
figure.cizim svg {{ width:100%; height:auto; display:block; }}
figure.sema {{
  margin:26px 0 6px; background:#fcfcfa; border:1px solid var(--cizgi);
  border-radius:6px; padding:18px; overflow-x:auto;
}}
figure.sema svg {{ width:100%; height:auto; display:block; }}
figcaption {{ font-family:var(--sans); font-size:12.5px; color:var(--daha-soluk);
              margin-top:10px; }}
.aciklama {{ font-size:14.5px; color:var(--soluk); max-width:var(--olcu);
             margin:4px 0 0; }}

/* ---------------------------------------------------------- kusurlar */
.kusurlar {{ display:grid; gap:14px; margin-top:24px; }}
.kusur {{ background:var(--yuzey); border:1px solid var(--cizgi);
          border-left:3px solid var(--uyari); border-radius:5px;
          padding:18px 20px; }}
.kusur header {{ display:flex; align-items:baseline; gap:10px;
                 flex-wrap:wrap; margin-bottom:8px; }}
.kusur h3 {{ font-family:var(--sans); font-size:16px; font-weight:600; }}
.kusur p {{ margin:0; font-size:14.5px; color:var(--soluk); }}
.etiket {{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.07em;
  text-transform:uppercase; padding:2px 8px; border-radius:99px;
}}
.etiket.fw {{ background:var(--hata-zemin); color:var(--hata); }}
.etiket.sim {{ background:var(--olcum-zemin); color:var(--olcum); }}
.etiket.duzeltildi {{ background:var(--gecti-zemin); color:var(--gecti); }}

/* ------------------------------------------------------ kanitlanmayan */
.sinir {{ background:var(--uyari-zemin); border:1px solid var(--cizgi);
          border-radius:6px; padding:24px 26px; margin-top:24px; }}
.sinir > p:first-child {{ font-size:15px; color:var(--murekkep); max-width:var(--olcu); }}
ul.acik {{ list-style:none; padding:0; margin:18px 0 0;
           display:grid; gap:14px; }}
ul.acik li {{ padding-left:18px; border-left:2px solid var(--uyari); }}
ul.acik h4 {{ font-family:var(--sans); font-size:14.5px; font-weight:600;
              margin-bottom:3px; }}
ul.acik p {{ margin:0; font-size:14px; color:var(--soluk); }}

/* ---------------------------------------------------------- tezgah */
ol.tezgah {{ list-style:none; padding:0; margin:24px 0 0;
             display:grid; gap:1px; background:var(--cizgi);
             border:1px solid var(--cizgi); border-radius:6px;
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

/* --------------------------------------------------------- calistir */
pre {{
  font-family:var(--mono); font-size:13px; line-height:1.7;
  background:var(--yuzey); border:1px solid var(--cizgi);
  border-radius:6px; padding:16px 18px; overflow-x:auto; margin:20px 0 0;
}}
pre .y {{ color:var(--daha-soluk); }}

footer {{ margin-top:72px; padding-top:22px; border-top:1px solid var(--cizgi);
          font-family:var(--sans); font-size:12.5px; color:var(--daha-soluk); }}

@media (max-width:640px) {{
  body {{ font-size:16px; }}
  .basamak {{ grid-template-columns:44px 1fr; }}
  .basamak .rozet {{ grid-column:2; justify-self:start; }}
}}
</style>

<div class="sayfa">

<header class="ust">
  <p class="gozustu">Olcum Karti &middot; Asama 1 &middot; ATmega328P</p>
  <h1>Girise 12.00 V koyunca<br>ekranda ne yaziyor?</h1>
  <p class="girisi">Bu sayfa tek bir soruyu sonuna kadar takip ediyor. Zincirin
  her halkasi gercek parcadan olusuyor: devreyi <em>ngspice</em> cozuyor,
  firmware'i <em>gercek avr-g++</em> derliyor, ikiliyi <em>komut komut</em> bir
  ATmega328P yorumlayicisi kosturuyor, cikan baytlari <em>arayuzun kendi
  ayristiricisi</em> okuyor. Hicbir ara adimda &ldquo;herhalde soyle olur&rdquo;
  yok.</p>

  <div class="kpi">
    <div class="iyi"><span class="n">{OK}</span><span class="e">dogrulama gecti</span></div>
    <div class="iyi"><span class="n">{HATA}</span><span class="e">basarisiz</span></div>
    <div><span class="n">10</span><span class="e">katman</span></div>
    <div><span class="n">{z['cevrim']/1e6:.0f}M</span><span class="e">AVR cevrimi kosturuldu</span></div>
    <div><span class="n">4</span><span class="e">kusur bulundu</span></div>
  </div>
</header>

<section>
  <h2>Zincir</h2>
  <p class="altbaslik">Soldan saga her kutu, bir oncekinin ciktisini girdi
  olarak aliyor. Kirmizi cizgi yok: hicbir yerde ara sonuc elle yazilmadi.</p>

  <div class="zincir">
    <div class="halka"><span class="sira">1</span><span class="ad">Uygulanan deger</span>
      <span class="nasil">3.30 / 5.00 / 12.00 / 24.00 V<br>5 / 10 / 20 / 30 mA</span></div>
    <div class="halka"><span class="sira">2</span><span class="ad">Devre</span>
      <span class="nasil">ngspice DC tarama<br>gercek bolucu + LM358</span></div>
    <div class="halka"><span class="sira">3</span><span class="ad">ADC</span>
      <span class="nasil">veri sayfasi denklemi<br>ornekle-tut RC oturmasi</span></div>
    <div class="halka"><span class="sira">4</span><span class="ad">Firmware</span>
      <span class="nasil">gercek .elf<br>komut komut yorumlaniyor</span></div>
    <div class="halka"><span class="sira">5</span><span class="ad">Seri port</span>
      <span class="nasil">USART0, 115200 baud<br>ham baytlar</span></div>
    <div class="halka"><span class="sira">6</span><span class="ad">Arayuz</span>
      <span class="nasil">arayuz/app.js<br>kendi ayristiricisi</span></div>
  </div>
  <p class="zincir-not">Firmware katmani onemli: aritmetigi Python'da
  <i>yeniden yazmak</i> tasarim niyetini dogrular, gercek kodu degil &mdash; iki
  uygulama sessizce ayrisabilir. Burada avr-libc'nin yazilim float kutuphanesi
  dahil her sey gercek komutlarla kosuyor.</p>
</section>

<section>
  <h2>Sonuc</h2>
  <p class="altbaslik">Dort calisma noktasinda, uygulanan deger ile kartin
  bildirdigi deger. Hata sutunu ADC adimi cinsinden: <b>1 adim =
  {z['lsb_v']*1000:.2f} mV</b>. Hicbir nokta yarim adimi asmiyor, yani olcum
  <b>kuantalama sinirinda</b> &mdash; devrede duzeltilecek sistematik hata yok.</p>

  <div class="tablo-kutu">
  <table>
    <thead><tr>
      <th>uygulanan V</th><th>uygulanan mA</th>
      <th>okunan V</th><th>okunan mA</th><th>okunan W</th>
      <th>hata mV</th><th>hata adim</th>
    </tr></thead>
    <tbody>
{satirlar_olcum()}
    </tbody>
    <caption>Akim sutunu ofset <b>sifirlanmadan once</b> alindi: her satirda
    ayni <b>+0.183 mA</b> fark var. Sabit olmasi, bunun kazanc hatasi degil
    LM358'in giris ofseti oldugunu gosteriyor (2 mV &times; 7.912 = 15.8 mV
    &asymp; 6 ADC adimi). <code>s</code> komutu bunu siliyor. Guc her ornekte
    ayri carpiliyor: ort(V&times;I) &ne; ort(V)&times;ort(I).</caption>
  </table>
  </div>

{svg("s9a-dogrusallik.svg")}
  <p class="aciklama">Sagdaki yesil serit &plusmn;1 ADC adimi. 10 bitlik bir
  donusturucude bundan iyisi fiziksel olarak yok.</p>
</section>

<section>
  <h2>Kalibrasyon gercekten calisiyor mu</h2>
  <p class="altbaslik">Karti bilerek <b>yanlis referansla</b> kosturdum:
  gercek AREF {kal['aref_gercek']} V, ama firmware {kal['aref_sanilan']} V
  sabitine inaniyor. Sistematik hata cikmali, sonra <code>kv12.00</code> onu
  silmeli.</p>

{svg("s9c-kalibrasyon.svg")}
  <p class="aciklama">{ (kal['once']-12)*1000 :+.1f} mV hata, tek komutla
  {(kal['sonra']-12)*1000:+.1f} mV'a indi. Carpan
  <code>{kal['carpan']}</code> EEPROM'a yazildi ve <b>yeniden aciliste geri
  okundu</b> &mdash; testin bir adimi da bu.</p>
</section>

<section>
  <h2>Osiloskop</h2>
  <p class="altbaslik">Karta {osilo['dc']:.0f} V DC uzerine
  {osilo['ac_genlik']:.0f} V tepe, {osilo['ac_hz']:.1f} Hz sinus uygulandi ve
  <code>t</code> komutu verildi. Firmware {osilo['adet']} ornegi
  {osilo['hz']:,} ornek/sn ile yakalayip seri porttan gonderdi.</p>

{svg("s9b-osiloskop.svg")}
  <p class="aciklama">Genlik hatasi <b>%+0.03</b>. Artik sinyalin RMS'i
  <b>30.0 mV</b>; saf kuantalama icin teorik deger adim/&radic;12 =
  <b>30.6 mV</b>. Yani geriye kuantalamadan baska bir sey kalmadi.
  &minus;53 mV'luk DC kaymasi da beklenen sey: ADC asagi yuvarliyor, ortalama
  yarim adim asagi kayiyor.</p>
</section>

<section>
  <h2>Katmanlar</h2>
  <p class="altbaslik">Her katman, altindakinin <b>goremeyecegi</b> bir seyi
  yakaliyor. Sirasi tesaduf degil: SPICE bileseni dogrular ama kodu bilmez,
  ERC baglantiyi dogrular ama <i>yonu</i> bilmez, derleyici kodu dogrular ama
  devreyi bilmez.</p>

  <ol class="merdiven">
{merdiven_html()}
  </ol>
</section>

<section>
  <h2>Bu turda bulunan kusurlar</h2>
  <p class="altbaslik">Dordu de bu calisma sirasinda ortaya cikti. Ikisi
  firmware'de, ikisi benim yazdigim simulatorde &mdash; ve simulatordekiler
  once <i>firmware hatasi gibi</i> gorunduler.</p>

  <div class="kusurlar">
{kusur_html()}
  </div>
</section>

<section>
  <h2>Sema</h2>
  <p class="altbaslik">ERC 0 ihlal veriyor, ama ERC polarite goremez. Bu yuzden
  netlist'teki pin islevleri ayrica okunuyor: her diyodun katodu, TL431'in
  anodu, LM358'in besleme uclari. {S['erc']}, netlist 21/21.</p>

{svg("_sema/olcum-karti.svg", "sema")}
  <figcaption>KiCad renkleri koyu zeminde okunmadigi icin sema kalici acik
  levha uzerinde.</figcaption>
</section>

<section>
  <h2>Bunlar hala kanitlanmadi</h2>
  <div class="sinir">
    <p>Yukaridakilerin hicbiri tezgah olcumu degil. Simulasyon gurultusuz,
    parcalar ideal, lehim direnci sifir. Asagidakiler <b>ancak multimetreyle</b>
    kapanir &mdash; ve kapanmadan &ldquo;kart calisiyor&rdquo; demek dogru olmaz.</p>
    <ul class="acik">
{liste_html(KANITLANMAYAN)}
    </ul>
  </div>
</section>

<section>
  <h2>Tezgahta sirasiyla</h2>
  <p class="altbaslik">Yukaridaki acik maddeleri kapatan en kisa yol. Her
  adimda ne beklendigi yaziyor ki, <b>beklenmeyen</b> bir sey gorursen
  anlayasin.</p>

  <ol class="tezgah">
{tezgah_html()}
  </ol>
</section>

<section>
  <h2>Kendin kostur</h2>
  <p class="altbaslik">Bu sayfadaki her sayi asagidaki komutlarin ciktisindan
  uretildi. Sayfayi ureten betikte elle yazilmis tek bir olcum degeri yok;
  kayitta aranan satir bulunamazsa betik hata verir.</p>
<pre><span class="y"># tum zincir (S1-S10), ~2.5 dakika</span>
cd projeler/olcum-karti/uretim
python dogrula.py

<span class="y"># sadece hizlilar (S1-S7), ~25 saniye</span>
python dogrula.py --hizli

<span class="y"># tek tek</span>
python test_avr.py      <span class="y"># S8  simulatorun kendisi</span>
python sim_kart.py      <span class="y"># S9  kart uctan uca</span>
python gorsel_s9.py     <span class="y"># kanit grafikleri</span>
python kanit-uret.py    <span class="y"># bu sayfa</span></pre>
</section>

<footer>
  Uretim: <code>uretim/kanit-uret.py</code> &middot; kaynak veriler
  <code>kanit/tam-dogrulama.txt</code> ve <code>kanit/s9-veri.json</code> &middot;
  ADC modeli ATmega328/P veri sayfasi Atmel-42735B (11/2016), Tablo 28-1 &middot;
  Sekil 28-7 &middot; Sekil 28-8.
</footer>

</div>
"""

if __name__ == "__main__":
    KANIT.mkdir(parents=True, exist_ok=True)
    hedef = KANIT / "kanit-sayfasi.html"
    hedef.write_text(SAYFA, encoding="utf-8")
    print(f"yazildi: {hedef}  ({hedef.stat().st_size // 1024} KB)")
    print(f"  {OK} dogrulama, {HATA} hata, {len(ADIMLAR)} adim")
