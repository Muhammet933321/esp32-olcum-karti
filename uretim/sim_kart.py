# -*- coding: utf-8 -*-
"""S9 — KARTIN TAMAMI, uctan uca.

Zincirin her halkasi GERCEK parcadan olusur, hicbiri taklit degil:

  uygulanan gerilim/akim
      -> ngspice          (gercek bolucu + gercek LM358 makromodeli, DC tarama)
      -> ADC              (veri sayfasi denklemi, ornekle-tut RC oturmasi)
      -> GERCEK FIRMWARE  (avr-g++ ile derlenmis .elf, komut komut kosturuluyor)
      -> seri port baytlari
      -> GERCEK ARAYUZ    (arayuz/app.js ayristiricisi, node ile)
      -> ekranda gorunen sayi

Sorulan soru tek: kartin girisine 12.00 V koyarsam ekranda 12.00 V mi yaziyor?

KAPSAM DISI — bu test bunlari KANITLAMAZ:
  * gercek lehim/temas dirençleri, gercek gurultu, gercek sicaklik surukleme
  * TL431'in gercek referans gerilimi (tezgahta olculdu: 2.470 V)
  * direnclerin gercek toleransi (%1 metal film varsayildi)
Bunlar ancak tezgahta multimetre ile dogrulanir; test sonunda o listeyi basar.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import sim_akim                                    # noqa: E402
import sim_bolucu                                  # noqa: E402
import spice                                       # noqa: E402
from avr import elf, mega328                       # noqa: E402
from avr.cekirdek import Cekirdek                  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
ESKIZ = BURASI.parent / "arsiv" / "asama1" / "olcum-karti"
ARDUINO_CLI = BURASI.parents[2] / ".araclar" / "arduino-cli.exe"
CIKTI = BURASI.parent / "arsiv" / "asama1" / "kanit"

AREF_OLCULEN = 2.470       # tezgahta multimetre ile olculdu (2026-09-07)
SONT = 10.0                # 1x 10R takili
KAZANC = sim_akim.KAZANC
THEVENIN = 100e3 * 10e3 / 110e3   # bolucu dugumunun kaynak direnci


class Rapor:
    def __init__(self):
        self.gecti = self.kaldi = 0

    def bilgi(self, s=""):
        print(s)

    def kosul(self, ad, tamam, ek=""):
        if tamam:
            self.gecti += 1
        else:
            self.kaldi += 1
        print(f"  {'[OK]' if tamam else '[!!]'} {ad}" + (f"  {ek}" if ek else ""))
        return tamam

    def yakin(self, ad, alinan, beklenen, tolerans, birim="", yuzde=False):
        if yuzde:
            sapma = abs(alinan - beklenen) / abs(beklenen) * 100 if beklenen else 0
            tamam = sapma <= tolerans
            ek = f"{alinan:.4f}{birim} (beklenen {beklenen:.4f}, sapma %{sapma:.3f})"
        else:
            sapma = abs(alinan - beklenen)
            tamam = sapma <= tolerans
            ek = f"{alinan:.4f}{birim} (beklenen {beklenen:.4f}, fark {sapma:.4f})"
        return self.kosul(ad, tamam, ek)


# --------------------------------------------------------------- derleme
def firmware_derle(hedef: Path) -> Path:
    hedef.mkdir(parents=True, exist_ok=True)
    s = subprocess.run(
        [str(ARDUINO_CLI), "compile", "--fqbn", "arduino:avr:uno",
         "--warnings", "all", "--output-dir", str(hedef), str(ESKIZ)],
        capture_output=True, text=True, timeout=900)
    if s.returncode != 0:
        raise SystemExit("arduino-cli derleyemedi:\n" + s.stdout + s.stderr)
    elfler = list(hedef.glob("*.elf"))
    if not elfler:
        raise SystemExit(f"ELF uretilmedi: {hedef}")
    return elfler[0]


# ------------------------------------------------------------ analog model
def bolucu_tablosu(rapor: Rapor):
    """ngspice ile gercek bolucuyu tarar: giris gerilimi -> A0 dugum gerilimi."""
    kayit, dizin = spice.kos(sim_bolucu.netlist_dc(30.0, "1n"),
                             BURASI / "_s9_bolucu")
    veri = spice.degerler(dizin / "dc.txt")
    x = np.array([s[0] for s in veri])
    y = np.array([s[1] for s in veri])
    oran = x[-1] / y[-1]
    rapor.yakin("Bolucu orani ngspice'tan", oran, 11.0, 0.5, "", yuzde=True)
    return x, y


def akim_tablosu(rapor: Rapor, vos: str):
    """ngspice ile gercek LM358 katini tarar: yuk akimi -> A1 cikis gerilimi."""
    imaks = AREF_OLCULEN / KAZANC / SONT * 1.1
    kayit, dizin = spice.kos(sim_akim.netlist_dc(SONT, vos, imaks),
                             BURASI / "_s9_akim")
    veri = spice.degerler(dizin / "dc.txt")
    x = np.array([s[0] for s in veri])
    y = np.array([s[2] for s in veri])
    # Kazanc EGIM olarak olculur: tek noktadan oran alinirsa giris ofseti
    # (vos) kazanca karisir ve %1.7 yuksek cikar. Iki nokta farki ofseti atar.
    a, b_ = len(x) // 4, len(x) * 3 // 4
    k = (y[b_] - y[a]) / ((x[b_] - x[a]) * SONT)
    rapor.yakin("LM358 kazanci ngspice'tan (egim)", k, KAZANC, 0.5, "", yuzde=True)
    v0 = float(y[0])
    rapor.bilgi(f"    sifir akimda cikis {v0*1000:.1f} mV — 's' komutu bunu siler")
    return x, y


class Dunya:
    """Kartin girisine baglanan dis dunya."""

    def __init__(self, v_tab, i_tab):
        self.vx, self.vy = v_tab
        self.ix, self.iy = i_tab
        self.volt = 0.0            # bolucu girisine uygulanan DC gerilim
        self.amper = 0.0           # sonttan gecen akim
        self.ac_genlik = 0.0       # osiloskop icin sinus tepe degeri
        self.ac_hz = 0.0
        self.kart = None
        self.a0_kayit = []

    def gerilim_ham(self, kanal: int, deger: float) -> float:
        """Verilen giris icin ngspice'in soyledigi dugum gerilimi.

        Testin beklenen degerleri bundan turetilir; boylece beklenti benim
        cebrim degil, devrenin kendi simulasyonu olur.
        """
        if kanal == 0:
            return float(np.interp(deger, self.vx, self.vy))
        if kanal == 1:
            return float(np.interp(deger, self.ix, self.iy))
        return 0.0

    def gerilim(self, kanal: int) -> float:
        if kanal == 0:
            v = self.volt
            if self.ac_genlik and self.kart is not None:
                # ADC'nin IDEAL ornekleme ani — komutun calistigi an degil.
                # Ikisi karisirsa 1000 orneklik yakalamada zamanlama kayar.
                t = self.kart.ornek_cevrim / mega328.F_CPU
                v += self.ac_genlik * np.sin(2 * np.pi * self.ac_hz * t)
            return self.gerilim_ham(0, v)
        if kanal == 1:
            return self.gerilim_ham(1, self.amper)
        return 0.0


# ------------------------------------------------------------- yardimcilar
def kart_kur(flash, dunya, aref, eeprom=None):
    kart = mega328.Kart(flash, Cekirdek, aref=aref,
                        kanal_gerilim=dunya.gerilim,
                        kaynak_direnc=THEVENIN, eeprom=eeprom)
    dunya.kart = kart
    return kart


def d_satirlari(metin: str):
    cikti = []
    for s in metin.splitlines():
        p = s.split()
        if len(p) == 8 and p[0] == "D":
            try:
                cikti.append([float(x) for x in p[1:6]] + [int(p[6]), int(p[7])])
            except ValueError:
                pass
    return cikti


def beklenen_kod(volt_dugum: float, aref: float) -> int:
    """Veri sayfasi denklemi: ADC = floor(V_in x 1024 / V_REF)."""
    k = int(volt_dugum / aref * 1024.0)
    return max(0, min(1023, k))


def komut(kart, metin: str, saniye: float):
    kart.seri_gonder(metin)
    kart.saniye_kadar_kos(saniye)


def main() -> int:
    r = Rapor()
    veri = {}                 # kanit sayfasi ve grafikler icin ham sonuclar
    t_bas = time.time()
    print("=" * 78)
    print("  S9 — KART UCTAN UCA  (ngspice -> gercek firmware -> gercek arayuz)")
    print("=" * 78)

    CIKTI.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------- 1. derleme
    print("\n--- 1. Gercek firmware'i derle -----------------------------------")
    elf_yol = firmware_derle(BURASI / "_s9_derleme")
    flash, _ = elf.flash_goruntusu(elf_yol)
    simgeler = elf.semboller(elf_yol)
    print(f"  {elf_yol.name}  ({elf_yol.stat().st_size:,} bayt ELF)")
    # setup()/loop()/olc() -Os ile main icine gomuluyor, simgeleri kalmiyor.
    # Ikili gercekten BU kaynaktan uretildi mi sorusu, veri simgeleri ve
    # kaynaktaki metinlerin flash'ta bulunmasiyla dogrulanir.
    r.kosul("main() ELF'te var", "main" in simgeler)
    veri_simgeleri = ("ayar", "enerji_pJ", "tampon", "rapor_ms", "v_adim",
                      "i_adim", "akis", "ornek")
    eksik = [k for k in veri_simgeleri if k not in simgeler]
    r.kosul("Durum degiskenlerinin hepsi SRAM'de", not eksik,
            f"{len(veri_simgeleri)} simge" if not eksik else f"eksik: {eksik}")
    metinler = (b"Olcum Karti", b"D <volt> <amper> <watt> <joule> <wh> <ms> <ornek>",
                b"kv<volt>", b"ohm", b"! tetiklenemedi",
                b"t[esik]")
    yok = [t for t in metinler if t not in bytes(flash)]
    r.kosul("Kaynaktaki metinler ikilinin icinde", not yok,
            f"{len(metinler)} metin" if not yok else f"bulunamadi: {yok}")

    # ----------------------------------------------------- 2. analog model
    print("\n--- 2. Analog kati ngspice ile tara ------------------------------")
    v_tab = bolucu_tablosu(r)
    i_tab = akim_tablosu(r, "2m")          # LM358 tipik giris ofseti
    dunya = Dunya(v_tab, i_tab)

    # ------------------------------------------------------------- 3. acilis
    print("\n--- 3. Firmware'i baslat -----------------------------------------")
    kart = kart_kur(flash, dunya, AREF_OLCULEN)
    kart.saniye_kadar_kos(0.30)
    acilis = kart.tx.decode("ascii", "replace")

    r.kosul("Acilis basligi geldi", "Olcum Karti" in acilis)
    r.kosul("Ayar dokumu basildi", "--- ayarlar ---" in acilis)
    r.kosul("Yardim metni basildi", "y : bu yardim" in acilis)
    r.kosul("Cikis bicimi ilan edildi",
            "D <volt> <amper> <watt> <joule> <wh> <ms> <ornek>" in acilis)

    # AREF guvenligi: ADMUX'un REFS bitleri sifir olmali (harici referans)
    admux = kart.cpu.m[mega328.ADMUX]
    r.kosul("ADMUX REFS = 00 (HARICI referans secili)", (admux >> 6) == 0,
            f"ADMUX = {admux:#04x}")
    r.kosul("ADC en az bir donusum yapti", kart.adc_donusum > 0,
            f"{kart.adc_donusum} donusum")

    ilk = d_satirlari(acilis)
    r.kosul("Olcum akisi kendiliginden basladi", len(ilk) > 0,
            f"{len(ilk)} rapor satiri")

    # raporu hizlandir ki test kisa sursun
    kart.tx.clear()
    komut(kart, "h50\n", 0.10)
    r.kosul("h50 komutu kabul edildi",
            "Rapor araligi = 50 ms" in kart.tx.decode("ascii", "replace"))

    # -------------------------------------------------- 4. gerilim/akim/guc
    print("\n--- 4. Uygulanan deger ile okunan degeri karsilastir --------------")
    print(f"  AREF = {AREF_OLCULEN} V (tezgahta olculen), sont = {SONT} ohm, "
          f"ADC adimi = {AREF_OLCULEN / 1024 * 11 * 1000:.1f} mV")
    print()
    print(f"  {'uygulanan':>18} {'okunan':>18} {'hata':>9}   {'hata':>9}")
    print(f"  {'V':>8} {'mA':>9} {'V':>8} {'mA':>9} {'V':>9} {'mA':>9}")
    print("  " + "-" * 62)

    olcumler = []
    for v_uyg, i_uyg in ((3.30, 0.0050), (5.00, 0.0100),
                         (12.00, 0.0200), (24.00, 0.0300)):
        dunya.volt, dunya.amper = v_uyg, i_uyg
        kart.tx.clear()
        kart.saniye_kadar_kos(0.25)
        d = d_satirlari(kart.tx.decode("ascii", "replace"))
        if not d:
            r.kosul(f"{v_uyg} V icin rapor geldi", False)
            continue
        son = d[-1]
        v_ok, i_ok, w_ok = son[0], son[1], son[2]
        olcumler.append((v_uyg, i_uyg, v_ok, i_ok, w_ok))
        print(f"  {v_uyg:8.2f} {i_uyg*1000:9.2f} {v_ok:8.3f} {i_ok*1000:9.3f} "
              f"{v_ok - v_uyg:+9.3f} {(i_ok - i_uyg)*1000:+9.3f}")

    veri["olcumler"] = [list(x) for x in olcumler]
    print()
    lsb_v = AREF_OLCULEN / 1024 * 11
    lsb_i = AREF_OLCULEN / 1024 / KAZANC / SONT
    print(f"  1 LSB = {lsb_v*1000:.1f} mV gerilimde, "
          f"{lsb_i*1e6:.1f} uA akimda")
    print()
    for v_uyg, i_uyg, v_ok, i_ok, w_ok in olcumler:
        # Beklenen deger CEBIRLE degil, ngspice tablosu + veri sayfasi
        # denklemi ile turetiliyor: dugum gerilimi -> ADC kodu -> okuma.
        kod_v = beklenen_kod(dunya.gerilim_ham(0, v_uyg), AREF_OLCULEN)
        kod_i = beklenen_kod(dunya.gerilim_ham(1, i_uyg), AREF_OLCULEN)
        bek_v = kod_v * lsb_v
        bek_i = kod_i * lsb_i
        r.yakin(f"  {v_uyg:5.2f} V: firmware ADC kodu {kod_v} ile birebir",
                v_ok, bek_v, lsb_v * 0.55, " V")
        r.yakin(f"  {v_uyg:5.2f} V: okuma uygulanan degere esit",
                v_ok, v_uyg, lsb_v, " V")
        r.yakin(f"  {i_uyg*1000:5.2f} mA: firmware ADC kodu {kod_i} ile birebir",
                i_ok, bek_i, lsb_i * 0.55, " A")
        r.yakin(f"  {v_uyg:5.2f} V x akim = watt tutarli", w_ok, v_ok * i_ok,
                max(w_ok, 1e-6) * 0.02, " W")

    # ------------------------------------------------------ 5. ofset sifirla
    print("\n--- 5. 's' komutu: LM358 giris ofsetini sifirla -------------------")
    # Beklenti yine ngspice'tan: sifir akimda LM358 cikisi ne ise o.
    v0 = dunya.gerilim_ham(1, 0.0)
    beklenen_ofset_adim = beklenen_kod(v0, AREF_OLCULEN)
    print(f"  ngspice: sifir akimda LM358 cikisi {v0*1000:.1f} mV "
          f"-> ADC kodu {beklenen_ofset_adim} bekleniyor")
    print(f"  (LM358 vos = 2 mV, kazanc {KAZANC:.3f}; makromodelin cikis "
          f"tabani 20 mV oldugu icin ideal cebirden biraz yuksek)")
    dunya.amper = 0.0
    kart.tx.clear()
    komut(kart, "s\n", 2.40)                 # firmware 2 sn bekliyor
    cvp = kart.tx.decode("ascii", "replace")
    m = re.search(r"Ofset = (-?\d+) adim", cvp)
    r.kosul("'s' komutu ofseti buldu ve yazdi", m is not None,
            m.group(0) if m else cvp[-120:].replace("\n", " | "))
    if m:
        ofset = int(m.group(1))
        r.yakin("  Bulunan ofset LM358 modelini dogruluyor",
                ofset, beklenen_ofset_adim, 1.5, " adim")

    dunya.amper = 0.0200
    kart.tx.clear()
    kart.saniye_kadar_kos(0.25)
    d = d_satirlari(kart.tx.decode("ascii", "replace"))
    if d and m:
        kod = beklenen_kod(dunya.gerilim_ham(1, 0.0200), AREF_OLCULEN)
        bek = (kod - int(m.group(1))) * lsb_i
        r.yakin("  Ofset sonrasi okuma (kod - ofset) x adim ile birebir",
                d[-1][1], bek, lsb_i * 0.55, " A")
        # Kalan sapma model kaynakli: LM358 makromodelinin cikis tabani 20 mV,
        # kucuk isaret ofseti ise 15.8 mV. Fark ~1 LSB'lik fazla cikarma yapar.
        r.yakin("  Ofset sonrasi 20.00 mA okumasi (kalan sapma)",
                d[-1][1], 0.0200, 3 * lsb_i, " A")

    # ------------------------------------------------ 6. EEPROM kaliciligi
    print("\n--- 6. EEPROM: ayar yeniden aciliste duruyor mu -------------------")
    eeprom_kopya = bytearray(kart.eeprom)
    r.kosul("EEPROM'a gercekten yazildi",
            bytes(eeprom_kopya[:2]) == b"\xfe\xc0",
            f"imza = {eeprom_kopya[1]:02x}{eeprom_kopya[0]:02x} (0xC0FE bekleniyor)")

    dunya2 = Dunya(v_tab, i_tab)
    kart2 = kart_kur(flash, dunya2, AREF_OLCULEN, eeprom=eeprom_kopya)
    kart2.saniye_kadar_kos(0.30)
    yeniden = kart2.tx.decode("ascii", "replace")
    m2 = re.search(r"i ofset\s*:\s*(-?\d+)", yeniden)
    r.kosul("Yeniden aciliste ofset EEPROM'dan geldi",
            m2 is not None and m and int(m2.group(1)) == int(m.group(1)),
            f"okunan {m2.group(1) if m2 else '?'} / yazilan {m.group(1) if m else '?'}")

    # --------------------------------------------------- 7. kalibrasyon
    print("\n--- 7. 'kv' kalibrasyonu: yanlis AREF'i duzeltiyor mu -------------")
    aref_yanlis = 2.478                       # S1'in SPICE tahmini
    # Kod = V/AREF_gercek*1024, okuma = kod*AREF_sanilan/1024*11.
    # Yani okuma/gercek = AREF_sanilan/AREF_gercek: referans BUYUDUKCE okuma DUSER.
    hata_bekleniyor = (AREF_OLCULEN / aref_yanlis - 1) * 100
    print(f"  Kart AREF = {aref_yanlis} V ile calistiriliyor ama firmware "
          f"{AREF_OLCULEN} V sabitine inaniyor")
    print(f"  -> beklenen sistematik hata: %{hata_bekleniyor:+.3f} "
          f"(referans buyudukce okuma duser)")

    dunya3 = Dunya(v_tab, i_tab)
    kart3 = kart_kur(flash, dunya3, aref_yanlis)
    kart3.saniye_kadar_kos(0.30)
    komut(kart3, "h50\n", 0.05)
    dunya3.volt, dunya3.amper = 12.00, 0.0
    kart3.tx.clear()
    kart3.saniye_kadar_kos(0.25)
    d = d_satirlari(kart3.tx.decode("ascii", "replace"))
    once = d[-1][0] if d else 0.0
    print(f"  kalibrasyon oncesi: {once:.4f} V  (hata %{(once/12-1)*100:+.3f})")

    kart3.tx.clear()
    komut(kart3, "kv12.00\n", 0.40)
    cvp3 = kart3.tx.decode("ascii", "replace")
    m3 = re.search(r"v_duzeltme = ([\d.]+)", cvp3)
    r.kosul("'kv' komutu duzeltme carpani hesapladi", m3 is not None,
            m3.group(0) if m3 else cvp3[-120:].replace("\n", " | "))

    kart3.tx.clear()
    kart3.saniye_kadar_kos(0.25)
    d = d_satirlari(kart3.tx.decode("ascii", "replace"))
    sonra = d[-1][0] if d else 0.0
    print(f"  kalibrasyon sonrasi: {sonra:.4f} V  (hata %{(sonra/12-1)*100:+.3f})")
    veri["kalibrasyon"] = {"aref_gercek": aref_yanlis, "aref_sanilan": AREF_OLCULEN,
                           "once": once, "sonra": sonra, "uygulanan": 12.00,
                           "carpan": float(m3.group(1)) if m3 else None}
    r.yakin("  Kalibrasyon sonrasi 12.00 V", sonra, 12.00, lsb_v, " V")
    r.kosul("  Kalibrasyon hatayi kucultttu", abs(sonra - 12) < abs(once - 12),
            f"{abs(once-12)*1000:.1f} mV -> {abs(sonra-12)*1000:.1f} mV")

    # ------------------------------------------------------- 8. enerji
    print("\n--- 8. Enerji sayaci ---------------------------------------------")
    dunya.volt, dunya.amper = 12.00, 0.0200
    kart.tx.clear()
    komut(kart, "e\n", 0.05)
    r.kosul("'e' enerji sayacini sifirladi",
            "Enerji sifirlandi" in kart.tx.decode("ascii", "replace"))
    kart.tx.clear()
    kart.saniye_kadar_kos(1.00)
    d = d_satirlari(kart.tx.decode("ascii", "replace"))
    if len(d) >= 2:
        ilk_d, son_d = d[0], d[-1]
        dt = (son_d[5] - ilk_d[5]) / 1000.0
        dj = son_d[3] - ilk_d[3]
        guc = son_d[2]
        print(f"  {dt:.3f} s icinde {dj:.4f} J biriktirdi, anlik guc {guc:.4f} W")
        r.yakin("  Enerji = guc x sure", dj, guc * dt, 3.0, " J", yuzde=True)
        r.yakin("  Wh alani Joule ile tutarli", son_d[4] * 3600, son_d[3],
                0.5, " J", yuzde=True)
        r.kosul("  Sayac ileri gidiyor", son_d[3] > ilk_d[3],
                f"{ilk_d[3]:.4f} -> {son_d[3]:.4f} J")

    # ------------------------------------------------- 9. ornekleme hizi
    print("\n--- 9. Ornekleme -------------------------------------------------")
    if d:
        n = d[-1][6]
        aralik = (d[-1][5] - d[-2][5]) / 1000.0 if len(d) >= 2 else 0.05
        hiz = n / aralik
        print(f"  {aralik*1000:.0f} ms pencerede {n} ornek -> {hiz:,.0f} ornek/sn")
        tavan = mega328.F_CPU / (4 * 13 * 128)
        r.kosul(f"  Ornekleme hizi ADC tavaninin ({tavan:,.0f}/sn) altinda",
                1200 <= hiz <= tavan, f"{hiz:,.0f} ornek/sn "
                f"(ADC 4 donusum x 13 saat x 128 on bolucu)")
        r.kosul("  Gurultu bastirma = sqrt(N)", n > 50,
                f"sqrt({n}) = {n**0.5:.1f} kat")

    # ------------------------------------------------------ 10. osiloskop
    print("\n--- 10. Osiloskop kipi -------------------------------------------")
    # 1000 ornek / 76923 Hz = 13.0 ms. Pencereye TAM 3 cevrim sigsin ki
    # ortalama, eksik cevrim yuzunden kaymasin.
    dunya.volt, dunya.ac_genlik = 12.0, 6.0
    dunya.ac_hz = 3 * 76923 / 1000
    kart.tx.clear()
    komut(kart, "t\n", 0.60)
    osilo = kart.tx.decode("ascii", "replace")
    mb = re.search(r"^S (\d+) (\d+) ([\d.]+)\s*$", osilo, re.M)   # println CR LF gonderir
    r.kosul("Osiloskop basligi dogru bicimde", mb is not None,
            mb.group(0) if mb else osilo[:120].replace("\n", " | "))
    if mb:
        adet, hz, adim = int(mb.group(1)), int(mb.group(2)), float(mb.group(3))
        govde = osilo[mb.end():]
        ornekler = [int(x) for x in re.findall(r"\b\d{1,3}\b", govde)][:adet]
        r.kosul(f"  {adet} ornek geldi", len(ornekler) == adet,
                f"{len(ornekler)} adet")
        if len(ornekler) == adet:
            tepe = (max(ornekler) - min(ornekler)) * adim
            bek = 2 * dunya.ac_genlik
            print(f"  ornekleme {hz:,} Hz, volt/adim {adim:.6f}, "
                  f"tepeden tepeye {tepe:.2f} V (uygulanan {bek:.2f} V)")
            veri["osilo"] = {"adet": adet, "hz": hz, "volt_adim": adim,
                             "ornekler": ornekler,
                             "ac_genlik": dunya.ac_genlik,
                             "ac_hz": dunya.ac_hz, "dc": dunya.volt}
            r.yakin("  Tepeden tepeye gerilim", tepe, bek, 4.0, " V", yuzde=True)
            # 200 Hz sinus, 76923 Hz ornekleme, 1000 ornek = 13 ms = 2.6 cevrim
            ort = sum(ornekler) / len(ornekler) * adim
            r.yakin("  Ortalama = DC bileseni (tam 3 cevrim)", ort, 12.0, 1.0,
                    " V", yuzde=True)

        # --- tetikleme: 't<esik>' yolu (once olu koddu, simdi erisilebilir)
        tepe_adim = max(ornekler)
        dip_adim = min(ornekler)
        esik = (tepe_adim + dip_adim) // 2
        print(f"  tetikleme denemesi: esik {esik} "
              f"(isaret {dip_adim}-{tepe_adim} adim arasinda)")
        kart.tx.clear()
        komut(kart, f"t{esik}\n", 0.60)
        tet = kart.tx.decode("ascii", "replace")
        mt = re.search(r"^S (\d+) (\d+) ([\d.]+)\s*$", tet, re.M)
        r.kosul("  Tetiklemeli yakalama basarili", mt is not None,
                mt.group(0) if mt else tet[:100].replace("\n", " | "))
        if mt:
            govde2 = tet[mt.end():]
            o2 = [int(x) for x in re.findall(r"\b\d{1,3}\b", govde2)][:int(mt.group(1))]
            if o2:
                # yukselen kenarda tetiklendiyse ilk ornek esigin civarinda olmali
                r.kosul("  Yakalama esigin uzerinde basliyor",
                        o2[0] >= esik - 8,
                        f"ilk ornek {o2[0]}, esik {esik}")

        # --- ulasilamaz esik: hata dali gercekten calisiyor mu
        kart.tx.clear()
        komut(kart, "t250\n", 3.20)      # firmware 200000 donusum bekliyor
        r.kosul("  Ulasilamaz esikte '! tetiklenemedi' donuyor",
                "! tetiklenemedi" in kart.tx.decode("ascii", "replace"),
                "olu koddu, artik calisiyor")

    # -------------------------------------------- 11. hatali komut, sinir
    print("\n--- 11. Hatali girdi ---------------------------------------------")
    kart.tx.clear()
    komut(kart, "zzz\n", 0.05)
    r.kosul("Bilinmeyen komut reddedildi",
            "? bilinmeyen komut" in kart.tx.decode("ascii", "replace"))
    kart.tx.clear()
    komut(kart, "h9999\n", 0.05)
    r.kosul("Sinir disi rapor araligi reddedildi",
            "20-5000 ms" in kart.tx.decode("ascii", "replace"))
    kart.tx.clear()
    komut(kart, "h" + "9" * 40 + "\n", 0.10)
    r.kosul("Tampon tasmasi kartsi cokertmedi (16 baytlik sabit tampon)",
            kart.cpu.pc != 0 and len(kart.tx) > 0)

    # --------------------------------------------- 12. arayuze teslim
    print("\n--- 12. Yakalanan seri akisini gercek arayuze ver -----------------")
    dunya.volt, dunya.amper, dunya.ac_genlik = 12.00, 0.0200, 0.0
    kart.tx.clear()
    kart.saniye_kadar_kos(0.40)
    akis = kart.tx.decode("ascii", "replace")
    (CIKTI / "seri-akis.txt").write_text(akis, encoding="utf-8")
    print(f"  {len(akis)} bayt yazildi: kanit/seri-akis.txt")

    ui = subprocess.run(
        ["node", "test_arayuz_akis.js", str(CIKTI / "seri-akis.txt"),
         f"{dunya.volt}", f"{dunya.amper}"],
        cwd=BURASI, capture_output=True, timeout=300)
    # node UTF-8 yazar, konsol cp1254 — kod cozmeyi acikca yap.
    metin = (ui.stdout or ui.stderr).decode("utf-8", "replace").strip()
    print("  " + metin.replace("\n", "\n  "))
    r.kosul("Arayuz zincirin sonunu dogruladi", ui.returncode == 0)

    # ------------------------------------------------------------- ozet
    print("\n" + "=" * 78)
    veri["ozet"] = {"gecti": r.gecti, "kaldi": r.kaldi,
                    "cevrim": kart.cpu.cevrim + kart2.cpu.cevrim + kart3.cpu.cevrim,
                    "lsb_v": lsb_v, "lsb_i": lsb_i, "aref": AREF_OLCULEN,
                    "sont": SONT, "kazanc": KAZANC}
    (CIKTI / "s9-veri.json").write_text(
        json.dumps(veri, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  ham sonuclar: kanit/s9-veri.json")

    sure = time.time() - t_bas
    print(f"  S9: {r.gecti}/{r.gecti + r.kaldi} kosul gecti   "
          f"({kart.cpu.cevrim + kart2.cpu.cevrim + kart3.cpu.cevrim:,} AVR cevrimi, "
          f"{sure:.1f} s)")
    print("=" * 78)
    return 0 if r.kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
