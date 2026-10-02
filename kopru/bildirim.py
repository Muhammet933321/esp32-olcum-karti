# -*- coding: utf-8 -*-
"""1E — MQTT bildirimleri: zarf bicimi + PC dinleyicisi (yalniz stdlib).

    python bildirim.py dinle --host olcum.local --cihaz <cihaz dosyasi>
        eslesmis cihazla kartin /bildirim/bilgi'sini al, araciya baglan, ok/<onek>/#'e abone ol,
        cozulen mesajlari zaman damgasiyla yaz.
    python bildirim.py dinle --uri mqtts://host:8883 --kullanici u --onek <hex32> --anahtar-dosya f
        elle kullanim (parola sorulur, yankilanmaz).

Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K4, K5, K10, K12). Bu dosyanin zarf
bolumu kartin `bildirim.h`'siyle BIREBIR ayni baytlari uretir/okur.

Zarf (K5):
    bayt 0..3   "OKB1"
    bayt 4..15  nonce (12 B, rastgele)
    bayt 16..   ChaCha20-Poly1305 sifreli metin, son 16 B etiket
    AAD         konu adinin UTF-8 baytlari
    duz metin   kompakt JSON (UTF-8)

/bildirim/bilgi yaniti (K10): ayni zarf, anahtar = cihaz anahtari K,
AAD = "OK1-bildirim\\n<kimlik>\\n<n>", duz metin {"u","k","p","o","a"}.

Parola ve anahtar HICBIR cikti/hata mesajina yazilmaz.
"""
from __future__ import annotations

import argparse
import datetime
import getpass
import json
import re
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import chacha
import mqtt_istemci

SIHIR = b"OKB1"
NONCE_UZUNLUK = chacha.NONCE_UZUNLUK
ETIKET_UZUNLUK = chacha.ETIKET_UZUNLUK
ZARF_EN_AZ = len(SIHIR) + NONCE_UZUNLUK + ETIKET_UZUNLUK
ANAHTAR_UZUNLUK = chacha.ANAHTAR_UZUNLUK
BILGI_YOLU = "/bildirim/bilgi"
_ONEK_RE = re.compile(r"[0-9a-f]{32}")
_ANAHTAR_HEX_RE = re.compile(r"[0-9a-fA-F]{64}")
_URI_KURALLARI = {"mqtt": (1883, False), "tcp": (1883, False),
                  "mqtts": (8883, True), "ssl": (8883, True)}


# ── zarf ─────────────────────────────────────────────────────────────────
def _anahtar_denetle(anahtar: bytes) -> None:
    if not isinstance(anahtar, (bytes, bytearray)) or len(anahtar) != ANAHTAR_UZUNLUK:
        raise ValueError(f"bildirim anahtari {ANAHTAR_UZUNLUK} bayt olmali")


def zarf_kur(anahtar: bytes, konu: str, icerik: dict, nonce: bytes | None = None) -> bytes:
    """Karttaki zarf bicimi: "OKB1" + nonce + sifreli metin + etiket; AAD = konu (UTF-8).
    `nonce` yalniz sinama icin verilir; bos birakilirsa rastgele uretilir."""
    _anahtar_denetle(anahtar)
    if nonce is None:
        nonce = secrets.token_bytes(NONCE_UZUNLUK)
    elif len(nonce) != NONCE_UZUNLUK:
        raise ValueError(f"nonce {NONCE_UZUNLUK} bayt olmali")
    duz = json.dumps(icerik, ensure_ascii=False, separators=(",", ":"),
                     allow_nan=False).encode("utf-8")
    return SIHIR + bytes(nonce) + chacha.sifrele(anahtar, nonce, duz, konu.encode("utf-8"))


def _sonlu_degil(ad: str):
    raise ValueError(f"zarf icerigi sonlu olmayan sayi ({ad}) tasiyor")


def _zarf_coz(anahtar: bytes, aad: bytes, veri: bytes) -> dict:
    _anahtar_denetle(anahtar)
    veri = bytes(veri)
    if len(veri) < ZARF_EN_AZ:
        raise ValueError(f"zarf cok kisa ({len(veri)} < {ZARF_EN_AZ} bayt)")
    if veri[:len(SIHIR)] != SIHIR:
        raise ValueError("zarf sihri 'OKB1' degil")
    nonce = veri[len(SIHIR):len(SIHIR) + NONCE_UZUNLUK]
    duz = chacha.coz(anahtar, nonce, veri[len(SIHIR) + NONCE_UZUNLUK:], aad)   # etiket tutmazsa ValueError
    icerik = json.loads(duz.decode("utf-8"),        # UnicodeDecodeError/JSONDecodeError de ValueError
                        parse_constant=_sonlu_degil)   # S7: NaN/Infinity -> ValueError (JS gibi)
    if not isinstance(icerik, dict):
        raise ValueError("zarf icerigi JSON nesnesi degil")
    return icerik


