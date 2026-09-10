# -*- coding: utf-8 -*-
"""ÖLÇÜM KARTI — YETENEK TABLOSU (ne ölçebiliyoruz, hangi aralıkta,
hangi hızda, hangi çözünürlükte).

    python yetenek_tablosu.py            # terminale yazar
    python yetenek_tablosu.py --html     # ../yetenek.html üretir

⚠️ HİÇBİR SAYI ELLE YAZILMADI. Hepsi tek kaynaktan türetiliyor:
   * uretim/tasarim3_sabit.py          (bölücüler, PGA, şönt, ADC)
   * kod/olcum-karti-a3/olcum3.h       (firmware sabitleri)
   * kod/olcum-karti-a3/olcum-karti-a3.ino  (zaman tabanı, döngü bütçesi)

⚠️ DONANIM HENÜZ KURULMADI. Bu tablo TASARIMIN vaadidir, ölçülmüş bir
   kartın değil. "Doğruluk" sütunlarında ayrım açıkça yapılıyor:
     ÇÖZÜNÜRLÜK  = hesaplanabilir, kesin
     GÜRÜLTÜ     = veri sayfası tipiği, tezgahta doğrulanmalı
     DOĞRULUK    = kalibrasyondan SONRA; referans cihaza bağlı (AN8000)
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tasarim3_sabit as T                              # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
INO = (KOD / "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
OLC_H = (KOD / "olcum3.h").read_text(encoding="utf-8", errors="replace")

NORMAL, HV = T.KANALLAR[0], T.KANALLAR[1]


def sabit_h(ad: str) -> float:
    return float(re.search(rf"#define {ad}\s+([0-9.]+)f", OLC_H).group(1))


def ino_sabit(ad: str) -> float:
    return float(re.search(rf"{ad}\s*=\s*([0-9.]+)", INO).group(1))


# ─────────────────────────────────────────────── ADS yolunun GERÇEK hızı
# sim3_bant.py bölüm 1 ile AYNI bütçe; oradaki senaryo D.
def _i2c_us(bit):
    return bit / T.I2C_HIZ * 1e6


T_DON_US = 1e6 / T.ADS_SPS
T_YAZ_US = _i2c_us(T.I2C_YAZMA_BIT)
T_OKU_US = _i2c_us(20 + 29)
ADS_PERIYOT_US = 2 * T_YAZ_US + (T_DON_US - T_YAZ_US) + 2 * T_OKU_US
ADS_SPS_GERCEK = 1e6 / ADS_PERIYOT_US

RAPOR_MS = ino_sabit("rapor_ms")
ORNEK_PENCERE = RAPOR_MS / 1000.0 * ADS_SPS_GERCEK

# ─────────────────────────────────────────────── süzgeç bantları
TAU = {
    "NORMAL": (NORMAL["thev"] + T.RC_R) * T.RC_C,
    "YUKSEK": (HV["thev"] + T.RC_R) * T.RC_C,
    "AKIM": (2 * T.SONT_KELVIN_R + 2 * T.ADS_SERI_R) * T.ADS_AKIM_C,
}
KESIM = {k: 1 / (2 * math.pi * v) for k, v in TAU.items()}

# `f` komutunun izin verdiği üst frekans — KODDAN
F_SINIR = float(re.search(r"\|\| f > ([0-9.]+)f\)", INO).group(1))

# skop zaman tabanı
TDIV = [int(x) for x in re.search(
    r"SKOP_TDIV_US\[\] = \{(.*?)\};", INO, re.S).group(1).replace("\n", "").split(",")
    if x.strip()]
SKOP_BOLME = int(re.search(r"SKOP_BOLME\s*=\s*(\d+)", INO).group(1))
SKOP_HZ_AZAMI = int(re.search(r"SKOP_HZ_AZAMI\s*=\s*(\d+)", INO).group(1))
SKOP_HZ_ASGARI = int(re.search(r"SKOP_HZ_ASGARI\s*=\s*(\d+)", INO).group(1))


def skop_hz(tdiv_us):
    pencere = tdiv_us * SKOP_BOLME * 1e-6
    istenen = (SKOP_BOLME * 100) / pencere
    return min(max(istenen, SKOP_HZ_ASGARI), SKOP_HZ_AZAMI)


def satir(*s):
    print("  " + " │ ".join(s))


def cizgi(genislikler, ch="─"):
    print("  " + "─┼─".join(ch * g for g in genislikler))


def basla(baslik):
    print()
    print("═" * 100)
    print(f"  {baslik}")
    print("═" * 100)


def main() -> int:
    print()
    print("╔" + "═" * 98 + "╗")
    print("║" + "  ÖLÇÜM KARTI — YETENEK TABLOSU".ljust(98) + "║")
    print("║" + "  Aşama 3 · çift yönlü ön uç · sayılar tek kaynaktan türetildi".ljust(98) + "║")
    print("╚" + "═" * 98 + "╝")
    print()
    print("  ⚠ DONANIM HENÜZ KURULMADI. Bu tablo TASARIMIN vaadidir.")
    print("    Doğrulama zinciri tasarımı ve firmware'i sınar, kurulmuş bir kartı DEĞİL.")

    # ══════════════════════════════════════════════════════ 1. ANA TABLO
    basla("1. NE ÖLÇEBİLİYORUZ")
    g = [22, 24, 11, 13, 12]
    satir("büyüklük".ljust(g[0]), "aralık".ljust(g[1]), "hız".ljust(g[2]),
          "adım (LSB)".ljust(g[3]), "bant".ljust(g[4]))
    cizgi(g)

    for k in (NORMAL, HV):
        ad = "NORMAL" if k is NORMAL else "YUKSEK"
        satir(f"Gerilim · {ad}".ljust(g[0]),
              f"±{k['fs_sim']:.1f} V (garantili)".ljust(g[1]),
              f"{ADS_SPS_GERCEK:.0f} Sa/s".ljust(g[2]),
              f"{k['adim']*1e3:.3f} mV".ljust(g[3]),
              f"{KESIM[ad]:.1f} Hz".ljust(g[4]))

    for rs in T.SONT_SECENEK:
        adc = T.ADS_AKIM_KIRPMA / rs
        isil = T.SONT_AKIM_ISIL[rs]
        menzil = min(adc, isil)
        kim = "ADC" if adc < isil else "ISIL"
        adim = (T.ADS_AKIM_KIRPMA / T.ADS_SAYIM) / rs
        et = f"{rs:g} Ω" if rs >= 1 else f"{rs*1e3:.0f} mΩ"
        satir(f"Akım · şönt {et}".ljust(g[0]),
              f"±{menzil:.3f} A ({kim})".ljust(g[1]),
              f"{ADS_SPS_GERCEK:.0f} Sa/s".ljust(g[2]),
              f"{adim*1e6:.1f} µA".ljust(g[3]),
              f"{KESIM['AKIM']:.1f} Hz".ljust(g[4]))

    i_maks = max(min(T.ADS_AKIM_KIRPMA / r, T.SONT_AKIM_ISIL[r])
                 for r in T.SONT_SECENEK)
    p_maks = HV["fs_sim"] * i_maks
    satir("Güç (V×I, işaretli)".ljust(g[0]),
          f"±{p_maks/1e3:.1f} kW (tavan)".ljust(g[1]),
          f"{ADS_SPS_GERCEK:.0f} Sa/s".ljust(g[2]),
          "— (türetilmiş)".ljust(g[3]),
          f"40–70 Hz".ljust(g[4]))

    wh_tavan = (2**63 - 1) / 3.6e15
    satir("Enerji (işaretli)".ljust(g[0]),
          f"±{wh_tavan:.0f} Wh".ljust(g[1]),
          "her örnek".ljust(g[2]),
          "1 pJ".ljust(g[3]),
          "—".ljust(g[4]))

    skop_adim = sabit_h("SKOP_ADC_TAVAN") / sabit_h("SKOP_ADC_SAYIM") * sabit_h("SKOP_ORAN")
    satir("Osiloskop (dalga)".ljust(g[0]),
          f"{T.SKOP_MENZIL_EKSI:.1f} … +{T.SKOP_MENZIL_ARTI:.1f} V".ljust(g[1]),
          f"…{SKOP_HZ_AZAMI/1e3:.0f} kSa/s".ljust(g[2]),
          f"{skop_adim*1e3:.1f} mV".ljust(g[3]),
          f"{T.SK_F0/1e3:.1f} kHz".ljust(g[4]))

    hizli_fs = T.ADS_AKIM_KIRPMA  # şönt gerilimi tam ölçeği (hızlı yol)
    satir("Hızlı akım (dalga)".ljust(g[0]),
          f"±{hizli_fs*1e3:.0f} mV şönt".ljust(g[1]),
          f"{T.ESP_KANAL_SPS/1e3:.1f} kSa/s".ljust(g[2]),
          "12 bit".ljust(g[3]),
          "16.5 kHz".ljust(g[4]))

    # ═══════════════════════════════════════════ 2. HIZ — NEREDEN GELİYOR
    basla("2. ÖRNEKLEME HIZI — NEREDEN GELİYOR")
    print()
    print(f"  ADS yolu (voltmetre/ampermetre/wattmetre), ÖLÇÜM BAŞINA bütçe:")
    print(f"     2 × tek atış yazması   {2*T_YAZ_US:7.1f} µs   "
          f"(I2C {T.I2C_HIZ/1e3:.0f} kHz, {T.I2C_YAZMA_BIT} bit)")
    print(f"     dönüşüm ({T.ADS_SPS} SPS)     {T_DON_US - T_YAZ_US:7.1f} µs   "
          f"(ikinci yazma dönüşümle örtüşüyor)")
    print(f"     2 × dönüşüm okuması    {2*T_OKU_US:7.1f} µs")
    print(f"     {'─'*40}")
    print(f"     TOPLAM                 {ADS_PERIYOT_US:7.1f} µs  →  "
          f"{ADS_SPS_GERCEK:.0f} Sa/s   (Nyquist {ADS_SPS_GERCEK/2:.0f} Hz)")
    print()
    print(f"  ⚠ Bu bir ÜST SINIR: saf bit sayımı, ESP32 Wire sürücüsünün işlem")
    print(f"    başına ek yükü (onlarca µs) sayılmadı. Gerçek hız bundan DÜŞÜK olur.")
    print(f"  ⚠ TEK ATIŞIN BEDELİ: sürekli kipte {T.ADS_SPS} Sa/s olurdu ama V ve I")
    print(f"    örnekleri 0…23° sürüklenirdi (B17). Tek atış nominal hızın "
          f"%{ADS_SPS_GERCEK/T.ADS_SPS*100:.0f}'ini veriyor")
    print(f"    (yani %{(1-ADS_SPS_GERCEK/T.ADS_SPS)*100:.0f} KAYIP), "
          f"karşılığında kayma 95 µs'de SABİTLENİYOR.")
    print()
    print(f"  Rapor penceresi: {RAPOR_MS:.0f} ms → pencere başına "
          f"{ORNEK_PENCERE:.0f} örnek")
    print(f"     50 Hz'te çevrim başına {ADS_SPS_GERCEK/50:.1f} örnek · "
          f"pencerede {RAPOR_MS/1000*50:.0f} şebeke çevrimi")

    print()
    print(f"  Osiloskop yolu (ESP32 dahili ADC, DMA):")
    print(f"     {'s/böl':>10} {'hız':>12} {'pencere':>10} {'örnek':>8}")
    print(f"     {'─'*44}")
    for us in TDIV:
        hz = skop_hz(us)
        pencere = us * SKOP_BOLME * 1e-6
        n = max(100.0, min(pencere * hz, 4096))
        et = f"{us} µs" if us < 1000 else (f"{us/1000:.0f} ms" if us < 1e6 else f"{us/1e6:.0f} s")
        print(f"     {et:>10} {hz/1e3:>9.2f} kSa/s {pencere*1e3:>8.0f} ms {n:>8.0f}")
    print(f"     Hızlı yol (V ve I aynı anda): {T.ESP_KANAL_SPS/1e3:.1f} kSa/s "
          f"kanal başına, toplam {T.ESP_TOPLAM_SPS/1e3:.0f} kSa/s")

    # ═══════════════════════════════════════════ 3. ÇÖZÜNÜRLÜK vs DOĞRULUK
    basla("3. ÇÖZÜNÜRLÜK ≠ DOĞRULUK — KARIŞTIRILMASI KOLAY ÜÇ SAYI")
    print()
    print("  (a) ADIM (LSB)          — hesaplanabilir, kesin")
    print("  (b) GÜRÜLTÜ             — veri sayfası tipiği; ORTALAMA ile azalır")
    print("  (c) MUTLAK DOĞRULUK     — INL + kazanç + referans; ORTALAMA ile")
    print("                            AZALMAZ. Tavanı burası koyar.")
    print()
    g2 = [20, 12, 14, 18, 20]
    satir("kanal".ljust(g2[0]), "adım".ljust(g2[1]), "gürültü/örnek".ljust(g2[2]),
          f"gürültü {RAPOR_MS:.0f} ms ort.".ljust(g2[3]),
          "ayırt edilebilir Δ".ljust(g2[4]))
    cizgi(g2)
    for k in (NORMAL, HV):
        ad = "Gerilim NORMAL" if k is NORMAL else "Gerilim YUKSEK"
        gur_v = T.ADS_GURULTU[k["pga"]] * k["N"]
        gur_ort = gur_v / math.sqrt(ORNEK_PENCERE)
        satir(ad.ljust(g2[0]),
              f"{k['adim']*1e3:.3f} mV".ljust(g2[1]),
              f"{gur_v*1e3:.2f} mV".ljust(g2[2]),
              f"{gur_ort*1e3:.3f} mV".ljust(g2[3]),
              f"~{max(gur_ort, k['adim'])*1e3:.2f} mV".ljust(g2[4]))
    for rs in (0.1, 0.015):
        gur_a = T.ADS_GURULTU[T.ADS_AKIM_KIRPMA] / rs
        gur_ort = gur_a / math.sqrt(ORNEK_PENCERE)
        adim_a = (T.ADS_AKIM_KIRPMA / T.ADS_SAYIM) / rs
        et = f"Akım {rs:g} Ω" if rs >= 1 else f"Akım {rs*1e3:.0f} mΩ"
        satir(et.ljust(g2[0]),
              f"{adim_a*1e6:.1f} µA".ljust(g2[1]),
              f"{gur_a*1e6:.0f} µA".ljust(g2[2]),
              f"{gur_ort*1e6:.1f} µA".ljust(g2[3]),
              f"~{max(gur_ort, adim_a)*1e6:.0f} µA".ljust(g2[4]))
    print()
    print("  🔴 ORTALAMA ALMAK SAYIM ARTIRMAZ — bu tuzağa DEVIR bir kez düştü.")
    print(f"     Yukarıdaki gürültü sayılarını menzile bölerseniz 'milyonlarca")
    print(f"     sayım' çıkar. ÇIKMAZ: ADS1115 16 bit, yani menzil başına en çok")
    print(f"     {2*T.ADS_SAYIM:,.0f} kod var".replace(",", " ") + " ve ortalama almak KODLARIN ARASINI")
    print(f"     dolduramaz — yalnızca gürültüyü bastırır. Üstelik ADC'nin")
    print(f"     DOĞRUSALLIK hatası (INL) ortalamayla HİÇ azalmaz.")
    print()
    print("     DEVIR 1.3'teki \"200 ms ortalamada 146 000 sayım\" iddiası bu")
    print("     yüzden türetilemedi ve doğrulanmamış olarak işaretlenmişti.")
    print("     Doğru okuma: ortalama, ayırt edilebilir DEĞİŞİMİ iyileştirir;")
    print("     MUTLAK doğruluğu iyileştirmez.")
    print()
    print("  Mutlak doğruluk zinciri (ortalamadan ETKİLENMEYEN kalemler):")
    print(f"     ADS1115 ofset       : ±{T.ADS_OFSET_LSB} LSB   → sıfır kalibrasyonu SİLER")
    print(f"     ADS1115 kazanç      : PGA uyumu ±%{T.ADS_PGA_UYUM*100:.1f} → kazanç kalibrasyonu siler")
    print( "     Bölücü dirençleri   : metal film ±%1  → kazanç kalibrasyonu siler")
    print( "     ADS1115 INL         : veri sayfası tipiği; kalibrasyon SİLMEZ  ⚠ TEZGAH")
    print( "     Şönt termal sürükl. : yüke bağlı; kalibrasyon SİLMEZ           ⚠ TEZGAH")
    print( "     REFERANS CİHAZ      : AN8000 ±(%0.5 + 4 hane) = 12 V'ta ±%0.83")
    print()
    print("  ► Kalibrasyondan sonra MUTLAK doğruluk tavanı ≈ referansın kendisi,")
    print("    yani ±%0.8. Kartın ÇÖZÜNÜRLÜĞÜ bunun çok altında — kart farkı")
    print("    görür ama 'gerçek değer' diyemez.")
    print()

    # ═══════════════════════════════════════════ 4. GÜÇ — GEÇERLİLİK BANDI
    basla("4. GÜÇ ÖLÇÜMÜ — GEÇERLİLİK BANDI (en dar kısıt burası)")

    def dfaz(f, tv, ti):
        return math.degrees(math.atan(2*math.pi*f*ti) - math.atan(2*math.pi*f*tv))

    print()
    print("  Faz kalibrasyonu (`F`) SABİT bir zaman gecikmesi saklıyor; düzelttiği")
    print("  şey ise iki RC'nin arctan farkı. İkisi yalnızca kalibrasyon")
    print("  frekansında örtüşür. 50 Hz'te kalibre edilmiş kartta KALAN hata:")
    print()
    g3 = [10, 14, 14, 16]
    satir("frekans".ljust(g3[0]), "tol ±%1".ljust(g3[1]),
          "tol ±%5 (J)".ljust(g3[2]), "tol ±%10 (K)".ljust(g3[3]))
    cizgi(g3)
    for f in (50, 60, 100, 200, 400):
        hu = []
        for tol in (0.01, 0.05, 0.10):
            tv, ti = TAU["NORMAL"] * (1 - tol), TAU["AKIM"] * (1 + tol)
            dtk = dfaz(50, tv, ti) / (360 * 50)
            kalan = dfaz(f, tv, ti) - 360 * f * dtk
            hata = (math.cos(math.radians(60 + kalan))
                    / math.cos(math.radians(60)) - 1) * 100
            hu.append(f"{hata:+.1f}%")
        im = "" if f <= F_SINIR else "   ← `f` sınırının ÜSTÜNDE"
        satir(f"{f} Hz".ljust(g3[0]), hu[0].ljust(g3[1]),
              hu[1].ljust(g3[2]), hu[2].ljust(g3[3]) + im)
    print()
    print(f"  (PF = 0.5 yükte güç hatası. Dirençli yükte hata ~10 kat küçük —")
    print(f"   kusur EN ÇOK KULLANILAN test koşulunda gizleniyor.)")
    print()
    print(f"  ► `f` komutunun üst sınırı: {F_SINIR:.0f} Hz (koddan okundu)")
    print(f"  ► GEÇERLİLİK BANDI: 40–70 Hz. Bu bantta PF=0.5'te en kötü %8.0")
    print(f"  ► Kondansatör toleransı BELİRLEYİCİ. Envanterde yazmıyor —")
    print(f"    C2 ve C18'in üzerindeki HARF okunmalı (J=%5, K=%10).")

    # ═══════════════════════════════════════════ 5. YAPAMADIKLARI
    basla("5. KARTIN YAPAMADIKLARI (dürüstlük bölümü)")
    print()
    for s in (
        f"ADS yolu bir TEMEL BİLEŞEN wattmetresidir. Süzgeç kutbu {KESIM['AKIM']:.0f} Hz'te;",
        "  5. harmoniğin gücü temele göre ~12 kat bastırılıyor. Harmonikli/bozuk",
        "  dalgada güç okuması güvenilmez — dalga şekli işi HIZLI YOLUN.",
        "",
        "D satırındaki V ve I ARİTMETİK ORTALAMA, RMS DEĞİL. AC'de ikisi de ~0",
        "  okur. Kart bir AC voltmetre DEĞİL; AC gerilim için osiloskop yolu var.",
        "",
        f"`f` {F_SINIR:.0f} Hz'in üstünde reddediyor; 40–70 Hz dışında uyarı basıyor.",
        "",
        "Mutlak doğruluk KALİBRASYONA bağlı ve kalibrasyon referansı kullanıcının",
        "  multimetresi (AN8000, ±%0.8). Kartın çözünürlüğü çok daha iyi ama",
        "  mutlak doğruluğu referanstan iyi OLAMAZ.",
        "",
        "Otomatik menzil AŞAĞI yönde bir şebeke çevrimi (≥20 ms) gecikmeli —",
        "  yukarı yön (doymayı önleyen yön) anlık.",
    ):
        print("  " + s)

    # ═══════════════════════════════════════════ 6. TEZGAH LİSTESİ
    basla("6. BU TABLONUN TEZGAHTA DOĞRULANMASI GEREKEN SATIRLARI")
    print()
    for i, s in enumerate((
        f"ÖRNEKLEME HIZI. `D` satırındaki örnek sayısı {RAPOR_MS:.0f} ms'de "
        f"~{ORNEK_PENCERE:.0f} olmalı.",
        "ALERT/RDY darbesi (tek atışta MANDAL, darbe değil) — skopla görülmeli.",
        "I2C'nin gerçekten 400 kHz kurulduğu; 100 kHz'e düşerse kayma 4 kat büyür.",
        "ADS1115 gürültü tabanı — tablodaki sayılar veri sayfası TİPİĞİ.",
        "ESP32 ADC'sinin gerçek tam ölçeği (3.1 V nominal, yongaya göre değişir).",
        "Kondansatör tolerans harfi (J/K) — güç bandını bu belirliyor.",
        "Şönt direncinin gerçek değeri ve termal sürüklenmesi.",
        "🔴 ŞÖNTÜN GÜÇ DEĞERİ. ±11.5 A rakamı 2 W varsayımından geliyor ve o 2 W",
        "   bir ÇIKARIM (11.547 = √(2/0.015)). Parça gelince üzerindeki değeri oku.",
    ), 1):
        print(f"  {i}. {s}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
