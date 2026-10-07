// CURUTUCU 5C: testlerin YAKALAMADIGINI dusundugum mutasyonlar. Kosum (mobil/ icinden):
//   node mutasyon/kos.mjs --liste test/curutucu-5c/yasayan-liste.mjs
// YASIYOR = iddia bos (kusur girse test yesil kalir).
const KABUK = "test/kabuk.test.js";
const EKRAN = "test/ekran.test.js";

// C3, C4, C8, C10: duzeltmede mantik saf modullere tasindi (durdur_gorunum.js, kayit_dugme.js);
// ayni mutasyonlar yeni yerleriyle mutasyon/duzeltme5c-liste.mjs'te (5C-D6).
export default [
  {
    ad: "5C-C6: durdur adreslerinde BAGLI adres okunmuyor (yalniz onbellek + AP)",
    dosya: "src/cekirdek/uygulama.js",
    bul: "  try { bagli = kurulu ? kurulu.durum().adres : null; } catch { bagli = null; }",
    koy: "  bagli = null;",
    test: KABUK,
  },
];
