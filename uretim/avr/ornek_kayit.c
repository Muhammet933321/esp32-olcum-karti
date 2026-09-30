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
    b->kal_no = 7u;
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
    || defined(SENARYO_DIZIN) || defined(SENARYO_TARAMA) || defined(SENARYO_MANTIKSAL) \
    || defined(SENARYO_YONET) || defined(SENARYO_SURUM) || defined(SENARYO_PIL)
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
/* 1C-1: OLAY ve NOT paketleri (C == Python, test_kayit.py B71.B16-B20) */
static void bicim_1c1(void)
{
    static const KayitPilAyar a = { 3.0f, 4.1875f, 86400UL, 300000UL, 200u, 1.0f };
    static const KayitDcir d = { 1u, 3.875f, 1.25f, 3.75f, 3.6875f, 0.09375f, 0.15625f,
                                 104.5f, 0.40625f };
    static const KayitPilSonuc s = { 2u, 0u, 2512.25f, 9.125f, 4.1875f, 2.9921875f,
                                     3599000UL, 12u };
    uint8_t p[KAYIT_NOT_BAS + KAYIT_NOT_METIN + 1u];
    char m[KAYIT_NOT_METIN + 4u];
    uint16_t n;
    uint8_t i;
    n = kayit_olay_ayar_paketle(1234u, &a, p);
    metin("OA "); hexdizi(p, n); satir();
    n = kayit_olay_dcir_paketle(300123UL, &d, p);
    metin("OD "); hexdizi(p, n); satir();
    n = kayit_olay_sonuc_paketle(3600000UL, &s, p);
    metin("OS "); hexdizi(p, n); satir();
    n = kayit_not_paketle(42u, KNT_NOT, 5000u, 0u,
                          "\xc5\x9f\xc3\xb6nt \"de\xc4\x9fi\xc5\x9fti\" \\ \x01" "a\xfe", p);
    metin("NT "); hexdizi(p, n); satir();
    for (i = 0; i < 118u; i++) m[i] = 'a';                 /* 118 + 2 = 120: sigar */
    m[118] = (char)0xc5; m[119] = (char)0x9f; m[120] = 0;
    n = kayit_not_paketle(7u, KNT_AD, 0u, 0u, m, p);
    metin("NT2 "); ondalik(n); satir();
    m[118] = 'a'; m[119] = (char)0xc5; m[120] = (char)0x9f; m[121] = 0;   /* 119 + 2: sigmaz */
    n = kayit_not_paketle(7u, KNT_AD, 0u, 0u, m, p);
    metin("NT3 "); ondalik(n); yaz(' '); ondalik(p[KAYIT_NOT_BAS + 118u]); satir();
    metin("TUR "); ondalik(KAYIT_T_OLAY); yaz(' '); ondalik(KAYIT_T_NOT);
    yaz(' '); ondalik(KAYIT_T_AZAMI); yaz(' '); ondalik(KAYIT_OTURUM_PIL);
    yaz(' '); ondalik(KB_SEBEP_PIL); yaz(' '); ondalik(KB_SEBEP_YENIDEN);
    yaz(' '); ondalik(KB_SEBEP_OTURUM); satir();
    {                          /* son inceleme: Ga/Ge/Gn/Gx ayristirici (B71.B21) */
        static const char *const nk[] = {
            "Ga12 ad", "Ga12", "Ga ad", "Ga0 ad", "Ga-5 ad", "Ga12x", "Ge7 a, b",
            "Gn5 not", "Gn5", "Gn5@1500 not", "Gn5@ not", "Gn5@-5 not", "Gx5:7",
            "Gx5:7@1500 yeni", "Gx5:-1 x", "Gx5 x", "Gx5:0 x", "Gn4294967297 x", "Gz5 x",
            "Gn4294967295@4294967295 son"};
        KayitNotKomut k;
        uint8_t j, r;
        for (j = 0; j < (uint8_t)(sizeof(nk) / sizeof(nk[0])); j++) {
            r = kayit_not_ayir(nk[j], &k);
            metin("NK"); ondalik(j); yaz(' '); ondalik(r); yaz(' '); ondalik(k.hedef);
            yaz(' '); ondalik(k.nokta_ms); yaz(' '); ondalik(k.degistirir); yaz(' ');
            ondalik(k.alan); yaz(' ');
            if (!r && k.metin) hexdizi((const uint8_t *)k.metin, (uint16_t)strlen(k.metin));
            satir();
        }
    }
    metin("KN "); ondalik(KN_DCIR); yaz(' ');
    ondalik(KN_YUKSEK | KN_V_HATA | KN_I_HATA | KN_V_DOYDU | KN_DURAKLAMA | KN_KAYIP_ONCE);
    satir();
}

