# -*- coding: utf-8 -*-
"""B58f — KUTUNUN KENDI BESLEMESI: zaman benzetimi.

    python sim3_kutu_besleme.py            # ~1 dk

B58 serisi kutunun beslemesini bastan degistirdi: dis besleme yok, iki 18650
PARALEL -> tek TP4056 (DW01A + FS8205A) -> TEK anahtar (PIL) -> MT1 (5 V barasi:
ESP32 + kartin +5 V'u) -> F0 -> B0505S (YALITIMLI 5 -> 5 V) -> MT2 (24 V) ->
kart. `kutu.py` bunu DURAGAN sayilarla ve baglanti grafiyla denetliyor. Bu
betik ZAMANI benzetiyor: anahtar kapaninca ve acilinca ne oluyor.

Neden ayri bir benzetim: duragan butce (B0505S %73 yuk, paket 1.16 A) dogru
olabilir ama ACILIS ondan farkli bir hal. Tek anahtar her seyi AYNI ANDA
aciyor; MT2 kartin 136 uF'sini 24 V'a doldururken B0505S'i asiri yuke sokuyor,
o da 5 V barasini, o da paketi. Eski duzende (B52b) 24 V kendi hucresinden
geliyordu; simdi butun enerji TEK paketten ve B0505S'in dar bogazindan geciyor.

Bolumler:
  1. Anahtar kapanis ani (mikrosaniye): kondansator darbesi, DW01A kisa devre
     algilamasi, MT1'in dogrudan gecis yolu -> 5 V barasinin tepe gerilimi.
  2. Acilis (milisaniye): ortalanmis MT3608 + B0505S + kart modeli, bilinmeyen
     her parametre TARANARAK. 24 V geliyor mu, ESP32 brownout, DW01A asiri akim
     ve asiri desarj, F0 / F1 sigortalari, B0505S asiri yuk suresi.
  3. Kapanis: raylar hangi sirayla sonuyor (B18 durumu).
  4. Yalniz USB (PIL kapali): kutu PC'den ne ceker.
  5. Paralel hucre dengeleme: 10.3'teki +-0.1 V kurali yeterli mi.
  6. PIL acikken sarj: 10.6'daki kuralin sayisal gerekcesi.
  7. B0505S kaynakli gurultu: ray dalgalanmasi ve ortak mod akimi.
  8. Negatif kontroller: her dedektor bozuk bir senaryoda GERCEKTEN kirmizi mi.

⚠ BU BIR DAVRANIS MODELI, SPICE DEGIL. MT3608'ler ortalanmis (anahtarlama
  dalgasi yok), B0505S Thevenin esdegeri + koruma modeli. Veri sayfasinin
  VERMEDIGI her sey (MT3608 yumusak baslama suresi, B0505S'in asiri yuk
  davranisi, DW01A gecikmelerinin alt siniri) tek degere baglanmadi: taranir
  ve karar EN KOTU kola gore verilir. Kaynaklar `tasarim3_sabit.py` B58f.
"""
from __future__ import annotations

import math
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
import tasarim3_sabit as T                              # noqa: E402
from tezgah import tezgah                               # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)


# ═══════════════════════════════════════════════════════════════════════
#  ORTAK: kart kapasitesi, paket direnci, DW01A esikleri
# ═══════════════════════════════════════════════════════════════════════

def _uf(deger: str) -> float:
    m = re.match(r"\s*([\d.]+)\s*([munp]?)F", deger)
    assert m, deger
    return float(m.group(1)) * {"": 1.0, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12}[m.group(2)]


def kart_kapasitesi() -> float:
    """24 V girisinin gordugu kapasite: C16 (+12..-12) + C17 (+12..GND).
    7912 duzenlemeye baslamadan GND dugumu -12'ye yakin durur, C17 de 24 V'un
    uzerinde kalir -> kotu hal ikisinin toplami (kutu.py sigorta_paylari ile ayni)."""
    import yerlesim3 as Y
    nl = Y.Netlist(Y.NETLIST)
    return _uf(nl.deger["C16"]) + _uf(nl.deger["C17"])


def rds(vgs, kose: int):
    """FS8205A TEK FET direnci (25 C). kose 0 = tipik, 1 = maks. Vgs = DW01A'nin
    OD cikisi ~ hucre gerilimi; iki veri noktasi arasinda dogrusal."""
    a, b = T.FS8205_RDS[2.5][kose], T.FS8205_RDS[4.5][kose]
    return a + (b - a) * (np.asarray(vgs, dtype=float) - 2.5) / 2.0


def dw01_oc_akim(v_hucre, kotu: bool = True, sicak: float = T.FS8205_SICAK):
    """DW01A asiri akim esigi (A). Kotu = en DUSUK akim: VOIP min, Rds maks, isinmis FET."""
    if kotu:
        return T.DW01_VOIP[0] / (2 * rds(v_hucre, 1) * sicak)
    return T.DW01_VOIP[1] / (2 * rds(v_hucre, 0))


def izole_r(pw: float, kose: int) -> float:
    """B0505S cikis direnci (Thevenin): %10 -> %100 yukte regulasyon (kose 0 tip, 1 maks)."""
    reg = T.IZOLE_YUK_REG[pw][kose]
    return reg * 5.0 / (0.9 * T.IZOLE_ANMA_AKIM[pw])


def izole_voc(pw: float, kose_egri: int, r_out: float, v_giris):
    """Bosta cikis: %10 yukteki egri noktasi + R_out * %10 anma; girisle ^HAT_REG."""
    v10 = 5.0 * T.IZOLE_EGRI_10[kose_egri] * (np.maximum(v_giris, 0.0) / 5.0) ** T.IZOLE_HAT_REG
    return v10 + r_out * 0.1 * T.IZOLE_ANMA_AKIM[pw]


def _kapi_metni(no: str) -> str:
    import kutu_veri as K
    for a in K.ADIMLAR:
        for s in a.get("alt", []):
            if s["no"] == no:
                return " ".join(s.get("yap", []) + s.get("kontrol", []))
    return ""


# ═══════════════════════════════════════════════════════════════════════
#  1. ANAHTAR KAPANIS ANI — mikrosaniye
# ═══════════════════════════════════════════════════════════════════════

def darbe_benzet(voc, r_src, l_w, c_bus, rds_cift, dt=10e-9, t_son=400e-6):
    """Paket -> anahtar kablosu (R, L) -> MT1 giris seramigi -> MT1 bobini + Schottky
    (dogrudan gecis: anahtarlama baslamadan cikis kondansatorleri pilden dolar) -> 5 V barasi.
    Donus: (paket akimi tepe, V_CS tepe, V_CS > VSIP_min suresi, bara tepe, I2t kol basina)."""
    n = len(voc)
    voc, r_src, l_w, c_bus, rds_cift = (np.asarray(x, dtype=float) for x in (voc, r_src, l_w, c_bus, rds_cift))
    c_in, esr = T.MT3608_C, 5e-3
    i_w = np.zeros(n); v_a = np.zeros(n); i_l = np.zeros(n); v_b = np.zeros(n)
    r_yuk = 100.0                                     # ESP32 henuz acilmadi (LDO + kondansatorler)
    i_tepe = np.zeros(n); vcs_tepe = np.zeros(n); vcs_sure = np.zeros(n)
    vb_tepe = np.zeros(n); i2t_kol = np.zeros(n)
    for _ in range(int(t_son / dt)):
        v_uc = v_a + esr * (i_w - i_l)
        i_w += dt * (voc - r_src * i_w - v_uc) / l_w
        i_l = np.maximum(i_l + dt * (v_uc - T.MT3608_DCR * i_l - T.MT3608_DIYOT_VF - v_b) / T.MT3608_L, 0.0)
        v_a += dt * (i_w - i_l) / c_in
        v_b += dt * (i_l - v_b / r_yuk) / c_bus
        vcs = i_w * rds_cift
        i_tepe = np.maximum(i_tepe, i_w)
        vcs_tepe = np.maximum(vcs_tepe, vcs)
        vcs_sure += dt * (vcs > T.DW01_VSIP[0])
        vb_tepe = np.maximum(vb_tepe, v_b)
        i2t_kol += dt * (i_w / 2) ** 2               # iki kol paralel: kol basina yarisi
    return i_tepe, vcs_tepe, vcs_sure, vb_tepe, i2t_kol


