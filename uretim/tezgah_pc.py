# -*- coding: utf-8 -*-
"""4G — PC UYGULAMASI GERCEK KARTTA KABUL (tezgah; zincirde DEGIL).

    python uretim/tezgah_pc.py --o3 [--bosluk 200]
        Ö3 (spec §10): kopru (`pc.py --usb-yok`, GERCEK veri dizini, varsayilan ONAYLI) acik
        -> `Gb200` + ad "4G kabul" -> esitleme -> kopru >= 3 dk KAPALI (kart kaydetmeye devam)
        -> kopru acilir, bosluk ilk turda dolar -> `Gd` -> son esitleme -> kopru kapanir ->
        kartin akisi GECICI dizine bagimsiz indirilir: PC arsivi BAYT BAYT ayni mi.
    python uretim/tezgah_pc.py --o5 [--sekme 3] [--edge 2]
        Ö5 + 4 canli izleyici + p0 gecikmesi: kopru GECICI veri dizinliyle (`--onaysiz`), kartla
        arasinda bayt kaydeden TCP rolesi (`KayitciVekil`); bos dizinden TAM esitleme surerken
        basliksiz Edge sekmeleri kopruyu izler, vekil (/pil /kal/liste /kunye.json) dovulur,
        sekmeden 5 x `p0`; karta dogrudan `/akis` istemcileri yuvalar dolana dek (`event: dolu`; baska
        sureclerin karta acik baglantilari — ör. kullanicinin tarayicisi — sayilir). Sonra kayit
        bellekte taranir: web parolasi (yalniz OLCUM_PAROLA verildiyse), cihaz anahtari K, MQTT
        araci adresi/kullanici/parola/onek/yuk anahtari (DPAPI + OKB1 zarfi SUREC ICINDE
        cozulur, ASLA basilmaz), `Authorization:` basligi. Kayit ve gecici dizin SILINIR.
    secenekler: --http olcum.local

Kurallar (4G): karta yalniz `?`, `G?`, `Gb<ms>`, `Gd`, `Ga<id> <ad>`, `Gn<id> <not>`, `p0`.
`N?` ASLA. Flas yazilmaz. Kopru acikken AYRI surecten imzali istek yok (sayac yarisi): bagimsiz
indirme kopru KAPANDIKTAN sonra bu surecte. Saf yardimcilar (`KayitciVekil`, `sir_bicimleri`,
`kayitta_ara`, `yetki_basligi`, `akis_karsilastir`) B22a "4G"de cevrimdisi sinaniyor.
Yalniz standart kutuphane.
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))

import kayit_bicim as KB                                   # noqa: E402

PC_PY = KOK / "kopru" / "pc.py"
G_ALAN = ["durum", "oturum", "nokta", "sonraki", "onay", "doluluk", "onaysiz",
          "dusen", "yaz_azami_us", "sil_azami_us", "sil_adet", "tarama_ms", "son_hata",
          "son_not", "mesaj_dusen"]           # W2 (A3-W2): son iki alan; eski firmware 13 alan
G_ALAN_ESKI = 13
gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    gecti, kaldi = gecti + bool(kosul), kaldi + (not kosul)
    print(f"  [{'OK' if kosul else '!!'}] {ad}" + (f"   {ek}" if ek else ""), flush=True)


# ══ SAF YARDIMCILAR (B22a "4G") ═══════════════════════════════════════════════════════════
class KayitciVekil:
    """Iki yonu de BAYT BAYT kaydeden TCP rolesi: istemci (kopru) -> 127.0.0.1:port -> hedef.

    Kayit bellekte (`parcalar`: baglanti no, yon 'i' istemciden / 'k' karttan, zaman, bayt) ve
    istenirse `dosya`ya (ham, ekleme). HTTP'yi YORUMLAMAZ: ne gecerse o kaydedilir.

    `host_yaz`: istemci yonunde `Host:` satiri bununla DEGISTIRILIR (kaydedilen = karta giden).
    Kart DNS yeniden baglamaya karsi yalniz kendi adini/IP'sini kabul ediyor (`host_gecerli`,
    "Host reddedildi" 403) — kopru `127.0.0.1:<port>`'u yazdiginda baska hicbir bayt degismez."""

    def __init__(self, hedef_host: str, hedef_port: int = 80, dosya=None, host_yaz: str | None = None):
        # ad BIR KEZ cozulur: Windows `olcum.local`'i ~8 s'de bir 2.7 s'de yeniden cozuyor — her
        # baglantida cozmek rolenin kendisine gecikme eklerdi (4G'de p0 olcumunu boyle bozdu)
        self.hedef = (socket.gethostbyname(hedef_host), hedef_port)
        self.host_yaz = host_yaz.encode("ascii") if host_yaz else None
        self.dosya = Path(dosya) if dosya else None
        self.parcalar: list[tuple[int, str, float, bytes]] = []
        self._kilit = threading.Lock()
        self._dur = threading.Event()
        self._no = 0
        self._soketler: list[socket.socket] = []
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind(("127.0.0.1", 0))
        self.s.listen(32)
        self.port = self.s.getsockname()[1]
        self._is = threading.Thread(target=self._kabul, name="kayitci", daemon=True)

    def baslat(self) -> "KayitciVekil":
        self._is.start()
        return self

    def _kaydet(self, no: int, yon: str, veri: bytes) -> None:
        with self._kilit:
            self.parcalar.append((no, yon, time.monotonic(), veri))
            if self.dosya is not None:
                with open(self.dosya, "ab") as f:
                    f.write(veri)

    def _kabul(self) -> None:
        while not self._dur.is_set():
            try:
                i, _ = self.s.accept()
            except OSError:
                return
            with self._kilit:
                self._no += 1
                no = self._no
            threading.Thread(target=self._bagla, args=(i, no), daemon=True).start()

    def _bagla(self, i: socket.socket, no: int) -> None:
        try:
            k = socket.create_connection(self.hedef, timeout=15)
        except OSError:
            i.close()
            return
        k.settimeout(None)
        self._soketler += [i, k]
        a = threading.Thread(target=self._pompa, args=(i, k, no, "i"), daemon=True)
        b = threading.Thread(target=self._pompa, args=(k, i, no, "k"), daemon=True)
        a.start()
        b.start()

    def _pompa(self, kaynak: socket.socket, hedef: socket.socket, no: int, yon: str) -> None:
        try:
            while True:
                veri = kaynak.recv(65536)
                if not veri:
                    break
                if yon == "i" and self.host_yaz:
                    veri = _HOST.sub(b"Host: " + self.host_yaz + b"\r\n", veri)
                self._kaydet(no, yon, veri)
                hedef.sendall(veri)
        except OSError:
            pass
        for s, nasil in ((hedef, socket.SHUT_WR), (kaynak, socket.SHUT_RD)):
            try:
                s.shutdown(nasil)
            except OSError:
                pass

    def durdur(self) -> None:
        self._dur.set()
        try:
            self.s.close()
        except OSError:
            pass
        for s in self._soketler:
            try:
                s.close()
            except OSError:
                pass

    def akislar(self) -> dict[tuple[int, str], bytes]:
        """(baglanti, yon) -> o yondeki butun baytlar (TCP parcalari birlesik: bolunmus sir da bulunur)."""
        d: dict[tuple[int, str], bytearray] = {}
        with self._kilit:
            for no, yon, _, v in self.parcalar:
                d.setdefault((no, yon), bytearray()).extend(v)
        return {a: bytes(b) for a, b in d.items()}

    def istekler(self) -> list[dict]:
        """Her baglantidaki istek satirlari + yanit durum kodlari (sirayla eslenir) ve ilk
        baytlarin zamani: {no, yontem, yol, durum, t_istek, t_yanit}."""
        zaman: dict[tuple[int, str], float] = {}
        with self._kilit:
            for no, yon, t, _ in self.parcalar:
                zaman.setdefault((no, yon), t)
        ak = self.akislar()
        cikti = []
        for (no, yon), v in sorted(ak.items()):
            if yon != "i":
                continue
            istek = re.findall(rb"(GET|POST|PUT|DELETE|OPTIONS|HEAD) (\S+) HTTP/1\.[01]\r\n", v)
            durum = re.findall(rb"HTTP/1\.[01] (\d{3})", ak.get((no, "k"), b""))
            for j, (yontem, yol) in enumerate(istek):
                cikti.append({"no": no, "yontem": yontem.decode(), "yol": yol.decode("latin-1"),
                              "durum": int(durum[j]) if j < len(durum) else None,
                              "t_istek": zaman.get((no, "i")), "t_yanit": zaman.get((no, "k"))})
        return cikti


