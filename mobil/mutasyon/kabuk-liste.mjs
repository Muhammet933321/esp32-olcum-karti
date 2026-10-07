// 5C-kabuk mutasyonlari: acil durdurma yolu (uygulama.js) ve PBKDF2 olcum gorunumu. 5P (P6): eski Ionic kabugunu
// (serit bileseni, tema.css, Durum / Canli gorunumleri) hedefleyenler o dosyalarla birlikte silindi.
// Kosum: node mutasyon/kos.mjs --liste mutasyon/kabuk-liste.mjs
const KABUK = "test/kabuk.test.js";
const EKRAN = "test/ekran.test.js";

export default [
  {
    ad: "5C-kabuk: acilDurdur kart kurulumunu bekliyor",
    dosya: "src/cekirdek/uygulama.js",
    bul: "  return durdurNesnesi.durdur();",
    koy: "  return parcalar().then(() => durdurNesnesi.durdur());",
    test: KABUK,
  },
  {
    ad: "5C-kabuk: durdur adreslerinde onbellek okunmuyor",
    dosya: "src/cekirdek/uygulama.js",
    bul: "  try { kayit = yerelOnbellek(localStorage).oku(); } catch { kayit = null; }",
    koy: "  kayit = null;",
    test: KABUK,
  },
  {
    ad: "5C-kabuk: durdur adreslerinde bagli adres okunmuyor",
    dosya: "src/cekirdek/uygulama.js",
    bul: "  try { bagli = kurulu ? kurulu.durum().adres : null; } catch { bagli = null; }",
    koy: "  bagli = null;",
    test: KABUK,
  },
  {
    ad: "5C-kabuk: onbellek deposuna erisilemeyince bagli adres de kayboluyor (yakalama yok)",
    dosya: "src/cekirdek/uygulama.js",
    bul: "  try { kayit = yerelOnbellek(localStorage).oku(); } catch { kayit = null; }",
    koy: "  kayit = yerelOnbellek(localStorage).oku();",
    test: KABUK,
  },
  {
    ad: "5C-kabuk: PBKDF2 yanlis sonucu 'basvuru yok' diye gosteriliyor",
    dosya: "src/ekran/olcum_gorunum.js",
    bul: 'o.dogru === false ? "m.ol.yanlis" : "m.ol.basvuru_yok"',
    koy: '"m.ol.basvuru_yok"',
    test: EKRAN,
  },
];
