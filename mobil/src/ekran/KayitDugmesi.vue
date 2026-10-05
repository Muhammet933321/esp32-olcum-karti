<script setup>
// "Kaydi baslat" / "Kaydi durdur" (A39, A40). ACIL DURDUR DEGILDIR: kirmizi degil, cerceveli, serit
// disinda. Durdurma iki dokunus ister (uzun bir kaydi yanlislikla kesmemek icin); ACIL DURDUR tek.
// Mantik kayit_dugme.js'te (DOM'suz sinanir): kapalilik, iki dokunus, pil testinde salt okuma.
import { computed, inject, onBeforeUnmount, ref } from "vue";
import Ikon from "../bilesen/Ikon.vue";
import { dokunus, dugmeHali, durdurOnayi } from "./kayit_dugme.js";
import { c } from "./metin.js";

const props = defineProps({ hizMs: { type: Number, required: true } });

const kabuk = inject("kabuk");
const suruyor = ref(false);
const onay = ref(false);
const hata = ref("");
const dugme = computed(() => dugmeHali({
  baglanti: kabuk.baglanti.value, akis: kabuk.akis.value, suruyor: suruyor.value, oturumTuru: kabuk.oturumTuru.value,
}));
const onayci = durdurOnayi({ degisti: (bekliyor) => { onay.value = bekliyor; } });

async function calistir(is) {
  suruyor.value = true;
  hata.value = "";
  try {
    await is();
  } catch (e) {
    hata.value = c("m.cn.komut_hata", { tur: e && typeof e.tur === "string" ? e.tur : "?" });
  } finally {
    suruyor.value = false;
  }
}

function bas() {
  const is = dokunus(dugme.value, onayci);
  if (is === "baslat") calistir(() => kabuk.kayitBaslat(props.hizMs));
  else if (is === "durdur") calistir(() => kabuk.kayitDurdur());
}
onBeforeUnmount(() => onayci.birak());
</script>

<template>
  <button v-if="dugme.is === 'durdur'" id="kayit-durdur" type="button" class="dugme" :disabled="dugme.kapali" @click="bas">
    <Ikon ad="dur" />{{ onay ? c("cn.durdur_eminim") : c("cn.durdur") }}
  </button>
  <button v-else id="kayit-baslat" type="button" class="dugme ana" :disabled="dugme.kapali" @click="bas">
    <Ikon ad="kayit" />{{ c("cn.baslat") }}
  </button>
  <p v-if="dugme.neden" class="bilgi uyari">{{ c(dugme.neden, dugme.nedenDeger) }}</p>
  <p v-if="dugme.aciklama" id="kayit-salt-okuma" class="bilgi uyari">{{ c(dugme.aciklama) }}</p>
  <p v-if="hata" id="kayit-hata" class="bilgi hata" role="alert">{{ hata }}</p>
</template>
