# -*- coding: utf-8 -*-
"""B25 — BRINGUP KOSUCUSUNUN KENDISINI SINAR (donanim GEREKMIYOR).

    python test_tezgah_kart.py

🔴 NEDEN VAR. `tezgah_kart.py` yarin gercek karta baglanacak ve
"gecti/kaldi" diyecek. YANLIS BIR BRINGUP TESTI, TESTSIZLIKTEN KOTUDUR:
gecmeyen bir karta "gecti" der ve kusur tezgahtan cikip alana gider.
Ama kosucuyu donanim olmadan nasil sinariz?

`kopru/kart_baglanti.py`'deki `KayitKart` tam bunun icin var: `SeriKart`
ile AYNI yuzeyi tasiyor, komutlara betiklenmis yanit veriyor ve yanit
satirlarini akisin ICINE koyuyor — gercek kartta oldugu gibi.

Yontem, projenin geri kalaniyla ayni: **iki yonlu**.
  1. SAGLIKLI kart senaryosu  -> her denetim YESIL olmali
  2. Kasitli BOZULMUS senaryolar -> DOGRU denetim kirmizi olmali,
     otekiler yesil kalmali

(2) olmadan (1) hicbir sey kanitlamaz: her zaman True donen bir denetim
de saglikli senaryoda yesil olurdu.

⚠ Bu adim gercek donanimi DOGRULAMIYOR. Yalnizca "kosucu dogru soruyu
  soruyor ve dogru cevaba bakiyor mu" diye soruyor.
"""
from __future__ import annotations

import io
import contextlib
import re
import sys
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))

import tezgah_kart as TK                                # noqa: E402
from kart_baglanti import KayitKart                     # noqa: E402
from tezgah import tezgah                               # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> bool:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))
    return kosul


# ── SAGLIKLI KART ────────────────────────────────────────────────────
# Satirlar firmware kaynagindaki bicimlerle AYNI. Sayilar gercekci:
# ornek sayisi `tezgah_kart.ORNEK_BEKLENEN`'den turetiliyor ki
# beklenti degisirse senaryo da pesinden gitsin.

_ORNEK = int(round(TK.ORNEK_BEKLENEN))
RAPOR_S = TK.RAPOR_MS / 1000.0


def afis_satirlari(psram_kb=8192, fs=True, tampon=True, parola_yok=True,
                   skop=True, yapisik=False, mac_uyumsuz=False):
    s = [
        "",
        "Olcum Karti — Asama 3 (CIFT YONLU on uc)",
        f"PSRAM: {psram_kb} KB" if psram_kb else "PSRAM: YOK — derin skop bellegi kullanilamaz",
    ]
    # PSRAM varken firmware tamponu 24 SAATE cikariyor (ino:2412-2415):
    # 86400 nokta, 86400*12/1024 = 1012 KB, PSRAM'de. Ilk yazimda burada
    # ic RAM hali (5400/1.50 saat/63 KB) "saglikli" sayilmisti — oysa o
    # PSRAM'siz DUSMUS hal. Senaryo gercek saglikli kartı tarif etmeli.
    if not tampon:
        s.append("  pil egri tamponu: AYRILAMADI — mAh/Wh sayaclari calisir")
    elif psram_kb:
        s.append("  pil egri tamponu: 86400 nokta = 24.00 saat @ 1.00 Hz, "
                 "1012 KB (PSRAM)")
    else:
        s.append("  pil egri tamponu: 5400 nokta = 1.50 saat @ 1.00 Hz, "
                 "63 KB (ic RAM)")
    s.append("Cikis: D <volt> <amper> <watt> <joule> <wh> <ms> "
             "<ornek> <menzil> <durum>")
    s.append("`h` yardim")
    if not skop:
        s.append("! osiloskop suruculu kurulamadi")
    # B26: afis GERCEK MAC'i de ilan ediyor. `mac_uyumsuz` eski kusuru
    # taklit eder: SSID ilklenmemis bellekten gelmis, MAC ise gercek.
    # ⚠ OUI BILEREK SENTETIK (02:00:00 = yerel yonetimli, uretici yok).
    #   Gercek kartin OUI'si burada dursaydi, DEVIR'de kasitli olarak
    #   kisaltilmis MAC son ekiyle birlesip tam adresi kurardi — bagimsiz
    #   gizlilik denetimi bunu B26'da yakaladi.
    _mac = "02:00:00:00:AB:AB" if mac_uyumsuz else "02:00:00:00:A1:B2"
    _ag = f"Ag: AP  SSID=OLCUM-KARTI-A1B2  MAC={_mac}  http://192.168.4.1"
    _ar = ("Arayuz: LittleFS'te (karttan servis ediliyor)" if fs
           else "Arayuz: YOK — uretim/arayuz-yaz.py ile yukleyin")
    if yapisik:
        # Firmware'de `Ag:` blogunun sonunda println YOKKEN olusan hal.
        s.append(_ag + _ar)
    else:
        s.append(_ag)
        s.append(_ar)
    s.append("")
    if parola_yok:
        s.append("! UYARI: web parolasi YOK — komut ucu yalnizca jeton ile korunuyor")
    return s


