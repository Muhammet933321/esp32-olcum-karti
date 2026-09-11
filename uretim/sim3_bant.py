# -*- coding: utf-8 -*-
"""B20 — ORNEKLEME HIZI, BANT SINIRI ve MENZIL DAVRANISI.

    python sim3_bant.py

B17 ADS yolunu tek atis kipine aldi ve uzerine iki duzeltme koydu
(1/|H(f)| olcek duzeltmesi + kesirli gecikme). Iddialarinin HEPSI
50 Hz'te ve 860 SPS varsayimiyla sinanmisti. B20 ikisini de kirdi:

  1. [!] ORNEKLEME HIZI 860 SPS DEGILDI. Iki ayri kusur ayni yere
     vuruyordu: (a) loop() basinda SUREKLI kipten kalma olu bir
     bekleme her turda 4000 us zaman asimina dusuyordu, (b) her ayar
     yazmasi COMP_QUE = 11b gonderdigi icin ALERT/RDY pini yuksek
     empedansta kaliyor, o bekleme HIC basarili olamiyordu.
     Gercek periyot 11.0 ms = 91 SPS. Firmware'in her yerde yazdigi
     860 SPS'in ONDA BIRI.

  2. [!] BANT SINIRI HICBIR YERDE YAZILI DEGILDI. `f` komutu 400 Hz'e
     izin veriyordu; o frekansta Lagrange hizalayicinin genligi %11.8
     sarkiyor ve faz kalibrasyonu (SABIT zaman gecikmesi) duzeltmesi
     gereken arctan farkini artik izlemiyor.

  3. [!] OTOMATIK MENZIL AC'DE KULLANILAMIYORDU. Esikler ANLIK |v|'ye
     uygulaniyordu; bir sinus her yarim cevrimde iki esigi de gecip
     saniyede ~200 menzil degisimi yaratiyordu.

Bu betik ucunu de OLCUYOR ve duzeltmelerin gercekten uygulandigini
FIRMWARE KAYNAGINDAN dogruluyor.

⚠ Bu adim TASARIMI ve FIRMWARE'i sinar, kurulmus bir KARTI degil.
  I2C'nin gercek zamanlamasi ve ALERT/RDY'nin gercekten darbe verdigi
  TEZGAHTA olculmeli.
"""
from __future__ import annotations

