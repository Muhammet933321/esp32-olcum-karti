/*
 * B71 — kayit motorunun AVR emulatorunde kosturulmasi.
 *
 * NEDEN AVR: ESP32-S3'u komut komut calistiran bir emulatorumuz yok, ama
 * AVR'yi calistiran ve bit birebir dogrulanmis bir emulatorumuz var
 * (test_avr.py). kayit_*.h hicbir platform cagrisi icermiyor; flas
 * erisimi KayitFlas islev isaretcileriyle geliyor. Burada o isaretciler
 * emule NOR flasa (uretim/avr/nor_flas.py) bagli. Kosturulan kod, kartta
 * kosacak kodun ta kendisi.
 *
 * Tek senaryo derlenir: -DSENARYO_BICIM | _NOKTACI | _GUNLUK | _YAZICI |
 * _KESINTI. Testte -DKAYIT_SEKTOR=512UL -DKAYIT_AZAMI_YUK=256u.
 * Surucu: uretim/test_kayit.py.
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>

#include "kayit_bicim.h"
#include "kayit_nokta.h"
#include "kayit_gunluk.h"

#define KULLANILMAYABILIR __attribute__((unused))

/* ─────────────────────────────── seri cikis */
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

static KULLANILMAYABILIR void metin(const char *s)
{
    while (*s) yaz(*s++);
}

static KULLANILMAYABILIR void satir(void) { yaz('\n'); }

static KULLANILMAYABILIR void hex8(uint8_t v)
{
    static const char h[] = "0123456789abcdef";
    yaz(h[v >> 4]);
    yaz(h[v & 15u]);
}

static KULLANILMAYABILIR void hex32(uint32_t v)
{
    int8_t i;
    for (i = 3; i >= 0; i--) hex8((uint8_t)(v >> (8 * i)));
}

static KULLANILMAYABILIR void hexdizi(const uint8_t *p, uint16_t n)
{
    while (n--) hex8(*p++);
}

static KULLANILMAYABILIR void ondalik(uint32_t v)
{
    char b[11];
    int8_t i = 0;
    do { b[i++] = (char)('0' + (v % 10u)); v /= 10u; } while (v);
    while (i) yaz(b[--i]);
}

static KULLANILMAYABILIR void sayi(const char *ad, int32_t v)
{
    metin(ad);
    yaz(' ');
    if (v < 0) { yaz('-'); ondalik((uint32_t)(-v)); }
    else ondalik((uint32_t)v);
    satir();
}

/* ─────────────────────────────── deterministik veri (test_kayit.py ile AYNI) */
static KULLANILMAYABILIR void nokta_uret(uint32_t k, KayitNokta *p)
{
    uint16_t v = (uint16_t)(k % 30000u), i = (uint16_t)(k % 20000u);
    p->kart_ms = k * 37u + 5u;
    p->n = (uint16_t)(k % 50u + 1u);
    p->bayrak = (uint8_t)(k & 0x3Fu);
    p->v_ort_kod = (float)v + 0.25f;
    p->v_min_kod = (int16_t)((int16_t)v - 7);
    p->v_maks_kod = (int16_t)((int16_t)v + 7);
    p->i_ort_kod = -(float)i - 0.5f;
    p->i_min_kod = (int16_t)(-(int16_t)i - 3);
    p->i_maks_kod = (int16_t)(-(int16_t)i + 3);
    p->w_ort = (float)k * 0.5f;
    p->w_min = (float)k * 0.25f;
    p->w_maks = (float)k * 0.75f;
}

static KULLANILMAYABILIR void basla_uret(KayitBasla *b, uint32_t hiz_ms)
{
    memset(b, 0, sizeof(*b));
    b->oturum_turu = KAYIT_OTURUM_OLCUM;
    b->kal_bicim = KAYIT_KAL_BICIM;
    b->hiz_ms = hiz_ms;
    b->unix_s = 0u;
    b->kart_ms = 1000u;
    b->acilis = 3u;
    memcpy(b->surum, "B71-test", 8);
    b->kal.normal.n = 16.5f;
    b->kal.normal.pga = 2.0f;
    b->kal.normal.kazanc = 1.0078125f;
    b->kal.normal.sifir_ham = -12;
    b->kal.normal.tau = 0.0029296875f;
    b->kal.yuksek.n = 312.5f;
    b->kal.yuksek.pga = 2.0f;
    b->kal.yuksek.kazanc = 0.9921875f;
    b->kal.yuksek.sifir_ham = 5;
    b->kal.yuksek.tau = 0.0030517578125f;
    b->kal.i_ofset = -3;
    b->kal.i_pga = 0.25f;
    b->kal.sont_ohm = 0.0048828125f;
    b->kal.i_duzeltme = 1.0f;
    b->kal.sebeke_hz = 50.0f;
    b->kal.faz_kal_us[0] = 12.5f;
    b->kal.faz_kal_us[1] = -3.25f;
}

