#ifndef PIL_TEST_H
#define PIL_TEST_H
/*
 * B21 — PIL KAPASITE TESTI (2026-09-10)
 *
 * Harici TAS DIRENC yuk, karttaki IRFZ44N (Q1) anahtarla kesiliyor.
 * MOSFET yalnizca AC/KAPA yapiyor; guc tas direncte yaniyor.
 *
 * NEDEN AYRI DOSYA: .ino zaten 1400 satir ve Arduino'nun otomatik
 * prototip ekleyicisi struct kullanan fonksiyonlarda bozuluyor
 * (bkz. tipler3.h'nin basindaki not). Durum makinesi + halka tampon
 * kendi basligina alindi.
 *
 * ⚠ GUVENLIK — KAPI YONU. Q1'in kapisi R42 (10K) ile GND'ye CEKILI.
 *   ESP32 reset atarsa, coker ya da WDT tetiklenirse GPIO yuksek
 *   empedansa doner, kapi 0 V'a iner ve MOSFET KAPANIR: pil bosalmayi
 *   durdurur. Bu, donanim WDT'sini bedava bir emniyete cevirir.
 *   Acilista da boyle: pinMode cagrilmadan once GPIO giris kipinde,
 *   yani yuk zaten KAPALI.
 */
#include <stdint.h>
#include "olcum3.h"

/* ─────────────────────────────────── durumlar */
enum PilDurum : uint8_t {
    PIL_BEKLEMEDE = 0,
    PIL_CALISIYOR = 1,
    PIL_BITTI     = 2,   /* kesme gerilimine ulasildi — NORMAL son */
    PIL_DURDURULDU = 3,  /* kullanici durdurdu */
    PIL_HATA      = 4,   /* baslatma reddedildi ya da emniyet devreye girdi */
};

/* Hata/ret sebepleri — kullaniciya NEDEN reddedildigi soylenmeli */
enum PilHata : uint8_t {
    PILH_YOK = 0,
    PILH_GERILIM_DUSUK,    /* zaten kesmenin altinda */
    PILH_GERILIM_YUKSEK,   /* MOSFET Vdss siniri (38.5 V) */
    PILH_TERS,             /* ters polarite */
    PILH_BAYPAS,           /* MOSFET kapaliyken akim var -> yuk J3'te */
    PILH_SURE,             /* azami sure asildi */
    PILH_AKIM_YOK,         /* baslatildi ama akim akmadi -> yuk bagli degil */
};

/* MOSFET'in Vdss'inden gelen SERT sinir. IRFZ44N 55 V, %70 pay.
 * sim3_pil.py bolum 4 bunu sinar. */
#define PIL_AZAMI_V   38.5f
/* Baslatma denetimlerinin akim esigi: gurultunun cok uzerinde,
 * en kucuk gercek yuk akiminin cok altinda (sim3_pil.py bolum 2b). */
#define PIL_AKIM_ESIK 0.020f
/* DCIR darbesi — tasarim3_sabit.py: PIL_DCIR_ARALIK_S / PIL_DCIR_DARBE_S.
 * sim3_pil.py bolum 5c bu ikisini ORADAN okuyup bu dosyayla karsilastiriyor,
 * yani ayrisirlarsa zincir kirmiziya doner. */
#define PIL_DCIR_ARALIK_MS 300000u
#define PIL_DCIR_MS        200u

/* ─────────────────────────────────── egri kaydi (halka tampon)
 *
 * 12 bayt/nokta: ms (uint32) + V (float) + I (float).
 * 2 saat @ 1 Hz = 7200 nokta = 86 KB. IC RAM'e siğiyor; PSRAM'e
 * BAGIMLI DEGIL (DEVIR 4.9: PSRAM'in kartta bulundugu kanitlanmadi).
 * PSRAM varsa .ino acilista tamponu buyutuyor.
 */
typedef struct {
    uint32_t ms;
    float    v;
    float    i;
} PilNokta;

/* Halka tampon. `bas` en eski, `adet` doluluk, `sira` KACINCI nokta
 * oldugu (tarayici "bende 12480'e kadar var" diyebilsin diye —
 * tampon sarmis olsa bile sira numarasi artmaya devam eder). */
/* 🔴 B21: bu alanlar once uint16_t idi. PSRAM tamponu 24 saat @ 1 Hz =
 * 86400 nokta istiyor, ama uint16 tavani 65535 — `24u * 3600u` SESSIZCE
 * 20864'e dusuyordu (24 saat yerine 5.8 saat) ve kimse gormuyordu.
 * Derleyici uyariyordu ama arduino-cli ONBELLEKTEN derledigi icin uyari
 * basilmiyordu; test_firmware3.py'ye "--clean" eklenince ortaya cikti. */
typedef struct {
    PilNokta *nokta;
    uint32_t  kapasite;
    uint32_t  bas;
    uint32_t  adet;
    uint32_t  sira;        /* uretilen TOPLAM nokta sayisi */
} PilHalka;

static void pil_halka_sifirla(PilHalka *h)
{
    h->bas = 0;
    h->adet = 0;
    h->sira = 0;
}

static void pil_halka_ekle(PilHalka *h, uint32_t ms, float v, float i)
{
    if (!h->nokta || !h->kapasite) { h->sira++; return; }
    uint32_t yer = (h->bas + h->adet) % h->kapasite;
    h->nokta[yer].ms = ms;
    h->nokta[yer].v = v;
    h->nokta[yer].i = i;
    if (h->adet < h->kapasite) h->adet++;
    else h->bas = (h->bas + 1) % h->kapasite;
    h->sira++;
}

