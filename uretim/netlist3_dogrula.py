# -*- coding: utf-8 -*-
"""B3 — Asama 3 semasinin netlist'ini tasarima karsi dogrular.

NEDEN GEREKLI: ERC bir diyodun TERS baglandigini yakalayamaz — iki ucu da
bagli oldugu icin sema temiz gorunur. Asama 1'de tam olarak bu oldu: ERC
0 ihlal verirken iki koruma diyodu da tersti.

Asama 3'e OZGU denetimler (Asama 2'de olmayan):
  * Bolucularin ALT ucu GND'ye DEGIL, VREF'e gitmeli — cift yonluluk
    tamamen buna bagli. GND'ye gitseydi sema yine ERC-temiz olurdu ama
    kart negatif olcemezdi.
  * ADS #2 iki DIFERANSIYEL cift kullanmali (AIN0-AIN1, AIN2-AIN3) ve
    AIN1/AIN3 VREF'te olmali.
  * Tamponlar gercekten IZLEYICI olmali (cikis, eksi girise donmeli).
  * Sallen-Key topolojisi dogru olmali: C1 geri beslemesi CIKISA gitmeli,
    C2 GND'ye. Ters baglanirsa suzgec calisir ama Q ve f0 degisir.
  * B16: akim kanalinin ortusme suzgeci ADS'in KENDI kolunda olmali
    (R38/R39'un ARDINDA). C4 dugumune konsaydi netlist yine temiz
    gorunurdu ama hizli yolun bandi da kapanirdi — bu, B16 oncesinde
    GERCEKTEN olan seydi. Asagida hem yer hem DEGER denetleniyor.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from netlist_dogrula import netleri_oku                 # noqa: E402
import tasarim3_sabit as T                             # noqa: E402
from tezgah import tezgah                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
SEMA = BURASI.parent / "sema3" / "olcum-karti-a3.kicad_sch"
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

BEKLENEN = {
    # B18/F12: R41 (1K bosaltma). Kelepceler +3V3'te KALIYOR (F6
    # UYGULANMADI) — gerekce sim3_kelepce.py bolum 1'de olculu.
    "+3V3": {"D1.1(K)", "D3.1(K)", "J5.1", "R1.1", "R24.1", "R25.1",
             "U6.8(VDD)", "U7.1(ADDR)", "U7.8(VDD)", "C15.1", "R41.1"},
    "+5V": {"J5.8", "U3.8(V+)", "U4.8(V+)", "C9.1", "C10.1"},
    # B11: +-12 V rayi artik semada. 7912 (U9) orta noktayi TANIMLIYOR:
    #   U9.1 (GND pini) -> +12V   ·   U9.2 (VI) -> -12V   ·   U9.3 (VO) -> GND
    # B21: Q3 (BC557) emiteri +12 V'ta — kapi surucusunun ust kolu.
    "+12V": {"U5.8(V+)", "U8.8(V+)", "C11.1", "C13.1",
             "C16.1", "C17.1", "F1.2", "R40.1", "U9.1(GND)", "Q3.3(E)"},
    "-12V": {"U5.4(V-)", "U8.4(V-)", "C12.1", "C14.1",
             "C16.2", "J6.2", "U9.2(VI)"},
    "/TL_RAY": {"C1.1", "R1.2", "R2.1", "U1.1(REF)", "U1.3(K)"},
    # B15/F1: ADS kolu artik 1K seri direncin (R36) ARDINDA.
    # Bolucu altlari, C2/C3 ve R28 GERCEK VREF'te kalmali.
    # B19: skop bolucusunun ALT UCU da artik VREF'te (R23.2) — kanal
    # CIFT YONLU. Onceden GND'ye gidiyordu ve ESP32 eksi okuyamiyordu.
    "/VREF": {"C2.2", "C3.2", "R16.2", "R28.1", "R6.2", "U3.1", "U3.2(-)",
              "R36.1", "R23.2"},
    "/VREF_ADS": {"R36.2", "U7.5(AIN1)", "U7.7(AIN3)"},
    "/V_GIRIS": {"J1.1", "R4.1"},
    "/V_TAMPON": {"U3.6(-)", "U3.7", "R34.1"},
    "/V_ADS": {"R34.2", "U7.4(AIN0)"},
    "/HV_GIRIS": {"J2.1", "R10.1"},
    "/HV_TAMPON": {"U4.1", "U4.2(-)", "R35.1"},
    "/HV_ADS": {"R35.2", "U7.6(AIN2)"},
    # B21: Q1 (IRFZ44N) SOURCE'u da burada — pil testi yolu J7 -> Q1 -> sont.
    # J3 DOGRUDAN bagli kaliyor (normal ampermetre kullanimi etkilenmiyor).
    "/YUK_EKSI": {"J3.1", "R18.1", "RS.1", "Q1.S(S)"},
    # Kelvin uclari IKI yere gidiyor: ADS'in RC'sine ve hizli yolun
    # fark yukseltecine (R27/R29). Hizli yol RC'nin ARDINDAN cekilseydi
    # 7.96 kHz'e hapsolurdu (DEVIR 4.8 notu).
    # B15/F2: ADS kolu 1K'nin (R38/R39) ARDINDA; hizli yol (R27/R29)
    # direncin ONUNDEN tapliyor, yani bant genisligi etkilenmiyor.
    "/SONT_P": {"C4.1", "R18.2", "R27.1", "R38.1"},
    "/SONT_N": {"C4.2", "R19.2", "R29.1", "R39.1"},
    # B16: ortusme suzgeci ADS'in KENDI kolunda — C18+C19+C20 = 1.32 uF,
    # R38/R39'un ARDINDA. C4 dugumune konsaydi hizli yolun bandi da
    # kapanirdi (B16 oncesi tam bu oluyordu).
    "/SONT_P_A": {"R38.2", "U6.4(AIN0)", "C18.1", "C19.1", "C20.1"},
    "/SONT_N_A": {"R39.2", "U6.5(AIN1)", "C18.2", "C19.2", "C20.2"},
    "/I_HIZLI": {"D3.2(A)", "D4.1(K)", "J5.7", "R33.2"},
    "/SKOP_GIRIS": {"J4.1", "R20.1"},
    "/SKOP": {"D1.2(A)", "D2.1(K)", "J5.5", "R26.2"},
    "/SDA": {"J5.3", "R25.2", "U6.9(SDA)", "U7.9(SDA)"},
    "/SCL": {"J5.4", "R24.2", "U6.10(SCL)", "U7.10(SCL)"},
    "/HAZIR": {"J5.6", "U6.2(ALERT/RDY)"},
    "GND": {"C1.2", "C6.2", "D2.2(A)", "J1.2", "J2.2", "J3.2", "J4.2",
            "J5.2", "J5.9", "R19.1", "R3.2", "RS.2", "U1.2(A)",
            "U3.4(V-)", "U4.4(V-)", "U4.5(+)", "U6.1(ADDR)",
            "U6.3(GND)", "U6.6(AIN2)", "U6.7(AIN3)", "U7.3(GND)",
            "C8.2", "D4.2(A)", "U8.5(+)",
            "C9.2", "C10.2", "C11.2", "C12.2", "C13.2", "C14.2", "C15.2",
            # B11: 7912'nin CIKISI artik GND'yi suruyor
            "C17.2", "R40.2", "U9.3(VO)",
            # B18/F12: +3V3 bosaltma direncinin alt ucu
            "R41.2",
            # B21: pil testi — J7 eksi ucu, NPN emiteri, KAPI CEKME direnci
            "J7.2", "Q2.3(E)", "R42.2"},
}

# ERC'nin GOREMEDIGI kurallar — yon, polarite, adres, topoloji
KRITIK = [
    # --- CIFT YONLULUK: bolucu altlari VREF'te, GND'de DEGIL
    ("NORMAL bolucu alt ucu VREF'te (GND'de DEGIL)", "/VREF", "R6.2"),
    ("YUKSEK bolucu alt ucu VREF'te (GND'de DEGIL)", "/VREF", "R16.2"),
    # --- ADS #2 diferansiyel ciftler
    ("ADS#2 AIN0 = NORMAL tampon cikisi (1K ardinda)",
     "/V_ADS", "U7.4(AIN0)"),
    ("ADS#2 AIN1 = VREF (AIN0-AIN1 cifti, 1K ardinda)",
     "/VREF_ADS", "U7.5(AIN1)"),
    ("ADS#2 AIN2 = YUKSEK tampon cikisi (1K ardinda)",
     "/HV_ADS", "U7.6(AIN2)"),
    ("ADS#2 AIN3 = VREF (AIN2-AIN3 cifti, 1K ardinda)",
     "/VREF_ADS", "U7.7(AIN3)"),
    # --- B15/F1-F2: ADS giris koruma direncleri GERCEKTEN yerinde mi
    ("B15/F1: R34 tampon cikisi ile ADS arasinda", "/V_TAMPON", "R34.1"),
    ("B15/F1: R35 HV tamponu ile ADS arasinda", "/HV_TAMPON", "R35.1"),
    ("B15/F1: R36 VREF ile ADS arasinda", "/VREF", "R36.1"),
    ("B15/F2: R38 SONT_P ile ADS arasinda", "/SONT_P", "R38.1"),
    ("B15/F2: R39 SONT_N ile ADS arasinda", "/SONT_N", "R39.1"),
    # --- hizli yol koruma direncinin ONUNDEN taplanmali (bant genisligi)
    ("B15/F2: hizli yol R38'in ONUNDEN tapliyor", "/SONT_P", "R27.1"),
    ("B15/F2: hizli yol R39'un ONUNDEN tapliyor", "/SONT_N", "R29.1"),
    # --- B11: 7912 ORTA NOKTA REGULATORU
    # ⚠ ERC'de `ground_pin_not_ground` kurali BILEREK kapatildi (7912'nin
    #   GND pini kart GND'sine degil +12V rayina bagli). Denetim burada,
    #   ve ERC'ninkinden DAHA KESIN: uc pinin de nereye gittigi yaziliyor.
    ("B11: 7912 GND pini +12V rayinda (kart GND'sinde DEGIL)",
     "+12V", "U9.1(GND)"),
    ("B11: 7912 VI pini -12V rayinda", "-12V", "U9.2(VI)"),
    ("B11: 7912 VO pini kart GND'sini SURUYOR", "GND", "U9.3(VO)"),
    # 79xx'te giris kapasitesi VI ile GND-pini, cikis kapasitesi VO ile
    # GND-pini arasina konur. Bizim eslemede GND-pini = +12V.
    ("B11: C16 (giris kap.) +12V ile -12V arasinda", "-12V", "C16.2"),
    ("B11: C16'nin arti ucu +12V'ta", "+12V", "C16.1"),
    ("B11: C17 (cikis kap.) +12V ile GND arasinda", "GND", "C17.2"),
    ("B11: C17'nin arti ucu +12V'ta", "+12V", "C17.1"),
    # Bosaltma direnci YONU: +12 -> GND olmali. GND -> -12 konsaydi
    # regulatorun yukunu AZALTIRDI, cogaltmazdi.
    ("B11: bosaltma direnci +12V'tan GND'ye (ters DEGIL)", "+12V", "R40.1"),
    ("B11: bosaltma direncinin obur ucu GND'de", "GND", "R40.2"),
    # Sigorta 24 V girisinin ARTI kolunda
    ("B11: sigorta cikisi +12V rayinda", "+12V", "F1.2"),
    ("B11: 24 V girisinin eksi ucu -12V rayinda", "-12V", "J6.2"),
    # --- bolucu altlari GERCEK VREF'te kalmali (direncin ardinda DEGIL)
    ("B15/F1: NORMAL bolucu alti GERCEK VREF'te", "/VREF", "R6.2"),
    ("B15/F1: HV bolucu alti GERCEK VREF'te", "/VREF", "R16.2"),
    ("B15/F1: fark yuk. REF ucu GERCEK VREF'te", "/VREF", "R28.1"),
    # --- tamponlar gercekten izleyici mi
    ("Vref tamponu izleyici (cikis -> eksi giris)", "/VREF", "U3.2(-)"),
    ("NORMAL tamponu izleyici", "/V_TAMPON", "U3.6(-)"),
    ("YUKSEK tamponu izleyici", "/HV_TAMPON", "U4.2(-)"),
    # --- kelepce POLARITESI (Asama 1'de tam burasi tersti)
    ("D1 ust kelepce: KATOT +3V3'te", "+3V3", "D1.1(K)"),
    ("D1 ust kelepce: ANOT skop dugumunde", "/SKOP", "D1.2(A)"),
    ("D2 alt kelepce: KATOT skop dugumunde", "/SKOP", "D2.1(K)"),
    ("D2 alt kelepce: ANOT GND'de", "GND", "D2.2(A)"),
    # --- TL431 yonu
    ("TL431 KATOT rayda", "/TL_RAY", "U1.3(K)"),
    ("TL431 REF katoda bagli", "/TL_RAY", "U1.1(REF)"),
    ("TL431 ANOT GND'de", "GND", "U1.2(A)"),
    # --- ADS adresleri (ters olsa iki cip ayni adresi paylasir)
    ("ADS#1 ADDR -> GND (0x48)", "GND", "U6.1(ADDR)"),
    ("ADS#2 ADDR -> +3V3 (0x49)", "+3V3", "U7.1(ADDR)"),
    # --- ADS #1 kullanilmayan girisler GND'de
    #     (TI s.12: bos girisi asiri surmek DIGER kanallari bozar)
    ("ADS#1 AIN2 bosta birakilmamis", "GND", "U6.6(AIN2)"),
    ("ADS#1 AIN3 bosta birakilmamis", "GND", "U6.7(AIN3)"),
    # --- op-amp beslemeleri
    ("LM358'ler +5 V'ta (3.3 V'ta cikis yetmezdi)", "+5V", "U3.8(V+)"),
    ("TL072 +12 V'ta", "+12V", "U5.8(V+)"),
    ("TL072 -12 V'ta (skop kanali negatife inebilmeli)", "-12V", "U5.4(V-)"),
    # --- kullanilmayan kesitler bosta DEGIL
    ("Bos LM358 kesiti izleyici baglanmis", "GND", "U4.5(+)"),
    # U5B artik BOSTA DEGIL — hizli akim Sallen-Key'i oldu (B8).
    ("Bos TL072 kesiti izleyici baglanmis", "GND", "U8.5(+)"),
    # --- B8: HIZLI AKIM YOLU
    ("Fark yuk. + kolu SONT_P'den geliyor", "/SONT_P", "R27.1"),
    ("Fark yuk. - kolu SONT_N'den geliyor", "/SONT_N", "R29.1"),
    ("Fark yuk. REF ucu VREF'te (cift yonluluk buna bagli)",
     "/VREF", "R28.1"),
    ("Fark yuk. geri beslemesi cikisa donuyor", "Net-(R30-Pad2)", "R30.2"),
    ("Hizli akim ESP32'ye gidiyor (GPIO5)", "/I_HIZLI", "J5.7"),
    ("Hizli yol ust kelepce: KATOT +3V3'te", "+3V3", "D3.1(K)"),
    ("Hizli yol ust kelepce: ANOT dugumde", "/I_HIZLI", "D3.2(A)"),
    ("Hizli yol alt kelepce: KATOT dugumde", "/I_HIZLI", "D4.1(K)"),
    ("Hizli yol alt kelepce: ANOT GND'de", "GND", "D4.2(A)"),
    # --- AYIRMA KONDANSATORLERI
    # Ilk surumde HIC YOKTU; netlist denetimi gosterdi. Op-amp cikisi
    # kapasitif yuk (Sallen-Key) suruyor ve besleme empedansi yuksekse
    # salinim olabilir.
    ("U3/U4 (+5V) ayirma kondansatoru var", "+5V", "C9.1"),
    ("U5 (+12V) ayirma kondansatoru var", "+12V", "C11.1"),
    ("U5 (-12V) ayirma kondansatoru var", "-12V", "C12.1"),
    ("U8 (+12V) ayirma kondansatoru var", "+12V", "C13.1"),
    ("U8 (-12V) ayirma kondansatoru var", "-12V", "C14.1"),
    ("ADS rayinda (+3V3) ayirma kondansatoru var", "+3V3", "C15.1"),
    # --- I2C pull-up gercekten +3V3'te
    ("SDA pull-up +3V3'te", "+3V3", "R25.1"),
    ("SCL pull-up +3V3'te", "+3V3", "R24.1"),
]

# Sallen-Key topolojisi: adlandirilmamis netlerde arandigi icin ayri
SALLEN_KEY = [
    # --- B8 hizli akim Sallen-Key'i (U5B)
    ("SK2: C2 (C8) GND'ye", "GND", "C8.2"),
    ("SK2: C2 opamp + girisinde", "Net-(U5B-+)", "C8.1"),
    ("SK2: C1 (C7) CIKISA donuyor", "Net-(U5B--)", "C7.2"),
    ("SK2: opamp izleyici", "Net-(U5B--)", "U5.6(-)"),
    ("SK2: kelepce seri direnci cikistan sonra", "Net-(U5B--)", "R33.1"),
    ("SK: C2 (C6) GND'ye — ust kutup", "GND", "C6.2"),
    ("SK: C2 opamp + girisinde", "Net-(U5A-+)", "C6.1"),
    ("SK: C1 (C5) CIKISA donuyor (GND'ye DEGIL)", "Net-(U5A--)", "C5.2"),
    ("SK: opamp izleyici — cikis eksi giriste", "Net-(U5A--)", "U5.2(-)"),
    ("SK: kelepce seri direnci CIKISTAN sonra", "Net-(U5A--)", "R26.1"),
]

# ADS yolunun RC ortusme suzgecleri — HIC DENETLENMIYORDU.
# R17 bir tur kaldirilip geri konuldu ve netlist denetimi bunu hic
# gormedi: her iki durumda da 75/75 gecti. Suzgecin TOPOLOJISI
# (seri direnc + tamponun ONUNDE + kondansator VREF'e) artik kural.
RC_SUZGEC = [
    # NORMAL kanal: R4/R6 dugumu -> R7 -> U3B(+) dugumu -> C2 -> VREF
    ("RC-N: R7 bolucu dugumunde", "Net-(R4-Pad2)", "R7.1"),
    ("RC-N: R7'nin obur ucu tampon girisinde", "Net-(U3B-+)", "R7.2"),
    ("RC-N: tampon girisi suzgecin ARDINDAN", "Net-(U3B-+)", "U3.5(+)"),
    ("RC-N: C2 suzgec dugumunde", "Net-(U3B-+)", "C2.1"),
    ("RC-N: C2 VREF'e donuyor (GND'ye DEGIL)", "/VREF", "C2.2"),
    # YUKSEK kanal: R15/R16 dugumu -> R17 -> U4A(+) dugumu -> C3 -> VREF
    ("RC-H: R17 bolucu dugumunde", "Net-(R15-Pad2)", "R17.1"),
    ("RC-H: R17'nin obur ucu tampon girisinde", "Net-(U4A-+)", "R17.2"),
    ("RC-H: tampon girisi suzgecin ARDINDAN", "Net-(U4A-+)", "U4.3(+)"),
    ("RC-H: C3 suzgec dugumunde", "Net-(U4A-+)", "C3.1"),
    ("RC-H: C3 VREF'e donuyor (GND'ye DEGIL)", "/VREF", "C3.2"),
]


_CARPAN = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "": 1.0}


def coz(s: str) -> float:
    """'220nF' -> 220e-9. Semada yazan degeri sayiya cevirir."""
    m = re.fullmatch(r"([\d.]+)\s*([pnu]?)F", s.strip())
    return float(m.group(1)) * _CARPAN[m.group(2)] if m else float("nan")


def cevir(x: float) -> str:
    """1e-9 -> '1nF'. Sabitler dosyasindaki degeri sema yazimina cevirir."""
    for ek, c in (("u", 1e-6), ("n", 1e-9), ("p", 1e-12)):
        if x >= c:
            v = x / c
            return f"{v:g}{ek}F"
    return f"{x}F"


def main() -> int:
    u = subprocess.run(
        [KICAD_CLI, "sch", "export", "netlist", "--output", "netlist3.net",
         str(SEMA)],
        cwd=BURASI, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300)
    if u.returncode != 0:
        print(u.stdout, u.stderr)
        return 1

    netler = netleri_oku(BURASI / "netlist3.net")
    gecti = kaldi = 0

    print("  NET ICERIKLERI — tasarima birebir uyuyor mu")
    print()
    for ad, beklenen in sorted(BEKLENEN.items()):
        alinan = netler.get(ad, set())
        tamam = alinan == beklenen
        gecti += tamam
        kaldi += not tamam
        print(f"  {'[OK]' if tamam else '[!!]'}   {ad:<16} {len(beklenen)} uc")
        if not tamam:
            print(f"        eksik : {sorted(beklenen - alinan)}")
            print(f"        fazla : {sorted(alinan - beklenen)}")

    print()
    print("  ERC'nin GOREMEDIGI kurallar (yon / polarite / adres / topoloji):")
    for ad, net, pin in KRITIK + SALLEN_KEY + RC_SUZGEC:
        tamam = pin in netler.get(net, set())
        gecti += tamam
        kaldi += not tamam
        print(f"  {'[OK]' if tamam else '[!!]'}   {ad:<52} {pin} -> {net}")

    print()
    print("  NEGATIF DENETIM — bolucu altlari GND'ye BAGLANMAMIS olmali")
    for ad, pin in (("NORMAL bolucu alti", "R6.2"),
                    ("YUKSEK bolucu alti", "R16.2")):
        tamam = pin not in netler.get("GND", set())
        gecti += tamam
        kaldi += not tamam
        print(f"  {'[OK]' if tamam else '[!!]'}   {ad:<52} {pin} GND'de degil")

    print()
    print("  B19 — skop kanali CIFT YONLU mu")
    for ad, net, pin in (
            ("B19: R23'un alt ucu VREF'te (GND'de DEGIL)", "/VREF", "R23.2"),
            ("B19: R23'un ust ucu bolucu dugumunde", "Net-(R20-Pad2)",
             "R23.1"),
            ("B19: R20 skop girisinde", "/SKOP_GIRIS", "R20.1")):
        tamam = pin in netler.get(net, set())
        gecti += tamam
        kaldi += not tamam
        print(f"  {'[OK]' if tamam else '[!!]'}   {ad:<52} {pin} -> {net}")
    tamam = "R23.2" not in netler.get("GND", set())
    gecti += tamam
    kaldi += not tamam
    print(f"  {'[OK]' if tamam else '[!!]'}   "
          f"{'B19 NEGATIF: R23 alt ucu GND"de DEGIL':<52} R23.2")

    print()
    print("  B18 — kelepce raylari ve +3V3 bosaltma direnci")
    for ad, kosul_net, pin in (
            ("B18: D1 ust kelepcesi +3V3'te KALDI (F6 uygulanmadi)",
             "+3V3", "D1.1(K)"),
            ("B18: D3 ust kelepcesi +3V3'te KALDI", "+3V3", "D3.1(K)"),
            ("B18/F12: R41 ust ucu +3V3'te", "+3V3", "R41.1"),
            ("B18/F12: R41 alt ucu GND'de", "GND", "R41.2")):
        tamam = pin in netler.get(kosul_net, set())
        gecti += tamam
        kaldi += not tamam
        print(f"  {'[OK]' if tamam else '[!!]'}   {ad:<52} {pin} -> "
              f"{kosul_net}")

    print()
    print("  B16 — ortusme suzgeci DOGRU KOLDA ve DOGRU DEGERDE mi")
    # negatif: suzgec kondansatorleri C4 dugumunde (SONT_P/N) OLMAMALI
    for ref in ("C18", "C19", "C20"):
        tamam = not ({f"{ref}.1", f"{ref}.2"}
                     & (netler.get("/SONT_P", set())
                        | netler.get("/SONT_N", set())))
        gecti += tamam
        kaldi += not tamam
        print(f"  {'[OK]' if tamam else '[!!]'}   "
              f"{ref + ' C4 dugumunde DEGIL (hizli yol serbest)':<52} "
              f"/SONT_P|N disinda")
    # degerler semadan okunuyor — sabitler dosyasiyla ayrisamaz
    degerler = dict(re.findall(
        r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\)',
        (BURASI / "netlist3.net").read_text(encoding="utf-8")))
    for ad, kosul, ek in (
            ("B18/F12: R26 kelepce seri direnci buyutuldu",
             degerler.get("R26") == "10K",
             f"R26 = {degerler.get('R26')} (eskiden 2.7K)"),
            ("B18/F12: R33 de ayni deger",
             degerler.get("R33") == degerler.get("R26"),
             f"R33 = {degerler.get('R33')}"),
            ("B19: R23 skop bolucusu 2.7K (cift yonlu menzil)",
             degerler.get("R23") == "2.7K",
             f"R23 = {degerler.get('R23')} (eskiden 6.8K)"),
            ("B18/F12: R41 bosaltma direnci 1K",
             degerler.get("R41") == "1K", f"R41 = {degerler.get('R41')}"),
            ("C4 yalnizca RF (B16: 100nF degil)",
             degerler.get("C4") == cevir(T.SONT_C), f"C4 = {degerler.get('C4')}"),
            ("C18+C19+C20 = ADS_AKIM_C",
             abs(sum(coz(degerler.get(r, "0")) for r in ("C18", "C19", "C20"))
                 - T.ADS_AKIM_C) < 1e-12,
             " + ".join(degerler.get(r, "?") for r in ("C18", "C19", "C20"))
             + f" = {T.ADS_AKIM_C*1e6:.3f} uF")):
        gecti += kosul
        kaldi += not kosul
        print(f"  {'[OK]' if kosul else '[!!]'}   {ad:<52} {ek}")

    # 🔴 B20 (2026-09-10) — KURULUM KILAVUZU YANLIS REFERANS VERIYORDU.
    # Kilavuz "Sallen-Key (U5A): R22/R23, C7" diyordu. Netlist baska bir
    # sey soyluyor ve bu bir MONTAJ TUZAGIYDI: R23 bolucunun ALT BACAGI
    # (2.7K, VREF'e — B19'un konusu), Sallen-Key'in direnci R21; C7 ise
    # U5B'ye ait, U5A'nınki C5. R23'e 6.8K takmak skop kanalini hem tek
    # yonlu birakir hem olcegini bozardi.
    #
    # Asagidaki denetim kilavuzun METNINI degil TOPOLOJIYI okuyor, ve
    # kilavuzun uretilen ciktisinda dogru referanslarin gectigini sinar.
    print()
    kilavuz = (BURASI / "kurulum3-uret.py").read_text(encoding="utf-8",
                                                      errors="replace")
    u5a_arti = set(netler.get("Net-(U5A-+)", []))
    u5a_eksi = set(netler.get("Net-(U5A--)", []))
    sk_dugum = set(netler.get("Net-(C5-Pad1)", []))
    for ad, kosul, ek in (
        ("U5A'nin + girisi R21 ve C6'ya bagli",
         {"R21.2", "C6.1", "U5.3(+)"} <= u5a_arti,
         f"Net-(U5A-+) = {sorted(u5a_arti)}"),
        ("U5A'nin Sallen-Key dugumu R21/R22/C5",
         {"R21.1", "R22.2", "C5.1"} <= sk_dugum,
         f"Net-(C5-Pad1) = {sorted(sk_dugum)}"),
        ("C5 geri beslemesi U5A cikisinda (C7 DEGIL)",
         "C5.2" in u5a_eksi and "C7.2" not in u5a_eksi,
         f"Net-(U5A--) = {sorted(u5a_eksi)}"),
        ("R23 SALLEN-KEY'IN DEGIL, BOLUCUNUN bacagi",
         "R23.2" in set(netler.get("/VREF", []))
         and "R23.1" in set(netler.get("Net-(R20-Pad2)", [])),
         "R23 alt ucu VREF'te, ust ucu R20-R22 dugumunde"),
        ("Kilavuz U5A icin R21/R22 ve C5 yaziyor",
         "R21/R22" in kilavuz and "C5 = {T.SK_C1" in kilavuz,
         "eskiden R22/R23 ve C7 yaziyordu — montaj tuzagi"),
        ("Kilavuz artik R22/R23'u Sallen-Key diye ANMIYOR",
         "R22/R23 = {T.SK_R" not in kilavuz,
         "eski yanlis satir kaldirildi")):
        gecti += kosul
        kaldi += not kosul
        print(f"  {'[OK]' if kosul else '[!!]'}   {ad:<52} {ek}")

    # ═══════════════════════ B21 — PIL TESTI ANAHTARI ve KAPI SURUCUSU
    print()
    q1g = set(netler.get("Net-(Q1-PadG)", []))
    for ad, kosul, ek in (
        ("B21: MOSFET drain J7'ye (yuk konnektoru) bagli",
         set(netler.get("Net-(J7-Pin_1)", [])) == {"J7.1", "Q1.D(D)"},
         f"{sorted(netler.get('Net-(J7-Pin_1)', []))}"),
        ("B21: MOSFET source SONTUN UST ucunda (akim olculuyor)",
         "Q1.S(S)" in set(netler.get("/YUK_EKSI", [])),
         "Q1 -> /YUK_EKSI -> RS.1: anahtar akim yolunun ICINDE"),
        ("B21: 🔴 KAPI, R42 ile GND'ye CEKILI (failsafe KAPALI)",
         "R42.1" in q1g and "R42.2" in set(netler.get("GND", [])),
         "ESP32 yuksek-Z'ye donerse kapi 0 V -> MOSFET KAPANIR"),
        ("B21: 🔴 kapi +12 V'a CEKILMIYOR (ters kurulum degil)",
         not (q1g & set(netler.get("+12V", []))),
         "kapi dogrudan +12 V'a bagli olsaydi kart olurken yuk BAGLI kalirdi"),
        ("B21: kapi seri direnci R45 yerinde",
         "R45.2" in q1g and "R45.1" in set(netler.get("Net-(Q3-C)", [])),
         "BC557 tepe akimini siniryor (12/220 = 55 mA < 100 mA)"),
        ("B21: PNP emiteri +12 V'ta (ust kol)",
         "Q3.3(E)" in set(netler.get("+12V", [])),
         "kapi 12 V'a surulebiliyor — 3.3 V IRFZ44N icin YETMEZ"),
        ("B21: NPN emiteri GND'de (alt kol)",
         "Q2.3(E)" in set(netler.get("GND", [])),
         "iki katli surucu: GPIO yuksek -> kapi 12 V (TERS DEGIL)"),
        ("B21: GPIO, R44 uzerinden NPN tabanina",
         set(netler.get("/PIL_KAPI", [])) == {"J5.10", "R44.1"}
         and "R44.2" in set(netler.get("Net-(Q2-B)", [])),
         "J5 pin 10 (eski yedek pin) -> 4.7K -> 2N2222 tabani"),
        ("B21: 🔴 kapi neti J7/drain ile KISA DEVRE DEGIL",
         not (q1g & {"J7.1", "Q1.D(D)"})
         and not (set(netler.get("/PIL_KAPI", [])) & {"J7.1", "Q1.D(D)"}),
         "ilk yerlesimde iki tel ayni y'de gecip kisa devre olmustu; "
         "ERC bunu GORMEDI, netlist gordu")):
        gecti += kosul
        kaldi += not kosul
        print(f"  {'[OK]' if kosul else '[!!]'}   {ad:<52} {ek}")

    # Deger denetimi — B21 parcalari
    for ref, bek in (("R42", "10K"), ("R43", "10K"), ("R44", "4.7K"),
                     ("R45", "220R"), ("Q1", "IRFZ44N"),
                     ("Q2", "2N2222"), ("Q3", "BC557")):
        kosul = degerler.get(ref) == bek
        gecti += kosul
        kaldi += not kosul
        print(f"  {'[OK]' if kosul else '[!!]'}   "
              f"{'B21: ' + ref + ' degeri':<52} "
              f"{degerler.get(ref, '?')} (beklenen {bek})")

    bos = [a for a in netler if a.startswith("unconnected-")]
    # B21: J5'in 10. pini artik BOS DEGIL — pil testi MOSFET kapisini suruyor.
    # Geriye yalnizca ADS#2'nin bilerek bos ALERT ucu kaliyor.
    tamam = sorted(bos) == ["unconnected-(U7-ALERT{slash}RDY-Pad2)"]
    gecti += tamam
    kaldi += not tamam
    print()
    print(f"  {'[OK]' if tamam else '[!!]'}   "
          f"{'Bilerek bos uclar: ADS#2 ALERT + J5 yedek pin':<52} {bos}")

    print()
    print(f"  {gecti}/{gecti + kaldi} dogrulama gecti")
    tezgah("B3 Sema", [
        ("Kurulan kart SEMAYLA ayni mi",
         "Netlist yalnizca semayi dogruluyor; lehimlenen kart baska "
         "olabilir. Olcum: her dugumu ohmmetrenin sureklilik kipiyle "
         "netliste karsi tek tek gec"),
        ("Polarite: elektrolitik ve diyot yonleri",
         "ERC yon hatasi YAKALAMAZ. Olcum: montajdan ONCE her "
         "kutuplu parcayi gozle dogrula — enerji verdikten sonra "
         "elektrolitik geri donusu yok"),
    ])
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
