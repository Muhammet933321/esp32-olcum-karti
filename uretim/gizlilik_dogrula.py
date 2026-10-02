# -*- coding: utf-8 -*-
"""Yayinlanan depoda KISISEL IZ kaldi mi — tek komutla tara.

    python gizlilik_dogrula.py        (0 = temiz, 1 = iz var)

🔴 NEDEN VAR (B26, 2026-09-12). Depo herkese acik. Kural
`dogrula3.py`nin icinde bir YORUM olarak yaziliydi — ve yorum kurali
KORUMAZ. Bagimsiz bir gizlilik denetimi HEAD'de 59 mutlak yol buldu:

  * `uretim/b15-arastirma.md`      56 kez  ("**Yer:** <mutlak yol>")
  * `arsiv/*/tam-dogrulama.txt`     2 kez  (ureteç gunlugu)
  * `uretim/netlist{,2,3}.net`      3 kez  (kicad-cli `(source ...)`)

Netlist'lerdeki temizlik VARDI ama ISE YARAMIYORDU: B3'te uygulaniyor,
B9 netlist'i DAHA SONRA yeniden uretiyordu. (Artik `netlist_temizle.py`
her uretim yerinde cagriliyor.)

⚠ GREP BU ORTAMDA GUVENILMEZ. Denetim ajani `grep -i` ile birden fazla
`-e` deseninin COKTUGUNU (`Aborted`, rc=134) ve `2>/dev/null` varsa
SESSIZCE BOS sonuc verdigini bildirdi; kendi taramam da bu yuzden
"temiz" demisti. Bu betik saf Python okur — desen basina tek gecis.

NE ARANIR / NE ARANMAZ
  ARANIR : mutlak Windows yollari (kullanici klasoru ya da proje koku; ters
           VE duz egik cizgili, her surucu harfi),
           koda gomulu parolalar (`..parola = "..."`), e-posta adresleri,
           tam MAC adresleri
  ARANMAZ: `Muhammet933321` (GitHub kullanici adi, zaten aleni),
           LICENSE'taki telif sahibi adi, `192.168.4.1` (ESP32 SoftAP
           evrensel varsayilani), `Path.home()` / `LOCALAPPDATA` gibi
           ortam degiskenli yollar — bunlar kullanici adi tasimaz.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
B = chr(92)

# (ad, derlenmis desen, aciklama)
# 4A: surucu harfinin onunde harf/rakam olmamali ("http://" icindeki "p:/" yol degil).
SURUCU = r"(?<![A-Za-z0-9])[A-Za-z]:"

DESENLER = [
    ("Mutlak Windows yolu (kullanici klasoru)",
     re.compile(SURUCU + re.escape(B) + r"{1,2}[Uu]sers" + re.escape(B),
                re.I),
     "kullanici hesap adini acik eder"),
    ("Mutlak Windows yolu (proje koku)",
     re.compile(SURUCU + re.escape(B) + r"{1,2}[Mm]uhammet" + re.escape(B),
                re.I),
     "diskteki klasor duzenini acik eder; klonlayan icin de ISE YARAMAZ"),
    # 🔴 4A: yukaridaki iki desen yalniz TERS egik cizgiyi ariyordu. Python/JS
    #    yollari cogu zaman surucu + `:/Users/<ad>/...` diye yazilir (Path.as_posix(),
    #    Git Bash ciktisi, kesif notlari) ve HICBIRI yakalanmiyordu.
    ("Mutlak Windows yolu (duz egik cizgi: kullanici / ev / proje koku)",
     re.compile(SURUCU + r"/+(?:Users|home|Documents and Settings|Muhammet)(?:/|\b)",
                re.I),
     "ayni iz, duz egik cizgili yazimla — hesap adini ve klasor duzenini acik eder"),
    ("E-posta adresi",
     re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),
     "commit yazari ayri — bu, DOSYA ICINDEKI adres"),
    ("Tam MAC adresi",
     re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
     "cihaza ozgu kimlik"),
]

# Bilerek gecen, sir OLMAYAN degerler.
BEYAZ = (
    "02:00:00:00",          # sentetik test MAC'i (yerel yonetimli OUI)
    "noreply@anthropic.com",
    "users.noreply.github.com",
)


# ── 4A: koda gomulu parola ───────────────────────────────────────────
# Adi parola/sifre/password ile BITEN bir alana (`x.parola = "..."`,
# `"parola": "..."`, `WEB_PAROLA = '...'`) yazilmis duz metin. `parola_hex`,
# `sifreli` gibi adlar (ozet / sifreli veri) aranmaz.
PAROLA = re.compile(
    r"""(?i)\b\w*(?:parola|sifre|şifre|password|passwd)["']?\s*[:=]\s*[bfr]?"""
    r"""(["'])(?P<d>[^"'\n]{4,})\1""")
