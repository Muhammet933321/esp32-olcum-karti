/* ═══════════════════════════════════════════════════════════════════════
   ag.h — WiFi DURUM MAKINESI  (B22.4)

   Once ev agina (STA) baglanmayi dener; 10 s'de olmazsa KENDI AGINI kurar
   (AP). Boylece "bilgisayar yoksa" senaryosu var olan bir altyapiya
   BAGIMLI DEGIL — sahada, yonlendirici olmadan da calisiyor.

   ── B22.4 ONCESI DURUM ────────────────────────────────────────────────
   `WIFI_AD = ""` sabit bosftu, yani `WiFi.begin()` HIC cagrilmiyordu:
   radyo acilmiyor, IP alinmiyordu. AP kipi ise dosyada hic yoktu. Yani
   kartin WiFi'si bugune kadar KULLANILMAMISTI.

   ── 🔴 NVS: AYRI ANAHTARLAR, `Ayar3`'E DOKUNULMUYOR ───────────────────
   Ag ayarlari `Ayar3` yapisina EKLENMEDI. Gerekce: `ayar_yukle`
   `n == sizeof(Ayar3)` denetimi yapiyor; yapi buyurse `AYAR3_IMZA`
   bumplanmak zorunda ve bu KALIBRASYONU SIFIRLAR. Bir WiFi parolasi
   degisikligi yeniden kalibrasyona mal olamaz. Ayri ad alani, ayri omur.

   ── 🔴 AP PAROLASI: MAC'TEN TURETILMIYOR ──────────────────────────────
   Ilk akla gelen "SSID'ye MAC son eki koy, parolayi da MAC'ten uret"
   HICBIR SEY KORUMAZ: SSID zaten beacon ile yayinlaniyor, yani MAC
   herkese acik. Bunun yerine ILK ACILISTA rastgele bir parola uretilip
   NVS'e yaziliyor ve seri konsola BASILIYOR. Kullanici WiFi'yi zaten
   seri konsoldan kuruyor (`Na`/`Np`), yani ek bir kulfet degil.
   `NA<parola>` ile degistirilebiliyor.
   ═══════════════════════════════════════════════════════════════════════ */
#ifndef AG_H
#define AG_H

#include <Arduino.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <esp_mac.h>          /* esp_read_mac — B26, asagiya bak */

#define AG_ALAN "olcumag"        /* NVS ad alani — "olcum3" DEGIL */
#define AG_MDNS "olcum"          /* http://olcum.local */
#define AG_STA_BEKLE_MS 10000u
/* AGD (5.12.109): acilista ev agi yoksa AP + STA'yi bu aralikla yeniden dene; baglaninca
   AP bu kadar daha acik kalir. Karar ag_karar.h'de (platformsuz, AVR'de sinaniyor).
   30 s: her deneme bir kanal taramasi (~2 s, AP o sirada kanal degistirir) — surekli
   tarama AP'yi kullanilamaz yapardi; tezgah olcutu "ag acildiktan <= 60 s'de STA". */
#define AG_STA_YENIDEN_MS 30000u
#define AG_AP_PAY_MS 5000u
/* Coklu ag (2026-10-06, tasarim/2026-10-06-coklu-ag.md): STA bu kadar kesik kalirsa AP + yeniden
   deneme (CA6; > olculen surucu donusu 7-14 s ve 5m'nin 60 s kopma senaryosu). "Bu aga gec":
   hedefe bu kadar, olmazsa onceki aga bu kadar (CA7). */
#define AG_STA_KOPUK_MS 90000u
#define AG_GECIS_MS 20000u

#include "ag_karar.h"
#include "ag_liste.h"           /* coklu ag (2026-10-06): kayitli aglar + aday secimi, platformsuz */

enum AgKip { AG_KAPALI = 0, AG_STA = 1, AG_AP = 2, AG_BAGLANIYOR = 3 };   /* 1E-2: 3 = STA bekleniyor */

struct AgDurum {
    uint8_t kip;
    char    ssid[33];
    char    ip[16];
    char    mac[18];        /* B26: arayuzun GERCEK MAC'i, surucu ayaga
                               kalktiktan SONRA okundu. SSID'in dogru
                               turetildigini sinamanin BAGIMSIZ olcutu. */
    bool    mdns;
};