_HOST = re.compile(rb"(?im)^Host:[^\r\n]*\r\n")


def sir_bicimleri(deger) -> list[bytes]:
    """Bir sirrin kayitta gorunebilecegi bicimleri: ham, onaltilik (kucuk/BUYUK), base64
    (standart, URL-guvenli, dolgusuz) ve metinse yuzde kodlu. Tekrarsiz, bos olmayan."""
    ham = deger.encode("utf-8") if isinstance(deger, str) else bytes(deger)
    adaylar = [ham, ham.hex().encode(), ham.hex().upper().encode()]
    for b in (base64.b64encode(ham), base64.urlsafe_b64encode(ham)):
        adaylar += [b, b.rstrip(b"=")]
    if isinstance(deger, str):
        adaylar += [deger.upper().encode("utf-8"),
                    urllib.parse.quote(deger, safe="").encode("ascii")]
    gorulen, cikti = set(), []
    for a in adaylar:
        if a and a not in gorulen:
            gorulen.add(a)
            cikti.append(a)
    return cikti


_KELIME = re.compile(rb"[A-Za-z0-9_\-]")


def kayitta_ara(kayit, sirlar: dict) -> dict[str, dict]:
    """sirlar: {etiket: deger} -> {etiket: {"ham": n, "sinirli": n}}. `kayit` bayt ya da bayt
    listesi (her akis ayri aranir). "sinirli": iki yaninda harf/rakam/-/_ olmayan eslesme (bir
    kullanici adi daha uzun bir sozcugun parcasi olarak gecmisse ayirt edilsin). DEGER DONMEZ."""
    parcalar = [kayit] if isinstance(kayit, (bytes, bytearray)) else list(kayit)
    cikti = {}
    for etiket, deger in sirlar.items():
        ham = sinirli = 0
        for b in sir_bicimleri(deger):
            for p in parcalar:
                a = p.find(b)
                while a >= 0:
                    ham += 1
                    once = p[a - 1:a] if a else b""
                    sonra = p[a + len(b):a + len(b) + 1]
                    if not (once and _KELIME.fullmatch(once)) and not (sonra and _KELIME.fullmatch(sonra)):
                        sinirli += 1
                    a = p.find(b, a + 1)
        cikti[etiket] = {"ham": ham, "sinirli": sinirli}
    return cikti


_YETKI = re.compile(rb"(?im)^(?:proxy-)?authorization[ \t]*:")


def yetki_basligi(kayit) -> int:
    """`Authorization:` (ve `Proxy-Authorization:`) basligi kac kez gecti (buyuk/kucuk harf duyarsiz)."""
    parcalar = [kayit] if isinstance(kayit, (bytes, bytearray)) else list(kayit)
    return sum(len(_YETKI.findall(p)) for p in parcalar)


