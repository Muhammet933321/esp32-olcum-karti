# -*- coding: utf-8 -*-
"""BELGELER/9-pc-uygulamasi.html — PC UYGULAMASI KILAVUZU (alt proje 4'un kullanici yuzu).

belge-uret.py cagirir: `veri()` sayilari/adlari KODDAN okur, `govde(v)` sayfayi kurar,
`denetle(...)` sayfanin kodla ayrismadigini olcer (B9; ozet satiri "N/N kural gecti").

Kaynaklar (elle sayi/ad YOK — hepsi buradan okunur, okunamazsa uretim COKER):
    kopru/pc.py             secenekler (AST: docstring disindaki "--..." dizeleri), onay varsayilani
    kopru/pc_ayar.py        ad, port, veri dizini adi ve alt dizinleri, ayar dosyasi, kart adresi
    kopru/arka_esitle.py    esitleme araligi (varsayilan / en az)
    kopru/imza.py           eslestirme alt komutlari, parola alt siniri, ad siniri, parola istemi
    kopru/pc_bildirim.py    bildirim siniflari, CLI (ayar / durum), yerel sessizlik suresi
    kopru/windows_bildirim.py   kaynak adi (AUMID) ve gorunen ad
    kopru/otomatik-baslat.ps1   kisayol adi, dal agaci (worktree) reddi
    kopru/*.bat             dort cift tiklama dosyasi ve cagirdiklari
    Kopru Baslat.bat        kokteki eski giris (kopru\\PC Baslat.bat'i cagirir); arayuz3/cevrimdisi.html
    arayuz3/ekran/pc_kopru.js + ortak/src/sozluk_pc.js   panelin bildirim bolumu (4H): adi, siniflari
    kod/olcum-karti-a3/     USB komutlari (E?, Ez1, Ez0, Ex<n>, Q?, Qt) ve cihaz siniri

KURAL (kutu.py'deki "plan soru sormadan bitirilebilir" kuraliyla AYNI): kullanici bu sayfayi
KIMSEYE SORMADAN tamamlayabilmeli. Hicbir metin onu "bana sor / soyle"ye yollamaz; desenler
TURKCE yazilir (kutu.py B55n: ASCII "soyle" hicbir seyi yakalamiyordu).
"""
from __future__ import annotations

import ast
import html as _html
import re
from pathlib import Path

DOSYA = "9-pc-uygulamasi.html"
BASLIK = "PC uygulaması"
ALT = "Köprü · bilgisayarda arşiv · Windows bildirimleri — kurmak, başlatmak, kullanmak"

# Kilavuzun anlattigi pc.py secenekleri. Her biri pc.py'nin KODUNDA (docstring disinda)
# bir dize olarak bulunmali; koddaki her secenek de ya burada ya HARIC'te (gerekceli).
SECENEKLER = [
    ("--sessiz", "Arka plan kipi: konsol yok, tarayıcı açılmaz (otomatik başlatma bunu kullanır). "
                 "Çökerse iz <code>arkaplan-hata.txt</code>'ye yazılır"),
    ("--durdur", "Çalışan köprüyü (arka plandakini de) durdurur — <code>Kopruyu Durdur.bat</code> "
                 "bunu çağırır"),
    ("--tarayici-acma", "Köprü açılır ama tarayıcı açılmaz"),
    ("--usb-yok", "Yalnız WiFi: COM portu <b>hiç açılmaz</b>. Köprü açıkken firmware yüklemek, "
                  "tezgah araçlarını ya da Arduino Seri Monitörü'nü kullanmak için"),
    ("--wifi-yok", "Yalnız USB. Kayıt arşivi (eşitleme) bu kipte çalışmaz — kayıt verisi yalnız "
                   "WiFi'den alınır"),
    ("--port", "COM portunu elle verir (ör. <code>--port COM6</code>); verilmezse köprü kartın "
               "USB köprü çipinden (CH343) kendisi bulur"),
    ("--kart-host", "Kartın WiFi adresi (varsayılan <code>{kart_host}</code>). Kartın kendi ağındayken "
                    "<code>--kart-host 192.168.4.1</code>, ya da kartın IP'si"),
    ("--cihaz", "Eşleşmiş cihaz dosyasını elle seçer (iki kart varsa); verilmezse kartın kimliğine "
                "göre bulunur"),
    ("--onaysiz", "Kayıtları diske eşitler ama karta <b>onay göndermez</b> (aşağıda “Onay ne demek”)"),
    ("--esitleme-aralik", "Eşitleme aralığı, saniye (varsayılan {aralik:.0f}, en az {aralik_en_az:.0f})"),
    ("--esitleme-yok", "Arka plan eşitlemesi kapalı (canlı izleme ve komutlar çalışır)"),
    ("--bildirim-yok", "MQTT aboneliği ve Windows bildirimleri kapalı"),
    ("--lan", "Yerel ağdaki telefonlar <code>http://&lt;bilgisayarın IP'si&gt;:{port}</code> adresinden "
              "<b>yalnız izler</b>; tek izinli komut DURDUR (<code>p0</code>)"),
]
# Kodda olup kilavuzda anlatilmayanlar — GEREKCELI. Yeni bir secenek eklenip buraya da
# kilavuza da yazilmazsa B9 kirmizi.
HARIC = {
    "--kayit": "gelistirici araci: kayitli .satir dosyasini canli gibi oynatir (olu tekrar)",
    "--http-port": "yalniz olu tekrar / test; port KOKENIN parcasi, degistirmek panelin bu "
                   "bilgisayardaki ayarlarini ayirir (4A-1) — kullaniciya onerilmez",
    "--yardim": "secenek listesini basar; kilavuz zaten listeliyor",
}

# Bildirim siniflari — pc_bildirim.SINIFLAR ile BIREBIR (fazla/eksik kirmizi).
BILDIRIM = [
    ("kopuk", "Karttan haber yok / Ev interneti koptu",
     "Yalnız <b>kayıt sürerken</b>. Kart yerelde (USB ya da WiFi) hâlâ görünüyorsa “Ev interneti "
     "koptu — kart çalışıyor”. Kart dönünce <b>aynı bildirim</b> “yeniden bağlandı” olur. Kartın "
     "MQTT ayarı yoksa: kayıt sürerken kart {yerel_kopuk:.0f} s susarsa"),
    ("bitti", "Kayıt / pil testi bitti", "Kayıt durdu, planlı süre doldu, pil testi bitti"),
    ("dolu", "Kartın belleği doldu", "Kayıt yer kalmadığı için durdu"),
    ("esik", "Eşik aşıldı", "Kartta kurulu eşik"),
    ("yeniden_basladi", "Kart yeniden başladı",
     "Kayıt kesildi ve sürüyor, ya da kesildi — son haberin saatiyle"),
    ("kacirilan", "N olay kaçırıldı", "Köprü kapalıyken ya da bağlantı yokken kaçan olayların sayısı"),
    ("deneme", "Deneme bildirimi", "USB'den <code>Qt</code> gönderilince — yolun çalıştığını sınamak için"),
]

