# -*- coding: utf-8 -*-
"""B72 — KAYIT MOTORU GERCEK KARTTA (tezgah; zincirde DEGIL).

    python tezgah_kayit.py --yedek                 tam flas yedegi (depo DISINA)
    python tezgah_kayit.py --duman                 G komutlari + 10 s kayit + esitleme
    python tezgah_kayit.py --durma                 flas yazmasinin olcume etkisi
    python tezgah_kayit.py --kesinti 20            kayit surerken 20 RTS sifirlamasi
    python tezgah_kayit.py --esit                  esitlenen dosya == flastaki bolum
    python tezgah_kayit.py --dolu                  (once `Gb20` ile ~1.6 sa ONAYSIZ doldur)
                                                   DOLU · tarama · 11 MB esitleme · halka donusu
    python tezgah_kayit.py --bicim                 (dolu bolumde) GF!: anlik mi, web doner mi
    python tezgah_kayit.py --kal                   1B kalibrasyon gecmisi (kalibrasyon komutu CALISTIRMAZ)
    python tezgah_kayit.py --pil                   1C-1 p1 reddi (ADS yok), ad/etiket/not, DEVAM regresyonu
    python tezgah_kayit.py --ayrinti               1C-2 Gb0: ornek hizi, zaman farki, hazir alan, DEVAM
    python tezgah_kayit.py --hazirsiz [--doldur]   1C-2 GF! + Gb0: kirli silme sayilir, KA_SILME bosluktan sonra
    python tezgah_kayit.py --skop                  1C-3 Gt0/Gt2000 (CAL 1 kHz), OLCUM'e ekleme, retler, acilis
    python tezgah_kayit.py --plan                  1C-4 Gp: baslar/biter (sebep 7), yeniden baslama, atlama, iptal
                                                    (--doldur: once bolumu Gb20 ile doldur, ~1.6 sa)
    secenekler: --port COM6  --http olcum.local  (ya da kartin IP'si)

🔴 --yedek NVS'i (WiFi ve web parolalarini) icerir: DEPO DISINA yazilir
   (<calisma alani>/.yedek/olcum-karti/). Geri donus:
   esptool --port COM6 -b 921600 write-flash 0x0 <yedek>.bin
Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md (Task 8).
"""
from __future__ import annotations

import datetime
import os
import random
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                   # noqa: E402
import kayit_bicim as KB                               # noqa: E402
import kayit_esitle as KE                              # noqa: E402

YEDEK = KOK.parents[1] / ".yedek" / "olcum-karti"
G_ALAN = ["durum", "oturum", "nokta", "sonraki", "onay", "doluluk", "onaysiz",
          "dusen", "yaz_azami_us", "sil_azami_us", "sil_adet", "tarama_ms", "son_hata"]
gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    gecti, kaldi = gecti + bool(kosul), kaldi + (not kosul)
    print(f"  [{'OK' if kosul else '!!'}] {ad}" + (f"   {ek}" if ek else ""))


def esptool() -> Path:
    taban = Path(os.environ["LOCALAPPDATA"]) / "Arduino15" / "packages" / "esp32" / "tools"
    return sorted(taban.glob("esptool_py/*/esptool.exe"))[-1]


def flas_oku(port: str, ofset: int, boyut: int, hedef: Path) -> int:
    """esptool read-flash; 921600 baud'da ara sira 'Corrupt data' (2026-09-30,
    gecici) -> bir kez daha, sonra 460800 ile dene."""
    rc = 1
    for baud in ("921600", "921600", "460800"):
        rc = subprocess.run([str(esptool()), "--port", port, "-b", baud, "read-flash",
                             hex(ofset), hex(boyut), str(hedef)]).returncode
        if rc == 0:
            break
        time.sleep(1.0)
    return rc


def kayit_bolumu() -> tuple[int, int]:
    for s in (KOK / "kod" / "olcum-karti-a3" / "partitions.csv").read_text().splitlines():
        p = [x.strip() for x in s.split("#", 1)[0].split(",")]
        if len(p) >= 5 and p[0] == "kayit":
            return int(p[3], 0), int(p[4], 0)
    raise SystemExit("partitions.csv'de kayit bolumu yok")


def g_coz(satir: str) -> dict | None:
    p = satir.split()
    if len(p) != 14 or p[0] != "G" or not all(x.lstrip("-").isdigit() for x in p[1:]):
        return None
    return dict(zip(G_ALAN, (int(x) for x in p[1:])))


def dinle(k, sn: float, kosul=None) -> tuple[list[str], dict | None]:
    son, satirlar, g = time.time() + sn, [], None
    while time.time() < son:
        s = k.satir_oku(0.2)
        if s is None:
            continue
        satirlar.append(s)
        gg = g_coz(s)
        if gg:
            g = gg
            if kosul and kosul(g):
                break
    return satirlar, g


def komut(k, c: str, bekle: float = 1.0, kosul=None):
    k.yaz(c + "\n")
    return dinle(k, bekle, kosul)


def durum_iste(k, bekle: float = 2.0) -> dict | None:
    """G satiri yalniz durum/oturum degisince kendiliginden basilir; onay ve
    sayaclar icin `G?` ile iste."""
    return komut(k, "G?", bekle, lambda g: True)[1]


def esitle(k, host: str, dizin: Path) -> dict:
    return KE.Esitleyici(f"http://{host}", dizin, KE.seri_onay(k)).esitle()


def yedek(port: str) -> int:
    YEDEK.mkdir(parents=True, exist_ok=True)
    hedef = YEDEK / f"tam-{datetime.datetime.now():%Y%m%d-%H%M%S}.bin"
    print(f"tam flas yedegi -> {hedef} (16 MB, ~3 dk)")
    rc = flas_oku(port, 0, 0x1000000, hedef)
    ok("tam flas yedegi alindi (16 MB)",
       rc == 0 and hedef.exists() and hedef.stat().st_size == 16 * 1024 * 1024, str(hedef))
    return 0 if kaldi == 0 else 1


def duman(k, host: str) -> None:
    print("\n── duman: G komutlari, 10 s kayit, esitleme")
    g = durum_iste(k)
    ok("G? durum satiri geliyor ve tarama bitmis (durum 1 = kayit yok)",
       bool(g) and g["durum"] == 1, f"{g}")
    komut(k, "Gb200")
    _, g = dinle(k, 14, lambda x: x["durum"] == 2 and x["nokta"] >= 40)
    ok("Gb200: kayit basladi, ~10 s'de >= 40 nokta", bool(g) and g["durum"] == 2
       and g["nokta"] >= 40, f"{g}")
    _, g = komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    ok("Gd: kayit durdu (durum 1)", bool(g) and g["durum"] == 1, f"{g}")
    with tempfile.TemporaryDirectory() as d:
        r = esitle(k, host, Path(d))
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
    ot = KB.oturumlari_kur(kay)
    son = max(ot.values(), key=lambda o: o.id) if ot else None
    ok("esitlenen son oturum: BASLA (kalibrasyon kopyasi) + >= 40 nokta + BITIR",
       bool(son) and son.basla is not None and len(son.noktalar) >= 40
       and son.bitir is not None,
       f"{r} nokta={len(son.noktalar) if son else 0} surum={son.basla.surum if son and son.basla else '-'}")
    g = durum_iste(k)
    ok("onay karta ulasti (G onay = sonraki - 1)",
       bool(g) and g["onay"] == g["sonraki"] - 1, f"{g}")


