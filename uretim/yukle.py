# -*- coding: utf-8 -*-
"""FIRMWARE'I DERLER VE KARTA YUKLER — tek komut, dogru FQBN.

    python yukle.py                 derle + yukle (portu otomatik bul)
    python yukle.py --port COM7     portu elle sec
    python yukle.py --derle         yalnizca derle, yukleme
    python yukle.py --liste         ne yapacagini yazar, yapmaz

🔴 NEDEN VAR — IKI GERCEK SORUN

1. `arduino-cli` PATH'TE DEGIL. Ikili `Elekronic/.araclar/arduino-cli.exe`
   altinda duruyor. DEVIR'deki ilk gun akisi ciplak `arduino-cli compile`
   yaziyordu ve ESP32 gununun BIRINCI komutu oldugu gibi kosmuyordu.
   Zincir kendini kurtariyordu (`test_firmware3.py` yolu biliyor) ama elle
   derleme icin sarmalayici yoktu.

2. FQBN IKI KOMUTTA ELLE TEKRARLANIYORDU. Tek kaynak `hedef2.py`; elle
   yazilan her kopya ayrisma adayidir ve bu projenin en cok yandigi sinif
   tam olarak bu. Ustelik FQBN'in kendisi tuzakli:
   `PSRAM=opi` olmadan 8 MB PSRAM hic acilmaz, `FlashSize=16M` olmadan
   LittleFS'in 0x310000 ofseti 4 MB sinirina duser.

Yani bu betik bir kolaylik degil, iki ayrisma yuzeyini kapatan bir sey.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))

import hedef2                                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ESKIZ = KOK / "kod" / "olcum-karti-a3"
ARDUINO_CLI = KOK.parents[1] / ".araclar" / "arduino-cli.exe"


def port_bul(elle: str | None) -> tuple[str | None, str | None]:
    if elle:
        return elle, None
    import kart_baglanti
    p = kart_baglanti.portlari_listele()
    if not p:
        return None, ("Seri port yok. Kart takili mi? ⚠ IKI USB SOKETLI "
                      "kartta UART/COM soketine tak — `Serial` yerel USB'de "
                      "DEGIL (hedef2.py CDCOnBoot eklemiyor).")
    if len(p) > 1:
        return None, f"Birden cok port: {', '.join(p)}. --port ile secin."
    return p[0], None


def kos(argv: list[str]) -> int:
    print("  $ " + " ".join(str(x) for x in argv))
    return subprocess.run(argv, cwd=KOK).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Firmware derle + yukle")
    ap.add_argument("--port", help="COM portu (bosken tek port secilir)")
    ap.add_argument("--derle", action="store_true", help="yalnizca derle")
    ap.add_argument("--liste", action="store_true", help="komutlari yazar")
    a = ap.parse_args()

    print("=" * 78)
    print("  FIRMWARE DERLE + YUKLE")
    print("=" * 78)
    print(f"  FQBN   : {hedef2.FQBN}")
    print(f"  eskiz  : {ESKIZ.relative_to(KOK)}")
    print(f"  cli    : {ARDUINO_CLI}")
    print()
    print("  ⚠ Kart ESP32-S3 **N16R8** olmali (16 MB flash, 8 MB oktal")
    print("    PSRAM). FQBN'deki PSRAM=opi ve FlashSize=16M sart.")
    print()

    derle = [str(ARDUINO_CLI), "compile", "--warnings", "all",
             "--fqbn", hedef2.FQBN, str(ESKIZ)]
    if a.liste:
        print("  " + " ".join(derle))
        print(f"  {ARDUINO_CLI} upload -p <PORT> --fqbn {hedef2.FQBN} {ESKIZ}")
        return 0

    if not ARDUINO_CLI.exists():
        print(f"  arduino-cli bulunamadi: {ARDUINO_CLI}")
        print("  Beklenen yer: proje kokunun IKI ustundeki `.araclar/`")
        return 2

    rc = kos(derle)
    if rc != 0:
        print("\n  DERLEME BASARISIZ — yukleme yapilmadi.")
        return rc
    print("\n  Derleme tamam.")
    if a.derle:
        return 0

    port, hata = port_bul(a.port)
    if hata:
        print(f"\n  YUKLEME ATLANDI: {hata}")
        return 2
    print()
    rc = kos([str(ARDUINO_CLI), "upload", "-p", port,
              "--fqbn", hedef2.FQBN, str(ESKIZ)])
    if rc == 0:
        print("\n  Yuklendi. Sirada:")
        print("    python arayuz-uret.py && python arayuz-yaz.py")
        print("    python tezgah_kart.py --sifirla")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
