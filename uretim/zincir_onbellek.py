# -*- coding: utf-8 -*-
"""ARTIMLI ZINCIR — degismeyen adimin YESIL sonucunu yeniden kullan (HIZ, 2026-10-03).

    python dogrula3.py --artimli      degismeyen adimlar onbellekten
    python dogrula3.py                TAM kosu (varsayilan; onbellegi de tazeler)
    python dogrula3.py --artimli --tam   hepsini kos

── NE ZAMAN YENIDEN KULLANILIR ──────────────────────────────────────

Bir adimin onbellek kaydi ancak HEPSI tutarsa kullanilir:
  * kayit YESIL bir kosudan (kirmizi adim hic saklanmaz)
  * ayni proje koku (mutasyon kopyasi asil agacin kaydini KULLANAMAZ)
  * ayni "genel anahtar": dogrula3.py + bu dosya + kanca dosyalari + Python
    surumu + ilgili ortam degiskenleri + adim basligi
  * adimin GERCEKTEN OKUDUGU her dosyanin icerigi (sha256) ayni
  * adimin LISTELEDIGI her dizinin ad listesi ayni
  * adimin varligina BAKTIGI her yolun var/yok durumu ayni
  * adimin YAZDIGI kalici her dosya (BELGELER, sema, netlist ...) hala
    adimin biraktigi icerikte (silinmis/degismis cikti -> yeniden uret)
  * cagirdigi her disaridan aracin (kicad-cli, avr-gcc, arduino-cli ...)
    ikilisi + kurulum dizini imzasi ayni
  * kayit 24 saatten genc
ve adim "HER ZAMAN KOS" diye isaretlenmemis. Biri tutmazsa adim KOSAR ve
sebebi basilir.

── GIRDI KESFI (elle liste YOK, KANIT) ───────────────────────────────

Adimin komutlari `izli_ortam()` ile kosar:
  * PYTHONPATH'in basinda `zincir_kanca/` -> her Python sureci (alt surecleri
    ve onlarin alt surecleri dahil, ortam miras kaldigi icin) `sitecustomize`
    ile `sys.addaudithook` kurar ve actigi/yazdigi/listeledigi/yokladigi her
    yolu, actigi her sureci IZ dizinine yazar.
  * NODE_OPTIONS=--require node_kanca.cjs -> node sureçleri (node --test'in
    alt surecleri dahil) ayni seyi fs / module.registerHooks / child_process
    uzerinden yazar.
  * Python OLMAYAN, node OLMAYAN araclar (kendi okumalarini goremeyiz) icin
    `ARAC_KURALLARI`: argumandaki her yol + aracin "isaret edildigi" dizinler
    girdi sayilir (derleyici: deponun BUTUN C ailesi dosyalari; kicad-cli:
    semanin dizini + KiCad kullanici ayarlari). Kurali olmayan arac -> adim
    HER ZAMAN KOSAR.
  * SAYIM DENETIMI: acilan her Python/node sureci bir rapor yazmak zorunda.
    Eksik rapor (ortami silinen alt surec, -I bayragi, os.system, Popen disi
    surec acilisi) -> girdiler SINIRLANAMAZ -> adim HER ZAMAN KOSAR.

⚠ KALAN RISKLER (DEVIR 5.12.9x HIZ): araclarin KENDI kurulum dosyalari (ESP32
  cekirdegi, avr-libc, KiCad kutuphaneleri) yalnizca ikili + dizin imzasiyla
  izleniyor; sys.path'e yeni bir golge modul eklenmesi (importlib'in kendi
  listelemeleri sayilmiyor); saat/tarih ya da tohumsuz rastgelelige bagli
  davranis. Ucunu de 24 saat kurali ve TAM kosu sinirliyor.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
KANCA_DIZIN = BURASI / "zincir_kanca"
ONBELLEK_YOLU = BURASI / ".zincir_onbellek.json"
IZ_ORTAM = "OLCUM_ZINCIR_IZ"
SURUM = 1
AZAMI_YAS_SN = 24 * 3600
# Bu ucunden biri son TAM kosudan beri degistiyse artimli kosu reddedilir, TAM kosar.
TAM_TETIK = ("uretim/dogrula3.py", "uretim/mutasyon.py", "uretim/tasarim3_sabit.py")
BUYUK_DOSYA = 64 * 1024 * 1024        # ustu icerik yerine (boyut, mtime) imzasi

# dogrula3.py'nin cop toplayicisinin sildikleri — girdi/cikti sayilmaz (her kosu
# siliniyor; sayilsa hicbir adim yeniden kullanilamazdi). TEK KAYNAK: dogrula3
# temizligi de bunu kullaniyor.
COP_HER_YERDE = ("__pycache__",)
COP_URETIM_KOPRU = ("_b[0-9]*", "_chk*", "_lk*", "__pycache__")
COP_URETIM_DOSYA = ("_a4_*.elf", "erc*.rpt")
COP_BUILD = ("kod/olcum-karti-a3/build", "arsiv/asama2/olcum-karti-a2/build",
             "arsiv/asama1/olcum-karti/build")

ORTAM_ANAHTARLARI = ("PATH", "PATHEXT", "SYSTEMROOT", "COMSPEC", "LOCALAPPDATA", "APPDATA",
                     "USERPROFILE", "HOME", "LANG", "TZ")
ORTAM_ONEKLERI = ("PYTHON", "NODE_", "OLCUM_", "LC_")
# kancanin kendi kurdugu / degistirdigi
ORTAM_HARIC = {IZ_ORTAM, "PYTHONPATH", "NODE_OPTIONS"}

PY_ADLAR = {"python", "pythonw", "py", "python3", "pyw"}
NODE_ADLAR = {"node"}
DERLEYICI = re.compile(
    r"^(?:avr-[\w+.-]+|xtensa-[\w+.-]+|riscv32-[\w+.-]+|arm-none-eabi-[\w+.-]+|arduino-cli|"
    r"gcc|g\+\+|cc|c\+\+|cpp|ld|as|objdump|nm|size|ar|ranlib|esptool)$", re.I)
C_AILESI = {".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".ino", ".s", ".inc", ".ld",
            ".tpp", ".ipp", ".def"}
KICAD = {"kicad-cli"}
# ctypes ile yuklenip GIRDI OKUMAYAN sistem kutuphaneleri
SISTEM_DLL = {"kernel32", "user32", "shell32", "advapi32", "ole32", "oleaut32", "msvcrt", "ntdll",
              "ws2_32", "iphlpapi", "bcrypt", "combase", "shlwapi", "winmm", "gdi32", "comctl32",
              "dwmapi", "uxtheme", "secur32", "crypt32", "version", "psapi", "setupapi",
              "cfgmgr32", "hid", "winhttp", "wininet", "userenv", "msvcp140", "vcruntime140",
              "ucrtbase", "api-ms-win-core-path-l1-1-0", "kernelbase"}
OUTPUT_BAYRAK = {"-o", "--output", "--build-path", "--out", "-O", "--output-dir",
                 "--export-dir", "--build-cache-path"}


# ── yardimcilar ───────────────────────────────────────────────────────
def _nc(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def sha_dosya(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def sha_metin(*parcalar) -> str:
    h = hashlib.sha256()
    for x in parcalar:
        h.update(str(x).encode("utf-8", "replace"))
        h.update(b"\x00")
    return h.hexdigest()


def komut_ayir(komut) -> list[str]:
    """Windows komut satirini argv'ye ayir (CommandLineToArgvW ile ayni kural)."""
    if isinstance(komut, list):
        return [str(x) for x in komut]
    if not komut:
        return []
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        f = ctypes.windll.shell32.CommandLineToArgvW
        f.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        f.restype = ctypes.POINTER(wintypes.LPWSTR)
        n = ctypes.c_int()
        dizi = f(str(komut), ctypes.byref(n))
        try:
            return [dizi[i] for i in range(n.value)]
        finally:
            ctypes.windll.kernel32.LocalFree(dizi)
    import shlex
    return shlex.split(komut)


