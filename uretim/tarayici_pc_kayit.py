# -*- coding: utf-8 -*-
"""T4D — PANEL PC KOPRUSUNDE: PC arsivi (Kayitlar), kart vekili (Ayarlar, Pil), eski skop arsivi.

    python tarayici_pc_kayit.py                    # 0 = yesil, 1 = kirmizi
    python tarayici_pc_kayit.py --goruntu DIZIN    # ekran goruntuleri

🔴 NEDEN BU BETIK VAR: B22a koprunun uclarini, B7 panelin mantigini AYRI AYRI sinar. Panelin
   PC'deki asil vaadi (tasarim PC10/PC11/PC12) ancak GERCEK kopru (kopru.sunucu_kur, yalniz
   127.0.0.1) + GERCEK arka plan esitlemesi (arka_esitle.ArkaEsitleme -> kayit_esitle.Esitleyici)
   + GERCEK panel + GERCEK Edge (olcum.localhost kokeni) bir aradayken olculur:
     * Kayitlar listesi koprunun DISK ARSIVIDIR ("bu PC'de"), tarayicinin IndexedDB'si DEGIL;
       kayit acilir, tuval cizilir, CSV indirmesi bagimsiz Python hesabiyla bayt bayt ayni,
       Karsilastirma iki PC kaydini cizer; panel /kayit/* ya da /eslestir/* ISTEMEZ.
     * Ayarlar > Kalibrasyon gecmisi kartin /kal/liste'sini koprunun IMZALI vekilinden alir;
       kart erisilemezse PC arsivinin kopyasina duser (sebebiyle). Gelismis kartin kunyesini
       vekilden okur. Pil durumu /pil vekilinden.
     * Osiloskop ekraninda B35 satir arsivi "Eski arsiv" basligi altinda.
     * Konsol hatasi yok, 390 px telefonda yatay tasma yok, Ingilizce metinler.

Kart: B72'nin sahte karti (test_kayit_esp._SahteKart — imza dogrulayicisi BAGIMSIZ); oturumlar
tarayici_kayitlar.akis_kur'dan (kayit_bicim paketleyicileri: adli/etiketli olcum, pil, ayrintili,
osiloskop, saatsiz). Kopru karta eslesir (imza.esles), canli akis USB kolundan (KayitKart).
Arsiv gecici OLCUM_PC_DIZIN'de (gercek_dizin_koru: kullanicinin %LOCALAPPDATA%'sina yazilmaz).
"""
from __future__ import annotations

import json
import os
import shutil
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
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import gercek_dizin_koru                                   # noqa: E402
_KORUMA = gercek_dizin_koru.koru()   # LOCALAPPDATA gecici dizine — gercek PC dizinine asla yazilmaz
_ORTAM = {a: os.environ[a] for a in ("OLCUM_PC_DIZIN", "OLCUM_CIHAZ_DIZIN")}

import tarayici_kayitlar as TK                             # noqa: E402  (oturumlar + Python basvurusu)
import test_kayit_esp as T                                 # noqa: E402  (B72 sahte karti)
os.environ.update(_ORTAM)            # ice aktarilan testler ortami yeniden yonlendirdi — bizimki kalsin
import arka_esitle as AE                                   # noqa: E402
import imza as IM                                          # noqa: E402
import kart_baglanti                                       # noqa: E402
import kart_wifi as KW                                     # noqa: E402
import kayit_bicim as KB                                   # noqa: E402
import kopru as kopru_mod                                  # noqa: E402
import pc_ayar                                             # noqa: E402
from tarayici_tema import KayitliTarayici, bos_port, css_takimlari, rgb   # noqa: E402

UYG = "document.querySelector('#uyg')._vnode.component.proxy"
gecti = kaldi = 0
KUNYE = b'{"surum":"0123456789ab","dosya":31,"icerik_bayt":411511}'
PIL = (b"durum=BEKLEMEDE\nhata=-\nmah=0\nwh=0\ncoulomb=0\nocv=0\nvson=0\nkesme=3.0\ndcir_ani=0\n"
       b"dcir_otr=0\ndcir_n=0\nsira=0\nilk_sira=0\nkalan=0\n--\n")
