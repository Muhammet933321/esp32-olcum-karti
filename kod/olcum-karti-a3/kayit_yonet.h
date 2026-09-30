#ifndef KAYIT_YONET_H
#define KAYIT_YONET_H
/*
 * B72 — KAYIT YONETICISI: kartin kayit DURUM MAKINESI, platformsuz.
 *
 * Eskiden kayit_esp.h'nin icindeydi ve ESP32'ye bagli oldugu icin HIC
 * calistirilarak sinanmiyordu (1A-2 son inceleme O5). Artik NVS bir islev
 * tablosu, zaman parametre: ayni kod kartta Preferences ile, AVR testinde
 * (uretim/test_kayit.py B71.V) emule NVS + emule NOR ile acilistan acilisa
 * kosuyor.
 *
 * Kapatilan inceleme bulgulari:
 *   O1  akis KIMLIGI (NVS "kimlik"): NVS kaybolunca ya da flas NVS'in
 *       bildiginden GERIDE kalinca yenilenir -> PC eski akisa eklemez
 *   O2  onay "son gelen kazanir" (kuyrukta dusmez); sahte onay reddedilir
 *   O3  durum 4'te (acik oturum, yer yok) DURDURMA niyeti NVS'te ("kapat"):
 *       yer acilinca oturum SURDURULMEZ, BITIR(kullanici) ile kapanir
 *   O4  bicimleme MANTIKSAL: NVS'e taban yazmak (atomik), silme arka planda
 *       KYN_TEMIZ_MS aralikla (dolu sektor ~25 ms iki cekirdegi durdurur)
 *
 * NVS anahtarlari: acilis · kimlik · taban · onay (kisitli) · kapat
 * ⚠ Butun cagrilar KAYIT KILIDI altinda (kayit_esp.h).
 */
#include "kayit_oturum.h"

/* G satirindaki durum kodlari */
#define KDR_TARIYOR  0u
#define KDR_BOS      1u
#define KDR_KAYIT    2u
#define KDR_DOLU     3u
#define KDR_BEKLIYOR 4u   /* acik oturum var, yer yok: gecerli onay gelince DEVAM (ya da kapanis) */
#define KDR_HATA     5u

#ifndef KYN_ONAY_ARALIK
#define KYN_ONAY_ARALIK 16u        /* NVS'e onay: en az bu kadar sira ilerleyince */
#endif
#ifndef KYN_ONAY_MS
#define KYN_ONAY_MS 30000UL        /* ... ya da bu kadar sure gecince */
#endif
#ifndef KYN_TEMIZ_MS
#define KYN_TEMIZ_MS 200UL         /* arka plan silmeleri arasi en az */
#endif
#define KYN_TEMIZ_BAKIS 64u        /* bir adimda en fazla bu kadar sektore bakilir */
#ifndef KYN_HAZIR_HEDEF
#define KYN_HAZIR_HEDEF 480u       /* 1C-2: ~1.9 MB = ~10 dk ayrintili kayit */
#endif

typedef struct {
    uint32_t (*oku)(void *baglam, const char *ad, uint32_t varsayilan);
    int      (*yaz)(void *baglam, const char *ad, uint32_t deger);   /* 0 = tamam */
    void *baglam;
} KayitNvs;

typedef struct {
    KayitGunluk *g;
    KayitYazici *y;
    KayitNvs     nvs;
    uint8_t  hazir, hata, devam_bekliyor;
    uint32_t acilis, kimlik, kapat_id;
    uint32_t onay_nvs, onay_nvs_ms;
    uint32_t temiz_s, temiz_ms;      /* arka plan temizligi imleci (== sektor_adet: yok) */
    int32_t  son_hata;
    uint8_t  on_sil_izin;            /* 1C-2: DISARIDAN (kart: kayit/skop/pil yok) */
    uint8_t  on_sil_onceki;
} KayitYonetici;

static inline void kyn_kur(KayitYonetici *m, KayitGunluk *g, KayitYazici *y,
                           const KayitNvs *nvs)
{
    memset(m, 0, sizeof(*m));
    m->g = g;
    m->y = y;
    m->nvs = *nvs;
}

static inline void kyn__kapat_niyeti(KayitYonetici *m, uint32_t id)
{
    m->kapat_id = id;
    (void)m->nvs.yaz(m->nvs.baglam, "kapat", id);
}

/* Acik ama yazilmayan oturumu KAPAT (surdurmeden): yazici o oturuma
   hazirlanir, gerekirse yeni sektor + TEKRAR (her sektor kendini anlatsin),
   sonra BITIR(sebep) ayrilmis paya. */