static Preferences ag_nvs;
static AgDurum ag_durum = {AG_KAPALI, "", "", "", false};

/* W2 (alt proje 5 istegi): mDNS SERVIS duyurusu. Android `.local` adini guvenilir cozmez,
   NSD ile `_http._tcp` servisi tarar; TXT `kimlik` (16 onaltilik, /eslestir/bilgi'deki ayni
   deger) yanlis karti baglanmadan elemeye yarar — asil dogrulama yine eslesme/imza.
   Iki yol: AP'de MDNS.begin setup'ta (ag_baslat_rf), kimlik ise ondan SONRA (guv_esp_ac) gelir
   → ag_mdns_kimlik duyurur; STA'da MDNS.begin ag gorevinde, kimlik o anda zaten var →
   ag__mdns_servis duyurur. Bayrak tek duyuru icin; ag gorevi kimlik yazildiktan SONRA kurulur. */
static char ag_mdns_kim[17] = "";
static bool ag_mdns_servis_var = false;

static void ag__mdns_servis(void)
{
    if (!ag_durum.mdns || !ag_mdns_kim[0] || ag_mdns_servis_var) return;
    if (MDNS.addService("http", "tcp", 80)) {
        MDNS.addServiceTxt("http", "tcp", "kimlik", (const char *)ag_mdns_kim);
        ag_mdns_servis_var = true;
    }
}

static void ag_mdns_kimlik(const char kim[17])
{
    snprintf(ag_mdns_kim, sizeof(ag_mdns_kim), "%s", kim);
    ag__mdns_servis();
}

static void ag_rastgele_parola(char *hedef, uint8_t n)
{
    /* Karistirilmasi kolay karakterler (0/O, 1/l/I) BILEREK yok:
       kullanici bunu seri konsoldan okuyup telefona yazacak. */
    static const char ABC[] = "abcdefghjkmnpqrstuvwxyz23456789";
    for (uint8_t i = 0; i < n; i++) hedef[i] = ABC[esp_random() % (sizeof(ABC) - 1)];
    hedef[n] = 0;
}

/* ── COKLU AG (2026-10-06, tasarim/2026-10-06-coklu-ag.md) ───────────────
   NVS (CA1): w<i>a ad · w<i>p parola · w<i>o oncelik (i = 0..7) · w_son en son baglanilan.
   Liste RAM'de PAYLASILMAZ: her iki cekirdek de gerektiginde NVS'ten okur (komutlar
   cekirdek 1'de yazar, ag gorevi cekirdek 0'da okur) — ortak dizi, kilit, yaris yok.
   Parola yalniz begin() aninda okunur, hicbir ciktiya girmez (CA9). */
static void ag__anahtar(char *h, uint8_t i, char tur)
{
    h[0] = 'w'; h[1] = (char)('0' + i); h[2] = tur; h[3] = 0;
}

static void ag__liste_oku(AglKayit k[AGL_AZAMI])
{
    char h[4];
    for (uint8_t i = 0; i < AGL_AZAMI; i++) {
        memset(&k[i], 0, sizeof(k[i]));
        ag__anahtar(h, i, 'a');
        String ad = ag_nvs.getString(h, "");
        if (!agl_ad_gecerli(ad.c_str())) continue;
        snprintf(k[i].ad, sizeof(k[i].ad), "%s", ad.c_str());
        k[i].dolu = 1u;
        ag__anahtar(h, i, 'o');
        k[i].oncelik = ag_nvs.getUChar(h, 0) ? 1u : 0u;
    }
}

static String ag__parola(uint8_t i)
{
    char h[4];
    ag__anahtar(h, i, 'p');
    return ag_nvs.getString(h, "");
}

