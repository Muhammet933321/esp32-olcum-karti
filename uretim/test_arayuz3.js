/* ═══════════════════════════════════════════════════════════════════════
   B7 — Asama 3 arayuzu   (node uretim/test_arayuz3.js)

   Iki is yapiyor:

   1) ARAYUZ <-> FIRMWARE KOMUT DENETIMI
      Arayuzun gonderebilecegi HER komut harfini, firmware'in gercekten
      tanidigi `case` harfleriyle karsilastirir.

      NEDEN: Asama 2'de bu tam olarak ters gitti. DEVIR 4.1 app.js'teki
      uc komutu duzeltti ama index.html'deki UCUNU ATLADI:
          "Ayarlari goster" -> 'd'   (boyle bir komut yok, '?' olmali)
          "Enerjiyi sifirla" -> 'e'  (Asama 2'de enerji sifirlama YOK)
          "Akimi sifirla"   -> 's'   (o SONT komutu, 'z' olmali)
      Uc dugme sessizce calismiyordu ve hicbir test bunu gormuyordu,
      cunku testler yalnizca app.js'e bakiyordu. Bu test HTML'e de bakiyor.

   2) ASAMA 3 PROTOKOLU
      9 alanli D satiri, <menzil> alani, cift yonlu degerler, negatif guc.
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const KOK = path.join(__dirname, '..');
const ARAYUZ = path.join(KOK, 'arayuz3');
const APP = path.join(ARAYUZ, 'app.js');
const HTML = path.join(ARAYUZ, 'index.html');
const INO = path.join(KOK, 'kod', 'olcum-karti-a3', 'olcum-karti-a3.ino');

// ── Vue taklidi
let secenekler = null;
const sandbox = {
  Vue: { createApp(o) { secenekler = o; return { mount() { return {}; } }; } },
  navigator: { serial: {} },
  window: { addEventListener() {}, devicePixelRatio: 1 },
  document: { documentElement: {}, createElement: () => ({ click() {} }) },
  getComputedStyle: () => ({ getPropertyValue: () => '#000' }),
  setTimeout: () => 0,
  console,
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(APP, 'utf8'), sandbox, { filename: 'app.js' });

function ornek() {
  const o = Object.assign({}, secenekler.data());
  Object.assign(o, secenekler.methods);
  o.$nextTick = () => {};
  o.$refs = {};
  o.grafikCiz = () => {};
  o.osiloCiz = () => {};
  for (const [ad, fn] of Object.entries(secenekler.computed || {})) {
    Object.defineProperty(o, ad, { get: fn.bind(o) });
  }
  return o;
}

/* [!] ASENKRON IDDIA KUYRUGU (B27 A2).
   Bir `.then()` icinde yazilan `ok()` OZET SATIRINDAN SONRA kosuyordu:
   sayilmiyor, kirmizi olsa bile surec 0 ile cikiyordu — yani iddia
   degil, susleme. Asenkron iddialar buraya birakiliyor ve ozetten ONCE
   (bolum 12'nin zincirinde) bekleniyor. */
const SONRA = [];

let gecti = 0, kaldi = 0;
function ok(ad, kosul, ek = '') {
  if (kosul) { gecti++; console.log(`[OK] ${ad}${ek ? '  ' + ek : ''}`); }
  else { kaldi++; console.log(`[!!] ${ad}${ek ? '  ' + ek : ''}`); }
}
function yakin(ad, a, b, tol = 1e-9) {
  ok(ad, Math.abs(a - b) <= tol, `${a} ~ ${b}`);
}

console.log('B7 — Asama 3 arayuzu (arayuz3/)\n');

/* ═════════════════ 1. ARAYUZ <-> FIRMWARE KOMUT DENETIMI ═════════════ */
console.log('--- 1. Arayuzun gonderdigi her komut firmwarece taniniyor mu ---');

const ino = fs.readFileSync(INO, 'utf8');
const firmwareHarfleri = new Set(
  [...ino.matchAll(/case '(.)':/g)].map((m) => m[1])
);
console.log('     firmware: ' + [...firmwareHarfleri].sort().join(' '));

/* Arayuzun gonderdikleri — HEM app.js HEM index.html taranıyor.
   Asama 2'de yalnizca app.js taranmisti ve index.html'deki uc hatali
   komut fark edilmemisti. */
const appKaynak = fs.readFileSync(APP, 'utf8');
const htmlKaynak = fs.readFileSync(HTML, 'utf8');

/* Sayfanin BAGLADIGI stil dosyalari — elle liste degil. Bir stil dosyasi
   eklenir/cikarilirsa butun CSS iddialari kendiliginden onu izler. */