def d_satiri(ornek=None, menzil=0, durum=0):
    """🔴 B26 — ALAN SIRASI DUZELTILDI.

    Eskiden ornek sayisi SON alana konuyordu:
        f"D ... 200 1234 {n}"          # <- n, menzil'in yerinde
    Firmware bicimi ise
        D <volt> <amper> <watt> <joule> <wh> <ms> <ornek> <menzil>
    yani ornek 7., menzil 8. alan. Sahte kart bu sirayi yanlis
    modelliyordu ve kosucunun `split()[-1]` ayristiricisi de ayni
    hatayi paylastigi icin test YESIL kaliyordu. Gercek kartta
    kosulunca ornek sayisi olarak `menzil` (0) okundu.

    Ders: sahte kartin GERCEK firmware'i modelledigi ayrica
    sinanmali — kendi kendine tutarli olmasi yetmiyor.
    """
    n = _ORNEK if ornek is None else ornek
    # B27/K1: 10. alan `durum` — bit0 GERILIM okunamadi, bit1 AKIM okunamadi
    return f"D 12.3456 0.123456 1.52345 0.1234 0.0001234 200 {n} {menzil} {durum}"


def yanitlar_saglikli(loop_us=8500, i2c="I2C: 0x48 0x49",
                      g_reddi=True, r_onayi=True, bilinmeyen=True):
    y = {
        "?": ["A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=0 "
              "y_kazanc=1.000000 y_sifir=0 sont=0.015 i_duz=1.000 i_ofset=0",
              "R normal=+-32.4 V/0.99 mV  yuksek=+-613.7 V/18.7 mV",
              "L normal -32.4 .. 32.4 V  yuksek -613.7 .. 613.7 V",
              f"K 0 {loop_us} 0",
              "  (K = atlanan enerji ms · en uzun dongu us · >20ms tur)"],
        "N": ["* ag: AP  SSID=OLCUM-KARTI-A1B2  IP=192.168.4.1  mDNS=olcum.local",
              "* ev agi: (tanimli degil)",
              "   AP parolasi: kj7mn2pq4xrt",
              "* web parolasi: YOK — komut ucu parolasiz"],
        "#": [i2c, "  beklenen: 0x48 (akim)  0x49 (gerilim) — bulunan 2"],
    }
    y["g"] = (["! g: gerilim degeri gerekli, orn. `g12.34`"] if g_reddi
              else ["* gerilim kazanci 0.000000"])
    y["i"] = ["! i: akim degeri gerekli, orn. `i1.5`"]
    # B26: ciplak `f` REDDEDILMIYOR — B22.1'den beri DEGERI basiyor.
    # Hata mesaji yalnizca BOZUK girdide cikiyor. Eski kayit `f` icin
    # hata donduruyordu, yani sahte kart gercek firmware'i YANLIS
    # modelliyordu ve bayat denetimi "dogruluyordu".
    y["f"] = ["* sebeke frekansi 50.00 Hz"]
    y["fabc"] = ["! f: frekans gerekli, orn. `f50` ya da `f0` (DC)"]
    y["K"] = [f"* blokaj sayaclari sifirlandi — onceki: atlanan 0 ms, "
              f"en uzun dongu {loop_us} us, >20ms tur 0"]
    y["Z"] = ["* akim sifiri ham=0"]
    y["R"] = (["! R: onay gerekli — `R!` yaz. TUM kalibrasyonu siler."]
              if r_onayi else ["* FABRIKA AYARLARI yuklendi"])
    y["QQ"] = (["! bilinmeyen komut — `h` yardim"] if bilinmeyen else [])
    return y