static inline int kyn__kapat(KayitYonetici *m, uint32_t id, const KayitBasla *b,
                             uint32_t nokta_sonraki, uint8_t sebep)
{
    KayitYazici *y = m->y;
    int r;
    y->oturum = id;
    y->basla = *b;
    y->nokta_sira = nokta_sonraki;
    y->yuk_nokta = 0u;
    y->son_hata = 0;
    r = ky__yer(y, 0u);
    if (r) { y->oturum = 0u; return r; }
    return ky_bitir(y, sebep);
}

/* Acik olcum oturumunu surdur (DEVAM) — ya da kullanici durdurmussa KAPAT.
   Olcum DISI acik oturum (1C-1: pil testi) ASLA surdurulmez: "kart yeniden
   basladi" ile kapanir (emniyet, spec O7). Yazilamazsa (yer yok) oturum acik
   kalir: durum 4, onay gelince yeniden denenir. */
static inline void kyn__devam_dene(KayitYonetici *m, uint32_t simdi_ms, uint32_t unix_s)
{
    KayitGunluk *g = m->g;
    const KayitOzet *o = kg_acik_oturum(g), *h;
    KayitBasla b;
    KayitDevam d;
    uint32_t id;
    int r;
    m->devam_bekliyor = 0u;
    if (!o) {
        if (m->kapat_id) kyn__kapat_niyeti(m, 0u);     /* kapatilacak oturum kalmadi */
        return;
    }
    id = o->id;
    if (kg_basla_oku(g, o->basla_adres, id, &b)) { m->son_hata = KG_HATA; return; }
    if (o->tur != KAYIT_OTURUM_OLCUM) {
        r = kyn__kapat(m, id, &b, o->nokta_sonraki, KB_SEBEP_YENIDEN);
    } else if (id == m->kapat_id) {
        r = kyn__kapat(m, id, &b, o->nokta_sonraki, KB_SEBEP_KULLANICI);
    } else {
        d.acilis = m->acilis;
        d.unix_s = unix_s;
        d.kart_ms = simdi_ms;
        d.nokta_sira = 0u;
        r = ky_devam(m->y, id, &b, o->nokta_sonraki, &d);
    }
    h = kg_acik_oturum(g);
    if (h && h->id == id && !m->y->oturum) m->devam_bekliyor = 1u;   /* hala acik */
    else if (id == m->kapat_id) kyn__kapat_niyeti(m, 0u);            /* kapandi */
    if (r) m->son_hata = r;
}

static inline void kyn__onay_kaydet(KayitYonetici *m, uint8_t zorla, uint32_t simdi_ms)
{
    uint32_t o = m->g->onay;
    if (o == m->onay_nvs) return;
    if (zorla || o - m->onay_nvs >= KYN_ONAY_ARALIK
        || simdi_ms - m->onay_nvs_ms >= KYN_ONAY_MS) {
        if (!m->nvs.yaz(m->nvs.baglam, "onay", o)) {
            m->onay_nvs = o;
            m->onay_nvs_ms = simdi_ms;
        }
    }
}

/* ACILIS. `rastgele`: yeni akis kimligi gerekirse (kartta esp_random). */
static inline int kyn_ac(KayitYonetici *m, uint32_t simdi_ms, uint32_t unix_s,
                         uint32_t rastgele)
{
    KayitGunluk *g = m->g;
    uint32_t taban, onay, eski;
    uint8_t i;
    int r = KG_HATA;
    m->hazir = 0u;
    m->hata = 0u;
    m->devam_bekliyor = 0u;
    m->son_hata = 0;
    m->acilis = m->nvs.oku(m->nvs.baglam, "acilis", 0u) + 1u;
    (void)m->nvs.yaz(m->nvs.baglam, "acilis", m->acilis);
    m->kimlik = m->nvs.oku(m->nvs.baglam, "kimlik", 0u);
    taban = m->nvs.oku(m->nvs.baglam, "taban", 0u);
    onay = m->nvs.oku(m->nvs.baglam, "onay", 0u);
    m->kapat_id = m->nvs.oku(m->nvs.baglam, "kapat", 0u);
    m->onay_nvs = onay;
    m->onay_nvs_ms = simdi_ms;
    for (i = 0; i < 3u && r != KG_TAMAM; i++) r = kg_ac(g, taban, onay);
    if (r != KG_TAMAM) {
        m->hata = 1u;
        m->son_hata = r;
        return r;
    }
    /* O1: kimlik yoksa (NVS yeni ya da KAYIP) ya da flas NVS'in onayladigi
       yerden GERIDE (bolum kaybolmus/degismis) ise YENI akis: numara geri
       gidebilir, PC bunu eski akisin devami sanip veri kaybetmesin. */
    if (!m->kimlik || onay > g->sonraki_sira - 1u) {
        eski = m->kimlik;
        m->kimlik = rastgele ? rastgele : 1u;
        if (m->kimlik == eski) m->kimlik ^= 0x5A5A5A5AUL;
        (void)m->nvs.yaz(m->nvs.baglam, "kimlik", m->kimlik);
    }
    m->hazir = 1u;
    m->temiz_s = g->eski ? 0u : g->sektor_adet;
    m->temiz_ms = simdi_ms;
    kyn__devam_dene(m, simdi_ms, unix_s);
    return KG_TAMAM;
}