/* ─────────────────────────────── emule NOR (uretim/avr/nor_flas.py) */
#if defined(SENARYO_GUNLUK) || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI)
#define NOR_KOMUT (*(volatile uint8_t *)0xE0)
#define NOR_A0    (*(volatile uint8_t *)0xE1)
#define NOR_A1    (*(volatile uint8_t *)0xE2)
#define NOR_A2    (*(volatile uint8_t *)0xE3)
#define NOR_VERI  (*(volatile uint8_t *)0xE4)
#ifndef NOR_SEKTOR_ADET
#define NOR_SEKTOR_ADET 8u      /* test_kayit.py derle() -D ile gecirir */
#endif
#define DIZIN_KAP 6u

static void nor_adres(uint32_t a)
{
    NOR_A0 = (uint8_t)a;
    NOR_A1 = (uint8_t)(a >> 8);
    NOR_A2 = (uint8_t)(a >> 16);
}

static int f_oku(void *b, uint32_t a, void *h, uint32_t n)
{
    uint8_t *p = (uint8_t *)h;
    (void)b;
    nor_adres(a);
    while (n--) *p++ = NOR_VERI;
    return 0;
}

static int f_yaz(void *b, uint32_t a, const void *k, uint32_t n)
{
    const uint8_t *p = (const uint8_t *)k;
    (void)b;
    nor_adres(a);
    while (n--) NOR_VERI = *p++;
    return 0;
}

static int f_sil(void *b, uint32_t a)
{
    (void)b;
    nor_adres(a);
    NOR_KOMUT = 0x5E;
    while (NOR_KOMUT & 1u) {}
    return 0;
}

static const KayitFlas FLAS = { f_oku, f_yaz, f_sil, 0 };
static KayitSektor sektor[NOR_SEKTOR_ADET];
static KayitOzet dizin[DIZIN_KAP];
static KayitGunluk g;
#endif

/* ── senaryolar ── */

#if defined(SENARYO_BICIM)
static void senaryo(void)
{
    static const uint8_t dokuz[9] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    uint8_t p[KAYIT_BASLA_BAYT], p2[KAYIT_NOKTA_BAYT], h[KAYIT_BASLIK_BAYT];
    KayitNokta n, n2;
    KayitBasla b;

    metin("CRC "); hex32(kayit_crc_ekle(0u, dokuz, 9u)); satir();
    nokta_uret(12345u, &n);
    kayit_nokta_paketle(&n, p);
    metin("NOKTA "); hexdizi(p, KAYIT_NOKTA_BAYT); satir();
    kayit_nokta_coz(p, &n2);
    kayit_nokta_paketle(&n2, p2);
    metin("GIDISDONUS "); metin(memcmp(p, p2, KAYIT_NOKTA_BAYT) ? "0" : "1"); satir();
    basla_uret(&b, 200u);
    kayit_basla_paketle(&b, p);
    metin("BASLA "); hexdizi(p, KAYIT_BASLA_BAYT); satir();
    kayit_baslik_yaz(h, KAYIT_T_NOKTA, 7u, 42u, p, 20u);
    metin("BASLIK "); hexdizi(h, KAYIT_BASLIK_BAYT); satir();
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_NOKTACI)
static void p_yaz(const KayitNokta *p)
{
    uint8_t b[KAYIT_NOKTA_BAYT];
    kayit_nokta_paketle(p, b);
    metin("P ");
    hexdizi(b, KAYIT_NOKTA_BAYT);
    satir();
}

