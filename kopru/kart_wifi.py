# -*- coding: utf-8 -*-
"""4B — koprunun WiFi YUKARI-AKISI: kart ile ESLESMIS CIHAZ olarak konusur (PC6).

Iki sinif, `kart_baglanti.SeriKart` ile AYNI yuzey (ac / kapat / satir_oku / yaz /
ad / bildir / durum_satiri / baglanti_no):

    WifiKart     kartin /akis SSE'si (imzali), /komut (imzali; p0 IMZASIZ)
    SecmeliKart  USB (OtoSeriKart) ONCE; dogrulanmis kart USB'de yoksa WiFi

Tasarim: tasarim/2026-10-03-alt-proje-4-pc.md PC6 + "4B uygulama kararlari".

── GUVENLIK ───────────────────────────────────────────────────────────
  * Her (yeniden) baglanmadan ONCE `/eslestir/bilgi` (acik uc): kartin KIMLIGI
    cihaz dosyasiyla karsilastirilir (D5 #18). Uymuyorsa ya da bu kart icin
    eslesmis cihaz yoksa /akis ACILMAZ, komut GONDERILMEZ — acik mesajla.
    Kimlik dosya adina gider: once 16 onaltilik mi diye bakilir (yol gecisi).
  * `/akis` adresi TEK KULLANIMLIK (sayac): her baglanmada YENI imzali adres
    (`imza.akis_url`, D5 #17); bekleme artar (1, 2, 4 ... 30 s), veri gelen
    baglantidan sonra 1 s'ye doner — kartin seri web cekirdegi bogulmaz.
  * Komutlar imzali (`imza.ac`; jeton/parola YOK). `p0` (DURDUR) HER ZAMAN
    imzasiz ve kart dogrulanmadan da gider: kart onu serbest birakir
    (komut_serbest), kopru hicbir katmanda geciktirmez (O7).
  * E ve Q komutlarini kopru zaten `/komut`'ta reddeder (kopru.komut_izinli);
    gizli satir suzgeci (Kopru.dongu) bu yukari-akista da calisir.
  * Kartin NTP saati yoksa (`saat` != 1) her baglantida BIR KEZ imzali `/saat`
    (R11). Ret yaniti (HTTPError) okunup KAPATILIR ve kodla soylenir.
  * Vekil (HTTP_PROXY / sistem vekili) KULLANILMAZ: kart yerel agda ya da kendi
    AP'sinde; vekile giden istek kartin anahtarli trafigini disari tasirdi.

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import http.client
import queue
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imza as IM                                         # noqa: E402
import pc_ayar                                            # noqa: E402

BEKLE_TABAN = 1.0
BEKLE_AZAMI = 30.0
KIMLIK_DESEN = re.compile(r"[0-9a-f]{16}")
ACILIS_DESEN = re.compile(r"[0-9a-f]{32}")
SATIR_AZAMI = 65536

_ACICI = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def vekilsiz_ac(istek, timeout=None):
    """urlopen gibi, ama sistem/ortam vekiline UYMAZ (kart yerel agda)."""
    return _ACICI.open(istek, timeout=timeout)


def bekleme(n: int) -> float:
    """n. basarisiz denemeden sonraki bekleme: 1, 2, 4, 8, 16, 30, 30 ... s."""
    return min(BEKLE_AZAMI, BEKLE_TABAN * (2 ** min(n, 10)))


class KartDogrulanamadi(RuntimeError):
    """4C: adresteki kart bu PC'nin eslestigi kart olarak DOGRULANAMADI (erisilemez, bicimsiz,
    eslesme yok, kimlik uymuyor). Metin kullaniciya soylenir."""


def _hata_metni(h: urllib.error.HTTPError) -> str:
    """HTTPError'un govdesini oku ve KAPAT (D5 #18: kapatilmayan yanit soketi tutar)."""
    try:
        govde = h.read(300).decode("utf-8", "replace").strip()
    except Exception:                                       # noqa: BLE001
        govde = ""
    finally:
        h.close()
    return f"HTTP {h.code}" + (f" {govde}" if govde else "")