def bolum1(r):
    bolum(r, "1. ANAHTAR KAPANIS ANI (mikrosaniye) — DW01A kisa devre algilamasi")
    r.bilgi("  PIL anahtari kapaninca MT1'in 22 uF giris seramigi dogrudan pilden dolar;")
    r.bilgi("  sonra MT1'in bobini + diyodu uzerinden 5 V barasi da (anahtarlama henuz yok).")
    r.bilgi("  DW01A bu darbeyi 'kisa devre' sanabilir: V_CS = I x 2 Rds > VSIP (min 1.00 V)")
    r.bilgi("  ve ~5 us surerse paketi KESER ve yuk kalkana kadar acmaz.")
    r.bilgi("")
    # en kotu darbe: dolu hucre, en dusuk direnc (yeni hucre, soguk FET)
    kombin = [(lw, kose, cb) for lw in T.PAKET_KABLO_L for kose in (0, 1) for cb in T.BARA_5V_C]
    voc = [T.HUCRE_V_UST] * len(kombin)
    rds_c = [2 * float(rds(T.HUCRE_V_UST, k)) for _, k, _ in kombin]
    r_src = [T.HUCRE_IC_DIRENC_ALT / 2 + T.SIGORTA_2A_R / 2 + rc + T.PAKET_KABLO_R * 0.4
             for rc in rds_c]                         # anahtar + tel: kisa kablo (alt uc)
    i_tepe, vcs_tepe, vcs_sure, vb_tepe, i2t = darbe_benzet(
        voc, r_src, [k[0] for k in kombin], [k[2] for k in kombin], rds_c)
    for j, (lw, kose, cb) in enumerate(kombin):
        r.bilgi(f"    L={lw * 1e9:3.0f} nH  Rds {'tip ' if kose == 0 else 'maks'}  C_bara={cb * 1e6:2.0f} uF: "
                f"I tepe {i_tepe[j]:5.1f} A  V_CS {vcs_tepe[j]:.2f} V ({vcs_sure[j] * 1e6:4.2f} us > 1.00 V)  "
                f"bara tepe {vb_tepe[j]:.2f} V")
    r.bilgi("")
    sure_maks = float(vcs_sure.max())
    r.kosul("Acilis darbesi DW01A kisa devre esigini gecmiyor ya da gecikmesinden kisa",
            sure_maks < T.DW01_TOI2 / 2,
            f"V_CS > {T.DW01_VSIP[0]:.2f} V en fazla {sure_maks * 1e6:.2f} us (tipik gecikme "
            f"{T.DW01_TOI2 * 1e6:.0f} us, pay 2x) · tepe V_CS {vcs_tepe.max():.2f} V")
    i2t_maks = float(i2t.max())
    r.kosul("Darbe kol sigortalarini (2 A F) zorlamiyor",
            T.SIGORTA_2A_I2T_ALT / i2t_maks >= 10,
            f"kol basina I2t {i2t_maks * 1e3:.2f} mA2s, erime >= {T.SIGORTA_2A_I2T_ALT:.2f} A2s "
            f"(pay {T.SIGORTA_2A_I2T_ALT / i2t_maks:.0f}x)")
    vb = float(vb_tepe.max())
    r.kosul("Dogrudan gecis tepesi B0505S giris darbe sinirinin altinda",
            vb < T.IZOLE_GIRIS_DARBE,
            f"bara tepe {vb:.2f} V < {T.IZOLE_GIRIS_DARBE:.0f} V (1 s darbe siniri)")
    r.bilgi(f"    (Calisma araligi {T.IZOLE_GIRIS_ARALIK[1]:.1f} V'u {'ASIYOR' if vb > T.IZOLE_GIRIS_ARALIK[1] else 'asmiyor'}: "
            f"tepe {vb:.2f} V; darbe < 1 ms, veri sayfasinin 1 s'lik darbe sinirinin cok altinda.)")
    return {"vb_tepe": vb, "vcs_tepe": float(vcs_tepe.max())}


# ═══════════════════════════════════════════════════════════════════════
#  2-3. ACILIS VE KAPANIS — ortalanmis zaman benzetimi
# ═══════════════════════════════════════════════════════════════════════

KORUMA = {"A3": "sarkma; Royer surucu siniri 3x anma", "B15": "akim siniri 1.5x anma",
          "B11": "akim siniri 1.1x anma (Hi-Link'in garantisi)",
          "C": "hiccup: veri sayfasinin kapasitif yuk suresinden uzun asiri yukte kapan, 20 ms bekle"}


def senaryo(**kw) -> dict:
    s = dict(pw=1.0, kor="A3", egri="kotu", voc=3.7, paket="cift", ss=1e-3, ss_tip="ref",
             f1="F 400 mA", c_bus=T.BARA_5V_C[0], c_ek=0.0, r_o=0.0, grup="ana")
    s.update(kw)
    return s


def _param(sc: list[dict], t_ref: dict) -> dict:
    """Senaryo listesini benzetimin dizi parametrelerine cevir."""
    n = len(sc)
    P = {k: np.zeros(n) for k in ("voc", "hucre", "r_hucre", "pw", "ir", "r_out", "egri", "k_lim",
                                  "t_trip", "ss", "ss_akim", "r_f1", "c_bus", "c_ek", "esr_ek", "r_o")}
    for j, s in enumerate(sc):
        pw = s["pw"]
        ir = T.IZOLE_ANMA_AKIM.get(pw, pw / 5.0)
        kose = 1 if s["egri"] == "kotu" else 0
        hucre, r_h = {"cift": (2, T.HUCRE_IC_DIRENC), "tek": (1, T.HUCRE_IC_DIRENC),
                      "tek_yasli": (1, T.HUCRE_IC_DIRENC_YASLI),
                      "olu": (1, 1.5)}[s["paket"]]
        P["voc"][j] = s["voc"]; P["hucre"][j] = hucre; P["r_hucre"][j] = r_h
        P["pw"][j] = pw; P["ir"][j] = ir
        P["r_out"][j] = izole_r(pw, kose) if pw in T.IZOLE_ANMA_AKIM else 0.02
        P["egri"][j] = T.IZOLE_EGRI_10[0 if kose else 1]
        P["k_lim"][j] = s.get("k", {"A3": T.IZOLE_ASIRI_TAVAN, "B15": 1.5, "B11": T.IZOLE_KISA_SURELI,
                                    "C": T.IZOLE_ASIRI_TAVAN, "sert": np.inf}[s["kor"]])
        P["t_trip"][j] = s.get("t_trip", t_ref.get(pw, np.inf)) if s["kor"] == "C" else np.inf
        P["ss"][j] = s["ss"]
        P["ss_akim"][j] = s["ss_tip"] == "akim"
        P["r_f1"][j] = T.SIGORTA[s["f1"]][0] + 0.02
        P["c_bus"][j] = s["c_bus"]
        P["c_ek"][j] = s["c_ek"]
        P["esr_ek"][j] = T.MT2_GIRIS_ESR.get(s["c_ek"], 1.0) if s["c_ek"] else 1.0
        P["r_o"][j] = s.get("r_o", 0.0)
    return P


