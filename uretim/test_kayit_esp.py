# -*- coding: utf-8 -*-
"""B72 — KAYIT MOTORUNUN KARTA BAGLANMASI: bolum tablosu · firmware kaynagi · esitleme.

    python test_kayit_esp.py

Gercek karti DEGIL; tabloyu, firmware KAYNAGINI (yorumlar cikarilarak) ve
PC esitleme istemcisini (sahte kart sunucusuna karsi) sinar. Kartta
olculecekler `tezgah_kayit.py`'de ve tezgah kalemi olarak basiliyor.
Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md
"""
from __future__ import annotations

import hashlib
import http.server
import io
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
import gercek_dizin_koru                                   # noqa: E402
_KORUMA = gercek_dizin_koru.koru()   # LOCALAPPDATA gecici dizine — gercek PC dizinine asla yazilmaz
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tezgah import tezgah                          # noqa: E402
import kayit_bicim as KB                             # noqa: E402
import kayit_esitle as KE                            # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  [OK] {ad}" + (f"   {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"  [!!] {ad}" + (f"   {ek}" if ek else ""))


def kod(metin: str) -> str:
    """C/C++ yorumlarini cikar — iddialar KODA baksin, prozaya degil."""
    return re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", metin, flags=re.S))


def govde(kaynak: str, imza: str) -> str:
    """`imza` ile baslayan fonksiyonun { ... } govdesi (yorumsuz kaynakta)."""
    i = kaynak.find(imza)
    if i < 0:
        return ""
    j = kaynak.find("{", i)
    derinlik = 0
    for k in range(j, len(kaynak)):
        if kaynak[k] == "{":
            derinlik += 1
        elif kaynak[k] == "}":
            derinlik -= 1
            if derinlik == 0:
                return kaynak[j:k + 1]
    return ""


def bolum_tablosu(yol: Path) -> list[dict]:
    """ESP-IDF bolum CSV'si -> [{ad, tur, alt, ofset, boyut}]."""
    satirlar = []
    for s in yol.read_text(encoding="utf-8").splitlines():
        s = s.split("#", 1)[0].strip()
        if not s:
            continue
        p = [x.strip() for x in s.split(",")]
        satirlar.append({"ad": p[0], "tur": p[1], "alt": p[2],
                         "ofset": int(p[3], 0), "boyut": int(p[4], 0)})
    return satirlar


def huge_app_csv() -> Path | None:
    taban = Path(os.environ.get("LOCALAPPDATA", "")) / "Arduino15" / "packages" / "esp32"
    return next(iter(sorted((taban / "hardware" / "esp32").glob(
        "*/tools/partitions/huge_app.csv"), reverse=True)), None)


# ── B72.P · bolum tablosu ─────────────────────────────────────────────
def bolum_tablo() -> None:
    print("\n── B72.P  bolum tablosu (partitions.csv)")
    yol = KOD / "partitions.csv"
    ok("B72.P0 cizim klasorunde partitions.csv var (cekirdegin semasini gecersiz kilar)",
       yol.exists())
    if not yol.exists():
        return
    t = {b["ad"]: b for b in bolum_tablosu(yol)}
    eski_yol = huge_app_csv()
    eski = {b["ad"]: b for b in bolum_tablosu(eski_yol)} if eski_yol else {}
    ayni = all(t.get(a) == eski.get(a) for a in ("nvs", "otadata", "app0"))
    ok("B72.P1 nvs / otadata / app0 huge_app ile BIREBIR (WiFi parolalari ve "
       "kalibrasyon NVS'te yerinde kalir)", bool(eski) and ayni,
       f"nvs={t.get('nvs')}")
    sp, esp = t.get("spiffs"), eski.get("spiffs")
    ok("B72.P2 panel bolumu ayni ofsette ve kuculmedi",
       bool(sp and esp) and sp["ofset"] == esp["ofset"] and sp["boyut"] >= esp["boyut"],
       f"{sp}")
    k = t.get("kayit")
    ok("B72.P3 kayit bolumu: data, alt tur 0x40, 4096'nin kati, >= 10 MB",
       bool(k) and k["tur"] == "data" and int(k["alt"], 0) == 0x40
       and k["boyut"] % 4096 == 0 and k["boyut"] >= 10 * 1024 * 1024,
       f"{k} = {k['boyut'] // 4096 if k else 0} sektor")
    sirali = sorted(t.values(), key=lambda b: b["ofset"])
    cakisma = any(a["ofset"] + a["boyut"] > b["ofset"] for a, b in zip(sirali, sirali[1:]))
    son = sirali[-1]
    ok("B72.P4 bolumler cakismiyor, 16 MB'i asmiyor, coredump en sonda",
       not cakisma and son["ofset"] + son["boyut"] <= 16 * 1024 * 1024
       and son["ad"] == "coredump", f"son={son}")
    au = (BURASI / "arayuz-uret.py").read_text(encoding="utf-8")
    ok("B72.P5 arayuz-uret.py panel ofsetini partitions.csv'den okuyor (tek kaynak)",
       "olcum-karti-a3\" / \"partitions.csv\"" in au and "huge_app.csv\"), reverse" not in au)


# ── B72.F · firmware kaynagi ──────────────────────────────────────────
def _oku(ad: str) -> str:
    y = KOD / ad
    return y.read_text(encoding="utf-8", errors="replace") if y.exists() else ""