const CSS_YOLLARI = [...htmlKaynak.matchAll(
  /<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"/g)]
  .map((m) => m[1])
  .filter((u) => !/^https?:/.test(u))
  .map((u) => path.join(ARAYUZ, u));
const cssOku = () => CSS_YOLLARI.filter((p) => fs.existsSync(p))
  .map((p) => fs.readFileSync(p, 'utf8')).join('\n');

/* [!] B22.2: YORUMLAR CIKARILIYOR.
   Bir yorumda ornek olarak `gonder('x')` yazmak, komutu GONDERMEK degildir.
   B22.2'de tasiyici katmaninin aciklama yorumu tam olarak bunu yaziyordu ve
   ileri yon denetimi "arayuz 'x' komutu gonderiyor, firmware'de yok" diye
   kirmiziya dondu. Tersi daha kotu olurdu: firmware'e eklenip arayuze
   konmamis bir komut, YALNIZCA bir yorumda adi geciyor diye "erisilebilir"
   sayilabilirdi — ters yon denetiminin butun degeri kaybolurdu.
   (Ayni sinif kusur bu oturumda CSS sinifi, NVS imzasi ve `faz_kal` alani
   denetimlerinde de cikti. Metin tabanli her iddia KODA bakmali.) */
function yorumsuz(kaynak) {
  return kaynak
    .replace(/\/\*[\s\S]*?\*\//g, ' ')     // /* ... */
    .replace(/<!--[\s\S]*?-->/g, ' ')      // <!-- ... -->  (index.html)
    .replace(/^\s*\/\/.*$/gm, ' ');        // satir basindaki //
}

function komutlariTopla(ham, etiket) {
  const kaynak = yorumsuz(ham);
  const bulunan = [];
  // gonder('x'...)  ve  komut('x')  bicimleri
  for (const m of kaynak.matchAll(/(?:gonder|komut)\(\s*'([^']*)'/g)) {
    bulunan.push({ k: m[1], nerede: etiket });
  }
  /* [!] B20: yukaridaki kalip cagrinin ILK karakterinin tirnak olmasini
     istiyor, o yuzden UCLU ifadeleri kaciriyordu:
         this.gonder(m === 1 ? 'y' : 'n')
     'n' ve 'y' bu yuzden "arayuzde yok" gorunuyordu. Ikinci gecis,
     cagri parantezinin ICINDEKI butun tirnakli sabitleri topluyor. */
  for (const m of kaynak.matchAll(/(?:gonder|komut)\(([^)]*)\)/g)) {
    for (const q of m[1].matchAll(/'([^']*)'/g)) {
      /* Yalnizca HARFLE baslayanlar komut olabilir: `gonder('a' + ...)`
         cagrisindaki '1' / '0' komut degil ARGUMAN. Firmware'in butun
         komut harfleri A-Z / a-z. */
      if (q[1] && /^[A-Za-z]/.test(q[1])
          && !bulunan.some((b) => b.k === q[1])) {
        bulunan.push({ k: q[1], nerede: etiket + ' (uclu)' });
      }
    }
  }
  return bulunan;
}

const gonderilenler = komutlariTopla(appKaynak, 'app.js')
  .concat(komutlariTopla(htmlKaynak, 'index.html'));

ok('Arayuzde komut gonderen cagri bulundu', gonderilenler.length > 0,
   `${gonderilenler.length} cagri`);

const bilinmeyen = [];
for (const { k, nerede } of gonderilenler) {
  if (!k) continue;                       // gonder(degisken) — atlanir
  const harf = k[0];
  if (!firmwareHarfleri.has(harf)) bilinmeyen.push(`${nerede}: '${k}'`);
}
ok('Arayuzun gonderdigi HER komut firmware\'de tanimli',
   bilinmeyen.length === 0,
   bilinmeyen.length ? bilinmeyen.join(', ') : `${gonderilenler.length} cagri denetlendi`);

/* [!] B20 (2026-09-10) — TERS YON. Yukarisi yalnizca "arayuzun gonderdigi
   her komut firmware'de var mi" diye soruyordu. Bu denetim TEK YONLU
   oldugu icin, firmware'e YENI bir komut eklenip arayuze konmamasi
   GORUNMUYORDU: B17 `f` (sebeke frekansi) ve `F` (faz kalibrasyonu)
   komutlarini ekledi, arayuze hic koymadi ve zincir 70/70 yesildi.
   Sonucu sessiz degildi: fabrika ayari 50 Hz oldugu icin DC olcen bir
   kullanici gucu %82 yuksek okuyor ve duzeltecek denetim bulamiyordu. */
const gonderilenHarfler = new Set(
  gonderilenler.map((x) => (x.k || '')[0]).filter(Boolean));
/* Kullaniciya acik OLMAYAN komutlar — arayuzde bulunmalari beklenmiyor.
   Her biri icin GEREKCE yazili; listeye bir harf eklemek bilincli bir
   karar olmali. */
const ARAYUZSUZ = {
  h: 'yardim — seri port icin',
  /* B34: `c<ham>` ham ADC kodunun fabrika-kalibre mV karsiligini veren
     bir SORGU. Arayuzun elinde hic ham kod olmuyor — kart `/skop.bin`'de
     ham kod + TEK olcek carpani yolluyor ve arayuz volta o carpanla
     ceviriyor. Bu komut olcum betikleri icin var: olculmus bir supurmeyi
     KAYNAGI DEGISTIRMEDEN kalibrasyondan gecirmeye yariyor (B34'te
     "egri ADC'nin mi kaynagin mi" sorusu boyle yanitlandi).
     ⚠ Kalibrasyon skop eksenine uygulanirsa (DEVIR 5.12.48'deki acik
     karar) bu satir DUSMELI: o zaman arayuzun da bir soyleyecegi olur. */
  c: 'ham kod -> kalibre mV sorgusu; olcum betikleri icin',
  Y: 'yardim (es anlamli)',
  /* B26: TEZGAH TESHIS komutu — blokaj sayaclarini sifirlar.
     `tezgah_kart.py` bununla acilis isinmasini disarida birakip
     KARARLI HAL olcuyor (cift cekirdek karari, DEVIR 5.12.34).

     Neden B20'nin `f`/`F` durumundan FARKLI: o ikisi kullanicinin
     OKUDUGU degeri degistiriyordu (sebeke frekansi yanlis kalinca guc
     %82 yanlis okunuyordu), yani arayuzde olmamalari gercek bir kusurdu.
     `K` hicbir olcumu, kalibrasyonu ya da gosterilen degeri
     degistirmiyor — yalnizca teshis sayaclarini sifirliyor. Arayuzde
     blokaj sayaci PANELI de yok; olsaydi dugmesi oraya konurdu.
     ⚠ Arayuze bir gun blokaj/tani paneli eklenirse bu harf listeden
     CIKARILACAK. */
  K: 'blokaj sayaci sifirlama — tezgah teshisi, olcumu etkilemiyor',
};
const arayuzdeYok = [...firmwareHarfleri]
  .filter((h) => !gonderilenHarfler.has(h) && !(h in ARAYUZSUZ));
ok('Firmware\'in HER kullanici komutu arayuzden erisilebilir',
   arayuzdeYok.length === 0,
   arayuzdeYok.length
     ? `arayuzde YOK: ${arayuzdeYok.map((h) => `'${h}'`).join(', ')}`
     : `${firmwareHarfleri.size} komut harfi, ${Object.keys(ARAYUZSUZ).length} tanesi bilerek disarida`);

/* B20: `f` ve `F` ozellikle sinaniyor — bu ikisi B17'de eklenip
   unutulmustu, bir daha ayni sekilde kaybolmasinlar. */
/* Bu iki iddia fonksiyonun VARLIGINI degil GOVDESINI siniyor: adi duran
   ama icinden gonder() cikarilmis bir fonksiyon testi kandirmasin. */
function govdeIcinde(kaynak, ad, aranan) {
  /* [!] B21: once `ad + '('` araniyordu ve bu, adin bir YORUMDA gecmesine
     kaniyordu — `pilCsvIndir` iddiasi bu yuzden yanlislikla kirmizi
     yandi (helper yorumu bulup bir SONRAKI fonksiyonun govdesine
     bakiyordu). Artik TANIM bicimi araniyor: satir basi + ad + '() {'.
     Bulunamazsa eski gevsek kalibba dusulyor (async/parametreli
     tanimlar icin). */
  let i = -1;
  for (const kalip of ['\n    ' + ad + '(', '\n    async ' + ad + '(',
                       '\n  ' + ad + '(', '\n  async ' + ad + '(']) {
    const k = kaynak.indexOf(kalip);
    if (k >= 0 && (i < 0 || k < i)) i = k;
  }
  if (i < 0) i = kaynak.indexOf(ad + '(');
  if (i < 0) return false;
  const j = kaynak.indexOf('{', i);
  if (j < 0) return false;
  let d = 0;
  for (let k = j; k < kaynak.length; k++) {
    if (kaynak[k] === '{') d++;
    else if (kaynak[k] === '}') { d--; if (d === 0)
      return kaynak.slice(j, k + 1).includes(aranan); }
  }
  return false;
}
ok('B20: sebeke frekansi `f` arayuzde',
   gonderilenHarfler.has('f') && govdeIcinde(appKaynak, 'sebekeGonder', "gonder('f'"),
   'olcek duzeltmesi kullaniciya acik');
ok('B20: faz kalibrasyonu `F` arayuzde',
   gonderilenHarfler.has('F') && govdeIcinde(appKaynak, 'fazGonder', "gonder('F'"),
   'menzil basina faz duzeltmesi kullaniciya acik');
ok('B20: olcek carpani kullaniciya GOSTERILIYOR',
   appKaynak.includes('sebekeUyari') && htmlKaynak.includes('sebekeUyari'),
   'DC olcumunde %82 hata artik gorunur');

/* ── B21: pil kapasite testi arayuzu ────────────────────────────────── */
ok('B21: testi baslatma `p1` arayuzde',
   govdeIcinde(appKaynak, 'pilBaslat', "gonder('p1')"),
   'kesme denetimi kartta, ama tetigi arayuz cekiyor');
ok('B21: testi durdurma `p0` arayuzde',
   govdeIcinde(appKaynak, 'pilDurdurKomut', "gonder('p0')"),
   'kullanici her an durdurabiliyor');
ok('B21: kesme gerilimi `P` arayuzde',
   govdeIcinde(appKaynak, 'pilKesmeGonder', "gonder('P'"),
   'kesme gerilimi kullanici tarafindan ayarlanabiliyor');
ok('B21: kesme girisi MOSFET Vdss sinirinda kirpiliyor',
   /v\s*<=\s*38\.5/.test(appKaynak),
   'arayuz 38.5 V ustunu gondermiyor (firmware de ayrica reddediyor)');
/* Bu iddia adin GECTIGINI degil, boslugun GERCEKTEN SAYILDIGINI ve
   grafige ISARET olarak konuldugunu siniyor — yoksa degisken adini
   birakip mantigi silmek testi kandirirdi. */
ok('B21: [!] BOSLUK kullaniciya GOSTERILIYOR',
   govdeIcinde(appKaynak, 'pilYokla', 'this.pilBosluk +=')
   && govdeIcinde(appKaynak, 'pilYokla', 'bosluk: true')
   && htmlKaynak.includes('pilBosluk'),
   'kart penceresinden uzun kopmada egride bosluk olur — sessizce '
   + 'interpolasyon YAPILMIYOR, sayilip isaretleniyor');
ok('B21: [!] J7/J3 montaj tuzagi arayuzde YAZIYOR',
   /J7/.test(htmlKaynak) && /J3/.test(htmlKaynak),
   'yuk J3\'e baglanirsa kesme calismaz — kullanici bunu gormeli');
ok('B21: veri IndexedDB\'de (sekme kapansa da kalir)',
   appKaynak.includes('indexedDB.open'),
   'localStorage 5 MB ile sinirli; 24 saatlik test sigmaz');
ok('B21: CSV disari aktarma var',
   govdeIcinde(appKaynak, 'pilCsvIndir', 'text/csv'),
   'IndexedDB tarayici verisi — "verileri temizle" denince gider, '
   + 'ASIL ARSIV CSV');

/* ── B22.1 ─────────────────────────────────────────────────────────────
   Faz kalibrasyonunun BIRIMI ornek -> mikrosaniye oldu (K2). Bu, ters yon
   komut denetiminin GOREMEYECEGI bir ayrisma sinifi: harf ('F') iki
   tarafta da duruyor, degisen ANLAM. Arayuz +-1 ile kirpmaya devam
   etseydi kullanici 292 us'lik gercek duzeltmeyi HIC giremezdi ve sebebi
   gorunmezdi (eski govde sinir disi degeri sessizce yutuyordu). */
ok('B22.1: faz kalibrasyonu arayuzde MIKROSANIYE',
   govdeIcinde(appKaynak, 'fazGonder', '2000') &&
   !govdeIcinde(appKaynak, 'fazGonder', 'd >= -1 && d <= 1'),
   'firmware siniri +-2000 us — arayuz ayni siniri kullanmali');
ok('B22.1: faz birimi SABLONDA da us yaziyor',
   /Faz kalibrasyonu[^<]*µs/.test(htmlKaynak) &&
   !/Faz kalibrasyonu, örnek/.test(htmlKaynak),
   'etiket "ornek" derse kullanici 0.02 girer, 75 kat kucuk duzeltme');
/* IKI ret yolu var: sayi degil, ve sinir disi. Tek `this.hata` aramak
   yetmiyordu — sinir disi dalinin mesajini silen mutasyon KACTI. */
ok('B22.1: fazGonder HER ret yolunda sebebini soyluyor',
   govdeIcinde(appKaynak, 'fazGonder', 'sayı girin') &&
   govdeIcinde(appKaynak, 'fazGonder', '2000 µs arası olmalı'),
   'sayi-degil ve sinir-disi AYRI AYRI bildiriliyor; tek `this.hata` '
   + 'aramak yetmiyordu (mutasyon kacmisti)');

/* `R!` fabrika sifirlama — bozulmus NVS'ten tek kurtulus yolu.
   Onay eki hem firmware'de hem arayuzde: kazara tetiklenmemeli. */
ok('B22.1: fabrika sifirlama arayuzden erisilebilir',
   govdeIcinde(appKaynak, 'fabrikaSifirla', "gonder('R!')"),
   'ciplak `R` firmware\'de reddediliyor, onay eki sart');
/* Bayragin ADININ gecmesi yetmez — ERKEN DONUS kapisi durmali. Ilk
   yazimda `sifirlaOnay` aranıyordu ve "onayi kaldir" mutasyonu KACTI:
   kapi silinse bile govdede `this.sifirlaOnay = false;` duruyordu. */
/* ── B22.4: AG KURULUMU ────────────────────────────────────────────────
   Kartin WiFi'sini kartin WiFi'si uzerinden kurmak tavuk-yumurta olurdu;
   akis USB ile baglanip ag bilgilerini yazmak. Ters yon denetimi `N`
   harfini zaten zorunlu kiliyor, bu iddialar HANGI alt komutlarin
   erisilebildigini civiliyor. */
ok('B22.4: ag adi ve parolasi arayuzden yazilabiliyor',
   govdeIcinde(appKaynak, 'agSsidGonder', "gonder('Na'") &&
   govdeIcinde(appKaynak, 'agSifreGonder', "gonder('Np'"),
   'USB ile bagla, WiFi kur, sonra kablosuza gec');
ok('B22.4: web parolasi arayuzden kurulabiliyor',
   govdeIcinde(appKaynak, 'agWebSifreGonder', "gonder('Ns'"),
   'komut ucunun tek parola korumasi');
ok('B22.4: ag durumu ve ac/kapa sablonda',
   htmlKaynak.includes("komut('N?')") && htmlKaynak.includes("komut('N1')") &&
   htmlKaynak.includes("komut('N0')"));
/* Parolalar duz metin gidiyor — kart TLS konusmuyor. Kullanici ag
   uzerinden kuruyorsa bunu BILMELI. */
ok('B22.4: ag uzerinden kurulumda duz metin UYARISI var',
   /tasiyiciAdi !== 'seri'[\s\S]{0,400}şifrelenmeden/.test(htmlKaynak),
   'USB disinda parola duz metin gidiyor');

/* ── B22.5: IKI COZUCU, TEK GOSTERICI ──────────────────────────────────
   ASCII dokumu 4000 ornekte 20 250 B; ikili 8 032 B. Ikisi de AYNI
   `osiloTopla` yapisini kurup AYNI `osiloBitir()`i cagirmali — cizim
   kodu iki kez yazilsaydi ikisi ayrisir ve BIRI SESSIZCE YANLIS cizerdi
   (bu projenin uc kez yandigi sinif). */
ok('B22.5: ikili skop cozucusu var',
   govdeIcinde(appKaynak, 'skopIkiliAl', '/skop.bin'));
ok('B22.5: iki cozucu de AYNI gostericiyi cagiriyor',
   govdeIcinde(appKaynak, 'skopIkiliCoz', 'osiloBitir()') &&
   appKaynak.includes("satir.trim() === 'E'"),
   'ikili yol da osiloBitir(), ASCII yol da');
ok('B22.5: yakalama YETENEGE gore yol seciyor',
   govdeIcinde(appKaynak, 'osiloYakala', "yetenek.skop === 'ikili'") &&
   govdeIcinde(appKaynak, 'osiloYakala', "gonder('tB')"),
   'ayni veriyi ASCII + ikili olarak IKI KEZ tasima');
/* Kismi ya da yanlis yanit SESSIZCE cizilmemeli — bu, `pilYokla`'nin
   B22.2'de kapatilan sessiz-sifir kusurunun ikili karsiligi. */
ok('B22.5: ikili yanit IMZASI denetleniyor',
   govdeIcinde(appKaynak, 'skopIkiliCoz', '0x53') &&
   govdeIcinde(appKaynak, 'skopIkiliCoz', 'imzası'),
   'S3B degilse cizme, SEBEBINI soyle');
ok('B22.5: ikili yanit UZUNLUGU denetleniyor',
   govdeIcinde(appKaynak, 'skopIkiliCoz', '32 + adet * 2'),
   'kesik govde sessizce yarim grafik cizmesin');
/* [!] Endian ACIKCA kucuk: `Uint16Array` platformun endian'ini kullanir
   ve bir gun sessizce ters okuyabilirdi. */
ok('B22.5: endian ACIKCA kucuk-endian',
   govdeIcinde(appKaynak, 'skopIkiliCoz', 'getUint16(32 + i * 2, true)') &&
   !govdeIcinde(appKaynak, 'skopIkiliCoz', 'new Uint16Array'),
   'DataView + true; Uint16Array platforma birakirdi');

ok('B22.1: fabrika sifirlama IKI ASAMALI onay istiyor',
   govdeIcinde(appKaynak, 'fabrikaSifirla', 'if (!this.sifirlaOnay)') &&
   govdeIcinde(appKaynak, 'fabrikaSifirla', 'return;') &&
   htmlKaynak.includes('sifirlaOnay'),
   'tek tikla tum kalibrasyon silinmemeli');

/* Asama 2'nin hatalarinin tekrarlanmadigini ACIKCA sina */
const tumKomutlar = gonderilenler.map((x) => x.k);
ok('Ayarlari goster `?` gonderiyor (Asama 2\'de `d` idi — komut yok)',
   tumKomutlar.includes('?') && !tumKomutlar.includes('d'));
ok('Akimi sifirla `Z` gonderiyor (Asama 2\'de `s` idi — o sont komutu)',
   tumKomutlar.includes('Z'));
ok('Gerilim kalibresi `g` (Asama 2\'de `v` idi)',
   appKaynak.includes("gonder('g' + v)"));
ok('Gerilim sifiri `z` — Asama 3\'te AKIM degil GERILIM sifiri',
   appKaynak.includes("sifirlaV() { this.gonder('z'); }"));

/* ═════════════════ 2. ASAMA 3 PROTOKOLU ═════════════════════════════ */
console.log('\n--- 2. D satiri: 9 alan ve <menzil> ---');
{
  const u = ornek();
  u.satirIsle('D 12.3456 0.025300 0.312345 1.2340 0.0003428 45678 172 0');
  yakin('volt', u.volt, 12.3456);
  yakin('amper', u.amper, 0.0253);
  yakin('watt', u.watt, 0.312345);
  ok('ornek sayisi', u.ornekAdet === 172, String(u.ornekAdet));
  ok('menzil = 0 (NORMAL)', u.menzil === 0, String(u.menzil));
  ok('menzil adi NORMAL', u.menzilAd === 'NORMAL', u.menzilAd);
  ok('menzil araligi gosteriliyor', u.menzilAralik.includes('32.44'),
     u.menzilAralik);

  u.satirIsle('D 480.5 1.2 576.6 100.0 0.0277 46678 172 1');
  ok('menzil = 1 (YUKSEK)', u.menzil === 1, String(u.menzil));
  ok('menzil adi YUKSEK', u.menzilAd === 'YÜKSEK', u.menzilAd);
  ok('yuksek menzil araligi', u.menzilAralik.includes('613.7'), u.menzilAralik);
}

console.log('\n--- 3. ASAMA 2 satiri da bozulmadan okunmali (8 alan) ---');
{
  const u = ornek();
  u.satirIsle('D 12.3456 0.025300 0.312345 1.2340 0.0003428 45678 172');
  yakin('volt yine okunuyor', u.volt, 12.3456);
  ok('menzil bilinmiyor -> null', u.menzil === null, String(u.menzil));
  ok('menzil adi "—"', u.menzilAd === '—', u.menzilAd);
}

console.log('\n--- 4. CIFT YONLU gosterim ---');
{
  const u = ornek();
  u.satirIsle('D -24.5000 -0.150000 3.67500 -5.0 -0.00139 1000 172 0');
  ok('negatif gerilim okundu', u.volt < 0, String(u.volt));
  ok('negatif akim okundu', u.amper < 0, String(u.amper));
  ok('negatif akim isaretiyle gosteriliyor',
     String(u.akimGoster).startsWith('-'), u.akimGoster);
  ok('akim birimi mA secildi', u.akimBirim === 'mA', u.akimBirim);
  ok('pozitif guc "yuk cekiyor"', u.gucYon === 'yük çekiyor', u.gucYon);

  // negatif guc: yuk kaynak durumuna gecmis
  u.satirIsle('D 12.0000 -0.150000 -1.80000 -5.0 -0.00139 1200 172 0');
  ok('negatif guc okundu', u.watt < 0, String(u.watt));
  ok('negatif guc "kaynak" diye isaretleniyor',
     u.gucYon.includes('kaynak'), u.gucYon);
  ok('negatif enerji okunabiliyor', u.joule < 0, String(u.joule));

  /* 🔴 B27/K1 — `durum` alani: ADC yanit vermeyince "veri yok".
     Gercek kartta tek ADS ile gorulen satir: `... 97 0 1` -> bit0 = V yok.
     Firmware sessizce 0 donup kalibrasyon sabitini ters cevirince ekranda
     "1.716 V" cikiyordu; arayuz bunu ARTIK olcum sanmamali. */
  u.satirIsle('D 1.7156 0.000012 0.00004 0.0000 0.0000000 67704 97 0 1');
  ok('durum=1: gerilim GECERSIZ isaretleniyor', u.voltGecersiz === true,
     `adsDurum=${u.adsDurum}`);
  ok('durum=1: akim hala GECERLI', u.amperGecersiz === false, '');
  ok('durum=1: guc gecersiz (V yoksa V*I de yok)', u.gucGecersiz === true, '');
  ok('durum=1: guc yonu etiketi BOS (sahte sayiya etiket yok)',
     u.gucYon === '', JSON.stringify(u.gucYon));
  u.satirIsle('D 12.0 0.5 6.0 1.0 0.0003 68000 97 0 2');
  ok('durum=2: akim GECERSIZ, gerilim gecerli',
     u.amperGecersiz === true && u.voltGecersiz === false, '');
  u.satirIsle('D 12.0 0.5 6.0 1.0 0.0003 68200 97 0 0');
  ok('durum=0: ikisi de gecerli', !u.voltGecersiz && !u.amperGecersiz, '');
  ok('eski firmware (9 alan) -> durum 0 sayilir (guven)',
     (u.satirIsle('D 12.0 0.5 6.0 1.0 0.0003 68400 97 0'), u.adsDurum === 0),
     `adsDurum=${u.adsDurum}`);

  /* B27/K5 — sont menusu KARTI gostermeli, tarayiciyi degil.
     Gercek kartin `?` cevabi (sont=0.100000) menude '0.1' secmeli;
     listede olmayan bir deger menuyu bozmamali ama gercek gorunmeli. */
  u.sontSecim = '10';
  u.satirIsle('A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=-1646 '
              + 'y_kazanc=1.000000 y_sifir=-91 sont=0.100000 i_duz=1.000000 i_ofset=0');
  ok('K5: `?` cevabindan kartSont okunuyor', u.kartSont === 0.1, String(u.kartSont));
  ok('K5: menu kartin degerine UYDURULUYOR (10 -> 0.1)', u.sontSecim === '0.1',
     u.sontSecim);
  ok('K5: uyusma var, uyari yok', u.sontUyumsuz === false, '');
  ok('K5: kart degeri yaziya dokuluyor', u.kartSontYazi.includes('100') && u.kartSontYazi.includes('mΩ'),
     u.kartSontYazi);
  u.satirIsle('A menzil=NORMAL oto=1 n_kazanc=1 n_sifir=0 y_kazanc=1 y_sifir=0 '
              + 'sont=0.123456 i_duz=1 i_ofset=0');
  ok('K5: listede olmayan deger menuyu DEGISTIRMIYOR', u.sontSecim === '0.1', u.sontSecim);
  ok('K5: ama uyusmazlik UYARILIYOR', u.sontUyumsuz === true, `kartSont=${u.kartSont}`);

  /* B27/K3 — kart "giris rayda" derse ESKI sonuc panelde kalmamali */
  u.satirIsle('W 218.11 218.47 0.9984 61.78 3.536 -61.37 -3.49 297 218.35');
  ok('K3: W satiri hizli sonucu dolduruyor', u.hizli !== null && u.hizli.p > 200,
     String(u.hizli && u.hizli.p));
  u.satirIsle('! hizli yol: giris RAYDA — sinyal yok  V ham ort=14  (bos giris ya da on uc bagli degil)');
  ok('K3: "giris rayda" gelince ESKI sonuc SILINIYOR', u.hizli === null, String(u.hizli));
  ok('K3: hata metni panelde', u.hizliHata.includes('RAYDA'), u.hizliHata);
  u.satirIsle('W 12.0 12.1 0.99 12.0 1.0 12.0 1.0 297 12.0');
  ok('K3: yeni gecerli W hatayi temizliyor', u.hizliHata === '' && u.hizli !== null, '');

  /* B27/K2 — olu bant: gurultu duzeyinde guc etiket URETMEMELI */
  u.satirIsle('D 1.7156 -0.000004 -0.00001 0 0 68600 97 0 0');
  ok('K2: -10 uW "kaynak" etiketi uretmiyor (olu bant)', u.gucYon === '',
     JSON.stringify(u.gucYon));
  u.satirIsle('D 12.0 -0.5 -6.0 0 0 68800 97 0 0');
  ok('K2: -6 W hala "kaynak" diyor (olu bant gercek geri beslemeyi yutmuyor)',
     u.gucYon.includes('kaynak'), u.gucYon);
}

console.log('\n--- 5. Kalibrasyon NEGATIF degeri kabul ediyor mu ---');
{
  const u = ornek();
  const gonderilen = [];
  u.gonder = (k) => gonderilen.push(k);

  u.kalibV = '12.05'; u.kalibreV();
  ok('pozitif gerilim kalibresi g12.05', gonderilen[0] === 'g12.05',
     gonderilen[0]);

  u.kalibV = '-24.5'; u.kalibreV();
  ok('NEGATIF gerilim kalibresi g-24.5 (Asama 2\'de reddedilirdi)',
     gonderilen[1] === 'g-24.5', gonderilen[1]);

  u.kalibA = '-0.25'; u.kalibreA();
  ok('NEGATIF akim kalibresi i-0.25', gonderilen[2] === 'i-0.25',
     gonderilen[2]);

  u.kalibV = '0'; u.kalibreV();
  ok('SIFIR kalibrasyon degeri gonderilmiyor', gonderilen.length === 3,
     `${gonderilen.length} komut`);

  u.sontSecim = '0.1'; u.sontGonder();
  ok('sont komutu s0.1', gonderilen[3] === 's0.1', gonderilen[3]);
  u.menzilSec(1);
  ok('menzil YUKSEK -> y', gonderilen[4] === 'y', gonderilen[4]);
  ok('menzil secince oto kapaniyor', u.otoMenzil === false);
  u.menzilSec(0);
  ok('menzil NORMAL -> n', gonderilen[5] === 'n', gonderilen[5]);
  u.otoMenzil = false; u.otoMenzilDegistir();
  ok('oto menzil acma -> a1', gonderilen[6] === 'a1', gonderilen[6]);
  u.otoMenzilDegistir();
  ok('oto menzil kapatma -> a0', gonderilen[7] === 'a0', gonderilen[7]);
  u.sifirlaV();
  ok('gerilim sifiri -> z', gonderilen[8] === 'z', gonderilen[8]);
  u.sifirlaA();
  ok('akim sifiri -> Z', gonderilen[9] === 'Z', gonderilen[9]);
  u.enerjiSifirla();
  ok('enerji sifirla -> e', gonderilen[10] === 'e', gonderilen[10]);
}

console.log('\n--- 5b. B8 HIZLI YOL (W satiri) ---');
{
  const u = ornek();
  u.satirIsle('W 0.13712 0.22117 0.6200 12.0200 0.01840 12.0100 0.01820 297 0.15550');
  ok('W satiri ayristirildi', u.hizli !== null);
  yakin('gercek guc P', u.hizli.p, 0.13712, 1e-9);
  yakin('gorunur guc S', u.hizli.s, 0.22117, 1e-9);
  yakin('guc faktoru', u.hizli.pf, 0.62, 1e-9);
  yakin('Vrms', u.hizli.vRms, 12.02, 1e-9);
  ok('ornek sayisi', u.hizli.n === 297, String(u.hizli.n));
  yakin('hizalamasiz guc AYRI alanda', u.hizli.pHam, 0.1555, 1e-9);
  ok('hizalama farki gosteriliyor', /düzeltti/.test(u.hizalamaFarki),
     u.hizalamaFarki);

  // Dirençsel yukte hizalamali ve hizalamasiz AYNI olmali
  u.satirIsle('W 1.00000 1.00000 1.0000 10.0000 0.10000 10.0 0.1 297 1.00000');
  ok('Dirençsel yukte "fark yok" deniyor',
     /yok \(dirençsel\)/.test(u.hizalamaFarki), u.hizalamaFarki);

  const gonderilen = [];
  u.gonder = (k) => gonderilen.push(k);
  u.hizliOlc();
  ok('hizli olcum komutu `w`', gonderilen[0] === 'w', gonderilen[0]);
}

console.log('\n--- 6. Demo kart Asama 3 protokolu uretiyor mu ---');
{
  const SahteKart = require(path.join(ARAYUZ, 'sahte-kart.js'));
  const d = SahteKart.dSatiri(1000, 1.5);
  const p = d.satir.split(/\s+/);
  /* 🔴 B27: burasi `p.length === 9` idi — firmware'e alan eklenince (K1
     `durum`) demo kart guncellendi ama bu sabit kaldi ve YANLIS KIRMIZI
     verdi. Beklenen, firmware'in KENDI bicim dizesinden turetiliyor:
     "D " + N adet % => N+1 alan. Demo kart firmware'den sapinca burasi
     kirmizi olur; sabit bir sayi ise firmware degisince kirmizi olurdu. */
  const dBicim = ino.match(/"D (%[^"]*)"/);
  const alanBeklenen = dBicim ? dBicim[1].split(/\s+/).length + 1 : -1;
  ok(`D satiri ${alanBeklenen} alanli (firmware bicim dizesinden)`,
     p.length === alanBeklenen, `${p.length} alan: ${d.satir}`);
  ok('9. alan menzil', p[8] === '0' || p[8] === '1', p[8]);
  ok('10. alan durum (ADC yanit bitleri, demo kartta 0)', p[9] === '0',
     `durum=${p[9]} — demo kartta iki ADC de "var"`);

  const u = ornek();
  u.satirIsle(d.satir);
  ok('arayuz demo satirini ayristirdi', isFinite(u.volt) && u.menzil !== null,
     `${u.volt} V, menzil ${u.menzil}`);

  // demo kart bilinmeyen komutu reddediyor mu
  ok('demo kart `d` komutunu REDDEDIYOR (Asama 2 hatasi)',
     SahteKart.komut('d')[0].startsWith('!'), SahteKart.komut('d')[0]);
  ok('demo kart `?` komutunu taniyor',
     SahteKart.komut('?')[0].startsWith('A '), SahteKart.komut('?')[0]);
  ok('demo kart `Z` (akim sifiri) taniyor',
     SahteKart.komut('Z')[0].includes('akim sifiri'), SahteKart.komut('Z')[0]);
  ok('demo kart sifira yakin kazanc kalibresini reddediyor',
     SahteKart.komut('g0.5')[0].startsWith('!'), SahteKart.komut('g0.5')[0]);

  const w = SahteKart.komut('w');
  ok('demo kart `w` ile W satiri uretiyor', w[0].startsWith('W '), w[0]);
  /* B39: alan sayisi ELLE YAZILMIYOR, firmware'in protokol yorumundan
     (`//   W <P> ... <kal>`) TURETILIYOR. Elle 10 yazan onceki hali,
     firmware 11. alani ekleyince sahte karti geride birakacakti — ya da
     tersine, sahte kart guncellenip firmware unutulsaydi fark etmezdi. */
  const inoKaynak = fs.readFileSync(
    path.join(KOK, 'kod', 'olcum-karti-a3', 'olcum-karti-a3.ino'), 'utf8');
  const wProto = inoKaynak.match(/^\/\/\s+(W <[^\n]*>)\s*$/m);
  const wAlan = wProto ? wProto[1].trim().split(/\s+/).length : -1;
  ok('demo W satirinin alan sayisi FIRMWARE protokoluyle ayni',
     wAlan > 0 && w[0].split(/\s+/).length === wAlan,
     `demo ${w[0].split(/\s+/).length} · firmware ${wAlan} (${wProto ? wProto[1] : 'yorum yok'})`);
  ok('demo pencere yanliligini UYARIYOR', /yanlilik BUYUK/.test(w[1]), w[1]);
}