def _konumlar(veri: bytes) -> tuple[list, dict[int, tuple[int, int]]]:
    kayitlar = KB.akis_coz(veri)
    a, yer = 0, {}
    for k in kayitlar:
        n = KB.toplam_bayt(len(k.yuk))
        yer[k.sira] = (a, a + n)
        a += n
    return kayitlar, yer


def akis_karsilastir(pc: bytes, taze: bytes) -> dict:
    """PC arsivinin akisi ile karttan YENI indirilen akis: ORTAK sira araligi bayt bayt ayni mi.

    Arsiv kartta artik temizlenmis eski kayitlari tasiyabilir (onek), taze indirme arsivin son
    esitlemesinden sonra yazilmis kayitlari tasiyabilir (sonek): ikisi de KUSUR DEGIL, sayilir.
    Ortak aralik iki yanda da kesintisiz olmali; tek bayt farki `ayni` False."""
    pk, py = _konumlar(pc)
    tk, ty = _konumlar(taze)
    ortak = sorted(set(py) & set(ty))
    d = {"pc_kayit": len(pk), "taze_kayit": len(tk), "ortak": len(ortak),
         "pc_ilk": pk[0].sira if pk else None, "pc_son": pk[-1].sira if pk else None,
         "taze_ilk": tk[0].sira if tk else None, "taze_son": tk[-1].sira if tk else None,
         "yalniz_pc": len(set(py) - set(ty)), "yalniz_taze": len(set(ty) - set(py)),
         "tam_ayni": pc == taze, "ayni": False, "ortak_bayt": 0}
    if not ortak:
        return d
    a, b = ortak[0], ortak[-1]
    p_dilim = pc[py[a][0]:py[b][1]]
    t_dilim = taze[ty[a][0]:ty[b][1]]
    kesintisiz = [k.sira for k in pk if a <= k.sira <= b] == [k.sira for k in tk if a <= k.sira <= b]
    d["ortak_bayt"] = len(p_dilim)
    d["ayni"] = kesintisiz and p_dilim == t_dilim
    return d


# ══ CANLI ARACLAR ════════════════════════════════════════════════════════════════════════
class Sse(threading.Thread):
    """Basit SSE istemcisi: olaylari (zaman, ad, veri) toplar."""

    def __init__(self, host: str, port: int, yol: str = "/akis", basliklar=None, ad: str = ""):
        super().__init__(name=f"sse-{ad}", daemon=True)
        self.host, self.port, self.yol = host, port, yol
        self.basliklar = basliklar or {}
        self.olaylar: list[tuple[float, str, str]] = []
        self.http = None
        self.hata = None
        self._c = None
        self._dur = threading.Event()

    def run(self) -> None:
        try:
            self._c = http.client.HTTPConnection(self.host, self.port, timeout=45)
            self._c.request("GET", self.yol, headers=self.basliklar)
            y = self._c.getresponse()
            self.http = y.status
            ad, veri = None, []
            while not self._dur.is_set():
                s = y.fp.readline()
                if not s:
                    break
                s = s.decode("utf-8", "replace").rstrip("\r\n")
                if s == "":
                    if veri or ad:
                        self.olaylar.append((time.monotonic(), ad or "message", "\n".join(veri)))
                    ad, veri = None, []
                elif s.startswith("event:"):
                    ad = s[6:].strip()
                elif s.startswith("data:"):
                    veri.append(s[5:][1:] if s[5:6] == " " else s[5:])
        except Exception as e:                              # noqa: BLE001
            if not self._dur.is_set():
                self.hata = f"{type(e).__name__}: {e}"

    def kapat(self) -> None:
        self._dur.set()
        c = self._c
        if c is not None and c.sock is not None:
            try:
                c.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            c.close()

    def veriler(self, onek: str = "", bas: int = 0) -> list[str]:
        return [v for _, a, v in self.olaylar[bas:] if a == "message" and v.startswith(onek)]

    def olay(self, ad: str) -> str | None:
        return next((v for _, a, v in self.olaylar if a == ad), None)

    def bekle(self, kosul, sn: float, bas: int = 0):
        son = time.monotonic() + sn
        while time.monotonic() < son:
            for _, a, v in self.olaylar[bas:]:
                if kosul(a, v):
                    return v
            time.sleep(0.1)
        return None


def g_coz(satir: str) -> dict | None:
    p = satir.split()
    if (len(p) - 1 not in (len(G_ALAN), G_ALAN_ESKI) or p[0] != "G"
            or not all(x.lstrip("-").isdigit() for x in p[1:])):
        return None
    return dict(zip(G_ALAN, (int(x) for x in p[1:])))