def arac_adi(argv0: str) -> str:
    ad = os.path.basename(str(argv0).strip('"')).lower()
    for son in (".exe", ".cmd", ".bat", ".dll"):
        if ad.endswith(son):
            ad = ad[: -len(son)]
    return ad


def arac_yolu(argv0: str, cwd: str | None) -> str | None:
    a = str(argv0).strip('"')
    if os.path.isabs(a) and os.path.exists(a):
        return a
    if cwd and os.path.exists(os.path.join(cwd, a)):
        return os.path.join(cwd, a)
    return shutil.which(a)


def izli_ortam(iz_dizin: Path, taban: dict | None = None) -> dict:
    """Komutun ve BUTUN alt sureclerinin girdilerini kaydettiren ortam."""
    ortam = dict(os.environ if taban is None else taban)
    ortam[IZ_ORTAM] = str(iz_dizin)
    eski = ortam.get("PYTHONPATH")
    ortam["PYTHONPATH"] = str(KANCA_DIZIN) + (os.pathsep + eski if eski else "")
    kanca = (KANCA_DIZIN / "node_kanca.cjs").as_posix()
    eski = ortam.get("NODE_OPTIONS")
    ortam["NODE_OPTIONS"] = f'--require "{kanca}"' + (" " + eski if eski else "")
    return ortam


# ── iz okuma ──────────────────────────────────────────────────────────
@dataclass
class Iz:
    oku: set = field(default_factory=set)
    yaz: set = field(default_factory=set)
    liste: set = field(default_factory=set)
    yokla: dict = field(default_factory=dict)
    surecler: list = field(default_factory=list)     # (tur, dict) — kaydedilen surec acilislari
    cp: int = 0
    popen: int = 0
    diger: list = field(default_factory=list)
    dll: set = field(default_factory=set)
    ag: set = field(default_factory=set)
    rapor_py: int = 0
    rapor_node: int = 0
    kanca_hata: list = field(default_factory=list)


