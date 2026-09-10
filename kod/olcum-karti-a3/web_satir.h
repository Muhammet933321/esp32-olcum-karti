/* ═══════════════════════════════════════════════════════════════════════
   web_satir.h — SATIR TAMPONU  (B22.4)

   Karta yazilan bayt akisini SATIRLARA boler. `Serial` aynasi bunu
   kullaniyor: her tamamlanan satir hem seri porta hem SSE istemcilerine
   gidiyor.

   NEDEN AYRI VE SAF C: `olcum3.h` ve `pil_test.h` gibi platform bagimsiz
   yazildi, boylece `test_olcum3.py` bunu GERCEK AVR emulatorunde
   kosturabiliyor. Sinir kosullari (tam dolu tampon, CRLF, bos satir,
   tasma) donanim olmadan sinanabiliyor — B22.4'un sinanabilen tek
   parcasi bu.

   🔴 NEDEN HALKA TAMPON DEGIL: plan "halka tampon + tasma sayaci"
   diyordu. Satir tamponu SECILDI cunku tuketici (akis_yolla) YAZMA
   ANINDA cagriliyor; arada biriktirilecek bir sey yok. Halka tampon
   ikinci bir kuyruk ve ikinci bir "ne zaman bosaltilir" sorusu getirirdi.
   Tasma sayaci KORUNDU: bir satir sinira sigmazsa kirpiliyor ve KAC BAYT
   atildigi sayiliyor — sessiz kirpma yasak.

   Azami satir uzunlugu: en uzun gercek satir `M f=… n=…` (~160 B).
   224 pay birakiyor; asilirsa kirpiliyor ama satir YINE DE tamamlaniyor,
   yani ayristirici hizasini kaybetmiyor.
   ═══════════════════════════════════════════════════════════════════════ */
#ifndef WEB_SATIR_H
#define WEB_SATIR_H

#include <stdint.h>

#define WEB_SATIR_AZAMI 224u

typedef struct {
    char     tampon[WEB_SATIR_AZAMI];
    uint16_t n;
    uint32_t kirpilan;      /* sinira sigmayip ATILAN bayt sayisi */
    uint32_t satir;         /* tamamlanan satir sayisi */
} SatirTampon;

static void satir_sifirla(SatirTampon *s)
{
    s->n = 0;
    s->kirpilan = 0;
    s->satir = 0;
    s->tampon[0] = 0;
}

/* Bir bayt ekler.
 * Donus 1 ise SATIR HAZIR: `s->tampon` NUL-sonlu ve okunabilir.
 * Donus 0 ise satir henuz tamamlanmadi (ya da BOS satir atlandi).
 *
 * `\r` yok sayiliyor: firmware `println` ile CRLF yaziyor, ayristirici
 * ise satiri zaten trim ediyor. Bos satir SSE'ye gonderilmiyor — protokol
 * icerigi tasimiyor ve her `Serial.println()` bir bos olay uretirdi.
 */
static uint8_t satir_ekle(SatirTampon *s, char c)
{
    if (c == '\r') return 0;
    if (c == '\n') {
        if (s->n == 0) return 0;              /* bos satir — atla */
        s->tampon[s->n] = 0;
        s->n = 0;
        s->satir++;
        return 1;
    }
    if (s->n < WEB_SATIR_AZAMI - 1u) {
        s->tampon[s->n++] = c;
    } else {
        s->kirpilan++;                        /* sessiz kirpma YASAK */
    }
    return 0;
}

#endif /* WEB_SATIR_H */