def durma(k) -> None:
    print("\n── durma: flas yazma/silmenin olcume etkisi (her kip 60 s)")
    sonuc = {}
    for ad, c in (("kayitsiz", None), ("5/s", "Gb200"), ("50/s", "Gb20")):
        komut(k, "Gd", 2)
        if c:
            komut(k, c, 3)
        g0 = durum_iste(k)
        k.yaz("K\n")                           # blokaj sayaclarini sifirla
        satirlar, _ = dinle(k, 60)
        g = durum_iste(k)
        kk = [s.split() for s in satirlar if s.startswith("K ")]
        kk = [x for x in kk if len(x) == 4 and all(y.isdigit() for y in x[1:])]
        sonuc[ad] = (kk[-1] if kk else None, g0, g)
        print(f"  {ad:9s} K(kayip_ms loop_azami_us >20ms)={kk[-1][1:] if kk else '-'}  "
              f"yaz_azami={g and g['yaz_azami_us']} us  sil_azami={g and g['sil_azami_us']} us  "
              f"sil +{g and g0 and g['sil_adet'] - g0['sil_adet']}  dusen={g and g['dusen']}")
    komut(k, "Gd", 2)
    for ad in ("5/s", "50/s"):
        _, g0, g = sonuc[ad]
        ok(f"{ad}: kuyrukta dusen nokta yok (flas beklemesi sessiz kayip yapmadi)",
           bool(g and g0) and g["dusen"] == g0["dusen"], f"{g0 and g0['dusen']} -> {g and g['dusen']}")


def devam_tutarli(kayitlar) -> bool:
    beklenen: dict = {}
    for k in kayitlar:
        if k.tur == KB.T_BASLA:
            beklenen[k.oturum] = 0
        elif k.tur == KB.T_NOKTA:
            ilk = struct.unpack_from("<I", k.yuk)[0]
            if beklenen.get(k.oturum, ilk) != ilk:
                return False
            beklenen[k.oturum] = ilk + (len(k.yuk) - 4) // KB.NOKTA_BAYT
        elif k.tur == KB.T_DEVAM:
            ns = KB.devam_coz(k.yuk)["nokta_sira"]
            if beklenen.get(k.oturum, ns) != ns:
                return False                   # DEVAM = flastaki son noktanin bitisi
            beklenen[k.oturum] = ns
    return True


def yeni_acilis(k, sn: float = 30.0) -> bool:
    """Sifirlamadan sonra YENI acilisin afisini bekle. 🔴 Ilk surumde
    afis beklenmiyordu: tamponda kalmis ESKI `G ... durum=2` satiri "kayit
    surdu" sayiliyordu ve kart daha WiFi'ye baglanirken (~5 s) yeniden
    sifirlaniyordu — 20 sifirlamanin 2'si DEVAM'a hic ulasmadi (18/20)."""
    son = time.time() + sn
    while time.time() < son:
        s = k.satir_oku(0.2)
        if s is not None and s.startswith("Kayit:"):
            return True
    return False


def kesinti(k, host: str, n: int) -> None:
    print(f"\n── kesinti: kayit surerken {n} RTS sifirlamasi")
    rng = random.Random(72)
    komut(k, "Gd", 2)
    _, g = komut(k, "Gb100", 5, lambda x: x["durum"] == 2)
    oturum = g["oturum"] if g else 0
    geri = 0
    taramalar = []
    for i in range(n):
        time.sleep(rng.uniform(2.0, 15.0))
        k.sifirla()
        acildi = yeni_acilis(k)
        _, g = dinle(k, 20, lambda x: x["durum"] == 2) if acildi else ([], None)
        ayni = bool(acildi and g and g["durum"] == 2 and g["oturum"] == oturum)
        geri += ayni
        taramalar.append(g["tarama_ms"] if g else -1)
        print(f"  sifirlama {i + 1:2d}/{n}: afis={'var' if acildi else 'YOK'} "
              f"durum={g and g['durum']} oturum={g and g['oturum']} "
              f"nokta={g and g['nokta']} tarama={g and g['tarama_ms']} ms")
    time.sleep(3)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    ok(f"{n} sifirlamanin hepsinde kayit AYNI oturumla surdu", geri == n, f"{geri}/{n}")
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
    ot = KB.oturumlari_kur(kay).get(oturum)
    siralar = [x.sira for x in kay]
    idx = [j for j, _ in ot.noktalar] if ot else []
    ok("flasta DEVAM sayisi sifirlama sayisina esit", bool(ot) and len(ot.devamlar) == n,
       f"{len(ot.devamlar) if ot else 0}")
    if ot and ot.devamlar:
        ms = sorted(d["kart_ms"] for d in ot.devamlar)
        print(f"  acilistan DEVAM'a (kayit yeniden basliyor): en az {ms[0]} ms, "
              f"ortanca {ms[len(ms) // 2]} ms, en cok {ms[-1]} ms")
    ok("oturumun nokta siralari tekrarsiz ve artan; DEVAM'lar tutarli; kayit sirasi tekrarsiz",
       bool(idx) and idx == sorted(set(idx)) and devam_tutarli(kay)
       and len(siralar) == len(set(siralar)),
       f"{len(idx)} nokta, en uzun tarama {max(taramalar)} ms")


