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
 * _DIZIN | _KESINTI. Testte -DKAYIT_SEKTOR=512UL -DKAYIT_AZAMI_YUK=256u.
 * Surucu: uretim/test_kayit.py.
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>

#include "kayit_bicim.h"
#include "kayit_nokta.h"
#include "kayit_gunluk.h"
#include "kayit_oturum.h"

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
#if defined(SENARYO_GUNLUK) || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI) \
    || defined(SENARYO_DIZIN) || defined(SENARYO_TARAMA)
#define NOR_KOMUT (*(volatile uint8_t *)0xE0)
#define NOR_A0    (*(volatile uint8_t *)0xE1)
#define NOR_A1    (*(volatile uint8_t *)0xE2)
#define NOR_A2    (*(volatile uint8_t *)0xE3)
#define NOR_VERI  (*(volatile uint8_t *)0xE4)
#define NOR_ARIZA_OKU (*(volatile uint8_t *)0xE5)   /* yalniz test: n. okuma baytinda hata */
#define NOR_ARIZA_YAZ (*(volatile uint8_t *)0xE6)   /* yalniz test: n. yazma baytinda hata */
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
    return (NOR_KOMUT & 2u) ? -1 : 0;     /* bit1: islem basarisiz */
}

static int f_yaz(void *b, uint32_t a, const void *k, uint32_t n)
{
    const uint8_t *p = (const uint8_t *)k;
    (void)b;
    nor_adres(a);
    while (n--) NOR_VERI = *p++;
    return (NOR_KOMUT & 2u) ? -1 : 0;
}

static int f_sil(void *b, uint32_t a)
{
    uint8_t d;
    (void)b;
    nor_adres(a);
    NOR_KOMUT = 0x5E;
    do { d = NOR_KOMUT; } while (d & 1u);
    return (d & 2u) ? -1 : 0;
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
    kg_ac(&g, 0u, 0u); durum("G1");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u));
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 13u));
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u));
    durum("G2");
    oku(2u, sizeof(tampon));
    kg_ac(&g, 0u, 0u); durum("G3");
    i = 0;
    do { s = kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u); i++; } while (s > 0 && i < 1000u);
    metin("DOLU "); ondalik(i); yaz(' '); ondalik((uint32_t)(-s)); satir();
    durum("G4");
    sayi("RED", kg_onayla(&g, 0xFFFFFFF0UL)); durum("G5");
    sayi("ONAY", kg_onayla(&g, 33u));
    kg_ac(&g, 0u, g.onay); durum("G5b");      /* yeniden acilis: onay korunmali */
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 100u)); durum("G6");
    oku(1u, 200u);
    oku(6u, 100u);
    kg_bicimle(&g); durum("G7");
    kg_ac(&g, g.sonraki_sira, 0u); durum("G8");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u));
    f_yaz(0, 3u * KAYIT_SEKTOR, COP, sizeof(COP));
    kg_ac(&g, 0u, 0u); durum("G9");
    f_yaz(0, 28u, YARIM, sizeof(YARIM));
    kg_ac(&g, 0u, 0u); durum("G10");
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u)); durum("G11");
    oku(35u, sizeof(tampon));
    /* son inceleme: bilinmeyen tur (6), okuma hatasi ve yarim yazma (4) */
    sayi("EK9", kg_ekle(&g, 9u, 0u, yuk, 12u));
    kg_ac(&g, 0u, 0u); durum("G12");
    oku(37u, sizeof(tampon));
    NOR_ARIZA_OKU = 40u;
    sayi("ACHATA", kg_ac(&g, 0u, 0u));      /* 1. gecis (~40. bayt) */
    NOR_ARIZA_OKU = 200u;
    sayi("ACHATA2", kg_ac(&g, 0u, 0u));     /* 2. gecis: 1. gecis ~162 bayt okur */
    kg_ac(&g, 0u, 0u); durum("G13");
    NOR_ARIZA_YAZ = 30u;                      /* 16 baslik + 13 yuk, 30. bayt = dolgu */
    sayi("YAZHATA", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 13u));
    sayi("EK", kg_ekle(&g, KAYIT_T_SAAT, 0u, yuk, 12u));
    kg_ac(&g, 0u, 0u); durum("G14");
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_YAZICI)
static KayitYazici y;

static void oz(const char *ad)
{
    uint16_t i;
    for (i = 0; i < g.dizin_adet; i++) {
        const KayitOzet *o = &g.dizin[i];
        metin(ad);
        yaz(' '); ondalik(o->id); yaz(' '); ondalik(o->tur);
        yaz(' '); ondalik(o->hiz_ms); yaz(' '); ondalik(o->ilk_sira);
        yaz(' '); ondalik(o->son_sira); yaz(' '); ondalik(o->nokta_sonraki);
        yaz(' '); ondalik(o->durum); yaz(' '); ondalik(o->basi_silindi);
        satir();
    }
}

