<script setup>
// 5B: gecici baglanti ekrani (kabuk ve sekmeler 5C'de). Kart bulunur; eslesmemisse eslestirme ekrani
// acilir; esliyse imzali bir istekle (kayit listesi) baglanti denenir. Eslestirme YALNIZ kullanici
// parolayi kendisi yazarsa olur.
import { ref, shallowRef } from "vue";
import { IonButton, IonContent, IonInput, IonItem, IonLabel, IonList, IonNote, IonPage } from "@ionic/vue";
import Esles from "./Esles.vue";
import { agKur } from "../cekirdek/ag.js";
import { KartAg, Kasa, Kesif } from "../cekirdek/eklenti.js";
import { kartKur } from "../cekirdek/kart.js";
import { kasaKur } from "../cekirdek/kasa.js";
import { kesifKur, yerelOnbellek } from "../cekirdek/kesif.js";
import { ceviriMobil } from "../cekirdek/sozluk_mobil.js";

const dil = "tr";
const c = (anahtar, degerler) => ceviriMobil(anahtar, dil, degerler);

const DURUM = {
  bagli: "m.bg.durum_bagli", eslesmemis: "m.bg.durum_eslesmemis", bulunamadi: "m.bg.durum_bulunamadi",
  "kimlik-uymuyor": "m.bg.durum_kimlik",
};

const elle = ref("");
const suruyor = ref(false);
const baglanti = shallowRef(null);
const eslesiyor = ref(false);
const mesaj = ref("");
let kart = null;

async function kartAl() {
  if (kart) return kart;
  const d = await KartAg.wifiDurumu();
  const yerelDongu = d.hataAyiklama === true;
  const ag = agKur(KartAg, { yerelDongu });
  const kesif = kesifKur({ kartFetch: ag.kartFetch, eklenti: Kesif, onbellek: yerelOnbellek(localStorage), yerelDongu });
  kart = kartKur({ ag, kesif, kasa: kasaKur(Kasa) });
  return kart;
}

async function calistir(is) {
  suruyor.value = true;
  mesaj.value = "";
  try {
    await is(await kartAl());
  } catch (e) {
    mesaj.value = c("m.bg.hata", { tur: typeof e?.tur === "string" ? e.tur : "?" });
  } finally {
    suruyor.value = false;
  }
}

const baglan = () => calistir(async (k) => { baglanti.value = await k.baglan({ elle: elle.value }); });

const dene = () => calistir(async (k) => {
  const y = await k.istek("GET", "/kayit/liste");
  const liste = await y.json();
  mesaj.value = c("m.bg.imzali_tamam", { oturum: Array.isArray(liste.oturumlar) ? liste.oturumlar.length : 0 });
});

const kaldir = () => calistir(async (k) => {
  const s = await k.eslesmeyiKaldir();
  mesaj.value = c(s.kartta ? "m.bg.kaldirildi" : "m.bg.kaldirildi_yerel");
  baglanti.value = null;
});

function eslesti() {
  eslesiyor.value = false;
  baglanti.value = { ...baglanti.value, durum: "bagli" };
}
</script>

<template>
  <Esles v-if="eslesiyor" :kart="kart" :adres="baglanti.adres" :kimlik="baglanti.kimlik" @eslesti="eslesti" />
  <ion-page v-else>
    <ion-content class="ion-padding">
      <h1>{{ c("m.bg.baslik") }}</h1>
      <ion-item>
        <ion-input id="bg-elle" v-model="elle" :label="c('m.kb.elle')" label-placement="stacked" :placeholder="c('m.kb.elle_ornek')" inputmode="url" autocapitalize="off" />
      </ion-item>
      <ion-button id="bg-baglan" expand="block" size="large" :disabled="suruyor" @click="baglan">{{ c("m.bg.baglan") }}</ion-button>

      <ion-list v-if="baglanti" id="bg-sonuc">
        <ion-item><ion-label>{{ c("m.bg.durum") }}</ion-label><ion-note slot="end">{{ c(DURUM[baglanti.durum] || "m.bg.durum_bulunamadi") }}</ion-note></ion-item>
        <ion-item v-if="baglanti.adres"><ion-label>{{ c("m.kb.adres") }}</ion-label><ion-note slot="end">{{ baglanti.adres }}</ion-note></ion-item>
        <ion-item v-if="baglanti.kimlik"><ion-label>{{ c("m.kb.kimlik") }}</ion-label><ion-note slot="end">{{ baglanti.kimlik }}</ion-note></ion-item>
      </ion-list>

      <ion-button v-if="baglanti && baglanti.durum === 'eslesmemis'" id="bg-esles" expand="block" size="large" :disabled="suruyor" @click="eslesiyor = true">{{ c("m.bg.esles") }}</ion-button>
      <ion-button v-if="baglanti && baglanti.durum === 'bagli'" id="bg-dene" expand="block" size="large" :disabled="suruyor" @click="dene">{{ c("m.bg.dene") }}</ion-button>
      <ion-button v-if="baglanti && baglanti.durum === 'bagli'" id="bg-kaldir" expand="block" size="large" fill="outline" :disabled="suruyor" @click="kaldir">{{ c("m.bg.kaldir") }}</ion-button>

      <p v-if="mesaj" id="bg-mesaj" role="status">{{ mesaj }}</p>
    </ion-content>
  </ion-page>
</template>
