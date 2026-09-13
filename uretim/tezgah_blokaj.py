# -*- coding: utf-8 -*-
"""BOSTA BLOKAJ OLCUMU — `K` sayacini sifirla, bekle, oku. Tekrarli.

    python tezgah_blokaj.py                 # 3 x 60 s
    python tezgah_blokaj.py --sure 45 --tekrar 4 --port COM6
    python tezgah_blokaj.py --skop          # B40/B41: butunluk + blokaj + susma

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

    def hata_say(v, esik=60):
        return sum(1 for i in range(2, len(v) - 2)
                   if abs(v[i] - st.median(v[i - 2:i] + v[i + 1:i + 3])) > esik)

    # ── 1. ORNEK BUTUNLUGU (surulu dugum) ───────────────────────────
    komut("X20000", 0.5)
    komut("x500", 1.0)
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
    ok("[!] Surulu dugumde TEK-ORNEK HATASI YOK (> 60 kod)",
       ornek > 0 and hata == 0,
       f"{hata} hata / {ornek} ornek — B40b'de ADS eszamanliyken 3-9/1000 idi")
    komut("X0", 0.5)

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
    if "--skop" in arg:
        print("SKOP YAKALAMASI SIRASINDA BLOKAJ (B40)")
        kod = skop_blokaj(k)
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
