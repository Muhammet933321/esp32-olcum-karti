// ACIL DURDUR seridinin durum -> gorunum eslemesi (A10). Saf; DOM'suz sinanir.
//   bos          -> yalniz dugme
//   gonderiliyor -> "gonderiliyor"
//   durduruldu   -> "durduruldu", birkac saniye sonra silinir
//   ulasilamadi  -> "ULASILAMADI", KALICI kirmizi uyari (yeniden basilana kadar durur)
// Dugme HER halde basilabilir: hicbir hal dugmeyi kapatmaz.

export const DURDURULDU_SURE_MS = 4000;

const GORUNUM = Object.freeze({
  bos: Object.freeze({ anahtar: null, sinif: "", kalici: false, rol: "status", ikon: null }),
  gonderiliyor: Object.freeze({ anahtar: "m.dd.gonderiliyor", sinif: "gonderiliyor", kalici: true, rol: "status", ikon: null }),
  durduruldu: Object.freeze({ anahtar: "m.dd.durduruldu", sinif: "durduruldu", kalici: false, rol: "status", ikon: "tamam" }),
  ulasilamadi: Object.freeze({ anahtar: "m.dd.ulasilamadi", sinif: "ulasilamadi", kalici: true, rol: "alert", ikon: "uyari" }),
});

export function seritGorunumu(hal) {
  return Object.hasOwn(GORUNUM, hal) ? GORUNUM[hal] : GORUNUM.bos;
}

// Bir hal ekranda ne kadar kalir: 0 = kendiliginden SILINMEZ.
export function seritSuresi(hal) {
  return hal === "durduruldu" ? DURDURULDU_SURE_MS : 0;
}