def iz_oku(dizin: Path) -> Iz:
    iz = Iz()
    for f in sorted(Path(dizin).glob("*.jsonl")):
        tur = "py" if f.name.startswith("py-") else "node"
        if tur == "py":
            iz.rapor_py += 1
        else:
            iz.rapor_node += 1
        cp = popen = 0
        for satir in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                k = json.loads(satir)
            except ValueError:
                # yarim kalan son satir (oldurulen surec): kayit ONCESINDE yaziliyor, kayip yok
                continue
            t, p = k.get("t"), k.get("p")
            if t == "oku":
                iz.oku.add(p)
            elif t in ("mod", "yukle"):
                iz.oku.add(p)
            elif t == "yaz":
                iz.yaz.add(p)
            elif t == "liste":
                iz.liste.add(p)
            elif t == "yokla":
                iz.yokla.setdefault(p, bool(k.get("e")))
            elif t == "surec":
                d = json.loads(p)
                iz.surecler.append(d)
                popen += 1
            elif t == "cp":
                cp += 1
            elif t == "diger":
                iz.diger.append(p)
            elif t == "dll":
                iz.dll.add(p)
            elif t == "ag":
                iz.ag.add(p)
            elif t == "kanca_hata":
                iz.kanca_hata.append(p)
        if tur == "py":
            iz.cp += cp
            iz.popen += popen
    return iz


# ── haric tutulanlar ──────────────────────────────────────────────────
class Kapsam:
    """Hangi yol girdi/cikti sayilir, hangisi sayilmaz."""

    def __init__(self, kok: Path, ek_haric: list[str] = (), onbellek: Path | None = None):
        self.kok = _nc(str(kok))
        # Onbellegin KENDISI (ve atomik yazimin gecici dosyasi) hicbir adimin girdisi
        # degil — ama adimlarin listeledigi uretim/'de duruyor. Sayilsaydi ilk tam
        # kosudan sonra uretim/'yi listeleyen her adim (B2, B15, B73) "dizin degisti"
        # diye kosardi (olculdu, 2026-10-03).
        self.onbellek_ad = (onbellek or ONBELLEK_YOLU).name
        haric = [tempfile.gettempdir(), os.environ.get("TEMP", ""), os.environ.get("TMP", ""),
                 str(KANCA_DIZIN), os.environ.get("SystemRoot", r"C:\Windows"), *ek_haric]
        taban = _nc(sys.base_prefix)
        self.haric = [_nc(h) for h in haric if h]
        self.py_taban = taban
        self.py_site = _nc(os.path.join(sys.base_prefix, "Lib", "site-packages"))

    def ic(self, p: str) -> str | None:
        """Depo icindeyse POSIX goreli yol, degilse None."""
        n = _nc(p)
        if n == self.kok:
            return "."
        if n.startswith(self.kok + os.sep):
            return n[len(self.kok) + 1:].replace(os.sep, "/")
        return None

    def cop_mu(self, p: str) -> bool:
        parcalar = _nc(p).split(os.sep)
        if any(x in COP_HER_YERDE for x in parcalar) or p.lower().endswith((".pyc", ".pyo")):
            return True
        g = self.ic(p)
        if g is None:
            return False
        ust = g.split("/")
        for b in COP_BUILD:
            if g == b or g.startswith(b + "/"):
                return True
        # dogrula3.cop_topla() bu kaliplari uretim/ ve kopru/ altinda HER DERINLIKTE
        # (rglob) siler; `arsiv` iceren yollar haric (kullanicinin olcum gunlugu)
        if ust[0] in ("uretim", "kopru") and len(ust) > 1 and "arsiv" not in ust:
            if any(fnmatch.fnmatch(x, k) for x in ust[1:] for k in COP_URETIM_KOPRU):
                return True
        if ust[0] == "uretim" and len(ust) == 2:
            if any(fnmatch.fnmatch(ust[1], k) for k in COP_URETIM_DOSYA):
                return True
        return False

    def yoksay(self, p: str) -> bool:
        """cop + onbellek dosyalari: liste/agac imzasina girmez."""
        return self.cop_mu(p) or os.path.basename(p).startswith(self.onbellek_ad)

    def sayilmaz(self, p: str) -> bool:
        n = _nc(p)
        if os.path.basename(p).startswith(self.onbellek_ad):
            return True
        if self.ic(p) is not None:
            return self.cop_mu(p) or n.startswith(_nc(str(KANCA_DIZIN)))
        if any(n == h or n.startswith(h + os.sep) for h in self.haric):
            return True
        if (n == self.py_taban or n.startswith(self.py_taban + os.sep)) and not (
                n.startswith(self.py_site + os.sep)):
            return True
        return self.cop_mu(p)


def pyc_kaynak(p: str) -> str:
    """__pycache__/x.cpython-314.pyc -> x.py"""
    pp = Path(p)
    if pp.suffix.lower() in (".pyc", ".pyo") and pp.parent.name == "__pycache__":
        return str(pp.parent.parent / (pp.name.split(".")[0] + ".py"))
    return p


