#ifndef KAYIT_ESP_H
#define KAYIT_ESP_H
/*
 * B72 — KAYIT MOTORUNUN KARTA BAGLANMASI (alt proje 1A-2).
 *
 * Motor kayit_*.h'de (B71; AVR emulatorunde emule NOR + elektrik kesme ile
 * sinaniyor). Bu dosya YALNIZ ESP32 yapistiricisi: flas bolumu
 * (esp_partition), NVS, cekirdek 0'daki kayit gorevi, kuyruklar, kilit.
 * Tasarim: tasarim/2026-09-29-yazilim-sistemi.md §5.
 * Plan: tasarim/2026-09-29-plan-1a2-kayit-firmware.md.
 *
 * 🔴 BURADA `Serial` YOK. Bu baslik `#define Serial CIKIS`'ten ONCE dahil
 *    ediliyor; burada basilan satir web aynasini (SSE) atlardi, ustelik
 *    cekirdek 0'dan basmak aynanin satir bolucusunu yarisa sokardi (B28:
 *    tek yazar). Butun basma .ino'da, cekirdek 1'de.
 *
 * CEKIRDEKLER:
 *   cekirdek 1 (loop)   kayit_ornek / kayit_duraklama: noktaci, nokta KUYRUGA
 *   cekirdek 0 (kayit)  kayit_gorevi: kuyruk -> ky_nokta, istekler, NTP, NVS
 *   cekirdek 0 (ag)     /kayit/liste ve /kayit/veri uclari: kg_oku
 * Butun kg_* / ky_* cagrilari `kayit_kilit` ALTINDA (1A-1 son inceleme).
 */
#include <Arduino.h>
#include <Preferences.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include "esp_partition.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "ag.h"

#define KG__PARCA 256u            /* flasi 256'lik parcalarla oku (AVR testinde 32) */
#include "kayit_nokta.h"
#include "kayit_oturum.h"

#define KAYIT_FW_SURUM    "A3-B72"
#define KAYIT_ALT_TUR     0x40      /* partitions.csv: kayit, data, 0x40 */
#define KAYIT_DIZIN_KAP   64u
#define KAYIT_KUYRUK      256u      /* nokta; 50/s'de ~5 s flas beklemesini yutar */
#define KAYIT_VERI_AZAMI  8192u     /* /kayit/veri tek yanit tavani (dahili RAM) */
#define KAYIT_ONAY_ARALIK 16u       /* NVS'e onay: en az bu kadar sira ilerleyince */
#define KAYIT_ONAY_MS     30000u    /* ... ya da bu kadar sure gecince */

/* G satirindaki durum kodlari */
#define KDR_TARIYOR  0u
#define KDR_BOS      1u
#define KDR_KAYIT    2u
#define KDR_DOLU     3u
#define KDR_BEKLIYOR 4u   /* acik oturum var, yer yok: gecerli onay gelince DEVAM */
#define KDR_HATA     5u

/* cekirdek 1 -> 0 istekleri */
#define KM_BASLAT  1u
#define KM_DURDUR  2u
#define KM_ONAY    3u
#define KM_BICIMLE 4u

typedef struct {
    uint8_t    tur;
    uint32_t   deger;
    KayitBasla basla;
} KayitMesaj;

typedef struct {
    uint8_t  durum;
    uint32_t oturum, nokta_sira, sonraki_sira, onay;
    uint16_t doluluk_binde, onaysiz_binde;
    uint32_t dusen, bozuk, silinen, sil_adet;
    uint32_t yaz_azami_us, sil_azami_us, tarama_ms;
    uint32_t acilis, hiz_ms, nesil;
    int32_t  son_hata;
} KayitDurum;

/* olcum_al'in son HAM ornegi — ikisi de cekirdek 1: olcum_al yazar, loop okur */
typedef struct {
    int16_t ham_v, ham_i;
    uint8_t hata, v_doydu, menzil;
} KayitHam;
static KayitHam kayit_ham;