def dolu(k, host: str) -> None:
    """Bolum 50/s ile ONAYSIZ doldurulduktan sonra (Gb20, ~1.6 sa):
    DOLU davranisi · dolu bolumde acilis taramasi · 11 MB esitleme hizi ·
    onaydan sonra halka doner ve DOLU sektor silinirken olcum dongusu
    (spec §11'in gercek en kotu hali)."""
    print("\n── dolu: bellek dolu -> tarama -> esitleme -> halka donusu")
    g = durum_iste(k)
    if g and g["durum"] != 3:
        # DOLU bayragi acilista sifirlanir (yalniz yer bulamayan yazmada kurulur):
        # yeni kayit iste, kart yer bulamayinca DOLU'ya gecmeli
        _, g = komut(k, "Gb20", 30, lambda x: x["durum"] == 3)
        g = durum_iste(k)
    ok("bellek onaysiz veriyle dolu: yeni kayit yer bulamaz, durum 3 (DOLU), oturum kapali",
       bool(g) and g["durum"] == 3 and g["oturum"] == 0, f"{g}")
    ok("DOLU'da onaysiz veri silinmedi (onaysiz >= %99)",
       bool(g) and g["onaysiz"] >= 990, f"onaysiz {g and g['onaysiz']} binde")
    k.sifirla()
    _, g = dinle(k, 30, lambda x: x["durum"] != 0) if yeni_acilis(k) else ([], None)
    # DOLU bayragi yalniz yer bulamayan YAZMADA kurulur; acilista kg_ac
    # sifirlar -> durum 1. Onaysiz veri (NVS'teki onayla) yerinde kalmali.
    ok("dolu bolumde acilis taramasi < 5 s; onaysiz veri acilistan sonra da korunuyor",
       bool(g) and g["durum"] in (1, 3) and 0 < g["tarama_ms"] < 5000
       and g["onaysiz"] >= 990, f"tarama {g and g['tarama_ms']} ms, {g}")
    with tempfile.TemporaryDirectory() as d:
        t0 = time.time()
        r = KE.Esitleyici(f"http://{host}", Path(d), KE.seri_onay(k)).esitle()
        sure = time.time() - t0
        boy = (Path(d) / KE.DOSYA).stat().st_size
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
    print(f"  esitleme: {r['yeni_kayit']} kayit, {boy / 1e6:.2f} MB, {sure:.0f} s "
          f"= {boy / 1024 / max(sure, 1e-3):.0f} KB/s, bosluk {r['bosluk']}")
    time.sleep(1)
    k.yaz(f"Go{r['son_sira']}\n")               # son onay kesin gitsin
    g = durum_iste(k)
    ok("esitleme sonrasi: onay = sonraki-1, onaysiz 0, siralar tekrarsiz",
       bool(g) and g["onay"] == g["sonraki"] - 1 and g["onaysiz"] == 0
       and len({x.sira for x in kay}) == len(kay), f"{g}")
    komut(k, "Gb20", 5, lambda x: x["durum"] == 2)
    g0 = durum_iste(k)
    k.yaz("K\n")
    satirlar, _ = dinle(k, 120)
    g = durum_iste(k)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    kk = [s.split() for s in satirlar if s.startswith("K ")]
    kk = [x for x in kk if len(x) == 4 and all(y.isdigit() for y in x[1:])]
    sil = g["sil_adet"] - g0["sil_adet"] if g and g0 else -1
    print(f"  halka donusu 120 s @ 50/s: silme +{sil}, sil_azami {g and g['sil_azami_us']} us, "
          f"K(kayip_ms loop_azami_us >20ms)={kk[-1][1:] if kk else '-'}")
    ok("halka dondu (dolu sektorler silinerek) ve kuyrukta dusen nokta yok",
       sil > 20 and bool(g and g0) and g["dusen"] == g0["dusen"],
       f"silme +{sil}, dusen {g0 and g0['dusen']} -> {g and g['dusen']}")


def bicim(k, host: str, sn: float = 90.0) -> None:
    """DOLU bolumde GF! (son inceleme O4): mantiksal bicimleme ANINDA biter,
    web (p0 dahil) donmaz, eski sektorler arka planda aralikla silinir."""
    import json
    import urllib.request
    print(f"\n── bicim: GF! sonrasi {sn:.0f} s web yaniti + dongu + temizlik")
    t0 = time.time()
    k.yaz("GF!\n")
    time.sleep(1.0)
    g = durum_iste(k)          # durum degismedigi icin G kendiliginden BASILMAZ
    anlik = time.time() - t0
    ok("GF! aninda biter: doluluk 0, onaysiz 0 (fiziksel silme beklenmez)",
       bool(g) and g["doluluk"] == 0 and g["onaysiz"] == 0 and anlik < 5,
       f"{anlik:.1f} s {g}")
    k.yaz("K\n")
    en_uzun, hata, n, kalan = 0.0, 0, 0, []
    son = time.time() + sn
    satirlar = []
    while time.time() < son:
        t = time.time()
        try:
            with urllib.request.urlopen(f"http://{host}/kayit/liste", timeout=5) as y:
                kalan.append(json.loads(y.read()).get("temiz_kalan"))
        except Exception:
            hata += 1
        en_uzun = max(en_uzun, time.time() - t)
        n += 1
        while True:
            s = k.satir_oku(0.05)
            if s is None:
                break
            satirlar.append(s)
    kk = [s.split() for s in satirlar if s.startswith("K ")]
    kk = [x for x in kk if len(x) == 4 and all(y.isdigit() for y in x[1:])]
    g = durum_iste(k)
    print(f"  {n} istek, en uzun {en_uzun * 1000:.0f} ms, hata/503 {hata}; temiz_kalan "
          f"{kalan[:1]} -> {kalan[-1:]}; K(kayip_ms loop_azami_us >20ms)="
          f"{kk[-1][1:] if kk else '-'}; sil_azami {g and g['sil_azami_us']} us")
    ok("temizlik surerken web DONMUYOR: her istek < 1 s (p0 ayni sunucuda)",
       n > 10 and en_uzun < 1.0, f"en uzun {en_uzun:.2f} s")
    ok("arka plan temizligi ilerliyor (temiz_kalan azaliyor)",
       len([x for x in kalan if x is not None]) >= 2 and kalan[-1] < kalan[0], f"{kalan[:1]}->{kalan[-1:]}")


def _kl(k) -> list[list[str]]:
    satir, _ = komut(k, "kl", 3)
    return [s.split(" ", 6) for s in satir if s.startswith("KL ") and not s.startswith("KL.")]


