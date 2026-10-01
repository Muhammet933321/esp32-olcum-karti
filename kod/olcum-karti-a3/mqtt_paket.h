/* mqtt_paket.h — 1E: MQTT 3.1.1 ISTEMCI paketleri (platformsuz).
 *
 * Kart yalniz YAYINLAR (abone olmaz): CONNECT (vasiyetli), PUBLISH (QoS 0/1),
 * PINGREQ, DISCONNECT uretir; CONNACK, PUBACK, PINGRESP okur. Gelen her paket
 * parca parca (TLS kayitlari keyfi bolunur) bayt bayt cozulur; bilinmeyen ya da
 * buyuk govdeler atlanir (ilk MQP_GOVDE_AZAMI bayti saklanir).
 *
 * Neden esp-mqtt degil: Arduino-ESP32 3.3.11'deki esp-mqtt gorevi cekirdege
 * SABITLENMIYOR (CONFIG_MQTT_TASK_CORE_SELECTION_ENABLED kapali, oncelik >= 1):
 * TLS el sikismasi cekirdek 1'e kayip olcum dongusunu bloklayabilir. Bu
 * paketleri cekirdek 0'a sabitli kendi gorevimiz esp-tls uzerinden yollar.
 * Tasarim: tasarim/2026-10-01-1e-mqtt-bildirim.md (K1, kart tezgahi notu).
 * AVR'de sinaniyor: test_kayit.py B71.MQ* (SENARYO_MQTT); PC tarafi
 * kopru/mqtt_istemci.py sahte araci ayni baytlari cozer (B72.Q*). */
#ifndef MQTT_PAKET_H
#define MQTT_PAKET_H

#include <stdint.h>
#include <string.h>

#ifndef MQP_ISLEV
#define MQP_ISLEV static inline
#endif
#ifndef MQP_GOVDE_AZAMI
#define MQP_GOVDE_AZAMI 8u        /* CONNACK/PUBACK/SUBACK icin yeter */
#endif

#define MQP_CONNECT    1u
#define MQP_CONNACK    2u
#define MQP_PUBLISH    3u
#define MQP_PUBACK     4u
#define MQP_SUBACK     9u
#define MQP_PINGREQ   12u
#define MQP_PINGRESP  13u
#define MQP_DISCONNECT 14u

#define MQP_E_YER    (-1)         /* cikti tamponu yetmiyor */
#define MQP_E_UZUN   (-2)         /* alan 65535'ten uzun */
#define MQP_E_KONU   (-3)         /* yayin/vasiyet konusu bos ya da + / # iceriyor */
#define MQP_E_BOZUK  (-4)         /* gelen paket MQTT degil (kalan uzunluk 4 bayti asti) */
#define MQP_E_ALAN   (-5)         /* parola kullanicisiz / QoS > 1 / vasiyet tutarsiz /
                                     bos istemci kimligi + temiz oturum degil */

typedef struct {
    const char    *istemci;        /* client id (bos olabilir: temiz oturumda araci uretir) */
    const char    *kullanici;      /* NULL ya da "" = yok */
    const char    *parola;         /* NULL = yok; kullanicisiz parola 3.1.1'de YASAK */
    const char    *vasiyet_konu;   /* NULL = vasiyet yok */
    const uint8_t *vasiyet;
    uint16_t       vasiyet_n;
    uint8_t        vasiyet_qos;    /* 0 / 1 */
    uint8_t        vasiyet_tut;    /* retain */
    uint16_t       keepalive;      /* s */
    uint8_t        temiz;          /* clean session */
} MqpBaglan;

typedef struct {
    uint8_t  asama;                /* 0 baslik, 1 kalan uzunluk, 2 govde */
    uint8_t  bas;                  /* sabit baslik bayti */
    uint8_t  u_bayt;               /* kalan uzunlugun okunan bayt sayisi */
    uint32_t carpan;
    uint32_t uzunluk;              /* kalan uzunluk (govde) */
    uint32_t alinan;               /* govdeden okunan */
    uint8_t  govde[MQP_GOVDE_AZAMI];
} MqpOkuyucu;

