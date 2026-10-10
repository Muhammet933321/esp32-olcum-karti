// README ekran goruntuleri: panel demo kipi (py demo_sunucu.py, port 8772), PC koprusu
// (kopru/pc.py, http://olcum.localhost:8770) ve BELGELER/*.html.
// Kullanim: node cek.js <is> [...]   (isler asagida; CIKIS ortam degiskeni cikis klasoru)
// Gizlilik: Ayarlar -> Ag / Eslestirme / Bu telefon CEKILMEZ (ag adi, IP, kart kimligi).
const path = require('path');
// Playwright depoya bagimlilik olarak girmez: yolu PLAYWRIGHT ortam degiskeniyle verin (yoksa 'playwright' aranir).
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');

const CIKIS = process.env.CIKIS || path.join(__dirname, '..', '..', 'gorsel', 'readme');
const KOK = process.env.KOK || path.join(__dirname, '..', '..');
const belge = (ad) => 'file:///' + path.join(KOK, 'BELGELER', ad).split(path.sep).join('/');
const DEMO = 'http://localhost:8772/?demo';
const KOPRU = 'http://olcum.localhost:8770/';
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

async function sayfa(tarayici, { gen = 1440, yuk = 900 } = {}) {
  const ctx = await tarayici.newContext({ viewport: { width: gen, height: yuk }, deviceScaleFactor: 1, locale: 'tr-TR' });
  const p = await ctx.newPage();
  p.on('pageerror', (e) => console.log('  [sayfa hatasi]', e.message.slice(0, 160)));
  return p;
}

async function cek(p, ad, secenek = {}) {
  await p.screenshot({ path: path.join(CIKIS, ad), ...secenek });
  console.log('  ->', ad);
}