static void senaryo(void)
{
    KayitBasla b, bb;
    KayitNokta p;
    KayitSaat z;
    KayitDevam d;
    uint32_t k, t = 0u, id, ns;
    int r = 0;

    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u, 0u);
    ky_kur(&y, &g);

    /* O1: 40 nokta, 200 ms; tampon dolunca ve 5 s'de bir bosaltilir */
    basla_uret(&b, 200u);
    sayi("O1", ky_baslat(&y, &b));
    for (k = 0; k < 40u && !r; k++) {
        nokta_uret(k, &p);
        t += 200u;
        r = ky_nokta(&y, &p, t);
        if (!r) r = ky_zaman(&y, t);
    }
    sayi("R1", r);
    sayi("B1", ky_bitir(&y, KB_SEBEP_KULLANICI));

    /* O2: ortada saat kaydi */
    basla_uret(&b, 1000u);
    sayi("O2", ky_baslat(&y, &b));
    for (k = 100; k < 110u; k++) {
        nokta_uret(k, &p);
        t += 1000u;
        ky_nokta(&y, &p, t);
        if (k == 104u) {
            z.unix_s = 1790000000UL;
            z.kart_ms = t;
            z.acilis = 3u;
            ky_saat(&y, &z);
        }
    }
    sayi("B2", ky_bitir(&y, KB_SEBEP_KULLANICI));

    /* O3: acik birakilir, "yeniden baslama" sonrasi surdurulur */
    basla_uret(&b, 500u);
    sayi("O3", ky_baslat(&y, &b));
    for (k = 200; k < 210u; k++) { nokta_uret(k, &p); t += 500u; ky_nokta(&y, &p, t); }
    sayi("BO", ky_bosalt(&y));
    kg_ac(&g, 0u, 0u);                  /* RAM'deki her sey unutuldu */
    ky_kur(&y, &g);
    oz("OZ");
    r = -9;
    {
        const KayitOzet *o = kg_acik_oturum(&g);
        if (o) {
            id = o->id;
            ns = o->nokta_sonraki;
            if (!kg_basla_oku(&g, o->basla_adres, id, &bb)) {
                d.acilis = 4u; d.unix_s = 0u; d.kart_ms = 50u; d.nokta_sira = 0u;
                r = ky_devam(&y, id, &bb, ns, &d);
            }
        }
    }
    sayi("DV", r);
    for (k = 210; k < 215u; k++) { nokta_uret(k, &p); t += 500u; ky_nokta(&y, &p, t); }
    sayi("B3", ky_bitir(&y, KB_SEBEP_KULLANICI));
    kg_ac(&g, 0u, 0u);
    oz("OZS");

    /* O4: onay YOK -> bellek dolar; BITIR(DOLU) yazilmali */
    ky_kur(&y, &g);
    basla_uret(&b, 100u);
    sayi("O4", ky_baslat(&y, &b));
    k = 1000u;
    r = 0;
    while (!r && k < 20000u) { nokta_uret(k, &p); k++; t += 100u; r = ky_nokta(&y, &p, t); }
    sayi("DOLU", r);
    sayi("BESLENEN", (int32_t)(k - 1000u));
    sayi("AKTIF", (int32_t)y.oturum);
    sayi("DUSEN", (int32_t)y.dusen);
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_KESINTI)
static KayitYazici y;

/* Sonsuz is yuku: test_kayit.py rastgele bir cevrimde KESER, karti
   yeniden acar. Her acilis: kurtar -> acik oturum varsa DEVAM, yoksa YENI. */
static void senaryo(void)
{
    KayitNokta p;
    KayitBasla b;
    uint32_t k = 0u, t = 0u, id = 0u, adres = KG_ADRES_YOK;
    const KayitOzet *acik;
    int32_t r;

    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u, 0u);
    ky_kur(&y, &g);
    kg_onayla(&g, g.sonraki_sira - 1u);    /* cihaz her seyi aldi: halka donsun */
    metin("AC "); ondalik(g.sonraki_sira); yaz(' '); ondalik(g.bozuk); satir();
    acik = kg_acik_oturum(&g);
    if (acik) { id = acik->id; k = acik->nokta_sonraki; adres = acik->basla_adres; }
    if (id) {
        KayitDevam d;
        memset(&d, 0, sizeof(d));
        d.acilis = 1u;
        r = kg_basla_oku(&g, adres, id, &b);
        if (!r) r = ky_devam(&y, id, &b, k, &d);
        metin("DEVAM "); ondalik(id); yaz(' '); ondalik(k); satir();
    } else {
        basla_uret(&b, 100u);
        r = ky_baslat(&y, &b);
        metin("YENI "); ondalik(r > 0 ? (uint32_t)r : 0u); satir();
        r = (r > 0) ? 0 : r;
    }
    if (r) { metin("HATA "); ondalik((uint32_t)(-r)); satir(); metin("BITTI\n"); return; }
    for (;;) {
        nokta_uret(k, &p);
        k++;
        t += 100u;
        r = ky_nokta(&y, &p, t);
        if (!r && (k & 3u) == 0u) {
            r = ky_bosalt(&y);
            kg_onayla(&g, g.sonraki_sira - 1u);
        }
        if (r) { metin("HATA "); ondalik((uint32_t)(-r)); satir(); metin("BITTI\n"); return; }
    }
}
#endif