# Kullaniciyi bana yollayan kalip — kutu.py'deki SORAN ile ayni aile (+ "claude").
SORAN = (r"\bsöyle\b", r"\bbana (sor|söyle|yaz|bildir)", r"\bsorarsın\b",
         r"\bbana danış", r"\bbenimle\b", r"\bclaude")
IZINLI_IP = {"127.0.0.1", "192.168.4.1"}


def _kucuk(s: str) -> str:
    """Turkce kucuk harf: 'İ'.lower() 'i̇' verir (kutu.py ile ayni)."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def duz_metin(html: str) -> str:
    """Etiketsiz, varliklari cozulmus metin (tarama icin)."""
    govde = re.sub(r"<(style|script)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return _html.unescape(re.sub(r"<[^>]+>", " ", govde))


def _oku(kok: Path, yol: str) -> str:
    return (kok / yol).read_text(encoding="utf-8", errors="replace")


def _bul(desen: str, metin: str, kaynak: str, grup: int = 1, bayrak=re.M) -> str:
    m = re.search(desen, metin, bayrak)
    if not m:
        raise RuntimeError(f"belge_pc: {kaynak} icinde bulunamadi: {desen}")
    return m.group(grup)


def kod_secenekleri(pc_kaynak: str) -> set[str]:
    """pc.py'nin KODUNDAKI "--..." dizeleri (modul ve fonksiyon docstring'leri haric)."""
    agac = ast.parse(pc_kaynak)
    docs = set()
    for d in [agac] + [n for n in ast.walk(agac)
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]:
        if d.body and isinstance(d.body[0], ast.Expr) and isinstance(
                getattr(d.body[0], "value", None), ast.Constant):
            docs.add(id(d.body[0].value))
    return {n.value for n in ast.walk(agac)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs
            and re.fullmatch(r"--[a-z][a-z-]*", n.value)}


def veri(kok: Path) -> dict:
    pc = _oku(kok, "kopru/pc.py")
    pa = _oku(kok, "kopru/pc_ayar.py")
    ae = _oku(kok, "kopru/arka_esitle.py")
    im = _oku(kok, "kopru/imza.py")
    pb = _oku(kok, "kopru/pc_bildirim.py")
    wb = _oku(kok, "kopru/windows_bildirim.py")
    ps = _oku(kok, "kopru/otomatik-baslat.ps1")
    ino = _oku(kok, "kod/olcum-karti-a3/olcum-karti-a3.ino")
    gh = _oku(kok, "kod/olcum-karti-a3/guvenlik.h")
    sp = _oku(kok, "ortak/src/sozluk_pc.js")
    so = _oku(kok, "ortak/src/sozluk.js")
    pk = _oku(kok, "arayuz3/ekran/pc_kopru.js")

    def _tr(anahtar: str, kaynak: str, ad_: str) -> str:
        """Panel sozlugundeki Turkce metin (kilavuz paneldeki adi AYNEN soylesin)."""
        return _bul(r'"' + re.escape(anahtar) + r'":\s*S\("([^"]+)"', kaynak, ad_)

    ad =_bul(r'^AD\s*=\s*"([^"]+)"', pa, "pc_ayar.py")
    port = int(_bul(r"^PORT\s*=\s*(\d+)", pa, "pc_ayar.py"))
    v = {
        "ad": ad, "port": port, "adres": f"http://{ad}:{port}",
        "kart_host": _bul(r'^KART_HOST\s*=\s*"([^"]+)"', pa, "pc_ayar.py"),
        "veri_ad": _bul(r'taban\s*/\s*"([^"]+)"', pa, "pc_ayar.py"),
        "veri_ortam": _bul(r'os\.environ\.get\("(OLCUM_PC_DIZIN)"\)', pa, "pc_ayar.py"),
        "ayar_ad": _bul(r'^AYAR\s*=\s*"([^"]+)"', pa, "pc_ayar.py"),
        "alt": re.findall(r'veri_dizini\(\)\s*/\s*"([a-z]+)"', pa),
        "bildirim_alt": _bul(r'dizin\s*/\s*"([a-z]+)"\s*/\s*"son\.json"', pc, "pc.py"),
        "aralik": float(_bul(r"^ARALIK_SN\s*=\s*([0-9.]+)", ae, "arka_esitle.py")),
        "aralik_en_az": float(_bul(r"^ARALIK_EN_AZ\s*=\s*([0-9.]+)", ae, "arka_esitle.py")),
        "onay_varsayilan": _bul(r'ayar\.get\("esitleme_onay",\s*(True|False)\)', pc, "pc.py") == "True",
        "parola_en_az": int(_bul(r"^PAROLA_EN_AZ\s*=\s*(\d+)", im, "imza.py")),
        "ad_azami": int(_bul(r"^AD_AZAMI\s*=\s*(\d+)", im, "imza.py")),
        "parola_istemi": _bul(r'getpass\.getpass\("([^"]+)"\)', im, "imza.py"),
        "cihaz_azami": int(_bul(r"#define GUV_CIHAZ_AZAMI\s+(\d+)", gh, "guvenlik.h")),
        "siniflar": tuple(re.findall(r'"([a-z_]+)"',
                                     _bul(r"^SINIFLAR\s*=\s*\(([^)]*)\)", pb, "pc_bildirim.py"))),
        "yerel_kopuk": float(_bul(r"^YEREL_KOPUK_SN\s*=\s*([0-9.]+)", pb, "pc_bildirim.py")),
        "aumid": _bul(r'^AUMID\s*=\s*"([^"]+)"', wb, "windows_bildirim.py"),
        "gorunen_ad": _bul(r'^GORUNEN_AD\s*=\s*"([^"]+)"', wb, "windows_bildirim.py"),
        "aumid_anahtar": _bul(r'rf"(Software\\Classes\\AppUserModelId)\\\{AUMID\}"', wb,
                              "windows_bildirim.py"),
        "kisayol": _bul(r"^\$ad\s*=\s*'([^']+)'", ps, "otomatik-baslat.ps1"),
        "kod_secenek": kod_secenekleri(pc),
        "e_yardim": _bul(r'F\("(! E: E\? liste[^"]*)"\)', ino, "olcum-karti-a3.ino"),
        "q_yardim": _bul(r'F\("(\s*Q\? bildirim[^"]*)"\)', ino, "olcum-karti-a3.ino"),
        # 4H: panelde Ayarlar > Gelismis > "Bildirimler (bu bilgisayar)" (ekran/pc_kopru.js)
        "panel_gelismis": _tr("ay.b_gelismis", so, "sozluk.js"),
        "panel_bolum": _tr("pc.bl_baslik", sp, "sozluk_pc.js"),
        "panel_dil": _tr("pc.bl_dil", sp, "sozluk_pc.js"),
        "panel_siniflar": tuple(re.findall(r"'([a-z_]+)'", _bul(
            r"BILDIRIM_SINIFLARI\s*=\s*Object\.freeze\(\[([^\]]*)\]", pk, "pc_kopru.js"))),
        "panel_sinif_ad": {s: _tr(f"pc.bl_s_{s}", sp, "sozluk_pc.js")
                           for s in re.findall(r"'([a-z_]+)'", _bul(
                               r"BILDIRIM_SINIFLARI\s*=\s*Object\.freeze\(\[([^\]]*)\]", pk,
                               "pc_kopru.js"))},
    }
    return v


# ═══════════════════════════════════════════════════════════ sayfa

def _secenek_tablosu(v: dict) -> str:
    satir = "".join(
        f"<tr><td><code>{s}</code></td><td>{a.format(**v)}</td></tr>" for s, a in SECENEKLER)
    return f"<table><tr><th>Seçenek</th><th>Ne yapar</th></tr>{satir}</table>"


def _bildirim_tablosu(v: dict) -> str:
    satir = "".join(
        f"<tr><td><b>{b}</b></td><td>{a.format(**v)}</td>"
        f"<td>{_html.escape(v['panel_sinif_ad'].get(s, '—'))}</td><td><code>{s}</code></td></tr>"
        for s, b, a in BILDIRIM)
    return ("<table><tr><th>Bildirim</th><th>Ne zaman</th><th>Paneldeki kutu</th>"
            f"<th>Komut satırı adı</th></tr>{satir}</table>")


def govde(v: dict) -> str:
    vd = f"%LOCALAPPDATA%\\{v['veri_ad']}"
    cihaz, arsiv, satir = "cihaz", "arsiv", "satir"
    for a in (cihaz, arsiv, satir):
        if a not in v["alt"]:
            raise RuntimeError(f"belge_pc: pc_ayar.py'de '{a}' alt dizini yok: {v['alt']}")
    onay = "AÇIK" if v["onay_varsayilan"] else "KAPALI"
    return f"""
