#ifndef KAYIT_NOKTA_H
#define KAYIT_NOKTA_H
/*
 * B71 — NOKTACI: ham ornekleri kayit noktasina toplar (olcum cekirdeginde,
 * her ornekte cagrilir).
 *
 * Kullanicinin kurali (2026-09-29): "sicramalari goz onunden alacak bir
 * islem asla istemiyorum". Bu yuzden her nokta ORTALAMANIN yaninda aralik
 * icindeki EN DUSUK ve EN YUKSEK HAM kodu da tasir: 200 ms'lik bir noktada
 * 5 ms'lik bir sicrama ortalamada erir ama min/maks'ta kalir.
 *
 * Kurallar:
 *   * Aralik `hiz_ms`; nokta cizelgesi kaymaz (bas += hiz).
 *   * Menzil degisirse nokta O ANDA kapanir: NORMAL ve YUKSEK kanalin kodu
 *     ayni noktada ASLA karismaz (ayni kod iki menzilde 19 kat farkli volt).
 *   * Okunamayan ornek (ADS hatasi) istatistige GIRMEZ, bayrak birakir.
 *   * Ornek gelmeyen aralik (skop ADS'i susturdu) bos nokta URETMEZ;
 *     sonraki nokta KN_DURAKLAMA tasir.
 *   * Toplamlar tam sayi: kod int32 (65535 x 32768 sigar), guc int64
 *     mikrowatt. float toplam uzun aralikta hassasiyet yerdi.
 */
#include "kayit_bicim.h"

#define KN_HATA_V 0x01u   /* kn_ornek `hata`: gerilim ADS'i okunamadi */
#define KN_HATA_I 0x02u   /* kn_ornek `hata`: akim ADS'i okunamadi */

typedef struct {
    uint32_t hiz_ms;
    uint32_t bas_ms;       /* bu noktanin basladigi an */
    uint8_t  menzil;       /* bu noktanin menzili (0/1) */
    uint8_t  ornek_var;    /* bu noktaya (gecerli ya da hatali) ornek geldi */
    uint8_t  bayrak;       /* bu noktanin birikmis KN_* bayraklari */
    uint8_t  bekleyen;     /* SONRAKI noktaya tasinacak bayraklar */
    uint16_t n;
    int32_t  v_top, i_top;
    int64_t  w_top_uw;
    int16_t  v_min, v_maks, i_min, i_maks;
    float    w_min, w_maks;
} KayitNoktaci;

static inline void kn__sifirla(KayitNoktaci *k)
{
    k->ornek_var = 0u;
    k->n = 0u;
    k->v_top = 0;
    k->i_top = 0;
    k->w_top_uw = 0;
    k->v_min = 32767;
    k->i_min = 32767;
    k->v_maks = -32768;
    k->i_maks = -32768;
    k->w_min = 0.0f;
    k->w_maks = 0.0f;
    k->bayrak = k->bekleyen;
    k->bekleyen = 0u;
}

/* Y1 (1C-1 inceleme M7): ornegin KN_DCIR bayragi YALNIZ PIL oturumunda kalir.
   Kayitsiz kalan pil testi (tarama sirasinda p1, kuyruk dolu) surerken acik ya
   da DEVAM almis bir OLCUM oturumu DCIR isaretli nokta almaz; diger bitler aynen. */
static inline uint8_t kn_ek_suz(uint8_t oturum_turu, uint8_t ek)
{
    return oturum_turu == KAYIT_OTURUM_PIL ? ek : (uint8_t)(ek & (uint8_t)~KN_DCIR);
}

static inline void kn_baslat(KayitNoktaci *k, uint32_t hiz_ms, uint32_t simdi_ms,
                             uint8_t menzil)
{
    k->hiz_ms = hiz_ms ? hiz_ms : 1u;
    k->bas_ms = simdi_ms;
    k->menzil = menzil ? 1u : 0u;
    k->bekleyen = 0u;
    kn__sifirla(k);
}

