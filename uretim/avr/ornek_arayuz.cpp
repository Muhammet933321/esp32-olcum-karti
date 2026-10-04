/*
 * W6 inceleme — kartin panel dosyasi isleyicisinin AVR'de DAVRANISI (sim3_web.py 6r).
 *
 * W6'dan beri `.gz`e dusus ve MIME secimi cekirdegin StaticRequestHandler'inda
 * DEGIL, firmware'in kendi `ArayuzIsleyici` + `arayuz_tur`unda. 6n bunlari alt
 * dizeyle ariyordu: `exists(yol + ".gz")` -> `exists(yol)` ya da `endsWith` ->
 * `startsWith` tek belirtecle paneli olduruyor, 6n yesil kaliyordu.
 *
 * Burada kosan kod kartin METNI: sim3_web.py `.ino`dan `arayuz_tur` ve
 * `class ArayuzIsleyici`yi oldugu gibi kesip `arayuz_kaynak.h`ye yaziyor.
 * MIME tablosu cekirdegin KENDI `mimetable.h/.cpp`si (ayni kurulu surum),
 * dosya sistemi goruntunun GERCEK dosya listesi (`_fs.json`), isleyiciler
 * `setup()`taki kayit sirasiyla (`arayuz_vektor.h`, her kosuda uretiliyor).
 *
 * Bu dosyadaki ince katman (String, LittleFS, RequestHandler) yalniz isleyicinin
 * kullandigi kadar; cekirdekteki imzalarla ayni (RequestHandler.h 3.3.11).
 * Dagitim cekirdegin `_parseRequest`i gibi: ilk `canHandle` kazanir, onun
 * `handle`i false donerse 404 (sonraki isleyiciye DUSMEZ).
 *
 * Cikti:  H|<i>|<isleyici|->|<handle 1|0>|<gonder adedi>|<acilan|->|<istek|->|<tur|->|<onbellek|->
 *         Y <yigin bos bayt> <String tasmasi>
 *         BITTI
 */
