# -*- coding: utf-8 -*-
"""Yayinlanan depoda KISISEL IZ kaldi mi — tek komutla tara.

    python gizlilik_dogrula.py        (0 = temiz, 1 = iz var)

🔴 NEDEN VAR (B26, 2026-09-12). Depo herkese acik. Kural
`dogrula3.py`nin icinde bir YORUM olarak yaziliydi — ve yorum kurali
KORUMAZ. Bagimsiz bir gizlilik denetimi HEAD'de 59 mutlak yol buldu:

  * `uretim/b15-arastirma.md`      56 kez  ("**Yer:** <mutlak yol>")
  * `arsiv/*/tam-dogrulama.txt`     2 kez  (ureteç gunlugu)
  * `uretim/netlist{,2,3}.net`      3 kez  (kicad-cli `(source ...)`)

Netlist'lerdeki temizlik VARDI ama ISE YARAMIYORDU: B3'te uygulaniyor,
B9 netlist'i DAHA SONRA yeniden uretiyordu. (Artik `netlist_temizle.py`
her uretim yerinde cagriliyor.)

⚠ GREP BU ORTAMDA GUVENILMEZ. Denetim ajani `grep -i` ile birden fazla
`-e` deseninin COKTUGUNU (`Aborted`, rc=134) ve `2>/dev/null` varsa
SESSIZCE BOS sonuc verdigini bildirdi; kendi taramam da bu yuzden
"temiz" demisti. Bu betik saf Python okur — desen basina tek gecis.

NE ARANIR / NE ARANMAZ
  ARANIR : mutlak Windows yollari (kullanici klasoru ya da proje koku),
           WiFi/AP/web parolalari, e-posta adresleri, tam MAC adresleri
  ARANMAZ: `Muhammet933321` (GitHub kullanici adi, zaten aleni),
           LICENSE'taki telif sahibi adi, `192.168.4.1` (ESP32 SoftAP
           evrensel varsayilani), `Path.home()` / `LOCALAPPDATA` gibi
           ortam degiskenli yollar — bunlar kullanici adi tasimaz.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
B = chr(92)

# (ad, derlenmis desen, aciklama)
DESENLER = [
    ("Mutlak Windows yolu (kullanici klasoru)",
     re.compile(r"[Cc]:" + re.escape(B) + r"{1,2}[Uu]sers" + re.escape(B),
                re.I),
     "kullanici hesap adini acik eder"),
    ("Mutlak Windows yolu (proje koku)",
     re.compile(r"[Cc]:" + re.escape(B) + r"{1,2}[Mm]uhammet" + re.escape(B),
                re.I),
     "diskteki klasor duzenini acik eder; klonlayan icin de ISE YARAMAZ"),
    ("E-posta adresi",
     re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),
     "commit yazari ayri — bu, DOSYA ICINDEKI adres"),
    ("Tam MAC adresi",
     re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
     "cihaza ozgu kimlik"),
]

# Bilerek gecen, sir OLMAYAN degerler.
BEYAZ = (
    "02:00:00:00",          # sentetik test MAC'i (yerel yonetimli OUI)
    "noreply@anthropic.com",
    "users.noreply.github.com",
)


def _gitignore_desenleri() -> list[str]:
    p = KOK / ".gitignore"
    if not p.exists():
        return []
    return [s.strip() for s in p.read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.startswith("#")]


def _yok_sayilir(goreli: str, desenler: list[str]) -> bool:
    """`.gitignore`nin kaba bir esi — yalnizca burada gereken kadar."""
    import fnmatch
    parcalar = goreli.split("/")
    for d in desenler:
        d = d.lstrip("/")
        if d.endswith("/"):                      # klasor deseni
            k = d.rstrip("/").replace("**/", "")
            if any(fnmatch.fnmatch(x, k) for x in parcalar[:-1]) \
               or goreli.startswith(k + "/"):
                return True
        elif "/" in d:                            # yol deseni
            if fnmatch.fnmatch(goreli, d) or fnmatch.fnmatch(goreli, d + "*"):
                return True
        elif fnmatch.fnmatch(parcalar[-1], d):    # dosya adi deseni
            return True
    return False


def takip_edilenler() -> list[str]:
    """`git ls-files`; git yoksa agaci `.gitignore`ye gore yuru.

    ⚠ Fallback SART: `mutasyon.py` projeyi `.git` OLMADAN kopyaliyor.
    Fallback olmasaydi kopyada 0 dosya taranir, "temiz" denir ve bu
    betigin kendi mutasyonu KACARDI — yani denetim kendini sinayamazdi.
    """
    u = subprocess.run(["git", "ls-files"], cwd=KOK,
                       capture_output=True, text=True)
    # ⚠ splitlines(), split() DEGIL: "Kopru Baslat.bat" bosluk iceriyor,
    #   split() onu iki sahte yola bolup dosyayi TARAMADAN geciyordu.
    liste = [x for x in u.stdout.splitlines() if x.strip()]
    if liste:
        return liste
    desenler = _gitignore_desenleri() + [".git/"]
    cikti = []
    for p in KOK.rglob("*"):
        if not p.is_file():
            continue
        g = p.relative_to(KOK).as_posix()
        if not _yok_sayilir(g, desenler):
            cikti.append(g)
    return cikti


def main() -> int:
    dosyalar = takip_edilenler()
    print("=" * 78)
    print("  GIZLILIK — yayinlanan depoda kisisel iz var mi?")
    print("=" * 78)
    print(f"  {len(dosyalar)} takip edilen dosya\n")

    toplam = 0
    for ad, desen, neden in DESENLER:
        bulgu: list[tuple[str, int, str]] = []
        for f in dosyalar:
            p = KOK / f
            if not p.exists():
                continue
            try:
                metin = p.read_bytes().decode("utf-8", "replace")
            except OSError:
                continue
            for i, satir in enumerate(metin.splitlines(), 1):
                for m in desen.finditer(satir):
                    if any(b in m.group(0) for b in BEYAZ):
                        continue
                    bulgu.append((f, i, m.group(0)[:60]))
        if bulgu:
            toplam += len(bulgu)
            print(f"  [!!] {ad}: {len(bulgu)} gecis — {neden}")
            for f, i, s in bulgu[:8]:
                print(f"         {f}:{i}  {s}")
            if len(bulgu) > 8:
                print(f"         ... ve {len(bulgu) - 8} tane daha")
        else:
            print(f"  [OK] {ad}: temiz")

    print()
    if toplam:
        print(f"  KIRMIZI: {toplam} kisisel iz — yayinlamadan once temizle.")
        return 1
    print("  Temiz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
