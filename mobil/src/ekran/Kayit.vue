<script setup>
// Kayit gorunumu (A26, A41): tek oturumun grafigi (ortak/src/grafik.js `Grafik`: kiskacla yakinlastir,
// surukle), GORUNEN aralikta istatistik (ham veriden, Worker'da) ve notlar (okuma). Paylasim 5F'de.
// Veri: cekirdek/kayitlar.js; seriler ve piramitleri Worker'dan hazir gelir.
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Grafik } from "@ortak/grafik.js";
import { gorunurluk } from "@panel/kayit_gorunum.js";
import Ikon from "../bilesen/Ikon.vue";
import { temaDinle } from "../bilesen/tema_dinle.js";
import { kayitlarAl } from "../cekirdek/uygulama.js";
import { SAG_EKSENLER, okumaTablosu, satirGorunumu } from "./kayitlar_gorunum.js";
import { c } from "./metin.js";

const rota = useRoute();
const yonlendirici = useRouter();
const oturumNo = Number(rota.params.oturum);
const tuval = ref(null);
const hal = ref("yukleniyor");          // yukleniyor | hazir | bos | olcumsuz | yok | hata
const hataTuru = ref("");
// shallowRef: seriler ve piramitleri Vue Proxy'sine SARILMAZ (Grafik her karede yuz binlerce kez erisir;
// derin tepkili kapta cizim ~7 kat yavasliyordu — curutucu 5D B7).
const veri = shallowRef(null);
const sag = ref("akim");
const okuma = ref(null);
const baslik = computed(() => (veri.value && veri.value.baslik ? satirGorunumu(veri.value.baslik) : null));
const tablo = computed(() => okumaTablosu(okuma.value));
let grafik = null;
let temaBirak = null;
let kaynak = null;
let gecikme = null;
let okumaNo = 0;

function seriler() {
  return gorunurluk(veri.value.seriler, { v: true, sag: sag.value, zarf: true });
}

async function okumaIste(t0, t1) {
  const no = ++okumaNo;
  try {
    const ok = await kaynak.okuma(oturumNo, t0, t1);
    if (no === okumaNo) okuma.value = ok;
  } catch {
    if (no === okumaNo) okuma.value = null;
  }
}

// Pencere degistikce istatistik yenilenir; surukleme sirasinda her karede degil, durunca.
function pencereDegisti(durum) {
  if (gecikme !== null) clearTimeout(gecikme);
  gecikme = setTimeout(() => { gecikme = null; okumaIste(durum.t0, durum.t1); }, 150);
}

function tumunuGoster() {
  if (!grafik || !veri.value) return;
  if (gecikme !== null) { clearTimeout(gecikme); gecikme = null; }   // bekleyen ESKI pencere tabloyu ezmesin
  grafik.durumAyarla({ t0: veri.value.t0, t1: veri.value.t1 });
  okumaIste(veri.value.t0, veri.value.t1);
}

onMounted(async () => {
  try {
    kaynak = await kayitlarAl();
    const g = Number.isInteger(oturumNo) ? await kaynak.oturum(oturumNo) : null;
    if (g === null) { hal.value = "yok"; return; }
    veri.value = g;
    if (g.tur === "yok") { hal.value = "bos"; return; }
    if (g.gecerli === 0) { hal.value = "olcumsuz"; return; }   // noktalar var, hepsi "okunamadi" bayrakli
    hal.value = "hazir";
  } catch (e) {
    hataTuru.value = e && typeof e.tur === "string" ? e.tur : "?";
    hal.value = "hata";
  }
});

// Tuval `hazir` olunca DOM'a girer: grafik o zaman kurulur.
watch(tuval, (el) => {
  if (!el || grafik || !veri.value) return;
  grafik = new Grafik(el, { zamanKokeni: 0, onDegisim: pencereDegisti });
  temaBirak = temaDinle(() => { if (grafik) grafik.ciz(); });
  grafik.veriAyarla(seriler());
  okumaIste(veri.value.t0, veri.value.t1);
});
watch(sag, () => { if (grafik && veri.value) grafik.veriAyarla(seriler(), { koru: true }); });

