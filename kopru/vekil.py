# -*- coding: utf-8 -*-
"""4D — PANEL PC'DE: PC arsivi (salt okuma) + kartin uclarinin imzali vekili (PC10, PC11).

Tasarim: tasarim/2026-10-03-alt-proje-4-pc.md PC10 / PC11 + "4D uygulama kararlari".
`kopru.Isleyici.do_GET` bu uclari TEK satirla buraya yollar (`UCLAR`); kopru.py'nin
geri kalani degismez.

── PC10: PC ARSIVI, SALT OKUMA ────────────────────────────────────────
Tek yazar Python (`arka_esitle.ArkaEsitleme` -> `kayit_esitle.Esitleyici`); panel
yalniz OKUR — `esitle.kilit`'in onledigi iki yazar / iki kopya yarisi dogmaz.

    GET /arsiv/liste                              akislar (kart, akis, boy, durum, oturumlar)
    GET /arsiv/veri?kart=&akis=&ofset=&bayt=      kayitlar.kyt'nin bayt araligi (AYNEN)
    GET /arsiv/kal?kart=&akis=                    kalibrasyon.json (AYNEN)

  * Her parametre KATI: kart 16 kucuk onaltilik, akis/ofset/bayt bastaki sifirsiz
    ondalik; bilinmeyen / tekrar eden parametre 400. Cozulen yol arsiv dizininin
    ICINDE olmali (4A `gun_yolu` dersi: mutlak / UNC yol arsivi EZER, `exists()`
    SMB baglantisi acar). Sembolik bag / baglanti noktasi izlenmez.
  * "Boy" KALICI onektir: `durum.json`'un `bayt`i (Esitleyici veriyi fsync'ten SONRA
    durumu atomik yaziyor). Dosyada ondan sonrasi (cokme kuyrugu, suren yazim) verilmez.
  * Yalniz bu bilgisayardan (yerel ag 403), yalniz ayni kokenden (CSRF 403). POST /
    PUT / DELETE yok — kopru.do_POST bu yollari tanimaz.
  * Yanitta mutlak yol YOK: arsiv adi veri dizinine goreli (`arsiv/<kart>/akis-<n>`).

── PC11: KART UCLARININ IMZALI VEKILI ────────────────────────────────
    GET /pil[?sira=N]   GET /kal/liste   GET /kunye.json

  Kopru karta WiFi'den ESLESMIS CIHAZ olarak imzali istek atar (`WifiKart.imzali_ac`:
  canli akis ve arka plan esitlemesiyle AYNI Cihaz nesnesi ve sayac kilidi). Beyaz
  liste: yalniz bu uc yol, yalniz GET, yalniz izinli parametre. Panelin gonderdigi imza
  basliklari (X-Cihaz / X-Sayac / X-Imza) ve `_c _s _i` TASINMAZ — kopru kendi
  cihaziyla imzalar (`_c` vb. parametre 400).
  `p0` BURADAN GECMEZ: `/komut` vekilde degil; p0 kopru.`/komut` -> SecmeliKart yolundan
  IMZASIZ ve sayac kilidini BEKLEMEDEN gider (kart_wifi._p0) — yavas bir vekil istegi
  DURDUR'u geciktiremez (O7).
  Hata: kart WiFi'den dogrulanamiyor / erisilemiyor / imzayi reddediyor / WiFi yukari-akisi
  yok -> 502 + JSON {"vekil": <neden>, "mesaj": ...} + `X-Kopru-Vekil: hata`. Kartin kendi
  2xx / 404 / 503'u AYNEN gecer (`X-Kopru-Vekil: kart`).

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import http.client
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imza as IM                                         # noqa: E402
import kart_wifi as KW                                    # noqa: E402
import kayit_bicim as KB                                  # noqa: E402
import kayit_esitle as KE                                 # noqa: E402
import pc_ayar                                            # noqa: E402

ARSIV_UCLARI = ("/arsiv/liste", "/arsiv/veri", "/arsiv/kal")
# yol -> izinli sorgu parametreleri (hepsi bastaki sifirsiz ondalik)
VEKIL_UCLARI = {"/pil": ("sira",), "/kal/liste": (), "/kunye.json": ()}
UCLAR = ARSIV_UCLARI + tuple(VEKIL_UCLARI)

KART_DESEN = re.compile(r"[0-9a-f]{16}")
SAYI_DESEN = re.compile(r"0|[1-9][0-9]{0,15}")
AKIS_DIZIN = re.compile(r"akis-(0|[1-9][0-9]{0,15})")
VERI_AZAMI = 4 * 1024 * 1024          # tek /arsiv/veri yanitinin tavani (panel 2 MB ister)
KAL_AZAMI = 1024 * 1024
VEKIL_GOVDE_AZAMI = 256 * 1024        # kartin /pil, /kal/liste, /kunye.json yanitlari birkac KB
VEKIL_ZAMAN_ASIMI = 10.0
DOGRULAMA_OMRU_SN = 30.0              # vekil, kart dogrulamasini bu kadar yeniden kullanir

LAN_RET = ("PC arsivi ve kart vekili yalniz bu bilgisayardan (kopru calisan PC) — yerel agdan "
           "salt okuma canli izlemedir")
CAPRAZ_RET = "baska bir kokenden (site) gelen istek reddedildi"
YOL_DESEN = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\)[^\s,;)'\"]*|/(?:home|Users)/[^\s,;)'\"]*")


def yolsuz(metin: str) -> str:
    """Kullaniciya giden metinden mutlak yollari cikar (kullanici adi tasimasin)."""
    return YOL_DESEN.sub("<yol>", str(metin))


def arsiv_koku(kopru) -> Path:
    """Esitlemenin yazdigi arsivin koku (kurulmadiysa `pc_ayar.arsiv_dizini()`)."""
    es = getattr(kopru, "esitleme", None)
    kok = getattr(es, "arsiv_kok", None) if es is not None else None
    return Path(kok) if kok else pc_ayar.arsiv_dizini()


def wifi_al(kart):
    """Yukari-akisin WiFi kolu (`SecmeliKart.wifi` ya da `WifiKart`); yoksa None."""
    if isinstance(kart, KW.WifiKart):
        return kart
    w = getattr(kart, "wifi", None)
    return w if isinstance(w, KW.WifiKart) else None


def akis_dizini(kok: Path, kart: str, akis: str) -> Path:
    """Dogrulanmis akis dizini. Bicim disi ya da arsiv kokunun DISINA cikan yol -> ValueError."""
    if not isinstance(kart, str) or not KART_DESEN.fullmatch(kart):
        raise ValueError("kart 16 kucuk onaltilik olmali")
    if not isinstance(akis, str) or not SAYI_DESEN.fullmatch(akis):
        raise ValueError("akis bastaki sifirsiz ondalik olmali")
    kok_r = Path(kok).resolve()
    d = Path(kok) / kart / f"akis-{akis}"
    if d.is_symlink() or d.parent.is_symlink():
        raise ValueError("arsiv dizini sembolik bag")
    if not d.resolve().is_relative_to(kok_r):
        raise ValueError("arsiv dizininin disi")
    return d


def _durum_oku(d: Path) -> dict:
    """durum.json'dan YALNIZ tamsayi alanlar (bicimsizse bos)."""
    try:
        v = json.loads((d / KE.DURUM).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(v, dict):
        return {}
    return {a: v[a] for a in ("son_sira", "bayt", "onaylanan", "kimlik")
            if isinstance(v.get(a), int) and not isinstance(v.get(a), bool) and v[a] >= 0}


def kalici_boy(d: Path, boyut: int) -> int:
    """Verilebilecek bayt: durum.json `bayt`i (kalici onek); yoksa / tutarsizsa dosya boyu."""
    b = _durum_oku(d).get("bayt")
    return b if isinstance(b, int) and 0 <= b <= boyut else boyut


class ArsivOkuyucu:
    """Arsiv dizinini salt okur. Oturum ozeti (kayit_bicim) dosya boyu + mtime ile onbellekte."""

    def __init__(self):
        self._kilit = threading.Lock()
        self._onbellek: dict[str, tuple] = {}

    def _oturumlar(self, f: Path, boy: int, mtime: int) -> list[dict]:
        anahtar = str(f)
        with self._kilit:
            o = self._onbellek.get(anahtar)
        if o is not None and o[0] == (boy, mtime):
            return o[1]
        with open(f, "rb") as fp:
            veri = fp.read(boy)
        kayitlar, _ = KB.akis_onek(veri)
        ozet = []
        for ot in sorted(KB.oturumlari_kur(kayitlar).values(), key=lambda x: x.id):
            b = ot.basla
            ozet.append({"id": ot.id, "tur": b.oturum_turu if b else None,
                         "unix_s": b.unix_s if b else None, "ad": ot.ad,
                         "nokta": len(ot.noktalar), "bitti": ot.bitir is not None})
        with self._kilit:
            self._onbellek[anahtar] = ((boy, mtime), ozet)
        return ozet

    def liste(self, kok: Path) -> list[dict]:
        kok = Path(kok)
        if not kok.is_dir():
            return []
        cikti = []
        for kd in sorted(kok.iterdir()):
            if not KART_DESEN.fullmatch(kd.name) or kd.is_symlink() or not kd.is_dir():
                continue
            for ad in sorted(kd.iterdir()):
                m = AKIS_DIZIN.fullmatch(ad.name)
                if not m:
                    continue
                try:
                    d = akis_dizini(kok, kd.name, m.group(1))
                except ValueError:
                    continue
                f = d / KE.DOSYA
                if not f.is_file():
                    continue
                st = f.stat()
                boy = kalici_boy(d, st.st_size)
                durum = _durum_oku(d)
                try:
                    oturumlar = self._oturumlar(f, boy, st.st_mtime_ns)
                except OSError:
                    oturumlar = []
                cikti.append({"kart": kd.name, "akis": int(m.group(1)), "ad": f"arsiv/{kd.name}/{ad.name}",
                              "bayt": boy, "dosya_bayt": st.st_size, "degisim": round(st.st_mtime, 3),
                              "durum": durum, "kal": (d / KE.KAL_DOSYA).is_file(),
                              "oturum": len(oturumlar), "oturumlar": oturumlar})
        cikti.sort(key=lambda a: a["degisim"], reverse=True)
        return cikti


class KartVekili:
    """Kopru basina tek vekil: kart dogrulamasini (bilgi -> kimlik -> cihaz) kisa sure yeniden kullanir."""

    def __init__(self):
        self._kilit = threading.Lock()
        self._cihaz = None
        self._wifi = None
        self._zaman = 0.0

    def unut(self) -> None:
        with self._kilit:
            self._cihaz = None

    def _cihaz_al(self, wifi):
        with self._kilit:
            if (self._cihaz is not None and self._wifi is wifi
                    and time.monotonic() - self._zaman < DOGRULAMA_OMRU_SN):
                return self._cihaz
        cihaz, _, _ = wifi.dogrula()                 # PAYLASILAN Cihaz (ayni sayac)
        with self._kilit:
            self._cihaz, self._wifi, self._zaman = cihaz, wifi, time.monotonic()
        return cihaz

    def getir(self, wifi, yol: str, argumanlar: list) -> tuple[int, str, bytes, bool]:
        """(kod, tur, govde, kartin_yaniti_mi). Kart yaniti degilse govde JSON hata."""
        try:
            cihaz = self._cihaz_al(wifi)
        except KW.KartDogrulanamadi as e:
            return _hata(502, "dogrulanamadi", "kart WiFi'den dogrulanamadi — " + yolsuz(str(e)))
        try:
            with wifi.imzali_ac(cihaz, "GET", yol, argumanlar, b"", VEKIL_ZAMAN_ASIMI) as y:
                govde = y.read(VEKIL_GOVDE_AZAMI + 1)
                tur = y.headers.get("Content-Type") or "application/octet-stream"
                kod = y.status
        except urllib.error.HTTPError as h:
            try:
                govde = h.read(VEKIL_GOVDE_AZAMI) or b""
                tur = h.headers.get("Content-Type") or "text/plain"
            except Exception:                               # noqa: BLE001
                govde, tur = b"", "text/plain"
            finally:
                h.close()
            if h.code == 401:
                self.unut()
                return _hata(502, "imza", "kart koprunun imzasini reddetti (HTTP 401) — cihaz kartta "
                                          "silinmis olabilir; kopruyu yeniden eslestirin: "
                                          "`python kopru/imza.py esles`")
            return h.code, tur, govde, True
        except IM.KartKimligiHatasi as e:
            self.unut()
            return _hata(502, "kimlik", yolsuz(str(e)))
        except (OSError, http.client.HTTPException, ValueError) as e:
            self.unut()
            return _hata(502, "erisim", f"karta WiFi'den ulasilamadi ({type(e).__name__})")
        if len(govde) > VEKIL_GOVDE_AZAMI:
            return _hata(502, "buyuk", "kartin yaniti vekil siniri asti")
        return kod, tur, govde, True


def _hata(kod: int, neden: str, mesaj: str) -> tuple[int, str, bytes, bool]:
    return (kod, "application/json",
            json.dumps({"vekil": neden, "mesaj": mesaj}, ensure_ascii=False).encode("utf-8"), False)


_DURUM_KILIT = threading.Lock()


def _durum(kopru, ad: str, sinif):
    """Kopru nesnesine bagli tekil yardimci (ArsivOkuyucu / KartVekili)."""
    with _DURUM_KILIT:
        x = getattr(kopru, ad, None)
        if x is None:
            x = sinif()
            setattr(kopru, ad, x)
        return x


def sorgu_kati(yol_sorgu: str, izinli: tuple, zorunlu: tuple = ()) -> dict:
    """Sorguyu KATI coz: bilinmeyen / tekrar eden / bos parametre ve eksik zorunlu -> ValueError."""
    ham = yol_sorgu.split("?", 1)[1] if "?" in yol_sorgu else ""
    try:
        ciftler = urllib.parse.parse_qsl(ham, keep_blank_values=True, strict_parsing=bool(ham),
                                         max_num_fields=8)
    except ValueError:
        raise ValueError("sorgu bicimsiz") from None
    d: dict[str, str] = {}
    for a, v in ciftler:
        if a not in izinli or a in d:
            raise ValueError(f"izinsiz ya da tekrar eden parametre: {a[:20]!r}")
        d[a] = v
    eksik = [a for a in zorunlu if a not in d]
    if eksik:
        raise ValueError("eksik parametre: " + ", ".join(eksik))
    return d


def _sayi(v: str, ad: str) -> int:
    if not SAYI_DESEN.fullmatch(v):
        raise ValueError(f"{ad} bastaki sifirsiz ondalik olmali")
    return int(v)


# ── HTTP ────────────────────────────────────────────────────────────────
def isle(h, yol: str) -> None:
    """`kopru.Isleyici` icin: kapilar (yerel + ayni koken) sonra arsiv ya da vekil."""
    if not h._yerel():
        return h._yanit(403, LAN_RET.encode("utf-8"))
    if h._capraz():
        return h._yanit(403, CAPRAZ_RET.encode("utf-8"))
    try:
        if yol == "/arsiv/liste":
            return _arsiv_liste(h)
        if yol == "/arsiv/veri":
            return _arsiv_veri(h)
        if yol == "/arsiv/kal":
            return _arsiv_kal(h)
        return _vekil(h, yol)
    except ValueError as e:
        return h._yanit(400, yolsuz(str(e)).encode("utf-8"))


def _ikili(h, kod: int, govde: bytes, tur: str, ek: dict | None = None) -> None:
    h.send_response(kod)
    h.send_header("Content-Type", tur)
    h.send_header("Content-Length", str(len(govde)))
    h.send_header("Cache-Control", "no-store")
    for a, v in (ek or {}).items():
        h.send_header(a, v)
    h.end_headers()
    if govde:
        h.wfile.write(govde)


def _arsiv_liste(h) -> None:
    sorgu_kati(h.path, ())
    okuyucu = _durum(h.kopru, "_pc_arsiv", ArsivOkuyucu)
    try:
        liste = okuyucu.liste(arsiv_koku(h.kopru))
    except OSError as e:
        return h._yanit(503, f"PC arsivi okunamadi ({type(e).__name__})".encode("utf-8"))
    govde = json.dumps({"arsivler": liste}, ensure_ascii=False).encode("utf-8")
    _ikili(h, 200, govde, "application/json; charset=utf-8")


def _akis_dosyasi(h, ad: str, izinli: tuple) -> tuple[Path, dict]:
    q = sorgu_kati(h.path, izinli, izinli)
    d = akis_dizini(arsiv_koku(h.kopru), q["kart"], q["akis"])
    return d / ad, q


def _arsiv_veri(h) -> None:
    f, q = _akis_dosyasi(h, KE.DOSYA, ("kart", "akis", "ofset", "bayt"))
    ofset, bayt = _sayi(q["ofset"], "ofset"), _sayi(q["bayt"], "bayt")
    if not 1 <= bayt <= VERI_AZAMI:
        raise ValueError(f"bayt 1..{VERI_AZAMI} olmali")
    if not f.is_file():
        return h._yanit(404, "arsivde boyle bir akis yok".encode("utf-8"))
    try:
        boy = kalici_boy(f.parent, f.stat().st_size)
        if ofset > boy:
            raise ValueError(f"ofset arsivin disinda (boy {boy})")
        with open(f, "rb") as fp:
            fp.seek(ofset)
            govde = fp.read(min(bayt, boy - ofset))
    except OSError as e:
        return h._yanit(503, f"arsiv okunamadi ({type(e).__name__})".encode("utf-8"))
    _ikili(h, 200, govde, "application/octet-stream", {"X-Arsiv-Boy": str(boy)})


def _arsiv_kal(h) -> None:
    f, _ = _akis_dosyasi(h, KE.KAL_DOSYA, ("kart", "akis"))
    if not f.is_file():
        return h._yanit(404, "bu akisin kalibrasyon kopyasi yok".encode("utf-8"))
    try:
        with open(f, "rb") as fp:
            govde = fp.read(KAL_AZAMI + 1)
    except OSError as e:
        return h._yanit(503, f"kalibrasyon kopyasi okunamadi ({type(e).__name__})".encode("utf-8"))
    if len(govde) > KAL_AZAMI:
        return h._yanit(503, "kalibrasyon kopyasi beklenenden buyuk".encode("utf-8"))
    _ikili(h, 200, govde, "application/json; charset=utf-8")


def _vekil(h, yol: str) -> None:
    izinli = VEKIL_UCLARI[yol]
    q = sorgu_kati(h.path, izinli)
    argumanlar = [(a, str(_sayi(q[a], a))) for a in izinli if a in q]
    wifi = wifi_al(h.kopru.kart)
    if wifi is None:
        kod, tur, govde, kart = _hata(502, "wifi_yok", "kopru kartla WiFi'den konusmuyor (--wifi-yok "
                                                       "ya da olu tekrar): /pil, /kal/liste ve "
                                                       "/kunye.json yalniz WiFi'den")
    else:
        kod, tur, govde, kart = _durum(h.kopru, "_kart_vekili", KartVekili).getir(wifi, yol, argumanlar)
    _ikili(h, kod, govde, tur, {"X-Kopru-Vekil": "kart" if kart else "hata"})
