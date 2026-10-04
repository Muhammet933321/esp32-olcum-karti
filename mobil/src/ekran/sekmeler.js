// Kabugun dort sekmesi (A39–A42). Saf liste: yonlendirme.js rotalari, App.vue sekme cubugunu
// buradan kurar. `baslik` sozluk anahtari; `ikon` bilesen/Ikon.vue'daki ad.
export const SEKMELER = Object.freeze([
  Object.freeze({ ad: "durum", yol: "/durum", baslik: "m.sk.durum", ikon: "durum" }),
  Object.freeze({ ad: "canli", yol: "/canli", baslik: "m.sk.canli", ikon: "canli" }),
  Object.freeze({ ad: "kayitlar", yol: "/kayitlar", baslik: "m.sk.kayitlar", ikon: "kayitlar" }),
  Object.freeze({ ad: "ayarlar", yol: "/ayarlar", baslik: "m.sk.ayarlar", ikon: "ayarlar" }),
]);

export const ILK_YOL = SEKMELER[0].yol;

export function sekmeBul(ad) {
  return SEKMELER.find((s) => s.ad === ad) || SEKMELER[0];
}