/* 1C-2: AYRINTI kaydi (C == Python, test_kayit.py B71.B22-B23) */
static void bicim_1c2(void)
{
    uint8_t p[KAYIT_AYRINTI_BAS + 3u * KAYIT_AYRINTI_ORNEK];
    kayit_ayrinti_bas_paketle(p, 1000u, 123456UL, 4000000000UL, 3u,
                              (uint8_t)(KA_KAYIP_ONCE | KA_SILME));
    kayit_ayrinti_ornek_paketle(p + 16, 1234, -567, 0u, KAO_YUKSEK);
    kayit_ayrinti_ornek_paketle(p + 22, -32768, 32767, 500u, (uint8_t)(KAO_V_HATA | KAO_V_DOYDU));
    kayit_ayrinti_ornek_paketle(p + 28, 0, 0, 4095u, KAO_I_HATA);
    metin("AY "); hexdizi(p, (uint16_t)sizeof(p)); satir();
    metin("TUR2 "); ondalik(KAYIT_T_AYRINTI); yaz(' '); ondalik(KAYIT_T_AZAMI); satir();
}

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
    bicim_1c1();
    bicim_1c2();
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
                     (float)i * 0.5f, 0u, 0u, 0u, &c)) p_yaz(&c);
    }
    if (kn_zaman(&k, 300u, &c)) p_yaz(&c);
    metin("S1\n");

    /* S2: t=0..40 NORMAL (1000), t=45..85 YUKSEK (2000) */
    kn_baslat(&k, 100u, 0u, 0u);
    for (i = 0; i < 5; i++)
        if (kn_ornek(&k, (uint32_t)i * 10u, 0u, 1000, 10, 1.0f, 0u, 0u, 0u, &c)) p_yaz(&c);
    for (i = 0; i < 5; i++)
        if (kn_ornek(&k, 45u + (uint32_t)i * 10u, 1u, 2000, 20, 2.0f, 0u, 0u, 0u, &c)) p_yaz(&c);
    if (kn_zaman(&k, 145u, &c)) p_yaz(&c);
    metin("S2\n");

    /* S3: hatali ornek, doyma, kuyruk kaybi, uzun duraklama */
    kn_baslat(&k, 50u, 0u, 0u);
    kn_ornek(&k, 0u, 0u, 5, 1, 0.25f, 0u, 0u, 0u, &c);
    kn_ornek(&k, 10u, 0u, 9999, 1, 99.0f, KN_HATA_V, 0u, 0u, &c);
    kn_ornek(&k, 20u, 0u, 7, 3, 0.75f, 0u, 1u, 0u, &c);
    kn_kayip(&k);
    if (kn_ornek(&k, 260u, 0u, 1, 1, 1.0f, 0u, 0u, 0u, &c)) p_yaz(&c);
    if (kn_zaman(&k, 310u, &c)) p_yaz(&c);
    metin("S3\n");

    /* S4: 40 000 uc deger ornek tek noktada — int32/int64 tasmaz */
    kn_baslat(&k, 1000000UL, 0u, 0u);
    for (t = 0; t < 40000UL; t++)
        kn_ornek(&k, t, 0u, 32767, -32768, 7000.0f, 0u, 0u, 0u, &c);
    if (kn_zaman(&k, 1000000UL, &c)) p_yaz(&c);
    metin("S4\n");

    /* S5 (1C-1): ek bayrak (KN_DCIR) ornegin AIT OLDUGU noktaya. 100 ms'deki
       ornek onceki noktayi KAPATIR ve bayragi YENI noktaya verir; 200 ms'deki
       ornek 3. noktanin tek DCIR ornegi. */
    kn_baslat(&k, 100u, 0u, 0u);
    for (i = 0; i < 30; i++) {
        t = (uint32_t)i * 10u;
        if (kn_ornek(&k, t, 0u, (int16_t)(100 + i), (int16_t)(-i), (float)i * 0.5f, 0u, 0u,
                     (t == 100u || t == 110u || t == 200u) ? KN_DCIR : 0u, &c)) p_yaz(&c);
    }
    if (kn_zaman(&k, 300u, &c)) p_yaz(&c);
    metin("S5\nBITTI\n");
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

#if defined(SENARYO_MANTIKSAL)
/* B72 (son inceleme O4): MANTIKSAL bicimleme. Bicimleme = NVS'e taban
   yazmak; tabanin altindaki kayitlar yok sayilir, fiziksel silme arka
   planda (kg_temizle_adim) ya da sil-sonra-kullan ile. Dolu bolumde 2912 x
   25 ms = ~73 s surup web sunucusunu donduran fiziksel bicimlemenin yerine. */
static uint8_t tampon[600];

static void dm(const char *ad)
{
    metin(ad);
    metin(" sonraki="); ondalik(g.sonraki_sira);
    metin(" bas="); ondalik(g.bas);
    metin(" ofset="); ondalik(g.bas_ofset);
    metin(" onay="); ondalik(g.onay);
    metin(" kull="); ondalik(kg_kullanilan(&g));
    metin(" dizin="); ondalik(g.dizin_adet);
    metin(" taban="); ondalik(g.taban);
    metin(" eski="); ondalik(g.eski);
    satir();
}

static void oku(const char *ad, uint32_t sira)
{
    uint32_t ilk, son, n = kg_oku(&g, sira, tampon, sizeof(tampon), &ilk, &son);
    metin(ad); yaz(' '); ondalik(n); yaz(' '); ondalik(ilk); yaz(' '); ondalik(son); satir();
}

static void basliklar(const char *ad)
{
    uint8_t b;
    uint32_t s;
    metin(ad);
    for (s = 0; s < NOR_SEKTOR_ADET; s++) {
        f_oku(0, s * KAYIT_SEKTOR, &b, 1u);
        yaz(' '); hex8(b);
    }
    satir();
}