<div class="kpi">
  <div><span>Panel adresi</span><b style="font-size:17px">{v['ad']}:{v['port']}</b></div>
  <div><span>Kayıt eşitleme</span><b>{v['aralik']:.0f} s'de bir</b></div>
  <div><span>Karta onay</span><b>varsayılan {onay.lower()}</b></div>
  <div><span>Veri klasörü</span><b style="font-size:17px">{v['veri_ad']}</b></div>
</div>

<p><b>PC uygulaması</b>, kartla bu bilgisayar arasında duran tek bir programdır
(<code>kopru/pc.py</code>; “köprü”). Üç iş yapar:</p>
<table>
<tr><th>İş</th><th>Ne demek</th></tr>
<tr><td><b>Köprü</b></td><td>Kartın panelini bu bilgisayarda <code>{v['adres']}</code>
    adresinden açar. Canlı ölçüm ve komutlar kart <b>USB'deyse USB'den</b>, değilse
    <b>WiFi'den</b> gider. Panel, kartın kendi sunduğu panelle aynıdır</td></tr>
<tr><td><b>Arşiv</b></td><td>Kartın kayıtlarını <b>WiFi'den</b> bu bilgisayarın diskine
    kopyalar — her bağlanışta ve {v['aralik']:.0f} saniyede bir. Panelin <b>Kayıtlar</b>
    ekranı bu kopyayı gösterir</td></tr>
<tr><td><b>Bildirim</b></td><td>Kart internete bildirim yolluyorsa (MQTT) onları dinler ve
    <b>Windows bildirimi</b> olarak gösterir — tarayıcı kapalıyken de</td></tr>
</table>
<div class="ok"><b>Asıl kayıt kartta.</b> Bilgisayar yalnız bir kopya tutar. Köprü kapalıyken
de kart ölçer ve kaydeder; köprü açılınca eksikleri kendisi çeker.</div>

<h2>1 · İlk kurulum — bu bilgisayarı karta bir kez tanıtmak</h2>
<p>Köprünün karta WiFi'den konuşabilmesi için bu bilgisayar kartla <b>eşleşmiş</b> olmalı.
Bu <b>bir kez</b> yapılır; anahtar bu bilgisayarda, Windows hesabınıza bağlı şifreli
saklanır.</p>
<table>
<tr><th>Gerekenler</th><td>Python kurulu (<code>python</code> ya da <code>py</code>) ·
    kart ev ağında ve tarayıcıda <code>http://{v['kart_host']}</code> açılıyor · kartın
    <b>web parolası</b> (en az {v['parola_en_az']} karakter)</td></tr>
</table>

<h3>Adım 0 — zaten eşleşmiş mi?</h3>
<p>Dosya Gezgini'nin adres çubuğuna <code>{vd}\\{cihaz}</code> yazıp Enter'a basın. İçinde
16 harf/rakamlık adı olan bir <code>.json</code> dosyası varsa bu bilgisayar <b>zaten
eşleşmiş</b>: Adım 4'teki denetimi yapıp 2. bölüme geçin. Klasör yoksa ya da boşsa devam
edin.</p>

<h3>Adım 1 — köprü açıksa durdurun</h3>
<p><code>projeler\\olcum-karti\\kopru\\Kopruyu Durdur.bat</code> dosyasına çift tıklayın.
“çalışan köprü yok” derse sorun yok. (Eşleştirme aracı ile köprü aynı anahtar dosyasını
kullanır; ikisi aynı anda çalışırsa kart istekleri tekrar sanıp reddedebilir.)</p>

<h3>Adım 2 — komutu çalıştırın</h3>
<p>Dosya Gezgini'nde <code>projeler\\olcum-karti</code> klasörünü açın, adres çubuğuna
<code>cmd</code> yazıp Enter'a basın. Açılan pencereye:</p>
<pre>python kopru/imza.py esles --host {v['kart_host']} --ad PC-kopru</pre>
<p><code>--ad</code> bu bilgisayarın kartın listesindeki adıdır (en çok {v['ad_azami']} bayt,
istediğinizi yazın). <code>python</code> bulunamazsa aynı komutu <code>py</code> ile yazın.
Kart kendi ağındaysa (ev ağına bağlı değilse) bilgisayarı kartın ağına bağlayıp
<code>--host 192.168.4.1</code> yazın.</p>

