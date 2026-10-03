# -*- coding: utf-8 -*-
"""B72 — KARTIN KAYITLARINI ESITLE (PC tarafi; PC uygulamasi da kullanacak).

    python kayit_esitle.py --http olcum.local --dizin kayitlar/ --port COM6
    python kayit_esitle.py --http olcum.local --dizin kayitlar/     # HTTP onayi

Kart asil kaydi tutar (tasarim §5). Bu istemci eksik kayitlari
`/kayit/veri`'den ceker, CRC'lerini dogrular, kartin baytlarini diske AYNEN
ekler, fsync eder ve ANCAK ONDAN SONRA "N'e kadar aldim" onayi yollar. Kartin
akilli temizligi yalniz bu onaylara bakar: onay erken gitseydi kartta
silinen veri diskte olmayabilirdi.

Diskte:
  kayitlar.kyt   kartin ham kayit akisi (kayit_bicim.akis_coz ile okunur)
  durum.json     {son_sira, bayt, onaylanan, kimlik} — atomik yazilir
  esitle.kilit   ayni dizine iki esitleme yazmasin (isletim sistemi kilidi)

Dayaniklilik (1A-2 son inceleme O1/O2 + minor):
  * Kartin AKIS KIMLIGI (X-Kayit-Kimlik) degisirse DUR: NVS/flas kaybinda
    kart numarayi yeniden baslatir; eski akisa eklemek eslitlenmemis veriyi
    sessizce kaybettirirdi. Yeni kart/akis -> yeni dizin.
  * Kartin sirasi (X-Sonraki-Sira) bizim son siramizin GERISINDEYSE DUR.
  * Bos yanit ama kartta daha yeni sira varsa (bicimlenmis ya da yarim
    yazilmis sira) HATA degil ama 'bitti' de degil: uyari + bekleyen sayisi.
  * Onay yalniz diske yazildiktan sonra; "onaylandi" ise yalniz kart X-Onay
    ile DOGRULAYINCA yazilir, dogrulanmazsa yeniden yollanir (kartta onay
    kaybolabilir; kaybolursa dolu kart takili kalirdi).
  * Cokme: durum.json'dan uzun dosyanin GECERLI kayitlari ileri sarilir
    (fsync'li veri + kaybolan yeniden adlandirma), yarim kuyruk kirpilir.

Onay yollari:
  * seri (`Go<sira>`, USB — parola gerekmez)
  * HTTP (`/komut`: oturum jetonu /akis'ten + Basic Auth; parola ORTAM
    DEGISKENINDEN, depoya ASLA yazilmaz)
Yalniz standart kutuphane.
"""
from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kayit_bicim as KB                                   # noqa: E402
import imza as IM                                          # noqa: E402  (1D)

DOSYA = "kayitlar.kyt"

# Windows PAYLASIM IHLALI: hedefi o an acik tutan biri (dizinleyici, virus tarayici, durumu okuyan
# baska surec) varken os.replace PermissionError [WinError 5] verir. 4 iscili mutasyon kosusunda 20
# kosunun 2'sinde test bu yuzden coktu (HIZ inceleme 2026-10-03); gercek kopru de yasayabilir.
DEGISTIR_DENEME = 8


def atomik_degistir(g, p, deneme: int = DEGISTIR_DENEME, uyu=time.sleep) -> None:
    """os.replace(g, p); paylasim ihlalinde (PermissionError) kisa araliklarla yeniden dener."""
    for i in range(deneme):
        try:
            os.replace(g, p)
            return
        except PermissionError:
            if i == deneme - 1:
                raise
            uyu(0.05 * (i + 1))
DURUM = "durum.json"
KILIT = "esitle.kilit"
KAL_DOSYA = "kalibrasyon.json"   # 1B: kartin kalibrasyon gecmisi (/kal/liste)
EN_AZ_BAYT = 1100      # en buyuk kayit 16 + 1012 = 1028 B; kucuk parca hic veri getiremez


class Kilit:
    """Ayni dizine iki esitleme ayni anda yazmasin. Isletim sistemi kilidi:
    surec olurse (cokme) kilit KENDILIGINDEN kalkar — elle silinecek kalinti
    birakmaz."""

    def __init__(self, dizin: Path):
        self.yol = Path(dizin) / KILIT
        self.f = None

    def __enter__(self):
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.yol, "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            self.f = None
            raise RuntimeError(f"{self.yol.parent}: baska bir esitleme suruyor")
        return self

    def __exit__(self, *a):
        if not self.f:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.f.close()
            self.f = None


