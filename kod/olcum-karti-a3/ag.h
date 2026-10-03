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
   AG_STA'yi gordugunde alanlar hazirdir. */
static volatile uint8_t ag_hazir = 0;        /* kip kesinlesti (STA / AP / KAPALI) */
static uint32_t ag_bas_ms = 0;

static void ag__kip_yaz(uint8_t k)
{
    __sync_synchronize();                    /* alanlar kip'ten ONCE gorunsun */
    ag_durum.kip = k;
    __sync_synchronize();
    ag_hazir = 1;
}

static uint8_t ag__ap_kur(void);

/* setup: radyoyu ac. Donus: kip (STA'da AG_BAGLANIYOR — sonucu gorev verir). */
static uint8_t ag_baslat_rf(void)
{
    String ad = ag_nvs.getString("wifi_ad", "");
    String sifre = ag_nvs.getString("wifi_sifre", "");
    if (ad.length()) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ad.c_str(), sifre.c_str());
        snprintf(ag_durum.ssid, sizeof(ag_durum.ssid), "%s", ad.c_str());
        ag_bas_ms = millis();
        ag_durum.kip = AG_BAGLANIYOR;
        return AG_BAGLANIYOR;
    }
    return ag__ap_kur();       /* bekleme yok: AP hemen kurulur */
}

/* ag gorevi (cekirdek 0), sunucu dongusunden ONCE: STA'yi bekle, olmazsa AP. */
static void ag_bekle_tamamla(void)
{
    if (ag_durum.kip != AG_BAGLANIYOR) { ag_hazir = 1; return; }
    while (WiFi.status() != WL_CONNECTED
           && (int32_t)(millis() - (ag_bas_ms + AG_STA_BEKLE_MS)) < 0)
        vTaskDelay(pdMS_TO_TICKS(100));
    if (WiFi.status() == WL_CONNECTED) {
        snprintf(ag_durum.ip, sizeof(ag_durum.ip), "%s",
                 WiFi.localIP().toString().c_str());
        /* B26: surucu AYAKTA, bu MAC gercek. */
        snprintf(ag_durum.mac, sizeof(ag_durum.mac), "%s",
                 WiFi.macAddress().c_str());
        ag_durum.mdns = MDNS.begin(AG_MDNS);
        ag__mdns_servis();
        ag__kip_yaz(AG_STA);
        return;
    }
    WiFi.disconnect(true);
    (void)ag__ap_kur();
}

/* STA olmadi (ya da hic kurulmadi) -> KENDI AGIN. Kipi ag__kip_yaz ile kesinlestirir. */
static uint8_t ag__ap_kur(void)
{
    String ap = ag_ap_ssid();
    String aps = ag_nvs.getString("ap_sifre", "");
    WiFi.mode(WIFI_AP);
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
