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

/* ─────────────────────────────────── PT (2026-10-07) — kesme, OCV evresi, kayit hizi
 * tasarim/2026-10-07-pil-iyilestirme.md PT1-PT5. Kullanicinin 18650 testi 2 s'de
 * bitiyordu: kesme TEK ANLIK ornekte veriliyordu ve ±0.12 V'luk gurultunun ilk dibi
 * kesiyordu. Karar artik BURADA (pil_adim, platformsuz); .ino yalniz yan etkiyi
 * yapar (MOSFET, seri satir, kayit). sim3_pil.py bolum 7 AVR emulatorunde sinar. */
#define PIL_KESME_TAU_MS   1000u   /* PT1: kesme, gerilimin ust. kayan ortalamasiyla */
#define PIL_OCV_MS         5000u   /* PT2: p1 kabulunden sonra yuk KAPALI evre */
#define PIL_HALKA_EN_AZ_MS 50u     /* PT4: /pil canli egrisi (RAM halkasi) en cok 20/s */

/* evre (yalniz PIL_CALISIYOR'da anlamli). Sifir = YUK: sifirlanmis yapi OCV demez. */
#define PIL_EVRE_YUK 0u
#define PIL_EVRE_OCV 1u

/* pil_adim'in istedigi yan etkiler (bit) — .ino uygular */
#define PILA_YUK_AC     0x01u   /* OCV evresi bitti: MOSFET'i AC */
#define PILA_DCIR_BAS   0x02u   /* DCIR darbesi basladi: MOSFET'i KAPAT */
#define PILA_DCIR_BITTI 0x04u   /* darbe bitti: MOSFET'i AC + DCIR olayi */
#define PILA_BITTI      0x08u   /* kesme: pil_durdur(PIL_BITTI) */
#define PILA_SURE       0x10u   /* azami sure asildi: pil_durdur(PIL_HATA, PILH_SURE) */

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
    uint8_t  evre;         /* PT2: PIL_EVRE_OCV (yuk kapali) / PIL_EVRE_YUK */
    uint8_t  dcir_acik;    /* PT5: bu testte DCIR darbesi var mi (baslarken kopyalanir) */
    uint8_t  ema_hazir;    /* PT1: v_ema yuk altindaki ilk ornekle tohumlandi */
    uint32_t dcir_bas_ms;
    float    dcir_i_once;  /* darbeden hemen onceki akim */
    float    dcir_v_once;
    float    v_ema;        /* PT1: yuk altindaki gerilimin EMA'si (tau PIL_KESME_TAU_MS) */
    float    dcir_v_ani;   /* darbenin ilk ornegindeki V (DCIR olayi; eskiden .ino'da) */
    uint32_t yuk_bas_ms;   /* PT2: yukun acildigi an (kesme bundan 1 tau sonra) */
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
    p->evre = PIL_EVRE_YUK;
    p->dcir_acik = 0;
    p->ema_hazir = 0;
    p->dcir_bas_ms = 0;
    p->dcir_i_once = p->dcir_v_once = 0.0f;
    p->v_ema = p->dcir_v_ani = 0.0f;
    p->yuk_bas_ms = 0;
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

/* ─────────────────────────────────── PT3/PT4: kayit hizi
 * Ayar3.pil_kayit_hz (BUYUMEZ: AYAR3_IMZA ayni kalir, kalibrasyon sifirlanmaz).
 * 0 = HER ORNEK (pil oturumu hiz_ms 0: AYRINTI kayitlari + 1/s nokta). Yeni giris
 * yalniz listeden (Pr); eski kayitli 0.2 gibi degerler okunmaya devam eder. */
static uint8_t pil_hz_izinli(uint32_t hz)
{
    return (uint8_t)(hz == 0u || hz == 1u || hz == 5u || hz == 20u || hz == 50u);
}

/* hz -> pil oturumunun nokta araligi (BASLA hiz_ms). 0 = her ornek. NaN/eksi
   (bozuk ayar) varsayilan 1/s; pozitif deger 20 ms .. 60 s'ye kirpilir. */