def bolum_kaynak() -> None:
    print("\n── B72.F  firmware kaynagi (yorumlar cikarilarak)")
    esp_h, ino = _oku("kayit_esp.h"), _oku("olcum-karti-a3.ino")
    esp_k, ino_k = kod(esp_h), kod(ino)
    ok("B72.F1 kayit_esp.h Serial KULLANMIYOR (cekirdek 0'dan basmak aynayi "
       "yarisa sokar; baslik makrodan ONCE dahil)",
       bool(esp_k) and "Serial" not in esp_k)
    i_dahil = ino_k.find('#include "kayit_esp.h"')
    i_makro = ino_k.find("#define Serial CIKIS")
    # "KAPALI" .ino'da zaten 16 kez geciyordu: afisin KENDI dalina bak (son inceleme O5)
    ok("B72.F2 kayit_esp.h `#define Serial`'dan ONCE dahil; kayit bolumu yoksa "
       "afis KAPALI der",
       0 <= i_dahil < i_makro and re.search(
           r'if \(kayit_kur\(\)\) \{.*?\} else \{\s*Serial\.println\(F\("KAPALI',
           ino_k, re.S) is not None)
    ok("B72.F3 kayit gorevi CEKIRDEK 0'da (olcum cekirdegi flas beklemesin)",
       re.search(r"xTaskCreatePinnedToCore\(\s*kayit_gorevi[^;]*,\s*0\s*\)", esp_k)
       is not None)
    g = govde(esp_k, "static void kayit_gorevi(")
    ok("B72.F4 gorev butun ky_/kg_ islerini kilit ALTINDA yapiyor",
       "xSemaphoreTake(kayit_kilit" in g and "xSemaphoreGive(kayit_kilit" in g
       and 0 <= g.find("xSemaphoreTake(kayit_kilit") < g.find("ky_nokta("))
    # Durum makinesi kayit_yonet.h'de ve B71.V'de CALISTIRILARAK sinaniyor;
    # burada yalniz yapistirici: acilis + NVS'in Preferences'a baglanmasi.
    ny = govde(esp_k, "static int kayit_nvs_yaz(")
    ok("B72.F5 gorev acilista kyn_ac'i (esp_random ile) cagiriyor; NVS yazma hatasi "
       "YUTULMUYOR (bicimleme iptal edebilsin)",
       "kyn_ac(&kayit_m" in g and "esp_random()" in g
       and "putUInt(ad, deger) == sizeof(uint32_t)" in ny and "return -1" in ny)
    i_parca = esp_k.find("#define KG__PARCA")
    i_motor = esp_k.find('#include "kayit_yonet.h"')
    ok("B72.F6 ESP32 okuma parcasi (256) motordan ONCE tanimli",
       0 <= i_parca < i_motor and "256u" in esp_k[i_parca:i_parca + 40])
    oa = govde(ino_k, "Okuma3 olcum_al(")
    lp = govde(ino_k, "void loop(")
    ok("B72.F7 olcum_al HAM kodu, hata bitlerini ve menzili kayit_ham'a veriyor",
       all(x in oa for x in ("kayit_ham.ham_v = ham_v", "kayit_ham.ham_i = ham_i",
                             "kayit_ham.hata = ads_hata", "kayit_ham.menzil")))
    skop = lp[lp.find("if (skop_is != SKOP_IS_YOK)"):]
    ok("B72.F8 loop noktaciyi besliyor; skop duraklamasinda kayit_duraklama; "
       "G satiri yalniz loop'ta (cekirdek 1)",
       "kayit_ornek(o.watt" in lp and "kayit_duraklama(" in skop[:skop.find("return;")]
       and "kayit_durum_bas(false)" in lp and '"G %u' in ino_k)
    kk = govde(ino_k, "static void kayit_komut(")
    # 1C-1: pil_testi_suruyor() artik Gb/Gd dallarinda da var — iddia F DALINA bakmali
    #   (butun islevde arayinca 1C-1'den sonra BOS kaldi; mutasyon yakaladi)
    fd = kk[kk.find("alt == 'F'"):kk.find("m.tur = KM_BICIMLE")]
    ok("B72.F9 pil testi surerken GF! REDDEDILIR (bicimleme istegi kuyruga girmez)",
       "pil_testi_suruyor()" in fd)
    ok("B72.F10 `G` komutu tanimli ve yardimda; hiz listesi dar",
       "case 'G': kayit_komut(s)" in ino_k and "Gb<ms>" in ino
       and "h == 60000" in ino_k)
    vs = govde(ino_k, "void kayit_veri_sayfa(")
    ls = govde(ino_k, "void kayit_liste_sayfa(")
    ok("B72.F11 /kayit/liste ve /kayit/veri kayitli; ikisi de Host denetimli",
       'sunucu.on("/kayit/liste"' in ino_k and 'sunucu.on("/kayit/veri"' in ino_k
       and "host_gecerli()" in vs and "host_gecerli()" in ls)
    ok("B72.F12 /kayit/veri kg_oku'yu SURELI kilit altinda, tavanla (8192) cagiriyor; "
       "web uclarinda sonsuz bekleme YOK (p0 donmasin)",
       0 <= vs.find("kayit_kilit_al_web()") < vs.find("kg_oku(")
       < vs.find("xSemaphoreGive(kayit_kilit") and "KAYIT_VERI_AZAMI" in vs
       and "kayit_kilit_al_web()" in ls and "portMAX_DELAY" not in vs + ls
       and "pdMS_TO_TICKS(KAYIT_WEB_BEKLE_MS)" in esp_k)
    ok("B72.F13 onay KUYRUGA girmez (son gelen kazanir); gorev her turda kyn_adim'e verir",
       "kayit_onay_iste(v)" in kk and "KM_ONAY" not in ino_k + esp_k
       and "kyn_adim(&kayit_m, kayit_onay_istek" in g)
    ok("B72.F14 /kayit/veri akis kimligini ve X-Onay'i basliyor; /kayit/liste kimlik veriyor",
       'sendHeader("X-Kayit-Kimlik"' in vs and 'sendHeader("X-Onay"' in vs
       and '\\"kimlik\\"' in ls)
    fo = govde(esp_k, "static int kayit_f_oku(")
    nf = govde(esp_k, "static void kayit__nefes(")
    ok("B72.F16 uzun tarama cekirdek 0'i BIRAKIR (Task WDT dolu bolumde karti "
       "sonsuz yeniden baslatiyordu) ve okuma bellege esli bolumden",
       "vTaskDelay(1)" in nf and "kayit__nefes()" in fo
       and "memcpy(h, kayit_esle_ptr + a, n)" in fo
       and "esp_partition_mmap(" in esp_k)
    # ── 1B: kalibrasyon gecmisi (davranis B71.C'de, burada yapistirici) ──
    st = govde(ino_k, "void setup(")
    ok("B72.F17 setup kalibrasyon gecmisini ayar_yukle'den SONRA kuruyor (#1 = gercek Ayar3)",
       0 <= st.find("ayar_yukle()") < st.find("kalgec_kur(&"))
    bd = govde(ino_k, "static void kayit_basla_doldur(")
    ok("B72.F18 her oturum basliginda kalibrasyon NUMARASI (kgc_oturum_no: taslak varsa "
       "otomatik kaydeder)",
       "b->kal_no = kgc_oturum_no(&kalgec, &b->kal" in bd and "kayit_kal_doldur(&b->kal)" in bd)
    kl = govde(ino_k, "void kal_liste_sayfa(")
    ok("B72.Y6a (1B inceleme M2) /kal/liste okunamayan/bozuk kaydi SESSIZCE atlamaz: "
       '{"no":n,"bozuk":true} yazar (numarasi tutmayan blob da bozuk)',
       0 <= kl.find("|| e.no != no) {")
       and '\\"bozuk\\":true' in kl[kl.find("|| e.no != no) {"):kl.find("continue;", kl.find("|| e.no != no) {"))]
       and "kgc_coz(blob, &e)) continue;" not in kl)
    ok("B72.F19 /kal/liste kayitli, Host denetimli; once `adet`, sonra bloblar (cekirdek 1 "
       "kaydederken tutarli)",
       'sunucu.on("/kal/liste"' in ino_k and "host_gecerli()" in kl
       and 0 <= kl.find('"adet"') < kl.find("kgc_coz("))
    nb = govde(esp_k, "static uint32_t kalgec_nvs_bos(")
    ok("B72.F20 NVS'te yer: nvs_get_stats'in available_entries'i (GC sayfasi haric)",
       "nvs_get_stats(" in nb and "available_entries" in nb)
    ok("B72.F21 `k` komutu tanimli ve yardimda",
       "case 'k': kalgec_komut(s)" in ino_k and "kk<t><not>" in ino)
    # 1B son inceleme I1: otomatik kayit ve basarisizligi SESSIZDI
    ob = govde(ino_k, "static void kalgec_oturum_bildir(uint32_t no, uint32_t once) {")   # ileri bildirim degil
    ok("B72.F22 kayit baslarken kalibrasyon OTOMATIK kaydedilirse ya da oturum "
       "numarasiz kalirsa kart SOYLER (numara + not/tur komutu · hata adi)",
       "kalgec_oturum_bildir(" in bd and 0 <= bd.find("kgc_oturum_no(") < bd.find("kalgec_oturum_bildir(")
       and "otomatik kaydedildi" in ob and "NUMARASIZ" in ob and "kalgec_hata_adi(" in ob
       and "kalgec_uyari_bas()" in ob)
    kk = govde(ino_k, "static void kalgec_komut(")
    kk = kk[kk.find("alt == 'k'"):kk.find("alt == 'n'")]
    ok("B72.F23 `kk` degerler zaten kayitliyken HANGI numara oldugunu ve not/tur "
       "komutunu soyler (sifirlar gecmise girmez)",
       "KGC_YOK" in kk and "kalgec_etkin" in kk and "zaten" in kk and "sifir" in kk
       and "kalgec_uyari_bas()" in kk)
    ub = govde(ino_k, "static void kalgec_uyari_bas(")
    ok("B72.F24 gecmis dolmak uzereyken (35/40) afiste, `kk`'da ve otomatik kayitta uyari",
       "kgc_dolmak_uzere(&kalgec)" in ub and "kalgec_uyari_bas()" in st)
    ok("B72.F25 firmware surum adi her bicim eklemesiyle DEGISIR (1C-1: OLAY/NOT kayitlari; "
       "PC/tezgah eski firmware'den ayirt eder)",
       re.search(r'#define KAYIT_FW_SURUM\s+"A3-4B"', esp_k) is not None)
    tg = govde(ino_k, "static void kalgec_taslak_guncelle() {")
    ok("B72.F26 etkin kalibrasyon (degerlerin gecmisteki numarasi) tek taramayla bulunur; "
       "`k?`, afis ve /kal/liste onu gosterir",
       "kalgec_etkin = kgc_esle(&kalgec, &k)" in tg and "kalgec_etkin" in govde(ino_k, "static void kalgec_durum_bas(")
       and '\\"etkin\\"' in kl and "kalgec_etkin" in st)
    # ── 1C-1: pil testi kendi oturumunda (davranis B71.PL'de, burada yapistirici) ──
    pb = govde(ino_k, "static void pil_baslat() {")
    red = pb[pb.find("if (h != PILH_YOK)"):pb.find("return;") + 1]
    ok("B72.F27 kabul edilen p1 pil kaydini acar (kayit_pil_baslat, test CALISIYOR'a "
       "gectikten sonra); reddedilen p1 ACMAZ",
       bool(red) and "kayit_pil_baslat" not in red
       and 0 <= pb.find("pil.durum = PIL_CALISIYOR") < pb.find("kayit_pil_baslat()"))
    pd = govde(ino_k, "static void pil_durdur(")
    ok("B72.F28 pil_durdur YUKU HER SEYDEN ONCE keser; kayit mesaji ondan SONRA "
       "(p0 kayit kuyruguna/kilidine takilmaz)",
       pd.lstrip("{ \r\n\t").startswith("pil_yuk(false)")
       and 0 <= pd.find("pil_yuk(false)") < pd.find("kayit_pil_bitir("))
    pi = govde(ino_k, "static void pil_isle(")
    a = pi.find("pil.dcir_sayisi++")
    ok("B72.F29 her DCIR darbesi bitince olay kaydi (kayit_pil_dcir) — darbe sonu blogunda",
       a >= 0 and "kayit_pil_dcir(" in pi[a:pi.find("}", a)])
    lp = govde(ino_k, "void loop() {")
    ok("B72.F30 noktaci DCIR darbesindeki ornekleri KN_DCIR ile isaretler",
       "kayit_ornek(o.watt, millis(), pil.dcir_icinde ? KN_DCIR : 0u)" in lp)
    kk2 = govde(ino_k, "static void kayit_komut(")
    ok("B72.F31 pil testi surerken Gb ve Gd REDDEDILIR (kayit testle baslar/biter); p0 "
       "hala jetonsuz serbest",
       "pil_testi_suruyor()" in kk2[kk2.find("alt == 'b'"):kk2.find("alt == 'd'")]
       and "pil_testi_suruyor()" in kk2[kk2.find("alt == 'd'"):kk2.find("alt == 'o'")]
       and "k[0] == 'p' && k[1] == '0'" in govde(ino_k, "static bool komut_serbest("))
    bt = govde(ino_k, "static void kayit_pil_bitir(uint8_t sebep) {")   # ileri bildirim degil
    mg = govde(esp_k, "static bool kayit_mesaj_gonder(")
    mb = govde(esp_k, "static void kayit_mesaj_birak(")
    ok("B72.F32 pil bitir mesaji DUSMEZ ve GECILMEZ: kuyruga giremezse bekler, loop her "
       "turda yeniden dener; bekleyen varken hicbir istek (p1, Gb, olay, not) onun ONUNE "
       "gecemez — once o gider, gidemezse yeni istek reddedilir (son inceleme 1-2)",
       "kayit_mesaj_birak(m)" in bt and "kayit__bekleyeni_gonder()" in lp
       and re.search(r"if \(kayit__bekleyeni_gonder\(\) && kayit__kuyruga\(m\)\) return true;", mg)
       is not None
       and re.search(r"kayit_bekleyen_m = \*m;\s*kayit_bekleyen = 1u;", mb) is not None
       and "xQueueSend(kayit_mesaj_q" not in ino_k)
    km = govde(esp_k, "static void kayit__mesaj(")
    ok("B72.F33 kayit gorevi yeni istekleri yoneticiye verir: PIL_BASLAT (baslat + AYAR "
       "olayi) · OLAY · PIL_BITIR · NOT",
       all(x in km for x in ("case KM_PIL_BASLAT", "case KM_OLAY", "case KM_PIL_BITIR",
                             "case KM_NOT", "kyn_pil_bitir(", "kyn_not(", "kyn_olay("))
       and "kyn_olay(" in km[km.find("case KM_PIL_BASLAT"):km.find("case KM_OLAY")]
       and 0 <= km.find("case KM_PIL_BASLAT") < km.find("kyn_baslat(", km.find("case KM_PIL_BASLAT")))
    nk = govde(ino_k, "static void kayit_not_komut(")
    ok("B72.F34 Ga/Ge/Gn/Gx: yardimda; oturum numarasi zorunlu; Gx ':' + sira ister "
       "(bozuk argumanda kayit YAZILMAZ); Gn bos metni reddeder",
       "Ga<oturum>" in ino and "kayit_not_komut(s)" in kk2
       and "kayit_not_ayir(s, &k)" in nk and "KM_NOT" in nk and "strtoul" not in nk
       and 0 <= nk.find("if (r)") < nk.find("kayit_mesaj_gonder("))
    ka = re.search(r"#define KOMUT_AZAMI\s+(\d+)u", ino_k)
    ki = govde(ino_k, "void komut_isle() {")
    ks = govde(ino_k, "void komut_sayfa() {")
    ok("B72.F37 komut satiri 120 baytlik notu tasir (KOMUT_AZAMI >= 160) ve uzun komut "
       "SESSIZCE KESILMEZ: seri ve web REDDEDER (son inceleme 3)",
       ka is not None and int(ka.group(1)) >= 160
       and "char m[KOMUT_AZAMI]" in ino_k and "tampon[KOMUT_AZAMI]" in ki
       and "cok uzun" in ki and "tasti = 1" in ki and "sizeof(KomutKalem::m)" in ks
       and "cok uzun" in ks)
    pk = ino_k[ino_k.find("case 'p': {"):ino_k.find("pil_baslat();", ino_k.find("case 'p': {"))]
    ok("B72.F38 test SURERKEN p1 REDDEDILIR (eskisi yeniden baslatiyordu: pil oturumu SONUC'suz "
       "kapaniyor ya da ret halinde acik kalip nokta yaziyordu)",
       "pil.durum == PIL_CALISIYOR" in pk and "zaten suruyor" in pk)
    ok("B72.F39 DCIR 'ani' degeri darbenin ILK orneginden (ilk darbede de): kosul "
       "dcir_sayisi'na bakmaz (B21'den kalma hata; 1C-1 bunu flasa yaziyordu)",
       "pil.dcir_sayisi == 0 ||" not in pi and "if (pil.dcir_ani == 0.0f) {" in pi)
    # ── 1C-2: ayrintili kip (davranis B71.A/H/Z'de, burada yapistirici) ──
    hg = govde(ino_k, "static bool kayit__hiz_gecerli(")
    ok("B72.F40 Gb0 = ayrintili kip (her ornek) kabul edilir ve yardimda yaziyor",
       "h == 0" in hg and "0 = her ornek" in ino)
    ko = govde(esp_k, "static void kayit_ornek(")
    ok("B72.F41 ayrintili oturumda loop her ornegi zamaniyla (micros) halkaya iter; noktaci "
       "o zaman calismaz",
       "kayit_ayr_aktif" in ko and "kh_it(&kayit_halka, &o)" in ko and "o.us = micros()" in ko
       and 0 <= ko.find("kayit_ayr_aktif") < ko.find("kayit_kn_aktif) return"))
    kg2 = govde(esp_k, "static void kayit_gorevi(")
    kk3 = govde(esp_k, "static bool kayit_kur(")
    ok("B72.F42 kayit gorevi halkayi bosaltip yaziciya verir (kilit altinda); halka PSRAM'de, "
       "KAYIT_HALKA_ORNEK ornek",
       "kh_al(&kayit_halka, &o)" in kg2 and "ky_ayrinti_ornek(&kayit_y, &o" in kg2
       and "KAYIT_HALKA_ORNEK" in kk3 and "kh_kur(&kayit_halka" in kk3
       and re.search(r"heap_caps_malloc\(KAYIT_HALKA_ORNEK[^;]*MALLOC_CAP_SPIRAM", kk3) is not None)
    iv = govde(esp_k, "static void kayit_on_sil_izin_ver(")
    sk = lp[:lp.find("if (skop_is != SKOP_IS_YOK) {")]
    ok("B72.F43 on silme izni: kayit yok + skop yok + pil testi yok; loop skop erken "
       "donusunden ONCE gunceller, gorev kyn_adim'dan once yoneticiye yazar",
       "KDR_KAYIT" in iv
       and "kayit_on_sil_izin_ver(skop_is == SKOP_IS_YOK && !pil_testi_suruyor())" in sk
       and 0 <= kg2.find("kayit_m.on_sil_izin = kayit_on_sil_izin") < kg2.find("kyn_adim("))
    gb = govde(ino_k, "static void kayit_ga_bas(")
    ok("B72.F44 G? ardindan GA satiri: hazir sektor, ayrintili ornek, dusen ornek, kayit ici "
       "silme duraklamasi (G satiri DEGISMEDI)",
       '"GA %lu %lu %lu %lu"' in gb
       and "kayit_ga_bas()" in kk2[kk2.find("alt == '?'"):kk2.find("alt == 'b'")])
    dg = govde(esp_k, "static void kayit__durum_guncelle(")
    ok("B72.F46 durum yeni alanlari cekirdek 0'da (kilit altinda) doldurur: hazir, dusen ornek, "
       "ayrintili silme",
       "t.hazir = kayit_g.hazir" in dg and "t.ornek_dusen = kayit_halka.dusen" in dg
       and "t.ayr_silme = kayit_ayr_silme" in dg)
    # son inceleme (Important 1-2): KA_SILME silmeyi YAPAN bosaltmadan sonraki
    # kayda dusuyordu (halkadaki silme ONCESI ornekler); GA yalniz tabloda kaydi
    # olan sektorleri sayiyordu (GF! sonrasi eski sektorler 0).
    # 🔴 kartta (2026-10-01, 204 kirli silme): 3'unde isaret DURUSTAN ONCEKI
    # ornege dustu — sayac silmeden once artiyor, kayit_f_sil silmeye girmeden
    # kayit__nefes ile 1 tik birakiyordu; o arada itilen ornek isaretleniyordu.
    # Kural artik kanita dayali: sayac degistikten sonra onceki ornekten >= 15 ms
    # sonra gelen ILK ornek (silme ~25 ms durdurur; aralik 2 ms, ADS'siz <= 10 ms);
    # 100 ms icinde durus yoksa (kisa silme) yine isaretlenir.
    fs = govde(esp_k, "static int kayit_f_sil(")
    ok("B72.F47 kirli silmeden sonra uretilen ILK ornek KO_SILME_ONCE tasir: sayac degistikten "
       "sonra >= 15 ms bosluktan sonra gelen ornek (ya da 100 ms); gorulen yalniz ISARETLI "
       "ornek itilince guncellenir; ayrintili degilken esitlenir; nefes silmeden SONRA",
       "const uint32_t ks = kayit_g.kirli_sil;" in ko
       and "if (ksi_ornek(&kayit_ksi, ks, o.us, simdi))" in ko
       and "ksi_itildi(&kayit_ksi, ks, (uint8_t)(kh_it(&kayit_halka, &o) && (o.bayrak & KO_SILME_ONCE)));" in ko
       and ko.find("ksi_itildi(") < ko.find("ksi_esitle(&kayit_ksi, kayit_g.kirli_sil);")
       < ko.find("if (!kayit_kn_aktif) return;")
       and 0 <= fs.find("esp_partition_erase_range(") < fs.find("kayit__nefes()"))
    ok("B72.F48 GA kayit ici silme = kirli silme sayaci (kayit_g.kirli_sil), gorev turunda "
       "ayrintili oturum surduyse — Gd'nin son bosaltmasi dahil; temizlik kayitta durur "
       "(kayit_yonet.h, B71.Z7)",
       kg2.find("const uint32_t ks0 = kayit_g.kirli_sil;") < kg2.find("kh_al(&kayit_halka, &o)")
       and kg2.find("kyn_adim(") < kg2.find("kayit_ayr_silme += kayit_g.kirli_sil - ks0;")
       and "if (ayr0 || (kayit_y.oturum && kayit_y.ayrinti))" in kg2
       and "kayit_g.silinen_sektor" not in kg2)
    # ── 1C-3: osiloskop gunlugu (davranis B71.B25-B28, S1-S8'de; burada yapistirici) ──
    sa = govde(ino_k, "static bool kayit__skop_aralik(")
    ok("B72.F49 Gt<ms>: yalniz rakam, 0 (her tetik) ya da 1000..3600000; disi REDDEDILIR",
       "x < 1000UL" in sa and "x > 3600000UL" in sa and "*q < '0' || *q > '9'" in sa
       and "x != 0" in sa)
    skk = govde(ino_k, "static void kayit_skop_komut(")
    ok("B72.F50 PSRAM yuvasi yoksa Gt REDDEDILIR (sessiz bos gunluk yok); yuva PSRAM'de",
       0 <= skk.find("!kayit_skop_yuva") < skk.find("kayit_mesaj_gonder(&m)")
       and re.search(r"kayit_skop_yuva = \(KayitSkopYuva \*\)heap_caps_malloc\(sizeof\(KayitSkopYuva\),"
                     r"\s*MALLOC_CAP_SPIRAM\)", govde(esp_k, "static bool kayit_kur(")) is not None)
    p1 = ino_k.find("if (s[1] == '1') {")
    pc = ino_k[p1:ino_k.find("pil_baslat();", p1)]
    ok("B72.F51 pil testinde Gt reddi; gunluk surerken p1 reddi (once Gtd) — Oe7",
       0 <= skk.find("pil_testi_suruyor()") < skk.find("kayit_mesaj_gonder(&m)")
       and "skop_gunluk.aktif" in pc)
    sk = govde(ino_k, "void skop_komut(")
    ok("B72.F52 gunlukte elle yakalama (t, t<esik>, tB, ta, tK) REDDEDILIR; ayar komutlari serbest",
       0 <= sk.find("skop_gunluk.aktif") < sk.find("skop_yolla()")
       and all(x in sk[:sk.find("skop_yolla()")] for x in ("alt == 'B'", "alt == 'a'", "alt == 'K'")))
    gi = govde(ino_k, "static void skop_gunluk_isle(")
    ok("B72.F53 gunluk yeniden kurmadan once: skop bos, dokum yok, YUVA BOS, aralik doldu",
       0 <= gi.find("kayit_skop_dolu") < gi.find("skop_is_ver(SKOP_IS_GUNLUK)")
       and gi.find("skop_dokum.aktif") < gi.find("skop_is_ver(SKOP_IS_GUNLUK)")
       and gi.find("aralik_ms") < gi.find("skop_is_ver(SKOP_IS_GUNLUK)")
       and "skop_gunluk_isle();" in lp)
    si = govde(ino_k, "static void skop_sonuc_isle(")
    sg = govde(ino_k, "static void skop_gorevi(")
    gs = govde(ino_k, "static void skop_gunluk_sonuc(")
    ok("B72.F54 gunluk yakalamasi DOKUMSUZ (M/S2 basilmaz) yuvaya gider; gorev GUNLUK'te de yakalar; "
       "META yakalamanin AYARIYLA (son tdiv/kip, adim, tetik, hz)",
       0 <= si.find("is == SKOP_IS_GUNLUK") < si.find("skop_dokum.aktif = true")
       and "is == SKOP_IS_DOKUM || is == SKOP_IS_IKILI || is == SKOP_IS_GUNLUK" in sg
       and "SKOP_TDIV_US[skop_son_tdiv]" in gs and "skop_son_kip" in gs
       and "skop_volt_adim()" in gs and "skop_tetik_idx" in gs and "skop_hz" in gs
       and "memcpy(y->kod, (const void *)skop_veri" in gs
       and gs.find("kayit_skop_dolu = 1u") < gs.find("kayit_mesaj_gonder(&m)"))
    ms = govde(esp_k, "static void kayit__mesaj(")
    ksk = ms[ms.find("case KM_SKOP:"):]
    ok("B72.F55 KM_SKOP: gorev yuvadan kyn_skop ile yazar, SONRA yuvayi bosaltir; yazamazsa sayar",
       "kyn_skop(&kayit_m, &kayit_skop_yuva->meta, kayit_skop_yuva->kod" in ksk
       and 0 <= ksk.find("kyn_skop(") < ksk.find("kayit_skop_dolu = 0u")
       and "kayit_skop_hata" in ksk)
    ns = govde(esp_k, "static void kayit__nesil(")
    dg2 = govde(esp_k, "static void kayit__durum_guncelle(")
    ok("B72.F56 SKOP oturumunda noktaci KAPALI, ayrintili yalniz OLCUM'de (hiz 0 = her tetik); "
       "durum oturum turunu tasir",
       "if (d.tur == KAYIT_OTURUM_SKOP) kayit_kn_aktif = 0u;" in ns
       and "if (d.tur != KAYIT_OTURUM_OLCUM) kayit_ayr_aktif = 0u;" in ns
       and ns.find("kayit_ayr_aktif = 0u") < ns.find("kn_baslat(")
       and "t.tur = kayit_y.oturum ? kayit_y.basla.oturum_turu : 0u;" in dg2)
    gt = govde(ino_k, "static void kayit_gt_bas(")
    ok("B72.F57 G? ardindan GT satiri: etkin, aralik, yakalama, yazilamayan (G/GA degismedi)",
       '"GT %lu %lu %lu %lu"' in gt
       and 0 <= kk2.find("kayit_ga_bas()") < kk2.find("kayit_gt_bas()") < kk2.find("alt == 'b'"))
    kd = kk2[kk2.find("alt == 'd'"):kk2.find("alt == 'o'")]
    ok("B72.F58 Gd gunlugu de durdurur; baglandigi oturum kapaninca (Gd/DOLU/baska oturum) "
       "gunluk kendiliginden durur; SKOP_KAL olayi gunluk baslarken gider",
       "skop_gunluk_durdur(false);" in kd
       and "d.oturum != skop_gunluk.oturum" in gi
       and "kayit_olay_skop_kal_paketle(" in skk and "kal_mv_tab" in skk)
    gd = govde(ino_k, "static void skop_gunluk_durdur(")
    ok("B72.F59 yakalama numarasi acilis boyunca TEKDUZE (Gt sifirlamaz) ve yuva BAGLI oturumu "
       "tasir; gorev yalniz o oturum etkinse yazar, degilse sayar (ucustaki yakalama yeni "
       "oturuma girmez)",
       "y->no = ++skop_gunluk_no;" in gs and "y->oturum = skop_gunluk.oturum;" in gs
       and ino_k.count("skop_gunluk_no = 0") == 1 and "static uint32_t skop_gunluk_no = 0;" in ino_k
       and "kayit_y.oturum == kayit_skop_yuva->oturum" in ksk
       and ksk.find("kayit_y.oturum == kayit_skop_yuva->oturum") < ksk.find("kyn_skop("))
    ok("B72.F60 her yakalama sonucundan (tetik yok dahil) sonra en az o kadar (>= 100 ms) OLCUM: "
       "Gt0 tetik beklerken olcumu durdurmaz (kartta 5.0 -> 0.1 D/s olculdu)",
       "skop_gunluk.serbest_ms = millis() + (sure > 100u ? sure : 100u);" in gs
       and gs.find("skop_gunluk.serbest_ms") < gs.find("if (sonuc != SKOP_SONUC_OK) return;")
       and 0 <= gi.find("(int32_t)(simdi - skop_gunluk.serbest_ms) < 0") < gi.find("skop_is_ver(SKOP_IS_GUNLUK)"))
    ok("B72.F61 Gtd yalniz SKOP oturumunu kapatir (OLCUM'e eklenmisse olcum SURER, K11); yeni "
       "oturum TUR SKOP ile acilir; KM_SKOP_BASLAT pil yolunu paylasir (BASLA + olay)",
       "if (kullanici && !skop_gunluk.eklendi && d.durum == KDR_KAYIT && d.tur == KAYIT_OTURUM_SKOP)" in gd
       and "m.basla.oturum_turu = KAYIT_OTURUM_SKOP;" in skk
       and re.search(r"case KM_SKOP_BASLAT:\s*case KM_PIL_BASLAT: \{", ms) is not None)
    ok("B72.F62 Gt0'in NORMAL'e aldigi skop kipi gunluk durunca (Gtd, Gd, oturum kapanmasi) GERI "
       "yuklenir ve panel bilgilendirilir",
       "skop_gunluk.eski_kip = skop_ayar.kip;" in skk
       and "skop_ayar.kip = skop_gunluk.eski_kip;" in gd and "skop_ayar_yaz();" in gd)
    # ── 1C-4: zamanlanmis kayit (karar mantigi B71.R'de; burada yapistirici) ──
    pk = govde(ino_k, "static void kayit_plan_komut(")
    ua = govde(ino_k, "static bool kayit__u32_al(")
    ok("B72.F63 Gp<unix>,<sure>,<hiz> / Gp+<s>,... / Gp- / Gp?: yalniz rakam (10 hane, 32 bit "
       "tasmasiz), virgul ayrac, artik karakter RED; hiz Gb kumesinden",
       "x > 0xFFFFFFFFULL" in ua and "++n > 10u" in ua
       and "kayit__hiz_gecerli((long)hiz)" in pk and "plan_iptal(&kayit_plan)" in pk
       and "goreli" in pk and "*p++ != ','" in pk)
    ok("B72.F64 saat yoksa (NTP gelmedi) plan KURULMAZ ve kart bunu soyler; goreli bicim kartin "
       "saatine cevrilir",
       0 <= pk.find("if (!simdi)") < pk.find("plan_kur(&kayit_plan")
       and "saat yok" in pk and "bas = simdi + bas;" in pk)
    pa = govde(esp_k, "static void kayit_plan_ac(")
    ok("B72.F65 plan kendi NVS ad alaninda (`plan`), acilista plan_ac ile okunur (kurulumda, "
       "kayit_kur'dan sonra)",
       'plan_nvs.begin("plan", false)' in pa and "plan_ac(&kayit_plan, &t)" in pa
       and 0 <= ino_k.find("if (kayit_kur()) {") < ino_k.find("kayit_plan_ac();"))
    pi = govde(ino_k, "static void kayit_plan_isle(")
    ok("B72.F66 saniyede bir plan_adim: tarama bitmeden karar YOK (DEVAM belli degil); mesgul "
       "durumu ve gercek saat (NTP) ile; loop'ta",
       "millis() - son < 1000u" in pi and 0 <= pi.find("KDR_TARIYOR") < pi.find("plan_adim(")
       and "plan_adim(&kayit_plan, simdi, mesgul, d.oturum)" in pi
       and "kayit_plan_isle();" in lp)
    ok("B72.F67 BASLAT: BASLA (kalibrasyon kopyasi, Gb gibi) + PLAN olayi TEK mesajda; plan "
       "YALNIZ istek kuyruga girdiyse 'basliyor' olur (girmezse sonraki saniye yeniden)",
       "kayit_basla_doldur(&m.basla, kayit_plan.hiz)" in pi and "m.tur = KM_PLAN_BASLAT" in pi
       and "kayit_olay_plan_paketle(" in pi and "m.sebep = kayit_plan_istek;" in pi
       and "kayit_plan_beklenen = kayit_plan_istek;" in pi
       and "if (kayit_mesaj_gonder(&m)) {\n      kayit_plan_beklenen = kayit_plan_istek;\n"
           "      plan_basliyor(&kayit_plan, simdi);" in pi.replace("\r", ""))
    ms4 = govde(esp_k, "static void kayit__mesaj(")
    kb4 = ms4[ms4.find("case KM_PLAN_BITIR:"):]
    kb5 = ms4[ms4.find("case KM_PLAN_BASLAT:"):ms4.find("case KM_PLAN_BITIR:")]
    # 🔴 1C-4 incelemesi: plan BASLAT'tan sonra beliren HERHANGI bir oturumu
    # benimsiyordu (kullanicinin Gb/p1'ini sonunda sebep 7 ile kapatabilirdi) ve
    # mesgul denetimi cekirdek 0 ile atomik degildi. Artik cekirdek 0 mesgulse
    # ACMAZ ve sonucu (oturum ya da hata) istek numarasiyla yayinlar.
    ok("B72.F68 KM_PLAN_BITIR yalniz etkin oturum PLANIN oturumuysa kapatir (mesajdaki sebep: "
       "7 ya da Gp- ile 1); KM_PLAN_BASLAT cekirdek 0'da oturum ya da DEVAM bekleyisi varsa "
       "ACMAZ (Y2: platformsuz kyn_plan_baslat, B71.PK3), sonucu istek numarasiyla yayinlar",
       0 <= kb4.find("kayit_y.oturum == id") < kb4.find("ky_bitir(&kayit_y, m->sebep)")
       and 0 <= kb5.find("kyn_plan_baslat(") < kb5.find("kayit_plan_sonuc = s;")
       < kb5.find("kayit_plan_sonuc_no = m->sebep;"))
    du = govde(esp_k, "static void kayit__durum_guncelle(")
    pi2 = govde(ino_k, "static void kayit_plan_isle() {")
    ok("B72.Y2 (1C-4 inceleme M3) planin oturumu KANITLA: KM_PLAN_BASLAT kyn_plan_baslat ile "
       "(acmadan once NVS kaniti); cekirdek 0 acilis kanitini yayinlar; cekirdek 1 tarama "
       "bitince BIR KEZ plan_acilis ile benimser — plan_adim'dan ONCE",
       "t.plan_no = kayit_m.plan_kanit_no;" in du and "t.plan_ot = kayit_m.plan_kanit_ot;" in du
       and 0 <= pi2.find("KDR_TARIYOR") < pi2.find("plan_acilis(&kayit_plan, d.plan_no, d.plan_ot)")
       < pi2.find("plan_adim(") and "kayit_plan_acildi" in pi2)
    gp = govde(ino_k, "static void kayit_gp_bas(")
    ok("B72.F69 G? ardindan GP satiri: durum (saat yoksa 6), baslangic, sure, hiz, oturum",
       '"GP %u %lu %lu %lu %lu"' in gp and "PLAN_SAAT_YOK" in gp
       and 0 <= kk2.find("kayit_gt_bas()") < kk2.find("kayit_gp_bas()") < kk2.find("alt == 'b'"))
    ok("B72.F70 plan baslangicta MESGULSE ATLAR: oturum VEYA oturumsuz pil testi VEYA skop "
       "gunlugu (Oe7: pil testi DOLU'da oturumsuz surebilir)",
       "const uint8_t mesgul = (uint8_t)(d.oturum || pil_testi_suruyor() || skop_gunluk.aktif);" in pi)
    ok("B72.F71 Gp- suren planda KAYDI DA durdurur (sebep 1, otomatik bitis sessizce kalkmaz); "
       "plan yoksa 'iptal' demez",
       pk.find("kayit_plan.durum == PLAN_SURUYOR && kayit_plan.oturum") < pk.find("plan_iptal(&kayit_plan)")
       and "kayit__plan_bitir(kayit_plan.oturum, KB_SEBEP_KULLANICI)" in pk and "plan yok" in pk)
    ok("B72.F72 plan cekirdek 0'in sonucunu ALIR: istek numarasi eslesirse plan_sonuc (oturuma "
       "bagla ya da BASLATILAMADI) ve kart sebebi soyler",
       "kayit_plan_sonuc_no == kayit_plan_beklenen" in pi and "plan_sonuc(&kayit_plan, s)" in pi
       and "baslatilamadi" in pi and "atlandi" in pi)
    ok("B72.F73 plan ARTIK beklemedigi gec bir oturumu (zaman asimi / Gp-) KAPATIR — sahipsiz "
       "kayit kalmaz",
       0 <= pi.find("if (!plan_sonuc(&kayit_plan, s))") < pi.find("if (s > 0)")
       < pi.find("kayit__plan_bitir((uint32_t)s, KB_SEBEP_PLAN)"))
    km = govde(esp_k, "static void kayit__mesaj(")
    wa = _oku("web_akis.h")
    ap = [m.start() for m in re.finditer(r'getString\("ap_sifre"', ino_k)]
    # 4B (D5 #12 kok): eskiden iddia "her ap_sifre okumasi bir Serial.ham( cagrisinin ICINDE"
    # diyordu; satir UC ham() ile basiliyordu ("...(yalniz USB): " + parola + "\r\n") ve araya
    # IDF gunlugu girerse parola ISARETSIZ ayri satira dusuyordu. Artik parola TEK yerde okunur
    # (ap_parolasi_bas), satir orada tek tamponda kurulur ve TEK ham() ile gider.
    apb = govde(ino_k, "static void ap_parolasi_bas(")
    ok("B72.D0 (1D on-cesi sizinti + 4B D5 #12) AP parolasi YALNIZ ham UART'a ve TEK yazimla: tek "
       "okuma yeri ap_parolasi_bas; satir (isaret + parola + CRLF) tek tamponda, TEK Serial.ham, "
       "aynali baski yok, tampon silinir; N? ve AP afisi onu cagirir",
       "void ham(const char *s)" in wa and len(ap) == 1 and bool(apb)
       and 'getString("ap_sifre"' in apb and apb.count("Serial.ham(") == 1
       and "AP parolasi (yalniz USB): " in apb and "\\r\\n" in apb
       and not re.search(r"Serial\.(print|println|printf|write)\(", apb)
       and apb.find("Serial.ham(") < apb.rfind("memset(")
       and ino_k.count("ap_parolasi_bas(") >= 3,
       f"{len(ap)} okuma, {ino_k.count('ap_parolasi_bas(')} ad")
    pd = govde(ino_k, "static void kayit_pil_dcir(float v_oturmus) {")
    ko = govde(esp_k, "static void kayit_ornek(")
    ok("B72.Y1 (1C-1 inceleme M7) pil olayi KENDI mesaj turuyle (KM_PIL_OLAY) yalniz PIL "
       "oturumuna; skop KAL eki (KM_OLAY) yalniz OLCUM oturumuna; baslatma mesajlari olayi "
       "kendi BASLA turune; kayit_ornek KN_DCIR'i oturum turuyle suzer (kn_ek_suz)",
       "m.tur = KM_PIL_OLAY;" in pd
       and "kyn_olay(&kayit_m, KAYIT_OTURUM_PIL, m->yuk, m->n)" in km
       and "kyn_olay(&kayit_m, KAYIT_OTURUM_OLCUM, m->yuk, m->n)" in km
       and km.count("kyn_olay(&kayit_m, b.oturum_turu, m->yuk, m->n)") == 1
       and "kyn_plan_baslat(" in km
       and "kn_ek_suz(kayit_kn_tur, ek)" in ko)
    gk = govde(ino_k, "static void kayit_plan_komut(")
    ok("B72.Y3 (1C-4 inceleme M4) plan NVS'e yazilamazsa (KP_NVS) kart 'kuruldu' DEMEZ, sebebini "
       "ve onceki planin gecerli oldugunu soyler",
       "r == KP_NVS" in gk and gk.find("r == KP_NVS") < gk.find("plan kuruldu")
       and "onceki plan gecerli" in gk)
    kp = govde(ino_k, "static void kayit_pil_baslat() {")
    ok("B72.F36 kayit acilamazsa pil testi YINE baslar ve kart 'KAYDEDILMIYOR' der "
       "(bolum yok / tarama / hata / dolu / bekliyor / kuyruk dolu)",
       "KAYDEDILMIYOR" in kp and "!kayit_bolum" in kp
       and all(x in kp for x in ("KDR_TARIYOR", "KDR_HATA", "KDR_DOLU", "KDR_BEKLIYOR"))
       and "m.basla.oturum_turu = KAYIT_OTURUM_PIL" in kp)
    gd = govde(esp_k, "static void kayit__gonder(")
    ok("B72.F15 kuyruk dolarsa kayip SESSIZ degil: sonraki nokta KAYIP_ONCE, sayac artar",
       "kn_kayip(&kayit_kn)" in gd and "kayit_kuyruk_dusen = kayit_kuyruk_dusen + 1u" in gd)


