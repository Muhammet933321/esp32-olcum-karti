# -*- coding: utf-8 -*-
"""HIZ (2026-10-03): artimli zincir + paralel mutasyon kosucusu — KENDI testleri.

    python test_zincir_hiz.py            (~65 s)

ZINCIRDE DEGIL (30 s sinirini asiyor; zincire girse HER ZAMAN KOSAR olurdu — kendi
sahte araclarini cagiriyor). Bu dosyaya ya da mutasyon.py / dogrula3.py /
zincir_onbellek.py / zincir_kanca/'ya dokunan her degisiklikten sonra elle kos ve
mutasyonlarini kostur:
    python mutasyon.py --neden HIZ --paralel 4

Iki hizlandirma da "yesil test bir sey kanitlamaz" kuralinin tam ortasina
dokunuyor: artimli zincir yanlislikla bir adimi atlarsa kirmizi bir tasarim
YESIL gorunur; paralel kosucu iscileri birbirine karistirirsa bos bir iddia
"YAKALANDI" gorunur. Bu dosya ikisini de SAHTE, kucuk projelerde sinar —
gercek zincirin 13 dakikasini beklemeden, gercek karta dokunmadan.

A) mutasyon.py --paralel
   A1 sirali (1) ve paralel (3) AYNI YAKALANDI/KACTI/UYGULANAMADI kumesini verir
   A2 her isci kendi TEMP'inde ve kendi LOCALAPPDATA'sinda kosar; arac
      kurulumu (Arduino15) junction ile gorunur
   A3 IKI esanli kosu + dogrula3'un %TEMP% suepurmesi (gecici.kalintilari_sil)
      ayni anda: taban YESIL kalir, sonuclar dogru (ozel TEMP olmasa suepurme
      adimin `spice-*` dizinini silip tabani kirmiziya cevirirdi — A3b bunu
      ozel TEMP'i KAPATARAK gosterir)
   A4 kopyalar + ozel dizinler sonunda silinir; junction HEDEFI silinmez
   A5 Ctrl+C (CTRL_BREAK) -> kopyalar yine silinir
   A6 --neden onek suzgeci; --adim'siz kosu AGIR'i atlar ama --neden atlamaz
   A7 taban kirmiziysa hicbir mutasyon "YAKALANDI" sayilmaz

B) dogrula3.py --artimli (zincir_onbellek.py)
   B1 hicbir sey degismedi -> onbellekten
   B2 adimin ACTIGI dosya degisti -> kosar
   B3 yalniz ALT Python surecinin actigi dosya degisti -> kosar
   B4 arac argumani olan dosya degisti -> kosar (derleyici kurali)
   B5 kurali olmayan aracin okudugu dosya -> adim HER ZAMAN KOSAR
   B6 --tam hepsini kosar
   B7 son tam kosu > 24 sa -> tam kosu
   B8 bozuk onbellek / bozuk kayit -> kosar
   B9 sayim kilidi onbellekten gelen adimlarla da isler; --sayim-kilidi-yaz
      --artimli ile REDDEDILIR
   B10 varligina bakilan yol belirdi / listelenen dizine dosya eklendi -> kosar
   B11 adimin ciktisi silindi -> kosar; kirmizi adim hic saklanmaz
   B12 baska kokteki (mutasyon kopyasi) onbellek kullanilmaz
   B13 oldurulen alt surecin okumasi da kayitli (yaz-gec)
   B14 TAM_TETIK dosyasi degisti -> tam kosu
   B15 iz ortamini dusuren Python alt sureci -> HER ZAMAN KOSAR

C) bagimsiz HIZ incelemesinin (2026-10-03) olcup gosterdigi kusurlar
   B19 adim OKUDUKTAN sonra degisen girdi (TOCTOU) -> kayit GECERSIZ; B19b mtime'i
       koruyan degisiklik; B19c depo disi girdi
   B20 zincir sonunda cikti yeniden ozetlenmez (disaridan degisiklik kutsanmaz);
       B20c izlenmeyen yazarin (kicad-cli) adim SIRASINDAKI yazimi o adimin
   B21 kullanicinin PYTHONPATH/NODE_OPTIONS'u, B22 HTTP_PROXY ve gerisi anahtarda
       (RED listesi); B22b oturum degiskenleri anahtarda DEGIL
   B23 ozel_ortam.py (adim ortamini kuran) anahtarda; dogrula3'un her depo modulu
       ANA_SUREC ya da ANAHTAR_DISI
   B24 golge modul (betigin dizinine colorsys.py) -> adim kosar
   B25 ngspice spinit / ~/.spiceinit girdi
   A5b/A5c Ctrl+C semafor beklerken / kopyalarken: yeni surec yok, kalinti yok
   A6b varsayilan isci sayisi makine yukune gore
   A9  ic ice ozel LOCALAPPDATA (B3/B23 iscide dogrula3) Arduino15 + Python'u gorur
   A10 kopya cop dizinlerini tasimaz, kaybolan girdide yeniden dener
   A11 isciler kosu basindaki ANLIK kopyadan kopyalar
   A12 iddiasiz COKME = SUPHELI, tek basina yeniden kosulur; A13 kirmizi taban bir
       kez yeniden olculur; A16 cokme teshisi son istisna satiri
   A14 kopru durum.json paylasim ihlalinde yeniden dener
   A15 Ctrl+C'de kalan kopya yazilir; mutasyon basina Edge sizintisi KIRMIZI
   A17 bayat _mutp* supurulur, sahibi canli olana dokunulmaz
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import gecici                                         # noqa: E402
import mutasyon as M                                   # noqa: E402
import ozel_ortam                                      # noqa: E402
import zincir_onbellek as ZO                           # noqa: E402

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


def yaz(p: Path, metin: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(metin).lstrip("\n"), encoding="utf-8")
    return p


# ══════════════════════════════════════════════════════════════════════
# A) PARALEL MUTASYON KOSUCUSU
# ══════════════════════════════════════════════════════════════════════
ADIM_PY = '''
import os, sys, tempfile, time
from pathlib import Path
B = Path(__file__).resolve().parent
sonuc = []
if os.environ.get("ADIM_BASLAMA"):      # A5c: hicbir adim baslamadi mi
    (Path(os.environ["ADIM_BASLAMA"]) / f"{os.getpid()}").write_text("1")
# 1. dogrula3 suepurmesinin HEDEF ALDIGI bicimde bir dizin: spice-* + _surucu.py
d = tempfile.mkdtemp(prefix="spice-")
open(os.path.join(d, "_surucu.py"), "w").write("# gecici")
time.sleep(float(os.environ.get("ADIM_UYKU", "0.8")))
sonuc.append(("spice dizini suepurulmedi", os.path.exists(os.path.join(d, "_surucu.py"))))
# 2. veri
sonuc.append(("veri dogru", (B / "veri.txt").read_text().strip() == "dogru"))
sonuc.append(("ikinci kural", True))
# 3. isci ortami (yalniz paralel kosucuda isaretli)
if os.environ.get("ADIM_ORTAM_DENETLE"):
    # BU iscinin dizini mi: <kap>/_mutpN-....ozel/tmp — yalniz "_mutp" gecmesi YETMEZ
    # (test bir mutasyon iscisinin icinde kosarken DIS iscinin yolu da "_mutp" tasir).
    kap = B.parent.parent
    gt = Path(tempfile.gettempdir()).resolve()
    sonuc.append(("ozel TEMP", gt.name == "tmp" and gt.parent.name.endswith(".ozel")
                  and gt.parent.parent == kap.resolve()))
    y = Path(os.environ.get("LOCALAPPDATA", ".")).resolve()
    sonuc.append(("ozel LOCALAPPDATA", y.name == "yerel" and y.parent.name.endswith(".ozel")
                  and y.parent.parent == kap.resolve()))
    sonuc.append(("junction ile arac kurulumu gorunuyor",
                  (Path(y) / "Arduino15" / "nobet.txt").read_text() == "arac"))
print("  [OK] KIRMIZI kelimesi gecen YESIL bir satir (teshis bunu gostermemeli)")
for ad, k in sonuc:
    print(("  [OK] " if k else "  [!!] ") + ad)
n = sum(1 for _a, k in sonuc if k)
print(f"  {n}/{len(sonuc)} dogrulama gecti")
sys.exit(0 if n == len(sonuc) else 1)
'''

IKINCI_PY = '''
from pathlib import Path
v = (Path(__file__).resolve().parent / "veri2.txt").read_text().strip()
print("  [OK] v2" if v == "iyi" else "  [!!] v2")
print(f"  {int(v == 'iyi')}/1 dogrulama gecti")
raise SystemExit(0 if v == "iyi" else 1)
'''


def sahte_mut_proje(kap: Path) -> Path:
    kok = kap / "proje"
    yaz(kok / "uretim" / "adim.py", ADIM_PY)
    yaz(kok / "uretim" / "veri.txt", "dogru\n")
    yaz(kok / "uretim" / "ikinci.py", IKINCI_PY)
    yaz(kok / "uretim" / "veri2.txt", "iyi\n")
    return kok


SAHTE_MUT = [
    ("X1", "adim.py", "uretim/veri.txt", "dogru", "yanlis", "veri bozulursa kirmizi"),
    ("X1", "adim.py", "uretim/adim.py", "# 3. isci ortami", "# 3. ISCI ORTAMI",
     "yorum degisikligi KACAR (bos mutasyon ornegi)"),
    ("X1", "adim.py", "uretim/adim.py", "BU DESEN YOK", "x", "uygulanamaz"),
    ("X1", "adim.py", "uretim/adim.py", 'sonuc.append(("ikinci kural", True))', "pass",
     "iddia dusunce sayim degisir (rc 0 olsa da)"),
    ("X2", "ikinci.py", "uretim/veri2.txt", "iyi", "kotu", "ikinci betik"),
    ("X2", "ikinci.py", "uretim/ikinci.py", '"  [OK] v2"', '"  [OK]  v2"', "kacar"),
]
BEKLENEN = {1: "YAKALANDI", 2: "KACTI", 3: "UYGULANAMADI", 4: "YAKALANDI", 5: "YAKALANDI",
            6: "KACTI"}


def test_paralel() -> None:
    print("\n  ── A) paralel mutasyon kosucusu")
    kap = Path(tempfile.mkdtemp(prefix="olcum-hiztest-"))
    eski_yerel = os.environ.get("LOCALAPPDATA")
    try:
        kok = sahte_mut_proje(kap)
        sahte_yerel = kap / "gercek_yerel"
        yaz(sahte_yerel / "Arduino15" / "nobet.txt", "arac")
        yaz(sahte_yerel / "olcum-karti" / "kopru.txt", "kullanicinin")
        # 🔴 BUTUN A testleri SAHTE bir LOCALAPPDATA ile: iscilerin junction'i GERCEK
        #    Arduino15'e (ESP32/AVR cekirdekleri) gitmesin. guvenli_sil'i bozan bir
        #    mutasyon (HIZ: junction izlenir) junction'in hedefini SILER — o hedef
        #    burada sahte dizin olmali. Alt surecler (A5 surucusu) de bunu miras alir.
        os.environ["LOCALAPPDATA"] = str(sahte_yerel)
        ortam = dict(os.environ, LOCALAPPDATA=str(sahte_yerel), ADIM_ORTAM_DENETLE="1")
        sessiz = []

        t0 = time.time()
        s1 = M.mutasyonlari_kos(SAHTE_MUT, kok, 1, ortam, cikis=sessiz.append)
        t1 = time.time() - t0
        t0 = time.time()
        s3 = M.mutasyonlari_kos(SAHTE_MUT, kok, 3, ortam, cikis=sessiz.append)
        t3 = time.time() - t0
        d1 = {r["i"]: r["durum"] for r in s1["sonuclar"]}
        d3 = {r["i"]: r["durum"] for r in s3["sonuclar"]}
        ilk = {r["i"]: r.get("ilk_kirmizi", "") for r in s1["sonuclar"]}
        ok("A1 YAKALANDI satirinin teshisi oldurenin [!!] satiri (yesil satirdaki 'KIRMIZI' "
           "kelimesi degil)", ilk.get(1, "").startswith("[!!] veri dogru")
           and ilk.get(5, "").startswith("[!!] v2"), str(ilk))
        ok("A1 sirali (--paralel 1) beklenen YAKALANDI/KACTI/UYGULANAMADI", d1 == BEKLENEN,
           str(d1) + (f" taban={s1['taban_kirmizi'][0]}" if s1["taban_kirmizi"] else ""))
        ok("A1 paralel (3 isci) AYNI kume", d3 == d1, f"{d3}  ({t1:.1f} s -> {t3:.1f} s)")
        ok("A1 paralel sonuc listesi SECIM sirasinda (ozet ve kacan listesi bitis sirasina "
           "gore karismaz)", [r["i"] for r in s3["sonuclar"]] == sorted(BEKLENEN),
           str([r["i"] for r in s3["sonuclar"]]))
        ok("A2 isci ortami (ozel TEMP + ozel LOCALAPPDATA + Arduino15 junction) tabanda yesil",
           s1["taban_kirmizi"] is None and s3["taban_kirmizi"] is None)
        kalan = [p.name for p in kap.iterdir() if p.name != "proje" and p.name != "gercek_yerel"]
        ok("A4 kopyalar ve ozel dizinler silindi", not kalan and not s3["kalan_dizin"], str(kalan))
        ok("A4 junction HEDEFI silinmedi (gercek arac kurulumu yerinde)",
           (sahte_yerel / "Arduino15" / "nobet.txt").exists())
        ok("A4 gercek olcum-karti dizini isciye BAGLANMADI (kullanicinin dosyasi tek ve yerinde)",
           sorted(p.name for p in (sahte_yerel / "olcum-karti").iterdir()) == ["kopru.txt"])

        # A3: iki esanli kosu + dogrula3'un suepurmesi.
        # 🔴 Suepurme GERCEK %TEMP%'te KOSTURULMAZ: o, kullanicinin baska bir agacta
        #    suren (eski kosucuyla, ortak TEMP'li) mutasyon kosusunun dizinlerini
        #    silerdi — tam da bu dosyanin kapattigi kusur. "Ortak TEMP" sahte bir
        #    dizin; iscilerin taban ortaminin TEMP'i de o (ozel TEMP olmasaydi
        #    adim oraya yazacakti ve suepurulecekti).
        import threading
        ortak_tmp = kap / "ortak_tmp"
        ortak_tmp.mkdir()
        tempfile.tempdir = str(ortak_tmp)       # gecici.kalintilari_sil -> gettempdir()
        dur = threading.Event()
        n_sil = [0]

        def suepur():
            while not dur.is_set():
                n_sil[0] += gecici.kalintilari_sil()
                time.sleep(0.05)
        sonuc = {}
        ortam3 = dict(ortam, ADIM_UYKU="1.5", TEMP=str(ortak_tmp), TMP=str(ortak_tmp),
                      TMPDIR=str(ortak_tmp))

        def kos(ad):
            sonuc[ad] = M.mutasyonlari_kos(SAHTE_MUT, kok, 2, ortam3, cikis=sessiz.append)
        ipler = [threading.Thread(target=suepur)] + [threading.Thread(target=kos, args=(a,))
                                                    for a in ("k1", "k2")]
        for t in ipler:
            t.start()
        for t in ipler[1:]:
            t.join()
        dur.set()
        ipler[0].join()
        ok("A3 iki esanli kosu + %TEMP% suepurmesi: iki taban da yesil, iki sonuc da dogru",
           all(sonuc[a]["taban_kirmizi"] is None
               and {r["i"]: r["durum"] for r in sonuc[a]["sonuclar"]} == BEKLENEN
               for a in ("k1", "k2")),
           str({a: (sonuc[a]["taban_kirmizi"] or [None])[0] for a in sonuc}))
        kalan = [p.name for p in kap.iterdir()
                 if p.name not in ("proje", "gercek_yerel", "ortak_tmp")]
        ok("A3 esanli kosulardan da kalinti yok", not kalan, str(kalan))

        # A3b: NEGATIF KONTROL — suepurme gercekten isiriyor mu: ortak TEMP'teki
        # spice-*/_surucu.py dizinini siliyor mu (siliyorsa A3'un yesili anlamli).
        d = Path(tempfile.mkdtemp(prefix="spice-"))
        (d / "_surucu.py").write_text("#")
        gecici.kalintilari_sil()
        ok("A3b negatif kontrol: suepurme ortak TEMP'teki spice-*/_surucu.py dizinini SILER",
           not d.exists() and str(d).startswith(str(ortak_tmp)))
        shutil.rmtree(d, ignore_errors=True)
        tempfile.tempdir = None

        # A7: taban kirmizi -> hicbir sonuc yok
        (kok / "uretim" / "veri.txt").write_text("bozuk\n")
        s = M.mutasyonlari_kos(SAHTE_MUT[:2], kok, 2, ortam, cikis=sessiz.append)
        ok("A7 taban kirmiziysa kosu durur, hicbir mutasyon YAKALANDI sayilmaz",
           s["taban_kirmizi"] is not None and not any(
               r["durum"] == "YAKALANDI" for r in s["sonuclar"]),
           str((s["taban_kirmizi"] or [None])[0]))
        (kok / "uretim" / "veri.txt").write_text("dogru\n")
        kalan = [p.name for p in kap.iterdir()
                 if p.name not in ("proje", "gercek_yerel", "ortak_tmp")]
        ok("A7 taban kirmizi kosudan da kalinti yok", not kalan, str(kalan))

        # A5: Ctrl+C (CTRL_BREAK) — ayri surecte surucu
        if sys.platform == "win32":
            surucu = yaz(kap / "surucu.py", f'''
                import os, sys
                sys.path.insert(0, {str(BURASI)!r})
                import mutasyon as M
                from pathlib import Path
                M.sinyal_kur()
                ortam = dict(os.environ, ADIM_UYKU="30")
                r = M.mutasyonlari_kos({SAHTE_MUT!r}, Path({str(kok)!r}), 2, ortam)
                print("KESILDI=" + str(r["kesildi"]))
            ''')
            p = subprocess.Popen([sys.executable, str(surucu)], cwd=kap,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 encoding="utf-8", errors="replace")
            son = time.time() + 60
            while time.time() < son and not list(kap.glob("_mutp*.ozel/tmp/spice-*")):
                time.sleep(0.2)
            basladi = bool(list(kap.glob("_mutp*.ozel/tmp/spice-*")))
            p.send_signal(signal.CTRL_BREAK_EVENT)
            try:
                cikti, _ = p.communicate(timeout=90)
            except subprocess.TimeoutExpired:
                p.kill()
                cikti, _ = p.communicate()
            kalan = [x.name for x in kap.iterdir()
                     if x.name not in ("proje", "gercek_yerel", "surucu.py", "ortak_tmp")]
            ok("A5 Ctrl+C (CTRL_BREAK) kosuyu keser ve kopyalari siler",
               basladi and "KESILDI=True" in cikti and not kalan,
               f"basladi={basladi} kalan={kalan} cikti={cikti[-200:]!r}")

        # A8: AGIR (tarayici) mutasyonlari en fazla TARAYICI_AZAMI esanli
        test_tarayici(kap, sessiz)

        # A6: secim
        sec, atl = M.secim(None, "4C:")
        ok("A6 --neden onek suzgeci yalniz o onekle baslayanlari secer",
           sec and all(m[5].startswith("4C:") for m in sec)
           and len(sec) == sum(1 for m in M.MUTASYONLAR if m[5].startswith("4C:")))
        sec, atl = M.secim(None, None)
        ok("A6 hedefsiz kosu AGIR adimlari atlar", atl and not any(m[0] in M.AGIR for m in sec))
        sec, _ = M.secim(None, "TTR:")
        ok("A6 --neden AGIR adimlari atlamaz (hedefli istek)",
           bool(sec) and all(m[0] in M.AGIR for m in sec))
        ok("A6 Edge acan AGIR-disi betik (B57 kutu_ipucu_test) da tarayici sinirinda; "
           "duz betik degil",
           M.sinirli(("B57", "kutu_ipucu_test.py")) and M.sinirli(("T3A", "tarayici_tema.py"))
           and M.sinirli(("B3", "dogrula3.py")) and not M.sinirli(("B50", "kutu.py")))
        ok("A6 kopyalar artimli zincirin onbellegini TASIMAZ (kopyada kok farkli + dosya disarida)",
           ".zincir_onbellek.json" in M.ATLA_DOSYA)
    finally:
        tempfile.tempdir = None
        if eski_yerel is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = eski_yerel
        M.guvenli_sil(kap)


TARAYICI_PY = '''
import os, subprocess, sys, tempfile, time
from pathlib import Path
# Windows'ta "a" kipi ATOMIK DEGIL (CRT sona-git + yaz): esanli surecler ayni dosyaya
# eklerken satir kaybeder. Her kosu KENDI dosyasini yazar.
kayit = Path(os.environ["ADIM_KAYIT"]) / f"{os.getpid()}-{time.time_ns()}.txt"
bas = time.time()
if os.environ.get("ADIM_SIZDIR"):
    # basliksiz Edge'in kapanmadan kalmasi: profil dizini (ozel TEMP altinda) komut
    # satirinda gecen, adimdan SONRA yasayan bir "msedge.exe"
    d = Path(tempfile.mkdtemp(prefix="olcum-edge-"))
    exe = d / "msedge.exe"
    import shutil
    shutil.copy(os.environ["ADIM_SAHTE_EDGE"], exe)
    # waitfor bir sinyal adini sistem genelinde TEK surece verir: esanli testler icin benzersiz ad
    subprocess.Popen([str(exe), "/T", "40", f"olcumhiz{os.getpid()}"],
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
time.sleep(1.0)
kayit.write_text(f"{bas} {time.time()}")
# m1
# m2
# m3
# m4
print("  1/1 dogrulama gecti")
'''


def test_tarayici(kap: Path, sessiz: list) -> None:
    kok = kap / "proje"
    yaz(kok / "uretim" / "tarayici_sahte.py", TARAYICI_PY)
    kayit = kap / "tarayici_kayit"
    kayit.mkdir()
    muts = [("XT", "tarayici_sahte.py", "uretim/tarayici_sahte.py", f"# m{n}", f"# M{n}", "kacar")
            for n in range(1, 5)]
    eski = M.AGIR
    M.AGIR = set(eski) | {"XT"}
    try:
        ortam = dict(os.environ, ADIM_KAYIT=str(kayit))
        s = M.mutasyonlari_kos(muts, kok, 4, ortam, cikis=sessiz.append)
        ok(f"A8 hepsi tarayici/AGIR olan secimde isci sayisi TARAYICI_AZAMI'ya iner (her isci kendi "
           f"tabanini kosuyor; fazlasi yalniz fazladan taban demek)", s["paralel"] == M.TARAYICI_AZAMI,
           f"paralel={s['paralel']}")
        for f in kayit.iterdir():
            f.unlink()
        # karisik secim (4 tarayici + 1 duz): 4 isci kalir, tarayici siniri SEMAFORLA uygulanmali
        s = M.mutasyonlari_kos(muts + [SAHTE_MUT[0]], kok, 4, ortam, cikis=sessiz.append)
        olay = []
        for f in kayit.iterdir():
            b, z = f.read_text().split()
            olay += [(float(b), 1), (float(z), -1)]
        en_cok = an = 0
        for _z, d in sorted(olay):
            an += d
            en_cok = max(en_cok, an)
        ok(f"A8 AGIR (tarayici) kosulari 4 iscide bile en fazla {M.TARAYICI_AZAMI} esanli",
           s["paralel"] == 4 and len(olay) == 16 and en_cok <= M.TARAYICI_AZAMI
           and [r["durum"] for r in s["sonuclar"]] == ["KACTI"] * 4 + ["YAKALANDI"],
           f"en cok {en_cok} esanli, {len(olay) // 2} kosu")

        # Edge sizintisi: sahte "msedge.exe" ozel TEMP'teki profilden yasiyor
        findstr = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "waitfor.exe"
        ortam2 = dict(ortam, ADIM_SIZDIR="1", ADIM_SAHTE_EDGE=str(findstr))
        s = M.mutasyonlari_kos(muts[:1], kok, 1, ortam2, cikis=sessiz.append)
        kalan = M.edge_kalanlar(str(kap))      # yalniz BU testin dizinleri (esanli testler)
        artik = [p.name for p in kap.iterdir() if p.name.startswith(M.ISCI_ONEK)]
        ok("A8 AGIR mutasyondan sonra sizan Edge YAKALANIR, oldurulur, kalinti kalmaz",
           s["sonuclar"] and s["sonuclar"][0].get("sizinti", 0) >= 1 and not kalan and not artik,
           f"sonuc={s['sonuclar'][:1]} kalan={kalan} artik={artik} genel={s['sizinti']}")
    finally:
        M.AGIR = eski


# ══════════════════════════════════════════════════════════════════════
# B) ARTIMLI ZINCIR
# ══════════════════════════════════════════════════════════════════════
def sahte_zincir_proje(kap: Path) -> Path:
    kok = kap / "proje"
    yaz(kok / "a.py", '''
        from pathlib import Path
        B = Path(__file__).resolve().parent
        v = (B / "veri_a.txt").read_text()
        # geri donus aginda (127.0.0.0/8, 127.0.0.1 DEGIL) sahte sunucu — 4E testi gibi; dis ag sayilmamali
        import socket
        sv = socket.socket(); sv.bind(("127.83.41.7", 0)); sv.listen(1)
        socket.create_connection(("127.83.41.7", sv.getsockname()[1]), timeout=5).close(); sv.close()
        print("  1/1 dogrulama gecti" if v else "  0/1 dogrulama gecti")
    ''')
    yaz(kok / "veri_a.txt", "a1")
    yaz(kok / "b.py", '''
        import subprocess, sys
        from pathlib import Path
        B = Path(__file__).resolve().parent
        r = subprocess.run([sys.executable, str(B / "b_cocuk.py")], capture_output=True, text=True)
        print(r.stdout, end="")
        print("  2/2 dogrulama gecti")
    ''')
    yaz(kok / "b_cocuk.py", '''
        from pathlib import Path
        print((Path(__file__).resolve().parent / "veri_b.txt").read_text())
    ''')
    yaz(kok / "veri_b.txt", "b1")
    araclar = kok / "araclar"
    araclar.mkdir()
    findstr = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "findstr.exe"
    shutil.copy(findstr, araclar / "avr-gcc.exe")
    shutil.copy(findstr, araclar / "bilinmez-arac.exe")
    yaz(kok / "c.py", '''
        import subprocess, sys
        from pathlib import Path
        B = Path(__file__).resolve().parent
        r = subprocess.run([str(B / "araclar" / "avr-gcc.exe"), "c", "veri_c.txt"], cwd=B,
                           capture_output=True, text=True)
        print("  1/1 dogrulama gecti" if r.returncode == 0 else "  0/1 dogrulama gecti")
    ''')
    yaz(kok / "veri_c.txt", "c1")
    yaz(kok / "d.py", '''
        import subprocess, sys
        from pathlib import Path
        B = Path(__file__).resolve().parent
        # arac DOSYAYI ARGUMANLA degil, kendi bildigi bir yerden okuyor gibi: kurali yok
        r = subprocess.run([str(B / "araclar" / "bilinmez-arac.exe"), "d", "veri_d.txt"], cwd=B,
                           capture_output=True, text=True)
        print("  1/1 dogrulama gecti")
    ''')
    yaz(kok / "veri_d.txt", "d1")
    yaz(kok / "e.py", '''
        import os
        from pathlib import Path
        B = Path(__file__).resolve().parent
        var = (B / "isaret" / "bayrak.txt").exists()
        adlar = sorted(os.listdir(B / "liste_dizin"))
        print(f"  1/1 dogrulama gecti  bayrak={var} adlar={adlar}")
    ''')
    # ⚠ Adimlar betigin dizinini (kok) sys.path olarak LISTELER (golge modul) — kokte dosya
    #   belirmesi/silinmesi HER Python adimini kosturur. Tek adimi hedefleyen testler alt dizinde.
    (kok / "isaret").mkdir()
    (kok / "ciktilar").mkdir()
    (kok / "liste_dizin").mkdir()
    yaz(kok / "liste_dizin" / "x.txt", "x")
    yaz(kok / "f.py", '''
        from pathlib import Path
        B = Path(__file__).resolve().parent
        (B / "ciktilar" / "cikti_f.txt").write_text("uretildi")
        print("  1/1 dogrulama gecti")
    ''')
    yaz(kok / "g.py", '''
        import subprocess, sys, time
        from pathlib import Path
        B = Path(__file__).resolve().parent
        p = subprocess.Popen([sys.executable, str(B / "g_sunucu.py")])
        isaret = B / "g_hazir.txt"
        son = time.time() + 20
        while not isaret.exists() and time.time() < son:
            time.sleep(0.05)
        p.terminate(); p.wait()
        isaret.unlink()
        print("  1/1 dogrulama gecti")
    ''')
    yaz(kok / "g_sunucu.py", '''
        import time
        from pathlib import Path
        B = Path(__file__).resolve().parent
        (B / "veri_g.txt").read_text()
        (B / "g_hazir.txt").write_text("1")
        time.sleep(60)
    ''')
    yaz(kok / "veri_g.txt", "g1")
    yaz(kok / "h.py", '''
        import subprocess, sys
        from pathlib import Path
        B = Path(__file__).resolve().parent
        ortam = {"SystemRoot": __import__("os").environ.get("SystemRoot", "")}
        subprocess.run([sys.executable, "-c", "print(1)"], env=ortam, capture_output=True)
        print("  1/1 dogrulama gecti")
    ''')
    yaz(kok / "k.py", '''
        import sys
        print("  0/1 dogrulama gecti")
        sys.exit(1)
    ''')
    yaz(kok / "i.py", '''
        import subprocess, sys
        # -I: yalitilmis kip PYTHONPATH'i yok sayar -> kanca yuklenmez -> rapor yok
        subprocess.run([sys.executable, "-I", "-c", "print(1)"], capture_output=True)
        print("  1/1 dogrulama gecti")
    ''')
    yaz(kok / "j.mjs", '''
        import { k } from './k.mjs';
        import { readFileSync } from 'node:fs';
        const v = readFileSync(new URL('./veri_j.txt', import.meta.url), 'utf8');
        console.log(`  1/1 dogrulama gecti ${k} ${v}`);
    ''')
    yaz(kok / "k.mjs", "export const k = 1;\n")
    yaz(kok / "veri_j.txt", "j1")
    # L ve M AYNI dosyayi farkli icerikle yazar (B3/B9 ve netlist3.net gibi)
    yaz(kok / "l.py", '''
        from pathlib import Path
        (Path(__file__).resolve().parent / "ortak_cikti.txt").write_text("L")
        print("  1/1 dogrulama gecti")
    ''')
    yaz(kok / "m.py", '''
        from pathlib import Path
        (Path(__file__).resolve().parent / "ortak_cikti.txt").write_text("M")
        print("  1/1 dogrulama gecti")
    ''')
    # N, onbellek dosyasinin DURDUGU dizini listeler (B2/B15/B73 ve uretim/ gibi)
    (kok / "durum").mkdir()
    yaz(kok / "durum" / "kalici.txt", "k")
    yaz(kok / "n.py", '''
        import os
        from pathlib import Path
        d = Path(__file__).resolve().parent / "durum"
        # dizindeki HER dosyayi okur (uretim/*.json'u tarayan bir adim gibi) — onbellek dahil
        n = sum(len((d / a).read_bytes()) > 0 for a in os.listdir(d) if (d / a).is_file())
        print("  1/1 dogrulama gecti", n)
    ''')
    yaz(kok / "tetik.py", "# tam kosu tetigi\n")
    return kok


def govde(kok: Path, betik: str):
    def g(cal):
        komut = ["node", betik] if betik.endswith(".mjs") else [sys.executable, betik]
        r = cal(komut, cwd=kok, timeout=120)
        return r.returncode == 0, r.stdout.rstrip(), r.stdout
    return g


ADIMLAR_B = [("A", "a.py"), ("B", "b.py"), ("C", "c.py"), ("D", "d.py"), ("E", "e.py"),
             ("F", "f.py"), ("G", "g.py"), ("H", "h.py"), ("I", "i.py"), ("J", "j.mjs"),
             ("K", "k.py"), ("L", "l.py"), ("M", "m.py"), ("N", "n.py")]
HER_ZAMAN_B = ["D", "H", "I"]


def zincir_kos(kok: Path, yol: Path, artimli=True, tam=False, simdi=None):
    z = ZO.Zincir(kok=kok, yol=yol, artimli=artimli, tam=tam, simdi=simdi, tetik=("tetik.py",))
    for b, betik in ADIMLAR_B:
        z.kos(b, govde(kok, betik))
    z.bitir()
    return z, {s.baslik: s for s in z.sonuclar}


def test_artimli() -> None:
    print("\n  ── B) artimli zincir")
    # Sahte proje %TEMP%'TE OLAMAZ: Kapsam %TEMP%'i girdi saymiyor (orasi adimlarin
    # gecici dizinleri). Kardes dizin — mutasyon kopyalari gibi.
    kap = KOK.parent / f"_zhiz-test-{os.getpid()}"
    M.guvenli_sil(kap)
    kap.mkdir()
    try:
        kok = sahte_zincir_proje(kap)
        # onbellek, N'nin listeledigi dizinde (uretim/.zincir_onbellek.json gibi); ILK tam
        # kosuda henuz yok, sonunda yaziliyor
        yol = kok / "durum" / ".zincir_onbellek.json"
        z, s = zincir_kos(kok, yol, artimli=False)
        ok("B0 ilk (tam) kosu: K kirmizi, digerleri yesil",
           [b for b, x in s.items() if not x.tamam] == ["K"], str({b: x.tamam for b, x in s.items()}))
        v = json.loads(yol.read_text(encoding="utf-8"))
        ok("B0 kirmizi adim onbellege YAZILMAZ; tam kosu kirmizi icerdigi icin 'son_tam' yok",
           "K" not in v["adimlar"] and "son_tam" not in v)
        z, s = zincir_kos(kok, yol, artimli=True)
        ok("B0 YESIL tam kosu kaydi yokken artimli kip TAM kosar", z.tam_kosu, z.tam_sebep)

        # 'son_tam'i elle kur: K'yi yesile cevirip tam kos
        (kok / "k.py").write_text("print('  1/1 dogrulama gecti')\n", encoding="utf-8")
        z, s = zincir_kos(kok, yol, artimli=False)
        v = json.loads(yol.read_text(encoding="utf-8"))
        ok("B0 yesil tam kosu 'son_tam' yazar", "son_tam" in v and all(x.tamam for x in s.values()))
        her = {b: x.her_zaman for b, x in s.items() if x.her_zaman}
        ok("B5 kurali olmayan arac (bilinmez-arac) -> D HER ZAMAN KOSAR",
           "D" in her and any("sinirlanamayan arac" in h for h in her["D"]), str(her.get("D")))
        ok("B15 iz ortamini dusuren Python alt sureci -> H HER ZAMAN KOSAR",
           "H" in her and any("iz ortamini dusurdu" in h for h in her["H"]), str(her.get("H")))
        ok("B15b -I bayrakli (kancayi yuklemeyen) Python alt sureci -> I HER ZAMAN KOSAR "
           "(rapor sayimi)", "I" in her and any("rapor var" in h for h in her["I"]),
           str(her.get("I")))
        ok("B5/B15 digerleri sinirli (HER ZAMAN listesinde yalniz D, H, I; A'nin 127.83.41.7 "
           "geri donus baglantisi dis ag sayilmaz)",
           sorted(her) == HER_ZAMAN_B, str(sorted(her)))

        z, s = zincir_kos(kok, yol)
        alinan = sorted(b for b, x in s.items() if x.onbellek_yas is not None)
        ok("B1 hicbir sey degismedi -> D, H, I disindaki her adim (node dahil) onbellekten; "
           "ayni dosyayi yazan L ve M de (cikti zincir SONUNDAKI haliyle); onbellegin durdugu "
           "dizini listeleyen N de", alinan == ["A", "B", "C", "E", "F", "G", "J", "K", "L", "M", "N"],
           str(alinan) + " " + str({b: x.sebep for b, x in s.items() if x.onbellek_yas is None}))
        ok("B1 onbellekten gelen adimin ciktisi (sayim satiri) aynen geri gelir",
           "1/1 dogrulama gecti" in s["A"].cikti and s["A"].tamam)

        def tek_degisiklik(ad, islem, beklenen_kosan):
            islem()
            z, s = zincir_kos(kok, yol)
            kosan = sorted(b for b, x in s.items() if x.onbellek_yas is None)
            ok(ad, kosan == sorted(beklenen_kosan + HER_ZAMAN_B),
               f"kosan={kosan} sebep={[x.sebep for b, x in s.items() if b in beklenen_kosan]}")
            return s

        tek_degisiklik("B2 adimin actigi dosya degisti -> yalniz o adim kosar",
                       lambda: (kok / "veri_a.txt").write_text("a2"), ["A"])
        tek_degisiklik("B2b icerik ayni, yalniz dokunuldu (mtime) -> yine onbellekten",
                       lambda: os.utime(kok / "veri_a.txt"), [])
        tek_degisiklik("B3 yalniz ALT Python surecinin actigi dosya degisti -> B kosar",
                       lambda: (kok / "veri_b.txt").write_text("b2"), ["B"])
        tek_degisiklik("B4 derleyici argumani olan dosya degisti -> C kosar",
                       lambda: (kok / "veri_c.txt").write_text("c2"), ["C"])
        tek_degisiklik("B4b derleyici IKILISI degisti (boyut/mtime) -> C kosar",
                       lambda: os.utime(kok / "araclar" / "avr-gcc.exe",
                                        (time.time(), time.time() + 5)), ["C"])
        tek_degisiklik("B16 node: import edilen ES modulu degisti -> J kosar",
                       lambda: (kok / "k.mjs").write_text("export const k = 2;\n"), ["J"])
        # B16c: ES modul yuklemesi node'un YUKLEYICI kancasindan da kayitli mi (fs yamasindan
        # bagimsiz — Node 24 ESM kaynagini fs.readFileSync'ten okuyor, bu bir ic ayrinti)
        iz_d = Path(tempfile.mkdtemp(prefix="olcum-zincir-iz-"))
        try:
            subprocess.run(["node", "j.mjs"], cwd=kok, env=ZO.izli_ortam(iz_d),
                           capture_output=True, timeout=60)
            kayitlar = [json.loads(x) for f in iz_d.glob("node-*.jsonl")
                        for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        finally:
            shutil.rmtree(iz_d, ignore_errors=True)
        ok("B16c node yukleyici kancasi (module.registerHooks) import edilen k.mjs'yi kaydeder",
           any(k.get("t") == "yukle" and k.get("p", "").endswith("k.mjs") for k in kayitlar),
           str([k for k in kayitlar if k.get("t") == "yukle"])[:200])
        tek_degisiklik("B16b node: fs ile okunan dosya degisti -> J kosar",
                       lambda: (kok / "veri_j.txt").write_text("j2"), ["J"])
        tek_degisiklik("B10 varligina bakilan yol belirdi -> E kosar",
                       lambda: (kok / "isaret" / "bayrak.txt").write_text("1"), ["E"])
        tek_degisiklik("B10b listelenen dizine dosya eklendi -> E kosar",
                       lambda: (kok / "liste_dizin" / "y.txt").write_text("y"), ["E"])
        tek_degisiklik("B11 adimin ciktisi silindi -> F kosar (cikti yeniden uretilir)",
                       lambda: (kok / "ciktilar" / "cikti_f.txt").unlink(), ["F"])
        ok("B11 F ciktiyi yeniden uretti", (kok / "ciktilar" / "cikti_f.txt").exists())
        tek_degisiklik("B13 OLDURULEN alt surecin okudugu dosya degisti -> G kosar (yaz-gec)",
                       lambda: (kok / "veri_g.txt").write_text("g2"), ["G"])

        # B11b: kirmizi adim saklanmaz -> sonraki kosuda yine kosar
        (kok / "veri_a.txt").write_text("")
        (kok / "a.py").write_text((kok / "a.py").read_text() + "\nraise SystemExit(0 if v else 1)\n")
        z, s = zincir_kos(kok, yol)
        z2, s2 = zincir_kos(kok, yol)
        ok("B11b kirmizi adim onbellege yazilmaz, sonraki kosuda YINE kosar",
           not s["A"].tamam and s2["A"].onbellek_yas is None and not s2["A"].tamam)
        (kok / "veri_a.txt").write_text("a3")
        zincir_kos(kok, yol)

        z, s = zincir_kos(kok, yol, tam=True)
        ok("B6 --tam hepsini kosar", all(x.onbellek_yas is None for x in s.values())
           and z.tam_kosu)

        v = json.loads(yol.read_text(encoding="utf-8"))
        z, s = zincir_kos(kok, yol, simdi=v["son_tam"]["zaman"] + 25 * 3600)
        ok("B7 son tam kosu 24 saatten eski -> TAM kosu", z.tam_kosu
           and all(x.onbellek_yas is None for x in s.values()), z.tam_sebep)

        # B14: tetik dosyasi (B7 'son_tam'i gelecege yazdi: once simdiki zamanla tam kos)
        zincir_kos(kok, yol, tam=True)
        z, s = zincir_kos(kok, yol)
        ok("B14 on kosul: degisiklik yokken artimli", not z.tam_kosu, z.tam_sebep)
        (kok / "tetik.py").write_text("# degisti\n")
        z, s = zincir_kos(kok, yol)
        ok("B14 TAM_TETIK dosyasi degisti -> TAM kosu", z.tam_kosu and "tetik.py" in z.tam_sebep,
           z.tam_sebep)

        # B8: bozuk onbellek
        yol.write_text("{bozuk json", encoding="utf-8")
        z, s = zincir_kos(kok, yol)
        ok("B8 bozuk onbellek -> TAM kosu (sebep: bozuk)", z.tam_kosu and "bozuk" in z.tam_sebep,
           z.tam_sebep)
        v = json.loads(yol.read_text(encoding="utf-8"))
        del v["adimlar"]["A"]["imza"]
        v["adimlar"]["B"]["imza"]["dosya"] = "bozuk"
        yol.write_text(json.dumps(v), encoding="utf-8")
        z, s = zincir_kos(kok, yol)
        ok("B8 bozuk adim kaydi -> o adim kosar (A, B)",
           s["A"].onbellek_yas is None and s["B"].onbellek_yas is None
           and s["C"].onbellek_yas is not None, f"{s['A'].sebep} | {s['B'].sebep}")

        # B17: onbellek dosyasi ILK kez belirince, onun dizinini listeleyen adim (uretim/'yi
        # listeleyen B2/B15/B73 gibi) yine onbellekten gelmeli — ilk tam kosudan hemen sonra
        kok_n = kap / "proje_n"
        yaz(kok_n / "n2.py", '''
            import os
            from pathlib import Path
            print("  1/1 dogrulama gecti", sorted(os.listdir(Path(__file__).resolve().parent / "durum")))
        ''')
        (kok_n / "durum").mkdir()
        yol_n = kok_n / "durum" / ".zincir_onbellek.json"
        for artimli in (False, True):
            zn = ZO.Zincir(kok=kok_n, yol=yol_n, artimli=artimli, tetik=())
            sn = zn.kos("N2", govde(kok_n, "n2.py"))
            zn.bitir()
        ok("B17 ilk tam kosunun SONUNDA yazilan onbellek dosyasi, dizinini listeleyen adimi "
           "kosturmaz", sn.onbellek_yas is not None and not zn.tam_kosu,
           f"{zn.tam_sebep} {sn.sebep}")

        # B18: OZEL LOCALAPPDATA (dogrula3 adimlari gercek %LOCALAPPDATA%\\olcum-karti'yi gormez)
        gercek = kap / "gercek_yerel"
        yaz(gercek / "Arduino15" / "cekirdek.txt", "c1")
        yaz(gercek / "Python" / "surum.txt", "3.14")
        yaz(gercek / "olcum-karti" / "kopru.txt", "kullanicinin")
        kok_y = kap / "proje_y"
        yaz(kok_y / "y.py", '''
            import os
            from pathlib import Path
            y = Path(os.environ["LOCALAPPDATA"])
            ozel = y.name == "yerel"          # yalniz OZEL dizine yazar (gercege asla)
            if ozel:
                (y / "olcum-karti").mkdir(exist_ok=True)
                (y / "olcum-karti" / "test.txt").write_text("x")
            v = (y / "Arduino15" / "cekirdek.txt").read_text() if ozel else "?"
            p = (y / "Python" / "surum.txt").read_text() if ozel else "?"
            print(f"  {int(ozel)}/1 dogrulama gecti", v, "python", p)
            raise SystemExit(0 if ozel else 1)
        ''')

        def kos_y():
            oz = kap / f"_zincir-yerel-test-{time.time_ns()}"
            yerel = ozel_ortam.yerel_kur(oz / "yerel", str(gercek))
            try:
                zy = ZO.Zincir(kok=kok_y, yol=kok_y / "onb.json", artimli=True, tetik=(),
                               ozel_yerel=yerel)
                sy = zy.kos("Y", govde(kok_y, "y.py"))
                zy.bitir()
                return sy
            finally:
                ozel_ortam.guvenli_sil(oz)
        # depo DISI girdi (gercek_yerel): "adim basladiktan sonra degisti" denetimi mtime'a
        # 100 ms pay birakir — hemen once yazilmis dosya da (temkinli) "degisti" sayilirdi
        time.sleep(0.3)
        s1, s2 = kos_y(), kos_y()
        (gercek / "Arduino15" / "cekirdek.txt").write_text("c2")
        s3 = kos_y()
        ok("B18 adim OZEL LOCALAPPDATA'da kosar; gercek dizinin HER ust dizini (Arduino15, "
           "Python ...) junction'la gorunur; gercek olcum-karti'ya YAZMAZ",
           s1.tamam and "c1" in s1.cikti and "python 3.14" in s1.cikti
           and sorted(p.name for p in (gercek / "olcum-karti").iterdir()) == ["kopru.txt"],
           s1.cikti.strip()[-80:])
        ok("B18 her kosu BASKA ozel dizinde olsa da adim onbellekten gelir (junction yolu gercek "
           "yola cevrilir)", s2.onbellek_yas is not None, s2.sebep)
        ok("B18 junction arkasindaki gercek dosya degisince adim kosar",
           s3.onbellek_yas is None and "c2" in s3.cikti, s3.sebep)
        ok("B18 ozel dizinler silindi, junction hedefi yerinde",
           (gercek / "Arduino15" / "cekirdek.txt").exists()
           and not list(kap.glob("_zincir-yerel-test-*")))
        kaynak = (BURASI / "dogrula3.py").read_text(encoding="utf-8")
        ok("B18 dogrula3 zinciri ozel LOCALAPPDATA ile kuruyor ve sonunda siliyor",
           "ozel_ortam.yerel_kur(" in kaynak and "ozel_yerel=yerel)" in kaynak
           and "return _kos(argv, artimli, kilit_yaz, izsiz, yerel)" in kaynak
           and "ozel_ortam.guvenli_sil(ozel)" in kaynak)

        # B12: baska kok
        kok2 = kap / "kopya"
        shutil.copytree(kok, kok2)
        yol2 = kap / "onbellek2.json"
        shutil.copy(yol, yol2)
        z, s = zincir_kos(kok2, yol2)
        ok("B12 baska kokun (mutasyon kopyasi) onbellegi KULLANILMAZ", z.tam_kosu
           and all(x.onbellek_yas is None for x in s.values()), z.tam_sebep)

        # B9: sayim kilidi onbellekten gelen adimlarla
        import dogrula3
        z, s = zincir_kos(kok, yol)
        sonuclar = [(x.baslik, x.tamam, x.sure, x.cikti) for x in z.sonuclar]
        alinan = [x.baslik for x in z.sonuclar if x.onbellek_yas is not None]
        eski_yol = dogrula3.TABAN_YOLU
        try:
            dogrula3.TABAN_YOLU = kap / "kilit.json"
            dogrula3.TABAN_YOLU.write_text(json.dumps(
                {b: [list(c) for c in __import__("sayim").sayimlar(c)]
                 for b, _t, _s, c in sonuclar}), encoding="utf-8")
            h_ayni = dogrula3.sayim_kilidi(sonuclar)
            kilit = json.loads(dogrula3.TABAN_YOLU.read_text(encoding="utf-8"))
            kilit["A"] = [[2, 2]]
            dogrula3.TABAN_YOLU.write_text(json.dumps(kilit), encoding="utf-8")
            h_fark = dogrula3.sayim_kilidi(sonuclar)
        finally:
            dogrula3.TABAN_YOLU = eski_yol
        ok("B9 sayim kilidi onbellekten gelen adimlarin sayisini da karsilastirir",
           len(alinan) >= 5 and not h_ayni and any(h.startswith("A:") for h in h_fark),
           f"alinan={alinan} fark={h_fark}")
        # (alt surecle DEGIL: reddi bozan bir mutasyon tam zinciri kostururdu)
        red = dogrula3.arguman_reddi(["--artimli", "--sayim-kilidi-yaz"])
        kaynak = (BURASI / "dogrula3.py").read_text(encoding="utf-8")
        govde_main = kaynak[kaynak.index("def main("):]
        ok("B9 --sayim-kilidi-yaz --artimli ile REDDEDILIR (kilit yalniz tam kosudan); "
           "tek basina --sayim-kilidi-yaz serbest; main() reddi ilk is olarak uyguluyor",
           bool(red) and "TAM kosu ister" in red
           and dogrula3.arguman_reddi(["--sayim-kilidi-yaz"]) is None
           and dogrula3.arguman_reddi(["--artimli"]) is None
           and govde_main.index("arguman_reddi(argv)") < govde_main.index("ZO.Zincir(")
           and "return 2" in govde_main[:govde_main.index("ZO.Zincir(")], str(red))
    finally:
        M.guvenli_sil(kap)


def test_yapisal() -> None:
    print("\n  ── yapisal")
    gi = (KOK / ".gitignore").read_text(encoding="utf-8")
    ok("onbellek dosyasi .gitignore'da (depoya girmez, mutlak yol tasir) — satir olarak",
       "uretim/.zincir_onbellek.json" in [x.strip() for x in gi.splitlines()])
    import dogrula3
    kaynak = (BURASI / "dogrula3.py").read_text(encoding="utf-8")
    ok("dogrula3 cop toplayicisi kaliplari zincir_onbellek'ten aliyor (TEK KAYNAK)",
       "ZO.COP_URETIM_KOPRU" in kaynak and "ZO.COP_BUILD" in kaynak
       and "ZO.COP_URETIM_DOSYA" in kaynak)
    ok("dogrula3 22 adimin hepsini Zincir uzerinden kosuyor",
       len(dogrula3.ADIMLAR) + len(dogrula3.EL_ADIM_GOVDELERI) == dogrula3.ADIM_SAYISI)
    k = ZO.Kapsam(KOK)
    ok("cop kaliplari: uretim/avr/__pycache__, kopru/_b1/x, uretim/erc3.rpt, kod/.../build/x cop; "
       "kopru/arsiv/_b1 ve uretim/tasarim3.py DEGIL",
       all(k.cop_mu(str(KOK / p)) for p in ("uretim/avr/__pycache__/x.pyc", "kopru/_b1/x",
                                             "uretim/erc3.rpt", "kod/olcum-karti-a3/build/x.o"))
       and not any(k.cop_mu(str(KOK / p)) for p in ("kopru/arsiv/_b1", "uretim/tasarim3.py")))


# ══════════════════════════════════════════════════════════════════════
# C) HIZ INCELEMESI (2026-10-03) — bagimsiz incelemenin olcup gosterdigi kusurlar
# ══════════════════════════════════════════════════════════════════════
def test_inceleme_zincir() -> None:
    print("\n  ── C) inceleme: artimli zincir")
    kap = KOK.parent / f"_zhiz-ek-{os.getpid()}"
    M.guvenli_sil(kap)
    kap.mkdir()
    eski_ortam = {k: os.environ.get(k) for k in ("PYTHONPATH", "NODE_OPTIONS", "HTTP_PROXY",
                                                 "CLAUDE_CODE_SESSION_ID")}
    try:
        # ── B19: TOCTOU — adim okuduktan SONRA degisen girdi
        kok_t = kap / "proje_t"
        yaz(kok_t / "t.py", '''
            from pathlib import Path
            B = Path(__file__).resolve().parent
            v = (B / "veri_t.txt").read_text().strip()
            (B / "tetik_t.txt").read_text()
            (B.parent / "dis_t.txt").read_text()          # depo DISI girdi
            ok = v != "kot"
            print(f"  {int(ok)}/1 dogrulama gecti")
            raise SystemExit(0 if ok else 1)
        ''')
        yaz(kok_t / "veri_t.txt", "iyi")
        yaz(kok_t / "tetik_t.txt", "t1")
        yaz(kap / "dis_t.txt", "d1")
        mod = {"hedef": None, "icerik": "", "mtime_koru": False}

        def govde_t(cal):
            r = cal([sys.executable, "t.py"], cwd=kok_t, timeout=120)
            if mod["hedef"] is not None:
                # "kullanici" adim KOSARKEN (adim dosyayi okuduktan sonra) degistiriyor
                p = mod["hedef"]
                st = os.stat(p)
                p.write_text(mod["icerik"])
                if mod["mtime_koru"]:
                    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
                mod["hedef"] = None
            return r.returncode == 0, r.stdout.rstrip(), r.stdout

        def kos_t(artimli=True):
            z = ZO.Zincir(kok=kok_t, yol=kok_t / "onb.json", artimli=artimli, tetik=())
            s = z.kos("T", govde_t)
            z.bitir()
            return z, s

        time.sleep(0.3)          # depo disi dis_t.txt: 100 ms mtime payinin disinda kalsin
        mod.update(hedef=kok_t / "veri_t.txt", icerik="kot", mtime_koru=False)
        _z, s1 = kos_t(artimli=False)
        _z, s2 = kos_t()
        ok("B19 adim OKUDUKTAN sonra degisen (depo ici, ilk kez gorulen) girdi: kayit GECERSIZ, "
           "sonraki --artimli kosu adimi KOSTURUR ve kirmiziyi gorur (eskiden onbellekten YESIL)",
           s1.tamam and bool(s1.gecersiz) and s2.onbellek_yas is None and not s2.tamam,
           f"s1.gecersiz={s1.gecersiz[:120]!r} s2: yas={s2.onbellek_yas} tamam={s2.tamam} "
           f"sebep={s2.sebep[:80]!r}")

        (kok_t / "veri_t.txt").write_text("iyi")
        kos_t(artimli=False)
        _z, s3 = kos_t()
        ok("B19 on kosul: degisiklik yokken T onbellekten", s3.onbellek_yas is not None, s3.sebep)
        # B19b: kayitli girdi, mtime KORUNARAK ayni boyda degisir — yalniz icerik karsilastirmasi
        (kok_t / "tetik_t.txt").write_text("t2")          # T'yi kosmaya zorla
        mod.update(hedef=kok_t / "veri_t.txt", icerik="kot", mtime_koru=True)
        _z, s4 = kos_t()
        _z, s5 = kos_t()
        ok("B19b mtime'i KORUYAN (ayni boy) degisiklik adim kosarken: onceki kaydin girdileri "
           "adimdan ONCE icerikle ozetlenir -> GECERSIZ, sonraki kosu kosar",
           s4.onbellek_yas is None and s4.tamam and bool(s4.gecersiz)
           and s5.onbellek_yas is None and not s5.tamam,
           f"s4.gecersiz={s4.gecersiz[:100]!r} s5 yas={s5.onbellek_yas} tamam={s5.tamam}")
        # B19c: depo DISI girdi (ilk kez gorulen) adim kosarken degisir — mtime yolu
        (kok_t / "veri_t.txt").write_text("iyi")
        (kok_t / "onb.json").unlink()
        time.sleep(0.3)
        mod.update(hedef=kap / "dis_t.txt", icerik="d2", mtime_koru=False)
        _z, s6 = kos_t(artimli=False)
        _z, s7 = kos_t()
        ok("B19c depo DISI girdi adim kosarken degisti (mtime adim basladiktan sonra): GECERSIZ, "
           "sonraki kosu kosar", bool(s6.gecersiz) and "dis_t" in s6.gecersiz
           and s7.onbellek_yas is None, f"s6.gecersiz={s6.gecersiz[:120]!r} s7.sebep={s7.sebep[:80]!r}")

        # ── B20: CIKTI zincir sonunda yeniden ozetlenmez (disaridan degisiklik kutsanmaz)
        kok_c = kap / "proje_c"
        (kok_c / "ciktilar").mkdir(parents=True)
        yaz(kok_c / "p.py", '''
            from pathlib import Path
            (Path(__file__).resolve().parent / "ciktilar" / "out.txt").write_text("P")
            print("  1/1 dogrulama gecti")
        ''')
        yaz(kok_c / "r.py", 'print("  1/1 dogrulama gecti")\n')
        q_yaz = {"aktif": False}

        def gp(cal):
            r = cal([sys.executable, "p.py"], cwd=kok_c, timeout=120)
            return r.returncode == 0, r.stdout, r.stdout

        def gq(cal):
            r = cal([sys.executable, "r.py"], cwd=kok_c, timeout=120)
            if q_yaz["aktif"]:
                # izlenmeyen bir arac (kicad-cli gibi) P'nin ciktisini Q SIRASINDA yeniden yaziyor
                (kok_c / "ciktilar" / "out.txt").write_text("Q")
            return r.returncode == 0, r.stdout, r.stdout

        def kos_c(artimli=True, sona=None):
            z = ZO.Zincir(kok=kok_c, yol=kok_c / "onb.json", artimli=artimli, tetik=())
            z.kos("P", gp)
            z.kos("Q", gq)
            if sona:
                sona()
            z.bitir()
            return {s.baslik: s for s in z.sonuclar}

        kos_c(artimli=False)
        s = kos_c()
        ok("B20 on kosul: P ve Q onbellekten", all(x.onbellek_yas is not None for x in s.values()),
           str({b: x.sebep for b, x in s.items()}))
        kos_c(sona=lambda: (kok_c / "ciktilar" / "out.txt").write_text("X"))
        s = kos_c()
        ok("B20 zincir bittikten sonra (bitir'den once) disaridan degisen CIKTI kaydi kutsamaz: "
           "sonraki kosuda sahibi P KOSAR", s["P"].onbellek_yas is None, s["P"].sebep)
        q_yaz["aktif"] = True
        kos_c(artimli=False)
        s = kos_c()
        ok("B20c izlenmeyen yazar: Q SIRASINDA degisen (P'nin) cikti Q'nun yazimi sayilir — P ve Q "
           "onbellekten (ping-pong yok)", all(x.onbellek_yas is not None for x in s.values()),
           str({b: x.sebep for b, x in s.items()}))

        # ── B21/B22: ortam anahtari — RED listesi
        def anahtar(**ek):
            eski = {k: os.environ.get(k) for k in ek}
            try:
                for k, v in ek.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
                return ZO.genel_anahtar("X")
            finally:
                for k, v in eski.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        golge = kap / "golge"
        golge.mkdir()
        a0 = anahtar(PYTHONPATH=None, NODE_OPTIONS=None, HTTP_PROXY=None)
        ok("B21 kullanicinin PYTHONPATH'i ve NODE_OPTIONS'u anahtarda (her adim onlarla kosuyor)",
           anahtar(PYTHONPATH=str(golge)) != a0 and anahtar(NODE_OPTIONS="--require x.cjs") != a0)
        ok("B22 HTTP_PROXY (ve gerisi: RED listesi) anahtarda — vekil yerel sunucuya giden "
           "istegi kirar", anahtar(HTTP_PROXY="http://127.0.0.1:9") != a0
           and anahtar(ARDUINO_DIRECTORIES_DATA=str(golge)) != a0)
        ok("B22b oturuma ozgu degisken (CLAUDE_CODE_SESSION_ID, VSCODE_PID) anahtari DEGISTIRMEZ "
           "(yeni oturum onbellegi bosa cikarmasin)",
           anahtar(CLAUDE_CODE_SESSION_ID="baska-oturum", VSCODE_PID="1") == a0)
        # davranis: PYTHONPATH degisince adim kosar
        kos_t(artimli=False)
        os.environ["PYTHONPATH"] = str(golge)
        try:
            _z, s8 = kos_t()
        finally:
            if eski_ortam["PYTHONPATH"] is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = eski_ortam["PYTHONPATH"]
        ok("B21 kullanici PYTHONPATH kurunca adim onbellekten GELMEZ",
           s8.onbellek_yas is None and "genel anahtar" in s8.sebep, s8.sebep)

        # ── B23: ana surecin adim ortamini kuran dosyalari anahtarda
        ana = kap / "ana"
        for d in set(ZO.ANA_SUREC) | {"ozel_ortam.py"}:
            (ana / d).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(BURASI / d, ana / d)
        a1 = ZO.genel_anahtar("X", burasi=ana)
        (ana / "ozel_ortam.py").write_text((ana / "ozel_ortam.py").read_text(encoding="utf-8")
                                          + "\n# degisti\n", encoding="utf-8")
        ok("B23 ozel_ortam.py (adimlarin LOCALAPPDATA'sini kuran) degisince genel anahtar degisir",
           ZO.genel_anahtar("X", burasi=ana) != a1)
        r = subprocess.run([sys.executable, "-c",
                            "import json, sys; sys.path.insert(0, sys.argv[1]); import dogrula3; "
                            "print(json.dumps([getattr(m, '__file__', None) or '' "
                            "for m in list(sys.modules.values())]))", str(BURASI)],
                           capture_output=True, text=True, cwd=str(BURASI), timeout=120)
        try:
            yuklu = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            yuklu = []
        b = str(BURASI.resolve()).lower()
        yerel = sorted({os.path.relpath(f, BURASI).replace(os.sep, "/") for f in yuklu
                        if f and str(Path(f).resolve()).lower().startswith(b + os.sep)
                        and f.endswith(".py")})
        eksik = [f for f in yerel if f not in ZO.ANA_SUREC and f not in ZO.ANAHTAR_DISI]
        ok("B23 dogrula3'un import ettigi HER depo modulu ya ANA_SUREC'te (anahtar) ya ANAHTAR_DISI'nda "
           "(gerekceli)", bool(yerel) and not eksik and "ozel_ortam.py" in yerel,
           f"yuklu={yerel} eksik={eksik}")

        # ── B24: golge modul (uretim/gzip.py gibi)
        kok_s = kap / "proje_s"
        # ⚠ json DEGIL: iz kancasi json'u surec acilisinda zaten yukluyor (sys.modules) — golge
        #   hic devreye girmezdi. Kancanin yuklemedigi bir standart modul.
        yaz(kok_s / "s.py", '''
            import colorsys
            print("  1/1 dogrulama gecti", colorsys.rgb_to_hsv(1, 0, 0))
        ''')

        def kos_s(artimli=True):
            z = ZO.Zincir(kok=kok_s, yol=kok_s / "onb.json", artimli=artimli, tetik=())
            g = govde(kok_s, "s.py")
            s = z.kos("S", g)
            z.bitir()
            return s
        kos_s(artimli=False)
        on = kos_s()
        yaz(kok_s / "colorsys.py", 'raise ImportError("GOLGE colorsys")\n')
        try:
            sg = kos_s()
        finally:
            (kok_s / "colorsys.py").unlink()
        ok("B24 betigin dizinine standart kutuphaneyi GOLGELEYEN modul (colorsys.py) eklenince adim "
           "KOSAR (ve kirmiziyi gorur)", on.onbellek_yas is not None and sg.onbellek_yas is None
           and not sg.tamam, f"on={on.sebep!r} sg={sg.sebep[:100]!r}")

        # ── B25: ngspice spinit / ~/.spiceinit
        iz = ZO.Iz()
        iz.dll.add(r"C:\Program Files\KiCad\10.0\bin\ngspice.dll")
        g = ZO.cozumle(iz, kok_s, [], ZO.Kapsam(kok_s))
        ok("B25 ngspice.dll yuklenince ~/.spiceinit ve spinit dosya girdisi (C duzeyinde okunuyor)",
           any(p.endswith(".spiceinit") for p in g.dosya)
           and any(p.lower().endswith("spinit") for p in g.dosya), str(sorted(g.dosya))[:200])
    finally:
        for k, v in eski_ortam.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        M.guvenli_sil(kap)


KIRILGAN_PY = '''
import os, sys
from pathlib import Path
isaret = Path(os.environ["ADIM_COKME"]) / "taban_bir_kez"
if not isaret.exists():
    isaret.write_text("1")
    print("  0/1 dogrulama gecti")
    sys.exit(1)
print("  1/1 dogrulama gecti")
# k1
'''

COKME_PY = '''
import os, sys
from pathlib import Path
MUT_GECICI = False
MUT_KALICI = False
isaret = Path(os.environ["ADIM_COKME"]) / "coktu"
if MUT_GECICI and not isaret.exists():
    isaret.write_text("1")
    raise PermissionError("[WinError 5] sahte paylasim ihlali")
if MUT_KALICI:
    raise RuntimeError("deterministik cokme")
print("  [OK] c")
print("  1/1 dogrulama gecti")
'''

SEMAFOR_PY = '''
import os, time
from pathlib import Path
(Path(os.environ["ADIM_KAYIT"]) / f"{os.getpid()}-{time.time_ns()}.txt").write_text("basladi")
time.sleep(float(os.environ.get("ADIM_UYKU", "30")))
print("  1/1 dogrulama gecti")
# s1
# s2
# s3
# s4
'''


def test_inceleme_kosucu() -> None:
    print("\n  ── C) inceleme: paralel mutasyon kosucusu")
    import threading
    kap = Path(tempfile.mkdtemp(prefix="olcum-hizek-"))
    eski_yerel = os.environ.get("LOCALAPPDATA")
    try:
        kok = sahte_mut_proje(kap)
        sahte_yerel = kap / "gercek_yerel"
        yaz(sahte_yerel / "Arduino15" / "nobet.txt", "arac")
        yaz(sahte_yerel / "Python" / "surum.txt", "3.14")
        yaz(sahte_yerel / "olcum-karti" / "kopru.txt", "kullanicinin")
        os.environ["LOCALAPPDATA"] = str(sahte_yerel)
        ortam = dict(os.environ, LOCALAPPDATA=str(sahte_yerel), ADIM_ORTAM_DENETLE="1")
        sessiz: list = []

        def artik():
            return sorted(p.name for p in kap.iterdir() if p.name.startswith(M.ISCI_ONEK)
                          or p.name.startswith("_ic"))

        # ── A9: IC ICE ozel LOCALAPPDATA (B3/B23 mutasyonu iscide dogrula3 kosuyor)
        ad_link = sahte_yerel / "Application Data"          # LOCALAPPDATA'nin KENDISINE baglanti
        ozel_ortam.baglanti_kur(ad_link, sahte_yerel)
        isci = None
        try:
            isci = M.Isci(1, kok, {"LOCALAPPDATA": str(sahte_yerel)}, M._Ortak(1, sessiz.append))
            ic = ozel_ortam.yerel_kur(kap / "_ic_yerel" / "yerel", isci.ortam["LOCALAPPDATA"])
            gorunen = sorted(os.listdir(ic))
            sizan = [x for x in gorunen if (ic / x / "olcum-karti" / "kopru.txt").exists()
                     or (ic / x / "kopru.txt").exists()]
            ok("A9 ic ice ozel LOCALAPPDATA (iscinin dizininden kurulan) Arduino15 ve Python'u "
               "GORUR (eskiden yalniz Temp: ESP32 cekirdegi yok, Python yeniden indirilebilirdi)",
               (ic / "Arduino15" / "nobet.txt").exists() and (ic / "Python" / "surum.txt").exists(),
               str(gorunen))
            ok("A9 korunan olcum-karti hicbir yoldan gorunmez; LOCALAPPDATA'nin KENDISINE giden "
               "baglanti ('Application Data') izlenmez (iscide de ic icede de)",
               not (ic / "olcum-karti").exists() and not sizan
               and not (Path(isci.ortam["LOCALAPPDATA"]) / "Application Data").exists()
               and "Application Data" not in gorunen, f"sizan={sizan} gorunen={gorunen}")
        finally:
            ozel_ortam.guvenli_sil(kap / "_ic_yerel")
            if isci is not None:
                isci.temizle()
            os.rmdir(ad_link)
        ok("A9 temizlik: ic ice dizinler silindi, baglanti hedefleri yerinde",
           not artik() and (sahte_yerel / "Arduino15" / "nobet.txt").exists(), str(artik()))

        # ── A10: kopyalayici + zincir AYNI agacta
        (kok / "uretim" / "_b2_bol_hv").mkdir()
        (kok / "uretim" / "_b2_bol_hv" / "x.raw").write_text("spice")
        (kok / "kopru" / "_chk1").mkdir(parents=True)
        (kok / "kopru" / "arsiv" / "_b1").mkdir(parents=True)
        (kok / "kopru" / "arsiv" / "_b1" / "olcum.satir").write_text("kullanicinin")
        hedef = kap / "_mutpT-1-1"
        k = M.kopyala(hedef, kok)
        ok("A10 kopya zincirin cop dizinlerini (uretim/_b*, kopru/_chk*) TASIMAZ; kopru/arsiv "
           "altindaki ayni adli dizin (kullanicinin olcumu) tasinir",
           not (k / "uretim" / "_b2_bol_hv").exists() and not (k / "kopru" / "_chk1").exists()
           and (k / "kopru" / "arsiv" / "_b1" / "olcum.satir").exists()
           and (k / "uretim" / "adim.py").exists())
        M.guvenli_sil(k)
        asil = shutil.copytree
        sayac = {"n": 0}

        def bozuk_copytree(src, dst, *a, **kw):
            sayac["n"] += 1
            if sayac["n"] == 1:
                os.makedirs(dst)
                (Path(dst) / "yarim.txt").write_text("yarim")
                raise shutil.Error([(str(src), str(dst), "[WinError 3] kaybolan girdi")])
            return asil(src, dst, *a, **kw)
        shutil.copytree = bozuk_copytree
        try:
            try:
                k = M.kopyala(hedef, kok)
                hata = None
            except Exception as h:              # noqa: BLE001
                k, hata = None, h
        finally:
            shutil.copytree = asil
        ok("A10 canli agacta kaybolan girdi (shutil.Error) kosuyu DUSURMEZ: yarim kopya silinip "
           "yeniden denenir", hata is None and k is not None and (k / "uretim" / "adim.py").exists()
           and not (k / "yarim.txt").exists() and sayac["n"] >= 2, f"hata={hata!r} n={sayac['n']}")
        if k is not None:
            M.guvenli_sil(k)
        # gercek esanli zincir benzetimi: _b* dizinleri durmadan kurulup siliniyor
        dur = threading.Event()
        cop_hata = []

        def cop_uret():
            n = 0
            while not dur.is_set():
                d = kok / "uretim" / f"_b9_x{n % 7}"
                try:
                    d.mkdir(exist_ok=True)
                    for j in range(20):
                        (d / f"{j}.raw").write_text("x" * 100)
                    shutil.rmtree(d, ignore_errors=True)
                except OSError as h:
                    cop_hata.append(repr(h))
                n += 1
        t = threading.Thread(target=cop_uret)
        t.start()
        hatalar = []
        try:
            for n in range(8):
                try:
                    k = M.kopyala(kap / f"_mutpT-2-{n}", kok)
                    if list((k / "uretim").glob("_b9_*")):
                        hatalar.append(f"{n}: _b9 kopyalandi")
                    M.guvenli_sil(k)
                except Exception as h:          # noqa: BLE001
                    hatalar.append(f"{n}: {h!r}"[:120])
        finally:
            dur.set()
            t.join()
        ok("A10 zincir adimi _b* dizinlerini kurup silerken 8 kopyanin hicbiri cokmez ve hicbiri "
           "onlari tasimaz", not hatalar, str(hatalar[:3]))
        for d in kok.rglob("_b9_x*"):
            shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(kok / "uretim" / "_b2_bol_hv", ignore_errors=True)
        shutil.rmtree(kok / "kopru", ignore_errors=True)

        # ── A11: ANLIK kopya — kosu basladiktan sonra canli agac degisse de sonuc ayni
        bozuldu = threading.Event()

        def cikis_bozan(satir):
            sessiz.append(satir)
            if "taban" in satir and not bozuldu.is_set():
                (kok / "uretim" / "veri.txt").write_text("bozuk\n")
                bozuldu.set()
        try:
            s = M.mutasyonlari_kos(SAHTE_MUT, kok, 3, ortam, cikis=cikis_bozan)
        finally:
            (kok / "uretim" / "veri.txt").write_text("dogru\n")
        d = {r["i"]: r["durum"] for r in s["sonuclar"]}
        ok("A11 isciler kosu basindaki ANLIK kopyadan kopyalar: ilk tabandan sonra canli agac "
           "bozulsa da taban yesil ve karar kumesi ayni", bozuldu.is_set()
           and s["taban_kirmizi"] is None and d == BEKLENEN,
           f"{d} taban={(s['taban_kirmizi'] or [None])[0]}")
        ok("A11 anlik kopya da kosu sonunda silinir", not artik(), str(artik()))

        # ── A12: COKME (iddiasiz kirmizi) = SUPHELI -> tek basina yeniden kosulur
        cokme_d = kap / "cokme_isaret"
        cokme_d.mkdir()
        yaz(kok / "uretim" / "cokme.py", COKME_PY)
        yaz(kok / "uretim" / "kirilgan.py", KIRILGAN_PY)
        ortam_c = dict(ortam, ADIM_COKME=str(cokme_d))
        muts = [("XC", "cokme.py", "uretim/cokme.py", "MUT_GECICI = False", "MUT_GECICI = True",
                 "yalniz ilk kosuda coker (paralel yukte paylasim ihlali gibi)"),
                ("XC", "cokme.py", "uretim/cokme.py", "MUT_KALICI = False", "MUT_KALICI = True",
                 "her kosuda coker")]
        s = M.mutasyonlari_kos(muts, kok, 2, ortam_c, cikis=sessiz.append)
        r = {x["i"]: x for x in s["sonuclar"]}
        ok("A12 iddiasiz COKME yalniz ilk kosuda: tek basina yeniden kosulur, karar ikinci kosunun "
           "(KACTI) — eskiden sahte YAKALANDI",
           r.get(1, {}).get("durum") == "KACTI" and bool(r.get(1, {}).get("cokme_ilk")),
           str(r.get(1))[:200])
        ok("A12 her kosuda coken mutasyon yeniden kosulduktan sonra YAKALANDI; teshis SON "
           "istisna satiri (Traceback basligi degil)",
           r.get(2, {}).get("durum") == "YAKALANDI" and bool(r.get(2, {}).get("cokme_ilk"))
           and "RuntimeError: deterministik cokme" in r.get(2, {}).get("ilk_kirmizi", ""),
           str(r.get(2))[:200])
        ok("A16 teshis: [!!] yoksa cokmenin son istisna satiri",
           M.teshis("x\nTraceback (most recent call last):\n  File \"a\", line 1\n    f()\n"
                    "PermissionError: [WinError 5] Erisim engellendi\n")
           == "cokme: PermissionError: [WinError 5] Erisim engellendi"
           and M.teshis("  [OK] KIRMIZI degil\n  [!!] gercek\n") == "[!!] gercek")

        # ── A13: kirmizi taban BIR KEZ yeniden olculur
        s = M.mutasyonlari_kos([("XK", "kirilgan.py", "uretim/kirilgan.py", "# k1", "# K1",
                                 "kacar")], kok, 1, ortam_c, cikis=sessiz.append)
        ok("A13 bir kez kirmizi olan taban yeniden olculur; ikincisi yesilse kosu surer",
           s["taban_kirmizi"] is None and [x["durum"] for x in s["sonuclar"]] == ["KACTI"],
           str((s["taban_kirmizi"] or [None])[0]))

        ev = threading.Event()
        ev.set()
        try:
            M.kosut(kok, "adim.py", ortam, durdur=ev)
            durduruldu = False
        except M.Durduruldu:
            durduruldu = True
        ok("A5d durdur (Ctrl+C) kuruluyken kosut YENI SUREC ACMAZ", durduruldu)

        # ── A15: sonuc yazimi
        cikti: list = []
        m0 = SAHTE_MUT[0]
        rc = M.sonuc_kodu({"sonuclar": [], "taban_kirmizi": None, "sizinti": [],
                           "kalan_dizin": [kap / "_mutp2-9028-682360000"], "kesildi": True},
                          [m0], cikti.append)
        metin = "\n".join(cikti)
        ok("A15 Ctrl+C'de silinemeyen kopya ADIYLA yazilir; 'kopyalar temizlendi' DENMEZ",
           rc == 130 and "_mutp2-9028-682360000" in metin and "temizlendi" not in metin, metin)
        cikti.clear()
        rc = M.sonuc_kodu({"sonuclar": [{"i": 1, "m": m0, "durum": "YAKALANDI", "rc": 1,
                                         "sayim": [], "sizinti": 2}],
                           "taban_kirmizi": None, "sizinti": [], "kalan_dizin": [],
                           "kesildi": False}, [m0], cikti.append)
        ok("A15 mutasyon basina gorulen Edge SIZINTISI kosuyu KIRMIZI yapar (son taramada hicbir "
           "sey kalmasa da)", rc == 1 and "SIZDI" in "\n".join(cikti), "\n".join(cikti))

        # ── A17: bayat _mutp* supurmesi — sahibi OLU olan silinir, CANLI olanin dizinine dokunulmaz
        p = subprocess.Popen([sys.executable, "-c", "pass"])
        p.wait()
        olu, canli = p.pid, os.getpid()
        hedef_d = kap / "baglanti_hedefi"
        yaz(hedef_d / "deger.txt", "kalmali")
        d_olu = kap / f"_mutp9-{olu}-123"
        d_canli = kap / f"_mutp8-{canli}-123.ozel"
        for d in (d_olu, d_canli):
            d.mkdir()
            ozel_ortam.baglanti_kur(d / "Arduino15", hedef_d)
            eski_t = time.time() - 3600
            os.utime(d, (eski_t, eski_t))
        ok("A17 ad -> sahip pid", ozel_ortam.sahip_pid(d_olu.name, "_mutp") == olu
           and ozel_ortam.sahip_pid(d_canli.name, "_mutp") == canli
           and ozel_ortam.sahip_pid("_zincir-yerel-4321-99", "_zincir-yerel-") == 4321
           and ozel_ortam.sahip_pid("_mutpA-77-5-1", "_mutp") == 77)
        M.mutasyonlari_kos(SAHTE_MUT[:1], kok, 1, ortam, cikis=sessiz.append)
        ok("A17 kosu basinda sahibi olmus bayat _mutp* dizini supurulur (baglanti hedefi yerinde); "
           "sahibi CANLI olan (uzun suren baska bir kosu) KORUNUR",
           not d_olu.exists() and d_canli.exists() and (hedef_d / "deger.txt").exists(),
           f"olu={d_olu.exists()} canli={d_canli.exists()}")
        ozel_ortam.guvenli_sil(d_canli)

        # ── A14: kopru durum.json'u paylasim ihlalinde yeniden dener
        sys.path.insert(0, str(KOK / "kopru"))
        import kayit_esitle as KE
        dd = kap / "durum_test"
        dd.mkdir()
        hedef_j, gec = dd / "durum.json", dd / "durum.tmp"
        hedef_j.write_text("eski")
        gec.write_text("yeni")
        acik = open(hedef_j, "r")                       # paylasim: OKU+YAZ, SIL yok
        try:
            os.replace(gec, hedef_j)
            on_kosul = False
            gec.write_text("yeni")
        except PermissionError:
            on_kosul = True
        threading.Timer(0.3, acik.close).start()
        try:
            KE.atomik_degistir(gec, hedef_j)
            sonuc = hedef_j.read_text()
        except OSError as h:
            sonuc = repr(h)
        finally:
            time.sleep(0.4)
            acik.close()
        ok("A14 kopru durum.json: hedef acikken os.replace PermissionError (on kosul) ve "
           "atomik_degistir kapaninca YAZAR (eskiden test 4 iscide coktu)",
           on_kosul and sonuc == "yeni", f"on_kosul={on_kosul} sonuc={sonuc!r}")

        # ── A6b: varsayilan isci sayisi makine yukune gore
        n = os.cpu_count() or 1
        taban = max(1, min(4, n - 2))
        y = M.sistem_yuku(0.2)
        ok("A6b varsayilan isci: bosta min(4, cekirdek-2), tam yukte 1; yuk olculebiliyor",
           M.varsayilan_paralel(0.0) == taban and M.varsayilan_paralel(1.0) == 1
           and M.varsayilan_paralel(None) == taban and (y is None or 0.0 <= y <= 1.0)
           and 1 <= M.varsayilan_paralel() <= taban, f"yuk={y} taban={taban}")

        # ── A5b/A5c: Ctrl+C semafor beklerken ve kopyalama sirasinda
        if sys.platform == "win32":
            test_kesme(kap, kok)
    finally:
        if eski_yerel is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = eski_yerel
        M.guvenli_sil(kap)


def _kes_kos(kap: Path, surucu_metin: str, hazir, sinir: float = 60):
    surucu = yaz(kap / "surucu_k.py", surucu_metin)
    p = subprocess.Popen([sys.executable, str(surucu)], cwd=kap,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace")
    son = time.time() + sinir
    while time.time() < son and not hazir():
        time.sleep(0.05)
    basladi = hazir()
    t_kes = time.time()
    p.send_signal(signal.CTRL_BREAK_EVENT)
    try:
        cikti, _ = p.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        p.kill()
        cikti, _ = p.communicate()
    return basladi, t_kes, time.time() - t_kes, cikti


def test_kesme(kap: Path, kok: Path) -> None:
    # A5b: 4 isci, 4 AGIR + 1 duz mutasyon -> 2 tarayici kosar, 2 isci semaforda bekler
    yaz(kok / "uretim" / "semafor_sahte.py", SEMAFOR_PY)
    kayit = kap / "semafor_kayit"
    kayit.mkdir()
    muts = ([("XS", "semafor_sahte.py", "uretim/semafor_sahte.py", f"# s{n}", f"# S{n}", "kacar")
             for n in range(1, 5)] + [SAHTE_MUT[0]])
    basladi, t_kes, sure, cikti = _kes_kos(kap, f'''
        import os, sys
        sys.path.insert(0, {str(BURASI)!r})
        import mutasyon as M
        from pathlib import Path
        M.sinyal_kur()
        M.AGIR = set(M.AGIR) | {{"XS"}}
        ortam = dict(os.environ, ADIM_KAYIT={str(kayit)!r}, ADIM_UYKU="30")
        r = M.mutasyonlari_kos({muts!r}, Path({str(kok)!r}), 4, ortam)
        print("KESILDI=" + str(r["kesildi"]))
        print("KALAN=" + str(len(r["kalan_dizin"])))
    ''', lambda: len(list(kayit.iterdir())) >= 2)
    time.sleep(1.0)
    sonra = [f for f in kayit.iterdir() if f.stat().st_mtime > t_kes + 0.05]
    kalan = [x.name for x in kap.iterdir() if x.name.startswith(M.ISCI_ONEK)]
    ok("A5b Ctrl+C: semaforda bekleyen isciler YENI tarayici kosusu BASLATMAZ; kopyalar silinir",
       basladi and "KESILDI=True" in cikti and not sonra and not kalan and sure < 60,
       f"basladi={basladi} sonradan={len(sonra)} kalan={kalan} sure={sure:.1f}s "
       f"cikti={cikti[-160:]!r}")

    # A5c: kopyalama SIRASINDA kesme (buyuk agac)
    kok_b = kap / "buyuk"
    for i in range(30):
        for j in range(60):
            yaz(kok_b / "uretim" / f"d{i}" / f"f{j}.txt", "x" * 64)
    yaz(kok_b / "uretim" / "adim.py", ADIM_PY)
    yaz(kok_b / "uretim" / "veri.txt", "dogru\n")
    bas = kap / "baslama"
    bas.mkdir()
    ortak_on = M.ISCI_ONEK + "1-"
    basladi, _t, sure, cikti = _kes_kos(kap, f'''
        import os, sys
        sys.path.insert(0, {str(BURASI)!r})
        import mutasyon as M
        from pathlib import Path
        M.sinyal_kur()
        ortam = dict(os.environ, ADIM_UYKU="30", ADIM_BASLAMA={str(bas)!r})
        r = M.mutasyonlari_kos({SAHTE_MUT[:2]!r}, Path({str(kok_b)!r}), 2, ortam)
        print("KESILDI=" + str(r["kesildi"]))
    ''', lambda: any(x.name.startswith(ortak_on) and not x.name.endswith(".ozel")
                     for x in kap.iterdir()))
    kalan = [x.name for x in kap.iterdir() if x.name.startswith(M.ISCI_ONEK)]
    ok("A5c Ctrl+C isci KOPYALARKEN: kosu kesilir, hicbir adim baslamaz, kalinti yok",
       basladi and "KESILDI=True" in cikti and not list(bas.iterdir()) and not kalan and sure < 60,
       f"basladi={basladi} adim={len(list(bas.iterdir()))} kalan={kalan} sure={sure:.1f}s "
       f"cikti={cikti[-160:]!r}")


def main() -> int:
    print("=" * 78)
    print("  HIZ — artimli zincir + paralel mutasyon kosucusu (sahte projelerde)")
    print("=" * 78)
    t0 = time.time()
    test_yapisal()
    test_artimli()
    test_inceleme_zincir()
    test_paralel()
    test_inceleme_kosucu()
    print(f"\n  ({time.time() - t0:.0f} s)")
    print()
    print(f"  {gecti}/{gecti + kaldi} dogrulama gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
