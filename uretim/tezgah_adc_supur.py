# -*- coding: utf-8 -*-
"""ADC DOGRUSALLIK SUPURMESI — gercek kartta, CAL (PWM+RC) kaynagiyla.

    python tezgah_adc_supur.py                     # GPIO4 + GPIO5, 21 nokta
    python tezgah_adc_supur.py --adim 10           # 101 nokta (B34 gibi)
    python tezgah_adc_supur.py --port COM6 --csv olcum-adc-supurme.csv

🔴 NEDEN BU BETIK VAR: B34'un 101 noktali supurmesi ELLE, gecici bir
   betikle yapildi ve o betik KAYDEDILMEDI — yani olcum tekrarlanabilir
   degildi. Bu projede "tekrarlanamayan olcum bir anekdottur".

IKI OKUMA YOLU, AYNI PIN:
   * skop yakalamasi (`t`)  -> GPIO4'un ham kodu, N ornegin ortalamasi
   * `wR`                   -> GPIO4 VE GPIO5'in ham kodu (300'er ornek)

   GPIO4'u iki yoldan okumak BAGIMSIZ bir tutarlilik denetimi: ayni pin,
   iki farkli surekli-ADC yapilandirmasi (tek kanal 20 kSa/s vs iki
   kanal 41.7 kSa/s). Ayrisirlarsa biri yanlistir ve GPIO5 icin `wR`ye
   guvenilemez. Uyusurlarsa `wR` GPIO5 icin gecerli bir arac.

   GPIO5 (hizli AKIM kanali, ADC1_CH4) bugune kadar HIC karakterize
   edilmedi ve guc faktorunun BASKA KAYNAGI YOK.

DUZENEK: GPIO10 -> 10K -> 100nF -> 10K -> 100nF -> GPIO4 (+ GPIO5 ayni
dugume). PWM 20 kHz, 10 bit gorev. Gorev orani TAM BILINEN bir sayi;
olcum kendi varsayimina degil bagimsiz bir sayiya dayaniyor.

⚠ GPIO5'e tel TAKILI DEGILSE bostaki pin okunur: yayilim ~2400 kod.
  Betik bunu YAKALAR ve GPIO5 sutununu "BOSTA" diye isaretler —
  bos pinin egrisini "olctum" sanmak, olcmemekten kotu.
"""
from __future__ import annotations

import csv
import statistics
import sys
import time
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
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


class Kart:
    """Seri kart + satir toplayici. `D`/`K` satirlarini eliyor."""

    def __init__(self, port):
        self.k = kart_baglanti.SeriKart(port)
        self.k.ac()

    def kapat(self):
        self.k.kapat()

    def yaz(self, komut):
        self.k.yaz(komut)

    def bekle(self, onek: str, sn: float = 4.0) -> str | None:
        son = time.monotonic() + sn
        while time.monotonic() < son:
            s = self.k.satir_oku(0.2)
            if s is None:
                continue
            if s.startswith(onek):
                return s
        return None

    def skop_ortalama(self, sn: float = 8.0):
        """`t` yolla, `S2 … E` blogunu topla, ornek ortalamasini dondur.

        ⚠ AYNI COZUCU: kopru ve arsivin kullandigi `SkopCozucu`. Burada
          ayri bir ayristirici yazilsaydi ucuncu bir temsil dogardi.
        """
        c = SkopCozucu()
        self.k.yaz("t")
        son = time.monotonic() + sn
        while time.monotonic() < son:
            s = self.k.satir_oku(0.2)
            if s is None:
                continue
            if s.startswith("! tetiklenemedi"):
                return None
            b = c.besle(s)
            if b is not None:
                if not b["tam"] or not b["ornek"]:
                    return None
                return (statistics.fmean(b["ornek"]),
                        statistics.pstdev(b["ornek"]), len(b["ornek"]))
        return None

    def wr(self, sn: float = 4.0):
        """`wR` -> {v_ort, v_min, v_max, i_ort, i_min, i_max} ya da None."""
        self.k.yaz("wR")
        s = self.bekle("WR ", sn)
        if not s:
            return None
        d = {}
        for alan in s[3:].split():
            ad, _, deger = alan.partition("=")
            try:
                d[ad] = float(deger)
            except ValueError:
                pass
        return d if "v_ort" in d and "i_ort" in d else None

    def kalibre_mv(self, kod: int) -> int | None:
        self.k.yaz(f"c{kod}")
        s = self.bekle("c ham=", 3.0)
        if not s:
            return None
        for alan in s.split():
            if alan.startswith("mv="):
                try:
                    return int(alan[3:])
                except ValueError:
                    return None
        return None


