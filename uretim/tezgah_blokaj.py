# -*- coding: utf-8 -*-
"""BOSTA BLOKAJ OLCUMU — `K` sayacini sifirla, bekle, oku. Tekrarli.

    python tezgah_blokaj.py                 # 3 x 60 s
    python tezgah_blokaj.py --sure 45 --tekrar 4 --port COM6
    python tezgah_blokaj.py --skop          # B40/B41/B42: butunluk + blokaj + susma + tetik yeri
    python tezgah_blokaj.py --tetik         # B42: yalniz tetik konumu (~1 dk)
    python tezgah_blokaj.py --olcum [--http olcum.local]   # B43: olcum satiri eksenle ayni mi, WiFi'de var mi
    python tezgah_blokaj.py --onay          # B47: gurultu reddi igneyi eliyor mu (tK8,9 ile A/B)

🔴 NEDEN: bringup kosucusu tek bir 45 s penceresine bakiyor ve kartta
   ~50 s'de bir ~22 ms'lik periyodik bir olay var (B27 A4'te olculdu).
   Tek pencere o olayi bazen gorur bazen gormez — ayni kart iki farkli
   cevap verir. Tekrarli olcum dagilimi gosterir: "kac pencerede kac
   uzun tur, en uzunu ne".

   Bir firmware degisikliginin blokaji ARTIRIP ARTIRMADIGINI soylemek
   icin iki surumu AYNI betikle olcup karsilastirmak gerekiyor; tek
   kosu bunu soyleyemez.

⚠ PASIF: pencere boyunca HICBIR komut gonderilmiyor — `?` bile tek
  basina bir turu ~12 ms bloklar (B28).
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).parent.parent
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                       # noqa: E402
from arsiv import SkopCozucu                               # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))


def seri_yakala(k, sn=30):
    """`t` gonder, ASCII dokumu coz. (blok, S2'ye kadar gecen s) doner;
    kart `! ` ile reddederse (None, None)."""
    c = SkopCozucu()
    t0 = time.monotonic()
    k.yaz("t")
    ts2 = None
    son_ = t0 + sn
    while time.monotonic() < son_:
        s = k.satir_oku(0.1)
        if s is None:
            continue
        if s.startswith("S2") and ts2 is None:
            ts2 = time.monotonic() - t0
        if s.startswith("! "):
            return None, None
        b = c.besle(s)
        if b:
            return b, ts2
    return None, ts2


def skop_tetik_konumu(k, durumlar=((1, 25), (1, 50), (1, 75), (3, 10), (5, 25)),
                      tekrar=6) -> int:
    """B42 — tetik ornegi ON-TETIK ayarinin soyledigi yerde mi.

    Panelden olculdu (2026-09-13, CAL + RC duzenegi, on-tetik %25):
      5 ms/bol, 1000 ornek, beklenen 250 -> 143 42 3 54 113 249 109 229 105 73
      200 us/bol, 167 ornek, beklenen 41 -> 153 12 127 123 2 38 147 4 13 123
    ve iki yakalamada isaretin gosterdigi ornek esigi GECMIYORDU. Sebep:
    tetikten sonraki sayac bitince DMA cercevesinin (256 ornek) geri kalani
    halkaya yazilmaya devam ediyor; on-tetik gecmisini, kisa pencerede
    tetik orneginin KENDISINI eziyordu. Zincir ve butun tezgah testleri
    yesildi: hicbiri tetigin YERINE bakmiyordu.

    Her yakalamada sinanan (NORMAL kip — tetiksiz yakalama sayilmaz):
      (a) tetik_idx == adet * on // 100   (firmware'in tamsayi bolmesi)
      (b) v[idx-1] < esik <= v[idx]       (isaret GERCEK bir yukselen gecis)
    """
    def komut(kom, sn=0.3):
        k.yaz(kom)
        time.sleep(sn)

    komut("X1000", 0.5)
    komut("x500", 1.0)
    # esik: serbest kosu yakalamasinin ortasi (RC dugumu ~130 kod tepe-tepe)
    for c in ("tm0", "tp25", "te0", "th14", "tl4095", "tb1"):
        komut(c)
    b, _ = seri_yakala(k)
    if not b or not b["ornek"]:
        ok("[!] Tetik konumu olculebildi", False, "serbest kosu yakalamasi gelmedi")
        return 1
    mn, mx = min(b["ornek"]), max(b["ornek"])
    esik = (mn + mx) // 2
    ok("CAL 1 kHz sinyali skop girisinde var (tepe-tepe > 60 kod)", mx - mn > 60,
       f"{mn}..{mx} — RC duzenegi (GPIO10 -> 2x10K/100nF -> GPIO4) sokulmusse bu sinama anlamsiz")
    komut(f"tl{esik}")
    komut("tm1")                                     # NORMAL: tetiksiz sonuc yok

    print(f"  esik {esik} kod · her durumda {tekrar} yakalama")
    print(f"  {'taban':>5} {'on':>4} {'adet':>5} {'beklenen':>8} | tetik_idx (x = esigi gecmiyor)")
    konum_tamam = gecis_tamam = True
    yakalanan = 0
    for tb, on in durumlar:
        komut(f"tb{tb}")
        komut(f"tp{on}")
        idxler = []
        beklenen = None
        for _ in range(tekrar):
            b, _ = seri_yakala(k, 10)
            if not b or not b["tam"] or not b["tetiklendi"]:
                idxler.append("YOK")
                konum_tamam = gecis_tamam = False
                continue
            yakalanan += 1
            v, i = b["ornek"], b["tetik_idx"]
            beklenen = b["adet_bildirilen"] * on // 100
            gecis = 0 < i < len(v) and v[i - 1] < esik <= v[i]
            konum_tamam = konum_tamam and i == beklenen
            gecis_tamam = gecis_tamam and gecis
            idxler.append(f"{i}{'' if gecis else 'x'}")
        adet = b["adet_bildirilen"] if b else -1
        print(f"  tb{tb:<3} {on:3d}% {adet:5d} {beklenen if beklenen is not None else -1:8d} | "
              + " ".join(str(x) for x in idxler))

    for c in ("tm0", "tp25", "th40", "tl2048", "tb5"):
        komut(c)
    komut("X0", 0.5)
    ok("[!] Tetik ornegi ON-TETIK ayarinin yerinde (her yakalamada)",
       yakalanan > 0 and konum_tamam,
       "B42 oncesi cerceve kuyrugu gecmisi eziyordu: 5 ms/bol'de 3..249 (beklenen 250)")
    ok("[!] Tetik isareti GERCEK esik gecisini gosteriyor",
       yakalanan > 0 and gecis_tamam,
       "kisa pencerede tetik orneginin kendisi eziliyordu — iz kilitlenmez")
    return 1 if kaldi else 0


def ct_tablosu(k):
    """`CT` -> (oran, ofset, kodlar, mv) ya da None (tablo yok)."""
    k.yaz("CT")
    son_ = time.monotonic() + 4
    while time.monotonic() < son_:
        s = k.satir_oku(0.2)
        if s and s.startswith("CT "):
            p = s.split()
            if p[1] == "0":
                return None
            alan = dict(x.split("=", 1) for x in p[2:] if "=" in x)
            dugum = [tuple(int(y) for y in x.split(":")) for x in p[2:] if ":" in x]
            return (float(alan["oran"]), float(alan["ofset"]),
                    [d[0] for d in dugum], [d[1] for d in dugum])
    return None


def eksen_volt(kod, ct, ofset):
    """Arayuzun `kodVolt` + `kalMv` kuralinin BIREBIR karsiligi (app.js):
    tablo disi kod uctaki egimle uzatiliyor, ic kodlar dogrusal aradeger."""
    oran, _, ks, vs = ct
    n = len(ks)
    if kod <= ks[0]:
        mv = vs[0] + (kod - ks[0]) * (vs[1] - vs[0]) / (ks[1] - ks[0])
    elif kod >= ks[-1]:
        mv = vs[-1] + (kod - ks[-1]) * (vs[-1] - vs[-2]) / (ks[-1] - ks[-2])
    else:
        i = 0
        while i < n - 2 and ks[i + 1] < kod:
            i += 1
        mv = vs[i] + (vs[i + 1] - vs[i]) * (kod - ks[i]) / (ks[i + 1] - ks[i])
    return mv / 1000.0 * oran - ofset


def m_coz(satir):
    return {a.split("=", 1)[0]: float(a.split("=", 1)[1])
            for a in (satir or "").split()[1:] if "=" in a}


def eksenden_olcum(kodlar, ct, ofset):
    v = [eksen_volt(x, ct, ofset) for x in kodlar]
    ort = sum(v) / len(v)
    return {"Vmax": max(v), "Vmin": min(v), "Vpp": max(v) - min(v), "Vort": ort,
            "Vrms": (sum(x * x for x in v) / len(v)) ** 0.5,
            "Vac": max(0.0, sum((x - ort) ** 2 for x in v) / len(v)) ** 0.5}


def skop_olcum_kalibre(k, http_host="olcum.local", tol_v=0.002) -> int:
    """B43 — skop OLCUM SATIRI eksenle ayni kalibrasyonda mi, WiFi'de var mi.

    Panelden olculdu (2026-09-13, CAL 1 kHz, ayni kodlar 1843..1989):
        M satiri   Vmax -6.27  Vmin -10.47  Vpp 4.20 V   (dogrusal model)
        eksen      Vmax +0.73  Vmin  -3.93  Vpp 4.66 V   (eFuse tablosu, B36)
    ve WiFi (ikili yol) yakalamalarinda olcum satiri HIC yoktu (`olcum: null`).

    Sinanan:
      1. ASCII: `M` volt degerleri, dalganin KENDI kodlarindan arayuz
         kuraliyla hesaplananla <= tol_v
      2. frekans CAL'e +-%1 (iki yolda)
      3. ikili: `M` satiri onay satirindan ONCE geliyor (arayuz onu o
         yakalamaya bagliyor)
      4. ikili: o `M`, `/skop.bin`'den cekilen dalganin degerleri
    """
    import struct
    import urllib.request

    def komut(kom, sn=0.3):
        k.yaz(kom)
        time.sleep(sn)

    ct = ct_tablosu(k)
    if not ct:
        ok("[!] Kartta kalibrasyon tablosu var (CT)", False, "CT 0 — eFuse egrisi yok")
        return 1
    komut("X1000", 0.5)
    komut("x500", 1.0)
    for c in ("tm0", "tp25", "te0", "th14", "tl1916", "tb3"):
        komut(c)

    def karsilastir(ad, m, beklenen):
        farklar = {a: m.get(a, float("nan")) - beklenen[a] for a in beklenen}
        en = max(abs(x) if x == x else float("inf") for x in farklar.values())
        print(f"  {ad:<7} " + " ".join(
            f"{a}={m.get(a, float('nan')):+.4f}/{beklenen[a]:+.4f}" for a in ("Vmax", "Vmin", "Vpp", "Vort", "Vac")))
        return en

    # ── 1+2. ASCII yolu ─────────────────────────────────────────────
    b, _ = seri_yakala(k, 10)
    ascii_en = float("inf")
    f_ascii = None
    if b and b["tam"] and b["olcum"]:
        m = m_coz(b["olcum"])
        f_ascii = m.get("f")
        ascii_en = karsilastir("ASCII", m, eksenden_olcum(b["ornek"], ct, b["ofset"]))
    ok("[!] ASCII: olcum satirinin VOLT degerleri eksenle ayni",
       ascii_en <= tol_v,
       f"en buyuk fark {ascii_en:.4f} V (sinir {tol_v} V) — B43 oncesi ~7 V, Vpp %10 dusuk")

    # ── 3+4. ikili yol ──────────────────────────────────────────────
    k.yaz("tB")
    m_satir = None
    m_once = False
    son_ = time.monotonic() + 10
    onay = False
    while time.monotonic() < son_:
        s = k.satir_oku(0.1)
        if not s:
            continue
        if s.startswith("M "):
            m_satir = s
        if s.startswith("* skop yakalandi (ikili)"):
            onay = True
            m_once = m_satir is not None
            break
        if s.startswith("! "):
            break
    ok("[!] Ikili: olcum satiri ONAY satirindan once geliyor", onay and m_once,
       "onay yok" if not onay else ("M satiri var" if m_once else "M satiri YOK — WiFi'de olcum gosterilemez"))
    ikili_en = float("inf")
    f_ikili = None
    try:
        with urllib.request.urlopen(f"http://{http_host}/skop.bin", timeout=8) as y:
            g = y.read()
        adet = struct.unpack_from("<H", g, 4)[0]
        ofset = struct.unpack_from("<f", g, 16)[0]
        kodlar = list(struct.unpack_from(f"<{adet}H", g, 32))
        if m_satir:
            m = m_coz(m_satir)
            f_ikili = m.get("f")
            ikili_en = karsilastir("ikili", m, eksenden_olcum(kodlar, ct, ofset))
    except OSError as e:
        print(f"  /skop.bin cekilemedi: {e}")
    ok("[!] Ikili: olcum satiri /skop.bin'deki dalganin degerleri",
       ikili_en <= tol_v, f"en buyuk fark {ikili_en:.4f} V")
    f_tamam = all(f is not None and abs(f - 1000.0) <= 10.0 for f in (f_ascii, f_ikili))
    ok("Frekans CAL 1 kHz'ye +-%1 (iki yolda)", f_tamam, f"ASCII {f_ascii} · ikili {f_ikili} Hz")

    for c in ("tm0", "tp25", "th40", "tl2048", "tb5"):
        komut(c)
    komut("X0", 0.5)
    return 1 if kaldi else 0


def skop_tetik_onayi(k, tekrar=20) -> int:
    """B47 — tetik onayi (gurultu reddi) IGNEYI GERCEKTEN eliyor mu.

    Ayni firmware, iki kip, ayni igne kaynagi: `tK8,9` (I2C tiklatmasi,
    B44'te her yakalamada 1-5 igne/1000). OTO kip, CAL kapali, esik =
    dugumun ortalamasi + 30 kod (RC dugumu yavas bosaliyor, her turda
    yeniden ortalanir), histerezis 0. Gercek bir gecis YOK; tetik yalniz
    igneden gelebilir. `tetiklendi` sayiliyor:
        onay=1 (tek ornek)   -> igneler tetikler  (beklenen > 0)
        onay=2 (iki ornek)   -> hicbiri tetiklemez (beklenen 0)
    Ikisi de 0 cikarsa deney BOS (igne yok) — bu ayrica sinaniyor. Ayrica
    gercek bir sinyalde (CAL 1 kHz) onay=2'nin tetiklemeye devam ettigi ve
    tetik konumunun ILK gecis ornegi kaldigi (B42) dogrulaniyor.
    """
    def komut(kom, sn=0.3):
        k.yaz(kom)
        time.sleep(sn)

    def kuplaj_yakala(pinler, sn=12):
        c = SkopCozucu()
        k.yaz("tK" + pinler)
        blok = None
        red = None
        son_ = time.monotonic() + sn
        while time.monotonic() < son_:
            s = k.satir_oku(0.1)
            if not s:
                continue
            if s.startswith("! tetiklenemedi"):
                red = "tetiklenemedi"
            elif s.startswith("! "):
                red = s
            # sira: `* kuplaj:` (loop, yakalama bitince) -> S2 ... E (dokum turlari)
            if s.startswith("* kuplaj:") and red:
                break
            b = c.besle(s)
            if b:
                blok = b
                break
        return blok, red

    komut("X0", 1.0)
    for c_ in ("tm0", "te0", "th0", "tp25", "tb3"):
        komut(c_)
    print(f"  {'onay':>4} {'yakalama':>8} {'tetiklendi':>10} {'esik-ort':>9}  aciklama")
    sonuc = {}
    for onay in (1, 2):
        komut(f"tn{onay}")
        komut("tl4095")                      # ilk yakalama serbest kosu
        tetik = 0
        adet = 0
        ort = None
        for _ in range(tekrar):
            if ort is not None:
                komut(f"tl{int(ort + 30)}", 0.2)
            b, _ = kuplaj_yakala("8,9")
            if b is None or not b["ornek"]:
                continue
            adet += 1
            if ort is not None and b["tetiklendi"]:
                tetik += 1
            ort = sum(b["ornek"]) / len(b["ornek"])
        sonuc[onay] = (tetik, adet)
        print(f"  {onay:4d} {adet:8d} {tetik:10d} {'+30':>9}  "
              + ("tek ornek — igne tetikler" if onay == 1 else "iki ornek — igne tetiklemez"))
    ok("[!] Deney BOS DEGIL: tek-ornek kipte igneler tetikliyor",
       sonuc[1][1] >= 10 and sonuc[1][0] > 0,
       f"{sonuc[1][0]}/{sonuc[1][1]} — 0 ise igne kaynagi (tK8,9) calismiyor, sonuc anlamsiz")
    ok("[!] Gurultu reddi (onay=2) igneleri ELIYOR: 0 sahte tetik",
       sonuc[2][1] >= 10 and sonuc[2][0] == 0,
       f"{sonuc[2][0]}/{sonuc[2][1]}")

    # ── gercek sinyal: onay=2 tetiklemeye devam ediyor, konum degismiyor ──
    komut("X1000", 0.5)
    komut("x500", 1.0)
    komut("tm1")                             # NORMAL: tetiksiz sonuc yok
    b, _ = seri_yakala(k)
    esik = (min(b["ornek"]) + max(b["ornek"])) // 2 if b and b["ornek"] else 1916
    komut(f"tl{esik}")
    komut("th14")
    konum = []
    for onay in (2, 1):
        komut(f"tn{onay}")
        for _ in range(5):
            b, _ = seri_yakala(k, 10)
            if not b or not b["tam"] or not b["tetiklendi"]:
                konum.append((onay, "YOK"))
                continue
            v, i = b["ornek"], b["tetik_idx"]
            gecis = 0 < i < len(v) and v[i - 1] < esik <= v[i]
            konum.append((onay, i if gecis else f"{i}x"))
    beklenen = 833 * 25 // 100
    print(f"  gercek sinyal (CAL 1 kHz, NORMAL, esik {esik}): beklenen idx {beklenen} → "
          + " ".join(f"o{o}:{i}" for o, i in konum))
    ok("[!] onay=2 GERCEK sinyalde tetikliyor ve tetik ILK gecis orneginde (B42 korunuyor)",
       all(i == beklenen for o, i in konum if o == 2) and any(o == 2 for o, _ in konum),
       "onay ornegini tetik sayarsa konum 1 kayar; ya da hic tetiklemez")
    ok("onay=1 de ayni konumda", all(i == beklenen for o, i in konum if o == 1))
    for c_ in ("tn2", "tm0", "th40", "tl2048", "tb5"):
        komut(c_)
    komut("X0", 0.5)
    return 1 if kaldi else 0


def skop_blokaj(k, zaman_tabanlari=(3, 5, 7, 9, 10)) -> int:
    """B40/B41 — skop yakalamasi olcumu nasil etkiliyor.

    B40 oncesi (2026-09-13) `t` olcum dongusunu tb3'te 667 ms, tb9'da
    4437 ms blokluyordu. B40b yakalamayi ayri goreve alip bunu 1-5 ms'ye
    indirdi AMA ADS'yi eszamanli calistirdi ve I2C kenarlari ADC'ye
    tek-ornek hata soktu (kullanicinin ekraninda igneler + sahte tetik).
    B41: yakalama surerken ADS SUSUYOR ve bu SAYILIYOR.

    Sinanan uc sey:
      1. ORNEK BUTUNLUGU — surulu dugumde tek-ornek hatasi SIFIR. B40b'yi
         yakalayamayan eksik iddia tam olarak buydu.
      2. Komut dongusu yakalama sirasinda cevap veriyor (<= 20 ms).
      3. ADS susmasi GIZLENMIYOR: `ads_duraklama_ms` yakalama suresi kadar
         artiyor; >1 s araliklar enerji sayacinda kayip olarak gorunuyor.
    """
    import statistics as st

    def k_oku(sn=20.0):
        son_ = time.monotonic() + sn
        while time.monotonic() < son_:
            s = k.satir_oku(0.2)
            if s and K_DESEN.match(s):
                return tuple(int(x) for x in K_DESEN.match(s).groups())
        return None

    def komut(kom, sn=0.5):
        k.yaz(kom)
        time.sleep(sn)

    def durum():
        """`?` ciktisindan K (kayip, azami, uzun) ve C (ads_duraklama_ms).
        Kartin kendiliginden bastigi K satirini beklemek YANILTIYORDU: o
        satir yalnizca degisince basiliyor ve yakalama okuyucusu onu
        yutabiliyordu (tb10 satirinda -1 goruldu)."""
        k.yaz("?")
        kk, cc = None, None
        son_ = time.monotonic() + 4
        while time.monotonic() < son_ and (kk is None or cc is None):
            s = k.satir_oku(0.2)
            if not s:
                continue
            if K_DESEN.match(s):
                kk = tuple(int(x) for x in K_DESEN.match(s).groups())
            elif s.startswith("C ") and "ads_duraklama_ms=" in s:
                cc = int(s.split("ads_duraklama_ms=")[1].split()[0])
        return kk, cc

    def yakala(sn=30):
        return seri_yakala(k, sn)

    def hata_say(v, esik=60):
        return sum(1 for i in range(2, len(v) - 2)
                   if abs(v[i] - st.median(v[i - 2:i] + v[i + 1:i + 3])) > esik)

    # ── 1. ORNEK BUTUNLUGU ──────────────────────────────────────────
    # 🔴 B44 duzeltmesi: bu sinama CAL 20 kHz ile kosuyordu ve B44 CAL
    #    PWM'inin KENDI kenarinin da tek-ornek hata soktugunu buldu (kenar
    #    ornekleme anina denk gelince ~60 kod, 25 ornekte bir, faz kaydigi
    #    icin ara sira). Uc temiz kosudan sonra dorduncusu 11/3721 verdi —
    #    I2C ile ilgisi yok. Artik CAL KAPALI: dugum kondansatorlerde
    #    yavas bosaliyor (-25 kod/s, gurultu 2.2 kod), >60 kodluk bir
    #    sicrama yine ayirt edilir. Kalan taban ~0.06/1000 (B44 kontrol
    #    kosulari, kaynagi bilinmiyor) -> olcut 1 hata/3721'e kadar (0.27/1000);
    #    B40b'nin kusuru 3-9/1000 idi, 10x pay var.
    komut("X0", 1.0)
    for c in ("tm0", "tl0", "th0"):
        komut(c, 0.3)
    hata = ornek = 0
    for tb, tekrar in ((3, 3), (10, 1)):
        komut(f"tb{tb}", 0.4)
        for _ in range(tekrar):
            b, _ = yakala()
            if b:
                hata += hata_say(b["ornek"])
                ornek += len(b["ornek"])
    ok("[!] TEK-ORNEK HATASI yok (> 60 kod, CAL kapali, <= 1/3721)",
       ornek > 0 and hata <= 1,
       f"{hata} hata / {ornek} ornek ({1000.0 * hata / max(ornek, 1):.2f}/1000) — "
       f"B40b'de ADS eszamanliyken 3-9/1000 idi")

    # ── 2+3. donguler ve susma muhasebesi (en kotu: tetik yok) ──────
    for c in ("tm0", "tl4095", "th4"):
        komut(c, 0.3)
    print(f"  {'taban':>5} {'yakalama':>9} {'dongu azami':>12} {'atlanan':>8} "
          f"{'ADS susma':>10} | yakalama")
    en_kotu = 0
    tam_hepsi = True
    muhasebe_tamam = True
    tb10_sure = None
    for tb in zaman_tabanlari:
        komut(f"tb{tb}", 0.4)
        k.yaz("K")                                   # sayaclari sifirla
        time.sleep(0.5)
        _, d0 = durum()
        b, sure = yakala()
        time.sleep(0.3)
        kk, d1 = durum()
        azami = kk[1] if kk else -1
        atlanan = kk[0] if kk else -1
        susma = (d1 - d0) if (d0 is not None and d1 is not None) else -1
        en_kotu = max(en_kotu, azami)
        tam_hepsi = tam_hepsi and bool(b and b["tam"])
        if sure and susma >= 0 and susma < 0.8 * sure * 1000:
            muhasebe_tamam = False
        if tb == 10:
            tb10_sure = sure
        print(f"  tb{tb:<3} {sure if sure else -1:8.2f}s {azami:10d} us {atlanan:6d} ms "
              f"{susma:8d} ms | "
              + (f"{len(b['ornek'])}/{b['adet_bildirilen']} tam" if b else "BLOK YOK"))
    komut("tl2048", 0.3)
    komut("tb5", 0.3)
    ok("[!] Yakalama sirasinda KOMUT dongusu cevap veriyor (<= 20 ms)",
       0 < en_kotu <= 20000,
       f"en uzun tur {en_kotu} us — B40 oncesi tb9'da 4437 ms")
    ok("[!] ADS susmasi GIZLENMIYOR (ads_duraklama_ms ~ yakalama suresi)",
       muhasebe_tamam, "susma sayilmasaydi enerji/pil araligi sessizce kayardi")
    ok("Butun yakalamalar TAM geldi", tam_hepsi,
       "hizli ama bozuk yakalama basari degil")
    ok("OTO kipte tetik yokken 200 ms/bol yakalamasi <= 3.0 s (onceden 4.08)",
       tb10_sure is not None and tb10_sure <= 3.0,
       f"{tb10_sure:.2f} s — pencere 2 s, taban 2.7 s" if tb10_sure else "olculemedi")
    return 1 if kaldi else 0


K_DESEN = re.compile(r"^K (\d+) (\d+) (\d+)")


def main() -> int:
    arg = sys.argv[1:]

    def secenek(ad, varsayilan):
        return arg[arg.index(ad) + 1] if ad in arg else varsayilan

    port = secenek("--port", None)
    sure = float(secenek("--sure", "60"))
    tekrar = int(secenek("--tekrar", "3"))

    k = kart_baglanti.SeriKart(port)
    k.ac()
    time.sleep(1.0)
    http_host = secenek("--http", "olcum.local")
    if "--tetik" in arg or "--olcum" in arg or "--onay" in arg:
        kod = 0
        if "--tetik" in arg:
            print("SKOP TETIK KONUMU (B42)")
            kod = skop_tetik_konumu(k) or kod
        if "--olcum" in arg:
            print("SKOP OLCUM SATIRI — KALIBRASYON + WiFi (B43)")
            kod = skop_olcum_kalibre(k, http_host) or kod
        if "--onay" in arg:
            print("SKOP TETIK ONAYI — GURULTU REDDI (B47)")
            kod = skop_tetik_onayi(k) or kod
        k.kapat()
        print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
        return kod
    if "--skop" in arg:
        print("SKOP YAKALAMASI SIRASINDA BLOKAJ (B40)")
        kod = skop_blokaj(k)
        print("\nSKOP TETIK KONUMU (B42)")
        kod = skop_tetik_konumu(k) or kod
        print("\nSKOP OLCUM SATIRI — KALIBRASYON + WiFi (B43)")
        kod = skop_olcum_kalibre(k, http_host) or kod
        print("\nSKOP TETIK ONAYI — GURULTU REDDI (B47)")
        kod = skop_tetik_onayi(k) or kod
        k.kapat()
        print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
        return kod
    # --sifirla: bringup kosucusunun yaptigi gibi acilistan olc. Acilis
    # gecisi (WiFi, mDNS, NVS) ile kararli hal FARKLI davranabilir.
    if "--sifirla" in arg:
        print("kart sifirlaniyor (acilis gecisi olculecek)...")
        k.sifirla()
        time.sleep(4.0)                              # afis + WiFi

    def k_oku(bekle_sn: float = 6.0):
        """Kartin kendiliginden bastigi `K` satirini bekle (komutsuz)."""
        son = time.monotonic() + bekle_sn
        while time.monotonic() < son:
            s = k.satir_oku(0.3)
            if s and K_DESEN.match(s):
                m = K_DESEN.match(s)
                return tuple(int(x) for x in m.groups())
        return None

    print(f"kart {k.k.ad if hasattr(k, 'k') else port} · {tekrar} x {sure:.0f} s")
    print(f"  {'pencere':>7} {'azami us':>9} {'>20ms tur':>9} {'atlanan ms':>10}")
    sonuclar = []
    for i in range(tekrar):
        k.yaz("K")                                   # sifirla (eski degeri basar)
        time.sleep(0.5)
        # Sifirlama sonrasi ilk K satirini at (icinde sifirlama ani var)
        k_oku(6.0)
        t0 = time.monotonic()
        son = None
        while time.monotonic() - t0 < sure:
            r = k_oku(6.0)
            if r:
                son = r
        if son is None:
            print(f"  {i+1:7d}  (K satiri gelmedi)")
            continue
        atlanan, azami, uzun = son
        sonuclar.append(son)
        print(f"  {i+1:7d} {azami:9d} {uzun:9d} {atlanan:10d}")
    k.kapat()

    if sonuclar:
        en = max(s[1] for s in sonuclar)
        toplam_uzun = sum(s[2] for s in sonuclar)
        print(f"\n  en uzun tur {en} us · toplam >20ms tur {toplam_uzun} "
              f"/ {tekrar * sure:.0f} s · atlanan {sum(s[0] for s in sonuclar)} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
