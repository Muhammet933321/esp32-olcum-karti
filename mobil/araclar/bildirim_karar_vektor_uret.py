"""Bildirim karar vektorleri: Kotlin `BildirimKarar`, kartla ve gercek araciyla sinanmis Python
basvurusuyla (kopru/pc_bildirim.py `Mantik`) AYNI olay dizisinde AYNI bildirim dizisini uretmeli.

Bu betik basvuruyu YALNIZ ice aktarir (degistirmez, aga cikmaz, gercek ayar / veri dizinine dokunmaz:
LOCALAPPDATA gecici dizine cevrilir) ve mobil/test/vektor/bildirim_karar.json'i uretir. Metin kurulmaz:
basvurunun metin islevleri (`BM.metin`, `kod_metni`, `_sayi`, `_sure`, `_saat_yazi`) "anahtar + degerler"
dokumune cevrilir; Kotlin tarafi ayni dokumu uretir.

    python mobil/araclar/bildirim_karar_vektor_uret.py        (depo kokunden)
"""
import json
import os
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
_gecici = tempfile.mkdtemp(prefix="bkv-")
os.environ["LOCALAPPDATA"] = _gecici
os.environ["APPDATA"] = _gecici
sys.path.insert(0, str(KOK / "kopru"))
import pc_bildirim as P  # noqa: E402


def _py(v):
    return str(v)


def _metin(anahtar, dil="tr", **deg):
    if anahtar == "bld.kesildi_saat":
        return f"EK({anahtar},{deg['saat']})"
    return json.dumps({"anahtar": anahtar, "deg": {k: _py(v) for k, v in deg.items()}}, ensure_ascii=False)


P.BM.metin = _metin
P.BM.kod_metni = lambda onek, kod, dil="tr": f"KOD({onek}{_py(kod)})"
P._sayi = lambda x, bolen, basamak, dil: f"SAYI({_py(x)},{bolen},{basamak})"
P._sure = lambda ms: f"SURE({_py(ms)})"
P._saat_yazi = lambda unix: f"SAAT({unix})"


class Cikis:
    def __init__(self):
        self.liste = []

    def goster(self, etiket, baslik, metin, sessiz=False):
        d = json.loads(metin)
        self.liste.append([etiket, d["anahtar"], d["deg"], bool(sessiz)])


def g_satiri(durum, oturum):
    return "G " + " ".join(str(x) for x in [durum, oturum] + [0] * (P.G_ALAN - 2))