onBeforeUnmount(() => {
  okumaNo += 1;
  if (gecikme !== null) clearTimeout(gecikme);
  if (temaBirak) temaBirak();
  if (grafik) grafik.yokEt();
  grafik = null;
});
</script>

<template>
  <div class="ekran">
    <button id="kg-geri" type="button" class="dugme" @click="yonlendirici.push('/kayitlar')"><Ikon ad="geri" />{{ c("m.kg.geri") }}</button>

    <p v-if="hal === 'yukleniyor'" id="kg-hal" class="bilgi" role="status">{{ c("m.ky.yukleniyor") }}</p>
    <p v-else-if="hal === 'yok'" id="kg-hal" class="bilgi uyari" role="status">{{ c("m.kg.yok") }}</p>
    <p v-else-if="hal === 'hata'" id="kg-hal" class="bilgi hata" role="alert">{{ c("m.ky.hata", { tur: hataTuru }) }}</p>

    <article v-if="baslik" id="kg-baslik" class="kart">
      <div class="kb">
        <h2>{{ baslik.ad === null ? c("m.ky.adsiz", { n: baslik.oturum }) : baslik.ad }}</h2>
      </div>
      <div class="ikili">
        <div><span class="et">{{ c(baslik.tur) }}</span><b class="mono">{{ baslik.tarih || "—" }}</b></div>
        <div><span class="et">{{ c("m.kg.sure") }}</span><b class="mono">{{ baslik.sure || "—" }}</b></div>
      </div>
    </article>

    <p v-if="hal === 'bos'" id="kg-bos" class="bilgi" role="status">{{ c("m.kg.bos") }}</p>
    <p v-if="hal === 'olcumsuz'" id="kg-olcumsuz" class="bilgi uyari" role="status">{{ c("m.kg.olcumsuz", { n: veri.adet }) }}</p>

    <div v-if="hal === 'hazir'" class="kart">
      <p v-if="veri.tahmini" class="bilgi uyari">{{ c("m.kg.tahmini") }}</p>
      <canvas id="kg-grafik" ref="tuval" class="grafik buyuk dokun" role="img" :aria-label="c('m.kg.grafik_etiket')"></canvas>
      <div id="kg-sag-eksen" class="secim" role="radiogroup" :aria-label="c('m.cn.sag_eksen')">
        <button v-for="e in SAG_EKSENLER" :key="e.deger" type="button" role="radio" :aria-checked="sag === e.deger" @click="sag = e.deger">{{ c(e.anahtar) }}</button>
      </div>
      <button id="kg-tumu" type="button" class="dugme" @click="tumunuGoster">{{ c("m.kg.tumu") }}</button>
      <p class="bilgi">{{ c("m.kg.ipucu") }}</p>
    </div>

    <article v-if="hal === 'hazir' && tablo" id="kg-okuma" class="kart">
      <div class="kb"><h2>{{ c("m.kg.aralik") }}</h2><span class="sure mono">{{ tablo.sure }}</span></div>
      <table class="okuma">
        <thead><tr><th></th><th>{{ c("m.kg.ort") }}</th><th>{{ c("m.kg.min") }}</th><th>{{ c("m.kg.maks") }}</th></tr></thead>
        <tbody>
          <tr v-for="s in tablo.satirlar" :key="s.anahtar"><th>{{ c(s.anahtar) }} · {{ s.birim }}</th><td>{{ s.ort }}</td><td>{{ s.min }}</td><td>{{ s.maks }}</td></tr>
        </tbody>
      </table>
      <div class="ikili">
        <div><span class="et">{{ c("m.kg.mah") }}</span><b class="mono">{{ tablo.mah }}</b></div>
        <div><span class="et">{{ c("m.kg.wh") }}</span><b class="mono">{{ tablo.wh }}</b></div>
      </div>
      <p class="bilgi">{{ c("m.kg.ornek", { n: tablo.adet }) }}</p>
    </article>

    <article v-if="veri && veri.notlar.length" id="kg-notlar" class="kart">
      <div class="kb"><h2>{{ c("m.kg.notlar") }}</h2></div>
      <ul class="notlar">
        <li v-for="(n, i) in veri.notlar" :key="i"><span v-if="n.gecen" class="mono">{{ n.gecen }}</span> {{ n.metin }}</li>
      </ul>
    </article>
  </div>
</template>
