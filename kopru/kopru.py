# -*- coding: utf-8 -*-
"""PC KOPRUSU — kart ile tarayicilar arasinda role, arsiv ve surucu hakemi.

    python kopru/pc.py                    # PC uygulamasi (onerilen giris noktasi)
    python kopru/kopru.py                 # ayni sey (eski komut, pc.py'ye devreder)
    python kopru/kopru.py --port COM7
    python kopru/kopru.py --kayit arsiv/2026-09-10.satir --http-port 8771   # olu tekrar
    python kopru/kopru.py --lan           # yerel aga SALT OKUMA (yalniz p0)

Panel: http://olcum.localhost:8770 (yalniz bu bilgisayar; `pc_ayar.py` PC1).

🔴 KOPRUNUN ASIL DEGERI GUZEL ARAYUZ DEGIL, ROLE OLMASI.

Kopru kartin satir akisini (USB ya da WiFi) N tarayiciya cogaltiyor:
tarayicilar karta degil kopruye baglanir, kartta TEK `/akis` yuvasi tutulur.
⚠ (2026-10-03) Eski gerekce "kartin SSE'si tek istemcili, her HTTP istegi
  loop()'u blokluyor" artik GECERSIZ: B28'den beri web cekirdek 0'da ayri
  gorevde, olcum cekirdek 1'de; kart en cok 4 `/akis` istemcisine (AKIS_AZAMI)
  hizmet ediyor. Koprunun bugunku degeri (alt proje 4, `pc.py` tek surec):
    * USB'de dogrulanmis kart yoksa kartla WiFi'den ESLESMIS CIHAZ olarak konusur
      (kart_wifi.py: imzali /akis ve /komut, p0 imzasiz); kart artik ikinci
      /akis'i reddetmiyor, `/kopru` kaydi ve CORS izni kalkti (firmware A3-4B);
    * kartin kayitlarini arka planda diske esitler (arka_esitle.py, 4C) ve panele
      o arsivi + kartin uclarini imzali vekil eder (vekil.py, 4D);
    * MQTT bildirimlerine abone olup Windows bildirimi gosterir (pc_bildirim.py, 4E);
    * paneli guvenli yerel kokenden (`olcum.localhost`, PWA kabugu 4F) sunar.
  4G (gercek kart): 6 tarayici sekmesi + komut istemcisi kartta TEK yuva tuttu;
  kalan 3 yuvaya kullanicinin tarayicisi + 2 dogrudan istemci, sonraki `event: dolu`.
  Eski `.satir` gunlugu (B35) yalniz satir arsivi; kayitlarin asil arsivi 4C'ninki.

── GUVENLIK (4A, PC2) ────────────────────────────────────────────────
Kart USB'de KIMLIK SORMAZ: USB'ye yazabilen her sey karta `Ns`/`GF!`/`p1`
yaptirabilir. Bu yuzden kopru:
  * varsayilan YALNIZ 127.0.0.1'e baglanir; `--lan` ile butun arayuzlere
    acilirsa dongu DISI istemciler SALT OKUMA (gorur, yalniz `p0`);
  * yalniz localhost / *.localhost / IP adresli Host basligini kabul eder
    (DNS yeniden baglama: kotu bir site kendi adini 127.0.0.1'e cozdurup
    ayni koken sayilamaz);
  * E ve Q komutlarini kimseden tasimaz; `EK` anahtar satirini ve USB'ye
    ozel parola satirlarini ne yayinlar ne arsivler (onekli/bolunmus da);
  * baska KOKENDEN gelen tarayici istegini (`Sec-Fetch-Site` / `Origin`)
    yan etkili uclarda reddeder: `<img src=".../skop.bin">` karta `t`
    yollatamaz, `.../akis` suruculugu kapamaz (4A inceleme);
  * `/skop.bin` kendi `t`sini yalniz `/komut`'un kapisindan gecerse yollar
    (`X-Olcum` + surucu jetonu, `komut_izinli`).

── ROLE BAYT-SEFFAF ──────────────────────────────────────────────────
Karttan gelen satir aynen `data: <satir>` olarak yayiliyor. Firmware,
`sahte-kart.js` ve kopru AYNI baytlari konusuyor; arayuzun tek
ayristiricisi bu yuzden yetiyor. `test_kopru.py` bunu bayt-bayt siniyor.

── KOMUT UCU: /komut ─────────────────────────────────────────────────
Kartin kendi ucu da `/komut` (B22.4): istemci KOPRUYE mi KARTA mi bagli
  oldugunu bilmek zorunda kalmiyor. Ayni yol, ayni yontem, ayni `X-Olcum`;
  kart eslesmis cihazdan imza da bekler — kopru kendi cihaziyla imzalar
  (panelin imza basliklarini TASIMAZ, 4D-7).

── SURUCU HAKEMI ─────────────────────────────────────────────────────
N izleyici, BIR surucu. Jeton kimdeyse kalibrasyon/menzil/pil onda.
🔴 TEK ISTISNA: `p0` (pil desarjini DURDUR) her zaman, jetonsuz,
   kimliksiz gecer. Baslatmak yetki ister; durdurmayi hicbir sey
   geciktiremez.

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import http.server
import ipaddress
import json
import queue
import re
import secrets
import select
import socket
import socketserver
import sys
import threading
import time
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"
# 3A (P4): panel paylasilan hesabi `/ortak/<ad>.js`ten `import` ediyor —
# kart LittleFS'ten, `arayuz3/sunucu.py` ve kopru `ortak/src/`ten AYNI
# dosyayi sunuyor. DUSME DEGIL: yalniz bu onek, yalniz `<ad>.js`.
ORTAK = KOK / "ortak" / "src"
ORTAK_AD = re.compile(r"[a-z0-9_-]+\.js")
# `app.js` ES modulu: tarayici modul betigini yalnizca JavaScript MIME
# turuyle calistirir; `mimetypes` Windows kayit defterinden `.js` ->
# `text/plain` okuyabiliyor. Elle sabitleniyor.
JS_TURU = "text/javascript"

sys.path.insert(0, str(BURASI))
from arsiv import Arsiv, SkopCozucu, skop_ikili           # noqa: E402
import kart_baglanti                                      # noqa: E402
import pc_ayar                                            # noqa: E402
import vekil                                              # noqa: E402  (4D: PC arsivi + kart vekili)

# 4A (PC1): TEK port, yalniz 127.0.0.1. Eskiden 0.0.0.0:80 -> LAN IP:80 ->
# 0.0.0.0:8770 diye dusuyordu (stok-takip 127.0.0.1:80'i tutuyor); koken
# porta bagli oldugu icin artik DUSULMUYOR — gerekce pc_ayar.py'de.
PORT = pc_ayar.PORT

# Her taşımada, jetonsuz, kimliksiz gecen komutlar.
SERBEST_KOMUTLAR = {"p0"}

# 4I: `/akis` isleyicisi bu aralikla istemcinin soketini yokluyor (kapandi mi).
# Kart bostayken akisa satir gelmez; kopus yalniz 15 s'lik kalp atisinda fark
# edilseydi yenilenen sekme o kadar izleyici kalirdi. Hedef: rol <= ~2 s'de bosalsin.
AKIS_YOKLAMA_S = 0.5
KALP_S = 15.0
# 4I (inceleme): surucunun akislari kapaninca rol bu kadar YENIDEN YUKLENME icin bekler.
# Yenilenen sekmenin yeni /akis'i eski isleyici kapanisi fark ettikten SONRA geliyor;
# rol hemen yasayan arka sekmeye verilseydi yenilenen sekme izleyici kalirdi (403).
AKIS_DEVIR_BEKLE_S = 3.0

# 4A (PC2): dongu DISI istemcinin (yerel ag) ret sebebi.
LAN_RET = ("yerel agdan salt okuma: bu baglanti yalniz izleyebilir ve `p0` (DURDUR) "
           "gonderebilir. Komut icin kopru calisan bilgisayarda "
           f"{pc_ayar.adres()} adresini acin")

# 4A (D5 #12): yayinlanmayan / arsivlenmeyen satirlar.
#  * `EK <n> <64 hex>` cihaz anahtari (kart `Ep` yanitini YALNIZ seriye basar).
#    Kart onu UC ayri `ham()` cagrisiyla basiyor; araya ESP-IDF gunlugu girerse
#    satir ONEKLENIR ("W (12) wifi: ..EK 3 ab..") ya da anahtar ALT SATIRA duser.
#    Eski suzgec yalniz `startswith("EK ")` idi: ikisini de kaciriyordu.
#  * "(yalniz USB)" isaretli satirlar — `N?` ve AP kipindeki acilis afisi AP
#    parolasini ham UART'a basiyor (B72.D0: aga cikmasin diye). Kopru ham UART'i
#    okudugu icin o satiri ag istemcilerine VE arsive tasiyordu.
#  Isaretli satir TAMAM degilse (EK satirinda 64 onaltilik yok, ya da USB'ye ozel
#  parola satiri — degerin bolunup bolunmedigi bilinemez) sonraki GIZLI_PENCERE
#  satir da duser: bolunmus deger orada. Tam `EK` satirinda pencere ACILMAZ
#  (ardindan gelen olcum satirlari bosuna kaybolmasin).
#  Pencere disinda: harf iceren >= 24 onaltilik dizisi (anahtar parcasi) duser;
#  16'lik kart kimligi ve uzun ondalik sayilar GECER.
#  4A inceleme: isaretler DARALTILDI (yanlis pozitif 2 olcum satirini da yutuyordu):
#  `F` yaniti "... YUKSEK 1.50" `EK \d`ye, `NA` onayi "* AP parolasi kaydedildi"
#  `AP parolas`a takiliyordu. Firmware'in TEK EK bicimi "EK %u " (ardindan anahtar):
#  sayidan sonra bosluk ya da satir sonu sart. AP parolasi isareti "AP parolasi
#  (yalniz USB): " — bolunmus parcasi yalniz ardindan " (" ya da satir sonu gelirse.
EK_DESEN = re.compile(r"EK \d+(?: |$)")
EK_TAM = re.compile(r"EK \d+ [0-9A-Fa-f]{64}")
USB_GIZLI = re.compile(r"\(yalniz USB\)|AP parolas(?:i? *$|i \()", re.I)
HEX_UZUN = re.compile(r"[0-9A-Fa-f]{24,}")
GIZLI_PENCERE = 2

# Karta yakalama YAPTIRAN komutlar (tam eslesme).
#
# 🔴 `tb0`/`tl500` gibi AYAR komutlari bu kumede DEGIL — onlar yakalama
#    uretmiyor, yalnizca `T ...` ayar satiri basiyor. Onek eslemesi
#    yapilsaydi her ayar degisikligi bosuna bir yakalama beklerdi.
#
# ⚠ `tB` -> `t` CEVRILIYOR. Arayuz ikili tasiyicida `tB` yolluyor; `tB`
#   dokumu seri porta HIC basmiyor, gövdeyi kartin kendi HTTP ucuna
#   birakiyor. Kopru ise karta USB'den bagli — kartin WiFi'si kapali bile
#   olabilir. Cevirmeseydik kopru kendi `t`sini yollamak zorunda kalir ve
#   kart IKI KEZ yakalardi (biri bosa, ustelik ikisi farkli dalga).
SKOP_KOMUTLARI = {"t", "tB", "ta"}

# Canli yakalamanin tavani. Kartin kendi yakalama zaman asimi
# `pencere_ms * 1.2 + 300`; ustune ASCII dokumun seri porttan gecisi
# geliyor: 4000 ornek ~20 250 B, 115 200 baud'da ~1.8 s. 20 s arayuzun
# `osiloBekliyor` tavaniyla AYNI — arayuz vazgectikten sonra donen bir
# yanit kullaniciya hicbir sey soylemezdi.
SKOP_BEKLE_SN = 20.0

# 4A inceleme: `?gun=` dosya yoluna giriyor — yalniz YYYY-AA-GG (yol gecisi, UNC).
GUN_DESEN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# 4H: yerel ag istemcisine verilen 403'lerin ISARETI. Panel bu baslikla ham ret metni yerine
# cevrilmis "yerel agdan salt okuma — bu PC'den ya da karta dogrudan" uyarisini gosterir. Yalniz
# LAN_RET'li retlerde (capraz koken / surucu degil retlerinde YOK); kart bu basligi hic yollamaz.
LAN_ISARET = ("X-Kopru-Ret", "lan")

# 4H: koprunun sundugu panel kabugunun surumu (sw.js `SURUM`, arayuz-uret.py `kabuk_surumu` yazar).
SW_SURUM = re.compile(r"^const SURUM = '([0-9a-f]{12})';$", re.M)


def kabuk_surumu() -> str | None:
    """4H: `/durum` `kabuk` — panel Ayarlar > Gelismis'te kartin arayuz surumunun yaninda gosterir."""
    try:
        m = SW_SURUM.search((ARAYUZ / "sw.js").read_text(encoding="utf-8"))
    except OSError:
        return None
    return m.group(1) if m else None


