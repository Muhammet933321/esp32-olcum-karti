/* kayit_plan.h — 1C-4 zamanlanmis kayit: KARAR MANTIGI (platformsuz).
 *
 * Tek bekleyen plan: baslangic (unix s), sure (s; 0 = Gd'ye dek), hiz (hiz_ms).
 * `plan_adim` gercek saate ve oturum durumuna bakip ne yapilacagini SOYLER
 * (PE_BASLAT / PE_BITIR); oturumu acip kapatmak cagiranin isi (kart: KM_*).
 * Durum her degisimde NVS'e yazilir: yeniden baslamada bekleyen plan bekler,
 * baslamis planin oturumu DEVAM aldiysa bitis korunur.
 *
 * Kurallar (tasarim/2026-10-01-1c4-zamanlanmis-kayit.md K2-K9):
 *  - baslangicta MESGULSE (oturum, oturumsuz pil testi, skop gunlugu) plan ATLANIR;
 *  - kart baslangicta kapaliydiysa pencere (bas + sure) icinde GEC baslar,
 *    pencere gecmisse KACIRILDI;
 *  - saat yoksa (simdi_unix == 0) bekler; kurulamaz;
 *  - plan YALNIZ cekirdek 0'in bildirdigi oturuma baglanir (`plan_sonuc`):
 *    o an etkin olan baska bir oturumu BENIMSEMEZ (1C-4 incelemesi I1);
 *    cekirdek 0 mesgul dediyse ATLANDI, hata dediyse ya da sonuc
 *    PLAN_BASLAT_S icinde gelmediyse BASLATILAMADI;
 *  - planin oturumu kapandiysa (Gd, DOLU, DEVAM alamadi) BITTI — yeni oturum ACMAZ;
 *  - acilista SURUYOR ama oturumu bilinmiyorsa (sonuc gelmeden elektrik
 *    gitti) BITTI: hangi oturum oldugu bilinemez, tahmin edilmez —
 *    Y2 (1C-4 inceleme M3): cekirdek 0'in KANITI varsa (plan_acilis) o oturum
 *    benimsenir; BEKLIYOR kalmis plan da (BASLAT gitti, NVS yazilmadan elektrik)
 *    ayni kanitla. Kanit tahmin degildir: o pencerede cekirdek 0 baska oturum acmaz.
 * AVR'de sinaniyor: test_kayit.py B71.R1-R13 (SENARYO_PLAN). */
#ifndef KAYIT_PLAN_H
#define KAYIT_PLAN_H

#include <stdint.h>
#include "kayit_yonet.h"          /* KayitNvs */

#define PLAN_YOK       0u
#define PLAN_BEKLIYOR  1u
#define PLAN_SURUYOR   2u
#define PLAN_BITTI     3u
#define PLAN_ATLANDI   4u
#define PLAN_KACIRILDI 5u
#define PLAN_SAAT_YOK  6u         /* yalniz GP satirinda: BEKLIYOR + saat yok */
#define PLAN_BASLATILAMADI 7u     /* cekirdek 0 oturumu acamadi (DOLU/hata) ya da cevap yok */

#define PE_YOK    0u
#define PE_BASLAT 1u
#define PE_BITIR  2u

#define KP_SAAT    (-1)           /* saat yok: kurulamaz */
#define KP_SURE    (-2)           /* sure > 30 gun */
#define KP_GECMIS  (-3)           /* pencere tamamen gecmis */
#define KP_SURUYOR (-4)           /* plan suruyor: once Gp- */
#define KP_ZAMAN   (-5)           /* baslangic anlamsiz: 2023'ten once ya da 1 yildan ileri */
#define KP_NVS     (-6)           /* Y3: NVS'e yazilamadi — KURULMADI, onceki plan gecerli */

#define PLAN_SURE_AZAMI (30UL * 86400UL)
#define PLAN_UNIX_ALT   1700000000UL      /* 2023-11: bundan kucuk 'unix' bir yazim hatasidir */
#define PLAN_ILERI_AZAMI (366UL * 86400UL)
#ifndef PLAN_BASLAT_S
#define PLAN_BASLAT_S 10u         /* BASLAT'tan sonra oturumun gorunmesi icin en fazla */
#endif

typedef struct {
    const KayitNvs *nvs;
    uint32_t bas, sure, hiz, no, oturum, baslat_unix;
    uint8_t  durum;
} KayitPlan;

