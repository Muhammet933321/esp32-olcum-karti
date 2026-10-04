<script setup>
// ACIL DURDUR seridi (A8–A11). Kabukta (App.vue) TEK yerde, sekmelerin hemen ustunde durur.
// Dokunus isleyicisi DOGRUDAN acilDurdur'dur: onay yok, bekleme yok, yonlendirme yok, kart nesnesi
// beklenmez. Sonuc seridin icinde: gonderiliyor / durduruldu (birkac saniye) / ULASILAMADI (kalici).
// Dugme hicbir halde kapanmaz — her zaman yeniden basilabilir.
import { computed, onBeforeUnmount, ref } from "vue";
import Ikon from "./Ikon.vue";
import { seritGorunumu, seritSuresi } from "./durdur_gorunum.js";
import { acilDurdur, durdurDinle, durdurDurumu } from "../cekirdek/uygulama.js";
import { c } from "../ekran/metin.js";

const hal = ref(durdurDurumu());
const gorunum = computed(() => seritGorunumu(hal.value));
let silme = 0;

const birak = durdurDinle((yeni) => {
  clearTimeout(silme);
  hal.value = yeni;
  const sure = seritSuresi(yeni);
  if (sure > 0) silme = setTimeout(() => { if (hal.value === yeni) hal.value = "bos"; }, sure);
});
onBeforeUnmount(() => { clearTimeout(silme); birak(); });
</script>

<template>
  <div id="durdur-seridi" class="serit">
    <button id="durdur" type="button" class="durdur" :aria-label="c('m.dd.etiket')" @click="acilDurdur">
      <Ikon ad="dur" /><span>{{ c("m.dd.dugme") }}</span>
    </button>
    <p v-if="gorunum.anahtar" id="durdur-durum" class="serit-durum" :class="gorunum.sinif" :role="gorunum.rol" aria-live="assertive">
      <Ikon v-if="gorunum.ikon" :ad="gorunum.ikon" /><span>{{ c(gorunum.anahtar) }}</span>
    </p>
  </div>
</template>
