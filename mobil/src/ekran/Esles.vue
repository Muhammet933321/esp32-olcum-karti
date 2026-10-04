<script setup>
// Eslestirme ekrani (Ayarlar rotasinin ICINDE acilir: ACIL DURDUR seridi ve sekmeler yerinde kalir).
// Mantik esles_durum.js'te.
// Kullanim: <Esles :kart="kart" :adres="b.adres" :kimlik="b.kimlik" @eslesti="..." />
//   kart: cekirdek/kart.js kartKur() nesnesi; baglan() "eslesmemis" dondukten sonra.
import { watch } from "vue";
import { IonButton, IonInput, IonItem, IonLabel, IonList, IonNote, IonSpinner } from "@ionic/vue";
import { ceviriMobil } from "../cekirdek/sozluk_mobil.js";
import { eslesDurumu } from "./esles_durum.js";

const props = defineProps({
  kart: { type: Object, required: true },
  adres: { type: String, required: true },
  kimlik: { type: String, required: true },
});
const emit = defineEmits(["eslesti"]);

const dil = "tr";
const c = (anahtar, degerler) => ceviriMobil(anahtar, dil, degerler);

// Bir kare + bir gorev: ilerleme gostergesi ekrana CIZILDIKTEN sonra PBKDF2 baslar.
const kareBekle = () => new Promise((coz) => { requestAnimationFrame(() => setTimeout(coz, 0)); });

const { ad, parola, suruyor, tamam, hata, gonder } = eslesDurumu(props.kart, { kareBekle, varsayilanAd: c("m.es.ad_varsayilan") });
watch(tamam, (v) => { if (v) emit("eslesti"); });
</script>

<template>
  <div id="es-ekran" class="ayar">
      <h1>{{ c("m.es.baslik") }}</h1>
      <p>{{ c("m.es.kart_dogru_mu") }}</p>
      <ion-list id="es-kart">
        <ion-item><ion-label>{{ c("m.kb.kimlik") }}</ion-label><ion-note slot="end">{{ kimlik }}</ion-note></ion-item>
        <ion-item><ion-label>{{ c("m.kb.adres") }}</ion-label><ion-note slot="end">{{ adres }}</ion-note></ion-item>
      </ion-list>

      <ion-item class="es-alan">
        <ion-input id="es-ad" v-model="ad" :label="c('m.es.ad')" label-placement="stacked" :maxlength="24" :disabled="suruyor" autocapitalize="off" />
      </ion-item>
      <ion-item class="es-alan">
        <ion-input id="es-parola" v-model="parola" :label="c('m.es.parola')" label-placement="stacked" type="password" autocomplete="off" autocapitalize="off" autocorrect="off" :spellcheck="false" :clear-on-edit="false" :disabled="suruyor" />
      </ion-item>
      <p class="es-not">{{ c("m.es.parola_not") }}</p>

      <ion-button id="es-gonder" class="es-dugme" expand="block" size="large" :disabled="suruyor || tamam" @click="gonder">
        {{ suruyor ? c("m.es.suruyor") : c("m.es.gonder") }}
      </ion-button>
      <p v-if="suruyor" id="es-ilerleme" role="status"><ion-spinner /> {{ c("m.es.suruyor_not") }}</p>
      <p v-if="hata" id="es-hata" role="alert">{{ c(hata.anahtar, hata.degerler) }}</p>
      <p v-if="tamam" id="es-tamam" role="status">{{ c("m.es.tamam") }}</p>
  </div>
</template>

<style scoped>
.es-alan, .es-dugme { min-height: 48px; }
.es-alan ion-input { min-height: 48px; }
.es-not { font-size: 0.9rem; }
</style>
