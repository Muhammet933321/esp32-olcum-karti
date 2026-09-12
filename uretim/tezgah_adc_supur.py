# -*- coding: utf-8 -*-
"""ADC DOGRUSALLIK SUPURMESI — gercek kartta, CAL (PWM+RC) kaynagiyla.

    python tezgah_adc_supur.py                     # GPIO4 + GPIO5, 21 nokta
    python tezgah_adc_supur.py --adim 10           # 101 nokta (B34 gibi)
    python tezgah_adc_supur.py --port COM6 --csv olcum-adc-supurme.csv
    python tezgah_adc_supur.py --analiz olcum-adc-supurme.csv   # KARTSIZ
    python tezgah_adc_supur.py --ab                # okuma yolu farki A/B

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

⚠ GPIO5'e tel TAKILI DEGILSE bostaki pin okunur. Betik bunu firmware'in
  CEKME SINAMASIYLA (`wB`, B37) yakalar ve sutunu "BOSTA" isaretler —
  bos pinin egrisini "olctum" sanmak, olcmemekten kotu.

🔴 "BOSTA MI" KARARI YAYILIMA DAYANMIYOR. Ilk yazim "yayilim > %10"
   bakiyordu. Kartta gorüldu (2026-09-13): CAL kapaliyken RC dugumunun
   kondansatorleri SARJLI kaliyor, yayilim yalnizca 18 kod — ama
   arkalarinda kaynak yok (GPIO10 giris kipinde). Yayilim olcutu bunu
   "surulu" sayardi; cekme sinamasi %100 kayma ile BOS dedi. Dogrusu o.

⚠ TEZGAH YAN ETKISI: GPIO4 ve GPIO5 AYNI dugume baglanince cekme
  sinamasinda iki dahili direnc PARALEL calisir (~12.5K). 20K'lik RC
  kaynaginda kayma ~%61'e cikar (tek pinle %41-50); ust ucta ADC
  egriligi bunu koda cevirirken buyutur. `cekme_yuzde` sutunu bunu
  gosteriyor. Gercek on uc (op-amp) bu durumu hic yasamaz.
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

    def wb(self, sn: float = 6.0):
        """`wB` -> {v_yuzde, v_bos, i_yuzde, i_bos, esik} ya da None.

        Firmware'in cekme sinamasi (B37). Betigin "bosta mi" karari
        BUNA dayaniyor, yayilima DEGIL — bkz. modul basligi.
        """
        self.k.yaz("wB")
        s = self.bekle("WB ", sn)
        if not s:
            return None
        d = {}
        for alan in s[3:].split():
            ad, _, deger = alan.partition("=")
            try:
                d[ad] = float(deger)
            except ValueError:
                pass
        return d if "i_bos" in d and "v_yuzde" in d else None

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

    # KARTSIZ: kayitli bir supurmeyi yeniden analiz et. Ham veri depoda,
    # analiz ondan URETILIYOR — iddia degisince 5 dk olcum tekrarlanmiyor.
    if "--analiz" in arg:
        yol = secenek("--analiz")
        print("=" * 78)
        print(f"  ADC DOGRUSALLIK — KAYITLI SUPURMENIN ANALIZI: {yol}")
        print("=" * 78)
        analiz(csv_oku(yol))
        print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
        return 1 if kaldi else 0

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

    if "--ab" in arg:
        ab_testi(kart)
        kart.kapat()
        print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
        return 1 if kaldi else 0

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
          f"{'wR v_ort':>9} {'fark':>6} | {'wR i_ort':>9} {'5-4':>6} "
          f"{'cekme%':>6}")
    print("  " + "-" * 72)
    en_buyuk_fark = 0.0
    en_buyuk_cekme = 0.0
    esik_yuzde = 75.0
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
        # Bos pin karari FIRMWARE'IN CEKME SINAMASINDAN (B37) — yayilim
        # sarjli ama kaynaksiz bir dugumu "surulu" sanirdi.
        cek = kart.wb()
        if cek is None:
            print(f"  {gorev:5d}  (wB okunamadi)")
            continue
        bosta = cek["i_bos"] >= 1
        cekme_yuzde = max(cek["v_yuzde"], cek["i_yuzde"])
        en_buyuk_cekme = max(en_buyuk_cekme, cekme_yuzde) if not bosta \
            else en_buyuk_cekme
        esik_yuzde = 100.0 * cek.get("esik", 3072) / 4096.0
        if bosta:
            gpio5_bosta_sayisi += 1
        kal_v = kart.kalibre_mv(int(round(sk_ort)))
        kal_i = kart.kalibre_mv(int(round(w["i_ort"]))) if not bosta else None
        print(f"  {gorev:5d} {sk_ort:9.2f} {sk_std:8.2f} {w['v_ort']:9.2f} "
              f"{fark:+6.2f} | {w['i_ort']:9.2f} "
              f"{w['i_ort'] - w['v_ort']:+6.2f} {cekme_yuzde:6.0f}"
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
            "gpio5_wr_yayilim": int(i_yay),
            "cekme_v_yuzde": f"{cek['v_yuzde']:.0f}",
            "cekme_i_yuzde": f"{cek['i_yuzde']:.0f}",
            "cekme_esik_yuzde": f"{esik_yuzde:.0f}",
        })

    kart.yaz("X0")
    time.sleep(0.2)
    kart.kapat()

    analiz(satirlar)

    if csv_yolu and satirlar:
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
            f.write("# cekme_*: wB bos-pin sinamasi (B37), tam olcegin yuzdesi\n")
            f.write("# Uretici: uretim/tezgah_adc_supur.py "
                    "(analiz: --analiz <bu dosya>)\n")
            y = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
            y.writeheader()
            y.writerows(satirlar)
        print(f"\n     CSV: {yol}")

    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    return 1 if kaldi else 0


# ═══════════════════════════════════════════════════════════════════════
#  ANALIZ — kartsiz, CSV'den de kosuyor
# ═══════════════════════════════════════════════════════════════════════

# B34'un (2026-09-12, GPIO4, skop yolu, GPIO5 BAGLI DEGILKEN) olctugu
# dogrudan sapma. Bu betik o olcumu tekrarliyor; buyuk sapma ya dogrusal-
# sizligin degistigi ya da duzenegin bozuldugu demek.
B34_INL_KOD = 75.6


def _dogru(pts):
    """En kucuk kareler: (egim, kesme, artiklar)."""
    mx = statistics.fmean(p[0] for p in pts)
    my = statistics.fmean(p[1] for p in pts)
    eg = (sum((x - mx) * (y - my) for x, y in pts)
          / sum((x - mx) ** 2 for x, _ in pts))
    ke = my - eg * mx
    return eg, ke, [y - (eg * x + ke) for x, y in pts]


def analiz(satirlar) -> None:
    """Olculen ya da CSV'den okunan satirlar uzerinde butun iddialar.

    Satirlar taze olcumden de (sayilar karisik tipte) CSV'den de (hepsi
    metin) gelebiliyor; her alan burada donusturuluyor.
    """
    print()
    n = len(satirlar)
    ok("Supurme tamamlandi", n >= 3, f"{n} nokta")
    if n < 3:
        return

    def f(r, ad):
        return float(r[ad])

    def gorev(r):
        return int(float(r["gorev_promil"]))

    # %5..%90 bandi: altta sifir kodu, ustte doyum (kod 4095) var.
    bant = [r for r in satirlar if 50 <= gorev(r) <= 900]

    # ── 1. GPIO5 gercekten surulu mu (cekme sinamasina gore) ─────────
    bosta = sum(1 for r in satirlar if r.get("gpio5_durum") == "BOSTA")
    if bosta == n:
        print("  ⚠ GPIO5 HER noktada BOSTA (cekme sinamasi): tel takili")
        print("    degil. GPIO5 sutunu bir OLCUM DEGIL.")
    ok("GPIO5 surulu (tel takili)", bosta == 0, f"{bosta}/{n} noktada bosta")

    # ── 2. GPIO5 ile GPIO4 AYNI YAKALAMADA ───────────────────────────
    # Ayni `wR` yakalamasi, ayni an, ayni dugum, farkli kanal (ADC1_CH3
    # vs CH4). Kip ya da zaman farki YOK; kalan fark kanal ofseti/kazanci.
    if bosta == 0 and bant:
        d = [f(r, "gpio5_wr_ort") - f(r, "gpio4_wr_ort") for r in bant]
        ok("[!] GPIO5 ile GPIO4 ayni yakalamada <= 2 kod (ort ve std)",
           abs(statistics.fmean(d)) <= 2.0 and statistics.pstdev(d) <= 2.0,
           f"GPIO5-GPIO4: ort {statistics.fmean(d):+.2f}, "
           f"std {statistics.pstdev(d):.2f} kod "
           f"(2026-09-13: -0.26 / 0.75)")

    # ── 3. Iki OKUMA YOLU: skop (tek kanal) vs wR (iki kanal) ────────
    # 🔴 ILK YAZIM "en buyuk fark <= 8 kod" istiyordu ve 101 noktada
    #    12.8 kodla KIRMIZI dondu. Esik gevsetilmedi; fark AYRISTIRILDI.
    #    Tekrarli A/B olcumu (`--ab`, 2026-09-13) farkin RASTGELE
    #    OLMADIGINI gosterdi:
    #        gorev   tb3(83 kSa/s)-wR   tb5(20 kSa/s)-wR
    #        %30         +1.1               +3.4
    #        %60         +3.7               +4.5
    #        %90         +4.1               +6.9
    #    Seviyeyle ORANTILI ve ornekleme hizi dustukce BUYUYOR: ADC'nin
    #    ornekleme kondansatorunun dugumden cektigi ortalama akimla
    #    tutarli (~4 pF x V x f). Bu duzenekte kaynak empedansi 20K; gercek
    #    on uc (op-amp ~0, skop bolucusu ~2.6K) bunu en az 8 kat kucultur.
    #    Seviyeyle orantili bir fark KAZANC terimidir — dogrusallik
    #    analizindeki en iyi dogru onu siler (GPIO4/GPIO5/B34 egrilikleri
    #    bu yuzden birebir tutuyor). Iddia iki PARCAYA ayrildi:
    #      (a) kazanc farki kucuk mu      (b) kazanc silinince kalan gurultu mu
    if bant:
        pts = [(f(r, "gpio4_wr_ort"),
                f(r, "gpio4_skop_ort") - f(r, "gpio4_wr_ort")) for r in bant]
        eg, ke, art = _dogru(pts)
        ok("[!] Okuma yollari arasi KAZANC farki < %0.5",
           abs(eg) < 0.005,
           f"skop - wR = {ke:+.2f} + %{eg*100:.3f} x kod "
           f"(2026-09-13: %0.141; 20K kaynakta ornekleme yuku)")
        ok("Kazanc silinince kalan fark GURULTU duzeyinde (std <= 4 kod)",
           statistics.pstdev(art) <= 4.0,
           f"artik std {statistics.pstdev(art):.2f}, en "
           f"{min(art):+.1f}..{max(art):+.1f} kod (wR yalnizca 300 ornek)")

    # ── 4. Bos-pin esiginin SURULU taraftaki payi ────────────────────
    # Bu tezgahta iki pin ayni dugumde: iki dahili cekme paralel — en
    # zorlu durum. Surulu hicbir nokta esigi GECMEMELI; gecerse `w`
    # surulu bir girisi reddeder.
    if bosta == 0 and satirlar and "cekme_i_yuzde" in satirlar[0]:
        cek = [max(f(r, "cekme_v_yuzde"), f(r, "cekme_i_yuzde"))
               for r in satirlar]
        esik = float(satirlar[0].get("cekme_esik_yuzde") or 75.0)
        ok("[!] Surulu dugumde cekme kaymasi bos-pin esiginin ALTINDA",
           max(cek) < esik,
           f"en buyuk %{max(cek):.0f} / esik %{esik:.0f} "
           f"(pay {esik - max(cek):.0f} puan; iki pin tek dugumde)")

    # ── 5. Dogrusallik: gorev oranina (TAM BILINEN) gore sapma ───────
    def inl(anahtar):
        pts = [(gorev(r), f(r, anahtar)) for r in satirlar
               if 50 <= gorev(r) <= 850]                    # B34 bandi
        if len(pts) < 3:
            return None
        _, _, art = _dogru(pts)
        return max(art, key=abs), (sum(a * a for a in art) / len(art)) ** 0.5

    print()
    sonuc = {}
    for anahtar, etiket in (("gpio4_skop_ort", "GPIO4 skop"),
                            ("gpio4_wr_ort", "GPIO4 wR  "),
                            ("gpio5_wr_ort", "GPIO5 wR  ")):
        if anahtar.startswith("gpio5") and bosta:
            continue
        s = inl(anahtar)
        if s:
            sonuc[anahtar] = s
            print(f"     {etiket}: %5-%85 bandinda en buyuk {s[0]:+.1f} kod, "
                  f"rms {s[1]:.1f} kod")
    print(f"     (B34, GPIO4 skop, GPIO5 bagli degilken: +-{B34_INL_KOD} kod)")

    if "gpio4_skop_ort" in sonuc:
        g4 = abs(sonuc["gpio4_skop_ort"][0])
        ok("B34'un GPIO4 dogrusalsizligi TEKRARLANDI (+-%15)",
           abs(g4 - B34_INL_KOD) <= 0.15 * B34_INL_KOD,
           f"{g4:.1f} kod vs B34 {B34_INL_KOD} — B34'un betigi kaydedilmemisti; "
           f"bu, olcumun ILK tekrari")
    if "gpio5_wr_ort" in sonuc and "gpio4_wr_ort" in sonuc:
        r5, r4 = sonuc["gpio5_wr_ort"][1], sonuc["gpio4_wr_ort"][1]
        ok("[!] GPIO5'in egriligi GPIO4'unkiyle ayni (rms +-%15)",
           abs(r5 - r4) <= 0.15 * r4,
           f"rms GPIO5 {r5:.1f} / GPIO4 {r4:.1f} kod — ayniysa GPIO4'e "
           f"uygulanan eFuse duzeltmesi (B36) GPIO5'e de gecerli")


def ab_testi(kart, gorevler=(300, 600, 900), tekrar: int = 5) -> None:
    """Okuma yollari farkinin RASTGELE mi SISTEMATIK mi oldugunu olc.

    Ayni gorev oraninda skop(tb3, 83 kSa/s), skop(tb5, 20 kSa/s) ve wR
    DONUSUMLU okunuyor. Fark ornekleme hizina bagliysa ornekleme yukudur.
    """
    print(f"\n  A/B — {tekrar} tekrar, donusumlu")
    print(f"  {'gorev':>5} {'tb3 83k':>11} {'tb5 20k':>11} {'wR':>11} | "
          f"{'tb3-wR':>7} {'tb5-wR':>7}")
    kart.yaz("X20000")
    kart.bekle("X cal_hz=", 3.0)
    hiz_farki = []
    for g in gorevler:
        kart.yaz(f"x{g}")
        time.sleep(0.6)
        a, b, c = [], [], []
        for _ in range(tekrar):
            kart.yaz("tb3"); time.sleep(0.2)
            r = kart.skop_ortalama()
            if r:
                a.append(r[0])
            kart.yaz("tb5"); time.sleep(0.2)
            r = kart.skop_ortalama()
            if r:
                b.append(r[0])
            w = kart.wr()
            if w:
                c.append(w["v_ort"])
        if not (a and b and c):
            print(f"  {g:5d}  (okunamadi)")
            continue
        ma, mb, mc = statistics.fmean(a), statistics.fmean(b), statistics.fmean(c)
        hiz_farki.append(mb - ma)
        print(f"  {g:5d} {ma:8.2f}±{statistics.pstdev(a):3.1f} "
              f"{mb:8.2f}±{statistics.pstdev(b):3.1f} "
              f"{mc:8.2f}±{statistics.pstdev(c):3.1f} | "
              f"{ma - mc:+7.2f} {mb - mc:+7.2f}")
    kart.yaz("X0")
    kart.yaz("tb3")
    time.sleep(0.3)
    if hiz_farki:
        ok("Okuma yolu farki ORNEKLEME HIZINA bagli (tb5 > tb3)",
           statistics.fmean(hiz_farki) > 0,
           f"ortalama tb5-tb3 {statistics.fmean(hiz_farki):+.2f} kod — "
           f"yavas ornekleme dugumu daha az yukler")


def csv_oku(yol):
    with open(yol, encoding="utf-8") as f:
        return list(csv.DictReader(s for s in f if not s.startswith("#")))


if __name__ == "__main__":
    raise SystemExit(main())
