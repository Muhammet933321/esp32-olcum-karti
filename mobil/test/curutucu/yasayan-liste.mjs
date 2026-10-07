// CURUTUCU (5A-7): bulundugu gun testlerin YAKALAMADIGI mutasyonlar (16/16 yasiyordu). Testler
// guclendirildi; artik hepsi OLMELI ve ana listeye (mutasyon/liste.mjs) dahildir.
// Ilk hali: kosucu bunlara "YASIYOR" diyordu —
// yani ilgili iddia bos (ya da ayiklayici / desen kaciriyor).
//   node mutasyon/kos.mjs --liste test/curutucu/yasayan-liste.mjs [--neden ONEK]
const KT = "android/app/src/main/java/tr/olcumkarti/mobil";
export default [
  // --- gizlilik.test.js: "uretim kodunda console.* ve Log.* cagrisi yok" ---
  {
    ad: "G1: Log.wtf ile adres logcat'e (desen tek harfli yontem ariyor: Log.[a-z]\\()",
    dosya: `${KT}/ag/KartAgPlugin.kt`,
    bul: 'if (url == null) { call.reject("bicim", "bicim"); return }',
    koy: 'if (url == null) { call.reject("bicim", "bicim"); return }; android.util.Log.wtf("KartAg", url)',
    test: "test/gizlilik.test.js",
  },
  {
    ad: "G2: printStackTrace ile istisna (adres icerir) logcat'e",
    dosya: `${KT}/ag/HttpIstek.kt`,
    bul: 'throw AgHatasi("cleartext")',
    koy: 'e.printStackTrace(); throw AgHatasi("cleartext")',
    test: "test/gizlilik.test.js",
  },
  {
    ad: "G3: console.trace taranan dosyada (yontem listesi: log|info|warn|error|debug)",
    dosya: "src/cekirdek/kesif.js",
    bul: "    const t0 = simdi();",
    koy: "    const t0 = simdi(); console.trace(elle, beklenenKimlik);",
    test: "test/gizlilik.test.js",
  },
  {
    ad: "G4: console.log TARANMAYAN dosyada (giris.js; 5P P6'dan once main.js — dosya listesi elle yaziliydi)",
    dosya: "src/giris.js",
    bul: "\nbasla();",
    koy: "\nconsole.log(localStorage.getItem('kart.son')); basla();",
    test: "test/gizlilik.test.js",
  },
  // --- gizlilik.test.js: "uretim kodunda WebView'in kendi ag cagrisi yok" ---
  {
    ad: "G5: fetch dolayli cagriliyor (desen \\bfetch\\( ariyor)",
    dosya: "src/cekirdek/kesif.js",
    bul: "    const t0 = simdi();",
    koy: '    const t0 = simdi(); const f = globalThis["fetch"]; f("http://example.com/").catch(() => {});',
    test: "test/gizlilik.test.js",
  },
  {
    ad: "G6: WebRTC ile disari paket (CSP ve shouldInterceptRequest kapsamaz; desen listesinde yok)",
    dosya: "src/cekirdek/kesif.js",
    bul: "    const t0 = simdi();",
    koy: '    const t0 = simdi(); new RTCPeerConnection({ iceServers: [{ urls: "stun:example.com" }] }).createDataChannel("x");',
    test: "test/gizlilik.test.js",
  },
  // --- gizlilik.test.js: "yerel kapi: MainActivity her istegi ... WebKapi'den geciriyor" (metin eslestirme) ---
  {
    ad: "G7: WebKapi istemcisi hic takilmiyor (olu kod) — test yalniz metnin VARLIGINA bakiyor",
    dosya: `${KT}/MainActivity.java`,
    bul: "        bridge.setWebViewClient(new BridgeWebViewClient(bridge) {",
    koy: "        if (savedInstanceState == this.getIntent().getExtras() && false) bridge.setWebViewClient(new BridgeWebViewClient(bridge) {",
    test: "test/gizlilik.test.js",
  },
  // --- sozluk.test.js: "ekrana gomulu metin yok" ---
  {
    ad: "S1: bagli ozellikte duz metin (:helper-text=\"'...'\")",
    dosya: "src/telefon/KartBolumu.vue",
    bul: 'inputmode="url"',
    koy: 'inputmode="url" :title="\'Kartın adresini yazın\'"',
    test: "test/sozluk.test.js",
  },
  {
    ad: "S2: v-text ile gomulu metin",
    dosya: "src/telefon/KartBolumu.vue",
    bul: "<p v-if=\"bulunamadi\" class=\"ipucu\" data-bt-tani-ipucu>{{ t('m.bt.bulunamadi_ipucu') }}</p>",
    koy: "<p v-if=\"bulunamadi\" class=\"ipucu\" data-bt-tani-ipucu>{{ t('m.bt.bulunamadi_ipucu') }}</p><p v-text=\"'Kart bulunamadı'\"></p>",
    test: "test/sozluk.test.js",
  },
  {
    ad: "S3: tek tirnakli duz ozellik (title='...')",
    dosya: "src/telefon/KartBolumu.vue",
    bul: '<h2 id="bt-kart-baslik">',
    koy: "<h2 id=\"bt-kart-baslik\" title='Kartı bul'>",
    test: "test/sozluk.test.js",
  },
  {
    ad: "S4: betikten ekrana giden sabit metin",
    dosya: "src/telefon/KartBolumu.vue",
    bul: "export default KART_BOLUMU;",
    koy: 'export default { ...KART_BOLUMU, title: "Kartı bul — tekrar deneyin" };',
    test: "test/sozluk.test.js",
  },
  {
    ad: "S5: {{ }} icinde dizgi sabiti",
    dosya: "src/telefon/KartBolumu.vue",
    bul: "{{ t('m.ay.kart') }}</h2>",
    koy: "{{ t('m.ay.kart') }}{{ \" (deneme sürümü)\" }}</h2>",
    test: "test/sozluk.test.js",
  },
  // --- kesif.test.js ---
  {
    ad: "K1: NSD aday siniri (8) kalkti",
    dosya: "src/cekirdek/kesif.js",
    bul: ".sort((a, b) => puan(a) - puan(b)).slice(0, NSD_AZAMI_ADAY);",
    koy: ".sort((a, b) => puan(a) - puan(b));",
    test: "test/kesif.test.js",
  },
  {
    ad: "K2: eklentinin soyledigi adres hedef kuralindan GECMEDEN onbellege/sonuca yaziliyor",
    dosya: "src/cekirdek/kesif.js",
    bul: "try { adres = hedefYazi(hedefAyir(y.adres, { yerelDongu })); } catch { /* adayin adresi kalir */ }",
    koy: "adres = y.adres;",
    test: "test/kesif.test.js",
  },
  {
    ad: "K3: elle beklenirken ILK degil SON uygun aday yedek oluyor",
    dosya: "src/cekirdek/kesif.js",
    bul: "if (elleBekliyor) yedek = yedek || s; else kapat(s);",
    koy: "if (elleBekliyor) yedek = s; else kapat(s);",
    test: "test/kesif.test.js",
  },
  // --- ag.test.js ---
  {
    ad: "A1: yol karakter kumesi satir sonu disinda her seye acildi (sekme, kontrol, ASCII disi)",
    dosya: "src/cekirdek/ag.js",
    bul: "(\\/[\\x21-\\x7e]*)?$/",
    koy: "(\\/[^ ]*)?$/",
    test: "test/ag.test.js",
  },
];