def main() -> int:
    arg = sys.argv[1:]

    def secenek(ad, varsayilan=None):
        return arg[arg.index(ad) + 1] if ad in arg else varsayilan

    port = secenek("--port")
    adim = int(secenek("--adim", "50"))            # promil adimi
    csv_yolu = secenek("--csv")

    print("=" * 78)
    print("  ADC DOGRUSALLIK SUPURMESI — GPIO4 (skop + wR) ve GPIO5 (wR)")
    print("=" * 78)

    try:
        kart = Kart(port)
    except RuntimeError as e:
        print(f"Karta baglanilamadi: {e}")
        return 1
    print(f"     kart: {kart.k.ad} · adim {adim} promil "
          f"({1000 // adim + 1} nokta)\n")

    # CAL: 20 kHz, 10 bit (B34 ile ayni)
    kart.yaz("X20000")
    s = kart.bekle("X cal_hz=", 3.0) or ""
    print(f"     CAL: {s.strip()[:80]}")
    # 🔴 Gorev cozunurlugu 10 bit OLMALI: B33'te 50 kHz'in 10 bitle
    #    uretilemedigi (9 bit) gorulmustu. Cozunurluk dusukse gorev orani
    #    "tam bilinen" olmaktan cikar ve olcumun dayanagi zayiflar.
    coz = None
    for alan in s.split():
        if alan.startswith("cozunurluk="):
            try:
                coz = int(alan.split("=")[1])
            except ValueError:
                pass
    ok("CAL gorev cozunurlugu 10 bit (gorev orani tam bilinen)",
       coz == 10, f"cozunurluk={coz} · {s.strip()[:60]}")
    kart.yaz("tb3")                                  # 833 ornek, B34 gibi
    time.sleep(0.4)

    satirlar = []
    print(f"\n  {'gorev':>5} {'skop ort':>9} {'skop std':>8} "
          f"{'wR v_ort':>9} {'fark':>6} | {'wR i_ort':>9} {'i yayilim':>9}")
    print("  " + "-" * 72)
    en_buyuk_fark = 0.0
    gpio5_bosta_sayisi = 0
    for gorev in range(0, 1001, adim):
        kart.yaz(f"x{gorev}")
        time.sleep(0.25)                             # RC + PWM oturma
        sk = kart.skop_ortalama()
        w = kart.wr()
        if sk is None or w is None:
            print(f"  {gorev:5d}  {'(okunamadi)':>30}")
            continue
        sk_ort, sk_std, sk_n = sk
        fark = w["v_ort"] - sk_ort
        en_buyuk_fark = max(en_buyuk_fark, abs(fark))
        i_yay = w["i_max"] - w["i_min"]
        # Bos pin: yayilim tam olcegin %10'unu asiyorsa DC kaynak degil.
        bosta = i_yay > 4096 * 0.10
        if bosta:
            gpio5_bosta_sayisi += 1
        kal_v = kart.kalibre_mv(int(round(sk_ort)))
        kal_i = kart.kalibre_mv(int(round(w["i_ort"]))) if not bosta else None
        print(f"  {gorev:5d} {sk_ort:9.2f} {sk_std:8.2f} {w['v_ort']:9.2f} "
              f"{fark:+6.2f} | {w['i_ort']:9.2f} {i_yay:9.0f}"
              + ("  BOSTA" if bosta else ""))
        satirlar.append({
            "gorev_promil": gorev,
            "gpio4_skop_ort": f"{sk_ort:.2f}", "gpio4_skop_std": f"{sk_std:.2f}",
            "gpio4_skop_n": sk_n,
            "gpio4_wr_ort": f"{w['v_ort']:.2f}",
            "gpio4_wr_min": int(w["v_min"]), "gpio4_wr_max": int(w["v_max"]),
            "gpio4_kalibre_mv": kal_v if kal_v is not None else "",
            "gpio5_wr_ort": f"{w['i_ort']:.2f}",
            "gpio5_wr_min": int(w["i_min"]), "gpio5_wr_max": int(w["i_max"]),
            "gpio5_kalibre_mv": kal_i if kal_i is not None else "",
            "gpio5_durum": "BOSTA" if bosta else "surulu",
        })

    kart.yaz("X0")
    time.sleep(0.2)
    kart.kapat()

    print()
    n = len(satirlar)
    ok("Supurme tamamlandi", n >= 3, f"{n} nokta")

    # ── 1. Iki yol AYNI pinde UYUSUYOR mu ────────────────────────────
    # skop yolu: tek kanal, 20 kSa/s; wR yolu: iki kanal, 41.7 kSa/s
    # toplam. Ayni ham kod cikmali (birkac kodluk gurultu payi ile).
    ok("[!] GPIO4: skop yolu ile `wR` yolu UYUSUYOR (<= 8 kod)",
       en_buyuk_fark <= 8.0,
       f"en buyuk fark {en_buyuk_fark:.2f} kod — ayrisirlarsa biri "
       f"yanlis ve GPIO5 icin `wR`ye guvenilemez")

    # ── 2. GPIO5 gercekten surulu mu ─────────────────────────────────
    if gpio5_bosta_sayisi == n:
        print("\n  ⚠ GPIO5 HER noktada BOSTA gorundu (yayilim > %10):")
        print("    tel takili degil. GPIO5 sutunu bir OLCUM DEGIL.")
        ok("GPIO5 surulu (tel takili)", False,
           f"{gpio5_bosta_sayisi}/{n} noktada bosta")
    else:
        ok("GPIO5 surulu (tel takili)", gpio5_bosta_sayisi == 0,
           f"{gpio5_bosta_sayisi}/{n} noktada bosta")
        # GPIO4 ile GPIO5 ayni dugumu okuyor — ayni ADC birimi (ADC1),
        # farkli kanal. Kanaldan kanala fark KANAL ofseti/kazanci demek.
        if gpio5_bosta_sayisi == 0:
            farklar = [float(r["gpio5_wr_ort"]) - float(r["gpio4_wr_ort"])
                       for r in satirlar]
            ok("GPIO5 ile GPIO4 ayni dugumde birkac kod icinde",
               max(abs(f) for f in farklar) <= 12.0,
               f"GPIO5-GPIO4: en kucuk {min(farklar):+.1f}, "
               f"en buyuk {max(farklar):+.1f} kod")

    # ── 3. Dogrusallik: en kucuk kareler dogrusundan sapma ───────────
    def inl(anahtar, etiket):
        pts = [(r["gorev_promil"], float(r[anahtar])) for r in satirlar
               if 50 <= r["gorev_promil"] <= 850]          # B34 bandi
        if len(pts) < 3:
            return
        mx = statistics.fmean(p[0] for p in pts)
        my = statistics.fmean(p[1] for p in pts)
        eg = (sum((x - mx) * (y - my) for x, y in pts)
              / sum((x - mx) ** 2 for x, _ in pts))
        ke = my - eg * mx
        art = [y - (eg * x + ke) for x, y in pts]
        enb = max(art, key=abs)
        rms = (sum(a * a for a in art) / len(art)) ** 0.5
        print(f"     {etiket}: %5-%85 bandinda dogrudan sapma "
              f"en buyuk {enb:+.1f} kod, rms {rms:.1f} kod "
              f"(B34 GPIO4: +-75.6 / rms ~18)")
        return enb, rms

    print()
    inl("gpio4_skop_ort", "GPIO4")
    if gpio5_bosta_sayisi == 0:
        inl("gpio5_wr_ort", "GPIO5")

    if csv_yolu:
        yol = Path(csv_yolu)
        with open(yol, "w", encoding="utf-8", newline="") as f:
            f.write("# ADC dogrusallik supurmesi — "
                    f"{time.strftime('%Y-%m-%d')}, kartta olculdu\n")
            f.write("# Kaynak: CAL (GPIO10) PWM 20 kHz, 10 bit gorev + "
                    "2 kademe RC (10K/100nF x2)\n")
            f.write("# GPIO4: skop yakalamasi (tb3, 833 ornek) VE wR "
                    "(300 ornek); GPIO5: wR (300 ornek)\n")
            f.write("# kalibre_mv: Espressif eFuse egri semasi "
                    "(adc_cali_raw_to_voltage)\n")
            f.write("# Uretici: uretim/tezgah_adc_supur.py\n")
            y = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
            y.writeheader()
            y.writerows(satirlar)
        print(f"\n     CSV: {yol}")

    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
