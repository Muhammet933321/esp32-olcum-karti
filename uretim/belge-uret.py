# -*- coding: utf-8 -*-
"""KULLANICI BELGELERINI URETIR  ->  ../BELGELER/*.html

    python belge-uret.py

Bu betik, kullanicinin GOZLE OKUYACAGI belgeleri uretiyor. Muhendislik
ayrintisi DEVIR.md'de; burasi "kart ne yapabiliyor" sorusunun cevabi.

⚠ HICBIR SAYI ELLE YAZILMADI. Hepsi tek kaynaktan geliyor:
    uretim/tasarim3_sabit.py           bolucular, PGA, sont, ADC
    kod/olcum-karti-a3/olcum3.h        firmware sabitleri
    kod/olcum-karti-a3/*.ino, *.h      zaman tabani, tampon, sinirlar
Grafiklerin verisi de HESAPLANIYOR — dekoratif cizim yok.

RENK PALETI: dataviz becerisinin dogrulanmis varsayilan paleti
(validate_palette.js ile sinandi: butun denetimler PASS).
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tasarim3_sabit as T                              # noqa: E402
import dogrula3 as D3                                   # noqa: E402
import belge_menu as MN                                 # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
HEDEF = KOK / "BELGELER"
INO = (KOD / "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
OLC_H = (KOD / "olcum3.h").read_text(encoding="utf-8", errors="replace")
PIL_H = (KOD / "pil_test.h").read_text(encoding="utf-8", errors="replace")

NORMAL, HV = T.KANALLAR[0], T.KANALLAR[1]


AG_H = (KOD / "ag.h").read_text(encoding="utf-8", errors="replace")
# LittleFS olculeri — `arayuz-uret.py`'nin uretttigi hazir JSON.
# Yoksa sayfa yine cikiyor ama olcu satirlari gizleniyor (elle sayi YOK).
_FS = BURASI / "_fs.json"
FS = (json.loads(_FS.read_text(encoding="utf-8")) if _FS.exists()
      else {"bolum_boyut": 0, "icerik_bayt": 0})
KOPRU_PY = (KOK / "kopru" / "kopru.py").read_text(encoding="utf-8",
                                                  errors="replace")


def h_sabit(ad):
    return float(re.search(rf"#define {ad}\s+([0-9.]+)f", OLC_H).group(1))


def h_metin(ad, kaynak=None):
    """String `#define` okur: `#define AG_MDNS "olcum"` -> `olcum`.

    `h_sabit` yalnizca `[0-9.]+f` yakaliyor; ag.h'nin degerleri metin.
    Bu okuyucu olmadan mDNS adi belgeye ELLE yazilirdi ve `ag.h`
    degistiginde sessizce ayrisirdi.
    """
    return re.search(rf'#define {ad}\s+"([^"]*)"',
                     kaynak if kaynak is not None else OLC_H).group(1)


def h_tamsayi(ad, kaynak=None):
    """Sayisal `#define` okur; `u`/`UL` sonekini yutar (AG_STA_BEKLE_MS)."""
    return int(re.search(rf"#define {ad}\s+([0-9]+)[uUlL]*",
                         kaynak if kaynak is not None else OLC_H).group(1))


def py_sabit(ad, kaynak):
    return int(re.search(rf"^{ad}\s*=\s*([0-9]+)", kaynak, re.M).group(1))


def ino_sayi(ad):
    # B27 A2: `rapor_ms` artik `= RAPOR_MS_VARSAYILAN;` — sag taraf bir
    # tanimlayiciysa #define'a BIR seviye inilir. Sayi bulamayip import
    # aninda patlamak yerine (zinciri B9'da kirdi) makroyu cozuyoruz.
    m = re.search(rf"{ad}\s*=\s*([A-Za-z_][A-Za-z0-9_]*|[0-9.]+)\s*;", INO)
    deger = m.group(1)
    if not re.fullmatch(r"[0-9.]+", deger):
        deger = re.search(rf"#define\s+{deger}\s+([0-9.]+)", INO).group(1)
    return float(deger)


# ── kartin gercek hizi (sim3_bant.py bolum 1 ile AYNI butce)
T_DON = 1e6 / T.ADS_SPS
T_YAZ = T.I2C_YAZMA_BIT / T.I2C_HIZ * 1e6
T_OKU = (20 + 29) / T.I2C_HIZ * 1e6
PERIYOT_US = 2 * T_YAZ + (T_DON - T_YAZ) + 2 * T_OKU
SPS = 1e6 / PERIYOT_US
RAPOR_MS = ino_sayi("rapor_ms")

TAU_V = (NORMAL["thev"] + T.RC_R) * T.RC_C
TAU_I = (2 * T.SONT_KELVIN_R + 2 * T.ADS_SERI_R) * T.ADS_AKIM_C
F_SINIR = float(re.search(r"\|\| f > ([0-9.]+)f\)", INO).group(1))
PIL_AZAMI_V = float(re.search(r"#define PIL_AZAMI_V\s+([0-9.]+)f", PIL_H).group(1))
SKOP_ADIM = h_sabit("SKOP_ADC_TAVAN") / h_sabit("SKOP_ADC_SAYIM") * h_sabit("SKOP_ORAN")
SKOP_TDIV = [int(x) for x in re.search(r"SKOP_TDIV_US\[\] = \{(.*?)\};",
                                       INO, re.S).group(1).replace("\n", "").split(",")
             if x.strip()]
SKOP_BOLME = int(re.search(r"SKOP_BOLME\s*=\s*(\d+)", INO).group(1))
SKOP_AZAMI = int(re.search(r"SKOP_HZ_AZAMI\s*=\s*(\d+)", INO).group(1))
SKOP_ASGARI = int(re.search(r"SKOP_HZ_ASGARI\s*=\s*(\d+)", INO).group(1))

# ═══════════════════════════════════════════════════ ORTAK STIL / SVG

# dataviz varsayilan paleti — validate_palette.js: ALL CHECKS PASS
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
S1D, S2D, S3D, S4D = "#3987e5", "#d95926", "#199e70", "#c98500"

STIL = """
:root{color-scheme:light dark;
  --yz:#fcfcfb; --yz2:#f4f3f0; --cizgi:#e2e0da;
  --m1:#0b0b0b; --m2:#52514e; --m3:#77756d;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
  --iyi:#0a7d3f; --uyari:#b25e00; --kotu:#b3261e;}
@media (prefers-color-scheme:dark){:root:not([data-tema="acik"]){
  --yz:#1a1a19; --yz2:#232322; --cizgi:#3a3a37;
  --m1:#ffffff; --m2:#c3c2b7; --m3:#9a988e;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  --iyi:#4ec27d; --uyari:#e0a350; --kotu:#f2837a;}}
*{box-sizing:border-box}
body{margin:0;background:var(--yz);color:var(--m1);
  font:16px/1.65 -apple-system,"Segoe UI",Roboto,sans-serif;}
.kutu{max-width:960px;margin:0 auto;padding:32px 22px 80px}
h1{font-size:30px;line-height:1.25;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:21px;margin:44px 0 4px;letter-spacing:-.01em;
   padding-top:18px;border-top:1px solid var(--cizgi)}
h3{font-size:16px;margin:26px 0 6px;color:var(--m2);
   text-transform:uppercase;letter-spacing:.06em;font-weight:600}
p{margin:10px 0}
.alt{color:var(--m2);font-size:15px;margin:0 0 26px}
.ust{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 22px;font-size:14px}
.ust a{color:var(--m2);text-decoration:none;padding:5px 11px;
  border:1px solid var(--cizgi);border-radius:99px}
.ust a:hover{color:var(--m1);border-color:var(--m3)}
.ust a.bu{background:var(--m1);color:var(--yz);border-color:var(--m1)}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:15px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--cizgi)}
th{font-size:12px;text-transform:uppercase;letter-spacing:.05em;
   color:var(--m3);font-weight:600}
td.s,th.s{text-align:right;font-variant-numeric:tabular-nums}
.kart{background:var(--yz2);border:1px solid var(--cizgi);
  border-radius:12px;padding:16px 18px;margin:14px 0}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:10px;margin:16px 0}
