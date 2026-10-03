# -*- coding: utf-8 -*-
"""4C — ARKA PLAN DISK ARSIVI: kopru sureci kartin kayitlarini WiFi'den diske esitler.

Tasarim: tasarim/2026-10-03-alt-proje-4-pc.md PC5 / PC6 / PC9 + "4C uygulama kararlari";
ust tasarim §5 (kucuk parcalar, ONAY YALNIZ KALICI YAZIMDAN SONRA, kartin baytlari AYNEN).

    pc.py: ArkaEsitleme(wifi, kopru.yayinla, pc_ayar.arsiv_dizini(), onay=..., tetik=...)

Bir TUR:
  1. Kart dogrulanir (`WifiKart.dogrula`: acik /eslestir/bilgi, kimlik, eslesmis cihaz). Butun
     imzali istekler canli akisla AYNI Cihaz nesnesini ve AYNI sayac kilidini kullanir
     (`WifiKart.imzali_ac`): iki nesne ayni milisaniyede ayni sayaci uretir, kart ikincisini
     tekrar diye (401) reddeder; araya giren istek sayaci 64 ms'lik pencerenin otesine atarsa
     yoldaki eski imzali istek reddedilir.
  2. Imzali /kayit/liste: kartin kayit AKIS kimligi (bicimlenince / sifirlaninca degisir),
     sonraki sira, oturumlar.
  3. `kayit_esitle.Esitleyici` -> <arsiv>/<kart kimligi>/akis-<akis kimligi>/ (kayitlar.kyt,
     durum.json, kalibrasyon.json). Parca <= PARCA_BAYT (kartin tavani 8192), iki parca isteginin
     baslangici arasi en az PARCA_ARASI_SN; CRC diske yazmadan once, fsync, atomik durum. Onay (`Go<sira>`, imzali)
     ANCAK kalici yazimdan SONRA: ONAY_PARCA parcada bir + tur sonunda (kart X-Onay ile
     dogrular). Akis kimligi degisince YENI alt dizin — iki akis asla karismaz.
  4. Durum satiri `* esitleme: ...` (hata/atlama `! esitleme: ...`) kopru uzerinden
     TARAYICILARA; .satir arsivine GIRMEZ (yalniz Kopru.dongu'nun okudugu kart satirlari
     arsivlenir). Yeni kayit yokken sessiz.

Zamanlama: ilk tur hemen; her yukari-akis (yeniden) baglantisinda (`tetik` degisince); sonra
ARALIK_SN'de bir. Hata: HATA_TABAN_SN'den 2 katlanarak HATA_AZAMI_SN'ye. Her durumda iki tur
BASLANGICI arasi en az TABAN_SN — yeniden baglanti firtinasi karti dovemez. Tek tur = tek
istek dizisi (es zamanli istek yok).

Kayit verisinin seri (USB) yolu YOK (PC6): kart yalniz USB'den erisilebiliyorsa tur ATLANIR ve
soylenir (USB seri dokumu 4C-2, ERTELENDI).

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import http.client
import json
import sys
import threading
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imza as IM                                         # noqa: E402
import kart_wifi as KW                                    # noqa: E402
import kayit_esitle as KE                                 # noqa: E402

ARALIK_SN = 120.0        # varsayilan aralik (ayar / --esitleme-aralik)
ARALIK_EN_AZ = 30.0      # verilebilecek en kisa aralik
TABAN_SN = 10.0          # iki tur BASLANGICI arasi mutlak alt sinir (firtina dahil)
HATA_TABAN_SN = 15.0     # ilk hatadan sonra; her ardisik hatada 2 kat
HATA_AZAMI_SN = 600.0
PARCA_BAYT = 8192        # kartin /kayit/veri tavani (KAYIT_VERI_AZAMI)
PARCA_ARASI_SN = 0.1     # iki parca isteginin baslangici arasi EN AZ (<= 10 istek/s, <= 80 KB/s).
#                          Gercek kartta olculdu: canli akis bunsuz da aksamiyor; bedeli yalniz
#                          buyuk esitlemede (1.27 MB: ~20 -> ~29 s). Gerekce: spec 4C-3
ONAY_PARCA = 64          # uzun esitlemede ~512 KB'de bir onay (+ tur sonunda)
YOKLA_SN = 0.5           # dongunun tetik / durdurma yoklama adimi


def hata_beklemesi(n: int) -> float:
    """n. ardisik hatadan sonra bekleme: 15, 30, 60, 120, 240, 480, 600, 600 ... s."""
    return min(HATA_AZAMI_SN, HATA_TABAN_SN * (2 ** min(max(n, 1) - 1, 16)))


def _hata_metni(e: BaseException) -> str:
    if isinstance(e, urllib.error.HTTPError):
        try:
            govde = e.read(200).decode("utf-8", "replace").strip()
        except Exception:                                   # noqa: BLE001
            govde = ""
        finally:
            e.close()
        if e.code == 401:
            return ("kart imzayi reddetti (HTTP 401) — cihaz kartta silinmis olabilir; "
                    "`python kopru/imza.py esles`")
        return f"kart HTTP {e.code}" + (f" ({govde})" if govde else "")
    if isinstance(e, urllib.error.URLError):
        return f"karta ulasilamadi ({e.reason})"
    if isinstance(e, (OSError, http.client.HTTPException)):
        return f"karta ulasilamadi ({type(e).__name__}: {e})"
    return str(e) or type(e).__name__


class ArkaEsitleme:
    """Kopru surecindeki esitleme dongusu (tek iplik). `tur()` tek basina da cagrilabilir."""

    def __init__(self, wifi, yayinla, arsiv_kok, onay: bool = True, aralik: float = ARALIK_SN,
                 tetik=None, usb_etkin=None, saat=time.monotonic, bekle=None, duvar=time.time,
                 parca_arasi: float = PARCA_ARASI_SN, zaman_asimi: float = 10.0):
        self.wifi = wifi
        self.yayinla = yayinla
        self.arsiv_kok = Path(arsiv_kok)
        self.onay = bool(onay)
        self.aralik = max(ARALIK_EN_AZ, float(aralik))
        self._tetik = tetik or (lambda: 0)
        self._usb_etkin = usb_etkin or (lambda: False)
        self._saat = saat
        self._bekle_islev = bekle
        self._duvar = duvar
        self.parca_arasi = parca_arasi
        self.zaman_asimi = zaman_asimi
        self._dur = threading.Event()
        self._is: threading.Thread | None = None
        self._kilit = threading.Lock()
        self._hata_n = 0
        self._son_hata: str | None = None
        self._son_no = None
        self._son_baslangic: float | None = None
        self._sonraki: float | None = None
        self._d = {"etkin": True, "onay": self.onay, "aralik_s": self.aralik, "taban_s": TABAN_SN,
                   "parca_bayt": PARCA_BAYT, "sonuc": "bekliyor", "mesaj": "", "son_deneme": None,
                   "son_basari": None, "yeni_kayit": 0, "toplam_yeni": 0, "son_sira": None,
                   "kart_son_sira": None, "oturum": None, "bayt": None, "onay_gitti": False,
                   "onay_dogrulandi": False, "arsiv": None, "kart": None, "hata_sayisi": 0}

    # ── dis yuzey ────────────────────────────────────────────────────
    def baslat(self) -> None:
        if self._is is not None and self._is.is_alive():
            return
        self._dur.clear()
        self._is = threading.Thread(target=self._dongu, name="kopru-esitleme", daemon=True)
        self._is.start()

    def durdur(self, bekle: float = 5.0) -> None:
        self._dur.set()
        if self._is is not None and self._is is not threading.current_thread():
            self._is.join(bekle)
        self._is = None

    def durum(self) -> dict:
        """Kopru `/esitleme/durum` icin: mutlak yol YOK (arsiv adi veri dizinine gorelidir)."""
        with self._kilit:
            d = dict(self._d)
        if self._sonraki is not None and self._is is not None:
            d["sonraki_deneme_s"] = round(max(0.0, self._sonraki - self._saat()), 1)
        return d

    def tur(self) -> dict:
        """Bir esitleme turu. Hata ATMAZ: sonuc sozlugu ({sonuc: tamam|hata|atlandi|durduruldu,
        mesaj, ...}) dondurur, durumu gunceller, gerekiyorsa durum satiri yayinlar."""
        basla = self._duvar()
        try:
            r = self._tur()
        except Exception as e:                              # noqa: BLE001 — iplik olmesin
            r = {"sonuc": "hata", "mesaj": _hata_metni(e)}
        self._sonuc_isle(r, basla)
        return r

    # ── tur ──────────────────────────────────────────────────────────
    def _tur(self) -> dict:
        try:
            cihaz, kart_k, _ = self.wifi.dogrula()
        except KW.KartDogrulanamadi as e:
            if self._usb_etkin():
                return {"sonuc": "atlandi",
                        "mesaj": ("atlandi — kart yalniz USB'den erisilebilir; kayit verisi yalniz "
                                  "WiFi'den alinir (USB seri dokumu 4C-2, ertelendi): " + str(e))}
            return {"sonuc": "hata", "mesaj": f"kart WiFi'den dogrulanamadi — {e}"}

        def istek(yontem, yol, argumanlar=(), govde=b""):
            return self.wifi.imzali_ac(cihaz, yontem, yol, list(argumanlar), govde, self.zaman_asimi)

        with istek("GET", "/kayit/liste") as y:
            liste = json.loads(y.read().decode("utf-8", "replace"))
        akis = liste.get("kimlik") if isinstance(liste, dict) else None
        if isinstance(akis, bool) or not isinstance(akis, int) or akis < 0:
            raise ValueError("/kayit/liste kayit akis kimligi bicimsiz")
        kart_dizin = self.arsiv_kok / kart_k
        dizin = kart_dizin / f"akis-{akis}"
        notlar: list[str] = []
        if not dizin.exists() and kart_dizin.is_dir():
            eskiler = sorted(p.name for p in kart_dizin.glob("akis-*") if p.is_dir())
            if eskiler:
                notlar.append(f"kartin kayit akisi degisti ({', '.join(eskiler)} -> akis-{akis}: "
                              "bicimlendi ya da sifirlandi) — yeni arsiv dizini, eskisi yerinde")
        gonderilen: list[int] = []

        def onayla(sira: int) -> None:
            with istek("POST", "/komut", (), f"Go{sira}".encode("ascii")) as y:
                y.read()
            gonderilen.append(sira)

        es = KE.Esitleyici(self.wifi.taban, dizin, onayla if self.onay else None, bayt=PARCA_BAYT,
                           zaman_asimi=self.zaman_asimi, istek=istek, parca_arasi=self.parca_arasi,
                           uyu=self._bekle, durdu=self._dur.is_set, onay_parca=ONAY_PARCA)
        r = es.esitle()
        try:
            bayt = json.loads((dizin / KE.DURUM).read_text(encoding="utf-8")).get("bayt")
        except (OSError, ValueError):
            bayt = None
        sonraki = liste.get("sonraki")
        r.update(sonuc="durduruldu" if r.get("durduruldu") else "tamam", kart=kart_k, akis=akis,
                 arsiv=f"arsiv/{kart_k}/akis-{akis}", onay_gitti=bool(gonderilen), notlar=notlar,
                 kart_son_sira=sonraki - 1 if isinstance(sonraki, int) else None,
                 oturum=len(liste.get("oturumlar") or []), bayt=bayt)
        return r

    def _sonuc_isle(self, r: dict, basla: float) -> None:
        tamam = r["sonuc"] in ("tamam", "durduruldu")
        onceki = self._d["sonuc"]
        with self._kilit:
            self._d.update(son_deneme=basla, sonuc=r["sonuc"], mesaj=r.get("mesaj", ""))
            if tamam:
                self._d.update(son_basari=self._duvar(), hata_sayisi=0)
                for a in ("yeni_kayit", "son_sira", "kart_son_sira", "oturum", "bayt", "onay_gitti",
                          "arsiv", "kart"):
                    self._d[a] = r.get(a)
                self._d["onay_dogrulandi"] = bool(r.get("onay_dogrulandi"))
                self._d["toplam_yeni"] += r.get("yeni_kayit", 0)
            else:
                self._d["hata_sayisi"] += 1
        if not tamam:
            self._hata_n += 1
            if r["mesaj"] != self._son_hata:            # ayni sebep tekrar tekrar basilmaz
                self._son_hata = r["mesaj"]
                self._soyle(f"! esitleme: {r['mesaj']} — {hata_beklemesi(self._hata_n):.0f} s sonra "
                            "yeniden")
            return
        self._hata_n = 0
        self._son_hata = None
        yeni = r.get("yeni_kayit", 0)
        parcalar = []
        if yeni:
            parcalar.append(f"{yeni} yeni kayit, son sira {r['son_sira']}")
            if not self.onay:
                parcalar.append("onay gitmedi (onaysiz)")
            elif r.get("onay_gitti"):
                parcalar.append("onay gitti" + (" (kart dogruladi)" if r.get("onay_dogrulandi")
                                                else " ama kart DOGRULAMADI — sonraki turda yeniden"))
        elif onceki not in ("tamam", "bekliyor", "durduruldu"):
            parcalar.append(f"yeniden calisiyor — yeni kayit yok, son sira {r['son_sira']}")
        if r.get("bosluk"):
            parcalar.append("bosluk " + ", ".join(f"{a}-{b - 1}" for a, b in r["bosluk"])
                            + " (kartta temizlenmis)")
        if r.get("uyari"):
            parcalar.append(f"UYARI: {r['uyari']} ({r.get('bekleyen')} bekleyen)")
        if r.get("kalibrasyon_arsiv"):
            parcalar.append(f"kartin kalibrasyon gecmisi degismis — eskisi {r['kalibrasyon_arsiv']}")
        if r.get("kalibrasyon_hata"):
            parcalar.append(f"kalibrasyon gecmisi alinamadi ({r['kalibrasyon_hata']})")
        parcalar = list(r.get("notlar") or []) + parcalar
        if parcalar:
            self._soyle("* esitleme: " + "; ".join(parcalar))

    def _soyle(self, metin: str) -> None:
        try:
            self.yayinla(metin)
        except Exception:                                   # noqa: BLE001 — yayin esitlemeyi oldurmez
            pass

    # ── dongu ────────────────────────────────────────────────────────
    def _bekle(self, sn: float) -> None:
        if self._bekle_islev is not None:
            self._bekle_islev(sn)
        else:
            self._dur.wait(sn)

    def _dongu(self) -> None:
        self._sonraki = self._saat()                     # ilk tur hemen
        while not self._dur.is_set():
            simdi = self._saat()
            try:
                no = self._tetik()
            except Exception:                               # noqa: BLE001
                no = self._son_no
            yeni_baglanti = no != self._son_no
            taban_tamam = (self._son_baslangic is None
                           or simdi >= self._son_baslangic + TABAN_SN)
            if taban_tamam and (simdi >= self._sonraki or yeni_baglanti):
                self._son_no = no
                self._son_baslangic = simdi
                r = self.tur()
                if self._dur.is_set():
                    break
                ara = self.aralik if r["sonuc"] in ("tamam", "durduruldu") else hata_beklemesi(self._hata_n)
                self._sonraki = max(self._saat() + ara, self._son_baslangic + TABAN_SN)
                continue
            hedef = self._sonraki
            if yeni_baglanti and self._son_baslangic is not None:
                hedef = min(hedef, self._son_baslangic + TABAN_SN)
            self._bekle(min(YOKLA_SN, max(0.0, hedef - simdi)))
