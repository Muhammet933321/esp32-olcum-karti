#ifndef SKOP_OLC_H
#define SKOP_OLC_H
/*
 * Osiloskop olcum matematigi — ASAMA 2 ve ASAMA 3 ORTAK.
 *
 * !! BU DOSYA ELLE DUZENLENMEZ. olcum2.h icindeki ayni blogun birebir
 *    kopyasidir ve uretim/skop_olc_uret.py tarafindan uretilir.
 *    uretim/test_skop_ayni.py iki metni karakter karakter karsilastirir;
 *    ayrisirlarsa zincir KALIR.
 *
 * Degisiklik yapacaksan: once olcum2.h icinde yap, sonra
 *     python uretim/skop_olc_uret.py
 */
#include <stdint.h>
#include <math.h>       /* sqrtf */

/* ═══════════════════════════════════════════════════════════════════════
   OSİLOSKOP ÖLÇÜMLERİ

   Gerçek osiloskopların ekranın altında gösterdiği otomatik ölçümler.
   Burada, `olcum2.h`'nin geri kalanı gibi PLATFORM BAĞIMSIZ yazıldı
   (int/double yok) — böylece AVR emülatöründe bit-birebir koşturulabiliyor
   ve doğrulama zincirine girebiliyor.

   Hepsi tek geçişte değil, birkaç kısa geçişte hesaplanıyor; 4000 örnek
   için 240 MHz'de toplam birkaç yüz mikrosaniye.
   ═══════════════════════════════════════════════════════════════════════ */

/* 1F (S2): ESP32-S3 derleyicisi (xtensa gcc, -ffp-contract=fast varsayılanı)
 * `a*b + c`yi tek komuta (madd.s / msub.s) KAYNAŞTIRIYORDU: aradaki yuvarlama
 * kalkıyor, kart AVR başvurusundan (ve ortak/src/skop.js'ten) ayrışıyordu —
 * "iki mimaride aynı IEEE sonucu" varsayımı bu blokta YANLIŞTI. Pragma bu
 * bloktaki fonksiyonlara `optimize` niteliği ekler: her işlem ayrı yuvarlanır,
 * ve GCC nitelikli fonksiyonu niteliği farklı bir çağırana GÖMMEZ (gömülse
 * çağıranın ayarıyla yeniden kaynaşırdı). AVR'de FMA yok; etkisiz.
 * Kanıt ikilide: B6 (test_firmware3.py) skop_olc'u söküp madd/msub arar. */
#pragma GCC push_options
#pragma GCC optimize ("fp-contract=off")

typedef struct {
    float vmax;        /* tepe (V, prob ucunda)            */
    float vmin;        /* dip                              */
    float vpp;         /* tepeden tepeye                   */
    float vort;        /* ortalama (DC bileşen)            */
    float vrms;        /* toplam RMS (DC dahil)            */
    float vac;         /* AC RMS (ortalama çıkarılmış)     */
    float frekans;     /* Hz — 0 ise ölçülemedi            */
    float periyot;     /* s                                */
    float duty;        /* % — orta seviyenin üstünde geçen */
    float t_yuksel;    /* s, %10→%90                       */
    float t_dus;       /* s, %90→%10                       */
    uint16_t cevrim;   /* ölçüme giren tam çevrim sayısı   */
} SkopOlcum;

/* İki örnek arasında `esik`in geçildiği kesirli konumu döndürür.
 * Doğrusal ara değerleme: kenar iki örnek arasına düşerse periyot
 * ölçümü örnek çözünürlüğüne hapsolmaz. Bu, frekans doğruluğunu
 * tipik olarak 10–50 kat iyileştiriyor. */
static float skop_kesisim(float onceki, float simdi, float esik)
{
    float fark = simdi - onceki;
    if (fark > -1e-9f && fark < 1e-9f) return 0.0f;
    return (esik - onceki) / fark;
}

/* uint64_t -> float, DOĞRU YUVARLANMIŞ (en yakına, eşitlikte çifte) ve her
 * platformda AYNI. Yalnız tam dönüşüm (< 2^24 + 1) ve 2'nin kuvvetiyle
 * çarpma kullanır; kütüphanenin (float)uint64_t yoluna (AVR'de libgcc /
 * avr-libc) güvenmez. JS karşılığı: ortak/src/skop.js `u64f`. */