<h3>Adım 3 — parola sorusu</h3>
<p>Ekranda şu soru çıkar:</p>
<pre>{_html.escape(v['parola_istemi'])}</pre>
<p>Kartın <b>web parolasını</b> yazıp Enter'a basın. Yazarken ekranda <b>hiçbir şey
görünmez</b> — bu normal, yazdıklarınız gidiyor. Parola ağa çıkmaz ve hiçbir yere
kaydedilmez.</p>

<div class="no"><b>Web parolası ≠ WiFi parolası.</b> Kartta üç ayrı parola var; burada
istenen <b>yalnız web parolası</b>:
<table>
<tr><th>Parola</th><th>Ne için</th><th>Nasıl kurulur</th></tr>
<tr><td><b>Web parolası</b> ✔</td><td>Kartın panelinde komut vermek ve eşleştirmek. En az
    {v['parola_en_az']} karakter</td><td>USB'den <code>Ns&lt;parola&gt;</code></td></tr>
<tr><td>WiFi parolası</td><td>Kartın <b>ev ağınıza</b> bağlanması (modeminizin parolası)</td>
    <td>USB'den <code>Np&lt;parola&gt;</code></td></tr>
<tr><td>AP parolası</td><td>Telefonun <b>kartın kendi ağına</b> bağlanması</td>
    <td>Kart kendisi üretir</td></tr>
</table>
PC köprüsünün <b>kendi parolası yoktur</b>: <code>{v['adres']}</code> hiçbir zaman parola
sormaz.</div>

<p><b>Başarılı olursa</b> son satır şöyledir (sayı ve klasör sizde farklı):</p>
<pre>eslesti: cihaz 3 (PC-kopru) -&gt; ...\\{v['veri_ad']}\\{cihaz}\\&lt;kart kimliği&gt;.json</pre>
<p>Hata alırsanız aşağıdaki <a href="#sorun">Sorun giderme</a> tablosuna bakın.</p>

<h3>Adım 4 — kartın listesinde görün</h3>
<pre>python kopru/imza.py liste --host {v['kart_host']}</pre>
<p>Kartın eşleşmiş cihazları yazılır (<code>"ad":"PC-kopru"</code> gibi). Verdiğiniz ad
listede varsa kurulum bitti. Kart en çok <b>{v['cihaz_azami']}</b> cihaz tutar; eski,
kullanmadığınız bir kayıt (ör. aynı bilgisayarın önceki eşleşmesi) varsa
<code>python kopru/imza.py sil --host {v['kart_host']} --n &lt;numara&gt;</code> ile silin —
kendi numaranızı (eşleştirme çıktısındaki <code>cihaz N</code>) silmeyin.</p>

<h2>2 · Başlatmak</h2>
<p><code>projeler\\olcum-karti\\kopru\\PC Baslat.bat</code> dosyasına <b>çift tıklayın</b>.
Bir konsol penceresi açılır, birkaç saniye sonra tarayıcıda panel gelir:
<b><code>{v['adres']}</code></b>.</p>
<table>
<tr><th>Konsolda</th><td><code>Kopru acildi — kart: …</code>, panel adresi, kayıt arşivinin
    klasörü ve bildirim durumu yazar. Pencere açık kaldıkça köprü çalışır</td></tr>
<tr><th>Kart USB'de</th><td>Kartın <b>COM yazan</b> USB soketini kullanın; köprü kartı
    kendisi bulur. Kart takılı değilse WiFi'den bağlanır, takılınca USB'ye geçer</td></tr>
<tr><th>Zaten çalışıyorsa</th><td>İkinci kopya açılmaz; yalnız tarayıcı açılır</td></tr>
<tr><th>Adres</th><td>Yalnız bu bilgisayardan açılır. Port {v['port']} sabittir; başka bir
    program tutuyorsa köprü açılmaz ve bunu yazar</td></tr>
</table>
<p class="kucuk">Kökteki eski <code>Kopru Baslat.bat</code> da aynı programı açar.</p>

<h3>Uygulama olarak kurmak (Edge)</h3>
<p>Panel açıkken Edge'in adres çubuğunun sağındaki <b>“Uygulamayı yükle”</b> simgesine ya da
<b>⋯ menüsü → Uygulamalar → Bu siteyi uygulama olarak yükle</b>'ye tıklayın. Panel kendi
penceresinde, Başlat menüsünde ve görev çubuğunda simgesiyle açılır. Köprü kapalıyken bu
pencere <b>“Köprü çalışmıyor”</b> sayfasını gösterir ve köprü açılınca kendiliğinden panele
döner.</p>

<h2>3 · Günlük kullanım</h2>
<table>
<tr><th>Panelde</th><th>Köprüdeyken</th></tr>
<tr><td><b>Canlı</b></td><td>Ölçüm ve komutlar; kart USB'deyse USB'den, değilse WiFi'den</td></tr>
<tr><td><b>Kayıtlar</b></td><td>Liste <b>bu bilgisayardaki arşivden</b> gelir (“bu PC'de
    (köprü arşivi)”). Grafik, dışa aktarma, rapor ve Karşılaştırma aynen çalışır. Panel bu
    arşive yazmaz ve silmez</td></tr>
<tr><td><b>Pil testi</b></td><td>Eğri kartın WiFi'sinden gelir (köprü karta WiFi'den
    ulaşamıyorsa yalnız anlık durum)</td></tr>
<tr><td><b>Ayarlar → Kalibrasyon geçmişi</b></td><td>Karttan; kart ulaşılamazsa bu
    bilgisayardaki kopyadan (kaynak satırında yazar)</td></tr>
<tr><td><b>Ayarlar → Depolama</b></td><td>Bu bilgisayardaki arşivin özeti — salt okuma</td></tr>
<tr><td><b>Osiloskop → Eski arşiv</b></td><td>Köprünün eski satır günlüğündeki yakalamalar
    (salt okuma)</td></tr>
<tr><td><b>Ayarlar → Eşleştirme</b></td><td>Köprüde <b>kullanılmaz</b> — köprü 1. bölümdeki
    komutla eşleşir</td></tr>
<tr><td><b>Ayarlar → {v['panel_gelismis']}</b></td><td>“{v['panel_bolum']}” bölümü (4. bölüm)
    ve köprünün sunduğu panelin sürümü — ikisi de yalnız köprüde</td></tr>
</table>

<h3>Eşitleme durum satırı</h3>
<p>Kayıtlar ekranında tek satır:
<i>“Köprü eşitlemesi: son başarılı … · son turda N yeni kayıt · kartın son sırası … · karta
onay açık”</i>. Hata varsa sebebini ve kaç saniye sonra yeniden deneyeceğini yazar. Kart
yalnız USB'deyse (WiFi'de değilse) tur <b>atlanır</b>: kayıt verisi yalnız WiFi'den
alınır.</p>