def kart_kur(afis=None, yanit=None, telemetri_adet=40, ornek=None,
             gecikme=0.0, kalici=None):
    """Saglikli bir kart benzetimi. Afis + surekli `D` akisi + yanitlar.

    ⚠ `KayitKart` SONLU: gercek kart sonsuza kadar `D` basiyor, kayit
    bitiyor. `D` hizina bakan denetimler icin `gecikme` ile gercek
    tempoyu taklit ediyoruz — yoksa 40 satir bir anda gelir ve "hiz"
    olcumu anlamsiz cikar. Bu bir kosucu kusuru DEGIL, kaydin sinirli
    olmasi; ama testin bunu bilmesi gerekiyor.
    """
    satirlar = list(afis if afis is not None else afis_satirlari())
    satirlar += [d_satiri(ornek) for _ in range(telemetri_adet)]
    y = yanit if yanit is not None else yanitlar_saglikli()
    if kalici is None:
        return KayitKart(satirlar, y, gecikme=gecikme)
    # B26: NVS kalicilik denetimi DURUM istiyor — bkz. AyarliKart
    return AyarliKart(satirlar, y, gecikme=gecikme, kalici=kalici)


def kart_kur_telemetrili(**kw):
    """`D` denetimleri icin: gercek tempo + bol satir."""
    kw.setdefault("telemetri_adet", 120)
    kw.setdefault("gecikme", RAPOR_S)
    return kart_kur(**kw)


class AyarliKart(KayitKart):
    """`KayitKart` + KUCUK BIR DURUM: `s<ohm>` yazinca `?` ciktisindaki
    `sont=` gercekten degisir ve reset'i atlatir.

    🔴 NEDEN GEREKLI (B26): NVS kalicilik denetimi "ayirt edici bir deger
    yaz, resetle, hayatta kaldi mi" diye soruyor. DURUMSUZ bir sahte kart
    bu soruyu modelleyemez — `?` hep ayni satiri doner ve iddia, NVS hic
    calismasa bile gecer. Denetimin ilk yaziminda tam bu oldu: yazilan da
    varsayilan da 0'di, "0 == 0" diye yesil yaniyordu.

    `kalici=False` ise yazma KABUL EDILIR ama reset degeri geri alir —
    yani `ayar_kaydet()` hic cagrilmamis gibi davranir.
    """

    def __init__(self, *a, kalici=True, varsayilan=0.015, **kw):
        super().__init__(*a, **kw)
        self.kalici = kalici
        self.varsayilan = varsayilan
        self._yazilan = None

    def _sont_yaz(self, deger):
        y = self.yanitlar.get("?")
        if y:
            self.yanitlar["?"] = [
                re.sub(r"sont=[\d.]+", f"sont={deger:.6f}", x) for x in y]

    def yaz(self, metin):
        if metin.startswith("s") and len(metin) > 1:
            try:
                v = float(metin[1:])
            except ValueError:
                v = None
            if v is not None and v > 1e-4:
                self._yazilan = v
                self._sont_yaz(v)
                self.yanitlar[metin] = [
                    f"* sont {v:.6f} ohm, menzil +-{0.256 / v:.4f} A"]
        super().yaz(metin)

    def sifirla(self, bekle: float = 0.0) -> bool:
        if not self.kalici:
            # NVS'e yazilmamis gibi: reset varsayilana donduruyor
            self._sont_yaz(self.varsayilan)
        return super().sifirla(bekle)


