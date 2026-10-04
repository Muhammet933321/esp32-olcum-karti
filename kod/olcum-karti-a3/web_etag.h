/* ═══════════════════════════════════════════════════════════════════════
   web_etag.h — ARAYUZ DOSYALARININ ETag'I ve If-None-Match KARARI  (W6)

   Kartin LittleFS'ten sundugu panel dosyalari `Cache-Control: no-cache`
   ile gidiyor (arayuz guncellemesi HEMEN gorulsun). `no-cache` "her
   kullanimda sunucuya SOR" demek — ama ETag olmadan tarayicinin
   soracagi bir sey yok: her acilis ~90 KB'yi (gzip) BASTAN indiriyordu
   (DEVIR 5.12.106, telefonda olculdu). Bu dosya ETag'i ve 304 kararini
   veriyor; govdeyi gondermek hala isleyicinin isi.

   ETAG NEREDEN: `uretim/arayuz-uret.py` goruntuye `etag.txt` kunyesini
   yaziyor — her dosya icin GORUNTUDEKI baytlarin (gzip'liyse gzip'li
   hali) sha256'sinin ilk 16 onaltiligi. Satir bicimi:

       <istek yolu> <16 kucuk onaltilik>\n        ornek: /app.js 0123456789abcdef

   Istek yolu tarayicinin istedigi yol (`/app.js`), goruntudeki dosya
   (`/app.js.gz`) DEGIL. Icerik degisince ozet degisir, degismezse
   (gzip mtime=0) AYNI kalir: kuvvetli ETag.

   🔴 NEDEN KART HESAPLAMIYOR: cekirdegin `enableETag`'i (`calcETag`)
   dosyanin TAMAMINI okuyup MD5 cikariyor — her istekte gondermek kadar
   flas okumasi. Kunye acilista bir kez okunuyor; istek basina maliyet
   ~40 satirlik bir tarama.

   🔴 NEDEN `enableETag(true, fn)` DE DEGIL: cekirdek `header("If-None-
   Match") == etag` diye BIREBIR karsilastiriyor. Kunyede olmayan bir
   dosya icin fn bos dize donerse, If-None-Match GONDERMEYEN her istek
   `"" == ""` ile 304 alir — bos govde, sayfa acilmaz. Ayrica liste
   (`"a", "b"`), `W/` ve `*` bilmiyor ve 304'e Cache-Control/ETag koymuyor.

   NEDEN AYRI VE SAF C: `web_satir.h` gibi platformsuz; `sim3_web.py`
   bunu GERCEK AVR emulatorunde, uretecin GERCEK kunye satirlariyla
   kosturuyor (iki dil, tek bicim).
   ═══════════════════════════════════════════════════════════════════════ */
#ifndef WEB_ETAG_H
#define WEB_ETAG_H

#include <stdint.h>
#include <stddef.h>

#define WEB_ETAG_HEX   16u                    /* kunyedeki ozet uzunlugu */
#define WEB_ETAG_BOY   (WEB_ETAG_HEX + 3u)    /* "\"" + 16 + "\"" + NUL */

static uint8_t etag__hex(char c)
{
    /* YALNIZ kucuk harf: uretec `hexdigest()` yaziyor. Buyuk harf ya da
       baska bir sey = bozuk kunye -> ETag YOK (her zaman 200, guvenli taraf). */
    return (uint8_t)((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'));
}

/* `kunye` NUL-sonlu metinde `yol`un ETag'ini arar. Bulursa `etag`e tirnakli
 * yazar (`"0123456789abcdef"`, WEB_ETAG_BOY bayt) ve 1 doner; yoksa 0.
 * Yol BIREBIR eslesmeli: `/app.js` satiri `/app.js.gz` ya da `/app.j`
 * istegine ETag VERMEZ. Bicimi bozuk satir yok sayilir (ilk gecerli
 * eslesen kazanir). */
static uint8_t etag_bul(const char *kunye, const char *yol, char *etag)
{
    if (!kunye || !yol || !etag || yol[0] != '/') return 0;
    const char *s = kunye;
    while (*s) {
        /* satir: yol */
        const char *y = yol;
        const char *p = s;
        while (*p && *p != ' ' && *p != '\n' && *y && *p == *y) { p++; y++; }
        uint8_t uydu = (*y == 0 && *p == ' ');
        if (uydu) {
            const char *h = p + 1;
            uint8_t i = 0;
            while (i < WEB_ETAG_HEX && etag__hex(h[i])) i++;
            if (i == WEB_ETAG_HEX && (h[i] == '\n' || h[i] == '\r' || h[i] == 0)) {
                etag[0] = '"';
                for (i = 0; i < WEB_ETAG_HEX; i++) etag[1 + i] = h[i];
                etag[1 + WEB_ETAG_HEX] = '"';
                etag[2 + WEB_ETAG_HEX] = 0;
                return 1;
            }
        }
        /* sonraki satira */
        while (*s && *s != '\n') s++;
        if (*s == '\n') s++;
    }
    return 0;
}

/* If-None-Match basligi `etag`i (tirnakli) kapsiyor mu? 1 = 304 gonder.
 * RFC 9110 13.1.2: `*` ya da virgulle ayrilmis varlik etiketleri; ZAYIF
 * karsilastirma (`W/"x"` == `"x"`). Bos/eksik baslik -> 0 (200). Bozuk bir
 * oge listenin geri kalanini OKUMAZ (guvenli taraf: 200). */
static uint8_t etag_eslesir(const char *inm, const char *etag)
{
    if (!inm || !etag || etag[0] != '"') return 0;
    const char *p = inm;
    for (;;) {
        while (*p == ' ' || *p == '\t' || *p == ',') p++;
        if (*p == 0) return 0;
        if (*p == '*') {
            /* `*` yalniz basina tek oge olarak anlamli; ardinda yalniz bosluk */
            const char *q = p + 1;
            while (*q == ' ' || *q == '\t') q++;
            return (uint8_t)(*q == 0);
        }
        if (p[0] == 'W' && p[1] == '/') p += 2;
        if (*p != '"') return 0;
        const char *e = etag;
        const char *q = p;
        while (*q && *e && *q == *e) {
            if (q != p && *q == '"') break;
            q++; e++;
        }
        /* tam eslesme: ikisi de kapanan tirnakta */
        if (q != p && *q == '"' && *e == '"' && e[1] == 0) return 1;
        /* bu ogeyi atla: kapanan tirnaga kadar */
        q = p + 1;
        while (*q && *q != '"') q++;
        if (*q != '"') return 0;
        p = q + 1;
    }
}

#endif