# ── B72.E · esitleme istemcisi (sahte kart) ───────────────────────────
class _SahteKart:
    """Kartin /kayit/veri ucunun sahtesi — kg_oku ile ayni anlam: `sira` ve
    sonrasi, kayit bolunmeden `bayt`a kadar. Basliklar da gercek kart gibi:
    X-Kayit-Kimlik, X-Sonraki-Sira, X-Onay."""

    def __init__(self, kayitlar: list[bytes]):
        self.kayitlar = kayitlar
        self.bozuk = False
        self.sirayi_yok_say = False     # yanitta istenenden ESKI kayit (savunma)
        self.bos_don = False            # veri var ama bos govde (parca boyu vb.)
        self.kimlik = 7
        self.onay = 0
        self.onay_dusur = 0             # sonraki N onay karta ULASMAZ
        self.komutlar: list[str] = []
        self.kal_liste = None           # 1B: /kal/liste (None = eski firmware, 404)
        self.kal_yanit = None           # ("ham", bayt) · ("kod", 500) · ("kes", bayt): bozuk yanit
        # 1D: imza (BAGIMSIZ dogrulayici, imza.py KULLANILMAZ) + eslestirme uclari
        self.cihazlar: dict[int, bytes] = {}
        self.acilis = "11" * 16
        self.imza_zorunlu = False
        self.gorulen: dict[int, set] = {}
        self.istekler: list[str] = []   # yontem yol basliklar govde (sizinti denetimi)
        self.ret_401 = 0
        self.imzali = 0
        self.parola = "dogru-parola-12"
        self.tuz = bytes(range(16))
        self.tur = 10000                # istemcinin alt siniri (TUR_EN_AZ)
        self.gkimlik = "0011223344556677"
        self.bekleyen = None
        self.kart_kanit_boz = False
        # 4B: kopru WiFi yukari-akisi (kart_wifi.WifiKart) icin
        self.akis_satirlari: list[str] = []   # /akis'te `data:` olarak yollanan protokol satirlari
        self.akis_tut = 0.0                   # satirlardan sonra akis kac s acik kalir (sonra kapanir)
        self.akis_bitir = threading.Event()
        self.akis_dolu = False                # kartin 4 yuvasi dolu: `event: dolu`
        self.akis_sayisi = 0                  # 200 ile acilan /akis
        self.saat_kaynak = 0                  # /eslestir/bilgi "saat": 0 yok, 1 ntp, 2 cihaz
        self.saat_istekleri: list[str] = []
        self.komut_imzali: list[tuple] = []   # (govde, imzali mi)
        self.komut_red = 0                    # !=0: p0 disi komuta bu kodla ret
        # 4C: arka plan esitlemesi (kopru/arka_esitle.py)
        self.erisilemez = False               # ag kopuk: istek yanitsiz kapanir
        self.bilgi_kod = 0                    # !=0: /eslestir/bilgi bu kodla doner (kart hazir degil)
        self.bilgi_hata_kalan = 0             # >0: sonraki N /eslestir/bilgi 503 doner
        self.liste_kod = 0                    # !=0: /kayit/liste bu kodla doner (kayit mesgul)
        self.zaman = time.monotonic           # istek gunlugunun saati (sanal saat verilebilir)
        self.zamanli: list[tuple] = []        # (zaman, yontem, yol) — her istek
        self.onay_kanca = None                # Go<sira> karta ULASTIGI anda cagrilir (sira)
        # 4D: koprunun kart vekili (kopru/vekil.py) icin kartin diger GET uclari
        self.ek_get: dict[str, tuple] = {}    # yol -> (kod, tur, govde); /pil, /kunye.json ...
        self.ek_bekle: dict[str, float] = {}  # yol -> yanittan once bekleme (yavas kart)

    def liste(self) -> dict:
        """Kartin /kayit/liste ozeti (yalniz esitlemenin kullandigi alanlar)."""
        return {"surum": 1, "durum": 1, "sonraki": self.sonraki(), "onay": self.onay,
                "kimlik": self.kimlik, "oturumlar": [{"id": 1, "tur": 1, "ilk": 1,
                                                      "son": self.sonraki() - 1}]}

    def sonraki(self) -> int:
        return max((struct.unpack_from("<I", k, 4)[0] for k in self.kayitlar), default=0) + 1

    def onayla(self, sira: int) -> None:
        """Kartin onayi uygulamasi (seri ya da HTTP yolu)."""
        if self.onay_dusur:
            self.onay_dusur -= 1
            return
        if sira < self.sonraki() and sira > self.onay:
            self.onay = sira

    def veri(self, sira: int, bayt: int) -> tuple[bytes, int, int]:
        govde, ilk, son = b"", 0, 0
        if self.bos_don:
            return govde, ilk, son
        for ham in self.kayitlar:
            s = struct.unpack_from("<I", ham, 4)[0]
            if s < sira and not self.sirayi_yok_say:
                continue
            if len(govde) + len(ham) > bayt:
                break
            govde += ham
            ilk, son = ilk or s, s
        if self.bozuk and len(govde) > 20:
            govde = govde[:20] + bytes([govde[20] ^ 1]) + govde[21:]
        return govde, ilk, son



def _kanonik_bgmz(yontem: str, yol: str, args, acilis: str, sayac: int, govde: bytes) -> bytes:
    """1D spec K9'un BAGIMSIZ yeniden yazimi (imza.py'yi kullanmaz)."""
    import hashlib as _hs
    q = "&".join(urllib.parse.quote(a, safe="-._~") + "=" + urllib.parse.quote(d, safe="-._~")
                 for a, d in args)
    return ("OK1\n" + yontem + "\n" + yol + ("?" + q if q else "") + "\n" + acilis + "\n"
            + str(sayac) + "\n" + _hs.sha256(govde).hexdigest()).encode()


def _es_hmac(P: bytes, etiket: str, kimlik: str, nk: bytes, nc: bytes, son: str) -> bytes:
    import hashlib as _hs
    import hmac as _hm
    return _hm.new(P, f"{etiket}\n{kimlik}\n{nk.hex()}\n{nc.hex()}\n{son}".encode(),
                   _hs.sha256).digest()