/* Yeni kayit. Durum 4'te bekleyen eski oturum SURDURULMEZ: kapatma niyetine
   alinir (yer yoksa acilistan sonra da gecerli). Donus: oturum id ya da KG_*. */
static inline int32_t kyn_baslat(KayitYonetici *m, const KayitBasla *b,
                                 uint32_t simdi_ms, uint32_t unix_s)
{
    int32_t r;
    if (!m->hazir) return KG_HATA;
    if (m->devam_bekliyor) {
        const KayitOzet *o = kg_acik_oturum(m->g);
        if (o) kyn__kapat_niyeti(m, o->id);
        kyn__devam_dene(m, simdi_ms, unix_s);          /* yer varsa hemen kapanir */
    }
    r = ky_baslat(m->y, b);
    m->son_hata = (r < 0) ? r : 0;
    return r;
}

/* Durdur. Durum 4'te: niyet (O3) — yer acilinca BITIR(kullanici). */
static inline int kyn_durdur(KayitYonetici *m)
{
    int r;
    if (m->y->oturum) {
        r = ky_bitir(m->y, KB_SEBEP_KULLANICI);
        m->son_hata = r;
        return r;
    }
    if (m->devam_bekliyor) {
        const KayitOzet *o = kg_acik_oturum(m->g);
        if (o) kyn__kapat_niyeti(m, o->id);
        return KG_TAMAM;
    }
    return KG_YOK;
}

/* 1C-1: etkin oturuma OLAY. Oturum yoksa KG_YOK (sessiz: pil testi kayitsiz
   da calisir, K5). */
static inline int kyn_olay(KayitYonetici *m, const uint8_t *yuk, uint16_t n)
{
    int r;
    if (!m->hazir) return KG_HATA;
    r = ky_olay(m->y, yuk, n);
    if (r && r != KG_YOK) m->son_hata = r;
    return r;
}

/* 1C-1: pil testi bitti — SONUC olayi, hemen ardindan BITIR(sebep). Yalniz
   etkin oturum PIL ise: test bittiginde baska bir oturum (olcum) aciksa ona
   dokunulmaz (KG_YOK). */
static inline int kyn_pil_bitir(KayitYonetici *m, const uint8_t *sonuc, uint16_t n,
                                uint8_t sebep)
{
    int r;
    if (!m->hazir) return KG_HATA;
    if (!m->y->oturum || m->y->basla.oturum_turu != KAYIT_OTURUM_PIL) return KG_YOK;
    r = ky_olay(m->y, sonuc, n);
    if (r) {                   /* DOLU: ky__dolu oturumu BITIR(DOLU) ile kapatti */
        m->son_hata = r;
        return r;
    }
    r = ky_bitir(m->y, sebep);
    m->son_hata = r;
    return r;
}

/* 1C-1: oturuma ad / etiket / not (NOT kaydi). Baslikta oturum 0, hedef
   yukun ilk 4 baytinda; 1 <= hedef < sonraki_sira olmali (verilmemis bir
   oturuma not yazilmaz). Yer acmak gerekirse etkin oturumun TEKRAR'i yazilir.
   Dolu ise KG_DOLU doner ama etkin oturum KAPATILMAZ: not onun verisi degil.
   Donus: kaydin sirasi (> 0; sonraki not onu `degistirir` ile hedefler) ya
   da KG_*. */
static inline int32_t kyn_not(KayitYonetici *m, const uint8_t *yuk, uint16_t n)
{
    uint32_t h;
    int32_t s;
    int r;
    if (!m->hazir) return KG_HATA;
    if (n < KAYIT_NOT_BAS) return KG_YOK;
    h = kayit_o32(yuk);
    if (!h || h >= m->g->sonraki_sira) return KG_YOK;
    r = ky__yer(m->y, kayit_toplam_bayt(n));
    if (r) {
        m->son_hata = r;
        return r;
    }
    s = kg_ekle(m->g, KAYIT_T_NOT, 0u, yuk, n);
    if (s < 0) m->son_hata = (int)s;
    return s;
}

