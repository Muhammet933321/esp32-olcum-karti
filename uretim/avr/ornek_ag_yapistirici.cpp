/*
 * AGD inceleme — kartin AG YAPISTIRICISININ AVR'de DAVRANISI (sim3_web.py 5m).
 *
 * 5m'nin AVR bolumu yalniz karar motorunu (ag_karar.h) sinar; ag.h'deki
 * yapistiriciyi alt dizeyle arardi. Inceleme iki mutant buldu, ikisinde de
 * B22b 144/144 yesil kaldi:
 *   - ag__sta_oldu `WiFi.localIP()` yerine `WiFi.softAPIP()` yazar
 *     -> kip STA ama ag_durum.ip = AP adresi (IP ile gelen istek 403);
 *   - ag_isle `bagli` ile `iliskili`yi yer degistirir
 *     -> kip STA, DHCP bitmeden (ip 0.0.0.0) yazilir.
 *
 * Burada kosan kod kartin METNI: sim3_web.py ag.h'den `ag_baslat_rf`,
 * `ag__sta_oldu`, `ag__uygula`, `ag_bekle_tamamla`, `ag_isle`, `ag__ap_kur`
 * (+ kullandiklari tanimlar) oldugu gibi kesip `ag_yapistirici.h`ye yaziyor.
 * Karar motoru ag_karar.h'nin kendisi.
 *
 * Bu dosyadaki ince katman yalniz yapistiricinin kullandigi kadar: String,
 * WiFi, MDNS, Preferences, millis/vTaskDelay. Surucu modeli (`dunya`):
 *   - begin() bir deneme baslatir; ag varsa 300 ms sonra ILISKI kurulur
 *     (`WiFi.STA.connected()`), 2000 ms sonra IP gelir. `WiFi.status()`
 *     WL_CONNECTED'i YALNIZ IP'den sonra verir — cekirdek 3.3.11 STA.cpp,
 *     ARDUINO_EVENT_WIFI_STA_GOT_IP'de `_setStatus(WL_CONNECTED)`.
 *   - ag yoksa deneme duser; otomatik baglanma aciksa surucu 300 ms'de bir
 *     yeniden dener (calisirken kopma: 5.12.106'da olculen kendiliginden donus).
 *   - bagliyken argumansiz begin() iliskiyi KOPARMAZ (inceleme notu).
 *   - STA kipi kapaliysa (WIFI_AP) iliski/IP yok.
 * Senaryolar `ag_yap_vektor.h`de (sim3_web.py uretir). Zaman yalniz harness
 * (100 ms'lik ag gorevi turu) ve vTaskDelay ile ilerler: deterministik.
 *
 * Cikti:  M <i> <ms> <kip>                 WiFi.mode cagrisi (1 STA, 2 AP, 3 AP+STA)
 *         B <i> <ms>                       WiFi.begin cagrisi (argumanli ya da degil)
 *         P <i> <ms>                       WiFi.softAP cagrisi
 *         K <i> <ms> <surum> <kip> <ip>    ag_hazir (kip surumu) degisti
 *         S <i> <kip> <ip> <mod> <ipvar> <mdns> <servis>   senaryo sonu
 *         BITTI
 */
#include <avr/io.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* ── UART ──────────────────────────────────────────────────────────── */
static void uart_baslat(void)
{
    UBRR0H = 0;
    UBRR0L = 16;
    UCSR0A = (1 << U2X0);
    UCSR0B = (1 << TXEN0);
    UCSR0C = (3 << UCSZ00);
}
static void yaz(char c)
{
    while (!(UCSR0A & (1 << UDRE0))) {}
    UDR0 = c;
}
static void metin(const char *s) { while (*s) yaz(*s++); }
static void sayi(uint32_t v)
{
    char b[11];
    uint8_t n = 0;
    do { b[n++] = (char)('0' + (uint8_t)(v % 10u)); v /= 10u; } while (v);
    while (n) yaz(b[--n]);
}

/* ── ince Arduino katmani ──────────────────────────────────────────── */
class String {
 public:
    enum { KAP = 24 };
    String() { b_[0] = 0; }
    String(const char *s) { b_[0] = 0; ekle(s); }
    String(const String &o) { b_[0] = 0; ekle(o.b_); }
    String &operator=(const String &o) { if (this != &o) { b_[0] = 0; ekle(o.b_); } return *this; }
    const char *c_str() const { return b_; }
    unsigned int length() const { return (unsigned int)strlen(b_); }

 private:
    void ekle(const char *s) { strncat(b_, s, KAP - 1 - strlen(b_)); }
    char b_[KAP];
};

typedef enum { WIFI_MODE_NULL = 0, WIFI_STA = 1, WIFI_AP = 2, WIFI_AP_STA = 3 } wifi_mode_t;
enum { WL_IDLE_STATUS = 0, WL_DISCONNECTED = 6, WL_CONNECTED = 3 };
#define pdMS_TO_TICKS(x) (x)
#define __sync_synchronize() ((void)0)

#include "ag_yap_vektor.h"

static const Senaryo *g_s;
static uint8_t  g_i;
static uint32_t g_t;               /* simdi (ms) */
static uint8_t  g_mod;             /* WiFi.mode */
static bool     g_oto, g_deniyor, g_iliski, g_ip;
static uint32_t g_dt, g_it;        /* deneme / iliski ani */