#include <avr/io.h>
#include <avr/pgmspace.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "mimetable.h"   /* cekirdegin kendisi (-I .../WebServer/src/detail) */

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
static void sayi(uint16_t v)
{
    char b[6];
    uint8_t n = 0;
    do { b[n++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (n) yaz(b[--n]);
}

/* ── yigin derinligi: .bss sonu ile en derin SP arasi ──────────────── */
extern char __bss_end;
static uint16_t g_sp_min = 0xFFFF;
static inline void sp_olc(void)
{
    if (SP < g_sp_min) g_sp_min = SP;
}

/* ── ince Arduino katmani ──────────────────────────────────────────── */
static uint8_t g_tasma;

class String {
 public:
    enum { KAP = 40 };   /* en uzun: "/vendor/vue.global.prod.js.gz" 29, MIME 29 */
    String() { b_[0] = 0; }
    String(const char *s) { b_[0] = 0; ekle(s); }
    String(const String &o) { b_[0] = 0; ekle(o.b_); }
    String &operator=(const String &o) { if (this != &o) { b_[0] = 0; ekle(o.b_); } return *this; }
    const char *c_str() const { return b_; }
    unsigned int length() const { return (unsigned int)strlen(b_); }
    bool endsWith(const char *s) const
    {
        size_t n = strlen(b_), m = strlen(s);
        return m <= n && strcmp(b_ + n - m, s) == 0;
    }
    bool endsWith(const String &s) const { return endsWith(s.b_); }
    bool startsWith(const char *s) const { return strncmp(b_, s, strlen(s)) == 0; }
    bool startsWith(const String &s) const { return startsWith(s.b_); }
    String &operator+=(const char *s) { ekle(s); return *this; }
    String operator+(const char *s) const { String r(*this); r.ekle(s); return r; }
    bool operator==(const char *s) const { return strcmp(b_, s) == 0; }

 private:
    void ekle(const char *s)
    {
        sp_olc();
        size_t n = strlen(b_), m = strlen(s);
        if (n + m >= KAP) { g_tasma = 1; m = KAP - 1 - n; }
        memcpy(b_ + n, s, m);
        b_[n + m] = 0;
    }
    char b_[KAP];
};

enum HTTPMethod { HTTP_DELETE = 0, HTTP_GET = 1, HTTP_HEAD = 2, HTTP_POST = 3 };
class WebServer {};

/* Cekirdegin RequestHandler'iyla ayni sanal imzalar (yalniz isleyicinin ezdikleri). */
class RequestHandler {
 public:
    virtual bool canHandle(HTTPMethod method, const String &uri) { (void)method; (void)uri; return false; }
    virtual bool canHandle(WebServer &server, HTTPMethod method, const String &uri)
    {
        (void)server; (void)method; (void)uri; return false;
    }
    virtual bool handle(WebServer &server, HTTPMethod requestMethod, const String &requestUri)
    {
        (void)server; (void)requestMethod; (void)requestUri; return false;
    }
};

#include "arayuz_vektor.h"   /* DOSYALAR, DIZINLER, ISTEKLER (PROGMEM) + isleyici kurulumu */

static String g_acilan;
static int8_t pgm_ara(const char *blob, const char *yol)
{
    int8_t i = 0;
    for (const char *p = blob; pgm_read_byte(p); p += strlen_P(p) + 1, i++)
        if (strcmp_P(yol, p) == 0) return i;
    return -1;
}

class File {
 public:
    File() : var_(false), dizin_(false) {}
    File(bool var, bool dizin) : var_(var), dizin_(dizin) {}
    operator bool() const { return var_; }
    bool isDirectory() const { return dizin_; }
    void close() {}

 private:
    bool var_, dizin_;
};

class LittleFSInce {
 public:
    bool exists(const char *y) { sp_olc(); return pgm_ara(DOSYALAR, y) >= 0 || pgm_ara(DIZINLER, y) >= 0; }
    bool exists(const String &y) { return exists(y.c_str()); }
    File open(const String &y, const char *kip)
    {
        (void)kip;
        sp_olc();
        g_acilan = y;
        if (pgm_ara(DOSYALAR, y.c_str()) >= 0) return File(true, false);
        if (pgm_ara(DIZINLER, y.c_str()) >= 0) return File(true, true);
        return File();
    }
};
static LittleFSInce LittleFS;

/* Kartta Cache-Control + ETag/304 + streamFile; burada ne istendigi kaydediliyor. */
static uint8_t g_gonder;
static String g_istek, g_tur;
static const char *g_onbellek;
static void arayuz_gonder(File &f, const char *istek_yolu, const String &tur, const char *onbellek)
{
    (void)f;
    sp_olc();
    g_gonder++;
    g_istek = istek_yolu;
    g_tur = tur;
    g_onbellek = onbellek;
}

#include "arayuz_kaynak.h"   /* kartin `arayuz_tur` + `class ArayuzIsleyici` METNI */

ISLEYICI_KUR   /* static ArayuzIsleyici I0(...), I1(...); static RequestHandler *const ISLEYICILER[] */

int main(void)
{
    uart_baslat();
    WebServer sunucu;
    char tampon[String::KAP];
    uint8_t i = 0;
    for (const char *p = ISTEKLER; pgm_read_byte(p); p += strlen_P(p) + 1, i++) {
        strncpy_P(tampon, p, sizeof(tampon) - 1);
        tampon[sizeof(tampon) - 1] = 0;
        const HTTPMethod m = tampon[0] == 'P' ? HTTP_POST : HTTP_GET;
        const String uri(tampon + 2);
        g_acilan = "";
        g_istek = "";
        g_tur = "";
        g_onbellek = 0;
        g_gonder = 0;
        int8_t secilen = -1;
        bool sonuc = false;
        for (uint8_t h = 0; h < ISLEYICI_ADET; h++) {
            if (ISLEYICILER[h]->canHandle(sunucu, m, uri)) {
                secilen = (int8_t)h;
                sonuc = ISLEYICILER[h]->handle(sunucu, m, uri);
                break;
            }
        }
        metin("H|"); sayi(i);
        metin("|"); if (secilen < 0) metin("-"); else sayi((uint16_t)secilen);
        metin(sonuc ? "|1|" : "|0|"); sayi(g_gonder);
        metin("|"); metin(g_acilan.length() ? g_acilan.c_str() : "-");
        metin("|"); metin(g_istek.length() ? g_istek.c_str() : "-");
        metin("|"); metin(g_tur.length() ? g_tur.c_str() : "-");
        metin("|"); metin(g_onbellek ? g_onbellek : "-");
        metin("\r\n");
    }
    metin("Y ");
    sayi((uint16_t)(g_sp_min - (uint16_t)&__bss_end));
    metin(" ");
    sayi(g_tasma);
    metin("\r\nBITTI\r\n");
    for (;;) {}
}
