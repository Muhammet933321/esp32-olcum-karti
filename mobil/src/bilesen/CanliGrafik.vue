<script setup>
// Canli grafik: ortak/src/grafik.js `Grafik` sinifini bir <canvas> uzerinde calistirir. Veri
// kabuk.seri()'den (canli.seri(): son 5 dk halka tamponu); pencere ve sag eksen secimi disaridan.
// Etkilesim KAPALI (tema.css .grafik: pointer-events none): her olcum pencereyi yeniden kurar ve
// grafigin ustunden sayfa kaydirilabilmeli.
import { inject, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Grafik } from "@ortak/grafik.js";
import { pencereSerileri } from "../ekran/canli_gorunum.js";
import { temaDinle } from "./tema_dinle.js";

const props = defineProps({
  pencereS: { type: Number, default: 60 },
  sagEksen: { type: String, default: "a" },
  kucuk: { type: Boolean, default: false },
  etiket: { type: String, required: true },
});

const kabuk = inject("kabuk");
const tuval = ref(null);
let grafik = null;
let temaBirak = null;

function ciz() {
  if (!grafik) return;
  const p = pencereSerileri(kabuk.seri(), props.pencereS * 1000, props.sagEksen);
  grafik.secenek.zamanKokeni = p.sonT;          // x ekseni "simdi"ye gore (eksi sureler)
  grafik.veriAyarla(p.seriler);
}

onMounted(() => {
  grafik = new Grafik(tuval.value, { zamanKokeni: 0 });
  tuval.value.tabIndex = -1;                    // etkilesim kapali: klavye odagi da almasin
  temaBirak = temaDinle(() => { if (grafik) grafik.ciz(); });
  ciz();
});
onBeforeUnmount(() => {
  if (temaBirak) temaBirak();
  if (grafik) grafik.yokEt();
  grafik = null;
});
watch(() => [kabuk.cizim.value, props.pencereS, props.sagEksen], ciz);
</script>

<template>
  <canvas ref="tuval" class="grafik" :class="{ kucuk }" role="img" :aria-label="etiket"></canvas>
</template>