static const esp_partition_t *kayit_bolum = nullptr;
static KayitSektor *kayit_sektor = nullptr;
static KayitOzet   *kayit_dizin = nullptr;
static uint8_t     *kayit_veri_tampon = nullptr;
static KayitGunluk  kayit_g;
static KayitYazici  kayit_y;
static SemaphoreHandle_t kayit_kilit = nullptr;
static QueueHandle_t kayit_nokta_q = nullptr;
static QueueHandle_t kayit_mesaj_q = nullptr;
static TaskHandle_t  kayit_gorev_kolu = nullptr;
static Preferences   kayit_nvs;
static KayitDurum    kayit_durum = {};
static portMUX_TYPE  kayit_mux = portMUX_INITIALIZER_UNLOCKED;

static volatile uint32_t kayit_kuyruk_dusen = 0;   /* cekirdek 1 yazar */
static volatile uint32_t kayit_yaz_azami_us = 0;
static volatile uint32_t kayit_sil_azami_us = 0;
static volatile uint32_t kayit_sil_adet = 0;

static uint8_t  kayit_hazir = 0, kayit_hata = 0;
static uint32_t kayit_acilis = 0, kayit_tarama_ms = 0;
static int32_t  kayit_son_hata = 0;
static uint8_t  kayit_devam_bekliyor = 0;
static uint32_t kayit_onay_nvs = 0, kayit_onay_nvs_ms = 0;
static uint8_t  kayit_saat_ntp = 0, kayit_saat_gecerli = 0;

/* ─────────────────────────────── flas: esp_partition */
static int kayit_f_oku(void *b, uint32_t a, void *h, uint32_t n)
{
    (void)b;
    return esp_partition_read(kayit_bolum, a, h, n) == ESP_OK ? 0 : -1;
}

static int kayit_f_yaz(void *b, uint32_t a, const void *k, uint32_t n)
{
    uint32_t t = micros();
    esp_err_t e;
    (void)b;
    e = esp_partition_write(kayit_bolum, a, k, n);
    t = micros() - t;
    if (t > kayit_yaz_azami_us) kayit_yaz_azami_us = t;
    return e == ESP_OK ? 0 : -1;
}

static int kayit_f_sil(void *b, uint32_t a)
{
    uint32_t t = micros();
    esp_err_t e;
    (void)b;
    e = esp_partition_erase_range(kayit_bolum, a, KAYIT_SEKTOR);
    t = micros() - t;
    if (t > kayit_sil_azami_us) kayit_sil_azami_us = t;
    kayit_sil_adet = kayit_sil_adet + 1u;
    return e == ESP_OK ? 0 : -1;
}

/* ─────────────────────────────── zaman */
static uint32_t kayit__unix(void)
{
    time_t t = time(nullptr);
    return (t > (time_t)1700000000) ? (uint32_t)t : 0u;   /* 0 = bilinmiyor */
}

/* ─────────────────────────────── durum (cekirdek 0 yazar, herkes okur) */
static KayitDurum kayit_durum_al(void)
{
    KayitDurum t;
    portENTER_CRITICAL(&kayit_mux);
    t = kayit_durum;
    portEXIT_CRITICAL(&kayit_mux);
    return t;
}

