// Kabugun dort sekmesi (A39–A42). Saf liste: yonlendirme.js rotalari, App.vue sekme cubugunu
// buradan kurar. `baslik` sozluk anahtari; `ikon` bilesen/Ikon.vue'daki ad.
export const SEKMELER = Object.freeze([
  Object.freeze({ ad: "durum", yol: "/durum", baslik: "m.sk.durum", ikon: "durum" }),
  Object.freeze({ ad: "canli", yol: "/canli", baslik: "m.sk.canli", ikon: "canli" }),
  Object.freeze({ ad: "kayitlar", yol: "/kayitlar", baslik: "m.sk.kayitlar", ikon: "kayitlar" }),
  Object.freeze({ ad: "ayarlar", yol: "/ayarlar", baslik: "m.sk.ayarlar", ikon: "ayarlar" }),
]);

export const ILK_YOL = SEKMELER[0].yol;

// Sekmenin ALTINDAKI rotalar (rota adi -> sekme adi): baslik ve secili sekme ust sekmeninkidir.
export const ALT_ROTALAR = Object.freeze({ kayit: "kayitlar" });

export function sekmeBul(ad) {
  const asil = Object.hasOwn(ALT_ROTALAR, ad) ? ALT_ROTALAR[ad] : ad;
  return SEKMELER.find((s) => s.ad === asil) || SEKMELER[0];
}