static void senaryo(void)
{
    uint8_t yuk[100];
    uint32_t i, s, taban, taban2, n = 0u;
    int r;
    for (i = 0; i < sizeof(yuk); i++) yuk[i] = (uint8_t)i;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u, 0u);
    for (i = 0; i < 12u; i++) kg_ekle(&g, KAYIT_T_SAAT, 1u, yuk, 100u);   /* eski: 3 sektor */
    dm("M1");
    taban = g.sonraki_sira;                  /* cagiran NVS'e ONCE bunu yazar */
    kg_bicimle_mantiksal(&g); dm("M2");
    oku("OK2", 1u);
    for (i = 0; i < 3u; i++) kg_ekle(&g, KAYIT_T_SAAT, taban, yuk, 100u);
    dm("M3");
    oku("OK3", 1u);
    kg_ac(&g, taban, g.onay); dm("M4");     /* elektrik kesildi, yeniden acilis */
    oku("OK4", 1u);
    s = 0u;
    while (s < NOR_SEKTOR_ADET) {
        r = kg_temizle_adim(&g, &s);
        if (r < 0) { sayi("THATA", r); break; }
        n += (uint32_t)r;
    }
    sayi("TEMIZ", (int32_t)n); dm("M5");
    basliklar("BAS5");
    oku("OK5", 1u);
    taban2 = g.sonraki_sira;                 /* taban NVS'e yazildi, RAM'e GECMEDEN kesildi */
    kg_ac(&g, taban2, g.onay); dm("M6");
    oku("OK6", 1u);
    kg_ekle(&g, KAYIT_T_SAAT, taban2, yuk, 12u); dm("M7");
    oku("OK7", 1u);
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_YONET) || defined(SENARYO_PIL)
/* B72 (son inceleme O1-O5): kayit YONETICISI (kayit_yonet.h) — kartin
   durum makinesi, platformsuz. Her ACILIS bir asama: `t_adim` NVS'ten okunur,
   NVS (emule, nor_flas.py) ve flas acilistan acilisa KALICI. Asama bitince
   program "BITTI" der: elektrik kesilmis gibi (BITIR yazilmaz). */
#include "kayit_yonet.h"
#define NVS_ANAHTAR (*(volatile uint8_t *)0xE7)
#define NVS_V(i)    (*(volatile uint8_t *)(0xE8 + (i)))
#define NVS_KOMUT   (*(volatile uint8_t *)0xEC)

static const char *const NVS_ADLAR[] = {"acilis", "kimlik", "taban", "onay", "kapat",
                                        "t_adim", "t_rast"};

static uint8_t nvs_sira(const char *ad)
{
    uint8_t i;
    for (i = 0; i < sizeof(NVS_ADLAR) / sizeof(NVS_ADLAR[0]); i++)
        if (!strcmp(ad, NVS_ADLAR[i])) return i;
    return 0xFFu;
}

static uint32_t nvs_oku(void *b, const char *ad, uint32_t varsayilan)
{
    (void)b;
    NVS_ANAHTAR = nvs_sira(ad);
    NVS_KOMUT = 1u;
    if (!(NVS_KOMUT & 1u)) return varsayilan;
    return (uint32_t)NVS_V(0) | ((uint32_t)NVS_V(1) << 8)
         | ((uint32_t)NVS_V(2) << 16) | ((uint32_t)NVS_V(3) << 24);
}

static int nvs_yaz(void *b, const char *ad, uint32_t v)
{
    (void)b;
    NVS_ANAHTAR = nvs_sira(ad);
    NVS_V(0) = (uint8_t)v; NVS_V(1) = (uint8_t)(v >> 8);
    NVS_V(2) = (uint8_t)(v >> 16); NVS_V(3) = (uint8_t)(v >> 24);
    NVS_KOMUT = 2u;
    return (NVS_KOMUT & 2u) ? -1 : 0;
}

static const KayitNvs NVS = { nvs_oku, nvs_yaz, 0 };
static KayitYazici y;
static KayitYonetici m;
static uint32_t k_nokta, t_ms;

static void dr(const char *ad)
{
    metin(ad);
    yaz(' '); ondalik(kyn_durum(&m));
    yaz(' '); ondalik(kyn_oturum(&m));
    yaz(' '); ondalik(g.sonraki_sira);
    yaz(' '); ondalik(g.onay);
    yaz(' '); ondalik(kg_kullanilan(&g));
    yaz(' '); ondalik((uint32_t)(-m.son_hata));
    yaz(' '); ondalik(m.kapat_id);
    yaz(' '); ondalik(m.kimlik);
    yaz(' '); ondalik(g.taban);
    satir();
}

static int noktalar(uint32_t n)
{
    KayitNokta p;
    int r = 0;
    while (n-- && !r) {
        nokta_uret(k_nokta++, &p);
        t_ms += 100u;
        r = ky_nokta(&y, &p, t_ms);
    }
    return r;
}

#endif