/* Cekirdek 1 -> 0 istekleri (tek yazar: komut cekirdegi; ag gorevi tuketir ve sifirlar) */
static volatile int8_t  ag_istek_gecis = -1;    /* Ng<i>: bu kayda gec */
static volatile uint8_t ag_istek_tara  = 0;     /* Nt: tara ve listeyi yayinla */
/* Cekirdek 0 -> 1 sonuclari: ag gorevi yazar, SURUM'u en son artirir; cekirdek 1 basar.
   ⚠ Tamponlar PSRAM'de (ag_yukle ayirir): statik DRAM %25 sinirinda (E6 notu) — burada
   statik ~740 B daha sinirin uzerine cikariyordu (2026-10-06 derlemede olculdu). */
#define AG_TARAMA_AZAMI 16u
#define AG_MESAJ 112u
struct AgCok {
    AglGorunen tarama[AG_TARAMA_AZAMI];
    char       mesaj[AG_MESAJ];
    char       gecis_ad[AGL_AD], geri_ad[AGL_AD];   /* GECIS/GERI'de karsilastirma (NVS'siz) */
};
static AgCok            *ag_c = nullptr;
static volatile uint8_t  ag_tarama_adet = 0;
static volatile uint8_t  ag_tarama_surum = 0;
static volatile uint8_t  ag_mesaj_surum = 0;

static void ag__mesaj(const char *m)
{
    if (!ag_c) return;
    snprintf(ag_c->mesaj, sizeof(ag_c->mesaj), "%s", m);
    __sync_synchronize();
    ag_mesaj_surum = (uint8_t)(ag_mesaj_surum + 1u);
}

static void ag_yukle(void)
{
    if (!ag_c) ag_c = (AgCok *)heap_caps_calloc(1, sizeof(AgCok), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!ag_c) ag_c = (AgCok *)calloc(1, sizeof(AgCok));          /* PSRAM yoksa dahili (yigin) */
    ag_nvs.begin(AG_ALAN, false);
    if (ag_nvs.getString("ap_sifre", "").length() < 8) {
        char p[13];
        ag_rastgele_parola(p, 12);
        ag_nvs.putString("ap_sifre", p);
    }
    /* CA2: TASIMA — eski tek kayit (wifi_ad/wifi_sifre) yuva 0'a; eski anahtarlar SILINMEZ
       (eski firmware'e donulurse de calisir). Bir kez: w0a yazilinca bir daha olmaz. */
    if (!ag_nvs.isKey("w0a")) {
        String ad = ag_nvs.getString("wifi_ad", "");
        if (agl_ad_gecerli(ad.c_str())) {
            ag_nvs.putString("w0p", ag_nvs.getString("wifi_sifre", ""));
            ag_nvs.putUChar("w0o", 0);
            ag_nvs.putString("w0a", ad);
            ag_nvs.putChar("w_son", 0);
        }
    }
}

/* 🔴 B26 (2026-09-11, GERCEK KARTTA bulundu) — SSID MAC'TEN GELMIYORDU.

   Eskiden burasi `WiFi.macAddress(m)` cagiriyordu. Ama `ag_baslat()`
   bu fonksiyonu `WiFi.mode()`'dan ONCE cagiriyor ve kayitli ev agi
   yokken (varsayilan durum) WiFi surucusu o ana kadar HIC baslamamis
   oluyor. `esp_wifi_get_mac` boyle bir durumda ESP_ERR_WIFI_NOT_INIT
   donup tampona DOKUNMUYOR, yani `m[6]` ILKLENMEMIS YIGIN BELLEGI
   olarak SSID'e giriyordu.

   Olculen: kartin gercek MAC'i ...:96:9c, yani SSID
   `OLCUM-KARTI-969C/969D` olmaliydi. Gorulen: firmware yazildiktan
   sonraki ilk acilista `OLCUM-KARTI-0400`, sonraki acilislarda hep
   `OLCUM-KARTI-ABAB` (AB AB = tekrarlayan dolgu bayti deseni).
   Deger SABIT kaldigi icin kusur "rastgele SSID" gibi gorunmuyor —
   ayni kod yolu ayni yigin icerigini biraktigindan deterministik
   cop uretiyor. Akis degisince (flash sonrasi) bir kez zaten degisti.

   NEDEN ONEMLI: B22'nin butun "telefondan, bilgisayarsiz kullan"
   hikayesi bu ada dayaniyor. Ad degistigi her seferde telefondaki ag
   profili kiriliyor ve 12 karakterlik AP parolasi elle yeniden
   giriliyor. Ayrica AP parolasini MAC'ten TURETMEME kararinin
   gerekcesi ("SSID zaten MAC son ekini yayinliyor") fiilen yanlisti.

   COZUM: `esp_read_mac()` eFuse'tan okur, WiFi surucusunun baslatilmis
   olmasini GEREKTIRMEZ ve hem STA hem AP yolunda ayni sonucu verir.
   ESP_MAC_WIFI_SOFTAP secildi cunku ad AP arayuzunu tanitiyor. */
