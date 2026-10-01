# -*- coding: utf-8 -*-
"""1E — tezgah icin SAHTE MQTT 3.1.1 ARACI (yalniz stdlib; duz TCP, TLS YOK).

    python sahte_araci.py --port 1883 --kullanici kart:pw:rw --kullanici cihaz:pw2:r

Gercek araci (EMQX Serverless) yerine yerel sinama: kartin vasiyet (LWT), keepalive ve yeniden
baglanma davranisi bu aracıya karsi OLCULUR. Kod olarak:

    a = SahteAraci(host="0.0.0.0", port=0, kullanicilar={"kart": ("pw", "rw"), "cihaz": ("pw2", "r")})
    a.start(); a.port; ...; a.stop()

Neleri yapar (MQTT 3.1.1):
  CONNECT      kullanici/parola denetimi (yanlis, bilinmeyen ya da kimliksiz -> CONNACK 5);
               her CONNECT `.baglantilar`a yazilir (kimlik, keepalive, vasiyet konu/yuk/qos/retain,
               temiz oturum, kullanici adi, sonuc) — PAROLA hicbir kayda girmez.
               Ayni istemci kimligiyle ikinci baglanti eskisini DUSURUR (vasiyeti yayinlanir).
  ACL          "r" kullanicisi PUBLISH ederse baglanti kesilir (olay `acl_red`, yayin dagitilmaz).
  SUBSCRIBE    `+` ve `#` joker karakterleri, SUBACK; eslesen retained mesajlar retain=1 ile iletilir.
  PUBLISH      QoS 0/1; QoS 1'de yayinciya PUBACK; aboneye min(yayin qos, abonelik qos);
               canli iletimde retain bayragi 0 (3.1.1); retained deposu (bos yuk siler).
  PINGREQ      PINGRESP.  UNSUBSCRIBE destekli.  QoS 2 YOK (baglanti kesilir).
  Keepalive    1.5 x keepalive boyunca paket gelmezse baglanti kesilir, vasiyet yayinlanir.
  Vasiyet      DISCONNECT'siz her kapanista (kopus, keepalive, takeover, acl, protokol) yayinlanir;
               DISCONNECT'te ve aracı kendi kapandiginda (`kapali_tut`) YAYINLANMAZ.
  Kesinti      `kapali_tut()` dinlemeyi birakir + butun istemcileri dusurur; `ac()` AYNI portta
               yeniden dinler (retained deposu korunur — kalici aracı gibi).

Olay gunlugu `.olaylar` (her olay bir sozluk: `i` sira, `t` time.monotonic(), `tur`, ...):
  connect · disconnect(neden) · will_published(neden, konu, yuk, qos, retain) · publish ·
  abone · acl_red · puback · arac_kapali · arac_acik · arac_yayin.
`.kosul` bir threading.Condition: `olay_bekle(...)` / `bekle(...)` ile testler beklemeden
olayi yakalar.
"""
from __future__ import annotations

import argparse
import hmac
import os
import socket
import struct
import sys
import threading
import time

CONNECT, CONNACK, PUBLISH, PUBACK = 1, 2, 3, 4
SUBSCRIBE, SUBACK, UNSUBSCRIBE, UNSUBACK = 8, 9, 10, 11
PINGREQ, PINGRESP, DISCONNECT = 12, 13, 14
KEEPALIVE_CARPAN = 1.5               # spec 3.1.2.10: istemciye 1.5 x kadar tolerans
BAGLANTI_ZAMAN_ASIMI = 10.0          # CONNECT gelmeden acik kalabilecek sure


class ProtokolHatasi(Exception):
    pass


# ── kodlayici/ayristirici (istemciden BAGIMSIZ; bu dosya tek basina calisir) ──
def uzunluk_kodla(n: int) -> bytes:
    if not 0 <= n <= 268_435_455:
        raise ValueError("kalan uzunluk sinir disi")
    cikis = bytearray()
    while True:
        b, n = n % 128, n // 128
        cikis.append(b | 0x80 if n else b)
        if not n:
            return bytes(cikis)


def paket(ilk: int, govde: bytes = b"") -> bytes:
    return bytes([ilk]) + uzunluk_kodla(len(govde)) + govde