def _sunucu(kart: _SahteKart):
    class Isleyici(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _imza(self, yontem: str, govde: bytes):
            """None = imzasiz; True = gecerli; False = 401 gonderildi."""
            import hashlib as _hs
            import hmac as _hm
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
            kart.istekler.append(f"{yontem} {self.path} {dict(self.headers)} {govde!r}")
            kart.zamanli.append((kart.zaman(), yontem, self.path))
            qd = dict(q)
            if self.headers.get("X-Imza"):
                n, s, im = self.headers["X-Cihaz"], self.headers["X-Sayac"], self.headers["X-Imza"]
            elif "_i" in qd:
                n, s, im = qd.get("_c", "0"), qd.get("_s", "0"), qd["_i"]
            else:
                if kart.imza_zorunlu and u.path not in ("/eslestir/bilgi", "/eslestir/baslat",
                                                        "/eslestir/kanit"):
                    self._red()
                    return False
                return None
            K = kart.cihazlar.get(int(n))
            args = [(a, d) for a, d in q if a not in ("_c", "_s", "_i")]
            if K is None or not _hm.compare_digest(
                    _hm.new(K, _kanonik_bgmz(yontem, u.path, args, kart.acilis, int(s), govde),
                            _hs.sha256).hexdigest(), im):
                self._red()
                return False
            g = kart.gorulen.setdefault(int(n), set())
            if int(s) in g or int(s) < 1 or (g and int(s) <= max(g) - 64):
                self._red()
                return False
            g.add(int(s))
            kart.imzali += 1
            return True

        def _red(self):
            kart.ret_401 += 1
            self.send_response(401)
            self.send_header("X-Acilis", kart.acilis)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _json(self, d):
            g = json.dumps(d).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(g)))
            self.end_headers()
            self.wfile.write(g)

        def _kod(self, kod: int):
            self.send_response(kod)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if kart.erisilemez:                          # 4C: ag kopuk — yanitsiz kapanir
                self.close_connection = True
                return
            if self._imza("GET", b"") is False:
                return
            if u.path == "/eslestir/bilgi" and (kart.bilgi_kod or kart.bilgi_hata_kalan > 0):
                if kart.bilgi_hata_kalan > 0:
                    kart.bilgi_hata_kalan -= 1
                self._kod(kart.bilgi_kod or 503)
                return
            if u.path == "/kayit/liste":                 # 4C: kartla ayni anlam (oturum dizini)
                if kart.liste_kod:
                    self._kod(kart.liste_kod)
                    return
                self._json(kart.liste())
                return
            if u.path == "/eslestir/bilgi":
                self._json({"surum": "OK1", "kimlik": kart.gkimlik, "acilis": kart.acilis,
                            "tuz": kart.tuz.hex(), "tur": kart.tur, "zorunlu": int(kart.imza_zorunlu),
                            "misafir": 0, "saat": kart.saat_kaynak, "cihaz_azami": 8})
                return
            if u.path == "/akis":
                kart.akis_sayisi += 1
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                if kart.akis_dolu:                       # gercek kart: 4 yuva doluysa
                    self.wfile.write(b"event: dolu\ndata: 4\n\n")
                    return
                self.wfile.write(b'retry: 3000\n\nevent: kimlik\n'
                                 b'data: {"jeton":"abc123","surucu":true}\n\n')
                for i, s in enumerate(list(kart.akis_satirlari)):   # gercek kartin bicimi (B22.4)
                    self.wfile.write(f"id: {i + 1}\ndata: {s}\n\n".encode("utf-8"))
                self.wfile.write(b": kalp\n\n")
                self.wfile.flush()
                if kart.akis_tut:
                    kart.akis_bitir.wait(kart.akis_tut)
                return
            if u.path == "/kal/liste" and kart.kal_yanit is not None:
                tur, deger = kart.kal_yanit
                if tur == "kod":
                    self.send_error(deger)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                # "kes": gövdenin yarisi gelir, baglanti kopar (IncompleteRead)
                self.send_header("Content-Length", str(len(deger) * (2 if tur == "kes" else 1)))
                self.end_headers()
                self.wfile.write(deger)
                return
            if u.path == "/kal/liste" and kart.kal_liste is not None:
                govde = json.dumps(kart.kal_liste, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                self.wfile.write(govde)
                return
            if u.path in kart.ek_get:                    # 4D: vekil sinamasi (imza yukarida denetlendi)
                if kart.ek_bekle.get(u.path):
                    time.sleep(kart.ek_bekle[u.path])
                kod, tur, govde = kart.ek_get[u.path]
                self.send_response(kod)
                self.send_header("Content-Type", tur)
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                self.wfile.write(govde)
                return
            if u.path != "/kayit/veri":
                self.send_error(404)
                return
            govde, ilk, son = kart.veri(int(q.get("sira", ["1"])[0]),
                                        int(q.get("bayt", ["8192"])[0]))
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("X-Kayit-Kimlik", str(kart.kimlik))
            self.send_header("X-Ilk-Sira", str(ilk))
            self.send_header("X-Son-Sira", str(son))
            self.send_header("X-Sonraki-Sira", str(kart.sonraki()))
            self.send_header("X-Onay", str(kart.onay))
            self.end_headers()
            self.wfile.write(govde)

        def do_POST(self):
            import hashlib as _hs
            import hmac as _hm
            n = int(self.headers.get("Content-Length", "0"))
            ham = self.rfile.read(n)
            govde = ham.decode()
            u = urllib.parse.urlparse(self.path)
            qd = dict(urllib.parse.parse_qsl(u.query, keep_blank_values=True))
            if kart.erisilemez:
                self.close_connection = True
                return
            imzali = self._imza("POST", ham)
            if imzali is False:
                return
            if u.path == "/eslestir/baslat":
                kart.bekleyen = (1, bytes(range(0x20, 0x30)), bytes.fromhex(qd["nc"]), qd["ad"])
                self._json({"eno": 1, "nk": bytes(range(0x20, 0x30)).hex()})
                return
            if u.path == "/eslestir/kanit":
                eno, nk, nc, ad = kart.bekleyen
                kart.bekleyen = None
                P = _hs.pbkdf2_hmac("sha256", kart.parola.encode(), kart.tuz, kart.tur, 32)
                if not _hm.compare_digest(_es_hmac(P, "OK1-istemci", kart.gkimlik, nk, nc, ad).hex(),
                                          qd["kanit"]):
                    self.send_response(403)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                yeni = min(i for i in range(1, 9) if i not in kart.cihazlar)
                kart.cihazlar[yeni] = _es_hmac(P, "OK1-anahtar", kart.gkimlik, nk, nc, str(yeni))
                kk = _es_hmac(P, "OK1-kart", kart.gkimlik, nk, nc, str(yeni))
                if kart.kart_kanit_boz:
                    kk = bytes(32)
                self._json({"n": yeni, "kart_kanit": kk.hex()})
                return
            if u.path == "/saat":                        # 1D: CIHAZ sinifi — imza ZORUNLU
                if not imzali:
                    self._red()
                    return
                if kart.saat_kaynak == 1:
                    self.send_response(409)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                kart.saat_istekleri.append(qd.get("unix", ""))
                self.send_response(204)
                self.end_headers()
                return
            serbest = govde in ("p0", "?") and self.headers.get("X-Olcum") == "1"   # komut_serbest
            if kart.komut_red and govde != "p0":
                self.send_response(kart.komut_red)
                self.send_header("Content-Length", "11")
                self.end_headers()
                self.wfile.write(b"reddedildi!")
                return
            if imzali or serbest or (self.headers.get("X-Olcum") == "1"
                                     and self.headers.get("X-Jeton") == "abc123"):
                kart.komut_imzali.append((govde, bool(imzali)))
                kart.komutlar.append(govde)
                if govde.startswith("Go"):
                    if kart.onay_kanca:
                        kart.onay_kanca(int(govde[2:]))
                    kart.onayla(int(govde[2:]))
                self.send_response(204)
            else:
                self.send_response(403)
            self.end_headers()

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def _kayitlar(n: int, bas: int = 1) -> list[bytes]:
    return [KB.kayit_paketle(KB.T_NOKTA if i % 3 else KB.T_SAAT, i, 7,
                             bytes((i + j) & 0xFF for j in range(4 + (i % 5) * 36)))
            for i in range(bas, bas + n)]


def _hatali(islev) -> bool:
    try:
        islev()
    except ValueError:
        return True
    return False


def _es(taban: str, d, onay=None, **kw):
    return KE.Esitleyici(taban, d, onay, onay_bekle=0.01, **kw)


def bolum_esitle() -> None:
    print("\n── B72.E  esitleme istemcisi (sahte kart)")
    kay = _kayitlar(50)
    tum = b"".join(kay)
    kart = _SahteKart(kay)
    sunucu, taban = _sunucu(kart)

    def sifirla(kayitlar=None):
        kart.__init__(kay if kayitlar is None else kayitlar)
    try:
        with tempfile.TemporaryDirectory() as d:
            onaylar: list[tuple[int, int]] = []

            def onay(s):   # onay aninda dosyada kac bayt var
                onaylar.append((s, (Path(d) / KE.DOSYA).stat().st_size))
                kart.onayla(s)

            e = _es(taban, d, onay, bayt=1100)
            e.esitle(azami_tur=2)
            r = e.esitle()
            dosya = (Path(d) / KE.DOSYA).read_bytes()
            ok("B72.E1 karttaki butun kayitlar diske AYNEN (bayt bayt) geldi",
               dosya == tum and e.son_sira() == 50, f"{r}")
            ok("B72.E2 kesilen esitleme kaldigi yerden surdu, tekrar yok",
               len(KB.akis_coz(dosya)) == 50)
            yazili = [len(b"".join(k for k in kay if struct.unpack_from("<I", k, 4)[0] <= s))
                      for s, _ in onaylar]
            ok("B72.E4 onay YALNIZ diske yazildiktan sonra ve yazilanin sonuna kadar",
               bool(onaylar) and all(b == y for (_, b), y in zip(onaylar, yazili))
               and onaylar[-1][0] == 50 and kart.onay == 50, f"{onaylar[:3]}...")
            n_onay = len(onaylar)
            r2 = e.esitle()
            ok("B72.E5 yeni kayit yokken tekrar kosmak hicbir sey cekmez, onaylamaz",
               r2["yeni_kayit"] == 0 and len(onaylar) == n_onay)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            kart.bozuk = True
            onaylar2: list[int] = []
            hata = _hatali(lambda: _es(taban, d, onaylar2.append).esitle())
            ok("B72.E3 bozuk yanit REDDEDILIR: diske yazilmaz, onaylanmaz",
               hata and not onaylar2 and not (Path(d) / KE.DOSYA).exists())
        sifirla(kay[10:])                       # 1..10 temizlikte silinmis
        with tempfile.TemporaryDirectory() as d:
            r = _es(taban, d).esitle()
            ok("B72.E6 temizlikte silinmis aralik BOSLUK olarak bildirilir",
               r["bosluk"] == [(1, 11)] and r["son_sira"] == 50, f"{r['bosluk']}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d)
            e.esitle()
            kart.kayitlar = kay + _kayitlar(3, 51)
            kart.sirayi_yok_say = True          # yanitta istenenden ESKI kayit
            # azami_tur: denetim yoksa (mutasyon) 100 000 tur fsync'le ~20 dk donuyordu
            hata = _hatali(lambda: e.esitle(azami_tur=100))
            ok("B72.E7 yanitta istenenden eski/tekrar sira gelirse esitleme DURUR",
               hata and (Path(d) / KE.DOSYA).read_bytes() == tum and e.son_sira() == 50)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, bayt=1100)
            e.esitle(azami_tur=1)
            yarim = kay[e.son_sira()]           # sira son+1 (> 100 B)
            with open(Path(d) / KE.DOSYA, "ab") as f:
                f.write(yarim[:len(yarim) // 2])   # durum yazilmadan kesilen YARIM ekleme
            e.esitle()
            ok("B72.E9 durum yazilmadan kesilen YARIM ekleme kirpilir: dosya tam, tekrarsiz",
               (Path(d) / KE.DOSYA).read_bytes() == tum)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            def patlayan(s):
                raise OSError("ag koptu")
            try:
                _es(taban, d, patlayan).esitle()
            except OSError:
                pass
            onaylar3: list[int] = []

            def onay3(s):
                onaylar3.append(s)
                kart.onayla(s)
            r = _es(taban, d, onay3).esitle()
            ok("B72.E10 onay yollanamadiysa sonraki kosu yeniden yollar (veri tekrar "
               "cekilmez)", onaylar3 == [50] and r["yeni_kayit"] == 0 and kart.onay == 50,
               f"{onaylar3} {r}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, kart.onayla)
            e.esitle()
            kart.kimlik = 99                    # NVS kayboldu: kart YENI akis basladi
            kart.kayitlar = kay + _kayitlar(5, 51)
            n0 = kart.onay
            hata = _hatali(e.esitle)
            ok("B72.E11 kartin akis KIMLIGI degisirse esitleme DURUR: yazmaz, onaylamaz",
               hata and (Path(d) / KE.DOSYA).read_bytes() == tum and kart.onay == n0)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, kart.onayla)
            e.esitle()
            kart.kayitlar = _kayitlar(3)        # numara 1'den yeniden (kimlik AYNI)
            hata = _hatali(e.esitle)
            ok("B72.E12 kartin sirasi istemcinin gerisine duserse (bos yanit + "
               "X-Sonraki-Sira) esitleme DURUR — sessiz 'yeni 0 kayit' YOK",
               hata and e.son_sira() == 50)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            kart.bos_don = True                 # kartta kayit var ama govde bos
            r = _es(taban, d).esitle()
            # HATA degil: bicimlenmis araligi ya da harcanmis (yarim yazilmis)
            # sirayi da ayni sekilde gorur. ATLAMAZ da: veri gelince okunur.
            ok("B72.E13 kartta daha yeni kayit varken bos yanit: sessizce 'bitti' YOK — "
               "uyari + bekleyen sayisi, son_sira ilerlemez, yazilmaz",
               r.get("bekleyen") == 50 and r["son_sira"] == 0 and bool(r.get("uyari"))
               and not (Path(d) / KE.DOSYA).exists(), f"{r}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            kart.onay_dusur = 1                 # ilk onay kuyrukta dustu
            e = _es(taban, d, kart.onayla)
            r = e.esitle()
            durum = e._durum()
            ok("B72.E14 onay karta ulasmazsa X-Onay'dan anlasilir ve YENIDEN yollanir; "
               "'onaylandi' yalniz kart dogrulayinca yazilir",
               kart.onay == 50 and durum["onaylanan"] == 50 and r.get("onay_dogrulandi"),
               f"kart.onay={kart.onay} durum={durum} r={r}")
            kart.onay_dusur = 99                # kart onaylari hic almiyor
            kart.onay = 0
            e2 = _es(taban, d, kart.onayla)
            d2 = e2._durum()
            d2["onaylanan"] = 0
            e2._durum_yaz(d2)
            r2 = e2.esitle()
            ok("B72.E14b kart onayi hic almazsa 'onaylandi' YAZILMAZ, sonraki kosu yeniden dener",
               not r2.get("onay_dogrulandi") and e2._durum()["onaylanan"] == 0, f"{r2}")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, kart.onayla, bayt=1100)
            e.esitle(azami_tur=1)
            d1 = e._durum()
            ek = b"".join(k for k in kay if struct.unpack_from("<I", k, 4)[0] > d1["son_sira"])[:2000]
            gecerli = KB.akis_onek(ek)[1]
            with open(Path(d) / KE.DOSYA, "ab") as f:
                f.write(ek)                     # fsync'li veri + yeniden adlandirma KAYBOLDU
            e.esitle()
            ok("B72.E15 durum.json geride kalmissa (rename kayboldu) dosyadaki GECERLI "
               "kayitlar korunur, ileri sarilir; tekrar yok, dosya tam",
               gecerli > 0 and (Path(d) / KE.DOSYA).read_bytes() == tum and e.son_sira() == 50,
               f"ileri sarilan {gecerli} B")
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            e = _es(taban, d, bayt=1100)
            e.esitle(azami_tur=1)
            with open(Path(d) / KE.DOSYA, "ab") as f:
                f.write(kay[-1])                # GECERLI ama sirasi ATLAYAN kuyruk
            e.esitle()
            ok("B72.E17 ileri sarma yalniz kesintisiz diziyi kabul eder: atlayan kuyruk "
               "kirpilir, aradaki kayitlar yeniden cekilir (kayip yok)",
               (Path(d) / KE.DOSYA).read_bytes() == tum and e.son_sira() == 50)
        sifirla()
        with tempfile.TemporaryDirectory() as d:
            with KE.Kilit(Path(d)):
                try:
                    _es(taban, d).esitle()
                    ikinci = False
                except RuntimeError:
                    ikinci = True
            ok("B72.E16 ayni dizinde ikinci esitleme kilit yuzunden BASLAMAZ",
               ikinci and not (Path(d) / KE.DOSYA).exists())
        sifirla()
        kal = {"surum": 1, "adet": 2, "taslak": 0, "azami": 40, "kayitlar": [
            {"no": 1, "unix": 0, "acilis": 0, "tur": 0, "kaynak": 2,
             "not": "1B oncesi kalibrasyon (Ayar3)",
             "kal": {"normal": {"n": 16.5, "pga": 2.0, "kazanc": 1.0, "sifir_ham": -12, "tau": 0.0029},
                     "yuksek": {"n": 312.5, "pga": 2.0, "kazanc": 0.99, "sifir_ham": 5, "tau": 0.0031},
                     "i_ofset": -3, "i_pga": 0.25, "sont_ohm": 0.005, "i_duzeltme": 1.0,
                     "sebeke_hz": 50.0, "faz0": 12.5, "faz1": -3.25}},
            {"no": 2, "unix": 1790000000, "acilis": 5, "tur": 1, "kaynak": 0,
             "not": "şönt değişti ğü", "kal": {}}]}
        kart.kal_liste = kal
        with tempfile.TemporaryDirectory() as d:
            r = _es(taban, d, kart.onayla).esitle()
            p = Path(d) / KE.KAL_DOSYA
            yuklu = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
            ok("B72.E18 kalibrasyon gecmisi kalibrasyon.json'a ATOMIK yazilir, Turkce not "
               "bozulmadan (karttaki listeyle ayni)",
               yuklu == kal and r.get("kalibrasyon") == 2
               and not p.with_suffix(".tmp").exists(), f"{r.get('kalibrasyon')}")
        kart.kal_liste = None
        with tempfile.TemporaryDirectory() as d:
            r = _es(taban, d, kart.onayla).esitle()
            ok("B72.E19 eski firmware (/kal/liste 404) veri esitlemesini DURDURMAZ",
               r["son_sira"] == 50 and r.get("kalibrasyon") is None
               and r.get("kalibrasyon_hata") is None               # 404 hata DEGIL
               and not (Path(d) / KE.KAL_DOSYA).exists(), f"{r}")
        # 1B son inceleme I3: PC dosyayi korlemesine eziyordu
        with tempfile.TemporaryDirectory() as d:
            sifirla()
            kart.kal_liste = json.loads(json.dumps(kal))
            _es(taban, d, kart.onayla).esitle()
            p = Path(d) / KE.KAL_DOSYA
            kart.kal_liste["kayitlar"][1]["not"] = "not duzeltildi"      # kn: olagan
            kart.kal_liste["kayitlar"][1]["tur"] = 2                     # kt: olagan
            r1 = _es(taban, d, kart.onayla).esitle()
            arsiv1 = sorted(x.name for x in Path(d).glob("kalibrasyon-*.json"))
            duzeltme_yazildi = json.loads(p.read_text(encoding="utf-8")) == kart.kal_liste
            onceki = p.read_bytes()
            # ayni numara, BASKA tarih (NVS silinip gecmis yeniden kuruldu)
            kart.kal_liste["kayitlar"][0] = {**kal["kayitlar"][0], "unix": 1791000000}
            r2 = _es(taban, d, kart.onayla).esitle()
            arsiv2 = sorted(Path(d).glob("kalibrasyon-*.json"))
            ikinci = p.read_bytes()
            # bir kayit KAYBOLDU (`adet` kayboldu, baska kart)
            kart.kal_liste = {**kart.kal_liste, "adet": 1, "kayitlar": kart.kal_liste["kayitlar"][:1]}
            r3 = _es(taban, d, kart.onayla).esitle()
            arsiv3 = sorted(Path(d).glob("kalibrasyon-*.json"))
            ok("B72.E20 not/tur duzeltmesi dosyaya yazilir (yedek yok); kartin gecmisi "
               "DEGISIRSE (ayni numara baska deger/tarih · kayit kayboldu) eski dosya "
               "zaman damgali YEDEKLENIR, sonra kartinki yazilir — PC hicbir kaydi kaybetmez",
               duzeltme_yazildi and not arsiv1 and r1.get("kalibrasyon_arsiv") is None
               and len(arsiv2) == 1 and arsiv2[0].read_bytes() == onceki
               and r2.get("kalibrasyon_arsiv") == arsiv2[0].name
               and len(arsiv3) == 2 and r3.get("kalibrasyon_arsiv") in {x.name for x in arsiv3}
               and (Path(d) / r3["kalibrasyon_arsiv"]).read_bytes() == ikinci
               and json.loads(p.read_text(encoding="utf-8")) == kart.kal_liste,
               f"arsiv1={arsiv1} arsiv2={[x.name for x in arsiv2]} arsiv3={[x.name for x in arsiv3]}")
        # 1B son inceleme I4: /kal/liste hatasi veri esitlemesinden SONRA cokuyordu
        durumlar = {"bozuk JSON": ("ham", b"{bozuk"), "500": ("kod", 500),
                    "yarida kopan": ("kes", b'{"surum":1,"adet":'),
                    "gecersiz UTF-8 (cp1254)": ("ham", b'{"surum":1,"adet":1,"kayitlar":'
                                                       b'[{"no":1,"not":"\xfe\xf0nt"}]}')}
        sonuc = {}
        for ad, yanit in durumlar.items():
            with tempfile.TemporaryDirectory() as d:
                sifirla()
                p = Path(d) / KE.KAL_DOSYA
                p.write_text('{"eski": 1}', encoding="utf-8")
                kart.kal_yanit = yanit
                try:
                    r = _es(taban, d, kart.onayla).esitle()
                except Exception as h:                       # noqa: BLE001
                    r = {"istisna": repr(h)}
                sonuc[ad] = (r.get("son_sira"), r.get("kalibrasyon"), r.get("kalibrasyon_hata"),
                             p.read_text(encoding="utf-8"), r.get("istisna"))
        ok("B72.E21 /kal/liste bozuk/yarim/500 ise veri esitlemesi TAMAMLANIR, hata "
           "raporlanir, eski kalibrasyon.json yerinde; gecersiz UTF-8 (eski firmware'in "
           "cp1254 notu) degistirilerek yazilir",
           all(v[0] == 50 and v[4] is None for v in sonuc.values())
           and all(v[1] is None and v[2] and v[3] == '{"eski": 1}'
                   for a, v in sonuc.items() if a != "gecersiz UTF-8 (cp1254)")
           and sonuc["gecersiz UTF-8 (cp1254)"][1] == 1
           and "�" in sonuc["gecersiz UTF-8 (cp1254)"][3],
           str({a: (v[0], v[1], v[2], v[4]) for a, v in sonuc.items()}))
        kart.kal_yanit = None
        # Y6 (1B inceleme M2): kartin okuyamadigi kayit {"no", "bozuk": true} gelir
        with tempfile.TemporaryDirectory() as d:
            sifirla()
            kart.kal_liste = json.loads(json.dumps(kal))
            _es(taban, d, kart.onayla).esitle()
            p = Path(d) / KE.KAL_DOSYA
            kart.kal_liste["kayitlar"][1] = {"no": 2, "bozuk": True}
            r6 = _es(taban, d, kart.onayla).esitle()
            y6 = json.loads(p.read_text(encoding="utf-8"))
            arsiv6 = sorted(x.name for x in Path(d).glob("kalibrasyon-*.json"))
        with tempfile.TemporaryDirectory() as d:
            sifirla()
            kart.kal_liste = json.loads(json.dumps(kal))
            kart.kal_liste["kayitlar"][1] = {"no": 2, "bozuk": True}
            r7 = _es(taban, d, kart.onayla).esitle()
            y7 = json.loads((Path(d) / KE.KAL_DOSYA).read_text(encoding="utf-8"))
        ok("B72.Y6b (1B inceleme M2) kartta BOZUK kayit: PC'de saglam kopyasi varsa O KALIR "
           "('kartta_bozuk' isaretiyle, yedek ACILMAZ); yoksa bozuk isaretiyle yazilir — eksik "
           "gecmis TAM sanilmaz; esitleme bozuk numaralari bildirir",
           y6["kayitlar"][1] == {**kal["kayitlar"][1], "kartta_bozuk": True} and not arsiv6
           and r6.get("kalibrasyon_bozuk") == [2]
           and y7["kayitlar"][1] == {"no": 2, "bozuk": True} and r7.get("kalibrasyon_bozuk") == [2],
           f"y6={y6['kayitlar'][1]} arsiv={arsiv6} r6={r6.get('kalibrasyon_bozuk')} "
           f"y7={y7['kayitlar'][1]} r7={r7.get('kalibrasyon_bozuk')}")
        sifirla()
        KE.http_onay(taban)(42)
        ok("B72.E8 HTTP onayi jetonu /akis'ten alip X-Olcum + X-Jeton ile Go<sira> yollar",
           kart.komutlar == ["Go42"], str(kart.komutlar))
    finally:
        sunucu.shutdown()

# ── B72.G · 1D guvenlik: Python basvuru cekirdegi + test vektorleri ──────────
# RFC 4231 (HMAC-SHA256) ve RFC 7914 §11 (PBKDF2-HMAC-SHA256). Sabitler RFC'den;
# Python'un kendi hmac/hashlib'i ile de karsilastirilir (yanlis kopyalanmis
# sabit YESIL gecemez).
RFC4231 = [
    (bytes([0x0b]) * 20, b"Hi There",
     "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"),
    (b"Jefe", b"what do ya want for nothing?",
     "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"),
    (bytes([0xaa]) * 20, bytes([0xdd]) * 50,
     "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"),
    (bytes(range(1, 26)), bytes([0xcd]) * 50,
     "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"),
    (bytes([0xaa]) * 131, b"Test Using Larger Than Block-Size Key - Hash Key First",
     "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"),
    (bytes([0xaa]) * 131,
     b"This is a test using a larger than block-size key and a larger than "
     b"block-size data. The key needs to be hashed before being used by the "
     b"HMAC algorithm.",
     "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2"),
]
RFC7914 = [
    ("passwd", b"salt", 1,
     "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc"
     "49ca9cccf179b645991664b39d77ef317c71b845b1e30bd509112041d3a19783"),
    ("Password", b"NaCl", 80000,
     "4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56"
     "a1d425a1225833549adb841b51c9b3176a272bdebba1d078478f62b397f33c8d"),
]


def _ham_hmac(k: bytes, m: bytes) -> bytes:
    import hmac as _h
    import hashlib as _s
    return _h.new(k, m, _s.sha256).digest()


def bolum_guvenlik_py() -> None:
    """1D T1: kopru/imza.py saf islevleri + uretim/vektor_guvenlik.json.
    Protokol ornekleri BURADA spec'teki bicim yeniden yazilarak bagimsiz
    hesaplanir (imza.py'nin dizgi kurulusunu kopyalamaz)."""
    import hashlib
    print("\n── B72.G  1D guvenlik: Python cekirdegi · RFC vektorleri · kanonik bicim")
    try:
        import imza as IM
    except ImportError as e:
        ok("B72.G0 kopru/imza.py yuklenir", False, str(e))
        return
    vj = BURASI / "vektor_guvenlik.json"
    V = json.loads(vj.read_text(encoding="utf-8")) if vj.exists() else {}
    ok("B72.G0 uretim/vektor_guvenlik.json var ve RFC + protokol bolumleri iceriyor",
       all(k in V for k in ("hmac", "pbkdf2", "protokol", "imza")), str(sorted(V)))

    # G1 HMAC: RFC sabiti == Python hmac == JSON
    g1 = all(_ham_hmac(k, m).hex() == h for k, m, h in RFC4231)
    g1j = [(x["anahtar"], x["veri"], x["hmac"]) for x in V.get("hmac", [])] == \
          [(k.hex(), m.hex(), h) for k, m, h in RFC4231]
    ok("B72.G1 RFC 4231 HMAC-SHA256 (1,2,3,4,6,7): RFC sabiti == Python hmac == JSON",
       g1 and g1j, f"hmac={g1} json={g1j}")

    # G2 PBKDF2: RFC 7914 == hashlib == imza.pbkdf2 (32 B onek)
    g2 = all(hashlib.pbkdf2_hmac("sha256", p.encode(), s, c, 64).hex() == h
             for p, s, c, h in RFC7914)
    g2i = all(IM.pbkdf2(p, s, c).hex() == h[:64] for p, s, c, h in RFC7914[:1])
    g2j = [(x["parola"], x["tuz"], x["tur"], x["dk"]) for x in V.get("pbkdf2", [])] == \
          [(p, s.hex(), c, h) for p, s, c, h in RFC7914]
    ok("B72.G2 RFC 7914 PBKDF2-HMAC-SHA256: RFC == hashlib == imza.pbkdf2 (32 B) == JSON",
       g2 and g2i and g2j, f"hashlib={g2} imza={g2i} json={g2j}")

    # G3 yuzde kodlama
    g3 = (IM.yuzde_kodla("a&b=c") == "a%26b%3Dc" and IM.yuzde_kodla("ğ") == "%C4%9F"
          and IM.yuzde_kodla("a b") == "a%20b" and IM.yuzde_kodla("Az09-._~") == "Az09-._~")
    ok("B72.G3 yuzde kodlama: & = bosluk ve UTF-8 kodlanir; A-Z a-z 0-9 - . _ ~ aynen", g3)

    # G4 kanonik belirsizlik (Review Focus 1)
    k1 = IM.kanonik("GET", "/kayit/veri", [("a", "1&b=2")], "00" * 16, 5, b"")
    k2 = IM.kanonik("GET", "/kayit/veri", [("a", "1"), ("b", "2")], "00" * 16, 5, b"")
    ok("B72.G4 kanonik BELIRSIZ DEGIL: a='1&b=2' ile a=1&b=2 farkli metin", k1 != k2,
       f"{k1!r} | {k2!r}")

    # G5 protokol: spec bicimiyle bagimsiz hesap == imza.py == JSON
    p = V.get("protokol", {})
    try:
        P, kim, nk, nc, ad, n = (bytes.fromhex(p["P"]), p["kimlik"], bytes.fromhex(p["nk"]),
                                 bytes.fromhex(p["nc"]), p["ad"], p["n"])
        govde = f"\n{kim}\n{nk.hex()}\n{nc.hex()}\n"
        bek_i = _ham_hmac(P, ("OK1-istemci" + govde + ad).encode()).hex()
        bek_k = _ham_hmac(P, ("OK1-kart" + govde + str(n)).encode()).hex()
        bek_a = _ham_hmac(P, ("OK1-anahtar" + govde + str(n)).encode()).hex()
        g5 = (IM.kanit_istemci(P, kim, nk, nc, ad).hex() == bek_i == p["kanit_istemci"]
              and IM.kanit_kart(P, kim, nk, nc, n).hex() == bek_k == p["kanit_kart"]
              and IM.cihaz_anahtari(P, kim, nk, nc, n).hex() == bek_a == p["K"])
    except (KeyError, ValueError) as e:
        g5 = False
        bek_i = str(e)
    ok("B72.G5 eslestirme: istemci kaniti, kart kaniti ve K spec bicimiyle (OK1-*, \\n "
       "ayirici, ad sonda) bagimsiz hesapla == imza.py == JSON; ad UTF-8 ('PC ğ')",
       g5 and "ğ" in p.get("ad", ""), bek_i[:40])

    # G6 imza ornekleri: spec bicimi bagimsiz yeniden yazim
    def _kanonik_bagimsiz(y, yol, args, ac, s, gv):
        import urllib.parse as up
        q = "&".join(up.quote(a, safe="-._~") + "=" + up.quote(d, safe="-._~") for a, d in args)
        return ("OK1\n" + y + "\n" + yol + ("?" + q if q else "") + "\n" + ac + "\n"
                + str(s) + "\n" + hashlib.sha256(gv).hexdigest()).encode()
    g6, notlar = True, []
    for o in V.get("imza", []):
        args = [tuple(x) for x in o["argumanlar"]]
        kb = _kanonik_bagimsiz(o["yontem"], o["yol"], args, o["acilis"], o["sayac"],
                               bytes.fromhex(o["govde"]))
        ki = IM.kanonik(o["yontem"], o["yol"], args, o["acilis"], o["sayac"],
                        bytes.fromhex(o["govde"]))
        im = IM.imzala(bytes.fromhex(o["K"]), o["yontem"], o["yol"], args, o["acilis"],
                       o["sayac"], bytes.fromhex(o["govde"]))
        if not (kb == ki and kb.hex() == o["kanonik"] and im == o["imza"]
                == _ham_hmac(bytes.fromhex(o["K"]), kb).hex()):
            g6 = False
            notlar.append(o["ad"])
    turler = {o["ad"] for o in V.get("imza", [])}
    ok("B72.G6 imza ornekleri (GET sorgusuz, GET sorgulu+yuzde kodlu, POST govdeli, "
       "akis _c/_s/_i HARIC): bagimsiz kanonik == imza.py == JSON",
       g6 and {"get", "get_sorgu", "post", "akis"} <= turler, f"{notlar} {sorted(turler)}")
    ak = [o for o in V.get("imza", []) if o["ad"] == "akis"]
    ok("B72.G6b EventSource imza argumanlari (_c _s _i) kanonige GIRMEZ",
       bool(ak) and "_c" not in bytes.fromhex(ak[0]["kanonik"]).decode()
       and "_i" not in bytes.fromhex(ak[0]["kanonik"]).decode())

    # G8 JSON guncel: imza.py degisip vektorler yeniden uretilmezse C (B71.U) eski
    # vektorlerle sinanirdi
    import vektor_guvenlik as VG
    ok("B72.G8 vektor_guvenlik.json GUNCEL (vektor_guvenlik.uret() ile ayni)",
       vj.exists() and json.loads(vj.read_text(encoding="utf-8")) == VG.uret())

    # G7 ad
    ok("B72.G7 ad_gecerli: 1-24 bayt UTF-8, kontrol karakteri yok",
       IM.ad_gecerli("Telefon ğ") and not IM.ad_gecerli("x" * 25)
       and not IM.ad_gecerli("a\nb") and not IM.ad_gecerli("")
       and not IM.ad_gecerli("ğ" * 13) and IM.ad_gecerli("ğ" * 12))


def bolum_guvenlik_kart() -> None:
    """1D T3: kartin web kapisi, uclar, imzali komut, USB'ye ozel E komutlari,
    K'nin YALNIZ ham UART'a basilmasi (Serial aynasi SSE'ye tasir)."""
    print("\n── B72.F74+  1D kart: kapi · uclar · imzali komut · E komutlari · ham UART")
    esp, ino, gh, wa = (_oku("guvenlik_esp.h"), _oku("olcum-karti-a3.ino"), _oku("guvenlik.h"),
                        _oku("web_akis.h"))
    esp_k, ino_k, gh_k, wa_k = kod(esp), kod(ino), kod(gh), kod(wa)
    SINIF = {"/": "GUV_ACIK", "/akis": "GUV_IZLEME", "/pil": "GUV_IZLEME",
             "/kayit/liste": "GUV_OKUMA", "/kayit/veri": "GUV_OKUMA", "/kal/liste": "GUV_OKUMA",
             "/skop.bin": "GUV_OKUMA", "/komut": "GUV_KOMUT",   # 4B: /kopru KALKTI (PC8)
             "/eslestir/bilgi": "GUV_ACIK", "/eslestir/baslat": "GUV_ACIK",
             "/eslestir/kanit": "GUV_ACIK", "/cihaz/liste": "GUV_CIHAZ",
             "/cihaz/sil": "GUV_CIHAZ", "/saat": "GUV_CIHAZ",
             "/bildirim/bilgi": "GUV_CIHAZ"}                       # 1E (K10)
    kayitlar = re.findall(r'sunucu\.on\("([^"]+)"\s*,\s*(?:(HTTP_\w+)\s*,\s*)?(\w+)\s*\)', ino_k)
    eksik, yanlis = [], []
    for yol, yontem, isl in kayitlar:
        bek = "GUV_ACIK" if yontem == "HTTP_OPTIONS" else SINIF.get(yol)
        if bek is None:
            eksik.append(yol)
            continue
        if f"guv_kapi({bek})" not in govde(ino_k, f"void {isl}(")[:700]:
            yanlis.append((yol, isl))
    ok("B72.F74 HER web ucu kapidan gecer, sinifi tabloya uyar; tabloda olmayan uc YOK; "
       "spec'teki 6 yeni uc kayitli",
       bool(kayitlar) and not eksik and not yanlis
       and set(SINIF) <= {y for y, _, _ in kayitlar}, f"eksik={eksik} yanlis={yanlis}")

    kg = govde(ino_k, "void komut_sayfa(")
    i_blok = kg.find("if (!guv_imzali && !komut_serbest(k.c_str())) {")
    ok("B72.F75 imzali komut jeton + parola ARAMAZ; imzasiz dal bugunku jeton + Basic yolu",
       0 <= i_blok < kg.find('sunucu.header("X-Jeton")') < kg.find("web_yetki()"))
    i_e = kg.find("k[0] == 'E'")
    ok("B72.F76 /komut 'E' ile baslayan komutu 403 ile REDDEDER (USB'ye ozel), kuyruga koymadan",
       0 <= i_e < kg.find("komut_kuyruga(") and "403" in kg[i_e:i_e + 200])
    ok("B72.F81 zorunlu 1'de imzasiz komut reddi komut_serbest'ten SONRA (p0 ve ? serbest kalir)",
       0 <= i_blok < kg.find("guv.ayar.zorunlu") < kg.find('sunucu.header("X-Jeton")'))

    sk = govde(ino_k, "static void guv_seri_komut(")
    khex = [s for s in sk.splitlines() if "khex" in s]
    # 4B (D5 #12 kok): eski iddia "khex bir Serial.ham satirinda" diyordu ve satir UC ham()
    # cagrisiyla basiliyordu (onek, hex, CRLF): araya IDF gunlugu girerse anahtar ayri satira
    # dusuyor, kopru suzgeci onu isaretsiz goruyordu. Artik EK satiri TEK tamponda kurulur
    # ("EK %u %s\r\n"), TEK ham() ile gider, iki tampon da silinir.
    sp = sk[sk.find("case 'p':"):sk.find("case 'z':")]
    ok("B72.F77 (+4B D5 #12) K hex'i YALNIZ ham UART'a ve TEK yazimla: EK satiri (onek + 64 hex + "
       "CRLF) tek tamponda, `p` dalinda TEK Serial.ham; khex hicbir aynali baskida yok; tamponlar "
       "silinir; WebAkis::ham yalniz gercek porta yazar",
       '"EK %u %s\\r\\n"' in sp and sp.count("Serial.ham(") == 1
       and not any(("Serial.print" in s or "Serial.ham" in s) for s in khex)
       and sp.find("Serial.ham(") < sp.rfind("memset(")
       and "void ham(const char *s)" in wa_k
       and "_besle" not in govde(wa_k, "void ham(const char *s)"),
       f"ham={sp.count('Serial.ham(')}")
    ok("B72.F82 E komutlari (z zorunlu, m misafir, p USB eslestirme, x sil, t tur olcumu, r tur "
       "yaz, ? liste) seri dagiticida", all(f"case '{c}':" in sk for c in "zmpxtr?"))

    kp = govde(ino_k, "static bool guv_kapi(")
    dg = govde(ino_k, "static bool guv__dogrula(")
    ok("B72.F78 imza basligi VARSA sonuc dogrulamadir: basarisizsa 401 + X-Acilis, imzasiz dala "
       "DUSMEZ (zorunlu 0'da da)",
       "if (guv__imza_var()) return guv__dogrula(sinif);" in kp and "guv__red(401" in dg
       and "X-Acilis" in govde(ino_k, "static void guv__red("))
    ok("B72.F79 form kodlamali imzali POST 400 (WebServer govdeyi sorguya karistirir)",
       "x-www-form-urlencoded" in dg and "400" in dg)
    # 4B (PC8): eski F81c "/kopru (CORS kokeni kaydi) zorunlulukta imzasiz REDDEDILIR" KALKTI —
    # uc yok (kopru sunucu tarafinda vekil, CORS gereksiz; sim3_web 2d/4a). Kalkan ucun
    # isleyicisi, kaydi ve CORS on-ucusu geri gelmesin:
    ok("B72.F81c (4B PC8) /kopru ucu, kopru adresi ve CORS on-ucus isleyicisi YOK; /akis bir "
       "kopru kaydina bakmaz",
       "kopru_sayfa" not in ino_k and "kopru_adres" not in ino_k and "onuc_sayfa" not in ino_k
       and "HTTP_OPTIONS" not in ino_k and "Access-Control-Allow" not in ino_k
       and "kopru" not in govde(ino_k, "void akis_sayfa("))
    i_n = ino_k.find("if (alt == 0 || alt == '?') {")
    ns = ino_k[i_n:ino_k.find("if (alt == 'a')", i_n)] if i_n >= 0 else ""
    ok("B72.F91 N? AP parolasini YALNIZ ham UART'a basar (Serial aynasi /akis'e tasiyordu: "
       "ag dinleyen AP parolasini goruyordu) — 4B: tek yazimli ap_parolasi_bas uzerinden",
       bool(ns) and "ap_parolasi_bas(" in ns and 'ap_sifre' not in ns
       and not re.search(r'Serial\.print(ln)?\(ag_nvs\.getString\("ap_sifre"', ns))
    ok("B72.F81b misafir izleme yalniz IZLEME sinifini acar",
       "sinif == GUV_IZLEME && guv.ayar.misafir" in kp and kp.count("misafir") == 1)
    atla = [s for s in dg.splitlines() if "continue" in s]
    ok("B72.F86 /akis imzasi _c _s _i sorgu argumanlarindan okunur; bu uc ve ham govde (plain) "
       "kanonik dongude ATLANIR (atlama satirinin kendisi denetlenir)",
       len(atla) == 1 and all(f'a == "{a}"' in atla[0] for a in ("_c", "_s", "_i", "plain"))
       and all(f'sunucu.arg("{a}")' in dg for a in ("_c", "_s", "_i")))
    i_bas, i_bit = dg.find("guv_imza_bas("), dg.find("guv_imza_bit(")
    ok("B72.F89 guv_imza_bas basariliysa guv_imza_bit HER ZAMAN cagrilir (mbedTLS baglami "
       "serbest kalir; arada return yok)",
       0 <= i_bas < i_bit and "return" not in dg[dg.find("if (!r) {", i_bas):i_bit])

    st = govde(ino_k, "void saat_sayfa(")
    ok("B72.F80 /saat yalniz NTP saati YOKKEN ayarlar; 1 700 000 000 alti ret",
       0 <= st.find("guv_saat_ntp") < st.find("settimeofday") and "1700000000" in st)
    ok("B72.F83 mbedTLS baglami GUV_CTX_BOYU'na sigar (derleme denetimi); SHA-256; PBKDF2 "
       "cekirdekte (guv_pbkdf2) ve tablonun nefesi zamanlayiciya pay verir",
       "static_assert(sizeof(GuvMbedCtx) <= GUV_CTX_BOYU" in esp_k
       and "MBEDTLS_MD_SHA256" in govde(esp_k, "static int gm__kur(")
       and "gm_nefes" in esp_k[esp_k.find("static const GuvKripto guv_kripto"):]
       and "vTaskDelay(" in govde(esp_k, "static void gm_nefes("))
    eg = govde(gh_k, "guv__esit(")
    ok("B72.F84 sabit zamanli karsilastirma: dongude erken cikis yok (XOR birikimi, tek return)",
       "f |=" in eg and eg.count("return") == 1)
    i_ns = ino_k.find('ag_nvs.putString("web_sifre"')
    ok("B72.F85 Ns (parola degisti) P onbellegini siler ve eski cihazlar icin Ex! der",
       i_ns >= 0 and "guv_parola_degisti(" in ino_k[i_ns:i_ns + 600]
       and "Ex!" in ino_k[i_ns:i_ns + 600])
    ok("B72.F87 uretim kodunda GUV_SINAMA YOK; guvenlik_esp.h Serial aynasindan ONCE dahil ve "
       "Serial kullanmiyor (cekirdek 0)",
       "GUV_SINAMA" not in esp_k + ino_k and "Serial" not in esp_k
       and 0 <= ino_k.find('#include "guvenlik_esp.h"') < ino_k.find("#define Serial CIKIS"))
    # ── 1D son inceleme duzeltmeleri ──
    ok("B72.F92 mbedTLS donus kodlari DENETLENIR: md_setup/hmac_starts hatasi bas'tan -1, ekle "
       "hatasi baglamda saklanir ve bit -1 doner (karar yigindaki eski MAC'e dayanmaz)",
       "int hata;" in esp_k and "mbedtls_md_setup(" in govde(esp_k, "static int gm__kur(")
       and "!= 0" in govde(esp_k, "static int gm__kur(")
       and "if (gm__kur(c, 1) != 0) return -1;" in govde(esp_k, "static int gm_hmac_bas(")
       and esp_k.count("mbedtls_md_setup(") == 1
       and "c->hata" in govde(esp_k, "static void gm_hmac_ekle(")
       and "c->hata" in govde(esp_k, "static int gm_hmac_bit(")
       and "mbedtls_pkcs5" not in esp_k)
    tg = sk[sk.find("case 't':"):sk.find("case 'r':")]
    rg = sk[sk.find("case 'r':"):sk.find("default:")]
    ok("B72.F93 Et/Er SINIRLI (Et 1000..GUV_TUR_EN_COK, Er GUV_TUR_EN_AZ..GUV_TUR_EN_COK) ve pil "
       "testi surerken REDDEDILIR (cekirdek 1 = olcum dongusu)",
       "GUV_TUR_EN_COK" in tg and "pil_testi_suruyor()" in tg
       and "GUV_TUR_EN_AZ" in rg and "GUV_TUR_EN_COK" in rg and "pil_testi_suruyor()" in rg)
    gi = govde(ino_k, "static void guv_isle(")
    ok("B72.F96 P cekirdek 1'de (guv_isle) hesaplanir; eslestirme uclari PBKDF2 YAPMAZ ve web "
       "parolasini OKUMAZ; Ns/Er sonrasi P yeniden",
       "guv_p_hesapla(" in gi and "pil_testi_suruyor()" in gi
       and all("web_sifre" not in govde(ino_k, f"void {u}(") and "pbkdf2" not in govde(ino_k, f"void {u}(")
               for u in ("eslestir_baslat_sayfa", "eslestir_kanit_sayfa"))
       and ino_k.count("guv_p_eski = 1") >= 3)
    yw = govde(ino_k, "static int web_yetki(")
    ok("B72.F95 eski Basic-Auth yolu da deneme sinirli: yanlis parola 2^k s bekletir (429), dogru "
       "sifirlar; YALNIZ Authorization basligi varken sayilir",
       "web_serbest_ms" in yw and 'hasHeader("Authorization")' in yw and "429" in kg
       and "web_yetki()" in kg and "web_yetkili()" not in ino_k)
    i_ag, i_guv = ino_k.find("ag_baslat_rf();"), ino_k.find("guv_esp_ac();")   # 1E-2: radyo setup'ta acilir
    pg = sk[sk.find("case 'p':"):sk.find("case 'z':")]
    ok("B72.F97 rastgele sayilar RF acikken: guv_esp_ac ag kurulduktan SONRA; Ep WiFi kapaliyken "
       "REDDEDILIR (RF'siz RNG yalanci-rastgele)",
       0 <= i_ag < i_guv and "WiFi.getMode()" in pg)
    # ── 1D kart tezgahi (2026-10-01) bulgulari ──
    zg = sk[sk.find("case 'z':"):sk.find("case 't':")]
    ok("B72.F98 (kart tezgahi: her Ez/Em cekirdek 1'i P hesabiyla 4.7 s donduruyordu, ardindan "
       "gelen seri komutlar bekliyordu) Ez/Em P'yi YALNIZ ayar bozukken (tuz yeniden uretildi) "
       "yeniden hesaplatir",
       "ayar_bozuk" in zg and re.search(r"if \(\w+\)\s*guv_p_eski = 1;", zg) is not None
       and zg.count("guv_p_eski = 1") == 1)
    ok("B72.F99 (kart tezgahi: 85 us/tur, her turda HMAC kurulumu + bellek ayirma) kartin SHA'si "
       "mbedtls_sha256 (bellek ayirmasiz, KOPYALANABILIR), tabloda sha_kopya; varsayilan tur "
       "20 000 (kartta < 1 s, tezgah olcer: 25 000 = 956 ms, pay yetersiz)",
       "mbedtls_sha256_clone(" in govde(esp_k, "static int gm_sha_kopya(")
       and "gm_sha_kopya" in esp_k[esp_k.find("static const GuvKripto guv_kripto"):]
       and "mbedtls_md_" not in govde(esp_k, "static int gm_sha_bas(")
       and re.search(r"#define GUV_TUR_VARSAYILAN\s+20000UL", gh_k) is not None)
    ok("B72.F100 Et SABIT sinama parolasiyla olcer (gercek parola DEGIL) ve P'nin ilk 8 baytini "
       "basar: tezgah kartin PBKDF2'sini Python hashlib ile karsilastirir",
       '"olcum-tur-olcumu-1D"' in tg and "web_sifre" not in tg and '"ET %lu %lu %s"' in tg)
    toplanan =re.search(r"toplanacak\[\]\s*=\s*\{([^}]*)\}", ino_k)
    tz = _oku_tezgah = (BURASI / "tezgah_kayit.py").read_text(encoding="utf-8")
    tg2 = tz[tz.find("def guvenlik("):tz.find("\ndef esit(")]
    fin = tg2[tg2.rfind("finally:"):]
    ok("B72.F94 tezgah --guvenlik yarida kalsa da karti GERI ALIR: Em0, Ez0 ve test cihazinin "
       "silinmesi finally blogunda",
       "finally:" in tg2 and all(x in fin for x in ('"Em0"', '"Ez0"', '"Ex')))
    ok("B72.F101 (kart tezgahi: olcum.local cozumu ~3 s) tezgah Ep'yi SSE dinleyicisi BAGLANDIKTAN "
       "sonra gonderir; baglanmamissa 'anahtar SSE'de yok' denetimi KIRMIZI (bos yere gecmez)",
       0 <= tg2.find("bagli = ") < tg2.find("IM.esles_usb(") and "bagli and c.n" in tg2)
    # 4B (PC8): eski ek kosul "ve CORS on ucu (onuc_sayfa) X-Cihaz'a izin veriyor" KALKTI —
    # capraz koken izni hic verilmiyor (kopru sunucu tarafinda vekil; F81c, sim3_web 4a).
    ok("B72.F88 imza basliklari toplaniyor (X-Cihaz, X-Sayac, X-Imza, Content-Type)",
       toplanan is not None and all(f'"{b}"' in toplanan.group(1)
                                    for b in ("X-Cihaz", "X-Sayac", "X-Imza", "Content-Type")))


class _SahteSeri:
    """1D esles_usb icin USB seri sahtesi: E? ve Ep<ad> yanitlari."""

    def __init__(self, K: bytes, n: int = 3, kimlik: str = "0011223344556677"):
        self.K, self.n, self.kimlik = K, n, kimlik
        self.yazilan: list[str] = []
        self.kuyruk: list[str] = ["D 1.7 0 0 0 0 1 2 0 3"]

    def yaz(self, s: str) -> None:
        self.yazilan.append(s)
        if s.startswith("E?"):
            self.kuyruk.append(f"E zorunlu=0 misafir=0 tur=50000 kimlik={self.kimlik} saat=0 cihaz=2")
        elif s.startswith("Ep"):
            self.kuyruk += ["D 1.7 0 0 0 0 1 2 0 3", f"EK {self.n} {self.K.hex()}",
                            f"* E: USB'den cihaz {self.n} eklendi"]

    def satir_oku(self, zaman_asimi: float = 0.5):
        return self.kuyruk.pop(0) if self.kuyruk else None


def bolum_guvenlik_istemci() -> None:
    """1D T4: PC istemcisi (kopru/imza.py) sahte karta karsi; sahte kartin imza
    dogrulayicisi BAGIMSIZ (spec bicimi hmac ile yeniden yazilmis)."""
    print("\n── B72.I  1D PC istemcisi: eslestirme · imzali esitleme · yeniden esitleme · saklama")
    import imza as IM
    kay = _kayitlar(30)
    kart = _SahteKart(kay)
    sunucu, taban = _sunucu(kart)
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            # E25 parolali eslestirme: parola, P ve K agda YOK; yanlis parola ve sahte kart kaniti kaydetmez
            kart.kart_kanit_boz = True
            try:
                IM.esles(taban, "PC ğ", kart.parola, dizin=d / "c")
                sahte = False
            except Exception as e:                       # noqa: BLE001
                sahte = "kart" in str(e).lower()
            dosyasiz_1 = not list((d / "c").glob("*.json")) if (d / "c").exists() else True
            kart.kart_kanit_boz = False
            try:
                IM.esles(taban, "PC", "yanlis-parola-99", dizin=d / "c")
                yanlis = False
            except Exception:                            # noqa: BLE001
                yanlis = True
            dosyasiz_2 = not list((d / "c").glob("*.json")) if (d / "c").exists() else True
            # sahte kanitli deneme SAHTE KARTTA cihaz birakti (gercek sahte kart parolayi
            # bilmez, birakamaz); istemci HICBIR SEY kaydetmedi (dosyasiz_1) — listeyi temizle
            kart.cihazlar.clear()
            kart.istekler.clear()
            c = IM.esles(taban, "PC ğ", kart.parola, dizin=d / "c")
            trafik = "\n".join(kart.istekler)
            import hashlib as _hs
            P = _hs.pbkdf2_hmac("sha256", kart.parola.encode(), kart.tuz, kart.tur, 32)
            ok("B72.I5 parolali eslestirme: dogru parola -> cihaz; trafikte parola, P ve K YOK; "
               "yanlis parola ve SAHTE kart kaniti (karsilikli dogrulama) cihaz KAYDETMEZ",
               c.n == 1 and c.K == kart.cihazlar[1] and kart.parola not in trafik
               and P.hex() not in trafik and c.K.hex() not in trafik and sahte and yanlis
               and dosyasiz_1 and dosyasiz_2,
               f"n={c.n} sahte={sahte} yanlis={yanlis}")

            # E20 imzali esitleme: zorunlu kartta imzali gecer, imzasiz 401
            kart.imza_zorunlu = True
            kart.imzali = 0
            es = _es(taban, d / "e", onay=KE.imzali_onay(c, taban), cihaz=c)
            r = es.esitle()
            imzasiz_red = False
            try:
                _es(taban, d / "e2").esitle()
            except Exception:                            # noqa: BLE001
                imzasiz_red = True
            ok("B72.I0 eslesmis Esitleyici /kayit/veri ve Go onayini IMZALAR (zorunlu sahte kart "
               "kabul eder); eslesmemis olan 401 alir",
               (d / "e" / KE.DOSYA).read_bytes() == b"".join(kay) and kart.onay == 30
               and kart.imzali >= 2 and imzasiz_red, f"{r} imzali={kart.imzali} onay={kart.onay}")

            # E21 kart yeniden basladi (acilis degisti): BIR KEZ esitlenir, dongu yok
            kart.acilis = "22" * 16
            kart.ret_401 = 0
            kart.kayitlar = kay + _kayitlar(5, 31)
            r2 = es.esitle()
            bir_kez = kart.ret_401 == 1
            kart.cihazlar.pop(c.n)                       # cihaz silindi: 401, acilis AYNI
            kart.ret_401 = 0
            kart.kayitlar = kart.kayitlar + _kayitlar(2, 36)
            sonsuz_yok = False
            try:
                es.esitle()
            except Exception:                            # noqa: BLE001
                sonsuz_yok = kart.ret_401 <= 2
            kart.cihazlar[c.n] = c.K
            ok("B72.I1 (Review Focus 2) yeni acilis: istemci 401 + X-Acilis ile BIR KEZ esitlenir ve "
               "basarir; acilis ayniyken 401 (cihaz silindi) dongu yapmaz, hata verir",
               bir_kez and r2.get("yeni_kayit", 0) == 5 and c.acilis == "22" * 16 and sonsuz_yok,
               f"ret={kart.ret_401} r2={r2} acilis={c.acilis[:4]}")

            # E22 sayac diskte kalici ve tekdüze
            s1 = c.sayac
            c2 = IM.Cihaz.yukle(c.dosya)
            import time as _t
            gercek = _t.time
            try:
                _t.time = lambda: 1.0                    # saat geri gitti
                s2 = c2.sonraki_sayac()
            finally:
                _t.time = gercek
            ok("B72.I2 sayac diskte kalici: yeni nesne eskisinin altina inmez, saat geri gitse de artar",
               s1 > 0 and s2 > s1, f"{s1} -> {s2}")

            # E23 eslesmemis Esitleyici bugunku yolu kullanir (imza basligi YOK)
            kart.imza_zorunlu = False
            kart.istekler.clear()
            kart.kayitlar = kay
            _es(taban, d / "e3", onay=KE.http_onay(taban)).esitle()
            ok("B72.I3 (regresyon) eslesmemis Esitleyici imza basligi YOLLAMAZ; jetonlu onay calisir",
               kart.istekler and not any("X-Imza" in s for s in kart.istekler)
               and any("X-Jeton" in s for s in kart.istekler), str(len(kart.istekler)))

            # E24 anahtar diskte duz durmaz (Windows: DPAPI)
            metin = c.dosya.read_text(encoding="utf-8")
            if sys.platform == "win32":
                ok("B72.I4 anahtar dosyada DUZ DEGIL (DPAPI); geri yuklenen K ayni",
                   c.K.hex() not in metin and '"K_dpapi"' in metin
                   and IM.Cihaz.yukle(c.dosya).K == c.K)
            else:
                ok("B72.I4 (Windows disi: DPAPI yok) dosya izni 600 ve uyari alani",
                   (c.dosya.stat().st_mode & 0o077) == 0 and '"K_duz"' in metin)

            # E26 USB eslestirmesi: E? ile kimlik, Ep ile EK satiri
            Ku = bytes(range(100, 132))
            seri = _SahteSeri(Ku, n=3)
            cu = IM.esles_usb(seri, "Laptop", dizin=d / "u")
            ok("B72.I6 USB eslestirmesi: E? kimligi + Ep<ad> -> EK satirindan K ve numara; "
               "diske kaydedilir",
               cu.n == 3 and cu.K == Ku and cu.kimlik == "0011223344556677"
               and any(s.startswith("Ep") and "Laptop" in s for s in seri.yazilan)
               and IM.Cihaz.yukle(cu.dosya).K == Ku, str(seri.yazilan))

            # E27 EventSource adresi: _c _s _i, kanonik bagimsiz hesapla dogrulanir
            u = IM.akis_url(c, taban)
            kart.imza_zorunlu = True
            import urllib.request as _ur
            with _ur.urlopen(u, timeout=5) as y:
                akis_ok = y.status == 200
            ok("B72.I7 /akis imzali adresi (_c _s _i sorguda) zorunlu kartta kabul edilir",
               akis_ok and "_i=" in u and f"_c={c.n}" in u)
            kart.imza_zorunlu = False
            # I8 (son inceleme KRITIK): sahte kart PBKDF2 maliyetini ve tuzu dayatamaz;
            # kimlik dosya adina gider; kisa parola HICBIR istek atmadan reddedilir
            kart.istekler.clear()
            sonuclar = {}
            for ad, ayar in (("tur1", {"tur": 1}), ("tur_cok", {"tur": 5_000_000}),
                             ("kimlik", {"gkimlik": "../../x"}), ("tuz", {"tuz": b"\x01"})):
                eski = (kart.tur, kart.gkimlik, kart.tuz)
                for a, v in ayar.items():
                    setattr(kart, a, v)
                try:
                    IM.esles(taban, "PC", kart.parola, dizin=d / "i8")
                    sonuclar[ad] = "KABUL"
                except (ValueError, RuntimeError) as e:
                    sonuclar[ad] = "ret"
                kart.tur, kart.gkimlik, kart.tuz = eski
            kanitsiz = not any("/eslestir/kanit" in s for s in kart.istekler)
            kart.istekler.clear()
            kisa = "ret"
            for kp in ("kisa9chr!", "onbir-krkt1"):          # K3 (kullanici onayi): en az 12
                try:
                    IM.esles(taban, "PC", kp, dizin=d / "i8")
                    kisa = "KABUL"
                except ValueError:
                    pass                                      # istek atilmadan ret
                except RuntimeError:
                    kisa = "KABUL"                            # karta GITTI (kart reddetti)
            ok("B72.I8 (son inceleme KRITIK) istemci sahte kartin dayattigi tur < 10 000 ya da asiri turu, "
               "bicimsiz kimligi (dosya adi) ve tuzu REDDEDER, kanit YOLLAMADAN; 12 karakterden kisa "
               "(9 ve 11) parola HICBIR istek atmadan reddedilir",
               all(v == "ret" for v in sonuclar.values()) and kanitsiz and kisa == "ret"
               and not kart.istekler and not (d / "i8").exists(), f"{sonuclar} kanitsiz={kanitsiz} kisa={kisa}")

            # I8b (S7): kart turu JSON TAMSAYISI, kimligi METIN olarak verir. int() gevsekligi
            # (20000.7 -> 20000, "20_000", "20000", True) ve tamsayi kimlik (str() ile 16 hane)
            # eslesmeyi YURUTMEMELI. Parola siniri kartta UTF-8 BAYT: 6 Turkce harf (12 bayt)
            # kartin kabul ettigi parola, istemci de kabul etmeli; 11 bayt istek atmadan ret.
            kart.istekler.clear()
            gevsek = {}
            for ad, ayar in (("tur_kesir", {"tur": 20000.7}), ("tur_alt_cizgi", {"tur": "20_000"}),
                             ("tur_metin", {"tur": "20000"}), ("tur_true", {"tur": True}),
                             ("kimlik_tamsayi", {"gkimlik": 1234567890123456})):
                eski = (kart.tur, kart.gkimlik, kart.tuz)
                for a, v in ayar.items():
                    setattr(kart, a, v)
                try:
                    IM.esles(taban, "PC", kart.parola, dizin=d / "i8b")
                    gevsek[ad] = "KABUL"
                except (ValueError, TypeError):
                    gevsek[ad] = "ret"
                except (RuntimeError, OSError):              # OSError: sahte kart kesirli turla coker
                    gevsek[ad] = "KARTA GITTI"
                kart.tur, kart.gkimlik, kart.tuz = eski
            kanitsiz_b = not any("/eslestir/kanit" in s for s in kart.istekler)
            kart.istekler.clear()
            try:
                IM.esles(taban, "PC", "ğğğğğ1", dizin=d / "i8b")     # 6 harf ama 11 bayt
                bayt11 = "KABUL"
            except ValueError:
                bayt11 = "ret"
            except (RuntimeError, OSError):
                bayt11 = "KARTA GITTI"
            istek11 = list(kart.istekler)
            eski_parola = kart.parola
            kart.parola = "şşşşşş"                                    # 6 harf, 12 bayt
            try:
                c12 = IM.esles(taban, "PC", "şşşşşş", dizin=d / "i8b12")
                bayt12 = "KABUL" if c12.n else "?"
            except (ValueError, RuntimeError) as e:
                bayt12 = f"ret ({e})"
            kart.parola = eski_parola
            # I8c (1D #16): kaydet() her imzali istekte cagriliyor; iki surec (kopru + esitleme)
            # ayni cihaz dosyasini kullanabilir. Ortak `.tmp` adi birinin os.replace'ini kirar.
            # Dosya fsync'lenmeden yerine konmamali (elektrik kesilirse anahtar dosyasi bos).
            import threading as _th
            ca = IM.Cihaz.yukle(c12.dosya) if bayt12 == "KABUL" else None
            yaris_hata = []

            def _yaris(cihaz):
                try:
                    for _ in range(150):
                        cihaz.sonraki_sayac()
                except Exception as e:                       # noqa: BLE001 — yaris hatasi sayilir
                    yaris_hata.append(repr(e))
            if ca is not None:
                cb = IM.Cihaz.yukle(c12.dosya)
                isler = [_th.Thread(target=_yaris, args=(x,)) for x in (ca, cb)]
                for i_ in isler:
                    i_.start()
                for i_ in isler:
                    i_.join()
            try:
                son_c = IM.Cihaz.yukle(c12.dosya)
                okunur = son_c.K == c12.K
            except Exception as e:                           # noqa: BLE001
                okunur = f"okunamadi {e!r}"
            artik = sorted(p.name for p in c12.dosya.parent.iterdir() if p != c12.dosya)
            sira = []
            _fs, _rp = os.fsync, os.replace
            os.fsync = lambda fd: (sira.append("fsync"), _fs(fd))[1]
            os.replace = lambda a, b: (sira.append("replace"), _rp(a, b))[1]
            try:
                son_c.kaydet()
            finally:
                os.fsync, os.replace = _fs, _rp
            ok("B72.I8c (1D #16) iki surec ayni cihaz dosyasini kaydederken yaris YOK (benzersiz gecici "
               "dosya), dosya okunur ve anahtar ayni, artik gecici dosya kalmaz; kaydet once fsync sonra "
               "yerine koyar",
               ca is not None and not yaris_hata and okunur is True and not artik
               and "fsync" in sira and "replace" in sira and sira.index("fsync") < sira.index("replace"),
               f"hata={yaris_hata[:2]} okunur={okunur} artik={artik[:4]} sira={sira}")

            ok("B72.I8b (S7) tur kesirli / metin / alt cizgili / True ve tamsayi kimlik kanit YOLLAMADAN "
               "reddedilir; parola siniri UTF-8 BAYT (kartla ayni): 11 baytlik 6 harf istek atmadan ret, "
               "12 baytlik 6 harf eslesir",
               all(v == "ret" for v in gevsek.values()) and kanitsiz_b and bayt11 == "ret"
               and not istek11 and bayt12 == "KABUL",
               f"{gevsek} kanitsiz={kanitsiz_b} 11B={bayt11} istek={istek11} 12B={bayt12}")

            # I9 (son inceleme): kayit_esitle komut satiri imzali yolu kullanir
            kart.imza_zorunlu = True
            kart.kayitlar = kay
            rc = KE.main(["--http", taban, "--dizin", str(d / "cli"), "--cihaz", str(c.dosya)])
            rc2 = KE.main(["--http", taban, "--dizin", str(d / "cli2"), "--cihaz-dizin", str(c.dosya.parent)])
            kart.imza_zorunlu = False
            ok("B72.I9 kayit_esitle komut satiri eslesmis cihazla IMZALI esitler (--cihaz ya da "
               "--cihaz-dizin'de kart kimligine uyan dosya); zorunlu sahte kart kabul eder",
               rc == 0 and rc2 == 0 and (d / "cli" / KE.DOSYA).exists()
               and (d / "cli2" / KE.DOSYA).exists(), f"rc={rc} rc2={rc2}")
    finally:
        sunucu.shutdown()


def bolum_bildirim_kart() -> None:
    """1E: MQTT bildirimlerinin karta baglanmasi (bildirim_esp.h + .ino). Platformsuz
    cekirdek B71.Q / B71.M'de; PC tarafi (ChaCha20-Poly1305, MQTT, sahte araci)
    test_bildirim.py'de — burada alt surec olarak kosar."""
    print("\n── B72.Q1+  1E kart: gorev cekirdegi · vasiyet · USB'ye ozel Q · sir basilmaz")
    be, ino, ke, ko = (_oku("bildirim_esp.h"), _oku("olcum-karti-a3.ino"), _oku("kayit_esp.h"),
                       _oku("kayit_oturum.h"))
    be_k, ino_k, ke_k, ko_k = kod(be), kod(ino), kod(ke), kod(ko)
    bg = govde(be_k, "static void bildirim_baslat(")
    ok("B72.Q1 bildirim gorevi CEKIRDEK 0'a SABIT (xTaskCreatePinnedToCore(..., 0)); esp-mqtt "
       "YOK (3.3.11'de gorevi sabitlenmiyor: TLS el sikismasi olcum cekirdegine kayardi)",
       re.search(r"xTaskCreatePinnedToCore\(\s*bildirim_gorevi\s*,.*,\s*0\s*\)\s*;", bg) is not None
       and "mqtt_client.h" not in be_k + ino_k and "esp_mqtt_client" not in be_k + ino_k)
    bb = govde(be_k, "static int bld__baglan(")
    ok("B72.Q2 CONNECT: keepalive 5 s (K8), vasiyet durum konusunda QoS 1 + retained, vasiyet "
       "HER baglanista yeniden sifrelenir (yeni nonce, K6), temiz oturum",
       re.search(r"#define BLD_KEEPALIVE_S\s+5u", be_k) is not None
       and "m.keepalive = BLD_KEEPALIVE_S;" in bb and "m.vasiyet_qos = 1;" in bb
       and "m.vasiyet_tut = 1;" in bb and "m.vasiyet_konu = b->konu_durum;" in bb
       and 0 <= bb.find("bld_vasiyet_json(") < bb.find("bld__zarfla(") < bb.find("mqp_baglan(")
       and "m.temiz = 1;" in bb)
    ok("B72.Q3 TLS dogrulamasi CA demetiyle (esp_crt_bundle_attach); dogrulamayi gevseten "
       "bayrak YOK; duz TCP yalniz mqtt:// ile (yerel sinama)",
       "cfg.crt_bundle_attach = esp_crt_bundle_attach;" in bb and "skip_common_name" not in be_k
       and re.search(r"if\s*\(tls\)\s*cfg\.crt_bundle_attach.*?else\s+cfg\.is_plain_tcp\s*=\s*true;",
                     bb, re.S) is not None)
    gor = govde(be_k, "static void bildirim_gorevi(")
    ok("B72.Q4 yalniz STA kipinde baglanir (K8; AP kipinde MQTT yok); baglaninca durum ZORLA "
       "yayinlanir (retained vasiyetin ustune c:1)",
       "ag_durum.kip == AG_STA" in gor
       and gor.find("bld__baglan(") < gor.find("durum_zorla = 1;") < gor.find("bld_durum_json("))
    gl = govde(be_k, "static int bld__gelen(")
    ok("B72.Q5 olay kuyruktan YALNIZ eslesen PUBACK ile duser (yayin aninda degil); ayni anda "
       "tek olay ucusta; onaysiz olay baglantiyi yeniler (yeniden gonderilir, `n` ayiklar)",
       "bld_kuyruk_at(" not in gor and "bld_kuyruk_at(" in gl
       and "mqp_puback_pid(&b->ok) == (int32_t)b->ucusta" in gl
       and "!b->ucusta && bld_kuyruk_adet(&bld)" in gor and "BLDH_PUBACK" in gor)
    pm = re.search(r"#define BLD_PING_MS\s+(\d+)UL", be_k)
    pr = re.search(r"#define BLD_PINGRESP_MS\s+(\d+)UL", be_k)
    ok("B72.Q6 canlilik: PINGREQ keepalive'dan ONCE (4 s < 5 s); PINGRESP gelmezse baglanti olu "
       "(olu agi kart en gec ~9 s'de fark eder)",
       bool(pm and pr) and int(pm.group(1)) < 5000 and int(pr.group(1)) <= 5000
       and "BLDH_PING" in gor)
    kp = govde(be_k, "static void bld__kapat(")
    ok("B72.Q7 nazik kapanis (Q0 / ayar degisimi) DISCONNECT'ten ONCE c:0 yayinlar — araci nazik "
       "kopuista vasiyeti yayinlamaz, 'cevrimici' durum asili kalmasin",
       0 <= kp.find("bld_vasiyet_json(") < kp.find("mqp_kopar("))
    kg = govde(ino_k, "void komut_sayfa(")
    i_q = kg.find("k[0] == 'Q'")
    ok("B72.Q8 /komut 'Q' ile baslayan komutu 403 ile REDDEDER (araci parolalari aga cikmaz, K9)",
       0 <= i_q < kg.find("komut_kuyruga(") and "403" in kg[i_q:i_q + 200]
       and "case 'Q': bld_seri_komut(s); break;" in ino_k)
    sk = govde(ino_k, "static void bld_seri_komut(")
    oz = re.search(r"typedef struct \{([^{}]*)\} BildirimOzet;", be_k)
    ok("B72.Q9 Q komutlari SIR BASMAZ (Serial aynasi /akis'a tasir): ozet yapisinda parola/anahtar "
       "alani yok (yalniz var/yok), komut metni geri yansitilmaz, seri isleyici ayari kendisi okumaz",
       bool(oz) and not re.search(r"\b(kp|cp|anahtar)\s*\[", oz.group(1))
       and "kp_var" in oz.group(1) and "bld__ayar_oku" not in sk
       and not re.search(r"(Serial\.\w+|snprintf)\([^;]*s \+ 2", sk))
    ok("B72.Q10 bildirim_esp.h'de Serial YOK (kayit_esp.h gibi: aynayi atlar, cekirdek 0 yaris)",
       not re.search(r"\bSerial\b", be_k))
    bil = govde(be_k, "static int bildirim_bilgi_zarf(")
    ok("B72.Q11 /bildirim/bilgi yaniti CIHAZ anahtariyla sifreli, AAD kimlik + cihaz no'ya bagli "
       "('OK1-bildirim\\n<kimlik>\\n<n>'), nonce RF rastgelesi; ayar eksikse -1 (404)",
       'snprintf(aad, sizeof(aad), "OK1-bildirim\\n%s\\n%u", kimlik, (unsigned)n);' in bil
       and "esp_fill_random(cikti + 4, 12);" in bil and "bld__aead(K," in bil
       and "int r = -1;" in bil)
    q1 = sk[sk.find("case '1':"):sk.find("case '0':")]
    ok("B72.Q12 onek + bildirim anahtari YALNIZ RF acikken uretilir (Ep gibi: RF'siz RNG zayif)",
       q1.find("WIFI_MODE_NULL") < q1.find("bildirim_sir_uret(") and "WIFI_MODE_NULL" in q1)
    # tam imza: "#define KY_BITIR_KANCA" oneki KY_BITIR_KANCA_ESKI gibi yanlis adi da
    # kabul ediyordu (mutasyon kosusu yakaladi) — o zaman bos varsayilan devreye girer
    ik = ke_k.find("#define KY_BITIR_KANCA(y, sebep)")
    ok("B72.Q13 oturum-kapandi kancasi kayit_oturum.h'DEN ONCE tanimli (sonra tanimlansa bos "
       "varsayilan SESSIZCE kullanilirdi) ve iki BITIR yerinde de cagriliyor (ky_bitir, ky__dolu)",
       0 <= ik < ke_k.find('#include "kayit_nokta.h"') and ik < ke_k.find('#include "kayit_yonet.h"')
       and "KY_BITIR_KANCA(y, sebep);" in govde(ko_k, "static inline int ky_bitir(")
       and "KY_BITIR_KANCA(y, KB_SEBEP_DOLU);" in govde(ko_k, "static inline int ky__dolu("))
    pd = govde(ino_k, "static void pil_durdur(")
    pb = govde(be_k, "static void bildirim_pil_bitti(")
    ok("B72.Q14 pil bitisi kayitsiz testte de bildirilir; cekirdek 1'deki kanca yalniz kisa "
       "kritik bolge (NVS / ag / bekleme YOK)",
       "bildirim_pil_bitti(" in pd and pd.find("pil_yuk(false)") < pd.find("bildirim_pil_bitti(")
       and "portENTER_CRITICAL(&bld_mux);" in pb
       and not re.search(r"Preferences|esp_tls|vTaskDelay|xQueue", pb))
    ok("B72.Q17 Qt istekleri BIRLESMEZ: cekirdek 1 istek sayacini, gorev islenen sayacini birer "
       "artirir (bayrak arka arkaya iki Qt'yi tek olay yapiyordu — kart tezgahi 2026-10-01)",
       "while (bld_deneme_islenen != bld_deneme_istek) {" in gor
       and "bld_deneme_islenen = (uint8_t)(bld_deneme_islenen + 1u);" in gor
       and "bld_deneme_istek = (uint8_t)(bld_deneme_istek + 1u);" in sk)

    # PC tarafi (saf Python ChaCha20-Poly1305, MQTT istemcisi, sahte araci) — alt surec.
    # ~15 s; B72'nin her mutasyonu bunu yeniden kosmasin diye GIRDILERININ ozetiyle
    # onbellekli: yalniz GECEN kosu saklanir, kopru/*.py ya da testin kendisi degisirse
    # (o dosyalarin mutasyonu dahil) yeniden kosar.
    girdi = [KOK / "kopru" / a for a in ("chacha.py", "mqtt_istemci.py", "bildirim.py",
                                        "sahte_araci.py", "imza.py",
                                        # 4E: PC bildirimleri de test_bildirim.py'de sinaniyor
                                        "pc_bildirim.py", "windows_bildirim.py", "bildirim_metin.py",
                                        "kart_wifi.py", "pc_ayar.py")]
    girdi += [KOK / "ortak" / "src" / "sozluk.js", KOK / "kod" / "olcum-karti-a3" / "bildirim.h"]
    girdi.append(Path(__file__).with_name("test_bildirim.py"))
    oz = hashlib.sha256(b"".join(p.read_bytes() if p.exists() else b"-" for p in girdi)).hexdigest()
    onb = Path(tempfile.gettempdir()) / f"ok_test_bildirim_{oz[:32]}.gecti"
    if onb.exists():
        ok("B72.Q16 test_bildirim.py yesil (girdileri degismedi: onbellekteki GECEN kosu)", True,
           onb.read_text(encoding="utf-8"))
    else:
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("test_bildirim.py"))],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=600)
        m = re.findall(r"(\d+)/(\d+) dogrulama gecti", r.stdout)
        gec = r.returncode == 0 and bool(m) and m[-1][0] == m[-1][1]
        ok("B72.Q16 test_bildirim.py (RFC 8439 vektorleri, zarf, bilgi_coz, MQTT istemcisi + "
           "sahte araci) yesil", gec, (m[-1][0] + "/" + m[-1][1]) if m else r.stdout[-300:])
        if gec:
            onb.write_text(f"{m[-1][0]}/{m[-1][1]}", encoding="utf-8")