static String ag_ap_ssid(void)
{
    uint8_t m[6] = {0};
    esp_read_mac(m, ESP_MAC_WIFI_SOFTAP);
    char s[24];
    snprintf(s, sizeof(s), "OLCUM-KARTI-%02X%02X", m[4], m[5]);
    return String(s);
}

/* ── 1E-2: KURULUM IKIYE BOLUNDU (2026-10-02) ───────────────────────────
   Eskiden `ag_baslat()` setup()'ta STA baglantisini 10 s'ye dek BEKLIYORDU: kartta
   olculdu, sifirlamadan ilk `D` satirina 5.7-7.2 s (ortalama 6.35 s); ev agi yoksa
   (AP'ye dusus) her acilista >10 s olcum yok. Simdi:
     ag_baslat_rf()     setup, cekirdek 1, KISA: radyoyu acar (WiFi.mode + begin —
                        guv_esp_ac'in rastgele sayilari RF ister, 1D) ya da kayitli ag
                        yoksa AP'yi hemen kurar. STA'da kip = AG_BAGLANIYOR.
     ag_bekle_tamamla() ag gorevi, cekirdek 0: baglantiyi bekler; olmazsa AP'ye duser.
                        Bitince `ag_hazir` = 1 (cekirdek 1 "Ag:" satirini basar).
   Alanlar (ssid/ip/mac/mdns) once doldurulur, `kip` EN SON yazilir: baska gorev
   AG_STA'yi gordugunde alanlar hazirdir.

   AGD: `ag_hazir` artik bir SURUM sayaci — her kip yazimi bir artirir; cekirdek 1
   "Ag:" satirini her degisimde (acilis AP -> sonra STA) bir kez basar. Sifir = kip
   henuz yazilmadi. */
static volatile uint8_t ag_hazir = 0;        /* kip surumu (0: kesinlesmedi) */
static AgKarar ag_k = {0, AGK_YOK};          /* AGD: yalniz ag gorevi (setup'ta kurulur) */

static void ag__kip_yaz(uint8_t k)
{
    __sync_synchronize();                    /* alanlar kip'ten ONCE gorunsun */
    ag_durum.kip = k;
    __sync_synchronize();
    ag_hazir = (uint8_t)(ag_hazir + 1u);     /* tek yazar: ag gorevi / setup (-Wvolatile: ++ degil) */
}

static uint8_t ag__ap_kur(wifi_mode_t kip);

/* Ag gorevinin (cekirdek 0) deneme durumu */
static int8_t ag_denenen = -1;          /* son begin() edilen kayit */
static int8_t ag_son_basarisiz = -1;    /* CA4: onceki denemede baglanamayan */
static int8_t ag_tercih = -1;           /* CA7: AP'deyken istenen gecis -> sonraki deneme bu kayit */
static int8_t ag_gecis_hedef = -1, ag_gecis_onceki = -1;
static uint8_t ag_tarama_neden = 0;     /* 1 deneme · 2 kullanici (Nt) · 4 gecis */

/* kayda begin (parola NVS'ten, yalniz bu an) */
static void ag__begin(const AglKayit k[AGL_AZAMI], int8_t i)
{
    String sifre = ag__parola((uint8_t)i);
    WiFi.begin(k[i].ad, sifre.c_str());
    ag_denenen = i;
}

