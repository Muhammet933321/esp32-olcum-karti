import "./cekirdek/rtc_kapat.js";       // ILK ice aktarim: WebRTC arayuzleri baska hicbir kod calismadan kalkar
import { createApp } from "vue";
import { IonicVue } from "@ionic/vue";
import "@ionic/vue/css/core.css";
import "@ionic/vue/css/normalize.css";
import "@ionic/vue/css/structure.css";
import "@ionic/vue/css/typography.css";
import App from "./App.vue";
import { ceviriMobil } from "./cekirdek/sozluk_mobil.js";

document.title = ceviriMobil("m.uygulama", "tr");
createApp(App).use(IonicVue).mount("#app");
