# -*- coding: utf-8 -*-
"""1E — asgari MQTT 3.1.1 istemcisi (yalniz stdlib: socket + ssl).

    c = Istemci("host", 8883, True, "kullanici", "parola", keepalive=30)
    c.baglan()                              # TLS: ssl.create_default_context() (sertifika + ad denetimi)
    c.abone("ok/<onek>/#", qos=1)
    while True:
        m = c.bekle(1.0)                    # (konu, yuk, retain) | None
    c.yayinla("konu", b"yuk", qos=1, retain=True)
    c.kapat()

Kapsam: CONNECT/CONNACK · SUBSCRIBE/SUBACK · PUBLISH QoS 0/1 (alinan ve gonderilen) ·
PUBACK · PINGREQ/PINGRESP · DISCONNECT. YOK: QoS 2, MQTT 5, vasiyet, oturum surdurme.

Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K12). Tezgah ve alt proje 4 bunu kullanir.

Dayaniklilik:
  - Alinan baytlar bir tampona yazilir, paket ancak TAM gelince ayrilir (`Ayristirici`):
    zaman asimi ya da parcali okuma paketin ortasinda akisi KAYDIRMAZ.
  - `abone`/`yayinla` yanit beklerken araya giren PUBLISH'ler kuyruga alinir (kaybolmaz,
    QoS 1 ise PUBACK hemen gider); `bekle` once kuyrugu bosaltir.
  - Keepalive: bos kalinan sure keepalive/2'yi gecince PINGREQ gider (aracinin 1.5x
    toleransi hic zorlanmaz). PINGREQ'ten sonra `keepalive` saniye hicbir paket
    gelmezse BaglantiKoptu. UYARI: Keepalive yalniz `bekle`/`abone`/`yayinla` calisirken
    islenir: cagiran `bekle`'yi duzenli (<= keepalive/2) cagirmali.
"""
from __future__ import annotations

import collections
import secrets
import socket
import ssl
import struct
import time

# Paket turleri (ust 4 bit)
CONNECT, CONNACK, PUBLISH, PUBACK = 1, 2, 3, 4
SUBSCRIBE, SUBACK, PINGREQ, PINGRESP, DISCONNECT = 8, 9, 12, 13, 14

UZUNLUK_AZAMI = 268_435_455                 # 4 bayt "kalan uzunluk" siniri
_CONNACK_METIN = {
    1: "protokol surumu kabul edilmedi",
    2: "istemci kimligi reddedildi",
    3: "araci kullanilamiyor",
    4: "kullanici adi ya da parola hatali",
    5: "yetkisiz (kullanici bu islem icin yetkili degil)",
}


class MqttHata(Exception):
    """Protokol ya da araci kaynakli hata."""


class BaglantiKoptu(MqttHata):
    """Soket kapandi, okunamadi ya da PINGREQ yanitsiz kaldi."""


class BaglantiReddedildi(MqttHata):
    """CONNACK donus kodu != 0. `kod` 1..5 (4 = hatali kimlik, 5 = yetkisiz)."""

    def __init__(self, kod: int):
        self.kod = kod
        super().__init__(f"baglanti reddedildi (kod {kod}): "
                         f"{_CONNACK_METIN.get(kod, 'bilinmeyen sebep')}")


# ── saf cekirdek ─────────────────────────────────────────────────────────
def uzunluk_kodla(n: int) -> bytes:
    """MQTT 'kalan uzunluk': 7 bit/bayt, ust bit = devam; en cok 4 bayt (<= 268 435 455)."""
    if not 0 <= n <= UZUNLUK_AZAMI:
        raise ValueError(f"kalan uzunluk 0..{UZUNLUK_AZAMI} olmali ({n})")
    cikis = bytearray()
    while True:
        b, n = n % 128, n // 128
        cikis.append(b | 0x80 if n else b)
        if not n:
            return bytes(cikis)


