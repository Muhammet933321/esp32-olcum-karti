/* ═══════════════════════════════════════════════════════════════════════
   S7 — Arayuz mantiginin testi   (node uretim/test_arayuz.js)

   Vue ve DOM taklit edilip app.js yukleniyor, sonra firmware'in gercekten
   urettigi satirlar ayristiriciya veriliyor. Boylece arayuz tarayici
   acilmadan test ediliyor.
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const APP = path.join(__dirname, '..', 'arsiv', 'asama1', 'arayuz', 'app.js');

// ── Vue taklidi: createApp cagrilinca secenekleri yakala
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

// ── sahte ornek: data() + methods + computed, $nextTick yutuluyor
function ornek() {
  const o = Object.assign({}, secenekler.data());
  Object.assign(o, secenekler.methods);
  o.$nextTick = () => {};
  o.$refs = {};
  o.grafikCiz = () => {};
  o.osiloCiz = () => {};
  // computed'lari getter olarak bagla
  for (const [ad, fn] of Object.entries(secenekler.computed || {})) {
    Object.defineProperty(o, ad, { get: fn.bind(o) });
  }
  return o;
}

// ── kucuk test cercevesi
let gecti = 0, kaldi = 0;
function ok(ad, kosul, ek = '') {
  if (kosul) { gecti++; console.log(`[OK] ${ad}${ek ? '  ' + ek : ''}`); }
  else { kaldi++; console.log(`[!!] ${ad}${ek ? '  ' + ek : ''}`); }
}
function yakin(ad, a, b, tol = 1e-9) {
  ok(ad, Math.abs(a - b) <= tol, `${a} ≈ ${b}`);
}

console.log('S7 — Arayuz mantigi (arayuz/app.js)\n');

// ─────────────────────────────────────────── 1. olcum satiri
{
  const u = ornek();
  u.satirIsle('D 12.3456 0.025300 0.312345 1.2340 0.0003428 45678');

  yakin('Gerilim ayristirildi', u.volt, 12.3456);
  yakin('Akim ayristirildi', u.amper, 0.0253);
  yakin('Guc ayristirildi', u.watt, 0.312345);
  yakin('Joule ayristirildi', u.joule, 1.234);
  yakin('Wh ayristirildi', u.wh, 0.0003428);
  ok('Gecmise eklendi', u.gecmis.length === 1);
  yakin('Ilk ornek t=0', u.gecmis[0].t, 0);

  // ikinci ornek: zaman ilk ornege gore
  u.satirIsle('D 12.0 0.02 0.24 1.5 0.0004 46678');
  yakin('Ikinci ornek t=1 sn', u.gecmis[1].t, 1.0);
  ok('Gunluge dusmedi (veri satiri)', u.gunluk.length === 0,
     `gunluk=${u.gunluk.length}`);
}

// ─────────────────────────────────────────── 2. birim olcekleme
{
  const u = ornek();
  const dene = (a, bd, bb) => {
    u.amper = a;
    ok(`${a} A -> ${u.akimGoster} ${u.akimBirim}`,
       u.akimBirim === bb, `beklenen birim ${bb}`);
  };
  dene(1.5, null, 'A');
  dene(0.0253, null, 'mA');
  dene(0.000015, null, 'µA');

  // Esikler: >=1 W -> W, >=1 mW -> mW, altinda µW
  u.watt = 2.5;     ok('2.5 W  -> W',  u.gucBirim === 'W',  u.gucGoster + ' ' + u.gucBirim);
  u.watt = 0.005;   ok('5 mW   -> mW', u.gucBirim === 'mW', u.gucGoster + ' ' + u.gucBirim);
  u.watt = 0.0005;  ok('0.5 mW -> µW', u.gucBirim === 'µW', u.gucGoster + ' ' + u.gucBirim);
}

// ─────────────────────────────────────────── 3. osiloskop akisi
{
  const u = ornek();
  u.satirIsle('S 8 76923 0.106480');
  ok('Osiloskop basligi yakalandi', u.osiloTopla !== null &&
     u.osiloTopla.adet === 8);
  ok('  baslik gunluge dusmedi', u.gunluk.length === 0);

  u.satirIsle('10 20 30 40');
  ok('Kismi veri toplaniyor', u.osilo === null &&
     u.osiloTopla.veri.length === 4, `${u.osiloTopla.veri.length}/8`);

  u.satirIsle('50 60 70 80');
  ok('Tamamlaninca osilo dolduruldu', u.osilo !== null &&
     u.osilo.veri.length === 8);
  ok('  toplama durumu temizlendi', u.osiloTopla === null);
  ok('  bekleme bayragi indi', u.osiloBekliyor === false);
  yakin('  tepe gerilim = 80 x voltAdim', u.osiloTepe, 80 * 0.10648, 1e-9);

  // fazla deger gelirse kirpilmali
  const v = ornek();
  v.satirIsle('S 3 76923 0.1');
  v.satirIsle('1 2 3 4 5 6');
  ok('Fazla ornek kirpildi', v.osilo.veri.length === 3,
     `${v.osilo.veri.length} ornek`);
}

// ─────────────────────────────────────────── 4. diger satirlar gunluge
{
  const u = ornek();
  u.satirIsle('--- ayarlar ---');
  u.satirIsle('  sont      : 10.0000 ohm');
  ok('Metin satirlari gunluge dustu', u.gunluk.length === 2);

  u.osiloBekliyor = true;
  u.satirIsle('! tetiklenemedi');
  ok('Tetikleme hatasi bekleme bayragini indirdi', u.osiloBekliyor === false);

  u.satirIsle('');
  ok('Bos satir yok sayildi', u.gunluk.length === 3);
}

// ─────────────────────────────────────────── 5. gecmis budama
{
  const u = ornek();
  for (let i = 0; i < 20050; i++) {
    u.satirIsle(`D 5 0.01 0.05 1 0.0001 ${i * 200}`);
  }
  ok('Gecmis sinirsiz buyumuyor', u.gecmis.length <= 20000,
     `${u.gecmis.length} kayit`);
  ok('  en yeni kayit korundu',
     Math.abs(u.gecmis[u.gecmis.length - 1].t - 20049 * 0.2) < 1e-6);
}

// ─────────────────────────────────────────── 6. sure bicimi
{
  const u = ornek();
  u.gecmis = [{ t: 45 }];   ok('45 sn', u.sureGoster === '45 sn', u.sureGoster);
  u.gecmis = [{ t: 125 }];  ok('2 dk 5 sn', u.sureGoster === '2dk 5sn', u.sureGoster);
  u.gecmis = [{ t: 7325 }]; ok('2 saat 2 dk', u.sureGoster === '2s 2dk', u.sureGoster);
  u.gecmis = [];            ok('veri yokken tire', u.sureGoster === '—', u.sureGoster);
}

console.log(`\n  ${gecti}/${gecti + kaldi} dogrulama gecti`);
process.exit(kaldi ? 1 : 0);
