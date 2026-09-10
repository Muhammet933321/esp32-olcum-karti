/* ═══════════════════════════════════════════════════════════════════════
   A5 — Osiloskop protokolu ile arayuz arasindaki koprü.

   node uretim/test_skop_arayuz.js

   Asama 2 firmware'i `S2` basligi, `M` olcum satiri, ham ADC kodlari ve
   `E` sonlandiricisi yayinliyor. Bu test ONLARI ELLE YAZMIYOR: butun
   sabitler olcum-karti-a2.ino ve olcum2.h kaynagindan okunuyor, akis o
   sabitlerden uretiliyor ve arayuzun KENDI ayristiricisi (arayuz/app.js)
   onu okuyor.

   Boylece firmware'deki bir sabit degisirse test kendiliginden onu takip
   eder; ikisi sessizce ayrisamaz.
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const KOK = path.join(__dirname, '..');
const INO = path.join(KOK, 'arsiv', 'asama2', 'olcum-karti-a2', 'olcum-karti-a2.ino');
const H = path.join(KOK, 'arsiv', 'asama2', 'olcum-karti-a2', 'olcum2.h');
const APP = path.join(KOK, 'arsiv', 'asama1', 'arayuz', 'app.js');

let gecti = 0, kaldi = 0;
function ok(ad, kosul, ek = '') {
  if (kosul) { gecti++; console.log(`  [OK] ${ad}${ek ? '  ' + ek : ''}`); }
  else { kaldi++; console.log(`  [!!] ${ad}${ek ? '  ' + ek : ''}`); }
}
function yakin(ad, a, b, tol, birim = '') {
  ok(ad, Math.abs(a - b) <= tol,
     `${a.toFixed(6)}${birim} ~ ${b.toFixed(6)}${birim}`);
}

// ─────────────────────────────── 1. sabitleri KAYNAKTAN cek
const ino = fs.readFileSync(INO, 'utf8');
const h = fs.readFileSync(H, 'utf8');
const app = fs.readFileSync(APP, 'utf8');

function sabit(metin, ad) {
  const m = metin.match(new RegExp(`${ad}\\s*=\\s*([0-9.]+)f?\\s*;`));
  if (!m) throw new Error(`kaynakta bulunamadi: ${ad}`);
  return parseFloat(m[1]);
}
function makro(metin, ad) {
  const m = metin.match(new RegExp(`#define\\s+${ad}\\s+([0-9.]+)f?`));
  if (!m) throw new Error(`kaynakta bulunamadi: ${ad}`);
  return parseFloat(m[1]);
}

const TAVAN = makro(h, 'SKOP_ADC_TAVAN');
const SAYIM = makro(h, 'SKOP_ADC_SAYIM');
const ORAN = makro(h, 'BOLME_ORANI');
const VOLT_ADIM = TAVAN / SAYIM * ORAN;
const HZ_AZAMI = sabit(ino, 'SKOP_HZ_AZAMI');
const HZ_ASGARI = sabit(ino, 'SKOP_HZ_ASGARI');
const BOLME = sabit(ino, 'SKOP_BOLME');

// Zaman tabani merdiveni — firmware ve arayuz AYNI listeyi tasimali
function tdivListesi(metin, desen) {
  const m = metin.match(desen);
  if (!m) throw new Error('zaman tabani listesi bulunamadi');
  return m[1].split(',').map((x) => parseInt(x.trim(), 10))
             .filter((x) => !isNaN(x));
}
const TDIV_INO = tdivListesi(ino, /SKOP_TDIV_US\[\]\s*=\s*\{([^}]*)\}/);
const TDIV_APP = tdivListesi(app, /const SKOP_TDIV\s*=\s*\[([^\]]*)\]/);

console.log(`\n  kaynaktan: tavan=${TAVAN} sayim=${SAYIM} oran=${ORAN}`);
console.log(`  hiz ${HZ_ASGARI}..${HZ_AZAMI} Sa/s, ${BOLME} bolme`);
console.log(`  volt/adim = ${VOLT_ADIM.toFixed(6)} V, tam olcek ` +
            `${(VOLT_ADIM * SAYIM).toFixed(1)} V`);
console.log(`  zaman tabani: ${TDIV_INO.length} kademe ` +
            `${TDIV_INO[0]} us .. ${TDIV_INO[TDIV_INO.length - 1]} us`);

// ─────────────────────────────── 2. zaman tabani mantigi
console.log('\n  --- zaman tabani ---');
ok('Firmware ve arayuz AYNI zaman tabani merdivenini tasiyor',
   JSON.stringify(TDIV_INO) === JSON.stringify(TDIV_APP),
   `${TDIV_INO.length} vs ${TDIV_APP.length} kademe`);

// skop_taban_coz()'un JS karsiligi — .ino'daki formulun aynisi
function tabanCoz(tdivUs) {
  const pencere = tdivUs * BOLME * 1e-6;
  let hz = (BOLME * 100) / pencere;
  if (hz > HZ_AZAMI) hz = HZ_AZAMI;
  if (hz < HZ_ASGARI) hz = HZ_ASGARI;
  hz = Math.round(hz);
  let n = Math.round(pencere * hz);
  if (n > 4000) n = 4000;
  if (n < 100) n = 100;
  return { hz, n, pencere };
}

const AZAMI_ADET = sabit(ino, 'SKOP_AZAMI_ADET');
let tumGecerli = true, enUzun = 0, enKisa = Infinity;
for (const td of TDIV_INO) {
  const { hz, n, pencere } = tabanCoz(td);
  if (hz < HZ_ASGARI || hz > HZ_AZAMI || n < 100 || n > AZAMI_ADET)
    tumGecerli = false;
  enUzun = Math.max(enUzun, pencere);
  enKisa = Math.min(enKisa, pencere);
}
ok('Her kademe donanim sinirlari icinde kaliyor', tumGecerli,
   `hiz ${HZ_ASGARI}..${HZ_AZAMI}, adet 100..${AZAMI_ADET}`);
ok('En uzun pencere >= 1 s (50 Hz rahat sigar)', enUzun >= 1.0,
   `${enUzun.toFixed(2)} s`);
ok('En kisa pencere <= 2 ms (hizli kenar gorunur)', enKisa <= 2e-3,
   `${(enKisa * 1e3).toFixed(2)} ms`);

// 50 Hz'in tam cevrimi hangi kademelerde siger — ESKI KUSUR buydu
const T50 = 1 / 50;
const sigan = TDIV_INO.filter((td) => tabanCoz(td).n / tabanCoz(td).hz >= T50);
ok('50 Hz icin en az bir tam cevrim sigan kademe VAR', sigan.length > 0,
   `${sigan.length} kademe`);

// ─────────────────────────────── 3. akisi uret
const KADEME = 6;                       // 10 ms/bolme
const { hz: FS, n: ADET } = tabanCoz(TDIV_INO[KADEME]);
const TETIK = Math.round(ADET * 0.25);

// 50 Hz sinus: gercek kullanim durumu
const kodlar = [];
for (let i = 0; i < ADET; i++) {
  const t = i / FS;
  kodlar.push(Math.round(2048 + 1500 * Math.sin(2 * Math.PI * 50 * t)));
}

const satirlar = [];
satirlar.push(`S2 ${ADET} ${FS} ${VOLT_ADIM.toFixed(6)} ${TETIK} ` +
              `${TDIV_INO[KADEME]} 0 1`);
satirlar.push('M f=50.000 T=0.020000000 Vpp=35.669 Vmax=42.234 Vmin=6.565 ' +
              'Vort=24.350 Vrms=27.243 Vac=12.611 duty=50.00 ' +
              'tr=0.000000000 tf=0.000000000 n=4');
let parca = [];
for (let i = 0; i < ADET; i++) {
  parca.push(String(kodlar[i]));
  if (i % 16 === 15) { satirlar.push(parca.join(' ')); parca = []; }
}
if (parca.length) satirlar.push(parca.join(' '));
satirlar.push('E');

// ─────────────────────────────── 4. arayuzun KENDI ayristiricisi
let secenekler = null;
const sandbox = {
  Vue: { createApp(o) { secenekler = o; return { mount() { return {}; } }; } },
  navigator: { serial: {} },
  window: { addEventListener() {}, devicePixelRatio: 1 },
  document: { documentElement: {}, createElement: () => ({ click() {} }) },
  getComputedStyle: () => ({ getPropertyValue: () => '#000' }),
  setTimeout: () => 0,
  location: { search: '' },
  console,
};
vm.createContext(sandbox);
vm.runInContext(app, sandbox, { filename: 'app.js' });

const o = Object.assign({}, secenekler.data());
Object.assign(o, secenekler.methods);
o.$nextTick = () => {};
o.$refs = {};
o.grafikCiz = () => {};
o.osiloCiz = () => {};
for (const [ad, fn] of Object.entries(secenekler.computed || {})) {
  Object.defineProperty(o, ad, { get: fn.bind(o) });
}

console.log('\n  --- arayuz akisi ---');
for (const s of satirlar) o.satirIsle(s);

// ─────────────────────────────── 5. denetimler
ok('Arayuz yakalamayi tamamladi', o.osilo !== null);
if (o.osilo) {
  ok('Ornek adedi firmware ile ayni', o.osilo.adet === ADET, `${o.osilo.adet}`);
  ok('Ornekleme hizi firmware ile ayni', o.osilo.hz === FS, `${o.osilo.hz} Sa/s`);
  ok('Toplanan ornek sayisi basliktaki adede esit',
     o.osilo.veri.length === ADET, `${o.osilo.veri.length}`);
  ok('Tetik konumu tasindi', o.osilo.tetikIdx === TETIK, `${o.osilo.tetikIdx}`);
  ok('Zaman tabani tasindi', o.osilo.tdivUs === TDIV_INO[KADEME],
     `${o.osilo.tdivUs} us`);
  ok('Tetiklendi bayragi tasindi', o.osilo.tetiklendi === true);
  yakin('volt/adim kaynaktan turetilene esit',
        o.osilo.voltAdim, VOLT_ADIM, 1e-6, ' V');
  ok('Kodlar bit birebir geri geldi',
     o.osilo.veri.every((v, i) => v === kodlar[i]));
  ok('Arayuz zaman tabani indeksini basliktan ogrendi',
     o.skopTdiv === KADEME, `${o.skopTdiv} == ${KADEME}`);

  // M satiri ayristirildi mi
  ok('M olcum satiri ayristirildi', o.osilo.olcum !== null);
  if (o.osilo.olcum) {
    yakin('Frekans alani', o.osilo.olcum.f, 50.0, 1e-6, ' Hz');
    yakin('Vpp alani', o.osilo.olcum.Vpp, 35.669, 1e-6, ' V');
    yakin('Duty alani', o.osilo.olcum.duty, 50.0, 1e-6, ' %');
  }
  const l = o.skopOlcumler;
  ok('Olcum paneli doldu', l.length >= 8, `${l.length} kalem`);
  ok('Panelde frekans var',
     l.some((x) => x.ad === 'Frekans' && x.d.includes('50.0')));

  // Tam olcek ve Nyquist
  yakin('Tam olcek tasarim belgesiyle uyumlu (48.7 V)',
        VOLT_ADIM * SAYIM, 48.7, 0.1, ' V');
  ok('Bu kademede 50 Hz icin >= 1 tam cevrim var',
     (ADET / FS) * 50 >= 1.0, `${((ADET / FS) * 50).toFixed(2)} cevrim`);
  ok('Uyari yok (kademe uygun)', o.skopUyari === '', `"${o.skopUyari}"`);
}

// ─────────────────────────────── 6. arayuz Asama 2 komutlarini gonderiyor mu
console.log('\n  --- komut kumesi ---');
const gonderilen = [];
o.gonder = (k) => gonderilen.push(k);
o.sontSecim = '10'; o.sontGonder();
o.kalibV = '12.05'; o.kalibreV();
o.kalibA = '0.1187'; o.kalibreA();
o.skopTdiv = 5; o.tabanDegistir(1);
o.osiloOtomatik();

ok('Sont komutu Asama 2 bicimi (s<ohm>)', gonderilen[0] === 's10',
   gonderilen[0]);
ok('Gerilim kalibresi Asama 2 bicimi (v<gercek>)', gonderilen[1] === 'v12.05',
   gonderilen[1]);
ok('Akim kalibresi Asama 2 bicimi (i<gercek>)', gonderilen[2] === 'i0.1187',
   gonderilen[2]);
ok('Zaman tabani komutu (tb<n>)', gonderilen[3] === 'tb6', gonderilen[3]);
ok('Otomatik kurulum komutu (ta)', gonderilen[4] === 'ta', gonderilen[4]);

// ─────────────────────────────── 7. firmware kaynaginda dallar duruyor mu
console.log('\n  --- firmware kaynagi ---');
ok('Tetikleme basarisizlik dali duruyor',
   ino.includes('! tetiklenemedi'));
ok('Histerezis mantigi duruyor', /histerezis/.test(ino) &&
   /hazir = true/.test(ino));
ok('On-tetik halka tamponu duruyor', /on_yuzde/.test(ino) &&
   /% n\)/.test(ino));
ok('Otomatik kurulum duruyor', /skop_otomatik/.test(ino));
ok('S2 basligi duruyor', ino.includes('S2 '));
ok('E sonlandiricisi duruyor', /println\(F\("E"\)\)/.test(ino));

console.log(`\n  ${gecti} gecti, ${kaldi} kaldi`);
process.exit(kaldi ? 1 : 0);