# ── cozumleme: iz -> girdi kumesi ─────────────────────────────────────
@dataclass
class Girdiler:
    dosya: set = field(default_factory=set)          # icerik imzasi
    dizin_agac: set = field(default_factory=set)     # tum agac icerigi (araclarin isaret ettigi)
    liste: set = field(default_factory=set)          # ad listesi
    yokla: dict = field(default_factory=dict)        # yol -> var mi
    arac: set = field(default_factory=set)           # ikili (boyut, mtime) imzasi
    kurulum: set = field(default_factory=set)        # (dizin, derinlik) — ad+boyut+mtime listesi
    cikti: set = field(default_factory=set)          # kalici cikti dosyalari
    her_zaman: list = field(default_factory=list)    # bos degilse adim HER ZAMAN KOSAR


def _yol_argumanlari(argv: list[str], cwd: str | None) -> tuple[list[str], list[str]]:
    """Arac argumanlarindaki VAR olan yollar: (girdiler, ciktilar)."""
    gir, cik = [], []
    cikti_bekle = False
    for a in argv[1:]:
        aday = [a]
        if a.startswith("-") and "=" in a:
            bayrak, deger = a.split("=", 1)
            aday = [deger]
            if bayrak in OUTPUT_BAYRAK:
                for x in aday:
                    cik.append(os.path.join(cwd or ".", x) if not os.path.isabs(x) else x)
                continue
        elif re.match(r"^-[ILBo]\S", a) or re.match(r"^-include\S", a):
            aday = [a[2:]] if not a.startswith("-include") else [a[8:]]
        if a.startswith("@"):
            aday = [a[1:]]
        if cikti_bekle:
            cikti_bekle = False
            cik.append(os.path.join(cwd or ".", a) if not os.path.isabs(a) else a)
            continue
        if a in OUTPUT_BAYRAK:
            cikti_bekle = True
            continue
        for x in aday:
            if not x or x.startswith("-"):
                continue
            y = x if os.path.isabs(x) else os.path.join(cwd or ".", x)
            try:
                if os.path.exists(y):
                    gir.append(os.path.abspath(y))
            except (OSError, ValueError):
                pass
    return gir, cik


def _c_ailesi(kok: Path, kapsam: Kapsam) -> set[str]:
    bul = set()
    for d, alt, dosyalar in os.walk(kok):
        alt[:] = [x for x in alt if x not in (".git", "BELGELER", "__pycache__", "node_modules")
                  and not kapsam.cop_mu(os.path.join(d, x))]
        for f in dosyalar:
            if os.path.splitext(f)[1].lower() in C_AILESI or f.lower() == "partitions.csv":
                bul.add(os.path.join(d, f))
    return bul