console.log('\n--- 7. Sablon: menzil ve guc yonu gosteriliyor mu ---');
{
  ok('menzilAd sablonda kullaniliyor', htmlKaynak.includes('menzilAd'));
  ok('menzilAralik sablonda kullaniliyor', htmlKaynak.includes('menzilAralik'));
  ok('gucYon sablonda kullaniliyor', htmlKaynak.includes('gucYon'));
  ok('menzil dugmeleri var', htmlKaynak.includes('menzilSec(0)') &&
     htmlKaynak.includes('menzilSec(1)'));
  ok('gerilim sifirlama dugmesi var', htmlKaynak.includes('sifirlaV'));
  ok('hizli olcum dugmesi var', htmlKaynak.includes('hizliOlc'));
  ok('hizalama farki sablonda', htmlKaynak.includes('hizalamaFarki'));
  /* Hizli yolun MUTLAK dogrulugu sinirli — arayuz bunu SOYLEMELI,
     yoksa kullanici ADS'in degeri yerine bu sayiya guvenir. */
  ok('mutlak deger uyarisi sablonda',
     htmlKaynak.includes('D satırı') && htmlKaynak.includes('ADS1115'));
  /* CSS tuzagi: display tanimlayan sinif [hidden] kuralini ezer. */
  ok('`button.etkin` icinde display kullanilmiyor ([hidden] tuzagi)',
     !/button\.etkin\s*\{[^}]*display/.test(cssOku()));
}

/* ═══════════════════════════════════════════════════════════════════════
   8. VARLIK DENETIMI  (B22.0, 2026-09-10)

   NEDEN EKLENDI: bu zincir 15/15 ve bu dosya 82/82 YESILKEN arayuz
   tarayicida HIC ACILMIYORDU. index.html `style.css` ve
   `vendor/vue.global.prod.js` istiyordu; ikisi de arayuz3/ icinde yoktu.
   sunucu.py onlari `../arayuz`'dan dusuruyordu, ama o dizin 5.12.32'de
   `arsiv/asama1/arayuz`'a tasinmisti. Sonuc: iki 404, Vue tanimsiz,
   app.js ilk satirinda ReferenceError, ekranda ham {{ }} sablonu.

   Hicbir test bunu goremedi cunku:
     * bu dosya Vue'yu KENDISI taklit ediyor, vendor dosyasina ihtiyaci yok
     * proje genelinde bir tane bile dosya-varlik denetimi yoktu
     * "ek.css bagli" denetimi bile yalnizca DIZENIN html'de gectigine
       bakiyor, dosyanin diskte oldugunu DEGIL

   Buradaki iddialar metin degil VARLIK sinaliyor: referans verilen dosya
   gercekten duruyor mu, kullanilan sinif gercekten tanimli mi.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 8. Varlik denetimi: referanslar diskte var mi ---');
{
  /* Dosyayi KOSULSUZ okumak yanlis: eksikse test cokuyor ve hangi iddianin
     dustugu gorunmuyor (yigin izi basiliyor). Once varligini SINA. */
  /* [!] B27 A2: CSS listesi ELLE yazilmiyor, index.html'den TURETILIYOR.
     Once ['style.css','ek.css'] sabitti; ek.css style.css'e katilinca
     test "diskte yok" diye coktu — ama daha kotusu tersi: sayfaya YENI
     bir stil dosyasi baglansa test onu hic gormezdi, yani "her sinif
     tanimli" iddiasi eksik kaynakla calisirdi. */
  const cssYollari = CSS_YOLLARI;
  ok('index.html en az bir stil dosyasi bagliyor', cssYollari.length >= 1,
     cssYollari.map((p) => path.basename(p)).join(' '));
  ok('bagli her stil dosyasi DISKTE var',
     cssYollari.every((p) => fs.existsSync(p)),
     cssYollari.filter((p) => !fs.existsSync(p)).join(' '));
  const oku = (p) => (fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '');

  /* [!] YORUMLAR CIKARILIYOR. Once cikarilmiyordu ve ".kpi kuralini sil"
     mutasyonu KACTI: ek.css'in kendi aciklama yorumunda ".kpi" gectigi icin
     sinif "tanimli" sayiliyordu. Bir iddianin kendi yorumuyla karsilanmasi,
     iddia olmadigi anlamina gelir. */
  const tumCss = cssYollari.map(oku).join('\n').replace(/\/\*[\s\S]*?\*\//g, '');

  /* (a) index.html'in her href/src'i arayuz3/ altinda duruyor mu.
         Disaridan (http) gelen varlik YOK — arayuz internetsiz calismali. */
  /* `(?:^|\s)` sart: `:href="kopruAdresi"` bir Vue BAGLAMASI, dosya yolu
     degil. Onsuz `:href` de eslesiyordu ve B22.2'de eklenen kopru
     baglantisi "diskte yok" diye kirmiziya dondu. */
  const referanslar = [...htmlKaynak.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)]
    .map((m) => m[1])
    .filter((u) => !/^(https?:|data:|#|mailto:)/.test(u));
  /* ⚠ IDDIA SAYISI SABIT TUTULUYOR — referans basina bir `ok()` YOK.
     Once oyleydi ve bir mutasyon kacti: statik <script src="sahte-kart.js">
     geri konunca BIR iddia basarisiz oldu ama AYNI ANDA bir referans (yani
     bir iddia) eklendi; toplam degismedi ve mutasyon gorunmez kaldi.
     Iddia sayisi girdiyle birlikte buyuyorsa, sayim tabanli her denetim
     (dogrula3.py'nin sayim kilidi dahil) korlesir. */
  ok('index.html en az 3 yerel varlik istiyor', referanslar.length >= 3,
     referanslar.join(' '));
  const eksikVarlik = referanslar.filter((r) => !fs.existsSync(path.join(ARAYUZ, r)));
  ok('index.html\'in her yerel varligi DISKTE var',
     eksikVarlik.length === 0, eksikVarlik.join(' ') || referanslar.length + ' referans');

  /* (b) sunucu.py arayuz3/ DISINA cikmiyor. K4'un mekanizmasi buydu:
         bulunamayan dosyayi baska bir dizinden servis etmek. O dizin
         tasininca kusur sessizce ortaya cikti. */
  const sunucu = fs.readFileSync(path.join(ARAYUZ, 'sunucu.py'), 'utf8');
  const govde = sunucu.replace(/"""[\s\S]*?"""/g, '');   // docstring haric
  ok('sunucu.py dizin disina dusme yapmiyor (K4 mekanizmasi)',
     !/BURASI\.parent/.test(govde) && !/translate_path/.test(govde));

  /* (c) sahte-kart.js STATIK baglanmamali — yalnizca ?demo'da dinamik
         iniyor. Kosulsuz baglanirsa 15 936 B her acilista bosuna iner ve
         B22.5'te LittleFS goruntusune de girer. */
  ok('sahte-kart.js statik <script> ile baglanmamis',
     !/<script[^>]+sahte-kart\.js/.test(htmlKaynak));
  ok('sahte-kart.js dinamik yukleniyor (betikYukle)',
     govdeIcinde(appKaynak, 'demoVeri', 'betikYukle') &&
     govdeIcinde(appKaynak, 'betikYukle', 'createElement'));
  /* Betik indikten SONRA demo bayragi acilmali; erken acilirsa gonder()'in
     demo dali SahteKart tanimsizken calisir. */
  /* B22.2: bayrak artik `tasiyiciAdi`. Sira hala onemli — tasiyici demoya
     gecince gonder() SahteKart'a yoneliyor, betik inmemisse tanimsiz. */
  ok('demo tasiyicisi betik yuklendikten SONRA seciliyor',
     govdeIcinde(appKaynak, 'demoVeri', 'await this.betikYukle') &&
     appKaynak.indexOf('await this.betikYukle') <
       appKaynak.indexOf("this.tasiyiciAdi = 'demo'"));

  /* (d) index.html'de STATIK kullanilan her sinif CSS'te tanimli mi.
         `:class="..."` Vue ifadesidir, sinif adi degil — (?:^|\s) onu
         disarida birakiyor; {} olan da sablon/nesne, sinif degil. */
  const siniflar = new Set();
  for (const m of htmlKaynak.matchAll(/(?:^|\s)class="([^"{}]+)"/g)) {
    for (const c of m[1].split(/\s+/)) if (/^[a-z][a-z0-9-]*$/.test(c)) siniflar.add(c);
  }
  /* Lookahead BUYUK HARFI de dislamali: `[a-z0-9-]` ile yazildiginda
     `.kpi` iddiasi `.kpiX` selektoruyle karsilanmis sayiliyordu ve
     "kurali sil" mutasyonu KACIYORDU (B22.0 mutasyon turu). */
  const tanimsizSinif = [...siniflar].filter(
    (c) => !new RegExp('\\.' + c + '(?![A-Za-z0-9_-])').test(tumCss));
  ok('index.html\'deki her statik sinif CSS\'te TANIMLI',
     tanimsizSinif.length === 0, tanimsizSinif.join(' '));

  /* Guvenlik uyarilari govde metninden ayirt edilebilmeli. .uyari
     tanimsizken "Yuku J7'ye baglayin, J3'e degil — yoksa MOSFET baypas
     olur ve KESME CALISMAZ" duz paragraf olarak goruntuleniyordu. */
  ok('J7/J3 baypas uyarisi .uyari sinifiyla isaretli',
     /class="uyari"[\s\S]{0,200}J7/.test(htmlKaynak));
  /* .uyari ile .hata GORSEL olarak ayrilmali: .hata gecici bir hatadir,
     .uyari kalici bir emniyet talimatidir. Ikisi ayni goruntuye sahipse
     kullanici emniyet uyarisini "gecmis bir hata" sanip gozardi eder.

     HAM METIN KARSILASTIRMASI YETMIYOR: iki kural ayri dosyalarda ve ayri
     girintide duruyor, yani govdeleri ANLAMCA ayni olsa bile metinleri
     farkli cikiyordu — "ikisini ayni yap" mutasyonu bu yuzden KACTI.
     Bildirimleri normallestirip KUME olarak karsilastiriyoruz. */
  const bildirimler = (kaynak, secici) => {
    const m = kaynak.match(new RegExp('\\' + secici + '\\s*\\{([^}]*)\\}'));
    if (!m) return null;
    return m[1].split(';').map((d) => d.replace(/\s+/g, ' ').trim().toLowerCase())
      .filter(Boolean).sort().join('|');
  };
  const bUyari = bildirimler(tumCss, '.uyari');
  const bHata = bildirimler(tumCss, '.hata');
  ok('.uyari gorsel olarak .hata\'dan AYRI tanimli',
     bUyari !== null && bHata !== null && bUyari !== bHata);

  /* (e) Yedeksiz var(--x) kullanimi tanimli mi. Tanimsiz olan sessizce
         gecersize duser: renk/kenarlik hic uygulanmaz, hata da vermez. */
  const tanimli = new Set(
    [...tumCss.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((m) => m[1]));
  const tanimsizDegisken = [...new Set(
    [...tumCss.matchAll(/var\((--[a-z0-9-]+)\)/g)].map((m) => m[1]))]
    .filter((v) => !tanimli.has(v));
  ok('yedeksiz her CSS degiskeni TANIMLI',
     tanimsizDegisken.length === 0, tanimsizDegisken.join(' '));
}

/* ═══════════════════════════════════════════════════════════════════════
   9. TASIYICI KATMANI (B22.2)

   Bu bolumun cogu METIN degil YAPI siniyor: tasiyicilar vm baglaminda
   gercekten olusturuluyor ve yuzeyleri karsilastiriliyor. Ucunun ayni
   yuzeyi sunmasi, "tek arayuz uc tasima" iddiasinin ta kendisi — biri
   otekilerden ayrisirsa panel kodu dallanmaya baslar ve bu proje tam
   olarak oradan uc kez yandi (DEVIR 4.1, 4.15, B17).
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 9. Tasiyici katmani: uc tasima, tek arayuz ---');
{
  const kod = yorumsuz(appKaynak);
  let T = null;
  try { T = vm.runInContext('TASIYICILAR', sandbox); } catch (e) { /* yok */ }

  ok('TASIYICILAR kaydi var', T && typeof T === 'object',
     T ? Object.keys(T).join(' ') : 'YOK');

  if (T) {
    const YUZEY = ['ad', 'yetenek', 'destekli', 'ac', 'kapat', 'gonder'];
    ok('Uc tasiyici kayitli (seri · akis · demo)',
       ['seri', 'akis', 'demo'].every((k) => k in T),
       Object.keys(T).join(' '));

    const eksik = [];
    for (const [k, t] of Object.entries(T)) {
      for (const y of YUZEY) if (!(y in t)) eksik.push(k + '.' + y);
    }
    ok('Her tasiyici AYNI yuzeyi sunuyor', eksik.length === 0,
       eksik.length ? eksik.join(' ') : YUZEY.join(' '));

    /* Yetenek tablosu da ayni SEKILDE olmali: bir tasiyicida olmayan
       alan, sablonda `undefined` olarak sessizce yanlis davranir. */
    const alanlar = Object.keys(T.seri.yetenek).sort().join(',');
    const ayrik = Object.entries(T)
      .filter(([, t]) => Object.keys(t.yetenek).sort().join(',') !== alanlar)
      .map(([k]) => k);
    ok('Yetenek tablolari AYNI alanlara sahip', ayrik.length === 0,
       ayrik.length ? 'ayrisan: ' + ayrik.join(' ') : alanlar);

    /* Modlar arasindaki farkin GERCEKTEN yetenek tablosunda yasadigini
       sina — hepsi ayni degerleri verseydi tablo susleme olurdu. */
    const gecmisler = new Set(Object.values(T).map((t) => t.yetenek.gecmis_s));
    ok('Yetenek tablosu modlari GERCEKTEN ayiriyor', gecmisler.size > 1,
       'gecmis_s: ' + [...gecmisler].join(' / '));
  }

  /* [!] Bu iddia, B22.0'da bulunan sessiz-sifir kusurunun tekrarlanamaz
     halidir: `pilYokla` goreli `fetch('/pil?…')` yapiyordu ve sayfa
     localhost:8772'den servis edildigi icin istek karta HIC gitmiyordu.
     404 govdesi `anahtar=deger` sanilip ayristiriliyor, tum KPI'lar
     sessizce 0 oluyordu. Artik her uzak istek kartAdres()'ten gecmeli. */
  const fetchler = [...kod.matchAll(/fetch\(([^,)]*)/g)].map((m) => m[1].trim());
  const kacak = fetchler.filter((a) => !a.includes('kartAdres('));
  ok('app.js\'te kartAdres() disinda fetch( YOK',
     kacak.length === 0,
     kacak.length ? kacak.join(' | ') : `${fetchler.length} istek, hepsi kartAdres()`);

  ok('kartAdres() taban onekini uyguluyor',
     govdeIcinde(appKaynak, 'kartAdres', 'kartTaban'),
     'bos taban = ayni koken; dolu taban = PC\'den karta dogrudan');

  ok('pilYokla yanit DURUMUNU denetliyor',
     govdeIcinde(appKaynak, 'pilYokla', 'y.ok'),
     'fetch 404\'te REDDETMEZ — denetlenmezse hata sayfasi ayristirilir');
  ok('pilYokla yanit BICIMINI denetliyor',
     govdeIcinde(appKaynak, 'pilYokla', "indexOf('durum=')"),
     'kismi yanit (kartta yigin sikismasi) tutarli Content-Length ile gelir');
  ok('pilYokla basarisizligi KULLANICIYA soyluyor',
     govdeIcinde(appKaynak, 'pilYokla', 'pilHataMetni') &&
     htmlKaynak.includes('pilHataMetni'),
     'sessiz sifir yerine sebep');

  /* Ayristiriciya tasiyiciya ozgu dal girmemeli: tel ustundeki baytlar
     her tasimada ayni oldugu icin tek ayristirici yetiyor. Dal acmak,
     baytlarin ayristigi anlamina gelir. */
  ok('satirIsle icinde tasiyiciya ozgu dal YOK',
     !govdeIcinde(appKaynak, 'satirIsle', 'tasiyiciAdi') &&
     !govdeIcinde(appKaynak, 'satirIsle', 'this.demo'),
     'ayni satirlar seri, akis ve sahte kartta birebir ayni');

  /* Tek kaynak: `demo` artik ayri bir bayrak degil, tasiyicidan turetilen
     computed. Iki bayrak tutmak DEVIR 4.1'in deseniydi. */
  ok('`demo` tasiyicidan TURETILIYOR, ayri bayrak degil',
     /demo\(\)\s*\{\s*return this\.tasiyiciAdi === 'demo'/.test(kod) &&
     !/^\s*demo:\s*false/m.test(kod),
     'tek kaynak');

  /* Tercih kaliciligi: bu alanlar her acilista yeniden giriliyordu. */
  ok('Tercihler localStorage\'da tutuluyor',
     govdeIcinde(appKaynak, 'ayarYaz', 'localStorage.setItem') &&
     govdeIcinde(appKaynak, 'ayarOku', 'localStorage.getItem'),
     'pencere · gostergeler · sont · sebeke Hz · adres · tasiyici');
  ok('localStorage erisimi try/catch icinde',
     govdeIcinde(appKaynak, 'ayarOku', 'catch') &&
     govdeIcinde(appKaynak, 'ayarYaz', 'catch'),
     'ozel kipte ve kota dolunca ERISIMIN KENDISI atiyor');
}