<div class="uy"><b>Onay ne demek?</b> Köprü kayıtları diske <b>kalıcı olarak yazdıktan
sonra</b> karta “bunlar kopyalandı” der (varsayılan {onay.lower()}). Kartın belleği dolunca
yalnız <b>bir yere kopyalanmış</b> eski kayıtları siler; kopyalanmamış veri asla silinmez.
Yani onay açıkken kart, bu bilgisayara kopyalanan eski kayıtları yer gerektiğinde silebilir
— onlar bu bilgisayarda durur, ama <b>henüz eşitlenmemiş bir telefon</b> onları artık
göremez. İstemiyorsanız onayı kapatın: <code>PC Baslat.bat --onaysiz</code>, ya da kalıcı
olarak <code>{vd}\\{v['ayar_ad']}</code> dosyasına <code>{{"esitleme_onay": false}}</code>
yazın (köprüyü yeniden başlatınca geçerli). Onay kapalıyken (ve başka bir cihaz da onay
vermediyse) kart dolunca kaydı durdurur ve bildirir.</div>

<h2>4 · Bildirimler</h2>
<p>Köprü, kartın internete yolladığı bildirimleri dinler (yalnız dinler, yayın yapmaz) ve
Windows bildirimi gösterir. Kaynak adı <b>“{v['gorunen_ad']}”</b>. Bunun için kartın bildirim
(MQTT) ayarı USB'den yapılmış olmalı; yapılmamışsa yalnız “karttan haber yok” (yerel yol)
çalışır.</p>
{_bildirim_tablosu(v)}
<p>Hepsi varsayılan <b>açık</b>. Açıp kapamanın iki yolu var; ikisi de aynı ayar dosyasına
(<code>{v['ayar_ad']}</code>) yazar ve köprüyü yeniden başlatmak gerekmez.</p>
<table>
<tr><th>Panelden</th><td><b>Ayarlar → {v['panel_gelismis']} → “{v['panel_bolum']}”</b>.
    Bağlantı durumunu (aracıya bağlı mı, kart çevrimiçi mi), son olayı, her bildirimin
    aç/kapa kutusunu ve <b>“{v['panel_dil']}”</b> seçimini gösterir; tıkladığınız an kaydedilir.
    Bölüm yalnız köprünün açtığı panelde (<code>{v['adres']}</code>) görünür — kartın kendi
    sayfasında ve yerel ağdaki başka bir cihazdan açılan panelde yoktur</td></tr>
<tr><th>Komut satırından</th><td><code>0</code> kapalı, <code>1</code> açık:
<pre>python kopru/pc_bildirim.py ayar esik=0 kacirilan=0
python kopru/pc_bildirim.py ayar dil=en</pre>
    Durum (abone mi, son mesaj ne zaman): <code>python kopru/pc_bildirim.py durum</code></td></tr>
</table>
<table>
<tr><th>Deneme</th><td>Köprüyü <code>PC Baslat.bat --usb-yok</code> ile açın, Arduino
    IDE'nin Seri Monitörü'nden (115200) karta <code>Qt</code> gönderin → “Deneme bildirimi”
    gelmeli</td></tr>
<tr><th>Rahatsız Etmeyin</th><td>Açıksa bildirim ekranda belirmez, yalnız Bildirim
    merkezine düşer. Belirmesini istiyorsanız Windows Ayarlar → Sistem → Bildirimler →
    öncelikli bildirimlere <b>“{v['gorunen_ad']}”</b>'nı ekleyin</td></tr>
<tr><th>Kaynak adı kaydı</th><td>İlk bildirimde Windows'a
    <code>HKCU\\{v['aumid_anahtar']}\\{v['aumid']}</code> yazılır (ad + simge; yönetici
    gerekmez). Kaldırmak: <code>reg delete "HKCU\\{v['aumid_anahtar']}\\{v['aumid']}" /f</code>
    — bildirimler açık kaldıkça bir sonraki bildirimde yeniden yazılır</td></tr>
</table>

<h2>5 · Seçenekler</h2>
<p>Seçenek vermek için komut satırından:
<code>"kopru\\PC Baslat.bat" --onaysiz</code> ya da <code>python kopru/pc.py --onaysiz</code>
(<code>projeler\\olcum-karti</code> klasöründe). Köprü zaten çalışıyorsa yeni seçenek
uygulanmaz — önce durdurun.</p>
{_secenek_tablosu(v)}

<h2>6 · Windows açılışında otomatik başlatma</h2>
<table>
<tr><th>Kurmak</th><td><code>projeler\\olcum-karti\\kopru\\Otomatik Baslat Kur.bat</code> —
    Başlangıç klasörüne <code>{v['kisayol']}</code> kısayolu konur. Köprü her oturum
    açılışında <b>arka planda</b> (<code>--sessiz</code>: pencere ve tarayıcı yok)
    başlar</td></tr>
<tr><th>Kaldırmak</th><td><code>Otomatik Baslatmayi Kapat.bat</code> (aynı klasör). O an
    çalışan köprüyü durdurmaz — onu <code>Kopruyu Durdur.bat</code> durdurur</td></tr>
<tr><th>Ayarlar</th><td>Arka plandaki köprüye seçenek verilmez; onay ve aralık için
    <code>{v['ayar_ad']}</code> (<code>"esitleme_onay"</code>,
    <code>"esitleme_aralik_s"</code>)</td></tr>
</table>
<div class="no"><b>Yalnız ana klasörden kurun:</b> <code>projeler\\olcum-karti</code>. Geçici
dal klasörlerinden (<code>olcum-karti-…</code>) kurmayın: o klasör silinince kısayol olmayan
bir dosyayı gösterir ve köprü iz bırakmadan açılmaz. Betik geçici dal klasöründe
çalıştırılırsa zaten reddeder.</div>

<h2>7 · Durdurmak</h2>
<table>
<tr><th>Her durumda</th><td><code>kopru\\Kopruyu Durdur.bat</code> (arka plandakini de
    durdurur)</td></tr>
<tr><th>Pencerede açtıysanız</th><td>Konsol penceresinde <b>Ctrl+C</b></td></tr>
<tr><th>Komut satırından</th><td><code>python kopru/pc.py --durdur</code></td></tr>
</table>
<div class="uy"><b>Görev Yöneticisi'nden <code>pythonw.exe</code> sonlandırmayın:</b> stok
takip programı da aynı adla çalışıyor, yanlışı kapanır.<br>
Köprü kartın COM portunu tutar. <b>Firmware yüklemeden</b>, tezgah araçlarından,
Arduino Seri Monitörü'nden ve <code>imza.py</code>'den önce köprüyü durdurun — ya da köprüyü
<code>--usb-yok</code> ile açın (o zaman portu hiç tutmaz).</div>