#if defined(SENARYO_YONET)
static void senaryo(void)
{
    KayitBasla b;
    KayitSaat z;
    uint32_t adim, i, s, n;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    ky_kur(&y, &g);
    kyn_kur(&m, &g, &y, &NVS);
    adim = nvs_oku(0, "t_adim", 0u);
    t_ms = 1000u;
    sayi("AC", kyn_ac(&m, t_ms, 0u, nvs_oku(0, "t_rast", 7u)));
    dr("D0");
    k_nokta = y.nokta_sira;
    switch (adim) {
    case 1:                                   /* kayit basla, 30 nokta, elektrik gider */
        basla_uret(&b, 100u);
        sayi("BAS", kyn_baslat(&m, &b, t_ms, 0u));
        noktalar(30u);
        ky_bosalt(&y);
        dr("D1");
        break;
    case 2:                                   /* DEVAM; halka ONAYSIZ dolar; kafada yarim yazma */
        i = 0u;
        while (!g.sektor[(g.bas + 1u) % NOR_SEKTOR_ADET].ilk && i++ < 5000u)
            if (noktalar(1u)) break;
        z.unix_s = 0u; z.kart_ms = t_ms; z.acilis = m.acilis;
        NOR_ARIZA_YAZ = 10u;                  /* SAAT kaydinin basligi yarida */
        sayi("YARIM", ky_saat(&y, &z));
        (void)NOR_KOMUT;
        dr("D2");
        break;
    case 3:                                   /* durum 4: kullanici DURDURUR */
        sayi("DUR", kyn_durdur(&m));
        dr("D3");
        break;
    case 4:                                   /* niyet NVS'ten; esitleme onaylar -> KAPANIR */
        kyn_adim(&m, g.sonraki_sira - 1u, t_ms, 0u);
        dr("D4");
        break;
    case 6:                                   /* durdurma YOK: onayla -> SURER (DEVAM) */
        kyn_adim(&m, g.sonraki_sira - 1u, t_ms, 0u);
        dr("D6");
        break;
    case 7:                                   /* kayit, bicimle, yeni kayit, elektrik gider */
        basla_uret(&b, 100u);
        kyn_baslat(&m, &b, t_ms, 0u);
        noktalar(40u);
        sayi("BIC", kyn_bicimle(&m, t_ms));
        dr("D7a");
        basla_uret(&b, 200u);
        sayi("BAS", kyn_baslat(&m, &b, t_ms, 0u));
        noktalar(10u);
        ky_bosalt(&y);
        dr("D7b");
        break;
    case 8:                                   /* yeniden acilis: eski gorunmez, temizlik */
        n = 0u;
        for (i = 0; i < 400u && m.temiz_s < NOR_SEKTOR_ADET; i++) {
            s = m.temiz_s;
            t_ms += 50u;
            kyn_adim(&m, 0u, t_ms, 0u);
            if (m.temiz_s != s) n++;
        }
        sayi("TUR", (int32_t)i);
        sayi("ILERLEME", (int32_t)n);
        dr("D8");
        for (s = 0; s < NOR_SEKTOR_ADET; s++) {
            uint8_t bb;
            f_oku(0, s * KAYIT_SEKTOR, &bb, 1u);
            metin("SB "); ondalik(s); yaz(' '); ondalik(bb);
            yaz(' '); ondalik(g.sektor[s].ilk ? 1u : 0u); satir();
        }
        break;
    case 9:                                   /* taban NVS'e YAZILAMAZSA bicimleme IPTAL */
        basla_uret(&b, 100u);
        kyn_baslat(&m, &b, t_ms, 0u);
        noktalar(20u);
        kyn_durdur(&m);
        dr("D9a");
        sayi("BIC", kyn_bicimle(&m, t_ms));
        dr("D9b");
        break;
    case 12:                                  /* onay: son gelen kazanir, sahte reddedilir */
        basla_uret(&b, 100u);
        kyn_baslat(&m, &b, t_ms, 0u);
        noktalar(20u);
        kyn_durdur(&m);
        kyn_adim(&m, 5u, t_ms, 0u);  dr("D12a");
        kyn_adim(&m, 3u, t_ms, 0u);  dr("D12b");
        kyn_adim(&m, 0xFFFFFF00UL, t_ms, 0u); dr("D12c");
        break;
    case 14:                                  /* onay NVS'ten: onaylanmis eski veri yer acar */
        basla_uret(&b, 100u);
        sayi("BAS", kyn_baslat(&m, &b, t_ms, 0u));
        sayi("YAZ", noktalar(60u));
        dr("D14");
        break;
    case 13:                                  /* durum 4'te YENI kayit: eskisi kapatilacak */
        basla_uret(&b, 300u);
        sayi("BAS", kyn_baslat(&m, &b, t_ms, 0u));
        dr("D13");
        break;
    default:
        break;
    }
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_HALKA)
/* 1C-2: ORNEK HALKASI (kayit_halka.h) — tek uretici / tek tuketici. AVR tek
   cekirdek: bariyer yalniz derleyici bariyeri (__sync_synchronize baglanmaz). */
#define KAYIT_BARIYER() __asm__ __volatile__("" ::: "memory")
#include "kayit_halka.h"
static KayitOrnek hb[8];
static KayitHalka h;

static void ornek(KayitOrnek *o, uint32_t k)
{
    o->us = 100u + k;
    o->ms = k;
    o->v = (int16_t)((int32_t)k - 4);
    o->i = (int16_t)(-(int32_t)k);
    o->bayrak = (uint8_t)(k & 0x0Fu);
}

static void ho(const char *ad, const KayitOrnek *o)
{
    metin(ad);
    yaz(' '); ondalik(o->us);
    yaz(' '); ondalik(o->ms);
    yaz(' '); ondalik((uint16_t)o->v);
    yaz(' '); ondalik((uint16_t)o->i);
    yaz(' '); ondalik(o->bayrak);
    satir();
}

