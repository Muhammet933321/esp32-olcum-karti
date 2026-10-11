/* ═══════════════════════════════════════════════════════════════════════
   5.12.121 (CE) — PANELIN GORUNUR METNI, node'da GERCEK Vue ile.

   test_arayuz3.js Vue'yu TAKLIT ediyor (sablon hic islenmiyor); bir metnin
   ekranda hangi dilde CIKTIGI ancak sablon gercekten islenince gorulur.
   Burada depodaki `vendor/vue.global.prod.js` (tarayicinin indirdigi AYNI
   dosya) kendi vm baglaminda yukleniyor ve DOM yerine duz nesne agacina
   cizen bir OZEL RENDERER (Vue `createRenderer`) kuruluyor. v-if / v-for /
   v-show / bilesenler / {{ }} Vue'nun kendi derleyicisi ve calisma
   zamaniyla isleniyor; agactan GORUNUR metin toplaniyor:
     - metin dugumleri (v-show ile gizli ogenin ve <script>/<style>/<svg>
       altindakiler HARIC),
     - title / placeholder / aria-label / alt oznitelikleri (ipucu, bos alan
       ve ekran okuyucu da "gorunur" sayilir).
   Tarayici DEGIL: CSS (display:none sinifi, text-transform) uygulanmaz —
   gizli bir dalin metni burada da sayilir (daha siki).
   ═══════════════════════════════════════════════════════════════════════ */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const VUE = path.join(__dirname, '..', 'arayuz3', 'vendor', 'vue.global.prod.js');

/* Derleyicinin tarayici surumu HTML varliklarini bir <div>'in innerHTML'iyle cozuyor. */
const VARLIK = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', hellip: '…', mdash: '—',
  ndash: '–', middot: '·', times: '×', minus: '−', deg: '°', micro: 'µ', plusmn: '±', rarr: '→', larr: '←' };
function varlikCoz(s) {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (t, a) => {
    if (a[0] === '#') return String.fromCodePoint(a[1] === 'x' || a[1] === 'X' ? parseInt(a.slice(2), 16) : Number(a.slice(1)));
    return a in VARLIK ? VARLIK[a] : t;
  });
}

function vueYukle() {
  const ctx = {
    console,
    setTimeout, clearTimeout, queueMicrotask, Promise,
    document: {
      createElement() {
        /* compiler-dom decodeHtmlBrowser: metin -> textContent; oznitelik -> '<div foo="…">' + children[0] */
        const d = { _h: '' };
        Object.defineProperty(d, 'innerHTML', { set(v) { this._h = v; } });
        Object.defineProperty(d, 'textContent', { get() { return varlikCoz(this._h); } });
        Object.defineProperty(d, 'children', {
          get() {
            const m = /^<div foo="([\s\S]*)">$/.exec(this._h);
            return [{ getAttribute: () => varlikCoz(m ? m[1] : '') }];
          },
        });
        return d;
      },
    },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(VUE, 'utf8') + '\n;globalThis.Vue = Vue;', ctx, { filename: 'vue.global.prod.js' });
  return ctx.Vue;
}

/* ── duz nesne agaci ─────────────────────────────────────────────────── */
function oge(etiket) {
  return {
    tur: 'oge', etiket, ozn: {}, cocuk: [], ata: null, style: {}, value: '', checked: false, options: [],
    addEventListener() {}, removeEventListener() {}, setAttribute(a, v) { this.ozn[a] = String(v); },
    removeAttribute(a) { delete this.ozn[a]; }, getAttribute(a) { return this.ozn[a] ?? null; },
    focus() {}, blur() {}, getContext() { return null; }, getBoundingClientRect() { return { width: 0, height: 0, left: 0, top: 0 }; },
  };
}
const dugumIslemleri = {
  createElement: (etiket) => oge(etiket),
  createText: (metin) => ({ tur: 'metin', metin, ata: null }),
  createComment: (metin) => ({ tur: 'yorum', metin, ata: null }),
  setText(d, metin) { d.metin = metin; },
  setElementText(o, metin) {
    for (const c of o.cocuk) c.ata = null;
    o.cocuk = metin === '' ? [] : [{ tur: 'metin', metin, ata: o }];
  },
  insert(c, ata, capa) {
    if (c.ata) dugumIslemleri.remove(c);
    const i = capa ? ata.cocuk.indexOf(capa) : -1;
    if (i < 0) ata.cocuk.push(c); else ata.cocuk.splice(i, 0, c);
    c.ata = ata;
  },
  remove(c) {
    const a = c.ata;
    if (a) { const i = a.cocuk.indexOf(c); if (i >= 0) a.cocuk.splice(i, 1); }
    c.ata = null;
  },
  parentNode: (d) => d.ata,
  nextSibling(d) {
    const a = d.ata;
    if (!a) return null;
    return a.cocuk[a.cocuk.indexOf(d) + 1] || null;
  },
  /* <teleport to="body"> (Baglanti penceresi): hedef bu cizimin govdesi. `.sinif` (SZ: Sifir kumesi
     `.skop-denetim`e teleport, defer): cizimin agacinda (kok + govde) ilk eslesen oge. */
  querySelector(secici) {
    if (secici === 'body') return GOVDE.dugum;
    const m = /^\.([\w-]+)$/.exec(secici);
    if (!m) return null;
    const ara = (d) => {
      if (!d || d.tur !== 'oge') return null;
      if ((d.ozn.class || '').split(/\s+/).includes(m[1])) return d;
      for (const c of d.cocuk) { const x = ara(c); if (x) return x; }
      return null;
    };
    return ara(GOVDE.kok) || ara(GOVDE.dugum);
  },
  setScopeId() {},
  insertStaticContent() { throw new Error('statik icerik beklenmiyor'); },
};
function ozellikYaz(o, ad, onceki, yeni) {
  if (/^on[A-Z]/.test(ad)) return;
  if (ad === 'style') { o.ozn.style = typeof yeni === 'string' ? yeni : JSON.stringify(yeni || {}); return; }
  if (ad === 'value' || ad === 'checked') { o[ad] = yeni; return; }
  if (ad === 'innerHTML') { o.html = yeni == null ? '' : String(yeni); return; }   // v-html
  if (yeni === null || yeni === undefined || yeni === false) delete o.ozn[ad];
  else o.ozn[ad] = typeof yeni === 'object' ? JSON.stringify(yeni) : String(yeni);
}

