<script setup>
// Uygulama KABUGU (5C): ust cubuk + yonlendirici cikisi + ACIL DURDUR seridi + dort sekme.
// ACIL DURDUR seridi BURADA, yonlendirici cikisinin DISINDA ve sekmelerin HEMEN ustunde: her rotada,
// eslestirme ekrani acikken de gorunur (A8). Ekranlar seridi KENDILERI koymaz (test/kabuk.test.js).
// Uygulamada katman acan bilesen (iletisim kutusu, kayan pencere) KULLANILMAZ: seridi hicbir sey ortmez.
import { computed, onBeforeUnmount, onMounted, provide, ref } from "vue";
import { useRoute } from "vue-router";
import DurdurSeridi from "./bilesen/DurdurSeridi.vue";
import Ikon from "./bilesen/Ikon.vue";
import { canliAl, kartAl } from "./cekirdek/uygulama.js";
import { VARSAYILAN_HIZ_MS } from "./ekran/canli_gorunum.js";
import { baglantiGorunumu } from "./ekran/durum_gorunum.js";
import { kabukDurumu } from "./ekran/kabuk_durum.js";
import { c } from "./ekran/metin.js";
import { SEKMELER, sekmeBul } from "./ekran/sekmeler.js";

const kabuk = kabukDurumu({ kartAl, canliAl, belge: document });
provide("kabuk", kabuk);
provide("kayitHizi", ref(VARSAYILAN_HIZ_MS));     // Durum ve Canli ayni secimi kullanir

const rota = useRoute();
const sekme = computed(() => sekmeBul(rota.name));
const bag = computed(() => baglantiGorunumu({
  baglanti: kabuk.baglanti.value, araniyor: kabuk.araniyor.value, akis: kabuk.akis.value,
}));

onMounted(() => { kabuk.gorunurlukDegisti(); });
onBeforeUnmount(() => { kabuk.birak(); });
</script>

<template>
  <div id="kabuk" class="kabuk">
    <header class="ust">
      <h1 id="baslik">{{ c(sekme.baslik) }}</h1>
      <span id="baglanti-cipi" class="cip" :class="bag.sinif" role="status">{{ c(bag.anahtar) }}</span>
    </header>
    <main id="icerik" class="icerik"><router-view /></main>
    <DurdurSeridi />
    <nav id="sekmeler" class="sekme" :aria-label="c('m.sk.gezinme')">
      <router-link v-for="s in SEKMELER" :id="'sekme-' + s.ad" :key="s.ad" :to="s.yol"><Ikon :ad="s.ikon" /><span>{{ c(s.baslik) }}</span></router-link>
    </nav>
  </div>
</template>