def acilis_benzet(sc: list[dict], c_kart: float, t_ref: dict, dt: float = 1e-6,
                  t_kapa: float = 0.22, t_son: float = 0.34, dt_kapali: float = 5e-6) -> dict:
    """Ortalanmis zaman benzetimi. Butun senaryolar ayni anda (numpy dizileri).

    MT3608: tepe akim kipli boost, ortalanmis. Yumusak baslama iki bicimde (veri sayfasi
    mekanizmayi soylemiyor): 'ref' = referans rampasi, UVLO'da sifirlanir (en kotu);
    'akim' = akim siniri rampasi. B0505S: Thevenin (egri + R_out) + koruma kolu.
    MT2 girisi: modulun 22 uF seramigi + istege bagli elektrolitik (ESR'siyle).

    ⚠ ADIM: acik fazda 1 us. 5 us'de DW01A sureleri 2.8 ms -> yakinsamis 21.9 ms (8x DUSUK) ve
    24 V suresi %50 sapiyordu — UVLO cirpinmasi kaba adimda yutuluyor. Kapanis 5 us yeter."""
    P = _param(sc, t_ref)
    n = len(sc)
    ir, r_out, k_lim, t_trip = P["ir"], P["r_out"], P["k_lim"], P["t_trip"]
    c_bo = T.MT3608_C
    c_ek = P["c_ek"]; ek_var = c_ek > 0
    c_es_ek = np.where(ek_var, c_bo * c_ek / (c_bo + np.where(ek_var, c_ek, 1.0)), 0.0)
    c24 = T.MT3608_C * T.MT3608_C_24V_ETKIN
    c_k = c_kart
    eta = T.MT3608_VERIM
    tau_c = 50e-6                                        # MT3608 dongu zaman sabiti (~3 kHz)
    uvlo_on, uvlo_off = T.MT3608_UVLO, T.MT3608_UVLO - T.MT3608_UVLO_HIST
    i_kart_tam = T.RAY24_AKIM_KOTU + T.PANEL_LED_AKIM
    ss_akim = P["ss_akim"] > 0
    voc = P["voc"]
    r_pk = (P["r_hucre"] / P["hucre"] + T.SIGORTA_2A_R / P["hucre"]
            + 2 * rds(voc, 1) * T.FS8205_ACILIS + T.PAKET_KABLO_R)
    r_pt = r_pk + T.MT3608_DCR
    c_es2 = c_bo * c24 / (c_bo + c24)
    c_es_f1 = c24 * c_k / (c24 + c_k)

    def katsayi(h):
        """Ustel aktarim katsayilari (iki kondansator arasi R): adimdan bagimsiz kararli."""
        return (np.where(ek_var, 1 - np.exp(-h / np.maximum(P["esr_ek"] * c_es_ek, 1e-12)), 0.0),
                1 - np.exp(-h / (r_pt * P["c_bus"])),
                1 - np.exp(-h / (T.MT3608_DCR * c_es2)),
                1 - np.exp(-h / (P["r_f1"] * c_es_f1)))
    a_ek, a_pt1, a_pt2, a_f1 = katsayi(dt)
    dt_acik = dt

    v_bus = np.zeros(n); v_bo = np.zeros(n); v_ek = np.zeros(n); v24 = np.zeros(n); v_c = np.zeros(n)
    v_pk_onceki = voc.copy()
    en1 = np.zeros(n, bool); en2 = np.zeros(n, bool); iz_on = np.zeros(n, bool)
    ss1 = np.zeros(n); ss2 = np.zeros(n)
    t_boot = np.full(n, np.inf); sifirlanma = np.zeros(n)
    ovl = np.zeros(n); kapali_bitis = np.full(n, -1.0); hiccup = np.zeros(n)
    i_bi = np.zeros(n)
    O = {k: np.zeros(n) for k in ("i_pk_maks", "oc_kosu", "oc_maks", "oc_tip_kosu", "oc_tip_maks",
                                  "od_kosu", "od_maks", "i2t_f0", "i_f0_maks", "i2t_f1",
                                  "iz_ovl", "iz_maks", "uvlo2")}
    for k in ("vpk_min", "vbus_min", "vbi_min_iz"):
        O[k] = np.full(n, 9.0)
    t24 = np.full(n, np.inf)
    dur = {}
    t_esp_olu = np.full(n, np.inf); t_ray_olu = np.full(n, np.inf)
    esik_kotu = dw01_oc_akim(voc, True, T.FS8205_ACILIS)
    esik_tip = dw01_oc_akim(voc, False)

    t, anlik_alindi = 0.0, False
    while t < t_son:
        acik = t < t_kapa
        if not acik and dt != dt_kapali:
            dt = dt_kapali
            a_ek, a_pt1, a_pt2, a_f1 = katsayi(dt)
        # ── ESP32 (devkit LDO'su 5 V barasindan) ─────────────────────
        v3 = np.clip(v_bus - T.ESP32_LDO_DUSUM, 0.0, 3.3)
        t_boot = np.where((v3 >= 3.0) & ~np.isfinite(t_boot), t, t_boot)
        dustu = np.isfinite(t_boot) & (v3 < T.ESP32_BROWNOUT)
        if acik:
            sifirlanma += dustu
        t_boot = np.where(dustu, np.inf, t_boot)
        faz = np.where(np.isfinite(t_boot), t - t_boot, -1.0)
        patlama = (faz > 20e-3) & (np.mod(np.maximum(faz, 0.0), 5e-3) < 2e-3)
        i_esp = np.where(v3 < 2.0, v_bus / 200.0,
                         np.where(faz < 20e-3, 0.08,
                                  np.where(patlama, T.ESP32_5V_TEPE, T.ESP32_5V_AKIM_TIPIK)))
        i_k5 = np.where(v_bus > 2.0, T.KART_5V_AKIM, 0.0)

        # ── B0505S ────────────────────────────────────────────────────
        v_bi = np.maximum(v_bus - T.SIGORTA_1A_R * i_bi, 0.0)
        iz_on = np.where(v_bi >= T.IZOLE_BASLAMA_V, True,
                         np.where(v_bi < T.IZOLE_BASLAMA_V - 0.5, False, iz_on))
        calisir = iz_on & (t >= kapali_bitis)
        v_oc = 5.0 * P["egri"] * (v_bi / 5.0) ** T.IZOLE_HAT_REG + r_out * 0.1 * ir
        # B0505S cikisi -> (istege bagli seri direnc R_o) -> MT2 girisi (seramik + elektrolitik)
        i_iz = np.where(calisir, np.clip((v_oc - v_bo) / (r_out + P["r_o"]), 0.0, k_lim * ir), 0.0)
        ovl = np.where(calisir & (i_iz > ir), ovl + dt, 0.0)
        tetik = ovl > t_trip
        kapali_bitis = np.where(tetik, t + T.IZOLE_HICCUP_KAPALI, kapali_bitis)
        hiccup += tetik
        ovl = np.where(tetik, 0.0, ovl)
        i_iz = np.where(tetik, 0.0, i_iz)
        i_bi = np.where(calisir & ~tetik,
                        T.IZOLE_BOSTA_AKIM + v_oc * i_iz / (T.IZOLE_VERIM * np.maximum(v_bi, 0.5)), 0.0)

        # ── MT2 girisi: seramik + elektrolitik (ESR) ─────────────────
        q_ek = (v_ek - v_bo) * c_es_ek * a_ek

        # ── MT2 (B0505S cikisindan 24 V) ─────────────────────────────
        onceki = en2
        en2 = np.where(v_bo >= uvlo_on, True, np.where(v_bo < uvlo_off, False, en2))
        O["uvlo2"] += onceki & ~en2
        ss2 = np.where(en2, ss2 + dt, 0.0)
        rampa = np.minimum(1.0, ss2 / P["ss"])
        vref2 = np.where(ss_akim, 24.0, 24.0 * rampa)
        lim2 = np.where(ss_akim, T.MT3608_GIRIS_SINIR * rampa, T.MT3608_GIRIS_SINIR)
        q_f1 = (v24 - v_c) * c_es_f1 * a_f1
        i_f1 = q_f1 / dt
        dv2 = v_bo - T.MT3608_DIYOT_VF - v24
        q_pt2 = np.where(dv2 > 0, dv2 * c_es2 * a_pt2, 0.0)
        i_ist2 = np.maximum(i_f1 + c24 * (vref2 - v24) / tau_c, 0.0)
        i_in2 = np.where(en2, v24 * i_ist2 / (eta * np.maximum(v_bo, 0.3)), 0.0)
        i_in2 = np.minimum(i_in2, lim2)
        tavan = (v_bo - i_in2 * T.MT3608_DCR) / (1 - T.MT3608_DMAX)
        i_in2 = np.where(v24 < tavan, i_in2, 0.0)
        # tek adimda seramigi eksiye cekemez: bu adimda verilebilecek yuk kadar
        i_in2 = np.minimum(i_in2, (v_bo * c_bo + q_ek) / dt + i_iz)
        i_out2 = i_in2 * eta * v_bo / np.maximum(v24, 0.5)

        # ── MT1 (paketten 5 V barasi) ────────────────────────────────
        i_bara = i_esp + i_k5 + i_bi
        dv1 = voc - T.MT3608_DIYOT_VF - v_bus
        q_pt1 = np.where(acik & (dv1 > 0), dv1 * P["c_bus"] * a_pt1, 0.0)
        i_pt1 = q_pt1 / dt
        vs = voc - r_pk * i_pt1
        # UVLO MT1'in IN pininde (= paket terminali, bir onceki adim): kaynak cokerse kapanir
        en1 = acik & np.where(v_pk_onceki >= uvlo_on, True, np.where(v_pk_onceki < uvlo_off, False, en1))
        ss1 = np.where(en1, ss1 + dt, 0.0)
        vref1 = 5.0 * np.minimum(1.0, ss1 / P["ss"])
        i_ist1 = np.maximum(i_bara + P["c_bus"] * (vref1 - v_bus) / tau_c - i_pt1, 0.0)
        p1 = v_bus * i_ist1 / eta
        disk = vs * vs - 4 * r_pk * p1
        i_b1 = np.where(disk >= 0, (vs - np.sqrt(np.maximum(disk, 0))) / (2 * r_pk), vs / (2 * r_pk))
        i_b1 = np.where(en1, np.minimum(i_b1, T.MT3608_GIRIS_SINIR), 0.0)
        v_pk = vs - r_pk * i_b1
        i_o1 = i_b1 * v_pk * eta / np.maximum(v_bus, 0.5)
        i_pk = np.where(acik, i_b1 + i_pt1, 0.0)
        v_pk_onceki = np.where(acik, v_pk, voc)

        i_kart = i_kart_tam * np.minimum(1.0, v_c / 5.0)

        # ── Olcumler ─────────────────────────────────────────────────
        if acik:
            if t > 1e-3:                               # anahtar ani darbesi bolum 1'de (L'li model)
                O["i_pk_maks"] = np.maximum(O["i_pk_maks"], i_pk)
            O["oc_kosu"] = np.where(i_pk > esik_kotu, O["oc_kosu"] + dt, 0.0)
            O["oc_maks"] = np.maximum(O["oc_maks"], O["oc_kosu"])
            O["oc_tip_kosu"] = np.where(i_pk > esik_tip, O["oc_tip_kosu"] + dt, 0.0)
            O["oc_tip_maks"] = np.maximum(O["oc_tip_maks"], O["oc_tip_kosu"])
            O["od_kosu"] = np.where(v_pk < T.DW01_VODP[2], O["od_kosu"] + dt, 0.0)
            O["od_maks"] = np.maximum(O["od_maks"], O["od_kosu"])
            O["vpk_min"] = np.minimum(O["vpk_min"], v_pk)
            pencere = ~np.isfinite(t24) | (t < t24 + 5e-3)
            O["i2t_f0"] += dt * i_bi ** 2 * pencere
            O["i_f0_maks"] = np.maximum(O["i_f0_maks"], i_bi)
            O["i2t_f1"] += dt * i_f1 ** 2 * pencere
            O["iz_ovl"] += dt * (i_iz > ir)
            O["iz_maks"] = np.maximum(O["iz_maks"], i_iz / ir)
            son_boot = faz > 1e-3
            O["vbus_min"] = np.where(son_boot, np.minimum(O["vbus_min"], v_bus), O["vbus_min"])
            O["vbi_min_iz"] = np.where(calisir & np.isfinite(t24) & (t > t24 + 5e-3),
                                       np.minimum(O["vbi_min_iz"], v_bi), O["vbi_min_iz"])
            t24 = np.where((v_c >= 23.5) & ~np.isfinite(t24), t, t24)
            if not anlik_alindi and t >= t_kapa - 1e-3:
                anlik_alindi = True
                dur = {"v_bus": v_bus.copy(), "v24": v24.copy(), "v_c": v_c.copy(), "i_pk": i_pk.copy(),
                       "iz_yuk": (v_bo * i_iz) / P["pw"], "v_bo": v_bo.copy(), "v_pk": v_pk.copy(),
                       "v_bi": v_bi.copy()}
        else:
            t_esp_olu = np.where((v3 < T.ESP32_BROWNOUT) & ~np.isfinite(t_esp_olu), t - t_kapa, t_esp_olu)
            t_ray_olu = np.where((v_c < 12.0) & ~np.isfinite(t_ray_olu), t - t_kapa, t_ray_olu)

        # ── Durum guncelle ───────────────────────────────────────────
        v_bus = np.maximum(v_bus + dt * (i_o1 - i_bara) / P["c_bus"] + q_pt1 / P["c_bus"], 0.0)
        v_bo = np.maximum(v_bo + dt * (i_iz - i_in2) / c_bo - q_pt2 / c_bo + q_ek / c_bo, 0.0)
        v_ek = np.where(ek_var, np.maximum(v_ek - q_ek / np.where(ek_var, c_ek, 1.0), 0.0), 0.0)
        v24 = np.maximum(v24 + dt * i_out2 / c24 + q_pt2 / c24 - q_f1 / c24, 0.0)
        v_c = np.maximum(v_c + q_f1 / c_k - dt * i_kart / c_k, 0.0)
        t += dt

    O.update(t24=t24, sifirlanma=sifirlanma, hiccup=hiccup, dur=dur,
             t_esp_olu=t_esp_olu, t_ray_olu=t_ray_olu)
    return O