static uint32_t pil_nokta_ms(float hz)
{
    float ms;
    if (!(hz >= 0.0f)) return 1000u;
    if (hz == 0.0f) return 0u;
    ms = 1000.0f / hz + 0.5f;
    if (ms < 20.0f) ms = 20.0f;
    if (ms > 60000.0f) ms = 60000.0f;
    return (uint32_t)ms;
}

/* /pil canli egrisinin (RAM halkasi) araligi: nokta araligi, en cok 20/s. */
static uint32_t pil_halka_ms(float hz)
{
    const uint32_t ms = pil_nokta_ms(hz);
    return ms < PIL_HALKA_EN_AZ_MS ? PIL_HALKA_EN_AZ_MS : ms;
}

/* `Pr<hz>` argumani (s = 'r'den sonrasi). Yalniz rakam, bastaki sifir yok
   ("0" haric), en cok 3 hane. Donus 0 tamam (*hz yazilir), 1 bicim, 2 izinsiz. */
static uint8_t pil_pr_ayir(const char *s, uint32_t *hz)
{
    uint32_t v = 0u;
    uint8_t n = 0u;
    if (!s || !*s) return 1u;
    if (s[0] == '0' && s[1]) return 1u;
    for (; *s; s++, n++) {
        if (*s < '0' || *s > '9' || n >= 3u) return 1u;
        v = v * 10u + (uint32_t)(*s - '0');
    }
    if (!pil_hz_izinli(v)) return 2u;
    *hz = v;
    return 0u;
}

/* `Pd<0|1>` argumani: 0 / 1, baska her sey 0xFF. */
static uint8_t pil_pd_ayir(const char *s)
{
    if (!s || (s[0] != '0' && s[0] != '1') || s[1]) return 0xFFu;
    return (uint8_t)(s[0] - '0');
}

/* ─────────────────────────────────── PT1/PT2: durum makinesi (her olcumde)
 * PT1 ust. kayan ortalama: a = dt / (tau + dt). Tek dip (~0.15 V, birkac ms)
 * EMA'yi mV duzeyinde oynatir; ortalama kesmenin altina inince ~1.1 tau'da keser. */
static float pil_ema_adim(float ema, float v, uint32_t dt_us)
{
    const float a = (float)dt_us / ((float)PIL_KESME_TAU_MS * 1000.0f + (float)dt_us);
    return ema + a * (v - ema);
}

typedef struct {
    float    kesme_v;
    uint32_t azami_s;      /* 0 = sinirsiz; BASLANGICTAN sayilir (OCV evresi dahil) */
    uint32_t halka_ms;     /* /pil egrisine nokta araligi (pil_halka_ms) */
} PilParam;

/* p1 kabul edildi (pil_baslatilabilir gecti). Yuk KAPALI kalir: once OCV evresi. */
static void pil_baslat_kur(PilTest *p, uint32_t ms, float v_bos, uint8_t dcir_acik)
{
    pil_sifirla(p);
    p->v_bas = v_bos;              /* OCV (yuk yokken) */
    p->v_son = v_bos;
    p->durum = PIL_CALISIYOR;
    p->evre = PIL_EVRE_OCV;
    p->dcir_acik = dcir_acik ? 1u : 0u;
    p->baslama_ms = ms;
    p->son_kayit_ms = ms;
    p->son_dcir_ms = ms;
}

/* Kayit noktacisinin KN_OCV bayragi: test SURUYOR ve yuk henuz acilmadi. */
static uint8_t pil_ocv_evresinde(const PilTest *p)
{
    return (uint8_t)(p->durum == PIL_CALISIYOR && p->evre == PIL_EVRE_OCV);
}

/* PT1 kesme olcutu: SAF. Yuk en az 1 tau acikken ve EMA <= kesme. */
static uint8_t pil_kesme_karar(const PilTest *p, uint32_t ms, float kesme_v)
{
    return (uint8_t)(ms - p->yuk_bas_ms >= PIL_KESME_TAU_MS
                     && pil_kesmeli_mi(p->v_ema, kesme_v));
}

