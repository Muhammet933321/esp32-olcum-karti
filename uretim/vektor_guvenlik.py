# -*- coding: utf-8 -*-
"""1D test vektorleri: uretim/vektor_guvenlik.json'u URETIR (sabit girdiler).

    python vektor_guvenlik.py          # JSON'u yeniden yazar
    python vektor_guvenlik.py --denetle   # yazmadan, dosya guncel mi (0/1)

Kim kullanir: B72.G (Python), B71.U (C, AVR emulatoru), alt proje 2'nin JS'i.
RFC bolumleri sabit (RFC 4231, RFC 7914 §11); protokol ve imza bolumleri
kopru/imza.py ile hesaplanir ve B72.G bunlari spec bicimiyle BAGIMSIZ yeniden
hesaplayarak dogrular.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BURASI = Path(__file__).parent
sys.path.insert(0, str(BURASI.parent / "kopru"))
import imza as IM                                   # noqa: E402

HEDEF = BURASI / "vektor_guvenlik.json"

RFC4231 = [
    ("0b" * 20, b"Hi There".hex(),
     "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"),
    (b"Jefe".hex(), b"what do ya want for nothing?".hex(),
     "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"),
    ("aa" * 20, "dd" * 50,
     "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"),
    (bytes(range(1, 26)).hex(), "cd" * 50,
     "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"),
    ("aa" * 131, b"Test Using Larger Than Block-Size Key - Hash Key First".hex(),
     "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"),
    ("aa" * 131,
     (b"This is a test using a larger than block-size key and a larger than "
      b"block-size data. The key needs to be hashed before being used by the "
      b"HMAC algorithm.").hex(),
     "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2"),
]
RFC7914 = [
    ("passwd", b"salt".hex(), 1,
     "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc"
     "49ca9cccf179b645991664b39d77ef317c71b845b1e30bd509112041d3a19783"),
    ("Password", b"NaCl".hex(), 80000,
     "4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56"
     "a1d425a1225833549adb841b51c9b3176a272bdebba1d078478f62b397f33c8d"),
]


def uret() -> dict:
    kim = "a1b2c3d4e5f60718"
    nk = bytes(range(0x10, 0x20))
    nc = bytes(range(0x40, 0x50))
    # AVR'de PBKDF2 hizli olsun: tur 2 (kartta tur ayardan, varsayilan >= 50 000)
    kisa = {"parola": "dogru-parola-12", "tuz": bytes(range(0xA0, 0xB0)).hex(), "tur": 2}
    P = IM.pbkdf2(kisa["parola"], bytes.fromhex(kisa["tuz"]), kisa["tur"])
    ad, n = "PC ğ", 3
    K = IM.cihaz_anahtari(P, kim, nk, nc, n)
    uc = {**kisa, "tur": 3}
    proto = {"pbkdf2_kisa": {**kisa, "P": P.hex()},
             "pbkdf2_uc": {**uc, "P": IM.pbkdf2(uc["parola"], bytes.fromhex(uc["tuz"]), 3).hex()},
             "P": P.hex(), "kimlik": kim, "nk": nk.hex(), "nc": nc.hex(), "ad": ad, "n": n,
             "kanit_istemci": IM.kanit_istemci(P, kim, nk, nc, ad).hex(),
             "kanit_kart": IM.kanit_kart(P, kim, nk, nc, n).hex(),
             "K": K.hex()}
    acilis = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
    ornekler = [
        ("get", "GET", "/kayit/liste", [], 1, b""),
        ("get_sorgu", "GET", "/kayit/veri", [("sira", "12"), ("not", "a&b=c ğ")], 1759000000123, b""),
        ("post", "POST", "/komut", [], 2, "Go1234".encode()),
        ("akis", "GET", "/akis", [], 7, b""),     # istek: /akis?_c=3&_s=7&_i=<imza>
    ]
    imz = []
    for adi, y, yol, args, s, gv in ornekler:
        o = {"ad": adi, "K": K.hex(), "yontem": y, "yol": yol,
             "argumanlar": [list(a) for a in args], "acilis": acilis, "sayac": s,
             "govde": gv.hex(),
             "kanonik": IM.kanonik(y, yol, args, acilis, s, gv).hex(),
             "imza": IM.imzala(K, y, yol, args, acilis, s, gv)}
        if adi == "akis":
            o["tam_sorgu"] = f"_c={n}&_s={s}&_i={o['imza']}"
        imz.append(o)
    return {
        "aciklama": "1D test vektorleri — uretim/vektor_guvenlik.py uretir; elle duzenleme",
        "hmac": [{"anahtar": k, "veri": m, "hmac": h} for k, m, h in RFC4231],
        "pbkdf2": [{"parola": p, "tuz": s, "tur": c, "dk": h} for p, s, c, h in RFC7914],
        "protokol": proto,
        "imza": imz,
    }


def main() -> int:
    metin = json.dumps(uret(), ensure_ascii=False, indent=1) + "\n"
    if "--denetle" in sys.argv:
        guncel = HEDEF.exists() and HEDEF.read_text(encoding="utf-8") == metin
        print("guncel" if guncel else "ESKI — python vektor_guvenlik.py")
        return 0 if guncel else 1
    HEDEF.write_text(metin, encoding="utf-8", newline="\n")
    print(f"yazildi: {HEDEF.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