def uzunluk_coz(veri: bytes) -> tuple[int, int] | None:
    """`veri` bir 'kalan uzunluk' ile basliyorsa (deger, tuketilen bayt); henuz tam degilse
    None; 4 baytta bitmiyorsa MqttHata."""
    deger, carpan = 0, 1
    for i, b in enumerate(veri[:4]):
        deger += (b & 0x7F) * carpan
        if not b & 0x80:
            return deger, i + 1
        carpan *= 128
    if len(veri) >= 4:
        raise MqttHata("bicimsiz kalan uzunluk (4 bayttan uzun)")
    return None


def dize(metin: str) -> bytes:
    """MQTT UTF-8 dizesi: 2 bayt uzunluk + UTF-8."""
    b = metin.encode("utf-8")
    if len(b) > 0xFFFF:
        raise ValueError("MQTT dizesi 65535 bayttan uzun")
    return struct.pack(">H", len(b)) + b


def paket(ilk_bayt: int, govde: bytes = b"") -> bytes:
    return bytes([ilk_bayt]) + uzunluk_kodla(len(govde)) + govde


class Ayristirici:
    """Akistan paket ayirir: `besle(baytlar)` ile ver, `sonraki()` tam paketi
    (ilk_bayt, govde) dondurur; tam gelmediyse None (parcali okumalar guvenle birikir)."""

    def __init__(self) -> None:
        self._tampon = bytearray()

    def besle(self, veri: bytes) -> None:
        self._tampon += veri

    def sonraki(self) -> tuple[int, bytes] | None:
        t = self._tampon
        if len(t) < 2:
            return None
        u = uzunluk_coz(bytes(t[1:5]))
        if u is None:
            return None
        deger, n = u
        son = 1 + n + deger
        if len(t) < son:
            return None
        ilk, govde = t[0], bytes(t[1 + n:son])
        del t[:son]
        return ilk, govde

    def bekleyen(self) -> int:
        return len(self._tampon)


def publish_coz(ilk: int, govde: bytes) -> tuple[str, bytes, bool, int, int | None]:
    """PUBLISH paketini coz: (konu, yuk, retain, qos, paket_no | None)."""
    qos, retain = (ilk >> 1) & 3, bool(ilk & 1)
    if qos == 3:
        raise MqttHata("gecersiz QoS 3")
    if len(govde) < 2:
        raise MqttHata("PUBLISH kisa")
    n = struct.unpack(">H", govde[:2])[0]
    if len(govde) < 2 + n:
        raise MqttHata("PUBLISH konusu eksik")
    try:
        konu = govde[2:2 + n].decode("utf-8")
    except UnicodeDecodeError as h:
        raise MqttHata("PUBLISH konusu UTF-8 degil") from h
    i, no = 2 + n, None
    if qos:
        if len(govde) < i + 2:
            raise MqttHata("PUBLISH paket numarasi eksik")
        no = struct.unpack(">H", govde[i:i + 2])[0]
        i += 2
    return konu, govde[i:], retain, qos, no


