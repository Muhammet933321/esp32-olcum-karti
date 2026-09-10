/* ═══════════════════════════════════════════════════════════════════════
   web_akis.h — `Serial` AYNASI  (B22.4)

   🔴 COZULEN KUSUR: SSE yalnizca `D` satirini tasiyordu.

   `akis_yolla` tek bir yerden, `loop()`'un rapor blogundan cagriliyordu
   ve oraya yalnizca `son_satir` (yani `D`) geliyordu. `S2` / `M` / ham
   skop verisi / `E` / `T` / `W` / `B` ve butun `*` bilgi, `!` hata
   yanitlari YALNIZCA `Serial.print` ile gidiyordu. Sonuc: WiFi ile
   baglanan bir arayuz SALT-OKUNUR ve SESSIZ olurdu — osiloskop yakalar,
   hicbir sey gormezdi; komut gonderir, yanitini bilemezdi.

   COZUM: `Serial`i bir AYNAYA cevir. Yazilan her bayt hem gercek seri
   porta hem satir tamponuna gidiyor; satir tamamlaninca `web_satir_hazir`
   cagriliyor ve satir SSE istemcilerine yayiliyor.

   NEDEN MAKRO: `.ino` icinde 245 `Serial.` cagrisi var, dort baslik
   dosyasinda ise SIFIR (olculdu). Yani tek bir `#define` butun uretimi
   aynaya aliyor ve cagri yerlerinin HICBIRI degismiyor — degistirseydik
   245 satirlik bir fark cikar ve icinde bir tanesini atlamak kolay
   olurdu (DEVIR 4.15'te `index.html`'in UC dugmesi tam boyle atlanmisti).

   ⚠ `#define Serial CIKIS` BUTUN `#include`'lardan SONRA gelmeli, yoksa
     kutuphane basliklarindaki `Serial` bildirimi de yeniden adlanir.
     Ayrica `CIKIS` nesnesi olusturulurken `Serial` HALA gercek nesneyi
     gostermeli — bu yuzden tanim makrodan ONCE.

   ⚠ `akis_yolla` icinde `Serial` KULLANILAMAZ: sonsuz ozyineleme olurdu.
     (Bugun kullanmiyor; zincir bunu denetliyor.)
   ═══════════════════════════════════════════════════════════════════════ */
#ifndef WEB_AKIS_H
#define WEB_AKIS_H

#include <Arduino.h>
#include "web_satir.h"

/* `.ino` tanimliyor: tamamlanmis bir satiri SSE istemcilerine yayar. */
void web_satir_hazir(const char *satir);

class WebAkis : public Print {
public:
    explicit WebAkis(HardwareSerial &seri) : _s(seri) { satir_sifirla(&_st); }

    /* Seri porta delege edilenler — cagri yerleri degismesin diye. */
    void begin(unsigned long baud) { _s.begin(baud); }
    int available() { return _s.available(); }
    int read() { return _s.read(); }
    void flush() { _s.flush(); }
    operator bool() const { return true; }

    size_t write(uint8_t c) override {
        size_t n = _s.write(c);
        _besle((char)c);
        return n;
    }

    size_t write(const uint8_t *veri, size_t adet) override {
        size_t n = _s.write(veri, adet);
        for (size_t i = 0; i < adet; i++) _besle((char)veri[i]);
        return n;
    }

    uint32_t kirpilan() const { return _st.kirpilan; }
    uint32_t satir_sayisi() const { return _st.satir; }

private:
    void _besle(char c) {
        if (satir_ekle(&_st, c)) web_satir_hazir(_st.tampon);
    }
    HardwareSerial &_s;
    SatirTampon _st;
};

#endif /* WEB_AKIS_H */