const ISLER = {
  // Canli: grafik tembel modulle ~15 s'de gelir; pencere dolsun diye uzun bekle
  async canli(t) {
    const p = await sayfa(t);
    await p.goto(DEMO + '#/canli');
    await bekle(50000);
    await cek(p, 'pc-canli.png');
  },
  async skop(t) {
    const p = await sayfa(t);
    await p.goto(DEMO + '#/skop');
    await bekle(4000);
    await p.locator('select:has(option[value="sinus50"])').selectOption({ index: Number(process.env.SKOP_SINYAL || 2) });   // 2 = 1 kHz kare
    await bekle(800);
    await p.getByRole('button', { name: 'Otomatik', exact: true }).click();
    await bekle(4000);
    await p.getByRole('button', { name: 'Yakala', exact: true }).click();
    await bekle(6000);
    await cek(p, 'pc-skop.png');
  },
  async pil(t) {
    const p = await sayfa(t);
    await p.goto(DEMO + '#/pil');
    await bekle(4000);
    await p.getByRole('button', { name: 'Li-ion 3.0 V' }).click();
    await p.locator('#pil-ad').fill('18650 örnek');
    await p.getByRole('button', { name: 'Testi başlat' }).click();
    await bekle(Number(process.env.PIL_MS || 60000));
    await p.evaluate(() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); document.querySelectorAll('main, .icerik, [class*=icerik]').forEach((e) => { e.scrollTop = 0; }); });
    await bekle(500);
    await cek(p, 'pc-pil.png');
  },
  // PC koprusu: gercek arsiv (Kayitlar, kayit gorunumu, Karsilastirma, Baglanti penceresi)
  async 'pc-kayitlar'(t) {
    const p = await sayfa(t);
    await p.goto(KOPRU + '#/kayitlar');
    await bekle(15000);
    await cek(p, 'pc-kayitlar.png');
  },
  async 'pc-kayit'(t) {
    const p = await sayfa(t);
    await p.goto(KOPRU + '#/kayit/' + (process.env.OTURUM || '64955'));
    await bekle(20000);
    await p.evaluate(() => document.activeElement && document.activeElement.blur());
    const g = p.locator('canvas:visible').first().locator('xpath=ancestor::section[1]');
    // sade gorunum: en dusuk / en yuksek bandi kapali (yalniz ortalama cizgisi)
    if (process.env.MINMAX !== '1') { await g.locator('label', { hasText: 'En düşük / en yüksek' }).locator('input').uncheck(); await bekle(1500); }
    await cek(g, 'pc-kayit.png');
  },
  async 'pc-karsilastir'(t) {
    const p = await sayfa(t);
    await p.goto(KOPRU + '#/kayitlar');
    await bekle(12000);
    for (const no of (process.env.KARSI || '64702,64446,64159').split(',')) {
      await p.locator('input[data-kl-sec$=":' + no + '"]').check();
    }
    await p.getByRole('link', { name: 'Karşılaştır', exact: true }).click();
    await bekle(12000);
    await p.evaluate(() => document.activeElement && document.activeElement.blur());
    await cek(p.locator('canvas:visible').first().locator('xpath=ancestor::section[1]'), 'pc-karsilastir.png');
  },
  // gercek kart: Pil testi ekrani (son testin sonucu + egri)
  async 'pc-pil-gercek'(t) {
    const p = await sayfa(t);
    await p.goto(KOPRU + '#/pil');
    await bekle(15000);
    await p.evaluate(() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); });
    await cek(p, 'pc-pil-gercek.png');
  },
  // demo kipinde: pencere statik icerik, karta komut gitmez
  async 'pc-baglanti'(t) {
    const p = await sayfa(t);
    await p.goto(DEMO + '#/canli');
    await bekle(6000);
    await p.locator('button').filter({ hasText: /^\W*Bağlantı$/ }).first().click();
    await bekle(2500);
    const pen = p.getByText('Nereye ne takılır').locator('xpath=ancestor::*[self::dialog or contains(@class,"pencere") or @role="dialog"][1]');
    await cek(p, 'pc-baglanti.png');
    if (await pen.count()) {
      await pen.locator('button, [role=tab]').filter({ hasText: /^\s*Akım\s*$/ }).first().click();
      await bekle(1200);
      await cek(pen, 'pc-baglanti-akim.png');
    } else console.log('  [pencere secici yok]');
  },
  // BELGELER: kutu 3B (bitmis kutu), yerlesim (tum plan + bir ara adim)
  async 'belge-kutu'(t) {
    const p = await sayfa(t, { gen: 1280, yuk: 800 });
    await p.goto(belge('8-kutu.html'));
    await bekle(3000);
    await p.locator('#uc-hepsi').check();
    await p.getByRole('button', { name: 'izometrik' }).click();
    await bekle(3000);
    const kutu = p.locator('#uc-tuval').locator('xpath=ancestor::*[self::details or self::section or self::div][1]');
    await kutu.scrollIntoViewIfNeeded();
    await bekle(1500);
    await cek(kutu, 'belge-kutu-3b.png');
    // ici: duvarlar saydam + kablolar
    await p.locator('#uc-duvar').selectOption('saydam');
    await p.locator('#uc-kablo').check();
    await bekle(2500);
    await cek(kutu, 'belge-kutu-ici.png');
    // bir alt adim: adim gezgini + 3B + o adimin cizimi
    await p.locator('#uc-hepsi').uncheck();
    await p.locator('#uc-duvar').selectOption('yakin');
    await p.getByRole('button', { name: process.env.KUTU_ADIM || '10', exact: true }).first().click();
    await bekle(2500);
    await p.setViewportSize({ width: 1280, height: 1000 });
    await p.evaluate(() => document.querySelector('.gorus').scrollIntoView({ block: 'start' }));
    await bekle(1500);
    await cek(p, 'belge-kutu-adim.png');
  },
  async 'belge-yerlesim'(t) {
    const p = await sayfa(t, { gen: 1280, yuk: 800 });
    await p.goto(belge('7-yerlesim.html'));
    await bekle(3000);
    await p.getByRole('button', { name: process.env.YER_ADIM || '4', exact: true }).first().click();
    await bekle(2500);
    await cek(p, 'belge-yerlesim-adim.png');
    await p.getByRole('button', { name: '8', exact: true }).first().click();
    await bekle(1500);
    await p.locator('#g-tum').check();
    await bekle(2500);
    await cek(p, 'belge-yerlesim-tum.png');
  },
};

(async () => {
  const isler = process.argv.slice(2);
  const t = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    await Promise.all(isler.map((ad) => {
      if (!ISLER[ad]) throw new Error('bilinmeyen is: ' + ad);
      return ISLER[ad](t).catch((e) => console.log('  [' + ad + ' HATA]', e.message.split('\n')[0]));
    }));
  } finally {
    await t.close();
  }
})();