# ── B72.W · 4B kopru WiFi: eslesmis cihaz olarak imzali /akis + /komut ─────────
def _wifi_oku(w, n: int, sure: float = 6.0) -> list:
    """WifiKart'tan n satir (ya da sure dolana dek)."""
    son, al = time.monotonic() + sure, []
    while len(al) < n and time.monotonic() < son:
        x = w.satir_oku(0.1)
        if x is not None:
            al.append(x)
    return al


def _bekle_kosul(kosul, sure: float = 6.0) -> bool:
    son = time.monotonic() + sure
    while time.monotonic() < son:
        if kosul():
            return True
        time.sleep(0.02)
    return kosul()


def bolum_kopru_wifi() -> None:
    """4B (PC5-PC7, D5 #17/#18): kopru kartla WiFi'den ESLESMIS CIHAZ olarak konusur.
    Sahte kartin imza dogrulayicisi BAGIMSIZ (spec bicimi hmac ile yeniden yazilmis)."""
    print("\n── B72.W  4B kopru WiFi: imzali /akis (her baglantida YENI adres) · imzali /komut · "
          "p0 imzasiz · kart kimligi · /saat · PC5 cihaz dizini")
    import imza as IM
    import kart_wifi as KW
    import kopru as KO
    kart = _SahteKart([])
    sunucu, taban = _sunucu(kart)
    eski_ortam = {a: os.environ.get(a) for a in ("OLCUM_PC_DIZIN", "OLCUM_CIHAZ_DIZIN", "LOCALAPPDATA",
                                                    "OLCUM_PAROLA")}
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cdiz = d / "cihaz"
            c = IM.esles(taban, "kopru", kart.parola, dizin=cdiz)

            def yeni(**kw):
                bekl = []
                w = KW.WifiKart(taban, dizin=cdiz,
                                bekle=lambda sn, _b=bekl: (_b.append(sn), time.sleep(0.02)), **kw)
                durum = []
                w.bildir = durum.append
                return w, bekl, durum

            # W1 akis satirlari BIREBIR; SSE cercevesi (kimlik, id, retry, kalp) tasinmaz
            kart.akis_satirlari = ["D 12.3456 0.891234 10.99881 1234.5678 0.3429355 3600000 133 0",
                                   "K 420 1503 0", "* enerji sifirlandi", "S2 1000 671 0.028787 500 5000 0 1 63.5"]
            kart.akis_tut = 0.3
            kart.istekler.clear()
            w, bekl, durum = yeni()
            w.ac()
            al = _wifi_oku(w, 4)
            w.kapat()
            ok("B72.W1 WiFi yukari-akisi kartin /akis satirlarini BIREBIR ve sirayla verir; kimlik/id/"
               "retry/kalp cercevesi satir sayilmaz; baglanti durumu `* kopru: WiFi baglandi` olarak "
               "bildir'e (akisa/arsive DEGIL) gider",
               al == kart.akis_satirlari and any(x.startswith("* kopru: WiFi baglandi") for x in durum)
               and not any("jeton" in x or x.startswith(("id:", "retry", ":")) for x in al),
               f"{al} | {durum[:3]}")

            # W2 (D5 #17) her yeniden baglanmada YENI imzali adres; tekrar (401) yok; veri gelince bekleme 1 s
            kart.akis_tut = 0.0
            kart.ret_401 = 0
            kart.istekler.clear()
            once = kart.akis_sayisi
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: kart.akis_sayisi - once >= 4)
            w.kapat()
            akislar = [x.split()[1] for x in kart.istekler if x.split()[1].startswith("/akis?")]
            sayaclar = [dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(a).query)).get("_s") for a in akislar]
            ok("B72.W2 (D5 #17) imzali /akis adresi tek kullanimlik: her yeniden baglanmada YENI adres "
               "(farkli sayac/imza), kart hicbirini tekrar diye reddetmez; veri gelen baglantidan sonra "
               "bekleme 1 s'ye doner",
               len(akislar) >= 4 and len(set(akislar)) == len(akislar) and len(set(sayaclar)) == len(sayaclar)
               and kart.ret_401 == 0 and bekl and all(b == 1.0 for b in bekl[:3]),
               f"{len(akislar)} akis, 401={kart.ret_401}, bekleme={bekl[:5]}")

            # W2b veri gelmeyen baglanti: bekleme ARTAR (1, 2, 4, 8, 16, 30 s) ve 30'da durur
            kart.akis_satirlari = []
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: len(bekl) >= 7)
            w.kapat()
            ok("B72.W2b veri gelmeyen (hemen kapanan) baglantilarda yeniden baglanma beklemesi ARTAR "
               "(1, 2, 4, 8, 16, 30 s) ve 30 s'de durur — kartin seri web cekirdegi istek firtinasina "
               "bogulmaz", bekl[:7] == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0], str(bekl[:8]))

            # W3 (D5 #18) kart kimligi cihaz dosyasina uymuyor: akis YOK, komut YOK, p0 VAR
            kart.akis_satirlari = ["D 1.0"]
            dogru_kimlik = kart.gkimlik
            kart.gkimlik = "8899aabbccddeeff"
            kart.istekler.clear()
            kart.komutlar.clear()
            kart.komut_imzali.clear()
            w, bekl, durum = yeni(cihaz_dosyasi=c.dosya)
            w.ac()
            _bekle_kosul(lambda: any("DEGIL" in x for x in durum))
            try:
                w.yaz("A?")
                komut_red = ""
            except RuntimeError as e:
                komut_red = str(e)
            w.yaz("p0")
            w.kapat()
            akis_gitti = any(x.split()[1].startswith("/akis") for x in kart.istekler)
            ok("B72.W3 (D5 #18) kartin kimligi cihaz dosyasina UYMUYORSA kopru /akis ACMAZ ve komut "
               "GONDERMEZ (acik mesaj: hangi kimlik, hangi dosya); p0 (DURDUR) yine de imzasiz gider",
               not akis_gitti and "dogrulanmadi" in komut_red and kart.komutlar == ["p0"]
               and kart.komut_imzali == [("p0", False)]
               and any("8899aabbccddeeff" in x and c.kimlik in x and "DEGIL" in x for x in durum),
               f"akis={akis_gitti} red={komut_red[:60]!r} komut={kart.komut_imzali} durum={durum[-1:]}")
            # W3b dizinden secimde bu kart icin cihaz dosyasi yok
            kart.istekler.clear()
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: any("ESLESMEMIS" in x for x in durum))
            w.kapat()
            ok("B72.W3b bu kartla eslesmis cihaz dosyasi yoksa /akis ACILMAZ; mesaj eslestirme komutunu "
               "soyler (imza.py esles)",
               not any(x.split()[1].startswith("/akis") for x in kart.istekler)
               and any("ESLESMEMIS" in x and "imza.py esles" in x for x in durum), str(durum[-1:]))
            kart.gkimlik = dogru_kimlik

            # W4 komutlar IMZALI (jeton/parola yok); p0 imzasiz ve X-Olcum'lu
            kart.akis_tut = 2.0
            kart.akis_bitir.clear()
            kart.komutlar.clear()
            kart.komut_imzali.clear()
            kart.istekler.clear()
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: w.bagli)
            w.yaz("A?")
            w.yaz("p0")
            kart.akis_bitir.set()
            w.kapat()
            kom = [x for x in kart.istekler if x.startswith("POST /komut")]
            ok("B72.W4 WiFi'de komut IMZALI gider (X-Imza, jeton/parola yok); p0 IMZASIZ, X-Olcum'lu ve "
               "kart dogrulanmadan da gonderilebilir (O7: p0 her katmanda serbest)",
               kart.komut_imzali == [("A?", True), ("p0", False)] and len(kom) == 2
               and "X-Imza" in kom[0] and "X-Jeton" not in kom[0] and "Authorization" not in kom[0]
               and "X-Imza" not in kom[1] and "'X-Olcum': '1'" in kom[1],
               f"{kart.komut_imzali}")

            # W4b (4G) p0 canli akisin KARSI ADRESINE gider (ad cozumu yok); o adres olmezse ada duser
            kart.akis_tut = 2.0
            kart.akis_bitir.clear()
            kart.komutlar.clear()
            kart.istekler.clear()
            ad_host = "localhost:" + taban.rsplit(":", 1)[1]
            w = KW.WifiKart(ad_host, dizin=cdiz, bekle=lambda sn: time.sleep(0.02))
            w.bildir = lambda m: None
            w.ac()
            _bekle_kosul(lambda: w.bagli)
            ip_bagli = w._ip
            zaman_asimi = w._akis_soket.gettimeout() if w._akis_soket is not None else None
            w.yaz("p0")
            w._ip = ("127.0.0.1", 9)                    # kart baska IP almis gibi: kapali port
            w.yaz("p0")
            kart.akis_bitir.set()
            w.kapat()
            ip_kapali = w._ip
            hostlar = [x.split("'Host': '", 1)[1].split("'", 1)[0] for x in kart.istekler
                       if x.startswith("POST /komut") and "'Host': '" in x]
            ok("B72.W4b (4G) p0 canli akisin KARSI ADRESINE gider (Windows `olcum.local` cozumu 2.7 s "
               "surebiliyor — kartta p0 2.77 s'de ulasiyordu); o adres yanit vermezse ada geri duser; "
               "akis kapaninca adres silinir; akis soketine 40 s okuma zaman asimi GERCEKTEN uygulanir "
               "(http.client SSE yanitinda baglantinin soketini None yapiyordu: soket 10 s'de kaliyordu)",
               ip_bagli is not None and ip_bagli[0] == "127.0.0.1" and kart.komutlar == ["p0", "p0"]
               and hostlar[:1] == [taban.split("//", 1)[1]] and hostlar[1:] == [ad_host]
               and ip_kapali is None and zaman_asimi == w.okuma_zaman_asimi,
               f"zaman asimi={zaman_asimi} ip={ip_bagli} host={hostlar} komut={kart.komutlar} sonra={ip_kapali}")

            # W5 (R11) kartta NTP yoksa her baglantida BIR KEZ imzali /saat; NTP varsa hic
            kart.akis_tut = 0.0
            kart.saat_kaynak = 0
            kart.saat_istekleri.clear()
            once = kart.akis_sayisi
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: kart.akis_sayisi - once >= 3)
            w.kapat()
            simdi = time.time()
            n_bag = kart.akis_sayisi - once
            n_saat = len(kart.saat_istekleri)
            saat_ok = (n_saat in (n_bag, n_bag - 1, n_bag + 1) and n_saat >= 2
                       and all(abs(int(u) - simdi) < 30 for u in kart.saat_istekleri))
            kart.saat_kaynak = 1
            kart.saat_istekleri.clear()
            kart.istekler.clear()
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: kart.akis_sayisi - once >= n_bag + 2)
            w.kapat()
            ok("B72.W5 (R11) kartin NTP saati yoksa kopru her baglantida BIR KEZ imzali /saat verir "
               "(unix ~ simdi); NTP varsa /saat hic gonderilmez",
               saat_ok and not any("/saat" in x for x in kart.istekler),
               f"baglanti={n_bag} saat={n_saat}")
            kart.saat_kaynak = 0

            # W6 HTTPError kapatilir ve kullaniciya kodla soylenir
            kart.akis_tut = 2.0
            kart.akis_bitir.clear()
            kart.komut_red = 403
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: w.bagli)
            kapanan = []
            asil = w._ac                                 # 4J: kart istekleri WifiKart'in kendi acicisindan

            def izle(istek, timeout=None):
                try:
                    return asil(istek, timeout=timeout)
                except urllib.error.HTTPError as h:
                    eski_kapat = h.close
                    h.close = lambda _e=eski_kapat, _k=h.code: (kapanan.append(_k), _e())
                    raise
            w._ac = izle
            try:
                w.yaz("A?")
                mesaj = ""
            except RuntimeError as e:
                mesaj = str(e)
            finally:
                del w._ac
            kart.komut_red = 0
            kart.akis_bitir.set()
            w.kapat()
            ok("B72.W6 (D5 #18) kartin ret yaniti (HTTPError) KAPATILIR ve kod + govde ile soylenir",
               "403" in mesaj and "reddedildi" in mesaj and 403 in kapanan, f"{mesaj!r} kapanan={kapanan}")

            # W7 (D5 #18) imza.ac / akis_url: acilisi bilgiden alirken kimlik denetlenir; uymazsa istek YOK
            kart.gkimlik = "8899aabbccddeeff"
            kart.istekler.clear()
            c2 = IM.Cihaz(d / "yok.json", c.kimlik, c.n, c.K, c.ad, c.sayac, "")
            c2.kaydet = lambda: None
            hatalar = []
            for islev in (lambda: IM.ac(c2, taban, "POST", "/komut", [], b"A?"),
                          lambda: IM.akis_url(c2, taban)):
                try:
                    islev()
                    hatalar.append("GECTI")
                except IM.KartKimligiHatasi as e:
                    hatalar.append("kimlik" if "8899aabbccddeeff" in str(e) else str(e))
            kart.gkimlik = dogru_kimlik
            ok("B72.W7 (D5 #18) imza.ac ve akis_url kartin kimligini cihaz dosyasiyla karsilastirir "
               "(acilisi /eslestir/bilgi'den alirken); uymazsa KartKimligiHatasi, imzali istek GITMEZ",
               hatalar == ["kimlik", "kimlik"] and not any("X-Imza" in x or "_i=" in x for x in kart.istekler),
               str(hatalar))
            # W7b 401 + yeni acilis yolunda ilk HTTPError kapatilir
            kapali = []

            class _Gov(io.BytesIO):
                def close(self):
                    kapali.append(1)
                    super().close()
            yanitlar = [urllib.error.HTTPError(taban, 401, "imza", {"X-Acilis": "33" * 16}, _Gov(b"x")),
                        io.BytesIO(b"tamam")]

            def sahte_ac(istek, timeout=None):
                y = yanitlar.pop(0)
                if isinstance(y, Exception):
                    raise y
                return y
            c3 = IM.Cihaz(d / "yok3.json", c.kimlik, c.n, c.K, c.ad, 0, "11" * 16)
            c3.kaydet = lambda: None
            IM.ac(c3, taban, "GET", "/kayit/liste", acici=sahte_ac)
            ok("B72.W7b (D5 #18) imza.ac 401 + yeni X-Acilis yolunda ilk yaniti (HTTPError) KAPATIR",
               kapali == [1] and c3.acilis == "33" * 16, f"kapali={kapali}")

            # W8 gizli satir suzgeci WiFi'de de: EK satiri yayinlanmaz/arsivlenmez; durum satiri arsive girmez
            kart.akis_tut = 0.5
            kart.akis_satirlari = ["D 1.0", "EK 3 " + "ab" * 32, "W (12) wifi: x EK 4 ",
                                   "cd" * 32, "D 2.0", "D 3.0", "D 4.0"]
            w, bekl, durum = yeni()
            k = KO.Kopru(w, d / "arsiv_w")
            yay = []
            k.yayinla = yay.append
            w.bildir = yay.append
            th = threading.Thread(target=k.dongu, daemon=True)
            w.ac()
            th.start()
            _bekle_kosul(lambda: "D 4.0" in yay)
            k.calisiyor = False
            th.join(2)
            w.kapat()
            k.arsiv.kapat()
            ars = list(k.arsiv.ham_satirlar())
            # Beklenen: baglanti acilinca pencere (2 satir: D 1.0, tam EK) + bolunmus EK'nin penceresi
            # (cd.. parcasi, D 2.0) duser; D 3.0 / D 4.0 gecer (USB'deki suzgecle AYNI kural).
            yay_d = [x for x in yay if x.startswith("D ")]
            ars_d = [x for x in ars if x.startswith("D ")]
            ok("B72.W8 kopru gizli satir suzgeci WiFi yukari-akisinda da calisir: EK (tam ve bolunmus) "
               "yayinlanmaz/arsivlenmez, olcum satirlari aynen; durum satirlari arsive GIRMEZ",
               yay_d[:2] == ["D 3.0", "D 4.0"] and ars_d[:2] == ["D 3.0", "D 4.0"]
               and not any("ab" * 8 in x or "cd" * 8 in x or "EK " in x for x in yay + ars)
               and any(x.startswith("* kopru: WiFi") for x in yay)
               and not any(x.startswith(("* kopru", "! kopru")) for x in ars),
               f"yay={yay} ars={ars}")

            # W9 (PC5) cihaz dizini depo DISINDA; ortam ile degisir; eski kopru/.cihaz BIR KEZ KOPYALANIR
            for a in ("OLCUM_PC_DIZIN", "OLCUM_CIHAZ_DIZIN"):
                os.environ.pop(a, None)
            os.environ["LOCALAPPDATA"] = str(d / "yerel")
            v1 = IM.varsayilan_dizin()
            os.environ["OLCUM_PC_DIZIN"] = str(d / "pc")
            v2 = IM.varsayilan_dizin()
            os.environ["OLCUM_CIHAZ_DIZIN"] = str(d / "ozel")
            v3 = IM.varsayilan_dizin()
            eski_d, yeni_d = d / "agac" / ".cihaz", d / "goc"
            eski_d.mkdir(parents=True)
            (eski_d / f"{c.kimlik}.json").write_bytes(c.dosya.read_bytes())
            g1 = IM.goc_et(eski_d, yeni_d)
            g2 = IM.goc_et(eski_d, yeni_d)
            (eski_d / "ffffffffffffffff.json").write_text("{}", encoding="utf-8")
            g3 = IM.goc_et(eski_d, yeni_d)
            ok("B72.W9 (PC5) cihaz dizini %LOCALAPPDATA%\\olcum-karti\\cihaz (OLCUM_PC_DIZIN / "
               "OLCUM_CIHAZ_DIZIN ile degisir; calisma agacinda DEGIL); eski kopru/.cihaz dosyasi yeni "
               "dizin bossa BIR KEZ KOPYALANIR (tasinmaz), sonra bir daha dokunulmaz",
               v1 == d / "yerel" / "olcum-karti" / "cihaz" and v2 == d / "pc" / "cihaz" and v3 == d / "ozel"
               and g1 == [f"{c.kimlik}.json"] and g2 == [] and g3 == []
               and (eski_d / f"{c.kimlik}.json").exists()
               and (yeni_d / f"{c.kimlik}.json").read_bytes() == c.dosya.read_bytes()
               and IM.Cihaz.yukle(yeni_d / f"{c.kimlik}.json").K == c.K
               and Path(IM.ESKI_DIZIN).parent == (KOK / "kopru").resolve(),
               f"{v1} {v2} {v3} {g1} {g2} {g3}")

            # W10 eslestirme: --parola-ortamdan YALNIZ istenince OLCUM_PAROLA'yi okur; basilmaz, saklanmaz
            import contextlib
            import getpass as _gp
            os.environ["OLCUM_CIHAZ_DIZIN"] = str(d / "es")
            os.environ["OLCUM_PAROLA"] = kart.parola
            cikti = io.StringIO()
            with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(cikti):
                rc1 = IM.main(["esles", "--host", taban, "--ad", "kopru-2", "--parola-ortamdan"])
            ortamda_kaldi = "OLCUM_PAROLA" in os.environ
            dosyalar = sorted(p_.name for p_ in (d / "es").glob("*.json"))
            metin_ok = kart.parola not in cikti.getvalue() and not any(
                kart.parola in p_.read_text(encoding="utf-8") for p_ in (d / "es").glob("*.json"))
            sorulan = []
            asil_gp = _gp.getpass
            _gp.getpass = lambda *a, **k: (sorulan.append(1), kart.parola)[1]
            os.environ["OLCUM_PAROLA"] = "yanlis-ama-uzun-parola-1"
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc2 = IM.main(["esles", "--host", taban, "--ad", "kopru-3"])
            finally:
                _gp.getpass = asil_gp
            os.environ.pop("OLCUM_PAROLA", None)
            kart.istekler.clear()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    rc3 = IM.main(["esles", "--host", taban, "--ad", "kopru-4", "--parola-ortamdan"])
                except SystemExit as e:
                    rc3 = e.code
            ok("B72.W10 (PC7) `imza.py esles --parola-ortamdan` OLCUM_PAROLA'dan eslesir, cihazi YENI "
               "dizine yazar; parola ne ekrana ne dosyaya yazilir ve ortamdan silinir; bayrak YOKSA ortam "
               "OKUNMAZ (getpass sorulur); bayrak var degisken yoksa karta HICBIR istek gitmeden hata",
               rc1 == 0 and dosyalar == [f"{kart.gkimlik}.json"] and metin_ok and not ortamda_kaldi
               and rc2 == 0 and sorulan == [1] and rc3 not in (0, None) and not kart.istekler,
               f"rc={rc1},{rc2},{rc3} dosya={dosyalar} ortam={ortamda_kaldi} sorulan={sorulan}")

            # W11 cihaz kartta silinmis: /akis 401 — acik mesaj, firtina yok
            kart.akis_satirlari = ["D 1.0"]
            kart.akis_tut = 0.0
            Kc = kart.cihazlar.pop(c.n)
            kart.ret_401 = 0
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: len(bekl) >= 4)
            w.kapat()
            kart.cihazlar[c.n] = Kc
            ok("B72.W11 kart cihazi tanimiyorsa (/akis 401) mesaj eslestirmeyi soyler, yeniden deneme "
               "beklemesi ARTAR (istek firtinasi yok)",
               any("401" in x and "esles" in x for x in durum) and bekl[:4] == [1.0, 2.0, 4.0, 8.0]
               and kart.ret_401 <= len(bekl) + 1, f"401={kart.ret_401} bekleme={bekl[:5]}")

            # W12 kartin 4 yuvasi dolu: `event: dolu` — acik mesaj, sonra yeniden denenir
            kart.akis_dolu = True
            w, bekl, durum = yeni()
            w.ac()
            _bekle_kosul(lambda: len(bekl) >= 2)
            w.kapat()
            kart.akis_dolu = False
            ok("B72.W12 kartin canli izleyici yuvalari doluysa (`event: dolu`) kopru bunu SOYLER ve "
               "artan beklemeyle yeniden dener", any("dolu" in x for x in durum) and bekl[:2] == [1.0, 2.0],
               f"{durum[-1:]} {bekl[:3]}")

            # W13 kapat() suresinde bitmeyen ESKI iplik (ör. mDNS cozumu) yeni akisa satir KOYAMAZ
            w, bekl, durum = yeni()
            eski_dur = threading.Event()
            eski_dur.set()                                   # kapatilmis ipligin olayi
            sonuc_13 = []

            def _eski_iplik():
                w._yerel.dur = eski_dur
                w._koy("D eski")
                sonuc_13.append(w._durdu())
            t13 = threading.Thread(target=_eski_iplik)
            t13.start()
            t13.join(2)
            w._koy("D yeni")                                 # bu iplik: guncel (durdurulmamis) olay
            ok("B72.W13 durdurma olayi IPLIK BASINA: kapatilmis eski WiFi ipliginin satiri kuyruga "
               "girmez (USB<->WiFi gecisinde eski akis yeni akisa karismaz); guncel iplik koyar",
               sonuc_13 == [True] and w.satir_oku(0.1) == "D yeni" and w.satir_oku(0.05) is None,
               str(sonuc_13))

            # W14-W16 (4J) butun kart istekleri OGRENILMIS karsi adrese; Host ad olarak kalir;
            # olu adreste ada BIR KEZ dusulur; eski adresteki yabanci cihaz dogrulanamaz -> ad
            bolum_kopru_wifi_4j(KW, kart, cdiz, taban)
    finally:
        for a, v in eski_ortam.items():
            if v is None:
                os.environ.pop(a, None)
            else:
                os.environ[a] = v
        sunucu.shutdown()