/* Her olcumden sonra. Donus: PILA_* (yan etkileri .ino yapar, AYNI turda). */
static uint8_t pil_adim(PilTest *p, PilHalka *h, const PilParam *a, uint32_t ms,
                        float v, float i, float w, uint32_t dt_us)
{
    if (p->durum != PIL_CALISIYOR) return 0u;

    /* --- emniyet: azami sure (baslangictan) */
    if (a->azami_s && (ms - p->baslama_ms) / 1000UL > a->azami_s) return PILA_SURE;

    /* --- PT2: OCV evresi — yuk KAPALI, nokta kaydi var, birikim ve kesme YOK */
    if (p->evre == PIL_EVRE_OCV) {
        p->v_son = v;
        if (ms - p->son_kayit_ms >= a->halka_ms) {
            pil_halka_ekle(h, ms - p->baslama_ms, v, i);
            p->son_kayit_ms = ms;
        }
        if (ms - p->baslama_ms < PIL_OCV_MS) return 0u;
        p->evre = PIL_EVRE_YUK;
        p->yuk_bas_ms = ms;
        p->son_dcir_ms = ms;       /* DCIR zamanlayicisi yuk acilinca baslar */
        p->ema_hazir = 0u;
        return PILA_YUK_AC;
    }

    /* --- DCIR darbesi icindeysek */
    if (p->dcir_icinde) {
        if (ms - p->dcir_bas_ms == 0u) return 0u;    /* ilk tur, henuz olcum yok */
        if (p->dcir_ani == 0.0f) {
            /* darbeden SONRAKI ILK ornek — "ani" deger. dcir_ani darbe basinda 0'a
               cekiliyor. (Eskiden `dcir_sayisi == 0 ||` de vardi: ILK darbede her
               ornekte dogruydu, ani deger darbenin SON orneginden geliyordu.) */
            p->dcir_ani = pil_dcir(p->dcir_v_once, v, p->dcir_i_once);
            p->dcir_v_ani = v;
        }
        if (ms - p->dcir_bas_ms >= (uint32_t)(PIL_DCIR_MS)) {
            p->dcir_oturmus = pil_dcir(p->dcir_v_once, v, p->dcir_i_once);
            p->dcir_sayisi++;
            p->dcir_icinde = 0u;
            p->son_dcir_ms = ms;
            return PILA_DCIR_BITTI;
        }
        return 0u;                                   /* darbe boyunca BIRIKTIRME */
    }

    /* --- normal birikim */
    p->yuk_pC = yuk_ekle3(p->yuk_pC, i, dt_us);
    p->enerji_pJ = enerji_ekle3(p->enerji_pJ, w, dt_us);
    p->v_son = v;
    if (!p->ema_hazir) {           /* yuk altindaki ILK ornek: OCV'den baslasa 1 tau gecikirdi */
        p->v_ema = v;
        p->ema_hazir = 1u;
    } else {
        p->v_ema = pil_ema_adim(p->v_ema, v, dt_us);
    }

    /* --- egri kaydi */
    if (ms - p->son_kayit_ms >= a->halka_ms) {
        pil_halka_ekle(h, ms - p->baslama_ms, v, i);
        p->son_kayit_ms = ms;
    }

    /* --- KESME (PT1: anlik ornek DEGIL, EMA) */
    if (pil_kesme_karar(p, ms, a->kesme_v)) return PILA_BITTI;

    /* --- DCIR darbesi zamani mi (PT5: kapaliyken HIC) */
    if (p->dcir_acik && ms - p->son_dcir_ms >= (uint32_t)(PIL_DCIR_ARALIK_MS)) {
        p->dcir_v_once = v;
        p->dcir_i_once = i;
        p->dcir_ani = 0.0f;
        p->dcir_icinde = 1u;
        p->dcir_bas_ms = ms;
        return PILA_DCIR_BAS;
    }
    return 0u;
}

#endif /* PIL_TEST_H */