const GOVDE = { dugum: null };
let VUE_ONBELLEK = null;
/** Gercek Vue + ozel renderer. */
function kur() {
  if (VUE_ONBELLEK) return VUE_ONBELLEK;
  const Vue = vueYukle();
  const r = Vue.createRenderer(Object.assign({ patchProp: ozellikYaz }, dugumIslemleri));
  VUE_ONBELLEK = { Vue, createApp: r.createApp };
  return VUE_ONBELLEK;
}

const ATLA = new Set(['script', 'style', 'svg', 'canvas', 'template']);
const OZN = ['title', 'placeholder', 'aria-label', 'alt'];
/** Gorunur metin parcalari: [{ tur: 'metin'|ozn, metin, yol }]. Bitisik metin dugumleri (ayni ogede) BIRLESIK. */
function gorunurMetin(kok) {
  const cikti = [];
  const gez = (d, yol) => {
    if (d.tur !== 'oge') return;
    if (ATLA.has(d.etiket) || d.style.display === 'none' || 'hidden' in d.ozn) return;
    const y = yol + '>' + d.etiket + (d.ozn.class ? '.' + d.ozn.class.split(/\s+/)[0] : '');
    for (const a of OZN) if (d.ozn[a] && d.ozn[a].trim()) cikti.push({ tur: a, metin: d.ozn[a].trim(), yol: y });
    if (d.html) htmlMetni(d.html, y + '>v-html', cikti);
    let parca = '';
    const bosalt = () => { const t = parca.replace(/\s+/g, ' ').trim(); if (t) cikti.push({ tur: 'metin', metin: t, yol: y }); parca = ''; };
    for (const c of d.cocuk) {
      if (c.tur === 'metin') parca += c.metin;
      else if (c.tur === 'oge') { bosalt(); gez(c, y); }
    }
    bosalt();
  };
  gez(kok, '');
  return cikti;
}

/** v-html icerigi (uretilmis SVG / satir ici HTML): metin + oznitelikler. SVG <text> yolu `>svg>text` ile isaretli. */
function htmlMetni(html, yol, cikti) {
  const t = html.replace(/<(script|style)\b[\s\S]*?<\/\1>/g, ' ');
  for (const m of t.matchAll(/<([a-zA-Z][\w-]*)\b([^>]*)>/g)) {
    for (const a of OZN) {
      const o = new RegExp('\\s' + a + '="([^"]*)"').exec(m[2]);
      if (o && o[1].trim()) cikti.push({ tur: a, metin: varlikCoz(o[1]).trim(), yol: yol + '>' + m[1] });
    }
  }
  /* svg icindeki <text> ayri parca (fiziksel etiketler izin listesine yol ile baglanir) */
  const svgsiz = t.replace(/<svg\b[\s\S]*?<\/svg>/g, (svg) => {
    for (const m of svg.matchAll(/<text\b[^>]*>([\s\S]*?)<\/text>/g)) {
      const x = varlikCoz(m[1].replace(/<[^>]*>/g, '')).replace(/\s+/g, ' ').trim();
      if (x) cikti.push({ tur: 'metin', metin: x, yol: yol + '>svg>text' });
    }
    return ' ';
  });
  const duz = varlikCoz(svgsiz.replace(/<\/?(?:b|strong|em|i|code|kbd|sub|sup|abbr|small|span|a)\b[^>]*>/g, '').replace(/<[^>]*>/g, '\n'));
  for (const x of duz.split('\n').map((v) => v.replace(/\s+/g, ' ').trim()).filter(Boolean)) {
    cikti.push({ tur: 'metin', metin: x, yol });
  }
}

/** Bekleyen isler (mikro gorevler + dinamik import) bitene kadar dondur. */
async function bekle(tur = 6) {
  for (let i = 0; i < tur; i++) await new Promise((r) => setImmediate(r));
}

/** Kok uygulamayi (ya da bir bileseni) cizer: { kok, ornek, uyg, metin() }. */
function ciz(secenek) {
  const { createApp } = kur();
  const kok = oge('div');
  const govde = oge('body');
  GOVDE.dugum = govde;
  GOVDE.kok = kok;
  const uyg = createApp(secenek);
  uyg.config.warnHandler = () => {};
  uyg.config.errorHandler = (h) => { throw h; };
  const ornek = uyg.mount(kok);
  return { kok, govde, ornek, uyg, metin: () => gorunurMetin(kok).concat(gorunurMetin(govde)) };
}

module.exports = { kur, ciz, bekle, gorunurMetin, varlikCoz };
