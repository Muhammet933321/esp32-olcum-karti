/* ═══════════════════════════════════════════════════════════════════════
   HT5 — HAT DIRENCI DUZELTICISI                              (ekran/pil_hat.js)

   tasarim/2026-10-07-pil-iyilestirme.md HT1–HT5. Pil sekmesinin "Test parametreleri"
   kartinda ozet ("Hat direnci: n mΩ", ekran/pil.js PilPt kip 'hat') hep durur; bu
   bilesen kullanici "Ayarla…"ya basinca DINAMIK iner (acilis, #/pil acilisi ve KU1
   butceleri degismez). Iki yol:
     * elle `Ph<n>` (0…1000 mΩ, kartin pil_ph_ayir kurali; gecersiz giris GITMEZ),
     * "Multimetreyle duzelt": yalniz test surerken ve I >= 0.1 A — kullanici pil
       kutuplarinda olctugu gerilimi yazar; R_yeni = R_eski + (V_mm − V_gosterilen) / I
       (V_gosterilen = V kartindaki duzeltilmis deger), 0…1000'e kirpilir, TEK onaydan
       sonra gider.
   Gonderim app.js pilAyarGonder ($root) ile; kartin onayi / reddi / sessizligi sonuc
   satirinda. Metin + hesap + akis ortak/sozluk_hat.js'te (B7 ve node'da sinanir).
   ═══════════════════════════════════════════════════════════════════════ */

import { hatGorunum, hatIslem } from '/ortak/sozluk_hat.js';

const SABLON = `
<div class="pil-hat" data-pil="hat-duzeltici">
  <div class="alan"><label for="pil-hat">{{ g.giris }}</label>
    <input id="pil-hat" type="text" inputmode="numeric" v-model="hatGiris" autocomplete="off" data-pil="hat-giris"
           @keydown.enter.prevent="ht('yaz')"></div>
  <button type="button" :disabled="g.mesgul" @click="ht('yaz')" data-pil="hat-yaz">{{ g.yaz }}</button>
  <div class="alan"><label for="pil-mm">{{ g.mm }}</label>
    <input id="pil-mm" type="text" inputmode="decimal" v-model="mmGiris" :disabled="!g.mmAcik" autocomplete="off" data-pil="hat-mm"
           @keydown.enter.prevent="ht('oner')"></div>
  <button type="button" :disabled="!g.mmAcik || g.mesgul" @click="ht('oner')" data-pil="hat-duzelt">{{ g.duzelt }}</button>
  <p class="ipucu" data-pil="hat-mm-ipucu">{{ g.mmIpucu }}</p>
  <template v-if="g.oneri">
    <p class="uyari" data-pil="hat-oneri">{{ g.oneri }}</p>
    <div class="satir">
      <button type="button" class="birincil" :disabled="g.mesgul" @click="ht('gonder')" data-pil="hat-gonder">{{ g.gonder }}</button>
      <button type="button" @click="ht('vazgec')" data-pil="hat-vazgec">{{ g.vazgec }}</button>
    </div>
  </template>
  <p v-if="g.sonuc" :class="g.sonucHata ? 'uyari' : 'ipucu'" role="status" data-pil="hat-sonuc">{{ g.sonuc }}</p>
  <p class="ipucu">{{ g.ipucu }}</p>
</div>`;

export const PilHat = {
  name: 'PilHat',
  props: { r: Number },          // kartin su anki hat direnci (mΩ, /pil hat_mohm)
  template: SABLON,
  data() { return { hatGiris: '', mmGiris: '', oneri: null, mesgul: false, sonuc: null }; },
  computed: {
    g() { return hatGorunum(this.$root, this.$data); },
  },
  methods: {
    ht(a) { return hatIslem(this.$root, this.$data, a, this.r); },
  },
};