class Kopru:
    """`kopru/pc.py`'yi alt surec olarak acar/kapatir; komutlar kendi `/akis` oturumuyla."""

    def __init__(self, ek: list[str], ortam: dict | None = None, gunluk: Path | None = None):
        import pc_ayar
        self.port = pc_ayar.PORT
        self.ek, self.ortam, self.gunluk = ek, ortam or {}, gunluk
        self.p = None
        self.akis: Sse | None = None
        self.jeton = None

    def ac(self, sn: float = 30.0) -> float:
        import pc
        if pc.zaten_calisiyor(self.port):
            raise SystemExit("8770'te kopru ZATEN acik — once `python kopru/pc.py --durdur`")
        env = {**os.environ, "OLCUM_TOAST_YOK": "1", **self.ortam}
        cikis = open(self.gunluk, "ab") if self.gunluk else subprocess.DEVNULL
        t = time.time()
        self.p = subprocess.Popen([sys.executable, str(PC_PY), "--usb-yok", "--tarayici-acma", *self.ek],
                                  env=env, stdout=cikis, stderr=subprocess.STDOUT, cwd=str(KOK))
        son = time.monotonic() + sn
        while time.monotonic() < son:
            if pc.zaten_calisiyor(self.port):
                return t
            if self.p.poll() is not None:
                break
            time.sleep(0.3)
        raise SystemExit(f"kopru acilmadi (cikis {self.p.poll()}) — gunluk: {self.gunluk}")

    def kapat(self) -> None:
        import pc
        if self.akis:
            self.akis.kapat()
            self.akis = None
        if pc.zaten_calisiyor(self.port):
            pc.durdur(self.port, bekle=10.0)
        if self.p is not None:
            try:
                self.p.wait(15)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait(5)
        self.p = None

    def istek(self, yol: str, veri: bytes | None = None, basliklar=None, sn: float = 10.0):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=sn)
        try:
            c.request("POST" if veri is not None else "GET", yol, body=veri, headers=basliklar or {})
            y = c.getresponse()
            return y.status, y.read()
        finally:
            c.close()

    def json(self, yol: str) -> dict:
        kod, govde = self.istek(yol)
        return json.loads(govde) if kod == 200 else {"_http": kod}

    def surucu_ol(self) -> None:
        self.akis = Sse("127.0.0.1", self.port, ad="kopru")
        self.akis.start()
        k = self.akis.bekle(lambda a, v: a == "kimlik", 10)
        if not k:
            raise SystemExit(f"kopru /akis kimlik vermedi ({self.akis.hata})")
        d = json.loads(k)
        self.jeton = d["jeton"]
        if not d.get("surucu"):
            self.istek("/devral", b"", {"X-Olcum": "1", "X-Jeton": self.jeton})

    def komut(self, metin: str) -> int:
        kod, _ = self.istek("/komut", metin.encode("utf-8"),
                            {"X-Olcum": "1", "X-Jeton": self.jeton or "", "Content-Type": "text/plain"})
        return kod

    def g(self, metin: str = "G?", kosul=lambda g: True, sn: float = 8.0) -> dict | None:
        bas = len(self.akis.olaylar)
        if metin:
            kod = self.komut(metin)
            if kod != 204:
                print(f"    ! {metin}: kopru HTTP {kod}")
                return None
        v = self.akis.bekle(lambda a, v: a == "message" and bool(g_coz(v)) and kosul(g_coz(v)), sn, bas)
        return g_coz(v) if v else None

    def esitleme_bekle(self, sonra: float, sn: float = 150.0) -> dict | None:
        """`son_basari` (duvar saati) `sonra`dan buyuk olana dek /esitleme/durum."""
        son = time.monotonic() + sn
        while time.monotonic() < son:
            d = self.json("/esitleme/durum")
            if (d.get("son_basari") or 0) > sonra and d.get("sonuc") == "tamam":
                return d
            time.sleep(1.0)
        return None


def _durum_oku(dizin: Path) -> dict:
    return json.loads((dizin / "durum.json").read_text(encoding="utf-8"))


def _kart_cihazi(host: str):
    import imza as IM
    import pc_ayar
    taban = IM.taban_url(host)
    kimlik = IM.bilgi(taban, 10.0)["kimlik"]
    return IM.Cihaz.yukle(pc_ayar.cihaz_dizini() / f"{kimlik}.json"), taban


def bagimsiz_indir(host: str, hedef: Path) -> dict:
    """Kartin akisinin TAMAMI gecici dizine — ONAYSIZ, eslesmis cihazla imzali (kopru KAPALIYKEN)."""
    import kayit_esitle as KE
    cihaz, taban = _kart_cihazi(host)
    t = time.monotonic()
    r = KE.Esitleyici(taban, hedef, None, cihaz=cihaz, parca_arasi=0.1).esitle()
    r["sure_s"] = round(time.monotonic() - t, 1)
    return r