import math
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
KOD = KOK / "kod" / "olcum-karti-a3"
INO = (KOD / "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
OLC_H = (KOD / "olcum3.h").read_text(encoding="utf-8", errors="replace")
TIP_H = (KOD / "tipler3.h").read_text(encoding="utf-8", errors="replace")

SEBEKE_HZ = 50.0
TAU_V = (T.KANALLAR[0]["thev"] + T.RC_R) * T.RC_C
TAU_Y = (T.KANALLAR[1]["thev"] + T.RC_R) * T.RC_C
TAU_I = (2 * T.SONT_KELVIN_R + 2 * T.ADS_SERI_R) * T.ADS_AKIM_C


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


def alt(r, baslik):
    r.bilgi("")
    r.bilgi(f"  --- {baslik} " + "-" * max(0, 62 - len(baslik)))


def web_server_kaynagi():
    """Derlemede kullanilan WebServer.cpp'yi bulur.

    Yol makineye ozgu oldugu icin arastiriliyor. BULUNAMAZSA iddia
    KIRMIZI yanar — sessizce atlanmaz. Zincir zaten arduino-cli ile
    derliyor, yani cekirdek bu makinede kurulu olmak zorunda.
    """
    import os
    kok = os.environ.get("LOCALAPPDATA")
    if not kok:
        return None
    taban = Path(kok) / "Arduino15" / "packages" / "esp32" / "hardware" / "esp32"
    if not taban.is_dir():
        return None
    for surum in sorted(taban.iterdir(), reverse=True):
        aday = surum / "libraries" / "WebServer" / "src" / "WebServer.cpp"
        if aday.is_file():
            return aday
    return None


def govde(kaynak: str, imza: str) -> str:
    """Bir C fonksiyonunun govdesini {..} dengeleyerek cikarir."""
    i = kaynak.index(imza)
    j = kaynak.index("{", i)
    d = 0
    for k in range(j, len(kaynak)):
        if kaynak[k] == "{":
            d += 1
        elif kaynak[k] == "}":
            d -= 1
            if d == 0:
                return kaynak[j:k + 1]
    raise AssertionError(f"govde bulunamadi: {imza}")


def yorumsuz(metin: str) -> str:
    """// ve /* */ yorumlarini atar. Yorumdaki eski kod parcalari
    iddiayi kandirmasin diye HER yapisal denetim bunu kullaniyor."""
    metin = re.sub(r"/\*.*?\*/", " ", metin, flags=re.S)
    return re.sub(r"//[^\n]*", " ", metin)


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — [!] GERCEK ORNEKLEME HIZI
# ═══════════════════════════════════════════════════════════════════════

def i2c_us(bit):
    return bit / T.I2C_HIZ * 1e6


# ads_yaz: start + (adres7+rw+ack) + 3x(8+ack) + stop
BIT_YAZ = T.I2C_YAZMA_BIT
# ads_oku: yazmac isaretleme (start+adres+ack+yazmac+ack+stop) +
#          tekrar start + adres+ack + 2x(8+ack)
BIT_OKU = 20 + 29
T_DONUSUM_US = 1e6 / T.ADS_SPS


def bolum1(r):
    bolum(r, "BOLUM 1 — [!] GERCEK ORNEKLEME HIZI (860 SPS DEGILDI)")

    t_yaz, t_oku = i2c_us(BIT_YAZ), i2c_us(BIT_OKU)
    r.bilgi(f"     I2C {T.I2C_HIZ/1e3:.0f} kHz · ayar yazmasi {BIT_YAZ} bit "
            f"= {t_yaz:.1f} us · donusum okumasi {BIT_OKU} bit = {t_oku:.1f} us")
    r.bilgi(f"     ADS donusumu ({T.ADS_SPS} SPS nominal) = {T_DONUSUM_US:.1f} us")
    r.bilgi("")

    g_loop = yorumsuz(govde(INO, "void loop()"))
    g_olc = yorumsuz(govde(INO, "Okuma3 olcum_al()"))

    # --- 1a. loop() icinde OLU bekleme kaldi mi?
    alt(r, "1a · loop() icindeki olu bekleme")
    bekle_loop = [int(x) for x in
                  re.findall(r"yeni_donusum_bekle\((\d+)\)", g_loop)]
    delay_loop = [int(x) for x in re.findall(r"\bdelay\((\d+)\)", g_loop)]
    r.bilgi(f"     loop() icindeki yeni_donusum_bekle : {bekle_loop or 'YOK'}")
    r.bilgi(f"     loop() icindeki delay()            : {delay_loop or 'YOK'}")
    r.bilgi("")
    r.bilgi("     TEK ATIS kipinde loop()'un basinda UCUSTA DONUSUM YOKTUR:")
    r.bilgi("     bir onceki olcum_al iki yazmaci da okudu ve tek atis kipi")
    r.bilgi("     donusum bitince kapanir. Oradaki her bekleme ALERT kusursuz")
    r.bilgi("     calissa bile HER TURDA zaman asimina duser.")
    r.kosul("  1a: loop() basinda olu bekleme YOK",
            not bekle_loop,
            "olcum_al donusumu kendisi baslatip kendisi bekliyor")
    r.kosul("  1a: loop() icinde bloklayici delay() YOK",
            not delay_loop,
            "yerine yield() — gorev degistirmeyi birakir, tik beklemez")
    r.kosul("  1a: ama loop() yine de YIELD ediyor (WDT/gorev acligi)",
            "yield()" in g_loop,
            "delay(2) bu dongudeki tek vTaskDelay idi; silinince yerine "
            "yield() konmali")

    # --- 1a-bis. [!] B22.1 (K1): KUTUPHANE ICINDEKI GIZLI delay(1)
    alt(r, "1a-bis · WebServer kutuphanesindeki gizli delay(1)")
    r.bilgi("     1a YALNIZCA .ino'nun loop() govdesine bakiyor ve yesil")
    r.bilgi("     yaniyor — dogru ama ALAKASIZ. loop()'un ilk satiri")
    r.bilgi("     sunucu.handleClient() ve o cagri, ISTEMCI YOKKEN her turda")
    r.bilgi("     delay(1) yapiyor (WebServer.cpp, _nullDelay varsayilan true).")
    r.bilgi("     CONFIG_FREERTOS_HZ = 1000 oldugu icin bu vTaskDelay(1 tik):")
    r.bilgi("     dongu bir sonraki TIK SINIRINA kadar blokleniyor.")
    r.bilgi("     Sunucu WiFi kapaliyken bile dinleme soketi kurdugundan")
    r.bilgi("     (begin() kosulsuz) kusur WiFi kapaliyken de gecerliydi.")
    r.bilgi("")
    ws_yol = web_server_kaynagi()
    r.kosul("  1a-bis: WebServer kaynagi bulundu",
            ws_yol is not None,
            "bulunamazsa asagidaki iddialar SESSIZCE kaybolurdu")
    if ws_yol is not None:
        ws = ws_yol.read_text(encoding="utf-8", errors="replace")
        r.kosul("  1a-bis: kutuphane HALA _nullDelay ile delay(1) yapiyor",
                "_nullDelay" in ws and "delay(1)" in ws,
                "duzeltme hala gerekli mi diye bakiyoruz — kutuphane bunu "
                "kaldirirsa iddia dusup bizi uyarir")
    g_setup = yorumsuz(govde(INO, "void setup()"))
    r.kosul("  1a-bis: firmware enableDelay(false) cagiriyor",
            "sunucu.enableDelay(false)" in g_setup,
            "tek satirlik duzeltme")
    r.kosul("  1a-bis: enableDelay, sunucu.begin()'den ONCE",
            0 <= g_setup.find("enableDelay(false)") < g_setup.find("sunucu.begin()"),
            "niyet acik olsun")

    # --- 1b. COMP_QUE — ALERT/RDY etkin mi?
    alt(r, "1b · COMP_QUE: ALERT/RDY pini ETKIN mi")
    komp_tek = int(re.search(r"ADS_KOMP_TEK\s*=\s*(0x[0-9A-Fa-f]+)",
                             INO).group(1), 16)
    komp_kap = int(re.search(r"ADS_KOMP_KAPALI\s*=\s*(0x[0-9A-Fa-f]+)",
                             INO).group(1), 16)
    r.bilgi("     TI SBAS444E 7.3.8:")
    r.bilgi('       "Set the COMP_QUE[1:0] bits to any 2-bit value other')
    r.bilgi('        than 11b to keep the ALERT/RDY pin enabled"')
    r.bilgi("     Yazmac tablosu, 11b: \"Disable comparator and set")
    r.bilgi("       ALERT/RDY pin to high-impedance (default)\"")
    r.bilgi("")
    r.bilgi(f"     ADS_KOMP_TEK    = 0x{komp_tek:04X} -> COMP_QUE = "
            f"{komp_tek & 3:02b}b")
    r.bilgi(f"     ADS_KOMP_KAPALI = 0x{komp_kap:04X} -> COMP_QUE = "
            f"{komp_kap & 3:02b}b")
    r.kosul("  1b: RDY kipi icin kullanilan sabit 11b DEGIL",
            (komp_tek & 3) != 3,
            f"COMP_QUE = {komp_tek & 3:02b}b — komparator etkin, pin surulur")

    # --- 1b-bis. B26: KENAR YONU. COMP_QUE dogru olsa da bu yanlisti.
    alt(r, "1b-bis · RDY kenar yonu: once KALKMA, sonra DUSME")
    r.bilgi("     🔴 B20 bu pinin BIR kusurunu duzeltti (COMP_QUE=11b ->")
    r.bilgi("        pin yuksek empedansta, 91 SPS). Duzeltme DOGRUYDU ama")
    r.bilgi("        YETMIYORDU: altinda ikinci bir kusur duruyordu ve")
    r.bilgi("        donanim olmadigi icin 665 SPS hic OLCULMEMISTI.")
    r.bilgi("")
    r.bilgi("     Tezgahta olculdu (B26, 2026-09-11):")
    r.bilgi("       RDY dustu @1228 us  |  kalkti: HAYIR")
    r.bilgi("       okuma oncesi LOW    |  okuma sonrasi LOW")
    r.bilgi("     Yani pin donusum bitince LOW'a cekip OYLE KALIYOR;")
    r.bilgi("     geri kaldiran sey YENI DONUSUMU BASLATAN ayar yazmasi,")
    r.bilgi("     donusum yazmacini okumak DEGIL.")
    r.bilgi("")
    r.bilgi("     Eski sira (once dus, sonra kalk) ikinci dongude HER")
    r.bilgi("     cagrida 4000 us zaman asimina dusuyordu: 6.17 ms/tur,")
    r.bilgi("     162 ornek/s — hedefin dortte biri. Duzeltilince 33 ->")
    r.bilgi("     97 ornek/200 ms olctuk (tek ADS).")
    r.bilgi("")
    g_bekle = yorumsuz(govde(INO, "bool yeni_donusum_bekle"))
    kenar = re.findall(r"digitalRead\(PIN_HAZIR\)\s*==\s*(LOW|HIGH)", g_bekle)
    r.kosul("  1b-bis: `yeni_donusum_bekle` iki kenara da bakiyor",
            len(kenar) >= 2, f"bulunan: {kenar or 'YOK'}")
    r.kosul("  1b-bis: ONCE de-assert (LOW bitsin), SONRA donusum (HIGH bitsin)",
            kenar[:2] == ["LOW", "HIGH"],
            f"sira {kenar[:2]} — ters olursa ikinci dongu HIC bitmez ve "
            f"her tur zaman asimina duser (B26'nin olctugu kusur)")

    # ALERT/RDY hangi cipte telli? Netlistten oku — elle yazma.
    net = (BURASI / "netlist3.net").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'\(name "/HAZIR"\)(.*?)\n\t\t\)', net, re.S)
    hazir_dugum = re.findall(r'\(ref "([^"]+)"\)', m.group(1)) if m else []
    r.bilgi(f"     Netlistte /HAZIR netindeki dugumler: {hazir_dugum}")
    # RDY'yi YALNIZCA telli cipe acmis olmali
    g_kur = yorumsuz(govde(INO, "static void ads_kur"))
    g_tek = yorumsuz(govde(INO, "static void ads_tek_atis_baslat"))
    kosullu = ("ADS_AKIM ? ADS_KOMP_TEK" in g_kur.replace("  ", " ")
               or re.search(r"ADS_AKIM\s*\?\s*ADS_KOMP_TEK", g_kur))
    kosullu2 = re.search(r"ADS_AKIM\s*\?\s*ADS_KOMP_TEK", g_tek)
    r.kosul("  1b: RDY YALNIZCA ALERT'i telli olan cipe aciliyor",
            bool(kosullu) and bool(kosullu2),
            "GERILIM cipinin ALERT ucu netlistte bilerek bos "
            "(unconnected-(U7-ALERT{slash}RDY-Pad2))")
    r.kosul("  1b: iki baslatma yolu da ayni kurali uyguluyor",
            bool(kosullu) and bool(kosullu2),
            "ads_kur ve ads_tek_atis_baslat — biri unutulursa pin "
            "bir sonraki yazmada yeniden kapanirdi")

    # --- 1c. Butce
    alt(r, "1c · Dongu periyodu butcesi")
    bekle_olc = [int(x) for x in
                 re.findall(r"yeni_donusum_bekle\((\d+)\)", g_olc)]
    dus_olc = [int(x) for x in
               re.findall(r"delayMicroseconds\((\d+)\)", g_olc)]

    def periyot(olu_bekle, olu_delay_ms, alert_var):
        t = sum(olu_bekle) + olu_delay_ms * 1000.0
        t += 2 * t_yaz                       # iki tek atis yazmasi
        if alert_var:
            # ikinci yazmadan sonra kalan donusum suresi
            t += T_DONUSUM_US - t_yaz
        else:
            t += sum(bekle_olc) + sum(dus_olc)
        t += 2 * t_oku
        return t

    senaryolar = [
        ("A. B20 ONCESI (olu bekleme + COMP_QUE=11b)", [4000], 2, False),
        ("B. yalniz COMP_QUE duzeltilse", [4000], 2, True),
        ("C. yalniz olu bekleme silinse", [], 0, False),
        ("D. B20 SONRASI (ikisi de)", [], 0, True),
    ]
    r.bilgi(f"     {'senaryo':<44} {'periyot':>9} {'SPS':>7} {'Nyquist':>8}")
    r.bilgi("     " + "-" * 71)
    hiz = {}
    for ad, ob, od, av in senaryolar:
        p = periyot(ob, od, av)
        hiz[ad[0]] = 1e6 / p
        r.bilgi(f"     {ad:<44} {p/1000:8.3f}ms {1e6/p:6.1f} {1e6/p/2:7.1f}Hz")
    r.bilgi("")
    r.bilgi("     ⚠ A senaryosunda delay(2) = vTaskDelay(2 tik) @1 kHz, yani")
    r.bilgi("       sabit 2000 us degil TIK SINIRINA yuvarlama; gercek periyot")
    r.bilgi("       11.0 ms'e KILITLENIYORDU. Buradaki 2000 us bir ALT SINIR.")
    r.kosul("  1c: B20 sonrasi hiz, oncesinin en az 5 katı",
            hiz["D"] / hiz["A"] >= 5.0,
            f"{hiz['A']:.0f} -> {hiz['D']:.0f} SPS ({hiz['D']/hiz['A']:.1f} kat)")
    r.kosul("  1c: iki duzeltme de GEREKLI — biri tek basina yetmiyor",
            hiz["B"] < 0.5 * hiz["D"] and hiz["C"] < 0.5 * hiz["D"],
            f"yalniz COMP_QUE {hiz['B']:.0f} · yalniz bekleme {hiz['C']:.0f} "
            f"· ikisi {hiz['D']:.0f} SPS")

    # [!] B22.1 (K1): AYNI TIK KILIDI, BIR KATMAN ASAGIDA.
    # Yukaridaki A senaryosu icin tik yuvarlamasi ZATEN biliniyordu
    # ("11.0 ms'e KILITLENIYORDU"), ama ayni mekanizmanin kutuphane
    # icindeki delay(1) icin de gecerli oldugu gorulmemisti. D senaryosu
    # "1502.8 us / 665 SPS" diyordu; gercekte handleClient()'in delay(1)'i
    # periyodu bir sonraki tik sinirina cekiyordu.
    TIK_US = 1000.0                      # CONFIG_FREERTOS_HZ = 1000
    p_govde = periyot([], 0, True)
    p_kilit = math.ceil(p_govde / TIK_US) * TIK_US
    r.bilgi("")
    r.bilgi(f"     TIK KILIDI (delay(1), enableDelay(false) OLMADAN):")
    r.bilgi(f"       govde {p_govde:.1f} us -> ceil({p_govde:.1f}/{TIK_US:.0f})"
            f" x {TIK_US:.0f} = {p_kilit:.0f} us = {1e6/p_kilit:.1f} SPS")
    r.bilgi(f"       enableDelay(false) ile: {1e6/p_govde:.1f} SPS")
    r.bilgi(f"       pay {p_kilit - p_govde:.1f} us — web tarafina eklenecek")
    r.bilgi(f"       her {p_kilit - p_govde:.0f} us bir sonraki basamaga atlatir")
    r.kosul("  1c: tik kilidi hizi anlamli olcude dusuruyordu",
            1e6 / p_kilit < 0.85 * (1e6 / p_govde),
            f"{1e6/p_govde:.1f} -> {1e6/p_kilit:.1f} SPS — B22.1'in "
            f"enableDelay(false) duzeltmesinin buyuklugu")

    alt(r, "1d · TEK ATISIN BELGELENMEMIS BEDELI")
    r.bilgi("     B17 sürekli kipten tek atisa gecerken bir bedel yazmadi:")
    r.bilgi("     tek atista I2C yazma+okuma donusumle SERILESIR, sureklide")
    r.bilgi("     ise donusum arka planda akar.")
    r.bilgi(f"     tek atis tavani : {hiz['D']:6.1f} SPS")
    r.bilgi(f"     surekli kip     : {T.ADS_SPS:6.1f} SPS")
    r.kosul("  1d: tek atis, surekli kipin hizina ULASAMIYOR",
            hiz["D"] < T.ADS_SPS,
            f"tavan {hiz['D']:.0f} SPS = nominalin %{hiz['D']/T.ADS_SPS*100:.0f}'i "
            f"— bu tek atisin BEDELI, B17 yazmamisti")
    return hiz["D"]


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — LAGRANGE KESIRLI GECIKMENIN BANT SINIRI
# ═══════════════════════════════════════════════════════════════════════

