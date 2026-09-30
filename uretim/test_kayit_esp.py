# -*- coding: utf-8 -*-
"""B72 — KAYIT MOTORUNUN KARTA BAGLANMASI: bolum tablosu · firmware kaynagi · esitleme.

    python test_kayit_esp.py

Gercek karti DEGIL; tabloyu, firmware KAYNAGINI (yorumlar cikarilarak) ve
PC esitleme istemcisini (sahte kart sunucusuna karsi) sinar. Kartta
olculecekler `tezgah_kayit.py`'de ve tezgah kalemi olarak basiliyor.
Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md
"""
from __future__ import annotations

import http.server
import os
import re
import struct
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tezgah import tezgah                          # noqa: E402
import kayit_bicim as KB                             # noqa: E402
import kayit_esitle as KE                            # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


def kod(metin: str) -> str:
    """C/C++ yorumlarini cikar — iddialar KODA baksin, prozaya degil."""
    return re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", metin, flags=re.S))


def govde(kaynak: str, imza: str) -> str:
    """`imza` ile baslayan fonksiyonun { ... } govdesi (yorumsuz kaynakta)."""
    i = kaynak.find(imza)
    if i < 0:
        return ""
    j = kaynak.find("{", i)
    derinlik = 0
    for k in range(j, len(kaynak)):
        if kaynak[k] == "{":
            derinlik += 1
        elif kaynak[k] == "}":
            derinlik -= 1
            if derinlik == 0:
                return kaynak[j:k + 1]
    return ""


def bolum_tablosu(yol: Path) -> list[dict]:
    """ESP-IDF bolum CSV'si -> [{ad, tur, alt, ofset, boyut}]."""
    satirlar = []
    for s in yol.read_text(encoding="utf-8").splitlines():
        s = s.split("#", 1)[0].strip()
        if not s:
            continue
        p = [x.strip() for x in s.split(",")]
        satirlar.append({"ad": p[0], "tur": p[1], "alt": p[2],
                         "ofset": int(p[3], 0), "boyut": int(p[4], 0)})
    return satirlar


def huge_app_csv() -> Path | None:
    taban = Path(os.environ.get("LOCALAPPDATA", "")) / "Arduino15" / "packages" / "esp32"
    return next(iter(sorted((taban / "hardware" / "esp32").glob(
        "*/tools/partitions/huge_app.csv"), reverse=True)), None)


# ── B72.P · bolum tablosu ─────────────────────────────────────────────
def bolum_tablo() -> None:
    print("\n── B72.P  bolum tablosu (partitions.csv)")
    yol = KOD / "partitions.csv"
    ok("B72.P0 cizim klasorunde partitions.csv var (cekirdegin semasini gecersiz kilar)",
       yol.exists())
    if not yol.exists():
        return
    t = {b["ad"]: b for b in bolum_tablosu(yol)}
    eski_yol = huge_app_csv()
    eski = {b["ad"]: b for b in bolum_tablosu(eski_yol)} if eski_yol else {}
    ayni = all(t.get(a) == eski.get(a) for a in ("nvs", "otadata", "app0"))
    ok("B72.P1 nvs / otadata / app0 huge_app ile BIREBIR (WiFi parolalari ve "
       "kalibrasyon NVS'te yerinde kalir)", bool(eski) and ayni,
       f"nvs={t.get('nvs')}")
    sp, esp = t.get("spiffs"), eski.get("spiffs")
    ok("B72.P2 panel bolumu ayni ofsette ve kuculmedi",
       bool(sp and esp) and sp["ofset"] == esp["ofset"] and sp["boyut"] >= esp["boyut"],
       f"{sp}")
    k = t.get("kayit")
    ok("B72.P3 kayit bolumu: data, alt tur 0x40, 4096'nin kati, >= 10 MB",
       bool(k) and k["tur"] == "data" and int(k["alt"], 0) == 0x40
       and k["boyut"] % 4096 == 0 and k["boyut"] >= 10 * 1024 * 1024,
       f"{k} = {k['boyut'] // 4096 if k else 0} sektor")
    sirali = sorted(t.values(), key=lambda b: b["ofset"])
    cakisma = any(a["ofset"] + a["boyut"] > b["ofset"] for a, b in zip(sirali, sirali[1:]))
    son = sirali[-1]
    ok("B72.P4 bolumler cakismiyor, 16 MB'i asmiyor, coredump en sonda",
       not cakisma and son["ofset"] + son["boyut"] <= 16 * 1024 * 1024
       and son["ad"] == "coredump", f"son={son}")
    au = (BURASI / "arayuz-uret.py").read_text(encoding="utf-8")
    ok("B72.P5 arayuz-uret.py panel ofsetini partitions.csv'den okuyor (tek kaynak)",
       "olcum-karti-a3\" / \"partitions.csv\"" in au and "huge_app.csv\"), reverse" not in au)


