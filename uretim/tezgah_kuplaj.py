# -*- coding: utf-8 -*-
"""B44 — KUPLAJ DENEYI: skop orneklerine hata PINDEN mi, HATTAN mi giriyor?

    python tezgah_kuplaj.py --asama 1        # tel oynatmadan (K0 K1 K2 K3 K0)
    python tezgah_kuplaj.py --asama 2        # SDA/SCL telleri GPIO41/42'deyken (K0 K4 K5 K0)
    python tezgah_kuplaj.py --asama 1 --tekrar 20 --port COM6

B41'de GPIO8/9 (I2C) kenarlari GPIO4'un skop donusumune tek-ornek hata
sokuyordu (3-9/1000) ve cozum olarak "I2C'yi ADC1 disina tasi" onerildi.
Ama gerekce KANITLANMADI, ve karsi bir isaret var: GPIO10 da ADC1 pini ve
20 kHz CAL kare dalgasi basarken hata SIFIRDI. Tasimanin ise yarayip
yaramayacagini tel oynatmadan once OLC.

Firmware `tK<pinler>`: normal bir skop yakalamasi (ADS susuyor) + yakalama
boyunca secilen pinlerde I2C benzeri kenar patlamasi. Surus her durumda
AYNI (acik-drenaj + dahili pull-up); degisen yalnizca pinin YERI ve YUKU.

    durum  pinler   pin nerede            hatta yuk (modul, pull-up, tel)
    K0     —        (kontrol)             —
    K1     8,9      ADC1 pedi             VAR   <- B41'in durumu
    K2     2        ADC1 pedi             yok
    K3     40       ADC'siz pin           yok
    K4     8,9      ADC1 pedi             yok   (asama 2: teller sokuk)
    K5     41,42    ADC'siz pin           VAR   (asama 2: teller orada) = TASINMIS HAL

Okuma:
    K5 ~ 0 ve K1 > 0          -> TASIMAK ISE YARAR (dogrudan sinandi)
    K5 ~ K1                   -> tasimak ISE YARAMAZ; sebep hat/tel, pin degil
    K2 > 0, K3 = 0            -> ADC1 pedi kendi basina hassas
    K4 = 0, K1 > 0            -> yuk (hat akimi) sart
"""
from __future__ import annotations

import statistics as st
import sys
import time
from pathlib import Path

KOK = Path(__file__).parent.parent
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                       # noqa: E402
from arsiv import SkopCozucu                               # noqa: E402