def cozumle(iz: Iz, kok: Path, kokler: list[dict], kapsam: Kapsam | None = None) -> Girdiler:
    """Iz + adimin kendi kostugu kok komutlar -> girdi kumesi.

    kokler: [{"komut": argv, "cwd": ...}] — dogrula3'un dogrudan actigi surecler."""
    kapsam = kapsam or Kapsam(kok)
    g = Girdiler()
    yazilan = {_nc(p) for p in iz.yaz}

    # 1. surec sayimi: her Python/node sureci rapor yazmali
    acilan = [dict(s, kok=False) for s in iz.surecler] + [dict(s, kok=True, iz=True) for s in kokler]
    bekle_py = bekle_node = 0
    for s in acilan:
        argv = komut_ayir(s.get("komut"))
        if not argv:
            g.her_zaman.append(f"bos komut: {s!r}"[:200])
            continue
        exe = s.get("exe") or argv[0]
        ad = arac_adi(exe)
        cwd = s.get("cwd")
        if s.get("kabuk") or ad in ("cmd", "powershell", "pwsh", "bash", "sh"):
            g.her_zaman.append(f"kabuk ile surec: {' '.join(argv)[:160]}")
            continue
        if ad in PY_ADLAR:
            if not s.get("iz", True):
                g.her_zaman.append(f"Python alt sureci iz ortamini dusurdu: {' '.join(argv)[:160]}")
            bekle_py += 1
            continue
        if ad in NODE_ADLAR:
            if not s.get("iz", True):
                g.her_zaman.append(f"node alt sureci iz ortamini dusurdu: {' '.join(argv)[:160]}")
            bekle_node += 1
            continue
        yol = arac_yolu(exe, cwd)
        if yol:
            g.arac.add(os.path.abspath(yol))
        if DERLEYICI.match(ad):
            gir, cik = _yol_argumanlari(argv, cwd)
            for x in gir:
                (g.dizin_agac if os.path.isdir(x) else g.dosya).add(x)
            g.cikti.update(cik)
            g.dosya.update(_c_ailesi(kok, kapsam))
            if ad == "arduino-cli":
                yerel = os.environ.get("LOCALAPPDATA", "")
                if yerel:
                    a15 = os.path.join(yerel, "Arduino15")
                    g.dosya.add(os.path.join(a15, "arduino-cli.yaml"))
                    g.kurulum.add((os.path.join(a15, "packages"), 4))
                    g.kurulum.add((os.path.join(a15, "libraries"), 3))
                g.kurulum.add((os.path.join(os.path.expanduser("~"), "Documents", "Arduino",
                                            "libraries"), 3))
            elif yol:
                # aracin kendi kurulumu (avr-libc / xtensa basliklari): ikilinin 2 ust dizini.
                # Depo icindeki bir arac icin gereksiz (dosyalari zaten icerikle izleniyor) ve
                # zararli olurdu: deponun mtime'lari her degisiklikte adimi kostururdu.
                kur = os.path.dirname(os.path.dirname(os.path.abspath(yol)))
                if kapsam.ic(kur) is None and kapsam.ic(yol) is None:
                    g.kurulum.add((kur, 3))
            continue
        if ad in KICAD:
            gir, cik = _yol_argumanlari(argv, cwd)
            for x in gir:
                if os.path.isdir(x):
                    g.dizin_agac.add(x)
                else:
                    g.dosya.add(x)
                    if kapsam.ic(x) is not None:
                        g.dizin_agac.add(os.path.dirname(x))
            g.cikti.update(cik)
            appdata = os.environ.get("APPDATA")
            if appdata:
                g.dizin_agac.add(os.path.join(appdata, "kicad"))
            if yol:
                g.kurulum.add((os.path.dirname(os.path.abspath(yol)), 1))
            continue
        g.her_zaman.append(f"sinirlanamayan arac: {ad} ({' '.join(argv)[:120]})")

    if iz.rapor_py < bekle_py:
        g.her_zaman.append(f"{bekle_py} Python sureci acildi, {iz.rapor_py} rapor var — "
                           "biri iz yazmadi (-I/-S bayragi, ortam silindi ya da erken oldu)")
    if iz.rapor_node < bekle_node:
        g.her_zaman.append(f"{bekle_node} node sureci acildi, {iz.rapor_node} rapor var")
    if iz.cp > iz.popen:
        g.her_zaman.append(f"subprocess DISI surec acilisi ({iz.cp - iz.popen}): multiprocessing/"
                           "os.spawn — girdiler goremedigimiz bir surece gitti")
    g.her_zaman += [f"sinirsiz cagri: {d}" for d in iz.diger]
    g.her_zaman += [f"kanca hatasi: {d}" for d in iz.kanca_hata[:3]]
    g.her_zaman += [f"ag: {a}" for a in sorted(iz.ag)]
    for d in sorted(iz.dll):
        ad = arac_adi(d)
        if ad in SISTEM_DLL:
            continue
        if ad == "ngspice" and os.path.isabs(d):
            # surucu netlistini kancada taradi (.include -> oku); DLL'in kendisi arac imzasi
            g.arac.add(d)
            continue
        g.her_zaman.append(f"ctypes ile yuklenen kutuphane: {d}")

    # 2. Python/node kayitlari
    for p in iz.oku:
        p = pyc_kaynak(p)
        if kapsam.sayilmaz(p) or _nc(p) in yazilan:
            continue
        if os.path.isdir(p):
            continue
        g.dosya.add(os.path.abspath(p))
    for p in iz.yaz:
        if kapsam.sayilmaz(p) or not os.path.isfile(p):
            continue
        g.cikti.add(os.path.abspath(p))
    for p in iz.liste:
        if kapsam.sayilmaz(p) or _nc(p) in yazilan:
            continue
        g.liste.add(os.path.abspath(p))
    for p, v in iz.yokla.items():
        if kapsam.sayilmaz(p) or _nc(p) in yazilan:
            continue
        # yazilan bir dizinin altindaki yoklama da (adimin kendi ciktisi) sayilmaz
        if any(_nc(p).startswith(y + os.sep) for y in yazilan):
            continue
        g.yokla[os.path.abspath(p)] = v
    # dosya girdisi cikti da ise cikti olarak izlenir
    g.dosya -= g.cikti
    g.dosya = {p for p in g.dosya if not kapsam.sayilmaz(p) or p in g.arac}
    g.cikti = {os.path.abspath(p) for p in g.cikti if not kapsam.sayilmaz(p) and os.path.isfile(p)}
    return g


# ── imza ──────────────────────────────────────────────────────────────
def _dosya_imza(p: str) -> str:
    try:
        st = os.stat(p)
    except OSError:
        return "YOK"
    if os.path.isdir(p):
        return "DIZIN"
    if st.st_size > BUYUK_DOSYA:
        return f"buyuk:{st.st_size}:{st.st_mtime_ns}"
    try:
        return sha_dosya(Path(p))
    except OSError as h:
        return f"OKUNAMADI:{h.__class__.__name__}"


def _liste_imza(p: str, kapsam: Kapsam) -> str:
    try:
        adlar = sorted(a for a in os.listdir(p) if not kapsam.yoksay(os.path.join(p, a)))
    except OSError:
        return "YOK"
    return sha_metin(*adlar)


