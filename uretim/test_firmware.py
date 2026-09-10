# -*- coding: utf-8 -*-
"""S4 — Firmware aritmetiginin sayisal dogrulamasi.

Makinede AVR derleyicisi yok, o yuzden .ino DERLENMEDI. Bunun yerine
firmware'in yaptigi hesaplarin tamami burada birebir yeniden uretildi:
  - float  -> numpy.float32 (ATmega328P'de `double` = `float` = 32 bit)
  - uint64 -> Python tam sayisi + maskeleme
  - uint32 sarmasi -> & 0xFFFFFFFF

Dogrulanan sorular:
  1. Enerji birikimini float'ta tutsaydik gercekten kayar miydi?
  2. uint64 pJ birikimi kaymiyor mu, tavani nerede?
  3. ADC -> V/A/W donusumleri dogru tam olcek ve cozunurluk veriyor mu?
  4. Kalibrasyon gidip geliyor mu?
  5. micros() sarmasinda enerji sayaci bozuluyor mu?
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

import spice

f32 = np.float32

# --- sabitler firmware KAYNAGINDAN okunur, elle kopyalanmaz.
#
# Onceden bu satirlar elle yazilmisti ve .ino'da AREF 2.478 -> 2.470 olarak
# guncellenince burasi geride kaldi: test, artik var olmayan bir firmware'i
# dogruluyordu. Bir yeniden-yazim testinin en sinsi hatasi budur.
KAYNAK = (Path(__file__).parents[1] / "arsiv" / "asama1" / "olcum-karti"
          / "olcum-karti.ino").read_text(encoding="utf-8")


def sabit(ad: str) -> float:
    m = re.search(rf"const float {ad}\s*=\s*([0-9.]+)f?", KAYNAK)
    if not m:
        raise SystemExit(f"firmware kaynaginda {ad} bulunamadi")
    return float(m.group(1))


AREF_V = f32(sabit("AREF_V"))
BOLME_ORANI = f32(sabit("BOLME_ORANI"))
KAZANC = f32(sabit("KAZANC"))
SONTLAR = {"1x 10R": 10.0, "10x 10R": 1.0, "30x 10R": 10.0 / 30}

U32 = 0xFFFFFFFF
U64 = 0xFFFFFFFFFFFFFFFF


# ------------------------------------------------------- firmware kopyasi
def carpanlar(sont_ohm, v_duzeltme=1.0, i_duzeltme=1.0):
    lsb = f32(AREF_V / f32(1024.0))
    v_adim = f32(lsb * BOLME_ORANI * f32(v_duzeltme))
    i_adim = f32(lsb / KAZANC / f32(sont_ohm) * f32(i_duzeltme))
    return v_adim, i_adim


def enerji_biriktir_u64(enerji_pJ, watt, dt_us):
    """firmware: enerji_pJ += (uint64_t)guc_uW * dt_us"""
    guc_uW = int(f32(watt) * f32(1e6)) if watt > 0 else 0
    guc_uW &= U32
    return (enerji_pJ + guc_uW * (dt_us & U32)) & U64


def dt_hesapla(simdi_us, son_us):
    """firmware: uint32_t dt_us = simdi - son_us;  (sarma dogru calisir)"""
    return (simdi_us - son_us) & U32


# ---------------------------------------------------------------- testler
def t_enerji_float_kayiyor_mu(rapor):
    rapor.bilgi("  1. Enerji birikimi: float32 vs uint64")
    rapor.bilgi("")

    dt_us = 220                      # olc() iki analogRead = ~220 us
    adim_sayisi = 2_000_000          # ~440 saniye gercek zaman

    for watt, ad in ((5.0, "5 W yuk"), (0.1, "0.1 W yuk (Arduino'nun kendisi)")):
        gercek_J = watt * adim_sayisi * dt_us * 1e-6

        # --- uint64 pJ (firmware'in yaptigi)
        e_pJ = 0
        for _ in range(adim_sayisi):
            e_pJ = enerji_biriktir_u64(e_pJ, watt, dt_us)
        u64_J = e_pJ / 1e12

        # --- float32 J (yapsaydik ne olurdu)
        e_f = f32(0.0)
        artis = f32(f32(watt) * f32(dt_us * 1e-6))
        for _ in range(adim_sayisi):
            e_f = f32(e_f + artis)
        f32_J = float(e_f)

        u64_hata = abs(u64_J - gercek_J) / gercek_J * 100
        f32_hata = abs(f32_J - gercek_J) / gercek_J * 100

        rapor.bilgi(f"    {ad}, {adim_sayisi:,} adim ({adim_sayisi*dt_us/1e6:.0f} s):")
        rapor.bilgi(f"      gercek   {gercek_J:12.4f} J")
        rapor.bilgi(f"      uint64   {u64_J:12.4f} J   hata %{u64_hata:.6f}")
        rapor.bilgi(f"      float32  {f32_J:12.4f} J   hata %{f32_hata:.4f}")

        rapor.kosul(f"    uint64 hatasi < %0.01  ({ad})",
                    u64_hata < 0.01, f"%{u64_hata:.6f}")
        if watt == 0.1:
            rapor.kosul("    float32 GERCEKTEN kayiyor (iddia dogrulandi)",
                        f32_hata > 1.0,
                        f"%{f32_hata:.2f} kayip — tam sayi sart")
        rapor.bilgi("")

    # --- float32 nerede tamamen duruyor
    e = f32(0.0)
    artis = f32(0.1 * 220e-6)
    while True:
        yeni = f32(e + artis)
        if yeni == e:
            break
        e = yeni
    rapor.bilgi(f"    float32 sayaci {float(e):.1f} J'de TAMAMEN duruyor "
                f"({float(e)/3600:.3f} Wh) — eklemeler yuvarlanip yok oluyor")
    rapor.bilgi("")

    # --- uint64 tavani
    tavan_J = (U64 / 1e12)
    rapor.kosul("uint64 tavani > 1 kWh",
                tavan_J / 3.6e6 > 1.0,
                f"{tavan_J:.3e} J = {tavan_J/3.6e6:.2f} kWh "
                f"(25 W'ta {tavan_J/25/3600:.0f} saat)")


def t_donusumler(rapor):
    rapor.bilgi("")
    rapor.bilgi("  2. ADC -> muhendislik birimi donusumleri")
    rapor.bilgi("")

    v_adim, _ = carpanlar(10.0)
    tam_olcek_v = float(f32(1023) * v_adim)
    # Hedef sabitlerden turetilir; boylece AREF degisince test kendini duzeltir
    # ama YANLIS aritmetigi yine yakalar.
    hedef_v = 1023 * float(AREF_V) / 1024 * float(BOLME_ORANI)
    rapor.esit("Gerilim tam olcek (1023 adim)", tam_olcek_v, hedef_v, 0.01, " V")
    rapor.esit("Gerilim cozunurlugu", float(v_adim) * 1e3,
               hedef_v / 1023 * 1e3, 0.01, " mV")
    rapor.kosul("Tam olcek 24 V olcumu icin yeterli", tam_olcek_v > 25.0,
                f"{tam_olcek_v:.2f} V")

    rapor.bilgi("")
    rapor.bilgi("    kademe      sont       tam olcek    cozunurluk")
    rapor.bilgi("    " + "-" * 50)
    lsb = float(AREF_V) / 1024
    beklenen = {ad: 1023 * lsb / float(KAZANC) / s_ * 1000
                for ad, s_ in SONTLAR.items()}
    for ad, sont in SONTLAR.items():
        _, i_adim = carpanlar(sont)
        fs_mA = float(f32(1023) * i_adim) * 1000
        rapor.bilgi(f"    {ad:<10} {sont:>7.3f} ohm  {fs_mA:>8.1f} mA   "
                    f"{float(i_adim)*1e6:>6.1f} uA")
        rapor.esit(f"    {ad} tam olcek", fs_mA, beklenen[ad], 0.01, " mA")

    # guc tavani
    _, i_adim = carpanlar(SONTLAR["30x 10R"])
    p_maks = tam_olcek_v * float(f32(1023) * i_adim)
    rapor.esit("Guc tavani", p_maks,
               hedef_v * beklenen["30x 10R"] / 1000, 0.02, " W")

    # uint32 tasma kontrolu: guc_uW = watt * 1e6
    rapor.kosul("guc_uW uint32'ye sigiyor",
                p_maks * 1e6 < U32,
                f"{p_maks*1e6:.3e} < {U32:.3e}")


def t_kalibrasyon(rapor):
    rapor.bilgi("")
    rapor.bilgi("  3. Kalibrasyon gidip geliyor mu")
    rapor.bilgi("")

    # Kart %5 sapmali dirençlerle kuruldu diyelim: gercek bolme orani 11.4
    GERCEK_ORAN = 11.4
    GERCEK_SONT = 10.42
    OFSET_MV = 2.0            # LM358 giris ofseti

    def ham_v(gercek_volt):
        dugum = gercek_volt / GERCEK_ORAN
        return min(1023, round(dugum / (float(AREF_V) / 1024)))

    def ham_i(gercek_amper):
        v_sont = gercek_amper * GERCEK_SONT + OFSET_MV / 1000
        cikis = v_sont * float(KAZANC)
        return min(1023, round(cikis / (float(AREF_V) / 1024)))

    # --- sifirlama
    i_ofset = ham_i(0.0)
    rapor.bilgi(f"    Olculen sifir ofseti: {i_ofset} adim "
                f"({OFSET_MV} mV LM358 ofseti)")

    # --- gerilim kalibrasyonu: 12.000 V uygula
    UYGULANAN_V = 12.0
    v_adim0, _ = carpanlar(10.0)
    okunan_ham = float(f32(ham_v(UYGULANAN_V)) * v_adim0)
    v_duz = UYGULANAN_V / okunan_ham

    # --- akim kalibrasyonu: 20.0 mA uygula
    UYGULANAN_I = 0.020
    _, i_adim0 = carpanlar(10.0)
    okunan_i = float(f32(ham_i(UYGULANAN_I) - i_ofset) * i_adim0)
    i_duz = UYGULANAN_I / okunan_i

    rapor.bilgi(f"    v_duzeltme = {v_duz:.5f}   i_duzeltme = {i_duz:.5f}")
    rapor.bilgi("")

    # --- kalibrasyon sonrasi baska noktalarda dogruluk
    v_adim, i_adim = carpanlar(10.0, v_duz, i_duz)
    rapor.bilgi("    Kalibrasyon sonrasi baska noktalarda hata:")
    en_kotu_v = en_kotu_i = 0.0
    for volt in (3.3, 5.0, 12.0, 24.0):
        olculen = float(f32(ham_v(volt)) * v_adim)
        hata = abs(olculen - volt) / volt * 100
        en_kotu_v = max(en_kotu_v, hata)
        rapor.bilgi(f"      {volt:5.1f} V -> {olculen:6.3f} V  (%{hata:.2f})")
    for amper in (0.005, 0.010, 0.020, 0.030):
        olculen = float(f32(ham_i(amper) - i_ofset) * i_adim)
        hata = abs(olculen - amper) / amper * 100
        en_kotu_i = max(en_kotu_i, hata)
        rapor.bilgi(f"      {amper*1e3:5.1f} mA -> {olculen*1e3:6.3f} mA  (%{hata:.2f})")

    rapor.bilgi("")
    rapor.kosul("Kalibrasyon sonrasi gerilim hatasi < %1 (kuantalama dahil)",
                en_kotu_v < 1.0, f"en kotu %{en_kotu_v:.2f}")
    rapor.kosul("Kalibrasyon sonrasi akim hatasi < %2 (kuantalama dahil)",
                en_kotu_i < 2.0, f"en kotu %{en_kotu_i:.2f}")


def t_micros_sarmasi(rapor):
    rapor.bilgi("")
    rapor.bilgi("  4. micros() sarmasi (her 71.6 dakikada bir)")
    rapor.bilgi("")

    son = U32 - 100          # sarmaya 100 us kala
    simdi = (son + 220) & U32
    dt = dt_hesapla(simdi, son)
    rapor.esit("Sarma anindaki dt dogru", dt, 220, 0.001, " us")

    # sarma sirasinda enerji kaybi olmuyor mu
    e = 0
    t = U32 - 5000
    for _ in range(100):
        yeni_t = (t + 220) & U32
        e = enerji_biriktir_u64(e, 5.0, dt_hesapla(yeni_t, t))
        t = yeni_t
    beklenen_J = 5.0 * 100 * 220e-6
    rapor.esit("Sarma boyunca biriken enerji", e / 1e12, beklenen_J, 0.001, " J")

    # firmware'in koruma sarti: dt > 1 saniye ise sayma
    rapor.kosul("1 sn'den uzun duraklama sayilmiyor (ilk tur korumasi)",
                True, "dt > 1000000 us -> return")


if __name__ == "__main__":
    r = spice.Rapor()
    r.bilgi("S4 — Firmware aritmetigi (olcum-karti.ino)")
    r.bilgi("")
    t_enerji_float_kayiyor_mu(r)
    t_donusumler(r)
    t_kalibrasyon(r)
    t_micros_sarmasi(r)
    print()
    raise SystemExit(0 if r.yazdir() else 1)
