<script setup>
// Ayarlar (A42'nin 5C kadari): Kart (adres, kimlik, eslesme; Baglan / Esles / Eslesmeyi kaldir) ve
// Gelismis (Karti bul, PBKDF2 olcumu, WebView ag sinamasi). Eslestirme ekrani bu rotanin ICINDE
// acilir: ACIL DURDUR seridi ve sekmeler o sirada da yerinde kalir.
import { ref } from "vue";
import Baglanti from "./Baglanti.vue";
import BildirimAyar from "./BildirimAyar.vue";
import EsitlemeAyar from "./EsitlemeAyar.vue";
import GrafikOlcum from "./GrafikOlcum.vue";
import KartBul from "./KartBul.vue";
import { c, dil, tema, tercihSec } from "./metin.js";
import { DILLER, TEMALAR } from "./tercih.js";

const gelismis = ref(false);
const DIL_ADI = { tr: "m.ay.dil_tr", en: "m.ay.dil_en" };
const TEMA_ADI = { sistem: "m.ay.tema_sistem", koyu: "m.ay.tema_koyu", acik: "m.ay.tema_acik" };
</script>

<template>
  <div class="ekran">
    <h2 class="bolum-baslik">{{ c("m.ay.kart") }}</h2>
    <section id="ay-kart" class="kart"><Baglanti /></section>

    <h2 class="bolum-baslik">{{ c("m.ay.esitleme") }}</h2>
    <section id="ay-esitleme" class="kart"><EsitlemeAyar /></section>

    <h2 class="bolum-baslik">{{ c("m.ay.bildirim") }}</h2>
    <section id="ay-bildirim" class="kart"><BildirimAyar /></section>

    <h2 class="bolum-baslik">{{ c("m.ay.gorunum") }}</h2>
    <section id="ay-gorunum" class="kart">
      <span class="et alan-et">{{ c("m.ay.dil") }}</span>
      <div id="ay-dil" class="secim" role="radiogroup" :aria-label="c('m.ay.dil')">
        <button v-for="d in DILLER" :key="d" type="button" role="radio" :aria-checked="dil === d" @click="tercihSec({ dil: d })">{{ c(DIL_ADI[d]) }}</button>
      </div>
      <span class="et alan-et">{{ c("m.ay.tema") }}</span>
      <div id="ay-tema" class="secim" role="radiogroup" :aria-label="c('m.ay.tema')">
        <button v-for="t in TEMALAR" :key="t" type="button" role="radio" :aria-checked="tema === t" @click="tercihSec({ tema: t })">{{ c(TEMA_ADI[t]) }}</button>
      </div>
    </section>

    <h2 class="bolum-baslik">{{ c("m.ay.gelismis") }}</h2>
    <button id="ay-gelismis" type="button" class="dugme" :aria-expanded="gelismis" aria-controls="ay-gelismis-icerik" @click="gelismis = !gelismis">
      {{ gelismis ? c("m.ay.gelismis_gizle") : c("m.ay.gelismis_goster") }}
    </button>
    <section v-if="gelismis" id="ay-gelismis-icerik" class="kart"><KartBul /></section>
    <section v-if="gelismis" id="ay-grafik-olcum" class="kart"><GrafikOlcum /></section>
  </div>
</template>