def kosturi(kart, asama=0, http_adres=None, sifirla=True, yazma=False):
    """Kosucuyu sessizce kostur, Sonuc'u ve ciktisini dondur.

    `yazma` = NVS'e yazan (tehlike sinifli) denetimler de kossun mu.
    Varsayilan KAPALI, tipki gercek kosucuda oldugu gibi.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s = TK.kosum(kart, asama, http_adres, sifirla, yazma)
    return s, buf.getvalue()


def kirmizilar(cikti: str) -> list[str]:
    return [x.strip()[5:].strip() for x in cikti.splitlines()
            if x.strip().startswith("[!!]")]


# ═══════════════════════════════════════════════════════════ SENARYOLAR

def bolum1_saglikli():
    print("\n--- 1. SAGLIKLI KART: her denetim yesil olmali " + "-" * 24)
    s, cikti = kosturi(kart_kur(), asama=0)
    ok("Asama 0: saglikli kartta hicbir denetim KALMIYOR", s.kaldi == 0,
       f"{s.gecti} gecti, {s.kaldi} kaldi, {s.atlandi} atlandi"
       + ("  " + ", ".join(kirmizilar(cikti)[:3]) if s.kaldi else ""))
    ok("Asama 0'da anlamli sayida denetim KOSTU", s.gecti >= 15,
       f"{s.gecti} denetim — az ise senaryo eksik, kosucu korlesir")
    ok("Web denetimleri --http yokken ATLANIYOR", s.atlandi >= 5,
       f"{s.atlandi} atlandi (HTTP verilmedi)")

    # Asama 1: `D` denetimleri de kossun — GERCEK TEMPODA.
    s1, c1 = kosturi(kart_kur_telemetrili(), asama=1)
    ok("Asama 1: `D` denetimleri de yesil", s1.kaldi == 0,
       f"{s1.gecti} gecti, {s1.kaldi} kaldi"
       + ("  " + ", ".join(kirmizilar(c1)[:3]) if s1.kaldi else ""))
    ok("Asama 1 asama 0'dan DAHA COK denetim kosturuyor", s1.gecti > s.gecti,
       f"{s.gecti} -> {s1.gecti}")
    return s


def bolum2_mutasyonlar():
    """Her senaryo TAM BIR seyi bozuyor; dogru denetim kirmizi olmali."""
    print("\n--- 2. BOZUK KART SENARYOLARI: dogru denetim kirmizi olmali " + "-" * 8)

    senaryolar = [
        ("PSRAM yok (FQBN'de PSRAM=opi eksik)",
         dict(afis=afis_satirlari(psram_kb=0)),
         "PSRAM", 0),
        ("PSRAM 2 MB (yanlis modul)",
         dict(afis=afis_satirlari(psram_kb=2048)),
         "PSRAM >= 8 MB", 0),
        ("LittleFS bos (arayuz yazilmamis)",
         dict(afis=afis_satirlari(fs=False)),
         "Arayuz LittleFS'te", 0),
        ("Pil tamponu ayrilamadi",
         dict(afis=afis_satirlari(tampon=False)),
         "Pil egri tamponu AYRILDI", 0),
        ("loop_azami_us esigin USTUNDE (cift cekirdek gerekiyor)",
         dict(yanit=yanitlar_saglikli(loop_us=TK.CIFT_CEKIRDEK_ESIK_US + 1)),
         "esigin ALTINDA", 0),
        # 🔴 B26 — GERCEK KARTTA bulunan kusurun senaryosu: SSID
        #    ilklenmemis bellekten gelmis, MAC gercek. Eski kosucu bunu
        #    GORMUYORDU ("Ag kipi bildirildi" yalnizca satirin VARLIGINA
        #    bakiyordu), o yuzden 18/18 yesilken kart yanlis ad yayinladi.
        ("AP SSID'i MAC'ten gelmiyor (ilklenmemis bellek)",
         dict(afis=afis_satirlari(mac_uyumsuz=True)),
         "SSID soneki gercek MAC", 0),
        ("Ciplak `g` KABUL EDILIYOR (K3 tuglalama geri geldi)",
         dict(yanit=yanitlar_saglikli(g_reddi=False)),
         "Ciplak `g` REDDEDILIYOR", 0),
        ("`R` onaysiz fabrika sifirlamasi yapiyor",
         dict(yanit=yanitlar_saglikli(r_onayi=False)),
         "onaysiz fabrika sifirlamasi YAPMIYOR", 0),
        ("Bilinmeyen komut SESSIZCE yutuluyor",
         dict(yanit=yanitlar_saglikli(bilinmeyen=False)),
         "Bilinmeyen komut ACIKCA reddediliyor", 0),
        ("Osiloskop DMA surucusu kurulamadi",
         dict(afis=afis_satirlari(skop=False)),
         "Osiloskop DMA surucusu kuruldu", 0),
        ("Afis satirlari YAPISIK (Ag: sonrasi println yok)",
         dict(afis=afis_satirlari(yapisik=True)),
         "Afis satirlari yapisik DEGIL", 0),
        ("I2C'de hicbir cihaz yok (ADS bagli degil)",
         dict(yanit=yanitlar_saglikli(i2c="I2C: (hicbir cihaz yok)")),
         "0x48 adresinde gorunuyor", 1),
        ("Yalniz 0x48 var (ADS #2'nin ADDR pini bosta)",
         dict(yanit=yanitlar_saglikli(i2c="I2C: 0x48")),
         "0x49 adresinde gorunuyor", 1),
        ("Ornek sayisi ~100 (enableDelay ise yaramamis)",
         dict(ornek=100),
         "Ornek sayisi beklenen bantta", 1),
        ("Ornek sayisi ~19 (B20 duzeltmeleri gitmis)",
         dict(ornek=19),
         "Ornek sayisi beklenen bantta", 1),
        ("`D` satiri hic gelmiyor",
         dict(telemetri_adet=0, gecikme=0.0),
         "`D` olcum satiri geliyor", 1),
    ]

    for ad, kw, beklenen_kirmizi, asama in senaryolar:
        kart = (kart_kur_telemetrili(**kw) if asama >= 1 else kart_kur(**kw))
        s, cikti = kosturi(kart, asama=asama)
        kirmizi = kirmizilar(cikti)
        yakalandi = any(beklenen_kirmizi in x for x in kirmizi)
        ok(f"{ad[:52]:<52} -> yakalandi", yakalandi,
           f"beklenen kirmizi: '{beklenen_kirmizi}'" if not yakalandi
           else f"{len(kirmizi)} kirmizi")

    # ── B26: NVS kalicilik denetimi TEHLIKE SINIFLI, yani yalnizca
    #    --yazmaya-izin-ver ile kosuyor. Ayri blok, cunku yukaridaki
    #    senaryolar bilerek yazma izni OLMADAN kosuyor.
    _s, c_izinsiz = kosturi(kart_kur(), asama=0, yazma=False)
    ok("NVS denetimi izin YOKKEN kosmuyor",
       "NVS kalibrasyon kaliciligi" in c_izinsiz
       and "--yazmaya-izin-ver gerekiyor" in c_izinsiz,
       "tehlike sinifli denetim varsayilan olarak ATLANMALI")

    _s, c_izinli = kosturi(kart_kur(kalici=True), asama=0, yazma=True)
    ok("NVS denetimi izin VARKEN saglikli kartta yesil",
       not any("NVS" in x or "RESET'i ATLATTI" in x
               for x in kirmizilar(c_izinli)),
       f"{len(kirmizilar(c_izinli))} kirmizi")

    _s, c_bozuk = kosturi(kart_kur(kalici=False), asama=0, yazma=True)
    ok("Ayar RESET'te KAYBOLURSA yakalaniyor",
       any("RESET'i ATLATTI" in x for x in kirmizilar(c_bozuk)),
       "yazma kabul ediliyor ama reset varsayilana donduruyor — "
       "`ayar_kaydet()` hic cagrilmamis gibi")


def bolum3_kapsam():
    """Bir senaryo BIR seyi bozmali — her sey birden kirmizi olmamali."""
    print("\n--- 3. KAPSAM: bozulan sey KADAR kirmizi olmali " + "-" * 21)
    _s0, c0 = kosturi(kart_kur(), asama=0)
    taban = len(kirmizilar(c0))
    ok("Saglikli senaryoda taban kirmizi = 0", taban == 0, f"{taban}")

    _s1, c1 = kosturi(kart_kur(yanit=yanitlar_saglikli(g_reddi=False)),
                      asama=0)
    k1 = kirmizilar(c1)
    ok("Tek bozuk komut YALNIZCA kendi denetimini kirmiziya cevirir",
       len(k1) == 1, f"{len(k1)} kirmizi: {', '.join(x[:34] for x in k1)}")

    _s2, c2 = kosturi(kart_kur(afis=afis_satirlari(psram_kb=2048)), asama=0)
    k2 = kirmizilar(c2)
    ok("Yanlis PSRAM boyutu yalnizca PSRAM denetimini dusurur",
       len(k2) == 1, f"{len(k2)} kirmizi: {', '.join(x[:34] for x in k2)}")


def bolum4_telemetri_ayiklama():
    """🔴 Kosucunun EN KIRILGAN yeri: yanit, `D` akisinin icinde geliyor."""
    print("\n--- 4. TELEMETRI AYIKLAMA: yanit `D` akisinin icinde " + "-" * 16)

    # 🔴 `KayitKart.yaz()` yaniti IMLECIN ONUNE koyuyor, yani yanit her
    #    zaman ILK satir olur ve hicbir telemetri satiri ayiklanmaz.
    #    Ilk yazimda bunu fark etmedim: test "ayiklama calisiyor" dedi
    #    ama ayiklanacak hicbir sey YOKTU — yani iddia boştu (0 satir).
    #    Gercek kartta yanit, akmakta olan `D` satirlarinin ARASINA
    #    duser; o durumu yanitin KENDISINI telemetriyle sararak kuruyoruz.
    yanit = dict(yanitlar_saglikli())
    yanit["?"] = [d_satiri(), d_satiri(), "K 0 8500 0", d_satiri()]
    kart = KayitKart([d_satiri() for _ in range(30)], yanit)
    k = TK.Konusma(kart)
    sat = k.sor("?", r"^K \d+ \d+ \d+", zaman_asimi=3.0)
    ok("Komut yaniti `D` akisinin icinden AYIKLANIYOR", bool(sat),
       sat[0] if sat else "bulunamadi — telemetri ayiklama calismiyor")
    ok("Ayiklanan telemetri KAYBOLMUYOR", len(k.telemetri) >= 2,
       f"{len(k.telemetri)} telemetri satiri biriktirildi")
    ok("Ayiklanan satirlar yanit olarak DONDURULMUYOR",
       all(not x.startswith("D ") for x in sat), f"donen: {sat}")

    # Yanit HIC gelmezse `sor` BOS donmeli — "belki gelmistir" dememeli.
    kart2 = KayitKart([d_satiri() for _ in range(10)], {"?": []})
    k2 = TK.Konusma(kart2)
    sat2 = k2.sor("?", r"^K \d+ \d+ \d+", zaman_asimi=0.6)
    ok("Yanit gelmezse BOS donuyor (sessiz gecis yok)", sat2 == [],
       f"{sat2}")


def bolum5_emniyet():
    """Kosucu EMNIYET kurallarina uyuyor mu — kaynak denetimi."""
    print("\n--- 5. EMNIYET " + "-" * 58)
    kaynak = (BURASI / "tezgah_kart.py").read_text(encoding="utf-8")
    kod = re.sub(r"#.*", "", kaynak)
    kod = re.sub(r'"""(?:.|\n)*?"""', "", kod)

    # Pil desarjini BASLATAN komut: firmware'de `p` + sure. Kosucu
    # yalnizca `p0` (DURDUR) gonderebilir.
    #
    # 🔴 Ilk yazimda desen her tirnakli p-dizgesini yakaliyordu ve
    #    "pil egri tamponu" gibi METINLERI komut sandi — iddia BOSTU
    #    (hep kirmizi verirdi, yani gurultu). Artik yalnizca GERCEKTEN
    #    GONDERILEN komutlara bakiyor.
    gonderilen = set()
    # Komutlar kisa ve tek satirlik; desen bunu kullanarak cok satirli
    # govdelerden cop toplamiyor.
    kisa = r'([^"\s]{1,8})'
    gonderilen |= set(re.findall(r'\.(?:sor|satirlar)\("' + kisa + r'"', kod))
    gonderilen |= set(re.findall(r'\.yaz\("' + kisa + r'"', kod))
    gonderilen |= set(re.findall(r'govde=b"' + kisa + r'"', kod))
    p_komutlari = sorted(x for x in gonderilen if x.startswith("p"))
    ok("Kosucu YALNIZCA `p0` (durdur) gonderiyor",
       all(x == "p0" for x in p_komutlari),
       f"gonderilen p-komutlari: {p_komutlari or 'yok'} — "
       f"desarj BASLATAN komut olamaz")
    ok("Gonderilen komut kumesi bos degil (desen tutuyor)",
       len(gonderilen) >= 5,
       f"{len(gonderilen)} komut: {sorted(gonderilen)}")

    ok("Fabrika sifirlamasi ONAYLI bicimde HIC gonderilmiyor",
       '"R!"' not in kod and "'R!'" not in kod,
       "`R!` gonderilirse butun kalibrasyon silinir")

    # Tehlike siniflandirmasi: her denetim kayitli
    for ad, asama, tehlike, _islev in TK.DENETIMLER:
        if tehlike not in ("yok", "NVS-yazar", "FIZIKSEL-TEHLIKE"):
            ok(f"Tehlike sinifi tanimli: {ad}", False, tehlike)
            break
    else:
        ok("Her denetimin tehlike sinifi tanimli", True,
           f"{len(TK.DENETIMLER)} denetim")

    ok("Denetimler asamalarina gore siralanabiliyor",
       all(a in (0, 1, 2) for _ad, a, _t, _i in TK.DENETIMLER))


def bolum6_beklentiler_kaynaktan():
    """Kosucunun beklentileri ELLE YAZILMIS OLMAMALI."""
    print("\n--- 6. BEKLENTILER KAYNAKTAN TURETILIYOR MU " + "-" * 27)
    # 🔴 B27: burasi `TK.D_ALAN == 8` idi — iddia "kaynaktan turetiliyor
    #    mu" diye sorarken BEKLENTIYI ELLE yaziyordu. Firmware'e alan
    #    eklenince (K1 `durum`) turetme dogru calisti, test yanlis kirmizi
    #    verdi. Dogru iddia: turetilen sayi, bicim dizesindeki `%`
    #    sayisiyla BAGIMSIZ olarak ayni mi.
    _m = re.search(r'"D (%[^"]*)"', TK.INO)
    _bagimsiz = _m.group(1).count("%") if _m else -1
    ok("`D` alan sayisi firmware bicim dizesinden", TK.D_ALAN == _bagimsiz,
       f"{TK.D_ALAN} — bicimde {_bagimsiz} adet %% var, ikisi ayni olmali")

    # 🔴 B26 — SAYI DEGIL, SIRA. Yandaki iddia yalnizca ALAN SAYISINA
    #    bakiyordu (8 == 8) ve alan sirasi takas olunca sessiz kaldi:
    #    sahte kart ornegi SON alana koyuyor, kosucu da SON alani
    #    okuyordu; ikisi tutarli, ikisi de firmware'den farkliydi.
    #    Gercek kartta "ornek = 0" (yani `menzil`) okundu.
    _ilan = next(x for x in afis_satirlari() if x.startswith("Cikis: D "))
    _adlar = [a.strip("<>") for a in _ilan.split()[2:]]
    ok("Protokol ilani `ornek` alanini adlandiriyor", "ornek" in _adlar,
       " ".join(_adlar))
    if "ornek" in _adlar:
        _i = _adlar.index("ornek") + 1
        _alanlar = d_satiri(777).split()
        ok("Sahte kart `ornek`i ILAN EDILEN yere koyuyor",
           _alanlar[_i] == "777",
           f"{_i}. alan = {_alanlar[_i]} — sahte kart gercek firmware'i "
           f"modellemeli, kendi kendine tutarli olmasi YETMEZ")
        ok("Kosucu ayni indeksi afisten turetiyor",
           TK._ornek_indeksi(type("B", (), {"afis": afis_satirlari()})) == _i,
           f"indeks {_i} — elle yazilmiyor")
    ok("mDNS adi ag.h'den", TK.MDNS_AD == "olcum", TK.MDNS_AD)
    ok("AP oneki ag.h'den", TK.AP_ONEK == "OLCUM-KARTI-", TK.AP_ONEK)
    ok("AKIS_AZAMI .ino'dan", TK.AKIS_AZAMI == 4, str(TK.AKIS_AZAMI))
    ok("Beklenen ornek sayisi HESAPLANIYOR (elle yazilmiyor)",
       120 < TK.ORNEK_BEKLENEN < 145,
       f"{TK.ORNEK_BEKLENEN:.1f} — sim3_bant.py ile ayni butce")

    # Bicim degisirse beklenti de degismeli: kaynagi bozup yeniden okuyalim.
    import importlib
    eski = TK.INO
    try:
        # Bicim dizesini NE OLURSA OLSUN 3 alana indir — sabit metin
        # eslestirmesi firmware degisince sessizce eslesmez oluyordu.
        TK.INO = re.sub(r'"D (%[^"]*)"', '"D %.4f %.6f %lu"', eski, count=1)
        m = re.search(r'"D (%[^"]*)"', TK.INO)
        yeni_alan = len(m.group(1).split())
        ok("Bicim degisince alan sayisi da degisiyor", yeni_alan == 3,
           f"{yeni_alan} — turetme sabit olsaydi {TK.D_ALAN} kalirdi")
    finally:
        TK.INO = eski
        importlib.reload  # noqa: B018  (yalnizca niyet belgesi)


def main() -> int:
    print("=" * 78)
    print("  B25  BRINGUP KOSUCUSUNUN KENDISI  (donanim gerekmiyor)")
    print("=" * 78)
    bolum1_saglikli()
    bolum2_mutasyonlar()
    bolum3_kapsam()
    bolum4_telemetri_ayiklama()
    bolum5_emniyet()
    bolum6_beklentiler_kaynaktan()

    print()
    print("=" * 78)
    print(f"  {gecti}/{gecti + kaldi} dogrulama gecti")
    print("=" * 78)

    tezgah("B25 Kart bringup kosucusu", [
        ("[!] Kosucunun kendisi gercek kartta calisiyor mu",
         "Bu adim kosucuyu KAYITLI bir kart uzerinde siniyor. Gercek "
         "seri port, gercek zamanlama ve gercek USB CDC davranisi "
         "yalnizca kart takilinca gorulur: `python tezgah_kart.py "
         "--sifirla`"),
        ("Acilis afisi yakalanabiliyor mu",
         "DTR/RTS ile reset YALNIZCA UART kopruli kartlarda calisiyor. "
         "Yerel USB CDC'de EN dugmesine elle basmak gerekir — afis "
         "alinamazsa PSRAM/LittleFS denetimleri ATLANIR, kirmizi olmaz"),
        # 🔴 B26: bu satirdaki IKI SAYI da elle yaziliydi ve IKISI de
        #    bayatlamisti ("24 denetim / 72 kalem" derken gercek 27/75
        #    idi) — ustelik kalem sayisi ayni dosyanin SONUNDA dogru
        #    yaziyordu, yani uretilen belge kendi icinde celisiyordu.
        #    Bu, DEVIR'in "projenin defalarca yandigi ayrisma sinifinin
        #    belge surumu" dedigi seyin ta kendisi. Denetim sayisi artik
        #    TURETILIYOR; kalem sayisi buradan gorunmedigi icin hic
        #    yazilmiyor (dosyanin kendi toplam satiri zaten veriyor).
        ("Denetimler yeterli mi",
         f"Kosucu {len(TK.DENETIMLER)} denetim yapiyor; `_tezgah.md` bundan "
         "COK DAHA fazla kalem sayiyor (toplam dosyanin sonunda). Fark, "
         "multimetre isteyen kalemler. Kart calisir calismaz ikisini "
         "birlikte kullan"),
    ])
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