/* ─────────────────────────────── yazma */
MQP_ISLEV uint8_t mqp__uzunluk_boy(uint32_t n)
{
    return (uint8_t)(n < 128u ? 1u : n < 16384u ? 2u : n < 2097152u ? 3u : 4u);
}

MQP_ISLEV uint8_t mqp__uzunluk_yaz(uint32_t n, uint8_t *c)
{
    uint8_t i = 0;
    do {
        uint8_t b = (uint8_t)(n & 0x7Fu);
        n >>= 7;
        if (n) b |= 0x80u;
        c[i++] = b;
    } while (n);
    return i;
}

MQP_ISLEV uint16_t mqp__metin_boy(const char *s)
{
    size_t n = s ? strlen(s) : 0u;
    return (uint16_t)(n > 65535u ? 65535u : n);
}

/* 2 bayt uzunluk + bayt; `c` NULL degil, yer onceden denetlendi */
MQP_ISLEV uint32_t mqp__alan(uint8_t *c, const uint8_t *v, uint16_t n)
{
    c[0] = (uint8_t)(n >> 8);
    c[1] = (uint8_t)n;
    if (n) memcpy(c + 2, v, n);
    return 2u + n;
}

MQP_ISLEV int mqp__uzun_mu(const char *s)
{
    return s && strlen(s) > 65535u;
}

/* Donus: paket uzunlugu ya da MQP_E_*. */
MQP_ISLEV int32_t mqp_baglan(const MqpBaglan *b, uint8_t *c, uint16_t azami)
{
    const uint8_t kul = (uint8_t)(b->kullanici && b->kullanici[0]);
    const uint8_t par = (uint8_t)(b->parola != 0);
    const uint8_t vas = (uint8_t)(b->vasiyet_konu != 0);
    uint32_t kalan, o;
    uint8_t bayrak = 0;
    if (par && !kul) return MQP_E_ALAN;
    if (b->vasiyet_qos > 1u) return MQP_E_ALAN;
    if (!vas && (b->vasiyet_qos || b->vasiyet_tut || b->vasiyet_n)) return MQP_E_ALAN;
    if (mqp__uzun_mu(b->istemci) || mqp__uzun_mu(b->kullanici) || mqp__uzun_mu(b->parola)
        || mqp__uzun_mu(b->vasiyet_konu)) return MQP_E_UZUN;
    if (vas) {                      /* vasiyet konusu da KONU ADI: bos degil, joker yok (4.7.1) */
        const char *p = b->vasiyet_konu;
        if (!*p) return MQP_E_KONU;
        for (; *p; p++)
            if (*p == '+' || *p == '#') return MQP_E_KONU;
    }
    if (!mqp__metin_boy(b->istemci) && !b->temiz) return MQP_E_ALAN;   /* MQTT-3.1.3-7 */
    kalan = 10u + 2u + mqp__metin_boy(b->istemci);
    if (vas) kalan += 2u + mqp__metin_boy(b->vasiyet_konu) + 2u + b->vasiyet_n;
    if (kul) kalan += 2u + mqp__metin_boy(b->kullanici);
    if (par) kalan += 2u + mqp__metin_boy(b->parola);
    if (1u + mqp__uzunluk_boy(kalan) + kalan > azami) return MQP_E_YER;
    c[0] = (uint8_t)(MQP_CONNECT << 4);
    o = 1u + mqp__uzunluk_yaz(kalan, c + 1);
    o += mqp__alan(c + o, (const uint8_t *)"MQTT", 4u);
    c[o++] = 4u;                                   /* 3.1.1 */
    if (kul) bayrak |= 0x80u;
    if (par) bayrak |= 0x40u;
    if (vas) bayrak = (uint8_t)(bayrak | 0x04u | (b->vasiyet_qos << 3) | (b->vasiyet_tut ? 0x20u : 0u));
    if (b->temiz) bayrak |= 0x02u;
    c[o++] = bayrak;
    c[o++] = (uint8_t)(b->keepalive >> 8);
    c[o++] = (uint8_t)b->keepalive;
    o += mqp__alan(c + o, (const uint8_t *)(b->istemci ? b->istemci : ""), mqp__metin_boy(b->istemci));
    if (vas) {
        o += mqp__alan(c + o, (const uint8_t *)b->vasiyet_konu, mqp__metin_boy(b->vasiyet_konu));
        o += mqp__alan(c + o, b->vasiyet, b->vasiyet_n);
    }
    if (kul) o += mqp__alan(c + o, (const uint8_t *)b->kullanici, mqp__metin_boy(b->kullanici));
    if (par) o += mqp__alan(c + o, (const uint8_t *)b->parola, mqp__metin_boy(b->parola));
    return (int32_t)o;
}