class WifiKart:
    """Kartin WiFi uclarina eslesmis cihaz olarak baglanan yukari-akis.

    Okuma ayri bir iplikte: SSE satirlari kuyruga, `satir_oku` kuyruktan.
    Durum degisiklikleri `bildir` ile (kopru: akisa, arsive DEGIL) BIR KEZ.
    """

    def __init__(self, host: str | None = None, dizin=None, cihaz_dosyasi=None, bekle=None,
                 zaman_asimi: float = 10.0, okuma_zaman_asimi: float = 40.0, saat=time.time):
        self.host = host or pc_ayar.kart_host()
        self.taban = IM.taban_url(self.host)
        self.dizin = Path(dizin) if dizin else None
        self.cihaz_dosyasi = Path(cihaz_dosyasi) if cihaz_dosyasi else None
        self.zaman_asimi = zaman_asimi
        # kart 15 s'de bir `: kalp` yollar; 40 s sessizlik = kopuk
        self.okuma_zaman_asimi = okuma_zaman_asimi
        self._bekle_islev = bekle
        self._saat = saat
        self.bildir = None
        self.durum_satiri: str | None = None
        self.baglanti_no = 0
        self.kopuk = False                    # SeriKart yuzeyi; WiFi kopuklugu ic dongude
        self.bagli = False
        self._kuyruk: queue.Queue = queue.Queue(maxsize=4000)
        self.dusen = 0
        # Durdurma olayi IPLIK BASINA: kapat() suresi icinde (ör. mDNS cozumu) bitmeyen eski
        # iplik, yeni ac() ile baslayan iplikle durumu/kuyrugu PAYLASMASIN — eski iplik kendi
        # olayina bakar, kuyruga satir koymaz.
        self._dur = threading.Event()
        self._yerel = threading.local()
        self._is: threading.Thread | None = None
        self._baglanti: http.client.HTTPConnection | None = None
        self._cihaz: IM.Cihaz | None = None   # BU kartla dogrulanmis cihaz (yoksa komut yok)
        # Sayac kilidi (4B-12 + 4C): akis adresi, komut, /saat VE arka plan esitlemesi AYNI Cihaz
        # nesnesini kullanir; imzanin uretimi ile istegin karta ulasmasi (yanit basi) tek kritik
        # bolgede — kart sayaclari SIRAYLA gorur (pencere 64 ms; araya giren istek eskiyi reddettirir)
        self._imza_kilit = threading.RLock()
        self._cihazlar: dict[Path, IM.Cihaz] = {}   # dosya -> TEK paylasilan Cihaz nesnesi
        self._son_neden: str | None = None

    # ── yuzey ────────────────────────────────────────────────────────
    @property
    def ad(self) -> str:
        c = self._cihaz
        return f"wifi:{self.host}" + (f" (cihaz {c.n})" if c else "")

    def ac(self) -> None:
        """Hata ATMAZ: kart erisilemiyorsa arka planda denemeye devam eder."""
        if self._is is not None and self._is.is_alive():
            return
        dur = self._dur = threading.Event()
        self._is = threading.Thread(target=self._dongu, args=(dur,), name="kopru-wifi", daemon=True)
        self._is.start()

    def kapat(self) -> None:
        self._dur.set()
        b = self._baglanti
        if b is not None and b.sock is not None:
            try:
                b.sock.shutdown(socket.SHUT_RDWR)   # bekleyen readline'i hemen birak
            except OSError:
                pass
        if self._is is not None and self._is is not threading.current_thread():
            self._is.join(3.0)
        self._is = None
        self.bagli = False
        while True:                                  # kalan satirlar: yeni yukari-akisla karismasin
            try:
                self._kuyruk.get_nowait()
            except queue.Empty:
                break

    def satir_oku(self, zaman_asimi: float = 0.5) -> str | None:
        try:
            return self._kuyruk.get(timeout=max(0.0, zaman_asimi))
        except queue.Empty:
            return None

    def yaz(self, metin: str) -> None:
        if metin == "p0":
            return self._p0()
        cihaz = self._cihaz
        if cihaz is None:
            raise RuntimeError(f"WiFi ({self.host}): kart dogrulanmadi — komut GONDERILMEDI"
                               + (f" ({self._son_neden})" if self._son_neden else ""))
        try:
            with self.imzali_ac(cihaz, "POST", "/komut", [], metin.encode("utf-8")) as y:
                y.read()
        except urllib.error.HTTPError as h:
            raise RuntimeError(f"kart komutu reddetti: {_hata_metni(h)}") from None
        except IM.KartKimligiHatasi as e:
            raise RuntimeError(str(e)) from None
        except OSError as e:
            raise RuntimeError(f"karta WiFi'den ulasilamadi ({self.host}): {e}") from None

    def imzali_ac(self, cihaz: IM.Cihaz, yontem: str, yol: str, argumanlar=(), govde: bytes = b"",
                  zaman_asimi: float | None = None):
        """4C: imzali istek (urlopen gibi yanit; `with` ile). Imza + istek + yanit basi SAYAC
        KILIDINDE: canli akis, komut ve arka plan esitlemesi ayni Cihaz'in sayacini sirayla kullanir.
        Govdeyi cagiran kilitsiz okur (kart imzayi yanit basindan once dogrulamistir)."""
        with self._imza_kilit:
            return IM.ac(cihaz, self.taban, yontem, yol, list(argumanlar), govde,
                         zaman_asimi or self.zaman_asimi, acici=vekilsiz_ac)

    def dogrula(self) -> tuple[IM.Cihaz, str, dict]:
        """Adresteki karti dogrula: acik `/eslestir/bilgi` -> kimlik bicimi -> bu kart icin eslesmis
        cihaz dosyasi -> kimlik uyusmasi; acilis tazelenir. Donus: (PAYLASILAN Cihaz, kimlik, bilgi).
        Hata: KartDogrulanamadi (metin kullaniciya). Canli akis ve arka plan esitlemesi (4C) ayni yol."""
        try:
            b = IM.bilgi(self.taban, self.zaman_asimi, acici=vekilsiz_ac)
        except urllib.error.HTTPError as h:
            raise KartDogrulanamadi(f"/eslestir/bilgi {_hata_metni(h)} (eski firmware?)") from None
        except (OSError, ValueError, http.client.HTTPException) as e:
            raise KartDogrulanamadi(f"kart erisilemiyor ({e})") from None
        kimlik, acilis = b.get("kimlik"), b.get("acilis")
        if not (isinstance(kimlik, str) and KIMLIK_DESEN.fullmatch(kimlik)
                and isinstance(acilis, str) and ACILIS_DESEN.fullmatch(acilis)):
            raise KartDogrulanamadi("/eslestir/bilgi bicimsiz (kimlik/acilis) — kart degil ya da eski firmware")
        cihaz, neden = self._cihaz_bul(kimlik)
        if cihaz is None:
            raise KartDogrulanamadi(neden)
        with self._imza_kilit:
            if cihaz.acilis != acilis:
                cihaz.acilis = acilis
                cihaz.kaydet()
        return cihaz, kimlik, b

    # ── ic ───────────────────────────────────────────────────────────
    def _p0(self) -> None:
        """DURDUR: imzasiz, X-Olcum'lu; kimlik/cihaz denetimine TAKILMAZ (O7)."""
        istek = urllib.request.Request(self.taban + "/komut", data=b"p0", method="POST",
                                       headers={"X-Olcum": "1", "Content-Type": "text/plain"})
        try:
            with vekilsiz_ac(istek, timeout=self.zaman_asimi) as y:
                y.read()
        except urllib.error.HTTPError as h:
            raise RuntimeError(f"p0: {_hata_metni(h)}") from None
        except OSError as e:
            raise RuntimeError(f"p0 karta WiFi'den ulasamadi ({self.host}): {e}") from None

    def _soyle(self, metin: str) -> None:
        self.durum_satiri = None if metin.startswith("* ") else metin
        if self.bildir:
            self.bildir(metin)

    def _neden(self, metin: str) -> None:
        if metin != self._son_neden:
            self._son_neden = metin
            self._soyle(f"! kopru: WiFi ({self.host}) — {metin}")

    def _bekle(self, sn: float) -> None:
        if self._bekle_islev is not None:
            self._bekle_islev(sn)
        else:
            (getattr(self._yerel, "dur", None) or self._dur).wait(sn)

    def _durdu(self) -> bool:
        return (getattr(self._yerel, "dur", None) or self._dur).is_set()

    def _koy(self, satir: str) -> None:
        if self._durdu():
            return                                    # durdurulmus (eski) iplik: satir yeni akisa karismaz
        try:
            self._kuyruk.put_nowait(satir)
        except queue.Full:
            self.dusen += 1                           # kopru dongusu takilmissa: olcumu bekletme

    def _dongu(self, dur: threading.Event) -> None:
        self._yerel.dur = dur
        n = 0
        while not self._durdu():
            veri = False
            try:
                veri = self._bir_baglanti()
            except Exception as e:                        # noqa: BLE001 — iplik olmesin
                self._neden(f"beklenmeyen hata: {e!r}")
            if self._durdu():
                break
            if veri:
                n = 0
            self._bekle(bekleme(n))
            n += 1

    def _cihaz_bul(self, kimlik: str) -> tuple[IM.Cihaz | None, str]:
        if self.cihaz_dosyasi is not None:
            dosya = self.cihaz_dosyasi
        else:
            dosya = (self.dizin or IM.varsayilan_dizin()) / f"{kimlik}.json"
            if not dosya.exists():
                return None, (f"bu PC {kimlik} kimlikli kartla ESLESMEMIS ({dosya.parent} icinde "
                              f"cihaz dosyasi yok) — `python kopru/imza.py esles --host {self.host} "
                              f"--ad <bu-PC>`")
        try:
            with self._imza_kilit:                    # ayni surecteki kaydet() ile yarismasin
                c = IM.Cihaz.yukle(dosya)
        except (OSError, ValueError, KeyError) as e:
            return None, f"cihaz dosyasi okunamadi ({dosya.name}): {e}"
        if c.kimlik != kimlik:
            return None, (f"adresteki kartin kimligi {kimlik} — cihaz dosyasi ({dosya.name}) "
                          f"{c.kimlik} kimlikli kartla eslesmis: bu kart o DEGIL, /akis acilmadi, "
                          f"komut GONDERILMEZ (p0 haric)")
        return self._paylasilan(c), ""

    def _paylasilan(self, c: IM.Cihaz) -> IM.Cihaz:
        """4C (4B-12): ayni cihaz dosyasi icin TEK Cihaz nesnesi — akis, komut ve arka plan
        esitlemesi ayni sayaci ilerletir. Iki nesne ayni milisaniyede AYNI sayaci uretir, kart
        ikincisini tekrar diye reddeder (401). Dosya yeniden eslestirmeyle degismisse (n / K /
        kimlik) yenisi alinir; sayac geri gitmez."""
        with self._imza_kilit:
            eski = self._cihazlar.get(c.dosya)
            if eski is not None and (eski.kimlik, eski.n, eski.K) == (c.kimlik, c.n, c.K):
                eski.sayac = max(eski.sayac, c.sayac)
                return eski
            self._cihazlar[c.dosya] = c
            return c

    def _bir_baglanti(self) -> bool:
        """Bir baglanti denemesi. Donus: bu baglantida en az bir olcum satiri geldi mi."""
        try:
            cihaz, kimlik, b = self.dogrula()
        except KartDogrulanamadi as e:
            self._cihaz = None
            self._neden(str(e))
            return False
        self._cihaz = cihaz
        if self._durdu():
            return False
        with self._imza_kilit:
            url = IM.akis_url(cihaz, self.taban, acici=vekilsiz_ac)     # HER baglanmada YENI
            # 4C: istek + yanit basi da kilitte — yavas baglantida (mDNS) araya giren esitleme
            # istegi daha buyuk sayacla once ulasirsa kart bu adresi pencere disi diye reddederdi
            baglanti, y, hata = self._akis_iste(url)
        acildi = False
        try:
            if hata is not None:
                raise hata
            if y.status == 401:
                y.close()
                self._neden("kart imzayi reddetti (HTTP 401) — cihaz kartta silinmis olabilir; "
                            f"yeniden eslestirin: `python kopru/imza.py esles --host {self.host} "
                            f"--ad <bu-PC>`")
                return False
            if y.status != 200:
                y.close()
                self._neden(f"/akis HTTP {y.status}")
                return False
            if baglanti.sock is not None:
                baglanti.sock.settimeout(self.okuma_zaman_asimi)
            acildi = True
            self.baglanti_no += 1
            self.bagli = True
            self._son_neden = None
            self._soyle(f"* kopru: WiFi baglandi — {self.host} (cihaz {cihaz.n}, kart {kimlik})")
            if b.get("saat") != 1:
                self._saat_ver(cihaz)
            return self._oku(y)
        except (OSError, http.client.HTTPException) as e:
            if not self._durdu() and not acildi:
                self._neden(f"/akis acilamadi ({e})")
            return False
        finally:
            if self._baglanti is baglanti:
                self.bagli = False
                self._baglanti = None
            baglanti.close()
            if acildi and not self._durdu():
                self._soyle(f"! kopru: WiFi baglantisi koptu ({self.host}) — yeniden baglaniliyor")

    def _akis_iste(self, url: str):
        """/akis istegini gonder, yanit basini al. Donus (baglanti, yanit | None, hata | None)."""
        u = urllib.parse.urlsplit(url)
        baglanti = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=self.zaman_asimi)
        self._baglanti = baglanti
        try:
            baglanti.request("GET", u.path + "?" + u.query,
                             headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"})
            return baglanti, baglanti.getresponse(), None
        except (OSError, http.client.HTTPException) as e:
            return baglanti, None, e

    def _oku(self, y) -> bool:
        """SSE cercevesini coz: `data:` satirlari (olaysiz) = kartin protokol satirlari."""
        veri = False
        olay = None
        while not self._durdu():
            ham = y.readline(SATIR_AZAMI)
            if not ham:
                break                                    # kart kapatti
            s = ham.decode("utf-8", "replace").rstrip("\r\n")
            if s == "":
                olay = None                              # olay sonu
                continue
            if s.startswith(":"):
                continue                                 # yorum (kalp)
            if s.startswith("event:"):
                olay = s[6:].strip()
                continue
            if s.startswith("data:"):
                d = s[5:]
                if d.startswith(" "):
                    d = d[1:]
                if olay in (None, "message"):
                    self._koy(d)
                    veri = True
                elif olay == "dolu":
                    self._neden(f"kartin canli izleyici yuvalari dolu ({d}) — yeniden denenecek")
                    return veri
                # `kimlik` (kartin oturum jetonu) ve bilinmeyen olaylar TASINMAZ:
                # kopru kendi tarayicilarina kendi jetonunu verir
                continue
            # `id:` / `retry:` — kopru tarafinda anlami yok
        return veri

    def _saat_ver(self, cihaz: IM.Cihaz) -> None:
        """R11: kartin NTP saati yok — bu PC saati verir (imzali, CIHAZ sinifi)."""
        try:
            with self.imzali_ac(cihaz, "POST", "/saat", [("unix", str(int(self._saat())))]) as y:
                y.read()
            self._soyle("* kopru: kartin NTP saati yok — saat bu PC'den verildi (imzali /saat)")
        except urllib.error.HTTPError as h:
            metin = _hata_metni(h)
            if h.code != 409:                            # 409: arada NTP geldi — sorun degil
                self._soyle(f"! kopru: WiFi — kartin saati verilemedi ({metin})")
        except (OSError, IM.KartKimligiHatasi) as e:
            self._soyle(f"! kopru: WiFi — kartin saati verilemedi ({e})")


class SecmeliKart:
    """4B (PC6): USB ONCE, yoksa WiFi — tek yukari-akis yuzeyi.

    USB'de DOGRULANMIS kart (OtoSeriKart bagli) varsa canli akis ve komut USB'den;
    WiFi baglantisi o an KAPATILIR (ayni satirlar iki kez arsive dusmesin). USB'de
    kart yoksa WiFi (eslesmis cihaz). Gecis `* kopru: ...` durum satiriyla soylenir
    (akisa; arsive DEGIL — Kopru.dongu yalniz satir_oku'nun dondurdugunu arsivler).
    Gecis aninda WiFi kuyrugunda kalan satirlar atilir: USB dogrulama satirlariyla
    cift olmasin.
    """

    USB_YOKLA_SN = 0.05

    def __init__(self, usb, wifi=None):
        self.usb, self.wifi = usb, wifi
        self.bildir = None
        self._etkin: str | None = None
        self._gecis = 0
        usb.bildir = self._ilet
        if wifi is not None:
            wifi.bildir = self._ilet

    def _ilet(self, metin: str) -> None:
        if self.bildir:
            self.bildir(metin)

    def _usb_bagli(self) -> bool:
        return bool(getattr(self.usb, "bagli", False))

    @property
    def etkin(self) -> str | None:
        return self._etkin

    @property
    def baglanti_no(self) -> int:
        return (self._gecis + getattr(self.usb, "baglanti_no", 0)
                + (getattr(self.wifi, "baglanti_no", 0) if self.wifi is not None else 0))

    @property
    def durum_satiri(self) -> str | None:
        if self._etkin == "wifi" and self.wifi is not None:
            return self.wifi.durum_satiri
        return self.usb.durum_satiri

    @property
    def ad(self) -> str:
        if self._etkin == "wifi" and self.wifi is not None:
            return self.wifi.ad
        return self.usb.ad

    def ac(self) -> None:
        self.usb.ac()

    def kapat(self) -> None:
        self.usb.kapat()
        if self.wifi is not None:
            self.wifi.kapat()

    def _sec(self, hedef: str) -> None:
        if hedef == self._etkin:
            return
        onceki, self._etkin = self._etkin, hedef
        self._gecis += 1
        if hedef == "usb":
            if self.wifi is not None and onceki == "wifi":
                self.wifi.kapat()
                self._ilet("* kopru: yukari-akis USB — kart USB'de dogrulandi; WiFi baglantisi kapatildi")
        else:
            self.wifi.ac()
            self._ilet(f"* kopru: USB'de dogrulanmis kart yok — yukari-akis WiFi ({self.wifi.host}, "
                       f"eslesmis cihaz olarak)")

    def satir_oku(self, zaman_asimi: float = 0.5) -> str | None:
        if self._usb_bagli():
            self._sec("usb")
            return self.usb.satir_oku(zaman_asimi)
        if self.wifi is None:
            return self.usb.satir_oku(zaman_asimi)
        # USB'yi yokla (OtoSeriKart kendi araligiyla arar; bulup dogrularsa bagli olur)
        s = self.usb.satir_oku(min(zaman_asimi, self.USB_YOKLA_SN))
        if self._usb_bagli():
            self._sec("usb")
            return s
        self._sec("wifi")
        return self.wifi.satir_oku(zaman_asimi)

    def yaz(self, metin: str) -> None:
        if metin == "p0":
            # EMNIYET: p0 hicbir yukari-akis seciminde takilmaz — biri olmazsa oteki
            hatalar = []
            sira = [self.usb, self.wifi] if self._usb_bagli() else [self.wifi, self.usb]
            for y in sira:
                if y is None:
                    continue
                try:
                    y.yaz("p0")
                    return
                except Exception as e:                    # noqa: BLE001
                    hatalar.append(str(e))
            raise RuntimeError("p0 hicbir yoldan gonderilemedi: " + " | ".join(hatalar))
        if self._etkin == "wifi" and self.wifi is not None and not self._usb_bagli():
            return self.wifi.yaz(metin)
        return self.usb.yaz(metin)