def kapasitif_referans(pw: float) -> float:
    """Veri sayfasi: B0505S tam yukte, cikisinda IZOLE_C_AZAMI (2400 uF) varken baslayabiliyor.
    Ayni Thevenin modeliyle o testin ASIRI YUK suresi (akim > anma) — modulun en az bu kadar
    asiri yuke dayandigi veri sayfasindan TURETILEN alt sinir (hiccup kolunun tetik suresi)."""
    r_o = izole_r(pw, 1)
    ir = T.IZOLE_ANMA_AKIM[pw]
    v_oc = float(izole_voc(pw, 0, r_o, 5.0))
    r_yuk = 5.0 / ir
    dt, v, sure = 2e-6, 0.0, 0.0
    for _ in range(int(0.5 / dt)):
        i = (v_oc - v) / r_o
        sure += dt * (i > ir)
        v += dt * (i - v / r_yuk) / T.IZOLE_C_AZAMI
    return sure


# Kullanilabilir pil araligi. "tek" = paralel paketin tek hucreyle calismasi (bir sigorta atmis ya da
# hucre cikarilmis). BOS pil (3.0 V, tek yaslanmis hucre) ayrica: orada acilmamak BEKLENEN davranis.
PIL_DURUMU = ((4.2, "cift"), (3.7, "cift"), (3.3, "cift"), (3.3, "tek"))
K_TARAMA = (1.5, 2.0, 2.5, 3.0)


def senaryolar() -> list[dict]:
    """PLAN (2 W + MT2 giris kondansatoru) x bilinmeyenler; B0505S asiri yuk kati taramasi;
    F1 alt matrisi; neden-boyle negatif kontrolleri."""
    s = []
    pw, c_ek = max(T.IZOLE_GUC_SECENEK), T.MT2_GIRIS_C
    for kor in KORUMA:
        for egri in ("kotu", "tip"):
            for ss in T.MT3608_SS:
                for ss_tip in ("ref", "akim"):
                    for voc, paket in PIL_DURUMU:
                        s.append(senaryo(pw=pw, kor=kor, egri=egri, ss=ss, ss_tip=ss_tip, voc=voc,
                                         paket=paket, c_ek=c_ek))
    # B0505S asiri yukte anmanin kac katini verirse DW01A (tipik) keser?
    for k in K_TARAMA:
        for egri in ("kotu", "tip"):
            for ss in T.MT3608_SS:
                for ss_tip in ("ref", "akim"):
                    for voc in (3.7, 3.3):
                        s.append(senaryo(pw=pw, kor="A3", k=k, egri=egri, ss=ss, ss_tip=ss_tip, voc=voc,
                                         c_ek=c_ek, grup="k"))
    # YEDEK YOL: B0505S +Vo ile MT2 girisi arasina seri direnc (10.5'teki belirtiye gore takilir)
    # ⚠ iki egri de: 'tipik' egri daha yuksek V_oc = daha cok akim; ilk surum yalniz 'kotu'
    # egriyi tariyordu ve 1 ohm'luk direnci de "yeter" sayiyordu (mutasyon kacti). Tarama:
    # A3'te 0.5/1/2 ohm YETMIYOR (DW01A 27–33 ms), 3 ohm yetiyor.
    for kor in ("A3", "B11", "C"):
        for egri in ("kotu", "tip"):
            for ss in T.MT3608_SS:
                for ss_tip in ("ref", "akim"):
                    for voc, paket in ((3.7, "cift"), (3.3, "cift"), (3.3, "tek")):
                        s.append(senaryo(pw=pw, kor=kor, egri=egri, ss=ss, ss_tip=ss_tip, voc=voc,
                                         paket=paket, c_ek=c_ek, r_o=T.MT2_SERI_R_YEDEK, grup="yedek"))
    # BOS PIL: tek yaslanmis hucre, 3.0 V — bilgi
    for kor in KORUMA:
        s.append(senaryo(pw=pw, kor=kor, voc=3.0, paket="tek_yasli", c_ek=c_ek, grup="bos"))
    # F1 darbesi: en guclu B0505S + en hizli rampa en kotusu
    for ss in (T.MT3608_SS[0], T.MT3608_SS[-1]):
        for f1 in ("F 400 mA", "F 50 mA", "T 50 mA"):
            s.append(senaryo(pw=pw, kor="A3", egri="tip", voc=4.2, ss=ss, f1=f1, c_ek=c_ek,
                             c_bus=T.BARA_5V_C[1], grup="f1"))
    # NEDEN BOYLE — tasarim kararlarini ve dedektorleri sinayan bozuk senaryolar
    s.append(senaryo(pw=pw, kor="A3", ss=1e-3, ss_tip="ref", c_ek=0.0, grup="neg_kondansatorsuz"))
    s.append(senaryo(pw=min(T.IZOLE_ANMA_AKIM), kor="B15", ss=1e-3, ss_tip="akim", c_ek=c_ek, grup="neg_1w"))
    s.append(senaryo(pw=pw, kor="C", t_trip=0.5e-3, ss=1e-3, c_ek=c_ek, grup="neg_hiccup"))
    s.append(senaryo(pw=pw, kor="A3", egri="tip", voc=3.0, paket="olu", ss=1e-3, c_ek=c_ek, grup="neg_brownout"))

    return s


