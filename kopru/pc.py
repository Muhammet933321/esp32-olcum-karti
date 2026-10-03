# -*- coding: utf-8 -*-
"""PC UYGULAMASI — olcum kartinin bu bilgisayardaki TEK ana sureci (alt proje 4).

    python kopru/pc.py                    # kopruyu ac + paneli tarayicida ac
    pythonw kopru/pc.py --sessiz          # arka plan: konsol yok, tarayici yok
    python kopru/pc.py --port COM7        # portu elle ver (yoksa VID'den)
    python kopru/pc.py --lan              # yerel aga SALT OKUMA (yalniz p0)
    python kopru/pc.py --kayit GUN.satir --http-port 8771   # olu tekrar
    python kopru/pc.py --tarayici-acma    # tarayici acmadan
    python kopru/pc.py --durdur           # calisan kopruyu durdur (arka plandaki de)

Panel: http://olcum.localhost:8770 — yalniz bu bilgisayardan (PC1/PC2).

4A bugun yalniz ROLEYI barindiriyor; arka plan eslemesi (4C) ve MQTT
bildirimleri (4E) AYNI surece eklenecek — ikinci bir arka plan sureci
ayni COM portu / ayni cihaz sayacini tutmasin diye (PC4).

Desen stok-takip'ten (stok/konsol.py), kanitlanmis:
  * `zaten_calisiyor()` — kopru ayaktayken ikinci kopya ACILMAZ; masaustu
    kisayolu yalniz tarayiciyi acar, `--sessiz` sessizce cikar.
  * `--sessiz` — pythonw ile konsolsuz; cokerse iz
    `%LOCALAPPDATA%\\olcum-karti\\arkaplan-hata.txt` (`OLCUM_PC_DIZIN`).
  * Windows'ta `allow_reuse_address = False` (+ SO_EXCLUSIVEADDRUSE) —
    kopru.Sunucu'da.
  * Kart takili degilken de acilir (kart_baglanti.OtoSeriKart): Windows
    acilisinda kart yoksa kisayol ise yaramaz olmasin.

Baslangic kisayolu: `kopru/Otomatik Baslat Kur.bat` / `... Kapat.bat`.
⚠ Kopru COM portunu TUTAR: kopru acikken tezgah araclari portu acamaz ve
  "PC kopru bu portu kullaniyor — kapatin" der (PC3; `kart_baglanti`
  uzerinden acan araclar). `yukle.py` arduino-cli'yi dogrudan cagirir, o
  mesaji VERMEZ — yuklemeden once kopruyu durdurun:
  `kopru/Kopruyu Durdur.bat` ya da `python kopru/pc.py --durdur`.
  ⚠ "pythonw.exe'yi oldur" DEGIL: stok-takip'in arka plan sunucusu da pythonw.

Yalnizca standart kutuphane.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
import kart_baglanti                                      # noqa: E402
import kopru as kopru_mod                                 # noqa: E402
import pc_ayar                                            # noqa: E402

YARDIM = __doc__


def zaten_calisiyor(port: int = pc_ayar.PORT) -> bool:
    """Bu portta BIZIM kopru mu cevap veriyor? (`/durum` imzasi: `kart` + `skop_arsiv`).

    ⚠ `olcum.localhost` degil `127.0.0.1`: isletim sistemi `*.localhost`u
      cozmuyor, yalniz tarayici cozuyor (pc_ayar.py).
    """
    try:
        with pc_ayar.yerel_istek(port, "/durum") as y:     # vekilsiz (4A inceleme)
            d = json.load(y)
    except Exception:                                       # noqa: BLE001
        return False
    return isinstance(d, dict) and "kart" in d and "skop_arsiv" in d


def durdur(port: int = pc_ayar.PORT, bekle: float = 5.0) -> tuple[bool, str]:
    """Calisan kopruyu KENDI ucundan (`POST /kapat`, yalniz bu bilgisayar) durdur.

    4A inceleme: eskiden tek yol "Gorev Yoneticisi > pythonw.exe" idi; ayni
    yoldan stok-takip'in arka plan sunucusu da calisiyor.
    """
    if not zaten_calisiyor(port):
        return False, f"{port} portunda calisan kopru yok"
    try:
        with pc_ayar.yerel_istek(port, "/kapat", veri=b"", basliklar={"X-Olcum": "1"},
                                 zaman_asimi=3.0):
            pass
    except Exception as e:                                  # noqa: BLE001
        return False, f"kopru durdurulamadi: {e}"
    son = time.monotonic() + bekle
    while time.monotonic() < son:
        if not zaten_calisiyor(port):
            return True, f"kopru durduruldu ({pc_ayar.adres(port)}); COM portu serbest"
        time.sleep(0.2)
    return False, f"kopru {bekle:.0f} s icinde kapanmadi"


def _secenek(arg: list[str], ad: str, varsayilan=None):
    if ad in arg:
        i = arg.index(ad)
        if i + 1 >= len(arg):
            raise RuntimeError(f"{ad} bir deger ister")
        return arg[i + 1]
    return varsayilan


def calistir(arg: list[str], tarayici_ac=webbrowser.open, yazdir=print) -> int:
    """Kopruyu ac ve kapanana dek hizmet et. Donus: cikis kodu."""
    if "--yardim" in arg or "-h" in arg:
        yazdir(YARDIM)
        return 0
    sessiz = "--sessiz" in arg
    lan = "--lan" in arg
    kayit = _secenek(arg, "--kayit")
    http_port = int(_secenek(arg, "--http-port", pc_ayar.PORT))
    adres = pc_ayar.adres(http_port)

    if "--durdur" in arg:
        tamam, mesaj = durdur(http_port)
        yazdir(mesaj)
        return 0 if tamam else 1

    # ── tek kopya ────────────────────────────────────────────────────
    if zaten_calisiyor(http_port):
        if kayit:
            yazdir(f"{http_port} portunda kopru zaten calisiyor. Olu tekrar icin baska "
                   f"port verin: --http-port {http_port + 1}")
            return 2
        if sessiz:
            return 0
        yazdir(f"Kopru zaten calisiyor — {adres} aciliyor.")
        tarayici_ac(adres + "/")
        return 0

    # ── once HTTP portu (COM portunu bosuna tutmamak icin) ───────────
    try:
        sunucu = kopru_mod.sunucu_kur(None, lan=lan, port=http_port)
    except OSError as e:
        raise RuntimeError(
            f"{http_port} portu baska bir program tarafindan kullaniliyor (kopru degil): "
            f"{e}. O programi kapatin ya da --http-port ile baska port verin — ⚠ adres "
            f"degisirse panelin bu bilgisayardaki ayarlari o adreste AYRI tutulur") from e

    try:
        if kayit:
            satirlar = [s.split("\t", 1)[-1].rstrip("\n")
                        for s in Path(kayit).read_text(encoding="utf-8").splitlines()]
            kart = kart_baglanti.KayitKart(satirlar, gecikme=0.2)
        else:
            kart = kart_baglanti.OtoSeriKart(_secenek(arg, "--port"))
        kopru = kopru_mod.Kopru(kart, KOK / "kopru" / "arsiv")
        sunucu.RequestHandlerClass.kopru = kopru
        if not sessiz and hasattr(kart, "bildir"):
            # 4A inceleme: kart durumu (bulunamadi / baglandi / koptu) konsola da.
            # Eskiden yalniz /akis'e gidiyordu: `--port COM7` yanlissa konsoldaki
            # kullanici "acildi" yazisini gorup neden veri gelmedigini bilemiyordu.
            akisa = kart.bildir

            def bildir(metin, _akisa=akisa):
                yazdir(metin)
                _akisa(metin)
            kart.bildir = bildir
    except BaseException:
        sunucu.server_close()
        raise

    def yukari_akis():
        # Kart acilisi (otomatik secimde kimlik dogrulamasi saniyeler surebilir)
        # HTTP'yi bekletmesin: ikinci kopyanin `zaten_calisiyor`u zaman asimina
        # dusup "port baska programda" demesin.
        kart.ac()
        kopru.dongu()
    threading.Thread(target=yukari_akis, daemon=True).start()

    if not sessiz:
        yazdir(f"Kopru acildi — kart: {kart.ad}")
        yazdir(f"  Panel (bu bilgisayar) : {adres}")
        if lan:
            yazdir(f"  Yerel ag (SALT OKUMA) : http://{kopru_mod.lan_ip()}:{http_port}"
                   f"   — telefonlar izler, yalniz p0 (DURDUR) gonderebilir")
        yazdir(f"  Arsiv                 : {kopru.arsiv.dizin}")
        yazdir("Kapatmak icin Ctrl+C (arka plandaysa: kopru\\Kopruyu Durdur.bat)")
        if "--tarayici-acma" not in arg:
            threading.Timer(0.6, lambda: tarayici_ac(adres + "/")).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        if not sessiz:
            yazdir("\nkapatiliyor…")
    finally:
        kopru.durdur()
        kart.kapat()
        sunucu.server_close()
    return 0


def main(arg: list[str] | None = None) -> int:
    arg = sys.argv[1:] if arg is None else list(arg)
    if "--sessiz" not in arg:
        try:
            return calistir(arg)
        except RuntimeError as e:
            print(f"Kopru acilamadi: {e}")
            return 1
    # Sessiz kipte konsol yok (pythonw); hatayi goren olmaz — dosyaya yaz.
    try:
        return calistir(arg)
    except Exception:                                       # noqa: BLE001
        dizin = pc_ayar.veri_dizini()
        try:
            dizin.mkdir(parents=True, exist_ok=True)
            damga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            (dizin / "arkaplan-hata.txt").write_text(
                damga + "\n" + traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
