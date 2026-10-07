// Panelin Ayarlar'indaki "Bu telefon" bolumu (5P K13, K14) — kok bilesenin secenekleri. Panel bolumu
// `await __olcumOrtam.ayarBolumu()` ile alir ve PcBildirimBolumu gibi baglar: <component :is :dil-secim>.
//
//   props: dilSecim  'tr' | 'en' (| 'sistem': telefonun dili)
//          baglam    cekirdek baglami (testte sahte); verilmezse BuTelefon.vue gercek baglami kullanir
//   olay:  baglanti-degisti ({durum, adres, kimlik} | null) — Kart bolumunde baglan / eslestir / kaldir bitti
//
// Alt bolumler: Kart · Esitleme · Bildirimler · Gelismis (her biri kendi <section class="kart">'i).
// Ionic YOK: panelin style.css siniflari ve belirtecleri; metinler sozluk_mobil.js'ten.

import { cevir, dilCoz } from "./ortak.js";

export const BASLIK_ANAHTARI = "m.bt.baslik";

export const BU_TELEFON = {
  name: "BuTelefonBolumu",
  props: {
    dilSecim: { type: String, default: "tr" },
    baglam: { type: Object, default: null },
  },
  emits: ["baglanti-degisti"],
  computed: {
    dil() { return dilCoz(this.dilSecim); },
    b() { return this.baglam || this.varsayilanBaglam(); },
  },
  methods: {
    t(anahtar, degerler = null) { return cevir(this.dil, anahtar, degerler); },
    // BuTelefon.vue bunu gercek baglamla degistirir (bu modul cekirdege / Capacitor'a bagimli degil).
    varsayilanBaglam() { throw new TypeError("baglam gerekli"); },
    baglantiDegisti(ozet) { this.$emit("baglanti-degisti", ozet); },
  },
};
