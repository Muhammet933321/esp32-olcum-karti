# -*- coding: utf-8 -*-
"""8-kutu.html'in Ingilizcesi (BELGELER/en/8-kutu.html) — CEVIRI BELLEGI.

NEDEN SONRADAN CEVIRI: `kutu.py` binlerce iddia iceren bir denetim ve bir
kismi TURKCE METIN uzerinde desen ariyor ("bana sor" yasagi, "yapistir"
kurali, adim sirasi...). `kutu_veri.py`'nin metinleri ve uretecin akisi
bu yuzden DEGISMIYOR: Turkce sayfa bugunku gibi uretilir, Ingilizce sayfa
o sayfanin metin birimleri bu tablodan cevrilerek elde edilir.

BIRIM: blok ogesi (p, li, td, th, h1-h5, summary, figcaption, button,
option, label, svg <text>/<title>...) icindeki metin + satir ici etiketler
(<b>, <code>, <span>...) — yani bir cumle kendi bicimiyle birlikte cevrilir.
Ek olarak: aria-label / title ozellikleri, betikteki alt adim basliklari
(S), parca bilgi kartlari (BILGI) ve 3B sahne adlari (SAHNE).

ANAHTAR: birimin bosluklari tek bosluga indirilir, metindeki SAYILAR {0},
{1}... yer tutucusuna cevrilir (olcu degisince ceviri kopmasin; Ingilizcede
sira degisebilir, numara ayni sayiyi gosterir). Metinde zaten bulunan
{ad...} yer tutuculari aynen kalir. Iki dilde yer tutucu kumesi AYNI olmali
(denetim). Envanterden gelen kayit (CON029 · <kutu adi>) ANAHTARA girmez:
{S0} olur ve Ingilizce sayfada lang="tr" ile ozgun haliyle kalir (VERI).

PANEL ETIKETLERI: kutunun uzerinde Turkce yazan etiketler («PİL» gibi)
Ingilizce metinde «...» icinde yazilir; sayfada ilk gectigi yerde
"BATTERY 1 (PİL 1)", sonra yalnizca "BATTERY 1" olur (ETIKET tablosu); ozgun
yazi <span lang="tr"> icinde.

Eksik ceviri = Ingilizce sayfa YAZILMAZ ve denetim kirmizi (kutu.py).
"""
from __future__ import annotations

import json
import re
from html import unescape

# ── kutunun uzerindeki fiziksel etiketler ─────────────────────────────────
ETIKET = {
    "AÇ / KAPA": "ON / OFF",
    "PİL": "BATTERY",
    "YÜK": "LOAD",
    "GÜÇ": "POWER",
    "ŞARJ": "CHARGE",
    "SKOP": "SCOPE",
}

# Ingilizce sayfada Turkce harfle KALABILECEK kelimeler — her biri gerekcesiyle.
# Denetim lang="tr" ile isaretli ogeleri (dil baglantisi, panelin ozgun etiketi,
# envanter kaydi) zaten atlar; liste bu kelimelerin NEDEN kaldigini belgeler ve
# isaretsiz kalmalari halinde de yalniz bunlara izin verir.
TR_IZIN = {
    "Türkçe": "dil baglantisinin etiketi: dil secici kendi dilinde yazilir (lang=\"tr\")",
    "AÇ": "kutunun panelindeki ozgun etiket (AÇ / KAPA), ilk geciste parantez icinde",
    "PİL": "kutunun panelindeki ozgun etiket, ilk geciste parantez icinde",
    "YÜK": "kutunun panelindeki ozgun etiket, ilk geciste parantez icinde",
    "GÜÇ": "kutunun panelindeki ozgun etiket, ilk geciste parantez icinde",
    "ŞARJ": "kutunun panelindeki ozgun etiket, ilk geciste parantez icinde",
}

# belge_menu.MENU_EN yoksa (tek dilli serit) kullanilan etiketler — ayni adlar
MENU_EN = {"index.html": "Start", "1-ne-yapabilir.html": "What it can do",
           "2-olcumler.html": "Measurements", "3-pil-testi.html": "Battery test",
           "6-ag.html": "Connecting", "9-pc-uygulamasi.html": "PC app",
           "2-malzemeler.html": "Parts", "4-kurulum.html": "Assembly",
           "7-yerlesim.html": "Layout", "8-kutu.html": "Enclosure",
           "5-muhendislik.html": "Engineering"}

# Satir ici etiketler: birimi BOLMEZ (cumleyle birlikte cevrilir).
SATIR_ICI = {"b", "i", "em", "strong", "code", "span", "a", "sub", "sup", "kbd",
             "small", "u", "abbr", "tspan"}
CEVRILEN_OZELLIK = ("aria-label", "title", "placeholder", "alt")

_HARF = "A-Za-z0-9_ÇĞİÖŞÜçğıöşü"
SAYI = re.compile(rf"(?<![{_HARF}.])\d+(?:\.\d+)?(?![{_HARF}])")
YER = re.compile(r"\{[A-Za-z_][^{}]*\}|\{S?\d+\}")
TR_HARF = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
# envanter kaydi (yerlesim3_belge.Stok._yaz / kutu._stok_metin): "CON029, ... <span class='kucuk'>· KUTU</span>"
STOK_HTML = re.compile(r"[A-Z]{1,4}\d{2,4}(?:, [A-Z]{1,4}\d{2,4})*(?: …)? <span class='kucuk'>· [^<]*</span>")
STOK_DUZ = re.compile(r"^[A-Z]{1,4}\d{2,4}(?:, [A-Z]{1,4}\d{2,4})*(?: …)? · .*$")
# cevrilmesi gereken metin: harf iceriyor ve yalnizca dilden bagimsiz simgeler degil
NOTR = re.compile(r"^(?:[A-Z0-9][A-Z0-9.+\-−/×±_]*|[A-Za-z]+\d[A-Za-z0-9.+\-−/×±_]*|[a-z]|mm|cm|mA|µA|uA|mV|kΩ|Ω|MΩ|V|A|W|mm²|"
                  r"Ø[\d.]+|x|y|z|ms|s|Hz|kHz|MHz|g|°C|°|%|pF|nF|µF|uF|mF|dB|LSB|PCB|GND|COM|"
                  r"Type-C|DC-DC|WebGL)$")


def _bosluk(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ── sozluk ────────────────────────────────────────────────────────────────
def _oku(metin: str) -> tuple[dict, list]:
    """'tr: ...' / 'en: ...' ciftleri. 'en: =' Turkcesiyle ayni (ozel ad, kod)."""
    d, cift, tr = {}, [], None
    for satir in metin.splitlines():
        if not satir.strip() or satir.startswith("#"):
            continue
        if satir.startswith("tr: "):
            tr = _bosluk(satir[4:])
        elif satir.startswith("en: ") and tr is not None:
            en = satir[4:].strip()
            if tr in d:
                cift.append(tr)
            d[tr] = tr if en == "=" else en
            tr = None
        else:
            raise ValueError(f"kutu_en sozlugu: bozuk satir: {satir[:60]!r}")
    return d, cift


# ── anahtar / doldurma ────────────────────────────────────────────────────
def _parcala(s: str):
    """HTML birimini etiket / metin parcalarina ayir."""
    return re.findall(r"<[^>]*>|[^<]+", s)


def anahtar(s: str, html: bool = True) -> tuple[str, list[str], list[str]]:
    """(anahtar, sayilar, stok_parcalari)."""
    stok: list[str] = []

    def _st(m):
        stok.append(m.group(0))
        return "{S%d}" % (len(stok) - 1)

    s = STOK_HTML.sub(_st, s) if html else s
    sayilar: list[str] = []
    out = []
    for p in (_parcala(s) if html else [s]):
        if html and p.startswith("<"):
            out.append(p)
            continue
        if html:
            p = p.replace("&#x27;", "'").replace("&#39;", "'").replace("&quot;", '"')
        parca, i = [], 0
        for m in YER.finditer(p):
            parca.append((p[i:m.start()], False))
            parca.append((m.group(0), True))
            i = m.end()
        parca.append((p[i:], False))
        for t, korunan in parca:
            if korunan:
                out.append(t)
                continue

            def _sy(m):
                sayilar.append(m.group(0))
                return "{%d}" % (len(sayilar) - 1)
            out.append(SAYI.sub(_sy, t))
    return _bosluk("".join(out)), sayilar, stok


def yer_tutucular(s: str) -> list[str]:
    return sorted(YER.findall(s))


# buyuk harfli ama Turkce olan (NOTR'a takilmasin)
TR_BUYUK = {"SKOP", "KAPA", "KAPI", "BOŞ", "DOLU", "YOK", "VAR", "DEĞİL", "KULLANMA", "KALIN",
            "KABLO", "KAYNAK", "SARI", "MAVİ", "YEŞİL", "KIRMIZI", "SİYAH", "TEK", "AYRI"}


def cevrilmeli(k: str) -> bool:
    """Anahtarda dile bagli metin var mi (etiketler ve yer tutucular haric)."""
    duz = YER.sub(" ", re.sub(r"<[^>]*>", " ", unescape(k)))
    for w in re.findall(rf"[{_HARF}µΩ²°Ø%.+\-−/×±]+", duz):
        w = w.strip(".-−/+")
        if not w or not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", w):
            continue
        if TR_HARF.search(w) or w in TR_BUYUK or not NOTR.match(w):
            return True
    return False


class Cevirmen:
    """Bir sayfanin cevirisi: eksikleri ve kullanilan anahtarlari toplar."""

    def __init__(self):
        self.eksik: dict[str, str] = {}       # anahtar -> ornek birim
        self.kullanilan: set[str] = set()
        self.yer_hata: list[str] = []
        self.etiket_gorulen: set[str] = set()

    def _etiket(self, en: str, ilk: bool) -> str:
        def _e(m):
            tr, no = m.group(1), m.group(2) or ""      # «PİL» {0} -> "BATTERY 1 (PİL 1)"
            ad = ETIKET[tr]
            if ilk and tr not in self.etiket_gorulen:
                self.etiket_gorulen.add(tr)
                return f'{ad}{no} (<span lang="tr">{tr}{no}</span>)'
            return ad + no
        return re.sub(r"«([^»]+)»( \{\d+\})?", _e, en)

    def birim(self, s: str, html: bool = True, ilk_etiket: bool = False) -> str:
        """Bir birimi cevir. Bulunamazsa Turkcesi kalir ve eksik sayilir."""
        if not s.strip():
            return s
        k, sayilar, stok = anahtar(s, html)
        if not cevrilmeli(k):
            # yalniz envanter kaydindan olusan hucre: ceviri yok ama VERI isaretlenir
            return STOK_HTML.sub(lambda m: f'<span lang="tr">{m.group(0)}</span>', s) if stok else s
        en = METIN.get(k)
        if en is None:
            self.eksik.setdefault(k, s)
            return s
        self.kullanilan.add(k)
        en = self._etiket(en, ilk_etiket and html)
        bas = s[:len(s) - len(s.lstrip())]
        son = s[len(s.rstrip()):]

        def _dol(m):
            t = m.group(0)
            if t.startswith("{S"):
                return f'<span lang="tr">{stok[int(t[2:-1])]}</span>'
            if re.fullmatch(r"\{\d+\}", t):
                return sayilar[int(t[1:-1])]
            return t
        return bas + YER.sub(_dol, en) + son

    # ── HTML govdesi ──
    def html(self, sayfa: str) -> str:
        jeton = re.compile(r"<!--.*?-->|<(script|style)\b.*?</\1\s*>|<[^>]*>|[^<]+", re.S)
        out, tampon = [], []
        svg_derinlik = [0]

        def bosalt():
            if not tampon:
                return
            s = "".join(tampon)
            tampon.clear()
            out.append(self.birim(s, True, ilk_etiket=svg_derinlik[0] == 0))

        for m in jeton.finditer(sayfa):
            t = m.group(0)
            if not t.startswith("<"):
                tampon.append(t)
                continue
            ad = re.match(r"</?([A-Za-z][\w-]*)", t)
            ad = ad.group(1).lower() if ad else ""
            if ad in SATIR_ICI and not t.startswith("<!"):
                tampon.append(self._ozellik(t))
                continue
            bosalt()
            if ad == "svg":
                svg_derinlik[0] += -1 if t.startswith("</") else 1
            out.append(t if m.group(1) else self._ozellik(t))
        bosalt()
        return "".join(out)

    def _ozellik(self, t: str) -> str:
        def _o(m):
            ic = m.group(3)
            en = self.birim(ic, True)
            if m.group(2) == '"':
                en = en.replace('"', "&quot;")
            else:
                en = en.replace("'", "&#x27;")
            return f"{m.group(1)}={m.group(2)}{en}{m.group(2)}"
        return re.sub(r"\b(%s)=([\"'])(.*?)\2" % "|".join(CEVRILEN_OZELLIK), _o, t)

    # ── JSON verisi ──
    def bilgi(self, b: dict) -> dict:
        out = {}
        for k, v in b.items():
            v = dict(v)
            for a in ("t", "s", "n"):
                if a in v:
                    v[a] = self.birim(v[a], False)
            r = []
            for satir in v.get("r", []):
                satir = list(satir)
                stok_satiri = satir[0] == "Stok"
                satir[0] = self.birim(satir[0], False)
                if not (stok_satiri and STOK_DUZ.match(satir[1])):
                    satir[1] = self.birim(satir[1], False)
                r.append(satir)
            if "r" in v:
                v["r"] = r
            out[k] = v
        return out


def sayfa_cevir(tr: str, nav_en: str) -> tuple[str, Cevirmen]:
    """Turkce sayfadan Ingilizce sayfa. nav_en: Ingilizce gezinme seridi (dil baglantisiyla)."""
    C = Cevirmen()
    s = tr.replace('<html lang="tr">', '<html lang="en">', 1)
    nav = re.search(r'<nav class="ust">.*?</nav>', s, re.S)
    s = s[:nav.start()] + "\x00NAV\x00" + s[nav.end():]
    # betikler ayri: once govde
    betikler = []

    def _bt(m):
        betikler.append(m.group(0))
        return f"\x00B{len(betikler) - 1}\x00"
    s = re.sub(r"<script\b.*?</script>", _bt, s, flags=re.S)
    s = C.html(s)
    s = s.replace("\x00NAV\x00", nav_en)
    for i, b in enumerate(betikler):
        s = s.replace(f"\x00B{i}\x00", betik_cevir(b, C))
    return s, C


def _json_degistir(js: str, bas: str, son: str, f) -> str:
    i = js.index(bas) + len(bas)
    j = js.index(son, i)
    veri = json.loads(js[i:j].replace("<\\/", "</"))
    yeni = json.dumps(f(veri), ensure_ascii=False).replace("</", "<\\/")
    return js[:i] + yeni + js[j:]


def betik_cevir(b: str, C: Cevirmen) -> str:
    if "application/json" in b[:80]:
        return b                      # makine verisi (kutu arayuzu): anahtarlar API, cevrilmez
    if "var S = " not in b:
        return b

    def _s(v):
        for x in v:
            x["b"] = C.birim(x["b"], False)
            x["ab"] = C.birim(x["ab"], False)
        return v

    def _sahne(v):
        for x in v:
            if x.get("ad"):
                x["ad"] = C.birim(x["ad"], False)
        return v
    b = _json_degistir(b, "var S = ", ";\n", _s)
    b = _json_degistir(b, "var BILGI = ", ";\n", C.bilgi)
    b = _json_degistir(b, "var SAHNE = ", ";\n", _sahne)
    for tr, en in JS_CEVIRI:
        if tr not in b:
            C.yer_hata.append(f"JS metni bulunamadi: {tr[:50]!r}")
        b = b.replace(tr, en)
    return b


# ═══════════════════════════════════════════════════════════════════════
#  JS ARAYUZ METINLERI (kutu_3b.JS_IPUCU / JS_3B ve kutu.py'nin adim betigi)
#  (Turkce parca, Ingilizce parca) — Turkce parca betikte BULUNMALI (denetim).
# ═══════════════════════════════════════════════════════════════════════
JS_CEVIRI: list[tuple[str, str]] = [
    # kutu_3b.JS_IPUCU — parca bilgi kartinin alt satiri
    ("'sabitlendi · Esc ya da boş bir yere tıkla: kapat'", "'pinned · Esc or click an empty spot: close'"),
    ("'tıkla / dokun: sabitle · Esc: kapat'", "'click / tap: pin · Esc: close'"),
    # kutu_3b.JS_3B — durum ve bilgi satiri
    ("'3B duraklatıldı…'", "'3D paused…'"),
    ("'3B çizilemedi: '", "'3D could not be drawn: '"),
    ("'Tarayıcı WebGL desteklemiyor — 3B görünüm kapalı.'", "'The browser does not support WebGL — 3D view off.'"),
    ("{kutu: 'taban', duvar: 'dış kat', duvar_ic: 'iç kat', direk: 'direk', delik: 'delik',\n"
     "               panel: 'panel', tasiyici: 'ayak/altlık', parca: 'parça', kablo: 'kablo', kapak: 'kapak'}",
     "{kutu: 'base', duvar: 'outer layer', duvar_ic: 'inner layer', direk: 'post', delik: 'hole',\n"
     "               panel: 'panel', tasiyici: 'foot/spacer', parca: 'part', kablo: 'cable', kapak: 'lid'}"),
    ("'bitmiş kutu: '", "'finished enclosure: '"),
    ("'bu adıma kadar: '", "'up to this step: '"),
    ("' · soluk: bu adımda hazırlanan, henüz takılmamış parçalar'",
     "' · faded: parts prepared in this step, not fitted yet'"),
    ("' · soluk olanlar sırada'", "' · faded ones come next'"),
    ("'henüz parça yok'", "'no parts yet'"),
    ("' — soluk çizgiler yapacağın kutuyu gösteriyor'", "' — the faded lines show the enclosure you will build'"),
    ("' — \"hedefi göster\" ile hedef kutuyu görebilirsin'", "' — with \"show target\" you can see the target enclosure'"),
    ("' · bu adımın parçası duvarın arkasında: \"yakın olanlar saydam\" seç ya da üstten bak'",
     "' · this step\\'s part is behind a wall: choose \"near ones transparent\" or look from the top'"),
    ("'bu adımda hazırlanıyor — kutuya henüz takılmadı'", "'prepared in this step — not fitted in the enclosure yet'"),
    ("'⏳ henüz yok — ' + S[bl.gor].no + ' adımında takılır'", "'⏳ not yet — fitted in step ' + S[bl.gor].no"),
    ("'★ bu adımın parçası'", "'★ part of this step'"),
    ("' · parça '", "' · part '"),
    # VERIYE BAGLI KOD: N/P gezinmesi ic kat deliklerini SAHNE adinin "(iç)" sonekinden
    # taniyor — ad "(inner)" olarak cevrildigi icin desen de cevrilmeli (yoksa EN sayfada
    # ic kat delikleri N/P listesine girer). Siralama da Ingilizce adlara gore.
    ("!/\\(iç\\)$/.test(k.bl.ad)", "!/\\(inner\\)$/.test(k.bl.ad)"),
    ("a.ad.localeCompare(b.ad, 'tr')", "a.ad.localeCompare(b.ad, 'en')"),
    # kutu.py — alt adim gorunumu
    ("'Adım ' + s.a + ' — '", "'Step ' + s.a + ' — '"),
    ("' · yapılan '", "' · done '"),
]

# ═══════════════════════════════════════════════════════════════════════
#  CEVIRI TABLOSU — "tr: <anahtar>" / "en: <ceviri>" ("en: =" ayni kalir)
# ═══════════════════════════════════════════════════════════════════════
SOZLUK = r"""
tr: Kutu ve panel — Ölçüm Kartı
en: Enclosure and panel — Measurement Board
tr: Kutu ve panel
en: Enclosure and panel
tr: Çubuktan kutu, panel delikleri, şönt ve Q1, jaklar, kablolar — alt adım alt adım, her birinin çizimi ve 3B görünümüyle. Sonunda hangi ölçümü nereden yapacağın yazıyor.
en: An enclosure from sticks, panel holes, shunt and Q1, jacks, cables — sub-step by sub-step, each with its drawing and 3D view. At the end: which measurement you take from where.
tr: Bu belge ne — kurallar
en: What this document is — rules
tr: Kartlar bitti. Bundan sonrası: <b>çubuktan kutu</b>, panel delikleri, şönt ve Q1, jaklar, kablolar, testler.
en: The boards are done. From here on: <b>an enclosure from sticks</b>, panel holes, shunt and Q1, jacks, cables, tests.
tr: <b>Parça bilgisi:</b> çizimlerde ve 3B görünümde bir parçanın <b>üzerine gel</b> (telefonda dokun): adı, ölçüsü, çubuksa <b>uzunluğu</b> ve kesim listesindeki satırı, hangi adımda takıldığı, stoktaki yeri çıkar. Tıkla / dokun: kart sabit kalır. Klavyeyle: çizimlerde <b>Tab</b> parçadan parçaya geçer, 3B'de <b>N / P</b> sonraki / önceki parça, <b>Esc</b> kapatır.
en: <b>Part info:</b> in the drawings and the 3D view, <b>hover over</b> a part (tap on a phone): its name, size, for a stick its <b>length</b> and its row in the cut list, the step it is fitted in, and its place in stock. Click / tap: the card stays put. With the keyboard: in drawings <b>Tab</b> moves from part to part, in 3D <b>N / P</b> next / previous part, <b>Esc</b> closes.
tr: Kutu <b>dil basacağı (tahta çubuk)</b> ({0} × {1} × {2} mm) çubuklardan. İç ölçü <b>{3} × {4} × {5} mm</b>, dış {6} × {7} × {8}.
en: The enclosure is made of <b>tongue depressors (wooden sticks)</b> ({0} × {1} × {2} mm). Inside <b>{3} × {4} × {5} mm</b>, outside {6} × {7} × {8}.
tr: <b>Sağlamlık:</b> duvarlar iki kat (dışta {0} yatay sıra, içte dikey çubuklar; {1} mm), dört köşede {2} × {3} mm direk; kapak yan duvarlardan M3x12 cıvata + somunla tak-çıkar; kartlar gömme somunlu ayaklara vidalı. Taban ve kapak parçaları düz bölümden: yuvarlak uç hiçbir duvarın altına gelmiyor. Delikler duvar dikilmeden, parça düz zemindeyken.
en: <b>Strength:</b> the walls are two layers (outside {0} horizontal rows, inside vertical sticks; {1} mm), a {2} × {3} mm post in each of the four corners; the lid comes off through the side walls with M3x12 bolts + nuts; the boards are screwed to feet with embedded nuts. Base and lid pieces come from the flat section: no rounded end ends up under a wall. Holes are made before the walls go up, while the piece lies on a flat surface.
tr: <b>Kural:</b> değerli parçalar — kartlar (A, B), ESP32, şönt, Q1 — yapıştırılmaz (vida, ayak, konnektör); kutunun kendi parçaları (çubuk, ayak, altlık) yapıştırılır. <b>Sıcak silikonla yapıştırılan duvar parçaları</b> (senin kararın): YUVA1 (sıcak silikon), YUVA2 (sıcak silikon), MT1 (sıcak silikon), MT2 (sıcak silikon), IZ (sıcak silikon), CB (sıcak silikon), KL (sıcak silikon), F0 (sıcak silikon), F1P (sıcak silikon), F2 (sıcak silikon) — izopropil alkol ya da ısı tabancasıyla sökülür.
en: <b>Rule:</b> valuable parts — the boards (A, B), ESP32, shunt, Q1 — are never glued (screws, feet, connectors); the enclosure's own parts (sticks, feet, spacers) are glued. <b>Wall parts glued with hot glue</b> (your decision): YUVA1 (hot glue), YUVA2 (hot glue), MT1 (hot glue), MT2 (hot glue), IZ (hot glue), CB (hot glue), KL (hot glue), F0 (hot glue), F1P (hot glue), F2 (hot glue) — they come off with isopropyl alcohol or a heat gun.
tr: <b>Kullanım sınırı:</b> yalnız pil / DC-DC beslemeli, toprağa göre yüzen devreler. HV ölçerken USB takılı olmaz.
en: <b>Limit of use:</b> only battery / DC-DC powered circuits that float with respect to earth. No USB plugged in while measuring HV.
tr: Aşağıda <b>ileri / geri</b> ile tek tek ilerle; 3B görünüm adım şeridinin altında (sürükle: döndür, Ctrl+tekerlek: yakınlaştır). Tezgahta telefondan: <code>python uretim/belge_sun.py</code>.
en: Below, go one at a time with <b>next / back</b>; the 3D view is under the step bar (drag: rotate, Ctrl+wheel: zoom). From a phone at the bench: <code>python uretim/belge_sun.py</code>.
tr: Çubuk kullanan her adımda <b>"Bu adımda gereken çubuk parçaları"</b> tablosu var: hangi uzunluktan kaç tane, çubuk üstünde çizili. {0} ve {1} toplu kesim listeleri; oradaki "hangi adımda" sütunu aynı bilgiyi verir.
en: Every step that uses sticks has a <b>"Stick pieces needed in this step"</b> table: how many of which length, drawn on the stick. {0} and {1} are the combined cut lists; their "which step" column gives the same information.
tr: Hangi yapıştırıcı nerede
en: Which glue goes where
tr: İş
en: Job
tr: Yapıştırıcı
en: Glue
tr: Nasıl
en: How
tr: Lamine (üst üste) parçalar: ayak blokları, direkler, köşebent, ankraj, TP4056 rafı blokları
en: Laminated (stacked) parts: foot blocks, posts, corner bracket, anchor, TP4056 shelf blocks
tr: <b>Japon (CA, sıvı)</b>
en: <b>CA glue (super glue, liquid)</b>
tr: Yüze ince çizgi, {0} s bastır; kelepçe gerekmez. Gömme somunun dişine damlatma — somunu kuru geçir.
en: A thin line on the face, press {0} s; no clamp needed. Do not drip it into the thread of the embedded nut — fit the nut dry.
tr: Taban / kapak sıraları (uç uca ve yan yana)
en: Base / lid rows (end to end and side by side)
tr: <b>Maskeleme bandı + japon</b>
en: <b>Masking tape + CA glue</b>
tr: Parçaları düz zeminde dizip üstünden maskeleme bandıyla tut, derzlere ince japon süz (altına kapton/pişirme kâğıdı: masaya yapışır).
en: Lay the pieces out on a flat surface, hold them from above with masking tape and run thin CA glue into the joints (put Kapton / baking paper underneath: it sticks to the table).
tr: Raylar (taban altı, kapak altı)
en: Rails (under the base, under the lid)
tr: <b>Sıcak silikon</b>
en: <b>Hot glue</b>
tr: Ray boyunca sürekli, ince bir çizgi; {0} s içinde bastır. Yerinde oynatma payı veren tek yapıştırıcı.
en: A continuous thin bead along the rail; press within {0} s. The only glue that gives you time to adjust the position.
tr: Dış kat sıraları (tabana ve birbirine)
en: Outer layer rows (to the base and to each other)
tr: <b>Japon + içeriden sıcak silikon</b>
en: <b>CA glue + hot glue from inside</b>
tr: Uçları ve ortayı japonla tuttur (hizala, {0} s bastır), sonra iç köşeye sıcak silikonla fileto çek: japon hizayı, silikon dayanımı verir.
en: Tack the ends and the middle with CA glue (align, press {0} s), then run a hot-glue fillet into the inside corner: the CA gives the alignment, the hot glue the strength.
tr: İç kat dikey çubuklar
en: Inner layer vertical sticks
tr: <b>Japon (üst-orta-alt üç çizgi)</b>
en: <b>CA glue (three lines: top, middle, bottom)</b>
tr: Sıcak silikon kalınlık yapar (iç kat {0} mm olmalı, delikler hizasız kalır); japon ince kalır. Çubuğu tek seferde doğru yere koy — kayma payı yok.
en: Hot glue adds thickness (the inner layer must be {0} mm, otherwise the holes no longer line up); CA stays thin. Put the stick in the right place the first time — there is no room to slide it.
tr: Şönt / ESP32 altlıkları (tabana)
en: Shunt / ESP32 spacers (to the base)
tr: Kutu parçaları; sökmek gerekirse maket bıçağıyla altından kesilir.
en: Enclosure parts; if they ever need to come off, cut underneath with a utility knife.
tr: ESP32 kızağı (yan raylar, omuz takozları — altlığın üstüne)
en: ESP32 cradle (side rails, shoulder blocks — on top of the spacer)
tr: Devkit yerinde ve kenarına bir kat kâğıt sarılıyken parçayı daya, damla japon, {0} s bastır. Devkit'e japon değdirme; kuruyunca kâğıdı çek.
en: With the devkit in place and a layer of paper wrapped around its edge, press the piece against it, a drop of CA glue, press {0} s. Do not let CA glue touch the devkit; pull the paper out once it has cured.
tr: {0} yuvaları, modüller (MT1, MT2, B0505S), {1} µF, KL, sigorta şeritleri (arka duvarın iç yüzü)
en: {0} holders, modules (MT1, MT2, B0505S), {1} µF, KL, fuse strips (inner face of the back wall)
tr: Yuvanın tabanına boydan boya iki şerit, duvara {0} s bastır; iç kat çubuklarının arasına denk gelen yerde silikonu kalın bırak ({1} mm boşluğu doldurur). Japon DEĞİL: bazı yuva plastiklerini (PP) tutmaz ve ısıda gevrekleşir. Sökmek: ısı tabancası ya da izopropil alkol + maket bıçağı.
en: Two beads along the full length of the holder's base, press against the wall {0} s; where it lands between the inner-layer sticks, leave the glue thick (it fills the {1} mm gap). NOT CA glue: it does not bond some holder plastics (PP) and turns brittle with heat. To remove: heat gun or isopropyl alcohol + utility knife.
tr: Silikon mastik (tüp, kürlenen)
en: Silicone sealant (tube, curing)
tr: Yapısal değil, {0} saat kürlenir, üstüne hiçbir şey tutmaz. Yalnız ileride su/toz sızdırmazlık istersen jak somunlarının çevresine.
en: Not structural, cures in {0} hours, nothing sticks on top of it. Only around the jack nuts if you later want water/dust sealing.
tr: Şöntün kendisi ve Kelvin lehimleri
en: The shunt itself and the Kelvin solder joints
tr: <b>Yapıştırıcı yok — makaron + kablo bağı</b>
en: <b>No glue — heat-shrink + cable tie</b>
tr: Şönt {0} A'de ~{1} °C ısınır, kapalı kutuda {2} °C'yi geçer: sıcak silikon ~{3} °C'de yumuşayıp akar, üstelik şöntün soğumasını keser ({4} A sınırı açık havada soğumaya göre). {5} mΩ'a geçerken bu lehimler sökülür. Gerilmeyi kablo bağı alır ({6}: burgulu çift şönt altlığına); istersen lehimin üstüne makaron — bacağın klemense girecek alt ucu açık kalsın.
en: At {0} A the shunt heats up by ~{1} °C and in a closed enclosure it goes past {2} °C: hot glue softens and flows at ~{3} °C, and it also stops the shunt from cooling (the {4} A limit assumes cooling in open air). These joints are desoldered when changing to {5} mΩ. The strain is taken by a cable tie ({6}: the twisted pair to the shunt spacer); if you like, heat-shrink over the solder — leave the lower end of the leg that goes into the terminal block bare.
tr: Soğutucunun kendisine değen yerler (Q1'in tabı, kapı teli, mika pul)
en: Places touching the heatsink itself (Q1's tab, the gate wire, the mica washer)
tr: <b>Kablo bağı, yapıştırıcı yok</b>
en: <b>Cable tie, no glue</b>
tr: Sıcak silikon soğutucunun yüzeyinde yumuşar; CA ısıda gevrekleşir. ⚠ Köşebendin TABANA yapıştırılması bu yasağın DIŞINDA ({0}): o derz soğutucudan {1} mm ahşap ötede, oraya ulaşan ısı {2} K'den az.
en: Hot glue softens on the heatsink's surface; CA turns brittle with heat. ⚠ Gluing the corner bracket to the BASE is OUTSIDE this ban ({0}): that joint is {1} mm of wood away from the heatsink, the heat that reaches it is under {2} K.
tr: Hangi deliğe ne geliyor — ve neden
en: Which hole gets what — and why
tr: Çap / yuva
en: Diameter / slot
tr: Gelen parça · stok
en: Part fitted · stock
tr: Neden bu parça / bu delik
en: Why this part / this hole
tr: <b>PİL {0}</b>
en: <b>«PİL» {0}</b>
tr: <span class='kucuk'>ön · x {0} · z {1}</span>
en: <span class='kucuk'>front · x {0} · z {1}</span>
tr: 4mm Born Jak Şeffaf Mavi (Büyük Boy)
en: 4 mm banana jack, clear blue (large)
tr: Pil deşarj yolu (Q1 savağı, {0} A'e kadar): büyük boy jak. MAVİ, YÜK'ten ayırt edilsin diye — karıştırılırsa pil kesmesi çalışmaz.
en: Battery discharge path (Q1 drain, up to {0} A): large jack. BLUE so it can be told apart from «YÜK» — mix them up and the battery cut-off does not work.
tr: Pil eksisi = şönt altı = COM ile aynı düğüm; mavi çiftin ikinci ucu.
en: Battery negative = bottom of the shunt = same node as COM; the second terminal of the blue pair.
tr: <b>YÜK {0}</b>
en: <b>«YÜK» {0}</b>
tr: 4mm Born Jak Şeffaf Yeşil (Büyük Boy)
en: 4 mm banana jack, clear green (large)
tr: Yük akımının GİRDİĞİ uç ({0} A'e kadar): büyük boy jak {1} A taşır, küçük vidalı jak taşımaz. YEŞİL (B60): bütün jaklar tek model (büyük şeffaf) ve stoktaki siyahlar COM ile CAL'e gitti; YÜK çifti tek renk kalsın diye yeşil ×{2}. Kart akımı hep devrenin eksi/dönüş tarafından ölçer. Bariyer klemens (CON012) PCB tipiydi, panele vidalanamadı.
en: The terminal where the load current ENTERS (up to {0} A): the large jack carries {1} A, the small screw jack does not. GREEN (B60): all jacks are a single model (large clear) and the black ones in stock went to COM and CAL; green ×{2} so the «YÜK» pair stays one colour. The board always measures current on the negative/return side of the circuit. The barrier terminal block (CON012) was a PCB type and could not be screwed to the panel.
tr: Yük akımının ÇIKTIĞI uç; şöntün alt bacağı = kart GND = COM. İki jak olması şart: akım şöntten SERİ geçmeli.
en: The terminal where the load current LEAVES; bottom leg of the shunt = board GND = COM. Two jacks are a must: the current has to pass through the shunt in SERIES.
tr: 4mm Born Jak Şeffaf Siyah (Büyük Boy)
en: 4 mm banana jack, clear black (large)
tr: TEK COM: V, HV ve SKOP'un ortak eksisi; içeride YÜK {0} / PİL {1} ile aynı düğüm. Tek jak olması bilerek — ikinci bir COM olsaydı şönt baypas edilebilirdi.
en: ONE COM: the common negative of V, HV and «SKOP»; inside it is the same node as «YÜK» {0} / «PİL» {1}. A single jack on purpose — a second COM would let the shunt be bypassed.
tr: 4mm Born Jak Şeffaf Kırmızı (Büyük Boy)
en: 4 mm banana jack, clear red (large)
tr: Gerilim girişi: yüksek empedans ({0} kΩ, akım yok) — akım için değil GÖRÜNÜŞ için büyük: B60'tan beri panelde tek jak modeli var. KIRMIZI = ölçüm artısı.
en: Voltage input: high impedance ({0} kΩ, no current) — large for LOOKS, not for current: since B60 the panel has a single jack model. RED = measurement positive.
tr: 4mm Born Jak Şeffaf Sarı (Büyük Boy)
en: 4 mm banana jack, clear yellow (large)
tr: {0} V'a kadar giriş: büyük boy jakın gövdesi/yalıtımı daha uzun, sağ kenarda ve öbür metalden ≥ {1} mm kaçak yolu (IEC {2} takviyeli). Kutudaki TEK SARI jak (B60): bütün jaklar aynı model olunca 'tek büyük kırmızı' ipucu kalktı, renk onun yerini aldı. Yanlışlıkla V'ye takılan {3} V R4'ü zamanla yakar (B15/A1) — HV'nin rengini başka hiçbir jak kullanmaz (denetimli). İç ucu makaronla.
en: Input up to {0} V: the large jack has a longer body/insulation, it sits at the right edge with ≥ {1} mm creepage to other metal (IEC {2} reinforced). The ONLY YELLOW jack on the enclosure (B60): once all jacks were the same model the 'one big red' cue was gone, colour took its place. {3} V plugged into V by mistake slowly burns R4 (B15/A1) — no other jack uses HV's colour (audited). Inner end heat-shrunk.
tr: <b>AÇ / KAPA</b>
en: <b>«AÇ / KAPA»</b>
tr: Kutunun tek anahtarı: paketi {0} V yükselticiye bağlar. Paket tarafında olmalı — MT3608 boşta {1}–{2} mA çekip paketi haftalarda bitirir. KTS102 tek kutup yeter: eksi hat ortak, kesilmesi gerekmiyor.
en: The enclosure's only switch: connects the pack to the {0} V boost converter. It must sit on the pack side — an idle MT3608 draws {1}–{2} mA and empties the pack in weeks. A single-pole KTS102 is enough: the negative line is common and does not need to be broken.
tr: <b>GÜÇ</b>
en: <b>«GÜÇ»</b>
tr: 5mm LED Yeşil (şeffaf)
en: 5 mm LED, green (clear)
tr: Kartın enerjili olup olmadığının TEK görsel cevabı. +{0} rayında olmak zorunda: akım GND'ye GİRER, yani {1}'nin çekmek üzere tasarlandığı yön. GND ile −{2} arasına konsaydı regülatörden akım VERMESİ istenirdi, 79xx veremez. ESP32'nin sürdüğü bir gösterge, ESP32 USB'deyken analog kapalıysa 'hazır' diye yalan söylerdi — bu yüzden pasif.
en: The ONLY visual answer to whether the board is powered. It has to be on the +{0} rail: the current flows INTO GND, i.e. the direction {1} is designed to sink. Placed between GND and −{2} it would ask the regulator to SOURCE current, which a 79xx cannot do. An indicator driven by the ESP32 would lie 'ready' while the ESP32 is on USB and the analog side is off — hence passive.
tr: B60 (kullanıcı kararı, alım yok): CAL SİYAH büyük jak — stokta her renkten {0} var, sarı HV'ye ayrıldı. COM ile karışabilir ama ZARARSIZ: CAL'e takılan COM kablosu ölçümü çalıştırmaz, {1} kΩ bir şeyi yakmaz. B59'da sağ üste, SKOP'un yanına ve V'nin üstüne çıktı: CAL → SKOP patch kablosu kısa. Kullanıcının görselinde HV'nin tam üstündeydi — bir HV ucu ({2} V) yanlışlıkla CAL'e girse {3} kΩ'dan ~{4} mA akar, GPIO'yu ve iki ADS'yi öldürür; SKOP ile yer değiştirdi. Komşuları V ve SKOP, en yakını {5} mm.
en: B60 (user decision, nothing to buy): CAL is a BLACK large jack — stock has {0} of each colour, yellow is reserved for HV. It can be confused with COM but it is HARMLESS: a COM lead plugged into CAL does not start a measurement, {1} kΩ burns nothing. In B59 it moved to the top right, next to «SKOP» and above V: the CAL → «SKOP» patch lead is short. In the user's sketch it sat right above HV — an HV probe ({2} V) slipping into CAL would push ~{4} mA through {3} kΩ and kill the GPIO and both ADS chips; it swapped places with «SKOP». Its neighbours are V and «SKOP», the closest {5} mm away.
tr: Osiloskop girişi: {0} kΩ, akım yok → kırmızı; B60'tan beri öbür jaklarla aynı model (büyük şeffaf).
en: Oscilloscope input: {0} kΩ, no current → red; since B60 the same model as the other jacks (large clear).
tr: <b>ŞARJ</b>
en: <b>«ŞARJ»</b>
tr: <span class='kucuk'>arka · x {0} · z {1}</span>
en: <span class='kucuk'>back · x {0} · z {1}</span>
tr: {0} × {1} oval
en: {0} × {1} oval
tr: (kendi parçası yok)
en: (no part of its own)
tr: Tek şarj girişi (B58): analog {0} V artık yalıtılmış B0505S'ten geldiği için paketin eksisi −{1} rayına değmiyor, tek USB toprağı hiçbir şeyi kısa etmiyor. Eskiden iki hücre ayrı topraklıydı ve iki Type-C gerekiyordu.
en: Single charging input (B58): the analog {0} V now comes from the isolated B0505S, so the pack negative does not touch the −{1} rail and a single USB ground shorts nothing. Previously the two cells had separate grounds and needed two Type-C ports.
tr: Kendi parçası yok: ESP32 devkit'in COM yazan Type-C soketi duvarın {0} mm içinde; fiş bu yuvadan geçer. Oval {1} × {2}: Type-C fişin plastik gövdesi ~{3} × {4}.
en: No part of its own: the ESP32 devkit's Type-C socket marked COM sits {0} mm inside the wall; the plug goes through this slot. Oval {1} × {2}: the plastic body of a Type-C plug is ~{3} × {4}.
tr: Alt giriş: gaz tahliyesinde üst deliklerin hava alabilmesi için karşı açıklık şart, yoksa basınç yolu tek delikte tıkanır. ⚠ ISIL gerekçe DEĞİL — baca akışı hesaplandı, ΔT {0} K'de {1} L/dk = {2} mW, duvarların attığı ısının %{3}'i. x {4} iç kat çubuğunun ({5}–{6}) ortası.
en: Lower inlet: when gas is vented the upper holes need an opposite opening to draw air, otherwise the pressure path chokes at a single hole. ⚠ NOT a THERMAL reason — the chimney flow was calculated: at ΔT {0} K, {1} L/min = {2} mW, {3}% of the heat the walls shed. Centre of the inner-layer stick at x {4} ({5}–{6}).
tr: İkinci giriş, ilkinin karşı ucunda: tek delik tıkanırsa (toz, kablo) alt açıklık kalsın. Dört delik iki ayna çifti oluşturuyor, akış çaprazlama. x {0} iç kat çubuğunun ({1}–{2}) ortası.
en: Second inlet, at the opposite end from the first: if one hole is blocked (dust, a cable) a lower opening remains. The four holes form two mirrored pairs, the flow runs diagonally. Centre of the inner-layer stick at x {0} ({1}–{2}).
tr: Li-ion termal kaçağında gaz basınç yapmadan çıksın diye; kapak {0} cıvatayla sıkılı ve kutu {1} L. Üst sıra: gaz yukarı çıkar. x {2} iç kat çubuğunun ({3}–{4}) içinde (ortası x {5}).
en: So that gas from a Li-ion thermal runaway gets out without building pressure; the lid is held by {0} bolts and the enclosure is {1} L. Top row: gas rises. Inside the inner-layer stick at x {2} ({3}–{4}) (its centre at x {5}).
tr: İkinci çıkış: tek delik tıkanırsa (toz, kablo) basınç yolu kapanmasın. HV1'in karşı ucunda — aynı engel ikisini birden kapatamaz. x {0} iç kat çubuğunun ({1}–{2}) içinde (ortası x {3}).
en: Second outlet: if one hole is blocked (dust, a cable) the pressure path must not close. At the opposite end from HV1 — the same obstacle cannot block both. Inside the inner-layer stick at x {0} ({1}–{2}) (its centre at x {3}).
tr: <b>Kapak cıvataları ×{0}</b>
en: <b>Lid bolts ×{0}</b>
tr: M3x12 + somun + pul (MEK034/{0})
en: M3x12 + nut + washer (MEK034/{0})
tr: Yan duvarlardan (y {0} / {1}, z {2}) kapak rayına; tahtaya diş açılmaz, somun tutar → kapak tak-çıkar. RAY DA DELİNİR ({3}): duvardaki delik kılavuz olur, aynı Ø{4}.
en: Through the side walls (y {0} / {1}, z {2}) into the lid rail; no thread is cut in the wood, the nut holds → the lid comes on and off. THE RAIL IS DRILLED TOO ({3}): the hole in the wall serves as a guide, same Ø{4}.
tr: <b>Kart ayak blokları ×{0} (A ×{1}, B ×{2})</b>
en: <b>Board foot blocks ×{0} (A ×{1}, B ×{2})</b>
tr: Ø{0} ({1}. kat) + Ø{2} ({3}.–{4}. kat) + Ø{5} ({6}. kat)
en: Ø{0} (layer {1}) + Ø{2} (layers {3}–{4}) + Ø{5} (layer {6})
tr: M3x10 vida + gömme M3 somun
en: M3x10 screw + embedded M3 nut
tr: Somun {0}.–{1}. katın Ø{2} cebinde, dış yüzüne bir damla japon: kartlar vidayla sökülebilir, tahtaya diş yok. Cebin altındaki {3}. kat da Ø{4} delik — vidanın ucu dayanmasın; &lt;b&gt;altındaki katlar delinmez&lt;/b&gt; (kart A bloğu {5} kat, kart B bloğu {6} kat). Merkezler kartın {7}×{8} boş köşe deliklerinden.
en: The nut sits in the Ø{2} pocket of layers {0}–{1}, a drop of CA glue on its outer face: the boards can be unscrewed, no thread in the wood. Layer {3} below the pocket also gets a Ø{4} hole — so the screw tip does not bottom out; &lt;b&gt;the layers below are not drilled&lt;/b&gt; (board A block {5} layers, board B block {6} layers). Centres from the board's {7}×{8} empty corner holes.
tr: <b>Duvara asılı parçalar — EK DELİK YOK (TP1)</b>
en: <b>Parts hung on the wall — NO EXTRA HOLE (TP1)</b>
tr: kablo bağı (SRF012)
en: cable tie (SRF012)
tr: CB, F0, F1P, F2, IZ, KL, MT1, MT2, YUVA1, YUVA2 duvara sıcak silikonla yapıştırılı (B57b yuvalar, B73 modüller ve küçük parçalar — kullanıcı kararı). TP1 modülünde montaj deliği YOK: ahşap tutucuya kablo bağıyla tutuluyor. Duvar parçaları için duvara hiç delik açılmıyor.
en: CB, F0, F1P, F2, IZ, KL, MT1, MT2, YUVA1, YUVA2 are hot-glued to the wall (B57b holders, B73 modules and small parts — user decision). The TP1 module has NO mounting hole: it is held to a wooden holder with a cable tie. No holes at all are made in the wall for wall parts.
tr: Konumlar iç koordinat (önden bakınca soldan); {0}/{1}'deki parça-parça tablo aynı delikleri parçanın kendi ucundan ölçer. Bütün jaklar aynı model (büyük şeffaf, B60). Renk: kırmızı = V/SKOP, siyah = COM ve CAL, SARI = yalnız HV, mavi = PİL, yeşil = YÜK.
en: Positions are inner coordinates (seen from the front, from the left); the part-by-part table in {0}/{1} measures the same holes from the part's own end. All jacks are the same model (large clear, B60). Colours: red = V/«SKOP», black = COM and CAL, YELLOW = HV only, blue = «PİL», green = «YÜK».
tr: Delikleri nasıl açarım (matkapsız)
en: How do I make the holes (without a drill)
tr: Aşama
en: Stage
tr: <b>İşaretle</b>
en: <b>Mark</b>
tr: Cetvelle parçanın sol ucundan x'i, alt kenarından z'yi ölç, iki çizgi çek; kesişme deliğin MERKEZİ. Pergel yoksa çapı/{0}'yi işaretleyip küçük bir daire çiz (Ø{1} için {2} mm).
en: With a ruler measure x from the left end of the piece and z from its bottom edge, draw two lines; where they cross is the CENTRE of the hole. Without compasses, mark the diameter/{0} and draw a small circle ({2} mm for Ø{1}).
tr: <b>Kılavuz</b>
en: <b>Pilot</b>
tr: Merkeze biz / kalın iğne / çivi ucuyla hafifçe bastırıp döndürerek {0}–{1} mm çukur aç. ÇAKMA yok — çakılan çivi {2} mm çubuğu lif boyunca yarar.
en: Press an awl / thick needle / nail point into the centre gently and twist to make a {0}–{1} mm dimple. NO HAMMERING — a driven nail splits a {2} mm stick along the grain.
tr: <b>Delme (havya)</b>
en: <b>Piercing (soldering iron)</b>
tr: Havyanın eski konik ucunu ({0} °C) merkeze dik bastır; {1}–{2} s'de {3} mm tahtayı geçer, ~{4} mm yanık delik açar. Altına fire çubuk koy, pencereyi aç (duman). Yarmaz, en güvenli matkapsız yol. Yanık kenar jakın flanşı/somunu altında kalır.
en: Press an old conical tip of the soldering iron ({0} °C) square onto the centre; it gets through {3} mm of wood in {1}–{2} s and burns a ~{4} mm hole. Put a scrap stick underneath, open the window (smoke). It does not split the wood — the safest way without a drill. The burnt edge ends up under the jack's flange/nut.
tr: <b>Delme (matkap ucu elle)</b>
en: <b>Drilling (drill bit by hand)</b>
tr: Matkap ucun varsa {0} mm'lik ucu penseyle tutup elle döndürerek de geçer ({1} mm tahta, ~{2} dk). El matkabı / pin vise ({3}–{4} ₺) M3 deliklerini dakikaya indirir — Ø{5}–{6} için yine büyütme gerekir.
en: If you have drill bits, a {0} mm bit held in pliers and turned by hand also gets through ({1} mm of wood, ~{2} min). A hand drill / pin vise ({3}–{4} ₺) brings the M3 holes down to a minute — for Ø{5}–{6} you still need to enlarge.
tr: <b>Büyütme</b>
en: <b>Enlarging</b>
tr: {0} mm'lik deliği maket bıçağının ucunu döndürerek ya da kalem/marker üstüne sarılı {1}'lik zımparayla çapa getir: &lt;b&gt;Ø{2} için bıçak ucu ya da tornavida sapına sarılı zımpara&lt;/b&gt; (havyanın açtığı ~{3} mm'den yalnız {4} mm büyük), Ø{5} için kalem, Ø{6} için kalın marker. Sık sık jakla dene: gövde sürtünerek geçmeli, boşluk kalmamalı (somun sıkınca jak dönmez). &lt;b&gt;Havalandırma delikleri (Ø{7}) istisna:&lt;/b&gt; orada sıkı geçme aranmaz, delik açık olsun yeter — LED ise sıkı geçmeli, yoksa öne düşer.
en: Bring the {0} mm hole up to size by twisting the tip of a utility knife or with {1} sandpaper wrapped around a pen/marker: &lt;b&gt;for Ø{2} a knife tip or sandpaper wrapped around a screwdriver shaft&lt;/b&gt; (only {4} mm bigger than the ~{3} mm the iron makes), for Ø{5} a pen, for Ø{6} a thick marker. Test often with the jack: the body should go through with friction, with no play (then the jack does not turn when the nut is tightened). &lt;b&gt;Ventilation holes (Ø{7}) are the exception:&lt;/b&gt; no tight fit needed there, the hole just has to be open — the LED, however, must fit tightly or it falls out the front.
tr: <b>En büyük delik (Ø{0}) — en dar et</b>
en: <b>The largest hole (Ø{0}) — the thinnest wood</b>
tr: Paneldeki en büyük yuvarlak delik Ø{0}: {1} mm çubukta her yanda &lt;b&gt;{2} mm&lt;/b&gt; et kalır — en kolay çatlayan yer. Büyütmeyi kalın markera sarılı zımparayla yap, sık sık jakla dene, altına fire çubuk koy. İleride kalem/marker büyütmesinin yetmediği daha büyük bir delik gerekirse: çemberi çiz, &lt;b&gt;çember ÜSTÜNE&lt;/b&gt; havyayla {3}–{4} küçük delik aç, göbeği bıçakla it, eğeyle çizgiye getir.
en: The largest round hole on the panel is Ø{0}: on a {1} mm stick that leaves &lt;b&gt;{2} mm&lt;/b&gt; of wood on each side — the easiest place to crack. Enlarge with sandpaper wrapped around a thick marker, test often with the jack, put a scrap stick underneath. If you later need a bigger hole than a pen/marker can enlarge: draw the circle, burn {3}–{4} small holes &lt;b&gt;ON the circle&lt;/b&gt; with the iron, push the centre out with a knife, file up to the line.
tr: <b>Oval yuva ({0} × {1})</b>
en: <b>Oval slot ({0} × {1})</b>
tr: Merkezden ±{0} mm'de iki Ø{1} daire çiz (merkezler {2} mm aralıklı), ikisini de havya + büyütme ile aç, arasını maket bıçağıyla düz kes, köşeleri yuvarla. USB-C / Type-C fişin metal gövdesi {3} × {4}, plastik kılıfı ~{5} × {6}: {7} × {8} rahat geçirir.
en: Draw two Ø{1} circles at ±{0} mm from the centre (centres {2} mm apart), open both with the iron + enlarging, cut straight between them with a utility knife, round off the corners. The metal shell of a USB-C / Type-C plug is {3} × {4}, its plastic overmould ~{5} × {6}: {7} × {8} lets it through easily.
tr: <b>M3 delikleri (Ø{0})</b>
en: <b>M3 holes (Ø{0})</b>
tr: Havya ucuyla tek geçiş yeter; cıvata sürtünerek geçmeli. Ayak ve kapak bloğunun {0}.–{1}. katındaki Ø{2} somun cebi: havya + büyütme, somunu deneyerek. &lt;b&gt;Cebin hemen altındaki kat&lt;/b&gt; da Ø{3} delinir (vidanın ucu dayanmasın); daha alttaki katlar delinmez.
en: One pass with the iron tip is enough; the bolt should go through with friction. The Ø{2} nut pocket in layers {0}–{1} of the foot and lid blocks: iron + enlarging, testing with the nut. &lt;b&gt;The layer right below the pocket&lt;/b&gt; also gets a Ø{3} hole (so the screw tip does not bottom out); the layers further down are not drilled.
tr: <b>Delikli plaket (FR4) — Ø{0}</b>
en: <b>Perfboard (FR4) — Ø{0}</b>
tr: ⚠ &lt;b&gt;Havya KULLANMA:&lt;/b&gt; cam elyaf erimez, reçine karbonlaşır ve karbon iletkendir. Kartın köşesindeki {0}×{1} boş bölgede zaten Ø{2} delikler var; &lt;b&gt;ortadaki deliği büyüt&lt;/b&gt;: {3} mm matkap ucunu &lt;b&gt;penseyle tutup elle çevir&lt;/b&gt; ({4} mm FR4'te ~{5} s) ya da yuvarlak iğne eğeyle aç. Kartı masaya yatır, altına fire tahta koy, bastırma — plaket çatlar. &lt;b&gt;Toz cam elyafıdır:&lt;/b&gt; ıslak bezle sil, üfleme. Kart A lehimli: delik bölgesinde iz ya da parça olmadığını önce gözle doğrula (yerleşim planı o {6}×{7}'yi boş bıraktı).
en: ⚠ &lt;b&gt;DO NOT use the soldering iron:&lt;/b&gt; glass fibre does not melt, the resin carbonises and carbon conducts. The empty {0}×{1} area in the board's corner already has Ø{2} holes; &lt;b&gt;enlarge the middle hole&lt;/b&gt;: &lt;b&gt;hold a {3} mm drill bit in pliers and turn it by hand&lt;/b&gt; (~{5} s in {4} mm FR4) or open it with a round needle file. Lay the board flat on the table with scrap wood underneath, do not press — the board cracks. &lt;b&gt;The dust is glass fibre:&lt;/b&gt; wipe it with a damp cloth, do not blow. Board A is soldered: first check by eye that there are no traces or parts around the hole (the layout plan left that {6}×{7} empty).
tr: <b>İç kat ({0})</b>
en: <b>Inner layer ({0})</b>
tr: Dış kattaki delik kılavuz olur: havya ucunu ondan geçirip iç çubuğu del, sonra büyüt. Oval yuvaların arkasında iç çubuk kısa, delme yok.
en: The hole in the outer layer is the guide: pass the iron tip through it to pierce the inner stick, then enlarge. Behind the oval slots the inner stick is short, no drilling.
tr: Parça düz zeminde: çatlak var mı (ışığa tut)? Jak somunu düz oturuyor mu? Çatlak varsa japonla doldur, kurumadan bastır; büyükse parçayı yeniden kes (fire var).
en: Piece on a flat surface: any cracks (hold it up to the light)? Does the jack nut sit flat? If cracked, fill with CA glue and press before it cures; if the crack is large, cut the piece again (there are spares).
tr: Bütün delik ölçüleri deliğin <b>merkezi</b>. Çap sütunu Ø = yuvarlak delik; "{0} × {1} oval" = genişlik × yükseklik dikdörtgen yuva (USB, ŞARJ). Yuvarlak: born jaklar Ø{2} / Ø{3}, toggle'lar Ø{4}, M3 cıvatalar Ø{5}.
en: All hole dimensions are to the <b>centre</b> of the hole. Diameter column Ø = round hole; "{0} × {1} oval" = width × height rectangular slot (USB, «ŞARJ»). Round: banana jacks Ø{2} / Ø{3}, toggles Ø{4}, M3 bolts Ø{5}.
tr: Başlamadan önce — Yerleşim planında bitmiş olmalı
en: Before you start — must be finished in the layout plan
tr: <a href='7-yerlesim.html#s0.9'>Yerleşim {0}</a>
en: <a href='7-yerlesim.html#s0.9'>Layout {0}</a>
tr: İlk elektrik: +{0} / −{1} V ölçüldü, sigorta düşümü kontrol edildi
en: First power-up: +{0} / −{1} V measured, fuse drop checked
tr: <a href='7-yerlesim.html#s1.12'>Yerleşim {0}</a>
en: <a href='7-yerlesim.html#s1.12'>Layout {0}</a>
tr: J5 başlığına {0} telli ESP32 kablosu hazır (eşleme orada)
en: {0}-wire ESP32 cable for header J5 ready (the pin mapping is there)
tr: <a href='7-yerlesim.html#s5.12'>Yerleşim {0}</a>
en: <a href='7-yerlesim.html#s5.12'>Layout {0}</a>
tr: B tarafı: B:D8'e HV teli lehimli, B:O16 → A:C11 sarı tel bağlı
en: Side B: HV wire soldered to B:D8, yellow wire B:O16 → A:C11 connected
tr: <a href='7-yerlesim.html#s8.6'>Yerleşim {0}</a>
en: <a href='7-yerlesim.html#s8.6'>Layout {0}</a>
tr: Kapı sürücüsü (Q2/Q3) lehimli, T_KAPI teli (Z36) çıkmış
en: Gate driver (Q2/Q3) soldered, T_KAPI wire (Z36) brought out
tr: Kart-kart tel
en: Board-to-board wire
tr: B:O16 → A:C11 <span class='kucuk'>(B:T_N6 → A:T_HVALT: zincir alt dugumu (~{0} V, Thevenin {1}.2K). {2} cm kes — kutud)</span>
en: B:O16 → A:C11 <span class='kucuk'>(B:T_N6 → A:T_HVALT: bottom node of the divider chain (~{0} V, Thevenin {1}.2K). Cut {2} cm — in the encl)</span>
tr: Malzeme — stoktan {0}, alınacak {1}
en: Materials — from stock {0}, to buy {1}
tr: Stoktan çıkar
en: Take from stock
tr: Alınacak
en: To buy
tr: <b>Dil basacağı çubuk</b>
en: <b>Tongue depressor sticks</b>
tr: Gereken {0}, elde ~{1}; en az {2} al, fire payıyla {3}
en: Needed {0}, on hand ~{1}; buy at least {2}, {3} with spares
tr: <b>Yük yolu için kalın kablo (≥{0} mm²)</b>
en: <b>Heavy wire for the load path (≥{0} mm²)</b>
tr: KBL003 karışık montaj kablosunda kalın damar varsa oradan (soyup ölç: çıplak iletken tek damarda ≥ {0} mm, çok damarlı demette ~{1} mm). Halka pabuç stokta YOK ve plan onu ŞART KOŞMUYOR: jakta lehim kulağı ya da iki somun arasında kalaysız halka, bariyerde kalaysız burulmuş uç ({2}). Pabuç almak isteğe bağlı: yalıtımsız pabucun borusu sıkılıp lehimlenir.
en: If the KBL003 mixed hook-up wire has a heavy conductor, take it from there (strip and measure: bare conductor ≥ {0} mm for solid wire, ~{1} mm for a stranded bundle). Ring lugs are NOT in stock and the plan does NOT REQUIRE them: a solder lug on the jack or an untinned loop between two nuts, an untinned twisted end in the barrier block ({2}). Buying lugs is optional: the barrel of an uninsulated lug is crimped and soldered.
tr: <b>Ölçüm kabloları (banana + krokodil)</b>
en: <b>Test leads (banana + crocodile clip)</b>
tr: Kalibrasyon adımları ({0}–{1}) panel jaklarına kablo istiyor: bir ucu {2} mm banana erkek (CON005/CON006, {3} adet), öbür ucu krokodil (CON065/{4}, {5} adet) — ikisi de stokta. CAL → SKOP için kısa bir banana–banana da aynı parçalardan yapılır.
en: The calibration steps ({0}–{1}) need leads to the panel jacks: one end a {2} mm male banana plug (CON005/CON006, {3} pcs), the other an crocodile clip (CON065/{4}, {5} pcs) — both in stock. A short banana–banana lead for CAL → «SKOP» is made from the same parts.
tr: <b>{0} mA {1}×{2} cam sigorta (hızlı, F — stoktaki)</b>
en: <b>{0} mA {1}×{2} glass fuse (fast, F — the one in stock)</b>
tr: Bir tanesini ölç: gerçek {0} mA telin soğuk direnci {1}–{2} Ω (Littelfuse {3}/{4}); yuvadaki {5} Ω = {6} mA (FUS001). F {7} mA anahtar darbesinde atar → aşağıdaki T tipi gelene kadar yuvadaki {8} mA kalsın (stoktaki F'lerin hiçbiri darbeye ≥{9}× pay vermiyor).
en: Measure one: a genuine {0} mA wire has a cold resistance of {1}–{2} Ω (Littelfuse {3}/{4}); the {5} Ω in the holder = {6} mA (FUS001). An F {7} mA blows on the switch surge → keep the {8} mA in the holder until the T type below arrives (none of the F fuses in stock gives ≥{9}× margin on the surge).
tr: <b>{0} mA T (gecikmeli) {1}×{2} cam sigorta, markalı — İSTEĞE BAĞLI, sonraki plan</b>
en: <b>{0} mA T (time-delay) {1}×{2} glass fuse, branded — OPTIONAL, later plan</b>
tr: Littelfuse {0} / ESKA {1}.5xx / Schurter; cam gövde (seramik {2} mA çok dirençli). Anahtar açılış darbesine ({3} µF) ≥ {4}× pay; T {5} mA da olur (daha bol pay). Kullanıcı kararı {6}-{7}-{8}: yuvadaki sigorta hiç atmadı, kurulum bunu beklemiyor.
en: Littelfuse {0} / ESKA {1}.5xx / Schurter; glass body (ceramic {2} mA has too much resistance). ≥ {4}× margin on the switch-on surge ({3} µF); a T {5} mA also works (more margin). User decision {6}-{7}-{8}: the fuse in the holder has never blown, the build does not expect it to.
tr: <b>Soğutucu boşaltma direnci: {0} MΩ</b>
en: <b>Heatsink bleed resistor: {0} MΩ</b>
tr: Q1'in soğutucusu mikayla yalıtık, yani kutuda yüzen bir metal plaka. {0} MΩ ile kart GND'ye bağlanıyor: statik akıyor ama mika delinirse PİL {1}'i GND'ye kısa etmiyor ({2} µA). Düz tel BAĞLAMA.
en: Q1's heatsink is insulated with mica, i.e. a floating metal plate inside the enclosure. It is tied to board GND through {0} MΩ: static drains away, but if the mica is punctured it does not short «PİL» {1} to GND ({2} µA). DO NOT use a plain wire.
tr: <b>Hücre sigortası ×{0} (F1P, F2): {1} A F {2}×{3} cam</b>
en: <b>Cell fuse ×{0} (F1P, F2): {1} A F {2}×{3} glass</b>
tr: Her iki hücrenin ARTI ucuna birer tane. TP4056'nın koruma FET'i (FS8205) B−/OUT− arasında olduğu için hücre ucu ve H+/H− kablosundaki kısa devreyi DW01A kesemez; o kolu yalnız bu sigorta korur (kısa devre {0} A). ⚠ Anma neden yüksek: sigorta TP4056'nın BAT ucunda, yani ŞARJ akımının tamamı ({1} A, Rprog fabrika ayarı) buradan geçiyor — daha küçüğü ilk şarjda atar. Sürekli deşarj {2} mA; belirleyici olan şarj.
en: One on the POSITIVE end of each cell. The TP4056's protection FET (FS8205) sits between B−/OUT−, so the DW01A cannot interrupt a short on the cell end or in the H+/H− wire; only this fuse protects that branch (short-circuit {0} A). ⚠ Why the rating is high: the fuse is on the TP4056's BAT terminal, so the whole CHARGE current ({1} A, factory Rprog setting) flows through it — a smaller one blows on the first charge. Continuous discharge {2} mA; it is the charging that decides.
tr: <b>Sigorta yuvası ×{0}: {1}×{2} PCB klipsli (F1P, F2, F0)</b>
en: <b>Fuse holder ×{0}: {1}×{2} PCB clips (F1P, F2, F0)</b>
tr: Arka duvara, çubuk parçasına kablo bağıyla (F1P TP4056 rafının sağında, F2 sağ alt köşede, F0 sol uçta MT1'in yanında). Panel deliği YOK — kutu içi, servis için kapak açılır (hücre değişimi zaten kapak açtırıyor).
en: On the back wall, held to a stick piece with a cable tie (F1P to the right of the TP4056 shelf, F2 in the bottom right corner, F0 at the left end next to MT1). NO panel hole — inside the enclosure, the lid is opened for service (changing a cell needs the lid opened anyway).
tr: <b>Q1 soğutucusu (plan {0} × {1} × {2} mm VARSAYIYOR)</b>
en: <b>Q1 heatsink (the plan ASSUMES {0} × {1} × {2} mm)</b>
tr: Kayıtta ölçü yok (MEK002 'muhtelif boyutlarda'). Plan {0} × {1} × {2} mm varsayıyor ve Q1 için bu ölçüyle yer ayırdı. Elindeki blok daha büyükse kutuya girer ama kart B'ye olan açıklığı daralır — o zaman bloğu küçült ya da Q1'i {3}–{4} mm sağa kaydır. Daha küçükse sorun yok: Q1 pil testinde {5} W harcıyor, bu blok fazlasıyla yeter (soğutucusuz bile Tj {6} °C, sınır {7}).
en: The stock record has no size (MEK002 'various sizes'). The plan assumes {0} × {1} × {2} mm and reserved that space for Q1. If your block is bigger it still fits, but the clearance to board B shrinks — then make the block smaller or move Q1 {3}–{4} mm to the right. If it is smaller, no problem: Q1 dissipates {5} W in the battery test, this block is more than enough (even without a heatsink Tj {6} °C, limit {7}).
tr: <b>TO-{0} yalıtım (mika/plastik izolatör + burç)</b>
en: <b>TO-{0} insulation (mica/plastic insulator + bushing)</b>
tr: Q1'i soğutucudan yalıtmak için; plastik delikli/deliksiz izolatörler de var (MEK037–{0})
en: To insulate Q1 from the heatsink; plastic insulators with/without a hole are also available (MEK037–{0})
tr: <b>M3×{0} / M3×{1} vida, somun, pul</b>
en: <b>M3×{0} / M3×{1} screws, nuts, washers</b>
tr: Kart ayakları ×{0}, kapak ×{1}, Q1 köşebent ×{2}; gömme somun ×{3} ({4} ayak + {5} kapak rayı bloğu). {6} yuvaları artık yapıştırılıyor (B57b), onlara cıvata yok
en: Board feet ×{0}, lid ×{1}, Q1 corner bracket ×{2}; embedded nuts ×{3} ({4} feet + {5} lid rail blocks). The {6} holders are now glued (B57b), no bolts for them
tr: <b>{0}'li vidalı klemens {1} mm ({2} V iç bağlantı)</b>
en: <b>{0}-way screw terminal block {1} mm ({2} V internal connection)</b>
tr: Kartın {0} V telleri buraya; kart lehim sökmeden çıkar
en: The board's {0} V wires go here; the board comes out without desoldering
tr: <b>Dişi header ({0}'lü + {1}'li konnektör uçları)</b>
en: <b>Female header ({0}-way + {1}-way connector ends)</b>
tr: Şönt demeti ve Q1 kapı teli için kesilir
en: Cut for the shunt harness and the Q1 gate wire
tr: <b>XP128 {0} mm klemens (şönt bacakları + yük kabloları)</b>
en: <b>XP128 {0} mm terminal block (shunt legs + load cables)</b>
tr: Şönt bacakları ({0}–{1} mm) kutuplara; altlık çubuğuna yapıştırılır, şönt vidayla değişir
en: Shunt legs ({0}–{1} mm) into the poles; glued to the spacer stick, the shunt is swapped with a screwdriver
tr: <b>{0} mΩ Ø{1} şönt (takılı) + {2} mΩ Ø{3} (yedek, mA işleri)</b>
en: <b>{0} mΩ Ø{1} shunt (fitted) + {2} mΩ Ø{3} (spare, for mA work)</b>
tr: {0} mΩ: {1} A sürekli, {2} mA adım. {3} mΩ (R044): {4} A, {5} mA adım; kalibrasyon {6}'de ikisi de kullanılır
en: {0} mΩ: {1} A continuous, {2} mA step. {3} mΩ (R044): {4} A, {5} mA step; calibration {6} uses both
tr: <b>{0} hücre ×{1} (pil paketi, paralel)</b>
en: <b>{0} cell ×{1} (battery pack, parallel)</b>
tr: Başlı hücre: yaylı yuvada başlık temas eder; MEK025 yalıtım contası tak. PARALEL bağlanır: ilk takışta iki hücrenin gerilimi ±{0} V içinde olmalı ({1})
en: Button-top cell: the button touches in the spring holder; fit the MEK025 insulating ring. Connected in PARALLEL: at first insertion the two cell voltages must be within ±{0} V ({1})
tr: <b>{0} tekli yuva ×{1}</b>
en: <b>{0} single holder ×{1}</b>
tr: PWR004 (motorobit) ya da PWR007 (direnc.net); {0}×{1}×{2} ÖLÇÜLDÜ (B52d) — PWR009 PCB tipi, duvara cıvatalanmaz
en: PWR004 (motorobit) or PWR007 (direnc.net); {0}×{1}×{2} MEASURED (B52d) — PWR009 is a PCB type, cannot be bolted to the wall
tr: <b>TP4056 korumalı Type-C ×{0} (tek şarj girişi)</b>
en: <b>TP4056 protected Type-C ×{0} (single charging input)</b>
tr: İki paralel hücreyi birlikte doldurur. Rprog {0} kΩ fabrika ({1} A, hücre başına ~{2} A) → {3} kΩ ile {4} A, kutu daha az ısınır (isteğe bağlı)
en: Charges both parallel cells together. Rprog {0} kΩ factory ({1} A, ~{2} A per cell) → with {3} kΩ, {4} A, the enclosure heats up less (optional)
tr: <b>MT3608 yükseltici ×{0}</b>
en: <b>MT3608 boost converter ×{0}</b>
tr: Biri {0} V ({1} V barası: ESP32 + analog girişi), biri {2} V (analog, girişi B0505S); {3}'de yüksüz ayarlanır
en: One at {0} V ({1} V bus: ESP32 + analog input), one at {2} V (analog, fed from the B0505S); set with no load in {3}
tr: <b>{0} mm yeşil LED + {1} kΩ direnç (GÜÇ lambası)</b>
en: <b>{0} mm green LED + {1} kΩ resistor («GÜÇ» lamp)</b>
tr: LED003 ×{0}, direnç R060 (10K) ×{1} — ikisi de stokta. Daha parlak istersen {2}.7K (R015): {3} mA
en: LED003 ×{0}, resistor R060 (10K) ×{1} — both in stock. If you want it brighter, {2}.7K (R015): {3} mA
tr: <b>KTS102 toggle ×{0} (PİL, kutunun tek anahtarı)</b>
en: <b>KTS102 toggle ×{0} («PİL», the enclosure's only switch)</b>
tr: {0} ayak: orta + bir uç kullanılır (ON-OFF). Stokta {1}, biri yedek. Ortak (orta) ayağı ohmmetreyle doğrula, lehimde ayağı uzun ısıtma. B58'den beri KTS202 gerekmiyor
en: {0} pins: the middle + one end are used (ON-OFF). {1} in stock, one is a spare. Confirm the common (middle) pin with an ohmmeter, do not heat the pin for long when soldering. Since B58 no KTS202 is needed
tr: <b>F0 sigortası: {0} A {1}×{2} cam (hızlı)</b>
en: <b>F0 fuse: {0} A {1}×{2} glass (fast)</b>
tr: Ölçüm tarafının {0} V girişinde, kutu içinde (B58e). Yalnız iç arızada atar; atarsa kapağı aç, önce arızayı bul (B0505S, MT2, kart), sonra değiştir
en: On the {0} V input of the measurement side, inside the enclosure (B58e). It only blows on an internal fault; if it does, open the lid, find the fault first (B0505S, MT2, board), then replace it
tr: <b>B0505S-2WR3 ({0} W) yalıtılmış DC-DC, {1} V → {2} V (Hi-Link, motorobit) — {3} W DEĞİL</b>
en: <b>B0505S-2WR3 ({0} W) isolated DC-DC, {1} V → {2} V (Hi-Link, motorobit) — NOT {3} W</b>
tr: Kutunun iki toprağını ayıran tek parça (B58): analog {0} V bu modülün yalıtılmış çıkışından. Sürekli yük {1} W = %{2}; üreticinin en az %{3} yük şartı en düşük yükte %{4}. {5} W sürümünü (B0505S-1WR3) ALMA: sürekli yüke yeter (%{6}) ama açılışta yetmez — akım sınırında MT2'nin girişini ~{7} V'a çeker, kart {8} V'a çıkamaz (B58f benzetimi, sim3_kutu_besleme.py). {9} VDC yalıtımlı, kısa devre korumalı; gövde {10} × {11} × {12}, duvarda yeri ayrılı. Bacak sırası ada göre ({13}). {14}-{15}-{16}'de geldi (MOD013)
en: The one part that separates the enclosure's two grounds (B58): the analog {0} V comes from this module's isolated output. Continuous load {1} W = {2}%; the manufacturer's minimum-load requirement of {3}% is {4}% at the lowest load. DO NOT BUY the {5} W version (B0505S-1WR3): enough for the continuous load ({6}%) but not at power-up — in current limit it pulls MT2's input to ~{7} V and the board cannot reach {8} V (B58f simulation, sim3_kutu_besleme.py). {9} VDC isolation, short-circuit protected; body {10} × {11} × {12}, its place on the wall is reserved. Pin order by name ({13}). Arrived {14}-{15}-{16} (MOD013)
tr: <b>{0} µF {1} V elektrolitik ×{2} (MT2 girişi, CB)</b>
en: <b>{0} µF {1} V electrolytic ×{2} (MT2 input, CB)</b>
tr: B58f benzetimi: {0} µF her modelde yetiyor, {1} yetmiyor. Stokta {2}; {3} µF {4} V (C040) da olur
en: B58f simulation: {0} µF is enough for every model, {1} is not. In stock {2}; {3} µF {4} V (C040) also works
tr: <b>{0} Ω {1} W direnç ×{2} — YALNIZ {3}'teki belirtide (yedek yol)</b>
en: <b>{0} Ω {1} W resistor ×{2} — ONLY for the symptom in {3} (fallback)</b>
tr: B0505S +Vo ile MT2 IN+ arasına seri {0} Ω. Varsayılan olarak TAKILMAZ: kutu dolu pilde açılmıyorsa takılır ({1}). Stokta {2}
en: {0} Ω in series between B0505S +Vo and MT2 IN+. NOT FITTED by default: fitted if the enclosure does not power up with a full battery ({1}). In stock {2}
tr: <b>HB950 {0} pin bariyer klemens ×{1} (güç düğümü)</b>
en: <b>HB950 {0}-pin barrier terminal block ×{1} (power node)</b>
tr: YÜK/PİL kalın kabloları burada birleşir, XP128'e tek köprü gider. Bariyerin vidası altına iki-üç kalaysız burulmuş uç sığar; şönt değiştirirken yalnız XP128'in iki vidası gevşer
en: The heavy «YÜK»/«PİL» cables join here, a single bridge goes to the XP128. Two or three untinned twisted ends fit under a barrier screw; when changing the shunt only the two XP128 screws are loosened
tr: ◀ geri
en: ◀ back
tr: ileri ▶
en: next ▶
tr: 3B panelini aç/kapat
en: Open/close the 3D panel
tr: <b>3B görünüm</b> <span class="kucuk">sol tuş: döndür · orta/sağ tuş ya da Shift: kaydır · Ctrl+tekerlek (ya da tıklayıp tekerlek): yakınlaştır · çift tık: sıfırla · ok tuşları: döndür · <b>parçanın üzerine gel: adı, ölçüsü, uzunluğu</b> · tıkla / dokun: sabitle · <b>N / P</b>: sonraki / önceki parça · Esc: kapat</span>
en: <b>3D view</b> <span class="kucuk">left button: rotate · middle/right button or Shift: pan · Ctrl+wheel (or click, then wheel): zoom · double click: reset · arrow keys: rotate · <b>hover over a part: name, size, length</b> · click / tap: pin · <b>N / P</b>: next / previous part · Esc: close</span>
tr: izometrik
en: isometric
tr: üst
en: top
tr: ön
en: front
tr: arka
en: back
tr: sol
en: left
tr: sağ
en: right
tr: duvarlar
en: walls
tr: opak
en: opaque
tr: yakın olanlar saydam
en: near ones transparent
tr: hepsi saydam
en: all transparent
tr: hedefi göster
en: show target
tr: kablolar
en: cables
tr: hepsini göster
en: show all
tr: 3B kutu görünümü
en: 3D view of the enclosure
tr: <span class='ano'>{0}</span> <b>Çubuğunu ve parçaları ölç</b>
en: <span class='ano'>{0}</span> <b>Measure your sticks and parts</b>
tr: yaptım
en: done
tr: Bir çubuğu cetvelle ölç: <b>{0} × {1} × {2} mm</b>, uçlarda <b>{3} mm</b> yuvarlak bölüm ({4}-{5}-{6}'de doğrulandı); ortada <b>{7} mm düz</b> bölüm kalıyor.
en: Measure a stick with a ruler: <b>{0} × {1} × {2} mm</b>, with a <b>{3} mm</b> rounded section at each end (verified {4}-{5}-{6}); that leaves a <b>{7} mm flat</b> section in the middle.
tr: Kumpasla doğrula: born jak gövde dişi (≈ {0} mm; B60'tan beri panelde TEK model, büyük şeffaf); jakların duvarın içine uzanan boyu ({1}-{2}-{3}): {4} mm. USB-C fiş gövdesi (≈ {5} × {6}), toggle dişi ({7}). <b>Tutmuyorsa delik tablosunu değil ölçtüğün sayıyı kullan:</b> delik = ölçülen diş + {8} mm, en yakın matkap ucuna yuvarla, deneyerek büyüt. Tablodaki çaplar nominal; asıl ölçüt parçanın somuna kadar geçmesi.
en: Check with calipers: the thread of the banana jack body (≈ {0} mm; since B60 a SINGLE model on the panel, large clear); how far the jacks reach into the wall ({1}-{2}-{3}): {4} mm. USB-C plug body (≈ {5} × {6}), toggle thread ({7}). <b>If it does not match, use the number you measured, not the hole table:</b> hole = measured thread + {8} mm, round to the nearest drill bit, enlarge while testing. The diameters in the table are nominal; what counts is that the part goes in up to the nut.
tr: <b>Kart ölçüleri ÖLÇÜLDÜ</b> ({0}-{1}-{2}), yeniden ölçmene gerek yok: kart A {3} × {4} (Adım {5}'te bu ölçüye kesiliyor), kart B fabrika {6} × {7} (kesilmiyor), devkit {8} × {9}. Plan bu sayılarla üretildi. Tek bakılacak şey: <b>B:O16 → A:C11 sarı telin boyu</b>. Kutuda (kart B {10}°) iki lehim noktası düz çizgide {11} mm, kenarlardan ~{12} mm: tel <b>{13} mm</b> olmalı. Yerleşimde daha kısa kestiysen: ucuna aynı kalınlıkta tel ekle, lehimle, makaronla kapla (~{14} V, tehlikesiz) — GND ile burma, B'de GND yok.
en: <b>The board sizes WERE MEASURED</b> ({0}-{1}-{2}), no need to measure again: board A {3} × {4} (cut to this size in Step {5}), board B factory {6} × {7} (not cut), devkit {8} × {9}. The plan was generated with these numbers. The only thing to check: <b>the length of the yellow wire B:O16 → A:C11</b>. In the enclosure (board B at {10}°) the two solder points are {11} mm apart in a straight line, ~{12} mm from the edges: the wire must be <b>{13} mm</b>. If you cut it shorter in the layout: splice on a wire of the same gauge, solder, cover with heat-shrink (~{14} V, harmless) — do not twist it to GND, there is no GND on B.
tr: <b>Bir sayı tutmazsa ne yapacaksın:</b> ±{0} mm'ye kadar hiçbir şey — Adım {1} zaten "ölç, kalanı kes" diyor ve iç kat / direk / ray boyları oradan gerçek ölçüne göre çıkıyor. Daha büyüğü için sayıyı tek yerden değiştir: <code>uretim/kutu_veri.py</code> içindeki ilgili alanı düzelt, <code>python kutu.py</code> koş — kesim listesi, delik tabloları, çizimler ve 3B sahne yeniden üretilir; tutarsız bir şey kaldıysa denetim kırmızı verir.
en: <b>What to do if a number does not match:</b> up to ±{0} mm, nothing — Step {1} already says "measure, cut the rest", and the inner layer / post / rail lengths come from your real measurement there. For anything bigger, change the number in one place: fix the relevant field in <code>uretim/kutu_veri.py</code>, run <code>python kutu.py</code> — the cut list, hole tables, drawings and 3D scene are regenerated; if anything is left inconsistent the audit turns red.
tr: Çubuklar düz mü, çatlak var mı? Eğri olanları kapak için ayır.
en: Are the sticks straight, any cracks? Set the warped ones aside for the lid.
tr: A'nın dış ölçüsü {0} × {1}'den büyük mü? ({2} cm'lik kenar kesilmediyse {3} çıkar.) Büyükse <b>Adım {4}'te kes</b> — plan bu ölçüyle üretildi, büyük kalırsa ön jak gövdelerine {5} mm'den az pay kalıyor.
en: Is A's outer size larger than {0} × {1}? (If the {2} cm edge was not cut, it comes out {3}.) If larger, <b>cut it in Step {4}</b> — the plan was made with this size; if it stays larger there is less than {5} mm of clearance to the front jack bodies.
tr: <span class='ano'>{0}</span> <b>Kesim listesi — önce taban ve dış kat</b>
en: <span class='ano'>{0}</span> <b>Cut list — base and outer layer first</b>
tr: 🛑 <b>Önce çubuk say.</b> Bu listenin kendisi <b>{0} çubuk</b> istiyor, elinde ~{1} var → <b>en az {2} çubuk daha al</b> (fire payıyla ~{3} + {4}). Planın tamamı {5} çubuk; hepsini şimdi almak zorunda değilsin ama bu adımı bitirmeye yetecek kadarı şart, yoksa kesim yarıda kalır.
en: 🛑 <b>Count your sticks first.</b> This list alone needs <b>{0} sticks</b>, you have ~{1} → <b>buy at least {2} more sticks</b> (~{3} + {4} with spares). The whole plan takes {5} sticks; you do not have to buy them all now, but you need enough to finish this step, otherwise the cutting stops halfway.
tr: Çubuğun <b>iki ucu yuvarlak</b>: düz birleşme isteyen her parça ortadaki <b>düz bölümden</b> ({0} mm) kesilir. İç kat ve direk parçaları <b>tam çubuktan (bir yuvarlak uç parçada kalır)</b>: {1} mm boyunda, <b>yuvarlak uç aşağı</b> (tabanda gizli kalır). Duvar {2} sıra = {3} mm; çubuğu ortadan bölmek bu boyu VERMEZ ({4} mm kalır), o yüzden her dikey parça için bir tam çubuk açılır ve artan düz kısım öbür parçalara gider.
en: The stick has <b>two rounded ends</b>: every piece that needs a square joint is cut from the <b>flat section</b> in the middle ({0} mm). Inner layer and post pieces come <b>from a whole stick (one rounded end stays on the piece)</b>: {1} mm long, <b>rounded end down</b> (hidden at the base). The wall is {2} rows = {3} mm; cutting a stick in half does NOT give this length ({4} mm left), so a whole stick is used for each vertical piece and the leftover flat part goes to other pieces.
tr: <b>Ölç-kes-ölç:</b> şimdi yalnız <b>taban, raylar ve dış kat</b> parçalarını kes. İç kat, direkler, kapak ve altlıklar duvar bitince gerçek ölçüye göre kesilecek ({0}).
en: <b>Measure-cut-measure:</b> cut only the <b>base, rails and outer layer</b> pieces now. Inner layer, posts, lid and spacers are cut to the real size once the walls are done ({0}).
tr: Maket bıçağı ya da ince testere; kesmeden önce kurşun kalemle işaretle. Parçaları gruplara ayır.
en: Utility knife or fine saw; mark with a pencil before cutting. Sort the pieces into groups.
tr: Kesim listesi — şimdi kesilecekler
en: Cut list — to cut now
tr: Kesim listesi
en: Cut list
tr: bir çubuk {0} mm · gri uçlar yuvarlak ({1} mm) · düz bölüm {2} mm
en: one stick {0} mm · grey ends rounded ({1} mm) · flat section {2} mm
tr: Taban sırası — kısa parça
en: Base row — short piece
tr: artan {0}
en: leftover {0}
tr: Taban sırası — uzun parça
en: Base row — long piece
tr: Taban rayı — kısa parça
en: Base rail — short piece
tr: Taban rayı — uzun parça
en: Base rail — long piece
tr: Dış kat ön sıra {0} — sol
en: Outer layer front row {0} — left
tr: Dış kat ön sıra {0} — sağ
en: Outer layer front row {0} — right
tr: Dış kat arka sıra {0} — sol (arkadan)
en: Outer layer back row {0} — left (from behind)
tr: Dış kat arka sıra {0} — sağ (arkadan)
en: Outer layer back row {0} — right (from behind)
tr: Dış kat yan sıra {0} — kısa parça
en: Outer layer side row {0} — short piece
tr: Dış kat yan sıra {0} — uzun parça
en: Outer layer side row {0} — long piece
tr: Dış kat yan sıra {0}–{1} — kısa parça
en: Outer layer side rows {0}–{1} — short piece
tr: Dış kat yan sıra {0}–{1} — uzun parça
en: Outer layer side rows {0}–{1} — long piece
tr: Parça
en: Piece
tr: Hangi adımda
en: Which step
tr: düz bölümden
en: from the flat section
tr: Bütün plan için <b>{0} çubuk</b> gerekiyor ({1} mm testere payıyla, {2} mm artık). Elde ~{3}: en az <b>{4}</b> daha, fire payıyla {5}.
en: The whole plan needs <b>{0} sticks</b> (with {1} mm saw kerf, {2} mm left over). On hand ~{3}: at least <b>{4}</b> more, {5} with spares.
tr: Her gruptaki parça sayısı listedekiyle aynı mı?
en: Does the number of pieces in each group match the list?
tr: Aynı gruptaki parçaların boyu eşit mi (üst üste koy, uçlar hizalı)?
en: Are the pieces in a group the same length (stack them, ends aligned)?
tr: <span class='ano'>{0}</span> <b>Kart A'yı {kart_a_en:.0f} × {kart_a_boy:.0f} mm'ye getir</b>
en: <span class='ano'>{0}</span> <b>Bring board A to {kart_a_en:.0f} × {kart_a_boy:.0f} mm</b>
tr: Elindeki plaket <b>{0} × {1} mm</b> kesilmişti; plan <b>{2} × {3}</b> istiyor. Fazlalık <b>sağda ~{4} mm, önde ~{5} mm</b> (A1 köşesi sol-arkada kalıyor, lehimli bölgeye dokunmuyorsun).
en: Your board was cut to <b>{0} × {1} mm</b>; the plan wants <b>{2} × {3}</b>. The excess is <b>~{4} mm on the right, ~{5} mm at the front</b> (corner A1 stays at the back left, you do not touch the soldered area).
tr: <b>Neden şart:</b> kesmezsen kart sağda x {0}'e uzanır ve ESP32'nin (x {1}) üstüne biner. Kutuya sığmaz.
en: <b>Why it is a must:</b> uncut, the board reaches x {0} on the right and runs over the ESP32 (x {1}). It does not fit in the enclosure.
tr: <b>Nasıl:</b> kesilecek çizgiyi iki yüzden de maket bıçağıyla <b>delik sırasının ortasından</b> derin çiz ({0}–{1} geçiş), sonra masa kenarında kısa kenardan başlayarak kır. Zımparayla düzelt. Cam elyafı tozu için maske/ıslak bez.
en: <b>How:</b> score the cut line deeply on both faces with a utility knife <b>through the middle of the hole row</b> ({0}–{1} passes), then snap it over the edge of the table starting from the short side. Clean up with sandpaper. Mask / damp cloth for the glass-fibre dust.
tr: Kesmeden önce kesim çizgisinin lehimli bir ize ya da parçaya denk gelmediğini gözle kontrol et — yerleşim planı kenarda {0}×{1} delik boş bırakmıştı.
en: Before cutting, check by eye that the cut line does not cross a soldered trace or part — the layout plan left {0}×{1} holes empty at the edge.
tr: Kesilen kenarda kalkmış bakır ya da kopmuş iz yok (ışığa tut).
en: No lifted copper or broken traces on the cut edge (hold it up to the light).
tr: Kart, planın sol-arka köşesine (x {0}, y {1}) konunca ön duvara <b>{2} mm</b> kalıyor — bu boşluk ön panel jaklarının {3} mm'lik gövdeleri ve kablo kıvrımı için.
en: With the board in the back-left corner of the plan (x {0}, y {1}) there are <b>{2} mm</b> left to the front wall — this space is for the {3} mm bodies of the front panel jacks and the cable bends.
tr: <span class='ano'>{0}</span> <b>Taban sıralarını diz</b>
en: <span class='ano'>{0}</span> <b>Lay out the base rows</b>
tr: Taban parçalarını düz bir zeminde <b>sıra sıra</b> diz: her sıra iki parça uç uca, ek yeri sırada bir sağa bir sola (kaydırmalı).
en: Lay the base pieces out on a flat surface <b>row by row</b>: each row is two pieces end to end, the joint alternating right and left from row to row (staggered).
tr: Sıralar yan yana, boşluksuz. Henüz yapıştırma yok.
en: Rows side by side, no gaps. No gluing yet.
tr: Bu adımda gereken çubuk parçaları — toplam {0}
en: Stick pieces needed in this step — {0} in total
tr: Parçaları çubuk üstünde gör
en: See the pieces on the stick
tr: Bu adımın parçaları çubuk üstünde
en: This step's pieces on the stick
tr: Taban — kuşbakışı
en: Base — top view
tr: {0} × {1} mm — {2} sıra, her sıra iki parça, ek yeri sırada bir sola bir sağa
en: {0} × {1} mm — {2} rows, two pieces per row, the joint alternating left and right
tr: {0} sıra × {1} mm
en: {0} rows × {1} mm
tr: sarı = alttan yapıştırılan iki ray (sıralara dik, ikişer parça)
en: yellow = the two rails glued underneath (across the rows, two pieces each)
tr: Dizilen tabanın eni ve boyu tabloyla uyuyor mu?
en: Do the width and depth of the laid-out base match the table?
tr: <span class='ano'>{0}</span> <b>Alttan raylarla bağla</b>
en: <span class='ano'>{0}</span> <b>Join from underneath with rails</b>
tr: Rayları tabanın <b>altına</b>, sıralara dik (derinlik yönünde), uçlardan içeride yapıştır. Ray bütün sıraları birbirine bağlar.
en: Glue the rails to the <b>underside</b> of the base, across the rows (front to back), set in from the ends. The rail ties all the rows together.
tr: <b>Ray merkezleri: sol kenardan {0} mm ve {1} mm</b> (dış en {2} mm'nin ¼'ü ve ¾'ü). Kutu fiilen bu iki rayın üstünde duruyor: devrilme ve yük payı hesabı bu konumu varsayıyor, ±{3} mm'den fazla kaydırma.
en: <b>Rail centres: {0} mm and {1} mm from the left edge</b> (¼ and ¾ of the {2} mm outer width). The enclosure actually stands on these two rails: the tipping and load margin calculations assume this position, do not shift them more than ±{3} mm.
tr: Sıcak silikonu ray boyunca sürekli çek, nokta nokta değil; {0} s içinde bastır. Sıralar arası derzleri isteğe bağlı ince japonla süz (maskeleme bandı üstten tutar).
en: Run the hot glue continuously along the rail, not in dots; press within {0} s. Optionally run thin CA glue into the joints between rows (masking tape holds them from above).
tr: Taban tek parça gibi kalkıyor mu? Ortadan tutup kaldır.
en: Does the base lift as one piece? Pick it up by the middle.
tr: Taban düz mü, beşik gibi kamburlaşmamış mı?
en: Is the base flat, not bowed like a cradle?
tr: <span class='ano'>{0}</span> <b>Ön duvar parçalarını del</b>
en: <span class='ano'>{0}</span> <b>Drill the front wall pieces</b>
tr: Delikler duvar dikilmeden, parça <b>düz zeminde</b> delinir: {0} mm'lik çubukta Ø{1} delik {2} mm et bırakır, yerinde delmek çatlatır.
en: The holes are made before the walls go up, with the piece <b>on a flat surface</b>: a Ø{1} hole in a {0} mm stick leaves {2} mm of wood, drilling it in place cracks it.
tr: Aşağıdaki tabloda her delik hangi sıranın hangi parçasına geliyor; <b>ölçüler deliğin MERKEZİ</b>: parçanın <b>sol ucundan</b> x, çubuğun <b>alt kenarından</b> z. Çap sütunu Ø yazıyorsa <b>yuvarlak</b> delik, "{0} × {1} oval" yazıyorsa dikdörtgen yuva.
en: The table below shows which piece of which row each hole goes into; <b>dimensions are to the CENTRE of the hole</b>: x from the <b>left end</b> of the piece, z from the <b>bottom edge</b> of the stick. If the diameter column says Ø it is a <b>round</b> hole, if it says "{0} × {1} oval" it is a rectangular slot.
tr: Matkap yoksa: "Delikleri nasıl açarım" bölümü (sayfanın başında) — havya ucuyla kılavuz, bıçak/zımparayla büyütme. Parçanın altına fire çubuk koy.
en: Without a drill: see "How do I make the holes" (at the top of the page) — pilot with the iron tip, enlarge with a knife/sandpaper. Put a scrap stick under the piece.
tr: Delinen parçayı sıra ve konumuyla etiketle (örn. "ön {0} sol").
en: Label each drilled piece with its row and position (e.g. "front {0} left").
tr: Ön duvar — dışarıdan
en: Front wall — from outside
tr: ön duvar
en: front wall
tr: ek {0}
en: joint {0}
tr: PİL {0}
en: «PİL» {0}
tr: AÇ / KAPA
en: «AÇ / KAPA»
tr: GÜÇ
en: «GÜÇ»
tr: YÜK {0}
en: «YÜK» {0}
tr: Ön duvar — DIŞARIDAN bakış · x dış sol kenardan
en: Front wall — seen from OUTSIDE · x from the outer left edge
tr: turuncu çizgi = dış kat ek yeri
en: orange line = outer layer joint
tr: {0} mm (dış)
en: {0} mm (outer)
tr: Delik tablosu — parça parça
en: Hole table — piece by piece
tr: Sıra
en: Row
tr: Merkez: parçanın sol ucundan
en: Centre: from the left end of the piece
tr: Merkez: çubuğun alt kenarından
en: Centre: from the bottom edge of the stick
tr: sağ ({0} mm)
en: right ({0} mm)
tr: sol ({0} mm)
en: left ({0} mm)
tr: Ölçüler <b>önden bakan kişinin solundan</b>. Sıra {0} mm, iki parça; ek yerleri (soldan): {1}. sıra {2}, {3}. sıra {4}, {5}. sıra {6}, {7}. sıra {8}, {9}. sıra {10}. Sol parça sıfırdan ek yerine, sağ parça ek yerinden sona. Deliksiz sıralar da aynı ek yerleriyle.
en: Dimensions are <b>from the left of a person looking at the front</b>. Row {0} mm, two pieces; joints (from the left): row {1} {2}, row {3} {4}, row {5} {6}, row {7} {8}, row {9} {10}. The left piece runs from zero to the joint, the right piece from the joint to the end. Rows without holes use the same joints.
tr: Jakı deliğe sok: gövde geçiyor, somun yüzeye oturuyor.
en: Push the jack into the hole: the body goes through, the nut sits on the surface.
tr: Delik çevresinde çatlak yok.
en: No cracks around the hole.
tr: <span class='ano'>{0}</span> <b>Arka duvar parçalarını del</b>
en: <span class='ano'>{0}</span> <b>Drill the back wall pieces</b>
tr: Aynı yöntem; ölçüler yine deliğin MERKEZİ, ama <b>arkadan bakınca soldan</b> (parçalar da o çerçevede adlandı: "sol (arkadan)").
en: Same method; dimensions are again to the CENTRE of the hole, but <b>from the left as seen from behind</b> (the pieces are named in that frame too: "left (from behind)").
tr: USB ve ŞARJ yuvaları oval ({0} × {1}): merkezin {2} mm sağına ve soluna iki Ø{3} daire, arası maket bıçağıyla.
en: The USB and «ŞARJ» slots are oval ({0} × {1}): two Ø{3} circles {2} mm to the right and left of the centre, the part between them cut with a utility knife.
tr: <b>Deler delmez iki ovalin İÇ yüzüne kurşun kalemle adını yaz: ŞARJ / USB.</b> İkisi tıpatıp aynı ve etiketler {0}'e kadar yapıştırılmıyor; bu çizim arkadan bakana göre ters. Kutu kurulunca <b>önden (jak tarafından) bakınca ŞARJ solda, USB sağda</b>.
en: <b>As soon as they are drilled, write the name on the INSIDE face of both ovals in pencil: «ŞARJ» / USB.</b> The two are identical and the labels are not stuck on until {0}; this drawing is mirrored for someone looking from behind. Once the enclosure is built, <b>seen from the front (the jack side) «ŞARJ» is on the left, USB on the right</b>.
tr: Arka duvar — dışarıdan
en: Back wall — from outside
tr: arka duvar
en: back wall
tr: ŞARJ
en: «ŞARJ»
tr: Arka duvar — DIŞARIDAN bakış · x dış sol kenardan (arkaya geçince kendi solun)
en: Back wall — seen from OUTSIDE · x from the outer left edge (your own left once you go round to the back)
tr: Ölçüler <b>arkaya geçip arkadan bakan kişinin solundan</b>. Sıra {0} mm, iki parça; ek yerleri (soldan): {1}. sıra {2}, {3}. sıra {4}, {5}. sıra {6}, {7}. sıra {8}, {9}. sıra {10}. Sol parça sıfırdan ek yerine, sağ parça ek yerinden sona. Deliksiz sıralar da aynı ek yerleriyle.
en: Dimensions are <b>from the left of a person who has gone round to the back and looks from behind</b>. Row {0} mm, two pieces; joints (from the left): row {1} {2}, row {3} {4}, row {5} {6}, row {7} {8}, row {9} {10}. The left piece runs from zero to the joint, the right piece from the joint to the end. Rows without holes use the same joints.
tr: USB-C fişi iki yuvadan da rahat geçiyor.
en: A USB-C plug goes easily through both slots.
tr: İki ovalin iç yüzünde ŞARJ / USB yazıyor.
en: The inside faces of the two ovals say «ŞARJ» / USB.
tr: <span class='ano'>{0}</span> <b>{1}. sıra — ön ve arka</b>
en: <span class='ano'>{0}</span> <b>Row {1} — front and back</b>
tr: Ön ve arka duvarın ilk sırasını tabanın kenarına, <b>dik</b> yapıştır. Geniş yüz dışa, delikli parçalar tablodaki yerde.
en: Glue the first row of the front and back walls to the edge of the base, <b>upright</b>. Wide face outwards, the drilled pieces where the table says.
tr: Her sıra iki parça; ek yeri tabloda yazan x'te. <b>Arka duvar parçaları "arkadan bakınca" adlandı:</b> önde durup yerleştiriyorsan "sol (arkadan)" parça senin SAĞINA gelir — şaşırmamak için arka sırayı kutunun arkasına geçip diz.
en: Each row is two pieces; the joint is at the x given in the table. <b>The back wall pieces are named "as seen from behind":</b> if you place them standing at the front, the "left (from behind)" piece comes to YOUR RIGHT — to avoid confusion, go round to the back of the enclosure to lay the back row.
tr: {0}. sıra — izometrik
en: Row {0} — isometric
tr: {0}. sıra
en: Row {0}
tr: {0}. sıra bitti · dış kat yüksekliği {1} mm
en: Row {0} done · outer layer height {1} mm
tr: öne bakan kenar = ön duvar (jaklar)
en: edge facing forward = front wall (jacks)
tr: Diğer çizimler ({0})
en: Other drawings ({0})
tr: Ön duvar — ek yerleri
en: Front wall — joints
tr: Arka duvar — ek yerleri (arkadan bakış)
en: Back wall — joints (seen from behind)
tr: Bütün sıraların parça boyları ve ek yerleri
en: Piece lengths and joints of all rows
tr: Ön (sol + sağ, önden)
en: Front (left + right, from the front)
tr: Arka (sol + sağ, arkadan)
en: Back (left + right, from behind)
tr: Yanlar (önden arkaya)
en: Sides (front to back)
tr: Her sıra iki parça; sayılar parça boyu, soldan sağa. Ek yerleri deliklerden ≥ {0} mm uzakta ve ardışık sıralarda ≥ {1} mm kaymış (denetimli). Yan sıralar ön ve arka dış katların arasına girer.
en: Each row is two pieces; the numbers are piece lengths, left to right. Joints are ≥ {0} mm from holes and shifted ≥ {1} mm between consecutive rows (audited). The side rows fit between the front and back outer layers.
tr: Gönye ya da kitap kenarıyla bak: duvar tabana dik mi?
en: Check with a square or the edge of a book: is the wall perpendicular to the base?
tr: <span class='ano'>{0}</span> <b>{1}. sıra — yanlar</b>
en: <span class='ano'>{0}</span> <b>Row {1} — sides</b>
tr: Yan duvarların ilk sırasını ön ve arka duvarın <b>arasına</b> sıkıştır.
en: Fit the first row of the side walls <b>between</b> the front and back walls.
tr: Parçayı uçlarından ve ortadan japonla tuttur (hizala, {0} s bastır); sonra iç köşeye sıcak silikonla fileto çek.
en: Tack the piece with CA glue at the ends and the middle (align, press {0} s); then run a hot-glue fillet into the inside corner.
tr: Dört köşe de kapalı mı?
en: Are all four corners closed?
tr: <span class='ano'>{0}</span> <b>{1}. sıradan en üste</b>
en: <span class='ano'>{0}</span> <b>From row {1} to the top</b>
tr: Üstteki sıraları aynı şekilde ekle; ek yerleri tabloda — sıradan sıraya kayıyor, üst üste gelmiyor.
en: Add the upper rows the same way; the joints are in the table — they shift from row to row and never line up.
tr: Kalan bütün sıraları ekle — duvar toplam {0} sıra ({1} mm). Delikli parçalar tablodaki konumda: aynı x'teki delikler alt alta hizalanmalı.
en: Add all the remaining rows — the wall has {0} rows in total ({1} mm). Drilled pieces in the position from the table: holes at the same x must line up one above the other.
tr: Duvar yüksekliği her köşede aynı mı?
en: Is the wall height the same at every corner?
tr: Kutuyu ters çevir, sallanıyor mu?
en: Turn the enclosure upside down — does it rock?
tr: <span class='ano'>{0}</span> <b>Ölç, kalanı kes</b>
en: <span class='ano'>{0}</span> <b>Measure, cut the rest</b>
tr: Şimdi gerçek ölçüleri al: duvar yüksekliği (derz dahil), iç en, iç boy.
en: Now take the real dimensions: wall height (including joints), inside width, inside depth.
tr: İç kat çubuklarını, direk parçalarını ve kapak raylarını <b>ölçtüğün</b> yüksekliğe/uzunluğa kes (tablo nominal; {0}–{1} mm sapma normal).
en: Cut the inner layer sticks, post pieces and lid rails to the height/length <b>you measured</b> (the table is nominal; {0}–{1} mm of deviation is normal).
tr: Kesim listesi — duvar ölçüldükten sonra
en: Cut list — after the wall is measured
tr: artan (düz)
en: leftover (flat)
tr: İç kat dikey çubuk (yuvarlak uç aşağı)
en: Inner layer vertical stick (rounded end down)
tr: {0}. yarım
en: half {0}
tr: İç kat kısa çubuk — x {0}, yuvanın üstü (z {1}
en: Inner layer short stick — x {0}, above the slot (z {1}
tr: Köşe direği parçası (yuvarlak uç aşağı)
en: Corner post piece (rounded end down)
tr: Kapak sırası — kısa parça
en: Lid row — short piece
tr: Kapak sırası — uzun parça
en: Lid row — long piece
tr: Kapak rayı (yan duvara yaslı, tek parça)
en: Lid rail (against the side wall, one piece)
tr: Ayak bloğu parçası — A ({0} blok × {1} kat)
en: Foot block piece — A ({0} blocks × {1} layers)
tr: Altlık — ESP32
en: Spacer — ESP32
tr: ESP32 kızak rayı — {0} mm şerit, uzun kenarı ü
en: ESP32 cradle rail — {0} mm strip, on its long ed
tr: ESP32 omuz takozu — {0} mm şerit, ikiye böl ({1}
en: ESP32 shoulder block — {0} mm strip, split in two ({1}
tr: Altlık — RS
en: Spacer — RS
tr: Ayak bloğu parçası — B ({0} blok × {1} kat)
en: Foot block piece — B ({0} blocks × {1} layers)
tr: Köşebent parçası — Q1 ({0} kat)
en: Corner bracket piece — Q1 ({0} layers)
tr: HV ankraj bloğu ({0} kat)
en: HV anchor block ({0} layers)
tr: TP1 raf — alt kat, kanal için iki parça ({0} p
en: TP1 shelf — bottom layer, two pieces for the channel ({0} p
tr: TP1 raf — üst kat ({0} parça)
en: TP1 shelf — top layer ({0} pieces)
tr: TP1 raf — dayanak, uzun kenarı üstünde dik (
en: TP1 shelf — stop, upright on its long edge (
tr: Kapak somun bloğu parçası ({0} blok × {1} kat)
en: Lid nut block piece ({0} blocks × {1} layers)
tr: Uzunluk (nominal)
en: Length (nominal)
tr: tam çubuktan (bir yuvarlak uç parçada kalır)
en: from a whole stick (one rounded end stays on the piece)
tr: İç kat kısa çubuk — x {0}, yuvanın üstü (z {1}'dan)
en: Inner layer short stick — x {0}, above the slot (from z {1})
tr: çubuk ortadan ikiye
en: stick cut in half
tr: ESP32 kızak rayı — {0} mm şerit, uzun kenarı üstünde dik
en: ESP32 cradle rail — {0} mm strip, upright on its long edge
tr: ESP32 omuz takozu — {0} mm şerit, ikiye böl ({1} + {2})
en: ESP32 shoulder block — {0} mm strip, split in two ({1} + {2})
tr: TP1 raf — alt kat, kanal için iki parça ({0} parça)
en: TP1 shelf — bottom layer, two pieces for the channel ({0} pieces)
tr: TP1 raf — dayanak, uzun kenarı üstünde dik ({0} parça)
en: TP1 shelf — stop, upright on its long edge ({0} pieces)
tr: Bir iç kat çubuğunu deneme yerleştir: üstü dış katla hizalı mı?
en: Dry-fit one inner layer stick: is its top flush with the outer layer?
tr: <span class='ano'>{0}</span> <b>İç kat — dikey çubuklar</b>
en: <span class='ano'>{0}</span> <b>Inner layer — vertical sticks</b>
tr: Dört duvarın <b>iç yüzüne</b> dikey çubukları yapıştır (kontrplak gibi çapraz kat). <b>Yuvarlak uç aşağı.</b>
en: Glue the vertical sticks to the <b>inside face</b> of all four walls (cross-layered like plywood). <b>Rounded end down.</b>
tr: Konum önemli: her yuvarlak deliğin tam arkasına bir çubuk <b>ortalanır</b> (tablo). Aradaki dar boşluklar boş kalabilir, dış kat kapatıyor.
en: Position matters: a stick is <b>centred</b> right behind every round hole (table). The narrow gaps in between can stay empty, the outer layer covers them.
tr: Japonu üst-orta-alt üç ince çizgi sür, tek seferde doğru yere koy, {0} s bastır. Sıcak silikon KULLANMA: kalınlık yapar, iç kat {1} mm kalmalı.
en: Apply the CA glue in three thin lines — top, middle, bottom — put the stick in the right place the first time, press {0} s. DO NOT use hot glue: it adds thickness, the inner layer must stay {1} mm.
tr: Ön duvar — iç kat çubukları
en: Front wall — inner layer sticks
tr: turuncu çizgi = dış kat ek yeri · kesikli = iç kat dikey çubuk (iç yüzde, üstte sol kenarı)
en: orange line = outer layer joint · dashed = inner layer vertical stick (on the inside face, its left edge at the top)
tr: Arka duvar — iç kat çubukları (arkadan bakış)
en: Back wall — inner layer sticks (seen from behind)
tr: İç kat çubuk konumları
en: Inner layer stick positions
tr: Çubuk sol kenarları (mm, İÇ sol köşeden — önden bakınca)
en: Stick left edges (mm, from the INSIDE left corner — seen from the front)
tr: {0}, {1}, {2} (kısa, z {3}'dan), {4}, {5}, {6}, {7}, {8} (kısa, z {9}'dan), {10}, {11}
en: {0}, {1}, {2} (short, from z {3}), {4}, {5}, {6}, {7}, {8} (short, from z {9}), {10}, {11}
tr: sol / sağ (y)
en: left / right (y)
tr: Ön/arka çubuklar iç sol köşeden ölçülür (ikisi de önden bakan kişinin solundan; arka duvarda içeriden bakarken sağdan sayman gerekir). Her delik bir çubuğun ortasına geliyor; aradaki dar boşluklar boş kalır. Yan çubuklar arka iç köşeden. Direkler köşede {0} mm; kapak rayı direkler arasında ({1} mm).
en: Front/back sticks are measured from the inside left corner (both from the left of a person looking at the front; on the back wall, looking from inside, you have to count from the right). Every hole lands on the middle of a stick; the narrow gaps in between stay empty. Side sticks from the back inside corner. Posts in the corners, {0} mm; the lid rail between the posts ({1} mm).
tr: Duvara parmakla bastır: artık esnememeli.
en: Press the wall with a finger: it should no longer flex.
tr: Deliklerin arkasında çubuk ortası var, ek yeri yok.
en: Behind every hole there is the middle of a stick, not a joint.
tr: <span class='ano'>{0}</span> <b>Kapak cıvata deliklerini aç (kutu boşken)</b>
en: <span class='ano'>{0}</span> <b>Drill the lid bolt holes (while the enclosure is empty)</b>
tr: Her yan duvarda iki nokta işaretle (aşağıdaki tablo: y arka dış köşeden, z tabandan), <b>Ø{0} del</b> — delik dış kat ({1} mm) + iç kat ({2} mm) boyunca geçer.
en: Mark two points on each side wall (table below: y from the back outer corner, z from the base), <b>drill Ø{0}</b> — the hole goes through the outer layer ({1} mm) + inner layer ({2} mm).
tr: <b>Neden şimdi:</b> kutu şu an boş. Adım {0}'dan sonra içeride lehimlenmiş kart A var ve havyayla delerken çıkan yanık talaşı doğrudan onun üstüne döküleceği için burada deliniyor. Kapağa henüz gerek yok: konumlar tablodan.
en: <b>Why now:</b> the enclosure is empty at this point. After Step {0} the soldered board A is inside, and the burnt shavings from piercing with the iron would fall right onto it, so it is done here. The lid is not needed yet: the positions come from the table.
tr: Somun blokları kapak yapılınca ({0}) <b>cıvatanın üstüne merkezlenerek</b> yapıştırılacak — kendi kendine hizalanır.
en: The nut blocks are glued once the lid is made ({0}), <b>centred over the bolt</b> — they align themselves.
tr: Kapak — kuşbakışı
en: Lid — top view
tr: sarı = yan duvarlara yaslanan iki kapak rayı (altta, {0} mm yüzü dik) · siyah = M3 cıvata
en: yellow = the two lid rails against the side walls (underneath, {0} mm face upright) · black = M3 bolt
tr: y (arka dış köşeden)
en: y (from the back outer corner)
tr: z (tabandan)
en: z (from the base)
tr: Cıvata
en: Bolt
tr: Dört delikten M3 cıvata sürtünerek geçiyor.
en: An M3 bolt goes through all four holes with friction.
tr: Delikler yan duvarın iç kat çubuğunun ortasına denk geldi (ek yerine değil).
en: The holes landed on the middle of the side wall's inner layer stick (not on a joint).
tr: <span class='ano'>{0}</span> <b>Köşe direkleri</b>
en: <span class='ano'>{0}</span> <b>Corner posts</b>
tr: Her köşe için {0} parçayı üst üste japonla yapıştırıp <b>{1} × {2} × {3} mm</b> direk yap ({4} adet), yuvarlak uçlar aşağı.
en: For each corner, glue {0} pieces on top of each other with CA glue to make a <b>{1} × {2} × {3} mm</b> post ({4} pcs), rounded ends down.
tr: Dört iç köşeye, iki duvara da yaslanacak şekilde yapıştır; üstü duvarla hizalı.
en: Glue them into the four inside corners so they rest against both walls; tops flush with the wall.
tr: Kuşbakışı — köşe direkleri
en: Top view — corner posts
tr: Yerleşim
en: Layout
tr: kuşbakışı · alt kenar = ön duvar (jaklar) · açık kahverengi = ayak / altlık / köşebent
en: top view · bottom edge = front wall (jacks) · light brown = foot / spacer / corner bracket
tr: ince çerçeve = panel parçasının içeri uzanan gövdesi · köşelerde direkler
en: thin outline = the body of a panel part reaching inside · posts in the corners
tr: aynı hizadaki jaklar: daireler soldan sağa, adlar alt alta = panelde üstten alta
en: jacks at the same position: circles left to right, names one below the other = top to bottom on the panel
tr: Kutuyu köşelerinden tutup bur: köşeler oynamamalı.
en: Twist the enclosure by its corners: the corners should not move.
tr: Dört direğin üstü aynı seviyede.
en: The tops of all four posts are level.
tr: <span class='ano'>{0}</span> <b>İç katı deliklerden geçerek del</b>
en: <span class='ano'>{0}</span> <b>Drill the inner layer through the holes</b>
tr: Dış kattaki her delik kılavuz: havya ucunu / matkabı ondan geçir, iç kat çubuğunu <b>dıştan içe</b> del, aynı çapa büyüt. İçeriden çıkarken kıymık verirse fire çubukla destekle.
en: Every hole in the outer layer is a guide: pass the iron tip / drill through it and drill the inner layer stick <b>from outside in</b>, enlarge to the same diameter. If it splinters coming out on the inside, back it with a scrap stick.
tr: Arka duvar için de aynı. <b>USB ve ŞARJ yuvalarında delme yok:</b> arkalarındaki iç kat çubukları kısa, yuvanın üstünden başlıyor ({0} tablosu).
en: The same for the back wall. <b>No drilling at the USB and «ŞARJ» slots:</b> the inner layer sticks behind them are short and start above the slot ({0} table).
tr: Her delik iki kattan düz geçiyor; jak gövdesi rahat giriyor.
en: Every hole goes straight through both layers; the jack body goes in easily.
tr: <span class='ano'>{0}</span> <b>Born jakları tak ({1} adet)</b>
en: <span class='ano'>{0}</span> <b>Fit the banana jacks ({1} pcs)</b>
tr: Kutuya giren
en: Going into the enclosure
tr: V girişi born jak çifti (panel): kırmızı = V girişi, siyah = COM (kart GND).
en: V input banana jack pair (panel): red = V input, black = COM (board GND).
tr: HV girişi born jakı (panel): AYRI, işaretli ve kutudaki TEK SARI jak (B60); COM, J1'in COM'uyla ortak.
en: HV input banana jack (panel): SEPARATE, marked, and the ONLY YELLOW jack on the enclosure (B60); its COM is shared with J1's COM.
tr: YÜK born jak çifti (büyük boy, yeşil ×{0}, panel): J3.1 → yük eksisi, J3.2 → kaynak eksisi. Jakların iç ucundan şöntün yanındaki bariyer klemense (HB950) kısa kalın kablo — jak tarafı lehim kulağı ya da iki somun arasında kalaysız halka, bariyer tarafı kalaysız burulmuş uç (kalay vida altında akar, gevşer; halka pabuç stokta yok, gerekmez); akım J3.1 → şönt → J3.2 yolunu izler.
en: «YÜK» banana jack pair (large, green ×{0}, panel): J3.1 → load negative, J3.2 → source negative. A short heavy cable from the inner end of the jacks to the barrier terminal block (HB950) next to the shunt — on the jack side a solder lug or an untinned loop between two nuts, on the barrier side an untinned twisted end (solder creeps under a screw and loosens; ring lugs are not in stock and not needed); the current follows the path J3.1 → shunt → J3.2.
tr: Skop girişi born jakı (panel); COM ortak.
en: Scope input banana jack (panel); COM shared.
tr: PİL born jak çifti (büyük boy, mavi ×{0}, panel): J7.1 → yük direnci, J7.2 → pil eksisi; J3'ten AYRI — karıştırılırsa kesme çalışmaz.
en: «PİL» banana jack pair (large, blue ×{0}, panel): J7.1 → load resistor, J7.2 → battery negative; SEPARATE from J3 — mix them up and the cut-off does not work.
tr: Sekiz jakı deliklere tak, somunları içeriden sık. Hepsi AYNI model (büyük şeffaf, B60). Renkler: <b>YÜK</b> yeşil ×{0}, <b>PİL</b> mavi ×{1}, <b>V/SKOP</b> kırmızı, <b>COM</b> siyah, <b>HV sarı</b> — kutudaki tek sarı jak, yerini karıştırma.
en: Fit the eight jacks into the holes, tighten the nuts from inside. All the SAME model (large clear, B60). Colours: <b>«YÜK»</b> green ×{0}, <b>«PİL»</b> blue ×{1}, <b>V/«SKOP»</b> red, <b>COM</b> black, <b>HV yellow</b> — the only yellow jack on the enclosure, do not mix up its position.
tr: HV jakının içerideki ucuna somunu sıktıktan sonra <b>makaron geçir ama DARALTMA</b> — HV teli {0}'te bağlanacak (aşağıdaki ① ya da ② yöntemi); makaronu o zaman bağlantının üstüne çekip daraltacaksın.
en: After tightening the nut, <b>slide heat-shrink over the inner end of the HV jack but DO NOT SHRINK it</b> — the HV wire is connected in {0} (method ① or ② below); that is when you pull the heat-shrink over the joint and shrink it.
tr: <b>Jaka kablo nasıl bağlanır</b> (jakın arkasındaki metal saplamaya; bütün jaklarda aynı). Jakı panele tutan somunu kablo için kullanma — o somunu her sıktığında jak da döner. ① Pakette <b>lehim kulağı</b> (delikli, kulakçıklı ince pul) varsa: somun → kulak → ikinci somun; kabloyu kulağa lehimle, makaron geçir — en iyisi. ② Kulak yoksa: kabloyu ~{0} mm soy, telleri sıkıca bük ve <b>kalaylama</b>; yuvarlak uçlu kargaburunla halka yap, iki somunun arasına saplamanın çevresine <b>saat yönünde</b> sar (somunu sıktıkça halka kapanır), dış somunu sıkıca sık. Taşan tek tel kalmasın; somunun dışında kalan çıplak kısmı makaronla kapat. ③ Saplamada <b>tek somun</b> varsa o somun jakı tutuyor: <b>ikinci somun</b> gerekir — saplama M3 ise stoktaki M3 somun (MEK034), değilse hırdavattan saplamaya uyan somun. <b>Neden kalaysız:</b> kalay basınç altında zamanla akar, somun gevşer; {1} A'lik yolda gevşek bağlantı ısınır. Halka pabuç stokta yok ve gerekmez; almak istersen yalıtımsız pabucun borusunu sık ve lehimle (lehim boruda kalır, somunun altına girmez). Ertesi gün somunları bir kez daha sık.
en: <b>How to connect a cable to a jack</b> (to the metal stud at the back of the jack; the same for all jacks). Do not use the nut that holds the jack to the panel for the cable — every time you tighten it the jack turns too. ① If the pack has a <b>solder lug</b> (a thin washer with a hole and a tab): nut → lug → second nut; solder the cable to the lug, slide heat-shrink over it — the best option. ② Without a lug: strip the cable ~{0} mm, twist the strands tightly and <b>do not tin them</b>; make a loop with round-nose pliers and wrap it around the stud between two nuts <b>clockwise</b> (the loop closes as you tighten the nut), tighten the outer nut firmly. No stray strands; cover the bare part outside the nut with heat-shrink. ③ If the stud has <b>only one nut</b>, that nut holds the jack: you need a <b>second nut</b> — the M3 nut from stock (MEK034) if the stud is M3, otherwise a nut that fits the stud from a hardware store. <b>Why untinned:</b> under pressure solder slowly creeps and the nut loosens; on a {1} A path a loose joint heats up. Ring lugs are not in stock and not needed; if you want to buy some, crimp and solder the barrel of an uninsulated lug (the solder stays in the barrel, it does not go under the nut). Tighten the nuts once more the next day.
tr: <b>Kalın uçları ŞİMDİ hazırla (kutu boşken):</b> dört büyük jakın iç ucuna <b>≥{0} mm² pigtail</b> bağla (yukarıdaki yöntem; kalınlığı soyup ölçerek anla: çıplak iletken tek damarda ≥ {1} mm, çok damarlı demette ~{2} mm) ve <b>ucunu etiketle</b>. Boylar (kart A'nın çevresinden dolaşarak ölçüldü, {3}–{4} cm pay dahil):
en: <b>Prepare the heavy leads NOW (while the enclosure is empty):</b> connect a <b>≥{0} mm² pigtail</b> to the inner end of the four large jacks (method above; judge the gauge by stripping and measuring: bare conductor ≥ {1} mm for solid wire, ~{2} mm for a stranded bundle) and <b>label its end</b>. Lengths (measured going around board A, {3}–{4} cm slack included):
tr: • <b>YÜK {0}</b> → {1}'de bariyerin {2}. kutbuna — <b>{3} cm</b>
en: • <b>«YÜK» {0}</b> → to pole {2} of the barrier in {1} — <b>{3} cm</b>
tr: • <b>PİL {0}</b> → {1}'de Q1'in savağına — <b>{2} cm</b> (en uzun yol)
en: • <b>«PİL» {0}</b> → to Q1's drain in {1} — <b>{2} cm</b> (the longest run)
tr: • <b>PİL {0}</b> → {1}'de bariyerin {2}. kutbuna — <b>{3} cm</b>
en: • <b>«PİL» {0}</b> → to pole {2} of the barrier in {1} — <b>{3} cm</b>
tr: <b>Neden şimdi:</b> {0}'de kart A takılı olacak ve bu jakların arkasında yalnız <b>{1} mm</b> kör boşluk kalıyor; havya oraya girmiyor. Pigtail'leri kutunun ortasına doğru kıvır, {2}'de yalnız uçlarını vidalayacaksın.
en: <b>Why now:</b> in {0} board A will be fitted and there is only <b>{1} mm</b> of blind space behind these jacks; a soldering iron does not get in there. Bend the pigtails towards the middle of the enclosure, in {2} you only screw down their ends.
tr: Bu adımda taktığın jakların etiketlerini hemen yapıştır — <b>V</b> · <b>COM</b> · <b>HV ⚡</b> · <b>YÜK {0}</b> · <b>YÜK {1}</b> · <b>SKOP</b> · <b>PİL {2}</b> · <b>PİL {3}</b>; kalan etiketler {4}'de.
en: Stick on the labels of the jacks you fitted in this step right away — <b>V</b> · <b>COM</b> · <b>HV ⚡</b> · <b>«YÜK» {0}</b> · <b>«YÜK» {1}</b> · <b>«SKOP»</b> · <b>«PİL» {2}</b> · <b>«PİL» {3}</b>; the remaining labels in {4}.
tr: Kuşbakışı
en: Top view
tr: Jakların içerideki uçları birbirine değmiyor.
en: The inner ends of the jacks do not touch each other.
tr: Somunlar sıkı; jak elle dönmüyor.
en: The nuts are tight; the jack does not turn by hand.
tr: <span class='ano'>{0}</span> <b>PİL anahtarı, CAL jakı ve GÜÇ lambası</b>
en: <span class='ano'>{0}</span> <b>«PİL» switch, CAL jack and «GÜÇ» lamp</b>
tr: PİL — KTS102: paket (TP1 OUT+) → MT1. Kutunun TEK anahtarı (B58e): ESP32 ve ölçüm tarafı birlikte açılır. Şarj ederken KAPALI; USB'yi PC'ye takarken AÇIK.
en: «PİL» — KTS102: pack (TP1 OUT+) → MT1. The enclosure's ONLY switch (B58e): the ESP32 and the measurement side switch on together. OFF while charging; ON when plugging the USB into the PC.
tr: CAL jakı: devkit GPIO10 → {0} kΩ (R059) → jak. Skop kapısı ve kapalı kutu testinde CAL → SKOP kısa kablo.
en: CAL jack: devkit GPIO10 → {0} kΩ (R059) → jack. For the scope GATE and the closed-enclosure test, a short CAL → «SKOP» lead.
tr: GÜÇ lambası: +{0} rayı (klemens +, KL.+) → {1} kΩ (R060) → LED anodu; katot kart GND'ye. PASİF — ESP32'ye bağlanmaz. Akım ~{2} mA ve GND'ye GİRER ({3} çeker). LED'i −{4} rayına BAĞLAMA: regülatör o yönde akım veremez. Direnci LED'in bacağına lehimle, makaronla kapat; karta dokunma.
en: «GÜÇ» lamp: +{0} rail (terminal block +, KL.+) → {1} kΩ (R060) → LED anode; cathode to board GND. PASSIVE — not connected to the ESP32. Current ~{2} mA, flowing INTO GND ({3} sinks it). DO NOT connect the LED to the −{4} rail: the regulator cannot source current in that direction. Solder the resistor to the LED leg, cover it with heat-shrink; do not touch the board.
tr: Bu adımda takılanlar: <b>AÇ / KAPA</b> · <b>CAL</b> · <b>GÜÇ</b>. Hepsi <b>ÖN</b> duvara; somunlar dıştan sıkılır. <b>PİL</b> anahtarı (KTS102, {0} ayak) kutunun tek AÇ/KAPA'sı — ayakları yere doğru baksın (kablolar aşağı iner).
en: Fitted in this step: <b>«AÇ / KAPA»</b> · <b>CAL</b> · <b>«GÜÇ»</b>. All on the <b>FRONT</b> wall; nuts tightened from outside. The <b>«PİL»</b> switch (KTS102, {0} pins) is the enclosure's only on/off switch — pins pointing down (the cables run downwards).
tr: <b>Konumlar aşağıdaki çizimden ve delik tablosundan okunur</b>, metinden değil. Dizilimin mantığı (B59): <b>sol üst</b> AÇ/KAPA + GÜÇ lambası, <b>orta sıra</b> COM · V · HV (ölçüm probu COM'un yanından), <b>sağ üst</b> CAL · SKOP (patch kablo kısa), <b>alt sıra</b> PİL çifti solda, YÜK çifti sağda. Hepsi {0} mm ızgarada ve {1}., {2}., {3}. çubuk sıralarının ortasında.
en: <b>Read the positions from the drawing and the hole table below</b>, not from the text. The logic of the arrangement (B59): <b>top left</b> «AÇ / KAPA» + «GÜÇ» lamp, <b>middle row</b> COM · V · HV (the measuring probe next to COM), <b>top right</b> CAL · «SKOP» (short patch lead), <b>bottom row</b> the «PİL» pair on the left, the «YÜK» pair on the right. All on a {0} mm grid, in the middle of stick rows {1}, {2} and {3}.
tr: ⚠ <b>CAL jakının iç ucuna (lehim kulağı ya da saplama) makaron geçir.</b> Panelde en yakın komşusuna <b>{0} mm</b> var; komşuları V ve SKOP ve onlarda {1} V'a kadar gerilim bulunabiliyor, panelin arkası da kalabalık. Makaron yoksa izole bant sar.
en: ⚠ <b>Slide heat-shrink over the inner end of the CAL jack (solder lug or stud).</b> Its nearest neighbour on the panel is <b>{0} mm</b> away; its neighbours are V and «SKOP», which can carry up to {1} V, and the back of the panel is crowded. Without heat-shrink, wrap it in insulating tape.
tr: <b>GÜÇ lambası (LED1):</b> {0} mm yeşil LED'i ön duvarın üst sırasındaki Ø{1} deliğe <b>dışarıdan içeri</b> it (sıkı geçer; gevşekse deliğin içine bir damla sıcak silikon). ⚠ <b>Bacak yönünü şimdi işaretle:</b> <b>uzun bacak = artı (anot)</b>, gövdenin yanındaki düzlük kısa bacağın (katot) tarafıdır. LED takılınca hangisinin uzun olduğu artık görünmüyor — kısa bacağı kıvır ya da üstüne makaron geçir. Kablolaması {2}'te: uzun bacak {3} kΩ üzerinden +{4} rayına, kısa bacak kart GND'ye.
en: <b>«GÜÇ» lamp (LED1):</b> push the {0} mm green LED <b>from outside in</b> into the Ø{1} hole in the top row of the front wall (tight fit; if loose, a drop of hot glue inside the hole). ⚠ <b>Mark the leg orientation now:</b> <b>long leg = positive (anode)</b>, the flat on the side of the body is on the short leg's (cathode) side. Once the LED is fitted you can no longer see which leg is longer — bend the short leg or slide heat-shrink over it. Wiring in {2}: long leg through {3} kΩ to the +{4} rail, short leg to board GND.
tr: Arka duvara bu adımda takılan bir şey yok: ŞARJ ve USB yuvaları boş kalır (Type-C fişleri doğrudan modüllerin soketine girer), havalandırma delikleri açık.
en: Nothing goes on the back wall in this step: the «ŞARJ» and USB slots stay empty (the Type-C plugs go straight into the modules' sockets), the ventilation holes are open.
tr: Anahtar iki konumda net oturuyor.
en: The switch clicks firmly into both positions.
tr: CAL jakı elle dönmüyor; LED dışarıdan bakınca delikte oturuyor.
en: The CAL jack does not turn by hand; seen from outside the LED sits in its hole.
tr: <span class='ano'>{0}</span> <b>Şarj modülünü (TP1) kart A'dan ÖNCE tak</b>
en: <span class='ano'>{0}</span> <b>Fit the charging module (TP1) BEFORE board A</b>
tr: TP4056 korumalı (DW01+FS8205): B± pakete (iki hücre paralel), OUT± yüke. Rprog fabrika {0} kΩ ({1} A, hücre başına ~{2} A). Yük altında şarj etme: PİL KAPALI.
en: TP4056 protected (DW01+FS8205): B± to the pack (two cells in parallel), OUT± to the load. Rprog factory {0} kΩ ({1} A, ~{2} A per cell). Do not charge under load: «PİL» OFF.
tr: <b>Neden şimdi:</b> TP4056 kart A'nın arka boş şeridinin <b>altına</b> giriyor (kart tabanına {0} mm kalıyor). Kart takılınca {1} mm'lik modül duvarla kart arasındaki {2} mm'lik aralıktan indirilip yatırılamaz, uçtaki pedlerine de havya girmez.
en: <b>Why now:</b> the TP4056 goes <b>under</b> the empty back strip of board A ({0} mm to the board's underside). Once the board is in, the {1} mm module cannot be lowered and laid flat through the {2} mm gap between wall and board, and a soldering iron cannot reach its end pads.
tr: <b>Önce tezgahta lehimle:</b> modülün <b>B+, B−, OUT+, OUT−</b> pedlerine ~{0} cm {1} mm² kablo (artılar kırmızı, eksiler siyah), uçlarını etiketle: B+ / B− / OUT+ / OUT−. IN+/IN− boş kalır (şarj Type-C'den gelir). Uçlar {2}'te sigortalara ve PİL anahtarına bağlanacak.
en: <b>Solder it at the bench first:</b> ~{0} cm of {1} mm² wire to the module's <b>B+, B−, OUT+, OUT−</b> pads (positives red, negatives black), label the ends: B+ / B− / OUT+ / OUT−. IN+/IN− stay empty (charging comes from the Type-C). The ends are connected to the fuses and the «PİL» switch in {2}.
tr: <b>Raf — dört çubuk parçası</b> (hepsi {0} mm genişlik, enine kesim): alt kat iki {1} mm, üst kat bir {2} mm, dayanak bir {3} mm. Alt kattaki iki parçayı aralarında <b>{4} mm kanal</b> kalacak şekilde koy, üst katı ikisinin üstüne japonla yapıştır. Dayanağı üst katın duvardan uzak ucuna, <b>uzun kenarı üstünde dik</b> yapıştır (modül bu kenara yaslanacak).
en: <b>Shelf — four stick pieces</b> (all {0} mm wide, cut across): bottom layer two {1} mm, top layer one {2} mm, stop one {3} mm. Place the two bottom pieces with a <b>{4} mm channel</b> between them, glue the top layer on both with CA glue. Glue the stop to the end of the top layer away from the wall, <b>upright on its long edge</b> (the module will rest against this edge).
tr: <b>Hangi oval:</b> önden (jak tarafından) bakınca <b>solda</b> olan — {0}'de iç yüzüne ŞARJ yazdın; öbürü (USB) ESP32'nin. Karıştırırsan ESP32 kart A'nın altına düşer ve kart oturmaz.
en: <b>Which oval:</b> the one on the <b>left</b> seen from the front (the jack side) — in {0} you wrote «ŞARJ» on its inside face; the other one (USB) is the ESP32's. Mix them up and the ESP32 ends up under board A and the board does not sit down.
tr: Rafı ŞARJ yuvasının tam önüne, tabana <b>sıcak silikonla</b> yapıştır: üst katın ucu duvara değsin, yuva rafın ortasına gelsin (konum tabloda). Yuvanın arkasında iç kat çubuğu kısa, raf o {0} mm'lik girintiye de girebilir — sorun değil.
en: Glue the shelf to the base right in front of the «ŞARJ» slot <b>with hot glue</b>: the end of the top layer touches the wall, the slot is centred on the shelf (position in the table). Behind the slot the inner layer stick is short, so the shelf can also go into that {0} mm recess — not a problem.
tr: <b>Modülü (TP1) kablo bağıyla tuttur:</b> kanaldan bir kablo bağı geçir; modülü rafa koy, Type-C soketi yuvaya girsin, uzak kenarı dayanağa yaslansın (fişi takarken itme kuvvetini dayanak alır, bağ değil). Bağı modülün <b>ortasından</b> (soketten ~{0} mm), entegrenin üstünden geçirip sık — LED'leri ve uçtaki pedleri kapatmasın. Modülde montaj deliği yok — <b>vida/cıvata YOK</b>.
en: <b>Secure the module (TP1) with a cable tie:</b> pass a cable tie through the channel; put the module on the shelf, the Type-C socket into the slot, the far edge against the stop (the stop takes the pushing force when you plug in, not the tie). Run the tie over the <b>middle</b> of the module (~{0} mm from the socket), over the IC, and tighten — it must not cover the LEDs or the end pads. The module has no mounting hole — <b>NO screws/bolts</b>.
tr: Dört kablonun uçlarını duvarla kart A arasındaki aralıktan yukarı al, duvara maskeleme bandıyla geçici tuttur — kart A takılırken ezilmesinler.
en: Bring the ends of the four wires up through the gap between the wall and board A, hold them to the wall temporarily with masking tape — so they are not crushed when board A goes in.
tr: Arka duvar — iç yüzdeki parçalar (arkadan bakış; delikler dıştan)
en: Back wall — parts on the inside face (seen from behind; holes from outside)
tr: Ön duvar — iç yüzdeki parçalar
en: Front wall — parts on the inside face
tr: Duvara asılı parçalar — konumlar (iç koordinat, önden bakınca soldan; arka duvar için arkadan bakınca sağdan)
en: Parts hung on the wall — positions (inner coordinates, from the left seen from the front; for the back wall, from the right seen from behind)
tr: x (sol kenar)
en: x (left edge)
tr: z (alt kenar)
en: z (bottom edge)
tr: en × yük × derin
en: w × h × d
tr: {0} × {1} × {2} (ölçüldü). Arka duvarın iç yüzüne SICAK SİLİKONLA yapıştırılır (kullanıcı kararı {3}-{4}-{5}, cıvata yok): yuvanın tabanına boydan boya iki şerit, duvara {6} s bastır. Sökülebilir: ısı tabancasıyla ısıt ya da derze izopropil alkol damlat, maket bıçağıyla kaldır. Hücre yuvadan çıkar. Hücre başlı (PWR005) — yaylı yuvada başlık temas eder; yalıtım contası MEK025.
en: {0} × {1} × {2} (measured). Glued to the inside face of the back wall WITH HOT GLUE (user decision {3}-{4}-{5}, no bolts): two beads along the full length of the holder's base, press against the wall {6} s. Removable: warm it with a heat gun or drip isopropyl alcohol into the joint, lift with a utility knife. The cell comes out of the holder. Button-top cell (PWR005) — the button touches in the spring holder; insulating ring MEK025.
tr: YUVA1 ile aynı: arka duvarın iç yüzüne SICAK SİLİKONLA yapıştırılır, cıvata yok. Sökülebilir: ısı tabancası ya da izopropil alkol, maket bıçağıyla kaldır. Yuva {0} mm (ölçüldü); üstünde kapağa pay kalır, {1} kontrol eder.
en: Same as YUVA1: glued to the inside face of the back wall WITH HOT GLUE, no bolts. Removable: heat gun or isopropyl alcohol, lift with a utility knife. Holder {0} mm (measured); there is room for the lid above it, {1} checks it.
tr: Kart RAF gibi yatay ({0} × {1} × {2} ölçüldü, soket kart kenarından {3} mm dışarı): soket ŞARJ yuvasına girer. Kart A'nın arka boş şeridinin ALTINDA kalır — bu yüzden kart A'dan önce ({4}), kabloları tezgahta lehimlenmiş olarak takılır. Kanallı {5} parçalı çubuk rafının üstüne oturur, uzak kenarı dayanağa yaslanır; tek kablo bağı kanaldan geçip modülün ortasını sarar. Modülde montaj deliği yok, vida yok. Sökülebilir: kart A'yı {6} vidasından kaldır, bağı kes.
en: The board lies horizontally like a SHELF ({0} × {1} × {2} measured, socket {3} mm beyond the board edge): the socket goes into the «ŞARJ» slot. It sits UNDER the empty back strip of board A — that is why it is fitted before board A ({4}), with its wires soldered at the bench. It sits on the channelled {5}-piece stick shelf, far edge against the stop; one cable tie runs through the channel and wraps the middle of the module. The module has no mounting hole, no screws. Removable: lift board A off its {6} screws, cut the tie.
tr: Arka duvarın iç yüzüne düz (A'nın boş arka şeridinin üstü), sıcak silikonla — PCB'nin arkasından, çipin ve bobinin üstüne değil. OUT pedleri SOLA (F0 ve B0505S). Trimpot içe bakar, ayar kapak açıkken. Derze izopropil alkol damlatıp plastik kartla kaldırarak sökülür.
en: Flat on the inside face of the back wall (above A's empty back strip), with hot glue — on the back of the PCB, not on the chip and the inductor. OUT pads to the LEFT (F0 and B0505S). Trimpot facing in, adjusted with the lid open. Removed by dripping isopropyl alcohol into the joint and lifting with a plastic card.
tr: Arka duvarın en alt sırasına, TP4056 rafının sağına (konum listesinde): iki klips + en fazla {0} mm'lik plaket şeridi, arkasından sıcak silikonla. Sigorta içe çekilerek değişir. İzopropil alkolle sökülür.
en: On the bottom row of the back wall, to the right of the TP4056 shelf (in the position list): two clips + a perfboard strip of at most {0} mm, hot-glued from behind. The fuse is changed by pulling it inwards. Removed with isopropyl alcohol.
tr: Arka duvarın SAĞ ALT köşesine, en alt sıraya, aynı yöntemle (klips şeridi, sıcak silikon). Çıkışı arka duvar boyunca F1P'nin çıkış klipsine (= TP4056 B+). İzopropil alkolle sökülür.
en: In the BOTTOM RIGHT corner of the back wall, on the bottom row, the same way (clip strip, hot glue). Its output runs along the back wall to F1P's output clip (= TP4056 B+). Removed with isopropyl alcohol.
tr: MT1'in üstüne, aynı yöntemle (sıcak silikon, PCB'nin arkasından); IN pedleri SOLA (B0505S ve {0} µF). Girişi B0505S'in yalıtılmış {1} V'u, çıkışı {2} V iç klemensine. İzopropil alkolle sökülür.
en: Above MT1, the same way (hot glue, on the back of the PCB); IN pads to the LEFT (B0505S and {0} µF). Its input is the B0505S's isolated {1} V, its output goes to the {2} V internal terminal block. Removed with isopropyl alcohol.
tr: MT2'nin soluna, bacaklar aşağı; dört bacağına ince tel lehimli ve makaronlu. Gövdesinden sıcak silikonla duvara; izopropil alkolle sökülür. Giriş ({0} +Vin, {1} −Vin) ve çıkış ({2} −Vout, {3} +Vout) tarafı hiçbir telle birleşmez.
en: To the left of MT2, pins down; thin wire soldered to all four pins and heat-shrunk. Hot-glued to the wall by its body; removed with isopropyl alcohol. The input side ({0} +Vin, {1} −Vin) and the output side ({2} −Vout, {3} +Vout) are not joined by any wire.
tr: MT2'nin üstüne, yatık (gövde x yönünde), gövdesinden sıcak silikonla. Bacakları MT2'nin giriş pedlerine lehimli — ⚠ Elektrolitik: &lt;b&gt;şeritli bacak EKSİ&lt;/b&gt; (MT2 IN−), uzun bacak artı (MT2 IN+). İzopropil alkol ve iki bacağın lehimi sökülerek sökülür.
en: Above MT2, lying down (body along x), hot-glued by its body. Its legs are soldered to MT2's input pads — ⚠ Electrolytic: &lt;b&gt;the striped leg is NEGATIVE&lt;/b&gt; (MT2 IN−), the long leg positive (MT2 IN+). Removed with isopropyl alcohol and by desoldering both legs.
tr: Arka duvarın sol ucuna, MT1'in soluna ve B0505S'in altına (konum listesinde): iki klips + en fazla {0} mm'lik plaket şeridi (FUS009 tek gövde değil), şeridin arkasından sıcak silikonla. İçine {1} A hızlı cam sigorta (FUS003) — {2}'e kadar TAKMA. Sigorta içe doğru çekilerek çıkar. İzopropil alkolle sökülür.
en: At the left end of the back wall, to the left of MT1 and below the B0505S (in the position list): two clips + a perfboard strip of at most {0} mm (FUS009 is not a single body), hot-glued from the back of the strip. Holds a {1} A fast glass fuse (FUS003) — DO NOT FIT it before {2}. The fuse comes out by pulling it inwards. Removed with isopropyl alcohol.
tr: B0505S'in üstüne, tabanından sıcak silikonla (PCB klemensinde montaj deliği yok). Vidalar içe: {0}'te MT2'nin çıkışı ve kartın {1} V telleri buraya vidalanır. Hangi vidanın + olduğunu kalemle yaz. İzopropil alkolle sökülür.
en: Above the B0505S, hot-glued by its base (the PCB terminal block has no mounting hole). Screws facing in: in {0} MT2's output and the board's {1} V wires are screwed in here. Write with a pen which screw is +. Removed with isopropyl alcohol.
tr: Type-C fişi dışarıdan ŞARJ yuvasına tam giriyor; fişi iterken modül geri kaçmıyor.
en: A Type-C plug goes fully into the «ŞARJ» slot from outside; the module does not slide back when you push the plug.
tr: Modül rafta oynamıyor; kablolar etiketli ve kart A'nın ayak yerlerini kapatmıyor.
en: The module does not move on the shelf; the wires are labelled and do not cover board A's foot positions.
tr: <span class='ano'>{0}</span> <b>Ayakları kartla hizala, gömme somun</b>
en: <span class='ano'>{0}</span> <b>Align the feet with the board, embedded nuts</b>
tr: Yerleşim planı her kartın köşesinde <b>{0}×{1} delik</b> boş bıraktı: bu dört deliğin ortasına Ø{2} del (A'da dört köşe, B'de çapraz iki köşe).
en: The layout plan left <b>{0}×{1} holes</b> empty in each board's corner: drill Ø{2} in the middle of these four holes (four corners on A, two diagonal corners on B).
tr: Kartın yeri tabloda (telli kenar öne). Ayak bloğu kartın kenarından ~{0} mm taşar, normal.
en: The board's position is in the table (wired edge to the front). The foot block overhangs the board's edge by ~{0} mm, that is normal.
tr: Ayak bloğu: <b>{0} parça çubuk üst üste = {1} mm</b> (kartın altındaki atlama telleri için bu yükseklik ÖLÇÜLDÜ). <b>{2}. kat Ø{3}</b> (vida girer), <b>{4}. ve {5}. kat Ø{6} = somun cebi</b> ({7} mm derin: M3 somun {8} mm, tam gömülür ve lamine düz kalır), <b>{9}. kat Ø{10}</b> — vidanın ucu oraya çıkar, altındaki katlar delinmez, sadece yükseltir; tahtaya dayanmaz. Cep çapı neden Ø{11}: M3 somun köşeden köşeye {12} mm, daha darına girmez.
en: Foot block: <b>{0} stick pieces stacked = {1} mm</b> (this height was MEASURED for the jumper wires under the board). <b>Layer {2} Ø{3}</b> (the screw goes in), <b>layers {4} and {5} Ø{6} = nut pocket</b> ({7} mm deep: an M3 nut is {8} mm, fully embedded and the laminate stays flat), <b>layer {9} Ø{10}</b> — the screw tip comes out there, the layers below are not drilled, they only add height; the screw does not bottom out on wood. Why the pocket is Ø{11}: an M3 nut is {12} mm across the corners, it does not fit anything narrower.
tr: <b>Somunu cebe koyarken dış yüzüne bir damla japon</b> (japon, somunun DIŞ yüzüne — dişine değil) — cep yuvarlak olduğu için dönmeyi tek başına engellemez; dönen somun vidayı ne sıkar ne söker. Somun kutuda kalıcıdır, sorun değil: sökülmesi gereken şey kart, somun değil.
en: <b>When putting the nut into the pocket, a drop of CA glue on its outer face</b> (CA on the nut's OUTER face — not on its thread) — the pocket is round, so on its own it does not stop the nut from turning; a turning nut neither tightens nor releases the screw. The nut stays in the enclosure for good, that is fine: what needs to come off is the board, not the nut.
tr: <b>Delikler nasıl üst üste gelir (sıra önemli):</b> ① Üstteki <b>{0} katı</b> üst üste koy, mandalla/bantla sık, hepsini birden <b>tek seferde Ø{1}</b> del — dört delik böyle eş eksenli çıkar, elle işaretleme yok. ② Yandan kurşun kalemle bir <b>hizalama çizgisi</b> çek (katlar geri aynı sırayla ve aynı yöne gelsin). ③ Katları ayır; {2}. ve {3}. katın deliğini Ø{4}'e büyüt (Ø{5} kılavuz matkabı ortalar), {6}. katı Ø{7}'e getir. ④ Önce {8}. + {9}. + {10}. katı japonla yapıştır — cep şimdi üstü açık bir kuyu. ⑤ Somunu kuyuya bırak (Ø{11} kuyuda {12} mm somun kendiliğinden ortalanır), dış yüzüne damla japon, üstüne {13}. katı çizgiye göre koy ve bastır. ⑥ <b>Japon kurumadan M3 vidayı sok-çıkar:</b> girmiyorsa katlar kaymıştır, hemen düzelt. ⑦ Kalan alt katları (yükseltici, deliksiz) bu başlığın altına yapıştır.
en: <b>How the holes line up (order matters):</b> ① Stack the top <b>{0} layers</b>, clamp them with a peg/tape, drill all of them <b>at once Ø{1}</b> — that way the four holes come out coaxial, no marking by hand. ② Draw an <b>alignment line</b> on the side with a pencil (so the layers go back in the same order and the same way round). ③ Separate the layers; enlarge the hole in layers {2} and {3} to Ø{4} (the Ø{5} pilot centres the drill), bring layer {6} to Ø{7}. ④ First glue layers {8} + {9} + {10} with CA glue — the pocket is now a well open at the top. ⑤ Drop the nut into the well (a {12} mm nut centres itself in a Ø{11} well), a drop of CA glue on its outer face, put layer {13} on top following the line and press. ⑥ <b>Before the CA cures, screw an M3 screw in and out:</b> if it does not go in, the layers have shifted, fix it at once. ⑦ Glue the remaining lower layers (riser, no holes) under this head.
tr: <b>Tabana yapıştırma — blok karta vidalıyken:</b> blokları M3 vidalarla <b>karta vidala</b>, kartı bloklarıyla birlikte tablodaki yere koy, blokların kartın dışına taşan kenarlarına sıcak silikonla fileto çek; silikon soğuyunca vidaları sök, kartı kaldır. Hizayı vida verir: kalemle işaretleyip tek tek yapıştırırsan {0}–{1} mm kayma vidayı somuna sokmaz. <b>Kart B için iki blok aynı yöntemle ama {2} kat ({3} mm)</b> — B'nin altında tel yok, alçak kalıyor.
en: <b>Gluing to the base — with the blocks screwed to the board:</b> <b>screw</b> the blocks <b>to the board</b> with M3 screws, put the board with its blocks in the place from the table, run a hot-glue fillet along the edges of the blocks that stick out beyond the board; once the glue has cooled, take the screws out and lift the board. The screws give the alignment: if you mark with a pen and glue them one by one, a {0}–{1} mm shift stops the screw from reaching the nut. <b>For board B, two blocks the same way but {2} layers ({3} mm)</b> — there are no wires under B, it stays low.
tr: İzometrik
en: Isometric
tr: ön ve sol duvar saydam çizildi (içeriyi görmek için)
en: front and left walls drawn transparent (to see inside)
tr: Bu adımdaki parçaların yeri — sol-arka iç köşeden (mm)
en: Positions of the parts in this step — from the back-left inside corner (mm)
tr: en × boy
en: w × d
tr: yük
en: height
tr: Kartı koy, M3 vida dört delikten de somuna giriyor.
en: Put the board in, the M3 screw reaches the nut through all four holes.
tr: Kart sallanmıyor, altı hiçbir yere değmiyor.
en: The board does not rock, its underside touches nothing.
tr: <span class='ano'>{0}</span> <b>Ana kartı vidala</b>
en: <span class='ano'>{0}</span> <b>Screw down the main board</b>
tr: <b>YÖN ÖNEMLİ — kare kart dört türlü oturur, ayaklar simetrik olduğu için yanlış yön de vidalanır:</b> tellerin sıra hâlinde çıktığı uzun kenar (<b>A–C sütunları</b>: V, COM, SKOP, HV alt, Kelvin/yıldız ve {0} V telleri) <b>ön panele, jaklara</b> baksın — kartın <b>A1 köşesi (ön-sol)</b> kutunun o köşesine gelir. Bu yönde J5 başlığı (ESP32 kablosu) kartın arka yarısında kalır.
en: <b>ORIENTATION MATTERS — a square board sits four ways, and since the feet are symmetric the wrong way can be screwed down too:</b> the long edge where the wires come out in a row (<b>columns A–C</b>: V, COM, «SKOP», HV low, Kelvin/star and the {0} V wires) <b>faces the front panel, the jacks</b> — the board's <b>A1 corner (front-left)</b> goes into that corner of the enclosure. In this orientation header J5 (ESP32 cable) is in the back half of the board.
tr: Kartın arka şeridinin altında TP4056 var: dört kablosu ayak ya da kart altında ezilmesin.
en: The TP4056 is under the board's back strip: its four wires must not be crushed under a foot or the board.
tr: Kart A'yı ayaklara oturt, dört M3x10 vidayla tuttur (pul ile). <b>Yapıştırma.</b>
en: Seat board A on the feet, fasten it with four M3x10 screws (with washers). <b>No glue.</b>
tr: Vidayı fazla sıkma; plaket çatlar.
en: Do not overtighten the screws; the board cracks.
tr: Kart tek parça çıkıyor (dene: vidaları sök, tak).
en: The board comes out in one piece (try it: take the screws out, put them back).
tr: <span class='ano'>{0}</span> <b>ESP32, kart B ve altlıklar</b>
en: <span class='ano'>{0}</span> <b>ESP32, board B and spacers</b>
tr: <b>ESP32 — kızakta; önce hizala, sonra yapıştır.</b> Devkit pinleri yukarı, soketli ucu arka duvara ~{0} mm. <b>Hangi oval:</b> önden (jak tarafından) bakınca <b>sağda</b> olan — iç yüzünde USB yazıyor; öbüründe {1}'da taktığın şarj modülü var. Dışarıdan bir Type-C kabloyu o ovalden devkit'in <b>COM yazan</b> soketine tak ve <b>takılı bırak</b>: devkit'in yerini kablo belirler, aşağıdaki parçaları ona dayayarak yapıştırırsın. Fiş girmiyorsa devkit'i fiş girene kadar yana kaydır — önden bakınca sağa <b>{2} mm</b>, sola yalnız <b>{3} mm</b> yer var (solda kart A'nın arka-sağ ayağı); daha fazlası gerekirse devkit'i yerinde bırak, ovali COM soketine doğru eğeyle genişlet.
en: <b>ESP32 — in the cradle; align first, then glue.</b> Devkit pins up, socket end ~{0} mm from the back wall. <b>Which oval:</b> the one on the <b>right</b> seen from the front (the jack side) — it says USB on its inside face; the other one holds the charging module you fitted in {1}. From outside, plug a Type-C cable through that oval into the devkit's socket <b>marked COM</b> and <b>leave it plugged in</b>: the cable sets the devkit's position, you glue the parts below against it. If the plug does not go in, slide the devkit sideways until it does — seen from the front there is <b>{2} mm</b> of room to the right, only <b>{3} mm</b> to the left (on the left is board A's back-right foot); if you need more, leave the devkit in place and file the oval out towards the COM socket.
tr: <b>Altlık</b> dört parça: iki sıra, her sıra ortadan bölük, aradaki <b>{0} mm kanal</b> kablo bağının geçtiği yer. <b>Kanal, iki yanındaki pinlerde dupont ucu OLMAYAN bir hizaya gelmeli</b>: bağ {1} mm, pinlerin arası ~{2} mm — bağ pinlerin arasından geçemez, BOŞ pinlerin tepesinden geçer. Kullanılacak pinler: 3V3, 5V, GND, GPIO4, GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10. Devkit'in üstündeki pin yazılarına bak, iki yanda da boş {3}–{4} pinlik hizayı bul; kanal orada değilse parça boylarını kaydır (arka + {5} + ön = {6} mm). Altlığı tabloda yazan yere tabana sıcak silikonla yapıştır (±{7} mm tolerans; rayların altında yer kalsın).
en: <b>Spacer</b> four pieces: two rows, each split in the middle; the <b>{0} mm channel</b> between them is where the cable tie runs. <b>The channel must line up with pins that have NO dupont connector on either side</b>: the tie is {1} mm, the pins are ~{2} mm apart — the tie cannot pass between pins, it passes over the tops of EMPTY pins. Pins in use: 3V3, 5V, GND, GPIO4, GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10. Look at the pin labels on the devkit, find a row of {3}–{4} empty pins on both sides; if the channel is not there, shift the piece lengths (back + {5} + front = {6} mm). Hot-glue the spacer to the base where the table says (±{7} mm tolerance; leave room under the rails).
tr: <b>Kızak</b> — hepsi japonla altlığın üstüne, devkit yerinde ve kablo COM'da takılıyken (devkit'in kenarına bir kat kâğıt sar: hem {0} mm pay verir hem japonu devkit'ten uzak tutar): ① <b>Yan raylar</b> — {1} mm'lik enine şeritler, uzun kenarı üstünde dik; iki uzun kenara ikişer tane, <b>kanal hizasında ray yok</b> (bağ oradan çıkar). ② <b>Omuz takozları</b> — bir şeridi ikiye böl ({2} + {3} mm); anten ucunda, <b>anten çıkıntısının iki yanında</b> kartın omuzlarına daya. Aralarında en az <b>{4} mm</b> boşluk kalsın: çıkıntı ~{5} mm ve ortada — takozlar ANTENE DEĞMEZ, USB takılırken itme kuvvetini kartın omuzları taşır. Arka tarafı arka duvar tutar (çekerken devkit en çok {6} mm geri gider).
en: <b>Cradle</b> — everything CA-glued on top of the spacer, with the devkit in place and the cable plugged into COM (wrap a layer of paper around the devkit's edge: it gives {0} mm of play and keeps the CA glue away from the devkit): ① <b>Side rails</b> — {1} mm strips cut across, upright on their long edge; two on each long side, <b>no rail where the channel is</b> (the tie comes out there). ② <b>Shoulder blocks</b> — split one strip in two ({2} + {3} mm); at the antenna end, rest them against the board's shoulders <b>on either side of the antenna tab</b>. Leave at least <b>{4} mm</b> between them: the tab is ~{5} mm and in the middle — the blocks DO NOT TOUCH THE ANTENNA, the board's shoulders take the pushing force when plugging in the USB. The back wall holds the back end (when pulling, the devkit moves back {6} mm at most).
tr: Japon kuruyunca kabloyu çıkar, <b>kablo bağını</b> kanaldan geçir: devkit'in altından, iki yandaki boş pinlerin tepesinden, üstte kilitle. Devkit oynamayacak kadar sık, kartı eğmeden; bağ dupont ucuna, USB soketlerine ve BOOT/RESET düğmelerine basmasın. <b>Sökmek:</b> bağı kes, telleri çek, devkit yukarı çıkar — kızak yerinde kalır, geri takınca devkit kendi yerine oturur.
en: Once the CA has cured, unplug the cable and pass the <b>cable tie</b> through the channel: under the devkit, over the tops of the empty pins on both sides, locked on top. Tight enough that the devkit does not move, without bending the board; the tie must not press on a dupont connector, the USB sockets or the BOOT/RESET buttons. <b>To remove:</b> cut the tie, pull off the wires, the devkit lifts out — the cradle stays in place, put back, the devkit drops into its own spot.
tr: <b>Kart B'yi takmadan önce kapla.</b> Zincirin tamamı ({0} → {1} V) bu kartta: iki yüzü de {2}–{3} ince kat tırnak cilası/konformal lak. T_HV ve T_N6 tellerini ÖNCE lehimle, sonra lehim noktalarını da kapla. Ayrıntı ve kaplanmayacak yerler: "Yalıtkan kaplama" bölümü.
en: <b>Coat board B before fitting it.</b> The whole divider chain ({0} → {1} V) is on this board: {2}–{3} thin coats of nail varnish/conformal coating on both faces. Solder the T_HV and T_N6 wires FIRST, then coat the solder points too. Details and areas not to coat: the "Insulating coating" section.
tr: Kart B'yi ayaklarına vidala. <b>YÖN ÖNEMLİ — dört türlü takılabilir:</b> kartın <b>A1 köşesi (ön-sol)</b> kutunun o köşesine baksın. Bu yönde {0} V'luk giriş düğümü kutudaki her iletkenden en uzakta kalıyor <i>ve</i> HV kablosu en kısa ({1} mm) oluyor; yanlış yön ikisini birden kötüleştirir.
en: Screw board B onto its feet. <b>ORIENTATION MATTERS — it can be fitted four ways:</b> the board's <b>A1 corner (front-left)</b> faces that corner of the enclosure. In this orientation the {0} V input node stays furthest from every conductor in the enclosure <i>and</i> the HV cable is the shortest ({1} mm); the wrong orientation makes both worse.
tr: USB-C fişi yuvadan girip sokete oturuyor.
en: A USB-C plug goes through the slot and seats in the socket.
tr: Kart B ile kart A arasındaki tel gergin değil.
en: The wire between board B and board A is not taut.
tr: <span class='ano'>{0}</span> <b>Şönt demetini tezgahta lehimle</b>
en: <span class='ano'>{0}</span> <b>Solder the shunt harness at the bench</b>
tr: Kutuya <b>{0} mΩ {1} A şönt (R042)</b> takılır. Veri sayfası (YSR serisi): tek parça <b>manganin</b> tel Ø{2} mm, {3} mΩ ±%{4}, <b>{5} A</b>, bacaklar arası {6} ± {7} mm, bacaklardaki <b>basık yerin</b> (boncuk) altında bacak yalnız {8} mm. Aynı kutudaki öbür {9} mΩ'u (R043, akımı yazmayan) <b>KULLANMA</b>: veri sayfası genel katalog, alaşımı belirsiz (bakır-nikel olabilir, ±{10} ppm/°C) — {11} A'de şönt ~{12} °C ısınır, okuma bakır-nikelde ~%{13}, manganinde ~%{14} kayar. {15} mΩ (R044) {16} A'de kalıyor ama {17} kat ince okur — mA işleri için yedek; klemens vidasıyla değişir. Kalın yük kabloları bacağa LEHİMLENMEZ: bacaklar XP128 {18} mm klemensin (CON064) iki kutbuna — aralık zaten {19} mm, <b>önce bükmeden dene</b>, girmezse hafif bük; kalın kablolar XP128'e de girmez, <b>bariyer klemenste</b> (HB950) birleşir ve XP128'in her kutbuna tek köprü gider ({20}, {21}). Şöntün hangi bacağı RS.1 (YÜK {22} tarafı) hangisi RS.2 (YÜK {23}) — işaretle.
en: The enclosure gets a <b>{0} mΩ {1} A shunt (R042)</b>. Datasheet (YSR series): a single piece of <b>manganin</b> wire Ø{2} mm, {3} mΩ ±{4}%, <b>{5} A</b>, {6} ± {7} mm between legs, below the <b>crimp</b> (bead) on the legs only {8} mm of leg. DO NOT USE the other {9} mΩ in the same storage box (R043, no current rating printed): its datasheet is a generic catalogue and the alloy is unknown (it may be copper-nickel, ±{10} ppm/°C) — at {11} A the shunt heats up ~{12} °C, and the reading drifts ~{13}% with copper-nickel, ~{14}% with manganin. The {15} mΩ (R044) stays at {16} A but reads {17} times finer — the spare for mA work; it is swapped with the terminal screws. The heavy load cables are NOT SOLDERED to the legs: the legs go into the two poles of the XP128 {18} mm terminal block (CON064) — the spacing is already {19} mm, <b>try it before bending</b>, bend slightly if it does not fit; the heavy cables do not fit the XP128 either, they join at the <b>barrier terminal block</b> (HB950) and a single bridge goes to each XP128 pole ({20}, {21}). Mark which shunt leg is RS.1 («YÜK» {22} side) and which RS.2 («YÜK» {23}).
tr: <b>Kelvin telleri</b> = akım taşımayan iki ince ölçüm teli: şöntün gerilimini, klemens temasının direnci (birkaç mΩ — şöntün kendisi kadar) karışmadan okur. Onları bacaklardaki <b>basık yerin kendisine</b> lehimle: veri sayfası ölçüm noktasını orada gösteriyor, basığın altındaki {0} mm'lik bacak klemense girecek — onu çıplak bırak, vidaya lehim/temas YOK. Lehim yeri {1} mm kayarsa şöntün görünen değeri ~%{2} değişir; {3}'deki kalibrasyon bunu düzeltir. <b>Lehim:</b> havya ≤ {4} °C, her lehimde ≤ {5}–{6} s (veri sayfası {7} °C / {8} s'yi sınıyor); önce teli kalayla, flux kullan. <b>Lehimlere sıcak silikon SÜRME</b> — şönt tam akımda ~{9} °C ısınır, silikon yumuşar ve şöntün soğumasını keser; gerilmeyi {10}'deki kablo bağı alır, istersen lehimin üstüne makaron. Kelvin çifti S+ (RS.1) ve S− (RS.2) burgulu, yıldız GND RS.2'ye S− ile <b>aynı noktaya</b>. Teller ~{11} cm (kutuda şöntten kart A'nın ön kenarına ~{12} cm). Üç telin ucuna {13}'lü <b>dişi header</b> (CON018'den kes).
en: <b>Kelvin wires</b> = two thin sense wires that carry no current: they read the shunt voltage without the contact resistance of the terminal block (a few mΩ — as much as the shunt itself) mixing in. Solder them to <b>the crimp itself</b> on the legs: the datasheet shows the measuring point there; the {0} mm of leg below the crimp goes into the terminal block — leave it bare, NO solder/contact at the screw. If the solder point moves {1} mm, the shunt's apparent value changes ~{2}%; the calibration in {3} corrects that. <b>Soldering:</b> iron ≤ {4} °C, ≤ {5}–{6} s per joint (the datasheet limits it to {7} °C / {8} s); tin the wire first, use flux. <b>DO NOT PUT hot glue on the joints</b> — at full current the shunt heats up ~{9} °C, the glue softens and stops the shunt from cooling; the cable tie in {10} takes the strain, heat-shrink over the joint if you like. The Kelvin pair S+ (RS.1) and S− (RS.2) twisted, the star GND to RS.2 at <b>the same point</b> as S−. Wires ~{11} cm (in the enclosure ~{12} cm from the shunt to the front edge of board A). A {13}-way <b>female header</b> on the end of the three wires (cut from CON018).
tr: Kart A'daki T_SP / T_SN / T_YILDIZ tellerinin uçlarına <b>erkek pin</b>: demet konnektörle takılır, kart sökülebilir kalır.
en: <b>Male pins</b> on the ends of the T_SP / T_SN / T_YILDIZ wires on board A: the harness plugs in with a connector, the board stays removable.
tr: S+ ↔ RS.1 bacağı, S− ↔ RS.2 bacağı: bip ötmeli.
en: S+ ↔ RS.1 leg, S− ↔ RS.2 leg: should beep.
tr: Yıldız ↔ S−: ötmeli (aynı nokta).
en: Star ↔ S−: should beep (same point).
tr: RS.1 ↔ RS.2: {0}–{1} Ω (şönt + prob).
en: RS.1 ↔ RS.2: {0}–{1} Ω (shunt + probe).
tr: <span class='ano'>{0}</span> <b>Q1 demeti ve soğutucu</b>
en: <span class='ano'>{0}</span> <b>Q1 harness and heatsink</b>
tr: Q1'i soğutucuya <b>yalıtarak</b> vidala: mika/silikon izolatör + burç + termal macun. Kapı bacağına {0} pinli dişi header, makaronla.
en: Screw Q1 to the heatsink <b>insulated</b>: mica/silicone insulator + bushing + thermal paste. A {0}-pin female header on the gate leg, with heat-shrink.
tr: Soğutucuyu üç parça çubuktan köşebende M3 vida + somunla tuttur.
en: Fasten the heatsink to the three-piece stick corner bracket with an M3 screw + nut.
tr: <b>Soğutucuyu {0} MΩ ile kart GND'ye bağla</b> (R026): direncin bir ucunu soğutucunun vida somununun altına, diğer ucunu kart GND'ye (A:T_YILDIZ ya da şöntün RS.2 bacağı; ⚠ {1} V klemensinin siyah ucu DEĞİL — o −{2} rayı). Neden dirençle: mika soğutucuyu yalıttığı için soğutucu kapalı kutuda <b>yüzen</b> bir metal plaka kalıyor; direnç statik birikimini akıtıp potansiyelini tanımlıyor. Neden doğrudan tel DEĞİL: mika bir gün delinirse soğutucu Q1'in savağına, yani <b>PİL {3}</b>'e (pil testinde {4} V) bağlanır — düz tel bunu GND'ye kısa devre ederdi ve o yolda bizim koyduğumuz bir sigorta yok. {5} MΩ ile en kötü hâlde {6} µA akar.
en: <b>Connect the heatsink to board GND through {0} MΩ</b> (R026): one end of the resistor under the heatsink's screw nut, the other end to board GND (A:T_YILDIZ or the shunt's RS.2 leg; ⚠ NOT the black end of the {1} V terminal block — that is the −{2} rail). Why a resistor: the mica insulates the heatsink, so it stays a <b>floating</b> metal plate in the closed enclosure; the resistor drains static build-up and defines its potential. Why NOT a direct wire: if the mica is ever punctured, the heatsink is connected to Q1's drain, i.e. <b>«PİL» {3}</b> ({4} V in the battery test) — a plain wire would short that to GND, and there is no fuse of ours on that path. With {5} MΩ, {6} µA flows at worst.
tr: Q1 tabı ↔ soğutucu: ötmemeli.
en: Q1 tab ↔ heatsink: should not beep.
tr: Kapı ↔ kaynak: ötmemeli.
en: Gate ↔ source: should not beep.
tr: Soğutucu ↔ kart GND: ötmemeli ama direnç kademesinde ≈ {0} MΩ okumalı ({1} Ω okursan mika delinmiş ya da vida tabı sıyırmış).
en: Heatsink ↔ board GND: should not beep, but should read ≈ {0} MΩ on the resistance range (if you read {1} Ω the mica is punctured or the screw has scraped the tab).
tr: <span class='ano'>{0}</span> <b>Şönt ve Q1'i kutuya al</b>
en: <span class='ano'>{0}</span> <b>Bring the shunt and Q1 into the enclosure</b>
tr: Type-C şönt, kutuda {0} mΩ Ø{1} mm manganin (R042, {2} A sürekli) takılı; {3} mΩ Ø{4} mm (R044, {5} A, {6} mA adım) yedek. R042 veri sayfası: tek parça manganin tel Ø{7}, {8} mm aralık, {9} A; bacaklardaki basık yer = ölçüm noktası, altında {10} mm bacak. Plakete GİRMEZ; bacaklar XP128 {11} mm klemense (CON064); yük kabloları XP128'e girmez, yanındaki bariyer klemenste (HB950) birleşir, XP128'e tek köprü (B55n). Kelvin telleri bacaklardaki BASIK YERİN kendisine lehimlenir (veri sayfasının ölçüm noktası; altındaki {12} mm bacak klemense girer, vidaya lehim yok); 'RS.2' saydığın bacağa S−, yıldız GND ve J3.2 gider — tutarlı ol. Isıl sınır tel çapından (B53).
en: Type-C shunt; the enclosure has a {0} mΩ Ø{1} mm manganin fitted (R042, {2} A continuous); {3} mΩ Ø{4} mm (R044, {5} A, {6} mA step) is the spare. R042 datasheet: a single piece of manganin wire Ø{7}, {8} mm spacing, {9} A; the crimp on the legs = measuring point, {10} mm of leg below it. It does NOT GO on the perfboard; the legs go into the XP128 {11} mm terminal block (CON064); the load cables do not go into the XP128, they join at the barrier terminal block (HB950) next to it, a single bridge to the XP128 (B55n). The Kelvin wires are soldered to the CRIMP ITSELF on the legs (the datasheet's measuring point; the {12} mm of leg below it goes into the terminal block, no solder at the screw); S−, the star GND and J3.2 go to the leg you count as 'RS.2' — be consistent. Thermal limit from the wire diameter (B53).
tr: IRFZ44N (Q006), kutuda: kaynağı bariyer klemensin {0}. kutbuna (= şöntün RS.1 düğümü, B55n), savağı J7.1'e (PİL {1}), kapısı karta tek telle (T_KAPI). Soğutucusuz {2} A'e kadar.
en: IRFZ44N (Q006), in the enclosure: source to pole {0} of the barrier terminal block (= the shunt's RS.1 node, B55n), drain to J7.1 («PİL» {1}), gate to the board with a single wire (T_KAPI). Up to {2} A without a heatsink.
tr: Şönt altlığını (iki parça, aradaki <b>{0} mm kanal</b> kablo bağının geçtiği yer) ve Q1 köşebendini plandaki yere yapıştır; şöntü kanaldan geçen kablo bağıyla, köşebendi tabana silikonla (kutu parçası).
en: Glue the shunt spacer (two pieces, the <b>{0} mm channel</b> between them is where the cable tie runs) and the Q1 corner bracket in the planned place; the shunt with a cable tie through the channel, the corner bracket to the base with hot glue (an enclosure part).
tr: Parçaların hiçbirini doğrudan tabana yapıştırma.
en: Do not glue any of the parts directly to the base.
tr: Şönt bacakları serbest, hava alıyor.
en: The shunt legs are free, in the air.
tr: Q1 soğutucusu hiçbir parçaya {0} mm'den yakın değil.
en: The Q1 heatsink is no closer than {0} mm to any part.
tr: <span class='ano'>{0}</span> <b>Yük yolunu bağla</b>
en: <span class='ano'>{0}</span> <b>Connect the load path</b>
tr: <b>Güç düğümü bariyer klemensi</b> (HB950, CON011) şönt bloğunun yanına: XP128'in her kutbundan bariyerin ilgili kutbuna <b>kısa kalın köprü</b> çek. XP128'de şönt bacağı + o tek köprüden başka bir şey olmayacak.
en: <b>Power node barrier terminal block</b> (HB950, CON011) next to the shunt block: run a <b>short heavy bridge</b> from each XP128 pole to the matching barrier pole. Nothing but the shunt leg + that single bridge goes into the XP128.
tr: YÜK {0} jakının <b>kalın kablosu</b> (≥{1} mm², {2}'de takıldı) → <b>bariyer kutup {3}</b> (= RS.1 düğümü); <b>bariyer kutup {4}</b> (= RS.2 düğümü) → YÜK {5} jakının kalın kablosu. Bariyer tarafında: teli ~{6} mm soy, sıkıca bük, <b>kalaylama</b>, vidanın (varsa pulunun) altına saat yönünde yatır ve sık — kalaylı uç vida altında zamanla gevşer (gerekçe {7}). ⚠ <b>Halka pabuç stokta YOK</b> ve gerekmez; almak istersen {8}'deki gibi borusu lehimli pabuç.
en: The <b>heavy cable</b> of the «YÜK» {0} jack (≥{1} mm², fitted in {2}) → <b>barrier pole {3}</b> (= RS.1 node); <b>barrier pole {4}</b> (= RS.2 node) → the heavy cable of the «YÜK» {5} jack. On the barrier side: strip the wire ~{6} mm, twist it tightly, <b>do not tin it</b>, lay it clockwise under the screw (and its washer, if any) and tighten — a tinned end loosens under a screw over time (reason in {7}). ⚠ <b>Ring lugs are NOT in stock</b> and not needed; if you want to buy some, a lug with its barrel soldered as in {8}.
tr: Kısa tut: ölçülen bütün akım bu yoldan geçecek (sürekli ≤ {0} A, {1} mΩ şöntün ısıl sınırı; {2} mΩ takılıysa {3} A). Şöntü tutan XP128 klemensi {4} A: kısa süreli de olsa geçme.
en: Keep it short: all the measured current flows through this path (continuous ≤ {0} A, the thermal limit of the {1} mΩ shunt; {3} A if the {2} mΩ is fitted). The XP128 terminal block holding the shunt is {4} A: do not exceed it, not even briefly.
tr: <b>HB950'nin üstündeki baskıya bak</b> (ör. "300V 15A"): en az {0} A olmalı. Daha düşük yazıyorsa o sayıyı kutunun akım sınırı say ve panelde YÜK etiketinin altına yaz.
en: <b>Check the print on top of the HB950</b> (e.g. "300V 15A"): it must be at least {0} A. If it says less, take that number as the enclosure's current limit and write it on the panel under the «YÜK» label.
tr: Ön duvar
en: Front wall
tr: Bağlanacak kablolar
en: Cables to connect
tr: Tür
en: Type
tr: Kart deliği
en: Board hole
tr: <span class='kucuk'>yuk donusu -&gt; sont ust bacagi</span>
en: <span class='kucuk'>load return -&gt; upper leg of the shunt</span>
tr: <span class='kucuk'>sont alt bacagi -&gt; kaynak eksisi</span>
en: <span class='kucuk'>lower leg of the shunt -&gt; source negative</span>
tr: YÜK {0} ↔ YÜK {1}: {2}–{3} Ω (şönt {4} mΩ + prob).
en: «YÜK» {0} ↔ «YÜK» {1}: {2}–{3} Ω (shunt {4} mΩ + probe).
tr: YÜK {0} ↔ V, SKOP, HV jakları: OL (sonsuz).
en: «YÜK» {0} ↔ V, «SKOP», HV jacks: OL (open).
tr: <span class='ano'>{0}</span> <b>Kelvin ve yıldız konnektörünü tak</b>
en: <span class='ano'>{0}</span> <b>Plug in the Kelvin and star connector</b>
tr: {0}'te hazırladığın {1}'lü demeti kartın T_SP / T_SN / T_YILDIZ pinlerine tak — sıraya dikkat: S+ → T_SP (C25), S− → T_SN (C27), yıldız → T_YILDIZ (C29).
en: Plug the {1}-way harness you prepared in {0} onto the board's T_SP / T_SN / T_YILDIZ pins — mind the order: S+ → T_SP (C25), S− → T_SN (C27), star → T_YILDIZ (C29).
tr: Burgulu çifti kablo bağıyla şönt altlığına tuttur.
en: Tie the twisted pair to the shunt spacer with a cable tie.
tr: A:S+ (şönt üst)
en: A:S+ (shunt top)
tr: kelvin
en: kelvin
tr: <span class='kucuk'>S+ : sont BACAGINA, sikistirma izinin ustunden — klemensten degil</span>
en: <span class='kucuk'>S+ : to the shunt LEG, above the crimp mark — not from the terminal block</span>
tr: A:S− (şönt alt)
en: A:S− (shunt bottom)
tr: <span class='kucuk'>S- : ayni sekilde; S+ ile BURULU cift</span>
en: <span class='kucuk'>S- : the same way; TWISTED pair with S+</span>
tr: A:GND yıldız (şönt alt BACAĞI, S− ile aynı nokta)
en: A:GND star (shunt bottom LEG, same point as S−)
tr: yildiz
en: star
tr: <span class='kucuk'>kart topraginin guc yoluna TEK baglantisi — S- ile AYNI noktaya, sont bacagina (klemens vidasina DEGIL: vida-bacak temas direnci COM'u S-'den I x R kadar kaydirir)</span>
en: <span class='kucuk'>the board ground's ONLY connection to the power path — at the SAME point as S-, on the shunt leg (NOT the terminal screw: the screw-to-leg contact resistance shifts COM from S- by I x R)</span>
tr: Kart C25 ↔ YÜK {0} jakı: ötmeli. Kart C27 ↔ YÜK {1}: ötmeli.
en: Board C25 ↔ «YÜK» {0} jack: should beep. Board C27 ↔ «YÜK» {1}: should beep.
tr: Kart C29 ↔ <b>şöntün RS.2 bacağı</b>: ötmeli (yıldız oraya lehimli). ⚠ COM <b>jakıyla</b> ölçme — COM'un teli {0}'de bağlanıyor, şu an takılı değil ve OL okursun; sağlam lehimi sökmeye kalkma.
en: Board C29 ↔ <b>the shunt's RS.2 leg</b>: should beep (the star is soldered there). ⚠ Do not measure to the COM <b>jack</b> — COM's wire is connected in {0}, it is not fitted yet and you would read OL; do not go desoldering a good joint.
tr: YÜK {0} ↔ COM: <b>öter</b> (arada yalnız {1} mΩ şönt var) — ohm kademesinde ≤ {2} Ω oku; asıl kontrol yukarıdaki C25/C27 ayrımı.
en: «YÜK» {0} ↔ COM: <b>beeps</b> (only the {1} mΩ shunt in between) — read ≤ {2} Ω on the ohms range; the real check is the C25/C27 distinction above.
tr: <span class='ano'>{0}</span> <b>Q1'i yük yoluna bağla</b>
en: <span class='ano'>{0}</span> <b>Connect Q1 to the load path</b>
tr: <b>Güç düğümü bariyerde, XP128'de değil.</b> Şönt bloğunun yanına <b>HB950 {0} pin bariyer klemensi</b> (CON011) yapıştır/vidala. Her XP128 kutbunda yalnız <b>şönt bacağı + tek köprü kablosu</b> kalsın; kalın kabloların hepsi bariyerde birleşsin. Gerekçe: XP128'in kafesine Ø{1} mm manganin çubukla damarlı kablo birlikte girerse basıncı çubuk alır, kablo gevşer — {2} A'lik yolda gevşek klemens ısınır. Ölçüme etkisi yok: Kelvin uçları şöntün <b>bacağında</b>, bu düğümde değil; düğümdeki temas direnci akımı değiştirmez, ölçülen gerilime girmez.
en: <b>The power node is at the barrier, not at the XP128.</b> Glue/screw an <b>HB950 {0}-pin barrier terminal block</b> (CON011) next to the shunt block. Only <b>the shunt leg + a single bridge wire</b> stay in each XP128 pole; all the heavy cables join at the barrier. Reason: if a Ø{1} mm manganin rod and a stranded cable go into the XP128's cage together, the rod takes the pressure and the cable works loose — on a {2} A path a loose terminal heats up. No effect on the measurement: the Kelvin ends are on the shunt's <b>leg</b>, not at this node; contact resistance at the node does not change the current and does not enter the measured voltage.
tr: Bariyer <b>kutup {0}</b> (= RS.1 düğümü): YÜK {1} jakı · Q1'in <b>kaynağı</b> · XP128 kutup {2}'e giden köprü.
en: Barrier <b>pole {0}</b> (= RS.1 node): «YÜK» {1} jack · Q1's <b>source</b> · the bridge to XP128 pole {2}.
tr: Bariyer <b>kutup {0}</b> (= RS.2 düğümü): YÜK {1} jakı · PİL {2} jakı · XP128 kutup {3}'ye giden köprü.
en: Barrier <b>pole {0}</b> (= RS.2 node): «YÜK» {1} jack · «PİL» {2} jack · the bridge to XP128 pole {3}.
tr: PİL {0} jakı → Q1'in <b>savağı</b> (bariyere uğramaz, tek kablo).
en: «PİL» {0} jack → Q1's <b>drain</b> (does not pass the barrier, a single cable).
tr: Hepsi kalın kablo; jak tarafları {0}'de bağlandı. Bariyer tarafında burulmuş, <b>kalaysız</b> uçlar vidanın (varsa pulunun) altına — bir kutba iki-üç uç sığar, hepsini aynı yöne (saat yönü) yatır. Kalaylı uç vida altında zamanla gevşer ({1}). Halka pabuç stokta yok ve gerekmez.
en: All heavy cable; the jack ends were connected in {0}. On the barrier side, twisted <b>untinned</b> ends under the screw (and its washer, if any) — two or three ends fit in one pole, lay them all the same way (clockwise). A tinned end loosens under a screw over time ({1}). Ring lugs are not in stock and not needed.
tr: <b>Şönt değiştirirken</b> ({0} mΩ ↔ {1} mΩ) yalnız XP128'in iki vidası gevşer — kalın kablolar ve Kelvin lehimleri yerinde kalır.
en: <b>When changing the shunt</b> ({0} mΩ ↔ {1} mΩ) only the two XP128 screws are loosened — the heavy cables and the Kelvin joints stay in place.
tr: <span class='kucuk'>Q1 kaynagi -&gt; sont ust bacagi</span>
en: <span class='kucuk'>Q1 source -&gt; upper leg of the shunt</span>
tr: <span class='kucuk'>pil testi yuku -&gt; Q1 savagi</span>
en: <span class='kucuk'>battery test load -&gt; Q1 drain</span>
tr: <span class='kucuk'>pil eksisi -&gt; sont alt bacagi</span>
en: <span class='kucuk'>battery negative -&gt; lower leg of the shunt</span>
tr: PİL {0} ↔ YÜK {1}: ötmeli (ikisi de RS.2).
en: «PİL» {0} ↔ «YÜK» {1}: should beep (both are RS.2).
tr: PİL {0} ↔ YÜK {1}: <b>kırmızı prob PİL {2}'de</b> ölç — ötmemeli. (Ters probda MOSFET'in gövde diyotu öter, o normal.) Kapı teli henüz takılı değil: ölçerken Q1'in kapısını kaynağına ince telle kısa devre et (yüzen kapı MOSFET'i yarı açabilir, yanlış 'öter' verir).
en: «PİL» {0} ↔ «YÜK» {1}: measure with the <b>red probe on «PİL» {2}</b> — should not beep. (With the probes reversed the MOSFET's body diode beeps, that is normal.) The gate wire is not connected yet: while measuring, short Q1's gate to its source with a thin wire (a floating gate can half-open the MOSFET and give a false 'beep').
tr: <span class='ano'>{0}</span> <b>Kapı telini tak</b>
en: <span class='ano'>{0}</span> <b>Connect the gate wire</b>
tr: Kartın T_KAPI telinin (Z36) ucuna erkek pin; Q1 demetinin dişi ucunu tak.
en: A male pin on the end of the board's T_KAPI wire (Z36); plug on the female end of the Q1 harness.
tr: Teli Q1 bacağından ~{0} mm sonra köşebende <b>kablo bağıyla</b> tut — soğutucunun yanında silikon yok (yumuşar).
en: Hold the wire to the corner bracket <b>with a cable tie</b> ~{0} mm after the Q1 leg — no hot glue next to the heatsink (it softens).
tr: A:Q1 kapı
en: A:Q1 gate
tr: sinyal
en: signal
tr: <span class='kucuk'>kapi teli</span>
en: <span class='kucuk'>gate wire</span>
tr: Q1 kapısı ↔ kaynağı: ötmemeli.
en: Q1 gate ↔ source: should not beep.
tr: Kapı teli soğutucuya değmiyor.
en: The gate wire does not touch the heatsink.
tr: <span class='ano'>{0}</span> <b>V ve COM jakları</b>
en: <span class='ano'>{0}</span> <b>V and COM jacks</b>
tr: Kartın V girişi teli (C4) → <b>V jakı</b>; COM teli (C6) → <b>COM jakı</b>. Jak tarafı {0}'deki yöntemle: lehim kulağı varsa lehim, yoksa <b>kalaysız</b> halka iki somunun arasında; çıplak uç kalmasın. Bu teller akım taşımaz ama gevşek bağlantı okumayı oynatır. (Halka pabuç stokta yok, gerekmez.)
en: The board's V input wire (C4) → <b>V jack</b>; the COM wire (C6) → <b>COM jack</b>. On the jack side, the method from {0}: solder if there is a solder lug, otherwise an <b>untinned</b> loop between two nuts; no bare end left showing. These wires carry no current, but a loose joint makes the reading wander. (Ring lugs are not in stock, not needed.)
tr: A:V girişi (J1)
en: A:V input (J1)
tr: <span class='kucuk'>V girisi (KIRMIZI uc). COM teliyle burulabilir</span>
en: <span class='kucuk'>V input (RED end). Can be twisted with the COM wire</span>
tr: A:COM jak
en: A:COM jack
tr: <span class='kucuk'>COM jak -&gt; kart GND (SIYAH uc)</span>
en: <span class='kucuk'>COM jack -&gt; board GND (BLACK end)</span>
tr: Yol kontrolü — jaktan karta
en: Path check — from jack to board
tr: Uç {0}
en: End {0}
tr: V jakı
en: V jack
tr: HV jakı
en: HV jack
tr: SKOP jakı
en: «SKOP» jack
tr: Bölücüler GND'ye değil VREF'e iniyor; jak ile COM arası enerji yokken sonsuz okur. Anlamlı ölçüm jak ile VREF arası: kartta U3'ün {0}. bacağı, delik <b>A:R8</b>.
en: The dividers go down to VREF, not GND; with no power, jack to COM reads open. The meaningful measurement is jack to VREF: pin {0} of U3 on the board, hole <b>A:R8</b>.
tr: V jakı ↔ kart C4: ötmeli. COM jakı ↔ kart C6: ötmeli.
en: V jack ↔ board C4: should beep. COM jack ↔ board C6: should beep.
tr: V jakı ↔ kart R8 (VREF): tabloda yazan direnç.
en: V jack ↔ board R8 (VREF): the resistance given in the table.
tr: <span class='ano'>{0}</span> <b>SKOP jakı</b>
en: <span class='ano'>{0}</span> <b>«SKOP» jack</b>
tr: Skop teli (B16) → <b>SKOP jakı</b>.
en: Scope wire (B16) → <b>«SKOP» jack</b>.
tr: Skopun dönüşü COM jakıdır; <b>ayrı tel yok</b> (netlistteki J4.2 aynı fiziksel jak).
en: The scope's return is the COM jack; <b>no separate wire</b> (J4.2 in the netlist is the same physical jack).
tr: A:Skop jak (J4)
en: A:Scope jack (J4)
tr: <span class='kucuk'>skop girisi</span>
en: <span class='kucuk'>scope input</span>
tr: SKOP jakı ↔ kart B16: ötmeli.
en: «SKOP» jack ↔ board B16: should beep.
tr: SKOP jakı ↔ R8 (VREF): tabloda yazan direnç.
en: «SKOP» jack ↔ R8 (VREF): the resistance given in the table.
tr: <span class='ano'>{0}</span> <b>HV jakı ve kablo ankrajı</b>
en: <span class='ano'>{0}</span> <b>HV jack and cable anchor</b>
tr: <b>Ön koşul:</b> Yerleşim {0}'nin B tarafı bitmiş olmalı (B:D8'e HV lehimi, B:O16 → A:C11 sarı tel).
en: <b>Prerequisite:</b> side B of Layout {0} must be finished (HV soldered to B:D8, yellow wire B:O16 → A:C11).
tr: HV jakı → kart B D8: <b>silikon prob kablosu</b> (KBL004). Kısa yoldan, diğer tellere paralel gitmesin.
en: HV jack → board B D8: <b>silicone probe cable</b> (KBL004). By a short route, not running parallel to other wires.
tr: <b>Kablonun gerilim sınıfı — kararı burada ver, sorma:</b> kılıfın üstündeki baskıyı oku ({0} V tam skala). ① <b>{1} V ve üstü yazıyorsa</b> (ör. {2} kV / {3} kV silikon prob kablosu): doğrudan kullan. ② <b>Daha düşük yazıyorsa ya da hiç baskı yoksa:</b> kabloyu <b>boydan boya makaronla</b> kapla (ikinci yalıtım; makaron uçlardan {4} mm taşsın) <b>ve</b> panelde HV etiketinin altına okuduğun değeri yaz — o değerin üstünde ölçüm yapma. Baskısız kablonun kılıfı tek başına {5} V sayılmaz; kaplarsan ikinci katman riski taşır, kutunun kendisi zaten yalıtkan. ③ Her iki halde de kablo <b>tek parça</b> olsun: ek yeri / lüstür klemens yok.
en: <b>The cable's voltage class — decide here, do not ask:</b> read the print on the jacket ({0} V full scale). ① <b>If it says {1} V or more</b> (e.g. {2} kV / {3} kV silicone probe cable): use it as is. ② <b>If it says less, or there is no print at all:</b> cover the cable <b>with heat-shrink along its full length</b> (a second insulation; the heat-shrink overlapping {4} mm at the ends) <b>and</b> write the value you read on the panel under the HV label — do not measure above that value. The jacket of an unprinted cable alone does not count as {5} V; covered, the second layer carries the risk, and the enclosure itself is an insulator anyway. ③ Either way the cable must be <b>one piece</b>: no splices / screw connectors.
tr: Ankraj: üç çubuk parçasını üst üste yapıştırıp kart B'nin önüne, tabana dik yapıştır (plandaki yer); HV kablosunu buna kablo bağıyla tut — çekilince D8 lehimi değil bağ direnir.
en: Anchor: glue three stick pieces on top of each other and glue them upright to the base in front of board B (the planned place); hold the HV cable to it with a cable tie — when the cable is pulled, the tie resists, not the D8 joint.
tr: HV'nin dönüşü de COM jakıdır; ayrı tel yok.
en: HV's return is also the COM jack; no separate wire.
tr: <b>HV ankraj bloğu</b>
en: <b>HV anchor block</b>
tr: B:HV jak
en: B:HV jack
tr: hv
en: hv
tr: <span class='kucuk'>HV jak -&gt; B karti. {0} V silikon test kablosu</span>
en: <span class='kucuk'>HV jack -&gt; board B. {0} V silicone test lead</span>
tr: HV jakı ↔ kart B'nin R10 bacağı: ötmeli. (D8'in kendisi {0}'te cilayla kaplandı — kaplı lehime prob değmez, kazıma; komşu çıplak bacaktan ölç.)
en: HV jack ↔ the R10 leg of board B: should beep. (D8 itself was coated with varnish in {0} — a probe does not contact a coated joint, do not scrape; measure from the bare neighbouring leg.)
tr: HV jakı ↔ R8 (VREF): tabloda yazan direnç (≈ {0} MΩ).
en: HV jack ↔ R8 (VREF): the resistance given in the table (≈ {0} MΩ).
tr: Kabloyu elle çek: kart B ve D8 lehimi oynamıyor.
en: Pull the cable by hand: board B and the D8 joint do not move.
tr: <span class='ano'>{0}</span> <b>MT1'i {1} V'a, MT2'yi {2} V'a yüksüz ayarla</b>
en: <span class='ano'>{0}</span> <b>Set MT1 to {1} V and MT2 to {2} V with no load</b>
tr: İki MT3608'i tezgahta, <b>yük takmadan</b> ayarla: çıkışı multimetreyle izle, trimpotu saat yönü tersine çevir. Fabrika ayarı {0} V'a kadar çıkabilir: <b>ayarlanmamış modülü ESP32'ye ya da karta bağlama</b> ({1} V ESP32'yi öldürür).
en: Set the two MT3608s at the bench <b>with no load connected</b>: watch the output with a multimeter, turn the trimpot anticlockwise. The factory setting can go up to {0} V: <b>do not connect an unadjusted module to the ESP32 or the board</b> ({1} V kills the ESP32).
tr: <b>MT1 → {0} V</b>: girişe bir {1} ({2}–{3} V). <b>MT2 → {4} V</b>: girişe {5} V ver — kutuda onu B0505S'in yalıtılmış {6} V'u besleyecek; tezgahta bir USB şarj adaptörü ya da az önce ayarladığın MT1'in çıkışı yeter.
en: <b>MT1 → {0} V</b>: a {1} on the input ({2}–{3} V). <b>MT2 → {4} V</b>: feed {5} V to the input — in the enclosure it is fed from the B0505S's isolated {6} V; at the bench a USB charger or the MT1 output you just set is enough.
tr: İkisini etiketle: MT1 ({0} V), MT2 ({1} V).
en: Label both: MT1 ({0} V), MT2 ({1} V).
tr: <b>B0505S'i de tezgahta dene</b> (duvara gitmeden). <b>Gövdede bacak adı yazmaz</b>: yazılı yüz sana dönük, bacaklar aşağıdayken noktanın altındaki en soldaki bacak {0}. Hi-Link veri sayfası: <b>{1} = +Vin, {2} = −Vin, {3} = −Vout, {4} = +Vout</b> ({5} ve {6} yok) — <b>yan yana duran iki bacak GİRİŞ</b>, aralıklı ikisi ÇIKIŞ. ⚠ Mornsun B0505S'te {7} = GND, {8} = Vin: başka markanın şemasına bakma; girişi ters beslemek modülü bozar (−{9} V sınırı). Bacaklara krokodil takma ({10}–{11} arası {12} mm): önce dört bacağa ince tel lehimle (havya ≤ {13} °C, gövdeden ≥ {14} mm), makaronla kapla — {15}'de modül zaten böyle takılıyor. Gövdede <b>2WR3</b> yazmalı ({16} W sürümü açılışta yetmez, B58f). Girişine {17} V (USB şarj adaptörü ya da ayarlı MT1), çıkışında {18}–{19} V oku (yüksüzken regülesiz modül biraz yüksek okur; kutuda MT2 onu yükler). Veri sayfası uzun süre yüksüz çalıştırmayı önermiyor: oku ve kapat.
en: <b>Try the B0505S at the bench too</b> (before it goes on the wall). <b>The body has no pin names</b>: with the printed face towards you and the pins down, the leftmost pin under the dot is {0}. Hi-Link datasheet: <b>{1} = +Vin, {2} = −Vin, {3} = −Vout, {4} = +Vout</b> (no {5} and {6}) — <b>the two pins side by side are the INPUT</b>, the two spaced apart are the OUTPUT. ⚠ On the Mornsun B0505S {7} = GND, {8} = Vin: do not go by another brand's diagram; feeding the input reversed damages the module (−{9} V limit). Do not clip crocodile clips onto the pins ({12} mm between {10}–{11}): first solder thin wire to all four pins (iron ≤ {13} °C, ≥ {14} mm from the body), cover with heat-shrink — that is how the module is fitted in {15} anyway. The body must say <b>2WR3</b> (the {16} W version is not enough at power-up, B58f). {17} V on its input (USB charger or the adjusted MT1), read {18}–{19} V on its output (with no load an unregulated module reads a little high; in the enclosure MT2 loads it). The datasheet does not recommend running it unloaded for long: read and switch off.
tr: MT1 çıkışı {0}–{1} V (giriş {2}–{3} V'ta).
en: MT1 output {0}–{1} V (input at {2}–{3} V).
tr: MT2 çıkışı {0}–{1} V (giriş {2}–{3} V'ta).
en: MT2 output {0}–{1} V (input at {2}–{3} V).
tr: B0505S: çıkış ({0} ↔ {1}) {2}–{3} V (yüksüz); enerjisizken bacak {4} (−Vin) ↔ bacak {5} (−Vout) ötmüyor.
en: B0505S: output ({0} ↔ {1}) {2}–{3} V (no load); unpowered, pin {4} (−Vin) ↔ pin {5} (−Vout) does not beep.
tr: <span class='ano'>{0}</span> <b>Yuvaları, MT1/MT2'yi, B0505S'i ve hücre sigortalarını tak</b>
en: <span class='ano'>{0}</span> <b>Fit the holders, MT1/MT2, the B0505S and the cell fuses</b>
tr: {0} yuvası; iki hücre PARALEL (B58): eksiler TP4056'nın B−'sinde birleşir = kart GND (ESP32 ile ortak). Arka duvara sıcak silikonla yapıştırılır — kutu kuralının tek istisnası (cıvata deliği yok).
en: {0} holder; the two cells in PARALLEL (B58): the negatives join at the TP4056's B− = board GND (shared with the ESP32). Hot-glued to the back wall — the only exception to the enclosure rule (no bolt holes).
tr: {0} yuvası, hücre {1}'e PARALEL; artısı kendi sigortasından (F2). İlk takışta iki hücrenin gerilimi ±{2} V içinde olmalı ({3}).
en: {0} holder, in PARALLEL with cell {1}; its positive through its own fuse (F2). At first insertion the two cell voltages must be within ±{2} V ({3}).
tr: MT3608 yüksüz {0} V'a ayarlanır (fabrika ayarı {1} V'a kadar çıkabilir — önce ayar, sonra ESP32). Çıkış {2} V barası: ESP32'nin 5V (VIN) pini ve F0 (ölçüm tarafı); devkit USB'yle diyot-OR yapar.
en: The MT3608 is set to {0} V with no load (the factory setting can go up to {1} V — set it first, then the ESP32). Output {2} V bus: the ESP32's 5V (VIN) pin and F0 (measurement side); the devkit diode-ORs it with USB.
tr: MT3608 yüksüz {0} V'a ayarlanır; girişi B0505S'in yalıtılmış {1} V'u. {2} V yükü {3}–{4} mA. Anahtarlama dalgalanması −{5} rayında skopla ölçülecek ({6}).
en: The MT3608 is set to {0} V with no load; its input is the B0505S's isolated {1} V. {2} V load {3}–{4} mA. The switching ripple on the −{5} rail is to be measured with the scope ({6}).
tr: B0505S-2WR3 ({0} V → {1} V yalıtılmış, {2} W): kutunun İKİ TOPRAĞINI ayıran tek parça. Giriş (bacak {3} +Vin, {4} −Vin) paket/ESP32 tarafı = kart GND; çıkış ({5} +Vout, {6} −Vout) MT2'ye — bacak {7} kartın −{8} rayı olur (gövdede ad yazmaz, numaralar {9}'de). İki tarafı birleştiren tek bir tel −{10}'yi GND'ye kısa eder. Yük {11} W (%{12}). {13} W sürümü sürekli yüke yeter ama açılışta kartı {14} V'a çıkaramayabilir (B58f benzetimi).
en: B0505S-2WR3 ({0} V → {1} V isolated, {2} W): the one part that separates the enclosure's TWO GROUNDS. Input (pin {3} +Vin, {4} −Vin) pack/ESP32 side = board GND; output ({5} +Vout, {6} −Vout) to MT2 — pin {7} becomes the board's −{8} rail (no names on the body, numbers in {9}). A single wire joining the two sides shorts −{10} to GND. Load {11} W ({12}%). The {13} W version is enough for the continuous load but may not bring the board up to {14} V at power-up (B58f simulation).
tr: MT2'nin giriş kondansatörü ({0} µF {1} V, C042): açılışta MT2'nin çektiği tepe akımı verir; yoksa MT2 girişini B0505S'ten çökertip yeniden başlar ve kart {2} V'a çıkamayabilir (B58f). B0505S'in çıkış tarafında = −{3} rayı tarafı: kart GND'ye DEĞMEZ.
en: MT2's input capacitor ({0} µF {1} V, C042): supplies the peak current MT2 draws at power-up; without it MT2 collapses its input from the B0505S and restarts, and the board may not reach {2} V (B58f). On the B0505S's output side = the −{3} rail side: it DOES NOT TOUCH board GND.
tr: {0} V iç klemens (CON007, {1}'li {2} mm): MT2'nin {3} V çıkışı ve kartın C34 (+) / C36 (−) telleri buraya; kart lehim sökmeden çıkar. Klemens − = kartın −{4} rayı: kart GND'ye hiçbir yoldan DEĞMEZ.
en: {0} V internal terminal block (CON007, {1}-way {2} mm): MT2's {3} V output and the board's C34 (+) / C36 (−) wires go here; the board comes out without desoldering. Terminal − = the board's −{4} rail: it DOES NOT TOUCH board GND by any path.
tr: Kutu içinde, PCB klipsli {0}×{1} yuva (FUS009) + {2} A hızlı (FUS003): {3} V barası → F0 → B0505S girişi. Yalnız iç arızada atar (B0505S, MT2, kart); panelde değil, çünkü ölçüm akımının (YÜK jakları, bilerek sigortasız) korunduğunu düşündürüyordu. Kartın F1'i {4} V tarafında.
en: Inside the enclosure, a {0}×{1} PCB-clip holder (FUS009) + {2} A fast (FUS003): {3} V bus → F0 → B0505S input. It only blows on an internal fault (B0505S, MT2, board); not on the panel, because there it suggested the measurement current (the «YÜK» jacks, deliberately unfused) was protected. The board's F1 is on the {4} V side.
tr: Hücre {0} sigortası: PCB klipsli {1}×{2} yuva (FUS009) + {3} A F (FUS004), hücrenin ARTI ucunda. TP4056'nın koruması hücre ucundaki kısayı kesemez (FET B−/OUT− arasında); o yolu yalnız bu korur.
en: Cell {0} fuse: {1}×{2} PCB-clip holder (FUS009) + {3} A F (FUS004), on the cell's POSITIVE end. The TP4056's protection cannot interrupt a short at the cell end (the FET is between B−/OUT−); only this protects that path.
tr: Hücre {0} sigortası: F1P'nin aynısı. Paralelde her hücrenin AYRI sigortası şart — biri içeriden kısa devre olursa öbürü onu sigortasız doldurmaya çalışır.
en: Cell {0} fuse: the same as F1P. In parallel, each cell MUST have its OWN fuse — if one shorts internally, the other tries to fill it with no fuse in between.
tr: Arka duvar (içeriden): iki {0} yuvası üst üste — YUVA1 alt, YUVA2 üst (konum tabloda). <b>Sıcak silikonla yapıştır — cıvata yok</b> (kullanıcı kararı): önce yerini kurşun kalemle işaretle (sıcak silikonda kaydırma payı birkaç saniye), yuvanın tabanına boydan boya iki şerit çek, duvara {1} s bastır. İç kat çubuklarının arasına denk gelen yerde silikonu kalın bırak — {2} mm boşluğu doldurur. <b>Yön:</b> YUVA1'in kırmızı telinin çıktığı ucu SOLA (F1P'ye), YUVA2'ninki SAĞA (F2'ye). Hücreleri henüz TAKMA ({3}). YUVA2'nin üstü kapağa {4} mm.
en: Back wall (from inside): two {0} holders one above the other — YUVA1 below, YUVA2 above (position in the table). <b>Hot-glue them — no bolts</b> (user decision): first mark the position with a pencil (hot glue only gives you a few seconds to adjust), run two beads along the full length of the holder's base, press against the wall {1} s. Where it lands between the inner layer sticks, leave the glue thick — it fills the {2} mm gap. <b>Orientation:</b> the end of YUVA1 where its red wire comes out to the LEFT (towards F1P), YUVA2's to the RIGHT (towards F2). DO NOT insert the cells yet ({3}). The top of YUVA2 is {4} mm from the lid.
tr: Şarj modülü (TP1) {0}'da, kart A'dan önce takıldı; burada ona dokunma.
en: The charging module (TP1) was fitted in {0}, before board A; do not touch it here.
tr: <b>Tezgahta önce:</b> MT1 ve MT2'ye kablolarını lehimle (TP1 gibi; kutuda pedlere havya rahat girmez): teli kartın parça yüzünden sok, alttan lehimle, taşan ucu kes — modülün arkası duvara düz otursun. Uçları etiketle. Hangi pede ne geldiği ve kesim boyları {0} / {1}'ün kablo tablosunda ve çiziminde (numaralı). MT2'nin IN− ucuna '−{2} tarafı' yaz.
en: <b>At the bench first:</b> solder the wires to MT1 and MT2 (like TP1; in the enclosure the iron does not reach the pads easily): push the wire in from the component side of the board, solder underneath, trim the excess — the back of the module must sit flat on the wall. Label the ends. Which wire goes to which pad and the cut lengths are in the cable table and drawing of {0} / {1} (numbered). Write '−{2} side' on MT2's IN− end.
tr: <b>Sigorta yuvası = iki ayrı klips</b> (FUS009), tek gövde değil: iki klipsi kart A'dan artan plaketten kestiğin en fazla <b>{0} mm</b>'lik bir şeride lehimle — önce sigortayı iki klipse tak, bacakları şeride geçir, lehimle; sigorta aralığı kendiliğinden doğru olur. Her klipsin iki bacağını altta birleştir; teli klipsin yanındaki boş delikten ön yüzden sok, arkada klips bacağına lehimle. Üç şerit: F0, F1P, F2. (Kapaklı KF-{1} denendi: {2} × {3} mm ölçüsüyle yerleşime sığmıyor — F1P kart A'nın altına giriyor, kapaklar üst üste geliyor.)
en: <b>Fuse holder = two separate clips</b> (FUS009), not a single body: solder the two clips onto a strip of at most <b>{0} mm</b> cut from the perfboard left over from board A — first put the fuse into both clips, pass the legs through the strip, solder; the fuse spacing comes out right by itself. Join the two legs of each clip underneath; push the wire in from the front through the empty hole next to the clip and solder it to the clip leg at the back. Three strips: F0, F1P, F2. (A covered KF-{1} was tried: at {2} × {3} mm it does not fit the layout — F1P goes under board A and the covers overlap.)
tr: <b>Tutturma — sıcak silikon</b> (kullanıcı kararı {0}-{1}-{2}): MT1, MT2, B0505S, {3} µF, KL ve üç sigorta şeridi duvara sıcak silikonla; sökmek için izopropil alkol damlat, plastik kartla kaldır. Silikon PCB'nin ARKASINA ya da kenarına — çipin ve bobinin üstüne değil (ısınan yerler). MT1/MT2'nin trimpotu içe ve erişilebilir kalsın. Kartlar, ESP32, şönt ve Q1 yapıştırılmaz.
en: <b>Fixing — hot glue</b> (user decision {0}-{1}-{2}): MT1, MT2, B0505S, {3} µF, KL and the three fuse strips are hot-glued to the wall; to remove, drip isopropyl alcohol and lift with a plastic card. Glue on the BACK or the edge of the PCB — not on the chip and the inductor (the parts that get hot). The MT1/MT2 trimpots face in and stay reachable. The boards, ESP32, shunt and Q1 are not glued.
tr: MT1 ve MT2 arka duvarın solunda, üst üste (x {0}–{1}; MT1 z {2}, MT2 z {3}). MT1'in OUT pedleri SOLA (F0 ve B0505S), MT2'nin IN pedleri SOLA (B0505S ve {4} µF).
en: MT1 and MT2 on the left of the back wall, one above the other (x {0}–{1}; MT1 z {2}, MT2 z {3}). MT1's OUT pads to the LEFT (F0 and B0505S), MT2's IN pads to the LEFT (B0505S and {4} µF).
tr: <b>B0505S (IZ)</b> MT2'nin soluna, bacaklar aşağı, gövdesinden yapıştır. ⚠ Bu modül kutunun <b>iki toprağını ayıran TEK parça</b>: giriş tarafı ({0} +Vin, {1} −Vin) ile çıkış tarafı ({2} −Vout, {3} +Vout) hiçbir telle birleşmesin.
en: <b>B0505S (IZ)</b> to the left of MT2, pins down, glued by its body. ⚠ This module is the <b>ONLY part separating the enclosure's two grounds</b>: the input side ({0} +Vin, {1} −Vin) and the output side ({2} −Vout, {3} +Vout) must not be joined by any wire.
tr: <b>MT2'nin giriş kondansatörü (CB, {0} µF {1} V, C042)</b> MT2'nin üstüne, yatık. Bacaklarını MT2'nin giriş pedlerine lehimle: uzun bacak IN+, ⚠ <b>şeritli bacak EKSİ → IN−</b>.
en: <b>MT2's input capacitor (CB, {0} µF {1} V, C042)</b> above MT2, lying down. Solder its legs to MT2's input pads: long leg IN+, ⚠ <b>striped leg NEGATIVE → IN−</b>.
tr: <b>{0} V iç klemensi (KL, CON007)</b> B0505S'in üstüne; vidalar içe. Hangi vidanın + olduğunu kalemle yaz: {1}'te MT2'nin çıkışı ve kartın {2} V telleri aynı kutupla buraya vidalanacak.
en: <b>{0} V internal terminal block (KL, CON007)</b> above the B0505S; screws facing in. Write with a pen which screw is +: in {1} MT2's output and the board's {2} V wires are screwed in here with the same polarity.
tr: <b>Analog sigortası F0</b> B0505S'in altına, MT1'in soluna (konum tabloda); içine {0} A hızlı cam sigorta (FUS003) — şimdilik <b>TAKMA</b>, {1}'te ilk enerji sırası için çıkarılmış duracak.
en: <b>Analog fuse F0</b> below the B0505S, to the left of MT1 (position in the table); it takes a {0} A fast glass fuse (FUS003) — <b>DO NOT FIT</b> it for now, in {1} it stays out for the first power-up sequence.
tr: Hücre sigortaları <b>F1P ve F2</b> en alt sırada (konum tabloda); içlerine <b>{0} A F</b> cam sigorta (FUS004). Anma neden bu kadar yüksek: sigorta hücrenin artısında, yani şarj akımı da buradan geçiyor ({1} A; tek hücre takılıysa tamamı) — daha küçüğü ilk şarjda atar.
en: Cell fuses <b>F1P and F2</b> on the bottom row (position in the table); they take <b>{0} A F</b> glass fuses (FUS004). Why the rating is so high: the fuse is on the cell's positive, so the charging current flows through it too ({1} A; all of it if only one cell is fitted) — a smaller one blows on the first charge.
tr: Yuvalar yerinden oynamıyor (silikon soğuduktan sonra elle it).
en: The holders do not move (push them by hand once the glue has cooled).
tr: Kapak kapanıyor: YUVA2'nin üstü kapağa değmiyor.
en: The lid closes: the top of YUVA2 does not touch the lid.
tr: Silikon soğuyunca modülleri elle it; oynamamalı.
en: Once the glue has cooled, push the modules by hand; they should not move.
tr: B0505S'in giriş ({0}, {1}) ve çıkış ({2}, {3}) telleri arasında bip: ötmemeli.
en: Beep between the input ({0}, {1}) and output ({2}, {3}) wires of the B0505S: should not beep.
tr: <span class='ano'>{0}</span> <b>Pil paketini kablola (iki hücre paralel)</b>
en: <span class='ano'>{0}</span> <b>Wire the battery pack (two cells in parallel)</b>
tr: TP1'in {0}'da lehimlediğin dört ucu (B+, B−, OUT+, OUT−) duvarla kart A arasındaki aralıktan geliyor; bandı sök, uçları aşağıdaki tabloya göre bağla.
en: The four ends of TP1 you soldered in {0} (B+, B−, OUT+, OUT−) come up through the gap between the wall and board A; remove the tape and connect the ends as in the table below.
tr: Aşağıdaki tabloya göre; hücreler <b>TAKILI DEĞİLKEN</b>. İki hücre <b>paralel</b>: her hücrenin artısı <b>KENDİ sigortasından</b> (F1P, F2) geçip TP4056'nın <b>B+</b>'sında birleşir, eksileri <b>B−</b>'de. <b>H1+ / H2+ doğrudan B+'ya GİTMEZ.</b> Neden: TP4056'nın koruma FET'i (FS8205) B− ile OUT− arasında; hücre uçlarındaki ya da hücre kablolarındaki bir kısa devre o FET'in DIŞINDA kalır, DW01A bunu <b>kesemez</b>. Paralelde bir de şu var: hücrelerden biri içeriden kısa devre olursa öbürü onu sigortasız doldurmaya çalışır.
en: Following the table below; with the cells <b>NOT INSERTED</b>. The two cells in <b>parallel</b>: each cell's positive goes <b>through ITS OWN fuse</b> (F1P, F2) and they join at the TP4056's <b>B+</b>, the negatives at <b>B−</b>. <b>H1+ / H2+ DO NOT GO straight to B+.</b> Why: the TP4056's protection FET (FS8205) is between B− and OUT−; a short at the cell ends or in the cell wires stays OUTSIDE that FET, the DW01A <b>cannot interrupt</b> it. And in parallel there is one more thing: if one cell shorts internally, the other tries to fill it with no fuse in between.
tr: Hücre telleri <b>yuvanın kendi telleri</b>: kırmızı (+, yaysız uç) doğrudan sigorta klipsine, siyah TP4056 B−'ye. F2'nin çıkışı arka duvar boyunca <b>F1P'nin çıkış klipsine</b> gelir; TP4056 B+'ya oradan tek tel gider (iki hücre burada paralel). Yuva teli tablodaki boydan kısa gelirse ek yap (lehim + makaron).
en: The cell wires are <b>the holder's own wires</b>: the red one (+, the end without the spring) straight to the fuse clip, the black one to TP4056 B−. F2's output runs along the back wall to <b>F1P's output clip</b>; a single wire goes from there to TP4056 B+ (the two cells are in parallel here). If a holder wire is shorter than the length in the table, splice it (solder + heat-shrink).
tr: TP4056'da paket <b>B±</b>'ye, yük <b>OUT±</b>'ye. En büyük akım şarjda {0} A (iki hücreye yarı yarıya); {1} mm² bunu rahat taşır, kalın kablo gerekmez.
en: On the TP4056 the pack goes to <b>B±</b>, the load to <b>OUT±</b>. The largest current is {0} A while charging (half to each cell); {1} mm² carries that easily, no heavy wire needed.
tr: <b>PİL anahtarı (SWP1)</b> paket tarafında: TP1.OUT+ → PİL → MT1 girişi. Kapalıyken MT1 hiç çekmez; kutunun tek anahtarı bu. KTS102'nin <b>orta</b> bacağı TP4056 OUT+'ya; öbür tel, anahtar AÇ konumundayken orta bacakla <b>öten</b> dış bacağa (multimetreyle bul).
en: <b>«PİL» switch (SWP1)</b> on the pack side: TP1.OUT+ → «PİL» → MT1 input. When off, MT1 draws nothing; this is the enclosure's only switch. The KTS102's <b>middle</b> pin to TP4056 OUT+; the other wire to the outer pin that <b>beeps</b> with the middle one when the switch is in the ON position (find it with a multimeter).
tr: MT1'in {0} V çıkışı ESP32'ye: devkit'te tek 5V pini var ve {1}'de J5 kablosunun 5V teli de oraya takılacak — <b>çatal</b> yap: dişi header'dan (CON018) tek pinlik bir parça kes, MT1'in {2} V telini ve J5 kablosunun 5V telini İKİSİNİ BİRDEN onun kuyruğuna lehimle, makaronla kapla; bu tek dişi uç devkit'in 5V pinine geçer (erkek pine erkek header takılmaz). GND için devkit'in ikinci GND pini.
en: MT1's {0} V output to the ESP32: the devkit has a single 5V pin and in {1} the 5V wire of the J5 cable also goes there — make a <b>Y-splice</b>: cut a single-pin piece off a female header (CON018), solder BOTH MT1's {2} V wire and the J5 cable's 5V wire to its tail, cover with heat-shrink; this single female end goes onto the devkit's 5V pin (a male header does not fit a male pin). For GND, the devkit's second GND pin.
tr: ⚠ <b>İlk takışta iki hücre aynı gerilimde olmalı (±{0} V)</b>: farklıysa yüksek olan alçak olanı büyük akımla doldurur. Takmadan önce ikisini ayrı ayrı ölç; fark büyükse önce <b>yalnız birini</b> tak ve {1}'daki gibi tam doldur ({2} V), çıkar, ötekini tak ve doldur, sonra ikisini birlikte tak.
en: ⚠ <b>At first insertion the two cells must be at the same voltage (±{0} V)</b>: otherwise the higher one fills the lower one with a large current. Measure both separately before inserting; if the difference is large, first insert <b>only one</b> and charge it fully as in {1} ({2} V), take it out, insert the other one and charge it, then insert both together.
tr: kabloları göster (çizimler ve 3B)
en: show cables (drawings and 3D)
tr: Arka duvar — içeriden bakış: bu adımın kabloları
en: Back wall — seen from inside: this step's cables
tr: Arka duvar içeriden — kablolar
en: Back wall from inside — cables
tr: kart A'nın arka kenarı (duvardan {0} mm önde)
en: back edge of board A ({0} mm in front of the wall)
tr: ESP32 (önde)
en: ESP32 (in front)
tr: ön → PİL anahtarı orta bacak
en: front → «PİL» switch middle pin
tr: ön → PİL anahtarı dış bacak (AÇ'ta ortayla öten)
en: front → «PİL» switch outer pin (beeps with the middle one when ON)
tr: artı ({0} V / {1} V)
en: positive ({0} V / {1} V)
tr: paket / kart GND
en: pack / board GND
tr: −{0} tarafı (B0505S çıkışı)
en: −{0} side (B0505S output)
tr: hücre → sigorta → TP4056
en: cell → fuse → TP4056
tr: sinyal (J5, CAL)
en: signal (J5, CAL)
tr: kondansatör bacağı
en: capacitor leg
tr: arka duvar İÇERİDEN · jak tarafından bakış · x soldan, z yerden · soluk = önceki adımların kabloları · uç yerleri ±{0} mm tahmin
en: back wall FROM INSIDE · seen from the jack side · x from the left, z from the floor · faded = cables from earlier steps · end positions ±{0} mm estimate
tr: Kuşbakışı — kablolar
en: Top view — cables
tr: Kablolar — çizimdeki numaralarla (satıra dokun: çizimde yanar)
en: Cables — with the numbers in the drawing (tap a row: it lights up in the drawing)
tr: <b>{0}. yuvanın kırmızı teli</b>
en: <b>red wire of holder {0}</b>
tr: <b>F1P klips {0}</b>
en: <b>F1P clip {0}</b>
tr: yuvanın sol ucundan duvar dibine iner, F1P'nin üstünden girer
en: runs down from the left end of the holder to the bottom of the wall, enters above F1P
tr: <b>yuvanın kendi teli: {0} cm gerekir (uzunsa kes, kısaysa ek)</b>
en: <b>the holder's own wire: {0} cm needed (cut if long, splice if short)</b>
tr: <span class='kucuk'>hücre {0} artı → kendi sigortası (yuva ucundan, kırmızı)</span>
en: <span class='kucuk'>cell {0} positive → its own fuse (from the holder end, red)</span>
tr: <b>F1P klips {0} (çıkış)</b>
en: <b>F1P clip {0} (output)</b>
tr: <b>TP4056 B+ teli</b>
en: <b>TP4056 B+ wire</b>
tr: duvar ile kart A arasındaki aralıktan TP4056'nın teline
en: through the gap between the wall and board A to the TP4056's wire
tr: <b>TP4056'nın kendi teli: pedden {0} cm'de kes</b>
en: <b>the TP4056's own wire: cut it {0} cm from the pad</b>
tr: <span class='kucuk'>sigorta → TP4056 B+</span>
en: <span class='kucuk'>fuse → TP4056 B+</span>
tr: <b>F2 klips {0}</b>
en: <b>F2 clip {0}</b>
tr: {0}. yuvanın sağ ucundan sağ alt köşeye iner
en: runs down from the right end of holder {0} to the bottom right corner
tr: <span class='kucuk'>hücre {0} artı → kendi sigortası (paralelde her hücrenin ayrı sigortası şart)</span>
en: <span class='kucuk'>cell {0} positive → its own fuse (in parallel, each cell must have its own fuse)</span>
tr: <b>F2 klips {0} (çıkış)</b>
en: <b>F2 clip {0} (output)</b>
tr: ESP32'nin üstünden, {0}. yuvanın altından (yerden {1} mm) arka duvar boyunca sola
en: over the ESP32, under holder {0} ({1} mm off the floor), to the left along the back wall
tr: <span class='kucuk'>sigorta → F1P'nin çıkış klipsi = TP4056 B+ düğümü (iki hücre burada paralel)</span>
en: <span class='kucuk'>fuse → F1P output clip = TP4056 B+ node (the two cells are in parallel here)</span>
tr: <b>{0}. yuvanın siyah teli</b>
en: <b>black wire of holder {0}</b>
tr: <b>TP4056 B− teli</b>
en: <b>TP4056 B− wire</b>
tr: yuvanın sol ucundan aralığa iner, TP4056'nın teline
en: runs down from the left end of the holder into the gap, to the TP4056's wire
tr: <b>yuvanın kendi teli: {0} cm gerekir (uzunsa kes, kısaysa ek); TP4056'nın telini pedden {1} cm'de kes, ikisini orada birleştir (lehim + makaron)</b>
en: <b>the holder's own wire: {0} cm needed (cut if long, splice if short); cut the TP4056's wire {1} cm from the pad, join the two there (solder + heat-shrink)</b>
tr: <span class='kucuk'>hücre {0} eksi — siyah</span>
en: <span class='kucuk'>cell {0} negative — black</span>
tr: {0}. yuvanın sol (yaylı) ucundan aralığa iner, TP4056'nın teline
en: runs down from the left (spring) end of holder {0} into the gap, to the TP4056's wire
tr: <span class='kucuk'>hücre {0} eksi — siyah (paralel)</span>
en: <span class='kucuk'>cell {0} negative — black (parallel)</span>
tr: <b>TP4056 OUT+ teli</b>
en: <b>TP4056 OUT+ wire</b>
tr: <b>PİL anahtarı orta bacak</b>
en: <b>«PİL» switch middle pin</b>
tr: aralıktan yukarı, kapağın altından öne, PİL anahtarına
en: up through the gap, forward under the lid, to the «PİL» switch
tr: <b>TP4056'nın kendi teli: pedden {0} cm gerekir — tel ~{1} cm, {2} cm ek (lehim + makaron)</b>
en: <b>the TP4056's own wire: {0} cm needed from the pad — wire ~{1} cm, {2} cm splice (solder + heat-shrink)</b>
tr: <span class='kucuk'>korumalı çıkış (B+ değil!) → PİL anahtarı</span>
en: <span class='kucuk'>protected output (not B+!) → «PİL» switch</span>
tr: <b>PİL anahtarı dış bacak (AÇ'ta ortayla öten)</b>
en: <b>«PİL» switch outer pin (beeps with the middle one when ON)</b>
tr: PİL anahtarından kapağın altından arkaya, MT1'in sağ ucuna
en: from the «PİL» switch back under the lid, to the right end of MT1
tr: <span class='kucuk'>anahtar paket tarafında: kapalıyken MT1 hiç çekmez</span>
en: <span class='kucuk'>switch on the pack side: when off, MT1 draws nothing</span>
tr: <b>TP4056 OUT− teli</b>
en: <b>TP4056 OUT− wire</b>
tr: kısa yoldan, parçaların önünden
en: by the short route, in front of the parts
tr: <span class='kucuk'>eksi doğrudan</span>
en: <span class='kucuk'>negative, direct</span>
tr: <b>ESP32 5V pini</b>
en: <b>ESP32 5V pin</b>
tr: <span class='kucuk'>{0} V → devkit 5V/VIN pini (J5 kablosunun 5V teliyle çatal)</span>
en: <span class='kucuk'>{0} V → devkit 5V/VIN pin (Y-splice with the 5V wire of the J5 cable)</span>
tr: <b>ESP32 GND pini (ikinci)</b>
en: <b>ESP32 GND pin (the second one)</b>
tr: <span class='kucuk'>= kart GND (ESP32 üzerinden). Paket eksisi bu düğümde.</span>
en: <span class='kucuk'>= board GND (via the ESP32). The pack negative is on this node.</span>
tr: Uç adları: H1±/H2± hücre uçları · TP1.B±/OUT± şarj modülü · MT1/MT2.IN±/OUT± yükselticiler · IZ.IN± = B0505S bacak {0}/{1}, IZ.OUT± = bacak {2}/{3} (gövdede ad yok) · KL.± iç klemens · A.C34/C36 kartın {4} V telleri. Denetim bu listeden düğüm grafını kurup kartın −{5} rayının kart GND'den ayrı kaldığını ölçüyor — iki taraf yalnız B0505S'in içinden ayrılıyor.
en: End names: H1±/H2± cell ends · TP1.B±/OUT± charging module · MT1/MT2.IN±/OUT± boost converters · IZ.IN± = B0505S pins {0}/{1}, IZ.OUT± = pins {2}/{3} (no names on the body) · KL.± internal terminal block · A.C34/C36 the board's {4} V wires. The audit builds the node graph from this list and checks that the board's −{5} rail stays separate from board GND — the two sides are separated only inside the B0505S.
tr: {0}. ve {1}. yuvanın siyah teli ↔ TP4056 B−: ötmeli. F1P'nin ve F2'nin çıkış klipsi ↔ TP4056 B+: ötmeli.
en: Black wire of holders {0} and {1} ↔ TP4056 B−: should beep. Output clip of F1P and of F2 ↔ TP4056 B+: should beep.
tr: Paket eksisi kart GND'ye J5 kablosuyla bağlanır — o kontrol {0}'de (şimdi ötmemesi NORMAL: FS8205'in gövde diyotları hücresizken B− ile OUT−'yu da ayrı tutar).
en: The pack negative is connected to board GND through the J5 cable — that check is in {0} (it is NORMAL that it does not beep now: without cells, the body diodes of the FS8205 also keep B− and OUT− apart).
tr: PİL kapalı: TP1.OUT+ ↔ MT1.IN+ ötmemeli; açık: ötmeli.
en: «PİL» off: TP1.OUT+ ↔ MT1.IN+ should not beep; on: should beep.
tr: F1P çıkarılınca H1+ ↔ TP1.B+ kesik; F2 çıkarılınca H2+ ↔ TP1.B+ kesik (her sigorta gerçekten kendi hücresinin yolunda).
en: With F1P removed, H1+ ↔ TP1.B+ is open; with F2 removed, H2+ ↔ TP1.B+ is open (each fuse really is in its own cell's path).
tr: <span class='ano'>{0}</span> <b>Analog beslemeyi kablola: {1} V → F0 → B0505S → MT2 → klemens → kart</b>
en: <span class='ano'>{0}</span> <b>Wire the analog supply: {1} V → F0 → B0505S → MT2 → terminal block → board</b>
tr: {0} V girişi. Tezgahta: XT30 (CON058) — kart tarafı ERKEK uç (pimli), güç kaynağı tarafı DİŞİ uç; gerilim taşıyan taraf kapalı soketli olsun. Kablo yalıtımlı, kırmızı = +, siyah = −. Kutuda (B58): XT30 kesilir, teller iç klemense (KL) — {1} V'u kutunun kendi pili (MT2) verir, dış besleme yok.
en: {0} V input. At the bench: XT30 (CON058) — MALE end on the board side (with pins), FEMALE end on the power-supply side; the side carrying voltage should have the shrouded socket. Insulated wire, red = +, black = −. In the enclosure (B58): the XT30 is cut off, the wires go to the internal terminal block (KL) — the {1} V comes from the enclosure's own battery (MT2), no external supply.
tr: Kartın {0} V girişinin telleri (<b>J6</b>: C34 kırmızı, C36 siyah) klemense <b>vidalanır</b> — kart lehim sökmeden çıkar. Tellerin ucunda tezgahtan kalan <b>XT30 erkek</b> varsa kes: dış besleme yok, XT30 kullanılmıyor.
en: The wires of the board's {0} V input (<b>J6</b>: C34 red, C36 black) are <b>screwed</b> into the terminal block — the board comes out without desoldering. If the wire ends still have the <b>XT30 male</b> from the bench, cut it off: no external supply, the XT30 is not used.
tr: Aşağıdaki tabloya göre: {0} V barası (MT1 çıkışı) → <b>F0</b> ({1} A hızlı, FUS003, kutu içi, {2}) → B0505S bacak {3} (+Vin); bacak {4} (−Vin) → {5} V barasının eksisi. B0505S bacak {6} (+Vout) → MT2 IN+, bacak {7} (−Vout) → MT2 IN−; MT2 çıkışı → klemens (+ → C34, − → C36).
en: Following the table below: {0} V bus (MT1 output) → <b>F0</b> ({1} A fast, FUS003, inside the enclosure, {2}) → B0505S pin {3} (+Vin); pin {4} (−Vin) → the negative of the {5} V bus. B0505S pin {6} (+Vout) → MT2 IN+, pin {7} (−Vout) → MT2 IN−; MT2 output → terminal block (+ → C34, − → C36).
tr: <b>CB ({0} µF)</b> MT2'nin giriş uçlarına, B0505S'in telleriyle aynı noktaya: uzun bacak → IN+, şeritli bacak → IN−. Neden: açılışta MT2 kartın {1} µF'sini doldururken B0505S'in veremeyeceği tepe akımı çekiyor; kondansatör yoksa MT2 girişini çökertip baştan başlıyor ve kart {2} V'a çıkamayabilir (B58f benzetimi).
en: <b>CB ({0} µF)</b> on MT2's input terminals, at the same point as the B0505S wires: long leg → IN+, striped leg → IN−. Why: at power-up, while charging the board's {1} µF, MT2 draws a peak current the B0505S cannot supply; without the capacitor MT2 collapses its input and starts over, and the board may not reach {2} V (B58f simulation).
tr: <b>Kural (denetimli):</b> B0505S'in çıkış tarafı (MT2 girişi, klemens −, kartın −{0} rayı) kart GND'ye hiçbir yoldan <b>DEĞMEZ</b>. Kutunun iki toprağını ayıran tek parça B0505S: iki tarafı birleştiren tek bir tel −{1}'yi GND'ye kısa eder.
en: <b>Rule (audited):</b> the B0505S's output side (MT2 input, terminal −, the board's −{0} rail) <b>DOES NOT TOUCH</b> board GND by any path. The B0505S is the only part separating the enclosure's two grounds: a single wire joining the two sides shorts −{1} to GND.
tr: Neden F0 {0} V tarafında: analog zincirindeki bir arıza (B0505S, MT2, kart) paketi ve {1} V barasını çekemesin. {2} V tarafını ayrıca korumaya gerek yok — kartın kendi F1'i orada, B0505S'in gücü de {3}–{4} W ile sınırlı ve kısa devrede kendini keser.
en: Why F0 is on the {0} V side: a fault in the analog chain (B0505S, MT2, board) must not be able to pull down the pack and the {1} V bus. The {2} V side needs no separate protection — the board's own F1 is there, and the B0505S's power is limited to {3}–{4} W and it shuts itself off on a short.
tr: Sigorta: kartta F1. Açılışta kartın {0} µF'si dolar; B58'den beri anahtar {1} V tarafında ve {2} V B0505S + MT2 üzerinden yükseliyor, yani darbe sert bir {3} V kaynağındakinden yumuşak — ama hesap en kötü hâli (sert kaynak) varsayıyor: gerçek bir {4} mA <b>hızlı</b> (F) sigortayı bu darbe <b>atar</b> (darbe I²t erime değerinin {5}–{6} katı — Littelfuse {7}/{8} veri sayfaları, denetim hesaplıyor). <b>Karar ({9}-{10}-{11}): takılı sigorta kalıyor, T sonraki plana.</b> Şu an yuvada '{12} mA' duruyor ve {13}+ açmada <b>hiç atmadı</b> — bu tek başına iyi haber ama <i>hangi</i> sigorta olduğunu söylemiyor: gerçek bir {14} mA F bu darbede atardı. B52'de ölçülen <b>{15} Ω</b>, {16} mA olamaz ({17} mA'lık tel {18}–{19} Ω okur) — {20} Ω <b>{21} mA</b> sınıfıdır. İkisi birlikte tek bir şey söylüyor: yuvadaki etikete bakma, <b>ohmmetreye bak</b>. Merak edersen sigortayı çıkar, soğukken direncini ölç: <b>{22}–{23} Ω</b> → gerçekten {24} mA (o zaman T tipidir, çünkü atmadı); <b>{25} Ω</b> civarı → {26} mA sınıfı (FUS001). Her iki hâlde de <b>kısa devre koruması var</b> ve kutu kurulumu beklemiyor. İleride <b>T (gecikmeli) {27} mA cam</b> (Littelfuse {28} / ESKA / Schurter, pay ≥ {29}×) alınırsa takılır ve {30} kez aç-kapa denenir: her açılışta +{31}/−{32} gelmeli. Stoktaki FUS010 F tipi, {33} mA F de darbeye pay vermiyor — ikisi de değiştirmeye değmez. TL072 kısmi arızasını hiçbir sigorta açmaz.
en: Fuse: F1 on the board. At power-up the board's {0} µF charges; since B58 the switch is on the {1} V side and the {2} V rises through the B0505S + MT2, so the surge is softer than from a stiff {3} V source — but the calculation assumes the worst case (stiff source): this surge <b>blows</b> a genuine {4} mA <b>fast</b> (F) fuse (the surge I²t is {5}–{6} times the melting value — Littelfuse {7}/{8} datasheets, the audit calculates it). <b>Decision ({9}-{10}-{11}): the fitted fuse stays, T goes to the later plan.</b> Right now the holder has a '{12} mA' in it and it has <b>never blown</b> in {13}+ power-ups — good news on its own, but it does not tell you <i>which</i> fuse it is: a genuine {14} mA F would blow on this surge. The <b>{15} Ω</b> measured in B52 cannot be {16} mA (a {17} mA wire reads {18}–{19} Ω) — {20} Ω is the <b>{21} mA</b> class. Together they say one thing: ignore the label in the holder, <b>trust the ohmmeter</b>. If you are curious, take the fuse out and measure its cold resistance: <b>{22}–{23} Ω</b> → really {24} mA (then it is a T type, since it did not blow); around <b>{25} Ω</b> → {26} mA class (FUS001). Either way there <b>is short-circuit protection</b> and the build does not wait on it. If a <b>T (time-delay) {27} mA glass</b> fuse (Littelfuse {28} / ESKA / Schurter, margin ≥ {29}×) is bought later, it is fitted and switched on and off {30} times: +{31}/−{32} must come up every time. The FUS010 in stock is an F type, and a {33} mA F gives no margin on the surge either — neither is worth swapping in. No fuse opens on a partial TL072 failure.
tr: <b>GÜÇ lambası:</b> {0} kΩ direnci (R060) LED'in <b>uzun bacağına</b> lehimle, makaronla kapat; direncin öbür ucu <b>klemensin ARTI</b> ucuna (KL.+ = +{1} rayı). LED'in kısa bacağı (katot) <b>COM jakının lehim kulağına</b> (= kart GND; tablodaki kablo {2}, {3} cm). ⚠ MT1'in eksisine bağlama: o nokta kart GND'ye ancak {4}'deki J5 ile bağlanır, {5}'te lamba yanmaz. ⚠ Klemensin EKSİ ucuna da bağlama: −{6} rayıdır, {7} o yönde akım veremez, ray kayar.
en: <b>«GÜÇ» lamp:</b> solder the {0} kΩ resistor (R060) to the LED's <b>long leg</b>, cover with heat-shrink; the resistor's other end to the <b>POSITIVE</b> screw of the terminal block (KL.+ = +{1} rail). The LED's short leg (cathode) to the <b>solder lug of the COM jack</b> (= board GND; cable {2} in the table, {3} cm). ⚠ Do not connect it to MT1's negative: that point only joins board GND through J5 in {4}, in {5} the lamp would not light. ⚠ Do not connect it to the NEGATIVE screw of the terminal block either: that is the −{6} rail, {7} cannot source current in that direction, the rail drifts.
tr: ön → kart A C34 teli ({0} V +)
en: front → board A C34 wire ({0} V +)
tr: ön → kart A C36 teli (−{0})
en: front → board A C36 wire (−{0})
tr: ön → GÜÇ LED'i uzun bacak ({0} kΩ ile)
en: front → «GÜÇ» LED long leg (via {0} kΩ)
tr: ön → GÜÇ LED'i kısa bacak
en: front → «GÜÇ» LED short leg
tr: ön → COM jakının lehim kulağı
en: front → solder lug of the COM jack
tr: <b>F0 klips {0}</b>
en: <b>F0 clip {0}</b>
tr: <span class='kucuk'>{0} V barası → F0 (kutu içi sigorta, {1} A)</span>
en: <span class='kucuk'>{0} V bus → F0 (fuse inside the enclosure, {1} A)</span>
tr: <span class='kucuk'>B0505S GND — kart GND tarafı</span>
en: <span class='kucuk'>B0505S GND — board GND side</span>
tr: <span class='kucuk'>yalıtılmış {0} V (+Vo) → MT2</span>
en: <span class='kucuk'>isolated {0} V (+Vo) → MT2</span>
tr: <b>MT2 IN− (−{0} tarafı)</b>
en: <b>MT2 IN− (−{0} side)</b>
tr: <span class='kucuk'>yalıtılmış 0V → MT2 eksisi — bu uç −{0} rayı olur, kart GND'ye DEĞMEZ</span>
en: <span class='kucuk'>isolated 0V → MT2 negative — this end becomes the −{0} rail, it DOES NOT TOUCH board GND</span>
tr: <b>{0} µF uzun bacak</b>
en: <b>{0} µF long leg</b>
tr: kondansatörün kendi bacağı
en: the capacitor's own leg
tr: <span class='kucuk'>{0} µF artısı (uzun bacak) → MT2 IN+ (B0505S +Vo ile aynı nokta)</span>
en: <span class='kucuk'>{0} µF positive (long leg) → MT2 IN+ (same point as B0505S +Vo)</span>
tr: <b>{0} µF şeritli bacak</b>
en: <b>{0} µF striped leg</b>
tr: <span class='kucuk'>{0} µF eksisi (şeritli bacak) → MT2 IN− — −{1} rayı tarafı</span>
en: <span class='kucuk'>{0} µF negative (striped leg) → MT2 IN− — the −{1} rail side</span>
tr: <b>KL + vidası</b>
en: <b>KL + screw</b>
tr: <span class='kucuk'>{0} V → klemens +</span>
en: <span class='kucuk'>{0} V → terminal +</span>
tr: <b>KL − vidası</b>
en: <b>KL − screw</b>
tr: <span class='kucuk'>{0} V eksisi → klemens −</span>
en: <span class='kucuk'>{0} V negative → terminal −</span>
tr: <b>kart A C34 teli ({0} V +)</b>
en: <b>board A C34 wire ({0} V +)</b>
tr: klemensten kart A'nın üstünden öne, kartın ön kenarındaki tele
en: from the terminal block forward over board A, to the wire at the board's front edge
tr: <span class='kucuk'>klemens → kart {0} V + (T_24P)</span>
en: <span class='kucuk'>terminal → board {0} V + (T_24P)</span>
tr: <b>kart A C36 teli (−{0})</b>
en: <b>board A C36 wire (−{0})</b>
tr: <span class='kucuk'>klemens → kart {0} V − (T_24N = −{1} rayı)</span>
en: <span class='kucuk'>terminal → board {0} V − (T_24N = −{1} rail)</span>
tr: <b>GÜÇ LED'i uzun bacak ({0} kΩ ile)</b>
en: <b>«GÜÇ» LED long leg (via {0} kΩ)</b>
tr: klemensten kart A'nın üstünden öne, GÜÇ lambasına
en: from the terminal block forward over board A, to the «GÜÇ» lamp
tr: <span class='kucuk'>{0} kΩ (R060) LED'in uzun bacağına lehimli, makaronlu</span>
en: <span class='kucuk'>{0} kΩ (R060) soldered to the LED's long leg, heat-shrunk</span>
tr: <b>GÜÇ LED'i kısa bacak</b>
en: <b>«GÜÇ» LED short leg</b>
tr: <b>COM jakının lehim kulağı</b>
en: <b>solder lug of the COM jack</b>
tr: <span class='kucuk'>katot → COM jakının lehim kulağı = kart GND (J5'ten önce de lamba yanar)</span>
en: <span class='kucuk'>cathode → solder lug of the COM jack = board GND (the lamp lights even before J5)</span>
tr: B0505S bacak {0} (−Vin) ↔ bacak {1} (−Vout): <b>ötmemeli</b> (yalıtım sağlam).
en: B0505S pin {0} (−Vin) ↔ pin {1} (−Vout): <b>should not beep</b> (isolation intact).
tr: Klemens − (C36) ↔ kart GND (C29): ötmemeli.
en: Terminal − (C36) ↔ board GND (C29): should not beep.
tr: <b>Kutup (enerjiden ÖNCE):</b> klemens + ↔ MT2 OUT+ ve kartın C34'ü ötmeli; klemens − ↔ MT2 OUT− ve C36 ötmeli. Ters olursa ilk enerjide iki TL072 ölür (XT30 kodluydu, klemens değil).
en: <b>Polarity (BEFORE power):</b> terminal + ↔ MT2 OUT+ and the board's C34 should beep; terminal − ↔ MT2 OUT− and C36 should beep. If reversed, both TL072s die at the first power-up (the XT30 was keyed, the terminal block is not).
tr: F0 takılıyken {0} V barası ↔ B0505S Vin bağlı; F0 çıkarılınca kesik (sigorta gerçekten yolda).
en: With F0 fitted, the {0} V bus ↔ B0505S Vin is connected; with F0 removed, open (the fuse really is in the path).
tr: <b>CB kutbu (enerjiden ÖNCE):</b> kondansatörün şeritli bacağı ↔ MT2 IN− ötmeli; ters takılan elektrolitik ilk enerjide ısınır ve patlar.
en: <b>CB polarity (BEFORE power):</b> the capacitor's striped leg ↔ MT2 IN− should beep; an electrolytic fitted backwards heats up and bursts at the first power-up.
tr: <span class='ano'>{0}</span> <b>Kutuda ilk enerji — pilden</b>
en: <span class='ano'>{0}</span> <b>First power-up in the enclosure — from the battery</b>
tr: Soketlerdeki entegreler takılı değil ({0}'de takılacak), J5 kablosu takılı değil, PİL KAPALI, USB takılı değil, <b>F0 yuvasında sigorta YOK</b> (ölçüm tarafı önce kapalı kalsın).
en: The socketed ICs are not fitted (they go in during {0}), the J5 cable is not connected, «PİL» OFF, no USB plugged in, <b>NO fuse in the F0 holder</b> (the measurement side stays off at first).
tr: Hücreleri tak (kutuplara dikkat; ±{0} V kuralı {1}'te). <b>PİL AÇ</b>: {2} V barasında {3}–{4} V, ESP32 açılır. Klon devkit'te VBUS diyotu olmayabilir: USB soketinin VBUS ucunda <b>{5} V</b> oku. {6} V okursan MT1 USB'ye geri besliyor → ESP32'ye giden {7} V telinin arasına stoktaki Schottky <b>SR5100</b> (D004; çizgili uç ESP32'ye) koy, makaronla kapla ve MT1'i <b>{8} V</b>'a çıkar (diyotta ~{9} V düşer).
en: Insert the cells (mind the polarity; the ±{0} V rule is in {1}). <b>«PİL» ON</b>: {3}–{4} V on the {2} V bus, the ESP32 starts. A clone devkit may have no VBUS diode: read <b>{5} V</b> on the VBUS pin of the USB socket. If you read {6} V, MT1 is back-feeding the USB → put the Schottky <b>SR5100</b> from stock (D004; striped end to the ESP32) in the {7} V wire going to the ESP32, cover it with heat-shrink and raise MT1 to <b>{8} V</b> (~{9} V drops across the diode).
tr: PİL'i kapat, <b>F0'ı tak</b> ({0} A), PİL'i yeniden aç: klemenste {1} V, kartta +{2} V / −{3} V (V35 / R33, GND: V36); GÜÇ lambası yanar.
en: Switch «PİL» off, <b>fit F0</b> ({0} A), switch «PİL» back on: {1} V at the terminal block, +{2} V / −{3} V on the board (V35 / R33, GND: V36); the «GÜÇ» lamp lights.
tr: <b>Kutu açılmazsa</b> (PİL açınca ESP32 hiç açılmıyor ya da bir an yanıp sönüyor, GÜÇ lambası yanmıyor): paketin koruması (DW01A) açılış akımında kesmiş. PİL'i kapat, {0} saniye bekle, yeniden aç. Sürerse pili {1}'daki gibi <b>doldur</b> ve dene — benzetimde dolu pilde B0505S'in dört davranış modelinin hepsi açılıyor. Dolu pilde de açılmıyorsa: PİL'i kapat, B0505S'in +Vo teli ile MT2'nin IN+ ucu arasına <b>{2} × {3} Ω {4} W</b> direnci (R052) seri lehimle, makaronla kapla, dene. Yine olmuyorsa TP4056 modülünü stoktaki yedekle değiştir (MOD002, {5}'daki gibi). <b>{6} V gelmiyorsa</b> (ESP32 açık ama klemenste {7} V yok ya da GÜÇ lambası yanıp sönüyor): seri direnç takılıysa <b>çıkar</b> — bu B0505S aşırı yükte kapanıp yeniden deneyen türden, direnç ona fazla gelir; takılı değilse CB'nin iki bacağının MT2 girişine lehimli olduğuna ve kutbuna bak.
en: <b>If the enclosure does not power up</b> (with «PİL» on the ESP32 does not start at all or flashes once, the «GÜÇ» lamp does not light): the pack protection (DW01A) has tripped on the inrush current. Switch «PİL» off, wait {0} seconds, switch it on again. If it persists, <b>charge</b> the battery as in {1} and try — in the simulation all four behaviour models of the B0505S start up with a full battery. If it does not start with a full battery either: switch «PİL» off, solder the <b>{2} × {3} Ω {4} W</b> resistor (R052) in series between the B0505S's +Vo wire and MT2's IN+ terminal, cover with heat-shrink, try. If it still fails, replace the TP4056 module with the spare from stock (MOD002, as in {5}). <b>If {6} V does not come up</b> (the ESP32 is on but there is no {7} V at the terminal block, or the «GÜÇ» lamp blinks): if the series resistor is fitted, <b>remove it</b> — this B0505S is the type that shuts down on overload and retries, the resistor is too much for it; if it is not fitted, check that both legs of CB are soldered to MT2's input and its polarity.
tr: Skopla −{0} rayına bak (MT3608 + B0505S dalgalanması): {1} mV üstü görürsen MT2 çıkışına {2} µF {3} V (C035) + {4} nF (C008) ekle ({5}.23'ün gürültü endişesi burada ölçülür). ⚠ Stoktaki {6} µF'lerin çoğu {7} V — {8} V rayına TAKMA, patlar.
en: Look at the −{0} rail with the scope (MT3608 + B0505S ripple): if you see more than {1} mV, add {2} µF {3} V (C035) + {4} nF (C008) at MT2's output (the noise concern of {5}.23 is measured here). ⚠ Most of the {6} µF capacitors in stock are {7} V — DO NOT FIT them on the {8} V rail, they burst.
tr: 🛑 <b>Ölçtükten sonra PİL'i KAPAT.</b> Sıradaki adım ({0}) soketlere entegre, ADS modülü ve {1} telli J5 kablosu takıyor — bunlar <b>enerjili karta takılmaz</b>: yanlış oturan bir entegre ya da ters takılan bir modül anında ölür.
en: 🛑 <b>Switch «PİL» OFF after measuring.</b> The next step ({0}) fits the ICs into their sockets, the ADS module and the {1}-wire J5 cable — these <b>are not plugged into a powered board</b>: a badly seated IC or a module plugged in backwards dies instantly.
tr: −{0} rayı ↔ kart GND arasında gerilim <b>≈ −{1} V</b> ({2} V okursan B0505S'in iki tarafı bir yerde birleşmiş — hemen kapat).
en: Voltage between the −{0} rail ↔ board GND <b>≈ −{1} V</b> (if you read {2} V, the two sides of the B0505S are joined somewhere — switch off at once).
tr: {0} dk sonra MT1, B0505S, MT2 ve {1} ılık, sıcak değil.
en: After {0} min, MT1, B0505S, MT2 and {1} are warm, not hot.
tr: <span class='ano'>{0}</span> <b>Şarj kuralı ve etiket</b>
en: <span class='ano'>{0}</span> <b>Charging rule and label</b>
tr: Şarj: <b>PİL anahtarını KAPAT</b>, sonra ŞARJ yuvasına <b>tek Type-C</b> tak — iki hücre birlikte dolar ({0} A, hücre başına yarısı). PİL açıkken şarj etme: TP4056 yük altında şarjı bitiremez.
en: Charging: <b>switch the «PİL» switch OFF</b>, then plug <b>a single Type-C</b> into the «ŞARJ» slot — both cells charge together ({0} A, half per cell). Do not charge with «PİL» on: under load the TP4056 cannot finish charging.
tr: ⚠ Şarj sırasında kutunun toprağı (COM) şarj cihazının toprağına bağlanır: <b>şarj ederken ölçüm yapma</b>, HV'de asla.
en: ⚠ While charging, the enclosure's ground (COM) is connected to the charger's ground: <b>do not measure while charging</b>, never on HV.
tr: Etiket (arka panele, ŞARJ yuvasının yanına): "ŞARJ: PİL kapalı · şarjda ölçüm yok".
en: Label (on the back panel, next to the «ŞARJ» slot): "CHARGE: battery switch off · no measuring while charging".
tr: TP4056'nın LED'i şarjda kırmızı, bitince mavi (kapak açıkken kart A'nın arka kenarından bakınca). Kapak kapalıyken ışık yuvanın kenarından ancak loş sızar — göremiyorsan ≈ {0} saat bekle.
en: The TP4056's LED is red while charging and blue when done (seen from the back edge of board A with the lid open). With the lid closed the light only leaks dimly around the edge of the slot — if you cannot see it, wait ≈ {0} hours.
tr: USB'yi çıkar, PİL AÇ: ESP32 açılıyor, WiFi paneli geliyor, GÜÇ lambası yanıyor — kutu tamamen kablosuz.
en: Unplug the USB, «PİL» ON: the ESP32 starts, the WiFi panel comes up, the «GÜÇ» lamp lights — the enclosure is completely wireless.
tr: <span class='ano'>{0}</span> <b>J5 kablosu ve entegreler</b>
en: <span class='ano'>{0}</span> <b>J5 cable and ICs</b>
tr: PİL KAPALI ({0}'te kapattın). Soketlere entegreleri tak: U3, U4 (LM358), U5, U8 (TL072). Çentik yönü.
en: «PİL» OFF (you switched it off in {0}). Fit the ICs into the sockets: U3, U4 (LM358), U5, U8 (TL072). Mind the notch.
tr: ADS modüllerini yuvalarına tak.
en: Plug the ADS modules into their sockets.
tr: J5 başlığına {0} telli kabloyu tak (eşleme Yerleşim {1}). <b>3V3 ile 5V'u karıştırma.</b>
en: Plug the {0}-wire cable onto header J5 (mapping in Layout {1}). <b>Do not mix up 3V3 and 5V.</b>
tr: CAL jakı: devkit GPIO10 pinine tek dişi jumper, ucuna {0} kΩ (R059) seri, jakın iç ucuna lehim; jumper'ı SCL (GPIO9) pininin yanından dikkatle ayır.
en: CAL jack: a single female jumper on the devkit's GPIO10 pin, {0} kΩ (R059) in series at its end, soldered to the inner end of the jack; carefully keep the jumper clear of the SCL (GPIO9) pin next to it.
tr: USB'yi devkit'in COM yazan soketine, arka yuvadan tak.
en: Plug the USB into the devkit's socket marked COM, through the back slot.
tr: ön → CAL jakının lehim kulağı
en: front → solder lug of the CAL jack
tr: <b>ESP32 pinleri (J5 kablosu)</b>
en: <b>ESP32 pins (J5 cable)</b>
tr: <b>kart A J5 başlığı</b>
en: <b>board A header J5</b>
tr: ESP32'den yukarı, kart A'nın üstünden J5 başlığına
en: up from the ESP32, over board A to header J5
tr: ince tel (jumper)
en: thin wire (jumper)
tr: <span class='kucuk'>{0} telli kablo; tel eşlemesi Yerleşim {1}</span>
en: <span class='kucuk'>{0}-wire cable; wire mapping in Layout {1}</span>
tr: <b>CAL jakının lehim kulağı</b>
en: <b>solder lug of the CAL jack</b>
tr: ESP32'den yukarı, kart B'nin üstünden (HV'ye ≥ {0} mm) öne, CAL jakına
en: up from the ESP32, forward over board B (≥ {0} mm from HV), to the CAL jack
tr: <span class='kucuk'>{0} kΩ seri direnç jakın iç ucunda, makaronlu</span>
en: <span class='kucuk'>{0} kΩ series resistor at the inner end of the jack, heat-shrunk</span>
tr: Entegre çentikleri doğru yönde.
en: IC notches the right way round.
tr: {0} tel doğru pinde.
en: {0} wires on the right pins.
tr: J5 takılınca, hücreler takılı değilken: TP4056 OUT− ↔ kart GND (C29): ötmeli (paket eksisi = kart GND; bağ ESP32'nin GND'si ve J5 üzerinden).
en: With J5 plugged in and the cells out: TP4056 OUT− ↔ board GND (C29): should beep (pack negative = board GND; joined through the ESP32's GND and J5).
tr: <span class='ano'>{0}</span> <b>Vref ve I²C kapıları</b>
en: <span class='ano'>{0}</span> <b>Vref and I²C GATEs</b>
tr: <b>Enerji:</b> PİL AÇ. Seri konsol için USB'yi PC'ye takabilirsin — PİL açıkken yükü pil taşır (MT1'in {0} V'u USB'nin ~{1} V'unu bastırır). <b>PİL kapalıyken USB takma:</b> ölçüm tarafı da PC'den beslenmeye çalışır (~{2} A, USB {3} portunun sınırına yakın).
en: <b>Power:</b> «PİL» ON. You can plug the USB into the PC for the serial console — with «PİL» on the battery carries the load (MT1's {0} V overrides the USB's ~{1} V). <b>Do not plug in USB with «PİL» off:</b> the measurement side also tries to run from the PC (~{2} A, close to the limit of a USB {3} port).
tr: <b>Kapı {0} — Vref.</b> Multimetre kart GND'ye referanslı: ① <b>TL431 katodu</b> = {1} V (±%{2} → {3}–{4} V). ② <b>U3'ün {5}. bacağı (delik A:R8)</b> = {6} V (±{7} mV). ③ Aynı ölçümü bölücüler bağlıyken tekrarla — <b>kaymıyorsa tampon çalışıyor.</b> <i>Tutmazsa:</i> ① yanlışsa TL431 yönü / 220R besleme; ① doğru ② yanlışsa U3 soketi, çentiği ya da U3'ün +{8} V beslemesi ({9} V'ta çıkış yeterince yükselmez).
en: <b>GATE {0} — Vref.</b> Multimeter referenced to board GND: ① <b>TL431 cathode</b> = {1} V (±{2}% → {3}–{4} V). ② <b>Pin {5} of U3 (hole A:R8)</b> = {6} V (±{7} mV). ③ Repeat the same measurement with the dividers connected — <b>if it does not shift, the buffer works.</b> <i>If it fails:</i> ① wrong → TL431 orientation / 220R feed; ① right, ② wrong → U3's socket, its notch, or U3's +{8} V supply (at {9} V the output does not rise high enough).
tr: <b>Kapı {0} — I²C.</b> Seri konsolda <code>#</code>: <b>0x48 ve 0x49 ikisi de</b> listede görünmeli. <i>Tutmazsa:</i> SDA/SCL ters, ADDR ucu boşta (0x48 = GND, 0x49 = +3V3) ya da pull-up yok. <b>Bir adres eksikken kalibrasyona geçme</b> — eksik olan kanal sessizce sıfır okur.
en: <b>GATE {0} — I²C.</b> In the serial console <code>#</code>: <b>both 0x48 and 0x49</b> must appear in the list. <i>If it fails:</i> SDA/SCL swapped, ADDR pin floating (0x48 = GND, 0x49 = +3V3) or no pull-up. <b>Do not go on to calibration with an address missing</b> — the missing channel silently reads zero.
tr: İki kapı da geçmeden Adım {0}'ye başlama.
en: Do not start Step {0} until both GATEs have passed.
tr: WiFi ayarları seri konsoldan: <code>Ns&lt;web parolası&gt;</code>, <code>Na&lt;ssid&gt;</code>, <code>Np&lt;parola&gt;</code>; durum <code>N?</code>.
en: WiFi settings from the serial console: <code>Ns&lt;web password&gt;</code>, <code>Na&lt;ssid&gt;</code>, <code>Np&lt;password&gt;</code>; status <code>N?</code>.
tr: <b>KAPI {0}</b> — Kılavuz <b>{1} Vref</b> kapısı: TL431 katodu ve U3A çıkışı (U3 soketine LM358 tak).
en: <b>GATE {0}</b> — Guide <b>{1} Vref</b> GATE: TL431 cathode and U3A output (fit an LM358 in the U3 socket).
tr: gerekli kart dışı parça: —
en: off-board parts needed: —
tr: <b>KAPI {0}</b> — Kılavuz <b>{1}</b>: firmware'de <code>#</code> — 0x48 ve 0x49 ikisi de görünmeli.
en: <b>GATE {0}</b> — Guide <b>{1}</b>: <code>#</code> in the firmware — both 0x48 and 0x49 must appear.
tr: Seri konsoldan (USB). Her komut ayarı NVS'e yazar. Kazanç kalibrasyonu (<code>i</code>, <code>g</code>) tam skalanın %{0}'inin altındaki değeri reddeder — 'en az' sütunu.
en: From the serial console (USB). Every command writes the setting to NVS. The gain calibration (<code>i</code>, <code>g</code>) rejects values below {0}% of full scale — the 'minimum' column.
tr: Ne yapar
en: What it does
tr: Ne zaman
en: When
tr: En az
en: Minimum
tr: Şönt değerini gir ({0} mΩ takılı)
en: Enter the shunt value ({0} mΩ fitted)
tr: Bir kez. {0} mΩ'a geçince s0.015 + Z.
en: Once. When changing to {0} mΩ: s0.015 + Z.
tr: Akım sıfırı
en: Current zero
tr: YÜK'e hiçbir şey bağlı değilken.
en: With nothing connected to «YÜK».
tr: Akım kazancı
en: Current gain
tr: Bilinen akım geçirirken; multimetrenin okuduğunu yaz.
en: While passing a known current; type in what the multimeter reads.
tr: {0} A ({1} mΩ takılıyken) · {2} A ({3} mΩ)
en: {0} A (with {1} mΩ fitted) · {2} A ({3} mΩ)
tr: NORMAL menzile geç
en: Switch to the NORMAL range
tr: V kanalı ±{0} V.
en: V channel ±{0} V.
tr: Gerilim sıfırı
en: Voltage zero
tr: V jakı boşta iken.
en: With the V jack open.
tr: Gerilim kazancı
en: Voltage gain
tr: Bilinen gerilimi verip multimetrenin okuduğunu yaz.
en: Apply a known voltage and type in what the multimeter reads.
tr: {0} V (NORMAL) · {1} V (YÜKSEK)
en: {0} V (NORMAL) · {1} V (HIGH)
tr: YÜKSEK menzile geç
en: Switch to the HIGH range
tr: HV kanalı; sonra tekrar z / g (eşik yüksek, aşağıya bak).
en: HV channel; then z / g again (the threshold is high, see below).
tr: Pil kesme gerilimi
en: Battery cut-off voltage
tr: Örnek: {0} için {1} V.
en: Example: {1} V for {0}.
tr: Bütün ayarları yaz
en: Print all settings
tr: Kalibrasyon sonunda oku, bir yere not et.
en: Read them at the end of calibration and note them down somewhere.
tr: <span class='ano'>{0}</span> <b>Kapı {1} — akım (iki aşamalı)</b>
en: <span class='ano'>{0}</span> <b>GATE {1} — current (two stages)</b>
tr: <b>Kural:</b> test kaynağı kutudan <b>bağımsız</b> olmalı. Kutunun kendi pil paketi OLAMAZ: paketin eksisi kart GND'dir, ondan YÜK'e akım çekersen dönüş akımı kart GND telinden (J5 kablosu) geçer — ölçüm bozulur, ince tel ısınır. Test kaynağı: <b>tezgah beslemesi</b> (WCT-{0}-{1} + MOD011 buck, <b>{2} V</b>'a ayarlı) → <b>{3} Ω {4} W (R049)</b> ≈ {5} A. WCT artık kutuya bağlı değil (B58): yalıtılmış bir test kaynağı.
en: <b>Rule:</b> the test source must be <b>independent</b> of the enclosure. It CANNOT be the enclosure's own battery pack: the pack negative is board GND, so if you draw current from it through «YÜK» the return current flows through the board GND wire (J5 cable) — the measurement is corrupted and the thin wire heats up. Test source: <b>bench supply</b> (WCT-{0}-{1} + MOD011 buck, set to <b>{2} V</b>) → <b>{3} Ω {4} W (R049)</b> ≈ {5} A. The WCT is no longer connected to the enclosure (B58): it is an isolated test source.
tr: Firmware kazanç kalibrasyonunu tam skalanın %{0}'inin ({1} kod) altında reddeder: {2} mΩ ile bu {3} A demek, {4} A yetmez. Kazanç düzeltmesi (<code>i</code>) şöntten bağımsızdır → <b>önce {5} mΩ (R044) tak</b>, <code>s0.015</code>, <code>Z</code> yüksüzken; buck + {6} Ω YÜK {7}–{8}'den seri, multimetre {9} A kademesi seriye, <code>i&lt;ölçülen&gt;</code>.
en: The firmware rejects a gain calibration below {0}% of full scale ({1} codes): with {2} mΩ that means {3} A, {4} A is not enough. The gain correction (<code>i</code>) is independent of the shunt → <b>fit the {5} mΩ (R044) first</b>, <code>s0.015</code>, <code>Z</code> with no load; buck + {6} Ω in series through «YÜK» {7}–{8}, multimeter on its {9} A range in series, <code>i&lt;measured&gt;</code>.
tr: Sonra <b>{0} mΩ'u tak</b>, <code>s0.005</code>, <code>Z</code>; aynı ~{1} A'i ölç: multimetreyle ±%{2} tutmalı. ≥{3} A için: buck {4} V + üç {5} Ω paralel ({6} Ω, ≈{7} A, {8} s; MOD011 {9} A'lik) ile <code>i</code>. Kabloları ters çevir: işaret değişmeli.
en: Then <b>fit the {0} mΩ</b>, <code>s0.005</code>, <code>Z</code>; measure the same ~{1} A: it should agree with the multimeter within ±{2}%. For ≥{3} A: buck {4} V + three {5} Ω in parallel ({6} Ω, ≈{7} A, {8} s; the MOD011 is rated {9} A) with <code>i</code>. Reverse the leads: the sign should change.
tr: <i>±%{0} tutmazsa:</i> şöntün görünen değeri {1} mΩ değil (veri sayfası ±%{2}, Kelvin lehiminin yeri mm başına ~%{3} oynatır). Kart <b>X</b> A, multimetre <b>Y</b> A okuyorsa <code>s</code> değerini {4} × X ÷ Y yap (ör. X {5}, Y {6} → <code>s0.00523</code>), <code>Z</code>, yeniden ölç. Ya da ≥{7} A yoluyla {8} mΩ takılıyken doğrudan <code>i</code> ver: o zaman şöntün gerçek değeri kazanca girer, <code>s</code>'ye dokunma.
en: <i>If it is not within ±{0}%:</i> the shunt's apparent value is not {1} mΩ (datasheet ±{2}%, the position of the Kelvin joint shifts it ~{3}% per mm). If the board reads <b>X</b> A and the multimeter <b>Y</b> A, set the <code>s</code> value to {4} × X ÷ Y (e.g. X {5}, Y {6} → <code>s0.00523</code>), <code>Z</code>, measure again. Or give <code>i</code> directly with the {8} mΩ fitted, using the ≥{7} A route: then the shunt's real value goes into the gain, do not touch <code>s</code>.
tr: <b>KAPI {0}</b> — Kılavuz <b>{1} Akım kanalı</b>: <code>Z</code> sıfırı, bilinen akım, ters akım.
en: <b>GATE {0}</b> — Guide <b>{1} Current channel</b>: <code>Z</code> zero, known current, reverse current.
tr: gerekli kart dışı parça: J3, RS
en: off-board parts needed: J3, RS
tr: <span class='ano'>{0}</span> <b>Kapı {1} — NORMAL gerilim</b>
en: <span class='ano'>{0}</span> <b>GATE {1} — NORMAL voltage</b>
tr: <code>n</code>; <b>V jakını kısa bir kabloyla COM'a bağla</b> (gerçek {0} V) ve <code>z</code>, sonra kabloyu çıkar. ⚠ Boştaki V jakında <code>z</code> verme: giriş havada kalır ve okuma Vref civarına (~{1} V) oturur; sıfır o noktaya kurulursa bütün okumalar o kadar kayar ({2}-{3}-{4} kartta: boşta {5} V, kısa devrede −{6} V). Bilinen gerilimi (tezgah beslemesi {7}–{8} V — kutunun kendi pili DEĞİL, {9} kuralı) V–COM'a ver, multimetreyle kıyasla, <code>g&lt;ölçülen&gt;</code>; ters bağla: işaret değişmeli.
en: <code>n</code>; <b>connect the V jack to COM with a short lead</b> (a real {0} V) and <code>z</code>, then remove the lead. ⚠ Do not give <code>z</code> with the V jack open: the input floats and the reading settles around Vref (~{1} V); if zero is set at that point every reading shifts by that much (on the {2}-{3}-{4} board: {5} V open, −{6} V shorted). Apply a known voltage (bench supply {7}–{8} V — NOT the enclosure's own battery, rule {9}) to V–COM, compare with the multimeter, <code>g&lt;measured&gt;</code>; connect it reversed: the sign should change.
tr: <b>KAPI {0}</b> — Kılavuz <b>{1} NORMAL</b>: <code>z</code>, <code>g&lt;volt&gt;</code>, ters giriş.
en: <b>GATE {0}</b> — Guide <b>{1} NORMAL</b>: <code>z</code>, <code>g&lt;volt&gt;</code>, reversed input.
tr: gerekli kart dışı parça: J1
en: off-board parts needed: J1
tr: <span class='ano'>{0}</span> <b>Kapı {1} — YÜKSEK gerilim</b>
en: <span class='ano'>{0}</span> <b>GATE {1} — HIGH voltage</b>
tr: <code>y</code>; önce <b>HV jakını kısa bir kabloyla COM'a bağla</b>, <code>z</code>, kabloyu çıkar ({0}'teki gibi; boştayken sıfırlama yapma). Sonra {1} V (tezgah beslemesi), sonra {2} V (WCT'nin kendi çıkışı). Kutu B58'den beri yalnız kendi pilinden çalışıyor: WCT kutuya bağlı değil, burada serbestçe test kaynağı olur. (Eski düzende WCT kutuyu beslerdi ve eksisi −{3} rayıydı — o kural kalktı.)
en: <code>y</code>; first <b>connect the HV jack to COM with a short lead</b>, <code>z</code>, remove the lead (as in {0}; do not zero it while open). Then {1} V (bench supply), then {2} V (the WCT's own output). Since B58 the enclosure runs only from its own battery: the WCT is not connected to the enclosure and can freely be the test source here. (In the old arrangement the WCT powered the enclosure and its negative was the −{3} rail — that rule is gone.)
tr: Kazanç kalibrasyonu ≥{0} V ister: iki <b>yalıtılmış</b> kaynağı seri bağla (varsa) ya da HV kazancını fabrika {1}'da bırak (bölücü %{2} metal film, hata ≤ %{3}). <b>Tek el kuralı.</b>
en: The gain calibration needs ≥{0} V: connect two <b>isolated</b> supplies in series (if you have them) or leave the HV gain at the factory {1} (divider {2}% metal film, error ≤ {3}%). <b>One-hand rule.</b>
tr: <b>KAPI {0}</b> — Kılavuz <b>{1} YÜKSEK</b>: <b>önce {2} V</b>, sonra kademeli. Tek el, eller uzakta.
en: <b>GATE {0}</b> — Guide <b>{1} HIGH</b>: <b>{2} V first</b>, then in steps. One hand, hands clear.
tr: gerekli kart dışı parça: J2
en: off-board parts needed: J2
tr: <span class='ano'>{0}</span> <b>Kapı {1} — osiloskop</b>
en: <span class='ano'>{0}</span> <b>GATE {1} — oscilloscope</b>
tr: Sinyal kaynağı: kartın CAL çıkışı — seri konsolda <code>X&lt;hz&gt;</code> ile aç, <code>x</code> ile kapat; panelde <b>CAL jakı → SKOP jakı</b> kısa kablo (COM zaten ortak). <code>t</code> komutlarıyla yakala; kare dalga ve frekans görünmeli. Genlik {0} V DEĞİL ≈{1} V görünür: CAL'in {2} kΩ seri direnci ile skop girişinin ~{3} kΩ'u (R20 {4} kΩ + R23 {5} kΩ) bölücü kurar, {6}/{7} ≈ %{8} (eski '{9} kΩ seri, ≤ %{10}' notu B55g'de {11} kΩ'a geçilince eskidi).
en: Signal source: the board's CAL output — switch it on with <code>X&lt;hz&gt;</code> in the serial console, off with <code>x</code>; on the panel a short lead <b>CAL jack → «SKOP» jack</b> (COM is already common). Capture with the <code>t</code> commands; a square wave and its frequency should appear. The amplitude shows as ≈{1} V, NOT {0} V: CAL's {2} kΩ series resistor and the scope input's ~{3} kΩ (R20 {4} kΩ + R23 {5} kΩ) form a divider, {6}/{7} ≈ {8}% (the old '{9} kΩ series, ≤ {10}%' note went out of date when B55g moved to {11} kΩ).
tr: <b>KAPI {0}</b> — Kılavuz <b>{1} Osiloskop</b>: bilinen kare dalga, <code>ta</code>.
en: <b>GATE {0}</b> — Guide <b>{1} Oscilloscope</b>: known square wave, <code>ta</code>.
tr: gerekli kart dışı parça: J4
en: off-board parts needed: J4
tr: <span class='ano'>{0}</span> <b>Kapı {1} — hızlı akım yolu</b>
en: <span class='ano'>{0}</span> <b>GATE {1} — fast current path</b>
tr: Dirençsel yük (tezgah beslemesi + {0} Ω, {1} kuralı) YÜK'ten; <code>w</code> → PF ≈ {2}.
en: Resistive load (bench supply + {0} Ω, rule {1}) through «YÜK»; <code>w</code> → PF ≈ {2}.
tr: <b>KAPI {0}</b> — Kılavuz <b>{1} Hızlı akım yolu</b>: dirençsel yükte <code>w</code> → PF ≈ {2}.
en: <b>GATE {0}</b> — Guide <b>{1} Fast current path</b>: <code>w</code> on a resistive load → PF ≈ {2}.
tr: <span class='ano'>{0}</span> <b>Kapı {1} — pil testi</b>
en: <span class='ano'>{0}</span> <b>GATE {1} — battery test</b>
tr: Failsafe: PİL kapalıyken ve RESET'te Q1 kapısı {0} V (PİL {1} ↔ PİL {2} ötmemeli).
en: Failsafe: with «PİL» off and during RESET, Q1's gate is {0} V («PİL» {1} ↔ «PİL» {2} should not beep).
tr: Pil yerine <b>tezgah beslemesi</b> (buck {0} V; kutudaki hücreler paketin parçası, çıkarma) + {1} Ω {2} W, PİL {3} – PİL {4} ve V jakıyla (KULLANIM: pil kapasitesi): <code>P3.5</code>, <code>p1</code> → ≈{5} A akmalı. Buck'ı yavaşça {6} V'a indir: kart testi <b>kesmeli</b> (akım {7}, Q1 kapısı {8} V). Kesme eşiğini böyle gerçek bir pilden daha kesin sınarsın.
en: Instead of a battery, a <b>bench supply</b> (buck {0} V; the cells in the enclosure are part of the pack, do not take them out) + {1} Ω {2} W, with «PİL» {3} – «PİL» {4} and the V jack (USE: battery capacity): <code>P3.5</code>, <code>p1</code> → ≈{5} A should flow. Slowly lower the buck to {6} V: the board <b>must stop</b> the test (current {7}, Q1 gate {8} V). This way you test the cut-off threshold more precisely than with a real battery.
tr: <b>KAPI {0}</b> — Pil testi: Q1 kapısı kart kapalıyken ve RESET'te <b>kapalı</b> kalmalı (tezgâh listesindeki failsafe kalemi).
en: <b>GATE {0}</b> — Battery test: Q1's gate must stay <b>off</b> with the board off and during RESET (the failsafe item in the bench list).
tr: gerekli kart dışı parça: J7, Q1, RS
en: off-board parts needed: J7, Q1, RS
tr: <span class='ano'>{0}</span> <b>Kapağı yap</b>
en: <span class='ano'>{0}</span> <b>Make the lid</b>
tr: Kapak sıralarını taban gibi diz (ek yerleri kaydırmalı), altına iki rayı direklerin arasına yapıştır. Raylar {0} mm yüzü dik (aşağı sarkar). ⚠ <b>Rayları yan duvara YASLAMA — her birini {1} mm içeri al</b> (toplam {2} mm geçme payı). Yaslarsan kapak takımı açıklığın tam kendisi kadar olur ve girmez; çubuk toleransı ve ahşabın nemle oynaması bu payı yiyor. Kapağı ters çevirip düz zeminde dizerken araya bir kartvizit koyarsan pay kendiliğinden çıkar.
en: Lay out the lid rows like the base (joints staggered), glue the two rails underneath between the posts. The rails with their {0} mm face upright (hanging down). ⚠ <b>DO NOT PUT the rails against the side wall — set each one {1} mm in</b> ({2} mm of fit clearance in total). If you put them against the wall, the lid assembly is exactly as wide as the opening and does not go in; stick tolerance and the wood moving with humidity eat up this clearance. If you put a business card in between while laying the lid upside down on a flat surface, the clearance comes out by itself.
tr: <b>Rayları del:</b> kapağı yerine koy, yan duvardaki dört Ø{0} deliğin arkasında {1} mm'lik kapak rayı var ve orada delik yok. Havya ucunu <b>dıştaki delikten geçirip rayı da del</b> — delik kılavuz olduğu için eş eksenli çıkar, işaretleme yok ({2}'deki iç kat yöntemi). Kapağı kaldırmadan yap.
en: <b>Drill the rails:</b> put the lid in place; behind the four Ø{0} holes in the side wall there is the {1} mm lid rail, with no hole yet. <b>Pass the iron tip through the outer hole and drill the rail too</b> — the hole is the guide so they come out coaxial, no marking (the inner layer method from {2}). Do it without lifting the lid.
tr: <b>Somunlu blokları KAPAK TEZGAHTAYKEN yapıştır — kutunun içinde değil.</b> Rayları deldikten sonra <b>kapağı kaldır</b> ve ters çevirip masaya koy (raylar yukarı). Her ray deliğine <b>dıştan</b> (rayın duvara bakan yüzünden) bir M3x12 cıvata sok; ucuna <b>gömme somunlu {0} katlı bloğu</b> ({1}. kat Ø{2} · {3}.–{4}. kat Ø{5} somun cebi · {6}. kat Ø{7}) — somunun dış yüzüne bir damla japon (japon, somunun DIŞ yüzüne — dişine değil), {8}'deki ayak bloğunun aynısı — vidala. Blok şimdi cıvatanın üstünde <b>kendi kendine merkezlenmiş</b> durumda: temas yüzüne japon sür, rayın iç yüzüne bastır. Kuruyunca cıvatayı sök. İki bağımsız ölçüm tutturmaya çalışmazsın; kapak kapalıyken içeride somun tutulamadığı için bu blok şart (B54).
en: <b>Glue the nut blocks WITH THE LID ON THE BENCH — not inside the enclosure.</b> After drilling the rails, <b>lift the lid off</b> and put it upside down on the table (rails up). Push an M3x12 bolt into each rail hole <b>from outside</b> (from the face of the rail that faces the wall); on its end screw the <b>{0}-layer block with its embedded nut</b> (layer {1} Ø{2} · layers {3}–{4} Ø{5} nut pocket · layer {6} Ø{7}) — a drop of CA glue on the nut's outer face (CA on the nut's OUTER face — not on its thread), the same as the foot block in {8}. The block is now <b>self-centred</b> on the bolt: put CA glue on the contact face and press it against the inner face of the rail. Once cured, take the bolt out. You do not have to match two independent measurements; since a nut cannot be held inside with the lid closed, this block is a must (B54).
tr: Kapağı yapıştırma.
en: Do not glue the lid.
tr: Kapak oturuyor, raylar yan duvarlara sürtmeden giriyor.
en: The lid sits down, the rails go in without rubbing on the side walls.
tr: <span class='ano'>{0}</span> <b>Kapağı dene — sonra ÇIKAR</b>
en: <span class='ano'>{0}</span> <b>Try the lid — then TAKE IT OFF</b>
tr: Bloklar kuruyunca dört <b>M3x12</b> cıvatayı pul ile sık: bir kez tam sık, tak-çıkarı dene. Tahtada diş yok, içeriye el girmez. (Delikler {0}'de açıldı.)
en: Once the blocks have cured, tighten the four <b>M3x12</b> bolts with washers: tighten fully once, try taking it on and off. No thread in the wood, no hand needs to go inside. (The holes were made in {0}.)
tr: <b>Sonra cıvataları sök ve kapağı KALDIR — kapak Adım {0}'e kadar açık kalır.</b> Son toplama ({1}) kutunun içinde kablo bağı atıyor: kapak takılıyken yapılamaz.
en: <b>Then take the bolts out and LIFT the lid off — the lid stays off until Step {0}.</b> The final tidy-up ({1}) puts cable ties inside the enclosure: that cannot be done with the lid on.
tr: Kapak bu adımda <b>bitmiş ve denenmiş</b> oluyor; kutunun üstünde durmuyor. Kapatma Adım {0}'te.
en: In this step the lid gets <b>finished and tried</b>; it does not stay on the enclosure. Closing is in Step {0}.
tr: Cıvatalar takılıyken kapak elle çekince kalkmıyor.
en: With the bolts in, the lid does not come off when pulled by hand.
tr: Cıvatalar söküldü, <b>kapak kutunun üstünden alındı</b> — kutu yine açık.
en: The bolts are out, <b>the lid is off the enclosure</b> — the enclosure is open again.
tr: Dört delik de rayın somun bloğuna denk geliyor (cıvata boşta dönmüyor).
en: All four holes land on the rail's nut block (the bolt does not spin freely).
tr: <span class='ano'>{0}</span> <b>Etiketle ve topla</b>
en: <span class='ano'>{0}</span> <b>Label and tidy up</b>
tr: <b>Panelin bütün etiketlerini yaz/yapıştır</b> — eksiksiz liste: <b>Ön panel:</b> <b>YÜK {0}</b> <span class='kucuk'>(yükün −)</span> · <b>YÜK {1}</b> <span class='kucuk'>(kaynağın −)</span> · <b>PİL {2}</b> <span class='kucuk'>(direnç ← pil +)</span> · <b>PİL {3}</b> <span class='kucuk'>(pil −)</span> · <b>V</b> · <b>COM</b> <span class='kucuk'>(= YÜK {4} = PİL {5})</span> · <b>SKOP</b> · <b>AÇ / KAPA</b> <span class='kucuk'>(PİL)</span> · <b>CAL</b> <span class='kucuk'>(→ SKOP'a kısa kablo)</span> · <b>GÜÇ</b> <span class='kucuk'>(±{6} V var)</span> · <b>HV ⚡</b>
en: <b>Write/stick on all the panel labels</b> — complete list: <b>Front panel:</b> <b>«YÜK» {0}</b> <span class='kucuk'>(load −)</span> · <b>«YÜK» {1}</b> <span class='kucuk'>(source −)</span> · <b>«PİL» {2}</b> <span class='kucuk'>(resistor ← battery +)</span> · <b>«PİL» {3}</b> <span class='kucuk'>(battery −)</span> · <b>V</b> · <b>COM</b> <span class='kucuk'>(= «YÜK» {4} = «PİL» {5})</span> · <b>«SKOP»</b> · <b>«AÇ / KAPA»</b> <span class='kucuk'>(«PİL»)</span> · <b>CAL</b> <span class='kucuk'>(→ short lead to «SKOP»)</span> · <b>«GÜÇ»</b> <span class='kucuk'>(±{6} V present)</span> · <b>HV ⚡</b>
tr: <b>Arka panel:</b> <b>ŞARJ</b> <span class='kucuk'>(PİL kapalıyken)</span> · <b>USB</b> <span class='kucuk'>(⚡ HV ölçerken çıkar)</span>
en: <b>Back panel:</b> <b>«ŞARJ»</b> <span class='kucuk'>(with «PİL» off)</span> · <b>USB</b> <span class='kucuk'>(⚡ unplug when measuring HV)</span>
tr: Arka panele ŞARJ yuvasının yanına şarj kuralı etiketi ({0}). USB yuvasının yanına: ⚠ HV varken USB'yi çıkar.
en: On the back panel, next to the «ŞARJ» slot, the charging rule label ({0}). Next to the USB slot: ⚠ unplug the USB when HV is present.
tr: Kabloları kablo bağıyla topla; HV kablosu tek başına ve diğerlerinden ≥ {0} mm.
en: Tidy the cables with cable ties; the HV cable on its own and ≥ {0} mm from the others.
tr: <b>Kutu prensibi:</b> değerli parçalar (kartlar, ESP32, şönt, Q1) yapıştırılmaz; {0} yuvaları, modüller (MT1, MT2, B0505S), {1} µF, KL ve sigorta şeritleri sıcak silikonla tutuyor. Başka kaba geçerken vidaları ve kablo bağlarını sök, konnektörleri ayır; silikonlu parçaları izopropil alkol damlatıp plastik kartla kaldır.
en: <b>Enclosure principle:</b> valuable parts (boards, ESP32, shunt, Q1) are not glued; the {0} holders, modules (MT1, MT2, B0505S), {1} µF, KL and the fuse strips are held with hot glue. When moving to another enclosure, take out the screws and cable ties, unplug the connectors; lift the hot-glued parts by dripping isopropyl alcohol and using a plastic card.
tr: Kutuyu salla: içeride oynayan bir şey yok.
en: Shake the enclosure: nothing moves inside.
tr: Kapak henüz açık: içeride unutulan alet, tel kırpıntısı, vida yok.
en: The lid is still off: no tools, wire offcuts or screws left inside.
tr: <span class='ano'>{0}</span> <b>Kapağı tak ve cıvatala</b>
en: <span class='ano'>{0}</span> <b>Fit the lid and bolt it down</b>
tr: Kapağı ({0}'de yapıldı) yerine koy; {1}'de açılan dört delikten <b>M3x12</b> cıvatayı pulla dıştan tak, raydaki gömme somuna sık.
en: Put the lid (made in {0}) in place; through the four holes made in {1}, fit the <b>M3x12</b> bolts with washers from outside and tighten them into the embedded nuts in the rail.
tr: <b>Kutu burada kapanıyor:</b> bundan sonra kutunun içine giren iş yok. İçeride bir şey değiştirmek gerekirse dört cıvata sökülür, kapak kalkar — kartlar ve pil bloğu vida/kablo bağıyla tutulduğu için hiçbir şey kırılmaz.
en: <b>The enclosure closes here:</b> from now on there is no work inside the enclosure. If something inside needs changing, the four bolts come out and the lid lifts off — nothing breaks, since the boards and the battery block are held with screws/cable ties.
tr: Hücreler yerinde mi, son kez bak ({0}'te takılmıştı): yuvalar kapak altında kalıyor, hücre değiştirmek için kapağı açman gerekir. Şarj için gerekmez — ŞARJ yuvası dışarıda.
en: Check one last time that the cells are in place (they were inserted in {0}): the holders are under the lid, to change a cell you have to open the lid. Not needed for charging — the «ŞARJ» slot is outside.
tr: Kapak dört cıvatayla sıkı; elle çekince kalkmıyor.
en: The lid is tight with four bolts; it does not come off when pulled by hand.
tr: Kapak ile en yüksek parça ({0} yuvası / Q1 soğutucusu) arasında boşluk var, kapak hiçbir şeye bastırmıyor.
en: There is a gap between the lid and the tallest part ({0} holder / Q1 heatsink), the lid presses on nothing.
tr: <span class='ano'>{0}</span> <b>Kapalı kutuda uçtan uca</b>
en: <span class='ano'>{0}</span> <b>End to end in the closed enclosure</b>
tr: Kapak kapalı, her şey panelden. Kutu <b>kendi pilinden</b>: PİL AÇ, USB takılı DEĞİL — okumaları WiFi panelinden al. Test kaynağı <b>tezgah beslemesi</b> (buck {0} V, {1} kuralı) → {2} Ω / {3} W → <b>YÜK {4} – YÜK {5}</b>; V jakını buck'ın artısına bağla. Kartın V ve I okuması multimetreyle <b>±%{6} / ±%{7}</b> içinde olmalı.
en: Lid closed, everything from the panel. The enclosure runs <b>from its own battery</b>: «PİL» ON, USB NOT plugged in — take the readings from the WiFi panel. Test source a <b>bench supply</b> (buck {0} V, rule {1}) → {2} Ω / {3} W → <b>«YÜK» {4} – «YÜK» {5}</b>; connect the V jack to the buck's positive. The board's V and I readings must be within <b>±{6}% / ±{7}%</b> of the multimeter.
tr: CAL → SKOP kısa kabloyla: panelde kare dalga görünüyor.
en: With the short CAL → «SKOP» lead: a square wave shows on the panel.
tr: {0} dk sonra kutunun hiçbir yüzü elde ısı hissettirmiyor.
en: After {0} min no face of the enclosure feels warm to the hand.
tr: <b>Pil kapasite testini gerçek bir pille sınamak istersen</b> (isteğe bağlı): kutudaki iki {0} paketin parçası, onları çıkarma — üçüncü bir hücre al.
en: <b>If you want to try the battery capacity test with a real battery</b> (optional): the two {0} cells in the enclosure are part of the pack, do not take them out — get a third cell.
tr: V okuması multimetreyle ±%{0} içinde.
en: V reading within ±{0}% of the multimeter.
tr: I okuması multimetreyle ±%{0} içinde.
en: I reading within ±{0}% of the multimeter.
tr: SKOP'ta CAL'in kare dalgası görünüyor.
en: CAL's square wave shows on «SKOP».
tr: Bitince: neyi nereden ölçerim
en: When it is done: what do I measure from where
tr: Ölçüm
en: Measurement
tr: Hangi uç
en: Which terminal
tr: Nasıl bağlanır
en: How to connect
tr: Çözünürlük
en: Resolution
tr: <b>V (kırmızı) + COM (siyah)</b>
en: <b>V (red) + COM (black)</b>
tr: Krokodil kabloyla devreye <b>paralel</b>. Menzil: <code>n</code>.
en: With crocodile-clip leads, in <b>parallel</b> with the circuit. Range: <code>n</code>.
tr: <span class='kucuk'>{0} mV adım</span>
en: <span class='kucuk'>{0} mV step</span>
tr: <b>HV (SARI) + COM (siyah)</b>
en: <b>HV (YELLOW) + COM (black)</b>
tr: Menzil: <code>y</code>. <b>Tek el kuralı.</b> USB'yi PC'ye TAKMA — WiFi paneli kullan (COM = kart GND = USB toprağı). Ölçülen devre toprağa bağlıysa (şebekeli kaynak, PC'li devre) HV'yi KULLANMA: bu kart yüzen (pil / DC-DC) devreler için.
en: Range: <code>y</code>. <b>One-hand rule.</b> DO NOT plug the USB into the PC — use the WiFi panel (COM = board GND = USB ground). If the circuit being measured is earthed (mains-powered supply, a circuit with a PC), DO NOT USE HV: this board is for floating (battery / DC-DC) circuits.
tr: <b>Akım, ≤ {0} A sürekli</b>
en: <b>Current, ≤ {0} A continuous</b>
tr: <b>YÜK {0} – YÜK {1}</b>
en: <b>«YÜK» {0} – «YÜK» {1}</b>
tr: Akım <b>eksi hattan</b> ölçülür: kaynağın + ucu yükün + ucuna <b>doğrudan</b> gider, kutuya girmez. Eksi hattı kes: yükün eksisi <b>YÜK {0}</b>, kaynağın eksisi <b>YÜK {1}</b>. Aynı anda gerilim için yalnız <b>V jakını</b> devrenin artısına bağla; <b>COM'a krokodil TAKMA</b> — COM zaten YÜK {2}'dir. COM'u devrenin eksisine (YÜK {3} tarafı) takarsan şönt baypas olur: okuma düşer, ince kablo ısınır. Sınır {4} mΩ şöntün <b>ısınması</b> (Ø{5} mm manganin, üretici {6} A; sürekli {7} A) ve şöntü tutan <b>XP128 klemensi ({8} A)</b>: kısa süreli de olsa {9} A'i GEÇME. mA hassasiyeti gerekirse {10} mΩ (R044) tak, <code>s0.015</code> + <code>Z</code>: {11} A sürekli, adım {12} mA.
en: Current is measured <b>on the negative line</b>: the source's + goes <b>directly</b> to the load's +, it does not enter the enclosure. Break the negative line: the load's negative to <b>«YÜK» {0}</b>, the source's negative to <b>«YÜK» {1}</b>. For voltage at the same time, connect only the <b>V jack</b> to the circuit's positive; <b>DO NOT clip anything to COM</b> — COM already is «YÜK» {2}. If you clip COM to the circuit's negative («YÜK» {3} side) the shunt is bypassed: the reading drops and the thin lead heats up. The limit is the <b>heating</b> of the {4} mΩ shunt (Ø{5} mm manganin, manufacturer {6} A; continuous {7} A) and the <b>XP128 terminal block ({8} A)</b> holding the shunt: DO NOT EXCEED {9} A, not even briefly. If you need mA resolution, fit the {10} mΩ (R044), <code>s0.015</code> + <code>Z</code>: {11} A continuous, {12} mA step.
tr: <span class='kucuk'>{0} mA adım</span>
en: <span class='kucuk'>{0} mA step</span>
tr: <b>Güç ve enerji (W, Wh)</b>
en: <b>Power and energy (W, Wh)</b>
tr: <b>V + COM ve YÜK birlikte</b>
en: <b>V + COM and «YÜK» together</b>
tr: Gerilim ve akım aynı anda bağlıysa kart gücü kendi hesaplar; reaktif yükte de doğru.
en: With voltage and current connected at the same time, the board calculates the power itself; correct for reactive loads too.
tr: <span class='kucuk'>işaretli, gerçek güç</span>
en: <span class='kucuk'>signed, real power</span>
tr: <b>SKOP (kırmızı) + COM</b>
en: <b>«SKOP» (red) + COM</b>
tr: Dalga şeklini görmek için. Zaman tabanı {0} µs – {1} ms/bölme. Asimetrik menzil: eksi tarafı daha geniş.
en: To see the waveform. Time base {0} µs – {1} ms/div. Asymmetric range: the negative side is wider.
tr: <span class='kucuk'>{0} kSa/s'e kadar</span>
en: <span class='kucuk'>up to {0} kSa/s</span>
tr: <b>Güç — kutunun kendi pili</b>
en: <b>Power — the enclosure's own battery</b>
tr: <b>PİL AÇ (tek anahtar)</b>
en: <b>«PİL» ON (single switch)</b>
tr: Kutu yalnız kendi pilinden çalışır (B58: dış besleme yok). İki {0} paralel: süre ≈ {1} saat (ESP32 WiFi'de, analog açık). USB'siz kullanımda kutu tamamen yüzer: HV ölçümü için en güvenli hal. <b>Şarj:</b> PİL KAPALI, ŞARJ yuvasına tek Type-C — iki hücre birlikte dolar (≈ {2} saat). Şarj ederken ölçüm yapma: şarj kablosu COM'u şarj cihazının toprağına bağlar. <b>USB'yi PC'ye takarken PİL AÇIK olsun</b>: yükü pil taşır; kapalıyken ölçüm tarafı da PC'den beslenmeye çalışır (~{3} A).
en: The enclosure runs only from its own battery (B58: no external supply). Two {0} in parallel: runtime ≈ {1} hours (ESP32 on WiFi, analog on). Used without USB the enclosure floats completely: the safest state for HV measurements. <b>Charging:</b> «PİL» OFF, a single Type-C into the «ŞARJ» slot — both cells charge together (≈ {2} hours). Do not measure while charging: the charging cable ties COM to the charger's ground. <b>Have «PİL» ON when plugging the USB into the PC</b>: the battery carries the load; when it is off, the measurement side also tries to run from the PC (~{3} A).
tr: <span class='kucuk'>{0} × {1} paralel</span>
en: <span class='kucuk'>{0} × {1} in parallel</span>
tr: <b>Pil kapasitesi (mAh)</b>
en: <b>Battery capacity (mAh)</b>
tr: <b>PİL {0} – PİL {1} + yük direnci + V jakı</b>
en: <b>«PİL» {0} – «PİL» {1} + load resistor + V jack</b>
tr: <b>Zorunlu:</b> V jakı → pil + (COM zaten pil −, ayrıca tel takma). Pil + → yük direnci → <b>PİL {0}</b>; pil − → <b>PİL {1}</b>. Pilin + ucu hiçbir PİL jakına <b>doğrudan</b> takılmaz: iki tel çıkar, biri dirence, biri V'ye. <b>YÜK boş kalsın.</b> Pil ≤ {2} V ise <code>n</code>, üstü <code>y</code>. Direnç seçimi: akım = pil V ÷ R, sınır {3} A — {4} V {5} için {6} Ω {7} W ({8} A, dirençte {9} W). <code>P&lt;kesme&gt;</code>, <code>p1</code>. <b>⚠ Kutupları KARIŞTIRMA:</b> ters bağlarsan akım Q1'in gövde diyodundan akar ve kart bunu <b>KESEMEZ</b> (MOSFET kapalıyken bile; {10} Ω ile ~{11} A sürekli). Kart 'ters bağlı / baypas' hatası verirse testi başlatmaz ama akım durmaz — <b>kabloyu hemen çıkar</b>.
en: <b>Required:</b> V jack → battery + (COM already is battery −, no extra wire). Battery + → load resistor → <b>«PİL» {0}</b>; battery − → <b>«PİL» {1}</b>. The battery's + is never plugged <b>directly</b> into a «PİL» jack: two wires come off it, one to the resistor, one to V. <b>Leave «YÜK» empty.</b> Battery ≤ {2} V: <code>n</code>, above that <code>y</code>. Choosing the resistor: current = battery V ÷ R, limit {3} A — for a {4} V {5}, {6} Ω {7} W ({8} A, {9} W in the resistor). <code>P&lt;cutoff&gt;</code>, <code>p1</code>. <b>⚠ DO NOT MIX UP the polarity:</b> connected backwards, the current flows through Q1's body diode and the board <b>CANNOT STOP</b> it (even with the MOSFET off; ~{11} A continuous with {10} Ω). If the board reports a 'reversed / bypass' error it does not start the test, but the current does not stop — <b>unplug the lead at once</b>.
tr: <span class='kucuk'>≤ {0} V pil</span>
en: <span class='kucuk'>≤ {0} V battery</span>
tr: <b>Kutu açılmıyorsa</b>
en: <b>If the enclosure does not power up</b>
tr: <b>PİL anahtarı</b>
en: <b>«PİL» switch</b>
tr: PİL açınca kutu açılmıyorsa (ESP32 hiç açılmıyor ya da bir an yanıp sönüyor, GÜÇ lambası yanmıyor): pil azalmış — PİL'i kapat, pili <b>doldur</b> (ŞARJ, PİL kapalı), sonra yeniden aç. Açılışta kart {0} µF'sini doldururken paketten kısa bir süre {1}–{2} A çekiliyor; boşalmış pil bunu taşıyamaz. Dolu pilde de oluyorsa {3}'teki yordam ({4} × {5} Ω seri direnç).
en: If the enclosure does not power up when «PİL» is switched on (the ESP32 does not start at all or flashes once, the «GÜÇ» lamp does not light): the battery is low — switch «PİL» off, <b>charge</b> the battery («ŞARJ», «PİL» off), then switch it on again. At power-up, while the board charges its {0} µF, {1}–{2} A is drawn from the pack for a moment; a flat battery cannot deliver that. If it also happens with a full battery, the procedure in {3} ({4} × {5} Ω series resistor).
tr: <span class='kucuk'>dolu pilde açılır</span>
en: <span class='kucuk'>starts with a full battery</span>
tr: <b>Şarj (ısıl kural)</b>
en: <b>Charging (thermal rule)</b>
tr: <b>Kapak kapalı, PİL KAPALI</b>
en: <b>Lid closed, «PİL» OFF</b>
tr: {0}'nin <b>şarj tavanı {1} °C</b> (deşarjda {2} °C). Kutu kapalı ve havalandırmanın ısıl katkısı %{3} mertebesinde, yani içeride ne ısınırsa hücreye biner. İki kural: <b>({4}) şarj ederken ölçüm yapma</b> — kart ve ESP32 kapalıyken kutuya giren güç yarıya iniyor; <b>({5}) şarj modülünün kendisi ısınır</b> (TP4056 {6} A'de ~{7}–{8} W, arka duvarın dibinde). Sıcak bir odada (>{9} °C) kapağı açık şarj et. ⚠ Bu bir HESAP değil kural: kutu içi sıcaklık artışı ölçülmedi. İlk şarjda içeriye bir termometre koy, {10} saat sonra hücre gövdesine el sür. <b>Karar eşiği:</b> hücre gövdesi elinde <b>ılıktan sıcağa</b> geçiyorsa (yaklaşık {11} °C üstü, {12} °C tavanına yakın) kapağı açık şarj etmeye geç (ya da şarj akımını yarıya indir: Rprog {13} kΩ → {14} kΩ, {15} A); el sıcaklığında kalıyorsa kapalı şarj güvenli, bir daha ölçmeye gerek yok.
en: The {0}'s <b>charging ceiling is {1} °C</b> ({2} °C when discharging). The enclosure is closed and the thermal contribution of the ventilation is of the order of {3}%, so whatever heats up inside ends up on the cell. Two rules: <b>({4}) do not measure while charging</b> — with the board and the ESP32 off, the power going into the enclosure halves; <b>({5}) the charging module itself heats up</b> (TP4056 at {6} A ~{7}–{8} W, at the bottom of the back wall). In a hot room (>{9} °C) charge with the lid open. ⚠ This is a rule, not a CALCULATION: the temperature rise inside the enclosure has not been measured. On the first charge put a thermometer inside, touch the cell body after {10} hours. <b>Decision threshold:</b> if the cell body goes from <b>warm to hot</b> under your hand (roughly above {11} °C, close to the {12} °C ceiling), switch to charging with the lid open (or halve the charging current: Rprog {13} kΩ → {14} kΩ, {15} A); if it stays at hand temperature, charging closed is safe and there is no need to measure again.
tr: <span class='kucuk'>tavan {0} °C</span>
en: <span class='kucuk'>ceiling {0} °C</span>
tr: Akım ve gerilim ölçümü — bağlantı
en: Current and voltage measurement — connection
tr: YÜK jakları devreye SERİ girer; COM içeride YÜK {0}'dir
en: The «YÜK» jacks go in SERIES with the circuit; inside, COM is «YÜK» {0}
tr: Akım ve gerilim ölçümü
en: Current and voltage measurement
tr: pil / güç kaynağı
en: battery / power supply
tr: ÖLÇÜLEN DEVRE
en: CIRCUIT UNDER TEST
tr: motor, kart, lamba…
en: motor, board, lamp…
tr: ÖLÇÜM KUTUSU
en: MEASUREMENT BOX
tr: içeride: {0} mΩ şönt · COM = YÜK {1}
en: inside: {0} mΩ shunt · COM = «YÜK» {1}
tr: + hattı: kaynağın + → yükün + (kutuya girmez)
en: + line: source + → load + (does not enter the enclosure)
tr: yükün −
en: load −
tr: kaynağın −
en: source −
tr: yükün +
en: load +
tr: BOŞ — içeride YÜK {0}
en: EMPTY — inside it is «YÜK» {0}
tr: Akım YÜK {0} → şönt → YÜK {1} yolundan geçer (eksi hat).
en: The current takes the path «YÜK» {0} → shunt → «YÜK» {1} (negative line).
tr: COM'a krokodil takma: yükün eksisine takarsan şönt baypas olur.
en: Do not clip anything to COM: if you clip it to the load's negative, the shunt is bypassed.
tr: Pil kapasite testi — bağlantı
en: Battery capacity test — connection
tr: PİL jakları deşarj yolu; V jakı zorunlu
en: The «PİL» jacks are the discharge path; the V jack is required
tr: Pil kapasite testi
en: Battery capacity test
tr: PİL
en: «PİL»
tr: YÜK DİRENCİ
en: LOAD RESISTOR
tr: örn. {0} Ω {1} W taş direnç
en: e.g. {0} Ω {1} W ceramic resistor
tr: içeride: Q1 anahtarı + şönt · COM = PİL {0}
en: inside: Q1 switch + shunt · COM = «PİL» {0}
tr: pil +
en: battery +
tr: direnç ← pil +
en: resistor ← battery +
tr: pil −
en: battery −
tr: pilin + — ZORUNLU
en: battery + — REQUIRED
tr: BOŞ — içeride PİL {0}
en: EMPTY — inside it is «PİL» {0}
tr: Pilin + ucu jaka DEĞİL: direnç üstünden PİL {0}'e, ayrıca V'ye.
en: The battery's + does NOT go to a jack: through the resistor to «PİL» {0}, and separately to V.
tr: Kart Q1 ile yükü açıp kapatır, kesme geriliminde keser. YÜK boş kalır.
en: The board switches the load on and off with Q1 and cuts it off at the cut-off voltage. «YÜK» stays empty.
tr: Ağırlık merkezi — kutu dengeli mi
en: Centre of mass — is the enclosure balanced
tr: <b>Sonuç: kutu dengeli.</b> Ağırlık merkezi geometrik merkezden yanlara <b>+{0} mm</b>, öne-arkaya <b>-{1} mm</b> kaçıyor (kutu {2} × {3} mm). Bir taraf ağır değil: iki taban rayı yükün <b>%{4} / %{5}</b>'ünü taşıyor.
en: <b>Result: the enclosure is balanced.</b> The centre of mass is off the geometric centre by <b>+{0} mm</b> sideways and <b>-{1} mm</b> front-to-back (enclosure {2} × {3} mm). No side is heavy: the two base rails carry <b>{4}% / {5}%</b> of the load.
tr: Devrilmeye pay bol: kutu her yönde <b>{0}°</b> eğilene kadar devrilmiyor (kütle tahminlerinin en kötü halinde bile {1}°). Ağırlık merkezi tabandan <b>{2} mm</b>, yani dış yüksekliğin yüzde {3}'ünde — alçak.
en: Plenty of margin against tipping: the enclosure does not tip over until it is tilted <b>{0}°</b> in any direction (even in the worst case of the mass estimates, {1}°). The centre of mass is <b>{2} mm</b> above the base, i.e. at {3} percent of the outer height — low.
tr: Denge kendiliğinden değil, iki şeyden geliyor: kutunun kendi tahtası toplamın <b>%{0}</b>'si ve simetrik; ağır parçalar da zıt yanlarda (ana kart solda, Q1 soğutucusu ve {1}'ler sağda).
en: The balance does not come by chance, but from two things: the enclosure's own wood is <b>{0}%</b> of the total and symmetric; and the heavy parts are on opposite sides (the main board on the left, the Q1 heatsink and the {1}s on the right).
tr: <b>Hiçbiri tartılmadı</b> — sayılar hacim × yoğunluk ya da benzerinden kestirme. Bu yüzden denetim her sonucu bir de kütlelerin <i>en kötü</i> halinde hesaplıyor: her kalemi ağırlık merkezini en çok kaydıracak yönde sınırına itip tekrar bakıyor. Bir kalemi tartarsan söyle, <code>kutu_veri.KUTLE</code>'yi günceller, sayıları yeniden üretirim.
en: <b>Nothing was weighed</b> — the numbers are estimates from volume × density or similar parts. That is why the audit also calculates every result for the <i>worst case</i> of the masses: it pushes each item to its limit in the direction that shifts the centre of mass the most and checks again. If you weigh an item, tell me: I update <code>kutu_veri.KUTLE</code> and regenerate the numbers.
tr: Ölçüt neydi: her ray yükün en az %{0}'ini taşısın (kötü halde %{1}), ağırlık merkezi derinlikte orta bölgede kalsın, devrilme açısı her yönde ≥ {2}°, ağırlık merkezi kutunun yarı yüksekliğinin altında.
en: What the criteria were: each rail carries at least {0}% of the load ({1}% in the worst case), the centre of mass stays in the middle zone in depth, the tipping angle is ≥ {2}° in every direction, the centre of mass is below half the enclosure's height.
tr: Destek açıklığı ve ağırlık merkezi
en: Support span and centre of mass
tr: Ağırlık merkezi
en: Centre of mass
tr: kablo demeti {0} g
en: cable bundle {0} g
tr: Kuşbakışı — ağırlık merkezi, iki hücre ({0} g)
en: Top view — centre of mass, two cells ({0} g)
tr: sarı = kutunun üzerinde durduğu iki taban rayı (destek açıklığı) · kesikli daire = geometrik merkez · kırmızı = ağırlık merkezi
en: yellow = the two base rails the enclosure stands on (support span) · dashed circle = geometric centre · red = centre of mass
tr: üst kenar = ARKA duvar (pil bloğu) · alt kenar = ÖN panel (jaklar)
en: top edge = BACK wall (battery block) · bottom edge = FRONT panel (jacks)
tr: Yapılandırmaya göre
en: By configuration
tr: Yapılandırma
en: Configuration
tr: AM x (yan)
en: CoM x (side)
tr: AM y (derinlik)
en: CoM y (depth)
tr: Ray yük payı sol/sağ
en: Rail load share left/right
tr: En küçük devrilme açısı
en: Smallest tipping angle
tr: Kötü halde
en: Worst case
tr: <b>İki hücre (normal)</b>
en: <b>Two cells (normal)</b>
tr: <b>Tek hücre (paket tek hücreyle de çalışır)</b>
en: <b>One cell (the pack also works with a single cell)</b>
tr: <b>Hücresiz (taşıma / saklama)</b>
en: <b>No cells (transport / storage)</b>
tr: AM x/y = ağırlık merkezinin geometrik merkezden sapması; + değer sağa ve öne. Pil bloğu yoksa ön panelin jakları dengelenmiyor, ağırlık merkezi +{0} mm öne kayıyor — devrilme açısı yine {1}°, sorun değil.
en: CoM x/y = offset of the centre of mass from the geometric centre; + is to the right and to the front. Without the battery block the front panel's jacks are not balanced, the centre of mass moves +{0} mm forward — the tipping angle is still {1}°, not a problem.
tr: Kütle nereye dağılıyor
en: Where the mass goes
tr: Kütle
en: Mass
tr: kutunun tahtası
en: the enclosure's wood
tr: pil bloğu (hücreler dahil)
en: battery block (cells included)
tr: kartlar ve güç parçaları
en: boards and power parts
tr: panel öğeleri
en: panel items
tr: kapak
en: lid
tr: Kullanılan kütleler
en: Masses used
tr: ± belirsizlik
en: ± uncertainty
tr: tahmin: {0}×{1} delikli plaket ({2} mm ≈ {3} g) + ~{4} parça, soket, klemens
en: estimate: {0}×{1} perfboard ({2} mm ≈ {3} g) + ~{4} parts, sockets, terminal blocks
tr: katalog: ESP32-S3 DevKitC-{0} ≈ {1} g
en: catalogue: ESP32-S3 DevKitC-{0} ≈ {1} g
tr: tahmin: {0}×{1} plaket (≈ {2} g) + HV bölücü zinciri
en: estimate: {0}×{1} perfboard (≈ {2} g) + HV divider chain
tr: tahmin: manganin U şönt + XP128 klemens
en: estimate: manganin U shunt + XP128 terminal block
tr: tahmin: IRFZ44N {0} g + TO-{1} soğutucu ({2}×{3}×{4} alüminyum)
en: estimate: IRFZ44N {0} g + TO-{1} heatsink ({2}×{3}×{4} aluminium)
tr: tahmin: {0} tekli plastik yuva, yaylı
en: estimate: {0} single plastic holder, with spring
tr: tahmin: TP4056 Type-C modülü
en: estimate: TP4056 Type-C module
tr: tahmin: MT3608 yükseltici modülü
en: estimate: MT3608 boost converter module
tr: tahmin: 5x20 PCB klipsli sigorta yuvası + cam sigorta
en: estimate: 5x20 PCB-clip fuse holder + glass fuse
tr: tahmin: B0505S-2WR3 SIP (~{0} g) + dört kısa kablo ve makaron
en: estimate: B0505S-2WR3 SIP (~{0} g) + four short wires and heat-shrink
tr: tahmin: {0} µF {1} V radyal elektrolitik (~{2} g) + bacaklar
en: estimate: {0} µF {1} V radial electrolytic (~{2} g) + legs
tr: tahmin: {0}'li {1} mm vidalı klemens + kablo uçları
en: estimate: {0}-way {1} mm screw terminal block + wire ends
tr: <b>HÜCRE</b>
en: <b>CELL</b>
tr: katalog: {0} {1} mAh ≈ {2} g (yuvaya takılınca eklenir)
en: catalogue: {0} {1} mAh ≈ {2} g (added when inserted into the holder)
tr: <b>jak_büyük</b>
en: <b>large jack</b>
tr: tahmin: {0} mm born jak büyük boy, pirinç gövde + somun
en: estimate: {0} mm banana jack, large, brass body + nut
tr: <b>jak_küçük</b>
en: <b>small jack</b>
tr: tahmin: {0} mm vidalı banana soket
en: estimate: {0} mm screw banana jack
tr: <b>anahtar</b>
en: <b>switch</b>
tr: tahmin: KTS102 toggle + somun
en: estimate: KTS102 toggle + nut
tr: tahmin: 5x20 PCB klipsli sigorta yuvası + cam sigorta (B58e: kutu içi)
en: estimate: 5x20 PCB-clip fuse holder + glass fuse (B58e: inside the enclosure)
tr: tahmin: {0} mm LED + seri direnç + makaron + kısa tel
en: estimate: {0} mm LED + series resistor + heat-shrink + short wire
tr: tahmin: kutu içi kablo demeti + kablo bağları + makaron
en: estimate: cable bundle inside the enclosure + cable ties + heat-shrink
tr: Çubuk yoğunluğu {0} g/cm³ varsayıldı → bir çubuk {1} g. <b>{2} çubuğu tartıp söyle</b> (÷{3}): kutunun tahtası toplamın en büyük parçası, en çok bu sayı önemli.
en: Stick density assumed {0} g/cm³ → one stick {1} g. <b>Weigh {2} sticks and tell me</b> (÷{3}): the enclosure's wood is the largest part of the total, this number matters most.
tr: Kutu arayüzü — 3D baskı / başka kap için
en: Enclosure interface — for 3D printing / another enclosure
tr: İleride 3D baskı ya da başka bir kaba geçersen ihtiyacın olan her sayı burada; aynı veri JSON olarak da gömülü (<code>&lt;script id='kutu-arayuz'&gt;</code>). Panel x'leri iç sol köşeden, önden bakınca — arka panel için de aynı eksen.
en: If you later move to 3D printing or another enclosure, every number you need is here; the same data is also embedded as JSON (<code>&lt;script id='kutu-arayuz'&gt;</code>). Panel x values from the inside left corner, seen from the front — the same axis for the back panel too.
tr: İç ölçü
en: Inside dimensions
tr: Köşe direği
en: Corner post
tr: HV kaçak yolu
en: HV creepage distance
tr: Kapak cıvatası
en: Lid bolt
tr: M3x12, yan duvar, y {0}/{1}, z {2}
en: M3x12, side wall, y {0}/{1}, z {2}
tr: İç parçalar (sol-arka köşe, mm)
en: Internal parts (back-left corner, mm)
tr: Panel delikleri (mm)
en: Panel holes (mm)
tr: İçeri uzantı
en: Reach inside
tr: Yalıtkan kaplama (tırnak cilası / konformal lak)
en: Insulating coating (nail varnish / conformal coating)
tr: <b>B</b> — Kart B'nin İKİ YÜZÜ de — zincirin tamamı bu kartta
en: <b>B</b> — BOTH FACES of board B — the whole divider chain is on this board
tr: {0}'ten ÖNCE (kart kutuya girmeden, elde kolay)
en: BEFORE {0} (before the board goes into the enclosure, easy to handle)
tr: {0} × 820K seri zincir {1} → {2} V basamaklarıyla bu kartta; komşu pedler arası kaçak hem emniyet hem ORAN hatası. Lehim yüzü öncelikli: kaçak yolu orada. Kartın süreklilik/direnç ölçümleri geçmiş olmalı; kaplanmış pede prob değmez.
en: The {0} × 820K series chain with its {1} → {2} V steps is on this board; leakage between neighbouring pads is both a safety issue and a RATIO error. The solder side comes first: that is where the leakage path is. The board's continuity/resistance checks must have passed; a probe does not contact a coated pad.
tr: <b>B</b> — T_HV ve T_N6 tellerinin lehim noktaları + telin ilk {0} mm'si
en: <b>B</b> — the solder points of the T_HV and T_N6 wires + the first {0} mm of the wire
tr: teller LEHİMLENDİKTEN sonra (kartı takmadan önce pigtail olarak lehimle)
en: AFTER the wires are SOLDERED (solder them as pigtails before fitting the board)
tr: Zincirin en yüksek ({0} V) ve en düşük ucu. Lehim tepeciği kaplanmazsa kaçak yolunun en dar yeri açıkta kalır. Önce lehimle, sonra kapla — tersi olursa cilayı kazımak gerekir.
en: The highest ({0} V) and lowest end of the chain. If the solder blob is not coated, the narrowest point of the leakage path is left exposed. Solder first, then coat — the other way round you have to scrape the varnish off.
tr: Kaplanmayacak yerler
en: Areas not to coat
tr: Nereye DEĞİL
en: Where NOT
tr: En yüksek düğümü {0} V (skop girişi) ve en yüksek empedansı {1} kΩ: {2} MΩ'luk yüzey kaçağı %{3} hata verir, bütçede kaybolur. Gerekmiyor.
en: Its highest node is {0} V (scope input) and its highest impedance {1} kΩ: {2} MΩ of surface leakage gives a {3}% error, lost in the budget. Not needed.
tr: <b>Q1 soğutucusu ve regülatörlerin çevresi</b>
en: <b>Around the Q1 heatsink and the regulators</b>
tr: Nitroselüloz ısıda sararıp çatlar, üstelik ısı yolunu da bozar. Zaten orada yüksek gerilim yok: Q1 pil testinde ≤ {0} V, regülatörler ±{1} V.
en: Nitrocellulose yellows and cracks with heat, and it also spoils the heat path. There is no high voltage there anyway: Q1 ≤ {0} V in the battery test, the regulators ±{1} V.
tr: <b>Panel jaklarının lehim kulakları (CAL, PİL, YÜK, HV)</b>
en: <b>Solder lugs of the panel jacks (CAL, «PİL», «YÜK», HV)</b>
tr: Tel oynayınca cila çatlar. Orada makaron ya da izole bant doğru çözüm — Kulaklar arası artık geniş (B56/B58e), yine de tel oynar.
en: The varnish cracks when the wire moves. There, heat-shrink or insulating tape is the right solution — the lugs are now far apart (B56/B58e), but the wire still moves.
tr: <b>Ölçüm noktaları ve test pedleri</b>
en: <b>Measuring points and test pads</b>
tr: Kaplanmış pede prob değmez; kapı ölçümleri önce.
en: A probe does not contact a coated pad; do the GATE measurements first.
tr: {0}–{1} <b>ince</b> kat, her kat kurusun (tek kalın kat çözücüyü içeride hapseder). Kaplama <b>yüzey kaçağını</b> keser, havadan atlamayı kesmez — mesafe yerine geçmez. Asıl kazanç doğrulukta: HV bölücüsü {2} MΩ olduğu için yüzey kaçağı orana paralel girer ({3} MΩ kirli yüzey ≈ %{4} okuma hatası). Sökmek gerekirse aseton çıkarır, ama aseton bazı plastiklere de saldırır.
en: {0}–{1} <b>thin</b> coats, letting each coat dry (one thick coat traps the solvent inside). The coating stops <b>surface leakage</b>, not arcing through air — it does not replace distance. The real gain is accuracy: since the HV divider is {2} MΩ, surface leakage goes in parallel with the ratio ({3} MΩ of dirty surface ≈ {4}% reading error). If it has to come off, acetone removes it, but acetone also attacks some plastics.
tr: Dar açıklıklar (&lt; {0} mm, iletken taraflı)
en: Narrow clearances (&lt; {0} mm, with a conductive side)
tr: Boşluk
en: Gap
tr: Çift
en: Pair
tr: Sorun mu, ne yapmalı
en: Is it a problem, what to do
tr: {0} mm — devkit'in gövdesi kart B'nin ahşap ayağına değebilir; yalıtkan, yerinde ayarlanır. Anten bu uçta ama ✅ KAPANDI (kullanıcı kararı {1}-{2}-{3}): dahili anten kartın kendi kalınlığında küçük bir çıkıntı, yanındaki ahşap blok sorun değil. Ahşap {4} GHz'de düşük kayıplı ve kutunun tamamı zaten ahşap.
en: {0} mm — the devkit's body can touch board B's wooden foot; it is an insulator, adjusted in place. The antenna is at this end, but ✅ CLOSED (user decision {1}-{2}-{3}): the internal antenna is a small tab the thickness of the board itself, the wooden block next to it is not a problem. Wood has low loss at {4} GHz and the whole enclosure is wood anyway.
tr: B ↔ HV ankraj bloğu
en: B ↔ HV anchor block
tr: {0} mm — kart B ölçülünce {1}×{2} çıktı (model {3} delik alanıydı), ankraja {4}'dan {5}'e indi. Ankraj bilerek kartın önünde: HV kablosu çekilince D8 lehimi değil kablo bağı direniyor. Ahşap, iletken değil.
en: {0} mm — when board B was measured it came out {1}×{2} (the model was a {3}-hole area), the gap to the anchor went down from {4} to {5}. The anchor is in front of the board on purpose: when the HV cable is pulled, the cable tie resists, not the D8 joint. Wood, not a conductor.
tr: B ↔ Q1-köşebent
en: B ↔ Q1 corner bracket
tr: {0} mm — aynı sebep (kart B {1} mm). Q1'in ahşap köşebendi; soğutucunun KENDİSİ daha uzakta. Ahşap-plaket boşluğu, elektriksel risk yok.
en: {0} mm — same reason (board B {1} mm). Q1's wooden corner bracket; the heatsink ITSELF is further away. A wood-to-board gap, no electrical risk.
tr: {0} mm — şöntün gövdesi kart B'nin ahşap ayağına yaklaşıyor. Manganin U havada, altlığa değmiyor; ayak yalıtkan, sorun yok.
en: {0} mm — the shunt's body comes close to board B's wooden foot. The manganin U is in the air, it does not touch the spacer; the foot is an insulator, no problem.
tr: A (boş kenar) ↔ MT1
en: A (empty edge) ↔ MT1
tr: {0} mm — kart A {1} mm'lik ayağa çıkınca ortaya çıktı (kullanıcı kararı: altındaki atlama telleri için {2}–{3} mm gerekiyor). Kartın ARKA BOŞ ŞERİDİ artık z {4}–{5}'de, MT3608 ise z {6}–{7}: düşeyde {8} mm kalıyor. Şerit boş plaket, MT modülü de yalıtkan gövdeli — değmezler, sadece pay daraldı. Gerekirse MT1 bir sıra yukarı alınır.
en: {0} mm — appeared when board A went up onto {1} mm feet (user decision: the jumper wires underneath need {2}–{3} mm). The board's EMPTY BACK STRIP is now at z {4}–{5}, the MT3608 at z {6}–{7}: {8} mm remains vertically. The strip is bare perfboard and the MT module has an insulating body — they do not touch, only the margin got smaller. If needed, MT1 moves up one row.
tr: {0} mm — kart A'nın ön-sağ ayağı ile kart B'nin gövdesi. İkisi de sabit ve ayak {1}'de karttan işaretlenerek konuyor, yani yerinde ayarlanabilir.
en: {0} mm — board A's front-right foot and the body of board B. Both are fixed and the foot is placed in {1} by marking from the board, so it can be adjusted in place.
tr: {0} mm — kart B {1} mm ölçülünce ortaya çıktı (model {2} ile {3} görünüyordu). Elektriksel olarak sorun değil: {4} V'luk düğüm kartın KARŞI kenarında (yön {5}°) ve en yakın iletkene mesafesi {6} mm. Buradaki {7} mm plaket kenarı ↔ devkit gövdesi.
en: {0} mm — appeared when board B was measured at {1} mm (the model showed {3} with {2}). Not an electrical problem: the {4} V node is on the OPPOSITE edge of the board (orientation {5}°) and its distance to the nearest conductor is {6} mm. The {7} mm here is board edge ↔ devkit body.
tr: {0} mm — kart A'nın ahşap ayağı devkit gövdesine yaklaşıyor; yalıtkan, yerinde ayarlanır.
en: {0} mm — board A's wooden foot comes close to the devkit body; an insulator, adjusted in place.
tr: Gerçek 3B boşluk (Öklid), parçanın kendi taşıyıcısı hariç. Liste <b>kilitli</b>: yeni bir iletken taraflı çift {0} mm'nin altına inerse denetim kırmızıya döner. Ayrıca <b>{1} ahşap–ahşap çift</b> {2} mm'nin altında — bunlar tek tek yazılmıyor, bıçakla yerinde ayarlanıyor; denetim yalnız çakışmadıklarına bakıyor.
en: Real 3D clearance (Euclidean), excluding the part's own carrier. The list is <b>locked</b>: if a new pair with a conductive side goes below {0} mm, the audit turns red. In addition <b>{1} wood–wood pairs</b> are below {2} mm — they are not listed one by one, they are trimmed in place with a knife; the audit only checks that they do not collide.
tr: Bu sayfa <code>uretim/kutu.py</code> tarafından, denetim geçtikten sonra üretildi. Kutu ölçüleri ve adımlar <code>kutu_veri.py</code>'den, kablolar <code>yerlesim3_veri.KABLOLAR</code>'dan, KAPI metinleri <code>yerlesim3_belge.KAPI</code>'dan, menziller <code>tasarim3_sabit</code>'ten; çizimler, tablolar ve 3B sahne aynı sayılardan üretiliyor.
en: This page was generated by <code>uretim/kutu.py</code> after the audit passed. Enclosure dimensions and steps come from <code>kutu_veri.py</code>, cables from <code>yerlesim3_veri.KABLOLAR</code>, GATE texts from <code>yerlesim3_belge.KAPI</code>, ranges from <code>tasarim3_sabit</code>; the drawings, tables and 3D scene are generated from the same numbers. The English text is translated from the Turkish page (the master) through <code>uretim/kutu_en.py</code>.
tr: Çubuğunu ve parçaları ölç
en: Measure your sticks and parts
tr: Ölçü ve kesim
en: Measuring and cutting
tr: Kesim listesi — önce taban ve dış kat
en: Cut list — base and outer layer first
tr: Kart A'yı {kart_a_en:.0f} × {kart_a_boy:.0f} mm'ye getir
en: Bring board A to {kart_a_en:.0f} × {kart_a_boy:.0f} mm
tr: Taban sıralarını diz
en: Lay out the base rows
tr: Alttan raylarla bağla
en: Join from underneath with rails
tr: Ön duvar parçalarını del
en: Drill the front wall pieces
tr: Dış kat parçalarını del (düz zeminde)
en: Drill the outer layer pieces (on a flat surface)
tr: Arka duvar parçalarını del
en: Drill the back wall pieces
tr: {0}. sıra — ön ve arka
en: Row {0} — front and back
tr: {0}. sıra — yanlar
en: Row {0} — sides
tr: {0}. sıradan en üste
en: From row {0} to the top
tr: Ölç, kalanı kes
en: Measure, cut the rest
tr: İç kat — dikey çubuklar
en: Inner layer — vertical sticks
tr: Kapak cıvata deliklerini aç (kutu boşken)
en: Drill the lid bolt holes (while the enclosure is empty)
tr: Köşe direkleri
en: Corner posts
tr: İç katı deliklerden geçerek del
en: Drill the inner layer through the holes
tr: Panel parçalarını tak
en: Fit the panel parts
tr: Born jakları tak ({0} adet)
en: Fit the banana jacks ({0} pcs)
tr: PİL anahtarı, CAL jakı ve GÜÇ lambası
en: «PİL» switch, CAL jack and «GÜÇ» lamp
tr: Şarj modülünü (TP1) kart A'dan ÖNCE tak
en: Fit the charging module (TP1) BEFORE board A
tr: Kartları ve güç parçalarını hazırla
en: Prepare the boards and power parts
tr: Ayakları kartla hizala, gömme somun
en: Align the feet with the board, embedded nuts
tr: Ana kartı vidala
en: Screw down the main board
tr: ESP32, kart B ve altlıklar
en: ESP32, board B and spacers
tr: Şönt demetini tezgahta lehimle
en: Solder the shunt harness at the bench
tr: Q1 demeti ve soğutucu
en: Q1 harness and heatsink
tr: Şönt ve Q1'i kutuya al
en: Bring the shunt and Q1 into the enclosure
tr: Yük yolunu bağla
en: Connect the load path
tr: Güç yolu — YÜK jakları, şönt, Kelvin
en: Power path — «YÜK» jacks, shunt, Kelvin
tr: Kelvin ve yıldız konnektörünü tak
en: Plug in the Kelvin and star connector
tr: Q1'i yük yoluna bağla
en: Connect Q1 to the load path
tr: Pil testi yolu — Q1 ve PİL jakları
en: Battery test path — Q1 and «PİL» jacks
tr: Kapı telini tak
en: Connect the gate wire
tr: V ve COM jakları
en: V and COM jacks
tr: Ölçüm girişleri
en: Measurement inputs
tr: HV jakı ve kablo ankrajı
en: HV jack and cable anchor
tr: MT1'i {0} V'a, MT2'yi {1} V'a yüksüz ayarla
en: Set MT1 to {0} V and MT2 to {1} V with no load
tr: Besleme — pil paketi ve analog besleme
en: Supply — battery pack and analog supply
tr: Yuvaları, MT1/MT2'yi, B0505S'i ve hücre sigortalarını tak
en: Fit the holders, MT1/MT2, the B0505S and the cell fuses
tr: Pil paketini kablola (iki hücre paralel)
en: Wire the battery pack (two cells in parallel)
tr: Analog beslemeyi kablola: {0} V → F0 → B0505S → MT2 → klemens → kart
en: Wire the analog supply: {0} V → F0 → B0505S → MT2 → terminal block → board
tr: Kutuda ilk enerji — pilden
en: First power-up in the enclosure — from the battery
tr: Şarj kuralı ve etiket
en: Charging rule and label
tr: J5 kablosu ve entegreler
en: J5 cable and ICs
tr: ESP32 ve ilk iki kapı
en: ESP32 and the first two GATEs
tr: Vref ve I²C kapıları
en: Vref and I²C GATEs
tr: Kalibrasyon ve kalan kapılar
en: Calibration and the remaining GATEs
tr: Kapı {0} — akım (iki aşamalı)
en: GATE {0} — current (two stages)
tr: Kapı {0} — NORMAL gerilim
en: GATE {0} — NORMAL voltage
tr: Kapı {0} — YÜKSEK gerilim
en: GATE {0} — HIGH voltage
tr: Kapı {0} — osiloskop
en: GATE {0} — oscilloscope
tr: Kapı {0} — hızlı akım yolu
en: GATE {0} — fast current path
tr: Kapı {0} — pil testi
en: GATE {0} — battery test
tr: Kapağı yap
en: Make the lid
tr: Kapak — yap, del, dene (henüz kapatma)
en: Lid — make, drill, try (do not close yet)
tr: Kapağı dene — sonra ÇIKAR
en: Try the lid — then TAKE IT OFF
tr: Etiketle ve topla
en: Label and tidy up
tr: Kapat ve son kontrol
en: Close and final check
tr: Kapağı tak ve cıvatala
en: Fit the lid and bolt it down
tr: Kapalı kutuda uçtan uca
en: End to end in the closed enclosure
tr: A-ayak1 — A için
en: A-foot1 — for A
tr: ayak bloğu · gömme M3 somunlu
en: foot block · with embedded M3 nut
tr: Ölçü
en: Size
tr: {0} × {1} mm, yükseklik {2} mm
en: {0} × {1} mm, height {2} mm
tr: {0} çubuk üst üste lamine
en: {0} sticks laminated on top of each other
tr: Ayak bloğu parçası — A ({0} blok × {1} kat) — {2} mm × {3}
en: Foot block piece — A ({0} blocks × {1} layers) — {2} mm × {3}
tr: x {0} · y {1} mm (sol-arka iç köşeden)
en: x {0} · y {1} mm (from the back-left inside corner)
tr: Adım
en: Step
tr: {0} · Ayakları kartla hizala, gömme somun
en: {0} · Align the feet with the board, embedded nuts
tr: A-ayak2 — A için
en: A-foot2 — for A
tr: A-ayak3 — A için
en: A-foot3 — for A
tr: A-ayak4 — A için
en: A-foot4 — for A
tr: B-ayak1 — B için
en: B-foot1 — for B
tr: Ayak bloğu parçası — B ({0} blok × {1} kat) — {2} mm × {3}
en: Foot block piece — B ({0} blocks × {1} layers) — {2} mm × {3}
tr: B-ayak2 — B için
en: B-foot2 — for B
tr: ESP32-altlık1a — ESP32 için
en: ESP32-spacer1a — for ESP32
tr: altlık
en: spacer
tr: Altlık — ESP32 — {0} mm × {1}
en: Spacer — ESP32 — {0} mm × {1}
tr: {0} · ESP32, kart B ve altlıklar
en: {0} · ESP32, board B and spacers
tr: ESP32-altlık1b — ESP32 için
en: ESP32-spacer1b — for ESP32
tr: ESP32-altlık2a — ESP32 için
en: ESP32-spacer2a — for ESP32
tr: ESP32-altlık2b — ESP32 için
en: ESP32-spacer2b — for ESP32
tr: ESP32-ray-sağ-arka — ESP32 için
en: ESP32-rail-right-back — for ESP32
tr: ESP32 kızağı · dik şerit, kutu parçası
en: ESP32 cradle · upright strip, enclosure part
tr: ESP32 kızak rayı — {0} mm şerit, uzun kenarı üstünde dik — {1} mm × {2}
en: ESP32 cradle rail — {0} mm strip, upright on its long edge — {1} mm × {2}
tr: ESP32-ray-sağ-ön — ESP32 için
en: ESP32-rail-right-front — for ESP32
tr: ESP32-ray-sol-arka — ESP32 için
en: ESP32-rail-left-back — for ESP32
tr: ESP32-ray-sol-ön — ESP32 için
en: ESP32-rail-left-front — for ESP32
tr: ESP32-takoz-sağ — ESP32 için
en: ESP32-block-right — for ESP32
tr: ESP32 omuz takozu — {0} mm şerit, ikiye böl ({1} + {2}) — {3} mm × {4}
en: ESP32 shoulder block — {0} mm strip, split in two ({1} + {2}) — {3} mm × {4}
tr: ESP32-takoz-sol — ESP32 için
en: ESP32-block-left — for ESP32
tr: HV ankraj bloğu
en: HV anchor block
tr: kutu parçası · ahşap
en: enclosure part · wood
tr: Üç çubuk parçası üst üste, kart B'nin önünde tabana dik yapıştırılır; HV kablosu buna kablo bağıyla tutulur — çekilince D8 lehimi değil bağ direnir.
en: Three stick pieces stacked, glued upright to the base in front of board B; the HV cable is held to it with a cable tie — when pulled, the tie resists, not the D8 joint.
tr: HV ankraj bloğu ({0} kat) — {1} mm × {2}
en: HV anchor block ({0} layers) — {1} mm × {2}
tr: {0} · HV jakı ve kablo ankrajı
en: {0} · HV jack and cable anchor
tr: Q1-köşebent — Q1 için
en: Q1-bracket — for Q1
tr: köşebent
en: corner bracket
tr: Köşebent parçası — Q1 ({0} kat) — {1} mm × {2}
en: Corner bracket piece — Q1 ({0} layers) — {1} mm × {2}
tr: {0} · Şönt ve Q1'i kutuya al
en: {0} · Bring the shunt and Q1 into the enclosure
tr: RS-altlık1a — RS için
en: RS-spacer1a — for RS
tr: Altlık — RS — {0} mm × {1}
en: Spacer — RS — {0} mm × {1}
tr: RS-altlık1b — RS için
en: RS-spacer1b — for RS
tr: Dış kat — arka duvar, {0}. sıra, sağ (arkadan)
en: Outer layer — back wall, row {0}, right (from behind)
tr: çubuk parçası · dil basacağı (tahta çubuk)
en: stick piece · tongue depressor (wooden stick)
tr: Dış kat arka sıra {0} — sağ (arkadan) — {1} mm × {2}
en: Outer layer back row {0} — right (from behind) — {1} mm × {2}
tr: çubuğun düz bölümünden
en: from the flat section of the stick
tr: {0} · {1}. sıra — ön ve arka
en: {0} · Row {1} — front and back
tr: Dış kat — arka duvar, {0}. sıra, sol (arkadan)
en: Outer layer — back wall, row {0}, left (from behind)
tr: Dış kat arka sıra {0} — sol (arkadan) — {1} mm × {2}
en: Outer layer back row {0} — left (from behind) — {1} mm × {2}
tr: {0} · {1}. sıradan en üste
en: {0} · From row {1} to the top
tr: Dış kat — sağ yan duvar, {0}. sıra
en: Outer layer — right side wall, row {0}
tr: Dış kat yan sıra {0} — kısa parça — {1} mm × {2}
en: Outer layer side row {0} — short piece — {1} mm × {2}
tr: {0} · {1}. sıra — yanlar
en: {0} · Row {1} — sides
tr: Dış kat yan sıra {0} — uzun parça — {1} mm × {2}
en: Outer layer side row {0} — long piece — {1} mm × {2}
tr: Dış kat yan sıra {0}–{1} — kısa parça — {2} mm × {3}
en: Outer layer side rows {0}–{1} — short piece — {2} mm × {3}
tr: Dış kat yan sıra {0}–{1} — uzun parça — {2} mm × {3}
en: Outer layer side rows {0}–{1} — long piece — {2} mm × {3}
tr: Dış kat — sol yan duvar, {0}. sıra
en: Outer layer — left side wall, row {0}
tr: Dış kat — ön duvar, {0}. sıra, sağ
en: Outer layer — front wall, row {0}, right
tr: Dış kat ön sıra {0} — sağ — {1} mm × {2}
en: Outer layer front row {0} — right — {1} mm × {2}
tr: Dış kat — ön duvar, {0}. sıra, sol
en: Outer layer — front wall, row {0}, left
tr: Dış kat ön sıra {0} — sol — {1} mm × {2}
en: Outer layer front row {0} — left — {1} mm × {2}
tr: Kapak rayı — sağ
en: Lid rail — right
tr: Yan duvara {0} mm pay bırakarak, {1} mm yüzü dik.
en: Leaving {0} mm of clearance to the side wall, {1} mm face upright.
tr: Kapak rayı (yan duvara yaslı, tek parça) — {0} mm × {1}
en: Lid rail (against the side wall, one piece) — {0} mm × {1}
tr: {0} · Kapağı yap
en: {0} · Make the lid
tr: Kapak rayı — sol
en: Lid rail — left
tr: Kapak — {0}. sıra, kısa parça
en: Lid — row {0}, short piece
tr: Kapak sırası — kısa parça — {0} mm × {1}
en: Lid row — short piece — {0} mm × {1}
tr: Kapak — {0}. sıra, uzun parça
en: Lid — row {0}, long piece
tr: Kapak sırası — uzun parça — {0} mm × {1}
en: Lid row — long piece — {0} mm × {1}
tr: Taban rayı — sağ ray, kısa parça
en: Base rail — right rail, short piece
tr: Tabanın altına, sıralara dik; kutu bu iki rayın üstünde durur.
en: Under the base, across the rows; the enclosure stands on these two rails.
tr: Taban rayı — kısa parça — {0} mm × {1}
en: Base rail — short piece — {0} mm × {1}
tr: {0} · Alttan raylarla bağla
en: {0} · Join from underneath with rails
tr: Taban rayı — sağ ray, uzun parça
en: Base rail — right rail, long piece
tr: Taban rayı — uzun parça — {0} mm × {1}
en: Base rail — long piece — {0} mm × {1}
tr: Taban rayı — sol ray, kısa parça
en: Base rail — left rail, short piece
tr: Taban rayı — sol ray, uzun parça
en: Base rail — left rail, long piece
tr: Taban — {0}. sıra, kısa parça
en: Base — row {0}, short piece
tr: Taban sırası — kısa parça — {0} mm × {1}
en: Base row — short piece — {0} mm × {1}
tr: {0} · Taban sıralarını diz
en: {0} · Lay out the base rows
tr: Taban — {0}. sıra, uzun parça
en: Base — row {0}, long piece
tr: Taban sırası — uzun parça — {0} mm × {1}
en: Base row — long piece — {0} mm × {1}
tr: İç kat — arka duvar, x {0}–{1}
en: Inner layer — back wall, x {0}–{1}
tr: İç kat dikey çubuk (yuvarlak uç aşağı) — {0} mm × {1}
en: Inner layer vertical stick (rounded end down) — {0} mm × {1}
tr: tek uçlu: yuvarlak uç bir tarafta kalır
en: single-ended: the rounded end stays on one side
tr: {0} · İç kat — dikey çubuklar
en: {0} · Inner layer — vertical sticks
tr: Kısa çubuk: altındaki yuvanın üstünden, z {0} mm'den başlıyor.
en: Short stick: starts above the slot below it, from z {0} mm.
tr: İç kat kısa çubuk — x {0}, yuvanın üstü (z {1}'dan) — {2} mm × {3}
en: Inner layer short stick — x {0}, above the slot (from z {1}) — {2} mm × {3}
tr: yarım çubuk: bir çubuktan iki tane
en: half stick: two from one stick
tr: İç kat — sağ yan duvar, y {0}–{1}
en: Inner layer — right side wall, y {0}–{1}
tr: İç kat — sol yan duvar, y {0}–{1}
en: Inner layer — left side wall, y {0}–{1}
tr: İç kat — ön duvar, x {0}–{1}
en: Inner layer — front wall, x {0}–{1}
tr: MT2 giriş kondansatörü {0} µF {1} V (elektrolitik)
en: MT2 input capacitor {0} µF {1} V (electrolytic)
tr: duvara asılı · arka duvarın iç yüzü
en: hung on the wall · inside face of the back wall
tr: MT2'nin üstüne, yatık (gövde x yönünde), gövdesinden sıcak silikonla. Bacakları MT2'nin giriş pedlerine lehimli — ⚠ Elektrolitik: şeritli bacak EKSİ (MT2 IN−), uzun bacak artı (MT2 IN+). İzopropil alkol ve iki bacağın …
en: Above MT2, lying down (body along x), hot-glued by its body. Its legs are soldered to MT2's input pads — ⚠ Electrolytic: the striped leg is NEGATIVE (MT2 IN−), the long leg positive (MT2 IN+). Removed with isopropyl alcohol and by …
tr: {0} × {1} mm, duvardan {2} mm çıkıntı
en: {0} × {1} mm, sticking out {2} mm from the wall
tr: sıcak silikon ile yapıştırılı — sökmek: derze izopropil alkol damlat, plastik kartla kaldır
en: glued with hot glue — to remove: drip isopropyl alcohol into the joint, lift with a plastic card
tr: Takıldığı adım
en: Fitted in step
tr: {0} · Yuvaları, MT1/MT2'yi, B0505S'i ve hücre sigortalarını tak
en: {0} · Fit the holders, MT1/MT2, the B0505S and the cell fuses
tr: Analog sigortası F0 ({0}×{1} PCB klipsli, {2} A F)
en: Analog fuse F0 ({0}×{1} PCB clips, {2} A F)
tr: Arka duvarın sol ucuna, MT1'in soluna ve B0505S'in altına (konum listesinde): iki klips + en fazla {0} mm'lik plaket şeridi (FUS009 tek gövde değil), şeridin arkasından sıcak silikonla. İçine {1} A hızlı cam sigorta …
en: At the left end of the back wall, to the left of MT1 and below the B0505S (in the position list): two clips + a perfboard strip of at most {0} mm (FUS009 is not a single body), hot-glued from the back of the strip. Holds a {1} A fast glass fuse …
tr: Hücre {0} sigorta yuvası ({1}×{2} PCB klipsli)
en: Cell {0} fuse holder ({1}×{2} PCB clips)
tr: B0505S yalıtılmış DC-DC ({0} V → {1} V, {2} W)
en: B0505S isolated DC-DC ({0} V → {1} V, {2} W)
tr: MT2'nin soluna, bacaklar aşağı; dört bacağına ince tel lehimli ve makaronlu. Gövdesinden sıcak silikonla duvara; izopropil alkolle sökülür. Giriş ({0} +Vin, {1} −Vin) ve çıkış ({2} −Vout, {3} +Vout) tarafı hiçbir telle …
en: To the left of MT2, pins down; thin wire soldered to all four pins and heat-shrunk. Hot-glued to the wall by its body; removed with isopropyl alcohol. The input side ({0} +Vin, {1} −Vin) and the output side ({2} −Vout, {3} +Vout) are not joined by any …
tr: {0} V iç klemens ({1}'li, {2} mm)
en: {0} V internal terminal block ({1}-way, {2} mm)
tr: B0505S'in üstüne, tabanından sıcak silikonla (PCB klemensinde montaj deliği yok). Vidalar içe: {0}'te MT2'nin çıkışı ve kartın {1} V telleri buraya vidalanır. Hangi vidanın + olduğunu kalemle yaz. İzopropil alkolle …
en: Above the B0505S, hot-glued by its base (the PCB terminal block has no mounting hole). Screws facing in: in {0} MT2's output and the board's {1} V wires are screwed in here. Write with a pen which screw is +. Removed with isopropyl …
tr: Arka duvarın iç yüzüne düz (A'nın boş arka şeridinin üstü), sıcak silikonla — PCB'nin arkasından, çipin ve bobinin üstüne değil. OUT pedleri SOLA (F0 ve B0505S). Trimpot içe bakar, ayar kapak açıkken. Derze izopropil …
en: Flat on the inside face of the back wall (above A's empty back strip), with hot glue — on the back of the PCB, not on the chip and the inductor. OUT pads to the LEFT (F0 and B0505S). Trimpot facing in, adjusted with the lid open. Removed with isopropyl …
tr: MT3608 — {0} V (analog ray)
en: MT3608 — {0} V (analog rail)
tr: TP4056 şarj modülü — paket (raf)
en: TP4056 charging module — pack (shelf)
tr: Kart RAF gibi yatay ({0} × {1} × {2} ölçüldü, soket kart kenarından {3} mm dışarı): soket ŞARJ yuvasına girer. Kart A'nın arka boş şeridinin ALTINDA kalır — bu yüzden kart A'dan önce ({4}), kabloları tezgahta lehimlenmiş …
en: The board lies horizontally like a SHELF ({0} × {1} × {2} measured, socket {3} mm beyond the board edge): the socket goes into the «ŞARJ» slot. It sits UNDER the empty back strip of board A — that is why it is fitted before board A ({4}), with its wires soldered at the bench …
tr: raf: {0} × {1} mm + {2} × {3} mm + {4} × {5} mm çubuk, {6} mm bağ kanalı
en: shelf: {0} × {1} mm + {2} × {3} mm + {4} × {5} mm sticks, {6} mm tie channel
tr: {0} · Şarj modülünü (TP1) kart A'dan ÖNCE tak
en: {0} · Fit the charging module (TP1) BEFORE board A
tr: {0} yuvası — hücre {1} (paket, paralel)
en: {0} holder — cell {1} (pack, parallel)
tr: {0} × {1} × {2} (ölçüldü). Arka duvarın iç yüzüne SICAK SİLİKONLA yapıştırılır (kullanıcı kararı {3}-{4}-{5}, cıvata yok): yuvanın tabanına boydan boya iki şerit, duvara {6} s bastır. Sökülebilir: ısı tabancasıyla ısıt ya …
en: {0} × {1} × {2} (measured). Glued to the inside face of the back wall WITH HOT GLUE (user decision {3}-{4}-{5}, no bolts): two beads along the full length of the holder's base, press against the wall {6} s. Removable: warm it with a heat gun or …
tr: sıcak silikon ile yapıştırılı — sökmek: ısı tabancasıyla ısıt ya da derze izopropil alkol damlat, maket bıçağıyla kaldır
en: glued with hot glue — to remove: warm it with a heat gun or drip isopropyl alcohol into the joint, lift with a utility knife
tr: YUVA1 ile aynı: arka duvarın iç yüzüne SICAK SİLİKONLA yapıştırılır, cıvata yok. Sökülebilir: ısı tabancası ya da izopropil alkol, maket bıçağıyla kaldır. Yuva {0} mm (ölçüldü); üstünde kapağa pay kalır, {1} kontrol …
en: Same as YUVA1: glued to the inside face of the back wall WITH HOT GLUE, no bolts. Removable: heat gun or isopropyl alcohol, lift with a utility knife. Holder {0} mm (measured); there is room for the lid above it, {1} checks …
tr: CAL kare dalga çıkışı (ESP32 GPIO10, seri dirençli)
en: CAL square-wave output (ESP32 GPIO10, with series resistor)
tr: born jak · ön duvar
en: banana jack · front wall
tr: Kartın test sinyali (X ile açılır) kapak KAPALIYKEN de dışarıdan alınsın diye: skop kapısı ({0}) ve kapalı-kutu testi ({1}) CAL → SKOP kısa patch kablosuyla yapılır. GPIO10 J5'te yok; devkit'ten tek dişi jumper + {2} …
en: So that the board's test signal (switched on with X) can be taken from outside even with the lid CLOSED: the scope GATE ({0}) and the closed-enclosure test ({1}) are done with a short CAL → «SKOP» patch lead. GPIO10 is not on J5; a single female jumper from the devkit + {2} …
tr: Panelde yazan
en: Printed on the panel
tr: CAL (→ SKOP'a kısa kablo)
en: CAL (→ short lead to «SKOP»)
tr: Metal gövde
en: Metal body
tr: x {0} · z {1} mm ({2}. sıra)
en: x {0} · z {1} mm (row {2})
tr: Delindiği adım
en: Drilled in step
tr: {0} · Ön duvar parçalarını del
en: {0} · Drill the front wall pieces
tr: {0} · PİL anahtarı, CAL jakı ve GÜÇ lambası
en: {0} · «PİL» switch, CAL jack and «GÜÇ» lamp
tr: Havalandırma — üst sol (çıkış)
en: Ventilation — top left (outlet)
tr: havalandırma deliği · arka duvar
en: ventilation hole · back wall
tr: Üst sıranın sol ucunda; HV2'nin aynası. Hiçbir parça kapatmıyor (YUVA2 x {0}'den başlar, B0505S z {1}'de biter).
en: At the left end of the top row; the mirror of HV2. No part covers it (YUVA2 starts at x {0}, the B0505S ends at z {1}).
tr: ≋ (havalandırma)
en: ≋ (ventilation)
tr: {0} · Arka duvar parçalarını del
en: {0} · Drill the back wall pieces
tr: Havalandırma — üst sağ (çıkış)
en: Ventilation — top right (outlet)
tr: Üst sıranın sağ ucunda, HV1 ile tam simetrik; F2 (z {0}–{1}) çok altta kalıyor.
en: At the right end of the top row, exactly symmetric to HV1; F2 (z {0}–{1}) is well below.
tr: Havalandırma — alt sol (giriş)
en: Ventilation — bottom left (inlet)
tr: Alt yarıda, ŞARJ yuvasının (x {0}) sağında ve F1P'nin (z {1}–{2}) üstünde; HV4'ün aynası.
en: In the lower half, to the right of the «ŞARJ» slot (x {0}) and above F1P (z {1}–{2}); the mirror of HV4.
tr: Havalandırma — alt sağ (giriş)
en: Ventilation — bottom right (inlet)
tr: En alt sırada, USB yuvasının (x {0}–{1}) sağında; F2 x {2}'den başlıyor. HV3'ün aynası.
en: On the bottom row, to the right of the USB slot (x {0}–{1}); F2 starts at x {2}. The mirror of HV3.
tr: V girişi
en: V input
tr: NORMAL gerilim kanalı.
en: NORMAL voltage channel.
tr: {0} · Born jakları tak ({1} adet)
en: {0} · Fit the banana jacks ({1} pcs)
tr: COM (ortak)
en: COM (common)
tr: TEK COM: V, HV ve SKOP'un ortak ucu; içeride YÜK {0} ve PİL {1} ile aynı düğüm.
en: ONE COM: the common terminal of V, HV and «SKOP»; inside it is the same node as «YÜK» {0} and «PİL» {1}.
tr: COM (= YÜK {0} = PİL {1})
en: COM (= «YÜK» {0} = «PİL» {1})
tr: YÜKSEK gerilim girişi
en: HIGH voltage input
tr: Sağ kenarda, orta sırada: COM · V · HV — ölçüm probu COM'un yanından alınır. İşaretli; arka ucu makaronla kaplanır. Komşusunda CAL yok (bilerek).
en: At the right edge, in the middle row: COM · V · HV — the measuring probe is taken next to COM. Marked; its back end is covered with heat-shrink. CAL is not its neighbour (on purpose).
tr: YÜK {0} — devrenin eksisi
en: «YÜK» {0} — the circuit's negative
tr: Akım buradan girer: ölçülen yükün EKSİ ucu. Yükün + ucu kutuya gelmez, doğrudan kaynağın +'sına.
en: The current enters here: the NEGATIVE end of the load being measured. The load's + does not come to the enclosure, it goes straight to the source's +.
tr: YÜK {0} (yükün −)
en: «YÜK» {0} (load −)
tr: YÜK {0} — kaynağın eksisi
en: «YÜK» {0} — the source's negative
tr: Kaynağın EKSİ ucu. Şöntün alt bacağı = kart GND = COM.
en: The source's NEGATIVE end. Bottom leg of the shunt = board GND = COM.
tr: YÜK {0} (kaynağın −)
en: «YÜK» {0} (source −)
tr: Osiloskop girişi
en: Oscilloscope input
tr: Dalga şekli kanalı.
en: Waveform channel.
tr: PİL {0} — yük direncinin ucu
en: «PİL» {0} — the load resistor's end
tr: Q1'in savağı. Pilin + ucu buraya DİRENÇ ÜSTÜNDEN gelir (pil + → direnç → PİL {0}); ayrıca pil + → V.
en: Q1's drain. The battery's + comes here THROUGH THE RESISTOR (battery + → resistor → «PİL» {0}); and separately battery + → V.
tr: PİL {0} (direnç ← pil +)
en: «PİL» {0} (resistor ← battery +)
tr: PİL {0} — pilin eksisi
en: «PİL» {0} — the battery's negative
tr: Pilin EKSİ ucu. YÜK {0} ile aynı düğüm (şönt altı).
en: The battery's NEGATIVE end. Same node as «YÜK» {0} (bottom of the shunt).
tr: PİL {0} (pil −)
en: «PİL» {0} (battery −)
tr: GÜÇ lambası — analog raylar ayakta
en: «GÜÇ» lamp — analog rails up
tr: LED · ön duvar
en: LED · front wall
tr: PASİF: ESP32'ye bağlı DEĞİL, firmware gerektirmez. +{0} rayı ile kart GND arasında {1} kΩ seri direnç (R060) + {2} mm yeşil LED (LED003) — PİL anahtarının ve F0'ın ardında olduğu için yalnız kart gerçekten enerjiliyken …
en: PASSIVE: NOT connected to the ESP32, needs no firmware. {1} kΩ series resistor (R060) + {2} mm green LED (LED003) between the +{0} rail and board GND — since it sits behind the «PİL» switch and F0, only when the board is really powered …
tr: GÜÇ (±{0} V var)
en: «GÜÇ» (±{0} V present)
tr: Şarj girişi — TP4056 Type-C (iki hücre birlikte)
en: Charging input — TP4056 Type-C (both cells together)
tr: oval yuva (delik) · arka duvar
en: oval slot (hole) · back wall
tr: TP1 rafının Type-C soketi bu yuvadan bakar; iki hücre paralel, tek kabloyla birlikte dolar. Paketin eksisi kart GND: şarj kablosu COM'u (ölçülen devrenin referansı) şarj cihazının toprağına bağlar — şarj ederken ölçüm …
en: The Type-C socket of the TP1 shelf looks out through this slot; the two cells in parallel charge together with one cable. The pack negative is board GND: the charging cable connects COM (the reference of the circuit being measured) to the charger's ground — while charging, no measuring …
tr: ŞARJ (PİL kapalıyken)
en: «ŞARJ» (with «PİL» off)
tr: {0} × {1} mm oval
en: {0} × {1} mm oval
tr: PİL anahtarı (kutunun tek AÇ/KAPA'sı)
en: «PİL» switch (the enclosure's only on/off switch)
tr: anahtar / panel parçası · ön duvar
en: switch / panel part · front wall
tr: KTS102: paket (TP4056 OUT+) → MT1. Açınca ESP32 ve ölçüm tarafı (±{0} V) birlikte açılır; kapalıyken kutu tamamen enerjisiz ve MT1 hiç çekmez. Şarj ederken KAPALI; USB'yi PC'ye takarken AÇIK (yükü pil taşır). Sol üstte, …
en: KTS102: pack (TP4056 OUT+) → MT1. Switched on, the ESP32 and the measurement side (±{0} V) come on together; switched off, the enclosure is completely unpowered and MT1 draws nothing. OFF while charging; ON when plugging the USB into the PC (the battery carries the load). Top left, …
tr: AÇ / KAPA (PİL)
en: «AÇ / KAPA» («PİL»)
tr: ESP32 USB yuvası
en: ESP32 USB slot
tr: {0} × {1} mm oval yuva; devkit'in COM yazan Type-C soketi buraya bakar.
en: {0} × {1} mm oval slot; the devkit's Type-C socket marked COM looks out here.
tr: USB (⚡ HV ölçerken çıkar)
en: USB (⚡ unplug when measuring HV)
tr: Köşe direği D1
en: Corner post D1
tr: kutu iskeleti · lamine çubuk
en: enclosure frame · laminated sticks
tr: Yükseklik
en: Height
tr: {0} × {1} mm ({2} çubuk üst üste)
en: {0} × {1} mm ({2} sticks stacked)
tr: Köşe direği parçası (yuvarlak uç aşağı) — {0} mm × {1}
en: Corner post piece (rounded end down) — {0} mm × {1}
tr: {0} · Köşe direkleri
en: {0} · Corner posts
tr: Köşe direği D2
en: Corner post D2
tr: Köşe direği D3
en: Corner post D3
tr: Köşe direği D4
en: Corner post D4
tr: kesim listesi satırı
en: cut list row
tr: Ana kart ({0}×{1} delikli plaket, {2}×{3} kesilmiş)
en: Main board ({0}×{1} perfboard, cut to {2}×{3})
tr: kart / güç parçası · kutunun tabanında
en: board / power part · on the enclosure floor
tr: Dört köşede ahşap ayak bloğu (gömme M3 somunlu); plaket M3x10 vidayla ayaklara. YAPIŞTIRILMAZ — vidayı sök, kart çıkar. Telli kenarı (A–C sütunları) ÖN panele baksın.
en: A wooden foot block in each of the four corners (with embedded M3 nut); the perfboard is screwed to the feet with M3x10 screws. NOT GLUED — take out the screws, the board comes out. The wired edge (columns A–C) faces the FRONT panel.
tr: {0} mm (ayak / altlık üstünde)
en: {0} mm (on feet / spacer)
tr: Taban izi
en: Footprint
tr: x {0}–{1} · y {2}–{3} mm (sol-arka iç köşeden)
en: x {0}–{1} · y {2}–{3} mm (from the back-left inside corner)
tr: Taşıyıcı
en: Carrier
tr: {0} × ayak, {1} kat
en: {0} × foot, {1} layers
tr: HV zinciri kartı ({0}×{1} cm)
en: HV chain board ({0}×{1} cm)
tr: İki ahşap ayak (gömme somunlu) + M3 vida. YÖN ÖNEMLİ: A1 köşesi (ön-sol) kutunun o köşesine baksın. Bu yönde {0} V'luk düğüm kutudaki her iletkenden en uzak ve HV kablosu ({1} mm) en kısa. Sökülebilir.
en: Two wooden feet (with embedded nuts) + M3 screws. ORIENTATION MATTERS: the A1 corner (front-left) faces that corner of the enclosure. In this orientation the {0} V node is furthest from every conductor in the enclosure and the HV cable ({1} mm) is the shortest. Removable.
tr: ESP32-S3 devkit
en: ESP32-S3 devkit
tr: Pinler yukarı, USB soketi ARKA duvara {0} mm. Altlık dört parça: iki sıra, her sıra ortadan bölük — aradaki {1} mm kanal kablo bağının geçtiği yer. Altlığın üstünde kızak: iki yanda dik raylar, anten ucunda anten …
en: Pins up, USB socket {0} mm from the BACK wall. Spacer in four pieces: two rows, each split in the middle — the {1} mm channel between them is where the cable tie runs. On top of the spacer, the cradle: upright rails on both sides, at the antenna end antenna …
tr: {0} × altlik
en: {0} × spacer
tr: IRFZ44N + soğutucu
en: IRFZ44N + heatsink
tr: Soğutucu DİK (kanatlar y yönünde), ahşap köşebende M3 vida + somun. MOSFET'in tabı soğutucudan yalıtılmış. Kapı teli konnektörle. Sökülebilir.
en: Heatsink UPRIGHT (fins along y), on the wooden corner bracket with an M3 screw + nut. The MOSFET's tab is insulated from the heatsink. Gate wire with a connector. Removable.
tr: {0} × kosebent
en: {0} × corner bracket
tr: {0} mΩ Ø{1} şönt (R042, {2} A) — {3} mΩ yedek
en: {0} mΩ Ø{1} shunt (R042, {2} A) — {3} mΩ spare
tr: Bacakları (veri sayfası: {0} mm aralık — önce bükmeden dene) XP128 {1} mm klemense (CON064) vidalanır — klemens tek çubuk altlığa yapışık; kalın yük kabloları XP128'e girmez, yanındaki bariyer klemenste (HB950) birleşir, …
en: Its legs (datasheet: {0} mm spacing — try it before bending) are screwed into the XP128 {1} mm terminal block (CON064) — the terminal block is glued to a single-stick spacer; the heavy load cables do not go into the XP128, they join at the barrier terminal block (HB950) next to it, …
tr: Dış kat — arka duvar, {0}. sıra
en: Outer layer — back wall, row {0}
tr: iki çubuk parçası, ek yeri kaydırmalı
en: two stick pieces, joint staggered
tr: sol parça
en: left piece
tr: sağ parça
en: right piece
tr: Ek yeri
en: Joint
tr: x {0} mm (dış sol kenardan, bu yüze bakınca)
en: x {0} mm (from the outer left edge, looking at this face)
tr: Dış kat — ön duvar, {0}. sıra
en: Outer layer — front wall, row {0}
tr: Kablo {0}: {1} µF uzun bacak → MT2 IN+
en: Cable {0}: {1} µF long leg → MT2 IN+
tr: kablo · kondansatör bacağı
en: cable · capacitor leg
tr: {0} µF artısı (uzun bacak) → MT2 IN+ (B0505S +Vo ile aynı nokta) · Uç yerleri ±{1} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: {0} µF positive (long leg) → MT2 IN+ (same point as B0505S +Vo) · End positions ±{1} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: Kesim boyu
en: Cut length
tr: kesilmez (kendi bacağı)
en: not cut (its own leg)
tr: Güzergah
en: Route
tr: {0} · Analog beslemeyi kablola: {1} V → F0 → B0505S → MT2 → klemens → kart
en: {0} · Wire the analog supply: {1} V → F0 → B0505S → MT2 → terminal block → board
tr: Kablo {0}: {1} µF şeritli bacak → MT2 IN− (−{2} tarafı)
en: Cable {0}: {1} µF striped leg → MT2 IN− (−{2} side)
tr: {0} µF eksisi (şeritli bacak) → MT2 IN− — −{1} rayı tarafı · Uç yerleri ±{2} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: {0} µF negative (striped leg) → MT2 IN− — the −{1} rail side · End positions ±{2} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: Kablo {0}: ESP32 GPIO10 → CAL jakının lehim kulağı
en: Cable {0}: ESP32 GPIO10 → solder lug of the CAL jack
tr: kablo · sinyal (J5, CAL)
en: cable · signal (J5, CAL)
tr: {0} kΩ seri direnç jakın iç ucunda, makaronlu · Uç yerleri ±{1} mm tahmin.
en: {0} kΩ series resistor at the inner end of the jack, heat-shrunk · End positions ±{1} mm estimate.
tr: {0} · J5 kablosu ve entegreler
en: {0} · J5 cable and ICs
tr: Kablo {0}: ESP32 pinleri (J5 kablosu) → kart A J5 başlığı
en: Cable {0}: ESP32 pins (J5 cable) → board A header J5
tr: {0} telli kablo; tel eşlemesi Yerleşim {1} · Uç yerleri ±{2} mm tahmin.
en: {0}-wire cable; wire mapping in Layout {1} · End positions ±{2} mm estimate.
tr: Kablo {0}: F0 klips {1} → B0505S {2} (+Vin)
en: Cable {0}: F0 clip {1} → B0505S {2} (+Vin)
tr: kablo · artı ({0} V / {1} V)
en: cable · positive ({0} V / {1} V)
tr: F0 → B0505S Vin · Uç yerleri ±{0} mm tahmin; B0505S'in gövdesinde ad YOK: bacak numarası {1}, {2}, {3}, {4} ({5}) — yan yana iki bacak giriş.
en: F0 → B0505S Vin · End positions ±{0} mm estimate; the B0505S has NO names on its body: pin numbers {1}, {2}, {3}, {4} ({5}) — the two pins side by side are the input.
tr: Kablo {0}: F1P klips {1} (çıkış) → TP4056 B+ teli
en: Cable {0}: F1P clip {1} (output) → TP4056 B+ wire
tr: kablo · hücre → sigorta → TP4056
en: cable · cell → fuse → TP4056
tr: sigorta → TP4056 B+ · Uç yerleri ±{0} mm tahmin; TP4056'da ped adları kartın üstünde (B+ / B− / OUT+ / OUT−).
en: fuse → TP4056 B+ · End positions ±{0} mm estimate; on the TP4056 the pad names are printed on the board (B+ / B− / OUT+ / OUT−).
tr: TP4056'nın kendi teli: pedden {0} cm'de kes
en: The TP4056's own wire: cut it {0} cm from the pad
tr: {0} · Pil paketini kablola (iki hücre paralel)
en: {0} · Wire the battery pack (two cells in parallel)
tr: Kablo {0}: F2 klips {1} (çıkış) → F1P klips {2} (çıkış)
en: Cable {0}: F2 clip {1} (output) → F1P clip {2} (output)
tr: sigorta → F1P'nin çıkış klipsi = TP4056 B+ düğümü (iki hücre burada paralel) · Uç yerleri ±{0} mm tahmin.
en: fuse → F1P output clip = TP4056 B+ node (the two cells are in parallel here) · End positions ±{0} mm estimate.
tr: Kablo {0}: {1}. yuvanın kırmızı teli → F1P klips {2}
en: Cable {0}: red wire of holder {1} → F1P clip {2}
tr: hücre {0} artı → kendi sigortası (yuva ucundan, kırmızı) · Uç yerleri ±{1} mm tahmin.
en: cell {0} positive → its own fuse (from the holder end, red) · End positions ±{1} mm estimate.
tr: yuvanın kendi teli: {0} cm gerekir (uzunsa kes, kısaysa ek)
en: the holder's own wire: {0} cm needed (cut if long, splice if short)
tr: Kablo {0}: {1}. yuvanın siyah teli → TP4056 B− teli
en: Cable {0}: black wire of holder {1} → TP4056 B− wire
tr: kablo · paket / kart GND
en: cable · pack / board GND
tr: hücre {0} eksi — siyah · Uç yerleri ±{1} mm tahmin; TP4056'da ped adları kartın üstünde (B+ / B− / OUT+ / OUT−).
en: cell {0} negative — black · End positions ±{1} mm estimate; on the TP4056 the pad names are printed on the board (B+ / B− / OUT+ / OUT−).
tr: yuvanın kendi teli: {0} cm gerekir (uzunsa kes, kısaysa ek); TP4056'nın telini pedden {1} cm'de kes, ikisini orada birleştir (lehim + makaron)
en: the holder's own wire: {0} cm needed (cut if long, splice if short); cut the TP4056's wire {1} cm from the pad, join the two there (solder + heat-shrink)
tr: Kablo {0}: {1}. yuvanın kırmızı teli → F2 klips {2}
en: Cable {0}: red wire of holder {1} → F2 clip {2}
tr: hücre {0} artı → kendi sigortası (paralelde her hücrenin ayrı sigortası şart) · Uç yerleri ±{1} mm tahmin.
en: cell {0} positive → its own fuse (in parallel, each cell must have its own fuse) · End positions ±{1} mm estimate.
tr: hücre {0} eksi — siyah (paralel) · Uç yerleri ±{1} mm tahmin; TP4056'da ped adları kartın üstünde (B+ / B− / OUT+ / OUT−).
en: cell {0} negative — black (parallel) · End positions ±{1} mm estimate; on the TP4056 the pad names are printed on the board (B+ / B− / OUT+ / OUT−).
tr: yalıtılmış {0} V (+Vo) → MT2 · Uç yerleri ±{1} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−); B0505S'in gövdesinde ad YOK: bacak numarası {2}, {3}, {4}, {5} ({6}) — yan yana iki bacak giriş.
en: isolated {0} V (+Vo) → MT2 · End positions ±{1} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−); the B0505S has NO names on its body: pin numbers {2}, {3}, {4}, {5} ({6}) — the two pins side by side are the input.
tr: Kablo {0}: B0505S {1} (−Vout) → MT2 IN− (−{2} tarafı)
en: Cable {0}: B0505S {1} (−Vout) → MT2 IN− (−{2} side)
tr: kablo · −{0} tarafı (B0505S çıkışı)
en: cable · −{0} side (B0505S output)
tr: yalıtılmış 0V → MT2 eksisi — bu uç −{0} rayı olur, kart GND'ye DEĞMEZ · Uç yerleri ±{1} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−); B0505S'in gövdesinde ad YOK: bacak numarası {2}, {3}, {4}, {5} …
en: isolated 0V → MT2 negative — this end becomes the −{0} rail, it DOES NOT TOUCH board GND · End positions ±{1} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−); the B0505S has NO names on its body: pin numbers {2}, {3}, {4}, {5} …
tr: Kablo {0}: KL + vidası → kart A C34 teli ({1} V +)
en: Cable {0}: KL + screw → board A C34 wire ({1} V +)
tr: klemens → kart {0} V + (T_24P) · Uç yerleri ±{1} mm tahmin.
en: terminal → board {0} V + (T_24P) · End positions ±{1} mm estimate.
tr: Kablo {0}: KL + vidası → GÜÇ LED'i uzun bacak ({1} kΩ ile)
en: Cable {0}: KL + screw → «GÜÇ» LED long leg (via {1} kΩ)
tr: {0} kΩ (R060) LED'in uzun bacağına lehimli, makaronlu · Uç yerleri ±{1} mm tahmin.
en: {0} kΩ (R060) soldered to the LED's long leg, heat-shrunk · End positions ±{1} mm estimate.
tr: Kablo {0}: KL − vidası → kart A C36 teli (−{1})
en: Cable {0}: KL − screw → board A C36 wire (−{1})
tr: klemens → kart {0} V − (T_24N = −{1} rayı) · Uç yerleri ±{2} mm tahmin.
en: terminal → board {0} V − (T_24N = −{1} rail) · End positions ±{2} mm estimate.
tr: Kablo {0}: GÜÇ LED'i kısa bacak → COM jakının lehim kulağı
en: Cable {0}: «GÜÇ» LED short leg → solder lug of the COM jack
tr: katot → COM jakının lehim kulağı = kart GND (J5'ten önce de lamba yanar) · Uç yerleri ±{0} mm tahmin.
en: cathode → solder lug of the COM jack = board GND (the lamp lights even before J5) · End positions ±{0} mm estimate.
tr: Kablo {0}: MT1 OUT+ → ESP32 5V pini
en: Cable {0}: MT1 OUT+ → ESP32 5V pin
tr: {0} V → devkit 5V/VIN pini (J5 kablosunun 5V teliyle çatal) · Uç yerleri ±{1} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: {0} V → devkit 5V/VIN pin (Y-splice with the 5V wire of the J5 cable) · End positions ±{1} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: Kablo {0}: MT1 OUT+ → F0 klips {1}
en: Cable {0}: MT1 OUT+ → F0 clip {1}
tr: {0} V barası → F0 (kutu içi sigorta, {1} A) · Uç yerleri ±{2} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: {0} V bus → F0 (fuse inside the enclosure, {1} A) · End positions ±{2} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: Kablo {0}: MT1 OUT− → ESP32 GND pini (ikinci)
en: Cable {0}: MT1 OUT− → ESP32 GND pin (the second one)
tr: = kart GND (ESP32 üzerinden). Paket eksisi bu düğümde. · Uç yerleri ±{0} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: = board GND (via the ESP32). The pack negative is on this node. · End positions ±{0} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: B0505S GND — kart GND tarafı · Uç yerleri ±{0} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−); B0505S'in gövdesinde ad YOK: bacak numarası {1}, {2}, {3}, {4} ({5}) — yan yana iki bacak giriş.
en: B0505S GND — board GND side · End positions ±{0} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−); the B0505S has NO names on its body: pin numbers {1}, {2}, {3}, {4} ({5}) — the two pins side by side are the input.
tr: Kablo {0}: MT2 OUT+ → KL + vidası
en: Cable {0}: MT2 OUT+ → KL + screw
tr: {0} V → klemens + · Uç yerleri ±{1} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: {0} V → terminal + · End positions ±{1} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: Kablo {0}: MT2 OUT− → KL − vidası
en: Cable {0}: MT2 OUT− → KL − screw
tr: {0} V eksisi → klemens − · Uç yerleri ±{1} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: {0} V negative → terminal − · End positions ±{1} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: Kablo {0}: PİL anahtarı dış bacak (AÇ'ta ortayla öten) → MT1 IN+
en: Cable {0}: «PİL» switch outer pin (beeps with the middle one when ON) → MT1 IN+
tr: anahtar paket tarafında: kapalıyken MT1 hiç çekmez · Uç yerleri ±{0} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−).
en: switch on the pack side: when off, MT1 draws nothing · End positions ±{0} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−).
tr: Kablo {0}: TP4056 OUT+ teli → PİL anahtarı orta bacak
en: Cable {0}: TP4056 OUT+ wire → «PİL» switch middle pin
tr: korumalı çıkış (B+ değil!) → PİL anahtarı · Uç yerleri ±{0} mm tahmin; TP4056'da ped adları kartın üstünde (B+ / B− / OUT+ / OUT−).
en: protected output (not B+!) → «PİL» switch · End positions ±{0} mm estimate; on the TP4056 the pad names are printed on the board (B+ / B− / OUT+ / OUT−).
tr: TP4056'nın kendi teli: pedden {0} cm gerekir — tel ~{1} cm, {2} cm ek (lehim + makaron)
en: the TP4056's own wire: {0} cm needed from the pad — wire ~{1} cm, {2} cm splice (solder + heat-shrink)
tr: Kablo {0}: TP4056 OUT− teli → MT1 IN−
en: Cable {0}: TP4056 OUT− wire → MT1 IN−
tr: eksi doğrudan · Uç yerleri ±{0} mm tahmin; MT3608'de ped adı modülün üstünde yazılı (IN+ / IN− / OUT+ / OUT−); TP4056'da ped adları kartın üstünde (B+ / B− / OUT+ / OUT−).
en: negative, direct · End positions ±{0} mm estimate; on the MT3608 the pad names are printed on the module (IN+ / IN− / OUT+ / OUT−); on the TP4056 the pad names are printed on the board (B+ / B− / OUT+ / OUT−).
tr: Kapak cıvatası — M3x12
en: Lid bolt — M3x12
tr: bağlantı elemanı
en: fastener
tr: M3x12 + somun + pul
en: M3x12 + nut + washer
tr: Ø{0} mm, yan duvardan kapak rayına
en: Ø{0} mm, through the side wall into the lid rail
tr: {0} · Kapak cıvata deliklerini aç (kutu boşken)
en: {0} · Drill the lid bolt holes (while the enclosure is empty)
tr: {0} · Kapağı tak ve cıvatala
en: {0} · Fit the lid and bolt it down
tr: Taban sırası {0}
en: Base row {0}
tr: Taban rayı
en: Base rail
tr: Dış kat ön {0}
en: Outer layer front {0}
tr: Dış kat arka {0}
en: Outer layer back {0}
tr: Dış kat sol {0}
en: Outer layer left {0}
tr: Dış kat sağ {0}
en: Outer layer right {0}
tr: İç kat ön
en: Inner layer front
tr: İç kat arka
en: Inner layer back
tr: İç kat sol
en: Inner layer left
tr: İç kat sağ
en: Inner layer right
tr: Köşe direği {0}
en: Corner post {0}
tr: delik YÜK {0}
en: hole «YÜK» {0}
tr: delik YÜK {0} (iç kat)
en: hole «YÜK» {0} (inner layer)
tr: delik PİL {0}
en: hole «PİL» {0}
tr: delik PİL {0} (iç kat)
en: hole «PİL» {0} (inner layer)
tr: delik V
en: hole V
tr: delik V (iç kat)
en: hole V (inner layer)
tr: delik COM
en: hole COM
tr: delik COM (iç kat)
en: hole COM (inner layer)
tr: delik SKOP
en: hole «SKOP»
tr: delik SKOP (iç kat)
en: hole «SKOP» (inner layer)
tr: delik AÇ / KAPA
en: hole «AÇ / KAPA»
tr: delik AÇ / KAPA (iç kat)
en: hole «AÇ / KAPA» (inner layer)
tr: delik CAL
en: hole CAL
tr: delik CAL (iç kat)
en: hole CAL (inner layer)
tr: delik GÜÇ
en: hole «GÜÇ»
tr: delik GÜÇ (iç kat)
en: hole «GÜÇ» (inner layer)
tr: delik HV ⚡
en: hole HV ⚡
tr: delik HV ⚡ (iç kat)
en: hole HV ⚡ (inner layer)
tr: delik ŞARJ
en: hole «ŞARJ»
tr: delik ≋
en: hole ≋
tr: delik ≋ (iç kat)
en: hole ≋ (inner layer)
tr: delik USB
en: hole USB
tr: YÜK {0} (iç)
en: «YÜK» {0} (inner)
tr: PİL {0} (iç)
en: «PİL» {0} (inner)
tr: V (iç)
en: V (inner)
tr: COM (iç)
en: COM (inner)
tr: SKOP (iç)
en: «SKOP» (inner)
tr: AÇ / KAPA (iç)
en: «AÇ / KAPA» (inner)
tr: CAL (iç)
en: CAL (inner)
tr: GÜÇ (iç)
en: «GÜÇ» (inner)
tr: HV ⚡ (iç)
en: HV ⚡ (inner)
tr: ≋ (iç)
en: ≋ (inner)
tr: ESP32-altlık1a
en: ESP32-spacer1a
tr: ESP32-altlık1b
en: ESP32-spacer1b
tr: ESP32-altlık2a
en: ESP32-spacer2a
tr: ESP32-altlık2b
en: ESP32-spacer2b
tr: ESP32-ray-sol-ön
en: ESP32-rail-left-front
tr: ESP32-ray-sağ-arka
en: ESP32-rail-right-back
tr: ESP32-ray-sağ-ön
en: ESP32-rail-right-front
tr: ESP32-takoz-sağ
en: ESP32-block-right
tr: RS-altlık1a
en: RS-spacer1a
tr: RS-altlık1b
en: RS-spacer1b
tr: Q1-köşebent
en: Q1-bracket
tr: ESP32 (anten)
en: ESP32 (antenna)
tr: Kapak sırası {0}
en: Lid row {0}
tr: Kapak rayı
en: Lid rail
tr: Kayıt
en: Record
tr: <span class='kotu'>kayıtta yok</span>
en: <span class='kotu'>not in the stock records</span>
tr: kayıtta yok
en: not in the stock records
# tablo basliklari ve tek kelimelik etiketler
tr: Delik
en: Hole
tr: KTS102 On/Off {0} Ayak Toggle Anahtar
en: KTS102 on/off {0}-pin toggle switch
tr: <b>SKOP</b>
en: <b>«SKOP»</b>
tr: <b>Kontrol</b>
en: <b>Check</b>
tr: Nerede
en: Where
tr: Ne
en: What
tr: Not
en: Note
tr: Kontrol
en: Check
tr: Uzunluk
en: Length
tr: Adet
en: Qty
tr: Nereden
en: From
tr: Kart {0} × {1} mm (±{2}).
en: Board {0} × {1} mm (±{2}).
tr: Taban
en: Base
tr: SKOP
en: «SKOP»
tr: Duvar
en: Wall
tr: Kapak
en: Lid
tr: Kural
en: Rule
tr: Stokta
en: In stock
tr: Stok
en: Stock
tr: Nereye
en: To
tr: Beklenen
en: Expected
tr: No
en: No.
tr: Yol
en: Route
tr: Kesim
en: Cut
tr: Kesit
en: Cross-section
tr: <b>B0505S {0} (+Vin)</b>
en: =
tr: <span class='kucuk'>F0 → B0505S Vin</span>
en: =
tr: <b>B0505S {0} (−Vin)</b>
en: =
tr: <b>B0505S {0} (+Vout)</b>
en: =
tr: <b>B0505S {0} (−Vout)</b>
en: =
tr: <span class='ano'>{0}</span> <b>Kalibrasyon</b>
en: <span class='ano'>{0}</span> <b>Calibration</b>
tr: Komut
en: Command
tr: <b>Gerilim, ≤ ±{0} V</b>
en: <b>Voltage, ≤ ±{0} V</b>
tr: <b>Gerilim, ±{0} V</b>
en: <b>Voltage, ±{0} V</b>
tr: <b>Osiloskop, -{0} … +{1} V</b>
en: <b>Oscilloscope, -{0} … +{1} V</b>
tr: Toplam
en: Total
tr: Pay
en: Share
tr: Kalem
en: Item
tr: Ref
en: =
tr: Panel
en: =
tr: Neden
en: Why
tr: <b>Kart A</b>
en: <b>Board A</b>
tr: B-ayak1 ↔ ESP32
en: B-foot1 ↔ ESP32
tr: B-ayak2 ↔ RS
en: B-foot2 ↔ RS
tr: A-ayak4 ↔ B
en: A-foot4 ↔ B
tr: A-ayak2 ↔ ESP32
en: A-foot2 ↔ ESP32
tr: Duvarlar
en: Walls
tr: Kalibrasyon
en: Calibration
tr: Kat
en: Layers
tr: Konum
en: Position
tr: Tutturma
en: Fixing
tr: Yerden
en: Above floor
tr: Kablo {0}: B0505S {1} (+Vout) → MT2 IN+
en: Cable {0}: B0505S {1} (+Vout) → MT2 IN+
tr: Kablo {0}: MT1 OUT− → B0505S {1} (−Vin)
en: Cable {0}: MT1 OUT− → B0505S {1} (−Vin)
tr: A-ayak1
en: A-foot1
tr: A-ayak2
en: A-foot2
tr: A-ayak3
en: A-foot3
tr: A-ayak4
en: A-foot4
tr: B-ayak1
en: B-foot1
tr: B-ayak2
en: B-foot2
tr: Kablo {0}
en: Cable {0}
tr: <b>KULLANMA</b>
en: <b>DO NOT USE</b>
tr: <b>KALIN KABLO</b>
en: <b>HEAVY CABLE</b>
tr: KAYNAK
en: SOURCE
tr: <b>KABLO</b>
en: <b>CABLE</b>
"""

METIN, CIFT = _oku(SOZLUK)
