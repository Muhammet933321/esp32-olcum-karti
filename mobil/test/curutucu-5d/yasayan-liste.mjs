// Curutucu 5D — YASAYAN mutasyonlar: mobil/mutasyon/*-liste.mjs listelerinde olmayan, davranisi bozan ve
// BUTUN mevcut test takiminin (457 test) YAKALAMADIGI degisiklikler. Aday listesi: aday-liste.mjs (30 aday, 16'si oldu).
// Bu 14'u resmi kosucuyla iki kez kosuldu (2026-10-05): ikisinde de YASIYOR.
// Kosum (mobil/ icinden):   node mutasyon/kos.mjs --liste test/curutucu-5d/yasayan-liste.mjs
// Bulundugunda hepsi YASIYORDU; duzeltmelerden sonra (2026-10-05) hepsi OLDU olmali.
// Test komutu: butun takim, yalniz bu dizin haric (buradaki testler bilerek kirmizi).
const TUMU = { komut: [process.execPath, "node_modules/vitest/vitest.mjs", "run", "--exclude", "test/curutucu-5d/**"] };

const E = "src/cekirdek/esitleme.js";
const K = "src/cekirdek/kayitlar.js";
const V = "src/cekirdek/kayit_veri.js";
const O = "src/cekirdek/depo_oku.js";
const IS = "src/isci/kayit_isci.js";
const GO = "src/ekran/GrafikOlcum.vue";
const MA = "android/app/src/main/java/tr/olcumkarti/mobil/MainActivity.java";

export default [
  // ── esitleme.js ──
  { ad: "C5D-Y1: sifirla suren esitlemeyi beklemiyor (tur surerken 'Kopyayi sifirla' hata verir)", dosya: E,
    bul: "      while (suren) { try { await suren; } catch { /* kos atmaz */ } }\n", koy: "", test: TUMU },
  { ad: "C5D-Y2: sifirladan sonra 60 s kurali sifirlanmiyor (kopya hemen yeniden inmez)", dosya: E,
    bul: "    sonDeneme = null;\n    yay({ ...BOS });", koy: "    yay({ ...BOS });", test: TUMU },
  { ad: "C5D-Y3: 'kartta daha yeni sira var ama veri gelmedi' (bekleyen) durumdan dusuyor (uyari hic cikmaz)", dosya: E,
    bul: "bekleyen: Number.isInteger(s.bekleyen) ? s.bekleyen : 0,", koy: "bekleyen: 0,", test: TUMU },
  // ── kayitlar.js / kayit_veri.js ──
  { ad: "C5D-Y4: kart kimligi degisince kopya yeniden cozulmuyor (ayni boy + ayni akis kimliginde baska kartin listesi)", dosya: K,
    bul: "if (!yuklenen || yuklenen.kimlik !== kimlik || yuklenen.boy", koy: "if (!yuklenen || yuklenen.boy", test: TUMU },
  { ad: "C5D-Y5: akis kimligi isciye gecmiyor (eski akistan kalan kopya kartin guncel akisi sayilir: 'Kart + telefon' yalani)", dosya: V,
    bul: "Number.isInteger(a.akisKimlik) ? a.akisKimlik : null);", koy: "null);", test: TUMU },
  { ad: "C5D-Y6: 'zaman tahmini' uyarisi hic cikmiyor", dosya: V,
    bul: "tahmini: Array.isArray(h.tahmini) && h.tahmini.some(Boolean),", koy: "tahmini: false,", test: TUMU },
  { ad: "C5D-Y7: yeniden yuklemede eski oturum onbellegi kaliyor (buyuyen oturumda bayat grafik / istatistik)", dosya: V,
    bul: "uyari: oturumlar.uyarilar.length, onbellek: new Map(),", koy: "uyari: oturumlar.uyarilar.length, onbellek: (veriKur.onb ||= new Map()),", test: TUMU },
  // ── A24: gizlilik testinin dar istisnalari (uc muaf dosya) ve yerel akitma ──
  { ad: "C5D-Y10: yerelOku Capacitor'in dosya on ekini ve 10.x agini da kabul ediyor (testin 'kotu' listesinde yok)", dosya: O,
    bul: "export const DEPO_ADRESI = /^\\/_depo\\/[0-9a-f]{16}\\/kayitlar\\.kyt$/;",
    koy: "export const DEPO_ADRESI = /^\\/_depo\\/[0-9a-f]{16}\\/kayitlar\\.kyt$|^\\/_capacitor_file_\\/|^http:\\/\\/10\\./;", test: TUMU },
  { ad: "C5D-Y11: isci kabugu mesajla verilen adresten betik yukluyor (dinamik import; yasak sozcuk yok)", dosya: IS,
    bul: "  const { no, is, ...arguman } = e.data || {};\n", koy: '  const { no, is, ...arguman } = e.data || {};\n  if (is === "betik") await import(arguman.url);\n', test: TUMU },
  { ad: "C5D-Y12: yerelOku okudugu adresi gorsel istegiyle disari tasiyor (Image; yasak sozcuk yok)", dosya: O,
    bul: "  if (y.status === 404) return new Uint8Array(0);", koy: "  if (y.status === 404) return new Uint8Array(0);\n  if (typeof Image === 'function') new Image().src = url;", test: TUMU },
  // C5D-Y13 (GET disi yontem): denetim saf Kotlin'e tasindi (DepoYolu.dosyaKimligi) — mutasyonu kotlin-liste.mjs'te.
  { ad: "C5D-Y14: MainActivity depo on ekli istegi Capacitor'in dosya sunucusuna birakiyor (yerel akitma tumden devre disi)", dosya: MA,
    bul: "                if (DepoYolu.INSTANCE.depoAdresi(url)) return depoYaniti(url, request.getMethod());\n", koy: "", test: TUMU },
];
