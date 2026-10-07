<script>
// Bu telefon › Kart. Mantik kart_bolum.js'te (DOM'suz sinanir); burada yalniz sablon.
import { KART_BOLUMU } from "./kart_bolum.js";

export default KART_BOLUMU;
</script>

<template>
  <section class="kart" data-bt-bolum="kart" aria-labelledby="bt-kart-baslik">
    <h2 id="bt-kart-baslik">{{ t('m.ay.kart') }}</h2>
    <p class="ay-ozet" data-bt-durum aria-live="polite">{{ durumYazi }}</p>
    <dl v-if="baglanti && (baglanti.adres || baglanti.kimlik)" class="ay-bilgi" data-bt-bilgi>
      <template v-if="baglanti.adres"><dt>{{ t('m.kb.adres') }}</dt><dd data-bt-adres>{{ baglanti.adres }}</dd></template>
      <template v-if="baglanti.kimlik"><dt>{{ t('m.kb.kimlik') }}</dt><dd data-bt-kimlik>{{ baglanti.kimlik }}</dd></template>
      <template v-if="saatYazi"><dt>{{ t('m.bt.saat') }}</dt><dd class="ay-aciklama" data-bt-saat-kaynak>{{ saatYazi }}</dd></template>
    </dl>

    <div class="satir">
      <div class="alan bt-genis">
        <label for="bt-elle">{{ t('m.kb.elle') }}</label>
        <input
          id="bt-elle" v-model="elle" type="text" inputmode="url" name="kart-adresi" autocomplete="off" autocapitalize="off"
          autocorrect="off" spellcheck="false" :placeholder="t('m.kb.elle_ornek')" aria-describedby="bt-elle-ipucu" @keyup.enter="baglan"
        >
      </div>
      <button type="button" class="birincil" data-bt-baglan :disabled="suruyor" :aria-busy="suruyor ? 'true' : 'false'" @click="baglan">{{ t('m.bg.baglan') }}</button>
    </div>
    <p id="bt-elle-ipucu" class="ipucu">{{ t('m.bt.bul_ipucu') }}</p>
    <p v-if="bulunamadi" class="ipucu" data-bt-tani-ipucu>{{ t('m.bt.bulunamadi_ipucu') }}</p>

    <div v-if="bagli || kaldirAcik" class="dugme-grup bt-dugmeler">
      <button v-if="bagli" type="button" data-bt-dene :disabled="suruyor" @click="dene">{{ t('m.bg.dene') }}</button>
      <button v-if="bagli" type="button" data-bt-saat :disabled="suruyor" @click="saatVer">{{ t('m.bt.saat_ver') }}</button>
      <template v-if="kaldirAcik">
        <template v-if="onay === 'kaldir'">
          <button type="button" class="tehlike" data-bt-kaldir-eminim :disabled="suruyor" @click="kaldir">{{ t('m.bt.kaldir_eminim') }}</button>
          <button type="button" data-bt-kaldir-vazgec @click="onayVazgec">{{ t('m.bt.vazgec') }}</button>
        </template>
        <button v-else type="button" data-bt-kaldir :disabled="suruyor" @click="onayIste('kaldir')">{{ t('m.bg.kaldir') }}</button>
      </template>
    </div>
    <p v-if="onay === 'kaldir'" class="uyari" role="alert">{{ t('m.bt.kaldir_uyari') }}</p>
    <p v-if="bagli" class="ipucu">{{ t('m.bt.saat_ipucu') }}</p>

    <div class="ay-duyuru" aria-live="polite"><p v-if="mesaj && !mesajHata" class="ipucu" data-bt-mesaj>{{ yaz(mesaj) }}</p></div>
    <p v-if="mesaj && mesajHata" class="hata" role="alert" data-bt-hata>{{ yaz(mesaj) }}</p>

    <div v-if="eslesmeAcik" class="bt-alt" data-bt-esles>
      <h3 class="bt-alt-baslik">{{ t('m.es.baslik') }}</h3>
      <p class="ipucu">{{ t('m.es.kart_dogru_mu') }}</p>
      <div class="es-form">
        <div class="alan">
          <label for="bt-ad">{{ t('m.es.ad') }}</label>
          <input
            id="bt-ad" v-model="ad" type="text" name="cihaz-adi" maxlength="24" autocomplete="off" autocapitalize="off"
            autocorrect="off" spellcheck="false" :disabled="esliyor" :aria-invalid="adHatasi ? 'true' : null" aria-describedby="bt-ad-ipucu"
          >
          <span id="bt-ad-ipucu" class="ipucu">{{ t('m.bt.ad_ipucu') }}</span>
        </div>
        <div class="alan">
          <label for="bt-parola">{{ t('m.es.parola') }}</label>
          <input
            id="bt-parola" ref="parola" type="password" name="web-parolasi" autocomplete="off" autocapitalize="off"
            autocorrect="off" spellcheck="false" :disabled="esliyor" aria-describedby="bt-parola-ipucu" @keyup.enter="eslestir"
          >
          <span id="bt-parola-ipucu" class="ipucu">{{ t('m.es.parola_not') }}</span>
        </div>
        <button type="button" class="birincil" data-bt-eslestir :disabled="esliyor || suruyor" :aria-busy="esliyor ? 'true' : 'false'" @click="eslestir">
          {{ esliyor ? t('m.es.suruyor') : t('m.es.gonder') }}
        </button>
      </div>
      <p v-if="esliyor" class="ipucu" role="status" data-bt-esles-suruyor>{{ t('m.es.suruyor_not') }}</p>
      <p v-if="eslesHata" class="hata" role="alert" data-bt-esles-hata>{{ yaz(eslesHata) }}</p>
    </div>
    <p v-if="eslesTamam" class="ipucu" role="status" data-bt-esles-tamam>{{ t('m.es.tamam') }}</p>

    <div v-if="bagli" class="bt-alt" data-bt-cihazlar>
      <div class="ay-ust">
        <h3 id="bt-liste-baslik" class="bt-alt-baslik ay-kaynak">{{ t('m.bt.liste_baslik') }}</h3>
        <button type="button" data-bt-liste-yenile :disabled="suruyor" @click="listeYukle">{{ t('m.bt.yenile') }}</button>
      </div>
      <p v-if="listeHata" class="hata" role="alert" data-bt-liste-hata>{{ yaz(listeHata) }}</p>
      <ul v-if="satirlar.length" class="ag-liste" aria-labelledby="bt-liste-baslik" data-bt-liste>
        <li v-for="c in satirlar" :key="c.n" :data-bt-cihaz="c.n">
          <span class="ag-ad">{{ c.ad }}</span>
          <span v-if="c.kendi" class="rozet acik" data-bt-kendi>{{ t('m.bt.bu_telefon') }}</span>
          <span class="etiket">{{ t('m.bt.no', { n: c.n }) }}</span>
          <span class="bosluk"></span>
          <button v-if="c.kendi" type="button" :data-bt-kendi-kaldir="c.n" :disabled="suruyor" @click="onayIste('kaldir')">{{ t('m.bg.kaldir') }}</button>
          <template v-else-if="onay === 'sil' + c.n">
            <button type="button" class="tehlike" :data-bt-sil-eminim="c.n" :disabled="suruyor" @click="cihazSil(c.n)">{{ t('m.bt.sil_eminim') }}</button>
            <button type="button" :data-bt-sil-vazgec="c.n" @click="onayVazgec">{{ t('m.bt.vazgec') }}</button>
          </template>
          <button v-else type="button" :data-bt-sil="c.n" :disabled="suruyor" :aria-label="t('m.bt.sil_ad', { ad: c.ad })" @click="onayIste('sil' + c.n)">{{ t('m.bt.sil') }}</button>
          <span class="bt-cihaz-zaman">{{ t('m.bt.cihaz_zaman', { eklenme: c.eklenmeYazi, son: c.sonYazi }) }}</span>
        </li>
      </ul>
      <p v-else-if="listeBos" class="ipucu" data-bt-liste-bos>{{ t('m.bt.liste_bos') }}</p>
      <p v-if="onay && onay !== 'kaldir'" class="uyari" role="alert">{{ t('m.bt.sil_uyari') }}</p>
    </div>
  </section>
</template>
