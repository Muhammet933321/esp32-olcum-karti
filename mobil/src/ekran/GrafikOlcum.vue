<script setup>
// Ayarlar > Gelismis > Grafik olcumu (Ö6, A27): 800 bin noktalik uretilmis seride betikli 200 kare.
// Mantik cekirdek/grafik_olcum.js'te (Node'da sinanir); burada tuval ve animasyon karesi baglanir.
import { nextTick, onBeforeUnmount, ref } from "vue";
import { Grafik } from "@ortak/grafik.js";
import { KARE, NOKTA, OLCUT_MS, grafikOlc, grafikSerileri, kareBetigi, seriUret } from "../cekirdek/grafik_olcum.js";
import { c } from "./metin.js";

const tuval = ref(null);
const suruyor = ref(false);
const sonuc = ref(null);
const hata = ref(false);
let grafik = null;
let birakildi = false;

const kareBekle = () => new Promise((coz) => { requestAnimationFrame(() => coz()); });

async function olc() {
  if (suruyor.value) return;
  suruyor.value = true;
  sonuc.value = null;
  hata.value = false;
  await nextTick();                      // tuval DOM'a girsin
  await kareBekle();
  try {
    const seri = seriUret(NOKTA);
    grafik = new Grafik(tuval.value, { zamanKokeni: 0 });
    sonuc.value = await grafikOlc({
      grafik, seriler: grafikSerileri(seri), kareler: kareBetigi(seri.t[0], seri.t[NOKTA - 1], KARE),
      simdi: () => performance.now(), kareBekle, iptal: () => birakildi,
    });
  } catch {
    hata.value = true;
  } finally {
    if (grafik) grafik.yokEt();
    grafik = null;
    suruyor.value = false;
  }
}

onBeforeUnmount(() => { birakildi = true; });
</script>

<template>
  <button id="go-baslat" type="button" class="dugme" :disabled="suruyor" @click="olc">{{ c("m.go.baslat") }}</button>
  <canvas v-if="suruyor" id="go-tuval" ref="tuval" class="grafik buyuk" role="img" :aria-label="c('m.go.baslat')"></canvas>
  <p v-if="suruyor" id="go-suruyor" class="bilgi" role="status">{{ c("m.go.suruyor") }}</p>
  <p v-if="hata" id="go-hata" class="bilgi hata" role="alert">{{ c("m.go.hata") }}</p>
  <div v-if="sonuc" id="go-sonuc" role="status">
    <p v-if="sonuc.gecersiz" id="go-gecersiz" class="bilgi hata" role="alert">{{ c("m.go.gecersiz") }}</p>
    <p v-else class="bilgi" :class="{ uyari: !sonuc.gecti }">{{ c(sonuc.gecti ? "m.go.gecti" : "m.go.kaldi", { olcut: OLCUT_MS, p95: sonuc.aralik.p95 }) }}</p>
    <p class="bilgi mono">{{ c("m.go.ozet", { nokta: sonuc.nokta, kare: sonuc.kare, hazirlik: sonuc.hazirlikMs }) }}</p>
    <p class="bilgi mono">{{ c("m.go.aralik", sonuc.aralik) }}</p>
    <p class="bilgi mono">{{ c("m.go.cizim", sonuc.cizim) }}</p>
  </div>
</template>
