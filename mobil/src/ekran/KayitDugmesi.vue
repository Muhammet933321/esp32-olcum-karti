<script setup>
// "Kaydi baslat" / "Kaydi durdur" (A39, A40). ACIL DURDUR DEGILDIR: kirmizi degil, cerceveli, serit
// disinda. Durdurma iki dokunus ister (uzun bir kaydi yanlislikla kesmemek icin); ACIL DURDUR tek.
// Mantik kayit_dugme.js'te (DOM'suz sinanir): kapalilik, iki dokunus, pil testinde salt okuma.
import { computed, inject, onBeforeUnmount, ref, watch } from "vue";
import Ikon from "../bilesen/Ikon.vue";
import { kayitBittiMi } from "../cekirdek/bildirim.js";
import { izlemeSorusu } from "../cekirdek/uygulama.js";
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
// Anlik izleme sorusu (kullanici karari): kayit BU telefondan baslatilinca bir kez; kaydi bekletmez.
const soru = ref(izlemeSorusu.hal());
const soruBirak = izlemeSorusu.dinle((h) => { soru.value = h; });
// Kayit durumu kartin G satirindan: KAYIT -> BEKLIYOR "bitti" DEGIL; akis kopunca (bilinmiyor) soru kalir.
const kayitKodu = computed(() => { const g = kabuk.akis.value.kayit; return g && Number.isInteger(g.durum) ? g.durum : null; });
watch(kayitKodu, (yeni, once) => { if (kayitBittiMi(once, yeni)) izlemeSorusu.kayitBitti(); });

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
  if (is === "baslat") calistir(async () => { await kabuk.kayitBaslat(props.hizMs); izlemeSorusu.kayitBasladi(); });
  else if (is === "durdur") calistir(() => kabuk.kayitDurdur());
}
onBeforeUnmount(() => { onayci.birak(); soruBirak(); });
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
  <div v-if="soru === 'soruluyor' || soru === 'aciliyor'" id="izleme-soru" class="soru" role="group" aria-labelledby="izleme-soru-et">
    <p id="izleme-soru-et" class="bilgi">{{ c("m.bl.soru") }}</p>
    <div class="soru-dugmeler">
      <button id="izleme-soru-evet" type="button" class="dugme" :disabled="soru === 'aciliyor'" @click="izlemeSorusu.evet()">{{ c("m.bl.soru_evet") }}</button>
      <button id="izleme-soru-hayir" type="button" class="dugme" :disabled="soru === 'aciliyor'" @click="izlemeSorusu.hayir()">{{ c("m.bl.soru_hayir") }}</button>
    </div>
  </div>
  <p v-else-if="soru === 'acildi'" id="izleme-soru-sonuc" class="bilgi" role="status">{{ c("m.bl.soru_acildi") }}</p>
  <p v-else-if="soru === 'acilamadi'" id="izleme-soru-sonuc" class="bilgi uyari" role="status">{{ c("m.bl.soru_acilamadi") }}</p>
</template>