CAPRAZ_RET = ("baska bir kokenden (site) gelen istek reddedildi — panel yalniz "
              f"{pc_ayar.adres()} adresinden kullanilir")
TETIK_RET = ("X-Olcum basligi gerekli: canli yakalama karta `t` yollatir (komut) — "
             "panel yakalamayi `/komut` ile baslatir")


def dongu_mu(ip: str) -> bool:
    """Istemci adresi bu bilgisayar mi (127/8, ::1, IPv4-esli 127)? Bozuk -> HAYIR."""
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    return a.is_loopback


def host_gecerli(host: str | None) -> bool:
    """Host basligi: localhost, *.localhost ya da IP adresi. Baslik yoksa kabul.

    DNS yeniden baglama korumasi: bir tarayici BASKA bir adla (kotu.example)
    bu sunucuya geliyorsa o ad 127.0.0.1'e cozdurulmus demektir; sayfa ayni
    koken sayilip `X-Olcum` basligini on-ucussuz ekleyebilir. Tarayici Host'u
    hep yazar; basliksiz istek tarayicidan gelmez.
    """
    if not host:
        return True
    h = host.strip().lower()
    if h.startswith("["):
        h = h[1:].split("]", 1)[0]
    elif h.count(":") == 1:
        h = h.split(":", 1)[0]
    h = h.rstrip(".")
    if h == "localhost" or h.endswith(".localhost"):
        return True
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