def kal(k, host: str) -> None:
    """1B kalibrasyon gecmisi kartta. ⚠ Kalibrasyon komutu (z g Z i s f F R)
    CALISTIRILMAZ: ADS takili degilse cop olcum gercek kalibrasyonun yerine
    yazilirdi. Not/tur duzeltmesi denenir ve ESKI haline geri yazilir."""
    import json
    import urllib.request
    print("\n── kal: kalibrasyon gecmisi (1B) — kalibrasyon komutu calistirilmaz")
    satir, _ = komut(k, "k?", 2)
    kg = [s.split() for s in satir if s.startswith("KG ")]
    kg = kg[-1] if kg else []
    ok("gecmis var (#1 = 1B oncesi Ayar3), NVS'te yer olculdu, etkin = son kayit",
       len(kg) == 8 and int(kg[1]) >= 1 and int(kg[4]) >= 6 * 40
       and kg[3] == "0" and kg[7] == kg[2], f"KG {kg[1:]}")
    son_no, taslak = int(kg[2]), kg[3]
    satir, _ = komut(k, f"kv{son_no}", 2)
    kv = next((s.split() for s in satir if s.startswith("KV ")), [])
    satir, _ = komut(k, "?", 2)
    a = next((s for s in satir if s.startswith("A menzil")), "")
    alan = dict(x.split("=", 1) for x in a.split()[1:] if "=" in x)
    esit_mi = (len(kv) == 19 and taslak == "0"
               and abs(float(kv[4]) - float(alan.get("n_kazanc", "nan"))) < 1e-5
               and int(kv[5]) == int(alan.get("n_sifir", "0"))
               and abs(float(kv[9]) - float(alan.get("y_kazanc", "nan"))) < 1e-5
               and int(kv[10]) == int(alan.get("y_sifir", "0"))
               and int(kv[12]) == int(alan.get("i_ofset", "0"))
               and abs(float(kv[14]) - float(alan.get("sont", "nan"))) < 1e-7
               and abs(float(kv[15]) - float(alan.get("i_duz", "nan"))) < 1e-5)
    ok(f"son kayit (#{son_no}) degerleri kartin guncel Ayar3'u ile ayni (taslak yok)",
       esit_mi, f"KV {kv[1:6]}… A {a[:80]}")
    once = {r[1]: r for r in _kl(k)}.get(str(son_no))
    komut(k, f"kn{son_no} tezgah denemesi ğ", 2)
    komut(k, f"kt{son_no}i", 2)
    k.sifirla()
    yeni_acilis(k)
    dinle(k, 8, lambda x: x["durum"] != 0)
    sonra = {r[1]: r for r in _kl(k)}.get(str(son_no))
    ok("not ve tur duzeltmesi yeniden acilista KALICI (Turkce karakter dahil)",
       bool(sonra) and sonra[4] == "2" and sonra[6].strip() == "tezgah denemesi ğ",
       f"{sonra}")
    if once:                                   # kullanicinin notunu/turunu GERI yaz
        komut(k, f"kn{son_no} {once[6].strip() if len(once) > 6 else ''}", 2)
        komut(k, f"kt{son_no}{'-di'[int(once[4])]}", 2)
    geri = {r[1]: r for r in _kl(k)}.get(str(son_no))
    ok("deneme notu/turu eski haline geri yazildi", geri == once, f"{geri} vs {once}")
    if taslak == "0":                         # taslak yokken `kk` HICBIR sey yazmaz
        satir, _ = komut(k, "kk-tezgah", 2)
        satir2, _ = komut(k, "k?", 2)
        kg2 = next((s.split() for s in satir2 if s.startswith("KG ")), [])
        ok("taslak yokken `kk` kayit ACMAZ, degerlerin numarasini soyler",
           any(s.startswith(f"* k: degerler zaten kayitli: #{son_no} ") for s in satir)
           and kg2[1:3] == kg[1:3], f"{[s for s in satir if 'k:' in s]} KG {kg2[1:3]}")
    komut(k, "Gd", 2)
    satir, _ = komut(k, "Gb200", 5, lambda x: x["durum"] == 2)
    ok("taslak yokken kayit baslangici kalibrasyon icin SESSIZ (otomatik kayit yok)",
       not any("otomatik kaydedildi" in s or "NUMARASIZ" in s for s in satir),
       str([s for s in satir if "k:" in s]))
    time.sleep(3)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    with tempfile.TemporaryDirectory() as d:
        r = esitle(k, host, Path(d))
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
        js = json.loads((Path(d) / KE.KAL_DOSYA).read_text(encoding="utf-8"))
    ot = KB.oturumlari_kur(kay)
    sono = max(ot.values(), key=lambda o: o.id) if ot else None
    ok("yeni oturum basligi surum 2 ve kalibrasyon NUMARASINI tasiyor",
       bool(sono) and sono.basla is not None and sono.basla.bicim_surum == 2
       and sono.basla.kal_no == son_no,
       f"surum={sono and sono.basla and sono.basla.bicim_surum} kal_no={sono and sono.basla and sono.basla.kal_no}")
    liste = {str(x["no"]): x for x in js.get("kayitlar", [])}
    kl_son = {r[1]: r for r in _kl(k)}
    ok("/kal/liste (kalibrasyon.json) == kl: ayni numaralar, notlar, turler",
       r.get("kalibrasyon") == len(kl_son) == js.get("adet")
       and all(liste[n]["not"] == (v[6].strip() if len(v) > 6 else "")
               and str(liste[n]["tur"]) == v[4] for n, v in kl_son.items()),
       f"json adet {js.get('adet')} kl {len(kl_son)}")
    ok("/kal/liste etkin kalibrasyonu soyluyor (== k?)", js.get("etkin") == son_no,
       f"etkin {js.get('etkin')}")


def pil(k, host: str) -> None:
    """1C-1 pil testi oturumu kartta. ADS takili degil: p1 REDDEDILMELI ve
    oturum ACMAMALI (test hic baslamadi). Ad/etiket/not gercek bir olcum
    oturumuna yazilir, PC esitlenen dosyadan okur; Gx notu siler. Pil surerken
    Gb/Gd reddi ve pil oturumunun kendisi ADS olmadan sinanamaz: AVR (B71.PL)
    + kaynak iddialari (B72.F27-F36); gercek pil testi tezgah kalemi."""
    print("\n── pil: pil testi oturumu (1C-1) — ADS yok, p1 reddedilmeli")
    komut(k, "Gd", 2)
    g0 = durum_iste(k)
    satir, _ = komut(k, "p1", 3)
    g1 = durum_iste(k)
    ok("p1 (ADS yok) REDDEDILDI; kayit oturumu ACILMADI, 'kaydi istendi'/KAYDEDILMIYOR "
       "basilmadi",
       any("REDDEDILDI" in s for s in satir)
       and not any("kaydi istendi" in s or "KAYDEDILMIYOR" in s for s in satir)
       and bool(g0) and bool(g1) and g1["sonraki"] == g0["sonraki"]
       and g1["durum"] == g0["durum"],
       f"{[s for s in satir if 'pil' in s]} sonraki {g0 and g0['sonraki']} -> "
       f"{g1 and g1['sonraki']}")
    _, g = komut(k, "Gb200", 5, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    time.sleep(2)
    cevap = []
    for c in (f"Ga{oid} tezgah adı ğ", f"Ge{oid} tezgah, 1C-1", f"Gn{oid} not bir",
              f"Gn{oid}@1500 not iki", "Gn0 gecersiz", f"Gx{oid} iki nokta yok"):
        s, _ = komut(k, c, 1.5)
        cevap.append((c, [x for x in s if x.startswith(("* G", "! G"))]))
    ok("Ga/Ge/Gn kuyruga girdi; Gn0 ve ':' siz Gx REDDEDILDI (kayit yazilmadi)",
       all(any(x.startswith("* G not") for x in r) for _, r in cevap[:4])
       and all(any(x.startswith("! G") for x in r) for _, r in cevap[4:]), str(cevap))
    k.sifirla()
    acildi = yeni_acilis(k)
    _, g2 = dinle(k, 20, lambda x: x["durum"] == 2) if acildi else ([], None)
    ok("kayit surerken yeniden baslatma: OLCUM oturumu yine DEVAM aldi (regresyon)",
       bool(g2) and g2["durum"] == 2 and g2["oturum"] == oid, f"{g2}")
    time.sleep(2)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
    ot = KB.oturumlari_kur(kay).get(oid)
    notlar = sorted(n["metin"] for n in ot.notlar.values()) if ot else []
    ok("esitlenen dosyada PC oturumun adini, etiketlerini ve iki notunu okuyor (Turkce "
       "dahil); not kayitlari baslikta oturum 0",
       bool(ot) and ot.ad == "tezgah adı ğ" and ot.etiketler == ["tezgah", "1C-1"]
       and notlar == ["not bir", "not iki"]
       and all(x.oturum == 0 for x in kay if x.tur == KB.T_NOT),
       f"ad={ot and ot.ad} etiket={ot and ot.etiketler} notlar={notlar}")
    if ot and ot.notlar:
        sira = min(ot.notlar)
        s, _ = komut(k, f"Gx{oid}:{sira} ", 1.5)
        time.sleep(1)
        with tempfile.TemporaryDirectory() as d:
            esitle(k, host, Path(d))
            kay2 = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
        ot2 = KB.oturumlari_kur(kay2).get(oid)
        ok("Gx<oturum>:<sira> (bos metin) notu SILER: esitlenen son halde tek not kaldi",
           bool(ot2) and len(ot2.notlar) == 1 and sira not in ot2.notlar,
           f"{[x for x in s if 'G' in x]} {ot2 and ot2.notlar}")


HAZIR_HEDEF = 480                              # kayit_yonet.h KYN_HAZIR_HEDEF


def _ga(k) -> list[int] | None:
    s, _ = komut(k, "G?", 2)
    ga = next((x.split() for x in s if x.startswith("GA ")), None)
    return [int(v) for v in ga[1:]] if ga and len(ga) == 5 and all(
        v.isdigit() for v in ga[1:]) else None


def _ayr_esitle(k, host: str, oid: int):
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))
        kay = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
    return kay, KB.oturumlari_kur(kay).get(oid)