/* 0 tamam, -1 bir alan yazilamadi. Y3: o zaman durum YAZILMAZ (gecerlilik isareti EN SON). */
static inline int plan__yaz(KayitPlan *p)
{
    const KayitNvs *n = p->nvs;
    int h = 0;
    if (!n) return 0;
    h |= n->yaz(n->baglam, "pl_bas", p->bas);
    h |= n->yaz(n->baglam, "pl_sure", p->sure);
    h |= n->yaz(n->baglam, "pl_hiz", p->hiz);
    h |= n->yaz(n->baglam, "pl_no", p->no);
    h |= n->yaz(n->baglam, "pl_ot", p->oturum);
    h |= n->yaz(n->baglam, "pl_bu", p->baslat_unix);
    if (h) return -1;
    return n->yaz(n->baglam, "pl_dur", p->durum) ? -1 : 0;   /* EN SON: durum gecerliligi */
}

static inline void plan_ac(KayitPlan *p, const KayitNvs *n)
{
    p->nvs = n;
    p->bas = n->oku(n->baglam, "pl_bas", 0u);
    p->sure = n->oku(n->baglam, "pl_sure", 0u);
    p->hiz = n->oku(n->baglam, "pl_hiz", 0u);
    p->no = n->oku(n->baglam, "pl_no", 0u);
    p->oturum = n->oku(n->baglam, "pl_ot", 0u);
    p->baslat_unix = n->oku(n->baglam, "pl_bu", 0u);
    p->durum = (uint8_t)n->oku(n->baglam, "pl_dur", PLAN_YOK);
    if (p->durum == PLAN_SAAT_YOK || p->durum > PLAN_BASLATILAMADI) p->durum = PLAN_YOK;
    /* SURUYOR + oturumsuz (sonuc gelmeden elektrik gitti) karari plan_acilis'te: cekirdek
       0'in kaniti tarama bitince belli olur */
}

/* Y2 (1C-4 inceleme M3): acilista BIR KEZ, tarama bittikten sonra ve plan_adim'dan ONCE.
   `kanit_no`/`kanit_ot`: cekirdek 0'in kaniti (kyn_ac) — plan `kanit_no` icin acilan
   oturum `kanit_ot` su an devam ediyor. Plan BEKLIYOR (BASLAT gitti, plan NVS'i
   yazilmadan elektrik) ya da SURUYOR/oturumsuz kalmissa ve kanit BU planin ise o oturum
   benimsenir (sure dolunca BITIR). Kanit yoksa SURUYOR/oturumsuz -> BITTI (tahmin yok);
   BEKLIYOR beklemeye devam eder. Donus 1 = benimsendi. */
static inline uint8_t plan_acilis(KayitPlan *p, uint32_t kanit_no, uint32_t kanit_ot)
{
    const uint8_t belirsiz = (uint8_t)(p->durum == PLAN_BEKLIYOR
                                       || (p->durum == PLAN_SURUYOR && !p->oturum));
    if (belirsiz && kanit_no && kanit_ot && kanit_no == p->no) {
        if (p->durum == PLAN_BEKLIYOR) p->baslat_unix = p->bas;
        p->durum = PLAN_SURUYOR;
        p->oturum = kanit_ot;
        plan__yaz(p);
        return 1u;
    }
    if (p->durum == PLAN_SURUYOR && !p->oturum) {       /* kanit yok: tahmin edilmez */
        p->durum = PLAN_BITTI;
        plan__yaz(p);
    }
    return 0u;
}

/* Donus 0 ya da KP_*. Suren plan degistirilemez (once Gd ya da Gp-). Y3 (1C-4 inceleme
   M4): NVS'e yazilamazsa (NVS dolu) KP_NVS — plan yalniz RAM'de kalip yeniden baslamada
   sessizce kaybolmasin; onceki plan RAM'de geri gelir, NVS'e geri yazilir (en iyi caba). */
