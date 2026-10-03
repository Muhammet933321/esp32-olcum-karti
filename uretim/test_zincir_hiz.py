# -*- coding: utf-8 -*-
"""HIZ (2026-10-03): artimli zincir + paralel mutasyon kosucusu — KENDI testleri.

    python test_zincir_hiz.py            (~40 s)

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
        ok("A6 varsayilan isci sayisi min(4, cekirdek-2), en az 1",
           M.varsayilan_paralel() == max(1, min(4, (os.cpu_count() or 1) - 2)))
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
        olay = []
        for f in kayit.iterdir():
            b, z = f.read_text().split()
            olay += [(float(b), 1), (float(z), -1)]
        en_cok = an = 0
        for _z, d in sorted(olay):
            an += d
            en_cok = max(en_cok, an)
        ok(f"A8 AGIR (tarayici) kosulari 4 iscide bile en fazla {M.TARAYICI_AZAMI} esanli",
           len(olay) == 16 and en_cok <= M.TARAYICI_AZAMI
           and all(r["durum"] == "KACTI" for r in s["sonuclar"]),
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
        var = (B / "bayrak.txt").exists()
        adlar = sorted(os.listdir(B / "liste_dizin"))
        print(f"  1/1 dogrulama gecti  bayrak={var} adlar={adlar}")
    ''')
    (kok / "liste_dizin").mkdir()
    yaz(kok / "liste_dizin" / "x.txt", "x")
    yaz(kok / "f.py", '''
        from pathlib import Path
        B = Path(__file__).resolve().parent
        (B / "cikti_f.txt").write_text("uretildi")
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
        ok("B5/B15 digerleri sinirli (HER ZAMAN listesinde yalniz D, H, I)",
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
                       lambda: (kok / "bayrak.txt").write_text("1"), ["E"])
        tek_degisiklik("B10b listelenen dizine dosya eklendi -> E kosar",
                       lambda: (kok / "liste_dizin" / "y.txt").write_text("y"), ["E"])
        tek_degisiklik("B11 adimin ciktisi silindi -> F kosar (cikti yeniden uretilir)",
                       lambda: (kok / "cikti_f.txt").unlink(), ["F"])
        ok("B11 F ciktiyi yeniden uretti", (kok / "cikti_f.txt").exists())
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
            print(f"  {int(ozel)}/1 dogrulama gecti", v)
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
        s1, s2 = kos_y(), kos_y()
        (gercek / "Arduino15" / "cekirdek.txt").write_text("c2")
        s3 = kos_y()
        ok("B18 adim OZEL LOCALAPPDATA'da kosar, Arduino15'i junction'dan okur, GERCEK dizine "
           "yazmaz", s1.tamam and "c1" in s1.cikti and not (gercek / "olcum-karti").exists(),
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


def main() -> int:
    print("=" * 78)
    print("  HIZ — artimli zincir + paralel mutasyon kosucusu (sahte projelerde)")
    print("=" * 78)
    t0 = time.time()
    test_yapisal()
    test_artimli()
    test_paralel()
    print(f"\n  ({time.time() - t0:.0f} s)")
    print()
    print(f"  {gecti}/{gecti + kaldi} dogrulama gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
