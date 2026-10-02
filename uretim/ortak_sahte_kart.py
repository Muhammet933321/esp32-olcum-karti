# -*- coding: utf-8 -*-
"""B73 / 2C — ESITLEME ISTEMCISI CAPRAZ TESTI: B72'nin sahte karti + Python basvuru kosucusu.

    python ortak_sahte_kart.py sunucu   # JS tarafi icin sahte kart (yalniz 127.0.0.1)
    python ortak_sahte_kart.py py       # ayni senaryolari kopru/kayit_esitle.py ile kosar

Kart: test_kayit_esp._SahteKart + _sunucu — B72.E'nin sahte karti AYNEN (burada
yeniden yazilmadi; yalniz durumu senaryo adimlarina gore degistirilir).

Senaryolar ortak/test/esitle.test.js'de VERI olarak yazili. Adim yorumlayicisinin
kart/disk kismi BURADA tek yerde (`kart_ayarla`, `disk_baytlari`); JS tarafi kart
ve disk adimlarini `sunucu` kipinin komutlariyla yaptirir. Boylece Python ve JS
istemcisi AYNI kart durumlarindan gecer; test sakladiklari akis baytlarini, durumu,
kalibrasyon dosyalarini ve onay dizisini karsilastirir.

`sunucu` kipi: stdout ilk satir {"port": N}; stdin her satir bir JSON komut,
stdout her satir bir JSON yanit (ASCII):
  {"k": "sifirla", "kayitlar": [[n, bas(, yuk_bayt)], ...], "cihaz": {"n", "K"} | null}
  {"k": "kart", "alanlar": {...}}                    -> kart_ayarla
  {"k": "disk", "adim": {...}, "son_sira": N}        -> {"hex": eklenecek baytlar}
  {"k": "durum"}                                     -> {onay, imzali, ret_401, komutlar}
  {"k": "json", "deger": x}                          -> {"metin": json.dumps(x, indent=1, ...)}
  {"k": "kal_cakisir", "eski": x, "yeni": y}         -> {"sonuc": bool} | {"hata": tur}
  {"k": "kal_bozuk", "veri": x, "eski": y}           -> {"bozuk", "veri"} | {"hata": tur}
  {"k": "son"}
`py` kipi: stdin senaryolar JSON (UTF-8); stdout her senaryonun adim anliklari JSON.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_kayit_esp as T                            # noqa: E402  (sahte kart B72)

KB, KE = T.KB, T.KE
import imza as IM                                     # noqa: E402  (kopru/, T yolu ekledi)

ALANLAR = {"bozuk", "sirayi_yok_say", "bos_don", "kimlik", "onay", "onay_dusur",
           "kal_liste", "imza_zorunlu"}


def _sira(ham: bytes) -> int:
    return struct.unpack_from("<I", ham, 4)[0]


def kayitlar_kur(araliklar) -> list[bytes]:
    """[[n, bas]] -> test_kayit_esp._kayitlar(n, bas); [[n, bas, yuk]] -> sabit yuk boylu
    NOKTA kayitlari (parca siniri: 1012 B yuk = en buyuk kayit 1028 B)."""
    kay: list[bytes] = []
    for a in araliklar:
        n, bas = int(a[0]), int(a[1])
        if len(a) > 2:
            kay += [KB.kayit_paketle(KB.T_NOKTA, i, 7, bytes((i * 7 + j) & 0xFF for j in range(int(a[2]))))
                    for i in range(bas, bas + n)]
        else:
            kay += T._kayitlar(n, bas)
    return kay


def sifirla(kart, kayitlar, cihaz) -> None:
    kart.__init__(kayitlar_kur(kayitlar))
    if cihaz:
        kart.cihazlar[int(cihaz["n"])] = bytes.fromhex(cihaz["K"])


def kart_ayarla(kart, alanlar: dict) -> None:
    for a, v in alanlar.items():
        if a == "kayitlar":
            kart.kayitlar = kayitlar_kur(v)
        elif a == "kal_yanit":       # ["ham"|"kes", hex] · ["kod", 500] · null
            kart.kal_yanit = None if v is None else (
                (v[0], int(v[1])) if v[0] == "kod" else (v[0], bytes.fromhex(v[1])))
        elif a in ALANLAR:
            setattr(kart, a, v)
        else:
            raise ValueError(f"bilinmeyen kart alani: {a}")


def disk_baytlari(kart, adim: dict, son: int) -> bytes:
    """Cokme benzetimi: depodaki akisa durum YAZILMADAN eklenen baytlar."""
    e = adim["ekle"]
    if e == "yarim":                  # sira son+1'in yarisi (B72.E9)
        ham = next(k for k in kart.kayitlar if _sira(k) == son + 1)
        return ham[:len(ham) // 2]
    if e == "sonraki":                # son'dan sonrakiler, `azami` bayta kesik (B72.E15)
        return b"".join(k for k in kart.kayitlar if _sira(k) > son)[:int(adim["azami"])]
    if e == "son_kayit":              # GECERLI ama sirasi ATLAYAN kuyruk (B72.E17)
        return kart.kayitlar[-1]
    raise ValueError(f"bilinmeyen disk adimi: {e}")


def hata_turu(h: BaseException) -> str:
    if isinstance(h, ValueError):
        return "deger"
    if isinstance(h, RuntimeError):
        return "calisma"
    if isinstance(h, OSError):
        return "os"
    return type(h).__name__


def _py_hata(islev):
    try:
        return islev(), None
    except Exception as h:                             # noqa: BLE001
        return None, type(h).__name__


# ── py kipi: Python basvurusu ────────────────────────────────────────────
def senaryo_py(kart, taban: str, d: Path, s: dict) -> dict:
    sifirla(kart, s["kayitlar"], s.get("cihaz"))
    onaylar: list[list[int]] = []
    arsivler: list[str] = []
    anliklar = []
    cihaz = None

    def boy() -> int:
        p = d / KE.DOSYA
        return p.stat().st_size if p.exists() else 0

    for adim in s["adimlar"]:
        tur = adim["tur"]
        if tur == "kart":
            kart_ayarla(kart, adim["alanlar"])
        elif tur == "disk":
            if "kal_metin" in adim:
                d.mkdir(parents=True, exist_ok=True)
                (d / KE.KAL_DOSYA).write_bytes(adim["kal_metin"].encode("utf-8"))
            else:
                b = disk_baytlari(kart, adim, KE.Esitleyici(taban, d).son_sira())
                with open(d / KE.DOSYA, "ab") as f:
                    f.write(b)
        elif tur == "durum":
            e = KE.Esitleyici(taban, d)
            x = e._durum()
            x.update(adim["alanlar"])
            e._durum_yaz(x)
        elif tur == "esitle":
            onay_ad = adim.get("onay", "kart")
            imzali = bool(adim.get("imzali"))
            if imzali and cihaz is None:
                cihaz = IM.Cihaz(d.parent / (d.name + "-cihaz") / "c.json", kart.gkimlik,
                                 int(s["cihaz"]["n"]), bytes.fromhex(s["cihaz"]["K"]), "PC")
            ic = KE.imzali_onay(cihaz, taban) if imzali else kart.onayla

            def onay(sira: int, ic=ic, onay_ad=onay_ad) -> None:
                onaylar.append([sira, boy()])
                if onay_ad == "patlayan":
                    raise OSError("ag koptu")
                ic(sira)
            kw = {"onay_bekle": 0.01}
            if "bayt" in adim:
                kw["bayt"] = adim["bayt"]
            e = KE.Esitleyici(taban, d, None if onay_ad == "yok" else onay,
                              cihaz=cihaz if imzali else None, **kw)
            r, hata = None, None
            try:
                r = e.esitle(adim["azami_tur"]) if "azami_tur" in adim else e.esitle()
            except Exception as h:                     # noqa: BLE001
                hata = {"tur": hata_turu(h), "mesaj": str(h)}
            if r is not None:
                r = json.loads(json.dumps(r))          # demet -> liste
                if r.get("kalibrasyon_arsiv"):
                    arsivler.append(r["kalibrasyon_arsiv"])
                    r["kalibrasyon_arsiv"] = len(arsivler) - 1
            p, pd, pk = d / KE.DOSYA, d / KE.DURUM, d / KE.KAL_DOSYA
            anliklar.append({
                "sonuc": r, "hata": hata,
                "veri": p.read_bytes().hex() if p.exists() else "",
                "durum": json.loads(pd.read_text(encoding="utf-8")) if pd.exists() else None,
                "kal": pk.read_bytes().hex() if pk.exists() else None,
                "arsivler": [(d / a).read_bytes().hex() for a in arsivler],
                "onaylar": [list(x) for x in onaylar],
                "kart_onay": kart.onay, "imzali": kart.imzali, "ret_401": kart.ret_401,
            })
        else:
            raise ValueError(f"bilinmeyen adim: {tur}")
    return {"ad": s["ad"], "anliklar": anliklar}


def kos_py(senaryolar: list) -> list:
    kart = T._SahteKart([])
    sunucu, taban = T._sunucu(kart)
    cikti = []
    try:
        for s in senaryolar:
            with tempfile.TemporaryDirectory() as g:
                cikti.append(senaryo_py(kart, taban, Path(g) / "esitle", s))
    finally:
        sunucu.shutdown()
    return cikti


# ── sunucu kipi: JS istemcisinin karsisindaki sahte kart ──────────────────
def komut(kart, k: dict) -> dict:
    ad = k.get("k")
    if ad == "sifirla":
        sifirla(kart, k["kayitlar"], k.get("cihaz"))
        return {"tamam": True}
    if ad == "kart":
        kart_ayarla(kart, k["alanlar"])
        return {"tamam": True}
    if ad == "disk":
        return {"hex": disk_baytlari(kart, k["adim"], int(k["son_sira"])).hex()}
    if ad == "durum":
        return {"onay": kart.onay, "imzali": kart.imzali, "ret_401": kart.ret_401,
                "komutlar": kart.komutlar}
    if ad == "json":
        return {"metin": json.dumps(k["deger"], ensure_ascii=False, indent=1)}
    if ad == "kal_cakisir":
        s, h = _py_hata(lambda: KE.Esitleyici._kal_cakisir(k["eski"], k["yeni"]))
        return {"sonuc": s} if h is None else {"hata": h}
    if ad == "kal_bozuk":
        veri = k["veri"]
        s, h = _py_hata(lambda: KE.Esitleyici._kal_bozuk_birlestir(veri, k["eski"]))
        return {"bozuk": s, "veri": veri} if h is None else {"hata": h}
    if ad == "son":
        return {"tamam": True}
    raise ValueError(f"bilinmeyen komut: {ad}")


def _yaz(x) -> None:
    sys.stdout.write(json.dumps(x) + "\n")              # ensure_ascii: kod sayfasi sorunu yok
    sys.stdout.flush()


def sunucu_kipi() -> int:
    kart = T._SahteKart([])
    sunucu, _ = T._sunucu(kart)
    _yaz({"port": sunucu.server_address[1]})
    try:
        while True:
            satir = sys.stdin.buffer.readline()
            if not satir:
                break
            if not satir.strip():
                continue
            k = json.loads(satir.decode("utf-8"))
            try:
                yanit = komut(kart, k)
            except Exception as h:                     # noqa: BLE001
                yanit = {"hata": f"{type(h).__name__}: {h}"}
            _yaz(yanit)
            if k.get("k") == "son":
                break
    finally:
        sunucu.shutdown()
    return 0


def main(argv: list[str]) -> int:
    kip = argv[1] if len(argv) > 1 else ""
    if kip == "sunucu":
        return sunucu_kipi()
    if kip == "py":
        senaryolar = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        _yaz(kos_py(senaryolar))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
