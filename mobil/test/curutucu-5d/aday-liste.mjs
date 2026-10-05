// Curutucu 5D — ADAY mutasyonlar (mobil/mutasyon/*-liste.mjs listelerinde OLMAYAN, davranisi bozan degisiklikler).
// Her biri BUTUN mevcut test takimina karsi kosulur (yalniz bu dizin haric: buradaki testler bilerek kirmizi).
// Kosum (mobil/ icinden):   node mutasyon/kos.mjs --liste test/curutucu-5d/aday-liste.mjs
// YASAYANLAR ayrica yasayan-liste.mjs'te (o liste "hepsi YASIYOR" beklentisiyle saklanir).
// Ilk kosuda yasayip EKRANA ETKISI OLMADIGI icin (esdeger sayilip) cikarilan iki aday: hata halinde `sonMs`in
// tazelenmesi (hata gorunumu sonMs'i kullanmiyor) ve liste sonucundaki `kimlik` alani (hicbir ekran okumuyor).
const TUMU = { komut: [process.execPath, "node_modules/vitest/vitest.mjs", "run", "--exclude", "test/curutucu-5d/**"] };

const E = "src/cekirdek/esitleme.js";
const KB = "src/ekran/kabuk_durum.js";
const K = "src/cekirdek/kayitlar.js";
const V = "src/cekirdek/kayit_veri.js";
const KG = "src/ekran/kayitlar_gorunum.js";
const DG = "src/ekran/durum_gorunum.js";
const U = "src/cekirdek/uygulama.js";
const O = "src/cekirdek/depo_oku.js";
const IS = "src/isci/kayit_isci.js";
const EA = "src/ekran/EsitlemeAyar.vue";
const GO = "src/ekran/GrafikOlcum.vue";
const KY = "src/ekran/Kayitlar.vue";
const KV = "src/ekran/Kayit.vue";
const MA = "android/app/src/main/java/tr/olcumkarti/mobil/MainActivity.java";