def lagrange_katsayi(d):
    n = [-1.0, 0.0, 1.0, 2.0]
    h = []
    for k in n:
        p = 1.0
        for j in n:
            if j != k:
                p *= (d - j) / (k - j)
        h.append(p)
    return h


def lagrange_yanit(d, f_norm):
    """(genlik, gerceklesen gecikme - d) ornek cinsinden."""
    h = lagrange_katsayi(d)
    w = 2 * math.pi * f_norm
    re_ = sum(h[k] * math.cos(-w * (k - 1)) for k in range(4))
    im = sum(h[k] * math.sin(-w * (k - 1)) for k in range(4))
    genlik = math.hypot(re_, im)
    if w < 1e-12:
        return genlik, 0.0
    faz = math.atan2(im, re_)
    gecikme = -faz / w
    return genlik, gecikme - d


def bolum2(r, fs):
    bolum(r, "BOLUM 2 — LAGRANGE KESIRLI GECIKMENIN BANT SINIRI")
    r.bilgi("  olcum3.h'deki yorum soyle diyor:")
    r.bilgi('    "Guvenilir wattmetre bandi ~5 kHz"')
    r.bilgi("  Bu HIZLI YOL icin dogru (41.7 kSa/s). ADS yolu ayni suzgeci")
    r.bilgi(f"  {fs:.0f} SPS'te kullaniyor — orada bant BAMBASKA.")
    r.bilgi("")

    # firmware'in gercek d'si: t_kayma / T
    d_ger = i2c_us(BIT_YAZ) / (1e6 / fs)
    r.bilgi(f"     Firmware'in gercek d'si = t_kayma/T = "
            f"{i2c_us(BIT_YAZ):.1f}/{1e6/fs:.1f} = {d_ger:.4f} ornek")
    r.bilgi("")
    r.bilgi(f"     {'f (Hz)':>7} {'f/fs':>7} {'|H| (d gercek)':>15} "
            f"{'|H| (d=0.5)':>13} {'faz hatasi (der)':>17}")
    r.bilgi("     " + "-" * 64)
    for f in (1, 10, 50, 60, 100, 200, 300, 400, 430):
        if f >= fs / 2:
            break
        g1, dg1 = lagrange_yanit(d_ger, f / fs)
        g2, _ = lagrange_yanit(0.5, f / fs)
        r.bilgi(f"     {f:>7} {f/fs:>7.4f} {g1:>15.6f} {g2:>13.6f} "
                f"{360*f*dg1/fs:>17.4f}")

    # d TAM SAYI ise suzgec saf gecikmeye doner — kirpma sinirlari zararsiz
    alt(r, "2b · d TAM SAYI oldugunda genlik TAM 1 (kirpma zararsiz)")
    en_sapma = 0.0
    for d in (-1.0, 0.0, 1.0, 2.0):
        for f in (1, 50, 200, 400):
            if f >= fs / 2:
                continue
            g, _ = lagrange_yanit(d, f / fs)
            en_sapma = max(en_sapma, abs(g - 1.0))
    r.kosul("  2b: d = -1/0/1/2'de genlik her frekansta 1",
            en_sapma < 1e-9,
            f"en buyuk sapma {en_sapma:.2e} — olcum_al'daki [-1,2] kirpmasi "
            f"kendi basina genlik hatasi URETMIYOR")

    # bant siniri
    alt(r, "2c · %X sarkma sinirini veren ust frekans")
    d_kotu = 1.0 + 0.0817        # F=+1 ile ulasilabilen en kotu d
    r.bilgi(f"     {'sinir':>8} {'d gercek':>10} {'d = 0.5':>9} "
            f"{'en kotu d':>11}")
    r.bilgi("     " + "-" * 42)
    sinirlar = {}
    for lim in (0.001, 0.005, 0.01, 0.02, 0.05):
        satir = []
        for d in (d_ger, 0.5, d_kotu):
            f = 0.0
            while f < fs / 2:
                f += 0.25
                g, _ = lagrange_yanit(d, f / fs)
                if abs(g - 1.0) > lim:
                    break
            satir.append(f)
        sinirlar[lim] = satir
        r.bilgi(f"     {lim*100:7.1f}% {satir[0]:9.1f} {satir[1]:8.1f} "
                f"{satir[2]:10.1f}")

    # `f` komutunun siniri koddan okunuyor
    m = re.search(r"f > ([0-9.]+)f", yorumsuz(INO))
    f_sinir = float(m.group(1))
    r.bilgi("")
    r.bilgi(f"     `f` komutunun ust siniri (koddan okundu): {f_sinir:.0f} Hz")
    en_kotu_f = sinirlar[0.02][2]
    r.kosul("  2c: `f` siniri, %2 sarkma bandinin ICINDE",
            f_sinir <= en_kotu_f,
            f"{f_sinir:.0f} Hz <= {en_kotu_f:.1f} Hz (izin verilen en kotu d)")
    r.kosul("  2c: `f` siniri Nyquist'in altinda",
            f_sinir < fs / 2,
            f"{f_sinir:.0f} Hz < {fs/2:.1f} Hz")

    alt(r, "2d · 'FAZ HATASI TAM SIFIR' yalnizca d = 0.5 icin dogru")
    r.bilgi("     olcum3.h:278 ve sim3_senkron.py:209 bunu KOSULSUZ yaziyor.")
    r.bilgi("     Lagrange yalnizca d = 0.5'te SIMETRIK, yani dogrusal fazli.")
    _, dg_yarim = lagrange_yanit(0.5, 200.0 / fs)
    _, dg_ger = lagrange_yanit(d_ger, 200.0 / fs)
    r.bilgi(f"     200 Hz'te faz gecikmesi hatasi: d=0.5 -> {dg_yarim:.3e} ornek"
            f" · d={d_ger:.4f} -> {dg_ger:.3e} ornek")
    r.kosul("  2d: d = 0.5'te faz hatasi gercekten sifir",
            abs(dg_yarim) < 1e-9, f"{dg_yarim:.2e} ornek")
    r.kosul("  2d: firmware'in kullandigi d'de faz hatasi SIFIR DEGIL",
            abs(dg_ger) > 1e-6,
            f"{dg_ger:.3e} ornek — B17'nin kosulsuz iddiasi yanlis")
    return f_sinir


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — FAZ KALIBRASYONU TEK FREKANSTA
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r, fs, f_sinir):
    bolum(r, "BOLUM 3 — FAZ KALIBRASYONU TEK FREKANSTA YAPILIYOR")
    r.bilgi("  `F<ornek>` SABIT bir zaman gecikmesi sakliyor. Duzelttigi sey")
    r.bilgi("  ise suzgec eslesmezligi:")
    r.bilgi("      dfaz(f) = atan(2*pi*f*tau_i) - atan(2*pi*f*tau_v)")
    r.bilgi("  Sabit gecikme DOGRUSAL faz verir, arctan farki VERMEZ —")
    r.bilgi("  ikisi yalnizca TEK bir frekansta ortusur.")
    r.bilgi("")
    r.bilgi(f"     tau_NORMAL {TAU_V*1e3:.4f} ms · tau_YUKSEK {TAU_Y*1e3:.4f} ms"
            f" · tau_AKIM {TAU_I*1e3:.4f} ms")

    def dfaz(f, tau_v):
        return math.degrees(math.atan(2*math.pi*f*TAU_I)
                            - math.atan(2*math.pi*f*tau_v))

    # 50 Hz'te tam duzelten sabit gecikme
    dt_kal = dfaz(SEBEKE_HZ, TAU_V) / (360.0 * SEBEKE_HZ)     # saniye
    r.bilgi(f"     50 Hz'te eslesmezlik {dfaz(SEBEKE_HZ, TAU_V):+.4f} derece")
    r.bilgi(f"     -> tam duzelten sabit gecikme {dt_kal*1e6:+.2f} us "
            f"= {dt_kal*fs:+.5f} ornek")
    r.bilgi("")
    r.bilgi(f"     {'f (Hz)':>7} {'gercek dfaz':>13} {'kalibrasyonun':>15} "
            f"{'KALAN':>9} {'PF=0.5 hata':>13}")
    r.bilgi("     " + "-" * 62)
    for f in (1, 10, 50, 60, 100, 200, 400):
        ger = dfaz(f, TAU_V)
        kal = 360.0 * f * dt_kal
        kalan = ger - kal
        hata = (math.cos(math.radians(60.0 + kalan))
                / math.cos(math.radians(60.0)) - 1) * 100
        im = "" if f <= f_sinir else "  <- `f` sinirinin USTUNDE"
        r.bilgi(f"     {f:>7} {ger:>12.4f}° {kal:>14.4f}° {kalan:>8.4f}° "
                f"{hata:>12.3f}%{im}")

    alt(r, "3b · [!] ASIL SINIR BURADA: KONDANSATOR TOLERANSI")
    r.bilgi("     Yukarisi NOMINAL parcayla. Gercekte eslesmeyi C2 ile C18'in")
    r.bilgi("     GERCEK degerleri belirliyor (B16/DEVIR 5.12.26: envanterde")
    r.bilgi("     tolerans yazmiyor, parcanin uzerindeki harf okunmali —")
    r.bilgi("     J = %5, K = %10). Sabit ZAMAN gecikmesiyle kalibre edilen")
    r.bilgi("     kart, kalibrasyon frekansindan uzaklasinca AKTIF ZARAR verir:")
    r.bilgi("")
    r.bilgi(f"     {'f':>6}  " + "  ".join(f"{'tol ±%d%%' % int(t*100):>9}"
                                          for t in (0.01, 0.05, 0.10)))
    r.bilgi("     " + "-" * 44)

    def kalan_tol(f, tol):
        tv, ti = TAU_V * (1 - tol), TAU_I * (1 + tol)

        def dft(x):
            return math.degrees(math.atan(2*math.pi*x*ti)
                                - math.atan(2*math.pi*x*tv))
        dtk = dft(SEBEKE_HZ) / (360.0 * SEBEKE_HZ)
        return dft(f) - 360.0 * f * dtk

    for f in (50, 60, 100, 150, 200, 400):
        s = "  ".join(f"{kalan_tol(f, t):>8.2f}°" for t in (0.01, 0.05, 0.10))
        r.bilgi(f"     {f:>5}  {s}")

    # SEBEKE BANDI — kartin gercekten gecerli oldugu yer.
    # Olcut FAZ degil GUC: kullaniciyi ilgilendiren o.
    def guc_hatasi(kalan_der, theta=60.0):
        return abs(math.cos(math.radians(theta + kalan_der))
                   / math.cos(math.radians(theta)) - 1) * 100

    sebeke_bandi = (40, 45, 50, 55, 60, 65, 70)
    en_sebeke = max(abs(kalan_tol(f, 0.10)) for f in sebeke_bandi)
    en_guc = max(guc_hatasi(kalan_tol(f, 0.10)) for f in sebeke_bandi)
    r.bilgi("")
    r.bilgi(f"     50 Hz'te kalibre edilmis kart, ±%10 tolerans kosesi,")
    r.bilgi(f"     40-70 Hz bandinda: en kotu kalan faz {en_sebeke:.2f}°,")
    r.bilgi(f"     PF=0.5'te guc hatasi en kotu %{en_guc:.1f}")
    r.bilgi("     (en kotu nokta 50 Hz'ten EN UZAK olan 40 Hz — kalibrasyon")
    r.bilgi("      frekansindan uzaklastikca bozuluyor, simetrik degil.)")
    r.kosul("  3b: SEBEKE bandinda (40-70 Hz) PF=0.5 guc hatasi %10'un altinda",
            en_guc < 10.0,
            f"en kotu %{en_guc:.1f} — kart bu bantta kalibre edilebilir; "
            f"100 Hz'te %20.5, 200 Hz'te %56.3 olacakti")
    # `f` sinirinda ne oluyor — SAYIYI TESTE BAGLA, gizleme
    k_sinir = abs(kalan_tol(f_sinir, 0.10))
    guc_sinir = abs(math.cos(math.radians(60.0 + kalan_tol(f_sinir, 0.10)))
                    / math.cos(math.radians(60.0)) - 1) * 100
    r.bilgi("")
    r.bilgi(f"     `f` sinirinda ({f_sinir:.0f} Hz), ±%10 tolerans kosesi:")
    r.bilgi(f"       kalan faz {k_sinir:.2f}° -> PF=0.5'te guc hatasi "
            f"%{guc_sinir:.1f}")
    r.kosul("  3b: `f` siniri, kalan hatanin YONETILEBILIR oldugu yerde",
            guc_sinir < 25.0,
            f"%{guc_sinir:.1f} — 200 Hz'te %56.3, 400 Hz'te tamamen "
            f"gecersizdi. Sinir 400 -> {f_sinir:.0f} Hz'e cekildi")
    r.kosul("  3b: firmware sebeke bandi disinda UYARIYOR",
            "40.0f" in yorumsuz(INO) and "70.0f" in yorumsuz(INO),
            "`f` komutu 40-70 Hz disinda faz kalibrasyonunun gecerliligini "
            "yitirdigini yaziyor")
    r.bilgi("")
    r.bilgi("     [!] ACIK TASARIM SORUSU (DEVIR 5.12.30'a yazildi):")
    r.bilgi("       Kalibrasyon SABIT GECIKME yerine TAU ESLESMEZLIGI olarak")
    r.bilgi("       saklanirsa (olculen fazdan tau_i_etkin cozulup her")
    r.bilgi("       frekansta arctan farki hesaplanirsa) bant genisler.")
    r.bilgi("       Maliyeti iki atanf(). UYGULANMADI — `F` komutunun anlamini")
    r.bilgi("       degistirir ve tezgahta dogrulanmadan yapilmamali.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — OLCEK DUZELTMESININ FREKANS BAGIMLILIGI
# ═══════════════════════════════════════════════════════════════════════

def bolum4(r, fs, f_sinir):
    bolum(r, "BOLUM 4 — 1/|H(f)| OLCEK DUZELTMESI FREKANSLA NE YAPIYOR")

    def carpan(f, tau):
        return math.sqrt(1 + (2*math.pi*f*tau)**2)

    r.bilgi(f"     {'f (Hz)':>7} {'NORMAL':>9} {'AKIM':>9} {'GUC carpani':>12} "
            f"{'tau %1 -> guc':>14}")
    r.bilgi("     " + "-" * 56)
    for f in (1, 10, 50, 60, 100, 200, 400):
        cn, ca = carpan(f, TAU_V), carpan(f, TAU_I)
        # tau'da %1 hatanin guce etkisi
        c2 = carpan(f, TAU_V*1.01) * carpan(f, TAU_I*1.01)
        duyar = (c2 / (cn*ca) - 1) * 100
        isaret = "" if f <= f_sinir else "   <- `f` sinirinin USTUNDE"
        r.bilgi(f"     {f:>7} {cn:>9.4f} {ca:>9.4f} {cn*ca:>12.4f} "
                f"{duyar:>13.3f}%{isaret}")

    c_sinir = carpan(f_sinir, TAU_V) * carpan(f_sinir, TAU_I)
    c_400 = carpan(400, TAU_V) * carpan(400, TAU_I)
    r.kosul("  4: `f` sinirinda olcek carpani makul kaliyor",
            c_sinir < 20.0,
            f"{f_sinir:.0f} Hz'te {c_sinir:.2f}x — 400 Hz'te {c_400:.1f}x "
            f"olacakti, tau hatasina o kadar duyarli")
    r.bilgi("")
    r.bilgi("     ⚠ Duzeltme YALNIZCA o.watt'a uygulaniyor; D satirindaki V ve")
    r.bilgi("       I ARITMETIK ORTALAMA, RMS degil. AC'de ikisi de ~0 okur.")
    r.bilgi("       Bu bir kusur DEGIL ama BELGELENMEMISTI: ADS yolu bir")
    r.bilgi("       WATTMETRE yoludur, AC voltmetre degil.")
    g_loop = yorumsuz(govde(INO, "void loop()"))
    r.kosul("  4: D satiri gercekten ORTALAMA veriyor (RMS iddiasi yok)",
            "v_top / ornek" in g_loop.replace("  ", " "),
            "v_top/ornek — sqrt yok, RMS degil")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 5 — [!] OTOMATIK MENZIL AC'DE
# ═══════════════════════════════════════════════════════════════════════

def menzil_benzet(tepe_v, fs, yeni_mantik, sure_s=1.0):
    """menzil_gozet'i taklit edip 1 s'te kac gecis oldugunu sayar."""
    n = T.KANALLAR[0]
    normal_fs = n["pga"] * ((n["rust"] + n["ralt"]) / n["ralt"]) - 1.7153125
    ust, alt_ = 0.90 * normal_fs, 0.70 * normal_fs
    menzil, gecis, doyan = 0, 0, 0
    tepe_simdi = tepe_onceki = 0.0
    pencere_us = 1e6 / SEBEKE_HZ
    t_pencere = t_kilit = 0.0
    dt = 1e6 / fs
    N = int(sure_s * fs)
    for k in range(N):
        t = k * dt
        v = tepe_v * math.sin(2 * math.pi * SEBEKE_HZ * t * 1e-6)
        m = abs(v)
        if menzil == 0 and m > normal_fs:
            doyan += 1
        if yeni_mantik:
            if m > tepe_simdi:
                tepe_simdi = m
            if t - t_pencere >= pencere_us:
                tepe_onceki, tepe_simdi, t_pencere = tepe_simdi, 0.0, t
            tepe = max(tepe_onceki, tepe_simdi)
            if t - t_kilit < pencere_us:
                continue
            if menzil == 0 and m > ust:
                menzil, gecis, t_kilit = 1, gecis + 1, t
            elif menzil == 1 and tepe < alt_:
                menzil, gecis, t_kilit = 0, gecis + 1, t
        else:
            if menzil == 0 and m > ust:
                menzil, gecis = 1, gecis + 1
            elif menzil == 1 and m < alt_:
                menzil, gecis = 0, gecis + 1
    return gecis, doyan / max(1, N) * 100


def bolum5(r, fs):
    bolum(r, "BOLUM 5 — [!] OTOMATIK MENZIL AC'DE CALISMIYORDU")
    r.bilgi("  Esikler ANLIK |v|'ye uygulaniyordu. Bir sinusun genligi her")
    r.bilgi("  yarim cevrimde asagi esigin altina inip tepede yukari esigi")
    r.bilgi("  asiyor -> saniyede yuzlerce menzil degisimi.")
    r.bilgi("")
    r.bilgi(f"     {'tepe (V)':>9} {'ESKI gecis/s':>13} {'ESKI doyan %':>13} "
            f"{'YENI gecis/s':>13} {'YENI doyan %':>13}")
    r.bilgi("     " + "-" * 66)
    en_eski, en_yeni = 0, 0
    for tepe in (25, 30, 35, 50, 100, 300):
        ge, de = menzil_benzet(tepe, fs, False)
        gy, dy = menzil_benzet(tepe, fs, True)
        en_eski, en_yeni = max(en_eski, ge), max(en_yeni, gy)
        r.bilgi(f"     {tepe:>9} {ge:>13} {de:>12.1f}% {gy:>13} {dy:>12.1f}%")
    r.kosul("  5: ESKI mantik AC'de chatter yapiyordu (kusur GERCEK)",
            en_eski > 20,
            f"en cok {en_eski} gecis/s — her gecis menzil_uygula'nin "
            f"~1518 us'sini odetiyor")
    r.kosul("  5: YENI mantik chatter'i kesiyor",
            en_yeni <= 2,
            f"en cok {en_yeni} gecis/s")

    alt(r, "5b · Duzeltme firmware'de gercekten uygulanmis mi")
    g_goz = yorumsuz(govde(INO, "static void menzil_gozet"))
    r.kosul("  5b: ASAGI karari pencere TEPESI ile veriliyor",
            re.search(r"menzil\s*==\s*1.*?tepe\s*<", g_goz, re.S) is not None,
            "anlik |v| degil, bir sebeke cevriminde tutulan tepe")
    r.kosul("  5b: YUKARI karari hala ANLIK (doymayi onlemek icin)",
            re.search(r"menzil\s*==\s*0.*?\bm\s*>", g_goz, re.S) is not None,
            "yukari yon hizli olmali")
    r.kosul("  5b: gecis sonrasi SUSTURMA var",
            "menzil_kilit_us" in g_goz,
            "bir sebeke cevrimi boyunca yeni gecis yok")

    alt(r, "5c · Tampon: menzil degisiminde DOYMUS ornekler tasiniyordu")
    g_uyg = yorumsuz(govde(INO, "static void menzil_uygula"))
    r.kosul("  5c: menzil_uygula'nin okudugu ornek ARTIK ATILMIYOR",
            "hv_tampon[0]" in g_uyg,
            "eskiden ads_oku'nun sonucu atiliyordu; artik tamponu tazeliyor")
    r.kosul("  5c: tazeleme KOSULLU (yalnizca doymus ornek varsa)",
            "hv_doydu" in g_uyg,
            "doymamis ornekler zaten dogru; bosuna tazelemek V/I hizasini "
            "bir ornek bozardi")
    r.kosul("  5c: doygunluk hem ADS'i hem yazilim kelepcesini sayiyor",
            "gerilim_doydu" in INO and "32767" in govde(INO, "static bool gerilim_doydu"),
            "olc_gerilim3'un int16 kelepcesi NORMAL kanalda ADS'ten ONCE giriyor")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 6 — YAPISAL AYRISMA DENETIMLERI
# ═══════════════════════════════════════════════════════════════════════

def bolum6(r):
    bolum(r, "BOLUM 6 — AYRISMA: AYNI SAYI IKI DOSYADA")

    alt(r, "6a · Ayar3 imzasi TEK KAYNAK mi")
    r.bilgi("     B17 'imza 0xC0F3 -> 0xC0F4' dedi ama yalnizca tipler3.h'yi")
    r.bilgi("     degistirdi; .ino elle 0xC0F3 yazmaya devam ediyordu — yani")
    r.bilgi("     NVS'e hep ESKI imza gidiyor, surum damgasi hicbir sey")
    r.bilgi("     korumuyordu.")
    imza_tanim = re.findall(r"#define\s+AYAR3_IMZA\s+(0x[0-9A-Fa-f]+)", TIP_H)
    ino_y = yorumsuz(INO)
    ino_sabit = re.findall(r"imza\s*(?:!=|=)\s*(0x[0-9A-Fa-f]+)", ino_y)
    r.bilgi(f"     tipler3.h  #define AYAR3_IMZA : {imza_tanim}")
    r.bilgi(f"     .ino icinde ELLE yazilmis imza sabitleri: "
            f"{ino_sabit or 'YOK'}")
    r.kosul("  6a: imza tek yerde tanimli", len(imza_tanim) == 1,
            f"AYAR3_IMZA = {imza_tanim[0] if imza_tanim else '?'}")
    r.kosul("  6a: .ino'da elle yazilmis imza sabiti YOK",
            not ino_sabit, "ayar_yukle ve ayar_kaydet AYAR3_IMZA kullaniyor")
    r.kosul("  6a: varsayilan_ayar3 da ayni sabiti kullaniyor",
            "a->imza = AYAR3_IMZA" in TIP_H, "ucu de tek kaynaktan")

    alt(r, "6b · tau sabitleri tasarim3_sabit.py ile ayrismis mi")
    r.bilgi("     ⚠ test_olcum3.py bunu 1e-3 s TOLERANSLA siniyor; tau ~2.9 ms")
    r.bilgi("       oldugu icin bu %35 tolerans demek. Burada SIKI sinaniyor.")
    tau_kod = {
        "NORMAL": float(re.search(r"TAU_NORMAL\s+([0-9.]+)f", OLC_H).group(1)),
        "YUKSEK": float(re.search(r"TAU_YUKSEK\s+([0-9.]+)f", OLC_H).group(1)),
        "AKIM": float(re.search(r"TAU_AKIM\s+([0-9.]+)f", OLC_H).group(1)),
    }
    tau_kaynak = {"NORMAL": TAU_V, "YUKSEK": TAU_Y, "AKIM": TAU_I}
    for ad in ("NORMAL", "YUKSEK", "AKIM"):
        r.esit(f"  6b: TAU_{ad} tasarim3_sabit ile ayni",
               tau_kod[ad], tau_kaynak[ad], 0.001, " s")

    alt(r, "6c · skop ADIMI DORT DOSYADA — ayrismis mi")
    r.bilgi("     B19 'sabit ayrismasi denetimi' yapmisti ama yalnizca")
    r.bilgi("     SKOP_ORAN ve VREF'e bakti; ADIM'i atladi. Sonuc: firmware")
    r.bilgi("     ve arayuzun iki kopyasi 3.10 V kullanirken tasarim3_sabit")
    r.bilgi("     2.9 V kullaniyordu — %6.92 ayrisma, hicbir iddia gormedi.")
    r.bilgi("")
    tavan = float(re.search(r"SKOP_ADC_TAVAN\s+([0-9.]+)f", OLC_H).group(1))
    sayim = float(re.search(r"SKOP_ADC_SAYIM\s+([0-9.]+)f", OLC_H).group(1))
    oran = float(re.search(r"SKOP_ORAN\s+([0-9.]+)f", OLC_H).group(1))
    APP = (KOK / "arayuz3" / "app.js").read_text(encoding="utf-8",
                                                 errors="replace")
    SAHTE = (KOK / "arayuz3" / "sahte-kart.js").read_text(encoding="utf-8",
                                                          errors="replace")
    m_app = re.search(r"\(([0-9.]+)\s*/\s*([0-9.]+)\s*\*\s*([0-9.]+)\)", APP)
    s_tav = float(re.search(r"ADC_TAVAN\s*=\s*([0-9.]+)", SAHTE).group(1))
    s_say = float(re.search(r"ADC_SAYIM\s*=\s*([0-9.]+)", SAHTE).group(1))
    s_oran = float(re.search(r"BOLME_ORANI\s*=\s*([0-9.]+)", SAHTE).group(1))

    kopyalar = {
        "tasarim3_sabit.py": T.SKOP_ADIM,
        "kod/olcum3.h": tavan / sayim * oran,
        "arayuz3/app.js": (float(m_app.group(1)) / float(m_app.group(2))
                           * float(m_app.group(3))),
        "arayuz3/sahte-kart.js": s_tav / s_say * s_oran,
    }
    for ad, v in kopyalar.items():
        r.bilgi(f"     {ad:<24} {v*1e3:9.4f} mV/adim")
    en, az = max(kopyalar.values()), min(kopyalar.values())
    r.kosul("  6c: dort kopyanin skop adimi AYNI",
            (en - az) / az < 1e-6,
            f"yayilim %{(en/az - 1)*100:.4f} — hepsi {en*1e3:.4f} mV")
    r.bilgi("")
    r.bilgi("     ⚠ Bu denetim dordunun AYNI oldugunu sinar, DOGRU oldugunu")
    r.bilgi("       degil. 3.1 V bir veri sayfasi nominali; ESP32 ADC'sinin")
    r.bilgi("       gercek tam olcegi yongaya gore degisiyor ve dogrusal")
    r.bilgi("       degil — TEZGAHTA kalibre edilmeli.")

    alt(r, "6d · ADS ESD diyodu: SKALER ile SPICE MODELI ayrismis mi")
    r.bilgi("     ADS1115'in ic ESD diyodunun ileri gerilimi IKI yerde:")
    r.bilgi("       * tasarim3_sabit.ADS_ESD_VF — elle hesapta kullanilan sayi")
    r.bilgi("       * sim3_ariza.D_ESD          — ngspice .model satiri")
    r.bilgi("     Hicbir sey ikisini birbirine baglamiyordu; biri degisse")
    r.bilgi("     otekinin haberi olmazdi.")
    ariza = (BURASI / "sim3_ariza.py").read_text(encoding="utf-8",
                                                 errors="replace")
    m_esd = re.search(r'D_ESD\s*=\s*"[^"]*IS=([0-9.Ee+-]+)\s+N=([0-9.]+)'
                      r'\s+RS=([0-9.]+)', ariza)
    IS_, N_, RS_ = (float(m_esd.group(1)), float(m_esd.group(2)),
                    float(m_esd.group(3)))
    VT = 0.025852                      # kT/q @ 300 K
    I_TASARIM = T.ADS_TASARIM_AKIM_HEDEFI
    vf_model = N_ * VT * math.log(I_TASARIM / IS_) + I_TASARIM * RS_
    r.bilgi("")
    r.bilgi(f"     SPICE modeli: IS={IS_:.2e} N={N_} RS={RS_}")
    r.bilgi(f"     Vf({I_TASARIM*1e3:.0f} mA) = N*Vt*ln(I/IS) + I*RS = "
            f"{vf_model*1e3:.1f} mV")
    r.bilgi(f"     Skaler ADS_ESD_VF            = "
            f"{T.ADS_ESD_VF*1e3:.1f} mV  (TI: ~500 mV)")
    r.esit("  6d: SPICE ESD modeli skaler ADS_ESD_VF ile ayni",
           vf_model, T.ADS_ESD_VF, 0.05, " V")
    r.bilgi("")
    r.bilgi("     ⚠ B2 (sim3_giris.py) BILEREK farkli bir model kullaniyor")
    r.bilgi("       (genel silisyum, Vf ~0.655 V). Bu bir ayrisma DEGIL,")
    r.bilgi("       sim3_ariza.py'de gerekcesi yazili bir SECIM: 500 mV daha")
    r.bilgi("       dusuk kelepce, yani daha cok akim, yani DAHA KOTUMSER.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 7 — BLOKLAYAN HTTP ISLEYICISI
# ═══════════════════════════════════════════════════════════════════════

def bolum7(r):
    bolum(r, "BOLUM 7 — [!] SSE ISLEYICISI loop()'U KILITLIYORDU")
    r.bilgi("  akis_sayfa(), loop() icindeki sunucu.handleClient()'tan")
    r.bilgi("  cagriliyor. Icinde `while (c.connected())` oldugu icin istemci")
    r.bilgi("  bagli kaldigi surece GERI DONMUYORDU: olcum_al kosmuyor,")
    r.bilgi("  enerji birikmiyor, ve son_satir'i YALNIZCA loop() yazdigi icin")
    r.bilgi("  akisa tek bir bayat satir gidip sonsuza kadar susuyordu.")
    r.bilgi("")
    g = yorumsuz(govde(INO, "void akis_sayfa()"))
    r.kosul("  7: akis_sayfa icinde while dongusu YOK",
            "while" not in g, "durum makinesine cevrildi")
    r.kosul("  7: akis_sayfa icinde IC ICE handleClient cagrisi YOK",
            "handleClient" not in g,
            "eskiden handleClient icinden handleClient cagriliyordu — "
            "ozyineleme riski")
    r.kosul("  7: akis_sayfa icinde delay YOK",
            "delay" not in g, "isleyici hemen donuyor")
    # 🔴 B26: BU IDDIA BAYATLAMISTI. B20 `loop()`a acik bir `akis_yolla`
    #    cagrisi koymus ve "SSE loop()'tan besleniyor" diye sinamisti.
    #    B22.4 `Serial` aynasini (WebAkis) getirdi: `Serial.println` ile
    #    yazilan HER satir zaten `web_satir_hazir` -> `akis_yolla` yolundan
    #    gidiyor. Acik cagri kaldirilmadigi icin her `D` satiri SSE'ye IKI
    #    KEZ dustu (kartta olculdu: 80 olay / 40 benzersiz). Cagri
    #    kaldirilinca bu iddia kirmiziya dondu — cunku ESKI mekanizmayi
    #    ariyordu. Dogru iddia: loop() `D` satirini SERIAL'E yaziyor
    #    (aynanin tetiklenmesi icin bu yeter), dogrudan akisa DEGIL.
    #    Tek-cagri-yeri iddiasi sim3_web.py'de (1b).
    g_loop = yorumsuz(govde(INO, "void loop()"))
    r.kosul("  7: loop() `D` satirini Serial'e yaziyor (ayna SSE'ye tasir)",
            "Serial.println(son_satir)" in g_loop,
            "aynayi tetikleyen tek sey Serial yazmasi")
    r.kosul("  7: loop() akisa DOGRUDAN yazmiyor (ayna ile cift olurdu)",
            "akis_yolla" not in g_loop,
            "B26: acik cagri + ayna = her satir iki kez")

    # --- 8. B27/K1: YANIT VERMEYEN ADC SESSIZ KALMASIN
    alt(r, "8 · K1: ADC yanit vermezse `durum` alani ve enerji kapisi")
    r.bilgi("     Gercek kartta tek ADS ile gorulen: 0x49 yokken firmware")
    r.bilgi("     sessizce 0 donuyor, kalibrasyon o sifira uygulaniyor ve")
    r.bilgi("     ekranda kendinden emin '1.716 V' cikiyordu — ters cevrilmis")
    r.bilgi("     n_sifir. Cip bozulunca da ayni sahte sayi. Enerji de bu")
    r.bilgi("     copla birikiyordu (0.03 J / 3 dk, bos giristen).")
    r.bilgi("")
    g_oku = yorumsuz(govde(INO, "static int16_t ads_oku"))
    # `if (Wire.available() < 2)` blogunun ICINDE hata biti kurulmali
    _m = re.search(r"if\s*\(\s*Wire\.available\(\)\s*<\s*2\s*\)\s*\{([^}]*)\}",
                   g_oku)
    # ⚠ `\bads_hata\s*\|=` — kelime siniri SART. Ilk yazim `"ads_hata" in
    #   blok` idi ve mutasyon KACTI: `ads_hata_pencere |= bit;` satiri alt
    #   dizge olarak eslesip iddiayi yesil tutuyordu (hafizadaki "alt dizge
    #   tuzagi", bir kez daha).
    r.kosul("  8: ads_oku okuma basarisizken hata bitini KURUYOR",
            bool(_m) and re.search(r"\bads_hata\s*\|=", _m.group(1)) is not None,
            "kurmazsa `durum` hep 0 kalir ve arayuz sahte sayiyi olcum sanir")
    r.kosul("  8: ads_oku okuma basariliyken hata bitini TEMIZLIYOR",
            re.search(r"ads_hata\s*&=\s*~", g_oku) is not None,
            "temizlemezse bir kez dusen cip sonsuza kadar 'yok' gorunur")
    r.kosul("  8: loop() enerjiyi ADC hatasi YOKKEN biriktiriyor",
            re.search(r"if\s*\(\s*!\s*ads_hata\s*\)\s*enerji_biriktir", g_loop)
            is not None,
            "kapisiz olursa yanit vermeyen cipin copu Wh sayacina girer")
    _d = re.search(r'"D (%[^"]*)"', INO)
    r.kosul("  8: `D` bicimi `durum` alanini tasiyor (9 alan)",
            bool(_d) and _d.group(1).count("%") == 9,
            f"{_d.group(1).count('%') if _d else '?'} alan")
    r.kosul("  8: afis ilani `<durum>` diyor",
            "<menzil> <durum>" in INO,
            "kosucu ve arayuz indeksi bu ilandan turetiyor")

    # --- 9. B27/K4: ARAYUZ METNI SABITLE AYNI MI
    alt(r, "9 · K4: skop yardim metni tasarim sabitiyle ayni")
    r.bilgi("     index.html 'Menzil 0 – 48.7 V, tek yönlü' diyordu; B19 skopu")
    r.bilgi("     cift yonlu yapmisti (-63.5 … +46.8 V). Arayuz Python sabitini")
    r.bilgi("     goremez (derleme yok) — o yuzden metin burada SABITLE")
    r.bilgi("     KARSILASTIRILIYOR. 'Ayni sayi kac dosyada duruyor?' dersi.")
    r.bilgi("")
    _html = (KOK / "arayuz3" / "index.html").read_text(encoding="utf-8",
                                                          errors="replace")
    # ⚠ HTML yorumlari CIKARILIYOR: aciklama yorumu eski ifadeyi ("tek
    #   yönlü") alintiliyor ve iddia ilk yazimda KENDI yorumunu yakaladi.
    _html = re.sub(r"<!--.*?-->", "", _html, flags=re.S)
    _eksi = f"{T.SKOP_MENZIL_EKSI:.1f}".replace("-", "−")   # tipografik eksi
    _arti = f"+{T.SKOP_MENZIL_ARTI:.1f}"
    r.kosul(f"  9: metin '{_eksi} … {_arti} V' diyor (sabitten)",
            f"Menzil {_eksi} … {_arti} V" in _html,
            f"SKOP_MENZIL_EKSI={T.SKOP_MENZIL_EKSI:.1f} "
            f"SKOP_MENZIL_ARTI={T.SKOP_MENZIL_ARTI:.1f} — metin sapmis")
    # --- 10. B27/K3: BOS GIRISTEN 223 W BASILMASIN
    alt(r, "10 · K3: hizli yol, giris raydaysa W basmiyor")
    r.bilgi("     GPIO4 bostayken ham ADC raya yapisik (~0) okunuyor; olcek o")
    r.bilgi("     degeri -63.5 V'a, akimi 3.5 A'e cevirip P=223.5667 W diye DORT")
    r.bilgi("     ondalikla basiyordu. Artik ham ortalama raydaysa (<%2 / >%98)")
    r.bilgi("     `! hizli yol: giris RAYDA` basilip W ATLANIYOR. Kartta 3/3.")
    r.bilgi("")
    g_hizli = yorumsuz(govde(INO, "static void hizli_yolla"))
    _ray = g_hizli.find("RAYDA")
    _olcek = g_hizli.find("hizli_olcekle(adet)")
    _w = g_hizli.find('Serial.print(F("W "))')
    r.kosul("  10: rayda denetimi hizli_olcekle'den ONCE",
            0 <= _ray < _olcek,
            "olcekten sonra ham kod kaybolur, rayda oldugu anlasilamaz")
    # `return;` RAYDA'dan SONRA ve hizli_olcekle'den ONCE olmali. Ilk yazim
    # `RAYDA[^}]*return;` idi — aradaki ic `if {}` bloklari yuzunden dogru
    # kodda bile eslesmiyordu.
    _ret = g_hizli.find("return;", _ray) if _ray >= 0 else -1
    r.kosul("  10: rayda denetimi W basilmadan ONCE ve return ediyor",
            0 <= _ray < _ret < _olcek and _ray < _w,
            "return olmazsa uyari basilir AMA W de basilir — sahte sayi yine ekrana gider")
    r.kosul("  10: esik ADC sayimindan turetiliyor (%2), elle yazilmiyor",
            "SKOP_ADC_SAYIM * 0.02f" in g_hizli,
            "82 diye sabit yazilsaydi ADC bit derinligi degisince sessizce kayardi")

    r.kosul("  9: metin 'çift yönlü' diyor, 'tek yönlü' DEGIL",
            "çift yönlü" in _html and "tek yönlü" not in _html,
            "B19 oncesi ifade geri gelmis olur")
    r.kosul("  7: baglanti kopunca istemci temizleniyor",
            "stop()" in yorumsuz(govde(INO, "static void akis_yolla")),
            "kopmus istemciye yazmaya devam edilmiyor")

    alt(r, "7b · ortalama_oku gercekten ortalama aliyor mu")
    r.bilgi("     TEK ATIS kipinde cip donusum bitince kapanir; yeni bir")
    r.bilgi("     OS=1 yazilmadikca donusum yazmaci DEGISMEZ. Eski govde")
    r.bilgi("     hicbir donusum baslatmadigi icin 16-32 okuma AYNI bayat")
    r.bilgi("     degeri okuyup 'ortalamasini' aliyordu.")
    g_ort = yorumsuz(govde(INO, "static int16_t ortalama_oku"))
    r.kosul("  7b: ortalama_oku her turda donusum BASLATIYOR",
            "ads_tek_atis_baslat" in g_ort,
            "yoksa gurultu azaltma tam sifir olurdu")
    r.kosul("  7b: kalibrasyon komutlari bunu kullaniyor",
            len(re.findall(r"ortalama_oku\(", yorumsuz(INO))) >= 4,
            "z / g / Z / i — dordu de tek gurultulu ornekle "
            "kalibre ediyordu")


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B20 — ORNEKLEME HIZI, BANT SINIRI VE MENZIL DAVRANISI")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI ve FIRMWARE'i sinar, kurulmus bir KARTI degil.")
    fs = bolum1(r)
    f_sinir = bolum2(r, fs)
    bolum3(r, fs, f_sinir)
    bolum4(r, fs, f_sinir)
    bolum5(r, fs)
    bolum6(r)
    bolum7(r)
    tamam = r.yazdir()
    # Bu adimin butun iddialari bir ZAMANLAMA MODELINE dayaniyor.
    # Modeli yalanlayacak tek sey gercek karttir.
    tezgah("B20 Ornekleme hizi ve bant", [
        ("[!] `D` satirindaki ORNEK SAYISI — ilk, en ucuz ve en onemli test",
         "200 ms'de 133 +-3 beklenir. ~100 cikarsa B22.1'in "
         "enableDelay(false)'u ISE YARAMAMIS; ~19 cikarsa B20'nin kendi "
         "duzeltmeleri cokmus. IKI AYRI kusur, ikisi de bu tek sayidan "
         "gorulur — o yuzden once bu olculur"),
        ("`Wire` gercekten 400 kHz mi",
         "Skopla SCL periyodunu olc. 100 kHz'e duserse V/I kaymasi DORT "
         "KAT buyur ve butun faz butcesi gecersizlesir"),
        ("[!] ALERT/RDY gercekten DARBE mi, MANDAL mi",
         "Skopla bak. Tek atista mandal olabilir — veri sayfasi kendisiyle "
         "CELISIYOR (5.12.30). Mandalsa `yeni_donusum_bekle` mantigi "
         "degismeli; bugunku kod darbe varsayiyor"),
        ("/HAZIR hattinda harici pull-up gerekiyor mu",
         "Bugun ESP32'nin dahili ~45 kOhm'una guveniliyor; en kotu yukselme "
         "11.1 us. Skopta yavas gorunuyorsa stoktaki 10K eklensin"),
        ("`t_kayma_us` gercekten ~95 us mi",
         "`?` ciktisinda gorunuyor. I2C yazma suresi hesabina dayaniyor "
         "(B17); sapma faz duzeltmesini kaydirir"),
        ("[!] `K` satiri — loop_azami_us",
         "`K <kayip_ms> <loop_azami_us> <uzun_tur>`. **20 000 us'yi "
         "gecerse CIFT CEKIRDEK karari tetiklenir** (5.12.34). Bu, o "
         "kararin TEK olcutu. Ayrica kayip_ms > 0 ise enerji sayaci "
         "aralik atlamis demektir"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