/* setup: radyoyu ac. Donus: kip (STA'da AG_BAGLANIYOR — sonucu gorev verir). */
static uint8_t ag_baslat_rf(void)
{
    AglKayit k[AGL_AZAMI];
    ag__liste_oku(k);
    const uint8_t n = agl_adet(k);
    agk_kur(&ag_k, n ? 1u : 0u, millis());
    if (n) {
        /* taramasiz ilk tahmin (setup kisa kalir, 1E-2): en son baglanilan > oncelikli > ilk */
        const int8_t i = agl_ilk(k, ag_nvs.getChar("w_son", -1));
        /* DHCP cihaz adi (2026-10-06, kullanici: telefon hotspotunda "bilinmiyor" / "esp32s3-..."
           gorunuyordu): kartin KENDI AGININ adi (OLCUM-KARTI-XXXX, MAC'ten) — ayni kart her yerde
           ayni adla. setHostname WiFi.mode()'dan ONCE (surucu baslamadan; sonra yok sayilir). */
        WiFi.setHostname(ag_ap_ssid().c_str());
        WiFi.mode(WIFI_STA);
        ag__begin(k, i);
        snprintf(ag_durum.ssid, sizeof(ag_durum.ssid), "%s", k[i].ad);
        ag_durum.kip = AG_BAGLANIYOR;
        return AG_BAGLANIYOR;
    }
    return ag__ap_kur(WIFI_AP);   /* bekleme yok: AP hemen kurulur; ev agi yok -> deneme de yok */
}

/* AGD: STA baglandi (acilista ya da AP'deyken yeniden denemede). */
static void ag__sta_oldu(void)
{
    /* calisirken kopma: surucu kendisi doner (5.12.106'da olculen yol) — AP'deyken kapatilmisti */
    WiFi.setAutoReconnect(true);
    snprintf(ag_durum.ssid, sizeof(ag_durum.ssid), "%s", WiFi.SSID().c_str());
    snprintf(ag_durum.ip, sizeof(ag_durum.ip), "%s",
             WiFi.localIP().toString().c_str());
    /* B26: surucu AYAKTA, bu MAC gercek. */
    snprintf(ag_durum.mac, sizeof(ag_durum.mac), "%s",
             WiFi.macAddress().c_str());
    /* mDNS AP'de kurulduysa SURUYOR: IDF mdns'in on tanimli arayuz isleyicisi
       (CONFIG_MDNS_PREDEF_NETIF_STA/AP) STA IP alinca STA'da, AP kapaninca AP'de
       acar/kapatir; servisler arayuzden bagimsiz. MDNS.end() HIC cagrilmaz — servis
       bayragi (ag_mdns_servis_var) bu yuzden gecerli kalir. AP'de basarisizsa burada
       yeniden denenir (bayrak o durumda zaten 0). */
    if (!ag_durum.mdns) ag_durum.mdns = MDNS.begin(AG_MDNS);
    ag__mdns_servis();
    /* coklu ag: hangi kayit baglandi — sonraki acilisin ilk tahmini (w_son), donus sifirlanir */
    {
        AglKayit k[AGL_AZAMI];
        ag__liste_oku(k);
        const int8_t i = agl_bul(k, ag_durum.ssid);
        if (i >= 0 && ag_nvs.getChar("w_son", -1) != i) ag_nvs.putChar("w_son", i);
        ag_son_basarisiz = -1;
        ag_tercih = -1;
    }
    ag__kip_yaz(AG_STA);
}

/* GECIS/GERI'de `bagli` = HEDEF aga bagli (eski baglanti sayilmaz). Her turda cagrilir:
   NVS okumaz (ad gecis basinda kopyalandi); SSID yalniz WL_CONNECTED iken sorulur. */
static uint8_t ag__hedefte(const char *ad)
{
    if (!ad || !ad[0] || WiFi.status() != WL_CONNECTED) return 0;
    return strcmp(WiFi.SSID().c_str(), ad) == 0;
}

/* yeniden deneme (CA4/CA5): tek kayitta surucudeki yapilandirma (eski yol, AP'ye dokunmaz);
   birden cokta TARAMA baslat — sonucu ag__tarama_isle secer ve begin eder. Bloklamaz. */