.kpi div{background:var(--yz2);border:1px solid var(--cizgi);
  border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:24px;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums}
.kpi span{font-size:12px;color:var(--m2);text-transform:uppercase;
  letter-spacing:.05em}
.uy{border-left:3px solid var(--uyari);background:var(--yz2);
  padding:12px 16px;margin:14px 0;border-radius:0 8px 8px 0;font-size:15px}
.ok{border-left:3px solid var(--iyi);background:var(--yz2);
  padding:12px 16px;margin:14px 0;border-radius:0 8px 8px 0;font-size:15px}
.no{border-left:3px solid var(--kotu);background:var(--yz2);
  padding:12px 16px;margin:14px 0;border-radius:0 8px 8px 0;font-size:15px}
figure{margin:22px 0}
figcaption{font-size:14px;color:var(--m2);margin-top:8px}
svg{max-width:100%;height:auto;display:block}
code{background:var(--yz2);padding:1px 6px;border-radius:5px;
  font:14px/1 ui-monospace,Consolas,monospace}
.kucuk{font-size:14px;color:var(--m2)}
.rozet{display:inline-block;font-size:12px;padding:2px 8px;border-radius:99px;
  background:var(--yz2);border:1px solid var(--cizgi);color:var(--m2)}
"""

# Gezinme seridi `belge_menu.py`'de — `kurulum3-uret.py` ile PAYLASILIYOR.
# Ikinci bir kopya tutulursa yeni sekme yalnizca birinde gorunur; B23.2'de
# tam olarak bu oldu (`4-kurulum.html` "Baglanma"yi gostermedi).
# `4-kurulum.html`'i bu betik URETMIYOR, o yuzden uretilen sayfa sayisi
# len(MENU) DEGIL — main() sayiyor.
MENU = MN.MENU


def sayfa(dosya, baslik, alt, govde):
    ust = MN.serit(dosya)
    html = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{baslik} — Ölçüm Kartı</title><style>{STIL}</style></head><body>
<div class="kutu">{ust}
<h1>{baslik}</h1><p class="alt">{alt}</p>
{govde}
<p class="kucuk" style="margin-top:60px;border-top:1px solid var(--cizgi);
 padding-top:14px">Bu sayfa <code>uretim/belge-uret.py</code> tarafından
 üretildi — buradaki her sayı tasarım dosyalarından hesaplanıyor, elle
 yazılmıyor. Donanım henüz kurulmadı; değerler tasarımın vaadidir.</p>
</div></body></html>"""
    (HEDEF / dosya).write_text(html, encoding="utf-8")
    return len(html)