def ayrinti(k, host: str, sn: float = 60.0) -> None:
    """1C-2 ayrintili kip (Gb0) kartta. ADS takili degil: ornek kodlari hata
    bayrakli ama ZAMAN gercek — olculen: ornek hizi, zaman farki dagilimi,
    bosluklar, hazir alan, kayit ici silme, DEVAM. Gercek 500/s ADS gelince."""
    print("\n── ayrinti: Gb0 (her ornek) — ADS yok, zaman/bosluk/hazir alan olculur")
    komut(k, "Gd", 3)
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))                   # her sey onayli: on silme yapabilsin
    ga0 = _ga(k)
    time.sleep(12)
    ga1 = _ga(k)
    ok("GA satiri geliyor; esitleme + onaydan sonra BOSTA hazir alan buyuyor (on silme)",
       bool(ga0) and bool(ga1) and (ga1[0] > ga0[0] or ga0[0] >= HAZIR_HEDEF),
       f"GA {ga0} -> {ga1}")
    son = time.time() + 300                    # 480 sektor x 500 ms = 4 dk
    while ga1 and ga1[0] < HAZIR_HEDEF and time.time() < son:
        time.sleep(15)
        ga1 = _ga(k) or ga1
    print(f"  hazir alan {ga1 and ga1[0]} sektor (hedef {HAZIR_HEDEF})")
    hazir0 = ga1[0] if ga1 else 0
    sil0 = ga1[3] if ga1 else 0
    _, g = komut(k, "Gb0", 5, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    time.sleep(sn)
    ga2 = _ga(k)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    kay, o = _ayr_esitle(k, host, oid)
    orn = KB.ayrinti_ornekler(o) if o else []
    dt = [b[1] - a[1] for a, b in zip(orn, orn[1:])]
    dts = sorted(dt)
    orta = dts[len(dts) // 2] if dts else 0
    hiz = len(orn) / sn if sn else 0
    kayitlar = sorted(o.ayrinti, key=lambda r: r["sira"]) if o else []
    silme = sum(1 for r in kayitlar if r["bayrak"] & KB.KA_SILME)
    kayip = sum(1 for r in kayitlar if r["bayrak"] & KB.KA_KAYIP_ONCE)
    bosluk = sum(1 for x in dt if x > 16380)
    # oturumun kapladigi sektor ~ kayit baytlari / sektor (baslik + ek kayitlar kucuk)
    bayt = sum(KB.BASLIK_BAYT + len(x.yuk) for x in kay if x.oturum == oid)
    sektor = bayt / 4096
    print(f"  {len(orn)} ornek / {sn:.0f} s = {hiz:.0f}/s · dt ortanca {orta} us, en buyuk "
          f"{max(dt) if dt else 0} us, > 16.38 ms bosluk {bosluk} · {len(kayitlar)} kayit · "
          f"KA_SILME {silme} · KA_KAYIP {kayip} · hazir {hazir0} -> {ga2 and ga2[0]} · "
          f"~{sektor:.0f} sektor")
    ok("Gb0 her ornegi kaydetti: sira kesintisiz, sayi ~ sure x dongu hizi; GA ornek sayisi == "
       "flastaki", bool(orn) and [s for s, *_ in orn] == list(range(len(orn)))
       and hiz > 20 and o.bitir is not None and o.bitir["nokta_adedi"] == len(orn)
       and bool(ga2) and ga2[1] <= len(orn),
       f"{len(orn)} ornek, {hiz:.0f}/s, bitir={o and o.bitir}")
    ok("KA_SILME kayit sayisi == GA'nin kayit ici silme artisi; hazir alan oturumu "
       "karsiladiysa ikisi de 0; halkadan ornek dusmedi (GA dusen 0, KA_KAYIP 0)",
       bool(ga2) and 0 <= (ga2[3] - sil0) - silme <= 1 and (sektor + 2 > hazir0 or silme == 0)
       and ga2[2] == 0 and kayip == 0,
       f"KA_SILME={silme} GA={ga2} sil0={sil0} hazir0={hazir0} ~{sektor:.0f} sektor")
    # DEVAM: ayrintili oturum surerken yeniden baslatma
    _, g = komut(k, "Gb0", 5, lambda x: x["durum"] == 2)
    oid2 = g["oturum"] if g else 0
    time.sleep(5)
    k.sifirla()
    acildi = yeni_acilis(k)
    _, g2 = dinle(k, 20, lambda x: x["durum"] == 2) if acildi else ([], None)
    time.sleep(5)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    kay2, o2 = _ayr_esitle(k, host, oid2)
    orn2 = KB.ayrinti_ornekler(o2) if o2 else []
    # son inceleme: yeniden baslamada micros SIFIRLANIR; zaman her ACILIS icinde
    # artmali ve DEVAM'dan sonra da ayrintili ornek yazilmis olmali
    artan = all(a[1] < b[1] for a, b in zip(orn2, orn2[1:]) if a[5] == b[5])
    sonra = sum(1 for x in orn2 if x[5] == 1)
    ok("ayrintili oturum surerken yeniden baslatma: AYNI oturum DEVAM ile ayrintili surer, "
       "ornek sirasi kesintisiz; DEVAM'dan sonra da ornek var, zaman her acilista artan",
       bool(g2) and g2["oturum"] == oid2 and o2 is not None and len(o2.devamlar) == 1
       and [s for s, *_ in orn2] == list(range(len(orn2))) and len(orn2) > 0
       and o2.basla is not None and o2.basla.hiz_ms == 0 and artan and sonra > 0,
       f"g2={g2 and (g2['durum'], g2['oturum'])} devam={o2 and len(o2.devamlar)} n={len(orn2)} "
       f"acilis1={sonra} artan={artan}")


def hazirsiz(k, host: str, sn: float = 60.0, doldur: bool = False) -> None:
    """1C-2 spec: kayit ici silme duraklamasi hazir alanLA (`--ayrinti`) ve
    hazir alanSIZ sayilir. GF! (mantiksal bicimleme) sonrasi butun sektorler
    ESKI ve flas KIRLI; hemen Gb0: arka plan temizligi kayitta DURUR, kafa her
    eski sektoru kendisi siler (~25 ms iki cekirdek durur). Her kirli silme GA'da
    sayilir ve durustan sonra uretilen ilk ornek KA_SILME'li kaydi baslatir.
    ⚠ GF! karttaki kayitlari siler (bu kartta yalniz tezgah oturumlari var).
    🔴 Ilk surum acilistan hemen sonra kaydediyordu: onceki `--ayrinti` kafanin
    onundeki ~480 sektoru zaten silmisti, sonuc 0 == 0 (bos) cikti; son
    inceleme ayrica GF! sonrasi bu silmelerin HIC sayilmadigini buldu."""
    print(f"\n── hazirsiz: GF! ve hemen Gb0 {sn:.0f} s (butun sektorler kirli)")
    komut(k, "Gd", 3)
    if doldur:
        # Kafanin ONUNDEKI sektorler de kirli olsun: 1A-2'nin GF! temizligi
        # butun bolumu silmisti ve o gunden beri ~1000 sektor kullanildi —
        # 40 dk'lik ilk deneme (eski firmware) kirli sektore HIC ulasmadi.
        print("  bolum Gb20 ile DOLU'ya dek dolduruluyor (~1.6 sa)...")
        komut(k, "Gb20", 5, lambda x: x["durum"] == 2)
        son = time.time() + 4 * 3600
        g = None
        while time.time() < son:
            _, g = dinle(k, 60, lambda x: x["durum"] == 3)
            if g and g["durum"] == 3:
                break
            g = durum_iste(k)
            if g and g["durum"] == 3:
                break
        ok("bolum doldu (DOLU, durum 3)", bool(g) and g["durum"] == 3, f"{g}")
        # 🔴 ilk surum burada esitleyip onayliyordu: onaylar gelirken kart BOSTA
        # oldugu icin on silme kafanin onunu temizledi ve 60 s'lik kayit o temiz
        # bolgede kaldi (yine 0 == 0). Esitleme YOK: GF! onaysiz tezgah verisini
        # mantiksal siler, flas kirli kalir.
    k.yaz("GF!\n")
    time.sleep(1.5)
    g0 = durum_iste(k)
    ga0 = _ga(k)
    _, g = komut(k, "Gb0", 8, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    time.sleep(sn)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    ga1 = _ga(k)
    kay, o = _ayr_esitle(k, host, oid)
    orn = KB.ayrinti_ornekler(o) if o else []
    kayitlar = sorted(o.ayrinti, key=lambda r: r["sira"]) if o else []
    silme = [r for r in kayitlar if r["bayrak"] & KB.KA_SILME]
    t = {s: us for s, us, *_ in orn}
    bosluk = {r["ilk"]: t[r["ilk"]] - t[r["ilk"] - 1] for r in kayitlar if r["ilk"] - 1 in t}
    sb = sorted(bosluk.get(r["ilk"], 0) for r in silme)
    diger = sorted(b for s, b in bosluk.items() if b > 16380 and s not in {r["ilk"] for r in silme})
    fark = (ga1[3] - ga0[3]) if ga0 and ga1 else None
    print(f"  GA {ga0} -> {ga1} · {len(orn)} ornek · {len(kayitlar)} kayit · KA_SILME {len(silme)} "
          f"· onundeki bosluk ortanca {sb[len(sb) // 2] if sb else '-'} us, en kucuk "
          f"{sb[0] if sb else '-'}, en buyuk {sb[-1] if sb else '-'} · bayraksiz > 16.38 ms: {diger[:5]}")
    ok("GF! sonrasi hemen ayrintili kayit: kirli silme GERCEKTEN oldu ve sayildi; her biri bir "
       "KA_SILME kaydi (GA'dan en fazla 1 eksik: Gd'nin son bosaltmasi); sira kesintisiz, dusen yok",
       bool(g0) and g0["doluluk"] == 0 and bool(orn) and len(silme) > 0 and fark is not None
       and 0 <= fark - len(silme) <= 1 and ga1[2] == 0
       and [s for s, *_ in orn] == list(range(len(orn))),
       f"KA_SILME={len(silme)} GA silme +{fark} n={len(orn)}")
    ok("KA_SILME'li her kayit silme DURUSUNDAN hemen sonra baslar (ilk orneginin onunde "
       ">= 15 ms bosluk)", bool(sb) and sb[0] >= 15000, f"bosluklar {sb[:8]}")


def _gt(k) -> list[int] | None:
    s, _ = komut(k, "G?", 2)
    gt = next((x.split() for x in s if x.startswith("GT ")), None)
    return [int(v) for v in gt[1:]] if gt and len(gt) == 5 and all(
        v.isdigit() for v in gt[1:]) else None


def _skop_frekans(y: dict) -> float:
    """Kodlardan frekans: esigin (tepe-tepe ortasi) yukselen gecisleri arasi."""
    v = y["kodlar"]
    if not v:
        return 0.0
    mn, mx = min(v), max(v)
    orta, h = (mn + mx) / 2, max(2.0, (mx - mn) / 8)
    gec, alt = [], v[0] < orta
    for j, x in enumerate(v):
        if alt and x > orta + h:
            gec.append(j)
            alt = False
        elif not alt and x < orta - h:
            alt = True
    if len(gec) < 2:
        return 0.0
    return y["meta"]["hz"] / ((gec[-1] - gec[0]) / (len(gec) - 1))


def skop(k, host: str) -> None:
    """1C-3 osiloskop gunlugu kartta. Skop ADS'e bagli DEGIL (ADC1, GPIO4). CAL
    (GPIO10, X1000) girise RC duzenegiyle ya da tek telle bagliysa 1 kHz olculur;
    bagli degilse (kart kutuda, 2026-10-01) yakalamalar duz gelir ve frekans
    sinanmaz — boru hatti, retler, olcumun surmesi ve acilis yine sinanir."""
    from tezgah_blokaj import seri_yakala
    print("\n── skop: osiloskop gunlugu (1C-3)")
    komut(k, "Gd", 3)
    for c in ("X1000", "x500", "tm0", "tp25", "te0", "th14", "tl4095", "tb3"):
        komut(k, c, 0.4)
    b, _ = seri_yakala(k)
    mn, mx = (min(b["ornek"]), max(b["ornek"])) if b and b.get("ornek") else (0, 0)
    sinyal = mx - mn > 60
    print(f"  skop girisi: {mn}..{mx} kod — {'CAL 1 kHz VAR' if sinyal else 'SINYAL YOK (frekans sinanmaz)'}")
    komut(k, f"tl{(mn + mx) // 2 if sinyal else 2048}", 0.4)

    def d_say(sn: float) -> float:
        satir, _ = dinle(k, sn)
        return sum(1 for x in satir if x.startswith("D ")) / sn

    def bitir_esitle(oid: int):
        komut(k, "Gd", 6, lambda x: x["durum"] == 1)
        return _ayr_esitle(k, host, oid)[1]

    # Gt0: her tetik (kip NORMAL'e alinir, durunca GERI)
    d0 = d_say(8)
    _, g = komut(k, "Gt0", 8, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    d1 = d_say(20)
    gt = _gt(k)
    st, _ = komut(k, "Gtd", 4)
    sq, _ = komut(k, "t?", 1.5)
    o = bitir_esitle(oid)
    yk = sorted(o.skoplar.values(), key=lambda y: y["t_sira"]) if o else []
    fr = [_skop_frekans(y) for y in yk if y["tam"]]
    kip0 = any("kip=0" in x for x in sq if x.startswith("T "))
    print(f"  Gt0 20 s: {len(yk)} yakalama · D/s {d0:.1f} -> {d1:.1f} · GT {gt} · frekans "
          f"{[round(f) for f in fr[:5]]} · kip geri: {kip0}")
    ok("Gt0: SKOP oturumu; tetik beklerken OLCUM SURER (D/s en az yari — once 5.0 -> 0.1 idi); "
       "durunca kip GERI (OTO); SKOP_KAL olayi" + (" ; her yakalama tam ve ~1 kHz" if sinyal
                                                    else "; sinyal yok: tetiksiz yakalama KAYDEDILMEZ"),
       o is not None and o.basla is not None and o.basla.oturum_turu == KB.OTURUM_SKOP
       and d1 >= 0.4 * d0 and kip0 and bool(gt) and gt[0] == 1
       and any(x.get("tur") == KB.KO_SKOP_KAL and len(x.get("mv", [])) == 17 for x in o.olaylar)
       and ((len(yk) >= 5 and all(y["tam"] for y in yk) and all(950 < f < 1050 for f in fr)
             and len(fr) == len(yk)) if sinyal else not yk),
       f"n={len(yk)} D/s {d0:.1f}->{d1:.1f} kip0={kip0} GT={gt} Gtd={[x for x in st if 'G' in x][:2]}")
    # Gt2000 (OTO: tetiksiz da yakalar)
    komut(k, "tm0", 0.4)
    _, g = komut(k, "Gt2000", 8, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    time.sleep(30)
    gt = _gt(k)
    komut(k, "Gtd", 4)
    o = bitir_esitle(oid)
    yk = sorted(o.skoplar.values(), key=lambda y: y["t_sira"]) if o else []
    ara = sorted(b2["meta"]["t_ms"] - a2["meta"]["t_ms"] for a2, b2 in zip(yk, yk[1:]))
    ikili = [KB.skop_ikili(y) for y in yk]
    print(f"  Gt2000 30 s: {len(yk)} yakalama · aralik ortanca {ara[len(ara) // 2] if ara else '-'} ms "
          f"· GT {gt}")
    ok("Gt2000: ~15 yakalama, aralik ortancasi ~2000 ms, hepsi TAM ve /skop.bin (S3B) bicimine "
       "cevrilir; GT yakalama == flastaki; numaralar tekrarsiz",
       12 <= len(yk) <= 17 and bool(ara) and 1900 <= ara[len(ara) // 2] <= 2600
       and all(y["tam"] for y in yk) and all(x is not None and x[:3] == b"S3B" for x in ikili)
       and bool(gt) and abs(gt[2] - len(yk)) <= 1 and len({y["no"] for y in yk}) == len(yk),
       f"n={len(yk)} ara={ara[:5]} GT={gt}")
    # OLCUM oturumuna ekleme + emniyet retleri + Gtd olcumu KAPATMAZ (K11)
    komut(k, "Gd", 3)
    _, g = komut(k, "Gb200", 8, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    komut(k, "Gt2000", 3)
    time.sleep(6)
    sp = []
    for _ in range(4):                         # yakalama ucustaysa once o ret gelir
        sp, _ = komut(k, "p1", 1.5)
        if any("osiloskop gunlugu suruyor" in x for x in sp):
            break
        time.sleep(1.0)
    st, _ = komut(k, "t", 2)
    time.sleep(4)
    komut(k, "Gtd", 4)
    g2 = durum_iste(k)
    time.sleep(3)
    o = bitir_esitle(oid)
    ok("Gb200 + Gt2000: yakalamalar OLCUM oturumuna (noktalar da var); gunlukte p1 ve elle `t` "
       "REDDEDILDI; Gtd yalniz gunlugu durdurdu, OLCUM SURDU (K11)",
       o is not None and o.basla is not None and o.basla.oturum_turu == KB.OTURUM_OLCUM
       and len(o.noktalar) > 0 and len(o.skoplar) >= 2 and all(y["tam"] for y in o.skoplar.values())
       and any("osiloskop gunlugu suruyor" in x for x in sp)
       and any("osiloskop gunlugu suruyor" in x for x in st)
       and bool(g2) and g2["durum"] == 2 and g2["oturum"] == oid,
       f"nokta={o and len(o.noktalar)} skop={o and len(o.skoplar)} Gtd sonrasi={g2 and (g2['durum'], g2['oturum'])} "
       f"p1={[x for x in sp if '!' in x][:1]} t={[x for x in st if '!' in x][:1]}")
    # yeniden baslama: SKOP oturumu sebep 5, gunluk surmez
    _, g = komut(k, "Gt2000", 8, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    time.sleep(5)
    k.sifirla()
    acildi = yeni_acilis(k)
    time.sleep(8)
    gt = _gt(k)
    o = _ayr_esitle(k, host, oid)[1]
    ok("gunluk surerken yeniden baslatma: SKOP oturumu sebep 5 ile kapandi, DEVAM yok, gunluk "
       "surmuyor (GT etkin 0); onceki yakalamalar tam",
       acildi and o is not None and o.bitir is not None and o.bitir["sebep"] == 5
       and not o.devamlar and bool(gt) and gt[0] == 0
       and len(o.skoplar) >= 1 and all(y["tam"] for y in o.skoplar.values()),
       f"bitir={o and o.bitir} devam={o and len(o.devamlar)} GT={gt}")
    komut(k, "X0", 0.5)
    komut(k, "tm0", 0.4)


def _gp(k) -> list[int] | None:
    s, _ = komut(k, "G?", 2)
    gp = next((x.split() for x in s if x.startswith("GP ")), None)
    return [int(v) for v in gp[1:]] if gp and len(gp) == 6 and all(
        v.isdigit() for v in gp[1:]) else None


def _durum_bekle(k, durum: int, sn: float) -> tuple[dict | None, float]:
    t0 = time.time()
    _, g = dinle(k, sn, lambda x: x["durum"] == durum)
    return g, time.time() - t0


def plan(k, host: str) -> None:
    """1C-4 zamanlanmis kayit kartta (NTP saati gerekir: kart ev aginda STA)."""
    print("\n── plan: zamanlanmis kayit (1C-4)")
    komut(k, "Gd", 3)
    komut(k, "Gp-", 1.5)
    red = []
    for c in ("Gp+5,10", "Gp+5,10,7", "Gp+99999999999,10,200", "Gpx", "Gp+5,9999999,200"):
        s, _ = komut(k, c, 1.2)
        red.append(any(x.startswith("! G") for x in s))
    ok("Gp gecersiz argumanlar REDDEDILDI (eksik alan, gecersiz hiz, tasan sayi, harf, > 30 gun)",
       all(red), str(red))
    # A: baslar, sebep 7 ile biter
    t_kom = time.time()
    s, _ = komut(k, "Gp+20,30,200", 1.5)
    if any("saat yok" in x for x in s):
        ok("NTP saati var (plan kurulabilir)", False, "kart 'saat yok' dedi — STA/NTP yok")
        return
    gp1 = _gp(k)
    g, _ = _durum_bekle(k, 2, 40)
    t_bas = time.time() - t_kom
    oid = g["oturum"] if g else 0
    g2, _ = _durum_bekle(k, 1, 45)
    t_bit = time.time() - t_kom
    gp2 = _gp(k)
    kay, o = _ayr_esitle(k, host, oid)
    pl = [x for x in (o.olaylar if o else []) if x.get("tur") == getattr(KB, "KO_PLAN", -1)]
    print(f"  Gp+20,30,200: basladi +{t_bas:.1f} s, bitti +{t_bit:.1f} s · GP {gp1} -> {gp2} · PLAN {pl[:1]}")
    ok("Gp+20,30,200: ~20 s sonra OLCUM oturumu acildi, ~50 s'de sebep 7 'planli sure doldu' ile "
       "kapandi (GP 1 -> 3); PLAN olayi sure 30 / hiz 200; noktalar var",
       bool(gp1) and gp1[0] == 1 and 18 <= t_bas <= 24 and bool(g2) and 48 <= t_bit <= 55
       and o is not None and o.bitir is not None and o.bitir["sebep"] == 7
       and bool(pl) and pl[0]["sure_s"] == 30 and pl[0]["hiz_ms"] == 200 and len(o.noktalar) > 0
       and bool(gp2) and gp2[0] == 3,
       f"bas={t_bas:.1f} bit={t_bit:.1f} GP={gp1}->{gp2} bitir={o and o.bitir}")
    # B: plan surerken yeniden baslatma -> DEVAM, bitis planlanan anda
    t_kom = time.time()
    komut(k, "Gp+8,45,200", 1.5)
    g, _ = _durum_bekle(k, 2, 30)
    oid = g["oturum"] if g else 0
    time.sleep(5)
    k.sifirla()
    acildi = yeni_acilis(k)
    g2, _ = _durum_bekle(k, 1, 70)
    t_bit = time.time() - t_kom
    kay, o = _ayr_esitle(k, host, oid)
    print(f"  plan + yeniden baslatma: bitti +{t_bit:.1f} s (plan 53) · devam {o and len(o.devamlar)}")
    ok("plan surerken yeniden baslatma: oturum DEVAM aldi, plan NVS'ten SURUYOR, planlanan anda "
       "(~53 s) sebep 7 ile kapandi",
       acildi and o is not None and len(o.devamlar) == 1 and o.bitir is not None
       and o.bitir["sebep"] == 7 and 50 <= t_bit <= 60,
       f"bit={t_bit:.1f} devam={o and len(o.devamlar)} bitir={o and o.bitir}")
    # C: elle kayit surerken plan ATLANIR, elle kayit surer
    _, g = komut(k, "Gb200", 6, lambda x: x["durum"] == 2)
    oid = g["oturum"] if g else 0
    komut(k, "Gp+3,20,1000", 1.5)
    time.sleep(7)
    gp = _gp(k)
    gd = durum_iste(k)
    komut(k, "Gd", 5, lambda x: x["durum"] == 1)
    ok("elle kayit surerken plan ATLANDI (GP 4), elle kayit BOLUNMEDI",
       bool(gp) and gp[0] == 4 and bool(gd) and gd["durum"] == 2 and gd["oturum"] == oid,
       f"GP={gp} durum={gd and (gd['durum'], gd['oturum'])}")
    # D: iptal
    komut(k, "Gp+30,10,200", 1.5)
    gp_a = _gp(k)
    komut(k, "Gp-", 1.5)
    gp_b = _gp(k)
    ok("Gp- bekleyen plani iptal eder (GP 1 -> 0)",
       bool(gp_a) and gp_a[0] == 1 and bool(gp_b) and gp_b[0] == 0, f"{gp_a} -> {gp_b}")


def esit(k, host: str, port: str) -> None:
    print("\n── esit: esitlenen dosya == flastaki bolum")
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))
        dosya = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
        k.kapat()
        ofset, boyut = kayit_bolumu()
        dokum = Path(d) / "kayit.bin"
        time.sleep(1.0)                        # port birakilsin
        if flas_oku(port, ofset, boyut, dokum):
            raise SystemExit("esptool bolumu okuyamadi")
        flas, bozuk = KB.flas_coz(dokum.read_bytes(), 4096)

    def ozu(x):
        return (x.tur, x.sira, x.oturum, x.yuk)
    sozluk = {x.sira: x for x in flas}
    ayni = [x for x in dosya if x.sira in sozluk and ozu(sozluk[x.sira]) == ozu(x)]
    ok("esitlenen her kayit flastaki kayitla BAYT BAYT ayni",
       bool(dosya) and len(ayni) == len(dosya),
       f"{len(ayni)}/{len(dosya)} (flasta {len(flas)} kayit, {bozuk} bozuk sektor ucu)")


def main() -> int:
    a = sys.argv[1:]

    def sec(ad, v=None):
        return a[a.index(ad) + 1] if ad in a else v

    port, host = sec("--port", "COM6"), sec("--http", "olcum.local")
    if "--yedek" in a:
        return yedek(port)
    k = kart_baglanti.SeriKart(port)
    k.ac()
    time.sleep(1.0)
    try:
        if "--duman" in a:
            duman(k, host)
        if "--durma" in a:
            durma(k)
        if "--kesinti" in a:
            kesinti(k, host, int(sec("--kesinti", "20")))
        if "--dolu" in a:
            dolu(k, host)
        if "--bicim" in a:
            bicim(k, host)
        if "--kal" in a:
            kal(k, host)
        if "--pil" in a:
            pil(k, host)
        if "--ayrinti" in a:
            ayrinti(k, host)
        if "--skop" in a:
            skop(k, host)
        if "--plan" in a:
            plan(k, host)
        if "--hazirsiz" in a:
            hazirsiz(k, host, float(sec("--sure", "60")), "--doldur" in a)
        if "--esit" in a:
            esit(k, host, port)
    finally:
        k.kapat()
    print(f"\n{gecti}/{gecti + kaldi} tezgah denetimi gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