# Deneme parolasi oldugu GORULEN degerler: bu sozcuklerden birini iceren,
# 4+ ayni karakter tekrari, ya da sozluk anahtari ("es.parola").
# ⚠ Yeni bir test parolasi yazarken bu sozcuklerden birini kullanin
#   ("sinama-parolasi-12"); kullanicinin gercek parolasi hicbirine uymaz
#   varsayimi BURADA yazili — "kart", "1234" gibi gercek parolada da gecebilecek
#   parcalar bilerek listede YOK.
PAROLA_DENEME = ("sinama", "sınama", "deneme", "test", "ornek", "örnek", "gizli",
                 "dogru", "doğru", "yanlis", "yanlış", "sahte")
PAROLA_TEKRAR = re.compile(r"(.)\1{3,}")
PAROLA_SOZLUK = re.compile(r"^[a-z]{1,6}\.[a-z0-9_.]+$")
# Tek tek bilinen deneme degerleri (desen degil, TAM deger) ve gerekcesi.
PAROLA_BEYAZ = {
    "Ölçüm-kartı1": "ortak/ kripto capraz vektorlerinin belgelenmis proje parolasi "
                    "(ortak_vektor_kripto.PROJE_PAROLA, UTF-8 sinamasi)",
    "p@ss:1": "uretim/avr/ornek_kayit.c MQTT CONNECT paket sinamasi (ozel karakter)",
}
# Uretilmis capraz vektor dosyalari: ureten betikler (taranan .py) zaten
# denetleniyor; RFC 6070/7914 PBKDF2 vektorleri ("password", "passwd") burada.
PAROLA_ATLA = ("ortak/test/vektor/", "uretim/vektor_guvenlik.json")


def parola_deneme_mi(deger: str) -> bool:
    d = deger.lower()
    return (deger in PAROLA_BEYAZ or any(s in d for s in PAROLA_DENEME)
            or bool(PAROLA_TEKRAR.search(deger)) or bool(PAROLA_SOZLUK.match(deger)))


def parola_tara(dosyalar) -> int:
    bulgu = []
    for f in dosyalar:
        if f.startswith(PAROLA_ATLA) or not f.endswith(METIN_UZANTI):
            continue
        p = KOK / f
        if not p.exists():
            continue
        try:
            metin = p.read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        for i, satir in enumerate(metin.splitlines(), 1):
            for m in PAROLA.finditer(satir):
                if not parola_deneme_mi(m.group("d")):
                    # Degeri BASMA: gercek bir parolaysa cikti da sizinti olur.
                    bulgu.append((f, i, m.group(0)[:m.start("d") - m.start()] + "<...>"))
    if bulgu:
        print(f"  [!!] Koda gomulu parola: {len(bulgu)} gecis — gercek parola depoya "
              f"girmez; deneme degeriyse 'sinama'/'deneme' gibi bir sozcuk kullanin")
        for f, i, s in bulgu[:8]:
            print(f"         {f}:{i}  {s}")
    else:
        print("  [OK] Koda gomulu parola: temiz")
    return len(bulgu)


def _gitignore_desenleri() -> list[str]:
    p = KOK / ".gitignore"
    if not p.exists():
        return []
    return [s.strip() for s in p.read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.startswith("#")]


def _yok_sayilir(goreli: str, desenler: list[str]) -> bool:
    """`.gitignore`nin kaba bir esi — yalnizca burada gereken kadar."""
    import fnmatch
    parcalar = goreli.split("/")
    for d in desenler:
        d = d.lstrip("/")
        if d.endswith("/"):                      # klasor deseni
            k = d.rstrip("/").replace("**/", "")
            if any(fnmatch.fnmatch(x, k) for x in parcalar[:-1]) \
               or goreli.startswith(k + "/"):
                return True
        elif "/" in d:                            # yol deseni
            if fnmatch.fnmatch(goreli, d) or fnmatch.fnmatch(goreli, d + "*"):
                return True
        elif fnmatch.fnmatch(parcalar[-1], d):    # dosya adi deseni
            return True
    return False