/* KILIT ALTINDA cagrilir */
static void kayit__durum_guncelle(void)
{
    KayitDurum t;
    memset(&t, 0, sizeof(t));
    if (!kayit_hazir) t.durum = kayit_hata ? KDR_HATA : KDR_TARIYOR;
    else if (kayit_y.oturum) t.durum = KDR_KAYIT;
    else if (kayit_devam_bekliyor) t.durum = KDR_BEKLIYOR;
    else if (kayit_g.dolu) t.durum = KDR_DOLU;
    else t.durum = KDR_BOS;
    t.oturum = kayit_y.oturum;
    t.nokta_sira = kayit_y.nokta_sira + kayit_y.yuk_nokta;
    t.sonraki_sira = kayit_g.sonraki_sira;
    t.onay = kayit_g.onay;
    if (kayit_hazir) {
        t.doluluk_binde = kg_binde(&kayit_g, kg_kullanilan(&kayit_g));
        t.onaysiz_binde = kg_binde(&kayit_g, kg_onaysiz(&kayit_g));
    }
    t.dusen = kayit_y.dusen + kayit_kuyruk_dusen;
    t.bozuk = kayit_g.bozuk;
    t.silinen = kayit_g.silinen_sektor;
    t.sil_adet = kayit_sil_adet;
    t.yaz_azami_us = kayit_yaz_azami_us;
    t.sil_azami_us = kayit_sil_azami_us;
    t.tarama_ms = kayit_tarama_ms;
    t.acilis = kayit_acilis;
    t.hiz_ms = kayit_y.oturum ? kayit_y.basla.hiz_ms : 0u;
    t.son_hata = kayit_son_hata;
    portENTER_CRITICAL(&kayit_mux);
    t.nesil = kayit_durum.nesil
            + ((t.durum != kayit_durum.durum || t.oturum != kayit_durum.oturum) ? 1u : 0u);
    kayit_durum = t;
    portEXIT_CRITICAL(&kayit_mux);
}

/* ─────────────────────────────── NVS'e onay (kisitli yazim) */
static void kayit__onay_kaydet(uint8_t zorla)
{
    uint32_t o = kayit_g.onay;
    if (o == kayit_onay_nvs) return;
    if (zorla || o - kayit_onay_nvs >= KAYIT_ONAY_ARALIK
        || millis() - kayit_onay_nvs_ms >= KAYIT_ONAY_MS) {
        kayit_nvs.putUInt("onay", o);
        kayit_onay_nvs = o;
        kayit_onay_nvs_ms = millis();
    }
}

/* ─────────────────────────────── acik oturumu surdur (KILIT ALTINDA) */
static void kayit__devam_dene(void)
{
    const KayitOzet *o = kg_acik_oturum(&kayit_g);
    const KayitOzet *h;
    KayitBasla b;
    KayitDevam d;
    uint32_t id;
    int r;
    if (!o || o->tur != KAYIT_OTURUM_OLCUM) return;
    id = o->id;
    if (kg_basla_oku(&kayit_g, o->basla_adres, id, &b)) return;
    d.acilis = kayit_acilis;
    d.unix_s = kayit__unix();
    d.kart_ms = millis();
    d.nokta_sira = 0u;
    r = ky_devam(&kayit_y, id, &b, o->nokta_sonraki, &d);
    /* DOLU: kafa sektoru temizse ky__dolu BITIR(DOLU) yazip oturumu kapatti.
       Kapatamadiysa (kafa yarim — 1A-1 bulgu 2) oturum hala ACIK: onay
       gelince yeniden denenecek. */
    h = kg_acik_oturum(&kayit_g);
    kayit_devam_bekliyor = (r == KG_DOLU && h && h->id == id) ? 1u : 0u;
    if (r) kayit_son_hata = r;
}