def dize(b: bytes | str) -> bytes:
    if isinstance(b, str):
        b = b.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def _dize_oku(g: bytes, i: int) -> tuple[bytes, int]:
    if i + 2 > len(g):
        raise ProtokolHatasi("dize uzunlugu eksik")
    n = (g[i] << 8) | g[i + 1]
    if i + 2 + n > len(g):
        raise ProtokolHatasi("dize eksik")
    return g[i + 2:i + 2 + n], i + 2 + n


class Ayristirici:
    def __init__(self) -> None:
        self._t = bytearray()

    def besle(self, veri: bytes) -> None:
        self._t += veri

    def sonraki(self) -> tuple[int, bytes] | None:
        t = self._t
        if len(t) < 2:
            return None
        deger, carpan, i = 0, 1, 1
        while True:
            if i >= len(t):
                if i > 4:
                    raise ProtokolHatasi("kalan uzunluk 4 bayttan uzun")
                return None
            b = t[i]
            i += 1
            deger += (b & 0x7F) * carpan
            if not b & 0x80:
                break
            carpan *= 128
            if i > 4:
                raise ProtokolHatasi("kalan uzunluk 4 bayttan uzun")
        if len(t) < i + deger:
            return None
        ilk, govde = t[0], bytes(t[i:i + deger])
        del t[:i + deger]
        return ilk, govde


# ── konu kurallari ───────────────────────────────────────────────────────
def filtre_gecerli(f: str) -> bool:
    if not f or "\x00" in f:
        return False
    parcalar = f.split("/")
    for i, p in enumerate(parcalar):
        if "#" in p and (p != "#" or i != len(parcalar) - 1):
            return False
        if "+" in p and p != "+":
            return False
    return True


def konu_gecerli(k: str) -> bool:
    return bool(k) and "\x00" not in k and "+" not in k and "#" not in k


def konu_eslesir(filtre: str, konu: str) -> bool:
    """MQTT 3.1.1 4.7: `+` tek seviye, `#` kalan hepsi (ust seviyenin kendisi dahil);
    `$` ile baslayan konulari basi joker olan filtre eslestirmez."""
    if konu.startswith("$") and filtre[:1] in ("+", "#"):
        return False
    f, k = filtre.split("/"), konu.split("/")
    for i, p in enumerate(f):
        if p == "#":
            return True
        if i >= len(k):
            return False
        if p != "+" and p != k[i]:
            return False
    return len(f) == len(k)


