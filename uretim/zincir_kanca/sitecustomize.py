# -*- coding: utf-8 -*-
"""ZINCIR IZ KANCASI — artimli zincirin (dogrula3.py --artimli) girdi kesfi.

Bu dizin YALNIZ `zincir_onbellek.izli_ortam()` tarafindan PYTHONPATH'in basina
konur; normal kosularda hic yuklenmez. `OLCUM_ZINCIR_IZ` ortam degiskeni yoksa
HICBIR SEY yapmaz (ayni dizini elle PYTHONPATH'e koyan biri etkilenmesin).

NE KAYDEDER (surec basina bir `py-<pid>-....jsonl` dosyasi, IZ dizininde):
  oku / yaz   `open` denetim olayi (sys.addaudithook) — kip ya da bayraklara gore;
              ayrica `_winapi.CopyFile2` (kaynak oku, hedef yaz), rename/remove/
              mkdir/rmdir/rmtree (yaz)
  liste       os.listdir / os.scandir (importlib'in kendi yol onbellegi HARIC)
  yokla       os.path.exists/isfile/isdir/lexists + os.stat/lstat — yoklanan
              yolun VAR/YOK sonucu (acilmadan yalniz varligina bakilan dosya,
              ornegin `_fs.json` yoksa baska dala giren sim3_web.py)
  surec       subprocess.Popen (komut satiri, cwd, ortam iz degiskenini tasiyor mu)
  cp          _winapi.CreateProcess (Popen DISI surec acilisini yakalamak icin say)
  diger       os.system / os.startfile / os.spawn* / os.exec* — SINIRSIZ isareti
  dll         ctypes.dlopen
  ag          loopback DISI socket.connect / getaddrinfo — dis durum
  mod         cikista sys.modules'teki her modulun dosyasi (gecerli .pyc varken
              import kaynagi .py'yi HIC acmaz; bu satir onu kapatir)
  liste       cikista sys.path'teki her dizin (golge modul: uretim/gzip.py)
  son         surec duzgun bitti

🔴 YAZ-GEC (write-through). Her YENI kayit olaydan ONCE diske yazilir (os.write,
   denetlenmeyen cagri). Oldurulen bir surec (test'in terminate ettigi sunucu)
   hicbir kaydini kaybetmez — olay kancasi islemden ONCE calisir.
🔴 Kanca kendi icinde denetlenen bir sey cagirirsa (sys._getframe bile bir olay)
   sonsuz ozyineleme olur: is parcacigi basina yeniden giris kilidi.
"""
import os as _os

_IZ = _os.environ.get("OLCUM_ZINCIR_IZ")