/* QoS 0'da pid yazilmaz (yok sayilir); QoS 1'de pid 0 olamaz. */
MQP_ISLEV int32_t mqp_yayin(const char *konu, const uint8_t *yuk, uint16_t n, uint8_t qos,
                            uint8_t tut, uint16_t pid, uint8_t *c, uint16_t azami)
{
    const char *p;
    uint32_t kalan, o;
    if (qos > 1u || (qos && !pid)) return MQP_E_ALAN;
    if (!konu || !konu[0]) return MQP_E_KONU;
    if (mqp__uzun_mu(konu)) return MQP_E_UZUN;
    for (p = konu; *p; p++)
        if (*p == '+' || *p == '#') return MQP_E_KONU;
    kalan = 2u + mqp__metin_boy(konu) + (qos ? 2u : 0u) + n;
    if (1u + mqp__uzunluk_boy(kalan) + kalan > azami) return MQP_E_YER;
    c[0] = (uint8_t)((MQP_PUBLISH << 4) | (qos << 1) | (tut ? 1u : 0u));
    o = 1u + mqp__uzunluk_yaz(kalan, c + 1);
    o += mqp__alan(c + o, (const uint8_t *)konu, mqp__metin_boy(konu));
    if (qos) {
        c[o++] = (uint8_t)(pid >> 8);
        c[o++] = (uint8_t)pid;
    }
    if (n) memcpy(c + o, yuk, n);
    return (int32_t)(o + n);
}

MQP_ISLEV int32_t mqp__iki(uint8_t tip, uint8_t *c, uint16_t azami)
{
    if (azami < 2u) return MQP_E_YER;
    c[0] = (uint8_t)(tip << 4);
    c[1] = 0u;
    return 2;
}

MQP_ISLEV int32_t mqp_ping(uint8_t *c, uint16_t azami) { return mqp__iki(MQP_PINGREQ, c, azami); }
MQP_ISLEV int32_t mqp_kopar(uint8_t *c, uint16_t azami) { return mqp__iki(MQP_DISCONNECT, c, azami); }

/* ─────────────────────────────── okuma */
MQP_ISLEV void mqp_oku_kur(MqpOkuyucu *o)
{
    memset(o, 0, sizeof(*o));
}

/* `v`'den bayt tuketir; bir paket TAMAMLANINCA durur (1 doner, *kullanilan
   tuketilen bayt). 0: daha bayt lazim (hepsi tuketildi). MQP_E_BOZUK: akis
   bozuk — baglanti kapatilmali (okuyucu yeniden kurulmadan kullanilmaz). */
