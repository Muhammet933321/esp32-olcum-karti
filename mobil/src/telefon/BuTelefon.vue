<script>
// "Bu telefon" kok bileseni. Secenekler bu_telefon.js'te; burada alt bolumler ve gercek baglam baglanir.
import { BU_TELEFON } from "./bu_telefon.js";
import { gercekBaglam } from "./baglam.js";
import BildirimBolumu from "./BildirimBolumu.vue";
import EsitlemeBolumu from "./EsitlemeBolumu.vue";
import GelismisBolumu from "./GelismisBolumu.vue";
import KartBolumu from "./KartBolumu.vue";

export default {
  ...BU_TELEFON,
  components: { KartBolumu, EsitlemeBolumu, BildirimBolumu, GelismisBolumu },
  methods: { ...BU_TELEFON.methods, varsayilanBaglam: gercekBaglam },
};
</script>

<template>
  <div class="bt-mod" data-bu-telefon :lang="dil">
    <h2 class="gorunmez">{{ t('m.bt.baslik') }}</h2>
    <p class="ipucu bt-giris">{{ t('m.bt.aciklama') }}</p>
    <kart-bolumu :dil="dil" :b="b" @baglanti-degisti="baglantiDegisti" />
    <esitleme-bolumu :dil="dil" :b="b" />
    <bildirim-bolumu :dil="dil" :b="b" />
    <gelismis-bolumu :dil="dil" :b="b" />
  </div>
</template>

<style>
/* Yalniz panel belirtecleri (renk yazilmaz): uc temada (koyu / acik / on panel) panelle ayni gorunur.
   Dokunma hedefi en az 40 px (K19). Yazi boyutlari rem. */
.bt-mod .bt-giris { margin: 0 0 12px; }
.bt-mod button { min-height: 40px; }
.bt-mod input[type=text], .bt-mod input[type=password] { min-height: 40px; }
.bt-mod .bt-anahtar {
  display: flex; align-items: center; gap: 10px; min-height: 40px; cursor: pointer;
  color: var(--yazi); font-size: .875rem;
}
.bt-mod .bt-anahtar input { inline-size: 20px; block-size: 20px; margin: 0; flex: none; accent-color: var(--vurgu); }
.bt-mod .bt-alt { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--kenar-c); }
.bt-mod .bt-alt-baslik { margin: 0 0 8px; font-size: .875rem; font-weight: 600; color: var(--yazi); }
.bt-mod .bt-ust-bosluk { margin-top: 12px; }
.bt-mod .bt-dugmeler { margin-top: 12px; }
.bt-mod .bt-genis { flex: 1 1 220px; min-width: 0; }
.bt-mod .bt-dikkat { color: var(--uyari); font-weight: 600; }
.bt-mod .bt-cihaz-zaman { flex-basis: 100%; font-size: .75rem; color: var(--soluk); font-variant-numeric: tabular-nums; }
.bt-mod .bt-satirlar {
  list-style: none; margin: 6px 0 0; padding: 0; display: grid; gap: 4px;
  font-size: .8125rem; color: var(--yazi); overflow-wrap: anywhere;
}
.bt-mod .bt-adimlar { margin: 8px 0 0; padding-left: 1.25rem; font-size: .8125rem; line-height: 1.5; color: var(--yazi); }
.bt-mod .bt-yonerge { margin-top: 8px; }
</style>