static inline int plan_kur(KayitPlan *p, uint32_t bas, uint32_t sure, uint32_t hiz,
                           uint32_t simdi_unix)
{
    KayitPlan eski;
    if (!simdi_unix) return KP_SAAT;
    if (bas < PLAN_UNIX_ALT || (int32_t)(bas - simdi_unix) > (int32_t)PLAN_ILERI_AZAMI)
        return KP_ZAMAN;
    if (sure > PLAN_SURE_AZAMI) return KP_SURE;
    if (sure && (uint32_t)(bas + sure) <= simdi_unix) return KP_GECMIS;
    if (p->durum == PLAN_SURUYOR) return KP_SURUYOR;
    eski = *p;
    p->bas = bas;
    p->sure = sure;
    p->hiz = hiz;
    p->no = p->no + 1u;
    p->oturum = 0u;
    p->baslat_unix = 0u;
    p->durum = PLAN_BEKLIYOR;
    if (plan__yaz(p)) {
        *p = eski;
        (void)plan__yaz(p);
        return KP_NVS;
    }
    return 0;
}

/* Plani unut. Suren planin kaydini kapatmak cagiranin isi (kart: Gp- KM_PLAN_BITIR
   sebep kullanici gonderir, ONCE). */
static inline void plan_iptal(KayitPlan *p)
{
    p->durum = PLAN_YOK;
    plan__yaz(p);
}

/* PE_BASLAT'tan hemen sonra cagiran (oturum acma istegini gonderdikten sonra). */
static inline void plan_basliyor(KayitPlan *p, uint32_t simdi_unix)
{
    p->durum = PLAN_SURUYOR;
    p->oturum = 0u;
    p->baslat_unix = simdi_unix;
    plan__yaz(p);
}

static inline void plan__durum(KayitPlan *p, uint8_t d)
{
    p->durum = d;
    plan__yaz(p);
}

/* Cekirdek 0'in KM_PLAN_BASLAT sonucu: > 0 oturum id, 0 mesgul (o an oturum ya
   da DEVAM bekleyisi vardi), < 0 KG_* hata. Donus 1 = alindi; 0 = plan bu sonucu
   BEKLEMIYOR (zaman asimi, Gp-, yinelenen) — sonuc bir oturumsa cagiran kapatir. */
static inline uint8_t plan_sonuc(KayitPlan *p, int32_t sonuc)
{
    if (p->durum != PLAN_SURUYOR || p->oturum) return 0u;
    if (sonuc > 0) {
        p->oturum = (uint32_t)sonuc;
        plan__yaz(p);
    } else {
        plan__durum(p, sonuc == 0 ? PLAN_ATLANDI : PLAN_BASLATILAMADI);
    }
    return 1u;
}

/* Saniyede bir. `mesgul`: etkin oturum, oturumsuz pil testi ya da skop gunlugu;
   `oturum_id`: kayit motorunun ETKIN oturumu (0 = yok; tarama bitmeden
   cagrilmamali). Donus PE_*. */
static inline uint8_t plan_adim(KayitPlan *p, uint32_t simdi_unix, uint8_t mesgul,
                                uint32_t oturum_id)
{
    if (p->durum == PLAN_BEKLIYOR) {
        if (!simdi_unix) return PE_YOK;                          /* saat bekleniyor */
        if ((int32_t)(simdi_unix - p->bas) < 0) return PE_YOK;   /* henuz degil */
        if (p->sure && (int32_t)(simdi_unix - (p->bas + p->sure)) >= 0) {
            plan__durum(p, PLAN_KACIRILDI);
            return PE_YOK;
        }
        if (mesgul) {                                             /* isi BOLMEZ */
            plan__durum(p, PLAN_ATLANDI);
            return PE_YOK;
        }
        return PE_BASLAT;
    }
    if (p->durum != PLAN_SURUYOR) return PE_YOK;
    if (!p->oturum) {                     /* cekirdek 0'in sonucunu bekle: BENIMSEME YOK */
        /* isaretli fark: NTP saati geri adim atarsa zaman asimi sayilmaz (M2) */
        if (simdi_unix && (int32_t)(simdi_unix - p->baslat_unix) > (int32_t)PLAN_BASLAT_S)
            plan__durum(p, PLAN_BASLATILAMADI);
        return PE_YOK;
    }
    if (!oturum_id || oturum_id != p->oturum) {                   /* Gd, DOLU, DEVAM yok */
        plan__durum(p, PLAN_BITTI);
        return PE_YOK;
    }
    if (!p->sure || !simdi_unix) return PE_YOK;
    if ((int32_t)(simdi_unix - (p->bas + p->sure)) >= 0) return PE_BITIR;
    return PE_YOK;
}

#endif /* KAYIT_PLAN_H */
