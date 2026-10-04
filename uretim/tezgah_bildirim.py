# -*- coding: utf-8 -*-
"""1E — MQTT BILDIRIMLERI GERCEK KARTTA (tezgah; zincirde DEGIL).

    python tezgah_bildirim.py --liste                  planlanan denetimleri yazar, DONANIMA DOKUNMAZ
    python tezgah_bildirim.py                          tam akis (= --bildirim); sifirlama tekrari 3
    python tezgah_bildirim.py --tekrar 10              vasiyet olcumu icin 10 RTS sifirlamasi
    python tezgah_bildirim.py --basladi 16 [--kip bagli|rastgele]
                                                       E7 (W5): GERCEK aracida `basladi` kaybi kartta mi
                                                       aracida mi (Q? olay sayaci; ayara DOKUNMAZ)
    secenekler: --port COM6  --http olcum.local  --ip <PC'nin LAN IP'si>  --ustune-yaz

Hicbir kullanici sirri GEREKMEZ: araci kimlik bilgileri her kosuda RASTGELE uretilir, kartin
NVS'ine yazilir, ASLA ekrana basilmaz ve temizlikte silinir. Araci gercek bulut aracisi (EMQX) degil, bu
bilgisayarda calisan `kopru/sahte_araci.py` (duz TCP; kart `mqtt://` ile baglanir — Q? bunu
"yalniz yerel sinama" diye uyarir). Kartin yazilimi A3-1E, `COM6`, web `olcum.local` olmali.

Ne olcer (kartin bildirim yolu GERCEKTEN calisiyor mu):
  - CONNECT alanlari (keepalive 5, vasiyet QoS1+retain, temiz oturum, istemci kimligi),
  - vasiyet ve durum zarflari PC'de cozulur, konu AAD'si baglidir,
  - Qt deneme olayi, `n` artar; /bildirim/bilgi (imzali) kartin ayariyla ayni,
  - RTS sifirlamasindan vasiyetin aracida yayinlanmasina kadar gecen sure (hedef <= 10 s, sinir 15 s),
  - araci kesintisi: kart <= 12 s'de duser, bekleyen olay kuyrukta tutulur, araci donunce <= 70 s'de
    yeniden baglanir ve olay ulasir,
  - E8 yanitsiz araci: sessiz araci (soket acik, yanit yok) ve kara delik vekili (iletmez, kapatmaz)
    -> kart <= 9.5 s'de kendisi kapatir, Q? hata=-7; Q? canlilik alanlari (tur, adim, ping/pong yasi),
  - bagliyken bos yigin >= 60 KB, Q? / SSE / seri konsolda parola YOK, /komut'tan Q 403.
Temizlik HER ZAMAN calisir (Q0, Qu/Qk/Qp/Qc/Qd bos, test cihazi Ex<n>, araci durdurulur).

Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K1-K12). Kart: kod/olcum-karti-a3/bildirim_esp.h.
⚠ Bu betik Windows Guvenlik Duvari kuralini DEGISTIRMEZ. Kart baglanamazsa ne yapilacagi yazilir.
"""
from __future__ import annotations

import argparse
import collections
import random
import re
import secrets
import socket
import statistics
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent

# Surum KAYNAKTAN (1F: elle yazilan "A3-1E" her surumde guncellenmek zorundaydi)
FW = re.search(r'#define KAYIT_FW_SURUM\s+"([^"]+)"',
               (Path(__file__).resolve().parent.parent / "kod" / "olcum-karti-a3" / "kayit_esp.h")
               .read_text(encoding="utf-8")).group(1)
KEEPALIVE_S = 5
VASIYET_HEDEF_S = 10.0
VASIYET_SINIR_S = 15.0
DUSME_SINIR_S = 12.0
YENIDEN_BAGLAN_SINIR_S = 70.0
RAM_SINIR = 60_000
# E8: yanitsiz aracıyi kart en gec 4 s (BLD_PING_MS: son yazmadan PINGREQ'e) + 5 s (BLD_PINGRESP_MS)
# = 9 s'de fark eder; +0.5 s gorev turu (select 50 ms) ve olcum payi. Susma ani son yazmadan
# hemen sonraya denk gelirse 9 s'yi birkac on ms gecebilir — bu yuzden 9.0 degil.
SESSIZ_TASARIM_S = 9.0
SESSIZ_SINIR_S = SESSIZ_TASARIM_S + 0.5

# (kod, metin) — `--liste` ve README gibi: gercek denetimlerle ayni sirada
PLAN = [
    ("ON", "Onkosul: Q? yanit veriyor (firmware A3-1E), kart STA kipinde, bildirim ayari BOS "
           "(doluysa durur, silmez; --ustune-yaz ile devam), E? ile kart kimligi"),
    ("C0", "USB eslestirmesi (Ep) + imzali GET /bildirim/bilgi: bildirim ayarlanmamisken 404"),
    ("A1", "Karta erisilebilir PC LAN IP'si (olcum.local'in IP'sine UDP-connect hilesi); sahte araci o IP'de "
           "rastgele portta kalkar, rastgele kart/cihaz kimlik bilgileriyle"),
    ("A2", "USB'den Qu mqtt://ip:port, Qk/Qp (kart), Qc/Qd (cihaz), Q1; Qv = QV gecti 0 (RFC 8439 oz sinamasi)"),
    ("C1", "Imzali /bildirim/bilgi coz: uri/cihaz kullanicisi/parola/onek/anahtar kartin ayariyla ayni; "
           "imzasiz 401; Q? onekin YALNIZ ilk 8 hanesini yazar"),
    ("B1", "Kart araciya baglanir (<= 45 s). Baglanamazsa: guvenlik duvari icin Turkce yonerge"),
    ("B2", "CONNECT alanlari: istemci kimligi ok-<kimlik>, keepalive 5, temiz oturum, kart kullanicisi, "
           "vasiyet QoS1 + retain, vasiyet konusu ok/<onek>/durum"),
    ("B3", "Vasiyet yuku zarf: konu AAD'iyle cozulur, tam {c:0, a:<acilis>}; a = durum mesajindaki a"),
    ("B4", "Durum: QoS0 + retained, c:1, f=A3-1E, a/t/k/o/y/d/e; PC abonesi alir; yanlis konu AAD'si ve "
           "yanlis anahtar COZMEZ"),
    ("D1", "Qt x2: deneme olaylari QoS1 + retain yok, n artar, kuyruk 0'a iner, Q? olay sayaci artar"),
    ("Y1", "Bagliyken QY dahili_bos >= 60000 bayt (K11)"),
    ("E1", "RTS sifirlamasi xN (--tekrar, varsayilan 3): kart yeniden acilir; vasiyet <= 15 s (hedef 10; "
           "sure yazilir); vasiyet c:0 + onceki acilis; PC abonesi canli c:0 gordu"),
    ("E2", "Sifirlamadan sonra kart yeniden baglanir; durum c:1 retained c:0'in USTUNE yazilir (yeni acilis "
           "> eski); `basladi` olayi n=1, devam alani, yeni acilis"),
    ("F1", "Araci kesintisi (kapali_tut): kart <= 12 s'de 'bagli' degil; vasiyet YAYINLANMAZ (araci yok)"),
    ("F2", "Kesintideyken Qt: Q? kuyruk >= 1"),
    ("F3", "ac() (ayni port): kart <= 70 s'de yeniden baglanir, bekleyen deneme olayi ULASIR, kuyruk 0, "
           "retained durum yeniden yazilir (c:1), PC abonesi kendiliginden geri baglanir"),
    ("S1", "E8 sessiz araci (TCP acik, yanit yok): kart <= 9.5 s'de baglantiyi kendisi kapatir, Q? hata=-7 "
           "(PINGRESP; -6 DEGIL), tur sayaci artmaya devam eder; konus() ile <= 70 s'de geri baglanir"),
    ("S2", "E8 kara delik vekili (iki yonde iletmez, kapatmaz): kart vekil uzerinden baglanir, kes() sonrasi "
           "<= 9.5 s'de kapatir, Q? hata=-7; aracı keepalive'la vasiyeti yayinlar; Qu eski adrese doner"),
    ("H1", "POST /komut 'Q?' -> 403 (Q yalniz USB)"),
    ("G1", "Seri konsol + /akis SSE metninde kart/cihaz parolasi, bildirim anahtari, tam onek YOK"),
    ("T1", "Temizlik (HER ZAMAN): Q0, Qu/Qk/Qp/Qc/Qd bos, Ex<n>, araci durur; E?/Q? baslangic durumuna doner"),
]