ASAMA = {
    "1": [("K0", "", "kontrol (tiklatma yok)"),
          ("K1", "8,9", "I2C hatlari, teller BAGLI (B41 durumu)"),
          ("K2", "2", "BOS ADC1 pini"),
          ("K3", "40", "BOS ADC'siz pin"),
          ("K0", "", "kontrol (kayma var mi)")],
    # Asama 1'in ilk kosusu (2026-09-13): K1 1.68, K2 0, K3 4.08 /1000 —
    # BOS ADC'SIZ pin hata sokuyor, bos ADC1 pini sokmuyor; K1 onceki
    # kosuda 6.72 idi. Tek kosuya guvenilmedi: `--karisik` durumlari tur
    # tur ICICE kosar (kayma ve sira etkisi durumlara esit dagilir).
    "1b": [("K0", "", "kontrol (tiklatma yok)"),
           ("K1", "8,9", "I2C hatlari, teller BAGLI"),
           ("K2", "2", "BOS ADC1 pini (GPIO2)"),
           ("K3", "40", "BOS ADC'siz pin (GPIO40)"),
           ("K3b", "41", "BOS ADC'siz pin (GPIO41)")],
    # 1b icice kosusu (panel sekmesi ACIKKEN): K0 0.10, K1 0.50, K2 0,
    # K3 0 (!), K3b 0.10 /1000. Sirali kosuda K3 4.08 idi -> hata PINE
    # degil ZAMANA bagli. En guclu aday WiFi trafigi. `W*` durumlarinda
    # yakalama boyunca PC karta yogun HTTP istegi atiyor (tiklatma yok).
    "1c": [("K0", "", "kontrol (tiklatma yok, WiFi bosta)"),
           ("W", "", "tiklatma yok, WiFi YUKLU (PC -> /app.js dongusu)"),
           ("K1", "8,9", "I2C hatlari, teller BAGLI, WiFi bosta"),
           ("K3", "40", "BOS ADC'siz pin, WiFi bosta")],
    # 1c (panel sekmesi KAPALI, 20 tur): K0 4.02 (!), W 0, K1 0.90, K3 0.
    # Kontrolde 3/20 yakalama bozuk, ikisinde TAM 33 hata — tiklatmadan
    # BAGIMSIZ, ara sira gelen bir olay. `--olay` yalniz kontrol yakalar,
    # bozuk yakalamalarin ham verisini ve ZAMANINI kaydeder.
    "0": [("K0", "", "kontrol (tiklatma yok)")],
    # `--olay` (150 kontrol, CAL 20 kHz): 4 bozuk yakalama, hatalar TAM 25
    # ornekte bir, ayni fazda, 60-70 kod. 20 kHz'nin 4. harmonigi 80 kHz,
    # 83 333 Hz ornekte 3333 Hz'e = 25 ornege katlaniyor; 833/25 = 33 hata
    # (kontrolde iki kez TAM 33 gorulmustu). CAL PWM kenari ornekleme anina
    # denk gelince hata. -> Asagidaki kosular CAL KAPALI (`--cal-kapali`).
    "1d": [("K0", "", "kontrol (tiklatma yok)"),
           ("K1", "8,9", "I2C hatlari, teller BAGLI"),
           ("K2", "2", "BOS ADC1 pini (GPIO2)"),
           ("K3", "40", "BOS ADC'siz pin (GPIO40)")],
    # 1d (CAL KAPALI, 20 tur, >30 kod): K0 0, K1 2.22, K2 0.06, K3 0.18
    # /1000. Hatayi YUKLU hat uretiyor; bos pinlerde ADC1/ADC'siz farki
    # anlamli degil. Asama 2 bunu TASINMIS halde dogrudan sinar.
    # Kosum: --asama 2 --karisik --cal-kapali --tekrar 20
    "2": [("K0", "", "kontrol (tiklatma yok)"),
          ("K4", "8,9", "GPIO8/9 BOS (teller sokuk)"),
          ("K5", "41,42", "hat ADC'siz pinde, teller BAGLI = tasinmis hal"),
          ("K3", "40", "BOS ADC'siz pin (referans)")],
}


def hata_say(v, esik=60):
    """B41 ile AYNI olcut: komsu 4 ornegin medyanindan > 60 kod sapma."""
    return sum(1 for i in range(2, len(v) - 2)
               if abs(v[i] - st.median(v[i - 2:i] + v[i + 1:i + 3])) > esik)


def kuplaj_yakala(k, pinler: str, sn=15):
    """`tK<pinler>` -> (blok, patlama) ya da (None, sebep)."""
    c = SkopCozucu()
    k.yaz("tK" + pinler)
    blok = None
    patlama = None
    son = time.monotonic() + sn
    while time.monotonic() < son and (blok is None or patlama is None):
        s = k.satir_oku(0.1)
        if not s:
            continue
        if s.startswith("! "):
            return None, s
        if s.startswith("* kuplaj:") and "patlama=" in s:
            patlama = int(s.split("patlama=")[1].split()[0])
            continue
        b = c.besle(s)
        if b:
            blok = b
    if blok is None or patlama is None:
        return None, "zaman asimi"
    return blok, patlama


class WifiYuku:
    """Yakalama suresince karta ardisik HTTP GET (kartin WiFi VERICISI
    calissin diye buyuk bir dosya). Ad cozumu bir kez: mDNS gecikmesi
    yuk olcumunu bozmasin."""

    def __init__(self, host):
        import socket
        self.ip = socket.gethostbyname(host)
        self.dur = None
        self.istek = 0
        self.bayt = 0

    def __enter__(self):
        import threading
        import urllib.request
        self.dur = threading.Event()

        def dongu():
            while not self.dur.is_set():
                try:
                    with urllib.request.urlopen(f"http://{self.ip}/app.js", timeout=3) as y:
                        self.bayt += len(y.read())
                        self.istek += 1
                except OSError:
                    time.sleep(0.05)
        self.t = threading.Thread(target=dongu, daemon=True)
        self.t.start()
        time.sleep(0.2)                  # yakalama baslamadan trafik akiyor olsun
        return self

    def __exit__(self, *a):
        self.dur.set()
        self.t.join(timeout=5)


