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

enum AgKip { AG_KAPALI = 0, AG_STA = 1, AG_AP = 2 };

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

/* Kullaniciya gorunen tek kurulum yolu. Donus: kip. */
static uint8_t ag_baslat(void)
{
    String ad = ag_nvs.getString("wifi_ad", "");
    String sifre = ag_nvs.getString("wifi_sifre", "");

    if (ad.length()) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ad.c_str(), sifre.c_str());
        uint32_t son = millis() + AG_STA_BEKLE_MS;
        while (WiFi.status() != WL_CONNECTED && (int32_t)(millis() - son) < 0) {
            delay(200);
        }
        if (WiFi.status() == WL_CONNECTED) {
            ag_durum.kip = AG_STA;
            snprintf(ag_durum.ssid, sizeof(ag_durum.ssid), "%s", ad.c_str());
            snprintf(ag_durum.ip, sizeof(ag_durum.ip), "%s",
                     WiFi.localIP().toString().c_str());
            /* B26: surucu AYAKTA, bu MAC gercek. */
            snprintf(ag_durum.mac, sizeof(ag_durum.mac), "%s",
                     WiFi.macAddress().c_str());
            ag_durum.mdns = MDNS.begin(AG_MDNS);
            return AG_STA;
        }
        WiFi.disconnect(true);
    }

    /* STA olmadi (ya da hic kurulmadi) -> KENDI AGIN. */
    String ap = ag_ap_ssid();
    String aps = ag_nvs.getString("ap_sifre", "");
    WiFi.mode(WIFI_AP);
    bool ok = WiFi.softAP(ap.c_str(), aps.c_str());
    ag_durum.kip = ok ? AG_AP : AG_KAPALI;
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
    return ag_durum.kip;
}

static const char *ag_kip_adi(uint8_t k)
{
    return k == AG_STA ? "STA (ev agi)" : (k == AG_AP ? "AP (kendi agi)" : "KAPALI");
}

#endif /* AG_H */
