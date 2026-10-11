# -*- coding: utf-8 -*-
"""SZ capraz vektorleri: ortak/test/vektor/skop_sifir.json'u URETIR (osiloskop KULLANICI SIFIRI).

    python ortak_vektor_skop_sifir.py             # JSON'u yeniden yazar
    python ortak_vektor_skop_sifir.py --denetle   # yazmadan: dosya C ile HALA ayni mi (0/1)

BASVURU = KARTIN GERCEK C KODU: `kod/olcum-karti-a3/skop_olc.h` + `skop_sifir.h` avr-gcc ile derlenip
AVR emulatorunde kosar (uretim/avr/ornek_skop_sifir.c, `M` komutu): ham kodlar -> skop_olc ->
skop_sifir_ofsetle(ofset = skop_sifir_ofset(fabrika, kullanici sifiri)) — kartin `M` satirinin
egrisiz yolu (.ino skop_ofsetle). JS (ortak/src/skop.js) `skopSifirOfset` + `skopOlcKart` her alani
Object.is ile ayni vermeli (ortak/test/skop.test.js). Kullanici sifiri 0 iken ofset fabrika degerinin
KENDISI: eski vektorler ve eski kayitlarin cozumu degismez.

Dalgalar ortak_vektor_skop.py'den (ayni belirlenimci uretec), <= 1024 ornekli olanlar.
"""
from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avr import mega328                    # noqa: E402
from avr.cekirdek import Cekirdek          # noqa: E402
from avr.elf import flash_goruntusu        # noqa: E402
import gecici                              # noqa: E402
import ortak_vektor_skop as OVS            # noqa: E402

HEDEF = KOK / "ortak" / "test" / "vektor" / "skop_sifir.json"
BASLIK_DIZIN = KOK / "kod" / "olcum-karti-a3"
ORNEK = BURASI / "avr" / "ornek_skop_sifir.c"
PROGRAM_ADRES = 0x0A00
RAM_BOYUT = 0xC000 + 2 * 1024 + 16
ALANLAR = OVS.ALANLAR                      # f T Vpp Vmax Vmin Vort Vrms Vac duty tr tf

f32 = OVS.f32
FABRIKA = f32(f32(1.7153125) * f32(f32(38.03703704) - 1.0))   # SKOP_VOLT_OFSET (float katlamasi)
# Kullanici sifirlari (V): 0 = fabrika; kartta olculen USB'li ~0.3 / USB'siz ~2.6; sinir 6.
KULLANICI = (0.0, 2.6, -0.33, 0.32, 5.999)
DALGALAR = ("kare50", "sinus_gurultu", "ucgen", "dc_ustu_kucuk_ac", "duz", "tek_ornek", "sk2_igne_tam")


def derle() -> bytearray:
    if not OVS.AVR_GCC.exists():
        raise SystemExit(f"avr-gcc yok: {OVS.AVR_GCC}")
    d = gecici.dizin("skopsifir_v_")
    elf = d / "ornek_skop_sifir.elf"
    r = subprocess.run(
        [str(OVS.AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu11", "-Wall",
         "-Wextra", f"-I{BASLIK_DIZIN}", "-o", str(elf), str(ORNEK), "-lm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("avr-gcc derleyemedi:\n" + r.stderr)
    if any("warning:" in x for x in r.stderr.splitlines()):
        raise SystemExit("avr-gcc uyari verdi:\n" + r.stderr)
    flash, _ = flash_goruntusu(elf)
    return flash


def vakalar() -> list[dict]:
    hepsi = {v["ad"]: v for v in OVS.vakalar()}
    out = []
    for ad in DALGALAR:
        v = hepsi[ad]
        assert len(v["ham"]) <= 1024
        for kul in KULLANICI:
            out.append({"ad": f"{ad} kul={kul:+g}", "ham": v["ham"], "adet": v["adet"], "volt_adim": v["volt_adim"],
                        "hz": v["hz"], "fabrika": FABRIKA, "kul": f32(kul)})
    return out


def kostur(flash: bytearray, vs: list[dict]) -> list[list[str]]:
    b = bytearray()
    for v in vs:
        b += b"M" + struct.pack("<H", v["adet"]) + struct.pack("<4f", v["volt_adim"], v["hz"], v["fabrika"], v["kul"])
        b += struct.pack(f"<{v['adet']}H", *v["ham"][:v["adet"]])
    b += b"Q"
    assert len(b) <= 0xC000 - PROGRAM_ADRES
    kart = mega328.Kart(flash, lambda f: Cekirdek(f, ram_boyut=RAM_BOYUT))
    kart.cpu.m[PROGRAM_ADRES:PROGRAM_ADRES + len(b)] = b
    for _ in range(20000):
        kart.cevrim_kadar_kos(1_000_000)
        if b"BITTI" in kart.tx:
            break
    else:
        raise SystemExit("emulator bitmedi")
    satir = [s.split() for s in kart.tx.decode("ascii", "replace").splitlines() if s.startswith("M ")]
    assert len(satir) == len(vs) and all(len(p) == 14 for p in satir), satir[:2]
    return satir


def uret() -> str:
    vs = vakalar()
    sonuc = kostur(derle(), vs)
    satirlar = []
    for v, p in zip(vs, sonuc):
        bek = {"ofset": OVS.cozf(p[1])}
        bek.update({ad: OVS.cozf(h) for ad, h in zip(ALANLAR, p[2:13])})
        bek["n"] = int(p[13])
        v["beklenen"] = bek
        satirlar.append(json.dumps(v, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    sha = hashlib.sha256()
    for ad in ("skop_olc.h", "skop_sifir.h"):
        sha.update((BASLIK_DIZIN / ad).read_bytes().replace(b"\r\n", b"\n"))
    bas = {
        "aciklama": "SZ capraz vektorleri: kullanici sifiri. skop_olc + skop_sifir_ofsetle(skop_sifir_ofset(fabrika, "
                    "kul)) AVR emulatorunde (uretim/avr/ornek_skop_sifir.c); beklenen = C'nin float32 ciktisi. "
                    "JS skopSifirOfset(fabrika, kul) ve skopOlcKart(ham, {adim, ofset, hz, adet}) Object.is ile ayni.",
        "kaynak": "kod/olcum-karti-a3/skop_olc.h + kod/olcum-karti-a3/skop_sifir.h",
        "kaynak_sha256": sha.hexdigest(),
        "alanlar": ["ofset"] + list(ALANLAR) + ["n"],
    }
    ust = json.dumps(bas, ensure_ascii=False, indent=1)[:-2]
    return ust + ',\n "vakalar": [\n  ' + ",\n  ".join(satirlar) + "\n ]\n}\n"


def main() -> int:
    metin = uret()
    if "--denetle" in sys.argv:
        guncel = HEDEF.exists() and HEDEF.read_text(encoding="utf-8") == metin
        print("guncel" if guncel else f"ESKI — python uretim/{Path(__file__).name}")
        return 0 if guncel else 1
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_bytes(metin.encode("utf-8"))
    n = metin.count('"ad":')
    print(f"yazildi: {HEDEF.relative_to(KOK).as_posix()} ({n} vaka, {len(metin.encode('utf-8'))} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