# ── B72.F · firmware kaynagi ──────────────────────────────────────────
def _oku(ad: str) -> str:
    y = KOD / ad
    return y.read_text(encoding="utf-8", errors="replace") if y.exists() else ""


def bolum_kaynak() -> None:
    print("\n── B72.F  firmware kaynagi (yorumlar cikarilarak)")
    esp_h, ino = _oku("kayit_esp.h"), _oku("olcum-karti-a3.ino")
    esp_k, ino_k = kod(esp_h), kod(ino)
    ok("B72.F1 kayit_esp.h Serial KULLANMIYOR (cekirdek 0'dan basmak aynayi "
       "yarisa sokar; baslik makrodan ONCE dahil)",
       bool(esp_k) and "Serial" not in esp_k)
    i_dahil = ino_k.find('#include "kayit_esp.h"')
    i_makro = ino_k.find("#define Serial CIKIS")
    # "KAPALI" .ino'da zaten 16 kez geciyordu: afisin KENDI dalina bak (son inceleme O5)
    ok("B72.F2 kayit_esp.h `#define Serial`'dan ONCE dahil; kayit bolumu yoksa "
       "afis KAPALI der",
       0 <= i_dahil < i_makro and re.search(
           r'if \(kayit_kur\(\)\) \{.*?\} else \{\s*Serial\.println\(F\("KAPALI',
           ino_k, re.S) is not None)
    ok("B72.F3 kayit gorevi CEKIRDEK 0'da (olcum cekirdegi flas beklemesin)",
       re.search(r"xTaskCreatePinnedToCore\(\s*kayit_gorevi[^;]*,\s*0\s*\)", esp_k)
       is not None)
    g = govde(esp_k, "static void kayit_gorevi(")
    ok("B72.F4 gorev butun ky_/kg_ islerini kilit ALTINDA yapiyor",
       "xSemaphoreTake(kayit_kilit" in g and "xSemaphoreGive(kayit_kilit" in g
       and 0 <= g.find("xSemaphoreTake(kayit_kilit") < g.find("ky_nokta("))
    # Durum makinesi kayit_yonet.h'de ve B71.V'de CALISTIRILARAK sinaniyor;
    # burada yalniz yapistirici: acilis + NVS'in Preferences'a baglanmasi.
    ny = govde(esp_k, "static int kayit_nvs_yaz(")
    ok("B72.F5 gorev acilista kyn_ac'i (esp_random ile) cagiriyor; NVS yazma hatasi "
       "YUTULMUYOR (bicimleme iptal edebilsin)",
       "kyn_ac(&kayit_m" in g and "esp_random()" in g
       and "putUInt(ad, deger) == sizeof(uint32_t)" in ny and "return -1" in ny)
    i_parca = esp_k.find("#define KG__PARCA")
    i_motor = esp_k.find('#include "kayit_yonet.h"')
    ok("B72.F6 ESP32 okuma parcasi (256) motordan ONCE tanimli",
       0 <= i_parca < i_motor and "256u" in esp_k[i_parca:i_parca + 40])
    oa = govde(ino_k, "Okuma3 olcum_al(")
    lp = govde(ino_k, "void loop(")
    ok("B72.F7 olcum_al HAM kodu, hata bitlerini ve menzili kayit_ham'a veriyor",
       all(x in oa for x in ("kayit_ham.ham_v = ham_v", "kayit_ham.ham_i = ham_i",
                             "kayit_ham.hata = ads_hata", "kayit_ham.menzil")))
    skop = lp[lp.find("if (skop_is != SKOP_IS_YOK)"):]
    ok("B72.F8 loop noktaciyi besliyor; skop duraklamasinda kayit_duraklama; "
       "G satiri yalniz loop'ta (cekirdek 1)",
       "kayit_ornek(o.watt" in lp and "kayit_duraklama(" in skop[:skop.find("return;")]
       and "kayit_durum_bas(false)" in lp and '"G %u' in ino_k)
    kk = govde(ino_k, "static void kayit_komut(")
    ok("B72.F9 pil testi surerken GF! REDDEDILIR (bicimleme istegi kuyruga girmez)",
       0 <= kk.find("pil_testi_suruyor()") < kk.find("m.tur = KM_BICIMLE"))
    ok("B72.F10 `G` komutu tanimli ve yardimda; hiz listesi dar",
       "case 'G': kayit_komut(s)" in ino_k and "Gb<ms>" in ino
       and "h == 60000" in ino_k)
    vs = govde(ino_k, "void kayit_veri_sayfa(")
    ls = govde(ino_k, "void kayit_liste_sayfa(")
    ok("B72.F11 /kayit/liste ve /kayit/veri kayitli; ikisi de Host denetimli",
       'sunucu.on("/kayit/liste"' in ino_k and 'sunucu.on("/kayit/veri"' in ino_k
       and "host_gecerli()" in vs and "host_gecerli()" in ls)
    ok("B72.F12 /kayit/veri kg_oku'yu SURELI kilit altinda, tavanla (8192) cagiriyor; "
       "web uclarinda sonsuz bekleme YOK (p0 donmasin)",
       0 <= vs.find("kayit_kilit_al_web()") < vs.find("kg_oku(")
       < vs.find("xSemaphoreGive(kayit_kilit") and "KAYIT_VERI_AZAMI" in vs
       and "kayit_kilit_al_web()" in ls and "portMAX_DELAY" not in vs + ls
       and "pdMS_TO_TICKS(KAYIT_WEB_BEKLE_MS)" in esp_k)
    ok("B72.F13 onay KUYRUGA girmez (son gelen kazanir); gorev her turda kyn_adim'e verir",
       "kayit_onay_iste(v)" in kk and "KM_ONAY" not in ino_k + esp_k
       and "kyn_adim(&kayit_m, kayit_onay_istek" in g)
    ok("B72.F14 /kayit/veri akis kimligini ve X-Onay'i basliyor; /kayit/liste kimlik veriyor",
       'sendHeader("X-Kayit-Kimlik"' in vs and 'sendHeader("X-Onay"' in vs
       and '\\"kimlik\\"' in ls)
    fo = govde(esp_k, "static int kayit_f_oku(")
    nf = govde(esp_k, "static void kayit__nefes(")
    ok("B72.F16 uzun tarama cekirdek 0'i BIRAKIR (Task WDT dolu bolumde karti "
       "sonsuz yeniden baslatiyordu) ve okuma bellege esli bolumden",
       "vTaskDelay(1)" in nf and "kayit__nefes()" in fo
       and "memcpy(h, kayit_esle_ptr + a, n)" in fo
       and "esp_partition_mmap(" in esp_k)
    gd = govde(esp_k, "static void kayit__gonder(")
    ok("B72.F15 kuyruk dolarsa kayip SESSIZ degil: sonraki nokta KAYIP_ONCE, sayac artar",
       "kn_kayip(&kayit_kn)" in gd and "kayit_kuyruk_dusen = kayit_kuyruk_dusen + 1u" in gd)


