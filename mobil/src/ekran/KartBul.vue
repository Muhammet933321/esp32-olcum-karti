<script setup>
// 5A-6: "Karti bul" — gecici, sade ekran (gorsel tasarim turu sonra). Kesfin ve ag eklentisinin
// telefonda calistiginin duman testi; her adayin sonucu gorunur (cleartext olcumu icin de).
import { ref } from "vue";
import { IonButton, IonContent, IonInput, IonItem, IonLabel, IonList, IonNote, IonPage } from "@ionic/vue";
import { agKur } from "../cekirdek/ag.js";
import { KartAg, Kesif } from "../cekirdek/eklenti.js";
import { HedefHatasi } from "../cekirdek/hedef.js";
import { kesifKur, KesifHatasi, yerelOnbellek } from "../cekirdek/kesif.js";
import { ceviriMobil } from "../cekirdek/sozluk_mobil.js";

const dil = "tr";
const c = (anahtar, degerler) => ceviriMobil(anahtar, dil, degerler);

const elle = ref("");
const araniyor = ref(false);
const sonuc = ref(null);
const hata = ref("");
const denenenler = ref([]);
const duyurular = ref([]);

const KAYNAK = { elle: "m.kb.kaynak_elle", onbellek: "m.kb.kaynak_onbellek", ad: "m.kb.kaynak_ad", nsd: "m.kb.kaynak_nsd", ap: "m.kb.kaynak_ap" };
const HATA = {
  bulunamadi: "m.kb.hata_bulunamadi", "kimlik-uymuyor": "m.kb.hata_kimlik", bicim: "m.kb.hata_bicim",
  "ozel-degil": "m.kb.hata_ozel_degil", "ad-izinsiz": "m.kb.hata_ad_izinsiz", "wifi-yok": "m.kb.hata_wifi_yok",
};

async function ara() {
  araniyor.value = true;
  sonuc.value = null;
  hata.value = "";
  denenenler.value = [];
  duyurular.value = [];
  try {
    const durum = await KartAg.wifiDurumu();
    if (!durum.wifi && !durum.hataAyiklama) { hata.value = c(HATA["wifi-yok"]); return; }
    const yerelDongu = durum.hataAyiklama === true;
    const ag = agKur(KartAg, { yerelDongu });
    const kesif = kesifKur({ kartFetch: ag.kartFetch, eklenti: Kesif, onbellek: yerelOnbellek(localStorage), yerelDongu });
    // Duyuru taramasi sonuctan bagimsiz gosterilir: yarisi baska bir aday kazansa da TXT kimligi gorunsun.
    const tarama = Kesif.nsdTara({ sureMs: 1500 }).then((t) => t.servisler || [], () => []);
    const s = await kesif.bul({ elle: elle.value });
    sonuc.value = s;
    denenenler.value = s.denenenler;
    duyurular.value = (await tarama).map((d) => ({ adres: `${d.ip}:${d.port}`, uyuyor: d.kimlik === s.kimlik }));
  } catch (e) {
    if (e instanceof KesifHatasi) denenenler.value = e.denenenler;
    const tur = e instanceof KesifHatasi || e instanceof HedefHatasi ? e.tur : "";
    hata.value = c(HATA[tur] || "m.kb.hata_bilinmeyen");
  } finally {
    araniyor.value = false;
  }
}
</script>

<template>
  <ion-page>
    <ion-content class="ion-padding">
      <h1>{{ c("m.kb.baslik") }}</h1>
      <ion-item>
        <ion-input v-model="elle" :label="c('m.kb.elle')" label-placement="stacked" :placeholder="c('m.kb.elle_ornek')" inputmode="url" autocapitalize="off" />
      </ion-item>
      <ion-button id="ara" expand="block" size="large" :disabled="araniyor" @click="ara">
        {{ araniyor ? c("m.kb.araniyor") : c("m.kb.ara") }}
      </ion-button>

      <p v-if="hata" id="hata" role="alert">{{ hata }}</p>

      <ion-list v-if="sonuc" id="sonuc">
        <ion-item><ion-label>{{ c("m.kb.adres") }}</ion-label><ion-note slot="end">{{ sonuc.adres }}</ion-note></ion-item>
        <ion-item><ion-label>{{ c("m.kb.kimlik") }}</ion-label><ion-note slot="end">{{ sonuc.kimlik }}</ion-note></ion-item>
        <ion-item><ion-label>{{ c("m.kb.kaynak") }}</ion-label><ion-note slot="end">{{ c(KAYNAK[sonuc.kaynak]) }}</ion-note></ion-item>
        <ion-item><ion-label>{{ c("m.kb.sure") }}</ion-label><ion-note slot="end">{{ c("m.kb.sure_ms", { ms: sonuc.sureMs }) }}</ion-note></ion-item>
        <ion-item v-if="sonuc.kaynak === 'nsd'">
          <ion-label>{{ c("m.kb.txt") }}</ion-label>
          <ion-note slot="end">{{ sonuc.txtKimlik === sonuc.kimlik ? c("m.kb.txt_uyuyor") : c("m.kb.txt_uymuyor") }}</ion-note>
        </ion-item>
      </ion-list>

      <h2 v-if="duyurular.length">{{ c("m.kb.duyurular") }}</h2>
      <ion-list id="duyurular">
        <ion-item v-for="d in duyurular" :key="d.adres">
          <ion-label>{{ d.adres }}</ion-label>
          <ion-note slot="end">{{ c("m.kb.txt") }}: {{ d.uyuyor ? c("m.kb.txt_uyuyor") : c("m.kb.txt_uymuyor") }}</ion-note>
        </ion-item>
      </ion-list>

      <h2 v-if="denenenler.length">{{ c("m.kb.denenenler") }}</h2>
      <ion-list id="denenenler">
        <ion-item v-for="d in denenenler" :key="d.adres + d.kaynak">
          <ion-label>{{ d.adres }}</ion-label>
          <ion-note slot="end">{{ c(KAYNAK[d.kaynak]) }} · {{ d.sonuc }}</ion-note>
        </ion-item>
      </ion-list>
    </ion-content>
  </ion-page>
</template>
