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

/* AVR tek cekirdek: bariyer yalniz derleyici bariyeri (__sync_synchronize
   AVR'de baglanmaz). kayit_oturum.h kayit_halka.h'yi dahil ediyor: EN BASTA. */
#define KAYIT_BARIYER() __asm__ __volatile__("" ::: "memory")
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
    || defined(SENARYO_YONET) || defined(SENARYO_SURUM) || defined(SENARYO_PIL) \
    || defined(SENARYO_AYRINTI) || defined(SENARYO_HAZIR) || defined(SENARYO_SKOP)
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

static KULLANILMAYABILIR const KayitFlas FLAS = { f_oku, f_yaz, f_sil, 0 };
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

/* 1C-3: SKOP kaydi (iki parca, 0. parca META) ve SKOP_KAL olayi */
static void bicim_1c3(void)
{
    static const int16_t mv[17] = { -12, 120, 330, 541, 752, 963, 1174, 1385, 1596,
                                    1807, 2018, 2229, 2440, 2651, 2862, 3073, 3184 };
    KayitSkopMeta m;
    uint8_t p[KAYIT_SKOP_PARCA_BAS + KAYIT_SKOP_META + 3u * 2u];
    uint8_t q[KAYIT_SKOP_PARCA_BAS + 2u * 2u];
    uint8_t o[KAYIT_OLAY_AZAMI];
    uint16_t n;
    m.t_ms = 123456UL; m.sure_ms = 250UL; m.hz = 83333UL; m.tdiv_us = 200UL;
    m.adim = 0.03125f; m.ofset = -1.25f; m.tetik = 1234u; m.esik = 2048u;
    m.kip = 1u; m.tetiklendi = 1u; m.kenar = 0u; m.histerezis = 300u; m.on_yuzde = 25u; m.onay = 2u;
    kayit_skop_parca_paketle(p, 7u, 0u, 3u, 5u, 0u);
    kayit_skop_meta_paketle(p + KAYIT_SKOP_PARCA_BAS, &m);
    kayit_y16(p + 48, 0u); kayit_y16(p + 50, 4095u); kayit_y16(p + 52, 2048u);
    kayit_skop_parca_paketle(q, 7u, 3u, 2u, 5u, 1u);
    kayit_y16(q + 12, 1u); kayit_y16(q + 14, 4094u);
    metin("SK0 "); hexdizi(p, (uint16_t)sizeof(p)); satir();
    metin("SK1 "); hexdizi(q, (uint16_t)sizeof(q)); satir();
    n = kayit_olay_skop_kal_paketle(98765UL, mv, o);
    metin("SKAL "); hexdizi(o, n); satir();
    metin("TUR3 "); ondalik(KAYIT_T_SKOP); yaz(' '); ondalik(KAYIT_T_AZAMI); yaz(' ');
    ondalik(KAYIT_OTURUM_SKOP); satir();
}