def bolum2(r, c_kart: float):
    bolum(r, "2. ACILIS (milisaniye) — PIL anahtari kapaninca butun zincir")
    t_ref = {pw: kapasitif_referans(pw) for pw in T.IZOLE_ANMA_AKIM}
    r.bilgi("  B0505S'in asiri yuke dayanma suresi veri sayfasinda YOK. Alt siniri su tanimdan:")
    r.bilgi(f"  modul {T.IZOLE_C_AZAMI * 1e6:.0f} uF + tam yukle baslayabiliyor (Mornsun). O testte anmanin ustunde:")
    for pw, t in t_ref.items():
        r.bilgi(f"    {pw:.0f} W: {t * 1e3:5.1f} ms  -> hiccup kolu (C) bundan uzun asiri yukte kapanir, 20 ms bekler")
    r.bilgi(f"  Kart kapasitesi (C16 + C17, netlist) = {c_kart * 1e6:.0f} uF. MT2 girisi: 22 uF seramik + "
            f"{T.MT2_GIRIS_C * 1e6:.0f} uF elektrolitik ({T.MT2_GIRIS_STOK}, ESR {T.MT2_GIRIS_ESR[T.MT2_GIRIS_C]} ohm).")
    r.bilgi("  Yumusak baslama iki bicimde: 'ref' referans rampasi (UVLO'da sifirlanir) / 'akim' akim rampasi.")
    r.bilgi("  ESP32 WiFi patlamalari acilistan 20 ms sonra basliyor (gercekte ~300 ms — KOTU varsayim).")
    sc = senaryolar()
    t0 = time.time()
    O = acilis_benzet(sc, c_kart, t_ref)
    r.bilgi(f"  {len(sc)} senaryo, {time.time() - t0:.0f} s.")
    r.bilgi("")
    return sc, O, t_ref


def _sec(sc, **kw):
    return np.array([all(s.get(k) == v for k, v in kw.items()) for s in sc])


def bolum2_iddia(r, sc, O, t_ref, c_kart):
    ana = _sec(sc, grup="ana")
    r.bilgi("  PLAN (2 W + MT2 girisinde elektrolitik) — her satir kombinasyonun EN KOTU yumusak baslama/egrisi:")
    r.bilgi("    koruma  Voc  paket       24V'a(ms)  bara min  I_pk maks  DW01 tip(ms)  kotu(ms)  B0505S>anma(ms)  hiccup")
    for kor in KORUMA:
        for voc, paket in PIL_DURUMU:
            m = ana & _sec(sc, kor=kor, voc=voc, paket=paket)
            t24 = O["t24"][m].max()
            r.bilgi(f"    {kor:5}  {voc:4.1f}  {paket:10}  "
                    f"{'YOK' if not np.isfinite(t24) else f'{t24 * 1e3:6.1f}':>9}  "
                    f"{O['vbus_min'][m].min():7.2f}  {O['i_pk_maks'][m].max():8.2f}  "
                    f"{O['oc_tip_maks'][m].max() * 1e3:11.1f}  {O['oc_maks'][m].max() * 1e3:8.1f}  "
                    f"{O['iz_ovl'][m].max() * 1e3:14.1f}  {O['hiccup'][m].max():5.0f}")
    r.bilgi("")
    t24 = O["t24"][ana]
    gelmeyen = [sc[j] for j in np.where(ana & ~np.isfinite(O["t24"]))[0]]
    r.kosul("PLAN: her modelde kart 24 V'a ulasiyor (23.5 V)",
            np.isfinite(t24).all(),
            f"{int(np.isfinite(t24).sum())}/{len(t24)} kol, en gec "
            f"{np.nanmax(np.where(np.isfinite(t24), t24, np.nan)) * 1e3:.0f} ms" if np.isfinite(t24).any()
            else "hicbiri", )
    if gelmeyen:
        r.bilgi(f"    GELMEYEN: {sorted({(s['kor'], s['egri'], s['ss'], s['ss_tip'], s['voc']) for s in gelmeyen})[:6]}")
    r.kosul("PLAN: ESP32 acilista hicbir kolda sifirlanmiyor (5 V barasi >= brownout + LDO)",
            (O["sifirlanma"][ana] == 0).all() and O["vbus_min"][ana].min() >= T.ESP32_BROWNOUT + T.ESP32_LDO_DUSUM,
            f"bara en dusuk {O['vbus_min'][ana].min():.2f} V (sinir {T.ESP32_BROWNOUT + T.ESP32_LDO_DUSUM:.1f} V)")
    c_top = T.MT3608_C + T.MT2_GIRIS_C + T.MT3608_C * T.MT3608_C_24V_ETKIN + c_kart
    r.kosul("PLAN: B0505S'in gordugu toplam kapasite veri sayfasi sinirinin altinda",
            c_top < T.IZOLE_C_AZAMI,
            f"{c_top * 1e6:.0f} uF < {T.IZOLE_C_AZAMI * 1e6:.0f} uF (MT2 dogrudan gecisiyle kart dahil)")
    dolu = ana & _sec(sc, voc=4.2)
    r.kosul("PLAN: DOLU pilde (4.2 V) dort B0505S modelinin hicbirinde DW01A (tipik) acilista kesmiyor",
            O["oc_tip_maks"][dolu].max() < T.DW01_TOI1_ALT,
            f"tipik esik ustunde en uzun {O['oc_tip_maks'][dolu].max() * 1e3:.1f} ms < {T.DW01_TOI1_ALT * 1e3:.0f} ms "
            f"(esik {float(dw01_oc_akim(4.2, False)):.2f} A)")
    # Tek hucre + guclu modul + yarim pil koseside hucre 2.5 V'un altina ~30 ms iniyor: o hal
    # 'kutu acilmazsa -> doldur' yordamina dusuyor (bilgi). Iddia plani normal kullanimi: iki hucre.
    tek = ana & _sec(sc, paket="tek")
    r.bilgi(f"    tek hucre (3.3 V): hucre < {T.DW01_VODP[2]:.2f} V en fazla {O['od_maks'][tek].max() * 1e3:.0f} ms "
            f"(DW01A tipik gecikme {T.DW01_TOD * 1e3:.0f} ms) — kesebilir, 10.5 / KULLANIM yordami")
    saglam = ana & np.array([s["voc"] >= 3.3 and s["paket"] == "cift" for s in sc])
    r.kosul("PLAN: iki hucre, pil >= 3.3 V iken acilis DW01A asiri desarj kesmesini tetiklemiyor",
            O["od_maks"][saglam].max() < T.DW01_TOD / 2,
            f"V_hucre < {T.DW01_VODP[2]:.2f} V en fazla {O['od_maks'][saglam].max() * 1e3:.1f} ms "
            f"(gecikme tipik {T.DW01_TOD * 1e3:.0f} ms, pay 2x)")
    # F0: IEC 60127-2 sayfa 1 (F): %150'de >= 1 sa acmaz, %210'da <= 30 dk acar
    f0_maks = O["i_f0_maks"][ana].max()
    r.kosul("PLAN: F0 (1 A F) acilista %210'un altinda -> ms olcekli darbede acma bolgesine girmiyor",
            f0_maks < 2.1 * T.F0_SIGORTA,
            f"en buyuk {f0_maks:.2f} A = %{f0_maks / T.F0_SIGORTA * 100:.0f} (IEC 60127-2: %210'da bile "
            f"acma suresi dakikalar) · I2t {O['i2t_f0'][ana].max() * 1e3:.0f} mA2s")
    f1g = _sec(sc, grup="f1")
    for f1 in ("F 400 mA", "T 50 mA"):
        m = f1g & _sec(sc, f1=f1)
        i2t, erime = O["i2t_f1"][m].max(), T.SIGORTA[f1][1]
        r.kosul(f"PLAN: F1 ({f1}) gercek acilis darbesinde pay >= {T.SIGORTA_DARBE_PAYI:.0f}",
                erime / i2t >= T.SIGORTA_DARBE_PAYI,
                f"darbe {i2t * 1e3:.3f} mA2s, erime {erime * 1e3:.2f} mA2s -> pay {erime / i2t:.0f}x")
    m50 = f1g & _sec(sc, f1="F 50 mA")
    i2t50 = O["i2t_f1"][m50].max()
    r.bilgi(f"    F 50 mA (bilgi): gercek acilista pay {T.SIGORTA['F 50 mA'][1] / i2t50:.1f}x — kutu.py'nin "
            f"sert-kaynak hesabi (atar) hala en kotu hal.")
    # duragan hal: iki bagimsiz modelin capraz denetimi (kutu.besleme_butcesi)
    import kutu
    b = kutu.besleme_butcesi()
    d = O["dur"]
    j = int(np.where(ana & _sec(sc, kor="A3", egri="tip", voc=3.7, ss=T.MT3608_SS[1], ss_tip="ref"))[0][0])
    r.esit("Duragan: B0505S yuku (benzetim) = kutu.py butcesi", float(d["iz_yuk"][j]), b["iz_yuk"], 0.05)
    r.esit("Duragan: kart gerilimi", float(d["v_c"][j]), 24.0, 0.01, " V")
    r.esit("Duragan: 5 V barasi", float(d["v_bus"][j]), 5.0, 0.01, " V")
    vbi = d["v_bi"][saglam]
    r.kosul("Duragan: B0505S girisi veri sayfasi araliginda (4.5–5.5 V, pil >= 3.3 V)",
            vbi.min() >= T.IZOLE_GIRIS_ARALIK[0] and vbi.max() <= T.IZOLE_GIRIS_ARALIK[1],
            f"{vbi.min():.2f} … {vbi.max():.2f} V (F0 dusumu dahil, ESP32 WiFi tepesi anlarinda)")
    return {"t24_maks": float(np.nanmax(np.where(np.isfinite(t24), t24, np.nan)))}