static float skop_u64_float(uint64_t x)
{
    uint8_t k = 0u;
    uint8_t son = 0u;      /* son atılan bit (koruma)            */
    uint8_t artik = 0u;    /* daha önce atılanlardan biri 1 mi   */
    float f;
    while (x >= 16777216ull) {             /* 2^24: float'a tam sığmıyor */
        artik |= son;
        son = (uint8_t)(x & 1u);
        x >>= 1;
        k++;
    }
    if (son && (artik || (x & 1u))) x++;   /* 2^24 olabilir: yine tam */
    f = (float)(uint32_t)x;
    for (; k > 0u; k--) f *= 2.0f;         /* tam: yalnız üs değişir */
    return f;
}

/* ── SK2 (2026-10-10): ALT / ÜST DURUM SEVİYELERİ (IEEE 181 histogram yöntemi) ────────────
 * Eşikler (%50, %10–%90) ve kare dalganın genliği eskiden en küçük / en büyük ÖRNEKTEN
 * kuruluyordu: tek bir gürültü tepesi Vpp'yi şişiriyordu (kartta 5 V kare 6.3 V), alt
 * seviyedeki tek bir dip %10 eşiğini kaydırıp düşme süresini bozuyordu (3/20 yakalamada
 * 63–123 µs). Şimdi:
 *   - Histogram YIĞINDA (256 × uint16_t = 512 B; statik bellek yok). Kutu genişliği 2'nin
 *     kuvveti: kutu = (h − hmin) >> k, k en küçük kaydırma (en çok 256 kutu) — örnek başına
 *     bölme yok. Alt yarı [0, yarı), üst yarı [yarı, kutu_sayısı), yarı = ⌈kutu_sayısı / 2⌉.
 *   - Her yarının en kalabalık kutusu (eşitlikte KÜÇÜK indis) çevresindeki ±bant kutu
 *     (bant = kutu_sayısı / 16, yarının içinde kırpılır) o durumun bandıdır; bandaki
 *     örneklerin ORTALAMASI (tam tamsayı toplam / sayı, tek bölme) durum seviyesidir.
 *   - İKİ DURUM sayılması için her bant örneklerin en az 1/16'sını, iki bant birlikte en az
 *     3/4'ünü tutmalı. Sinüs (iki bant ~%32), üçgen (~%12), DC, gürültü ve iğne kümesi bu
 *     sınamayı GEÇEMEZ: seviyeler en küçük / en büyük örnek kalır ve skop_olc eski
 *     davranışla BİT BİT aynıdır (test_skop_olcum.py SK2 (c), dondurulmuş çıktılarla).
 * d[0] alt, d[1] üst seviye (kod, float32); dönüş 1 = iki durum. */
static uint8_t skop_durum(const uint16_t *ham, uint16_t adet, uint16_t hmin, uint16_t hmax,
                          float *d)
{
    uint16_t kutu[256];
    const uint16_t aralik = (uint16_t)(hmax - hmin);
    uint16_t i, b, kutu_say, yari, bant, la, lb, ua, ub, m_alt, m_ust;
    uint8_t k = 0u;
    uint32_t c_alt = 0u, c_ust = 0u, s_alt = 0u, s_ust = 0u;

    d[0] = (float)hmin;
    d[1] = (float)hmax;
    while ((uint16_t)(aralik >> k) > 255u) k++;
    kutu_say = (uint16_t)((uint16_t)(aralik >> k) + 1u);       /* 1 … 256 */
    if (kutu_say < 2u) return 0u;
    for (b = 0u; b < kutu_say; b++) kutu[b] = 0u;
    for (i = 0u; i < adet; i++) kutu[(uint16_t)(ham[i] - hmin) >> k]++;
    yari = (uint16_t)((kutu_say + 1u) / 2u);
    m_alt = 0u;
    for (b = 1u; b < yari; b++) if (kutu[b] > kutu[m_alt]) m_alt = b;
    m_ust = yari;
    for (b = (uint16_t)(yari + 1u); b < kutu_say; b++) if (kutu[b] > kutu[m_ust]) m_ust = b;
    bant = (uint16_t)(kutu_say / 16u);
    la = (m_alt > bant) ? (uint16_t)(m_alt - bant) : 0u;
    lb = (uint16_t)(m_alt + bant);
    if (lb >= yari) lb = (uint16_t)(yari - 1u);
    ua = (m_ust >= (uint16_t)(yari + bant)) ? (uint16_t)(m_ust - bant) : yari;
    ub = (uint16_t)(m_ust + bant);
    if (ub >= kutu_say) ub = (uint16_t)(kutu_say - 1u);
    for (i = 0u; i < adet; i++) {
        const uint16_t h = ham[i];
        b = (uint16_t)((uint16_t)(h - hmin) >> k);
        if (b >= la && b <= lb)      { c_alt++; s_alt += h; }
        else if (b >= ua && b <= ub) { c_ust++; s_ust += h; }
    }
    if (c_alt * 16u < (uint32_t)adet || c_ust * 16u < (uint32_t)adet
        || (c_alt + c_ust) * 4u < 3u * (uint32_t)adet) return 0u;
    d[0] = skop_u64_float(s_alt) / (float)c_alt;           /* c ≤ 65535: tam */
    d[1] = skop_u64_float(s_ust) / (float)c_ust;
    return 1u;
}

