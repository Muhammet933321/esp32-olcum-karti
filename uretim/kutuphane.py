"""KiCad sembol kutuphanesinden sembol tanimi cikarma ve duzlestirme.

KiCad sembollerinin bir kismi `(extends "ATA")` ile baska bir sembolden
turer — cizim ve pinler atada durur. Semanin `lib_symbols` blogu ise
tam cozulmus tanim ister, o yuzden burada duzlestiriliyor.
"""
from __future__ import annotations

import re
from pathlib import Path

KICAD = Path(r"C:\Program Files\KiCad\10.0")
SEMBOL_DIZIN = KICAD / "share" / "kicad" / "symbols"


def _govde(metin: str, ad: str) -> str:
    """Parantez sayarak `(symbol "<ad>"` blogunu ayikla."""
    bas = metin.find(f'\t(symbol "{ad}"\n')
    if bas < 0:
        raise KeyError(ad)
    derinlik, i, dize = 0, bas, False
    while i < len(metin):
        k = metin[i]
        if dize:
            if k == "\\":
                i += 2
                continue
            if k == '"':
                dize = False
        elif k == '"':
            dize = True
        elif k == "(":
            derinlik += 1
        elif k == ")":
            derinlik -= 1
            if derinlik == 0:
                return metin[bas:i + 1]
        i += 1
    raise ValueError(f"{ad}: sembol kapanmadi")


def _ust_duzey(govde: str) -> list[tuple[str, str]]:
    """Sembol govdesinin ust duzey alt-ifadelerini (ad, metin) olarak dondurur.

    `property` icin ad "property <PropAdi>" olur, boylece cocuk-ata birlestirmesi
    ozellik bazinda yapilabilir.
    """
    parcalar: list[tuple[str, str]] = []
    derinlik, i, dize, bas = 0, 0, False, None
    while i < len(govde):
        k = govde[i]
        if dize:
            if k == "\\":
                i += 2
                continue
            if k == '"':
                dize = False
        elif k == '"':
            dize = True
        elif k == "(":
            derinlik += 1
            if derinlik == 2:
                bas = i
        elif k == ")":
            if derinlik == 2 and bas is not None:
                metin = govde[bas:i + 1]
                ic = metin[1:-1].split()
                ad = ic[0] if ic else "?"
                if ad == "property":
                    m = re.search(r'"([^"]*)"', metin)
                    ad = f"property {m.group(1)}" if m else ad
                elif ad == "symbol":
                    m = re.search(r'"([^"]*)"', metin)
                    ad = f"symbol {m.group(1)}" if m else ad
                parcalar.append((ad, metin))
                bas = None
            derinlik -= 1
        i += 1
    return parcalar


def sembol_cek(kutuphane: str, ad: str) -> str:
    """Sembolu tam cozulmus (extends duzlestirilmis) halde dondurur.

    Duzlestirme KiCad'in kendi kanonik sirasini taklit eder: once bayraklar
    (pin_numbers, pin_names, in_bom, ...), sonra ozellikler, sonra cizim
    bloklari, en sonda embedded_fonts. Sira yanlis olursa KiCad
    `lib_symbol_mismatch` uyarisi verir.
    """
    metin = (SEMBOL_DIZIN / f"{kutuphane}.kicad_sym").read_text(encoding="utf-8")
    govde = _govde(metin, ad)
    ata_m = re.search(r'\(extends "([^"]+)"\)', govde)

    if ata_m:
        ata = ata_m.group(1)
        cocuk = dict(_ust_duzey(govde))
        cocuk.pop("extends", None)
        ata_parcalar = _ust_duzey(_govde(metin, ata))

        # Atanin sirasini sablon al; cocukta varsa cocugunkini kullan.
        birlesik: list[str] = []
        for a_ad, a_metin in ata_parcalar:
            if a_ad.startswith("symbol "):
                # cizim blogu: cocugun adiyla yeniden adlandir
                birlesik.append(a_metin.replace(f'(symbol "{ata}_',
                                                f'(symbol "{ad}_', 1))
            elif a_ad in cocuk:
                birlesik.append(cocuk.pop(a_ad))
            else:
                birlesik.append(a_metin)
        # cocukta olup atada olmayanlar (nadir) sona
        for _k, v in cocuk.items():
            birlesik.append(v)

        basluk = f'\t(symbol "{ad}"'
        govde = basluk + "\n\t\t" + "\n\t\t".join(birlesik) + "\n\t)"

    # lib_id kutuphane onekli olmali: "R" -> "Device:R"
    if not ad.startswith(f"{kutuphane}:"):
        govde = govde.replace(f'(symbol "{ad}"', f'(symbol "{kutuphane}:{ad}"', 1)
    return govde


def pinler(kutuphane: str, ad: str) -> list[tuple]:
    """(birim, numara, isim, x, y, aci, tip) listesi."""
    govde = sembol_cek(kutuphane, ad)
    kisa = ad.split(":")[-1]
    cikti = []
    for m in re.finditer(r'\(symbol "' + re.escape(kisa) + r'_(\d+)_\d+"', govde):
        birim = int(m.group(1))
        bas = m.end()
        son = govde.find(f'(symbol "{kisa}_', bas)
        dilim = govde[bas: son if son > 0 else len(govde)]
        for p in re.finditer(
                r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*'
                r'\(length ([\d.]+)\)\s*\(name "([^"]*)"'
                r'(?:.*?)\(number "([^"]*)"', dilim, re.S):
            tip, x, y, aci, uz, isim, no = p.groups()
            cikti.append((birim, no, isim, float(x), float(y), int(aci), tip))
    return cikti


if __name__ == "__main__":
    for kut, ad in [("Device", "R"), ("Device", "C"),
                    ("Diode", "1N4148"), ("Reference_Voltage", "TL431LP"),
                    ("Amplifier_Operational", "LM358"),
                    ("power", "GND"), ("power", "+5V"), ("power", "PWR_FLAG")]:
        try:
            g = sembol_cek(kut, ad)
            p = pinler(kut, ad)
            print(f"\n=== {kut}:{ad}  ({len(g)} karakter, {len(p)} pin)")
            for birim, no, isim, x, y, aci, tip in p:
                print(f"    birim {birim}  pin {no:>3} {isim:<10} "
                      f"({x:>7.2f},{y:>7.2f}) aci {aci:>3}  {tip}")
        except (KeyError, ValueError) as e:
            print(f"\n=== {kut}:{ad} -> HATA {e!r}")
