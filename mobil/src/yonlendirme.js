// Yonlendirici: dort sekme, her biri AYRI ekran. ACIL DURDUR seridi rotalarin HICBIRINDE degil —
// kabukta (App.vue), yonlendirici cikisinin disinda, tek yerde (A8).
// Kare (hash) gecmisi: paket ici dosyalarla calisir, sunucu yonlendirmesi istemez.
import { createRouter, createWebHashHistory } from "vue-router";
import { ILK_YOL, SEKMELER } from "./ekran/sekmeler.js";
import Durum from "./ekran/Durum.vue";
import Canli from "./ekran/Canli.vue";
import Kayitlar from "./ekran/Kayitlar.vue";
import Ayarlar from "./ekran/Ayarlar.vue";

const EKRANLAR = { durum: Durum, canli: Canli, kayitlar: Kayitlar, ayarlar: Ayarlar };

export function yonlendiriciKur() {
  return createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: "/", redirect: ILK_YOL },
      ...SEKMELER.map((s) => ({ path: s.yol, name: s.ad, component: EKRANLAR[s.ad] })),
      // Kayit gorunumu (A41): Kayitlar sekmesinin ALTINDA; tembel yuklenir (grafik + panel yardimcilari).
      { path: "/kayitlar/:oturum(\\d+)", name: "kayit", component: () => import("./ekran/Kayit.vue") },
      { path: "/:bilinmeyen(.*)*", redirect: ILK_YOL },
    ],
  });
}