def karisik_kos(k, komut, asama, tur, http_host="olcum.local") -> int:
    """Durumlari TUR TUR icice kos; yakalama basina hata listesini sakla."""
    durumlar = ASAMA[asama]
    yuk_istek = yuk_bayt = 0
    kayit = {ad: {"pin": p, "acik": a, "hata": [], "ornek": 0, "patlama": 0}
             for ad, p, a in durumlar}
    print(f"KUPLAJ DENEYI (icice) — asama {asama} · {tur} tur x {len(durumlar)} durum (tb3)")
    for t in range(tur):
        for ad, pinler, _ in durumlar:
            if ad.startswith("W"):
                with WifiYuku(http_host) as y:
                    b, p = kuplaj_yakala(k, pinler)
                yuk_istek += y.istek
                yuk_bayt += y.bayt
            else:
                b, p = kuplaj_yakala(k, pinler)
            if b is None or not b["tam"]:
                print(f"  tur {t + 1} {ad}: REDDEDILDI ({p if b is None else 'eksik'})")
                for c in ("X0", "tl2048", "th40", "tb5"):
                    komut(c)
                k.kapat()
                return 1
            kayit[ad]["hata"].append(hata_say(b["ornek"]))
            kayit[ad].setdefault("hata30", []).append(hata_say(b["ornek"], 30))
            kayit[ad]["ornek"] += len(b["ornek"])
            kayit[ad]["patlama"] += p
        print(f"  tur {t + 1}/{tur}: " + "  ".join(
            f"{ad}={kayit[ad]['hata'][-1]}/{kayit[ad]['hata30'][-1]}" for ad, _, _ in durumlar)
            + "   (>60/>30 kod)")
    for c in ("X0", "tl2048", "th40", "tb5"):
        komut(c)
    k.kapat()

    print(f"\n  {'durum':<5} {'pinler':<6} {'ornek':>6} {'>60':>5} {'/1000':>6} {'>30':>5} {'/1000':>6} "
          f"{'hatali yakalama':>16} {'patlama':>8}  aciklama")
    for ad, v in kayit.items():
        h = sum(v["hata"])
        h30 = sum(v["hata30"])
        print(f"  {ad:<5} {v['pin'] or '-':<6} {v['ornek']:6d} {h:5d} "
              f"{1000.0 * h / v['ornek']:6.2f} {h30:5d} {1000.0 * h30 / v['ornek']:6.2f} "
              f"{sum(1 for x in v['hata30'] if x):>9d}/{len(v['hata']):<6d}"
              f"{v['patlama']:8d}  {v['acik']}")
    if yuk_istek or any(ad.startswith("W") for ad, _, _ in durumlar):
        print(f"\n  WiFi yuku: {yuk_istek} istek, {yuk_bayt / 1e6:.2f} MB (W yakalamalari boyunca)")
    k0 = kayit.get("K0")
    kontrol_temiz = k0 is not None and sum(k0["hata"]) == 0
    print(f"\n[{'OK' if kontrol_temiz else '!!'}] Kontrol (K0) hatasiz")
    patlama_var = all(v["patlama"] > 50 * len(v["hata"]) for v in kayit.values())
    print(f"[{'OK' if patlama_var else '!!'}] Her durumda patlama GERCEKTEN yapildi")
    return 0 if (kontrol_temiz and patlama_var) else 1


def olay_kaydet(k, komut, adet, yol) -> int:
    """Yalniz kontrol yakalamalari: her birinin zamani + hata indeksleri;
    bozuk olanlarin HAM verisi dosyaya."""
    import json
    t0 = time.monotonic()
    kayit = []
    print(f"OLAY KAYDI — {adet} kontrol yakalamasi (tb3, tiklatma yok)")
    for i in range(adet):
        ts = time.monotonic() - t0
        b, p = kuplaj_yakala(k, "")
        if b is None:
            print(f"  {i}: REDDEDILDI ({p})")
            continue
        v = b["ornek"]
        yer = [j for j in range(2, len(v) - 2)
               if abs(v[j] - st.median(v[j - 2:j] + v[j + 1:j + 3])) > 60]
        kayit.append({"i": i, "t": round(ts, 3), "hata": len(yer), "yer": yer,
                      "ornek": v if yer else None, "hz": b["hz"]})
        if yer:
            print(f"  {i:3d} t={ts:7.2f}s  hata={len(yer):3d}  ilk={yer[:6]}")
    for c in ("X0", "tl2048", "th40", "tb5"):
        komut(c)
    k.kapat()
    Path(yol).write_text(json.dumps(kayit), encoding="utf-8")
    bozuk = [r for r in kayit if r["hata"]]
    print(f"\n  {len(bozuk)}/{len(kayit)} yakalama bozuk · kayit: {yol}")
    if len(bozuk) >= 2:
        araliklar = [round(b2["t"] - b1["t"], 2) for b1, b2 in zip(bozuk, bozuk[1:])]
        print(f"  bozuk yakalamalar arasi sure (s): {araliklar}")
    return 0