static bool ag_var(uint32_t t)
{
    return (t >= g_s->a1 && t < g_s->a1s) || (t >= g_s->a2 && t < g_s->a2s);
}

static void dunya(void)
{
    const uint32_t t = g_t;
    if (!(g_mod & WIFI_STA)) { g_deniyor = g_iliski = g_ip = false; return; }
    if (g_iliski && !ag_var(t)) {
        g_iliski = g_ip = false;
        if (g_oto) { g_deniyor = true; g_dt = t; }
    }
    if (g_deniyor && !g_iliski && t - g_dt >= 300u) {
        if (ag_var(t)) { g_iliski = true; g_it = t; g_deniyor = false; }
        else if (g_oto) g_dt = t;
        else g_deniyor = false;
    }
    if (g_iliski && !g_ip && t - g_it >= 2000u) g_ip = true;
}

static void olay(const char *k)
{
    metin(k); metin(" "); sayi(g_i); metin(" "); sayi(g_t);
}

static uint32_t millis(void) { return g_t; }
static void vTaskDelay(uint32_t ms) { g_t += ms; }

class IPAddress {
 public:
    explicit IPAddress(const char *s) : s_(s) {}
    String toString() const { return String(s_); }

 private:
    const char *s_;
};

class StaArayuz {
 public:
    bool connected() { dunya(); return g_iliski; }
};

class SahteWiFi {
 public:
    StaArayuz STA;
    int status() { dunya(); return g_ip ? WL_CONNECTED : WL_DISCONNECTED; }
    void mode(wifi_mode_t m) { g_mod = (uint8_t)m; olay("M"); metin(" "); sayi(g_mod); metin("\r\n"); dunya(); }
    int begin(const char *, const char *) { return begin(); }
    int begin(void)
    {
        olay("B"); metin("\r\n");
        dunya();
        if ((g_mod & WIFI_STA) && !g_iliski) { g_deniyor = true; g_dt = g_t; }
        return 0;
    }
    bool softAP(const char *, const char *) { olay("P"); metin("\r\n"); return (g_mod & WIFI_AP) != 0; }
    void setAutoReconnect(bool b) { g_oto = b; }
    bool disconnect(bool, bool) { g_deniyor = g_iliski = g_ip = false; return true; }
    IPAddress localIP() { dunya(); return IPAddress(g_ip ? "192.0.2.57" : "0.0.0.0"); }
    IPAddress softAPIP() { return IPAddress((g_mod & WIFI_AP) ? "192.168.4.1" : "0.0.0.0"); }
    String SSID() { dunya(); return String(g_iliski ? "sinama-agi" : ""); }
    String macAddress() { return String("02:00:00:00:00:01"); }
    String softAPmacAddress() { return String("02:00:00:00:00:02"); }
};
static SahteWiFi WiFi;

static uint8_t g_mdns_bas, g_servis;
class SahteMDNS {
 public:
    bool begin(const char *) { g_mdns_bas++; return true; }
    bool addService(const char *, const char *, uint16_t) { g_servis++; return true; }
    bool addServiceTxt(const char *, const char *, const char *, const char *) { return true; }
};
static SahteMDNS MDNS;

class SahtePreferences {
 public:
    String getString(const char *a, const char *) { return String(strcmp(a, "wifi_ad") == 0 && g_s->kimlik ? "sinama-agi" : ""); }
};
static SahtePreferences ag_nvs;

static String ag_ap_ssid(void) { return String("OLCUM-KARTI-0102"); }

#include "ag_yapistirici.h"     /* kartin METNI (ag.h'den kesilmis) */

/* ── kosu ──────────────────────────────────────────────────────────── */
static uint8_t g_surum;

static void kip_bak(void)
{
    if (ag_hazir == g_surum) return;
    g_surum = ag_hazir;
    olay("K"); metin(" "); sayi(g_surum); metin(" "); sayi(ag_durum.kip); metin(" ");
    metin(ag_durum.ip[0] ? ag_durum.ip : "-"); metin("\r\n");
}

int main(void)
{
    uart_baslat();
    for (g_i = 0; g_i < SEN_ADET; g_i++) {
        g_s = &SEN[g_i];
        g_t = 0; g_mod = 0; g_oto = true; g_deniyor = g_iliski = g_ip = false; g_dt = g_it = 0;
        g_mdns_bas = g_servis = 0; g_surum = 0;
        memset(&ag_durum, 0, sizeof(ag_durum));
        ag_hazir = 0; ag_k.t = 0; ag_k.evre = AGK_YOK;
        strcpy(ag_mdns_kim, "0123456789abcdef"); ag_mdns_servis_var = false;

        (void)ag_baslat_rf();          /* setup */
        kip_bak();
        ag_bekle_tamamla();            /* ag gorevi, sunucu dongusunden once */
        kip_bak();
        while (g_t < g_s->son) {       /* ag gorevi dongusu: 100 ms'lik tur */
            g_t += 100u;
            ag_isle();
            kip_bak();
        }
        dunya();
        metin("S "); sayi(g_i); metin(" "); sayi(ag_durum.kip); metin(" ");
        metin(ag_durum.ip[0] ? ag_durum.ip : "-"); metin(" "); sayi(g_mod); metin(" ");
        sayi(g_ip); metin(" "); sayi(ag_durum.mdns); metin(" "); sayi(g_servis); metin("\r\n");
    }
    metin("BITTI\r\n");
    for (;;) {}
}