import belge_grafik as G                              # noqa: E402
import belge_sayfa as P                               # noqa: E402
import belge_malzeme as M                             # noqa: E402


def main() -> int:
    HEDEF.mkdir(parents=True, exist_ok=True)
    i_maks = max(min(T.ADS_AKIM_KIRPMA / r, T.SONT_AKIM_ISIL[r])
                 for r in T.SONT_SECENEK)
    d = {
        "sps": SPS, "rapor_ms": RAPOR_MS,
        "ornek_pencere": RAPOR_MS / 1000.0 * SPS,
        "nv_fs": NORMAL["fs_sim"], "hv_fs": HV["fs_sim"],
        "i_maks": i_maks, "p_maks": HV["fs_sim"] * i_maks,
        "i_adim_100m": (T.ADS_AKIM_KIRPMA / T.ADS_SAYIM) / 0.1,
        "wh_tavan": (2 ** 63 - 1) / 3.6e15,
        "mah_tavan": (2 ** 63 - 1) / 3.6e12,
        "skop_adim": SKOP_ADIM, "skop_tdiv": SKOP_TDIV,
        "skop_bolme": SKOP_BOLME, "skop_azami": SKOP_AZAMI,
        "skop_asgari": SKOP_ASGARI,
        "skop_eksi": T.SKOP_MENZIL_EKSI, "skop_arti": T.SKOP_MENZIL_ARTI,
        "sk_f0": T.SK_F0, "f_sinir": F_SINIR,
        "pil_azami_v": PIL_AZAMI_V, "pil_akim": T.PIL_AKIM_SOGUTUCUSUZ,
        "dcir_ms": T.PIL_DCIR_DARBE_S * 1000,
        "tau_v": TAU_V, "tau_i": TAU_I, "t_yaz": T_YAZ,
        "gurultu_ort": T.ADS_GURULTU[NORMAL["pga"]] * NORMAL["N"]
                       / math.sqrt(RAPOR_MS / 1000.0 * SPS),
        # ── ag (B23.2) — hepsi kaynaktan, hicbiri elle
        "mdns": h_metin("AG_MDNS", AG_H),
        "ap_onek": re.search(r'"(OLCUM-KARTI-)%02X%02X"', AG_H).group(1),
        "sta_bekle_s": h_tamsayi("AG_STA_BEKLE_MS", AG_H) / 1000.0,
        "kart_port": int(re.search(r"WebServer sunucu\((\d+)\)", INO).group(1)),
        "kopru_port": py_sabit("PORT", KOPRU_PY),
        "kopru_yedek": py_sabit("YEDEK_PORT", KOPRU_PY),
        "ap_parola_n": int(re.search(r"ag_rastgele_parola\(p,\s*(\d+)\)",
                                     AG_H).group(1)),
        "fs_bolum": FS["bolum_boyut"], "fs_icerik": FS["icerik_bayt"],
        "sse_hz": 1000.0 / RAPOR_MS,
        "akis_azami": int(re.search(r"#define AKIS_AZAMI\s+(\d+)",
                                    INO).group(1)),
        "adim_sayisi": D3.ADIM_SAYISI,
        "hiz_kalem": [
            ("Wattmetre (V·I·W·mAh)", SPS, G.S1),
            ("Osiloskop — en hizli", SKOP_AZAMI, G.S3),
            ("Osiloskop — en yavas", SKOP_ASGARI, G.S3),
            ("Hizli akim (dalga sekli)", T.ESP_KANAL_SPS, G.S2),
            ("Pil testi egri kaydi", T.PIL_KAYIT_HZ, G.S4)],
    }
    n = 0
    sayfa_n = 0
    sayfa_n += 1
    n += sayfa("index.html", "Olcum Karti",
               "Voltmetre · ampermetre · wattmetre · enerji sayaci · "
               "osiloskop · pil testi", P.index(d))
    sayfa_n += 1
    n += sayfa("1-ne-yapabilir.html", "Ne yapabilir",
               "Kartin butun yetenekleri, ornek ekranlarla",
               P.ne_yapabilir(d, T, NORMAL, HV))
    sayfa_n += 1
    n += sayfa("2-olcumler.html", "Olcumler",
               "Neyi, ne kadar hassas, ne siklikla",
               P.olcumler(d, T, NORMAL, HV))
    sayfa_n += 1
    n += sayfa("3-pil-testi.html", "Pil kapasite testi",
               "Hangi pilleri, kac amperle, ne kadar surede",
               P.pil_testi(d, T))
    sayfa_n += 1
    n += sayfa("6-ag.html", "Baglanma",
               "Telefondan, bilgisayardan ya da ikisinden birden",
               P.ag(d, T))
    sayfa_n += 1
    n += sayfa("2-malzemeler.html", "Malzemeler",
               "Semadan uretiliyor, stok kaydiyla karsilastiriliyor",
               M.malzemeler(d))
    sayfa_n += 1
    n += sayfa("5-muhendislik.html", "Muhendislik",
               "Nasil calisiyor — istege bagli",
               P.muhendislik(d, T, NORMAL, HV))
    # ⚠ `index.html`'deki "Hangi belgeye bakmalayim" tablosu MENU'den
    # TURETILMIYOR, elle yaziliyor. Ikisi sessizce ayrisabilir — B23.2'de
    # yeni sayfa MENU'ye eklenip tabloya eklenmese hic fark edilmezdi.
    # Burasi o ayrismayi KIRMIZI yapiyor.
    # 🔴 Ilk yazimda TUM sayfaya bakiyordu ve iddia BOSTU: gezinme seridi
    # zaten her adresi iceriyor, yani denetim her zaman geciyordu
    # (mutasyonla olculdu — sahte bir MENU satiri eklendi, yesil kaldi).
    # Artik YALNIZCA "Hangi belgeye bakmalayim" tablosunun icine bakiyor.
    govde = (HEDEF / "index.html").read_text(encoding="utf-8")
    bas = govde.find("Hangi belgeye")
    tablo = govde[govde.find("<table>", bas):govde.find("</table>", bas)]
    if bas < 0 or not tablo:
        print("  KIRMIZI: index.html'de belge tablosu bulunamadi")
        return 1
    eksik = [d for d, _a in MENU
             if d != "index.html" and f'href="{d}"' not in tablo]
    if eksik:
        print(f"  KIRMIZI: MENU'de olup index tablosunda olmayan sayfa: "
              f"{', '.join(eksik)}")
        return 1
    print(f"BELGELER/ yazildi: {sayfa_n} sayfa, {n/1024:.0f} KB")
    print(f"  olcum hizi {SPS:.0f} Sa/s · skop adim {SKOP_ADIM*1e3:.1f} mV")
    print(f"  akim tavani {i_maks:.2f} A · pil siniri {PIL_AZAMI_V:.1f} V")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