#if defined(SENARYO_DIZIN)
static KayitYazici y;

static void dz(const char *ad)
{
    uint16_t i;
    for (i = 0; i < g.dizin_adet; i++) {
        const KayitOzet *o = &g.dizin[i];
        metin(ad);
        yaz(' '); ondalik(o->id); yaz(' '); ondalik(o->tur);
        yaz(' '); ondalik(o->hiz_ms); yaz(' '); ondalik(o->ilk_sira);
        yaz(' '); ondalik(o->son_sira); yaz(' '); ondalik(o->nokta_sonraki);
        yaz(' '); ondalik(o->durum); yaz(' '); ondalik(o->basi_silindi);
        satir();
    }
}

/* Son inceleme bulgu 5: dizin bakimi. 8 kisa oturum (kapasite 6) ->
   tahliye; sonra her sey onaylanip yeni oturum halkayi dondurur ->
   temizlik (kg__sektor_dusur). Canli dizin flastan yeniden kurulanla
   karsilastirilir. */
static void senaryo(void)
{
    KayitBasla b, bb;
    KayitNokta p;
    const KayitOzet *o;
    uint32_t k, s, t = 0u;
    int r;

    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u, 0u);
    ky_kur(&y, &g);
    for (s = 0; s < 8u; s++) {
        basla_uret(&b, 100u + s);
        sayi("ID", ky_baslat(&y, &b));
        for (k = 0; k < 3u; k++) { nokta_uret(s * 10u + k, &p); t += 100u; ky_nokta(&y, &p, t); }
        ky_bitir(&y, KB_SEBEP_KULLANICI);
    }
    dz("DZ");
    kg_onayla(&g, g.sonraki_sira - 1u);
    basla_uret(&b, 999u);
    sayi("ID9", ky_baslat(&y, &b));
    r = 0;
    for (k = 0; k < 45u && !r; k++) { nokta_uret(1000u + k, &p); t += 100u; r = ky_nokta(&y, &p, t); }
    if (!r) r = ky_bosalt(&y);
    if (r) sayi("HATA", r);
    sayi("SILINEN", (int32_t)g.silinen_sektor);
    dz("DC");                            /* canli dizin */
    kg_ac(&g, 0u, g.onay);
    dz("DR");                            /* flastan yeniden kurulan */
    o = kg_acik_oturum(&g);
    if (o) {
        sayi("YANLIS", kg_basla_oku(&g, o->basla_adres, o->id + 1u, &bb));
        sayi("DOGRU", kg_basla_oku(&g, o->basla_adres, o->id, &bb));
    }
    /* RAM kaybi: yeni oturum eskisini kapatmadan baslar -> iki ACIK */
    ky_kur(&y, &g);
    basla_uret(&b, 777u);
    sayi("ID10", ky_baslat(&y, &b));
    o = kg_acik_oturum(&g);
    sayi("ACIK", o ? (int32_t)o->id : 0);
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_TARAMA)
/* B72: bos flasta kurtarma yalniz sektor BASLIKLARINI okumali; baslik
   disindaki 0xFF denetimi yalniz yazilan (bas) sektorde gerekli.
   BAS/OFSET: bas sektorun kuyrugu kirliyse yeni kayit oraya YAZILMAMALI
   (OFSET = KAYIT_SEKTOR). */
static void senaryo(void)
{
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    sayi("AC", kg_ac(&g, 0u, 0u));
    sayi("BAS", (int32_t)g.bas);
    sayi("OFSET", (int32_t)g.bas_ofset);
    metin("BITTI\n");
}
#endif

/* ── giris ── */
#if !(defined(SENARYO_BICIM) || defined(SENARYO_NOKTACI) || defined(SENARYO_GUNLUK) \
      || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI) || defined(SENARYO_DIZIN) \
      || defined(SENARYO_TARAMA))
#error "SENARYO_* tanimli degil"
#endif

int main(void)
{
    uart_baslat();
    senaryo();
    for (;;) {}
}
