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
"""
from __future__ import annotations

import io
import os
import time
from pathlib import Path

# `D` satirinin alanlari — firmware'deki snprintf bicimiyle AYNI SIRA.
D_BASLIK = ["ms_kopru", "volt", "amper", "watt", "joule", "wh",
            "kart_ms", "ornek", "menzil"]


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

    def yaz(self, satir: str) -> None:
        if not satir:
            return
        d = self._akim_dosya()
        ms = int((time.monotonic() - self.t0) * 1000)
        d.write(f"{ms}\t{satir}\n")
        self.satir_adedi += 1
        simdi = time.monotonic()
        if simdi - self._son_flush >= self.flush_sn:
            d.flush()
            os.fsync(d.fileno())
            self._son_flush = simdi

    def kapat(self) -> None:
        if self._dosya:
            self._dosya.flush()
            self._dosya.close()
            self._dosya = None

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
