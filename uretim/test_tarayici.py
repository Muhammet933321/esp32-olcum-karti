# -*- coding: utf-8 -*-
"""tarayici.py KAPANIS SOZLESMESI — basliksiz Edge sizdirmiyor mu (T-TR).

NEDEN VAR (2026-10-02): `Tarayici.kapat()` yalniz Popen'in PID'ini olduruyordu.
Edge Windows'ta kendini YENIDEN BASLATIYOR; Popen'in PID'i gercek tarayici degil.
Her tarayici testi bir Edge'i (~150 MB) acik birakti: 81 surec 12.3 GB RAM, %TEMP%'te
460 profil 131 GB disk birikti ve bilgisayar kilitlendi (kullanici yeniden baslatti).
Ayrica sabit 9333 portu: eski Edge o portu tutarken yeni test ESKI tarayiciya baglaniyordu.

Iddialar (Windows'ta; baska platformda atlanir):
  1. kapat() sonrasi profili kullanan HIC Edge sureci kalmaz, profil dizini silinir
  2. iki Tarayici ayni anda acilinca farkli portlar kullanir (sabit port yok)
  3. kapat() cagrilmadan cikan surec (istisna) da temizlenir (atexit)
  4. kapat() iki kez cagrilabilir (hata yok)

    python test_tarayici.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
import tarayici as T  # noqa: E402

gecen = kalan = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecen, kalan
    if kosul:
        gecen += 1
        print(f"[OK] {ad}  {ek}".rstrip())
    else:
        kalan += 1
        print(f"[!!] {ad}  {ek}".rstrip())


def profil_surecleri(profil: str) -> list[int]:
    """Komut satirinda bu profil dizini gecen msedge sureclerinin PID'leri."""
    ad = Path(profil).name
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
         f"Where-Object {{ $_.CommandLine -like '*{ad}*' }} | ForEach-Object {{ $_.ProcessId }}"],
        capture_output=True, text=True, timeout=60)
    return [int(x) for x in r.stdout.split() if x.strip().isdigit()]


def bekle_bos(profil: str, sn: float = 8.0) -> list[int]:
    son = time.monotonic() + sn
    while True:
        p = profil_surecleri(profil)
        if not p or time.monotonic() > son:
            return p
        time.sleep(0.5)


def main() -> int:
    if sys.platform != "win32":
        print("Windows degil: atlandi")
        return 0

    # 1 + 4: tek tarayici, normal kapanis, iki kez kapat
    t = T.Tarayici()
    profil = t.profil
    t.git("about:blank")
    acikken = profil_surecleri(profil)
    t.kapat()
    t.kapat()                                    # 4: ikinci cagri sessiz
    kalan_p = bekle_bos(profil)
    ok("1. kapat() sonrasi profili kullanan Edge sureci KALMAZ (acikken vardi)",
       bool(acikken) and not kalan_p, f"acikken={len(acikken)} sonra={kalan_p}")
    ok("1. kapat() profil dizinini siler", not Path(profil).exists(), profil)

    # 2: iki tarayici ayni anda — farkli portlar
    a = T.Tarayici()
    b = T.Tarayici()
    try:
        pa, pb = a.port, b.port
        ua = a.js("location.href")
        ub = b.js("location.href")
    finally:
        a.kapat()
        b.kapat()
    ok("2. iki Tarayici ayni anda FARKLI portta ve ikisi de calisiyor (sabit 9333 yok)",
       pa != pb and ua == ub == "about:blank", f"{pa} {pb}")
    ok("2. ikisinin de surecleri temizlendi",
       not bekle_bos(a.profil) and not bekle_bos(b.profil))

    # 3: kapat() cagirmadan istisnayla cikan surec
    kod = ("import sys; sys.path.insert(0, r'%s'); import tarayici as T; "
           "t = T.Tarayici(); print(t.profil, flush=True); raise RuntimeError('cokme')") % BURASI
    r = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, timeout=120)
    p3 = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
    ok("3. cocuk surec istisnayla cikti (kapat cagrilmadi)", r.returncode != 0 and bool(p3),
       f"rc={r.returncode}")
    kalan3 = bekle_bos(p3) if p3 else ["?"]
    ok("3. kapat() cagrilmadan cikan surecin Edge'i de temizlendi (atexit)",
       bool(p3) and not kalan3 and not Path(p3).exists(), f"{kalan3}")

    print(f"\n{gecen}/{gecen + kalan} dogrulama gecti")
    return 0 if kalan == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