# ── bir istemci baglantisi ───────────────────────────────────────────────
class _Baglanti:
    def __init__(self, araci: "SahteAraci", soket: socket.socket, adres) -> None:
        self.araci, self.soket, self.adres = araci, soket, adres
        self.istemci_id: str | None = None
        self.kullanici: str | None = None
        self.rol = "rw"
        self.keepalive = 0
        self.will: dict | None = None
        self.abonelikler: dict[str, int] = {}
        self.kayitli = False
        self.neden: str | None = None
        self.kapali = threading.Event()
        self._yaz_kilit = threading.Lock()
        self._neden_kilit = threading.Lock()
        self._paket_no = 0
        self.thread = threading.Thread(target=self._calis, daemon=True)

    # -- yazma
    def gonder(self, veri: bytes) -> bool:
        with self._yaz_kilit:
            try:
                self.soket.sendall(veri)
                return True
            except OSError:
                return False

    def yayin_gonder(self, konu: str, yuk: bytes, qos: int, retain: bool) -> None:
        govde = dize(konu)
        if qos:
            with self._yaz_kilit:
                self._paket_no = self._paket_no % 0xFFFF + 1
                no = self._paket_no
            govde += struct.pack(">H", no)
        self.gonder(paket((PUBLISH << 4) | (qos << 1) | int(retain), govde + yuk))

    def en_iyi_abonelik(self, konu: str) -> int | None:
        en = None
        for f, q in list(self.abonelikler.items()):
            if konu_eslesir(f, konu) and (en is None or q > en):
                en = q
        return en

    # -- kapatma
    def neden_ayarla(self, neden: str) -> None:
        with self._neden_kilit:
            if self.neden is None:
                self.neden = neden

    def kapat(self, neden: str) -> None:
        self.neden_ayarla(neden)
        for islem in (lambda: self.soket.shutdown(socket.SHUT_RDWR), self.soket.close):
            try:
                islem()
            except OSError:
                pass

    # -- okuma dongusu
    def _calis(self) -> None:
        ayr = Ayristirici()
        basla = son_alinan = time.monotonic()
        self.soket.settimeout(0.05)
        try:
            while self.neden is None:
                simdi = time.monotonic()
                if self.kayitli:
                    if self.keepalive and simdi - son_alinan > KEEPALIVE_CARPAN * self.keepalive:
                        self.neden_ayarla("keepalive")
                        break
                elif simdi - basla > BAGLANTI_ZAMAN_ASIMI:
                    self.neden_ayarla("red")
                    break
                try:
                    veri = self.soket.recv(65536)
                except socket.timeout:
                    continue
                except OSError:
                    self.neden_ayarla("kopus")
                    break
                if not veri:
                    self.neden_ayarla("kopus")
                    break
                ayr.besle(veri)
                while self.neden is None:
                    p = ayr.sonraki()
                    if p is None:
                        break
                    son_alinan = time.monotonic()
                    self._isle(*p)
        except (ProtokolHatasi, ValueError, IndexError, struct.error):
            self.neden_ayarla("protokol")
        finally:
            self._bitir()

    def _bitir(self) -> None:
        try:
            neden = self.neden or "kopus"
            self.kapat(neden)
            if self.kayitli:
                self.araci._baglanti_bitti(self, neden)
        finally:
            with self.araci.kosul:
                self.araci._tum.discard(self)
            self.kapali.set()

    # -- paketler
    def _isle(self, ilk: int, g: bytes) -> None:
        tur = ilk >> 4
        if not self.kayitli:
            if tur != CONNECT:
                raise ProtokolHatasi("ilk paket CONNECT degil")
            self._connect(g)
            return
        if tur == PUBLISH:
            self._publish(ilk, g)
        elif tur == SUBSCRIBE:
            self._subscribe(g)
        elif tur == UNSUBSCRIBE:
            self._unsubscribe(g)
        elif tur == PUBACK:
            self.araci._olay("puback", istemci=self.istemci_id, no=struct.unpack(">H", g[:2])[0])
        elif tur == PINGREQ:
            self.gonder(paket(PINGRESP << 4))
        elif tur == DISCONNECT:
            self.neden_ayarla("disconnect")
        else:
            raise ProtokolHatasi(f"desteklenmeyen paket turu {tur}")

    def _connect(self, g: bytes) -> None:
        ad, i = _dize_oku(g, 0)
        if i + 4 > len(g):
            raise ProtokolHatasi("CONNECT kisa")
        seviye, bayrak = g[i], g[i + 1]
        keepalive = struct.unpack(">H", g[i + 2:i + 4])[0]
        i += 4
        if ad != b"MQTT":
            raise ProtokolHatasi("protokol adi MQTT degil")
        if bayrak & 1:
            raise ProtokolHatasi("CONNECT ayrilmis bit 1")
        temiz = bool(bayrak & 2)
        cid_b, i = _dize_oku(g, i)
        will = None
        if bayrak & 4:
            wk, i = _dize_oku(g, i)
            wy, i = _dize_oku(g, i)
            will = {"konu": wk.decode("utf-8"), "yuk": wy, "qos": (bayrak >> 3) & 3,
                    "retain": bool(bayrak & 0x20)}
            if will["qos"] == 3:
                raise ProtokolHatasi("vasiyet QoS 3")
        elif bayrak & 0x38:
            raise ProtokolHatasi("vasiyet yok ama vasiyet bayraklari var")
        kul = par = None
        if bayrak & 0x80:
            b, i = _dize_oku(g, i)
            kul = b.decode("utf-8")
        if bayrak & 0x40:
            b, i = _dize_oku(g, i)
            par = b
        cid = cid_b.decode("utf-8")
        rc, rol = 0, "rw"
        if seviye != 4:
            rc = 1
        elif not cid and not temiz:
            rc = 2
        elif self.araci.kullanicilar:
            kayit = self.araci.kullanicilar.get(kul) if kul is not None else None
            if kayit is None or par is None or not hmac.compare_digest(par, kayit[0].encode("utf-8")):
                rc = 5
            else:
                rol = kayit[1]
        if not cid and not rc:
            cid = self.araci._yeni_kimlik()
        kayit_d = {"t": time.monotonic(), "istemci_id": cid, "keepalive": keepalive,
                   "temiz": temiz, "kullanici": kul, "sonuc": rc, "will": will is not None,
                   "will_konu": will["konu"] if will else None,
                   "will_yuk": will["yuk"] if will else None,
                   "will_qos": will["qos"] if will else None,
                   "will_retain": will["retain"] if will else None}
        with self.araci.kosul:
            self.araci.baglantilar.append(kayit_d)
        self.araci._olay("connect", istemci=cid, kullanici=kul, keepalive=keepalive,
                         sonuc=rc, will=kayit_d["will_konu"])
        if rc:
            self.gonder(paket(CONNACK << 4, bytes([0, rc])))
            self.neden_ayarla("red")
            return
        # ayni kimlikli eski baglanti: dusur (vasiyeti yayinlanir), bitmesini bekle
        with self.araci.kosul:
            eski = self.araci._istemciler.get(cid)
        if eski is not None and eski is not self:
            eski.kapat("takeover")
            eski.kapali.wait(2.0)
        self.istemci_id, self.kullanici, self.rol = cid, kul, rol
        self.keepalive, self.will = keepalive, will
        with self.araci.kosul:
            self.araci._istemciler[cid] = self
            self.kayitli = True
        self.gonder(paket(CONNACK << 4, bytes([0, 0])))

    def _publish(self, ilk: int, g: bytes) -> None:
        qos, retain = (ilk >> 1) & 3, bool(ilk & 1)
        konu_b, i = _dize_oku(g, 0)
        konu = konu_b.decode("utf-8")
        no = None
        if qos in (1, 2):
            no = struct.unpack(">H", g[i:i + 2])[0]
            i += 2
        yuk = g[i:]
        if qos >= 2:
            raise ProtokolHatasi("QoS 2 desteklenmiyor")
        if not konu_gecerli(konu):
            raise ProtokolHatasi("gecersiz konu")
        if self.rol != "rw":
            self.araci._olay("acl_red", istemci=self.istemci_id, kullanici=self.kullanici, konu=konu)
            self.neden_ayarla("acl")
            return
        if qos == 1:
            self.gonder(paket(PUBACK << 4, struct.pack(">H", no)))
        self.araci._olay("publish", istemci=self.istemci_id, konu=konu, yuk=yuk, qos=qos, retain=retain)
        self.araci._dagit(konu, yuk, qos, retain)

    def _subscribe(self, g: bytes) -> None:
        no = struct.unpack(">H", g[:2])[0]
        i, sonuclar, yeni = 2, [], []
        if i >= len(g):
            raise ProtokolHatasi("SUBSCRIBE bos")
        while i < len(g):
            f_b, i = _dize_oku(g, i)
            if i >= len(g):
                raise ProtokolHatasi("SUBSCRIBE istenen QoS eksik")
            q = g[i]
            i += 1
            f = f_b.decode("utf-8")
            if q > 2 or not filtre_gecerli(f):
                sonuclar.append(0x80)
                continue
            verilen = min(q, 1)
            self.abonelikler[f] = verilen
            sonuclar.append(verilen)
            yeni.append((f, verilen))
        self.gonder(paket(SUBACK << 4, struct.pack(">H", no) + bytes(sonuclar)))
        for f, verilen in yeni:
            self.araci._olay("abone", istemci=self.istemci_id, filtre=f, qos=verilen)
            with self.araci.kosul:
                eslesen = [(k, v) for k, v in self.araci.retained.items() if konu_eslesir(f, k)]
            for konu, (yuk, q) in eslesen:
                self.yayin_gonder(konu, yuk, min(q, verilen), True)

    def _unsubscribe(self, g: bytes) -> None:
        no = struct.unpack(">H", g[:2])[0]
        i = 2
        while i < len(g):
            f_b, i = _dize_oku(g, i)
            self.abonelikler.pop(f_b.decode("utf-8"), None)
        self.gonder(paket(UNSUBACK << 4, struct.pack(">H", no)))


