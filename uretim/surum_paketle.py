# -*- coding: utf-8 -*-
"""SURUM PAKETLE — GitHub Releases'e yuklenecek dosyalari uretir ve KISISEL IZ icin tarar.

    python uretim/surum_paketle.py 3.0.1                 # cikis: <depo>/../olcum-karti-surum/v3.0.1/
    python uretim/surum_paketle.py 3.0.1 --cikis D:/x    # baska klasor
    python uretim/surum_paketle.py 3.0.1 --apk-yok       # imzali APK olmadan (yalniz kart + PC)
    python uretim/surum_paketle.py 3.0.1 --kirli         # commit'lenmemis degisiklik varken de (denemek icin)

Uretilenler (ada gore sirali — GitHub dosyalari alfabetik dizer):
    olcum-karti-v<S>-android.apk              imzali APK (once: mobil/araclar/surum_apk.ps1)
    olcum-karti-v<S>-bilgisayar.zip           PC uygulamasi (git archive: kopru, arayuz3, ortak/src)
    olcum-karti-v<S>-kart-1-firmware.bin      0x10000
    olcum-karti-v<S>-kart-2-panel.bin         0x310000 (LittleFS)
    olcum-karti-v<S>-kart-3-bootloader.bin    0x0      (yalniz bos karta)
    olcum-karti-v<S>-kart-4-partitions.bin    0x8000   (yalniz bos karta)
    SHA256SUMS.txt

🔴 NEDEN BETIK (DEVIR 5.12.125): v3.0.0 hazirlanirken firmware ikilisinde derleyen makinenin KULLANICI
   KLASORU YOLU bulundu — arduino-cli, assert `__FILE__` dizgilerine Arduino15 paket yolunu oldugu gibi
   gomuyor. Depo herkese acik; iz yayina cikmadan once elle yakalandi. Bu betik firmware'i
   `-ffile-prefix-map` ile derler ve HER ciktiyi tarar; iz bulursa KIRMIZI cikar, dosyalari SILER.

⚠ VERILMEYENLER: `*.merged.bin` (0x0'a yazilinca NVS'i — parolalari, kalibrasyonu — siler) ve tam flas
   yedekleri (`tam-*.bin`; NVS'i ICERIR). `.elf` / `.map` yerel yol tasir, cikis klasorune girmez.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))

import hedef2                                           # noqa: E402
import yukle                                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PC_YOLLAR = ("kopru", "arayuz3", "ortak/src", "LICENSE", "README.md", "README.en.md")
APK_YOLU = KOK / "mobil" / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
ESPOSTA = re.compile(rb"[A-Za-z0-9._%+-]+@(gmail|hotmail|outlook|yahoo|icloud|proton)[A-Za-z0-9.-]*\.[a-z]{2,}", re.I)


def yerel_kokler() -> list[str]:
    """Derleyicinin dizgilere gomebilecegi yerel kok dizinler (ters ve duz boluyle)."""
    aday = [Path(os.environ.get("LOCALAPPDATA", "")) / "Arduino15", Path(os.environ.get("USERPROFILE", "")),
            KOK.parents[1], KOK]
    cik: list[str] = []
    for a in aday:
        s = str(a)
        if len(s) < 4:
            continue
        for b in (s, s.replace("\\", "/")):
            if b not in cik:
                cik.append(b)
    return cik


def iz_desenleri() -> list[tuple[str, re.Pattern]]:
    """Ciktilarda ARANAN kisisel izler. Kullanici adi yalniz YOL biciminde aranir (LICENSE'taki ad iz degil)."""
    d = [("kullanici klasoru", re.compile(rb"[A-Za-z]:[\\/]+Users[\\/]", re.I)),
         ("ev dizini", re.compile(rb"/(home|Users)/[A-Za-z0-9_.-]+/")),
         ("e-posta", ESPOSTA)]
    kul = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if len(kul) >= 3:
        d.append(("kullanici adi (yol)", re.compile(rb"[\\/]" + re.escape(kul.encode()) + rb"[\\/]", re.I)))
    alan = KOK.parents[1].name
    if len(alan) >= 4:
        d.append(("calisma alani (yol)", re.compile(rb"[\\/]" + re.escape(alan.encode()) + rb"[\\/]", re.I)))
    return d


def tara(dosya: Path) -> list[str]:
    """Bir cikti dosyasindaki izler (zip / apk ise icindeki her dosya ve dosya adi)."""
    parcalar: list[tuple[str, bytes]] = []
    if dosya.suffix in (".zip", ".apk"):
        with zipfile.ZipFile(dosya) as z:
            for ad in z.namelist():
                parcalar.append((ad, z.read(ad)))
                parcalar.append((ad + " (ad)", ad.encode("utf-8", "replace")))
    else:
        parcalar.append((dosya.name, dosya.read_bytes()))
    bulgu = []
    for ad, veri in parcalar:
        for ne, desen in iz_desenleri():
            m = desen.search(veri)
            if m:
                bulgu.append(f"{ne}: {ad[-60:]} @ {m.start()}")
    return bulgu


def kos(komut: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(komut, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def firmware(cikis: Path, on: str) -> None:
    bayrak = " ".join(f"-ffile-prefix-map={k}=y{i // 2}" for i, k in enumerate(yerel_kokler()))
    with tempfile.TemporaryDirectory() as gecici:
        r = kos([str(yukle.ARDUINO_CLI), "compile", "--warnings", "all", "--fqbn", hedef2.FQBN, "--clean",
                 "--build-property", "compiler.c.extra_flags=" + bayrak,
                 "--build-property", "compiler.cpp.extra_flags=" + bayrak,
                 "--output-dir", gecici, str(yukle.ESKIZ)])
        if r.returncode != 0:
            raise SystemExit("firmware derlenemedi:\n" + (r.stderr or r.stdout)[-600:])
        g = Path(gecici)
        ad = yukle.ESKIZ.name + ".ino"
        shutil.copyfile(g / f"{ad}.bin", cikis / f"{on}-kart-1-firmware.bin")
        shutil.copyfile(g / f"{ad}.bootloader.bin", cikis / f"{on}-kart-3-bootloader.bin")
        shutil.copyfile(g / f"{ad}.partitions.bin", cikis / f"{on}-kart-4-partitions.bin")


def panel(cikis: Path, on: str) -> None:
    r = kos([sys.executable, str(BURASI / "arayuz-uret.py")], cwd=str(BURASI))
    if r.returncode != 0:
        raise SystemExit("panel goruntusu uretilemedi:\n" + (r.stderr or r.stdout)[-600:])
    shutil.copyfile(BURASI / "_fs.bin", cikis / f"{on}-kart-2-panel.bin")
    d = kos(["git", "-C", str(KOK), "status", "--porcelain", "--", "uretim/_fs.json", "arayuz3/sw.js"]).stdout.strip()
    if d:
        raise SystemExit("panel yeniden uretilince _fs.json / sw.js DEGISTI — once onlari commit'le:\n" + d)


def pc_zip(cikis: Path, on: str, surum: str) -> None:
    r = kos(["git", "-C", str(KOK), "archive", "--format=zip", f"--prefix=olcum-karti-pc-v{surum}/",
             "-o", str(cikis / f"{on}-bilgisayar.zip"), "HEAD", *PC_YOLLAR])
    if r.returncode != 0:
        raise SystemExit("PC zip'i uretilemedi:\n" + r.stderr[-400:])


def apk(cikis: Path, on: str, surum: str) -> None:
    if not APK_YOLU.exists():
        raise SystemExit(f"imzali APK yok: {APK_YOLU}\n  once: mobil\\araclar\\surum_apk.ps1 -Depo <anahtar.jks>  (ya da --apk-yok)")
    gradle = (KOK / "mobil" / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
    if f'versionName "{surum}"' not in gradle:
        raise SystemExit(f"mobil/android/app/build.gradle versionName {surum} DEGIL — once surumu guncelle ve APK'yi yeniden derle")
    # v2+ imza APK'nin sonundaki "APK Sig Block 42" blogunda durur (minSdk 28: v1 / META-INF imzasi YOK).
    if b"APK Sig Block 42" not in APK_YOLU.read_bytes():
        raise SystemExit("APK imzasiz gorunuyor (imza blogu yok) — surum_apk.ps1 ile derle")
    shutil.copyfile(APK_YOLU, cikis / f"{on}-android.apk")


def main(argv: list[str] | None = None) -> int:
    a = sys.argv[1:] if argv is None else argv
    surum = next((x for x in a if not x.startswith("--") and re.fullmatch(r"\d+\.\d+\.\d+", x)), None)
    if not surum:
        print(__doc__)
        return 2
    cikis = Path(a[a.index("--cikis") + 1]) if "--cikis" in a else KOK.parent / "olcum-karti-surum" / f"v{surum}"
    kirli = kos(["git", "-C", str(KOK), "status", "--porcelain", "--untracked-files=no"]).stdout.strip()
    if kirli and "--kirli" not in a:
        print("RED: commit'lenmemis degisiklik var (PC zip'i HEAD'den alinir, firmware calisma agacindan):\n" + kirli[:400])
        return 1
    cikis.mkdir(parents=True, exist_ok=True)
    on = f"olcum-karti-v{surum}"
    print(f"SURUM PAKETLE v{surum} -> {cikis.name}/")
    firmware(cikis, on)
    print("  firmware derlendi (yerel yollar haritalandi)")
    panel(cikis, on)
    print("  panel goruntusu")
    pc_zip(cikis, on, surum)
    print("  PC zip'i (git archive HEAD)")
    if "--apk-yok" not in a:
        apk(cikis, on, surum)
        print("  imzali APK")
    dosyalar = sorted(cikis.glob(on + "-*"), key=lambda p: p.name.lower())
    kotu = {d.name: tara(d) for d in dosyalar}
    kotu = {k: v for k, v in kotu.items() if v}
    if kotu:
        for k, v in kotu.items():
            print(f"  [!!] KISISEL IZ — {k}: " + "; ".join(v[:4]))
            (cikis / k).unlink()
        print("KIRMIZI: izli dosyalar SILINDI, hicbiri yayinlanmamali.")
        return 1
    (cikis / "SHA256SUMS.txt").write_bytes(
        ("\n".join(f"{hashlib.sha256(d.read_bytes()).hexdigest()}  {d.name}" for d in dosyalar) + "\n").encode())
    for d in dosyalar:
        print(f"  [OK] {d.name:<44} {d.stat().st_size:>9} B  kisisel iz yok")
    print(f"\n{len(dosyalar)} dosya + SHA256SUMS.txt hazir: {cikis}")
    print("Sirada: `git tag -a v%s` + push, sonra GitHub -> Releases'e bu dosyalari yukle." % surum)
    print("⚠ Bu firmware ikilisini YAYINLAMADAN ONCE karta yukleyip dene (arduino-cli upload --input-dir ya da esptool).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
