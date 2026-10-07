// 5D curutucu duzeltmelerini (DURUM 2026-10-05, B1–B13) GERI ALAN mutasyonlar. Kosum (mobil/ icinden):
//   node mutasyon/kos.mjs --neden 5D-D
// Her biri curutucunun kanit testinden (test/curutucu-5d/) ya da duzeltmeyle eklenen testten olmeli.
const E = "src/cekirdek/esitleme.js";
const C = "test/curutucu-5d/";

export default [
  { ad: "5D-D-B3: onay tur basinda bir kez okunuyor (anahtar kapatilsa da Go gider)", dosya: E,
    bul: "            if (!onayli()) return;\n", koy: "", test: C + "esitleme-kenar.test.js" },
  { ad: "5D-D-B12: onayAcik atarsa esitleme de atiyor", dosya: E,
    bul: "const onayli = () => { try { return onayAcik() === true; } catch { return false; } };", koy: "const onayli = () => onayAcik() === true;", test: C + "esitleme-kenar.test.js" },
  { ad: "5D-D-B4: sifirlama surerken elle tur baslatilabiliyor", dosya: E,
    bul: "    if (sifirlaniyor) return Promise.resolve(hal);          // sifirlama bitmeden tur baslamaz\n", koy: "", test: "test/esitleme.test.js" },
  { ad: "5D-D-B4: ikinci sifirlama ilkiyle ic ice giriyor", dosya: E,
    bul: '    if (sifirlaniyor) throw Object.assign(new Error("mesgul"), { name: "KartHatasi", tur: "mesgul" });\n', koy: "", test: "test/esitleme.test.js" },
  { ad: "5D-D-B5: arkaya gecince bekleyen ek tur silinmiyor", dosya: E,
    bul: "    if (!gorunur) tekrar = false;\n", koy: "", test: C + "esitleme-kenar.test.js" },
  { ad: "5D-D-B2: isci cokunce kusak artmiyor (bos islemci 'yuklu' sayilir)", dosya: "src/cekirdek/kayit_istemci.js",
    bul: "/* zaten bitmis */ } kusak += 1; }", koy: "/* zaten bitmis */ } }", test: C + "kayitlar-yalan.test.js" },
  { ad: "5D-D-B2: kayitlar islemci kusagina bakmiyor", dosya: "src/cekirdek/kayitlar.js",
    bul: " || yuklenen.kusak !== kusak()) {", koy: ") {", test: C + "kayitlar-yalan.test.js" },
  { ad: "5D-D-B11: okuma ekrandaki kartin kopyasini yeniden saglamiyor", dosya: "src/cekirdek/kayitlar.js",
    bul: "    if ((await hazirla(gorunenKimlik)) === null) return null;\n", koy: "", test: C + "kayitlar-yalan.test.js" },
  { ad: "5D-D-B1: esitleme metni eslestirme anahtarini yine eziyor", dosya: "src/cekirdek/sozluk_mobil.js",
    bul: '  "m.es.sifirlandi": S(', koy: '  "m.es.tamam": S(', test: C + "sozluk-cakisma.test.js" },
];