/* 1C-4: PLAN olayi ve sebep 7 */
static void bicim_1c4(void)
{
    KayitPlanOlay po;
    uint8_t o[KAYIT_OLAY_AZAMI];
    uint16_t n;
    po.bas_unix = 1790000000UL; po.sure_s = 21600UL; po.hiz_ms = 60000UL; po.plan_no = 3u;
    n = kayit_olay_plan_paketle(424242UL, &po, o);
    metin("PLAN "); hexdizi(o, n); satir();
    metin("SEB7 "); ondalik(KB_SEBEP_PLAN); satir();
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
    bicim_1c3();
    bicim_1c4();
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
    sayi("EK9", kg_ekle(&g, 200u, 0u, yuk, 12u));   /* 1C-2: 9 artik AYRINTI */
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

#if defined(SENARYO_YONET) || defined(SENARYO_PIL) || defined(SENARYO_AYRINTI) \
    || defined(SENARYO_HAZIR) || defined(SENARYO_SKOP)
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

static KULLANILMAYABILIR int noktalar(uint32_t n)
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

#if defined(SENARYO_AYRINTI)
/* 1C-2: AYRINTILI KIP YAZICISI (kayit_oturum.h ky_ayrinti_*). Sentetik ornek
   dizisi test_kayit.py _ayr_uret ile AYNI: 2000 us periyot +-200 us titresim,
   k=100'de +30 ms ve k=250'de +20 ms bosluk, k=299 DUSER (k=300 KO_KAYIP_ONCE),
   bayrak her 50 ornekte degisir. Asama 1: 0..399, elektrik gider. Asama 2:
   DEVAM, 400..639 YENI ACILISIN saatiyle (micros sifirdan: 500 ms + ...),
   5 s bosaltma, tamponda ornek varken durdur; noktali oturumda ornek reddi.
   Asama 3 (ayri flas): bolmeden sonra yazma HATASI, kalan tamponda. */
static void ayr_uret(uint32_t k, KayitOrnek *o)
{
    uint32_t us = k >= 400u ? 500000UL + 2000UL * (k - 400u)
                : 1000000UL + 2000UL * k + (k >= 100u ? 30000UL : 0u)
                  + (k >= 250u ? 20000UL : 0u);
    us = us + (k * 37u) % 401u - 200u;
    o->us = us;
    o->ms = us / 1000u;
    o->v = (int16_t)((int32_t)(k * 13u) - 500);
    o->i = (int16_t)(-(int32_t)(k * 7u));
    o->bayrak = (uint8_t)((k / 50u) & 0x0Fu);
    if (k == 300u) o->bayrak = (uint8_t)(o->bayrak | KO_KAYIP_ONCE);
}

static void ayr_besle(uint32_t bas, uint32_t son)
{
    KayitOrnek o;
    uint32_t k;
    int r;
    for (k = bas; k < son; k++) {
        if (k == 299u) continue;
        ayr_uret(k, &o);
        r = ky_ayrinti_ornek(&y, &o, o.ms);
        if (r) { sayi("AYHATA", r); return; }
    }
}

/* Asama 3: sektoru R (8..36) ornek kalana dek doldur; A = R + 20 ornek
   biriktir (tampon siniri: AVR'de kucuk);
   16.38 ms'yi asan ornek bosaltmayi tetikler: R ornek bu sektore, KALAN yeni
   sektore giderken TEKRAR yazimi HATA verir (kalan tamponda, t0'i kaydirilmis).
   Sonraki ornek son ornekten R x 2 ms + 5 ms sonra: dogru nicem > 4095 ->
   yeni kayit; eski origine gore (a_q duzeltilmemis) 5 ms gorunur -> 2R ms hata.
   v = 3000 + k (test_kayit.py zamani k'den kurar). */
static void a3_ver(uint32_t k, uint32_t us, KayitOrnek *o)
{
    o->us = us;
    o->ms = us / 1000u;
    o->v = (int16_t)(3000u + k);
    o->i = (int16_t)(-(int32_t)k);
    o->bayrak = 0u;
    (void)ky_ayrinti_ornek(&y, o, o->ms);
}

static void ayr3_hata(void)
{
    const uint32_t sabit = KAYIT_BASLIK_BAYT + KAYIT_AYRINTI_BAS + KY_BITIR_PAY;
    KayitOrnek o;
    uint32_t k = 0u, R = 0u, A, j, n, us = 2000000UL, t_son;
    for (j = 0u; j < 300u; j++) {
        uint32_t kalan = KAYIT_SEKTOR - g.bas_ofset;
        R = kalan >= sabit + KAYIT_AYRINTI_ORNEK ? (kalan - sabit) / KAYIT_AYRINTI_ORNEK : 0u;
        if (R >= 8u && R <= 36u && R + 4u <= KAYIT_AYRINTI_TAMPON) break;
        for (n = 0u; n < 20u; n++, k++, us += 2000u) a3_ver(k, us, &o);
        ky_zaman(&y, o.ms + 5000u);
    }
    sayi("R3", (int32_t)R);
    sayi("K0", (int32_t)k);
    A = R + 20u;
    if (A > KAYIT_AYRINTI_TAMPON) A = KAYIT_AYRINTI_TAMPON;
    sayi("A3", (int32_t)A);
    for (n = 0u; n < A; n++, k++, us += 2000u) a3_ver(k, us, &o);
    t_son = us - 2000u;
    NOR_ARIZA_YAZ = (uint8_t)(kayit_toplam_bayt(KAYIT_AYRINTI_BAS + R * KAYIT_AYRINTI_ORNEK) + 5u);
    a3_ver(k, t_son + 17000u, &o); k++;           /* tetik: bolme, TEKRAR yarida */
    sayi("KALAN3", y.a_adet);
    a3_ver(k, t_son + R * 2000u + 5000u, &o); k++;
    for (n = 0u; n < 4u; n++, k++) a3_ver(k, t_son + R * 2000u + 7000u + 2000u * n, &o);
}

static void senaryo(void)
{
    KayitBasla b;
    KayitNokta p;
    KayitOrnek o;
    uint32_t adim, t;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    ky_kur(&y, &g);
    kyn_kur(&m, &g, &y, &NVS);
    adim = nvs_oku(0, "t_adim", 0u);
    t_ms = 1000u;
    sayi("AC", kyn_ac(&m, t_ms, 0u, nvs_oku(0, "t_rast", 7u)));
    dr("R0");
    switch (adim) {
    case 1:
        basla_uret(&b, 0u);                       /* hiz_ms 0 = AYRINTILI */
        sayi("BAS", kyn_baslat(&m, &b, t_ms, 0u));
        sayi("AYR", y.ayrinti);
        nokta_uret(0u, &p);
        sayi("NK", ky_nokta(&y, &p, t_ms));       /* ayrintili oturumda nokta YOK */
        ayr_besle(0u, 400u);
        dr("R1");
        break;
    case 2:                                       /* DEVAM: ayrintili surer */
        sayi("AYR", y.ayrinti);
        ayr_besle(400u, 601u);
        sayi("TAMP1", y.a_adet);
        t = y.yuk_ilk_ms;
        ky_zaman(&y, t + 4999u);
        sayi("TAMP2", y.a_adet);
        ky_zaman(&y, t + 5000u);
        sayi("TAMP3", y.a_adet);
        ayr_besle(601u, 640u);                    /* son inceleme: Gd kuyrugu */
        sayi("TAMP4", y.a_adet);
        sayi("DUR", kyn_durdur(&m));
        basla_uret(&b, 100u);                     /* noktali oturum: ornek YOK */
        kyn_baslat(&m, &b, t_ms, 0u);
        ayr_uret(700u, &o);
        sayi("AO", ky_ayrinti_ornek(&y, &o, o.ms));
        sayi("DUR2", kyn_durdur(&m));
        dr("R2");
        break;
    case 3:                                       /* son inceleme: bolme + yazma hatasi */
        basla_uret(&b, 0u);
        sayi("BAS3", kyn_baslat(&m, &b, t_ms, 0u));
        ayr3_hata();
        sayi("DUR3", kyn_durdur(&m));
        break;
    default:
        break;
    }
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_HAZIR)
/* 1C-2: HAZIR ALAN (kayit_gunluk.h kg_on_sil_adim, kayit_yonet.h kyn_adim).
   Silmeler SAYILIR (FLAS_SAY sarmalayicisi). Hedef derleme basina:
   -DKYN_HAZIR_HEDEF (A: 5, B: 100). Asama 1 doldur + onayla (arka sektor
   HARIC) · 2 (A) on silme + ayrintili kayit · 3 (A) izin/oturum/aralik +
   bicimleme · 4 (B) onaysizda dur, hepsi onayli iken bile bas sektor korunur ·
   5 (A, ayri flas) GF! sonrasi hemen ayrintili kayit: temizlik durur, kirli
   silme sayilir ve isaretlenir. */
static uint32_t sil_say = 0u;
static int say_sil(void *b, uint32_t a)
{
    sil_say++;
    return f_sil(b, a);
}
static const KayitFlas FLAS_SAY = { f_oku, f_yaz, say_sil, 0 };

static void doldur(void)          /* halka ONAYSIZ dolar ama DOLU'ya dusmez */
{
    uint32_t i = 0u;
    while (!g.sektor[(g.bas + 1u) % NOR_SEKTOR_ADET].ilk && i++ < 20000u)
        if (noktalar(1u)) break;
}

static void adim_n(uint32_t n)    /* n x 100 ms gorev turu */
{
    while (n--) {
        t_ms += 100u;
        kyn_adim(&m, 0u, t_ms, 0u);
    }
}

/* Son inceleme: CEKIRDEK 1'i taklit eder (kayit_esp.h kayit_ornek). Ornekler
   16'lik partiler halinde "itilir" (zaman o anda), gorev partiyi sonra bosaltir
   — halkada bekleyen ornekler silmeden ONCE uretilmistir. Kirli sektor silmesi
   iki cekirdegi ~25 ms durdurur: itme aninda `kirli_sil` degistiyse saat 25 ms
   atlar ve ornek KO_SILME_ONCE tasir (kart da boyle isaretler). */
#define Z_PARTI 16u
static KayitOrnek z_parti[Z_PARTI];
static uint32_t z_us = 5000000UL, z_k = 0u, z_gordum = 0u;
static uint32_t z_durus = 25000UL;           /* kirli silme durusu; asama 5: 10 ms */

static void z_besle(uint32_t n, uint8_t adim)
{
    uint32_t j, a;
    while (n) {
        for (a = 0u; a < Z_PARTI && n; a++, n--) {
            KayitOrnek *o = &z_parti[a];
            o->bayrak = 0u;
            if (g.kirli_sil != z_gordum) {
                z_us += z_durus * (g.kirli_sil - z_gordum);
                o->bayrak = KO_SILME_ONCE;
                z_gordum = g.kirli_sil;
            }
            o->us = z_us;
            o->ms = z_us / 1000u;
            o->v = (int16_t)(z_k & 0x7FFFu);
            o->i = (int16_t)(-(int16_t)(z_k & 0x3FFFu));
            z_us += 2000UL;
            z_k++;
        }
        for (j = 0u; j < a; j++) ky_ayrinti_ornek(&y, &z_parti[j], t_ms);
        t_ms += 2u * a;
        if (adim) kyn_adim(&m, 0u, t_ms, 0u);
    }
}

static void senaryo(void)
{
    KayitBasla b;
    uint32_t adim, s0, k, j, onay, kk;
    kg_kur(&g, &FLAS_SAY, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    ky_kur(&y, &g);
    kyn_kur(&m, &g, &y, &NVS);
    adim = nvs_oku(0, "t_adim", 0u);
    t_ms = 1000u;
    sayi("AC", kyn_ac(&m, t_ms, 0u, nvs_oku(0, "t_rast", 7u)));
    sayi("HZ0", (int32_t)g.hazir);
    k_nokta = y.nokta_sira;
    switch (adim) {
    case 1:
        basla_uret(&b, 100u);
        kyn_baslat(&m, &b, t_ms, 0u);
        doldur();
        kyn_durdur(&m);
        s0 = sil_say;
        adim_n(20u);                              /* izin KAPALI (varsayilan) */
        sayi("KAPALI", (int32_t)(sil_say - s0));
        onay = g.sektor[(g.bas + NOR_SEKTOR_ADET - 1u) % NOR_SEKTOR_ADET].ilk - 1u;
        kyn_adim(&m, onay, t_ms, 0u);
        sayi("ONAY", (int32_t)onay);
        sayi("BAS", (int32_t)g.bas);
        dr("Z1");
        break;
    case 2:
        m.on_sil_izin = 1u;
        s0 = sil_say;
        adim_n(1u);                               /* izin acildiktan 100 ms (< KYN_TEMIZ_MS): HENUZ yok */
        sayi("HZ4", (int32_t)g.hazir);
        adim_n(200u);
        sayi("HZ", (int32_t)g.hazir);
        sayi("SIL2", (int32_t)(sil_say - s0));
        basla_uret(&b, 0u);                       /* ayrintili */
        kyn_baslat(&m, &b, t_ms, 0u);
        s0 = sil_say;
        z_gordum = g.kirli_sil;
        onay = g.kirli_sil;
        while (g.hazir && z_k < 20000u) z_besle(Z_PARTI, 0u);
        sayi("HAZIRDA", (int32_t)(sil_say - s0));
        z_besle(150u, 0u);                        /* ~2 kirli sektor; halka 3. asamaya yetsin */
        do { k = g.kirli_sil; z_besle(Z_PARTI, 0u); } while (g.kirli_sil != k);
        sayi("SONRA", (int32_t)(sil_say - s0));
        sayi("KIRLI2", (int32_t)(g.kirli_sil - onay));
        sayi("DUR", kyn_durdur(&m));
        dr("Z2");
        break;
    case 3:
        m.on_sil_izin = 1u;
        adim_n(10u);                              /* ilk tur izin gecisi; sonra silebilir */
        basla_uret(&b, 100u);
        kyn_baslat(&m, &b, t_ms, 0u);
        s0 = sil_say;
        adim_n(20u);
        sayi("OTURUMDA", (int32_t)(sil_say - s0));
        kyn_durdur(&m);
        m.on_sil_izin = 0u;
        s0 = sil_say;
        adim_n(20u);
        sayi("IZINSIZ", (int32_t)(sil_say - s0));
        m.on_sil_izin = 1u;
        s0 = sil_say;
        adim_n(1u);                               /* < KYN_TEMIZ_MS */
        sayi("HEMEN", (int32_t)(sil_say - s0));
        adim_n(20u);
        sayi("SONRA3", (int32_t)(sil_say - s0));
        sayi("HZ3", (int32_t)g.hazir);
        sayi("YAC", kg_ac(&g, 0u, g.onay));       /* AYNI surecte yeniden acilis (RAM dolu) */
        sayi("YACHZ", (int32_t)g.hazir);
        adim_n(20u);                              /* ayni sektorler yeniden hazir: bicim sinansin */
        sayi("HZ5", (int32_t)g.hazir);
        sayi("BIC", kyn_bicimle(&m, t_ms));       /* bicimden sonra silme YOK: Z2/Z6 flasi okur */
        sayi("BICHZ", (int32_t)g.hazir);
        break;
    case 4:                                       /* B: onaysizda durur; hepsi onayli: bas korunur */
        m.on_sil_izin = 1u;
        adim_n(300u);
        sayi("HZB1", (int32_t)g.hazir);
        sayi("BAS", (int32_t)g.bas);
        kyn_adim(&m, g.sonraki_sira - 1u, t_ms, 0u);
        adim_n(100u);
        sayi("HZB2", (int32_t)g.hazir);
        break;
    case 5:                                     /* son inceleme: GF! sonrasi hemen Gb0 */
        sayi("BIC5", kyn_bicimle(&m, t_ms));     /* butun sektorler ESKI, flas kirli */
        z_durus = 10000UL;                        /* < 16.38 ms: bosluk KAYIT ICINDE kalirdi */
        m.on_sil_izin = 1u;
        basla_uret(&b, 0u);
        sayi("BAS5", kyn_baslat(&m, &b, t_ms, 0u));
        s0 = sil_say;
        onay = g.kirli_sil;
        z_gordum = g.kirli_sil;
        k = g.bas;
        j = 0u;
        while (j < 3u && z_k < 20000u) {          /* uc sektor ilerle; gorev turu her partide */
            z_besle(Z_PARTI, 1u);
            j += (g.bas + NOR_SEKTOR_ADET - k) % NOR_SEKTOR_ADET;
            k = g.bas;
        }
        do { kk = g.kirli_sil; z_besle(Z_PARTI, 1u); } while (g.kirli_sil != kk);
        j += (g.bas + NOR_SEKTOR_ADET - k) % NOR_SEKTOR_ADET;
        sayi("ILERLE5", (int32_t)j);
        sayi("SIL5", (int32_t)(sil_say - s0));
        sayi("KIRLI5", (int32_t)(g.kirli_sil - onay));
        sayi("DUR5", kyn_durdur(&m));
        break;
    default:
        break;
    }
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_HALKA)
/* 1C-2: ORNEK HALKASI (kayit_halka.h) — tek uretici / tek tuketici. Bariyer
   dosyanin basinda tanimli. */
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
    {   /* H4: kirli silme isareti (ksi_*): kanit bosluk, dusen isaret korunur */
        KayitSilmeIsaret s;
        uint32_t us = 1000000UL, ms = 1000u, i;
        ksi_esitle(&s, 0u);
        sayi("A0", ksi_ornek(&s, 0u, us, ms));                 /* degisim yok */
        us += 6000u; ms += 6u;                                 /* ms CIFT: 1006 */
        sayi("A1", ksi_ornek(&s, 1u, us, ms));                 /* sayac artti, durus YOK */
        ksi_itildi(&s, 1u, 0u);
        us += 27000u; ms += 27u;
        n = ksi_ornek(&s, 1u, us, ms);                         /* durustan sonra */
        sayi("A2", (int32_t)n);
        ksi_itildi(&s, 1u, (uint8_t)n);
        us += 6000u; ms += 6u;
        sayi("A3", ksi_ornek(&s, 1u, us, ms));                 /* isaret tuketildi */
        us += 27000u; ms += 27u;
        sayi("B1", ksi_ornek(&s, 2u, us, ms));                 /* durus, ama itme DUSER */
        ksi_itildi(&s, 2u, 0u);
        us += 6000u; ms += 6u;
        n = ksi_ornek(&s, 2u, us, ms);                         /* kanit SURER */
        sayi("B2", (int32_t)n);
        ksi_itildi(&s, 2u, (uint8_t)n);
        us = 5000000UL; ms = 2000u;                            /* kisa silme: bosluk yok */
        (void)ksi_ornek(&s, 2u, us, ms);                       /* zaman tabani (sayac ayni) */
        for (i = 0u, n = 0u; i < 40u && !n; i++) {
            us += 6000u; ms += 6u;
            n = ksi_ornek(&s, 3u, us, ms);
        }
        sayi("CMS", (int32_t)ms);
        ksi_itildi(&s, 3u, (uint8_t)n);
        ksi_esitle(&s, 5u);                                    /* ayrintili degilken */
        us += 60000u; ms += 60u;
        sayi("D1", ksi_ornek(&s, 5u, us, ms));
    }
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

#if defined(SENARYO_SKOP)
/* 1C-3: OSILOSKOP GUNLUGU YAZICISI (kayit_oturum.h ky_skop, kayit_yonet.h
   kyn_skop). Yakalama kodu kod(k, no) = (37k + 101no + 11) & 0xFFF (test_kayit.py
   _skop_kod ile AYNI); AVR'de 2 KB RAM: en fazla 240 ornek. Asama 1: SKOP
   oturumu (hiz 0) iki yakalama; OLCUM'e eklenen yakalama noktalarin arasinda;
   ayrintili OLCUM'e eklenen yakalama ornek tamponundan sonra; acik SKOP oturumu,
   elektrik gider. Asama 2: acilis (SKOP sebep 5). Asama 3 (ayri flas): DOLU. */
#define SK_AZAMI 240u
static uint16_t sk_kod[SK_AZAMI];

static void sk_meta(uint32_t no, KayitSkopMeta *mt)
{
    mt->t_ms = 1000u + no; mt->sure_ms = 50u + no; mt->hz = 83333UL; mt->tdiv_us = 200u;
    mt->adim = 0.03125f; mt->ofset = -1.25f; mt->tetik = (uint16_t)(3u * no); mt->esik = 2048u;
    mt->kip = 1u; mt->tetiklendi = 1u; mt->kenar = 0u; mt->histerezis = 40u;
    mt->on_yuzde = 25u; mt->onay = 2u;
}

static int sk_yaz(uint32_t no, uint16_t n)
{
    KayitSkopMeta mt;
    uint16_t k;
    for (k = 0u; k < n; k++) sk_kod[k] = (uint16_t)((37u * k + 101u * no + 11u) & 0xFFFu);
    sk_meta(no, &mt);
    return kyn_skop(&m, &mt, sk_kod, n, no);
}

static void senaryo(void)
{
    KayitBasla b;
    KayitNokta p;
    KayitOrnek o;
    uint32_t adim, j;
    int r = 0;
    kg_kur(&g, &FLAS, NOR_SEKTOR_ADET, sektor, dizin, DIZIN_KAP);
    ky_kur(&y, &g);
    kyn_kur(&m, &g, &y, &NVS);
    adim = nvs_oku(0, "t_adim", 0u);
    t_ms = 1000u;
    sayi("AC", kyn_ac(&m, t_ms, 0u, nvs_oku(0, "t_rast", 7u)));
    switch (adim) {
    case 1:
        basla_uret(&b, 0u);                       /* SKOP oturumu: hiz 0 = her tetik */
        b.oturum_turu = KAYIT_OTURUM_SKOP;
        kyn_baslat(&m, &b, t_ms, 0u);
        sayi("OT1", kyn_oturum(&m));
        sayi("AYR3", y.ayrinti);
        nokta_uret(0u, &p);
        sayi("NK3", ky_nokta(&y, &p, t_ms));
        o.us = 5000u; o.ms = 5u; o.v = 1; o.i = 2; o.bayrak = 0u;
        sayi("AO3", ky_ayrinti_ornek(&y, &o, t_ms));
        sayi("SK1", sk_yaz(1u, SK_AZAMI));
        sayi("SK2", sk_yaz(2u, 100u));
        sayi("DUR1", kyn_durdur(&m));
        basla_uret(&b, 100u);                     /* OLCUM'e eklenen yakalama */
        kyn_baslat(&m, &b, t_ms, 0u);
        sayi("OT4", kyn_oturum(&m));
        noktalar(5u);
        sayi("SK4", sk_yaz(1u, 50u));
        noktalar(5u);
        sayi("DUR4", kyn_durdur(&m));
        basla_uret(&b, 0u);                       /* ayrintili OLCUM'e eklenen yakalama */
        kyn_baslat(&m, &b, t_ms, 0u);
        sayi("OT8", kyn_oturum(&m));
        for (j = 0u; j < 10u; j++) {
            o.us = 9000000UL + 2000UL * j; o.ms = o.us / 1000u;
            o.v = (int16_t)j; o.i = (int16_t)(-(int16_t)j); o.bayrak = 0u;
            ky_ayrinti_ornek(&y, &o, t_ms);
        }
        sayi("ATAMP0", y.a_adet);
        sayi("SK8", sk_yaz(1u, 30u));
        sayi("ATAMP", y.a_adet);
        sayi("DUR8", kyn_durdur(&m));
        basla_uret(&b, 2000u);                    /* acik SKOP oturumu: elektrik gider */
        b.oturum_turu = KAYIT_OTURUM_SKOP;
        kyn_baslat(&m, &b, t_ms, 0u);
        sayi("OT5", kyn_oturum(&m));
        sayi("SK5", sk_yaz(1u, 20u));
        dr("S1");
        break;
    case 2:                                       /* acilis: SKOP oturumu sebep 5, DEVAM yok */
        dr("S2");
        break;
    case 3:                                       /* ayri flas: onaysiz doldur -> DOLU */
        basla_uret(&b, 0u);
        b.oturum_turu = KAYIT_OTURUM_SKOP;
        kyn_baslat(&m, &b, t_ms, 0u);
        sayi("OT6", kyn_oturum(&m));
        for (j = 1u; j < 100u && !r; j++) r = sk_yaz(j, SK_AZAMI);
        sayi("SKN", (int32_t)(j - 1u));
        sayi("SKR", r);
        sayi("OTUR6", kyn_oturum(&m));
        break;
    default:
        break;
    }
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_PLAN)
/* 1C-4: ZAMANLANMIS KAYIT KARAR MANTIGI (kayit_plan.h). NVS emule (nor_flas.py,
   acilistan acilisa KALICI); saat ve oturum taklit. Her asama bir acilis:
   1 R1/R2/R4/R5/R7/R8/R9 + R3 hazirligi · 2 R3 gec baslama · 3 R6 DEVAM'li
   oturumda bitis, saat geri, suren planda kur reddi · 4 R6 DEVAM alamadi. */
#include "kayit_plan.h"
#define NVS_ANAHTAR (*(volatile uint8_t *)0xE7)
#define NVS_V(i)    (*(volatile uint8_t *)(0xE8 + (i)))
#define NVS_KOMUT   (*(volatile uint8_t *)0xEC)

static const char *const NVS_ADLAR[] = {"acilis", "kimlik", "taban", "onay", "kapat",
                                        "t_adim", "t_rast", "pl_bas", "pl_sure", "pl_hiz",
                                        "pl_no", "pl_dur", "pl_ot", "pl_bu"};

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
static KayitPlan p;

static void pd(const char *ad, uint8_t e)
{
    metin(ad);
    yaz(' '); ondalik(e);
    yaz(' '); ondalik(p.durum);
    yaz(' '); ondalik(p.oturum);
    satir();
}

static uint8_t adim_bas(const char *ad, uint32_t t, uint8_t mesgul, uint32_t id)
{
    uint8_t e = plan_adim(&p, t, mesgul, id);
    pd(ad, e);
    if (e == PE_BASLAT) plan_basliyor(&p, t);
    return e;
}

#define T0 1800000000UL                       /* gercekci unix (KP_ZAMAN alt siniri 1.7e9) */

static void senaryo(void)
{
    uint32_t adim = nvs_oku(0, "t_adim", 0u);
    plan_ac(&p, &NVS);
    pd("AC", 0u);
    switch (adim) {
    case 1:
        sayi("K1", plan_kur(&p, T0 + 1000u, 60u, 200u, T0 + 900u));
        adim_bas("R1a", T0 + 950u, 0u, 0u);
        adim_bas("R1b", T0 + 1000u, 0u, 0u);
        adim_bas("R1x", T0 + 1001u, 1u, 55u);     /* baska oturum belirdi: BENIMSENMEZ */
        adim_bas("R1y", T0 + 999u, 0u, 0u);       /* NTP saati 1 s GERI aldi: zaman asimi DEGIL */
        sayi("S1", plan_sonuc(&p, 77));           /* cekirdek 0: planin oturumu 77 */
        pd("R1c", 0u);
        sayi("S1b", plan_sonuc(&p, 78));          /* ikinci (yinelenen) sonuc ALINMAZ */
        adim_bas("R1d", T0 + 1059u, 1u, 77u);
        adim_bas("R1e", T0 + 1060u, 1u, 77u);
        adim_bas("R1f", T0 + 1061u, 0u, 0u);
        adim_bas("R7", T0 + 1070u, 0u, 0u);
        sayi("K2", plan_kur(&p, T0 + 2000u, 60u, 200u, T0 + 1900u));
        adim_bas("R2a", T0 + 2000u, 1u, 0u);      /* mesgul (oturumsuz pil testi dahil) */
        adim_bas("R2b", T0 + 2001u, 0u, 0u);
        sayi("K4", plan_kur(&p, T0 + 4000u, 100u, 200u, T0 + 3900u));
        adim_bas("R4", T0 + 4200u, 0u, 0u);
        sayi("K5a", plan_kur(&p, T0 + 5000u, 100u, 200u, 0u));
        sayi("K5b", plan_kur(&p, T0 + 5000u, 100u, 200u, T0 + 4900u));
        adim_bas("R5a", 0u, 0u, 0u);
        adim_bas("R5b", T0 + 5000u, 0u, 0u);
        adim_bas("R9a", T0 + 5005u, 0u, 0u);
        adim_bas("R9b", T0 + 5011u, 0u, 0u);      /* sonuc gelmedi: BASLATILAMADI */
        sayi("S9", plan_sonuc(&p, 66));           /* GEC sonuc: alinmaz (yapistirici kapatir) */
        pd("R9c", 0u);
        sayi("K8", plan_kur(&p, T0 + 6000u, 100u, 200u, T0 + 5900u));
        plan_iptal(&p);
        adim_bas("R8a", T0 + 6000u, 0u, 0u);
        sayi("KS", plan_kur(&p, T0 + 6500u, PLAN_SURE_AZAMI + 1u, 200u, T0 + 6400u));
        sayi("KG", plan_kur(&p, T0 + 6000u, 100u, 200u, T0 + 6400u));
        sayi("KZa", plan_kur(&p, 20u, 0u, 200u, T0 + 6400u));            /* '+' unutuldu */
        sayi("KZb", plan_kur(&p, T0 + 6400u + 400u * 86400u, 10u, 200u, T0 + 6400u));
        sayi("K10", plan_kur(&p, T0 + 6500u, 0u, 200u, T0 + 6400u));     /* sure 0 = Gd'ye dek */
        adim_bas("R10a", T0 + 6500u, 0u, 0u);
        plan_sonuc(&p, 91);
        adim_bas("R10b", T0 + 99999u, 1u, 91u);
        adim_bas("R10c", T0 + 100000u, 0u, 0u);
        sayi("K11", plan_kur(&p, T0 + 200000u, 60u, 200u, T0 + 199000u));
        adim_bas("R11a", T0 + 200000u, 0u, 0u);
        plan_sonuc(&p, -1);                       /* cekirdek 0: DOLU */
        pd("R11b", 0u);
        sayi("K12", plan_kur(&p, T0 + 250000u, 60u, 200u, T0 + 249000u));
        adim_bas("R12a", T0 + 250000u, 0u, 0u);
        plan_sonuc(&p, 0);                        /* cekirdek 0: kuyrukta onde Gb vardi: MESGUL */
        pd("R12b", 0u);
        sayi("K3", plan_kur(&p, T0 + 300000u, 100u, 200u, T0 + 299900u));
        break;
    case 2:                                   /* kart 300000'de kapaliydi: GEC basla */
        adim_bas("R3a", T0 + 300050u, 0u, 0u);
        plan_sonuc(&p, 90);
        adim_bas("R3b", T0 + 300051u, 1u, 90u);
        break;                                /* elektrik gider: SURUYOR, oturum 90 */
    case 3:                                   /* oturum DEVAM aldi */
        adim_bas("R6a", T0 + 300060u, 1u, 90u);
        adim_bas("R6b", T0 + 299990u, 1u, 90u);  /* saat GERI: yeniden baslama yok */
        adim_bas("R6c", T0 + 300100u, 1u, 90u);
        sayi("K6", plan_kur(&p, T0 + 400000u, 100u, 200u, T0 + 300100u));
        break;
    case 4:                                   /* DEVAM alamadi: oturum yok */
        adim_bas("R6d", T0 + 300101u, 0u, 0u);
        adim_bas("R6e", T0 + 300102u, 0u, 0u);
        sayi("K13", plan_kur(&p, T0 + 400000u, 50u, 200u, T0 + 399900u));
        adim_bas("R13a", T0 + 400000u, 0u, 0u);  /* BASLAT, sonuc gelmeden elektrik gider */
        break;
    case 5:                                   /* acilis: SURUYOR ama oturum bilinmiyor */
        adim_bas("R13b", T0 + 400010u, 1u, 33u);
        break;
    default:
        break;
    }
    metin("BITTI\n");
}
#endif

#if defined(SENARYO_GUV)
/* 1D: ESLESTIRME + IMZALI ISTEK (guvenlik.h). Kriptografi sinama SHA-256'sindan
   (sha256_sinama.h, RFC vektorleriyle olculur), NVS emule (ADA gore blob,
   acilistan acilisa KALICI). Vektorler uretim/vektor_guvenlik.json'dan -D ile
   gelir (test_kayit.py derler). Asamalar: 1 vektorler + eslestirme + imza +
   tekrar + doluluk · 2 kalicilik, yeni acilis, silme · 3 ayar kaliciligi.
   ⚠ ATmega328p 2 KB RAM: etiketler flasta (PSTR), her adim ayri NOINLINE islev,
   guvenlik.h islevleri GUV_ISLEV ile noinline (yoksa yigin tasiyordu). */
#include <avr/pgmspace.h>
#define GUV_SINAMA 1
#define GUV_ISLEV static __attribute__((noinline, unused))
#define GUV_CTX_BOYU 176u          /* sinama HMAC'i 169 B; kartta 224 */
#define GUV_NEFES_ARALIK 2u        /* sinamada her 2 turda bir nefes (kartta 1000) */
#include "sha256_sinama.h"
#include "guvenlik.h"
_Static_assert(sizeof(SsHmac) <= GUV_CTX_BOYU, "GUV_CTX_BOYU sinama HMAC'ina yetmiyor");
#define NVS_ANAHTAR (*(volatile uint8_t *)0xE7)
#define NVS_V(i)    (*(volatile uint8_t *)(0xE8 + (i)))
#define NVS_KOMUT   (*(volatile uint8_t *)0xEC)
#define NVS_AD      (*(volatile uint8_t *)0xED)
#define NVS_BLOB    (*(volatile uint8_t *)0xEE)
#define STR_(x) #x
#define STR(x) STR_(x)
#define NI __attribute__((noinline))
/* vektor imzalari flasta (RAM'de 5 x 65 B yer tutuyordu); kullanirken yigina kopyalanir */
static const char V_KANIT[] PROGMEM = STR(GUV_V_KANIT);
static const char V_GET[] PROGMEM = STR(GUV_V_IMZA_GET);
static const char V_POST[] PROGMEM = STR(GUV_V_IMZA_POST);
static const char V_AKIS[] PROGMEM = STR(GUV_V_IMZA_AKIS);
static const char V_SORGU[] PROGMEM = STR(GUV_V_IMZA_GET_SORGU);
#define VK(isim, t) strcpy_P((t), (isim))

static uint32_t t_adim_oku(void)
{
    NVS_ANAHTAR = 5u;                          /* nor_flas.NVS_ADLAR: t_adim */
    NVS_KOMUT = 1u;
    if (!(NVS_KOMUT & 1u)) return 0u;
    return (uint32_t)NVS_V(0) | ((uint32_t)NVS_V(1) << 8);
}

static void gv_ad(const char *ad)
{
    while (*ad) NVS_AD = (uint8_t)*ad++;
}

static int gv_oku(void *b, const char *ad, void *h, uint16_t n)
{
    uint8_t *p = (uint8_t *)h;
    uint16_t i, uz;
    (void)b;
    gv_ad(ad);
    NVS_KOMUT = 3u;
    if (!(NVS_KOMUT & 1u)) return -1;                      /* YOK */
    uz = (uint16_t)(NVS_V(0) | ((uint16_t)NVS_V(1) << 8));
    if (uz != n) return -2;                                /* BOZUK (boy) */
    for (i = 0; i < n; i++) p[i] = NVS_BLOB;
    return 0;
}

static int gv_yaz(void *b, const char *ad, const void *k, uint16_t n)
{
    const uint8_t *p = (const uint8_t *)k;
    uint16_t i;
    (void)b;
    for (i = 0; i < n; i++) NVS_BLOB = p[i];
    gv_ad(ad);
    NVS_KOMUT = 4u;
    return (NVS_KOMUT & 2u) ? -1 : 0;
}

/* sinama rastgelesi: xorshift32, tohum acilisa gore (acilis nonce'u her acilista farkli) */
static uint32_t rs;
static void gv_rastgele(uint8_t *h, uint16_t n)
{
    while (n--) {
        rs ^= rs << 13; rs ^= rs >> 17; rs ^= rs << 5;
        *h++ = (uint8_t)(rs >> 8);
    }
}

static const GuvNvs GNVS = { gv_oku, gv_yaz, 0 };
static uint8_t gv_bit_hata = 0;               /* U17: kriptografi hatasi enjeksiyonu */
static uint8_t gv_bit_tek = 0;                /* U17H: yalniz SONRAKI cagri hata */
static uint16_t gv_nefes_say = 0;
static int gv_hmac_bit(void *ctx, uint8_t c[32])
{
    int r = ss_hmac_bit(ctx, c);
    if (gv_bit_tek) {
        gv_bit_tek = 0;
        return -1;
    }
    return gv_bit_hata ? -1 : r;
}
static void gv_nefes(void) { gv_nefes_say++; }
static const GuvKripto GK = { ss_hmac_bas, ss_hmac_ekle, gv_hmac_bit, ss_sha_bas,
                              ss_sha_ekle, ss_sha_bit, gv_rastgele, gv_nefes };
static GuvDurum g;
static uint8_t K4[32];                         /* cihaz 4'un K'si (test tarafi hesaplar) */
static const char PAROLA[] = "dogru-parola-12";

static void metin_P(const char *p)
{
    char c;
    while ((c = (char)pgm_read_byte(p++))) yaz(c);
}
#define KOD(ad, r) kod_P(PSTR(ad), (r))
#define HEXS(ad, v) hexs_P(PSTR(ad), (v))
static NI void kod_P(const char *ad, int r)
{
    metin_P(ad); yaz(' ');
    if (r < 0) { yaz('-'); r = -r; }
    ondalik((uint32_t)r); satir();
}
static NI void hexs_P(const char *ad, const uint8_t *v) { metin_P(ad); yaz(' '); hexdizi(v, 32); satir(); }

static void hexten(const char *h, uint8_t *v, uint8_t n)
{
    uint8_t i, a, b;
    for (i = 0; i < n; i++) {
        a = (uint8_t)h[2 * i]; b = (uint8_t)h[2 * i + 1];
        a = (uint8_t)(a <= '9' ? a - '0' : a - 'a' + 10);
        b = (uint8_t)(b <= '9' ? b - '0' : b - 'a' + 10);
        v[i] = (uint8_t)((a << 4) | b);
    }
}

static void hexyaz(const uint8_t *v, uint8_t n, char *h)
{
    static const char x[] PROGMEM = "0123456789abcdef";
    uint8_t i;
    for (i = 0; i < n; i++) {
        h[2 * i] = (char)pgm_read_byte(&x[v[i] >> 4]);
        h[2 * i + 1] = (char)pgm_read_byte(&x[v[i] & 15u]);
    }
    h[2 * n] = 0;
}

static NI void dec64(uint64_t v, char *t)
{
    char r[21];
    uint8_t n = 0;
    do { r[n++] = (char)('0' + (uint8_t)(v % 10u)); v /= 10u; } while (v);
    while (n) *t++ = r[--n];
    *t = 0;
}

/* TEST TARAFI BAGIMSIZ YENIDEN YAZIM (spec K5/K6): HMAC(P, etiket \n kimlik \n nk \n nc \n son) */
static NI void t_hmac_es(const uint8_t P[32], const char *etiket, const uint8_t nk[16],
                         const uint8_t nc[16], const char *son, uint8_t c[32])
{
    SsHmac m;
    char h[33];
    ss_hmac_bas(&m, P, 32);
    ss_hmac_ekle(&m, etiket, (uint16_t)strlen(etiket));
    ss_hmac_ekle(&m, "\n", 1);
    hexyaz(g.ayar.kimlik, 8, h); ss_hmac_ekle(&m, h, 16); ss_hmac_ekle(&m, "\n", 1);
    hexyaz(nk, 16, h); ss_hmac_ekle(&m, h, 32); ss_hmac_ekle(&m, "\n", 1);
    hexyaz(nc, 16, h); ss_hmac_ekle(&m, h, 32); ss_hmac_ekle(&m, "\n", 1);
    ss_hmac_ekle(&m, son, (uint16_t)strlen(son));
    ss_hmac_bit(&m, c);
}

static NI void govde_ozet(const char *govde, uint8_t oz[32])
{
    SsSha sh;
    ss_sha_bas(&sh); ss_sha_ekle(&sh, govde, (uint16_t)strlen(govde)); ss_sha_bit(&sh, oz);
}

/* TEST TARAFI imzalayici, sorgusuz (spec K9): OK1\n Y \n yol \n acilis \n s \n sha(govde) */
static NI void t_imzala(const uint8_t K[32], const char *y, const char *yol, uint64_t s,
                        const char *govde, char imza[65])
{
    SsHmac m;
    uint8_t oz[32];
    char t[65];
    govde_ozet(govde, oz);
    ss_hmac_bas(&m, K, 32);
    ss_hmac_ekle(&m, "OK1\n", 4);
    ss_hmac_ekle(&m, y, (uint16_t)strlen(y)); ss_hmac_ekle(&m, "\n", 1);
    ss_hmac_ekle(&m, yol, (uint16_t)strlen(yol)); ss_hmac_ekle(&m, "\n", 1);
    guv_acilis_hex(&g, t); ss_hmac_ekle(&m, t, 32); ss_hmac_ekle(&m, "\n", 1);
    dec64(s, t); ss_hmac_ekle(&m, t, (uint16_t)strlen(t)); ss_hmac_ekle(&m, "\n", 1);
    hexyaz(oz, 32, t); ss_hmac_ekle(&m, t, 64);
    ss_hmac_bit(&m, oz);
    hexyaz(oz, 32, imza);
}

/* kartin dogrulamasi: guv_imza_bas/arg/bit (args: ad, deger, ..., 0) */
static NI int dogrula(uint8_t n, const char *y, const char *yol, const char *const *args,
                      uint64_t s, const char *govde, const char *imza)
{
    GuvImza im;
    uint8_t oz[32], i;
    int r = guv_imza_bas(&g, &im, n, y, yol);
    if (r) return r;
    for (i = 0; args && args[i]; i += 2) guv_imza_arg(&g, &im, args[i], args[i + 1]);
    govde_ozet(govde, oz);
    return guv_imza_bit(&g, &im, s, oz, imza, 1800000000UL);
}

/* t_imzala + dogrula ayni sayacla (cihaz 4, sorgusuz) */
static NI int imza_dene(const char *y, const char *yol, uint64_t s)
{
    char t[65];
    t_imzala(K4, y, yol, s, "", t);
    return dogrula(4u, y, yol, 0, s, "", t);
}

static NI uint8_t say_var(void)
{
    GuvCihaz c;
    uint8_t i, n = 0;
    for (i = 1; i <= GUV_CIHAZ_AZAMI; i++) if (!guv_cihaz_oku(&g, i, &c)) n++;
    return n;
}

static NI void hexsatir_kisa(const char *onek_P, const uint8_t *v, uint8_t n)
{
    char h[33];
    hexyaz(v, n, h); metin_P(onek_P); yaz(' '); metin(h); satir();
}

/* ── asama 1 ── */
static NI void a1_kripto(void)
{
    SsHmac m;
    uint8_t k1[20], c[32];
    memset(k1, 0x0b, sizeof(k1));
    ss_hmac_bas(&m, k1, 20); ss_hmac_ekle(&m, "Hi There", 8); ss_hmac_bit(&m, c); HEXS("H1", c);
    ss_hmac_bas(&m, (const uint8_t *)"Jefe", 4);
    ss_hmac_ekle(&m, "what do ya want for nothing?", 28); ss_hmac_bit(&m, c); HEXS("H2", c);
    /* U2: PBKDF2 artik CEKIRDEGIN (guv_pbkdf2, tablo HMAC'i + nefes) — RFC 7914 ve tur 3 */
    KOD("PB1R", guv_pbkdf2(&GK, "passwd", (const uint8_t *)"salt", 4, 1, c)); HEXS("PB1", c);
    { uint8_t tuz[16], i; uint16_t n0 = gv_nefes_say;
      for (i = 0; i < 16u; i++) tuz[i] = (uint8_t)(0xA0u + i);
      KOD("PB3R", guv_pbkdf2(&GK, PAROLA, tuz, 16, 3, c)); HEXS("PB3", c);
      KOD("NEF", (int)(gv_nefes_say - n0)); }
}

static NI void a1_vektor(void)
{
    uint8_t kim[8], tuz[16], nk[16], nc[16], kk[32], kart[32], n = 0, i;
    GuvCihaz c;
    int r;
    hexten("a1b2c3d4e5f60718", kim, 8);
    for (i = 0; i < 16u; i++) tuz[i] = (uint8_t)(0xA0u + i);
    guv__sinama_ayar(&g, kim, tuz, 2u);
    KOD("UP", guv_p_hesapla(&g, PAROLA));      /* kartta cekirdek 1 (guv_isle) hesaplar */
    r = guv_esles_usb(&g, "usb1", 1800000000UL, &n, kk); KOD("USB1", r ? r : n);
    r = guv_esles_usb(&g, "usb2", 1800000000UL, &n, kk); KOD("USB2", r ? r : n);
    for (i = 0; i < 16u; i++) { nk[i] = (uint8_t)(0x10u + i); nc[i] = (uint8_t)(0x40u + i); }
    guv__sinama_bekleyen(&g, 7u, nk, nc, "PC \xc4\x9f", 1000UL);
    { char t[65]; VK(V_KANIT, t); hexten(t, kk, 32); }
    r = guv_esles_kanit(&g, 7u, kk, 1500UL, 1800000000UL, &n, kart);
    KOD("U3", r); KOD("U3N", n); HEXS("U3KK", kart);
    if (!guv_cihaz_oku(&g, 3u, &c)) HEXS("U3K", c.K);
}

static NI void a1_imza_vektor(void)
{
    static const char *const SORGU_DOGRU[] = {"sira", "12", "not", "a&b=c \xc4\x9f", 0};
    static const char *const SORGU_BOL[] = {"sira", "12", "not", "a", "b", "c \xc4\x9f", 0};
    uint8_t a[16];
    char t[65];
    hexten("0f1e2d3c4b5a69788796a5b4c3d2e1f0", a, 16);
    guv__sinama_acilis(&g, a);
    VK(V_GET, t); KOD("U4A", dogrula(3u, "GET", "/kayit/liste", 0, 1u, "", t));
    VK(V_POST, t); KOD("U4B", dogrula(3u, "POST", "/komut", 0, 2u, "Go1234", t));
    VK(V_AKIS, t); KOD("U4C", dogrula(3u, "GET", "/akis", 0, 7u, "", t));
    VK(V_SORGU, t);
    KOD("U4D", dogrula(3u, "GET", "/kayit/veri", SORGU_DOGRU, 1759000000123ULL, "", t));
    /* U10a Review Focus 1: not='a&b=c' yerine not=a & b=c olarak sunulan ayni imza */
    KOD("U10A", dogrula(3u, "GET", "/kayit/veri", SORGU_BOL, 1759000000124ULL, "", t));
}

static NI void a1_eslesme(void)
{
    uint8_t eno = 0, n = 0, nk[16], nc[16], kk[32], P[32], i;
    GuvCihaz c;
    int r;
    for (i = 0; i < 16u; i++) nc[i] = (uint8_t)(0x60u + i);
    /* U5 parola: 9 karakter ve bos; bos ad */
    KOD("U5A", guv_p_hesapla(&g, "kisa-9chr"));
    KOD("U5D", guv_esles_baslat(&g, "tel", nc, 2000UL, &eno, nk));   /* P yok: PAROLA */
    KOD("U5B", guv_p_hesapla(&g, ""));
    KOD("U5E", guv_p_hesapla(&g, PAROLA));
    KOD("U5C", guv_esles_baslat(&g, "", nc, 2000UL, &eno, nk));
    /* U6 tam eslestirme (kartin nk'si rastgele; istemci kaniti TEST TARAFINDA bagimsiz) */
    r = guv_esles_baslat(&g, "telefon", nc, 10000UL, &eno, nk);
    KOD("U6A", r);
    ss_pbkdf2(PAROLA, g.ayar.tuz, 16, g.ayar.tur, P);
    t_hmac_es(P, "OK1-istemci", nk, nc, "telefon", kk);
    r = guv_esles_kanit(&g, eno, kk, 11000UL, 1800000000UL, &n, K4);
    KOD("U6B", r); KOD("U6N", n);
    t_hmac_es(P, "OK1-kart", nk, nc, "4", kk);
    KOD("U6KART", !memcmp(kk, K4, 32));
    t_hmac_es(P, "OK1-anahtar", nk, nc, "4", K4);
    KOD("U6K", !guv_cihaz_oku(&g, 4u, &c) && !memcmp(c.K, K4, 32));
}

static NI void a1_deneme(void)
{
    uint8_t eno = 0, n = 0, nk[16], nc[16], kk[32], P[32], i;
    for (i = 0; i < 16u; i++) nc[i] = (uint8_t)(0x60u + i);
    /* U7 deneme siniri: 1 s, sonra 2 s; basarida sifirlanir */
    memset(kk, 0, sizeof(kk));
    KOD("U7A", guv_esles_baslat(&g, "x", nc, 20000UL, &eno, nk));
    KOD("U7B", guv_esles_kanit(&g, eno, kk, 20100UL, 1800000000UL, &n, P));
    KOD("U7C", guv_esles_baslat(&g, "x", nc, 20200UL, &eno, nk));
    KOD("U7D", guv_esles_baslat(&g, "x", nc, 21100UL, &eno, nk));
    KOD("U7E", guv_esles_kanit(&g, eno, kk, 21200UL, 1800000000UL, &n, P));
    KOD("U7F", guv_esles_baslat(&g, "x", nc, 23100UL, &eno, nk));
    KOD("U7G", guv_esles_baslat(&g, "x", nc, 23200UL, &eno, nk));
    ss_pbkdf2(PAROLA, g.ayar.tuz, 16, g.ayar.tur, P);
    t_hmac_es(P, "OK1-istemci", nk, nc, "x", kk);
    KOD("U7H", guv_esles_kanit(&g, eno, kk, 23300UL, 1800000000UL, &n, P));
    memset(kk, 0, sizeof(kk));
    KOD("U7I", guv_esles_baslat(&g, "y", nc, 23400UL, &eno, nk));
    KOD("U7J", guv_esles_kanit(&g, eno, kk, 23500UL, 1800000000UL, &n, P));
    KOD("U7K", guv_esles_baslat(&g, "y", nc, 24400UL, &eno, nk));
    KOD("U7L", guv_esles_baslat(&g, "y", nc, 24500UL, &eno, nk));
    /* U7M/N her bekleyen eslestirme TEK deneme: yanlistan sonra dogru kanit da YOK */
    KOD("U7M", guv_esles_kanit(&g, eno, kk, 24600UL, 1800000000UL, &n, P));
    ss_pbkdf2(PAROLA, g.ayar.tuz, 16, g.ayar.tur, P);
    t_hmac_es(P, "OK1-istemci", nk, nc, "y", kk);
    KOD("U7N", guv_esles_kanit(&g, eno, kk, 24700UL, 1800000000UL, &n, P));
    /* U8 60 s zaman asimi (dogru kanitla bile) */
    KOD("U8A", guv_esles_baslat(&g, "z", nc, 30000UL, &eno, nk));
    ss_pbkdf2(PAROLA, g.ayar.tuz, 16, g.ayar.tur, P);
    t_hmac_es(P, "OK1-istemci", nk, nc, "z", kk);
    KOD("U8B", guv_esles_kanit(&g, eno, kk, 90001UL, 1800000000UL, &n, P));
}

static NI void a1_pencere(void)
{
    char h[65];
    /* U9 tekrar penceresi (cihaz 4, test tarafi imzalar) */
    KOD("U9A", imza_dene("GET", "/pil", 10u));
    KOD("U9B", imza_dene("GET", "/pil", 10u));
    KOD("U9C", imza_dene("GET", "/pil", 12u));
    KOD("U9D", imza_dene("GET", "/pil", 11u));
    KOD("U9E", imza_dene("GET", "/pil", 11u));
    KOD("U9F", imza_dene("GET", "/pil", 200u));
    KOD("U9G", imza_dene("GET", "/pil", 136u));
    KOD("U9H", imza_dene("GET", "/pil", 137u));
    /* U9b sahte imza buyuk sayacla pencereyi ILERLETEMEZ */
    memset(h, '0', 64); h[64] = 0;
    KOD("U9I", dogrula(4u, "GET", "/pil", 0, 100000u, "", h));
    KOD("U9J", imza_dene("GET", "/pil", 201u));
    KOD("U9K", imza_dene("GET", "/pil", 0u));
    /* U9L son karakteri degismis gecerli imza (ilk baytlar ayni): sabit zamanli TAM karsilastirma */
    t_imzala(K4, "GET", "/pil", 500u, "", h);
    h[63] = (char)(h[63] == '0' ? '1' : '0');
    KOD("U9L", dogrula(4u, "GET", "/pil", 0, 500u, "", h));
    h[63] = (char)(h[63] == '0' ? '1' : '0');
    t_imzala(K4, "GET", "/pil", 500u, "", h);
    KOD("U9M", dogrula(4u, "GET", "/pil", 0, 500u, "", h));
}

static NI void a1_degisiklik(void)
{
    static const char *const SORGU_EK[] = {"x", "1", 0};
    char s[65];
    uint8_t a[16], b[16];
    /* U10 tek degisiklik (U9L sayaci 500'e tasidi) = ret (yontem, yol, arguman, govde, acilis) */
    t_imzala(K4, "GET", "/kayit/liste", 600u, "", s);
    KOD("U10B", dogrula(4u, "POST", "/kayit/liste", 0, 600u, "", s));
    KOD("U10C", dogrula(4u, "GET", "/kayit/veri", 0, 600u, "", s));
    KOD("U10D", dogrula(4u, "GET", "/kayit/liste", SORGU_EK, 600u, "", s));
    KOD("U10E", dogrula(4u, "GET", "/kayit/liste", 0, 600u, "x", s));
    memcpy(b, g.acilis, 16); memcpy(a, g.acilis, 16); a[0] ^= 1u;
    guv__sinama_acilis(&g, a);
    KOD("U10F", dogrula(4u, "GET", "/kayit/liste", 0, 600u, "", s));
    guv__sinama_acilis(&g, b);
    KOD("U10G", dogrula(4u, "GET", "/kayit/liste", 0, 600u, "", s));
    KOD("U10H", dogrula(9u, "GET", "/kayit/liste", 0, 601u, "", s));
}

/* U17 kriptografi hatasi (mbedTLS ayirma vb.): dogru imza bile REDDEDILIR (yigindaki
   eski MAC'e guvenilmez), eslestirme ve P hesabi hata dondurur; hata gecince ayni
   istek kabul (pencere ilerlememisti) */
static NI void a1_hata(void)
{
    char s[65];
    uint8_t eno = 0, n = 0, nk[16], nc[16], kk[32], P[32];
    memset(nc, 0x33, sizeof(nc));
    t_imzala(K4, "GET", "/pil", 700u, "", s);
    gv_bit_hata = 1u;
    KOD("U17A", dogrula(4u, "GET", "/pil", 0, 700u, "", s));
    gv_bit_hata = 0u;
    KOD("U17B", dogrula(4u, "GET", "/pil", 0, 700u, "", s));
    KOD("U17C", guv_esles_baslat(&g, "h", nc, 50000UL, &eno, nk));
    ss_pbkdf2(PAROLA, g.ayar.tuz, 16, g.ayar.tur, P);
    t_hmac_es(P, "OK1-istemci", nk, nc, "h", kk);
    gv_bit_hata = 1u;
    KOD("U17D", guv_esles_kanit(&g, eno, kk, 50100UL, 1800000000UL, &n, P));
    KOD("U17E", guv_p_hesapla(&g, PAROLA));
    gv_bit_hata = 0u;
    KOD("U17F", guv_p_hesapla(&g, PAROLA));
    /* U17H: YALNIZ istemci kanitinin HMAC'i hata verir (cikti dogru MAC olsa bile);
       sonraki anahtar/kart HMAC'leri saglam — hata yok sayilsaydi eslestirme acilirdi */
    KOD("U17G", guv_esles_baslat(&g, "h", nc, 51000UL, &eno, nk));
    ss_pbkdf2(PAROLA, g.ayar.tuz, 16, g.ayar.tur, P);
    t_hmac_es(P, "OK1-istemci", nk, nc, "h", kk);
    gv_bit_tek = 1u;
    KOD("U17H", guv_esles_kanit(&g, eno, kk, 51100UL, 1800000000UL, &n, P));
    gv_bit_tek = 0u;
}

static NI void a1_dolu(void)
{
    uint8_t eno = 0, n = 0, nk[16], nc[16], kk[32], i;
    int r;
    memset(nc, 0x55, sizeof(nc));
    /* U11 liste dolu (1..5 var; 6, 7, 8; 9. ret) */
    for (i = 6; i <= 9u; i++) {
        char ad[6] = {'u', 's', 'b', (char)('0' + i), 0, 0};
        r = guv_esles_usb(&g, ad, 1800000000UL, &n, kk);
        KOD("U11", r < 0 ? r : n);
    }
    KOD("U11B", guv_esles_baslat(&g, "dolu", nc, 40000UL, &eno, nk));
    KOD("U11N", say_var());
}

/* ── asama 2 ── */
static NI void a2(void)
{
    uint8_t kk[32], P[32], n = 0;
    GuvCihaz c;
    char s[65];
    int r;
    KOD("U12N", say_var());
    VK(V_POST, s); KOD("U12A", dogrula(3u, "POST", "/komut", 0, 2u, "Go1234", s));
    if (!guv_cihaz_oku(&g, 4u, &c)) memcpy(K4, c.K, 32);
    KOD("U12Z", imza_dene("GET", "/pil", 0u));    /* taze pencerede sayac 0 da ret */
    KOD("U12B", imza_dene("GET", "/pil", 1u));
    /* U13 silme + ayni numaraya yeniden eslesme: eski K gecmez */
    if (!guv_cihaz_oku(&g, 1u, &c)) memcpy(kk, c.K, 32);
    KOD("U13A", guv_cihaz_sil(&g, 1u));
    t_imzala(kk, "GET", "/pil", 5u, "", s);
    KOD("U13B", dogrula(1u, "GET", "/pil", 0, 5u, "", s));
    r = guv_esles_usb(&g, "yeni", 1800000000UL, &n, P);
    KOD("U13C", r ? r : n);
    KOD("U13D", dogrula(1u, "GET", "/pil", 0, 5u, "", s));
    KOD("U13E", guv_cihaz_sil(&g, 12u));
    KOD("U13F", guv_cihaz_sil(&g, 2u));           /* tek silme NVS'e: asama 3'te 7 cihaz */
    KOD("U14Y", guv_ayar_yaz(&g, 1, 1, 3u));
}

/* ── asama 4/5: AYAR BOZUK -> fail-closed (zorunlu 1), ayar yazilinca duzelir ── */
static NI void a4(void)
{
    metin_P(PSTR("U18Z ")); ondalik(g.ayar.zorunlu); satir();
    KOD("U18Y", guv_ayar_yaz(&g, 0, -1, 0u));
    hexsatir_kisa(PSTR("U18K"), g.ayar.kimlik, 8);
}

static NI void a5(void)
{
    metin_P(PSTR("U18S ")); ondalik(g.ayar.zorunlu); satir();
}

/* ── asama 3 ── */
static NI void a3(void)
{
    metin_P(PSTR("U14 ")); ondalik(g.ayar.zorunlu); yaz(' '); ondalik(g.ayar.misafir);
    yaz(' '); ondalik(g.ayar.tur); satir();
    KOD("U15P", say_var());
    KOD("U15A", guv_cihaz_sil(&g, 0u));
    KOD("U15N", say_var());
}

static void senaryo(void)
{
    uint32_t adim = t_adim_oku();
    char h[33];
    rs = 0x9E3779B9UL ^ (adim * 0x01000193UL);
    if (adim == 4u) {                           /* U18: boyu yanlis (bozuk) ayar kaydi */
        static const uint8_t bozuk[5] = {1u, 2u, 3u, 4u, 5u};
        (void)gv_yaz(0, "ayar", bozuk, 5u);
    }
    KOD("AC", guv_ac(&g, &GK, &GNVS));
    guv_acilis_hex(&g, h); metin_P(PSTR("ACILIS ")); metin(h); satir();
    hexsatir_kisa(PSTR("KIMLIK"), g.ayar.kimlik, 8);
    hexsatir_kisa(PSTR("TUZ"), g.ayar.tuz, 16);
    switch (adim) {
    case 1:
        a1_kripto();
        a1_vektor();
        a1_imza_vektor();
        a1_eslesme();
        a1_deneme();
        a1_pencere();
        a1_degisiklik();
        a1_hata();
        a1_dolu();
        break;
    case 2:
        a2();
        break;
    case 3:
        a3();
        break;
    case 4:
        a4();
        break;
    case 5:
        a5();
        break;
    default:
        break;
    }
    metin_P(PSTR("BITTI\n"));
}
#endif

/* ── giris ── */
#if !(defined(SENARYO_BICIM) || defined(SENARYO_NOKTACI) || defined(SENARYO_GUNLUK) \
      || defined(SENARYO_YAZICI) || defined(SENARYO_KESINTI) || defined(SENARYO_DIZIN) \
      || defined(SENARYO_TARAMA) || defined(SENARYO_MANTIKSAL) || defined(SENARYO_YONET) \
      || defined(SENARYO_SURUM) || defined(SENARYO_KALGEC) || defined(SENARYO_PIL) \
      || defined(SENARYO_HALKA) || defined(SENARYO_AYRINTI) || defined(SENARYO_HAZIR) \
      || defined(SENARYO_SKOP) || defined(SENARYO_PLAN) || defined(SENARYO_GUV))
#error "SENARYO_* tanimli degil"
#endif

int main(void)
{
    uart_baslat();
    senaryo();
    for (;;) {}
}