# ── aracı ────────────────────────────────────────────────────────────────
class SahteAraci:
    def __init__(self, host: str = "0.0.0.0", port: int = 0,
                 kullanicilar: dict[str, tuple[str, str]] | None = None, gunluk=None) -> None:
        for kul, (_, rol) in (kullanicilar or {}).items():
            if rol not in ("rw", "r"):
                raise ValueError(f"{kul}: rol 'rw' ya da 'r' olmali")
        self.host, self.port = host, port
        self.kullanicilar = dict(kullanicilar or {})        # bos = herkes (rw)
        self.gunluk = gunluk                                # her olayda cagrilir (CLI)
        self.kosul = threading.Condition()
        self.baglantilar: list[dict] = []
        self.olaylar: list[dict] = []
        self.retained: dict[str, tuple[bytes, int]] = {}
        self._istemciler: dict[str, _Baglanti] = {}
        self._tum: set[_Baglanti] = set()
        self._dinleyici: socket.socket | None = None
        self._kabul_thread: threading.Thread | None = None
        self._sayac = 0

    # -- yasam dongusu
    def start(self) -> "SahteAraci":
        self._dinle_ac()
        return self

    def _dinle_ac(self, bekle: float = 5.0) -> None:
        son = time.monotonic() + bekle
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name != "nt":
                # Windows'ta SO_REUSEADDR AKTIF dinleyen portu da calmaya izin verir (CLAUDE.md
                # "Windows tuzagi"); orada hic verilmez, TIME_WAIT bind'i zaten engellemez.
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((self.host, self.port))
                break
            except OSError:
                s.close()
                if time.monotonic() >= son:
                    raise
                time.sleep(0.1)
        s.listen(32)
        self.port = s.getsockname()[1]
        with self.kosul:
            self._dinleyici = s
        t = threading.Thread(target=self._kabul, args=(s,), daemon=True)
        self._kabul_thread = t
        t.start()

    def _kabul(self, dinleyici: socket.socket) -> None:
        dinleyici.settimeout(0.1)
        while self._dinleyici is dinleyici:
            try:
                s, adres = dinleyici.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
            b = _Baglanti(self, s, adres)
            with self.kosul:
                self._tum.add(b)
            b.thread.start()

    def kapali_tut(self) -> None:
        """Aracı kesintisi: dinlemeyi birak, butun istemcileri dusur (vasiyet YAYINLANMAZ —
        aracı kendisi yok). Retained deposu korunur. `ac()` ayni portta geri getirir."""
        with self.kosul:
            s, self._dinleyici = self._dinleyici, None
        if s is not None:
            try:
                s.close()
            except OSError:
                pass
        if self._kabul_thread is not None:
            self._kabul_thread.join(2.0)
            self._kabul_thread = None
        with self.kosul:
            bekleyenler = list(self._tum)
        for b in bekleyenler:
            b.kapat("sunucu_kapali")
        for b in bekleyenler:
            b.kapali.wait(2.0)
        if s is not None:
            self._olay("arac_kapali")

    def ac(self) -> None:
        """`kapali_tut()`tan sonra AYNI portta yeniden dinle."""
        with self.kosul:
            acik = self._dinleyici is not None
        if not acik:
            self._dinle_ac()
            self._olay("arac_acik")

    def stop(self) -> None:
        self.kapali_tut()

    def __enter__(self) -> "SahteAraci":
        return self.start()

    def __exit__(self, *a) -> None:
        self.stop()

    # -- olay gunlugu
    def _olay(self, tur: str, **alanlar) -> dict:
        o = {"t": time.monotonic(), "tur": tur, **alanlar}
        with self.kosul:
            o["i"] = len(self.olaylar)
            self.olaylar.append(o)
            self.kosul.notify_all()
        if self.gunluk is not None:
            try:
                self.gunluk(o)
            except Exception:                              # noqa: BLE001
                pass
        return o

    def bekle(self, kosul, zaman_asimi: float = 10.0, baslangic: int = 0) -> dict | None:
        """`baslangic` sirasindan sonraki ilk olay: `kosul(olay)` dogruysa dondur; zaman asimi: None."""
        son = time.monotonic() + zaman_asimi
        with self.kosul:
            i = baslangic
            while True:
                while i < len(self.olaylar):
                    if kosul(self.olaylar[i]):
                        return self.olaylar[i]
                    i += 1
                kalan = son - time.monotonic()
                if kalan <= 0:
                    return None
                self.kosul.wait(kalan)

    def olay_bekle(self, tur: str, zaman_asimi: float = 10.0, baslangic: int = 0, **alanlar) -> dict | None:
        return self.bekle(lambda o: o["tur"] == tur and all(o.get(k) == v for k, v in alanlar.items()),
                          zaman_asimi, baslangic)

    def olaylar_sec(self, tur: str, baslangic: int = 0, **alanlar) -> list[dict]:
        with self.kosul:
            return [o for o in self.olaylar[baslangic:]
                    if o["tur"] == tur and all(o.get(k) == v for k, v in alanlar.items())]

    def retained_al(self, konu: str) -> tuple[bytes, int] | None:
        with self.kosul:
            return self.retained.get(konu)

    def bagli_istemciler(self) -> list[str]:
        with self.kosul:
            return sorted(self._istemciler)

    # -- dagitim
    def _yeni_kimlik(self) -> str:
        with self.kosul:
            self._sayac += 1
            return f"sahte-{self._sayac}"

    def _dagit(self, konu: str, yuk: bytes, qos: int, retain: bool) -> None:
        with self.kosul:
            if retain:
                if yuk:
                    self.retained[konu] = (yuk, qos)
                else:
                    self.retained.pop(konu, None)
            hedefler = [(b, b.en_iyi_abonelik(konu)) for b in list(self._istemciler.values())]
        for b, q in hedefler:
            if q is not None:
                b.yayin_gonder(konu, yuk, min(qos, q), False)    # canli iletimde retain = 0

    def yayinla(self, konu: str, yuk: bytes, qos: int = 0, retain: bool = False) -> None:
        """Aracı kendisi yayinlar (sinama)."""
        self._olay("arac_yayin", konu=konu, yuk=yuk, qos=qos, retain=retain)
        self._dagit(konu, yuk, qos, retain)

    def _baglanti_bitti(self, b: _Baglanti, neden: str) -> None:
        with self.kosul:
            if self._istemciler.get(b.istemci_id) is b:
                del self._istemciler[b.istemci_id]
        self._olay("disconnect", istemci=b.istemci_id, neden=neden)
        if b.will is not None and neden not in ("disconnect", "sunucu_kapali"):
            w = b.will
            self._olay("will_published", istemci=b.istemci_id, neden=neden, konu=w["konu"],
                       yuk=w["yuk"], qos=w["qos"], retain=w["retain"])
            self._dagit(w["konu"], w["yuk"], w["qos"], w["retain"])


