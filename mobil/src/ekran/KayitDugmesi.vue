<script setup>
// "Kaydi baslat" / "Kaydi durdur" (A39, A40). ACIL DURDUR DEGILDIR: kirmizi degil, cerceveli, serit
// disinda. Durdurma iki dokunus ister (uzun bir kaydi yanlislikla kesmemek icin); ACIL DURDUR tek.
import { computed, inject, onBeforeUnmount, ref } from "vue";
import Ikon from "../bilesen/Ikon.vue";
import { canliHali, kayitDugmesi } from "./canli_gorunum.js";
import { c } from "./metin.js";

const props = defineProps({ hizMs: { type: Number, required: true } });

const kabuk = inject("kabuk");
const hal = computed(() => canliHali({ baglanti: kabuk.baglanti.value, araniyor: kabuk.araniyor.value, akis: kabuk.akis.value }));
const dugme = computed(() => kayitDugmesi(kabuk.akis.value.kayit));
const suruyor = ref(false);
const onay = ref(false);
const hata = ref("");
let onaySilme = 0;
const ONAY_MS = 4000;

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

const baslat = () => calistir(() => kabuk.kayitBaslat(props.hizMs));

function durdur() {
  clearTimeout(onaySilme);
  if (!onay.value) {
    onay.value = true;
    onaySilme = setTimeout(() => { onay.value = false; }, ONAY_MS);
    return;
  }
  onay.value = false;
  calistir(() => kabuk.kayitDurdur());
}
onBeforeUnmount(() => clearTimeout(onaySilme));
</script>

<template>
  <button v-if="dugme.is === 'durdur'" id="kayit-durdur" type="button" class="dugme" :disabled="suruyor || !hal.komut" @click="durdur">
    <Ikon ad="dur" />{{ onay ? c("cn.durdur_eminim") : c("cn.durdur") }}
  </button>
  <button v-else id="kayit-baslat" type="button" class="dugme ana" :disabled="suruyor || !hal.komut || dugme.is === 'kapali'" @click="baslat">
    <Ikon ad="kayit" />{{ c("cn.baslat") }}
  </button>
  <p v-if="dugme.is === 'kapali'" class="bilgi uyari">{{ c(dugme.neden, dugme.nedenDeger) }}</p>
  <p v-if="hata" id="kayit-hata" class="bilgi hata" role="alert">{{ hata }}</p>
</template>