def _host_basligi(istek: str) -> str | None:
    if "'Host': '" not in istek:
        return None
    return istek.split("'Host': '", 1)[1].split("'", 1)[0]


def bolum_kopru_wifi_4j(KW, kart: "_SahteKart", cdiz: Path, taban: str) -> None:
    """4J: WifiKart'in BUTUN kart istekleri (acik /eslestir/bilgi, imzali /akis, /komut, esitleme /
    vekil / bildirim — hepsi `imzali_ac`) ogrenilmis karsi adrese gider; ad cozumu (Windows'ta
    `olcum.local` ~8 s'de bir 2.7 s) yalniz ilk baglantida ve adres oldugunde. Sahte kartta ad
    `localhost` (Windows'ta her ad baglantisi ::1 reddi yuzunden ~2 s — gercek kartin yavas cozumu
    gibi). Hangi adrese baglanildigi `kart_wifi._tcp_ac` kancasiyla izlenir."""
    port = taban.rsplit(":", 1)[1]
    ad_host = "localhost:" + port
    yabanci = _SahteKart([])
    yabanci.gkimlik = "8899aabbccddeeff"              # baska bir cihaz (kartin eski IP'sini almis)
    ys, ytaban = _sunucu(yabanci)
    yabanci_port = int(ytaban.rsplit(":", 1)[1])
    asil_tcp = KW._tcp_ac
    hedefler: list[str] = []
    sureler: dict[str, float] = {}

    def kayitli_tcp(adres, sure, kaynak=None):
        hedefler.append(adres[0])
        sureler[adres[0]] = sure
        if adres[0] == "192.0.2.1":                    # TEST-NET: kartin eski (olu) adresi
            raise ConnectionRefusedError("4J sinama: eski adres yanit vermiyor")
        if adres[0] == "192.0.2.2":                    # eski adreste BASKA bir cihaz
            adres = ("127.0.0.1", yabanci_port)
        return asil_tcp(adres, sure, kaynak)
    KW._tcp_ac = kayitli_tcp
    w = None
    try:
        kart.akis_satirlari = ["D 1.0"]
        kart.akis_tut = 30.0
        kart.akis_bitir.clear()
        kart.saat_kaynak = 1
        kart.komut_imzali.clear()
        kart.istekler.clear()
        w = KW.WifiKart(ad_host, dizin=cdiz, bekle=lambda sn: time.sleep(0.02))
        w.bildir = lambda m: None
        w.ac()
        _bekle_kosul(lambda: w.bagli, 10.0)
        w.yaz("A?")
        cihaz, _, _ = w.dogrula()
        with w.imzali_ac(cihaz, "GET", "/kayit/liste") as y:
            y.read()
        h14 = list(hedefler)
        yollar14 = [x.split()[1].split("?")[0] for x in kart.istekler]
        host14 = {_host_basligi(x) for x in kart.istekler}
        ok("B72.W14 (4J) WiFi koprusunun BUTUN kart istekleri (acik /eslestir/bilgi, imzali /akis, "
           "/komut, esitleme /kayit/*) ilk ad baglantisinda OGRENILEN karsi adrese gider — ad cozumu "
           "yalniz bir kez (Windows `olcum.local` ~8 s'de bir 2.7 s; 4G); `Host:` basligi HER istekte "
           "ad olarak kalir (kart yabanci Host'u 403 ile reddeder — DNS rebinding korumasi)",
           w.bagli and h14[:1] == ["localhost"] and len(h14) >= 5
           and all(h == "127.0.0.1" for h in h14[1:])
           and {"/eslestir/bilgi", "/akis", "/komut", "/kayit/liste"} <= set(yollar14)
           and host14 == {ad_host} and kart.komut_imzali == [("A?", True)] and w._karsi == "127.0.0.1",
           f"baglantilar={h14} yollar={yollar14} host={host14} komut={kart.komut_imzali} karsi={w._karsi}")

        # W15 olu adres (kart baska IP almis): BIR KEZ ada dusulur, istek karta TEK KEZ ulasir,
        # adres tazelenir; sonraki istek yine adsiz
        w._karsi = "192.0.2.1"
        hedefler.clear()
        n401 = kart.ret_401
        w.yaz("A2?")
        h15a = list(hedefler)
        karsi15 = w._karsi
        hedefler.clear()
        w.yaz("A3?")
        h15b = list(hedefler)
        ok("B72.W15 (4J) ogrenilmis adres yanit vermezse (kart baska IP almis) istek BIR KEZ ada duser "
           "ve karta TEK KEZ ulasir (yalniz baglanti kurulamamasi geri dusurur — imzali istek iki kez "
           "gitmez, 401 yok); olu adres en cok 2 s beklenir (sessiz adres her istegi 10 s bekletmesin); "
           "adres tazelenir, sonraki istek yeniden adsiz",
           h15a == ["192.0.2.1", "localhost"] and karsi15 == "127.0.0.1" and h15b == ["127.0.0.1"]
           and sureler.get("192.0.2.1", 99) <= 2.0 and sureler.get("localhost") == w.zaman_asimi
           and kart.komut_imzali == [("A?", True), ("A2?", True), ("A3?", True)] and kart.ret_401 == n401,
           f"once={h15a} karsi={karsi15} sonra={h15b} sure={sureler} komut={kart.komut_imzali} "
           f"401={kart.ret_401 - n401}")

        # W16 eski adreste BASKA bir cihaz: kimlik uymaz -> adres unutulur, ad ile kart dogrulanir;
        # yabanci cihaza imzali istek GITMEZ
        w._karsi = "192.0.2.2"
        hedefler.clear()
        yabanci.istekler.clear()
        try:
            _, k16, _ = w.dogrula()
        except KW.KartDogrulanamadi as e:
            k16 = f"HATA {e}"
        h16 = list(hedefler)
        y_yollar = [x.split()[1] for x in yabanci.istekler]
        ok("B72.W16 (4J) ogrenilmis adreste BASKA bir cihaz cevap verirse kimlik denetimi (D5 #18) onu "
           "reddeder, adres unutulur ve kart ad ile BIR KEZ daha dogrulanir; yabanci cihaza yalniz acik "
           "/eslestir/bilgi gider (imzali istek YOK) — IP'ye korlemesine guvenilmez",
           k16 == kart.gkimlik and h16 == ["192.0.2.2", "localhost"] and w._karsi == "127.0.0.1"
           and y_yollar == ["/eslestir/bilgi"] and not any("X-Imza" in x for x in yabanci.istekler),
           f"kimlik={k16} baglantilar={h16} yabanci={y_yollar} karsi={w._karsi}")
    finally:
        KW._tcp_ac = asil_tcp
        kart.akis_bitir.set()
        if w is not None:
            w.kapat()
        kart.akis_tut = 0.0
        ys.shutdown()


