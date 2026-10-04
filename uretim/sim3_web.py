# -*- coding: utf-8 -*-
"""B22.4 — KARTIN WEB KATMANI (Serial aynasi · SSE · komut ucu · guvenlik).

    python sim3_web.py

B22.4 oncesi kartin web tarafi UC yerden kirikti:

  1. [!] WiFi HIC ACILMIYORDU. `WIFI_AD` bos bir sabitti, yani
     `WiFi.begin()` bir kez bile cagrilmadi. AP kipi dosyada hic yoktu.
  2. [!] SSE YALNIZCA `D` SATIRINI TASIYORDU. `akis_yolla` tek bir yerden,
     `loop()`'un rapor blogundan cagriliyordu. `S2`/`M`/ham skop/`E`/`T`/
     `W`/`B` ve butun `*`/`!` yanitlari yalnizca `Serial.print`'teydi:
     WiFi ile baglanan arayuz SALT-OKUNUR ve SESSIZ olurdu.
  3. [!] KOMUT UCU YOKTU. `komut_calistir`'a HTTP'den giden yol yoktu.

Bu betik duzeltmelerin GERCEKTEN uygulandigini FIRMWARE KAYNAGINDAN
dogruluyor. Metin tabanli iddialar YORUMLARI CIKARARAK bakiyor — bir
iddianin kendi aciklama yorumuyla karsilanmasi, iddia olmadigi anlamina
gelir (bu ders B22.0-B22.2'de bes kez cikti).

⚠ Bu adim TASARIMI ve FIRMWARE'i sinar, kurulmus bir KARTI degil.
  Gercek WiFi baglantisi, mDNS'in telefonda cozulmesi, CSRF savunmasinin
  gercek tarayicilardaki davranisi ve `esp_wifi_start` <-> ADC DMA
  carpismasi TEZGAHTA olculmeli.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spice                                            # noqa: E402
from tezgah import tezgah                               # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"

INO = (KOD / "olcum-karti-a3.ino").read_text(encoding="utf-8", errors="replace")
AG_H = (KOD / "ag.h").read_text(encoding="utf-8", errors="replace")
AKIS_H = (KOD / "web_akis.h").read_text(encoding="utf-8", errors="replace")
SATIR_H = (KOD / "web_satir.h").read_text(encoding="utf-8", errors="replace")


def kod(metin: str) -> str:
    """C/C++ yorumlarini cikarir — iddialar KODA baksin, prozaya degil."""
    return re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", metin, flags=re.S))


INO_KOD = kod(INO)
AG_KOD = kod(AG_H)


def govde(kaynak: str, imza: str) -> str:
    """Bir fonksiyonun govdesini susluler sayarak cikarir."""
    i = kaynak.find(imza)
    if i < 0:
        return ""
    j = kaynak.find("{", i)
    if j < 0:
        return ""
    d = 0
    for k in range(j, len(kaynak)):
        if kaynak[k] == "{":
            d += 1
        elif kaynak[k] == "}":
            d -= 1
            if d == 0:
                return kaynak[j:k + 1]
    return ""


def bolum(r, baslik):
    r.bilgi("")
    r.bilgi("=" * 74)
    r.bilgi(f"  {baslik}")
    r.bilgi("=" * 74)
    r.bilgi("")


_URETEC = None


def uretec():
    """`arayuz-uret.py` modulu (adinda tire var — yoldan yukleniyor).
    Goruntu listesi ve kaynak cozme kurali TEK yerde: orada."""
    global _URETEC
    if _URETEC is None:
        import importlib.util
        oz = importlib.util.spec_from_file_location("arayuz_uret", BURASI / "arayuz-uret.py")
        _URETEC = importlib.util.module_from_spec(oz)
        oz.loader.exec_module(_URETEC)
    return _URETEC


# P5 (alt proje 3, 2026-10-02): kartin arayuz goruntusu (gzip) <= 600 KB,
# `ortak/` DAHIL. Uretecin sabitinden OKUNMUYOR: iddia spesifikasyonun
# sayisi; uretec degistirilse de bu sayi degismemeli.
P5_BUTCE = 600 * 1024


def _cekirdek_webserver():
    """Kurulu ESP32 Arduino cekirdeginin WebServer kaynagi (en yeni surum).
    Derleme ayni yerden yapiliyor (yukle.py / arduino-cli)."""
    import os
    kok = os.environ.get("LOCALAPPDATA")
    if not kok:
        return None
    taban = Path(kok) / "Arduino15" / "packages" / "esp32" / "hardware" / "esp32"
    adaylar = sorted(taban.glob("*/libraries/WebServer/src"),
                     key=lambda p: [int(x) if x.isdigit() else x
                                    for x in re.split(r"[.-]", p.parents[2].name)])
    adaylar = [p for p in adaylar if (p / "detail" / "mimetable.cpp").exists()]
    return adaylar[-1] if adaylar else None


def bolum6_moduller(r, k, _uret):
    """3A (P4/P5): ES modulleri goruntude, gzip'li, butce icinde."""
    goruntude = set(k["kaynak"])
    gz = set(k.get("gz", []))
    ortak = sorted("ortak/" + p.name for p in (KOK / "ortak" / "src").glob("*.js"))
    ekran = sorted("ekran/" + p.name for p in (KOK / "arayuz3" / "ekran").glob("*.js"))
    eksik = [a for a in ortak + ekran if a not in goruntude]
    r.kosul("  6l: [!] `ortak/src/*.js` -> `/ortak/`, `arayuz3/ekran/*.js` -> `/ekran/` GORUNTUDE",
            bool(ortak) and bool(ekran) and not eksik,
            " ".join(eksik) or f"{len(ortak)} ortak + {len(ekran)} ekran modulu")
    duz = [a for a in ortak + ekran if a not in gz]
    r.kosul("  6l: ES modulleri gzip'li (serveStatic `<yol>.gz` buluyor)",
            not duz and ".js" not in _uret.GZIPLENMEYEN,
            " ".join(duz) or "hepsi .gz")
    r.kosul("  6l: goruntu yolu -> kaynak: `ortak/x.js` ortak/src'ten, gerisi arayuz3'ten",
            _uret.kaynak_yolu("ortak/ozet.js") == KOK / "ortak" / "src" / "ozet.js"
            and _uret.kaynak_yolu("ekran/tema.js") == KOK / "arayuz3" / "ekran" / "tema.js"
            and _uret.kaynak_yolu("app.js") == KOK / "arayuz3" / "app.js")
    ortak_adet = len([a for a in goruntude if a.startswith("ortak/")])
    r.kosul(f"  6m: [!] P5 butcesi: arayuz goruntusu (gzip, ortak/ dahil) <= {P5_BUTCE} B",
            ortak_adet > 0 and 0 < k["icerik_bayt"] <= P5_BUTCE,
            f"{k['icerik_bayt']} B = %{100.0 * k['icerik_bayt'] / P5_BUTCE:.0f} "
            f"({ortak_adet} ortak modulu dahil)")


# 4F: manifest ikonlarinin karttaki toplam payi (PNG gzip'lenmez). Paletli PNG ile
# bugun ~15 KB; RGB'ye donulse ~45 KB olurdu — kart icin olu bayt degil ama ucuz da degil.
IKON_BUTCE = 24 * 1024


def bolum6_pwa(r, k, _uret):
    """4F (PC17): PWA kabugu — sw.js / cevrimdisi.html karta GIRMEZ, sw.js'in SURUM'u
    guncel, manifestteki her ikon goruntude ve butce icinde."""
    goruntude = set(k["kaynak"])
    kabuk = getattr(_uret, "PC_KABUGU", ())
    var = [a for a in kabuk if (KOK / "arayuz3" / a).is_file()]
    r.kosul("  6p: [!] 4F: PC kabugu (sw.js, cevrimdisi.html) VAR ama kart goruntusunde YOK",
            set(kabuk) == {"sw.js", "cevrimdisi.html"} and len(var) == 2
            and not goruntude & set(kabuk) and not set(_uret.goruntu_listesi()) & set(kabuk),
            " ".join(sorted(goruntude & set(kabuk))) or "kart service worker kullanamaz")
    try:
        metin = (KOK / "arayuz3" / "sw.js").read_text(encoding="utf-8")
        m = _uret.SW_SURUM.search(metin)
        beklenen = _uret.kabuk_surumu()
    except Exception as e:                                  # noqa: BLE001
        m, beklenen = None, f"hata: {e}"
    r.kosul("  6p: [!] 4F: sw.js SURUM kaynaktan hesaplananla AYNI (bayatsa: python arayuz-uret.py)",
            m is not None and m.group(1) == beklenen,
            f"sw.js {m.group(1) if m else 'yok'} / kaynak {beklenen}")
    ikonlar = _uret.manifest_ikonlari()
    eksik = [a for a in ikonlar if a not in goruntude]
    toplam = sum(k.get("bayt", {}).get(a, 10 ** 9) for a in ikonlar)
    r.kosul(f"  6p: 4F: manifestin her ikonu kart goruntusunde, toplam <= {IKON_BUTCE} B",
            len(ikonlar) >= 5 and not eksik and 0 < toplam <= IKON_BUTCE,
            " ".join(eksik) or f"{len(ikonlar)} ikon, {toplam} B")
    # Ikonlar ve manifest depoda elle konmus ikili degil: ureteç bugun AYNI baytlari veriyor
    import importlib.util
    import tempfile
    farkli = []
    try:
        oz = importlib.util.spec_from_file_location("ikon_uret", BURASI / "ikon-uret.py")
        iu = importlib.util.module_from_spec(oz)
        oz.loader.exec_module(iu)
        zemin = iu.css_renk("zemin-2", "#101821")
        renk = (iu.css_renk("volt", "#6ea8fe"), iu.css_renk("amper", "#f2a33c"))
        with tempfile.TemporaryDirectory(prefix="ikon4f_") as g:
            for ad, n, amac in iu.IKONLAR:
                iu.png_yaz(Path(g) / ad, n, iu.ciz(n, amac == "maskable", zemin, renk))
                asil = KOK / "arayuz3" / ad
                if not asil.is_file() or asil.read_bytes() != (Path(g) / ad).read_bytes():
                    farkli.append(ad)
        man = (KOK / "arayuz3" / "manifest.json").read_text(encoding="utf-8")
        if man != iu.manifest_metni("#%02x%02x%02x" % zemin):
            farkli.append("manifest.json")
    except Exception as e:                                  # noqa: BLE001
        farkli.append(f"hata: {e}")
    r.kosul("  6p: 4F: ikonlar + manifest ikon-uret.py'den BIREBIR yeniden uretiliyor (bayatsa: python ikon-uret.py)",
            not farkli, " ".join(farkli) or "5 ikon + manifest ayni")


# W6: AVR derleyicisi (test_olcum3.py ile ayni arac zinciri).
AVR_GCC = (Path.home() / "AppData/Local/Arduino15/packages/arduino/tools"
           / "avr-gcc/7.3.0-atmel3.6.1-arduino7/bin" / "avr-gcc.exe")


def _etag_avr(kunye: str, bul: list, esl: list):
    """web_etag.h'yi AVR emulatorunde kostur. (uyari satirlari, cikti satirlari) ya da None."""
    import json as _json
    import subprocess
    import gecici
    from avr import mega328
    from avr.cekirdek import Cekirdek
    from avr.elf import flash_goruntusu
    if not AVR_GCC.exists():
        return None
    d = gecici.dizin("olcum3_etag_")
    c = _json.dumps                                  # ASCII metinde C dize sabitiyle ayni kacislar
    v = ["/* sim3_web.py uretti (W6) */",
         f"static const char KUNYE[] = {c(kunye)};",
         f"#define BUL_ADET {len(bul)}u",
         "static const char *const BUL_YOL[] = {" + ", ".join(c(y) for y in bul) + "};",
         f"#define ESL_ADET {len(esl)}u",
         "static const char *const ESL_INM[] = {" + ", ".join(c(a) for a, _e, _b in esl) + "};",
         "static const char *const ESL_ETAG[] = {" + ", ".join(c(e) for _a, e, _b in esl) + "};", ""]
    (d / "etag_vektor.h").write_text("\n".join(v), encoding="ascii", newline="\n")
    elf = d / "ornek_etag.elf"
    p = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu11",
         "-Wall", "-Wextra", f"-I{KOD}", f"-I{d}", "-o", str(elf),
         str(BURASI / "avr" / "ornek_etag.c")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return [p.stderr[-1500:] or "derlenemedi"], []
    uyari = [x for x in p.stderr.splitlines() if "warning:" in x]
    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    for _ in range(100):
        if b"BITTI" in kart.tx:
            break
        kart.cevrim_kadar_kos(2_000_000)
    return uyari, kart.satirlar()


def _ag_sabit(ad: str) -> int:
    """ag.h'deki sure sabiti (ms). Bulunamazsa -1 (iddia kirmiziya doner)."""
    m = re.search(rf"#define {ad}\s+(\d+)u?\b", AG_H)
    return int(m.group(1)) if m else -1


