# -*- coding: utf-8 -*-
"""Kendini toplayan gecici dizin.

🔴 COZULEN KUSUR. Alti betik `tempfile.mkdtemp()` cagiriyor ve HICBIRI
silmiyordu. 2026-09-10'da olculdu: kullanicinin `%TEMP%` dizininde
**826** artik dizin birikmisti —

    spice-*   618      olcum3_*  135      skopolc_*  47
    kopru_*    22      fw3_*       4      skop_*      2

`spice.kos()` ozellikle kotu: cagri basina bir dizin ve tek bir zincir
kosusu duzinelerce cagri yapiyor.

NEDEN `finally` YETMIYOR: `spice.kos()` calisma dizinini GERI DONDURUYOR
— cagiran taraf `wrdata` ciktilarini oradan sonra okuyor. Silme, cagri
bitince degil SUREC bitince olmali. `atexit` tam olarak bu.

    from gecici import dizin
    g = dizin("olcum3_")        # surec bitince kendiliginden silinir

⚠ Hata ayiklarken dizinin KALMASINI istiyorsan `OLCUM_GECICI_KAL=1`
  ortam degiskenini kur.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

# Bu projenin urettigi gecici dizin onekleri — `dogrula3.py`'nin cop
# toplayicisi ESKI kalintilari da bu listeye gore suepuruyor.
ONEKLER = ("spice-", "olcum3_", "skopolc_", "kopru_", "fw3_", "skop_", "kayit_")
# DOSYA kalintilari: B72.Q16'nin test_bildirim onbellegi (%TEMP%'te onlarca birikmisti — HIZ
# inceleme 2026-10-03). Silinmesi yalniz bir sonraki B72 kosusunu ~23 s uzatir.
DOSYA_ONEKLER = ("ok_test_bildirim_",)

KAL = os.environ.get("OLCUM_GECICI_KAL") == "1"


def dizin(onek: str) -> Path:
    """Surec bitince kendiliginden silinen gecici dizin."""
    d = Path(tempfile.mkdtemp(prefix=onek))
    if not KAL:
        atexit.register(shutil.rmtree, d, ignore_errors=True)
    return d


def eski_kalintilar() -> list[Path]:
    """`%TEMP%` altinda bu projeden kalmis dizinler."""
    kok = Path(tempfile.gettempdir())
    bulunan = []
    for onek in ONEKLER:
        for d in kok.glob(onek + "*"):
            if not d.is_dir():
                continue
            # `spice-` yeterince ayirt edici degil: yalnizca surucusunu
            # tasiyan dizin BIZIM. Digerlerinin oneki projeye ozgu.
            if onek == "spice-" and not (d / "_surucu.py").exists():
                continue
            bulunan.append(d)
    return bulunan


def kalintilari_sil() -> int:
    """Eski kalintilari siler; silinen dizin (ve dosya) sayisini dondurur."""
    n = 0
    for d in eski_kalintilar():
        shutil.rmtree(d, ignore_errors=True)
        n += not d.exists()
    kok = Path(tempfile.gettempdir())
    for onek in DOSYA_ONEKLER:
        for f in kok.glob(onek + "*"):
            try:
                if f.is_file():
                    f.unlink()
                    n += 1
            except OSError:
                pass
    return n
