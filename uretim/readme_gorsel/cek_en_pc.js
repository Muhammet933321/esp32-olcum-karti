// Ingilizce PC paneli README goruntuleri (gercek kart, kopru) -> gorsel/readme/en
// Kullanim: node en_pc.js skop kayit karsilastir baglanti canli
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT);
const CIKIS = path.join(process.env.KOK, 'gorsel', 'readme', 'en');
const KOPRU = 'http://olcum.localhost:8770/';
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const blur = (p) => p.evaluate(() => document.activeElement && document.activeElement.blur());

async function sayfa(t, gen, yuk) {
  const ctx = await t.newContext({ viewport: { width: gen, height: yuk }, deviceScaleFactor: 1, locale: 'en-US' });
  await ctx.addInitScript(() => { try { localStorage.setItem('olcum.dil', '"en"'); } catch (e) {} });
  const p = await ctx.newPage();
  p.on('pageerror', (e) => console.log('  [sayfa hatasi]', e.message.slice(0, 160)));
  return p;
}

const ISLER = {
  async skop(t) {
    const p = await sayfa(t, 1440, 762);
    await p.goto(KOPRU + '#/skop');
    await bekle(9000);
    { const dv = p.getByRole('button', { name: /devral|take over/i }); if (await dv.count()) { await dv.first().click(); await bekle(4000); console.log('  suruculuk devralindi'); } }
    await p.getByRole('button', { name: 'Auto set', exact: true }).click();
    await bekle(9000);
    for (let i = 0; i < 6; i++) {
      const m = await p.evaluate(() => {
        const e = [...document.querySelectorAll('main *')].find((x) => x.children.length === 0 && /[µm]s\/böl/.test(x.textContent));
        let k = e; while (k && k.querySelectorAll('button').length < 2) k = k.parentElement;
        const metin = e.textContent.trim();
        if (/500\s*µs/.test(metin)) return metin;
        const d = [...k.querySelectorAll('button')];
        (/^(200|100|50|20)\s*µs/.test(metin) ? d[d.length - 1] : d[0]).click();
        return metin + ' -> tik';
      });
      console.log('  zaman tabani:', m);
      if (!/tik/.test(m)) break;
      await bekle(1000);
    }
    await p.getByRole('button', { name: 'Capture', exact: true }).click();
    await bekle(7000);
    await blur(p);
    console.log('  skop olcum:', (await p.locator('body').innerText()).replace(/\s+/g, ' ').match(/FREKANS.{0,230}/i)?.[0]);
    await p.screenshot({ path: path.join(CIKIS, 'pc-skop.png') });
  },
  async kayit(t) {
    const p = await sayfa(t, 1440, 1300);
    await p.goto(KOPRU + '#/kayit/70640');
    await bekle(25000);
    await blur(p);
    const g = p.locator('canvas:visible').first().locator('xpath=ancestor::section[1]');
    const etiketler = await g.locator('label').allInnerTexts();
    console.log('  grafik etiketleri:', JSON.stringify(etiketler));
    const mm = g.locator('label').filter({ hasText: /min|lowest/i }).locator('input');
    if (await mm.count()) { await mm.first().uncheck(); await bekle(1500); }
    // Turkce goruntuyle ayni kirpma: ad/etiket duzenleme formu gizlenir (kayit + grafik + ozet kalir)
    await p.evaluate(() => { const s = [...document.querySelectorAll('main section')].filter((e) => e.offsetParent); if (/EDIT NAME/i.test(s[1].innerText)) s[1].style.display = 'none'; });
    await bekle(800);
    const kutu = await p.evaluate(() => {
      const s = [...document.querySelectorAll('main section')].filter((e) => e.offsetParent);
      const a = s[0].getBoundingClientRect(), b = s[2].getBoundingClientRect();
      return { x: a.left + scrollX, y: a.top + scrollY, w: a.width, h: b.bottom - a.top, n: s.length, bas: s.slice(0, 4).map((e) => e.innerText.split('\n')[0]) };
    });
    console.log('  bolumler:', JSON.stringify(kutu));
    await p.screenshot({ path: path.join(CIKIS, 'pc-pil.png'), fullPage: true,
      clip: { x: kutu.x - 12, y: kutu.y - 12, width: kutu.w + 24, height: kutu.h + 24 } });
  },
  async karsilastir(t) {
    const p = await sayfa(t, 1440, 900);
    await p.goto(KOPRU + '#/kayitlar');
    await bekle(15000);
    for (const no of ['69354', '70640']) await p.locator('input[data-kl-sec$=":' + no + '"]').check();
    await p.locator('main').getByRole('link', { name: 'Compare', exact: true }).click();
    await bekle(15000);
    await blur(p);
    await p.locator('canvas:visible').first().locator('xpath=ancestor::section[1]').screenshot({ path: path.join(CIKIS, 'pc-karsilastir.png') });
  },
  async baglanti(t) {
    const p = await sayfa(t, 1440, 900);
    await p.goto(KOPRU + '#/canli');
    await bekle(8000);
    await p.locator('button').filter({ hasText: /Wiring/ }).first().click();
    await bekle(2500);
    const pen = p.getByText('What plugs where').locator('xpath=ancestor::*[self::dialog or contains(@class,"pencere") or @role="dialog"][1]');
    console.log('  pencere:', await pen.count(), JSON.stringify(await pen.locator('button, [role=tab]').allInnerTexts()));
    await pen.locator('button, [role=tab]').filter({ hasText: /^\s*Current\s*$/ }).first().click();
    await bekle(1500);
    await pen.screenshot({ path: path.join(CIKIS, 'pc-baglanti.png') });
  },
  async canli(t) {
    const p = await sayfa(t, 1440, 775);
    await p.goto(KOPRU + '#/canli');
    await bekle(6000);
    { const dv = p.getByRole('button', { name: /devral|take over/i }); if (await dv.count()) { await dv.first().click(); await bekle(2000); await p.reload(); console.log('  suruculuk devralindi'); } }
    await bekle(Number(process.env.CANLI_MS || 60000));
    await blur(p);
    await p.screenshot({ path: path.join(CIKIS, 'pc-canli.png') });
  },
};

(async () => {
  const t = await chromium.launch();
  try {
    for (const ad of process.argv.slice(2)) {
      console.log(ad);
      await ISLER[ad](t).catch((e) => console.log('  [HATA]', e.message.split('\n')[0]));
    }
  } finally { await t.close(); }
})();