def _agac_imza(p: str, kapsam: Kapsam) -> str:
    if not os.path.isdir(p):
        return "YOK"
    h = hashlib.sha256()
    for d, alt, dosyalar in os.walk(p):
        alt[:] = sorted(x for x in alt if not kapsam.yoksay(os.path.join(d, x)) and x != ".git")
        for f in sorted(dosyalar):
            tam = os.path.join(d, f)
            if kapsam.yoksay(tam):
                continue
            h.update(os.path.relpath(tam, p).encode("utf-8", "replace") + b"\x00")
            h.update(_dosya_imza(tam).encode() + b"\x00")
    return h.hexdigest()


def _kurulum_imza(p: str, derinlik: int) -> str:
    if not os.path.isdir(p):
        return "YOK"
    h = hashlib.sha256()
    kok_d = p.rstrip("\\/").count(os.sep)
    for d, alt, dosyalar in os.walk(p):
        if d.count(os.sep) - kok_d >= derinlik:
            alt[:] = []
        alt.sort()
        for f in sorted(dosyalar) + [x + "/" for x in alt]:
            tam = os.path.join(d, f.rstrip("/"))
            try:
                st = os.stat(tam)
                h.update(f"{os.path.relpath(tam, p)}|{st.st_size}|{st.st_mtime_ns}\n".encode(
                    "utf-8", "replace"))
            except OSError:
                pass
    return h.hexdigest()


def _arac_imza(p: str) -> str:
    try:
        st = os.stat(p)
    except OSError:
        return "YOK"
    return f"{st.st_size}:{st.st_mtime_ns}"


def imzala(g: Girdiler, kapsam: Kapsam) -> dict:
    return {
        "dosya": {p: _dosya_imza(p) for p in sorted(g.dosya)},
        "dizin_agac": {p: _agac_imza(p, kapsam) for p in sorted(g.dizin_agac)},
        "liste": {p: _liste_imza(p, kapsam) for p in sorted(g.liste)},
        "yokla": {p: v for p, v in sorted(g.yokla.items())},
        "arac": {p: _arac_imza(p) for p in sorted(g.arac)},
        "kurulum": {f"{p}|{n}": _kurulum_imza(p, n) for p, n in sorted(g.kurulum)},
        "cikti": {p: _dosya_imza(p) for p in sorted(g.cikti)},
    }


def imza_farki(kayit: dict, kapsam: Kapsam, sinir: int = 3) -> list[str]:
    """Kayittaki imza ile SIMDIKI durum arasindaki farklar (bos = ayni)."""
    fark = []
    for p, eski in kayit.get("dosya", {}).items():
        if _dosya_imza(p) != eski:
            fark.append(f"degisti: {p}" if eski != "YOK" else f"belirdi: {p}")
            if len(fark) >= sinir:
                return fark
    for p, eski in kayit.get("cikti", {}).items():
        if _dosya_imza(p) != eski:
            fark.append(f"cikti degisti/silindi: {p}")
            if len(fark) >= sinir:
                return fark
    for p, eski in kayit.get("liste", {}).items():
        if _liste_imza(p, kapsam) != eski:
            fark.append(f"dizin icerigi degisti: {p}")
            if len(fark) >= sinir:
                return fark
    for p, eski in kayit.get("yokla", {}).items():
        if bool(os.path.lexists(p)) != eski:
            fark.append(f"{'silindi' if eski else 'belirdi'}: {p}")
            if len(fark) >= sinir:
                return fark
    for p, eski in kayit.get("dizin_agac", {}).items():
        if _agac_imza(p, kapsam) != eski:
            fark.append(f"agac degisti: {p}")
            if len(fark) >= sinir:
                return fark
    for p, eski in kayit.get("arac", {}).items():
        if _arac_imza(p) != eski:
            fark.append(f"arac degisti: {p}")
            if len(fark) >= sinir:
                return fark
    for k, eski in kayit.get("kurulum", {}).items():
        p, n = k.rsplit("|", 1)
        if _kurulum_imza(p, int(n)) != eski:
            fark.append(f"arac kurulumu degisti: {p}")
            if len(fark) >= sinir:
                return fark
    return fark


# ── genel anahtar ─────────────────────────────────────────────────────
def ortam_ozeti(ortam: dict | None = None) -> dict:
    ortam = os.environ if ortam is None else ortam
    s = {}
    for k, v in ortam.items():
        ku = k.upper()
        if ku in ORTAM_HARIC:
            continue
        if ku in ORTAM_ANAHTARLARI or ku.startswith(ORTAM_ONEKLERI):
            s[ku] = v
    return dict(sorted(s.items()))


def genel_anahtar(baslik: str, ek_dosyalar=()) -> str:
    dosyalar = [BURASI / "dogrula3.py", Path(__file__).resolve(),
                KANCA_DIZIN / "sitecustomize.py", KANCA_DIZIN / "node_kanca.cjs", *ek_dosyalar]
    return sha_metin(SURUM, sys.version, sys.platform, baslik,
                     json.dumps(ortam_ozeti(), sort_keys=True),
                     *[_dosya_imza(str(p)) for p in dosyalar])


