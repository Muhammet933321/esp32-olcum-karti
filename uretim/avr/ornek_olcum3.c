/*
 * Asama 3 olcum katinin AVR uzerinde kosturulmasi.
 *
 * NEDEN AVR: ESP32-S3'u komut komut calistiran bir emulatorumuz yok, ama
 * AVR'yi calistiran ve 39/39 bit birebir dogrulanmis bir emulatorumuz var
 * (test_avr.py). olcum3.h hicbir platform cagrisi icermedigi ve her yerde
 * acik genislikli tip + float kullandigi icin iki mimaride de AYNI
 * IEEE-754 sonucu verir. Burada kosturulan kod, ESP32'de kosacak kodun
 * ta kendisidir.
 *
 * Beklenen degerler bir YENIDEN-UYGULAMADAN gelmiyor; hepsi analitik
 * olarak biliniyor (bkz. test_olcum3.py).
 */
#include <avr/io.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#include "olcum3.h"
#include "web_satir.h"

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

static void metin(const char *s) { while (*s) yaz(*s++); }

static void hex8(uint8_t v)
{
    const char *h = "0123456789abcdef";
    yaz(h[v >> 4]);
    yaz(h[v & 15]);
}

static void hexf(float f)
{
    uint8_t b[4];
    memcpy(b, &f, 4);
    for (int8_t i = 3; i >= 0; i--) hex8(b[i]);
}

static void hex64(int64_t v)
{
    uint64_t u = (uint64_t)v;
    for (int8_t i = 7; i >= 0; i--) hex8((uint8_t)(u >> (i * 8)));
}

static void alan(const char *ad, float v) { metin(" "); metin(ad); metin(" "); hexf(v); }

/* Gercek Vin'den ADS'in gorecegi ham kodu uretir (kalibrasyonsuz ideal). */
static int16_t ham_uret(float vin, const Kanal3 *k)
{
    float fark = (vin - VREF_NOMINAL) / k->n;
    float kod = fark / (k->pga / ADS_SAYIM);
    if (kod > 32767.0f) kod = 32767.0f;
    if (kod < -32768.0f) kod = -32768.0f;
    /* YUVARLA, kesme: gercek ADC en yakin koda yuvarlar. */
    return yuvarla16(kod);
}

