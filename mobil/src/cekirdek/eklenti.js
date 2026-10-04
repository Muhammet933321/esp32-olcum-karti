// Kotlin eklentilerinin WebView tarafi (Capacitor). Ekranlar bunlari dogrudan degil, cekirdek/
// modulleri (ag.js, kesif.js) uzerinden kullanir.
import { registerPlugin } from "@capacitor/core";

export const KartAg = registerPlugin("KartAg");
export const Kesif = registerPlugin("Kesif");