/* ─────────────────────────────── acilis (gorevde, KILIT ALTINDA) */
static void kayit__ac(void)
{
    static const KayitFlas f = { kayit_f_oku, kayit_f_yaz, kayit_f_sil, nullptr };
    uint32_t taban, onay, t0;
    uint8_t deneme;
    int r = KG_HATA;
    kayit_nvs.begin("kayit", false);
    kayit_acilis = kayit_nvs.getUInt("acilis", 0u) + 1u;
    kayit_nvs.putUInt("acilis", kayit_acilis);
    taban = kayit_nvs.getUInt("taban", 0u);
    onay = kayit_nvs.getUInt("onay", 0u);
    kayit_onay_nvs = onay;
    kayit_onay_nvs_ms = millis();
    kg_kur(&kayit_g, &f, kayit_bolum->size / KAYIT_SEKTOR,
           kayit_sektor, kayit_dizin, (uint16_t)KAYIT_DIZIN_KAP);
    ky_kur(&kayit_y, &kayit_g);
    t0 = millis();
    for (deneme = 0; deneme < 3u && r != KG_TAMAM; deneme++) r = kg_ac(&kayit_g, taban, onay);
    kayit_tarama_ms = millis() - t0;
    if (r != KG_TAMAM) {
        kayit_hata = 1u;
        kayit_son_hata = r;
        return;
    }
    kayit_hazir = 1u;
    kayit__devam_dene();
}

/* ─────────────────────────────── istekler (KILIT ALTINDA) */
static void kayit__mesaj(const KayitMesaj *m)
{
    int32_t r = 0;
    switch (m->tur) {
    case KM_BASLAT: {
        KayitBasla b = m->basla;
        if (!b.unix_s) b.unix_s = kayit__unix();
        kayit_devam_bekliyor = 0u;
        r = ky_baslat(&kayit_y, &b);
        break;
    }
    case KM_DURDUR:
        r = ky_bitir(&kayit_y, KB_SEBEP_KULLANICI);
        break;
    case KM_ONAY:
        r = kg_onayla(&kayit_g, m->deger);
        if (r == KG_TAMAM && kayit_devam_bekliyor) kayit__devam_dene();
        break;
    case KM_BICIMLE:
        if (kayit_y.oturum) (void)ky_bitir(&kayit_y, KB_SEBEP_KULLANICI);
        /* ONCE taban: bicimleme yarida kesilse de numara tekrar verilmez */
        kayit_nvs.putUInt("taban", kayit_g.sonraki_sira);
        r = kg_bicimle(&kayit_g);
        kayit__onay_kaydet(1u);
        kayit_devam_bekliyor = 0u;
        break;
    default:
        break;
    }
    kayit_son_hata = (r < 0 && r != KG_YOK) ? r : 0;   /* oturumsuz Gd hata degil */
}

/* ─────────────────────────────── NTP (gorevde) */
static void kayit__saat(void)
{
    if (!kayit_saat_ntp && ag_durum.kip == AG_STA) {
        configTime(0, 0, "pool.ntp.org", "time.google.com");
        kayit_saat_ntp = 1u;
    }
    if (!kayit_saat_gecerli && kayit__unix()) {
        kayit_saat_gecerli = 1u;
        if (kayit_y.oturum) {
            KayitSaat z;
            z.unix_s = kayit__unix();
            z.kart_ms = millis();
            z.acilis = kayit_acilis;
            (void)ky_saat(&kayit_y, &z);
        }
    }
}

/* ─────────────────────────────── gorev (cekirdek 0) */
static void kayit_gorevi(void *)
{
    KayitNokta p;
    KayitMesaj m;
    xSemaphoreTake(kayit_kilit, portMAX_DELAY);
    kayit__ac();
    kayit__durum_guncelle();
    xSemaphoreGive(kayit_kilit);
    for (;;) {
        bool var = xQueueReceive(kayit_nokta_q, &p, pdMS_TO_TICKS(100)) == pdTRUE;
        xSemaphoreTake(kayit_kilit, portMAX_DELAY);
        if (kayit_hazir) {
            while (var) {
                int r = ky_nokta(&kayit_y, &p, millis());
                if (r && r != KG_YOK) kayit_son_hata = r;
                var = xQueueReceive(kayit_nokta_q, &p, 0) == pdTRUE;
            }
            while (xQueueReceive(kayit_mesaj_q, &m, 0) == pdTRUE) kayit__mesaj(&m);
            (void)ky_zaman(&kayit_y, millis());
            kayit__saat();
            kayit__onay_kaydet(0u);
        }
        kayit__durum_guncelle();
        xSemaphoreGive(kayit_kilit);
    }
}