static void ag__sta_dene(void)
{
    AglKayit k[AGL_AZAMI];
    ag__liste_oku(k);
    if (ag_denenen >= 0) ag_son_basarisiz = ag_denenen;   /* bir onceki deneme olmadi */
    if (agl_adet(k) <= 1u && ag_tercih < 0) {
        WiFi.begin();                 /* surucudeki yapilandirma; bloklamaz, AP'ye dokunmaz */
        return;
    }
    if (!ag_tarama_neden) WiFi.scanNetworks(true);
    ag_tarama_neden = (uint8_t)(ag_tarama_neden | 1u);
}

/* AGD: karar motorunun eylemini uygula (yalniz ag gorevi, cekirdek 0). */
static void ag__uygula(uint8_t e)
{
    if (e == AGE_STA_OLDU) {
        ag__sta_oldu();
    } else if (e == AGE_AP_KUR) {
        /* Eskiden WiFi.disconnect(true): radyo kapanir, STA BIR DAHA denenmezdi.
           Simdi AP+STA: STA yapilandirmasi surucude kalir. Otomatik yeniden baglanma
           KAPALI — NO_AP_FOUND'da surucu araliksiz tarardi (AP her taramada kanal
           degistirir); denemeyi AG_STA_YENIDEN_MS'de bir biz yapiyoruz. */
        WiFi.setAutoReconnect(false);
        WiFi.disconnect(false, false);
        (void)ag__ap_kur(WIFI_AP_STA);
    } else if (e == AGE_STA_DENE) {
        ag__sta_dene();               /* tek kayit: WiFi.begin() (eski yol); coklu: tarama */
    } else if (e == AGE_GERI) {
        /* CA7: hedefe gecilemedi — ONCEKI aga don */
        AglKayit k[AGL_AZAMI];
        ag__liste_oku(k);
        char m[112];
        if (ag_gecis_onceki >= 0 && k[ag_gecis_onceki].dolu) {
            WiFi.disconnect(false, false);
            ag__begin(k, ag_gecis_onceki);
            snprintf(m, sizeof(m), "! ag: gecis olmadi — %s agina donuluyor", k[ag_gecis_onceki].ad);
        } else {
            snprintf(m, sizeof(m), "! ag: gecis olmadi — onceki ag kayitli degil");
        }
        ag__mesaj(m);
    } else if (e == AGE_AP_KAPAT) {
        WiFi.mode(WIFI_STA);          /* softAP kapanir; STA, sunucu ve mDNS surer */
    }
}