def takip_edilenler() -> list[str]:
    """`git ls-files`; git yoksa agaci `.gitignore`ye gore yuru.

    ⚠ Fallback SART: `mutasyon.py` projeyi `.git` OLMADAN kopyaliyor.
    Fallback olmasaydi kopyada 0 dosya taranir, "temiz" denir ve bu
    betigin kendi mutasyonu KACARDI — yani denetim kendini sinayamazdi.
    """
    u = subprocess.run(["git", "ls-files"], cwd=KOK,
                       capture_output=True, text=True)
    # ⚠ splitlines(), split() DEGIL: "Kopru Baslat.bat" bosluk iceriyor,
    #   split() onu iki sahte yola bolup dosyayi TARAMADAN geciyordu.
    liste = [x for x in u.stdout.splitlines() if x.strip()]
    if liste:
        return liste
    desenler = _gitignore_desenleri() + [".git/"]
    cikti = []
    for p in KOK.rglob("*"):
        if not p.is_file():
            continue
        g = p.relative_to(KOK).as_posix()
        if not _yok_sayilir(g, desenler):
            cikti.append(g)
    return cikti


# 🔴 B39 — METIN DOSYASINDA KONTROL KARAKTERI = SESSIZCE KOR BIR IDDIA.
#    Bash aracinin heredoc'u `\b`yi GERCEK backspace (0x08) olarak
#    yaziyor. Dosya calisiyor, regex hicbir seyle eslesmiyor, iddia HER
#    ZAMAN geciyor. 2026-09-13'te depoda UC tane bulundu; biri
#    sim3_web.py'nin GOMULU PAROLA denetimiydi ve ILK YAYINDAN BERI kordu.
#    Sekme (0x09), LF (0x0A), CR (0x0D) metinde mesru; gerisi degil.
KONTROL = re.compile("[" + "".join(chr(c) for c in range(0x20)
                                   if c not in (0x09, 0x0A, 0x0D)) + "]")
METIN_UZANTI = (".py", ".js", ".ino", ".h", ".c", ".cpp", ".html", ".css",
                ".md", ".json", ".csv", ".txt", ".net", ".kicad_sch",
                ".kicad_pro", ".yml", ".yaml", ".toml", ".bat", ".ps1",
                ".gitignore")


def kontrol_karakteri_tara(dosyalar) -> int:
    bulgu = []
    for f in dosyalar:
        if not f.endswith(METIN_UZANTI):
            continue
        p = KOK / f
        if not p.exists():
            continue
        try:
            metin = p.read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        for i, satir in enumerate(metin.splitlines(), 1):
            m = KONTROL.search(satir)
            if m:
                bulgu.append((f, i, f"0x{ord(m.group(0)):02X}",
                              satir.strip()[:50].replace(m.group(0), "<?>")))
    if bulgu:
        print(f"  [!!] Metin dosyasinda kontrol karakteri: {len(bulgu)} satir — "
              f"buyuk olasilikla bir kacis dizisi (\\b, \\f...) GERCEK "
              f"karaktere donmus; o satirdaki regex/iddia SESSIZCE KOR")
        for f, i, kod, s in bulgu[:8]:
            print(f"         {f}:{i}  {kod}  {s}")
    else:
        print("  [OK] Metin dosyasinda kontrol karakteri: temiz")
    return len(bulgu)


def main() -> int:
    dosyalar = takip_edilenler()
    print("=" * 78)
    print("  GIZLILIK — yayinlanan depoda kisisel iz var mi?")
    print("=" * 78)
    print(f"  {len(dosyalar)} takip edilen dosya\n")

    toplam = 0
    for ad, desen, neden in DESENLER:
        bulgu: list[tuple[str, int, str]] = []
        for f in dosyalar:
            p = KOK / f
            if not p.exists():
                continue
            try:
                metin = p.read_bytes().decode("utf-8", "replace")
            except OSError:
                continue
            for i, satir in enumerate(metin.splitlines(), 1):
                for m in desen.finditer(satir):
                    if any(b in m.group(0) for b in BEYAZ):
                        continue
                    bulgu.append((f, i, m.group(0)[:60]))
        if bulgu:
            toplam += len(bulgu)
            print(f"  [!!] {ad}: {len(bulgu)} gecis — {neden}")
            for f, i, s in bulgu[:8]:
                print(f"         {f}:{i}  {s}")
            if len(bulgu) > 8:
                print(f"         ... ve {len(bulgu) - 8} tane daha")
        else:
            print(f"  [OK] {ad}: temiz")

    kk = kontrol_karakteri_tara(dosyalar)
    toplam += parola_tara(dosyalar)

    print()
    if kk:
        print(f"  KIRMIZI: {kk} satirda kontrol karakteri — `cat -A` ile bak, "
              f"karakteri kacis dizisiyle degistir.")
    if toplam:
        print(f"  KIRMIZI: {toplam} kisisel iz — yayinlamadan once temizle.")
    if toplam or kk:
        return 1
    print("  Temiz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
