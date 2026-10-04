// CURUTUCU 5B: mevcut testlerin yakalamasi GEREKEN ama (iddiaya gore) yakalamadigi mutasyonlar.
//   node mutasyon/kos.mjs --liste test/curutucu-5b/yasayan-liste.mjs
// YASIYOR = ilgili iddia bos.
export default [
  {
    ad: "C1: WebView'in kendi fetch'i yapi bozma ile aliniyor ({ fetch: disFetch } = window) — 'fetch:' istisnasi yutuyor",
    dosya: "src/cekirdek/kesif.js",
    bul: "    const t0 = simdi();",
    koy: '    const t0 = simdi(); const { fetch: disFetch } = window; disFetch("http://example.com/").catch(() => {});',
    test: "test/gizlilik.test.js",
  },
  {
    ad: "C2: anahtar saklanamayinca bellekteki K sifirlanmiyor (test adi 'K sifirlanir' diyor)",
    dosya: "src/cekirdek/kart.js",
    bul: "      yeni.K.fill(0);\n",
    koy: "",
    test: "test/kart.test.js",
  },
  {
    ad: "C3: kimlik uymayinca baglanti dusurulmuyor (sonraki istekler ayni adrese imzali gider)",
    dosya: "src/cekirdek/kart.js",
    bul: "          if (baglanti === b) baglanti = null;\n",
    koy: "",
    test: "test/kart.test.js",
  },
  {
    ad: "C4: baglan, kartin soyledigi acilisi bicim denetimsiz kabul ediyor",
    dosya: "src/cekirdek/kart.js",
    bul: ' && ACILIS.test(s.bilgi.acilis)) cihaz.acilis',
    koy: ") cihaz.acilis",
    test: "test/kart.test.js",
  },
  {
    ad: "C5: istek, baglanti kimligi ile cihaz kimligini karsilastirmiyor (esles/baglan yarisi)",
    dosya: "src/cekirdek/kart.js",
    bul: "if (!c || b.kimlik !== c.kimlik) throw",
    koy: "if (!c) throw",
    test: "test/kart.test.js",
  },
  {
    ad: "C6: saat ag hatasinda yeniden verilemiyor (saatVerildi geri alinmiyor)",
    dosya: "src/cekirdek/kart.js",
    bul: 'if (e instanceof KartHatasi && e.tur === "ag") b.saatVerildi = false;',
    koy: "",
    test: "test/kart.test.js",
  },
  {
    ad: "C7: Retry-After ust siniri yok (kart 99999 s bekletebilir)",
    dosya: "src/cekirdek/kart.js",
    bul: "s >= 1 && s <= BEKLE_AZAMI_S ? { saniye: s } : null",
    koy: "s >= 1 ? { saniye: s } : null",
    test: "test/kart.test.js",
  },
  {
    ad: "C8: eslesmeyiKaldir 401'de 'kartta: true' demiyor (cihaz-silinmis esleme)",
    dosya: "src/cekirdek/kart.js",
    bul: 'kartta = e instanceof KartHatasi && e.tur === "cihaz-silinmis";',
    koy: "kartta = false;",
    test: "test/kart.test.js",
  },
  {
    ad: "C9: cihazYukle hata yolunda K'yi sifirlamiyor (isaret okunamadi)",
    dosya: "src/cekirdek/kasa.js",
    bul: "try { isaret = await isaretOku(kimlik); } catch (e) { K.fill(0); throw e; }",
    koy: "isaret = await isaretOku(kimlik);",
    test: "test/kasa.test.js",
  },
  {
    ad: "C10: cihazSakla 'geri' kurtarmasi kalkti (disk ilerideyse saklama reddediliyor)",
    dosya: "src/cekirdek/kasa.js",
    bul: '        if (e.tur !== "geri") throw e;\n        k.isaret = await isaretOku(kimlik);\n        if (cihaz.sayac < k.isaret) cihaz.sayac = k.isaret;',
    koy: "        throw e;",
    test: "test/kasa.test.js",
  },
];
