<script>
// Bu telefon › Esitleme. Mantik esitleme_bolum.js'te.
import { ESITLEME_BOLUMU } from "./esitleme_bolum.js";

export default ESITLEME_BOLUMU;
</script>

<template>
  <section class="kart" data-bt-bolum="esitleme" aria-labelledby="bt-es-baslik">
    <h2 id="bt-es-baslik">{{ t('m.ay.esitleme') }}</h2>
    <label class="bt-anahtar" for="bt-es-onay">
      <input id="bt-es-onay" type="checkbox" role="switch" :checked="onay" :aria-checked="onay ? 'true' : 'false'" aria-describedby="bt-es-onay-not" data-bt-es-onay @change="onayDegistir($event.target.checked)">
      <span>{{ t('m.es.onay') }}</span>
    </label>
    <p id="bt-es-onay-not" :class="onay ? 'uyari' : 'ipucu'">{{ t('m.es.onay_not') }}</p>

    <dl class="ay-bilgi bt-ust-bosluk">
      <dt>{{ t('m.es.depolama') }}</dt><dd data-bt-es-boyut :class="{ 'ay-aciklama': boyut === null }">{{ boyut === null ? t('m.es.depolama_yok') : boyut }}</dd>
    </dl>
    <div class="dugme-grup">
      <template v-if="eminim">
        <button type="button" class="tehlike" data-bt-es-sifirla-eminim :disabled="suruyor" @click="sifirla">{{ t('m.bt.sifirla_eminim') }}</button>
        <button type="button" data-bt-es-sifirla-vazgec @click="sifirlaVazgec">{{ t('m.bt.vazgec') }}</button>
      </template>
      <button v-else type="button" data-bt-es-sifirla :disabled="suruyor" :aria-busy="suruyor ? 'true' : 'false'" @click="sifirlaBasla">{{ t('m.es.sifirla') }}</button>
    </div>
    <p :class="eminim ? 'uyari' : 'ipucu'" :role="eminim ? 'alert' : null">{{ t('m.es.sifirla_not') }}</p>
    <div class="ay-duyuru" aria-live="polite"><p v-if="sonuc" class="ipucu" data-bt-es-sonuc>{{ yaz(sonuc) }}</p></div>
    <p v-if="hata" class="hata" role="alert" data-bt-es-hata>{{ yaz(hata) }}</p>
  </section>
</template>
