# -*- coding: utf-8 -*-
"""BOSTA BLOKAJ OLCUMU — `K` sayacini sifirla, bekle, oku. Tekrarli.

    python tezgah_blokaj.py                 # 3 x 60 s
    python tezgah_blokaj.py --sure 45 --tekrar 4 --port COM6
    python tezgah_blokaj.py --skop          # B40: yakalama sirasinda blokaj

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


def skop_blokaj(k, zaman_tabanlari=(3, 5, 7, 9)) -> int:
    """B40 — skop yakalamasi olcum dongusunu blokluyor mu.

    Kartta B40 oncesi olculen (2026-09-13), `t` sirasinda en uzun tur:
        tb3 667 ms · tb5 897 ms · tb7 1524 ms · tb9 4437 ms
    tb7 ve ustunde enerji sayaci o araligi ATIYORDU. En kotu durum icin
    tetik ULASILAMAZ yapiliyor (tl4095, OTO): yakalama zaman asimini
    bekler, tb9'da 4 s. Blokaj bu surenin hicbir parcasini gormemeli.
    Yakalamanin kendisi de TAM gelmeli — hizli ama bozuk yakalama basari
    degildir.
    """
    def k_oku(sn=20.0):
        son = time.monotonic() + sn
        while time.monotonic() < son:
            s = k.satir_oku(0.2)
            if s and K_DESEN.match(s):
                return tuple(int(x) for x in K_DESEN.match(s).groups())
        return None

    def komut(kom, sn=0.5):
        k.yaz(kom)
        time.sleep(sn)

    for c in ("tm0", "tl4095", "th4"):
        komut(c, 0.3)
    print(f"  {'taban':>5} {'dongu azami':>12} {'atlanan':>8} | yakalama")
    en_kotu = 0
    atlanan_top = 0
    tam_hepsi = True
    for tb in zaman_tabanlari:
        komut(f"tb{tb}", 0.4)
        k.yaz("K")
        time.sleep(0.3)
        k_oku()                                   # sifirlama anini at
        once = k_oku()
        c = SkopCozucu()
        k.yaz("t")
        blok = None
        son = time.monotonic() + 30
        while time.monotonic() < son and blok is None:
            s = k.satir_oku(0.2)
            if s is None:
                continue
            if s.startswith("! "):
                break
            blok = c.besle(s)
        s1, s2 = k_oku(), k_oku()
        azami = max(x[1] for x in (s1, s2) if x) if (s1 or s2) else -1
        atlanan = max(x[0] for x in (s1, s2) if x) if (s1 or s2) else -1
        en_kotu = max(en_kotu, azami)
        atlanan_top += max(atlanan, 0)
        tam = bool(blok and blok["tam"])
        tam_hepsi = tam_hepsi and tam
        print(f"  tb{tb:<3} {azami:10d} us {atlanan:6d} ms | "
              + (f"{len(blok['ornek'])}/{blok['adet_bildirilen']} tam, "
                 f"arada {blok['atlanan']} satir" if blok else "BLOK YOK"))
    komut("tl2048", 0.3)
    komut("tb5", 0.3)
    ok("[!] Yakalama sirasinda olcum dongusu <= 20 ms (en kotu: tetik yok)",
       0 < en_kotu <= 20000, f"en uzun tur {en_kotu} us — B40 oncesi tb9'da 4437 ms")
    ok("[!] Yakalama sirasinda enerji penceresi ATLANMIYOR",
       atlanan_top == 0, f"{atlanan_top} ms — B40 oncesi tb9'da 4439 ms")
    ok("Butun yakalamalar TAM geldi", tam_hepsi,
       "hizli ama bozuk yakalama basari degil")
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
