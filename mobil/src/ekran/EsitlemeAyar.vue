<script setup>
// Ayarlar › Esitleme (A21, A23, A42): onay anahtari (VARSAYILAN KAPALI, aciklamasiyla), telefondaki
// kopyanin boyutu, "Kopyayi sifirla" (iki dokunus). Mantik: cekirdek/esitleme_ayar.js, esitleme.js.
import { inject, onBeforeUnmount, onMounted, ref } from "vue";
import { esitlemeOnayi, esitlemeOnayiYaz, kopyaBoyutu } from "../cekirdek/uygulama.js";
import { boyutYaz } from "./esitleme_ayar_gorunum.js";
import { durdurOnayi } from "./kayit_dugme.js";
import { c } from "./metin.js";

const kabuk = inject("kabuk");
const onay = ref(esitlemeOnayi());
const boyut = ref(null);
const eminim = ref(false);
const suruyor = ref(false);
const sonuc = ref("");
const hata = ref("");

async function boyutOku() {
  try {
    const b = await kopyaBoyutu();
    boyut.value = b ? boyutYaz(b.toplam) : null;
  } catch {
    boyut.value = null;
  }
}

function onayDegistir() {
  onay.value = esitlemeOnayiYaz(!onay.value);
}

const onayci = durdurOnayi({ degisti: (v) => { eminim.value = v; } });

async function sifirla() {
  if (suruyor.value || !onayci.bas()) return;
  suruyor.value = true;
  sonuc.value = "";
  hata.value = "";
  try {
    await kabuk.kopyaSifirla();
    sonuc.value = c("m.es.sifirlandi");
  } catch (e) {
    hata.value = c("m.es.sifirla_hata", { tur: e && typeof e.tur === "string" ? e.tur : "?" });
  } finally {
    suruyor.value = false;
    boyutOku();
  }
}

onMounted(boyutOku);
onBeforeUnmount(() => onayci.birak());
</script>

<template>
  <span id="es-onay-et" class="et alan-et">{{ c("m.es.onay") }}</span>
  <button id="es-onay" type="button" class="dugme" role="switch" :aria-checked="onay" aria-labelledby="es-onay-et" @click="onayDegistir">
    {{ onay ? c("m.es.onay_acik") : c("m.es.onay_kapali") }}
  </button>
  <p class="bilgi" :class="{ uyari: onay }">{{ c("m.es.onay_not") }}</p>

  <span class="et alan-et">{{ c("m.es.depolama") }}</span>
  <b id="es-boyut" class="mono">{{ boyut === null ? c("m.es.depolama_yok") : boyut }}</b>
  <button id="es-sifirla" type="button" class="dugme" :disabled="suruyor" @click="sifirla">
    {{ eminim ? c("m.es.sifirla_eminim") : c("m.es.sifirla") }}
  </button>
  <p class="bilgi">{{ c("m.es.sifirla_not") }}</p>
  <p v-if="sonuc" id="es-sonuc" class="bilgi" role="status">{{ sonuc }}</p>
  <p v-if="hata" id="es-hata" class="bilgi hata" role="alert">{{ hata }}</p>
</template>