<h2 id="sorun">8 · Sorun giderme</h2>
<table>
<tr><th>Ne görüyorsunuz</th><th>Sebep</th><th>Ne yapın</th></tr>
<tr><td><code>{v['port']} portu baska bir program tarafindan kullaniliyor (kopru degil)</code></td>
    <td>Bu bilgisayarda başka bir program {v['port']} portunu tutuyor</td>
    <td>O programı kapatın. Başka porta geçmeyin: panelin bu bilgisayardaki ayarları adrese
    bağlıdır</td></tr>
<tr><td>Bir araç: <code>PC kopru bu portu kullaniyor — kapatin</code></td>
    <td>Köprü kartın COM portunu tutuyor</td>
    <td><code>Kopruyu Durdur.bat</code>, işiniz bitince yeniden <code>PC Baslat.bat</code>;
    ya da köprüyü <code>--usb-yok</code> ile açın</td></tr>
<tr><td><code>kart dogrulanmadi</code> … <code>ESLESMEMIS</code></td>
    <td>Bu bilgisayar bu kartla eşleşmemiş</td><td>1. bölüm</td></tr>
<tr><td><code>kart dogrulanmadi</code> … <code>bu kart o DEGIL</code></td>
    <td><code>{v['kart_host']}</code> adresinde başka bir kart cevap veriyor (iki kart ya da ad
    karışması)</td>
    <td>Doğru kartın IP'siyle açın: <code>--kart-host &lt;IP&gt;</code>; o kartı da
    kullanacaksanız onu da eşleştirin. Kimliği uymayan karta köprü komut göndermez</td></tr>
<tr><td><code>kart imzayi reddetti (HTTP 401)</code></td>
    <td>Bu bilgisayarın kaydı kartta silinmiş</td>
    <td>Köprüyü durdurup 1. bölümü yeniden yapın</td></tr>
<tr><td>Eşleştirmede <code>403 kanit yanlis (parola?)</code></td>
    <td>Parola yanlış — çoğunlukla WiFi parolası yazılmıştır</td>
    <td>Web parolasıyla tekrar deneyin. Her yanlış denemede kartın bekletme süresi iki katına
    çıkar (en çok ~4 dk): <code>429</code> görürseniz bekleyin</td></tr>
<tr><td>Eşleştirmede <code>403 web parolasi yok ya da {v['parola_en_az']} karakterden kisa</code></td>
    <td>Kartta web parolası kurulu değil ya da kısa</td>
    <td>USB'den <code>Ns&lt;en az {v['parola_en_az']} karakter&gt;</code> (Arduino Seri Monitörü,
    115200; köprü durdurulmuşken)</td></tr>
<tr><td>Eşleştirmede <code>409 cihaz listesi dolu</code></td>
    <td>Kartta {v['cihaz_azami']} cihaz kayıtlı</td>
    <td>Kullanmadığınız birini silin (1. bölüm, Adım 4; ya da USB'den <code>Ex&lt;n&gt;</code>)</td></tr>
<tr><td>Web parolasını bilmiyorum</td><td>—</td>
    <td>Parolasız USB eşleştirmesi: köprüyü durdurun, kart USB'de ve WiFi'si açıkken
    <code>python kopru/imza.py esles-usb --ad PC-kopru</code></td></tr>
<tr><td>Kartın panelinde (<code>{v['kart_host']}</code>) parola soruluyor</td>
    <td>O, kartın kendi paneli; kartın <b>web parolasını</b> ister</td>
    <td>Köprünün paneli (<code>{v['adres']}</code>) parola sormaz</td></tr>
<tr><td>Kayıtlar boş, satırda <code>atlandi</code> ya da hata</td>
    <td>Kart WiFi'de değil, eşleşme yok ya da <code>--wifi-yok</code>/<code>--esitleme-yok</code>
    ile açılmış</td>
    <td>Kartın WiFi'sini açın (USB'den <code>N1</code>), eşleşmeyi denetleyin; satırdaki sebep
    hangisi olduğunu yazar</td></tr>
<tr><td>Bildirim gelmiyor</td>
    <td>Kartın bildirim ayarı yok, köprü <code>--bildirim-yok</code> ile açık, o sınıf kapalı ya da
    Rahatsız Etmeyin açık</td>
    <td>Ayarlar → {v['panel_gelismis']} → “{v['panel_bolum']}” (bağlantı durumu, kapalı kutu)
    ya da <code>python kopru/pc_bildirim.py durum</code> (<code>etkin</code>, <code>abone</code>,
    <code>mesaj</code>); sonra 4. bölümdeki deneme. “Karttan haber yok” yalnız kayıt sürerken
    gelir</td></tr>
<tr><td>Telefonda (<code>--lan</code>) komut düğmeleri çalışmıyor</td>
    <td>Yerel ağdan bağlantı <b>salt okuma</b>; yalnız DURDUR geçer</td>
    <td>Telefondan komut için kartın kendi adresine bağlanın (<a href="6-ag.html">Bağlanma</a>)</td></tr>
<tr><td>Panel yerine “Köprü çalışmıyor”</td><td>Köprü kapalı</td>
    <td><code>PC Baslat.bat</code>; sayfa kendiliğinden döner</td></tr>
<tr><td>Arka planda başlamadı</td><td>Çökme izi</td>
    <td><code>{vd}\\arkaplan-hata.txt</code> dosyasının son satırı sebebi yazar;
    <code>PC Baslat.bat</code> ile pencerede açınca aynı hata ekranda görünür</td></tr>
</table>

<h2>9 · Dosyalar nerede, ne silinebilir</h2>
<p>Her şey depo <b>dışında</b>, <code>{vd}\\</code> altında (Dosya Gezgini adres çubuğuna
yazılabilir). Silmeden önce köprüyü durdurun.</p>
<table>
<tr><th>Ne</th><th>İçinde</th><th>Silinirse</th></tr>
<tr><td><code>{cihaz}\\</code></td><td>Eşleşme anahtarı (Windows hesabınıza bağlı şifreli)</td>
    <td><b>Silmeyin.</b> Silinirse yeniden eşleştirmek gerekir; kartta eski kayıt kalır</td></tr>
<tr><td><code>{arsiv}\\</code></td><td>Kartın kayıtlarının kopyası (kart → akış klasörleri)</td>
    <td><b>Dikkat:</b> onay açıkken kart bunların bir kısmını silmiş olabilir — buradaki tek
    kopya olabilir. Gerekmeyen bir akış klasörü silinebilir</td></tr>
<tr><td><code>{satir}\\</code></td><td>Köprünün günlük satır kaydı (canlı ölçüm satırları;
    Osiloskop → Eski arşiv buradan okur)</td>
    <td>Silinebilir; kayıtlar (<code>{arsiv}\\</code>) etkilenmez, Eski arşiv'deki
    yakalamalar gider</td></tr>
