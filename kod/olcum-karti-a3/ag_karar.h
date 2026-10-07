/* ═══════════════════════════════════════════════════════════════════════
   ag_karar.h — AG KIP KARARI (platformsuz)  (AGD, DEVIR 5.12.109)

   🔴 KARTTA BULUNAN KUSUR (2026-10-04): acilista kayitli ev agi (STA) YOKSA
   kart AG_STA_BEKLE_MS sonra kendi AP'sine dusuyor ve STA'yi BIR DAHA
   DENEMIYORDU — ev agi dakikalar sonra donse de. Gercek hayatta: elektrik
   kesintisinden sonra yonlendirici karttan YAVAS acilir -> kart elle
   sifirlanana dek ev aginda degil, bildirim yok (MQTT `durum=2`).
   Calisirken STA kopmasi ise SORUNSUZ (surucu kendisi doner, 4 senaryo
   olculdu, 5 dk kesinti dahil 7-14 s) — BU YOL DEGISMIYOR.

   Karar:
     kayitli ag YOK       -> saf AP (eskisi gibi), deneme yok        AGK_AP
     kayitli ag VAR       -> AG_STA_BEKLE_MS bekle                   AGK_BEKLE
       baglandi           -> STA, bitti                              AGK_STA
       baglanamadi        -> AP kur (AP+STA kipinde), STA'yi
                             AG_STA_YENIDEN_MS'de bir yeniden dene   AGK_AP_DENE
         baglandi         -> kip STA; AP AG_AP_PAY_MS daha acik
                             (AP'deki telefon istek ortasinda
                             kesilmesin), sonra kapanir              AGK_STA_PAY
         pay doldu        -> AP kapat, STA, bitti                    AGK_STA
     AGK_STA'dan sonra KISA kopma -> karar yok: surucu doner (5.12.106, 7-14 s).
     COKLU AG (2026-10-06, CA6): STA'da AG_STA_KOPUK_MS (30 s) kesik -> AP kur + yeniden
       dene (AGK_AP_DENE): kart acikken baska yere tasininca eski agi sonsuza dek beklemez;
       yapistirici her denemede tarayip baska kayitli agi da dener.
       2026-10-07 (kullanici karari; kartta hotspot kapatilinca ev agina ~2:30'da geciyordu,
       90 s + 30 s + baglanma): kesik 90 -> 30 s ve bu yolda ILK deneme HEMEN (AP_KUR'dan
       sonraki adim), sonrakiler yine AG_STA_YENIDEN_MS'de bir (her deneme ~2 s kanal taramasi,
       AP kullanilabilir kalmali). Uygulama: t bir deneme araligi GERIYE alinir ("deneme vadesi
       gelmis"); isaretsiz fark tasmada da dogru. Beklenen: kopma -> ilk deneme ~30 s, tipik
       gecis ~40 s, en kotu ~70 s (ilk taramada gorunmeyen ag bir sonraki denemeye kalir).
       ACILIS (AGK_BEKLE) ve GERI yolunda ilk deneme HEMEN DEGIL, AG_STA_YENIDEN_MS sonra:
       ikisinde de kayitli aglar az once denendi (acilista ag_bekle_tamamla tarayip en iyi
       adayi 10 s denedi; GERI'de hedef + onceki 20'ser s) — hemen bir tarama ayni bilgiyi
       yineler ve TAM AP ayaga kalkarken (telefon baglanmaya calisirken) kanali degistirir.
       Kopma yolunda ise 30 s boyunca surucu yalniz ESKI agi denedi, baska kayitli agi hic
       taramadi: ilk tarama yeni bilgidir.
     GECIS (CA7, `Ng`): yalniz AGK_STA'dan. agk_gecis -> AGK_GECIS (yapistirici yeni aga
       begin); AG_GECIS_MS'de baglanirsa STA, olmazsa AGE_GERI (onceki aga begin) ->
       AGK_GERI; o da AG_GECIS_MS'de olmazsa AP + yeniden deneme. `bagli` GECIS/GERI'de
       yapistiricinin "HEDEF aga bagli" bilgisidir (eski baglanti sayilmaz).

   Iliski kuruldu ama IP yok (DHCP surerken) yeniden denenmez: Arduino
   `STA.connect()` bagliyken once KOPARIR, deneme DHCP'yi keserdi.

   Kod burada, kart yapistiricisi `ag.h`'de; bu dosya AVR'de kosuyor
   (uretim/avr/ornek_ag_karar.c, sim3_web.py 5m). Sureler `ag.h`'de
   tanimli (tek kaynak) — ondan ONCE icerilmezse derlenmez.
   ═══════════════════════════════════════════════════════════════════════ */
#ifndef AG_KARAR_H
#define AG_KARAR_H

#include <stdint.h>

