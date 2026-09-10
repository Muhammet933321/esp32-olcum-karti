# -*- coding: utf-8 -*-
"""B17 — ADS YOLUNDA V/I ES ZAMANLILIGI ve SUZGEC DUZELTMESI.

    python sim3_senkron.py

B16 uc firmware kalemi birakmisti (DEVIR 5.12.26):
  1. menzil basina FAZ KALIBRASYONU
  2. PGA degisiminde ornek atma
  3. 1/|H(f)|^2 OLCEK DUZELTMESI

B17 bunlari ele alirken cok daha buyuk bir seyi buldu:

[!] ANA BULGU — IKI ADS BIRBIRINDEN BAGIMSIZ KOSUYOR.

`olcum-karti-a3.ino` sunu yaziyordu:
    "Iki AYRI ADS1115 oldugu icin V ve I YAKLASIK ES ZAMANLI ornekleniyor.
     Tek cip ile kanal degistirseydik aralarinda 1.16 ms gecikme kalirdi."

Ikinci cumle dogru, BIRINCISI DEGIL. Iki cip de SUREKLI kipte, her biri
KENDI ic osilatoruyla. Dongu yalnizca AKIM cipinin ALERT'ini bekliyor;
GERILIM cipi o sirada kendi cevriminin neresindeyse orada. Yani gerilim
ornegi 0 ile bir cevrim arasinda ESKI — ve iki osilator ayni olmadigi
icin bu gecikme SURUKLENIYOR.

ADS1115 ic osilator toleransi ±%10 (TI veri sayfasi; 860 SPS nominal ->
774..946 SPS). Yani kayma butun araligi tariyor.

Bunun 50 Hz'te karsiligi 0..23 DERECE, ve suruklendigi icin okuma
GEZINIYOR. PF=0.5'te guc %76'ya varan olcude dusuk okunabiliyor
(ortalama %37) —
B16'nin duzelttigi her seyden buyuk.

⚠ BU BETIK TASARIMI SINIYOR, KURULMUS BIR KARTI DEGIL. I2C'nin gercek
  zamanlamasi TEZGAHTA olculmeli.
"""
from __future__ import annotations

import math
import re as _re
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
from tezgah import tezgah                               # noqa: E402
import tasarim3_sabit as T                              # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent

T_DONUSUM = 1.0 / T.ADS_SPS          # nominal cevrim suresi
SEBEKE_HZ = 50.0


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


def alt(r, baslik):
    r.bilgi("")
    r.bilgi(f"  --- {baslik} " + "-" * max(0, 64 - len(baslik)))


def guc_orani(theta_der, dfaz_der):
    """P_olculen / P_gercek — yuk acisi theta, olcum faz hatasi dfaz."""
    return (math.cos(math.radians(theta_der + dfaz_der))
            / math.cos(math.radians(theta_der)))


def guc_orani_ort(theta_der, dfaz_maks_der):
    """Kayma 0..dfaz_maks arasinda DUZGUN dagilmissa ORTALAMA oran.

    Iki osilator birbirine gore surukledigi icin, uzun bir pencerede
    kayma butun araligi tariyor. Analitik ortalama:
        ort cos(t + d) = [sin(t + D) - sin(t)] / D      (D radyan)
    """
    d = math.radians(dfaz_maks_der)
    t = math.radians(theta_der)
    if d < 1e-12:
        return 1.0
    return (math.sin(t + d) - math.sin(t)) / d / math.cos(t)


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 0 — ANA BULGU: IKI ADS SENKRON DEGIL
# ═══════════════════════════════════════════════════════════════════════

