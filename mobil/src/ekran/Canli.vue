<script setup>
// Canli (A40): buyuk V / A / W, canli grafik (60 s / 5 dk), kayit hizi secimi + baslat / durdur.
// Kart bu agda degilse / akis yuvasi doluysa / akis modulu yoksa bunu ACIKCA soyler.
import { computed, inject, ref } from "vue";
import { useRouter } from "vue-router";
import CanliGrafik from "../bilesen/CanliGrafik.vue";
import Gosterge from "../bilesen/Gosterge.vue";
import KayitDugmesi from "./KayitDugmesi.vue";
import { BIRIM, HIZLAR, PENCERELER, SAG_EKSENLER, canliHali, kayitDugmesi } from "./canli_gorunum.js";
import { olcumYazilari } from "./durum_gorunum.js";
import { c } from "./metin.js";
import { sekmeBul } from "./sekmeler.js";

const kabuk = inject("kabuk");
const hiz = inject("kayitHizi");
const yonlendirici = useRouter();

const hal = computed(() => canliHali({ baglanti: kabuk.baglanti.value, araniyor: kabuk.araniyor.value, akis: kabuk.akis.value }));
const olcum = computed(() => olcumYazilari(hal.value.akiyor ? kabuk.akis.value.son : null));
const kayitSuruyor = computed(() => kayitDugmesi(kabuk.akis.value.kayit).is === "durdur");
const pencereS = ref(PENCERELER[0].s);
const sagEksen = ref(SAG_EKSENLER[0]);

const ayarlaraGit = () => yonlendirici.push(sekmeBul("ayarlar").yol);
</script>

<template>
  <div class="ekran">
    <p v-if="!hal.akiyor" id="cn-hal" class="bilgi" :class="hal.sinif" role="status">{{ c(hal.anahtar) }}</p>
    <button v-if="hal.esles" id="cn-esles" type="button" class="dugme ana" @click="ayarlaraGit">{{ c("m.dr.esles") }}</button>

    <div id="cn-degerler" class="kart sikisik">
      <Gosterge :etiket="c('m.cn.gerilim')" :deger="olcum.v" :birim="BIRIM.v" renk="renk-v" />
      <Gosterge :etiket="c('m.cn.akim')" :deger="olcum.a" :birim="BIRIM.a" renk="renk-a" />
      <Gosterge :etiket="c('m.cn.guc')" :deger="olcum.w" :birim="BIRIM.w" renk="renk-w" />
    </div>

    <div class="kart">
      <div class="gb">
        <span>{{ c("m.cn.sol_eksen") }} <b class="renk-v">{{ BIRIM.v }}</b></span>
        <span>{{ c("m.cn.sag_eksen") }} <b :class="'renk-' + sagEksen">{{ BIRIM[sagEksen] }}</b></span>
      </div>
      <CanliGrafik :pencere-s="pencereS" :sag-eksen="sagEksen" :etiket="c('m.cn.grafik_etiket')" />
      <div id="cn-pencere" class="secim" role="radiogroup" :aria-label="c('m.cn.pencere')">
        <button v-for="p in PENCERELER" :key="p.s" type="button" role="radio" :aria-checked="pencereS === p.s" @click="pencereS = p.s">{{ c(p.anahtar) }}</button>
      </div>
      <div id="cn-sag-eksen" class="secim" role="radiogroup" :aria-label="c('m.cn.sag_eksen')">
        <button v-for="e in SAG_EKSENLER" :key="e" type="button" role="radio" :aria-checked="sagEksen === e" @click="sagEksen = e">{{ BIRIM[e] }}</button>
      </div>
    </div>

    <div>
      <span class="et alan-et">{{ c("m.cn.hiz") }}</span>
      <div id="cn-hiz" class="secim" role="radiogroup" :aria-label="c('m.cn.hiz')">
        <button v-for="h in HIZLAR" :key="h.ms" type="button" role="radio" :aria-checked="hiz === h.ms" :disabled="kayitSuruyor" @click="hiz = h.ms">{{ h.yazi }}</button>
      </div>
    </div>

    <KayitDugmesi :hiz-ms="hiz" />
  </div>
</template>