def zarf_ac(anahtar: bytes, konu: str, veri: bytes) -> dict:
    """Zarfi ac. Yanlis sihir / kisa / etiket tutmuyor (yanlis anahtar, bozuk veri,
    YANLIS KONU) / JSON bozuk -> ValueError."""
    return _zarf_coz(anahtar, konu.encode("utf-8"), veri)


# ── /bildirim/bilgi ──────────────────────────────────────────────────────
def bilgi_aad(kimlik: str, n: int) -> bytes:
    return f"OK1-bildirim\n{kimlik}\n{n}".encode("utf-8")


def bilgi_coz(K: bytes, kimlik: str, n: int, govde: bytes) -> dict:
    """Kartin /bildirim/bilgi yanitini coz (anahtar = cihaz anahtari K). Donus:
    {uri, kullanici, parola, onek, anahtar(bytes)}. Bicim hatasi -> ValueError."""
    d = _zarf_coz(K, bilgi_aad(kimlik, n), govde)
    for alan in ("u", "k", "p", "o", "a"):
        if not isinstance(d.get(alan), str):
            raise ValueError(f"bilgide '{alan}' alani yok ya da metin degil")
    if not d["u"]:
        raise ValueError("bilgide araci adresi bos")
    if not _ONEK_RE.fullmatch(d["o"]):
        raise ValueError("onek 32 kucuk harfli hex olmali")
    if not _ANAHTAR_HEX_RE.fullmatch(d["a"]):
        raise ValueError("bildirim anahtari 64 hex olmali")
    return {"uri": d["u"], "kullanici": d["k"], "parola": d["p"], "onek": d["o"],
            "anahtar": bytes.fromhex(d["a"])}


def bilgi_al(cihaz, taban: str) -> dict:
    """Eslesmis cihazla imzali GET /bildirim/bilgi, sonra bilgi_coz."""
    import imza
    with imza.ac(cihaz, taban, "GET", BILGI_YOLU) as y:
        govde = y.read()
    return bilgi_coz(cihaz.K, cihaz.kimlik, cihaz.n, govde)


# ── dinleyici ────────────────────────────────────────────────────────────
def uri_coz(uri: str) -> tuple[str, int, bool]:
    """mqtt://h[:1883] | mqtts://h[:8883] (tcp/ssl takma adlari) -> (host, port, tls)."""
    u = urlsplit(uri)
    if u.scheme not in _URI_KURALLARI or not u.hostname:
        raise ValueError("araci adresi mqtt://ana:port ya da mqtts://ana:port olmali")
    varsayilan, tls = _URI_KURALLARI[u.scheme]
    return u.hostname, u.port or varsayilan, tls


def onek_denetle(onek: str) -> str:
    if not _ONEK_RE.fullmatch(onek):
        raise ValueError("onek 32 kucuk harfli hex olmali")
    return onek


def anahtar_oku(dosya) -> bytes:
    """Dosyada ham 32 bayt YA DA 64 hex karakter (bosluk/satir sonu serbest)."""
    ham = Path(dosya).read_bytes()
    if len(ham) == ANAHTAR_UZUNLUK:
        return ham
    metin = ham.decode("ascii", "replace").strip()
    if _ANAHTAR_HEX_RE.fullmatch(metin):
        return bytes.fromhex(metin)
    raise ValueError("anahtar dosyasi 32 ham bayt ya da 64 hex karakter icermeli")


def _damga() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def mesaj_satiri(anahtar: bytes, onek: str, konu: str, yuk: bytes, retain: bool,
                 zaman: str | None = None) -> str:
    """Bir mesaji tek satira cevir. Cozulemezse sebebi yazilir, yuk/anahtar ASLA."""
    ad = konu[len(f"ok/{onek}/"):] if konu.startswith(f"ok/{onek}/") else konu
    ek = " (retained)" if retain else ""
    try:
        govde = json.dumps(zarf_ac(anahtar, konu, yuk), ensure_ascii=False, separators=(",", ":"))
    except ValueError as h:
        govde = f"[COZULEMEDI: {h}]"
    return f"{zaman or _damga()}  {ad}{ek}  {govde}"


