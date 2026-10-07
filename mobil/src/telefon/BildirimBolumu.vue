<script>
// Bu telefon › Bildirimler. Mantik bildirim_bolum.js'te.
import { BILDIRIM_BOLUMU } from "./bildirim_bolum.js";

export default BILDIRIM_BOLUMU;
</script>

<template>
  <section class="kart" data-bt-bolum="bildirim" aria-labelledby="bt-bl-baslik">
    <h2 id="bt-bl-baslik">{{ t('m.ay.bildirim') }}</h2>
    <p v-if="!g" class="ipucu" data-bt-bl-yok>{{ t('m.bl.hata_genel', { tur: '?' }) }}</p>
    <template v-else>
      <dl class="ay-bilgi">
        <dt>{{ t('m.bl.ayar') }}</dt><dd data-bt-bl-ayar :class="{ 'bt-dikkat': g.ayarUyari }">{{ t(g.ayar) }}</dd>
        <dt>{{ t('m.bl.izin') }}</dt><dd data-bt-bl-izin :class="{ 'bt-dikkat': g.izinIste }">{{ t(g.izin) }}</dd>
        <template v-if="g.pilGoster">
          <dt>{{ t('m.bl.pil') }}</dt><dd data-bt-bl-pil :class="{ 'bt-dikkat': g.pilIste }">{{ t(g.pil) }}</dd>
          <dt>{{ t('m.bl.izleme') }}</dt><dd data-bt-bl-izleme :class="{ 'bt-dikkat': g.izlemeUyari }">{{ t(g.izleme) }}</dd>
        </template>
      </dl>
      <div class="dugme-grup">
        <button type="button" data-bt-bl-yenile :disabled="mesgul || kimlik === null" :aria-busy="yenileniyor ? 'true' : 'false'" @click="yenile">
          {{ yenileniyor ? t('m.bl.yenileniyor') : t('m.bl.yenile') }}
        </button>
        <button v-if="g.izinIste" type="button" data-bt-bl-izin-iste :disabled="mesgul" @click="izinIste">{{ t('m.bl.izin_iste') }}</button>
      </div>
      <p v-if="g.izinIste" class="ipucu">{{ t('m.bl.izin_not') }}</p>

      <label class="bt-anahtar bt-ust-bosluk" for="bt-bl-anlik">
        <input id="bt-bl-anlik" type="checkbox" role="switch" :checked="g.anlik" :aria-checked="g.anlik ? 'true' : 'false'" :disabled="mesgul" aria-describedby="bt-bl-anlik-not" data-bt-bl-anlik @change="anlikCevir">
        <span>{{ t('m.bl.anlik') }}</span>
      </label>
      <p id="bt-bl-anlik-not" class="ipucu">{{ t('m.bl.anlik_not') }}</p>

      <template v-if="g.pilGoster">
        <template v-if="g.pilIste">
          <p class="uyari">{{ t('m.bl.pil_not') }}</p>
          <div class="dugme-grup bt-ust-bosluk">
            <button type="button" data-bt-bl-pil-iste :disabled="mesgul" @click="pilIste">{{ t('m.bl.pil_iste') }}</button>
          </div>
        </template>
        <div class="dugme-grup bt-ust-bosluk">
          <button type="button" data-bt-bl-yonerge :aria-expanded="yonergeAcik ? 'true' : 'false'" aria-controls="bt-bl-yonerge" @click="yonergeAcik = !yonergeAcik">
            {{ yonergeAcik ? t('m.bl.yn_gizle') : t('m.bl.yn_goster') }}
          </button>
        </div>
        <div v-if="yonergeAcik" id="bt-bl-yonerge" class="bt-yonerge">
          <p class="ipucu">{{ t('m.bl.yn_neden') }}</p>
          <ol class="bt-adimlar">
            <li v-for="a in g.yonerge.adimlar" :key="a">{{ t(a) }}</li>
          </ol>
          <p class="ipucu">{{ t('m.bl.yn_not') }}</p>
          <div class="dugme-grup bt-ust-bosluk">
            <button type="button" data-bt-bl-ayarlari-ac :disabled="mesgul" @click="ayarlariAc">{{ t('m.bl.yn_ac') }}</button>
          </div>
        </div>
      </template>

      <fieldset class="skop-kume bt-ust-bosluk" :disabled="mesgul" data-bt-bl-siniflar>
        <legend>{{ t('m.bl.siniflar') }}</legend>
        <label v-for="s in g.siniflar" :key="s.sinif" class="bt-anahtar">
          <input type="checkbox" role="switch" :checked="s.acik" :aria-checked="s.acik ? 'true' : 'false'" :aria-labelledby="'bt-bl-sinif-ad-' + s.sinif" :data-bt-bl-sinif="s.sinif" @change="sinifDegistir(s.sinif)">
          <span :id="'bt-bl-sinif-ad-' + s.sinif">{{ t(s.anahtar) }}</span>
        </label>
      </fieldset>

      <div class="dugme-grup bt-ust-bosluk">
        <button type="button" data-bt-bl-deneme :disabled="mesgul" @click="deneme">{{ t('m.bl.deneme') }}</button>
      </div>
      <div class="ay-duyuru" aria-live="polite"><p v-if="sonuc" class="ipucu" data-bt-bl-sonuc>{{ yaz(sonuc) }}</p></div>
      <p v-if="hata" class="hata" role="alert" data-bt-bl-hata>{{ yaz(hata) }}</p>
    </template>
  </section>
</template>