def bolum2_dw01(r, sc, O):
    """DW01A asiri akim: B0505S asiri yukte anmanin kac katini veriyor — veri sayfasinda YOK."""
    r.bilgi("")
    r.bilgi("  DW01A ASIRI AKIM — acilista paket akimi B0505S'in asiri yuk davranisina bagli.")
    r.bilgi("  Mornsun R3 serisi 'buyuk kapasitif yukte CC kipinde normal acilis' diyor (akim sinirli);")
    r.bilgi("  sinirin kac kat oldugu yazmiyor. Tarama (sinir = k x anma), tipik esik ustunde en uzun sure:")
    km = _sec(sc, grup="k")
    kritik = float("inf")
    for k in K_TARAMA:
        satir = []
        for voc in (3.7, 3.3):
            tip = O["oc_tip_maks"][km & _sec(sc, k=k, voc=voc)].max()
            satir.append(f"{voc} V: {tip * 1e3:5.1f} ms")
            if tip >= T.DW01_TOI1_ALT:
                kritik = min(kritik, k)
        r.bilgi(f"    k={k:.1f}: {' · '.join(satir)} · paket tepe {O['i_pk_maks'][km & _sec(sc, k=k)].max():.2f} A")
    r.kosul("B0505S anmanin 2 katina kadar verirse DW01A (tipik) yarim pilde (>= 3.3 V) acilista kesmiyor",
            2.0 < kritik < float("inf"),
            f"kesme ilk k = {kritik:.1f} x anma'da basliyor (dedektor taramanin ust ucunda ISIRIYOR)"
            if np.isfinite(kritik) else "tarama hic kesme gostermedi — dedektor bozuk olabilir")
    ana = _sec(sc, grup="ana")
    kotu = O["oc_maks"][ana & _sec(sc, voc=3.7)].max()
    r.bilgi(f"  EN KOTU tolerans (VOIP {T.DW01_VOIP[0] * 1e3:.0f} mV + FS8205 Rds maks + {T.FS8205_ACILIS}x): "
            f"3.7 V'ta bile esik {kotu * 1e3:.0f} ms asiliyor — iki toleransin birlikte en uca dusmesi gerekir.")
    y = _sec(sc, grup="yedek")
    r.bilgi("")
    r.bilgi(f"  YEDEK YOL — B0505S +Vo ile MT2 girisi arasina {T.MT2_SERI_R_YEDEK:.0f} ohm ({T.MT2_SERI_R_STOK}, "
            f"{T.MT2_SERI_R_YEDEK:.0f} x 1 ohm 1 W seri): modulun akimini kendisi ne yaparsa yapsin sinirlar.")
    for kor in ("A3", "B11", "C"):
        m = y & _sec(sc, kor=kor)
        g = np.isfinite(O["t24"][m])
        r.bilgi(f"    {kor:4}: 24 V {int(g.sum())}/{int(m.sum())} · DW01A tipik esik ustunde en uzun "
                f"{O['oc_tip_maks'][m].max() * 1e3:.1f} ms")
    m = y & np.array([s["kor"] in ("A3", "B11") for s in sc])
    r.kosul("YEDEK YOL: guclu (3x) ve akim sinirli modelde 24 V geliyor ve DW01A (tipik) kesmiyor",
            np.isfinite(O["t24"][m]).all() and O["oc_tip_maks"][m].max() < T.DW01_TOI1_ALT,
            f"24 V {int(np.isfinite(O['t24'][m]).sum())}/{int(m.sum())}, DW01A en uzun "
            f"{O['oc_tip_maks'][m].max() * 1e3:.1f} ms")
    mc = y & _sec(sc, kor="C")
    r.bilgi(f"    ⚠ hiccup tipinde (C) yedek yol 24 V'u {int((~np.isfinite(O['t24'][mc])).sum())}/{int(mc.sum())} "
            f"kolda engelliyor -> belirtiye gore takilir, varsayilan DEGIL; o modul dolu pilde zaten acilir.")
    metin = _kapi_metni("10.5")
    r.kosul("10.5 iki belirtiyi ve cozumunu yaziyor (kullanici bana donmeden cozebilsin)",
            "açılmazsa" in metin and re.search(r"\bdoldur\b", metin) is not None and "1 Ω" in metin
            and "24 V gelmiyorsa" in metin,
            "kutu acilmazsa -> doldur / seri direnc; 24 V gelmiyorsa -> direnci cikar"
            if "açılmazsa" in metin else "10.5'te YOK")
    return kritik


def bolum2_neden(r, sc, O):
    """Tasarim kararlarinin gerekcesi: kararsiz halleri benzetim KIRMIZI goruyor mu."""
    bolum(r, "2b. NEDEN BOYLE — kararlarin gerekcesi (bu senaryolar BASARISIZ olmali)")
    j = {s["grup"]: i for i, s in enumerate(sc) if s["grup"].startswith("neg_")}
    d = O["dur"]
    jk = j["neg_kondansatorsuz"]
    r.kosul(f"MT2 girisinde elektrolitik YOKKEN (referans rampasi, 1 ms) kart 24 V'a CIKAMIYOR",
            not np.isfinite(O["t24"][jk]),
            f"kart {d['v_c'][jk]:.1f} V'ta takiliyor: MT2 girisini UVLO'ya cekip yumusak baslamayi "
            f"sifirliyor ({O['uvlo2'][jk]:.0f} kez)")
    j1 = j["neg_1w"]
    r.kosul("1 W modul (akim sinirli, 1.5x) kondansatorle bile kart 24 V'a CIKAMIYOR",
            not np.isfinite(O["t24"][j1]),
            f"kart {d['v_c'][j1]:.1f} V: MT2 girisi UVLO sinirinda, aktarilan guc ~ I_sinir x 2 V")
    r.bilgi(f"    Esik: kart 24 V'ta {24 * (T.RAY24_AKIM_KOTU + T.PANEL_LED_AKIM):.2f} W istiyor -> B0505S sinir "
            f"akimi >= {24 * (T.RAY24_AKIM_KOTU + T.PANEL_LED_AKIM) / T.MT3608_VERIM / (T.MT3608_UVLO + 0.1):.2f} A "
            f"olmali (1 W: anmanin "
            f"{24 * (T.RAY24_AKIM_KOTU + T.PANEL_LED_AKIM) / T.MT3608_VERIM / (T.MT3608_UVLO + 0.1) / T.IZOLE_ANMA_AKIM[1.0]:.1f}"
            f" kati — veri sayfasi garanti etmiyor; 2 W: "
            f"{24 * (T.RAY24_AKIM_KOTU + T.PANEL_LED_AKIM) / T.MT3608_VERIM / (T.MT3608_UVLO + 0.1) / T.IZOLE_ANMA_AKIM[2.0]:.1f} kati).")
    # DW01A dedektorunun isirdigi bolum 2'deki k taramasinda iddia ediliyor (kesme k <= 3'te
    # gorunmek ZORUNDA). Ayri bir "10 W sert modul" kontrolu anlamsizdi: paket MT1'i UVLO'ya
    # dusurup cirpindiriyor, akim hic kesintisiz esik ustunde kalmiyordu.
    r.kosul("Dedektor: 0.5 ms'de hiccup'a giren modul -> '24 V geliyor' KIRMIZI",
            not np.isfinite(O["t24"][j["neg_hiccup"]]),
            f"hiccup {O['hiccup'][j['neg_hiccup']]:.0f} kez")
    r.kosul("Dedektor: 1.5 ohm'luk olu paket -> brownout dedektoru tetikleniyor",
            O["sifirlanma"][j["neg_brownout"]] > 0 or O["vbus_min"][j["neg_brownout"]] < T.ESP32_BROWNOUT + T.ESP32_LDO_DUSUM,
            f"sifirlanma {O['sifirlanma'][j['neg_brownout']]:.0f}, bara min {O['vbus_min'][j['neg_brownout']]:.2f} V")