def capraz_mi(sec_fetch_site: str | None, origin: str | None, host: str | None) -> bool:
    """Istek BASKA bir kokenden (site) mi geliyor? (4A inceleme: CSRF)

    `<img src="http://127.0.0.1:8770/skop.bin">` ozel baslik EKLEYEMEZ ama GET
    yine de sunucuya ulasir: `X-Olcum` yalniz POST/fetch'i korur. Tarayici her
    istege `Sec-Fetch-Site` yazar (baska port = `same-site`, baska ad =
    `cross-site`); yalniz `same-origin` (panelin kendisi) ve `none` (adres
    cubugu) kabul. `Origin` varsa Host ile AYNI koken olmali. Basliksiz istek
    tarayicidan gelmiyor (curl, araclar) — kabul.
    """
    if sec_fetch_site is not None and sec_fetch_site.strip().lower() not in ("same-origin", "none"):
        return True
    if origin is not None:
        h = (host or "").strip().lower()
        if not h or origin.strip().lower().rstrip("/") != "http://" + h:
            return True
    return False


class GizliSuzgec:
    """Satir yayinlanir/arsivlenir mi? (D5 #12 — gerekce EK_DESEN'in ustunde)."""

    def __init__(self):
        self.pencere = 0

    def gecir(self, satir: str) -> bool:
        if EK_DESEN.search(satir) or USB_GIZLI.search(satir):
            if not EK_TAM.search(satir):
                self.pencere = GIZLI_PENCERE
            return False
        if self.pencere > 0:
            self.pencere -= 1
            return False
        for m in HEX_UZUN.finditer(satir):
            if any(c in "abcdefABCDEF" for c in m.group(0)):
                return False
        return True


