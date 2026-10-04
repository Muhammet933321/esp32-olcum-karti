// Ekranlarin ceviri kisayolu ve dil / tema tercihi (A42, A43). Dil TEPKISEL: `c()` sablonda
// cagrildiginda dil degisince ekran kendiliginden yeniden cizilir. Tercih yerel depoda (tercih.js).
import { ref } from "vue";
import { ceviriMobil } from "../cekirdek/sozluk_mobil.js";
import { VARSAYILAN, tercihOku, tercihUygula, tercihYaz } from "./tercih.js";

// Yerel depo yoksa (ya da erisim kapaliysa) tercih bellekte tutulur: gecerlilik kurali AYNI kalir.
const bellek = new Map();
const bellekDepo = { getItem: (a) => (bellek.has(a) ? bellek.get(a) : null), setItem: (a, d) => { bellek.set(a, String(d)); } };
const depoAl = () => (typeof localStorage === "object" && localStorage !== null ? localStorage : null);
const belgeAl = () => (typeof document === "object" && document !== null ? document : null);

function baslangic() {
  const depo = depoAl();
  if (!depo) return { ...VARSAYILAN };
  try { return tercihOku(depo); } catch { return { ...VARSAYILAN }; }
}

const ilk = baslangic();
export const dil = ref(ilk.dil);
export const tema = ref(ilk.tema);

// Uygulama acilirken bir kez (main.js): saklanan tercih belgeye uygulanir.
export function tercihBaslat() {
  const belge = belgeAl();
  if (belge) tercihUygula(belge, { dil: dil.value, tema: tema.value });
}

export function tercihSec(parca) {
  const depo = depoAl();
  if (!depo) tercihYaz(bellekDepo, { dil: dil.value, tema: tema.value });
  const yeni = tercihYaz(depo || bellekDepo, parca);
  dil.value = yeni.dil;
  tema.value = yeni.tema;
  tercihBaslat();
  return yeni;
}

export function c(anahtar, degerler = null) {
  return ceviriMobil(anahtar, dil.value, degerler);
}

// { anahtar, degerler } | { yazi } | null -> metin
export function yaz(o) {
  if (!o) return "";
  return typeof o.yazi === "string" ? o.yazi : c(o.anahtar, o.degerler || null);
}