# ── onbellek ──────────────────────────────────────────────────────────
def onbellek_oku(yol: Path) -> dict:
    """Bozuk / okunamayan / farkli surumlu onbellek = BOS onbellek (her adim kosar)."""
    try:
        v = json.loads(Path(yol).read_text(encoding="utf-8"))
        if not isinstance(v, dict) or v.get("surum") != SURUM or not isinstance(v.get("adimlar"), dict):
            return {"surum": SURUM, "adimlar": {}, "bozuk": True}
        return v
    except (OSError, ValueError):
        return {"surum": SURUM, "adimlar": {}, "bozuk": Path(yol).exists()}


def onbellek_yaz(yol: Path, veri: dict) -> None:
    gec = Path(str(yol) + f".{os.getpid()}.yaz")
    gec.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(gec, yol)


def git_head(kok: Path) -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=kok, capture_output=True, text=True,
                           timeout=30)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def git_degisen(kok: Path, eski: str, yeni: str, dosyalar) -> list[str] | None:
    try:
        r = subprocess.run(["git", "diff", "--name-only", eski, yeni, "--", *dosyalar], cwd=kok,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return [x for x in r.stdout.splitlines() if x.strip()]


@dataclass
class Sonuc:
    baslik: str
    tamam: bool
    sure: float
    cikti: str
    ekran: str
    onbellek_yas: float | None = None     # None = bu kosuda kostu
    sebep: str = ""                        # neden kostu (artimli kipte)
    her_zaman: list = field(default_factory=list)


class Calistir:
    """Adim govdesine verilen komut kosucusu: izli ortam + kok komut kaydi."""

    def __init__(self, iz_dizin: Path | None):
        self.iz_dizin = iz_dizin
        self.kokler: list[dict] = []

    def __call__(self, argv, cwd=None, timeout=1800, **k) -> subprocess.CompletedProcess:
        argv = [str(a) for a in argv]
        cwd = str(cwd or BURASI)
        self.kokler.append({"komut": argv, "cwd": os.path.abspath(cwd)})
        ortam = izli_ortam(self.iz_dizin) if self.iz_dizin else None
        return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, env=ortam, **k)


