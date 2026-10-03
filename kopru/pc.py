# -*- coding: utf-8 -*-
"""PC UYGULAMASI — olcum kartinin bu bilgisayardaki TEK ana sureci (alt proje 4).

    python kopru/pc.py                    # kopruyu ac + paneli tarayicida ac
    pythonw kopru/pc.py --sessiz          # arka plan: konsol yok, tarayici yok
    python kopru/pc.py --port COM7        # portu elle ver (yoksa VID'den)
    python kopru/pc.py --lan              # yerel aga SALT OKUMA (yalniz p0)
    python kopru/pc.py --kayit GUN.satir --http-port 8771   # olu tekrar
    python kopru/pc.py --tarayici-acma    # tarayici acmadan
    python kopru/pc.py --durdur           # calisan kopruyu durdur (arka plandaki de)
    python kopru/pc.py --kart-host 192.168.4.1   # kartin WiFi adresi (varsayilan olcum.local)
    python kopru/pc.py --cihaz DOSYA      # eslesmis cihaz dosyasi (yoksa kart kimligine gore)
    python kopru/pc.py --wifi-yok         # yalniz USB (4A davranisi)
    python kopru/pc.py --usb-yok          # yalniz WiFi: COM portu hic acilmaz (tezgah araclari kullanabilir)
    python kopru/pc.py --onaysiz          # 4C: kayitlari esitle ama karta ONAY (Go) yollama
    python kopru/pc.py --esitleme-aralik 300   # 4C: esitleme araligi (s; en az 30, varsayilan 120)
    python kopru/pc.py --esitleme-yok     # 4C: arka plan esitlemesi kapali
    python kopru/pc.py --bildirim-yok     # 4E: MQTT aboneligi + Windows bildirimi kapali

Panel: http://olcum.localhost:8770 — yalniz bu bilgisayardan (PC1/PC2).

4B (PC6) — YUKARI-AKIS: USB'de DOGRULANMIS kart varsa canli akis ve komut USB'den;
yoksa kartla WiFi'den ESLESMIS CIHAZ olarak (imzali /akis + /komut, p0 imzasiz;
kart_wifi.py). Gecis akista bir durum satiriyla soylenir. Kopru once eslestirilir
(bir kez, kartin WEB parolasiyla):
    python kopru/imza.py esles --host olcum.local --ad <bu-PC>
Cihaz anahtari `%LOCALAPPDATA%\\olcum-karti\\cihaz\\` altinda (PC5; DPAPI).

4C (PC5/PC9) — ARKA PLAN DISK ARSIVI ayni surecte (arka_esitle.py): kartin kayitlari
WiFi'den, canli akisla AYNI eslesmis cihaz nesnesi ve sayac kilidiyle, `%LOCALAPPDATA%\\
olcum-karti\\arsiv\\<kart kimligi>\\akis-<n>\\` altina; her (yeniden) baglantida ve 120 s'de bir.
Varsayilan ONAY verir (kalici yazimdan SONRA) — `--onaysiz` ya da ayar.json
`"esitleme_onay": false` kapatir. Durum: `GET /esitleme/durum` (yalniz bu bilgisayar).
Eski `.satir` satir gunlugu `...\\olcum-karti\\satir\\` (eskiden calisan agacin kopru/arsiv'i;
yeni dizin bossa BIR KEZ kopyalanir, eskisi yerinde kalir).
4E (PC13–PC16) — MQTT BILDIRIMLERI AYNI surecte (pc_bildirim.py): kartin /bildirim/bilgi'si
(eslesmis cihaz, imzali, ayni sayac kilidi) -> araciya YALNIZ ABONE -> Windows bildirimi
(windows_bildirim.py, WinRT toast; kaynak "Ölçüm kartı"). K ile sifreli zarf onbellekte
(`...\\olcum-karti\\bildirim\\`), cozulmus araci bilgisi diske/gunluge YAZILMAZ. Olay basina
ac/kapa: ayar.json `"bildirim": {"kopuk": false, ...}` (ya da `python kopru/pc_bildirim.py ayar
kopuk=0`). Durum: `GET /bildirim/durum` (yalniz bu bilgisayar). `--bildirim-yok` kapatir.
Ikinci bir arka plan sureci ayni COM portu / ayni cihaz sayacini tutmasin diye tek surec (PC4).

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
import arka_esitle                                        # noqa: E402
import imza                                               # noqa: E402
import kart_baglanti                                      # noqa: E402
import kart_wifi                                          # noqa: E402
import kopru as kopru_mod                                 # noqa: E402
import pc_ayar                                            # noqa: E402
import pc_bildirim                                        # noqa: E402  (4E)

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


def yukari_akis_kur(arg: list[str]):
    """4B (PC6): USB (OtoSeriKart, VID + kimlik) ONCE, yoksa WiFi (WifiKart, eslesmis cihaz).
    `--wifi-yok`: yalniz USB (4A davranisi). Kart adresi `--kart-host` > OLCUM_KART_HOST >
    olcum.local; `--cihaz` verilmezse cihaz dosyasi kartin kimligine gore secilir."""
    if "--wifi-yok" in arg and "--usb-yok" in arg:
        raise RuntimeError("--wifi-yok ile --usb-yok birlikte verilemez (yukari-akis kalmaz)")
    usb = kart_baglanti.OtoSeriKart(_secenek(arg, "--port"))
    if "--wifi-yok" in arg:
        return usb
    wifi = kart_wifi.WifiKart(_secenek(arg, "--kart-host") or pc_ayar.kart_host(),
                              cihaz_dosyasi=_secenek(arg, "--cihaz"))
    if "--usb-yok" in arg:
        # Yalniz WiFi: COM portu HIC acilmaz — kart USB'den beslenirken de WiFi yolu
        # sinanabilir; tezgah araclari (yukle.py, tezgah_*.py) portu kullanabilir.
        return wifi
    return kart_wifi.SecmeliKart(usb, wifi)


ESKI_SATIR_DIZINI = KOK / "kopru" / "arsiv"


def satir_goc(eski=None, yeni=None) -> list[str]:
    """4C: eski `.satir` gunlugu (calisan agacin kopru/arsiv) -> pc_ayar.satir_dizini(), YALNIZ
    yeni dizinde hic `.satir` yoksa; KOPYALAR (eski yerinde kalir — kullanicinin B35 arsivi
    silinmez, geri donus yolu). Kopyalanan dosya adlari (bos = bir sey yapilmadi)."""
    import shutil
    eski = Path(eski or ESKI_SATIR_DIZINI)
    yeni = Path(yeni or pc_ayar.satir_dizini())
    if not eski.is_dir() or (yeni.is_dir() and any(yeni.glob("*.satir"))):
        return []
    adaylar = sorted(eski.glob("*.satir"))
    if not adaylar:
        return []
    yeni.mkdir(parents=True, exist_ok=True)
    for a in adaylar:
        shutil.copy2(a, yeni / a.name)
    return [a.name for a in adaylar]


def esitleme_kur(arg: list[str], kart, kopru, arsiv_kok=None, yazdir=print):
    """4C (PC9): arka plan esitlemesini kur (BASLATMAZ) ve kopruye bagla (`/esitleme/durum`).
    WiFi yukari-akisi yoksa (`--wifi-yok`, olu tekrar) ya da `--esitleme-yok` ise None.
    Onay: varsayilan VERIR; `--onaysiz` ya da ayar.json `"esitleme_onay": false` kapatir; ayar
    dosyasi okunamazsa GUVENLI tarafa (onaysiz) duser ve soyler. Aralik `--esitleme-aralik` >
    ayar.json `esitleme_aralik_s` > 120 s; en az arka_esitle.ARALIK_EN_AZ."""
    wifi = kart.wifi if isinstance(kart, kart_wifi.SecmeliKart) else (
        kart if isinstance(kart, kart_wifi.WifiKart) else None)
    if "--esitleme-yok" in arg or wifi is None:
        neden = ("--esitleme-yok" if "--esitleme-yok" in arg else
                 "WiFi yukari-akisi yok: kayit verisi yalniz WiFi'den alinir (USB seri dokumu 4C-2, "
                 "ertelendi)")
        kopru.esitleme_neden = neden
        yazdir(f"  Esitleme              : KAPALI ({neden})")
        return None
    ayar, hata = pc_ayar.ayar_oku()
    onay = True
    if hata:
        onay = False
        yazdir(f"! esitleme: {hata} — guvenli tarafta ONAYSIZ calisiyor")
    else:
        deger = ayar.get("esitleme_onay", True)
        if not isinstance(deger, bool):
            onay = False
            yazdir(f"! esitleme: {pc_ayar.AYAR} esitleme_onay true/false degil — ONAYSIZ calisiyor")
        else:
            onay = deger
    if "--onaysiz" in arg:
        onay = False
    aralik = arka_esitle.ARALIK_SN
    a_ayar = (ayar or {}).get("esitleme_aralik_s")
    if isinstance(a_ayar, (int, float)) and not isinstance(a_ayar, bool):
        aralik = float(a_ayar)
    a_arg = _secenek(arg, "--esitleme-aralik")
    if a_arg is not None:
        try:
            aralik = float(a_arg)
        except ValueError:
            raise RuntimeError(f"--esitleme-aralik sayi olmali (saniye): {a_arg!r}") from None
    if aralik < arka_esitle.ARALIK_EN_AZ:
        yazdir(f"! esitleme: aralik {aralik:g} s cok kisa — {arka_esitle.ARALIK_EN_AZ:.0f} s kullaniliyor "
               "(kart dovulmesin)")
        aralik = arka_esitle.ARALIK_EN_AZ
    es = arka_esitle.ArkaEsitleme(
        wifi, kopru.yayinla, Path(arsiv_kok) if arsiv_kok else pc_ayar.arsiv_dizini(), onay=onay,
        aralik=aralik, tetik=lambda: getattr(kart, "baglanti_no", 0),
        usb_etkin=lambda: getattr(kart, "etkin", None) == "usb")
    kopru.esitleme = es
    return es


# ── 4E: MQTT bildirimleri (ayri blok; pc_bildirim.py / windows_bildirim.py) ──
def bildirim_kur(arg: list[str], kart, kopru, yazdir=print, cikis=None, veri_dizini=None):
    """4E (PC13–PC16): MQTT aboneligi + Windows bildirimini kur (BASLATMAZ), kopruye bagla
    (`/bildirim/durum`) ve kartin yerel satirlarini (`G` kayit durumu) dinlet. `--bildirim-yok`
    ise None. WiFi yukari-akisi yoksa (--wifi-yok) onbellekteki bilgiyle calisir (karttan bilgi
    alinamaz). `cikis` yalniz sinamada verilir (gercek bildirim gostermesin)."""
    if "--bildirim-yok" in arg:
        kopru.bildirim_neden = "--bildirim-yok"
        yazdir("  Bildirimler           : KAPALI (--bildirim-yok)")
        return None
    import windows_bildirim
    wifi = kart.wifi if isinstance(kart, kart_wifi.SecmeliKart) else (
        kart if isinstance(kart, kart_wifi.WifiKart) else None)
    dizin = Path(veri_dizini) if veri_dizini else pc_ayar.veri_dizini()
    if cikis is None:
        cikis = (windows_bildirim.WindowsBildirim(dizin, hata=kopru.yayinla) if sys.platform == "win32"
                 else windows_bildirim.YokBildirim(kopru.yayinla))
    mantik = pc_bildirim.Mantik(cikis, yayinla=kopru.yayinla, kalici=dizin / "bildirim" / "son.json")
    pb = pc_bildirim.PcBildirim(wifi, mantik, yayinla=kopru.yayinla, veri_dizini=dizin)
    pc_bildirim.satir_dinle(kart, pb.yerel_satir)
    kopru.bildirim = pb
    return pb


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
            # 4B (PC5): eski kopru/.cihaz anahtari varsa yeni yere BIR KEZ kopyala (tasima)
            gocen = imza.goc_et()
            if gocen and not sessiz:
                yazdir(imza.goc_mesaji(gocen))
            kart = yukari_akis_kur(arg)
        # 4C: eski .satir gunlugu calisma agacindan kullanici veri dizinine (BIR KEZ kopyalanir)
        satir_gocen = satir_goc()
        if satir_gocen and not sessiz:
            yazdir(f"* eski .satir arsivi yeni yere KOPYALANDI ({len(satir_gocen)} dosya): "
                   f"{ESKI_SATIR_DIZINI} -> {pc_ayar.satir_dizini()} (eskisi yerinde)")
        kopru = kopru_mod.Kopru(kart, pc_ayar.satir_dizini())
        sunucu.RequestHandlerClass.kopru = kopru
        esitleme = None if kayit else esitleme_kur(arg, kart, kopru,
                                                   yazdir=(lambda *_: None) if sessiz else yazdir)
        bildirim = None if kayit else bildirim_kur(arg, kart, kopru,           # 4E
                                                   yazdir=(lambda *_: None) if sessiz else yazdir)
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
    if esitleme is not None:
        esitleme.baslat()
    if bildirim is not None:                                # 4E
        bildirim.baslat()

    if not sessiz:
        yazdir(f"Kopru acildi — kart: {kart.ad}")
        yazdir(f"  Panel (bu bilgisayar) : {adres}")
        if lan:
            yazdir(f"  Yerel ag (SALT OKUMA) : http://{kopru_mod.lan_ip()}:{http_port}"
                   f"   — telefonlar izler, yalniz p0 (DURDUR) gonderebilir")
        if isinstance(kart, kart_wifi.SecmeliKart):
            yazdir(f"  Kart                  : USB once; yoksa WiFi {kart.wifi.host} "
                   f"(eslesmis cihaz: {imza.varsayilan_dizin()})")
        elif isinstance(kart, kart_wifi.WifiKart):
            yazdir(f"  Kart                  : YALNIZ WiFi {kart.host} (COM portu acilmaz; "
                   f"eslesmis cihaz: {imza.varsayilan_dizin()})")
        yazdir(f"  Satir gunlugu         : {kopru.arsiv.dizin}")
        if esitleme is not None:
            yazdir(f"  Kayit arsivi          : {esitleme.arsiv_kok} (esitleme {esitleme.aralik:.0f} s'de bir, "
                   + ("ONAY verir — kalici yazimdan sonra)" if esitleme.onay else "ONAYSIZ)"))
        if bildirim is not None:                            # 4E
            yazdir(f"  Bildirimler           : MQTT (yalniz abone) + {bildirim.mantik.cikis.yol} "
                   f"— durum {adres}/bildirim/durum")
        yazdir("Kapatmak icin Ctrl+C (arka plandaysa: kopru\\Kopruyu Durdur.bat)")
        if "--tarayici-acma" not in arg:
            threading.Timer(0.6, lambda: tarayici_ac(adres + "/")).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        if not sessiz:
            yazdir("\nkapatiliyor…")
    finally:
        if esitleme is not None:
            esitleme.durdur()
        if bildirim is not None:                            # 4E
            bildirim.durdur()
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
