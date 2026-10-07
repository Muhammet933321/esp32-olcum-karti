// "Bu telefon" bolumunun giris noktasi (5P K13). Telefon ortami `ayarBolumu()`yu buna baglar:
//
//   ayarBolumu: async () => (await import("../telefon/index.js")).bolum()
//
// Donus: Vue bileseni (SFC; vite derleme aninda render islevine cevirir — calisma aninda sablon derlenmez,
// CSP eval'i yasaklar). Panel `markRaw` ile baglar: <component :is :dil-secim>.
// Bilesen tembel iner: panelin acilisina girmez, Ayarlar › Bu telefon acilinca gelir.

export { baglantiDinle, mesgulMu } from "./olay.js";

export async function bolum() {
  const m = await import("./BuTelefon.vue");
  return m.default;
}