static void senaryo(void)
{
    KayitOrnek o;
    uint32_t k, n, hata;
    kh_kur(&h, hb, 8u);
    for (k = 0, n = 0; k < 8u; k++) { ornek(&o, k); n += kh_it(&h, &o); }
    sayi("IT1", (int32_t)n);
    sayi("AD1", (int32_t)kh_adet(&h));
    while (kh_al(&h, &o)) ho("H1", &o);
    for (k = 0; k < 8u; k++) { ornek(&o, 20u + k); kh_it(&h, &o); }
    for (k = 0, n = 0; k < 3u; k++) { ornek(&o, 40u + k); n += kh_it(&h, &o); }
    sayi("RED", (int32_t)n);
    sayi("DUSEN", (int32_t)h.dusen);
    kh_al(&h, &o);
    ornek(&o, 50u); sayi("IT2", kh_it(&h, &o));
    kh_al(&h, &o);
    ornek(&o, 51u); sayi("IT3", kh_it(&h, &o));
    while (kh_al(&h, &o)) ho("H2", &o);
    /* sayac sarmasi */
    kh_kur(&h, hb, 8u);
    h.yaz = 0xFFFFFFF0UL;
    h.oku = 0xFFFFFFF0UL;
    for (k = 0, n = 0, hata = 0; k < 40u; k++) {
        ornek(&o, k);
        kh_it(&h, &o);
        if (k % 3u == 2u) {
            while (kh_al(&h, &o)) { if (o.us != 100u + n) hata++; n++; }
        }
    }
    while (kh_al(&h, &o)) { if (o.us != 100u + n) hata++; n++; }
    sayi("H3N", (int32_t)n);
    sayi("H3HATA", (int32_t)hata);
    sayi("H3ADET", (int32_t)kh_adet(&h));
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_PIL)
/* 1C-1: PIL TESTI OTURUMU (kayit_yonet.h). Olcum -> pil gecisi (sebep 6),
   olaylar, pil bitir, not kayitlari (baslikta oturum 0), acilista acik pil
   oturumunun KAPATILMASI (DEVAM yok), yer yokken durum 4 -> onayla kapanis.
   Her ACILIS bir asama (`t_adim`); NVS ve flas acilistan acilisa KALICI. */
static uint8_t ly[KAYIT_NOT_BAS + KAYIT_NOT_METIN + 1u];

static void basla_tur(KayitBasla *b, uint32_t hiz, uint8_t tur)
{
    basla_uret(b, hiz);
    b->oturum_turu = tur;
}

static int32_t not_yaz(uint32_t hedef, uint8_t alan, uint32_t ms, uint32_t deg,
                       const char *s)
{
    uint16_t n = kayit_not_paketle(hedef, alan, ms, deg, s, ly);
    return kyn_not(&m, ly, n);
}

static void senaryo(void)
{
    static const KayitPilAyar a = { 3.0f, 4.1875f, 86400UL, 300000UL, 200u, 1.0f };
    static const KayitDcir d = { 1u, 3.875f, 1.25f, 3.75f, 3.6875f, 0.09375f, 0.15625f,
                                 104.5f, 0.40625f };
    static const KayitPilSonuc s = { 2u, 0u, 12.5f, 0.046875f, 4.1875f, 3.0f, 5000UL, 1u };
    KayitBasla b;
    KayitSaat z;
    uint32_t adim, i;
    int32_t pil, n1, n2;
    uint16_t n;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    ky_kur(&y, &g);
    kyn_kur(&m, &g, &y, &NVS);
    adim = nvs_oku(0, "t_adim", 0u);
    t_ms = 1000u;
    sayi("AC", kyn_ac(&m, t_ms, 0u, nvs_oku(0, "t_rast", 7u)));
    dr("L0");
    k_nokta = y.nokta_sira;
    switch (adim) {
    case 1:                  /* olcum -> pil; olaylar noktalar arasinda; elektrik gider */
        basla_tur(&b, 100u, KAYIT_OTURUM_OLCUM);
        sayi("OLC", kyn_baslat(&m, &b, t_ms, 0u));
        noktalar(20u);
        basla_tur(&b, 1000u, KAYIT_OTURUM_PIL);
        sayi("PIL", kyn_baslat(&m, &b, t_ms, 0u));
        n = kayit_olay_ayar_paketle(t_ms, &a, ly);
        sayi("OA", kyn_olay(&m, ly, n));
        noktalar(15u);
        n = kayit_olay_dcir_paketle(t_ms, &d, ly);
        sayi("OD", kyn_olay(&m, ly, n));
        noktalar(10u);
        dr("L1");
        break;
    case 2:                  /* acilis (kyn_ac) acik PIL'i KAPATTI; etkin oturum yok */
        dr("L2");
        n = kayit_olay_dcir_paketle(t_ms, &d, ly);
        sayi("OY", kyn_olay(&m, ly, n));
        break;
    case 3:                  /* pil bitir; olcum surerken pil bitir; not kayitlari */
        basla_tur(&b, 1000u, KAYIT_OTURUM_PIL);
        pil = kyn_baslat(&m, &b, t_ms, 0u);
        sayi("PIL", pil);
        noktalar(12u);
        n = kayit_olay_sonuc_paketle(t_ms, &s, ly);
        sayi("PB", kyn_pil_bitir(&m, ly, n, KB_SEBEP_PIL));
        sayi("PB2", kyn_pil_bitir(&m, ly, n, KB_SEBEP_PIL));
        basla_tur(&b, 100u, KAYIT_OTURUM_OLCUM);
        sayi("OLC", kyn_baslat(&m, &b, t_ms, 0u));
        noktalar(5u);
        sayi("PB3", kyn_pil_bitir(&m, ly, n, KB_SEBEP_PIL));
        dr("L3a");
        sayi("NA1", not_yaz((uint32_t)pil, KNT_AD, 0u, 0u, "ilk ad"));
        sayi("NA2", not_yaz((uint32_t)pil, KNT_AD, 0u, 0u, "son ad"));
        n1 = not_yaz((uint32_t)pil, KNT_NOT, 1500u, 0u, "n1");
        n2 = not_yaz((uint32_t)pil, KNT_NOT, 0u, 0u, "n2");
        sayi("N1", n1);
        sayi("N2", n2);
        sayi("NX1", not_yaz((uint32_t)pil, KNT_NOT, 0u, (uint32_t)n1, "n1b"));   /* @ yok: yer KORUNUR */
        sayi("NX2", not_yaz((uint32_t)pil, KNT_NOT, 0u, (uint32_t)n2, ""));
        sayi("NG0", not_yaz(0u, KNT_AD, 0u, 0u, "yok"));
        sayi("NGB", not_yaz(g.sonraki_sira, KNT_AD, 0u, 0u, "gelecek"));
        noktalar(5u);
        sayi("DUR", kyn_durdur(&m));
        dr("L3b");
        break;
    case 4:                  /* PIL basla, halka ONAYSIZ dolar; kafada yarim yazma */
        basla_tur(&b, 1000u, KAYIT_OTURUM_PIL);
        sayi("PIL", kyn_baslat(&m, &b, t_ms, 0u));
        i = 0u;
        while (!g.sektor[(g.bas + 1u) % NOR_SEKTOR_ADET].ilk && i++ < 5000u)
            if (noktalar(1u)) break;
        z.unix_s = 0u; z.kart_ms = t_ms; z.acilis = m.acilis;
        NOR_ARIZA_YAZ = 10u;                  /* SAAT kaydinin basligi yarida */
        sayi("YARIM", ky_saat(&y, &z));
        (void)NOR_KOMUT;
        dr("L4");
        break;
    case 5:                  /* yer yok: PIL acik bekler (durum 4); onay -> KAPANIR */
        dr("L5a");
        kyn_adim(&m, g.sonraki_sira - 1u, t_ms, 0u);
        dr("L5b");
        break;
    default:
        break;
    }
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_KALGEC)
/* 1B: KALIBRASYON GECMISI (kalgec.h). Her ACILIS bir asama (`t_adim`);
   NVS (emule, ADA gore blob) acilistan acilisa KALICI. */
