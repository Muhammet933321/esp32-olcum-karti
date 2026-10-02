"""B73 — `ortak/` (alt proje 2): JS hesap kodu Python basvurusuyla BAYT BAYT ayni mi.

    python test_ortak.py

Tasarim: tasarim/2026-10-02-alt-proje-2-ortak.md (O1-O8).
  1. Her `uretim/ortak_vektor_<dilim>.py --denetle`: depodaki JSON vektorleri Python
     basvurusuyla (kartla dogrulanmis kopru/*.py) HALA ayni.
  2. `node --test ortak/test/<dosya>`: JS o vektorlerle ve RFC/NIST vektorleriyle ayni.
  3. Yapi: her src modulunun testi var; src'de Node'a ozgu API YOK (tarayici + Capacitor
     ayni dosyayi yukler); package.json BAGIMLILIKSIZ.
Donanim gerekmiyor.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ORTAK = KOK / "ortak"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(BURASI))
from tezgah import tezgah  # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> bool:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))
    return kosul


def yapi() -> list[str]:
    print("\n── B73.Y  yapi: bagimliliksiz, tarayici uyumlu, her modulun testi var")
    p = ORTAK / "package.json"
    pj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    ok("B73.Y1 ortak/package.json yalniz ES modulu bildirir, BAGIMLILIK YOK (O1)",
       pj.get("type") == "module" and not any(k in pj for k in
                                               ("dependencies", "devDependencies", "peerDependencies")),
       str(pj))
    src = sorted((ORTAK / "src").glob("*.js")) if (ORTAK / "src").exists() else []
    ok("B73.Y2 ortak/src'de modul var", bool(src), ", ".join(s.name for s in src))
    eksik = [s.name for s in src if not (ORTAK / "test" / f"{s.stem}.test.js").exists()]
    ok("B73.Y3 her src modulunun ortak/test/<ad>.test.js testi var", not eksik, f"eksik: {eksik}")
    yasak = re.compile(r"\brequire\(|from\s+['\"]node:|\bprocess\.|\bBuffer\b|crypto\.subtle|"
                       r"import\(\s*['\"]node:")
    nodeca = [s.name for s in src if yasak.search(re.sub(r"//.*|/\*.*?\*/", "",
                                                           s.read_text(encoding="utf-8"), flags=re.S))]
    ok("B73.Y4 src'de Node'a ozgu API ve crypto.subtle YOK (tarayici/Capacitor; O1, O6)",
       not nodeca, f"kullanan: {nodeca}")
    return [s.stem for s in src]


def vektorler() -> None:
    print("\n── B73.V  capraz vektorler Python basvurusuyla HALA ayni (O3)")
    ureteciler = sorted(BURASI.glob("ortak_vektor_*.py"))
    ok("B73.V0 vektor ureteci var", bool(ureteciler), ", ".join(u.name for u in ureteciler))
    for u in ureteciler:
        dilim = u.stem.replace("ortak_vektor_", "")
        r = subprocess.run([sys.executable, u.name, "--denetle"], cwd=BURASI, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=900)
        ok(f"B73.V.{dilim} {u.name} --denetle: ortak/test/vektor/{dilim}.json Python'la ayni",
           r.returncode == 0 and (ORTAK / "test" / "vektor" / f"{dilim}.json").exists(),
           (r.stdout + r.stderr).strip().splitlines()[-1][:160] if (r.stdout + r.stderr).strip() else "")


def node_testleri(moduller: list[str]) -> None:
    print("\n── B73.N  node --test (JS == vektorler == RFC)")
    try:
        v = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except OSError:
        v = ""
    m = re.match(r"v(\d+)", v)
    if not ok("B73.N0 node >= 18 (yerlesik node:test)", bool(m) and int(m.group(1)) >= 18, v or "yok"):
        return
    for ad in moduller:
        t = ORTAK / "test" / f"{ad}.test.js"
        if not t.exists():
            continue
        # TAP raporlayicisi ACIKCA: Node 24 varsayilani "ℹ pass N" basar, "# pass N" degil
        r = subprocess.run(["node", "--test", "--test-reporter=tap", str(t)], cwd=KOK, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
        cik = r.stdout + r.stderr
        gec = re.search(r"^# pass (\d+)", cik, re.M)
        kal = re.search(r"^# fail (\d+)", cik, re.M)
        n_gec, n_kal = int(gec.group(1)) if gec else 0, int(kal.group(1)) if kal else -1
        ok(f"B73.N.{ad} node --test {t.name}: hepsi gecti", r.returncode == 0 and n_kal == 0 and n_gec > 0,
           f"{n_gec} gecti, {n_kal} kaldi")
        if r.returncode:
            for s in cik.splitlines():
                if s.lstrip().startswith("not ok") or "AssertionError" in s:
                    print("        " + s.strip()[:200])


def main() -> int:
    moduller = yapi()
    vektorler()
    node_testleri(moduller)
    tezgah("B73 ortak/ (JS hesap kodu)", [
        ("Kartin GERCEK akisi JS ile de ayni cozuluyor mu",
         "tezgah_kayit.py --esit ile esitlenen kayit.bin'i hem kopru/kayit_bicim.py hem "
         "ortak/src/kayit.js ile coz; oturumlar, noktalar, volt/amper bit bit ayni"),
        ("[!] Telefonda PBKDF2 suresi (Capacitor WebView)",
         "20 000 tur; spec 'telefonda < 1 s' (yazilim-sistemi §13). Node'daki sure telefonu temsil etmez"),
    ])
    print(f"\nB73: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