def bolum2_dusuk_pil(r, sc, O):
    m = _sec(sc, grup="bos")
    r.bilgi("")
    r.bilgi(f"  BOS PIL (tek yaslanmis hucre, 3.0 V): 24 V {int(np.isfinite(O['t24'][m]).sum())}/{int(m.sum())} kolda. "
            f"Paket MT1'in akimini tasiyamiyor, MT1 kendi UVLO'suna dusup cirpiniyor, ESP32 acilmiyor.")
    r.bilgi("  -> zararsiz (DW01A asiri desarjda keser); KULLANIM'daki 'once doldur' kurali bunun icin.")
    r.kosul("KULLANIM 'kutu acilmiyorsa pili doldur' diyor",
            # \b sart: ayni satirdaki "doldururken" desen "doldur"u tek basina karsiliyordu —
            # emir silinse bile yesil kaliyordu (mutasyon kacti, B58f).
            _kural_var(r"açılmıyorsa.*\bdoldur\b"), "bos pil davranisi kullaniciya yazili")


def bolum3(r, sc, O):
    bolum(r, "3. KAPANIS — PIL kapaninca raylar hangi sirayla sonuyor")
    ana = _sec(sc, grup="ana")
    esp, ray = O["t_esp_olu"][ana], O["t_ray_olu"][ana]
    r.bilgi(f"  ESP32 (3V3 < {T.ESP32_BROWNOUT} V): {np.nanmin(esp) * 1e3:.1f} … {np.nanmax(esp) * 1e3:.1f} ms")
    r.bilgi(f"  Kart raylari (24 V < 12 V): {np.nanmin(ray) * 1e3:.1f} … {np.nanmax(ray) * 1e3:.1f} ms")
    pencere = np.maximum(ray - esp, 0.0)
    r.bilgi(f"  +-12 acik / +3V3 kapali penceresi: en fazla {pencere.max() * 1e3:.0f} ms")
    r.kosul("Kapanis tamamlaniyor: iki taraf da 150 ms icinde sonuyor",
            np.isfinite(esp).all() and np.isfinite(ray).all() and max(esp.max(), ray.max()) < 0.15,
            f"ESP32 {esp.max() * 1e3:.0f} ms, raylar {ray.max() * 1e3:.0f} ms")
    r.bilgi("  Bu pencere B18'in SURESIZ guvenli buldugu hal (R26/R33 10K + R41 1K bosaltma, pay 1930 mV)")
    r.bilgi("  — sure onemli degil, yalnizca varligi. B58 oncesinde '24 V tak / USB cek' sirasi bu hali")
    r.bilgi("  SAATLERCE uretebiliyordu; simdi en fazla yukaridaki kadar.")


# ═══════════════════════════════════════════════════════════════════════
#  4. YALNIZ USB — PIL kapali, ESP32'nin USB'si PC'de
# ═══════════════════════════════════════════════════════════════════════

def usb_duragan(vbus: float, r_kablo: float, vf: float, i_esp: float) -> tuple[float, float, bool]:
    """PIL kapali; butun yuk USB'den. Donus (bara V, USB akimi A, B0505S calisir mi)."""
    p_iz_giris = 24.0 * (T.RAY24_AKIM_KOTU + T.PANEL_LED_AKIM) / T.MT3608_VERIM / T.IZOLE_VERIM
    v = vbus - vf
    for _ in range(60):
        i_iz = T.IZOLE_BOSTA_AKIM + p_iz_giris / max(v - T.SIGORTA_1A_R * 0.2, 1.0)
        calisir = v >= T.IZOLE_BASLAMA_V
        i = i_esp + T.KART_5V_AKIM + (i_iz if calisir else 0.0)
        v = vbus - vf - r_kablo * i
    return v, i, v >= T.IZOLE_BASLAMA_V


def bolum4(r):
    bolum(r, "4. YALNIZ USB (PIL kapali, ESP32'nin USB'si PC'de)")
    r.bilgi("  Devkit'in 5V pini 5 V barasina bagli: PIL kapaliyken USB takilirsa MT1'in cikisi")
    r.bilgi("  uzerinden B0505S + MT2 + kart da USB'den beslenmeye calisir.")
    satir = []
    for vbus in T.USB_VBUS:
        for rk in T.USB_KABLO_R:
            for vf in (T.USB_DIYOT_VF, 0.0):
                for i_esp in (T.ESP32_5V_AKIM_TIPIK, T.ESP32_5V_AKIM_KOTU):
                    v, i, cal = usb_duragan(vbus, rk, vf, i_esp)
                    satir.append((vbus, rk, vf, i_esp, v, i, cal))
    i_tip = min(s[5] for s in satir if s[3] == T.ESP32_5V_AKIM_TIPIK and s[6])
    i_max = max(s[5] for s in satir)
    calismayan = [s for s in satir if not s[6]]
    r.bilgi(f"    USB akimi: {i_tip * 1e3:.0f} … {i_max * 1e3:.0f} mA (USB 2.0 siniri {T.USB2_AKIM * 1e3:.0f} mA)")
    r.bilgi(f"    B0505S girisi {T.IZOLE_BASLAMA_V} V'un altina dusen kol: {len(calismayan)}/{len(satir)}")
    kural = _kural_usb()
    r.kosul("Yalniz USB'de akim USB 2.0 sinirini asabiliyor -> 'USB'yi takarken PIL acik' kurali GEREKLI",
            i_max > T.USB2_AKIM * 0.8 and kural,
            f"en kotu {i_max * 1e3:.0f} mA · kural KULLANIM'da {'VAR' if kural else 'YOK'}")
    r.kosul("11.2'nin 'PIL kapaliyken USB' sayisi benzetimle tutarli",
            _usb_metin_tutarli(i_tip, i_max),
            f"metin ~0.35 A diyor; benzetim tipik {i_tip:.2f} A, en kotu {i_max:.2f} A")
    # PIL acik + USB: USB akimi paylasiyor mu
    r.bilgi("  PIL ACIK + USB: MT1 5.0 V; USB tarafi VBUS - Vf. Diyot (klonda yoksa 10.5'te SR5100):")
    for vbus in T.USB_VBUS:
        fark = vbus - T.USB_DIYOT_VF - 5.0
        r.bilgi(f"    VBUS {vbus:.2f} V: USB tarafi {vbus - T.USB_DIYOT_VF:.2f} V -> "
                f"{'USB yuk paylasir (zararsiz, geri besleme yok)' if fark > 0 else 'diyot ters, USB akim vermez'}")
    # 10.5: klon devkit'te VBUS diyodu yoksa SR5100 + MT1 yukseltilir. B0505S'in girisi MT1'in
    # cikisinda (F0 uzerinden, diyottan ONCE) -> 5.5 V sinirini asmamali.
    m = re.search(r"MT1'i <b>(\d+[.,]\d+) V</b>'a çıkar", _kapi_metni("10.5"))
    v_sr = float(m.group(1).replace(",", ".")) if m else None
    r.kosul("10.5'in SR5100 yolunda (MT1 yukseltilmis) B0505S girisi hala veri sayfasi araliginda",
            v_sr is not None and v_sr + 0.05 <= T.IZOLE_GIRIS_ARALIK[1],
            f"MT1 {v_sr} V + 0.05 V ayar payi <= {T.IZOLE_GIRIS_ARALIK[1]} V" if v_sr is not None
            else "10.5'te MT1 ayari bulunamadi")
    return i_tip, i_max


def _kural_var(desen: str) -> bool:
    import kutu_veri as K
    for satir in K.KULLANIM:
        metin = " ".join(str(x) for x in (satir if isinstance(satir, (list, tuple)) else satir.values()))
        if re.search(desen, metin, re.S):
            return True
    return False


def _kural_usb() -> bool:
    return _kural_var(r"USB'yi PC'ye takarken PİL AÇIK")


def _usb_metin_tutarli(i_tip: float, i_max: float) -> bool:
    m = re.search(r"~(\d+[.,]\d+) A, USB 2\.0", _kapi_metni("11.2"))
    return bool(m) and i_tip * 0.85 <= float(m.group(1).replace(",", ".")) <= i_max * 1.05


# ═══════════════════════════════════════════════════════════════════════
#  5. PARALEL HUCRE DENGELEME — 10.3'teki kural
# ═══════════════════════════════════════════════════════════════════════

