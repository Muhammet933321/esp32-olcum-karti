# -*- coding: utf-8 -*-
"""4E — PC bildirimleri: kopru surecinde MQTT aboneligi + Windows bildirimi (yalniz stdlib).

Tasarim: tasarim/2026-10-03-alt-proje-4-pc.md PC13–PC16, PC18 + "4E uygulama kararlari";
ust tasarim §8 (bes olay, her biri ayri acilir/kapanir, yerel + MQTT'den gelen ayni olay TEK
bildirim, "karttan haber yok" yalniz kayit surerken ve kart donunce AYNI bildirim guncellenir,
"ev interneti koptu"); 1E tasarimi (konular, OKB1 zarfi, retained `durum`, vasiyet {c:0,a}).

    pc.py: bildirim_kur -> PcBildirim(wifi, Mantik(cikis, ...), yayinla=kopru.yayinla)

Iki parca:
  Mantik      SAF karar katmani (ag yok): MQTT mesajlari (`durum` / `olay`), kartin YEREL satirlari
              (koprunun canli akisindaki `G` kayit durumu satiri + satir gelis zamani) ve saniyede
              bir `tik` -> cikis.goster(etiket, baslik, metin, sessiz). Sinamada sahte cikis + saat.
  PcBildirim  iplik: /bildirim/bilgi (eslesmis cihaz, IMZALI, canli akisla AYNI Cihaz ve sayac
              kilidi — WifiKart.imzali_ac) -> araciya YALNIZ ABONE (ok/<onek>/#, QoS 1) -> Mantik.

── GUVENLIK (PC14) ─────────────────────────────────────────────────────
  * /bildirim/bilgi yaniti (K ile sifreli OKB1 zarfi; K DPAPI'de) diske OLDUGU GIBI yazilir:
    `<veri>\\bildirim\\<kart kimligi>.okb`. Cozulmus araci adresi / kullanici / parola / konu oneki /
    yuk anahtari YALNIZ bellekte; dosyaya, gunluge, durum satirina, /bildirim/durum'a, cokme izine
    GITMEZ. Hata metinleri istisna metninden DEGIL siniftan uretilir (ssl hatasi araci adini
    tasir) ve her durum metni yine de sirlardan arindirilir (`_temizle`).
  * Onbellek once kullanilir (kart erisilemezken de abone olunur); yeniden alma YALNIZ: zarf
    cozulemedi (anahtar degisti), CONNACK 4/5, ya da kart cevrimici gorunurken durum konusu
    SESSIZ (QR! oneki de degistirir: eski konu susar) — ve yalniz kart erisilebilirse; en sik
    YENILE_EN_AZ_SN'de bir.
  * Yayin YOK (cihaz hesabi zaten yalniz abone); karta komut YOK.

── OLAYLAR ─────────────────────────────────────────────────────────────
  sinif (ayar.json `bildirim.<sinif>`, varsayilan hepsi acik):
    kopuk            vasiyet / durum {c:0} — YALNIZ kayit surerken; kart yerelde gorunuyorsa
                     "ev interneti koptu"; donunce AYNI bildirim (etiket `baglanti`) guncellenir
    bitti            kayit_bitti (sebep 1/3/4/6/7) · pil_bitti · yerel `G` gecisi (kayit -> degil)
    dolu             dolu · kayit_bitti sebep 2 · yerel `G` -> 3
    esik             esik
    yeniden_basladi  basladi (devam=1) · kayit_bitti sebep 5
    kacirilan        (a, n) bosluklari (PC15; kalici oturum yok)
    deneme           Qt
  Yineleme (PC16): MQTT icinde (a, n); yollar arasi (aile, a, oturum) + zaman penceresi; daha
  ayrintili ikinci haber AYNI bildirimi SESSIZCE gunceller, daha az ayrintili olani duser.
"""
from __future__ import annotations

import collections
import datetime
import http.client
import json
import os
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bildirim                                           # noqa: E402
import bildirim_metin as BM                               # noqa: E402
import mqtt_istemci as mq                                 # noqa: E402
import pc_ayar                                            # noqa: E402

SINIFLAR = ("kopuk", "bitti", "dolu", "esik", "yeniden_basladi", "kacirilan", "deneme")
KAYITTA = (2, 4)                 # KDR_KAYIT, KDR_BEKLIYOR (kayit_yonet.h)
KDR_DOLU = 3
YEREL_ERISIM_SN = 15.0           # son yerel satir bundan yeniyse kart "yerelde gorunuyor"
YEREL_KOPUK_SN = 20.0            # yalniz yerel yol: bu kadar satir gelmezse "karttan haber yok"
PENCERE_SN = 900.0               # yollar arasi yineleme penceresi
YAKIN_SN = 120.0                 # oturumu bilinmeyen haberlerin eslesme penceresi
AN_AZAMI = 1024                  # akilda tutulan (a, n)
KEEPALIVE = 30
SESSIZLIK_SN = 180.0             # kart 60 s'de bir durum yollar; 3 kati sessizlik = konu degismis olabilir
SESSIZ_YENILE_ARALIK = 1800.0
YENILE_EN_AZ_SN = 60.0
G_ALAN = 13                      # `G` satiri alan sayisi (olcum-karti-a3.ino kayit_durum_bas)
_G_DESEN = re.compile(r"G(?: -?\d+){%d}" % G_ALAN)
_KIMLIK_DESEN = re.compile(r"[0-9a-f]{16}")


