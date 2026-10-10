"""Belgelerin iki dili: Turkce (ana, BELGELER/) ve Ingilizce (BELGELER/en/)."""
from pathlib import Path

DILLER = ("tr", "en")


def M(tr, en):
    """Iki dilli metin."""
    return {"tr": tr, "en": en}


def sec(metin, dil):
    """M(...) ise dile gore sec; duz dizgi ise aynen dondur."""
    if isinstance(metin, dict):
        return metin.get(dil) or metin["tr"]
    return metin


def cikis_yolu(belgeler, ad, dil):
    """BELGELER/<ad> (tr) ya da BELGELER/en/<ad> (en); klasoru olusturur."""
    kok = Path(belgeler) if dil == "tr" else Path(belgeler) / "en"
    kok.mkdir(parents=True, exist_ok=True)
    return kok / ad


def dil_baglantisi(ad, dil):
    """Sayfanin obur dildeki esine giden <a> etiketi."""
    if dil == "tr":
        return '<a class="dil" href="en/%s" lang="en">English</a>' % ad
    return '<a class="dil" href="../%s" lang="tr">Türkçe</a>' % ad
