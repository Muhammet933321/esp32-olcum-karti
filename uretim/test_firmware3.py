# -*- coding: utf-8 -*-
"""B6 — Asama 3 firmware'i: derleme + ikilide olu kod denetimi.

    python test_firmware3.py

B4/B5 olcum MATEMATIGINI dogruluyor (olcum3.h, AVR emulatorunde).
Bu adim onu CALISTIRAN programi dogruluyor:

  1. Gercek ESP32-S3 derleyicisiyle, dogru FQBN ile derleniyor mu
  2. -Wall -Wextra ile UYARISIZ mi
  3. Flash ve RAM payi yeterli mi
  4. IKILIDE OLU KOD var mi — derleyicinin attigi dallar
     (Asama 1'de osiloskop tetiklemesi tam boyle olu koda donusmustu:
      tek cagri (0,0) oldugu icin derleyici komple atmisti, S9 yakaladi)
  5. Protokol dizeleri firmware'de GERCEKTEN var mi — arayuz bunlara
     dayanacak. Asama 2'de arayuz ile firmware komutlari AYRISMISTI
     (DEVIR 4.1); bu denetim onu tekrarlanamaz kiliyor.
  6. 1F (S2): skop_olc ikilide ayri fonksiyon ve icinde kaynasmis kayan
     nokta komutu (madd.s/msub.s) YOK — kart AVR basvurusuyla ayni sonuc.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hedef2                                    # noqa: E402
import tasarim3_sabit as T                       # noqa: E402
from tezgah import tezgah                        # noqa: E402
import gecici                                   # noqa: E402

BURASI = Path(__file__).parent
KOK = BURASI.parent
ESKIZ = KOK / "kod" / "olcum-karti-a3"
ARDUINO_CLI = KOK.parents[1] / ".araclar" / "arduino-cli.exe"

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


# İkilide BULUNMASI gereken dizeler. Her biri bir DALIN derlendigini
# kanitliyor — derleyici erisilemeyen dali atarsa dize de gider.
BEKLENEN_DIZELER = [
    (b"D %.4f %.6f %.5f %.4f %.7f %lu %lu %u", "olcum satiri bicimi"),
    (b"PSRAM: ", "PSRAM raporu (DEVIR 4.9)"),
    # B22.1 — her biri bir DALIN derlendigini kanitliyor
    (b"! g: gerilim degeri gerekli", "ciplak `g` reddi (K3 tuglalama)"),
    (b"! i: akim degeri gerekli", "ciplak `i` reddi"),
    (b"! f: frekans gerekli", "ciplak `f` reddi (sessiz DC gecisi)"),
    (b"R: onay gerekli", "R! onay eki — kazara fabrika sifirlama olmasin"),
    (b"FABRIKA AYARLARI yuklendi", "fabrika sifirlama dali (kurtarma yolu)"),
    (b"K %lu %lu %lu", "blokaj sayaci satiri"),
    (b"pil egri tamponu: ", "tampon raporu sureyi SAYIDAN turetiyor"),
    (b"! Pr: 0 (her ornek), 1, 5, 20 ya da 50 olmali", "PT3 Pr reddi dali"),
    (b"* pil DCIR olcumu KAPALI", "PT5 Pd0 dali"),
    (b"pilayar", "PT5 DCIR ayarinin NVS ad alani"),
    (b"OCV evresi bitti", "PT2 OCV evresinden yuke gecis dali"),
    (b"! Ph: 0..1000 mOhm", "HT1 Ph reddi dali"),
    (b"* pil hat direnci ", "HT1 Ph onayi dali"),
    (b"hat direnci olayi kuyrukta DUSTU", "HT3 KO_PIL_HAT olayi gonderimi"),
    # B22.4 — her biri bir SAVUNMA DALININ derlendigini kanitliyor
    # 4B (PC8): "event: kopru" (kopru kayitliyken ikinci SSE istemcisi reddi) KALKTI —
    #   spec §5 "4 istemci, ret kalkar"; artik BULUNMAMALI listesinde.
    (b"event: dolu", "SSE yuvasi dolu — sessiz kapatma yok"),
    (b": kalp", "SSE kalp atisi (NAT/vekil zaman asimi)"),
    (b"X-Olcum basligi gerekli", "CSRF: ozel baslik dali"),
    (b"Host reddedildi", "DNS rebinding korumasi dali"),
    (b"gecersiz oturum jetonu", "jeton denetimi dali"),
    (b"OLCUM-KARTI-", "AP SSID oneki (kendi agini kurma dali)"),
    (b"web parolasi YOK", "parolasiz calisma UYARISI"),
    (b"NA: WPA2 en az 8 karakter", "AP parolasi uzunluk denetimi dali"),
    (b"gerilim sifiri", "gerilim sifir kalibrasyonu dali"),
    (b"gerilim kazanci", "gerilim kazanc kalibrasyonu dali"),
    (b"kazanc kalibrasyonu reddedildi", "kazanc REDDETME dali"),
    (b"akim sifiri", "akim sifiri dali"),
    (b"akim kalibrasyonu reddedildi", "akim REDDETME dali"),
    (b"menzil ", "menzil degistirme dali"),
    (b"otomatik menzil ", "otomatik menzil dali"),
    (b"enerji sifirlandi", "enerji sifirlama dali"),
    (b"beklenen: 0x48", "I2C tarama dali"),
    (b"S2 ", "osiloskop protokol basligi"),
    # --- B8 hizli yol
    (b"W ", "hizli yol guc satiri"),
    (b"hizli yol: 2 kanalli yapilandirma basarisiz", "2 kanal kurulum dali"),
    (b"hizli yol: yeterli ornek yok", "yetersiz ornek dali"),
    (b"pencere ", "pencere yanliligi uyarisi"),
    (b"cevrim (1 cevrimin altinda yanlilik BUYUK)", "yanlilik uyarisi dali"),
    (b"! tetiklenemedi", "osiloskop tetikleme dali"),
    (b"! skop: t ta tb", "osiloskop komut dali"),
    (b"YUKSEK", "menzil adi"),
    (b"NORMAL", "menzil adi"),
]

# BULUNMAMASI gerekenler — Asama 2'den kalma, artik yanlis olan seyler
BULUNMAMALI = [
    # B22.1: sure elle yazilmamali — PIL_IC_KAPASITE 5400 = 1.5 saat iken
    # acilis satiri "(2 saat)" diyordu, yani kullaniciya yanlis bilgi.
    (b"ic RAM'de (2 saat)", "elle yazilmis tampon suresi"),
    (b"v_duzeltme", "Asama 2'nin kalibrasyon alani (artik kazanc/sifir_ham)"),
    (b"tek yonlu", "tek yonlu olcum notu"),
    # 4B (PC8): kopru kaydi ve ikinci istemci reddi kalkti — ikilide izi kalmamali
    (b"event: kopru", "kopru kayitliyken ikinci /akis reddi (4B'de kalkti)"),
    (b"POST /kopru", "kok sayfadaki /kopru ucu tanitimi (4B'de kalkti)"),
]


# 1F (S2): ikilide skop_olc'un icinde BULUNMAMASI gereken kaynasmis kayan nokta
# komutlari (Xtensa FPU: a*b+c tek yuvarlamayla). `madd.s`/`msub.s` ESP32-S3'te
# B73 capraz uygulamasi sirasinda skop_olc'ta goruldu (Vrms/Vac toplamlari, %10/%90
# esikleri): kart AVR basvurusundan ayrisiyordu.
KAYNASMIS = re.compile(r"\b(madd|msub|maddn|msubn)\.s\b")
KAYAN_NOKTA = re.compile(r"\b[a-z0-9]+\.s\b")
KAYNASMASIZ_FONKSIYONLAR = ("skop_olc", "skop_kesisim", "skop_u64_float")


def _xtensa_arac(ad: str) -> Path | None:
    """ESP32 cekirdeginin kurdugu Xtensa arac zincirinden bir ikili (en yeni surum)."""
    kok = Path.home() / "AppData/Local/Arduino15/packages/esp32/tools/esp-x32"
    adaylar = sorted(kok.glob(f"*/bin/xtensa-esp32s3-elf-{ad}.exe"))
    return adaylar[-1] if adaylar else None


def kaynasma_denetimi(gec_dizin: Path) -> None:
    """1F (S2): skop_olc ikilide AYRI fonksiyon ve icinde madd.s/msub.s YOK.

    Kaynak `olcum2.h` -> `skop_olc.h` blogu `#pragma GCC optimize
    ("fp-contract=off")` ile derleniyor. Pragma'nin GERCEKTEN islediginin kaniti
    kaynak degil ikili: sokulmus fonksiyonda kaynasmis komut sayisi 0 olmali.
    Fonksiyon bir cagirana GOMULMUS olsaydi bu denetim BOS kalirdi (sembol yok,
    komut cagiranin icinde, onun ayariyla) — o yuzden sembolun varligi da iddia.
    ⚠ sqrtf kutuphanede (`__ieee754_sqrtf`: sqrt0.s + maddn.s + divn.s, ISA'nin
    dogru yuvarlanmis dizisi); skop_olc onu CAGIRIYOR. Derleyici bir gun o diziyi
    skop_olc'un icine acarsa buradaki maddn.s kaynasma DEGIL — ayirt etmek gerekir.
    """
    print("\n--- 2b. 1F (S2): skop_olc'ta kaynasmis kayan nokta (madd.s) YOK ----")
    elf = next(gec_dizin.glob("*.ino.elf"), None)
    nm, objdump = _xtensa_arac("nm"), _xtensa_arac("objdump")
    ok("1F S2: .elf ve Xtensa nm/objdump bulundu",
       elf is not None and nm is not None and objdump is not None,
       f"{objdump.parent.parent.name if objdump else 'objdump YOK'}")
    if elf is None or nm is None or objdump is None:
        return
    semboller = []          # (ad, adres, boy)
    for satir in subprocess.run([str(nm), "-S", str(elf)], capture_output=True, text=True,
                                encoding="utf-8", errors="replace").stdout.splitlines():
        p = satir.split()
        if len(p) == 4 and p[2] in ("t", "T") \
                and any(f"{len(a)}{a}" in p[3] for a in KAYNASMASIZ_FONKSIYONLAR):
            semboller.append((p[3], int(p[0], 16), int(p[1], 16)))
    ok("1F S2: skop_olc ikilide AYRI fonksiyon (gomulmedi — denetim bos degil)",
       any("8skop_olc" in s[0] for s in semboller),
       ", ".join(f"{s[0]} {s[2]} B" for s in semboller) or "sembol YOK")
    kaynasmis, kayan = [], 0
    for ad, adres, boy in semboller:
        dis = subprocess.run([str(objdump), "-d", f"--start-address={adres:#x}",
                              f"--stop-address={adres + boy:#x}", str(elf)],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout
        kayan += len(KAYAN_NOKTA.findall(dis))
        kaynasmis += [f"{ad}: {x.strip()}" for x in dis.splitlines() if KAYNASMIS.search(x)]
    # sokum gercekten kayan nokta kodu mu (bos/yanlis aralik sokulmesin)
    ok("1F S2: sokulen skop_olc kayan nokta komutlari iceriyor", kayan >= 20,
       f"{kayan} `.s` komutu")
    ok("1F S2: skop_olc'ta madd.s/msub.s YOK (kart = AVR basvurusu = ortak/src/skop.js)",
       not kaynasmis, f"{len(kaynasmis)} kaynasmis komut")
    for x in kaynasmis[:6]:
        print("       " + x)

    # ── 1F-2 (S8): BUTUN eskiz ceviri birimi. Ayni kaynasma guc_olc (6), olcum_al (5),
    #    skop_gorevi (4), suzgec_ters_kazanc (1)'de de vardi: B4/B5'in AVR'de dogruladigi
    #    olcum3.h matematigi kartta FARKLI sonuc veriyordu. Pragma .ino'nun basinda; kanit
    #    yine ikili: eskizin NESNE dosyasinin tamami (satir ici gomulen islevler de icinde —
    #    sembol listesine bakmak gomulmeyi kacirirdi).
    print("\n--- 2c. 1F-2 (S8): eskiz nesnesinin TAMAMINDA kaynasmis komut YOK ------")
    nesne = next((gec_dizin / "yapi" / "sketch").glob("*.ino.cpp.o"), None) \
        if (gec_dizin / "yapi" / "sketch").exists() else None
    ok("1F-2 S8: eskizin nesne dosyasi (--build-path) bulundu", nesne is not None,
       str(nesne.name) if nesne else "yok")
    if nesne is None:
        return
    dis = subprocess.run([str(objdump), "-d", str(nesne)], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    kayan_t = len(KAYAN_NOKTA.findall(dis))
    kaynasmis_t, islev = [], "?"
    for x in dis.splitlines():
        m = re.match(r"^[0-9a-f]+ <(.+)>:", x)
        if m:
            islev = m.group(1)
        elif KAYNASMIS.search(x):
            kaynasmis_t.append(f"{islev}: {x.strip()}")
    ok("1F-2 S8: eskiz nesnesi kayan nokta kodu iceriyor (sokum bos degil)", kayan_t >= 200,
       f"{kayan_t} `.s` komutu")
    ok("1F-2 S8: eskizin HICBIR islevinde madd.s/msub.s YOK (kart = AVR'de dogrulanan matematik)",
       not kaynasmis_t, f"{len(kaynasmis_t)} kaynasmis komut")
    for x in kaynasmis_t[:8]:
        print("       " + x)


def main() -> int:
    print("=" * 78)
    print("  B6  ASAMA 3 FIRMWARE — derleme + ikilide olu kod denetimi")
    print("=" * 78)

    print("\n--- 1. Derleme -----------------------------------------------------")
    print(f"     FQBN: {hedef2.FQBN}")
    gec_dizin = gecici.dizin("fw3_")
    d = subprocess.run(
        # 🔴 B21 (2026-09-10): "--clean" EKLENDI. Arduino-cli artimli
        # derliyor ve ONBELLEKTEN gelen ceviri birimlerinin uyarilarini
        # YENIDEN BASMIYOR. Sonuc: "Derleme UYARISIZ" iddiasi derleme
        # onbellegi durumuna gore DEGISIYORDU — B21 sirasinda ayni kod
        # icin pespese 3, 2 ve 0 uyari raporlandi. Onbellekli bir kosu
        # gercek uyarilari GIZLIYOR, yani iddia guvenilmezdi.
        # Bedeli: derleme ~12 s yerine ~60 s. Iddianin anlamli olmasi
        # bu bedele deger.
        [str(ARDUINO_CLI), "compile", "--fqbn", hedef2.FQBN, "--clean",
         "--warnings", "all", "--output-dir", str(gec_dizin),
         # 1F-2 (S8): nesne dosyalari da gecici dizinde (eskiz .o kaynasma taramasi)
         "--build-path", str(gec_dizin / "yapi"), str(ESKIZ)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=1800)

    if d.returncode != 0:
        print(d.stdout[-2500:])
        print(d.stderr[-2500:])
        ok("ESP32-S3 icin derlendi", False)
        return 1

    mf = re.search(r"Sketch uses (\d+) bytes \((\d+)%\)", d.stdout)
    mr = re.search(r"Global variables use (\d+) bytes \((\d+)%\)", d.stdout)
    ok("ESP32-S3 icin derlendi", True,
       f"flash {mf.group(1)} B (%{mf.group(2)}), RAM {mr.group(1)} B (%{mr.group(2)})"
       if mf and mr else "")

    uyarilar = [x for x in (d.stdout + d.stderr).splitlines() if "warning:" in x]
    ok("Derleme UYARISIZ (-Wall -Wextra)", not uyarilar, f"{len(uyarilar)} uyari")
    for u in uyarilar[:8]:
        print("       " + u)

    # 🔴 B22.1: eskiden `if mf:` / `if mr:` idi. arduino-cli cikti bicimi
    # degisip regex tutmazsa IKI IDDIA BIRDEN sessizce buharlasiyordu:
    # zincir yesil kalir, yalnizca toplam sayi duserdi ve bunu fark eden
    # bir denetim yok. Ayristirmanin KENDISI artik bir iddia.
    ok("Derleme ciktisindan flash/RAM ayristirildi", mf is not None and mr is not None,
       "regex tutmazsa esik iddialari kaybolur")
    ok("Flash payi yeterli (< %60)", mf is not None and int(mf.group(2)) < 60,
       f"%{mf.group(2)}" if mf else "AYRISTIRILAMADI")
    # B22.1: PSRAM oksuzu (64 800 B statik dizi) kaldirilinca RAM %35 -> %15.
    # Esik %40'tan %25'e SIKILASTIRILDI: gevsek kalirsa statik tamponun
    # geri gelmesi gorunmez olurdu.
    ok("RAM payi yeterli (< %25)", mr is not None and int(mr.group(2)) < 25,
       f"%{mr.group(2)}" if mr else "AYRISTIRILAMADI")
    # CA-4 (2026-10-08): yuzde TAMSAYI — 81 919 B de "%24" ve yesil; pay 28 B'ye inmisti ve
    #   hicbir iddia gormuyordu. Bayt olarak kilit: sinirin en az 4 KB altinda. Kirmiziysa
    #   kalici dahili tamponu PSRAM'e tasi (tasarim3_sabit.ESP_DRAM_ASGARI_PAY yorumu).
    #   Esitlik iddiasindan ONCE: statik tampon geri gelirse ilk kirmizi BU olur.
    pay = T.ESP_DRAM_SINIR - int(mr.group(1)) if mr else None
    ok(f"CA-4: statik DRAM %25 sinirinin ({T.ESP_DRAM_SINIR} B) en az "
       f"{T.ESP_DRAM_ASGARI_PAY} B altinda",
       pay is not None and T.ESP_DRAM_SINIR == 81920 and T.ESP_DRAM_ASGARI_PAY >= 4096
       and pay >= T.ESP_DRAM_ASGARI_PAY,
       f"olculen {mr.group(1)} B, pay {pay} B" if mr else "AYRISTIRILAMADI")

    # 🔴 `tasarim3_sabit.ESP_DRAM_KULLANILAN` bir OLCUMDUR ve elle tutulunca
    #    bayatladi: 51 084'te dondu, gercek 71 420 B. B21'in pil tamponu
    #    iddiasini 20 KB IYIMSER besliyordu. Artik `_firmware.json`'dan
    #    okunuyor; burasi da YEDEK sabitin olcumle esit oldugunu sinar —
    #    yedek, temiz bir klonda (B6 hic kosmamisken) devreye giriyor,
    #    o yuzden onun da dogru kalmasi gerekiyor.
    if mr:
        ok("Yedek DRAM sabiti olculen degerle AYNI",
           T._ESP_DRAM_SON_OLCUM == int(mr.group(1)),
           f"sabit {T._ESP_DRAM_SON_OLCUM} B, olculen {mr.group(1)} B — "
           f"esit degilse tasarim3_sabit.py:_ESP_DRAM_SON_OLCUM guncellenecek")

    # Olculen boyut KULLANICI belgesine gidiyor (`4-kurulum.html` kunyesi).
    # Elle yazildigi surece bayatladi: sayfa 481 935 B (%15) diyordu,
    # gercek 1 067 423 B (%33) idi — iki kattan fazla sapma, ve hicbir
    # denetim bunu goremezdi cunku sayi hicbir olcume BAGLI DEGILDI.
    # B6, B9'dan (belge uretimi) ONCE kostugu icin bu dosya hep taze.
    if mf and mr:
        (BURASI / "_firmware.json").write_text(json.dumps({
            "flash_bayt": int(mf.group(1)), "flash_yuzde": int(mf.group(2)),
            "ram_bayt": int(mr.group(1)), "ram_yuzde": int(mr.group(2)),
        }, indent=2), encoding="utf-8")

    print("\n--- 2. Ikilide olu kod denetimi ------------------------------------")
    ikili = next(gec_dizin.glob("*.ino.bin"), None)
    if ikili is None:
        ok("Ikili uretildi", False)
        return 1
    ham = ikili.read_bytes()
    print(f"     ikili {ikili.name}  {len(ham):,} bayt".replace(",", " "))

    for dize, aciklama in BEKLENEN_DIZELER:
        ok(f"{aciklama}", dize in ham,
           dize.decode('ascii', 'replace')[:44])

    for dize, aciklama in BULUNMAMALI:
        ok(f"YOK: {aciklama}", dize not in ham,
           dize.decode('ascii', 'replace'))

    kaynasma_denetimi(gec_dizin)

    print("\n--- 3. Kaynak ile tasarim ayni mi ----------------------------------")
    kaynak = (ESKIZ / "olcum3.h").read_text(encoding="utf-8")

    def sabit(ad):
        m = re.search(rf"#define {ad}\s+([0-9.]+)f?", kaynak)
        return float(m.group(1)) if m else None

    kn, kh = T.KANALLAR[0], T.KANALLAR[1]
    for ad, beklenen, tol in (("ORAN_NORMAL", kn["N"], 1e-4),
                              ("ORAN_YUKSEK", kh["N"], 1e-4),
                              ("VREF_NOMINAL", T.VREF, 1e-6)):
        v = sabit(ad)
        ok(f"{ad} tasarim3_sabit.py ile ayni",
           v is not None and abs(v - beklenen) < tol,
           f"{v} ~ {beklenen}")

    # Protokol: .ino'daki komut harfleri `?` ciktisinda listeleniyor mu
    ino = (ESKIZ / "olcum-karti-a3.ino").read_text(encoding="utf-8")
    komutlar = re.findall(r"case '([a-zA-Z?#])':", ino)
    print(f"     Komut harfleri: {' '.join(sorted(set(komutlar)))}")
    # 🔴 B22.1: liste ELLE yaziliydi ve B17'nin `f`/`F`'i ile B21'in
    # `p`/`P`'si hic eklenmemisti — yani bu denetim yeni komutlari
    # GORMUYORDU. Artik kaynaktan cikariliyor ve YALNIZCA bir asgari
    # sayi + kaybolmamasi gereken cekirdek kume sabit.
    kume = set(komutlar)
    ok("Komut harfi sayisi beklenenin altina dusmedi", len(kume) >= 20,
       f"{len(kume)} harf: {' '.join(sorted(kume))}")
    for h in ("z", "g", "Z", "i", "s", "n", "y", "a", "e", "t", "w", "?", "#",
              "f", "F", "p", "P", "R", "N"):
        ok(f"`{h}` komutu tanimli", h in kume)

    print("\n" + "=" * 78)
    print(f"  B6: {gecti}/{gecti + kaldi} kosul gecti")
    print("=" * 78)
    print()
    tezgah("B6 Firmware derleme + ikili", [
        ("I2C gercekten calisiyor mu",
         "`#` komutu -> `I2C: 0x48 0x49`. Ikisi de gorunmuyorsa adres "
         "pinleri ya da cekme direncleri yanlis"),
        ("Menzil gecisi gercek gerilimde puruzsuz mu",
         "Yavas artan bir gerilimde NORMAL->YUKSEK gecisini izle. "
         "Sicrama varsa histerezis yetersiz"),
        ("PSRAM kartta gercekten var mi",
         "Acilista `PSRAM: 8192 KB` yazmali. `YOK` yazarsa hedef2.py'de "
         "PSRAM=opi yerine PSRAM=enabled (quad) denenecek"),
    ])

    import shutil
    shutil.rmtree(gec_dizin, ignore_errors=True)
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