def lan_ip() -> str:
    """Disari bakan arayuzun IP'si. Paket gondermeden ogreniyor."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Kopru:
    """Yukari-akis ile aboneler arasindaki durum. HTTP'den bagimsiz."""

    def __init__(self, kart, arsiv_dizini: Path):
        self.kart = kart
        self.arsiv = Arsiv(arsiv_dizini)
        self.aboneler: list[queue.Queue] = []
        self.kilit = threading.Lock()
        self.jetonlar: dict[str, float] = {}
        self.surucu: str | None = None
        # 4I: yasayan `/akis` baglantilari ({jeton, soket, kuyruk, yerel, no}) ve en az
        # bir `/akis`i olmus jetonlar — "surucunun sekmesi kapandi mi" bunlardan okunur.
        self.akislar: list[dict] = []
        self.akisli: set[str] = set()
        self._akis_no = 0
        # 4I (inceleme): surucunun akislarinin kapali bulundugu ilk an (monotonic); None =
        # surucu yasiyor ya da rol devredildi. Pencere (AKIS_DEVIR_BEKLE_S) icinde rol yalniz
        # YENI kaydolan yerel akisa (yenilenen sekme) gecer, zaten acik sekmelere degil.
        self._bosaldi: float | None = None
        self.calisiyor = False
        self.son_satir = ""
        self.satir_adedi = 0
        self.arsiv_hatasi: str | None = None
        self.suzgec = GizliSuzgec()
        # 4C: arka plan esitlemesi (arka_esitle.ArkaEsitleme) — pc.esitleme_kur baglar
        self.esitleme = None
        self.esitleme_neden: str | None = None
        # 4A inceleme: OtoSeriKart'in baglanti sayaci; 0'dan — Kopru'dan once
        # acilmis bir baglantinin ilk satirlari da pencereye girsin
        self._baglanti_no = 0
        # OtoSeriKart durum degisikliklerini (kart yok / baglandi / koptu)
        # akisa soyler — arsive DEGIL, olcum degil.
        if hasattr(kart, "bildir"):
            kart.bildir = self.yayinla
        # ── skop yakalama (B35) ──────────────────────────────────────
        # 🔴 KOPRU KIPINDE SKOP HIC CALISMIYORDU. Arayuz `TasiyiciAkis`
        #    icin `skop: 'ikili'` ilan ediyor ve `/skop.bin` cekiyor;
        #    sayfa kopruden geldiginde o istek KOPRUYE gidiyor, kopru de
        #    `arayuz3/`yi servis ettigi icin 404 donuyordu. Yani tam da
        #    kullanicinin "sekilleri gormek + kayit almak" istedigi kipte
        #    osiloskop olu bir dugmeydi.
        #    Cozum: kopru `t` (ASCII dokum) gonderip blogu seri akistan
        #    toplar ve KARTIN BICIMINDE ikili dondurur. Firmware
        #    degismiyor, role bayt-seffaf kaliyor, ve dokum `Serial`den
        #    gectigi icin AYNI ANDA arsive de duser — kayit ozelligi
        #    bunun yan urunu.
        self.skop_cozucu = SkopCozucu()
        self.skop_son: dict | None = None
        self.skop_hata: str | None = None
        self.skop_olay = threading.Event()
        self.skop_kilit = threading.Lock()      # tek anda tek yakalama
        self.skop_kurulu = False    # arayuz komutu yolladi, cevap bekleniyor
        self.skop_adedi = 0

    # ── abonelik ─────────────────────────────────────────────────────
    def abone_ol(self) -> queue.Queue:
        k = queue.Queue(maxsize=2000)
        with self.kilit:
            self.aboneler.append(k)
        return k

    def abonelikten_cik(self, k: queue.Queue) -> None:
        with self.kilit:
            if k in self.aboneler:
                self.aboneler.remove(k)

    def yayinla(self, satir: str) -> None:
        with self.kilit:
            hedefler = list(self.aboneler)
        for k in hedefler:
            try:
                k.put_nowait(satir)
            except queue.Full:
                # 🔴 YAVAS ISTEMCI OTEKILERI YAVASLATAMAZ. Kuyruk dolarsa
                #    o istemcinin satiri DUSER; blokla beklemek koprunun
                #    tamamini o istemcinin hizina indirirdi — kartin
                #    `loop()`'unu bloklamamak icin kuruldugumuz seyin
                #    aynisini PC'de tekrarlamak olurdu.
                pass

    # ── jeton / surucu ───────────────────────────────────────────────
    def jeton_ver(self, surucu_olabilir: bool = True) -> str:
        j = secrets.token_urlsafe(12)
        with self.kilit:
            self.jetonlar[j] = time.time()
            # ilk baglanan surucu olur — 4A (PC2): yerel agdan baglanan ASLA
            if self.surucu is None and surucu_olabilir:
                self.surucu = j
        return j

    def surucu_mu(self, jeton: str | None) -> bool:
        return bool(jeton) and jeton == self.surucu

    # ── 4I: surucunun akisi kapaninca rol birakilir ──────────────────
    @staticmethod
    def soket_kapali(s) -> bool:
        """Karsi taraf baglantiyi kapatti mi? (okunabilir + 0 bayt = FIN; hata = kopuk)"""
        try:
            okunur, _, _ = select.select([s], [], [], 0)
            if not okunur:
                return False
            return s.recv(1, socket.MSG_PEEK) == b""
        except (OSError, ValueError):
            return True

    def akis_kaydet(self, jeton: str, soket, kuyruk, yerel: bool) -> dict:
        """Yeni `/akis` baglantisi. Surucunun akisi olmusse rol HEMEN en yeniye (buna) gecer:
        yenilenen sekme ilk `kimlik`inde surucu olur, acilis komutlari 403 almaz."""
        with self.kilit:
            self._akis_no += 1
            b = {"jeton": jeton, "soket": soket, "kuyruk": kuyruk, "yerel": yerel,
                 "no": self._akis_no}
            self.akislar.append(b)
            self.akisli.add(jeton)
        self.surucu_yokla(haric=b)
        return b

    def akis_bitti(self, b: dict) -> None:
        with self.kilit:
            if b in self.akislar:
                self.akislar.remove(b)
        self.surucu_yokla()

    def surucu_yokla(self, haric: dict | None = None) -> str | None:
        """4I politikasi: surucunun BUTUN `/akis`lari kapandiysa rol, once YENIDEN YUKLENME
        penceresi (AKIS_DEVIR_BEKLE_S) icinde YENI kaydolan yerel akisa (`haric`, yenilenen
        sekme), pencere dolunca en yeni YASAYAN yerel (donguden) akisa gecer ve o akisa
        `kimlik` olayi gider. Aday yoksa rol bosta bekler:
        sonraki yerel `/akis` ya da yasayan bir yerel sekmenin komutu alir. Surucu yasiyorsa
        HICBIR SEY olmaz (iki acik sekme arasinda sessiz calma yok; acik yol /devral).
        Hic `/akis`i olmamis jeton (arac, test) olu sayilmaz."""
        zamanla = False
        with self.kilit:
            j = self.surucu
            if j is None or j not in self.akisli:
                return None
            if any(b["jeton"] == j and not self.soket_kapali(b["soket"]) for b in self.akislar):
                self._bosaldi = None
                return None
            simdi = time.monotonic()
            if self._bosaldi is None:
                self._bosaldi = simdi
                zamanla = True
            if (haric is not None and haric["yerel"] and haric["jeton"] != j
                    and not self.soket_kapali(haric["soket"])):
                # Yeni kaydolan yerel akis = yenilenen sekme (kullanicinin baktigi): hemen ona
                yeni = haric
            elif simdi - self._bosaldi < AKIS_DEVIR_BEKLE_S:
                # Pencere suruyor: yenilenen sekmenin yeni /akis'i henuz gelmemis olabilir;
                # rol acik (arka) sekmelere VERILMEZ. Pencere sonunda zamanlayici yeniden yoklar.
                yeni = None
            else:
                adaylar = [b for b in self.akislar
                           if b["yerel"] and b["jeton"] != j and not self.soket_kapali(b["soket"])]
                yeni = max(adaylar, key=lambda b: b["no"]) if adaylar else None
            if yeni is None:
                if zamanla:
                    t = threading.Timer(AKIS_DEVIR_BEKLE_S + 0.05, self.surucu_yokla)
                    t.daemon = True
                    t.start()
                return None
            self._bosaldi = None
            self.surucu = yeni["jeton"]
            hedef = [b for b in self.akislar if b["jeton"] == yeni["jeton"] and b is not haric]
        olay = ("kimlik", json.dumps({"jeton": yeni["jeton"], "surucu": True}))
        for b in hedef:
            try:
                b["kuyruk"].put_nowait(olay)
            except queue.Full:
                pass
        self.yayinla("* kopru: surucu degisti")
        return yeni["jeton"]

    def devir_kalan(self) -> float:
        """Yeniden yuklenme penceresinden kalan sure (s); pencere yoksa 0."""
        with self.kilit:
            if self._bosaldi is None:
                return 0.0
            return max(0.0, AKIS_DEVIR_BEKLE_S - (time.monotonic() - self._bosaldi))

    def devral(self, jeton: str) -> bool:
        with self.kilit:
            if jeton not in self.jetonlar:
                return False
            self.surucu = jeton
            self._bosaldi = None
        return True

    def komut_izinli(self, komut: str, jeton: str | None,
                     yerel: bool = True) -> tuple[bool, str]:
        # 1D: E komutlari (USB eslestirme, zorunluluk, cihaz silme) karta YALNIZ
        # dogrudan USB'den verilir; kopru agdan gelen istegi seriye tasimaz.
        # Son inceleme: kart seriyi \r ve \n'de BOLER; "?\nEz0" bas harfi denetimini
        # atlatip E komutunu karta ulastiriyordu. Kontrol karakterli komut hic gecmez.
        if any(ord(c) < 0x20 or ord(c) == 0x7F for c in komut):
            return False, "komutta satir sonu / kontrol karakteri olamaz"
        if komut.startswith("E"):
            return False, ("E komutlari yalniz USB seri konsoldan (kopru uzerinden "
                           "verilemez) — eslestirme icin kopru/imza.py esles-usb")
        # 1E (K9): Q komutlari MQTT araci parolalarini tasir — yalniz USB
        if komut.startswith("Q"):
            return False, "Q komutlari (MQTT bildirim ayari) yalniz USB seri konsoldan"
        if komut in SERBEST_KOMUTLAR:
            return True, ""
        # 4A (PC2): dongu disi istemci salt okuma — p0 YUKARIDA, bu ondan SONRA
        if not yerel:
            return False, LAN_RET
        if self.surucu is None:
            return True, ""
        if self.surucu_mu(jeton):
            return True, ""
        # 4I: surucunun sekmesi kapanmis ama isleyicisi henuz fark etmemis olabilir
        self.surucu_yokla()
        if self.surucu_mu(jeton):
            return True, ""
        # 4I (inceleme): yeniden yuklenme penceresi suruyorsa acik sekmenin komutu pencere
        # sonunu bekler: yenilenen sekme gelirse rol onundur (403), gelmezse rol buna gecer.
        kalan = self.devir_kalan()
        if kalan > 0:
            time.sleep(kalan + 0.05)
            self.surucu_yokla()
            if self.surucu_mu(jeton):
                return True, ""
        return False, ("bu oturum SURUCU degil — komut reddedildi. "
                       "`p0` (durdur) her zaman acik.")

    # ── yukari-akis dongusu ──────────────────────────────────────────
    def dongu(self) -> None:
        self.calisiyor = True
        while self.calisiyor:
            try:
                satir = self.kart.satir_oku(0.5)
            except Exception as e:                      # noqa: BLE001
                self.yayinla(f"! kopru: kart okunamadi — {e}")
                time.sleep(1.0)
                continue
            # 4A inceleme: her (yeniden) baglantida pencere ACILIR, asla
            # kisalmaz — port yarim satirdan acildiysa (SeriKart ilk parcayi
            # zaten atiyor) ya da baglanti bir isaretten hemen sonra koptuysa
            # kuyruk akisa / arsive gecmesin.
            no = getattr(self.kart, "baglanti_no", 0)
            if no != self._baglanti_no:
                self._baglanti_no = no
                self.suzgec.pencere = max(self.suzgec.pencere, GIZLI_PENCERE)
            if satir is None:
                continue
            if not self.suzgec.gecir(satir):
                # 1D + 4A: cihaz anahtari / USB'ye ozel parola — agdaki
                # istemcilere de arsive de GITMEZ (onekli/bolunmus da)
                continue
            self.son_satir = satir
            self.satir_adedi += 1
            # 🔴 ARSIV HATASI ROLEYI OLDUREMEZ. Onceden `yaz()` bir kez
            #    atinca bu iplik olup gidiyordu: kopru ayakta gorunur,
            #    ama ne arsiv ne SSE calisirdi ve HICBIR YERDE yazmazdi.
            #    Rolenin kendisi kritik islev; arsiv onemli ama ikincil.
            #    Sebep bir kez akisa basiliyor — sessiz kalmiyor.
            try:
                ms = self.arsiv.yaz(satir)
            except Exception as e:                        # noqa: BLE001
                ms = 0
                if not self.arsiv_hatasi:
                    self.arsiv_hatasi = str(e)
                    self.yayinla(f"! kopru: arsive yazilamiyor — {e}")
            self.skop_besle(satir, ms)
            self.yayinla(satir)

    def skop_besle(self, satir: str, ms: int = 0) -> None:
        """Yukari-akis satirini skop cozucusune ver.

        ⚠ ARSIVDEN SONRA, YAYINDAN ONCE cagriliyor ve satiri
          DEGISTIRMIYOR — role bayt-seffafligi bozulmuyor.
        """
        # Kart tetikleyemediyse bekleyeni hemen serbest birak; 20 s
        # bosuna beklemek kullaniciya "sanki calisiyor" hissi verirdi.
        if satir.startswith("! tetiklenemedi"):
            self.skop_hata = "kart tetikleyemedi"
            self.skop_olay.set()
            return
        blok = self.skop_cozucu.besle(satir, ms)
        if blok is not None:
            blok["gun"] = time.strftime("%Y-%m-%d")
            self.skop_son = blok
            self.skop_adedi += 1
            self.skop_olay.set()

    def skop_hazirla(self) -> None:
        """Yakalama komutu karta RELAY EDILMEDEN once cagriliyor.

        Arayuz once `/komut` ile `tB` yolluyor, 400 ms sonra `/skop.bin`
        cekiyor. Kopru komutu tanidiginda "bu yakalamanin cevabini
        bekliyorum" diye isaretleniyor; `/skop.bin` o zaman KENDI `t`sini
        yollamiyor, gelmekte olani bekliyor. Isaretlenmeseydi kart iki kez
        yakalar, arayuze DONEN dalga kullanicinin tetikledigi dalga
        OLMAZDI.
        """
        self.skop_olay.clear()
        self.skop_hata = None
        self.skop_son = None
        self.skop_cozucu.sifirla()
        self.skop_kurulu = True

    def skop_yakala(self, bekle: float = SKOP_BEKLE_SN,
                    tetik_izni: tuple[bool, str] | None = None) -> tuple[dict | None, str]:
        """Yakalamayi getir. (blok, hata) donduruyor.

        Arayuz komutu zaten yolladiysa (`skop_kurulu`) YALNIZCA bekliyor;
        yollamadiysa (curl, betik) kendisi `t` tetikliyor. Iki yolda da
        dokum `Serial`den gectigi icin yakalama ARSIVE de dusuyor —
        "geriye donuk kayit" ozelligi bunun yan urunu.

        4A inceleme: kendi `t`sini yollamak bir KOMUT — `tetik_izni` (izin,
        neden) verilmis ve izin yoksa PermissionError (HTTP 403); karta hicbir
        sey gitmez. Bekleme yolu (komut zaten `/komut`'tan gecti) izin istemez.
        """
        with self.skop_kilit:
            kendi_tetikledi = not self.skop_kurulu
            if kendi_tetikledi:
                if tetik_izni is not None and not tetik_izni[0]:
                    raise PermissionError(tetik_izni[1])
                self.skop_hazirla()
                try:
                    self.kart.yaz("t")
                except Exception as e:                    # noqa: BLE001
                    self.skop_kurulu = False
                    return None, f"karta yazilamadi: {e}"
            self.skop_kurulu = False
            if not self.skop_olay.wait(bekle):
                return None, f"kart {bekle:.0f} s icinde yakalama dondurmedi"
            if self.skop_hata:
                return None, self.skop_hata
            blok = self.skop_son
            if blok is None:
                return None, "blok toplanamadi"
            # Kirpik blok CIZILMIYOR: eksik dalga "olculmus" gibi
            # gorunurdu ve tekrar denemek ucuz.
            if not blok["tam"]:
                return None, (f"blok kirpik ({len(blok['ornek'])}/"
                              f"{blok['adet_bildirilen']} ornek)")
            return blok, ""

    def durdur(self) -> None:
        self.calisiyor = False
        self.arsiv.kapat()


