/* Python tarafindan uretildi — sim2_kart.py */
#ifndef VEKTOR_H
#define VEKTOR_H
#include <stdint.h>
typedef struct {
    int16_t ham_v;
    int16_t ham_i;
    int16_t i_ofset;
    float   sont;
    float   v_pga;
    float   i_pga;
    uint32_t dt_us;
} Vektor;

#define VEKTOR_ADET 5
static const Vektor VEKTOR[VEKTOR_ADET] = {
    { 3362, 1280, 0, 1.000000f, 2.048000f, 0.256000f, 1163u },
    { 5094, 6398, 0, 1.000000f, 2.048000f, 0.256000f, 1163u },
    { 12225, 12796, 0, 1.000000f, 2.048000f, 0.256000f, 1163u },
    { 24449, 25593, 0, 1.000000f, 2.048000f, 0.256000f, 1163u },
    { 30562, 31991, 0, 1.000000f, 2.048000f, 0.256000f, 1163u },
};

/* Arayuz testi icin sabit calisma noktasi (12.00 V / 100.0 mA) */
#define SABIT_HAM_V 12225
#define SABIT_HAM_I 12796
#define SABIT_SONT  1.000000f
#define SABIT_V_PGA 2.048000f
#define SABIT_I_PGA 0.256000f
#endif
