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
       re.search(r'#define KAYIT_FW_SURUM\s+"A3-1C2"', esp_k) is not None)
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


def _sunucu(kart: _SahteKart):
    class Isleyici(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
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
            n = int(self.headers.get("Content-Length", "0"))
            govde = self.rfile.read(n).decode()
            if self.headers.get("X-Olcum") == "1" and self.headers.get("X-Jeton") == "abc123":
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


BOLUMLER = [bolum_tablo, bolum_kaynak, bolum_esitle]


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
