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
  {
    ad: "5A-3: kayan pencere denetimi kalkti",
    dosya: "test/sahte-kart/sunucu.mjs",
    bul: "if (!pencereKabul(pencereler.get(n), sayac)) {",
    koy: "if (false) {",
    test: "test/sahte-kart.test.js",
  },
  {
    ad: "5A-3: Host beyaz listesi kalkti",
    dosya: "test/sahte-kart/sunucu.mjs",
    bul: 'return h === ip || h.toLowerCase() === "olcum.local" || h.toLowerCase() === "olcum";',
    koy: "return true;",
    test: "test/sahte-kart.test.js",
  },
  {
    ad: "5A-3: p0 serbestligi kalkti",
    dosya: "test/sahte-kart/sunucu.mjs",
    bul: 'return k === "p0" || k === "?";',
    koy: 'return k === "?";',
    test: "test/sahte-kart.test.js",
  },
  {
    ad: "5A-4: 172.16/12 siniri 172/8 oldu",
    dosya: "src/cekirdek/hedef.js",
    bul: "(a === 172 && b >= 16 && b <= 31)",
    koy: "(a === 172)",
    test: "test/hedef.test.js",
  },
  {
    ad: "5A-4: bas sifirli (sekizlik gorunumlu) parca kabul",
    dosya: "src/cekirdek/hedef.js",
    bul: "/^(0|[1-9][0-9]{0,2})$/",
    koy: "/^[0-9]{1,4}$/",
    test: "test/hedef.test.js",
  },
  {
    ad: "5A-4: herkese acik IP reddi kalkti",
    dosya: "src/cekirdek/hedef.js",
    bul: 'throw new HedefHatasi("ozel-degil");',
    koy: "return { ad, port };",
    test: "test/hedef.test.js",
  },
  {
    ad: "5A-4: ad karsilastirmasi 'ile baslar' oldu",
    dosya: "src/cekirdek/hedef.js",
    bul: "if (ad.toLowerCase() === KART_ADI)",
    koy: "if (ad.toLowerCase().startsWith(KART_ADI))",
    test: "test/hedef.test.js",
  },
  {
    ad: "5A-4: yerel dongu secenek olmadan da izinli",
    dosya: "src/cekirdek/hedef.js",
    bul: "(yerelDongu && yerelDonguAdresi(ad))",
    koy: "yerelDonguAdresi(ad)",
    test: "test/hedef.test.js",
  },
  {
    ad: "5A-4: kartFetch hedef kuralini istekten once denetlemiyor",
    dosya: "src/cekirdek/ag.js",
    bul: "    urlDenetle(url, { yerelDongu });\n",
    koy: "",
    test: "test/ag.test.js",
  },
  {
    ad: "5A-4: eklenti hatasinin ham kodu disari siziyor",
    dosya: "src/cekirdek/ag.js",
    bul: 'HATA_TURLERI.includes(e.code) ? e.code : "ic-hata"',
    koy: "true ? e.code : null",
    test: "test/ag.test.js",
  },
  {
    ad: "5A-4: baslik adi buyuk/kucuk harfe duyarli",
    dosya: "src/cekirdek/ag.js",
    bul: "(basliklar.has(ad.toLowerCase()) ? basliklar.get(ad.toLowerCase()) : null)",
    koy: "(basliklar.has(ad) ? basliklar.get(ad) : null)",
    test: "test/ag.test.js",
  },
];