gecti = kaldi = 0
IMZA_KILIT = threading.RLock()
IM = BD = MQ = SA = KBAG = None            # `_moduller()` ile (import yan etkisiz kalsin)


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    gecti, kaldi = gecti + bool(kosul), kaldi + (not kosul)
    print(f"  [{'OK' if kosul else '!!'}] {ad}" + (f"   {ek}" if ek else ""))


def _moduller() -> None:
    global IM, BD, MQ, SA, KBAG
    if IM is not None:
        return
    yol = str(KOK / "kopru")
    if yol not in sys.path:
        sys.path.insert(0, yol)
    import bildirim
    import imza
    import kart_baglanti
    import mqtt_istemci
    import sahte_araci
    IM, BD, MQ, SA, KBAG = imza, bildirim, mqtt_istemci, sahte_araci, kart_baglanti


class Iptal(Exception):
    """Temiz durus: sebep kullaniciya yazilir, denetim sayilmaz."""


# ── seri yakalayici ──────────────────────────────────────────────────────
class SeriYakala:
    """SeriKart sarmalayici: GELEN her satir kaydedilir (parola sizinti denetimi icin).
    GIDEN komutlar kaydedilmez (Qp/Qd parolayi tasir)."""

    def __init__(self, k) -> None:
        self.k = k
        self.satirlar: list[str] = []

    @property
    def ad(self) -> str:
        return self.k.ad

    def satir_oku(self, zaman_asimi: float = 0.5):
        s = self.k.satir_oku(zaman_asimi)
        if s is not None:
            self.satirlar.append(s)
        return s

    def yaz(self, metin: str) -> None:
        self.k.yaz(metin)

    def sifirla(self, bekle: float = 0.35) -> bool:
        return self.k.sifirla(bekle)

    def metin(self) -> str:
        return "\n".join(self.satirlar)


def seri_bosalt(k, sn: float) -> None:
    son = time.monotonic() + sn
    while time.monotonic() < son:
        k.satir_oku(0.2)


def komut_satirlari(k, c: str, sn: float = 1.5) -> list[str]:
    k.yaz(c)
    satirlar, son = [], time.monotonic() + sn
    while time.monotonic() < son:
        s = k.satir_oku(0.2)
        if s is not None:
            satirlar.append(s)
    return satirlar


def q_oku(k, sn: float = 4.0) -> dict | None:
    """`Q?`: {acik, durum, hata, baglanti, yayin, olay, kuyruk, dusen, el_sikisma_ms, dahili_bos,
    dahili_en_az, qa: {uri, kart, kart_parola, cihaz, cihaz_parola, onek, anahtar}, uyarilar: [...]}.
    E8 firmware'i `Q` satirinin SONUNA tur, adim (metin), adim_yas, ping_yas, pong_yas ekler (-1 = hic);
    eski firmware'de bu anahtarlar YOKTUR (`.get` ile okuyun)."""
    k.yaz("Q?")
    son = time.monotonic() + sn
    d: dict = {"uyarilar": []}
    tam = None
    while time.monotonic() < son:
        s = k.satir_oku(0.2)
        if s is None:
            if tam is not None and time.monotonic() - tam > 0.4:
                break
            continue
        if s.startswith("Q acik="):
            d.update({a: int(b) for a, b in re.findall(r"(\w+)=(-?\d+)", s)})
            m = re.search(r"\badim=([a-z?]+)", s)              # E8: metin alan (yoksa eski firmware)
            if m:
                d["adim"] = m.group(1)
        elif s.startswith("QA "):
            d["qa"] = dict(re.findall(r"(\w+)=(\S+)", s[3:]))
        elif s.startswith("QY "):
            d.update({a: int(b) for a, b in re.findall(r"(\w+)=(-?\d+)", s)})
            tam = time.monotonic()
        elif s.startswith(("* Q:", "! Q:")):
            d["uyarilar"].append(s)
    return d if "acik" in d and "qa" in d and "dahili_bos" in d else None


def q_ayar(k, komut: str, onekler=("* Q:", "! Q:"), sn: float = 3.0) -> str:
    """Bir Q komutu gonder, ilk yanit satirini dondur ('' = yanit yok). Komut METNI ASLA basilmaz."""
    k.yaz(komut)
    son = time.monotonic() + sn
    while time.monotonic() < son:
        s = k.satir_oku(0.2)
        if s is not None and s.startswith(onekler):
            return s
    return ""


def yeni_acilis(k, sn: float = 30.0) -> bool:
    """Sifirlamadan sonra YENI acilis afisini ('Kayit: ...') bekle (tamponda kalmis eski satir
    'acildi' sayilmasin — tezgah_kayit.py ayni dersi aldi)."""
    son = time.monotonic() + sn
    while time.monotonic() < son:
        s = k.satir_oku(0.2)
        if s is not None and s.startswith("Kayit:"):
            return True
    return False


def lan_ip(host: str) -> tuple[str, str]:
    """(kartin IP'si, PC'nin o karta giden arayuzdeki IP'si). UDP connect paket yollamaz;
    yalnizca isletim sisteminin hangi arayuzu sececegini sorar."""
    kart_ip = socket.gethostbyname(host.rsplit(":", 1)[0] if host.count(":") == 1 else host)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((kart_ip, 9))
        return kart_ip, s.getsockname()[0]
    finally:
        s.close()


def ham_istek(taban: str, yol: str, basliklar: dict, yontem: str = "GET", govde=None,
              sn: float = 10.0) -> tuple[int, dict, str]:
    r = urllib.request.Request(taban + yol, data=govde, method=yontem, headers=basliklar)
    try:
        with urllib.request.urlopen(r, timeout=sn) as y:
            return y.status, dict(y.headers), y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as h:
        return h.code, dict(h.headers), h.read().decode("utf-8", "replace")


def imzali(c, taban: str, yontem: str, yol: str, args=(), govde: bytes = b"") -> tuple[int, bytes]:
    with IMZA_KILIT:
        try:
            with IM.ac(c, taban, yontem, yol, args, govde, 10.0) as y:
                return y.status, y.read()
        except urllib.error.HTTPError as h:
            return h.code, h.read()


# ── arka plan iplikleri ──────────────────────────────────────────────────
class SseYakala(threading.Thread):
    """/akis SSE metnini YAKALAR (kartin Serial aynasi): parola sizinti denetimi icin. Kart
    sifirlaninca kendiliginden yeniden baglanir."""

    def __init__(self, url_fn) -> None:
        super().__init__(daemon=True)
        self.url_fn = url_fn
        self.satirlar: list[str] = []
        self.kilit = threading.Lock()
        self.dur = threading.Event()
        self.ilk_veri = threading.Event()
        self.son_kod: int | None = None

    def run(self) -> None:
        while not self.dur.is_set():
            try:
                with urllib.request.urlopen(self.url_fn(), timeout=20) as y:
                    self.son_kod = 200
                    while not self.dur.is_set():
                        sat = y.readline()
                        if not sat:
                            break
                        s = sat.decode("utf-8", "replace")
                        if s.startswith("data:"):
                            self.ilk_veri.set()
                        with self.kilit:
                            self.satirlar.append(s)
            except urllib.error.HTTPError as h:
                self.son_kod = h.code
            except Exception:                                  # noqa: BLE001
                pass
            self.dur.wait(1.0)

    def metin(self) -> str:
        with self.kilit:
            return "".join(self.satirlar)