def mqtt_beklemesi(n: int) -> float:
    """n. ardisik basarisiz araci baglantisindan sonra: 2, 4, 8, 16, 32, 60, 60 ... s."""
    return min(60.0, 2.0 * (2 ** min(max(n, 1) - 1, 10)))


def bilgi_beklemesi(n: int) -> float:
    """Bildirim bilgisi yokken (kart erisilemez): 30, 60, 120, 240, 300 ... s."""
    return min(300.0, 30.0 * (2 ** min(max(n, 0), 10)))


def _tamsayi(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


# ── ayar (ayar.json; 4C ile ORTAK dosya — anahtarlar BIRLESTIRILIR) ──────
def ayar_oku() -> tuple[dict, str, str | None]:
    """(acik siniflar, dil, uyari). Dosya bozuk / deger bicimsiz -> o sinif ACIK (bildirim
    kaybolmasin) ve uyari."""
    acik = {s: True for s in SINIFLAR}
    d, hata = pc_ayar.ayar_oku()
    if hata:
        return acik, "tr", f"{pc_ayar.AYAR} okunamadi — bildirimler varsayilan (hepsi acik)"
    uyari = None
    b = d.get("bildirim", {})
    if not isinstance(b, dict):
        b, uyari = {}, f"{pc_ayar.AYAR} 'bildirim' bir nesne degil — varsayilan (hepsi acik)"
    for s in SINIFLAR:
        v = b.get(s, True)
        if isinstance(v, bool):
            acik[s] = v
        else:
            uyari = f"{pc_ayar.AYAR} bildirim.{s} true/false degil — acik sayildi"
    dil = d.get("bildirim_dil", "tr")
    return acik, dil if dil in BM.DILLER else "tr", uyari


def ayar_yaz(degisiklik: dict, dil: str | None = None) -> dict:
    """Bildirim anahtarlarini ayar.json'a BIRLESTIR (oteki anahtarlar — esitleme_onay vb. — aynen
    kalir). Dosya bozuksa YAZMAZ (ValueError): kullanicinin elle yazdigi ayar ezilmesin."""
    for s, v in degisiklik.items():
        if s not in SINIFLAR or not isinstance(v, bool):
            raise ValueError(f"bilinmeyen bildirim sinifi ya da true/false olmayan deger: {s}")
    if dil is not None and dil not in BM.DILLER:
        raise ValueError(f"dil {BM.DILLER} olmali")
    p = pc_ayar.veri_dizini() / pc_ayar.AYAR
    mevcut: dict = {}
    if p.exists():
        try:
            mevcut = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ValueError(f"{pc_ayar.AYAR} okunamadi ({type(e).__name__}) — uzerine YAZILMADI") from None
        if not isinstance(mevcut, dict):
            raise ValueError(f"{pc_ayar.AYAR} bir JSON nesnesi degil — uzerine YAZILMADI")
    b = mevcut.get("bildirim")
    b = dict(b) if isinstance(b, dict) else {}
    b.update(degisiklik)
    mevcut["bildirim"] = b
    if dil is not None:
        mevcut["bildirim_dil"] = dil
    _atomik_yaz(p, json.dumps(mevcut, ensure_ascii=False, indent=2).encode("utf-8"))
    return mevcut


def _atomik_yaz(p: Path, veri: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    gecici = p.with_name(p.name + ".yeni")
    with open(gecici, "wb") as f:
        f.write(veri)
        f.flush()
        os.fsync(f.fileno())
    os.replace(gecici, p)


def satir_dinle(kart, dinleyici) -> None:
    """Kartin `satir_oku`sunu sar: her kart satiri ONCE dinleyiciye (Kopru.dongu degismez).
    Dinleyici yalniz `G` satirini ayristirir; baska satirin icerigini SAKLAMAZ."""
    asil = kart.satir_oku

    def satir_oku(zaman_asimi: float = 0.5):
        s = asil(zaman_asimi)
        if s is not None:
            try:
                dinleyici(s)
            except Exception:                               # noqa: BLE001 — akis asla durmasin
                pass
        return s
    kart.satir_oku = satir_oku


# ── karar katmani ────────────────────────────────────────────────────────
class Mantik:
    """MQTT + yerel haberleri bildirime cevirir. Ag yok; butun durum burada, tek kilitte."""

    def __init__(self, cikis, yayinla=None, ayar=ayar_oku, saat=time.monotonic, duvar=time.time,
                 kalici=None):
        self.cikis = cikis
        self._yayinla = yayinla
        self._ayar_islev = ayar
        self._saat = saat
        self._duvar = duvar
        self._kalici = Path(kalici) if kalici else None
        self._kilit = threading.RLock()
        self._goruldu: collections.OrderedDict = collections.OrderedDict()
        self._son_n: dict[int, int] = {}
        self._son_a: int | None = None
        self._onceki = self._kalici_oku()           # (a, n) onceki calismadan
        self._a_guncel: int | None = None
        self.kacirilan = 0
        self.kart_cevrimici: bool | None = None
        self._durum: dict | None = None
        self.son_durum_mono: float | None = None
        self._son_gorulme: float | None = None      # kartin son "c:1" unix zamani
        self._oturum_tur: dict[int, int] = {}
        self._yerel_g: tuple[int, int] | None = None
        self._yerel_g_t: float | None = None
        self._yerel_son: float | None = None
        self.mqtt_bagli = False
        self._baglanti: str | None = None           # None | kopuk | ev | yerel
        self._baglanti_oturum = None
        self._kayitlar: list[dict] = []
        self._sayac = 0
        self.son_mesaj: float | None = None
        self.son_olay: float | None = None
        self.son_olay_tur: str | None = None
        self.bildirim_sayisi = 0
        self.son_bildirim: float | None = None
        self._son_uyari: str | None = None

    # ── disaridan ────────────────────────────────────────────────────
    def mqtt_bagli_oldu(self, bagli: bool) -> None:
        with self._kilit:
            self.mqtt_bagli = bool(bagli)

    def mqtt_mesaj(self, son: str, icerik: dict) -> None:
        """Cozulmus mesaj: `son` = konunun onekten sonraki kismi ("durum" / "olay")."""
        with self._kilit:
            self.son_mesaj = self._duvar()
            if son == "durum":
                self._durum_isle(icerik)
            elif son == "olay":
                self._olay_isle(icerik)

    def yerel_satir(self, satir: str) -> None:
        """Koprunun yukari-akisindan gelen HER kart satiri (USB ya da WiFi). Yalniz `G` ayristirilir."""
        with self._kilit:
            self._yerel_son = self._saat()
            if not satir.startswith("G ") or not _G_DESEN.fullmatch(satir.rstrip()):
                return
            p = satir.split()
            durum, oturum = int(p[1]), int(p[2])
            once = self._yerel_g
            self._yerel_g, self._yerel_g_t = (durum, oturum), self._saat()
            if once is None:
                return
            od, oo = once
            if od in KAYITTA and (durum not in KAYITTA or oturum != oo):
                dolu = durum == KDR_DOLU
                self._bildir({"aile": "oturum_sonu", "a": self._a_guncel, "oturum": oo, "sira": 1,
                              "sinif": "dolu" if dolu else "bitti",
                              "anahtar": "bld.dolu_oturum" if dolu else "bld.kayit_bitti_yerel",
                              "degisken": {"oturum": oo}})

    def tik(self) -> None:
        """Saniyede bir: yerel erisim degisti mi (kopuk <-> ev), yalniz yerel yolda kopukluk."""
        with self._kilit:
            if self.kart_cevrimici is False:
                self._baglanti_degerlendir()
                return
            yerel_yol = not self.mqtt_bagli or self.kart_cevrimici is None
            if not yerel_yol:
                return
            kopuk = self._yerel_son is not None and self._saat() - self._yerel_son > YEREL_KOPUK_SN
            if self._baglanti is None and kopuk:
                suruyor, oturum = self._kayit()
                if suruyor:
                    self._baglanti, self._baglanti_oturum = "yerel", oturum
                    self._goster("baglanti", "kopuk", "bld.kopuk_yerel", oturum=oturum)
            elif self._baglanti == "yerel" and not kopuk:
                self._geri_geldi(*self._kayit())

    def durum(self) -> dict:
        acik, dil, uyari = self._ayar()
        with self._kilit:
            suruyor, oturum = self._kayit()
            return {"mqtt_bagli": self.mqtt_bagli, "kart_cevrimici": self.kart_cevrimici,
                    "kayit_suruyor": suruyor, "oturum": oturum, "yerel_erisim": self._yerel_erisim(),
                    "son_mesaj": self.son_mesaj, "son_olay": self.son_olay,
                    "son_olay_tur": self.son_olay_tur, "kacirilan": self.kacirilan,
                    "baglanti_bildirimi": self._baglanti, "bildirim_sayisi": self.bildirim_sayisi,
                    "son_bildirim": self.son_bildirim, "ayar": acik, "dil": dil, "ayar_uyari": uyari}

    # ── durum (retained) ─────────────────────────────────────────────
    def _durum_isle(self, d: dict) -> None:
        c = d.get("c")
        if c == 1:
            self.kart_cevrimici = True
            self._durum, self.son_durum_mono = d, self._saat()
            if _tamsayi(d.get("t")) and d["t"] > 0:
                self._son_gorulme = d["t"]
            if _tamsayi(d.get("a")):
                self._a_guncel = d["a"]
            if _tamsayi(d.get("o")) and d["o"] > 0 and _tamsayi(d.get("y")):
                self._oturum_tur[d["o"]] = d["y"]
            if self._baglanti is not None:
                self._geri_geldi(d.get("k") in KAYITTA, d.get("o"))
        elif c == 0:
            self.kart_cevrimici = False
            self._baglanti_degerlendir()

    def _geri_geldi(self, suruyor: bool, oturum) -> None:
        if suruyor:
            self._goster("baglanti", "kopuk", "bld.geri_kayit", oturum=oturum)
        else:
            self._goster("baglanti", "kopuk", "bld.geri")
        self._baglanti = None

    def _baglanti_degerlendir(self) -> None:
        """Araci karti cevrimdisi diyor: kayit suruyorsa "karttan haber yok", kart yerelde
        gorunuyorsa "ev interneti koptu" — tek bildirim (etiket `baglanti`), degisince guncellenir."""
        hedef = "ev" if self._yerel_erisim() else "kopuk"
        if self._baglanti == hedef or (self._baglanti == "yerel" and hedef == "kopuk"):
            self._baglanti = hedef
            return
        if self._baglanti is None:
            suruyor, oturum = self._kayit()
            if not suruyor:
                return
            self._baglanti_oturum = oturum
        self._baglanti = hedef
        self._goster("baglanti", "kopuk", "bld.ev_interneti" if hedef == "ev" else "bld.kopuk",
                     oturum=self._baglanti_oturum)

    # ── olay ─────────────────────────────────────────────────────────
    def _olay_isle(self, d: dict) -> None:
        n, a, o = d.get("n"), d.get("a"), d.get("o")
        if not (_tamsayi(n) and _tamsayi(a) and isinstance(o, str)):
            return
        if (a, n) in self._goruldu:
            return                                          # QoS 1 yeniden teslim / yeniden gonderim
        if self._onceki is not None and self._onceki[0] == a and n <= self._onceki[1] \
                and a not in self._son_n:
            return                                          # onceki calismada gorulmus
        self._goruldu[(a, n)] = True
        while len(self._goruldu) > AN_AZAMI:
            self._goruldu.popitem(last=False)
        self._bosluk(a, n)
        self._a_guncel = a
        self.son_olay, self.son_olay_tur = self._duvar(), o
        self._kalici_yaz(a, n)
        oturum = d.get("oturum") if _tamsayi(d.get("oturum")) else None
        if o == "basladi":
            if d.get("devam") == 1:
                self._bildir({"aile": "basladi", "a": a, "oturum": oturum, "sira": 2,
                              "sinif": "yeniden_basladi", "anahtar": "bld.basladi_devam",
                              "degisken": {"oturum": oturum}})
        elif o == "kayit_bitti":
            s = d.get("sebep")
            if s == 2:
                sinif, anahtar, deg = "dolu", "bld.dolu_oturum", {"oturum": oturum}
            elif s == 5:
                sinif, anahtar = "yeniden_basladi", "bld.kesildi"
                deg = {"oturum": oturum, "tur": None, "saat": None}
            else:
                sinif, anahtar = "bitti", "bld.kayit_bitti"
                deg = {"oturum": oturum, "sebep": ("sebep.", s), "nokta": d.get("nokta", "?")}
            self._bildir({"aile": "oturum_sonu", "a": a, "oturum": oturum, "sira": 2, "sinif": sinif,
                          "anahtar": anahtar, "degisken": deg})
        elif o == "pil_bitti":
            self._bildir({"aile": "oturum_sonu", "a": a, "oturum": None, "sira": 3, "sinif": "bitti",
                          "anahtar": "bld.pil_bitti",
                          "degisken": {"durum": ("pil.durum.", d.get("durum")),
                                       "mah": ("sayi", d.get("mah_milli"), 1000, 1),
                                       "wh": ("sayi", d.get("wh_milli"), 1000, 2),
                                       "sure": ("sure", d.get("sure_ms"))}})
        elif o == "dolu":
            self._bildir({"aile": "oturum_sonu", "a": a, "oturum": None, "sira": 2, "sinif": "dolu",
                          "anahtar": "bld.dolu", "degisken": {}})
        elif o == "esik":
            self._bildir({"aile": "esik", "a": a, "oturum": None, "sira": 2, "sinif": "esik",
                          "anahtar": "bld.esik",
                          "degisken": {"deger": ("sayi", d.get("deger"), 10, 1),
                                       "esik": ("sayi", d.get("esik"), 10, 1)}})
        elif o == "deneme":
            self._bildir({"aile": "deneme", "a": a, "oturum": None, "sira": 2, "sinif": "deneme",
                          "anahtar": "bld.deneme", "degisken": {}})

    def _bosluk(self, a: int, n: int) -> None:
        """PC15: kalici oturum yok — cevrimdisiyken kacan olaylar (a, n) bosluklarindan sayilir."""
        eksik = 0
        once = self._son_n.get(a)
        if once is not None:
            eksik = max(0, n - once - 1)
            self._son_n[a] = max(once, n)
        else:
            if self._son_a is not None:
                eksik = n - 1                           # kart yeniden basladi; yeni acilisin ilk olaylari
            elif self._onceki is not None:
                pa, pn = self._onceki
                eksik = max(0, n - pn - 1) if pa == a else n - 1
            self._son_n[a] = n
        self._son_a = a
        if eksik > 0:
            self.kacirilan += eksik
            self._goster("kacirilan", "kacirilan", "bld.kacirilan", adet=self.kacirilan)

    # ── bildirim ─────────────────────────────────────────────────────
    def _bildir(self, olay: dict) -> None:
        simdi = self._saat()
        self._kayitlar = [r for r in self._kayitlar if simdi - r["t"] <= PENCERE_SN]
        acik, dil, _ = self._ayar()
        m = self._eslesen(olay, simdi)
        if m is not None:
            if olay["sira"] <= m["sira"]:
                return                                      # ayni ya da daha az ayrintili: tek bildirim
            m.update(sira=olay["sira"], sinif=olay["sinif"], anahtar=olay["anahtar"],
                     degisken=olay["degisken"])
            if acik.get(olay["sinif"], True):
                self._cikis(m["etiket"], self._metin(m, dil), sessiz=m["gosterildi"])
                m["gosterildi"] = True
            return
        r = dict(olay, t=simdi, etiket=self._etiket(olay), gosterildi=False)
        self._kayitlar.append(r)
        if acik.get(olay["sinif"], True):
            self._cikis(r["etiket"], self._metin(r, dil))
            r["gosterildi"] = True

    def _eslesen(self, olay: dict, simdi: float) -> dict | None:
        if olay["aile"] == "deneme":
            return None
        for r in reversed(self._kayitlar):
            if r["aile"] != olay["aile"]:
                continue
            if r["a"] is not None and olay["a"] is not None and r["a"] != olay["a"]:
                continue
            if r["oturum"] is not None and olay["oturum"] is not None:
                if r["oturum"] != olay["oturum"]:
                    continue
            elif simdi - r["t"] > YAKIN_SN:
                continue
            return r
        return None

    def _etiket(self, olay: dict) -> str:
        self._sayac += 1
        o, a = olay["oturum"], olay["a"]
        if olay["aile"] == "oturum_sonu" and _tamsayi(o) and o >= 0:
            return f"os-{o & 0xFFFFFFFF:x}"
        if olay["aile"] == "basladi" and _tamsayi(a) and a >= 0:
            return f"bs-{a & 0xFFFFFFFF:x}"
        return f"{olay['aile'][:2]}-t{self._sayac & 0xFFFFFF:x}"

    def _metin(self, r: dict, dil: str) -> str:
        deg = {}
        for ad, v in r["degisken"].items():
            if isinstance(v, tuple) and v and v[0] in ("sebep.", "pil.durum."):
                deg[ad] = BM.kod_metni(v[0], v[1], dil)
            elif isinstance(v, tuple) and v and v[0] == "sayi":
                deg[ad] = _sayi(v[1], v[2], v[3], dil)
            elif isinstance(v, tuple) and v and v[0] == "sure":
                deg[ad] = _sure(v[1])
            else:
                deg[ad] = "?" if v is None else v
        if r["anahtar"] == "bld.kesildi":
            o = r["oturum"]
            tur = self._oturum_tur.get(o) if _tamsayi(o) else None
            deg["tur"] = BM.kod_metni("oturum.tur.", tur if tur is not None else 1, dil)
            deg["saat"] = (BM.metin("bld.kesildi_saat", dil, saat=_saat_yazi(self._son_gorulme))
                           if self._son_gorulme else "")
        return BM.metin(r["anahtar"], dil, **deg)

    def _goster(self, etiket: str, sinif: str, anahtar: str, **deg) -> None:
        acik, dil, _ = self._ayar()
        if not acik.get(sinif, True):
            return
        deg = {k: ("?" if v is None else v) for k, v in deg.items()}
        self._cikis(etiket, BM.metin(anahtar, dil, **deg))

    def _cikis(self, etiket: str, metin: str, sessiz: bool = False) -> None:
        _, dil, _ = self._ayar()
        try:
            self.cikis.goster(etiket, BM.metin("bld.baslik", dil), metin, sessiz=sessiz)
            self.bildirim_sayisi += 1
            self.son_bildirim = self._duvar()
        except Exception as e:                              # noqa: BLE001 — bildirim yolu karar katmanini oldurmez
            self._uyar(f"! bildirim: gosterilemedi ({type(e).__name__})")

    # ── yardimcilar ──────────────────────────────────────────────────
    def _ayar(self) -> tuple[dict, str, str | None]:
        try:
            acik, dil, uyari = self._ayar_islev()
        except Exception:                                   # noqa: BLE001
            acik, dil, uyari = {s: True for s in SINIFLAR}, "tr", "bildirim ayari okunamadi"
        if uyari:
            self._uyar("! bildirim: " + uyari)
        return acik, dil, uyari

    def _uyar(self, metin: str) -> None:
        if metin == self._son_uyari:
            return
        self._son_uyari = metin
        if self._yayinla:
            try:
                self._yayinla(metin)
            except Exception:                               # noqa: BLE001
                pass

    def _kayit(self) -> tuple[bool | None, int | None]:
        """Kayit suruyor mu: yerel `G` ile MQTT `durum`'un HANGISI daha yeniyse o."""
        adaylar = []
        if self._yerel_g is not None:
            adaylar.append((self._yerel_g_t, self._yerel_g[0], self._yerel_g[1]))
        if self._durum is not None:
            adaylar.append((self.son_durum_mono, self._durum.get("k"), self._durum.get("o")))
        if not adaylar:
            return None, None
        _, k, o = max(adaylar, key=lambda x: x[0])
        return k in KAYITTA, o

    def _yerel_erisim(self) -> bool:
        return self._yerel_son is not None and self._saat() - self._yerel_son <= YEREL_ERISIM_SN

    def _kalici_oku(self):
        if self._kalici is None or not self._kalici.exists():
            return None
        try:
            d = json.loads(self._kalici.read_text(encoding="utf-8"))
            if _tamsayi(d.get("a")) and _tamsayi(d.get("n")):
                return d["a"], d["n"]
        except (OSError, ValueError, AttributeError):
            pass
        return None

    def _kalici_yaz(self, a: int, n: int) -> None:
        if self._kalici is None:
            return
        try:
            _atomik_yaz(self._kalici, json.dumps({"a": a, "n": n}).encode("ascii"))
        except OSError:
            pass


def _sayi(x, bolen, basamak: int, dil: str) -> str:
    if not _tamsayi(x):
        return "?"
    s = f"{x / bolen:.{basamak}f}"
    return s.replace(".", ",") if dil == "tr" else s


def _sure(ms) -> str:
    if not _tamsayi(ms) or ms < 0:
        return "?"
    s = ms // 1000
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}"


def _saat_yazi(unix) -> str:
    try:
        return datetime.datetime.fromtimestamp(unix).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return "?"


def hata_sinifi(e: BaseException) -> str:
    """Istisnadan SIR TASIMAYAN kisa metin (ssl hatalari araci adini tasir — metni kullanilmaz)."""
    if isinstance(e, ssl.SSLCertVerificationError):
        return "TLS sertifika/ad denetimi"
    if isinstance(e, ssl.SSLError):
        return "TLS"
    if isinstance(e, socket.gaierror):
        return "ad cozulemedi"
    if isinstance(e, (TimeoutError, socket.timeout)):
        return "zaman asimi"
    if isinstance(e, ConnectionRefusedError):
        return "baglanti reddedildi"
    if isinstance(e, mq.BaglantiKoptu):
        return "baglanti koptu"
    if isinstance(e, mq.MqttHata):
        return "protokol"
    if isinstance(e, OSError):
        return "ag"
    return type(e).__name__


# ── iplik: bilgi + araci ─────────────────────────────────────────────────
class PcBildirim:
    """Kopru surecindeki MQTT ipligi (tek). `durum()` -> GET /bildirim/durum."""

    def __init__(self, wifi, mantik: Mantik, yayinla=None, veri_dizini=None, istemci=mq.Istemci,
                 saat=time.monotonic, keepalive: int = KEEPALIVE, sessizlik: float = SESSIZLIK_SN,
                 yenile_en_az: float = YENILE_EN_AZ_SN, ssl_baglam=None, beklemeler=None):
        self.wifi = wifi
        self.mantik = mantik
        self._yayinla = yayinla
        self.dizin = Path(veri_dizini or pc_ayar.veri_dizini()) / "bildirim"
        self._istemci = istemci
        self._saat = saat
        self.keepalive = keepalive
        self.sessizlik = sessizlik
        self.yenile_en_az = yenile_en_az
        self._ssl = ssl_baglam
        self._beklemeler = beklemeler or (mqtt_beklemesi, bilgi_beklemesi)
        self._dur = threading.Event()
        self._is: threading.Thread | None = None
        self._b: dict | None = None                 # cozulmus bilgi — YALNIZ bellekte
        self._yenile = False
        self._son_yenileme: float | None = None
        self._son_sessiz_yenileme: float | None = None
        self._son_metin: str | None = None
        self.bilgi_alimi = 0                        # karttan /bildirim/bilgi alma sayisi
        self.cozulemeyen = 0
        self._d = {"etkin": True, "bilgi": "yok", "abone": False, "mesaj": "", "baglanti_sayisi": 0}

    # ── dis yuzey ────────────────────────────────────────────────────
    def baslat(self) -> None:
        if self._is is not None and self._is.is_alive():
            return
        self._dur.clear()
        self._is = threading.Thread(target=self._dongu, name="kopru-bildirim", daemon=True)
        self._is.start()

    def durdur(self, bekle: float = 5.0) -> None:
        self._dur.set()
        if self._is is not None and self._is is not threading.current_thread():
            self._is.join(bekle)
        self._is = None
        kapat = getattr(self.mantik.cikis, "kapat", None)
        if kapat:
            kapat()

    def yerel_satir(self, satir: str) -> None:
        self.mantik.yerel_satir(satir)

    def durum(self) -> dict:
        d = dict(self._d)
        d.update(self.mantik.durum())
        d["bildirim_yolu"] = getattr(self.mantik.cikis, "yol", "?")
        d["mesaj"] = self._temizle(d.get("mesaj") or "")
        return d

    # ── ic ───────────────────────────────────────────────────────────
    def _temizle(self, metin: str) -> str:
        """Derinlemesine savunma: durum metninde cozulmus bilginin hicbir parcasi kalmasin."""
        b = self._b
        if not b or not metin:
            return metin
        try:
            host = bildirim.uri_coz(b["uri"])[0]
        except ValueError:
            host = ""
        for s in (b.get("uri", ""), host, b.get("kullanici", ""), b.get("parola", ""),
                  b.get("onek", ""), b.get("anahtar", b"").hex()):
            if s and len(s) >= 3:
                metin = metin.replace(s, "<gizli>")
        return metin

    def _soyle(self, metin: str) -> None:
        metin = self._temizle(metin)
        self._d["mesaj"] = metin
        if metin == self._son_metin:
            return
        self._son_metin = metin
        if self._yayinla:
            try:
                self._yayinla(metin)
            except Exception:                               # noqa: BLE001
                pass

    def _bekle(self, sn: float) -> None:
        son = self._saat() + sn
        while not self._dur.is_set():
            kalan = son - self._saat()
            if kalan <= 0:
                return
            self._dur.wait(min(1.0, kalan))
            self.mantik.tik()

    def _dongu(self) -> None:
        n_araci = n_bilgi = 0
        while not self._dur.is_set():
            try:
                b = self._bilgi_hazirla()
                if b is None:
                    self._bekle(self._beklemeler[1](n_bilgi))
                    n_bilgi += 1
                    continue
                n_bilgi = 0
                baglandi = self._oturum(b)
                n_araci = 0 if baglandi else n_araci + 1
                if self._dur.is_set():
                    break
                if not self._yenile:
                    self._bekle(self._beklemeler[0](max(n_araci, 1)))
            except Exception as e:                          # noqa: BLE001 — iplik olmesin; METIN YOK (sir)
                self._soyle(f"! bildirim: beklenmeyen hata ({type(e).__name__}) — yeniden denenecek")
                self._bekle(30.0)

    def _bilgi_hazirla(self) -> dict | None:
        if self._b is not None and not self._yenile:
            return self._b
        if self._yenile:
            self._yenile = False
            if self._son_yenileme is not None and self._saat() - self._son_yenileme < self.yenile_en_az:
                return self._b
            self._son_yenileme = self._saat()
            b = self._karttan_al()
            if b is not None:
                self._b = b
            elif self._b is not None:
                self._soyle("! bildirim: bilgi yenilenemedi — onbellekteki bilgiyle devam")
            return self._b
        b = self._onbellekten()
        if b is not None:
            self._b = b
            self._d["bilgi"] = "onbellek"
            return b
        self._son_yenileme = self._saat()
        b = self._karttan_al()
        if b is not None:
            self._b = b
        return b

    def _cihaz(self, kimlik: str):
        if self.wifi is not None:
            c, _ = self.wifi._cihaz_bul(kimlik)       # karta gitmez: cihaz dosyasi (DPAPI) — PAYLASILAN nesne
            return c
        import imza as IM
        try:
            return IM.Cihaz.yukle(pc_ayar.cihaz_dizini() / f"{kimlik}.json")
        except (OSError, ValueError, KeyError):
            return None

    def _onbellekten(self) -> dict | None:
        if not self.dizin.is_dir():
            return None
        dosyalar = sorted(self.dizin.glob("*.okb"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in dosyalar:
            kimlik = p.stem
            if not _KIMLIK_DESEN.fullmatch(kimlik):
                continue
            c = self._cihaz(kimlik)
            if c is None:
                continue
            try:
                b = bildirim.bilgi_coz(c.K, kimlik, c.n, p.read_bytes())
            except (OSError, ValueError):
                continue                                    # cihaz yeniden eslesmis / bozuk: karttan alinir
            return b
        return None

    def _karttan_al(self) -> dict | None:
        if self.wifi is None:
            self._soyle("! bildirim: WiFi yukari-akisi yok (--wifi-yok) ve onbellekte gecerli bilgi yok — "
                        "MQTT bildirimi kapali")
            return None
        import kart_wifi as KW
        try:
            cihaz, kimlik, _ = self.wifi.dogrula()
        except KW.KartDogrulanamadi:
            self._soyle("! bildirim: kart WiFi'den dogrulanamadi (erisilemiyor ya da eslesme yok) — "
                        "bildirim bilgisi alinamadi, yeniden denenecek")
            return None
        if not _KIMLIK_DESEN.fullmatch(kimlik):
            return None
        try:
            with self.wifi.imzali_ac(cihaz, "GET", bildirim.BILGI_YOLU) as y:
                govde = y.read()
        except urllib.error.HTTPError as h:
            kod = h.code
            h.close()
            if kod == 404:
                self._soyle("! bildirim: kartta MQTT bildirimi ayarli degil (USB: Qu, Qc, Qd, Q1) — "
                            "yerel bildirimler yine calisir")
            else:
                self._soyle(f"! bildirim: kart /bildirim/bilgi'yi reddetti (HTTP {kod})")
            return None
        except Exception as e:                              # noqa: BLE001 — ag / kimlik
            self._soyle(f"! bildirim: /bildirim/bilgi alinamadi ({hata_sinifi(e)})")
            return None
        try:
            b = bildirim.bilgi_coz(cihaz.K, kimlik, cihaz.n, govde)
        except ValueError:
            self._soyle("! bildirim: /bildirim/bilgi cozulemedi (cihaz anahtari uymuyor)")
            return None
        _atomik_yaz(self.dizin / f"{kimlik}.okb", govde)   # PC14: zarf AYNEN (K ile sifreli)
        self.bilgi_alimi += 1
        self._d["bilgi"] = "karttan"
        self._b = b
        self._soyle("* bildirim: kartin bildirim bilgisi alindi (sifreli zarf onbellege yazildi)")
        return b

    def _oturum(self, b: dict) -> bool:
        """Bir araci baglantisi. Donus: baglanip abone olabildi mi."""
        try:
            host, port, tls = bildirim.uri_coz(b["uri"])
        except ValueError:
            self._soyle("! bildirim: kartin verdigi araci adresi bicimsiz")
            self._yenile = True
            return False
        c = self._istemci(host, port, tls, b["kullanici"], b["parola"], keepalive=self.keepalive,
                          zaman_asimi=10.0, ssl_baglam=self._ssl)
        try:
            c.baglan()
            c.abone(f"ok/{b['onek']}/#", 1)
        except mq.BaglantiReddedildi as h:
            c.kapat(nazik=False)
            if h.kod in (4, 5):
                self._yenile = True
                self._soyle(f"! bildirim: araci kimligi reddetti (kod {h.kod}) — kart erisilebilirse "
                            "bilgi yeniden alinacak")
            else:
                self._soyle(f"! bildirim: araci baglantiyi reddetti (kod {h.kod})")
            return False
        except Exception as e:                              # noqa: BLE001
            c.kapat(nazik=False)
            self._soyle(f"! bildirim: araciya baglanilamadi ({hata_sinifi(e)}) — yeniden denenecek")
            return False
        self._d.update(abone=True, baglanti_sayisi=self._d["baglanti_sayisi"] + 1)
        self.mantik.mqtt_bagli_oldu(True)
        self._soyle("* bildirim: araciya baglandi (yalniz abone) — kart olaylari dinleniyor")
        baslangic = self._saat()
        try:
            while not self._dur.is_set():
                m = c.bekle(1.0)
                if m is not None:
                    self._mesaj(b, *m)
                self.mantik.tik()
                if self._yenile or self._sessiz_mi(baslangic):
                    break
        except Exception as e:                              # noqa: BLE001
            self._soyle(f"! bildirim: araci baglantisi koptu ({hata_sinifi(e)}) — yeniden baglaniliyor")
        finally:
            self.mantik.mqtt_bagli_oldu(False)
            self._d["abone"] = False
            c.kapat()
        return True

    def _mesaj(self, b: dict, konu: str, yuk: bytes, retain: bool) -> None:
        on = f"ok/{b['onek']}/"
        if not konu.startswith(on):
            return
        try:
            icerik = bildirim.zarf_ac(b["anahtar"], konu, yuk)
        except ValueError:
            self.cozulemeyen += 1
            if self._son_yenileme is None or self._saat() - self._son_yenileme >= self.yenile_en_az:
                self._yenile = True
                self._soyle("! bildirim: bir mesaj cozulemedi — anahtar degismis olabilir (QR!); kart "
                            "erisilebilirse bilgi yeniden alinacak")
            return
        self.mantik.mqtt_mesaj(konu[len(on):], icerik)

    def _sessiz_mi(self, baslangic: float) -> bool:
        """Kart cevrimici gorunurken durum konusu SESSIZ: QR! oneki degistirmis olabilir."""
        if self.mantik.kart_cevrimici is not True:
            return False
        ref = max(self.mantik.son_durum_mono or baslangic, baslangic)
        if self._saat() - ref < self.sessizlik:
            return False
        if self._son_sessiz_yenileme is not None and \
                self._saat() - self._son_sessiz_yenileme < SESSIZ_YENILE_ARALIK:
            return False
        self._son_sessiz_yenileme = self._saat()
        self._yenile = True
        self._soyle("! bildirim: kart cevrimici gorunuyor ama durum konusu sessiz — konu degismis olabilir "
                    "(QR!); bilgi yeniden alinacak")
        return True


def main(argv=None) -> int:
    """`python kopru/pc_bildirim.py ayar kopuk=0 bitti=1 [dil=en]` — ayar.json'a birlestir.
    `python kopru/pc_bildirim.py durum` — calisan koprunun /bildirim/durum'u."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["durum"]:
        try:
            with pc_ayar.yerel_istek(pc_ayar.PORT, "/bildirim/durum") as y:
                print(json.dumps(json.load(y), ensure_ascii=False, indent=2))
            return 0
        except Exception as e:                              # noqa: BLE001
            print(f"kopru calismiyor ya da yanit yok ({type(e).__name__})")
            return 1
    if argv[:1] == ["ayar"]:
        degisiklik, dil = {}, None
        for p in argv[1:]:
            ad, _, deger = p.partition("=")
            if ad == "dil":
                dil = deger
            elif deger in ("0", "1"):
                degisiklik[ad] = deger == "1"
            else:
                print(f"bicim: <sinif>=0|1 (siniflar: {', '.join(SINIFLAR)}) ya da dil=tr|en — {p!r}")
                return 2
        try:
            d = ayar_yaz(degisiklik, dil)
        except ValueError as e:
            print(f"HATA: {e}")
            return 1
        print(json.dumps({"bildirim": d.get("bildirim"), "bildirim_dil": d.get("bildirim_dil", "tr")},
                         ensure_ascii=False))
        return 0
    print(main.__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
