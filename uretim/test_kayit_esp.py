# -*- coding: utf-8 -*-
"""B72 — KAYIT MOTORUNUN KARTA BAGLANMASI: bolum tablosu · firmware kaynagi · esitleme.

    python test_kayit_esp.py

Gercek karti DEGIL; tabloyu, firmware KAYNAGINI (yorumlar cikarilarak) ve
PC esitleme istemcisini (sahte kart sunucusuna karsi) sinar. Kartta
olculecekler `tezgah_kayit.py`'de ve tezgah kalemi olarak basiliyor.
Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md
"""
from __future__ import annotations

import http.server
import json
import os
import re
import struct
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
KOD = KOK / "kod" / "olcum-karti-a3"
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "kopru"))
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
       re.search(r'#define KAYIT_FW_SURUM\s+"A3-1D"', esp_k) is not None)
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
       "ACMAZ, sonucu istek numarasiyla yayinlar",
       0 <= kb4.find("kayit_y.oturum == id") < kb4.find("ky_bitir(&kayit_y, m->sebep)")
       and "if (!kayit_y.oturum && !kayit_m.devam_bekliyor)" in kb5
       and kb5.find("kyn_baslat(") < kb5.find("kayit_plan_sonuc = s;")
       < kb5.find("kayit_plan_sonuc_no = m->sebep;"))
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

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if self._imza("GET", b"") is False:
                return
            if u.path == "/eslestir/bilgi":
                self._json({"surum": "OK1", "kimlik": kart.gkimlik, "acilis": kart.acilis,
                            "tuz": kart.tuz.hex(), "tur": kart.tur, "zorunlu": int(kart.imza_zorunlu),
                            "misafir": 0, "saat": 0, "cihaz_azami": 8})
                return
            if u.path == "/akis":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'retry: 3000\n\nevent: kimlik\n'
                                 b'data: {"jeton":"abc123","surucu":true}\n\n')
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
            if imzali or (self.headers.get("X-Olcum") == "1" and self.headers.get("X-Jeton") == "abc123"):
                kart.komutlar.append(govde)
                if govde.startswith("Go"):
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
             "/skop.bin": "GUV_OKUMA", "/komut": "GUV_KOMUT", "/kopru": "GUV_KOMUT",
             "/eslestir/bilgi": "GUV_ACIK", "/eslestir/baslat": "GUV_ACIK",
             "/eslestir/kanit": "GUV_ACIK", "/cihaz/liste": "GUV_CIHAZ",
             "/cihaz/sil": "GUV_CIHAZ", "/saat": "GUV_CIHAZ"}
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
    ok("B72.F77 K hex'i YALNIZ ham UART'a: EK satiri Serial.ham ile; khex hicbir aynali "
       "baskida yok; WebAkis::ham yalniz gercek porta yazar",
       '"EK ' in sk and any("Serial.ham(" in s for s in khex)
       and not any(("Serial.print" in s or "printf" in s) and "ham(" not in s for s in khex)
       and "void ham(const char *s)" in wa_k
       and "_besle" not in govde(wa_k, "void ham(const char *s)"))
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
    kpg = govde(ino_k, "void kopru_sayfa(")
    ok("B72.F81c /kopru (CORS kokeni kaydi) zorunlulukta imzasiz REDDEDILIR",
       0 <= kpg.find("guv_kapi(GUV_KOMUT)") < kpg.find("if (!guv_imzali && guv.ayar.zorunlu)")
       < kpg.find("kopru_adres"))
    i_n = ino_k.find("if (alt == 0 || alt == '?') {")
    ns = ino_k[i_n:ino_k.find("if (alt == 'a')", i_n)] if i_n >= 0 else ""
    ok("B72.F91 N? AP parolasini YALNIZ ham UART'a basar (Serial aynasi /akis'e tasiyordu: "
       "ag dinleyen AP parolasini goruyordu)",
       bool(ns) and 'Serial.ham(ag_nvs.getString("ap_sifre"' in ns
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
    i_ag, i_guv = ino_k.find("ag_baslat();"), ino_k.find("guv_esp_ac();")
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
    ok("B72.F88 imza basliklari toplaniyor (X-Cihaz, X-Sayac, X-Imza, Content-Type) ve CORS "
       "on ucu izin veriyor",
       toplanan is not None and all(f'"{b}"' in toplanan.group(1)
                                    for b in ("X-Cihaz", "X-Sayac", "X-Imza", "Content-Type"))
       and "X-Cihaz" in govde(ino_k, "void onuc_sayfa("))


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
            try:
                IM.esles(taban, "PC", "kisa9chr!", dizin=d / "i8")
                kisa = "KABUL"
            except ValueError:
                kisa = "ret"
            ok("B72.I8 (son inceleme KRITIK) istemci sahte kartin dayattigi tur < 10 000 ya da asiri turu, "
               "bicimsiz kimligi (dosya adi) ve tuzu REDDEDER, kanit YOLLAMADAN; 10 karakterden kisa "
               "parola HICBIR istek atmadan reddedilir",
               all(v == "ret" for v in sonuclar.values()) and kanitsiz and kisa == "ret"
               and not kart.istekler and not (d / "i8").exists(), f"{sonuclar} kanitsiz={kanitsiz} kisa={kisa}")

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


BOLUMLER = [bolum_tablo, bolum_kaynak, bolum_esitle, bolum_guvenlik_py, bolum_guvenlik_kart,
            bolum_guvenlik_istemci]


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
        ("Gercek fis cekme (USB + PIL kapali)",
         "elle 5 kez: kurtarma hatasiz, kayit DEVAM ile surer, kayip en fazla "
         "son ~5 s"),
    ])
    print(f"\nB72: {gecti}/{gecti + kaldi} kosul gecti")
    return 0 if kaldi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
