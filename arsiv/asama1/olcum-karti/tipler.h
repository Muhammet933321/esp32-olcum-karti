/*
 * Ölçüm Kartı — veri tipleri
 *
 * NEDEN AYRI DOSYA: Arduino derleyicisi .ino dosyasının başına otomatik
 * fonksiyon prototipleri ekler. `Okuma olc()` gibi kendi tipini döndüren bir
 * fonksiyonun prototipi, struct tanımından ÖNCE yerleştirildiği için
 * "'Okuma' does not name a type" hatası verir. Tipler bir başlık dosyasında
 * olunca prototiplerden önce görülüyor ve sorun kalkıyor.
 */

#ifndef OLCUM_KARTI_TIPLER_H
#define OLCUM_KARTI_TIPLER_H

#include <stdint.h>

// EEPROM'da saklanan kalibrasyon ayarları
struct Ayar {
  uint16_t imza;
  float    sont_ohm;      // takılı şöntün değeri (ohm)
  float    v_duzeltme;    // gerilim kanalı kalibrasyon çarpanı
  float    i_duzeltme;    // akım kanalı kalibrasyon çarpanı
  int16_t  i_ofset;       // akım kanalı ham ADC sıfır noktası
};

// Tek bir ölçüm anı
struct Okuma {
  float volt;
  float amper;
  float watt;
};

#endif