# ── istemci ──────────────────────────────────────────────────────────────
class Istemci:
    def __init__(self, host: str, port: int | None = None, tls: bool = True,
                 kullanici: str | None = None, parola: str | None = None,
                 istemci_id: str | None = None, keepalive: int = 30,
                 zaman_asimi: float = 10.0, ssl_baglam: ssl.SSLContext | None = None,
                 temiz_oturum: bool = True):
        if parola is not None and kullanici is None:
            raise ValueError("MQTT 3.1.1: parola kullanici adi olmadan gonderilemez")
        if not 0 <= keepalive <= 0xFFFF:
            raise ValueError("keepalive 0..65535 s")
        self.host = host
        self.port = port if port is not None else (8883 if tls else 1883)
        self.tls = tls
        self.kullanici, self.parola = kullanici, parola
        self.istemci_id = istemci_id if istemci_id is not None else f"okb-{secrets.token_hex(4)}"
        self.keepalive = keepalive
        self.zaman_asimi = zaman_asimi              # CONNACK / SUBACK / PUBACK bekleme siniri
        self.temiz_oturum = temiz_oturum
        self._ssl_baglam = ssl_baglam
        self._soket: socket.socket | None = None
        self._ayr = Ayristirici()
        self._gelen: collections.deque = collections.deque()    # (konu, yuk, retain)
        self._puback: set[int] = set()
        self._paket_no = 0
        self._son_giden = 0.0                       # monotonic
        self._ping_zamani: float | None = None      # yanit bekleyen PINGREQ'in gonderilis zamani

    # -- baglanti ---------------------------------------------------------
    def baglan(self, zaman_asimi: float | None = None) -> None:
        zaman_asimi = self.zaman_asimi if zaman_asimi is None else zaman_asimi
        self.kapat(nazik=False)
        ham = socket.create_connection((self.host, self.port), timeout=zaman_asimi)
        try:
            ham.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if self.tls:
                baglam = self._ssl_baglam or ssl.create_default_context()
                self._soket = baglam.wrap_socket(ham, server_hostname=self.host)
            else:
                self._soket = ham
            self._ayr, self._gelen, self._puback = Ayristirici(), collections.deque(), set()
            self._ping_zamani = None
            self._gonder(self._connect_paketi())
            p = self._paket_al(time.monotonic() + zaman_asimi)
            if p is None:
                raise TimeoutError("CONNACK gelmedi")
            ilk, govde = p
            if ilk >> 4 != CONNACK or len(govde) != 2:
                raise MqttHata("CONNACK beklenirken baska paket geldi")
            if govde[1] != 0:
                raise BaglantiReddedildi(govde[1])
        except BaseException:
            self.kapat(nazik=False)
            ham.close()
            raise

    def _connect_paketi(self) -> bytes:
        bayrak = 0x02 if self.temiz_oturum else 0
        yuk = dize(self.istemci_id)
        if self.kullanici is not None:
            bayrak |= 0x80
            yuk += dize(self.kullanici)
        if self.parola is not None:
            bayrak |= 0x40
            yuk += dize(self.parola)
        govde = dize("MQTT") + bytes([4, bayrak]) + struct.pack(">H", self.keepalive) + yuk
        return paket(CONNECT << 4, govde)

    def kapat(self, nazik: bool = True) -> None:
        s, self._soket = self._soket, None
        if s is None:
            return
        try:
            if nazik:
                s.settimeout(2.0)
                s.sendall(paket(DISCONNECT << 4))
        except OSError:
            pass
        finally:
            try:
                s.close()
            except OSError:
                pass

    def __enter__(self) -> "Istemci":
        self.baglan()
        return self

    def __exit__(self, *a) -> None:
        self.kapat()

    # -- dusuk seviye -----------------------------------------------------
    def _gonder(self, veri: bytes) -> None:
        if self._soket is None:
            raise BaglantiKoptu("baglanti yok")
        try:
            self._soket.settimeout(self.zaman_asimi)
            self._soket.sendall(veri)
        except OSError as h:
            self.kapat(nazik=False)                 # yarim yazilmis akis: kurtarilamaz
            raise BaglantiKoptu(f"gonderilemedi: {h}") from h
        self._son_giden = time.monotonic()

    def _yeni_paket_no(self) -> int:
        self._paket_no = self._paket_no % 0xFFFF + 1          # 1..65535, 0 yok
        return self._paket_no

    def _ping_araligi(self) -> float:
        return self.keepalive / 2.0

    def _sonraki_keepalive_olayi(self) -> float | None:
        """Bir sonraki zamanlanmis olay (monotonic): PINGREQ gonder ya da baglantiyi olu say."""
        if not self.keepalive:
            return None
        if self._ping_zamani is not None:
            return self._ping_zamani + self.keepalive
        return self._son_giden + self._ping_araligi()

    def _keepalive_yurut(self, simdi: float) -> None:
        olay = self._sonraki_keepalive_olayi()
        if olay is None or simdi < olay:
            return
        if self._ping_zamani is not None:
            self.kapat(nazik=False)
            raise BaglantiKoptu("PINGREQ yanitsiz: aracidan paket gelmiyor")
        self._gonder(paket(PINGREQ << 4))
        self._ping_zamani = simdi

    def _paket_al(self, son: float) -> tuple[int, bytes] | None:
        """Siradaki TAM paket; `son` (monotonic) gecerse None. Keepalive'i de yurutur."""
        while True:
            p = self._ayr.sonraki()
            if p is not None:
                self._ping_zamani = None            # herhangi bir paket = araci yasiyor
                return p
            simdi = time.monotonic()
            if self._soket is None:
                raise BaglantiKoptu("baglanti yok")
            self._keepalive_yurut(simdi)
            bekle = son - simdi
            olay = self._sonraki_keepalive_olayi()
            if olay is not None:
                bekle = min(bekle, olay - simdi)
            if son - simdi <= 0:
                return None
            try:
                self._soket.settimeout(max(bekle, 0.001))
                veri = self._soket.recv(65536)
            except (TimeoutError, ssl.SSLWantReadError):
                continue
            except OSError as h:
                self.kapat(nazik=False)
                raise BaglantiKoptu(f"okunamadi: {h}") from h
            if not veri:
                self.kapat(nazik=False)
                raise BaglantiKoptu("araci baglantiyi kapatti")
            self._ayr.besle(veri)

    def _isle(self, ilk: int, govde: bytes) -> None:
        """Kimsenin beklemedigi paketler: PUBLISH kuyruga + PUBACK, PUBACK kaydi, gerisi yutulur."""
        tur = ilk >> 4
        if tur == PUBLISH:
            konu, yuk, retain, qos, no = publish_coz(ilk, govde)
            if qos == 2:
                raise MqttHata("QoS 2 PUBLISH geldi; istemci yalniz QoS 0/1 destekler")
            if qos == 1:
                self._gonder(paket(PUBACK << 4, struct.pack(">H", no)))
            self._gelen.append((konu, yuk, retain))
        elif tur == PUBACK and len(govde) >= 2:
            self._puback.add(struct.unpack(">H", govde[:2])[0])
        # PINGRESP, bekleyen olmayan SUBACK vb.: yutulur (canlilik _paket_al'da isaretlendi)

    # -- genel arayuz -----------------------------------------------------
    def abone(self, konu_filtresi: str, qos: int = 1) -> int:
        """SUBSCRIBE + SUBACK; verilen QoS'u dondurur. Arada gelen PUBLISH'ler kuyruga girer."""
        if qos not in (0, 1):
            raise ValueError("qos 0 ya da 1")
        no = self._yeni_paket_no()
        self._gonder(paket((SUBSCRIBE << 4) | 0x02,
                           struct.pack(">H", no) + dize(konu_filtresi) + bytes([qos])))
        son = time.monotonic() + self.zaman_asimi
        while True:
            p = self._paket_al(son)
            if p is None:
                raise TimeoutError("SUBACK gelmedi")
            ilk, govde = p
            if ilk >> 4 == SUBACK and len(govde) >= 3 and struct.unpack(">H", govde[:2])[0] == no:
                if govde[2] == 0x80:
                    raise MqttHata(f"abonelik reddedildi: {konu_filtresi!r}")
                return govde[2]
            self._isle(ilk, govde)

    def yayinla(self, konu: str, yuk: bytes, qos: int = 0, retain: bool = False) -> None:
        """PUBLISH; qos=1 ise PUBACK gelene dek bekler (TimeoutError)."""
        if qos not in (0, 1):
            raise ValueError("qos 0 ya da 1")
        ilk = (PUBLISH << 4) | (qos << 1) | int(bool(retain))
        govde = dize(konu)
        no = None
        if qos:
            no = self._yeni_paket_no()
            govde += struct.pack(">H", no)
        self._gonder(paket(ilk, govde + bytes(yuk)))
        if not qos:
            return
        son = time.monotonic() + self.zaman_asimi
        while no not in self._puback:
            p = self._paket_al(son)
            if p is None:
                raise TimeoutError("PUBACK gelmedi")
            self._isle(*p)
        self._puback.discard(no)

    def bekle(self, zaman_asimi: float = 1.0) -> tuple[str, bytes, bool] | None:
        """Siradaki PUBLISH: (konu, yuk, retain); `zaman_asimi` s icinde yoksa None.
        Bu sirada keepalive yurutulur ve QoS 1 PUBLISH'lere PUBACK gonderilir."""
        son = time.monotonic() + max(zaman_asimi, 0.0)
        while True:
            if self._gelen:
                return self._gelen.popleft()
            p = self._paket_al(son)
            if p is None:
                return None
            self._isle(*p)
