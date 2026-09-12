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
   govdeIcinde(appKaynak, 'skopIkiliAl', 'osiloBitir()') &&
   appKaynak.includes("satir.trim() === 'E'"),
   'ikili yol da osiloBitir(), ASCII yol da');
ok('B22.5: yakalama YETENEGE gore yol seciyor',
   govdeIcinde(appKaynak, 'osiloYakala', "yetenek.skop === 'ikili'") &&
   govdeIcinde(appKaynak, 'osiloYakala', "gonder('tB')"),
   'ayni veriyi ASCII + ikili olarak IKI KEZ tasima');
/* Kismi ya da yanlis yanit SESSIZCE cizilmemeli — bu, `pilYokla`'nin
   B22.2'de kapatilan sessiz-sifir kusurunun ikili karsiligi. */
ok('B22.5: ikili yanit IMZASI denetleniyor',
   govdeIcinde(appKaynak, 'skopIkiliAl', '0x53') &&
   govdeIcinde(appKaynak, 'skopIkiliAl', 'imzası'),
   'S3B degilse cizme, SEBEBINI soyle');
ok('B22.5: ikili yanit UZUNLUGU denetleniyor',
   govdeIcinde(appKaynak, 'skopIkiliAl', '32 + adet * 2'),
   'kesik govde sessizce yarim grafik cizmesin');
/* [!] Endian ACIKCA kucuk: `Uint16Array` platformun endian'ini kullanir
   ve bir gun sessizce ters okuyabilirdi. */
ok('B22.5: endian ACIKCA kucuk-endian',
   govdeIcinde(appKaynak, 'skopIkiliAl', 'getUint16(32 + i * 2, true)') &&
   !govdeIcinde(appKaynak, 'skopIkiliAl', 'new Uint16Array'),
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
  ok('demo W satiri 10 alanli', w[0].split(/\s+/).length === 10,
     String(w[0].split(/\s+/).length));
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
  ok('ek.css bagli', htmlKaynak.includes('ek.css'));
  /* CSS tuzagi: display tanimlayan sinif [hidden] kuralini ezer.
     ek.css'te display kullanilmadigindan emin ol. */
  const ek = fs.readFileSync(path.join(ARAYUZ, 'ek.css'), 'utf8');
  ok('ek.css `button.etkin` icinde display kullanmiyor ([hidden] tuzagi)',
     !/button\.etkin\s*\{[^}]*display/.test(ek));
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
  const cssYollari = ['style.css', 'ek.css'].map((d) => path.join(ARAYUZ, d));
  ok('style.css ve ek.css diskte var',
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
  const tumCss = ['style.css', 'ek.css']
    .map((d) => fs.readFileSync(path.join(ARAYUZ, d), 'utf8')).join('\n');
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
  const ctx = new Proxy({}, {
    get: (_, ad) => (...args) => { cagri.push([ad, args]); },
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
    ok('baglan(): kimlikten sonra `?` JETONLA gitti',
       gidenler.length === 1 && gidenler[0].metin === '?' && gidenler[0].jeton === 'xyz789',
       JSON.stringify(gidenler));

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
    bolum12Bitti();
  })();
}

function bolum12Bitti() {
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