/* ag gorevi (cekirdek 0), sunucu dongusunden ONCE: STA'yi bekle, olmazsa AP (+ deneme). */
static void ag_bekle_tamamla(void)
{
    if (ag_durum.kip != AG_BAGLANIYOR) { if (!ag_hazir) ag_hazir = 1; return; }
    /* CA5: birden cok kayitli ag — setup'in ilk tahmini (en son baglanilan) gorunmuyorsa TARA
       ve en iyi adaya gec (bloklayan tarama burada: cekirdek 0, sunucu dongusunden ONCE) */
    {
        AglKayit k[AGL_AZAMI];
        ag__liste_oku(k);
        if (agl_adet(k) > 1u) {
            const int16_t n = WiFi.scanNetworks(false);
            AglGorunen g[AG_TARAMA_AZAMI];
            uint8_t gn = 0;
            for (int16_t j = 0; j < n && gn < AG_TARAMA_AZAMI; j++) {
                String a = WiFi.SSID((uint8_t)j);
                if (!agl_ad_gecerli(a.c_str())) continue;
                snprintf(g[gn].ad, sizeof(g[gn].ad), "%s", a.c_str());
                g[gn].rssi = (int8_t)WiFi.RSSI((uint8_t)j);
                gn++;
            }
            WiFi.scanDelete();
            const int8_t i = agl_sec(k, g, gn, -1);
            if (i >= 0 && i != ag_denenen && WiFi.status() != WL_CONNECTED) {
                ag__begin(k, i);
                snprintf(ag_durum.ssid, sizeof(ag_durum.ssid), "%s", k[i].ad);
            }
        }
    }
    while (ag_k.evre == AGK_BEKLE) {
        ag__uygula(agk_adim(&ag_k, millis(), WiFi.status() == WL_CONNECTED, 0u));
        if (ag_k.evre == AGK_BEKLE) vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* AGD: ag gorevinin dongusunden her tur — AP'deyken STA'yi yeniden dener, baglaninca
   pay suresinden sonra AP'yi kapatir. Etkin degilse surucuyu HIC sorgulamaz. */
/* async tarama bitti mi: sonucu nedenine gore kullan (deneme / Nt / gecis) */
static void ag__tarama_isle(void)
{
    if (!ag_tarama_neden) return;
    const int16_t n = WiFi.scanComplete();
    if (n == -1) return;                                   /* WIFI_SCAN_RUNNING */
    AglGorunen g[AG_TARAMA_AZAMI];
    uint8_t gn = 0;
    for (int16_t j = 0; j < n && gn < AG_TARAMA_AZAMI; j++) {
        String a = WiFi.SSID((uint8_t)j);
        if (!agl_ad_gecerli(a.c_str())) continue;           /* gizli ag (bos ad) */
        snprintf(g[gn].ad, sizeof(g[gn].ad), "%s", a.c_str());
        g[gn].rssi = (int8_t)WiFi.RSSI((uint8_t)j);
        gn++;
    }
    WiFi.scanDelete();
    const uint8_t neden = ag_tarama_neden;
    ag_tarama_neden = 0;
    AglKayit k[AGL_AZAMI];
    ag__liste_oku(k);
    if ((neden & 2u) && ag_c) {                            /* Nt: cekirdek 1 basar */
        memcpy(ag_c->tarama, g, sizeof(AglGorunen) * gn);
        ag_tarama_adet = gn;
        __sync_synchronize();
        ag_tarama_surum = (uint8_t)(ag_tarama_surum + 1u);
    }
    if (neden & 4u) {                                      /* CA7: gorunuyorsa gec */
        const int8_t h = ag_gecis_hedef;
        char m[112];
        if (h >= 0 && k[h].dolu && agl_gorunur(g, gn, k[h].ad, nullptr) && ag_k.evre == AGK_STA) {
            ag_gecis_onceki = agl_bul(k, ag_durum.ssid);
            if (ag_c) {
                snprintf(ag_c->gecis_ad, sizeof(ag_c->gecis_ad), "%s", k[h].ad);
                snprintf(ag_c->geri_ad, sizeof(ag_c->geri_ad), "%s",
                         ag_gecis_onceki >= 0 ? k[ag_gecis_onceki].ad : "");
            }
            WiFi.disconnect(false, false);
            ag__begin(k, h);
            (void)agk_gecis(&ag_k, millis());
            snprintf(m, sizeof(m), "* ag: %s deneniyor — %u s'de olmazsa onceki aga donulur",
                     k[h].ad, (unsigned)(AG_GECIS_MS / 1000u));
        } else {
            snprintf(m, sizeof(m), "! ag: %s gorunmuyor — baglanti degismedi", h >= 0 ? k[h].ad : "?");
            ag_gecis_hedef = -1;
        }
        ag__mesaj(m);
    }
    if (neden & 1u) {                                      /* CA4/CA7: deneme — tercih, yoksa donuslu */
        int8_t i = -1;
        if (ag_tercih >= 0 && k[ag_tercih].dolu && agl_gorunur(g, gn, k[ag_tercih].ad, nullptr)) i = ag_tercih;
        if (i < 0) i = agl_sec(k, g, gn, ag_son_basarisiz);
        if (i >= 0) ag__begin(k, i);
        else ag_denenen = -1;                              /* hicbiri gorunmuyor: AP surer */
    }
}

/* cekirdek 1'in istekleri (Nt / Ng) */
static void ag__istekler(void)
{
    if (ag_istek_tara) {
        ag_istek_tara = 0;
        if (!ag_tarama_neden) WiFi.scanNetworks(true);
        ag_tarama_neden = (uint8_t)(ag_tarama_neden | 2u);
    }
    const int8_t g = ag_istek_gecis;
    if (g >= 0) {
        ag_istek_gecis = -1;
        if (ag_k.evre == AGK_STA) {                         /* once TARA: gorunmuyorsa ayrilma */
            ag_gecis_hedef = g;
            if (!ag_tarama_neden) WiFi.scanNetworks(true);
            ag_tarama_neden = (uint8_t)(ag_tarama_neden | 4u);
        } else if (agk_etkin(&ag_k)) {                      /* AP'de: sonraki deneme bu kayit */
            ag_tercih = g;
            ag__mesaj("* ag: kart su an kendi aginda — istenen ag sonraki denemede (<= 30 s)");
        }
    }
}

static void ag_isle(void)
{
    ag__istekler();
    ag__tarama_isle();
    if (!agk_etkin(&ag_k)) return;
    const uint8_t gecis = ag_k.evre == AGK_GECIS || ag_k.evre == AGK_GERI;
    const uint8_t bagli = gecis ? ag__hedefte(!ag_c ? nullptr : ag_k.evre == AGK_GECIS ? ag_c->gecis_ad
                                                                                       : ag_c->geri_ad)
                                : (WiFi.status() == WL_CONNECTED ? 1u : 0u);
    const uint8_t onceki = ag_k.evre;
    const uint8_t e = agk_adim(&ag_k, millis(), bagli, WiFi.STA.connected() ? 1u : 0u);
    ag__uygula(e);
    if (e == AGE_STA_OLDU && onceki == AGK_GECIS) {
        char m[112];
        snprintf(m, sizeof(m), "* ag: %s agina gecildi — IP %s", ag_durum.ssid, ag_durum.ip);
        ag__mesaj(m);
    } else if (e == AGE_AP_KUR && onceki == AGK_GERI) {
        ag__mesaj("! ag: onceki ag da olmadi — kendi agi acildi, kayitli aglar 30 s'de bir deneniyor");
    }
    if (e == AGE_STA_OLDU || e == AGE_AP_KUR) {
        ag_gecis_hedef = ag_gecis_onceki = -1;
        if (ag_c) ag_c->gecis_ad[0] = ag_c->geri_ad[0] = 0;
    }
}

/* STA olmadi (ya da hic kurulmadi) -> KENDI AGIN. Kipi ag__kip_yaz ile kesinlestirir.
   AGD: `kip` WIFI_AP (ev agi kayitli degil) ya da WIFI_AP_STA (ev agi yeniden denenecek). */
static uint8_t ag__ap_kur(wifi_mode_t kip)
{
    String ap = ag_ap_ssid();
    String aps = ag_nvs.getString("ap_sifre", "");
    WiFi.mode(kip);
    bool ok = WiFi.softAP(ap.c_str(), aps.c_str());
    snprintf(ag_durum.ssid, sizeof(ag_durum.ssid), "%s", ap.c_str());
    snprintf(ag_durum.ip, sizeof(ag_durum.ip), "%s",
             WiFi.softAPIP().toString().c_str());
    /* 🔴 B26: SSID'i DOGRULAYAN BAGIMSIZ OLCUT. Bu satir softAP AYAGA
       KALKTIKTAN SONRA calisiyor, yani buradaki MAC her halukarda
       gercek. SSID ise ag_ap_ssid()'den geliyor. Ikisi ayrisirsa ad
       yanlis turetilmis demektir — tezgah kosucusu tam bunu siniyor.
       Ayni kaynaktan okusaydi test totoloji olurdu ve eski kusuru
       YAKALAYAMAZDI. */
    snprintf(ag_durum.mac, sizeof(ag_durum.mac), "%s",
             WiFi.softAPmacAddress().c_str());
    ag_durum.mdns = ok && MDNS.begin(AG_MDNS);
    ag__mdns_servis();
    ag__kip_yaz(ok ? AG_AP : AG_KAPALI);
    return ok ? AG_AP : AG_KAPALI;
}

static const char *ag_kip_adi(uint8_t k)
{
    return k == AG_STA ? "STA (ev agi)" : (k == AG_AP ? "AP (kendi agi)"
         : (k == AG_BAGLANIYOR ? "BAGLANIYOR (ev agi bekleniyor)" : "KAPALI"));
}

#endif /* AG_H */