def kos(s):
    saat = {"mono": 1000.0, "duvar": 1790000000.0}
    cikis = Cikis()
    kapali = set(s.get("kapali", []))
    kalici = None
    if s.get("onceki") is not None:
        kalici = Path(_gecici) / f"kalici-{s['ad']}.json"
        kalici.write_text(json.dumps({"a": s["onceki"][0], "n": s["onceki"][1]}), encoding="utf-8")
    eski = (P.PENCERE_SN, P.YAKIN_SN)
    P.PENCERE_SN, P.YAKIN_SN = float(s.get("pencere", 900)), float(s.get("yakin", 120))
    try:
        m = P.Mantik(cikis, ayar=lambda: ({x: x not in kapali for x in P.SINIFLAR}, "tr", None),
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
            else:
                raise SystemExit(f"bilinmeyen islem: {t}")
        d = m.durum()
        return {"bildirimler": cikis.liste,
                "son": {"kacirilan": d["kacirilan"], "baglanti": d["baglanti_bildirimi"],
                        "kart_cevrimici": d["kart_cevrimici"], "kayit_suruyor": d["kayit_suruyor"]}}
    finally:
        P.PENCERE_SN, P.YAKIN_SN = eski


def durum(c=1, a=3, t=1790000000, k=1, o=0, y=1, **ek):
    d = {"c": c, "a": a, "t": t, "k": k, "o": o, "y": y, "d": 5, "e": 0, "f": "A3-test"}
    d.update(ek)
    return d


def olay(n, o, a=3, **ek):
    d = {"n": n, "a": a, "t": 1790000100, "o": o}
    d.update(ek)
    return d


KAYITTA = durum(k=2, o=53)
S = [
    {"ad": "vasiyet_kayit_surerken_kopuk_sonra_geri", "ops": [
        ["bagli", True], ["mqtt", "durum", KAYITTA], ["tik"], ["mqtt", "durum", {"c": 0, "a": 3}], ["tik"], ["tik"],
        ["saat", 30], ["mqtt", "durum", KAYITTA], ["tik"]]},
    {"ad": "vasiyet_kayit_yokken_sessiz", "ops": [
        ["bagli", True], ["mqtt", "durum", durum(k=1)], ["mqtt", "durum", {"c": 0, "a": 3}], ["tik"], ["saat", 5],
        ["mqtt", "durum", durum(k=1)]]},
    {"ad": "geri_geldi_kayit_bitmis", "ops": [
        ["bagli", True], ["mqtt", "durum", KAYITTA], ["mqtt", "durum", {"c": 0, "a": 3}], ["saat", 40], ["mqtt", "durum", durum(k=1, o=53)]]},
    {"ad": "ev_interneti_kart_yerelde", "ops": [
        ["bagli", True], ["mqtt", "durum", KAYITTA], ["yerel_gor"], ["mqtt", "durum", {"c": 0, "a": 3}], ["tik"],
        ["saat", 10], ["yerel_gor"], ["tik"], ["saat", 16], ["tik"], ["saat", 2], ["yerel_gor"], ["tik"],
        ["mqtt", "durum", KAYITTA]]},
    {"ad": "bekliyor_durumu_da_kayit_sayilir_ve_py_esitligi", "ops": [
        ["bagli", True], ["mqtt", "durum", durum(c=True, k=4.0, o=60)], ["mqtt", "durum", {"c": 0.0, "a": 3}],
        ["mqtt", "durum", durum(c=1.0, k=4, o=60)]]},
    {"ad": "olay_yineleme_ve_bosluk", "ops": [
        ["bagli", True], ["mqtt", "olay", olay(1, "deneme")], ["mqtt", "olay", olay(1, "deneme")],
        ["mqtt", "olay", olay(2, "deneme")], ["mqtt", "olay", olay(6, "deneme")], ["mqtt", "olay", olay(4, "deneme")],
        ["mqtt", "olay", olay(9, "esik", deger=612, esik=600)]]},
    {"ad": "kart_yeniden_basladi_yeni_acilis", "ops": [
        ["mqtt", "olay", olay(5, "deneme", a=3)], ["mqtt", "olay", olay(3, "basladi", a=4, devam=1, oturum=70)],
        ["mqtt", "olay", olay(4, "basladi", a=4, devam=0, oturum=70)], ["mqtt", "olay", olay(1, "basladi", a=5, devam=1)]]},
    {"ad": "onceki_calismadan_kalan", "onceki": [3, 7], "ops": [
        ["mqtt", "olay", olay(6, "deneme")], ["mqtt", "olay", olay(7, "deneme")], ["mqtt", "olay", olay(10, "deneme")],
        ["mqtt", "olay", olay(8, "deneme")]]},
    {"ad": "onceki_baska_acilis", "onceki": [2, 40], "ops": [
        ["mqtt", "olay", olay(3, "deneme", a=3)], ["mqtt", "olay", olay(4, "dolu", a=3)]]},
    {"ad": "kayit_bitti_sebepler", "ops": [
        ["mqtt", "durum", durum(k=2, o=81, y=2)],
        ["mqtt", "olay", olay(1, "kayit_bitti", sebep=1, oturum=80, nokta=1200)],
        ["mqtt", "olay", olay(2, "kayit_bitti", sebep=2, oturum=81)],
        ["mqtt", "olay", olay(3, "kayit_bitti", sebep=5, oturum=81)],
        ["mqtt", "olay", olay(4, "kayit_bitti", sebep=5, oturum=82)],
        ["mqtt", "olay", olay(5, "kayit_bitti", sebep=7, oturum=83)],
        ["mqtt", "olay", olay(6, "kayit_bitti", sebep=None, oturum=84, nokta=None)],
        ["mqtt", "olay", olay(7, "kayit_bitti", sebep=3)]]},
    {"ad": "kesildi_son_gorulme_yokken", "ops": [
        ["mqtt", "durum", durum(t=0, k=2, o=90, y=3)], ["mqtt", "olay", olay(1, "kayit_bitti", sebep=5, oturum=90)]]},
    {"ad": "pil_bitti_ve_esik_ve_dolu", "ops": [
        ["mqtt", "olay", olay(1, "pil_bitti", durum=2, mah_milli=2415300, wh_milli=8950, sure_ms=5400000)],
        ["saat", 200], ["mqtt", "olay", olay(2, "pil_bitti", durum=None, mah_milli="x", wh_milli=None, sure_ms=-5)],
        ["saat", 200], ["mqtt", "olay", olay(3, "dolu")], ["mqtt", "olay", olay(4, "esik", deger=None, esik=600)],
        ["mqtt", "olay", olay(5, "bilinmeyen_olay")]]},
    {"ad": "yerel_bitti_sonra_mqtt_ayrinti_sessiz_guncelleme", "ops": [
        ["mqtt", "durum", durum(k=2, o=53)], ["yerel", 2, 53], ["yerel", 1, 53],
        ["saat", 3], ["mqtt", "olay", olay(1, "kayit_bitti", sebep=1, oturum=53, nokta=77)],
        ["mqtt", "olay", olay(2, "kayit_bitti", sebep=1, oturum=53, nokta=77)]]},
    {"ad": "mqtt_once_sonra_yerel_dusuyor", "ops": [
        ["yerel", 2, 53], ["mqtt", "olay", olay(1, "kayit_bitti", sebep=1, oturum=53, nokta=5)], ["saat", 2], ["yerel", 1, 53]]},
    {"ad": "yerel_dolu_ve_oturum_degisimi", "ops": [
        ["yerel", 2, 10], ["yerel", 3, 10], ["yerel", 2, 11], ["yerel", 2, 12], ["yerel", 4, 12], ["yerel", 1, 12]]},
    {"ad": "pencere_dolunca_yeni_bildirim", "pencere": 900, "ops": [
        ["yerel", 2, 53], ["yerel", 1, 53], ["saat", 901], ["mqtt", "olay", olay(1, "kayit_bitti", sebep=1, oturum=53, nokta=1)]]},
    {"ad": "oturumsuz_haber_yakin_pencere", "yakin": 120, "ops": [
        ["yerel", 2, 53], ["yerel", 1, 53], ["saat", 100],
        ["mqtt", "olay", olay(1, "pil_bitti", durum=1, mah_milli=1000, wh_milli=3700, sure_ms=60000)],
        ["saat", 130], ["mqtt", "olay", olay(2, "dolu")]]},
    {"ad": "telefon_pencereleri_30s", "pencere": 30, "yakin": 30, "ops": [
        ["yerel", 2, 53], ["yerel", 1, 53], ["saat", 20], ["mqtt", "olay", olay(1, "kayit_bitti", sebep=1, oturum=53, nokta=9)],
        ["yerel", 2, 54], ["yerel", 1, 54], ["saat", 31], ["mqtt", "olay", olay(2, "kayit_bitti", sebep=1, oturum=54, nokta=9)]]},
    {"ad": "sinif_kapali", "kapali": ["bitti", "kopuk"], "ops": [
        ["bagli", True], ["mqtt", "durum", KAYITTA], ["yerel", 2, 53], ["yerel", 1, 53],
        ["mqtt", "olay", olay(1, "kayit_bitti", sebep=1, oturum=53, nokta=4)],
        ["mqtt", "olay", olay(2, "kayit_bitti", sebep=2, oturum=54)],
        ["mqtt", "durum", durum(k=2, o=55)], ["mqtt", "durum", {"c": 0, "a": 3}], ["mqtt", "olay", olay(5, "deneme")]]},
    {"ad": "bitti_kapali_dolu_acik_guncelleme_ilk_kez_sesli", "kapali": ["bitti"], "ops": [
        ["yerel", 2, 53], ["yerel", 1, 53], ["mqtt", "olay", olay(1, "kayit_bitti", sebep=2, oturum=53)]]},
    {"ad": "yalniz_yerel_yol_kopuk_ve_geri", "ops": [
        ["yerel", 2, 53], ["tik"], ["saat", 21], ["tik"], ["tik"], ["saat", 5], ["yerel", 2, 53], ["tik"],
        ["saat", 25], ["tik"], ["yerel", 1, 53], ["tik"]]},
    {"ad": "yerel_yol_kayit_yokken_sessiz_ve_mqtt_varken_yok", "ops": [
        ["yerel", 1, 53], ["saat", 30], ["tik"], ["bagli", True], ["mqtt", "durum", KAYITTA], ["yerel", 2, 53],
        ["saat", 30], ["tik"]]},
    {"ad": "yerel_kopuk_sonra_araci_cevrimdisi_diyor", "ops": [
        ["yerel", 2, 53], ["saat", 21], ["tik"], ["bagli", True], ["mqtt", "durum", {"c": 0, "a": 3}], ["tik"],
        ["yerel_gor"], ["tik"], ["mqtt", "durum", KAYITTA]]},
    {"ad": "bicimsiz_olaylar_yok_sayilir", "ops": [
        ["mqtt", "olay", {"n": "1", "a": 3, "o": "deneme"}], ["mqtt", "olay", {"n": 1, "a": 3.0, "o": "deneme"}],
        ["mqtt", "olay", {"n": True, "a": 3, "o": "deneme"}], ["mqtt", "olay", {"n": 1, "a": 3, "o": 5}],
        ["mqtt", "olay", {"n": 1, "a": 3}], ["mqtt", "olay", {}], ["mqtt", "baska", {"c": 1}],
        ["mqtt", "durum", {"c": 2}], ["mqtt", "durum", {}], ["mqtt", "olay", olay(2, "deneme")]]},
    {"ad": "yerel_ve_durum_hangisi_yeniyse", "ops": [
        ["bagli", True], ["yerel", 2, 53], ["saat", 5], ["mqtt", "durum", durum(k=1, o=53)], ["mqtt", "durum", {"c": 0, "a": 3}],
        ["saat", 5], ["mqtt", "durum", durum(k=1, o=53)], ["saat", 1], ["yerel", 2, 53], ["saat", 20],
        ["mqtt", "durum", {"c": 0, "a": 3}]]},
]

cikti = {"aciklama": "kopru/pc_bildirim.py Mantik'ten uretildi (mobil/araclar/bildirim_karar_vektor_uret.py); elle duzenleme",
         "senaryolar": [dict(s, beklenen=kos(s)) for s in S]}
hedef = KOK / "mobil" / "test" / "vektor" / "bildirim_karar.json"
hedef.write_text(json.dumps(cikti, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
toplam = sum(len(s["beklenen"]["bildirimler"]) for s in cikti["senaryolar"])
print(hedef.relative_to(KOK), len(S), "senaryo", toplam, "bildirim")