class Dinleyici(threading.Thread):
    """PC aboneligi: /bildirim/bilgi'den gelen bilgilerle (cihaz kullanicisi, salt-okur) araciya baglanir,
    ok/<onek>/#'e abone olur, her mesaji COZUP kaydeder; kopunca kendiliginden yeniden baglanir."""

    def __init__(self, bilgi: dict) -> None:
        super().__init__(daemon=True)
        self.bilgi = bilgi
        self.mesajlar: list[dict] = []
        self.kilit = threading.Lock()
        self.dur = threading.Event()
        self.bagli = threading.Event()
        self.baglanma_sayisi = 0
        self.hatalar: list[str] = []

    def run(self) -> None:
        host, port, tls = BD.uri_coz(self.bilgi["uri"])
        filtre = f"ok/{self.bilgi['onek']}/#"
        while not self.dur.is_set():
            c = MQ.Istemci(host, port, tls, self.bilgi["kullanici"], self.bilgi["parola"],
                           keepalive=30, zaman_asimi=5.0)
            try:
                c.baglan()
                c.abone(filtre, 1)
                self.baglanma_sayisi += 1
                self.bagli.set()
                while not self.dur.is_set():
                    m = c.bekle(0.5)
                    if m is None:
                        continue
                    konu, yuk, retain = m
                    try:
                        icerik, hata = BD.zarf_ac(self.bilgi["anahtar"], konu, yuk), None
                    except ValueError as h:
                        icerik, hata = None, str(h)
                    with self.kilit:
                        self.mesajlar.append({"t": time.monotonic(), "konu": konu, "retain": retain,
                                              "icerik": icerik, "hata": hata})
            except (MQ.MqttHata, OSError, TimeoutError) as h:
                self.hatalar.append(type(h).__name__)
            finally:
                self.bagli.clear()
                c.kapat()
            self.dur.wait(1.0)

    def liste(self) -> list[dict]:
        with self.kilit:
            return list(self.mesajlar)


# ── E7 (W5, 2026-10-03): `basladi` kaybi kartta mi aracida mi ──────────────────────────
# GERCEK araci, kartin bildirim ayarina DOKUNMAZ (yalniz `Q?` okunur, Q komutu YAZILMAZ). Abone:
# PC'nin 4E onbellegindeki sifreli bilgi zarfi (<veri>\bildirim\<kimlik>.okb, cihaz anahtari
# DPAPI'de) YALNIZ OKUNUR — karta imzali istek gitmez, cihaz sayaci degismez, hicbir sey yazilmaz.
# Ayirt edici olcu: kartin `Q? olay` sayaci = BU ACILISTA araciya ulasip PUBACK'i alinmis olay
# sayisi (RAM, acilista 0). `basladi` her acilisin ILK olayi ve kuyruk FIFO (bildirim.h) ->
# sifirlamadan hemen once olay >= 1 ise `basladi` ARACIDA onaylanmistir.
def basladi_gelenler(mesajlar: list[dict], olay_konu: str) -> list[int]:
    """Abonenin cozdugu mesajlardan `basladi` olaylarinin acilis numaralari (sirasiyla, tekrar dahil)."""
    return [m["icerik"]["a"] for m in mesajlar
            if m.get("konu") == olay_konu and isinstance(m.get("icerik"), dict)
            and m["icerik"].get("o") == "basladi" and isinstance(m["icerik"].get("a"), int)]


def basladi_siniflandir(a0: int, onyoklama: list, gelen: list[int],
                        son_a: int | None = None) -> list[tuple[int, str]]:
    """SAF. `a0`: ilk sifirlamadan ONCEKI acilis; `onyoklama[i]`: (a0 + 1 + i). acilista bir sonraki
    sifirlamadan HEMEN ONCE (son acilista beklemeden sonra) okunan `Q?` sozlugu (None = okunamadi);
    `gelen`: abonenin gordugu `basladi` acilislari; `son_a`: kosu sonunda retained durumun acilisi
    (a0 + len(onyoklama) olmali: her sifirlama TAM bir acilis). Siniflar:
      ulasti         abone gordu
      kartta_kaldi   gormedi; kart o acilista HICBIR olayin PUBACK'ini almadi (olay 0) — olay RAM
                     kuyrugunda / ucustayken sifirlandi (E4: kalici kuyruk bilincli olarak yok)
      aracida_kayip  gormedi; kart PUBACK aldi (olay >= 1) — araci onayladi ama aboneye ulastirmadi
      belirsiz       Q? okunamadi ya da acilis numaralari sifirlamalarla eslesmiyor"""
    tutarli = son_a is None or son_a == a0 + len(onyoklama)
    gk = set(gelen)
    out = []
    for i, q in enumerate(onyoklama, 1):
        a = a0 + i
        if not tutarli or (a not in gk and (not isinstance(q, dict) or not isinstance(q.get("olay"), int))):
            s = "belirsiz"
        elif a in gk:
            s = "ulasti"
        elif q["olay"] >= 1:
            s = "aracida_kayip"
        else:
            s = "kartta_kaldi"
        out.append((a, s))
    return out


def basladi_karar(siniflar: list[tuple[int, str]]) -> str:
    """'kayip yok' | 'kayip kartta' | 'kayip aracida' | 'kayip ikisinde' | 'belirsiz'."""
    say = collections.Counter(s for _, s in siniflar)
    if say.get("belirsiz") or not siniflar:
        return "belirsiz"
    kart, araci = say.get("kartta_kaldi", 0), say.get("aracida_kayip", 0)
    if kart and araci:
        return "kayip ikisinde"
    return "kayip kartta" if kart else ("kayip aracida" if araci else "kayip yok")


def pc_bilgi_onbellek() -> dict | None:
    """PC'nin 4E onbelleginden cozulmus bildirim bilgisi (YALNIZ BELLEKTE; ekrana basilmaz)."""
    _moduller()
    import types
    import pc_bildirim
    return pc_bildirim.PcBildirim(None, types.SimpleNamespace(cikis=None))._onbellekten()


def _q_bekle(k, kosul, sn: float) -> dict | None:
    son, q = time.monotonic() + sn, None
    while time.monotonic() < son:
        q = q_oku(k, 3.0)
        if q and kosul(q):
            return q
        k.satir_oku(0.5)
    return q


