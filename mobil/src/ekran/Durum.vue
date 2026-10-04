<script setup>
// Durum (A39): baglanti + eslesme + aktif kayit karti (kartin G satirindan) + kayit dugmesi +
// esitleme satiri (5D'ye kadar yer tutucu). Kararlar durum_gorunum.js'te (DOM'suz sinanir).
import { computed, inject } from "vue";
import { useRouter } from "vue-router";
import CanliGrafik from "../bilesen/CanliGrafik.vue";
import Ikon from "../bilesen/Ikon.vue";
import KayitDugmesi from "./KayitDugmesi.vue";
import { BIRIM } from "./canli_gorunum.js";
import { baglantiGorunumu, kayitGorunumu, olcumYazilari, YOK } from "./durum_gorunum.js";
import { c, yaz } from "./metin.js";
import { sekmeBul } from "./sekmeler.js";

const kabuk = inject("kabuk");
const hiz = inject("kayitHizi");
const yonlendirici = useRouter();

const bag = computed(() => baglantiGorunumu({
  baglanti: kabuk.baglanti.value, araniyor: kabuk.araniyor.value, akis: kabuk.akis.value,
  sonGorulmeMs: kabuk.sonGorulme.value, simdiMs: kabuk.simdi.value,
}));
const kayit = computed(() => kayitGorunumu(kabuk.akis.value.kayit, kabuk.izleme.value, kabuk.simdi.value));
const olcum = computed(() => olcumYazilari(kabuk.akis.value.son));
const hizYazi = computed(() => (kayit.value.hiz ? (kayit.value.hiz.yaklasik ? "~" : "") + yaz(kayit.value.hiz) : YOK));
const yuzdeYaz = (y) => (y === null ? YOK : c("m.dr.yuzde", { n: y }));
const en = (y) => ({ width: (y === null ? 0 : y) + "%" });

const ayarlaraGit = () => yonlendirici.push(sekmeBul("ayarlar").yol);
</script>

<template>
  <div class="ekran">
    <div id="dr-baglanti" class="bag" role="status">
      <b>{{ c(bag.anahtar) }}</b>
      <span v-if="bag.gecen">· {{ c("m.dr.son_gorulme") }} {{ c(bag.gecen.anahtar, bag.gecen.degerler) }}</span>
      <span v-if="kabuk.baglanti.value && kabuk.baglanti.value.adres" class="sag mono">{{ kabuk.baglanti.value.adres }}</span>
    </div>
    <button v-if="bag.esles" id="dr-esles" type="button" class="dugme ana" @click="ayarlaraGit">{{ c("m.dr.esles") }}</button>
    <button v-if="bag.yeniden" id="dr-yeniden" type="button" class="dugme" @click="kabuk.yenidenBaglan()">{{ c("m.dr.yeniden") }}</button>

    <article id="dr-kayit" class="kart">
      <div class="kb">
        <span class="rozet" :class="kayit.sinif">{{ c(kayit.rozet, kayit.rozetDeger) }}</span>
        <span v-if="kayit.suruyor" class="sure mono">{{ kayit.sure }}</span>
      </div>
      <div v-if="kayit.var" class="ikili">
        <div v-if="kayit.suruyor"><span class="et">{{ c("m.dr.oturum") }}</span><b class="mono">{{ kayit.oturum }}</b></div>
        <div v-if="kayit.suruyor"><span class="et">{{ c("m.cn.hiz") }}</span><b class="mono">{{ hizYazi }}</b></div>
        <div><span class="et">{{ c("m.dr.bellek") }}</span><b class="mono">{{ yuzdeYaz(kayit.doluluk) }}</b><div class="cubuk"><i :style="en(kayit.doluluk)"></i></div></div>
        <div><span class="et">{{ c("m.dr.esitlenmemis") }}</span><b class="mono">{{ yuzdeYaz(kayit.onaysiz) }}</b><div class="cubuk"><i :style="en(kayit.onaysiz)"></i></div></div>
      </div>
      <div class="uclu">
        <div><span class="et">{{ c("m.cn.gerilim") }} · {{ BIRIM.v }}</span><b class="renk-v">{{ olcum.v }}</b></div>
        <div><span class="et">{{ c("m.cn.akim") }} · {{ BIRIM.a }}</span><b class="renk-a">{{ olcum.a }}</b></div>
        <div><span class="et">{{ c("m.cn.guc") }} · {{ BIRIM.w }}</span><b class="renk-w">{{ olcum.w }}</b></div>
      </div>
      <CanliGrafik kucuk :pencere-s="60" :etiket="c('m.cn.grafik_etiket')" />
    </article>

    <KayitDugmesi :hiz-ms="hiz" />

    <div id="dr-esitleme" class="esit"><Ikon ad="esitle" /><span>{{ c("m.dr.esitleme_yakinda") }}</span></div>
  </div>
</template>
