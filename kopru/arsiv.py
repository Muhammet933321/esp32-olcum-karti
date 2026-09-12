# -*- coding: utf-8 -*-
"""Koprunun ARSIVI — asil kayit burada.

🔴 NEDEN TARAYICI DEGIL: `arayuz3/app.js` pil egrisini IndexedDB'de
tutuyor ve dosyanin kendi yorumu bunu durustce soyluyor —
*"tarayicinin verisidir, 'tarayici verilerini temizle' denince gider"*.
Bir olcum kaydinin omru tarayici tercihine bagli olamaz. Kopru varken
ASIL ARSIV DISKTEDIR; IndexedDB yalnizca cevrimdisi cizim icin yerel
kopya olur.

BICIM — eklemeli ham satir gunlugu:

    <ms>\t<satir>

`<ms>` koprunun basladigi andan itibaren gecen milisaniye. Ayrac TAB
oldugu icin ham satir `split("\\t", 1)[1]` ile BIREBIR geri aliniyor —
kartin urettigi baytlar hicbir yerde donusturulmuyor. Turetilmis CSV bu
gunlukten URETILIYOR, ayri tutulmuyor: iki temsil ayrisamaz.

⚠ CSV'nin bicimi Excel-TR uyumlu (`;` ayrac + BOM). `app.js`'te iki ayri
  CSV bicimi vardi (`csvIndir` `;`+BOM, `pilCsvIndir` `,` ve BOM'suz);
  burada TEK bicim var ve o Excel-TR olan.

── SKOP YAKALAMALARI (B35) ───────────────────────────────────────────
Gunluk yalnizca `D` satirlarini degil, skopun `S2 … E` ASCII dokumunu
de tasiyor. "Geriye donuk dalga sekli" ozelligi bu yuzden AYRI BIR
DOSYA GEREKTIRMIYOR: `skop_bloklari()` ayni gunlukten turetiyor,
`csv_uret`in `D` satirlarindan CSV uretmesiyle ayni desen.

🔴 HAM ADC KODU saklaniyor, mV DEGIL. B34'te olculen dogrusalsizligin
   duzeltmesi henuz karara baglanmadi; ham saklandigi icin ileride
   bulunacak her duzeltme ESKI kayitlara da uygulanabilir. mV
   saklansaydi her kayit o gunku kalibrasyona civilenirdi.
"""
from __future__ import annotations

import io
import os
import struct
import time
from pathlib import Path

# `D` satirinin alanlari — firmware'deki snprintf bicimiyle AYNI SIRA.
D_BASLIK = ["ms_kopru", "volt", "amper", "watt", "joule", "wh",
            "kart_ms", "ornek", "menzil"]

# ═══════════════════ SKOP YAKALAMALARI (B35) ═════════════════════════
#
# 🔴 TEK TEMSIL KURALI. Yakalama diske AYRI bir dosya olarak YAZILMIYOR;
#    `.satir` gunlugunde zaten duran `S2 … E` blogundan URETILIYOR —
#    `csv_uret`in `D` satirlarindan CSV uretmesiyle ayni desen. Ayri
#    tutulsaydi iki temsil ayrisirdi (bu projenin tekrarlayan hatasi).
#
# 🔴 HAM KOD SAKLANIYOR, VOLT DEGIL. Kalibrasyon (B34) henuz karara
#    baglanmadi; ham kod saklandigi icin ileride bulunacak her duzeltme
#    ESKI KAYITLARA DA geriye donuk uygulanabilir. mV saklansaydi her
#    kayit o gunku kalibrasyona CIVILENIRDI ve geri donusu olmazdi.
#
# ⚠ AYNI COZUCU IKI YERDE: koprunun canli `/skop.bin` ucu da, arsiv
#   okuyucusu da `SkopCozucu`yu besliyor. Iki ayri ayristirici yazilsaydi
#   biri sessizce baska bir dalga cizerdi.
SKOP_IMZA = b"S3B"
SKOP_SURUM = 1
SKOP_BASLIK_BAYT = 32
SKOP_AZAMI_ORNEK = 8192          # bozuk `S2` satirinin bellegi yemesine karsi


