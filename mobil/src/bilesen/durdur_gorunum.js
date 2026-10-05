// ACIL DURDUR seridinin durum -> gorunum eslemesi (A10). Saf; DOM'suz sinanir.
//   bos          -> yalniz dugme
//   gonderiliyor -> "gonderiliyor"
//   durduruldu   -> "durduruldu", birkac saniye sonra silinir
//   baska-yanit  -> "baska bir adres yanit verdi", KALICI kehribar uyari (kartin durdugu dogrulanamadi)
//   ulasilamadi  -> "ULASILAMADI", KALICI kirmizi uyari (yeniden basilana kadar durur)
// Dugme HER halde basilabilir: hicbir hal dugmeyi kapatmaz.

export const DURDURULDU_SURE_MS = 4000;

const GORUNUM = Object.freeze({
  bos: Object.freeze({ anahtar: null, sinif: "", kalici: false, rol: "status", ikon: null }),
  gonderiliyor: Object.freeze({ anahtar: "m.dd.gonderiliyor", sinif: "gonderiliyor", kalici: true, rol: "status", ikon: null }),
  durduruldu: Object.freeze({ anahtar: "m.dd.durduruldu", sinif: "durduruldu", kalici: false, rol: "status", ikon: "tamam" }),
  "baska-yanit": Object.freeze({ anahtar: "m.dd.baska_yanit", sinif: "baska-yanit", kalici: true, rol: "alert", ikon: "uyari" }),
  ulasilamadi: Object.freeze({ anahtar: "m.dd.ulasilamadi", sinif: "ulasilamadi", kalici: true, rol: "alert", ikon: "uyari" }),
});

export function seritGorunumu(hal) {
  return Object.hasOwn(GORUNUM, hal) ? GORUNUM[hal] : GORUNUM.bos;
}

// Bir hal ekranda ne kadar kalir: 0 = kendiliginden SILINMEZ.
export function seritSuresi(hal) {
  return hal === "durduruldu" ? DURDURULDU_SURE_MS : 0;
}

// Seridin dinleyici + zamanlayici mantigi (DurdurSeridi.vue yalniz `goster`i bir ref'e baglar).
//   const iz = seritIzleyici({ goster: (hal) => { ... } });
//   durdurDinle(iz.al);      // her yeni hal HEMEN gosterilir; yalniz gecici hal suresi dolunca "bos" olur
//   iz.birak();              // bekleyen silme iptal
// Kalici haller (ulasilamadi, baska-yanit, gonderiliyor) icin zamanlayici KURULMAZ.
export function seritIzleyici({ goster, zamanla = (fn, ms) => setTimeout(fn, ms), zamaniBirak = (z) => clearTimeout(z) }) {
  if (typeof goster !== "function") throw new TypeError("goster gerekli");
  let silme = null;
  let gosterilen = null;

  function iptal() {
    if (silme !== null) zamaniBirak(silme);
    silme = null;
  }

  function al(yeni) {
    iptal();
    gosterilen = yeni;
    goster(yeni);
    const sure = seritSuresi(yeni);
    if (sure > 0) {
      silme = zamanla(() => {
        silme = null;
        if (gosterilen !== yeni) return;
        gosterilen = "bos";
        goster("bos");
      }, sure);
    }
  }

  return { al, birak: iptal };
}
