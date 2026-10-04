// CURUTUCU 5C: testlerin YAKALAMADIGINI dusundugum mutasyonlar. Kosum (mobil/ icinden):
//   node mutasyon/kos.mjs --liste test/curutucu-5c/yasayan-liste.mjs
// YASIYOR = iddia bos (kusur girse test yesil kalir).
const KABUK = "test/kabuk.test.js";
const EKRAN = "test/ekran.test.js";

export default [
  {
    ad: "5C-C1: serit 'inert' (dokunulamaz, okunamaz) yapildi — v-if / disabled deseni bunu gormuyor",
    dosya: "src/bilesen/DurdurSeridi.vue",
    bul: '<div id="durdur-seridi" class="serit">',
    koy: '<div id="durdur-seridi" class="serit" inert>',
    test: KABUK,
  },
  {
    ad: "5C-C2: serit CSS'te pointer-events: none (dugme gorunur ama dokunus alttaki ogeye duser)",
    dosya: "src/tema.css",
    bul: ".serit { flex: none; position: relative;",
    koy: ".serit { pointer-events: none; flex: none; position: relative;",
    test: KABUK,
  },
  {
    ad: "5C-C3: ULASILAMADI hemen siliniyor (kalici degil) — silme zamanlayicisi her halde kuruluyor",
    dosya: "src/bilesen/DurdurSeridi.vue",
    bul: "if (sure > 0) silme = setTimeout",
    koy: "if (sure >= 0) silme = setTimeout",
    test: KABUK,
  },
  {
    ad: "5C-C4: serit sonucu hic gostermiyor (hal guncellenmiyor)",
    dosya: "src/bilesen/DurdurSeridi.vue",
    bul: "  hal.value = yeni;\n",
    koy: "",
    test: KABUK,
  },
  {
    ad: "5C-C5: arka plana gecis algilanmiyor (visibilityState karsilastirmasi bozuk) — akis yuvasi JS tarafinda birakilmiyor",
    dosya: "src/ekran/kabuk_durum.js",
    bul: 'belge.visibilityState === "hidden"',
    koy: 'belge.visibilityState === "gizli"',
    test: EKRAN,
  },
  {
    ad: "5C-C6: durdur adreslerinde BAGLI adres okunmuyor (yalniz onbellek + AP)",
    dosya: "src/cekirdek/uygulama.js",
    bul: "  try { bagli = kurulu ? kurulu.durum().adres : null; } catch { bagli = null; }",
    koy: "  bagli = null;",
    test: KABUK,
  },
  {
    ad: "5C-C7: Canli ekrani akis kopukken de ESKI olcumu gosteriyor",
    dosya: "src/ekran/Canli.vue",
    bul: "olcumYazilari(hal.value.akiyor ? kabuk.akis.value.son : null)",
    koy: "olcumYazilari(kabuk.akis.value.son)",
    test: EKRAN,
  },
  {
    ad: "5C-C8: kayit dugmesi 'kapali' halde (dolu / hata / tariyor) basilabiliyor",
    dosya: "src/ekran/KayitDugmesi.vue",
    bul: "!hal.komut || dugme.is === 'kapali'",
    koy: "!hal.komut",
    test: EKRAN,
  },
  {
    ad: "5C-C9: kabuk acilista hicbir sey yapmiyor (kart aranmiyor, akis acilmiyor)",
    dosya: "src/App.vue",
    bul: "onMounted(() => { kabuk.gorunurlukDegisti(); });",
    koy: "onMounted(() => {});",
    test: KABUK,
  },
  {
    ad: "5C-C10: 'Kaydi durdur' tek dokunusla durduruyor (onay adimi yok)",
    dosya: "src/ekran/KayitDugmesi.vue",
    bul: "  if (!onay.value) {",
    koy: "  if (false) {",
    test: EKRAN,
  },
];