def skop_ikili(blok: dict) -> bytes:
    """Blogu firmware'in `/skop.bin` bicimine paketle.

    🔴 BICIM FIRMWARE'DEN KOPYALANMADI, ONA UYULDU: arayuzde TEK bir
       ikili cozucu var (`skopIkiliCoz`); canli yakalama da arsivden
       acilan eski kayit da ondan geciyor. Kopru baska bir bicim uretseydi
       arayuzde ikinci bir cozucu gerekirdi ve ikisi ayrisirdi.

    `adet` alanina BILDIRILEN degil GERCEK ornek sayisi yaziliyor —
    kirpilmis bir kayitta arayuzun uzunluk denetimi yoksa cizim tamponun
    disini okurdu.
    """
    ornek = blok["ornek"]
    n = len(ornek)
    b = bytearray(SKOP_BASLIK_BAYT)
    b[0:3] = SKOP_IMZA
    b[3] = SKOP_SURUM
    struct.pack_into("<H", b, 4, n)
    struct.pack_into("<I", b, 8, int(blok["hz"]))
    struct.pack_into("<f", b, 12, float(blok["adim"]))
    struct.pack_into("<f", b, 16, float(blok["ofset"]))
    struct.pack_into("<I", b, 20, int(blok["tdiv_us"]))
    struct.pack_into("<H", b, 24, min(int(blok["tetik_idx"]), 0xFFFF))
    b[26] = int(blok["kip"]) & 0xFF
    b[27] = 1 if blok["tetiklendi"] else 0
    struct.pack_into("<I", b, 28, int(blok.get("sira", 0)) & 0xFFFFFFFF)
    return bytes(b) + struct.pack(f"<{n}H", *ornek)


class SkopCozucu:
    """`S2 … E` blogunu satir satir toplayan artimli cozucu.

    Hem canli akista (kopru) hem gunluk okumada (arsiv) ayni ornek
    kullaniliyor. `besle()` blok TAMAMLANINCA sozluk donduruyor, aksi
    halde None.

    ⚠ Blok icinde `D`/`K`/`*` satiri gorulebilir: olcum dongusu ile dokum
      ayni `Serial`i paylasiyor. Bunlar YOK SAYILIYOR ama SAYILIYOR
      (`atlanan`) — sessizce yutulsa, eksik bir dalga "tam" gorunurdu.
    """

    def __init__(self):
        self.sifirla()
        self.kirpilan = 0            # `E` gelmeden yeni `S2` ile kesilen

    def sifirla(self) -> None:
        self.baslik: dict | None = None
        self.ornek: list[int] = []
        self.olcum: str | None = None
        self.atlanan = 0

    # ── ic yardimcilar ───────────────────────────────────────────────
    @staticmethod
    def _baslik_coz(satir: str, ms: int) -> dict | None:
        """`S2 <adet> <Hz> <adim> <tetik> <tdiv_us> <kip> <tetik?> [ofset]`"""
        p = satir.split()
        if len(p) < 8:
            return None
        try:
            adet = int(p[1])
            if not 0 < adet <= SKOP_AZAMI_ORNEK:
                return None
            return {
                "ms": ms,
                "adet_bildirilen": adet,
                "hz": int(p[2]),
                "adim": float(p[3]),
                "tetik_idx": int(p[4]),
                "tdiv_us": int(p[5]),
                "kip": int(p[6]),
                "tetiklendi": p[7] == "1",
                # B19'un 9. alani. Eski kayitlarda YOK — 0 kabul ediliyor,
                # cunku o surumde ofset zaten sifirdi.
                "ofset": float(p[8]) if len(p) > 8 else 0.0,
            }
        except ValueError:
            return None

    @staticmethod
    def _ornek_coz(satir: str) -> list[int] | None:
        """Satir BASTAN SONA ham ADC kodu mu? Degilse None."""
        p = satir.split()
        if not p:
            return None
        try:
            d = [int(x) for x in p]
        except ValueError:
            return None
        if any(x < 0 or x > 0xFFFF for x in d):
            return None
        return d

    # ── genel yuzey ──────────────────────────────────────────────────
    def besle(self, satir: str, ms: int = 0) -> dict | None:
        satir = satir.strip()
        if not satir:
            return None

        if satir.startswith("S2 "):
            if self.baslik is not None:
                self.kirpilan += 1        # onceki blok `E` gormeden kesildi
            b = self._baslik_coz(satir, ms)
            self.sifirla()
            self.baslik = b
            return None

        if self.baslik is None:
            return None

        if satir == "E":
            blok = dict(self.baslik)
            blok["ornek"] = self.ornek
            blok["olcum"] = self.olcum
            blok["atlanan"] = self.atlanan
            blok["tam"] = len(self.ornek) == blok["adet_bildirilen"]
            self.sifirla()
            return blok

        if satir.startswith("M "):
            self.olcum = satir
            return None

        d = self._ornek_coz(satir)
        if d is None:
            self.atlanan += 1
            return None
        # Bozuk bir `S2` uzun bir sayi akisina denk gelirse bellek
        # buyumesin: BILDIRILEN ADET TAVAN. Tasan ornek SESSIZCE
        # atilmiyor, `atlanan`a yaziliyor — sessiz atilsaydi bozuk bir
        # dokum "tam" gorunurdu.
        yer = self.baslik["adet_bildirilen"] - len(self.ornek)
        if yer > 0:
            self.ornek.extend(d[:yer])
        self.atlanan += max(0, len(d) - max(yer, 0))
        return None