# ── B72.A · 4C arka plan disk arsivi: kopru icinde esitleme dongusu ───────────
class _SanalSaat:
    """Esitleme dongusunun saati: `bekle` zamani ilerletir, gercekte beklemez."""

    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def bekle(self, sn: float) -> None:
        self.t += sn
        time.sleep(0)


class _DonukSaat:
    """imza.py'nin `time` modulu yerine: time() SABIT (ayni milisaniye), gerisi gercek.
    Iki ayri Cihaz nesnesi ayni ms'de ayni sayaci uretir — paylasim kusurunu belirlenimci yapar."""

    def __init__(self, t: float):
        self.sabit = t

    def time(self) -> float:
        return self.sabit

    def __getattr__(self, ad):
        return getattr(time, ad)


def _arsivdeki(kok: Path, kart_k: str, akis: int):
    p = Path(kok) / kart_k / f"akis-{akis}" / KE.DOSYA
    return p.read_bytes() if p.exists() else None


def bolum_kopru_esitle() -> None:
    """4C (PC5, PC6, PC9): kopru sureci kartin kayitlarini WiFi'den, ESLESMIS CIHAZ olarak
    (WifiKart'in AYNI Cihaz nesnesi + sayac kilidi) arka planda diske esitler."""
    print("\n── B72.A  4C arka plan disk arsivi: kopru icinde esitleme dongusu (WiFi, imzali, "
          "kalici yazimdan SONRA onay, aralik + taban + artan bekleme)")
    import imza as IM
    import kart_wifi as KW
    import kopru as KO
    import arka_esitle as AE
    import pc as PC
    kay = _kayitlar(400)
    kart = _SahteKart(list(kay))
    sunucu, taban = _sunucu(kart)
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cdiz = d / "cihaz"
            IM.esles(taban, "kopru", kart.parola, dizin=cdiz)
            kart.imza_zorunlu = True                     # gercek kart gibi: imzasiz okuma yok
            gk = kart.gkimlik

            def wifi_yeni(**kw):
                return KW.WifiKart(taban, dizin=cdiz, bekle=lambda sn: time.sleep(0.02), **kw)

            def es_yeni(w, kok, **kw):
                yay: list[str] = []
                return AE.ArkaEsitleme(w, yay.append, kok, **kw), yay

            # A1 + A2 + A6: tek tur — arsiv bayt bayt, onay kalici yazimdan SONRA, parca <= 8192 + ara
            kok = d / "arsiv"
            anlar: list[tuple] = []

            def kanca(s):
                p = kok / gk / "akis-7"
                veri = (p / KE.DOSYA).read_bytes() if (p / KE.DOSYA).exists() else b""
                durum = (json.loads((p / KE.DURUM).read_text(encoding="utf-8"))
                         if (p / KE.DURUM).exists() else {})
                gerekli = b"".join(k for k in kart.kayitlar if struct.unpack_from("<I", k, 4)[0] <= s)
                anlar.append((s, veri[:len(gerekli)] == gerekli, durum.get("son_sira", 0) >= s))
            kart.onay_kanca = kanca
            kart.zamanli.clear()
            kart.istekler.clear()
            kart.komutlar.clear()
            w = wifi_yeni()
            # 4J: A6'nin araligi ISTEMCININ gonderme aninda olculur (kartin varis aninda degil: yuklu
            # makinede ilk istegin varisi gecikince ara 81-82 ms gorunuyordu — olcum makineyi sinardi)
            gonderim: list[tuple] = []
            asil_imzali = w.imzali_ac

            def _izli_imzali(cihaz_, yontem, yol, *a, **k):
                gonderim.append((time.monotonic(), yol))
                return asil_imzali(cihaz_, yontem, yol, *a, **k)
            w.imzali_ac = _izli_imzali
            e, yay = es_yeni(w, kok)
            r = e.tur()
            w.imzali_ac = asil_imzali
            ok("B72.A1 (PC9) kopru esitleme turu kartin BUTUN kayitlarini WiFi'den <kart kimligi>/akis-<akis "
               "kimligi>/kayitlar.kyt'ye bayt bayt yazar; `* esitleme:` durum satiri yeni kayit + son sira "
               "soyler",
               _arsivdeki(kok, gk, 7) == b"".join(kay) and r["sonuc"] == "tamam" and r["yeni_kayit"] == 400
               and r["son_sira"] == 400
               and any(x.startswith("* esitleme:") and "400 yeni kayit" in x and "son sira 400" in x
                       for x in yay), f"{ {a: r.get(a) for a in ('sonuc', 'yeni_kayit', 'son_sira', 'mesaj')} } "
                                      f"{yay[-1:]}")
            n_go = sum(1 for x in kart.komutlar if x.startswith("Go"))
            ok("B72.A2 (PC9) varsayilan ONAY: Go<sira> IMZALI gider ve karta ULASTIGI anda veri diskte + "
               "durum.json o siraya yazilmis (kalici yazimdan SONRA); kisa turda TEK Go (her Go kartin "
               f"akisina satir basar; uzun esitlemede {AE.ONAY_PARCA} parcada bir); kart dogrular, durum "
               "`onay gitti` der",
               bool(anlar) and all(a[1] and a[2] for a in anlar) and anlar[-1][0] == 400 and kart.onay == 400
               and n_go == 1
               and ("Go400", True) in kart.komut_imzali and r.get("onay_dogrulandi") is True
               and any("onay gitti" in x for x in yay), f"anlar={anlar[-2:]} onay={kart.onay} Go={n_go}")
            veri_ist = [(t, dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(p).query)))
                        for t, y, p in kart.zamanli if p.startswith("/kayit/veri")]
            bayt = [int(q.get("bayt", "0")) for _, q in veri_ist]
            gonder_veri = [t for t, y in gonderim if y == "/kayit/veri"]
            aralar = [b - a for a, b in zip(gonder_veri, gonder_veri[1:])]
            imzasiz = [x for x in kart.istekler if x.split()[1].startswith(("/kayit/", "/kal/"))
                       and "X-Imza" not in x]
            ok("B72.A6 (spec §5/§11) parca kartin tavanini asmaz (bayt <= 8192) ve iki parca isteginin "
               "baslangici arasi en az 100 ms (istek hizi tavani <= 10/s, tek istek; spec 4C-3) — 4J: ara "
               "ISTEMCININ gonderme aninda olculur (kartin varis ani makine yukunu de olcuyordu); "
               "butun kayit istekleri IMZALI",
               len(veri_ist) >= 5 and len(gonder_veri) == len(veri_ist)
               and all(0 < b <= 8192 for b in bayt) and max(bayt) == AE.PARCA_BAYT
               and min(aralar) >= 0.098 and not imzasiz,
               f"{len(veri_ist)} parca bayt={sorted(set(bayt))} en kisa ara={min(aralar or [0]) * 1000:.0f} ms "
               f"imzasiz={len(imzasiz)}")
            kart.onay_kanca = None

            # A3 --onaysiz: hic Go gitmez, arsiv yine tam
            kart.onay = 0
            kart.komutlar.clear()
            e3, yay3 = es_yeni(w, d / "arsiv3", onay=False)
            r3 = e3.tur()
            ok("B72.A3 (PC9) onaysiz kipte (--onaysiz) karta HICBIR Go<sira> gitmez; arsiv yine tam; durum "
               "`onay gitmedi (onaysiz)` der",
               not any(x.startswith("Go") for x in kart.komutlar) and kart.onay == 0
               and _arsivdeki(d / "arsiv3", gk, 7) == b"".join(kay) and r3["onay_gitti"] is False
               and any("onay gitmedi" in x for x in yay3), f"komutlar={kart.komutlar[:3]} {yay3[-1:]}")

            # A4 kopukluk + bosluk doldurma
            kart.erisilemez = True
            r4a = e.tur()
            ek = _kayitlar(60, 401)
            kart.kayitlar = kay + ek
            kart.erisilemez = False
            r4b = e.tur()
            ok("B72.A4 (O3) ag kopukken tur HATA olur (durum satiri `! esitleme:`), kart arada kayit uretir; "
               "geri gelince yalniz eksikler cekilir: arsiv == kartin butun kayitlari (tekrar yok)",
               r4a["sonuc"] == "hata" and any(x.startswith("! esitleme:") for x in yay)
               and r4b["yeni_kayit"] == 60 and _arsivdeki(kok, gk, 7) == b"".join(kay + ek),
               f"hata={r4a.get('mesaj', '')[:60]!r} yeni={r4b.get('yeni_kayit')}")

            # A5 kartin kayit akisi degisti (bicimlendi): YENI alt dizin, eskisine dokunulmaz
            eski7 = _arsivdeki(kok, gk, 7)
            yeni_kay = _kayitlar(10)
            kart.kayitlar = list(yeni_kay)
            kart.kimlik = 8
            kart.onay = 0
            r5 = e.tur()
            ok("B72.A5 kartin kayit AKIS kimligi degisirse (bicimlendi / sifirlandi) yeni alt dizin "
               "(akis-8); eski arsiv bayt bayt yerinde, iki akis KARISMAZ; durum satiri soyler",
               _arsivdeki(kok, gk, 8) == b"".join(yeni_kay) and _arsivdeki(kok, gk, 7) == eski7
               and r5["sonuc"] == "tamam" and r5["arsiv"] == f"arsiv/{gk}/akis-8"
               and any("akis" in x and "degisti" in x for x in yay), f"{r5.get('arsiv')} {yay[-1:]}")
            kart.kayitlar, kart.kimlik = list(kay), 7

            # A7 kart yalniz USB'den erisilebilir: esitleme atlanir, soylenir, dizin acilmaz
            w9 = KW.WifiKart("127.0.0.1:9", dizin=cdiz)
            e9, yay9 = es_yeni(w9, d / "arsiv9", usb_etkin=lambda: True)
            r9 = e9.tur()
            ok("B72.A7 (PC6) kart WiFi'den erisilemiyor ama USB'deyse esitleme ATLANIR ve `! esitleme:` "
               "satiri kayit verisinin yalniz WiFi'den alindigini (USB seri dokumu 4C-2, ertelendi) soyler; "
               "arsiv dizini acilmaz",
               r9["sonuc"] == "atlandi" and not (d / "arsiv9").exists()
               and any(x.startswith("! esitleme:") and "USB" in x and "4C-2" in x for x in yay9),
               f"{r9.get('sonuc')} {yay9[-1:]}")

            # A8 pc.py baglantisi: durum satiri tarayicilara gider, .satir arsivine GIRMEZ
            kart.akis_satirlari = ["D 1.0", "D 2.0", "D 3.0", "D 4.0"]
            kart.akis_tut = 3.0
            kart.akis_bitir.clear()
            w8 = wifi_yeni()
            k8 = KO.Kopru(w8, d / "satir8")
            abone = k8.abone_ol()
            e8 = PC.esitleme_kur([], w8, k8, arsiv_kok=d / "arsiv8", yazdir=lambda *_: None)
            th8 = threading.Thread(target=k8.dongu, daemon=True)
            w8.ac()
            th8.start()
            _bekle_kosul(lambda: w8.bagli)
            r8 = e8.tur()
            _bekle_kosul(lambda: k8.satir_adedi >= 2)
            k8.calisiyor = False
            th8.join(2)
            kart.akis_bitir.set()
            w8.kapat()
            k8.arsiv.kapat()
            gelen = []
            while not abone.empty():
                gelen.append(abone.get_nowait())
            ars8 = list(k8.arsiv.ham_satirlar())
            ok("B72.A8 (pc.esitleme_kur) `* esitleme:` durum satiri kopru uzerinden TARAYICILARA gider, "
               ".satir arsivine GIRMEZ (olcum satirlari girer)",
               r8["sonuc"] == "tamam" and any(x.startswith("* esitleme:") for x in gelen)
               and any(x.startswith("D ") for x in ars8) and not any("esitleme" in x for x in ars8),
               f"gelen={[x for x in gelen if 'esitleme' in x][:1]} ars={ars8[:3]}")

            # A9 ayni Cihaz nesnesi + kilit: akis yeniden baglanirken esitleme turlari — 401 YOK
            asil_time = IM.time
            IM.time = _DonukSaat(time.time())
            try:
                kart.akis_satirlari = ["D 1.0"]
                kart.akis_tut = 0.0
                kart.ret_401 = 0
                w = wifi_yeni()
                e9b, _ = es_yeni(w, d / "arsiv_sayac")
                once = kart.akis_sayisi
                w.ac()
                n_tur, son = 0, time.monotonic() + 2.5
                while time.monotonic() < son:
                    e9b.tur()
                    n_tur += 1
                w.kapat()
            finally:
                IM.time = asil_time
            ok("B72.A9 (4B-12) esitleme ile canli akis AYNI Cihaz nesnesini ve sayac kilidini paylasir: "
               "ayni milisaniyede bile tekrar sayac yok — kart hicbirini 401 ile reddetmez",
               kart.ret_401 == 0 and kart.akis_sayisi - once >= 5 and n_tur >= 5,
               f"401={kart.ret_401} akis={kart.akis_sayisi - once} tur={n_tur}")

            # A10 imzali /akis adresi uretimi + istek + yanit basi kilitte: yavas ag (mDNS) sirasinda
            # esitleme istegi araya girip sayaci ileri atamaz (kart pencere disi eski sayaci reddederdi)
            istekte = threading.Event()

            def yavaslat(w_):
                """4J: /akis baglantisi WifiKart'in kendi baglanti sinifindan — onu yavaslat."""
                class _Yavas(w_._baglanti_sinifi):
                    def request(self, yontem, url, *a, **k):
                        if url.startswith("/akis"):
                            istekte.set()
                            time.sleep(0.4)
                        return super().request(yontem, url, *a, **k)
                w_._baglanti_sinifi = _Yavas
                return w_
            kart.akis_satirlari = ["D 1.0"]
            kart.akis_tut = 2.0
            kart.akis_bitir.clear()
            kart.ret_401 = 0
            try:
                w = yavaslat(wifi_yeni())
                e10, _ = es_yeni(w, d / "arsiv_sira", onay=False)
                w.ac()
                istekte.wait(5)
                time.sleep(0.15)
                r10 = e10.tur()
                _bekle_kosul(lambda: w.bagli, 3)
                kart.akis_bitir.set()
                w.kapat()
                ret_a = kart.ret_401
                # ikinci duzen: esitleme turu SURERKEN (parcalar arasi) akis yavas yeniden baglanir —
                # esitlemenin her imzali istegi de kilitte olmali (yalniz dogrula degil)
                kart.akis_bitir.clear()
                istekte.clear()
                w = yavaslat(wifi_yeni())
                e10b, _ = es_yeni(w, d / "arsiv_sira2", onay=False)
                r10b: dict = {}
                isaret = len(kart.zamanli)
                t10 = threading.Thread(target=lambda: r10b.update(e10b.tur()), daemon=True)
                t10.start()
                _bekle_kosul(lambda: any(z[2].startswith("/kayit/veri") for z in kart.zamanli[isaret:]), 5)
                w.ac()
                istekte.wait(5)
                t10.join(15)
                _bekle_kosul(lambda: w.bagli, 3)
            finally:
                kart.akis_bitir.set()
            w.kapat()
            r10 = {**r10, "sonuc": r10["sonuc"] if r10b.get("sonuc") == "tamam" else "B:" + str(r10b.get("sonuc"))}
            kart.ret_401 = max(kart.ret_401, ret_a)
            ok("B72.A10 imzali /akis adresinin uretimi, istegi ve yanit basi esitlemeyle AYNI kilitte: "
               "yavas baglanti (mDNS) sirasinda gelen esitleme bekler — tur baslarken de, tur SURERKEN "
               "(parcalar arasi) de; kart akisi tekrar diye reddetmez (401 yok)",
               istekte.is_set() and kart.ret_401 == 0 and r10["sonuc"] == "tamam",
               f"401={kart.ret_401} tur={r10.get('sonuc')}")

            # A11 taban + artan bekleme (sanal saat): yeniden baglanti firtinasi kartı bogamaz
            def bilgi_zamanlari():
                return [z[0] for z in kart.zamanli if z[2] == "/eslestir/bilgi"]
            v = _SanalSaat()
            kart.zaman = v
            kart.bilgi_kod = 503
            no = [0]

            def firtina():
                no[0] += 1
                return no[0]
            kart.zamanli.clear()
            e11, _ = es_yeni(wifi_yeni(), d / "arsiv_t", saat=v, bekle=v.bekle, tetik=firtina)
            e11.baslat()
            _bekle_kosul(lambda: len(bilgi_zamanlari()) >= 7, 15)
            e11.durdur()
            tz = bilgi_zamanlari()
            ar_a = [round(b - a, 3) for a, b in zip(tz, tz[1:])]
            ok("B72.A11a hata + her an yeniden baglanti (firtina): esitleme turlari arasi EN AZ 10 s (mutlak "
               "taban, spec 4C-1) — kart dovulmez",
               len(ar_a) >= 6 and min(ar_a) >= 10.0 and max(ar_a) <= 10.0 + AE.YOKLA_SN + 1e-6,
               str(ar_a[:8]))
            kart.bilgi_kod = 0
            kart.bilgi_hata_kalan = 3
            kart.zamanli.clear()
            v2 = _SanalSaat()
            kart.zaman = v2
            e11b, _ = es_yeni(wifi_yeni(), d / "arsiv_t2", saat=v2, bekle=v2.bekle, tetik=lambda: 1,
                              onay=False)
            e11b.baslat()
            _bekle_kosul(lambda: len([z for z in kart.zamanli if z[2] == "/eslestir/bilgi"]) >= 6, 15)
            e11b.durdur()
            tz = [z[0] for z in kart.zamanli if z[2] == "/eslestir/bilgi"]
            ar_b = [round(b - a, 3) for a, b in zip(tz, tz[1:])]
            ok("B72.A11b hata sonrasi bekleme ARTAR (15, 30, 60 s), basaridan sonra normal aralik (120 s); "
               "ilk tur hemen (spec 4C-1)",
               len(ar_b) >= 5 and tz[0] - 1000.0 < 1.0
               and all(abs(a - b) <= AE.YOKLA_SN + 1e-6 for a, b in zip(ar_b[:5], [15.0, 30.0, 60.0, 120.0, 120.0])),
               str(ar_b[:6]))
            kart.zaman = time.monotonic
            ok("B72.A11c hata beklemesi 15, 30, 60 ... s, tavan 600 s; sabitler spec 4C-1 ile ayni (taban 10 "
               "<= hata tabani 15 <= en kisa aralik 30 <= aralik 120 <= tavan 600 s)",
               [AE.hata_beklemesi(n) for n in (1, 2, 3, 7, 40)] == [15.0, 30.0, 60.0, 600.0, 600.0]
               and (AE.TABAN_SN, AE.HATA_TABAN_SN, AE.ARALIK_EN_AZ, AE.ARALIK_SN, AE.HATA_AZAMI_SN)
               == (10.0, 15.0, 30.0, 120.0, 600.0) and AE.PARCA_ARASI_SN == 0.1 and AE.PARCA_BAYT == 8192,
               f"{[AE.hata_beklemesi(n) for n in range(1, 9)]}")

            # A12 durum ozeti (kopru /esitleme/durum): mutlak yol YOK
            dz = e.durum()
            metin = json.dumps(dz, ensure_ascii=False)
            ok("B72.A12 durum ozeti (kopru /esitleme/durum) son tur, yeni kayit, son sira, onay ve arsivin "
               "GORELI adini verir; mutlak yol (kullanici dizini) icermez",
               dz["etkin"] is True and dz["sonuc"] == "tamam" and dz["son_sira"] == 10 and dz["onay"] is True
               and dz["arsiv"] == f"arsiv/{gk}/akis-8" and dz["son_basari"] and "onay_gitti" in dz
               and str(d) not in metin and str(d).replace("\\", "/") not in metin
               and not re.search(r"[A-Za-z]:[\\/]", metin), metin[:160])
    finally:
        sunucu.shutdown()