class Esitleyici:
    """4C (kopru/arka_esitle.py) ek parametreleri — komut satirinda hepsi eski davranista:
      istek        (yontem, yol, argumanlar) -> yanit: imzali istegi CAGIRAN yapar (kopru: WifiKart'in
                   AYNI Cihaz nesnesi + sayac kilidi; ayri bir Cihaz sayaci yaristirirdi)
      parca_arasi  iki /kayit/veri isteginin BASLANGICLARI arasi en kisa sure (s; istek hizi tavani) —
                   kartin seri web cekirdegi canli akisa ve oteki istemcilere de hizmet etsin; eksik
                   kalan `uyu` ile beklenir (istek zaten bu kadar surduyse bekleme yok)
      durdu        () -> bool: parcalar ARASINDA bakilir; True ise (kopru kapaniyor) yazilan kalici
                   kalir, tur biter (onay dogrulamasi / kalibrasyon atlanir)
      onay_parca   onay N parcada bir (+ tur sonunda): her `Go` kartin akisina bir satir basar"""

    def __init__(self, taban_url: str, dizin, onay=None, bayt: int = 8192,
                 zaman_asimi: float = 10.0, onay_bekle: float = 0.3, cihaz=None,
                 istek=None, parca_arasi: float = 0.0, uyu=time.sleep, durdu=None,
                 onay_parca: int = 1):
        self.cihaz = cihaz              # 1D: imza.Cihaz -> butun istekler imzali
        self.istek = istek
        self.taban = taban_url.rstrip("/")
        self.dizin = Path(dizin)
        self.dizin.mkdir(parents=True, exist_ok=True)
        self.onay = onay
        self.bayt = max(bayt, EN_AZ_BAYT)
        self.zaman_asimi = zaman_asimi
        self.onay_bekle = onay_bekle
        self.parca_arasi = parca_arasi
        self.uyu = uyu
        self.durdu = durdu
        self.onay_parca = max(1, int(onay_parca))

    # ── durum ──
    def _durum(self) -> dict:
        p = self.dizin / DURUM
        d = {"son_sira": 0, "bayt": 0, "onaylanan": 0, "kimlik": None}
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
        atomik_degistir(g, p)

    def _hazirla(self, d: dict) -> None:
        """Durumdan UZUN dosya: durum yazilmadan kesilmis ekleme. GECERLI ve
        artan kayitlari ileri sar (fsync'li veri kaybolmasin), gerisini kirp."""
        p = self.dizin / DOSYA
        boy = p.stat().st_size if p.exists() else 0
        if boy < d["bayt"]:
            raise ValueError(f"{p} durumdan kisa ({boy} < {d['bayt']} B) — elle incele")
        if boy == d["bayt"]:
            return
        kuyruk = p.read_bytes()[d["bayt"]:]
        kayitlar, _ = KB.akis_onek(kuyruk)
        son, gecerli = d["son_sira"], 0
        for k in kayitlar:
            # YALNIZ kesintisiz dizi: arada atlanan sira varsa (tuhaf kuyruk)
            # ileri sarma durur, kalan yeniden CEKILIR — atlanan hic kaybolmaz
            if k.sira != son + 1:
                break
            son = k.sira
            gecerli += KB.toplam_bayt(len(k.yuk))
        with open(p, "r+b") as f:
            f.truncate(d["bayt"] + gecerli)
            f.flush()
            os.fsync(f.fileno())
        if gecerli:
            d["son_sira"] = son
            d["bayt"] += gecerli
            self._durum_yaz(d)

    # ── ag ──
    def _ac(self, yol: str, argumanlar=()):
        """GET: eslesmisse imzali (1D, kopru/imza.py), degilse bugunku acik yol."""
        if self.istek is not None:
            return self.istek("GET", yol, list(argumanlar))
        if self.cihaz is not None:
            return IM.ac(self.cihaz, self.taban, "GET", yol, list(argumanlar),
                         zaman_asimi=self.zaman_asimi)
        q = "&".join(f"{a}={d}" for a, d in argumanlar)
        return urllib.request.urlopen(self.taban + yol + (f"?{q}" if q else ""),
                                      timeout=self.zaman_asimi)

    def _getir(self, sira: int):
        with self._ac("/kayit/veri", [("sira", str(sira)), ("bayt", str(self.bayt))]) as y:
            return y.read(), y.headers

    @staticmethod
    def _sayi(basliklar, ad: str):
        v = basliklar.get(ad)
        return int(v) if v not in (None, "") else None

    def _kimlik_denetle(self, d: dict, basliklar) -> None:
        k = self._sayi(basliklar, "X-Kayit-Kimlik")
        if k is None:
            return                                  # eski firmware: baslik yok
        if d.get("kimlik") is None:
            d["kimlik"] = k
            self._durum_yaz(d)
        elif d["kimlik"] != k:
            raise ValueError(f"kartin kayit AKISI degismis (kimlik {d['kimlik']} -> {k}): "
                             "kart sifirlanmis ya da baska kart. Bu dizine EKLENMEZ — "
                             "yeni bir dizine esitle")

    def _ekle(self, govde: bytes) -> None:
        with open(self.dizin / DOSYA, "ab") as f:
            f.write(govde)
            f.flush()
            os.fsync(f.fileno())

    def _onay_dogrula(self, d: dict, onay_x) -> bool:
        """Kart onayi ALDI MI (X-Onay)? Almadiysa yeniden yolla, birkac kez."""
        if d["onaylanan"] >= d["son_sira"]:
            return True
        if not self.onay:
            return False
        for _ in range(4):
            if onay_x is not None and onay_x >= d["son_sira"]:
                d["onaylanan"] = d["son_sira"]
                self._durum_yaz(d)
                return True
            self.onay(d["son_sira"])
            time.sleep(self.onay_bekle)             # kart onayi bir sonraki turda uygular
            _, bas = self._getir(d["son_sira"] + 1)
            onay_x = self._sayi(bas, "X-Onay")
        return False

    def esitle(self, azami_tur: int = 100000) -> dict:
        with Kilit(self.dizin):
            return self._esitle(azami_tur)

    def _esitle(self, azami_tur: int) -> dict:
        d = self._durum()
        self._hazirla(d)
        yeni, bosluk, sonuc = 0, [], {}
        onay_x = None
        parca = 0
        onceki = None
        for _ in range(azami_tur):
            if onceki is not None and self.parca_arasi:
                kalan = self.parca_arasi - (time.monotonic() - onceki)
                if kalan > 0:
                    self.uyu(kalan)            # 4C: istek hizi tavani (tek istek, kart bogulmasin)
            if self.durdu is not None and self.durdu():
                return {"yeni_kayit": yeni, "son_sira": d["son_sira"], "bosluk": bosluk,
                        "onay_dogrulandi": d["onaylanan"] >= d["son_sira"], "kalibrasyon": None,
                        "durduruldu": True}
            son = d["son_sira"]
            onceki = time.monotonic()
            govde, bas = self._getir(son + 1)
            self._kimlik_denetle(d, bas)
            onay_x = self._sayi(bas, "X-Onay")
            sonraki = self._sayi(bas, "X-Sonraki-Sira")
            if sonraki is not None and sonraki - 1 < son:
                raise ValueError(f"kartin sirasi GERI gitti (kartta son {sonraki - 1}, "
                                 f"bizde {son}): kart sifirlanmis. Bu dizine EKLENMEZ")
            if not govde:
                if sonraki is not None and sonraki - 1 > son:
                    sonuc = {"bekleyen": sonraki - 1 - son,
                             "uyari": "kartta daha yeni sira var ama veri gelmedi "
                                      "(bicimlenmis ya da yarim yazilmis olabilir); "
                                      "yeni kayit gelince bosluk olarak gecilir"}
                break
            kayitlar = KB.akis_coz(govde)      # CRC: bozuk yanit diske YAZILMAZ, onaylanmaz
            siralar = [k.sira for k in kayitlar]
            if siralar[0] <= son or siralar != sorted(set(siralar)):
                raise ValueError(f"kart sirasi geri gitti ya da tekrar etti: {siralar[:3]} (son {son})")
            if siralar[0] > son + 1:
                bosluk.append((son + 1, siralar[0]))
            self._ekle(govde)                  # once KALICI yaz (fsync)
            d["son_sira"] = siralar[-1]
            d["bayt"] += len(govde)
            self._durum_yaz(d)
            yeni += len(kayitlar)
            parca += 1
            if self.onay and parca % self.onay_parca == 0:
                self.onay(d["son_sira"])       # ancak diske yazildiktan SONRA (yer acilsin)
        dogru = self._onay_dogrula(d, onay_x)
        return {"yeni_kayit": yeni, "son_sira": d["son_sira"], "bosluk": bosluk,
                "onay_dogrulandi": dogru, **self._kal_esitle(), **sonuc}

    def _kal_esitle(self) -> dict:
        """1B: kalibrasyon gecmisini kalibrasyon.json'a ATOMIK yaz. Kayitlar
        kalibrasyon NUMARASINI tasiyor (BASLA surum 2); degerler burada.
        Veri esitlemesinden SONRA calisir ve onu HICBIR hatayla bozmaz: eski
        firmware (404) sessiz; bozuk/yarim yanit, zaman asimi -> hata metni,
        eski dosya yerinde. Donus: {"kalibrasyon": adet | None,
        ["kalibrasyon_hata"], ["kalibrasyon_arsiv"]}."""
        try:
            with self._ac("/kal/liste") as y:
                # eski firmware notta gecersiz UTF-8 birakabiliyordu (cp1254 'ş')
                veri = json.loads(y.read().decode("utf-8", errors="replace"))
            if not isinstance(veri, dict) or not isinstance(veri.get("kayitlar"), list):
                raise ValueError("beklenmeyen bicim")
        except urllib.error.HTTPError as h:
            if h.code in (404, 503):
                return {"kalibrasyon": None}
            return {"kalibrasyon": None, "kalibrasyon_hata": f"HTTP {h.code}"}
        except (OSError, http.client.HTTPException, ValueError) as h:
            return {"kalibrasyon": None, "kalibrasyon_hata": f"{type(h).__name__}: {h}"}
        p = self.dizin / KAL_DOSYA
        sonuc = {"kalibrasyon": veri.get("adet")}
        eski, okunamadi = None, False
        if p.exists():
            try:
                eski = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                okunamadi = True                   # okunamayan dosya da korunur
        bozuk = self._kal_bozuk_birlestir(veri, eski)
        if bozuk:
            sonuc["kalibrasyon_bozuk"] = bozuk
        if p.exists() and (okunamadi or self._kal_cakisir(eski, veri)):
            sonuc["kalibrasyon_arsiv"] = self._kal_arsivle(p)
        g = p.with_suffix(".tmp")
        with open(g, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        atomik_degistir(g, p)
        return sonuc

    @staticmethod
    def _kal_bozuk_birlestir(veri: dict, eski) -> list:
        """Y6 (1B inceleme M2): kartin OKUYAMADIGI kayit {"no", "bozuk": true} gelir.
        PC'de saglam kopyasi varsa o KALIR ("kartta_bozuk": true) — kart bozdu diye PC
        iyi kopyayi kaybetmez; yoksa bozuk isaretiyle yazilir, eksik gecmis TAM sanilmaz.
        Donus: kartta bozuk numaralar."""
        try:
            saglam = {k["no"]: k for k in eski.get("kayitlar", []) if not k.get("bozuk")}
        except (AttributeError, KeyError, TypeError):
            saglam = {}
        bozuk = []
        for i, k in enumerate(veri["kayitlar"]):
            if isinstance(k, dict) and k.get("bozuk"):
                bozuk.append(k.get("no"))
                if k.get("no") in saglam:
                    iyi = {a: v for a, v in saglam[k["no"]].items() if a != "kartta_bozuk"}
                    veri["kayitlar"][i] = {**iyi, "kartta_bozuk": True}
        return bozuk

    @staticmethod
    def _kal_cakisir(eski, yeni: dict) -> bool:
        """Kartin gecmisi PC'dekinden bir kaydi SILIYOR ya da DEGISTIRIYOR mu
        (NVS silindi, `adet` kayboldu, baska kart)? Not ve tur duzeltmesi
        olagan (`kn`/`kt`); numara, tarih, acilis ve degerler degismez."""
        def kimlik(k: dict) -> dict:
            return {a: v for a, v in k.items() if a not in ("not", "tur", "kartta_bozuk")}
        try:
            e = {k["no"]: kimlik(k) for k in eski.get("kayitlar", [])}
            y = {k["no"]: kimlik(k) for k in yeni["kayitlar"]}
        except (AttributeError, KeyError, TypeError):
            return True
        return any(no not in y or y[no] != v for no, v in e.items())

    def _kal_arsivle(self, p: Path) -> str:
        """Eski dosyanin zaman damgali KOPYASI (fsync'li) — asil dosya ancak
        bundan sonra ezilir."""
        ad = time.strftime("kalibrasyon-%Y%m%d-%H%M%S")
        hedef, n = self.dizin / f"{ad}.json", 1
        while hedef.exists():
            hedef, n = self.dizin / f"{ad}-{n}.json", n + 1
        with open(hedef, "wb") as f:
            f.write(p.read_bytes())
            f.flush()
            os.fsync(f.fileno())
        return hedef.name


def seri_onay(kart):
    """USB seri uzerinden `Go<sira>` (kart_baglanti.SeriKart)."""
    def onayla(sira: int) -> None:
        kart.yaz(f"Go{sira}\n")
    return onayla


def imzali_onay(cihaz, taban_url: str, zaman_asimi: float = 5.0):
    """1D: `/komut` uzerinden imzali `Go<sira>` — jeton ve parola GEREKMEZ."""
    taban = taban_url.rstrip("/")

    def onayla(sira: int) -> None:
        with IM.ac(cihaz, taban, "POST", "/komut", [], f"Go{sira}".encode("ascii"),
                   zaman_asimi=zaman_asimi) as y:
            y.read()
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


def _cihaz_sec(taban: str, dosya, dizin):
    """1D: --cihaz verilmisse o; yoksa --cihaz-dizin'de KARTIN kimligine uyan dosya.
    Eski firmware (eslestirme ucu yok) ya da eslesmemis: None (bugunku yol)."""
    if dosya:
        return IM.Cihaz.yukle(dosya)
    try:
        kimlik = IM.bilgi(taban, 5.0)["kimlik"]
    except Exception:                                    # noqa: BLE001
        return None
    p = Path(dizin) / f"{kimlik}.json"
    return IM.Cihaz.yukle(p) if p.exists() else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kartin kayitlarini esitle")
    ap.add_argument("--http", default="olcum.local")
    ap.add_argument("--dizin", required=True)
    ap.add_argument("--port", help="USB seri onay (orn. COM6)")
    ap.add_argument("--parola-ortam", default="OLCUM_WEB_PAROLA",
                    help="HTTP onayi icin web parolasini tutan ortam degiskeni")
    ap.add_argument("--cihaz", help="1D: eslesmis cihaz dosyasi (imza.py esles)")
    ap.add_argument("--cihaz-dizin", default=None,
                    help="1D: --cihaz yoksa kartin kimligine uyan dosya burada aranir "
                         "(4B varsayilan: pc_ayar.cihaz_dizini — LOCALAPPDATA altinda olcum-karti/cihaz)")
    a = ap.parse_args(argv)
    taban = a.http if a.http.startswith("http") else f"http://{a.http}"
    if a.cihaz_dizin is None:
        gocen = IM.goc_et()                      # 4B (PC5): eski kopru/.cihaz -> yeni yer
        if gocen:
            print(IM.goc_mesaji(gocen))
    cihaz = _cihaz_sec(taban, a.cihaz, a.cihaz_dizin or IM.varsayilan_dizin())
    kart = None
    if a.port:
        import kart_baglanti
        kart = kart_baglanti.SeriKart(a.port)
        kart.ac()
        onay = seri_onay(kart)
    elif cihaz is not None:
        onay = imzali_onay(cihaz, taban)
    else:
        onay = http_onay(taban, os.environ.get(a.parola_ortam))
    if cihaz is not None:
        print(f"imzali (cihaz {cihaz.n}, {cihaz.ad})")
    try:
        r = Esitleyici(taban, a.dizin, onay, cihaz=cihaz).esitle()
    finally:
        if kart:
            kart.kapat()
    print(f"yeni {r['yeni_kayit']} kayit, son sira {r['son_sira']}, bosluk {r['bosluk']}, "
          f"onay {'dogrulandi' if r['onay_dogrulandi'] else 'DOGRULANAMADI'}, "
          + (f"kalibrasyon ALINAMADI ({r['kalibrasyon_hata']}) — eski {KAL_DOSYA} yerinde"
             if r.get("kalibrasyon_hata") else
             f"kalibrasyon {r['kalibrasyon'] if r['kalibrasyon'] is not None else 'yok (eski firmware)'}")
          + (f", kartin kalibrasyon gecmisi DEGISMIS: eskisi {r['kalibrasyon_arsiv']}"
             if r.get("kalibrasyon_arsiv") else "")
          + (f", UYARI: {r['uyari']}" if r.get("uyari") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
