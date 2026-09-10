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
        ("Sarj yonunde test",
         "Sayac ISARETLI ama sarj kaynagi yok — mAh geri saymali. "
         "Kaynak bulununca denenecek"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