/* SK2: iki durumlu sinyalde bir geçiş ancak ÖNCEKİ durum en az üç örnek sürmüşse ve SONRAKİ
 * durum en az üç örnek sürüyorsa kenardır: geçişi başlatan örnekten (a) önceki üç örnek ve
 * tamamlayan örnekle (b) sonraki iki örnek orta seviyenin doğru yanında olmalı (üst yan
 * s ≥ orta, alt yan s < orta — kesişim kuralıyla aynı). Değilse en çok iki örnek genişliğinde
 * bir İĞNEDİR (ön süzgecin sildiği genişlik; ham kipte kartta ~%3) — kenar sayılmaz. Kaydın
 * başında / sonunda var olan örneklere bakılır. yukari: 1 yükselen, 0 düşen. */
static uint8_t skop_igne(const uint16_t *ham, uint16_t adet, uint16_t a, uint16_t b,
                         float orta, uint8_t yukari)
{
    uint32_t j;
    for (j = (a > 3u) ? (uint32_t)a - 3u : 0u; j < (uint32_t)a; j++)
        if (((float)ham[j] >= orta) == (yukari != 0u)) return 1u;
    for (j = (uint32_t)b; j <= (uint32_t)b + 2u && j < (uint32_t)adet; j++)
        if (((float)ham[j] >= orta) != (yukari != 0u)) return 1u;
    return 0u;
}

/* skop_olc + durum seviyeleri (kod): d[0] alt, d[1] üst; dönüş 1 = iki durum (SK2).
 * Kartın eğri yolu (skop_olc_kalibre) Vpp'yi bu seviyelerden kurar. */