static void senaryo(void)
{
    KayitNoktaci k;
    KayitNokta c;
    uint32_t t;
    int16_t i;

    /* S1: 100 ms aralik, 10 ms'de bir ornek v=100+i, i_kod=-i, w=i/2 */
    kn_baslat(&k, 100u, 0u, 0u);
    for (i = 0; i < 30; i++) {
        t = (uint32_t)i * 10u;
        if (kn_ornek(&k, t, 0u, (int16_t)(100 + i), (int16_t)(-i),
                     (float)i * 0.5f, 0u, 0u, &c)) p_yaz(&c);
    }
    if (kn_zaman(&k, 300u, &c)) p_yaz(&c);
    metin("S1\n");

    /* S2: t=0..40 NORMAL (1000), t=45..85 YUKSEK (2000) */
    kn_baslat(&k, 100u, 0u, 0u);
    for (i = 0; i < 5; i++)
        if (kn_ornek(&k, (uint32_t)i * 10u, 0u, 1000, 10, 1.0f, 0u, 0u, &c)) p_yaz(&c);
    for (i = 0; i < 5; i++)
        if (kn_ornek(&k, 45u + (uint32_t)i * 10u, 1u, 2000, 20, 2.0f, 0u, 0u, &c)) p_yaz(&c);
    if (kn_zaman(&k, 145u, &c)) p_yaz(&c);
    metin("S2\n");

    /* S3: hatali ornek, doyma, kuyruk kaybi, uzun duraklama */
    kn_baslat(&k, 50u, 0u, 0u);
    kn_ornek(&k, 0u, 0u, 5, 1, 0.25f, 0u, 0u, &c);
    kn_ornek(&k, 10u, 0u, 9999, 1, 99.0f, KN_HATA_V, 0u, &c);
    kn_ornek(&k, 20u, 0u, 7, 3, 0.75f, 0u, 1u, &c);
    kn_kayip(&k);
    if (kn_ornek(&k, 260u, 0u, 1, 1, 1.0f, 0u, 0u, &c)) p_yaz(&c);
    if (kn_zaman(&k, 310u, &c)) p_yaz(&c);
    metin("S3\n");

    /* S4: 40 000 uc deger ornek tek noktada — int32/int64 tasmaz */
    kn_baslat(&k, 1000000UL, 0u, 0u);
    for (t = 0; t < 40000UL; t++)
        kn_ornek(&k, t, 0u, 32767, -32768, 7000.0f, 0u, 0u, &c);
    if (kn_zaman(&k, 1000000UL, &c)) p_yaz(&c);
    metin("S4\nBITTI\n");
}
#endif

#if defined(SENARYO_GUNLUK)
static uint8_t tampon[600];
/* cop: imza + gecerli gorunen alanlar, CRC tutmaz (sektor 3'un basina) */
static const uint8_t COP[16] = {0xA5, 0x02, 0x0A, 0x00, 0x11, 0x11, 0x11, 0x11,
                                0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x11};
/* yarim: sira 36'nin basligi yazilmis, yuku yazilmadan elektrik kesilmis */
static const uint8_t YARIM[16] = {0xA5, 0x05, 0x0C, 0x00, 0x24, 0x00, 0x00, 0x00,
                                  0x00, 0x00, 0x00, 0x00, 0x78, 0x56, 0x34, 0x12};

static void durum(const char *ad)
{
    metin(ad);
    metin(" sonraki="); ondalik(g.sonraki_sira);
    metin(" bas="); ondalik(g.bas);
    metin(" ofset="); ondalik(g.bas_ofset);
    metin(" onay="); ondalik(g.onay);
    metin(" bozuk="); ondalik(g.bozuk);
    metin(" dolu="); ondalik(g.dolu);
    metin(" silinen="); ondalik(g.silinen_sektor);
    metin(" kull="); ondalik(kg_kullanilan(&g));
    metin(" onaysiz="); ondalik(kg_onaysiz(&g));
    metin(" dizin="); ondalik(g.dizin_adet);
    satir();
}

static void oku(uint32_t sira, uint32_t kap)
{
    uint32_t ilk, son, n = kg_oku(&g, sira, tampon, kap, &ilk, &son);
    metin("OKU "); ondalik(n); yaz(' '); ondalik(ilk); yaz(' '); ondalik(son); satir();
    metin("VERI "); hexdizi(tampon, (uint16_t)n); satir();
}

static void senaryo(void)
{
    uint8_t yuk[100];
    int32_t s;
    uint16_t i;
    for (i = 0; i < sizeof(yuk); i++) yuk[i] = (uint8_t)i;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u); durum("G1");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u));
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 13u));
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u));
    durum("G2");
    oku(2u, sizeof(tampon));
    kg_ac(&g, 0u); durum("G3");
    i = 0;
    do { s = kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u); i++; } while (s > 0 && i < 1000u);
    metin("DOLU "); ondalik(i); yaz(' '); ondalik((uint32_t)(-s)); satir();
    durum("G4");
    kg_onayla(&g, 0xFFFFFFF0UL); durum("G5");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u)); durum("G6");
    oku(1u, 200u);
    oku(6u, 100u);
    kg_bicimle(&g); durum("G7");
    kg_ac(&g, g.sonraki_sira); durum("G8");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u));
    f_yaz(0, 3u * KAYIT_SEKTOR, COP, sizeof(COP));
    kg_ac(&g, 0u); durum("G9");
    f_yaz(0, 28u, YARIM, sizeof(YARIM));
    kg_ac(&g, 0u); durum("G10");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u)); durum("G11");
    oku(35u, sizeof(tampon));
    metin("BITTI\n");
}
#endif

/* ── giris ── */
#if !(defined(SENARYO_BICIM) || defined(SENARYO_NOKTACI) || defined(SENARYO_GUNLUK) \
      || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI))
#error "SENARYO_* tanimli degil"
#endif

int main(void)
{
    uart_baslat();
    senaryo();
    for (;;) {}
}
