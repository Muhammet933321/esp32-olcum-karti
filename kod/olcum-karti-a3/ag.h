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

#include "ag_karar.h"

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

static void ag_yukle(void)
{
    ag_nvs.begin(AG_ALAN, false);
    if (ag_nvs.getString("ap_sifre", "").length() < 8) {
        char p[13];
        ag_rastgele_parola(p, 12);
        ag_nvs.putString("ap_sifre", p);
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

/* setup: radyoyu ac. Donus: kip (STA'da AG_BAGLANIYOR — sonucu gorev verir). */
static uint8_t ag_baslat_rf(void)
{
    String ad = ag_nvs.getString("wifi_ad", "");
    String sifre = ag_nvs.getString("wifi_sifre", "");
    agk_kur(&ag_k, ad.length() ? 1u : 0u, millis());
    if (ad.length()) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ad.c_str(), sifre.c_str());
        snprintf(ag_durum.ssid, sizeof(ag_durum.ssid), "%s", ad.c_str());
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
    ag__kip_yaz(AG_STA);
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
        WiFi.begin();                 /* surucudeki yapilandirma; bloklamaz, AP'ye dokunmaz */
    } else if (e == AGE_AP_KAPAT) {
        WiFi.mode(WIFI_STA);          /* softAP kapanir; STA, sunucu ve mDNS surer */
    }
}

/* ag gorevi (cekirdek 0), sunucu dongusunden ONCE: STA'yi bekle, olmazsa AP (+ deneme). */
static void ag_bekle_tamamla(void)
{
    if (ag_durum.kip != AG_BAGLANIYOR) { if (!ag_hazir) ag_hazir = 1; return; }
    while (ag_k.evre == AGK_BEKLE) {
        ag__uygula(agk_adim(&ag_k, millis(), WiFi.status() == WL_CONNECTED, 0u));
        if (ag_k.evre == AGK_BEKLE) vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* AGD: ag gorevinin dongusunden her tur — AP'deyken STA'yi yeniden dener, baglaninca
   pay suresinden sonra AP'yi kapatir. Etkin degilse surucuyu HIC sorgulamaz. */
static void ag_isle(void)
{
    if (!agk_etkin(&ag_k)) return;
    ag__uygula(agk_adim(&ag_k, millis(), WiFi.status() == WL_CONNECTED,
                        WiFi.STA.connected() ? 1u : 0u));
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