<tr><td><code>{v['bildirim_alt']}\\</code></td><td>Şifreli bildirim bilgisi önbelleği</td>
    <td>Güvenli; kart ulaşılabilirken yeniden alınır</td></tr>
<tr><td><code>{v['ayar_ad']}</code></td><td>İsteğe bağlı ayarlar</td>
    <td>Güvenli; varsayılanlar döner (onay {onay.lower()}, {v['aralik']:.0f} s, bütün
    bildirimler açık)</td></tr>
<tr><td><code>arkaplan-hata.txt</code></td><td>Son çökme izi</td><td>Güvenli</td></tr>
</table>
<p class="kucuk">Klasörü taşımak için <code>{v['veri_ortam']}</code> ortam değişkeni.</p>

<h2>10 · Güvenlik notları</h2>
<table>
<tr><th>DURDUR her zaman çalışır</th><td>Pil testini kesen <code>p0</code> parola, imza ya da
    eşleşme istemez; köprüde, telefonda (<code>--lan</code>) ve kartta aynıdır</td></tr>
<tr><th>Parolalar</th><td>Web parolasını yalnız <code>imza.py</code>'nin sorusuna (ekranda
    görünmez) ya da kartın panelindeki Eşleştirme formuna yazın. <b>Komut satırına, bir
    dosyaya, sohbete ya da ekran görüntüsüne asla.</b> Köprü parolayı saklamaz</td></tr>
<tr><th>Yerel ağ</th><td>Köprü varsayılan olarak yalnız bu bilgisayarı dinler;
    <code>--lan</code> açılsa bile telefonlar yalnız izler</td></tr>
<tr><th>E ve Q komutları</th><td>Eşleştirme ve bildirim ayarı yalnız <b>USB seri
    konsolundan</b> değişir; köprü bunları karta asla iletmez</td></tr>
</table>

<h3>İsteğe bağlı: imzayı zorunlu yapmak (<code>Ez1</code>)</h3>
<p>Kart varsayılan olarak imzasız istekleri de (parolalı eski yol) kabul eder
(<code>E?</code> → <code>zorunlu=0</code>). <code>Ez1</code> açılınca
kart <b>yalnız eşleşmiş cihazların</b> isteklerini kabul eder (DURDUR yine serbest).
<b>Zorunlu değil</b>; yalnız kullandığınız bütün cihazlar (bu bilgisayar, telefonlar,
tarayıcılar — Ayarlar → Eşleştirme) eşleştikten sonra mantıklıdır, yoksa eşleşmemiş cihaz
karta erişemez.</p>
<table>
<tr><th>1</th><td><code>Kopruyu Durdur.bat</code> (ya da köprüyü <code>--usb-yok</code> ile açın)</td></tr>
<tr><th>2</th><td>Arduino IDE → Araçlar → Port: kartın COM portu → Seri Monitör, 115200 baud</td></tr>
<tr><th>3</th><td><code>E?</code> gönderin: <code>zorunlu=0</code> ve eşleşmiş cihazların listesi
    yazar — hepsini tanıyor musunuz bakın</td></tr>