/* `istenen` sira numarasindan itibaren kac nokta ELDE var?
 * Tarayici yeniden baglaninca bunu soruyor. Tampon sarmissa istenen
 * nokta artik yoktur — o zaman BOSLUK vardir ve arayuz bunu ISARETLER
 * (sessizce interpolasyon YAPILMAZ). */
static uint32_t pil_halka_bul(const PilHalka *h, uint32_t istenen,
                              uint32_t *ilk_yer, uint32_t *ilk_sira)
{
    uint32_t en_eski = h->sira - h->adet;      /* elde tutulan en eski sira */
    uint32_t bas_sira = (istenen > en_eski) ? istenen : en_eski;
    if (bas_sira >= h->sira) { *ilk_yer = 0; *ilk_sira = h->sira; return 0; }
    uint32_t atla = bas_sira - en_eski;
    *ilk_yer = (h->bas + atla) % h->kapasite;
    *ilk_sira = bas_sira;
    return h->sira - bas_sira;
}

/* ─────────────────────────────────── test durumu */
typedef struct {
    uint8_t  durum;        /* PilDurum */
    uint8_t  hata;         /* PilHata */
    uint32_t baslama_ms;
    uint32_t bitis_ms;
    int64_t  yuk_pC;       /* ISARETLI — sarj yonunde geri sayar */
    int64_t  enerji_pJ;
    float    v_bas;        /* yuk BAGLANMADAN once (OCV) */
    float    v_son;
    float    dcir_ani;     /* ilk ornekten — ohmik + bir miktar polarizasyon */
    float    dcir_oturmus; /* darbe sonundan */
    uint32_t dcir_sayisi;
    uint32_t son_kayit_ms;
    uint32_t son_dcir_ms;
    uint8_t  dcir_icinde;
    uint32_t dcir_bas_ms;
    float    dcir_i_once;  /* darbeden hemen onceki akim */
    float    dcir_v_once;
} PilTest;

static void pil_sifirla(PilTest *p)
{
    p->durum = PIL_BEKLEMEDE;
    p->hata = PILH_YOK;
    p->baslama_ms = p->bitis_ms = 0;
    p->yuk_pC = 0;
    p->enerji_pJ = 0;
    p->v_bas = p->v_son = 0.0f;
    p->dcir_ani = p->dcir_oturmus = 0.0f;
    p->dcir_sayisi = 0;
    p->son_kayit_ms = p->son_dcir_ms = 0;
    p->dcir_icinde = 0;
    p->dcir_bas_ms = 0;
    p->dcir_i_once = p->dcir_v_once = 0.0f;
}

/* Baslatma denetimi — SAF fonksiyon, AVR emulatorunde sinanabiliyor.
 * `v_bos` : MOSFET KAPALIYKEN olculen gerilim (OCV)
 * `i_bos` : MOSFET KAPALIYKEN olculen akim (0 olmali!)
 * Doner: PILH_YOK ise baslatilabilir. */
static uint8_t pil_baslatilabilir(float v_bos, float i_bos, float kesme_v)
{
    /* Ters polarite: cift yonlu kart negatifi GORUR, o yuzden
     * sessizce yanlis olcmek yerine REDDEDIYORUZ. */
    if (v_bos < 0.0f) return PILH_TERS;
    /* MOSFET kapaliyken pilin TAMAMI onun uzerinde. */
    if (v_bos > PIL_AZAMI_V) return PILH_GERILIM_YUKSEK;
    /* Zaten kesmenin altindaysa test anlamsiz — ve pili daha da
     * bosaltmak zararli. */
    if (v_bos <= kesme_v) return PILH_GERILIM_DUSUK;
    /* 🔴 BAYPAS DENETIMI: MOSFET KAPALI olmasina ragmen akim varsa,
     * yuk yanlislikla J3'e (dogrudan sonte) baglanmis demektir.
     * O halde KESME CALISMAZ ve kimse fark etmez. */
    float m = i_bos < 0.0f ? -i_bos : i_bos;
    if (m > PIL_AKIM_ESIK) return PILH_BAYPAS;
    return PILH_YOK;
}

/* Kesme olcutu — SAF. Ayri fonksiyon cunku AVR'de sinaniyor. */
static uint8_t pil_kesmeli_mi(float v, float kesme_v)
{
    return (uint8_t)(v <= kesme_v);
}

/* DCIR: yuk kesilince gerilim OCV'ye dogru siçrar.
 *     R = (V_yuksuz - V_yuklu) / I_yuklu
 * ⚠ Gercek OHMIK dusus mikrosaniyelerde olur; ilk ornegimiz ~1.5 ms
 *   sonra geliyor. Yani bu, ohmik + bir miktar polarizasyon. MUTLAK
 *   DCIR degil, KARSILASTIRILABILIR bir saglik gostergesi. */
static float pil_dcir(float v_yuklu, float v_yuksuz, float i_yuklu)
{
    float m = i_yuklu < 0.0f ? -i_yuklu : i_yuklu;
    if (m < PIL_AKIM_ESIK) return 0.0f;
    return (v_yuksuz - v_yuklu) / m;
}

#endif /* PIL_TEST_H */