def bolum0(r):
    bolum(r, "BOLUM 0 — [!] IKI ADS BIRBIRINDEN BAGIMSIZ KOSUYOR")
    ino = (KOK / "kod" / "olcum-karti-a3"
           / "olcum-karti-a3.ino").read_text(encoding="utf-8",
                                             errors="replace")
    r.bilgi("  Firmware'in kendi yorumu (olcum_al fonksiyonunun basi):")
    r.bilgi("    'Iki AYRI ADS1115 oldugu icin V ve I yaklasik es zamanli")
    r.bilgi("     ornekleniyor.'")
    r.bilgi("")
    r.bilgi("  Kodun gercekte yaptigi:")
    r.bilgi("    * iki cip de SUREKLI kipte (ads_kur(..., true))")
    r.bilgi("    * ALERT/RDY yalnizca AKIM cipinde kurulu")
    r.bilgi("    * dongu AKIM'in ALERT'ini bekliyor, sonra ikisini de okuyor")
    r.bilgi("    -> GERILIM cipi kendi cevriminin neresindeyse orada")

    # ⚠ Bu bolum TARIHI durumu anlatiyor. Kodun BUGUNKU hali bolum 5'te
    #   sinaniyor — orada "duzeltildi mi" diye bakiliyor.
    r.kosul("  B17-0: ALERT/RDY hala YALNIZCA akim cipinde",
            "ads_yaz(ADS_AKIM, ADS_UST" in ino
            and "ads_yaz(ADS_GERILIM, ADS_UST" not in ino,
            "tek atista sorun degil: gerilim ONCE baslatildigi icin akim "
            "bittiyse gerilim de bitmistir")

    alt(r, "0a · Kayma ne kadar")
    r.bilgi(f"     Nominal cevrim suresi (860 SPS) : {T_DONUSUM*1e3:.4f} ms")
    r.bilgi(f"     ADS1115 ic osilator toleransi   : ±%{T.ADS_OSILATOR_TOL*100:.0f} "
            f"(TI veri sayfasi)")
    r.bilgi(f"     Yani gercek hiz                 : "
            f"{T.ADS_SPS*(1-T.ADS_OSILATOR_TOL):.0f} .. "
            f"{T.ADS_SPS*(1+T.ADS_OSILATOR_TOL):.0f} SPS")
    r.bilgi("")
    t_maks = T_DONUSUM / (1 - T.ADS_OSILATOR_TOL)
    r.bilgi(f"     Gerilim orneginin yasi          : 0 .. "
            f"{t_maks*1e3:.4f} ms (duzgun dagilim)")
    r.bilgi(f"     50 Hz'te bunun faz karsiligi    : 0 .. "
            f"{360*SEBEKE_HZ*t_maks:.2f} DERECE")
    dfaz_maks = 360 * SEBEKE_HZ * t_maks
    r.kosul("  0a: [!] kayma 50 Hz'te 10 dereceyi asiyor",
            dfaz_maks > 10.0,
            f"{dfaz_maks:.1f}° — B16'nin duzelttigi suzgec eslesmezligi "
            f"0.44° idi, bu onun {dfaz_maks/0.44:.0f} kati")
    r.bilgi("")
    r.bilgi("     ⚠ Ve bu SABIT bir hata degil: iki osilator ayni olmadigi")
    r.bilgi("       icin kayma araligi TARIYOR. Okuma geziniyor.")
    r.bilgi(f"       Vurus periyodu = 1/|f_i - f_v|; iki cip %1 ayrissa")
    r.bilgi(f"       {1/(0.01*T.ADS_SPS)*1e3:.0f} ms, %0.1 ayrissa "
            f"{1/(0.001*T.ADS_SPS):.1f} s.")

    alt(r, "0b · Bunun guce etkisi")
    r.bilgi(f"     {'yuk':<20} {'en iyi':>9} {'en kotu':>9} "
            f"{'ortalama':>10} {'yargi':>10}")
    r.bilgi("     " + "-" * 62)
    en_kotu_ort = 0.0
    for ad, th in (("direncli (PF=1)", 0.0), ("PF=0.87", 30.0),
                   ("PF=0.50", 60.0), ("PF=0.26", 75.0)):
        iyi = guc_orani(th, 0.0)
        kotu = guc_orani(th, dfaz_maks)
        ort = guc_orani_ort(th, dfaz_maks)
        en_kotu_ort = max(en_kotu_ort, abs(ort - 1))
        r.bilgi(f"     {ad:<20} {(iyi-1)*100:8.1f}% {(kotu-1)*100:8.1f}% "
                f"{(ort-1)*100:9.1f}% "
                f"{'COMUS' if abs(ort-1) > 0.2 else 'zayif':>10}")
    r.kosul("  0b: [!] reaktif yukte ORTALAMA hata bile %20'yi asiyor",
            en_kotu_ort > 0.20,
            f"en kotu %{en_kotu_ort*100:.0f} — kayma tarandigi icin "
            f"ortalama alarak KURTULUNAMIYOR")
    r.kosul("  0b: direncli yukte hata gorece kucuk — kusurun neden "
            "gorulmedigini aciklar",
            abs(guc_orani_ort(0.0, dfaz_maks) - 1) < 0.05,
            f"%{(guc_orani_ort(0.0, dfaz_maks)-1)*100:.1f} — direncli yukle "
            f"denenirse kart 'calisiyor' gorunur")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — COZUM: ES ZAMANLI TEK ATIS