def _kur(iz_dizin):
    import json
    import ntpath
    import sys
    import threading

    yerel = threading.local()
    ad = f"py-{_os.getpid()}-{_os.urandom(4).hex()}.jsonl"
    fd = _os.open(_os.path.join(iz_dizin, ad),
                  _os.O_WRONLY | _os.O_CREAT | _os.O_APPEND | getattr(_os, "O_BINARY", 0))
    gorulen = set()
    kilit = threading.Lock()
    # YAZ-GEC: her kayit ANINDA diske. False olsaydi kayitlar cikista yazilirdi ve
    # oldurulen surecin (testin terminate ettigi sunucu) okumalari KAYBOLURDU —
    # test_zincir_hiz B13 bunu olcer (mutasyon "HIZ: yaz-gec").
    aninda = True
    tampon = []

    def yaz(tur, deger, ek=None):
        anahtar = (tur, deger)
        with kilit:
            if anahtar in gorulen:
                return
            gorulen.add(anahtar)
            satir = {"t": tur, "p": deger}
            if ek is not None:
                satir["e"] = ek
            veri = (json.dumps(satir, ensure_ascii=False) + "\n").encode("utf-8")
            if aninda or tur == "bas":
                _os.write(fd, veri)
            else:
                tampon.append(veri)

    def yol(p):
        if p is None or isinstance(p, int):
            return None
        try:
            p = _os.fsdecode(_os.fspath(p))
        except Exception:
            return None
        if not p or p.startswith("\\\\.\\") or p.upper() in ("NUL", "CON", "CONIN$", "CONOUT$"):
            return None
        try:
            return _os.path.abspath(p)
        except Exception:
            return None

    yazma_bayrak = (_os.O_WRONLY | _os.O_RDWR | _os.O_APPEND | _os.O_CREAT | _os.O_TRUNC)

    def importlib_mi():
        try:
            f = sys._getframe(2)
        except ValueError:
            return False
        return f.f_code.co_filename.startswith("<frozen importlib")

    yerel_adlar = ("127.0.0.1", "localhost", "::1", "0.0.0.0", "", None)

    def yerel_mi(ad) -> bool:
        # Butun 127.0.0.0/8 geri donus agi yerel (birlesme 2026-10-03: 4E testi sahte araciyi
        # 127.83.41.7'de acar; yalniz 127.0.0.1 sayilinca B72 HER ZAMAN KOSAR oluyordu).
        return ad in yerel_adlar or (isinstance(ad, str) and ad.startswith("127."))

    # Kanca HER denetim olayinda cagrilir (builtins.id, sys._getframe, exec ...);
    # ilgisiz olay ilk satirda donmeli — yoksa yogun Python (B58f) yavaslar.
    ilgi = frozenset((
        "open", "_winapi.CopyFile2", "os.rename", "os.replace", "os.remove", "os.unlink",
        "os.rmdir", "os.mkdir", "shutil.rmtree", "os.truncate", "os.symlink", "os.link",
        "os.listdir", "os.scandir", "subprocess.Popen", "_winapi.CreateProcess", "os.system",
        "os.startfile", "os.spawn", "os.exec", "os.posix_spawn", "os.fork", "os.forkpty",
        "ctypes.dlopen", "socket.connect", "socket.getaddrinfo"))

    def kanca(olay, a):
        if olay not in ilgi or getattr(yerel, "ic", False):
            return
        yerel.ic = True
        try:
            if olay == "open":
                p = yol(a[0])
                if p is None:
                    return
                kip, bayrak = a[1], a[2]
                if kip is not None:
                    w = any(c in str(kip) for c in "wax+")
                else:
                    w = isinstance(bayrak, int) and bool(bayrak & yazma_bayrak)
                yaz("yaz" if w else "oku", p)
            elif olay == "_winapi.CopyFile2":
                s, h = yol(a[0]), yol(a[1])
                if s:
                    yaz("oku", s)
                if h:
                    yaz("yaz", h)
            elif olay in ("os.rename", "os.replace"):
                for x in a[:2]:
                    p = yol(x)
                    if p:
                        yaz("yaz", p)
            elif olay in ("os.remove", "os.unlink", "os.rmdir", "os.mkdir", "shutil.rmtree",
                          "os.truncate", "os.symlink", "os.link"):
                p = yol(a[0])
                if p:
                    yaz("yaz", p)
            elif olay in ("os.listdir", "os.scandir"):
                if importlib_mi():
                    return
                p = yol(a[0] if a and a[0] is not None else ".")
                if p:
                    yaz("liste", p)
            elif olay == "subprocess.Popen":
                exe, komut, cwd, ortam = a
                if not isinstance(komut, str):
                    try:
                        komut = [_os.fsdecode(x) for x in komut]
                    except Exception:
                        komut = repr(komut)
                iz_var = ortam is None or ("OLCUM_ZINCIR_IZ" in ortam
                                           or b"OLCUM_ZINCIR_IZ" in ortam)
                yaz("surec", json.dumps({"exe": _os.fsdecode(exe) if exe else None,
                                         "komut": komut,
                                         "cwd": yol(cwd if cwd is not None else "."),
                                         "iz": iz_var, "no": _os.urandom(6).hex()},
                                        ensure_ascii=False))
            elif olay == "_winapi.CreateProcess":
                yaz("cp", f"{_os.getpid()}-{_os.urandom(6).hex()}")
            elif olay in ("os.system", "os.startfile", "os.spawn", "os.exec", "os.posix_spawn",
                          "os.fork", "os.forkpty"):
                yaz("diger", f"{olay}: {repr(a)[:300]}")
            elif olay == "ctypes.dlopen":
                yaz("dll", str(a[0]))
            elif olay == "socket.connect":
                adres = a[1]
                if isinstance(adres, tuple) and adres and not yerel_mi(adres[0]):
                    yaz("ag", f"connect {adres[0]}")
            elif olay == "socket.getaddrinfo":
                if a and not yerel_mi(a[0]) and not isinstance(a[0], bytes):
                    yaz("ag", f"getaddrinfo {a[0]}")
        except Exception as h:      # kanca asla kosulan programi dusurmesin
            try:
                yaz("kanca_hata", f"{olay}: {h!r}")
            except Exception:
                pass
        finally:
            yerel.ic = False

    # ── varlik yoklamalari (denetim olayi YOK; sarmalayarak) ──────────
    def sar_yokla(asil):
        def sarmal(p, *x, **k):
            sonuc = asil(p, *x, **k)
            if not getattr(yerel, "ic", False):
                yerel.ic = True
                try:
                    y = yol(p)
                    if y:
                        yaz("yokla", y, bool(_lexists(y)))
                except Exception:
                    pass
                finally:
                    yerel.ic = False
            return sonuc
        sarmal.__wrapped__ = asil
        sarmal.__name__ = getattr(asil, "__name__", "sarmal")
        return sarmal

    _lexists = ntpath.lexists
    for ad_ in ("exists", "isfile", "isdir", "lexists"):
        setattr(ntpath, ad_, sar_yokla(getattr(ntpath, ad_)))

    def sar_stat(asil):
        def sarmal(p, *x, **k):
            if isinstance(p, int) or k.get("dir_fd") is not None or getattr(yerel, "ic", False):
                return asil(p, *x, **k)
            try:
                sonuc = asil(p, *x, **k)
            except OSError:
                var = False
                raise
            else:
                var = True
            finally:
                yerel.ic = True
                try:
                    y = yol(p)
                    if y:
                        yaz("yokla", y, var)
                except Exception:
                    pass
                finally:
                    yerel.ic = False
            return sonuc
        sarmal.__wrapped__ = asil
        sarmal.__name__ = asil.__name__
        return sarmal

    _os.stat = sar_stat(_os.stat)
    _os.lstat = sar_stat(_os.lstat)

    yaz("bas", json.dumps({"argv": list(sys.argv), "exe": sys.executable,
                           "cwd": _os.getcwd()}, ensure_ascii=False))
    sys.addaudithook(kanca)

    def spice_tara():
        """ngspice.dll (ctypes) C duzeyinde okur — denetim olayi yok. Surucu
        `source <netlist>` ile calisir; netlistin .include/.lib/source satirlari
        burada okunan dosya olarak yazilir. Okunamazsa SINIRSIZ."""
        import re
        aday = [a for a in sys.argv[1:] if a.lower().endswith((".cir", ".sp", ".net", ".spice"))]
        for a in aday:
            p = _os.path.abspath(a)
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    metin = f.read()
            except OSError as h:
                yaz("diger", f"ngspice netlisti okunamadi: {p}: {h!r}")
                continue
            for m in re.finditer(r"(?im)^\s*(?:\.include|\.inc|\.lib|source)\s+(\S+)", metin):
                hedef = m.group(1).strip("\"'")
                yaz("oku", _os.path.abspath(_os.path.join(_os.path.dirname(p), hedef)))
        if not aday:
            yaz("diger", "ngspice yuklendi ama netlist arguman olarak verilmedi")

    def bitir():
        yerel.ic = True
        try:
            for m in list(sys.modules.values()):
                f = getattr(m, "__file__", None)
                if f:
                    yaz("mod", _os.path.abspath(f))
            # GOLGE MODUL: importlib'in dizin bakislari kayda girmiyor (importlib_mi). Betigin
            # dizinine (uretim/) gelen bir gzip.py standart kutuphaneyi golgeler — sys.path'teki
            # her dizinin AD LISTESI girdi (HIZ inceleme 2026-10-03: uretim/gzip.py ile 19/22
            # adim onbellekten YESIL geldi, dogrudan kosunca ImportError).
            for d in list(sys.path):
                try:
                    y = _os.path.abspath(d or _os.getcwd())
                except Exception:
                    continue
                if _os.path.isdir(y):
                    yaz("liste", y)
            if any("ngspice" in k[1].lower() for k in list(gorulen) if k[0] == "dll"):
                spice_tara()
            yaz("son", "")
            for veri in tampon:
                _os.write(fd, veri)
        except Exception:
            pass

    import atexit
    atexit.register(bitir)


if _IZ:
    _kur(_IZ)