def basladi_kaybi(k, n: int, kip: str = "bagli", tohum: int = 7) -> str:
    """E7: n RTS sifirlamasi; her birinden HEMEN ONCE `Q?` (olay/kuyruk/durum) kaydedilir, abone her
    `basladi`yi bekler. kip 'bagli': kart araciya baglanir baglanmaz (Q? durum 4) + 0..3 s — ilk
    gercek araci kosusunun (E1 dongusu) zamanlamasi; 'rastgele': afisten 2..15 s sonra."""
    _moduller()
    bilgi = pc_bilgi_onbellek()
    if not bilgi:
        raise Iptal("PC'nin bildirim onbellegi yok ya da cozulemiyor — kopruyu bir kez calistirin (4E)")
    olay_konu, durum_konu = f"ok/{bilgi['onek']}/olay", f"ok/{bilgi['onek']}/durum"
    din = Dinleyici(bilgi)
    din.start()
    try:
        if not din.bagli.wait(30):
            raise Iptal(f"araciya abone olunamadi ({din.hatalar[-1:] or '-'})")

        def son_durum_a():
            d = [m["icerik"] for m in din.liste() if m["konu"] == durum_konu and m["icerik"]
                 and m["icerik"].get("c") == 1 and isinstance(m["icerik"].get("a"), int)]
            return d[-1]["a"] if d else None
        q0 = _q_bekle(k, lambda q: q.get("durum") == 4, 60)
        son = time.monotonic() + 20
        while son_durum_a() is None and time.monotonic() < son:
            k.satir_oku(0.3)
        a0 = son_durum_a()
        if a0 is None or not q0 or q0.get("durum") != 4:
            raise Iptal(f"baslangic: retained durum yok ya da kart bagli degil (Q? durum {q0 and q0.get('durum')})")
        print(f"\n── E7: {n} RTS sifirlamasi (kip {kip}); baslangic acilisi a0, kart bagli")
        rng = random.Random(tohum)
        onyok: list = []
        for i in range(1, n + 1):
            k.sifirla()
            acildi = yeni_acilis(k, 30)
            if kip == "bagli":
                _q_bekle(k, lambda q: q.get("durum") == 4, 60)
                seri_bosalt(k, rng.uniform(0.0, 3.0))
            else:
                seri_bosalt(k, rng.uniform(2.0, 15.0))
            q = q_oku(k, 3.0) if i < n else _q_bekle(k, lambda q: q.get("olay", 0) >= 1, 90)
            onyok.append(q)
            print(f"  {i:2d}/{n}: afis={'var' if acildi else 'YOK'}  Q? durum={q and q.get('durum')} "
                  f"olay={q and q.get('olay')} kuyruk={q and q.get('kuyruk')} baglanti={q and q.get('baglanti')}"
                  f"  abone basladi={len(basladi_gelenler(din.liste(), olay_konu))}")
        seri_bosalt(k, 8.0)
        son_a = son_durum_a()
        gelen = basladi_gelenler(din.liste(), olay_konu)
        sinif = basladi_siniflandir(a0, onyok, gelen, son_a)
        karar = basladi_karar(sinif)
        say = collections.Counter(s for _, s in sinif)
        print(f"  siniflar {say}; abone yeniden baglanma {din.baglanma_sayisi - 1}; karar: {karar}")
        for (a, s), q in zip(sinif, onyok):
            if s != "ulasti":
                print(f"    acilis a0+{a - a0}: {s} (Q? durum={q and q.get('durum')} olay={q and q.get('olay')} "
                      f"kuyruk={q and q.get('kuyruk')})")
        ok(f"E7: her sifirlama tek acilis (retained durum a = a0 + {n}) ve abone kesintisiz",
           son_a == a0 + n and din.baglanma_sayisi == 1, f"son_a-a0={None if son_a is None else son_a - a0}, "
           f"abone baglanma {din.baglanma_sayisi}")
        ok("E7: PUBACK'i alinmis (Q? olay >= 1) her `basladi` aboneye ULASTI (aracida kayip yok)",
           karar in ("kayip yok", "kayip kartta"), karar)
        return karar
    finally:
        din.dur.set()