#include "kalgec.h"
#define NVS_ANAHTAR (*(volatile uint8_t *)0xE7)
#define NVS_V(i)    (*(volatile uint8_t *)(0xE8 + (i)))
#define NVS_KOMUT   (*(volatile uint8_t *)0xEC)
#define NVS_AD      (*(volatile uint8_t *)0xED)
#define NVS_BLOB    (*(volatile uint8_t *)0xEE)
#define NVS_BOS     (*(volatile uint8_t *)0xEF)

static uint32_t t_adim_oku(void)
{
    NVS_ANAHTAR = 5u;                          /* nor_flas.NVS_ADLAR: t_adim */
    NVS_KOMUT = 1u;
    if (!(NVS_KOMUT & 1u)) return 0u;
    return (uint32_t)NVS_V(0) | ((uint32_t)NVS_V(1) << 8);
}

static void kn_ad(const char *ad)
{
    while (*ad) NVS_AD = (uint8_t)*ad++;
}

static int kn_oku(void *b, const char *ad, void *h, uint32_t n)
{
    uint8_t *p = (uint8_t *)h;
    uint32_t i, uz;
    (void)b;
    kn_ad(ad);
    NVS_KOMUT = 3u;
    if (!(NVS_KOMUT & 1u)) return -1;
    uz = (uint32_t)NVS_V(0) | ((uint32_t)NVS_V(1) << 8);
    if (uz != n) return -1;
    for (i = 0; i < n; i++) p[i] = NVS_BLOB;
    return 0;
}

static int kn_yaz(void *b, const char *ad, const void *k, uint32_t n)
{
    const uint8_t *p = (const uint8_t *)k;
    uint32_t i;
    (void)b;
    for (i = 0; i < n; i++) NVS_BLOB = p[i];
    kn_ad(ad);
    NVS_KOMUT = 4u;
    return (NVS_KOMUT & 2u) ? -1 : 0;
}

static uint32_t kn_bos(void *b)
{
    (void)b;
    return NVS_BOS;
}

static const KalNvs KNVS = { kn_oku, kn_yaz, kn_bos, 0 };
static KalGecmis m;
static KayitKalibrasyon simdiki;

/* test_kayit.py _kal_uret() ile AYNI (butun kesirler ikili) */
static void kal_uret(KayitKalibrasyon *k, uint32_t t)
{
    memset(k, 0, sizeof(*k));
    k->normal.n = 16.5f;
    k->normal.pga = 2.0f;
    k->normal.kazanc = 1.0f + (float)t / 1024.0f;
    k->normal.sifir_ham = (int16_t)(-12 + (int16_t)t);
    k->normal.tau = 0.0029296875f;
    k->yuksek.n = 312.5f;
    k->yuksek.pga = 2.0f;
    k->yuksek.kazanc = 0.9921875f;
    k->yuksek.sifir_ham = 5;
    k->yuksek.tau = 0.0030517578125f;
    k->i_ofset = -3;
    k->i_pga = 0.25f;
    k->sont_ohm = 0.0048828125f;
    k->i_duzeltme = 1.0f;
    k->sebeke_hz = 50.0f;
    k->faz_kal_us[0] = 12.5f;
    k->faz_kal_us[1] = -3.25f;
}