# ══ Ö3 ═══════════════════════════════════════════════════════════════════════════════════
def o3(host: str, bosluk_s: float) -> None:
    import pc_ayar
    print(f"\n── Ö3: uzun kopukluk ({bosluk_s:.0f} s) + bosluk doldurma + bayt karsilastirma", flush=True)
    gunluk = Path(tempfile.mkdtemp(prefix="olcum-4g-")) / "kopru.log"
    kop = Kopru([], gunluk=gunluk)
    es3 = arsiv = None
    t_ac = kop.ac()
    try:
        es0 = kop.esitleme_bekle(t_ac - 1, 120)
        ok("kopru acildi, ilk esitleme turu tamam (GERCEK veri dizini, varsayilan onayli)",
           bool(es0), f"{es0 and {a: es0.get(a) for a in ('son_sira', 'kart_son_sira', 'onay', 'arsiv')}}")
        if not es0:
            return
        arsiv = pc_ayar.veri_dizini() / es0["arsiv"]
        kop.surucu_ol()
        g = kop.g("G?")
        if not g or g["durum"] != 1:
            ok("kartta suren kayit YOK (durum 1) — test kaydi baslatilabilir", False, f"{g}")
            return
        t_gb = time.time()
        g = kop.g("Gb200", lambda x: x["durum"] == 2, 8)
        oid = g["oturum"] if g else 0
        ok("Gb200: test kaydi basladi (imzali /komut kopru uzerinden)", bool(oid), f"{g}")
        if not oid:
            return
        bas = len(kop.akis.olaylar)
        for c in (f"Ga{oid} 4G kabul",
                  f"Gn{oid} 4G kabul: O3 bosluk doldurma, kopru {bosluk_s:.0f} s kapali"):
            kop.komut(c)
        time.sleep(2.0)
        notlar = [v for v in kop.akis.veriler("* G not", bas)]
        ok("Ga/Gn kuyruga girdi (iki '* G not kuyrukta')", len(notlar) >= 2, f"{len(notlar)}")
        es1 = kop.esitleme_bekle(t_gb + 3, 150)
        ok("kayit surerken bir esitleme turu daha (120 s aralik)", bool(es1),
           f"{es1 and (es1['son_sira'], es1['kart_son_sira'], es1['yeni_kayit'])}")
        if not es1:
            return
        kop.kapat()
        t_kapali = time.time()
        print(f"    kopru KAPALI {bosluk_s:.0f} s (kart kaydediyor)...", flush=True)
        time.sleep(bosluk_s)
        t_ac2 = kop.ac()
        es2 = kop.esitleme_bekle(t_ac2 - 1, 120)
        kapali_s = t_ac2 - t_kapali
        ok(f"kopru {kapali_s:.0f} s (>= 180) kapali kaldiktan sonra ilk turda bosluk doldu",
           bool(es2) and kapali_s >= 180 and es2["yeni_kayit"] > 0
           and es2["son_sira"] == es2["kart_son_sira"],
           f"{es2 and {a: es2.get(a) for a in ('yeni_kayit', 'son_sira', 'kart_son_sira')}}")
        if not es2:
            return
        dolum_s = round(es2["son_basari"] - es2["son_deneme"], 1)
        dolum_bayt = (es2.get("bayt") or 0) - (es1.get("bayt") or 0)
        kop.surucu_ol()
        g = kop.g("G?")
        ok("kart kopru kapaliyken kaydetmeyi SURDURDU (ayni oturum, durum 2)",
           bool(g) and g["durum"] == 2 and g["oturum"] == oid, f"{g}")
        t_gd = time.time()
        g = kop.g("Gd", lambda x: x["durum"] == 1, 8)
        ok("Gd: test kaydi durdu", bool(g), f"{g}")
        es3 = kop.esitleme_bekle(t_gd + 1, 150)
        ok("son esitleme: arsiv kartin son sirasinda, onay gitti ve kart dogruladi",
           bool(es3) and es3["son_sira"] == es3["kart_son_sira"] and es3.get("onay_dogrulandi"),
           f"{es3 and {a: es3.get(a) for a in ('yeni_kayit', 'son_sira', 'kart_son_sira', 'onay_gitti', 'onay_dogrulandi')}}")
    finally:
        kop.kapat()
    import pc
    ok("kopru kapandi (8770 serbest)", not pc.zaten_calisiyor())
    if not es3:
        return
    d = _durum_oku(arsiv)
    pc_bayt = (arsiv / "kayitlar.kyt").read_bytes()[:d["bayt"]]
    with tempfile.TemporaryDirectory(prefix="olcum-4g-taze-") as gd:
        r = bagimsiz_indir(host, Path(gd))
        taze = (Path(gd) / "kayitlar.kyt").read_bytes()
    k = akis_karsilastir(pc_bayt, taze)
    ok("PC arsivinin kayitlar.kyt'si kartin akisinin bagimsiz indirmesiyle BAYT BAYT ayni",
       k["ayni"] and k["yalniz_taze"] == 0, f"{k}; indirme {r['sure_s']} s")
    kayitlar = KB.akis_coz(pc_bayt)
    siralar = [x.sira for x in kayitlar if x.sira > es0["son_sira"]]
    kesintisiz = siralar == list(range(es0["son_sira"] + 1, es0["son_sira"] + 1 + len(siralar)))
    ot = KB.oturumlari_kur(kayitlar).get(oid)
    ok("arsivde test oturumu: ad '4G kabul', not, BITIR sebep 1 (kullanici), testin siralari kesintisiz",
       bool(ot) and ot.ad == "4G kabul" and len(ot.notlar) >= 1 and bool(ot.bitir)
       and ot.bitir.get("sebep") == 1 and kesintisiz,
       f"oturum {oid}: ad={ot and ot.ad!r} not={ot and len(ot.notlar)} bitir={ot and ot.bitir} "
       f"nokta={ot and len(ot.noktalar)} siralar {len(siralar)} kesintisiz={kesintisiz}")
    print(f"\n  Ö3 OZET: test oturumu {oid}; kopru {kapali_s:.0f} s kapali; bosluk {es2['yeni_kayit']} kayit / "
          f"{dolum_bayt} B, {dolum_s} s'de doldu; arsiv {d['son_sira']} son sira / {d['bayt']} B; "
          f"bagimsiz indirme {k['taze_kayit']} kayit, {r['sure_s']} s; ortak {k['ortak']} kayit "
          f"{k['ortak_bayt']} B ayni={k['ayni']}", flush=True)
    shutil.rmtree(gunluk.parent, ignore_errors=True)


# ══ Ö5 + 4 izleyici + p0 ════════════════════════════════════════════════════════════════
def _edge_sizinti(profiller=("olcum-edge-",)) -> int:
    """Komut satirinda VERILEN profil adlarindan biri gecen msedge surecleri.

    4G'de bulundu: ayni makinede baska bir koşu (zincir, baska calisma agaci) da `olcum-edge-`
    profilleri aciyor — genel onekle sayim BASKASININ tarayicisini sizinti sanar (ve "temizlik"
    onu oldururdu). Kabulde yalniz bu betigin acdigi profiller sayilir."""
    if sys.platform != "win32":
        return 0
    kosul = " -or ".join(f"$_.CommandLine -like '*{os.path.basename(p)}*'" for p in profiller)
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "@(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                        f"Where-Object {{ {kosul} }}).Count"],
                       capture_output=True, text=True, timeout=60)
    try:
        return int(r.stdout.strip() or 0)
    except ValueError:
        return -1