# ── B72.E · esitleme istemcisi (sahte kart) ───────────────────────────
class _SahteKart:
    """Kartin /kayit/veri ucunun sahtesi — kg_oku ile ayni anlam: `sira` ve
    sonrasi, kayit bolunmeden `bayt`a kadar. Basliklar da gercek kart gibi:
    X-Kayit-Kimlik, X-Sonraki-Sira, X-Onay."""

    def __init__(self, kayitlar: list[bytes]):
        self.kayitlar = kayitlar
        self.bozuk = False
        self.sirayi_yok_say = False     # yanitta istenenden ESKI kayit (savunma)
        self.bos_don = False            # veri var ama bos govde (parca boyu vb.)
        self.kimlik = 7
        self.onay = 0
        self.onay_dusur = 0             # sonraki N onay karta ULASMAZ
        self.komutlar: list[str] = []

    def sonraki(self) -> int:
        return max((struct.unpack_from("<I", k, 4)[0] for k in self.kayitlar), default=0) + 1

    def onayla(self, sira: int) -> None:
        """Kartin onayi uygulamasi (seri ya da HTTP yolu)."""
        if self.onay_dusur:
            self.onay_dusur -= 1
            return
        if sira < self.sonraki() and sira > self.onay:
            self.onay = sira

    def veri(self, sira: int, bayt: int) -> tuple[bytes, int, int]:
        govde, ilk, son = b"", 0, 0
        if self.bos_don:
            return govde, ilk, son
        for ham in self.kayitlar:
            s = struct.unpack_from("<I", ham, 4)[0]
            if s < sira and not self.sirayi_yok_say:
                continue
            if len(govde) + len(ham) > bayt:
                break
            govde += ham
            ilk, son = ilk or s, s
        if self.bozuk and len(govde) > 20:
            govde = govde[:20] + bytes([govde[20] ^ 1]) + govde[21:]
        return govde, ilk, son