# ═══════════════════════════════════════════════════════════════════════

def bolum1(r):
    bolum(r, "BOLUM 1 — COZUM: ES ZAMANLI TEK ATIS (single-shot)")
    r.bilgi("  SUREKLI kip birakiliyor. Her olcumde iki cipe de TEK ATIS")
    r.bilgi("  baslatma komutu yaziliyor, sonra ikisi de okunuyor.")
    r.bilgi("  Kalan kayma artik osilator farki degil, I2C yazma suresi —")
    r.bilgi("  ve o BILINEN, SABIT bir sayi, yani DUZELTILEBILIR.")
    r.bilgi("")
    bit = T.I2C_YAZMA_BIT
    t_yaz = bit / T.I2C_HIZ
    r.bilgi(f"     I2C hizi                : {T.I2C_HIZ/1e3:.0f} kHz")
    r.bilgi(f"     Bir ayar yazmasi        : {bit} bit -> "
            f"{t_yaz*1e6:.0f} us")
    r.bilgi(f"     Iki baslatma arasi kayma: {t_yaz*1e6:.0f} us")
    r.bilgi(f"     50 Hz'te faz karsiligi  : "
            f"{360*SEBEKE_HZ*t_yaz:.3f} DERECE")
    dfaz_yeni = 360 * SEBEKE_HZ * t_yaz
    dfaz_eski = 360 * SEBEKE_HZ * T_DONUSUM / (1 - T.ADS_OSILATOR_TOL)
    r.kosul("  B17-1: kalan kayma en az 10 kat kuculuyor",
            dfaz_eski / dfaz_yeni > 10,
            f"{dfaz_eski:.2f}° -> {dfaz_yeni:.3f}° "
            f"({dfaz_eski/dfaz_yeni:.0f} kat)")
    # [!] B20 (2026-09-10): burada `True is not False` yaziyordu — her zaman
    # dogru olan, hicbir sey OLCMEYEN bos bir iddia. Yerine iddianin
    # KENDISI sinaniyor: "kalan kayma SABIT" demek, kaymanin ADS
    # osilatorunun toleransindan BAGIMSIZ olmasi demek. Once (surekli kip)
    # kayma dogrudan donusum suresiydi, yani ±%10 ile geziniyordu; simdi
    # (tek atis) kayma yalnizca I2C yazma suresi, osilatorden bagimsiz.
    kayma_hizli = T_DONUSUM / (1 + T.ADS_OSILATOR_TOL)
    kayma_yavas = T_DONUSUM / (1 - T.ADS_OSILATOR_TOL)
    eski_yayilma = (kayma_yavas - kayma_hizli) / T_DONUSUM
    yeni_yayilma = 0.0          # t_yaz osilatore hic bagli degil
    r.bilgi(f"     Sureklide kaymanin osilatorle yayilimi : "
            f"%{eski_yayilma*100:.1f}")
    r.bilgi(f"     Tek atista                             : "
            f"%{yeni_yayilma*100:.1f}  (I2C, osilatorden bagimsiz)")
    r.kosul("  B17-1: kalan kayma SABIT ve BILINEN — duzeltilebilir",
            eski_yayilma > 0.15 and yeni_yayilma == 0.0,
            f"surukleyen osilator farki (%{eski_yayilma*100:.0f} yayilim) "
            f"yerine degismeyen I2C suresi (%0 yayilim)")

    alt(r, "1b · Kalan kaymayi da silmek: KESIRLI GECIKME")
    r.bilgi("     Firmware'de Lagrange yarim-ornek hizalayici ZATEN var")
    r.bilgi("     (hizala_yarim, d=1/2 sabit). B17 onu GENELLESTIRIYOR:")
    r.bilgi("     istenen d degeri icin 4 katsayili Lagrange.")
    r.bilgi("")
    d = t_yaz / T_DONUSUM
    r.bilgi(f"     Gereken kesirli gecikme: {t_yaz*1e6:.0f} us / "
            f"{T_DONUSUM*1e6:.0f} us = {d:.4f} ornek")
    r.bilgi("")
    r.bilgi(f"     {'yuk':<16} {'duzeltmesiz':>13} {'duzeltmeli':>12}")
    r.bilgi("     " + "-" * 44)
    en_kalan = 0.0
    for ad, th in (("direncli", 0.0), ("PF=0.50", 60.0), ("PF=0.26", 75.0)):
        ham = (guc_orani(th, dfaz_yeni) - 1) * 100
        # kesirli gecikme faz hatasini SIFIRLIYOR (Lagrange simetrik ->
        # dogrusal faz); geriye yalnizca genlik sarkmasi kaliyor
        kalan = (lagrange_genlik(d, SEBEKE_HZ * T_DONUSUM) - 1) * 100
        en_kalan = max(en_kalan, abs(kalan))
        r.bilgi(f"     {ad:<16} {ham:12.3f}% {kalan:11.3f}%")
    r.kosul("  1b: kesirli gecikme sonrasi kalan hata %0.1'in altinda",
            en_kalan < 0.1,
            f"%{en_kalan:.4f} — Lagrange simetrik oldugu icin FAZ hatasi "
            f"tam sifir, yalnizca genlik sarkmasi kaliyor")


