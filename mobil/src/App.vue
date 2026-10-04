<script setup>
// 5B: kabuk henuz yok (sekmeler ve DURDUR dugmesi 5C'de). Iki gecici ekran: Baglanti (eslestirme +
// imzali istek) ve Karti bul (kesif + WebView ag sinamasi).
import { ref } from "vue";
import { IonApp, IonButton } from "@ionic/vue";
import Baglanti from "./ekran/Baglanti.vue";
import KartBul from "./ekran/KartBul.vue";
import { ceviriMobil } from "./cekirdek/sozluk_mobil.js";

const ekran = ref("baglanti");
const c = (anahtar) => ceviriMobil(anahtar, "tr");
</script>

<template>
  <ion-app>
    <Baglanti v-if="ekran === 'baglanti'" />
    <KartBul v-else />
    <ion-button id="ekran-degistir" class="ekran-degistir" size="large" fill="clear" @click="ekran = ekran === 'baglanti' ? 'kartbul' : 'baglanti'">
      {{ ekran === "baglanti" ? c("m.kb.baslik") : c("m.bg.baslik") }}
    </ion-button>
  </ion-app>
</template>

<style>
.ekran-degistir { position: fixed; left: 0; right: 0; bottom: 0; z-index: 10; }
</style>
