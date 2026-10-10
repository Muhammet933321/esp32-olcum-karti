// SINYAL KAYNAGI (Arduino Uno / Nano, ATmega328P 16 MHz) — olcum kartinin osiloskobunu sinamak icin.
// D9 pininde kare dalga: Timer1, hizli PWM (kip 14, tavan ICR1). Frekans ve doluluk kuvars/rezonatore bagli,
// yazilim zamanlamasina degil. Seri 115200:  f<Hz>  (1..20000)   d<yuzde>  (1..99)   ?  (durum)
// Baglanti: D9 (ya da D13) -> SKOP, GND -> COM. Cikis 0..5 V, kaynak direnci ~25 ohm.
// D9 donanim cikisi (titresimsiz). D13 ayni sinyalin kesmeyle kopyasi: tasma kesmesinde 1, karsilastirma
// kesmesinde 0 — kenarlar birkac mikrosaniye oynayabilir, ortalama frekans ve doluluk ayni.

const uint8_t PIN = 9;
static uint32_t hz = 1000;
static uint8_t duty = 50;

static void durum(uint32_t tavan, uint16_t bolucu, uint16_t ocr) {
  Serial.print(F("F "));
  Serial.print((float)F_CPU / ((float)bolucu * (float)tavan), 3);
  Serial.print(F(" Hz  D "));
  Serial.print(100.0f * (float)(ocr + 1u) / (float)tavan, 2);
  Serial.print(F(" %  tavan "));
  Serial.print(tavan);
  Serial.print(F("  bolucu "));
  Serial.println(bolucu);
}

static void kur() {
  static const uint16_t bolucu[5] = {1, 8, 64, 256, 1024};
  for (uint8_t i = 0; i < 5; i++) {
    const uint32_t tavan = (F_CPU / bolucu[i] + hz / 2u) / hz;   // bir periyottaki sayim (yuvarlanmis)
    if (tavan < 4u || tavan > 65536UL) continue;
    uint32_t yuksek = (tavan * duty + 50u) / 100u;
    if (yuksek < 1u) yuksek = 1u;
    if (yuksek >= tavan) yuksek = tavan - 1u;
    noInterrupts();
    TCCR1A = _BV(COM1A1) | _BV(WGM11);
    TCCR1B = _BV(WGM13) | _BV(WGM12) | (uint8_t)(i + 1u);
    ICR1 = (uint16_t)(tavan - 1u);
    OCR1A = (uint16_t)(yuksek - 1u);
    TCNT1 = 0;
    TIMSK1 = _BV(TOIE1) | _BV(OCIE1A);   // D13 kopyasi
    interrupts();
    durum(tavan, bolucu[i], (uint16_t)(yuksek - 1u));
    return;
  }
  Serial.println(F("! frekans aralik disi"));
}

ISR(TIMER1_OVF_vect)   { PORTB |= _BV(PB5); }    // D13 = PB5: periyot basi -> 1
ISR(TIMER1_COMPA_vect) { PORTB &= (uint8_t)~_BV(PB5); }   // doluluk bitti -> 0

void setup() {
  pinMode(PIN, OUTPUT);
  pinMode(13, OUTPUT);
  Serial.begin(115200);
  Serial.println(F("SINYAL KAYNAGI D9 + D13 — f<Hz> d<yuzde> ?"));
  kur();
}

void loop() {
  static char s[16];
  static uint8_t n = 0;
  while (Serial.available()) {
    const char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      s[n] = 0;
      if (n) {
        const long v = atol(s + 1);
        if (s[0] == 'f' && v >= 1 && v <= 20000) { hz = (uint32_t)v; kur(); }
        else if (s[0] == 'd' && v >= 1 && v <= 99) { duty = (uint8_t)v; kur(); }
        else if (s[0] == '?') kur();
        else Serial.println(F("! f<1..20000> d<1..99> ?"));
      }
      n = 0;
    } else if (n < sizeof(s) - 1u) {
      s[n++] = c;
    }
  }
}