class Zincir:
    """Adim adim kos ya da onbellekten al; sonunda onbellegi yaz."""

    def __init__(self, kok: Path = KOK, yol: Path = ONBELLEK_YOLU, artimli: bool = False,
                 tam: bool = False, simdi: float | None = None, izle: bool = True,
                 tetik=TAM_TETIK, ek_anahtar=()):
        self.kok = Path(kok).resolve()
        self.yol = Path(yol)
        self.artimli = artimli
        self.simdi = time.time() if simdi is None else simdi
        self.izle = izle
        self.tetik = tetik
        self.ek_anahtar = tuple(ek_anahtar)
        self.kapsam = Kapsam(self.kok, onbellek=self.yol)
        self.veri = onbellek_oku(self.yol)
        self.sonuclar: list[Sonuc] = []
        self.tam_kosu, self.tam_sebep = True, "artimli istenmedi"
        if artimli:
            self.tam_kosu, self.tam_sebep = self._karar(tam)

    def _tetik_ozet(self) -> dict:
        return {d: _dosya_imza(str(self.kok / d)) for d in self.tetik}

    def _karar(self, tam: bool) -> tuple[bool, str]:
        if tam:
            return True, "--tam"
        if self.veri.get("bozuk"):
            return True, "onbellek bozuk/okunamadi"
        if self.veri.get("kok") != str(self.kok):
            return True, "onbellek baska bir proje kokune ait (ya da yok)"
        st = self.veri.get("son_tam")
        if not st:
            return True, "hic YESIL tam kosu kaydi yok"
        yas = self.simdi - st.get("zaman", 0)
        if yas > AZAMI_YAS_SN or yas < -300:
            return True, f"son tam kosu {yas / 3600:.1f} sa once (> 24 sa)"
        simdi = self._tetik_ozet()
        degisen = [d for d in self.tetik if st.get("tetik", {}).get(d) != simdi.get(d)]
        if degisen:
            return True, f"tam kosu sart: {', '.join(degisen)} son tam kosudan beri degisti"
        bas = git_head(self.kok)
        if bas and st.get("head") and bas != st["head"]:
            d = git_degisen(self.kok, st["head"], bas, self.tetik)
            if d is None or d:
                return True, f"git HEAD degisti ve {d or 'fark okunamadi'} etkilendi"
        return False, ""

    def kos(self, baslik: str, govde) -> Sonuc:
        anahtar = genel_anahtar(baslik, self.ek_anahtar)
        kayit = self.veri["adimlar"].get(baslik)
        sebep = ""
        if self.artimli and not self.tam_kosu:
            sebep = self._kullanilamaz(kayit, anahtar)
            if not sebep:
                s = Sonuc(baslik, True, kayit["sure"], kayit["cikti"], kayit["ekran"],
                          onbellek_yas=self.simdi - kayit["zaman"])
                self.sonuclar.append(s)
                return s
        iz_dizin = Path(tempfile.mkdtemp(prefix="olcum-zincir-iz-")) if self.izle else None
        try:
            cal = Calistir(iz_dizin)
            t0 = time.time()
            tamam, ekran, cikti = govde(cal)
            sure = time.time() - t0
            s = Sonuc(baslik, bool(tamam), sure, cikti, ekran, sebep=sebep)
            if iz_dizin is not None:
                g = cozumle(iz_oku(iz_dizin), self.kok, cal.kokler, self.kapsam)
                s.her_zaman = list(g.her_zaman)
                if s.tamam:
                    self.veri["adimlar"][baslik] = {
                        "anahtar": anahtar, "zaman": self.simdi, "sure": sure, "cikti": cikti,
                        "ekran": ekran, "her_zaman": g.her_zaman,
                        "imza": imzala(g, self.kapsam)}
                else:
                    self.veri["adimlar"].pop(baslik, None)
            else:
                self.veri["adimlar"].pop(baslik, None)
        finally:
            if iz_dizin is not None:
                shutil.rmtree(iz_dizin, ignore_errors=True)
        self.sonuclar.append(s)
        return s

    def _kullanilamaz(self, kayit, anahtar) -> str:
        if not isinstance(kayit, dict):
            return "onbellekte kaydi yok"
        try:
            if kayit.get("her_zaman"):
                return "HER ZAMAN KOSAR: " + kayit["her_zaman"][0]
            if kayit.get("anahtar") != anahtar:
                return "genel anahtar degisti (dogrula3/kanca/Python/ortam)"
            yas = self.simdi - float(kayit["zaman"])
            if yas > AZAMI_YAS_SN or yas < -300:
                return f"kayit {yas / 3600:.1f} sa eski"
            fark = imza_farki(kayit["imza"], self.kapsam)
            if fark:
                return "; ".join(fark)
            for k in ("cikti", "ekran", "sure"):
                kayit[k]
        except (KeyError, TypeError, ValueError, AttributeError) as h:
            return f"onbellek kaydi bozuk ({h.__class__.__name__})"
        return ""

    def bitir(self, genel_yesil: bool = True) -> None:
        """Onbellegi yaz. Butun adimlar KOSTUYSA ve hepsi yesilse 'son tam kosu' tazelenir.
        Kancasiz (--izsiz) kosu onbellege HIC dokunmaz: girdisini bilmedigi sonucu yazamaz."""
        if not self.izle:
            return
        self.veri["surum"] = SURUM
        self.veri["kok"] = str(self.kok)
        self.veri.pop("bozuk", None)
        hepsi_kostu = all(s.onbellek_yas is None for s in self.sonuclar)
        hepsi_yesil = all(s.tamam for s in self.sonuclar)
        if hepsi_kostu and hepsi_yesil and genel_yesil and self.izle and self.sonuclar:
            self.veri["son_tam"] = {"zaman": self.simdi, "head": git_head(self.kok),
                                    "tetik": self._tetik_ozet()}
        # CIKTILAR ZINCIRIN SONUNDAKI haliyle. Iki adim ayni dosyayi yazabiliyor (B3 ve B9
        # ikisi de netlist3.net uretiyor, ikincisi birincinin uzerine): adimin kendi
        # bitisindeki hal saklansaydi, sonraki kosuda B3 "cikti degisti" diye kosar, o da
        # B9'u kostururdu — her kosuda ikisi de (olculdu, 2026-10-03). Bir tam kosunun
        # BIRAKTIGI hal budur; kullanici ya da baska bir sey sonradan degistirirse yine
        # yakalanir.
        for kayit in self.veri["adimlar"].values():
            try:
                c = kayit["imza"]["cikti"]
                kayit["imza"]["cikti"] = {q: _dosya_imza(q) for q in c}
            except (KeyError, TypeError, AttributeError):
                pass
        try:
            onbellek_yaz(self.yol, self.veri)
        except OSError as h:
            print(f"  (uyari: zincir onbellegi yazilamadi: {h})")

    def ozet(self) -> list[str]:
        """OZET'in altina basilacak artimli satirlari."""
        if not self.artimli:
            return []
        sat = []
        alinan = [s for s in self.sonuclar if s.onbellek_yas is not None]
        if self.tam_kosu:
            sat.append(f"  ARTIMLI: TAM kosu yapildi — {self.tam_sebep}")
        else:
            sat.append(f"  ARTIMLI: {len(alinan)}/{len(self.sonuclar)} adim ONBELLEKTEN "
                       f"(yeniden kosulmadi):")
            for s in alinan:
                sat.append(f"    · {s.baslik:<44} {yas_yazi(s.onbellek_yas)} once kosmustu")
            for s in self.sonuclar:
                if s.onbellek_yas is None:
                    sat.append(f"    > kostu: {s.baslik} — {s.sebep}"[:150])
        return sat


def yas_yazi(sn: float) -> str:
    if sn < 90:
        return f"{sn:.0f} s"
    if sn < 5400:
        return f"{sn / 60:.0f} dk"
    return f"{sn / 3600:.1f} sa"
