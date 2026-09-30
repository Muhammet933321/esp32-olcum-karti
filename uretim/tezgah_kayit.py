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
        if "--esit" in a:
            esit(k, host, port)
    finally:
        k.kapat()
    print(f"\n{gecti}/{gecti + kaldi} tezgah denetimi gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