MQP_ISLEV int mqp_oku(MqpOkuyucu *o, const uint8_t *v, uint16_t n, uint16_t *kullanilan)
{
    uint16_t i = 0;
    while (i < n) {
        const uint8_t b = v[i++];
        if (o->asama == 0u) {
            o->bas = b;
            o->asama = 1u;
            o->u_bayt = 0u;
            o->carpan = 1u;
            o->uzunluk = 0u;
            o->alinan = 0u;
        } else if (o->asama == 1u) {
            o->uzunluk += (uint32_t)(b & 0x7Fu) * o->carpan;
            o->carpan <<= 7;
            o->u_bayt++;
            if (b & 0x80u) {
                if (o->u_bayt >= 4u) { o->asama = 3u; *kullanilan = i; return MQP_E_BOZUK; }
                continue;
            }
            if (!o->uzunluk) { o->asama = 0u; *kullanilan = i; return 1; }
            o->asama = 2u;
        } else if (o->asama == 2u) {
            if (o->alinan < MQP_GOVDE_AZAMI) o->govde[o->alinan] = b;
            o->alinan++;
            if (o->alinan == o->uzunluk) { o->asama = 0u; *kullanilan = i; return 1; }
        } else {
            *kullanilan = i;
            return MQP_E_BOZUK;
        }
    }
    *kullanilan = i;
    return 0;
}

MQP_ISLEV uint8_t mqp_tip(const MqpOkuyucu *o) { return (uint8_t)(o->bas >> 4); }

/* CONNACK donus kodu (0 = kabul, 5 = yetkisiz...) ya da -1 (CONNACK degil / bozuk) */
MQP_ISLEV int mqp_connack(const MqpOkuyucu *o)
{
    if (mqp_tip(o) != MQP_CONNACK || o->uzunluk != 2u) return -1;
    return o->govde[1];
}

/* ─────────────────────────────── adres */
/* "mqtts://ad[:port]" (TLS, varsayilan 8883) ya da "mqtt://ad[:port]" (sifresiz,
   1883 — yalniz yerel sinama; yuk yine uctan uca sifreli, ama ARACI PAROLASI acik
   gider). Ad: harf, rakam, '.', '-'. Kullanici bilgisi ('@'), yol, sorgu, bos ad,
   port 0 ya da > 65535 REDDEDILIR. 0 ya da MQP_E_ALAN. */
MQP_ISLEV int mqp_uri_coz(const char *uri, char *ad, uint8_t ad_azami, uint16_t *port,
                          uint8_t *tls)
{
    const char *p;
    uint8_t n = 0;
    uint32_t pt = 0;
    if (!uri || ad_azami < 2u) return MQP_E_ALAN;
    if (!strncmp(uri, "mqtts://", 8)) { *tls = 1u; *port = 8883u; p = uri + 8; }
    else if (!strncmp(uri, "mqtt://", 7)) { *tls = 0u; *port = 1883u; p = uri + 7; }
    else return MQP_E_ALAN;
    for (; *p && *p != ':'; p++) {
        const char c = *p;
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
              || c == '.' || c == '-')) return MQP_E_ALAN;
        if (n + 1u >= ad_azami) return MQP_E_ALAN;
        ad[n++] = c;
    }
    ad[n] = 0;
    if (!n) return MQP_E_ALAN;
    if (*p == ':') {
        p++;
        if (!*p) return MQP_E_ALAN;
        for (; *p; p++) {
            if (*p < '0' || *p > '9') return MQP_E_ALAN;
            pt = pt * 10u + (uint32_t)(*p - '0');
            if (pt > 65535u) return MQP_E_ALAN;
        }
        if (!pt) return MQP_E_ALAN;
        *port = (uint16_t)pt;
    }
    return 0;
}

/* PUBACK paket kimligi ya da -1 */
MQP_ISLEV int32_t mqp_puback_pid(const MqpOkuyucu *o)
{
    if (mqp_tip(o) != MQP_PUBACK || o->uzunluk != 2u) return -1;
    return (int32_t)(((uint16_t)o->govde[0] << 8) | o->govde[1]);
}

#endif /* MQTT_PAKET_H */