def _ag_karar_avr(senaryolar: list):
    """AGD: ag_karar.h'yi AVR emulatorunde kostur; sureler ag.h'den -D ile.
    (uyari satirlari, cikti satirlari) ya da None (arac yok)."""
    import subprocess
    import gecici
    from avr import mega328
    from avr.cekirdek import Cekirdek
    from avr.elf import flash_goruntusu
    if not AVR_GCC.exists():
        return None
    d = gecici.dizin("olcum3_agk_")
    v = ["/* sim3_web.py uretti (AGD) */", "#include <stdint.h>",
         "typedef struct { uint8_t kimlik; uint32_t t0, son, b1, b1s, b2, b2s, il, ils; } Senaryo;",
         f"#define SEN_ADET {len(senaryolar)}u", "static const Senaryo SEN[] = {"]
    for x in senaryolar:
        v.append("    {%du, %s}," % (x["kimlik"], ", ".join(
            "%dUL" % x[a] for a in ("t0", "son", "b1", "b1s", "b2", "b2s", "il", "ils"))))
    v += ["};", ""]
    (d / "ag_vektor.h").write_text("\n".join(v), encoding="ascii", newline="\n")
    elf = d / "ornek_ag_karar.elf"
    tanim = [f"-D{a}={_ag_sabit(a)}u" for a in ("AG_STA_BEKLE_MS", "AG_STA_YENIDEN_MS", "AG_AP_PAY_MS")]
    p = subprocess.run(
        [str(AVR_GCC), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu11",
         "-Wall", "-Wextra", *tanim, f"-I{KOD}", f"-I{d}", "-o", str(elf),
         str(BURASI / "avr" / "ornek_ag_karar.c")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return [p.stderr[-1500:] or "derlenemedi"], []
    uyari = [x for x in p.stderr.splitlines() if "warning:" in x]
    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    for _ in range(200):
        if b"BITTI" in kart.tx:
            break
        kart.cevrim_kadar_kos(2_000_000)
    return uyari, kart.satirlar()


def _ag_yap_kaynak() -> tuple:
    """AGD inceleme: ag.h'den yapistiricinin METNI (yorumlar dahil, oldugu gibi).
    (metin, eksik parcalar)."""
    sabit = re.findall(r"^#define AG_(?!H\b)\w+[^\n]*$", AG_H, flags=re.M)
    tek = [r"^enum AgKip \{[^\n]*$", r"^static AgDurum ag_durum = [^\n]*$",
           r"^static char ag_mdns_kim\[17\] = [^\n]*$", r"^static bool ag_mdns_servis_var = [^\n]*$",
           r"^static volatile uint8_t ag_hazir = [^\n]*$", r"^static AgKarar ag_k = [^\n]*$"]
    satir = [re.search(d, AG_H, flags=re.M) for d in tek]
    imza = ["static void ag__mdns_servis(void)", "static void ag__kip_yaz(uint8_t k)",
            "static uint8_t ag_baslat_rf(void)", "static void ag__sta_oldu(void)",
            "static void ag__uygula(uint8_t e)", "static void ag_bekle_tamamla(void)",
            "static void ag_isle(void)", "static uint8_t ag__ap_kur(wifi_mode_t kip)\n{"]
    fon = [_tanim(AG_H, i) for i in imza]
    eksik = ([d for d, m in zip(tek, satir) if not m] + [i for i, f in zip(imza, fon) if not f]
             + ([] if len(sabit) >= 5 else ["#define AG_*"]))
    yapi = _tanim(AG_H, "struct AgDurum {", sinif=True)
    if not yapi:
        eksik.append("struct AgDurum")
    v = ["/* sim3_web.py: kod/olcum-karti-a3/ag.h'den BIREBIR (AGD inceleme) */", *sabit,
         '#include "ag_karar.h"', satir[0].group(0) if satir[0] else "", yapi,
         *[m.group(0) for m in satir[1:] if m],
         "static uint8_t ag__ap_kur(wifi_mode_t kip);", *fon]
    return "\n\n".join(v) + "\n", eksik


def _ag_yap_avr(senaryolar: list):
    """AGD inceleme: kartin ag YAPISTIRICISI (ag.h metni) + ag_karar.h AVR'de, sahte
    WiFi surucusuyla. (uyari/hata satirlari, cikti satirlari) ya da None (arac yok)."""
    import subprocess
    import gecici
    from avr import mega328
    from avr.cekirdek import Cekirdek
    from avr.elf import flash_goruntusu
    gxx = AVR_GCC.parent / "avr-g++.exe"
    if not gxx.exists():
        return None
    metin, eksik = _ag_yap_kaynak()
    if eksik:
        return ["ag.h'de bulunamadi: " + ", ".join(eksik)], []
    d = gecici.dizin("olcum3_agy_")
    (d / "ag_yapistirici.h").write_text(metin, encoding="utf-8", newline="\n")
    v = ["/* sim3_web.py uretti (AGD inceleme) */",
         "typedef struct { uint8_t kimlik; uint32_t a1, a1s, a2, a2s, son; } Senaryo;",
         f"#define SEN_ADET {len(senaryolar)}u", "static const Senaryo SEN[] = {"]
    for x in senaryolar:
        v.append("    {%du, %s}," % (x["kimlik"], ", ".join(
            "%dUL" % x[a] for a in ("a1", "a1s", "a2", "a2s", "son"))))
    v += ["};", ""]
    (d / "ag_yap_vektor.h").write_text("\n".join(v), encoding="ascii", newline="\n")
    elf = d / "ornek_ag_yapistirici.elf"
    # -Wno-format-truncation: sahte String'in tamponu SABIT (24 B), derleyici onu ag_durum.ip[16]'ya
    # snprintf'le kirpilabilir goruyor. Kartta String yigindadir (boyu derleyiciye bilinmez) ve
    # snprintf'in kirpmasi zaten amaclanan guvenli yol; uyari sahte katmanin, kartin degil.
    p = subprocess.run(
        [str(gxx), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu++11",
         "-Wall", "-Wextra", "-Wno-format-truncation", "-fno-threadsafe-statics",
         f"-I{KOD}", f"-I{d}", "-o", str(elf),
         str(BURASI / "avr" / "ornek_ag_yapistirici.cpp")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return [p.stderr[-1500:] or "derlenemedi"], []
    uyari = [x for x in p.stderr.splitlines() if "warning:" in x]
    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    for _ in range(400):
        if b"BITTI" in kart.tx:
            break
        kart.cevrim_kadar_kos(2_000_000)
    return uyari, kart.satirlar()


def bolum5_ag_donus(r):
    """AGD (5.12.109): acilista ev agi yoksa AP + STA'yi yeniden dene; donunce AP kapanir.
    Kartta bulundu: eskiden AP'ye dusen kart STA'yi BIR DAHA denemiyordu (elektrik
    kesintisinden sonra yonlendirici karttan yavas acilinca kart ev agina hic donmuyordu)."""
    bolum(r, "BOLUM 5m — AGD: ev agi acilista yoksa AP + yeniden deneme, donunce AP kapanir")
    B, Y, P = (_ag_sabit(a) for a in ("AG_STA_BEKLE_MS", "AG_STA_YENIDEN_MS", "AG_AP_PAY_MS"))
    r.kosul("  5m: AGD: sureler — deneme araligi >= 20 s (her deneme bir kanal taramasi, AP o "
            "sirada kanal degistirir) ve aralik + pay + 15 s baglanma <= 60 s (tezgah olcutu); "
            "hepsi 100 ms'nin kati (AVR adimi)",
            min(B, Y, P) > 0 and Y >= 20000 and Y + P + 15000 <= 60000
            and not (B % 100 or Y % 100 or P % 100),
            f"bekle {B} · aralik {Y} · pay {P} ms")
    # ── karar motoru (ag_karar.h) AVR'de ─────────────────────────────────
    AP_KUR, DENE, OLDU, KAPAT = 1, 2, 3, 4                         # AGE_*
    E_YOK, E_DENE, E_STA, E_AP = 0, 2, 4, 5                        # AGK_* (ilgili olanlar)
    U = 0xFFFFFFFF                                                 # "pencere yok"
    b3 = B + 3 * Y + 1500                                          # 3 denemeden sonra baglanir
    il, ils = B + Y - 1000, B + 2 * Y + 10000                      # DHCP suren iliski penceresi

    def sen(ad, kimlik, son, A, S, t0=0, b1=U, b1s=U, b2=U, b2s=U, il_=U, ils_=U):
        return dict(ad=ad, kimlik=kimlik, t0=t0, son=son, b1=b1, b1s=b1s, b2=b2, b2s=b2s,
                    il=il_, ils=ils_, A=A, S=S)
    S_ = [
        sen("acilista 3 s'de baglanir; calisirken 60 s kopma", 1, 600000, [(3000, OLDU)], (E_STA, 0),
            b1=3000, b1s=120000, b2=180000, b2s=U),
        sen("ev agi hic yok", 1, B + 9 * Y + 5000,
            [(B, AP_KUR)] + [(B + k * Y, DENE) for k in range(1, 10)], (E_DENE, 1)),
        sen("3 denemeden sonra doner; sonra calisirken kopar", 1, b3 + 260000,
            [(B, AP_KUR), (B + Y, DENE), (B + 2 * Y, DENE), (B + 3 * Y, DENE), (b3, OLDU), (b3 + P, KAPAT)],
            (E_STA, 0), b1=b3, b1s=b3 + 100000, b2=b3 + 160000, b2s=U),
        sen("iliski (DHCP) surerken deneme yok", 1, ils + Y + 10000,
            [(B, AP_KUR), (ils, DENE), (ils + Y, DENE)], (E_DENE, 1), il_=il, ils_=ils),
        sen("ev agi KAYITLI DEGIL (bagli girdisi yok sayilir)", 0, 100000, [], (E_AP, 0), b1=0, b1s=50000),
        sen("sifir ilklenmis (WiFi N0)", 2, 100000, [], (E_YOK, 0), b1=0, b1s=U),
        sen("millis tasmasi", 1, B + 2 * Y + 5000, [(B, AP_KUR), (B + Y, DENE), (B + 2 * Y, DENE)],
            (E_DENE, 1), t0=0xFFFFFFFF - 4095),
        sen("pay icinde kopar: yine STA'da kalir", 1, b3 + 100000,
            [(B, AP_KUR), (B + Y, DENE), (B + 2 * Y, DENE), (B + 3 * Y, DENE), (b3, OLDU), (b3 + P, KAPAT)],
            (E_STA, 0), b1=b3, b1s=b3 + 1500),
        sen("tam AG_STA_BEKLE_MS aninda baglanir: AP kurulmaz", 1, B + 20000, [(B, OLDU)], (E_STA, 0),
            b1=B, b1s=U),
    ]
    sonuc = _ag_karar_avr(S_)
    if sonuc is None:
        r.bilgi("     avr-gcc bulunamadi — ag_karar.h AVR denetimi ATLANDI.")
        r.kosul("  5m: AGD: AVR araci yoksa bu ACIKCA soyleniyor", True, "sessiz atlama degil")
    else:
        uyari, sat = sonuc
        r.kosul("  5m: AGD: ag_karar.h AVR'de UYARISIZ derlendi (-Wall -Wextra, sureler ag.h'den) ve sonuna "
                "kadar kostu", not uyari and "BITTI" in sat, " | ".join(uyari[:2]) or f"{len(sat)} satir")
        A, S = {}, {}
        for x in (y.split() for y in sat):
            if len(x) == 4 and x[0] == "A":
                A.setdefault(int(x[1]), []).append((int(x[2]), int(x[3])))
            elif len(x) == 4 and x[0] == "S":
                S[int(x[1])] = (int(x[2]), int(x[3]))

        def bak(*ix):
            kotu = [f"#{i} {S_[i]['ad']}: {A.get(i, [])} S={S.get(i)}" for i in ix
                    if A.get(i, []) != S_[i]["A"] or S.get(i) != S_[i]["S"]]
            return not kotu, " ; ".join(kotu)[:300] or ", ".join(S_[i]["ad"] for i in ix)
        ok, ne = bak(0, 8)
        r.kosul("  5m: [!] AGD: acilista baglanirsa STA, AP HIC kurulmaz (sinirda da); calisirken kopmada "
                "KARAR YOK (surucu doner, 5.12.106 — bozulmadi)", ok, ne)
        ok, ne = bak(1, 6)
        r.kosul("  5m: [!] AGD: ev agi yoksa AP tam AG_STA_BEKLE_MS'de, STA AG_STA_YENIDEN_MS'de bir yeniden "
                "deneniyor, SONSUZA DEK (millis tasmasinda da)", ok, ne)
        ok, ne = bak(2, 7)
        r.kosul("  5m: [!] AGD: ev agi N denemeden sonra donerse STA; AP AG_AP_PAY_MS sonra kapanir, sonra "
                "deneme/AP yok; payda ya da sonra kopma da STA'da kalir", ok, ne)
        ok, ne = bak(3)
        r.kosul("  5m: AGD: STA iliskiliyken (DHCP surerken) yeniden denenmez (connect() bagliyi KOPARIR); "
                "iliski bitince hemen", ok, ne)
        ok, ne = bak(4, 5)
        r.kosul("  5m: AGD: ev agi kayitli degilse saf AP — hic deneme yok; sifir durumda (N0) hic eylem yok",
                ok, ne)
    # ── AGD inceleme: kart yapistiricisinin METNI (ag.h) AVR'de, sahte surucuyle ──
    #    Asagidaki kaynak iddialari alt dize arar; inceleme iki mutant buldu (ag__sta_oldu
    #    softAPIP / ag_isle bagli<->iliskili) ve ikisinde de B22b yesil kaliyordu.
    #    Sahte surucu: iliski begin()'den 300 ms, IP 2000 ms sonra; WL_CONNECTED YALNIZ
    #    IP'den sonra (cekirdek 3.3.11 STA.cpp, STA_GOT_IP).
    IP_STA, IP_AP = "192.0.2.57", "192.168.4.1"                    # RFC 5737 belge adresi
    a1 = B + Y + 5000                                              # ilk denemeden 5 s sonra gelir
    t_ip = B + 2 * Y + 300 + 2000                                  # 2. denemede iliski + DHCP
    a1s = t_ip + P + 80000
    YS = [dict(ad="ev agi acilista yok, ilk denemeden 5 s sonra gelir; sonra 5 dk kopar", kimlik=1,
               a1=a1, a1s=a1s, a2=a1s + 300000, a2s=U, son=a1s + 330000,
               bek=[("M", 0, 1), ("B", 0), ("M", B, 3), ("P", B), ("K", B, 1, 2, IP_AP),
                    ("B", B + Y), ("B", B + 2 * Y), ("K", t_ip, 2, 1, IP_STA), ("M", t_ip + P, 1)],
               S=(1, IP_STA, 1, 1, 1, 1)),
          dict(ad="ev agi acilista var; sonra 5 dk kopar", kimlik=1, a1=0, a1s=100000, a2=400000, a2s=U,
               son=450000, bek=[("M", 0, 1), ("B", 0), ("K", 2300, 1, 1, IP_STA)], S=(1, IP_STA, 1, 1, 1, 1)),
          dict(ad="ev agi KAYITLI DEGIL (ag yayinda olsa da)", kimlik=0, a1=0, a1s=U, a2=U, a2s=U, son=100000,
               bek=[("M", 0, 2), ("P", 0), ("K", 0, 1, 2, IP_AP)], S=(2, IP_AP, 2, 0, 1, 1))]
    sonuc = _ag_yap_avr(YS) if t_ip + P < a1s and 2300 < B else ([f"senaryo zamani tutarsiz: B={B}"], [])
    if sonuc is None:
        r.bilgi("     avr-g++ bulunamadi — ag yapistiricisi AVR denetimi ATLANDI.")
        r.kosul("  5m: AGD inceleme: AVR araci yoksa bu ACIKCA soyleniyor", True, "sessiz atlama degil")
    else:
        uyari, sat = sonuc
        r.kosul("  5m: AGD inceleme: kartin ag YAPISTIRICISI (ag.h METNI: ag_baslat_rf, ag_bekle_tamamla, "
                "ag_isle, ag__uygula, ag__sta_oldu, ag__ap_kur) + ag_karar.h AVR'de sahte surucuyle UYARISIZ "
                "derlendi ve sonuna kadar kostu", not uyari and "BITTI" in sat,
                " | ".join(uyari[:2])[:300] or f"{len(sat)} satir")
        G, GS = {}, {}
        for x in (y.split() for y in sat):
            if x and x[0] in "MBPK" and len(x) >= 3:
                G.setdefault(int(x[1]), []).append(
                    (x[0], *[int(z) if z.isdigit() else z for z in x[2:]]))
            elif len(x) == 8 and x[0] == "S":
                GS[int(x[1])] = (int(x[2]), x[3], *map(int, x[4:]))

        def ybak(i):
            ok = G.get(i, []) == YS[i]["bek"] and GS.get(i) == YS[i]["S"]
            return ok, (YS[i]["ad"] if ok else f"#{i}: {G.get(i, [])} S={GS.get(i)}"[:300])
        ok, ne = ybak(0)
        r.kosul("  5m: [!] AGD inceleme: ev agi acilista yok, sonra gelir — AP+STA, 30 s'de bir begin(); kip STA "
                "YALNIZ IP geldikten sonra ve `ag_durum.ip` STA'NIN adresi (AP'ninki ya da 0.0.0.0 degil); AP pay "
                "sonra kapanir; calisirken 5 dk kopmada yapistirici hicbir sey yapmaz", ok, ne)
        ok, ne = ybak(1)
        r.kosul("  5m: AGD inceleme: ev agi acilista var — DHCP bitince STA (ip STA'nin), AP HIC kurulmaz; 5 dk "
                "kopmada sessiz, surucu doner", ok, ne)
        ok, ne = ybak(2)
        r.kosul("  5m: AGD inceleme: ev agi kayitli degil — saf AP, begin() HIC cagrilmaz (ag yayinda olsa da)",
                ok, ne)
    # ── kart yapistiricisi (ag.h + .ino) — kaynaktan ─────────────────────
    agk = (KOD / "ag_karar.h").read_text(encoding="utf-8", errors="replace")
    r.kosul("  5m: AGD: karar platformsuz — ag_karar.h yalniz <stdint.h> icerir, sureleri ag.h'den alir",
            re.findall(r'#include\s*[<"]([^>"]+)', kod(agk)) == ["stdint.h"]
            and '#include "ag_karar.h"' in AG_KOD
            and 0 <= AG_KOD.find("#define AG_AP_PAY_MS") < AG_KOD.find('#include "ag_karar.h"'),
            "Arduino/WiFi baglantisi kararin icine girerse AVR'de sinanamaz")
    rf = govde(AG_KOD, "static uint8_t ag_baslat_rf(void)")
    uy = govde(AG_KOD, "static void ag__uygula(uint8_t e)")
    so = govde(AG_KOD, "static void ag__sta_oldu(void)")
    isl = govde(AG_KOD, "static void ag_isle(void)")

    def dal(ad):
        i = uy.find(f"e == {ad}")
        j = uy.find("} else if", i + 1)
        return uy[i:j if j > i else len(uy)] if i >= 0 else ""
    r.kosul("  5m: AGD: acilis — karar kayitli ag VAR/YOK ile kurulur; ev agi yoksa saf AP (WIFI_AP)",
            "agk_kur(&ag_k, ad.length() ? 1u : 0u, millis());" in rf
            and "return ag__ap_kur(WIFI_AP);" in rf and "while" not in rf,
            "kayitli degilken AP+STA kurulsaydi bos ada sonsuza dek tarama yapardi")
    d_ap = dal("AGE_AP_KUR")
    r.kosul("  5m: [!] AGD: AP'ye dusus radyoyu KAPATMIYOR — AP+STA, otomatik baglanma KAPALI (surekli "
            "tarama AP'yi bozar), STA yapilandirmasi silinmez",
            "WiFi.disconnect(false, false);" in d_ap
            and 0 <= d_ap.find("WiFi.setAutoReconnect(false);") < d_ap.find("ag__ap_kur(WIFI_AP_STA)")
            and "disconnect(true" not in AG_KOD,
            "eski kusur: WiFi.disconnect(true) + WIFI_AP — STA bir daha hic denenmiyordu")
    d_de = dal("AGE_STA_DENE")
    r.kosul("  5m: AGD: yeniden deneme AP'ye dokunmaz, bloklamaz — yalniz WiFi.begin() (surucudeki yapilandirma)",
            "WiFi.begin();" in d_de and not re.search(r"softAP|ag__ap_kur|WiFi\.mode|delay|while", d_de),
            "her denemede AP yeniden kurulsaydi telefon her 30 s'de duserdi")
    r.kosul("  5m: [!] AGD: STA olunca otomatik baglanma geri ACILIR (calisirken kopma yolu), ssid/ip/mac kip'ten "
            "ONCE; mDNS yeniden kurulmaz (MDNS.end yok — servis bayragi gecerli kalir)",
            0 <= so.find("WiFi.setAutoReconnect(true);") < so.find("ag__kip_yaz(AG_STA)")
            and all(0 <= so.find(f"ag_durum.{a}") < so.find("ag__kip_yaz(AG_STA)") for a in ("ssid", "ip", "mac"))
            and "if (!ag_durum.mdns) ag_durum.mdns = MDNS.begin(AG_MDNS);" in so
            and "MDNS.end" not in AG_KOD + INO_KOD and "ag__sta_oldu();" in dal("AGE_STA_OLDU"),
            "otomatik baglanma kapali kalsaydi calisirken kopan kart bir daha donmezdi")
    d_ka = dal("AGE_AP_KAPAT")
    r.kosul("  5m: AGD: pay dolunca AP kapanir (WIFI_STA) — STA'ya dokunulmaz",
            "WiFi.mode(WIFI_STA);" in d_ka and "disconnect" not in d_ka and "begin" not in d_ka)
    gv = govde(INO, "static void ag_gorevi(void *)")
    gv_d = kod(gv[gv.find("for (;;)"):]) if "for (;;)" in gv else ""
    r.kosul("  5m: AGD: ag_isle ag gorevinin DONGUSUNDE (her tur); etkin degilse surucuyu sorgulamaz; iliski "
            "WiFi.STA.connected()'tan",
            "ag_isle();" in gv_d
            and 0 <= kod(isl).find("if (!agk_etkin(&ag_k)) return;") < kod(isl).find("WiFi.")
            and "WiFi.STA.connected() ? 1u : 0u" in isl and "WiFi.status() == WL_CONNECTED" in isl,
            "dongude olmasa kart AP'de kalirdi (eski kusur, bu kez kodda)")
    ky = govde(AG_KOD, "static void ag__kip_yaz(uint8_t k)")
    r.kosul("  5m: AGD: `Ag:` satiri HER kip degisiminde (AP -> STA) yeniden basilir — kip yazimi surumu artirir",
            "ag_hazir = (uint8_t)(ag_hazir + 1u);" in ky
            and "ag_satiri_basildi = ag_hazir;" in kod(govde(INO, "static void ag_satiri_bas()")),
            "tek seferlik bayrakla STA'ya donus afiste HIC gorunmezdi")
    hg = kod(govde(INO, "static bool host_gecerli()"))
    r.kosul("  5m: AGD: AP acikken Host: AP'nin kendi adresi de kabul (gecis payinda AP'deki telefon 403 almaz)",
            "(WiFi.getMode() & WIFI_MODE_AP) && h == WiFi.softAPIP().toString()" in hg)
    bld = (KOD / "bildirim_esp.h").read_text(encoding="utf-8", errors="replace")
    kes = (KOD / "kayit_esp.h").read_text(encoding="utf-8", errors="replace")
    bg = kod(govde(bld, "static void bildirim_gorevi(void *)"))
    kg = kod(govde(kes, "static void kayit_gorevi(void *)"))
    r.kosul("  5m: AGD: MQTT ve NTP gecisten sonra KENDILIGINDEN baslar — kip her turda yeniden okunur",
            "for (;;)" in bg and "for (;;)" in kg
            and "if (!(ag_durum.kip == AG_STA && WiFi.status() == WL_CONNECTED))" in bg[bg.find("for (;;)"):]
            and "kayit__saat();" in kg[kg.find("for (;;)"):]
            and "if (!kayit_saat_ntp && ag_durum.kip == AG_STA)" in kod(govde(kes, "static void kayit__saat(void)")),
            "kip acilista bir kez okunsaydi AP'den donen kart bildirim gondermezdi")


def _tanim(kaynak: str, imza: str, sinif: bool = False) -> str:
    """`imza`dan kapanan susluye kadar TAM tanim (sinifsa sonundaki `;` ile)."""
    i = kaynak.find(imza)
    g = govde(kaynak[i:], imza) if i >= 0 else ""
    if not g:
        return ""
    j = kaynak.find("{", i)
    return kaynak[i:j] + g + (";" if sinif else "")


def _arayuz_avr(cekirdek: Path, dosyalar: list, dizinler: list, istekler: list, isleyiciler: list):
    """W6 inceleme: kartin `arayuz_tur` + `ArayuzIsleyici` METNI AVR'de, cekirdegin
    mimeTable'iyla. (hata/uyari satirlari, cikti satirlari) ya da None (arac yok)."""
    import json as _json
    import subprocess
    import gecici
    from avr import mega328
    from avr.cekirdek import Cekirdek
    from avr.elf import flash_goruntusu
    gxx = AVR_GCC.parent / "avr-g++.exe"
    if not gxx.exists():
        return None
    detay = cekirdek / "detail"
    tur = _tanim(INO, "static String arayuz_tur(const String &yol)")
    sinif = _tanim(INO, "class ArayuzIsleyici", sinif=True)
    if not tur or not sinif:
        return ["kartin metninde arayuz_tur / class ArayuzIsleyici bulunamadi"], []
    d = gecici.dizin("olcum3_arayuz_")
    c = _json.dumps                                  # ASCII yol/onbellek: C dize sabitiyle ayni kacislar
    (d / "pgmspace.h").write_text("#include <avr/pgmspace.h>\n", encoding="ascii", newline="\n")
    (d / "arayuz_kaynak.h").write_text("/* sim3_web.py: olcum-karti-a3.ino'dan BIREBIR */\n"
                                       + tur + "\n\n" + sinif + "\n", encoding="utf-8", newline="\n")

    def blob(ad, ogeler):                             # bitisik sabitler: "\0" sonrasi rakam sekizlik olmasin
        return (f"static const char {ad}[] PROGMEM = "
                + " ".join(c(x) + ' "\\0"' for x in ogeler) + ";")
    kur = " ".join(f"static ArayuzIsleyici I{n}({c(o)}, {c(b)});" for n, (o, b) in enumerate(isleyiciler))
    v = ["/* sim3_web.py uretti (W6 inceleme) */",
         blob("DOSYALAR", dosyalar), blob("DIZINLER", dizinler),
         blob("ISTEKLER", [f"{m} {u}" for m, u in istekler]),
         f"#define ISLEYICI_ADET {len(isleyiciler)}u",
         f"#define ISLEYICI_KUR {kur} static RequestHandler *const ISLEYICILER[] = "
         "{" + ", ".join(f"&I{n}" for n in range(len(isleyiciler))) + "};", ""]
    (d / "arayuz_vektor.h").write_text("\n".join(v), encoding="ascii", newline="\n")
    elf = d / "ornek_arayuz.elf"
    p = subprocess.run(
        [str(gxx), "-mmcu=atmega328p", "-DF_CPU=16000000UL", "-Os", "-std=gnu++11",
         "-Wall", "-Wextra", "-fno-threadsafe-statics", f"-I{d}", f"-I{detay}", "-o", str(elf),
         str(BURASI / "avr" / "ornek_arayuz.cpp"), str(detay / "mimetable.cpp")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return [p.stderr[-1500:] or "derlenemedi"], []
    uyari = [x for x in p.stderr.splitlines() if "warning:" in x]
    flash, _ = flash_goruntusu(elf)
    kart = mega328.Kart(flash, Cekirdek)
    for _ in range(100):
        if b"BITTI" in kart.tx:
            break
        kart.cevrim_kadar_kos(2_000_000)
    return uyari, kart.satirlar()


def bolum6_arayuz_isleyici(r, cekirdek: Path, isleyiciler: list):
    """W6 inceleme (6r): `.gz`e dusus + MIME + 404/dizin/POST — kartin metni AVR'de."""
    import json
    kunye = BURASI / "_fs.json"
    if not kunye.exists():
        r.bilgi("     _fs.json yok — ArayuzIsleyici AVR denetimi ATLANDI (python arayuz-uret.py).")
        r.kosul("  6r: goruntu yoksa bu ACIKCA soyleniyor", True, "sessiz atlama degil")
        return
    k = json.loads(kunye.read_text(encoding="utf-8"))
    gz = set(k.get("gz", []))
    dosyalar = ["/" + a + (".gz" if a in gz else "") for a in k.get("bayt", {})]
    dizinler = sorted({"/" + a.rsplit("/", 1)[0] for a in k.get("bayt", {}) if "/" in a})
    ortak = next((a for a in k.get("bayt", {}) if a.startswith("ortak/")), "ortak/ozet.js")
    onekler = [o for o, _b in isleyiciler]
    kok = onekler.index("/") if "/" in onekler else -1
    ven = onekler.index("/vendor/") if "/vendor/" in onekler else -1

    def gs(yol):                                    # goruntude neyle duruyor
        return "/" + yol + (".gz" if yol in gz else "")
    JS = "application/javascript"
    # (yontem, istek, isleyici, handle, acilan, tur) — TURLER ELLE (tarayicinin istedigi), tablodan DEGIL
    bek = [("G", "/index.html", kok, 1, gs("index.html"), "text/html"),
           ("G", "/app.js", kok, 1, gs("app.js"), JS),
           ("G", "/style.css", kok, 1, gs("style.css"), "text/css"),
           ("G", "/ekran/tema.js", kok, 1, gs("ekran/tema.js"), JS),
           ("G", "/" + ortak, kok, 1, gs(ortak), JS),
           ("G", "/manifest.json", kok, 1, gs("manifest.json"), "application/json"),
           ("G", "/kunye.json", kok, 1, gs("kunye.json"), "application/json"),
           ("G", "/ikon-180.png", kok, 1, gs("ikon-180.png"), "image/png"),
           ("G", "/vendor/vue.global.prod.js", ven, 1, gs("vendor/vue.global.prod.js"), JS),
           ("G", "/app.js.gz", kok, 1, "/app.js.gz", "application/x-gzip"),   # cekirdekteki gibi
           ("G", "/yok.js", kok, 0, None, None),
           ("G", "/vendor/yok.js", ven, 0, None, None),       # vendor 404: koke DUSMEZ
           ("G", "/ortak", kok, 0, None, None),               # dizin
           ("G", "/ekran/", -1, 0, None, None),               # dizin istegi: kok_sayfa/404
           ("P", "/app.js", -1, 0, None, None)]               # yalniz GET
    eksik = [a for _m, _u, _i, h, a, _t in bek if h and a not in dosyalar]
    sonuc = _arayuz_avr(cekirdek, dosyalar, dizinler, [(m, u) for m, u, *_ in bek], isleyiciler)
    if sonuc is None:
        r.bilgi("     avr-g++ bulunamadi — ArayuzIsleyici AVR denetimi ATLANDI.")
        r.kosul("  6r: AVR araci yoksa bu ACIKCA soyleniyor", True, "sessiz atlama degil")
        return
    uyari, sat = sonuc
    Y = next((s.split()[1:] for s in sat if s.startswith("Y ")), None)
    r.kosul("  6r: W6: kartin ArayuzIsleyici + arayuz_tur METNI AVR'de cekirdegin mimeTable'iyla UYARISIZ derlendi ve kostu",
            not uyari and "BITTI" in sat and Y is not None and int(Y[0]) >= 64 and Y[1] == "0",
            " | ".join(uyari[:2]) or (f"yigin payi {Y[0]} B, String tasmasi {Y[1]}" if Y else f"{len(sat)} satir"))
    H = {int(p[1]): p[2:] for p in (s.split("|") for s in sat) if len(p) == 9 and p[0] == "H"}
    kotu = list(eksik)
    for i, (m, u, isl, h, a, t) in enumerate(bek):
        g = H.get(i)
        if h:
            bekle = [str(isl), "1", "1", a, u, t, isleyiciler[isl][1]]
        else:
            bekle = [str(isl) if isl >= 0 else "-", "0", "0"]
        if g is None or (g if h else g[:3]) != bekle:
            kotu.append(f"{m} {u}: {'|'.join(g) if g else 'yok'}")
    r.kosul("  6r: [!] W6: istek -> `.gz`e dusus + ASIL yoldan MIME (js/css/html/json/png) + dogru Cache-Control; "
            "yok/dizin/POST/`/x/` -> isleyici GONDERMEZ",
            len(H) == len(bek) and not kotu,
            "; ".join(kotu[:3]) or f"{len(bek)} istek, {len(dosyalar)} goruntu dosyasi")


def bolum6_etag(r, k, _uret):
    """W6: ETag kunyesi (uretec) + kartin ETag/304 karari (web_etag.h, AVR'de)."""
    import gzip
    import json
    import tempfile
    etag = k.get("etag", {})
    beklenen_ad = list(_uret.goruntu_listesi()) + ["kunye.json"]
    hex16 = re.compile(r"^[0-9a-f]{16}$")
    kotu = [a for a, e in etag.items() if not hex16.match(str(e))]
    eksik = [a for a in beklenen_ad if a not in etag]
    fazla = [a for a in etag if a not in beklenen_ad]
    r.kosul("  6q: [!] W6: goruntudeki HER dosyanin ETag'i kunyede (16 kucuk onaltilik); etag.txt'in kendisi YOK",
            bool(etag) and not kotu and not eksik and not fazla and _uret.ETAG_KUNYE not in etag,
            " ".join(kotu + eksik + [f"{a}(fazla)" for a in fazla]) or f"{len(etag)} dosya")
    # Ayni kaynak -> ayni ETag (gzip mtime=0) ve goruntudeki ETag bugunku kaynaginki
    farkli = []
    for a in beklenen_ad[:-1]:
        bir, iki = _uret.etag_ozet(_uret.sikistir(a)[0]), _uret.etag_ozet(_uret.sikistir(a)[0])
        if bir != iki or etag.get(a) != bir:
            farkli.append(a)
    _kj = gzip.compress(json.dumps(_uret.kunye_hesapla(), separators=(",", ":")).encode("utf-8"), 9, mtime=0)
    r.kosul("  6q: [!] W6: ETag DEGISMEYEN dosyada SABIT — iki uretim ayni ozet, goruntudeki = kaynaktan hesaplanan",
            not farkli and etag.get("kunye.json") == _uret.etag_ozet(_kj),
            " ".join(farkli) or "kunye.json dahil")
    # Icerik degisince ETag degisir: GERCEK `sikistir` yolu, kaynak gecici kopyaya cevrilerek
    degismeyen = []
    asil = _uret.kaynak_yolu
    try:
        with tempfile.TemporaryDirectory(prefix="olcum3_etag_") as g:
            for ad in ("index.html", "app.js", "ortak/ozet.js"):
                kopya = Path(g) / ad.replace("/", "_")
                kopya.write_bytes(asil(ad).read_bytes() + b"\n")
                _uret.kaynak_yolu = (lambda a, _ad=ad, _k=kopya: _k if a == _ad else asil(a))
                try:
                    if _uret.etag_ozet(_uret.sikistir(ad)[0]) == etag.get(ad):
                        degismeyen.append(ad)
                finally:
                    _uret.kaynak_yolu = asil
    except Exception as e:                                  # noqa: BLE001
        degismeyen.append(f"hata: {e}")
    r.kosul("  6q: [!] W6: icerik DEGISINCE ETag degisir (index.html, app.js, ortak modulu; tek bayt)",
            not degismeyen, " ".join(degismeyen) or "uc dosyada da yeni ozet")
    metin = _uret.etag_kunyesi(etag)
    sinir = re.search(r"if \(n == 0 \|\| n > (\d+)\) return;", kod(govde(INO, "static void etag_kunye_yukle()")))
    r.kosul("  6q: W6: goruntudeki etag.txt kunyeden uretilmis ve kartin okuma sinirinin altinda",
            k.get("bayt", {}).get(_uret.ETAG_KUNYE) == len(metin.encode("ascii"))
            and sinir is not None and len(metin) <= int(sinir.group(1)) // 2,
            f"{len(metin)} B, sinir {sinir.group(1) if sinir else '?'} B (2x pay)")

    # ── Kartin karari: web_etag.h AVR'de, uretecin GERCEK satirlariyla ─────
    gercek = ["index.html", "app.js", "vendor/vue.global.prod.js", "kunye.json", "ikon-180.png",
              next((a for a in beklenen_ad if a.startswith("ortak/")), "ortak/ozet.js")]
    secme = {a: etag[a] for a in gercek if a in etag}
    E = '"' + etag.get("app.js", "0" * 16) + '"'
    kunye = (_uret.etag_kunyesi(secme)
             + "/bozuk1.js 0123456789ABCDEF\n"          # buyuk harf: uretec yazmaz
             + "/bozuk2.js 0123456789abcde\n"           # 15 hane
             + "/bozuk3.js 0123456789abcdef0\n"         # 17 hane
             + "/cift.js zzzz\n/cift.js 00112233445566ff\n")   # bozuk satir atlanir, ilk GECERLI kazanir
    bul = ["/" + a for a in gercek] + ["/app.js.gz", "/app.j", "app.js", "/", "/etag.txt",
                                        "/bozuk1.js", "/bozuk2.js", "/bozuk3.js", "/cift.js"]
    bul_bek = ['"' + etag[a] + '"' if a in etag else None for a in gercek] + [None] * 8 + ['"00112233445566ff"']
    esl = [(E, E, 1), ("W/" + E, E, 1), ('"0000000000000000", ' + E, E, 1),
           (' "aaaaaaaaaaaaaaaa" ,W/' + E + ' ', E, 1), ("*", E, 1),
           ('"0000000000000000"', E, 0), ("", E, 0), (E[:-3] + '"', E, 0), (E[:-1] + '0"', E, 0),
           (E[1:-1], E, 0), ("W/" + E[1:-1], E, 0), ('"', E, 0), (E[:-1], E, 0), ("*, " + E, E, 0)]
    sonuc = _etag_avr(kunye, bul, esl)
    if sonuc is None:
        r.bilgi("     avr-gcc bulunamadi — web_etag.h AVR denetimi ATLANDI.")
        r.kosul("  6q: W6: AVR araci yoksa bu ACIKCA soyleniyor", True, "sessiz atlama degil")
        return
    uyari, sat = sonuc
    r.kosul("  6q: W6: web_etag.h AVR'de UYARISIZ derlendi (-Wall -Wextra) ve sonuna kadar kostu",
            not uyari and "BITTI" in sat, " | ".join(uyari[:2]) or f"{len(sat)} satir")
    B = {int(p[1]): (p[2], p[3]) for p in (s.split() for s in sat) if len(p) == 4 and p[0] == "B"}
    Es = {int(p[1]): p[2] for p in (s.split() for s in sat) if len(p) == 3 and p[0] == "E"}
    N = next((s.split()[1:] for s in sat if s.startswith("N ")), None)
    bul_kotu = [bul[i] for i, b in enumerate(bul_bek)
                if B.get(i) != (("1", b) if b else ("0", "-"))]
    r.kosul("  6q: [!] W6: etag_bul uretecin satirlarindan AYNI ETag'i (tirnakli) buluyor; .gz/onek/yolsuz/bozuk -> YOK",
            len(B) == len(bul) and not bul_kotu,
            " ".join(bul_kotu) or f"{len(gercek)} gercek dosya + {len(bul) - len(gercek)} ret")
    esl_kotu = [f"{i}:{a!r}" for i, (a, _e, b) in enumerate(esl) if Es.get(i) != str(b)]
    r.kosul("  6q: [!] W6: If-None-Match esleserse 304 (tam, W/, liste, *), eslesmezse/bos/bozuksa 200",
            len(Es) == len(esl) and not esl_kotu and N == ["0", "0"],
            " ".join(esl_kotu) or f"{len(esl)} baslik + NULL girdiler")


# ═══════════════════════════════════════════════════════════════════════
def bolum1(r):
    bolum(r, "BOLUM 1 — `Serial` AYNASI (SSE artik HER satiri tasiyor)")
    r.bilgi("  Once SSE yalnizca `D` tasiyordu: `akis_yolla` TEK yerden,")
    r.bilgi("  loop()'un rapor blogundan cagriliyordu. Skop yakalamasi")
    r.bilgi("  yapan bir WiFi kullanicisi HICBIR SEY goremezdi.")
    r.bilgi("")

    r.kosul("  1a: `Serial` aynasi kurulu",
            "#define Serial CIKIS" in INO,
            "245 cagri yeri degismeden aynaya gidiyor")
    r.kosul("  1a: makrodan ONCE `#undef` var",
            re.search(r"#undef\s+Serial\s*\n\s*#define\s+Serial\s+CIKIS", INO)
            is not None,
            "cekirdekte `Serial` ZATEN makro — undef'siz 'redefined' uyarisi "
            "veriyor ve bu projede uyariya sifir tolerans var")

    # [!] `#define Serial` butun include'lardan SONRA gelmeli.
    i_tanim = INO.find("#define Serial CIKIS")
    son_include = max(m.start() for m in re.finditer(r"^#include", INO, re.M))
    r.kosul("  1a: `#define Serial` butun #include'lardan SONRA",
            i_tanim > son_include,
            "once gelirse kutuphane basliklarindaki Serial de yeniden adlanir")

    # Nesne olusturulurken `Serial` HALA gercek nesne olmali.
    i_nesne = INO.find("WebAkis CIKIS(Serial)")
    r.kosul("  1a: CIKIS nesnesi makrodan ONCE olusturuluyor",
            0 <= i_nesne < i_tanim,
            "sonra olsaydi kendi kendini sarardi")

    # [!] OZYINELEME: akis_yolla icinde Serial KULLANILAMAZ.
    g_yolla = kod(govde(INO, "static void akis_yolla(const char *satir)"))
    r.kosul("  1b: `akis_yolla` icinde Serial KULLANILMIYOR",
            bool(g_yolla) and "Serial" not in g_yolla,
            "ayna bu fonksiyonu cagiriyor — Serial kullansa SONSUZ OZYINELEME")

    r.kosul("  1b: satir bolucu ayri ve saf C (AVR'de sinaniyor)",
            "satir_ekle" in SATIR_H and "#include <Arduino.h>" not in SATIR_H,
            "sinir kosullari donanimsiz sinanabiliyor (test_olcum3.py)")
    # ⚠ Adin gecmesi yetmiyor — yapi alani ve yorum da adi tasiyor.
    #   ARTIRMA sinaniyor (mutasyon `s->kirpilan++` yerine `(void)0`
    #   koyunca iddia yesil kalmisti). Davranissal karsiligi AVR'de:
    #   test_olcum3.py "Kirpilan bayt SAYILIYOR" -> 77 bayt.
    r.kosul("  1b: kirpilan bayt GERCEKTEN artiriliyor",
            "s->kirpilan++" in kod(SATIR_H),
            "sessiz kirpma yasak")
    r.kosul("  1b: ayna kirpilan sayacini disari veriyor",
            "kirpilan()" in kod(AKIS_H))

    # 🔴 B26 — AYNA + ACIK CAGRI = HER SATIR IKI KEZ.
    #    B20 `loop()`in rapor blogunda `akis_yolla(son_satir)` cagiriyordu;
    #    o sirada SSE'yi besleyen tek yol buydu. B22.4 `Serial` aynasini
    #    getirince tamamlanan her satir zaten `web_satir_hazir()` ->
    #    `akis_yolla()` yolundan gitmeye basladi, ama eski cagri kaldirilmadi.
    #    Tezgahta olculdu: 8 sn'de 80 `D` olayi / 40 benzersiz satir,
    #    tekrar dagilimi {2: 40}. Kart 5/s rapor ederken yayin 10/s idi.
    #    Bir mekanizma daha genelini getirdiginde eskisi KALDIRILMALI.
    #    ⚠ `(?<!void )` SART: yoksa fonksiyonun KENDI TANIMI da cagri
    #      sayiliyor ve iddia dogru kodda bile kirmizi yaniyor.
    #    ⚠ B28'de bu iddianin SEKLI degisti, NIYETI degismedi. Artik
    #      `web_satir_hazir` (cekirdek 1) satiri KUYRUGA birakiyor ve
    #      `akis_kuyrugunu_bosalt` (cekirdek 0) sokete yaziyor. Yani
    #      "tek cagri yeri" olcutu artik yanlis — dogru olcut: sokete
    #      yazan TEK FONKSIYON var ve o da olcum tarafindan cagrilmiyor.
    #      (Bayat iddia tehlikesi: eski hali B28'den sonra da yesildi
    #      diye birakilsa, cift gonderim korumasi yok olurdu.)
    _g_hazir = kod(govde(INO, "void web_satir_hazir"))
    _g_bosalt = kod(govde(INO, "static void akis_kuyrugunu_bosalt()"))
    _cagri_yerleri = [m.start()
                      for m in re.finditer(r"(?<!void )(?<!static void )\bakis_yolla\s*\(", INO_KOD)]
    _bosalt_bas = INO_KOD.find("static void akis_kuyrugunu_bosalt()")
    _bosalt_son = _bosalt_bas + len(_g_bosalt) + 64 if _bosalt_bas >= 0 else -1
    _disarida = [i for i in _cagri_yerleri if not (_bosalt_bas <= i <= _bosalt_son)]
    r.kosul("  1b: sokete yazan TEK yol var (kuyruk bosaltici)",
            _bosalt_bas >= 0 and not _disarida and "akis_yolla(" in _g_bosalt,
            f"{len(_disarida)} cagri bosalticinin DISINDA — ikinci bir yol "
            f"satiri COGALTIR (B26: 8 sn'de 80 olay / 40 benzersiz)")
    r.kosul("  1b: ayna geri cagrisi satiri KUYRUGA veriyor",
            "xQueueSend" in _g_hazir and "akis_yolla" not in _g_hazir)


def bolum2(r):
    bolum(r, "BOLUM 2 — SSE: cok istemci, kalp atisi, yer imi")
    r.bilgi("  Once TEK global `akis_istemci` vardi; ikinci `GET /akis`")
    r.bilgi("  birincisini SESSIZCE uzerine yaziyor ve soketi kapatiyordu.")
    r.bilgi("")

    azami = re.search(r"#define AKIS_AZAMI (\d+)", INO)
    n = int(azami.group(1)) if azami else 0
    r.kosul("  2a: birden fazla SSE istemcisi destekleniyor", n >= 2,
            f"AKIS_AZAMI = {n}")
    r.kosul("  2a: yuva bulunamazsa SEBEBI soyleniyor",
            "event: dolu" in INO,
            "sessizce kapatmak yerine")
    r.kosul("  2b: kalp atisi var (NAT/vekil zaman asimi)",
            "akis_kalp" in INO_KOD and ": kalp" in INO,
            "15 s")
    # B28: kalp atisi da soket isi — ag gorevine tasindi. Cagrilmayan
    # bir kalp atisi yoktur; NEREDEN cagrildigi mimariyle degisir.
    r.kosul("  2b: kalp atisi ag gorevinden cagriliyor",
            "akis_kalp()" in kod(govde(INO, "static void ag_gorevi(void *)")),
            "soketlere dokunan her sey cekirdek 0'da")
    r.kosul("  2c: `id:` yer imi gonderiliyor",
            "id: " in INO and "akis_sira" in INO_KOD,
            "yeniden baglanmada nerede kalindigi bilinsin")
    r.kosul("  2c: `retry:` gonderiliyor", "retry: 3000" in INO)
    # 4B (PC8; spec 2026-09-29 §5 "4 istemci, ret kalkar", §10 "eskiyen iddia GEREKCESIYLE
    #   guncellenir"): eski iki 2d iddiasi ("kopru kayitliysa ikinci istemci REDDEDILIYOR",
    #   "kopru kaydi RAM'de") B22.6'nin TEK SURUCU kuralini kodluyordu. Kopru artik karta
    #   eslesmis cihaz olarak (imzali /akis) baglanan SIRADAN bir istemci ve kendi
    #   tarayicilarina sunucu tarafinda vekil — ikinci tarayiciyi reddetmenin gerekcesi kalmadi.
    #   Yerine: ret yolu YOK, /kopru kaydi YOK; tek ret sebebi 4 yuvanin dolmasi.
    g_akis = kod(govde(INO, "void akis_sayfa()"))
    r.kosul("  2d: [!] kopru tarzi istemci bagliyken ikinci /akis KABUL edilir — tek ret 'yuva dolu'",
            bool(g_akis) and "kopru" not in g_akis and g_akis.count("c.stop()") == 1
            and g_akis.find("event: dolu") < g_akis.find("c.stop()")
            and "kopru_canli" not in INO_KOD and "event: kopru" not in INO,
            "spec §5: 4 canli istemci, kopru kaydina bakilmadan")
    r.kosul("  2d: /kopru kaydi KALKTI (uc, isleyici, adres, omur)",
            '"/kopru"' not in INO_KOD and "kopru_sayfa" not in INO_KOD
            and "kopru_adres" not in INO_KOD and "KOPRU_OMUR_MS" not in INO_KOD,
            "kopru sunucu tarafinda vekil — kartin koprunun kokenini bilmesi gerekmiyor")


def bolum3(r):
    bolum(r, "BOLUM 3 — KOMUT UCU ve CSRF YUZEYI")
    r.bilgi("  Kart bir MOSFET suruyor: `p1` pil desarjini BASLATIYOR.")
    r.bilgi("  GET tabanli bir uc olsaydi <img src=...> ile uzaktan")
    r.bilgi("  tetiklenebilirdi. Ayrica ciplak `g` kanali tuglaliyordu")
    r.bilgi("  (B22.1'de kapatildi) — o da bir <img> ile gonderilebilirdi.")
    r.bilgi("")

    r.kosul("  3a: `/komut` ucu var", '"/komut"' in INO_KOD)
    r.kosul("  3a: YONTEM acikca POST",
            'sunucu.on("/komut", HTTP_POST' in INO_KOD,
            "HTTP_ANY olsaydi GET /komut?k=p1 calisirdi")
    r.kosul("  3a: hicbir uc HTTP_ANY ile kayitli degil",
            "HTTP_ANY" not in INO_KOD)
    # ⚠ GOVDE ICINDE aranmali: once dosya genelinde araniyordu ve
    #   `kopru_sayfa` da ayni denetimi yaptigi icin "komut ucundan
    #   kaldir" mutasyonu KACTI.
    g_kom0 = kod(govde(INO, "void komut_sayfa()"))
    r.kosul("  3b: ozel baslik KOMUT UCUNDA zorunlu",
            'header("X-Olcum")' in g_kom0,
            "<img>/<form> ozel baslik EKLEYEMEZ")
    # 4B (PC8): "ozel baslik KOPRU UCUNDA da zorunlu" iddiasi KALKTI — uc yok (2d). Yerine
    #   eski ucun hicbir yontemle kayitli olmadigi (OPTIONS dahil) denetleniyor.
    r.kosul("  3b: /kopru hicbir yontemle kayitli degil (POST da OPTIONS da)",
            not re.search(r'sunucu\.on\("/kopru"', INO_KOD),
            "yari silinmis uc: isleyicisi gitse de kayit kalirsa derleme degil davranis bozulur")

    # [!] collectHeaders cagrilmazsa header() HER ZAMAN bos doner ve butun
    #    CSRF savunmasi SESSIZCE devre disi kalir.
    # 🔴 Once yalnizca `"collectHeaders" in INO_KOD` bakiyordu ve iddia
    #    GEVSEKTI: `sunucu.collectHeadersX(...)` de geciyordu (B23.3
    #    mutasyon kosucusuyla olculdu — kacti). Artik cagrinin KENDISI
    #    ve toplanacak dizinin ona verildigi aranıyor.
    r.kosul("  3b: `collectHeaders` cagriliyor",
            "sunucu.collectHeaders(toplanacak" in INO_KOD.replace(" ", ""),
            "cagrilmazsa header() hep bos doner ve savunma sessizce oler")
    toplanan = re.search(r"const char \*toplanacak\[\] = \{([^}]*)\}", INO_KOD)
    metin = toplanan.group(1) if toplanan else ""
    r.kosul("  3b: X-Olcum ve X-Jeton toplananlar arasinda",
            "X-Olcum" in metin and "X-Jeton" in metin, metin.strip())

    r.kosul("  3c: oturum jetonu uretiliyor",
            "jeton_uret" in INO_KOD and "esp_random" in INO_KOD)
    r.kosul("  3c: jeton denetleniyor",
            'header("X-Jeton")' in INO_KOD and "oturum_jetonu" in INO_KOD)
    r.kosul("  3d: Host beyaz listesi var (DNS rebinding)",
            "hostHeader" in INO_KOD and "host_gecerli" in INO_KOD,
            "olmadan jeton ve ozel baslik savunmalari da coker")
    r.kosul("  3d: Host denetimi komut ucunda UYGULANIYOR",
            "host_gecerli()" in kod(govde(INO, "void komut_sayfa()")))

    # [!] EMNIYET: p0 her zaman serbest.
    g_ser = kod(govde(INO, "static bool komut_serbest(const char *k)"))
    r.kosul("  3e: [!] `p0` (DURDUR) jetonsuz/parolasiz gecebiliyor",
            "'p'" in g_ser and "'0'" in g_ser,
            "baslatmak yetki ister; durdurmayi hicbir sey geciktiremez")
    g_kom = kod(govde(INO, "void komut_sayfa()"))
    r.kosul("  3e: serbest komut jeton denetimini ATLIYOR",
            "komut_serbest" in g_kom and "!komut_serbest" in g_kom)
    # B27 A2: `?` (ayar dokumu) da serbest — sayfa acilinca K5 esitlemesi
    # parola sorusu acmadan calissin. Ama YALNIZCA tam `?`: `N` (parolalari
    # basar) ve baska hicbir harf serbest OLMAMALI.
    r.kosul("  3e: `?` (ayar dokumu, salt okunur) serbest",
            "'?'" in g_ser and "k[1] == 0" in g_ser,
            "tam eslesme sart: `?x` gecmemeli")
    r.kosul("  3e: [!] `N` (parolalari basar) serbest DEGIL",
            "'N'" not in g_ser and "'p'" in g_ser and g_ser.count("return true") == 2,
            "serbest liste tam olarak iki komut: p0 ve ?")

    r.kosul("  3f: komutlar KUYRUGA giriyor, dogrudan calismiyor",
            "komut_kuyruga" in g_kom and "komut_calistir" not in g_kom,
            "HTTP isleyicisi uzun komut beklemiyor; tek yazar disiplini")
    r.kosul("  3f: kuyrugu loop() bosaltiyor",
            "komut_kuyrugu_bosalt()" in kod(govde(INO, "void loop()")))


def bolum4(r):
    bolum(r, "BOLUM 3b — CIFT CEKIRDEK (B28): ag isi olcumden AYRI mi")
    # ── Bu bolum, B27 A4'te KARTTA OLCULEN kusurun kapandigini civiliyor:
    #    her HTTP istegi olcum dongusunu boyutuyla orantili blokluyordu
    #    (app.js 186 ms, vue 155 ms; esik 20 ms). Cozum: ag isi cekirdek
    #    0'da ayri bir gorevde, arada YALNIZCA kuyruk.
    g_loop = kod(govde(INO, "void loop()"))
    g_gorev = kod(govde(INO, "static void ag_gorevi(void *)"))
    g_hazir = kod(govde(INO, "void web_satir_hazir(const char *satir)"))
    # B40b: imza `static uint8_t skop_yakala()` (sonuc kodu dondurur)
    g_yakala = kod(govde(INO, "static uint8_t skop_yakala()"))
    g_bin = kod(govde(INO, "void skop_bin_sayfa()"))

    r.kosul("  3b.1: [!] loop() ARTIK handleClient cagirmiyor",
            "handleClient" not in g_loop,
            "olcumun sayfa sunumunu beklemesi bu asamanin cozdugu seyin ta kendisi")
    r.kosul("  3b.1: ag gorevi handleClient'i USTLENDI",
            "sunucu.handleClient()" in g_gorev and "akis_kalp()" in g_gorev)
    r.kosul("  3b.2: gorev CEKIRDEK 0'a sabitlendi (WiFi/lwIP orada)",
            "xTaskCreatePinnedToCore(ag_gorevi" in INO
            and re.search(r"xTaskCreatePinnedToCore\(ag_gorevi[^;]*?,\s*&ag_gorev_kolu,\s*0\)",
                          INO, re.S) is not None)
    r.kosul("  3b.2: gorev dongusunde vTaskDelay VAR",
            "vTaskDelay" in g_gorev,
            "tik birakilmazsa IDLE0 ac kalir ve gorev bekci kopegi karti yeniden baslatir")

    # Cekirdekler arasi tek gecit: kuyruklar. Elle sayacli halka tamponu
    # iki cekirdekte YARIS demek (kayip komut ya da cift calisma).
    r.kosul("  3b.3: komut kuyrugu FreeRTOS kuyrugu (elle sayac DEGIL)",
            "xQueueSend(komut_kuyrugu_q" in INO
            and "xQueueReceive(komut_kuyrugu_q" in INO
            and "komut_adet" not in INO_KOD)   # yorumlar haric: tarihce anlatiyor
    r.kosul("  3b.3: komutlar hala OLCUM cekirdeginde calisiyor (tek yazar)",
            "komut_kuyrugu_bosalt()" in g_loop and "komut_calistir" not in g_gorev,
            "kalibrasyon, NVS ve skop tek cekirdekten yaziliyor")

    # 🔴 B26'nin dersi burada da gecerli: sokete YAZAN tek bir yol olmali.
    r.kosul("  3b.4: [!] web_satir_hazir SOKETE YAZMIYOR, kuyruga birakiyor",
            "xQueueSend(akis_kuyrugu_q" in g_hazir and "akis_yolla" not in g_hazir,
            "olcum cekirdeginden TCP yazmak hem akis[] dizisinde ikinci "
            "yazar demek hem de bu asamanin kaldirdigi blokajin geri gelmesi")
    r.kosul("  3b.4: satirlari ag gorevi bosaltiyor",
            "akis_kuyrugunu_bosalt()" in g_gorev
            and "akis_yolla" in kod(govde(INO, "static void akis_kuyrugunu_bosalt()")))
    r.kosul("  3b.4: kuyruga birakma BEKLEMESIZ (olcum asla bloklanmaz)",
            "xQueueSend(akis_kuyrugu_q, &ak, 0)" in g_hazir)
    r.kosul("  3b.4: [!] dusen satir SESSIZ KALMIYOR",
            "satir dustu" in kod(govde(INO, "static void akis_kuyrugunu_bosalt()")),
            "eksik bir skop dokumunu tam sanmak, dusmesinden kotudur")

    # Skop tamponu iki cekirdekten gorulen TEK paylasilan tampon.
    r.kosul("  3b.5: skop yakalamasi kilidi BEKLEMEDEN aliyor (timeout 0)",
            "xSemaphoreTake(skop_kilidi, 0)" in g_yakala,
            "olcum tarafi beklerse cift cekirdegin anlami kalmaz")
    r.kosul("  3b.5: /skop.bin okuyucusu BEKLEYEN taraf",
            "xSemaphoreTake(skop_kilidi, pdMS_TO_TICKS" in g_bin
            and "503" in g_bin)

    # Seri cikti: cift cekirdekten sonra geriye kalan tek >20 ms kaynagi.
    r.kosul("  3b.6: seri TX tamponu begin()'den ONCE buyutuluyor",
            INO.find("setTxBufferSize") < INO.find("Serial.begin(115200)")
            and "setTxBufferSize" in INO,
            "`?` ciktisi (9 satir) varsayilan tamponu doldurup print'i "
            "blokluyordu: olculdu, 27 ms")
    # 🔴 B37 — TAMPONUN BUYUKLUGU de sinaniyor. IDF'nin TX halkasi
    #    NOSPLIT: her write cagrisi ~12 B baslik+hizalama tasiyor ve
    #    `Print::print(float)` rakam rakam yaziyor. `?` 548 bayt basip
    #    ~1.4 KB halka yeri yiyor; 2048'de doluyor ve 19.4 ms blokluyordu
    #    (kartta olculdu: 1000 baytlik tek write 229 us, ama 200'luk
    #    parcalar 1600 baytta bloklamaya basliyor). 8 KB ile `?` 5.8 ms.
    #    B34-B36'da `?` buyudukce birikmis, bringup koşucusu yakaladi.
    _tx = re.search(r"setTxBufferSize\((\d+)\)", INO)
    r.kosul("  3b.6: [!] seri TX tamponu >= 8 KB (halka ogesi basina ~12 B ek yuk)",
            _tx is not None and int(_tx.group(1)) >= 8192,
            f"{_tx.group(1) if _tx else '?'} B — 2048'de `?` 19.4 ms, "
            f"bringup esigi 20 ms: kil payi ve buyuyen her cikti asar")
    r.kosul("  3b.7: `C` telemetri satiri cekirdek/yigin/dusen bildiriyor",
            all(x in kod(govde(INO, "void ayar_yaz_seri()"))
                for x in ("olcum_cekirdek=", "ag_yigin_dip=", "akis_dusen=")),
            "yigin payi TAHMIN degil OLCULEN sayi olmali")

    bolum(r, "BOLUM 4 — CORS: `enableCORS(true)` KULLANILMAMALI")
    r.bilgi("  WebServer::enableCORS(true) uc basligi da `*` yapiyor")
    r.bilgi("  (WebServer.cpp:663-667): Allow-Origin, Allow-Methods,")
    r.bilgi("  Allow-Headers. Boylece HERHANGI bir sayfa yaniti OKUYABILIR")
    r.bilgi("  ve oturum jetonu sizar — jeton savunmasinin tamami coker.")
    r.bilgi("")
    r.kosul("  4a: `enableCORS` kullanilmiyor",
            "enableCORS" not in INO_KOD,
            "yerine kayitli kopru kokenine ELLE izin veriliyor")
    # 4B (PC8): eski "4a: ACAO yalnizca kayitli kopruye veriliyor" iddiasi KALKTI. Kopru
    #   karta tarayicidan degil SUNUCU TARAFINDAN (eslesmis cihaz, imzali istek) gidiyor;
    #   hicbir kokenin karti tarayicidan capraz okumasina gerek yok. CORS izni artik HIC
    #   verilmiyor: ne `/akis`'te ne bir on-ucus (OPTIONS) isleyicisinde. Saldiri yuzeyi
    #   kuculdu: kayitli kopru adresini taklit eden (ayni agdaki) bir kokene yanit okutulamaz.
    r.kosul("  4a: [!] hicbir koken icin Access-Control-Allow-Origin verilmiyor",
            "Access-Control-Allow" not in INO and "HTTP_OPTIONS" not in INO_KOD
            and "onuc_sayfa" not in INO_KOD,
            "kart tarayicidan yalniz kendi kokeninden kullanilir; kopru sunucu tarafinda vekil")
    # `ACAO: null` da yasak — sandbox'li iframe'ler de `null` kokenli.
    r.kosul("  4b: `Access-Control-Allow-Origin: null` verilmiyor",
            'Allow-Origin"), F("null")' not in INO and 'Allow-Origin: null' not in INO,
            "sandbox'li iframe'ler de null kokenli — acik kapi olurdu")


def bolum5(r):
    bolum(r, "BOLUM 5 — AG: STA -> AP dususu, NVS ayriligi, sir sizintisi")
    r.bilgi("  B22.4 oncesi `WIFI_AD` bos bir sabitti: WiFi HIC acilmadi.")
    r.bilgi("")
    r.kosul("  5a: eski sabitler kaldirildi",
            "WIFI_AD" not in INO_KOD and "WIFI_SIFRE" not in INO_KOD)
    r.kosul("  5a: STA denenip AP'ye DUSULUYOR",
            "WIFI_STA" in AG_KOD and "softAP" in AG_KOD,
            "AP kipi olmadan 'bilgisayar yoksa' senaryosu ag altyapisina "
            "bagimli kalirdi")
    r.kosul("  5a: mDNS kuruluyor", "MDNS.begin" in AG_KOD)
    # 🔴 Ad BOSALIRSA `http://<ad>.local` cozulmez ve BELGELER/6-ag.html
    #    bos adres yazar — B23.3 mutasyonu bunu KACIRDI, iddia yoktu.
    _mdns = re.search(r'#define AG_MDNS\s+"([^"]*)"', AG_KOD)
    # 🔴 Afis satirlarinin KAPANDIGI denetimi. "Ag: ..." blogunun sonunda
    #    println YOKTU ve cikti `http://192.168.4.1Arayuz: ...` seklinde
    #    yapisiyordu — adresi kopyalayan kullanici BOZUK adres aliyordu.
    #    B25 bringup kosucusu hazirlanirken bulundu (2026-09-11).
    #    ⚠ Kapsam: 1E-2'den beri satir `ag_satiri_bas()`te (STA sonucu
    #    loop()'tan da basilabiliyor): o govdenin ICINDE "Ag: " ile AP
    #    parolasi blogu arasindaki parcaya bakiyoruz — tum dosyada aramak
    #    komsu fonksiyonlarin println'lerini kabul ederdi.
    _kur = govde(INO, "static void ag_satiri_bas()")
    _i = _kur.find('F("Ag: ")')
    _j = _kur.find("if (ag_durum.kip == AG_AP)", _i + 1)
    _ara = _kur[_i:_j] if 0 <= _i < _j else ""
    r.kosul("  5a: `Ag:` satiri sonraki satirdan ONCE KAPANIYOR",
            "Serial.println();" in _ara.replace(" ", "").replace(
                "Serial.println()", "Serial.println();").replace(";;", ";"),
            "kapanmazsa IP adresi bir sonraki etikete yapisir ve "
            "kullanici bozuk adres kopyalar")
    # ── 1E-2 (2026-10-02): STA beklemesi setup()'tan ag gorevine tasindi.
    #    Kartta olculdu: sifirlamadan ilk `D`ye 5.7-7.2 s, ev agi yoksa > 10 s.
    _rf = govde(AG_KOD, "static uint8_t ag_baslat_rf(void)")
    _bk = govde(AG_KOD, "static void ag_bekle_tamamla(void)")
    _gv = govde(INO, "static void ag_gorevi(void *)")
    r.kosul("  5k: setup() STA BEKLEMEZ — ag_baslat_rf yalniz radyoyu acar (dongu/bekleme yok)",
            bool(_rf) and "WiFi.begin(" in _rf and not re.search(r"\bwhile\b|delay\(|vTaskDelay", _rf)
            and "ag_baslat_rf();" in govde(INO, "void setup()")
            and not re.search(r"while\s*\(\s*WiFi\.status\(\)", govde(INO, "void setup()")),
            "setup() beklerse olcum dongusu ag gelene dek (10 s'ye dek) durur")
    # AGD: bekleme dongusu karar motoruyla (ag_karar.h); AP'ye dusus ag__uygula'da.
    _uy = govde(AG_KOD, "static void ag__uygula(uint8_t e)")
    _so = govde(AG_KOD, "static void ag__sta_oldu(void)")
    r.kosul("  5k: STA beklemesi ag gorevinde, SUNUCU DONGUSUNDEN ONCE; olmazsa AP'ye duser",
            bool(_bk) and "while (ag_k.evre == AGK_BEKLE)" in _bk
            and "ag__uygula(agk_adim(&ag_k, millis(), WiFi.status() == WL_CONNECTED" in _bk
            and "ag__ap_kur(WIFI_AP_STA)" in _uy
            and 0 <= _gv.find("ag_bekle_tamamla();") < _gv.find("for (;;)"))
    r.kosul("  5k: kip EN SON yazilir (alanlar once): baska gorev AG_STA'yi gorunce ip/mac hazir",
            bool(_so) and 0 <= _so.find("ag_durum.ip") < _so.find("ag__kip_yaz(AG_STA)")
            and 0 <= _so.find("ag_durum.mac") < _so.find("ag__kip_yaz(AG_STA)")
            and "ag_durum.kip = AG_AP" not in AG_KOD and "ag_durum.kip = AG_STA" not in AG_KOD)
    r.kosul("  5k: STA sonucu `Ag:` satiri cekirdek 1'de basilir (loop; AGD: her kip degisiminde bir kez)",
            "if (ag_hazir != ag_satiri_basildi) ag_satiri_bas();" in govde(INO, "void loop()"))

    r.kosul("  5a: mDNS adi BOS DEGIL", bool(_mdns and _mdns.group(1)),
            f"http://{_mdns.group(1) if _mdns else '?'}.local")
    r.kosul("  5a: MDNS.begin adi sabitten aliyor",
            "MDNS.begin(AG_MDNS)" in AG_KOD.replace(" ", ""),
            "elle yazilirsa sabitle sessizce ayrisir")

    # [!] `Ns` (web parolasi) ANINDA gecerli — web_yetkili() her istekte
    #     NVS'ten okuyor. `N` komutunun ortak kuyrugu ise "bir sonraki
    #     acilista gecerli" diyor. Ns o kuyruga DUSERSE, korumayi KALDIRAN
    #     kullaniciya korumanin surdugu soylenmis olur. Yani mesajin
    #     dogrulugu bir EMNIYET ozelligi.
    #     ⚠ Kapsam: yorumlar ciplak metinde de gecebilir, o yuzden
    #     yalnizca KOD uzerinde ve `alt == 's'` dalinin ICINDE ariyoruz.
    #     🔴 Ilk yazimda dilim `alt == 's'`den ortak kuyruga kadardi ve
    #     SONRAKI dallarin `break`lerini de iceriyordu — mutasyon (Ns'in
    #     kendi break'ini sil) KACTI. Dilim artik yalnizca o dalin govdesi:
    #     `alt == 's'`den bir SONRAKI `else`e kadar.
    _ns = INO_KOD.find("alt == 's'")
    _son = INO_KOD.find("else", _ns + 1) if _ns >= 0 else -1
    _dal = INO_KOD[_ns:_son] if 0 <= _ns < _son else ""
    r.kosul("  5b: `Ns` dali ortak 'sonraki acilis' kuyruguna DUSMUYOR",
            "break" in _dal,
            "Ns ANINDA gecerli; kuyruga duserse parolayi KALDIRAN "
            "kullaniciya korumanin surdugu soylenir")
    r.kosul("  5b: parola KALDIRILDI mesaji korumasizligi SOYLUYOR",
            "korumasiz" in _dal,
            "sessiz 'kaldirildi' yeterli degil — komut ucu o an aciliyor")

    # [!] NVS AYRILIGI: Ayar3 buyurse imza bumplanir ve KALIBRASYON GIDER.
    r.kosul("  5b: ag ayarlari AYRI NVS ad alaninda",
            'AG_ALAN "olcumag"' in AG_H and '"olcum3"' not in AG_KOD,
            "Ayar3 buyurse sizeof denetimi bozulur, imza bumplanir ve "
            "KALIBRASYON SIFIRLANIR — bir WiFi parolasi buna mal olamaz")
    r.kosul("  5b: `Ayar3` yapisina ag alani EKLENMEDI",
            "wifi" not in (KOD / "tipler3.h").read_text(
                encoding="utf-8", errors="replace").lower())

    # [!] SIR SIZINTISI: parola kaynak kodda olmamali (ikilide duz metin).
    # ⚠ Desen ONCE `wifi_`/`ap_` oneki istiyordu; `String sifre = "..."`
    #   bicimindeki mutasyon KACTI. Artik adin ICINDE sifre/parola/pass
    #   gecen HER degiskene atanan uzun dize yakalaniyor.
    sabit = re.search(r'\b\w*(sifre|parola|pass\w*)\s*=\s*"[^"]{4,}"',
                      INO_KOD + AG_KOD, re.I)
    r.kosul("  5c: kaynakta sabit parola YOK", sabit is None,
            sabit.group(0)[:48] if sabit else "kimlik bilgileri NVS'ten")
    r.kosul("  5c: kimlik bilgileri NVS'ten okunuyor",
            'getString("wifi_ad"' in AG_KOD and 'getString("wifi_sifre"' in AG_KOD)
    # ⚠ Adin GECMESI yetmiyor: cagri yeri kalip TANIM yeniden adlansa
    #   iddia yine yesil yanardi (mutasyon KACTI). Govde sinaniyor.
    g_par = kod(govde(AG_H, "static void ag_rastgele_parola"))
    r.kosul("  5c: AP parolasi RASTGELE uretiliyor, MAC'ten TURETILMIYOR",
            bool(g_par) and "esp_random" in g_par
            and "macAddress" not in g_par,
            "SSID zaten MAC son ekini yayinliyor — MAC turevi parola "
            "HICBIR SEY korumaz")
    r.kosul("  5c: WPA2 asgari uzunlugu denetleniyor",
            "< 8" in AG_KOD or "strlen(deg) < 8" in INO_KOD)

    # 🔴 B26 (2026-09-11) — GERCEK KARTTA bulundu, tasarim zinciri
    #    18/18 yesilken GORUNMUYORDU. `ag_baslat()` `ag_ap_ssid()`'yi
    #    `WiFi.mode()`'dan ONCE cagiriyor; kayitli ev agi yokken WiFi
    #    surucusu o ana kadar hic baslamamis oluyor ve
    #    `WiFi.macAddress()` tampona DOKUNMUYOR (ESP_ERR_WIFI_NOT_INIT).
    #    Sonuc: SSID'e ILKLENMEMIS YIGIN BELLEGI giriyordu. Kartin
    #    gercek MAC'i ...:96:9c iken ad `OLCUM-KARTI-ABAB`
    #    cikti (AB AB = dolgu bayti deseni). Deger acilislar arasinda
    #    SABIT kaldigi icin kusur "rastgele ad" gibi de gorunmuyordu.
    g_ssid = kod(govde(AG_H, "static String ag_ap_ssid"))
    r.kosul("  5c: AP SSID'i eFuse MAC'inden (esp_read_mac) turetiliyor",
            bool(g_ssid) and "esp_read_mac" in g_ssid
            and "WiFi.macAddress" not in g_ssid,
            "esp_read_mac eFuse'tan okur, WiFi surucusunun baslatilmis "
            "olmasini gerektirmez; WiFi.macAddress() gerektirir")
    # Kartta sinanan iddianin BAGIMSIZ olcutu: afis, softAP ayaga
    # kalktiktan SONRA okunan GERCEK MAC'i da basmali. Ayni kaynaktan
    # okusaydi tezgah denetimi totoloji olur, eski kusuru kacirirdi.
    # ⚠ Ilk yazimda kosul `"MAC=" in INO` idi ve MUTASYON KACTI: afis
    #   satiri silinse bile `N` komut ciktisindaki kopya iddiayi yesil
    #   tutuyordu. Kosucu AFISI okuyor, `N`'i degil — kapsam setup()'a
    #   daraltildi. (mutasyon.py bunu ilk turda yakaladi.)
    #   1E-2: afisin "Ag:" satiri `ag_satiri_bas()`te — setup (AP/KAPALI) ve
    #   loop (STA sonucu) ONU cagiriyor; kapsam o govde + iki cagri.
    g_setup = govde(INO, "void setup()")
    g_agsat = govde(INO, "static void ag_satiri_bas()")
    _afis_yolu = ("ag_satiri_bas();" in kod(g_setup)
                  and "ag_satiri_bas();" in kod(govde(INO, "void loop()")))
    r.kosul("  5c: ACILIS AFISI gercek MAC'i da ilan ediyor",
            "MAC=" in g_agsat and "ag_durum.mac" in kod(g_agsat) and _afis_yolu,
            "tezgah_kart.py SSID sonekini AFISTEKI MAC ile "
            "karsilastiriyor; `N` ciktisindaki kopya yetmez")

    r.kosul("  5d: web parolasi YOKSA acilista UYARILIYOR",
            "web parolasi YOK" in INO,
            "sessiz 'guvenlik yok', guvenlik olmamasindan kotudur")
    r.kosul("  5d: ag durumu acilista BASILIYOR",
            "ag_kip_adi" in kod(g_agsat) and _afis_yolu,
            "DEVIR 4.9 kurali: durum sessiz kalamaz")

    r.kosul("  5e: `N` komut ailesi arayuzden erisilebilir olmali",
            "case 'N'" in INO_KOD,
            "ters yon denetimini test_arayuz3.js yapiyor")


def bolum6(r):
    bolum(r, "BOLUM 6 — ARAYUZ KARTTAN SERVIS EDILIYOR (B22.5)")
    r.bilgi("  Kart artik arayuzu KENDISI sunuyor: 'bilgisayar yoksa'")
    r.bilgi("  senaryosu tamamlaniyor. LittleFS bolumu 0xE0000 = 917 504 B")
    r.bilgi("  ve bugune kadar TAMAMEN BOS duruyordu.")
    r.bilgi("")

    g_setup = kod(govde(INO, "void setup()"))
    r.kosul("  6a: LittleFS baglaniyor", "LittleFS.begin(" in g_setup)
    r.kosul("  6a: OTOMATIK BICIMLENDIRME yok",
            "LittleFS.begin(false)" in g_setup,
            "basarisiz bir yazma 'bos dosya sistemi'ne donusup sebebi "
            "gizlerdi; bos bolum bir HATA degil, kok_sayfa bunu SOYLUYOR")

    # W6: `serveStatic` yerine `ArayuzIsleyici` (ayni yol/gz/MIME kurali + ETag/304).
    _kayit = re.compile(r'addHandler\(new ArayuzIsleyici\("([^"]*)",\s*"([^"]*)"\)\)')
    _isleyiciler = [(m.start(), m.group(1), m.group(2)) for m in _kayit.finditer(g_setup)]
    _vendor = [x for x in _isleyiciler if x[1] == "/vendor/"]
    _kokler = [x for x in _isleyiciler if x[1] == "/"]
    i_vendor = _vendor[0][0] if _vendor else -1
    i_kok = _kokler[0][0] if _kokler else -1
    r.kosul("  6b: `/vendor/` statik servisi kayitli", i_vendor >= 0 and "serveStatic" not in g_setup)
    r.kosul("  6b: `/vendor/` daha OZEL oldugu icin ONCE kayitli",
            0 <= i_vendor < i_kok,
            "sonra kayitli olsaydi `/` onu golgelerdi")
    r.kosul("  6b: vendor `immutable` (Vue bir kez iniyor)",
            bool(_vendor) and "immutable" in _vendor[0][2],
            "58 KB'lik indirme telefonda her acilista tekrarlanmasin")
    # [!] index.html immutable OLMAMALI: yoksa arayuz guncellemesi
    #    tarayiciya HIC ulasmaz. W6: `/index.html` istegi de bu isleyiciye dusuyor.
    r.kosul("  6b: kok servisi `no-cache` (arayuz guncellemesi gorulsun)",
            len(_kokler) == 1 and _kokler[0][2] == "no-cache" and len(_isleyiciler) == 2,
            "immutable olsaydi guncelleme tarayiciya hic ulasmazdi")

    # [!] `index.htm` TUZAGI
    g_kok = kod(govde(INO, "void kok_sayfa()"))
    r.kosul("  6c: ACIK kok isleyicisi var (index.htm tuzagi)",
            "index.html.gz" in g_kok
            and re.search(r'arayuz_gonder\(f,\s*"/index\.html",\s*String\(F\("text/html"\)\),\s*"no-cache"\)',
                          g_kok) is not None and "immutable" not in g_kok,
            "serveStatic dizin istegini `index.htm` ile karsiliyor "
            "(RequestHandlersImpl.h:198), `index.html` DEGIL; W6: no-cache + ETag, ASLA immutable")
    r.kosul("  6c: goruntu yoksa NE YAPILACAGI yaziliyor",
            "arayuz-yaz.py" in g_kok,
            "bos sayfa birakmak kullaniciyi 'calismiyor' sanisina iter")

    r.kosul("  6d: `enableETag` KULLANILMIYOR",
            "enableETag" not in INO_KOD,
            "calcETag dosyanin TAMAMINI okuyup ozet cikariyor — gondermek "
            "kadar bloklar; `immutable` ayni isi sifir maliyetle yapiyor")

    # ── W6: ETag + If-None-Match -> 304 (karar web_etag.h'de, AVR'de 6q) ──
    _top = re.search(r"toplanacak\[\]\s*=\s*\{([^}]*)\}", g_setup)
    r.kosul("  6q: [!] W6: `If-None-Match` toplaniyor; adet DIZIDEN (elle sayi yeni basligi disarida birakirdi)",
            _top is not None and '"If-None-Match"' in _top.group(1)
            and "collectHeaders(toplanacak, sizeof(toplanacak) / sizeof(toplanacak[0]))" in g_setup,
            "toplanmazsa sunucu.header() hep bos: HIC 304 olmaz, sessizce W6 oncesi")
    g_gon = kod(govde(INO, "static void arayuz_gonder("))
    _i_cc, _i_var = g_gon.find('sendHeader(F("Cache-Control"), onbellek)'), g_gon.find("if (var)")
    _i_et, _i_304 = g_gon.find('sendHeader(F("ETag"), etag)'), g_gon.find("send(304, tur, String())")
    _i_ret, _i_akis = g_gon.find("return;", _i_304), g_gon.find("streamFile(f, tur)")
    r.kosul("  6q: [!] W6: ETag YALNIZ kunyede bulununca; 304 GOVDESIZ ve streamFile'dan ONCE doner",
            0 <= _i_cc < _i_var < _i_et < _i_304 < _i_ret < _i_akis
            and "etag_eslesir(sunucu.header(\"If-None-Match\").c_str(), etag)" in g_gon
            and 0 <= g_gon.find("setContentLength(f.size())") < _i_304
            and "etag_bul(etag_kunye, istek_yolu, etag)" in g_gon,
            "Cache-Control 304'te de var; Content-Length 200'unki (RFC 9110 8.6), 0 degil")
    _ai_h = govde(kod(govde(INO, "class ArayuzIsleyici")),
                  "bool handle(WebServer &, HTTPMethod m, const String &uri)")
    r.kosul("  6q: W6: ETag ISTEK yoluyla aranir (`/app.js`), goruntudeki `.gz` yoluyla DEGIL",
            "arayuz_gonder(f, uri.c_str()," in _ai_h,
            "kunye istek yolunu tutuyor; `.gz` ile aransa hicbir dosya ETag almazdi")
    g_yk = kod(govde(INO, "static void etag_kunye_yukle()"))
    _i_yk = g_setup.find("etag_kunye_yukle();")
    r.kosul("  6q: W6: kunye isleyicilerden ONCE, bir kez, PSRAM'e okunuyor (statik DRAM payi ~80 B)",
            0 <= _i_yk < i_vendor and f'"/{uretec().ETAG_KUNYE}"' in g_yk
            and "MALLOC_CAP_SPIRAM" in g_yk and "etag_kunye = b;" in g_yk,
            f"/{uretec().ETAG_KUNYE}; yoksa ETag'siz (W6 oncesi davranis)")
    _hx = re.search(r"#define WEB_ETAG_HEX\s+(\d+)u", (KOD / "web_etag.h").read_text(encoding="utf-8"))
    r.kosul("  6q: W6: kartin ETag uzunlugu uretecinkiyle AYNI (web_etag.h <-> arayuz-uret.py)",
            _hx is not None and int(_hx.group(1)) == len(uretec().etag_ozet(b"")) == 16
            and '#include "web_etag.h"' in INO_KOD,
            f"{_hx.group(1) if _hx else '?'} onaltilik")

    # ── Toplu uclar: bitisik tampon ve blokaj ────────────────────────
    n = re.search(r"#define PIL_YANIT_NOKTA (\d+)u", INO)
    nokta = int(n.group(1)) if n else 0
    r.kosul("  6e: PIL_YANIT_NOKTA dusuruldu", 0 < nokta <= 200,
            f"{nokta} nokta ~ {nokta * 25} B  (600 iken ~15 KB idi)")
    g_pil = kod(govde(INO, "void pil_sayfa()"))
    r.kosul("  6e: pil ucu PARCALI gonderiyor",
            "sendContent" in g_pil and "CONTENT_LENGTH_UNKNOWN" in g_pil,
            "bitisik 20 KB'lik String, parcalanmis yiginda BASARISIZ olup "
            "sessizce kesik govde uretebiliyordu")
    r.kosul("  6e: pil ucu bitisik buyuk tampon ISTEMIYOR",
            "n * 34" not in g_pil and "n*34" not in g_pil)

    # ── Ikili skop ───────────────────────────────────────────────────
    g_bin = kod(govde(INO, "void skop_bin_sayfa()"))
    r.kosul("  6f: `/skop.bin` ucu kayitli", '"/skop.bin"' in INO_KOD)
    r.kosul("  6f: ikili baslik imzali", "'S'" in g_bin and "'3'" in g_bin
            and "'B'" in g_bin, "kismi yanit sessizce cizilmesin")
    r.kosul("  6f: ikili dokum de PARCALI", "sendContent" in g_bin)
    r.kosul("  6f: Host denetimi ikili ucta da var", "host_gecerli()" in g_bin)
    # [!] Tuketicisi olmayan bir uc yarim istir (B17'nin f/F kusuru).
    g_skop = kod(govde(INO, "void skop_komut(const char *s)"))
    # B40b: `tB` yakalamayi cekirdek 0'daki goreve veriyor.
    r.kosul("  6g: `tB` — ASCII DOKMEDEN yakalama komutu var",
            "'B'" in g_skop and "skop_is_ver(SKOP_IS_IKILI)" in g_skop,
            "yoksa WiFi'de ayni veri IKI KEZ tasinirdi (ASCII + ikili)")
    r.kosul("  6g: `tB` onayi `!` ile BASLAMIYOR",
            "* skop yakalandi (ikili)" in INO,
            "arayuz `!` gorunce skop beklemesini IPTAL ediyor")

    # ── Goruntu varlik listesi ───────────────────────────────────────
    uret = (BURASI / "arayuz-uret.py").read_text(encoding="utf-8",
                                                 errors="replace")
    m = re.search(r"VARLIKLAR = \[(.*?)\]", uret, re.S)
    varliklar = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
    html = (KOK / "arayuz3" / "index.html").read_text(encoding="utf-8",
                                                      errors="replace")
    # ⚠ `(?:^|\s)` sart: `:href="kopruAdresi"` bir Vue BAGLAMASI, dosya
    #   yolu degil. Onsuz `:href` de esleserek "goruntude yok" diyordu.
    #   (Ayni kusur test_arayuz3.js'te de cikmisti — iki yerde ayni
    #   deseni yazmanin bedeli.)
    istenen = {u for u in re.findall(r'(?:^|\s)(?:href|src)="([^"]+)"',
                                     html, re.M)
               if not re.match(r"^(https?:|data:|#|mailto:)", u)}
    istenen.add("index.html")
    eksik = istenen - varliklar
    r.kosul("  6h: index.html'in istedigi HER varlik goruntude",
            not eksik, " ".join(sorted(eksik)) or f"{len(varliklar)} varlik",
            )
    r.kosul("  6h: `sahte-kart.js` goruntuye GIRMIYOR",
            "sahte-kart.js" not in varliklar,
            "15 936 B, yalnizca ?demo icin — dinamik iniyor")

    # ── Telefonda uygulama gibi ──────────────────────────────────────
    # ⚠ HTML YORUMLARI CIKARILIYOR. Ilk yazimda `apple-mobile-web-app-
    #   capable` dizesi etiketin USTUNDEKI aciklama yorumunda da geciyordu
    #   ve "etiketi kaldir" mutasyonu KACTI. Bu sinif kusurun bu oturumda
    #   ALTINCI ortaya cikisi (CSS sinifi, NVS imzasi, faz_kal alani,
    #   .uyari govdesi, komut toplayici, simdi de HTML yorumu).
    html_kod = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    r.kosul("  6i: iOS tam ekran etiketi var",
            "apple-mobile-web-app-capable" in html_kod,
            "duz HTTP'de calisiyor; Android'de gercek PWA HTTPS ister")
    r.kosul("  6i: ikon ve manifest bagli",
            "apple-touch-icon" in html_kod and 'rel="manifest"' in html_kod)
    r.kosul("  6i: ikon URETILIYOR, depoda elle konmus ikili degil",
            (BURASI / "ikon-uret.py").exists()
            and (KOK / "arayuz3" / "ikon-180.png").exists())

    # ── 3A: ES MODULLERI KARTTAN DA YUKLENEBILMELI ───────────────────
    # `app.js` artik `<script type="module">` ve `ekran/tema.js`i import
    # ediyor; panel ileride `/ortak/*.js`i de alacak. Tarayici modul betigini
    # YALNIZCA JavaScript MIME turuyle calistirir (`text/plain` gelirse sayfa
    # HIC acilmaz). FIRMWARE DEGISMEDI: bu istekler kok statik isleyiciye
    # (W6'dan beri `ArayuzIsleyici("/")`) dusuyor; MIME tablosu ve gzip basligi
    # CEKIRDEKTEN — kurulu cekirdekten okunuyor, varsayilmiyor.
    r.kosul("  6n: `/ekran/`, `/ortak/` icin ozel isleyici YOK — kok statik isleyici sunuyor",
            '"/ortak' not in INO_KOD and '"/ekran' not in INO_KOD and i_kok >= 0)
    cekirdek = _cekirdek_webserver()
    if cekirdek is None:
        r.bilgi("     ESP32 cekirdegi (WebServer) bulunamadi — MIME/gzip denetimi ATLANDI.")
        r.kosul("  6n: cekirdek yoksa bu ACIKCA soyleniyor", True, "sessiz atlama degil")
    else:
        _mime = (cekirdek / "detail" / "mimetable.cpp").read_text(encoding="utf-8", errors="replace")
        _js = re.search(r'\{\s*"\.js"\s*,\s*"([^"]+)"\s*\}', _mime)
        r.kosul("  6n: [!] cekirdek `.js` -> JavaScript MIME (modul betigi bunu ister)",
                _js is not None and _js.group(1) in ("application/javascript", "text/javascript"),
                f"esp32 {cekirdek.parents[2].name}: {_js.group(1) if _js else '.js satiri yok'}")
        _isl = kod((cekirdek / "detail" / "RequestHandlersImpl.h").read_text(
            encoding="utf-8", errors="replace"))
        # ⚠ Ayni imzali `handle` FunctionRequestHandler'da da var — sinifin ICINDE ara.
        _sbt = govde(_isl[max(0, _isl.find("class StaticRequestHandler")):],
                     "bool handle(WebServer &server, HTTPMethod requestMethod, const String &requestUri)")
        _i_tur, _i_gz = _sbt.find("getContentType(path)"), _sbt.find("pathWithGz")
        _ws = kod((cekirdek / "WebServer.cpp").read_text(encoding="utf-8", errors="replace"))
        # W6: kartta artik `ArayuzIsleyici` sunuyor — cekirdegin kurali (MIME `.gz`
        #   eklenmeden ONCE, ASIL yoldan; varsayilan tablonun SONUNCUSU) onda da aynen.
        _ai = kod(govde(INO, "class ArayuzIsleyici"))
        _ai_h = govde(_ai, "bool handle(WebServer &, HTTPMethod m, const String &uri)")
        _tur = kod(govde(INO, "static String arayuz_tur(const String &yol)"))
        r.kosul("  6n: `.gz`e dususte MIME ASIL yoldan, Content-Encoding: gzip cekirdekten",
                0 <= _i_tur < _i_gz
                and "sizeof(mimeTable) / sizeof(mimeTable[0]) - 1" in _isl
                and "arayuz_tur(uri)" in _ai_h and 'yol += ".gz"' in _ai_h
                and "(int)maxType - 1" in _tur and "mimeTable[maxType - 1].mimeType" in _tur
                and 'sendHeader(F("Content-Encoding"), F("gzip"))' in govde(_ws, "void WebServer::_streamFileCore("),
                "x.js istenir, x.js.gz gonderilir, tur application/javascript kalir (W6: ArayuzIsleyici)")
        # W6 inceleme: yukaridaki alt dize denetimi `exists(yol)` / `startsWith` gibi tek
        #   belirteclik bozulmalari GECIRIYORDU — davranis kartin metniyle AVR'de (6r).
        bolum6_arayuz_isleyici(r, cekirdek, [(o, b) for _i, o, b in _isleyiciler])

    # ── Goruntunun bayatligi ─────────────────────────────────────────
    r.kosul("  6j: uretec ve yazici var",
            (BURASI / "arayuz-uret.py").exists()
            and (BURASI / "arayuz-yaz.py").exists())
    kunye = BURASI / "_fs.json"
    if not kunye.exists():
        # Iddia SESSIZCE kaybolmasin: yoklugu ACIKCA raporlaniyor.
        r.bilgi("     _fs.json yok — goruntu henuz uretilmedi "
                "(python arayuz-uret.py). Bayatlik denetimi ATLANDI.")
        r.kosul("  6j: goruntu yoksa bu ACIKCA soyleniyor", True,
                "sessiz atlama degil")
    else:
        import hashlib, json as _json
        k = _json.loads(kunye.read_text(encoding="utf-8"))
        # 3A: goruntu `/ortak/` (ortak/src) ve `/ekran/` de tasiyor. Kaynak
        #   yolu ve "goruntuye ne girer" listesi URETECIN fonksiyonlarindan
        #   (arayuz-yaz.py de ayni ikisini kullaniyor) — burada ikinci bir
        #   kopya kural yazilsaydi uc yer ayrisabilirdi. Uretimden SONRA
        #   eklenen bir ekran/ortak dosyasi da bayatlik: kartta 404 olur.
        _uret = uretec()
        bayat = [ad for ad, ozet in k["kaynak"].items()
                 if not _uret.kaynak_yolu(ad).exists()
                 or hashlib.sha256(_uret.kaynak_yolu(ad).read_bytes()
                                   ).hexdigest() != ozet]
        _liste = _uret.goruntu_listesi()
        bayat += [f"{ad}(goruntude yok)" for ad in _liste if ad not in k["kaynak"]]
        # Ters yon: uretec artik URETMEDIGI bir dosyayi goruntu hala tasiyorsa
        # (kural degisti ya da dosya listeden cikti) goruntu yine bayat.
        bayat += [f"{ad}(fazla)" for ad in k["kaynak"] if ad not in _liste]
        r.kosul("  6j: LittleFS goruntusu GUNCEL", not bayat,
                " ".join(bayat) or f"{len(k['kaynak'])} varlik, "
                f"{k['icerik_bayt']} B, bolumun %"
                f"{100.0 * k['icerik_bayt'] / k['bolum_boyut']:.1f}'i")
        r.kosul("  6j: goruntu bolume SIGIYOR",
                k["icerik_bayt"] < k["bolum_boyut"])
        bolum6_moduller(r, k, _uret)
        bolum6_pwa(r, k, _uret)
        bolum6_etag(r, k, _uret)


def main() -> int:
    r = spice.Rapor()
    r.bilgi("")
    r.bilgi("  B22.4 — KARTIN WEB KATMANI")
    r.bilgi("  " + "=" * 70)
    r.bilgi("  Bu adim TASARIMI ve FIRMWARE'i sinar, kurulmus bir KARTI degil.")
    bolum1(r)
    bolum2(r)
    bolum3(r)
    bolum4(r)
    bolum5(r)
    bolum5_ag_donus(r)
    bolum6(r)
    tamam = r.yazdir()
    # Bu adim FIRMWARE KAYNAGINI siniyor; asagidakilerin hicbiri kaynaktan
    # gorulemez. Once yalnizca docstring'de gomuluyduler — ekrana hic
    # cikmiyorlardi (B23.1'in duzelttigi kusur).
    tezgah("B22b Kart web katmani", [
        ("Kart gercekten WiFi'ya baglaniyor mu (STA -> AP dusmesi)",
         "Acilista `Ag: STA (ev agi)` ya da `Ag: AP (kendi agi)` yazmali. "
         "10 s'de STA olmazsa AP'ye dusmeli; AP parolasi seri konsola basilir"),
        ("AGD: acilista ev agi yoksa AP, ev agi gelince KENDILIGINDEN STA (DEVIR 5.12.109)",
         "Kayitli erisim noktasi KAPALIYKEN karti sifirla: ~10 s sonra `Ag: AP (kendi agi) ... "
         "(ev agi 30 s'de bir deneniyor)`. Erisim noktasini AC: <= 60 s'de ikinci satir "
         "`Ag: STA (ev agi)`; ~5 s sonra kartin AP adi PC'nin ag listesinden kalkar; `Q?` "
         "durum=4 (bagli); ev aginda `_http._tcp` + TXT kimlik gorunur. Calisirken kopma "
         "(5.12.106: 7-14 s'de kendiliginden donus) DEGISMEMELI; AP'deyken panel 192.168.4.1'de "
         "calismali (her 30 s'deki taramada kisa takilma olabilir — olculmedi)"),
        ("mDNS telefonda cozuluyor mu",
         "http://olcum.local acilmali. Android'de Chrome `.local`'i "
         "guvenilir cozmuyor (12+ ve degisken) — cozulmezse AP'nin SABIT "
         "192.168.4.1'i kullanilacak, bu bir kusur DEGIL"),
        ("CSRF savunmasi gercek tarayicida",
         "Baska bir makinede `<img src=http://<kart-ip>/komut?k=p>` iceren "
         "sayfa ac. Istek karta ULASMAMALI. Ulasiyorsa POST+X-Olcum "
         "savunmasi calismiyor demektir"),
        ("collectHeaders gercekten toplaniyor mu",
         "`curl -X POST --data-binary '?' http://<ip>/komut` (basliksiz) "
         "-> HTTP 400. 204 donerse baslik denetimi SESSIZCE olmus demektir"),
        ("esp_wifi_start() <-> adc_continuous_start() carpismasi",
         "Skop yakalarken WiFi'yi kopar/bagla (DEVIR 7.1 (1), esp-idf#12749). "
         "Beklenen kusur: `! tetiklenemedi` ya da sifir dolu DMA tamponu. "
         "Bugunku baslatma sirasi TESADUFEN guvenli"),
        ("SSE loop()'u ne kadar blokluyor — CIFT CEKIRDEKTEN SONRA",
         "Iki sekmede /akis acikken `D` satirindaki ornek sayisi ve `K` "
         "satirindaki loop_azami_us. B28'den beri SSE yazimi cekirdek "
         "0'da; olculdu: 1 istemciyle bosta 3.0 ms, tam sayfa yuklemesinde "
         "4.1 ms. 20 000 us'yi asmasi artik bir KARAR degil GERILEME "
         "isaretidir — ag isi olcum dongusune geri sizmis demektir"),
        ("LittleFS gercekten baglaniyor mu",
         "Acilista `Arayuz: LittleFS'te` yazmali. `begin(false)` — otomatik "
         "bicimlendirme YOK, yani bos bolum sessiz kalmaz"),
        ("serveStatic ve index.htm tuzagi",
         "`http://<ip>/` tam arayuzu vermeli (acik kok isleyicisi). "
         "`/vendor/vue.global.prod.js` ikinci yuklemede 304/onbellekten "
         "gelmeli — `immutable` calisiyor mu"),
        ("W6: ETag + 304 kartta (arayuz-uret.py + arayuz-yaz.py + firmware W6 SONRASI)",
         "`curl -sI http://<ip>/app.js` -> `ETag: \"<16 onaltilik>\"` + `Cache-Control: no-cache` + "
         "`Content-Encoding: gzip`. Ayni ETag ile `curl -s -o NUL -w \"%{http_code} %{size_download}\" "
         "-H \"If-None-Match: <etag>\" http://<ip>/app.js` -> `304 0`; baska bir etiketle -> `200 <boy>`. "
         "`/` (index) de ETag tasimali ve ASLA `immutable` olmamali. Telefonda/Edge'de ikinci acilis: "
         "Ag sekmesinde panel dosyalari 304, aktarilan ~0 B (DEVIR 5.12.108'deki tahminle karsilastir). "
         "Olcum dongusunde yeni blokaj yok (`K` satiri, KOMUT GONDERMEDEN)"),
        ("Telefondan ilk yukleme suresi",
         "PC'de OLCULDU (B27 A4): 622 ms, 107 KB, 7 istek; ikinci acilista "
         "statik trafik 0 B (onbellek). 3 s'yi gecerse panel cikarma adimi "
         "acilir (5.12.38). TELEFONDA ayni olcumu yap — WiFi mesafesi ve "
         "telefon CPU'su bu sayiyi buyutur"),
        ("Sayfa sunmanin OLCUME bedeli — CIFT CEKIRDEKTEN SONRA",
         "B27 A4'te (tek cekirdek) varlik varlik olculmustu: index 33 ms, "
         "style 34 ms, vue 155 ms, app.js 186 ms blokaj. B28'den sonra "
         "AYNI olcum: tam sayfa yuklemesinde 3.8-4.1 ms, bosta 3.0 ms, "
         "0 uzun tur. ⚠ Bu kalemin onceki hali 'bosta 300 s'de 20 ms'yi "
         "asan TUR YOK' diyordu — YANLIS: o olcumde 5 tur vardi (22.5 ms, "
         "~50 s'de bir). Metin olcum bitmeden yazilmisti. Olcum: `K` "
         "sifirla, sayfayi ac, KOMUT GONDERMEDEN kartin kendi `K` "
         "satirlarini dinle (`?` ciktisi tek basina bir turu ~12 ms bloklar)"),
        ("arayuz-yaz.py ile karta yazma",
         "esptool yolu ve 0x310000 ofseti HIC denenmedi. "
         "`python arayuz-uret.py && python arayuz-yaz.py`"),
        ("3A: panel karttan ES MODULU olarak aciliyor mu (STA + AP)",
         "`python arayuz-uret.py && python arayuz-yaz.py` sonrasi http://<ip>/: "
         "konsolda 0 hata; Ag sekmesinde /app.js ve /ekran/tema.js "
         "`Content-Type: application/javascript` + `Content-Encoding: gzip`; "
         "konsolda `await import('/ortak/rapor.js')` hatasiz. Ayarlar > Gorunum "
         "uc temayi degistiriyor, sayfa yenilenince secim kaliyor. Olcum "
         "dongusunde yeni blokaj yok (`K` satiri, KOMUT GONDERMEDEN)"),
    ])
    return 0 if tamam else 1


if __name__ == "__main__":
    raise SystemExit(main())
