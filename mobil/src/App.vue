<script setup>
// 5A-1: iskelet. Paketlenmis ortak/ kodunun WebView'de calistiginin kaniti (SHA-256("abc")).
import { IonApp, IonContent } from "@ionic/vue";
import { hex, sha256, utf8Kodla } from "@ortak/kripto.js";
import { ceviriMobil } from "./cekirdek/sozluk_mobil.js";

const ozet = hex(sha256(utf8Kodla("abc")));
const baslik = ceviriMobil("m.uygulama", "tr");
</script>

<template>
  <ion-app>
    <ion-content class="ion-padding">
      <h1>{{ baslik }}</h1>
      <p id="ozet">{{ ozet }}</p>
    </ion-content>
  </ion-app>
</template>