/* ═══════════════════════════════════════════════════════════════════════
   10. GORUNUMLER — hash yonlendirme (B27 Asama 1)

   Tek kaydirmali sayfa bes gorunume bolundu. Iki tuzak var ve ikisi de
   Vue taklidinde GORUNMEZ:
   (a) Gorunum `v-if` ile saklanirsa tuval YOK OLUR: gecmis kaybolmaz ama
       geri donunce bos bir grafik gelir, ilk D satirina kadar. `v-show`
       sart.
   (b) `display:none` tuval 0 genislik okur. Gorunum degisince yeniden
       cizilmezse skop/grafik 300x150 varsayilan olcude, sola yapisik
       kalir. Bu yuzden watch `gorunum` -> $nextTick -> grafikCiz+osiloCiz.
   Ikisi de headless Edge'de DOGRULANDI (nodemo-olcum,skop.png); burada
   yapi ve davranis civileniyor ki sonraki asamalarda kirilirsa gorulsun.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 10. Gorunumler: hash yonlendirme, v-show, yeniden cizim ---');
{
  const kod = yorumsuz(appKaynak);
  const html = yorumsuz(htmlKaynak);

  // app.js'teki liste ile index.html'deki v-show sarmallari BIREBIR ayni mi
  let G = null;
  try { G = vm.runInContext('GORUNUMLER', sandbox); } catch (e) { /* yok */ }
  const appIdler = G ? G.map((g) => g.id) : [];
  const htmlIdler = [...html.matchAll(/<main[^>]*v-show="gorunum === '([a-z]+)'"/g)]
    .map((m) => m[1]);
  ok('GORUNUMLER listesi var ve 5 gorunum tanimli',
     appIdler.length === 5, appIdler.join(' '));
  ok('index.html\'deki her <main v-show> app.js listesindeki bir gorunum',
     htmlIdler.length === appIdler.length &&
       htmlIdler.every((id) => appIdler.includes(id)) &&
       new Set(htmlIdler).size === htmlIdler.length,
     'html: ' + htmlIdler.join(' '));
  ok('Gorunumler v-show ile saklaniyor, v-if ile DEGIL (tuval canli kalsin)',
     !/<main[^>]*v-if="gorunum/.test(html) && htmlIdler.length === 5);

  // her gorunumun sekmesi var: nav, GORUNUMLER uzerinde v-for
  ok('Sekme seridi GORUNUMLER listesinden uretiliyor (elle kopya degil)',
     /<nav[^>]*class="gorunum-nav"[\s\S]{0,300}v-for="g in gorunumler"/.test(html) &&
       /gorunumler:\s*GORUNUMLER/.test(kod));

  // hash -> gorunum: bilinmeyen hash varsayilana duser, bilinen hash gecer
  let hashten = null;
  try { hashten = vm.runInContext('hashtenGorunum', sandbox); } catch (e) { /* yok */ }
  if (hashten) {
    const dene = (h) => { sandbox.location = { hash: h }; return hashten(); };
    ok('hashtenGorunum: #/skop -> skop', dene('#/skop') === 'skop');
    ok('hashtenGorunum: #skop (egik cizgisiz) -> skop', dene('#skop') === 'skop');
    ok('hashtenGorunum: bilinmeyen (#/yok) -> varsayilan olcum', dene('#/yok') === 'olcum');
    ok('hashtenGorunum: bos hash -> varsayilan olcum', dene('') === 'olcum');
    delete sandbox.location;
  } else {
    ok('hashtenGorunum fonksiyonu sandbox\'ta erisilebilir', false);
  }

  // mounted: hashchange dinleniyor (geri tusu calissin)
  ok('mounted() hashchange olayini dinliyor',
     govdeIcinde(appKaynak, 'mounted', "'hashchange'"));

  // DAVRANIS: watch.gorunum gercekten iki tuvali $nextTick icinde cizdiriyor mu.
  // Sahte `this`: nextTick'i hemen kosuyoruz, cizimleri sayiyoruz.
  const w = secenekler.watch && secenekler.watch.gorunum;
  ok('watch.gorunum tanimli', typeof w === 'function');
  if (typeof w === 'function') {
    let g = 0, o = 0, tick = 0;
    const sahte = {
      $nextTick(fn) { tick++; fn(); },
      grafikCiz() { g++; }, osiloCiz() { o++; },
    };
    sandbox.location = { hash: '#/olcum' };
    sandbox.history = { replaceState() {} };
    w.call(sahte, 'skop');
    ok('gorunum degisince grafik VE skop $nextTick icinde yeniden ciziliyor',
       tick === 1 && g === 1 && o === 1, `nextTick=${tick} grafik=${g} skop=${o}`);
    delete sandbox.location; delete sandbox.history;
  }

  // CSS: sekme sinifi ve etkin durumu tanimli (8. bolum genel sinif
  // denetimini yapiyor; burada ETKIN sekmenin ayirt edildigini civiliyoruz)
  const tumCss = cssOku();
  ok('Etkin sekme gorsel olarak ayirt ediliyor (.gorunum-sekme.etkin)',
     /\.gorunum-sekme\.etkin\s*\{[^}]*(color|border)/.test(tumCss));

  // Bildirimler TEK alanda: ust seritteki dort kosullu blok tek sarmalda
  // (yorumsuz() HTML yorumlarini sildiginden kapanis isareti degil, ilk
  //  <main> sinir: bildirim sarmali gorunumlerden ONCE bitmeli)
  const bildirimBlok = html.match(/<div class="bildirimler">([\s\S]*?)<main /);
  ok('Ust bildirimler tek .bildirimler sarmalinda',
     !!bildirimBlok && ['!destekli', 'kopruAdresi', 'v-if="hata"', '!surucuyum']
       .every((k) => bildirimBlok[1].includes(k)));

  // Kalibrasyon talimati pil sekmesinde DEGIL, ayar sekmesinde.
  // (Gorunumler ayrilinca ortaya cikan yerlesim kusuru — B27 A1.)
  const ayarBlok = html.match(/v-show="gorunum === 'ayar'"([\s\S]*?)<\/main>/);
  const pilBlok = html.match(/v-show="gorunum === 'pil'"([\s\S]*?)<\/main>/);
  ok('"Sira onemli" kalibrasyon talimati AYAR gorunumunde, pilde degil',
     !!ayarBlok && ayarBlok[1].includes('Sıra önemli') &&
       !!pilBlok && !pilBlok[1].includes('Sıra önemli'));
}

