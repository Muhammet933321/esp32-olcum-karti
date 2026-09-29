# -*- coding: utf-8 -*-
"""B72 — KAYIT MOTORU GERCEK KARTTA (tezgah; zincirde DEGIL).

    python tezgah_kayit.py --yedek                 tam flas yedegi (depo DISINA)
    python tezgah_kayit.py --duman                 G komutlari + 10 s kayit + esitleme
    python tezgah_kayit.py --durma                 flas yazmasinin olcume etkisi
    python tezgah_kayit.py --kesinti 20            kayit surerken 20 RTS sifirlamasi
    python tezgah_kayit.py --esit                  esitlenen dosya == flastaki bolum
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
    rc = subprocess.run([str(esptool()), "--port", port, "-b", "921600", "read-flash",
                         "0x0", "0x1000000", str(hedef)]).returncode
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


def esit(k, host: str, port: str) -> None:
    print("\n── esit: esitlenen dosya == flastaki bolum")
    with tempfile.TemporaryDirectory() as d:
        esitle(k, host, Path(d))
        dosya = KB.akis_coz((Path(d) / KE.DOSYA).read_bytes())
        k.kapat()
        ofset, boyut = kayit_bolumu()
        dokum = Path(d) / "kayit.bin"
        subprocess.run([str(esptool()), "--port", port, "-b", "921600", "read-flash",
                        hex(ofset), hex(boyut), str(dokum)], check=True)
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
        if "--esit" in a:
            esit(k, host, port)
    finally:
        k.kapat()
    print(f"\n{gecti}/{gecti + kaldi} tezgah denetimi gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
