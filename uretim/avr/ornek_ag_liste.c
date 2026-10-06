/*
 * Coklu ag (2026-10-06) — ag_liste.h'nin AVR uzerinde kosturulmasi (sim3_web.py 5n).
 * Kartta kosan karar kodunun TA KENDISI (ayni baslik). Her senaryo bir satir basar;
 * beklenen satirlar sim3_web.py'de (Python ayni kurali bagimsiz yazmaz: beklenenler
 * tasarimdan elle — CA3/CA4/CA13).
 *
 * Cikti:  <etiket> <deger...>\r\n   ...   BITTI
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>

#include "ag_liste.h"

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

static void sayi(int16_t v)
{
    char b[7];
    uint8_t n = 0;
    if (v < 0) { yaz('-'); v = (int16_t)-v; }
    do { b[n++] = (char)('0' + (uint8_t)(v % 10)); v = (int16_t)(v / 10); } while (v);
    while (n) yaz(b[--n]);
}

static void satir(const char *etiket, const int16_t *d, uint8_t n)
{
    metin(etiket);
    for (uint8_t i = 0; i < n; i++) { yaz(' '); sayi(d[i]); }
    metin("\r\n");
}

static AglKayit K[AGL_AZAMI];

static void gor(AglGorunen *g, uint8_t i, const char *ad, int8_t rssi)
{
    memset(&g[i], 0, sizeof(g[i]));
    strncpy(g[i].ad, ad, AGL_AD - 1u);
    g[i].rssi = rssi;
}

int main(void)
{
    uart_baslat();
    int16_t d[12];
    AglGorunen g[6];
    uint8_t c[AGL_AZAMI];

    /* L1: gecerlilik (CA13) — ad 0/1/32/33 bayt, parola 0/7/8/63/64 */
    {
        char a33[34], p64[65];
        memset(a33, 'a', 33); a33[33] = 0;
        memset(p64, 'p', 64); p64[64] = 0;
        d[0] = agl_ad_gecerli(""); d[1] = agl_ad_gecerli("x");
        d[2] = agl_ad_gecerli(a33 + 1); d[3] = agl_ad_gecerli(a33);
        d[4] = agl_parola_gecerli(""); d[5] = agl_parola_gecerli("1234567");
        d[6] = agl_parola_gecerli("12345678"); d[7] = agl_parola_gecerli(p64 + 1);
        d[8] = agl_parola_gecerli(p64);
        satir("L1", d, 9);
    }
    /* L2: ekle / ayni ad guncelleme ayni yuva / oncelik korunur / sil / bosalan yuvaya ekle */
    {
        memset(K, 0, sizeof(K));
        d[0] = agl_ekle(K, "EvAgi");
        d[1] = agl_ekle(K, "Hotspot");
        K[1].oncelik = 1;
        d[2] = agl_ekle(K, "Hotspot");          /* guncelleme: ayni yuva, oncelik KALIR */
        d[3] = K[1].oncelik;
        d[4] = agl_ekle(K, "evagi");             /* buyuk/kucuk harf FARKLI ag */
        d[5] = agl_sil(K, 0);
        d[6] = agl_sil(K, 0);                    /* zaten bos */
        d[7] = agl_ekle(K, "Yeni");              /* bosalan yuva 0 */
        d[8] = agl_adet(K);
        d[9] = agl_bul(K, "EvAgi");
        satir("L2", d, 10);
    }
    /* L3: 8 sinir — 9. yeni ad reddedilir, var olanin guncellemesi olur */
    {
        memset(K, 0, sizeof(K));
        char ad[4] = "A0";
        for (uint8_t i = 0; i < 8; i++) { ad[1] = (char)('0' + i); (void)agl_ekle(K, ad); }
        d[0] = agl_adet(K);
        d[1] = agl_ekle(K, "A8");
        d[2] = agl_ekle(K, "A5");
        d[3] = agl_ekle(K, "");
        satir("L3", d, 4);
    }
    /* L4: secim — gorunmeyen elenir, RSSI sirasi, oncelik once, ayni adin en gucluu */
    {
        memset(K, 0, sizeof(K));
        (void)agl_ekle(K, "EvAgi");     /* 0 */
        (void)agl_ekle(K, "Hotspot");   /* 1 */
        (void)agl_ekle(K, "Ofis");      /* 2 — gorunmuyor */
        (void)agl_ekle(K, "Komsu");     /* 3 */
        gor(g, 0, "EvAgi", -70); gor(g, 1, "Hotspot", -45); gor(g, 2, "Yabanci", -30);
        gor(g, 3, "Komsu", -80); gor(g, 4, "Komsu", -50);   /* ayni ad: en gucluu -50 */
        const uint8_t n = agl_adaylar(K, g, 5, c);
        d[0] = n; for (uint8_t i = 0; i < n; i++) d[1 + i] = c[i];
        satir("L4", d, (uint8_t)(1 + n));
        K[0].oncelik = 1;                                   /* EvAgi oncelikli: zayif olsa da once */
        const uint8_t m = agl_adaylar(K, g, 5, c);
        d[0] = m; for (uint8_t i = 0; i < m; i++) d[1 + i] = c[i];
        satir("L5", d, (uint8_t)(1 + m));
    }
    /* L6: donus — sec(-1) ilk; basarisiz olan ilk -> ikinci; son -> basa; gorunmeyen basarisiz -> ilk */
    {
        /* L5'in listesi: [0 (oncelik), 1 (-45), 3 (-50)] */
        d[0] = agl_sec(K, g, 5, -1);
        d[1] = agl_sec(K, g, 5, 0);
        d[2] = agl_sec(K, g, 5, 1);
        d[3] = agl_sec(K, g, 5, 3);
        d[4] = agl_sec(K, g, 5, 2);                         /* 2 (Ofis) gorunmuyor -> ilk */
        d[5] = agl_sec(K, g, 0, -1);                        /* tarama bos -> -1 */
        gor(g, 0, "Hotspot", -60);
        d[6] = agl_sec(K, g, 1, 1);                         /* tek aday basarisiz -> yine o */
        satir("L6", d, 7);
    }
    /* L7: taramasiz ilk tahmin — son iyi > oncelikli > ilk dolu > -1 */
    {
        memset(K, 0, sizeof(K));
        (void)agl_ekle(K, "A"); (void)agl_ekle(K, "B"); (void)agl_ekle(K, "C");
        d[0] = agl_ilk(K, -1);
        K[2].oncelik = 1;
        d[1] = agl_ilk(K, -1);
        d[2] = agl_ilk(K, 1);
        (void)agl_sil(K, 1);
        d[3] = agl_ilk(K, 1);                                /* son iyi silinmis -> oncelikli */
        memset(K, 0, sizeof(K));
        d[4] = agl_ilk(K, -1);
        d[5] = agl_ilk(K, 9);                                /* aralik disi */
        satir("L7", d, 6);
    }
    metin("BITTI\r\n");
    for (;;) {}
}
