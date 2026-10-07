# -*- coding: utf-8 -*-
"""B21 — PIL KAPASITE TESTI: anahtar, kapi surucusu, isil sinir, tampon.

    python sim3_pil.py

Harici TAS DIRENC yuk + karttaki IRFZ44N anahtar. MOSFET yalnizca AC/KAPA
yapiyor (dogrusal kip YOK), gucu tas direnc yiyor.

Bu adimin sinadigi sey TASARIM: kapi gerilimi yetiyor mu, arizada ne
oluyor, sogutucu gerekiyor mu, tampon RAM'e sigiyor mu, sayaclar tasiyor
mu. Kurulmus bir kart DEGIL.

VERI SAYFASI: INCHANGE (isc) IRFZ44N urun sartnamesi, sayfa 1-2.
⚠ Ikincil kaynak bir uretici. Elde parca olunca uzerindeki logo teyit
  edilmeli — tezgah listesinde var.
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
_KOD = KOK / "kod" / "olcum-karti-a3"
PH = (_KOD / "pil_test.h").read_text(encoding="utf-8", errors="replace")
INO = (_KOD / "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
TIP = (_KOD / "tipler3.h").read_text(encoding="utf-8", errors="replace")


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


def alt(r, baslik):
    r.bilgi("")
    r.bilgi(f"  --- {baslik} " + "-" * max(0, 62 - len(baslik)))


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 1 — [!] 3.3 V KAPI YETMEZ
# ═══════════════════════════════════════════════════════════════════════

def bolum1(r):
    bolum(r, "BOLUM 1 — [!] ESP32 IRFZ44N'i DOGRUDAN SUREMEZ")
    r.bilgi("  Stokta mantik seviyeli (IRL...) MOSFET YOK; elde olanlarin")
    r.bilgi("  hepsi standart kapili. Veri sayfasi:")
    r.bilgi(f"     Vgs(th)          : {T.IRFZ44N_VGS_TH[0]:.0f} .. "
            f"{T.IRFZ44N_VGS_TH[1]:.0f} V  (Vds=Vgs, Id=0.25 mA)")
    r.bilgi(f"     RDS(on) OLCUM KOSULU : Vgs = {T.IRFZ44N_VGS_SPEK:.0f} V")
    r.bilgi(f"     Vgs mutlak azami : ±{T.IRFZ44N_VGS_MUTLAK:.0f} V")
    r.bilgi("")
    ESP_V = 3.3
    r.bilgi(f"  ESP32 GPIO yuksek seviyesi: {ESP_V} V")
    r.kosul("  1: [!] 3.3 V kapi, esigin EN KOTU halinde ALTINDA",
            ESP_V < T.IRFZ44N_VGS_TH[1],
            f"{ESP_V} V < {T.IRFZ44N_VGS_TH[1]:.0f} V — MOSFET hic acilmayabilir")
    r.kosul("  1: 3.3 V, RDS(on)'un olculdugu kosulun cok altinda",
            ESP_V < 0.5 * T.IRFZ44N_VGS_SPEK,
            f"{ESP_V} V vs {T.IRFZ44N_VGS_SPEK:.0f} V — iyi halde bile "
            f"dogrusal bolgede kalir ve ISINIR")
    r.bilgi("")
    r.bilgi("  COZUM: kapi +12 V rayindan surulyor (B11 o rayi zaten koydu).")
    r.bilgi("     GPIO --4.7K--[2N2222]--10K--[BC557]-- +12 V")
    r.bilgi("                              |")
    r.bilgi("                        MOSFET kapisi --10K-- GND")
    r.kosul("  1: 12 V kapi, veri sayfasinin olcum kosulunu SAGLIYOR",
            T.PIL_KAPI_V >= T.IRFZ44N_VGS_SPEK,
            f"{T.PIL_KAPI_V:.0f} V >= {T.IRFZ44N_VGS_SPEK:.0f} V — "
            f"RDS(on) = {T.IRFZ44N_RDSON*1e3:.0f} m-ohm gecerli")
    r.kosul("  1: 12 V kapi, mutlak azaminin ALTINDA",
            T.PIL_KAPI_V < T.IRFZ44N_VGS_MUTLAK,
            f"{T.PIL_KAPI_V:.0f} V < {T.IRFZ44N_VGS_MUTLAK:.0f} V "
            f"(pay {T.IRFZ44N_VGS_MUTLAK - T.PIL_KAPI_V:.0f} V)")
    r.bilgi("")
    r.bilgi("  Surucunun parcalari STOKTA: 2N2222 (Q003 x12), BC557 (Q004 x7),")
    r.bilgi("  4.7K ve 10K dirençler. Satin alma GEREKMIYOR.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 2 — [!] ARIZADA NE OLUYOR (failsafe yonu)
# ═══════════════════════════════════════════════════════════════════════

def bolum2(r):
    bolum(r, "BOLUM 2 — [!] FAILSAFE YONU: ESP32 OLURSE YUK KAPANMALI")
    r.bilgi("  Bu, butun B21'in en onemli tek karari. Pil testi SAATLER")
    r.bilgi("  suruyor ve kimse basinda beklemiyor. ESP32 reset atarsa,")
    r.bilgi("  coker ya da WDT tetiklenirse GPIO'lar YUKSEK EMPEDANSA doner.")
    r.bilgi("  O anda kapinin nereye cekildigi pilin kaderini belirliyor.")
    r.bilgi("")
    r.bilgi(f"     {'kurulum':<28} {'GPIO yuksek-Z iken kapi':<26} {'sonuc'}")
    r.bilgi("     " + "-" * 70)
    r.bilgi(f"     {'kapi -> GND (SECILEN)':<28} {'0 V':<26} MOSFET KAPALI ✅")
    r.bilgi(f"     {'kapi -> +12 V (TERS)':<28} {'12 V':<26} MOSFET ACIK — pil "
            f"boşalmaya DEVAM EDER ❌")
    r.kosul("  2: kapi cekme direnci GND'ye (yukari DEGIL)",
            T.PIL_KAPI_CEKME_R > 0,
            f"{T.PIL_KAPI_CEKME_R/1e3:.0f}K kapi->GND — GPIO yuksek-Z'de "
            f"MOSFET KAPANIR")
    # Cekme direnci, kapi kacagini bastiracak kadar kucuk mu?
    # Veri sayfasi Igss <= 100 nA (Vgs = ±20 V).
    IGSS = 100e-9
    v_kacak = IGSS * T.PIL_KAPI_CEKME_R
    r.kosul("  2: cekme direnci kapi kacagini esigin COK altinda tutuyor",
            v_kacak < 0.1 * T.IRFZ44N_VGS_TH[0],
            f"Igss {IGSS*1e9:.0f} nA x {T.PIL_KAPI_CEKME_R/1e3:.0f}K = "
            f"{v_kacak*1e3:.2f} mV << {T.IRFZ44N_VGS_TH[0]:.0f} V esik")
    r.bilgi("")
    r.bilgi("  ⚠ Bu, ESP32'nin donanim WDT'sini BEDAVA bir emniyet yapiyor:")
    r.bilgi("    dongu takilirsa WDT reset atar, GPIO yuksek-Z olur, yuk kapanir.")
    r.bilgi("    (B20 tam da boyle bir dongu takilmasi buldu: SSE isleyicisi")
    r.bilgi("     loop()'u sonsuza kadar kilitliyordu.)")

    alt(r, "2b · SESSIZ HATA: yuk yanlis konnektore baglanirsa")
    r.bilgi("     J3 'Yuk donusu' DOGRUDAN sonte bagli (normal ampermetre")
    r.bilgi("     kullanimi). J7 'Pil testi yuk donusu' ise MOSFET'ten geciyor.")
    r.bilgi("     Kullanici yanlislikla J3'e baglarsa MOSFET BAYPAS edilir:")
    r.bilgi("     olcum calisir, grafik cizilir, ama KESME CALISMAZ ve kimse")
    r.bilgi("     fark etmez — pil asiri desarj olur.")
    r.bilgi("")
    r.bilgi("     DENETIM: test baslarken firmware MOSFET'i KAPALI tutup akima")
    r.bilgi("     bakar. Akim varsa yuk J3'te demektir -> TESTI REDDET.")
    esik = 3 * T.ADS_GURULTU[T.ADS_AKIM_KIRPMA] / 0.1     # 100 mohm sont
    r.kosul("  2b: baypas denetimi gurultuden ayirt edilebilir",
            esik < 0.05,
            f"esik 3-sigma = {esik*1e3:.1f} mA (100 m-ohm sont) — "
            f"en kucuk gercek yuk akimi bile ({0.1:.2f} A) bunun "
            f"{0.1/esik:.0f} kati")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 3 — ISIL SINIR: SOGUTUCU GEREKIYOR MU
# ═══════════════════════════════════════════════════════════════════════

def bolum3(r):
    bolum(r, "BOLUM 3 — MOSFET ISINMASI (dogrusal kip YOK, yalnizca RDS(on))")
    r.bilgi("  MOSFET yalnizca anahtar; guc TAS DIRENCTE yaniyor. MOSFET'in")
    r.bilgi("  yedigi tek sey I^2 x RDS(on).")
    r.bilgi("")
    r.bilgi(f"     RDS(on) {T.IRFZ44N_RDSON*1e3:.0f} m-ohm (MAKS, Vgs=10 V) · "
            f"Rth j-a {T.IRFZ44N_RTH_JA:.0f} C/W (SOGUTUCUSUZ)")
    r.bilgi(f"     Ortam {T.ORTAM_C:.0f} C · Tj hedefi {T.PIL_TJ_HEDEFI:.0f} C "
            f"(Tj mutlak {T.IRFZ44N_TJ_MAKS:.0f} C)")
    r.bilgi("")
    r.bilgi(f"     {'akim':>8} {'senaryo':<26} {'P':>8} {'Tj':>8} {'yargi'}")
    r.bilgi("     " + "-" * 66)
    for i, ad in ((0.89, "18650, 4.7 ohm tas dir."),
                  (2.56, "100 m-ohm sontun tavani"),
                  (T.PIL_AKIM_SOGUTUCUSUZ, "SOGUTUCUSUZ SINIR"),
                  (11.5, "15 m-ohm sontun tavani")):
        p = i * i * T.IRFZ44N_RDSON
        tj = T.ORTAM_C + p * T.IRFZ44N_RTH_JA
        yargi = "OK" if tj <= T.PIL_TJ_HEDEFI else "[!] SOGUTUCU SART"
        r.bilgi(f"     {i:7.2f}A {ad:<26} {p:7.3f}W {tj:7.1f}C  {yargi}")
    r.kosul("  3: 18650 senaryosunda MOSFET pratik olarak ISINMIYOR",
            T.ORTAM_C + 0.89**2 * T.IRFZ44N_RDSON * T.IRFZ44N_RTH_JA
            < T.ORTAM_C + 5.0,
            f"Tj artisi {0.89**2 * T.IRFZ44N_RDSON * T.IRFZ44N_RTH_JA:.1f} C")
    r.kosul("  3: sogutucusuz akim siniri belgelenmis ve makul",
            4.0 < T.PIL_AKIM_SOGUTUCUSUZ < 8.0,
            f"{T.PIL_AKIM_SOGUTUCUSUZ:.2f} A — 18650/LiPo isleri tamamen "
            f"icinde; 12 V akuyu yuksek akimda test icin SOGUTUCU gerekir")
    r.kosul("  3: [!] sontun 15 m-ohm tavani SOGUTUCUSUZ ASILAMAZ",
            T.ORTAM_C + 11.5**2 * T.IRFZ44N_RDSON * T.IRFZ44N_RTH_JA
            > T.IRFZ44N_TJ_MAKS,
            f"11.5 A'de Tj "
            f"{T.ORTAM_C + 11.5**2*T.IRFZ44N_RDSON*T.IRFZ44N_RTH_JA:.0f} C > "
            f"{T.IRFZ44N_TJ_MAKS:.0f} C — firmware bu akimi SINIRLAMALI ya da "
            f"kilavuz sogutucu ISTEMELI")

    alt(r, "3b · RDS(on) olcumu bozuyor mu")
    r.bilgi("     MOSFET yukle SERI. Ama sont MOSFET'ten SONRA olctugu icin")
    r.bilgi("     RDS(on) yalnizca YUKE eklenir, olcumu bozmaz.")
    for rl in (4.7, 7.5, 10.0):
        pay = T.IRFZ44N_RDSON / rl * 100
        r.bilgi(f"     {rl:4.1f} ohm yukte RDS(on) katkisi: %{pay:.2f} "
                f"(akim %{pay:.2f} duser, ama OLCULEN akim gercek akimdir)")
    r.kosul("  3b: RDS(on) yuke gore ihmal edilebilir",
            T.IRFZ44N_RDSON / 4.7 < 0.01,
            f"%{T.IRFZ44N_RDSON/4.7*100:.2f} — ve bu bir OLCUM hatasi degil, "
            f"yalnizca desarj akimini biraz dusuruyor")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 4 — [!] GERILIM SINIRI (MOSFET kapaliyken)
# ═══════════════════════════════════════════════════════════════════════

def bolum4(r):
    bolum(r, "BOLUM 4 — [!] PIL GERILIMI SINIRI: MOSFET'in Vdss'i")
    r.bilgi("  MOSFET KAPALIYKEN pilin TAMAMI onun uzerine biner. Kartin")
    r.bilgi("  gerilim kanali ±613 V olcebiliyor ama PIL TESTI bundan cok")
    r.bilgi("  daha dar bir bantta calisiyor — ve bu ayri bir sinir.")
    r.bilgi("")
    r.bilgi(f"     IRFZ44N Vdss : {T.IRFZ44N_VDSS:.0f} V")
    PAY = 0.7                    # %70 derating, anahtarlama uygulamasi
    v_guvenli = T.IRFZ44N_VDSS * PAY
    r.bilgi(f"     %{PAY*100:.0f} pay ile guvenli pil gerilimi: "
            f"{v_guvenli:.1f} V")
    r.bilgi("")
    r.bilgi(f"     {'pil':<22} {'gerilim':>9} {'yargi'}")
    r.bilgi("     " + "-" * 48)
    for ad, v in (("18650 1S", 4.2), ("LiPo 3S", 12.6), ("LiPo 6S", 25.2),
                  ("12 V kursun asit", 13.0), ("24 V akü", 29.0),
                  ("48 V paket", 58.0)):
        yargi = "OK" if v <= v_guvenli else "[!] SINIR DISI"
        r.bilgi(f"     {ad:<22} {v:8.1f}V  {yargi}")
    r.kosul("  4: 18650 / LiPo / 12 V isleri sinirin ICINDE",
            29.0 <= v_guvenli,
            f"24 V aku (29 V) <= {v_guvenli:.1f} V")
    r.kosul("  4: [!] 48 V paket SINIR DISI — firmware REDDETMELI",
            58.0 > v_guvenli,
            f"58 V > {v_guvenli:.1f} V — MOSFET kapaliyken delinir. "
            f"Test baslarken gerilim denetlenmeli")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 5 — SAYACLAR ve TAMPON
# ═══════════════════════════════════════════════════════════════════════

def bolum5(r):
    bolum(r, "BOLUM 5 — mAh SAYACI, TAMPON ve DCIR")

    alt(r, "5a · mAh sayaci — enerjiyle ayni yapi")
    r.bilgi("     yuk_pC += (int64)(amper * 1e6f) * dt_us     [uA x us = pC]")
    tavan_mAh = (2**63 - 1) / 3.6e12
    r.bilgi(f"     int64 tavani: {tavan_mAh:,.0f} mAh = "
            f"{tavan_mAh/1000:,.0f} Ah".replace(",", " "))
    r.kosul("  5a: mAh tavani her gercek pil icin fazlasiyla yeterli",
            tavan_mAh / 1000 > 1000,
            f"{tavan_mAh/1000:,.0f} Ah".replace(",", " ") +
            " — en buyuk ev tipi aku bile 200 Ah")
    # ⚠ Burada once `True is not (2**63-1 < 0)` yaziyordu — yani SABIT bir
    # ifade, hicbir sey olcmeyen bos bir iddia. (B20 ayni sinifi
    # sim3_senkron.py'den temizlemisti; ayni tuzaga tekrar dusuldu.)
    # Yerine OLCULEBILIR olan konuldu: birim zincirinin dogrulugu.
    #   uA x us = 1e-6 A x 1e-6 s = 1e-12 A.s = 1 pC
    #   1 mAh   = 1e-3 A x 3600 s = 3.6 C = 3.6e12 pC
    pC_per_mAh = 1e-3 * 3600 / 1e-12
    r.esit("  5a: birim zinciri (uA x us -> pC -> mAh) tutarli",
           pC_per_mAh, 3.6e12, 1e-12)
    r.bilgi("     ⚠ Sayacin ISARETLI oldugu (sarj yonunde geri saydigi) burada")
    r.bilgi("       SINANAMAZ — o, gercek kodun davranisi. AVR emulatorunde")
    r.bilgi("       test_olcum3.py'ye eklenecek (enerjinin 'sarj/desarj")
    r.bilgi("       cevriminde net sifir' testiyle ayni bicimde).")
    # tek ornekte tasma olur mu?
    en_buyuk = 11.5 * 1e6 * 20000          # 11.5 A, 20 ms'lik uzun bir dongu
    r.kosul("  5a: tek ornekte tasma yok",
            en_buyuk < 2**63 - 1,
            f"en kotu tek katki {en_buyuk:.3e} pC << {2**63-1:.3e}")

    alt(r, "5b · Yetisme tamponu ic RAM'e sigiyor mu")
    bos = T.ESP_DRAM_TOPLAM - T.ESP_DRAM_KULLANILAN
    r.bilgi(f"     ESP32-S3 DRAM toplam   : {T.ESP_DRAM_TOPLAM/1024:.0f} KB")
    r.bilgi(f"     Firmware kullaniyor    : {T.ESP_DRAM_KULLANILAN/1024:.0f} KB")
    r.bilgi(f"     Bos                    : {bos/1024:.0f} KB")
    r.bilgi(f"     B21 tamponu ({T.PIL_TAMPON_S/3600:.0f} saat @ "
            f"{T.PIL_KAYIT_HZ:.0f} Hz) : {T.PIL_TAMPON_BAYT/1024:.0f} KB")
    r.kosul("  5b: tampon bos DRAM'in ucte birinden kucuk",
            T.PIL_TAMPON_BAYT < bos / 3,
            f"{T.PIL_TAMPON_BAYT/1024:.0f} KB < {bos/3/1024:.0f} KB — "
            f"skop tamponu ve WiFi yigini icin pay kaliyor")
    r.kosul("  5b: tampon PSRAM'e BAGIMLI DEGIL",
            T.PIL_TAMPON_BAYT < bos,
            "PSRAM bulunursa tampon buyur, bulunmazsa islev KAYBOLMAZ "
            "(DEVIR 4.9: PSRAM calisma aninda yoklaniyor)")

    alt(r, "5c · DCIR darbesi")
    T_ORNEK = 1502.8e-6            # B20 bolum 1, tek atis periyodu
    n_darbe = T.PIL_DCIR_DARBE_S / T_ORNEK
    r.bilgi(f"     Darbe suresi {T.PIL_DCIR_DARBE_S*1e3:.0f} ms -> "
            f"{n_darbe:.0f} ornek")
    r.bilgi(f"     Ilk ornek darbeden {T_ORNEK*1e3:.2f} ms sonra geliyor")
    r.kosul("  5c: darbe icinde anlamli sayida ornek var",
            n_darbe >= 100,
            f"{n_darbe:.0f} ornek — hem ani hem oturmus deger okunabilir")
    kayip = T.PIL_DCIR_DARBE_S / T.PIL_DCIR_ARALIK_S * 100
    r.kosul("  5c: DCIR darbeleri mAh'yi anlamli olcude bozmuyor",
            kayip < 0.2,
            f"%{kayip:.3f} olu zaman (5 saatte "
            f"{5*3600/T.PIL_DCIR_ARALIK_S*T.PIL_DCIR_DARBE_S:.0f} s)")
    r.bilgi("")
    r.bilgi("     ⚠ DURUSTLUK: gercek OHMIK dusus mikrosaniyelerde olur;")
    r.bilgi(f"       ilk ornegimiz {T_ORNEK*1e3:.2f} ms sonra. Yani olculen sey")
    r.bilgi("       ohmik + bir miktar polarizasyon. MUTLAK DCIR degil,")
    r.bilgi("       KARSILASTIRILABILIR bir saglik gostergesi olarak")
    r.bilgi("       raporlanmali. Ayni pil tekrar olculunce anlamli.")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 6 — FIRMWARE'DE GERCEKTEN UYGULANDI MI (sabit AYRISMASI dahil)
# ═══════════════════════════════════════════════════════════════════════

def bolum6(r):
    bolum(r, "BOLUM 6 — FIRMWARE ve SABIT AYRISMASI")
    KOD = KOK / "kod" / "olcum-karti-a3"
    ph = (KOD / "pil_test.h").read_text(encoding="utf-8", errors="replace")
    ino = (KOD / "olcum-karti-a3.ino").read_text(encoding="utf-8",
                                                 errors="replace")

    alt(r, "6a · DCIR sabitleri iki dosyada — ayrismis mi")
    ar_ms = int(re.search(r"PIL_DCIR_ARALIK_MS (\d+)u", ph).group(1))
    da_ms = int(re.search(r"PIL_DCIR_MS\s+(\d+)u", ph).group(1))
    r.bilgi(f"     pil_test.h        : aralik {ar_ms/1000:.0f} s · "
            f"darbe {da_ms} ms")
    r.bilgi(f"     tasarim3_sabit.py : aralik {T.PIL_DCIR_ARALIK_S:.0f} s · "
            f"darbe {T.PIL_DCIR_DARBE_S*1e3:.0f} ms")
    r.esit("  6a: DCIR aralik sabiti ayni",
           ar_ms / 1000.0, T.PIL_DCIR_ARALIK_S, 1e-6, " s")
    r.esit("  6a: DCIR darbe sabiti ayni",
           da_ms / 1000.0, T.PIL_DCIR_DARBE_S, 1e-6, " s")

    alt(r, "6b · Vdss sinirini firmware ZORLUYOR mu")
    az_v = float(re.search(r"#define PIL_AZAMI_V\s+([0-9.]+)f", ph).group(1))
    r.bilgi(f"     pil_test.h PIL_AZAMI_V = {az_v} V")
    r.esit("  6b: firmware siniri, Vdss %70 payiyla ayni",
           az_v, T.IRFZ44N_VDSS * 0.7, 0.01, " V")
    r.kosul("  6b: baslatma denetimi bu siniri KULLANIYOR",
            "PILH_GERILIM_YUKSEK" in ph and "PIL_AZAMI_V" in ph,
            "48 V paket baglanirsa test REDDEDILIYOR")

    alt(r, "6c · Emniyet denetimleri firmware'de var mi")
    for ad, kosul, ek in (
        ("kapi acilista KAPALI kuruluyor",
         "digitalWrite(PIN_PIL_KAPI, LOW);" in ino
         and ino.index("digitalWrite(PIN_PIL_KAPI, LOW);")
             < ino.index("pinMode(PIN_PIL_KAPI, OUTPUT)"),
         "once LOW, SONRA cikis — tersi olsaydi pin bir an belirsiz surulurdu"),
        ("ters polarite reddediliyor", "PILH_TERS" in ph, "v_bos < 0"),
        ("zaten kesmenin altindaysa reddediliyor",
         "PILH_GERILIM_DUSUK" in ph, "v_bos <= kesme_v"),
        ("[!] BAYPAS denetimi var", "PILH_BAYPAS" in ph,
         "MOSFET KAPALIYKEN akim varsa yuk J3'e baglanmis -> kesme calismaz"),
        ("azami sure zaman asimi var", "PILH_SURE" in ino,
         "kimse basinda beklemiyor"),
        ("kesme MOSFET'i KAPATIYOR",
         "pil_durdur(PIL_BITTI" in ino and "pil_yuk(false)" in ino,
         "pil_durdur her yolda yuku kesiyor")):
        r.kosul(f"  6c: {ad}", kosul, ek)

    alt(r, "6d · Tampon boyutu tek kaynaktan mi")
    r.bilgi(f"     PIL_IC_KAPASITE (firmware'den okundu): "
            f"{T.PIL_IC_KAPASITE} nokta")
    r.kosul("  6d: sabit firmware'den TURETILIYOR, elle yazilmiyor",
            "PIL_IC_KAPASITE" in (BURASI / "tasarim3_sabit.py").read_text(
                encoding="utf-8", errors="replace"),
            "iki kopya ayrisirsa RAM iddiasi yalan soylerdi")
    kapasite_tipi = re.search(r"uint(\d+)_t\s+kapasite", ph)
    r.kosul("  6d: [!] halka alanlari 32 bit (uint16 TASIYORDU)",
            kapasite_tipi and kapasite_tipi.group(1) == "32",
            f"uint{kapasite_tipi.group(1) if kapasite_tipi else '?'}_t — "
            f"PSRAM'de 24 saat = 86400 nokta, uint16 tavani 65535: "
            f"`24u*3600u` SESSIZCE 20864'e dusuyordu")


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 7 — PT (2026-10-07): DURUM MAKINESI AVR EMULATORUNDE
# ═══════════════════════════════════════════════════════════════════════

AVR_GXX = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin/avr-g++.exe")


def _pil_avr():
    """pil_test.h'yi (pil_adim) AVR'de kostur. (uyari, satirlar) ya da None (arac yok).
    -Wno-unused-function: olcum3.h'nin bu harness'in cagirmadigi static fonksiyonlari
    (kalibrasyon, Lagrange) C++'ta uyari verir; kartin kodunda hepsi kullaniliyor."""
    import subprocess
    import gecici
    from avr import mega328
    from avr.cekirdek import Cekirdek
    from avr.elf import flash_goruntusu
    if not AVR_GXX.exists():
        return None
    elf = gecici.dizin("pil_") / "ornek_pil.elf"
    p = subprocess.run(
        [str(AVR_GXX), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu++11",
         "-Wall", "-Wextra", "-Wno-unused-function", "-fno-threadsafe-statics",
         f"-I{KOK / 'kod' / 'olcum-karti-a3'}", "-o", str(elf),
         str(BURASI / "avr" / "ornek_pil.cpp"), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return [p.stderr[-1500:] or "derlenemedi"], []
    uyari = [x for x in p.stderr.splitlines() if "warning:" in x]
    kart = mega328.Kart(flash_goruntusu(elf)[0], Cekirdek)
    for _ in range(200):
        if b"BITTI" in kart.tx:
            break
        kart.cevrim_kadar_kos(2_000_000)
    return uyari, kart.satirlar()


def bolum7(r):
    bolum(r, "BOLUM 7 — PT: KESME (EMA) · OCV EVRESI · DCIR AC/KAPA · KAYIT HIZI (AVR)")
    r.bilgi("  Kullanicinin 18650 testi (3.3 ohm, kesme 3 V) 2 s'de BITTI: kesme TEK ANLIK")
    r.bilgi("  ornekte veriliyordu, yuk altindaki ±0.12 V gurultunun ilk dibi kesti.")
    r.bilgi("  Kararlar tasarim/2026-10-07-pil-iyilestirme.md PT1-PT5. Kartin pil_adim'i")
    r.bilgi("  AVR'de kosuyor; beklenenler ANALITIK.")
    sonuc = _pil_avr()
    if sonuc is None:
        r.bilgi("     avr-g++ bulunamadi — pil_test.h AVR denetimi ATLANDI.")
        r.kosul("  7: AVR araci yoksa bu ACIKCA soyleniyor", True, "sessiz atlama degil")
        return
    uyari, sat = sonuc
    r.kosul("  7: pil_test.h AVR'de UYARISIZ derlendi (-Wall -Wextra) ve sonuna kadar kostu",
            not uyari and "BITTI" in sat, " | ".join(uyari[:2])[:300] or f"{len(sat)} satir")
    S: dict[str, list[list[int]]] = {}
    for x in sat:
        p = x.split()
        if p and p[0].startswith("S"):
            try:
                S.setdefault(p[0], []).append([int(v) for v in p[1:]])
            except ValueError:
                pass
    bas = 1000                                    # ornek_pil.cpp BAS_MS
    tau = int(re.search(r"#define PIL_KESME_TAU_MS\s+(\d+)u", PH).group(1))
    ocv_ms = int(re.search(r"#define PIL_OCV_MS\s+(\d+)u", PH).group(1))
    r.kosul("  7: tau 1 s, OCV evresi 5 s (PT1/PT2 karari)", (tau, ocv_ms) == (1000, 5000),
            f"tau {tau} ms, OCV {ocv_ms} ms")

    alt(r, "7a · PT1: gurultulu V (ortalama kesmenin 0.10 V ustu, dipler 0.15 V alti) KESMEZ")
    s1 = (S.get("S1") or [[-1] * 6])[0]
    yuk = bas + ocv_ms
    r.kosul("  7a: 20 s yukte KESME YOK, test suruyor; EMA ortalamada (3.100 V +- 5 mV)",
            s1[0] == 0 and s1[3] == 1 and abs(s1[4] - 31000) <= 50,
            f"kesme {s1[0]}, durum {s1[3]}, EMA {s1[4] / 1e4:.4f} V")
    r.kosul("  7a: [!] ayni dizide TEK ORNEK kurali ilk dipte keserdi (eski kusurun kaniti)",
            s1[1] > 0 and s1[5] == 28500 and 0 < s1[2] - yuk <= 50,
            f"{s1[1]} dip (en dip {s1[5] / 1e4:.3f} V), ilki yuk acildiktan "
            f"{s1[2] - yuk} ms sonra")

    alt(r, "7b · PT1: ortalama 3.10 -> 2.95 V (kesme 3.00) ~1.1 tau'da KESER")
    s2 = (S.get("S2") or [[-1] * 5])[0]
    beklenen = tau * math.log(0.15 / 0.05)        # e^(-t/tau) = (2.95-3.00)/(2.95-3.10) -> 1/3
    dt = s2[0] - s2[1]
    r.kosul("  7b: basamaktan sonra 1-2 tau icinde, analitik tau ln3 = 1.099 s'ye +- 0.1 s",
            tau <= dt <= 2 * tau and abs(dt - beklenen) <= 100,
            f"{dt} ms (analitik {beklenen:.0f} ms)")
    r.kosul("  7b: karar EMA'dan (kesme aninda EMA <= 3.000 V ve 20 mV'tan yakin), anlik V "
            "o anda 2.70 V — PIL_SONUC v_son EMA'yi yazar",
            2.98e4 <= s2[2] <= 3.0e4 and s2[4] == 27000,
            f"EMA {s2[2] / 1e4:.4f} V, anlik {s2[4] / 1e4:.4f} V")

    alt(r, "7c · PT2: OCV evresi — 5 s yuk KAPALI, noktalar isaretli, kesme yok, sonra yuk")
    s3a = S.get("S3a") or []
    s3 = (S.get("S3") or [[-1] * 7])[0]
    r.kosul("  7c: OCV evresinde (V 2.0 = kesmenin ALTI) her saniye ornek isaretli (KN_OCV "
            "kosulu) ve test SURUYOR",
            [x[0] for x in s3a] == [2000, 3000, 4000, 5000, 6000]
            and all(x[1:] == [1, 1] for x in s3a), str(s3a))
    r.kosul("  7c: yuk TAM 5 s'de BIR KEZ acilir; OCV'de 0.8 A gorulse de mAh BIRIKMEZ; "
            "/pil egrisine 5 nokta",
            s3[0] == bas + ocv_ms and s3[1] == 1 and s3[2] == 0 and s3[3] == 5,
            f"yuk_ac {s3[0]} ms x{s3[1]}, yuk_pC {s3[2]}, egri {s3[3]} nokta")
    r.kosul("  7c: yukte V hemen kesmenin altinda (2.9 V) ama kesme TAM 1 tau sonra, bir kez",
            s3[4] == s3[0] + tau and s3[5] == 1, f"kesme {s3[4]} ms x{s3[5]}")
    r.kosul("  7c: son isaretli ornek yukun acildigi ornek (olculurken yuk kapaliydi)",
            s3[6] == s3[0], f"son OCV ornegi {s3[6]} ms")
    s3b = (S.get("S3b") or [[-1, -1, -1]])[0]
    r.kosul("  7c: OCV evresinde p0: isaret (KN_OCV, /pil evre=ocv) test durunca BITER, evre "
            "alani OCV'de kalsa bile",
            s3b == [1, 0, 1], str(s3b))

    alt(r, "7d · PT5: DCIR KAPALI -> darbe YOK; ACIK -> 5 dk'da bir, eskisi gibi")
    s4 = {x[0]: x for x in S.get("S4") or []}
    k, a = s4.get(0, [0] + [-1] * 9), s4.get(1, [1] + [-1] * 9)
    r.kosul("  7d: DCIR kapaliyken 650 s'de HIC darbe yok (yuk hic kesilmez), kesme yok",
            k[1:4] == [0, 0, 0] and k[4] == 0 and k[7] == 0, str(k))
    r.kosul("  7d: DCIR acikken 650 s'de 2 darbe; ilki yuk acildiktan TAM 300 s sonra "
            "(zamanlayici yukle baslar)",
            a[1:5] == [2, 2, 300000, 2], str(a[1:5]))
    r.kosul("  7d: R = (4.0 - 3.6) / 1.0 = 0.400 ohm (ani ve oturmus); ani V darbenin ilk "
            "orneginden; darbe EMA'yi oynatmaz, kesme yok",
            a[5] == 4000 and a[6] == 4000 and a[9] == 40000 and a[8] == 36000 and a[7] == 0,
            f"r_ani {a[5] / 1e4} r_otr {a[6] / 1e4} v_ani {a[9] / 1e4} EMA {a[8] / 1e4}")

    alt(r, "7e · emniyet: azami sure baslangictan (OCV dahil)")
    s5 = (S.get("S5") or [[-1, -1]])[0]
    r.kosul("  7e: azami 7 s -> 8. saniyede bir kez PILA_SURE", s5 == [8000, 1], str(s5))

    alt(r, "7f · PT3/PT4: kayit hizi -> nokta araligi / canli egri araligi")
    s6 = S.get("S6") or []
    # satir: hz x 100, nokta_ms, halka_ms (ornek_pil.cpp s6 sirasi; 0.001 x 100 -> 0)
    bek = [[0, 0, 50], [100, 1000, 1000], [500, 200, 200], [2000, 50, 50], [5000, 20, 50],
           [20, 5000, 5000], [0, 60000, 60000], [100000, 20, 50], [-100, 1000, 1000]]
    r.kosul("  7f: 0 = her ornek (nokta 0, egri 50 ms = 20/s); 1/5/20/50 -> 1000/200/50/20 ms; "
            "eski 0.2 -> 5 s; egri en cok 20/s; 0.001 -> 60 s, 1000 -> 20 ms siniri; eksi -> 1/s",
            s6 == bek, str(s6))
    r.kosul("  7f: NaN (bozuk ayar) varsayilan 1/s",
            (S.get("S6n") or [[]])[0] == [1000, 1000], str(S.get("S6n")))

    alt(r, "7g · Pr / Pd ayristiricilari")
    s7 = {x[0]: x[1:] for x in S.get("S7") or []}
    # ornek_pil.cpp vektorleri: 0 1 5 20 50 | 2 10 100 | "" -1 " 5" 5x 05 00 0050 4294967297 "20 "
    bek7 = {0: [0, 0], 1: [0, 1], 2: [0, 5], 3: [0, 20], 4: [0, 50]}
    bek7.update({j: [2, 999] for j in (5, 6, 7)})
    bek7.update({j: [1, 999] for j in range(8, 17)})
    r.kosul("  7g: Pr yalniz 0/1/5/20/50; listede olmayan sayi 'izinsiz' (2); bos, isaret, "
            "bosluk, harf, bastaki sifir, 4+ hane 'bicim' (1); hatada hz YAZILMAZ",
            s7 == bek7, str({j: v for j, v in s7.items() if bek7.get(j) != v} or len(s7)))
    s8 = [x[1] for x in sorted(S.get("S8") or [])]
    r.kosul("  7g: Pd yalniz '0' / '1'; bos, 2, 01, sondaki bosluk, harf REDDEDILIR",
            s8 == [0, 1, 255, 255, 255, 255, 255], str(s8))
    r.kosul("  7g: izinli hizlar tam olarak {0, 1, 5, 20, 50}",
            (S.get("S9") or [[]])[0] == [0, 1, 5, 20, 50], str(S.get("S9")))


# ═══════════════════════════════════════════════════════════════════════
#  BOLUM 8 — PT: FIRMWARE YAPISTIRICISI (.ino) karari UYGULUYOR mu
# ═══════════════════════════════════════════════════════════════════════

def _govde(metin: str, bas: str) -> str:
    """`bas` ile baslayan fonksiyonun { } govdesi ('' yoksa)."""
    i = metin.find(bas)
    if i < 0:
        return ""
    j = metin.find("{", i)
    d = 0
    for k in range(j, len(metin)):
        d += {"{": 1, "}": -1}.get(metin[k], 0)
        if d == 0:
            return metin[j:k + 1]
    return ""


def bolum8(r):
    bolum(r, "BOLUM 8 — PT: .ino pil_adim'in isteklerini UYGULUYOR mu")
    ino = INO
    pi = _govde(ino, "static void pil_isle(")
    eylem = {}
    for bit in ("PILA_SURE", "PILA_YUK_AC", "PILA_DCIR_BITTI", "PILA_BITTI", "PILA_DCIR_BAS"):
        i = pi.find(f"(e & {bit})")
        eylem[bit] = pi[i:pi.find("}", i) + 1] if i >= 0 else ""
    r.kosul("  8: pil_isle karari pil_adim'dan alir (tek kaynak, AVR'de sinanan kod)",
            "pil_adim(&pil, &pil_halka, &a, millis()" in pi and "pil_kesmeli_mi" not in pi)
    r.kosul("  8: SURE -> pil_durdur(PIL_HATA, PILH_SURE); BITTI -> pil_durdur(PIL_BITTI)",
            "pil_durdur(PIL_HATA, PILH_SURE)" in eylem["PILA_SURE"]
            and "pil_durdur(PIL_BITTI, PILH_YOK)" in eylem["PILA_BITTI"])
    r.kosul("  8: YUK_AC -> MOSFET AC; DCIR_BITTI -> MOSFET AC + DCIR olayi; DCIR_BAS -> KAPAT",
            "pil_yuk(true)" in eylem["PILA_YUK_AC"]
            and "pil_yuk(true)" in eylem["PILA_DCIR_BITTI"]
            and "kayit_pil_dcir(" in eylem["PILA_DCIR_BITTI"]
            and "pil_yuk(false)" in eylem["PILA_DCIR_BAS"])
    pb = _govde(ino, "static void pil_baslat() {")
    r.kosul("  8: [!] p1 kabulunde yuk ACILMAZ (OCV evresi); kurulum pil_baslat_kur ile, "
            "DCIR ayari teste kopyalanir",
            "pil_yuk(true)" not in pb
            and "pil_baslat_kur(&pil, millis(), o.volt, pil_dcir_ayar)" in pb
            and 0 <= pb.find("pil_baslatilabilir(") < pb.find("pil_baslat_kur("))
    kb = _govde(ino, "static uint8_t pil_kayit_bayrak() {")
    lp = _govde(ino, "void loop() {")
    r.kosul("  8: kayit noktacisi OCV evresindeki ornekleri KN_OCV, darbedekileri KN_DCIR ile "
            "isaretler",
            "pil_ocv_evresinde(&pil) ? KN_OCV" in kb and "pil.dcir_icinde ? KN_DCIR" in kb
            and "kayit_ornek(o.watt, millis(), pil_kayit_bayrak())" in lp)
    i_p = ino.find("    case 'P': {")
    pk = ino[i_p:ino.find("    case 'p': {", i_p)]
    r.kosul("  8: Pr/Pd test SURERKEN reddedilir (oturumun hizi ve PIL_AYAR baslangicta yazildi)",
            0 <= pk.find("pil_testi_suruyor()") < pk.find("pil_pr_ayir(")
            and pk.find("pil_testi_suruyor()") < pk.find("pil_pd_ayir("))
    r.kosul("  8: Pr ayristiricidan gecer ve KALICI (ayar.pil_kayit_hz + ayar_kaydet); Ayar3 "
            "BUYUMEDI (alan ayni, AYAR3_IMZA 0xC0F6)",
            re.search(r"pil_pr_ayir\(s \+ 2, &hz\);\s*if \(r\) \{", pk) is not None
            and re.search(r"ayar\.pil_kayit_hz = \(float\)hz;\s*ayar_kaydet\(\);", pk) is not None
            and "float    pil_kayit_hz;" in TIP and "#define AYAR3_IMZA 0xC0F6u" in TIP)
    yz = _govde(ino, "static bool pil_dcir_yaz(")
    yk = _govde(ino, "static void pil_ayar_yukle() {")
    st = _govde(ino, "void setup() {")
    r.kosul("  8: Pd KALICI ayri NVS ad alaninda (pilayar/dcir, u8); acilista okunur, "
            "VARSAYILAN KAPALI; yazilamazsa ayar degismez",
            '#define PIL_NVS "pilayar"' in ino and 'putUChar("dcir"' in yz
            and 0 <= yz.find("if (n != 1u) return false;") < yz.find("pil_dcir_ayar =")
            and 'getUChar("dcir", 0)' in yk and "static uint8_t pil_dcir_ayar = 0;" in ino
            and "  pil_ayar_yukle();" in st
            and "pil_dcir_yaz(d)" in pk and "pil_pd_ayir(s + 2)" in pk)
    p0 = pk[:pk.find("float v = atof")]
    r.kosul("  8: `P` satiri kayit hizini (0'da 'her ornek') ve DCIR'i da yaziyor",
            "ayar.pil_kayit_hz" in p0 and "her ornek" in p0 and "DCIR" in p0
            and "pil_dcir_ayar" in p0)
    r.kosul("  8: yardimda Pr / Pd var", "Pr<hz>" in ino and "Pd1/Pd0" in ino)
    ps = _govde(ino, "void pil_sayfa() {")
    son = ps.find('F("\\n--\\n")')
    r.kosul("  8: /pil eski alanlar AYNEN, sona evre=ocv|yuk, kayit_hz=, dcir=0|1 (PT6)",
            all(0 <= ps.find(f'F("\\n{a}=")') < son for a in ("evre", "kayit_hz", "dcir"))
            and 0 <= ps.find('F("\\ncoulomb=")') < ps.find('F("\\nevre=")')
            and 'pil_ocv_evresinde(&pil) ? F("ocv") : F("yuk")' in ps
            and "pil_dcir_ayar ? '1' : '0'" in ps)


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B21 — PIL KAPASITE TESTI (tas direnc yuk + MOSFET anahtar)")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI sinar, kurulmus bir KARTI degil.")
    bolum1(r)
    bolum2(r)
    bolum3(r)
    bolum4(r)
    bolum5(r)
    bolum6(r)
    bolum7(r)
    bolum8(r)
    tamam = r.yazdir()
    tezgah("B21 Pil kapasite testi", [
        ("[!] FAILSAFE — kart calisirken RESET at",
         "Yuk KESILMELI. Kapi R42 ile GND'ye cekili, ESP32 olurse MOSFET "
         "kapanmali. B21'in EN ONEMLI tezgah testi; gecmezse pil testi "
         "hic kullanilmamali"),
        ("[!] BAYPAS denetimi — yuku bilerek J3'e bagla",
         "Test REDDEDILMELI. J3 dogrudan sonte gidiyor; oraya baglanirsa "
         "MOSFET baypas olur ve kesme CALISMAZ. Sessiz hatayi yakalayan "
         "tek sey bu"),
        ("Kesme gecikmesi",
         "`p1` kosarken bir istemciyi askiya al ve kesme gerilimine in. "
         "Fazla desarj < 0.5 mAh olmali — yani kesme loop() blokajina "
         "BAGLI OLMAMALI"),
        ("MOSFET'in uzerindeki logo",
         "Veri sayfasi ikincil kaynak (INCHANGE). Farkli bir uretici "
         "cikarsa Vdss ve Rds(on) yeniden denetlenmeli"),
        ("Kapi gerilimi — yuk acikken Vgs",
         "~11.8 V beklenir. Dususe Rds(on) buyur, MOSFET isinir"),
        ("Tas direncin gercek degeri ve isinmasi",
         "4.7-7.5 ohm / 10 W. Elle olc; 30 dk desarjda sicakligina bak"),
        ("[PT] 18650 + 3.3 ohm, kesme 3.0 V (kullanicinin 2 s'de biten testi)",
         "Once 5 s yuksuz (OCV, /pil evre=ocv), sonra yuk; test SAATLER surmeli, 2 s'de "
         "bitmemeli. Bitiste PIL_SONUC v_son ~3.0 V (EMA), anlik dip degil. Pd0'da yuk hic "
         "kesilmez; Pr0'da kayitta AYRINTI ornekleri + 1/s nokta"),
        ("Sarj yonunde test",
         "Sayac ISARETLI ama sarj kaynagi yok — mAh geri saymali. "
         "Kaynak bulununca denenecek"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
