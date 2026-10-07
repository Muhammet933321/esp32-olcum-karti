<script>
// Bu telefon › Gelismis. Mantik gelismis_bolum.js'te.
import { GELISMIS_BOLUMU } from "./gelismis_bolum.js";

export default GELISMIS_BOLUMU;
</script>

<template>
  <section class="kart" data-bt-bolum="gelismis" aria-labelledby="bt-gel-baslik">
    <h2 id="bt-gel-baslik">{{ t('m.ay.gelismis') }}</h2>

    <h3 class="bt-alt-baslik">{{ t('m.bt.surumler') }}</h3>
    <dl class="ay-bilgi">
      <dt>{{ t('m.bt.uygulama') }}</dt><dd data-bt-surum-uygulama>{{ uygulama || '—' }}</dd>
      <dt>{{ t('m.bt.panel') }}</dt><dd data-bt-surum-panel aria-live="polite" :class="{ 'ay-aciklama': !panel }">{{ panelYazi }}</dd>
    </dl>
    <div class="dugme-grup">
      <button type="button" data-bt-surum-yenile :disabled="panelOkunuyor" @click="panelOku">{{ t('m.bt.yenile') }}</button>
    </div>

    <div class="bt-alt" data-bt-tani>
      <h3 class="bt-alt-baslik">{{ t('m.kb.baslik') }}</h3>
      <p class="ipucu">{{ t('m.bt.tani_ipucu') }}</p>
      <div class="satir">
        <div class="alan bt-genis">
          <label for="bt-tani-elle">{{ t('m.kb.elle') }}</label>
          <input
            id="bt-tani-elle" v-model="elle" type="text" inputmode="url" name="tani-adresi" autocomplete="off" autocapitalize="off"
            autocorrect="off" spellcheck="false" :placeholder="t('m.kb.elle_ornek')" @keyup.enter="kesifAra"
          >
        </div>
        <button type="button" data-bt-tani-ara :disabled="araniyor" :aria-busy="araniyor ? 'true' : 'false'" @click="kesifAra">
          {{ araniyor ? t('m.kb.araniyor') : t('m.kb.ara') }}
        </button>
      </div>
      <p v-if="tani && tani.hata" class="hata" role="alert" data-bt-tani-hata>{{ t(tani.hata) }}</p>
      <dl v-if="tani && tani.sonuc" class="ay-bilgi bt-ust-bosluk" data-bt-tani-sonuc>
        <dt>{{ t('m.kb.adres') }}</dt><dd>{{ tani.sonuc.adres }}</dd>
        <dt>{{ t('m.kb.kimlik') }}</dt><dd>{{ tani.sonuc.kimlik }}</dd>
        <dt>{{ t('m.kb.kaynak') }}</dt><dd class="ay-aciklama">{{ taniKaynak }}</dd>
        <dt>{{ t('m.kb.sure') }}</dt><dd>{{ t('m.kb.sure_ms', { ms: tani.sonuc.sureMs }) }}</dd>
        <template v-if="txtYazi"><dt>{{ t('m.kb.txt') }}</dt><dd class="ay-aciklama">{{ txtYazi }}</dd></template>
      </dl>
      <template v-if="tani && tani.duyurular.length">
        <h4 class="bt-alt-baslik">{{ t('m.kb.duyurular') }}</h4>
        <ul class="bt-satirlar" data-bt-tani-duyurular>
          <li v-for="d in tani.duyurular" :key="d.adres"><span class="mono">{{ d.adres }}</span> <span>{{ t('m.kb.txt') }}: {{ d.uyuyor ? t('m.kb.txt_uyuyor') : t('m.kb.txt_uymuyor') }}</span></li>
        </ul>
      </template>
      <template v-if="taniSatirlari.length">
        <h4 class="bt-alt-baslik">{{ t('m.kb.denenenler') }}</h4>
        <ul class="bt-satirlar" data-bt-tani-denenenler>
          <li v-for="d in taniSatirlari" :key="d.anahtar"><span class="mono">{{ d.adres }}</span> <span>{{ d.kaynak }} · {{ d.sonuc }}</span></li>
        </ul>
      </template>
    </div>

    <div class="bt-alt">
      <h3 class="bt-alt-baslik">{{ t('m.bt.olcumler') }}</h3>
      <div class="dugme-grup">
        <button type="button" data-bt-durdur-olc :disabled="durdurSuruyor" :aria-busy="durdurSuruyor ? 'true' : 'false'" @click="durdurSina">{{ t('m.ol.durdur') }}</button>
        <button type="button" data-bt-pbkdf2 :disabled="pbkdf2Suruyor" :aria-busy="pbkdf2Suruyor ? 'true' : 'false'" @click="pbkdf2Sina">{{ t('m.ol.pbkdf2') }}</button>
        <button type="button" data-bt-websina :disabled="webSuruyor" :aria-busy="webSuruyor ? 'true' : 'false'" @click="webSina">
          {{ webSuruyor ? t('m.ws.suruyor') : t('m.ws.dugme') }}
        </button>
      </div>
      <div class="ay-duyuru" aria-live="polite">
        <p v-if="durdurSuruyor || pbkdf2Suruyor" class="ipucu">{{ t('m.ol.suruyor') }}</p>
      </div>
      <p v-if="durdurSonuc" class="ay-ozet" role="status" data-bt-durdur-sonuc>
        {{ t('m.ol.durdur_sonuc', { tekrar: durdurSonuc.tekrar, basari: durdurSonuc.basari, enaz: durdurSonuc.enAz, ortanca: durdurSonuc.ortanca, encok: durdurSonuc.enCok }) }}
      </p>
      <div v-if="pbkdf2Sonuc" role="status" data-bt-pbkdf2-sonuc>
        <p class="ay-ozet">{{ t('m.ol.pbkdf2_sonuc', pbkdf2Sonuc.sure) }}</p>
        <p :class="pbkdf2Sonuc.sinif === 'hata' ? 'uyari' : 'ipucu'">{{ t(pbkdf2Sonuc.dogrulama) }}</p>
        <p class="ipucu">{{ t('m.ol.ozet', { ozet: pbkdf2Sonuc.ozet }) }}</p>
        <p class="ipucu">{{ t('m.ol.uygulama') }}</p>
      </div>
      <ul v-if="webSonuc.length" class="bt-satirlar" data-bt-websonuc>
        <li v-for="w in webSonuc" :key="w.yol + w.adres"><span class="mono">{{ w.yol }} · {{ w.adres }}</span> <span>{{ webYazi(w.sonuc) }}</span></li>
      </ul>
    </div>
  </section>
</template>