BOLUMLER = [bolum_tablo, bolum_kaynak, bolum_esitle, bolum_guvenlik_py, bolum_guvenlik_kart,
            bolum_guvenlik_istemci, bolum_bildirim_kart, bolum_kopru_wifi, bolum_kopru_esitle]


def main() -> int:
    for b in BOLUMLER:
        b()
    tezgah("B72 Kayit firmware + esitleme", [
        ("Flas yazma/silmenin olcume etkisi (spec §11 ilk risk)",
         "tezgah_kayit.py --durma: 50/s ve 5/s'de kuyrukta dusen nokta 0; "
         "loop_azami ve sil_azami_us raporlanir"),
        ("Kayit surerken sifirlama (RTS) -> DEVAM",
         "tezgah_kayit.py --kesinti 20: her sifirlamada durum 2'ye doner, "
         "flasta tek oturum, noktalar bosluksuz, sira tekrar yok"),
        ("Esitlenen dosya == karttaki flas bolumu (bayt bayt)",
         "tezgah_kayit.py --esit: esptool ile okunan bolumdeki her kayit "
         "esitlenen dosyadakiyle ayni"),
        ("DOLU bolumde acilis (bolumu 50/s ONAYSIZ ~1.7 sa doldur)",
         "tezgah_kayit.py --dolu: tarama < 5 s ve Task WDT sifirlamasi YOK "
         "(2026-09-30'da sonsuz yeniden baslama bulundu), 11 MB esitlenir, "
         "onay dogrulanir, halka doner, dusen 0"),
        ("DOLU bolumde GF!",
         "tezgah_kayit.py --bicim: anlik biter, temizlik surerken /kayit/liste "
         "her istekte < 1 s (p0 ayni web sunucusunda), temiz_kalan azalir"),
        ("1B kalibrasyon gecmisi kartta",
         "tezgah_kayit.py --kal: #1 = Ayar3, not/tur kalici, oturum basliginda "
         "kal_no, /kal/liste == kl, etkin, `kk` taslaksiz kayit acmaz, Gb sessiz "
         "(kalibrasyon komutu CALISTIRMAZ)"),
        ("[!] ADS takilinca: GERCEK bir kalibrasyon adimi",
         "g sonrasi `k?` taslak=1; `kk<t><not>` yeni numara; ardindan baslayan "
         "kaydin kal_no'su o numara; unutulursa kayit baslarken otomatik ve kart "
         "'otomatik kaydedildi' der. z (sifirlama) sonrasi taslak=0 (sifirlar "
         "gecmise girmez); sont degistirip geri alinca eski numara"),
        ("[!] Gecmis doluyken tarama suresi",
         "30+ kayitli gecmiste degerler degisince kgc_esle en fazla 39 NVS "
         "okumasi: ayar komutu ve Gb'de loop_azami < 20 ms (tahmin ~4-8 ms)"),
        ("1C-1 pil oturumu kartta (ADS yok)",
         "tezgah_kayit.py --pil: p1 reddedilir ve oturum acmaz; Ga/Ge/Gn gercek oturuma, "
         "PC adi/etiketi/notlari okur, Gx siler; olcum oturumu yeniden baslatmada DEVAM"),
        ("[!] ADS takilinca: GERCEK pil testi kaydi",
         "p1 -> G satirinda PIL oturumu; 5 dk'da bir DCIR olayi; kesmede PIL_SONUC == `B` "
         "raporu (mAh, Wh, sure, dcir sayisi); test ortasinda fis cekilirse acilista oturum "
         "BITIR(5), DEVAM yok; olcum kaydi surerken p1 -> olcum BITIR(6)"),
        ("1C-2 ayrintili kip kartta (ADS yok)",
         "tezgah_kayit.py --ayrinti: hazir alan bosta buyur; Gb0 60 s: sira kesintisiz, "
         "zaman farki dagilimi, kayit ici silme 0, dusen 0; yeniden baslatmada DEVAM"),
        ("[!] Skop girisine CAL bagliyken osiloskop gunlugu (1C-3)",
         "X1000 + tek tel GPIO10 -> GPIO4 (ya da RC duzenegi): tezgah_kayit.py --skop sinyalli dalda "
         "Gt0 her yakalama tetikli ve ~1 kHz; 2026-10-01'de giriste sinyal yoktu (kodlar 0)"),
        ("[!] ADS takilinca: gercek 500/s ayrintili kayit",
         "Gb0 60 s: ~30 000 ornek, dt ortancasi ~2000 us; PC'de V/I (ve hizalamali W) kartin D "
         "satiriyla ayni anda karsilastirilir; hazir alan bitince KA_SILME kayitlari gorulur"),
        ("1E bildirimler kartta (PC'de sahte araci, hesap gerekmez)",
         "tezgah_bildirim.py: Qv gecti; CONNECT keepalive 5 + vasiyet QoS 1 retained; durum c:1 "
         "cozulur (f A3-1E); Qt olayi `n` artarak; RTS sifirlamasinda vasiyet <= 15 s; araci "
         "kesintisinde olay kuyrukta bekler, yeniden baglaninca gider; QY dahili_bos >= 60 KB; "
         "/komut Q'yu 403 ile reddeder; Q?/akis hicbir parolayi gostermez"),
        ("Gercek araci (EMQX Serverless): TLS + O4 (2026-10-02: 16/16 vasiyet 4.0-7.9 s)",
         "Qu mqtts://<adres>.emqxsl.com:8883, Qk/Qp kart, Qc/Qd cihaz, Q1: Q? bagli ve "
         "el_sikisma_ms; TLS el sikismasi sirasinda K satirinda loop_azami degismez (K11); "
         "fis cekme -> vasiyet <= 15 s (hedef 10), 10 tekrar (O4)"),
        ("Gercek fis cekme (USB + PIL kapali)",
         "elle 5 kez: kurtarma hatasiz, kayit DEVAM ile surer, kayip en fazla "
         "son ~5 s"),
    ])
    gercek_dizin_koru.denetle(_KORUMA, ok)
    print(f"\nB72: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