def main() -> int:
    arg = sys.argv[1:]

    def secenek(ad, varsayilan):
        return arg[arg.index(ad) + 1] if ad in arg else varsayilan

    asama = secenek("--asama", "1")
    tekrar = int(secenek("--tekrar", "10"))
    if asama not in ASAMA:
        print("--asama 1 ya da 2")
        return 2
    # --yalniz K0,K1 : bos oldugu henuz DOGRULANMAMIS pinlere dokunmadan kos
    yalniz = secenek("--yalniz", None)
    if yalniz:
        izin = set(yalniz.split(","))
        ASAMA[asama] = [d for d in ASAMA[asama] if d[0] in izin]

    k = kart_baglanti.SeriKart(secenek("--port", None))
    k.ac()
    time.sleep(1.0)

    def komut(kom, sn=0.3):
        k.yaz(kom)
        time.sleep(sn)

    # B41'in 1. sinamasiyla AYNI kosullar: surulu dugum, tetiksiz serbest kosu.
    # `--cal-kapali`: PWM kenarlari da bir kuplaj kaynagi (bkz. "1d").
    # Dugum 100 nF'ta tutuluyor: 12 us'de 30 kod atlayamaz.
    if "--cal-kapali" in arg:
        komut("X0", 1.0)
    else:
        komut("X20000", 0.5)
        komut("x500", 1.0)
    for c in ("tm0", "tl0", "th0", "tp25", "tb3"):
        komut(c)

    if "--karisik" in arg:
        return karisik_kos(k, komut, asama, tekrar)
    if "--olay" in arg:
        return olay_kaydet(k, komut, tekrar, secenek("--olay", "_kuplaj_olay.json"))

    print(f"KUPLAJ DENEYI — asama {asama} · durum basina {tekrar} yakalama (tb3, 83 kSa/s)")
    print(f"  {'durum':<5} {'pinler':<7} {'ornek':>6} {'hata':>5} {'/1000':>6} {'patlama':>8}  aciklama")
    sonuc = {}
    tamam = True
    for ad, pinler, aciklama in ASAMA[asama]:
        ornek = hata = patlama = 0
        red = None
        for _ in range(tekrar):
            b, p = kuplaj_yakala(k, pinler)
            if b is None:
                red = p
                break
            if not b["tam"]:
                red = "eksik yakalama"
                break
            ornek += len(b["ornek"])
            hata += hata_say(b["ornek"])
            patlama += p
        if red:
            print(f"  {ad:<5} {pinler or '-':<7} REDDEDILDI: {red}")
            tamam = False
            break
        oran = 1000.0 * hata / ornek if ornek else float("nan")
        sonuc.setdefault(ad, []).append((ornek, hata, patlama))
        print(f"  {ad:<5} {pinler or '-':<7} {ornek:6d} {hata:5d} {oran:6.2f} {patlama:8d}  {aciklama}")

    for c in ("X0", "tl2048", "th40", "tb5"):
        komut(c)
    k.kapat()
    if not tamam:
        return 1

    # ── gecerlilik: bos iddialari ele ─────────────────────────────────
    gecti = kaldi = 0

    def ok(ad_, kosul, ek=""):
        nonlocal gecti, kaldi
        gecti, kaldi = gecti + bool(kosul), kaldi + (not kosul)
        print(f"[{'OK' if kosul else '!!'}] {ad_}" + (f"  {ek}" if ek else ""))

    print()
    k0 = sonuc["K0"]
    ok("Kontrol (K0) iki kez de hatasiz", all(h == 0 for _, h, _ in k0),
       "kontrolde hata varsa deney OLCEMEZ — once o sebep bulunmali")
    tiklatan = [(a, v) for a, v in sonuc.items() if a != "K0"]
    ok("Tiklatma durumlarinda patlama GERCEKTEN yapildi",
       all(p > 50 for a, v in tiklatan for _, _, p in v),
       "patlama 0 ise 'hata yok' bos bir sonuc olurdu")
    ok("Kontrolde patlama sayaci da calisiyor (tiklatma yok, tempo ayni)",
       all(p > 50 for _, _, p in k0))
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