/* ═══════════════════════════════════════════════════════════════════════
   11. RAPOR ARALIGI + GRAFIK BOSLUKLARI (B27 A2)

   Kullanicinin ekran goruntusu (2026-09-12) iki sey gosterdi:
   (a) KPI kartlari "veri yok" derken grafik sahte 1.72 V'u DUZ CIZGI
       olarak cizmeye ve "tepe 1.72 V" yazmaya devam ediyordu — K1'in
       grafik yarisi eksikti.
   (b) "463 /sn" etiketi ADC hizini soyluyor, ekran 5/s guncelleniyordu;
       kullanici farki fark etti. Artik iki hiz ayri ve ikisi de OLCULUYOR.
   Ayrica rapor araligi (D satiri sikligi) `r<ms>` ile secilebilir oldu.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 11. Rapor araligi + grafik bosluklari (B27 A2) ---');
{
  const u = ornek();
  u.grafikCiz = secenekler.methods.grafikCiz;      // ornek() bunu susturuyor
  u.grafikPlanla = secenekler.methods.grafikPlanla;

  // (a) gecersiz kanal NaN olarak gecmise giriyor
  u.satirIsle('D 1.7160 0.000003 0.00001 0.0 0.0 1000 93 0 1');
  const s1 = u.gecmis[u.gecmis.length - 1];
  ok('durum=1 (V yok): gecmiste V ve W NaN, I sayi',
     Number.isNaN(s1.v) && Number.isNaN(s1.w) && s1.i === 0.000003,
     JSON.stringify(s1));
  u.satirIsle('D 12.0 0.5 6.0 0.0 0.0 1200 93 0 2');
  const s2 = u.gecmis[u.gecmis.length - 1];
  ok('durum=2 (I yok): I ve W NaN, V sayi',
     Number.isNaN(s2.i) && Number.isNaN(s2.w) && s2.v === 12);
  u.satirIsle('D 12.0 0.5 6.0 0.0 0.0 1400 93 0 0');
  const s3 = u.gecmis[u.gecmis.length - 1];
  ok('durum=0: uc kanal da sayi', [s3.v, s3.i, s3.w].every(Number.isFinite));

  // (b) iki hiz, ikisi de olculen araliktan
  ok('guncellemeHizi 200 ms araliktan "5 güncelleme/s"',
     u.guncellemeHizi === '5 güncelleme/s', u.guncellemeHizi);
  ok('orneklemeHizi 93 ornek / 200 ms = "465 örnek/s"',
     u.orneklemeHizi === '465 örnek/s', u.orneklemeHizi);

  // grafik: sahte tuval, cagrilari kaydeden baglam
  const cagri = [];
  /* Sahte 2B baglam: her cagriyi kaydeder. `measureText` GERCEK
     tarayicida her zaman bir TextMetrics doner; undefined dondurmek
     sahte baglamin kusuru olurdu (app.js'i savunmaci yazmak yerine
     taklidi duzeltiyoruz — B17 dersi: taklit GERCEGI modellemeli). */
  const ctx = new Proxy({}, {
    get: (_, ad) => (...args) => {
      cagri.push([ad, args]);
      if (ad === 'measureText') return { width: String(args[0] || '').length * 6 };
      return undefined;
    },
    set: () => true,
  });
  u.$refs.grafik = {
    getBoundingClientRect: () => ({ width: 800 }), dataset: {},
    height: 300, width: 0, style: {}, getContext: () => ctx,
  };
  u.pencere = 60; u.gosterV = true; u.gosterI = true; u.gosterW = false;
  const say = (ad) => cagri.filter((c) => c[0] === ad).length;
  const metinler = () => cagri.filter((c) => c[0] === 'fillText').map((c) => c[1][0]);

  // V tamamen NaN, I gecerli
  u.gecmis = [{ t: 0, v: NaN, i: 1, w: NaN }, { t: 1, v: NaN, i: 2, w: NaN },
              { t: 2, v: NaN, i: 3, w: NaN }];
  u.grafikCiz();
  ok('V tamamen NaN: "veri yok" etiketi var, "tepe … V" YOK',
     metinler().includes('veri yok') && !metinler().some((m) => /tepe .* V$/.test(m)),
     metinler().join(' | '));
  ok('I gecerli: "tepe … mA" etiketi var',
     metinler().some((m) => /^tepe .* mA$/.test(m)));

  // ortada NaN: cizgi KOPMALI (bir moveTo fazla, bir lineTo eksik)
  u.gosterV = false;
  cagri.length = 0;
  u.gecmis = [{ t: 0, v: 1, i: 1, w: 1 }, { t: 1, v: 1, i: 2, w: 1 },
              { t: 2, v: 1, i: 3, w: 1 }, { t: 3, v: 1, i: 4, w: 1 }];
  u.grafikCiz();
  const duzMove = say('moveTo'), duzLine = say('lineTo');
  cagri.length = 0;
  u.gecmis[1].i = NaN;
  u.grafikCiz();
  /* Kopan nokta iki lineTo goturur: kendi lineTo'su ve ardindaki noktanin
     lineTo'su (o artik moveTo). Ilk yazimda -1 beklenmisti, yanlisti. */
  ok('ortadaki NaN cizgiyi KOPARIYOR (moveTo +1, lineTo -2)',
     say('moveTo') === duzMove + 1 && say('lineTo') === duzLine - 2,
     `moveTo ${duzMove}->${say('moveTo')} lineTo ${duzLine}->${say('lineTo')}`);

  // CSV: NaN bos hucre (Blob/URL sanalikta yok; govde denetimi)
  ok('csvIndir NaN hucreyi BOS birakiyor',
     govdeIcinde(appKaynak, 'csvIndir', "Number.isNaN(x) ? ''"));

  // cizim birlestirme: rAF varsa bir kareye toplaniyor
  {
    let cizim = 0, raf = 0;
    const v = ornek();
    v.grafikPlanla = secenekler.methods.grafikPlanla;
    v.grafikCiz = () => { cizim++; };
    sandbox.requestAnimationFrame = (fn) => { raf++; setTimeout(fn, 0); return raf; };
    v.grafikPlanla(); v.grafikPlanla(); v.grafikPlanla();
    ok('uc grafikPlanla() tek requestAnimationFrame\'e birlesiyor',
       raf === 1 && cizim === 0, `raf=${raf} cizim=${cizim}`);
    delete sandbox.requestAnimationFrame;
    v.grafikPlanla();
  }

  // rapor araligi: A satiri -> tercih farkliysa surucu r<ms> yollar
  const gidenler = [];
  u.gonder = async (k) => { gidenler.push(k); };
  u.raporMs = 100; u.surucuyum = true; u.bagli = true;
  const A = 'A menzil=NORMAL oto=1 n_kazanc=1.000000 n_sifir=0 y_kazanc=1.000000 '
          + 'y_sifir=0 sont=0.100000 i_duz=1.000000 i_ofset=0 rapor=200';
  u.satirIsle(A);
  ok('A rapor=200, tercih 100, surucu -> r100 gonderildi',
     u.kartRapor === 200 && gidenler.includes('r100'), gidenler.join(' '));
  gidenler.length = 0; u.surucuyum = false;
  u.satirIsle(A);
  ok('izleyici hicbir sey gondermez', gidenler.length === 0);
  u.surucuyum = true; u.raporMs = 200; gidenler.length = 0;
  u.satirIsle(A);
  ok('A rapor=200, tercih 200 -> gereksiz r yok', gidenler.length === 0);
  u.kartRapor = null;
  u.satirIsle(A.replace(' rapor=200', ''));
  ok('eski firmware (rapor= yok) -> kartRapor dokunulmaz', u.kartRapor === null);

  // kartin yaniti: KIRPILMIS deger tercihi ezer (r5 -> 20)
  u.raporMs = 5;
  u.satirIsle('* rapor araligi 20 ms');
  ok('"* rapor araligi 20 ms" -> kartRapor 20 VE raporMs 20 (kirpma gorunur)',
     u.kartRapor === 20 && u.raporMs === 20);

  // watch: tercih degisince bagli surucu r<ms> yollar
  const w = secenekler.watch && secenekler.watch.raporMs;
  ok('watch.raporMs tanimli', typeof w === 'function');
  if (typeof w === 'function') {
    const g2 = []; const saklanan = [];
    const sahte = { ayarYaz: (k, v) => saklanan.push(k + '=' + v), bagli: true,
                    surucuyum: true, kartRapor: 200, gonder: async (k) => { g2.push(k); } };
    w.call(sahte, 500);
    ok('raporMs 500 -> localStorage + r500', saklanan.includes('raporMs=500') && g2.includes('r500'));
    const g3 = [];
    w.call({ ayarYaz() {}, bagli: false, surucuyum: true, kartRapor: 200,
             gonder: async (k) => { g3.push(k); } }, 500);
    ok('bagli degilken r gonderilmez (baglaninca A ile uydurulur)', g3.length === 0);
  }

  // firmware tarafi.
  // govdeIcinde() JS metotlari icin (girintili tanim); C'de tanim satir
  // basinda `void ad(` ve ilk girintili eslesme bir CAGRI oluyor — yanlis
  // govde. Tanimi tip sozcugu + ad + parametre + `{` ile ariyoruz.
  const cGovde = (kaynak, ad, aranan) => {
    const m = new RegExp('\\n[A-Za-z_][\\w\\s*]*\\b' + ad + '\\([^;{)]*\\)\\s*\\{').exec(kaynak);
    if (!m) return false;
    const j = kaynak.indexOf('{', m.index + m[0].length - 1);
    let d = 0;
    for (let k = j; k < kaynak.length; k++) {
      if (kaynak[k] === '{') d++;
      else if (kaynak[k] === '}') { d--; if (d === 0) return kaynak.slice(j, k + 1).includes(aranan); }
    }
    return false;
  };
  ok('firmware `r<ms>` 20..5000 arasina KIRPIYOR',
     /#define RAPOR_MS_EN_AZ\s+20\b/.test(ino) && /#define RAPOR_MS_EN_COK\s+5000\b/.test(ino)
       && /case 'r':[\s\S]{0,500}if \(v < RAPOR_MS_EN_AZ\)[\s\S]{0,120}if \(v > RAPOR_MS_EN_COK\)/.test(ino));
  ok('firmware A satirinda rapor= var (K5 deseni: kart soyler)',
     cGovde(ino, 'ayar_yaz_seri', '" rapor="'));
  ok('SSE olayi istemci basina TEK write() (dort print degil)',
     cGovde(ino, 'akis_yolla', '.write(') && !cGovde(ino, 'akis_yolla', '.print('));

  // sahte kart ayni davranis
  const SK = require(path.join(ARAYUZ, 'sahte-kart.js'));
  ok('sahte kart `r5` -> "* rapor araligi 20 ms" (kirpma firmware ile ayni)',
     SK.komut('r5')[0] === '* rapor araligi 20 ms' && SK.raporAralik() === 20);
  ok('sahte kart `r9999` -> 5000', SK.komut('r9999')[0] === '* rapor araligi 5000 ms');
  SK.komut('r200');
  ok('sahte kart A satirinda rapor=', /\brapor=200\b/.test(SK.komut('?')[0]));
  ok('sahte kart ornek sayisi aralikla olcekleniyor (200 ms -> 172)',
     SK.dSatiri(1000, 0).satir.split(' ')[7] === '172');
  SK.komut('r100');
  ok('… 100 ms -> 86', SK.dSatiri(1100, 0).satir.split(' ')[7] === '86');
  SK.komut('r200');

  // arayuz: secici GORUNUMDE ve secenekler tek listeden
  ok('Yenileme secicisi zaman grafigi arac cubugunda, RAPOR_SECENEKLERI\'nden',
     /v-model\.number="raporMs"[\s\S]{0,200}v-for="s in raporSecenekleri"/.test(yorumsuz(htmlKaynak))
       && /raporSecenekleri:\s*RAPOR_SECENEKLERI/.test(appKaynak));
  ok('Ornekleme kartinda guncellemeHizi gosteriliyor',
     yorumsuz(htmlKaynak).includes('{{ guncellemeHizi }}'));

  /* B27 A2-b: akim kanalinin menzili VE adimi. Kartta olculdu: 0.1 ohm
     sontte ham gurultu tam 1 LSB (78 uA); ekrandaki "7 uA" 96 orneklik
     ortalama. Adim gorunmeden bu sayi gercek akim sanildi. */
  {
    const a = ornek();
    a.kartSont = 0.1;
    ok('akimMenzilAralik 0.1 ohm -> ±2.56 A · 78.1 µA',
       a.akimMenzilAralik === '±2.56 A · 78.1 µA', a.akimMenzilAralik);
    a.kartSont = 10;
    ok('… 10 ohm -> ±25.6 mA · 0.78 µA',
       a.akimMenzilAralik === '±25.6 mA · 0.78 µA', a.akimMenzilAralik);
    /* Kart okunmadiysa menu tercihi YEDEK — ama kart konustuysa KART haklidir
       (sont fiziksel bir gercek; K5 deseni). */
    a.kartSont = null; a.sontSecim = '1';
    ok('kart okunmadan menu tercihi yedek (1 ohm)',
       a.akimMenzilAralik === '±256.0 mA · 7.81 µA', a.akimMenzilAralik);
    a.kartSont = 0.1;
    ok('kart konusunca KART kazaniyor (menu 1 ohm derken kart 0.1)',
       a.akimMenzilAralik === '±2.56 A · 78.1 µA', a.akimMenzilAralik);
    ok('Akim kartinda menzil/adim satiri var',
       yorumsuz(htmlKaynak).includes('{{ akimMenzilAralik }}'));
    ok('ADS kademesi firmware ile ayni (PGA_0256)',
       /const ADS_PGA_V = 0\.256;/.test(appKaynak) &&
       /#define PGA_0256\s+0\.256f/.test(fs.readFileSync(
         path.join(KOK, 'kod', 'olcum-karti-a3', 'olcum3.h'), 'utf8')));
  }

  // otomatik baglanma: sayfayi kart/kopru sunduysa EVET, yerel/demo/file HAYIR
  {
    const v = ornek();
    const karar = (loc, tasiyici = 'akis', bagli = false) => {
      sandbox.location = loc; v.tasiyiciAdi = tasiyici; v.bagli = bagli;
      const r = v.otomatikBaglanmali(); delete sandbox.location; return r;
    };
    const kart = { protocol: 'http:', hostname: 'olcum.local', search: '' };
    ok('kart sunuyor (olcum.local, akis) -> otomatik baglan', karar(kart) === true);
    ok('localhost -> baglanma (gelistirme sunucusu, USB kipi)',
       karar({ protocol: 'http:', hostname: 'localhost', search: '' }) === false);
    ok('file:// -> baglanma',
       karar({ protocol: 'file:', hostname: '', search: '' }) === false);
    ok('?demo -> baglanma (sahte kart)',
       karar({ protocol: 'http:', hostname: 'olcum.local', search: '?demo' }) === false);
    ok('tasiyici seri ise baglanma', karar(kart, 'seri') === false);
    ok('zaten bagliysa tekrar baglanma', karar(kart, 'akis', true) === false);
    ok('mounted() kopruyuAlgila SONRASINDA otomatikBaglanmali ile baglan() cagiriyor',
       /kopruyuAlgila\(\)\.then\([\s\S]{0,80}?otomatikBaglanmali\(\)\) this\.baglan\(\)/.test(yorumsuz(appKaynak)));
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   12. AKIS TASIYICISI: `?` KIMLIKTEN SONRA (B27 A2)

   Gercek kartta CDP ile olculdu: sayfa acilir acilmaz gonderilen `?`
   HER SEFERINDE 403 aliyordu ("gecersiz oturum jetonu") cunku `ac()`
   EventSource'u kurup hemen donuyor, jeton ise `kimlik` olayiyla
   sonradan geliyordu. Sonuc: WiFi yolunda K5 esitlemesi hic calismiyor,
   her acilis bir hata bildirimiyle basliyor.

   Bu bolum ASENKRON ve DAVRANISSAL: sahte EventSource ile `ac()`
   cagriliyor; `kimlik` gelmeden cozulmemeli, gelince cozulmeli, ve
   baglan() akisinda `?` jetonla gitmeli.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 12. Akis tasiyicisi: `?` kimlikten sonra ---');
{
  /* Asenkron bolumde yakalanmayan bir hata surecin SESSIZCE 0 ile
     cikmasina yol acar — 'dogrulama gecti' satiri basilmaz ama kimse
     kirmizi gormez. Acikca kirmizi yap. */
  process.on('unhandledRejection', (e) => {
    console.log('[!!] asenkron bolum COKTU: ' + (e && e.stack || e));
    process.exit(1);
  });
  const T = vm.runInContext('TASIYICILAR', sandbox);
  /* Sahte EventSource: olaylari elle tetikliyoruz. Global olarak sandbox'a
     konuyor cunku `ac()` `new EventSource(...)` diyor. */
  class SahteES {
    constructor(url) { this.url = url; this.dinleyici = {}; SahteES.son = this; }
    addEventListener(ad, fn) { (this.dinleyici[ad] = this.dinleyici[ad] || []).push(fn); }
    tetikle(ad, data) {
      for (const fn of (this.dinleyici[ad] || []).slice()) fn({ data });
    }
    close() {}
  }
  sandbox.EventSource = SahteES;
  const gercekSetTimeout = sandbox.setTimeout;
  sandbox.setTimeout = () => 0;          // 3 s tavan bu testte HIC dolmasin
  sandbox.clearTimeout = () => {};

  const u = ornek();
  u.kartAdres = (yol) => yol;
  u.kaydet = () => {};
  let cozuldu = false;
  const soz = T.akis.ac(u).then(() => { cozuldu = true; });

  (async () => {
    await new Promise((r) => setImmediate(r));
    ok('kimlik gelmeden ac() COZULMUYOR', cozuldu === false);
    ok('EventSource /akis ile acildi', SahteES.son && SahteES.son.url === '/akis');
    SahteES.son.tetikle('kimlik', JSON.stringify({ jeton: 'abc123', surucu: true }));
    await soz;
    ok('kimlik gelince ac() cozuluyor ve jeton alinmis', cozuldu && u.jeton === 'abc123', u.jeton);

    /* baglan() akisi: ac() -> `?`. Gonderilen `?` jetonlu gitmeli. */
    const v = ornek();
    v.kartAdres = (yol) => yol; v.kaydet = () => {};
    v.tasiyiciAdi = 'akis';
    const gidenler = [];
    v.gonder = async (metin) => { gidenler.push({ metin, jeton: v.jeton }); };
    const b = v.baglan();
    await new Promise((r) => setImmediate(r));
    ok('baglan(): kimlik gelmeden `?` GONDERILMEDI', gidenler.length === 0);
    SahteES.son.tetikle('kimlik', JSON.stringify({ jeton: 'xyz789', surucu: true }));
    await b;
    /* ⚠ Iddia "TEK komut" demiyor artik: B36 ile baglantida `CT`
       (kalibrasyon tablosu) da gidiyor. Korunan sey SAYI degil KURAL —
       ilk komut `?` ve gidenlerin HEPSI jetonlu. Sayiya kilitlemek,
       her yeni acilis komutunda bu testi anlamsizca kirardi. */
    ok('baglan(): kimlikten sonra `?` JETONLA gitti',
       gidenler.length >= 1 && gidenler[0].metin === '?'
       && gidenler.every((g) => g.jeton === 'xyz789'),
       JSON.stringify(gidenler));
    ok('baglan(): kalibrasyon tablosu da isteniyor (`CT`)',
       gidenler.some((g) => g.metin === 'CT'),
       'tablo gelmezse skop ekseni duzeltmesiz cizilir');

    /* hata olayi da cozmeli — yoksa baglan() sonsuza kadar askida */
    const w = ornek(); w.kartAdres = (yol) => yol; w.kaydet = () => {};
    let hataCozdu = false;
    const s2 = T.akis.ac(w).then(() => { hataCozdu = true; });
    await new Promise((r) => setImmediate(r));
    SahteES.son.tetikle('error', '');
    await s2;
    ok('akis hatasi ac()\'i cozuyor (askida kalmaz)', hataCozdu);

    sandbox.setTimeout = gercekSetTimeout;
    delete sandbox.EventSource; delete sandbox.clearTimeout;
    await bolum12Bitti();
  })();
}

async function bolum12Bitti() {
/* ═══════════════════════════════════════════════════════════════════════
   13. TASARIM SISTEMI (B27 Asama 2)

   Iki sinif kusur civileniyor:
   (a) TEMA YARIM KALMASI — bir belirtec yalnizca bir temada tanimliysa
       oteki temada `var()` sessizce gecersize duser: renk hic uygulanmaz,
       hata da vermez. Sayfa "bir temada guzel, otekinde okunaksiz" olur.
   (b) ARAYUZ <-> TUVAL AYRISMASI — kanal renkleri hem kartlarda hem
       `app.js`'in ciziminde kullaniliyor (`renk('--volt')`). Ucu de
       tanimli ve BIRBIRINDEN FARKLI olmali; ikisi ayni olursa grafikte
       gerilim ve akim ayirt edilemez.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 13. Tasarim sistemi: temalar, kanal renkleri, hareket ---');
{
  const css = cssOku();
  const blok = (secici) => {
    const i = css.indexOf(secici);
    if (i < 0) return null;
    const a = css.indexOf('{', i), b = css.indexOf('}', a);
    return a < 0 || b < 0 ? null : css.slice(a, b);
  };
  const belirtecler = (govde) => new Set(
    [...(govde || '').matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));

  const koyu = belirtecler(blok(':root {'));
  const acikBlok = css.match(/@media \(prefers-color-scheme: light\)\s*\{\s*:root\s*\{([^}]*)\}/);
  const acik = belirtecler(acikBlok && acikBlok[1]);

  ok('Koyu tema VARSAYILAN: butun belirtecler bare :root icinde',
     koyu.size >= 20, `${koyu.size} belirtec`);
  ok('Acik tema yalnizca DEGERLERI degistiriyor (yeni belirtec uretmiyor)',
     [...acik].every((b) => koyu.has(b)),
     [...acik].filter((b) => !koyu.has(b)).join(' '));

  /* Renk belirtecleri IKI temada da tanimli olmali. Olcu/bicim
     belirtecleri (--mono, --yuvarlak, --gecis, --govde) temaya gore
     degismez; onlar disarida. */
  const renkler = [...koyu].filter((b) =>
    !/^--(mono|govde|yuvarlak|yuvarlak-sm|gecis)$/.test(b));
  const eksikAcik = renkler.filter((b) => !acik.has(b));
  ok('Her renk/golge belirteci ACIK temada da yeniden tanimli',
     eksikAcik.length === 0, eksikAcik.join(' '));

  /* Kanal renkleri: tanimli, birbirinden FARKLI, iki temada da. */
  for (const [ad, kume] of [['koyu', blok(':root {')], ['acik', acikBlok && acikBlok[1]]]) {
    const g = kume || '';
    const oku = (b) => (g.match(new RegExp(b + ':\\s*([^;]+);')) || [])[1];
    const uc = ['--volt', '--amper', '--watt'].map(oku);
    ok(`Kanal renkleri ${ad} temada tanimli ve UCU DE FARKLI`,
       uc.every(Boolean) && new Set(uc.map((x) => x.trim().toLowerCase())).size === 3,
       uc.join(' '));
    const vurgu = oku('--vurgu');
    ok(`Vurgu ${ad} temada kanal renklerinden AYRI`,
       !!vurgu && !uc.map((x) => (x || '').trim().toLowerCase())
                     .includes(vurgu.trim().toLowerCase()),
       `vurgu ${vurgu}`);
  }

  /* app.js'in tuvalde okudugu her belirtec CSS'te tanimli olmali.
     Tanimsizsa getPropertyValue bos doner ve cizgi '#888'e duser —
     grafik sessizce gri cizilir. */
  const tuvalBelirtecleri = [...new Set(
    [...yorumsuz(appKaynak).matchAll(/renk\('(--[a-z0-9-]+)'\)/g)].map((m) => m[1]))];
  ok('app.js`in tuvalde okudugu her belirtec CSS`te TANIMLI',
     tuvalBelirtecleri.length >= 3 && tuvalBelirtecleri.every((b) => koyu.has(b)),
     tuvalBelirtecleri.filter((b) => !koyu.has(b)).join(' ') || tuvalBelirtecleri.join(' '));

  /* Hareket olculu: reduced-motion karsiligi VAR. */
  ok('prefers-reduced-motion karsiligi var (hareket kapanabiliyor)',
     /@media \(prefers-reduced-motion: reduce\)/.test(css) &&
     /animation-duration:\s*\.01ms\s*!important/.test(css));
  /* Sonsuz animasyon YALNIZCA DURUM GOSTERGELERINDE olabilir: canli
     akis noktasi ve acil durdurma noktasi. Olcum sayisinin oynamasi
     okunakligi bozar — ilk yazimda "en fazla bir tane" demistim, ama
     ikinci mesru gosterge gelince o kural yanlis yere kirmiziya dondu.
     Dogru olcut SAYI degil, HANGI SECICI. */
  const IZINLI_NABIZ = ['.rozet.acik .nokta', '.acil-nokta'];
  const nabizli = [...css.matchAll(/([^{}]+)\{[^{}]*animation:[^;]*infinite[^;]*;/g)]
    .map((m) => m[1].trim().split(/[\n,]/).pop().trim());
  ok('Sonsuz animasyon yalnizca durum gostergelerinde',
     nabizli.length > 0 && nabizli.every((s) => IZINLI_NABIZ.includes(s)),
     nabizli.join(' | '));
  ok('Olcum sayilarinda animasyon YOK (hane oynamasin)',
     !nabizli.some((s) => /\.deger|\.kpi-deger|\.skop-olcum-deger/.test(s)),
     nabizli.join(' | '));

  /* Olcum sayilari tabular: hane kaymasin. */
  ok('Olcum ve ikincil sayilar tabular-nums',
     /\.olcum \.deger\s*\{[^}]*tabular-nums/.test(css) &&
     /\.ikincil \.deger\s*\{[^}]*tabular-nums/.test(css));

  /* Tek CSS dosyasi: karttan her ek istek loop()`u blokluyor. */
  ok('Sayfa TEK stil dosyasi bagliyor', CSS_YOLLARI.length === 1,
     CSS_YOLLARI.map((p) => path.basename(p)).join(' '));

  /* Tasiyici seciciyle TASIYICILAR kaydi ortusmeli: ?demo ile tasiyici
     'demo' oluyordu ama menude karsiligi yoktu ve secici BOS gorunuyordu. */
  const menuSecenekleri = [...yorumsuz(htmlKaynak).matchAll(
    /<option value="(seri|akis|demo)"/g)].map((m) => m[1]);
  const T13 = vm.runInContext('TASIYICILAR', sandbox);
  ok('Her tasiyicinin menude bir secenegi var (bos secici yok)',
     Object.keys(T13).every((k) => menuSecenekleri.includes(k)),
     `menu: ${menuSecenekleri.join(' ')} | tasiyici: ${Object.keys(T13).join(' ')}`);
  ok('demo tasiyicisi HER ZAMAN destekli (olu dugme yok)',
     T13.demo.destekli() === true);
  ok('Menuden demo secilince sahte kart KURULUYOR',
     govdeIcinde(appKaynak, 'tasiyiciAdi', "this.demoVeri()"),
     'yoksa tasiyici degisir ama veri gelmez');

  /* 🔴 Headless render yakaladi: ?demo ile acilista demoVeri() hem
     mounted()'tan hem watch`tan cagriliyordu; ikisi de betigi beklerken
     gecti ve `sahte-kart.js` IKI KEZ indi -> "Identifier 'SahteKart' has
     already been declared" -> sayfanin o andan sonraki betikleri dustu.
     Kapi `await`ten ONCE kapanmali. */
  {
    const d = ornek();
    let inen = 0, kurulan = 0;
    d.betikYukle = async () => { inen++; };
    d.kaydet = () => {}; d.$nextTick = (f) => f && f();
    d.osiloOtomatik = () => {}; d.satirIsle = () => { kurulan++; };
    d.pilYokla = () => {};
    sandbox.SahteKart = {
      raporAralik: () => 200,
      dSatiri: () => ({ satir: 'D 1 0 0 0 0 0 96 0 0', w: 0 }),
      sinyaller: {}, komut: () => [],
    };
    SONRA.push(async () => {
      await Promise.all([d.demoVeri(), d.demoVeri()]);
      ok('demoVeri() IKI kez cagrilsa da betik BIR kez iniyor', inen === 1, `inen=${inen}`);
      ok('… ve akis bir kez kuruluyor (300 nokta, cift degil)',
         kurulan === 300, `satirIsle ${kurulan} kez`);
      delete sandbox.SahteKart;
    });
    /* 🔴 Headless render ikinci kusuru: `demoVeri()` once `tasiyiciAdi`yi
     'demo' yapip SONRA `bagli`yi aciyor; watch ondan sonra kosuyor ve
     acilan demo baglantisini "eski tasiyici" sanip KAPATIYORDU. Demo
     akisi ilk 300 noktadan sonra susuyor, rozet "bagli degil" diyordu.
     Bagli tasiyici artik acikca tutuluyor. */
  {
    const w = secenekler.watch.tasiyiciAdi;
    let kapanan = null;
    const T = vm.runInContext('TASIYICILAR', sandbox);
    const eskiKapat = T.demo.kapat;
    T.demo.kapat = async () => { kapanan = 'demo'; };
    const d = { ayarYaz() {}, kaydet() {}, bagli: true, bagliTasiyici: 'demo',
                demoVeri() { this.demoCagrildi = true; } };
    SONRA.push(async () => {
      await w.call(d, 'demo', 'seri');
      ok('demo kurulduktan sonra watch onu KAPATMIYOR (bagli kalir)',
         d.bagli === true && kapanan === null, `bagli=${d.bagli} kapanan=${kapanan}`);
      ok('… ve demoVeri ikinci kez cagrilmiyor', !d.demoCagrildi);

      const e2 = { ayarYaz() {}, kaydet() {}, bagli: true, bagliTasiyici: 'akis' };
      const eskiAkisKapat = T.akis.kapat;
      T.akis.kapat = async () => { kapanan = 'akis'; };
      await w.call(e2, 'seri', 'akis');
      ok('GERCEK tasiyici degisiminde ACIK olan kapaniyor',
         kapanan === 'akis' && e2.bagli === false && e2.bagliTasiyici === null);
      T.akis.kapat = eskiAkisKapat; T.demo.kapat = eskiKapat;
    });
  }
  ok('baglan() acik tasiyiciyi KAYDEDIYOR',
     govdeIcinde(appKaynak, 'baglan', 'this.bagliTasiyici = this.tasiyiciAdi'));
  ok('betikYukle ayni src`yi iki kez EKLEMIYOR',
       govdeIcinde(appKaynak, 'betikYukle', "querySelector('script[src=\"' + yol + '\"]')"),
       'const yeniden bildirimi SyntaxError verir');
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   14. TELEFON YERLESIMI + ACIL DURDURMA (B27 Asama 3)

   Iki sey civileniyor:
   (a) ACIL DURDURMA her gorunumde. Telefonda desarj surerken once dogru
       sekmeyi bulmak zorunda kalmak EMNIYET kusurudur. `p0` jeton ve
       parola istemeyen tek komut; serit de gorunumlerin DISINDA durmali,
       yoksa yalnizca acik sekmede gorunur.
   (b) Telefon kirilimi CSS'te var ve olcum kartlari orada yeniden
       diziliyor. "Telefonda basit surum" AYRI bir arayuz demek olurdu —
       bu proje arayuz ayrismasindan uc kez yandi; tek sablon, farkli
       yerlesim.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 14. Telefon yerlesimi + acil durdurma ---');
{
  const html = yorumsuz(htmlKaynak);
  const css = cssOku();

  /* (a) Acil serit: gorunumlerin DISINDA (ilk <main>'den once) ve
         kosulu "test calisiyor". */
  const acilIndeks = html.indexOf('class="acil"');
  const ilkMain = html.indexOf('<main ');
  ok('Acil durdurma seridi gorunumlerin DISINDA (her sekmede gorunur)',
     acilIndeks > 0 && ilkMain > 0 && acilIndeks < ilkMain,
     `acil@${acilIndeks} ilkMain@${ilkMain}`);
  ok('Acil serit YALNIZCA test calisirken gorunuyor',
     /v-if="pilDurum === 'CALISIYOR'"[\s\S]{0,120}class="acil"/.test(html) ||
     /class="acil"[\s\S]{0,120}v-if="pilDurum === 'CALISIYOR'"/.test(html));
  ok('Acil seritteki dugme `p0` gonderiyor (pilDurdurKomut)',
     /class="acil"[\s\S]{0,600}@click="pilDurdurKomut"/.test(html) &&
     govdeIcinde(appKaynak, 'pilDurdurKomut', "gonder('p0')"));
  /* Emniyet dugmesi ENGELLENMEMELI: `:disabled` konursa surucu olmayan
     oturumda ya da baglanti dalgalanmasinda durdurma kilitlenir. `p0`
     zaten jetonsuz gecen tek komut. */
  ok('Acil dugmede :disabled YOK (durdurma hicbir kosula bagli degil)',
     !/class="acil"[\s\S]{0,600}acil-dur[^>]*:disabled/.test(html));
  ok('Acil serit gorsel olarak uyari rengiyle ayirt ediliyor',
     /\.acil\s*\{[^}]*var\(--uyari\)/.test(css) &&
     /\.acil-dur\s*\{[^}]*var\(--uyari\)/.test(css));

  /* (b) Telefon kirilimi: olcum kartlari yeniden diziliyor ve cok dar
         ekranda tek sutuna donuyor. */
  const telefon = css.match(/@media \(max-width: 620px\)\s*\{([\s\S]*?)\n\}/);
  ok('Telefon kirilimi (<=620px) tanimli', !!telefon);
  if (telefon) {
    ok('Telefonda olcum kartlari iki sutun, guc tam genislik',
       /\.olcumler\s*\{[^}]*grid-template-columns:\s*1fr 1fr/.test(telefon[1]) &&
       /\.olcum\.w\s*\{[^}]*grid-column:\s*1 \/ -1/.test(telefon[1]));
    ok('Telefonda ust seridin alt basligi gizleniyor (yer kazanci)',
       /\.ust \.alt\s*\{[^}]*display:\s*none/.test(telefon[1]));
  }
  ok('Cok dar ekranda (<=380px) olcumler tek sutuna donuyor',
     /@media \(max-width: 380px\)[\s\S]{0,200}grid-template-columns:\s*1fr;/.test(css));

  /* Ust serit sadelesti: tasiyici secici ve adres AYARLAR'da. */
  const ust = html.match(/<header class="ust">([\s\S]*?)<\/header>/);
  ok('Ust seritte tasiyici secici ve adres kutusu YOK', !!ust &&
     !ust[1].includes('v-model="tasiyiciAdi"') && !ust[1].includes('v-model="kartTaban"'));
  ok('Ust seritte durum rozeti ve birincil eylem VAR', !!ust &&
     ust[1].includes('class="rozet"') && ust[1].includes('@click="baglan"'));
  const ayarBlok = html.match(/v-show="gorunum === 'ayar'"([\s\S]*?)<\/main>/);
  ok('Tasiyici secici ve kart adresi AYARLAR gorunumunde', !!ayarBlok &&
     ayarBlok[1].includes('v-model="tasiyiciAdi"') &&
     ayarBlok[1].includes('v-model="kartTaban"'));

  /* Telefonda `.local` tuzagi YAZILI olmali: Android mDNS cozmuyor ve
     kullanici "telefondan giremiyorum" diye takildi (2026-09-12). */
  ok('Baglanti karti Android `.local` tuzagini soyluyor',
     /Android/.test(html) && /\.local/.test(html) && /IP adresini/.test(html));
}

/* ═══════════════════════════════════════════════════════════════════════
   15. BUTCE VE DAYANIKLILIK (B27 Asama 4)

   Plandaki iki sayi (gzip < 250 KB, dosya <= 8) BELGEDE yaziyordu ama
   hicbir sey onlari sinamiyordu — yani butce degil temenniydi. Artik
   `_fs.json` (karta GERCEKTEN yazilan goruntunun kunyesi) uzerinden
   olculuyor.

   Dayaniklilik: kart yeniden baslarken sayfa acilirsa betiklerden biri
   gelmiyor ve ekranda ham `{{ }}` kaliyordu. `v-cloak` onu GIZLIYOR ama
   yerine bir sey KOYMUYOR — kullaniciya hicbir sey soylemeyen bos sayfa.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 15. Butce ve dayaniklilik ---');
{
  const html = yorumsuz(htmlKaynak);
  const kunyeYolu = path.join(KOK, 'uretim', '_fs.json');
  ok('LittleFS kunyesi (_fs.json) var', fs.existsSync(kunyeYolu));
  if (fs.existsSync(kunyeYolu)) {
    const kunye = JSON.parse(fs.readFileSync(kunyeYolu, 'utf8'));
    const BUTCE = 250 * 1024;
    ok(`Arayuz gzip butcesi: ${kunye.icerik_bayt} B < ${BUTCE} B`,
       kunye.icerik_bayt > 0 && kunye.icerik_bayt < BUTCE,
       `%${(100 * kunye.icerik_bayt / BUTCE).toFixed(0)} dolu`);
    /* Dosya sayisi: her dosya karta ayri bir HTTP istegi demek ve her
       istek olcum dongusunu blokluyor (kartta olculdu: 6.5 KB'lik
       style.css bile 34 ms). */
    const varliklar = fs.readFileSync(path.join(KOK, 'uretim', 'arayuz-uret.py'), 'utf8')
      .match(/VARLIKLAR = \[([\s\S]*?)\]/);
    const adet = varliklar ? (varliklar[1].match(/"/g) || []).length / 2 : -1;
    ok('Karta yazilan dosya sayisi <= 8', adet > 0 && adet <= 8, `${adet} dosya`);
    /* Sayfanin istedigi her yerel varlik goruntude OLMALI: biri eksikse
       kart 404 doner ve arayuz acilmaz (B22.0'in ta kendisi). */
    const istenen = [...html.matchAll(/(?:^|\s)(?:href|src)="([^"]+)"/gm)]
      .map((m) => m[1]).filter((u) => !/^(https?:|data:|#|mailto:)/.test(u));
    const yazilan = varliklar ? [...varliklar[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]) : [];
    const eksik = istenen.filter((u) => !yazilan.includes(u));
    ok('Sayfanin istedigi her varlik LittleFS goruntusunde',
       eksik.length === 0, eksik.join(' ') || istenen.join(' '));
  }

  /* Dayaniklilik: acilmama durumu. */
  ok('Betik `onerror` ile acilmama durumu yakalaniyor',
     /<script src="vendor\/vue\.global\.prod\.js" onerror="arayuzHata\(/.test(html) &&
     /<script src="app\.js" onerror="arayuzHata\(/.test(html));
  ok('Zaman asimi kapisi da var (betik indi ama Vue baslamadi)',
     /setTimeout\([\s\S]{0,400}hasAttribute\('v-cloak'\)/.test(html));
  ok('Acilmama kutusu VARSAYILAN OLARAK gizli (hidden)',
     /<div id="acilmadi" hidden/.test(html));
  ok('Acilmama kutusunda YENILE eylemi var',
     /id="acilmadi"[\s\S]{0,400}location\.reload\(\)/.test(html));

  /* Bosta yoklama seyreliyor: her `/pil` istegi kartta ~15 ms olcum
     kaybi. Test calisirken ya da pil gorunumundeyken siklasiyor. */
  const u = ornek();
  u.pilDurum = 'BEKLEMEDE'; u.gorunum = 'olcum';
  ok('Bosta pil yoklamasi seyrek (10 s)', u.pilYoklamaAralik === 10000, String(u.pilYoklamaAralik));
  u.pilDurum = 'CALISIYOR';
  ok('Test calisirken siklasiyor (2 s)', u.pilYoklamaAralik === 2000);
  u.pilDurum = 'BEKLEMEDE'; u.gorunum = 'pil';
  ok('Pil gorunumu acikken de siklasiyor (2 s)', u.pilYoklamaAralik === 2000);
}

/* ═══════════════════════════════════════════════════════════════════════
   16. SKOP ARSIVI — GERIYE DONUK KAYIT (B35)

   🔴 BU BOLUM BIR CANLI KUSURDAN DOGDU. `TasiyiciAkis` (hem kart hem
      KOPRU bu tasiyiciyi kullaniyor) `skop: 'ikili'` ilan edip
      `/skop.bin` cekiyordu; sayfa kopruden geldiginde o istek KOPRUYE
      gidiyor ve kopruda boyle bir uc YOKTU -> 404. Yani osiloskop, tam
      da kullanicinin "sekilleri gormek + kayit almak" istedigi kipte
      olu bir dugmeydi. Zincir 18/18 yesilken.

   Buradaki iddialar iki seyi koruyor:
     1. TEK IKILI COZUCU — canli yakalama ile arsivden acilan kayit AYNI
        koddan gecmeli; iki cozucu olsaydi biri sessizce baska bir dalga
        cizerdi (bu projenin uc kez yandigi ayrisma sinifi).
     2. KULLANICI NEYE BAKTIGINI BILMELI — arsiv kaydi cizilirken tuval
        bunu SOYLEMELI, yoksa gecmis bir dalgaya bakip "kart su anda
        bunu olcuyor" sanilir.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 16. Skop arsivi (geriye donuk kayit) ---');
{
  const html = yorumsuz(htmlKaynak);

  ok('Arsiv listesi ucu cekiliyor (/skop/liste)',
     govdeIcinde(appKaynak, 'skopKayitlariYukle', '/skop/liste'));
  ok('Tek kayit ucu cekiliyor (/skop/al)',
     govdeIcinde(appKaynak, 'skopKayitAc', '/skop/al'));
  /* [!] ASIL IDDIA: arsiv kaydi CANLI YOLLA AYNI cozucuden geciyor. */
  ok('[!] Arsiv kaydi CANLI ile AYNI ikili cozucuden geciyor',
     govdeIcinde(appKaynak, 'skopKayitAc', 'this.skopIkiliCoz(') &&
     govdeIcinde(appKaynak, 'skopIkiliAl', 'this.skopIkiliCoz('),
     'iki cozucu olsaydi eski kayit baska cizilirdi');

  /* Kopru olup olmadigi `/durum` ucundan anlasiliyor — kart o ucu HIC
     acmiyor, yani yanit gelmesi zaten koprunun imzasi. */
  ok('Kopru varligi /durum ucundan anlasiliyor',
     govdeIcinde(appKaynak, 'kopruYokla', '/durum') &&
     govdeIcinde(appKaynak, 'kopruYokla', 'skop_arsiv'));
  ok('Kopru yoklamasi baglanmayi BLOKLAMIYOR (arsiv ek ozellik)',
     govdeIcinde(appKaynak, 'baglan', 'this.kopruYokla();') &&
     !govdeIcinde(appKaynak, 'baglan', 'await this.kopruYokla()'),
     'yoklama coksun, olcum yine aksin');

  /* [!] Olu dugme YOK: arsiv bolumu yalnizca kopru kipinde ciziliyor.
     DEVIR 4.15 tam olarak bunun tersiydi — calismayan bir dugme. */
  ok('[!] Kayit bolumu YALNIZCA kopru kipinde ciziliyor',
     /<section class="kart" v-if="skopArsivVar">/.test(html),
     'kart dogrudan bagliyken kayit yok — olu dugme gosterilmiyor');

  /* [!] Canli mi arsiv mi: tuvalde SOYLENMELI. */
  ok('[!] Arsiv kaydi cizilirken tuvalde ayirt edici serit var',
     /v-if="skopAcikKayit"[\s\S]{0,400}arsiv-serit|arsiv-serit[\s\S]{0,200}skopAcikKayit/
       .test(html) && html.includes('canlı değil'),
     'yoksa gecmis dalga canli sanilir');
  ok('Serit CANLIYA DONME yolu sunuyor',
     /arsiv-serit[\s\S]{0,600}osiloYakala/.test(html));

  /* Canli yakalama arsiv isaretini KALDIRMALI, yoksa serit yeni dalga
     cizildikten sonra da "arsiv" demeye devam ederdi. */
  ok('[!] Canli yakalama arsiv isaretini kaldiriyor',
     govdeIcinde(appKaynak, 'osiloYakala', 'this.skopAcikKayit = null') &&
     govdeIcinde(appKaynak, 'osiloOtomatik', 'this.skopAcikKayit = null'),
     'yoksa canli dalga "arsiv" etiketiyle gosterilirdi');
  /* Arsiv kaydi acilinca SUREKLI kip durmali: yoksa bir sonraki tur
     kaydin ustune canli dalga ciziyor. */
  ok('[!] Arsiv kaydi acilinca surekli yakalama duruyor',
     govdeIcinde(appKaynak, 'skopKayitAc', 'if (this.surekli) this.surekliDegis()'),
     'yoksa kayit aninda canli dalgayla degisirdi');
  /* Surekli kipte liste tazelenmiyor: saniyede birkac yakalamada her
     turda liste cekmek kopruyu bosuna mesgul eder. */
  ok('Surekli kipte arsiv listesi tazelenmiyor',
     govdeIcinde(appKaynak, 'skopListeTazeleGerekirse', '!this.surekli'));

  /* Kirpik kayit SESSIZ kalmiyor — eksik dalga "olculmus" gorunmemeli. */
  ok('[!] Kirpik kayit listede isaretleniyor',
     /v-if="!k\.tam"[\s\S]{0,120}kırpık/.test(html),
     'eksik dalga sessizce tam gorunmemeli');
  /* ⚠ `.uyari` bu projede emniyet uyarisinin KUTU stili; rozete
     uygulaninca rozet butona benziyor (tarayici goruntusunde yakalandi).
     Kayit rozetleri kendi degistiricisini kullaniyor. */
  ok('Kayit rozetleri emniyet-uyarisi sinifini KULLANMIYOR',
     !/class="kayit-etiket[^"]*\buyari\b/.test(html) &&
     !/kayit-etiket"[^>]*:class="\{ uyari/.test(html),
     'emniyet uyarisi stili rozete bulasmamali');
  /* Zaman damgasi DUVAR SAATI DEGIL; oyle gosterilip yanlis okunmasin. */
  ok('Zaman damgasinin ne oldugu yaziyor (duvar saati degil)',
     html.includes('köprü açıldıktan') &&
     govdeIcinde(appKaynak, 'skopZaman', 'Math.floor(ms / 1000)'));

  /* 🔴 KOPRUDE ASCII, KARTTA IKILI — AYNI VERIYI IKI KEZ TASIMA.
     Kopru karta USB'den bagli ve dokumu ZATEN seri porttan almak
     zorunda (arsive dusmesinin tek yolu; kartta ikili-seri dokum yok).
     O dokum SSE'den tarayiciya da geldigine gore ayrica `/skop.bin`
     cekmek ayni dalgayi ikinci kez tasimak ve IKI KEZ cizmek olurdu —
     B22.5 tam da bundan kaciniyordu. */
  ok('[!] Koprude ASCII yolu, kartta ikili yol seciliyor',
     govdeIcinde(appKaynak, 'osiloYakala', 'if (this.skopArsivVar) {') &&
     govdeIcinde(appKaynak, 'osiloYakala', "yetenek.skop === 'ikili'"),
     'koprude tB + /skop.bin ayni dalgayi ikinci kez tasirdi');
  /* Liste tazeleme TEK tamamlanma noktasinda: `skopIkiliAl` icinde
     kalsaydi koprudeki ASCII yakalamalari listeye hic dusmezdi. */
  ok('[!] Liste tazeleme TEK tamamlanma noktasinda (osiloBitir)',
     govdeIcinde(appKaynak, 'osiloBitir', 'skopListeTazeleGerekirse()') &&
     !govdeIcinde(appKaynak, 'skopIkiliAl', 'skopListeTazeleGerekirse'),
     'yoksa koprudeki ASCII yakalamalari listeye dusmezdi');

  /* 🔴 SUREKLI KIP: onceki yakalama bitmeden yenisi ISTENMEMELI.
     Eski tur kosulsuzdu (her 500 ms bir yakalama) — kartta dogrudan
     sorun degildi ama koprude dokum SERI PORTTAN geciyor ve 4000 ornek
     ~1.8 s suruyor. Kosulsuz tur kuyruk biriktirir, bloklar birbirini
     keser ve arsiv KIRPIK kayitlarla dolar. */
  ok('[!] Surekli kip onceki yakalamayi BEKLIYOR',
     govdeIcinde(appKaynak, 'surekliTur', 'if (this.osiloBekliyor) {'),
     'yoksa koprude komut kuyrugu birikir, bloklar birbirini keser');
  {
    /* Davranis sinamasi: mesgulken `osiloYakala` CAGRILMAMALI. */
    const v = ornek();
    let cagri = 0;
    v.osiloYakala = () => { cagri++; };
    v.surekli = true;
    v.osiloBekliyor = true;
    v.surekliZaman = null;
    const eskiST = globalThis.setTimeout;
    globalThis.setTimeout = () => 0;          // tur zincirini kurma
    try {
      v.surekliTur();
      ok('[!] Mesgulken yeni yakalama ISTENMIYOR', cagri === 0, `${cagri} cagri`);
      v.osiloBekliyor = false;
      v.surekliTur();
      ok('Bos kalinca yakalama ISTENIYOR', cagri === 1, `${cagri} cagri`);
    } finally {
      globalThis.setTimeout = eskiST;
    }
  }

  /* Varsayilan durum: kopru yokken bolum kapali ve liste bos. */
  const u = ornek();
  ok('Varsayilan: arsiv KAPALI (kart dogrudan bagliyken)',
     u.skopArsivVar === false && u.skopKayitlar.length === 0
     && u.skopAcikKayit === null);
}

/* ═══════════════════════════════════════════════════════════════════════
   17. SKOP GERILIM EKSENI KALIBRASYONU (B36)

   B34 kartta olctu: skopun gerilim ekseni ham kodu SABIT bir carpanla
   ceviriyordu ve bu varsayim tutmuyordu. Cipin eFuse egrisi `CT` ile
   geliyor, duzeltme CIZIM ANINDA uygulaniyor.

   🔴 EN ONEMLI IDDIA: ceviri TEK NOKTADAN geciyor. Eskiden
      `kod * voltAdim - voltOfset` DORT ayri yerde yaziliydi (tetik
      seviyesi, tepe degeri, dikey olcek, cizim dongusu). Duzeltme
      eklenince dordunun de degismesi gerekirdi; biri unutulsa izgara
      etiketi bir sey, iz baska sey gosterirdi ve hata SESSIZ olurdu.

   ⚠ Buradaki tablo GERCEK KARTTAN alindi (2026-09-12). Uydurulsaydi
     test kendi uydurmasini dogrulardi.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 17. Skop gerilim ekseni kalibrasyonu ---');
{
  const html = yorumsuz(htmlKaynak);
  const CT_SATIR = 'CT 17 oran=38.037037 ofset=63.530090 tavan_mv=3100.0'
    + ' 0:0 256:229 512:452 768:667 1024:883 1280:1095 1536:1309'
    + ' 1792:1524 2048:1739 2304:1954 2560:2165 2816:2372 3072:2568'
    + ' 3328:2750 3584:2914 3840:3053 4095:3160';

  const v = ornek();
  v.satirIsle(CT_SATIR);
  ok('CT satiri ayristiriliyor',
     !!v.skopKal && v.skopKal.kod.length === 17,
     v.skopKal ? `${v.skopKal.kod.length} nokta` : 'tablo yok');
  ok('Metaveri (oran/ofset/tavan) okunuyor',
     v.skopKal && Math.abs(v.skopKal.oran - 38.037037) < 1e-4
     && Math.abs(v.skopKal.tavanMv - 3100) < 1e-3);

  /* Tablo noktalarinda aradeger TAM deger vermeli. */
  ok('Tablo noktasinda aradeger tam',
     Math.abs(v.kalMv(2048) - 1739) < 1e-6
     && Math.abs(v.kalMv(0) - 0) < 1e-6,
     `${v.kalMv(2048)} / ${v.kalMv(0)}`);
  /* Iki nokta ARASINDA dogrusal. */
  ok('Noktalar arasi dogrusal aradeger',
     Math.abs(v.kalMv(2176) - (1739 + 1954) / 2) < 1e-6,
     String(v.kalMv(2176)));
  /* 🔴 Tablo disi KIRPILMIYOR, uzatiliyor: kirpilsaydi doyuma giren bir
     sinyal DUZ bir cizgi gibi gorunur ve kirpildigi anlasilmazdi. */
  ok('[!] Tablo disi kod KIRPILMIYOR (uzatiliyor)',
     v.kalMv(4500) > v.kalMv(4095),
     `kod 4500 -> ${v.kalMv(4500).toFixed(1)} mV`);

  /* Kalibreli cevirinin GERCEK sayisi. Kart oran=38.037, ofset=63.530
     bildiriyor; kod 2048 -> 1739 mV -> 1.739*38.037 - 63.530 V. */
  {
    const u = ornek();
    u.satirIsle(CT_SATIR);
    u.osilo = { voltAdim: 3.10 / 4096 * 38.03703704, voltOfset: 63.530090,
                veri: [2048] };
    const beklenen = 1739 / 1000 * 38.037037 - 63.530090;
    ok('[!] Kalibreli kod->volt cevirisi DOGRU sayiyi veriyor',
       Math.abs(u.kodVolt(2048) - beklenen) < 1e-4,
       `${u.kodVolt(2048).toFixed(4)} V (beklenen ${beklenen.toFixed(4)})`);

    /* Duzeltmesiz deger FARKLI olmali — aksi halde tablo hicbir sey
       yapmiyor demektir ve "kalibre" etiketi bos bir vaat olurdu. */
    const w = ornek();
    w.osilo = u.osilo;                      // ayni yakalama, tablo YOK
    const fark = Math.abs(u.kodVolt(2048) - w.kodVolt(2048));
    ok('[!] Duzeltme GERCEKTEN bir sey degistiriyor',
       fark > 1.0, `${fark.toFixed(3)} V fark (kod 2048)`);
    /* Kartta olculen buyukluk: kod 2048'de +7.19 V (bkz. DEVIR B36). */
    ok('Fark kartta olculen buyuklukte (+-%10)',
       Math.abs(fark - 7.189) < 0.72, `${fark.toFixed(3)} V vs 7.189 V`);
  }

  /* 🔴 TEK CEVIRI NOKTASI — dort cagri yeri de `kodVolt` kullaniyor. */
  ok('[!] Tetik seviyesi `kodVolt`tan geciyor',
     govdeIcinde(appKaynak, 'esikVolt', 'this.kodVolt(this.skopEsik)'));
  ok('[!] Tepe degeri `kodVolt`tan geciyor',
     govdeIcinde(appKaynak, 'osiloTepe', 'this.kodVolt('));
  ok('[!] Cizim dongusu ve dikey olcek `kodVolt`tan geciyor',
     govdeIcinde(appKaynak, 'osiloCiz', 'this.kodVolt(hmin)')
     && govdeIcinde(appKaynak, 'osiloCiz', 'this.kodVolt(v)'),
     'izgara etiketi ile iz AYNI cevirimden gelmeli');
  ok('Cizimde artik ham `voltAdim` carpimi KALMADI',
     !/\bveri\[i\]\s*\*\s*voltAdim/.test(appKaynak)
     && !govdeIcinde(appKaynak, 'osiloCiz', '* voltAdim'),
     'ikinci bir ceviri yolu kalsaydi ayrisirdi');

  /* Bozuk / eksik tablo SESSIZCE kullanilmamali. */
  {
    const z = ornek();
    z.satirIsle('CT 0 kaynak=YOK');
    ok('[!] `CT 0 kaynak=YOK` tabloyu KURMUYOR', z.skopKal === null);
    /* 🔴 Bozuk tablo SESSIZCE kullanilmamali. Onceki hali
       `y.skopKal === null || uzunluklar esit` idi ve MUTASYON KACTI:
       denetim silinince de gecen bir totolojiydi. Simdi her bozuk bicim
       AYRI AYRI reddediliyor ve eksen ESKI yola dusuyor. */
    const bozuklar = [
      ['oran YOK',        'CT 3 0:0 256:229 512:452'],
      ['tek nokta',       'CT 1 oran=38.0 0:0'],
      ['sayi degil (NaN)', 'CT 3 oran=38.0 0:0 256:abc 512:452'],
      ['oran NaN',        'CT 3 oran=elma 0:0 256:229 512:452'],
    ];
    for (const [ad, satir] of bozuklar) {
      const y = ornek();
      y.satirIsle(satir);
      ok(`[!] Bozuk tablo REDDEDILIYOR: ${ad}`, y.skopKal === null,
         JSON.stringify(y.skopKal));
    }
    /* Reddedilince eksen duzeltmesiz yola DUSMELI — yarim bir tabloyla
       cizmek yerine eski, bilinen davranis. */
    {
      const y = ornek();
      y.osilo = { voltAdim: 3.10 / 4096 * 38.03703704, voltOfset: 63.530090,
                  veri: [2048] };
      const ham = y.kodVolt(2048);
      y.satirIsle('CT 3 oran=38.0 0:0 256:abc 512:452');
      ok('[!] Bozuk tablodan sonra eksen ESKI yola dusuyor',
         Math.abs(y.kodVolt(2048) - ham) < 1e-9,
         `${y.kodVolt(2048).toFixed(4)} vs ${ham.toFixed(4)}`);
    }
  }

  /* 🔴 SUSMUYORUZ: eksenin kalibre olup olmadigi EKRANDA yaziyor.
     Yazmasaydi duzeltmesiz bir eksen "olculmus" gorunur ve sayilar
     sessizce yanlis okunurdu (B34: girisde 9 V'a varan sapma). */
  ok('[!] Eksenin kalibre olup olmadigi EKRANDA yaziyor',
     /v-if="skopKal"[\s\S]{0,200}eksen kalibre/.test(html) &&
     /v-else[\s\S]{0,200}eksen HAM/.test(html),
     'duzeltmesiz eksen "kalibre" sanilmamali');
  ok('Tablo yokken SEBEBI ve buyuklugu yaziliyor',
     /v-if="!skopKal"[\s\S]{0,400}9 V/.test(html),
     '"ham" demek yetmez — ne kadar saptigi soylenmeli');

  /* Sahte kart GERCEK kartin protokolunu konusmali. */
  ok('[!] Sahte kart da `CT` cevapliyor (demo gercek yoldan kosuyor)',
     /CT 17 oran=/.test(fs.readFileSync(
       path.join(KOK, 'arayuz3', 'sahte-kart.js'), 'utf8')),
     'ayrisirsa demo arayuzu gercek yolundan sinamaz');
}

/* ═══════════════════════════════════════════════════════════════════════
   18. HIZLI YOL OLCEKLEMESI KALIBRE MI (B39)

   Dogrusal ADC modeli sifir giriste -6.9 V / -397 mA ofset veriyordu ve
   `guc_olc` ortalamayi CIKARMADIGI icin bu dogrudan P, Vrms ve PF'ye
   giriyordu (1 W direncsel yukte P 3.56 W, PF 0.77). Firmware artik
   eFuse tablosuyla olcekliyor ve `W` satirinin 11. alaninda bunu
   SOYLUYOR. Arayuz susmamali.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 18. Hizli yol olceklemesi kalibre mi ---');
{
  const html = yorumsuz(htmlKaynak);
  const a = ornek();
  a.satirIsle('W 0.36314 0.36356 0.9988 1.8291 0.19876 -1.8283 -0.19859 297 0.36313 1');
  ok('[!] `W` 11. alan 1 -> kalibre', a.hizli && a.hizli.kal === true,
     JSON.stringify(a.hizli && a.hizli.kal));
  const b = ornek();
  b.satirIsle('W 0.36314 0.36356 0.9988 1.8291 0.19876 -1.8283 -0.19859 297 0.36313 0');
  ok('[!] `W` 11. alan 0 -> HAM (kalibre SANILMIYOR)', b.hizli && b.hizli.kal === false);
  const c = ornek();
  c.satirIsle('W 0.36314 0.36356 0.9988 1.8291 0.19876 -1.8283 -0.19859 297 0.36313');
  ok('[!] eski 10 alanli `W` hala ayristiriliyor ama kal=BILINMIYOR (null)',
     c.hizli && c.hizli.kal === null && Math.abs(c.hizli.p - 0.36314) < 1e-9,
     'eski firmware bilinmiyor demek; "kalibre" sanmak YANLIS olurdu');
  ok('[!] Ekranda uc durum da ayri yaziyor (kalibre / HAM / bilinmiyor)',
     /hizli\.kal === true[\s\S]{0,160}olçekleme kalibre|hizli\.kal === true[\s\S]{0,160}ölçekleme kalibre/.test(html)
     && /hizli\.kal === false[\s\S]{0,160}ölçekleme HAM/.test(html)
     && /ölçekleme bilinmiyor/.test(html));
  ok('Kalibresizken ofsetin BUYUKLUGU yaziyor',
     /hizli\.kal !== true[\s\S]{0,200}-6\.9 V/.test(html),
     '"ham" demek yetmez — ne kadar yanlis oldugu soylenmeli');
  ok('Sifir kalibrasyonunun HALA gerektigi yaziyor',
     /sıfır[\s\S]{0,20}kalibrasyonu/.test(html),
     'eFuse duzeltmesi on ucun sifir ofsetini gidermez');
}

/* ═══════════════════════════════════════════════════════════════════════
   19. SKOP DOKUMU OLCUMLE IC ICE (B40)

   Kart dokumu olcum dongusunu bloklamamak icin turlara boluyor; aradaki
   `D`/`K` satirlari dokumun ICINE dusuyor (kartta goruldu). Eskiden
   ayristirici BUTUN satirlari ornek sayiyordu.
   ═══════════════════════════════════════════════════════════════════════ */
console.log('\n--- 19. Skop dokumu olcumle ic ice ---');
{
  const u = ornek();
  u.osiloBitir = function () { this.bitti = this.osiloTopla; this.osiloTopla = null; };
  u.satirIsle('S2 20 1000 0.028788 0 100 0 1 63.530090');
  u.satirIsle('M f=0.000 T=0.000000000 Vpp=1.0000 Vmax=1.0 Vmin=0.0 Vort=0.5 Vrms=0.5 Vac=0.1 duty=0.00 tr=0 tf=0 n=0');
  u.satirIsle('1 2 3 4 5 6 7 8 9 10');
  u.satirIsle('D 12.3456 0.891234 10.99881 1234.5678 0.3429355 3600000 133 0');
  u.satirIsle('K 0 2603 0');
  u.satirIsle('11 12 13 14 15 16 17 18 19 20');
  const beklenen = Array.from({ length: 20 }, (_, i) => i + 1);
  const veri = u.bitti ? u.bitti.veri : (u.osiloTopla ? u.osiloTopla.veri : []);
  ok('[!] Araya giren D/K satiri dalgaya ORNEK olarak girmiyor',
     JSON.stringify(veri) === JSON.stringify(beklenen),
     JSON.stringify(veri));
  ok('[!] Araya giren D satiri olcum gostergesine YINE ulasiyor',
     Math.abs(u.volt - 12.3456) < 1e-6, String(u.volt));

  /* WiFi: sabit 400 ms bekleme kaldirildi, onay satiri tetikliyor. */
  ok('[!] `tB` sonrasi sabit gecikmeli cekis YOK',
     !govdeIcinde(appKaynak, 'osiloYakala', 'setTimeout(() => this.skopIkiliAl()'),
     'tb7 ve ustunde yakalama 400 ms\'den uzun -> /skop.bin 503');
  const v = ornek();
  let cekildi = 0;
  v.skopIkiliAl = () => { cekildi++; };
  v.skopIkiliBekle = true;
  v.satirIsle('* skop yakalandi (ikili): 833 ornek @ 83333 Hz — /skop.bin');
  ok('[!] Onay satiri GELINCE govde cekiliyor', cekildi === 1, String(cekildi));
  v.satirIsle('* skop yakalandi (ikili): 833 ornek @ 83333 Hz — /skop.bin');
  ok('Beklenmeyen ikinci onay IKINCI cekis yapmiyor', cekildi === 1, String(cekildi));
  const y = ornek();
  let c2 = 0;
  y.skopIkiliAl = () => { c2++; };
  y.skopIkiliBekle = true;
  y.satirIsle('! tetiklenemedi');
  y.satirIsle('* skop yakalandi (ikili): 1 ornek @ 1 Hz — /skop.bin');
  ok('`!` satiri bekleyen ikili cekisi IPTAL ediyor', c2 === 0 && y.skopIkiliBekle === false);
}

/* Asenkron iddialar OZETTEN ONCE — sayilsinlar diye. Kuyruk bu
   fonksiyonun govdesinde (bolum 13) dolduruluyor; bosaltma burada,
   ozetin hemen oncesinde. */
for (const f of SONRA) await f();

console.log(`\n${gecti}/${gecti + kaldi} dogrulama gecti`);

/* ── TEZGAH KALEMLERI (B23.1) ──────────────────────────────────────────
   Bicim `uretim/tezgah.py` ile AYNI olmali — dogrula3.py ikisini de ayni
   ayristiriciyla topluyor. Node tarafinda ayri bir modul yazmak yerine
   uc satirlik ciktiyi burada uretmek yeterli; bicim degisirse tek yer
   (tezgah.py) degil IKI yer guncellenmeli — bu bilincli bir odun ve
   sim3_web.py'de bir iddia bunu civiliyor. */
function tezgah(adim, kalemler) {
  if (!kalemler.length) return;
  console.log('');
  console.log(`  === TEZGAH: ${adim} ===`);
  for (const [kalem, kabul] of kalemler) {
    console.log(`  [T] ${kalem}`);
    console.log(`      -> ${kabul}`);
  }
}

tezgah('B7 Arayuz', [
  ['[!] Arayuz tarayicida GERCEKTEN dogru gorunuyor mu',
   'Bu adim Vue`yu TAKLIT ediyor; sayfa hic render edilmiyor. B22.0`da '
   + 'arayuz zincir 15/15 yesilken tarayicida HIC acilmiyordu. '
   + '`python arayuz3/sunucu.py` -> konsolda 0 hata, ham {{ }} yok'],
  ['J7/J3 baypas uyarisi KIRMIZI seritli gorunuyor mu',
   'Emniyet uyarisi govde metninden ayirt edilebilmeli. B22.0 oncesi '
   + '`.uyari` sinifi hic tanimli degildi ve duz paragraf olarak cikiyordu'],
  ['Osiloskop iki yoldan da AYNI cizimi veriyor mu',
   'USB`de ASCII, WiFi`de ikili (/skop.bin) yol kullaniliyor. Ayni '
   + 'sinyalde iki kip AYNI dalgayi cizmeli; farkliysa cozuculerden biri '
   + 'yanlis (endian, olcek ya da ofset)'],
  ['Telefonda Ana Ekrana Ekle',
   'iPhone: adres cubugu OLMADAN, kendi ikonuyla acilmali. '
   + 'Android: kisayol Chrome sekmesinde acilir — bu beklenen davranis, '
   + 'gercek PWA kurulumu HTTPS istiyor'],
]);

process.exit(kaldi ? 1 : 0);
}

