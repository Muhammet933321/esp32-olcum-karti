# -*- coding: utf-8 -*-
"""B22.5 — LittleFS goruntusunu karta yazar.

    python arayuz-yaz.py               # portu otomatik bul
    python arayuz-yaz.py --port COM7

⚠ `arduino-cli` 1.5.2'nin dosya sistemi yukleme komutu YOK — bu yuzden
  `esptool` dogrudan cagriliyor. Ofset `_fs.json`'dan, o da
  `huge_app.csv`'den geliyor; hicbir adres elle yazilmiyor.

⚠ ONCE `arayuz-uret.py` kosturulmali. Bu betik kunyeyi KAYNAKLA
  KARSILASTIRIYOR: goruntu bayatsa YAZMIYOR. Bayat bir goruntuyu karta
  yazmak, depodaki arayuz ile karttaki arayuzun sessizce ayrismasi
  demekti — bu projenin uc kez yandigi hata sinifi (DEVIR 4.1, 4.15, B17).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
ARAYUZ = KOK / "arayuz3"
GORUNTU = BURASI / "_fs.bin"
KUNYE = BURASI / "_fs.json"

sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))


def main() -> int:
    if not GORUNTU.exists() or not KUNYE.exists():
        print("Goruntu yok. Once:  python arayuz-uret.py")
        return 1
    k = json.loads(KUNYE.read_text(encoding="utf-8"))

    # 🔴 BAYATLIK DENETIMI — bu betigin en onemli isi.
    bayat = []
    for ad, ozet in k["kaynak"].items():
        y = ARAYUZ / ad
        if not y.exists():
            bayat.append(f"{ad} (silinmis)")
        elif hashlib.sha256(y.read_bytes()).hexdigest() != ozet:
            bayat.append(ad)
    if bayat:
        print("Goruntu BAYAT — su dosyalar uretimden sonra degisti:")
        for b in bayat:
            print("   " + b)
        print("\nOnce:  python arayuz-uret.py")
        return 1

    # Arac arama mantigi `arayuz-uret.py`'de — IKI KOPYA OLMASIN.
    # Dosya adinda tire oldugu icin normal `import` calismiyor; bu
    # projenin adlandirma deseni (belge-uret.py, sema3-uret.py …)
    # korunsun diye modul yoldan yukleniyor.
    import importlib.util
    ozellik = importlib.util.spec_from_file_location(
        "arayuz_uret", BURASI / "arayuz-uret.py")
    _uret = importlib.util.module_from_spec(ozellik)
    ozellik.loader.exec_module(_uret)
    mk, esp, csv = _uret.araclar()

    arg = sys.argv[1:]
    port = arg[arg.index("--port") + 1] if "--port" in arg else None
    if not port:
        import kart_baglanti
        adaylar = kart_baglanti.portlari_listele()
        if not adaylar:
            print("COM portu bulunamadi — kart takili mi?")
            return 1
        port = adaylar[-1]

    ofset = k["ofset"]
    print(f"Yaziliyor: {GORUNTU.name} -> {port} @ {ofset}")
    print("  (kart BOOT kipine alinmasi gerekebilir: BOOT basili tut, RESET'e bas)")
    d = subprocess.run([str(esp), "--chip", "esp32s3", "--port", port,
                        "write-flash", ofset, str(GORUNTU)],
                       text=True, encoding="utf-8", errors="replace")
    if d.returncode != 0:
        print("\nesptool basarisiz. Seri monitor / kopru acik olmasin.")
        return 1
    print("\nTamam. Karti yeniden baslatip tarayicidan acin:")
    print("  http://olcum.local   ya da   http://192.168.4.1  (AP kipinde)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