/* <ad> adet son_no taslak son_hata son_tur son_kaynak */
static void kd(const char *ad)
{
    metin(ad);
    yaz(' '); ondalik(m.adet);
    yaz(' '); ondalik(m.son_var ? m.son.no : 0u);
    yaz(' '); ondalik((uint32_t)kgc_taslak(&m, &simdiki));
    yaz(' '); ondalik((uint32_t)(-m.son_hata));
    yaz(' '); ondalik(m.son.tur);
    yaz(' '); ondalik(m.son.kaynak);
    satir();
}

/* KE no donus tur kaynak not(hex) */
static void ke(uint32_t no)
{
    KalKayit e;
    int r;
    memset(&e, 0, sizeof(e));
    r = kgc_oku(&m, no, &e);
    metin("KE "); ondalik(no);
    yaz(' '); ondalik((uint32_t)(-r));
    yaz(' '); ondalik(e.tur);
    yaz(' '); ondalik(e.kaynak);
    yaz(' '); hexdizi((const uint8_t *)e.not_, (uint16_t)strlen(e.not_));
    satir();
}

/* n tane 'a' + kuyruk; calisma aninda kurulur (AVR'de dizgeler RAM'de) */
static char nb[48];
static const char *dolgu(uint8_t n, const char *kuyruk)
{
    uint8_t i = 0u;
    while (i < n) nb[i++] = 'a';
    while (*kuyruk && i < sizeof(nb) - 1u) nb[i++] = *kuyruk++;
    nb[i] = 0;
    return nb;
}

/* <ad> <not(hex)>: #2'nin notunu duzelt, geri oku */
static void nt(const char *ad, const char *s)
{
    KalKayit e;
    memset(&e, 0, sizeof(e));
    kgc_duzenle(&m, 2u, -1, s);
    kgc_oku(&m, 2u, &e);
    metin(ad);
    yaz(' '); hexdizi((const uint8_t *)e.not_, (uint16_t)strlen(e.not_));
    satir();
}

