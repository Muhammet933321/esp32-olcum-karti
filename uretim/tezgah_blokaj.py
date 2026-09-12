# -*- coding: utf-8 -*-
"""BOSTA BLOKAJ OLCUMU — `K` sayacini sifirla, bekle, oku. Tekrarli.

    python tezgah_blokaj.py                 # 3 x 60 s
    python tezgah_blokaj.py --sure 45 --tekrar 4 --port COM6

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