# ── tezgah ───────────────────────────────────────────────────────────────
class Tezgah:
    def __init__(self, k: SeriYakala, host: str, tekrar: int, ip: str | None, ustune: bool) -> None:
        self.k, self.host, self.tekrar, self.ip_arg, self.ustune = k, host, tekrar, ip, ustune
        self.taban = f"http://{host}"
        self.kart_kul = "kart-" + secrets.token_hex(3)
        self.cihaz_kul = "cihaz-" + secrets.token_hex(3)
        self.kart_par = secrets.token_urlsafe(18)
        self.cihaz_par = secrets.token_urlsafe(18)
        self.sirlar = [self.kart_par, self.cihaz_par]
        self.araci = self.cihaz = self.sse = self.din = self.tmp = None
        self.bilgi: dict | None = None
        self.kimlik = self.kart_id = self.uri = ""
        self.durum_konu = self.olay_konu = ""
        self.acilis: int | None = None
        self.adet0 = -1
        self.ayar_basladi = False

    # -- ortak yardimcilar
    def bekle(self, fn, sn: float):
        """`fn()` doğru bir deger dondurene dek (seri akisi bosaltarak) en cok `sn` s bekle."""
        son = time.monotonic() + sn
        while True:
            v = fn()
            if v:
                return v
            if time.monotonic() >= son:
                return None
            self.k.satir_oku(0.25)

    def kart_olayi(self, tur: str, baslangic: int = 0, **alan):
        return self.araci.bekle(lambda o: o["tur"] == tur and all(o.get(a) == b for a, b in alan.items()),
                                0.0, baslangic)

    def kart_baglandi(self, baslangic: int = 0):
        return self.araci.bekle(lambda o: o["tur"] == "connect" and o["kullanici"] == self.kart_kul
                                and o["sonuc"] == 0, 0.0, baslangic)

    def cozulmus(self, konu: str, yuk: bytes) -> dict | None:
        try:
            return BD.zarf_ac(self.bilgi["anahtar"], konu, yuk)
        except ValueError:
            return None

    def olaylar(self, baslangic: int = 0) -> list[tuple[dict, dict | None]]:
        return [(e, self.cozulmus(e["konu"], e["yuk"]))
                for e in self.araci.olaylar_sec("publish", baslangic, konu=self.olay_konu,
                                                istemci=self.kart_id)]

    def retained_durum(self) -> dict | None:
        r = self.araci.retained_al(self.durum_konu)
        return self.cozulmus(self.durum_konu, r[0]) if r else None

    def sse_url(self) -> str:
        if self.sse is not None and self.sse.son_kod == 401 and self.cihaz is not None:
            with IMZA_KILIT:
                return IM.akis_url(self.cihaz, self.taban)
        return self.taban + "/akis"

    # -- akis
    def calistir(self) -> None:
        self.onkosul()
        self.eslestir()
        self.araci_ve_ayar()
        self.bilgi_al()
        self.baglanma()
        self.deneme_olayi()
        self.ram()
        if self.tekrar > 0:
            self.sifirlama()
        self.kesinti()
        self.canlilik()
        self.komut_ve_sizinti()

    def onkosul(self) -> None:
        print("\n── onkosul: kart, kimlik, bos ayar")
        q = q_oku(self.k)
        ok("Q? yanit veriyor (firmware A3-1E: Q komutlari var)", q is not None)
        if q is None:
            raise Iptal("kart `Q?` yanitlamadi: firmware A3-1E degil, port yanlis ya da dogru Type-C "
                        "(COM yazan) takili degil")
        sta = not any("yalniz ev aginda" in u for u in q["uyarilar"])
        ok("kart STA kipinde (MQTT yalniz ev aginda calisir, AP'de yok)", sta)
        if not sta:
            raise Iptal("kart AP kipinde; ev agina baglayin (N1/Na/Np) ve yeniden baslatin")
        qa = q["qa"]
        bos = (qa.get("uri") == "-" and qa.get("kart") == "-" and qa.get("cihaz") == "-"
               and qa.get("kart_parola") == "yok" and qa.get("cihaz_parola") == "yok" and q["acik"] == 0)
        if not bos and not self.ustune:
            raise Iptal("kartta bildirim ayari ZATEN VAR (Q? ile bakin). Tezgah temizlikte bu ayarlari "
                        "silerdi ve parolalar geri okunamaz. Gercekten uzerine yazmak istiyorsaniz "
                        "--ustune-yaz verin")
        ok("bildirim ayari bos (tezgah kullanicinin ayarini silmez)", bos or self.ustune,
           "uzerine yazilacak (--ustune-yaz)" if not bos else "")
        satirlar = komut_satirlari(self.k, "E?", 1.5)
        e = next((x for x in satirlar if x.startswith("E zorunlu=")), "")
        m = re.search(r"kimlik=([0-9a-f]{16})", e)
        self.kimlik = m.group(1) if m else ""
        self.adet0 = int(re.search(r"cihaz=(\d+)", e).group(1)) if re.search(r"cihaz=(\d+)", e) else -1
        ok("E? kart kimligi (16 hex) ve cihaz sayisi okundu", bool(self.kimlik) and self.adet0 >= 0, e)
        if not self.kimlik:
            raise Iptal("E? satiri okunamadi (firmware 1D yok mu?)")

    def eslestir(self) -> None:
        print("\n── C0: USB eslestirmesi + /bildirim/bilgi (ayarsizken 404)")
        self.tmp = tempfile.TemporaryDirectory()
        self.sse = SseYakala(self.sse_url)
        self.sse.start()
        # olcum.local cozumu ~3 s: dinleyici BAGLANMADAN Ep gonderilirse "anahtar SSE'de yok" bos yere gecer
        self.bekle(self.sse.ilk_veri.is_set, 20)
        self.cihaz = IM.esles_usb(self.k, "bench-1E", dizin=Path(self.tmp.name))
        ok("USB eslestirmesi (Ep): test cihazi eklendi, 32 B anahtar", self.cihaz.n >= 1 and len(self.cihaz.K) == 32,
           f"cihaz {self.cihaz.n}")
        kod, govde = imzali(self.cihaz, self.taban, "GET", "/bildirim/bilgi")
        ok("bildirim ayarlanmamisken imzali /bildirim/bilgi 404", kod == 404, f"{kod} {govde[:60]!r}")

    def araci_ve_ayar(self) -> None:
        print("\n── A1/A2: sahte araci + USB ayari")
        try:
            kart_ip, pc_ip = lan_ip(self.host)
        except OSError as h:
            raise Iptal(f"{self.host} cozulemedi ({h}); --http <kartin IP'si> verin") from h
        if self.ip_arg:
            pc_ip = self.ip_arg
        ok("PC'nin karta giden arayuz IP'si bulundu (loopback degil)",
           not pc_ip.startswith("127.") and pc_ip != "0.0.0.0", f"kart {kart_ip} <- PC {pc_ip}")
        self.araci = SA.SahteAraci(pc_ip, 0, {self.kart_kul: (self.kart_par, "rw"),
                                              self.cihaz_kul: (self.cihaz_par, "r")}).start()
        self.uri = f"mqtt://{pc_ip}:{self.araci.port}"
        print(f"  sahte araci: {self.uri} (duz TCP; kimlik bilgileri rastgele, gosterilmez)")
        self.ayar_basladi = True
        sonuc = {}
        for ad, c in (("adres", f"Qu{self.uri}"), ("kart kullanicisi", f"Qk{self.kart_kul}"),
                      ("kart parolasi", f"Qp{self.kart_par}"), ("cihaz kullanicisi", f"Qc{self.cihaz_kul}"),
                      ("cihaz parolasi", f"Qd{self.cihaz_par}")):
            sonuc[ad] = q_ayar(self.k, c)
        ok("Qu/Qk/Qp/Qc/Qd USB'den kaydedildi ('kaydedildi', hata yok)",
           all("kaydedildi" in v and v.startswith("* Q:") for v in sonuc.values()),
           str({a: (v[:34] if "kaydedildi" not in v else "ok") for a, v in sonuc.items()}))
        y = q_ayar(self.k, "Q1")
        ok("Q1: bildirim ACIK (onek + bildirim anahtari uretildi)", "bildirim ACIK" in y, y[:70])
        qv = q_ayar(self.k, "Qv", ("QV ",))
        ok("Qv: RFC 8439 oz sinamasi kartta gecti (QV gecti 0)", qv.startswith("QV gecti 0"), qv[:40])

    def bilgi_al(self) -> None:
        print("\n── C1: imzali /bildirim/bilgi")
        try:
            with IMZA_KILIT:
                b = BD.bilgi_al(self.cihaz, self.taban)
        except Exception as h:                                  # noqa: BLE001
            raise Iptal(f"/bildirim/bilgi alinamadi: {type(h).__name__} {str(h)[:80]}") from h
        self.bilgi = b
        self.sirlar += [b["anahtar"].hex(), b["onek"]]
        self.durum_konu, self.olay_konu = f"ok/{b['onek']}/durum", f"ok/{b['onek']}/olay"
        ok("bilgi: uri, cihaz kullanicisi, cihaz parolasi kartta ayarlananla AYNI",
           b["uri"] == self.uri and b["kullanici"] == self.cihaz_kul and b["parola"] == self.cihaz_par)
        ok("bilgi: onek 32 kucuk hex, anahtar 32 bayt", len(b["onek"]) == 32 and len(b["anahtar"]) == 32)
        kod = ham_istek(self.taban, "/bildirim/bilgi", {"X-Olcum": "1"})[0]
        ok("imzasiz /bildirim/bilgi 401 (yalniz eslesmis cihaz)", kod == 401, str(kod))
        q = q_oku(self.k)
        ok("Q? onekin YALNIZ ilk 8 hanesini yazar, anahtari/parolalari 'var' diye gosterir",
           bool(q) and q["qa"].get("onek") == b["onek"][:8] and q["qa"].get("anahtar") == "var"
           and q["qa"].get("kart_parola") == "var" and q["qa"].get("cihaz_parola") == "var")
        self.din = Dinleyici(b)
        self.din.start()

    def baglanma(self) -> None:
        print("\n── B1-B4: kart araciya baglanir; CONNECT, vasiyet, durum")
        c = self.bekle(lambda: self.kart_baglandi(), 45)
        ok("kart sahte araciya baglandi (<= 45 s)", c is not None)
        if c is None:
            self.baglanamadi()
        self.kart_id = c["istemci"]
        k = next(x for x in self.araci.baglantilar if x["istemci_id"] == self.kart_id and x["sonuc"] == 0)
        ok("CONNECT: istemci kimligi ok-<kart kimligi>, kullanici = kart kullanicisi, temiz oturum",
           k["istemci_id"] == f"ok-{self.kimlik}" and k["kullanici"] == self.kart_kul and k["temiz"] is True,
           k["istemci_id"])
        ok("CONNECT: keepalive 5 s (araci 7.5 s'de vasiyeti yayinlar)", k["keepalive"] == KEEPALIVE_S,
           str(k["keepalive"]))
        ok("CONNECT: vasiyet var, QoS 1, retain, konu ok/<onek>/durum",
           k["will"] and k["will_qos"] == 1 and k["will_retain"] is True and k["will_konu"] == self.durum_konu,
           f"qos {k['will_qos']} retain {k['will_retain']}")
        w = self.cozulmus(k["will_konu"], k["will_yuk"])
        ok("vasiyet yuku zarf: konu AAD'iyle cozulur, tam {c:0, a}", w is not None and w.get("c") == 0
           and set(w) == {"c", "a"} and isinstance(w.get("a"), int), str(w))

        e = self.bekle(lambda: self.kart_olayi("publish", konu=self.durum_konu, istemci=self.kart_id), 30)
        d = self.cozulmus(self.durum_konu, e["yuk"]) if e else None
        ok("durum yayinlandi: QoS 0 + RETAIN, zarf cozulur", e is not None and d is not None
           and e["qos"] == 0 and e["retain"] is True)
        if d:
            ok("durum alanlari: c:1, f == A3-1E, a/t/k/o/y/d/e tamsayi", d.get("c") == 1 and d.get("f") == FW
               and all(isinstance(d.get(a), int) for a in "atkoyde"), str(d))
            self.acilis = d["a"]
            ok("vasiyetteki a = durum mesajindaki a (ayni acilis)", w is not None and w["a"] == d["a"],
               f"{w and w.get('a')} / {d['a']}")
            ok("YANLIS KONU AAD'siyle (olay konusu) durum zarfi COZULMEZ", hata_verir(
                lambda: BD.zarf_ac(self.bilgi["anahtar"], self.olay_konu, e["yuk"])))
            ok("yanlis anahtarla durum zarfi COZULMEZ", hata_verir(
                lambda: BD.zarf_ac(bytes(32), self.durum_konu, e["yuk"])))
        pc = self.bekle(lambda: next((m for m in self.din.liste() if m["konu"] == self.durum_konu
                                      and m["icerik"] and m["icerik"].get("c") == 1), None), 15)
        ok("PC abonesi (salt-okur cihaz kullanicisi) durumu aldi ve cozdu", pc is not None,
           "retained" if pc and pc["retain"] else "canli")
        ok("retained deposu kartin c:1 durumunu tutuyor", (self.retained_durum() or {}).get("c") == 1)

    def baglanamadi(self) -> None:
        q = q_oku(self.k) or {}
        hata, durum = q.get("hata"), q.get("durum")
        mesaj = [f"Kart 45 s icinde sahte araciya BAGLANMADI (Q? durum={durum}, hata={hata}).", ""]
        if hata == -3 or durum in (3, 5) and (hata or 0) in (-3, -4, -6):
            mesaj += [
                "Buyuk olasilikla Windows Guvenlik Duvari bu bilgisayardaki python.exe'ye GELEN baglantiyi",
                "engelliyor (kart TCP baglantisini kuramadi, Q? hata=-3). Yapilacak (kural bu betik",
                "tarafindan DEGISTIRILMEZ):",
                "  1. Betigin ilk acilisinda cikan 'Windows Guvenlik Duvari' penceresinde python.exe icin",
                "     'Ozel aglar'a izin ver' (Allow) secin ve betigi yeniden calistirin; ya da",
                "  2. Baslat > 'Guvenlik Duvari ile bir uygulamaya izin ver' > python.exe > Ozel'i isaretleyin.",
                f"  Ayrica kart ({self.host}) ile bu PC ayni ag/alt agda mi? (PC IP: {self.uri}).",
            ]
        elif isinstance(hata, int) and hata <= -100:
            mesaj.append(f"Araci kartin kimligini REDDETTI (CONNACK kodu {-100 - hata}); kart parolasi/"
                         "kullanicisi ayarlanamadi mi? Qk/Qp satirlarinin 'kaydedildi' dedigini kontrol edin.")
        else:
            mesaj.append("Q? hata kodlari: -3 TCP kurulamadi · -5 CONNACK gelmedi · -6 baglanti kapandi · "
                         "-100-N araci ret. Ag adi/IP'yi ve kartin ev aginda (STA) oldugunu kontrol edin.")
        raise Iptal("\n".join(mesaj))

    def deneme_olayi(self) -> None:
        print("\n── D1: Qt deneme olaylari")
        q0 = q_oku(self.k)
        olay0 = q0["olay"] if q0 else 0
        b = len(self.araci.olaylar)
        for _ in range(2):
            q_ayar(self.k, "Qt")
        son = self.bekle(lambda: len([d for _, d in self.olaylar(b) if d and d.get("o") == "deneme"]) >= 2
                         or None, 20)
        dn = [(e, d) for e, d in self.olaylar(b) if d and d.get("o") == "deneme"]
        ok("Qt x2: iki deneme olayi araciya ulasti ve cozuldu", son is not None and len(dn) >= 2, f"{len(dn)} adet")
        if len(dn) >= 2:
            (e1, d1), (e2, d2) = dn[0], dn[1]
            ok("deneme olaylari: QoS 1, retain YOK", e1["qos"] == 1 and e2["qos"] == 1
               and e1["retain"] is False and e2["retain"] is False)
            ok("n artiyor (ikincisi birincisinden buyuk), a = acilis, t tamsayi", d2["n"] > d1["n"]
               and d1["a"] == d2["a"] == self.acilis and isinstance(d1["t"], int), f"{d1['n']} -> {d2['n']}")
        q1 = self.bekle(lambda: (lambda q: q if q and q["kuyruk"] == 0 and q["olay"] >= olay0 + 2 else None)(
            q_oku(self.k)), 15)
        ok("kart PUBACK aldi: Q? kuyruk 0, olay sayaci +2", q1 is not None,
           f"olay {olay0} -> {q1['olay'] if q1 else '?'}")

    def ram(self) -> None:
        print("\n── Y1: ic RAM (K11)")
        q = q_oku(self.k)
        ok(f"bagliyken QY dahili_bos >= {RAM_SINIR} bayt", bool(q) and q["durum"] == 4
           and q["dahili_bos"] >= RAM_SINIR,
           f"bos {q and q['dahili_bos']} en_az {q and q['dahili_en_az']} el_sikisma {q and q['el_sikisma_ms']} ms")

    def sifirlama(self) -> None:
        n = self.tekrar
        print(f"\n── E1/E2: RTS sifirlamasi x{n}: vasiyet suresi, yeniden baglanma, durum/basladi")
        dts, nedenler = [], []
        sonuc = {"acildi": 0, "vasiyet": 0, "yuk": 0, "canli": 0, "yeniden": 0, "durum": 0, "basladi": 0}
        for i in range(1, n + 1):
            bagli = self.bekle(lambda: (lambda q: bool(q) and q["durum"] == 4)(q_oku(self.k)), 90)
            if not bagli:
                print(f"  sifirlama {i}/{n}: kart bagli degil, atlandi")
                continue
            seri_bosalt(self.k, 3.0)
            eski_a, b0 = self.acilis, len(self.araci.olaylar)
            t_reset = time.monotonic()
            self.k.sifirla()
            acildi = yeni_acilis(self.k, 30)
            sonuc["acildi"] += acildi
            w = self.bekle(lambda: self.kart_olayi("will_published", b0, istemci=self.kart_id), 30)
            dt = (w["t"] - t_reset) if w else None
            if w:
                sonuc["vasiyet"] += 1
                dts.append(dt)
                nedenler.append(w["neden"])
                c0 = self.cozulmus(w["konu"], w["yuk"])
                sonuc["yuk"] += bool(c0 and c0.get("c") == 0 and c0.get("a") == eski_a and w["qos"] == 1
                                     and w["retain"] is True and w["konu"] == self.durum_konu)
                t_w = w["t"]
                sonuc["canli"] += bool(self.bekle(lambda: next(
                    (m for m in self.din.liste() if m["konu"] == self.durum_konu and m["icerik"]
                     and m["icerik"].get("c") == 0 and m["icerik"].get("a") == eski_a
                     and m["t"] >= t_w - 0.5), None), 5))
            c = self.bekle(lambda: self.kart_baglandi(b0), int(YENIDEN_BAGLAN_SINIR_S))
            sonuc["yeniden"] += c is not None
            yeni_a = None
            if c:
                d = self.bekle(lambda: (lambda x: x if x and x.get("c") == 1 and x["a"] > eski_a else None)(
                    self.retained_durum()), 60)
                yeni_a = d["a"] if d else None
                sonuc["durum"] += bool(d and d.get("f") == FW)
                bs = self.bekle(lambda: next((x for _, x in self.olaylar(b0) if x and x.get("o") == "basladi"
                                              and x.get("a") == yeni_a), None), 60) if yeni_a else None
                sonuc["basladi"] += bool(bs and bs.get("n") == 1 and bs.get("devam") in (0, 1, 2))
                if yeni_a:
                    self.acilis = yeni_a
                devam = bs.get("devam") if bs else None
            else:
                devam = None
            print(f"  sifirlama {i:2d}/{n}: afis={'var' if acildi else 'YOK'}  reset -> vasiyet "
                  f"{'-' if dt is None else f'{dt:5.2f} s'} ({w['neden'] if w else '-'})  "
                  f"yeniden baglandi={'evet' if c else 'HAYIR'}  acilis {eski_a} -> {yeni_a}  basladi.devam={devam}")
        gec = len(dts)
        ok(f"{n} sifirlamanin hepsinde kart yeniden acildi (acilis afisi goruldu)", sonuc["acildi"] == n, f"{sonuc['acildi']}/{n}")
        if dts:
            print(f"  vasiyet suresi (reset -> aracida yayin): en az {min(dts):.2f} s, ortanca "
                  f"{statistics.median(dts):.2f} s, en cok {max(dts):.2f} s; nedenler {sorted(set(nedenler))}")
        ok(f"VASIYET <= {VASIYET_SINIR_S:.0f} s icinde yayinlandi ({n}/{n}; hedef {VASIYET_HEDEF_S:.0f} s: "
           f"{sum(1 for x in dts if x <= VASIYET_HEDEF_S)}/{n})",
           gec == n and all(x <= VASIYET_SINIR_S for x in dts), f"{gec} olcum")
        ok("vasiyet yuku: QoS1 + retain, c:0, a = onceki acilis, konu durum konusu", sonuc["yuk"] == n, f"{sonuc['yuk']}/{n}")
        ok("PC abonesi vasiyeti CANLI (c:0, eski acilis) gordu", sonuc["canli"] == n, f"{sonuc['canli']}/{n}")
        ok(f"kart <= {YENIDEN_BAGLAN_SINIR_S:.0f} s icinde yeniden baglandi", sonuc["yeniden"] == n, f"{sonuc['yeniden']}/{n}")
        ok("retained durum c:1'e DONDU (c:0'in ustune yazildi), yeni acilis > eski, f == A3-1E",
           sonuc["durum"] == n, f"{sonuc['durum']}/{n}")
        ok("`basladi` olayi: n == 1, devam in {0,1,2}, a = yeni acilis", sonuc["basladi"] == n, f"{sonuc['basladi']}/{n}")

    def kesinti(self) -> None:
        print("\n── F1-F3: araci kesintisi (kapali_tut / ac, ayni port)")
        q0 = self.bekle(lambda: (lambda q: q if q and q["durum"] == 4 else None)(q_oku(self.k)), 90)
        if not q0:
            ok("kesinti oncesi kart bagli", False)
            return
        b0 = len(self.araci.olaylar)
        t_k = time.monotonic()
        self.araci.kapali_tut()
        self.araci.yayinla(self.durum_konu, b"ESKI-ISARETCI", qos=1, retain=True)    # kartin ezmesi gereken retained
        t_dus, q = None, None
        while time.monotonic() - t_k < 30:
            q = q_oku(self.k, 3.0)
            if q and q["durum"] != 4:
                t_dus = time.monotonic() - t_k
                break
        ok(f"F1: araci gidince kart <= {DUSME_SINIR_S:.0f} s icinde 'bagli' DEGIL",
           t_dus is not None and t_dus <= DUSME_SINIR_S,
           f"{t_dus and round(t_dus, 1)} s, durum {q and q['durum']} hata {q and q['hata']}")
        ok("F1: kesintide vasiyet yayinlanmadi (araci kendisi yok)",
           not self.araci.olaylar_sec("will_published", b0))
        q_ayar(self.k, "Qt")
        seri_bosalt(self.k, 1.5)
        qk = q_oku(self.k)
        ok("F2: kesintideyken Qt: olay RAM kuyrugunda bekliyor (Q? kuyruk >= 1), kart bagli degil",
           bool(qk) and qk["kuyruk"] >= 1 and qk["durum"] != 4, f"kuyruk {qk and qk['kuyruk']} durum {qk and qk['durum']}")
        t_ac = time.monotonic()
        self.araci.ac()
        c = self.bekle(lambda: self.kart_baglandi(b0), int(YENIDEN_BAGLAN_SINIR_S))
        ok(f"F3: ac(): kart <= {YENIDEN_BAGLAN_SINIR_S:.0f} s icinde YENIDEN baglandi (geri cekilme 2,4,8..60 s)",
           c is not None and (c["t"] - t_ac) <= YENIDEN_BAGLAN_SINIR_S,
           f"{c and round(c['t'] - t_ac, 1)} s")
        dn = self.bekle(lambda: next((d for _, d in self.olaylar(b0) if d and d.get("o") == "deneme"), None), 30)
        ok("F3: kesintide kuyruga giren deneme olayi araci donunce ULASTI", dn is not None)
        d = self.bekle(lambda: (lambda x: x if x and x.get("c") == 1 else None)(self.retained_durum()), 30)
        ok("F3: retained durum yeniden yazildi (c:1; aracidaki eski isaretci EZILDI)", d is not None and d.get("a") == self.acilis)
        q = self.bekle(lambda: (lambda x: x if x and x["kuyruk"] == 0 and x["durum"] == 4 else None)(q_oku(self.k)), 20)
        ok("F3: kuyruk 0, kart bagli, olay sayaci artti", bool(q) and q["olay"] > q0["olay"],
           f"olay {q0['olay']} -> {q and q['olay']}")
        gb = self.bekle(lambda: next((m for m in self.din.liste() if m["t"] >= t_ac
                                      and m["konu"] == self.durum_konu and m["icerik"]
                                      and m["icerik"].get("c") == 1), None), 20)
        ok("F3: PC abonesi kesintiden sonra KENDILIGINDEN yeniden baglandi ve kartin c:1 durumunu aldi",
           gb is not None and self.din.baglanma_sayisi >= 2, f"{self.din.baglanma_sayisi} baglanma")

    # -- E8: yanitsiz araci (sessiz araci + kara delik vekili)
    def _bagli_q(self, sn: float):
        return self.bekle(lambda: (lambda q: q if q and q["durum"] == 4 else None)(q_oku(self.k)), sn)

    def _yanitsiz_olc(self, ad: str, q0: dict, t0: float, kapanis) -> None:
        """Susma ani `t0`; `kapanis()` kartin baglantiyi kapattigi olay (ya da None)."""
        d = self.bekle(kapanis, SESSIZ_SINIR_S + 10)
        dt = (d["t"] - t0) if d else None
        q = q_oku(self.k)                       # yeniden deneme -5'i en erken ~12 s sonra yazar
        ok(f"{ad}: kart yanitsiz baglantiyi <= {SESSIZ_SINIR_S} s icinde KENDISI kapatti "
           f"(tasarim {SESSIZ_TASARIM_S:.0f} s = 4 s ping + 5 s PINGRESP)",
           dt is not None and dt <= SESSIZ_SINIR_S, f"{dt and round(dt, 2)} s")
        ok(f"{ad}: Q? hata=-7 (PINGRESP / soket zaman asimi; -6 'araci kapatti' DEGIL), durum bagli degil, "
           "gorev turu artiyor", bool(q) and q["hata"] == -7 and q["durum"] != 4
           and q.get("tur", 0) > q0.get("tur", 0),
           f"hata {q and q['hata']} durum {q and q['durum']} tur {q0.get('tur')} -> {q and q.get('tur')} "
           f"adim {q and q.get('adim')} ping_yas {q and q.get('ping_yas')} pong_yas {q and q.get('pong_yas')}")

    def canlilik(self) -> None:
        print("\n── S1/S2: E8 yanitsiz araci — sessiz araci + kara delik vekili")
        q0 = self._bagli_q(90)
        if not q0:
            ok("S1: once kart bagli", False)
            return
        ok("S1: Q? E8 canlilik alanlari (tur, adim, adim_yas, ping_yas, pong_yas); bagliyken son PINGRESP "
           "<= 10 s once", all(a in q0 for a in ("tur", "adim", "adim_yas", "ping_yas", "pong_yas"))
           and 0 <= q0["pong_yas"] <= 10_000,
           f"tur {q0.get('tur')} adim {q0.get('adim')} adim_yas {q0.get('adim_yas')} "
           f"ping_yas {q0.get('ping_yas')} pong_yas {q0.get('pong_yas')}")
        # S1: sessiz araci — TCP acik, gelen okunur, hicbir yanit yok, keepalive uygulanmaz
        b0 = len(self.araci.olaylar)
        t0 = self.araci.sessiz()
        try:
            self._yanitsiz_olc("S1", q0, t0, lambda: self.kart_olayi("disconnect", b0, istemci=self.kart_id))
        finally:
            b1 = len(self.araci.olaylar)
            self.araci.konus()
        c = self._bagli_q(YENIDEN_BAGLAN_SINIR_S)
        ok(f"S1: konus(): kart <= {YENIDEN_BAGLAN_SINIR_S:.0f} s icinde yeniden BAGLI (Q? durum 4)",
           c is not None and self.kart_baglandi(b1) is not None)
        # S2: kara delik vekili — kart vekil uzerinden baglanir; kes() sonrasi iki yon de yutulur
        v = SA.KaraDelikVekil(self.araci.host, self.araci.port, host=self.araci.host).start()
        degisti = False
        try:
            b2 = len(self.araci.olaylar)
            y = q_ayar(self.k, f"Qumqtt://{self.araci.host}:{v.port}")
            degisti = "kaydedildi" in y
            q1 = self._bagli_q(YENIDEN_BAGLAN_SINIR_S) if degisti else None
            ok("S2: kart kara delik vekili uzerinden araciya baglandi", bool(q1) and degisti
               and self.kart_baglandi(b2) is not None and v.olay_bekle("baglanti", 0.0) is not None, y[:40])
            if q1:
                seri_bosalt(self.k, 2.0)
                b3, i3 = len(self.araci.olaylar), len(v.olaylar)
                t0 = v.kes()
                self._yanitsiz_olc("S2", q1, t0, lambda: next(
                    (o for o in v.olaylar[i3:] if o["tur"] == "istemci_kapandi"), None))
                w = self.bekle(lambda: self.kart_olayi("will_published", b3, istemci=self.kart_id), 15)
                ok("S2: aracı kartin sesini alamadi -> keepalive (7.5 s) ile vasiyeti YAYINLADI",
                   w is not None and w["neden"] == "keepalive", w and w["neden"])
        finally:
            if degisti:
                y = q_ayar(self.k, f"Qu{self.uri}")
                ok("S2: Qu eski (dogrudan) adrese dondu", "kaydedildi" in y, y[:40])
            v.stop()
        c = self._bagli_q(YENIDEN_BAGLAN_SINIR_S)
        ok(f"S2: vekil kalkinca kart <= {YENIDEN_BAGLAN_SINIR_S:.0f} s icinde dogrudan araciya BAGLI",
           c is not None)

    def komut_ve_sizinti(self) -> None:
        print("\n── H1/G1: /komut Q reddi, sizinti denetimi")
        h = {"X-Olcum": "1", "Content-Type": "text/plain"}
        kod, _, govde = ham_istek(self.taban, "/komut", h, "POST", b"Q?")
        if kod == 401:                                      # imza zorunluysa imzali dene
            kod, g = imzali(self.cihaz, self.taban, "POST", "/komut", (), b"Q?")
            govde = g.decode("utf-8", "replace")
        ok("H1: POST /komut 'Q?' -> 403 (Q komutlari yalniz USB)", kod == 403 and "USB" in govde, f"{kod} {govde[:50]}")
        seri = self.k.metin()
        sse = self.sse.metin() if self.sse else ""
        say_seri = sum(seri.count(s) for s in self.sirlar)
        say_sse = sum(sse.count(s) for s in self.sirlar)
        ok("G1: seri konsol kaydinda kart/cihaz parolasi, bildirim anahtari ve tam onek YOK",
           say_seri == 0 and len(self.k.satirlar) > 20, f"{len(self.k.satirlar)} satir tarandi, {say_seri} eslesme")
        ok("G1: /akis SSE metninde (seri aynasi) ayni sirlar YOK",
           say_sse == 0 and len(sse) > 200 and self.sse.son_kod is not None, f"{len(sse)} bayt tarandi, {say_sse} eslesme")

    # -- temizlik (her zaman)
    def temizlik(self) -> None:
        if self.ayar_basladi or self.cihaz is not None:
            print("\n── T1: temizlik")
        if self.din:
            self.din.dur.set()
        if self.ayar_basladi:
            q_ayar(self.k, "Q0")
            seri_bosalt(self.k, 1.0)                        # nazik kapanis (vasiyet yerine c:0) araciya ulassin
            for c in ("Qu", "Qk", "Qp", "Qc", "Qd"):
                q_ayar(self.k, c)
        if self.cihaz is not None:
            komut_satirlari(self.k, f"Ex{self.cihaz.n}", 1.5)
        if self.araci:
            self.araci.stop()
        if self.sse:
            self.sse.dur.set()
        if self.ayar_basladi or self.cihaz is not None:
            q = q_oku(self.k)
            e = next((x for x in komut_satirlari(self.k, "E?", 1.5) if x.startswith("E zorunlu=")), "")
            qa = (q or {}).get("qa", {})
            ok("temizlik: bildirim KAPALI, adres/kullanicilar bos, parolalar 'yok'",
               bool(q) and q["acik"] == 0 and qa.get("uri") == "-" and qa.get("kart") == "-"
               and qa.get("cihaz") == "-" and qa.get("kart_parola") == "yok" and qa.get("cihaz_parola") == "yok",
               str({a: b for a, b in qa.items() if a != "onek"}))
            ok("temizlik: bench cihazi silindi (E? cihaz sayisi baslangicla ayni)",
               f"cihaz={self.adet0}" in e, e)
        if self.tmp:
            self.tmp.cleanup()
        if self.ayar_basladi:
            print("  (kartta rastgele uretilmis onek + bildirim anahtari KALIR; QR! ile yenilenir)")


