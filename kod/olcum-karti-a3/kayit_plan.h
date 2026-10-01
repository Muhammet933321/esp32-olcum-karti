/* kayit_plan.h — 1C-4 zamanlanmis kayit: KARAR MANTIGI (platformsuz).
 *
 * Tek bekleyen plan: baslangic (unix s), sure (s; 0 = Gd'ye dek), hiz (hiz_ms).
 * `plan_adim` gercek saate ve oturum durumuna bakip ne yapilacagini SOYLER
 * (PE_BASLAT / PE_BITIR); oturumu acip kapatmak cagiranin isi (kart: KM_*).
 * Durum her degisimde NVS'e yazilir: yeniden baslamada bekleyen plan bekler,
 * baslamis planin oturumu DEVAM aldiysa bitis korunur.
 *
 * Kurallar (tasarim/2026-10-01-1c4-zamanlanmis-kayit.md K2-K9):
 *  - baslangicta oturum (elle, pil, skop gunlugu) VARSA plan ATLANIR;
 *  - kart baslangicta kapaliydiysa pencere (bas + sure) icinde GEC baslar,
 *    pencere gecmisse KACIRILDI;
 *  - saat yoksa (simdi_unix == 0) bekler; kurulamaz;
 *  - BASLAT'tan sonra oturum PLAN_BASLAT_S icinde gorunmezse BITTI;
 *  - planin oturumu kapandiysa (Gd, DOLU, DEVAM alamadi) BITTI — yeni oturum ACMAZ.
 * AVR'de sinaniyor: test_kayit.py B71.R1-R9 (SENARYO_PLAN). */
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

#define PE_YOK    0u
#define PE_BASLAT 1u
#define PE_BITIR  2u

#define KP_SAAT    (-1)           /* saat yok: kurulamaz */
#define KP_SURE    (-2)           /* sure > 30 gun */
#define KP_GECMIS  (-3)           /* pencere tamamen gecmis */
#define KP_SURUYOR (-4)           /* plan suruyor: once Gd ya da Gp- */

#define PLAN_SURE_AZAMI (30UL * 86400UL)
#ifndef PLAN_BASLAT_S
#define PLAN_BASLAT_S 10u         /* BASLAT'tan sonra oturumun gorunmesi icin en fazla */
#endif

typedef struct {
    const KayitNvs *nvs;
    uint32_t bas, sure, hiz, no, oturum, baslat_unix;
    uint8_t  durum;
} KayitPlan;

static inline void plan__yaz(KayitPlan *p)
{
    const KayitNvs *n = p->nvs;
    if (!n) return;
    (void)n->yaz(n->baglam, "pl_bas", p->bas);
    (void)n->yaz(n->baglam, "pl_sure", p->sure);
    (void)n->yaz(n->baglam, "pl_hiz", p->hiz);
    (void)n->yaz(n->baglam, "pl_no", p->no);
    (void)n->yaz(n->baglam, "pl_ot", p->oturum);
    (void)n->yaz(n->baglam, "pl_bu", p->baslat_unix);
    (void)n->yaz(n->baglam, "pl_dur", p->durum);     /* EN SON: durum gecerliligi isaretler */
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
    if (p->durum > PLAN_KACIRILDI) p->durum = PLAN_YOK;
}

/* Donus 0 ya da KP_*. Suren plan degistirilemez (once Gd ya da Gp-). */
static inline int plan_kur(KayitPlan *p, uint32_t bas, uint32_t sure, uint32_t hiz,
                           uint32_t simdi_unix)
{
    if (!simdi_unix) return KP_SAAT;
    if (sure > PLAN_SURE_AZAMI) return KP_SURE;
    if (sure && (uint32_t)(bas + sure) <= simdi_unix) return KP_GECMIS;
    if (p->durum == PLAN_SURUYOR) return KP_SURUYOR;
    p->bas = bas;
    p->sure = sure;
    p->hiz = hiz;
    p->no = p->no + 1u;
    p->oturum = 0u;
    p->baslat_unix = 0u;
    p->durum = PLAN_BEKLIYOR;
    plan__yaz(p);
    return 0;
}

/* Plani unut. Suren planda kayit SURER (otomatik bitis kalkar; Gd ile durur). */
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

/* Saniyede bir. `oturum_var`/`oturum_id`: kayit motorunun ETKIN oturumu (tarama
   bitmeden cagrilmamali). Donus PE_*. */
static inline uint8_t plan_adim(KayitPlan *p, uint32_t simdi_unix, uint8_t oturum_var,
                                uint32_t oturum_id)
{
    if (p->durum == PLAN_BEKLIYOR) {
        if (!simdi_unix) return PE_YOK;                          /* saat bekleniyor */
        if ((int32_t)(simdi_unix - p->bas) < 0) return PE_YOK;   /* henuz degil */
        if (p->sure && (int32_t)(simdi_unix - (p->bas + p->sure)) >= 0) {
            plan__durum(p, PLAN_KACIRILDI);
            return PE_YOK;
        }
        if (oturum_var) {                                         /* isi BOLMEZ */
            plan__durum(p, PLAN_ATLANDI);
            return PE_YOK;
        }
        return PE_BASLAT;
    }
    if (p->durum != PLAN_SURUYOR) return PE_YOK;
    if (!p->oturum) {                                             /* acilmasini bekle */
        if (oturum_var) {
            p->oturum = oturum_id;
            plan__yaz(p);
        } else if (simdi_unix && (uint32_t)(simdi_unix - p->baslat_unix) > PLAN_BASLAT_S) {
            plan__durum(p, PLAN_BITTI);
        }
        return PE_YOK;
    }
    if (!oturum_var || oturum_id != p->oturum) {                  /* Gd, DOLU, DEVAM yok */
        plan__durum(p, PLAN_BITTI);
        return PE_YOK;
    }
    if (!p->sure || !simdi_unix) return PE_YOK;
    if ((int32_t)(simdi_unix - (p->bas + p->sure)) >= 0) return PE_BITIR;
    return PE_YOK;
}

#endif /* KAYIT_PLAN_H */