/* ─────────────────────────────── kurulum (setup, cekirdek 1) */
static bool kayit_kur(void)
{
    uint32_t adet;
    kayit_bolum = esp_partition_find_first(ESP_PARTITION_TYPE_DATA,
                                           (esp_partition_subtype_t)KAYIT_ALT_TUR, "kayit");
    if (!kayit_bolum) return false;
    adet = kayit_bolum->size / KAYIT_SEKTOR;
    kayit_sektor = (KayitSektor *)heap_caps_malloc(adet * sizeof(KayitSektor), MALLOC_CAP_SPIRAM);
    kayit_dizin = (KayitOzet *)heap_caps_malloc(KAYIT_DIZIN_KAP * sizeof(KayitOzet),
                                                 MALLOC_CAP_SPIRAM);
    kayit_veri_tampon = (uint8_t *)heap_caps_malloc(KAYIT_VERI_AZAMI,
                                                     MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    kayit_kilit = xSemaphoreCreateMutex();
    kayit_nokta_q = xQueueCreate(KAYIT_KUYRUK, sizeof(KayitNokta));
    kayit_mesaj_q = xQueueCreate(4, sizeof(KayitMesaj));
    if (!kayit_sektor || !kayit_dizin || !kayit_veri_tampon || !kayit_kilit
        || !kayit_nokta_q || !kayit_mesaj_q) {
        kayit_bolum = nullptr;
        return false;
    }
    xTaskCreatePinnedToCore(kayit_gorevi, "kayit", 8192, nullptr, 1, &kayit_gorev_kolu, 0);
    return true;
}

/* ─────────────────────────────── noktaci (cekirdek 1) */
static KayitNoktaci kayit_kn;
static uint32_t kayit_kn_nesil = 0xFFFFFFFFu;
static uint8_t  kayit_kn_aktif = 0;

static void kayit__gonder(const KayitNokta *c)
{
    if (!kayit_nokta_q || xQueueSend(kayit_nokta_q, c, 0) != pdTRUE) {
        kn_kayip(&kayit_kn);                           /* sonraki nokta isaretli */
        kayit_kuyruk_dusen = kayit_kuyruk_dusen + 1u;
    }
}

static void kayit__nesil(uint32_t simdi, uint8_t menzil)
{
    KayitDurum d = kayit_durum_al();
    if (d.nesil == kayit_kn_nesil) return;
    kayit_kn_nesil = d.nesil;
    kayit_kn_aktif = (d.durum == KDR_KAYIT && d.hiz_ms) ? 1u : 0u;
    if (kayit_kn_aktif) kn_baslat(&kayit_kn, d.hiz_ms, simdi, menzil);
}

/* Her ornekte (loop, olcum_al'dan sonra). */
static void kayit_ornek(float watt, uint32_t simdi)
{
    KayitNokta c;
    uint8_t hata = kayit_ham.hata;
    kayit__nesil(simdi, kayit_ham.menzil);
    if (!kayit_kn_aktif) return;
    if (!isfinite(watt)) hata |= (uint8_t)(KN_HATA_V | KN_HATA_I);   /* NaN int64'e cevrilemez */
    if (kn_ornek(&kayit_kn, simdi, kayit_ham.menzil, kayit_ham.ham_v, kayit_ham.ham_i,
                 watt, hata, kayit_ham.v_doydu, &c))
        kayit__gonder(&c);
}

/* Skop ADS'i sustururken (loop'un erken donusu). */
static void kayit_duraklama(uint32_t simdi)
{
    KayitNokta c;
    kayit__nesil(simdi, kayit_ham.menzil);
    if (kayit_kn_aktif && kn_zaman(&kayit_kn, simdi, &c)) kayit__gonder(&c);
}

#endif /* KAYIT_ESP_H */
