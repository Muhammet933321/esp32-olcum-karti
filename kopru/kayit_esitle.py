# -*- coding: utf-8 -*-
"""B72 — KARTIN KAYITLARINI ESITLE (PC tarafi; PC uygulamasi da kullanacak).

    python kayit_esitle.py --http olcum.local --dizin kayitlar/ --port COM6
    python kayit_esitle.py --http olcum.local --dizin kayitlar/     # HTTP onayi

Kart asil kaydi tutar (tasarim §5). Bu istemci eksik kayitlari
`/kayit/veri`'den ceker, CRC'lerini dogrular, kartin baytlarini diske AYNEN
ekler, fsync eder ve ANCAK ONDAN SONRA "N'e kadar aldim" onayi yollar. Kartin
akilli temizligi yalniz bu onaylara bakar: onay erken gitseydi kartta
silinen veri diskte olmayabilirdi.

Diskte iki dosya:
  kayitlar.kyt   kartin ham kayit akisi (kayit_bicim.akis_coz ile okunur)
  durum.json     {son_sira, bayt, onaylanan} — atomik yazilir
Ekleme ile durum arasinda kesilirse (cokme) sonraki kosu dosyayi `bayt`a
kirpar: tekrar ya da yarim kayit kalmaz. Onay yollanamadan kesilirse
sonraki kosu onu yeniden yollar.

Onay yollari:
  * seri (`Go<sira>`, USB — parola gerekmez)
  * HTTP (`/komut`: oturum jetonu /akis'ten + Basic Auth; parola ORTAM
    DEGISKENINDEN, depoya ASLA yazilmaz)
Yalniz standart kutuphane.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kayit_bicim as KB                                   # noqa: E402

DOSYA = "kayitlar.kyt"
DURUM = "durum.json"


class Esitleyici:
    def __init__(self, taban_url: str, dizin, onay=None, bayt: int = 8192,
                 zaman_asimi: float = 10.0):
        self.taban = taban_url.rstrip("/")
        self.dizin = Path(dizin)
        self.dizin.mkdir(parents=True, exist_ok=True)
        self.onay = onay
        self.bayt = bayt
        self.zaman_asimi = zaman_asimi

    # ── durum ──
    def _durum(self) -> dict:
        p = self.dizin / DURUM
        d = {"son_sira": 0, "bayt": 0, "onaylanan": 0}
        if p.exists():
            d.update(json.loads(p.read_text(encoding="utf-8")))
        return d

    def son_sira(self) -> int:
        return self._durum()["son_sira"]

    def _durum_yaz(self, d: dict) -> None:
        p = self.dizin / DURUM
        g = p.with_suffix(".tmp")
        with open(g, "w", encoding="utf-8") as f:
            json.dump(d, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(g, p)

    def _hazirla(self, d: dict) -> None:
        """Durumdan uzun dosya = durum yazilmadan kesilen ekleme: kirp."""
        p = self.dizin / DOSYA
        boy = p.stat().st_size if p.exists() else 0
        if boy < d["bayt"]:
            raise ValueError(f"{p} durumdan kisa ({boy} < {d['bayt']} B) — elle incele")
        if boy > d["bayt"]:
            with open(p, "r+b") as f:
                f.truncate(d["bayt"])
                f.flush()
                os.fsync(f.fileno())

    # ── ag ──
    def _getir(self, sira: int) -> bytes:
        url = f"{self.taban}/kayit/veri?sira={sira}&bayt={self.bayt}"
        with urllib.request.urlopen(url, timeout=self.zaman_asimi) as y:
            return y.read()

    def _ekle(self, govde: bytes) -> None:
        with open(self.dizin / DOSYA, "ab") as f:
            f.write(govde)
            f.flush()
            os.fsync(f.fileno())

    def _onayla(self, d: dict) -> None:
        if self.onay and d["onaylanan"] < d["son_sira"]:
            self.onay(d["son_sira"])           # ancak diske yazildiktan SONRA
            d["onaylanan"] = d["son_sira"]
            self._durum_yaz(d)

    def esitle(self, azami_tur: int = 100000) -> dict:
        d = self._durum()
        self._hazirla(d)
        self._onayla(d)                        # onceki kosu onaydan once kesildiyse
        yeni, bosluk = 0, []
        for _ in range(azami_tur):
            son = d["son_sira"]
            govde = self._getir(son + 1)
            if not govde:
                break
            kayitlar = KB.akis_coz(govde)      # CRC: bozuk yanit diske YAZILMAZ, onaylanmaz
            siralar = [k.sira for k in kayitlar]
            if siralar[0] <= son or siralar != sorted(set(siralar)):
                raise ValueError(f"kart sirasi geri gitti ya da tekrar etti: "
                                 f"{siralar[:3]} (son {son})")
            if siralar[0] > son + 1:
                bosluk.append((son + 1, siralar[0]))
            self._ekle(govde)                  # once KALICI yaz (fsync)
            d["son_sira"] = siralar[-1]
            d["bayt"] += len(govde)
            self._durum_yaz(d)
            yeni += len(kayitlar)
            self._onayla(d)
        return {"yeni_kayit": yeni, "son_sira": d["son_sira"], "bosluk": bosluk}


def seri_onay(kart):
    """USB seri uzerinden `Go<sira>` (kart_baglanti.SeriKart)."""
    def onayla(sira: int) -> None:
        kart.yaz(f"Go{sira}\n")
    return onayla


def http_onay(taban_url: str, parola: str | None = None, zaman_asimi: float = 5.0):
    """`/komut` uzerinden `Go<sira>`: jeton /akis'in `kimlik` olayindan (bir
    kez alinir; kart yeniden baslayip 403 derse yenilenir)."""
    taban = taban_url.rstrip("/")
    bellek: dict = {"jeton": None}

    def jeton_al() -> str:
        with urllib.request.urlopen(f"{taban}/akis", timeout=zaman_asimi) as y:
            for _ in range(50):
                s = y.readline().decode("utf-8", "replace").strip()
                if s.startswith("data:") and "jeton" in s:
                    return json.loads(s[5:].strip())["jeton"]
        raise RuntimeError("oturum jetonu alinamadi")

    def gonder(sira: int) -> None:
        istek = urllib.request.Request(
            f"{taban}/komut", data=f"Go{sira}".encode("ascii"), method="POST",
            headers={"X-Olcum": "1", "X-Jeton": bellek["jeton"],
                     "Content-Type": "text/plain"})
        if parola:
            istek.add_header("Authorization", "Basic " + base64.b64encode(
                f"olcum:{parola}".encode()).decode("ascii"))
        urllib.request.urlopen(istek, timeout=zaman_asimi).read()

    def onayla(sira: int) -> None:
        if not bellek["jeton"]:
            bellek["jeton"] = jeton_al()
        try:
            gonder(sira)
        except urllib.error.HTTPError as h:
            if h.code != 403:
                raise
            bellek["jeton"] = jeton_al()
            gonder(sira)
    return onayla


def main() -> int:
    ap = argparse.ArgumentParser(description="Kartin kayitlarini esitle")
    ap.add_argument("--http", default="olcum.local")
    ap.add_argument("--dizin", required=True)
    ap.add_argument("--port", help="USB seri onay (orn. COM6)")
    ap.add_argument("--parola-ortam", default="OLCUM_WEB_PAROLA",
                    help="HTTP onayi icin web parolasini tutan ortam degiskeni")
    a = ap.parse_args()
    taban = a.http if a.http.startswith("http") else f"http://{a.http}"
    kart = None
    if a.port:
        import kart_baglanti
        kart = kart_baglanti.SeriKart(a.port)
        kart.ac()
        onay = seri_onay(kart)
    else:
        onay = http_onay(taban, os.environ.get(a.parola_ortam))
    try:
        r = Esitleyici(taban, a.dizin, onay).esitle()
    finally:
        if kart:
            kart.kapat()
    print(f"yeni {r['yeni_kayit']} kayit, son sira {r['son_sira']}, bosluk {r['bosluk']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
