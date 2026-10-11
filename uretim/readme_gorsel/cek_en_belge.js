// Ingilizce rehber sayfalarinin README goruntuleri (BELGELER/en -> gorsel/readme/en)
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT);
const KOK = process.env.KOK;
const CIKIS = path.join(KOK, 'gorsel', 'readme', 'en');
const belge = (ad) => 'file:///' + path.join(KOK, 'BELGELER', 'en', ad).split(path.sep).join('/');
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const t = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const ctx = await t.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1, locale: 'en-US' });
    // yerlesim: adim 4.1
    let p = await ctx.newPage();
    p.on('pageerror', (e) => console.log('  [sayfa hatasi]', e.message.slice(0, 160)));
    await p.goto(belge('7-yerlesim.html'));
    await bekle(3000);
    await p.getByRole('button', { name: '4', exact: true }).first().click();
    await bekle(2000);
    console.log('  yerlesim baslik:', (await p.locator('#g-baslik').innerText()).slice(0, 80), '|', await p.locator('#g-sayac').innerText());
    await p.evaluate(() => { const r = document.querySelector('#g-baslik').getBoundingClientRect(); window.scrollBy(0, r.top - 20); });
    await bekle(1200);
    await p.screenshot({ path: path.join(CIKIS, 'belge-yerlesim.png') });
    await p.close();

    // kutu
    p = await ctx.newPage();
    p.on('pageerror', (e) => console.log('  [sayfa hatasi]', e.message.slice(0, 160)));
    await p.goto(belge('8-kutu.html'));
    await bekle(3000);
    await p.locator('#uc-hepsi').check();
    await p.getByRole('button', { name: 'isometric' }).click();
    await bekle(3000);
    const tuval = p.locator('#uc-tuval');
    await tuval.scrollIntoViewIfNeeded();
    await bekle(1500);
    await tuval.screenshot({ path: path.join(CIKIS, 'belge-kutu-3b.png') });
    await p.locator('#uc-duvar').selectOption('saydam');
    await p.locator('#uc-kablo').check();
    await bekle(2500);
    await tuval.screenshot({ path: path.join(CIKIS, 'belge-kutu-ici.png') });
    await p.locator('#uc-hepsi').uncheck();
    await p.locator('#uc-duvar').selectOption('yakin');
    await p.getByRole('button', { name: '10', exact: true }).first().click();
    await bekle(2500);
    await p.setViewportSize({ width: 1280, height: 1000 });
    await p.evaluate(() => document.querySelector('.gorus').scrollIntoView({ block: 'start' }));
    await bekle(1500);
    await p.screenshot({ path: path.join(CIKIS, 'belge-kutu-adim.png') });
    console.log('  tamam');
  } finally {
    await t.close();
  }
})();
