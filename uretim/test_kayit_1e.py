"""B71'in 1E bolumleri — odakli giris (bildirim.h olay cekirdegi + mqtt_paket.h).

    python test_kayit_1e.py          (~30 s; tam B71 test_kayit.py ~4 dk)

Ayni bolumler tam B71'de (`test_kayit.py`, zincir) de kosar; bu dosya yalniz
mutasyon kosusu her 1E mutasyonunda tum AVR paketini yeniden kosmasin diye var
(mutasyon.py'deki 1E B71 girdileri bunu kosar).
"""
import sys

import test_kayit as T

T.bolum_bildirim()
T.bolum_mqtt()
print(f"\nB71-1E: {T.gecti}/{T.gecti + T.kaldi} kosul gecti")
sys.exit(0 if T.kaldi == 0 else 1)
