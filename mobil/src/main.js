import "./cekirdek/rtc_kapat.js";       // ILK ice aktarim: WebRTC arayuzleri baska hicbir kod calismadan kalkar
import { createApp } from "vue";
import { IonicVue } from "@ionic/vue";
import "@ionic/vue/css/core.css";
import "@ionic/vue/css/normalize.css";
import "@ionic/vue/css/structure.css";
import "@ionic/vue/css/typography.css";
import "./tema.css";
import App from "./App.vue";
import { ceviriMobil } from "./cekirdek/sozluk_mobil.js";
import { dil, tercihBaslat } from "./ekran/metin.js";
import { yonlendiriciKur } from "./yonlendirme.js";

tercihBaslat();                       // saklanan dil / tema belgeye (ilk boyamadan once)
document.title = ceviriMobil("m.uygulama", dil.value);
createApp(App).use(IonicVue).use(yonlendiriciKur()).mount("#app");