class Arsiv:
    """Eklemeli ham satir gunlugu. Acik dosya tutuyor, her satirda flush
    ETMIYOR — 5 Hz'te saniyede 5 fsync gereksiz asinma. Bunun yerine
    periyodik flush; cokme halinde en fazla son saniye kaybolur."""

    def __init__(self, dizin: str | Path, flush_sn: float = 2.0):
        self.dizin = Path(dizin)
        self.dizin.mkdir(parents=True, exist_ok=True)
        self.t0 = time.monotonic()
        self.flush_sn = flush_sn
        self._son_flush = self.t0
        self._dosya = None
        self._gun = None
        self.satir_adedi = 0

    def _akim_dosya(self):
        gun = time.strftime("%Y-%m-%d")
        if gun != self._gun:
            if self._dosya:
                self._dosya.close()
            yol = self.dizin / f"{gun}.satir"
            self._dosya = io.open(yol, "a", encoding="utf-8", newline="\n")
            self._gun = gun
        return self._dosya

    def yaz(self, satir: str) -> int:
        """Satiri gunluge ekle ve VURULAN ZAMAN DAMGASINI dondur.

        Damgayi dondurmesi onemli: canli skop cozucusu ayni damgayi
        kullaniyor, boylece canli yakalamanin kimligi (`gun`+`ms`) ile
        arsivden okunanin kimligi BIREBIR ayni oluyor. Cagiran taraf
        damgayi kendi hesaplasaydi iki kimlik birkac ms ayrisir ve
        "az once cektigim yakalama listede yok" olurdu.
        """
        if not satir:
            return -1
        d = self._akim_dosya()
        ms = int((time.monotonic() - self.t0) * 1000)
        d.write(f"{ms}\t{satir}\n")
        self.satir_adedi += 1
        simdi = time.monotonic()
        if simdi - self._son_flush >= self.flush_sn:
            d.flush()
            os.fsync(d.fileno())
            self._son_flush = simdi
        return ms

    def flush(self) -> None:
        """Bekleyen satirlari diske indir.

        Periyodik flush 2 s'de bir; okuyucu (skop listesi) araya girdiginde
        son yakalama HENUZ DISKTE OLMAYABILIR ve "az once cektim, listede
        yok" olurdu. Okuma yollari once bunu cagiriyor.
        """
        if self._dosya:
            self._dosya.flush()
            self._son_flush = time.monotonic()

    def kapat(self) -> None:
        if self._dosya:
            self._dosya.flush()
            self._dosya.close()
            self._dosya = None
        # 🔴 `_gun`u da SIFIRLA. Yoksa kapatilmis arsive gelen ilk yazma
        #    `_akim_dosya()`den None aliyordu ("bugun zaten acik" sanip)
        #    ve `yaz()` AttributeError atiyordu. Bu istisna yukari-akis
        #    ipligini oldurur, kopru ise ayakta gorunmeye devam ederdi:
        #    arsiv YOK, SSE YOK, hata mesaji YOK. Dosya `a` kipinde
        #    aciliyor, yeniden acmak hicbir sey kaybettirmiyor.
        self._gun = None

    # ── okuma / turetme ───────────────────────────────────────────────
    def gunler(self) -> list[str]:
        return sorted(p.stem for p in self.dizin.glob("*.satir"))

    def ham_satirlar(self, gun: str | None = None):
        """Kaydedilen HAM satirlari sirayla dondur — zaman damgasi soyulmus.

        Bu, kartin urettiginin BIREBIR aynisi olmali; `test_kopru.py`
        bunu bayt-bayt sinar. Sinanabilmesi bu fonksiyonun var olmasina
        bagli: rolenin seffafligini kanitlayan sey bu.
        """
        gun = gun or (self.gunler() or [None])[-1]
        if gun is None:
            return
        yol = self.dizin / f"{gun}.satir"
        if not yol.exists():
            return
        with io.open(yol, encoding="utf-8") as d:
            for sat in d:
                sat = sat.rstrip("\n")
                if not sat:
                    continue
                parca = sat.split("\t", 1)
                yield parca[1] if len(parca) == 2 else sat

    def zamanli_satirlar(self, gun: str | None = None):
        """(ms, ham_satir) ciftleri. CSV zaman damgasini buradan aliyor;
        `ham_satirlar` bilerek YALNIZ ham satiri veriyor cunku onun isi
        rolenin bayt-seffafligini kanitlamak."""
        gun = gun or (self.gunler() or [None])[-1]
        if gun is None:
            return
        yol = self.dizin / f"{gun}.satir"
        if not yol.exists():
            return
        with io.open(yol, encoding="utf-8") as d:
            for sat in d:
                sat = sat.rstrip("\n")
                if not sat:
                    continue
                parca = sat.split("\t", 1)
                if len(parca) == 2 and parca[0].isdigit():
                    yield int(parca[0]), parca[1]
                else:
                    yield 0, sat

    def csv_uret(self, hedef: str | Path, gun: str | None = None) -> int:
        """`D` satirlarindan Excel-TR uyumlu CSV uret.

        ⚠ CSV ayri TUTULMUYOR, gunlukten URETILIYOR. Ayri tutulsaydi iki
          temsil ayrisirdi — bu projenin tekrarlayan hatasi.
        """
        hedef = Path(hedef)
        n = 0
        with io.open(hedef, "w", encoding="utf-8-sig", newline="") as c:
            c.write(";".join(D_BASLIK) + "\r\n")
            for ms, ham in self.zamanli_satirlar(gun):
                if not ham.startswith("D "):
                    continue
                p = ham.split()
                if len(p) < 9:
                    continue
                # Turkce Excel ondalik ayraci VIRGUL bekliyor.
                alan = [x.replace(".", ",") for x in p[1:9]]
                c.write(";".join([str(ms)] + alan) + "\r\n")
                n += 1
        return n

    # ── skop yakalamalari (B35) ──────────────────────────────────────
    def skop_bloklari(self, gun: str | None = None):
        """Gunlukteki `S2 … E` bloklarini sirayla dondur.

        Dosyaya AYRICA yazilmiyorlar; `csv_uret` gibi gunlukten
        turetiliyorlar. Bu sayede "geriye donuk kayit" ozelligi arsivin
        bayt-seffafligini BOZMADAN geliyor.
        """
        gun = gun or (self.gunler() or [None])[-1]
        if gun is None:
            return
        c = SkopCozucu()
        for ms, ham in self.zamanli_satirlar(gun):
            blok = c.besle(ham, ms)
            if blok is not None:
                blok["gun"] = gun
                yield blok

    def skop_ozet(self, gun: str | None = None) -> list[dict]:
        """Listeleme icin HAFIF kayitlar — `ornek` dizisi TASINMIYOR.

        4000 ornekli bir yakalama JSON'da ~20 KB eder; liste ucu her
        satirda bunu tasisaydi 50 kayitlik bir gun 1 MB olurdu.
        """
        ozet = []
        for b in self.skop_bloklari(gun):
            ozet.append({
                "gun": b["gun"], "ms": b["ms"],
                "adet": len(b["ornek"]), "adet_bildirilen": b["adet_bildirilen"],
                "hz": b["hz"], "tdiv_us": b["tdiv_us"],
                "tetiklendi": b["tetiklendi"], "tam": b["tam"],
                "olcum": b["olcum"] or "",
            })
        return ozet

    def skop_bul(self, gun: str, ms: int) -> dict | None:
        """Tek bir yakalamayi kimliginden (gun + ms) getir."""
        for b in self.skop_bloklari(gun):
            if b["ms"] == ms:
                return b
        return None