static void senaryo(void)
{
    uint32_t adim = t_adim_oku(), t;
    int32_t r;
    uint8_t uy = 0u;
    kal_uret(&simdiki, 0u);
    switch (adim) {
    case 1:                                   /* C1: ilk acilis -> #1 (ilk) */
        sayi("AC", kgc_ac(&m, &KNVS, &simdiki, 100u, 1u));
        kd("C1");
        break;
    case 2:                                   /* C2-C4 */
        kgc_ac(&m, &KNVS, &simdiki, 150u, 2u);
        kal_uret(&simdiki, 1u);
        kd("C2a");
        sayi("KAY", kgc_kaydet(&m, &simdiki, KGT_DONANIM, "sont 5 mohm", 200u, 2u));
        kd("C2b");
        sayi("OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 201u, 2u));
        kal_uret(&simdiki, 2u);
        sayi("OTNO2", (int32_t)kgc_oturum_no(&m, &simdiki, 202u, 2u));
        kd("C4");
        break;
    case 3:                                   /* C5-C6: acilis + duzenleme */
        kal_uret(&simdiki, 2u);
        kgc_ac(&m, &KNVS, &simdiki, 300u, 3u);
        kd("C5");
        ke(3u);
        ke(2u);
        sayi("DUZ", kgc_duzenle(&m, 2u, KGT_INCE, "ince ayar notu"));
        break;
    case 4:                                   /* C6 kalici mi · C7: `adet` yazilamaz */
        kal_uret(&simdiki, 2u);
        kgc_ac(&m, &KNVS, &simdiki, 400u, 4u);
        ke(2u);
        kal_uret(&simdiki, 3u);
        sayi("YETIM", kgc_kaydet(&m, &simdiki, KGT_BELIRSIZ, "yetim", 401u, 4u));
        kd("C7a");
        break;
    case 5:                                   /* C7: acilis sonrasi yetim uzerine */
        kal_uret(&simdiki, 3u);
        kgc_ac(&m, &KNVS, &simdiki, 500u, 5u);
        kd("C7b");
        sayi("KAY4", kgc_kaydet(&m, &simdiki, KGT_INCE, "dorduncu", 501u, 5u));
        ke(4u);
        break;
    case 6:                                   /* C8: 40 dolar -> acik hata */
        kal_uret(&simdiki, 3u);
        kgc_ac(&m, &KNVS, &simdiki, 600u, 6u);
        for (t = 10u; m.adet < KALGEC_AZAMI && t < 200u; t++) {
            if (!uy && kgc_dolmak_uzere(&m)) { uy = 1u; sayi("UY", (int32_t)m.adet); }
            kal_uret(&simdiki, t);
            if (kgc_kaydet(&m, &simdiki, KGT_INCE, "dolgu", 600u + t, 6u) < 0) break;
        }
        sayi("ADET", (int32_t)m.adet);
        kal_uret(&simdiki, 999u);
        sayi("DOLU", kgc_kaydet(&m, &simdiki, KGT_INCE, "fazla", 900u, 6u));
        sayi("OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 901u, 6u));
        sayi("HATA", m.son_hata);
        break;
    case 7:                                   /* C9: NVS'te yer yok */
        r = kgc_ac(&m, &KNVS, &simdiki, 700u, 7u);
        sayi("AC", r);
        kd("C9");
        sayi("OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 701u, 7u));
        break;
    case 8:                                   /* C10: Turkce not, JSON'u bozan karakterler */
        kgc_ac(&m, &KNVS, &simdiki, 800u, 8u);
        kal_uret(&simdiki, 5u);
        r = kgc_kaydet(&m, &simdiki, KGT_DONANIM,
                       "T\xc3\xbcrk\xc3\xa7" "e \"not\" \\ \xc5\x9f\xc3\xb6nt de\xc4\x9fi\xc5\x9fti \xc4\x9f\xc3\xbc",
                       801u, 8u);
        sayi("KAY", r);
        if (r > 0) ke((uint32_t)r);
        /* C10b: 31 bayt siniri 2/3/4 baytlik karakterin ORTASINA duser;
           gecersiz UTF-8 (cp1254 terminal, kopuk dizi, asiri uzun, vekil) atilir */
        nt("N1", dolgu(30u, "\xc5\x9f"));
        nt("N2", dolgu(29u, "\xc5\x9f"));
        nt("N3", dolgu(29u, "\xe2\x82\xac"));
        nt("N4", dolgu(28u, "\xe2\x82\xac"));
        nt("N5", dolgu(28u, "\xf0\x9f\x94\x8b"));
        nt("N6", dolgu(27u, "\xf0\x9f\x94\x8b"));
        nt("N7", dolgu(0u, "a\xfe" "b\x80" "c\xc5" "d\xc0\xaf" "e\xed\xa0\x80" "f\xe2\x82"
                           "g\xf5\x80\x80\x80" "h\xe0\x80\x80" "i\xf4\x90\x80\x80" "j\xc5"));
        nt("N8", dolgu(0u, "\xfe\xf0\xfd\xe7x"));
        break;
    case 9:                                   /* C11-C12: sifir ofseti gecmise girmez; A->B->A */
        kgc_ac(&m, &KNVS, &simdiki, 900u, 9u);          /* #1 = kal_uret(0) = A */
        simdiki.normal.sifir_ham = 77;
        simdiki.yuksek.sifir_ham = -40;
        simdiki.i_ofset = 9;
        kd("C11a");
        sayi("S_KAY", kgc_kaydet(&m, &simdiki, KGT_INCE, "sifir", 901u, 9u));
        sayi("S_OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 902u, 9u));
        kd("C11b");
        simdiki.sont_ohm = 0.015625f;                    /* B: sont degisti */
        sayi("B_OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 903u, 9u));
        simdiki.sebeke_hz = 60.0f;                       /* C: sebeke de */
        sayi("C_OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 904u, 9u));
        kal_uret(&simdiki, 0u);                          /* A'ya don (sifirlar yine farkli) */
        simdiki.i_ofset = -8;
        kd("C12a");
        sayi("A_OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 905u, 9u));
        sayi("A_KAY", kgc_kaydet(&m, &simdiki, KGT_INCE, "A", 906u, 9u));
        simdiki.sont_ohm = 0.015625f;                    /* B'ye don */
        sayi("B2_OTNO", (int32_t)kgc_oturum_no(&m, &simdiki, 907u, 9u));
        kd("C12b");
        break;
    case 10:                                  /* C12c: ayni degerli iki kayit -> EN YENISI */
        kgc_ac(&m, &KNVS, &simdiki, 1000u, 10u);
        sayi("YENI", (int32_t)kgc_oturum_no(&m, &simdiki, 1001u, 10u));
        kd("C12c");
        break;
    default:
        break;
    }
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_SURUM)
/* 1B: BASLA surum 2 (102 B, kal_no) ve surum 1 (98 B, 1A-2 firmware'i) —
   kg_basla_oku ikisini de okumali: yukseltmeden once acilmis oturum
   DEVAM edebilsin. */
static void senaryo(void)
{
    uint8_t p[KAYIT_BASLA_BAYT], p1[KAYIT_BASLA_V1_BAYT];
    KayitBasla b, bb;
    int32_t id[2];
    uint16_t i, j;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    kg_ac(&g, 0u, 0u);
    basla_uret(&b, 250u);
    kayit_basla_paketle(&b, p);
    id[0] = kg_ekle(&g, KAYIT_T_BASLA, g.sonraki_sira, p, KAYIT_BASLA_BAYT);
    memcpy(p1, p, KAYIT_BASLA_V1_BAYT);
    p1[2] = 1u;
    p1[3] = 0u;
    id[1] = kg_ekle(&g, KAYIT_T_BASLA, g.sonraki_sira, p1, KAYIT_BASLA_V1_BAYT);
    kg_ac(&g, 0u, 0u);
    for (j = 0; j < 2u; j++) {
        for (i = 0; i < g.dizin_adet; i++) {
            if (g.dizin[i].id != (uint32_t)id[j]) continue;
            memset(&bb, 0, sizeof(bb));
            metin("BV ");
            ondalik((uint32_t)(-kg_basla_oku(&g, g.dizin[i].basla_adres, (uint32_t)id[j], &bb)));
            yaz(' '); ondalik(bb.bicim_surum);
            yaz(' '); ondalik(bb.kal_no);
            yaz(' '); ondalik(bb.hiz_ms);
            satir();
        }
    }
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
      || defined(SENARYO_TARAMA) || defined(SENARYO_MANTIKSAL) || defined(SENARYO_YONET) \
      || defined(SENARYO_SURUM) || defined(SENARYO_KALGEC) || defined(SENARYO_PIL) \
      || defined(SENARYO_HALKA))
#error "SENARYO_* tanimli degil"
#endif

int main(void)
{
    uart_baslat();
    senaryo();
    for (;;) {}
}