/* Butun kayitlari sil — MANTIKSAL (O4). ONCE taban NVS'e: yazilamazsa hicbir
   sey degismez; yazildiysa elektrik kesilse de bicimleme tamam sayilir. */
static inline int kyn_bicimle(KayitYonetici *m, uint32_t simdi_ms)
{
    KayitGunluk *g = m->g;
    if (!m->hazir) return KG_HATA;
    if (m->y->oturum) (void)ky_bitir(m->y, KB_SEBEP_KULLANICI);
    if (m->nvs.yaz(m->nvs.baglam, "taban", g->sonraki_sira)) {
        m->son_hata = KG_HATA;
        return KG_HATA;
    }
    kg_bicimle_mantiksal(g);
    m->devam_bekliyor = 0u;
    if (m->kapat_id) kyn__kapat_niyeti(m, 0u);
    m->temiz_s = 0u;
    m->temiz_ms = simdi_ms;
    kyn__onay_kaydet(m, 1u, simdi_ms);
    m->son_hata = 0;
    return KG_TAMAM;
}

/* Gorev turu: onay (son gelen kazanir, O2) · 5 s bosaltma · arka plan
   temizligi (aralikli) · NVS'e kisitli onay. */
static inline void kyn_adim(KayitYonetici *m, uint32_t onay_istek, uint32_t simdi_ms,
                            uint32_t unix_s)
{
    KayitGunluk *g = m->g;
    uint8_t n;
    int r;
    if (!m->hazir) return;
    if (onay_istek > g->onay) {
        r = kg_onayla(g, onay_istek);
        if (r) {
            m->son_hata = r;                           /* sahte onay: yok sayilir, gorunur */
        } else if (m->devam_bekliyor) {
            kyn__devam_dene(m, simdi_ms, unix_s);
        }
    }
    r = ky_zaman(m->y, simdi_ms);
    if (r && r != KG_YOK) m->son_hata = r;
    /* 1C-2 son inceleme: ayrintili kayitta arka plan temizligi YOK — her dolu
       sektor ~25 ms iki cekirdegi durdurur (500 ms'de bir delik). Kafa eski
       sektoru kendisi siler, o silme sayilir ve isaretlenir (kg_ilerle). */
    if (m->temiz_s < g->sektor_adet && simdi_ms - m->temiz_ms >= KYN_TEMIZ_MS
        && !(m->y->oturum && m->y->ayrinti)) {
        for (n = 0; n < KYN_TEMIZ_BAKIS && m->temiz_s < g->sektor_adet; n++) {
            r = kg_temizle_adim(g, &m->temiz_s);
            if (r) {
                if (r < 0) m->son_hata = r;
                m->temiz_ms = simdi_ms;
                break;
            }
        }
    }
    /* 1C-2 HAZIR ALAN: bosta onayli sektorler onceden silinir (dolu sektor
       ~25 ms iki cekirdegi durdurur; ayrintili kayit sirasinda olmasin).
       Temizlikle AYNI aralik; izin yeni acildiysa once KYN_TEMIZ_MS bekle. */
    if (m->on_sil_izin && !m->on_sil_onceki) m->temiz_ms = simdi_ms;
    m->on_sil_onceki = m->on_sil_izin;
    if (m->on_sil_izin && !m->y->oturum && !m->devam_bekliyor
        && m->temiz_s >= g->sektor_adet && g->hazir < KYN_HAZIR_HEDEF
        && simdi_ms - m->temiz_ms >= KYN_TEMIZ_MS) {
        r = kg_on_sil_adim(g);
        if (r < 0) m->son_hata = r;
        else if (r) m->temiz_ms = simdi_ms;
    }
    kyn__onay_kaydet(m, 0u, simdi_ms);
}

static inline uint8_t kyn_durum(const KayitYonetici *m)
{
    if (!m->hazir) return m->hata ? KDR_HATA : KDR_TARIYOR;
    if (m->y->oturum) return KDR_KAYIT;
    if (m->devam_bekliyor) return KDR_BEKLIYOR;
    if (m->g->dolu) return KDR_DOLU;
    return KDR_BOS;
}

/* Aktif oturum; durum 4'te BEKLEYEN oturum (G satirinda gorunsun). */
static inline uint32_t kyn_oturum(const KayitYonetici *m)
{
    const KayitOzet *o;
    if (m->y->oturum) return m->y->oturum;
    if (m->devam_bekliyor) {
        o = kg_acik_oturum(m->g);
        if (o) return o->id;
    }
    return 0u;
}

#endif /* KAYIT_YONET_H */