class Isleyici(http.server.SimpleHTTPRequestHandler):
    kopru: Kopru = None                                  # sinif duzeyinde
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": JS_TURU}

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ARAYUZ), **k)

    def log_message(self, bicim, *args):
        if "--ayrintili" in sys.argv:
            super().log_message(bicim, *args)

    # ── yardimcilar ──────────────────────────────────────────────────
    def _jeton(self) -> str | None:
        return self.headers.get("X-Jeton")

    def _istemci_ip(self) -> str:
        return self.client_address[0]

    def _yerel(self) -> bool:
        """4A (PC2): istek bu bilgisayardan mi? Degilse SALT OKUMA."""
        return dongu_mu(self._istemci_ip())

    def _capraz(self) -> bool:
        """4A inceleme: tarayici istegi baska bir kokenden mi? (bkz. capraz_mi)"""
        return capraz_mi(self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin"),
                         self.headers.get("Host"))

    def _kapi(self) -> bool:
        """Her istekte once: Host denetimi. Reddettiyse yaniti yazmistir."""
        if not host_gecerli(self.headers.get("Host")):
            self._yanit(403, ("Host taninmiyor — kopruye yalniz "
                              f"{pc_ayar.adres()} ya da IP adresiyle "
                              "baglanilir (DNS yeniden baglama korumasi)").encode("utf-8"))
            return False
        return True

    def _yanit(self, kod: int, govde: bytes = b"", tip="text/plain", basliklar=()):
        self.send_response(kod)
        self.send_header("Content-Type", tip + "; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        for ad, deger in basliklar:
            self.send_header(ad, deger)
        self.end_headers()
        if govde:
            self.wfile.write(govde)

    def _lan_ret(self, metin: str = LAN_RET):
        """4A (PC2) yerel ag reddi — 4H: `X-Kopru-Ret: lan` isaretiyle (panel cevrilmis uyari yazar)."""
        self._yanit(403, metin.encode("utf-8"), basliklar=(LAN_ISARET,))

    # ── GET ──────────────────────────────────────────────────────────
    def _sorgu(self) -> dict:
        parca = self.path.split("?", 1)
        if len(parca) < 2:
            return {}
        return {a: d[0] for a, d in urllib.parse.parse_qs(parca[1]).items()}

    def do_GET(self):
        if not self._kapi():
            return
        yol = self.path.split("?")[0]
        if yol == "/durum":
            return self._durum()
        if yol == "/esitleme/durum":
            return self._esitleme_durum()
        # 4D (PC10/PC11): PC arsivi (salt okuma) + kartin uclarinin imzali vekili — kopru/vekil.py
        # (kapilari orada: yalniz bu bilgisayar, yalniz ayni koken)
        if yol in vekil.UCLAR:
            return vekil.isle(self, yol)
        if yol == "/bildirim/durum":                        # 4E
            return self._bildirim_durum()
        if yol in ("/akis", "/skop.bin", "/skop/liste", "/skop/al") and self._capraz():
            # 4A inceleme (CSRF): baska kokenden <img>/<script> GET'i — surucu jetonu
            # verilmez, karta yakalama yaptirilmaz, arsiv okunmaz
            return self._yanit(403, CAPRAZ_RET.encode("utf-8"))
        if yol == "/akis":
            return self._akis()
        if yol == "/skop.bin":
            return self._skop_canli()
        if yol == "/skop/liste":
            return self._skop_liste()
        if yol == "/skop/al":
            return self._skop_al()
        if yol.startswith("/ortak/"):
            return self._ortak(yol[len("/ortak/"):])
        return super().do_GET()

    def _ortak(self, ad: str):
        """`/ortak/<ad>.js` -> `ortak/src/<ad>.js` (3A, P4). Baska her ad 404."""
        dosya = ORTAK / ad
        if not ORTAK_AD.fullmatch(ad) or not dosya.is_file():
            return self._yanit(404, b"ortak modulu yok")
        self._yanit(200, dosya.read_bytes(), JS_TURU)

    def _durum(self):
        k = self.kopru
        d = {
            "kart": k.kart.ad,
            "satir": k.satir_adedi,
            "abone": len(k.aboneler),
            "arsiv_satir": k.arsiv.satir_adedi,
            "surucu_var": k.surucu is not None,
            # Arayuz KOPRUDE mi KARTTA mi oldugunu bundan anliyor: kart
            # `/durum` ucunu HIC acmiyor, yani bu alanin varligi zaten
            # koprunun imzasi. Ayri bir "kopru misin" ucu acmak ikinci
            # bir gercek kaynagi olurdu.
            "skop_arsiv": True,
            "skop_adedi": k.skop_adedi,
            # 4D: bu istemci PC arsivini (/arsiv/*) okuyabilir mi, kartin uclari WiFi vekilinden
            # (/pil, /kal/liste, /kunye.json) gelebilir mi — ikisi de YALNIZ bu bilgisayara
            "pc_arsiv": self._yerel(),
            "vekil": self._yerel() and vekil.wifi_al(k.kart) is not None,
            # 4H: koprunun sundugu panel kabugunun surumu (Gelismis'te kartin arayuz surumunun yaninda)
            "kabuk": kabuk_surumu(),
        }
        self._yanit(200, json.dumps(d).encode("utf-8"), "application/json")

    def _esitleme_durum(self):
        """4C: arka plan esitlemesinin son durumu (salt okuma, YALNIZ bu bilgisayardan — 4D panel
        kullanacak). Mutlak yol yok: arsiv adi veri dizinine gorelidir."""
        if not self._yerel():
            return self._lan_ret()
        es = self.kopru.esitleme
        d = es.durum() if es is not None else {
            "etkin": False, "neden": self.kopru.esitleme_neden or "esitleme kurulmadi"}
        self._yanit(200, json.dumps(d, ensure_ascii=False).encode("utf-8"), "application/json")

    # ── 4E: MQTT bildirim durumu ─────────────────────────────────────
    def _bildirim_durum(self):
        """4E: bildirim ipliginin durumu (salt okuma, YALNIZ bu bilgisayardan — sonraki panel bolumu
        kullanacak): bagli mi, son olay, ac/kapa ayarlari. Araci adresi / kullanici / parola / konu
        oneki / anahtar YOK (pc_bildirim.PcBildirim.durum)."""
        if not self._yerel():
            return self._lan_ret()
        b = getattr(self.kopru, "bildirim", None)
        if b is not None:
            d = b.durum()
        else:
            import pc_bildirim as PB                    # 4H: kapaliyken de panel ac/kapa ayarini gorsun
            acik, dil, uyari = PB.ayar_oku()
            d = {"etkin": False, "neden": getattr(self.kopru, "bildirim_neden", None) or "bildirim kurulmadi",
                 "ayar": acik, "dil": dil, "ayar_uyari": uyari}
        self._yanit(200, json.dumps(d, ensure_ascii=False).encode("utf-8"), "application/json")

    def _bildirim_ayar(self):
        """4H: panelin "Bildirimler (bu bilgisayar)" bolumu — sinif ac/kapa + bildirim dili ayar.json'a
        BIRLESTIRILIR (pc_bildirim.ayar_yaz: oteki anahtarlar aynen, bozuk dosyanin ustune yazilmaz).
        Kapilar /kapat ile AYNI: `X-Olcum`, yalniz bu bilgisayar, yalniz ayni koken; govde JSON ve
        KATI (ayar_istegi_coz: yalniz bilinen siniflar / true-false / dil — sir giremez). Bildirim ipligi
        ayari her kararda dosyadan okur: degisiklik hemen gecerli."""
        import pc_bildirim as PB
        if self.headers.get("X-Olcum") != "1":
            return self._yanit(400, "X-Olcum basligi gerekli".encode("utf-8"))
        if not self._yerel():
            return self._lan_ret()
        if self._capraz():
            return self._yanit(403, CAPRAZ_RET.encode("utf-8"))
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            return self._yanit(415, "govde application/json olmali".encode("utf-8"))
        try:
            degisiklik, dil = PB.ayar_istegi_coz(self._govde_metin)
        except ValueError as e:
            return self._yanit(400, str(e).encode("utf-8"))
        try:
            PB.ayar_yaz(degisiklik, dil)
        except (ValueError, OSError) as e:
            metin = str(e) if isinstance(e, ValueError) else f"{pc_ayar.AYAR} yazilamadi ({type(e).__name__})"
            return self._yanit(409, metin.encode("utf-8"))
        acik, dil, uyari = PB.ayar_oku()
        self._yanit(200, json.dumps({"ayar": acik, "dil": dil, "ayar_uyari": uyari}, ensure_ascii=False)
                    .encode("utf-8"), "application/json")

    # ── skop (B35) ───────────────────────────────────────────────────
    def _skop_canli(self):
        """Kartin `/skop.bin` ucunun kopru karsiligi — AYNI BICIM.

        Arayuz hangi tasiyicida oldugunu bilmek zorunda kalmasin diye
        yol da, bicim de, imza da kartinkiyle ayni. `/komut` ucunde
        alinan kararin aynisi (bkz. dosya basligi).
        """
        k = self.kopru
        # 4A (PC2): canli yakalama karta `t` YOLLATIR — okuma degil, komut
        if not self._yerel():
            return self._lan_ret()
        # 4A inceleme: kendi `t`si icin /komut'un kapisi (X-Olcum + surucu jetonu)
        if self.headers.get("X-Olcum") != "1":
            izin = (False, TETIK_RET)
        else:
            izin = k.komut_izinli("t", self._jeton(), yerel=self._yerel())
        try:
            blok, hata = k.skop_yakala(tetik_izni=izin)
        except PermissionError as e:
            return self._yanit(403, str(e).encode("utf-8"))
        if blok is None:
            return self._yanit(503, hata.encode("utf-8"))
        govde = skop_ikili(blok)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        # Yakalamanin arsivdeki kimligi — arayuz "bu kayit listede hangisi"
        # sorusunu ek istek atmadan yanitlayabilsin.
        self.send_header("X-Skop-Gun", str(blok.get("gun", "")))
        self.send_header("X-Skop-Ms", str(blok.get("ms", 0)))
        self.end_headers()
        self.wfile.write(govde)

    def _skop_liste(self):
        k = self.kopru
        s = self._sorgu()
        if "gun" in s and not GUN_DESEN.fullmatch(s["gun"]):
            return self._yanit(400, "gun YYYY-AA-GG olmali".encode("utf-8"))
        gunler = k.arsiv.gunler()
        gun = s.get("gun") or (gunler[-1] if gunler else None)
        # Gunluge yazilani okuyacagiz; henuz diske inmemis satirlar
        # listede gorunmezdi ("az once cektim, listede yok").
        k.arsiv.flush()
        kayitlar = k.arsiv.skop_ozet(gun) if gun else []
        kayitlar.reverse()                       # en yenisi basta
        d = {"gunler": gunler, "gun": gun, "kayitlar": kayitlar}
        self._yanit(200, json.dumps(d).encode("utf-8"), "application/json")

    def _skop_al(self):
        k = self.kopru
        s = self._sorgu()
        gun, ms = s.get("gun"), s.get("ms")
        if not gun or ms is None or not ms.lstrip("-").isdigit():
            return self._yanit(400, "gun ve ms gerekli".encode("utf-8"))
        if not GUN_DESEN.fullmatch(gun):
            return self._yanit(400, "gun YYYY-AA-GG olmali".encode("utf-8"))
        k.arsiv.flush()
        blok = k.arsiv.skop_bul(gun, int(ms))
        if blok is None:
            return self._yanit(404, "yakalama bulunamadi".encode("utf-8"))
        govde = skop_ikili(blok)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _akis(self):
        k = self.kopru
        yerel = self._yerel()
        jeton = self._jeton() or k.jeton_ver(surucu_olabilir=yerel)
        kuyruk = k.abone_ol()
        bag = k.akis_kaydet(jeton, self.connection, kuyruk, yerel)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            # Once kimlik: istemci jetonu saklayip komutlarda gonderiyor.
            self.wfile.write(b"retry: 3000\n\n")
            self._olay("kimlik", json.dumps(
                {"jeton": jeton, "surucu": yerel and k.surucu_mu(jeton)}))
            # 4A: kart yoksa / koptuysa yeni gelen de bilsin (OtoSeriKart)
            durum = getattr(k.kart, "durum_satiri", None)
            if durum:
                self.wfile.write(b"data: " + durum.encode("utf-8") + b"\n\n")
                self.wfile.flush()
            son_yazma = son_yokla = time.monotonic()
            while True:
                try:
                    satir = kuyruk.get(timeout=AKIS_YOKLAMA_S)
                except queue.Empty:
                    satir = None
                simdi = time.monotonic()
                # 4I: sekme kapandi / yenilendi mi — rolun bosalmasi bunu bekliyor
                if simdi - son_yokla >= AKIS_YOKLAMA_S:
                    son_yokla = simdi
                    if k.soket_kapali(self.connection):
                        break
                if satir is None:
                    if simdi - son_yazma >= KALP_S:
                        # Kalp atisi: NAT ve ara vekiller sessiz baglantiyi
                        # dusuruyor. Yorum satiri istemciye gorunmuyor.
                        self.wfile.write(b": kalp\n\n")
                        self.wfile.flush()
                        son_yazma = simdi
                    continue
                if isinstance(satir, tuple):        # 4I: yalniz bu akisa olay (rol devri)
                    self._olay(*satir)
                else:
                    self.wfile.write(b"data: " + satir.encode("utf-8") + b"\n\n")
                    self.wfile.flush()
                son_yazma = simdi
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            k.abonelikten_cik(kuyruk)
            k.akis_bitti(bag)

    def _olay(self, ad: str, veri: str):
        self.wfile.write(f"event: {ad}\ndata: {veri}\n\n".encode("utf-8"))
        self.wfile.flush()

    # ── POST ─────────────────────────────────────────────────────────
    def do_POST(self):
        # Govde ONCE okunuyor: erken ret yanitinda okunmamis govde Windows'ta
        # baglantiyi RST ile koparir, istemci 400/403 yerine ConnectionAborted gorur.
        self._govde_metin = self._govde()
        if not self._kapi():
            return
        yol = self.path.split("?")[0]
        if yol == "/komut":
            return self._komut()
        if yol == "/devral":
            return self._devral()
        if yol == "/kapat":
            return self._kapat()
        if yol == "/bildirim/ayar":                         # 4H
            return self._bildirim_ayar()
        self._yanit(404, b"bilinmeyen uc")

    def _yalniz_okuma(self):
        # PUT/DELETE/PATCH: kopru bunlari HIC kabul etmez. Varsayilan (BaseHTTPRequestHandler) govdeyi
        # okumadan 501 doner; okunmamis govde Windows'ta baglantiyi RST ile kopariyor ve istemci yanit
        # yerine ConnectionAborted goruyordu (zincirde yuk altinda 4D iddiasini kirmiziya ceviren buydu).
        self._govde()
        self._yanit(405, "yalniz okuma — bu uc yazma kabul etmez".encode("utf-8"))

    do_PUT = do_DELETE = do_PATCH = _yalniz_okuma

    def _govde(self) -> str:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n).decode("utf-8", "replace").strip()

    def _komut(self):
        k = self.kopru
        # 🔴 Ozel baslik SART. Capraz kokende preflight'a zorluyor ve
        #    <img>/<form> ozel baslik EKLEYEMEZ — yani bir web sayfasi
        #    kullaniciya fark ettirmeden komut gonderemiyor.
        if self.headers.get("X-Olcum") != "1":
            return self._yanit(400, "X-Olcum basligi gerekli".encode("utf-8"))
        metin = self._govde_metin
        if not metin:
            return self._yanit(400, b"bos komut")
        # 4A inceleme: baska kokenden komut (on-ucus zaten engelliyor; derinlemesine
        # savunma). `p0` HARIC — emniyet, her katmanda serbest.
        if metin not in SERBEST_KOMUTLAR and self._capraz():
            return self._yanit(403, CAPRAZ_RET.encode("utf-8"))
        izin, neden = k.komut_izinli(metin, self._jeton(), yerel=self._yerel())
        if not izin:
            return self._lan_ret() if neden == LAN_RET else self._yanit(403, neden.encode("utf-8"))
        # Yakalama komutuysa: cozucuyu hazirla ve `tB`yi `t`ye cevir
        # (gerekcesi SKOP_KOMUTLARI'nin yaninda).
        if metin in SKOP_KOMUTLARI:
            k.skop_hazirla()
            if metin == "tB":
                metin = "t"
        try:
            k.kart.yaz(metin)
        except Exception as e:                            # noqa: BLE001
            return self._yanit(502, f"karta yazilamadi: {e}".encode("utf-8"))
        # Yanit GOVDESI BOS: kartin cevabi zaten SSE'den geliyor. Govdede
        # de dondurmek ayni satirin arayuzde IKI KEZ islenmesi olurdu.
        self._yanit(204)

    def _devral(self):
        k = self.kopru
        if self.headers.get("X-Olcum") != "1":
            return self._yanit(400, "X-Olcum basligi gerekli".encode("utf-8"))
        if not self._yerel():
            return self._lan_ret()
        if self._capraz():
            return self._yanit(403, CAPRAZ_RET.encode("utf-8"))
        jeton = self._jeton()
        if not jeton or not k.devral(jeton):
            return self._yanit(403, "bilinmeyen oturum".encode("utf-8"))
        k.yayinla("* kopru: surucu degisti")
        self._yanit(204)

    def _kapat(self):
        """4A inceleme: kopruyu DURDURMA yolu (`pc.py --durdur`, `Kopruyu Durdur.bat`).

        Eskiden talimat "Gorev Yoneticisi > pythonw.exe" idi — ayni yoldan
        stok-takip'in arka plan sunucusu da calisiyor, yanlisi oldurulurdu.
        Yalniz bu bilgisayardan, `X-Olcum` ile, ayni kokenden.
        """
        if self.headers.get("X-Olcum") != "1":
            return self._yanit(400, "X-Olcum basligi gerekli".encode("utf-8"))
        if not self._yerel():
            return self._lan_ret()
        if self._capraz():
            return self._yanit(403, CAPRAZ_RET.encode("utf-8"))
        self._yanit(204)
        self.kopru.yayinla("* kopru: kapatiliyor (bu bilgisayardan istendi)")
        threading.Thread(target=self.server.shutdown, daemon=True).start()


