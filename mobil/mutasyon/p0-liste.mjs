// 5C-p0 mutasyonlari (acil durdurma). Ana listeye (liste.mjs) dahil edilir.
export default [
  {
    ad: "5C-p0: durdur() eklentiye gitmeden once bir gorev turu bekliyor",
    dosya: "src/cekirdek/durdur.js",
    bul: "    const soz = p0(hedefler);",
    koy: "    const soz = Promise.resolve().then(() => p0(hedefler));",
    test: "test/durdur.test.js",
  },
  {
    ad: "5C-p0: ag.p0 eklentiye gitmeden once bekliyor",
    dosya: "src/cekirdek/ag.js",
    bul: "    try { cagri = eklenti.p0({ adresler: liste }); } catch { return Promise.resolve(yok()); }",
    koy: "    cagri = Promise.resolve().then(() => eklenti.p0({ adresler: liste }));",
    test: "test/durdur.test.js",
  },
  {
    ad: "5C-p0: kartin erisim noktasi adresi listede yok",
    dosya: "src/cekirdek/durdur.js",
    bul: "[...(Array.isArray(liste) ? liste : []), KART_AP_ADRESI]",
    koy: "[...(Array.isArray(liste) ? liste : [])]",
    test: "test/durdur.test.js",
  },
  {
    ad: "5C-p0: eklenti reddederse p0 atiyor",
    dosya: "src/cekirdek/ag.js",
    bul: "      yok,\n    );",
    koy: "    );",
    test: "test/durdur.test.js",
  },
  {
    ad: "5C-p0: eski (gec gelen) sonuc durumu eziyor",
    dosya: "src/cekirdek/durdur.js",
    bul: '(s) => { if (no === sira) bildir(',
    koy: '(s) => { if (true) bildir(',
    test: "test/durdur.test.js",
  },
  {
    ad: "5C-p0: adresler() atarsa durdurma da atiyor",
    dosya: "src/cekirdek/durdur.js",
    bul: "    try { liste = adresler(); } catch { liste = []; }",
    koy: "    liste = adresler();",
    test: "test/durdur.test.js",
  },
  {
    ad: "5C-p0: arayuz geri cagrisinin hatasi durdurmayi bozuyor",
    dosya: "src/cekirdek/durdur.js",
    bul: "if (degisti) { try { degisti(h); } catch { /* arayuz hatasi durdurmayi etkilemez */ } }",
    koy: "if (degisti) { degisti(h); }",
    test: "test/durdur.test.js",
  },
];