def _sunucu(kart: _SahteKart):
    class Isleyici(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/akis":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'retry: 3000\n\nevent: kimlik\n'
                                 b'data: {"jeton":"abc123","surucu":true}\n\n')
                return
            if u.path != "/kayit/veri":
                self.send_error(404)
                return
            govde, ilk, son = kart.veri(int(q.get("sira", ["1"])[0]),
                                        int(q.get("bayt", ["8192"])[0]))
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("X-Kayit-Kimlik", str(kart.kimlik))
            self.send_header("X-Ilk-Sira", str(ilk))
            self.send_header("X-Son-Sira", str(son))
            self.send_header("X-Sonraki-Sira", str(kart.sonraki()))
            self.send_header("X-Onay", str(kart.onay))
            self.end_headers()
            self.wfile.write(govde)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            govde = self.rfile.read(n).decode()
            if self.headers.get("X-Olcum") == "1" and self.headers.get("X-Jeton") == "abc123":
                kart.komutlar.append(govde)
                if govde.startswith("Go"):
                    kart.onayla(int(govde[2:]))
                self.send_response(204)
            else:
                self.send_response(403)
            self.end_headers()

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def _kayitlar(n: int, bas: int = 1) -> list[bytes]:
    return [KB.kayit_paketle(KB.T_NOKTA if i % 3 else KB.T_SAAT, i, 7,
                             bytes((i + j) & 0xFF for j in range(4 + (i % 5) * 36)))
            for i in range(bas, bas + n)]


def _hatali(islev) -> bool:
    try:
        islev()
    except ValueError:
        return True
    return False


def _es(taban: str, d, onay=None, **kw):
    return KE.Esitleyici(taban, d, onay, onay_bekle=0.01, **kw)


