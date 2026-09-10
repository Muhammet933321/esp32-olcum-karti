/* ═══════════════════════════════════════════════════════════════════════
   S10 — Zincirin son halkasi.

   node uretim/test_arayuz_akis.js <akis.txt> <beklenenV> <beklenenA>

   <akis.txt> SIMULE EDILEN GERCEK FIRMWARE'in seri portundan cikardigi
   ham baytlardir (uretim/sim_kart.py uretir). Burada elle yazilmis hicbir
   ornek satir yok: arayuzun kendi ayristiricisi, kartin kendi ciktisini
   okuyor. Ekranda gorunecek metin ne ise o basiliyor.
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const APP = path.join(__dirname, '..', 'arsiv', 'asama1', 'arayuz', 'app.js');

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

const akisYolu = process.argv[2];
const beklenenV = parseFloat(process.argv[3]);
const beklenenA = parseFloat(process.argv[4]);

const ham = fs.readFileSync(akisYolu, 'utf8');
const satirlar = ham.split(/\r?\n/);

const u = ornek();
for (const s of satirlar) u.satirIsle(s);

console.log(`Kartin gonderdigi ${ham.length} bayt / ${satirlar.length} satir ` +
            `arayuze verildi\n`);

ok('Arayuz en az bir olcum ayristirdi', u.gecmis.length > 0,
   `${u.gecmis.length} nokta`);
ok('Ekrandaki gerilim uygulanan gerilime esit',
   Math.abs(u.volt - beklenenV) < 0.05,
   `${u.bicim(u.volt, 4)} V  (uygulanan ${beklenenV.toFixed(2)} V)`);
ok('Ekrandaki akim uygulanan akima esit',
   Math.abs(u.amper - beklenenA) < 0.0005,
   `${u.akimGoster} ${u.akimBirim}  (uygulanan ${(beklenenA * 1000).toFixed(2)} mA)`);
ok('Ekrandaki guc = gerilim x akim',
   Math.abs(u.watt - u.volt * u.amper) < Math.max(u.watt * 0.02, 1e-6),
   `${u.gucGoster} ${u.gucBirim}`);
ok('Enerji alanlari dolduruldu', u.joule > 0 && u.wh > 0,
   `${u.joule.toFixed(4)} J = ${u.wh.toFixed(7)} Wh`);
ok('Ornekleme hizi hesaplandi', u.orneklemeHizi !== '—', u.orneklemeHizi);
ok('Gurultu bastirma gosterildi', u.gurultuBastirma.length > 0,
   u.gurultuBastirma);
ok('Gecmis zaman ekseni artiyor',
   u.gecmis.length < 2 || u.gecmis[u.gecmis.length - 1].t > u.gecmis[0].t,
   `${u.gecmis[0].t.toFixed(3)} s -> ${u.gecmis[u.gecmis.length - 1].t.toFixed(3)} s`);
ok('Veri satirlari gunluge dusmedi',
   u.gunluk.every(g => !String(g.metin || g).startsWith('D ')),
   `${u.gunluk.length} gunluk kaydi`);

const jsonKac = u.gecmis.filter(g => !isFinite(g.v) || !isFinite(g.i)).length;
ok('Hicbir noktada NaN yok', jsonKac === 0);

console.log(`\n  EKRANDA GORUNEN:  ${u.bicim(u.volt, 4)} V   ` +
            `${u.akimGoster} ${u.akimBirim}   ${u.gucGoster} ${u.gucBirim}   ` +
            `${u.joule.toFixed(4)} J`);
console.log(`\n  ${gecti}/${gecti + kaldi} dogrulama gecti`);
process.exit(kaldi === 0 ? 0 : 1);
