<script setup>
// Ayarlar (A42'nin 5C kadari): Kart (adres, kimlik, eslesme; Baglan / Esles / Eslesmeyi kaldir) ve
// Gelismis (Karti bul, PBKDF2 olcumu, WebView ag sinamasi). Eslestirme ekrani bu rotanin ICINDE
// acilir: ACIL DURDUR seridi ve sekmeler o sirada da yerinde kalir.
import { ref } from "vue";
import Baglanti from "./Baglanti.vue";
import KartBul from "./KartBul.vue";
import { c } from "./metin.js";

const gelismis = ref(false);
</script>

<template>
  <div class="ekran">
    <h2 class="bolum-baslik">{{ c("m.ay.kart") }}</h2>
    <section id="ay-kart" class="kart"><Baglanti /></section>

    <h2 class="bolum-baslik">{{ c("m.ay.gelismis") }}</h2>
    <button id="ay-gelismis" type="button" class="dugme" :aria-expanded="gelismis" aria-controls="ay-gelismis-icerik" @click="gelismis = !gelismis">
      {{ gelismis ? c("m.ay.gelismis_gizle") : c("m.ay.gelismis_goster") }}
    </button>
    <section v-if="gelismis" id="ay-gelismis-icerik" class="kart"><KartBul /></section>
  </div>
</template>
