"""MQTT paket vektorleri: Kotlin MqttPaket'in baytlari, kartla sinanmis Python basvurusuyla
(kopru/mqtt_istemci.py) AYNI olmali. Bu betik basvuruyu YALNIZ ice aktarir (degistirmez, aga cikmaz)
ve mobil/test/vektor/mqtt.json'i uretir. Degerler uydurma: gercek araci adresi / parola YOK.

    python mobil/araclar/mqtt_vektor_uret.py        (depo kokunden)
"""
import json
import struct
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "kopru"))
import mqtt_istemci as M  # noqa: E402


def hx(b: bytes) -> str:
    return bytes(b).hex()


def connect(kimlik, kullanici, parola, keepalive):
    i = M.Istemci("ornek.invalid", kullanici=kullanici, parola=parola, istemci_id=kimlik, keepalive=keepalive)
    return hx(i._connect_paketi())


def subscribe(no, konu, qos):
    return hx(M.paket((M.SUBSCRIBE << 4) | 0x02, struct.pack(">H", no) + M.dize(konu) + bytes([qos])))


def publish(konu, yuk, qos=0, kalici=False, no=None):
    govde = M.dize(konu) + (struct.pack(">H", no) if qos else b"") + yuk
    ilk = (M.PUBLISH << 4) | (qos << 1) | (1 if kalici else 0)
    k, y, r, q, n = M.publish_coz(ilk, govde)
    return {"ilk": ilk, "govde": hx(govde), "paket": hx(M.paket(ilk, govde)), "konu": k, "yuk": hx(y), "kalici": r, "qos": q, "no": n}


ONEK = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
v = {
    "aciklama": "kopru/mqtt_istemci.py'den uretildi (mobil/araclar/mqtt_vektor_uret.py); elle duzenleme",
    "uzunluk": [{"n": n, "bayt": hx(M.uzunluk_kodla(n))} for n in
                [0, 1, 127, 128, 129, 16383, 16384, 2097151, 2097152, 268435455]],
    "dize": [{"metin": m, "bayt": hx(M.dize(m))} for m in ["", "MQTT", "ok/x/durum", "ğüşİ ölçüm", "a" * 300]],
    "connect": [
        {"kimlik": "okm-0011aabb", "kullanici": "olcum-cihaz", "parola": "sinama-ğ 1", "keepalive": 5,
         "paket": connect("okm-0011aabb", "olcum-cihaz", "sinama-ğ 1", 5)},
        {"kimlik": "okm-1", "kullanici": "yalniz-kullanici", "parola": None, "keepalive": 30,
         "paket": connect("okm-1", "yalniz-kullanici", None, 30)},
        {"kimlik": "okm-2", "kullanici": None, "parola": None, "keepalive": 0, "paket": connect("okm-2", None, None, 0)},
        {"kimlik": "k" * 200, "kullanici": "u" * 150, "parola": "p" * 150, "keepalive": 65535,
         "paket": connect("k" * 200, "u" * 150, "p" * 150, 65535)},
    ],
    "subscribe": [
        {"no": 1, "konu": f"ok/{ONEK}/#", "qos": 1, "paket": subscribe(1, f"ok/{ONEK}/#", 1)},
        {"no": 65535, "konu": "ok/x/durum", "qos": 0, "paket": subscribe(65535, "ok/x/durum", 0)},
    ],
    "sabit": {
        "puback_1": hx(M.paket(M.PUBACK << 4, struct.pack(">H", 1))),
        "puback_65535": hx(M.paket(M.PUBACK << 4, struct.pack(">H", 65535))),
        "pingreq": hx(M.paket(M.PINGREQ << 4)),
        "disconnect": hx(M.paket(M.DISCONNECT << 4)),
    },
    "publish": [
        publish(f"ok/{ONEK}/durum", b"OKB1" + bytes(range(40)), 1, True, 7),
        publish(f"ok/{ONEK}/olay", b"\x00\xff\x80", 1, False, 65535),
        publish("ok/x/durum", b"", 0, True),
        publish("ölçüm/ğ", b"x" * 300, 0, False),
        publish("", b"yuk", 0, False),
    ],
    "publish_red": [
        {"ad": "qos3", "ilk": 0x36, "govde": hx(M.dize("a") + b"\x00\x01")},
        {"ad": "kisa", "ilk": 0x30, "govde": "00"},
        {"ad": "konu_eksik", "ilk": 0x30, "govde": "000561"},
        {"ad": "konu_utf8_degil", "ilk": 0x30, "govde": "0002ff00"},
        {"ad": "paket_no_eksik", "ilk": 0x32, "govde": hx(M.dize("a") + b"\x00")},
    ],
}
for r in v["publish_red"]:
    try:
        M.publish_coz(r["ilk"], bytes.fromhex(r["govde"]))
        raise SystemExit(f"basvuru reddetmedi: {r['ad']}")
    except M.MqttHata:
        pass

hedef = KOK / "mobil" / "test" / "vektor" / "mqtt.json"
hedef.write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(hedef.relative_to(KOK), len(v["connect"]), len(v["publish"]))