def bolum_esitle() -> None:
    print("\n── B72.E  esitleme istemcisi (sahte kart)")
    kay = _kayitlar(50)
    tum = b"".join(kay)
    kart = _SahteKart(kay)
    sunucu, taban = _sunucu(kart)

    def sifirla(kayitlar=None):
        kart.__init__(kay if kayitlar is None else kayitlar)
    try:
        with tempfile.TemporaryDirectory() as d:
            onaylar: list[tuple[int, int]] = []

            def onay(s):   # onay aninda dosyada kac bayt var
                onaylar.append((s, (Path(d) / KE.DOSYA).stat().st_size))
                kart.onayla(s)

            e = _es(taban, d, onay, bayt=1100)
            e.esitle(azami_tur=2)
            r = e.esitle()
            dosya = (Path(d) / KE.DOSYA).read_bytes()
            ok("B72.E1 karttaki butun kayitlar diske AYNEN (bayt bayt) geldi",
               dosya == tum and e.son_sira() == 50, f"{r}")
            ok("B72.E2 kesilen esitleme kaldigi yerden surdu, tekrar yok",
               len(KB.akis_coz(dosya)) == 50)
            yazili = [len(b"".join(k for k in kay if struct.unpack_from("<I", k, 4)[0] <= s))
                      for s, _ in onaylar]
            ok("B72.E4 onay YALNIZ diske yazildiktan sonra ve yazilanin sonuna kadar",
               bool(onaylar) and all(b == y for (_, b), y in zip(onaylar, yazili))
               and onaylar[-1][0] == 50 and kart.onay == 50, f"{onaylar[:3]}...")
            n_onay = len(onaylar)
            r2 = e.esitle()
            ok("B72.E5 yeni kayit yokken tekrar kosmak hicbir sey cekmez, onaylamaz",
               r2["yeni_kayit"] == 0 and len(onaylar) == n_onay)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            kart.bozuk = True
            onaylar2: list[int] = []
            hata = _hatali(lambda: _es(taban, d, onaylar2.append).esitle())
            ok("B72.E3 bozuk yanit REDDEDILIR: diske yazilmaz, onaylanmaz",
               hata and not onaylar2 and not (Path(d) / KE.DOSYA).exists())
        sifirla(kay[10:])                       # 1..10 temizlikte silinmis
        with tempfile.TemporaryDirectory() as d:
            r = _es(taban, d).esitle()
            ok("B72.E6 temizlikte silinmis aralik BOSLUK olarak bildirilir",
               r["bosluk"] == [(1, 11)] and r["son_sira"] == 50, f"{r['bosluk']}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d)
            e.esitle()
            kart.kayitlar = kay + _kayitlar(3, 51)
            kart.sirayi_yok_say = True          # yanitta istenenden ESKI kayit
            hata = _hatali(e.esitle)
            ok("B72.E7 yanitta istenenden eski/tekrar sira gelirse esitleme DURUR",
               hata and (Path(d) / KE.DOSYA).read_bytes() == tum and e.son_sira() == 50)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, bayt=1100)
            e.esitle(azami_tur=1)
            yarim = kay[e.son_sira()]           # sira son+1 (> 100 B)
            with open(Path(d) / KE.DOSYA, "ab") as f:
                f.write(yarim[:len(yarim) // 2])   # durum yazilmadan kesilen YARIM ekleme
            e.esitle()
            ok("B72.E9 durum yazilmadan kesilen YARIM ekleme kirpilir: dosya tam, tekrarsiz",
               (Path(d) / KE.DOSYA).read_bytes() == tum)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            def patlayan(s):
                raise OSError("ag koptu")
            try:
                _es(taban, d, patlayan).esitle()
            except OSError:
                pass
            onaylar3: list[int] = []

            def onay3(s):
                onaylar3.append(s)
                kart.onayla(s)
            r = _es(taban, d, onay3).esitle()
            ok("B72.E10 onay yollanamadiysa sonraki kosu yeniden yollar (veri tekrar "
               "cekilmez)", onaylar3 == [50] and r["yeni_kayit"] == 0 and kart.onay == 50,
               f"{onaylar3} {r}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, kart.onayla)
            e.esitle()
            kart.kimlik = 99                    # NVS kayboldu: kart YENI akis basladi
            kart.kayitlar = kay + _kayitlar(5, 51)
            n0 = kart.onay
            hata = _hatali(e.esitle)
            ok("B72.E11 kartin akis KIMLIGI degisirse esitleme DURUR: yazmaz, onaylamaz",
               hata and (Path(d) / KE.DOSYA).read_bytes() == tum and kart.onay == n0)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, kart.onayla)
            e.esitle()
            kart.kayitlar = _kayitlar(3)        # numara 1'den yeniden (kimlik AYNI)
            hata = _hatali(e.esitle)
            ok("B72.E12 kartin sirasi istemcinin gerisine duserse (bos yanit + "
               "X-Sonraki-Sira) esitleme DURUR — sessiz 'yeni 0 kayit' YOK",
               hata and e.son_sira() == 50)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            kart.bos_don = True                 # kartta kayit var ama govde bos
            r = _es(taban, d).esitle()
            # HATA degil: bicimlenmis araligi ya da harcanmis (yarim yazilmis)
            # sirayi da ayni sekilde gorur. ATLAMAZ da: veri gelince okunur.
            ok("B72.E13 kartta daha yeni kayit varken bos yanit: sessizce 'bitti' YOK — "
               "uyari + bekleyen sayisi, son_sira ilerlemez, yazilmaz",
               r.get("bekleyen") == 50 and r["son_sira"] == 0 and bool(r.get("uyari"))
               and not (Path(d) / KE.DOSYA).exists(), f"{r}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            kart.onay_dusur = 1                 # ilk onay kuyrukta dustu
            e = _es(taban, d, kart.onayla)
            r = e.esitle()
            durum = e._durum()
            ok("B72.E14 onay karta ulasmazsa X-Onay'dan anlasilir ve YENIDEN yollanir; "
               "'onaylandi' yalniz kart dogrulayinca yazilir",
               kart.onay == 50 and durum["onaylanan"] == 50 and r.get("onay_dogrulandi"),
               f"kart.onay={kart.onay} durum={durum} r={r}")
            kart.onay_dusur = 99                # kart onaylari hic almiyor
            kart.onay = 0
            e2 = _es(taban, d, kart.onayla)
            d2 = e2._durum()
            d2["onaylanan"] = 0
            e2._durum_yaz(d2)
            r2 = e2.esitle()
            ok("B72.E14b kart onayi hic almazsa 'onaylandi' YAZILMAZ, sonraki kosu yeniden dener",
               not r2.get("onay_dogrulandi") and e2._durum()["onaylanan"] == 0, f"{r2}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, kart.onayla, bayt=1100)
            e.esitle(azami_tur=1)
            d1 = e._durum()
            ek = b"".join(k for k in kay if struct.unpack_from("<I", k, 4)[0] > d1["son_sira"])[:2000]
            gecerli = KB.akis_onek(ek)[1]
            with open(Path(d) / KE.DOSYA, "ab") as f:
                f.write(ek)                     # fsync'li veri + yeniden adlandirma KAYBOLDU
            e.esitle()
            ok("B72.E15 durum.json geride kalmissa (rename kayboldu) dosyadaki GECERLI "
               "kayitlar korunur, ileri sarilir; tekrar yok, dosya tam",
               gecerli > 0 and (Path(d) / KE.DOSYA).read_bytes() == tum and e.son_sira() == 50,
               f"ileri sarilan {gecerli} B")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, bayt=1100)
            e.esitle(azami_tur=1)
            with open(Path(d) / KE.DOSYA, "ab") as f:
                f.write(kay[-1])                # GECERLI ama sirasi ATLAYAN kuyruk
            e.esitle()
            ok("B72.E17 ileri sarma yalniz kesintisiz diziyi kabul eder: atlayan kuyruk "
               "kirpilir, aradaki kayitlar yeniden cekilir (kayip yok)",
               (Path(d) / KE.DOSYA).read_bytes() == tum and e.son_sira() == 50)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            with KE.Kilit(Path(d)):
                try:
                    _es(taban, d).esitle()
                    ikinci = False
                except RuntimeError:
                    ikinci = True
            ok("B72.E16 ayni dizinde ikinci esitleme kilit yuzunden BASLAMAZ",
               ikinci and not (Path(d) / KE.DOSYA).exists())
        sifirla()
        KE.http_onay(taban)(42)
        ok("B72.E8 HTTP onayi jetonu /akis'ten alip X-Olcum + X-Jeton ile Go<sira> yollar",
           kart.komutlar == ["Go42"], str(kart.komutlar))
    finally:
        sunucu.shutdown()


BOLUMLER = [bolum_tablo, bolum_kaynak, bolum_esitle]


def main() -> int:
    for b in BOLUMLER:
        b()
    tezgah("B72 Kayit firmware + esitleme", [
        ("Flas yazma/silmenin olcume etkisi (spec §11 ilk risk)",
         "tezgah_kayit.py --durma: 50/s ve 5/s'de kuyrukta dusen nokta 0; "
         "loop_azami ve sil_azami_us raporlanir"),
        ("Kayit surerken sifirlama (RTS) -> DEVAM",
         "tezgah_kayit.py --kesinti 20: her sifirlamada durum 2'ye doner, "
         "flasta tek oturum, noktalar bosluksuz, sira tekrar yok"),
        ("Esitlenen dosya == karttaki flas bolumu (bayt bayt)",
         "tezgah_kayit.py --esit: esptool ile okunan bolumdeki her kayit "
         "esitlenen dosyadakiyle ayni"),
        ("DOLU bolumde acilis (bolumu 50/s ONAYSIZ ~1.7 sa doldur)",
         "tezgah_kayit.py --dolu: tarama < 5 s ve Task WDT sifirlamasi YOK "
         "(2026-09-30'da sonsuz yeniden baslama bulundu), 11 MB esitlenir, "
         "onay dogrulanir, halka doner, dusen 0"),
        ("DOLU bolumde GF!",
         "tezgah_kayit.py --bicim: anlik biter, temizlik surerken /kayit/liste "
         "her istekte < 1 s (p0 ayni web sunucusunda), temiz_kalan azalir"),
        ("Gercek fis cekme (USB + PIL kapali)",
         "elle 5 kez: kurtarma hatasiz, kayit DEVAM ile surer, kayip en fazla "
         "son ~5 s"),
    ])
    print(f"\nB72: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