def hata_verir(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    except Exception:                                          # noqa: BLE001
        return False
    return False


def liste() -> None:
    print("tezgah_bildirim.py — planlanan denetimler (bu komut DONANIMA DOKUNMAZ)\n")
    for kod, metin in PLAN:
        govde = metin
        satirlar, satir = [], ""
        for kelime in govde.split():
            if len(satir) + len(kelime) + 1 > 92:
                satirlar.append(satir)
                satir = kelime
            else:
                satir = f"{satir} {kelime}".strip()
        satirlar.append(satir)
        print(f"  {kod:3s} {satirlar[0]}")
        for s in satirlar[1:]:
            print(f"      {s}")
    print("\nOn kosullar: kart A3-1E, COM6'da, ev aginda (STA), web olcum.local; bildirim ayari bos;")
    print("Windows Guvenlik Duvari python.exe'nin ozel aglardan GELEN baglantisina izin vermeli.")
    print("Kullanici sirri gerekmez: araci kimlik bilgileri rastgele uretilir, gosterilmez, temizlikte silinir.")
    print("Secenekler: --tekrar N (RTS sifirlamasi, vars. 3) --port COM6 --http olcum.local --ip <PC IP>")
    print("            --ustune-yaz (kartta bildirim ayari VARSA silmeyi kabul et)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="1E MQTT bildirimleri — gercek kart tezgahi")
    ap.add_argument("--bildirim", action="store_true", help="tam akis (varsayilan)")
    ap.add_argument("--liste", action="store_true", help="planlanan denetimleri yaz, donanima dokunma")
    ap.add_argument("--tekrar", type=int, default=3, help="RTS sifirlamasi sayisi (vasiyet suresi); 0 = atla")
    ap.add_argument("--port", default="COM6")
    ap.add_argument("--http", default="olcum.local")
    ap.add_argument("--ip", default=None, help="PC'nin karta erisilebilir IP'si (otomatik bulunamazsa)")
    ap.add_argument("--ustune-yaz", action="store_true", help="kartta var olan bildirim ayarini silmeyi kabul et")
    ap.add_argument("--basladi", type=int, default=0,
                    help="E7: GERCEK araci, N RTS sifirlamasi; basladi kaybi kartta mi aracida mi "
                         "(kartin ayarina dokunmaz, PC'nin 4E onbellegini okur)")
    ap.add_argument("--kip", choices=("bagli", "rastgele"), default="bagli", help="E7 sifirlama zamanlamasi")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.liste:
        liste()
        return 0
    _moduller()
    ham = KBAG.SeriKart(a.port)
    try:
        ham.ac()
    except RuntimeError as h:
        print(f"HATA: {h}")
        return 2
    time.sleep(1.0)
    if a.basladi:
        # E7: Tezgah AKISI KURULMAZ (o kartin bildirim ayarini yazar ve temizlikte siler)
        try:
            basladi_kaybi(SeriYakala(ham), a.basladi, a.kip)
        except Iptal as h:
            print(f"\nDURDU: {h}")
            return 2
        finally:
            ham.kapat()
        print(f"\n{gecti}/{gecti + kaldi} tezgah denetimi gecti")
        return 0 if kaldi == 0 else 1
    t = Tezgah(SeriYakala(ham), a.http, a.tekrar, a.ip, a.ustune_yaz)
    sonuc = 0
    try:
        t.calistir()
    except Iptal as h:
        print(f"\nDURDU: {h}")
        sonuc = 2
    except KeyboardInterrupt:
        print("\nKesildi (Ctrl+C) — temizlik yapiliyor")
        sonuc = 130
    except Exception as h:                                     # noqa: BLE001
        print(f"\nBEKLENMEDIK HATA: {type(h).__name__}: {str(h)[:200]}")
        sonuc = 1
    finally:
        try:
            t.temizlik()
        finally:
            ham.kapat()
    print(f"\n{gecti}/{gecti + kaldi} tezgah denetimi gecti")
    return sonuc or (0 if kaldi == 0 else 1)


if __name__ == "__main__":
    sys.exit(main())