SATIRLAR_JS = TK.SATIRLAR_JS


def ok(ad: str, kosul: bool, ek: str = "") -> bool:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))
    return kosul


class UsbKayit(kart_baglanti.KayitKart):
    """SecmeliKart'in USB kolu: dogrulanmis kart gibi (`bagli`) — canli akis buradan, kayit
    verisi ve kart vekili WiFi kolundan (PC6)."""
    bagli = True
    bildir = None
    durum_satiri = None
    baglanti_no = 1


def main() -> int:
    arg = sys.argv[1:]
    goruntu = Path(arg[arg.index("--goruntu") + 1]) if "--goruntu" in arg else None
    if goruntu:
        goruntu.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("  T4D  PANEL PC KOPRUSUNDE — PC arsivi, kart vekili, eski skop arsivi (GERCEK kopru + Edge)")
    print("=" * 78)
    takim = css_takimlari()
    akis, no = TK.akis_kur()
    kart = T._SahteKart(list(akis.kayitlar))
    kart.kal_liste = {"surum": 1, "adet": 2, "taslak": 0, "etkin": 2, "azami": 40,
                      "kayitlar": [TK.kal_json(1), TK.kal_json(2)]}
    kart.ek_get = {"/kunye.json": (200, "application/json", KUNYE),
                   "/pil": (200, "text/plain; charset=utf-8", PIL)}
    kart_sun, kart_taban = T._sunucu(kart)
    gec = Path(tempfile.mkdtemp(prefix="olcum-t4d-"))
    indirme = gec / "indir"
    indirme.mkdir()
    cdiz = Path(os.environ["OLCUM_CIHAZ_DIZIN"])
    IM.esles(kart_taban, "kopru-t4d", kart.parola, dizin=cdiz)
    wifi = KW.WifiKart(kart_taban, dizin=cdiz)
    satirlar = [f"D {12 + i * 0.01:.4f} 0.100000 1.20000 0.0000 0.0000000 {1000 + i * 100} 172 0 0"
                for i in range(600)]
    usb = UsbKayit(satirlar, yanitlar={"?": ["A menzil=NORMAL oto=1"]}, gecikme=0.05)
    usb.ac()
    sec = KW.SecmeliKart(usb, wifi)
    kop = kopru_mod.Kopru(sec, pc_ayar.satir_dizini())
    # ── gercek arka plan esitlemesi: kartin kayitlari WiFi'den (imzali) PC arsivine ──────────
    es = AE.ArkaEsitleme(wifi, kop.yayinla, pc_ayar.arsiv_dizini(), onay=False, parca_arasi=0.0)
    kop.esitleme = es
    r = es.tur()
    akis_dizini = pc_ayar.arsiv_dizini() / kart.gkimlik / f"akis-{kart.kimlik}"
    kart_bayt = b"".join(akis.kayitlar)
    ok("Arsiv GERCEK esitlemeyle kuruldu (kopru karta eslesmis cihaz olarak, imzali): kayitlar.kyt kartin "
       "baytlariyla AYNI, kalibrasyon.json var, onay gitmedi (onaysiz)",
       r.get("sonuc") == "tamam" and (akis_dizini / "kayitlar.kyt").read_bytes() == kart_bayt
       and (akis_dizini / "kalibrasyon.json").is_file() and not any(c.startswith("Go") for c in kart.komutlar),
       f"{r.get('sonuc')} {r.get('mesaj', '')} yeni={r.get('yeni_kayit')}")
    oturumlar = KB.oturumlari_kur(KB.akis_coz(kart_bayt))

    sunucu = kopru_mod.sunucu_kur(kop, port=0)               # GERCEK baglama: yalniz 127.0.0.1
    istenen: list[str] = []
    taban_sinif = sunucu.RequestHandlerClass

    class Kayitli(taban_sinif):
        def do_GET(self):
            istenen.append(self.path.split("?")[0])
            return super().do_GET()

        def do_POST(self):
            istenen.append("POST " + self.path.split("?")[0])
            return super().do_POST()

    sunucu.RequestHandlerClass = Kayitli
    port = sunucu.server_address[1]
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    threading.Thread(target=kop.dongu, daemon=True).start()
    adres = f"http://{pc_ayar.AD}:{port}"
    print(f"     kopru: {sunucu.server_address} · panel: {adres} · sahte kart: {kart_taban}\n")
    resimler: list[Path] = []
    beklenen_hata: list[list] = []          # [yol, bas, son]: bu evrede beklenen ag hatalari (502)

    try:
        with KayitliTarayici(auth_iptal=False, port=bos_port()) as t:
            def resim(ad: str) -> None:
                if goruntu:
                    y = goruntu / f"{ad}.png"
                    t.goruntu(str(y))
                    resimler.append(y)
            t.cagir("Log.enable")
            t.tema("dark")
            try:
                t.cagir("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(indirme),
                                                        "eventsEnabled": False})
            except RuntimeError:
                t.cagir("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(indirme)})

            # ── 1. Kayitlar = PC arsivi ─────────────────────────────────
            t.git(adres + "/#/kayitlar")
            n_ot = len(oturumlar)
            liste = TK.bekle_js(t, f"document.querySelectorAll('.kl-satir').length === {n_ot}"
                                   f" && !!document.querySelector('[data-kl-pc-durum]') && {SATIRLAR_JS}", 30.0) or []
            ok("[!] PC10: olcum.localhost kokeninde Kayitlar listesi koprunun DISK ARSIVI — butun oturumlar "
               "(Python kayit_bicim cozumuyle ayni numaralar), hepsi 'bu PC'de', akis kimligi kartinki",
               sorted(x["o"] for x in liste) == sorted(oturumlar) and all(x["n"] == "pc" for x in liste)
               and all(x["k"] == kart.kimlik for x in liste) and "bu PC'de" in (liste[0]["m"] if liste else ""),
               " ".join(f"{x['o']}:{x['n']}" for x in liste))
            durum = t.js("(document.querySelector('[data-kl-pc-durum]') || {}).textContent") or ""
            ok("[!] Kopru esitlemesinin durum satiri (/esitleme/durum): son basarili zaman, yeni kayit, kartin son "
               "sirasi, karta onay KAPALI; canli bolgede (aria-live)",
               "Köprü eşitlemesi: son başarılı" in durum and f"{r.get('yeni_kayit')} yeni kayıt" in durum
               and "karta onay kapalı" in durum
               and t.js("document.querySelector('[data-kl-pc-durum]').closest('[aria-live]') !== null") is True, durum)
            ozet = t.js("(document.querySelector('[data-kl-pc-ozet]') || {}).textContent") or ""
            ok("[!] Salt okuma: esitle dugmesi, arsiv onayi kutusu, kopya silme YOK; ozet ve kopya satiri PC arsivini "
               "anlatir (kart + akis), uyari kutusu bos",
               t.js("!document.querySelector('.kl-esitle') && !document.querySelector('.kl-arsiv')"
                    " && !document.querySelector('[data-kl-sil]') && !document.querySelector('.kl-neden')"
                    " && !!document.querySelector('[data-kl-pc-salt]')") is True
               and f"1 akış · {n_ot} oturum" in ozet
               and kart.gkimlik in (t.js("(document.querySelector('.kl-kopya') || {}).textContent") or ""), ozet)
            idb = t.js("indexedDB.databases().then(l => l.map(d => d.name))")
            ok("[!] PC10: panel kayitlari tarayiciya YAZMADI (IndexedDB 'olcum-kayit' acilmadi) ve kopruden /kayit/* "
               "ya da /eslestir/* ISTEMEDI — tek yazar Python",
               isinstance(idb, list) and "olcum-kayit" not in idb
               and not any(y.startswith(("/kayit/", "/eslestir/")) for y in istenen)
               and "/arsiv/liste" in istenen and "/arsiv/veri" in istenen, f"idb={idb} istenen={sorted(set(istenen))}")
            ozet_js = ("import('/ekran/esitleme.js').then(m => new m.EsitlemeDenetcisi({kartAdres: (y) => y})"
                       f".akisBaytlari({kart.kimlik})).then(b => {{ let h = 0; for (let i = 0; i < b.length; i++)"
                       " h = (h * 31 + b[i]) >>> 0; return [b.length, h]; })")
            pb = t.js(ozet_js)
            h = 0
            for x in kart_bayt:
                h = (h * 31 + x) & 0xFFFFFFFF
            ok("[!] PC10: panelin PC arsivinden (/arsiv/veri, depo_pc.js) okudugu baytlar kartin baytlariyla BAYT BAYT "
               "ayni (boy + ozet)", pb == [len(kart_bayt), h], f"{pb} / {[len(kart_bayt), h]}")
            resim("1-kayitlar-pc")

            # ── 2. kayit gorunumu + disa aktarma ────────────────────────
            a_no = no["A"]
            t.js(f"location.hash = '#/kayit/{a_no}'")
            TK.bekle_js(t, "!!document.querySelector('canvas.kg-grafik') && !!document.querySelector('.kg-tuval').dataset.pencere")
            koyu = takim["koyu"]
            px, son = None, time.monotonic() + 8
            while time.monotonic() < son:
                px = TK.piksel_say(t, [list(rgb(koyu["--volt"])), list(rgb(koyu["--amper"]))])
                if px and px[0] > 80 and px[1] > 80:
                    break
                t.bekle(0.1)
            nerede = t.js("[...document.querySelectorAll('.kg-kpiler .kpi-deger')].map(d => d.textContent).join('|')") or ""
            ok("[!] PC kaydi acilir: tuval GERCEKTEN cizili (--volt ve --amper), ozette 'bu PC'de (köprü arşivi)'",
               bool(px) and px[0] > 80 and px[1] > 80 and "bu PC'de (köprü arşivi)" in nerede,
               f"volt {px and px[0]} amper {px and px[1]}")
            oA = oturumlar[a_no]
            kok_ad = f"kayit-{a_no}-aku-sarj-deneme"
            (indirme / f"{kok_ad}.csv").unlink(missing_ok=True)
            t.js("document.querySelector('[data-disari=\"csv_tr\"]').click()")
            tr_b = TK.indir_bekle(indirme, f"{kok_ad}.csv")
            ok("[!] Disa aktarma: PC kaydinin CSV'si (Excel-TR) BAGIMSIZ Python hesabiyla BAYT BAYT ayni",
               tr_b is not None and tr_b == TK.nokta_csv_py(oA, "tr"), f"{len(tr_b or b'')} B")
            t.js(f"location.hash = '#/kayit/{a_no}/rapor'")
            rapor = TK.bekle_js(t, "!!document.querySelector('.kg-rapor table') && document.querySelectorAll('.kg-rapor tr').length")
            ok("Rapor sayfasi PC kaydindan kuruluyor", bool(rapor) and rapor > 3, str(rapor))
            resim("2-kayit-pc")

            # ── 3. Karsilastirma iki PC kaydi ───────────────────────────
            t.js(f"location.hash = '#/karsilastir/{no['A']}@{kart.kimlik},{no['E']}@{kart.kimlik}'")
            lj = TK.bekle_js(t, "document.querySelectorAll('[data-kr-lejant]').length === 2 && !!document.querySelector('canvas.kr-grafik')"
                                " && [...document.querySelectorAll('[data-kr-lejant]')].map(l => l.dataset.durum)", 15)
            ok("[!] Karsilastirma iki PC kaydini lejantta CIZILI gosteriyor (kayit gorunumuyle ayni veri yolu)",
               lj == ["ici", "ici"], str(lj))

            # ── 4. Ayarlar: kalibrasyon gecmisi vekilden, kart erisilemezse PC kopyasi ──
            imzali_once = sum(1 for x in kart.istekler if x.startswith("GET /kal/liste") and "x-imza" in x.lower())
            t.js("location.hash = '#/ayar/kal-gecmis'")
            kal = TK.bekle_js(t, "document.querySelectorAll('[data-ay-kal]').length === 2"
                                 " && document.querySelector('[data-ay-kal-kaynak]').textContent.trim()", 15) or ""
            imzali_sonra = sum(1 for x in kart.istekler if x.startswith("GET /kal/liste") and "x-imza" in x.lower())
            ok("[!] PC11: Ayarlar > Kalibrasyon gecmisi kartin /kal/liste'si — kopru karta IMZALI vekil etti "
               "(kaynak 'kartın kalibrasyon geçmişi')",
               "kartın kalibrasyon geçmişi" in kal and imzali_sonra > imzali_once, f"{kal} imzali {imzali_once}->{imzali_sonra}")
            evre = ["/kal/liste", len(t.olaylar), None]
            beklenen_hata.append(evre)
            kart.erisilemez = True
            t.js("document.querySelector('[data-ay-bolum=\"kal-gecmis\"] .ay-ust button').click()")
            kal2 = TK.bekle_js(t, "document.querySelector('[data-ay-kal-kaynak]').textContent.includes('arşivin kopyası')"
                                  " && document.querySelectorAll('[data-ay-kal]').length === 2"
                                  " && document.querySelector('[data-ay-kal-kaynak]').textContent.trim()", 30) or ""
            kart.erisilemez = False
            evre[2] = len(t.olaylar)
            ok("[!] PC11: vekil karta ulasamazsa sebep yazilir ('köprü karta WiFi'den ulaşamadı') ve gecmis bu PC'deki "
               "arsivin kopyasindan (kart + akis + son esitleme)",
               "köprü karta WiFi'den ulaşamadı" in kal2 and "bu PC'deki arşivin kopyası" in kal2
               and kart.gkimlik in kal2 and str(kart.kimlik) in kal2, kal2)
            t.js("location.hash = '#/ayar/depolama'")
            dep = TK.bekle_js(t, "document.querySelectorAll('[data-ay-akis]').length === 1 && !!document.querySelector('[data-ay-salt]')"
                                 " && !document.querySelector('[data-ay-sil]') && document.querySelector('[data-ay-depo-pc]').textContent", 15)
            ok("Ayarlar > Depolama PC arsivini SALT OKUMA gosterir (silme dugmesi yok, aciklama); kartin dizini "
               "(/kayit/liste) SORULMAZ",
               bool(dep) and "panel yalnız okur" in dep and not any(y.startswith("/kayit/") for y in istenen),
               str(dep)[:90])
            t.js("location.hash = '#/ayar/gelismis'")
            panel = TK.bekle_js(t, "(document.querySelector('[data-ay-panel]') || {}).textContent.includes('0123456789ab')"
                                   " && document.querySelector('[data-ay-panel]').textContent", 15) or ""
            ok("[!] PC11: Gelismis kartin arayuz kunyesini (/kunye.json) kopru vekilinden okuyor",
               "0123456789ab" in panel and any(x.startswith("GET /kunye.json") and "x-imza" in x.lower() for x in kart.istekler),
               panel)

            # ── 5. Pil durumu /pil vekilinden ───────────────────────────
            pil = TK.bekle_js(t, f"{UYG}.kopruVekil === true && {UYG}.pilKaynak === 'http' && {UYG}.pilDurum", 10)
            ok("[!] PC11: kopruda /durum `vekil` -> pil durumu 'http' (kopru /pil'i karta IMZALI vekil etti)",
               pil == "BEKLEMEDE" and any(x.startswith("GET /pil?sira=") and "x-imza" in x.lower() for x in kart.istekler),
               f"{pil} {t.js(UYG + '.pilKaynak')}")

            # ── 6. Osiloskop: eski arsiv ────────────────────────────────
            t.js("location.hash = '#/skop'")
            eski = TK.bekle_js(t, "(() => { const h = document.querySelector('[data-skop-eski-arsiv]');"
                                  " return h && h.getBoundingClientRect().height > 0 && h.textContent; })()", 15) or ""
            ok("[!] PC12: Osiloskop ekraninda B35 satir arsivi 'Eski arşiv' basligi altinda (salt okuma aciklamasi)",
               eski.startswith("Eski arşiv") and "dönüştürülmez" in (t.js(
                   "document.querySelector('[data-skop-eski-arsiv]').nextElementSibling.textContent") or ""), eski)

            # ── 7. telefon genisligi + Ingilizce ────────────────────────
            t.ekran(390, 844)
            t.bekle(0.6)
            t.js("location.hash = '#/kayitlar'")
            TK.bekle_js(t, "document.querySelectorAll('.kl-satir').length > 0")
            t.bekle(0.3)
            l_tasma = TK.tasma(t)
            t.js(f"location.hash = '#/kayit/{a_no}'")
            TK.bekle_js(t, "!!document.querySelector('canvas.kg-grafik')")
            t.bekle(0.4)
            k_tasma = TK.tasma(t)
            resim("3-telefon-kayit-pc")
            ok("[!] 390 px telefonda PC Kayitlar listesi ve kayit gorunumu YATAY TASMIYOR",
               l_tasma <= 0 and k_tasma <= 0, f"liste {l_tasma} px, kayit {k_tasma} px")
            t.cagir("Emulation.clearDeviceMetricsOverride")
            t.js("location.hash = '#/kayitlar'")
            t.js(f"{UYG}.dilSecildi('en')")                 # 3H: ANINDA (yeniden yukleme yok)
            en = TK.bekle_js(t, "document.querySelectorAll('.kl-satir').length > 0 && !!document.querySelector('[data-kl-pc-durum]')"
                                " && ({d: document.querySelector('[data-kl-pc-durum]').textContent,"
                                " r: document.querySelector('.kl-satir .kl-rozet').textContent,"
                                " s: document.querySelector('[data-kl-pc-salt]').textContent})", 20) or {}
            ok("Ingilizce: 'on this PC (bridge archive)', 'Bridge sync: last success', salt okuma aciklamasi",
               en.get("r") == "on this PC (bridge archive)" and en.get("d", "").startswith("Bridge sync: last success")
               and en.get("s", "").startswith("Read-only"), str(en)[:160])
            t.js(f"{UYG}.dilSecildi('tr')")

            # ── 8. konsol ───────────────────────────────────────────────
            hatalar = []
            for i, o in enumerate(t.olaylar):
                if o["tur"] == "hata" or o.get("seviye") == "error":
                    hatalar.append(o["metin"])
                elif o["tur"] == "log":
                    yol = urllib.parse.urlparse(o.get("url", "")).path
                    if yol in ("/favicon.ico",):
                        continue
                    if any(yol == y and bas <= i < (son_ if son_ is not None else 10 ** 9) for y, bas, son_ in beklenen_hata):
                        continue
                    hatalar.append(o["metin"])
            ok("[!] Butun gezinti boyunca konsol / yukleme hatasi YOK (kartin erisilemedigi 502 evresi haric)",
               not hatalar, " | ".join(hatalar[:3]) or "temiz")
    except TK.Kopuk as h:
        ok("[!] Sayfa beklenen akista kaldi (ust uste 3 bekleme zaman asimi yok)", False, f"son beklenen: {h}")
    finally:
        kop.calisiyor = False
        sunucu.shutdown()
        sunucu.server_close()
        kop.durdur()
        kart_sun.shutdown()
        kart_sun.server_close()
        shutil.rmtree(gec, ignore_errors=True)

    gercek_dizin_koru.denetle(_KORUMA, ok)
    for y in resimler:
        print(f"     goruntu: {y}")
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