#if !defined(AG_STA_BEKLE_MS) || !defined(AG_STA_YENIDEN_MS) || !defined(AG_AP_PAY_MS)     || !defined(AG_STA_KOPUK_MS) || !defined(AG_GECIS_MS)
#error "ag_karar.h: AG_STA_BEKLE_MS / AG_STA_YENIDEN_MS / AG_AP_PAY_MS / AG_STA_KOPUK_MS / AG_GECIS_MS once tanimlanmali (ag.h)"
#endif

/* evre — 0 = sifir ilklenmis durum (WiFi N0, gorev yok): HIC karar yok */
enum { AGK_YOK = 0, AGK_BEKLE = 1, AGK_AP_DENE = 2, AGK_STA_PAY = 3, AGK_STA = 4, AGK_AP = 5,
       AGK_GECIS = 6, AGK_GERI = 7 };
/* eylem — yapistirici bunu uygular */
enum { AGE_YOK = 0, AGE_AP_KUR = 1, AGE_STA_DENE = 2, AGE_STA_OLDU = 3, AGE_AP_KAPAT = 4,
       AGE_GERI = 5 };

typedef struct {
    uint32_t t;        /* evrenin referans ani (ms): acilis / son deneme / baglanti
                          (CA6 kopma yolunda AP_DENE'ye girerken bir aralik geride: ilk deneme hemen) */
    uint8_t  evre;
} AgKarar;

static void agk_kur(AgKarar *k, uint8_t kimlik_var, uint32_t simdi_ms)
{
    k->evre = kimlik_var ? AGK_BEKLE : AGK_AP;
    k->t = simdi_ms;
}

/* adim gerekiyor mu — degilse yapistirici surucuyu hic sorgulamaz */
static uint8_t agk_etkin(const AgKarar *k)
{
    return k->evre == AGK_BEKLE || k->evre == AGK_AP_DENE || k->evre == AGK_STA_PAY
        || k->evre == AGK_STA || k->evre == AGK_GECIS || k->evre == AGK_GERI;
}

/* CA7: "bu aga gec" — yalniz STA'dayken (AP'deyken yapistirici sonraki denemeyi o aga yonlendirir).
   Donus 1: gecis basladi (yapistirici yeni aga begin etmeli). */
static uint8_t agk_gecis(AgKarar *k, uint32_t simdi_ms)
{
    if (k->evre != AGK_STA) return 0;
    k->evre = AGK_GECIS;
    k->t = simdi_ms;
    return 1;
}

/* bagli: STA'nin IP'si var (WL_CONNECTED). iliskili: STA erisim noktasina iliskili
   (IP'li ya da DHCP bekliyor). Donus: AGE_*. `simdi - t` isaretsiz: millis tasmasi guvenli. */
static uint8_t agk_adim(AgKarar *k, uint32_t simdi_ms, uint8_t bagli, uint8_t iliskili)
{
    const uint32_t gecen = simdi_ms - k->t;
    switch (k->evre) {
    case AGK_BEKLE:
        if (bagli) { k->evre = AGK_STA; k->t = simdi_ms; return AGE_STA_OLDU; }
        if (gecen >= AG_STA_BEKLE_MS) { k->evre = AGK_AP_DENE; k->t = simdi_ms; return AGE_AP_KUR; }
        return AGE_YOK;
    case AGK_AP_DENE:
        if (bagli) { k->evre = AGK_STA_PAY; k->t = simdi_ms; return AGE_STA_OLDU; }
        if (!iliskili && gecen >= AG_STA_YENIDEN_MS) { k->t = simdi_ms; return AGE_STA_DENE; }
        return AGE_YOK;
    case AGK_STA_PAY:
        if (gecen >= AG_AP_PAY_MS) { k->evre = AGK_STA; k->t = simdi_ms; return AGE_AP_KAPAT; }
        return AGE_YOK;
    case AGK_STA:                               /* CA6: t = son BAGLI an */
        if (bagli) { k->t = simdi_ms; return AGE_YOK; }
        /* 2026-10-07: t bir aralik geride -> sonraki adimda ilk deneme (yukaridaki not) */
        if (gecen >= AG_STA_KOPUK_MS) { k->evre = AGK_AP_DENE; k->t = simdi_ms - AG_STA_YENIDEN_MS; return AGE_AP_KUR; }
        return AGE_YOK;
    case AGK_GECIS:                             /* CA7: hedef aga AG_GECIS_MS */
        if (bagli) { k->evre = AGK_STA; k->t = simdi_ms; return AGE_STA_OLDU; }
        if (gecen >= AG_GECIS_MS) { k->evre = AGK_GERI; k->t = simdi_ms; return AGE_GERI; }
        return AGE_YOK;
    case AGK_GERI:                              /* onceki aga AG_GECIS_MS; olmazsa AP + deneme */
        if (bagli) { k->evre = AGK_STA; k->t = simdi_ms; return AGE_STA_OLDU; }
        if (gecen >= AG_GECIS_MS) { k->evre = AGK_AP_DENE; k->t = simdi_ms; return AGE_AP_KUR; }
        return AGE_YOK;
    default:
        return AGE_YOK;
    }
}

#endif /* AG_KARAR_H */