<tr><th>4</th><td><code>Ez1</code> gönderin. Geri almak: <code>Ez0</code></td></tr>
<tr><th>5</th><td>Seri Monitör'ü kapatıp köprüyü yeniden başlatın</td></tr>
</table>
"""


# ═══════════════════════════════════════════════════════════ denetim

def denetle(kok: Path, v: dict, sayfa_html: str, menu: list, butun_sayfalar: dict) -> list:
    """(ad, gecti, ayrinti) listesi. Her birinin `KLV:` onekli yalanlayan mutasyonu var
    (uretim/mutasyon.py, adim B9K)."""
    s = []
    metin = duz_metin(sayfa_html)

    # 1) Sayfa gezinme seridinde (index tablosundaki baglantiyi belge-uret.py genel olarak olcuyor).
    s.append(("Kilavuz sayfasi MENU'de (her sayfanin seridinde ve index tablosunda)",
              any(d == DOSYA for d, _a in menu), DOSYA))

    # 2-3) Secenekler iki yonde: belgelenen kodda var, koddaki belgede ya da gerekceli disarida.
    belgeli = {f for f, _a in SECENEKLER}
    yok = sorted(belgeli - v["kod_secenek"])
    s.append(("Belgelenen her pc.py secenegi pc.py'nin KODUNDA (docstring disi) var",
              not yok, f"kodda yok: {yok}" if yok else f"{len(belgeli)} secenek"))
    eksik = sorted(v["kod_secenek"] - belgeli - set(HARIC))
    bayat = sorted(set(HARIC) - v["kod_secenek"])
    s.append(("pc.py'deki her secenek kilavuzda ya da gerekceli HARIC'te; HARIC'te bayat kayit yok",
              not eksik and not bayat, f"belgesiz: {eksik} · bayat HARIC: {bayat}"
              if eksik or bayat else f"{len(v['kod_secenek'])} kod secenegi"))
    # Sayfanin HERHANGI bir yerinde gecen "--secenek" gercekten var (pc.py ya da imza.py) —
    # tabloyu degil serbest metni olcer: "--usb-yok ile acin" gibi tavsiyeler bayatlamasin.
    im_secenek = set(re.findall(r'add_argument\("(--[a-z-]+)"',
                                (kok / "kopru" / "imza.py").read_text(encoding="utf-8", errors="replace")))
    gecen = set(re.findall(r"(?<![\w-])--[a-z][a-z-]*", metin))
    hayali = sorted(gecen - v["kod_secenek"] - im_secenek)
    s.append(("Sayfada gecen her --secenek pc.py ya da imza.py'de gercekten var",
              not hayali, f"olmayan: {hayali}" if hayali else f"{len(gecen)} farkli secenek"))

    # 4) Cift tiklama dosyalari var ve anlatilan seyi cagiriyor.
    kopru = kok / "kopru"
    bat = {
        "PC Baslat.bat": lambda t: "kopru\\pc.py %*" in t and "kopru.py" not in t,
        "Kopruyu Durdur.bat": lambda t: "kopru\\pc.py --durdur" in t,
        "Otomatik Baslat Kur.bat": lambda t: "otomatik-baslat.ps1\" -Kur" in t,
        "Otomatik Baslatmayi Kapat.bat": lambda t: "otomatik-baslat.ps1\" -Kaldir" in t,
    }
    kotu = []
    for ad, kosul in bat.items():
        p = kopru / ad
        if not p.is_file() or not kosul(p.read_text(encoding="utf-8", errors="replace")):
            kotu.append(ad)
        elif ad not in metin:
            kotu.append(ad + " (sayfada yok)")
    s.append(("Dort .bat kopru/'da, dogru komutu cagiriyor ve sayfada adiyla geciyor",
              not kotu, str(kotu) if kotu else "4 dosya"))
    # 4b) Eski girisler de ayni programa yollar: kokteki "Kopru Baslat.bat" (sayfa "ayni programi
    #     acar" diyor) ve koprunun cevrimdisi sayfasi (kullaniciya hangi dosyayi soyluyor).
    pcb = "kopru\\PC Baslat.bat"
    kok_bat = kok / "Kopru Baslat.bat"
    kb = kok_bat.read_text(encoding="utf-8", errors="replace") if kok_bat.is_file() else ""
    cv = (kok / "arayuz3" / "cevrimdisi.html").read_text(encoding="utf-8", errors="replace")
    kotu = [ad for ad, kosul in (
        ("kokteki Kopru Baslat.bat PC Baslat.bat'i cagirmiyor",
         f'"%~dp0{pcb}" %*' in kb and "kopru.py" not in kb),
        ("sayfa kokteki .bat'in ayni programi actigini soylemiyor", "Kopru Baslat.bat" in metin),
        ("cevrimdisi.html PC Baslat.bat'i soylemiyor",
         cv.count(f"<code>{pcb}</code>") == 2 and "<code>Kopru Baslat.bat</code>" not in cv)) if not kosul]
    s.append(("Kokteki Kopru Baslat.bat ve cevrimdisi sayfa da kopru\\PC Baslat.bat'a (pc.py) yollar",
              not kotu, str(kotu) if kotu else "2 dosya"))

    # 5) "Yalniz ana klasorden kurun" iddiasi betikte uygulanıyor.
    ps = (kopru / "otomatik-baslat.ps1").read_text(encoding="utf-8", errors="replace")
    s.append(("Otomatik baslatma betigi gecici dal agacinda (.git DOSYA) kurmayi reddediyor",
              "-PathType Leaf" in ps and "-not $Zorla" in ps and "throw" in ps.split("-PathType Leaf", 1)[1][:200],
              "otomatik-baslat.ps1"))

    # 6) imza.py alt komutlari ve secenekleri (sayfadaki komutlar calisir).
    im = (kopru / "imza.py").read_text(encoding="utf-8", errors="replace")
    gerek = ['add_parser("esles")', 'e.add_argument("--host"', 'e.add_argument("--ad"',
             'add_parser("esles-usb")', 'for ad in ("liste", "sil", "saat")',
             'p.add_argument("--n"']
    yok = [g for g in gerek if g not in im]
    s.append(("Sayfadaki imza.py komutlari (esles/esles-usb/liste/sil, --host --ad --n) argparse'ta",
              not yok, str(yok) if yok else "6 parca"))

    # 7) Parola istemi web/WiFi ayrimini kendisi de soyluyor (kilavuz o istemi aynen gosteriyor).
    ist = v["parola_istemi"].lower()          # ASCII metin: _kucuk "I"yi "ı" yapardi
    s.append(("imza.py parola istemi 'WEB parolasi' + 'WiFi parolasi DEGIL' diyor",
              "web parolasi" in ist and "wifi parolasi degil" in ist, v["parola_istemi"]))

    # 8) Bildirim siniflari = pc_bildirim.SINIFLAR (fazla/eksik yok); CLI'si var.
    belgede = [a for a, _b, _c in BILDIRIM]
    s.append(("Bildirim siniflari pc_bildirim.SINIFLAR ile birebir",
              tuple(belgede) == v["siniflar"], f"belge {belgede} · kod {list(v['siniflar'])}"))
    pb = (kopru / "pc_bildirim.py").read_text(encoding="utf-8", errors="replace")
    s.append(("pc_bildirim.py CLI 'ayar' ve 'durum' alt komutlari var",
              'argv[:1] == ["ayar"]' in pb and 'argv[:1] == ["durum"]' in pb, "pc_bildirim.main"))
    # 8b) 4H: paneldeki bildirim bolumu GERCEKTEN var ve kilavuz onu panelin kendi adiyla anlatiyor.
    ay = (kok / "arayuz3" / "ekran" / "ayarlar.js").read_text(encoding="utf-8", errors="replace")
    ko = (kopru / "kopru.py").read_text(encoding="utf-8", errors="replace")
    yol_panel = f"Ayarlar → {v['panel_gelismis']} → “{v['panel_bolum']}”"
    eksik_p = [ad for ad, kosul in (
        ("pc_kopru.js siniflari = pc_bildirim.SINIFLAR", v["panel_siniflar"] == v["siniflar"]),
        ("ayarlar.js pc_kopru.js'i indiriyor", "import('./pc_kopru.js')" in ay),
        ("kopru.py POST /bildirim/ayar", 'yol == "/bildirim/ayar"' in ko),
        ("sayfada panel yolu", yol_panel in metin),
        ("sayfada CLI yolu", "pc_bildirim.py ayar" in metin)) if not kosul]
    s.append(("Panelin bildirim bolumu (Ayarlar > Gelismis) kodda var ve kilavuz onu adiyla anlatiyor; "
              "komut satiri yolu da duruyor",
              not eksik_p, str(eksik_p) if eksik_p else yol_panel))

    # 9) Sayfadaki USB komutlari kartin kendi yardim satirlarinda var.
    e, q = v["e_yardim"], v["q_yardim"]
    eksik_k = [k for k, kaynak in (("E? liste", e), ("Ez0|1", e), ("Ex<n>", e), ("Q?", q), ("Qt", q))
               if k not in kaynak]
    s.append(("USB komutlari (E?, Ez0/Ez1, Ex<n>, Q?, Qt) kartin yardim satirlarinda",
              not eksik_k, str(eksik_k) if eksik_k else "olcum-karti-a3.ino"))

    # 10) Kimseye sordurmuyor — belge-uret'in urettigi BUTUN sayfalar.
    soran = sorted({ad for ad, h in butun_sayfalar.items()
                    for p in SORAN if re.search(p, _kucuk(duz_metin(h)))})
    s.append(("Hicbir belge kullaniciyi karar/soru icin baskasina yollamiyor (bana sor/soyle/Claude)",
              not soran, f"yollayan: {soran}" if soran else f"{len(butun_sayfalar)} sayfa"))

    # 11) Sir/kisisel iz yok: mutlak yol ve izinli olmayan IP adresi.
    yol = re.findall(r"\b[A-Za-z]:[\\/]", metin)
    ipler = sorted(set(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", metin)) - IZINLI_IP)
    s.append(("Sayfada mutlak yol ve izinli olmayan IP yok",
              not yol and not ipler, f"yol {yol} · ip {ipler}" if yol or ipler else "temiz"))
    return s