def _kart_baglantilari(host: str) -> dict[str, int]:
    """Bu betik DISINDAKI sureclerin karta (80) acik TCP baglantilari: surec adi -> adet.
    Kartin 4 `/akis` yuvasindan birini kullanicinin tarayicisi tutuyor olabilir (4G'de: chrome)."""
    if sys.platform != "win32":
        return {}
    ip = socket.gethostbyname(host)
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-NetTCPConnection -RemoteAddress {ip} -RemotePort 80 -State Established "
                        "-ErrorAction SilentlyContinue | ForEach-Object { \"$($_.OwningProcess)\" }"],
                       capture_output=True, text=True, timeout=60)
    say: dict[str, int] = {}
    for pid in r.stdout.split():
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        q = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-Process -Id {pid}).ProcessName"],
                           capture_output=True, text=True, timeout=30)
        ad = q.stdout.strip() or f"pid{pid}"
        say[ad] = say.get(ad, 0) + 1
    return say


def _sekme_ac(cdp_port: int, url: str) -> str:
    import urllib.request
    ist = urllib.request.Request(f"http://127.0.0.1:{cdp_port}/json/new?{url}", method="PUT")
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(ist, timeout=10) as y:
        return json.load(y)["webSocketDebuggerUrl"]


def _sekme_js(ws_url: str, ifade: str, sn: float = 30.0):
    from tarayici import _WS
    w = _WS(ws_url)
    try:
        w.s.settimeout(sn)
        w.gonder(json.dumps({"id": 1, "method": "Runtime.evaluate",
                             "params": {"expression": ifade, "returnByValue": True, "awaitPromise": True}}))
        while True:
            m = json.loads(w.al())
            if m.get("id") == 1:
                r = m.get("result", {})
                if "exceptionDetails" in r:
                    return {"_hata": str(r["exceptionDetails"].get("text"))}
                return r.get("result", {}).get("value")
    finally:
        w.kapat()


UYG = "document.querySelector('#uyg')._vnode.component.proxy"
JS_SAY = ("new Promise(r=>{let n=0;const es=new EventSource('/akis');"
          "es.onmessage=e=>{if(e.data.startsWith('D '))n++};setTimeout(()=>{es.close();r(n)},4000)})")
JS_P0 = ("(async()=>{const t0=performance.now();const r=await fetch('/komut',{method:'POST',"
         "headers:{'X-Olcum':'1','Content-Type':'text/plain'},body:'p0'});"
         "return [r.status, Math.round(performance.now()-t0)];})()")