class Sunucu(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    # 🔴 ISTEMCININ BAGLANTIYI KOPARMASI HATA DEGIL, NORMAL. SSE acik bir
    #    sekme kapaninca / sayfa yenilenince soket koparilir ve
    #    `handle_one_request` keep-alive okumasinda patlar. Varsayilan
    #    `handle_error` bunun icin konsola 25 satirlik yigin izi basiyordu:
    #    kullanici her sekme yenilemesinde "bir sey bozuldu" sanirdi ve
    #    GERCEK bir iz bu gurultunun icinde kaybolurdu.
    #    ⚠ YALNIZCA kopma ailesi susturuluyor; baska her istisna aynen
    #      basiliyor — "hatalari gizle" degil, "hata olmayani hata diye
    #      gostermeyi birak".
    SESSIZ = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError,
              TimeoutError)

    def handle_error(self, istek, istemci_adresi):
        if isinstance(sys.exc_info()[1], self.SESSIZ):
            return
        super().handle_error(istek, istemci_adresi)
    # Windows'ta allow_reuse_address BASKA bir surecin aktif tuttugu portu
    # ele gecirmeye izin verir; yedek porta dusme hic tetiklenmez.
    # (stok-takip'in konsol.py'sinde de ayni not var.)
    if sys.platform == "win32":
        allow_reuse_address = False

    def server_bind(self):
        # 4A: olculdu (2026-10-03) — Windows'ta 127.0.0.1:P baska bir surecteyken
        # 0.0.0.0:P baglamasi BASARILI oluyor (dongu trafigi yine oteki surece
        # gider, kopru "acildi" der). SO_EXCLUSIVEADDRUSE bunu reddettiriyor.
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def sunucu_kur(kopru: Kopru, lan: bool = False, port: int = PORT) -> Sunucu:
    """4A (PC1/PC2): varsayilan YALNIZ 127.0.0.1; `lan` ile butun arayuzler
    (dongu disi istemciler salt okuma — Isleyici._yerel). Port mesgulse
    OSError: baska porta dusulmez (koken porta bagli, bkz. pc_ayar)."""
    # Sunucuya OZEL alt sinif: sinif niteligini paylasan iki sunucu (test,
    # ikinci kopru) birbirinin koprusunu ezmesin. `kopru` sonradan da
    # verilebilir: sunucu.RequestHandlerClass.kopru = ...
    isleyici = type("KopruIsleyici", (Isleyici,), {"kopru": kopru})
    return Sunucu(("0.0.0.0" if lan else "127.0.0.1", port), isleyici)


def main() -> int:
    """Eski giris noktasi — ayni secenekler `pc.py`'ye devrediliyor (4A, PC4)."""
    import pc
    return pc.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