def dinle(uri: str, kullanici: str, parola: str, onek: str, anahtar: bytes,
          sure: float = 0.0, yaz=print, yeniden_bekleme: float = 3.0,
          zaman_asimi: float = 10.0, keepalive: int = 30) -> int:
    """ok/<onek>/# konularini dinle, her mesaji `yaz(satir)` ile bildir. `sure` > 0 ise o
    kadar saniye sonra biter (0 = Ctrl+C'ye dek). Baglanti kopunca yeniden dener;
    kimlik reddi (kod 4/5) yeniden denenmez, hata verir. Donus = alinan mesaj sayisi."""
    host, port, tls = uri_coz(uri)
    onek_denetle(onek)
    _anahtar_denetle(anahtar)
    filtre = f"ok/{onek}/#"
    son = time.monotonic() + sure if sure > 0 else None
    alinan = 0
    while True:
        c = mqtt_istemci.Istemci(host, port, tls, kullanici, parola, keepalive=keepalive,
                                 zaman_asimi=zaman_asimi)
        try:
            c.baglan()
            c.abone(filtre, 1)
            yaz(f"{_damga()}  baglandi {host}:{port} "
                f"{'TLS' if tls else 'DUZ BAGLANTI (TLS YOK!)'}  abone ok/<onek>/#")
            while son is None or time.monotonic() < son:
                kalan = 1.0 if son is None else min(1.0, son - time.monotonic())
                m = c.bekle(max(kalan, 0.0))
                if m is not None:
                    alinan += 1
                    yaz(mesaj_satiri(anahtar, onek, *m))
            return alinan
        except mqtt_istemci.BaglantiReddedildi as h:
            if h.kod in (4, 5):
                raise
            yaz(f"{_damga()}  {h}")
        except (mqtt_istemci.MqttHata, OSError, TimeoutError) as h:
            yaz(f"{_damga()}  baglanti sorunu: {h}")
        finally:
            c.kapat()
        if son is not None and time.monotonic() >= son:
            return alinan
        yaz(f"{_damga()}  {yeniden_bekleme:g} s sonra yeniden denenecek")
        time.sleep(yeniden_bekleme if son is None else
                   max(0.0, min(yeniden_bekleme, son - time.monotonic())))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Olcum karti MQTT bildirim dinleyicisi")
    alt = ap.add_subparsers(dest="komut", required=True)
    d = alt.add_parser("dinle", help="bildirimleri dinle ve coz")
    d.add_argument("--host", default="olcum.local", help="kart (eslesmis cihazla bilgi alinir)")
    d.add_argument("--cihaz", default=None, help="kopru/.cihaz altindaki cihaz dosyasi")
    d.add_argument("--uri", default=None, help="elle: mqtts://host:8883 (bilgi alinmaz)")
    d.add_argument("--kullanici", default=None)
    d.add_argument("--onek", default=None, help="32 hex konu oneki")
    d.add_argument("--anahtar-dosya", default=None, help="bildirim anahtari (32 ham bayt ya da 64 hex)")
    d.add_argument("--sure", type=float, default=0.0, help="saniye; 0 = Ctrl+C'ye dek")
    a = ap.parse_args()
    try:
        if a.uri:
            if not (a.kullanici and a.onek and a.anahtar_dosya):
                ap.error("--uri ile --kullanici, --onek ve --anahtar-dosya birlikte gerekir")
            parola = getpass.getpass("araci parolasi (ekrana yazilmaz): ")
            b = {"uri": a.uri, "kullanici": a.kullanici, "parola": parola,
                 "onek": a.onek, "anahtar": anahtar_oku(a.anahtar_dosya)}
        else:
            import imza
            cihaz = imza.cihaz_bul(dosya=a.cihaz)
            b = bilgi_al(cihaz, imza.taban_url(a.host))
        dinle(b["uri"], b["kullanici"], b["parola"], b["onek"], b["anahtar"], sure=a.sure)
    except KeyboardInterrupt:
        print("durduruldu")
        return 0
    except (ValueError, OSError, mqtt_istemci.MqttHata) as h:
        print(f"HATA: {h}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