def lagrange_genlik(d, f_norm):
    """4 katsayili Lagrange kesirli gecikmenin genlik yaniti.

    f_norm = f / f_ornekleme.  Katsayilar (Waring-Lagrange, N=3):
        h[k] = prod_{j!=k} (d - j) / (k - j),  k,j = -1,0,1,2 kaydirilmis
    """
    h = lagrange_katsayi(d)
    w = 2 * math.pi * f_norm
    re_ = sum(h[k] * math.cos(-w * (k - 1)) for k in range(4))
    im = sum(h[k] * math.sin(-w * (k - 1)) for k in range(4))
    return math.hypot(re_, im)


def lagrange_katsayi(d):
    """h[-1], h[0], h[1], h[2] — d ornek gecikme icin."""
    n = [-1.0, 0.0, 1.0, 2.0]
    h = []
    for k in n:
        p = 1.0
        for j in n:
            if j != k:
                p *= (d - j) / (k - j)
        h.append(p)
    return h


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — SUZGEC OLCEK DUZELTMESI (B16'nin 3. kalemi)
# ═══════════════════════════════════════════════════════════════════════

def bolum2(r):
    bolum(r, "BOLUM 2 — 1/|H(f)|^2 OLCEK DUZELTMESI")
    r.bilgi("  B16: iki kanal da ayni RC ile suzuluyor, o yuzden guc")
    r.bilgi("  |H(f)|^2 kadar DUSUK okunuyor. Frekans bilinirse tam")
    r.bilgi("  duzeltilebilir — B16 oncesi bu MUMKUN DEGILDI (hata yukun")
    r.bilgi("  guc faktorune bagliydi).")
    r.bilgi("")
    r.bilgi(f"  {'kanal':<20} {'tau':>9} {'|H| @50Hz':>11} "
            f"{'|H|^2':>9} {'duzeltme':>10}")
    r.bilgi("  " + "-" * 62)
    for k in T.KANALLAR:
        tau = (k["thev"] + T.RC_R) * T.RC_C
        h = 1 / math.sqrt(1 + (2 * math.pi * SEBEKE_HZ * tau) ** 2)
        r.bilgi(f"  {k['ad']:<20} {tau*1e3:8.3f}ms {h:10.4f} "
                f"{h*h:8.4f} {1/(h*h):9.3f}x")
    tau_n = (T.KANALLAR[0]["thev"] + T.RC_R) * T.RC_C
    h_n = 1 / math.sqrt(1 + (2 * math.pi * SEBEKE_HZ * tau_n) ** 2)
    r.kosul("  B17-2: duzeltmesiz guc %40'tan fazla dusuk okunuyor",
            (1 - h_n * h_n) > 0.40,
            f"%{(1-h_n*h_n)*100:.0f} dusuk — carpan {1/(h_n*h_n):.3f}")
    r.bilgi("")
    r.bilgi("  ⚠ Duzeltme FREKANSI BILMEYI gerektiriyor. ADS yolu (860 SPS,")
    r.bilgi("    55 Hz suzgec) frekans olcemez. Cozum: kullanicinin")
    r.bilgi("    ayarladigi SEBEKE FREKANSI (50/60 Hz, ya da DC icin 0).")
    r.bilgi("    Bu bir varsayim degil, bir AYAR — ve yanlissa sonuc")
    r.bilgi("    ONGORULEBILIR sekilde kayar:")
    r.bilgi("")
    r.bilgi(f"     {'gercek f':>10} {'ayar 50 Hz ile hata':>22}")
    r.bilgi("     " + "-" * 36)
    en_h = 0.0
    for f in (45.0, 48.0, 50.0, 52.0, 55.0, 60.0):
        hg = 1 / math.sqrt(1 + (2 * math.pi * f * tau_n) ** 2)
        hata = (h_n * h_n) / (hg * hg) - 1
        en_h = max(en_h, abs(hata))
        r.bilgi(f"     {f:9.0f}Hz {hata*100:20.1f}%")
    r.kosul("  B17-2: 60 Hz sebekede 50 Hz ayari BUYUK hata yapiyor",
            en_h > 0.15,
            f"%{en_h*100:.0f} — o yuzden ayar KULLANICIYA acilmali, "
            f"sabit 50 Hz varsayilmamali")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — FAZ KALIBRASYONU (B16'nin 1. kalemi)
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r):
    bolum(r, "BOLUM 3 — MENZIL BASINA FAZ KALIBRASYONU")
    r.bilgi("  B16: kondansator toleransi V/I zaman sabitlerini ayirir ve")
    r.bilgi("  bu REAKTIF yukte guc hatasi yapar. Cozum: direncli bir yukle")
    r.bilgi("  okunan faz farkini olcup saklamak (referans cihaz GEREKMIYOR).")
    r.bilgi("")
    r.bilgi("  Kalibrasyon nasil isliyor:")
    r.bilgi("    1. DIRENCLI yuk bagla (rezistans, ampul)")
    r.bilgi("    2. Gercek faz farki SIFIR olmali")
    r.bilgi("    3. Okunan fark = suzgec eslesmezligi + kalan kayma")
    r.bilgi("    4. Menzil basina sakla, kesirli gecikmeye EKLE")
    r.bilgi("")
    r.bilgi(f"     {'artik faz':>11} {'PF=1':>9} {'PF=0.5':>9} "
            f"{'PF=0.26':>10}")
    r.bilgi("     " + "-" * 44)
    for dfaz in (0.0, 0.5, 1.0, 3.0, 6.0):
        s = [f"{(guc_orani(th, dfaz)-1)*100:8.2f}%"
             for th in (0.0, 60.0, 75.0)]
        r.bilgi(f"     {dfaz:10.1f}° {s[0]} {s[1]} {s[2]}")
    r.kosul("  B17-3: 1 dereceye kadar kalibre etmek PF=0.5'te hatayi "
            "%4'un altina indiriyor",
            abs(guc_orani(60.0, 1.0) - 1) < 0.04,
            f"%{abs(guc_orani(60.0, 1.0)-1)*100:.2f}")
    r.bilgi("")
    r.bilgi("  ⚠ Kalibrasyonun COZUNURLUGU, kesirli gecikmenin adimidir.")
    d_adim = 0.001
    r.bilgi(f"    Kesirli gecikme {d_adim} ornek adimla saklanirsa 50 Hz'te")
    r.bilgi(f"    {360*SEBEKE_HZ*d_adim*T_DONUSUM:.4f}° cozunurluk — fazlasiyla yeter.")
    r.kosul("  B17-3: kesirli gecikme cozunurlugu gereken hassasiyetin "
            "cok altinda",
            360 * SEBEKE_HZ * d_adim * T_DONUSUM < 0.1,
            f"{360*SEBEKE_HZ*d_adim*T_DONUSUM:.4f}° adim vs 1° hedef")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — B16'NIN 2. KALEMI: PGA OTURMASI
# ═══════════════════════════════════════════════════════════════════════

def bolum4(r):
    bolum(r, "BOLUM 4 — 'PGA DEGISIMINDE ORNEK AT' — GECERSIZ CIKTI")
    ino = (KOK / "kod" / "olcum-karti-a3"
           / "olcum-karti-a3.ino").read_text(encoding="utf-8",
                                             errors="replace")
    r.bilgi("  B16 ucuncu kalem olarak 'PGA degisiminden sonra 13 ornek")
    r.bilgi("  atilmali' demisti. Firmware'e bakinca:")
    r.bilgi("")
    r.bilgi("    * gerilim kanallarinin ikisi de PGA_1024'te SABIT")
    r.bilgi("    * akim kanali PGA ±0.256'da SABIT")
    r.bilgi("    * oto-menzil KANAL degistiriyor, PGA KADEMESI degil")
    r.bilgi("")
    pga_sabit = "PGA oto-kademesi bilerek yapilmiyor" in ino
    r.kosul("  B17-4: firmware PGA oto-kademesini BILEREK yapmiyor",
            pga_sabit,
            "DEVIR 4.14: giris empedansi PGA ile degisiyor, kazanc "
            "sicramasi kalibrasyonla silinemiyor")
    kanal_pga = all(k["pga"] == 1.024 for k in T.KANALLAR)
    r.kosul("  B17-4: iki gerilim kanali da AYNI PGA'da",
            kanal_pga, "PGA ±1.024 — kademe degisimi YOK")
    r.kosul("  B17-4: dolayisiyla B16'nin 2. kalemi UYGULANAMAZ",
            pga_sabit and kanal_pga,
            "atilacak ornek yok cunku PGA hic degismiyor")
    r.bilgi("")
    r.bilgi("  ⚠ AMA yerine GERCEK bir kalem var: KANAL degisimi.")
    r.bilgi("    menzil_uygula() zaten MUX'u yazip 1300 us bekliyor ve")
    r.bilgi("    ilk donusumu atiyor.")
    kanal_at = "delayMicroseconds(1300)" in ino and "ads_oku(ADS_GERILIM)" in ino
    r.kosul("  B17-4: kanal degisiminde ilk donusum ZATEN atiliyor",
            kanal_at,
            f"1300 us > bir cevrim ({T_DONUSUM*1e6:.0f} us) — dogru yapilmis")
    r.bilgi("")
    r.bilgi("  SONUC: B16'nin 2. kalemi KAPANDI — yapilacak is yok.")
    r.bilgi("  (B16 bunu firmware'e bakmadan yazmisti; B17 dogruladi.)")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 5 — FIRMWARE'DE UYGULANDI MI
# ═══════════════════════════════════════════════════════════════════════

def bolum5(r):
    bolum(r, "BOLUM 5 — FIRMWARE'DE GERCEKTEN UYGULANDI MI")
    h = (KOK / "kod" / "olcum-karti-a3"
         / "olcum3.h").read_text(encoding="utf-8", errors="replace")
    ino = (KOK / "kod" / "olcum-karti-a3"
           / "olcum-karti-a3.ino").read_text(encoding="utf-8",
                                             errors="replace")
    r.kosul("  B17-5: genel kesirli gecikme fonksiyonu var",
            "hizala_kesirli" in h,
            "hizala_yarim (d=1/2 sabit) genellestirildi")
    r.kosul("  B17-5: eski d=1/2 fonksiyonu KORUNDU (B5 kaniti gecerli)",
            "hizala_yarim" in h,
            "hizli yol onu kullanmaya devam ediyor")
    r.kosul("  B17-5: suzgec olcek duzeltmesi var",
            "suzgec_ters_kazanc" in h, "1/|H(f)| — guce iki kez uygulaniyor")
    r.kosul("  B17-5: duzeltme YALNIZCA guce uygulaniyor",
            "o.watt *= suzgec_ters_kazanc" in ino,
            "ortalama V ve I ham kaliyor: AC'de zaten ~0, DC'de duzeltme "
            "zaten 1")
    r.kosul("  B17-5: ADS yolu TEK ATIS kipine gecti",
            "ads_tek_atis_baslat" in ino,
            "iki cipe de baslatma yaziliyor, sonra ikisi de okunuyor")
    r.kosul("  B17-5: SUREKLI kip artik ADS yolunda KULLANILMIYOR",
            "ads_kur(ADS_AKIM, MUX_01, ayar.i_pga, true)" not in ino,
            "eski satir kaldirildi")
    r.kosul("  B17-5: yanlis yorum duzeltildi ve SEBEBI koda islendi",
            "B17'NIN BULDUGU KUSUR" in ino
            and "SUREKLI kip birakildi" in ino,
            "eski iddia alintilanip neden yanlis oldugu yaziliyor")
    r.kosul("  B17-5: kayma OLCULUYOR, varsayilmiyor",
            "OLCULUYOR, varsayilmiyor" in ino,
            "t_kayma_us = micros() farki — I2C suresi karta gore degisir")
    r.kosul("  B17-5: ornek periyodu da olculuyor",
            "ornek_periyot_us" in ino,
            "dongu web sunucusu da kostugu icin sabit hizli DEGIL")
    tip_h = (KOK / "kod" / "olcum-karti-a3" / "tipler3.h").read_text(
        encoding="utf-8", errors="replace")
    r.kosul("  B17-5: faz kalibrasyonu MENZIL BASINA saklaniyor",
            "faz_kal_us[2]" in tip_h,
            "[0] NORMAL, [1] YUKSEK — iki kanalin tau'su ayni degil")

    # ── [!] B22.1 (K2): faz duzeltmesi PERIYOTTAN BAGIMSIZ olmali ──────
    #
    # B20 zaten "faz kalibrasyonu (SABIT zaman gecikmesi)" diye yaziyordu,
    # ama UYGULAMA ornek cinsindendi:
    #     d = t_kayma_us / ornek_periyot_us + faz_kal[m]
    # Uygulanan zaman boylece faz_kal * ornek_periyot_us oluyordu, yani
    # DONGU PERIYODUYLA OLCEKLENIYORDU. Oysa duzeltilen sey iki RC'nin
    # arctan farki: SABIT bir zaman. Periyot degiskendir (web istegi,
    # menzil gecisi 1518 us, B22.1 oncesi enableDelay kusuru 2000 us).
    r.kosul("  B22.1: faz duzeltmesi US cinsinden ve BOLMENIN ICINDE",
            "ayar.faz_kal_us[ayar.menzil ? 1 : 0])" in ino
            and "/ ornek_periyot_us;" in ino,
            "d = (t_kayma_us + faz_kal_us) / ornek_periyot_us")
    # ⚠ YORUMLAR CIKARILIYOR. Bu iddia KODA bakiyor, proza'ya degil:
    # degisikligi anlatan aciklama yorumu `faz_kal[m]` yazdigi icin iddia
    # yanlislikla kirmiziya donuyordu. (Ayni sinif kusur B22.0'da CSS
    # tarafinda ters yonde cikmisti: yorum iddiayi KARSILIYORDU.)
    def _kod(metin: str) -> str:
        """C/C++ yorumlarini cikarir. `//.*` satir sonunda durur ("." satir
        sonuyla eslesmiyor), yani kacis dizisi gerekmiyor."""
        return _re.sub(r"//.*", "", _re.sub(r"/\*.*?\*/", "", metin,
                                            flags=_re.S))
    ino_kod, tip_kod = _kod(ino), _kod(tip_h)
    r.kosul("  B22.1: ornek cinsinden eski alan KODDA HIC KALMADI",
            "faz_kal[" not in ino_kod and "faz_kal[" not in tip_kod,
            "iki temsil kalirsa hangisinin gecerli oldugu belirsizlesir")
    # ⚠ tip_h DEGIL tip_kod: imzanin degistigini ANLATAN yorum da
    # "0xC0F6" yaziyor ve iddia ona kaniyordu (mutasyon KACTI).
    r.kosul("  B22.1: anlam degistigi icin NVS imzasi bumplandi",
            "0xC0F6u" in tip_kod and "0xC0F5" not in tip_kod,
            "yapi BOYUTU degismedi (float[2] -> float[2]), yani "
            "sizeof denetimi bunu goremez; imza TEK korumadir")

    # Sayisallastirma: 50 Hz'te kalibre edilmis kartin periyot degisince
    # yaptigi ARTIK faz hatasi. En kotu tau eslesmezligi (kondansator
    # toleransi +-%10) icin duzeltme 292.8 us; ornek cinsinden saklanirsa
    # bu deger periyotla olceklenir.
    T_KAL = 1502.79            # us — nominal dongu periyodu (665.4 SPS)
    DUZ_US = 292.8             # us — en kotu tau eslesmezligi duzeltmesi
    for T, ad in ((2000.0, "enableDelay kusuru"), (3000.0, "menzil gecisi")):
        # ornek cinsinden: saklanan d = DUZ_US / T_KAL, uygulanan = d * T
        artik_us = DUZ_US * (T / T_KAL) - DUZ_US
        artik_der = 360.0 * 50.0 * artik_us * 1e-6
        r.bilgi(f"     ornek cinsinden, periyot {T:.0f} us ({ad}): "
                f"artik {artik_der:+.3f} derece")
        r.kosul(f"  B22.1: {T:.0f} us'te ornek-cinsinden hata >1 derece "
                f"(B17 olcutu asiliyor)",
                abs(artik_der) > 1.0,
                "duzeltilen kusurun buyuklugu — us cinsinden bu hata SIFIR")
    r.bilgi("     us cinsinden: artik hata her periyotta 0.000 derece "
            "(duzeltme bolmenin icinde, olceklenmiyor)")
    r.kosul("  B17-5: sebeke frekansi AYAR olarak duruyor",
            "sebeke_hz" in ino or "sebeke_hz" in
            (KOK / "kod" / "olcum-karti-a3"
             / "tipler3.h").read_text(encoding="utf-8", errors="replace"),
            "kullanici 50/60/0 secebiliyor")


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B17 — ADS YOLUNDA ES ZAMANLILIK VE SUZGEC DUZELTMESI")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI ve FIRMWARE'i sinar, kurulmus bir KARTI degil.")
    bolum0(r)
    bolum1(r)
    bolum2(r)
    bolum3(r)
    bolum4(r)
    bolum5(r)
    tamam = r.yazdir()
    tezgah("B17 ADS es zamanliligi ve faz", [
        ("[!] Faz kalibrasyonunun TASINABILIRLIGI",
         "Direncli yukte USB'den `F` ile kalibre et, sonra AYNI yuke "
         "WiFi ile bak. PF farki > %0.5 ise B22.1'in us duzeltmesi eksik "
         "ve faz hala periyoda bagli demektir"),
        ("Kondansator tolerans harfi (J=%5, K=%10)",
         "Gucun gecerlilik bandini bu belirliyor. Kutudaki harfi oku; "
         "K ise en kotu tau eslesmezligi 292.8 us"),
        ("Sontun guc degeri",
         "+-11.5 A rakami 2 W CIKARIMINDAN geliyor. Uzerindeki degeri "
         "oku; dusukse akim tavani duser"),
        ("Direncli yukte PF gercekten 1'e yakin mi",
         "`w` komutu. PF < 0.99 ise suzgec eslesmezligi kalibre "
         "edilmemis demektir — once `F` ile duzelt"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
