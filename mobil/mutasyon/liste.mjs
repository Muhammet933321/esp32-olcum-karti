// Mutasyon listesi: her iddianin onu YALANLAYAN degisikligi.
//   ad    : "<dilim>: ne bozuluyor"  (--neden ONEK ile suzulur)
//   dosya : mobil/'e gore; bul: kaynakta TAM BIR KEZ gecen dizgi; koy: yerine konan
//   test  : vitest dosyasi (mobil/'e gore) ya da { komut: [...] }
export default [
  {
    ad: "5A-2: sozlukte EN metni bos",
    dosya: "src/cekirdek/sozluk_mobil.js",
    bul: '"Measurement Board"',
    koy: '""',
    test: "test/sozluk.test.js",
  },
  {
    ad: "5A-2: sablonda gomulu metin",
    dosya: "src/App.vue",
    bul: "<h1>{{ baslik }}</h1>",
    koy: "<h1>Ölçüm Kartı</h1>",
    test: "test/sozluk.test.js",
  },
  {
    ad: "5A-2: gomulu metin ayiklayicisi duz ozellige bakmiyor",
    dosya: "test/sozluk.test.js",
    bul: "u.test(o[2])) bulunan.push",
    koy: "u.test(o[2]) && false) bulunan.push",
    test: "test/sozluk.test.js",
  },
];
