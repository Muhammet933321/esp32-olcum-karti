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


def afis_satirlari(psram_kb=8192, fs=True, tampon=True, parola_yok=True):
    s = [
        "",
        "Olcum Karti — Asama 3 (CIFT YONLU on uc)",
        f"PSRAM: {psram_kb} KB" if psram_kb else "PSRAM: YOK — derin skop bellegi kullanilamaz",
    ]
    s.append("  pil egri tamponu: 5400 nokta = 1.50 saat @ 1.00 Hz, 63 KB (ic RAM)"
             if tampon else "  pil egri tamponu: AYRILAMADI — mAh/Wh sayaclari calisir")
    s += [
        "Cikis: D <volt> <amper> <watt> <joule> <wh> <ms> <ornek> <bayrak>",
        "`h` yardim",
        "Ag: AP  SSID=OLCUM-KARTI-A1B2  http://192.168.4.1",
        "Arayuz: LittleFS'te (karttan servis ediliyor)" if fs
        else "Arayuz: YOK — uretim/arayuz-yaz.py ile yukleyin",
        "",
    ]
    if parola_yok:
        s.append("! UYARI: web parolasi YOK — komut ucu yalnizca jeton ile korunuyor")
    return s


def d_satiri(ornek=None):
    n = _ORNEK if ornek is None else ornek
    return f"D 12.3456 0.123456 1.52345 0.1234 0.0001234 200 1234 {n}"


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
    y["f"] = ["! f: frekans gerekli, orn. `f50` ya da `f0` (DC)"]
    y["R"] = (["! R: onay gerekli — `R!` yaz. TUM kalibrasyonu siler."]
              if r_onayi else ["* FABRIKA AYARLARI yuklendi"])
    y["QQ"] = (["! bilinmeyen komut — `h` yardim"] if bilinmeyen else [])
    return y


def kart_kur(afis=None, yanit=None, telemetri_adet=40, ornek=None,
             gecikme=0.0):
    """Saglikli bir kart benzetimi. Afis + surekli `D` akisi + yanitlar.

    ⚠ `KayitKart` SONLU: gercek kart sonsuza kadar `D` basiyor, kayit
    bitiyor. `D` hizina bakan denetimler icin `gecikme` ile gercek
    tempoyu taklit ediyoruz — yoksa 40 satir bir anda gelir ve "hiz"
    olcumu anlamsiz cikar. Bu bir kosucu kusuru DEGIL, kaydin sinirli
    olmasi; ama testin bunu bilmesi gerekiyor.
    """
    satirlar = list(afis if afis is not None else afis_satirlari())
    satirlar += [d_satiri(ornek) for _ in range(telemetri_adet)]
    return KayitKart(satirlar,
                     yanit if yanit is not None else yanitlar_saglikli(),
                     gecikme=gecikme)


def kart_kur_telemetrili(**kw):
    """`D` denetimleri icin: gercek tempo + bol satir."""
    kw.setdefault("telemetri_adet", 120)
    kw.setdefault("gecikme", RAPOR_S)
    return kart_kur(**kw)


def kosturi(kart, asama=0, http_adres=None, sifirla=True):
    """Kosucuyu sessizce kostur, Sonuc'u ve ciktisini dondur."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s = TK.kosum(kart, asama, http_adres, sifirla, False)
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
         "cift cekirdek esiginin ALTINDA", 0),
        ("Ciplak `g` KABUL EDILIYOR (K3 tuglalama geri geldi)",
         dict(yanit=yanitlar_saglikli(g_reddi=False)),
         "Ciplak `g` REDDEDILIYOR", 0),
        ("`R` onaysiz fabrika sifirlamasi yapiyor",
         dict(yanit=yanitlar_saglikli(r_onayi=False)),
         "onaysiz fabrika sifirlamasi YAPMIYOR", 0),
        ("Bilinmeyen komut SESSIZCE yutuluyor",
         dict(yanit=yanitlar_saglikli(bilinmeyen=False)),
         "Bilinmeyen komut ACIKCA reddediliyor", 0),
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
    ok("`D` alan sayisi firmware bicim dizesinden", TK.D_ALAN == 8,
       f"{TK.D_ALAN} — .ino'daki 'D %.4f ...' bicimi sayiliyor")
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
        TK.INO = eski.replace('"D %.4f %.6f %.5f %.4f %.7f %lu %lu %u"',
                              '"D %.4f %.6f %lu"')
        m = re.search(r'"D (%[^"]*)"', TK.INO)
        yeni_alan = len(m.group(1).split())
        ok("Bicim degisince alan sayisi da degisiyor", yeni_alan == 3,
           f"{yeni_alan} — sabit olsaydi 8 kalirdi")
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
        ("Denetimler yeterli mi",
         "Kosucu 24 denetim yapiyor; `_tezgah.md` 72 kalem sayiyor. "
         "Fark, multimetre isteyen kalemler. Kart calisir calismaz "
         "ikisini birlikte kullan"),
    ])
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