static uint8_t skop_olc_d(const uint16_t *ham, uint16_t adet, float volt_adim,
                          float ornekleme_hz, SkopOlcum *o, float *d)
{
    uint16_t i;
    uint16_t hmin, hmax;
    uint32_t s1;
    uint64_t s2;
    float orta, hist, ust, alt;
    float ilk_kesim, son_kesim;
    uint16_t kesim_sayisi;
    uint8_t hazir, iki;
    float onceki;

    o->vmax = o->vmin = o->vpp = o->vort = 0.0f;
    o->vrms = o->vac = o->frekans = o->periyot = 0.0f;
    o->duty = o->t_yuksel = o->t_dus = 0.0f;
    o->cevrim = 0;
    d[0] = d[1] = 0.0f;
    if (adet == 0u || ornekleme_hz <= 0.0f) return 0u;

    /* --- 1. geçiş: uçlar + TAM tamsayı toplamlar ------------------------
     * 1F (S1): eskiden float32'de Σv ve Σv² toplanıp Vac = √(kare_ort − ort²)
     * alınıyordu: iki büyük, birbirine çok yakın sayının farkı (sadeleşme).
     * Sabit 2048 kodda Vac 0.196 V (doğrusu 0), ±3 kodluk gerçek gürültüde 0.
     * Şimdi kodların kendisi TAMSAYI toplanır, hiç yuvarlama olmadan:
     *   S1 = Σh   ≤ 65535·65535 < 2^32           (uint32_t)
     *   S2 = Σh²  ≤ 65535·65535² < 2^48          (uint64_t)
     *   n·S2 − S1² = n²·varyans (kod²) ≤ 65535⁴ < 2^64, ≥ 0 (Cauchy–Schwarz)
     * Varyans payı TAM hesaplanır, sonra TEK karekök: düz çizgide Vac TAM 0.
     * Vrms özdeşlikten: √(ort² + ac²) — iki terim de ≥ 0, sadeleşme yok; düz
     * çizgide √(ort²) = ort olduğundan Vrms == Vort TAM (IEEE ikili tabanda). */
    hmin = hmax = ham[0];
    s1 = 0u;
    s2 = 0u;
    for (i = 0u; i < adet; i++) {
        uint16_t h = ham[i];
        if (h < hmin) hmin = h;
        if (h > hmax) hmax = h;
        s1 += h;
        s2 += (uint32_t)h * h;
    }
    o->vmax = (float)hmax * volt_adim;
    o->vmin = (float)hmin * volt_adim;
    /* SK2: Vpp = durum seviyeleri farkı (kare dalganın GENLİĞİ); iki durum yoksa seviyeler
     * uç örneklerdir ve bu satır eskisiyle (vmax − vmin) aynı işlemdir. Gerçek tepeler
     * (aşım, iğne) Vmax / Vmin'de kalır. */
    iki = skop_durum(ham, adet, hmin, hmax, d);
    o->vpp  = d[1] * volt_adim - d[0] * volt_adim;
    {
        const float n = (float)adet;                     /* tam: < 2^16 */
        /* RMS'ler işaretsiz: eksi volt_adim'de de ≥ 0 (eski sözleşme) */
        const float va_mutlak = (volt_adim < 0.0f) ? -volt_adim : volt_adim;
        const uint64_t pay = (uint64_t)adet * s2 - (uint64_t)s1 * s1;
        const float ort = skop_u64_float(s1) / n;              /* kod */
        const float ac  = sqrtf(skop_u64_float(pay)) / n;      /* kod, ≥ 0 */
        o->vort = ort * volt_adim;
        o->vac  = ac * va_mutlak;
        o->vrms = sqrtf(ort * ort + ac * ac) * va_mutlak;
    }

    /* --- 2. geçiş: periyot, yükselen kenar kesişimleriyle -------------
     * Orta seviyede histerezisli kenar arıyoruz. Histerezis olmadan
     * gürültülü bir sinyalde her örnekte sahte kesişim sayardık. */
    orta = (d[0] + d[1]) * 0.5f;                   /* SK2: durum seviyelerinden */
    hist = (d[1] - d[0]) * 0.125f;                 /* %12.5 */
    if (hist < 1.0f) return iki;                   /* düz çizgi: ölçüm yok */

    ilk_kesim = son_kesim = 0.0f;
    kesim_sayisi = 0u;
    hazir = 0u;
    onceki = (float)ham[0];
    for (i = 1u; i < adet; i++) {
        float s = (float)ham[i];
        if (!hazir) {
            if (s < orta - hist) hazir = 1u;
        } else if (s >= orta) {
            float k = (float)(i - 1u) + skop_kesisim(onceki, s, orta);
            if (kesim_sayisi == 0u) ilk_kesim = k;
            son_kesim = k;
            kesim_sayisi++;
            hazir = 0u;
        }
        onceki = s;
    }

    if (kesim_sayisi >= 2u) {
        float ornek_periyot = (son_kesim - ilk_kesim) /
                              (float)(kesim_sayisi - 1u);
        if (ornek_periyot > 0.0f) {
            o->cevrim  = (uint16_t)(kesim_sayisi - 1u);
            o->periyot = ornek_periyot / ornekleme_hz;
            o->frekans = ornekleme_hz / ornek_periyot;

            /* Duty: yalnız TAM çevrimler üzerinde say — yarım çevrim
             * sayılırsa duty sistematik olarak kayar.
             * Kenar k = (i−1) + kesir, 0 < kesir ≤ 1: i, orta'yı geçen ilk
             * örnek. Sayılan örnekler (taban(ilk), taban(son)] — ilk kenardan
             * SONRAKİ örnekten son kenarın örneğine dek, tam (son − bas) tane
             * = tam çevrim sayısı × periyot. 1F (S3): eskiden [bas, son] idi,
             * ilk kenarın ÖNCESİNDEKİ (alttaki) örnek fazladan sayılıyordu:
             * temiz %50 kare %49.79 (120/241) okunuyordu. */
            {
                uint16_t bas = (uint16_t)ilk_kesim;
                uint16_t son = (uint16_t)son_kesim;
                uint16_t ust_sayi = 0u, top = 0u;
                for (i = (uint16_t)(bas + 1u); i <= son && i < adet; i++) {
                    if ((float)ham[i] >= orta) ust_sayi++;
                    top++;
                }
                if (top > 0u)
                    o->duty = 100.0f * (float)ust_sayi / (float)top;
            }
        }
    }

    /* --- 3. geçiş: yükselme / düşme süresi (%10 → %90) ----------------
     * KURAL (1F, S4): yükselme = %10'u yukarı geçişten (önceki < alt ≤ s)
     * %90'ı yukarı geçişe (önceki < ust ≤ s), ARADA sinyal %10'un altına
     * (s < alt) inmeden. İnerse — %90'a varmayan cüce darbe, kenarda geri
     * sekme — %10 noktası BIRAKILIR, sonraki yukarı geçişte yeniden kurulur.
     * Düşme simetrik: %90'ı aşağı geçişten (önceki > ust ≥ s) %10'u aşağı
     * geçişe (önceki > alt ≥ s), arada %90'ın üstüne (s > ust) çıkmadan.
     * Kayıttaki İLK tam geçiş ölçülür; bulununca tarama biter. Eskiden %10
     * noktası hiç bırakılmıyordu: %90'a varmayan bir darbe yükselme süresini
     * bir SONRAKİ kenara kadar uzatıyordu. */
    alt = d[0] + (d[1] - d[0]) * 0.1f;             /* SK2: durum seviyelerinden */
    ust = d[0] + (d[1] - d[0]) * 0.9f;
    {
        float t10 = -1.0f, t90 = -1.0f;
        uint16_t bas = 0u;                   /* SK2: geçişi başlatan örnek */
        onceki = (float)ham[0];
        for (i = 1u; i < adet && t90 < 0.0f; i++) {
            float s = (float)ham[i];
            if (t10 >= 0.0f && s < alt)
                t10 = -1.0f;                 /* %90'a varmadan geri indi */
            if (t10 < 0.0f && onceki < alt && s >= alt) {
                t10 = (float)(i - 1u) + skop_kesisim(onceki, s, alt);
                bas = i;
            }
            if (t10 >= 0.0f && onceki < ust && s >= ust) {
                t90 = (float)(i - 1u) + skop_kesisim(onceki, s, ust);
                if (iki && skop_igne(ham, adet, bas, i, orta, 1u))
                    t10 = t90 = -1.0f;       /* SK2: iğne, kenar değil */
            }
            onceki = s;
        }
        if (t10 >= 0.0f && t90 > t10)
            o->t_yuksel = (t90 - t10) / ornekleme_hz;
    }
    {
        float t90 = -1.0f, t10 = -1.0f;
        uint16_t bas = 0u;
        onceki = (float)ham[0];
        for (i = 1u; i < adet && t10 < 0.0f; i++) {
            float s = (float)ham[i];
            if (t90 >= 0.0f && s > ust)
                t90 = -1.0f;                 /* %10'a varmadan geri çıktı */
            if (t90 < 0.0f && onceki > ust && s <= ust) {
                t90 = (float)(i - 1u) + skop_kesisim(onceki, s, ust);
                bas = i;
            }
            if (t90 >= 0.0f && onceki > alt && s <= alt) {
                t10 = (float)(i - 1u) + skop_kesisim(onceki, s, alt);
                if (iki && skop_igne(ham, adet, bas, i, orta, 0u))
                    t90 = t10 = -1.0f;       /* SK2: iğne, kenar değil */
            }
            onceki = s;
        }
        if (t90 >= 0.0f && t10 > t90)
            o->t_dus = (t10 - t90) / ornekleme_hz;
    }
    return iki;
}

static void skop_olc(const uint16_t *ham, uint16_t adet, float volt_adim,
                     float ornekleme_hz, SkopOlcum *o)
{
    float d[2];
    (void)skop_olc_d(ham, adet, volt_adim, ornekleme_hz, o, d);
}

#pragma GCC pop_options    /* 1F (S2): bloğun başındaki push_options'ın eşi */

#endif /* SKOP_OLC_H */
