<script setup>
// Kayitlar (A25, A41): telefondaki kopyadan liste (+ kart erisilebilirse kartin dizini: "nerede").
// Arama (ad / etiket / not / #numara) ve tur suzgeci. Satira dokununca kayit gorunumu acilir; yalniz
// kartta olan oturum acilmaz (once esitlenmeli). Veri: cekirdek/kayitlar.js (cozme Web Worker'da).
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import Ikon from "../bilesen/Ikon.vue";
import { kayitlarAl } from "../cekirdek/uygulama.js";
import { TUR_SECENEKLERI, satirGorunumu } from "./kayitlar_gorunum.js";
import { c } from "./metin.js";

const kabuk = inject("kabuk");
const yonlendirici = useRouter();
const arama = ref("");
const tur = ref("hepsi");
const satirlar = ref([]);
const hal = ref("yukleniyor");          // yukleniyor | hazir | hata
const hataTuru = ref("");
const kartVar = ref(false);
const gorunen = computed(() => satirlar.value.map(satirGorunumu));
let sira = 0;
let gecikme = null;

async function yenile() {
  const no = ++sira;
  try {
    const k = await kayitlarAl();
    const s = await k.liste({ arama: arama.value, tur: tur.value });
    if (no !== sira) return;              // daha yeni bir istek var: eski yanit ekrani EZMEZ
    satirlar.value = s.satirlar;
    kartVar.value = s.kartVar;
    hal.value = "hazir";
  } catch (e) {
    if (no !== sira) return;
    hataTuru.value = e && typeof e.tur === "string" ? e.tur : "?";
    hal.value = "hata";
  }
}

function aramaDegisti() {
  if (gecikme !== null) clearTimeout(gecikme);
  gecikme = setTimeout(() => { gecikme = null; yenile(); }, 250);
}

function ac(s) {
  if (s.acilabilir) yonlendirici.push(`/kayitlar/${s.oturum}`);
}

onMounted(yenile);
onBeforeUnmount(() => { if (gecikme !== null) clearTimeout(gecikme); sira += 1; });
watch(tur, yenile);
// Esitleme yeni kayit getirdiyse ya da kart baglandi / koptuysa liste yenilenir.
watch(() => [kabuk.esitleme.value.sonMs, kabuk.baglanti.value && kabuk.baglanti.value.durum], yenile);
</script>

<template>
  <div class="ekran">
    <label class="gizli-etiket" for="ky-arama">{{ c("m.ky.arama") }}</label>
    <input id="ky-arama" v-model="arama" class="arama" type="search" inputmode="search" autocapitalize="off" autocomplete="off"
      :placeholder="c('m.ky.arama')" @input="aramaDegisti">
    <div id="ky-tur" class="secim" role="radiogroup" :aria-label="c('m.ky.tur')">
      <button v-for="t in TUR_SECENEKLERI" :key="t.deger" type="button" role="radio" :aria-checked="tur === t.deger" @click="tur = t.deger">{{ c(t.anahtar) }}</button>
    </div>

    <p v-if="hal === 'yukleniyor'" id="ky-hal" class="bilgi" role="status">{{ c("m.ky.yukleniyor") }}</p>
    <p v-else-if="hal === 'hata'" id="ky-hal" class="bilgi hata" role="alert">{{ c("m.ky.hata", { tur: hataTuru }) }}</p>
    <p v-else-if="gorunen.length === 0" id="ky-hal" class="bilgi" role="status">{{ c(arama || tur !== "hepsi" ? "m.ky.bulunamadi" : "m.ky.bos") }}</p>
    <p v-if="hal === 'hazir' && !kartVar" id="ky-kart-yok" class="bilgi">{{ c("m.ky.kart_yok") }}</p>

    <ul id="ky-liste" class="liste">
      <li v-for="s in gorunen" :key="s.oturum">
        <button type="button" class="satir" :aria-disabled="!s.acilabilir" @click="ac(s)">
          <span class="satir-ust">
            <b>{{ s.ad === null ? c("m.ky.adsiz", { n: s.oturum }) : s.ad }}</b>
            <span class="rozet" :class="s.neredeSinif">{{ c(s.nerede) }}</span>
          </span>
          <span class="satir-alt">
            <span>{{ c(s.tur) }}</span>
            <span v-if="s.tarih" class="mono">{{ s.tarih }}</span>
            <span v-if="s.sure" class="mono">{{ s.sure }}</span>
            <span v-if="s.kayitta" class="rozet uyari">{{ c("m.ky.kayitta") }}</span>
          </span>
          <span v-if="!s.acilabilir" class="satir-not">{{ c("m.ky.once_esitle") }}</span>
          <span v-else-if="s.eksik" class="satir-not">{{ c("m.ky.eksik") }}</span>
          <Ikon v-if="s.acilabilir" ad="ileri" class="satir-ok" />
        </button>
      </li>
    </ul>
  </div>
</template>