int main(void)
{
    uart_baslat();

    Kanal3 normal, yuksek;
    varsayilan_kanal3(&normal, &yuksek);

    /* ---------------- 1. sabitler ---------------- */
    metin("SBT");
    alan("n1", normal.n);
    alan("n2", yuksek.n);
    alan("vr", VREF_NOMINAL);
    alan("f1", tam_olcek_simetrik(&normal));
    alan("f2", tam_olcek_simetrik(&yuksek));
    alan("u1", tam_olcek_ust(&normal));
    alan("l1", tam_olcek_alt(&normal));
    alan("a1", adim3(&normal));
    alan("a2", adim3(&yuksek));
    metin("\r\n");

    /* ---------------- 2. CIFT YONLU gerilim: gidis-donus ---------------- */
    /* Negatiften pozitife: her nokta icin ham kod uret, geri coz. */
    static const float NOKTA[9] = {
        -600.0f, -400.0f, -100.0f, -12.0f, 0.0f, 12.0f, 100.0f, 400.0f, 600.0f
    };
    for (uint8_t i = 0; i < 9; i++) {
        int16_t h = ham_uret(NOKTA[i], &yuksek);
        metin("HV ");
        hexf(NOKTA[i]);
        metin(" ");
        hexf(olc_gerilim3(h, &yuksek));
        metin("\r\n");
    }
    static const float NOKTA2[7] = {
        -32.0f, -12.0f, -1.0f, 0.0f, 1.0f, 12.0f, 32.0f
    };
    for (uint8_t i = 0; i < 7; i++) {
        int16_t h = ham_uret(NOKTA2[i], &normal);
        metin("NV ");
        hexf(NOKTA2[i]);
        metin(" ");
        hexf(olc_gerilim3(h, &normal));
        metin("\r\n");
    }

    /* ---------------- 3. kalibrasyon ---------------- */
    /* Bozuk bir kanal kur: %3 kazanc hatasi + sifir kodu 60 LSB kaymis
     * (op-amp ofseti + ADS ofseti gibi). 60 LSB x 1.042 mV = 62 mV. */
    Kanal3 bozuk = normal;
    bozuk.kazanc = 1.03f;
    bozuk.sifir_ham = (int16_t)(normal.sifir_ham + 60);

    /* sifir kalibrasyonu: giris 0 V */
    int16_t h0 = ham_uret(0.0f, &normal);
    metin("KAL0 ");
    hexf(olc_gerilim3(h0, &bozuk));          /* kalibrasyon ONCESI */
    kalibre_sifir(h0, &bozuk);
    metin(" ");
    hexf(olc_gerilim3(h0, &bozuk));          /* kalibrasyon SONRASI: 0 olmali */
    metin("\r\n");

    /* kazanc kalibrasyonu: giriste bilinen 12 V */
    int16_t h12 = ham_uret(12.0f, &normal);
    metin("KALG ");
    hexf(olc_gerilim3(h12, &bozuk));         /* once */
    kalibre_kazanc(h12, 12.0f, &bozuk);
    metin(" ");
    hexf(olc_gerilim3(h12, &bozuk));         /* sonra: 12.0 olmali */
    metin(" ");
    hexf(bozuk.kazanc);
    metin("\r\n");
    /* kalibrasyon sonrasi BASKA bir noktada da dogru mu (dogrusallik) */
    int16_t hn = ham_uret(-24.0f, &normal);
    metin("KALX ");
    hexf(olc_gerilim3(hn, &bozuk));
    metin("\r\n");

    /* kazanc kalibrasyonu SIFIRA yakin girisle REDDEDILMELI */
    Kanal3 red = normal;
    float kazanc_once = red.kazanc;
    kalibre_kazanc(ham_uret(0.0f, &normal), 5.0f, &red);
    metin("KALR ");
    hexf(kazanc_once);
    metin(" ");
    hexf(red.kazanc);
    metin("\r\n");

    /* 🔴 B22.1 — TUGLALAMA TESTI (K3).
       Ciplak `g` komutu atof("") = 0 uretiyordu: kalibre_kazanc(ham, 0, k)
       -> kazanc *= 0/s -> 0. Kazanc 0 olunca olc_gerilim3 HEP 0 doner,
       yani kalibre_kazanc'in |s| > esik sarti bir daha ASLA saglanmaz:
       kanal NVS silinene kadar KALICI olarak olur.
       Bu, komut ayristiricisindaki duzeltmeden BAGIMSIZ ikinci savunma
       hatti — metin testi degil, gercek kodun DAVRANISI sinaniyor. */
    Kanal3 tugla = normal;
    int16_t ham_12 = ham_uret(12.0f, &normal);
    kalibre_kazanc(ham_12, 0.0f, &tugla);       /* ciplak `g` benzetimi */
    metin("KALB ");
    hexf(tugla.kazanc);                          /* 1: sifirlanmamali */
    kalibre_kazanc(ham_12, 12.0f, &tugla);       /* KURTARILABILIR mi */
    metin(" ");
    hexf(tugla.kazanc);                          /* 2: makul kalmali */
    metin(" ");
    hexf(olc_gerilim3(ham_12, &tugla));          /* 3: 12 V okumali */
    metin("\r\n");

    /* ---------------- 3b. B22.4 SATIR TAMPONU ---------------- */
    /* `Serial` aynasinin bayt akisini satirlara bolen parcasi. SSE'nin
       hangi satirlari tasidigi buna bagli: yanlis bolerse arayuzun tek
       ayristiricisi hizasini kaybeder. Sinir kosullari donanimsiz
       sinanabilsin diye saf C yazildi. */
    {
        SatirTampon st;
        satir_sifirla(&st);
        uint16_t hazir = 0, uzunluk = 0;

        /* (a) duz satir */
        const char *a = "D 12.3456 0.891234\n";
        for (const char *p = a; *p; p++) if (satir_ekle(&st, *p)) { hazir++; uzunluk = st.n; }
        /* satir_ekle n'i sifirliyor; uzunlugu tampondan olcelim */
        uzunluk = (uint16_t)strlen(st.tampon);

        /* (b) CRLF — firmware println CRLF yaziyor */
        const char *b = "A menzil=NORMAL\r\n";
        for (const char *p = b; *p; p++) if (satir_ekle(&st, *p)) hazir++;
        uint8_t crlf_temiz = (strchr(st.tampon, '\r') == 0);

        /* (c) BOS satir — SSE'ye gitmemeli */
        uint16_t bos_once = hazir;
        satir_ekle(&st, '\n');
        uint8_t bos_atlandi = (hazir == bos_once);

        /* (d) TASMA — 300 baytlik satir kirpilmali ama TAMAMLANMALI */
        for (uint16_t i = 0; i < 300; i++) satir_ekle(&st, 'x');
        uint8_t tasan_tamam = satir_ekle(&st, '\n');

        metin("WSAT ");
        hexf((float)hazir);        /* beklenen 2 (a, b) — (d) ayrica sayiliyor */
        metin(" ");
        hexf((float)uzunluk);      /* beklenen 18 */
        metin(" ");
        hexf((float)crlf_temiz);   /* beklenen 1 */
        metin(" ");
        hexf((float)bos_atlandi);  /* beklenen 1 */
        metin(" ");
        hexf((float)tasan_tamam);  /* beklenen 1 */
        metin(" ");
        hexf((float)st.kirpilan);  /* beklenen 300-223 = 77 */
        metin(" ");
        hexf((float)st.satir);     /* beklenen 3 */
        metin("\r\n");
    }

    /* ---------------- 4. CIFT YONLU akim ---------------- */
    /* PGA +-0.256, sont 0.1 ohm -> +-2.56 A */
    for (int8_t s = -3; s <= 3; s++) {
        int16_t ham = (int16_t)(s * 10000);
        metin("AK ");
        hexf((float)s);
        metin(" ");
        hexf(olc_akim3(ham, 0, PGA_0256, 0.1f, 1.0f));
        metin("\r\n");
    }

    /* ---------------- 5. ISARETLI enerji ---------------- */
    /* 10 s boyunca +2 W, sonra 10 s boyunca -2 W -> net 0 J */
    int64_t e = 0;
    for (uint16_t i = 0; i < 1000; i++) e = enerji_ekle3(e, 2.0f, 10000u);
    metin("EN1 ");
    hex64(e);
    metin(" ");
    hexf(enerji_joule3(e));
    metin("\r\n");
    for (uint16_t i = 0; i < 1000; i++) e = enerji_ekle3(e, -2.0f, 10000u);
    metin("EN2 ");
    hex64(e);
    metin(" ");
    hexf(enerji_joule3(e));
    metin("\r\n");
    /* Wh donusumu: 3600 J = 1 Wh */
    int64_t e2 = 0;
    for (uint16_t i = 0; i < 3600; i++) e2 = enerji_ekle3(e2, 1.0f, 1000000u);
    metin("ENW ");
    hexf(enerji_joule3(e2));
    metin(" ");
    hexf(enerji_wh3(e2));
    metin("\r\n");
    /* buyuk guc: int32 tasmasini tetikleyecek deger (7000 W) */
    int64_t e3 = enerji_ekle3(0, 7000.0f, 1000000u);
    metin("ENB ");
    hexf(enerji_joule3(e3));
    metin("\r\n");

    /* ---------------- 5b. B21: ISARETLI YUK (mAh) SAYACI ----------------
     * Enerjinin kardesi. Uc sey sinaniyor:
     *   YK1 : 1 A x 3600 s = 1000 mAh  (birim zinciri dogru mu)
     *   YK2 : desarj + ESIT sarj -> net TAM SIFIR  (sayac ISARETLI mi)
     *   YK3 : negatif akim tek basina NEGATIF yuk veriyor mu
     * sim3_pil.py bunu SINAYAMAZ (orada yalnizca birim aritmetigi var);
     * sayacin ISARETLI davranisi ancak GERCEK KODDA gorulur.
     */
    int64_t q1 = 0;
    for (uint16_t i = 0; i < 3600; i++) q1 = yuk_ekle3(q1, 1.0f, 1000000u);
    metin("YK1 ");
    hexf(yuk_mAh3(q1));
    metin(" ");
    hexf(yuk_coulomb3(q1));
    metin("\r\n");
    int64_t q2 = 0;
    for (uint16_t i = 0; i < 500; i++) q2 = yuk_ekle3(q2, 2.5f, 20000u);
    for (uint16_t i = 0; i < 500; i++) q2 = yuk_ekle3(q2, -2.5f, 20000u);
    metin("YK2 ");
    hex64(q2);
    metin(" ");
    hexf(yuk_mAh3(q2));
    metin("\r\n");
    int64_t q3 = yuk_ekle3(0, -1.5f, 2000000u);
    metin("YK3 ");
    hexf(yuk_mAh3(q3));
    metin("\r\n");

    /* ---------------- 6. LAGRANGE HIZALAYICI ---------------- */
    /*
     * v[n] = sin(w n)              (gerilim, t = n*T anlarinda)
     * i[n] = sin(w (n+0.5) - fi)   (akim, YARIM ornek GEC ornekleniyor)
     *
     * Gercek guc = 0.5*cos(fi).
     * Duzeltmesiz: ort(v[n]*i[n]) — yanli.
     * Duzeltmeli : ort(v[n]*hizala(i)) — hizalayici i'yi yarim ornek GERI
     * kaydirir, boylece v ile ayni ana gelir.
     *
     * DIZI KULLANILMIYOR — KAYAN PENCERE.
     * Ilk surumde `static float vv[264], ii[264]` vardi: 2112 bayt.
     * ATmega328P'nin SRAM'i 2048 bayt — TASTI ve degerler cop cikti.
     * Hizalayici yalnizca 4 ardisik ornek istedigi icin 4 float yeter.
     *
     * TAM SAYIDA PERIYOT: ortalama tam olsun diye N = (ornek/periyot) x cevrim.
     * Boylece beklenen deger analitik olarak TAM 0.5*cos(fi).
     */
    {
        const float FS = 41666.5f;
        static const uint16_t SPP[3] = {800u, 40u, 8u};
        static const uint16_t CEV[3] = {2u, 25u, 100u};
        static const float FI[3] = {0.0f, 1.0471975512f, 1.4706289056f};
        /* fi = 0 (PF=1) · pi/3 (PF=0.5) · acos(0.1) (PF=0.1) */
        for (uint8_t fi_i = 0; fi_i < 3; fi_i++) {
            for (uint8_t f_i = 0; f_i < 3; f_i++) {
                uint16_t spp = SPP[f_i];
                uint16_t N = (uint16_t)(spp * CEV[f_i]);
                float fi = FI[fi_i];
                float w = 2.0f * 3.14159265358979f / (float)spp;
                float frek = FS / (float)spp;

                float im2 = sinf(w * (-1.5f) - fi);
                float im1 = sinf(w * (-0.5f) - fi);
                float i0 = sinf(w * (0.5f) - fi);
                float ham = 0.0f, hiz = 0.0f;
                for (uint16_t n = 0; n < N; n++) {
                    float ip1 = sinf(w * ((float)n + 1.5f) - fi);
                    float v = sinf(w * (float)n);
                    ham += v * i0;
                    hiz += v * hizala_yarim(im2, im1, i0, ip1);
                    im2 = im1;
                    im1 = i0;
                    i0 = ip1;
                }
                ham /= (float)N;
                hiz /= (float)N;
                metin("LG ");
                hexf(frek);
                metin(" ");
                hexf(fi);
                metin(" ");
                hexf(ham);
                metin(" ");
                hexf(hiz);
                metin("\r\n");
            }
        }
    }

    /* hizalayicinin DC kazanci tam 1 olmali */
    metin("LGDC ");
    hexf(hizala_yarim(1.0f, 1.0f, 1.0f, 1.0f));
    metin("\r\n");

    /* ---------------- 7. olc3() birlesik yol ---------------- */
    /* 12 V, -1.5 A -> guc -18 W (yuk kaynak durumuna gecmis) */
    {
        int16_t hv = ham_uret(12.0f, &normal);
        int16_t hi = (int16_t)(-1.5f * 0.1f / (PGA_0256 / ADS_SAYIM));
        Okuma3 o = olc3(hv, hi, &normal, 0, PGA_0256, 0.1f, 1.0f);
        metin("OLC ");
        hexf(o.volt);
        metin(" ");
        hexf(o.amper);
        metin(" ");
        hexf(o.watt);
        metin("\r\n");
    }

    /* ---------------- 8. GUC OLCUMU (B8) ---------------- */
    /*
     * guc_olc() hizli yolun tam guc hesabi. Hizalayiciyi GERCEKTEN
     * kullanan yer burasi.
     *
     * Analitik olarak bilinen sinuslar:
     *   v[n] = Vg * sin(w n)
     *   i[n] = Ig * sin(w (n+0.5) - fi)     <- yarim ornek GEC
     * Beklenen:  P = Vg*Ig/2 * cos(fi)
     *            Vrms = Vg/sqrt(2),  Irms = Ig/sqrt(2)
     *            S = Vg*Ig/2,  PF = cos(fi)
     *
     * DIZI: guc_olc() dizi istiyor. ATmega328P'de 2048 bayt SRAM var,
     * 2 x 120 x 4 = 960 bayt — sigar. (Ilk surumde 264'luk diziler
     * kullanmistim ve TASMISTI; bkz. bolum 6 notu.)
     */
    {
        /* PENCERE UZUNLUGU KRITIK — ilk surumde N=120 (3 periyot) idi ve
         * hepsi %+2.48 hata veriyordu. Sebep faz DEGIL: hizalayici
         * kenarlari dusurunce 117 ornek kaliyor, o da 2.925 periyot —
         * TAM SAYI DEGIL. Tam olmayan pencerede sin^2'nin ortalamasi
         * 0.5 degil, artik terim kaliyor.
         * guc_olc() n = 2 .. adet-2 kullaniyor -> adet-3 ornek.
         * Tam 3 periyot (120 ornek) icin adet = 123 verilmeli. */
        static float vd[124], id[124];
        const uint16_t SPP = 40u;          /* ornek/periyot */
        const uint16_t N = 123u;           /* -3 kenar = 120 = TAM 3 periyot */
        const float VG = 10.0f, IG = 0.5f;
        static const float FI2[3] = {0.0f, 1.0471975512f, 1.4706289056f};

        for (uint8_t f_i = 0; f_i < 3; f_i++) {
            float fi = FI2[f_i];
            float w = 2.0f * 3.14159265358979f / (float)SPP;
            for (uint16_t n = 0; n < N; n++) {
                vd[n] = VG * sinf(w * (float)n);
                id[n] = IG * sinf(w * ((float)n + 0.5f) - fi);
            }
            GucOlcum g1, g0;
            guc_olc(vd, id, N, 1u, &g1);    /* hizalamali */
            guc_olc(vd, id, N, 0u, &g0);    /* hizalamasiz */

            metin("GU ");
            hexf(fi);
            metin(" ");
            hexf(g1.p);      metin(" ");
            hexf(g1.s);      metin(" ");
            hexf(g1.pf);     metin(" ");
            hexf(g1.v_rms);  metin(" ");
            hexf(g1.i_rms);  metin(" ");
            hexf(g0.p);      metin(" ");
            hexf((float)g1.n);
            metin("\r\n");
        }

        /* PENCERE YANLILIGI — tam sayi periyot OLMAYAN pencere.
         * Gercek kartta edinim penceresi sinyalin periyoduna hizali
         * olmayacak, yani bu yanlilik GERCEK. Buyuklugunu olcelim. */
        {
            float w = 2.0f * 3.14159265358979f / (float)SPP;
            for (uint16_t n = 0; n < N; n++) {
                vd[n] = VG * sinf(w * (float)n);
                id[n] = IG * sinf(w * ((float)n + 0.5f));
            }
            GucOlcum ga, gb;
            guc_olc(vd, id, 123u, 1u, &ga);   /* 120 ornek = 3.00 periyot */
            guc_olc(vd, id, 113u, 1u, &gb);   /* 110 ornek = 2.75 periyot */
            metin("GUP ");
            hexf(ga.p); metin(" ");
            hexf(gb.p);
            metin("\r\n");
        }

        /* Cok kisa pencere: olcum YAPILMAMALI */
        GucOlcum gk;
        guc_olc(vd, id, 4u, 1u, &gk);
        metin("GUK ");
        hexf((float)gk.n); metin(" ");
        hexf(gk.p);        metin(" ");
        hexf(gk.pf);
        metin("\r\n");

        /* DC yuk: v ve i sabit -> P = V*I, PF = 1 */
        for (uint16_t n = 0; n < N; n++) { vd[n] = 12.0f; id[n] = 0.25f; }
        GucOlcum gd;
        guc_olc(vd, id, N, 1u, &gd);
        metin("GUD ");
        hexf(gd.p);     metin(" ");
        hexf(gd.pf);    metin(" ");
        hexf(gd.v_rms); metin(" ");
        hexf(gd.i_rms);
        metin("\r\n");

        /* TERS akim: i negatif sabit -> guc NEGATIF, PF = -1 */
        for (uint16_t n = 0; n < N; n++) { id[n] = -0.25f; }
        GucOlcum gt;
        guc_olc(vd, id, N, 1u, &gt);
        metin("GUT ");
        hexf(gt.p);  metin(" ");
        hexf(gt.pf);
        metin("\r\n");
    }


    /* ═══════════════════════════ B17 — GENEL KESIRLI GECIKME */
    {
        /* LK1: d = 1/2'de genel fonksiyon, hizala_yarim ile AYNI mi?
         * Ayni olmazsa B5'in kaniti genel fonksiyona TASINAMAZ. */
        float en_fark = 0.0f;
        for (uint16_t k = 0; k < 64u; k++) {
            float a = sinf(0.1f * (float)k);
            float b = cosf(0.17f * (float)k);
            float c = sinf(0.31f * (float)k + 0.5f);
            float e = cosf(0.07f * (float)k + 1.1f);
            float y1 = hizala_yarim(a, b, c, e);
            float y2 = hizala_kesirli(0.5f, a, b, c, e);
            float f = y1 - y2;
            if (f < 0.0f) f = -f;
            if (f > en_fark) en_fark = f;
        }
        metin("LK1 ");
        hexf(en_fark);
        metin("\r\n");

        /* LK2: d = 0 ve d = 1 uc noktalari — tam ornege oturmali */
        metin("LK2 ");
        hexf(hizala_kesirli(0.0f, 10.0f, 20.0f, 30.0f, 40.0f));  /* 20 */
        metin(" ");
        hexf(hizala_kesirli(1.0f, 10.0f, 20.0f, 30.0f, 40.0f));  /* 30 */
        metin("\r\n");

        /* LK3: DC kazanci — her d icin katsayilar toplami 1 olmali */
        {
            float en_dc = 0.0f;
            for (uint8_t s = 0; s <= 10u; s++) {
                float d = (float)s * 0.1f;
                float y = hizala_kesirli(d, 5.0f, 5.0f, 5.0f, 5.0f);
                float f = y - 5.0f;
                if (f < 0.0f) f = -f;
                if (f > en_dc) en_dc = f;
            }
            metin("LK3 ");
            hexf(en_dc);
            metin("\r\n");
        }

        /* LK4: GERCEK is — bilinen bir kayma silinebiliyor mu?
         * v ve i ayni sinus, ama i `kay` ornek GEC ornekleniyor.
         * Duzeltmesiz guc dusuk cikar; hizala_kesirli(kay) ile duzelir.
         * ⚠ DIZI YOK: ATmega328P'de 2 KB SRAM var, ornekler dongude
         *   yeniden uretiliyor. */
        {
            /* PENCERE TAM SAYI CEVRIM olmali, yoksa ortalama
             * yanliligi tasir ve duzeltmenin kazanci olculemez.
             * 860/50 = 17.2 ornek/cevrim -> 172 ornek = TAM 10
             * cevrim. Ornekler ANALITIK uretildigi icin kenar
             * sorunu YOK: n-1 ve n+2 de hesaplanabiliyor. */
            const uint16_t N = 172u;      /* tam 10 cevrim */
            const float frek = 50.0f, fs = 860.0f;
            const float kay = 0.0817f;          /* I2C kaymasi, ornek */
            const float th = 1.0471976f;        /* 60 derece -> PF = 0.5 */
            const float w = 6.28318531f * frek / fs;
            float p_ham = 0.0f, p_duz = 0.0f;
            uint16_t say = 0;
            for (uint16_t n = 0u; n < N; n++) {
                float vn = sinf(w * (float)n);
                float im1 = sinf(w * ((float)n - 1.0f - kay) - th);
                float i0  = sinf(w * ((float)n - kay) - th);
                float ip1 = sinf(w * ((float)n + 1.0f - kay) - th);
                float ip2 = sinf(w * ((float)n + 2.0f - kay) - th);
                float id = hizala_kesirli(kay, im1, i0, ip1, ip2);
                p_ham += vn * i0;
                p_duz += vn * id;
                say++;
            }
            metin("LK4 ");
            hexf(p_ham / (float)say);
            metin(" ");
            hexf(p_duz / (float)say);
            metin("\r\n");
        }
    }

    /* ═══════════════════════════ B17 — SUZGEC OLCEK DUZELTMESI */
    {
        metin("SZ ");
        hexf(suzgec_ters_kazanc(0.0f, TAU_NORMAL));      /* DC -> 1.0 */
        metin(" ");
        hexf(suzgec_ters_kazanc(50.0f, TAU_NORMAL));
        metin(" ");
        hexf(suzgec_ters_kazanc(50.0f, TAU_YUKSEK));
        metin(" ");
        hexf(suzgec_ters_kazanc(50.0f, TAU_AKIM));
        metin("\r\n");

        /* SZ2: negatif/sifir tau da guvenli olmali (duzeltme yok) */
        metin("SZ2 ");
        hexf(suzgec_ters_kazanc(50.0f, 0.0f));
        metin(" ");
        hexf(suzgec_ters_kazanc(-10.0f, TAU_NORMAL));
        metin("\r\n");

        /* SZ3: kanal yapisinda tau tasiniyor mu */
        {
            Kanal3 n3, y3;
            varsayilan_kanal3(&n3, &y3);
            metin("SZ3 ");
            hexf(n3.tau);
            metin(" ");
            hexf(y3.tau);
            metin("\r\n");
        }
    }

    metin("BITTI\r\n");
    for (;;) {}
    return 0;
}