def bolum5(r):
    bolum(r, "5. PARALEL HUCRE DENGELEME — farkli gerilimde iki hucre takilirsa")
    r_dongu = 2 * T.HUCRE_IC_DIRENC_ALT + 2 * T.SIGORTA_2A_R + 0.02
    i_izin = T.HUCRE_SARJ_C_ORANI * T.HUCRE_KAPASITE_AH
    dv_izin = i_izin * r_dongu
    r.bilgi(f"  Dongu direnci (en kotu = en KUCUK): 2 x {T.HUCRE_IC_DIRENC_ALT * 1e3:.0f} mOhm hucre + "
            f"2 x {T.SIGORTA_2A_R * 1e3:.0f} mOhm sigorta + teller = {r_dongu * 1e3:.0f} mOhm")
    for dv in (0.05, 0.1, 0.2, 0.5, 1.2):
        i = dv / r_dongu
        r.bilgi(f"    fark {dv:4.2f} V -> {i:5.2f} A ({i / T.HUCRE_KAPASITE_AH:.1f} C) "
                f"{'— sigorta %' + format(i / T.PIL_KOL_SIGORTA * 100, '.0f') if i > T.PIL_KOL_SIGORTA else ''}")
    m = re.search(r"±\s*(\d+[.,]\d+)\s*V", _kapi_metni("10.3"))
    kural = float(m.group(1).replace(",", ".")) if m else None
    r.kosul("10.3'teki fark kurali hucrenin surekli sarj akimini asmiyor",
            kural is not None and kural <= dv_izin,
            f"kural ±{kural} V -> {kural / r_dongu:.2f} A <= {i_izin:.2f} A "
            f"({T.HUCRE_SARJ_C_ORANI} C) · izin verilen en buyuk fark {dv_izin:.2f} V"
            if kural is not None else "10.3'te ±x V kurali BULUNAMADI")
    i_bos_dolu = (T.HUCRE_V_UST - 3.0) / r_dongu
    r.bilgi(f"  Dolu + bos (1.2 V fark): {i_bos_dolu:.1f} A = kol sigortasinin %"
            f"{i_bos_dolu / T.PIL_KOL_SIGORTA * 100:.0f}'i -> sigorta atar (IEC %275: 10 ms–2 s),")
    r.bilgi("  hucre korunur; kural sigortanin atmasini ve hucreye asiri sarji onluyor.")


# ═══════════════════════════════════════════════════════════════════════
#  6. PIL ACIKKEN SARJ — 10.6'daki kural
# ═══════════════════════════════════════════════════════════════════════

def bolum6(r):
    bolum(r, "6. PIL ACIKKEN SARJ — 10.6'daki 'once PIL'i kapat' kurali")
    import kutu
    b = kutu.besleme_butcesi()
    p_tip, p_kotu = b["p_paket_tipik"], b["i5_kotu"] * 5.0 / T.MT3608_VERIM
    r.bilgi(f"  TP4056 {T.PIL_SARJ_AKIMI:.2f} A veriyor; yuk ayni dugumden cekiyor (paket gucu tipik "
            f"{p_tip:.2f} W, en kotu {p_kotu:.2f} W):")
    for v in (3.3, 3.7, 4.1):
        net_t = T.PIL_SARJ_AKIMI - p_tip / v
        net_k = T.PIL_SARJ_AKIMI - p_kotu / v
        r.bilgi(f"    hucre {v:.1f} V: hucrelere net {net_t:+.2f} A (tipik) / {net_k:+.2f} A (WiFi tepesi)")
    bitis = T.PIL_SARJ_AKIMI / 10
    r.bilgi(f"  TP4056 sarji akim {bitis * 1e3:.0f} mA'e dusunce bitirir; yuk {p_tip / 4.2 * 1e3:.0f} mA "
            f"cekerken bu esige HIC inmez -> hucreler 4.2 V'ta SURESIZ tutulur (yaslandirir).")
    metin = _kapi_metni("10.6")
    r.kosul("Sarj sirasinda yuk bitis esigini engelliyor -> 10.6 'PIL'i kapat' diyor",
            p_tip / 4.2 > bitis and "PİL anahtarını KAPAT" in metin,
            f"yuk {p_tip / 4.2 * 1e3:.0f} mA > bitis {bitis * 1e3:.0f} mA · kural "
            f"{'VAR' if 'PİL anahtarını KAPAT' in metin else 'YOK'}")


# ═══════════════════════════════════════════════════════════════════════
#  7. B0505S KAYNAKLI GURULTU
# ═══════════════════════════════════════════════════════════════════════

def bolum7(r, c_kart: float):
    bolum(r, "7. B0505S KAYNAKLI GURULTU — ray dalgalanmasi ve ortak mod akimi")
    c24 = T.MT3608_C * T.MT3608_C_24V_ETKIN
    en_kotu = 0.0
    for pw in T.IZOLE_GUC_SECENEK:
        f = T.IZOLE_FSW[pw] * 0.8                     # hafif yukte frekans kayar: dusuk uc
        w = 2 * math.pi * f
        d = 1 - 5.0 / 24.0
        g_mt2 = (1 - d) / (T.MT3608_L * c24 * w * w)   # acik cevrim boost hat -> cikis, w >> w0
        rc = 1 / (2 * math.pi * (T.SIGORTA['F 400 mA'][0] + 0.02) * c_kart)
        g_kart = rc / f
        v_ray = T.IZOLE_DALGALANMA[pw] * g_mt2 * g_kart
        en_kotu = max(en_kotu, v_ray)
        r.bilgi(f"    {pw:.0f} W: {T.IZOLE_DALGALANMA[pw] * 1e3:.0f} mVpp @ {f / 1e3:.0f} kHz -> MT2 cikisi "
                f"{T.IZOLE_DALGALANMA[pw] * g_mt2 * 1e6:.0f} uVpp -> kart raylari {v_ray * 1e6:.2f} uVpp "
                f"(F1 + {c_kart * 1e6:.0f} uF)")
    r.kosul("B0505S dalgalanmasinin raylara ulasan payi 10.5'in 50 mV olcutunun 1/1000'inden kucuk",
            en_kotu < 50e-3 / 1000, f"en kotu {en_kotu * 1e6:.2f} uVpp")
    i_cm = 2 * math.pi * max(T.IZOLE_FSW.values()) * T.IZOLE_BARIYER_C * 5.0
    r.bilgi(f"  Ortak mod: {T.IZOLE_BARIYER_C * 1e12:.0f} pF bariyerden ~{i_cm * 1e3:.2f} mA "
            f"({max(T.IZOLE_FSW.values()) / 1e3:.0f} kHz). Donus yolu J5 GND teli; ADS'ler kart GND'ye")
    r.bilgi("  gore olcuyor ve J5 GND'si ADS'nin analog dongusunde degil -> olcume girmez (TAHMIN).")


# ═══════════════════════════════════════════════════════════════════════
#  8. SAYISAL YAKINSAMA
# ═══════════════════════════════════════════════════════════════════════

def bolum8(r, sc, O, c_kart: float, t_ref: dict):
    bolum(r, "8. SAYISAL YAKINSAMA — adim 1 us -> 0.5 us")
    secim = [i for i, s in enumerate(sc) if s["grup"] == "ana" and s["ss"] == T.MT3608_SS[1]
             and s["egri"] == "kotu" and s["ss_tip"] == "ref" and s["voc"] == 3.7 and s["kor"] in ("A3", "C")]
    alt = [sc[i] for i in secim]
    O2 = acilis_benzet(alt, c_kart, t_ref, dt=0.5e-6, t_kapa=0.12, t_son=0.12)
    a, b = O["t24"][secim], O2["t24"]
    fark = float(np.max(np.abs(a - b) / b))
    fark_oc = float(np.max(np.abs(O["oc_tip_maks"][secim] - O2["oc_tip_maks"])))
    r.kosul("Sayisal yakinsama: 24 V suresi %5, DW01A tipik esik suresi 3 ms icinde",
            fark < 0.05 and fark_oc < 3e-3,
            f"t24 farki %{fark * 100:.1f}, DW01A suresi farki {fark_oc * 1e3:.1f} ms ({len(alt)} senaryo; "
            f"5 us'de 8x sapiyordu)")


class _Rapor(spice.Rapor):
    """numpy bool'u (np.True_) `is False` ile yakalanmiyordu: kirmizi satir SAYILMIYORDU."""
    def kosul(self, ad, dogru_mu, aciklama=""):
        return super().kosul(ad, bool(dogru_mu), aciklama)


def main() -> int:
    r = _Rapor()
    r.bilgi("")
    r.bilgi("  B58f — KUTUNUN KENDI BESLEMESI: zaman benzetimi")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  ⚠ Davranis modeli, SPICE degil. Veri sayfasinin vermedigi her sey taraniyor.")
    c_kart = kart_kapasitesi()
    bolum1(r)
    sc, O, t_ref = bolum2(r, c_kart)
    bolum2_iddia(r, sc, O, t_ref, c_kart)
    bolum2_dw01(r, sc, O)
    bolum2_dusuk_pil(r, sc, O)
    bolum2_neden(r, sc, O)
    bolum3(r, sc, O)
    bolum4(r)
    bolum5(r)
    bolum6(r)
    bolum7(r, c_kart)
    bolum8(r, sc, O, c_kart, t_ref)
    tamam = r.yazdir()
    tezgah("B58f Kutu besleme zinciri", [
        ("PIL acilisinda kutu aciliyor mu (DW01A + B0505S'in gercek asiri yuk davranisi)",
         "Yeni olcum DEGIL — 10.5'in ilk enerjisinde zaten gorulur: ESP32 acilir, GUC lambasi "
         "yanar, klemenste 24 V. Acilmazsa 10.5'teki yordam (PIL kapat-ac / doldur / TP4056 yedegi)"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