def o5(host: str, sekme: int, edge_n: int) -> None:
    import bildirim
    import imza as IM
    import pc_ayar
    from tarayici import Tarayici
    print("\n── Ö5 + 4 izleyici + p0: kopru (gecici veri dizini, --onaysiz) <-> KAYITCI <-> kart", flush=True)
    gecici = Path(tempfile.mkdtemp(prefix="olcum-4g-o5-"))
    cihaz_dizin = pc_ayar.cihaz_dizini()                 # GERCEK (anahtar) — sayac dosyasi tek surecte
    kayit_dosyasi = gecici / "kayit.bin"
    vek = KayitciVekil(host, 80, kayit_dosyasi, host_yaz=host).baslat()
    gunluk = gecici / "kopru.log"
    kop = Kopru(["--onaysiz"], {"OLCUM_KART_HOST": f"127.0.0.1:{vek.port}",
                                 "OLCUM_PC_DIZIN": str(gecici / "pc"),
                                 "OLCUM_CIHAZ_DIZIN": str(cihaz_dizin)}, gunluk)
    tarayicilar: list = []
    dogrudan: list[Sse] = []
    sekmeler: list[str] = []
    vekil_kod: dict[str, list[int]] = {}
    dur = threading.Event()
    p0: list = []
    baglanti_n = None
    kart_ip = socket.gethostbyname(host)             # dogrudan istemciler: ad cozumu (2.7 s) olcume girmesin
    try:
        t_ac = kop.ac()
        kop.surucu_ol()
        d1 = kop.akis.bekle(lambda a, v: a == "message" and v.startswith("D "), 30)
        ok("kopru kayitci uzerinden karta WiFi'den baglandi (akista D satiri)", bool(d1),
           f"{kop.akis.veriler('* kopru') + kop.akis.veriler('! kopru')}")
        if not d1:
            return
        adres = f"{pc_ayar.adres()}/"           # /json/new sorgusunda `#` kaybolur: kok adres
        for _ in range(edge_n):
            t = Tarayici(auth_iptal=False)
            tarayicilar.append(t)
            t.git(adres)
            sekmeler.append(None)                    # ilk sekme Tarayici'nin kendi sayfasi
            for _ in range(sekme - 1):
                sekmeler.append(_sekme_ac(t.port, adres))

        def vekil_dov():
            while not dur.is_set():
                for yol in ("/pil", "/kal/liste", "/kunye.json"):
                    try:
                        kod, _ = kop.istek(yol, sn=15)
                    except OSError:
                        kod = -1
                    vekil_kod.setdefault(yol, []).append(kod)
                dur.wait(1.0)
        vt = threading.Thread(target=vekil_dov, daemon=True)
        vt.start()
        time.sleep(4.0)                              # sekmeler yuklensin, panel kopruye baglansin
        es_once = kop.json("/esitleme/durum")
        # p0: ilk Edge'in ilk sekmesinden (panelin kendi kokeni), tam esitleme SURERKEN
        for _ in range(5):
            p0.append((time.monotonic(), tarayicilar[0].js(JS_P0)))
            time.sleep(1.0)
        es_p0 = kop.json("/esitleme/durum")
        kop.komut("?")
        g = kop.g("G?")
        ok("kopru uzerinden imzali komutlar (`?`, `G?`) kartta yanitlandi",
           bool(g) and bool(kop.akis.veriler("A menzil=")), f"G={g}")
        # sekmeler kopruyu izliyor mu (her biri: panel bagli + kendi EventSource'u D satiri aliyor)
        sayim = []
        for i, t in enumerate(tarayicilar):
            sayim.append([t.js(f"{UYG}.bagli"), t.js(JS_SAY)])
            for ws in sekmeler[i * sekme + 1:(i + 1) * sekme]:
                sayim.append([_sekme_js(ws, f"{UYG}.bagli"), _sekme_js(ws, JS_SAY)])
        abone = kop.json("/durum").get("abone")
        ok(f"{len(sayim)} tarayici sekmesi ({edge_n} Edge) kopruden canli akis aliyor (panel bagli + D satiri)",
           len(sayim) == sekme * edge_n and all(b is True and isinstance(n, int) and n >= 5 for b, n in sayim),
           f"(bagli, 4 s'de D) {sayim}; kopru abone {abone}")
        # karta DOGRUDAN istemciler: kopru 1 yuva tutarken 4. istemci `dolu`
        for i in range(4):
            s = Sse(kart_ip, 80, ad=f"dogrudan{i}")
            s.start()
            dogrudan.append(s)
            ad = s.bekle(lambda a, v: a in ("kimlik", "dolu"), 8)
            if ad is not None and s.olay("dolu") is not None:
                break
            s.bekle(lambda a, v: a == "message" and v.startswith("D "), 5)
        alan = [s for s in dogrudan if s.olay("dolu") is None and s.veriler("D ")]
        dolu = [s for s in dogrudan if s.olay("dolu") is not None]
        diger = _kart_baglantilari(host)
        kop_bas = len(kop.akis.olaylar)
        time.sleep(3.0)
        kop_akiyor = len(kop.akis.veriler("D ", kop_bas))
        ok("kart 4 yuva: kopru 1 yuva (butun sekmeleri tasiyor) + dogrudan istemciler veri aliyor; yuvalar "
           "dolunca sonraki istemci `event: dolu` (baska sureclerin karta acik baglantilari sayilir)",
           len(dolu) == 1 and len(alan) >= 2 and len(alan) + 1 + sum(diger.values()) == 4 and kop_akiyor >= 5,
           f"dogrudan veri alan {len(alan)}, dolu {len(dolu)}, kopru 1 yuva (3 s'de {kop_akiyor} D, kopru "
           f"abonesi {abone}), karta acik baska surec baglantisi {diger}")
        # kapanan dogrudan istemcinin yuvasi ne kadar surede bosaliyor (4B acik maddesi)
        bosalma = None
        if alan:
            alan[0].kapat()
            t0 = time.monotonic()
            while time.monotonic() - t0 < 30:
                s = Sse(kart_ip, 80, ad="yeniden")
                s.start()
                ad = s.bekle(lambda a, v: a in ("kimlik", "dolu"), 8)
                if ad is not None and s.olay("dolu") is None:
                    bosalma = round(time.monotonic() - t0, 2)
                    dogrudan.append(s)
                    break
                s.kapat()
                time.sleep(0.25)
        ok("kapanan dogrudan istemcinin kart yuvasi bosaliyor (yeni istemci kabul)", bosalma is not None,
           f"{bosalma} s")
        for s in dogrudan:
            s.kapat()
        dogrudan.clear()
        # tam esitleme bitsin, bildirim bilgisi karttan alinsin
        es = kop.esitleme_bekle(t_ac - 1, 180)
        baglanti_n = len(kop.akis.veriler("* kopru: WiFi baglandi"))
        son = time.monotonic() + 60
        bd = {}
        while time.monotonic() < son:
            bd = kop.json("/bildirim/durum")
            if bd.get("bilgi") == "karttan":
                break
            time.sleep(1.0)
        dur.set()
        vt.join(20)
        p0_ist = [x for x in vek.istekler() if x["yol"] == "/komut" and x["yontem"] == "POST"]
        ist = vek.istekler()
        veri_t = [x["t_istek"] for x in ist if x["yol"].startswith("/kayit/veri")]
        p0_sure = [r for _, r in p0]
        p0_esitlemede = sum(1 for t, _ in p0 if veri_t and min(veri_t) <= t <= max(veri_t))
        ok("p0 (sekmeden, esitleme + vekil + izleyiciler surerken) 5/5 kartta 204, <= 1 s",
           len(p0_sure) == 5 and all(isinstance(r, list) and r[0] == 204 and r[1] <= 1000 for r in p0_sure),
           f"(HTTP, ms) {p0_sure}; tam esitleme SURERKEN gonderilen {p0_esitlemede}/5; "
           f"esitleme o an {es_once.get('sonuc')}->{es_p0.get('sonuc')}")
        ok("tam esitleme (bos dizin, kayitci uzerinden) tamam; vekil istekleri yanitlandi",
           bool(es) and all(k and all(c in (200, 404) for c in k) for k in vekil_kod.values())
           and set(vekil_kod) == {"/pil", "/kal/liste", "/kunye.json"},
           f"esitleme {es and (es['son_sira'], es['bayt'], round(es['son_basari'] - es['son_deneme'], 1))}; "
           f"vekil {{{', '.join(f'{y}: {len(k)} istek kodlar {sorted(set(k))}' for y, k in vekil_kod.items())}}}")
        ok("bildirim bilgisi (/bildirim/bilgi) KAYITCI uzerinden karttan alindi", bd.get("bilgi") == "karttan",
           f"{ {a: bd.get(a) for a in ('bilgi', 'abone', 'etkin')} }")
    finally:
        dur.set()
        for s in dogrudan:
            s.kapat()
        for t in tarayicilar:
            t.kapat()
        kop.kapat()
        vek.durdur()
    import pc
    profiller = [t.profil for t in tarayicilar]
    time.sleep(5.0)                                  # Edge kendini yeniden baslatabiliyor: biraz bekle
    sizan = _edge_sizinti(profiller) if profiller else 0
    ok("kopru kapandi; bu betigin basliksiz Edge'lerinden sizinti yok", not pc.zaten_calisiyor() and sizan == 0,
       f"{len(profiller)} profil, kalan surec {sizan}")

    # ── kayit tarama: SIRLAR YALNIZ BELLEKTE, ASLA BASILMAZ ──
    ist = vek.istekler()
    akislar = list(vek.akislar().values())
    sayac: dict[str, int] = {}
    for x in ist:
        sayac[x["yol"].split("?")[0]] = sayac.get(x["yol"].split("?")[0], 0) + 1
    toplam = sum(len(v) for v in akislar)
    cihaz, _ = _kart_cihazi(host)
    sirlar: dict = {"cihaz anahtari K": cihaz.K}
    okb = gecici / "pc" / "bildirim" / f"{cihaz.kimlik}.okb"
    b = bildirim.bilgi_coz(cihaz.K, cihaz.kimlik, cihaz.n, okb.read_bytes()) if okb.exists() else None
    if b:
        araci_host = bildirim.uri_coz(b["uri"])[0]
        sirlar.update({"araci adresi (uri)": b["uri"], "araci sunucu adi": araci_host,
                       "araci kullanici": b["kullanici"], "araci parolasi": b["parola"],
                       "konu oneki": b["onek"], "yuk anahtari": b["anahtar"]})
    parola = os.environ.pop("OLCUM_PAROLA", None)
    if parola:
        sirlar["web parolasi"] = parola
    sonuc = kayitta_ara(akislar, sirlar)
    gunluk_sonuc = kayitta_ara([gunluk.read_bytes()] if gunluk.exists() else [], sirlar)
    yetki = yetki_basligi(akislar)
    kimlik_gorunur = kayitta_ara(akislar, {"kimlik": cihaz.kimlik})["kimlik"]["ham"]
    bilgi_yanit = [v for (no, yon), v in vek.akislar().items() if yon == "k" and any(
        x["no"] == no and x["yol"].startswith("/bildirim/bilgi") for x in ist)]
    zarf = any(b"OKB1" in v for v in bilgi_yanit)
    del sirlar, b, parola
    vt_ = [x["t_istek"] for x in ist if x["yol"].startswith("/kayit/veri") and x["t_istek"]]
    print(f"    kayit: {len(ist)} HTTP istegi, {toplam} B; yollar {dict(sorted(sayac.items()))}; "
          f"/kayit/veri ilk->son {round(max(vt_) - min(vt_), 1) if vt_ else None} s; kopru WiFi baglanti "
          f"satiri {baglanti_n}")
    ok("kayit gercek (pozitif denetim): kart kimligi kayitta gorunuyor, /bildirim/bilgi yaniti OKB1 zarfi",
       kimlik_gorunur > 0 and zarf and sayac.get("/bildirim/bilgi", 0) >= 1 and sayac.get("/kayit/veri", 0) > 0
       and sayac.get("/akis", 0) >= 1 and sayac.get("/komut", 0) >= 7, f"kimlik {kimlik_gorunur} kez, zarf {zarf}")
    ok("Ö5: kopru<->kart trafiginde K, MQTT araci adresi/kullanici/parola/onek/yuk anahtari YOK",
       all(v["ham"] == 0 for v in sonuc.values()) and len(sonuc) >= 7,
       "; ".join(f"{e}: {v['ham']}" for e, v in sonuc.items())
       + ("" if "web parolasi" in sonuc else "; web parolasi ARANMADI (OLCUM_PAROLA verilmedi)"))
    ok("Ö5: `Authorization:` basligi YOK", yetki == 0, f"{yetki}")
    ok("kopru konsol gunlugunde de sir yok", all(v["ham"] == 0 for v in gunluk_sonuc.values()),
       "; ".join(f"{e}: {v['ham']}" for e, v in gunluk_sonuc.items()))
    shutil.rmtree(gecici, ignore_errors=True)
    ok("kayit dosyasi ve gecici dizin silindi", not kayit_dosyasi.exists() and not gecici.exists())
    if p0_ist:
        gec = [round((x["t_yanit"] - x["t_istek"]) * 1000) for x in p0_ist
               if x["t_yanit"] and x["t_istek"] and x["durum"] == 204]
        print(f"    p0 kayitcida (kopru->kart->kopru): {gec} ms")
    _ = IM


def main() -> int:
    a = sys.argv[1:]

    def sec(ad, v=None):
        return a[a.index(ad) + 1] if ad in a else v

    host = sec("--http", "olcum.local")
    if "--o3" in a:
        o3(host, float(sec("--bosluk", "200")))
    if "--o5" in a:
        o5(host, int(sec("--sekme", "3")), int(sec("--edge", "2")))
    if not ({"--o3", "--o5"} & set(a)):
        print(__doc__)
        return 2
    print(f"\n{gecti}/{gecti + kaldi} tezgah denetimi gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