static inline void kn__kapat(KayitNoktaci *k, uint32_t bitis_ms, KayitNokta *c)
{
    c->kart_ms = bitis_ms;
    c->n = k->n;
    c->bayrak = (uint8_t)(k->bayrak | (k->menzil ? KN_YUKSEK : 0u));
    if (k->n) {
        c->v_ort_kod = (float)k->v_top / (float)k->n;
        c->i_ort_kod = (float)k->i_top / (float)k->n;
        c->w_ort = (float)k->w_top_uw / (float)k->n * 1.0e-6f;
        c->v_min_kod = k->v_min;
        c->v_maks_kod = k->v_maks;
        c->i_min_kod = k->i_min;
        c->i_maks_kod = k->i_maks;
        c->w_min = k->w_min;
        c->w_maks = k->w_maks;
    } else {
        c->v_ort_kod = 0.0f;
        c->i_ort_kod = 0.0f;
        c->w_ort = 0.0f;
        c->v_min_kod = c->v_maks_kod = 0;
        c->i_min_kod = c->i_maks_kod = 0;
        c->w_min = c->w_maks = 0.0f;
    }
    kn__sifirla(k);
}

/* Bir ornek ekle. Once sinir: menzil degistiyse ya da aralik dolduysa
   ELDEKI nokta `cikan`a yazilir ve 1 doner; ornek YENI noktaya girer.
   `ek`: bu ORNEGE ait ek bayrak (1C-1: KN_DCIR) — sinirdan SONRA, ornegin
   girdigi noktaya islenir (once islense kapanan eski noktaya duserdi). */
static inline uint8_t kn_ornek(KayitNoktaci *k, uint32_t simdi_ms, uint8_t menzil,
                               int16_t ham_v, int16_t ham_i, float watt,
                               uint8_t hata, uint8_t v_doydu, uint8_t ek,
                               KayitNokta *cikan)
{
    uint8_t cikti = 0u;
    menzil = menzil ? 1u : 0u;
    if (k->ornek_var) {
        if (menzil != k->menzil) {
            kn__kapat(k, simdi_ms, cikan);
            cikti = 1u;
            k->bas_ms = simdi_ms;
        } else if ((uint32_t)(simdi_ms - k->bas_ms) >= k->hiz_ms) {
            kn__kapat(k, k->bas_ms + k->hiz_ms, cikan);
            cikti = 1u;
            k->bas_ms += k->hiz_ms;
            if ((uint32_t)(simdi_ms - k->bas_ms) >= k->hiz_ms) {
                k->bas_ms = simdi_ms;
                k->bayrak |= KN_DURAKLAMA;
            }
        }
    } else if ((uint32_t)(simdi_ms - k->bas_ms) >= k->hiz_ms) {
        /* ornek gelmeyen aralik(lar): nokta URETILMEZ, zaman ilerler */
        k->bas_ms = simdi_ms;
        k->bayrak |= KN_DURAKLAMA;
    }
    k->menzil = menzil;
    k->ornek_var = 1u;
    k->bayrak |= ek;
    if (hata & KN_HATA_V) k->bayrak |= KN_V_HATA;
    if (hata & KN_HATA_I) k->bayrak |= KN_I_HATA;
    if (v_doydu) k->bayrak |= KN_V_DOYDU;
    if (!hata && k->n < 0xFFFFu) {
        int64_t w = (int64_t)(watt * 1.0e6f + (watt >= 0.0f ? 0.5f : -0.5f));
        if (k->n == 0u) {
            k->w_min = watt;
            k->w_maks = watt;
        } else {
            if (watt < k->w_min) k->w_min = watt;
            if (watt > k->w_maks) k->w_maks = watt;
        }
        k->n++;
        k->v_top += ham_v;
        k->i_top += ham_i;
        k->w_top_uw += w;
        if (ham_v < k->v_min) k->v_min = ham_v;
        if (ham_v > k->v_maks) k->v_maks = ham_v;
        if (ham_i < k->i_min) k->i_min = ham_i;
        if (ham_i > k->i_maks) k->i_maks = ham_i;
    }
    return cikti;
}

/* Ornek gelmese de (skop duraklamasi) aralik dolduysa noktayi kapat. */
static inline uint8_t kn_zaman(KayitNoktaci *k, uint32_t simdi_ms, KayitNokta *cikan)
{
    if (!k->ornek_var || (uint32_t)(simdi_ms - k->bas_ms) < k->hiz_ms) return 0u;
    kn__kapat(k, k->bas_ms + k->hiz_ms, cikan);
    k->bas_ms += k->hiz_ms;
    return 1u;
}

/* Kuyruk doluydu, az once uretilen nokta dustu: DEVAM EDEN noktaya isaret. */
static inline void kn_kayip(KayitNoktaci *k) { k->bayrak |= KN_KAYIP_ONCE; }

static inline void kn_bayrak(KayitNoktaci *k, uint8_t b) { k->bayrak |= b; }

#endif /* KAYIT_NOKTA_H */