export default [
  // ── esitleme.js ──
  { ad: "C5D: onay bir SONRAKI sirayi onayliyor (kart, telefonun almadigi kaydi silebilir)", dosya: E,
    bul: "`Go${sira}`", koy: "`Go${sira + 1}`", test: TUMU },
  { ad: "C5D: sifirla suren esitlemeyi beklemiyor", dosya: E,
    bul: "    if (suren) { try { await suren; } catch { /* kos atmaz */ } }\n", koy: "", test: TUMU },
  { ad: "C5D: sifirladan sonra 60 s kurali sifirlanmiyor (kopya hemen yeniden inmez)", dosya: E,
    bul: "    sonDeneme = null;\n    yay({ ...BOS });", koy: "    yay({ ...BOS });", test: TUMU },
  { ad: "C5D: 'kartta daha yeni sira var ama veri gelmedi' (bekleyen) ekrana hic cikmiyor", dosya: E,
    bul: "bekleyen: Number.isInteger(s.bekleyen) ? s.bekleyen : 0,", koy: "bekleyen: 0,", test: TUMU },
  // ── kabuk_durum.js ──
  { ad: "C5D: kopyaSifirla esitleme kurulu degilse kurmuyor (kart hic baglanmadiysa sifirlanamaz)", dosya: KB,
    bul: '    if (!esit) await esitlemeKur();\n    if (!esit) throw new KabukHatasi("esitleme-yok");', koy: '    if (!esit) throw new KabukHatasi("esitleme-yok");', test: TUMU },
  { ad: "C5D: simdiEsitle esitleme kurulu degilse kurmuyor", dosya: KB,
    bul: "    if (!esit) await esitlemeKur();\n    return esit ? esit.simdi() : null;", koy: "    return esit ? esit.simdi() : null;", test: TUMU },
  // ── uygulama.js ──
  { ad: "C5D: uygulama esitlemeye sonKimlik vermiyor (kartsizken sifirlama uretimde calismaz)", dosya: U,
    bul: "    onayAcik: esitlemeOnayi,                     // A21: varsayilan KAPALI; her turda yeniden okunur\n    sonKimlik,\n",
    koy: "    onayAcik: esitlemeOnayi,                     // A21: varsayilan KAPALI; her turda yeniden okunur\n", test: TUMU },
  { ad: "C5D: uygulama Kayitlar'a sonKimlik vermiyor (disarida liste uretimde bos)", dosya: U,
    bul: "    depoAl: (kimlik) => d.depoKur(KartDepo, kimlik),\n    sonKimlik,\n  });\n}\n\nexport function kayitlarAl",
    koy: "    depoAl: (kimlik) => d.depoKur(KartDepo, kimlik),\n  });\n}\n\nexport function kayitlarAl", test: TUMU },
  // ── kayitlar.js ──
  { ad: "C5D: kayit gorunumu kopyayi yuklemeden aciliyor (dogrudan acilista 'yok')", dosya: K,
    bul: "    if ((await hazirla(k.kimlik)) === null) return null;\n", koy: "", test: TUMU },
  { ad: "C5D: kart kimligi degisince kopya yeniden cozulmuyor (baska kartin listesi gorunur)", dosya: K,
    bul: "if (!yuklenen || yuklenen.kimlik !== kimlik || yuklenen.boy", koy: "if (!yuklenen || yuklenen.boy", test: TUMU },
  // ── kayit_veri.js ──
  { ad: "C5D: akis kimligi isciye gecmiyor (eski karttan kalan kopya 'ayni akis' sayilir)", dosya: V,
    bul: "Number.isInteger(a.akisKimlik) ? a.akisKimlik : null);", koy: "null);", test: TUMU },
  { ad: "C5D: 'zaman tahmini' uyarisi hic cikmiyor", dosya: V,
    bul: "tahmini: Array.isArray(h.tahmini) && h.tahmini.some(Boolean),", koy: "tahmini: false,", test: TUMU },
  { ad: "C5D: 'Tumunu goster' araligi tek nokta (t1 = t0)", dosya: V,
    bul: "t1: n ? h.t[n - 1] : 0,", koy: "t1: n ? h.t[0] : 0,", test: TUMU },
  { ad: "C5D: enerji alanlari yer degistiriyor (mAh <-> Wh)", dosya: V,
    bul: "{ wh: sayi(ok.enerji.wh), mah: sayi(ok.enerji.mah) }", koy: "{ wh: sayi(ok.enerji.mah), mah: sayi(ok.enerji.wh) }", test: TUMU },
  { ad: "C5D: yeniden yuklemede eski oturum onbellegi kaliyor (bayat grafik)", dosya: V,
    bul: "uyari: oturumlar.uyarilar.length, onbellek: new Map(),", koy: "uyari: oturumlar.uyarilar.length, onbellek: (veriKur.onb ||= new Map()),", test: TUMU,
  },
  // ── gorunum ──
  { ad: "C5D: liste satirinda 'eksik' isareti hic cikmiyor", dosya: KG,
    bul: "    eksik: s.eksik === true,\n    acilabilir", koy: "    eksik: false,\n    acilabilir", test: TUMU },
  { ad: "C5D: liste satirinda 'kayitta' rozeti hic cikmiyor", dosya: KG,
    bul: 'kayitta: s.durum === "kayitta",', koy: "kayitta: false,", test: TUMU },
  { ad: "C5D: istatistik tablosunda ornek sayisi hep 0", dosya: KG,
    bul: "adet: ok.v ? ok.v.adet : (ok.i ? ok.i.adet : 0),", koy: "adet: 0,", test: TUMU },
  { ad: "C5D: esitleme 'tamam' iken bekleyen uyarisi gosterilmiyor", dosya: DG,
    bul: 'const ek = e.bekleyen > 0 ? "m.es.bekleyen" : (e.bosluk > 0 ? "m.es.bosluk" : null);', koy: 'const ek = e.bosluk > 0 ? "m.es.bosluk" : null;', test: TUMU },
  // ── ekranlar ──
  { ad: "C5D: Ayarlar onay anahtari ACIK ayari KAPALI gosteriyor (ekran acilisinda okunmuyor)", dosya: EA,
    bul: "const onay = ref(esitlemeOnayi());", koy: "const onay = ref(false);", test: TUMU },
  { ad: "C5D: Ayarlar onay anahtari yalniz ekranda degisiyor (ayar SAKLANMIYOR)", dosya: EA,
    bul: "onay.value = esitlemeOnayiYaz(!onay.value);", koy: "onay.value = !onay.value;", test: TUMU },
  { ad: "C5D: Kayitlar esitleme bitince / kart baglaninca yenilenmiyor", dosya: KY,
    bul: "watch(() => [kabuk.esitleme.value.sonMs, kabuk.baglanti.value && kabuk.baglanti.value.durum], yenile);", koy: "", test: TUMU },
  { ad: "C5D: Kayit ekrani kapanirken grafik yok edilmiyor (dinleyici / kare sizintisi)", dosya: KV,
    bul: "  if (grafik) grafik.yokEt();\n  grafik = null;\n});", koy: "  grafik = null;\n});", test: TUMU },
  { ad: "C5D: Ö6 olcumu tek kanal ciziyor (yuk yariya iner, ekranda 800 bin yazar)", dosya: GO,
    bul: "seriler: grafikSerileri(seri),", koy: "seriler: grafikSerileri(seri).slice(0, 1),", test: TUMU },
  { ad: "C5D: Ö6 olcumunun tuvali gizli (hicbir sey cizilmez, 'GECTI' cikar)", dosya: GO,
    bul: 'class="grafik buyuk" role="img" :aria-label="c(\'m.go.baslat\')"', koy: 'class="grafik buyuk" hidden role="img" :aria-label="c(\'m.go.baslat\')"', test: TUMU },
  // ── A24: yerel okuma / gizlilik testinin dar istisnalari ──
  { ad: "C5D: yerelOku Capacitor'in dosya on ekini ve 10.x agini da kabul ediyor (kotu listede yok)", dosya: O,
    bul: "export const DEPO_ADRESI = /^\\/_depo\\/[0-9a-f]{16}\\/kayitlar\\.kyt$/;",
    koy: "export const DEPO_ADRESI = /^\\/_depo\\/[0-9a-f]{16}\\/kayitlar\\.kyt$|^\\/_capacitor_file_\\/|^http:\\/\\/10\\./;", test: TUMU },
  { ad: "C5D: isci kabugu mesajla verilen adresten betik yukluyor (dinamik import; 'fetch' sozcugu yok)", dosya: IS,
    bul: "  const { no, is, ...arguman } = e.data || {};\n", koy: '  const { no, is, ...arguman } = e.data || {};\n  if (is === "betik") await import(arguman.url);\n', test: TUMU },
  { ad: "C5D: yerelOku okudugu baytlari gorsel istegiyle disari tasiyor (Image; 'fetch' sozcugu yok)", dosya: O,
    bul: "  if (y.status === 404) return new Uint8Array(0);", koy: "  if (y.status === 404) return new Uint8Array(0);\n  if (typeof Image === 'function') new Image().src = url;", test: TUMU },
  { ad: "C5D: MainActivity depo dosyasini GET disi yontemlere de veriyor", dosya: MA,
    bul: 'kimlik == null || !"GET".equals(yontem) ? null', koy: "kimlik == null ? null", test: TUMU },
  { ad: "C5D: MainActivity depo on ekli istegi Capacitor'in dosya sunucusuna birakiyor", dosya: MA,
    bul: "                if (DepoYolu.INSTANCE.depoAdresi(url)) return depoYaniti(url, request.getMethod());\n", koy: "", test: TUMU },
];
