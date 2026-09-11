# -*- coding: utf-8 -*-
"""GERCEK KARTI SINAR — donanim geldiginde kosulacak bringup kosucusu.

    python tezgah_kart.py                    asama 0 (ciplak ESP32)
    python tezgah_kart.py --asama 1          + ADS1115 modulleri
    python tezgah_kart.py --asama 2          + analog on uc
    python tezgah_kart.py --port COM7        portu elle sec
    python tezgah_kart.py --sifirla          once karti sifirla (afis icin)
    python tezgah_kart.py --http olcum.local web katmanini da sina
    python tezgah_kart.py --liste            ne kosacagini yazar, kosmaz

🔴 NEDEN VAR. Zincirin 17 adimi TASARIMI dogruluyor; kart hic kurulmadi.
`uretim/_tezgah.md` neyin olculecegini soyluyor ama bir KONTROL LISTESI —
insan okur, koşmaz. Donanim geldiginde elle 70 kalem denemek hem yavas hem
atlamaya acik. Bu betik, elle denenmesi gerekmeyen her seyi OTOMATIK
kosturuyor; geriye yalnizca gercekten multimetre isteyen kalemler kaliyor.

── ASAMALAR ─────────────────────────────────────────────────────────
  0  Yalnizca ESP32-S3 karti. Analog on uc YOK, ADS YOK.
     Firmware acilis afisi, komut yuzeyi, blokaj sayaci, NVS savunmalari.
  1  + ADS1115 modulleri (I2C). Girisler BOSTA.
     Adresler, olcum satirinin BICIMI ve HIZI. DEGERLER anlamsiz — o
     yuzden hicbir denetim okunan gerilime/akima BAKMIYOR.
  2  + analog on uc kurulmus. Deger denetimleri burada anlamli olur.

Her denetim hangi asamada kosabilecegini KENDI soyluyor; ustteki asama
alttakileri de kosturuyor.

── EMNIYET ──────────────────────────────────────────────────────────
🔴 PIL DESARJINI BASLATAN KOMUT HICBIR ASAMADA OTOMATIK KOSTURULMUYOR.
   Yuk suren bir komutu bir test betiginin kendiliginden gondermesi kabul
   edilemez; `_tezgah.md`'de elle yapilacak kalem olarak duruyor.

⚠ NVS'e KALICI yazan denetimler `--yazmaya-izin-ver` istiyor. Varsayilan
  kapali: taze bir kartin kalibrasyonunu bir bringup kosusu bozmamali.

── BU BETIK NASIL SINANIYOR ─────────────────────────────────────────
`test_tezgah_kart.py` (zincirde B25) onu `KayitKart` uzerinde kosturuyor:
saglikli bir kart senaryosunda HEPSI yesil, kasitli bozulmus senaryolarda
DOGRU denetim kirmizi olmali. Yani kosucunun kendisi de mutasyonla
sinaniyor — cunku yanlis bir bringup testi, testsizlikten daha kotudur:
gecmeyen bir karta "gecti" der.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))

import tasarim3_sabit as T                              # noqa: E402
from tezgah import tezgah                               # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INO = (KOK / "kod" / "olcum-karti-a3"
       / "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
AG_H = (KOK / "kod" / "olcum-karti-a3"
        / "ag.h").read_text(encoding="utf-8", errors="replace")

# ── Firmware'den OKUNAN beklentiler ──────────────────────────────────
# Elle yazilan her beklenti, firmware degisince sessizce yanlis olur.
# Bu projenin butun ayrisma kusurlari boyle dogdu.


def _ino_sayi(ad: str, kaynak: str = INO) -> float:
    return float(re.search(rf"{ad}\s*=\s*([0-9.]+)", kaynak).group(1))


def _tanim(ad: str, kaynak: str) -> str:
    m = re.search(rf'#define {ad}\s+"([^"]*)"', kaynak)
    return m.group(1) if m else ""


RAPOR_MS = _ino_sayi("rapor_ms")
MDNS_AD = _tanim("AG_MDNS", AG_H)
AP_ONEK = re.search(r'"(OLCUM-KARTI-)%02X%02X"', AG_H).group(1)
AKIS_AZAMI = int(re.search(r"#define AKIS_AZAMI\s+(\d+)", INO).group(1))
CIFT_CEKIRDEK_ESIK_US = 20000       # DEVIR 5.12.34 — karar olcutu

# `D` satirinin alan sayisi, firmware'in KENDI bicim dizesinden.
_D_BICIM = re.search(r'"D (%[^"]*)"', INO)
D_ALAN = len(_D_BICIM.group(1).split()) if _D_BICIM else 0

# Beklenen ornek sayisi: rapor penceresinde kac ADS donusumu sigar.
# sim3_bant.py ile AYNI butce (B20) — orada dogrulaniyor.
_T_YAZ = T.I2C_YAZMA_BIT / T.I2C_HIZ * 1e6
_T_OKU = (20 + 29) / T.I2C_HIZ * 1e6
_T_DON = 1e6 / T.ADS_SPS
_PERIYOT_US = 2 * _T_YAZ + (_T_DON - _T_YAZ) + 2 * _T_OKU
ORNEK_BEKLENEN = RAPOR_MS * 1000.0 / _PERIYOT_US
ORNEK_PAY = 0.10                     # %10 — tik kuantalanmasi ve WiFi payi

# Telemetri satirlari: komut yaniti beklerken ARAYA GIRERLER.
TELEMETRI = ("D ", "S2 ", "S3 ", "M ", "W ", "B ", "E ", "T ", ": kalp")


class Sonuc:
    def __init__(self) -> None:
        self.gecti = 0
        self.kaldi = 0
        self.atlandi = 0
        self.kalanlar: list[str] = []

    def ok(self, ad: str, kosul: bool, ek: str = "") -> bool:
        if kosul:
            self.gecti += 1
            print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
        else:
            self.kaldi += 1
            self.kalanlar.append(ad)
            print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))
        return kosul

    def atla(self, ad: str, sebep: str) -> None:
        self.atlandi += 1
        print(f"  [--] {ad}   ATLANDI: {sebep}")

    def bilgi(self, s: str = "") -> None:
        print(f"       {s}" if s else "")


# ── Kartla konusma ───────────────────────────────────────────────────

class Konusma:
    """Komut gonderip yanit toplar. Telemetri satirlarini AYIKLAR.

    🔴 Kart surekli `D ...` basiyor (varsayilan 200 ms'de bir). Bir
    komutun yaniti bu akisin ICINE dusuyor — ayni tele yaziliyor. Naif
    bir "gonder, bir satir oku" yaklasimi %90 ihtimalle bir telemetri
    satiri okur ve YANLIS sonuc verir. O yuzden: gonder, sonra yanit
    desenine uyan satiri BULANA KADAR oku, telemetriyi biriktir.
    """

    def __init__(self, kart, sessiz: bool = False) -> None:
        self.kart = kart
        self.telemetri: list[str] = []
        self.sessiz = sessiz

    def _telemetri_mi(self, s: str) -> bool:
        return any(s.startswith(o) for o in TELEMETRI)

    def topla(self, sure: float) -> list[str]:
        """`sure` saniye boyunca gelen HER satiri topla."""
        son = time.monotonic() + sure
        cikti = []
        while time.monotonic() < son:
            s = self.kart.satir_oku(zaman_asimi=0.2)
            if s is None:
                time.sleep(0.01)
                continue
            s = s.rstrip()
            if not s:
                continue
            cikti.append(s)
            if self._telemetri_mi(s):
                self.telemetri.append(s)
        return cikti

    def sor(self, komut: str, desen: str, zaman_asimi: float = 3.0,
            adet: int = 1) -> list[str]:
        """Komutu gonder, `desen`e uyan `adet` satiri dondur.

        Bulunamazsa BOS liste doner — cagiran taraf bunu basarisizlik
        sayar. Sessizce "belki gelmemistir" demek, gecmeyen bir karta
        gecti demenin en kolay yoludur.
        """
        self.kart.yaz(komut)
        son = time.monotonic() + zaman_asimi
        bulunan = []
        r = re.compile(desen)
        while time.monotonic() < son and len(bulunan) < adet:
            s = self.kart.satir_oku(zaman_asimi=0.2)
            if s is None:
                time.sleep(0.01)
                continue
            s = s.rstrip()
            if not s:
                continue
            if self._telemetri_mi(s):
                self.telemetri.append(s)
                continue
            if r.search(s):
                bulunan.append(s)
        return bulunan

    def satirlar(self, komut: str, sure: float = 1.5) -> list[str]:
        """Komutu gonder, `sure` boyunca gelen TELEMETRI DISI satirlari dondur."""
        self.kart.yaz(komut)
        son = time.monotonic() + sure
        cikti = []
        while time.monotonic() < son:
            s = self.kart.satir_oku(zaman_asimi=0.2)
            if s is None:
                time.sleep(0.01)
                continue
            s = s.rstrip()
            if not s:
                continue
            if self._telemetri_mi(s):
                self.telemetri.append(s)
                continue
            cikti.append(s)
        return cikti


# ── HTTP ─────────────────────────────────────────────────────────────

def http(adres: str, yol: str, basliklar: dict | None = None,
         govde: bytes | None = None, metod: str = "GET",
         zaman_asimi: float = 5.0):
    """(durum, basliklar, govde) dondurur. Ag hatasi (0, {}, hata) olur."""
    url = f"http://{adres}{yol}"
    istek = urllib.request.Request(url, data=govde, method=metod)
    for k, v in (basliklar or {}).items():
        istek.add_header(k, v)
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            return y.status, dict(y.headers), y.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return 0, {}, str(e).encode()


# ═══════════════════════════════════════════════════════ DENETIMLER
#
# Her denetim bir islev; `DENETIMLER` listesi ad/asama/tehlike ile
# birlikte tutuyor. Beklenen dizgeler firmware kaynagindan ALINDI ve
# ASCII onekle eslesiyor — em-dash gibi karakterler seri hattinda
# bozulabilir, iddia bozulmasin diye.


class Baglam:
    def __init__(self, s, k, afis, http_adres, yazma_izni):
        self.s = s                    # Sonuc
        self.k = k                    # Konusma
        self.afis = afis              # acilis afisi satirlari (ya da None)
        self.http = http_adres        # "olcum.local" / IP / None
        self.yazma_izni = yazma_izni


def _afis_ara(c, parca):
    return any(parca in x for x in (c.afis or []))


# ── Asama 0 · acilis afisi ───────────────────────────────────────────

def d_afis_basligi(c):
    if c.afis is None:
        c.s.atla("Acilis afisi alindi", "kart sifirlanmadi (--sifirla)")
        return
    c.s.ok("Acilis afisi alindi", _afis_ara(c, "Olcum Karti"),
           "afis yalnizca acilista basiliyor")


def d_psram(c):
    if c.afis is None:
        c.s.atla("PSRAM bulundu ve boyutu dogru", "afis yok")
        return
    sat = [x for x in c.afis if x.startswith("PSRAM:")]
    if not c.s.ok("PSRAM satiri var", bool(sat), "afiste PSRAM: bekleniyor"):
        return
    m = re.search(r"PSRAM:\s*(\d+)\s*KB", sat[0])
    c.s.ok("PSRAM >= 8 MB (N16R8)", bool(m) and int(m.group(1)) >= 8 * 1024,
           sat[0].strip() + "  — yoksa FQBN'de PSRAM=opi eksik demektir")


def d_pil_tampon(c):
    if c.afis is None:
        c.s.atla("Pil egri tamponu ayrildi", "afis yok")
        return
    sat = [x for x in c.afis if "pil egri tamponu" in x]
    if not c.s.ok("Pil egri tamponu satiri var", bool(sat)):
        return
    c.s.ok("Pil egri tamponu AYRILDI", "AYRILAMADI" not in sat[0],
           sat[0].strip())


def d_littlefs(c):
    if c.afis is None:
        c.s.atla("Arayuz LittleFS'ten servis ediliyor", "afis yok")
        return
    sat = [x for x in c.afis if x.startswith("Arayuz:")]
    if not c.s.ok("Arayuz satiri var", bool(sat)):
        return
    c.s.ok("Arayuz LittleFS'te", "LittleFS" in sat[0],
           sat[0].strip() + "  — yoksa `python arayuz-yaz.py` calistirilacak")


def d_ag_satiri(c):
    if c.afis is None:
        c.s.atla("Ag kipi bildirildi", "afis yok")
        return
    c.s.ok("Ag kipi bildirildi", _afis_ara(c, "Ag: "),
           next((x.strip() for x in c.afis if x.startswith("Ag: ")), ""))


def d_parola_uyarisi(c):
    """Parola kurulu DEGILSE kart bunu YUKSEK SESLE soylemeli."""
    if c.afis is None:
        c.s.atla("Parolasizlik acikca uyariliyor", "afis yok")
        return
    c.s.ok("Parola durumu afiste ACIKCA yaziyor",
           _afis_ara(c, "web parolasi YOK") or _afis_ara(c, "AP parolasi"),
           "parolasizsa sessiz kalinmamali")


# ── Asama 0 · arastirmanin isaret ettigi ek denetimler ───────────────
# (B25 hazirlanirken bagimsiz bir denetim bunlari kaynaktan cikardi)

def d_skop_surucusu(c):
    """OLUMSUZ denetim: skop DMA surucusu kurulamadiysa afiste soyluyor.

    Bu analog on uce BAGLI DEGIL — ic ADC + DMA yolu ayakta mi diye
    soruyor. Kurulamamissa `t`/`w` komutlarinin hicbiri kosmaz.
    """
    if c.afis is None:
        c.s.atla("Osiloskop DMA surucusu kuruldu", "afis yok")
        return
    c.s.ok("Osiloskop DMA surucusu kuruldu",
           not _afis_ara(c, "osiloskop suruculu kurulamadi"),
           "kurulamadiysa t/tB/w komutlari hic calismaz")


def d_afis_satirlari_kapali(c):
    """Afisin her satiri KAPANMIS mi — yapisik satir yok mu.

    🔴 B25 hazirlanirken bulundu: `Ag:` blogunun sonunda `println`
    YOKTU ve cikti `...http://192.168.4.1Arayuz: ...` seklinde
    yapisiyordu. Adresi kopyalayan kullanici BOZUK adres aliyordu.
    Firmware duzeltildi; bu denetim geri gelmesini engelliyor.
    """
    if c.afis is None:
        c.s.atla("Afis satirlari yapisik degil", "afis yok")
        return
    yapisik = [x for x in c.afis if "Arayuz:" in x and not x.startswith("Arayuz:")]
    c.s.ok("Afis satirlari yapisik DEGIL", not yapisik,
           (yapisik[0][:70] if yapisik else "her satir kendi basina") +
           "  — yapisiksa IP adresi bir sonraki etikete karisir")


def d_protokol_satiri(c):
    """`D` satirinin alan adlari afiste ilan ediliyor mu.

    Arayuz, sahte-kart.js ve bu kosucu ayni siraya dayaniyor; alan
    eklenirse hepsi birden guncellenmeli (ino'daki not bunu soyluyor).
    """
    if c.afis is None:
        c.s.atla("Cikis protokolu ilan ediliyor", "afis yok")
        return
    sat = [x for x in c.afis if x.startswith("Cikis: D ")]
    if not c.s.ok("Cikis protokolu ilan ediliyor", bool(sat)):
        return
    alan = len(sat[0].split()) - 2          # "Cikis:" ve "D" haric
    c.s.ok("Ilan edilen alan sayisi firmware bicimiyle AYNI",
           alan == D_ALAN,
           f"afiste {alan}, bicim dizesinde {D_ALAN} — ayrisirsa arayuz "
           f"ve kosucu yanlis alani okur")


# ── Asama 0 · komut yuzeyi ───────────────────────────────────────────

def d_ayar_dokumu(c):
    sat = c.k.satirlar("?", sure=1.5)
    c.s.ok("`?` ayar dokumu basiyor",
           any(x.startswith("A menzil=") for x in sat),
           "; ".join(x[:40] for x in sat[:2]))
    c.s.ok("`?` menzil satirini basiyor",
           any(x.startswith("R normal=") for x in sat))


def d_blokaj_sayaci(c):
    """[!] CIFT CEKIRDEK KARARININ TEK OLCUTU."""
    sat = c.k.sor("?", r"^K \d+ \d+ \d+", zaman_asimi=3.0)
    if not c.s.ok("`K` blokaj sayaci satiri geliyor", bool(sat),
                  "K <atlanan ms> <en uzun dongu us> <20ms ustu tur>"):
        return
    m = re.match(r"K (\d+) (\d+) (\d+)", sat[0])
    azami = int(m.group(2))
    c.s.bilgi(f"loop_azami_us = {azami}   esik {CIFT_CEKIRDEK_ESIK_US}")
    c.s.ok("loop_azami_us cift cekirdek esiginin ALTINDA",
           azami < CIFT_CEKIRDEK_ESIK_US,
           f"{azami} us — ustundeyse olcum dongusu cekirdek 1'e "
           f"tasinacak (DEVIR 5.12.34)")
    c.s.ok("Atlanan enerji penceresi yok", int(m.group(1)) == 0,
           f"atlanan {m.group(1)} ms")


def d_ciplak_g_reddi(c):
    """K3: ciplak `g` bir kanali KALICI tugluyordu."""
    sat = c.k.sor("g", r"^! g: gerilim degeri gerekli", zaman_asimi=3.0)
    c.s.ok("Ciplak `g` REDDEDILIYOR (K3 tuglalama)", bool(sat),
           "kabul edilirse kazanc 0 NVS'e yazilir, kanal kalici olur")


def d_ciplak_i_reddi(c):
    sat = c.k.sor("i", r"^! i: akim degeri gerekli", zaman_asimi=3.0)
    c.s.ok("Ciplak `i` REDDEDILIYOR", bool(sat))


def d_ciplak_f_reddi(c):
    sat = c.k.sor("f", r"^! f: frekans gerekli", zaman_asimi=3.0)
    c.s.ok("Ciplak `f` REDDEDILIYOR (sessiz DC gecisi)", bool(sat))


def d_fabrika_onayi(c):
    """`R` tek basina fabrika sifirlamasi YAPMAMALI."""
    sat = c.k.sor("R", r"^! R: onay gerekli", zaman_asimi=3.0)
    c.s.ok("`R` onaysiz fabrika sifirlamasi YAPMIYOR", bool(sat),
           "onaysiz kabul edilirse butun kalibrasyon tek harfle gider")


def d_bilinmeyen_komut(c):
    sat = c.k.sor("QQ", r"^! bilinmeyen komut", zaman_asimi=3.0)
    c.s.ok("Bilinmeyen komut ACIKCA reddediliyor", bool(sat),
           "sessizce yutulursa yazim hatasi fark edilmez")


def d_ag_durumu(c):
    sat = c.k.satirlar("N", sure=1.5)
    c.s.ok("`N` ag durumunu basiyor",
           any(x.startswith("* ag:") for x in sat),
           "; ".join(x[:50] for x in sat[:2]))
    c.s.ok("`N` web parolasi durumunu basiyor",
           any("web parolasi" in x for x in sat))


# ── Asama 0/1 · I2C ──────────────────────────────────────────────────

def d_i2c_tarama_calisiyor(c):
    sat = c.k.sor("#", r"^I2C:", zaman_asimi=3.0)
    c.s.ok("`#` I2C taramasi calisiyor", bool(sat),
           sat[0][:60] if sat else "yanit yok")


def d_i2c_adresler(c):
    """ADS modulleri bagliyken 0x48 ve 0x49 GORUNMELI.

    ⚠ Kapsam tuzagi: `beklenen: 0x48 (akim)  0x49 (gerilim)` satiri
    adresleri ZATEN iceriyor. Bulunan listesine bakmadan `"0x48" in
    metin` demek, hicbir cihaz bagli olmasa bile GECERDI.
    """
    sat = c.k.satirlar("#", sure=2.0)
    bulunan = [x for x in sat if x.startswith("I2C:")]
    metin = bulunan[0] if bulunan else ""
    c.s.ok("ADS #1 0x48 adresinde gorunuyor", "0x48" in metin,
           "gorunmuyorsa: SDA/SCL ters, ADDR bosta, ya da pull-up yok")
    c.s.ok("ADS #2 0x49 adresinde gorunuyor", "0x49" in metin,
           "ADS #2'nin ADDR pini +3V3'e baglanmali")


# ── Asama 1 · olcum satiri ───────────────────────────────────────────

def d_olcum_satiri_bicimi(c):
    sat = [x for x in c.k.topla(2.0) if x.startswith("D ")]
    if not c.s.ok("`D` olcum satiri geliyor", bool(sat),
                  f"{RAPOR_MS:.0f} ms'de bir bekleniyor"):
        return
    alan = len(sat[0].split())
    c.s.ok("`D` satirinda dogru alan sayisi", alan == D_ALAN + 1,
           f"{alan - 1} alan, firmware bicimi {D_ALAN} diyor")


def d_ornek_sayisi(c):
    """[!] Ilk, en ucuz ve en onemli test."""
    sat = [x for x in c.k.topla(3.0) if x.startswith("D ")]
    if not c.s.ok("`D` satiri ornek sayisi tasiyor", bool(sat)):
        return
    try:
        n = int(sat[-1].split()[-1])
    except (ValueError, IndexError):
        c.s.ok("`D` son alani ornek sayisi", False, sat[-1][:60])
        return
    alt = ORNEK_BEKLENEN * (1 - ORNEK_PAY)
    ust = ORNEK_BEKLENEN * (1 + ORNEK_PAY)
    c.s.bilgi(f"ornek = {n}   beklenen {ORNEK_BEKLENEN:.0f} "
              f"({alt:.0f}..{ust:.0f})")
    c.s.ok("Ornek sayisi beklenen bantta", alt <= n <= ust,
           f"{n} — ~100 ise enableDelay(false) ise yaramamis, "
           f"~19 ise B20 duzeltmeleri gitmis demektir")


def d_olcum_hizi(c):
    t0 = time.monotonic()
    sat = [x for x in c.k.topla(3.0) if x.startswith("D ")]
    gecen = time.monotonic() - t0
    if len(sat) < 3:
        c.s.ok("`D` satir hizi olculebildi", False, f"{len(sat)} satir")
        return
    hiz = len(sat) / gecen
    beklenen = 1000.0 / RAPOR_MS
    c.s.ok("`D` satir hizi rapor penceresiyle uyumlu",
           abs(hiz - beklenen) / beklenen < 0.25,
           f"{hiz:.1f}/s, beklenen {beklenen:.1f}/s")


# ── Web katmani (HTTP) ───────────────────────────────────────────────

def d_web_kok(c):
    if not c.http:
        c.s.atla("Arayuz HTTP'den servis ediliyor", "--http verilmedi")
        return
    durum, bas, govde = http(c.http, "/")
    if not c.s.ok("Kok istegi yanit veriyor", durum == 200,
                  f"durum {durum}"):
        return
    c.s.ok("Kok HTML donuyor", b"<!doctype" in govde[:200].lower()
           or b"<html" in govde[:200].lower(), f"{len(govde)} bayt")


def d_web_csrf(c):
    """Ozel baslik OLMADAN komut ucu 400 donmeli."""
    if not c.http:
        c.s.atla("CSRF: ozel baslik zorunlu", "--http verilmedi")
        return
    durum, _b, govde = http(c.http, "/komut", govde=b"?", metod="POST")
    c.s.ok("CSRF: X-Olcum basligi olmadan REDDEDILIYOR", durum == 400,
           f"durum {durum} — 204 donduyse savunma SESSIZCE olmus demektir "
           f"(collectHeaders cagrilmiyor olabilir)")


def d_web_jeton(c):
    """Tehlikeli komut, gecersiz jetonla 403 donmeli."""
    if not c.http:
        c.s.atla("Jeton denetimi", "--http verilmedi")
        return
    durum, _b, _g = http(c.http, "/komut", basliklar={"X-Olcum": "1",
                                                      "X-Jeton": "yanlis"},
                         govde=b"z", metod="POST")
    c.s.ok("Gecersiz jeton REDDEDILIYOR", durum == 403, f"durum {durum}")


def d_web_p0_serbest(c):
    """[!] EMNIYET: `p0` (DURDUR) jetonsuz da gecmeli."""
    if not c.http:
        c.s.atla("p0 her zaman serbest", "--http verilmedi")
        return
    durum, _b, _g = http(c.http, "/komut", basliklar={"X-Olcum": "1"},
                         govde=b"p0", metod="POST")
    c.s.ok("`p0` (DURDUR) jetonsuz GECIYOR", durum == 204,
           f"durum {durum} — reddediliyorsa desarji durdurmanin en hizli "
           f"yolu kapali demektir; bu bir EMNIYET kusuru")


def d_web_host(c):
    """DNS rebinding: yabanci Host reddedilmeli."""
    if not c.http:
        c.s.atla("Host beyaz listesi", "--http verilmedi")
        return
    durum, _b, _g = http(c.http, "/komut",
                         basliklar={"X-Olcum": "1", "Host": "kotu.example.com"},
                         govde=b"p0", metod="POST")
    c.s.ok("Yabanci Host REDDEDILIYOR", durum == 403, f"durum {durum}")


# ── Kayit ────────────────────────────────────────────────────────────
# (ad, asama, tehlike, islev)

DENETIMLER = [
    ("Acilis afisi",            0, "yok", d_afis_basligi),
    ("PSRAM",                   0, "yok", d_psram),
    ("Pil egri tamponu",        0, "yok", d_pil_tampon),
    ("LittleFS arayuzu",        0, "yok", d_littlefs),
    ("Ag kipi",                 0, "yok", d_ag_satiri),
    ("Parola uyarisi",          0, "yok", d_parola_uyarisi),
    ("Osiloskop DMA surucusu",  0, "yok", d_skop_surucusu),
    ("Afis satirlari kapali",   0, "yok", d_afis_satirlari_kapali),
    ("Cikis protokolu ilani",   0, "yok", d_protokol_satiri),
    ("Ayar dokumu (?)",         0, "yok", d_ayar_dokumu),
    ("Blokaj sayaci (K)",       0, "yok", d_blokaj_sayaci),
    ("Ciplak g reddi",          0, "yok", d_ciplak_g_reddi),
    ("Ciplak i reddi",          0, "yok", d_ciplak_i_reddi),
    ("Ciplak f reddi",          0, "yok", d_ciplak_f_reddi),
    ("Fabrika sifirlama onayi", 0, "yok", d_fabrika_onayi),
    ("Bilinmeyen komut",        0, "yok", d_bilinmeyen_komut),
    ("Ag durumu (N)",           0, "yok", d_ag_durumu),
    ("I2C taramasi calisiyor",  0, "yok", d_i2c_tarama_calisiyor),
    ("Web: kok",                0, "yok", d_web_kok),
    ("Web: CSRF",               0, "yok", d_web_csrf),
    ("Web: jeton",              0, "yok", d_web_jeton),
    ("Web: p0 serbest",         0, "yok", d_web_p0_serbest),
    ("Web: Host beyaz listesi", 0, "yok", d_web_host),

    ("I2C adresleri",           1, "yok", d_i2c_adresler),
    ("Olcum satiri bicimi",     1, "yok", d_olcum_satiri_bicimi),
    ("Ornek sayisi",            1, "yok", d_ornek_sayisi),
    ("Olcum hizi",              1, "yok", d_olcum_hizi),
]


# ═══════════════════════════════════════════════════════ KOSUM

def kart_ac(port: str | None):
    """Gercek karti acar. (kart, hata) dondurur."""
    import kart_baglanti
    portlar = kart_baglanti.portlari_listele()
    if port is None:
        if not portlar:
            return None, "\n".join([
                "Seri port bulunamadi.",
                "  * Kart takili mi, surucu kurulu mu?"
                " (Aygit Yoneticisi -> Baglanti noktalari)",
                "  * 🔴 IKI USB SOKETLI bir gelistirme kartiysa UART/COM",
                "    soketine tak, YEREL USB'ye degil. Firmware `Serial`i",
                "    UART koprusunde tutuyor: hedef2.py CDCOnBoot/USBMode'u",
                "    BILEREK eklemiyor (yerel CDC tezgah ilk acilisini",
                "    bozabilir). Yanlis sokette HICBIR satir gelmez.",
            ])
        if len(portlar) > 1:
            return None, (f"Birden cok port var: {', '.join(portlar)}. "
                          f"--port ile secin.")
        port = portlar[0]
    kart = kart_baglanti.SeriKart(port)
    try:
        kart.ac()
    except OSError as e:
        return None, f"{port} acilamadi: {e}"
    return kart, None


def afis_al(kart, konusma, sifirla: bool, bekle: float = 3.0):
    """Acilis afisini toplar. Alinamazsa None.

    🔴 `SeriKart.ac()` DTR/RTS'i DISABLE kuruyor — yani baglanmak karti
    SIFIRLAMIYOR (bu bilerek: kazara reset atmasin). Afis ise yalnizca
    acilista basiliyor. O yuzden afisi gormek icin ya kart yeni
    acilmis olmali ya da `--sifirla` verilmeli.
    """
    if not sifirla:
        return None
    if not kart.sifirla():
        return None
    sat = konusma.topla(bekle)
    # Afis geldi mi? Baslik satiri yoksa kart yerel USB CDC'li olabilir
    # ve DTR/RTS bir pine bagli degildir — sinyaller gitti ama reset olmadi.
    return sat if any("Olcum Karti" in x for x in sat) else None


def kosum(kart, asama: int, http_adres, sifirla: bool, yazma_izni: bool):
    s = Sonuc()
    k = Konusma(kart)

    print("=" * 78)
    print(f"  TEZGAH BRINGUP — asama {asama}")
    print("=" * 78)
    print(f"  kart      : {kart.ad}")
    print(f"  web       : {http_adres or '(atlandi, --http ile acilir)'}")
    print(f"  NVS yazma : {'ACIK' if yazma_izni else 'kapali'}")
    print()

    afis = afis_al(kart, k, sifirla)
    if sifirla and afis is None:
        print("  ⚠ Acilis afisi ALINAMADI. Iki sebebi olabilir:")
        print("    * kart yerel USB CDC kullaniyor (DTR/RTS bir pine bagli")
        print("      degil) — EN dugmesine basip komutu tekrar calistirin")
        print("    * kart acilis afisini basmiyor (firmware eski olabilir)")
        print()

    c = Baglam(s, k, afis, http_adres, yazma_izni)
    for ad, gereken, tehlike, islev in DENETIMLER:
        if gereken > asama:
            continue
        if tehlike != "yok" and not yazma_izni:
            s.atla(ad, f"{tehlike} — --yazmaya-izin-ver gerekiyor")
            continue
        print(f"\n--- {ad}")
        try:
            islev(c)
        except Exception as e:                      # noqa: BLE001
            s.ok(ad, False, f"denetim COKTU: {type(e).__name__}: {e}")

    print()
    print("=" * 78)
    print(f"  {s.gecti} gecti · {s.kaldi} kaldi · {s.atlandi} atlandi")
    if s.kalanlar:
        print()
        print("  KALANLAR:")
        for x in s.kalanlar:
            print(f"    * {x}")
    print("=" * 78)
    return s


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Gercek kart uzerinde bringup denetimleri")
    ap.add_argument("--asama", type=int, default=0, choices=[0, 1, 2],
                    help="0 ciplak ESP32 · 1 +ADS · 2 +analog on uc")
    ap.add_argument("--port", help="COM portu (bosken tek port secilir)")
    ap.add_argument("--http", help="kartin adresi, orn. olcum.local ya da IP")
    ap.add_argument("--sifirla", action="store_true",
                    help="baslamadan once karti sifirla (acilis afisi icin)")
    ap.add_argument("--yazmaya-izin-ver", action="store_true",
                    dest="yazma_izni",
                    help="NVS'e KALICI yazan denetimleri de kostur")
    ap.add_argument("--liste", action="store_true",
                    help="denetimleri yazar, kosmaz")
    a = ap.parse_args()

    if a.liste:
        print("=" * 78)
        print("  TEZGAH BRINGUP DENETIMLERI")
        print("=" * 78)
        for ad, gereken, tehlike, islev in DENETIMLER:
            im = {0: "ciplak ESP32", 1: "+ADS", 2: "+analog on uc"}[gereken]
            t = "" if tehlike == "yok" else f"  [{tehlike}]"
            print(f"  asama {gereken} ({im:14}) {ad}{t}")
            if islev.__doc__:
                print(f"       {islev.__doc__.strip().splitlines()[0]}")
        print()
        print(f"  Toplam {len(DENETIMLER)} denetim.")
        print("  Elle yapilacaklar (multimetre isteyenler): uretim/_tezgah.md")
        return 0

    kart, hata = kart_ac(a.port)
    if hata:
        print("=" * 78)
        print("  KART ACILAMADI")
        print("=" * 78)
        print(f"  {hata}")
        print()
        print("  Donanimsiz denemek icin:  python test_tezgah_kart.py")
        return 2
    try:
        s = kosum(kart, a.asama, a.http, a.sifirla, a.yazma_izni)
    finally:
        kart.kapat()

    tezgah("B25 Kart bringup", [
        ("[!] Bu betigin ATLADIGI kalemler",
         "Multimetre isteyen her sey hala elle: Vref rayi, bolucu "
         "dogrusallugu, +3V3 geri beslemesi, sont Kelvin baglantisi. "
         "Listesi uretim/_tezgah.md'de"),
        ("[!] Pil desarjini BASLATAN test",
         "Bu betik hicbir asamada yuk surmuyor. Failsafe ve baypas "
         "denetimi elle yapilacak — kart calisirken RESET at, yukun "
         "kesildigini gor"),
        ("Acilis afisi gorulemiyorsa",
         "Yerel USB CDC'li kartta DTR/RTS reset atmiyor. EN dugmesine "
         "basip `--sifirla` ile tekrar kostur"),
    ])
    return 0 if s.kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
