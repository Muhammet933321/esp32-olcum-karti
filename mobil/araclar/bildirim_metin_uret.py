"""Bildirim metinleri (tasarim A43: Kotlin tarafinin metinleri strings.xml'de, tr + en).

TEK KAYNAK PC'nin sozlugu (kopru/bildirim_metin.py METIN): bu betik onu YALNIZ ice aktarir ve
  1) android/app/src/main/res/values/bildirim.xml (tr) ve values-en/bildirim.xml (en) uretir
     — ad: anahtardaki "." -> "_" ("bld.kopuk" -> "bld_kopuk"); yer tutucular "{ad}" olarak KALIR
       (metni BildirimMetin.kt kurar; Android'in %1$s bicimi kullanilmaz);
  2) mobil/test/vektor/bildirim_metin.json: karar vektorundeki (bildirim_karar.json) her senaryo icin
     PC'nin GERCEK metin ciktisi (tr ve en). Kotlin ayni senaryoda ayni metinleri uretmeli.
Telefona ozel sozler TELEFON'da: "bu PC" -> "bu telefon", arsiv -> Kayitlar ekrani.

    python mobil/araclar/bildirim_metin_uret.py        (depo kokunden; once bildirim_karar_vektor_uret.py)
"""
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

KOK = Path(__file__).resolve().parents[2]
_gecici = tempfile.mkdtemp(prefix="bmu-")
os.environ["LOCALAPPDATA"] = _gecici
os.environ["APPDATA"] = _gecici
sys.path.insert(0, str(KOK / "kopru"))
import pc_bildirim as P  # noqa: E402

BM = P.BM
TELEFON = {
    "bld.kacirilan": {
        "tr": "{adet} olay kaçırıldı (bu telefon bağlı değilken) — ayrıntılar kayıtlar eşitlenince Kayıtlar ekranında",
        "en": "{adet} events were missed (while this phone was not connected) — details are on the Recordings screen once recordings sync",
    },
    "bld.esik": {
        "tr": "Eşitlenmemiş veri %{deger} (eşik %{esik}) — kayıtları eşitleyin",
        "en": "Unsynced data {deger}% (threshold {esik}%) — sync the recordings",
    },
}
for anahtar, metin in TELEFON.items():
    assert anahtar in BM.METIN, anahtar
    BM.METIN[anahtar] = dict(BM.METIN[anahtar], **metin)


def xml_yaz(dil, hedef):
    satirlar = ["<?xml version='1.0' encoding='utf-8'?>",
                "<!-- URETILDI: mobil/araclar/bildirim_metin_uret.py (kaynak: kopru/bildirim_metin.py). Elle duzenleme. -->",
                "<resources>"]
    for anahtar in sorted(BM.METIN):
        s = BM.METIN[anahtar].get(dil)
        if s is None:
            raise SystemExit(f"{anahtar}: {dil} metni yok")
        # Android kaynak kacislari: \ ' " ve bastaki @ / ?
        s = s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        if s[:1] in "@?":
            s = "\\" + s
        satirlar.append(f'    <string name="{anahtar.replace(".", "_")}" translatable="{"true" if dil != "tr" or True else "false"}">{escape(s)}</string>')
    satirlar.append("</resources>")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text("\n".join(satirlar) + "\n", encoding="utf-8", newline="\n")


RES = KOK / "mobil" / "android" / "app" / "src" / "main" / "res"
xml_yaz("tr", RES / "values" / "bildirim.xml")
xml_yaz("en", RES / "values-en" / "bildirim.xml")


class Cikis:
    def __init__(self):
        self.liste = []

    def goster(self, etiket, baslik, metin, sessiz=False):
        self.liste.append([etiket, baslik, metin, bool(sessiz)])


def g_satiri(durum, oturum):
    return "G " + " ".join(str(x) for x in [durum, oturum] + [0] * (P.G_ALAN - 2))


def kos(s, dil):
    saat = {"mono": 1000.0, "duvar": 1790000000.0}
    cikis = Cikis()
    kapali = set(s.get("kapali", []))
    kalici = None
    if s.get("onceki") is not None:
        kalici = Path(_gecici) / f"kalici-{dil}-{s['ad']}.json"
        kalici.write_text(json.dumps({"a": s["onceki"][0], "n": s["onceki"][1]}), encoding="utf-8")
    eski = (P.PENCERE_SN, P.YAKIN_SN)
    P.PENCERE_SN, P.YAKIN_SN = float(s.get("pencere", 900)), float(s.get("yakin", 120))
    try:
        m = P.Mantik(cikis, ayar=lambda: ({x: x not in kapali for x in P.SINIFLAR}, dil, None),
                     saat=lambda: saat["mono"], duvar=lambda: saat["duvar"], kalici=kalici)
        for op in s["ops"]:
            t = op[0]
            if t == "saat":
                saat["mono"] += op[1]
                saat["duvar"] += op[1]
            elif t == "mqtt":
                m.mqtt_mesaj(op[1], op[2])
            elif t == "bagli":
                m.mqtt_bagli_oldu(op[1])
            elif t == "yerel":
                m.yerel_satir(g_satiri(op[1], op[2]))
            elif t == "yerel_gor":
                m.yerel_satir("K 1 2 3")
            elif t == "tik":
                m.tik()
        return cikis.liste
    finally:
        P.PENCERE_SN, P.YAKIN_SN = eski


karar = json.loads((KOK / "mobil" / "test" / "vektor" / "bildirim_karar.json").read_text(encoding="utf-8"))
cikti = {
    "aciklama": "kopru/pc_bildirim.py Mantik'in GERCEK metin ciktisi (mobil/araclar/bildirim_metin_uret.py); elle duzenleme",
    # Saat yazisi YEREL saat dilimiyle kurulur: testin ayni dilimde kosmasi icin uretildigi dilimin UTC farki (dk).
    "utc_fark_dk": int(datetime.datetime.fromtimestamp(1790000000).astimezone().utcoffset().total_seconds() // 60),
    "senaryolar": [{"ad": s["ad"], "tr": kos(s, "tr"), "en": kos(s, "en")} for s in karar["senaryolar"]],
}
hedef = KOK / "mobil" / "test" / "vektor" / "bildirim_metin.json"
hedef.write_text(json.dumps(cikti, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("bildirim.xml (tr, en):", len(BM.METIN), "metin;", hedef.relative_to(KOK), sum(len(s["tr"]) for s in cikti["senaryolar"]), "bildirim")