# ── komut satiri ─────────────────────────────────────────────────────────
def kullanici_coz(spec: str) -> tuple[str, tuple[str, str]]:
    """'ad:parola:rw' (rol 'r' ya da 'rw'; yoksa rw). Parolada ':' olabilir."""
    ad, ayrac, kalan = spec.partition(":")
    if not ad or not ayrac:
        raise ValueError("kullanici 'ad:parola[:rol]' olmali")
    parola, ayrac2, rol = kalan.rpartition(":")
    if not ayrac2 or rol not in ("r", "rw"):
        parola, rol = kalan, "rw"
    return ad, (parola, rol)


def olay_satiri(o: dict, t0: float) -> str:
    alanlar = []
    for k, v in o.items():
        if k in ("t", "i", "tur"):
            continue
        if isinstance(v, (bytes, bytearray)):
            v = f"<{len(v)} bayt>"                       # icerik sifreli zarf; basilmaz
        alanlar.append(f"{k}={v}")
    return f"[{o['t'] - t0:9.3f}] {o['tur']:<14s} " + " ".join(alanlar)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Sahte MQTT 3.1.1 araci (tezgah sinamasi, duz TCP)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--kullanici", action="append", default=[], metavar="AD:PAROLA[:rw|r]")
    a = ap.parse_args()
    try:
        kullanicilar = dict(kullanici_coz(s) for s in a.kullanici)
    except ValueError as h:
        print(f"HATA: {h}", file=sys.stderr)
        return 2
    t0 = time.monotonic()
    araci = SahteAraci(a.host, a.port, kullanicilar, gunluk=lambda o: print(olay_satiri(o, t0), flush=True))
    araci.start()
    print(f"dinleniyor {a.host}:{araci.port} (duz TCP — TLS YOK), "
          f"{len(kullanicilar)} kullanici" + ("" if kullanicilar else " (kimliksiz herkes)"), flush=True)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        araci.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
