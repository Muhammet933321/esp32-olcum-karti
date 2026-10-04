// Ayarlar > Gelismis: PBKDF2 olcumunun gorunumu (cekirdek/olcum.js pbkdf2Olc sonucu). Saf.
//   sure:       m.ol.pbkdf2_sonuc'un yer tutuculari
//   dogrulama:  sonuc basvuru degeriyle AYNI / YANLIS / bu tur icin basvuru yok (dogru === null)
//   ozet:       turetilen 32 baytin onaltiliginin ILK 16 hanesi (sinama parolasiyla; sir degil)
export const OZET_HANE = 16;

export function pbkdf2Gorunumu(o) {
  const dogrulama = o.dogru === true ? "m.ol.dogru" : o.dogru === false ? "m.ol.yanlis" : "m.ol.basvuru_yok";
  return {
    sure: { tur: o.tur, enaz: o.enAz, ortanca: o.ortanca, encok: o.enCok },
    dogrulama,
    sinif: o.dogru === false ? "hata" : "",
    ozet: typeof o.ozet === "string" ? o.ozet.slice(0, OZET_HANE) : "",
  };
}
