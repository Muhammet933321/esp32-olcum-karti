# -*- coding: utf-8 -*-
"""PC uygulamasinin sabitleri — koken, port, kullanici veri dizini (4A).

Tek kaynak: `kopru.py`, `pc.py` ve `kart_baglanti.py` (mesgul port mesaji)
buradan okur. Kararlar `tasarim/2026-10-03-alt-proje-4-pc.md` PC1 / PC5.

PC1 — KOKEN `http://olcum.localhost:8770`, sunucu YALNIZ 127.0.0.1'e bagli.
  Olculdu (2026-10-03, Edge 154, basliksiz): `olcum.localhost` istegi
  127.0.0.1'e ulasti (Host: olcum.localhost:8770), `isSecureContext === true`,
  service worker kaydoldu ve yeniden yuklemede sayfayi denetledi.
  `*.localhost` tarayicinin icinde donguye cozulur — hosts dosyasi gerekmez,
  stok-takip'in `127.0.0.1:80` / `stok` adlariyla carpismaz.
  ⚠ Isletim sistemi bu adi COZMEZ (`socket.getaddrinfo('olcum.localhost')`
    hata verir): Python tarafi kopruye hep `127.0.0.1` ile baglanir.
  ⚠ Port KOKENIN parcasi: IndexedDB / service worker / izinler kokene bagli.
    Port mesgulse baska porta DUSULMEZ (eski kopru 80 -> 8770 dusuyordu);
    dusulseydi panelin yerel verisi her seferinde baska bir kokende kalirdi.

PC5 — kullanici verisi depo DISINDA: `%LOCALAPPDATA%\\olcum-karti\\`
  (`OLCUM_PC_DIZIN` ile degistirilebilir). Calisma agaci degisince ya da
  `git clean`'de kaybolmaz.
  4B: eslesmis cihaz anahtari `...\\olcum-karti\\cihaz\\` (`OLCUM_CIHAZ_DIZIN`
  ile ayrica degistirilebilir) — eskiden `kopru/.cihaz` (calisma agaci basina:
  baska agactan acilan kopru anahtari bulamiyordu).

  4C: kayit arsivi `...\\olcum-karti\\arsiv\\`, eski `.satir` gunlugu `...\\olcum-karti\\satir\\`,
  istege bagli ayar `...\\olcum-karti\\ayar.json` (`esitleme_onay`, `esitleme_aralik_s`).

PC6 — kartin WiFi adresi `olcum.local` (`OLCUM_KART_HOST` ya da
  `pc.py --kart-host` ile degisir: IP, ya da kartin kendi AP'sinde 192.168.4.1).
"""
from __future__ import annotations

import os
from pathlib import Path

AD = "olcum.localhost"
PORT = 8770


def adres(port: int = PORT) -> str:
    """Panelin acildigi adres (tarayiciya verilen)."""
    return f"http://{AD}:{port}"


def yerel_istek(port: int, yol: str, veri: bytes | None = None, basliklar=None,
                zaman_asimi: float = 1.5):
    """Bu bilgisayardaki kopruye VEKILSIZ HTTP istegi (yanit nesnesi; `with` ile).

    4A inceleme: `urllib.request.urlopen` ortam (HTTP_PROXY) ve Windows sistem
    vekiline uyar; Windows'un `<local>` istisnasi 127.0.0.1'i KAPSAMIYOR. Vekil
    acikken `zaten_calisiyor` kopruyu goremiyor, ikinci kopya "port baska
    programda" diye cikiyordu. Kopru yalniz bu bilgisayarda: vekil hic kullanilmaz.
    """
    import urllib.request
    istek = urllib.request.Request(f"http://127.0.0.1:{port}{yol}", data=veri,
                                   method="POST" if veri is not None else "GET")
    for ad, deger in (basliklar or {}).items():
        istek.add_header(ad, deger)
    acici = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return acici.open(istek, timeout=zaman_asimi)


def veri_dizini() -> Path:
    """Kullanici basina veri dizini (olusturmaz)."""
    elle = os.environ.get("OLCUM_PC_DIZIN")
    if elle:
        return Path(elle)
    yerel = os.environ.get("LOCALAPPDATA")
    taban = Path(yerel) if yerel else Path.home() / ".local" / "share"
    return taban / "olcum-karti"


def cihaz_dizini() -> Path:
    """4B (PC5): eslesmis cihaz dosyalarinin dizini (olusturmaz). Calisma aninda
    okunur — testler ve ikinci bir kullanici ortam degiskeniyle yonlendirebilsin."""
    elle = os.environ.get("OLCUM_CIHAZ_DIZIN")
    return Path(elle) if elle else veri_dizini() / "cihaz"


def arsiv_dizini() -> Path:
    """4C (PC5): kartin kayit arsivi `...\\olcum-karti\\arsiv\\<kart kimligi>\\akis-<n>\\`
    (olusturmaz). `OLCUM_PC_DIZIN` ile birlikte yer degistirir."""
    return veri_dizini() / "arsiv"


def satir_dizini() -> Path:
    """4C (PC12 baglami): koprunun eski `.satir` satir gunlugu `...\\olcum-karti\\satir\\`
    (olusturmaz). Eskiden calisan agacin `kopru/arsiv/`i idi — `pc.satir_goc` bir kez KOPYALAR."""
    return veri_dizini() / "satir"


AYAR = "ayar.json"


def ayar_oku() -> tuple[dict | None, str | None]:
    """4C: istege bagli kullanici ayari `...\\olcum-karti\\ayar.json` (yoksa {}).
    Donus (ayar, hata): okunamiyor / bicimsiz ise (None, sebep) — cagiran GUVENLI varsayilana
    duser (esitleme: onaysiz)."""
    import json
    p = veri_dizini() / AYAR
    if not p.exists():
        return {}, None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"{AYAR} okunamadi ({type(e).__name__})"
    if not isinstance(d, dict):
        return None, f"{AYAR} bir JSON nesnesi degil"
    return d, None


KART_HOST = "olcum.local"


def kart_host() -> str:
    """4B (PC6): kartin WiFi adresi (ad ya da IP)."""
    return os.environ.get("OLCUM_KART_HOST") or KART_HOST
