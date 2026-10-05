<script setup>
// Ayarlar › Bildirimler (A31, A37, A38, A42): bildirim ayarinin karttan alinmasi, bildirim izni, anlik
// izleme (+ pil kisitlamasi, nedeni yazilarak), olay siniflari, deneme bildirimi. Mantik:
// cekirdek/bildirim.js + bildirim_gorunum.js. Araci adresi / kullanicisi bu ekrana HIC gelmez.
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import { bildirimAl, bildirimIzle, bildirimKimligi } from "../cekirdek/uygulama.js";
import { bildirimGorunumu, hataMetni, sinifCevir } from "./bildirim_gorunum.js";
import { c, yaz } from "./metin.js";

const durum = shallowRef(null);
const kimlik = ref(null);
const son = ref(null);
const mesgul = ref(false);
const yenileniyor = ref(false);       // yalniz karttan yenileme surerken (dugmenin yazisi)
const sonuc = ref(null);              // { anahtar, degerler } | null
const hata = ref(null);
let zamanlayici = null;

const g = computed(() => bildirimGorunumu(durum.value, { kimlik: kimlik.value, son: son.value }));

async function oku() {
  try {
    kimlik.value = await bildirimKimligi();
    if (son.value === null) son.value = bildirimIzle.son();
    durum.value = await bildirimAl().durum(kimlik.value);
  } catch {
    durum.value = null;
  }
}

// Bir islem: tek seferde bir tane; sonuc / hata satiri yenilenir, ardindan durum yeniden okunur.
async function yap(is) {
  if (mesgul.value) return;
  mesgul.value = true;
  sonuc.value = null;
  hata.value = null;
  try {
    sonuc.value = (await is()) || null;
  } catch (e) {
    hata.value = hataMetni(e && e.tur);
  } finally {
    mesgul.value = false;
    await oku();
  }
}

const yenile = () => yap(async () => {
  yenileniyor.value = true;
  try { son.value = await bildirimAl().yenile(); } finally { yenileniyor.value = false; }
  return son.value === "yazildi" ? { anahtar: "m.bl.yenile_tamam" } : null;
});
const izinIste = () => yap(async () => { await bildirimAl().izinIste(); });
const pilIste = () => yap(async () => { await bildirimAl().pilMuafiyetiIste(); });
const anlikCevir = () => yap(async () => { await bildirimAl().ayarYaz({ anlik: !durum.value.anlik }); });
const sinifDegistir = (sinif) => yap(async () => { await bildirimAl().ayarYaz({ kapali: sinifCevir(durum.value.kapali, sinif) }); });
const deneme = () => yap(async () => ({ anahtar: (await bildirimAl().deneme()) ? "m.bl.deneme_tamam" : "m.bl.deneme_izin_yok" }));

onMounted(() => {
  oku();
  zamanlayici = setInterval(() => { if (!mesgul.value) oku(); }, 3000);     // izin / pil penceresinden donunce, servis durumu
});
onBeforeUnmount(() => { if (zamanlayici !== null) clearInterval(zamanlayici); });
</script>

<template>
  <p v-if="!g" id="bl-yok" class="bilgi">{{ c("m.bl.hata_genel", { tur: "?" }) }}</p>
  <template v-else>
    <span class="et alan-et">{{ c("m.bl.ayar") }}</span>
    <b id="bl-ayar" :class="{ uyari: g.ayarUyari }">{{ c(g.ayar) }}</b>
    <button id="bl-yenile" type="button" class="dugme" :disabled="mesgul || kimlik === null" @click="yenile">
      {{ yenileniyor ? c("m.bl.yenileniyor") : c("m.bl.yenile") }}
    </button>

    <span class="et alan-et">{{ c("m.bl.izin") }}</span>
    <b id="bl-izin" :class="{ uyari: g.izinIste }">{{ c(g.izin) }}</b>
    <template v-if="g.izinIste">
      <p class="bilgi">{{ c("m.bl.izin_not") }}</p>
      <button id="bl-izin-iste" type="button" class="dugme" :disabled="mesgul" @click="izinIste">{{ c("m.bl.izin_iste") }}</button>
    </template>

    <span id="bl-anlik-et" class="et alan-et">{{ c("m.bl.anlik") }}</span>
    <button id="bl-anlik" type="button" class="dugme" role="switch" :aria-checked="g.anlik" aria-labelledby="bl-anlik-et" :disabled="mesgul" @click="anlikCevir">
      {{ g.anlik ? c("m.bl.acik") : c("m.bl.kapali") }}
    </button>
    <p class="bilgi">{{ c("m.bl.anlik_not") }}</p>
    <template v-if="g.pilGoster">
      <span class="et alan-et">{{ c("m.bl.pil") }}</span>
      <b id="bl-pil" :class="{ uyari: g.pilIste }">{{ c(g.pil) }}</b>
      <template v-if="g.pilIste">
        <p class="bilgi">{{ c("m.bl.pil_not") }}</p>
        <button id="bl-pil-iste" type="button" class="dugme" :disabled="mesgul" @click="pilIste">{{ c("m.bl.pil_iste") }}</button>
      </template>
      <span class="et alan-et">{{ c("m.bl.izleme") }}</span>
      <b id="bl-izleme" :class="{ uyari: g.izlemeUyari }">{{ c(g.izleme) }}</b>
    </template>

    <span class="et alan-et">{{ c("m.bl.siniflar") }}</span>
    <div id="bl-siniflar" class="anahtarlar">
      <button
        v-for="s in g.siniflar" :key="s.sinif" :data-sinif="s.sinif" type="button" class="dugme anahtar-satir" role="switch"
        :aria-checked="s.acik" :disabled="mesgul" @click="sinifDegistir(s.sinif)"
      >
        <span>{{ c(s.anahtar) }}</span><b>{{ s.acik ? c("m.bl.acik") : c("m.bl.kapali") }}</b>
      </button>
    </div>

    <button id="bl-deneme" type="button" class="dugme" :disabled="mesgul" @click="deneme">{{ c("m.bl.deneme") }}</button>
    <p v-if="sonuc" id="bl-sonuc" class="bilgi" role="status">{{ yaz(sonuc) }}</p>
    <p v-if="hata" id="bl-hata" class="bilgi hata" role="alert">{{ yaz(hata) }}</p>
  </template>
</template>
